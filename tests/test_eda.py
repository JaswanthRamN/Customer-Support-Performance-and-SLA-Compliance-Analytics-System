"""Reconcile EDA KPIs and output files against the cleaned source tables."""

import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from scripts.eda import DEFAULT_INPUT, DEFAULT_QUALITY, build_analysis, json_ready, load_cleaned, ratio, run


class EDATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.snapshot, cls.quality = load_cleaned(DEFAULT_INPUT, DEFAULT_QUALITY)
        cls.ticket_grain, cls.metrics, cls.groups = build_analysis(cls.data, cls.snapshot)

    def test_ticket_grain_and_group_totals(self):
        tickets = self.data["tickets"]
        self.assertEqual(len(self.ticket_grain), len(tickets))
        self.assertTrue(self.ticket_grain.ticket_id.is_unique)
        for name in ["monthly_volume", "priority", "category", "channel", "team_name", "status", "reassignments"]:
            self.assertEqual(int(self.groups[name].tickets.sum()), len(tickets), name)
        self.assertEqual(int(self.groups["backlog_age"].tickets.sum()), self.metrics["unresolved"])
        self.assertEqual(int(self.groups["backlog_by_priority"].tickets.sum()), self.metrics["unresolved"])

    def test_duration_mean_and_median_use_events_only(self):
        tickets = self.data["tickets"]
        response_hours = (tickets.first_response_at - tickets.created_at).dt.total_seconds().dropna() / 3600
        resolution_hours = (tickets.resolved_at - tickets.created_at).dt.total_seconds().dropna() / 3600
        self.assertAlmostEqual(self.metrics["response_hours_mean"], response_hours.sum() / len(response_hours))
        self.assertAlmostEqual(self.metrics["response_hours_median"], response_hours.median())
        self.assertAlmostEqual(self.metrics["resolution_hours_mean"], resolution_hours.sum() / len(resolution_hours))
        self.assertAlmostEqual(self.metrics["resolution_hours_median"], resolution_hours.median())
        self.assertGreater(self.metrics["response_hours_mean"], self.metrics["response_hours_median"])
        self.assertGreater(self.metrics["resolution_hours_mean"], self.metrics["resolution_hours_median"])
        self.assertEqual(len(response_hours) + self.metrics["unanswered"], self.metrics["tickets"])
        self.assertEqual(len(resolution_hours) + self.metrics["unresolved"], self.metrics["tickets"])

    def test_sla_denominators_and_backlog(self):
        tickets = self.data["tickets"]
        for commitment in ["response", "resolution", "overall"]:
            counts = tickets[f"{commitment}_sla_status"].value_counts()
            item = self.metrics["sla"][commitment]
            self.assertEqual(item["met"], counts.get("Met", 0))
            self.assertEqual(item["breached"], counts.get("Breached", 0))
            self.assertEqual(item["pending"], counts.get("Pending", 0))
            self.assertEqual(item["assessable"], item["met"] + item["breached"])
            self.assertAlmostEqual(item["compliance_pct"], 100 * item["met"] / item["assessable"])
            self.assertEqual(item["assessable"] + item["pending"], len(tickets))
        overdue = tickets.resolved_at.isna() & tickets.resolution_sla_status.eq("Breached")
        self.assertEqual(self.metrics["overdue_unresolved"], int(overdue.sum()))
        self.assertTrue(self.ticket_grain.loc[tickets.resolved_at.notna(), "backlog_age_hours"].isna().all())
        unresolved = tickets.resolved_at.isna()
        expected_age = (self.snapshot - tickets.loc[unresolved, "created_at"]).dt.total_seconds() / 3600
        pd.testing.assert_series_equal(
            self.ticket_grain.loc[unresolved, "backlog_age_hours"].reset_index(drop=True),
            expected_age.reset_index(drop=True), check_names=False,
        )

    def test_reassignment_and_reopen_counts(self):
        history = self.data["assignment_history"]
        tickets = self.data["tickets"]
        ordinary = history.loc[history.assignment_reason.eq("Reassignment")]
        self.assertEqual(self.metrics["reassignment_events"], len(ordinary))
        self.assertEqual(self.metrics["reassigned_tickets"], ordinary.ticket_id.nunique())
        self.assertEqual(self.metrics["reopened_tickets"], int(tickets.reopen_count.sum()))
        self.assertEqual(self.metrics["reopened_unresolved"], int((tickets.reopen_count.eq(1) & tickets.resolved_at.isna()).sum()))

    def test_feedback_excludes_missing_and_handles_no_ratings(self):
        feedback = self.data["customer_feedback"]
        self.assertEqual(self.metrics["rated"], len(feedback))
        self.assertAlmostEqual(self.metrics["csat_mean"], feedback.csat_score.mean())
        self.assertAlmostEqual(self.metrics["csat_median"], feedback.csat_score.median())
        self.assertEqual(self.metrics["unrated_resolved"], self.metrics["resolved"] - len(feedback))
        self.assertAlmostEqual(self.metrics["feedback_coverage_pct"], 100 * len(feedback) / self.metrics["resolved"])
        self.assertEqual(ratio(0, 0), None)

        chosen = set(self.data["tickets"].ticket_id.head(100))
        subset = {name: frame.copy() for name, frame in self.data.items()}
        subset["tickets"] = subset["tickets"].loc[subset["tickets"].ticket_id.isin(chosen)].copy()
        subset["assignment_history"] = subset["assignment_history"].loc[subset["assignment_history"].ticket_id.isin(chosen)].copy()
        subset["customer_feedback"] = subset["customer_feedback"].iloc[:0].copy()
        _, metrics, groups = build_analysis(subset, self.snapshot)
        self.assertEqual(metrics["rated"], 0)
        self.assertTrue(pd.isna(metrics["csat_mean"]))
        self.assertEqual(json_ready(metrics)["csat_mean"], None)
        self.assertEqual(groups["ratings"].responses.sum(), 0)

    def test_report_and_charts_export(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            metrics, charts = run(DEFAULT_INPUT, DEFAULT_QUALITY, output)
            self.assertEqual(metrics["tickets"], 10_000)
            self.assertEqual(len(charts), 7)
            for path in charts:
                self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            report = (output / "eda_report.md").read_text(encoding="utf-8")
            self.assertIn("Synthetic-data observation", report)
            self.assertIn("Average", report)
            self.assertIn("median", report)
            self.assertIn("Missing feedback was excluded", report)
            self.assertEqual(json.loads((output / "kpi_summary.json").read_text())["rated"], len(self.data["customer_feedback"]))

    def test_changed_cleaned_csv_is_rejected_even_if_row_count_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name in self.data:
                source = DEFAULT_INPUT / f"{name}.csv"
                (target / source.name).write_bytes(source.read_bytes())
            teams = target / "teams.csv"
            teams.write_bytes(teams.read_bytes().replace(b"Account and General", b"Account or General"))
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_cleaned(target, DEFAULT_QUALITY)


if __name__ == "__main__":
    unittest.main()
