# Power BI SLA Dashboard Guide

This guide designs a focused SLA page using the repository's ticket-grain model. It separates completed service outcomes from current operational risk. The repository provides Power Query, DAX, SQL, and build instructions; it does not contain a `.pbix` file.

## Population definitions

| Population | Definition | Use |
| --- | --- | --- |
| Completed first-response eligible | `first_response_at` exists and response status is Met or Breached | Retrospective response compliance |
| Completed resolution eligible | `resolved_at` exists and resolution status is Met or Breached | Retrospective resolution compliance |
| All classifiable response commitments | Response status is Met or Breached, including overdue unanswered tickets | Portfolio commitment exposure |
| All classifiable resolution commitments | Resolution status is Met or Breached, including overdue unresolved tickets | Portfolio commitment exposure |
| Current overdue unanswered | No first response and response status is Breached at the fixed snapshot | Operational response backlog |
| Current overdue unresolved | No final resolution and resolution status is Breached at the fixed snapshot | Operational resolution backlog |
| Approaching deadline | Open commitment is Pending, has positive time remaining, and has no more than 25% of its priority target remaining | Near-term intervention queue |

Pending commitments are excluded from compliance denominators. The dashboard's headline compliance cards use completed outcomes. The existing `[First-Response SLA Compliance %]` and `[Resolution SLA Compliance %]` remain available as all-classifiable commitment measures and must be labeled accordingly if displayed.

The 25% approaching threshold is relative to each priority target: for example, 1 hour of a 4-hour response target or 1 hour of a 4-hour resolution target. It is evaluated at `pAnalysisAsOfUtc`, not `NOW()`, so a refresh of this fixed historical dataset stays reproducible. A live operational model should replace the fixed snapshot with a controlled refresh timestamp.

## Page layout and visual mapping

Use a 16:9 page named **SLA Performance**.

| Section | Visual | Fields and measures |
| --- | --- | --- |
| Header | Slicers | `DimCreatedDate[Date]`, `FactTickets[priority]`, `DimCurrentTeam[team_name]` |
| Outcome cards | Four cards | `[Completed First-Response Compliance %]`, `[Completed Resolution Compliance %]`, `[Completed First-Response Breached]`, `[Completed Resolution Breached]` |
| Current risk cards | Three cards | `[Current Overdue Unanswered Tickets]`, `[Current Overdue Unresolved Tickets]`, `[Approaching Any Deadline Tickets]` |
| Trend | Two-line chart | Axis `DimCreatedDate[YearMonth]`; values completed response and resolution compliance |
| Priority comparison | Clustered bar chart | Axis `FactTickets[priority]`; values both completed compliance measures; add eligible counts to tooltip |
| Team comparison | Matrix | Rows `DimCurrentTeam[team_name]`; completed compliance, eligible, breach, current-overdue, and approaching measures |
| Overdue queue | Table | Ticket ID, priority, current team, status, resolution deadline, unresolved age; visual filter `is_overdue = True` |
| Approaching queue | Table | Ticket ID, priority, current team, response/resolution deadline and minutes remaining; filter using an approaching measure or matching flags |

The monthly chart groups tickets by creation month. It shows completed outcomes for created-ticket cohorts, not the month when a breach occurred and not historical backlog. A true breach-event trend requires status-event history.

## Recommended tooltips

Create report-page tooltips rather than placing every denominator on the canvas.

### Completed first-response tooltip

- `[Completed First-Response Met]`
- `[Completed First-Response Breached]`
- `[Completed First-Response Eligible]`
- Text: **Answered tickets only; Pending and currently unanswered tickets excluded. Met ÷ eligible.**

### Completed resolution tooltip

- `[Completed Resolution Met]`
- `[Completed Resolution Breached]`
- `[Completed Resolution Eligible]`
- Text: **Finally resolved tickets only; unresolved backlog excluded. Met ÷ eligible.**

### Current-risk tooltip

- `[Current Overdue Unanswered Tickets]`
- `[Current Overdue Unresolved Tickets]`
- `[Current Overdue Any-Commitment Tickets]`
- `[Approaching First-Response Deadline Tickets]`
- `[Approaching Resolution Deadline Tickets]`
- Text: **Snapshot as of 1 July 2026 00:00 UTC. A ticket may have both overdue commitments; the any-commitment measure counts it once.**

