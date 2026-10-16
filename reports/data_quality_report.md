# Data Quality Report

Snapshot: 2026-07-01T00:00:00+00:00

| Table | Input | Accepted | Rejected |
| --- | ---: | ---: | ---: |
| customers | 2,500 | 2,500 | 0 |
| teams | 3 | 3 | 0 |
| agents | 30 | 30 | 0 |
| tickets | 10,000 | 10,000 | 0 |
| assignment_history | 14,024 | 14,024 | 0 |
| customer_feedback | 3,756 | 3,756 | 0 |
| **Total** | **30,313** | **30,313** | **0** |

Unresolved tickets retaining null resolution: 1,188.
Normalization changes: 0.
Ready for analysis: True. Source CSVs unchanged: True.
Source checksum manifest matches: True. Source row counts match: True.

## File locations

- Source: `C:\Users\abhig\Desktop\Jobsyme Candidates\Aniketh\Customer-Support-Performance-and-SLA-Compliance-Analytics-System\data\sample\synthetic`
- Cleaned: `C:\Users\abhig\Desktop\Jobsyme Candidates\Aniketh\Customer-Support-Performance-and-SLA-Compliance-Analytics-System\data\processed\cleaned`
- Quarantine and normalization audit: `C:\Users\abhig\Desktop\Jobsyme Candidates\Aniketh\Customer-Support-Performance-and-SLA-Compliance-Analytics-System\data\processed\quarantine`

## Findings

No invalid records found. The generated source data already satisfies the cleaning rules.

## Interpretation

Every input record is counted as accepted or rejected. Rejection reasons may overlap. Exact duplicate extras are quarantined, not silently dropped. Conflicting keys reject all candidates. Null event timestamps are retained when permitted by ticket state. Bad history can quarantine its ticket and dependent rows; bad feedback alone does not remove a valid ticket.

Accepted rows pass the existing independent relational/lifecycle/SLA validator in memory and after CSV export when tickets remain. See the JSON report for per-rule counts and file checksums. Empty accepted ticket sets are marked not ready.
