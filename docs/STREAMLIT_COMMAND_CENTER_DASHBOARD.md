# Streamlit Command Center Dashboard

## Purpose

The Streamlit Command Center is now organized as the Signal-First Trading Research Dashboard V1 for the Self-Learning Swing Trading Engine. It is a research and operations dashboard for inspecting development-engine state, not a trading application.

The dashboard title is:

```text
Self-Learning Swing Trading Engine
```

The dashboard subtitle is:

```text
Autonomous Discovery, Scanner, Attribution, and Shadow Forward Testing
```

Every page displays:

```text
Experimental research system. Results are not financial advice and are not evidence of a live trading edge.
Development dashboard. Operational frozen run remains separate.
```

## Launch

Run from the development worktree only:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

If the sidebar shows `Discovery Lab`, `Live Scanner`, `Portfolio Backtests`, or
`Baselines and Legacy RSI`, the running process is not the Signal-First
development entrypoint from this worktree. Those old labels remain only in
legacy modules or historical operational context.

## Pages

The dashboard uses explicit `st.navigation` page registration in this order:

1. Signal Board
2. Shadow Forward Test
3. Model Edge Status
4. Scanner Results
5. Candidate Detail
6. Product-Class Research
7. Gate Audit
8. Data and Universe
9. Reports and Exports
10. Engine Commands
11. Legacy Baselines
12. Developer Diagnostics

Streamlit filename-derived pages are not used.
There is no tracked `dashboard/pages/` source directory in the Command Center
development worktree.

## Safety Boundaries

- The dashboard is for `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`.
- The operational repository `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner` is read-only dashboard context.
- Startup is blocked from the operational repository.
- A non-development current directory requires explicit confirmation before continuing.
- Page loads must not update FMP, run discovery, run scanner, run final-holdout update, retrain models, promote models, mutate SQLite, or modify artifacts.
- Mutating actions require explicit button clicks and confirmation checkboxes.
- The dashboard does not display or log `.env` contents or the FMP key.
- The FMP settings control uses a password input and writes only to the development `.env` after confirmation.

## Data Sources

The dashboard reads local development state:

- `state/engine.sqlite3`
- `artifacts/`
- `reports/`
- `data/raw/`
- `data/features/`
- `data/manifests/`
- `data/cache/regime/`
- `configs/universe/core.yaml`
- model audit exports where available

FMP is not contacted on page load. If no key is configured, the dashboard shows `FMP key configured: no` and disables FMP update commands.

## Regime Cache Diagnostics

Signal Board includes compact Regime KMeans Cache cards:

- regime cache status;
- last cached date;
- KMeans fits avoided;
- regime runtime;
- cache validity reason.

Developer Diagnostics includes a full `Regime KMeans Cache` section with summary
metadata, raw cache metadata, input columns, and KMeans configuration. The panel
reads only local metadata under `data/cache/regime/`; it does not run
`build-features`, recompute regime features, contact FMP, mutate SQLite, or
modify model artifacts on page load.

The diagnostics explain that the regime cache preserves exact current feature
semantics and only avoids recomputing historical expanding KMeans labels when
inputs and configuration are unchanged.

## Exports

Reusable helpers live in `src/swing_rsi/application/dashboard_exports.py`:

- `normalize_table_for_export(...)`
- `to_csv_bytes(...)`
- `to_xlsx_bytes(...)`
- `save_xlsx_report(...)`

All dashboard tables pass through `normalize_table_for_export(...)` before CSV
or XLSX serialization. The helper preserves genuinely numeric and date columns,
but converts mixed display columns such as `Value`, `Actual`, `Threshold`,
`Reason`, and `Status` to safe strings so Streamlit/Arrow, CSV, XLSX, and
Parquet diagnostics do not fail on mixed Python object values. Missing display
values remain `Not available`, and infinities remain distinguishable as `∞` and
`-∞`.

XLSX exports use `openpyxl`, freeze the header row, enable filters, apply readable widths, and redact API-key-like content. Generated dashboard workbooks are saved under:

```text
reports/dashboard_exports/
```

Dashboard command logs are saved under:

```text
reports/dashboard_command_logs/
```

Both directories are ignored by Git.

Developer Diagnostics also provides Regime KMeans Cache downloads. The XLSX
workbook contains `summary`, `metadata`, `input_columns`, and `kmeans_config`
sheets.

## Signal and Edge Status

The first screen answers whether any rows are live actionable, shadow-only,
rejected, pending, open, closed, or research-only.

If no promoted model exists, the dashboard displays:

```text
No promoted live scanner model exists yet.
Current signals are research/shadow validation only.
```

Every model and signal is classified using:

- `RESEARCH ONLY`
- `DEVELOPMENT CANDIDATE`
- `SHADOW VALIDATION`
- `FINAL-HOLDOUT QUALIFIED`
- `PROMOTED`

The dashboard does not call a row live unless the model is promoted and all
gates allow it.

## Supported Commands

The Engine Commands page can run only these confirmed development commands:

- `build-features`
- `universe-update`
- `scanner review run` (`scan --include-challengers`)
- `final-holdout-status`
- `final-holdout-update`
- `model-audit --generation latest`

Each command displays the exact command before execution, requires confirmation, captures output, logs to `reports/dashboard_command_logs/`, and refuses to run from the operational repository.

## Disabled Commands

Dashboard V1 does not run:

- `discover-models`
- `promote-model`
- `final-holdout-init`
- `forward-update`

Promotion remains outside the dashboard.

## Operational Frozen Run

The operational repository is displayed read-only with:

- run ID `3493ee8ac37bf96475c362e1`
- enrolled model ID `b93b2258c10aea5cef81d291`
- baseline date `2026-06-25`
- operational Git HEAD/status
- event counts when readable
- artifact integrity when readable

No operational `.env`, SQLite, artifacts, reports, logs, or data are written.
