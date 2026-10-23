# Cleaning Run: Commands and Results

Run date: October 23, 2026 (America/New_York).

Working directory: `C:\Users\abhig\Desktop\Jobsyme Candidates\Aniketh\Customer-Support-Performance-and-SLA-Compliance-Analytics-System`.

The project virtual environment used Python 3.12.14 with Pandas 3.0.1 and NumPy 2.3.5, matching the project's pinned dependencies. The exact data-processing commands executed in PowerShell were:

```powershell
& '.\.venv\Scripts\python.exe' -m scripts.generate_synthetic_data
& '.\.venv\Scripts\python.exe' -m scripts.validate_synthetic_data
& '.\.venv\Scripts\python.exe' -m scripts.clean_data
& '.\.venv\Scripts\python.exe' -m scripts.eda
& '.\.venv\Scripts\python.exe' -m scripts.load_postgres --check-only
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

The latest cleaner run completed successfully after applying the illustrative minute-based SLA policy. It accepted **30,326 input records** and quarantined **0 records**. The final report preserves **1,136 unresolved tickets with null resolution timestamps** and records **0 normalization changes**. All six cleaned tables passed the independent validator both in memory and after export.

The generator rebuilt the delivered synthetic source because the policy changed. The source validator passed all eight integrity groups, including row counts and SHA-256 checksums. The cleaner, EDA, and PostgreSQL preflight outputs were regenerated from that source. Corrupt fixtures used by tests remained confined to temporary directories. No dependencies were installed, and no push was performed.
