# Data Dictionary

## Dataset grain, relationships, and conventions

All records are synthetic. The default snapshot is **2026-07-01 00:00:00 UTC**, covering tickets created from January through June 2026. Six CSVs live in `data/sample/synthetic/`. Empty CSV cells mean null. UTC timestamps use `YYYY-MM-DDTHH:MM:SSZ`; PostgreSQL should store them as `TIMESTAMPTZ`.

| CSV | One row represents | Primary key | Foreign keys |
| --- | --- | --- | --- |
| customers.csv | A fictional customer account | customer_id | None |
| teams.csv | A support team | team_id | None |
| agents.csv | A fictional agent with a fixed home team | agent_id | team_id → teams |
| tickets.csv | A ticket at the snapshot | ticket_id | customer_id → customers; current_agent_id → agents; current_team_id → teams |
| assignment_history.csv | An uninterrupted ownership interval | assignment_id | ticket_id → tickets; agent_id → agents; team_id → teams |
| customer_feedback.csv | An optional response after final resolution | feedback_id | ticket_id → tickets (unique); customer_id → customers |

Do not join tickets directly to assignment history and then count rows as tickets: that inflates ticket volume. Aggregate history to ticket grain first, or use distinct ticket IDs. Join tickets to feedback with a left join to preserve unrated tickets. There is no separate SLA-policy CSV; the fixed policy is stored in the generator, metadata, and ticket target columns.

## customers.csv

All fields are required. Labels are generated placeholders, not people or businesses.

| Field | PostgreSQL type | Meaning / allowed values |
| --- | --- | --- |
| customer_id | TEXT | Unique synthetic ID, CU00001 onward |
| customer_label | TEXT | Synthetic Customer plus a number |
| segment | TEXT | Individual, Small Business, Enterprise |
| region | TEXT | Fictional Region A, Region B, Region C, Region D |
| joined_at | TIMESTAMPTZ | Account creation; precedes every linked ticket |

## teams.csv

All fields are required.

| Field | PostgreSQL type | Meaning |
| --- | --- | --- |
| team_id | TEXT | TM01, TM02, TM03 |
| team_name | TEXT | Tier 1 Support, Technical Support, Billing Support |
| specialization | TEXT | Account and General, Technical, Billing, respectively |

## agents.csv

All fields are required. Team membership is fixed; agent team-transfer history is not modeled.

| Field | PostgreSQL type | Meaning / allowed values |
| --- | --- | --- |
| agent_id | TEXT | Unique ID, AG001 onward |
| agent_label | TEXT | Synthetic Agent plus a number |
| team_id | TEXT | Home team; every assignment uses this team |
| hired_at | TIMESTAMPTZ | Before the agent's assignments |
| experience_level | TEXT | Junior, Intermediate, Senior; descriptive only |

## tickets.csv

One row per ticket; priority is fixed at creation. Required unless explicitly nullable.

| Field | PostgreSQL type | Meaning / null rules |
| --- | --- | --- |
| ticket_id | TEXT | Unique ID, TK000001 onward |
| customer_id | TEXT | Customer opening the ticket |
| priority | TEXT | Critical, High, Medium, Low |
| category | TEXT | Account, Technical, Billing, General |
| channel | TEXT | Email, Chat, Phone, Web |
| status | TEXT | Open, In Progress, Pending, Resolved, Closed |
| created_at | TIMESTAMPTZ | Ticket creation; at or before snapshot |
| first_response_at | TIMESTAMPTZ, nullable | First human response, never an automated acknowledgement; null for Open tickets |
| initial_resolved_at | TIMESTAMPTZ, nullable | First resolution; may exist on a currently unresolved reopened ticket |
| reopened_at | TIMESTAMPTZ, nullable | Reopen event after initial resolution; at most one per ticket |
| reopen_count | SMALLINT | 0 or 1, consistent with reopened_at |
| resolved_at | TIMESTAMPTZ, nullable | Final resolution of current lifecycle; null for unresolved tickets, including reopened tickets still awaiting resolution |
| closed_at | TIMESTAMPTZ, nullable | Administrative closure after final resolution; exists only for Closed tickets |
| current_agent_id | TEXT | Agent in final ownership interval, including completed tickets |
| current_team_id | TEXT | Current agent's home team; join teams for team_name |
| response_target_hours | INTEGER | Priority-specific calendar-hour target: 1, 4, 8, 24 |
| resolution_target_hours | INTEGER | Priority-specific calendar-hour target: 8, 24, 48, 72 |
| response_deadline | TIMESTAMPTZ | created_at plus response_target_hours; may be after snapshot |
| resolution_deadline | TIMESTAMPTZ | created_at plus resolution_target_hours; may be after snapshot |
| response_sla_status | TEXT | Met, Breached, Pending, using first_response_at |
| resolution_sla_status | TEXT | Met, Breached, Pending, using final resolved_at |
| overall_sla_status | TEXT | Breached if either commitment breached; Met if both met; otherwise Pending |

