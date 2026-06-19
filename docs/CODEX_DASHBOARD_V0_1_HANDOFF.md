# Codex Dashboard V0.1 Handoff Report

Generated: 2026-06-19T23:20:35Z

Scope: complete verification and handoff for Milestone: Local Research Dashboard V0.1.

Security note: this report does not include the FMP API key, `.env` contents, secrets, credentials, or authenticated request URLs. `.env` was not opened or printed.

## Dashboard V0.1 Hardening Addendum — 2026-06-19

This addendum records the focused hardening patch performed after the original handoff report. It supersedes any older references in this file that describe `dashboard/pages/overview.py` as an active Streamlit page or describe the smoke test as page-load-only.

### Duplicate Overview Finding

Finding: Overview was registered twice in Streamlit navigation. `dashboard/app.py` rendered `dashboard.pages.overview.render_page`, and `dashboard/pages/overview.py` also existed under Streamlit's multipage `pages/` directory. That made the app entrypoint and a separate page file both expose Overview.

Fix:

- Moved the shared Overview renderer to `dashboard/sections/overview.py`.
- Updated `dashboard/app.py` to import `dashboard.sections.overview.render_page`.
- Removed `dashboard/pages/overview.py` so Streamlit sees the entrypoint plus four page files.
- Added `dashboard/ui/navigation.py` with the canonical five user-facing section definitions.
- Added `test_dashboard_registers_exactly_five_user_facing_sections`.

Current user-facing sections are exactly:

1. Overview
2. Data and Audit
3. RSI Explorer
4. Research and Backtest
5. Walk-Forward Validation

### Safe FMP Download/Update Semantics

Previous behavior: `download_daily_to_raw` downloaded the requested range and wrote it directly to `data/raw/{TICKER}.csv`. A narrow requested range could overwrite and truncate a broader existing ticker history.

New behavior in `src/swing_rsi/application/datasets.py`:

- Load existing ticker CSV when present.
- Download the requested FMP range through the existing provider abstraction.
- Validate the downloaded OHLCV data before merge.
- Merge by `Date`.
- Prefer newly downloaded values for duplicate dates.
- Preserve existing dates outside the requested range.
- Sort chronologically.
- Validate the merged OHLCV data.
- Save atomically through `atomic_write_csv`.
- Return downloaded, existing, replaced, inserted, and final row counts.

Failed validation occurs before the atomic replace, so the original CSV remains intact. No destructive replacement action was added.

New tests prove:

- A short update does not remove a long existing history.
- Overlapping dates are updated once.
- Duplicate dates do not remain.
- Failed validation does not damage the original CSV.
- Updating one ticker does not mutate unrelated ticker files.

### Walk-Forward Boundary Protection

Audit result: no new purge implementation was required for current Version 1 behavior. `run_walk_forward` slices the training frame before running `run_grid_search`, and `backtest_fixed_horizon` skips any signal whose next-open entry or fixed-horizon exit would be outside the supplied frame. Therefore an incomplete training trade near a fold boundary cannot use test-window prices.

Hardening added:

- `test_future_test_window_price_changes_do_not_change_prior_training_selection` mutates prices only inside a future test window and verifies earlier training-selected parameters and training metrics remain unchanged.
- `test_training_slice_skips_trades_that_would_exit_in_test_window` proves a signal near the end of a training slice is ignored when its exit would require test-period prices.
- `dashboard/pages/walk_forward.py` now explains that the gap is unused sessions between train/test windows and that incomplete training-slice trades are skipped.

### Manual/Form Smoke Coverage

The hardening pass added Streamlit `AppTest` interaction smoke tests using temporary local synthetic DEMO data and no FMP calls:

- RSI Explorer controls are changed and the optional RSI(14)/30 control is toggled.
- Quick Research form is submitted.
- A candidate row is selected after research completes.
- Walk-Forward form is submitted.

These tests assert that each interaction completes without Streamlit page exceptions.

### Hardening Verification Results

Commands run after the hardening patch:

```text
.venv/bin/pytest
```

Result: 38 collected, 38 passed.

```text
.venv/bin/ruff check .
```

Result: all checks passed.

```text
.venv/bin/ruff format --check .
```

Result: 61 files already formatted.

```text
.venv/bin/mypy src
```

Result: success, no issues found in 35 source files.

```text
./scripts/run_dashboard.sh
curl -I http://localhost:8502
```

Result: Streamlit server started on `localhost:8502`; HTTP smoke returned `200 OK`; process was stopped cleanly. Streamlit printed only the optional Watchdog performance suggestion.

### Files Added By Hardening

```text
dashboard/sections/__init__.py
dashboard/sections/overview.py
dashboard/ui/navigation.py
tests/test_dashboard_interactions.py
```

### Files Modified By Hardening

```text
dashboard/app.py
dashboard/pages/data_audit.py
dashboard/pages/walk_forward.py
dashboard/ui/components.py
docs/CHANGELOG.md
docs/CODEX_DASHBOARD_V0_1_HANDOFF.md
docs/DECISIONS.md
src/swing_rsi/application/datasets.py
src/swing_rsi/cli.py
tests/test_application_services.py
tests/test_dashboard_imports.py
tests/test_walk_forward.py
```

### File Removed By Hardening

```text
dashboard/pages/overview.py
```

### Security Note For Hardening

No `.env` contents, FMP API key, secrets, credentials, or authenticated request URLs were printed or included. Automated dashboard interaction tests patched the downloader to fail if an FMP download was attempted.

## 1. Repository State

- Absolute repository path requested by the task: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- `pwd` verification output: `/Users/billyribeiro/trading-projects/swing-rsi-self-learner`
- Current Git branch: `feat/local-research-dashboard`
- Current commit hash: `353b583429db0a8b5fda3849b555390b4b37fc75`
- Branch existence check: `git branch --list feat/local-research-dashboard` returned `* feat/local-research-dashboard`
- Working tree: dirty
- Anything committed: no. Current branch still points at commit `353b583`.
- Anything pushed remotely: no. `git remote -v` returned no remotes, and `git branch -vv` shows no upstream.

### Modified tracked files

```text
.gitignore
README.md
START_HERE.md
docs/ARCHITECTURE.md
docs/CHANGELOG.md
docs/DECISIONS.md
pyproject.toml
scripts/bootstrap_mac.sh
src/swing_rsi/__init__.py
src/swing_rsi/cli.py
```

### Added files / untracked files

```text
dashboard/__init__.py
dashboard/app.py
dashboard/pages/__init__.py
dashboard/pages/data_audit.py
dashboard/pages/overview.py
dashboard/pages/research_backtest.py
dashboard/pages/rsi_explorer.py
dashboard/pages/walk_forward.py
dashboard/ui/__init__.py
dashboard/ui/charts.py
dashboard/ui/components.py
dashboard/ui/formatting.py
docs/DASHBOARD_V0_SCOPE.md
docs/CODEX_DASHBOARD_V0_1_HANDOFF.md
scripts/run_dashboard.sh
src/swing_rsi/application/__init__.py
src/swing_rsi/application/datasets.py
src/swing_rsi/application/project_status.py
src/swing_rsi/application/research_service.py
src/swing_rsi/application/validation_service.py
tests/test_application_services.py
tests/test_dashboard_imports.py
```

Note: `docs/CODEX_DASHBOARD_V0_1_HANDOFF.md` was created as the final requested handoff artifact after verification. It did not exist before this report step.

### Deleted files

None.

### Git diff --stat output

`git diff --stat` only includes modified tracked files, not untracked added files.

