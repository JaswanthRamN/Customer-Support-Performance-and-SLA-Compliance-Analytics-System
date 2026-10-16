# Cleaning Run: Commands and Results

Run date: October 16, 2026 (America/New_York).

Working directory: `C:\Users\abhig\Desktop\Jobsyme Candidates\Aniketh\Customer-Support-Performance-and-SLA-Compliance-Analytics-System`.

The project virtual environment was not used; execution used the bundled Python 3.12.14 interpreter with Pandas 3.0.1 and NumPy 2.3.5, matching the project's pinned dependencies. The exact data-processing and test commands executed in PowerShell were:

```powershell
& 'C:\Users\abhig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -p test_clean_data.py -v
& 'C:\Users\abhig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m scripts.clean_data
& 'C:\Users\abhig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
& 'C:\Users\abhig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m scripts.validate_synthetic_data
git diff --exit-code -- data/sample/synthetic
git diff --check
git status --short
```

The targeted cleaning test command was run twice during development: the first run exposed an empty-parent timestamp-lookup bug, which was corrected; the second run passed all 13 cleaning tests then present. Four more cleaning tests were subsequently added, and the complete suite passed all **27 tests** (17 cleaning tests and 10 existing synthetic-data tests), with exit code 0. Invalid-priority fixtures initially exposed a Pandas timedelta warning; invalid-priority handling was corrected before the successful runs.

The cleaner command ran twice, both successfully; the final run regenerated reports after adding explicit quarantine metadata-column names. Each run accepted **30,313 input records** and quarantined **0 records**. The final report preserves **1,188 unresolved tickets with null resolution timestamps** and records **0 normalization changes**. All six cleaned tables passed the independent validator both in memory and after export.

The source validator passed all eight integrity groups, including original source row counts and SHA-256 checksums. The source-only Git diff was empty; source CSVs and metadata were not modified. `git diff --check` passed; Git printed only informational LF/CRLF warnings for the edited Markdown documentation. `git status --short` showed the new cleaner, tests, quality reports, guide, and documentation changes; processed outputs remain ignored by the existing rules.

No generator command was run for the delivered source data during cleaning. Corrupt and generated fixtures used by tests were confined to temporary directories. No dependencies were installed and no commits or pushes were performed.
