# Limitations and Responsible Interpretation

## Data and metric limitations

- All data is synthetic and generated from documented assumptions. It cannot represent a real customer base, workforce, support policy, or observed business result.
- The simulation is not statistically calibrated to an external benchmark and contains no ticket text, sentiment, product telemetry, staffing schedule, cost, or active-work duration.
- Optional feedback creates response-selection risk. Satisfaction describes respondents, not every resolved ticket.
- SLA targets use elapsed calendar time. Business-hour calendars, holidays, entitlement tiers, and pause rules require different logic.
- The fixed 1 July 2026 UTC snapshot provides reproducibility, not a live clock or arbitrary historical backlog reconstruction.
- Resolution time uses final resolution after reopening. This may differ from systems reporting first resolution.
- Current-owner comparisons are associations, not evidence of who performed most work or caused an outcome.
- Assignment intervals record ownership, not continuous effort or productivity.

## Implementation limitations

- The APIs omit authentication, authorization, rate limiting, HTTPS termination, and production monitoring.
- Django uses unmanaged models and is not the schema migration authority.
- Airflow uses a compact LocalExecutor topology suitable for demonstration, not production scale.
- Docker Compose uses environment variables for local secrets; production should use managed secrets and least-privilege identities.
- The reporting context has a fixed snapshot; a production system should deliberately parameterize or materialize history.

## Validation limitations

- Automated tests use mocks or static inspection for database-dependent APIs, Airflow, Docker, and Power BI where external runtimes are unavailable.
- PostgreSQL preflight validates files without executing DDL or SQL.
- A Python baseline with `database_compared: false` is not evidence of observed SQL execution.
- Static Docker validation is not an image build, health transition, or smoke test.
- Static Airflow tests are not a scheduler-driven DAG run.
- Power Query and DAX inspection is not a Desktop refresh or visual validation.

## Delivered-artifact limitations

- No PBIX file, published Power BI dashboard, hosted API, production database, registry image, cloud deployment, or executed Airflow run is claimed.
- Generated processed data is ignored and must be reproduced locally.
- Public publication has not been performed and requires explicit authorization.

Use phrases such as “synthetic-data observation,” “descriptive association,” and “expected reconciliation baseline.” Avoid claims such as “improved customer satisfaction,” “best-performing team,” “agent productivity,” or “production-ready” unless separately supported.
