# Build-Features Performance Profile

## Scope

This is a read-only performance diagnosis of the current development
`build-features` workflow after the DataFrame fragmentation cleanup.

Development commit profiled:

```text
917e88c fix: batch feature construction to avoid dataframe fragmentation
```

No source code, feature definitions, labels, thresholds, gates, model artifacts,
SQLite state, FMP data, scanner snapshots, forward events, final-holdout events,
or operational repository files were modified.

## Profiling Method

The profiler used a temporary script under `/tmp` with:

- `time.perf_counter` high-level timers;
- `cProfile` / `pstats` top cumulative function timing;
- line-range timing mapped to existing `src/swing_rsi/engine/features.py`
  feature blocks;
- warning capture for `pandas.errors.PerformanceWarning`;
- parquet write timing to `/tmp/build_features_readonly_profile_parquet/`.

The run used local development data only. It did not call FMP and did not write
the normal development feature output paths during the profiling pass.

## Output Equivalence

Expected baseline:

```text
Feature rows: 90,148
Label rows: 90,148
Modeling rows: 90,148
Feature manifest hash: 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5
```

Profiled in-memory output:

```text
Feature rows: 90,148
Label rows: 90,148
Modeling rows: 90,148
Feature manifest hash: 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5
```

The manifest matched exactly.

No pandas `PerformanceWarning` was captured.

Feature-frame validation:

- label columns in feature frame: `0`
- positive infinity values: `35`
- negative infinity values: `0`

The same `35` positive infinity values are already present in the existing
development feature parquet for this manifest, so profiling introduced no new
infinities.

## Total Runtime

Instrumented profile runtime:

```text
262.83 seconds
```

The timing includes cProfile and feature line-range instrumentation overhead.

Memory:

| Metric | Value |
|---|---:|
| Max RSS | 2,353.11 MB |
| Feature frame | 371.41 MB |
| Label frame | 87.65 MB |
| Modeling frame | 457.38 MB |

Columns:

| Frame | Columns |
|---|---:|
| Feature frame | 534 |
| Numeric feature columns | 528 |
| Labels | 127 |
| Modeling frame | 659 |

## High-Level Timing

| Block | Seconds | % Total |
|---|---:|---:|
| Feature panel build | 191.91 | 73.02% |
| Label creation | 67.43 | 25.66% |
| Parquet writes to `/tmp` | 2.66 | 1.01% |
| Raw manifest generation in memory | 0.52 | 0.20% |
| Raw data loading | 0.18 | 0.07% |
| Nonfinite and label-column verification | 0.10 | 0.04% |
| Universe loading | 0.01 | 0.00% |
| Modeling frame assembly | 0.01 | 0.00% |

`nonfinite hygiene` as a model-matrix sanitation step is not part of
`build-features`; it is applied later in model/scanner paths. The profile only
timed read-only nonfinite verification of the generated feature frame.

## Feature-Block Timing

Feature line-range total:

```text
191.84 seconds
```

| Feature Block | Seconds | % Feature Build | % Total |
|---|---:|---:|---:|
| Regime features | 146.50 | 76.36% | 55.74% |
| RSI features | 28.79 | 15.01% | 10.95% |
| Sector daily aggregate features | 10.76 | 5.61% | 4.09% |
| Breadth features | 1.71 | 0.89% | 0.65% |
| Volatility/range features | 0.73 | 0.38% | 0.28% |
| Symbol metadata columns | 0.72 | 0.37% | 0.27% |
| Market-relative features | 0.71 | 0.37% | 0.27% |
| Returns/momentum features | 0.60 | 0.31% | 0.23% |
| Technical primitive features | 0.37 | 0.19% | 0.14% |
| Trend/structure features | 0.29 | 0.15% | 0.11% |
| Symbol-level setup/base OHLCV | 0.20 | 0.10% | 0.07% |
| Candle geometry features | 0.15 | 0.08% | 0.06% |
| Volume/participation features | 0.13 | 0.07% | 0.05% |
| Relationship graph features | 0.04 | 0.02% | 0.01% |
| Cross-sectional ranks | 0.04 | 0.02% | 0.01% |
| Sector-relative features | 0.04 | 0.02% | 0.01% |
| Relationship merge | 0.01 | 0.01% | 0.00% |
| Feature family/spec/manifest generation | 0.07 | 0.04% | 0.03% |
| Inverse/leveraged features | 0.00 | 0.00% | 0.00% |

