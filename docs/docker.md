# Docker and Docker Compose

The Compose stack defines PostgreSQL, FastAPI, Django REST Framework, Airflow initialization, the Airflow webserver, and the Airflow scheduler. All containers use the default Compose network and reach PostgreSQL by the service name `postgres`. Docker was unavailable in the development environment, so no image build or container execution is claimed.

## Files and responsibilities

| File/service | Responsibility |
| --- | --- |
| `docker/postgres/Dockerfile` | PostgreSQL image with first-volume initialization scripts |
| `postgres` | Persistent shared support database plus separate Airflow metadata database |
| `docker/fastapi/Dockerfile` / `fastapi` | Read-only aggregate analytics API on port 8000 |
| `docker/django/Dockerfile` / `django` | Read-only operational ticket API on port 8001 |
| `docker/airflow/Dockerfile` | Airflow image with only the pipeline's Python data dependencies |
| `airflow-init` | One-time metadata migration and admin-user creation |
| `airflow-webserver` | Airflow UI/API on port 8080 |
| `airflow-scheduler` | LocalExecutor scheduling plus scheduler health server |

The PostgreSQL named volume `postgres_data` persists both databases. `airflow_logs` persists task logs. `pipeline_processed` and `pipeline_reports` preserve cleaning outputs and reports across one-off FastAPI jobs and Airflow tasks. The API images and default Airflow container use UID 50000 so those volumes remain writable across services. The repository is mounted into Airflow workers so the DAG can call existing modules; the two nested pipeline volumes override its processed-data and report paths.

## Environment setup

Copy the template and replace every `change-me` value:

```powershell
Copy-Item .env.docker.example .env.docker
```

Never commit `.env.docker`. The Compose file requires PostgreSQL, Django, and Airflow admin secrets instead of silently using production-like defaults.

## Validate and start

With Docker Desktop or Docker Engine running:

```powershell
docker compose --env-file .env.docker config
docker compose --env-file .env.docker build
docker compose --env-file .env.docker up -d postgres
docker compose --env-file .env.docker up airflow-init
docker compose --env-file .env.docker up -d fastapi django airflow-webserver airflow-scheduler
docker compose --env-file .env.docker ps
```

On the first empty-volume start, PostgreSQL creates `customer_support_analytics` and `airflow`, then installs the support schema and reporting views. It does not silently load CSV rows. Load the validated dataset explicitly:

```powershell
docker compose --env-file .env.docker run --rm fastapi python -m scripts.clean_data
docker compose --env-file .env.docker run --rm fastapi python -m scripts.load_postgres --replace
docker compose --env-file .env.docker run --rm fastapi python -m scripts.reconcile_reporting --database
```

Alternatively, trigger the Airflow DAG after Airflow is healthy. Do not run the manual loader and DAG load concurrently; the database advisory lock protects correctness, but one will wait.

Endpoints after successful startup:

- FastAPI readiness: `http://localhost:8000/health/ready`
- FastAPI documentation: `http://localhost:8000/docs`
- Django tickets: `http://localhost:8001/api/v1/tickets/`
- Airflow: `http://localhost:8080`

Host ports can be changed in `.env.docker`; inter-container ports and service names stay unchanged.

## Health and logs

PostgreSQL uses `pg_isready` against the analytics database. FastAPI calls its database readiness endpoint. Django performs a one-row ticket-list request. Airflow checks the webserver and scheduler health endpoints. Services wait for PostgreSQL health, and Airflow runtime services wait for successful `airflow-init` completion.

```powershell
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail 200 postgres
docker compose --env-file .env.docker logs -f fastapi django
docker compose --env-file .env.docker logs -f airflow-webserver airflow-scheduler
```

Avoid posting logs publicly because connection metadata and operational identifiers may appear even though this project uses synthetic records.

## Shutdown and reset

Stop containers while preserving PostgreSQL data and Airflow logs:

```powershell
docker compose --env-file .env.docker down
```

Before a destructive reset, create a recoverable database backup:

```powershell
docker compose --env-file .env.docker exec -T postgres pg_dump -U postgres -d customer_support_analytics -Fc -f /tmp/customer_support.dump
docker compose --env-file .env.docker cp postgres:/tmp/customer_support.dump ./customer_support.dump
```

The following command permanently deletes only this Compose project's named PostgreSQL, Airflow-log, processed-data, and report volumes. Verify the project name shown by `docker compose ... config` and confirm the database backup exists before running it. Processed files and reports can be regenerated from the tracked synthetic source, but will still be removed:

```powershell
docker compose --env-file .env.docker down --volumes --remove-orphans
```

Recreate the stack with the startup commands. PostgreSQL initialization scripts run only when `postgres_data` is empty; changing an init script does not modify an existing volume.

## Validation performed in this repository

`tests/test_docker_config.py` parses `compose.yaml` with PyYAML and checks required services, named volumes, service-name networking, environment-variable secrets, health checks, dependency conditions, image entrypoints, non-root API users, and database initialization order.

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_docker_config -v
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

This static validation cannot replace `docker compose config`, image builds, health transitions, or endpoint smoke tests. Those commands remain required on a Docker-enabled host.
