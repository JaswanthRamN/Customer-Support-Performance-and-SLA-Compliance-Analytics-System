"""Cleaning contracts, including corrupt source fixtures and accepted row balances."""

import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from scripts.clean_data import clean_directory, clean_frames, read_sources
from scripts.generate_synthetic_data import DEFAULT_OUTPUT, SNAPSHOT, generate_data, write_dataset
from scripts.validate_synthetic_data import validate_data


class CleaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.source = Path(cls.temporary.name) / "source"
        write_dataset(generate_data(400, 42), cls.source, 42)
        cls.raw, _ = read_sources(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def fresh(self):
        return {name: frame.copy(deep=True) for name, frame in self.raw.items()}

    def check_balance(self, cleaned, rejected, report):
        for name, counts in report["tables"].items():
            self.assertEqual(counts["input"], counts["accepted"] + counts["rejected"])
            self.assertEqual(counts["accepted"], len(cleaned[name]))
            self.assertEqual(counts["rejected"], len(rejected[name]))

    def test_valid_data_and_legitimate_missing_resolution(self):
        cleaned, rejected, _, report = clean_frames(self.fresh(), SNAPSHOT)
        self.assertEqual(report["total_rejected"], 0)
        self.assertTrue(report["ready_for_analysis"])
        expected = self.raw["tickets"].loc[self.raw["tickets"].resolved_at.eq(""), "ticket_id"]
        actual = cleaned["tickets"].loc[cleaned["tickets"].resolved_at.isna(), "ticket_id"]
        self.assertEqual(set(expected), set(actual))
        self.assertGreater(len(actual), 0)
        self.check_balance(cleaned, rejected, report)

    def test_formatting_is_normalized_and_audited(self):
        raw = self.fresh()
        raw["tickets"].loc[0, "priority"] = "  " + raw["tickets"].loc[0, "priority"].lower() + "  "
        raw["tickets"].loc[0, "ticket_id"] = " " + raw["tickets"].loc[0, "ticket_id"] + " "
        raw["tickets"].loc[0, "reopen_count"] = raw["tickets"].loc[0, "reopen_count"] + ".0"
        raw["tickets"].loc[0, "created_at"] = raw["tickets"].loc[0, "created_at"].replace("Z", "+00:00")
        cleaned, _, audit, report = clean_frames(raw, SNAPSHOT)
        self.assertEqual(report["total_rejected"], 0)
        self.assertGreaterEqual(len(audit), 5)
        self.assertEqual(audit.source_record.unique().tolist(), [2])
        self.assertEqual(cleaned["tickets"].reopen_count.dtype, pd.Int64Dtype())

    def test_exact_duplicates_are_accounted_for(self):
        for name in ["tickets", "customer_feedback", "assignment_history"]:
            with self.subTest(table=name):
                raw = self.fresh()
                raw[name] = pd.concat([raw[name], raw[name].iloc[[0]]], ignore_index=True)
                cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
                self.assertEqual(report["total_rejected"], 1)
                self.assertEqual(len(cleaned[name]), len(self.raw[name]))
                self.assertIn("exact_duplicate_extra", rejected[name].iloc[0].dq_rejection_reasons)
                self.check_balance(cleaned, rejected, report)

    def test_conflicting_duplicates_reject_all_candidates_and_children(self):
        raw = self.fresh()
        duplicate = raw["tickets"].iloc[[0]].copy()
        duplicate.loc[:, "channel"] = "Chat" if duplicate.iloc[0].channel != "Chat" else "Email"
        raw["tickets"] = pd.concat([raw["tickets"], raw["tickets"].iloc[[0]], duplicate], ignore_index=True)
        cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
        ticket = self.raw["tickets"].iloc[0].ticket_id
        self.assertNotIn(ticket, set(cleaned["tickets"].ticket_id))
        self.assertEqual(len(rejected["tickets"]), 3)
        self.assertFalse(cleaned["assignment_history"].ticket_id.eq(ticket).any())
        self.assertFalse(cleaned["customer_feedback"].ticket_id.eq(ticket).any())
        self.check_balance(cleaned, rejected, report)

    def test_invalid_types_categories_timestamps_and_ids_are_quarantined(self):
        mutations = [
            ("tickets", "priority", "Urgent"), ("tickets", "reopen_count", "1.5"),
            ("tickets", "response_target_minutes", "infinity"), ("tickets", "created_at", "not a date"),
            ("tickets", "created_at", "2026-01-01T12:00:00"),
            ("tickets", "created_at", "2027-01-01T00:00:00Z"),
            ("tickets", "ticket_id", ""), ("customers", "segment", "NA"),
            ("tickets", "first_response_at", "bad response"),
        ]
        for table, column, value in mutations:
            with self.subTest(column=column, value=value):
                raw = self.fresh()
                raw[table].loc[0, column] = value
                cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
                self.assertIn(2, rejected[table].dq_source_record.tolist())
                self.assertEqual(rejected[table].iloc[0][column], value)
                self.check_balance(cleaned, rejected, report)

    def test_missing_required_column_quarantines_entire_table(self):
        raw = self.fresh()
        raw["customers"] = raw["customers"].drop(columns="segment")
        cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
        self.assertTrue(cleaned["customers"].empty)
        self.assertEqual(len(rejected["customers"]), len(raw["customers"]))
        self.assertTrue(report["schema_issues"]["customers"])
        self.assertFalse(report["ready_for_analysis"])
        self.assertTrue(cleaned["tickets"].empty)
        self.check_balance(cleaned, rejected, report)

    def test_missing_foreign_keys_propagate(self):
        raw = self.fresh()
        raw["agents"].loc[0, "team_id"] = "TM99"
        invalid_agent = raw["agents"].iloc[0].agent_id
        cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
        self.assertIn(invalid_agent, set(rejected["agents"].agent_id))
        self.assertNotIn(invalid_agent, set(cleaned["tickets"].current_agent_id))
        self.assertNotIn(invalid_agent, set(cleaned["assignment_history"].agent_id))
        validate_data(cleaned, SNAPSHOT)
        self.check_balance(cleaned, rejected, report)

    def test_bad_history_quarantines_ticket_and_dependent_rows(self):
        raw = self.fresh()
        ticket = raw["assignment_history"].iloc[0].ticket_id
        raw["assignment_history"].loc[0, "assigned_at"] = "2026-01-01T00:00:00Z"
        cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
        self.assertNotIn(ticket, set(cleaned["tickets"].ticket_id))
        self.assertFalse(cleaned["assignment_history"].ticket_id.eq(ticket).any())
        self.assertFalse(cleaned["customer_feedback"].ticket_id.eq(ticket).any())
        self.assertIn(ticket, set(rejected["tickets"].ticket_id))
        self.check_balance(cleaned, rejected, report)

    def test_bad_feedback_does_not_remove_valid_ticket(self):
        for column, value in [("csat_score", "6"), ("csat_score", "4.5"), ("csat_score", ""),
                              ("customer_id", "CU99999"), ("submitted_at", "2020-01-01T00:00:00Z")]:
            with self.subTest(column=column, value=value):
                raw = self.fresh()
                ticket = raw["customer_feedback"].iloc[0].ticket_id
                raw["customer_feedback"].loc[0, column] = value
                cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
                self.assertIn(ticket, set(cleaned["tickets"].ticket_id))
                self.assertEqual(report["tables"]["tickets"]["rejected"], 0)
                self.assertEqual(len(rejected["customer_feedback"]), 1)

    def test_completed_ticket_requires_resolution(self):
        raw = self.fresh()
        index = raw["tickets"].index[raw["tickets"].status.eq("Closed")][0]
        raw["tickets"].loc[index, "resolved_at"] = ""
        _, rejected, _, _ = clean_frames(raw, SNAPSHOT)
        self.assertIn(index + 2, rejected["tickets"].dq_source_record.tolist())

    def test_output_report_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            before = {p.name: p.read_bytes() for p in self.source.iterdir()}
            report = clean_directory(self.source, base / "cleaned", base / "quarantine", base / "reports" / "quality.json")
            self.assertEqual(report["total_rejected"], 0)
            self.assertTrue(report["source_files_unchanged"])
            self.assertTrue(report["source_manifest_matches"])
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.source.iterdir()})
            self.assertEqual(json.loads((base / "reports" / "quality.json").read_text())["total_accepted"], report["total_input"])
            self.assertTrue((base / "reports" / "quality.md").is_file())
            self.assertTrue((base / "quarantine" / "normalization_audit.csv").is_file())
            for name in self.raw:
                self.assertTrue(pd.read_csv(base / "quarantine" / f"{name}.csv").empty)

    def test_prevent_source_overwrite(self):
        with self.assertRaisesRegex(ValueError, "separate from source"):
            clean_directory(self.source, self.source)

    def test_schema_errors_in_each_table_are_reported(self):
        for name, frame in self.raw.items():
            with self.subTest(table=name):
                raw = self.fresh()
                raw[name] = frame.drop(columns=frame.columns[-1])
                cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
                self.assertEqual(len(rejected[name]), len(frame))
                self.assertTrue(report["schema_issues"][name])
                self.check_balance(cleaned, rejected, report)

    def test_extra_columns_preserve_source_values_even_with_audit_name_collision(self):
        raw = self.fresh()
        raw["customer_feedback"]["dq_source_record"] = "original extra value"
        cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT)
        self.assertTrue(cleaned["customer_feedback"].empty)
        self.assertEqual(rejected["customer_feedback"].iloc[0].dq_source_record, "original extra value")
        self.assertEqual(report["tables"]["customer_feedback"]["quarantine_metadata_columns"]["source_record"], "_dq_source_record")

    def test_csv_structure_failures_do_not_publish_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            for path in self.source.iterdir():
                (source / path.name).write_bytes(path.read_bytes())
            path = source / "customers.csv"
            path.write_text(path.read_text() + "too,few,fields\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed CSV record"):
                clean_directory(source, base / "cleaned", base / "quarantine", base / "reports" / "quality.json")
            self.assertFalse((base / "cleaned").exists())
            self.assertFalse((base / "reports").exists())

    def test_source_manifest_differences_are_reported_and_bad_rows_quarantined(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            for path in self.source.iterdir():
                (source / path.name).write_bytes(path.read_bytes())
            frame = self.raw["customer_feedback"].copy()
            frame.loc[0, "csat_score"] = "99"
            frame.to_csv(source / "customer_feedback.csv", index=False, lineterminator="\n")
            report = clean_directory(source, base / "cleaned", base / "quarantine", base / "reports" / "quality.json")
            self.assertFalse(report["source_manifest_matches"])
            self.assertTrue(report["source_files_unchanged"])
            self.assertEqual(report["total_rejected"], 1)
            self.assertEqual(pd.read_csv(base / "quarantine" / "customer_feedback.csv").iloc[0].csat_score, 99)
            self.assertEqual(report["tables"]["tickets"]["rejected"], 0)

    def test_full_delivered_dataset(self):
        raw, schemas = read_sources(DEFAULT_OUTPUT)
        cleaned, rejected, _, report = clean_frames(raw, SNAPSHOT, schemas)
        self.assertEqual(len(cleaned["tickets"]), 10_000)
        self.assertEqual(report["total_rejected"], 0)
        self.assertEqual(report["unresolved_tickets_with_null_resolution"], 1136)
        self.check_balance(cleaned, rejected, report)


if __name__ == "__main__":
    unittest.main()
