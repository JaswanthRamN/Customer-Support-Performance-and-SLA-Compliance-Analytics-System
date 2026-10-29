# Executive Power BI Dashboard Build Guide

This guide defines a single-page executive dashboard for the synthetic customer-support project. It uses the existing Power Query model and DAX measures in this repository. No `.pbix` file has been created.

## Audience and decisions

The page is designed for a support director who needs to answer four questions quickly:

1. How much demand and current backlog exist?
2. Are response and resolution commitments being met?
3. Where is workload concentrated by time, priority, category, and team?
4. Is customer experience acceptable, and which teams need investigation?

The dashboard is descriptive. Team comparisons show current snapshot ownership, not causal agent productivity. All observations come from synthetic data, and the SLA targets are project assumptions rather than universal standards.

## Recommended page layout

Use a 16:9 canvas. Keep the reading order left-to-right and top-to-bottom.

```text
+--------------------------------------------------------------------------------+
| Executive Support Overview                         Date | Priority | Team       |
+------------+------------+------------+------------+------------+---------------+
| Total      | Open       | Overall    | Avg Resp.  | Avg Resol. | Customer      |
| Tickets    | Backlog    | SLA %      | Hours      | Hours      | Rating        |
+--------------------------------------+-----------------------------------------+
| Ticket trend by created month        | Tickets by priority                    |
| line chart                           | clustered bar                          |
+--------------------------------------+-----------------------------------------+
| Tickets by category                  | Team comparison matrix                 |
| horizontal bar                       | volume, backlog, SLA, speed, CSAT       |
+--------------------------------------+-----------------------------------------+
| Context note: synthetic data; UTC; SLA targets are illustrative assumptions    |
+--------------------------------------------------------------------------------+
```

Use a neutral background, one primary blue, amber for pending/backlog, red for breaches, and green for compliance. Do not use red/green alone to communicate meaning; retain labels and values. Keep the six KPI cards visually consistent and display no more than two decimals.

## Visual-to-measure mapping

| Visual | Field or measure | Configuration and business meaning |
| --- | --- | --- |
| Total Tickets card | `[Total Tickets]` | Distinct ticket count in the selected filter context |
| Open Backlog card | `[Unresolved Backlog]` | Tickets without a final resolution; title it **Open Backlog** |
| SLA Compliance card | `[Overall SLA Compliance %]` | Met ÷ (Met + Breached); Pending is excluded. Subtitle: **Overall response and resolution SLA** |
| Average Response card | `[Average Response Hours]` | Answered tickets only; format `0.00 h` |
| Average Resolution card | `[Average Resolution Hours]` | Finally resolved tickets only; unresolved tickets are excluded; format `0.00 h` |
| Customer Rating card | `[Customer Rating]` | Mean rating among actual feedback responses; missing feedback is not zero; format `0.00 / 5` |
| Ticket trend line | Axis `DimCreatedDate[YearMonth]`; value `[Total Tickets]` | Sort YearMonth chronologically; show created-ticket demand, not backlog history |
| Priority distribution | Axis `FactTickets[priority]`; value `[Total Tickets]` | Sort Critical, High, Medium, Low using a custom sort column if desired |
| Category distribution | Axis `FactTickets[category]`; value `[Total Tickets]` | Horizontal bar; sort descending by ticket count |
| Team comparison matrix | Rows `DimCurrentTeam[team_name]`; values `[Total Tickets]`, `[Unresolved Backlog]`, `[Overall SLA Compliance %]`, `[Average Response Hours]`, `[Average Resolution Hours]`, `[Customer Rating]` | Shows current owner at the fixed snapshot; do not substitute historical team |
| Date slicer | `DimCreatedDate[Date]` | Between style; filters by ticket creation date |
| Priority slicer | `FactTickets[priority]` | Dropdown or tile; multi-select enabled |
| Team slicer | `DimCurrentTeam[team_name]` | Dropdown; current snapshot ownership |

The trend is a creation-volume trend. The model is an end-state snapshot and cannot reconstruct historical daily backlog. Avoid labeling any line as “backlog trend” unless status-history snapshots are added later.

## Manual Power BI Desktop steps

### 1. Load and validate the model

1. Follow `docs/power_bi_model.md` to create parameters, Power Query queries, role-playing dimensions, relationships, and measures.
2. In Model view, confirm that `FactTickets` is one row per ticket and that assignment history and feedback remain separate fact tables.
3. Confirm every relationship is single-direction as documented. Delete automatically generated relationships that create a second path.
4. Mark `DimCreatedDate` as a date table and sort its `Month` by `MonthNumber`. Sort `YearMonth` by `YearMonthNumber` if that column is available; otherwise use `Date` on a continuous month axis.
5. Format ticket counts as whole numbers, SLA measures as percentages with two decimals, durations as decimals with two decimals, and customer rating as a decimal with two decimals.

### 2. Create the page shell

1. Add a new report page named **Executive Overview**.
2. Choose **Format page → Canvas settings → 16:9**.
3. Add the title **Customer Support Executive Overview** and a small subtitle: **Synthetic portfolio data | UTC | Snapshot 1 July 2026**.
4. Enable **View → Gridlines** and **Snap to grid** while arranging visuals.
5. Reserve the top-right area for the three slicers and keep the bottom edge for the assumptions note.

