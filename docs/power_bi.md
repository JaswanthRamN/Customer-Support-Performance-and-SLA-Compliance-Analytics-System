# Power BI Supporting Assets

## Delivered scope

The repository provides Power Query M files, DAX measures, relationship and grain instructions, dashboard specifications, tooltips, and SQL reconciliation queries. It does **not** contain a PBIX file, screenshots from an executed report, or a published Power BI service workspace.

## Model grain

| Table | Grain | Counting rule |
| --- | --- | --- |
| `FactTickets` | One ticket | Source for ticket counts and ticket outcomes |
| `FactAssignmentHistory` | One ownership interval | Use intervals or distinct ticket IDs, never rows as ticket volume |
| `FactFeedback` | One submitted survey | Use feedback rows for rating metrics; preserve missing feedback |
| Team/agent/date dimensions | One dimension member | Use role-specific relationships |

Current team and current agent filter ticket outcomes. Historical team and historical agent filter assignment activity. Relationships are single-direction; assignment history is not merged into tickets.

## Import sequence

1. Configure `pServer`, `pDatabase`, and the fixed UTC analysis snapshot.
2. Paste the M queries from `powerbi/power_query/` into blank queries in the order documented in [the model guide](power_bi_model.md).
3. Enable load only for the three facts and required role-playing dimensions.
4. Create the documented one-to-many, single-direction relationships.
5. Create a dedicated Measures table and paste measures from `powerbi/dax/measures.dax`.
6. Apply formats: percentages, decimal hours, whole-number samples, and rating decimals.
7. Reconcile table counts and core measures before creating visuals.

## Dashboard pages

- **Executive overview:** KPI cards, trends, distributions, team comparison, and slicers.
- **SLA performance:** completed compliance, breaches, current overdue backlog, and approaching deadlines.
- **Team comparison:** current-owner outcomes separated from historical assignment activity.
- **Backlog and satisfaction:** aging, overdue and high-priority backlog, rating distribution, coverage, and satisfaction breakdowns.

Use the detailed [executive](executive_power_bi_dashboard.md), [SLA](sla_power_bi_dashboard.md), [team](team_power_bi_dashboard.md), and [backlog/satisfaction](backlog_satisfaction_power_bi.md) guides.

## Validation

Run the SQL reconciliation files after loading PostgreSQL, then compare them with the Python baseline and Power BI cards. Confirm that ticket counts use distinct IDs, assignment rows do not inflate ticket metrics, unresolved tickets are excluded from resolution averages, pending commitments are excluded from compliance denominators, missing feedback is excluded from rating averages, and current/historical team dimensions are not mixed.

The validation files are `sql/power_bi_reconciliation.sql`, `sql/sla_dashboard_validation.sql`, `sql/team_dashboard_validation.sql`, and `sql/backlog_satisfaction_validation.sql`.

## Presentation rules

Label all findings as synthetic-data observations. Display eligible sample sizes beside rates and averages. Do not rank teams causally, claim productivity effects, or imply that current ownership identifies the team responsible for every historical outcome.
