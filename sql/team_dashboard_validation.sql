-- Validate the Power BI team-comparison dashboard without multiplying ticket rows.
-- Result set 1 uses current snapshot ownership. Result set 2 uses historical
-- assignment ownership and must remain separate from ticket-outcome metrics.

-- 1. Current-owner ticket cohorts: one output row per current team.
WITH reassignment_by_ticket AS (
    SELECT ticket_id,
           COUNT(*) FILTER (WHERE assignment_reason = 'Reassignment') AS reassignment_events
    FROM support_analytics.assignment_history
    GROUP BY ticket_id
),
feedback_by_ticket AS (
    SELECT ticket_id, COUNT(*) AS feedback_responses,
           SUM(csat_score::numeric) AS customer_rating_sum
    FROM support_analytics.customer_feedback
    GROUP BY ticket_id
),
ticket_grain AS (
    SELECT t.ticket_id, t.current_team_id, t.first_response_at, t.resolved_at,
           t.created_at, t.response_sla_status, t.resolution_sla_status,
           t.reopen_count,
           COALESCE(r.reassignment_events, 0) AS reassignment_events,
           COALESCE(f.feedback_responses, 0) AS feedback_responses,
           COALESCE(f.customer_rating_sum, 0) AS customer_rating_sum
    FROM support_analytics.tickets AS t
    LEFT JOIN reassignment_by_ticket AS r USING (ticket_id)
    LEFT JOIN feedback_by_ticket AS f USING (ticket_id)
)
SELECT
    tm.team_name,
    COUNT(*) AS ticket_sample,
    COUNT(*) FILTER (WHERE first_response_at IS NOT NULL) AS response_time_sample,
    ROUND((AVG(EXTRACT(EPOCH FROM (first_response_at - created_at)) / 3600.0)
        FILTER (WHERE first_response_at IS NOT NULL))::numeric, 2) AS average_response_hours,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (first_response_at - created_at)) / 3600.0)
        FILTER (WHERE first_response_at IS NOT NULL))::numeric, 2) AS median_response_hours,
    COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) AS resolution_time_sample,
    ROUND((AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
        FILTER (WHERE resolved_at IS NOT NULL))::numeric, 2) AS average_resolution_hours,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
        FILTER (WHERE resolved_at IS NOT NULL))::numeric, 2) AS median_resolution_hours,
    COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
        AND response_sla_status IN ('Met', 'Breached')) AS completed_response_eligible,
    ROUND(100.0 * COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
        AND response_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
            AND response_sla_status IN ('Met', 'Breached')), 0), 2)
        AS completed_response_compliance_pct,
    COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
        AND resolution_sla_status IN ('Met', 'Breached')) AS completed_resolution_eligible,
    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
        AND resolution_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
            AND resolution_sla_status IN ('Met', 'Breached')), 0), 2)
        AS completed_resolution_compliance_pct,
    COUNT(*) FILTER (WHERE resolved_at IS NULL) AS current_backlog,
    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_at IS NULL) /
        NULLIF(COUNT(*), 0), 2) AS current_backlog_pct,
    SUM(reassignment_events) AS reassignment_events,
    COUNT(*) FILTER (WHERE reassignment_events > 0) AS reassigned_tickets,
    ROUND(100.0 * COUNT(*) FILTER (WHERE reassignment_events > 0) /
        NULLIF(COUNT(*), 0), 2) AS reassigned_ticket_pct,
    ROUND(100.0 * SUM(reassignment_events) / NULLIF(COUNT(*), 0), 2)
        AS reassignment_events_per_100_tickets,
    COUNT(*) FILTER (WHERE reopen_count > 0) AS reopened_tickets,
    ROUND(100.0 * COUNT(*) FILTER (WHERE reopen_count > 0) /
        NULLIF(COUNT(*), 0), 2) AS reopened_ticket_pct,
    SUM(feedback_responses) AS customer_rating_sample,
    ROUND(SUM(customer_rating_sum) / NULLIF(SUM(feedback_responses), 0), 2)
        AS average_customer_rating
FROM ticket_grain AS g
JOIN support_analytics.teams AS tm ON tm.team_id = g.current_team_id
GROUP BY tm.team_name
ORDER BY tm.team_name;

-- 2. Historical assignment lens: one row per recorded ownership interval.
-- Distinct ticket counts are non-additive because one ticket can visit many teams.
SELECT
    tm.team_name,
    COUNT(*) AS assignment_intervals,
    COUNT(DISTINCT h.ticket_id) AS distinct_assigned_tickets,
    COUNT(*) FILTER (WHERE h.assignment_reason = 'Reassignment') AS reassignment_events,
    ROUND(100.0 * COUNT(*) FILTER (WHERE h.assignment_reason = 'Reassignment') /
        NULLIF(COUNT(*), 0), 2) AS reassignment_event_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE h.assignment_reason = 'Reassignment') /
        NULLIF(COUNT(*), 0), 2) AS reassignment_events_per_100_intervals
FROM support_analytics.assignment_history AS h
JOIN support_analytics.teams AS tm ON tm.team_id = h.team_id
GROUP BY tm.team_name
ORDER BY tm.team_name;

-- 3. Grain and relationship checks; every result should be zero except row totals.
SELECT
    (SELECT COUNT(*) FROM support_analytics.tickets) AS ticket_rows,
    (SELECT COUNT(DISTINCT ticket_id) FROM support_analytics.tickets) AS distinct_ticket_ids,
    (SELECT COUNT(*) FROM support_analytics.assignment_history) AS assignment_rows,
    (SELECT COUNT(*) FROM (
        SELECT ticket_id FROM support_analytics.customer_feedback
        GROUP BY ticket_id HAVING COUNT(*) > 1
    ) AS duplicate_feedback) AS tickets_with_duplicate_feedback,
    (SELECT COUNT(*) FROM support_analytics.tickets t
        LEFT JOIN support_analytics.teams tm ON tm.team_id = t.current_team_id
        WHERE tm.team_id IS NULL) AS tickets_without_current_team,
    (SELECT COUNT(*) FROM support_analytics.assignment_history h
        LEFT JOIN support_analytics.teams tm ON tm.team_id = h.team_id
        WHERE tm.team_id IS NULL) AS assignments_without_historical_team;
