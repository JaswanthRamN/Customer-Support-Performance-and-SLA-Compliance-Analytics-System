"""Run with: python -m unittest discover -s tests -v"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.generate_synthetic_data import (
    DEFAULT_OUTPUT, SNAPSHOT, generate_data, overall_status, write_dataset,
)
from scripts.sla import POLICIES, deadline_at, elapsed_hours, sla_status, unresolved_age_hours
from scripts.validate_synthetic_data import load_data, validate_data, validate_directory


class SyntheticDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generate_data(500, seed=42)

    def test_generated_relationships_and_lifecycle(self):
        self.assertEqual(len(self.data["tickets"]), 500)
        self.assertEqual(len(validate_data(self.data, SNAPSHOT)), 7)

    def test_reproducible_and_seed_sensitive(self):
        again = generate_data(500, seed=42)
        for name, frame in self.data.items():
            pd.testing.assert_frame_equal(frame, again[name])
        self.assertFalse(self.data["tickets"].equals(generate_data(500, seed=43)["tickets"]))

    def test_sla_deadline_boundaries(self):
        deadline = SNAPSHOT - pd.Timedelta(hours=1)
        for event, snapshot, expected in [
            (deadline, SNAPSHOT, "Met"),
            (deadline + pd.Timedelta(seconds=1), SNAPSHOT, "Breached"),
            (pd.NaT, deadline - pd.Timedelta(seconds=1), "Pending"),
            (pd.NaT, deadline, "Pending"),
            (pd.NaT, deadline + pd.Timedelta(seconds=1), "Breached"),
        ]:
            with self.subTest(event=event, snapshot=snapshot):
                self.assertEqual(sla_status(event, deadline, snapshot), expected)
        self.assertEqual(overall_status("Breached", "Pending"), "Breached")
        self.assertEqual(overall_status("Met", "Pending"), "Pending")
        self.assertEqual(overall_status("Met", "Met"), "Met")

    def test_each_priority_policy_and_calculations(self):
        created = pd.Timestamp("2026-06-30T00:00:00Z")
        expected = {
            "Critical": (15, 240), "High": (60, 480),
            "Medium": (240, 1440), "Low": (480, 4320),
        }
        self.assertEqual(POLICIES, expected)
        for priority, (response_minutes, resolution_minutes) in expected.items():
            with self.subTest(priority=priority):
                response_deadline = deadline_at(created, response_minutes)
                resolution_deadline = deadline_at(created, resolution_minutes)
                self.assertEqual(response_deadline, created + pd.Timedelta(minutes=response_minutes))
                self.assertEqual(resolution_deadline, created + pd.Timedelta(minutes=resolution_minutes))
                self.assertEqual(sla_status(response_deadline, response_deadline, SNAPSHOT), "Met")
                self.assertEqual(sla_status(response_deadline + pd.Timedelta(seconds=1), response_deadline, SNAPSHOT), "Breached")
                self.assertEqual(sla_status(resolution_deadline, resolution_deadline, SNAPSHOT), "Met")
                self.assertEqual(sla_status(resolution_deadline + pd.Timedelta(seconds=1), resolution_deadline, SNAPSHOT), "Breached")
                self.assertEqual(sla_status(pd.NaT, response_deadline,
                                            response_deadline - pd.Timedelta(seconds=1)), "Pending")
                self.assertEqual(sla_status(pd.NaT, response_deadline, response_deadline), "Pending")
                self.assertEqual(sla_status(pd.NaT, response_deadline, response_deadline + pd.Timedelta(seconds=1)), "Breached")
                self.assertEqual(elapsed_hours(created, response_deadline), response_minutes / 60)
                self.assertEqual(elapsed_hours(created, pd.NaT), None)
                self.assertEqual(unresolved_age_hours(created, pd.NaT, SNAPSHOT),
                                 elapsed_hours(created, SNAPSHOT))
                self.assertIsNone(unresolved_age_hours(created, resolution_deadline, SNAPSHOT))

    def test_csv_round_trip_and_identical_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / "first", Path(temporary) / "second"]
            for path in paths:
                write_dataset(self.data, path, seed=42)
                self.assertEqual(len(validate_directory(path)), 8)
            for file in paths[0].iterdir():
                self.assertEqual(file.read_bytes(), (paths[1] / file.name).read_bytes())

    def test_small_dataset_without_feedback(self):
        data = generate_data(1, seed=42)
        self.assertTrue(data["customer_feedback"].empty)
        validate_data(data, SNAPSHOT)
        with tempfile.TemporaryDirectory() as temporary:
            write_dataset(data, temporary, seed=42)
            validate_directory(temporary)

    def test_invalid_ticket_counts(self):
        for count in [0, -1]:
            with self.assertRaises(ValueError):
                generate_data(count)

    def test_validator_rejects_corruption(self):
        mutations = [
            ("tickets", "ticket_id", self.data["tickets"].iloc[1].ticket_id),
            ("tickets", "customer_id", "MISSING"),
            ("tickets", "created_at", SNAPSHOT + pd.Timedelta(days=1)),
            ("tickets", "status", "Unknown"),
            ("tickets", "response_target_minutes", 999),
            ("tickets", "response_sla_status", "Wrong"),
            ("tickets", "reopen_count", 2),
            ("assignment_history", "team_id", "TM99"),
            ("assignment_history", "assigned_at", SNAPSHOT),
            ("customer_feedback", "csat_score", 6),
            ("customer_feedback", "customer_id", "MISSING"),
            ("customer_feedback", "submitted_at", pd.Timestamp("2020-01-01T00:00:00Z")),
        ]
        for table, column, value in mutations:
            with self.subTest(table=table, column=column):
                damaged = {name: frame.copy(deep=True) for name, frame in self.data.items()}
                damaged[table].loc[0, column] = value
                with self.assertRaises(ValueError):
                    validate_data(damaged, SNAPSHOT)

    def test_validator_rejects_history_gaps(self):
        damaged = {name: frame.copy(deep=True) for name, frame in self.data.items()}
        history = damaged["assignment_history"]
        row = history.index[history.unassigned_at.notna()][0]
        history.loc[row, "unassigned_at"] += pd.Timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError, "gap or overlap"):
            validate_data(damaged, SNAPSHOT)

    def test_validator_rejects_schema_and_checksum_changes(self):
        damaged = {name: frame.copy(deep=True) for name, frame in self.data.items()}
        damaged["customers"]["email"] = "unwanted field"
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            validate_data(damaged, SNAPSHOT)
        with tempfile.TemporaryDirectory() as temporary:
            write_dataset(self.data, temporary, seed=42)
            path = Path(temporary) / "teams.csv"
            path.write_bytes(path.read_bytes().replace(b"Account and General", b"Changed label"))
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                validate_directory(temporary)

    def test_default_portfolio_dataset_and_scenario_coverage(self):
        # Validate the delivered 10,000-ticket CSVs, not just in-memory samples.
        self.assertEqual(len(validate_directory(DEFAULT_OUTPUT)), 8)
        data = load_data(DEFAULT_OUTPUT)
        tickets = data["tickets"]
        self.assertEqual(len(tickets), 10_000)
        self.assertEqual(tickets.status.nunique(), 5)
        self.assertEqual(tickets.priority.nunique(), 4)
        self.assertTrue(tickets.resolved_at.isna().any())
        self.assertTrue(tickets.reopened_at.notna().any())
        self.assertTrue((tickets.reopened_at.notna() & tickets.resolved_at.isna()).any())
        for column in ["response_sla_status", "resolution_sla_status"]:
            self.assertEqual(set(tickets[column]), {"Met", "Breached", "Pending"})
        self.assertTrue(data["assignment_history"].assignment_reason.eq("Reassignment").any())
        self.assertGreater(len(data["customer_feedback"]), 0)
        self.assertLess(len(data["customer_feedback"]), tickets.resolved_at.notna().sum())


if __name__ == "__main__":
    unittest.main()
