# Streamlit Command Center Dashboard

## Purpose

The Streamlit Command Center is the local development console for the Self-Learning Swing Trading Engine. It is a research and operations dashboard for inspecting development-engine state, not a trading application.

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
`Baselines and Legacy RSI`, the running process is not the Command Center V1
entrypoint from this development worktree. That old 9-page navigation still
exists in the frozen operational repository for historical context and must not
be used for development Command Center checks.

## Pages

The dashboard uses explicit `st.navigation` page registration in this order:

1. Overview
2. Data and Universe
3. Model Registry
4. Gate Audit
5. Product-Class Specialists
6. Scanner Snapshots
7. Candidate Attribution
8. Shadow Final Holdout
9. Paper Forward Test
10. Reports and Exports
11. Engine Commands
12. Legacy Baselines

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
- `configs/universe/core.yaml`
- model audit exports where available

FMP is not contacted on page load. If no key is configured, the dashboard shows `FMP key configured: no` and disables FMP update commands.

## Exports

Reusable helpers live in `src/swing_rsi/application/dashboard_exports.py`:

- `to_csv_bytes(...)`
- `to_xlsx_bytes(...)`
- `save_xlsx_report(...)`

XLSX exports use `openpyxl`, freeze the header row, enable filters, apply readable widths, and redact API-key-like content. Generated dashboard workbooks are saved under:

```text
reports/dashboard_exports/
```

Dashboard command logs are saved under:

```text
reports/dashboard_command_logs/
```

Both directories are ignored by Git.

## Supported Commands

The Engine Commands page can run only these confirmed development commands:

- `build-features`
- `universe-update`
- `scan --include-challengers`
- `final-holdout-status`
- `final-holdout-update`
- `model-audit --generation latest`

Each command displays the exact command before execution, requires confirmation, captures output, logs to `reports/dashboard_command_logs/`, and refuses to run from the operational repository.

## Disabled Commands

Dashboard V1 does not run:

- `discover-models`
- `promote-model`

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
