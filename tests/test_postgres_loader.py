"""Loader checks that run without a local PostgreSQL server."""

from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts.generate_synthetic_data import ROOT, TABLES
from scripts.load_postgres import LOAD_ORDER, copy_table, db_config, load_database, preflight
from scripts.sla import POLICIES


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.row = None
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=None):
        statement = query.as_string() if hasattr(query, "as_string") else str(query)
        if "pg_advisory_xact_lock" in statement:
            self.connection.actions.append("lock")
        elif "CREATE SCHEMA" in statement:
            self.connection.actions.append("schema")
        elif "CREATE OR REPLACE VIEW support_analytics.vw_ticket_metrics" in statement:
            self.connection.actions.append("views")
        elif statement.startswith("SELECT COUNT(*) FROM"):
            for name in TABLES:
                if statement.endswith(f'"{name}"'):
                    self.row = (self.connection.existing.get(name, 0),)
                    return
            raise AssertionError(statement)
        elif statement.startswith("TRUNCATE TABLE"):
            self.connection.actions.append("truncate")
        elif params is not None and "ordered_assignments" in statement:
            expected = json.loads((ROOT / "reports" / "data_quality_report.json").read_text())
            values = {name: expected["tables"][name]["accepted"] for name in TABLES}
            values.update({"invalid_customer_chronology": self.connection.anomaly})
            self.description = [SimpleNamespace(name=name) for name in values]
            self.row = tuple(values.values())
            self.connection.actions.append("validate")
        else:
            raise AssertionError(statement[:100])

    def fetchone(self):
        return self.row

    @contextmanager
    def copy(self, command):
        statement = command.as_string()
        name = next((name for name in TABLES if f'"{name}"' in statement), None)
        if name is None:
            raise AssertionError(statement)
        self.connection.actions.append(name)
        chunks = []

        class Sink:
            def write(self, text):
                chunks.append(text)

        yield Sink()
        self.connection.copied[name] = "".join(chunks)


class FakeConnection:
    def __init__(self, existing=None, anomaly=0):
        self.existing = existing or {}
        self.anomaly = anomaly
        self.actions = []
        self.copied = {}
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exception_type, *_):
        self.committed = exception_type is None
        return False

    def cursor(self):
        return FakeCursor(self)


class PostgresLoaderTests(unittest.TestCase):
    def test_database_policy_seed_matches_shared_configuration(self):
        schema = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
        for priority, (response_minutes, resolution_minutes) in POLICIES.items():
            self.assertIn(f"('{priority}', {response_minutes}, {resolution_minutes},", schema)

    def test_preflight_matches_cleaned_csvs_and_metadata(self):
        result = preflight()
        self.assertFalse(result["database_loaded"])
        self.assertEqual(result["expected_row_counts"]["tickets"], 10_000)
        self.assertEqual(result["expected_row_counts"]["assignment_history"], 14_035)
        self.assertEqual(len(result["python_validation_checks"]), 7)

    def test_missing_configuration_fails_without_a_connection(self):
        with self.assertRaisesRegex(ValueError, "PGHOST, PGDATABASE, PGUSER"):
            db_config({})
        with self.assertRaisesRegex(ValueError, "PGPORT"):
            db_config({"PGHOST": "localhost", "PGDATABASE": "db", "PGUSER": "user", "PGPORT": "bad"})
        with self.assertRaisesRegex(ValueError, "PGSSLMODE"):
            db_config({"PGHOST": "localhost", "PGDATABASE": "db", "PGUSER": "user", "PGSSLMODE": "unknown"})

    def test_preflight_rejects_modified_cleaned_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = ROOT / "data" / "processed" / "cleaned"
            destination = Path(temporary)
            for name in TABLES:
                path = source / f"{name}.csv"
                (destination / path.name).write_bytes(path.read_bytes())
            target = destination / "teams.csv"
            target.write_bytes(target.read_bytes().replace(b"Billing Support", b"Billing Services"))
            with self.assertRaisesRegex(ValueError, "checksums"):
                preflight(destination)

    def test_copy_uses_exact_header_and_file_contents(self):
        fake = FakeConnection()
        path = ROOT / "data" / "processed" / "cleaned" / "teams.csv"
        copy_table(FakeCursor(fake), "teams", path)
        self.assertEqual(fake.copied["teams"], path.read_text(encoding="utf-8"))
        self.assertTrue(fake.copied["teams"].startswith("team_id,team_name,specialization\n"))

    def test_dependency_order_and_transaction_success(self):
        fake = FakeConnection()
        env = {"PGHOST": "localhost", "PGDATABASE": "demo", "PGUSER": "analyst"}
        with patch.dict("os.environ", env, clear=True):
            result = load_database(connect=lambda **_: fake)
        self.assertTrue(result["database_loaded"])
        self.assertTrue(fake.committed)
        self.assertEqual(fake.actions, ["lock", "schema", *LOAD_ORDER, "views", "validate"])
        self.assertEqual(result["database_row_counts"], result["expected_row_counts"])

    def test_nonempty_tables_refuse_implicit_replacement(self):
        fake = FakeConnection(existing={"tickets": 1})
        env = {"PGHOST": "localhost", "PGDATABASE": "demo", "PGUSER": "analyst"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "--replace"):
                load_database(connect=lambda **_: fake)
        self.assertFalse(fake.committed)
        self.assertFalse(fake.copied)

    def test_explicit_replacement_is_scoped_and_validated(self):
        fake = FakeConnection(existing={"tickets": 1})
        env = {"PGHOST": "localhost", "PGDATABASE": "demo", "PGUSER": "analyst"}
        with patch.dict("os.environ", env, clear=True):
            result = load_database(replace=True, connect=lambda **_: fake)
        self.assertTrue(fake.committed)
        self.assertTrue(result["replaced_existing_rows"])
        self.assertEqual(fake.actions, ["lock", "schema", "truncate", *LOAD_ORDER, "views", "validate"])

    def test_relationship_anomaly_rolls_back(self):
        fake = FakeConnection(anomaly=1)
        env = {"PGHOST": "localhost", "PGDATABASE": "demo", "PGUSER": "analyst"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "relationship validation failed"):
                load_database(connect=lambda **_: fake)
        self.assertFalse(fake.committed)


if __name__ == "__main__":
    unittest.main()
