# Dashboard V0.2 Handoff

Date: 2026-06-19  
Repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`  
Branch: `feat/local-research-dashboard`  
Code checkpoint commit: `75d1ca8cf51e643bbba0117d1a0e1cb5dd4bd24a`  
Commit message: `fix: complete dashboard UX and data-audit correctness`  
Push status: not pushed by Codex.

Git status note: the working tree was clean immediately after commit `75d1ca8cf51e643bbba0117d1a0e1cb5dd4bd24a`. This handoff file is generated after that commit so it can record the commit hash. Current status after writing this report is dirty only because `docs/CODEX_DASHBOARD_V0_2_HANDOFF.md` is an untracked post-commit handoff file.

## Observed Defects And Root Causes

1. Broken navigation
   - Observed: the Streamlit sidebar showed filename-derived entries such as `app`, `data audit`, `research backtest`, `rsi explorer`, and `walk forward`.
   - Root cause: `dashboard/app.py` rendered Overview directly, while active page files under `dashboard/pages/` were still auto-discovered by Streamlit.
   - Fix: `dashboard/app.py` now owns explicit `st.navigation` / `st.Page` registration. Active page renderers live under `dashboard/sections/`. Auto-discovered `dashboard/pages/*.py` source files were removed.

2. Filename displayed and accepted as ticker
   - Observed: Data and Audit could display `AAPL.csv` in ticker-facing controls.
   - Root cause: dashboard selector labels included `dataset.path.name`, and `download_daily_to_raw` normalized tickers with only `strip().upper()`.
   - Fix: `normalize_ticker` in `src/swing_rsi/application/datasets.py` trims, uppercases, strips one trailing `.csv`, preserves periods/hyphens, and rejects path/traversal/unsupported input. Dataset selectors now display ticker symbols only.

3. Selected-window audit showed full raw-file data
   - Observed: a 10-year selected research window still showed 2006/2008 rows and moves.
   - Root cause: `dashboard/pages/data_audit.py` used `structural_audit_csv(selected.path)` for all audit tables, then displayed raw-file audit objects under selected-window labels.
   - Fix: `structural_audit_frame(frame)` was added. The Data and Audit page now renders separate `Selected Research Window` and `Full Raw File` tabs with independent audit objects.

4. Unformatted display
   - Observed: dates showed timestamp-like values, returns showed raw decimals, volumes were hard to read, and raw column names appeared in tables.
   - Root cause: dashboard pages displayed pandas dataframes directly.
   - Fix: `dashboard/ui/formatting.py` now formats date labels, prices, percentages, volumes, and human-readable column names for display copies only.

5. Ambiguous download/update behavior
   - Observed: the UI had one ambiguous `Download/update` action.
   - Root cause: update-existing and custom-download workflows were collapsed into one form.
   - Fix: Data and Audit now has `Update Existing Dataset` and `Download New or Custom Range` workflows. Both call the same merge-safe storage service.

6. Partial expected-error handling
   - Observed: expected and unexpected dashboard failures were not consistently separated.
   - Fix: `dashboard/ui/errors.py` adds concise expected-error messages and local ignored logging for unexpected errors.

## Exact Fixes

- `dashboard/app.py`
  - Uses explicit `st.navigation(streamlit_pages(st), position="sidebar")`.
  - Does not render Overview directly.

- `dashboard/ui/navigation.py`
  - Defines the five sections, titles, URL paths, and callable renderers.
  - Required order:
    1. Overview
    2. Data and Audit
    3. RSI Explorer
    4. Research and Backtest
    5. Walk-Forward Validation

- `dashboard/sections/`
  - Contains active page renderers:
    - `overview.py`
    - `data_audit.py`
    - `rsi_explorer.py`
    - `research_backtest.py`
    - `walk_forward.py`

- `dashboard/pages/`
  - No active `.py` source pages remain.

- `src/swing_rsi/application/datasets.py`
  - Adds `normalize_ticker`.
  - Adds `structural_audit_frame`.
  - Adds `dataset_cache_key`.
  - Applies `normalize_ticker` before FMP/provider storage calls.

- `dashboard/ui/cache.py`
  - Adds mtime-keyed Streamlit cache for deterministic local CSV reads only.
  - Returns `.copy()` so page code cannot mutate cached data globally.
  - Cache is cleared after successful dataset updates.

- `src/swing_rsi/application/validation_service.py`
  - Adds `validate_walk_forward_configuration`.
  - The UI calls it before expensive walk-forward execution.

## Final Navigation Architecture

Navigation is explicit and centralized:

- Registry: `dashboard/ui/navigation.py`
- Entrypoint: `dashboard/app.py`
- Renderers: `dashboard/sections/*.py`
- Tests: `tests/test_dashboard_imports.py`

No page title is derived from a filename. The `app` label is not registered.

## Dataset Update Behavior

Previous behavior before Dashboard V0.2 correction:

- The underlying hardening service already merged downloaded data, but the UI still presented one ambiguous `Download/update` workflow.
- Ticker normalization was incomplete: `AAPL.csv` could become `AAPL.CSV`.
- Dataset labels included filenames, which made ticker controls confusing.

Current behavior:

- Update Existing Dataset:
  - User chooses an existing ticker symbol.
  - UI displays current first date, latest date, row count, and stale-day indicator.
  - Default request start is 14 calendar days before the latest stored date.
  - Downloaded rows are merged into existing history.
  - Existing dates outside the request are preserved.
  - Overlapping dates are replaced by newly downloaded values.
  - Inserted dates are added.
  - Duplicate dates are rejected by validation and do not remain.
  - The merged OHLCV frame is validated.
  - The final CSV is written atomically through `atomic_write_csv`.

- Download New or Custom Range:
  - User enters a symbol.
  - `normalize_ticker` converts valid filename-like input such as `AAPL.csv` to `AAPL`.
  - Existing history for that ticker is still merged, not destroyed.

Returned update counts:

- normalized ticker
- existing rows
- downloaded rows
- replaced dates
- inserted dates
- final rows
- first final date
- last final date
- saved path

No API key, `.env` contents, or authenticated URL is displayed.

## Raw Versus Selected-Window Behavior

The Data and Audit page now separates:

- `Selected Research Window`
- `Full Raw File`

Each tab independently displays:

- row count
- first date
- last date
- duplicate-date rows
- missing required values
- missing required columns
- zero-volume rows
- invalid OHLC rows
- nonpositive-price rows
- ten largest absolute close-to-close moves
- first five rows
- last five rows

Hard evidence from local `AAPL.csv` AppTest/manual check:

- Selected 10-year window row count: `2,514`
- Selected first date: `2016-06-20`
- Selected last date: `2026-06-18`
- Selected largest-move table did not include 2008 rows.
- Selected first rows began at `2016-06-20`.
- Full Raw File row count: `5,000`
- Full Raw File first date: `2006-08-03`
- Full Raw File largest moves still included `2008-09-29`.

Viewing or selecting a window does not modify the raw CSV.

## Ticker Normalization

Function: `swing_rsi.application.datasets.normalize_ticker`

Behavior:

- `"aapl"` -> `"AAPL"`
- `" AAPL "` -> `"AAPL"`
- `"AAPL.csv"` -> `"AAPL"`
- `"aapl.CSV"` -> `"AAPL"`
- `"brk.b"` -> `"BRK.B"`
- `"BRK-B.csv"` -> `"BRK-B"`
- `"../../AAPL.csv"` -> validation error
- path separators and traversal strings are rejected
- unsupported characters are rejected

Tests: `tests/test_application_services.py`

## Formatting Improvements

Display-only helpers in `dashboard/ui/formatting.py` now provide:

- dates as `YYYY-MM-DD`
- prices with fixed decimal formatting
- returns as percentages, for example `-17.90%`
- comma-separated whole-number volumes
- readable column names
- no timestamp display when only a trading date is relevant

Underlying numeric data is not changed for research, charts, or calculations.

## Caching Behavior

Implemented in `dashboard/ui/cache.py`.

Cached:

- deterministic local CSV reads only
- cache key includes resolved file path and file modification time
- returned dataframe is copied before use

Not cached:

- API keys
- FMP update/download requests
- file writes
- research runs
- walk-forward runs
- append-only actions

Cache invalidation:

- successful dataset update calls `clear_dataset_cache()`
- file modification changes the cache key

Test: `test_dataset_cache_key_changes_after_file_modification`

## Error Handling Behavior

Expected errors:

- missing dataset
- empty window
- invalid dates
- insufficient walk-forward samples
- failed download
- failed validation
- no eligible research rules

Expected errors are shown as concise actionable Streamlit messages.

Unexpected errors:

- logged locally to `logs/dashboard.log`
- `logs/` is ignored by Git
- stack traces are not displayed in the dashboard by default
- error logging avoids API keys, request headers, `.env` contents, and authenticated URLs

## Tests Added Or Updated

Application/service tests:

- ticker normalization strips `.csv`
- ticker normalization rejects traversal/path values
- selected-window audit excludes older rows
- selected-window largest moves remain inside the selected window
- raw-file audit still contains full history
- selected-window audit uses the supplied dataframe
- percentage formatting produces display percentages
- date formatting excludes midnight timestamps
- dataset cache key changes after file modification
- safe update preserves existing history
- overlap dates are replaced once
- duplicate dates do not remain
- failed validation preserves original CSV
- unrelated ticker files are not mutated

Dashboard import/navigation tests:

- exactly five user-facing sections are registered
- required display names and order are preserved
- `app` is not a registered page name
- no `dashboard/pages/*.py` source pages remain
- dashboard imports do not mutate data or call FMP
- dataset display label uses ticker, not filename

Dashboard interaction tests:

- Data and Audit end-date controls remain editable
- ticker selector options display `DEMO`, not `DEMO.csv`
- RSI Explorer controls succeed with DEMO data
- Quick Research form submission succeeds with DEMO data
- candidate row selection succeeds
- Walk-Forward form submission succeeds with DEMO data
- dashboard app startup succeeds without FMP calls
- every section renderer loads without Streamlit exceptions

Walk-forward leakage tests retained:

- future test-window mutation cannot alter prior training-selected parameters or training metrics
- incomplete training trades near fold boundaries cannot use test-window prices

## Verification Results

` .venv/bin/pytest`

- Exit status: 0
- Collected: 58
- Passed: 58
- Failed: 0
- Skipped: 0
- Warnings: none reported in pytest summary

` .venv/bin/ruff check .`

- Exit status: 0
- Result: `All checks passed!`

` .venv/bin/ruff format --check .`

- Exit status: 0
- Result: `62 files already formatted`

` .venv/bin/mypy src`

- Exit status: 0
- Result: `Success: no issues found in 35 source files`

Streamlit AppTest interaction suite:

- Command: `.venv/bin/pytest tests/test_dashboard_interactions.py`
- Exit status: 0
- Collected: 6
- Passed: 6
- Failed: 0
- Skipped: 0

Local server smoke:

- Direct command: `.venv/bin/streamlit run dashboard/app.py --server.address localhost --server.port 8507 --server.headless true`
- First sandboxed bind attempt failed with `PermissionError: [Errno 1] Operation not permitted`.
- Elevated local-only rerun started successfully on `localhost:8507`.
- HTTP check: `curl -I http://localhost:8507`
- Result: `HTTP/1.1 200 OK`
- Process stopped; no listener remained on port 8507.

Launcher smoke:

- Command: `./scripts/run_dashboard.sh`
- Started on `localhost:8502`
- HTTP check: `curl -I http://localhost:8502`
- Result: `HTTP/1.1 200 OK`
- Process stopped; no listener remained on port 8502.

Manual/AppTest Data and Audit acceptance using local `AAPL.csv`:

- Ticker selector displayed `AAPL`, not `AAPL.csv`.
- 10-year selected window displayed rows from 2016 through 2026.
- Selected largest moves did not include 2008.
- Selected first rows did not include 2006.
- Full Raw File tab still showed older raw history.
- Returns displayed as percentages.
- Dates displayed without `00:00:00`.
- Volumes were comma-formatted.

## Security Review

PASS:

- `.env` was not opened or printed by Codex.
- FMP API key value was not searched for, printed, displayed, copied, serialized, or committed.
- `.env` is ignored.
- `.venv` is ignored.
- `data/raw/*` is ignored except `.gitkeep`.
- `reports/*` is ignored except `.gitkeep`.
- `.streamlit/` is ignored.
- `logs/` is ignored.
- Staged/committed files did not include `.env`, `.venv`, raw market data, reports, `.streamlit`, logs, or credentials.
- `git ls-files .env .venv data/raw reports .streamlit logs` returned only `data/raw/.gitkeep` and `reports/.gitkeep`.
- Automated tests monkeypatch provider downloads where needed and do not contact FMP.
- Dashboard import and AppTest startup tests do not make FMP requests.
- Dashboard startup does not automatically contact FMP.

## Research-Integrity Review

PASS:

- Close-known signals still cannot enter at the same close.
- Default entry remains next-session open.
- No trading logic was changed to improve results.
- Transaction costs remain part of backtest/research calls.
- Failed trades are not hidden.
- RSI(14)/30 remains a control comparison and is off by default in RSI Explorer.
- Win rate is not the sole ranking metric.
- In-sample output is labeled as in-sample candidate research, not proven performance.
- Walk-forward aggregate uses unseen test metrics only.
- Training and unseen test displays are visually separated on the Walk-Forward page.
- Walk-forward rules are selected on training slices before unseen test evaluation.
- Future test-window price mutations do not alter prior training selections or metrics.
- Training-slice trades that cannot enter and exit inside the training slice are skipped.
- Synthetic/DEMO data remains plumbing-only evidence, not evidence of an edge.
- FMP corporate-action and historical-universe limitations remain displayed.

## Files Added In Commit

- `dashboard/sections/data_audit.py`
- `dashboard/sections/research_backtest.py`
- `dashboard/sections/walk_forward.py`
- `dashboard/ui/cache.py`
- `dashboard/ui/errors.py`

## Files Modified In Commit

- `.gitignore`
- `README.md`
- `START_HERE.md`
- `dashboard/app.py`
- `dashboard/sections/overview.py`
- `dashboard/sections/rsi_explorer.py`
- `dashboard/ui/formatting.py`
- `dashboard/ui/navigation.py`
- `docs/ARCHITECTURE.md`
- `docs/CHANGELOG.md`
- `docs/DASHBOARD_V0_SCOPE.md`
- `docs/DECISIONS.md`
- `scripts/run_dashboard.sh`
- `src/swing_rsi/application/datasets.py`
- `src/swing_rsi/application/validation_service.py`
- `tests/test_application_services.py`
- `tests/test_dashboard_imports.py`
- `tests/test_dashboard_interactions.py`

## Files Removed In Commit

- `dashboard/pages/__init__.py`
- `dashboard/pages/data_audit.py`
- `dashboard/pages/research_backtest.py`
- `dashboard/pages/walk_forward.py`

## Files Renamed In Commit

- `dashboard/pages/rsi_explorer.py` -> `dashboard/sections/rsi_explorer.py`

## Remaining Limitations And Deferred Items

- No exchange-calendar completeness audit.
- No corporate-action modeling.
- No historical-universe reconstruction.
- No survivorship-bias resolution.
- No production deployment.
- No authentication.
- No database.
- No FastAPI boundary.
- No SvelteKit frontend.
- No portfolio engine.
- No autonomous self-learning discovery loop.
- No options, NLP, intraday data, broker integration, order execution, or live trading.
- Local Streamlit is still temporary presentation infrastructure.
- Local server smoke verified HTTP startup, not a full browser visual regression suite.
- Automated tests do not make external FMP calls by design.

## Launch Command

```bash
./scripts/run_dashboard.sh
```

If Streamlit is missing:

```bash
.venv/bin/python -m pip install -e ".[all,dev,dashboard]"
```
