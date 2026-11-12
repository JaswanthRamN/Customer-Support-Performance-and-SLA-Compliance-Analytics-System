# API Guide

## Responsibility split

| Service | Responsibility | Data grain |
| --- | --- | --- |
| FastAPI | Aggregate analytics, KPI summaries, grouped SLA and service-time results, backlog reporting | One row per ticket from reporting views |
| Django REST Framework | Operational ticket listing/details and assignment-history retrieval | Ticket or assignment interval |

Both services are read-only and use the shared PostgreSQL schema. FastAPI does not manage operational tickets. Django models are `managed = False`, so PostgreSQL DDL remains owned by `sql/schema.sql`.

## FastAPI endpoints

| Method and route | Purpose |
| --- | --- |
| `GET /health/live` | Process liveness |
| `GET /health/ready` | Database readiness |
| `GET /api/v1/overview` | Ticket, backlog, overdue, reopening, and rating summary |
| `GET /api/v1/sla` | SLA results grouped by overall, priority, or current team |
| `GET /api/v1/teams` | Current-owner team metrics |
| `GET /api/v1/response-times` | Mean and median response/resolution metrics |
| `GET /api/v1/backlog` | Paginated unresolved-ticket details |

Validated filters include priority, current team, and inclusive created-date bounds. Grouping and pagination values are constrained by Pydantic. SQL uses static statements and bound parameters. Database failures return a safe 503 response with a request ID rather than exposing connection details.

Run locally:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Interactive OpenAPI documentation is available at `/docs`.

## Django REST Framework endpoints

| Method and route | Purpose |
| --- | --- |
| `GET /api/v1/tickets/` | Paginated ticket list |
| `GET /api/v1/tickets/{ticket_id}/` | Ticket details |
| `GET /api/v1/tickets/{ticket_id}/assignments/` | Ordered assignment history |

List filters include status, priority, current team, and inclusive created-date bounds. Pagination is capped at 100 rows per page. Routes are read-only; unsupported write methods are rejected.

Run locally:

```powershell
.\.venv\Scripts\python.exe ticket_service/manage.py runserver 127.0.0.1:8001
```

## Shared consistency rules

- Priority and status values come from the PostgreSQL constraints and corresponding API enums/choices.
- Timestamps are UTC-aware; date filters are inclusive and interpreted in UTC.
- FastAPI current-team analytics use snapshot ownership from `vw_ticket_metrics`.
- Django exposes current ownership on tickets and historical ownership in assignment records.
- Ticket KPIs must never be calculated by counting assignment rows.
- Missing feedback must remain null and must not become a zero rating.

## Security boundary

Authentication, authorization, rate limiting, and transport termination are outside the portfolio scope. The services must not be exposed publicly as-is. For a deployment, add identity controls, least-privilege database roles, HTTPS, allowed-host/origin restrictions, structured monitoring, and a secrets manager.

Detailed implementation notes remain in [FastAPI analytics API](analytics_api.md) and [Django ticket API](django_ticket_api.md).
