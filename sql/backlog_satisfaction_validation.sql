-- Validate the Power BI unresolved-ticket and customer-satisfaction pages.
-- The snapshot must match pAnalysisAsOfUtc.m. Ticket volume and feedback volume
-- are separate populations; missing feedback never becomes a zero score.

-- 1. Current backlog headline measures.
SELECT
    COUNT(*) FILTER (WHERE resolved_at IS NULL) AS unresolved_backlog,
    COUNT(*) FILTER (WHERE resolved_at IS NULL
        AND resolution_sla_status = 'Breached') AS overdue_backlog,
    COUNT(*) FILTER (WHERE resolved_at IS NULL
        AND priority IN ('Critical', 'High')) AS high_priority_backlog,
    COUNT(*) FILTER (WHERE resolved_at IS NULL
        AND resolution_sla_status = 'Breached'
        AND priority IN ('Critical', 'High')) AS high_priority_overdue_backlog,
    COUNT(*) FILTER (WHERE resolved_at IS NULL
        AND current_agent_id IS NULL) AS unassigned_current_tickets
FROM support_analytics.tickets;

-- 2. Mutually exclusive unresolved aging buckets.
WITH p AS (SELECT TIMESTAMPTZ '2026-07-01 00:00:00+00' AS as_of_utc),
backlog AS (
    SELECT t.ticket_id, t.priority, t.current_team_id,
           EXTRACT(EPOCH FROM (p.as_of_utc - t.created_at)) / 3600.0 AS age_hours,
           t.resolution_sla_status
    FROM support_analytics.tickets AS t
    CROSS JOIN p
    WHERE t.resolved_at IS NULL
), bucketed AS (
    SELECT *, CASE
        WHEN age_hours <= 24 THEN '0-24 hours'
        WHEN age_hours <= 72 THEN '25-72 hours'
        WHEN age_hours <= 168 THEN '4-7 days'
        WHEN age_hours <= 336 THEN '8-14 days'
        WHEN age_hours <= 720 THEN '15-30 days'
        ELSE '31+ days' END AS age_bucket,
        CASE
        WHEN age_hours <= 24 THEN 1 WHEN age_hours <= 72 THEN 2
        WHEN age_hours <= 168 THEN 3 WHEN age_hours <= 336 THEN 4
        WHEN age_hours <= 720 THEN 5 ELSE 6 END AS bucket_sort
    FROM backlog
)
SELECT age_bucket, COUNT(*) AS ticket_volume,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Breached') AS overdue_ticket_volume,
       ROUND(AVG(age_hours)::numeric, 2) AS average_age_hours
FROM bucketed
GROUP BY age_bucket, bucket_sort
ORDER BY bucket_sort;

-- 3. Backlog detail by current team, priority, category, and channel.
SELECT tm.team_name, t.priority, t.category, t.channel,
       COUNT(*) AS unresolved_ticket_volume,
       COUNT(*) FILTER (WHERE t.resolution_sla_status = 'Breached') AS overdue_ticket_volume,
       COUNT(*) FILTER (WHERE t.current_agent_id IS NULL) AS unassigned_ticket_volume
FROM support_analytics.tickets AS t
JOIN support_analytics.teams AS tm ON tm.team_id = t.current_team_id
WHERE t.resolved_at IS NULL
GROUP BY tm.team_name, t.priority, t.category, t.channel
ORDER BY tm.team_name, t.priority, t.category, t.channel;

-- 4. Rating distribution. Only actual feedback rows are eligible.
SELECT f.csat_score,
       COUNT(*) AS feedback_volume,
       ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2)
           AS feedback_distribution_pct
FROM support_analytics.customer_feedback AS f
GROUP BY f.csat_score
ORDER BY f.csat_score;

-- 5. Overall satisfaction and coverage populations.
SELECT
    (SELECT COUNT(*) FROM support_analytics.tickets) AS ticket_volume,
    (SELECT COUNT(*) FROM support_analytics.tickets WHERE resolved_at IS NOT NULL)
        AS resolved_ticket_volume,
    COUNT(*) AS feedback_volume,
    ROUND(AVG(csat_score::numeric), 2) AS average_rating,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY csat_score)::numeric, 2)
        AS median_rating,
    ROUND(100.0 * COUNT(*) FILTER (WHERE csat_score >= 4) /
        NULLIF(COUNT(*), 0), 2) AS positive_rating_pct,
    ROUND(100.0 * COUNT(*) /
        NULLIF((SELECT COUNT(*) FROM support_analytics.tickets
            WHERE resolved_at IS NOT NULL), 0), 2) AS feedback_coverage_pct
FROM support_analytics.customer_feedback;

-- 6. Satisfaction by current team, category, and channel. Feedback is first
-- aggregated to one ticket row so it cannot multiply ticket volume.
WITH feedback_by_ticket AS (
    SELECT ticket_id, COUNT(*) AS feedback_volume,
           SUM(csat_score::numeric) AS rating_sum,
           COUNT(*) FILTER (WHERE csat_score >= 4) AS positive_feedback_volume
    FROM support_analytics.customer_feedback
    GROUP BY ticket_id
), ticket_grain AS (
    SELECT t.ticket_id, t.resolved_at, t.category, t.channel, tm.team_name,
           COALESCE(f.feedback_volume, 0) AS feedback_volume,
           COALESCE(f.rating_sum, 0) AS rating_sum,
           COALESCE(f.positive_feedback_volume, 0) AS positive_feedback_volume
    FROM support_analytics.tickets AS t
    JOIN support_analytics.teams AS tm ON tm.team_id = t.current_team_id
    LEFT JOIN feedback_by_ticket AS f USING (ticket_id)
), dimensions AS (
    SELECT 'Current Team'::text AS dimension_type, team_name AS dimension_value, *
    FROM ticket_grain
    UNION ALL
    SELECT 'Category', category, * FROM ticket_grain
    UNION ALL
    SELECT 'Channel', channel, * FROM ticket_grain
)
SELECT dimension_type, dimension_value,
       COUNT(*) AS ticket_volume,
       COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) AS resolved_ticket_volume,
       SUM(feedback_volume) AS feedback_volume,
       ROUND(SUM(rating_sum) / NULLIF(SUM(feedback_volume), 0), 2) AS average_rating,
       ROUND(100.0 * SUM(positive_feedback_volume) /
           NULLIF(SUM(feedback_volume), 0), 2) AS positive_rating_pct,
       ROUND(100.0 * SUM(feedback_volume) /
           NULLIF(COUNT(*) FILTER (WHERE resolved_at IS NOT NULL), 0), 2)
           AS feedback_coverage_pct
FROM dimensions
GROUP BY dimension_type, dimension_value
ORDER BY dimension_type, dimension_value;

-- 7. Integrity checks. Expected: 0 unassigned current tickets and 0 duplicate
-- feedback ticket IDs under this project's required-ownership/one-survey schema.
SELECT
    COUNT(*) FILTER (WHERE current_agent_id IS NULL) AS tickets_without_current_agent,
    COUNT(*) FILTER (WHERE current_team_id IS NULL) AS tickets_without_current_team,
    (SELECT COUNT(*) FROM (
        SELECT ticket_id FROM support_analytics.customer_feedback
        GROUP BY ticket_id HAVING COUNT(*) > 1
    ) AS duplicates) AS tickets_with_duplicate_feedback
FROM support_analytics.tickets;
