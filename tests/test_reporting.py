"""Reporting-view contracts and independent Python reconciliation tests."""

import unittest

from scripts.eda import DEFAULT_INPUT, DEFAULT_QUALITY, build_analysis, load_cleaned
from scripts.generate_synthetic_data import ROOT
from scripts.reconcile_reporting import build_python_baseline


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.snapshot, _ = load_cleaned(DEFAULT_INPUT, DEFAULT_QUALITY)
        cls.baseline = build_python_baseline(cls.data, cls.snapshot)

    def test_ticket_grain_prevents_assignment_duplication(self):
        ticket_count = len(self.data["tickets"])
        self.assertEqual(self.baseline["ticket_grain"]["tickets"], ticket_count)
        self.assertTrue(self.baseline["ticket_grain"]["ticket_ids_unique"])
        self.assertGreater(self.baseline["ticket_grain"]["assignment_rows"], ticket_count)
        for counts in self.baseline["dimension_ticket_counts"].values():
            self.assertEqual(sum(counts.values()), ticket_count)

    def test_key_python_results_reconcile_with_existing_independent_eda(self):
        _, metrics, _ = build_analysis(self.data, self.snapshot)
        self.assertEqual(self.baseline["backlog"]["backlog_tickets"], metrics["unresolved"])
        self.assertEqual(self.baseline["backlog"]["overdue_tickets"], metrics["overdue_unresolved"])
        self.assertEqual(self.baseline["reassignments"]["reassigned_tickets"], metrics["reassigned_tickets"])
        self.assertEqual(self.baseline["reassignments"]["reassignment_events"], metrics["reassignment_events"])
        self.assertEqual(self.baseline["reopened"]["reopened_tickets"], metrics["reopened_tickets"])
        self.assertEqual(self.baseline["satisfaction"]["rated_tickets"], metrics["rated"])
        self.assertAlmostEqual(self.baseline["service_times"]["average_response_hours"],
                               round(metrics["response_hours_mean"], 2))
        self.assertAlmostEqual(self.baseline["service_times"]["median_resolution_hours"],
                               round(metrics["resolution_hours_median"], 2))

    def test_null_and_current_backlog_semantics(self):
        tickets = self.data["tickets"]
        self.assertEqual(self.baseline["service_times"]["answered_tickets"],
                         int(tickets.first_response_at.notna().sum()))
        self.assertEqual(self.baseline["service_times"]["resolved_tickets"],
                         int(tickets.resolved_at.notna().sum()))
        self.assertEqual(self.baseline["backlog"]["backlog_tickets"],
                         int(tickets.resolved_at.isna().sum()))

    def test_view_layer_documents_grain_and_current_ownership(self):
        sql = (ROOT / "sql" / "reporting_views.sql").read_text(encoding="utf-8")
        for view in ("vw_ticket_metrics", "vw_reporting_dimensions", "vw_sla_compliance",
                     "vw_service_times", "vw_backlog_aging", "vw_reassignment_rates",
                     "vw_reopened_rates", "vw_satisfaction", "vw_overdue_tickets",
                     "vw_historical_assignment_activity"):
            self.assertIn(f"support_analytics.{view}", sql)
        self.assertIn("GROUP BY ticket_id", sql)
        self.assertIn("Current Team", sql)
        self.assertIn("current backlog, not historical backlog", sql)
        self.assertIn("must not be counted as", sql)
        validation = (ROOT / "sql" / "validation.sql").read_text(encoding="utf-8")
        self.assertIn("invalid_ticket_metrics_grain", validation)
        self.assertIn("invalid_reporting_dimension_counts", validation)


if __name__ == "__main__":
    unittest.main()
