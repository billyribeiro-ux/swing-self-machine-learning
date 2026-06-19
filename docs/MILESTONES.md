# Milestones

## M0 — Repository bootstrap

- Canonical documentation
- Modern Python package layout
- Data validation
- Exact Wilder RSI
- Starter price features and labels
- Fixed-horizon backtester
- Grid search
- Walk-forward scaffold
- Scanner scaffold
- Append-only forward records
- Deterministic demo and tests
- FMP adapter, secure local configuration, and connection checker

## M1 — FMP real-data ingestion audit

- Confirm subscription history range and endpoint access
- Preserve raw provider responses or reproducible snapshots
- Generate per-symbol data-quality reports
- Test split and dividend consistency
- Compare adjusted and unadjusted semantics
- Detect missing sessions, duplicates, stale rows, and impossible OHLCV
- Audit SPY, QQQ, and the initial ten-symbol universe
- Establish provider-neutral raw and processed caches
- Document whether a second provider is required for delisted names and point-in-time universes

## M2 — RSI baseline research

- Reproduce RSI(14), 70/30 control
- Exhaustive length and lower-region maps
- Long and reversal definitions
- Parameter-neighborhood stability plots

## M3 — Honest execution and outcome engine

- Stops, targets, time exits, and 2R-before-1R labels
- Transaction-cost scenarios
- Trade overlap and capital rules

## M4 — Walk-forward research

- Expanding and rolling folds
- Gap and purging policy
- Final untouched holdout
- Multiple-testing controls

## M5 — Current scanner

- Multi-symbol scan
- Evidence cards
- Model registry and versioning
- CSV and machine-readable output

## M6 — Forward testing

- Scheduled signal logging
- Outcome maturation
- Calibration and edge-decay dashboard
- Promotion and retirement policy
