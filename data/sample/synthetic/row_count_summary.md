# Synthetic Data Summary

Seed: 42. Snapshot: 2026-07-01T00:00:00+00:00. All records are fictional.

| Table | Rows |
| --- | ---: |
| customers | 2,500 |
| teams | 3 |
| agents | 30 |
| tickets | 10,000 |
| assignment_history | 14,035 |
| customer_feedback | 3,758 |

## Scenario counts

| Scenario | Tickets |
| --- | ---: |
| Unresolved | 1,136 |
| Reopened at least once | 931 |
| Reassigned (including reopen handoffs) | 3,312 |
| Response SLA breached | 1,976 |
| Resolution SLA breached | 4,603 |
| With feedback | 3,758 |

## Ticket statuses

| Status | Tickets |
| --- | ---: |
| Closed | 8,757 |
| In Progress | 591 |
| Open | 204 |
| Pending | 341 |
| Resolved | 107 |

All 7 validation groups passed before export. Tests also validate the CSVs after reloading.

Scenario counts overlap. They are simulated operational patterns, not real business findings.
