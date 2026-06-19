# Open Questions

1. What exact event, horizon, entry, exit, stop, target, and sample define the reported 98.5% accuracy?
2. Is the primary Version 1 target reversal, continuation after pullback, or separate models for each?
3. Should optimization be ticker-specific, sector-specific, regime-specific, universal, or hierarchical?
4. What is the minimum acceptable number of independent trades?
5. Does FMP provide split/dividend-consistent OHLCV for every symbol and historical period we intend to test?
6. Does the current FMP subscription expose enough daily history for the required training, validation, holdout, and regime windows?
7. Can FMP supply delisted securities and point-in-time universe membership well enough to control survivorship bias, or will a second source be required?
8. Should adjusted OHLC or raw OHLC plus explicit corporate actions be canonical?
9. What liquidity thresholds define the eligible universe?
10. How should signal clustering across highly correlated stocks be treated?
11. Which exact transaction-cost and slippage model is appropriate for daily swing entries?
12. What final untouched date range will be reserved before forward testing?
13. Which SPY, QQQ, sector ETF, leveraged ETF, and inverse ETF relationships enter Version 1.5?
14. What criteria promote a model from research to forward testing and later paper approval?