```text
 .gitignore                |  1 +
 README.md                 |  8 ++++++++
 START_HERE.md             | 10 +++++++++-
 docs/ARCHITECTURE.md      |  8 ++++++++
 docs/CHANGELOG.md         | 10 ++++++++++
 docs/DECISIONS.md         |  6 ++++++
 pyproject.toml            |  9 ++++++---
 scripts/bootstrap_mac.sh  |  3 ++-
 src/swing_rsi/__init__.py |  2 +-
 src/swing_rsi/cli.py      | 35 +++++++++++++++++++++--------------
 10 files changed, 72 insertions(+), 20 deletions(-)
```

### Ignored local artifacts observed

These are intentionally ignored and not tracked:

```text
.streamlit/
.venv/
data/raw/AAPL.csv
data/raw/DEMO.csv
reports/demo_best_trades.csv
reports/demo_features_and_labels.csv
reports/demo_grid_search.csv
reports/demo_scanner_results.csv
```

`git check-ignore -v` confirmed:

- `.env` ignored by `.gitignore`
- `.venv/` ignored by `.gitignore`
- `data/raw/DEMO.csv` ignored by `.gitignore`
- `reports/demo_grid_search.csv` ignored by `.gitignore`
- `.streamlit/config.toml` ignored by `.gitignore`

## 2. Implementation Summary

### Overall dashboard architecture

Dashboard V0.1 adds a local Streamlit interface under `dashboard/`. It is intentionally separate from `src/swing_rsi/` research logic. Streamlit pages call reusable application services under `src/swing_rsi/application/`, and those services call the existing data, features, signals, backtest, research, scanner, and settings modules.

The resulting dependency direction is:

```text
dashboard Streamlit pages
  -> src/swing_rsi/application services
    -> existing swing_rsi data/features/signals/backtest/research modules
```

No separate HTTP API, database, authentication, deployment infrastructure, Node.js, React, Next.js, Svelte, SvelteKit, or FastAPI was added.

### Why Streamlit-specific code is separate

Streamlit code lives under `dashboard/` so the trading/research engine remains importable, testable, and usable from CLI without Streamlit as a mandatory dependency. Streamlit is only an optional local presentation layer. The core research functions remain in typed Python modules under `src/swing_rsi/`.

### Application/service modules added

- `src/swing_rsi/application/project_status.py`
  - `ProjectStatus`
  - `resolve_project_root`
  - `sanitize_url`
  - `collect_project_status`
- `src/swing_rsi/application/datasets.py`
  - `DatasetSummary`
  - `DownloadResult`
  - `StructuralAudit`
  - `discover_raw_datasets`
  - `load_raw_dataset`
  - `slice_date_window`
  - `download_daily_to_raw`
  - `structural_audit_csv`
- `src/swing_rsi/application/research_service.py`
  - `ControlEvaluation`
  - `ResearchRun`
  - `RSIExplorerData`
  - `grid_for_preset`
  - `candidate_rule_count`
  - `retail_control_rule`
  - `evaluate_retail_control`
  - `build_rule_trade_ledger`
  - `build_research_run_id`
  - `research_report_path`
  - `save_research_report`
  - `run_research`
  - `rule_from_result_row`
  - `build_trade_curve`
  - `returns_by_calendar_year`
  - `build_rsi_explorer_data`
- `src/swing_rsi/application/validation_service.py`
  - `WalkForwardAggregate`
  - `WalkForwardRun`
  - `aggregate_walk_forward_results`
  - `run_walk_forward_validation`

### CLI logic extracted into reusable services

`src/swing_rsi/cli.py` was modified so:

- `command_download` calls `download_daily_to_raw` instead of directly mixing provider calls, path construction, saving, and printing.
- `command_research` calls `run_research` instead of directly orchestrating grid search and CSV writing.

The existing CLI behavior remains: `download`, `research`, `demo`, `doctor`, and `fmp-check` still exist.

### How CLI and dashboard share logic

- CLI download and dashboard Data/Audit download both use `download_daily_to_raw`.
- CLI research and dashboard Research/Backtest both use `run_research`.
- Dashboard RSI Explorer uses `build_rsi_explorer_data`, which calls the existing `build_price_features`, `wilder_rsi`, and `generate_rsi_reversal_signal`.
- Dashboard Walk-Forward uses `run_walk_forward_validation`, which calls the existing `run_walk_forward`.

### Dataset discovery and loading

- `discover_raw_datasets(root)` scans only `data/raw/*.csv`.
- Unsupported files such as `.txt`, `.parquet`, `.gitkeep`, caches, and raw ignored files outside the CSV glob are ignored.
- Each CSV is loaded through `load_ohlcv_csv`, which normalizes columns and calls `validate_ohlcv`.
- `slice_date_window` validates and sorts data chronologically before non-mutating date filtering.

### Research run execution

- Dashboard form submission calls `run_research`.
- `run_research`:
  1. Slices the selected date window with `slice_date_window`.
  2. Selects a grid with `grid_for_preset`.
  3. Calls existing `run_grid_search`.
  4. Saves a report with `save_research_report`.
  5. Evaluates the RSI(14)/30 control with `evaluate_retail_control`.

### Report naming and saving

- `build_research_run_id` creates a collision-resistant run ID using ticker, window start, window end, holding period, UTC timestamp, and a random suffix.
- `research_report_path` creates a filename ending in `_grid_search.csv`.
- `save_research_report` refuses to overwrite an existing file by raising `FileExistsError`.
- Reports are written through `atomic_write_csv`.

### Walk-forward aggregation

- `run_walk_forward_validation` calls existing `run_walk_forward`.
- `aggregate_walk_forward_results` computes only from `test_` columns:
  - folds evaluated
  - folds without eligible rules
  - total unseen trades
  - weighted unseen win rate
  - weighted unseen mean return
  - median fold return
  - fraction of positive test folds
  - parameter stability across frozen selected rules
- Training metrics are not used in aggregate test metrics.

### Caching

No Streamlit caching is currently implemented.

This is conservative and satisfies the constraint that non-deterministic or state-changing work must not be cached. Operations deliberately not cached:

- FMP API requests
- downloads/updates
- append or file writes
- research runs
- walk-forward runs
- secrets or API-key status values

Deterministic CSV reads could be cached later, but this milestone does not implement caching.

## 3. File-by-File Report

### Dashboard files

#### `dashboard/__init__.py` - added

Purpose: makes `dashboard` importable for tests and package builds.

Connection: used by dashboard import smoke tests.

#### `dashboard/app.py` - added

Purpose: Streamlit entrypoint for the Overview page.

Important functions:

- `main`

Connection: `scripts/run_dashboard.sh` runs `streamlit run dashboard/app.py`.

#### `dashboard/pages/__init__.py` - added

Purpose: makes `dashboard.pages` importable for tests.

#### `dashboard/pages/overview.py` - added

Purpose: project status overview page.

Important functions:

- `render_page`

Connection:

- Calls `collect_project_status`.
- Displays dataset summary from `discover_raw_datasets`.
- Displays warning banners through UI components.

#### `dashboard/pages/data_audit.py` - added

Purpose: FMP download/update form and structural raw CSV audit.

Important functions:

- `render_page`
- `_years_ago`
- `_window_start_from_preset`

Connection:

- Calls `collect_project_status`.
- Calls `download_daily_to_raw` only after form submission.
- Calls `discover_raw_datasets`, `load_raw_dataset`, `slice_date_window`, and `structural_audit_csv`.

#### `dashboard/pages/rsi_explorer.py` - added

Purpose: interactive RSI chart and close-known candidate signal table.

Important functions:

- `render_page`
- `_years_ago`

Connection:

