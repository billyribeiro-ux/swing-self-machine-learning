# Dashboard V0.1 Hardening Handoff

Generated: 2026-06-20T00:26:53Z

Scope: final checkpoint report for the focused Dashboard V0.1 hardening patch.

Security note: `.env` was not opened or printed. This report does not include the FMP API key, secrets, credentials, or authenticated request URLs.

## Repository State

- Branch: `feat/local-research-dashboard`
- Commit hash: `ad1b381c5708a6718140b09dfe0aedb4777b086f`
- Latest commit message: `fix: harden dashboard data updates and validation boundaries`
- Pushed: no
- Remote configured: no
- Working tree before this report file was created: clean
- Current working tree after this report file was created: dirty only because `docs/CODEX_DASHBOARD_V0_1_HARDENING_HANDOFF.md` is untracked

The requested hardening commit is already the current `HEAD`. I did not create a duplicate empty commit.

## Files Added, Modified, And Removed

Files in the hardening checkpoint commit:

```text
M  .gitignore
M  README.md
M  START_HERE.md
A  dashboard/__init__.py
A  dashboard/app.py
A  dashboard/pages/__init__.py
A  dashboard/pages/data_audit.py
A  dashboard/pages/research_backtest.py
A  dashboard/pages/rsi_explorer.py
A  dashboard/pages/walk_forward.py
A  dashboard/sections/__init__.py
A  dashboard/sections/overview.py
A  dashboard/ui/__init__.py
A  dashboard/ui/charts.py
A  dashboard/ui/components.py
A  dashboard/ui/formatting.py
A  dashboard/ui/navigation.py
M  docs/ARCHITECTURE.md
M  docs/CHANGELOG.md
A  docs/CODEX_DASHBOARD_V0_1_HANDOFF.md
A  docs/DASHBOARD_V0_SCOPE.md
M  docs/DECISIONS.md
M  pyproject.toml
M  scripts/bootstrap_mac.sh
A  scripts/run_dashboard.sh
M  src/swing_rsi/__init__.py
A  src/swing_rsi/application/__init__.py
A  src/swing_rsi/application/datasets.py
A  src/swing_rsi/application/project_status.py
A  src/swing_rsi/application/research_service.py
A  src/swing_rsi/application/validation_service.py
M  src/swing_rsi/cli.py
A  tests/test_application_services.py
A  tests/test_dashboard_imports.py
A  tests/test_dashboard_interactions.py
M  tests/test_walk_forward.py
```

No tracked file deletion is present in the final commit because `dashboard/pages/overview.py` was never committed before it was removed during hardening.

## Duplicate Overview Resolution

Issue found: Overview was duplicated in Streamlit navigation.

Previous registration:

- `dashboard/app.py` rendered the Overview page.
- `dashboard/pages/overview.py` also existed in Streamlit's multipage directory.

Final resolution:

- `dashboard/app.py` now imports `render_page` from `dashboard.sections.overview`.
- Overview rendering lives in `dashboard/sections/overview.py`, outside the Streamlit page-registration directory.
- `dashboard/pages/overview.py` is absent.
- `dashboard/ui/navigation.py` defines exactly five user-facing sections.
- `tests/test_dashboard_imports.py::test_dashboard_registers_exactly_five_user_facing_sections` verifies the five-section set.

Current user-facing dashboard sections:

1. Overview
2. Data and Audit
3. RSI Explorer
4. Research and Backtest
5. Walk-Forward Validation

## Dataset Update Behavior

Previous behavior:

- `download_daily_to_raw` downloaded the requested date range and saved that frame directly to `data/raw/{TICKER}.csv`.
- A narrow request, such as a 30-day update, could overwrite a broader existing ticker CSV and silently truncate years of history.

Current behavior:

- Existing ticker CSV is loaded when present.
- Requested FMP range is downloaded through the existing provider abstraction.
- Downloaded OHLCV is validated before merge.
- Existing and downloaded rows are merged by `Date`.
- New downloaded values replace existing rows on duplicate dates.
- New dates are inserted.
- Dates outside the requested range are preserved.
- Final merged data is sorted chronologically.
- Final merged OHLCV is validated before writing.
- The result reports downloaded rows, existing rows, replaced dates, inserted dates, and final rows.

Implementation:

- `src/swing_rsi/application/datasets.py::download_daily_to_raw`
- `src/swing_rsi/application/datasets.py::_merge_downloaded_history`
- `dashboard/pages/data_audit.py` displays the merge counts.
- `src/swing_rsi/cli.py` uses the same service.

## Atomic-Write Protection

Atomic write behavior:

- The downloaded frame is validated first.
- The merged frame is validated second.
- `atomic_write_csv(validated, output, index=True)` runs only after validation succeeds.
- If validation fails, the original CSV is not replaced.

Tests proving this:

- `tests/test_application_services.py::test_download_update_failed_validation_does_not_damage_original_csv`
- `tests/test_application_services.py::test_download_update_preserves_existing_history_for_short_range`
- `tests/test_application_services.py::test_download_update_replaces_overlap_once_and_keeps_unique_dates`
- `tests/test_application_services.py::test_download_update_does_not_mutate_unrelated_ticker_files`

