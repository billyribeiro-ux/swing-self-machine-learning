# RSI Research Specification

## Objective

Discover which RSI behaviors, parameters, contexts, and confirmation stacks have stable forward swing-trading value. Do not assume any one length or level is correct.

## Baseline and crowding hypothesis

RSI(14) with 70/30 levels is retained as:

1. A reproducible control group
2. A possible crowd-attention feature
3. A benchmark that custom settings must beat out-of-sample

The idea that institutions exploit predictable retail reactions around standard settings is a research hypothesis. The engine must test measurable consequences rather than treating the causal story as proven.

## Initial search dimensions

- Length: 2 through 50
- Lower region: 5 through 60
- Upper region: 40 through 95
- Slope windows: 1, 2, 3, 5, and 10 bars
- Trigger modes:
  - Cross back above a learned lower level
  - Turn upward while still below the level
  - Reclaim after entering the region within a recent lookback
  - Failure swing
  - Bullish and bearish divergence
  - Compression followed by expansion
- Trend contexts:
  - No filter
  - Close above 50-day SMA
  - Close above 200-day SMA
  - 50-day SMA above 200-day SMA
  - Positive or negative moving-average slopes
- Participation contexts:
  - Relative volume
  - Close location inside the daily range
  - Exhaustion candle
  - Multi-day pullback
  - Failed breakdown and reclaim
- Volatility contexts:
  - ATR as a percentage of price
  - ATR percentile
  - Compression and expansion

## Outcomes

For each signal, measure:

- Next-open to 3, 5, 10, 20, and 30-day close returns
- Maximum favorable excursion
- Maximum adverse excursion
- Target hit before stop
- Signal-candle-low invalidation
- Immediate failure
- Temporal and regime stability

## Candidate ranking

Never rank by win rate alone. Minimum evidence includes:

- Number of independent trades
- Mean and median net return
- Expectancy
- Profit factor
- Max drawdown
- MFE and MAE
- Lower confidence bound on mean return
- Positive-year fraction
- Out-of-sample performance
- Walk-forward performance
- Parameter-neighborhood stability

## Multiple-testing control

Searching thousands of combinations can manufacture false discoveries. Later milestones must include false-discovery controls, deflated performance measures, stability maps, and a final untouched holdout period.

## Accuracy claim

Any claim such as 98.5% must specify exactly:

- What counts as a signal
- What counts as correct
- Entry timestamp and price
- Exit rule and horizon
- Stop and target
- Costs and slippage
- Sample size
- Tickers and date range
- In-sample, out-of-sample, walk-forward, or live-forward status

Until those definitions are fixed and reproduced, the number is a hypothesis to validate, not a model metric.
