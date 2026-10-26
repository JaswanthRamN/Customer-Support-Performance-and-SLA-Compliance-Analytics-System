"""Build independent Python KPI baselines and optionally compare PostgreSQL views."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from psycopg.rows import dict_row

from scripts.eda import DEFAULT_INPUT, DEFAULT_QUALITY, load_cleaned, ratio
from scripts.generate_synthetic_data import ROOT
from scripts.load_postgres import db_config

DEFAULT_REPORT = ROOT / "reports" / "reporting_reconciliation.json"


def rounded(value):
    return None if value is None or pd.isna(value) else round(float(value), 2)


def build_python_baseline(data, snapshot):
    """Calculate reporting metrics directly from cleaned DataFrames."""
    tickets = data["tickets"].copy()
    history = data["assignment_history"]
    feedback = data["customer_feedback"][["ticket_id", "csat_score"]]
    teams = data["teams"][["team_id", "team_name"]]
    agents = data["agents"][["agent_id", "agent_label"]]

    handoffs = (history.assign(is_reassignment=history.assignment_reason.eq("Reassignment"))
                .groupby("ticket_id", as_index=True).is_reassignment.sum())
    tickets["reassignment_events"] = tickets.ticket_id.map(handoffs).fillna(0).astype(int)
    tickets = tickets.merge(feedback, on="ticket_id", how="left", validate="one_to_one")
    tickets = tickets.merge(teams, left_on="current_team_id", right_on="team_id",
                            how="left", validate="many_to_one")
    tickets = tickets.merge(agents, left_on="current_agent_id", right_on="agent_id",
                            how="left", validate="many_to_one")
    tickets["response_hours"] = (tickets.first_response_at - tickets.created_at).dt.total_seconds() / 3600
    tickets["resolution_hours"] = (tickets.resolved_at - tickets.created_at).dt.total_seconds() / 3600
    tickets["is_backlog"] = tickets.resolved_at.isna()
    tickets["is_overdue"] = tickets.is_backlog & tickets.resolution_sla_status.eq("Breached")
    tickets["unresolved_age_hours"] = np.where(
        tickets.is_backlog, (snapshot - tickets.created_at).dt.total_seconds() / 3600, np.nan)

    def status_counts(column):
        counts = tickets[column].value_counts()
        met, breached, pending = [int(counts.get(value, 0)) for value in ("Met", "Breached", "Pending")]
        return {"met": met, "breached": breached, "pending": pending,
                "compliance_pct": rounded(ratio(met, met + breached))}

    resolved = int(tickets.resolved_at.notna().sum())
    rated = int(tickets.csat_score.notna().sum())
    positive = int(tickets.csat_score.ge(4).sum())
    backlog = tickets.loc[tickets.is_backlog, "unresolved_age_hours"]
    baseline = {
        "analysis_as_of": snapshot.isoformat(),
        "ticket_grain": {
            "tickets": len(tickets),
            "assignment_rows": len(history),
            "ticket_ids_unique": bool(tickets.ticket_id.is_unique),
        },
        "sla": {name: status_counts(f"{name}_sla_status")
                for name in ("response", "resolution", "overall")},
        "service_times": {
            "answered_tickets": int(tickets.response_hours.notna().sum()),
            "average_response_hours": rounded(tickets.response_hours.mean()),
            "median_response_hours": rounded(tickets.response_hours.median()),
            "resolved_tickets": resolved,
            "average_resolution_hours": rounded(tickets.resolution_hours.mean()),
            "median_resolution_hours": rounded(tickets.resolution_hours.median()),
        },
        "backlog": {
            "backlog_tickets": int(tickets.is_backlog.sum()),
            "overdue_tickets": int(tickets.is_overdue.sum()),
            "average_age_hours": rounded(backlog.mean()),
            "median_age_hours": rounded(backlog.median()),
        },
        "reassignments": {
            "reassigned_tickets": int(tickets.reassignment_events.gt(0).sum()),
            "reassignment_events": int(tickets.reassignment_events.sum()),
            "reassigned_ticket_pct": rounded(ratio(int(tickets.reassignment_events.gt(0).sum()), len(tickets))),
        },
        "reopened": {
            "reopened_tickets": int(tickets.reopen_count.gt(0).sum()),
            "reopened_unresolved_tickets": int((tickets.reopen_count.gt(0) & tickets.is_backlog).sum()),
            "reopened_ticket_pct": rounded(ratio(int(tickets.reopen_count.gt(0).sum()), len(tickets))),
        },
        "satisfaction": {
            "resolved_tickets": resolved,
            "rated_tickets": rated,
            "positive_ratings": positive,
            "average_csat": rounded(tickets.csat_score.mean()),
            "median_csat": rounded(tickets.csat_score.median()),
            "positive_csat_pct": rounded(ratio(positive, rated)),
            "feedback_coverage_pct": rounded(ratio(rated, resolved)),
        },
        "dimension_ticket_counts": {
            "Priority": {str(k): int(v) for k, v in tickets.priority.value_counts().items()},
            "Current Team": {str(k): int(v) for k, v in tickets.groupby("current_team_id").size().items()},
            "Current Agent": {str(k): int(v) for k, v in tickets.groupby("current_agent_id").size().items()},
        },
    }
    return baseline


def database_results(connection):
    """Read the corresponding key values from installed reporting views."""
    result = {}
    views = {
        "sla": "SELECT * FROM support_analytics.vw_sla_compliance WHERE dimension_type = 'Overall'",
        "service_times": "SELECT * FROM support_analytics.vw_service_times WHERE dimension_type = 'Overall'",
        "reassignments": "SELECT * FROM support_analytics.vw_reassignment_rates WHERE dimension_type = 'Overall'",
        "reopened": "SELECT * FROM support_analytics.vw_reopened_rates WHERE dimension_type = 'Overall'",
        "satisfaction": "SELECT * FROM support_analytics.vw_satisfaction WHERE dimension_type = 'Overall'",
    }
    with connection.cursor(row_factory=dict_row) as cursor:
        for name, query in views.items():
            cursor.execute(query)
            result[name] = dict(cursor.fetchone())
        cursor.execute("""
            SELECT COUNT(*) AS backlog_tickets,
                   COUNT(*) FILTER (WHERE is_overdue) AS overdue_tickets,
                   ROUND(AVG(unresolved_age_hours)::numeric, 2) AS average_age_hours,
                   ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
                         (ORDER BY unresolved_age_hours)::numeric, 2) AS median_age_hours
            FROM support_analytics.vw_ticket_metrics WHERE is_current_backlog
        """)
        result["backlog"] = dict(cursor.fetchone())
        cursor.execute("""
            SELECT dimension_type, dimension_id, tickets
            FROM support_analytics.vw_sla_compliance
            WHERE dimension_type IN ('Priority', 'Current Team', 'Current Agent')
        """)
        counts = {name: {} for name in ("Priority", "Current Team", "Current Agent")}
        for row in cursor.fetchall():
            counts[row["dimension_type"]][row["dimension_id"]] = int(row["tickets"])
        result["dimension_ticket_counts"] = counts
    return result


def compare_key_results(expected, actual):
    """Return human-readable mismatches for the shared SQL/Python fields."""
    mappings = {
        "service_times": ("answered_tickets", "average_response_hours", "median_response_hours",
                          "resolved_tickets", "average_resolution_hours", "median_resolution_hours"),
        "backlog": ("backlog_tickets", "overdue_tickets", "average_age_hours", "median_age_hours"),
        "reassignments": ("reassigned_tickets", "reassignment_events", "reassigned_ticket_pct"),
        "reopened": ("reopened_tickets", "reopened_unresolved_tickets", "reopened_ticket_pct"),
        "satisfaction": ("resolved_tickets", "rated_tickets", "positive_ratings", "average_csat",
                         "median_csat", "positive_csat_pct", "feedback_coverage_pct"),
    }
    mismatches = []
    for section, fields in mappings.items():
        for field in fields:
            observed = actual[section][field]
            observed = float(observed) if observed is not None else None
            if observed != expected[section][field]:
                mismatches.append(f"{section}.{field}: Python={expected[section][field]!r}, SQL={observed!r}")
    for commitment in ("response", "resolution", "overall"):
        for field in ("met", "breached", "pending", "compliance_pct"):
            sql_field = f"{commitment}_{field}"
            observed = actual["sla"][sql_field]
            observed = float(observed) if observed is not None else None
            if observed != expected["sla"][commitment][field]:
                mismatches.append(
                    f"sla.{commitment}.{field}: Python={expected['sla'][commitment][field]!r}, SQL={observed!r}")
    if actual["dimension_ticket_counts"] != expected["dimension_ticket_counts"]:
        mismatches.append("dimension_ticket_counts differ between Python and SQL")
    return mismatches


def run(report_path=DEFAULT_REPORT, compare_database=False, connect=None):
    data, snapshot, _ = load_cleaned(DEFAULT_INPUT, DEFAULT_QUALITY)
    baseline = build_python_baseline(data, snapshot)
    report = {"python_baseline": baseline, "database_compared": False,
              "database_match": None, "mismatches": []}
    failure = None
    if compare_database:
        import psycopg
        connector = connect or psycopg.connect
        with connector(**db_config()) as connection:
            actual = database_results(connection)
        report["database_compared"] = True
        report["mismatches"] = compare_key_results(baseline, actual)
        report["database_match"] = not report["mismatches"]
        if report["mismatches"]:
            failure = "Reporting reconciliation failed: " + "; ".join(report["mismatches"])
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failure:
        raise ValueError(failure)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", action="store_true", help="compare Python baseline with loaded PostgreSQL views")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(args.report, args.database)
    print(json.dumps({"database_compared": report["database_compared"],
                      "database_match": report["database_match"],
                      "report": str(args.report)}, indent=2))


if __name__ == "__main__":
    main()
