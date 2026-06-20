# Market Attribution

`src/swing_rsi/engine/attribution.py` produces evidence-based, probabilistic attribution for scanner candidates.

Attribution is not causal proof. It is a model-contribution and supporting-evidence summary from the data currently available.

## Implemented Outputs

For each candidate:

- model contribution share grouped by feature family;
- supporting feature evidence from the current feature snapshot;
- relationship confirmations;
- relationship divergences;
- nearest historical analogs from train-fitted feature scaling;
- residual/unexplained component.

## Contribution Groups

Feature names are mapped to groups such as:

- stock price structure;
- volume participation;
- broad market;
- sector;
- breadth;
- inverse/leveraged ETF relationships;
- volatility/range;
- regime;
- cross-instrument relationships;
- RSI family;
- residual/unexplained.

The local contribution method perturbs selected features back to their training medians and measures the change in the model probability. Contributions are normalized into shares for display.

## Evidence Rules

Supporting evidence must come from actual feature values in the row being scanned. The engine does not invent news, intent, institutional behavior, or unsupported causes.

Historical analogs exclude future information by using the model's stored training feature matrix and training labels.
