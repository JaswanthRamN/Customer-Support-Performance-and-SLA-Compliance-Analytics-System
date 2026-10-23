# Exploratory Data Analysis — Synthetic Customer Support Data

**Synthetic-data observation.** Fixed snapshot: 2026-07-01T00:00:00+00:00. Tickets created from 2026-01-01 through 2026-06-30 (UTC). All records are fictional.

## Scope and data checks

Analyzed **10,000 accepted tickets** from the cleaned six-table dataset. The cleaning report recorded **0 rejected records** across all tables. The ticket, team, feedback, and assignment joins were checked so each ticket contributes once to ticket-level KPIs. All event times are UTC; elapsed hours use a 24/7 calendar clock.

## Ticket demand and mix

Synthetic-data observation: monthly arrivals rose from **1,385 in 2026-01** to **1,910 in 2026-06**. The six-month average was **1,666.7 tickets per month**. The generator was configured with rising monthly demand weights, so this is an intended simulation pattern rather than a discovered real-world trend.

| Month | Tickets |
| --- | ---: |
| 2026-01 | 1,385 |
| 2026-02 | 1,432 |
| 2026-03 | 1,649 |
| 2026-04 | 1,712 |
| 2026-05 | 1,912 |
| 2026-06 | 1,910 |

Synthetic-data observation: **Technical** was the largest category (**3,507 tickets**). The tables below show the priority, category, channel, and snapshot-team mix. Team reflects final recorded ownership; it does not indicate all work done on a ticket.

### Priority

| Priority | Tickets |
| --- | --- |
| Critical | 605 |
| High | 2,182 |
| Medium | 4,701 |
| Low | 2,512 |

### Category

| Category | Tickets |
| --- | --- |
| Billing | 2,471 |
| Technical | 3,507 |
| Account | 2,530 |
| General | 1,492 |

### Channel

| Channel | Tickets |
| --- | --- |
| Email | 3,998 |
| Chat | 2,514 |
| Web | 2,048 |
| Phone | 1,440 |

### Current team

| Current team | Tickets |
| --- | --- |
| Tier 1 Support | 3,687 |
| Billing Support | 2,918 |
| Technical Support | 3,395 |

## Service speed and SLA

Synthetic-data observation: first response time was **2.70 h on average** and **1.25 h at the median**, among **9,796 answered tickets**. **204 tickets** had no first response and are excluded from those duration figures.

Final resolution time was **40.57 h on average** and **18.33 h at the median**, among **8,864 resolved tickets**. The gap between average and median reflects the simulated long tail of slower cases; it should not be interpreted as a real team benchmark.

| Priority | Answered | Response average (h) | Response median (h) | Resolved | Resolution average (h) | Resolution median (h) |
| --- | --- | --- | --- | --- | --- | --- |
| Critical | 593 | 0.15 | 0.08 | 530 | 12.86 | 3.02 |
| High | 2,147 | 0.67 | 0.40 | 1,959 | 16.72 | 6.21 |
| Medium | 4,597 | 2.57 | 1.51 | 4,158 | 33.43 | 18.45 |
| Low | 2,459 | 5.32 | 3.08 | 2,217 | 81.65 | 53.72 |

SLA compliance uses **Met / (Met + Breached)**. Pending commitments are reported separately and excluded from the denominator. Breached includes overdue unfinished tickets. Overall SLA is a ticket-level classification, not an average of response and resolution rates.

| Commitment | Met | Breached | Pending | Assessable | Compliance |
| --- | ---: | ---: | ---: | ---: | ---: |
| Response | 8,013 | 1,976 | 11 | 9,989 | 80.22% |
| Resolution | 5,343 | 4,603 | 54 | 9,946 | 53.72% |
| Overall | 4,387 | 5,569 | 44 | 9,956 | 44.06% |

### SLA by priority

| Priority | Commitment | Met | Breached | Pending | Assessable | Compliance |
| --- | --- | --- | --- | --- | --- | --- |
| Critical | response | 494 | 111 | 0 | 605 | 81.65% |
| Critical | resolution | 316 | 289 | 0 | 605 | 52.23% |
| Critical | overall | 263 | 342 | 0 | 605 | 43.47% |
| High | response | 1,745 | 436 | 1 | 2,181 | 80.01% |
| High | resolution | 1,158 | 1,023 | 1 | 2,181 | 53.09% |
| High | overall | 943 | 1,238 | 1 | 2,181 | 43.24% |
| Medium | response | 3,783 | 914 | 4 | 4,697 | 80.54% |
| Medium | resolution | 2,498 | 2,180 | 23 | 4,678 | 53.40% |
| Medium | overall | 2,066 | 2,617 | 18 | 4,683 | 44.12% |
| Low | response | 1,991 | 515 | 6 | 2,506 | 79.45% |
| Low | resolution | 1,371 | 1,111 | 30 | 2,482 | 55.24% |
| Low | overall | 1,115 | 1,372 | 25 | 2,487 | 44.83% |

## Backlog, reassignments, and reopened tickets

Synthetic-data observation: **1,136 tickets (11.36%)** were unresolved at the snapshot; **1,082** were past their resolution deadline. The largest priority backlog was **Medium (543)**. Unresolved tickets had an average age of **1,874.71 h** and a median age of **1,741.00 h** since creation.

