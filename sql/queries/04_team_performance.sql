-- Assignment history is aggregated to ticket grain before the ticket join.
-- Team means current snapshot assignment; it does not measure agent effort.
WITH handoffs AS (
    SELECT ticket_id,
           COUNT(*) FILTER (WHERE assignment_reason = 'Reassignment') AS reassignment_events
    FROM support_analytics.assignment_history
    GROUP BY ticket_id
),
ticket_grain AS (
    SELECT t.*, tm.team_name, f.csat_score,
           COALESCE(h.reassignment_events, 0) AS reassignment_events,
           EXTRACT(EPOCH FROM (t.first_response_at - t.created_at)) / 3600.0 AS response_hours,
           EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 3600.0 AS resolution_hours
    FROM support_analytics.tickets t
    JOIN support_analytics.teams tm ON tm.team_id = t.current_team_id
    LEFT JOIN handoffs h ON h.ticket_id = t.ticket_id
    LEFT JOIN support_analytics.customer_feedback f ON f.ticket_id = t.ticket_id
)
SELECT team_name,
       COUNT(*) AS tickets,
       COUNT(resolved_at) AS resolved_tickets,
       COUNT(*) FILTER (WHERE resolved_at IS NULL) AS unresolved_tickets,
       COUNT(response_hours) AS answered_tickets,
       ROUND(AVG(response_hours)::numeric, 2) AS response_mean_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_hours)::numeric, 2) AS response_median_hours,
       ROUND(AVG(resolution_hours)::numeric, 2) AS resolution_mean_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 2) AS resolution_median_hours,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Met') AS overall_sla_met,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Breached') AS overall_sla_breached,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Pending') AS overall_sla_pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE overall_sla_status = 'Met') /
             NULLIF(COUNT(*) FILTER (WHERE overall_sla_status IN ('Met', 'Breached')), 0), 2) AS overall_sla_compliance_pct,
       COUNT(*) FILTER (WHERE reassignment_events > 0) AS reassigned_tickets,
       SUM(reassignment_events) AS reassignment_events,
       COUNT(*) FILTER (WHERE reopen_count = 1) AS reopened_tickets,
       COUNT(csat_score) AS rated_tickets,
       ROUND(AVG(csat_score)::numeric, 2) AS average_csat,
       ROUND(100.0 * COUNT(csat_score) / NULLIF(COUNT(resolved_at), 0), 2) AS feedback_coverage_pct
FROM ticket_grain
GROUP BY team_name
ORDER BY team_name;
