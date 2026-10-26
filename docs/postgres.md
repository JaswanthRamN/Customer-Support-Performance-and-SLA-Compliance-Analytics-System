# PostgreSQL schema, load, and analysis

This stage loads the six **synthetic, cleaned** CSVs into the `support_analytics` schema and stores the illustrative priority targets in `sla_policies`. The fixed dataset snapshot is `2026-07-01 00:00:00 UTC`. Start with [data cleaning](data_cleaning.md) if `data/processed/cleaned/` is absent. The local CSVs are ignored by Git; the generator and cleaner reproduce them.

## Table relationships and grain

| Table | Grain | Main relationships |
| --- | --- | --- |
| `sla_policies` | One illustrative priority policy | Referenced by ticket priority and exact minute targets |
| `customers` | One fictional customer | Parent of `tickets` |
| `teams` | One support team | Parent of `agents`; referenced by current ticket ownership |
| `agents` | One fictional agent | Home team references `teams` |
| `tickets` | One ticket at the fixed snapshot | Customer and current agent/team |
| `assignment_history` | One ownership interval | Ticket and assigned agent/team |
| `customer_feedback` | At most one rating per ticket | Ticket and the same ticket customer |

[The schema](../sql/schema.sql) uses text IDs to preserve CSV identifiers, `TIMESTAMPTZ` for UTC events, integer minutes for exact targets, primary/foreign keys, category and lifecycle checks, and a unique partial index allowing at most one current assignment per ticket. The policy table is seeded from the same assumptions as `config/sla_policy.json`: Critical 15/240, High 60/480, Medium 240/1,440, and Low 480/4,320 response/resolution minutes. These are project assumptions, not universal standards. Composite foreign keys require each ticket's priority and targets to match the policy, an agent to belong to the recorded team, and feedback to belong to the ticket's customer. Indexes support creation-date volume, team/status filters, unresolved backlog, SLA breakdowns, and assignment lookups. Some cross-row rules, such as continuous assignment intervals and feedback occurring after final resolution, require [post-load validation](../sql/validation.sql). Schema creation and load happen in one transaction.

## Configure and load

Install [requirements](../requirements.txt), generate and clean the data, then set the connection variables in PowerShell. [`.env.example`](../.env.example) lists the names; the loader reads process environment variables and never writes credentials to a report.

```powershell
$env:PGHOST = 'localhost'
$env:PGPORT = '5432'
$env:PGDATABASE = 'support_analytics'
$env:PGUSER = 'your_postgres_user'
$env:PGPASSWORD = 'your_local_password'
$env:PGSSLMODE = 'prefer'
```

`PGHOST`, `PGDATABASE`, and `PGUSER` are required for loading. `PGPORT` defaults to 5432; password and SSL mode are optional for configurations that do not need them. Create the database and grant the role permission to create a schema and tables before loading. Do not put real credentials in `.env.example`, Git, or command arguments.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.load_postgres --check-only
.\.venv\Scripts\python.exe -m scripts.load_postgres
```

`--check-only` needs no database. It verifies the cleaned files' exact checksums and headers against the data-quality report, expected row counts, data types, timestamps, and relationships, then writes `reports/postgres_preflight.json`. A real load first repeats that preflight, creates the schema, and copies in dependency order: **customers → teams → agents → tickets → assignment_history → customer_feedback**. It then installs the reporting views, compares database row counts with accepted CSV counts, and requires every post-load anomaly count to be zero. On success it writes `reports/postgres_load_report.json` with counts and validation results. A failure rolls back all schema, data, and view changes from that run.

The loader refuses a nonempty target by default. To replace only these six tables after reviewing the target database, run `-m scripts.load_postgres --replace`; this truncates their rows inside the same transaction and reloads them. The loader does not drop the schema. `--input`, `--quality-report`, and `--report` allow custom paths.

Expected accepted counts for the default seed-42 dataset: customers **2,500**, teams **3**, agents **30**, tickets **10,000**, assignment history **14,035**, feedback **3,758**. All post-load relationship and reporting-grain anomaly counts should be **0**. The validator requires `vw_ticket_metrics` to contain exactly one row per ticket and every controlled dimension partition to contain exactly the ticket total. A preflight report with `database_loaded: false` proves only local CSV validation; it is not evidence of a live database load.

## Analysis queries

Run the [query files](../sql/queries/) after a successful load with a PostgreSQL SQL client, for example `psql -X -d support_analytics -f sql/queries/01_ticket_volume.sql`. Results describe **synthetic-data observations**, not real service performance.

| File | Business question and interpretation |
| --- | --- |
| [01_ticket_volume.sql](../sql/queries/01_ticket_volume.sql) | Counts tickets by UTC creation month, priority, category, and channel. Each grouping counts ticket rows once. |
| [02_service_times.sql](../sql/queries/02_service_times.sql) | Mean and median first-response and final-resolution hours, with answered/resolved sample sizes; missing events are excluded from duration calculations. |
| [03_sla_breaches.sql](../sql/queries/03_sla_breaches.sql) | Met, breached, and pending counts by priority. Compliance denominator is met plus breached, excluding pending. |
| [04_team_performance.sql](../sql/queries/04_team_performance.sql) | Current-team ticket workload, service speed, SLA, reassignments, reopenings, and CSAT. Assignment history is aggregated to ticket grain first; current ownership is not an effort allocation. |
| [05_backlog.sql](../sql/queries/05_backlog.sql) | Unresolved tickets by priority and age bucket plus the oldest 20 at the fixed snapshot. It contains two result-producing statements. |
| [06_satisfaction.sql](../sql/queries/06_satisfaction.sql) | Rated count, mean/median CSAT, positive-rating share, and feedback coverage. Missing feedback is excluded from score averages, never treated as zero. |

See [KPI definitions](kpi_definitions.md) for the business meaning and denominators. If you load a dataset with a different snapshot, change the literal in `05_backlog.sql` to that report's `analysis_as_of` timestamp.

For reusable Power BI or SQL-client sources, use the [reporting views and reconciliation guide](reporting_views.md). The views separate ticket-grain current-snapshot metrics from assignment-grain historical ownership activity.

## Validation status in this workspace

The six cleaned files passed preflight with the counts above, and the schema, validation query, and analysis files passed PostgreSQL syntax parsing. Automated loader tests cover dependency order, exact CSV headers, configuration, refusal of implicit replacement, explicit replacement, and transaction rollback. No PostgreSQL server or connection settings were available here, so a live load and database result reconciliation remain to be run against a configured instance.