### 3. Add KPI cards

1. Insert six Card visuals in one row.
2. Assign the measures in this order: `[Total Tickets]`, `[Unresolved Backlog]`, `[Overall SLA Compliance %]`, `[Average Response Hours]`, `[Average Resolution Hours]`, and `[Customer Rating]`.
3. Use the titles **Total Tickets**, **Open Backlog**, **Overall SLA Compliance**, **Avg Response**, **Avg Resolution**, and **Customer Rating**.
4. Turn category labels on and unnecessary visual headers off. Use consistent padding, font size, and background.
5. Add tooltips clarifying denominators: SLA excludes Pending, response excludes unanswered, resolution excludes unresolved, and rating excludes missing feedback.

### 4. Add trend and distribution visuals

1. Add a Line chart. Put `DimCreatedDate[YearMonth]` on X-axis and `[Total Tickets]` on Y-axis. Set the X-axis to chronological order and title it **Ticket Volume Trend**.
2. Add a Clustered bar chart for priority. Put `FactTickets[priority]` on Y-axis and `[Total Tickets]` on X-axis. Title it **Tickets by Priority**.
3. Add a second Clustered bar chart. Put `FactTickets[category]` on Y-axis and `[Total Tickets]` on X-axis, sort descending, and title it **Tickets by Category**.
4. Turn data labels on only when they remain readable. Keep zero baselines for bar charts.

### 5. Add team comparison

1. Insert a Matrix visual.
2. Add `DimCurrentTeam[team_name]` to Rows.
3. Add `[Total Tickets]`, `[Unresolved Backlog]`, `[Overall SLA Compliance %]`, `[Average Response Hours]`, `[Average Resolution Hours]`, and `[Customer Rating]` to Values.
4. Apply conditional formatting to SLA and backlog values. Use the same thresholds across all teams and state that they are presentation aids, not contractual targets.
5. Keep totals on for volume and backlog. Treat the total-row SLA, durations, and rating as recalculated portfolio measures, not averages of displayed team values.

### 6. Add and configure slicers

1. Add a Between slicer using `DimCreatedDate[Date]`.
2. Add dropdown slicers for `FactTickets[priority]` and `DimCurrentTeam[team_name]`.
3. Use **Format → Edit interactions** and confirm every slicer filters all six KPI cards and all four analysis visuals.
4. Do not use `DimHistoricalTeam` on this page; it is intended for assignment-history analysis and would not filter the current ticket KPIs.
5. Add a **Reset filters** bookmark and button after confirming the default state.

### 7. Final usability checks

1. Verify titles state exactly what each metric measures. Avoid the ambiguous title “SLA %”; use **Overall SLA Compliance**.
2. Test a single priority and a single team selection. Every value should change consistently, while the customer rating may be blank when no feedback exists in a very narrow selection.
3. Test a date range. It filters by ticket creation date; note that rating and resolution outcomes still describe those created tickets at the snapshot.
4. Use **View → Performance analyzer** and confirm visuals do not depend on merged assignment-history rows.
5. Add alt text to each visual and check color contrast before exporting screenshots.

## SQL reconciliation

Run `sql/power_bi_reconciliation.sql` against the loaded PostgreSQL database. With all slicers cleared, compare the Power BI cards with these independently calculated synthetic-data targets:

| Executive KPI | DAX measure | SQL column | Expected value |
| --- | --- | --- | ---: |
| Total Tickets | `[Total Tickets]` | `total_tickets` | 10,000 |
| Open Backlog | `[Unresolved Backlog]` | `unresolved_backlog` | 1,136 |
| Overall SLA Compliance | `[Overall SLA Compliance %]` | `overall_sla_compliance_pct` | 44.06% |
| Average Response Hours | `[Average Response Hours]` | `average_response_hours` | 2.70 |
| Average Resolution Hours | `[Average Resolution Hours]` | `average_resolution_hours` | 40.57 |
| Customer Rating | `[Customer Rating]` | `average_csat` | 3.87 |

The expected values were verified against the independent Pandas baseline in `reports/reporting_reconciliation.json`. `database_compared` is currently `false`, so a live PostgreSQL execution still must be performed after the database is configured. Do not mark the SQL check complete merely because the static formulas match.

For a sliced comparison, copy the selected ticket predicates into the `ticket_metrics` CTE. Filter feedback through the selected ticket IDs so team, priority, and created-date context matches Power BI. Never join assignment history into this reconciliation: its one-to-many rows would multiply ticket counts.

## Acceptance checklist

- Six headline cards match the unfiltered SQL result.
- Ticket trend totals 10,000 with all slicers cleared.
- Priority and category bars each total 10,000.
- Current-team ticket counts total 10,000.
- Date, priority, and current-team slicers filter every visual.
- SLA Pending tickets are excluded from the compliance denominator.
- Unanswered and unresolved tickets are excluded from the corresponding duration averages.
- Missing feedback is not treated as a zero rating.
- No assignment-history join multiplies ticket counts.
- The page visibly labels the dataset synthetic and the SLA targets illustrative.
