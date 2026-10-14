# Data Dictionary

## Data model and conventions

The planned `tickets` table contains one row per ticket at a fixed snapshot. The planned `sla_policies` table contains one row per priority. Join them on `priority`; no SQL tables exist yet.

Timestamp strings use ISO 8601 with a UTC offset, such as `2026-01-05T09:00:00Z`. Parse them as timezone-aware timestamps in Pandas and store them as PostgreSQL `TIMESTAMPTZ`. Durations are decimal hours, not rounded values used for SLA decisions.

## Tickets: source columns

| Field | PostgreSQL type | Required? | Meaning / allowed values |
| --- | --- | --- | --- |
| ticket_id | TEXT | Yes | Unique nonblank ticket identifier, e.g. T000001 |
| created_at | TIMESTAMPTZ | Yes | Ticket creation time in UTC |
| first_response_at | TIMESTAMPTZ | Conditional | First human reply; null when no reply has occurred |
| resolved_at | TIMESTAMPTZ | Conditional | Resolution event time; required for Resolved and Closed |
| status | TEXT | Yes | Open, In Progress, Pending, Resolved, Closed |
| priority | TEXT | Yes | Critical, High, Medium, Low; priority at creation |
| team | TEXT | Yes | Snapshot assignment: Tier 1 Support, Technical Support, or Billing Support |
| channel | TEXT | Yes | Email, Chat, Phone, or Web |
| category | TEXT | Yes | Account, Technical, Billing, or General |
| csat_score | SMALLINT | No | Integer 1–5; null means no feedback; only on Resolved or Closed tickets |

For this simplified dataset, Open, In Progress, and Pending tickets have a null `resolved_at`. Resolved and Closed tickets must have a first response and a resolution timestamp. No customer identifiers or message contents are needed.

## SLA policies: source columns

| Field | PostgreSQL type | Required? | Meaning |
| --- | --- | --- | --- |
| priority | TEXT | Yes | Unique priority value; matches tickets.priority |
| response_target_hours | NUMERIC(10,2) | Yes | Positive allowed elapsed hours to first response |
| resolution_target_hours | NUMERIC(10,2) | Yes | Positive allowed elapsed hours to resolution |

Use the illustrative thresholds in the business requirements. Policies are fixed for the whole dataset in this version.

## Analysis parameter

`analysis_as_of` is a single fixed UTC timestamp supplied to the analysis, not a source ticket column. Save it with the output metadata and display it on the dashboard. Reuse it across Python, SQL, and Power BI so results are reproducible.

## Planned derived fields

| Field | Type / unit | Definition |
| --- | --- | --- |
| created_date | Date in UTC | Calendar date of created_at |
| response_hours | Decimal hours, nullable | (first_response_at − created_at) in hours |
| resolution_hours | Decimal hours, nullable | (resolved_at − created_at) in hours |
| is_unresolved | Boolean | Status is Open, In Progress, or Pending |
| unresolved_age_hours | Decimal hours, nullable | (analysis_as_of − created_at) for unresolved tickets |
| backlog_age_bucket | Text, nullable | Under 24h; 24–under 48h; 48–under 72h; 72h or more |
| response_deadline | UTC timestamp | created_at + response_target_hours |
| resolution_deadline | UTC timestamp | created_at + resolution_target_hours |
| response_sla_status | Text | Met, Breached, or Pending under KPI rules |
| resolution_sla_status | Text | Met, Breached, or Pending under KPI rules |
| overall_sla_status | Text | Met, Breached, or Pending under KPI rules |

## Validation and missing-data rules

1. Require all source columns, including optional event and feedback columns. Trim whitespace and normalize documented category spellings before validation; do not guess unknown values.
2. Require unique ticket IDs. Remove only completely identical duplicate rows, recording the count. Quarantine all rows for conflicting duplicate IDs rather than choosing a winner.
3. Require parseable timestamps with an explicit timezone and `created_at <= analysis_as_of`.
4. When present, require `created_at <= first_response_at <= analysis_as_of` and `created_at <= resolved_at <= analysis_as_of`. For resolved tickets, require `first_response_at <= resolved_at`.
5. Enforce the status/event relationships and accepted category values above. Unknown teams, priorities, or missing SLA policies require review.
6. Validate positive SLA targets and one policy per priority. Require integer CSAT ratings from 1 to 5, only on resolved or closed tickets.
7. Keep valid missing replies, resolutions, and ratings as null. Do not impute zero durations or satisfaction scores.
8. Preserve raw input. Store rejected rows and rejection reasons separately; use accepted records for the KPIs and disclose input, accepted, removed duplicate, and rejected counts.

## Beginner example

A High-priority ticket created at 09:00 UTC and first answered at 12:00 UTC has `response_hours = 3`. Its response SLA is Met because the target is 4 hours. A null resolution timestamp means it remains unresolved; the resolution SLA depends on whether the fixed snapshot is past its 24-hour deadline.
