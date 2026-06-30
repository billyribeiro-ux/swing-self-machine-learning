# Sector Rotation BUY ORDINARY Target/Stop Policy Diagnostic

Date: 2026-06-30

Generation reviewed: `signal_discovery_20260629T232550+0000_92147b091ad7`

Confirmed prior diagnostic: `docs/POST_GENERATION_TBS_CALIBRATION_EVIDENCE_REVIEW.md`

Safety label for every conclusion in this report:

Calibration diagnostic only. Not a threshold change and not proof of edge.

## Executive Finding

The current target/stop policy for Sector Rotation BUY in `ORDINARY` scope is classified as:

`STOP_TOO_TIGHT`

The measured evidence points more strongly to stop tightness than to an excessive target or horizon mismatch. Under the current 20-session 2.0 ATR target / 1.0 ATR stop policy, the calibration slice has a 38.41% target-before-stop hit rate, a 60.16% stop-before-target rate, and a 44.51% rate of profitable horizon returns among rows that failed TBS. Stop hits also arrive materially earlier than target hits, with average time to stop of 5.22 sessions versus average time to target of 8.60 sessions.

Widening the stop improved diagnostic policy utility in calibration, and the same directional shape appeared in development holdout. This is not a production policy change. It is evidence for testing an archetype-specific policy candidate under governance.

Exactly one next engineering task:

`implement archetype-specific target/stop policy candidate for Sector Rotation BUY ORDINARY`

## Artifacts Used

- `reports/signal_discovery_calibration_v1/candidates.csv`
- `reports/signal_discovery_calibration_v1/no_signal.csv`
- `reports/signal_discovery_calibration_v1/row_level_calibration_audit.csv`
- `reports/signal_discovery_calibration_v1/analog_robustness.csv`
- `reports/signal_discovery_calibration_v1/blocked_row_analog_summary.csv`
- `reports/signal_discovery_calibration_v1/footprint_evidence.csv`
- `reports/signal_discovery_calibration_v1/score_components.csv`
- `reports/signal_discovery_calibration_v1/calibration_artifact_manifest.json`
- `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`

No discovery, scanner, forward update, final-holdout update, retraining, FMP update, or operational repository mutation was performed.

## Cohort Definition

Filter applied to the latest generation:

- `hypothesis_id = sector_rotation_buy_20d`
- `direction = Bullish`
- `product_class_scope = ORDINARY`
- `no_signal_reason = target_before_stop_probability_below_threshold`

Rows found: 22.

Tickers:

`AMZN`, `XLE`, `XLP`, `AAPL`, `XLY`, `GOOGL`, `XLU`, `XLB`, `XLV`, `XLF`, `XLK`, `MSFT`, `XLI`, `XLC`, `NVDA`, `XLRE`, `SPY`, `IWM`, `TSLA`, `DIA`, `QQQ`, `AMD`

Sector distribution:

- `consumer_discretionary`: 3
- `technology`: 3
- `communication_services`: 2
- `semiconductors`: 2
- all other sectors/scopes represented by one row each: `energy`, `consumer_staples`, `utilities`, `materials`, `health_care`, `financials`, `industrials`, `real_estate`, `broad_market`, `small_caps`, `industrials_large_cap`, `technology_growth`

Regime distribution:

- `uptrend_high_vol`: 22

Signal score distribution:

- min 0.439601
- p25 0.474320
- median 0.505474
- p75 0.517748
- max 0.546596
- mean 0.498998

Expected return distribution:

- min -0.027032
- p25 -0.001847
- median 0.006252
- p75 0.009760
- max 0.015290
- mean 0.003664

TBS probability distribution:

- min 0.342636
- p25 0.352071
- median 0.353828
- p75 0.358930
- max 0.394651
- mean 0.359324

Current rejection reason:

- `target_before_stop_probability_below_threshold`: 22

## Cohort Rows

