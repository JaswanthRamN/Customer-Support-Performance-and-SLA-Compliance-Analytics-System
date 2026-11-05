# FastAPI Analytics API

The API is a read-only layer over `support_analytics.vw_ticket_metrics`. It uses environment configuration, parameterized PostgreSQL queries, Pydantic request/response validation, bounded pagination, and generic database error messages. All data is synthetic and the SLA targets are illustrative assumptions.

## Setup and run

Install the pinned requirements, load PostgreSQL, and set the `PG*` variables documented in `.env.example`. Then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:create_app --factory --host 127.0.0.1 --port 8000
```

OpenAPI JSON is available at `/openapi.json`, Swagger UI at `/docs`, and ReDoc at `/redoc`. Do not bind publicly without adding authentication, HTTPS termination, rate limiting, and production observability.

## Tested routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health/live` | Process liveness without a database call |
| GET | `/health/ready` | PostgreSQL connectivity/readiness |
| GET | `/api/v1/overview` | Portfolio ticket, backlog, reopening, and satisfaction totals |
| GET | `/api/v1/sla` | SLA populations and compliance grouped by overall, priority, or current team |
| GET | `/api/v1/teams` | Current-team ticket outcomes; not causal attribution |
| GET | `/api/v1/response-times` | Average/median response and resolution times with samples |
| GET | `/api/v1/backlog` | Current unresolved summary and paginated ticket detail |

Analytics filters are `priority`, `team_id`, `created_from`, and `created_to`. List endpoints accept `limit` from 1 to 100 and non-negative `offset`. SLA and response-time endpoints accept `group_by=overall|priority|team`. Invalid enums, IDs, dates, ranges, and pagination return HTTP 422 before SQL executes.

All user values are passed through psycopg parameters. The only dynamic SQL fragments are selected from the fixed server-side `GROUPS` map after Pydantic enum validation. Database failures return generic HTTP 503 or 500 bodies with a request ID; SQL text, credentials, and driver errors are not returned.

## Testing scope

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Endpoint tests inject a deterministic fake database at the database boundary. They exercise all routes above, query-filter parameter passing, pagination, invalid input, OpenAPI path generation, readiness success/failure, safe error content, environment validation, and secret-safe settings representation. The SQL is separately parsed during repository validation.

A live PostgreSQL server was not available during implementation, so these tests do not claim network integration with PostgreSQL. Before deployment, run the loader, start the API with a least-privilege read-only database role, execute the same route checks against that instance, and compare results with the existing SQL/Python reconciliation baselines.
