# Business Requirements

## 1. Purpose and business objectives

Provide support managers with a consistent view of demand, service speed, SLA performance, backlog, and customer feedback so they can prioritize work and investigate operational problems.

The project should help stakeholders:

- Identify demand patterns to inform staffing discussions.
- Detect slow responses, slow resolutions, and missed SLA commitments.
- Identify aging unresolved tickets for follow-up.
- Compare team workload and performance with priority and channel context.
- Understand satisfaction alongside survey participation.

No target improvement is promised until a baseline is measured.

## 2. Stakeholders and decisions

| Stakeholder | Questions and decisions |
| --- | --- |
| Support manager | Where should workload or staffing be reviewed? |
| Team lead | Which unresolved or breached tickets need attention? |
| Operations analyst | Are metrics consistent, complete, and trustworthy? |
| Business sponsor | Is support meeting service commitments and customer expectations? |

## 3. Scope

In scope: ticket volume, first response time, resolution time, first response and resolution SLA compliance, team summaries, unresolved ticket counts and age, and CSAT. Include trends and filters for creation date, team, priority, channel, and category.

The synthetic-data stage also includes customer, team, and agent dimensions, ticket assignment history, and at most one reopening cycle per ticket.

Out of scope: live API integrations, predictive modeling, automated alerts, business-hour calendars, holiday calendars, paused SLA clocks, multiple reopening cycles, agent-level rankings, and production deployment.

## 4. Requirements

| ID | Requirement | Acceptance criteria for the completed project |
| --- | --- | --- |
| BR-01 | Analyze ticket demand | Counts reconcile to distinct valid ticket IDs; trends support daily and monthly views. |
| BR-02 | Measure service speed | Average and median response and resolution hours follow the KPI definitions; missing events are excluded and disclosed. |
| BR-03 | Measure SLA compliance | Separate response, resolution, and combined metrics include overdue unfinished tickets and exclude pending deadlines. |
| BR-04 | Show team performance | Team summaries include volume, speed, SLA, backlog, and CSAT with sample sizes and priority context. |
| BR-05 | Analyze unresolved tickets | Show count, percentage, age buckets, oldest tickets, and overdue resolution tickets at the snapshot time. |
| BR-06 | Analyze satisfaction | Show average score, positive-score percentage, and survey response rate; never replace missing scores with zero. |
| BR-07 | Provide interactive reporting | Power BI pages support creation-date, team, priority, channel, and category filters and display the snapshot time. |
| BR-08 | Validate source data | Document duplicate IDs, invalid categories, impossible timestamps, missing policies, and invalid ratings; rejected records are traceable. |
| BR-09 | Make results reproducible | Record input files, snapshot time, policy assumptions, and cleaning steps; Python and SQL metrics reconcile on a known sample. |

## 5. Analysis assumptions

- One row represents one ticket in a fixed snapshot. Timestamps use UTC.
- Use elapsed calendar hours, 24 hours a day, seven days a week. There are no paused clocks.
- Set and record a fixed `analysis_as_of` timestamp; source events must not occur after it.
- Statuses are Open, In Progress, Pending, Resolved, and Closed. Pending tickets remain unresolved and their SLA clocks continue.
- The first human reply is the first response; automated acknowledgments do not qualify.
- SLA priority is the priority captured at creation and is fixed for this version.
- Team is the assigned team at the snapshot. Assignment history supports ownership and transfer analysis; agents retain a fixed home team.
- A ticket may reopen once. Keep its initial resolution and reopen timestamps, but use its final resolution for resolution-time and SLA metrics. Unresolved reopened tickets have a null final resolution. SLA clocks run from original creation without resetting or pausing.
- Satisfaction is an optional score from 1 to 5, collected for resolved or closed tickets.
- Trends and date filters use ticket creation date; backlog means unresolved tickets from that selected creation cohort at the snapshot. This version does not reconstruct historical daily backlog.

## 6. Illustrative SLA policy

These are project assumptions, not contractual or industry-standard commitments.

| Priority | First response target (hours) | Resolution target (hours) |
| --- | ---: | ---: |
| Critical | 1 | 8 |
| High | 4 | 24 |
| Medium | 8 | 48 |
| Low | 24 | 72 |

An event exactly at the target meets the SLA. An unfinished event exactly at its deadline remains pending; it becomes breached only after the deadline.

## 7. Planned deliverables and completion checks

Deliver a documented synthetic dataset, Python cleaning workflow, PostgreSQL schema, SQL KPI queries, Power BI report, and findings report in later milestones.

Before calling the project complete, reconcile Python, SQL, and dashboard totals; verify deadline boundary cases and missing feedback handling; show data-quality exclusions and KPI denominators; and provide business recommendations supported by the results.

## 8. Limitations and interpretation

Team comparisons may reflect workload complexity and staffing differences, not individual productivity. Missing feedback can bias satisfaction results. Assignment history records ownership, not time actively working; the dataset does not include every status change or more than one reopen cycle. Synthetic findings demonstrate analytical methods rather than actual client performance.