| Ticker | Sector | Regime | Score | TBS p | Exp ret | Exp MFE | Exp MAE | OOD | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AMZN | consumer_discretionary | uptrend_high_vol | 0.5466 | 0.3947 | 0.0142 | 0.0923 | -0.0900 | 0.0208 | target_before_stop_probability_below_threshold |
| XLE | energy | uptrend_high_vol | 0.5368 | 0.3589 | 0.0153 | 0.0462 | -0.0395 | 0.0208 | target_before_stop_probability_below_threshold |
| XLP | consumer_staples | uptrend_high_vol | 0.5326 | 0.3538 | 0.0153 | 0.0431 | -0.0395 | 0.0208 | target_before_stop_probability_below_threshold |
| AAPL | technology | uptrend_high_vol | 0.5294 | 0.3589 | 0.0098 | 0.0862 | -0.0791 | 0.0208 | target_before_stop_probability_below_threshold |
| XLY | consumer_discretionary | uptrend_high_vol | 0.5220 | 0.3947 | 0.0131 | 0.0528 | -0.0675 | 0.0208 | target_before_stop_probability_below_threshold |
| GOOGL | communication_services | uptrend_high_vol | 0.5186 | 0.3521 | 0.0067 | 0.1048 | -0.0970 | 0.0208 | target_before_stop_probability_below_threshold |
| XLU | utilities | uptrend_high_vol | 0.5151 | 0.3538 | 0.0098 | 0.0444 | -0.0429 | 0.0208 | target_before_stop_probability_below_threshold |
| XLB | materials | uptrend_high_vol | 0.5138 | 0.3589 | 0.0086 | 0.0605 | -0.0592 | 0.0208 | target_before_stop_probability_below_threshold |
| XLV | health_care | uptrend_high_vol | 0.5121 | 0.3521 | 0.0098 | 0.0561 | -0.0613 | 0.0208 | target_before_stop_probability_below_threshold |
| XLF | financials | uptrend_high_vol | 0.5086 | 0.3538 | 0.0098 | 0.0437 | -0.0506 | 0.0208 | target_before_stop_probability_below_threshold |
| XLK | technology | uptrend_high_vol | 0.5057 | 0.3947 | -0.0027 | 0.1211 | -0.0903 | 0.0208 | target_before_stop_probability_below_threshold |
| MSFT | technology | uptrend_high_vol | 0.5053 | 0.3521 | 0.0001 | 0.1118 | -0.0901 | 0.0208 | target_before_stop_probability_below_threshold |
| XLI | industrials | uptrend_high_vol | 0.5046 | 0.3579 | 0.0065 | 0.0624 | -0.0683 | 0.0208 | target_before_stop_probability_below_threshold |
| XLC | communication_services | uptrend_high_vol | 0.4980 | 0.3521 | 0.0061 | 0.0456 | -0.0525 | 0.0208 | target_before_stop_probability_below_threshold |
| NVDA | semiconductors | uptrend_high_vol | 0.4908 | 0.3589 | -0.0027 | 0.1055 | -0.1066 | 0.0208 | target_before_stop_probability_below_threshold |
| XLRE | real_estate | uptrend_high_vol | 0.4899 | 0.3521 | 0.0040 | 0.0486 | -0.0532 | 0.0208 | target_before_stop_probability_below_threshold |
| SPY | broad_market | uptrend_high_vol | 0.4691 | 0.3538 | 0.0022 | 0.0436 | -0.0730 | 0.0208 | target_before_stop_probability_below_threshold |
| IWM | small_caps | uptrend_high_vol | 0.4674 | 0.3538 | 0.0033 | 0.0488 | -0.0855 | 0.0208 | target_before_stop_probability_below_threshold |
| TSLA | consumer_discretionary | uptrend_high_vol | 0.4668 | 0.3538 | -0.0108 | 0.1365 | -0.1207 | 0.0208 | target_before_stop_probability_below_threshold |
| DIA | industrials_large_cap | uptrend_high_vol | 0.4539 | 0.3426 | -0.0025 | 0.0372 | -0.0644 | 0.0208 | target_before_stop_probability_below_threshold |
| QQQ | technology_growth | uptrend_high_vol | 0.4511 | 0.3589 | -0.0079 | 0.0717 | -0.0931 | 0.0417 | target_before_stop_probability_below_threshold |
| AMD | semiconductors | uptrend_high_vol | 0.4396 | 0.3426 | -0.0270 | 0.1510 | -0.2004 | 0.0208 | target_before_stop_probability_below_threshold |

Scope checks for prior known rows:

| Row | Product scope | Status |
| --- | --- | --- |
| AMZN `sector_rotation_buy_20d` | `ORDINARY` | included |
| TZA `sector_rotation_buy_20d` | `LEVERAGED_INVERSE` | excluded from ORDINARY diagnostic |
| SQQQ `sector_rotation_buy_20d` | `LEVERAGED_INVERSE` | excluded from ORDINARY diagnostic |
| RWM `sector_rotation_buy_20d` | `INVERSE` | excluded from ORDINARY diagnostic |
| QID `sector_rotation_buy_20d` | `LEVERAGED_INVERSE` | excluded from ORDINARY diagnostic |

## Current Policy Baseline

Current label policy inspected from `src/swing_rsi/engine/labels.py`:

- Target definition: bullish target is next-session open entry plus `ATR(14) * 2.0`.
- Stop definition: bullish stop is next-session open entry minus `ATR(14) * 1.0`.
- ATR multiple: target 2.0 ATR, stop 1.0 ATR.
- ATR calculation: Wilder-style EWM true range using prior close, length 14.
- Entry timing: next trading session open.
- Signal-known timing: signal row is known at daily close; the row is not fillable at that same close.
- Horizon: `sector_rotation_buy_20d` uses 20 sessions.
- Time-exit behavior: unresolved labels use the horizon close for forward return diagnostics.
- Same-bar ambiguity rule: target wins only if target hit time is strictly before stop hit time; stop wins if stop hit time is less than or equal to target hit time.
- Transaction cost treatment in signal-discovery scoring: 5 bps round trip cost, deducted as 0.0005 where cost-adjusted utility is available.
- Portfolio backtest slippage setting: 2 bps in `PortfolioBacktestConfig`, but the TBS calibration label itself is ATR first-touch based and does not include slippage.

For the Sector Rotation BUY ORDINARY calibration cohort, the current policy baseline is:

| Metric | Value |
| --- | --- |
| Calibration rows | 11,017 |
| Target-before-stop hit rate | 0.3841 |
| Stop-before-target rate | 0.6016 |
| Unresolved/time-exit rate | 0.0143 |
| Average forward return | 0.0187 |
| Median forward return | 0.0164 |
| Average MFE | 0.0665 |
| Average MAE | -0.0495 |
| Worst MAE | -0.4508 |
| Average time to target | 8.6008 sessions |
| Average time to stop | 5.2191 sessions |
| Average time to max favorable excursion | Not persisted directly; MFE was computed over the horizon path |
| Average time to max adverse excursion | Not persisted directly; MAE was computed over the horizon path |
| Profitable time-exit rate among unresolved rows | 0.7389 |
| Profitable at horizon despite failing TBS | 0.4451 |
| Stop-before-target rows later positive at horizon | 0.4381 |
| Expected R under current policy | 0.1745 |
| Policy average return | 0.0041 |
| Cost-adjusted utility | 0.0036 |

