# Backtesting Standard

## Timing

- Daily signal is computed after the signal bar closes.
- Default entry is the next session open.
- Same-close entries are prohibited unless a separate pre-close signal design is created and timestamped.
- Fixed-horizon exit for holding period `H` uses the close at signal index `t + H`.

## Costs

Every report must state round-trip transaction cost and slippage assumptions. Zero-cost reports may be produced only as diagnostics and must be labeled as such.

## Overlap

The starter engine permits only one open trade per ticker. Signals occurring while a trade is open are ignored. Portfolio-level capital and cross-ticker overlap are future work.

## Price adjustments

Research must decide explicitly between raw OHLC with corporate-action events and consistently adjusted OHLC. Mixing adjusted close with raw open/high/low is prohibited because it can distort returns and stops.

## Required trade fields

- Signal date
- Entry date and price
- Exit date and price
- Holding period
- Gross return
- Net return
- MFE
- MAE
- Rule identifier

## Required metrics

- Trade count
- Win rate
- Average and median net return
- Standard deviation
- Expectancy
- Profit factor
- Maximum drawdown of the sequential trade equity curve
- Average MFE and MAE
- Positive-year fraction
- Lower confidence bound on mean return

## Bias controls

The production research universe must eventually address:

- Survivorship bias
- Delisted securities
- Corporate actions
- Data revisions
- Look-ahead bias
- Universe-selection bias
- Multiple testing
- Liquidity and fill feasibility
- Regime concentration

## Benchmark comparisons

Each candidate must be compared with:

- RSI(14) control logic
- Buy-and-hold over comparable periods
- A simple price-only baseline
- The same rule before and after estimated costs