- Calls `load_raw_dataset`, `slice_date_window`, `build_rsi_explorer_data`, and `retail_control_rule`.
- Uses existing `RSIReversalRule`.

#### `dashboard/pages/research_backtest.py` - added

Purpose: in-sample research and fixed-horizon candidate backtest view.

Important functions:

- `render_page`
- `_years_ago`
- `_preset_value`

Connection:

- Calls `run_research` on explicit form submission.
- Calls `candidate_rule_count`, `grid_for_preset`, `rule_from_result_row`, `build_rule_trade_ledger`, `returns_by_calendar_year`.
- Uses `streamlit.session_state` for submitted research results and selected source path/date/cost settings. No secrets are stored there.

#### `dashboard/pages/walk_forward.py` - added

Purpose: expanding walk-forward validation page.

Important functions:

- `render_page`
- `_years_ago`
- `_preset_value`

Connection:

- Calls `run_walk_forward_validation`.
- Displays `WalkForwardAggregate` output and fold rows.

#### `dashboard/ui/__init__.py` - added

Purpose: makes `dashboard.ui` importable.

#### `dashboard/ui/components.py` - added

Purpose: shared Streamlit UI utilities and persistent warnings.

Important constants/functions:

- `RESEARCH_WARNING`
- `DATA_WARNING`
- `st`
- `repository_root`
- `configure_page`
- `render_integrity_banner`
- `render_page_header`
- `render_navigation`

Connection: used by all dashboard pages.

#### `dashboard/ui/charts.py` - added

Purpose: shared chart helpers.

Important functions:

- `render_price_and_rsi`
- `render_trade_curves`

Connection: uses `build_trade_curve` from application research services.

#### `dashboard/ui/formatting.py` - added

Purpose: simple numeric/percent formatting helpers.

Important functions:

- `percent`
- `decimal`
- `whole`

Connection: used by Research/Backtest page.

### Core Python/application services

#### `src/swing_rsi/application/__init__.py` - added

Purpose: marks shared application services package.

#### `src/swing_rsi/application/project_status.py` - added

Purpose: project status and safe FMP configuration status.

Important classes/functions:

- `ProjectStatus`
- `resolve_project_root`
- `sanitize_url`
- `collect_project_status`

Connection:

- Used by Overview and Data/Audit pages.
- Uses `get_fmp_api_key` only to determine yes/no configuration.
- Does not return the API key.

#### `src/swing_rsi/application/datasets.py` - added

Purpose: dataset discovery, loading, non-mutating date-window slicing, FMP download-to-raw, structural audit.

Important classes/functions:

- `DatasetSummary`
- `DownloadResult`
- `StructuralAudit`
- `discover_raw_datasets`
- `load_raw_dataset`
- `slice_date_window`
- `download_daily_to_raw`
- `structural_audit_csv`

Connection:

- Used by dashboard pages and CLI download.
- Uses existing `download_daily`, `load_ohlcv_csv`, `save_ohlcv_csv`, and `validate_ohlcv`.

#### `src/swing_rsi/application/research_service.py` - added

Purpose: reusable research and RSI explorer orchestration.

Important classes/functions:

- `ControlEvaluation`
- `ResearchRun`
- `RSIExplorerData`
- `grid_for_preset`
- `candidate_rule_count`
- `retail_control_rule`
- `evaluate_retail_control`
- `build_rule_trade_ledger`
- `build_research_run_id`
- `research_report_path`
- `save_research_report`
- `run_research`
- `rule_from_result_row`
- `build_trade_curve`
- `returns_by_calendar_year`
- `build_rsi_explorer_data`

Connection:

- Used by CLI research, Research/Backtest page, RSI Explorer page, chart helpers, and tests.
- Calls existing `run_grid_search`, `backtest_fixed_horizon`, `summarize_trades`, `build_price_features`, `wilder_rsi`, and `generate_rsi_reversal_signal`.

#### `src/swing_rsi/application/validation_service.py` - added

Purpose: walk-forward orchestration and test-only aggregation.

Important classes/functions:

- `WalkForwardAggregate`
- `WalkForwardRun`
- `aggregate_walk_forward_results`
- `run_walk_forward_validation`

Connection:

- Used by Walk-Forward page and tests.
- Calls existing `run_walk_forward`.

#### `src/swing_rsi/cli.py` - modified

Purpose: keep CLI behavior while reusing application services.

Important changes:

- `command_download` now uses `download_daily_to_raw`.
- `command_research` now uses `run_research`.

Connection:

- CLI and dashboard now share same service layer for download and research.

#### `src/swing_rsi/__init__.py` - modified

Purpose: version bumped from `0.1.1` to `0.1.2`.

### Tests

#### `tests/test_application_services.py` - added

Purpose: tests non-UI application services.

Tests prove:

- project status never returns the API key
- dataset discovery ignores unsupported files
- date-window slicing is chronological
- structural audit counts known errors correctly
- candidate-grid count is correct
- research report saving refuses overwrite
- RSI control uses length 14 and lower level 30 only as control
- walk-forward aggregation uses test metrics only
- raw CSV files are not modified by date-window selection

#### `tests/test_dashboard_imports.py` - added

Purpose: import safety for dashboard modules.

Tests prove:

- dashboard imports do not mutate data
- dashboard imports do not attempt a data download

### Scripts

#### `scripts/run_dashboard.sh` - added

Purpose: local dashboard launcher.

Behavior:

1. Resolves repository root from script location.
2. Checks `.venv` exists.
3. Checks `.venv/bin/streamlit` exists.
4. Prints setup command if Streamlit is missing.
5. Sets local `PYTHONPATH`.
6. Sets `HOME` and Streamlit config paths to project-local `.streamlit/`.
7. Writes local non-secret Streamlit config/credentials files if missing.
8. Runs `.venv/bin/streamlit run dashboard/app.py --server.address localhost`.

Connection:

- Primary user launch command: `./scripts/run_dashboard.sh`.

#### `scripts/bootstrap_mac.sh` - modified

Purpose: clean bootstrap installs dashboard dependencies too.

Important change:

- Installs `.[all,dev,dashboard]`.
- Prints dashboard launch command.

### Configuration and dependencies

#### `pyproject.toml` - modified

Purpose:

- version bumped to `0.1.2`
- optional dependency group `dashboard` added
- wheel packages now include `dashboard`
- pytest `pythonpath` includes `.` so dashboard package imports in tests

Important dependency:

```toml
dashboard = [
  "streamlit>=1.40,<2",
]
```

### Documentation

#### `docs/DASHBOARD_V0_SCOPE.md` - added

Purpose: documents dashboard V0.1 scope, exclusions, warnings, launch command, and temporary Streamlit decision.

#### `docs/CODEX_DASHBOARD_V0_1_HANDOFF.md` - added

Purpose: permanent handoff report for ChatGPT audit.

#### `README.md` - modified

Purpose: documents `./scripts/run_dashboard.sh`, the temporary local Streamlit dashboard, and the non-production boundary.

#### `START_HERE.md` - modified

Purpose: adds local dashboard launch step.

#### `docs/ARCHITECTURE.md` - modified

Purpose: documents `application/` services and `dashboard/` local presentation layer boundary.

#### `docs/DECISIONS.md` - modified

Purpose: adds dated decision selecting Streamlit for Dashboard V0.1 local-only UI.

#### `docs/CHANGELOG.md` - modified

Purpose: adds `0.1.2` entry covering dashboard, services, tests, scripts, docs.

### Gitignore and local-artifact handling

#### `.gitignore` - modified

Purpose: adds `.streamlit/` to ignored local artifacts.

Existing generated data/report ignore rules remain:

- `data/raw/*`
- `reports/*`
- `.env`
- `.venv/`
- caches