Interpretation: the current target is not simply unreachable; rather, the stop is frequently reached earlier while a large minority of failed-TBS rows still show positive horizon returns.

## Calibration-Only Policy Grid

Calibration-only split:

- train: 51,332 rows, `2016-06-20` through `2022-05-05`
- calibration: 16,765 pooled rows, `2022-06-06` through `2024-05-01`
- holdout: 17,465 pooled rows, `2024-05-31` through `2026-05-28`
- calibration ORDINARY rows: 11,017
- calibration ORDINARY symbols: 23

All policy-grid rows below use calibration data only. The grid uses existing OHLCV/ATR paths and the same target-before-stop first-touch semantics as the current label code.

For each matrix cell: `target_before_stop_hit_rate / cost_adjusted_utility`.

All rows in the calibration grid share:

- sample count: 11,017
- symbol concentration: 0.0435
- year concentration: 0.5219
- regime concentration: 0.3612

Forward/MFE/MAE path distributions by horizon:

| Horizon | Avg forward | Median forward | Avg MFE | Avg MAE | Worst MAE |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 0.0037 | 0.0038 | 0.0290 | -0.0256 | -0.2968 |
| 10 | 0.0087 | 0.0089 | 0.0437 | -0.0357 | -0.3781 |
| 20 | 0.0187 | 0.0164 | 0.0665 | -0.0495 | -0.4508 |

### Current Policy Slice

| horizon | target | stop_mult | n | tbs | stop_rate | unresolved | avg_forward | med_forward | avg_mfe | avg_mae | worst_mae | avg_time_target | avg_time_stop | expected_r | utility | profitable_time_exit_rate | profitable_failed_tbs_rate | stop_before_positive_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 2.0000 | 1.0000 | 11017 | 0.1819 | 0.4508 | 0.3673 | 0.0037 | 0.0038 | 0.0290 | -0.0256 | -0.2968 | 3.6360 | 2.6472 | 0.1229 | 0.0023 | 0.7823 | 0.4684 | 0.2126 |
| 10 | 2.0000 | 1.0000 | 11017 | 0.3227 | 0.5584 | 0.1189 | 0.0087 | 0.0089 | 0.0437 | -0.0357 | -0.3781 | 5.7698 | 3.7145 | 0.1638 | 0.0032 | 0.8000 | 0.4246 | 0.3446 |
| 20 | 2.0000 | 1.0000 | 11017 | 0.3841 | 0.6016 | 0.0143 | 0.0187 | 0.0164 | 0.0665 | -0.0495 | -0.4508 | 8.6008 | 5.2191 | 0.1745 | 0.0036 | 0.7389 | 0.4451 | 0.4381 |

### Complete Calibration Grid, 5 Sessions

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.420/0.0002 | 0.511/0.0003 | 0.565/0.0005 | 0.596/0.0007 | 0.614/0.0009 | 0.627/0.0012 |
| 1.0 | 0.348/0.0005 | 0.425/0.0007 | 0.469/0.0010 | 0.494/0.0012 | 0.507/0.0014 | 0.517/0.0017 |
| 1.25 | 0.285/0.0007 | 0.348/0.0011 | 0.382/0.0014 | 0.399/0.0017 | 0.409/0.0018 | 0.417/0.0022 |
| 1.5 | 0.231/0.0010 | 0.280/0.0014 | 0.305/0.0018 | 0.318/0.0021 | 0.325/0.0023 | 0.331/0.0026 |
| 2.0 | 0.143/0.0013 | 0.170/0.0019 | 0.182/0.0023 | 0.188/0.0026 | 0.192/0.0028 | 0.194/0.0032 |
| 2.5 | 0.077/0.0013 | 0.092/0.0019 | 0.098/0.0023 | 0.101/0.0027 | 0.103/0.0029 | 0.104/0.0032 |
| 3.0 | 0.041/0.0014 | 0.048/0.0021 | 0.051/0.0025 | 0.052/0.0028 | 0.053/0.0030 | 0.054/0.0034 |

### Complete Calibration Grid, 10 Sessions

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.424/0.0002 | 0.526/0.0004 | 0.598/0.0007 | 0.651/0.0010 | 0.689/0.0014 | 0.737/0.0021 |
| 1.0 | 0.364/0.0006 | 0.460/0.0009 | 0.532/0.0013 | 0.584/0.0017 | 0.620/0.0021 | 0.663/0.0029 |
| 1.25 | 0.318/0.0009 | 0.409/0.0014 | 0.475/0.0019 | 0.523/0.0025 | 0.555/0.0030 | 0.592/0.0039 |
| 1.5 | 0.284/0.0012 | 0.367/0.0019 | 0.424/0.0024 | 0.465/0.0031 | 0.493/0.0037 | 0.524/0.0047 |
| 2.0 | 0.221/0.0018 | 0.283/0.0026 | 0.323/0.0032 | 0.351/0.0041 | 0.370/0.0047 | 0.391/0.0057 |
| 2.5 | 0.161/0.0022 | 0.204/0.0031 | 0.232/0.0037 | 0.249/0.0045 | 0.261/0.0052 | 0.274/0.0062 |
| 3.0 | 0.113/0.0026 | 0.141/0.0036 | 0.159/0.0043 | 0.168/0.0051 | 0.176/0.0058 | 0.184/0.0069 |

