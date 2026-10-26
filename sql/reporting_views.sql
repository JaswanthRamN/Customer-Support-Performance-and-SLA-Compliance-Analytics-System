-- Reusable reporting layer for the fixed synthetic-data snapshot.
-- All ticket KPI views derive from vw_ticket_metrics, which has exactly one row
-- per ticket. Never sum across dimension_type values: each ticket is represented
-- once in each of Overall, Priority, Current Team, and Current Agent.

CREATE OR REPLACE VIEW support_analytics.vw_reporting_context AS
SELECT TIMESTAMPTZ '2026-07-01 00:00:00+00' AS analysis_as_of,
       'Fixed synthetic-data snapshot; current backlog, not historical backlog'::text AS context_note;

CREATE OR REPLACE VIEW support_analytics.vw_ticket_metrics AS
WITH assignment_summary AS (
    SELECT ticket_id,
           COUNT(*) AS assignment_count,
           COUNT(*) FILTER (WHERE assignment_reason = 'Reassignment') AS reassignment_events,
           COUNT(*) FILTER (WHERE assignment_reason = 'Reopened') AS reopen_handoffs
    FROM support_analytics.assignment_history
    GROUP BY ticket_id
),
initial_owner AS (
    SELECT DISTINCT ON (ticket_id)
           ticket_id, agent_id AS initial_agent_id, team_id AS initial_team_id
    FROM support_analytics.assignment_history
    ORDER BY ticket_id, assigned_at, assignment_id
)
SELECT t.ticket_id, t.customer_id, t.priority, t.category, t.channel, t.status,
       t.created_at, t.first_response_at, t.resolved_at,
       t.current_team_id, current_team.team_name AS current_team_name,
       t.current_agent_id, current_agent.agent_label AS current_agent_label,
       io.initial_team_id, initial_team.team_name AS initial_team_name,
       io.initial_agent_id, initial_agent.agent_label AS initial_agent_label,
       EXTRACT(EPOCH FROM (t.first_response_at - t.created_at)) / 3600.0 AS response_hours,
       EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 3600.0 AS resolution_hours,
       CASE WHEN t.resolved_at IS NULL
            THEN EXTRACT(EPOCH FROM (ctx.analysis_as_of - t.created_at)) / 3600.0 END AS unresolved_age_hours,
       t.response_sla_status, t.resolution_sla_status, t.overall_sla_status,
       t.response_deadline, t.resolution_deadline,
       (t.resolved_at IS NULL) AS is_current_backlog,
       (t.resolved_at IS NULL AND t.resolution_sla_status = 'Breached') AS is_overdue,
       t.reopen_count, (t.reopen_count > 0) AS is_reopened,
       COALESCE(a.assignment_count, 0) AS assignment_count,
       COALESCE(a.reassignment_events, 0) AS reassignment_events,
       (COALESCE(a.reassignment_events, 0) > 0) AS is_reassigned,
       COALESCE(a.reopen_handoffs, 0) AS reopen_handoffs,
       f.csat_score, f.submitted_at AS feedback_submitted_at,
       ctx.analysis_as_of
FROM support_analytics.tickets t
CROSS JOIN support_analytics.vw_reporting_context ctx
JOIN support_analytics.teams current_team ON current_team.team_id = t.current_team_id
JOIN support_analytics.agents current_agent ON current_agent.agent_id = t.current_agent_id
JOIN initial_owner io ON io.ticket_id = t.ticket_id
JOIN support_analytics.teams initial_team ON initial_team.team_id = io.initial_team_id
JOIN support_analytics.agents initial_agent ON initial_agent.agent_id = io.initial_agent_id
LEFT JOIN assignment_summary a ON a.ticket_id = t.ticket_id
LEFT JOIN support_analytics.customer_feedback f ON f.ticket_id = t.ticket_id;

CREATE OR REPLACE VIEW support_analytics.vw_reporting_dimensions AS
SELECT 'Overall'::text AS dimension_type, 'ALL'::text AS dimension_id,
       'All tickets'::text AS dimension_name, m.*
FROM support_analytics.vw_ticket_metrics m
UNION ALL
SELECT 'Priority', priority, priority, m.*
FROM support_analytics.vw_ticket_metrics m
UNION ALL
SELECT 'Current Team', current_team_id, current_team_name, m.*
FROM support_analytics.vw_ticket_metrics m
UNION ALL
SELECT 'Current Agent', current_agent_id, current_agent_label, m.*
FROM support_analytics.vw_ticket_metrics m;

CREATE OR REPLACE VIEW support_analytics.vw_sla_compliance AS
SELECT dimension_type, dimension_id, dimension_name,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE response_sla_status = 'Met') AS response_met,
       COUNT(*) FILTER (WHERE response_sla_status = 'Breached') AS response_breached,
       COUNT(*) FILTER (WHERE response_sla_status = 'Pending') AS response_pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE response_sla_status = 'Met') /
             NULLIF(COUNT(*) FILTER (WHERE response_sla_status IN ('Met', 'Breached')), 0), 2)
           AS response_compliance_pct,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Met') AS resolution_met,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Breached') AS resolution_breached,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Pending') AS resolution_pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE resolution_sla_status = 'Met') /
             NULLIF(COUNT(*) FILTER (WHERE resolution_sla_status IN ('Met', 'Breached')), 0), 2)
           AS resolution_compliance_pct,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Met') AS overall_met,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Breached') AS overall_breached,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Pending') AS overall_pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE overall_sla_status = 'Met') /
             NULLIF(COUNT(*) FILTER (WHERE overall_sla_status IN ('Met', 'Breached')), 0), 2)
           AS overall_compliance_pct
