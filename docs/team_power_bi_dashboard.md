# Power BI Team Comparison Dashboard Guide

This page compares support teams while keeping ticket outcomes separate from historical assignment activity. It is a descriptive portfolio dashboard built from synthetic data. It does not establish that team assignment caused an SLA, time, backlog, reassignment, reopening, or satisfaction result. The repository contains source assets and instructions, not a `.pbix` file.

## Two lenses that must not be mixed

### Current-owner ticket lens

Use `DimCurrentTeam[team_name]`. Each ticket belongs to exactly one current team at the fixed snapshot, so team ticket counts add to 10,000. Use this lens for ticket volume, completed SLA compliance, response and resolution times, current backlog, current-cohort reassignment history, reopened rate, and customer satisfaction.

Current ownership is a snapshot label. It may differ from the team that initially responded, performed most handling, or resolved the ticket. Comparisons are associations, not agent or team productivity scores.

### Historical-assignment lens

Use `DimHistoricalTeam[team_name]` only with `FactAssignmentHistory` measures. Its grain is one ownership interval. A ticket can appear under several teams, so distinct assigned-ticket counts by historical team are non-additive. Use this lens for assignment intervals and reassignment-event frequency, not for SLA, duration, backlog, reopening, or satisfaction outcomes.

Do not place both team dimensions on one visual, do not connect the two team dimensions, and do not enable bidirectional filtering.

## Recommended page layout

Use a 16:9 page named **Team Performance** with a visible subtitle: **Descriptive comparison | Current ownership at 1 July 2026 UTC | Synthetic data**.

```text
+--------------------------------------------------------------------------------+
| Team Performance                     Created Date | Priority | Current Team     |
+--------------------------------------------------------------------------------+
| Current-owner comparison matrix: volume, eligible samples, SLA, time, backlog   |
+---------------------------------------+----------------------------------------+
| Volume and backlog by current team    | Completed SLA by current team          |
+---------------------------------------+----------------------------------------+
| Reassignment + reopened rates         | Customer rating + feedback sample      |
+--------------------------------------------------------------------------------+
| Separate historical assignment section: intervals and reassignment frequency    |
+--------------------------------------------------------------------------------+
```

## Visual-to-measure mapping

### Current-owner section

| Visual | Category | Values | Required sample-size context |
| --- | --- | --- | --- |
| Main comparison matrix | `DimCurrentTeam[team_name]` | `[Current-Owner Ticket Sample]`, `[Completed First-Response Compliance %]`, `[Completed Resolution Compliance %]`, `[Average Response Hours]`, `[Average Resolution Hours]`, `[Unresolved Backlog]`, `[Current-Owner Reassigned Ticket %]`, `[Reopened Ticket %]`, `[Customer Rating]` | Add completed eligible, time sample, and rating sample measures beside or in tooltips |
| Volume/backlog combo | Current team | Columns `[Total Tickets]`; line `[Unresolved %]` | `[Current-Owner Ticket Sample]` |
| SLA clustered bar | Current team | Both completed compliance measures | `[Completed First-Response Eligible]`, `[Completed Resolution Eligible]` |
| Time comparison | Current team | Average and median response/resolution hours | `[Response Time Sample]`, `[Resolution Time Sample]`; do not imply averages and medians are interchangeable |
| Reassignment/reopen bar | Current team | `[Current-Owner Reassigned Ticket %]`, `[Reopened Ticket %]` | `[Current-Owner Reassigned Tickets]`, `[Reopened Tickets]`, `[Current-Owner Ticket Sample]` |
| Satisfaction scatter | X `[Customer Rating]`; Y `[Positive CSAT %]`; Details current team; Size `[Customer Rating Sample]` | Rating and positive share | `[Customer Rating Sample]`, `[Feedback Coverage %]` |

Current-cohort reassignment means: among tickets currently owned by the displayed team, how many ever had a reassignment event? It does not attribute each handoff to that current team. Label it **Reassigned tickets in current-owner cohort**, not **Team reassignments**.

### Historical-assignment section