### Complete Calibration Grid, 20 Sessions

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.424/0.0002 | 0.526/0.0004 | 0.599/0.0006 | 0.656/0.0010 | 0.700/0.0014 | 0.762/0.0021 |
| 1.0 | 0.364/0.0006 | 0.462/0.0009 | 0.537/0.0013 | 0.597/0.0018 | 0.642/0.0022 | 0.710/0.0031 |
| 1.25 | 0.320/0.0009 | 0.415/0.0014 | 0.488/0.0019 | 0.549/0.0026 | 0.595/0.0031 | 0.663/0.0041 |
| 1.5 | 0.289/0.0013 | 0.379/0.0019 | 0.448/0.0025 | 0.507/0.0033 | 0.552/0.0039 | 0.618/0.0050 |
| 2.0 | 0.243/0.0020 | 0.323/0.0029 | 0.384/0.0036 | 0.438/0.0047 | 0.480/0.0055 | 0.537/0.0068 |
| 2.5 | 0.205/0.0025 | 0.274/0.0037 | 0.327/0.0045 | 0.373/0.0057 | 0.407/0.0066 | 0.454/0.0080 |
| 3.0 | 0.175/0.0031 | 0.233/0.0045 | 0.277/0.0055 | 0.314/0.0069 | 0.341/0.0079 | 0.376/0.0094 |

### Complete Calibration Grid, Stop Rate

5 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.573 | 0.465 | 0.378 | 0.303 | 0.241 | 0.141 |
| 1.0 | 0.627 | 0.514 | 0.417 | 0.331 | 0.262 | 0.152 |
| 1.25 | 0.658 | 0.540 | 0.436 | 0.345 | 0.272 | 0.158 |
| 1.5 | 0.673 | 0.552 | 0.445 | 0.352 | 0.276 | 0.160 |
| 2.0 | 0.683 | 0.560 | 0.451 | 0.355 | 0.279 | 0.161 |
| 2.5 | 0.688 | 0.563 | 0.454 | 0.357 | 0.280 | 0.162 |
| 3.0 | 0.689 | 0.564 | 0.454 | 0.358 | 0.280 | 0.162 |

10 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.576 | 0.474 | 0.400 | 0.339 | 0.289 | 0.208 |
| 1.0 | 0.636 | 0.537 | 0.458 | 0.391 | 0.335 | 0.240 |
| 1.25 | 0.678 | 0.580 | 0.500 | 0.428 | 0.365 | 0.262 |
| 1.5 | 0.707 | 0.611 | 0.529 | 0.452 | 0.385 | 0.274 |
| 2.0 | 0.741 | 0.644 | 0.558 | 0.475 | 0.404 | 0.286 |
| 2.5 | 0.757 | 0.659 | 0.571 | 0.487 | 0.414 | 0.293 |
| 3.0 | 0.761 | 0.664 | 0.575 | 0.490 | 0.417 | 0.295 |

20 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.576 | 0.474 | 0.401 | 0.344 | 0.299 | 0.232 |
| 1.0 | 0.636 | 0.538 | 0.463 | 0.402 | 0.355 | 0.279 |
| 1.25 | 0.680 | 0.585 | 0.511 | 0.447 | 0.398 | 0.317 |
| 1.5 | 0.711 | 0.620 | 0.549 | 0.486 | 0.436 | 0.349 |
| 2.0 | 0.755 | 0.670 | 0.602 | 0.536 | 0.482 | 0.387 |
| 2.5 | 0.786 | 0.704 | 0.636 | 0.569 | 0.513 | 0.414 |
| 3.0 | 0.799 | 0.719 | 0.651 | 0.583 | 0.527 | 0.426 |

### Complete Calibration Grid, Unresolved Rate

5 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.007 | 0.023 | 0.057 | 0.101 | 0.145 | 0.231 |
| 1.0 | 0.025 | 0.061 | 0.114 | 0.175 | 0.231 | 0.331 |
| 1.25 | 0.057 | 0.113 | 0.182 | 0.255 | 0.319 | 0.425 |
| 1.5 | 0.096 | 0.169 | 0.250 | 0.330 | 0.398 | 0.509 |
| 2.0 | 0.174 | 0.270 | 0.367 | 0.456 | 0.530 | 0.644 |
| 2.5 | 0.234 | 0.345 | 0.448 | 0.542 | 0.617 | 0.734 |
| 3.0 | 0.270 | 0.388 | 0.496 | 0.590 | 0.667 | 0.784 |

10 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.000 | 0.001 | 0.003 | 0.010 | 0.021 | 0.055 |
| 1.0 | 0.000 | 0.003 | 0.010 | 0.024 | 0.045 | 0.096 |
| 1.25 | 0.004 | 0.010 | 0.025 | 0.049 | 0.079 | 0.146 |
| 1.5 | 0.009 | 0.022 | 0.047 | 0.083 | 0.122 | 0.202 |
| 2.0 | 0.038 | 0.073 | 0.119 | 0.174 | 0.225 | 0.322 |
| 2.5 | 0.082 | 0.137 | 0.197 | 0.265 | 0.325 | 0.433 |
| 3.0 | 0.126 | 0.196 | 0.266 | 0.342 | 0.407 | 0.521 |