## Walk-Forward Leakage Protections

Current walk-forward boundary behavior:

- `run_walk_forward` selects rules on a prior training slice.
- `run_grid_search` receives only that training slice.
- `backtest_fixed_horizon` skips signals whose next-open entry or fixed-horizon exit would fall outside the supplied frame.
- A training trade near a fold boundary therefore cannot use test-window prices.
- Test metrics remain stored under `test_*` fields.
- Aggregate walk-forward results use test metrics only.

Tests added:

- `tests/test_walk_forward.py::test_future_test_window_price_changes_do_not_change_prior_training_selection`
- `tests/test_walk_forward.py::test_training_slice_skips_trades_that_would_exit_in_test_window`

UI note added:

- `dashboard/pages/walk_forward.py` explains that the gap is unused sessions between train/test windows and that training trades unable to enter and exit inside the training slice are skipped.

No new strategy features or alternative validation framework were added.

## Interaction Tests

Streamlit interaction tests use temporary local synthetic DEMO data and patch the downloader to fail if a dashboard smoke test attempts an FMP download.

Tests:

- `tests/test_dashboard_interactions.py::test_rsi_explorer_controls_smoke`
- `tests/test_dashboard_interactions.py::test_quick_research_submission_and_candidate_selection_smoke`
- `tests/test_dashboard_interactions.py::test_walk_forward_submission_smoke`

Coverage:

- RSI Explorer controls
- Quick Research form submission
- Candidate row selection
- Walk-Forward form submission

Result: all interaction tests passed without Streamlit page exceptions.

## Verification Results

### Pytest

Command:

```text
.venv/bin/pytest
```

Result:

```text
collected 38 items
38 passed in 17.69s
```

Breakdown:

```text
tests/test_application_services.py .............                         [ 34%]
tests/test_backtester.py .                                               [ 36%]
tests/test_dashboard_imports.py ..                                       [ 42%]
tests/test_dashboard_interactions.py ...                                 [ 50%]
tests/test_data_validation.py ..                                         [ 55%]
tests/test_fmp_provider.py ....                                          [ 65%]
tests/test_forward_journal.py .                                          [ 68%]
tests/test_no_future_leakage.py ...                                      [ 76%]
tests/test_rsi.py ....                                                   [ 86%]
tests/test_settings.py ..                                                [ 92%]
tests/test_walk_forward.py ...                                           [100%]
```

### Ruff

Command:

```text
.venv/bin/ruff check .
```

Result:

```text
All checks passed!
```

### Formatting

Command:

```text
.venv/bin/ruff format --check .
```

Result:

```text
61 files already formatted
```

### Mypy

Command:

```text
.venv/bin/mypy src
```

Result:

```text
Success: no issues found in 35 source files
```

## Streamlit Smoke-Test Result

### AppTest Page Smoke

Command: local Python AppTest script loading all five sections.

Result:

```text
PASS Overview: dashboard/app.py
PASS Data and Audit: dashboard/pages/data_audit.py
PASS RSI Explorer: dashboard/pages/rsi_explorer.py
PASS Research and Backtest: dashboard/pages/research_backtest.py
PASS Walk-Forward Validation: dashboard/pages/walk_forward.py
```

Warnings: Streamlit emitted expected bare-mode `missing ScriptRunContext` warnings. These did not create page exceptions.

### Local Server Smoke

Command:

```text
./scripts/run_dashboard.sh
```

Result:

```text
Uvicorn server started on localhost:8502
URL: http://localhost:8502
```

Command:

```text
curl -I http://localhost:8502
```

Result:

```text
HTTP/1.1 200 OK
```

The Streamlit process was stopped cleanly.

## Secret And Artifact Check

Tracked files check:

```text
git ls-files .env .venv data/raw reports .streamlit
```

Result:

```text
data/raw/.gitkeep
reports/.gitkeep
```

Ignored artifact check confirmed:

- `.env` ignored by `.gitignore`
- `.venv/` ignored by `.gitignore`
- `data/raw/*` ignored except `.gitkeep`
- `reports/*` ignored except `.gitkeep`
- `.streamlit/` ignored by `.gitignore`

Pattern scan found only expected template names, code variable names, documentation references, and dummy test values. No real credential value was opened or printed.

## Remaining Limitations

- This report file is intentionally generated after the hardening commit, so it is currently untracked unless the user asks for a separate documentation commit.
- No destructive replacement workflow was added for raw data.
- FMP corporate-action semantics remain unaudited.
- FMP historical-universe and survivorship-bias semantics remain unaudited.
- No exchange-calendar completeness audit exists.
- Streamlit smoke tests are headless AppTest plus local HTTP startup, not a manual browser visual QA pass.
- Walk-forward remains the existing expanding-window fixed-horizon daily implementation; no advanced purged cross-validation library was added.
- Synthetic DEMO results validate plumbing only and are not evidence of a live trading edge.

