# Changelog

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
