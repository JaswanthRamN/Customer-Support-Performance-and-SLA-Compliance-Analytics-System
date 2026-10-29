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
config/
  sla_policy.json           # Illustrative priority targets in exact minutes
docs/
  business_requirements.md   # Business goals, scope, and acceptance criteria
  data_dictionary.md        # Source fields, types, and validation rules
  kpi_definitions.md        # Metric formulas, denominators, and SLA logic
data/
  raw/                      # Original local inputs; ignored by Git
  processed/                # Cleaned local outputs; ignored by Git
  sample/synthetic/         # Six generated CSVs, metadata, and row-count summary
notebooks/                  # Future exploratory analysis
scripts/                    # SLA calculations, generator, validator, cleaner, loader, and EDA
tests/                      # Data integrity, boundary, and reproducibility tests
sql/                        # PostgreSQL schema, validation, and analysis queries
powerbi/                    # Power Query and DAX model source assets; no PBIX yet
reports/eda/                # EDA report, KPI summary, tables, and charts
requirements.txt            # Python dependencies
.gitignore
README.md
```

The empty folders contain `.gitkeep` files so the structure can be tracked by Git.

## Current stage: PostgreSQL reporting layer

The business documentation, validated 10,000-ticket synthetic dataset, Pandas cleaning pipeline, EDA, PostgreSQL schema, loader, analysis queries, reporting views, and Python reconciliation baseline are ready. The loader has passed local CSV preflight and automated tests. A live database import and SQL-to-Python comparison await a configured PostgreSQL instance. No Power BI dashboard has been built yet. SLA targets are illustrative elapsed-calendar-time assumptions for this fictional support operation, not universal standards.

## Local Python setup

Install Python 3.11 or newer, then run the following from the repository folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

You can run Python scripts using `.\.venv\Scripts\python.exe` without activating the environment. PostgreSQL is needed for the database load and Power BI Desktop for the dashboard stage. Database credentials belong in process environment variables, never in Git.

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

## Run the exploratory analysis

After installing `requirements.txt` and running the cleaner, use:

```powershell
.\.venv\Scripts\python.exe -m scripts.eda
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The script validates the cleaned six-table dataset and its accepted row counts before analysis. It writes the [EDA report](reports/eda/eda_report.md), [KPI summary](reports/eda/kpi_summary.json), reusable summary CSVs, and [seven charts](reports/eda/charts/). The fixed snapshot comes from the data-quality report. Charts and report label the results as synthetic-data observations. Output paths can be changed with `--input`, `--quality-report`, and `--output`.

The report explains volume, service speed, SLA, backlog, reassignment, reopening, and ratings. Averages and medians use only tickets with the relevant event. Missing feedback is excluded from score calculations, while coverage uses all resolved tickets as the denominator. See [KPI definitions](docs/kpi_definitions.md) for the complete rules.

Reusable [SQL reporting views](docs/reporting_views.md) provide SLA, service-time, backlog, reassignment, reopening, satisfaction, overdue-ticket, and assignment-history datasets. Summary views derive from one row per ticket and label team/agent as current snapshot ownership. An independent Pandas reconciliation command provides expected values and can compare them with a configured PostgreSQL database.

The [Power BI model guide](docs/power_bi_model.md) includes PostgreSQL Power Query M transformations, role-playing team/agent/date dimensions, safe relationships, DAX KPI measures, null and UTC handling, and a Desktop validation checklist. These are source assets and instructions; the repository does not currently contain a PBIX file.

The [executive dashboard build guide](docs/executive_power_bi_dashboard.md) maps KPI cards, trends, distributions, team comparison, and slicers to the model, with manual Power BI Desktop steps and SQL reconciliation targets.

## Load PostgreSQL and run SQL analysis

See the [PostgreSQL guide](docs/postgres.md) for table relationships, connection variables, dependency order, validation, reload behavior, and the six analysis queries. With cleaned CSVs available, local preflight runs without a server:

```powershell
.\.venv\Scripts\python.exe -m scripts.load_postgres --check-only
```

After configuring PostgreSQL through environment variables, run `.\.venv\Scripts\python.exe -m scripts.load_postgres`. The loader checks all six source files before connecting, copies them in dependency order inside one transaction, and verifies database counts and relationships before commit. It refuses to replace populated tables unless `--replace` is explicit.

## Suggested learning milestones

1. Review the requirements, data fields, and KPI rules. Explain what business decision each KPI supports.
2. Generate and inspect the synthetic dataset; explain its relationships and assumptions.
3. Run the cleaner and EDA, then explain which findings reflect the generator's assumptions and which metrics could mislead without their denominators.
4. Run the PostgreSQL load against a local instance and inspect its count/relationship report.
5. Run the SQL queries and reconcile their results against Python calculations.
6. Build a Power BI dashboard with summary, SLA, team, backlog, and satisfaction views.
7. Write a short findings report with evidence, recommendations, and limitations.

## Portfolio and privacy guidance

Use synthetic records without names, email addresses, ticket text, or other personal information. Present this as an independent portfolio simulation. Explain assumptions clearly and avoid claiming real business improvements from fictional data. Review exported reports and Power BI files before sharing because they may contain embedded data.

## Documentation

- [Business requirements](docs/business_requirements.md)
- [Data dictionary](docs/data_dictionary.md)
- [KPI definitions](docs/kpi_definitions.md)
- [PostgreSQL schema, load, and queries](docs/postgres.md)
- [SQL reporting views and Python reconciliation](docs/reporting_views.md)
- [Power BI model and Power Query guide](docs/power_bi_model.md)
- [Executive Power BI dashboard build guide](docs/executive_power_bi_dashboard.md)