## 4. Dashboard Page Report

### A. Overview

Works:

- Displays project name: `Swing RSI Self-Learner`.
- Displays package version from `swing_rsi.__version__`.
- Displays Python version.
- Displays project root.
- Displays FMP configured: `yes` or `no`.
- Displays sanitized FMP base URL without query strings or credentials.
- Displays count of raw ticker CSV files.
- Displays count of saved CSV reports.
- Displays dataset table with ticker, path, row count, first date, latest date, modification time, and load error if any.
- Includes page list/navigation text. Streamlit also provides multipage navigation for files under `dashboard/pages/`.
- Includes both persistent warning banners.

Automatic FMP calls:

- No automatic FMP calls are made on page load.

### B. Data and Audit

Works:

- Download/update form includes:
  - ticker
  - provider fixed to FMP
  - start date
  - optional end date
  - explicit submit button
- Default start date is about 10 years before current date.
- Download button is disabled/explained if FMP is not configured.
- Download calls `download_daily_to_raw`, which calls existing FMP provider/service directly. No CLI subprocess is used.
- Success message includes ticker, row count, first date, last date, and saved path.
- No API key or full authenticated URL is displayed.
- Dataset selector lists CSV files under `data/raw/`.
- Structural audit displays:
  - row count
  - first date
  - last date
  - duplicate date rows
  - missing required values
  - missing required columns
  - zero-volume rows
  - invalid OHLC rows
  - nonpositive-price rows
  - ten largest absolute close-to-close moves
  - first five rows
  - last five rows
- Research-window presets:
  - 3 years
  - 5 years
  - 10 years
  - 15 years
  - custom
- Raw file coverage is shown separately from selected research-window row count.
- `slice_date_window` does not modify or truncate the raw CSV.
- Tests verify raw CSV bytes remain unchanged after date-window selection.

Not claimed:

- Exchange-calendar completeness is not claimed.
- Corporate-action completeness is not claimed.

### C. RSI Explorer

Works:

- Uses existing `wilder_rsi` implementation.
- Selectable parameters:
  - ticker/raw CSV
  - date window
  - RSI length 2 through 50
  - lower reference level 5 through 60
  - trigger mode
  - slope window
  - trend filter
- Trigger modes:
  - `cross_above`
  - `turn_up_below`
  - `recent_reclaim`
- Trend filters:
  - `none`
  - `above_sma_50`
  - `above_sma_200`
  - `sma_50_above_200`
- Charts:
  - daily close
  - RSI plus selected lower reference level
- Candidate table includes:
  - signal date
  - close
  - RSI
  - relative volume
  - close position
- Signal label used: `Bullish RSI swing-reversal candidate`.
- Optional RSI(14)/30 control toggle is off by default.
- RSI(14)/30 is not the default recommendation.
- Default visualization values:
  - RSI length 10
  - lower reference 35
  - slope window 1
  - trigger `cross_above`
  - trend `none`
  These are explicitly a display default, not optimized values.

### D. Research and Backtest

Works:

- Form includes:
  - ticker
  - research start
  - research end
  - holding period
  - round-trip cost in basis points
  - minimum trade count
  - grid preset
- Grid presets:
  - Quick plumbing grid
  - Standard research grid
- Default grid is Quick plumbing grid.
- Candidate-count preview is shown before submit.
- Research runs only after explicit form submission.
- Spinner/progress state is used while running.
- Research service saves every completed run to `reports/` with collision-resistant name.
- Saved report filenames include ticker, date range, holding period, UTC timestamp, and unique suffix.
- Existing reports are not overwritten.
- Displays:
  - candidate count
  - eligible candidate count
  - highest-ranked in-sample candidate
  - top candidate table
  - rule parameters
  - trade count
  - win rate
  - mean and median net return
  - lower confidence bound
  - profit factor
  - max drawdown
  - mean MFE
  - mean MAE
  - positive-year fraction
  - research score
- Label used: `Highest-ranked in-sample candidate`.
- Does not use `Best strategy`, `Most accurate`, `Proven`, or `Perfect`.
- RSI(14)/30 control is evaluated under same date window, holding period, cost, and overlap rules.
- Candidate row selection displays:
  - complete trade ledger
  - sequential trade-equity curve
  - drawdown curve
  - returns by calendar year
  - win/loss distribution
  - MFE distribution
  - MAE distribution

Verification note:

- The page load was smoke-tested.
- Full Streamlit form submission was not manually clicked in a browser during this verification.
- The underlying `run_research`, report naming, report overwrite prevention, candidate-grid count, and trade-ledger service behavior were tested through unit tests and CLI demo.

### E. Walk-Forward Validation

Works:

- Form includes:
  - ticker
  - research date range
  - holding period
  - costs
  - minimum training trades
  - number of folds
  - gap
  - grid preset
- Default grid is Quick plumbing grid.
- Candidate-count preview is shown.
- Runs only on explicit form submit.
- Calls `run_walk_forward_validation`, which calls existing `run_walk_forward`.
- Existing walk-forward logic:
  - creates expanding chronological splits
  - searches/selects parameters on training only
  - leaves configured gap
  - freezes selected rule
  - evaluates on next unseen test window
  - records folds with no eligible training rule
- Fold-level display includes the returned fold table, including:
  - training end
  - test start
  - test end
  - selected frozen rule fields
  - training score
  - unseen `test_*` metrics
- Aggregate section is labeled `Out-of-sample walk-forward results`.
- Aggregates:
  - folds evaluated
  - folds without eligible rules
  - total unseen trades
  - weighted unseen win rate
  - weighted unseen mean return
  - median fold return
  - fraction of positive test folds
  - parameter stability
- Aggregation uses test metrics only.
- Tests verify training metrics do not leak into aggregate test metrics.

## 5. Data Flow

One complete workflow:

1. User selects a ticker.
   - Dashboard: `dashboard/pages/*.py` selectbox.
   - Dataset source: `discover_raw_datasets` in `src/swing_rsi/application/datasets.py`.

2. Data is loaded or downloaded.
   - Existing file load: `load_raw_dataset` -> `load_ohlcv_csv`.
   - Download: `download_daily_to_raw` -> `download_daily` -> `download_fmp_daily`.

3. Data is validated.
   - `load_ohlcv_csv` normalizes columns and calls `validate_ohlcv`.
   - `download_fmp_daily` normalizes FMP rows and calls `validate_ohlcv`.

4. Date window is selected.
   - `slice_date_window` validates, sorts chronologically, and filters rows.
   - It does not write back to raw CSV.

5. Features and RSI values are calculated.
   - Price features: `build_price_features` in `src/swing_rsi/features/price.py`.
   - RSI: `wilder_rsi` in `src/swing_rsi/features/rsi.py`.

6. Candidate rules are generated.
   - Grid presets: `grid_for_preset`.
   - Existing grids: `compact_demo_grid`, `default_research_grid`.
   - Rule class: `RSIReversalRule`.
   - Rule iteration: `RSIParameterGrid.rules`.

7. Signals are created.
   - `generate_rsi_reversal_signal` in `src/swing_rsi/signals/rsi_reversal.py`.
   - Signals are close-known and use current/prior values.

8. Trades are simulated.
   - `backtest_fixed_horizon` in `src/swing_rsi/backtest/engine.py`.
   - Entry: next session open.
   - Exit: close at signal index plus holding period.
   - Overlap: one open trade per ticker.

9. Metrics are calculated.
   - `summarize_trades` in `src/swing_rsi/backtest/metrics.py`.

10. Results are ranked.
   - `run_grid_search` ranks by:
     - `eligible`
     - `score`
     - `trade_count`
     - `mean_return`
   - Win rate is not the sole ranking criterion.