20 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.000 | 0.000 | 0.000 | 0.000 | 0.001 | 0.005 |
| 1.0 | 0.000 | 0.000 | 0.000 | 0.001 | 0.003 | 0.011 |
| 1.25 | 0.000 | 0.000 | 0.001 | 0.004 | 0.007 | 0.021 |
| 1.5 | 0.000 | 0.001 | 0.003 | 0.007 | 0.013 | 0.033 |
| 2.0 | 0.002 | 0.007 | 0.014 | 0.026 | 0.038 | 0.076 |
| 2.5 | 0.009 | 0.022 | 0.037 | 0.058 | 0.080 | 0.132 |
| 3.0 | 0.026 | 0.048 | 0.073 | 0.103 | 0.132 | 0.198 |

### Complete Calibration Grid, Expected R

5 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.029 | 0.037 | 0.044 | 0.051 | 0.055 | 0.068 |
| 1.0 | 0.041 | 0.052 | 0.062 | 0.072 | 0.077 | 0.089 |
| 1.25 | 0.051 | 0.066 | 0.079 | 0.091 | 0.096 | 0.109 |
| 1.5 | 0.064 | 0.084 | 0.099 | 0.111 | 0.117 | 0.129 |
| 2.0 | 0.083 | 0.106 | 0.123 | 0.136 | 0.143 | 0.156 |
| 2.5 | 0.081 | 0.107 | 0.125 | 0.138 | 0.146 | 0.159 |
| 3.0 | 0.084 | 0.111 | 0.129 | 0.142 | 0.150 | 0.164 |

10 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.030 | 0.039 | 0.048 | 0.062 | 0.076 | 0.106 |
| 1.0 | 0.046 | 0.058 | 0.074 | 0.093 | 0.108 | 0.142 |
| 1.25 | 0.060 | 0.080 | 0.100 | 0.123 | 0.143 | 0.180 |
| 1.5 | 0.077 | 0.104 | 0.123 | 0.149 | 0.170 | 0.210 |
| 2.0 | 0.107 | 0.141 | 0.164 | 0.196 | 0.220 | 0.262 |
| 2.5 | 0.122 | 0.160 | 0.186 | 0.217 | 0.242 | 0.285 |
| 3.0 | 0.141 | 0.182 | 0.209 | 0.242 | 0.270 | 0.313 |

20 sessions:

| target/stop | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.75 | 0.030 | 0.039 | 0.048 | 0.062 | 0.075 | 0.104 |
| 1.0 | 0.046 | 0.058 | 0.074 | 0.094 | 0.109 | 0.145 |
| 1.25 | 0.060 | 0.080 | 0.100 | 0.127 | 0.145 | 0.187 |
| 1.5 | 0.077 | 0.103 | 0.124 | 0.155 | 0.174 | 0.222 |
| 2.0 | 0.110 | 0.147 | 0.174 | 0.219 | 0.250 | 0.308 |
| 2.5 | 0.130 | 0.177 | 0.214 | 0.264 | 0.303 | 0.365 |
| 3.0 | 0.159 | 0.218 | 0.262 | 0.318 | 0.361 | 0.427 |

### Highest Calibration Utility Shapes

| horizon | target | stop_mult | n | tbs | stop_rate | unresolved | avg_forward | med_forward | avg_mfe | avg_mae | worst_mae | expected_r | policy_return | utility | symbol_conc | year_conc | regime_conc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 3.0000 | 2.0000 | 11017 | 0.3762 | 0.4258 | 0.1980 | 0.0187 | 0.0164 | 0.0665 | -0.0495 | -0.4508 | 0.4268 | 0.0099 | 0.0094 | 0.0435 | 0.5219 | 0.3612 |
| 20 | 2.5000 | 2.0000 | 11017 | 0.4538 | 0.4138 | 0.1323 | 0.0187 | 0.0164 | 0.0665 | -0.0495 | -0.4508 | 0.3649 | 0.0085 | 0.0080 | 0.0435 | 0.5219 | 0.3612 |
| 20 | 3.0000 | 1.5000 | 11017 | 0.3413 | 0.5267 | 0.1320 | 0.0187 | 0.0164 | 0.0665 | -0.0495 | -0.4508 | 0.3608 | 0.0084 | 0.0079 | 0.0435 | 0.5219 | 0.3612 |
| 20 | 3.0000 | 1.2500 | 11017 | 0.3140 | 0.5835 | 0.1026 | 0.0187 | 0.0164 | 0.0665 | -0.0495 | -0.4508 | 0.3185 | 0.0074 | 0.0069 | 0.0435 | 0.5219 | 0.3612 |
| 10 | 3.0000 | 2.0000 | 11017 | 0.1839 | 0.2949 | 0.5212 | 0.0087 | 0.0089 | 0.0437 | -0.0357 | -0.3781 | 0.3127 | 0.0074 | 0.0069 | 0.0435 | 0.5219 | 0.3612 |
| 20 | 2.0000 | 2.0000 | 11017 | 0.5369 | 0.3874 | 0.0757 | 0.0187 | 0.0164 | 0.0665 | -0.0495 | -0.4508 | 0.3077 | 0.0073 | 0.0068 | 0.0435 | 0.5219 | 0.3612 |

## Development-Holdout Diagnostic Comparison

All results in this section are labeled:

`DEVELOPMENT_HOLDOUT_DIAGNOSTIC_ONLY`

