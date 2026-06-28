# Regime KMeans Refit Equivalence Study

Date: 2026-06-28

Study type: read-only feature-equivalence and runtime study. No source code, feature definitions, labels, thresholds, gates, product-class mappings, SQLite state, model artifacts, scanner state, forward state, final-holdout state, or FMP data were modified.

## Repositories And Frozen Context

- Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`
- Development branch/commit inspected: `feat/product-class-specialist-challengers-v1` / `917e88c94b5acaf633139e540079a9e01eb2aa45`
- Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- Operational frozen run: `3493ee8ac37bf96475c362e1`
- Enrolled model: `b93b2258c10aea5cef81d291`
- Baseline date: `2026-06-25`
- Feature manifest: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`

## Baseline Implementation Summary

Current implementation inspected: `src/swing_rsi/engine/features.py`.

- `_expanding_kmeans_regime(...)` input columns: `market_regime_trend_score`, `market_regime_volatility_score`, `breadth_advance_pct`, `breadth_dispersion_20`.
- Date ordering: `build_feature_panel` sorts by `Date, symbol`; `_add_cross_sectional_features` builds one `market_daily` row per `Date`; `_expanding_kmeans_regime` iterates `market_daily` in that chronological order.
- Minimum sample requirement: 126 market-date rows before fitting.
- Cluster count: 3.
- Random seed: `random_state=42`.
- KMeans initialization: `n_init=10`.
- Scaling/preprocessing: no standardization or scaling. Positive/negative infinity is replaced with `NaN`; expanding-history column medians are computed using rows available through the current date; missing values are filled with those medians and then zero if a median is unavailable.
- Exact refit cadence: every eligible market date. The function slices `values.iloc[: position + 1]` and fits a new `KMeans` for that date.
- `fit_predict` cadence: yes, one `KMeans.fit_predict(...)` call per eligible date when at least three distinct filled rows exist. The confirmed profile counted 2,518 calls.
- Chronology: the baseline fit for date `t` uses rows through `t` only. It does not use future rows, labels, outcomes, or shuffling.
- Output column: `market_regime_cluster_expanding`.
- Other regime columns created in the same block: `market_regime_label`, `market_regime_trend_score`, `market_regime_volatility_score`, `regime_conditioned_return_20`.
- Downstream dependency: `regime_conditioned_return_20 = return_20 * market_regime_trend_score.fillna(0.0)`. It does not depend on the KMeans cluster label. `market_regime_cluster_expanding` is a numeric feature in the feature frame, but the frozen enrolled model inspected here does not require it.

## Study Method

The study loaded the existing development feature parquet only:

| Item | Value |
| --- | --- |
| Feature rows | 90,148 |
| Label rows | 90,148 |
| Modeling rows | 90,148 |
| Feature columns | 534 |
| Unique dates | 5,005 |
| Unique symbols | 35 |
| Coverage | 2006-08-03 through 2026-06-26 |
| Baseline non-null KMeans dates | 2,518 |

Alternatives were prototyped under `/tmp/regime_kmeans_refit_study/`. Each schedule fits only on rows available through the refit date. Between refit dates, the last fitted KMeans model assigns newer rows using the last refit-date imputation medians. No labels, outcomes, development-holdout outcomes, random shuffling, model training, discovery, scanner, forward-update, final-holdout-update, or daily-cycle command was used.

Cluster IDs were aligned before agreement measurement with deterministic majority assignment over date-level labels. Metrics below are after alignment.

## Runtime Table

| Schedule | Regime runtime seconds | KMeans fits | Estimated speedup | Runtime reduction | Classification |
| --- | --- | --- | --- | --- | --- |
| baseline daily | 146.50 | 2,518 | 1.00x | 0.00% | reference |
| 5 sessions | 28.03 | 504 | 5.23x | 80.87% | TOO_DIFFERENT |
| 10 sessions | 15.21 | 252 | 9.63x | 89.62% | TOO_DIFFERENT |
| 20 sessions | 8.72 | 126 | 16.79x | 94.04% | TOO_DIFFERENT |
| 40 sessions | 5.48 | 63 | 26.74x | 96.26% | TOO_DIFFERENT |
| monthly | 8.54 | 121 | 17.16x | 94.17% | TOO_DIFFERENT |
| quarterly | 4.39 | 41 | 33.38x | 97.00% | TOO_DIFFERENT |

