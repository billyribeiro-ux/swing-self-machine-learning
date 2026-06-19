# Model Validation Standard

## Chronological separation

Random shuffling is prohibited for time-series validation. Training observations must precede test observations.

## Walk-forward selection

For each fold:

1. Search and select parameters using the training window only.
2. Leave the configured gap between training and testing.
3. Freeze the selected rule.
4. Evaluate only on the next unseen test window.
5. Preserve every fold, including failures.

## Final holdout

Before any model is promoted, reserve a final untouched time period that was not used for feature design, parameter ranges, threshold tuning, or model selection.

## Stability requirements

Prefer broad stable parameter regions over one isolated optimum. Reports should show performance around neighboring RSI lengths and levels.

## Minimum sample

A configurable minimum trade count is mandatory. The minimum is a filter, not proof of adequacy. Confidence intervals and effective independence must also be considered.

## Regime robustness

Evaluate across:

- Bull, bear, and sideways markets
- High and low volatility
- Different sectors and liquidity profiles
- Multiple calendar periods

## Edge decay

Track rolling expectancy, hit rate, drawdown, and calibration. A model can be downgraded, paused, or retired when forward evidence deteriorates.

## Promotion states

```text
RESEARCH_ONLY
BACKTEST_CANDIDATE
OUT_OF_SAMPLE_CANDIDATE
WALK_FORWARD_CANDIDATE
FORWARD_TESTING
PAPER_APPROVED
LIVE_ELIGIBLE (future; not Version 1)
RETIRED
```
