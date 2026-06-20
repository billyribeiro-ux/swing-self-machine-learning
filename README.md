# Self-Learning Swing Trading Engine

A research-first Python project for autonomous daily swing-market discovery, attribution, scanner output, portfolio backtesting, and append-only paper forward testing.

## Version 1 boundary

Version 1 includes:

- Daily stock and ETF OHLCV data
- FMP as the primary initial data provider
- A configurable stock, broad ETF, sector ETF, inverse ETF, and leveraged ETF universe
- Declarative feature families for price, volume, trend, volatility, candle geometry, RSI, market-relative, sector-relative, inverse/leveraged ETF, breadth, relationship, and regime behavior
- Multi-horizon bullish and bearish swing labels
- Chronological model discovery with purging, calibration, quality gates, model registry, and immutable artifacts
- Live scanner snapshots with probabilistic market attribution and historical analogs
- Portfolio-level backtesting of scanner outputs
- Honest next-session entries
- Append-only paper-forward signal and pending-entry records
- Legacy RSI research and historical walk-forward tools under Baselines and Legacy RSI

Version 1 excludes options, gamma, implied volatility, intraday data, market internals, NLP/news attribution, live brokerage execution, deep learning, and reinforcement learning.

## Scientific rule

The engine is not allowed to call a historical result an edge merely because it has a high win rate. A candidate must have sufficient observations, positive expectancy after costs, acceptable drawdown, stability across time, out-of-sample performance, walk-forward performance, and forward-test confirmation.

`RSI(14)` with `70/30` levels remains a control group and a possible crowd-behavior feature. RSI is now one feature family among many, not the scanner strategy.

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

Open the local engine dashboard:

```bash
./scripts/run_dashboard.sh
```

The dashboard is a temporary local Streamlit presentation layer over the typed Python engine modules. It is not a production trading application.

Dashboard sections:

1. Overview
2. Data and Universe
3. Discovery Lab
4. Live Scanner
5. Candidate Attribution
6. Portfolio Backtests
7. Paper Forward Test
8. Model Registry
9. Baselines and Legacy RSI

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

## Run the autonomous scanner vertical slice

```bash
python -m swing_rsi.cli universe-update --start 2016-06-20
python -m swing_rsi.cli build-features
python -m swing_rsi.cli discover-models
python -m swing_rsi.cli scan --include-challengers
python -m swing_rsi.cli forward-update
```

Use `--include-challengers` only for inspection when no champion has passed promotion gates yet. Discovery never silently promotes a model.

Run the idempotent daily cycle:

```bash
./scripts/run_daily_cycle.sh --include-challengers
```

## Run legacy RSI research

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
12. `docs/AUTONOMOUS_DISCOVERY_ENGINE.md`
13. `docs/FEATURE_REGISTRY.md`
14. `docs/SCANNER_SPEC.md`
15. `docs/PAPER_FORWARD_TESTER.md`
16. `docs/DECISIONS.md`
17. `docs/OPEN_QUESTIONS.md`

This is an experimental research system, not financial advice and not a live trading system.
