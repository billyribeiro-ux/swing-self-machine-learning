# Version 1 Scope

## Mission

Build one elite daily swing-trading self-learning scanner first.

The engine will use historical daily price and volume data to discover RSI behavior and confirmation rules, backtest them with honest timing, validate them chronologically and walk-forward, scan current bars, and preserve all forward signals before outcomes are known.

## Included

- Daily OHLCV for stocks and ETFs
- Corporate-action-aware data handling policy
- RSI lengths from 2 through 50
- Learned lower and upper regions
- RSI slope, crosses, reclaims, turns, compression, divergence, and failure-swing research over time
- Price trend, moving-average, volatility, candle, pullback, gap, and relative-volume confirmations
- SPY and QQQ regime features in a later Version 1 milestone
- 3, 5, 10, 20, and 30 trading-day outcomes
- Next-session-open default entry
- Fixed-horizon exits first
- Transaction-cost assumptions
- Non-overlapping trades per ticker
- Baseline comparison with RSI(14), 70/30, and simple benchmarks
- Grid search first, Optuna later
- Out-of-sample and expanding walk-forward validation
- Scanner output with evidence and sample size
- Append-only forward signal and outcome records

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

1. Daily data ingests and validates correctly.
2. Features use only information known by signal time.
3. Labels are isolated and future-looking by explicit design.
4. Signals occur at the close and default entries occur no earlier than the next open.
5. Backtests model costs and overlapping positions honestly.
6. Candidate settings are compared using more than win rate.
7. Walk-forward validation selects parameters only from prior data.
8. Current scanner output identifies the exact model and evidence.
9. Forward records are written before outcomes and never rewritten.
10. Reports expose failures, instability, and insufficient samples.
