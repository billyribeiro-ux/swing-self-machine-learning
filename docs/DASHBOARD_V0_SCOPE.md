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

## V0.2 Corrections

Dashboard V0.2 keeps the same local Streamlit boundary but corrects the first implementation so it is usable for real daily RSI research setup work.

- Navigation is controlled only by `dashboard/app.py` through explicit `st.navigation` and `st.Page` registrations.
- The sidebar exposes exactly five user-facing sections in this order: Overview, Data and Audit, RSI Explorer, Research and Backtest, Walk-Forward Validation.
- Streamlit auto-discovered `dashboard/pages/*.py` page files are no longer used.
- Page renderers live under `dashboard/sections/`; shared presentation helpers live under `dashboard/ui/`.
- Dataset selectors display ticker symbols, not filenames.
- Provider symbols are normalized by `swing_rsi.application.datasets.normalize_ticker`.
- `AAPL.csv` is accepted as user input and normalized to `AAPL`; path-like or traversal input is rejected.
- Data and Audit separates selected research-window calculations from full raw-file calculations.
- Every selected-window table and metric is computed from the sliced dataframe only.
- The full raw-file tab keeps complete raw coverage visible without implying it is the selected research window.
- Local CSV reads may be cached only by file path and modification time. API keys, FMP requests, writes, research runs, and walk-forward runs are not cached.
- Expected dashboard errors are shown as concise user-facing messages. Unexpected dashboard errors are logged locally under ignored `logs/`.
- The local Streamlit toolbar is configured in minimal mode by `scripts/run_dashboard.sh`.

## V0.2 Requirement Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Exactly five named sections in required order | COMPLETE | `dashboard/ui/navigation.py`, `tests/test_dashboard_imports.py` |
| No filename-derived `app` or lowercase page labels | COMPLETE | Explicit `st.Page` registry and removed `dashboard/pages/*.py` source files |
| Ticker normalization strips one `.csv` suffix | COMPLETE | `normalize_ticker`, `tests/test_application_services.py` |
| Ticker normalization rejects path/traversal values | COMPLETE | `normalize_ticker`, `tests/test_application_services.py` |
| Safe dataset updates preserve existing history | COMPLETE | `download_daily_to_raw`, merge/update tests |
| Atomic dataset write after validation | COMPLETE | `download_daily_to_raw` validates before `atomic_write_csv` |
| Selected-window audit excludes older raw rows | COMPLETE | `structural_audit_frame`, selected-window tests |
| Full raw-file audit remains available | COMPLETE | Data and Audit full raw-file tab and raw audit tests |
| Date/return/volume display formatting | COMPLETE | `dashboard/ui/formatting.py`, formatting tests |
| Deterministic local CSV read caching only | COMPLETE | `dashboard/ui/cache.py`, cache-key invalidation test |
| Dashboard imports/startup make no FMP calls | COMPLETE | dashboard import and AppTest startup tests |
| RSI Explorer interaction with DEMO data | COMPLETE | `tests/test_dashboard_interactions.py` |
| Quick Research submission and candidate selection | COMPLETE | `tests/test_dashboard_interactions.py` |
| Walk-forward submission with DEMO data | COMPLETE | `tests/test_dashboard_interactions.py` |
| Future test-window mutation does not change prior training selection | COMPLETE | `tests/test_walk_forward.py` |
| Incomplete training trades cannot use test-period prices | COMPLETE | `tests/test_walk_forward.py` |
| Corporate-action and historical-universe warnings | COMPLETE | `dashboard/ui/components.py` |
| Exchange-calendar completeness claims | INTENTIONALLY DEFERRED | No exchange-calendar dependency is in V0 scope |

## Required Warnings

Every page displays:

```text
Experimental research system. Results are not financial advice and are not evidence of a live trading edge.
```

and:

```text
FMP corporate-action and historical-universe semantics have not yet been fully audited.
```