## Label Agreement Summary

| Schedule | Row agreement | Date agreement | Transition Jaccard | Regime-change diff | Worst year | Worst symbol | Worst product scope | Worst market-regime period |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 sessions | 73.56% | 73.67% | 42.30% | -305 | 2025 53.60% | XLC 68.90% | sector_etf 73.32% | downtrend_high_vol 68.80% |
| 10 sessions | 67.97% | 68.11% | 41.91% | -363 | 2024 45.24% | XLC 62.25% | sector_etf 67.68% | downtrend_high_vol 58.46% |
| 20 sessions | 64.47% | 64.61% | 40.30% | -382 | 2025 42.40% | XLC 58.33% | sector_etf 64.15% | downtrend_high_vol 57.15% |
| 40 sessions | 60.68% | 60.84% | 40.51% | -401 | 2025 34.00% | XLC 53.87% | sector_etf 60.33% | downtrend_high_vol 54.17% |
| monthly | 66.38% | 66.52% | 40.58% | -389 | 2024 36.11% | XLC 60.37% | sector_etf 66.06% | downtrend_high_vol 59.95% |
| quarterly | 61.43% | 61.60% | 40.25% | -419 | 2026 14.88% | XLC 54.37% | sector_etf 61.06% | downtrend_high_vol 55.05% |

Transition Jaccard compares dates where the aligned alternative and baseline each changed cluster. Regime-change difference is `alternative transition count - baseline transition count`; every alternative materially reduces transition count versus baseline.

### Agreement By Year

| Group | 5 sessions | 10 sessions | 20 sessions | 40 sessions | monthly | quarterly |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | 97.04% | 94.81% | 91.85% | 91.11% | 94.07% | 92.59% |
| 2017 | 99.20% | 99.60% | 99.20% | 98.80% | 99.20% | 99.20% |
| 2018 | 74.51% | 69.71% | 67.74% | 68.58% | 71.32% | 70.53% |
| 2019 | 74.21% | 70.63% | 64.68% | 53.97% | 65.87% | 60.71% |
| 2020 | 72.73% | 64.43% | 59.29% | 41.11% | 71.54% | 76.28% |
| 2021 | 82.94% | 81.75% | 78.17% | 72.22% | 78.17% | 80.56% |
| 2022 | 68.53% | 58.57% | 50.20% | 41.43% | 56.97% | 51.00% |
| 2023 | 70.00% | 64.80% | 62.80% | 63.20% | 66.80% | 57.20% |
| 2024 | 54.76% | 45.24% | 47.22% | 52.38% | 36.11% | 33.73% |
| 2025 | 53.60% | 47.20% | 42.40% | 34.00% | 44.80% | 30.80% |
| 2026 | 73.55% | 61.16% | 54.55% | 72.73% | 52.07% | 14.88% |

### Agreement By Symbol

| Group | 5 sessions | 10 sessions | 20 sessions | 40 sessions | monthly | quarterly |
| --- | --- | --- | --- | --- | --- | --- |
| AAPL | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| AMD | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| AMZN | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| DIA | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| GOOGL | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| IWM | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| META | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| MSFT | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| NVDA | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| QID | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| QQQ | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| RWM | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| SDS | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| SH | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| SOXL | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| SOXS | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| SPXU | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| SPY | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| SQQQ | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| TNA | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| TQQQ | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| TSLA | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| TZA | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| UPRO | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLB | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLC | 68.90% | 62.25% | 58.33% | 53.87% | 60.37% | 54.37% |
| XLE | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLF | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLI | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLK | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLP | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLRE | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLU | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLV | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| XLY | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |

### Agreement By Product Scope

