# Synthetic Data Generation Guide

## Purpose

Practice relational modeling, data validation, and business analysis with fictional support operations. No external data, real identities, emails, phone numbers, addresses, or ticket free text are used. Customer and agent labels are numbered placeholders. The synthetic sample folder is intentionally eligible for Git tracking; raw experiments remain ignored.

## Reproduce the delivered dataset

From the repository root, install `requirements.txt` into a Python environment and run:

```powershell
python -m scripts.generate_synthetic_data
python -m scripts.validate_synthetic_data
python -m unittest discover -s tests -v
```

Use the environment's interpreter if `python` is not on PATH. The delivered files were generated with Python 3.12.14, Pandas 3.0.1, and NumPy 2.3.5. Both dependency versions are pinned. Default seed is 42; the generator uses a local `numpy.random.default_rng` and never uses the current clock. Creation dates span January 1 through June 30, 2026, with a fixed July 1 UTC snapshot. Newer dependency versions or code changes can change seeded output; compare metadata and checksums when reproducing a run.

The generator prints row counts, validates the in-memory dataset, and writes six CSVs plus `metadata.json` and `row_count_summary.md`. The standalone validator reloads persisted files and checks their integrity and checksums. Failed validation raises an error and exits with a nonzero status. Output paths are relative to the current directory when supplied; the default is anchored to the repository.

CSVs use UTF-8 and LF line endings. `.gitattributes` preserves LF on Git checkout so Windows newline conversion does not invalidate the saved checksums.

## Simulation assumptions

- Create 2,500 fictional customer accounts for 10,000 tickets (one account per four requested tickets, minimum one), three teams, and 30 agents. Some customers may have no tickets.
- Customers joined and agents were hired before the ticket creation window. IDs are deterministic and prefixed by entity.
- Ticket arrivals favor weekdays and 08:00–18:59 UTC. Monthly arrival weights increase by 8% of the January baseline per month. This is a single UTC demand profile, not local-time scheduling by region.
- Priority probabilities are 6% Critical, 22% High, 47% Medium, and 25% Low. Categories and channels have separate weighted draws.
- Response delays are lognormal, adjusted by channel and customer segment. Resolution delays are lognormal, adjusted by category complexity and bounded below by first response. Means are intentionally not uniform across cohorts.
- Small persistent unanswered and unresolved queues generate both recent and aging backlog. Future events are absent at the fixed snapshot, rather than shifted into the past.
- Initial routing generally follows category but sometimes varies. Ordinary handoffs change agents and can cross teams. Reopens create an additional handoff. Ownership intervals are contiguous and persist after resolution; they do not measure active effort.
- Roughly 11% of initially resolved tickets are considered for reopening; the event must fit before the snapshot. At most one reopen cycle is modeled. Some reopened tickets remain unresolved.
- The illustrative SLA policy uses elapsed calendar time: Critical 15 minutes/4 hours, High 1/8 hours, Medium 4/24 hours, and Low 8/72 hours (response/resolution). Targets are fixed at creation and stored as integer minutes in `config/sla_policy.json`. They are project assumptions, not universal standards. Events at a deadline meet SLA; absent events at a deadline remain Pending and breach only after it. Reopening does not reset deadlines.
- About 43% of finally resolved tickets are considered for feedback, which must also arrive before the snapshot. Scores tend to be lower for breached or reopened tickets. This simulated relationship is built into the data, so it is not evidence of causation.
- Status Closed requires a closure event after final resolution. Resolved means final resolution exists but closure has not yet occurred. Open means no first human response; other unresolved tickets are In Progress or Pending.

Probabilities are generation parameters, not guaranteed exact output proportions. Snapshot censoring and lifecycle dependencies affect the final distributions. See the generated summary for actual scenario counts.

## Tests and integrity checks

Tests cover repeatable DataFrames, identical exported bytes, alternate-seed variation, a one-ticket run with no feedback, invalid ticket counts, CSV round trips, the delivered 10,000-ticket dataset, SLA deadline boundaries, all five statuses, all three SLA outcomes, unresolved reopens, transfers, and optional feedback.

Negative tests deliberately corrupt temporary copies with duplicate keys, missing references, future timestamps, unknown statuses, bad SLA targets/flags, invalid reopen counts, wrong assignment teams, ownership gaps, invalid feedback ratings/times/customers, unexpected columns, and changed file checksums. No invalid records are added to the deliverables.

## Suggested next analysis exercise

Load each CSV with Pandas. Check ticket counts by creation month, priority, and team. Derive first response and final resolution hours. Left join optional feedback and compare CSAT coverage by priority. Summarize reassignment counts to one row per ticket before joining tickets. Explain why completed-ticket averages alone can hide aging unresolved work.

PostgreSQL schemas, SQL KPI queries, and the Power BI dashboard remain later stages.
