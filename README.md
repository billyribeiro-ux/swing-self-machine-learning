# Swing RSI Self-Learner

A research-first Python project for discovering, validating, scanning, and forward-testing daily swing-trading setups centered on self-adjusting RSI behavior.

## Version 1 boundary

Version 1 deliberately includes:

- Daily stock and ETF OHLCV data
- RSI lengths and trigger zones discovered from historical data
- Trailing price, volume, trend, and volatility confirmation features
- Honest next-session entries
- Fixed-horizon backtesting
- Chronological and walk-forward validation
- Current-signal scanning
- Append-only forward-test signal and outcome records

Version 1 deliberately excludes options, gamma, implied volatility, intraday data, market internals, NLP/news attribution, live brokerage execution, deep learning, and reinforcement learning.

## Scientific rule

The engine is not allowed to call a historical result an edge merely because it has a high win rate. A candidate must have sufficient observations, positive expectancy after costs, acceptable drawdown, stability across time, out-of-sample performance, walk-forward performance, and forward-test confirmation.

`RSI(14)` with `70/30` levels remains a control group and a possible crowd-behavior feature. It is not treated as truth or as the default strategy.

## Fastest Mac setup

Open Terminal in this folder, then run:

```bash
chmod +x scripts/bootstrap_mac.sh
./scripts/bootstrap_mac.sh
source .venv/bin/activate
python -m swing_rsi.cli demo
```

The demo uses deterministic synthetic data only to prove that the plumbing works. It does **not** prove trading performance.

Expected demo outputs:

```text
data/raw/DEMO.csv
reports/demo_grid_search.csv
reports/demo_best_trades.csv
reports/demo_features_and_labels.csv
reports/demo_scanner_results.csv
```

Run tests at any time:

```bash
pytest
```

Run quality checks:

```bash
ruff check .
ruff format --check .
mypy src
```

## Download real daily data for research

After installation with the market-data extra:

```bash
python -m swing_rsi.cli download --ticker AAPL --start 2010-01-01
```

Then research it:

```bash
python -m swing_rsi.cli research \
  --input data/raw/AAPL.csv \
  --ticker AAPL \
  --holding-period 10 \
  --output reports/AAPL_grid_search.csv
```

## Canonical project records

Read these in order before changing architecture:

1. `AGENTS.md`
2. `docs/VISION.md`
3. `docs/V1_SCOPE.md`
4. `docs/ARCHITECTURE.md`
5. `docs/RSI_RESEARCH_SPEC.md`
6. `docs/BACKTESTING_STANDARD.md`
7. `docs/MODEL_VALIDATION_STANDARD.md`
8. `docs/FORWARD_TESTING_STANDARD.md`
9. `docs/DECISIONS.md`
10. `docs/OPEN_QUESTIONS.md`

## Important

This project is an experimental research system, not financial advice and not a live trading system. Real market research must account for data quality, corporate actions, delistings, survivorship bias, transaction costs, liquidity, execution assumptions, multiple testing, and regime changes.
