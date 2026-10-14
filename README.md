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
  sample/                   # Future small, synthetic portfolio dataset
notebooks/                  # Future exploratory analysis
scripts/                    # Future Python preparation scripts
sql/                        # Future PostgreSQL schema and analysis queries
powerbi/                    # Future Power BI report and supporting assets
reports/                    # Future findings and exported dashboard images
requirements.txt            # Python dependencies
.gitignore
README.md
```

The empty folders contain `.gitkeep` files so the structure can be tracked by Git.

## Current stage: foundation only

The project structure and business documentation are ready. No dataset, pipeline, database schema, SQL analysis, or dashboard has been built yet. SLA thresholds in the documentation are illustrative assumptions for a fictional support operation.

## Local Python setup

Install Python 3.11 or newer, then run the following from the repository folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

You can run Python scripts using `.\.venv\Scripts\python.exe` without activating the environment. PostgreSQL and Power BI Desktop will be needed in later stages; database credentials will stay in local environment variables or an ignored `.env` file.

## Suggested learning milestones

1. Review the requirements, data fields, and KPI rules. Explain what business decision each KPI supports.
2. Create a small synthetic dataset containing normal tickets and deliberate edge cases.
3. Validate and clean the data with Python, Pandas, and NumPy; document quality issues.
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
