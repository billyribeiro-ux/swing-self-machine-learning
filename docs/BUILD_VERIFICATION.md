# Build Verification

Verified on 2026-06-19 before delivery.

## Quality checks

```text
Ruff lint: passed
Ruff formatting: passed
Mypy strict type checking: passed across 27 source files
Pytest: 12 tests passed
```

## Behaviors covered by tests

- Exact Wilder RSI behavior for rising, falling, and constant series
- OHLCV validation and chronological sorting
- Invalid high/low rejection
- Trailing features remain unchanged when later bars are modified
- Future labels are explicitly separated and incomplete future windows remain empty
- Label columns are rejected from feature sets
- Signal-at-close and next-session-open entry timing
- One open trade per ticker and overlap prevention
- Expanding walk-forward folds are chronological and gapped
- Forward signals and outcomes are separate append-only records

## End-to-end demo

The deterministic synthetic demo successfully:

- Generated 1,200 daily OHLCV rows
- Evaluated 432 RSI candidate rules
- Selected a candidate using the configured research score
- Produced non-overlapping next-open trades
- Generated future outcome labels
- Produced scanner output files

Synthetic results were used only to verify software plumbing. They are not evidence of market performance.