The development holdout was used only to compare whether calibration-observed shapes generalize directionally. It was not used to select a production policy.

Development-holdout ORDINARY rows:

- rows: 11,477
- dates: `2024-05-31` through `2026-05-28`
- symbols: 23

Current policy in development holdout:

| Metric | Value |
| --- | --- |
| Target-before-stop hit rate | 0.3642 |
| Stop-before-target rate | 0.6153 |
| Unresolved/time-exit rate | 0.0205 |
| Average forward return | 0.0162 |
| Median forward return | 0.0121 |
| Average MFE | 0.0604 |
| Average MAE | -0.0484 |
| Worst MAE | -0.3997 |
| Average time to target | 8.8559 sessions |
| Average time to stop | 5.3412 sessions |
| Profitable time-exit rate | 0.8426 |
| Profitable despite failed TBS | 0.4594 |
| Stop-before-target rows later positive at horizon | 0.4466 |
| Cost-adjusted utility | 0.0031 |

Directional comparison:

| horizon | target | stop_mult | tbs_cal | stop_rate_cal | unresolved_cal | utility_cal | tbs_hold | stop_rate_hold | unresolved_hold | utility_hold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 2.0000 | 1.0000 | 0.1819 | 0.4508 | 0.3673 | 0.0023 | 0.1696 | 0.4589 | 0.3714 | 0.0021 |
| 10 | 2.0000 | 1.0000 | 0.3227 | 0.5584 | 0.1189 | 0.0032 | 0.3016 | 0.5674 | 0.1310 | 0.0029 |
| 10 | 2.0000 | 2.0000 | 0.3912 | 0.2865 | 0.3223 | 0.0057 | 0.3631 | 0.3144 | 0.3226 | 0.0038 |
| 10 | 2.5000 | 2.0000 | 0.2740 | 0.2933 | 0.4327 | 0.0062 | 0.2593 | 0.3223 | 0.4184 | 0.0043 |
| 10 | 3.0000 | 2.0000 | 0.1839 | 0.2949 | 0.5212 | 0.0069 | 0.1782 | 0.3253 | 0.4965 | 0.0048 |
| 20 | 2.0000 | 1.0000 | 0.3841 | 0.6016 | 0.0143 | 0.0036 | 0.3642 | 0.6153 | 0.0205 | 0.0031 |
| 20 | 2.0000 | 2.0000 | 0.5369 | 0.3874 | 0.0757 | 0.0068 | 0.5004 | 0.4074 | 0.0922 | 0.0048 |
| 20 | 2.5000 | 2.0000 | 0.4538 | 0.4138 | 0.1323 | 0.0080 | 0.4149 | 0.4335 | 0.1516 | 0.0059 |
| 20 | 3.0000 | 2.0000 | 0.3762 | 0.4258 | 0.1980 | 0.0094 | 0.3393 | 0.4474 | 0.2133 | 0.0068 |

Policy shapes that remained directionally consistent:

- 20-session wider-stop shapes stayed better than the current 2.0/1.0 policy by diagnostic utility.
- 10-session wider-stop shapes also retained positive utility, but below the best 20-session shapes.
- The current 20-session horizon remains directionally viable; the issue is not that the horizon is obviously too short or too long.

Policy shapes that failed:

| horizon | target | stop_mult | utility_cal | utility_hold | tbs_cal | tbs_hold |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | 0.7500 | 0.5000 | 0.0002 | -0.0002 | 0.4198 | 0.3996 |
| 10 | 0.7500 | 0.5000 | 0.0002 | -0.0002 | 0.4243 | 0.4060 |
| 20 | 0.7500 | 0.5000 | 0.0002 | -0.0002 | 0.4243 | 0.4060 |

Unstable or too concentrated shapes:

- No top calibration shape was dominated by one symbol; symbol concentration stayed at 0.0435.
- Year concentration stayed material at 0.5219 in calibration and 0.5010 for the current holdout baseline, so results should remain governance-only rather than production proof.
- Regime concentration is not extreme in calibration at 0.3612, but the current live cohort is entirely `uptrend_high_vol`, so prospective confirmation is still needed.

## Top-Row Path Analysis

The top blocked rows are as-of `2026-06-26`. The persisted modeling artifact ends on that date, so next-session entry and post-signal path outcomes are not available in existing artifacts.

Therefore, for current top rows:

- executable entry price: `N/A_next_session_open_not_persisted_for_unmatured_current_row`
- current executable target price: `N/A`
- current executable stop price: `N/A`
- MFE path after signal: `N/A`
- MAE path after signal: `N/A`
- did target hit: `N/A`
- did stop hit: `N/A`
- time to target: `N/A`
- time to stop: `N/A`
- time-exit return: `N/A`
- profitable at horizon despite failing TBS: `N/A`
- stop before eventual recovery: `N/A`
- target missed but forward return favorable: `N/A`

The table below uses signal-date `Open` and `ATR(14)` only as non-executable context. It is not a same-day fill assumption.

