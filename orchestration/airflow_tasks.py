"""Testable task callables reused by the Apache Airflow DAG."""

import json
import logging
import os
from pathlib import Path

from scripts.clean_data import (DEFAULT_CLEAN, DEFAULT_QUARANTINE, DEFAULT_REPORT,
                                clean_directory)
from scripts.generate_synthetic_data import DEFAULT_OUTPUT, ROOT, TABLES
from scripts.load_postgres import load_database, preflight
from scripts.reconcile_reporting import run as reconcile_reporting
from scripts.validate_synthetic_data import validate_directory

logger = logging.getLogger(__name__)


def check_data_availability(source=DEFAULT_OUTPUT):
    """Fail before expensive tasks when a required source artifact is absent or empty."""
    source = Path(source)
    required = [source / "metadata.json", *(source / f"{name}.csv" for name in TABLES)]
    missing = [path.name for path in required if not path.is_file()]
    empty = [path.name for path in required if path.is_file() and path.stat().st_size == 0]
    if missing or empty:
        raise FileNotFoundError(f"Source availability failed; missing={missing}, empty={empty}")
    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    expected_tables = set(TABLES)
    if set(metadata.get("row_counts", {})) != expected_tables:
        raise ValueError("Source metadata row_counts does not contain the six required tables")
    result = {"source": str(source.resolve()), "files": len(required),
              "expected_rows": sum(metadata["row_counts"].values())}
    logger.info("Source data available: files=%s expected_rows=%s",
                result["files"], result["expected_rows"])
    return result


def validate_source(source=DEFAULT_OUTPUT):
    checks = validate_directory(source)
    logger.info("Source validation passed: checks=%s", len(checks))
    return {"validation_checks": len(checks)}


def clean_source(source=DEFAULT_OUTPUT, output=DEFAULT_CLEAN,
                 quarantine=DEFAULT_QUARANTINE, report_path=DEFAULT_REPORT):
    report = clean_directory(source, output, quarantine, report_path)
    if not report["ready_for_analysis"]:
        raise ValueError("Cleaned dataset is not ready for analysis")
    logger.info("Cleaning complete: accepted=%s rejected=%s",
                report["total_accepted"], report["total_rejected"])
    return {"accepted": report["total_accepted"], "rejected": report["total_rejected"],
            "quality_report": str(Path(report_path).resolve())}


def validate_load_inputs(directory=DEFAULT_CLEAN, quality_path=DEFAULT_REPORT):
    result = preflight(directory, quality_path)
    logger.info("PostgreSQL load preflight passed: tables=%s",
                len(result["expected_row_counts"]))
    return {"analysis_as_of": result["analysis_as_of"],
            "expected_row_counts": result["expected_row_counts"]}


def load_postgres_idempotent(directory=DEFAULT_CLEAN, quality_path=DEFAULT_REPORT):
    """Transactionally replace only the six project tables with validated deterministic files."""
    result = load_database(directory, quality_path, replace=True)
    logger.info("PostgreSQL load complete: rows=%s", sum(result["database_row_counts"].values()))
    return {"database_loaded": result["database_loaded"],
            "database_row_counts": result["database_row_counts"],
            "replaced_existing_rows": result["replaced_existing_rows"]}


def post_load_checks(report_path=None):
    if report_path is None:
        report_directory = Path(os.getenv("AIRFLOW_PIPELINE_REPORT_DIR", ROOT / "reports" / "airflow"))
        report_path = report_directory / "post_load_reconciliation.json"
    report = reconcile_reporting(report_path=report_path, compare_database=True)
    if not report["database_compared"] or not report["database_match"]:
        raise ValueError("Post-load SQL/Python reconciliation did not match")
    logger.info("Post-load reconciliation passed: report=%s", Path(report_path).resolve())
    return {"database_match": True, "report": str(Path(report_path).resolve())}
