# Streamlit Navigation Fix Handoff

## Root Cause

The reported 9-page sidebar exactly matches the frozen operational repository
navigation on branch `feat/autonomous-swing-scanner-v1`:

1. Overview
2. Data and Universe
3. Discovery Lab
4. Live Scanner
5. Candidate Attribution
6. Portfolio Backtests
7. Paper Forward Test
8. Model Registry
9. Baselines and Legacy RSI

The development worktree entrypoint, `dashboard/app.py`, already launches the
Command Center registry through:

```python
page = st.navigation(streamlit_pages(st), position="sidebar")
```

The mismatch was a launch-path/process mismatch plus a test gap. The old labels
remain in the operational repository and in legacy section modules, but they are
not registered as visible Command Center pages in the development worktree.
Earlier tests asserted the helper list and section renderers; they did not prove
the actual `dashboard/app.py` entrypoint registered those pages.

## Files Changed

- `tests/test_dashboard_imports.py`
- `tests/test_streamlit_command_center.py`
- `docs/STREAMLIT_COMMAND_CENTER_DASHBOARD.md`
- `docs/STREAMLIT_COMMAND_CENTER_DASHBOARD_HANDOFF.md`
- `docs/STREAMLIT_NAVIGATION_FIX_HANDOFF.md`
- `docs/CHANGELOG.md`
- `docs/DECISIONS.md`

## Final Visible Page List

`streamlit run dashboard/app.py` in the development worktree registers exactly:

1. Overview
2. Data and Universe
3. Model Registry
4. Gate Audit
5. Product-Class Specialists
6. Scanner Snapshots
7. Candidate Attribution
8. Shadow Final Holdout
9. Paper Forward Test
10. Reports and Exports
11. Engine Commands
12. Legacy Baselines

The primary navigation labels `Discovery Lab`, `Live Scanner`,
`Portfolio Backtests`, and `Baselines and Legacy RSI` are not registered by the
development Command Center entrypoint.

## Tests Added Or Tightened

- Added an app-entrypoint navigation regression test that runs `dashboard/app.py`
  with a fake Streamlit module and captures the actual `st.Page` registrations.
- The app-entrypoint test asserts the exact 12 labels, exact order, URL paths,
  sidebar navigation position, and single default page.
- Added an app-entrypoint startup test proving operational-repository startup
  stops before navigation is registered.
- Tightened page-load safety coverage so Command Center page loads fail if they
  try the FMP download path.
- Tightened page-load mutation coverage to include the model artifact file in
  addition to SQLite and scanner snapshot bytes.

## Verification Results

Completed in the development worktree:

- `.venv/bin/pytest`: 320 passed, 11776 warnings
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: 111 files already formatted
- `.venv/bin/mypy src`: success, no issues in 61 source files
- `.venv/bin/streamlit run dashboard/app.py --server.port 8502 --server.headless true --server.address localhost`: started successfully
- `curl -I http://localhost:8502`: `HTTP/1.1 200 OK`
- App-entrypoint navigation capture: exactly the 12 required Command Center
  pages in order

Warnings were the existing pandas/joblib/performance warnings from the engine
test suite, not navigation failures.

## Local Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py --server.port 8502
```

## Operational State

The operational repository was inspected read-only to confirm the source of the
old 9-page labels. No operational files, SQLite databases, artifacts, scanner
snapshots, reports, logs, events, final-holdout state, or `.env` files were
modified.
