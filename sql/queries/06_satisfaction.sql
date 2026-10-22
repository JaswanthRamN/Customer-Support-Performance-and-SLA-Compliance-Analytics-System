-- Missing feedback is an absent row, never a zero score.
-- Coverage uses all finally resolved tickets as its denominator.
WITH summary AS (
    SELECT CASE WHEN GROUPING(t.priority) = 1 THEN 'All' ELSE t.priority END AS priority,
           COUNT(*) FILTER (WHERE t.resolved_at IS NOT NULL) AS resolved_tickets,
           COUNT(f.csat_score) AS rated_tickets,
           COUNT(*) FILTER (WHERE f.csat_score >= 4) AS positive_ratings,
           AVG(f.csat_score) AS average_csat,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.csat_score) AS median_csat
    FROM support_analytics.tickets t
    LEFT JOIN support_analytics.customer_feedback f ON f.ticket_id = t.ticket_id
    GROUP BY ROLLUP(t.priority)
)
SELECT priority, resolved_tickets, rated_tickets,
       resolved_tickets - rated_tickets AS unrated_resolved_tickets,
       ROUND(average_csat::numeric, 2) AS average_csat,
       ROUND(median_csat::numeric, 2) AS median_csat,
       ROUND(100.0 * positive_ratings / NULLIF(rated_tickets, 0), 2) AS positive_csat_pct,
       ROUND(100.0 * rated_tickets / NULLIF(resolved_tickets, 0), 2) AS feedback_coverage_pct
FROM summary
ORDER BY CASE WHEN priority = 'All' THEN 0 ELSE 1 END, priority;
