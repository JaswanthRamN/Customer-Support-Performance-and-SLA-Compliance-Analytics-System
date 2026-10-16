# Customer Support Performance and SLA Compliance Analytics System

A beginner-friendly Business Analyst portfolio project that turns support ticket data into actionable insights about workload, service speed, SLA compliance, team performance, unresolved tickets, and customer satisfaction.

## Business problem

Support managers need to understand whether customers receive timely help, where tickets accumulate, and which teams need additional support. This project will connect business requirements to measurable KPIs and a Power BI dashboard.

## Business questions

- How many tickets arrive, and how does demand vary by date, channel, category, and priority?
- How quickly do teams provide a first response and resolve tickets?
- Which priorities and teams miss their SLA targets?
- How many tickets remain unresolved, and how old are they?
- How does team workload relate to service quality and customer satisfaction?

## Technology and planned workflow

| Tool | Purpose |
| --- | --- |
| Python | Load, validate, and prepare ticket data |
| Pandas | Clean data and calculate analysis tables |
| NumPy | Support numerical calculations and conditional flags |
| PostgreSQL | Store cleaned tickets and SLA policies |
| SQL | Calculate reusable KPI summaries and investigate trends |
| Power BI | Present interactive dashboards for business stakeholders |

Planned flow: synthetic ticket data → Python validation and cleaning → PostgreSQL tables → SQL analysis → Power BI dashboard → business recommendations.

## Project structure

```text
docs/
  business_requirements.md   # Business goals, scope, and acceptance criteria
  data_dictionary.md        # Source fields, types, and validation rules
  kpi_definitions.md        # Metric formulas, denominators, and SLA logic
data/
  raw/                      # Original local inputs; ignored by Git
  processed/                # Cleaned local outputs; ignored by Git
  sample/synthetic/         # Six generated CSVs, metadata, and row-count summary
notebooks/                  # Future exploratory analysis
scripts/                    # Seeded generator, validator, and Pandas cleaner
tests/                      # Data integrity, boundary, and reproducibility tests
sql/                        # Future PostgreSQL schema and analysis queries
powerbi/                    # Future Power BI report and supporting assets
reports/                    # Data-quality report; future findings and dashboard images
requirements.txt            # Python dependencies
.gitignore
README.md
```

The empty folders contain `.gitkeep` files so the structure can be tracked by Git.

## Current stage: synthetic data and quality checks

The business documentation, a validated 10,000-ticket synthetic dataset, and a Pandas cleaning pipeline are ready. Six related CSVs cover customers, teams, agents, tickets, assignment history, and optional customer feedback. The cleaner creates separate accepted and quarantine outputs and a data-quality report. No database schema, SQL analysis, or dashboard has been built yet. SLA thresholds are illustrative assumptions for a fictional support operation.

## Local Python setup

Install Python 3.11 or newer, then run the following from the repository folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

You can run Python scripts using `.\.venv\Scripts\python.exe` without activating the environment. PostgreSQL and Power BI Desktop will be needed in later stages; database credentials will stay in local environment variables or an ignored `.env` file.

## Generate and validate the dataset

Run from the repository root after the Python setup above:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_synthetic_data
.\.venv\Scripts\python.exe -m scripts.validate_synthetic_data
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Defaults: 10,000 tickets, seed 42, January–June 2026 creation window, snapshot `2026-07-01T00:00:00Z`. Generation replaces the six CSVs and two metadata/summary files in `data/sample/synthetic/`. It does not change other files in that directory. Use another output directory for experiments:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_synthetic_data --tickets 2000 --seed 7 --output data/raw/experiment
.\.venv\Scripts\python.exe -m scripts.validate_synthetic_data --input data/raw/experiment
```

Use the pinned dependencies and Python 3.12.14 to reproduce the delivered environment exactly. Metadata records runtime versions and CSV checksums. Reproducibility tests compare all six DataFrames and exported file bytes across matching runs. The default-dataset test expects the delivered 10,000-ticket seed-42 output; keep experiments in another directory.

The simulation includes weekdays and working-hour demand peaks, increasing monthly demand, channel-dependent response speed, category-dependent complexity, long-tail delays, overdue unresolved tickets, initial routing variation, reassignments, one optional reopen cycle, and optional satisfaction ratings. These patterns are invented assumptions, not statistically calibrated claims. See the [data-generation guide](docs/synthetic_data_guide.md) and [actual row-count summary](data/sample/synthetic/row_count_summary.md).

## Clean the source files

```powershell
.\.venv\Scripts\python.exe -m scripts.clean_data
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The generated CSVs in `data/sample/synthetic/` serve as immutable source inputs for this stage. The cleaner leaves them unchanged, writes six cleaned CSVs to `data/processed/cleaned/`, and writes six quarantine CSVs plus a normalization audit to `data/processed/quarantine/`. The existing ignore rules keep these processed outputs local. Reproduce them by running the command above.

Read [the data-quality report](reports/data_quality_report.md) for accepted/rejected counts and [the cleaning guide](docs/data_cleaning.md) for rules, failure handling, and custom paths. Legitimate missing resolution timestamps stay blank for unresolved tickets. No bad record is silently discarded: every parsed source row is counted as accepted or quarantined with its original values, source record number, and reasons.

## Suggested learning milestones

1. Review the requirements, data fields, and KPI rules. Explain what business decision each KPI supports.
2. Generate and inspect the synthetic dataset; explain its relationships and assumptions.
3. Run the cleaner, review the quality report and tests, then explore workload, delays, and missing feedback with Pandas.
4. Create PostgreSQL tables and load the cleaned data.
5. Write SQL queries and reconcile their results against Python calculations.
6. Build a Power BI dashboard with summary, SLA, team, backlog, and satisfaction views.
7. Write a short findings report with evidence, recommendations, and limitations.

## Portfolio and privacy guidance

Use synthetic records without names, email addresses, ticket text, or other personal information. Present this as an independent portfolio simulation. Explain assumptions clearly and avoid claiming real business improvements from fictional data. Review exported reports and Power BI files before sharing because they may contain embedded data.

## Documentation

- [Business requirements](docs/business_requirements.md)
- [Data dictionary](docs/data_dictionary.md)
- [KPI definitions](docs/kpi_definitions.md)
