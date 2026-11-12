# Testing and Validation

## Automated suite

Run all tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers generation reproducibility, schemas, lifecycle rules, foreign keys, cleaning and quarantine behavior, SLA boundaries, EDA denominators, PostgreSQL loader transactions, reporting grain, API validation, Airflow task behavior, Docker configuration, and Power BI source assets.

The latest documented audit ran 90 tests: 90 passed, 0 failed, and 0 skipped. Test counts can change as the project evolves; use current command output as the authoritative result.

## Layer-specific checks

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_synthetic_data
.\.venv\Scripts\python.exe -m scripts.clean_data
.\.venv\Scripts\python.exe -m scripts.eda
.\.venv\Scripts\python.exe -m scripts.load_postgres --check-only
.\.venv\Scripts\python.exe -m scripts.reconcile_reporting
.\.venv\Scripts\python.exe ticket_service/manage.py check
```

## Live database acceptance

After loading a PostgreSQL database, run:

```powershell
.\.venv\Scripts\python.exe -m scripts.reconcile_reporting --database
psql -v ON_ERROR_STOP=1 -f sql/validation.sql
psql -v ON_ERROR_STOP=1 -f sql/power_bi_reconciliation.sql
```

The `--database` command is the authoritative SQL-to-Python comparison. A report with `database_compared: false` is only a Python baseline and must not be described as an observed SQL match.

## External-runtime acceptance

Automated API tests use controlled test doubles without PostgreSQL. On a loaded database, compare FastAPI aggregates with reporting views and Django ticket/detail/history values with source rows. Static Docker and Airflow tests do not build images or execute a DAG; render and build Compose, then inspect a complete DAG run. Static Power BI tests do not execute Desktop; refresh the model and reconcile cards with SQL before presenting it.

## Status vocabulary

- **Passed:** the check executed and met its assertion.
- **Failed:** the check executed and did not meet its assertion.
- **Skipped:** the test runner collected the check but intentionally skipped it.
- **Not run:** required software, credentials, or services were unavailable, so execution never occurred.

See the [dated audit](end_to_end_audit.md) for recorded evidence and environmental limitations.