11. Reports are saved.
   - `run_research` adds run metadata and calls `save_research_report`.
   - `save_research_report` refuses overwrite.
   - `atomic_write_csv` performs atomic CSV writes.

12. Walk-forward validation is performed.
   - `run_walk_forward_validation` calls `run_walk_forward`.
   - `aggregate_walk_forward_results` summarizes only test metrics.

## 6. RSI and Backtesting Behavior

- RSI formula: Wilder RSI.
- Implementation file: `src/swing_rsi/features/rsi.py`.
- Function: `wilder_rsi`.
- Seed/warm-up:
  - uses simple average of the first `length` gains/losses as Wilder seed.
  - first RSI value is placed at index position `length`.
  - rows before warm-up are `NaN`.
  - if series length is `<= length`, all RSI outputs are `NaN`.
- Missing RSI handling:
  - `wilder_rsi` rejects missing/non-numeric close inputs.
  - signal generation fills missing signal values as `False`.
- Available RSI lengths:
  - RSI Explorer UI: 2 through 50.
  - Quick grid: 2, 3, 5, 8, 14, 21.
  - Standard grid: 2 through 30.
- Available lower levels:
  - RSI Explorer UI: 5 through 60.
  - Quick grid: 20, 25, 30, 35, 40, 45.
  - Standard grid: 10 through 55 in steps of 5.
- Available slope windows:
  - RSI Explorer UI: 1, 2, 3, 5, 10.
  - Quick grid: 1, 2, 3.
  - Standard grid: 1, 2, 3, 5, 10.
- Trigger modes:
  - `cross_above`: prior RSI at/below lower level and current RSI above lower level.
  - `turn_up_below`: RSI at/below lower level and slope positive.
  - `recent_reclaim`: RSI was below within prior 1 to 3 bars, now above lower level and slope positive.
- Trend filters:
  - `none`
  - `above_sma_50`
  - `above_sma_200`
  - `sma_50_above_200`
- Signal timing:
  - signals are known at daily close.
- Entry timing:
  - next session open (`signal_position + 1`).
- Same-close entry:
  - no. A signal known at the close cannot enter at that same close in the implemented backtester.
- Exit timing:
  - close of bar `signal_position + holding_period`.
- Holding-period interpretation:
  - for holding period `H`, entry is at next open after signal bar `t`, and exit is close at bar `t + H`.
- Transaction-cost treatment:
  - `round_trip_cost_bps / 10000` is subtracted from gross return to produce net return.
- Overlapping-trade treatment:
  - signals while a trade is open are ignored.
  - a signal on the exit close is allowed to enter the following session.
- MFE:
  - maximum high from entry bar through exit bar, divided by entry price, minus 1.
- MAE:
  - minimum low from entry bar through exit bar, divided by entry price, minus 1.
- Equity curve:
  - `(1 + net_return).cumprod()`.
- Drawdown:
  - `equity / equity.cummax() - 1`.
- Profit factor:
  - sum of positive net returns divided by absolute sum of negative net returns.
  - infinity if there are no negative returns.
- Confidence-bound calculation:
  - lower confidence bound = mean return - `1.645 * standard_error`.
  - standard error = sample standard deviation divided by square root of trade count.
- Research-score formula:
  - `mean_return_lcb_90 * log1p(trade_count)` if eligible.
  - `-inf` if not eligible.
- Minimum-trade filtering:
  - eligible when trade count is greater than or equal to configured minimum.

## 7. Research-Integrity Audit

| Item | Status | Evidence |
|---|---|---|
| No look-ahead leakage | PASS | `build_price_features` uses rolling/current/prior data. Test `test_trailing_features_do_not_change_when_later_bars_change` verifies future-bar mutation does not alter prior features. |
| No same-close entry from a close-known signal | PASS | `backtest_fixed_horizon` uses `entry_position = signal_position + 1`. Test `test_backtester_enters_next_open_and_prevents_overlap` verifies next-open entry. |
| No future-derived feature columns | PASS | Feature construction in `features/price.py` uses trailing/current data. Future labels are in `features/labels.py` and prefixed `label_`. |
| Label columns are excluded from model features | PARTIAL | `assert_no_label_features` exists and test verifies it rejects `label_` columns. Current grid/search code does not build a model feature matrix and does not call this guard at every dashboard boundary. Current signal logic does not consume `label_` columns. |
| Training and test results remain separate | PASS | `run_walk_forward` stores training fields separately from `test_*` fields. Dashboard labels aggregate as out-of-sample. |
| Walk-forward rules are frozen before each test period | PASS | `run_walk_forward` selects best rule from training results, constructs `rule`, then evaluates test mask with that rule. |
| Aggregate walk-forward metrics use test results only | PASS | `aggregate_walk_forward_results` reads `test_trade_count`, `test_win_rate`, and `test_mean_return`; test `test_walk_forward_aggregation_uses_test_metrics_only` verifies training metrics do not affect aggregate. |
| Transaction costs are retained | PASS | Dashboard form accepts cost bps; `run_research`, `evaluate_retail_control`, `build_rule_trade_ledger`, and `run_walk_forward_validation` pass cost into backtest/search. |
| Failed trades are retained | PASS | Trade ledgers include all non-overlapping completed trades, including negative returns. No filtering removes losing trades. |
| RSI 14/30 is only a comparison control | PASS | `retail_control_rule` uses `control_rules`; dashboard control toggle is off by default in RSI Explorer; Research/Backtest displays it as `RSI(14)/30 control`. |
| Win rate is not sole ranking criterion | PASS | `run_grid_search` sorts by `eligible`, `score`, `trade_count`, `mean_return`; `score` is based on lower confidence bound and trade count. |
| Synthetic results are clearly identified as synthetic | PASS | CLI demo prints `Synthetic results are not evidence of a real trading edge.` README and docs also state this. |
| In-sample candidates are not described as proven | PASS | Dashboard labels use `Highest-ranked in-sample candidate`, not proven/perfect/accurate. |
| Raw FMP data limitations remain disclosed | PASS | Persistent dashboard banner and docs disclose FMP semantics are unaudited. |
| Corporate-action semantics remain disclosed | PASS | Banner says FMP corporate-action semantics have not been fully audited. |
| Survivorship-bias limitations remain disclosed | PASS | README and source docs retain survivorship-bias limitations; dashboard scope does not claim universe completeness. |

## 8. Security Audit

| Check | Status | Evidence |
|---|---|---|
| `.env` was not committed | PASS | `git ls-files .env` returned no file; `.env` ignored by `.gitignore`. |
| `.env` contents were never printed | PASS | `.env` was not opened or printed during this handoff. |
| API key does not appear in source files | PASS | Source scans found secret-handling variable names and dummy test strings only, not a real key. `.env` was excluded and not read. |
| API key does not appear in tests | PASS | Tests contain dummy values only. The real key was not read, copied, or compared. |
| API key does not appear in reports | PASS | `rg -l` over generated `reports`, `data/raw`, and `.streamlit` for key-related patterns returned no files. |
| API key does not appear in logs | PASS | Command outputs did not print a key. FMP live requests were not run. |
| API key does not appear in Streamlit session state | PASS | Dashboard stores research results, paths, dates, costs, and settings only; no FMP key is assigned to session state. |
| Full authenticated URLs are not exposed | PASS | FMP provider sends key in headers and tests assert `apikey` is not in request params. Dashboard displays only sanitized base URL. |
| Raw licensed market data ignored by Git | PASS | `data/raw/*` ignored; only `.gitkeep` tracked. |
| Generated reports ignored if required | PASS | `reports/*` ignored; only `.gitkeep` tracked. |
| Streamlit cache/config files ignored | PASS | `.streamlit/` added to `.gitignore`; `git check-ignore` confirmed `.streamlit/config.toml` ignored. |
| No external FMP calls during automated tests | PASS | Tests use mocked FMP response; dashboard import test prevents data download on import. |
| Dashboard imports do not make network requests | PASS | `tests/test_dashboard_imports.py` monkeypatches `download_daily` to fail if called during imports; test passed. |
| Dashboard startup does not automatically contact FMP | PASS | Startup smoke loaded server and pages without submitting download form; no FMP check/download was run. |

