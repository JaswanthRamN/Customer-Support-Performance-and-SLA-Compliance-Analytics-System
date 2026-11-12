# Data Pipeline and Orchestration

## End-to-end stages

1. **Availability:** confirm all six CSVs and metadata exist.
2. **Validation:** check schemas, required values, categories, IDs, checksums, lifecycle timestamps, foreign keys, assignment intervals, SLA derivations, and feedback rules.
3. **Cleaning:** normalize accepted values, preserve legitimate nulls, and quarantine invalid rows with original values and reasons.
4. **Load preflight:** compare cleaned counts and checksums with quality metadata before opening a database connection.
5. **PostgreSQL load:** acquire an advisory lock, load tables in dependency order inside one transaction, and validate counts and relationships.
6. **Post-load reconciliation:** compare reporting views with an independent Python baseline.
7. **Consumption:** serve reporting views through FastAPI and Power BI while Django exposes ticket-level records.

## Airflow DAG

`dags/customer_support_pipeline.py` orchestrates reusable functions from `orchestration/airflow_tasks.py`; it does not duplicate data-processing logic. Dependencies enforce availability before validation, validation before cleaning, cleaning before loading, and loading before post-load checks.

The DAG defines retries, execution timeouts, logging, and idempotent explicit replacement for repeatable portfolio runs. Replacement is protected by the loader transaction and advisory lock. Do not trigger manual and scheduled replacement loads concurrently.

## Local module execution

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_synthetic_data
.\.venv\Scripts\python.exe -m scripts.clean_data
.\.venv\Scripts\python.exe -m scripts.load_postgres --check-only
.\.venv\Scripts\python.exe -m scripts.load_postgres --replace
.\.venv\Scripts\python.exe -m scripts.reconcile_reporting --database
```

Use `--replace` only after confirming the target database and intended dataset. The loader does not silently replace populated tables.

## Operational checks

- Row counts after loading must equal cleaned accepted counts.
- Every foreign key must resolve.
- Each ticket must have exactly one current assignment matching its current owner.
- Reporting ticket grain must remain unique after views are installed.
- SQL/Python reconciliation must finish with `database_compared: true` and `database_match: true`.
- Failed validation or reconciliation must stop downstream work rather than publish partial outputs.

The practical Airflow path is the Compose stack. Detailed commands are in [the Airflow guide](airflow_pipeline.md) and [Docker guide](docker.md). Source and task tests do not prove that Airflow imported, scheduled, or executed the DAG; record a real run before claiming execution.