| Group | 5 sessions | 10 sessions | 20 sessions | 40 sessions | monthly | quarterly |
| --- | --- | --- | --- | --- | --- | --- |
| broad_market_etf | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| inverse_etf | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| leveraged_inverse_etf | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| leveraged_long_etf | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |
| sector_etf | 73.32% | 67.68% | 64.15% | 60.33% | 66.06% | 61.06% |
| stock | 73.67% | 68.11% | 64.61% | 60.84% | 66.52% | 61.60% |

### Agreement By Market-Regime Period

| Group | 5 sessions | 10 sessions | 20 sessions | 40 sessions | monthly | quarterly |
| --- | --- | --- | --- | --- | --- | --- |
| downtrend_high_vol | 68.80% | 58.46% | 57.15% | 54.17% | 59.95% | 55.05% |
| mixed | 89.33% | 84.46% | 82.01% | 81.23% | 84.48% | 76.16% |
| uptrend_high_vol | 68.97% | 64.14% | 58.32% | 55.05% | 61.01% | 55.20% |
| uptrend_low_vol | 76.93% | 73.01% | 69.80% | 65.00% | 70.76% | 66.67% |

## Cluster Quality Comparison

Baseline date-level distribution: `{'0': 450, '1': 358, '2': 1710}`. Baseline silhouette score on the diagnostic filled regime-input matrix: `0.033`. Baseline transition frequency: `35.60%`. Baseline average duration: `2.81` sessions.

| Schedule | ARI | NMI | Silhouette | Cluster size distribution | Transition frequency | Avg duration sessions |
| --- | --- | --- | --- | --- | --- | --- |
| 5 sessions | 0.357 | 0.198 | 0.032 | {'0': 478, '1': 355, '2': 1685} | 23.48% | 4.25 |
| 10 sessions | 0.273 | 0.121 | 0.046 | {'0': 492, '1': 347, '2': 1679} | 21.18% | 4.72 |
| 20 sessions | 0.208 | 0.085 | 0.042 | {'0': 530, '1': 363, '2': 1625} | 20.42% | 4.89 |
| 40 sessions | 0.168 | 0.069 | 0.021 | {'0': 589, '1': 420, '2': 1509} | 19.67% | 5.08 |
| monthly | 0.251 | 0.107 | 0.025 | {'0': 478, '1': 351, '2': 1689} | 20.14% | 4.96 |
| quarterly | 0.171 | 0.065 | 0.027 | {'0': 547, '1': 293, '2': 1678} | 18.95% | 5.27 |

The low ARI/NMI values and low transition-date agreement show that the scheduled refits are not preserving the current expanding-refit regime behavior.

## Downstream Feature-Impact Table

