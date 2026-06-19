# Local Research Dashboard V0.1

## Purpose

The first dashboard is a local Streamlit interface for inspecting the Version 1 daily RSI research loop. It is a thin presentation layer over the typed Python modules in `src/swing_rsi/`.

The dashboard is not a production trading application, not financial advice, and not evidence of a live trading edge.

## Included

- Project and FMP configuration status without showing secrets.
- Raw CSV discovery under `data/raw/`.
- FMP daily-data download through the existing provider abstraction.
- Structural raw-file audit without exchange-calendar completeness claims.
- RSI exploration using the existing Wilder RSI and signal modules.
- In-sample grid-search research and same-window RSI(14)/30 control comparison.
- Candidate trade ledgers, equity curves, drawdowns, yearly returns, MFE, and MAE displays.
- Expanding walk-forward validation with training and unseen test results kept separate.
- Test-only walk-forward aggregation.

## Excluded

- Svelte, React, Next.js, FastAPI, Node.js, a separate API, database, auth, or deployment.
- Scanner execution and forward-journal editing.
- Options, NLP, intraday data, brokerage connectivity, or live trading.
- Claims that in-sample or walk-forward results are proven live edges.

## Launch

```bash
./scripts/run_dashboard.sh
```

The script uses `.venv/bin/streamlit` directly. If Streamlit is missing, run:

```bash
.venv/bin/python -m pip install -e ".[all,dev,dashboard]"
```

## Temporary UI Decision

Streamlit is temporary local presentation infrastructure. The long-term commercial UI may later be replaced by SvelteKit over a typed FastAPI/OpenAPI boundary, but that is outside the current Version 1 dashboard milestone.

## Required Warnings

Every page displays:

```text
Experimental research system. Results are not financial advice and are not evidence of a live trading edge.
```

and:

```text
FMP corporate-action and historical-universe semantics have not yet been fully audited.
```

