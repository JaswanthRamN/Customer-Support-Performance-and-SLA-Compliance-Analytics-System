"""Validate and COPY cleaned support CSVs into PostgreSQL in one transaction."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import psycopg
from psycopg import sql

from scripts.generate_synthetic_data import ROOT, TABLES
from scripts.validate_synthetic_data import SCHEMAS, load_data, validate_data

DEFAULT_INPUT = ROOT / "data" / "processed" / "cleaned"
DEFAULT_QUALITY = ROOT / "reports" / "data_quality_report.json"
SCHEMA_SQL = ROOT / "sql" / "schema.sql"
VALIDATION_SQL = ROOT / "sql" / "validation.sql"
SCHEMA = "support_analytics"
LOAD_ORDER = ("customers", "teams", "agents", "tickets", "assignment_history", "customer_feedback")


def db_config(environ=None):
    """Read libpq-compatible settings without putting secrets in code or logs."""
    env = os.environ if environ is None else environ
    missing = [name for name in ("PGHOST", "PGDATABASE", "PGUSER") if not env.get(name)]
    if missing:
        raise ValueError("Missing database environment variables: " + ", ".join(missing))
    try:
        port = int(env.get("PGPORT", "5432"))
    except ValueError as error:
        raise ValueError("PGPORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("PGPORT must be between 1 and 65535")
    config = {"host": env["PGHOST"], "port": port, "dbname": env["PGDATABASE"],
              "user": env["PGUSER"], "connect_timeout": 10}
    if env.get("PGPASSWORD"):
        config["password"] = env["PGPASSWORD"]
    if env.get("PGSSLMODE"):
        if env["PGSSLMODE"] not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
            raise ValueError("Invalid PGSSLMODE")
        config["sslmode"] = env["PGSSLMODE"]
    return config


def preflight(directory=DEFAULT_INPUT, quality_path=DEFAULT_QUALITY):
    """Check the exact cleaned files, row counts, snapshot, and relationships."""
    directory = Path(directory)
    quality = json.loads(Path(quality_path).read_text(encoding="utf-8"))
    if not quality.get("ready_for_analysis"):
        raise ValueError("Data-quality report is not ready; run the cleaner first")
    expected_hashes = quality.get("cleaned_sha256")
    if not expected_hashes or set(expected_hashes) != {f"{name}.csv" for name in TABLES}:
        raise ValueError("Data-quality report lacks the six cleaned CSV checksums")
    hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in expected_hashes}
    if hashes != expected_hashes:
        raise ValueError("Cleaned CSV checksums differ from the data-quality report")
    for name in TABLES:
        with (directory / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
        if header != SCHEMAS[name].split():
            raise ValueError(f"{name}.csv has the wrong column order or names")
    data = load_data(directory)
    snapshot = pd.Timestamp(quality["analysis_as_of"])
    if snapshot.tzinfo is None:
        raise ValueError("analysis_as_of must have a timezone")
    checks = validate_data(data, snapshot)
    counts = {name: len(data[name]) for name in TABLES}
    expected = {name: quality["tables"][name]["accepted"] for name in TABLES}
    if counts != expected:
        raise ValueError(f"Cleaned row counts differ from the quality report: {counts} != {expected}")
    return {"analysis_as_of": snapshot.isoformat(), "schema": SCHEMA, "expected_row_counts": counts,
            "csv_sha256": hashes, "python_validation_checks": checks, "database_loaded": False}


def copy_table(cursor, table, csv_path):
    columns = SCHEMAS[table].split()
    command = sql.SQL("COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')").format(
        sql.Identifier(SCHEMA), sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns)))
    with cursor.copy(command) as copy:
        with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
            while chunk := handle.read(1024 * 1024):
                copy.write(chunk)


def load_database(directory=DEFAULT_INPUT, quality_path=DEFAULT_QUALITY, replace=False, connect=None):
    result = preflight(directory, quality_path)
    config = db_config()
    connector = connect or psycopg.connect
    # The context rolls back schema/COPY work on any failure and commits only
    # after counts and relationship checks pass. An advisory lock serializes loads.
    with connector(**config) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('support_analytics_load'))")
            cursor.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
            tables = sql.SQL(", ").join(sql.SQL("{}.{}").format(sql.Identifier(SCHEMA), sql.Identifier(name))
                                       for name in LOAD_ORDER)
            existing = {}
            for name in LOAD_ORDER:
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier(SCHEMA), sql.Identifier(name)))
                existing[name] = cursor.fetchone()[0]
            if any(existing.values()) and not replace:
                raise ValueError("Target schema already contains rows; use --replace to reload these six tables")
            if replace:
                cursor.execute(sql.SQL("TRUNCATE TABLE {} ").format(tables))
            for name in LOAD_ORDER:
                copy_table(cursor, name, Path(directory) / f"{name}.csv")
            cursor.execute(VALIDATION_SQL.read_text(encoding="utf-8"), (result["analysis_as_of"],))
            columns = [item.name for item in cursor.description]
            findings = dict(zip(columns, cursor.fetchone()))
            counts = {name: findings[name] for name in TABLES}
            anomalies = {key: value for key, value in findings.items() if key not in TABLES}
            if counts != result["expected_row_counts"]:
                raise ValueError(f"Database row counts differ from cleaned CSVs: {counts} != {result['expected_row_counts']}")
            if any(anomalies.values()):
                raise ValueError(f"Database relationship validation failed: {anomalies}")
            result.update({"database_loaded": True, "database_row_counts": counts,
                           "database_relationship_anomalies": anomalies, "replaced_existing_rows": bool(replace)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--quality-report", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--check-only", action="store_true", help="validate local CSVs without connecting")
    parser.add_argument("--replace", action="store_true", help="replace rows in only the six project tables")
    parser.add_argument("--report", type=Path, help="output JSON path; defaults by mode under reports/")
    args = parser.parse_args()
    if args.check_only and args.replace:
        parser.error("--check-only and --replace cannot be combined")
    result = preflight(args.input, args.quality_report) if args.check_only else load_database(
        args.input, args.quality_report, args.replace)
    report = args.report or ROOT / "reports" / ("postgres_preflight.json" if args.check_only else "postgres_load_report.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"database_loaded": result["database_loaded"],
                      "row_counts": result.get("database_row_counts", result["expected_row_counts"]),
                      "report": str(report)}, indent=2))


if __name__ == "__main__":
    main()