FROM support_analytics.vw_reporting_dimensions
GROUP BY dimension_type, dimension_id, dimension_name;

CREATE OR REPLACE VIEW support_analytics.vw_service_times AS
SELECT dimension_type, dimension_id, dimension_name,
       COUNT(*) AS tickets,
       COUNT(response_hours) AS answered_tickets,
       COUNT(*) - COUNT(response_hours) AS unanswered_tickets,
       ROUND(AVG(response_hours)::numeric, 2) AS average_response_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_hours)::numeric, 2)
           AS median_response_hours,
       COUNT(resolution_hours) AS resolved_tickets,
       COUNT(*) - COUNT(resolution_hours) AS unresolved_tickets,
       ROUND(AVG(resolution_hours)::numeric, 2) AS average_resolution_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 2)
           AS median_resolution_hours
FROM support_analytics.vw_reporting_dimensions
GROUP BY dimension_type, dimension_id, dimension_name;

CREATE OR REPLACE VIEW support_analytics.vw_backlog_aging AS
SELECT dimension_type, dimension_id, dimension_name,
       CASE WHEN unresolved_age_hours < 24 THEN 'Under 24h'
            WHEN unresolved_age_hours < 48 THEN '24–<48h'
            WHEN unresolved_age_hours < 72 THEN '48–<72h'
            ELSE '72h+' END AS age_bucket,
       COUNT(*) AS backlog_tickets,
       COUNT(*) FILTER (WHERE is_overdue) AS overdue_tickets,
       ROUND(AVG(unresolved_age_hours)::numeric, 2) AS average_age_hours,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY unresolved_age_hours)::numeric, 2)
           AS median_age_hours,
       MAX(analysis_as_of) AS analysis_as_of
FROM support_analytics.vw_reporting_dimensions
WHERE is_current_backlog
GROUP BY dimension_type, dimension_id, dimension_name,
         CASE WHEN unresolved_age_hours < 24 THEN 'Under 24h'
              WHEN unresolved_age_hours < 48 THEN '24–<48h'
              WHEN unresolved_age_hours < 72 THEN '48–<72h'
              ELSE '72h+' END;

CREATE OR REPLACE VIEW support_analytics.vw_reassignment_rates AS
SELECT dimension_type, dimension_id, dimension_name,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE is_reassigned) AS reassigned_tickets,
       SUM(reassignment_events) AS reassignment_events,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_reassigned) / NULLIF(COUNT(*), 0), 2)
           AS reassigned_ticket_pct
FROM support_analytics.vw_reporting_dimensions
GROUP BY dimension_type, dimension_id, dimension_name;

CREATE OR REPLACE VIEW support_analytics.vw_reopened_rates AS
SELECT dimension_type, dimension_id, dimension_name,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE is_reopened) AS reopened_tickets,
       COUNT(*) FILTER (WHERE is_reopened AND is_current_backlog) AS reopened_unresolved_tickets,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_reopened) / NULLIF(COUNT(*), 0), 2)
           AS reopened_ticket_pct
FROM support_analytics.vw_reporting_dimensions
GROUP BY dimension_type, dimension_id, dimension_name;

CREATE OR REPLACE VIEW support_analytics.vw_satisfaction AS
SELECT dimension_type, dimension_id, dimension_name,
       COUNT(resolved_at) AS resolved_tickets,
       COUNT(csat_score) AS rated_tickets,
       COUNT(*) FILTER (WHERE csat_score >= 4) AS positive_ratings,
       ROUND(AVG(csat_score)::numeric, 2) AS average_csat,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY csat_score)::numeric, 2) AS median_csat,
       ROUND(100.0 * COUNT(*) FILTER (WHERE csat_score >= 4) /
             NULLIF(COUNT(csat_score), 0), 2) AS positive_csat_pct,
       ROUND(100.0 * COUNT(csat_score) / NULLIF(COUNT(resolved_at), 0), 2)
           AS feedback_coverage_pct
FROM support_analytics.vw_reporting_dimensions
GROUP BY dimension_type, dimension_id, dimension_name;

CREATE OR REPLACE VIEW support_analytics.vw_overdue_tickets AS
SELECT ticket_id, priority, category, channel, status,
       created_at, resolution_deadline, unresolved_age_hours,
       current_team_id, current_team_name, current_agent_id, current_agent_label,
       initial_team_id, initial_team_name, initial_agent_id, initial_agent_label,
       reassignment_events, is_reopened, analysis_as_of
FROM support_analytics.vw_ticket_metrics
WHERE is_overdue;

-- Assignment-grain history. Rows can exceed tickets and must not be counted as
-- ticket volume. Recorded intervals show ownership records, not active effort.
CREATE OR REPLACE VIEW support_analytics.vw_historical_assignment_activity AS
SELECT h.assignment_id, h.ticket_id, t.priority,
       h.assigned_at, h.unassigned_at, h.assignment_reason,
       h.team_id AS historical_team_id, tm.team_name AS historical_team_name,
       h.agent_id AS historical_agent_id, a.agent_label AS historical_agent_label,
       EXTRACT(EPOCH FROM (COALESCE(h.unassigned_at, ctx.analysis_as_of) - h.assigned_at)) / 3600.0
           AS recorded_interval_hours,
       (h.unassigned_at IS NULL) AS is_current_assignment,
       ctx.analysis_as_of
FROM support_analytics.assignment_history h
JOIN support_analytics.tickets t ON t.ticket_id = h.ticket_id
JOIN support_analytics.teams tm ON tm.team_id = h.team_id
JOIN support_analytics.agents a ON a.agent_id = h.agent_id
CROSS JOIN support_analytics.vw_reporting_context ctx;
