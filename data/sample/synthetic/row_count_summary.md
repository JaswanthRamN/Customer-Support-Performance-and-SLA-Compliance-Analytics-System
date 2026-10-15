# Synthetic Data Summary

Seed: 42. Snapshot: 2026-07-01T00:00:00+00:00. All records are fictional.

| Table | Rows |
| --- | ---: |
| customers | 2,500 |
| teams | 3 |
| agents | 30 |
| tickets | 10,000 |
| assignment_history | 14,024 |
| customer_feedback | 3,756 |

## Scenario counts

| Scenario | Tickets |
| --- | ---: |
| Unresolved | 1,188 |
| Reopened at least once | 925 |
| Reassigned (including reopen handoffs) | 3,304 |
| Response SLA breached | 1,957 |
| Resolution SLA breached | 4,584 |
| With feedback | 3,756 |

## Ticket statuses

| Status | Tickets |
| --- | ---: |
| Closed | 8,730 |
| In Progress | 613 |
| Open | 209 |
| Pending | 366 |
| Resolved | 82 |

All 7 validation groups passed before export. Tests also validate the CSVs after reloading.

Scenario counts overlap. They are simulated operational patterns, not real business findings.