How accidental secret exposure was checked:

- Did not open `.env`.
- Confirmed `.env` is untracked and ignored.
- Confirmed tracked files do not include `.env`, `.venv`, raw CSVs, generated reports, or `.streamlit`.
- Searched tracked files and new dashboard/application files for key-related terms. Matches were limited to configuration variable names, security docs, provider code, and dummy test values.
- Searched generated `reports`, `data/raw`, and `.streamlit` for key-related patterns; no matching files were returned.

## 9. Dependencies

Added dependency:

| Dependency | Constraint | Mandatory or optional | Why needed |
|---|---|---|---|
| Streamlit | `streamlit>=1.40,<2` | Optional group `dashboard` | Local research dashboard UI. |

Relevant `pyproject.toml` group:

```toml
dashboard = [
  "streamlit>=1.40,<2",
]
```

No extra chart dependency was added. Charts use Streamlit built-ins.

Dependencies explicitly not added:

- Svelte
- SvelteKit
- React
- Next.js
- FastAPI
- Node.js
- database drivers
- authentication packages
- deployment tooling
- Celery/Redis/background queue infrastructure

## 10. Commands Executed

### Git commands

| Command | Result | Notes |
|---|---|---|
| `git switch -c feat/local-research-dashboard` | failed first time | Sandbox could not create Git ref directory. |
| `git switch -c feat/local-research-dashboard` with approval | exit 0 | Branch created. |
| `git status --short` | exit 0 | Working tree dirty with intended changes. |
| `git status --short --branch` | exit 0 | Branch `feat/local-research-dashboard`. |
| `git rev-parse HEAD` | exit 0 | `353b583429db0a8b5fda3849b555390b4b37fc75`. |
| `git diff --stat` | exit 0 | Tracked diff stat shown above. |
| `git diff --name-status` | exit 0 | Listed modified tracked files. |
| `git ls-files --others --exclude-standard` | exit 0 | Listed untracked added files. |
| `git branch --list feat/local-research-dashboard` | exit 0 | Branch exists. |
| `git branch -vv` | exit 0 | No upstream shown. |
| `git remote -v` | exit 0 | No remotes returned. |

### Installation commands

| Command | Result | Notes |
|---|---|---|
| `./.venv/bin/python -m pip install -e '.[dashboard]'` | failed first time | DNS/network blocked PyPI access in sandbox. |
| `./.venv/bin/python -m pip install -e '.[dashboard]'` with approval | exit 0 | Installed Streamlit and dependencies; editable package updated to `0.1.2`. |

### Test and quality commands

| Command | Result | Important output |
|---|---|---|
| `./.venv/bin/pytest` | exit 0 | 28 collected, 28 passed. |
| `./.venv/bin/ruff check .` | exit 0 | All checks passed. |
| `./.venv/bin/ruff format .` | exit 0 | Reformatted 15 files during implementation; final run left 58 files unchanged. |
| `./.venv/bin/ruff format --check .` | exit 0 | 58 files already formatted. |
| `./.venv/bin/mypy src` | exit 0 | No issues found in 35 source files. |

Earlier development check failures:

- Initial pytest failed because `dashboard` was not importable. Fixed by adding package markers and pytest path.
- Initial Ruff found formatting/style items. Fixed and reran.
- Initial mypy found pandas typing issues. Fixed and reran.

### Demo and dashboard smoke commands

| Command | Result | Important output |
|---|---|---|
| `./.venv/bin/python -m swing_rsi.cli demo` | exit 0 | Generated synthetic `DEMO.csv`, evaluated 432 rules, printed synthetic warning. |
| Streamlit `AppTest.from_file(...).run()` for all five pages | exit 0 | Loaded `dashboard/app.py` and four page files. Warnings: missing ScriptRunContext in bare test mode, ignorable. |
| `./scripts/run_dashboard.sh` | initially failed twice | First failure: Streamlit tried to write under home config outside sandbox. Fixed launcher to use project-local `.streamlit` and `HOME`. Second failure: sandbox blocked socket bind. |
| `./scripts/run_dashboard.sh` with approval | server started | Uvicorn server started on `localhost:8502`; Streamlit printed Watchdog performance suggestion. |
| `curl -I http://localhost:8502` | exit 0 | Returned `HTTP/1.1 200 OK`. |
| Ctrl-C to server session | exit 0 | Server stopped cleanly. |

### Security and artifact verification commands

| Command | Result | Notes |
|---|---|---|
| `git ls-files .env .venv data/raw reports .streamlit` | exit 0 | Only `.gitkeep` files under data/report were tracked. |
| `git check-ignore -v .env .venv data/raw/DEMO.csv reports/demo_grid_search.csv .streamlit/config.toml` | exit 0 | Confirmed ignore rules. |
| `git grep -n -E 'FMP_API_KEY|apikey|api_key|secret|credential|token' -- . ...` | exit 0 | Found only expected variable names/docs/dummy tests. |
| `rg -l ... reports data/raw .streamlit` | exit 0 | Returned no matching files. |
| `rg -n -e ... dashboard src/swing_rsi/application ...` | exit 0 | Found only service calls, dummy test values, `token` helper naming, local Streamlit credentials file creation with empty email. |

## 11. Test Results

### `pytest`

Command:

```bash
./.venv/bin/pytest
```

Result:

- Exit status: 0
- Tests collected: 28
- Tests passed: 28
- Tests failed: 0
- Tests skipped: 0
- Important output:

```text
tests/test_application_services.py .........                             [ 32%]
tests/test_backtester.py .                                               [ 35%]
tests/test_dashboard_imports.py .                                        [ 39%]
tests/test_data_validation.py ..                                         [ 46%]
tests/test_fmp_provider.py ....                                          [ 60%]
tests/test_forward_journal.py .                                          [ 64%]
tests/test_no_future_leakage.py ...                                      [ 75%]
tests/test_rsi.py ....                                                   [ 89%]
tests/test_settings.py ..                                                [ 96%]
tests/test_walk_forward.py .                                             [100%]
============================== 28 passed in 0.16s ==============================
```

### `ruff check .`

Command:

```bash
./.venv/bin/ruff check .
```

Result:

- Exit status: 0
- Output: `All checks passed!`

### `ruff format --check .`

Command:

```bash
./.venv/bin/ruff format --check .
```

Result:

- Exit status: 0
- Output: `58 files already formatted`

### `mypy src`

Command:

```bash
./.venv/bin/mypy src
```

Result:

- Exit status: 0
- Output: `Success: no issues found in 35 source files`

### Dashboard import and headless startup smoke

Commands:

- Streamlit AppTest script loading:
  - `dashboard/app.py`
  - `dashboard/pages/data_audit.py`
  - `dashboard/pages/rsi_explorer.py`
  - `dashboard/pages/research_backtest.py`
  - `dashboard/pages/walk_forward.py`
- `./scripts/run_dashboard.sh`
- `curl -I http://localhost:8502`

Result:

