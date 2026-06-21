# Feature Registry

`src/swing_rsi/engine/features.py` defines a declarative feature registry through `FeatureSpec`.

Every feature records:

- feature name;
- feature family;
- parameters;
- required OHLCV columns;
- lookback;
- as-of timing;
- cross-sectional requirement;
- benchmark requirement;
- feature version.

## Implemented Families

- `returns_momentum`: returns over 1, 2, 3, 5, 10, 20, 40, 63, 126, and 252 sessions, log returns, acceleration, streaks, momentum percentiles, distance from prior highs/lows.
- `trend_structure`: moving-average distances and slopes, trend persistence proxies, breakout/breakdown distance, pullback/recovery and gap behavior.
- `volatility_range`: true range, ATR, realized volatility, upside/downside volatility, range percentiles, compression/expansion, overnight and intraday range context.
- `volume_participation`: relative volume, volume z-score, dollar volume, volume trend, up/down volume proxies, OBV-like transformations, price-volume agreement.
- `candle_geometry`: body percentage, wick percentages, close position, inside/outside bars, expansion/rejection bars.
- `rsi_family`: Wilder RSI lengths 2 through 50, slope, acceleration, rolling percentile, distance from historical RSI zones.
- `technical_primitives`: ROC-like returns, stochastic location, MACD-style differences, Bollinger/Keltner normalized distance, CCI, MFI, z-scores, percentiles.
- `market_relative`: SPY/QQQ/IWM/DIA relative returns, rolling beta, rolling correlation, residual return and benchmark divergence.
- `sector_relative`: stock versus configured sector proxy return and trend relationships.
- `inverse_leveraged`: benchmark versus inverse/leveraged ETF correlation, divergence, relationship breakdown, and volume context.
- `breadth`: advance percentage, up-volume percentage, percentage above averages, rolling high/low participation, dispersion and skew.
- `relationship_graph`: rolling pair correlations, anti-correlation, beta, residual divergence, lagged correlation, relationship stability, decoupling.
- `regime`: unsupervised trend/volatility/breadth/correlation state labels.

## Latest Verified Local Feature Panel

The 2026-06-20 real local-data run produced:

- Feature rows: 89,973
- Feature columns: 534
- Enabled symbols represented: 35
- Date coverage in the feature parquet: 2006-08-03 through 2026-06-18
- Feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`

Family counts for numeric feature columns in that run:

- `rsi_family`: 294
- `relationship_graph`: 60
- `trend_structure`: 32
- `returns_momentum`: 29
- `technical_primitives`: 29
- `market_relative`: 20
- `volatility_range`: 16
- `inverse_leveraged`: 12
- `volume_participation`: 11
- `candle_geometry`: 8
- `sector_relative`: 8
- `breadth`: 6
- `regime`: 3

## Discovery Controls

The discovery runner applies missingness filtering, zero-variance filtering, near-duplicate correlation pruning, bounded feature counts, bounded mutual-information screening, chronological validation, and train-only preprocessing.

No feature family is an automatic trading rule. Tree and linear model families discover relationships from the training slice, then the selected feature set and manifest hash are stored with each model.

Feature screening is target-specific for heads with distinct prediction targets. The target-before-stop classifier starts from the complete eligible numeric feature universe, excluding `label_` columns, metadata, unsupported string/object columns, and registry-prohibited fields. Every eligible feature family is scored on training rows only before the configured feature cap is applied.

The target-before-stop screen may select market-relative, sector-relative, inverse/leveraged, breadth, relationship-graph, regime, RSI, trend, volume, volatility, candle, or technical features only when the train-only scoring and pruning order selects them naturally. There are no family quotas, and a family with no target-specific signal is allowed to have zero selected features.