| Schedule | Feature | Changed values | Mean abs diff | Max abs diff | Correlation |
| --- | --- | --- | --- | --- | --- |
| 5 sessions | market_regime_label | 0 | n/a | n/a | n/a |
| 5 sessions | market_regime_trend_score | 0 | 0.0000 | 0.00 | 1.000 |
| 5 sessions | market_regime_volatility_score | 0 | 0.0000 | 0.00 | 1.000 |
| 5 sessions | market_regime_cluster_expanding | 23,169 | 0.4063 | 2.00 | 0.444 |
| 5 sessions | regime_conditioned_return_20 | 0 | 0.0000 | 0.00 | 1.000 |
| 10 sessions | market_regime_label | 0 | n/a | n/a | n/a |
| 10 sessions | market_regime_trend_score | 0 | 0.0000 | 0.00 | 1.000 |
| 10 sessions | market_regime_volatility_score | 0 | 0.0000 | 0.00 | 1.000 |
| 10 sessions | market_regime_cluster_expanding | 28,063 | 0.4844 | 2.00 | 0.350 |
| 10 sessions | regime_conditioned_return_20 | 0 | 0.0000 | 0.00 | 1.000 |
| 20 sessions | market_regime_label | 0 | n/a | n/a | n/a |
| 20 sessions | market_regime_trend_score | 0 | 0.0000 | 0.00 | 1.000 |
| 20 sessions | market_regime_volatility_score | 0 | 0.0000 | 0.00 | 1.000 |
| 20 sessions | market_regime_cluster_expanding | 31,134 | 0.5378 | 2.00 | 0.296 |
| 20 sessions | regime_conditioned_return_20 | 0 | 0.0000 | 0.00 | 1.000 |
| 40 sessions | market_regime_label | 0 | n/a | n/a | n/a |
| 40 sessions | market_regime_trend_score | 0 | 0.0000 | 0.00 | 1.000 |
| 40 sessions | market_regime_volatility_score | 0 | 0.0000 | 0.00 | 1.000 |
| 40 sessions | market_regime_cluster_expanding | 34,454 | 0.5988 | 2.00 | 0.243 |
| 40 sessions | regime_conditioned_return_20 | 0 | 0.0000 | 0.00 | 1.000 |
| monthly | market_regime_label | 0 | n/a | n/a | n/a |
| monthly | market_regime_trend_score | 0 | 0.0000 | 0.00 | 1.000 |
| monthly | market_regime_volatility_score | 0 | 0.0000 | 0.00 | 1.000 |
| monthly | market_regime_cluster_expanding | 29,461 | 0.5156 | 2.00 | 0.295 |
| monthly | regime_conditioned_return_20 | 0 | 0.0000 | 0.00 | 1.000 |
| quarterly | market_regime_label | 0 | n/a | n/a | n/a |
| quarterly | market_regime_trend_score | 0 | 0.0000 | 0.00 | 1.000 |
| quarterly | market_regime_volatility_score | 0 | 0.0000 | 0.00 | 1.000 |
| quarterly | market_regime_cluster_expanding | 33,798 | 0.6074 | 2.00 | 0.189 |
| quarterly | regime_conditioned_return_20 | 0 | 0.0000 | 0.00 | 1.000 |

Only `market_regime_cluster_expanding` changes. The deterministic regime label, trend score, volatility score, and `regime_conditioned_return_20` remain identical because the alternative schedules only change the KMeans cluster assignment.

### Rows, Symbols, And Dates Most Affected

| Schedule | Symbols most affected | Dates most affected | Sample changed rows |
| --- | --- | --- | --- |
| 5 sessions | AAPL 663, XLE 663, TNA 663, TQQQ 663, TSLA 663 | 2023-02-15 35, 2024-05-14 35, 2024-05-20 35, 2024-05-21 35, 2024-05-23 35 | 2016-06-30 AAPL 2->1; 2016-06-30 AMD 2->1; 2016-06-30 AMZN 2->1; 2016-06-30 DIA 2->1; 2016-06-30 GOOGL 2->1 |
| 10 sessions | AAPL 803, XLE 803, TNA 803, TQQQ 803, TSLA 803 | 2023-01-30 35, 2024-06-24 35, 2024-05-31 35, 2024-06-06 35, 2024-06-07 35 | 2016-06-24 AAPL 2->0; 2016-06-24 AMD 2->0; 2016-06-24 AMZN 2->0; 2016-06-24 DIA 2->0; 2016-06-24 GOOGL 2->0 |
| 20 sessions | AAPL 891, XLE 891, TNA 891, TQQQ 891, TSLA 891 | 2022-11-01 35, 2024-05-22 35, 2024-04-12 35, 2024-04-25 35, 2024-04-26 35 | 2016-06-24 AAPL 2->0; 2016-06-24 AMD 2->0; 2016-06-24 AMZN 2->0; 2016-06-24 DIA 2->0; 2016-06-24 GOOGL 2->0 |
| 40 sessions | AAPL 986, XLE 986, TNA 986, TQQQ 986, TSLA 986 | 2022-07-14 35, 2023-09-13 35, 2023-09-21 35, 2023-09-26 35, 2023-09-29 35 | 2016-06-24 AAPL 2->0; 2016-06-24 AMD 2->0; 2016-06-24 AMZN 2->0; 2016-06-24 DIA 2->0; 2016-06-24 GOOGL 2->0 |
| monthly | AAPL 843, XLE 843, TNA 843, TQQQ 843, TSLA 843 | 2023-03-30 35, 2024-08-13 35, 2024-06-28 35, 2024-07-05 35, 2024-07-08 35 | 2016-06-24 AAPL 2->0; 2016-06-24 AMD 2->0; 2016-06-24 AMZN 2->0; 2016-06-24 DIA 2->0; 2016-06-24 GOOGL 2->0 |
| quarterly | AAPL 967, XLE 967, TNA 967, TQQQ 967, TSLA 967 | 2023-08-16 35, 2024-06-28 35, 2024-08-26 35, 2024-08-27 35, 2024-08-28 35 | 2016-06-24 AAPL 2->0; 2016-06-24 AMD 2->0; 2016-06-24 AMZN 2->0; 2016-06-24 DIA 2->0; 2016-06-24 GOOGL 2->0 |

