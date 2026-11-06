# Django REST Framework Ticket API

This is a separate, read-only operational ticket service mapped onto the existing PostgreSQL schema. Django models use `managed = False` and schema-qualified `db_table` values, so Django does not create or migrate duplicate `tickets`, `teams`, `agents`, or `assignment_history` tables.

## Tested routes

| Method | Route | Responsibility |
| --- | --- | --- |
| GET | `/api/v1/tickets/` | Paginated ticket listing with status, priority, current-team, and creation-date filters |
| GET | `/api/v1/tickets/{ticket_id}/` | Ticket lifecycle, current ownership, targets, deadlines, and SLA detail |
| GET | `/api/v1/tickets/{ticket_id}/assignments/` | Paginated chronological assignment history |

Filters reject unknown status or priority values, malformed team IDs, and reversed date ranges before ORM execution. Pagination defaults to 25 and is capped at 100. Django ORM parameterizes validated values.

The API is intentionally read-only. The shared database enforces coordinated status timestamps, priority targets, deadlines, and SLA classifications. A partial status or priority update could violate those constraints. Add write workflows only as explicit transactions that update every dependent field and include boundary tests.

## Running locally

Install `requirements.txt`, load the database using the existing loader, and configure the `PG*` variables plus `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` from `.env.example`. Start from the repository root:

```powershell
.\.venv\Scripts\python.exe ticket_service/manage.py runserver 127.0.0.1:8001
```

Use a PostgreSQL role with `SELECT` access only to `support_analytics.tickets`, `teams`, `agents`, and `assignment_history`. Authentication is intentionally not invented for this portfolio service; do not expose it publicly without adding authentication, authorization, TLS, throttling, and audit logging.

## DRF versus FastAPI responsibilities

| Service | Intended responsibility | Data shape |
| --- | --- | --- |
| Django REST Framework | Operational ticket retrieval, ticket detail, and ownership-history navigation | Ticket and assignment records |
| FastAPI analytics service | Read-only aggregates for overview, SLA, team, service-time, and backlog reporting | KPI summaries and paginated analytics |

Do not duplicate aggregate business logic inside DRF or operational record navigation inside FastAPI. Both services share PostgreSQL definitions and vocabulary, but their contracts remain independent. They can be deployed separately and use separate least-privilege roles.

## Shared-database migration strategy

1. `sql/schema.sql` remains the source of truth for shared support tables, keys, constraints, and indexes.
2. The loader applies shared schema changes before data loads and reporting views. Neither web framework owns those tables.
3. DRF shared models remain `managed = False`; the tickets app has migrations disabled. Never run `makemigrations` expecting it to change shared tables.
4. If Django later needs framework-owned tables, create a separate PostgreSQL schema and a separate Django app/migration module. Do not reuse shared table names.
5. Apply shared changes with versioned SQL using expand-and-contract: add compatible columns/constraints, deploy both services, backfill/validate, then remove obsolete fields in a later release.
6. Test model mappings and both API contracts against the expanded schema before destructive changes.
7. Keep reporting views backward compatible while FastAPI versions are active. Coordinate view removal separately from table migration.
8. Production database roles should separate schema ownership, loader writes, DRF reads, and FastAPI reporting-view reads.

## Test scope

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ticket_service -v
```

Tests exercise all three routes through DRF's API client, serializers, filters, pagination, nested current-owner labels, assignment serialization, invalid filters, and unmanaged/schema-qualified model contracts. Query services are patched at the view boundary, so no live PostgreSQL integration is claimed. Run an integration suite against a configured database before deployment.
