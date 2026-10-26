-- Run via scripts/load_postgres.py, which supplies one analysis_as_of parameter.
-- Six row counts must equal the cleaned CSV counts; all anomaly counts must be 0.
WITH params AS (
    SELECT %s::timestamptz AS analysis_as_of
),
ordered_assignments AS (
    SELECT h.*,
           ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY assigned_at, assignment_id) AS step_number,
           LEAD(assigned_at) OVER (PARTITION BY ticket_id ORDER BY assigned_at, assignment_id) AS next_assigned_at,
           LAG(agent_id) OVER (PARTITION BY ticket_id ORDER BY assigned_at, assignment_id) AS previous_agent_id
    FROM support_analytics.assignment_history h
)
SELECT
    (SELECT COUNT(*) FROM support_analytics.customers) AS customers,
    (SELECT COUNT(*) FROM support_analytics.teams) AS teams,
    (SELECT COUNT(*) FROM support_analytics.agents) AS agents,
    (SELECT COUNT(*) FROM support_analytics.tickets) AS tickets,
    (SELECT COUNT(*) FROM support_analytics.assignment_history) AS assignment_history,
    (SELECT COUNT(*) FROM support_analytics.customer_feedback) AS customer_feedback,
    (SELECT ABS(COUNT(*) - (SELECT COUNT(*) FROM support_analytics.tickets)) +
            (COUNT(*) - COUNT(DISTINCT ticket_id))
     FROM support_analytics.vw_ticket_metrics) AS invalid_ticket_metrics_grain,
    (SELECT COUNT(*)
     FROM (VALUES ('Overall'), ('Priority'), ('Current Team'), ('Current Agent')) expected(dimension_type)
     LEFT JOIN (
         SELECT dimension_type, COUNT(*) AS rows_in_dimension
         FROM support_analytics.vw_reporting_dimensions
         GROUP BY dimension_type
     ) observed USING (dimension_type)
     WHERE COALESCE(observed.rows_in_dimension, 0) <>
           (SELECT COUNT(*) FROM support_analytics.tickets)
    ) AS invalid_reporting_dimension_counts,
    (SELECT COUNT(*) FROM (
         (SELECT priority, response_target_minutes, resolution_target_minutes
          FROM support_analytics.sla_policies
          EXCEPT VALUES ('Critical', 15, 240), ('High', 60, 480),
                        ('Medium', 240, 1440), ('Low', 480, 4320))
         UNION ALL
         (VALUES ('Critical', 15, 240), ('High', 60, 480),
                 ('Medium', 240, 1440), ('Low', 480, 4320)
          EXCEPT SELECT priority, response_target_minutes, resolution_target_minutes
                 FROM support_analytics.sla_policies)
     ) policy_difference) AS invalid_sla_policy,
    (SELECT COUNT(*) FROM support_analytics.tickets t
     JOIN support_analytics.customers c ON c.customer_id = t.customer_id
     WHERE c.joined_at > t.created_at) AS invalid_customer_chronology,
    (SELECT COUNT(*) FROM support_analytics.assignment_history h
     JOIN support_analytics.agents a ON a.agent_id = h.agent_id
     WHERE a.hired_at > h.assigned_at) AS invalid_agent_chronology,
    (SELECT COUNT(*) FROM support_analytics.customer_feedback f
     JOIN support_analytics.tickets t ON t.ticket_id = f.ticket_id
     WHERE t.resolved_at IS NULL OR f.submitted_at < t.resolved_at) AS invalid_feedback_chronology,
    (SELECT COUNT(*) FROM support_analytics.tickets t
     WHERE NOT EXISTS (SELECT 1 FROM support_analytics.assignment_history h
                       WHERE h.ticket_id = t.ticket_id)) AS missing_assignment_history,
    (SELECT COUNT(*) FROM ordered_assignments o
     JOIN support_analytics.tickets t ON t.ticket_id = o.ticket_id
     CROSS JOIN params p
     WHERE (o.step_number = 1 AND (o.assigned_at <> t.created_at OR o.assignment_reason <> 'Initial'))
        OR (o.step_number > 1 AND o.assignment_reason = 'Initial')
        OR (o.next_assigned_at IS NOT NULL AND o.unassigned_at IS DISTINCT FROM o.next_assigned_at)
        OR (o.next_assigned_at IS NULL AND (o.unassigned_at IS NOT NULL OR o.agent_id <> t.current_agent_id))
        OR (o.previous_agent_id IS NOT NULL AND o.previous_agent_id = o.agent_id)
        OR o.assigned_at > COALESCE(t.resolved_at, p.analysis_as_of)
        OR (o.assignment_reason = 'Reopened' AND o.assigned_at IS DISTINCT FROM t.reopened_at)
        OR (o.assignment_reason = 'Reassignment' AND o.assigned_at >= COALESCE(t.initial_resolved_at, p.analysis_as_of))
    ) AS invalid_assignment_history,
    (SELECT COUNT(*) FROM support_analytics.tickets t
     WHERE (SELECT COUNT(*) FROM support_analytics.assignment_history h
            WHERE h.ticket_id = t.ticket_id AND h.assignment_reason = 'Reopened') <> t.reopen_count
    ) AS invalid_reopen_handoffs,
    (SELECT COUNT(*) FROM support_analytics.tickets t CROSS JOIN params p
     WHERE t.response_sla_status <> CASE
         WHEN t.first_response_at IS NOT NULL THEN
             CASE WHEN t.first_response_at <= t.response_deadline THEN 'Met' ELSE 'Breached' END
         WHEN p.analysis_as_of > t.response_deadline THEN 'Breached' ELSE 'Pending' END
        OR t.resolution_sla_status <> CASE
         WHEN t.resolved_at IS NOT NULL THEN
             CASE WHEN t.resolved_at <= t.resolution_deadline THEN 'Met' ELSE 'Breached' END
         WHEN p.analysis_as_of > t.resolution_deadline THEN 'Breached' ELSE 'Pending' END
    ) AS invalid_sla_classifications;