### All-classifiable tooltip

- `[Response SLA Eligible]` and `[First-Response SLA Compliance %]`
- `[Resolution SLA Eligible]` and `[Resolution SLA Compliance %]`
- Text: **Includes completed commitments plus open commitments already overdue; excludes Pending. Do not label as completed-ticket compliance.**

## Formatting and interaction guidance

Use green only for compliance, amber for approaching, and red for overdue/breached. Always include labels so meaning does not depend on color. Format percentages to two decimals and counts as whole numbers. Put eligible counts in tooltips beside every compliance rate; a high rate from a tiny population should be visible.

Use the current-team dimension, not historical assignment team, because this page combines current queues with ticket outcomes. Current team is snapshot ownership and should not be interpreted as the team responsible for every historical response or resolution. Use single-direction relationships and never merge assignment history into tickets.

Configure slicer interactions for every visual. Date filters are creation-date cohort filters. If a narrow filter has no eligible completed tickets, `DIVIDE` correctly returns blank; display **No eligible tickets** rather than 0% if the card visual supports conditional messaging.

For the overdue table, sort by hours overdue descending. For the approaching table, sort by minutes remaining ascending. Apply data bars cautiously and retain the numeric value. Add drill-through to a ticket-detail page only with synthetic identifiers and operational timestamps—there is no real personal information in this project.

## Manual Power BI steps

1. Refresh the existing queries after replacing `FactTickets.m` with the updated source. Confirm the new snapshot and remaining-minute columns load without changing the 10,000-ticket row count.
2. Add the new measures from `powerbi/dax/measures.dax` to the existing Measures table.
3. Create a page named **SLA Performance**, then add date, priority, and current-team slicers.
4. Build the four completed-outcome cards and three current-risk cards using the mapping above.
5. Add the created-month compliance line chart. Put both eligible measures in its tooltip.
6. Add priority bars and the current-team matrix. Keep percentage and denominator measures adjacent.
7. Add the overdue table and filter `FactTickets[is_overdue]` to True.
8. Add the approaching table. Include both remaining-minute columns; use a visual-level filter where the relevant remaining value is positive and no more than 25% of its target, with status Pending.
9. Create and assign the tooltip pages. Test Critical, High, Medium, and Low selections separately.
10. Run `sql/sla_dashboard_validation.sql` and reconcile the unfiltered cards, each priority/team row, created-month trend, overdue detail, and approaching queue.

## SQL validation and acceptance checks

`sql/sla_dashboard_validation.sql` returns separate result sets for headline metrics, priority/team compliance, created-month cohorts, overdue unresolved detail, and the approaching queue. It uses the same fixed UTC snapshot and 25% threshold as Power BI. SQL uses ticket-grain tables only, preventing one-to-many assignment joins from multiplying counts.

Independent Pandas calculations over the delivered synthetic ticket file provide these unfiltered validation targets:

| Metric | Expected value |
| --- | ---: |
| Completed first-response eligible | 9,796 |
| Completed first-response compliance | 81.80% |
| Completed resolution eligible | 8,864 |
| Completed resolution compliance | 60.28% |
| Current overdue unanswered | 193 |
| Current overdue unresolved | 1,082 |
| Approaching first-response deadline | 2 |
| Approaching resolution deadline | 4 |
| Distinct tickets approaching either deadline | 6 |

These file-based results validate the metric logic independently. A live PostgreSQL comparison remains pending until the cleaned data is loaded into a configured server.

Accept the page only when:

- Completed compliance numerators plus completed breach counts equal their eligible populations.
- Pending tickets do not enter completed or all-classifiable compliance denominators.
- Current overdue unresolved equals tickets with null `resolved_at` and breached resolution status.
- Approaching tickets are still Pending, have positive time remaining, and fall within 25% of their own priority target.
- Priority/team rows match SQL under the same slicers.
- Created-month values are described as cohort outcomes, not breach-event or backlog history.
- The overdue detail count matches its card after identical filters.
- The approaching detail count reconciles to the distinct-ticket card; a ticket near both deadlines is counted once by `[Approaching Any Deadline Tickets]`.
- All timestamps are interpreted as UTC and the snapshot is displayed on the page.
- SLA targets are labeled illustrative project assumptions, not universal standards.
