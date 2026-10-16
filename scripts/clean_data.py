"""Clean the six support CSVs with Pandas, preserving rejected source records."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.generate_synthetic_data import DEFAULT_OUTPUT, POLICIES, ROOT, TABLES
from scripts.validate_synthetic_data import OPTIONAL, SCHEMAS, load_data, validate_data

DEFAULT_CLEAN = ROOT / "data" / "processed" / "cleaned"
DEFAULT_QUARANTINE = ROOT / "data" / "processed" / "quarantine"
DEFAULT_REPORT = ROOT / "reports" / "data_quality_report.json"
INTEGER_COLUMNS = {"reopen_count", "response_target_hours", "resolution_target_hours", "csat_score"}
CATEGORIES = {
    ("customers", "segment"): ["Individual", "Small Business", "Enterprise"],
    ("customers", "region"): ["Region A", "Region B", "Region C", "Region D"],
    ("teams", "team_name"): ["Tier 1 Support", "Technical Support", "Billing Support"],
    ("teams", "specialization"): ["Account and General", "Technical", "Billing"],
    ("agents", "experience_level"): ["Junior", "Intermediate", "Senior"],
    ("tickets", "priority"): list(POLICIES),
    ("tickets", "category"): ["Account", "Technical", "Billing", "General"],
    ("tickets", "channel"): ["Email", "Chat", "Phone", "Web"],
    ("tickets", "status"): ["Open", "In Progress", "Pending", "Resolved", "Closed"],
    ("assignment_history", "assignment_reason"): ["Initial", "Reassignment", "Reopened"],
}
for sla_column in ["response_sla_status", "resolution_sla_status", "overall_sla_status"]:
    CATEGORIES[("tickets", sla_column)] = ["Met", "Breached", "Pending"]


def read_sources(directory):
    """Read IDs as text and blanks as blanks, never guessing 'NA' to mean null."""
    raw, schema_issues = {}, {}
    for name in TABLES:
        path = Path(directory) / f"{name}.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, [])
            for record, values in enumerate(reader, start=2):
                if len(values) != len(header):
                    raise ValueError(f"{path.name}: malformed CSV record {record}; expected {len(header)} fields, got {len(values)}")
        # A malformed CSV is a file-level error: do not skip unparseable rows.
        raw[name] = pd.read_csv(path, dtype="string", keep_default_na=False, encoding="utf-8-sig", on_bad_lines="error")
        expected = SCHEMAS[name].split()
        issues = []
        if len(header) != len(set(header)):
            issues.append("duplicate_column_names")
        if missing := sorted(set(expected) - set(header)):
            issues.append("missing_columns:" + ",".join(missing))
        if extra := sorted(set(header) - set(expected)):
            issues.append("unexpected_columns:" + ",".join(extra))
        schema_issues[name] = issues
    return raw, schema_issues


def clean_frames(raw, snapshot, schema_issues=None):
    """Return typed accepted frames, original rejected rows, audit, and counts.

    Every input row ends in exactly one of accepted or quarantine. Exact duplicate
    extras are quarantined; conflicting keys reject every candidate for that key.
    """
    snapshot = pd.Timestamp(snapshot)
    if snapshot.tzinfo is None:
        raise ValueError("analysis_as_of must have an explicit timezone")
    snapshot = snapshot.tz_convert("UTC")
    schema_issues = {name: list((schema_issues or {}).get(name, [])) for name in TABLES}
    frames, reasons, changes = {}, {}, []
    for name in TABLES:
        source = raw[name].reset_index(drop=True)
        raw[name] = source
        expected = SCHEMAS[name].split()
        if set(source.columns) != set(expected) and not schema_issues[name]:
            schema_issues[name].append("schema_mismatch")
        frames[name] = source.reindex(columns=expected).copy()
        reasons[name] = [set() for _ in range(len(source))]

    def mark(name, mask, reason):
        mask = pd.Series(mask, index=frames[name].index).fillna(True).astype(bool)
        for index in mask.index[mask]:
            reasons[name][index].add(reason)

    def audit(name, column, before, after, rule):
        before = before.astype("string").fillna("")
        after = after.astype("string").fillna("")
        for index in before.index[before.ne(after)]:
            changes.append({"table": name, "source_record": int(index + 2), "column": column,
                            "original_value": before[index], "cleaned_value": after[index], "rule": rule})

    for name, frame in frames.items():
        if schema_issues[name]:
            mark(name, pd.Series(True, index=frame.index), "table_schema_error")
        for column in frame:
            before = frame[column].astype("string")
            text = before.str.strip().replace("", pd.NA)
            audit(name, column, before, text, "trim_whitespace_or_blank_to_null")
            if column not in OPTIONAL:
                mark(name, text.isna(), f"required_value:{column}")
            if (name, column) in CATEGORIES:
                mapping = {value.casefold(): value for value in CATEGORIES[(name, column)]}
                normalized = text.str.casefold().map(mapping).astype("string")
                valid = normalized.notna()
                audit(name, column, text[valid], normalized[valid], "canonical_category_case")
                mark(name, ~valid, f"invalid_category:{column}")
                text = normalized.where(valid, text)
            if column.endswith("_at") or column.endswith("_deadline"):
                explicit_zone = text.str.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})").fillna(False)
                parsed = pd.to_datetime(text.where(explicit_zone), format="ISO8601", errors="coerce", utc=True)
                mark(name, text.notna() & parsed.isna(), f"invalid_timestamp:{column}")
                if not column.endswith("_deadline"):
                    mark(name, parsed.gt(snapshot), f"future_event:{column}")
                valid = parsed.notna()
                audit(name, column, text[valid], parsed[valid].dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "normalize_utc")
                frame[column] = parsed
            elif column in INTEGER_COLUMNS:
                number = pd.to_numeric(text, errors="coerce").astype("Float64")
                valid = (number.notna() & np.isfinite(number) & number.mod(1).eq(0)
                         & number.between(-(2**31), 2**31 - 1)).fillna(False)
                mark(name, ~valid, f"invalid_integer:{column}")
                frame[column] = number.where(valid).astype("Int64")
                audit(name, column, text[valid], frame.loc[valid, column].astype("string"), "canonical_integer")
            else:
                frame[column] = text

        key = frame.columns[0]
        # Do not choose a winner among conflicting records sharing a primary key.
        conflict = frame[key].duplicated(keep=False) & ~frame.duplicated(keep=False)
        conflicting_keys = set(frame.loc[conflict, key].dropna())
        # A group may contain both an identical pair and a conflicting third row.
        distinct_rows = frame.drop_duplicates()
        conflicting_keys.update(distinct_rows.loc[distinct_rows[key].duplicated(keep=False), key].dropna())
        mark(name, frame[key].isin(conflicting_keys), "conflicting_primary_key")
        mark(name, frame.duplicated(keep="first") & ~frame[key].isin(conflicting_keys), "exact_duplicate_extra")
        prefixes = {"customers": "CU", "teams": "TM", "agents": "AG", "tickets": "TK", "assignment_history": "AS", "customer_feedback": "FB"}
        mark(name, ~frame[key].str.fullmatch(prefixes[name] + r"\d+").fillna(False), "invalid_primary_key_format")

    customers, teams, agents, tickets, history, feedback = [frames[name] for name in TABLES]
    mark("customers", ~customers.customer_label.str.fullmatch(r"Synthetic Customer \d+").fillna(False), "invalid_synthetic_customer_label")
    mark("agents", ~agents.agent_label.str.fullmatch(r"Synthetic Agent \d+").fillna(False), "invalid_synthetic_agent_label")
    expected_specialization = {"Tier 1 Support": "Account and General", "Technical Support": "Technical", "Billing Support": "Billing"}
    mark("teams", teams.team_name.map(expected_specialization).ne(teams.specialization), "team_specialization_mismatch")
    completed = tickets.status.isin(["Resolved", "Closed"])
    mark("tickets", completed.ne(tickets.resolved_at.notna()), "status_resolution_mismatch")
    mark("tickets", tickets.status.eq("Closed").ne(tickets.closed_at.notna()), "status_closure_mismatch")
    mark("tickets", tickets.status.eq("Open").ne(tickets.first_response_at.isna()), "status_response_mismatch")
    mark("tickets", completed & tickets.first_response_at.isna(), "completed_without_response")
    for column in ["first_response_at", "initial_resolved_at", "reopened_at", "resolved_at", "closed_at"]:
        mark("tickets", tickets[column].notna() & tickets[column].lt(tickets.created_at), f"before_creation:{column}")
    initial = tickets.initial_resolved_at.notna()
    reopened = tickets.reopened_at.notna()
    mark("tickets", initial & (tickets.first_response_at.isna() | tickets.first_response_at.gt(tickets.initial_resolved_at)), "invalid_initial_resolution_order")
    mark("tickets", ~tickets.reopen_count.isin([0, 1]) | tickets.reopen_count.ne(reopened.astype(int)), "reopen_count_mismatch")
    mark("tickets", reopened & (~initial | tickets.reopened_at.le(tickets.initial_resolved_at)), "invalid_reopen_order")
    mark("tickets", completed & ~initial, "completed_without_initial_resolution")
    mark("tickets", reopened & completed & tickets.resolved_at.le(tickets.reopened_at), "invalid_final_resolution_order")
    same_resolution = tickets.resolved_at.eq(tickets.initial_resolved_at) | (tickets.resolved_at.isna() & tickets.initial_resolved_at.isna())
    mark("tickets", ~reopened & ~same_resolution, "nonreopened_resolution_mismatch")
    mark("tickets", tickets.closed_at.notna() & tickets.closed_at.lt(tickets.resolved_at), "closure_before_resolution")

    for event, prefix, policy_index in [("first_response_at", "response", 0), ("resolved_at", "resolution", 1)]:
        targets = tickets.priority.map({key: value[policy_index] for key, value in POLICIES.items()})
        deadlines = (tickets.created_at + pd.to_timedelta(targets.fillna(0), unit="h")).where(targets.notna())
        mark("tickets", tickets[f"{prefix}_target_hours"].ne(targets), f"{prefix}_policy_mismatch")
        mark("tickets", tickets[f"{prefix}_deadline"].ne(deadlines), f"{prefix}_deadline_mismatch")
        expected = np.where(tickets[event].notna(), np.where(tickets[event].le(deadlines), "Met", "Breached"),
                            np.where(deadlines.lt(snapshot), "Breached", "Pending"))
        mark("tickets", tickets[f"{prefix}_sla_status"].ne(expected), f"{prefix}_sla_mismatch")
    expected = np.where(tickets.response_sla_status.eq("Breached").fillna(False) | tickets.resolution_sla_status.eq("Breached").fillna(False), "Breached",
                        np.where((tickets.response_sla_status.eq("Met") & tickets.resolution_sla_status.eq("Met")).fillna(False), "Met", "Pending"))
    mark("tickets", tickets.overall_sla_status.ne(expected), "overall_sla_mismatch")
    mark("customer_feedback", ~feedback.csat_score.isin([1, 2, 3, 4, 5]), "invalid_feedback_rating")
    remaining_feedback = feedback.loc[[not entry for entry in reasons["customer_feedback"]]]
    repeated_feedback = remaining_feedback.index[remaining_feedback.ticket_id.duplicated(keep=False)]
    mark("customer_feedback", feedback.index.isin(repeated_feedback), "multiple_feedback_for_ticket")
    mark("assignment_history", history.unassigned_at.notna() & history.unassigned_at.le(history.assigned_at), "invalid_assignment_interval")

    def accepted(name):
        return frames[name].loc[[not entry for entry in reasons[name]]]

    def lookup(keys, mapping):
        # Series.map on an empty timezone-aware mapper fails in Pandas 3.0.
        result = mapping.reindex(pd.Index(keys)).copy()
        result.index = keys.index
        return result

    foreign_keys = [
        ("agents", "team_id", "teams", "team_id"),
        ("tickets", "customer_id", "customers", "customer_id"),
        ("tickets", "current_agent_id", "agents", "agent_id"),
        ("tickets", "current_team_id", "teams", "team_id"),
        ("assignment_history", "ticket_id", "tickets", "ticket_id"),
        ("assignment_history", "agent_id", "agents", "agent_id"),
        ("assignment_history", "team_id", "teams", "team_id"),
        ("customer_feedback", "ticket_id", "tickets", "ticket_id"),
        ("customer_feedback", "customer_id", "customers", "customer_id"),
    ]
    # Iterate to a fixed point: a rejected parent must not leave accepted children.
    previous_rejected = -1
    while previous_rejected != sum(bool(entry) for entries in reasons.values() for entry in entries):
        previous_rejected = sum(bool(entry) for entries in reasons.values() for entry in entries)
        for child, column, parent, parent_key in foreign_keys:
            mark(child, ~frames[child][column].isin(accepted(parent)[parent_key]), f"missing_accepted_parent:{column}")
        valid_customers = accepted("customers").set_index("customer_id")
        valid_agents = accepted("agents").set_index("agent_id")
        valid_tickets = accepted("tickets").set_index("ticket_id")
        mark("tickets", lookup(tickets.customer_id, valid_customers.joined_at).gt(tickets.created_at), "customer_joined_after_creation")
        mark("tickets", lookup(tickets.current_agent_id, valid_agents.team_id).ne(tickets.current_team_id), "current_agent_team_mismatch")
        mark("assignment_history", lookup(history.agent_id, valid_agents.team_id).ne(history.team_id), "agent_team_mismatch")
        mark("assignment_history", lookup(history.agent_id, valid_agents.hired_at).gt(history.assigned_at), "assignment_before_hire")
        mark("customer_feedback", feedback.customer_id.ne(lookup(feedback.ticket_id, valid_tickets.customer_id)), "feedback_customer_mismatch")
        resolution = lookup(feedback.ticket_id, valid_tickets.resolved_at)
        mark("customer_feedback", resolution.isna(), "feedback_without_final_resolution")
        mark("customer_feedback", feedback.submitted_at.lt(resolution), "feedback_before_final_resolution")

        active_history = accepted("assignment_history").sort_values(["ticket_id", "assigned_at"])
        groups = active_history.groupby("ticket_id", sort=False)
        first = groups.head(1).set_index("ticket_id")
        last = groups.tail(1).set_index("ticket_id")
        bad_ids = set(valid_tickets.index) - set(first.index)
        bad_ids.update(first.index[first.assigned_at.ne(valid_tickets.created_at.reindex(first.index))])
        bad_ids.update(first.index[first.assignment_reason.ne("Initial")])
        initial_counts = active_history.assignment_reason.eq("Initial").groupby(active_history.ticket_id).sum()
        bad_ids.update(initial_counts.index[initial_counts.ne(1)])
        bad_ids.update(last.index[last.unassigned_at.notna()])
        bad_ids.update(last.index[last.agent_id.ne(valid_tickets.current_agent_id.reindex(last.index))])
        next_start = groups.assigned_at.shift(-1)
        bad_interval = next_start.notna() & active_history.unassigned_at.ne(next_start)
        previous_agent = groups.agent_id.shift(1)
        bad_agent = previous_agent.notna() & active_history.agent_id.eq(previous_agent)
        terminal = lookup(active_history.ticket_id, valid_tickets.resolved_at).fillna(snapshot)
        bad_time = active_history.assigned_at.gt(terminal)
        reopen_history = active_history.assignment_reason.eq("Reopened")
        expected_reopen = lookup(active_history.ticket_id, valid_tickets.reopened_at)
        bad_reopen = reopen_history & (expected_reopen.isna() | active_history.assigned_at.ne(expected_reopen))
        first_end = lookup(active_history.ticket_id, valid_tickets.initial_resolved_at).fillna(snapshot)
        bad_transfer = active_history.assignment_reason.eq("Reassignment") & active_history.assigned_at.ge(first_end)
        for mask, reason in [(bad_interval, "ownership_gap_or_overlap"), (bad_agent, "handoff_same_agent"),
                             (bad_time, "assignment_after_resolution"), (bad_reopen, "invalid_reopen_handoff"),
                             (bad_transfer, "transfer_after_initial_resolution")]:
            bad_rows = active_history.index[mask.fillna(True)]
            mark("assignment_history", history.index.isin(bad_rows), reason)
            bad_ids.update(active_history.loc[bad_rows, "ticket_id"])
        reopen_counts = active_history.loc[reopen_history].groupby("ticket_id").size()
        expected_counts = valid_tickets.reopened_at.notna().astype(int)
        bad_ids.update(expected_counts.index[expected_counts.ne(reopen_counts.reindex(expected_counts.index, fill_value=0))])
        mark("tickets", tickets.ticket_id.isin(bad_ids), "invalid_or_incomplete_assignment_history")

    cleaned = {name: accepted(name).copy().reset_index(drop=True) for name in TABLES}
    final_checks = validate_data(cleaned, snapshot) if len(cleaned["tickets"]) else []
    quarantine, counts = {}, {}
    for name in TABLES:
        indices = [index for index, entry in enumerate(reasons[name]) if entry]
        quarantine[name] = raw[name].loc[indices].copy()
        source_column, reason_column = "dq_source_record", "dq_rejection_reasons"
        while source_column in quarantine[name].columns:
            source_column = "_" + source_column
        while reason_column in quarantine[name].columns:
            reason_column = "_" + reason_column
        quarantine[name].insert(0, source_column, [index + 2 for index in indices])
        quarantine[name].insert(1, reason_column, [";".join(sorted(reasons[name][index])) for index in indices])
        count = Counter(reason for entry in reasons[name] for reason in entry)
        counts[name] = {"input": len(raw[name]), "accepted": len(cleaned[name]), "rejected": len(indices),
                        "rejection_reason_counts": dict(sorted(count.items())),
                        "quarantine_metadata_columns": {"source_record": source_column, "rejection_reasons": reason_column}}
        assert counts[name]["input"] == counts[name]["accepted"] + counts[name]["rejected"]
    report = {
        "analysis_as_of": snapshot.isoformat(), "tables": counts, "schema_issues": schema_issues,
        "total_input": sum(item["input"] for item in counts.values()),
        "total_accepted": sum(item["accepted"] for item in counts.values()),
        "total_rejected": sum(item["rejected"] for item in counts.values()),
        "normalization_change_count": len(changes),
        "normalization_rules": dict(sorted(Counter(change["rule"] for change in changes).items())),
        "unresolved_tickets_with_null_resolution": int(cleaned["tickets"].resolved_at.isna().sum()),
        "independent_validation_checks": final_checks,
        "ready_for_analysis": bool(final_checks) and not any(schema_issues.values()),
    }
    return cleaned, quarantine, pd.DataFrame(changes, columns=["table", "source_record", "column", "original_value", "cleaned_value", "rule"]), report


def export_csv(frame, path):
    frame = frame.copy()
    for column in frame:
        if isinstance(frame[column].dtype, pd.DatetimeTZDtype):
            frame[column] = frame[column].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n", na_rep="")


def clean_directory(source=DEFAULT_OUTPUT, output=DEFAULT_CLEAN, quarantine=DEFAULT_QUARANTINE, report_path=DEFAULT_REPORT):
    source, output, quarantine, report_path = [Path(path).resolve() for path in (source, output, quarantine, report_path)]
    # Protect source data and ensure output sets cannot overwrite one another.
    targets = [output, quarantine, report_path.parent]
    if any(path == source or path.is_relative_to(source) or source.is_relative_to(path) for path in targets):
        raise ValueError("Output and report directories must be separate from source")
    if output == quarantine or output.is_relative_to(quarantine) or quarantine.is_relative_to(output):
        raise ValueError("Cleaned and quarantine directories must be separate")
    if report_path.suffix != ".json":
        raise ValueError("Report path must end in .json; a .md companion is written automatically")
    for data_path in [output, quarantine]:
        if report_path.parent == data_path or report_path.parent.is_relative_to(data_path) or data_path.is_relative_to(report_path.parent):
            raise ValueError("Report directory must be separate from cleaned and quarantine directories")
    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    hashes = {f"{name}.csv": hashlib.sha256((source / f"{name}.csv").read_bytes()).hexdigest() for name in TABLES}
    raw, schema_issues = read_sources(source)
    cleaned, rejected, audit, report = clean_frames(raw, metadata["analysis_as_of"], schema_issues)
    report["source_directory"] = str(source)
    report["cleaned_directory"] = str(output)
    report["quarantine_directory"] = str(quarantine)
    report["source_sha256"] = hashes
    report["source_manifest_matches"] = hashes == metadata.get("csv_sha256", {})
    report["source_row_counts_match"] = {name: len(raw[name]) for name in TABLES} == metadata.get("row_counts", {})
    for directory in [output, quarantine, report_path.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        export_csv(cleaned[name], output / f"{name}.csv")
        export_csv(rejected[name], quarantine / f"{name}.csv")
    audit.to_csv(quarantine / "normalization_audit.csv", index=False, lineterminator="\n")
    # Validate the exported CSVs as well as the in-memory values.
    report["exported_csv_validation_checks"] = validate_data(load_data(output), metadata["analysis_as_of"]) if len(cleaned["tickets"]) else []
    report["cleaned_sha256"] = {f"{name}.csv": hashlib.sha256((output / f"{name}.csv").read_bytes()).hexdigest() for name in TABLES}
    report["source_files_unchanged"] = all(hashlib.sha256((source / name).read_bytes()).hexdigest() == checksum for name, checksum in hashes.items())
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# Data Quality Report", "", f"Snapshot: {report['analysis_as_of']}", "",
             "| Table | Input | Accepted | Rejected |", "| --- | ---: | ---: | ---: |"]
    for name, count in report["tables"].items():
        lines.append(f"| {name} | {count['input']:,} | {count['accepted']:,} | {count['rejected']:,} |")
    lines.extend([f"| **Total** | **{report['total_input']:,}** | **{report['total_accepted']:,}** | **{report['total_rejected']:,}** |", "",
                  f"Unresolved tickets retaining null resolution: {report['unresolved_tickets_with_null_resolution']:,}.",
                  f"Normalization changes: {report['normalization_change_count']:,}.",
                  f"Ready for analysis: {report['ready_for_analysis']}. Source CSVs unchanged: {report['source_files_unchanged']}.",
                  f"Source checksum manifest matches: {report['source_manifest_matches']}. Source row counts match: {report['source_row_counts_match']}.",
                  "", "## File locations", "", f"- Source: `{source}`", f"- Cleaned: `{output}`", f"- Quarantine and normalization audit: `{quarantine}`",
                  "", "## Findings", ""])
    for name, count in report["tables"].items():
        for reason, amount in count["rejection_reason_counts"].items():
            lines.append(f"- {name}: {reason} — {amount} rows")
        for issue in report["schema_issues"][name]:
            lines.append(f"- {name}: {issue}")
    if report["total_rejected"] == 0 and not any(report["schema_issues"].values()):
        lines.append("No invalid records found. The generated source data already satisfies the cleaning rules.")
    lines.extend(["", "## Interpretation", "", "Every input record is counted as accepted or rejected. Rejection reasons may overlap. Exact duplicate extras are quarantined, not silently dropped. Conflicting keys reject all candidates. Null event timestamps are retained when permitted by ticket state. Bad history can quarantine its ticket and dependent rows; bad feedback alone does not remove a valid ticket.",
                  "", "Accepted rows pass the existing independent relational/lifecycle/SLA validator in memory and after CSV export when tickets remain. See the JSON report for per-rule counts and file checksums. Empty accepted ticket sets are marked not ready.", ""])
    report_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_CLEAN)
    parser.add_argument("--quarantine", type=Path, default=DEFAULT_QUARANTINE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = clean_directory(args.input, args.output, args.quarantine, args.report)
    print(json.dumps({"tables": report["tables"], "accepted": report["total_accepted"],
                      "rejected": report["total_rejected"], "ready_for_analysis": report["ready_for_analysis"]}, indent=2))
    print(f"Report: {args.report}")
    if not report["ready_for_analysis"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
