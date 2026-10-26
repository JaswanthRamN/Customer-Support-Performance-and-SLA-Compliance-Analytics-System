# SQL Reporting Views and Reconciliation

The PostgreSQL reporting layer is defined in `sql/reporting_views.sql` and installed automatically after the six cleaned CSV tables load. It uses the fixed synthetic-data snapshot `2026-07-01 00:00:00 UTC`. All outputs are synthetic-data observations, and the SLA targets remain illustrative project assumptions rather than universal standards.

## Grain and dimensions

`vw_ticket_metrics` is the protected reporting base: exactly one row per ticket. Assignment history is grouped to ticket ID before it joins this view, and feedback is one-to-one by schema constraint. This prevents tickets with several ownership intervals from being counted several times.

`vw_reporting_dimensions` intentionally repeats each ticket once in each dimension type:

| `dimension_type` | Meaning |
| --- | --- |
| Overall | All tickets, one row per ticket |
| Priority | Ticket priority captured at creation |
| Current Team | Team owning the ticket at the fixed snapshot |
| Current Agent | Agent owning the ticket at the fixed snapshot |

Filter to one `dimension_type` before totaling a summary view. Do not add Priority, Current Team, and Current Agent results together because they are parallel views of the same tickets.

Current team and agent describe snapshot ownership. They do not allocate historical handling effort or prove individual performance. Initial owner fields in `vw_ticket_metrics` support routing comparisons. `vw_historical_assignment_activity` is a separate assignment-grain view for handoff analysis: one ticket can have several rows, so use distinct ticket IDs for ticket counts. Its recorded interval is an ownership-record duration and must not be interpreted as active work time.

## View catalog

| View | Grain and purpose |
| --- | --- |
| `vw_reporting_context` | One row containing the fixed `analysis_as_of` snapshot |
| `vw_ticket_metrics` | One row per ticket with durations, SLA flags, current/initial ownership, handoff counts, feedback, backlog age, and overdue flag |
| `vw_reporting_dimensions` | One row per ticket per controlled reporting dimension |
| `vw_sla_compliance` | One row per dimension member with Met/Breached/Pending counts and response, resolution, and overall compliance |
| `vw_service_times` | Average and median response/resolution hours with event and missing-event sample sizes |
| `vw_backlog_aging` | Current unresolved tickets by dimension and mutually exclusive age bucket, including overdue counts |
| `vw_reassignment_rates` | Reassigned distinct tickets, reassignment events, and ticket rate |
| `vw_reopened_rates` | Reopened tickets, unresolved reopened tickets, and reopened rate |
| `vw_satisfaction` | Resolved/rated counts, mean and median CSAT, positive-rating share, and feedback coverage |
| `vw_overdue_tickets` | Ticket-level current backlog already beyond its resolution deadline |
| `vw_historical_assignment_activity` | One row per assignment interval with historical team and agent labels |

SLA compliance is `Met / (Met + Breached)`. Pending stays visible but is excluded from the denominator. Duration averages and medians exclude null events; their event sample sizes are shown. CSAT calculations exclude missing feedback rather than treating it as zero. Positive CSAT uses ratings of 4 or 5. Feedback coverage uses resolved tickets as the denominator.

Reassignment counts include only history rows whose reason is `Reassignment`; reopen handoffs remain separate. Reopened rate uses tickets with `reopen_count > 0` divided by tickets in the dimension. Backlog means tickets with null final `resolved_at` at the reporting snapshot. Overdue means that current backlog also has `resolution_sla_status = 'Breached'`.

## Current versus historical reporting

The dataset contains a fixed end-state snapshot and ownership intervals, not a complete status-event ledger. `vw_backlog_aging` and `vw_overdue_tickets` therefore report **current backlog at `analysis_as_of` for the selected creation cohort**. They cannot reconstruct how many tickets were open on an earlier date. Historical assignment rows show who held a ticket and when ownership changed; they do not reconstruct historical ticket status or historical backlog.

## Python reconciliation

Run the independent Pandas calculation without a database:

```powershell
.\.venv\Scripts\python.exe -m scripts.reconcile_reporting
```

This writes `reports/reporting_reconciliation.json` with ticket-grain totals, SLA results, response/resolution statistics, current backlog and overdue counts, reassignment/reopen rates, satisfaction, and ticket-count breakdowns for priority/current team/current agent. It reads the cleaned CSVs directly and does not call the EDA metric builder.

After loading PostgreSQL and setting the documented `PGHOST`, `PGDATABASE`, and `PGUSER` environment variables, compare those Python results with the installed SQL views:

```powershell
.\.venv\Scripts\python.exe -m scripts.reconcile_reporting --database
```

The command fails if any shared key result differs. A report with `database_compared: false` is a valid local Python baseline, but it is not evidence that a live PostgreSQL comparison ran.
