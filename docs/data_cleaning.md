# Pandas Data Cleaning

## Purpose and file locations

The generated files in `data/sample/synthetic/` are the original source for this stage. They are already valid; cleaning is not expected to invent errors or remove valid records. Use `scripts/clean_data.py` to normalize supported representations and quarantine genuine problems before analysis.

| Artifact | Default location |
| --- | --- |
| Six untouched source CSVs and snapshot metadata | data/sample/synthetic/ |
| Six cleaned CSVs with their original schemas | data/processed/cleaned/ |
| Six quarantine CSVs, including header-only files when no rows are rejected | data/processed/quarantine/ |
| Cell-level normalization audit | data/processed/quarantine/normalization_audit.csv |
| Human-readable quality report | reports/data_quality_report.md |
| Detailed counts, issues, snapshot, and source/output checksums | reports/data_quality_report.json |

Processed data stays local under the existing `.gitignore` rules. The cleaner replaces its named output files on rerun; archive earlier outputs in a different directory when comparing runs. Source files are protected by path checks and checked for unchanged SHA-256 hashes after cleaning. Input, cleaned, quarantine, and report directories must be separate, with no overlapping directory trees.

## Run the cleaner

From the repository root with the project environment:

```powershell
.\.venv\Scripts\python.exe -m scripts.clean_data
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Custom input must contain the six CSVs and a `metadata.json` with an explicit-timezone `analysis_as_of` value:

```powershell
.\.venv\Scripts\python.exe -m scripts.clean_data --input data/raw/experiment --output data/processed/experiment_cleaned --quarantine data/processed/experiment_quarantine --report reports/experiment/data_quality_report.json
```

The report argument ends in `.json`; a companion `.md` file is written automatically. Source manifest/checksum and row-count mismatches are reported rather than used to suppress cleaning, because correcting an imperfect copy may be intentional. The cleaner never changes the source manifest.

## Validation and normalization rules

1. **Read and schema:** read every value as text to preserve IDs and original values. Only empty/whitespace-only cells mean missing; the literal `NA` is not silently converted to null. Required columns must exist. Unexpected or duplicate column names are table-level schema errors: quarantine every row of that table and report the schema issue. Column ordering may differ; accepted exports use the documented order.
2. **Safe normalization:** trim surrounding whitespace; match known category spellings without regard to case; parse supported UTC or explicit-offset ISO timestamps and convert them to UTC; accept whole-number numeric representations such as `4.0` as integer 4. Every changed nonblank representation is recorded with table, source record, field, original value, cleaned value, and rule. The audit covers both subsequently accepted and rejected records.
3. **Types and domains:** IDs remain strings and must have the documented entity prefix followed by digits. Required values cannot be blank. Reopen count, SLA targets, and CSAT must be finite whole numbers within the integer range. Unknown categories are rejected, not guessed. CSAT must be an integer from 1 through 5; an optional survey is represented by no feedback row, not an invalid or empty rating in a feedback row.
4. **Duplicates:** compare normalized rows. For identical duplicates, keep the first candidate subject to all other checks; quarantine every extra copy as `exact_duplicate_extra`. For conflicting records sharing a primary key, quarantine all candidates, including identical copies within the conflict group. Do not select an arbitrary winner. Multiple otherwise valid feedback records for one ticket are ambiguous and are all rejected.
5. **Timestamps:** accept second-precision `YYYY-MM-DDTHH:MM:SSZ` or an explicit `+HH:MM`/`-HH:MM` offset. Reject unparseable, impossible, timezone-free, and future event timestamps. Future SLA deadlines are legitimate. Never turn an invalid supplied event into a legitimate missing event: parse failures carry rejection reasons.
6. **Ticket lifecycle:** verify status, first response, initial resolution, reopen, final resolution, closure, and snapshot ordering. Preserve null final resolution for Open, In Progress, and Pending tickets, including unresolved reopens. Require final resolution for Resolved and Closed tickets. There is no imputation of duration, resolution date, or satisfaction.
7. **SLA:** check integer-minute target values against the illustrative priority policy in `config/sla_policy.json`, deadlines against original creation, and response/resolution/overall flags against the events and snapshot. Inconsistent SLA fields are quarantined rather than silently recomputed. Reopening does not reset deadlines. These calendar-time targets are project assumptions, not universal standards.
8. **References and chronology:** check customer, team, agent, ticket, assignment, and feedback foreign keys against accepted parents; check customer join dates, agent hire dates, agent/team pairs, and feedback customer ownership/time. Bad feedback rejects the feedback row and preserves a valid ticket.
9. **Ownership intervals:** require complete ticket history from creation through its current owner, contiguous intervals, one initial assignment, agent changes at handoffs, final owner consistency, and reopen handoffs. An invalid history group quarantines the ticket; its remaining assignments and feedback then lose their accepted parent. This conservative policy avoids inventing missing history.
10. **Cascades:** repeat reference and history checks until no additional records are rejected. For example, a bad team can reject its agents, affected tickets, and dependent history/feedback. Each row receives all detected reasons; counts by reason can overlap.

## Quarantine and row accounting

Quarantine files preserve the original values, not the normalized values. `dq_source_record` is the logical CSV record number counting the header as record 1, not a Pandas index. `dq_rejection_reasons` contains semicolon-separated rule codes. If an unexpected original column already uses either name, the metadata name gains leading underscores; the JSON report records the resulting names without overwriting original data. Records with quoted embedded newlines may occupy multiple physical lines; their logical record number remains stable.

For each table, **input = accepted + rejected**, counting duplicate copies as input records. The report includes all three counts, schema issues, per-reason counts, normalization counts, preserved unresolved nulls, and source/output hashes. A rejected row is never written to its cleaned table. Empty quarantine files are retained with headers so a zero count is explicit.

The accepted data passes the existing independent lifecycle, reference, and SLA validator both in memory and after export. If no tickets survive, the report is marked not ready and the CLI exits with code 2 after saving outputs and diagnostics. Other runs may be ready with documented rejections, because the surviving relational dataset is internally consistent. There is no automatic acceptance threshold for a rejection rate.

Missing files/metadata, malformed CSV records with the wrong field count, invalid snapshot metadata, and unreadable CSV syntax are file-level failures: the command raises an error without publishing a new report/output set. Fix the file or use a fresh output directory and rerun. An unexpected failure can leave files from an earlier run in place; only use outputs from a successfully completed command with a matching report/checksum. Unexpected failures during file writing are not transactionally rolled back.

## Tests

Cleaning tests cover the delivered 10,000-ticket dataset, legitimate unresolved nulls, formatting audits, exact and conflicting duplicates, invalid types/categories/dates/ratings, missing columns, broken references, rejected-parent cascades, invalid ownership history, feedback isolation, source preservation, output reports, and protection against source overwrite. Corrupt fixtures exist only in temporary test copies. Existing generator and validation tests remain part of the complete suite.

See `reports/cleaning_run_commands.md` for the actual commands and results from the delivered run.