Historical daily backlog cannot be reconstructed from these snapshot records alone. Age buckets below are mutually exclusive and refer to unresolved tickets at the one fixed snapshot.

| Age bucket | Tickets |
| --- | --- |
| Under 24h | 50 |
| 24–<48h | 21 |
| 48–<72h | 9 |
| 72h+ | 1,056 |

Synthetic-data observation: **2,617 tickets** had at least one ordinary reassignment, totaling **3,104 ordinary reassignment events**. **931 tickets** reopened once; **128** of them remained unresolved at the snapshot. Reopen handoffs are distinct from ordinary reassignments. Ownership history is not a measure of active handle time.

### Ordinary reassignments per ticket

| Reassignments | Tickets |
| --- | --- |
| 0 | 7,383 |
| 1 | 2,130 |
| 2 | 487 |

### Reopened tickets by priority

| Priority | Tickets | Reopened |
| --- | --- | --- |
| Critical | 605 | 60 |
| High | 2,182 | 220 |
| Medium | 4,701 | 423 |
| Low | 2,512 | 228 |

## Customer ratings and coverage

Synthetic-data observation: **3,758 resolved tickets** had feedback, while **5,106 resolved tickets** did not. Coverage was **42.40% of resolved tickets** under the synthetic assumption that all resolved tickets were offered a survey. Missing feedback was excluded, never scored as zero.

Among rated tickets, average CSAT was **3.87/5**, median was **4.00/5**, and **66.92%** of ratings were 4 or 5. Feedback was generated with lower tendencies for breached and reopened cases; associations in this simulation do not establish causation.

### Rating distribution

| Rating | Responses |
| --- | --- |
| 1 | 32 |
| 2 | 229 |
| 3 | 982 |
| 4 | 1,481 |
| 5 | 1,034 |

### Feedback by priority

| Priority | Resolved | Rated | Coverage | Average CSAT | Median CSAT |
| --- | --- | --- | --- | --- | --- |
| Critical | 530 | 207 | 39.06% | 3.87 | 4.00 |
| High | 1,959 | 811 | 41.40% | 3.85 | 4.00 |
| Medium | 4,158 | 1,780 | 42.81% | 3.88 | 4.00 |
| Low | 2,217 | 960 | 43.30% | 3.86 | 4.00 |

## Preliminary portfolio insights

1. **Demand mix:** January-to-June ticket volume changed by **37.91%**. Technical tickets were the largest category at **3,507**. The generator deliberately raises demand weights, so use this as a portfolio staffing discussion rather than evidence for a real staffing decision.
2. **SLA and backlog:** response compliance was **80.22%**, while resolution compliance was **53.72%**. Of **1,136** unresolved tickets, **1,082 (95.25%)** were overdue and **1,056** were at least 72 hours old. Completed-ticket averages alone hide this queue.
3. **Ownership and reopening:** **2,617** tickets had an ordinary reassignment and **931** reopened. These are useful simulated investigation groups; ownership history does not show effort or root cause.
4. **Satisfaction coverage:** only **42.40%** of finally resolved tickets had feedback. Report the **3,758** rated-ticket denominator beside the **3.87/5** average; no-feedback cases are not zero ratings.

## KPI definitions used

- **Volume:** count of distinct accepted tickets by UTC creation month, priority, category, channel, or current team; denominator for share comparisons is all accepted tickets.
- **Response hours:** first human response minus creation in calendar hours; average and median among answered tickets only. Unanswered count is separate.
- **Resolution hours:** final resolution minus creation in calendar hours; average and median among finally resolved tickets only. Reopening does not reset the clock.
- **SLA compliance:** Met divided by Met plus Breached, for response, resolution, or overall status. Pending is excluded and shown separately. Overall breach occurs when either component breaches.
- **Backlog:** tickets lacking final resolution at the snapshot; overdue means their resolution SLA is Breached. Age runs from creation to snapshot.
- **Reassignment:** ordinary `Reassignment` rows in assignment history; tickets with at least one such row are counted once. A `Reopened` handoff is counted separately.
- **Reopened:** tickets with `reopen_count = 1`; unresolved reopened tickets still lack final resolution.
- **CSAT:** 1–5 score from the optional feedback table. Mean, median, and positive share use rated tickets; coverage is rated resolved tickets divided by all resolved tickets.

## Charts

- [01 Monthly Volume](charts/01_monthly_volume.png)
- [02 Ticket Mix](charts/02_ticket_mix.png)
- [03 Service Times](charts/03_service_times.png)
- [04 Sla Compliance](charts/04_sla_compliance.png)
- [05 Backlog](charts/05_backlog.png)
- [06 Reassignments Reopens](charts/06_reassignments_reopens.png)
- [07 Customer Ratings](charts/07_customer_ratings.png)

## Limits

All findings are synthetic-data observations from a seeded simulation. SLA targets and feedback behavior are design assumptions, not contractual standards. Priorities, channels, and ticket complexity differ across groups; descriptive comparisons are not causal estimates. Team is the recorded current owner and cannot measure individual productivity. The snapshot does not reconstruct historical daily backlog or every status transition. Feedback is optional and can be biased.