| Ticker | Date | Score | TBS p | Exp ret | Exp MFE | Exp MAE | Signal Open | Signal ATR14 | Ref target from signal open | Ref stop from signal open |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AMZN | 2026-06-26 | 0.5466 | 0.3947 | 0.0142 | 0.0923 | -0.0900 | 227.2100 | 7.9427 | 243.0954 | 219.2673 |
| XLE | 2026-06-26 | 0.5368 | 0.3589 | 0.0153 | 0.0462 | -0.0395 | 54.0000 | 1.2512 | 56.5024 | 52.7488 |
| XLP | 2026-06-26 | 0.5326 | 0.3538 | 0.0153 | 0.0431 | -0.0395 | 84.6500 | 1.2446 | 87.1391 | 83.4054 |
| AAPL | 2026-06-26 | 0.5294 | 0.3589 | 0.0098 | 0.0862 | -0.0791 | 275.0000 | 8.1581 | 291.3161 | 266.8419 |
| XLY | 2026-06-26 | 0.5220 | 0.3947 | 0.0131 | 0.0528 | -0.0675 | 113.2000 | 2.2261 | 117.6521 | 110.9739 |
| GOOGL | 2026-06-26 | 0.5186 | 0.3521 | 0.0067 | 0.1048 | -0.0970 | 342.5500 | 11.8830 | 366.3160 | 330.6670 |
| XLU | 2026-06-26 | 0.5151 | 0.3538 | 0.0098 | 0.0444 | -0.0429 | 46.0000 | 0.6743 | 47.3487 | 45.3257 |
| XLB | 2026-06-26 | 0.5138 | 0.3589 | 0.0086 | 0.0605 | -0.0592 | 51.5700 | 0.8928 | 53.3557 | 50.6772 |
| XLV | 2026-06-26 | 0.5121 | 0.3521 | 0.0098 | 0.0561 | -0.0613 | 156.3200 | 2.5844 | 161.4888 | 153.7356 |
| XLF | 2026-06-26 | 0.5086 | 0.3538 | 0.0098 | 0.0437 | -0.0506 | 53.5600 | 0.7512 | 55.0623 | 52.8088 |
| XLK | 2026-06-26 | 0.5057 | 0.3947 | -0.0027 | 0.1211 | -0.0903 | 181.0000 | 5.7853 | 192.5706 | 175.2147 |
| MSFT | 2026-06-26 | 0.5053 | 0.3521 | 0.0001 | 0.1118 | -0.0901 | 357.1500 | 13.2088 | 383.5675 | 343.9412 |

## Target/Stop Mismatch Classification

Classification:

`STOP_TOO_TIGHT`

Measured basis:

- Current 20-session policy has stop-before-target rate 0.6016 versus target-before-stop rate 0.3841.
- Current average time to stop is 5.2191 sessions; average time to target is 8.6008 sessions.
- 44.51% of rows that failed TBS were profitable at the 20-session horizon.
- 43.81% of stop-before-target rows later had positive 20-session forward return.
- Widening the stop from 1.0 ATR to 2.0 ATR improves calibration utility:
  - 20d 2.0/1.0: 0.0036
  - 20d 2.0/2.0: 0.0068
  - 20d 2.5/2.0: 0.0080
  - 20d 3.0/2.0: 0.0094
- Development-holdout diagnostics show the same direction:
  - 20d 2.0/1.0: 0.0031
  - 20d 2.0/2.0: 0.0048
  - 20d 2.5/2.0: 0.0059
  - 20d 3.0/2.0: 0.0068

Rejected classifications:

- `CURRENT_POLICY_VALID`: rejected because stop-before-target frequency and positive failed-TBS horizon returns indicate the current stop may be interrupting otherwise favorable paths.
- `TARGET_TOO_FAR`: rejected as the primary diagnosis because smaller targets raise TBS hit rates but do not produce the strongest utility; wider stops dominate the top utility table.
- `HORIZON_MISMATCH`: rejected because 20-session diagnostics remain strongest and directionally consistent.
- `TIME_EXIT_MORE_RELEVANT_THAN_TBS`: partially present but not the most specific classification. Time-exit returns support the stop-tightness interpretation.
- `ARCHETYPE_NOT_VIABLE`: rejected because multiple calibration-only policy shapes show positive utility and directionally consistent holdout behavior.
- `INSUFFICIENT_EVIDENCE`: rejected for this diagnostic because calibration has 11,017 ORDINARY rows across 23 symbols.
- `IMPLEMENTATION_DEFECT`: rejected because no target/stop calculation bug was proven.

## Analog And Footprint Comparison

Only AMZN from this exact ORDINARY Sector Rotation BUY TBS-blocked cohort was selected into the robust analog exports.

AMZN analog summary:

| Metric | Value |
| --- | --- |
| Analog count | 10 |
| Average forward return | 0.0029 |
| Median forward return | 0.0093 |
| Win rate | 0.6000 |
| Target-before-stop hit rate | 0.0000 |
| Average MFE | 0.0375 |
| Average MAE | -0.1370 |
| Worst MAE | -0.2355 |
| Original analog label | `MIXED` |
| Robust analog label | `MIXED_SUPPORT` |
| Caution flags | `same_year_concentration;same_regime_concentration;high_return_dispersion;high_mae_tail_risk` |
| Research usable | true |
| Too concentrated | true |

Interpretation:

- The AMZN analogs do not prove TBS support. Their top-depth TBS hit rate is weak despite positive median forward return.
- This is compatible with the target/stop-policy mismatch finding: analog outcomes can show forward-return support while TBS remains weak.
- Analog evidence does not override gates.

Footprint evidence:

- All 22 cohort rows have `NO_SIGNAL decision` footprint evidence.
- Evidence type is `neutral`.
- Strength is `moderate`.
- Claim: `No-signal rows preserve the blocking reason.`

Residual/unexplained score:

