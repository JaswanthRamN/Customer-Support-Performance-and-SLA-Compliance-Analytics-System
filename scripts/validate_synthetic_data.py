"""Validate CSV schemas, relationships, event ordering, ownership, and SLA flags."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.generate_synthetic_data import DEFAULT_OUTPUT, TABLES
from scripts.sla import POLICIES

SCHEMAS = {
    "customers": "customer_id customer_label segment region joined_at",
    "teams": "team_id team_name specialization",
    "agents": "agent_id agent_label team_id hired_at experience_level",
    "tickets": "ticket_id customer_id priority category channel status created_at first_response_at initial_resolved_at reopened_at reopen_count resolved_at closed_at current_agent_id current_team_id response_target_minutes resolution_target_minutes response_deadline resolution_deadline response_sla_status resolution_sla_status overall_sla_status",
    "assignment_history": "assignment_id ticket_id agent_id team_id assigned_at unassigned_at assignment_reason",
    "customer_feedback": "feedback_id ticket_id customer_id submitted_at csat_score",
}
OPTIONAL = {"first_response_at", "initial_resolved_at", "reopened_at", "resolved_at", "closed_at", "unassigned_at"}


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def load_data(directory):
    """Read persisted CSVs without silently accepting invalid timestamps."""
    data = {}
    for name in TABLES:
        frame = pd.read_csv(Path(directory) / f"{name}.csv")
        for column in frame.columns:
            if column.endswith("_at") or column.endswith("_deadline"):
                present = frame[column].dropna().astype(str)
                require(present.str.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z").all(),
                        f"{name}.{column}: expected explicit UTC timestamps")
                frame[column] = pd.to_datetime(frame[column], utc=True, errors="raise")
        data[name] = frame
    return data


def validate_data(data, snapshot):
    """Raise ValueError on first defect; return descriptive groups that passed."""
    snapshot = pd.Timestamp(snapshot)
    require(snapshot.tzinfo is not None, "Snapshot must have a timezone")
    checks = []
    require(set(data) == set(TABLES), "Expected exactly six tables")
    for name, frame in data.items():
        require(list(frame.columns) == SCHEMAS[name].split(), f"{name}: schema mismatch")
        primary_key = frame.columns[0]
        require(frame[primary_key].notna().all() and frame[primary_key].is_unique, f"{name}: invalid primary key")
        for column in frame.columns:
            if column not in OPTIONAL:
                require(frame[column].notna().all(), f"{name}.{column}: unexpected null")
            if pd.api.types.is_string_dtype(frame[column]):
                require(frame[column].dropna().str.strip().ne("").all(), f"{name}.{column}: blank value")
            if column.endswith("_at") or column.endswith("_deadline"):
                require(isinstance(frame[column].dtype, pd.DatetimeTZDtype), f"{name}.{column}: timezone required")
                # Deadlines can legitimately fall after the snapshot.
                if not column.endswith("_deadline"):
                    require(frame[column].dropna().le(snapshot).all(), f"{name}.{column}: future event")
    checks.append("Schemas, unique primary keys, required fields, UTC timestamps, snapshot bounds")
    customers, teams, agents, tickets, history, feedback = [data[name] for name in TABLES]
    require(len(tickets) > 0, "Tickets must not be empty")
    foreign_keys = [
        (agents.team_id, teams.team_id), (tickets.customer_id, customers.customer_id),
        (tickets.current_agent_id, agents.agent_id), (tickets.current_team_id, teams.team_id),
        (history.ticket_id, tickets.ticket_id), (history.agent_id, agents.agent_id),
        (history.team_id, teams.team_id), (feedback.ticket_id, tickets.ticket_id),
        (feedback.customer_id, customers.customer_id),
    ]
    for source, target in foreign_keys:
        require(source.isin(target).all(), f"Foreign key failure: {source.name}")
    checks.append("All foreign keys resolve")

    allowed = {
        ("customers", "segment"): ["Individual", "Small Business", "Enterprise"],
        ("customers", "region"): ["Region A", "Region B", "Region C", "Region D"],
        ("agents", "experience_level"): ["Junior", "Intermediate", "Senior"],
        ("tickets", "priority"): list(POLICIES),
        ("tickets", "category"): ["Account", "Technical", "Billing", "General"],
        ("tickets", "channel"): ["Email", "Chat", "Phone", "Web"],
        ("tickets", "status"): ["Open", "In Progress", "Pending", "Resolved", "Closed"],
        ("assignment_history", "assignment_reason"): ["Initial", "Reassignment", "Reopened"],
    }
    for (table, column), values in allowed.items():
        require(data[table][column].isin(values).all(), f"{table}.{column}: invalid category")
    require(customers.customer_label.str.fullmatch(r"Synthetic Customer \d+").all(), "Unsafe customer label")
    require(agents.agent_label.str.fullmatch(r"Synthetic Agent \d+").all(), "Unsafe agent label")
    checks.append("Controlled categories and synthetic-only labels")

    joined = tickets.customer_id.map(customers.set_index("customer_id").joined_at)
    require(joined.le(tickets.created_at).all(), "Customer joined after ticket creation")
    completed = tickets.status.isin(["Resolved", "Closed"])
    require(completed.eq(tickets.resolved_at.notna()).all(), "Status/resolution mismatch")
    require(tickets.status.eq("Closed").eq(tickets.closed_at.notna()).all(), "Status/closure mismatch")
    require(tickets.status.eq("Open").eq(tickets.first_response_at.isna()).all(), "Open/response mismatch")
    require((~completed | tickets.first_response_at.notna()).all(), "Completed ticket without response")
    for column in ["first_response_at", "initial_resolved_at", "reopened_at", "resolved_at", "closed_at"]:
        require((tickets[column].isna() | tickets[column].ge(tickets.created_at)).all(), f"{column} precedes creation")
    initial = tickets.initial_resolved_at.notna()
    require((~initial | tickets.first_response_at.le(tickets.initial_resolved_at)).all(), "Resolution precedes response")
    reopened = tickets.reopened_at.notna()
    require(tickets.reopen_count.isin([0, 1]).all() and tickets.reopen_count.eq(reopened.astype(int)).all(), "Invalid reopen count")
    require((~reopened | (initial & tickets.reopened_at.gt(tickets.initial_resolved_at))).all(), "Invalid reopen ordering")
    require((~completed | initial).all(), "Completed ticket without initial resolution")
    require((~(reopened & completed) | tickets.resolved_at.gt(tickets.reopened_at)).all(), "Final resolution precedes reopen")
    require((reopened | tickets.resolved_at.eq(tickets.initial_resolved_at)
             | (tickets.resolved_at.isna() & tickets.initial_resolved_at.isna())).all(), "Non-reopened resolution mismatch")
    require((tickets.closed_at.isna() | tickets.closed_at.ge(tickets.resolved_at)).all(), "Closure precedes resolution")
    checks.append("Customer chronology, lifecycle ordering, reopened and unresolved semantics")

    agent_teams = agents.set_index("agent_id").team_id
    require(tickets.current_agent_id.map(agent_teams).eq(tickets.current_team_id).all(), "Current agent/team mismatch")
    require(history.agent_id.map(agent_teams).eq(history.team_id).all(), "Assignment agent/team mismatch")
    hired = history.agent_id.map(agents.set_index("agent_id").hired_at)
    require(hired.le(history.assigned_at).all(), "Assignment before agent hire")
    require(set(history.ticket_id) == set(tickets.ticket_id), "Missing ticket assignment history")
    ticket_lookup = tickets.set_index("ticket_id")
    ordered = history.sort_values(["ticket_id", "assigned_at"])
    groups = ordered.groupby("ticket_id", sort=False)
    first = groups.head(1).set_index("ticket_id")
    last = groups.tail(1).set_index("ticket_id")
    require(first.assigned_at.eq(ticket_lookup.created_at.reindex(first.index)).all(), "Initial assignment must start at creation")
    require(first.assignment_reason.eq("Initial").all(), "Initial reason missing")
    require(groups.assignment_reason.apply(lambda x: x.eq("Initial").sum()).eq(1).all(), "Repeated initial assignment")
    require(last.unassigned_at.isna().all(), "Final assignment must be current")
    require(last.agent_id.eq(ticket_lookup.current_agent_id.reindex(last.index)).all(), "Current owner differs from history")
    next_start = groups.assigned_at.shift(-1)
    not_last = next_start.notna()
    require(ordered.loc[not_last, "unassigned_at"].eq(next_start[not_last]).all(), "Assignment gap or overlap")
    require((ordered.unassigned_at.isna() | ordered.unassigned_at.gt(ordered.assigned_at)).all(), "Invalid assignment duration")
    previous_agent = groups.agent_id.shift(1)
    require((previous_agent.isna() | ordered.agent_id.ne(previous_agent)).all(), "Reassignment did not change agent")
    terminal = ordered.ticket_id.map(ticket_lookup.resolved_at).fillna(snapshot)
    require(ordered.assigned_at.le(terminal).all(), "Assignment after final resolution")
    reopen_events = ordered[ordered.assignment_reason.eq("Reopened")].set_index("ticket_id")
    expected_reopens = tickets.loc[reopened].set_index("ticket_id").reopened_at
    require(reopen_events.index.is_unique and set(reopen_events.index) == set(expected_reopens.index), "Missing/extra reopen handoff")
    require(reopen_events.assigned_at.eq(expected_reopens.reindex(reopen_events.index)).all(), "Reopen handoff time mismatch")
    ordinary = ordered[ordered.assignment_reason.eq("Reassignment")]
    first_end = ordinary.ticket_id.map(ticket_lookup.initial_resolved_at).fillna(snapshot)
    require(ordinary.assigned_at.lt(first_end).all(), "Ordinary transfer after first resolution")
    checks.append("Contiguous ownership intervals, valid teams/hire dates, final owners and reopen handoffs")

    for event, prefix, policy_index in [("first_response_at", "response", 0), ("resolved_at", "resolution", 1)]:
        targets = tickets.priority.map({k: v[policy_index] for k, v in POLICIES.items()})
        require(tickets[f"{prefix}_target_minutes"].eq(targets).all(), f"{prefix}: policy mismatch")
        deadlines = tickets.created_at + pd.to_timedelta(targets, unit="m")
        require(tickets[f"{prefix}_deadline"].eq(deadlines).all(), f"{prefix}: deadline mismatch")
        expected = np.where(tickets[event].notna(), np.where(tickets[event].le(deadlines), "Met", "Breached"),
                            np.where(deadlines.lt(snapshot), "Breached", "Pending"))
        require(tickets[f"{prefix}_sla_status"].eq(expected).all(), f"{prefix}: incorrect SLA classification")
    either_breached = tickets.response_sla_status.eq("Breached") | tickets.resolution_sla_status.eq("Breached")
    both_met = tickets.response_sla_status.eq("Met") & tickets.resolution_sla_status.eq("Met")
    expected_overall = np.where(either_breached, "Breached", np.where(both_met, "Met", "Pending"))
    require(tickets.overall_sla_status.eq(expected_overall).all(), "Incorrect overall SLA")
    checks.append("Independent SLA target, deadline, and status reconciliation")

    require(feedback.ticket_id.is_unique, "Multiple feedback rows per ticket")
    require(feedback.customer_id.eq(feedback.ticket_id.map(ticket_lookup.customer_id)).all(), "Feedback customer mismatch")
    feedback_resolutions = feedback.ticket_id.map(ticket_lookup.resolved_at)
    require(feedback_resolutions.notna().all(), "Feedback on unresolved ticket")
    require(feedback.submitted_at.ge(feedback_resolutions).all(), "Feedback before final resolution")
    require(feedback.csat_score.isin([1, 2, 3, 4, 5]).all(), "Invalid CSAT rating")
    checks.append("Optional feedback uniqueness, customer ownership, rating bounds, and chronology")
    return checks


def validate_directory(directory):
    directory = Path(directory)
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    data = load_data(directory)
    checks = validate_data(data, metadata["analysis_as_of"])
    require(metadata["row_counts"] == {name: len(frame) for name, frame in data.items()}, "Metadata row counts mismatch")
    expected_hashes = {f"{name}.csv": hashlib.sha256((directory / f"{name}.csv").read_bytes()).hexdigest() for name in TABLES}
    require(metadata["csv_sha256"] == expected_hashes, "CSV checksum mismatch")
    return checks + ["Persisted CSV row counts and SHA-256 checksums match metadata"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    for check in validate_directory(args.input):
        print(f"PASS: {check}")


if __name__ == "__main__":
    main()
