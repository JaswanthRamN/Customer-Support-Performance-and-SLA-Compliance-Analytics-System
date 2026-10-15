"""Generate a reproducible relational support dataset; no network or personal data."""

import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "sample" / "synthetic"
SNAPSHOT = pd.Timestamp("2026-07-01T00:00:00Z")
START = pd.Timestamp("2026-01-01T00:00:00Z")
POLICIES = {"Critical": (1, 8), "High": (4, 24), "Medium": (8, 48), "Low": (24, 72)}
TABLES = ("customers", "teams", "agents", "tickets", "assignment_history", "customer_feedback")


def sla_status(event, deadline, snapshot):
    """An event at the deadline meets SLA; an absent event at it is pending."""
    if pd.notna(event):
        return "Met" if event <= deadline else "Breached"
    return "Breached" if snapshot > deadline else "Pending"


def overall_status(response, resolution):
    if "Breached" in (response, resolution):
        return "Breached"
    return "Met" if response == resolution == "Met" else "Pending"


def generate_data(ticket_count=10_000, seed=42):
    """Return six DataFrames. One local RNG makes calls independent of global state."""
    if ticket_count < 1:
        raise ValueError("ticket_count must be a positive integer")
    rng = np.random.default_rng(seed)
    teams = pd.DataFrame({
        "team_id": ["TM01", "TM02", "TM03"],
        "team_name": ["Tier 1 Support", "Technical Support", "Billing Support"],
        "specialization": ["Account and General", "Technical", "Billing"],
    })
    agents = pd.DataFrame({
        "agent_id": [f"AG{i:03d}" for i in range(1, 31)],
        "agent_label": [f"Synthetic Agent {i:03d}" for i in range(1, 31)],
        "team_id": np.repeat(teams.team_id.to_numpy(), 10),
        "hired_at": [START - pd.Timedelta(days=int(x)) for x in rng.integers(90, 900, 30)],
        "experience_level": rng.choice(["Junior", "Intermediate", "Senior"], 30, p=[.3, .45, .25]),
    })
    customer_count = max(1, ticket_count // 4)
    customers = pd.DataFrame({
        "customer_id": [f"CU{i:05d}" for i in range(1, customer_count + 1)],
        "customer_label": [f"Synthetic Customer {i:05d}" for i in range(1, customer_count + 1)],
        "segment": rng.choice(["Individual", "Small Business", "Enterprise"], customer_count, p=[.55, .3, .15]),
        "region": rng.choice(["Region A", "Region B", "Region C", "Region D"], customer_count),
        "joined_at": [START - pd.Timedelta(days=int(x)) for x in rng.integers(1, 730, customer_count)],
    })

    # More demand on weekdays, during UTC working hours, and later in the period.
    hours = pd.date_range(START, SNAPSHOT, freq="h", inclusive="left")
    weights = (np.where(hours.dayofweek < 5, 1.0, .45)
               * np.where((hours.hour >= 8) & (hours.hour < 19), 1.0, .3)
               * (1 + .08 * (hours.month.to_numpy() - 1)))
    chosen_hours = rng.choice(len(hours), ticket_count, p=weights / weights.sum())
    creation_times = hours[chosen_hours] + pd.to_timedelta(rng.integers(0, 3600, ticket_count), unit="s")
    creation_times = creation_times.sort_values()
    ticket_rows, assignment_rows, feedback_rows = [], [], []
    agent_team = agents.set_index("agent_id").team_id.to_dict()
    pools = {team: agents.loc[agents.team_id == team, "agent_id"].tolist() for team in teams.team_id}

    def delay(hours_value):
        return pd.Timedelta(seconds=max(1, int(hours_value * 3600)))

    for index, created in enumerate(creation_times, start=1):
        ticket_id = f"TK{index:06d}"
        customer = customers.iloc[int(rng.integers(customer_count))]
        category = str(rng.choice(["Account", "Technical", "Billing", "General"], p=[.25, .35, .25, .15]))
        priority = str(rng.choice(list(POLICIES), p=[.06, .22, .47, .25]))
        channel = str(rng.choice(["Email", "Chat", "Phone", "Web"], p=[.4, .25, .15, .2]))
        response_target, resolution_target = POLICIES[priority]
        complexity = {"Account": .85, "Technical": 1.45, "Billing": 1.1, "General": .7}[category]
        channel_factor = {"Email": 1.2, "Chat": .55, "Phone": .3, "Web": 1.05}[channel]
        segment_factor = .75 if customer.segment == "Enterprise" else 1.0
        response_delay = delay(response_target * rng.lognormal(-.7, .95) * channel_factor * segment_factor)
        resolution_delay = delay(resolution_target * rng.lognormal(-.45, .95) * complexity)
        response_candidate = created + response_delay
        # A small persistent queue creates old unanswered and unresolved cases.
        first_response = response_candidate if response_candidate <= SNAPSHOT and rng.random() >= .018 else pd.NaT
        initial_resolution = pd.NaT
        if pd.notna(first_response) and rng.random() >= .075:
            candidate = max(created + resolution_delay, first_response + delay(.1))
            if candidate <= SNAPSHOT:
                initial_resolution = candidate

        reopened = pd.NaT
        resolved = initial_resolution
        if pd.notna(initial_resolution) and rng.random() < .11:
            candidate = initial_resolution + delay(rng.uniform(2, 120))
            if candidate <= SNAPSHOT:
                reopened = candidate
                final_candidate = reopened + delay(rng.lognormal(2.4, 1) * complexity)
                resolved = final_candidate if final_candidate <= SNAPSHOT and rng.random() >= .16 else pd.NaT

        closed = pd.NaT
        if pd.notna(resolved):
            candidate = resolved + delay(rng.uniform(4, 72))
            if candidate <= SNAPSHOT:
                closed = candidate
            status = "Closed" if pd.notna(closed) else "Resolved"
        elif pd.isna(first_response):
            status = "Open"
        else:
            status = str(rng.choice(["In Progress", "Pending"], p=[.65, .35]))

        # Ownership persists after resolution. Transfers occur while work is active.
        initial_team = {"Account": "TM01", "General": "TM01", "Technical": "TM02", "Billing": "TM03"}[category]
        if rng.random() < .16:  # Deliberate initial routing variation.
            initial_team = str(rng.choice(teams.team_id))
        owner = str(rng.choice(pools[initial_team]))
        events = [(created, owner, "Initial")]
        active_end = initial_resolution if pd.notna(initial_resolution) else SNAPSHOT
        span_seconds = int((active_end - created).total_seconds())
        transfer_count = int(rng.choice([0, 1, 2], p=[.74, .21, .05]))
        if span_seconds > 3 and transfer_count:
            offsets = np.sort(rng.choice(np.arange(1, 1000), transfer_count, replace=False) / 1000)
            for offset in offsets:
                transfer_at = created + pd.Timedelta(seconds=max(1, int(span_seconds * offset)))
                if transfer_at <= events[-1][0] or transfer_at >= active_end:
                    continue
                owner = str(rng.choice(agents.loc[agents.agent_id != owner, "agent_id"]))
                events.append((transfer_at, owner, "Reassignment"))
        if pd.notna(reopened):
            owner = str(rng.choice(agents.loc[agents.agent_id != owner, "agent_id"]))
            events.append((reopened, owner, "Reopened"))
        for event_index, (assigned, agent_id, reason) in enumerate(events):
            assignment_rows.append({
                "assignment_id": f"AS{len(assignment_rows) + 1:07d}", "ticket_id": ticket_id,
                "agent_id": agent_id, "team_id": agent_team[agent_id],
                "assigned_at": assigned,
                "unassigned_at": events[event_index + 1][0] if event_index + 1 < len(events) else pd.NaT,
                "assignment_reason": reason,
            })

        response_deadline = created + pd.Timedelta(hours=response_target)
        resolution_deadline = created + pd.Timedelta(hours=resolution_target)
        response_sla = sla_status(first_response, response_deadline, SNAPSHOT)
        resolution_sla = sla_status(resolved, resolution_deadline, SNAPSHOT)
        ticket_rows.append({
            "ticket_id": ticket_id, "customer_id": customer.customer_id,
            "priority": priority, "category": category, "channel": channel, "status": status,
            "created_at": created, "first_response_at": first_response,
            "initial_resolved_at": initial_resolution, "reopened_at": reopened,
            "reopen_count": int(pd.notna(reopened)), "resolved_at": resolved, "closed_at": closed,
            "current_agent_id": events[-1][1], "current_team_id": agent_team[events[-1][1]],
            "response_target_hours": response_target, "resolution_target_hours": resolution_target,
            "response_deadline": response_deadline, "resolution_deadline": resolution_deadline,
            "response_sla_status": response_sla, "resolution_sla_status": resolution_sla,
            "overall_sla_status": overall_status(response_sla, resolution_sla),
        })
        if pd.notna(resolved) and rng.random() < .43:
            submitted = resolved + delay(rng.uniform(.5, 120))
            if submitted <= SNAPSHOT:
                score = int(np.clip(np.rint(rng.normal(4.3 - .8 * (resolution_sla == "Breached")
                                                     - .45 * pd.notna(reopened), .85)), 1, 5))
                feedback_rows.append({
                    "feedback_id": f"FB{len(feedback_rows) + 1:06d}", "ticket_id": ticket_id,
                    "customer_id": customer.customer_id, "submitted_at": submitted, "csat_score": score,
                })

    data = {
        "customers": customers, "teams": teams, "agents": agents,
        "tickets": pd.DataFrame(ticket_rows), "assignment_history": pd.DataFrame(assignment_rows),
        "customer_feedback": pd.DataFrame(feedback_rows, columns=["feedback_id", "ticket_id", "customer_id", "submitted_at", "csat_score"]),
    }
    # Even empty/all-null event columns need an explicit UTC dtype for small runs.
    for frame in data.values():
        for column in frame.columns:
            if column.endswith("_at") or column.endswith("_deadline"):
                frame[column] = pd.to_datetime(frame[column], utc=True)
    return data


def write_dataset(data, output, seed):
    """Write stable UTF-8 CSVs and metadata only after validation succeeds."""
    from scripts.validate_synthetic_data import validate_data

    checks = validate_data(data, SNAPSHOT)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in TABLES:
        frame = data[name].copy()
        for column in frame.columns:
            if pd.api.types.is_datetime64_any_dtype(frame[column]):
                frame[column] = frame[column].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        path = output / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n", na_rep="")
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = {
        "seed": seed, "generation_start": START.isoformat(), "analysis_as_of": SNAPSHOT.isoformat(),
        "python_version": platform.python_version(), "pandas_version": pd.__version__, "numpy_version": np.__version__,
        "row_counts": {name: len(data[name]) for name in TABLES},
        "sla_policy_hours": {k: {"response": v[0], "resolution": v[1]} for k, v in POLICIES.items()},
        "csv_sha256": hashes, "validation_checks": checks,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    tickets = data["tickets"]
    lines = ["# Synthetic Data Summary", "", f"Seed: {seed}. Snapshot: {SNAPSHOT.isoformat()}. All records are fictional.", "",
             "| Table | Rows |", "| --- | ---: |"]
    lines.extend(f"| {name} | {len(data[name]):,} |" for name in TABLES)
    lines.extend(["", "## Scenario counts", "", "| Scenario | Tickets |", "| --- | ---: |"])
    scenarios = {
        "Unresolved": tickets.resolved_at.isna().sum(), "Reopened at least once": tickets.reopen_count.sum(),
        "Reassigned (including reopen handoffs)": data["assignment_history"].ticket_id.value_counts().gt(1).sum(),
        "Response SLA breached": tickets.response_sla_status.eq("Breached").sum(),
        "Resolution SLA breached": tickets.resolution_sla_status.eq("Breached").sum(),
        "With feedback": len(data["customer_feedback"]),
    }
    lines.extend(f"| {name} | {int(count):,} |" for name, count in scenarios.items())
    lines.extend(["", "## Ticket statuses", "", "| Status | Tickets |", "| --- | ---: |"])
    lines.extend(f"| {name} | {count:,} |" for name, count in sorted(tickets.status.value_counts().items()))
    lines.extend(["", f"All {len(checks)} validation groups passed before export. Tests also validate the CSVs after reloading.",
                  "", "Scenario counts overlap. They are simulated operational patterns, not real business findings.", ""])
    (output / "row_count_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickets", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    metadata = write_dataset(generate_data(args.tickets, args.seed), args.output, args.seed)
    print(json.dumps(metadata["row_counts"], indent=2))
    print(f"Validated data written to {args.output}")


if __name__ == "__main__":
    main()
