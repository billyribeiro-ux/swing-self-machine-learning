# Vision

## Self-Learning Market Attribution System

The long-term project is a self-learning market attribution system for scalping, day trading, swing trading, and long-term portfolio investing. Its purpose is not merely to predict direction. It should investigate why an instrument moved, which forces preceded and sustained the move, what invalidates the explanation, and what historically happened next under similar conditions.

The ultimate engine should study relationships across price, volume, stocks, ETFs, inverse and leveraged ETFs, sectors, volatility, market internals, macro assets, catalysts, options, positioning, liquidity, and fundamentals. It should timestamp the sequence, generate competing hypotheses, assign weighted attribution, track outcomes, and retire decaying explanations.

Core principle:

> Do not teach the system what to think. Teach it how to investigate.

Indicators are candidate features, not authorities. Popular defaults can also be studied as crowd-behavior markers. Sequence matters. Attribution should be weighted rather than forced into one binary cause. Backtesting alone is insufficient; forward testing is mandatory.

## One intelligence core, multiple future heads

- Scalping: seconds to minutes
- Day trading: intraday
- Swing trading: days to weeks
- Portfolio investing: months to years

Each future head will use different labels, holding periods, execution assumptions, and risk controls while sharing the attribution and discovery architecture.

## Current deliberate reduction

The current implementation is still deliberately daily-only, but it now implements a broader self-learning swing scanner vertical slice. RSI remains available as a baseline feature family, while the engine studies price, volume, market, sector, breadth, inverse/leveraged ETF, relationship, volatility, and regime behavior.

The system produces probabilistic attribution from measured features and reports residual/unexplained influence instead of inventing causes.

See `docs/V1_SCOPE.md` for the binding current boundary.
