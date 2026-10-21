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

Synthetic-data observation: **Technical** was the largest category (**3,487 tickets**). The tables below show the priority, category, channel, and snapshot-team mix. Team reflects final recorded ownership; it does not indicate all work done on a ticket.

### Priority

| Priority | Tickets |
| --- | --- |
| Critical | 610 |
| High | 2,174 |
| Medium | 4,711 |
| Low | 2,505 |

### Category

| Category | Tickets |
| --- | --- |
| Billing | 2,482 |
| Technical | 3,487 |
| Account | 2,529 |
| General | 1,502 |

### Channel

| Channel | Tickets |
| --- | --- |
| Email | 4,013 |
| Chat | 2,515 |
| Web | 2,026 |
| Phone | 1,446 |

### Current team

| Current team | Tickets |
| --- | --- |
| Tier 1 Support | 3,692 |
| Billing Support | 2,932 |
| Technical Support | 3,376 |

## Service speed and SLA

Synthetic-data observation: first response time was **7.03 h on average** and **3.04 h at the median**, among **9,791 answered tickets**. **209 tickets** had no first response and are excluded from those duration figures.

Final resolution time was **57.72 h on average** and **33.52 h at the median**, among **8,812 resolved tickets**. The gap between average and median reflects the simulated long tail of slower cases; it should not be interpreted as a real team benchmark.

| Priority | Answered | Response average (h) | Response median (h) | Resolved | Resolution average (h) | Resolution median (h) |
| --- | --- | --- | --- | --- | --- | --- |
| Critical | 598 | 0.59 | 0.33 | 535 | 18.12 | 6.05 |
| High | 2,135 | 2.70 | 1.60 | 1,937 | 34.68 | 18.82 |
| Medium | 4,607 | 5.10 | 3.00 | 4,138 | 59.39 | 36.12 |
| Low | 2,451 | 16.01 | 9.19 | 2,202 | 84.48 | 56.27 |

SLA compliance uses **Met / (Met + Breached)**. Pending commitments are reported separately and excluded from the denominator. Breached includes overdue unfinished tickets. Overall SLA is a ticket-level classification, not an average of response and resolution rates.

| Commitment | Met | Breached | Pending | Assessable | Compliance |
| --- | ---: | ---: | ---: | ---: | ---: |
| Response | 8,029 | 1,957 | 14 | 9,986 | 80.40% |
| Resolution | 5,310 | 4,584 | 106 | 9,894 | 53.67% |
| Overall | 4,391 | 5,516 | 93 | 9,907 | 44.32% |

### SLA by priority

| Priority | Commitment | Met | Breached | Pending | Assessable | Compliance |
| --- | --- | --- | --- | --- | --- | --- |
| Critical | response | 499 | 111 | 0 | 610 | 81.80% |
| Critical | resolution | 319 | 290 | 1 | 609 | 52.38% |
| Critical | overall | 265 | 344 | 1 | 609 | 43.51% |
| High | response | 1,740 | 433 | 1 | 2,173 | 80.07% |
| High | resolution | 1,143 | 1,015 | 16 | 2,158 | 52.97% |
| High | overall | 936 | 1,226 | 12 | 2,162 | 43.29% |
| Medium | response | 3,807 | 899 | 5 | 4,706 | 80.90% |
| Medium | resolution | 2,520 | 2,138 | 53 | 4,658 | 54.10% |
| Medium | overall | 2,092 | 2,571 | 48 | 4,663 | 44.86% |
| Low | response | 1,983 | 514 | 8 | 2,497 | 79.42% |
| Low | resolution | 1,328 | 1,141 | 36 | 2,469 | 53.79% |
| Low | overall | 1,098 | 1,375 | 32 | 2,473 | 44.40% |

## Backlog, reassignments, and reopened tickets

Synthetic-data observation: **1,188 tickets (11.88%)** were unresolved at the snapshot; **1,082** were past their resolution deadline. The largest priority backlog was **Medium (573)**. Unresolved tickets had an average age of **1,796.74 h** and a median age of **1,628.54 h** since creation.

Historical daily backlog cannot be reconstructed from these snapshot records alone. Age buckets below are mutually exclusive and refer to unresolved tickets at the one fixed snapshot.

| Age bucket | Tickets |
| --- | --- |
| Under 24h | 67 |
| 24–<48h | 40 |
| 48–<72h | 10 |
| 72h+ | 1,071 |

Synthetic-data observation: **2,612 tickets** had at least one ordinary reassignment, totaling **3,099 ordinary reassignment events**. **925 tickets** reopened once; **131** of them remained unresolved at the snapshot. Reopen handoffs are distinct from ordinary reassignments. Ownership history is not a measure of active handle time.

### Ordinary reassignments per ticket

| Reassignments | Tickets |
| --- | --- |
| 0 | 7,388 |
| 1 | 2,125 |
| 2 | 487 |

### Reopened tickets by priority

| Priority | Tickets | Reopened |
| --- | --- | --- |
| Critical | 610 | 61 |
| High | 2,174 | 220 |
| Medium | 4,711 | 414 |
| Low | 2,505 | 230 |

## Customer ratings and coverage

Synthetic-data observation: **3,756 resolved tickets** had feedback, while **5,056 resolved tickets** did not. Coverage was **42.62% of resolved tickets** under the synthetic assumption that all resolved tickets were offered a survey. Missing feedback was excluded, never scored as zero.

Among rated tickets, average CSAT was **3.87/5**, median was **4.00/5**, and **66.93%** of ratings were 4 or 5. Feedback was generated with lower tendencies for breached and reopened cases; associations in this simulation do not establish causation.

### Rating distribution

| Rating | Responses |
| --- | --- |
| 1 | 31 |
| 2 | 226 |
| 3 | 985 |
| 4 | 1,479 |
| 5 | 1,035 |

### Feedback by priority

| Priority | Resolved | Rated | Coverage | Average CSAT | Median CSAT |
| --- | --- | --- | --- | --- | --- |
| Critical | 535 | 211 | 39.44% | 3.86 | 4.00 |
| High | 1,937 | 814 | 42.02% | 3.86 | 4.00 |
| Medium | 4,138 | 1,774 | 42.87% | 3.89 | 4.00 |
| Low | 2,202 | 957 | 43.46% | 3.85 | 4.00 |

## Preliminary portfolio insights

1. **Demand mix:** January-to-June ticket volume changed by **37.91%**. Technical tickets were the largest category at **3,487**. The generator deliberately raises demand weights, so use this as a portfolio staffing discussion rather than evidence for a real staffing decision.
2. **SLA and backlog:** response compliance was **80.40%**, while resolution compliance was **53.67%**. Of **1,188** unresolved tickets, **1,082 (91.08%)** were overdue and **1,071** were at least 72 hours old. Completed-ticket averages alone hide this queue.
3. **Ownership and reopening:** **2,612** tickets had an ordinary reassignment and **925** reopened. These are useful simulated investigation groups; ownership history does not show effort or root cause.
4. **Satisfaction coverage:** only **42.62%** of finally resolved tickets had feedback. Report the **3,756** rated-ticket denominator beside the **3.87/5** average; no-feedback cases are not zero ratings.

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