- AppTest exit status: 0
- Every page listed as loaded.
- Warning: Streamlit missing `ScriptRunContext` warnings in bare test mode. These are test-runner warnings, not page exceptions.
- Server startup: succeeded with approval.
- HTTP check: `HTTP/1.1 200 OK`.
- Server stopped cleanly with Ctrl-C.

### Newly added tests

#### `tests/test_application_services.py`

- `test_project_status_never_returns_api_key`
  - Proves `collect_project_status` reports configured status without returning the API key.
- `test_dataset_discovery_ignores_unsupported_files`
  - Proves only raw CSVs are discovered.
- `test_date_window_slicing_is_chronological`
  - Proves date-window slicing returns chronological data.
- `test_structural_audit_counts_known_errors`
  - Proves duplicate dates, missing values, zero volume, invalid OHLC, and nonpositive prices are counted.
- `test_candidate_grid_count_is_correct`
  - Proves quick grid count is 432.
- `test_research_report_naming_does_not_overwrite`
  - Proves report save refuses overwrite.
- `test_rsi_control_uses_14_30_only_as_control`
  - Proves control rule is length 14 and lower level 30.
- `test_walk_forward_aggregation_uses_test_metrics_only`
  - Proves aggregate walk-forward metrics use `test_*` metrics and ignore training metrics.
- `test_date_window_selection_does_not_modify_raw_csv`
  - Proves date-window selection does not mutate raw CSV bytes.

#### `tests/test_dashboard_imports.py`

- `test_dashboard_imports_do_not_mutate_data_or_call_fmp`
  - Proves dashboard modules import without mutating data.
  - Monkeypatches download function to fail if any import attempts a data download.

## 12. Dashboard Smoke Test

### How it was performed

1. Refreshed local synthetic/demo data:

```bash
./.venv/bin/python -m swing_rsi.cli demo
```

2. Used Streamlit testing API:

```python
from pathlib import Path
from streamlit.testing.v1 import AppTest

pages = [
    Path("dashboard/app.py"),
    Path("dashboard/pages/data_audit.py"),
    Path("dashboard/pages/rsi_explorer.py"),
    Path("dashboard/pages/research_backtest.py"),
    Path("dashboard/pages/walk_forward.py"),
]
for page in pages:
    at = AppTest.from_file(str(page)).run(timeout=30)
    if at.exception:
        raise SystemExit(...)
```

3. Started actual local server:

```bash
./scripts/run_dashboard.sh
```

4. Checked HTTP response:

```bash
curl -I http://localhost:8502
```

5. Stopped process with Ctrl-C.

### Results

- Synthetic data was available at `data/raw/DEMO.csv`.
- All five pages loaded in AppTest:
  - `dashboard/app.py`
  - `dashboard/pages/data_audit.py`
  - `dashboard/pages/rsi_explorer.py`
  - `dashboard/pages/research_backtest.py`
  - `dashboard/pages/walk_forward.py`
- Server started.
- Local port used by smoke test: `8502`.
- HTTP result: `HTTP/1.1 200 OK`.
- Process stopped cleanly.
- Warnings:
  - AppTest emitted `missing ScriptRunContext` warnings in bare mode. These are expected for Streamlit test runner and did not fail the test.
  - Streamlit server printed optional Watchdog performance suggestion.
- Console errors: none after launcher fixes.
- External FMP request: none made during smoke. No download form was submitted.

Important limitation: AppTest verified that every page loads. It did not simulate every widget interaction or submit every Streamlit form.

## 13. Manual User Instructions

### 1. Open Terminal

Open Terminal on the Mac.

### 2. Navigate to the repository

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

If that path does not resolve because of local casing, use:

```bash
cd /Users/billyribeiro/trading-projects/swing-rsi-self-learner
```

### 3. Activate `.venv`

```bash
source .venv/bin/activate
```

### 4. Install dashboard dependency if needed

If Streamlit is not installed:

```bash
.venv/bin/python -m pip install -e ".[all,dev,dashboard]"
```

### 5. Start the dashboard

Primary launch command:

```bash
./scripts/run_dashboard.sh
```

### 6. Open in browser

The script prints a URL such as:

```text
http://localhost:8501
```

or, if that port is occupied:

```text
http://localhost:8502
```

Open the printed URL in the browser.

### 7. Stop the dashboard

In the Terminal where the dashboard is running, press:

```text
Control-C
```