- No residual or unexplained score component was persisted in `score_components.csv`.
- Available score components include direction probability, target-before-stop probability, expected return, expected MFE, expected MAE, risk-adjusted utility, OOD penalty, liquidity score, footprint support score, conflict penalty, concentration penalty, and final signal score.

Conclusion: analog and footprint evidence supports a cautious interpretation. It does not contradict the target/stop mismatch diagnosis, but it also does not provide robust permission to bypass the TBS gate.

## Root Diagnostic Answer

For Sector Rotation BUY ORDINARY:

1. Current target too far: not the primary cause.
2. Current stop too tight: supported.
3. Current horizon too short or too long: not supported; 20 sessions remains directionally viable.
4. Early adverse movement before eventual favorable return: supported by high stop-before-positive-horizon rate.
5. Time-exit return positive when TBS fails: supported for 44.51% of failed-TBS rows.
6. Different target/stop profile required: supported as a candidate for controlled evaluation only.
7. Archetype lacks enough evidence: not supported for this diagnostic slice, though prospective validation is still required.

## Next Engineering Task

Exactly one next engineering task:

`implement archetype-specific target/stop policy candidate for Sector Rotation BUY ORDINARY`

The candidate should be evaluated under calibration-only governance and prospective evidence collection. It must not alter production gates, thresholds, OOD governance, live signal creation, or model promotion by itself.

## Immutability Report

Development repository before/after state:

| Item | Before | After |
| --- | --- | --- |
| HEAD | `56171ad831ccec53348c2a2b18c37f4ef057e231` | `56171ad831ccec53348c2a2b18c37f4ef057e231` |
| Git status | `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1` | `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1`; `?? docs/SECTOR_ROTATION_BUY_ORDINARY_TARGET_STOP_DIAGNOSTIC.md` |
| SQLite path | `state/engine.sqlite3` | `state/engine.sqlite3` |
| SQLite size | 385,888,256 bytes | 385,888,256 bytes |
| SQLite mtime_ns | 1782583720016271553 | 1782583720016271553 |
| SQLite sha256 | `5646a5cb4abc0a4260e83f1c311a93c55267c5b622862807f78a2458d14a98bb` | `5646a5cb4abc0a4260e83f1c311a93c55267c5b622862807f78a2458d14a98bb` |
| Representative artifact | `reports/signal_discovery_calibration_v1/calibration_artifact_manifest.json` | `reports/signal_discovery_calibration_v1/calibration_artifact_manifest.json` |
| Representative artifact size | 1,629 bytes | 1,629 bytes |
| Representative artifact mtime_ns | 1782776461203434757 | 1782776461203434757 |
| Representative artifact sha256 | `2d8f931b79809660e9eb5e9e858a54170fd087b772ea7fc7f64a1b43a0d29881` | `2d8f931b79809660e9eb5e9e858a54170fd087b772ea7fc7f64a1b43a0d29881` |
| Representative model artifact | `artifacts/models/ab6b20afabb330bc6293beea.joblib` | `artifacts/models/ab6b20afabb330bc6293beea.joblib` |
| Representative model artifact size | 7,002,182 bytes | 7,002,182 bytes |
| Representative model artifact mtime_ns | 1782572633736498893 | 1782572633736498893 |
| Representative model artifact sha256 | `6720ec3748dbfd4a1104600aa400e963be6478be00fa5abb7c7110e979ab6a0b` | `6720ec3748dbfd4a1104600aa400e963be6478be00fa5abb7c7110e979ab6a0b` |
| Scanner snapshot count | 4 | 4 |
| Forward-event count | 26 | 26 |
| Forward-event type counts | `FINAL_HOLDOUT_ENTRY_PENDING=1`, `FINAL_HOLDOUT_SIGNAL_CREATED=1`, `FINAL_HOLDOUT_SIGNAL_REJECTED=24` | `FINAL_HOLDOUT_ENTRY_PENDING=1`, `FINAL_HOLDOUT_SIGNAL_CREATED=1`, `FINAL_HOLDOUT_SIGNAL_REJECTED=24` |
| Final-holdout run count | 1 | 1 |
| Final-holdout event count | 24 | 24 |

Operational repository before/after state:

| Item | Before | After |
| --- | --- | --- |
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` |
| SQLite path | `state/engine.sqlite3` | `state/engine.sqlite3` |
| SQLite size | 250,781,696 bytes | 250,781,696 bytes |
| SQLite mtime_ns | 1782585787422972957 | 1782585787422972957 |
| SQLite sha256 | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |
| Scanner snapshot count | 18 | 18 |
| Forward-event count | 310 | 310 |
| Forward-event type counts | `ENTRY_PENDING=35`, `FINAL_HOLDOUT_SIGNAL_REJECTED=25`, `SIGNAL_CREATED=35`, `SIGNAL_REJECTED=215` | `ENTRY_PENDING=35`, `FINAL_HOLDOUT_SIGNAL_REJECTED=25`, `SIGNAL_CREATED=35`, `SIGNAL_REJECTED=215` |
| Final-holdout run count | 1 | 1 |
| Operational final-holdout event count | 25 | 25 |
| Prospective run ID | `3493ee8ac37bf96475c362e1` | `3493ee8ac37bf96475c362e1` |
| Baseline date | `2026-06-25` | `2026-06-25` |

Confirmed by diagnostic process:

- no source files changed;
- no model artifacts changed;
- no SQLite state changed;
- no scanner state changed;
- no forward state changed;
- no final-holdout state changed;
- no operational state changed.
