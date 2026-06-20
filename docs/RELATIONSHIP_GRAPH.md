# Relationship Graph

Relationship features are built from configured universe instruments without hardcoding one strategy.

The seed universe includes broad-market ETFs, sector ETFs, inverse ETFs, and leveraged ETFs. These are seeds, not assumptions of fixed causal structure.

## Implemented Measurements

- Rolling benchmark correlations against SPY, QQQ, IWM, and DIA.
- Rolling beta against broad-market benchmarks.
- Residual one-session return after benchmark movement.
- Pairwise rolling correlations for filtered universe pairs.
- Anti-correlation stability through negative rolling correlation values.
- Five-session relationship divergence for inverse and leveraged ETF pairs.
- Lead-lag correlation probes over bounded lags.
- Nearest related instruments from the latest rolling correlation matrix.

## Timing

Relationship values are trailing and use same-date or prior data only. Future rows cannot change prior relationship features; this is covered by regression tests that mutate future prices and compare prior features.

## Interpretation

Relationship evidence is reported as `Relationship confirmation` or `Relationship divergence`. It is not reported as proof of causality. If the model cannot explain enough of a candidate from measured features, the attribution engine reports a residual/unexplained component.
