# KPI Definitions

## Shared rules

Use accepted, unique tickets after validation. `N` means the count of tickets in the selected creation-date cohort and other active filters. All timestamps are UTC and durations use calendar hours. Use the same fixed `analysis_as_of` in every tool.

Calculate using full precision; round only displayed results. Express percentages as 0–100%. When a denominator is zero, display N/A rather than 0%. Always show the relevant sample size or denominator.

Resolved tickets have status Resolved or Closed. Unresolved tickets have status Open, In Progress, or Pending. Resolution time ends at `resolved_at`, including when the current status is Closed.

For the synthetic dataset, a reopened ticket retains `initial_resolved_at` and `reopened_at`; `resolved_at` represents final resolution and remains null until the reopened work is completed. Measure from original creation without resetting the SLA clock or subtracting the interval spent resolved. This is a simulation assumption rather than a universal support policy. Assignment ownership persists after closure and does not define unresolved status.

The six-table dataset normalizes team and feedback fields: join `tickets.current_team_id` to `teams.team_id` for team labels, and left join tickets to `customer_feedback` on ticket_id for CSAT. Never count assignment-history rows as tickets. A ticket can have many assignments but at most one current feedback response.

## Core metrics

| KPI | Definition and denominator | Business interpretation |
| --- | --- | --- |
| Ticket volume | N; group created_at by UTC day, week starting Monday, or month | Demand and workload entering support |
| Average first response time | Sum of response_hours / number of tickets with first_response_at | Typical mean wait for a human reply among answered tickets |
| Median first response time | Median response_hours among answered tickets | Central wait time less affected by extreme values |
| Average resolution time | Sum of resolution_hours / number of resolved tickets | Mean elapsed time to resolution among completed tickets |
| Median resolution time | Median resolution_hours among resolved tickets | Central resolution time less affected by extreme values |
| First response SLA compliance | 100 × response Met / (response Met + response Breached) | Share of assessable first responses meeting their commitment |
| Resolution SLA compliance | 100 × resolution Met / (resolution Met + resolution Breached) | Share of assessable resolutions meeting their commitment |
| Overall SLA compliance | 100 × overall Met / (overall Met + overall Breached) | Share of assessable tickets meeting both commitments |
| Unresolved ticket count | Count of unresolved tickets at analysis_as_of | Outstanding work in the selected creation cohort |
| Unresolved ticket percentage | 100 × unresolved ticket count / N | Share of the cohort still outstanding |
| Average unresolved age | Sum of unresolved_age_hours / unresolved ticket count | How long outstanding tickets have been waiting |
| Overdue unresolved count | Count of unresolved tickets with resolution_sla_status = Breached | Outstanding work already past the resolution commitment |
| Average CSAT | Sum of non-null csat_score / number of rated resolved tickets | Average reported satisfaction on a 1–5 scale |
| Positive CSAT percentage | 100 × number of ratings 4 or 5 / number of rated resolved tickets | Share of respondents reporting positive satisfaction |
| CSAT survey response rate | 100 × number of rated resolved tickets / number of resolved tickets | Coverage of customer feedback among completed tickets |
| Reassigned ticket count | Distinct tickets with at least one `Reassignment` history row | Tickets that changed owners during ordinary work |
| Reassignment event count | Count of `Reassignment` history rows | Total ordinary owner changes; can exceed reassigned-ticket count |
| Reopened ticket count | Count of tickets with `reopen_count = 1` | Tickets reopened after initial resolution |
| Reopened unresolved count | Count with `reopen_count = 1` and null final resolved_at | Reopened work still outstanding at the snapshot |

Response and resolution duration metrics exclude missing events. Display unanswered and unresolved counts beside them because completed-event averages alone can hide waiting customers. For the synthetic dataset, assume all resolved tickets were offered a survey; real data would require a survey invitation field for the response-rate denominator.

The EDA report includes average **and median** durations and CSAT, along with sample sizes. Averages can be pulled upward by the deliberately long-tailed simulation. Do not interpret an average–median gap as a real service benchmark. `Reopened` handoffs in assignment history are excluded from ordinary reassignment counts; report them separately through ticket reopening fields.

## SLA classification

For each commitment separately, let `deadline = created_at + target_hours`, `event_at` be its first response or resolution timestamp, and `snapshot = analysis_as_of`.

| Condition | Classification |
| --- | --- |
| Event exists and event_at <= deadline | Met |
| Event exists and event_at > deadline | Breached |
| Event is missing and snapshot > deadline | Breached |
| Event is missing and snapshot <= deadline | Pending |

Pending means the outcome is not yet assessable; exclude these tickets from that commitment's compliance denominator and report their count. Breached includes overdue unfinished work, not only completed late events.

Overall SLA status is Breached if either commitment is Breached; Met if both are Met; otherwise Pending. This treats a known missed commitment as an overall breach even if the other commitment is still pending. Overall compliance is calculated from ticket classifications, not by averaging the two separate SLA percentages.

## Worked response SLA example

Five High-priority tickets have a 4-hour response target:

| Ticket | Situation at snapshot | Response SLA |
| --- | --- | --- |
| A | Responded after 2 hours | Met |
| B | Responded after exactly 4 hours | Met |
| C | Responded after 5 hours | Breached |
| D | No response; age is 6 hours | Breached |
| E | No response; age is 3 hours | Pending |

Response SLA compliance is `2 / (2 + 2) × 100 = 50%`. The assessable sample size is 4 and the pending count is 1. Mean first response time is `(2 + 4 + 5) / 3 = 3.67 hours`; it covers the three answered tickets only.

## Team performance

Group core KPIs by the snapshot `team`. Show ticket volume, resolved count, unresolved count, response and resolution averages/medians, SLA compliance with assessable counts, and CSAT with rating counts. Recalculate ratios from ticket-level counts within each team; never average team percentages to produce the total.

Compare teams within similar priorities, categories, and channels. Current assignment may differ from the team that originally handled the ticket; assignment history allows this distinction to be explored. Staffing capacity and active work time are unavailable, so do not interpret volume as per-agent productivity or use these metrics alone to rank employees.

## Backlog age and date filtering

For unresolved tickets, calculate age from creation to the snapshot. Use mutually exclusive buckets: `[0,24)`, `[24,48)`, `[48,72)`, and `[72,infinity)` hours. Show oldest unresolved tickets by age, descending.

A creation-date filter restricts every metric to that cohort. For example, a January filter shows January-created tickets still unresolved at the snapshot, even if the snapshot is in February. Historical backlog trends require event history and are outside this version's scope.

## Planned validation before implementation is accepted

- Hand-calculate a small sample and compare Python, SQL, and Power BI results.
- Verify events exactly at and just after deadlines, and missing events before, at, and after deadlines.
- Verify that an overall breach remains a breach when the other commitment is pending.
- Check all-unrated, all-pending, and empty cohorts return N/A where appropriate.
- Reconcile grouped ticket counts and backlog buckets to the accepted ticket totals.
- Confirm that missing CSAT is excluded, and that SLA Pending differs from the ticket status Pending.
