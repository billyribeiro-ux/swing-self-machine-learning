# Getting Started on Mac

Follow these steps exactly.

## 1. Download and unzip

Download `swing-rsi-self-learner.zip`. Double-click the ZIP in Finder.

## 2. Move the folder

Create this folder if it does not exist:

```text
Documents/Trading-Projects
```

Move the unzipped `swing-rsi-self-learner` folder inside it.

## 3. Open Terminal in the project folder

In Finder, open `swing-rsi-self-learner`. Right-click the folder background and select **New Terminal at Folder** when available.

Another method:

1. Open Terminal.
2. Type `cd ` with one trailing space.
3. Drag the project folder from Finder into Terminal.
4. Press Return.

## 4. Install the project

Paste this entire block and press Return:

```bash
chmod +x scripts/bootstrap_mac.sh scripts/configure_fmp.sh
./scripts/bootstrap_mac.sh
```

The setup creates an isolated `.venv`, installs dependencies, and runs the tests.

## 5. Configure FMP

Run:

```bash
./scripts/configure_fmp.sh
```

The script asks for the FMP key. The characters will not appear while pasting. Press Return after pasting it.

The script stores the key only in `.env`, makes that file readable only by your Mac user, confirms that the key is configured, and performs a small FMP test request. The key value is never printed.

## 6. Run the demo

```bash
source .venv/bin/activate
python -m swing_rsi.cli demo
```

The demo uses synthetic data only to verify the pipeline.

## 7. Download AAPL daily data

```bash
python -m swing_rsi.cli download --provider fmp --ticker AAPL --start 2020-01-01
```

The expected file is:

```text
data/raw/AAPL.csv
```

## 8. Return to the project later

Open Terminal in the folder and run:

```bash
source .venv/bin/activate
```

When finished:

```bash
deactivate
```

## 9. Open in Codex

Open the entire repository folder, not one Python file. Codex must read `AGENTS.md` first.
