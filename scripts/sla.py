"""Shared illustrative calendar-time SLA policy and calculations."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "sla_policy.json"


def load_policy(path=POLICY_PATH):
    """Return {priority: (response_minutes, resolution_minutes)}."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    priorities = document["priorities"]
    policy = {
        priority: (int(values["response_minutes"]), int(values["resolution_minutes"]))
        for priority, values in priorities.items()
    }
    if not policy or any(value <= 0 for targets in policy.values() for value in targets):
        raise ValueError("SLA targets must be positive integer minutes")
    return policy


POLICIES = load_policy()


def deadline_at(created_at, target_minutes):
    """Calculate an elapsed-calendar-time deadline from ticket creation."""
    if pd.isna(created_at):
        return pd.NaT
    return pd.Timestamp(created_at) + pd.Timedelta(minutes=int(target_minutes))


def sla_status(event_at, deadline, snapshot):
    """Classify one commitment using an inclusive event deadline boundary."""
    if pd.notna(event_at):
        return "Met" if event_at <= deadline else "Breached"
    return "Breached" if snapshot > deadline else "Pending"


def elapsed_hours(start_at, end_at):
    """Return elapsed calendar hours, or None when either event is missing."""
    if pd.isna(start_at) or pd.isna(end_at):
        return None
    return (pd.Timestamp(end_at) - pd.Timestamp(start_at)).total_seconds() / 3600


def unresolved_age_hours(created_at, resolved_at, snapshot):
    """Return snapshot age only for unresolved tickets."""
    if pd.notna(resolved_at):
        return None
    return elapsed_hours(created_at, snapshot)
