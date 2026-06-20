# Swing RSI Self-Learner

A research-first Python project for discovering, validating, scanning, and forward-testing daily swing-trading setups centered on self-adjusting RSI behavior.

## Version 1 boundary

Version 1 includes:

- Daily stock and ETF OHLCV data
- FMP as the primary initial data provider
- RSI lengths and trigger regions discovered from historical data
- Trailing price, volume, trend, and volatility confirmation features
- Honest next-session entries
- Fixed-horizon backtesting
- Chronological and walk-forward validation
- Current-signal scanning
- Append-only forward-test signal and outcome records

Version 1 excludes options, gamma, implied volatility, intraday data, market internals, NLP/news attribution, live brokerage execution, deep learning, and reinforcement learning.

## Scientific rule

The engine is not allowed to call a historical result an edge merely because it has a high win rate. A candidate must have sufficient observations, positive expectancy after costs, acceptable drawdown, stability across time, out-of-sample performance, walk-forward performance, and forward-test confirmation.

`RSI(14)` with `70/30` levels remains a control group and a possible crowd-behavior feature. It is not treated as truth or as the default strategy.

## First Mac setup

Open Terminal in this folder and run:

```bash
chmod +x scripts/bootstrap_mac.sh scripts/configure_fmp.sh
./scripts/bootstrap_mac.sh
./scripts/configure_fmp.sh
```

The second script asks for the FMP key without displaying it, writes it only to a local `.env` file, and tests a small AAPL daily-data request. `.env` is excluded from Git.

Activate the project when returning later:

```bash
source .venv/bin/activate
```

Run the deterministic plumbing demo:

```bash
python -m swing_rsi.cli demo
```

Synthetic data proves that the software runs. It does **not** prove trading performance.

Open the local research dashboard:

```bash
./scripts/run_dashboard.sh
```

The dashboard is a temporary local Streamlit presentation layer over the typed Python research modules. It is not a production trading application. The long-term UI may later be replaced by SvelteKit over a typed FastAPI/OpenAPI boundary.

Dashboard sections:

1. Overview
2. Data and Audit
3. RSI Explorer
4. Research and Backtest
5. Walk-Forward Validation

Dataset updates in the dashboard are merge-safe: existing ticker history is preserved, overlapping dates are replaced by newly downloaded values, duplicates are removed, the merged OHLCV data is validated, and the CSV is written atomically. The dashboard displays ticker symbols such as `AAPL`, not filenames such as `AAPL.csv`, as provider symbols.

## Download real daily data from FMP

```bash
python -m swing_rsi.cli download \
  --provider fmp \
  --ticker AAPL \
  --start 2020-01-01
```

The file is saved to:

```text
data/raw/AAPL.csv
```

The available historical range depends on the user's FMP subscription. FMP data remains subject to corporate-action, missing-session, delisting, and survivorship-bias audits before research results are trusted.

## Run starter RSI research

```bash
python -m swing_rsi.cli research \
  --input data/raw/AAPL.csv \
  --ticker AAPL \
  --holding-period 10 \
  --output reports/AAPL_grid_search.csv
```

## Checks

```bash
pytest
ruff check .
ruff format --check .
mypy src
```

## Canonical project records

Read these before changing architecture:

1. `AGENTS.md`
2. `docs/VISION.md`
3. `docs/V1_SCOPE.md`
4. `docs/ARCHITECTURE.md`
5. `docs/FMP_SETUP.md`
6. `docs/FMP_DATA_SOURCE.md`
7. `docs/RSI_RESEARCH_SPEC.md`
8. `docs/BACKTESTING_STANDARD.md`
9. `docs/MODEL_VALIDATION_STANDARD.md`
10. `docs/FORWARD_TESTING_STANDARD.md`
11. `docs/DECISIONS.md`
12. `docs/OPEN_QUESTIONS.md`

This is an experimental research system, not financial advice and not a live trading system.
