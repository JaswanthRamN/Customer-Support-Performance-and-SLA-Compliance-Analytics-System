"""Pure-Python orchestration and static DAG contracts; Airflow is optional."""

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestration import airflow_tasks
from scripts.generate_synthetic_data import ROOT, TABLES


class AirflowTaskTests(unittest.TestCase):
    def test_data_availability_accepts_complete_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            row_counts = {name: 1 for name in TABLES}
            (source / "metadata.json").write_text(json.dumps({"row_counts": row_counts}), encoding="utf-8")
            for name in TABLES:
                (source / f"{name}.csv").write_text("header\n", encoding="utf-8")
            result = airflow_tasks.check_data_availability(source)
            self.assertEqual(result["files"], 7)
            self.assertEqual(result["expected_rows"], 6)

    def test_data_availability_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                airflow_tasks.check_data_availability(directory)

    @patch("orchestration.airflow_tasks.validate_directory", return_value=["one", "two"])
    def test_validation_reuses_existing_module(self, validate):
        self.assertEqual(airflow_tasks.validate_source("source"), {"validation_checks": 2})
        validate.assert_called_once_with("source")

    @patch("orchestration.airflow_tasks.clean_directory")
    def test_cleaning_requires_ready_report(self, clean):
        clean.return_value = {"ready_for_analysis": True, "total_accepted": 10,
                              "total_rejected": 1}
        result = airflow_tasks.clean_source("raw", "clean", "bad", "report.json")
        self.assertEqual(result["accepted"], 10)
        clean.assert_called_once_with("raw", "clean", "bad", "report.json")

    @patch("orchestration.airflow_tasks.preflight")
    def test_load_preflight_reuses_loader(self, preflight):
        preflight.return_value = {"analysis_as_of": "snapshot",
                                  "expected_row_counts": {name: 1 for name in TABLES}}
        result = airflow_tasks.validate_load_inputs("clean", "quality")
        self.assertEqual(len(result["expected_row_counts"]), 6)
        preflight.assert_called_once_with("clean", "quality")

    @patch("orchestration.airflow_tasks.load_database")
    def test_database_load_is_idempotent_replace(self, load):
        load.return_value = {"database_loaded": True,
                             "database_row_counts": {name: 1 for name in TABLES},
                             "replaced_existing_rows": True}
        result = airflow_tasks.load_postgres_idempotent("clean", "quality")
        self.assertTrue(result["database_loaded"])
        load.assert_called_once_with("clean", "quality", replace=True)

    @patch("orchestration.airflow_tasks.reconcile_reporting")
    def test_post_load_requires_database_match(self, reconcile):
        reconcile.return_value = {"database_compared": True, "database_match": True}
        result = airflow_tasks.post_load_checks("result.json")
        self.assertTrue(result["database_match"])
        reconcile.assert_called_once_with(report_path="result.json", compare_database=True)

    def test_dag_source_has_dependencies_retries_and_timeouts(self):
        source_path = ROOT / "dags" / "customer_support_pipeline.py"
        source = source_path.read_text(encoding="utf-8")
        ast.parse(source)
        for value in [
            "check_data_availability", "validate_source_data", "clean_and_quarantine",
            "validate_load_inputs", "load_postgresql_idempotently", "post_load_reconciliation",
            "max_active_runs=1", "execution_timeout", "retry_exponential_backoff",
            "availability() >> validate() >> clean() >> load_preflight() >> load() >> reconcile()",
        ]:
            self.assertIn(value, source)


if __name__ == "__main__":
    unittest.main()
