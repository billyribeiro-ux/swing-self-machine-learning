# Start Here

The Version 1 repository is already created and tested.

## Do these actions in order on your Mac

1. Download and unzip `swing-rsi-self-learner.zip`.
2. Move the folder to `Documents/Trading-Projects/`.
3. Open Terminal inside the folder.
4. Run:

```bash
chmod +x scripts/bootstrap_mac.sh scripts/configure_fmp.sh
./scripts/bootstrap_mac.sh
./scripts/configure_fmp.sh
```

5. Run the demo:

```bash
source .venv/bin/activate
python -m swing_rsi.cli demo
```

6. Open the local research dashboard:

```bash
./scripts/run_dashboard.sh
```

The dashboard is local research tooling only. It is not a production trading application. It opens the Self-Learning Swing Trading Engine sections: Overview, Data and Universe, Discovery Lab, Live Scanner, Candidate Attribution, Portfolio Backtests, Paper Forward Test, Model Registry, and Baselines and Legacy RSI.

In Data and Audit, ticker fields display provider symbols such as `AAPL`, not filenames such as `AAPL.csv`. Update Existing Dataset preserves older stored history and merges new FMP rows by date.

7. Run the autonomous scanner vertical slice after configuring FMP:

```bash
python -m swing_rsi.cli universe-update --start 2016-06-20
python -m swing_rsi.cli build-features
python -m swing_rsi.cli discover-models
python -m swing_rsi.cli scan --include-challengers
python -m swing_rsi.cli forward-update
```

If no model passes quality gates, inspect retained candidates. Do not weaken gates just to force a champion.

8. Download a single legacy RSI dataset when needed:

```bash
python -m swing_rsi.cli download --provider fmp --ticker AAPL --start 2020-01-01
```

RSI is now a baseline feature family and legacy research area, not the autonomous scanner strategy.

## Codex

When opening the project in Codex, open the entire `swing-rsi-self-learner` folder. The exact first assignment is saved in `docs/CODEX_FIRST_PROMPT.md`.
