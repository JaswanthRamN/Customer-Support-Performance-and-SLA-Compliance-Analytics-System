-- Replace the timestamp only if the cleaned dataset has a different snapshot.
-- Buckets are [0,24), [24,48), [48,72), [72,infinity) calendar hours.
WITH params AS (
    SELECT TIMESTAMPTZ '2026-07-01 00:00:00+00' AS analysis_as_of
),
backlog AS (
    SELECT t.ticket_id, t.priority, t.resolution_sla_status,
           EXTRACT(EPOCH FROM (p.analysis_as_of - t.created_at)) / 3600.0 AS age_hours
    FROM support_analytics.tickets t CROSS JOIN params p
    WHERE t.resolved_at IS NULL
)
SELECT priority,
       CASE WHEN age_hours < 24 THEN 'Under 24h'
            WHEN age_hours < 48 THEN '24–<48h'
            WHEN age_hours < 72 THEN '48–<72h'
            ELSE '72h+' END AS age_bucket,
       COUNT(*) AS unresolved_tickets,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Breached') AS overdue_unresolved,
       ROUND(AVG(age_hours)::numeric, 2) AS average_age_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY age_hours)::numeric, 2) AS median_age_hours
FROM backlog
GROUP BY priority, age_bucket
ORDER BY priority, age_bucket;

-- Oldest unresolved tickets at the same fixed snapshot.
WITH params AS (
    SELECT TIMESTAMPTZ '2026-07-01 00:00:00+00' AS analysis_as_of
)
SELECT t.ticket_id, t.priority, t.status, t.current_team_id,
       ROUND((EXTRACT(EPOCH FROM (p.analysis_as_of - t.created_at)) / 3600.0)::numeric, 2) AS age_hours,
       t.resolution_sla_status
FROM support_analytics.tickets t CROSS JOIN params p
WHERE t.resolved_at IS NULL
ORDER BY age_hours DESC, t.ticket_id
LIMIT 20;