### 8. Restart later

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
source .venv/bin/activate
./scripts/run_dashboard.sh
```

### If the script reports Streamlit is missing

Run:

```bash
.venv/bin/python -m pip install -e ".[all,dev,dashboard]"
./scripts/run_dashboard.sh
```

## 14. Known Limitations

- Dashboard is local Streamlit only; not a production trading application.
- No scanner execution was added.
- No forward-journal editing was added.
- No options, NLP, intraday data, brokerage connectivity, or live trading was added.
- No authentication, deployment, database, background queue, Celery, Redis, or multiprocessing infrastructure was added.
- No explicit Streamlit caching is implemented.
- Overview page provides page list and Streamlit multipage navigation, but no custom styled navigation system.
- Data audit is structural only. It does not verify exchange-calendar completeness.
- Data audit does not prove corporate-action adjustment correctness.
- Data audit does not prove delisted coverage or point-in-time universe membership.
- FMP split/dividend semantics remain unaudited.
- FMP historical-universe semantics remain unaudited.
- Survivorship-bias controls remain unresolved.
- Research standard grid currently uses RSI lengths 2 through 30, not the full 2 through 50 stated as a broad V1 search dimension.
- Standard grid lower levels are 10 through 55, not full 5 through 60.
- Upper-region/overbought logic is not implemented.
- Divergence, failure swing, and compression-expansion triggers are not implemented.
- SPY/QQQ regime features are not implemented.
- Walk-forward aggregation reports fold-level summaries, not a combined unseen trade ledger.
- Streamlit form submission behavior was not exhaustively browser-click tested; underlying service functions and page loads were tested.
- Live FMP download was not executed during verification to avoid external provider calls and secret exposure risk.
- Research/backtest page can be slow on large datasets with the Standard grid.
- `.streamlit/` config files are generated locally and ignored by Git.
- Generated reports and raw data are ignored by Git; users must manage them locally.
- Report `git diff --stat` does not include untracked added files, by Git behavior.

## 15. Deviations From Original Prompt

| Requirement | Status | Relevant file | Explanation |
|---|---|---|---|
| Read required docs before editing | COMPLETE | Conversation/tool log | Required docs were read first, then a pre-change report was provided. |
| Use Streamlit | COMPLETE | `pyproject.toml`, `dashboard/app.py` | Added optional Streamlit dependency and local Streamlit dashboard. |
| Do not add Svelte/SvelteKit/React/Next/FastAPI/Node/API/database/auth/deploy | COMPLETE | entire change set | None were added. |
| Keep dashboard as thin presentation layer | COMPLETE | `dashboard/*`, `src/swing_rsi/application/*` | Dashboard calls application services, which call core modules. |
| Keep market-data/RSI/signals/backtest/research under `src/swing_rsi/` | COMPLETE | `src/swing_rsi/application/*` | Core logic remains in `src/swing_rsi/`. |
| Do not duplicate research logic in Streamlit pages | COMPLETE | `dashboard/pages/*.py` | Pages call services such as `run_research` and `build_rsi_explorer_data`. |
| Do not invoke CLI with subprocesses | COMPLETE | `dashboard/pages/*.py` | No dashboard subprocess calls. |
| Extract reusable CLI logic if needed | COMPLETE | `src/swing_rsi/cli.py`, `src/swing_rsi/application/*` | Download and research commands now use services. |
| Never expose API key or `.env` | COMPLETE | `project_status.py`, tests | Status returns yes/no only; `.env` not opened. |
| Dashboard may display FMP configured yes/no only | COMPLETE | `overview.py`, `data_audit.py` | It displays yes/no and sanitized base URL. |
| No future leakage | COMPLETE | existing core plus tests | Existing leakage tests still pass. |
| No same-close entry | COMPLETE | `backtest/engine.py` | Entry remains next open. |
| No ranking by win rate alone | COMPLETE | `research/grid_search.py` | Ranking uses eligible, score, trade count, mean return. |
| RSI 14/30 as control, not default recommendation | COMPLETE | `research_service.py`, dashboard pages | Control function and optional comparison only. |
| Persistent research warning banner | COMPLETE | `dashboard/ui/components.py` | Rendered by `render_page_header`. |
| Persistent FMP audit warning banner | COMPLETE | `dashboard/ui/components.py` | Rendered by `render_page_header`. |
| Add optional dependency group `dashboard` | COMPLETE | `pyproject.toml` | `streamlit>=1.40,<2`. |
| Do not make Streamlit mandatory for CLI | COMPLETE | `pyproject.toml` | Streamlit is optional. |
| Suggested dashboard structure | COMPLETE | `dashboard/` | Used app/pages/ui structure. |
| Suggested application services structure | COMPLETE | `src/swing_rsi/application/` | Added status, datasets, research, validation services. |
| Create `scripts/run_dashboard.sh` | COMPLETE | `scripts/run_dashboard.sh` | Uses `.venv/bin/streamlit`; handles missing Streamlit. |
| Update bootstrap to install dashboard dependency | COMPLETE | `scripts/bootstrap_mac.sh` | Installs `.[all,dev,dashboard]`. |
| Overview page requirements | COMPLETE | `dashboard/pages/overview.py` | Displays project, version, Python, root, FMP status, base URL, raw counts, report counts, dataset dates/rows/mtime. |
| Overview no automatic FMP calls | COMPLETE | `overview.py`, tests | Status checks config only; no provider request. |
| Data and Audit download form | COMPLETE | `data_audit.py` | Ticker, FMP fixed, start/end, submit button. |
| Data and Audit default start about 10 years | COMPLETE | `data_audit.py` | `_years_ago(10)`. |
| Data and Audit structural audit | COMPLETE | `datasets.py`, `data_audit.py` | Counts requested structural issues. |
| Raw coverage separate from research window | COMPLETE | `data_audit.py` | Displays raw coverage and selected-window rows. |
| Do not claim exchange-calendar completeness | COMPLETE | `data_audit.py`, docs | No such claim. |
| RSI Explorer parameters | COMPLETE | `rsi_explorer.py` | Ticker, window, length 2-50, lower 5-60, trigger, slope, trend. |
| RSI Explorer uses Wilder RSI | COMPLETE | `research_service.py` | Calls existing `wilder_rsi`. |
| RSI Explorer control toggle off by default | COMPLETE | `rsi_explorer.py` | `value=False`. |
| Research/Backtest form with required fields | COMPLETE | `research_backtest.py` | Fields implemented. |
| Quick and Standard grid | COMPLETE | `research_service.py` | `grid_for_preset`. |
| Candidate count before run | COMPLETE | `research_backtest.py`, `walk_forward.py` | Uses `candidate_rule_count`. |
| Research runs only on submit | COMPLETE | `research_backtest.py` | Uses `st.form_submit_button`. |
| Save completed research runs with collision-resistant ID | COMPLETE | `research_service.py` | Run ID includes ticker/window/holding period/timestamp/suffix. |
| Do not overwrite existing report | COMPLETE | `research_service.py`, tests | `save_research_report` raises `FileExistsError`. |
| Display requested metrics | COMPLETE | `research_backtest.py` | Candidate/control metrics table. |
| Label highest row in-sample candidate | COMPLETE | `research_backtest.py` | Uses `Highest-ranked in-sample candidate`. |
| Always evaluate RSI(14)/30 control | COMPLETE | `research_backtest.py`, `research_service.py` | Control evaluated under same settings. |
| Candidate row trade ledger/charts/distributions | COMPLETE | `research_backtest.py`, `charts.py` | Implemented. |
| Walk-forward form fields | COMPLETE | `walk_forward.py` | Implemented. |
| Walk-forward via reusable service | COMPLETE | `validation_service.py` | Calls existing `run_walk_forward`. |
| Pure tested aggregation function | COMPLETE | `validation_service.py`, tests | `aggregate_walk_forward_results` tested. |
| Aggregate must not mix training/test | COMPLETE | `validation_service.py`, tests | Uses `test_*` columns only. |
| Streamlit forms to avoid reruns | COMPLETE | data/research/walk pages | Expensive actions behind forms. |
| Use caching only deterministic reads | CHANGED | dashboard pages | No caching implemented. This avoids improper caching; deterministic read caching can be added later. |
| Do not cache API keys/API writes/research runs | COMPLETE | dashboard pages/services | No caching used for these operations. |
| Expected errors concise | PARTIAL | dashboard pages | Common `FileNotFoundError`, `RuntimeError`, `ValueError`, `FileExistsError` are caught. Unexpected exceptions not specially logged. |
| Disable/explain operations when no `.env`/key | COMPLETE | `data_audit.py` | Download disabled when FMP not configured. |
| Tests for all new non-UI services | COMPLETE | `tests/test_application_services.py` | Added required service tests. |
| Dashboard imports do not mutate data or make FMP calls | COMPLETE | `tests/test_dashboard_imports.py` | Test passes. |
| Run checks | COMPLETE | verification | pytest, Ruff, format, mypy all run and pass. |
| Headless Streamlit startup smoke | COMPLETE | verification | AppTest all pages and local server HTTP 200. |
| Verify all five pages load | COMPLETE | verification | AppTest loaded all five. |
| No external FMP calls during tests | COMPLETE | tests | Mocked FMP tests only; no fmp-check run. |
| Create dashboard scope doc | COMPLETE | `docs/DASHBOARD_V0_SCOPE.md` | Added. |
| Update README/START/ARCH/DECISIONS/CHANGELOG | COMPLETE | docs | Updated. |
| Update OPEN_QUESTIONS if new research questions appear | NOT APPLICABLE | `docs/OPEN_QUESTIONS.md` | No new methodological question was introduced; existing FMP/cost/holdout questions remain. |
| Document Streamlit temporary and future SvelteKit/FastAPI possibility | COMPLETE | `README.md`, `docs/DASHBOARD_V0_SCOPE.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` | Documented. |
| Create branch `feat/local-research-dashboard` | COMPLETE | git | Branch exists and is active. |
| Do not push | COMPLETE | git | No remote configured; no push. |
| Do not commit secrets/raw data/reports/caches | COMPLETE | gitignore/security check | No commit made; generated artifacts ignored. |

## 16. Recommended Next Step

Smallest sensible next milestone:

Implement the M1 FMP real-data ingestion audit for the existing daily swing-RSI workflow.

Scope should stay narrow:

- provider-neutral raw/processed cache metadata
- reproducible FMP provenance
- per-symbol data-quality reports
- missing/duplicate/stale/impossible OHLCV checks
- split/dividend adjustment semantics investigation
- SPY, QQQ, and initial universe audit
- documentation of whether a second provider is required

Do not add options, NLP, intraday data, brokerage execution, live trading, auth, deployment, database, or SvelteKit in the next milestone.

## 17. Permanent Handoff File

Saved as:

```text
docs/CODEX_DASHBOARD_V0_1_HANDOFF.md
```

No existing handoff file was present before saving; no old report was overwritten.
