# Regime Cache Signal Board Fix Handoff

Date: 2026-06-28

## Summary

Fixed Regime KMeans Cache dashboard visibility after the Signal-First dashboard
refactor.

Development repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
```

Branch:

```text
feat/product-class-specialist-challengers-v1
```

The operational repository was checked read-only and was not modified.

## Root Cause

The prior Regime Cache dashboard implementation added compact cache cards to:

```text
dashboard/sections/overview.py
```

After the Signal-First dashboard refactor, `dashboard/ui/navigation.py` no
longer registers Overview in `USER_FACING_SECTIONS`. The first and default
user-facing page is:

```text
Signal Board
```

Therefore the cache cards existed on an old/unregistered page and were not
visible on the user-facing home page.

## Final Visible Locations

Signal Board now shows compact Regime KMeans Cache cards near the top status
area:

- Regime cache status;
- Last cached date;
- KMeans fits avoided;
- Regime runtime;
- Cache validity reason.

Signal Board also shows this caption:

```text
Regime cache preserves exact feature semantics while avoiding expensive historical KMeans recomputation.
```

Developer Diagnostics still includes the full `Regime KMeans Cache` section
with:

- cache schema;
- feature manifest hash;
- first cached date;
- last cached date;
- dates covered;
- cached dates reused;
- new dates computed;
- KMeans fits avoided;
- KMeans fits performed;
- regime runtime;
- input columns;
- KMeans configuration;
- cache validity reason;
- CSV/XLSX export.

## Current Displayed Cache Values

Signal Board AppTest against the current development cache metadata shows:

| Card | Value |
|---|---|
| Regime cache status | `HIT` |
| Last cached date | `2026-06-26` |
| KMeans fits avoided | `2,518` |
| Regime runtime | `2.51 seconds` |
| Cache validity reason | `cache_valid` |

The backing cache summary also shows:

| Field | Value |
|---|---|
| Cache schema | `expanding_kmeans_regime_cache_v1` |
| Universe snapshot ID | `6b1a74750684506e1a5b` |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| First cached date | `2006-08-03` |
| Last cached date | `2026-06-26` |
| Dates covered | 5,005 |
| Rows covered | 5,005 |
| Cached dates reused | 5,005 |
| New dates computed | 0 |
| KMeans fits avoided | 2,518 |
| KMeans fits performed | 0 |

If cache metadata is missing, Signal Board displays:

- Regime cache status: `Not found`;
- all other compact cache-card fields: `Not available`.

## Tests

Updated dashboard tests prove:

- Signal Board displays Regime cache status;
- Signal Board displays last cached date;
- Signal Board displays KMeans fits avoided with thousands separator;
- Signal Board displays regime runtime in seconds;
- Signal Board displays cache validity reason;
- missing cache metadata displays `Not found` / `Not available`;
- Developer Diagnostics displays the full Regime KMeans Cache section;
- page load does not run `build-features`;
- page load does not contact FMP;
- page load does not mutate SQLite;
- page load does not mutate model artifacts.

## Verification Results

Focused Streamlit tests:

```text
.venv/bin/pytest tests/test_streamlit_command_center.py tests/test_dashboard_imports.py
29 passed in 3.16s
```

Full test suite:

```text
.venv/bin/pytest
345 passed, 11576 warnings in 113.39s
```

Static checks:

```text
.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check .
119 files already formatted

.venv/bin/mypy src
Success: no issues found in 61 source files
```

Streamlit AppTest:

```text
Signal Board: no exceptions; Regime cache status HIT displayed.
Developer Diagnostics: no exceptions; Regime KMeans Cache section displayed.
```

Local HTTP smoke test:

```text
.venv/bin/streamlit run dashboard/app.py --server.address localhost --server.port 8513 --server.headless true
curl -I http://localhost:8513
HTTP/1.1 200 OK
```

No FMP update, discovery, scanner, final-holdout update, forward update,
daily-cycle, retraining, feature-definition change, label change, threshold
change, or gate change was performed.

## Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

## Operational Immutability Proof

Operational repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

| Item | Before | After |
|---|---|---|
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | clean on `feat/autonomous-swing-scanner-v1` | clean on `feat/autonomous-swing-scanner-v1` |
| SQLite hash | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |
| Enrolled model artifact hash | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` |
| Scanner snapshot count | 18 | 18 |
| Ordinary forward-event count | 285 | 285 |
| Final-holdout event count | 25 | 25 |
| Prospective run ID | `3493ee8ac37bf96475c362e1` | `3493ee8ac37bf96475c362e1` |
| Baseline date | `2026-06-25` | `2026-06-25` |
| Run status | `COLLECTING` | `COLLECTING` |

The operational repository was not pushed, committed, or modified.
