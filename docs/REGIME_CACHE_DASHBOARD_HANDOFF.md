# Regime Cache Dashboard Handoff

Date: 2026-06-28

## Summary

Added Regime KMeans Cache diagnostics to the Streamlit dashboard in the
development repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
```

Branch:

```text
feat/product-class-specialist-challengers-v1
```

The operational repository was checked read-only and was not modified.

## Dashboard Fields Added

Overview now shows compact Regime KMeans Cache status cards:

- regime cache status;
- last cached date;
- KMeans fits avoided;
- regime runtime;
- cache validity reason.

Developer Diagnostics now includes a full `Regime KMeans Cache` section with:

- summary status table;
- raw cache/latest-run metadata;
- regime input columns;
- KMeans configuration;
- CSV export for metadata;
- XLSX export with `summary`, `metadata`, `input_columns`, and `kmeans_config`
  sheets.

Both pages display this text:

```text
The regime cache preserves exact current feature semantics. It only avoids recomputing historical expanding KMeans labels when inputs and configuration are unchanged.
```

## Metadata Source

The dashboard reads local files under:

```text
data/cache/regime/
```

It reads:

- exact cache artifact schema `expanding_kmeans_regime_cache_v1`;
- latest-run status sidecar schema `expanding_kmeans_regime_cache_status_v1`.

Page load does not run `build-features`, recompute regime features, contact FMP,
mutate SQLite, or modify model artifacts.

If no cache metadata exists, the dashboard shows `NOT_FOUND` and:

```text
Run build-features to create the regime cache.
```

Forced rebuild guidance is displayed as:

```bash
SWING_RSI_REBUILD_REGIME_CACHE=1 .venv/bin/python -m swing_rsi.cli build-features
```

## Current Displayed Values

After a warm-cache development `build-features` run:

| Field | Value |
|---|---|
| Feature rows | 90,148 |
| Label rows | 90,148 |
| Modeling rows | 90,148 |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| Regime cache status | `HIT` |
| Validity reason | `cache_valid` |
| First cached date | `2006-08-03` |
| Last cached date | `2026-06-26` |
| Dates covered | 5,005 |
| Cached dates reused | 5,005 |
| New dates computed | 0 |
| KMeans fits avoided | 2,518 |
| KMeans fits performed | 0 |
| Regime runtime | 2.51 seconds |
| Cache schema | `expanding_kmeans_regime_cache_v1` |
| Status sidecar schema | `expanding_kmeans_regime_cache_status_v1` |

No pandas `PerformanceWarning` appeared in the build output.

## Tests Added

Added dashboard tests proving:

- Overview displays Regime cache status;
- Developer Diagnostics displays the Regime KMeans Cache section;
- missing cache metadata displays `NOT_FOUND` / not found without error;
- existing cache metadata displays `HIT` and `cache_valid`;
- missing numeric fields display `Not available`, not `0`;
- KMeans fits avoided displays with a thousands separator;
- runtime displays in seconds;
- page load does not run `build-features`;
- page load does not contact FMP;
- page load does not mutate SQLite;
- page load does not mutate model artifacts;
- CSV export works;
- XLSX export works and opens with `openpyxl`;
- XLSX contains `summary`, `metadata`, `input_columns`, and `kmeans_config`;
- exports do not contain `.env` contents or API-key-looking values.

## Verification Results

Warm-cache build:

```text
.venv/bin/python -m swing_rsi.cli build-features
Feature rows: 90,148
Label rows: 90,148
Modeling rows: 90,148
Feature manifest hash: 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5
Regime cache status: HIT (cache_valid)
Regime cache cached dates reused: 5,005
Regime cache new dates computed: 0
Regime cache KMeans fits avoided: 2,518
Regime cache KMeans fits performed: 0
Regime cache runtime: 2.51 seconds
```

Focused tests:

```text
.venv/bin/pytest tests/test_streamlit_command_center.py tests/test_dashboard_imports.py tests/test_regime_kmeans_cache.py
39 passed in 11.36s
```

Full tests:

```text
.venv/bin/pytest
345 passed, 11576 warnings in 110.14s
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

Streamlit AppTest coverage:

- Overview page exercised by `tests/test_streamlit_command_center.py`;
- Developer Diagnostics page exercised by `tests/test_streamlit_command_center.py`.

Local HTTP smoke test:

```text
.venv/bin/streamlit run dashboard/app.py --server.address localhost --server.port 8512 --server.headless true
curl -I http://localhost:8512
HTTP/1.1 200 OK
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

## Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

## Known Limitations

- The dashboard reports the latest local cache metadata; it does not validate
  cache exactness independently on page load.
- If the status sidecar is missing but an exact cache artifact exists, the
  latest build-run status is `UNKNOWN` until `build-features` runs again.
- Cache age is display-only and changes with wall-clock time.

## Next Smallest Task

Open the dashboard in a browser and visually confirm the Overview and Developer
Diagnostics Regime KMeans Cache panels in the normal user session.
