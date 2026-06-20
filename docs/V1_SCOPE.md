# Version 1 Scope

## Mission

Build one elite daily swing-trading self-learning scanner first.

The engine uses historical daily price and volume data to discover measurable relationships behind bullish and bearish swing outcomes, backtest scanner outputs with honest timing, register frozen model versions, scan current bars, and preserve paper-forward signals before outcomes are known.

## Included

- Daily OHLCV for stocks and ETFs, with FMP as the primary Version 1 provider
- Secure local secret handling through a Git-ignored `.env` file
- Corporate-action-aware data handling policy
- Configurable stock, broad ETF, sector ETF, inverse ETF, and leveraged ETF universe
- RSI lengths from 2 through 50 as one feature family and baseline, not as the strategy
- Price trend, moving-average, volatility, candle, pullback, gap, relative-volume, breadth, market-relative, sector-relative, inverse/leveraged ETF, relationship, and regime features
- 3, 5, 10, 20, and 40 trading-day outcomes
- Next-session-open default entry
- Fixed-horizon exits first
- Transaction-cost assumptions
- Non-overlapping trades per ticker
- Baseline comparison with RSI(14), 70/30, and simple benchmarks
- Grid search first, Optuna later
- Chronological train, calibration, and holdout validation with purged label horizons
- Historical walk-forward validation retained as legacy research tooling
- Scanner output with attribution, candidate status, model ID, and feature snapshot hash
- Append-only paper-forward signal and pending-entry records

## Excluded

- Options chains, Greeks, IV, skew, gamma, open interest, dealer hedging
- Intraday bars or market internals
- News and NLP
- Live order execution or brokerage integration
- Deep learning
- Reinforcement learning
- Portfolio construction
- Claims that historical accuracy guarantees live performance

## Version 1 done criteria

Version 1 is done only when the complete loop works:

1. FMP daily data ingests, preserves provenance, and validates correctly.
2. Features use only information known by signal time.
3. Labels are isolated and future-looking by explicit design.
4. Signals occur at the close and default entries occur no earlier than the next open.
5. Backtests model costs and overlapping positions honestly.
6. Candidate settings are compared using more than win rate.
7. Walk-forward validation selects parameters only from prior data.
8. Current scanner output identifies the exact model, feature snapshot, attribution, and evidence.
9. Paper-forward records are written before outcomes and never rewritten.
10. Reports expose failures, instability, and insufficient samples.