| Visual | Category | Values | Interpretation |
| --- | --- | --- | --- |
| Historical assignment matrix | `DimHistoricalTeam[team_name]` | `[Historical Assignment Intervals]`, `[Historical Assigned Tickets]`, `[Historical Reassignment Events]`, `[Historical Reassignment Event %]` | Recorded ownership intervals by the team that held them |
| Historical frequency bar | Historical team | `[Historical Reassignment Events per 100 Intervals]` | Event share of intervals; not a ticket outcome or causal quality score |

Keep the historical section in a bordered panel with a distinct title. Historical team slicers must not be synchronized with current team slicers.

## Tooltips and sample sizes

Every rate and average needs its denominator:

- Completed response compliance: `[Completed First-Response Eligible]`.
- Completed resolution compliance: `[Completed Resolution Eligible]`.
- Response mean/median: `[Response Time Sample]` answered tickets.
- Resolution mean/median: `[Resolution Time Sample]` finally resolved tickets.
- Backlog rate: `[Current-Owner Ticket Sample]`.
- Current-cohort reassignment and reopening rates: `[Current-Owner Ticket Sample]`.
- Customer rating and positive share: `[Customer Rating Sample]`; add `[Feedback Coverage %]` to expose response-selection risk.
- Historical reassignment event share: `[Historical Assignment Intervals]`.

Use `DIVIDE`, so empty eligible groups return blank instead of a misleading 0%. If a team has a small sample after slicers, show the sample count and avoid ranking it as definitively better or worse.

## Manual build steps

1. Confirm the model relationships match `docs/power_bi_model.md` and all filters are single-direction.
2. Add the new explicit team measures from `powerbi/dax/measures.dax`.
3. Create the **Team Performance** page and add created-date, priority, and current-team slicers for the current-owner section.
4. Build the main matrix first. Validate its current-owner ticket total is 10,000 with slicers cleared.
5. Add volume/backlog, SLA, time, reassignment/reopen, and satisfaction visuals from the mapping tables.
6. Add tooltip pages that expose the relevant eligible or observed sample sizes.
7. Create the separate historical-assignment panel using only `DimHistoricalTeam` and assignment-history measures.
8. Use **Edit interactions** so the current-team slicer does not alter the historical panel and the historical-team slicer does not alter current ticket visuals.
9. Add a text note: **Team results reflect current ownership or recorded assignment intervals; they do not measure causal team impact or active effort.**
10. Run `sql/team_dashboard_validation.sql` and compare every current and historical team row.

## Validation checks

The SQL file pre-aggregates reassignment history to one row per ticket before joining it to current-owner ticket metrics. Feedback is also aggregated to one row per ticket. This guarantees the current-team query remains ticket-grain even if future source rules permit multiple feedback responses.

Accept the dashboard only when:

- Current-team ticket samples total 10,000, with expected team counts of 3,687, 3,395, and 2,918.
- Current-team samples do not change when historical-team fields are used only in the isolated historical panel.
- Assignment intervals total 14,035; they are not used as the denominator for ticket KPIs.
- Completed SLA numerators never exceed their displayed eligible populations.
- Response and resolution averages exclude missing event timestamps and show their event samples.
- Current backlog counts only tickets with null final `resolved_at` at the fixed snapshot.
- Current-cohort reassigned tickets use distinct ticket IDs; reassignment events may exceed reassigned tickets.
- Historical distinct assigned-ticket counts are not added across teams because a ticket can visit several teams.
- Reopened rates divide distinct reopened tickets by current-owner ticket sample.
- Customer ratings exclude missing feedback and show feedback sample and coverage.
- SQL grain checks report 10,000 ticket rows, 10,000 distinct ticket IDs, 14,035 assignment rows, zero duplicate-feedback tickets, and zero missing team relationships.
- Titles use **current owner**, **historical assignment**, or **cohort** precisely and avoid unsupported claims such as “best team,” “team caused breaches,” or “agent productivity.”

The delivered CSV baseline maps those current counts to Tier 1 Support 3,687, Technical Support 3,395, and Billing Support 2,918. Historical assignment intervals are 5,192, 4,788, and 4,055 respectively, totaling 14,035. Their distinct assigned-ticket samples are 4,654, 4,301, and 3,656; these deliberately sum above 10,000 because tickets can move between teams.

All observed differences are synthetic-data observations shaped by generated ticket mix, routing, and feedback behavior. Priority, category, channel, complexity, reassignment, and optional feedback may differ by team; no adjustment for confounding or selection bias is performed.
