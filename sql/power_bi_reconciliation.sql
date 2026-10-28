-- Reconcile the headline Power BI DAX measures against PostgreSQL.
-- Each metric is calculated from ticket-grain rows or the separate feedback fact.
-- Run after sql/schema.sql has been loaded. Percentages return 0-100 values.

WITH ticket_metrics AS (
    SELECT
        COUNT(DISTINCT ticket_id) AS total_tickets,
        COUNT(DISTINCT ticket_id) FILTER (
            WHERE status IN ('Open', 'In Progress', 'Pending')
        ) AS open_tickets,
        COUNT(DISTINCT ticket_id) FILTER (WHERE resolved_at IS NOT NULL) AS resolved_tickets,
        COUNT(DISTINCT ticket_id) FILTER (WHERE resolved_at IS NULL) AS unresolved_backlog,
        AVG(EXTRACT(EPOCH FROM (first_response_at - created_at)) / 3600.0)
            FILTER (WHERE first_response_at IS NOT NULL) AS average_response_hours,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (first_response_at - created_at)) / 3600.0
        ) FILTER (WHERE first_response_at IS NOT NULL) AS median_response_hours,
        AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
            FILTER (WHERE resolved_at IS NOT NULL) AS average_resolution_hours,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0
        ) FILTER (WHERE resolved_at IS NOT NULL) AS median_resolution_hours,
        COUNT(*) FILTER (WHERE response_sla_status = 'Met') AS response_sla_met,
        COUNT(*) FILTER (WHERE response_sla_status = 'Breached') AS response_sla_breached,
        COUNT(*) FILTER (WHERE resolution_sla_status = 'Met') AS resolution_sla_met,
        COUNT(*) FILTER (WHERE resolution_sla_status = 'Breached') AS resolution_sla_breached,
        COUNT(*) FILTER (
            WHERE response_sla_status = 'Breached'
               OR resolution_sla_status = 'Breached'
        ) AS tickets_with_any_sla_breach,
        COUNT(DISTINCT ticket_id) FILTER (WHERE reopen_count > 0) AS reopened_tickets
    FROM support_analytics.tickets
),
feedback_metrics AS (
    SELECT
        COUNT(*) AS feedback_responses,
        COUNT(DISTINCT ticket_id) AS rated_tickets,
        AVG(csat_score::numeric) AS average_csat,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY csat_score) AS median_csat,
        COUNT(*) FILTER (WHERE csat_score >= 4) AS positive_feedback_responses
    FROM support_analytics.customer_feedback
)
SELECT
    t.total_tickets,
    t.open_tickets,
    t.resolved_tickets,
    t.unresolved_backlog,
    ROUND(t.average_response_hours::numeric, 2) AS average_response_hours,
    ROUND(t.median_response_hours::numeric, 2) AS median_response_hours,
    ROUND(t.average_resolution_hours::numeric, 2) AS average_resolution_hours,
    ROUND(t.median_resolution_hours::numeric, 2) AS median_resolution_hours,
    t.response_sla_breached,
    ROUND(100.0 * t.response_sla_met /
        NULLIF(t.response_sla_met + t.response_sla_breached, 0), 2)
        AS first_response_sla_compliance_pct,
    t.resolution_sla_breached,
    ROUND(100.0 * t.resolution_sla_met /
        NULLIF(t.resolution_sla_met + t.resolution_sla_breached, 0), 2)
        AS resolution_sla_compliance_pct,
    t.response_sla_breached + t.resolution_sla_breached AS sla_breach_count,
    t.tickets_with_any_sla_breach,
    t.reopened_tickets,
    f.feedback_responses,
    f.rated_tickets,
    ROUND(f.average_csat, 2) AS average_csat,
    ROUND(f.median_csat::numeric, 2) AS median_csat,
    ROUND(100.0 * f.positive_feedback_responses /
        NULLIF(f.feedback_responses, 0), 2) AS positive_csat_pct
FROM ticket_metrics AS t
CROSS JOIN feedback_metrics AS f;
