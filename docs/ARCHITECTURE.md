# Architecture

## Dependency flow

```text
FMP / CSV / optional comparison provider
   ↓
Raw-response provenance and provider adapter
   ↓
Normalization and OHLCV validation
   ↓
Trailing feature factory
   ↓
RSI candidate rules
   ↓
Signal timestamp at daily close
   ↓
Next-session execution model
   ↓
Backtest trades and metrics
   ↓
Chronological parameter search
   ↓
Walk-forward validation
   ↓
Current scanner
   ↓
Immutable forward signal log
   ↓
Separate append-only outcome log
```

## Package layout

```text
src/swing_rsi/
  settings.py               local environment and FMP configuration
  config.py                 YAML configuration and project paths
  data/
    providers/              FMP and future provider adapters
    loader.py               provider selection and CSV loading
    validation.py           OHLCV schema and market-data invariants
    storage.py              data persistence helpers
  features/                 trailing price features, RSI, and future labels
  signals/                  explicit candidate signal definitions
  backtest/                 execution timing, trades, and metrics
  research/                 candidate grids and walk-forward selection
  scanner/                  latest-bar evidence output
  forward/                  immutable signal and outcome journals
  reports/                  atomic report writers
  application/              shared CLI/dashboard orchestration services
  sample_data.py            deterministic plumbing-only demo data
  cli.py                    user-facing commands
dashboard/                  local Streamlit presentation layer
```

## Provider boundary

FMP is the primary Version 1 daily-data source, but research logic does not call FMP directly. Provider-specific responses are normalized at the ingestion boundary. This allows later comparison with another source without rewriting RSI, labeling, backtesting, or scanning logic.

API keys are loaded from `.env`, sent through request headers, and never printed or committed.

## Data separation

Feature columns contain only current and prior information. Future outcome columns must begin with `label_`. The scanner and signal generators must never accept `label_` columns as inputs.

## Execution timing

Version 1 signals are known only after a daily bar closes. The default simulated entry is the next session open. The fixed-horizon exit for an `H`-bar hold is the close of bar `t + H`, where `t` is the signal bar. No same-close fill is allowed.

## Persistence

- Raw and derived market data live under `data/` and are ignored by Git.
- Reports live under `reports/` and are ignored by Git.
- Forward signals and outcomes are separate append-only files.
- Methodology and decisions live under `docs/` and are the permanent source of truth.

## Local dashboard boundary

The Streamlit dashboard is a local-only presentation layer. It calls reusable Python services under `src/swing_rsi/application/` and does not duplicate market-data, RSI, signal, backtest, research, or walk-forward logic inside dashboard pages.

Streamlit is temporary local presentation infrastructure. The long-term UI may later be replaced by SvelteKit over a typed FastAPI/OpenAPI boundary, but no separate API or deployment layer exists in this milestone.

## Extension path

Once Version 1 is proven, additional indicators become candidate feature modules using the same interfaces. Sector, inverse ETF, market regime, news, options, and attribution layers are added only after the base validation loop is trustworthy.
