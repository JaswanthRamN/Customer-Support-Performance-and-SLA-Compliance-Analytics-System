# End-to-End Project Audit

**Audit date:** 11 November 2026  
**Dataset:** synthetic seed-42 portfolio dataset  
**Analysis snapshot:** 1 July 2026 00:00:00 UTC

## Executive conclusion

The locally executable parts of the project are internally consistent. Source validation, cleaning, exploratory analysis, PostgreSQL load preflight, independent Python reporting calculations, Django configuration checks, Python compilation, and all 90 automated tests passed. No critical data, SLA, metric-grain, or API-contract defect was found during this audit.

PostgreSQL, Docker, Airflow, and Power BI Desktop were not available in the audit environment. Their source configuration and mocked/static tests passed, but live database execution, container health, DAG execution, Power Query refresh, DAX evaluation, and dashboard rendering were **not run**. These are deployment acceptance checks, not passed checks.

## Audit status

| Area | Status | Evidence |
| --- | --- | --- |
| Synthetic generation and reproducibility | Passed | Generator tests cover deterministic frames and byte-identical CSV output for a matching seed, seed sensitivity, required scenarios, and small datasets. The delivered manifest row counts and SHA-256 hashes passed validation. |
| Source data validation | Passed | Schema, required fields, identifiers, categories, timestamps, lifecycle order, ownership intervals, SLA derivation, feedback, row counts, and checksums passed. |
| Cleaning and quarantine behavior | Passed | 30,326 of 30,326 input rows accepted; 0 rejected. Tests also passed for malformed rows, duplicate handling, propagation to child records, legitimate null resolution timestamps, and non-destructive failure behavior. |
| Foreign keys and relationships | Passed | All delivered customer, team, agent, ticket, assignment, and feedback references resolve. Assignment intervals are contiguous; each ticket has one current assignment consistent with its current agent/team. |
| EDA and Python KPIs | Passed | Analysis regenerated from cleaned files: 10,000 tickets and seven charts. Averages, medians, missing feedback, backlog, reassignment, and reopening rules passed tests. |
| PostgreSQL schema and loader | Passed (static/preflight) | Cleaned-file preflight passed for all six tables. Schema and loader tests passed for constraints, dependency order, transactions, idempotent replacement, advisory locking, rollback, and post-load relationship checks. |
| Live PostgreSQL load and SQL execution | Not run | Neither `psql` nor a PostgreSQL server was available. No claim is made that DDL, views, indexes, or queries ran against a live server in this audit. |
| SQL/Python metric reconciliation | Passed (definition/baseline); live comparison not run | Independent Python reporting baseline matches the separately generated EDA baseline and the SQL field definitions covered by tests. `database_compared` remains `false`; view results were not retrieved from PostgreSQL. |
| SLA logic | Passed | Critical 15m/4h, High 1h/8h, Medium 4h/24h, and Low 8h/72h targets agree across configuration, generated data, SQL seed data, and tests. Exact deadline is compliant; a missing event breaches only when snapshot time is strictly after its deadline. |
| FastAPI analytics API | Passed (isolated tests) | Liveness, readiness failure handling, overview, SLA, team performance, response-time, backlog pagination, validation, safe errors, and OpenAPI route exposure passed with test doubles. Live PostgreSQL-backed requests were not run. |
| Django REST Framework API | Passed (isolated tests) | Django system check and list, detail, filters, pagination, assignment history, read-only routing, unmanaged schema mapping, and error tests passed. Live PostgreSQL-backed requests were not run. |
| API consistency | Passed (contract/static) | Both APIs use the same priority/status vocabulary, explicit UTC database-session semantics, current ownership fields, shared PostgreSQL schema, and inclusive created-date range behavior. FastAPI reports ticket-grain aggregates from `vw_ticket_metrics`; Django exposes the underlying ticket and assignment records without creating tables. Live cross-API response comparison was not run. |
| Airflow | Passed (task/source tests); DAG run not run | Availability, validation, cleaning, loader reuse, idempotent replace mode, post-load reconciliation, dependencies, retries, and timeouts passed tests. Airflow is not installed, so DAG parsing by Airflow and task execution were not run. |
| Docker Compose | Passed (static tests); runtime not run | Required services, health checks, dependency conditions, service-name networking, volumes, secrets, entrypoints, non-root users, and initialization order passed six tests. Docker is unavailable, so Compose rendering, builds, startup, and health transitions were not run. |
| Power BI supporting assets | Passed (static tests); Desktop not run | Power Query files, ticket-grain model rules, role-playing dimensions, distinct-count DAX, null handling, UTC snapshot logic, dashboard mappings, and reconciliation SQL passed nine tests. No PBIX exists and no Power BI refresh or visual was run. |
| Python regression suite | Passed | 90 tests ran with 0 failures and 0 errors. |

No audit item failed. Items marked **Not run** require software or services absent from this workstation.

Automated-test totals: **90 passed, 0 failed, 0 skipped**. Infrastructure acceptance checks listed as not run are not counted as skipped tests because they were never collected or executed by the test runner.

## Reconciled baseline metrics

