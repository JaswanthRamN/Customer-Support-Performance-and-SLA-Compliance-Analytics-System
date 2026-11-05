"""Static, parameterized SQL for the analytics endpoints."""

FILTERS = """
    (%(priority)s::text IS NULL OR priority = %(priority)s::text)
    AND (%(team_id)s::text IS NULL OR current_team_id = %(team_id)s::text)
    AND (%(created_from)s::date IS NULL OR created_at >= %(created_from)s::date)
    AND (%(created_to)s::date IS NULL OR created_at < %(created_to)s::date + INTERVAL '1 day')
"""

OVERVIEW = f"""/* overview */
SELECT COUNT(*) AS total_tickets,
       COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) AS resolved_tickets,
       COUNT(*) FILTER (WHERE is_current_backlog) AS unresolved_tickets,
       COUNT(*) FILTER (WHERE is_overdue) AS overdue_tickets,
       COUNT(*) FILTER (WHERE is_reopened) AS reopened_tickets,
       COUNT(csat_score) AS rated_tickets,
       ROUND(AVG(csat_score)::numeric, 2) AS average_csat,
       MAX(analysis_as_of) AS analysis_as_of
FROM support_analytics.vw_ticket_metrics
WHERE {FILTERS}
"""

GROUPS = {
    "overall": ("'ALL'", "'All tickets'"),
    "priority": ("priority", "priority"),
    "team": ("current_team_id", "current_team_name"),
}


def sla_query(group_by: str) -> str:
    dimension_id, dimension_name = GROUPS[group_by]
    return f"""/* sla */
SELECT {dimension_id} AS dimension_id, {dimension_name} AS dimension_name,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE response_sla_status = 'Met') AS response_met,
       COUNT(*) FILTER (WHERE response_sla_status = 'Breached') AS response_breached,
       COUNT(*) FILTER (WHERE response_sla_status = 'Pending') AS response_pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE response_sla_status = 'Met') /
           NULLIF(COUNT(*) FILTER (WHERE response_sla_status IN ('Met','Breached')), 0), 2)
           AS response_compliance_pct,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Met') AS resolution_met,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Breached') AS resolution_breached,
       COUNT(*) FILTER (WHERE resolution_sla_status = 'Pending') AS resolution_pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE resolution_sla_status = 'Met') /
           NULLIF(COUNT(*) FILTER (WHERE resolution_sla_status IN ('Met','Breached')), 0), 2)
           AS resolution_compliance_pct,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Met') AS overall_met,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Breached') AS overall_breached,
       COUNT(*) FILTER (WHERE overall_sla_status = 'Pending') AS overall_pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE overall_sla_status = 'Met') /
           NULLIF(COUNT(*) FILTER (WHERE overall_sla_status IN ('Met','Breached')), 0), 2)
           AS overall_compliance_pct
FROM support_analytics.vw_ticket_metrics
WHERE {FILTERS}
GROUP BY 1, 2 ORDER BY 2 LIMIT %(limit)s OFFSET %(offset)s
"""

TEAM_PERFORMANCE = f"""/* teams */
SELECT current_team_id AS team_id, current_team_name AS team_name,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE is_current_backlog) AS unresolved_tickets,
       COUNT(*) FILTER (WHERE is_overdue) AS overdue_tickets,
       COUNT(response_hours) AS answered_tickets,
       ROUND(AVG(response_hours)::numeric, 2) AS average_response_hours,
       COUNT(resolution_hours) AS resolved_tickets,
       ROUND(AVG(resolution_hours)::numeric, 2) AS average_resolution_hours,
       ROUND(100.0 * COUNT(*) FILTER (WHERE response_sla_status = 'Met') /
           NULLIF(COUNT(*) FILTER (WHERE response_sla_status IN ('Met','Breached')), 0), 2)
           AS response_compliance_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE resolution_sla_status = 'Met') /
           NULLIF(COUNT(*) FILTER (WHERE resolution_sla_status IN ('Met','Breached')), 0), 2)
           AS resolution_compliance_pct,
       COUNT(*) FILTER (WHERE is_reassigned) AS reassigned_tickets,
       COUNT(*) FILTER (WHERE is_reopened) AS reopened_tickets,
       COUNT(csat_score) AS rated_tickets,
       ROUND(AVG(csat_score)::numeric, 2) AS average_csat
FROM support_analytics.vw_ticket_metrics
WHERE {FILTERS}
GROUP BY current_team_id, current_team_name
ORDER BY current_team_name LIMIT %(limit)s OFFSET %(offset)s
"""


def response_times_query(group_by: str) -> str:
    dimension_id, dimension_name = GROUPS[group_by]
    return f"""/* response-times */
SELECT {dimension_id} AS dimension_id, {dimension_name} AS dimension_name,
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
FROM support_analytics.vw_ticket_metrics
WHERE {FILTERS}
GROUP BY 1, 2 ORDER BY 2 LIMIT %(limit)s OFFSET %(offset)s
"""

BACKLOG_SUMMARY = f"""/* backlog-summary */
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE is_overdue) AS overdue
FROM support_analytics.vw_ticket_metrics
WHERE is_current_backlog AND {FILTERS}
"""

BACKLOG_ITEMS = f"""/* backlog-items */
SELECT ticket_id, priority, category, channel, status, created_at,
       resolution_deadline, unresolved_age_hours, current_team_id,
       current_team_name, current_agent_id, current_agent_label, is_overdue
FROM support_analytics.vw_ticket_metrics
WHERE is_current_backlog AND {FILTERS}
ORDER BY is_overdue DESC, unresolved_age_hours DESC, ticket_id
LIMIT %(limit)s OFFSET %(offset)s
"""
