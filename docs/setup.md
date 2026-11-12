# Setup Guide

## Prerequisites

- Python 3.11 or newer; Python 3.12 is the delivered and tested runtime.
- PostgreSQL 14 or newer for database-backed SQL, API, and Power BI work.
- Optional: Docker Desktop or Docker Engine with Compose.
- Optional: Power BI Desktop on Windows.
- Optional: Apache Airflow, preferably through the provided Docker image.

## Python environment

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The virtual environment is ignored by Git. Do not commit `.venv`, installed packages, caches, or local editor settings.

## Reproduce the local data workflow

The repository already contains the tracked seed-42 synthetic source. Regeneration is deterministic but overwrites the tracked synthetic CSVs, so use a separate output directory for experiments.

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_synthetic_data
.\.venv\Scripts\python.exe -m scripts.clean_data
.\.venv\Scripts\python.exe -m scripts.eda
.\.venv\Scripts\python.exe -m scripts.load_postgres --check-only
```

Experimental generation:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_synthetic_data --tickets 2000 --seed 7 --output data/raw/experiment
.\.venv\Scripts\python.exe -m scripts.validate_synthetic_data --input data/raw/experiment
```

Cleaned files and quarantine outputs are written below `data/processed/` and are intentionally ignored. Reports intended as portfolio evidence are tracked under `reports/`.

## PostgreSQL configuration

Copy the variable names from `.env.example` into your shell or secret manager. The project reads process environment variables and does not automatically load the file.

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "customer_support_analytics"
$env:PGUSER = "your_postgres_role"
$env:PGPASSWORD = "your-local-secret"
$env:PGSSLMODE = "prefer"
```

Create the schema, generate cleaned files, and load them:

```powershell
psql -v ON_ERROR_STOP=1 -f sql/schema.sql
psql -v ON_ERROR_STOP=1 -f sql/reporting_views.sql
.\.venv\Scripts\python.exe -m scripts.clean_data
.\.venv\Scripts\python.exe -m scripts.load_postgres
.\.venv\Scripts\python.exe -m scripts.reconcile_reporting --database
```

The loader refuses to replace populated business tables unless `--replace` is explicit. Review [the PostgreSQL guide](postgres.md) before using replacement mode.

## Run FastAPI

With PostgreSQL configured and loaded:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`. Readiness is at `/health/ready`.

## Run Django REST Framework

Set a local Django secret and use the same PostgreSQL variables:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-random-local-secret"
.\.venv\Scripts\python.exe ticket_service/manage.py runserver 127.0.0.1:8001
```

Tickets are available at `http://127.0.0.1:8001/api/v1/tickets/`. The shared models are unmanaged; do not run migrations expecting Django to own the analytics tables.

## Docker Compose

Copy `.env.docker.example` to `.env.docker`, replace every `change-me` value, and keep the resulting file untracked.

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker config
docker compose --env-file .env.docker build
docker compose --env-file .env.docker up -d postgres
docker compose --env-file .env.docker up airflow-init
docker compose --env-file .env.docker up -d fastapi django airflow-webserver airflow-scheduler
docker compose --env-file .env.docker ps
```

Database loading is deliberately explicit. Follow [the Docker guide](docker.md) for loading, logs, backups, shutdown, and destructive-reset warnings.

## Power BI

Power BI Desktop setup is manual. Load the M queries, define relationships, add DAX measures, and reconcile the model as described in [the Power BI guide](power_bi.md). The repository does not include a PBIX file.

## Secret handling

- Never commit `.env`, `.env.docker`, database passwords, private keys, API tokens, dumps, or production logs.
- Use a least-privilege read-only database role for both APIs and Power BI.
- The placeholder examples are documentation, not usable production credentials.
- Run the repository checks in [testing](testing.md) before creating a public release.