These are synthetic-data observations, not real operational results.

| Metric | Independent Python result | SQL definition expected result |
| --- | ---: | ---: |
| Tickets | 10,000 | 10,000 |
| Answered tickets | 9,796 | 9,796 |
| Mean / median response hours | 2.70 / 1.25 | 2.70 / 1.25 |
| Resolved tickets | 8,864 | 8,864 |
| Mean / median resolution hours | 40.57 / 18.33 | 40.57 / 18.33 |
| Response SLA met / breached / pending | 8,013 / 1,976 / 11 | 8,013 / 1,976 / 11 |
| Response SLA compliance | 80.22% | 80.22% |
| Resolution SLA met / breached / pending | 5,343 / 4,603 / 54 | 5,343 / 4,603 / 54 |
| Resolution SLA compliance | 53.72% | 53.72% |
| Current backlog / overdue | 1,136 / 1,082 | 1,136 / 1,082 |
| Reassigned tickets / events | 2,617 / 3,104 | 2,617 / 3,104 |
| Reopened tickets | 931 | 931 |
| Rated tickets / average rating | 3,758 / 3.87 | 3,758 / 3.87 |
| Positive rating share / feedback coverage | 66.92% / 42.40% | 66.92% / 42.40% |

The SQL column mapping and comparison code are implemented in `scripts/reconcile_reporting.py`. Because no live database was available, the SQL column contains the expected view result, not an observed database result. Run the database reconciliation command below before treating this as live SQL validation.

## Grain and denominator checks

- Ticket KPIs originate from one row per ticket. Assignment history has 14,035 rows and is pre-aggregated before it is joined to ticket metrics.
- Current team and current agent describe snapshot ownership. Historical team and agent fields describe assignment intervals and are not used as ticket-volume denominators.
- Response SLA compliance divides met by met plus breached. Pending tickets are explicit and excluded from the eligible denominator.
- Resolution-time averages and medians exclude unresolved tickets. Response-time metrics exclude unanswered tickets.
- Missing feedback remains missing and is never converted to zero. Satisfaction denominators use feedback rows; coverage uses resolved tickets.
- Backlog means `resolved_at IS NULL` at the fixed snapshot. Overdue backlog additionally requires a breached resolution commitment.

## Corrections made

No critical calculation or data-integrity issue was found. Repository-publication review identified one API consistency risk: FastAPI date filters had relied on the PostgreSQL server's default session timezone while Django explicitly used UTC. FastAPI now requests a UTC database session, and a regression assertion covers that connection option. The README project-stage description was also updated because it previously described the project as only being at the PostgreSQL reporting stage even though APIs, orchestration, Docker, and Power BI source assets now exist. This audit document makes passed, skipped, and not-run scope explicit.

## Limitations and required deployment checks

1. The data is deliberately synthetic. Patterns and findings are generator-driven and cannot support claims about a real support organization.
2. SLA targets are illustrative elapsed-calendar-time project assumptions, not universal service standards or business-hours SLAs.
3. The reporting snapshot is fixed. It supports reproducibility, but it is not a live operational clock or historical backlog reconstruction.
4. API authentication and authorization are intentionally absent for this portfolio project. Add them before any non-local or sensitive deployment.
5. Django models are unmanaged and read-only by design. `sql/schema.sql`, not Django migrations, owns the shared tables.
6. Airflow uses a local-executor portfolio topology. Production deployment would require secrets management, resource sizing, monitoring, and an appropriate executor.
7. Docker secrets are environment variables for local usability. Use a managed secret store in production.
8. Power BI deliverables are source transformations, DAX, validation SQL, and build instructions. There is no PBIX file, refresh evidence, or rendered dashboard.

## Commands executed

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_synthetic_data
.\.venv\Scripts\python.exe -m scripts.clean_data
.\.venv\Scripts\python.exe -m scripts.eda
.\.venv\Scripts\python.exe -m scripts.load_postgres --check-only
.\.venv\Scripts\python.exe -m scripts.reconcile_reporting
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe ticket_service\manage.py check
.\.venv\Scripts\python.exe -m compileall -q api scripts orchestration dags ticket_service
```

Unavailable-tool probes confirmed that `docker`, `psql`, and the Python `airflow` package were absent.

## Deployment acceptance commands

On a host with Docker, use the documented environment file and run:

```powershell
docker compose --env-file .env.docker config
docker compose --env-file .env.docker build
docker compose --env-file .env.docker up -d postgres
docker compose --env-file .env.docker run --rm fastapi python -m scripts.clean_data
docker compose --env-file .env.docker run --rm fastapi python -m scripts.load_postgres --replace
docker compose --env-file .env.docker run --rm fastapi python -m scripts.reconcile_reporting --database
docker compose --env-file .env.docker up airflow-init
docker compose --env-file .env.docker up -d fastapi django airflow-webserver airflow-scheduler
docker compose --env-file .env.docker ps
```

Then smoke-test both APIs against that database, trigger and inspect one Airflow DAG run, and refresh the Power BI model. Record those observed results separately; do not retroactively mark this local audit as having run them.
