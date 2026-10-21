"""Reproducible exploratory analysis of the cleaned synthetic support dataset."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "support-eda-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.generate_synthetic_data import ROOT
from scripts.validate_synthetic_data import load_data, validate_data

DEFAULT_INPUT = ROOT / "data" / "processed" / "cleaned"
DEFAULT_QUALITY = ROOT / "reports" / "data_quality_report.json"
DEFAULT_OUTPUT = ROOT / "reports" / "eda"
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
COLOR = {"navy": "#204466", "teal": "#198F9A", "orange": "#E38635", "purple": "#7956A6", "gray": "#647586"}


def ratio(numerator, denominator):
    """Return a percentage or None for a zero denominator."""
    return 100 * numerator / denominator if denominator else None


def brief_number(value, suffix=""):
    return "N/A" if value is None or pd.isna(value) else f"{value:,.2f}{suffix}"


def json_ready(value):
    """Use JSON null for unavailable metrics, never nonstandard NaN tokens."""
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if value is None or pd.isna(value):
        return None
    return value.item() if isinstance(value, np.generic) else value


def load_cleaned(directory, quality_path):
    quality = json.loads(Path(quality_path).read_text(encoding="utf-8"))
    if not quality.get("ready_for_analysis"):
        raise ValueError("Data-quality report is not ready for analysis; rerun cleaning")
    expected_hashes = quality.get("cleaned_sha256")
    if expected_hashes:
        observed_hashes = {name: hashlib.sha256((Path(directory) / name).read_bytes()).hexdigest()
                           for name in expected_hashes}
        if observed_hashes != expected_hashes:
            raise ValueError("Cleaned CSV checksums differ from the data-quality report")
    data = load_data(directory)
    snapshot = pd.Timestamp(quality["analysis_as_of"])
    validate_data(data, snapshot)
    expected = {name: item["accepted"] for name, item in quality["tables"].items()}
    observed = {name: len(frame) for name, frame in data.items()}
    if observed != expected:
        raise ValueError(f"Cleaned row counts differ from the data-quality report: {observed} != {expected}")
    return data, snapshot, quality


def build_analysis(data, snapshot):
    """Create ticket-grain measures and chart tables without losing unrated rows."""
    tickets = data["tickets"].copy()
    feedback = data["customer_feedback"][["ticket_id", "csat_score"]]
    teams = data["teams"][["team_id", "team_name"]]
    history = data["assignment_history"]
    if feedback.ticket_id.duplicated().any():
        raise ValueError("Feedback must have at most one row per ticket")
    tickets = tickets.merge(feedback, on="ticket_id", how="left", validate="one_to_one")
    tickets = tickets.merge(teams, left_on="current_team_id", right_on="team_id", how="left", validate="many_to_one")
    if tickets.csat_score.notna().sum() != len(feedback):
        raise ValueError("Feedback join lost ratings")
    if tickets.team_name.isna().any():
        raise ValueError("Team join lost labels")
    transfers = history.assign(is_transfer=history.assignment_reason.eq("Reassignment"))
    transfers = transfers.groupby("ticket_id")["is_transfer"].sum()
    tickets["reassignment_count"] = tickets.ticket_id.map(transfers).fillna(0).astype(int)
    tickets["response_hours"] = (tickets.first_response_at - tickets.created_at).dt.total_seconds() / 3600
    tickets["resolution_hours"] = (tickets.resolved_at - tickets.created_at).dt.total_seconds() / 3600
    tickets["unresolved"] = tickets.resolved_at.isna()
    tickets["backlog_age_hours"] = np.where(tickets.unresolved,
                                              (snapshot - tickets.created_at).dt.total_seconds() / 3600, np.nan)
    tickets["month"] = tickets.created_at.dt.strftime("%Y-%m")
    tickets["backlog_age_bucket"] = pd.cut(tickets.backlog_age_hours, bins=[0, 24, 48, 72, np.inf],
                                             labels=["Under 24h", "24–<48h", "48–<72h", "72h+"])

    total = len(tickets)
    responded = int(tickets.first_response_at.notna().sum())
    resolved = int(tickets.resolved_at.notna().sum())
    unresolved = int(tickets.unresolved.sum())
    rated = int(tickets.csat_score.notna().sum())
    sla = {}
    for name in ["response", "resolution", "overall"]:
        counts = tickets[f"{name}_sla_status"].value_counts()
        met, breached, pending = [int(counts.get(state, 0)) for state in ["Met", "Breached", "Pending"]]
        sla[name] = {"met": met, "breached": breached, "pending": pending,
                     "assessable": met + breached, "compliance_pct": ratio(met, met + breached)}
    metrics = {
        "snapshot": snapshot.isoformat(), "creation_start": tickets.created_at.min().isoformat(),
        "creation_end": tickets.created_at.max().isoformat(),
        "tickets": total, "responded": responded,
        "unanswered": total - responded, "resolved": resolved, "unresolved": unresolved,
        "unresolved_pct": ratio(unresolved, total),
        "response_hours_mean": tickets.response_hours.mean(),
        "response_hours_median": tickets.response_hours.median(),
        "resolution_hours_mean": tickets.resolution_hours.mean(),
        "resolution_hours_median": tickets.resolution_hours.median(),
        "sla": sla,
        "backlog_age_hours_mean": tickets.backlog_age_hours.mean(),
        "backlog_age_hours_median": tickets.backlog_age_hours.median(),
        "overdue_unresolved": int((tickets.unresolved & tickets.resolution_sla_status.eq("Breached")).sum()),
        "reassigned_tickets": int(tickets.reassignment_count.gt(0).sum()),
        "reassignment_events": int(tickets.reassignment_count.sum()),
        "reopened_tickets": int(tickets.reopen_count.gt(0).sum()),
        "reopened_unresolved": int((tickets.reopen_count.gt(0) & tickets.unresolved).sum()),
        "rated": rated, "unrated_resolved": resolved - rated,
        "csat_mean": tickets.csat_score.mean(), "csat_median": tickets.csat_score.median(),
        "positive_csat_pct": ratio(int(tickets.csat_score.ge(4).sum()), rated),
        "feedback_coverage_pct": ratio(rated, resolved),
    }
    if total != resolved + unresolved or sla["overall"]["assessable"] + sla["overall"]["pending"] != total:
        raise ValueError("KPI denominators do not reconcile to ticket count")
    if tickets.reassignment_count.sum() != history.assignment_reason.eq("Reassignment").sum():
        raise ValueError("Reassignment event count does not reconcile")

    groups = {}
    groups["monthly_volume"] = tickets.groupby("month", sort=True).size().rename("tickets").reset_index()
    for column in ["priority", "category", "channel", "team_name", "status"]:
        groups[column] = tickets.groupby(column, sort=False).size().rename("tickets").reset_index()
    groups["priority"] = groups["priority"].set_index("priority").reindex(PRIORITY_ORDER).reset_index()
    duration = tickets.groupby("priority", observed=True).agg(
        tickets=("ticket_id", "size"), answered=("response_hours", "count"),
        response_mean_hours=("response_hours", "mean"), response_median_hours=("response_hours", "median"),
        resolved=("resolution_hours", "count"), resolution_mean_hours=("resolution_hours", "mean"),
        resolution_median_hours=("resolution_hours", "median")).reindex(PRIORITY_ORDER).reset_index()
    groups["duration_by_priority"] = duration
    sla_rows = []
    for priority in PRIORITY_ORDER:
        subset = tickets.loc[tickets.priority.eq(priority)]
        for name in ["response", "resolution", "overall"]:
            counts = subset[f"{name}_sla_status"].value_counts()
            met, breached, pending = [int(counts.get(state, 0)) for state in ["Met", "Breached", "Pending"]]
            sla_rows.append({"priority": priority, "commitment": name, "met": met, "breached": breached,
                             "pending": pending, "assessable": met + breached,
                             "compliance_pct": ratio(met, met + breached)})
    groups["sla_by_priority"] = pd.DataFrame(sla_rows)
    groups["backlog_by_priority"] = (tickets.loc[tickets.unresolved].groupby("priority", observed=True).size()
                                      .reindex(PRIORITY_ORDER, fill_value=0).rename("tickets").reset_index())
    groups["backlog_age"] = (tickets.loc[tickets.unresolved].groupby("backlog_age_bucket", observed=False).size()
                                 .rename("tickets").reset_index())
    groups["reassignments"] = (tickets.reassignment_count.clip(upper=3).map(lambda n: "3+" if n == 3 else str(n))
                                .value_counts().reindex(["0", "1", "2", "3+"], fill_value=0)
                                .rename_axis("reassignment_count").reset_index(name="tickets"))
    groups["reassignments"] = groups["reassignments"].loc[groups["reassignments"].tickets.gt(0)].reset_index(drop=True)
    groups["reopened_by_priority"] = (tickets.groupby("priority", observed=True).agg(
        tickets=("ticket_id", "size"), reopened=("reopen_count", "sum"))
        .reindex(PRIORITY_ORDER).reset_index())
    groups["ratings"] = (tickets.csat_score.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
                          .rename_axis("csat_score").reset_index(name="responses"))
    coverage = (tickets.groupby("priority", observed=True).agg(resolved=("resolved_at", "count"),
                rated=("csat_score", "count"), mean_csat=("csat_score", "mean"),
                median_csat=("csat_score", "median")).reindex(PRIORITY_ORDER).reset_index())
    coverage["coverage_pct"] = [ratio(int(row.rated), int(row.resolved)) for row in coverage.itertuples()]
    groups["feedback_by_priority"] = coverage
    return tickets, metrics, groups


def configure_plots():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 13,
                         "axes.titleweight": "bold", "axes.labelsize": 10,
                         "figure.facecolor": "white", "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.facecolor": "white"})


def style_axis(ax, ylabel=None):
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)


def save_chart(fig, path, subtitle):
    fig.text(.04, .015, subtitle, fontsize=8, color=COLOR["gray"])
    fig.savefig(path, dpi=170, bbox_inches="tight", pad_inches=.15)
    plt.close(fig)


def make_charts(groups, metrics, output):
    configure_plots()
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    note = f"Synthetic-data observation  |  Snapshot {metrics['snapshot'][:10]} UTC"
    monthly = groups["monthly_volume"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(monthly.month, monthly.tickets, marker="o", linewidth=2.5, color=COLOR["teal"])
    for row in monthly.itertuples():
        ax.annotate(f"{row.tickets:,}", (row.month, row.tickets), xytext=(0, 8), textcoords="offset points", ha="center")
    ax.set_title("Ticket volume by creation month", loc="left", pad=12)
    ax.set_xlabel("Creation month (UTC)")
    ax.set_ylim(0, monthly.tickets.max() * 1.16)
    style_axis(ax, "Tickets")
    fig.tight_layout(rect=(0, .06, 1, 1))
    paths.append(output / "01_monthly_volume.png")
    save_chart(fig, paths[-1], note + "  |  One row per ticket")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, key, title in zip(axes, ["priority", "category", "channel"], ["Priority", "Category", "Channel"]):
        frame = groups[key]
        if key == "priority":
            frame = frame.set_index("priority").reindex(PRIORITY_ORDER).reset_index()
        bars = ax.barh(frame[key], frame.tickets, color=COLOR["navy"])
        ax.invert_yaxis()
        ax.bar_label(bars, padding=3, fmt=lambda value: f"{value:,.0f}")
        ax.set_xlim(0, frame.tickets.max() * 1.2)
        ax.set_title(title, loc="left")
        ax.set_xlabel("Tickets")
    fig.suptitle("Ticket mix", fontsize=15, fontweight="bold", x=.04, ha="left")
    fig.tight_layout(rect=(0, .06, 1, .94))
    paths.append(output / "02_ticket_mix.png")
    save_chart(fig, paths[-1], note + "  |  Three views of the same ticket population")

    duration = groups["duration_by_priority"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    x = np.arange(len(PRIORITY_ORDER))
    for ax, prefix, title, sample in [
        (axes[0], "response", "First response time", "answered"),
        (axes[1], "resolution", "Final resolution time", "resolved"),
    ]:
        ax.bar(x - .18, duration[f"{prefix}_mean_hours"], width=.35, label="Average", color=COLOR["orange"])
        ax.bar(x + .18, duration[f"{prefix}_median_hours"], width=.35, label="Median", color=COLOR["teal"])
        ax.set_xticks(x, PRIORITY_ORDER)
        ax.set_title(title, loc="left")
        style_axis(ax, "Elapsed calendar hours")
        ax.legend(frameon=False)
        ax.text(.5, -.19, "Sample n: " + ", ".join(str(int(n)) for n in duration[sample]),
                transform=ax.transAxes, ha="center", fontsize=8, color=COLOR["gray"])
    fig.suptitle("Average and median service time by priority", fontsize=15, fontweight="bold", x=.04, ha="left")
    fig.tight_layout(rect=(0, .08, 1, .94))
    paths.append(output / "03_service_times.png")
    save_chart(fig, paths[-1], note + "  |  Missing events excluded; durations measured from creation")

    sla = groups["sla_by_priority"]
    fig, ax = plt.subplots(figsize=(12, 5))
    for offset, commitment, color in [(-.25, "response", COLOR["teal"]), (0, "resolution", COLOR["orange"]),
                                       (.25, "overall", COLOR["purple"])]:
        subset = sla.loc[sla.commitment.eq(commitment)]
        values = subset.compliance_pct.to_numpy(dtype=float)
        bars = ax.bar(x + offset, values, width=.23, label=commitment.capitalize(), color=color)
        for bar, count in zip(bars, subset.assessable):
            ax.annotate(f"n={count:,}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7)
    ax.set_xticks(x, PRIORITY_ORDER)
    ax.set_ylim(0, 112)
    ax.set_title("SLA compliance by priority", loc="left", pad=12)
    ax.legend(frameon=False, ncol=3)
    style_axis(ax, "Met / (Met + Breached), %")
    fig.tight_layout(rect=(0, .06, 1, 1))
    paths.append(output / "04_sla_compliance.png")
    save_chart(fig, paths[-1], note + "  |  Pending excluded from each denominator; n labels show assessable tickets")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    backlog = groups["backlog_by_priority"]
    bars = axes[0].bar(backlog.priority, backlog.tickets, color=COLOR["navy"])
    axes[0].bar_label(bars, padding=3, fmt=lambda value: f"{value:,.0f}")
    axes[0].set_title("Unresolved tickets by priority", loc="left")
    style_axis(axes[0], "Tickets")
    age = groups["backlog_age"]
    bars = axes[1].bar(age.backlog_age_bucket.astype(str), age.tickets, color=COLOR["orange"])
    axes[1].bar_label(bars, padding=3, fmt=lambda value: f"{value:,.0f}")
    axes[1].set_title("Age since creation", loc="left")
    style_axis(axes[1], "Unresolved tickets")
    fig.suptitle("Backlog at the fixed snapshot", fontsize=15, fontweight="bold", x=.04, ha="left")
    fig.tight_layout(rect=(0, .06, 1, .94))
    paths.append(output / "05_backlog.png")
    save_chart(fig, paths[-1], note + "  |  24/48/72-hour bucket lower bounds included")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    change = groups["reassignments"]
    bars = axes[0].bar(change.reassignment_count, change.tickets, color=COLOR["purple"])
    axes[0].bar_label(bars, padding=3, fmt=lambda value: f"{value:,.0f}")
    axes[0].set_title("Ordinary reassignments per ticket", loc="left")
    axes[0].set_xlabel("Reassignments")
    style_axis(axes[0], "Tickets")
    reopened = groups["reopened_by_priority"]
    rates = 100 * reopened.reopened / reopened.tickets
    bars = axes[1].bar(reopened.priority, rates, color=COLOR["teal"])
    for bar, count in zip(bars, reopened.reopened):
        axes[1].annotate(f"{count:,}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                         xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
    axes[1].set_title("Reopened share by priority", loc="left")
    style_axis(axes[1], "Reopened / tickets, %")
    fig.suptitle("Ownership changes and reopening", fontsize=15, fontweight="bold", x=.04, ha="left")
    fig.tight_layout(rect=(0, .06, 1, .94))
    paths.append(output / "06_reassignments_reopens.png")
    save_chart(fig, paths[-1], note + "  |  Reopen handoffs are separate from ordinary reassignment events")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    ratings = groups["ratings"]
    bars = axes[0].bar(ratings.csat_score.astype(str), ratings.responses, color=COLOR["teal"])
    axes[0].bar_label(bars, padding=3, fmt=lambda value: f"{value:,.0f}")
    axes[0].set_title("Customer ratings", loc="left")
    axes[0].set_xlabel("CSAT score (1–5)")
    style_axis(axes[0], "Responses")
    coverage = groups["feedback_by_priority"]
    bars = axes[1].bar(coverage.priority, coverage.coverage_pct, color=COLOR["orange"])
    for bar, count, resolved_count in zip(bars, coverage.rated, coverage.resolved):
        axes[1].annotate(f"{count:,}/{resolved_count:,}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                         xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
    axes[1].set_title("Feedback coverage by priority", loc="left")
    style_axis(axes[1], "Rated / resolved, %")
    axes[1].set_ylim(0, max(65, float(coverage.coverage_pct.max()) * 1.25))
    fig.suptitle("Satisfaction and who responded", fontsize=15, fontweight="bold", x=.04, ha="left")
    fig.tight_layout(rect=(0, .06, 1, .94))
    paths.append(output / "07_customer_ratings.png")
    save_chart(fig, paths[-1], note + "  |  Missing feedback is excluded from rating calculations")
    return paths


def render_report(metrics, groups, quality, charts):
    def table(frame, columns=None, formats=None):
        columns = columns or list(frame.columns)
        formats = formats or {}
        labels = {"priority": "Priority", "category": "Category", "channel": "Channel", "team_name": "Current team",
                  "tickets": "Tickets", "answered": "Answered", "resolved": "Resolved", "rated": "Rated",
                  "response_mean_hours": "Response average (h)", "response_median_hours": "Response median (h)",
                  "resolution_mean_hours": "Resolution average (h)", "resolution_median_hours": "Resolution median (h)",
                  "commitment": "Commitment", "met": "Met", "breached": "Breached", "pending": "Pending",
                  "assessable": "Assessable", "compliance_pct": "Compliance", "backlog_age_bucket": "Age bucket",
                  "reassignment_count": "Reassignments", "reopened": "Reopened", "csat_score": "Rating",
                  "responses": "Responses", "coverage_pct": "Coverage", "mean_csat": "Average CSAT",
                  "median_csat": "Median CSAT"}
        lines = ["| " + " | ".join(labels.get(column, column.replace("_", " ").title()) for column in columns) + " |",
                 "| " + " | ".join(["---"] * len(columns)) + " |"]
        for row in frame[columns].itertuples(index=False, name=None):
            values = []
            for column, value in zip(columns, row):
                if pd.isna(value):
                    values.append("N/A")
                elif column in formats:
                    values.append(formats[column](value))
                elif isinstance(value, (int, np.integer)):
                    values.append(f"{value:,}")
                else:
                    values.append(str(value))
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    monthly = groups["monthly_volume"]
    first, last = monthly.iloc[0], monthly.iloc[-1]
    leading_category = groups["category"].sort_values("tickets", ascending=False).iloc[0]
    largest_backlog = groups["backlog_by_priority"].sort_values("tickets", ascending=False).iloc[0]
    long_backlog = int(groups["backlog_age"].set_index("backlog_age_bucket").loc["72h+", "tickets"])
    months = len(monthly)
    avg_month = metrics["tickets"] / months
    lines = [
        "# Exploratory Data Analysis — Synthetic Customer Support Data", "",
        f"**Synthetic-data observation.** Fixed snapshot: {metrics['snapshot']}. Tickets created from {metrics['creation_start'][:10]} through {metrics['creation_end'][:10]} (UTC). All records are fictional.", "",
        "## Scope and data checks", "",
        f"Analyzed **{metrics['tickets']:,} accepted tickets** from the cleaned six-table dataset. The cleaning report recorded **{quality['total_rejected']:,} rejected records** across all tables. The ticket, team, feedback, and assignment joins were checked so each ticket contributes once to ticket-level KPIs. All event times are UTC; elapsed hours use a 24/7 calendar clock.", "",
        "## Ticket demand and mix", "",
        f"Synthetic-data observation: monthly arrivals rose from **{first.tickets:,} in {first.month}** to **{last.tickets:,} in {last.month}**. The six-month average was **{avg_month:,.1f} tickets per month**. The generator was configured with rising monthly demand weights, so this is an intended simulation pattern rather than a discovered real-world trend.", "",
        "| Month | Tickets |", "| --- | ---: |",
    ]
    lines.extend(f"| {row.month} | {row.tickets:,} |" for row in monthly.itertuples())
    lines.extend(["", f"Synthetic-data observation: **{leading_category.category}** was the largest category (**{leading_category.tickets:,} tickets**). The tables below show the priority, category, channel, and snapshot-team mix. Team reflects final recorded ownership; it does not indicate all work done on a ticket.", ""])
    for key, label in [("priority", "Priority"), ("category", "Category"), ("channel", "Channel"), ("team_name", "Current team")]:
        lines.extend([f"### {label}", "", table(groups[key], [key, "tickets"]), ""])
    lines.extend(["## Service speed and SLA", "",
                  f"Synthetic-data observation: first response time was **{brief_number(metrics['response_hours_mean'], ' h')} on average** and **{brief_number(metrics['response_hours_median'], ' h')} at the median**, among **{metrics['responded']:,} answered tickets**. **{metrics['unanswered']:,} tickets** had no first response and are excluded from those duration figures.", "",
                  f"Final resolution time was **{brief_number(metrics['resolution_hours_mean'], ' h')} on average** and **{brief_number(metrics['resolution_hours_median'], ' h')} at the median**, among **{metrics['resolved']:,} resolved tickets**. The gap between average and median reflects the simulated long tail of slower cases; it should not be interpreted as a real team benchmark.", "",
                  table(groups["duration_by_priority"],
                        ["priority", "answered", "response_mean_hours", "response_median_hours", "resolved", "resolution_mean_hours", "resolution_median_hours"],
                        {name: lambda value: f"{value:.2f}" for name in ["response_mean_hours", "response_median_hours", "resolution_mean_hours", "resolution_median_hours"]}), "",
                  "SLA compliance uses **Met / (Met + Breached)**. Pending commitments are reported separately and excluded from the denominator. Breached includes overdue unfinished tickets. Overall SLA is a ticket-level classification, not an average of response and resolution rates.", "",
                  "| Commitment | Met | Breached | Pending | Assessable | Compliance |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for name, value in metrics["sla"].items():
        lines.append(f"| {name.title()} | {value['met']:,} | {value['breached']:,} | {value['pending']:,} | {value['assessable']:,} | {brief_number(value['compliance_pct'], '%')} |")
    lines.extend(["", "### SLA by priority", "", table(groups["sla_by_priority"],
                  ["priority", "commitment", "met", "breached", "pending", "assessable", "compliance_pct"],
                  {"compliance_pct": lambda value: f"{value:.2f}%"}), "",
                  "## Backlog, reassignments, and reopened tickets", "",
                  f"Synthetic-data observation: **{metrics['unresolved']:,} tickets ({brief_number(metrics['unresolved_pct'], '%')})** were unresolved at the snapshot; **{metrics['overdue_unresolved']:,}** were past their resolution deadline. The largest priority backlog was **{largest_backlog.priority} ({largest_backlog.tickets:,})**. Unresolved tickets had an average age of **{brief_number(metrics['backlog_age_hours_mean'], ' h')}** and a median age of **{brief_number(metrics['backlog_age_hours_median'], ' h')}** since creation.", "",
                  "Historical daily backlog cannot be reconstructed from these snapshot records alone. Age buckets below are mutually exclusive and refer to unresolved tickets at the one fixed snapshot.", "",
                  table(groups["backlog_age"], ["backlog_age_bucket", "tickets"]), "",
                  f"Synthetic-data observation: **{metrics['reassigned_tickets']:,} tickets** had at least one ordinary reassignment, totaling **{metrics['reassignment_events']:,} ordinary reassignment events**. **{metrics['reopened_tickets']:,} tickets** reopened once; **{metrics['reopened_unresolved']:,}** of them remained unresolved at the snapshot. Reopen handoffs are distinct from ordinary reassignments. Ownership history is not a measure of active handle time.", "",
                  "### Ordinary reassignments per ticket", "", table(groups["reassignments"]), "",
                  "### Reopened tickets by priority", "", table(groups["reopened_by_priority"]), "",
                  "## Customer ratings and coverage", "",
                  f"Synthetic-data observation: **{metrics['rated']:,} resolved tickets** had feedback, while **{metrics['unrated_resolved']:,} resolved tickets** did not. Coverage was **{brief_number(metrics['feedback_coverage_pct'], '%')} of resolved tickets** under the synthetic assumption that all resolved tickets were offered a survey. Missing feedback was excluded, never scored as zero.", "",
                  f"Among rated tickets, average CSAT was **{brief_number(metrics['csat_mean'])}/5**, median was **{brief_number(metrics['csat_median'])}/5**, and **{brief_number(metrics['positive_csat_pct'], '%')}** of ratings were 4 or 5. Feedback was generated with lower tendencies for breached and reopened cases; associations in this simulation do not establish causation.", "",
                  "### Rating distribution", "", table(groups["ratings"]), "",
                  "### Feedback by priority", "", table(groups["feedback_by_priority"],
                  ["priority", "resolved", "rated", "coverage_pct", "mean_csat", "median_csat"],
                  {"coverage_pct": lambda value: f"{value:.2f}%", "mean_csat": lambda value: f"{value:.2f}",
                   "median_csat": lambda value: f"{value:.2f}"}), "",
                  "## Preliminary portfolio insights", "",
                  f"1. **Demand mix:** January-to-June ticket volume changed by **{brief_number(ratio(int(last.tickets - first.tickets), int(first.tickets)), '%')}**. Technical tickets were the largest category at **{leading_category.tickets:,}**. The generator deliberately raises demand weights, so use this as a portfolio staffing discussion rather than evidence for a real staffing decision.",
                  f"2. **SLA and backlog:** response compliance was **{brief_number(metrics['sla']['response']['compliance_pct'], '%')}**, while resolution compliance was **{brief_number(metrics['sla']['resolution']['compliance_pct'], '%')}**. Of **{metrics['unresolved']:,}** unresolved tickets, **{metrics['overdue_unresolved']:,} ({brief_number(ratio(metrics['overdue_unresolved'], metrics['unresolved']), '%')})** were overdue and **{long_backlog:,}** were at least 72 hours old. Completed-ticket averages alone hide this queue.",
                  f"3. **Ownership and reopening:** **{metrics['reassigned_tickets']:,}** tickets had an ordinary reassignment and **{metrics['reopened_tickets']:,}** reopened. These are useful simulated investigation groups; ownership history does not show effort or root cause.",
                  f"4. **Satisfaction coverage:** only **{brief_number(metrics['feedback_coverage_pct'], '%')}** of finally resolved tickets had feedback. Report the **{metrics['rated']:,}** rated-ticket denominator beside the **{brief_number(metrics['csat_mean'])}/5** average; no-feedback cases are not zero ratings.", "",
                  "## KPI definitions used", "",
                  "- **Volume:** count of distinct accepted tickets by UTC creation month, priority, category, channel, or current team; denominator for share comparisons is all accepted tickets.",
                  "- **Response hours:** first human response minus creation in calendar hours; average and median among answered tickets only. Unanswered count is separate.",
                  "- **Resolution hours:** final resolution minus creation in calendar hours; average and median among finally resolved tickets only. Reopening does not reset the clock.",
                  "- **SLA compliance:** Met divided by Met plus Breached, for response, resolution, or overall status. Pending is excluded and shown separately. Overall breach occurs when either component breaches.",
                  "- **Backlog:** tickets lacking final resolution at the snapshot; overdue means their resolution SLA is Breached. Age runs from creation to snapshot.",
                  "- **Reassignment:** ordinary `Reassignment` rows in assignment history; tickets with at least one such row are counted once. A `Reopened` handoff is counted separately.",
                  "- **Reopened:** tickets with `reopen_count = 1`; unresolved reopened tickets still lack final resolution.",
                  "- **CSAT:** 1–5 score from the optional feedback table. Mean, median, and positive share use rated tickets; coverage is rated resolved tickets divided by all resolved tickets.", "",
                  "## Charts", ""])
    lines.extend(f"- [{path.stem.replace('_', ' ').title()}](charts/{path.name})" for path in charts)
    lines.extend(["", "## Limits", "",
                  "All findings are synthetic-data observations from a seeded simulation. SLA targets and feedback behavior are design assumptions, not contractual standards. Priorities, channels, and ticket complexity differ across groups; descriptive comparisons are not causal estimates. Team is the recorded current owner and cannot measure individual productivity. The snapshot does not reconstruct historical daily backlog or every status transition. Feedback is optional and can be biased.", ""])
    return "\n".join(lines)


def run(input_dir=DEFAULT_INPUT, quality_path=DEFAULT_QUALITY, output_dir=DEFAULT_OUTPUT):
    data, snapshot, quality = load_cleaned(input_dir, quality_path)
    _, metrics, groups = build_analysis(data, snapshot)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name, frame in groups.items():
        frame.to_csv(output / f"{name}.csv", index=False, lineterminator="\n")
    chart_paths = make_charts(groups, metrics, output / "charts")
    report = render_report(metrics, groups, quality, chart_paths)
    (output / "eda_report.md").write_text(report, encoding="utf-8")
    (output / "kpi_summary.json").write_text(json.dumps(json_ready(metrics), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return metrics, chart_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--quality-report", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    metrics, charts = run(args.input, args.quality_report, args.output)
    print(f"Analyzed {metrics['tickets']:,} tickets; created {len(charts)} charts and {args.output / 'eda_report.md'}")


if __name__ == "__main__":
    main()
