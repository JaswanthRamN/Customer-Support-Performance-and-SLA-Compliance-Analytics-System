# Power BI Backlog and Customer Satisfaction Views

This guide defines two report pages: **Unresolved Tickets** and **Customer Satisfaction**. Both use the existing ticket-grain model and fixed `2026-07-01 00:00:00 UTC` snapshot. The data is synthetic, the SLA targets are illustrative assumptions, and the repository does not contain a `.pbix` file.

## Page 1: Unresolved Tickets

### Metric definitions

- **Unresolved backlog:** distinct tickets with null final `resolved_at` at the snapshot.
- **Overdue backlog:** unresolved tickets whose resolution SLA status is Breached.
- **High-priority backlog:** unresolved Critical or High tickets.
- **Unassigned current tickets:** unresolved tickets with blank `current_agent_id`.
- **Age:** elapsed calendar hours from `created_at` to the fixed snapshot, not time actively worked.

Current agent is required by the delivered PostgreSQL schema and synthetic data. `[Unassigned Current Tickets]` should therefore be zero and acts as a routing-integrity check. Do not manufacture unassigned tickets or reinterpret closed assignment intervals as unassigned time.

The Power Query fields `backlog_age_bucket` and `backlog_age_bucket_sort` create mutually exclusive buckets:

| Sort | Bucket | Rule |
| ---: | --- | --- |
| 1 | 0-24 hours | Age ≤ 24 hours |
| 2 | 25-72 hours | 24 < age ≤ 72 hours |
| 3 | 4-7 days | 72 < age ≤ 168 hours |
| 4 | 8-14 days | 168 < age ≤ 336 hours |
| 5 | 15-30 days | 336 < age ≤ 720 hours |
| 6 | 31+ days | Age > 720 hours |

Sort `backlog_age_bucket` by `backlog_age_bucket_sort` and hide the sort field from report view.

### Layout and visual mapping

| Visual | Fields or measures | Notes |
| --- | --- | --- |
| KPI cards | `[Unresolved Backlog]`, `[Overdue Tickets]`, `[Overdue Backlog %]`, `[High-Priority Backlog]`, `[Unassigned Current Tickets]` | State snapshot date in page subtitle |
| Aging distribution | Axis `FactTickets[backlog_age_bucket]`; value `[Unresolved Backlog]` | Visual filter excludes blank bucket |
| Priority backlog | Axis `FactTickets[priority]`; value `[Unresolved Backlog]` | Custom sort Critical → Low |
| Current-team backlog | Axis `DimCurrentTeam[team_name]`; values `[Unresolved Backlog]`, `[Overdue Tickets]` | Current ownership only |
| Category/channel matrix | Rows category; columns channel; value `[Unresolved Backlog]` | Ticket volume, not assignment volume |
| Operational detail table | Ticket ID, priority, category, channel, current team/agent, created time, age, resolution deadline, SLA status | Sort overdue first, then oldest age |

Add created-date, priority, category, channel, current-team, and age-bucket slicers. Created date filters the creation cohort; it does not reconstruct historical backlog. The page is a current snapshot.

## Page 2: Customer Satisfaction

### Population rules

`[Total Tickets]` is ticket volume. `[Resolved Tickets]` is the resolution population. `[Feedback Responses]` is feedback volume. These measures answer different questions and must not share an ambiguous label such as “Count.”

`[Customer Rating]`, `[Average CSAT]`, `[Median CSAT]`, and rating percentages use actual `FactFeedback` rows only. A missing feedback row means **not observed**, never a zero rating. `[Feedback Coverage %]` exposes selection risk by dividing feedback responses by resolved tickets.

### Layout and visual mapping

