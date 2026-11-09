# Apache Airflow Data Pipeline

The DAG in `dags/customer_support_pipeline.py` orchestrates the existing project modules rather than duplicating their validation, cleaning, loading, or reconciliation logic. Airflow was not installed in the delivered development environment, so no DAG execution is claimed.

## Task sequence

| Order | Airflow task | Reused project function | Purpose |
| ---: | --- | --- | --- |
| 1 | `check_data_availability` | `orchestration.airflow_tasks.check_data_availability` | Require metadata plus all six non-empty source CSVs |
| 2 | `validate_source_data` | `scripts.validate_synthetic_data.validate_directory` | Verify schema, IDs, relationships, timestamps, SLA logic, row counts, and checksums |
| 3 | `clean_and_quarantine` | `scripts.clean_data.clean_directory` | Rebuild cleaned/quarantine outputs and the quality report |
| 4 | `validate_load_inputs` | `scripts.load_postgres.preflight` | Recheck cleaned checksums, counts, and relationships before connecting |
| 5 | `load_postgresql_idempotently` | `scripts.load_postgres.load_database` | Transactionally replace only the six project tables and recreate reporting views |
| 6 | `post_load_reconciliation` | `scripts.reconcile_reporting.run` | Compare independent Pandas results with PostgreSQL reporting views |

The dependency chain is deliberately sequential because each stage validates artifacts produced by the preceding stage. Tasks return only small metadata dictionaries through XCom, never DataFrames or CSV contents.

## Idempotency and concurrency

The load calls `load_database(..., replace=True)`. That loader validates every cleaned file before connecting, obtains a PostgreSQL transaction-level advisory lock, truncates only the six project tables, loads them in dependency order, rebuilds reporting views, validates row counts and foreign-key relationships, and commits once. A failure rolls back the entire transaction. Repeating a run against the same deterministic cleaned files produces the same database state.

The DAG sets `max_active_runs=1`, while the database advisory lock protects against other loader processes. The load task has one retry; all other tasks inherit two retries with exponential backoff from five to thirty minutes. Task execution timeouts range from five to forty-five minutes, and the whole run is capped at two hours.

## Environment configuration

Airflow workers need:

- Repository dependencies from `requirements.txt`.
- A separately installed Apache Airflow distribution compatible with the worker's Python version, installed using the official Airflow constraints for that exact version.
- `AIRFLOW_PROJECT_ROOT` pointing to this repository if the DAG is copied elsewhere.
- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, optional `PGPASSWORD`, and `PGSSLMODE`.
- Optional `AIRFLOW_SUPPORT_SCHEDULE`; default is daily at 06:00 UTC.
- Optional `AIRFLOW_PIPELINE_REPORT_DIR`; default is `reports/airflow` under the repository.

Use a database role allowed to load the six project tables and recreate reporting views. Store credentials in an Airflow secrets backend or injected environment, not in the DAG or repository.

## Running in Airflow

1. Create a dedicated Airflow environment and initialize Airflow according to its installed version.
2. Make the repository importable on every scheduler and worker. Either point Airflow's DAG folder at `dags/`, or copy the DAG and set `AIRFLOW_PROJECT_ROOT` to the repository.
3. Configure the PostgreSQL environment variables on scheduler and workers.
4. Confirm the source files and `metadata.json` are available at the same absolute repository path on every worker.
5. Run Airflow's DAG import/list command and confirm `customer_support_analytics_pipeline` has no import error.
6. Trigger one manual run before enabling the daily schedule.
7. Inspect task logs in order. Do not enable the schedule until post-load reconciliation reports a database match.

Exact CLI commands differ between Airflow releases and deployment modes; use the commands supplied by the installed Airflow version rather than assuming this repository installed Airflow.

## Validation without Airflow

The orchestration callables and DAG source contracts can be tested without importing Airflow:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_airflow_pipeline -v
```

These tests verify source availability failures, reuse of existing validators and cleaner, preflight reuse, `replace=True` loading, required database reconciliation, DAG syntax, dependency order, retries, timeouts, and single-run concurrency. They mock database and file-mutating boundaries, so they do not claim a PostgreSQL load or Airflow execution.

With PostgreSQL configured, separately run the existing loader and reconciliation commands before the first DAG deployment. In an Airflow-enabled environment, validate the imported DAG, trigger a manual run, confirm all six tasks succeed, and inspect the generated post-load reconciliation report.
