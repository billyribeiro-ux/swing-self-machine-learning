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

The dashboard is local research tooling only. It is not a production trading application.

7. Download the first real dataset:

```bash
python -m swing_rsi.cli download --provider fmp --ticker AAPL --start 2020-01-01
```

Do not begin tuning RSI from real data until the FMP ingestion audit milestone is complete.

## Codex

When opening the project in Codex, open the entire `swing-rsi-self-learner` folder. The exact first assignment is saved in `docs/CODEX_FIRST_PROMPT.md`.