## Latest-Snapshot Impact

Latest feature date: `2026-06-26`. Operational scanner candidates on the latest scanner date: `25` rows for `2026-06-26`, all using enrolled model `b93b2258c10aea5cef81d291`.

| Schedule | Latest date | Latest cluster diffs | Latest label diffs | Latest conditioned-return diffs | Candidate rows checked | Candidate cluster diffs | Candidate required-feature diffs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 sessions | 2026-06-26 | 0 | 0 | 0 | 25 | 0 | 0 |
| 10 sessions | 2026-06-26 | 0 | 0 | 0 | 25 | 0 | 0 |
| 20 sessions | 2026-06-26 | 35 | 0 | 0 | 25 | 25 | 0 |
| 40 sessions | 2026-06-26 | 0 | 0 | 0 | 25 | 0 | 0 |
| monthly | 2026-06-26 | 0 | 0 | 0 | 25 | 0 | 0 |
| quarterly | 2026-06-26 | 35 | 0 | 0 | 25 | 25 | 0 |

Frozen enrolled-model regime feature usage:

| Head | Required regime features |
| --- | --- |
| expected_return | market_regime_volatility_score, market_regime_trend_score |
| mae | market_regime_volatility_score, market_regime_trend_score |
| mfe | market_regime_trend_score, market_regime_volatility_score |
| primary_positive_return | none |
| target_before_stop | market_regime_volatility_score, market_regime_trend_score |

The enrolled model requires `market_regime_trend_score` and `market_regime_volatility_score` in secondary heads. It does not require `market_regime_cluster_expanding` or `regime_conditioned_return_20`, so the latest scanner candidate rows have zero differences in currently required regime features even when the alternative cluster label differs.

## Positive-Infinity Diagnostic

| Column | Positive infinity count |
| --- | --- |
| volume_trend_20 | 5 |
| volume_expansion_after_compression | 30 |

| Column | Symbol | Dates |
| --- | --- | --- |
| volume_expansion_after_compression | SOXS | 2016-09-29, 2016-09-30, 2016-10-11, 2016-10-12, 2016-10-13, 2016-11-09, 2016-11-10, 2016-11-11, 2016-11-21, 2016-12-01, 2016-12-02, 2016-12-14, 2016-12-15, 2016-12-22, 2016-12-28, 2016-12-29, 2016-12-30, 2017-01-03, 2017-01-12, 2017-01-17, 2017-01-20, 2017-01-24, 2017-01-25, 2017-01-27, 2017-01-30, 2017-01-31, 2017-02-02, 2017-02-03, 2017-03-15, 2017-03-21 |
| volume_trend_20 | SOXS | 2016-09-09, 2016-09-12, 2016-09-13, 2016-09-14, 2016-09-15 |

Total positive infinity values: `35`. Total negative infinity values: `0`. These infinities are in volume-participation features for `SOXS`; they are not produced by the regime KMeans code. Model-matrix nonfinite hygiene exists in `src/swing_rsi/engine/feature_hygiene.py`: positive and negative infinity are replaced with `NaN` before train-fitted imputation, and post-sanitization infinities are rejected. The enrolled model artifact did not expose those hygiene counters in registry `metrics_json`, but the current development source has the explicit sanitizer and training/scanner paths call it before estimator input.

