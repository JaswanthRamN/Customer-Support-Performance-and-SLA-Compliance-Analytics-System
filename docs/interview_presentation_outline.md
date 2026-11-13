# Interview Presentation Outline

## Recommended format

Use 10–12 slides for a 12–15 minute presentation, followed by questions. Keep a visible **Synthetic portfolio data** label on every results slide. Do not imply that a PBIX, live deployment, PostgreSQL execution, Docker run, or Airflow run exists unless completed after this outline was written.

## Slide 1 — Project and role

**Title:** Customer Support Performance and SLA Compliance Analytics System  
**Subtitle:** End-to-end Business Analyst portfolio project using validated synthetic data

Talking points:

- I translated a support-management problem into requirements, data rules, KPIs, a reporting model, APIs, orchestration, and dashboard specifications.
- My focus was consistent business logic and traceable evidence across tools.
- All records and observations are synthetic.

## Slide 2 — Business problem

Visual: five business questions or a simple problem-to-decision flow.

Talking points:

- Managers need a single view of demand, response, resolution, SLA risk, backlog, and customer feedback.
- Assignment history can multiply ticket counts, and incomplete events or surveys can distort averages.
- The analytical goal was trustworthy decision support, not just charts.

## Slide 3 — Objectives and stakeholders

Visual: stakeholder-to-decision table.

Talking points:

- Support manager: demand and staffing discussion.
- Team lead: overdue and aging ticket prioritization.
- Operations analyst: definition and reconciliation governance.
- Sponsor: service-commitment and satisfaction visibility.

## Slide 4 — Architecture and data model

Visual: generator → validation/cleaning → PostgreSQL/SQL → APIs/Power BI, with Airflow and Docker surrounding the flow.

Talking points:

- Six source datasets contain 30,326 rows, including 10,000 tickets and 14,035 assignment intervals.
- Ticket, assignment, and feedback facts remain separate.
- Current ownership and historical assignment are explicitly different analytical lenses.

## Slide 5 — Data quality and controls

Visual: quality scorecard.

Use only these validated numbers:

- 30,326 input rows; 30,326 accepted; 0 rejected.
- All foreign keys resolved.
- Row-count and checksum manifests matched.
- 1,136 legitimate null resolution timestamps were retained.

Talking points:

- Zero rejected rows reflects a valid generated source, not an absent quarantine design.
- Negative tests confirm invalid rows are reported and quarantined rather than silently discarded.

## Slide 6 — KPI governance and SLA logic

Visual: compact KPI denominator table and the four priority targets.

Talking points:

- Durations use only tickets with the relevant event.
- Compliance is Met divided by Met plus Breached; Pending is explicit.
- Exact deadline is compliant; missing at the exact deadline is still Pending.
- Missing feedback is never zero.

## Slide 7 — Demand and service-speed findings

Visuals: monthly-volume and service-time charts from `reports/eda/charts/`.

Validated synthetic findings:

- Monthly volume: 1,385 in January and 1,910 in June.
- Technical category: 3,507 tickets; Email channel: 3,998.
- Response: 2.70-hour mean, 1.25-hour median, 9,796 answered.
- Resolution: 40.57-hour mean, 18.33-hour median, 8,864 resolved.

Interpretation: mean-versus-median gaps show a simulated long tail and the need to display both.

## Slide 8 — SLA and backlog findings

Visuals: SLA and backlog charts.

Validated synthetic findings:

- Response compliance: 80.22%.
- Resolution compliance: 53.72%.
- Overall compliance: 44.06%.
- Backlog: 1,136; overdue: 1,082; age 72h+: 1,056.

Interpretation: the simulated operational priority is resolution flow and overdue backlog, not just first response.

## Slide 9 — Ownership, reopening, and satisfaction

Visual: three KPI groups with denominators.

Validated synthetic findings:

- 2,617 tickets had ordinary reassignments; 3,104 events.
- 931 reopened; 128 reopened and unresolved.
- 3,758 ratings; average 3.87/5; positive share 66.92%.
- Feedback coverage: 42.40%, so rating conclusions require caution.

## Slide 10 — SQL, APIs, and dashboard design

Visual: capability map, not screenshots of unbuilt products.

Talking points:

- SQL reporting begins at one row per ticket and pre-aggregates assignment history.
- FastAPI exposes aggregate analytics; Django REST Framework exposes ticket and assignment detail.
- Power BI assets define executive, SLA, team, backlog, and satisfaction pages.
- Current and historical team dimensions are separated to prevent unsupported attribution.

## Slide 11 — Recommendations

Present recommendations as conditional on confirmation with real data:

1. Triage overdue tickets by priority, deadline, and age.
2. Manage response and resolution SLAs separately.
3. Review reassigned and reopened cohorts for root causes.
4. Add structured operational reason codes and status-event history.
5. Improve survey invitation tracking and show feedback coverage beside CSAT.
6. Combine demand with staffing and skill data before changing capacity.

## Slide 12 — Limitations, validation, and next steps

Talking points:

- Synthetic results are illustrative and non-causal.
- 90 automated tests passed; data validation and Python analysis were executed.
- Live PostgreSQL reconciliation, Docker, Airflow execution, and Power BI refresh were not run in the audited environment.
- Next milestone: execute external runtimes, build the PBIX, and retain reconciliation evidence.

Close with: **The project demonstrates how I protect metric definitions, grain, and evidence from business question through delivery.**

## Likely interview questions

### Why show both average and median?

The simulated duration distributions are long-tailed. The mean describes total elapsed-time burden but is influenced by extreme values; the median describes the central ticket. Both require the eligible sample size.

### Why is resolution compliance lower than response compliance?

The validated synthetic data contains more simulated resolution delays. The project can identify the gap but cannot determine cause without workflow, staffing, complexity, and reason-code data.

### How did you prevent duplicate ticket counts?

Ticket metrics originate from a one-row-per-ticket fact. Assignment history is pre-aggregated before SQL joins and remains a separate fact in Power BI. Ticket measures use distinct ticket IDs where needed.

### Why not treat missing feedback as zero?

Missing means no observed rating, not dissatisfaction. A zero would be outside the valid 1–5 scale and would bias the average. I report feedback coverage separately.

### What would you do before production?

Execute live PostgreSQL reconciliation, build and validate the PBIX, run Docker and Airflow, add authentication and monitoring, use managed secrets, introduce status-event and staffing data, and agree operational targets with stakeholders.
