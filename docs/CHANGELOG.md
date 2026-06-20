# Changelog

## Unreleased

- Added the Self-Learning Swing Trading Engine vertical slice with configurable universe, raw-data manifests, autonomous feature registry, bullish/bearish labels, chronological model discovery, model registry, scanner snapshots, attribution, portfolio scanner backtesting, append-only paper-forward events, and daily-cycle orchestration.
- Added primary Streamlit dashboard sections for Data and Universe, Discovery Lab, Live Scanner, Candidate Attribution, Portfolio Backtests, Paper Forward Test, Model Registry, and Baselines and Legacy RSI.
- Added CLI commands for `universe-update`, `build-features`, `discover-models`, `model-registry`, `promote-model`, `scan`, `forward-update`, and `daily-cycle`.
- Added `configs/universe/core.yaml` seed universe for large stocks, broad ETFs, sector ETFs, inverse ETFs, and leveraged ETFs.
- Added scikit-learn, joblib, and pyarrow dependencies for local model discovery and parquet artifacts.
- Added autonomous-engine regression tests for backward-looking features, label isolation, purged splits, registry immutability, scanner idempotency, scanner-candidate persistence, append-only forward events, and next-open portfolio entries.
- Added a naive historical base-rate classifier as an explicit model-discovery baseline.
- Added holdout permutation-importance and feature-stability diagnostics to registered model metrics.
- Added drift reporting for feature and prediction distributions; drift can alert and train challengers later, but it does not mutate or promote models.
- Completed the paper-forward vertical slice from latest scanner events through pending entries, next-session paper fills, position marks, and time exits with idempotent append-only events.
- Fixed `scripts/run_daily_cycle.sh` executable permissions and verified the wrapper returns idempotent daily-cycle status.
- Fixed walk-forward split planning so automatically calculated test folds reserve the configured gap before sizing test windows.
- Added a canonical split-plan object shared by dashboard preflight validation and actual walk-forward execution.
- Added dashboard split-plan details for requested dates, effective trading sessions, available sessions, initial training sessions, sessions per test fold, gap, folds, total required sessions, and validity status.
- Added regression tests for the confirmed 2,514-session, 5-fold, 10-gap AAPL configuration and for preview/execution split-plan identity.

## 0.1.2-dashboard-v0.2 — 2026-06-19

- Replaced Streamlit filename-derived multipage navigation with explicit `st.navigation` / `st.Page` registration.
- Moved active page renderers to `dashboard/sections/` and removed auto-discovered `dashboard/pages/*.py` source files.
- Added ticker normalization so filename input such as `AAPL.csv` becomes provider symbol `AAPL` and path/traversal input is rejected.
- Split Data and Audit into separate selected-window and full-raw-file audit scopes.
- Added pure dataframe structural auditing through `structural_audit_frame`.
- Added readable dashboard display formatting for dates, prices, percentages, volume, and table column names.
- Reworked Data and Audit download controls into explicit update-existing and custom-download workflows.
- Added mtime-keyed local CSV read caching and cache invalidation after successful dataset updates.
- Added dashboard error handling with concise UI messages and ignored local logs for unexpected exceptions.
- Added walk-forward configuration prevalidation in the application service wrapper.
- Added tests for navigation order, ticker normalization, selected-window audit behavior, formatting, cache invalidation, AppTest interactions, and no-network dashboard startup.
- Added `watchdog` to the optional `dashboard` dependency group so local Streamlit runs can use filesystem event watching and avoid the performance hint.
- Disabled Streamlit's automatic file watcher in `scripts/run_dashboard.sh` to prevent browser reload loops while local ignored artifacts change during dashboard use.

## 0.1.2 — 2026-06-19

- Added local Streamlit research dashboard scaffold with overview, data audit, RSI explorer, research/backtest, and walk-forward pages.
- Added shared application services for project status, dataset discovery, structural audits, research runs, report naming, RSI explorer data, and walk-forward aggregation.
- Added no-overwrite research report saving with collision-resistant run IDs.
- Added `dashboard` optional dependency group and `scripts/run_dashboard.sh`.
- Updated CLI download and research commands to reuse application services.
- Added tests for dashboard-support services, import safety, report overwrite prevention, and test-only walk-forward aggregation.
- Documented the dashboard scope, temporary Streamlit boundary, and launch command.
- Hardened Dashboard V0.1 navigation to expose exactly five user-facing sections without a duplicate Overview page.
- Changed dashboard/CLI data downloads from overwrite saves to atomic merge updates that preserve existing ticker history.
- Added walk-forward boundary regression tests and form interaction smoke tests for RSI Explorer, research submission, candidate selection, and walk-forward submission.

## 0.1.1 — 2026-06-19

- Selected FMP as the initial primary daily-data provider.
- Added stable FMP end-of-day OHLCV adapter with header authentication.
- Added secure `.env` loading and a hidden-input Mac configuration script.
- Added `doctor`, `fmp-check`, and provider-selectable `download` commands.
- Added mocked FMP response, authentication, date, schema, and secret-exposure tests.
- Kept yfinance isolated as an optional fallback/comparison source.
- Updated Mac setup, milestones, Codex assignment, decisions, and provider documentation.

## 0.1.0 — 2026-06-19

- Created the canonical Version 1 repository.
- Locked scope to daily swing trading and RSI self-discovery.
- Added OHLCV ingestion and validation.
- Added exact Wilder RSI, trailing price features, and isolated forward labels.
- Added next-open fixed-horizon backtesting and metrics.
- Added grid-search and expanding walk-forward scaffolding.
- Added latest-bar scanner and append-only forward signal/outcome records.
- Added deterministic synthetic demo data and automated tests.
