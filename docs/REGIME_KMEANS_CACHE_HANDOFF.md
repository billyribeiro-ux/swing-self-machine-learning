# Regime KMeans Cache Handoff

Date: 2026-06-28

## Summary

Implemented Exact Expanding KMeans Regime Cache V1 in the development worktree:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
```

Development branch:

```text
feat/product-class-specialist-challengers-v1
```

The operational repository was inspected read-only and was not modified.

## Why Less-Frequent Refit Was Rejected

The read-only equivalence study found all less-frequent schedules were
`TOO_DIFFERENT` despite large speedups. Best row-level agreement was only
73.56% for 5-session refits, transition-date agreement remained weak, and ARI
/ NMI were low. Therefore this implementation does not change refit cadence.

The cache preserves the existing one expanding KMeans refit per eligible market
date.

## Cache Schema

Schema version:

```text
expanding_kmeans_regime_cache_v1
```

Default cache location:

```text
data/cache/regime/
```

The cache artifact is a single atomically replaced JSON file containing:

- cache schema version;
- universe snapshot ID;
- regime input columns;
- KMeans parameters;
- random seed;
- scaler/preprocessing configuration;
- minimum sample requirement;
- feature-builder code/version identifier;
- date-ordering contract;
- input prefix hash;
- full input hash;
- dates covered;
- last cached date;
- row count;
- symbols covered;
- output column names;
- output dataframe hash;
- creation timestamp UTC;
- update timestamp UTC;
- cache validity status;
- cached `Date` / `market_regime_cluster_expanding` records.

No secrets, `.env` values, provider keys, raw OHLCV, labels, model artifacts,
scanner state, forward state, or final-holdout state are stored in the cache.

## Validity Checks

The cache is reused only when all frozen inputs match:

- schema version;
- universe snapshot ID;
- sorted symbol set;
- date ordering;
- regime input columns;
- KMeans `n_clusters`, `random_state`, and `n_init`;
- preprocessing policy;
- 126-row minimum sample requirement;
- feature-builder version identifier;
- cached date prefix;
- historical input-prefix hash;
- cached output dataframe hash;
- last cached date;
- output column names.

## Invalidation Rules

The cache is invalidated and a full recompute is used when:

- the file is missing or corrupt;
- the schema changes;
- the universe snapshot changes;
- the symbol set changes;
- date ordering or historical dates change;
- any historical regime input value changes;
- KMeans config changes;
- random seed changes;
- input columns change;
- preprocessing config changes;
- output hash validation fails;
- `--rebuild-regime-cache` is passed;
- `SWING_RSI_REBUILD_REGIME_CACHE=1` is set.

For a valid unchanged historical prefix with later dates, the builder reuses old
labels and computes only the new dates with exact expanding refits.

## Atomic-Write Behavior

Writes go to a temporary file in `data/cache/regime/` and then use `os.replace`
to atomically replace the cache artifact. If the write fails, the previous valid
cache remains in place and the current feature output still comes from the exact
computed labels.

Unit coverage simulates an atomic replace failure and verifies the old cache is
not destroyed.

## First-Run Performance

Command:

```bash
.venv/bin/python -m swing_rsi.cli build-features --rebuild-regime-cache
```

Result:

| Metric | Value |
|---|---:|
| Feature rows | 90,148 |
| Label rows | 90,148 |
| Modeling rows | 90,148 |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| Regime cache status | `INVALIDATED (forced_rebuild)` |
| Cached dates reused | 0 |
| New dates computed | 5,005 |
| KMeans fits avoided | 0 |
| KMeans fits performed | 2,518 |
| Regime runtime | 131.82 seconds |

The forced rebuild was intentionally a full recompute. No pandas
`PerformanceWarning` appeared in output. No FMP update command was run.

## Second-Run Performance

Command:

```bash
time .venv/bin/python -m swing_rsi.cli build-features
```

Result:

| Metric | Value |
|---|---:|
| Feature rows | 90,148 |
| Label rows | 90,148 |
| Modeling rows | 90,148 |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| Regime cache status | `HIT (cache_valid)` |
| Cached dates reused | 5,005 |
| New dates computed | 0 |
| KMeans fits avoided | 2,518 |
| KMeans fits performed | 0 |
| Regime runtime | 2.54 seconds |
| Total command time | 50.505 seconds |

The warm-cache regime block avoided all 2,518 KMeans fits. No pandas
`PerformanceWarning` appeared in output. No FMP update command was run.

## Feature Manifest Hash

Before and after performance validation:

```text
3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5
```

The manifest did not change.

## Tests

New focused tests cover:

1. First run with no cache performs full recompute.
2. First run writes a valid cache.
3. Second run with identical inputs reuses cache.
4. Second run exactly matches full recompute labels.
5. Second run performs zero KMeans fits.
6. Appending one date computes only that date.
7. Appending one date matches full recompute.
8. Historical prefix change invalidates cache.
9. KMeans config change invalidates cache.
10. Input column change invalidates cache.
11. Universe/symbol-set change invalidates cache.
12. Random seed change invalidates cache.
13. Corrupt cache is ignored and recomputed.
14. Atomic write failure preserves the previous valid cache.
15. Forced rebuild ignores cache and rewrites it.
16. Regime-conditioned downstream features remain identical.
17. Feature manifest hash remains unchanged for unchanged input.
18. No label columns enter feature matrices.
19. No positive or negative infinity values are introduced.
20. Cache path is Git-ignored.
21. Tests make no FMP calls.
22. Tests do not touch the operational repository.

## Verification Results

```text
.venv/bin/pytest
340 passed, 11576 warnings in 111.42s
```

```text
.venv/bin/ruff check .
All checks passed.
```

```text
.venv/bin/ruff format --check .
119 files already formatted.
```

```text
.venv/bin/mypy src
Success: no issues found in 61 source files
```

Warnings were pre-existing pandas/joblib warnings in model-discovery style tests.

## Operational Immutability Proof

Operational repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

| Item | Before | After |
|---|---|---|
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | `?? docs/REGIME_KMEANS_REFIT_EQUIVALENCE_STUDY.md` | `?? docs/REGIME_KMEANS_REFIT_EQUIVALENCE_STUDY.md` |
| SQLite hash | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |
| Enrolled model artifact hash | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` |
| Scanner snapshot count | 18 | 18 |
| Ordinary forward-event count | 285 | 285 |
| Final-holdout event count | 25 | 25 |
| Prospective run ID | `3493ee8ac37bf96475c362e1` | `3493ee8ac37bf96475c362e1` |
| Baseline date | `2026-06-25` | `2026-06-25` |
| Run status | `COLLECTING` | `COLLECTING` |

The untracked operational report existed before this task and was not touched.

## Known Limitations

- The cache stores exact labels but not trained KMeans models.
- The cache still counts expected eligible fits by scanning the market-daily
  input, so warm-cache regime runtime is not zero.
- A forced rebuild remains as slow as the original expanding KMeans path.
- The cache is scoped to the current feature-builder process and local files; it
  is not a shared service cache.
- This does not address the separate positive-infinity diagnostics in volume
  features because they are unrelated to regime KMeans.

## Next Smallest Task

Add a lightweight dashboard/developer diagnostics panel that displays the latest
regime cache status, last cached date, fit count avoided, and cache validity
reason from the most recent `build-features` run.
