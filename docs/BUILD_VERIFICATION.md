# Build Verification

Verified on 2026-06-19 before delivery.

## Quality checks

```text
Ruff lint: passed
Ruff formatting: passed
Mypy strict type checking: passed across 30 source files
Pytest: 18 tests passed
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
- FMP header authentication without putting the key in query parameters
- Current FMP list responses and legacy historical wrappers
- FMP field normalization including `adjClose`
- FMP error messages do not expose the configured key
- Invalid FMP date ranges are rejected before a request
- Local `.env` loading and missing-key behavior

## End-to-end demo

The deterministic synthetic demo successfully:

- Generated 1,200 daily OHLCV rows
- Evaluated 432 RSI candidate rules
- Selected a candidate using the configured research score
- Produced non-overlapping next-open trades
- Generated future outcome labels
- Produced scanner output files

Synthetic results validate software plumbing only. They are not evidence of market performance.

## FMP verification

The adapter is fully covered with deterministic mocked HTTP tests. A live connection check is available through:

```bash
python -m swing_rsi.cli fmp-check
```

Live access is tested after the user's local `.env` is configured because the key is not embedded in the repository.
