-- Means and medians exclude missing events; sample sizes show that exclusion.
-- Resolution is final resolution after any reopen, measured from creation.
WITH durations AS (
    SELECT priority,
           EXTRACT(EPOCH FROM (first_response_at - created_at)) / 3600.0 AS response_hours,
           EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0 AS resolution_hours
    FROM support_analytics.tickets
)
SELECT CASE WHEN GROUPING(priority) = 1 THEN 'All' ELSE priority END AS priority,
       COUNT(*) AS ticket_count,
       COUNT(response_hours) AS answered_count,
       COUNT(*) - COUNT(response_hours) AS unanswered_count,
       ROUND(AVG(response_hours)::numeric, 2) AS response_mean_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_hours)::numeric, 2) AS response_median_hours,
       COUNT(resolution_hours) AS resolved_count,
       COUNT(*) - COUNT(resolution_hours) AS unresolved_count,
       ROUND(AVG(resolution_hours)::numeric, 2) AS resolution_mean_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 2) AS resolution_median_hours
FROM durations
GROUP BY ROLLUP(priority)
ORDER BY GROUPING(priority) DESC, priority;
