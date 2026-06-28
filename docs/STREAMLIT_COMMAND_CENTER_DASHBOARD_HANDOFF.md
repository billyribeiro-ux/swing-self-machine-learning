# Streamlit Command Center Dashboard Handoff

Supersession note: Signal-First Trading Research Dashboard V1 reorganizes the
visible Streamlit navigation around signals and edge status. See
`docs/SIGNAL_FIRST_DASHBOARD.md` and
`docs/SIGNAL_FIRST_DASHBOARD_HANDOFF.md` for the current page list and workflow.

## Architecture

The dashboard is a local Streamlit presentation layer over the existing Python engine and application services. New read-only dashboard helpers live in `src/swing_rsi/application/dashboard_service.py`; export helpers live in `src/swing_rsi/application/dashboard_exports.py`.

Page renderers live in `dashboard/sections/`, and explicit page registration lives in `dashboard/ui/navigation.py`.
The launch entrypoint is `dashboard/app.py`; it calls `st.navigation(streamlit_pages(st), position="sidebar")`.

## Page List

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

The legacy primary labels `Discovery Lab`, `Live Scanner`, `Portfolio Backtests`,
and `Baselines and Legacy RSI` are not registered as visible Command Center
pages. If they appear in a sidebar, the running process is using the old
operational dashboard or a stale process, not the development Command Center V1
entrypoint.

## Safety Boundaries

- Runs from the development worktree: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`.
- Blocks startup from the operational worktree: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`.
- Requires confirmation when launched outside the configured development worktree.
- Uses read-only SQLite connections for page-load dashboard reads.
- Does not contact FMP on page load.
- Does not run scanner, final-holdout update, discovery, data update, retraining, or promotion on page load.
- Does not show or log the FMP API key.

## Operational Read-Only Behavior

The Overview page displays the frozen operational run only as read-only context:

- run ID `3493ee8ac37bf96475c362e1`
- enrolled model ID `b93b2258c10aea5cef81d291`
- baseline date `2026-06-25`
- status and event counts when available
- operational Git HEAD and status
- artifact integrity when available

The dashboard does not write operational SQLite, artifacts, reports, logs, data, or `.env`.

## Supported Actions

- Read-only local status refresh.
- Confirmed development FMP universe update.
- Confirmed development scanner run with optional challengers.
- Confirmed development final-holdout update.
- Confirmed development engine commands from the allowlist.
- Password-only FMP key save to the development `.env`.
- CSV and XLSX downloads.
- On-demand Excel workbook creation under `reports/dashboard_exports/`.

## Disabled Actions

- Model discovery from the dashboard.
- Model promotion from the dashboard.
- Brokerage execution.
- External deployment.
- Authentication or cloud infrastructure.

## Export Behavior

Every main table has CSV and XLSX downloads. XLSX files are generated with `openpyxl`, freeze the header row, enable filters, use readable widths, apply simple date/percentage/number formats, and redact API-key-like content.

Generated dashboard files are ignored:

- `reports/dashboard_exports/`
- `reports/dashboard_command_logs/`

## Command Behavior

Allowed commands:

- `build-features`
- `universe-update`
- `scan --include-challengers`
- `final-holdout-status`
- `final-holdout-update`
- `model-audit --generation latest`

Each command displays the exact command, requires confirmation, runs from the development worktree, captures stdout/stderr, redacts secret markers, and writes a command log.

## Tests

Added and updated tests cover explicit navigation, page-load smoke tests, no-FMP page loads, no page-load SQLite/artifact mutation, model registry reads, gate audit failures, product-class scopes, scanner snapshots, missing attribution handling, final-holdout progress display, empty ordinary paper-forward state, report inventory, disabled discovery/promotion commands, CSV/XLSX generation, openpyxl workbook validation, secret redaction, command confirmation/refusal, command output capture, Git-ignore coverage, operational separation, and FMP settings.

The navigation regression coverage now captures the actual `st.Page`
registrations made by `dashboard/app.py`; it is not limited to testing the
internal helper list.

## Verification Results

Completed in the development worktree:

- `.venv/bin/pytest`: 320 passed, 11776 warnings
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: 111 files already formatted
- `.venv/bin/mypy src`: success, no issues in 61 source files
- Streamlit AppTest real-state smoke for all 12 Command Center pages: passed
- Local Streamlit HTTP smoke at `http://localhost:8502`: `HTTP/1.1 200 OK`

Warnings were existing pandas/joblib/performance warnings from autonomous-engine tests, not dashboard failures.

## Commit Hashes

Exact local commit hashes are reported in the Codex completion handoff. The handoff file itself cannot contain its own final commit hash without changing that hash.

## Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

## Known Limitations

- The dashboard remains local Streamlit infrastructure.
- Product-class comparison values depend on the available local model/report evidence.
- Final-holdout pages show prospective sample progress; current development runs are not final validation.
- FMP update buttons require a locally configured key and explicit confirmation.
- Dashboard V1 does not promote or discover models.

## Next Smallest Task

Add richer artifact drilldowns for selected model bundles without loading every model artifact on dashboard startup.