## Top Bottleneck

The single slowest remaining block is:

```text
Regime features
```

Measured time:

```text
146.50 seconds
```

Share:

```text
76.36% of feature-build line time
55.74% of total instrumented runtime
```

The cProfile output identifies the specific hotspot as
`_expanding_kmeans_regime(...)`, which repeatedly fits `sklearn.cluster.KMeans`
for expanding histories:

```text
features.py:257(_expanding_kmeans_regime) 146.355 seconds cumulative
sklearn.cluster._kmeans.KMeans.fit_predict 137.331 seconds cumulative
2,518 KMeans fit_predict calls
```

RSI features are the second-largest feature block. Their hotspot is rolling
percentile calculation:

```text
features.py:232(_rolling_percentile) 21.667 seconds cumulative
1,785 rolling-percentile calls
```

Label creation is the second-largest high-level workflow cost outside feature
building:

```text
labels.py:175(build_label_panel) 67.432 seconds cumulative
```

## cProfile Top 20 By Cumulative Time

```text
419119538 function calls (413890705 primitive calls) in 262.812 seconds

Ordered by: cumulative time

ncalls      tottime  cumtime  function
1           0.013    191.901  features.py:879(build_feature_panel)
1           0.009    159.850  features.py:509(_add_cross_sectional_features)
1           0.092    146.355  features.py:257(_expanding_kmeans_regime)
2518        0.004    137.331  sklearn/cluster/_kmeans.py:1050(fit_predict)
2518        0.033    137.327  sklearn/base.py:1381(wrapper)
2518        0.579    136.710  sklearn/cluster/_kmeans.py:1435(fit)
25180       0.175    121.613  sklearn/utils/parallel.py:206(wrapper)
25180     116.643    120.989  sklearn/cluster/_kmeans.py:629(_kmeans_single_lloyd)
1           0.019     67.432  labels.py:175(build_label_panel)
35          2.631     67.230  labels.py:67(build_symbol_labels)
2701223     1.931     35.383  pandas/core/indexing.py:1192(__getitem__)
35          0.053     31.959  features.py:283(_symbol_features)
2699583     2.234     30.548  pandas/core/indexing.py:1740(_getitem_axis)
7379        0.007     24.400  pandas/core/window/rolling.py:538(_apply)
7379        0.008     24.383  pandas/core/window/rolling.py:444(_apply_columnwise)
7379        0.023     24.360  pandas/core/window/rolling.py:424(_apply_series)
7379        0.016     24.085  pandas/core/window/rolling.py:571(homogeneous_func)
7379        2.371     24.057  pandas/core/window/rolling.py:577(calc)
1785        0.002     21.667  features.py:232(_rolling_percentile)
1785        0.002     21.651  pandas/core/window/rolling.py:2167(apply)
```

## Operational Immutability Proof

Operational repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

Before and after values matched exactly.

| Item | Before | After |
|---|---|---|
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | clean on `feat/autonomous-swing-scanner-v1` | clean on `feat/autonomous-swing-scanner-v1` |
| SQLite hash | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |
| Enrolled model artifact hash | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` |
| Scanner snapshot count | `18` | `18` |
| Ordinary forward-event count | `285` | `285` |
| Final-holdout event count | `25` | `25` |
| Prospective run ID | `3493ee8ac37bf96475c362e1` | `3493ee8ac37bf96475c362e1` |
| Baseline date | `2026-06-25` | `2026-06-25` |
| Run status | `COLLECTING` | `COLLECTING` |

Operational SQLite was opened with `mode=ro`. No operational mutating command was
run.

## Recommendation

Exactly one smallest recommended optimization:

Refactor `_expanding_kmeans_regime(...)` so it does not fit a fresh
`KMeans(n_clusters=3, n_init=10)` model for every expanding date. The smallest
safe next step is to prototype a read-only equivalence study comparing the
current per-date expanding KMeans labels against a less frequent refit schedule,
without changing feature definitions or committing implementation changes.
