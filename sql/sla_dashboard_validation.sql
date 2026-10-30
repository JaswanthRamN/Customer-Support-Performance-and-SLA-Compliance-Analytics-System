-- Power BI SLA dashboard validation. Each statement returns one result set.
-- The fixed snapshot must match powerbi/power_query/pAnalysisAsOfUtc.m.
-- Completed compliance and current overdue backlog are deliberately separate.

-- 1. Headline populations and compliance rates.
WITH p AS (SELECT TIMESTAMPTZ '2026-07-01 00:00:00+00' AS as_of_utc)
SELECT
    COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
        AND response_sla_status IN ('Met', 'Breached')) AS completed_response_eligible,
    COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
        AND response_sla_status = 'Breached') AS completed_response_breached,
    ROUND(100.0 * COUNT(*) FILTER (WHERE first_response_at IS NOT NULL AND response_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
            AND response_sla_status IN ('Met', 'Breached')), 0), 2) AS completed_response_compliance_pct,
    COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
        AND resolution_sla_status IN ('Met', 'Breached')) AS completed_resolution_eligible,
    COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
        AND resolution_sla_status = 'Breached') AS completed_resolution_breached,
    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_at IS NOT NULL AND resolution_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
            AND resolution_sla_status IN ('Met', 'Breached')), 0), 2) AS completed_resolution_compliance_pct,
    COUNT(*) FILTER (WHERE first_response_at IS NULL AND response_sla_status = 'Breached')
        AS current_overdue_unanswered,
    COUNT(*) FILTER (WHERE resolved_at IS NULL AND resolution_sla_status = 'Breached')
        AS current_overdue_unresolved,
    COUNT(*) FILTER (WHERE
        (first_response_at IS NULL AND response_sla_status = 'Pending'
            AND response_deadline > p.as_of_utc
            AND response_deadline <= p.as_of_utc
                + make_interval(secs => (response_target_minutes * 0.25 * 60)::double precision))
        OR
        (resolved_at IS NULL AND resolution_sla_status = 'Pending'
            AND resolution_deadline > p.as_of_utc
            AND resolution_deadline <= p.as_of_utc
                + make_interval(secs => (resolution_target_minutes * 0.25 * 60)::double precision)))
        AS approaching_any_deadline
FROM support_analytics.tickets
CROSS JOIN p;

-- 2. Completed compliance by priority and current team.
SELECT
    t.priority,
    tm.team_name,
    COUNT(*) FILTER (WHERE t.first_response_at IS NOT NULL
        AND t.response_sla_status IN ('Met', 'Breached')) AS response_eligible,
    ROUND(100.0 * COUNT(*) FILTER (WHERE t.first_response_at IS NOT NULL
        AND t.response_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE t.first_response_at IS NOT NULL
            AND t.response_sla_status IN ('Met', 'Breached')), 0), 2)
        AS completed_response_compliance_pct,
    COUNT(*) FILTER (WHERE t.resolved_at IS NOT NULL
        AND t.resolution_sla_status IN ('Met', 'Breached')) AS resolution_eligible,
    ROUND(100.0 * COUNT(*) FILTER (WHERE t.resolved_at IS NOT NULL
        AND t.resolution_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE t.resolved_at IS NOT NULL
            AND t.resolution_sla_status IN ('Met', 'Breached')), 0), 2)
        AS completed_resolution_compliance_pct
FROM support_analytics.tickets AS t
JOIN support_analytics.teams AS tm ON tm.team_id = t.current_team_id
GROUP BY t.priority, tm.team_name
ORDER BY CASE t.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2
    WHEN 'Medium' THEN 3 ELSE 4 END, tm.team_name;

-- 3. Created-ticket cohort trend. This is not a historical backlog trend.
SELECT
    date_trunc('month', created_at AT TIME ZONE 'UTC')::date AS created_month,
    COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
        AND response_sla_status IN ('Met', 'Breached')) AS response_eligible,
    ROUND(100.0 * COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
        AND response_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE first_response_at IS NOT NULL
            AND response_sla_status IN ('Met', 'Breached')), 0), 2)
        AS completed_response_compliance_pct,
    COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
        AND resolution_sla_status IN ('Met', 'Breached')) AS resolution_eligible,
    ROUND(100.0 * COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
        AND resolution_sla_status = 'Met') /
        NULLIF(COUNT(*) FILTER (WHERE resolved_at IS NOT NULL
            AND resolution_sla_status IN ('Met', 'Breached')), 0), 2)
        AS completed_resolution_compliance_pct
FROM support_analytics.tickets
GROUP BY 1
ORDER BY 1;

-- 4. Current overdue unresolved ticket detail.
WITH p AS (SELECT TIMESTAMPTZ '2026-07-01 00:00:00+00' AS as_of_utc)
SELECT t.ticket_id, t.priority, tm.team_name, t.status, t.created_at,
       t.resolution_deadline,
       ROUND(EXTRACT(EPOCH FROM (p.as_of_utc - t.resolution_deadline)) / 3600.0, 2)
           AS hours_overdue
FROM support_analytics.tickets AS t
JOIN support_analytics.teams AS tm ON tm.team_id = t.current_team_id
CROSS JOIN p
WHERE t.resolved_at IS NULL AND t.resolution_sla_status = 'Breached'
ORDER BY hours_overdue DESC, t.ticket_id;

-- 5. Tickets approaching either deadline: pending and within 25% of its target.
WITH p AS (SELECT TIMESTAMPTZ '2026-07-01 00:00:00+00' AS as_of_utc)
SELECT t.ticket_id, t.priority, tm.team_name, t.status,
       CASE
           WHEN t.first_response_at IS NULL AND t.response_sla_status = 'Pending'
                AND t.response_deadline > p.as_of_utc
                AND t.response_deadline <= p.as_of_utc
                    + make_interval(secs => (t.response_target_minutes * 0.25 * 60)::double precision)
               THEN 'First response'
           WHEN t.resolved_at IS NULL AND t.resolution_sla_status = 'Pending'
                AND t.resolution_deadline > p.as_of_utc
                AND t.resolution_deadline <= p.as_of_utc
                    + make_interval(secs => (t.resolution_target_minutes * 0.25 * 60)::double precision)
               THEN 'Resolution'
       END AS approaching_commitment,
       LEAST(
           CASE WHEN t.first_response_at IS NULL AND t.response_sla_status = 'Pending'
                THEN EXTRACT(EPOCH FROM (t.response_deadline - p.as_of_utc)) / 60.0 END,
           CASE WHEN t.resolved_at IS NULL AND t.resolution_sla_status = 'Pending'
                THEN EXTRACT(EPOCH FROM (t.resolution_deadline - p.as_of_utc)) / 60.0 END
       ) AS minutes_remaining
FROM support_analytics.tickets AS t
JOIN support_analytics.teams AS tm ON tm.team_id = t.current_team_id
CROSS JOIN p
WHERE (t.first_response_at IS NULL AND t.response_sla_status = 'Pending'
        AND t.response_deadline > p.as_of_utc
        AND t.response_deadline <= p.as_of_utc
            + make_interval(secs => (t.response_target_minutes * 0.25 * 60)::double precision))
   OR (t.resolved_at IS NULL AND t.resolution_sla_status = 'Pending'
        AND t.resolution_deadline > p.as_of_utc
        AND t.resolution_deadline <= p.as_of_utc
            + make_interval(secs => (t.resolution_target_minutes * 0.25 * 60)::double precision))
ORDER BY minutes_remaining, t.ticket_id;
