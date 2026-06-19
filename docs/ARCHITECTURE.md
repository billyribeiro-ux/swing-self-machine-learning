# Architecture

## Dependency flow

```text
Raw OHLCV
   ↓
Normalization and validation
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
  config.py                 YAML configuration and project paths
  data/                     ingestion, validation, and storage
  features/                 trailing price features, RSI, and future labels
  signals/                  explicit candidate signal definitions
  backtest/                 execution timing, trades, and metrics
  research/                 candidate grids and walk-forward selection
  scanner/                  latest-bar evidence output
  forward/                  immutable signal and outcome journals
  reports/                  atomic report writers
  sample_data.py            deterministic plumbing-only demo data
  cli.py                    user-facing commands
```

## Data separation

Feature columns contain only current and prior information. Future outcome columns must begin with `label_`. The scanner and signal generators must never accept `label_` columns as inputs.

## Execution timing

Version 1 signals are known only after a daily bar closes. The default simulated entry is the next session open. The fixed-horizon exit for an `H`-bar hold is the close of bar `t + H`, where `t` is the signal bar. No same-close fill is allowed.

## Persistence

- Raw and derived market data live under `data/` and are ignored by Git.
- Reports live under `reports/` and are ignored by Git.
- Forward signals and outcomes are separate append-only files.
- Methodology and decisions live under `docs/` and are the permanent source of truth.

## Extension path

Once Version 1 is proven, additional indicators become candidate feature modules using the same interfaces. Sector, inverse ETF, market regime, news, options, and attribution layers are added only after the base validation loop is trustworthy.