Lifecycle: `created_at <= first_response_at <= initial_resolved_at < reopened_at < resolved_at <= closed_at`, applying only to events that exist. Without a reopen, initial_resolved_at equals resolved_at. Pending ticket status does not mean SLA Pending. Pending tickets have running clocks.

A reopened ticket keeps the original resolution deadline: no reset, pause, or subtraction of time spent resolved. This is an explicit portfolio assumption. For a reopened unresolved ticket, initial_resolved_at remains populated and resolved_at is blank. Duration metrics use final resolved_at and therefore exclude this ticket until it is resolved again.

## assignment_history.csv

All fields required except unassigned_at. Every ticket starts assigned at creation. Intervals use `[assigned_at, unassigned_at)` boundaries: the previous interval ends exactly when the next begins. Exactly one final interval per ticket has no end. Ownership remains recorded after resolution/closure; a null end does not imply the ticket is unresolved.

| Field | PostgreSQL type | Meaning |
| --- | --- | --- |
| assignment_id | TEXT | Unique ID, AS0000001 onward |
| ticket_id | TEXT | Owned ticket |
| agent_id | TEXT | Assigned agent |
| team_id | TEXT | Assigned agent's home team |
| assigned_at | TIMESTAMPTZ | Interval start, at or before snapshot |
| unassigned_at | TIMESTAMPTZ, nullable | Next assignment's start, or null for final ownership |
| assignment_reason | TEXT | Initial, Reassignment, Reopened |

Ordinary reassignments occur before initial resolution (or snapshot for never-resolved tickets). Each reopen creates a handoff at reopened_at. Every handoff changes agents and may change teams. There are no ownership gaps or overlaps. The current owner in tickets must match the final interval. This models ownership, not billable effort or active handle time.

## customer_feedback.csv

All fields required for a row. A missing row means no feedback, not a zero rating. At most one row per ticket, only for tickets currently Resolved or Closed; previous-cycle feedback is not modeled.

| Field | PostgreSQL type | Meaning |
| --- | --- | --- |
| feedback_id | TEXT | Unique ID, FB000001 onward |
| ticket_id | TEXT | Unique ticket receiving feedback |
| customer_id | TEXT | Must match that ticket's customer |
| submitted_at | TIMESTAMPTZ | Between final resolution and snapshot |
| csat_score | SMALLINT | Integer 1–5; 4 or 5 is positive |

## Metadata and derived metrics

`metadata.json` records the seed, fixed creation window, snapshot, Python/Pandas/NumPy versions, SLA policy, row counts, validation groups, and SHA-256 checksum of each CSV. `row_count_summary.md` records actual counts and overlapping scenario counts. Neither includes a variable generation timestamp, so reruns in the same environment produce identical files.

Derive `response_hours = (first_response_at - created_at)` in hours, `resolution_hours = (resolved_at - created_at)` in hours, and unresolved age from creation to snapshot. Join teams for the former `team` label and feedback for the former `csat_score` ticket field. See `kpi_definitions.md` for formulas and denominators.

## Validation contract

The generator validates before export; the standalone validator reopens the CSVs and validates again. It rejects schema drift, duplicate/null/blank keys, unknown categories, broken foreign keys, mismatched agent/team and feedback/customer pairs, future events, impossible lifecycle order, invalid reopen counts, ownership gaps/overlaps, missing current intervals, policy/deadline/SLA inconsistencies, and invalid feedback ratings/times. It also verifies row counts and CSV checksums against metadata.

The generator emits clean source data. It does not inject deliberate invalid records; corruption tests create temporary invalid copies to prove that validation detects defects. The Pandas cleaning stage (`scripts/clean_data.py`) preserves these source CSVs and exports accepted records with the same six schemas. See `data_cleaning.md` for normalization, duplicate handling, cascading rejections, and quarantine rules. Quarantine files add source-record and rejection-reason columns to the original source values; the quality report accounts for every parsed input row.