## Operational Immutability Proof

The post-study snapshot below was taken before creating this allowed report file, so Git status could match exactly. After this report is created, the only expected Git status change is `docs/REGIME_KMEANS_REFIT_EQUIVALENCE_STUDY.md`.

| Item | Before | After study / before report |
| --- | --- | --- |
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | clean | clean |
| SQLite hash | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |
| Enrolled model artifact hash | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` |
| Scanner snapshot count | 18 | 18 |
| Ordinary forward-event count | 285 | 285 |
| Final-holdout event count | 25 | 25 |
| Prospective run ID | `3493ee8ac37bf96475c362e1` | `3493ee8ac37bf96475c362e1` |
| Baseline date | `2026-06-25` | `2026-06-25` |
| Run status | `COLLECTING` | `COLLECTING` |

Operational SQLite was opened read-only. No operational mutating command was run.

## Classification And Recommendation

All tested alternatives are classified `TOO_DIFFERENT`.

The runtime reductions are large, but equivalence fails:

- Best row-level agreement is only 73.56% for 5-session refits.
- Best date-level agreement is only 73.67% for 5-session refits.
- Transition-date Jaccard stays near 40-42%.
- ARI ranges from 0.168 to 0.357 and NMI from 0.065 to 0.198.
- The KMeans cluster feature changes in 23,169 to 34,454 feature rows depending on schedule.
- 20-session and quarterly refits change the latest cluster for all 35 latest feature rows and all 25 latest scanner candidate rows, although not in currently required enrolled-model regime features.

Do not implement less frequent KMeans refitting from this study. The current every-date expanding KMeans label sequence is too sensitive to replacing per-date refits with stale-model predictions, even when the stale model is chronology-safe.

## Assumptions Introduced

- Monthly and quarterly schedules refit on the first eligible trading session of the new calendar month or quarter.
- Between refit dates, missing regime-input values are filled with medians computed at the last refit date.
- Cluster-ID alignment uses deterministic majority matching over date-level labels, then applies that mapping to feature rows.
- Market-regime period means the existing deterministic `market_regime_label` bucket.
- Silhouette is diagnostic only and uses the already-built regime-input matrix after median fill; it is not used for fitting or schedule selection.

## Known Limitations

- This study did not retrain models, run discovery, run scanner, run final-holdout-update, run forward-update, update FMP data, or compare model predictions.
- It used the existing built development feature parquet as the input surface, so it evaluates refit-label equivalence for the current manifest rather than rebuilding all upstream features.
- The enrolled model artifact was inspected read-only; its selected features do not include the KMeans cluster, but other historical artifacts may.
- The study did not test warm-start KMeans, centroid anchoring, or cluster identity stabilization.

## Data Leakage Review

- Alternative KMeans models fit only on regime-input rows available through the refit date.
- Predictions between refits use only the last fitted model and last refit-date medians.
- No `label_` columns, future outcomes, development-holdout outcomes, scanner results, forward events, or final-holdout events enter any fit.
- No random shuffling is used.
- The baseline implementation uses same-date close-known market and breadth features, which are available only after the daily close; it does not use future dates.

## Scope Changes

None.

## Tests And Checks Run

- Read-only operational SQLite queries with `sqlite3 -readonly`.
- Read-only operational hash checks with `shasum -a 256`.
- `/tmp/regime_kmeans_refit_study/run_study.py` against existing parquet/model/SQLite artifacts.
- No `pytest`, `ruff`, `mypy`, scanner, discovery, retrain, data update, forward-update, final-holdout-update, or daily-cycle command was run because this was a strict read-only research task and those paths can create repository-local caches, artifacts, or state.

## Next Smallest Engineering Task

Run a read-only cluster-identity stability diagnostic that compares the current every-date expanding KMeans labels against a chronology-safe centroid-anchored daily refit, before attempting any refit-cadence optimization.