| Visual | Fields or measures | Sample-size requirement |
| --- | --- | --- |
| KPI cards | `[Customer Rating]`, `[Median CSAT]`, `[Positive CSAT %]`, `[Feedback Responses]`, `[Feedback Coverage %]` | Show `[Resolved Tickets]` beside coverage |
| Rating distribution | Axis `FactFeedback[csat_score]`; value `[Feedback Responses]` | Include scores 1 through 5; do not add a zero category |
| Satisfaction by current team | Axis `DimCurrentTeam[team_name]`; values `[Customer Rating]`, `[Positive CSAT %]` | Tooltip `[Feedback Responses]`, `[Resolved Tickets]`, `[Feedback Coverage %]` |
| Satisfaction by category | Axis `FactTickets[category]`; values rating and positive share | Ticket filters flow to feedback through `FactTickets` |
| Satisfaction by channel | Axis `FactTickets[channel]`; values rating and positive share | Show feedback sample and coverage |
| Volume/coverage matrix | Rows team/category/channel; values `[Total Tickets]`, `[Resolved Tickets]`, `[Feedback Responses]`, `[Feedback Coverage %]` | Explicitly distinguishes ticket from feedback volume |

Use the separate rating-count measures for cards or tooltip detail: `[Rating 1 Responses]` through `[Rating 5 Responses]`. Negative is scores 1-2, neutral is 3, and positive is 4-5. Use `DIVIDE`-based percentages so a group with no feedback displays blank rather than 0% satisfaction.

## Manual Power BI steps

1. Refresh `FactTickets` using the updated Power Query and confirm its row count remains 10,000.
2. Sort `backlog_age_bucket` by `backlog_age_bucket_sort` in Column tools.
3. Add the new measures from `powerbi/dax/measures.dax` to the Measures table.
4. Build **Unresolved Tickets** using only ticket and current-owner fields. Filter the detail and aging visuals to unresolved tickets.
5. Build **Customer Satisfaction** with feedback measures as values and ticket dimensions as grouping fields.
6. Add report-page tooltips showing eligible populations: unresolved ticket sample for backlog, feedback volume for ratings, and resolved volume for coverage.
7. Use **Edit interactions** to confirm all slicers behave as intended. Feedback score slicers should affect feedback visuals but must not be presented as changing total ticket volume.
8. Add a page note: **Missing feedback is excluded, not scored as zero. Satisfaction results describe respondents only.**
9. Run `sql/backlog_satisfaction_validation.sql` and compare headline cards, age buckets, backlog dimensions, rating distribution, and satisfaction dimension rows.

## Validation checklist

Independent calculations over the delivered CSVs provide these unfiltered reconciliation targets:

| Population | Expected |
| --- | ---: |
| Unresolved backlog | 1,136 |
| Overdue backlog | 1,082 |
| High-priority backlog | 298 |
| High-priority overdue backlog | 297 |
| Unassigned current tickets | 0 |
| 0-24 hour backlog | 50 |
| 25-72 hour backlog | 30 |
| 4-7 day backlog | 37 |
| 8-14 day backlog | 62 |
| 15-30 day backlog | 115 |
| 31+ day backlog | 842 |
| Feedback responses | 3,758 |
| Rating 1 / 2 / 3 / 4 / 5 | 32 / 229 / 982 / 1,481 / 1,034 |

- `FactTickets` remains exactly one row per ticket; assignment history is not joined into either page.
- Unresolved age buckets are mutually exclusive and sum to `[Unresolved Backlog]`.
- Overdue backlog is a subset of unresolved backlog.
- High-priority backlog includes only Critical and High unresolved tickets.
- Unassigned current tickets equals zero for the delivered required-ownership dataset.
- Rating distribution counts sum to `[Feedback Responses]`, expected 3,758 unfiltered.
- Rating values contain only 1-5; there is no zero-rating category.
- Average rating equals 3.87 and median rating equals 4.00 unfiltered.
- Positive feedback equals 2,515 and positive CSAT equals 66.92% unfiltered.
- Feedback coverage equals 42.40% of 8,864 resolved tickets.
- Team, category, and channel rows show ticket volume, resolved-ticket volume, and feedback volume separately.
- SQL aggregates feedback to ticket grain before dimension joins and never joins assignment history.
- Narrow groups with no feedback return blank satisfaction, not zero.
- Current-team labels mean ownership at the snapshot and do not prove causal responsibility for satisfaction or backlog.

Run the SQL after loading PostgreSQL. The expected totals above are independently established from the delivered CSV baseline; a live database comparison remains pending until a PostgreSQL server is configured.
