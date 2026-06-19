# Changelog

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
