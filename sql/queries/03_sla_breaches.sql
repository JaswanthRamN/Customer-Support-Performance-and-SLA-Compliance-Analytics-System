-- Pending is reported but excluded from the compliance denominator.
-- Overdue unfinished tickets already have Breached status in the snapshot.
WITH counts AS (
    SELECT CASE WHEN GROUPING(priority) = 1 THEN 'All' ELSE priority END AS priority,
           COUNT(*) AS tickets,
           COUNT(*) FILTER (WHERE response_sla_status = 'Met') AS response_met,
           COUNT(*) FILTER (WHERE response_sla_status = 'Breached') AS response_breached,
           COUNT(*) FILTER (WHERE response_sla_status = 'Pending') AS response_pending,
           COUNT(*) FILTER (WHERE resolution_sla_status = 'Met') AS resolution_met,
           COUNT(*) FILTER (WHERE resolution_sla_status = 'Breached') AS resolution_breached,
           COUNT(*) FILTER (WHERE resolution_sla_status = 'Pending') AS resolution_pending,
           COUNT(*) FILTER (WHERE overall_sla_status = 'Met') AS overall_met,
           COUNT(*) FILTER (WHERE overall_sla_status = 'Breached') AS overall_breached,
           COUNT(*) FILTER (WHERE overall_sla_status = 'Pending') AS overall_pending
    FROM support_analytics.tickets
    GROUP BY ROLLUP(priority)
)
SELECT *,
       ROUND(100.0 * response_met / NULLIF(response_met + response_breached, 0), 2) AS response_compliance_pct,
       ROUND(100.0 * resolution_met / NULLIF(resolution_met + resolution_breached, 0), 2) AS resolution_compliance_pct,
       ROUND(100.0 * overall_met / NULLIF(overall_met + overall_breached, 0), 2) AS overall_compliance_pct
FROM counts
ORDER BY CASE WHEN priority = 'All' THEN 0 ELSE 1 END, priority;
