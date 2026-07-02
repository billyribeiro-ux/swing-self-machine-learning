# Post-Generation TBS Calibration Evidence Review

Date: 2026-06-29

Generation reviewed: `signal_discovery_20260629T232550+0000_92147b091ad7`

Calibration artifacts used:

- `reports/signal_discovery_calibration_v1/calibration_summary.csv`
- `reports/signal_discovery_calibration_v1/calibration_summary.json`
- `reports/signal_discovery_calibration_v1/probability_distributions.csv`
- `reports/signal_discovery_calibration_v1/probability_buckets.csv`
- `reports/signal_discovery_calibration_v1/diagnostic_thresholds.csv`
- `reports/signal_discovery_calibration_v1/row_level_calibration_audit.csv`
- `reports/signal_discovery_calibration_v1/row_level_calibration_audit.parquet`
- `reports/signal_discovery_calibration_v1/calibration_artifact_manifest.json`
- `reports/signal_discovery_calibration_v1/analog_robustness.csv`
- `reports/signal_discovery_calibration_v1/analog_depth_comparison.csv`
- `reports/signal_discovery_calibration_v1/analog_caution_flags.csv`

Safety label for every conclusion in this report:

Calibration diagnostic only. Not a threshold change and not proof of edge.

## Executive Finding

The highest-scoring TBS-blocked rows are blocked correctly by the current gate. The persisted calibration artifacts do not show a clean model-underconfidence case. They show that the current 0.50 target-before-stop threshold is conservative, often unsupported by enough calibration rows in leveraged/inverse scopes, and not contradicted by bucket evidence for the current top blocked rows.

The main measured issue is not a source-code defect or automatic threshold problem. It is a target/stop-policy mismatch for parts of Sector Rotation BUY and leveraged-inverse 10-day SELL/SHORT contexts: several calibration buckets show positive average forward return and MFE while observed TBS hit rates remain materially below 0.50.

Overall root-cause classification:

- `VALID_MODEL_GATE`
- `TARGET_STOP_POLICY_MISMATCH`
- `ANALOG_SUPPORT_NOT_ROBUST`
- `PRODUCT_CLASS_INSTABILITY`
- `INSUFFICIENT_EVIDENCE`

Not supported:

- `MODEL_UNDERCONFIDENCE`
- `CALIBRATION_COLLAPSE`
- `IMPLEMENTATION_DEFECT`

## Current TBS-Blocked Population

Rows blocked by `target_before_stop_probability_below_threshold`: 217.

- BUY-side rows: 185
- SELL/SHORT-side rows: 32

Prior known rows:

| Prior row | Status in this generation |
|---|---|
| TZA `sector_rotation_buy_20d` | Present, TBS-blocked |
| SQQQ `sector_rotation_buy_20d` | Present, TBS-blocked |
| RWM `sector_rotation_buy_20d` | Present, TBS-blocked |
| AMZN `sector_rotation_buy_20d` | Present, TBS-blocked |
| QID `sector_rotation_buy_20d` | Present, TBS-blocked |
| SOXS `trend_continuation_sell_10d` | Present, TBS-blocked |
| SOXS `pullback_continuation_sell_10d` | Present, TBS-blocked |
| SOXS `breadth_deterioration_sell_10d` | Present, TBS-blocked |
| SOXS `breakdown_sell_10d` | Present, TBS-blocked |
| SOXS `volatility_expansion_sell_5d` | Absent from TBS-blocked set; blocked by `probability_below_threshold` instead |

## Rows Reviewed

The selected review set is the union of the top BUY rows, top SELL/SHORT rows, closest-to-threshold rows, highest expected-return rows, and strongest robust-analog rows. All rows have as-of date `2026-06-26`.

### Top 10 BUY-Side TBS-Blocked Rows by Signal Score

| Signal ID | Ticker | Action | Archetype | Horizon | Score | Model p | TBS p | Exp ret | Exp MFE | Exp MAE | OOD | Robust analog | Caution flags | Model ID | Scope |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| `0380a8a3771bff535b9688bf` | TZA | BUY | Sector Rotation | 20 | 0.6429 | 0.5804 | 0.3589 | 0.0869 | 0.4890 | -0.1306 | 0.0208 | WEAK_SUPPORT | high_return_dispersion;high_mae_tail_risk | `sector_rotation_buy_20d:hist_gradient_boosting` | LEVERAGED_INVERSE |
| `3421d9558bc50081c84808ca` | SQQQ | BUY | Sector Rotation | 20 | 0.6415 | 0.5804 | 0.3521 | 0.0612 | 0.2458 | -0.1502 | 0.0208 | WEAK_SUPPORT | high_return_dispersion;high_mae_tail_risk | `sector_rotation_buy_20d:hist_gradient_boosting` | LEVERAGED_INVERSE |
| `e5e063851858f2832fabe832` | RWM | BUY | Sector Rotation | 20 | 0.5683 | 0.5804 | 0.3589 | 0.0154 | 0.0966 | -0.0571 | 0.0208 | MIXED_SUPPORT | same_regime_concentration;high_return_dispersion;tbs_support_decay | `sector_rotation_buy_20d:hist_gradient_boosting` | INVERSE |
| `f566f671abc1be70924f8886` | AMZN | BUY | Sector Rotation | 20 | 0.5466 | 0.5804 | 0.3947 | 0.0142 | 0.0923 | -0.0900 | 0.0208 | MIXED_SUPPORT | same_year_concentration;same_regime_concentration;high_return_dispersion;high_mae_tail_risk | `sector_rotation_buy_20d:hist_gradient_boosting` | ORDINARY |
| `3049d5534cf722d50aa63338` | QID | BUY | Sector Rotation | 20 | 0.5440 | 0.5804 | 0.3521 | 0.0181 | 0.2083 | -0.1304 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `sector_rotation_buy_20d:hist_gradient_boosting` | LEVERAGED_INVERSE |
| `781296dcbf3a32ec65ac4f6d` | XLE | BUY | Sector Rotation | 20 | 0.5368 | 0.5804 | 0.3589 | 0.0153 | 0.0462 | -0.0395 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `sector_rotation_buy_20d:hist_gradient_boosting` | ORDINARY |
| `c2957593d4c2d9d44668a4b8` | SPXU | BUY | Sector Rotation | 20 | 0.5337 | 0.5804 | 0.3521 | 0.0137 | 0.3228 | -0.1038 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `sector_rotation_buy_20d:hist_gradient_boosting` | LEVERAGED_INVERSE |
| `75ab504bfcc6593c1cefd48a` | XLP | BUY | Sector Rotation | 20 | 0.5326 | 0.5804 | 0.3538 | 0.0153 | 0.0431 | -0.0395 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `sector_rotation_buy_20d:hist_gradient_boosting` | ORDINARY |
| `6272ec4052002b7f2db4c71f` | SDS | BUY | Sector Rotation | 20 | 0.5321 | 0.5804 | 0.3521 | 0.0074 | 0.2637 | -0.0761 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `sector_rotation_buy_20d:hist_gradient_boosting` | LEVERAGED_INVERSE |
| `c66a2a3f0ca1ed9d7f23766a` | AAPL | BUY | Sector Rotation | 20 | 0.5294 | 0.5804 | 0.3589 | 0.0098 | 0.0862 | -0.0791 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `sector_rotation_buy_20d:hist_gradient_boosting` | ORDINARY |

### Top 10 SELL/SHORT-Side TBS-Blocked Rows by Signal Score

| Signal ID | Ticker | Action | Archetype | Horizon | Score | Model p | TBS p | Exp ret | Exp MFE | Exp MAE | OOD | Robust analog | Caution flags | Model ID | Scope |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| `5eb57df1606dd64680951260` | SOXS | SELL_SHORT | Breakout / Breakdown | 10 | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.2618 | -0.1342 | 0.1875 | CONCENTRATION_ARTIFACT | same_symbol_concentration;same_year_concentration;high_return_dispersion;high_mae_tail_risk;tbs_support_decay;support_decays_top25;support_decays_top50;analogs_mostly_same_event_cluster | `breakdown_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `a6cc3d26e434b79b04f6cd33` | SOXS | SELL_SHORT | Breadth Thrust / Breadth Deterioration | 10 | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.2618 | -0.1342 | 0.1875 | CONCENTRATION_ARTIFACT | same_symbol_concentration;same_year_concentration;high_return_dispersion;high_mae_tail_risk;tbs_support_decay;support_decays_top25;support_decays_top50;analogs_mostly_same_event_cluster | `breadth_deterioration_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `944bdb7abc71d45cb1def65a` | SOXS | SELL_SHORT | Trend Continuation | 10 | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.2618 | -0.1342 | 0.1875 | CONCENTRATION_ARTIFACT | same_symbol_concentration;same_year_concentration;high_return_dispersion;high_mae_tail_risk;tbs_support_decay;support_decays_top25;support_decays_top50;analogs_mostly_same_event_cluster | `trend_continuation_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `01b288093f7da77b3b2b1b47` | SOXS | SELL_SHORT | Pullback Continuation | 10 | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.2618 | -0.1342 | 0.1875 | CONCENTRATION_ARTIFACT | same_symbol_concentration;same_year_concentration;high_return_dispersion;high_mae_tail_risk;tbs_support_decay;support_decays_top25;support_decays_top50;analogs_mostly_same_event_cluster | `pullback_continuation_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `a2ee9a868b510c6ae473b9af` | SQQQ | SELL_SHORT | Breadth Deterioration | 10 | 0.4934 | 0.6196 | 0.2613 | 0.0002 | 0.1631 | -0.1299 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `breadth_deterioration_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `d7a170d15412f5fad6df5fb1` | SQQQ | SELL_SHORT | Trend Continuation | 10 | 0.4934 | 0.6196 | 0.2613 | 0.0002 | 0.1631 | -0.1299 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `trend_continuation_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `9f34455fb29106d6aa18a2c8` | SQQQ | SELL_SHORT | Pullback Continuation | 10 | 0.4934 | 0.6196 | 0.2613 | 0.0002 | 0.1631 | -0.1299 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `pullback_continuation_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `4b5d5fb4b14f5718efff69a0` | SQQQ | SELL_SHORT | Breakout / Breakdown | 10 | 0.4934 | 0.6196 | 0.2613 | 0.0002 | 0.1631 | -0.1299 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `breakdown_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `223fe7b7ff282c12c5e61e6a` | QID | SELL_SHORT | Trend Continuation | 10 | 0.4863 | 0.6196 | 0.2613 | -0.0013 | 0.1065 | -0.0973 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `trend_continuation_sell_10d:extra_trees` | LEVERAGED_INVERSE |
| `d3327f0186b56f5589bd510b` | QID | SELL_SHORT | Breadth Deterioration | 10 | 0.4863 | 0.6196 | 0.2613 | -0.0013 | 0.1065 | -0.0973 | 0.0208 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |  | `breadth_deterioration_sell_10d:extra_trees` | LEVERAGED_INVERSE |

### Closest to the 0.50 TBS Threshold

No TBS-blocked row is close to 0.50 in absolute terms. The closest TBS probabilities are 0.3947, 0.3589, and 0.3538.

Top closest rows:

| Ticker | Hypothesis | Scope | TBS p | Distance to 0.50 |
|---|---|---|---:|---:|
| AMZN | `sector_rotation_buy_20d` | ORDINARY | 0.3947 | 0.1053 |
| XLY | `sector_rotation_buy_20d` | ORDINARY | 0.3947 | 0.1053 |
| XLK | `sector_rotation_buy_20d` | ORDINARY | 0.3947 | 0.1053 |
| TQQQ | `sector_rotation_buy_20d` | LEVERAGED_LONG | 0.3947 | 0.1053 |
| TZA | `sector_rotation_buy_20d` | LEVERAGED_INVERSE | 0.3589 | 0.1411 |
| RWM | `sector_rotation_buy_20d` | INVERSE | 0.3589 | 0.1411 |
| XLE | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.1411 |
| AAPL | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.1411 |
| XLB | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.1411 |
| NVDA | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.1411 |

### Highest Expected-Return TBS-Blocked Rows

| Ticker | Hypothesis | Action | Scope | Expected return | TBS p | Robust analog |
|---|---|---|---|---:|---:|---|
| TZA | `sector_rotation_buy_20d` | BUY | LEVERAGED_INVERSE | 0.0869 | 0.3589 | WEAK_SUPPORT |
| SQQQ | `sector_rotation_buy_20d` | BUY | LEVERAGED_INVERSE | 0.0612 | 0.3521 | WEAK_SUPPORT |
| SOXS | `pullback_continuation_sell_10d` | SELL_SHORT | LEVERAGED_INVERSE | 0.0361 | 0.2613 | CONCENTRATION_ARTIFACT |
| SOXS | `breakdown_sell_10d` | SELL_SHORT | LEVERAGED_INVERSE | 0.0361 | 0.2613 | CONCENTRATION_ARTIFACT |
| SOXS | `trend_continuation_sell_10d` | SELL_SHORT | LEVERAGED_INVERSE | 0.0361 | 0.2613 | CONCENTRATION_ARTIFACT |
| SOXS | `breadth_deterioration_sell_10d` | SELL_SHORT | LEVERAGED_INVERSE | 0.0361 | 0.2613 | CONCENTRATION_ARTIFACT |
| QID | `sector_rotation_buy_20d` | BUY | LEVERAGED_INVERSE | 0.0181 | 0.3521 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |
| RWM | `sector_rotation_buy_20d` | BUY | INVERSE | 0.0154 | 0.3589 | MIXED_SUPPORT |
| XLP | `sector_rotation_buy_20d` | BUY | ORDINARY | 0.0153 | 0.3538 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |
| XLE | `sector_rotation_buy_20d` | BUY | ORDINARY | 0.0153 | 0.3589 | NOT_SELECTED_FOR_ROBUST_ANALOG_EXPORT |

### Strongest Robust Analog Labels

No TBS-blocked row had `ROBUST_SUPPORT` or `SUPPORTIVE_BUT_CONCENTRATED`.

The strongest persisted robust labels were:

| Ticker | Hypothesis | Robust label | Interpretation |
|---|---|---|---|
| RWM | `sector_rotation_buy_20d` | MIXED_SUPPORT | Top-10 analog TBS hit was 0.60, but support decayed to 0.42 at top-50 with concentration warnings |
| AMZN | `sector_rotation_buy_20d` | MIXED_SUPPORT | Top-10/top-25/top-50 TBS hit rates were 0.00/0.04/0.10, so this is not TBS-supportive despite the label |
| TZA | `sector_rotation_buy_20d` | WEAK_SUPPORT | Top-10/top-25/top-50 TBS hit rates were 0.30/0.56/0.42 with negative average forward return at all depths |
| SQQQ | `sector_rotation_buy_20d` | WEAK_SUPPORT | Top-10/top-25/top-50 TBS hit rates were 0.20/0.48/0.38 with weak nearest-depth evidence |
| SOXS | four 10-day SELL/SHORT contexts | CONCENTRATION_ARTIFACT | Top-10 looked supportive, but all nearest analogs were same-symbol and same-year; support decayed by top-50 |

## Calibration Artifact Join Status

All selected rows joined to calibration artifacts. No selected row had missing calibration summary, probability distribution, diagnostic threshold, probability bucket, or row-level calibration context.

| Hypothesis | Family | Scope | Rows | Pos TBS | Neg TBS | Base rate | Model Brier | Naive Brier | Skill | ROC-AUC | PR-AUC | ECE | Slope | Intercept | Rank corr | Plateau pct | Unique cal p | Calibrator |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `sector_rotation_buy_20d` | hist_gradient_boosting | LEVERAGED_INVERSE | 2874 | 776 | 2098 | 0.2700 | 0.2013 | 0.1971 | -0.0042 | 0.5648 | 0.3140 | 0.0764 | 1.2091 | -0.1489 | 0.9203 | 0.5299 | 20 | IsotonicRegression |
| `sector_rotation_buy_20d` | hist_gradient_boosting | INVERSE | 958 | 266 | 692 | 0.2777 | 0.2054 | 0.2006 | -0.0048 | 0.5793 | 0.3270 | 0.0801 | 2.8185 | -0.7307 | 0.9749 | 0.3048 | 11 | IsotonicRegression |
| `sector_rotation_buy_20d` | hist_gradient_boosting | ORDINARY | 11017 | 4232 | 6785 | 0.3841 | 0.2367 | 0.2366 | -0.0002 | 0.5158 | 0.3969 | 0.0259 | 0.7027 | 0.1323 | 0.9725 | 0.3545 | 25 | IsotonicRegression |
| `sector_rotation_buy_20d` | hist_gradient_boosting | LEVERAGED_LONG | 1916 | 719 | 1197 | 0.3753 | 0.2325 | 0.2344 | 0.0020 | 0.5308 | 0.4061 | 0.0120 | 0.9712 | 0.0169 | 0.9746 | 0.3246 | 23 | IsotonicRegression |
| `breakdown_sell_10d` | extra_trees | LEVERAGED_INVERSE | 2946 | 887 | 2059 | 0.3011 | 0.2112 | 0.2104 | -0.0008 | 0.5510 | 0.3275 | 0.0496 | 1.2285 | -0.0079 | 0.9537 | 0.4294 | 10 | IsotonicRegression |
| `breadth_deterioration_sell_10d` | extra_trees | LEVERAGED_INVERSE | 2946 | 887 | 2059 | 0.3011 | 0.2112 | 0.2104 | -0.0008 | 0.5510 | 0.3275 | 0.0496 | 1.2285 | -0.0079 | 0.9537 | 0.4294 | 10 | IsotonicRegression |
| `trend_continuation_sell_10d` | extra_trees | LEVERAGED_INVERSE | 2946 | 887 | 2059 | 0.3011 | 0.2112 | 0.2104 | -0.0008 | 0.5509 | 0.3275 | 0.0496 | 1.2285 | -0.0079 | 0.9537 | 0.4294 | 10 | IsotonicRegression |
| `pullback_continuation_sell_10d` | extra_trees | LEVERAGED_INVERSE | 2946 | 887 | 2059 | 0.3011 | 0.2112 | 0.2104 | -0.0008 | 0.5510 | 0.3275 | 0.0496 | 1.2285 | -0.0079 | 0.9537 | 0.4294 | 10 | IsotonicRegression |

Calibration method for all rows above: `isotonic_regression`.

Missing join keys: none.

## Probability Distribution Review

The raw and calibrated distributions show compression, but not a proven calibration collapse for the current rows.

| Hypothesis | Scope | Type | Min | Median | P90 | P99 | Max | Mean | Std | >=0.30 | >=0.35 | >=0.40 | >=0.45 | >=0.50 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `sector_rotation_buy_20d` | LEVERAGED_INVERSE | raw | 0.1256 | 0.3243 | 0.4066 | 0.4843 | 0.5454 | 0.3215 | 0.0689 | 1848 | 969 | 343 | 81 | 20 |
| `sector_rotation_buy_20d` | LEVERAGED_INVERSE | calibrated | 0.0000 | 0.3426 | 0.3947 | 0.4135 | 0.4325 | 0.3464 | 0.0344 | 2759 | 1102 | 38 | 0 | 0 |
| `sector_rotation_buy_20d` | INVERSE | raw | 0.2080 | 0.3610 | 0.4197 | 0.4997 | 0.5391 | 0.3603 | 0.0517 | 844 | 579 | 184 | 49 | 10 |
| `sector_rotation_buy_20d` | INVERSE | calibrated | 0.3379 | 0.3521 | 0.3947 | 0.4135 | 0.4302 | 0.3578 | 0.0187 | 958 | 645 | 21 | 0 | 0 |
| `sector_rotation_buy_20d` | ORDINARY | raw | 0.1051 | 0.3565 | 0.4540 | 0.5636 | 0.6839 | 0.3518 | 0.0845 | 8141 | 5874 | 2895 | 1183 | 498 |
| `sector_rotation_buy_20d` | ORDINARY | calibrated | 0.0000 | 0.3521 | 0.3947 | 0.4325 | 1.0000 | 0.3583 | 0.0349 | 10733 | 6337 | 747 | 28 | 12 |
| `sector_rotation_buy_20d` | LEVERAGED_LONG | raw | 0.1078 | 0.3755 | 0.5118 | 0.6283 | 0.6802 | 0.3736 | 0.1075 | 1380 | 1122 | 810 | 444 | 224 |
| `sector_rotation_buy_20d` | LEVERAGED_LONG | calibrated | 0.0000 | 0.3538 | 0.4135 | 0.4545 | 1.0000 | 0.3690 | 0.0461 | 1867 | 1162 | 304 | 27 | 10 |
| 10-day SELL/SHORT LI contexts | LEVERAGED_INVERSE | raw | 0.1703 | 0.2838 | 0.3314 | 0.3565 | 0.3759 | 0.2806 | 0.0401 | 1068 | 54 | 0 | 0 | 0 |
| 10-day SELL/SHORT LI contexts | LEVERAGED_INVERSE | calibrated | 0.0000 | 0.2613 | 0.2769 | 0.2769 | 0.2769 | 0.2515 | 0.0340 | 0 | 0 | 0 | 0 | 0 |

Interpretation:

- Calibration compressed probabilities into a narrow band, especially for SELL/SHORT leveraged-inverse contexts.
- Raw-versus-calibrated rank correlations remain high, from 0.9203 to 0.9749 in the relevant groups.
- Unique calibrated probability counts range from 10 to 25. That is coarse but not enough by itself to classify the current blocked rows as `CALIBRATION_COLLAPSE`.
- SELL/SHORT leveraged-inverse calibrated probabilities never reach 0.30 in the calibration slice, so the 0.50 production threshold has no direct support in that scope from qualifying rows.

## Diagnostic Threshold Review

Diagnostic thresholds are not production threshold recommendations.

| Context | Threshold evidence classification | Measured basis |
|---|---|---|
| Sector Rotation BUY, LEVERAGED_INVERSE | INSUFFICIENT_CALIBRATION_EVIDENCE | 0.50 had 0 qualifying rows; 0.35 had TBS hit 0.3249 and average return -0.0437 |
| Sector Rotation BUY, INVERSE | INSUFFICIENT_CALIBRATION_EVIDENCE | 0.50 had 0 qualifying rows; 0.35 had TBS hit 0.3147 and average return -0.0093 |
| Sector Rotation BUY, ORDINARY | THRESHOLD_TOO_STRICT_BY_CALIBRATION | 0.30-0.40 had positive average returns, but 0.50 had only 12 rows; this supports policy mismatch diagnostics, not a gate change |
| Sector Rotation BUY, LEVERAGED_LONG | MIXED_OR_UNSTABLE | 0.40 had TBS hit 0.4441 and positive average return 0.0962; 0.50 had only 10 rows and negative average return -0.0766 |
| 10-day SELL/SHORT LEVERAGED_INVERSE contexts | INSUFFICIENT_CALIBRATION_EVIDENCE | 0.30 through 0.60 all had 0 qualifying rows after calibration |

### Threshold Details

| Context | Thresh | Qual rows | Qual rate | Obs TBS | Precision | Recall | Avg ret | Med ret | Avg MFE | Avg MAE | Worst MAE | Target | Stop | Unres | Utility | Symbol conc | Year conc | Regime conc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Sector Rotation BUY LI | 0.30 | 2759 | 0.9600 | 0.2740 | 0.2740 | 0.9742 | -0.0404 | -0.0557 | 0.1102 | -0.1274 | -0.5731 | 0.2740 | 0.7046 | 0.0214 | -0.0409 | 0.1736 | 0.5335 | 0.3762 |
| Sector Rotation BUY LI | 0.35 | 1102 | 0.3834 | 0.3249 | 0.3249 | 0.4613 | -0.0437 | -0.0542 | 0.0949 | -0.1131 | -0.4683 | 0.3249 | 0.6543 | 0.0209 | -0.0442 | 0.3113 | 0.6561 | 0.4574 |
| Sector Rotation BUY LI | 0.40 | 38 | 0.0132 | 0.2895 | 0.2895 | 0.0142 | 0.0100 | 0.0227 | 0.1535 | -0.1099 | -0.2934 | 0.2895 | 0.7105 | 0.0000 | 0.0095 | 0.7632 | 0.8158 | 0.7368 |
| Sector Rotation BUY LI | 0.45-0.60 | 0 | 0.0000 | N/A | N/A | 0.0000 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Sector Rotation BUY INVERSE | 0.30 | 958 | 1.0000 | 0.2777 | 0.2777 | 1.0000 | -0.0093 | -0.0149 | 0.0376 | -0.0427 | -0.1439 | 0.2777 | 0.7077 | 0.0146 | -0.0098 | 0.5000 | 0.5219 | 0.3612 |
| Sector Rotation BUY INVERSE | 0.35 | 645 | 0.6733 | 0.3147 | 0.3147 | 0.7632 | -0.0093 | -0.0145 | 0.0370 | -0.0409 | -0.1439 | 0.3147 | 0.6713 | 0.0140 | -0.0098 | 0.5116 | 0.6124 | 0.4620 |
| Sector Rotation BUY INVERSE | 0.40 | 21 | 0.0219 | 0.2857 | 0.2857 | 0.0226 | 0.0205 | 0.0147 | 0.0565 | -0.0284 | -0.0752 | 0.2857 | 0.7143 | 0.0000 | 0.0200 | 0.6190 | 0.8571 | 0.6667 |
| Sector Rotation BUY INVERSE | 0.45-0.60 | 0 | 0.0000 | N/A | N/A | 0.0000 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Sector Rotation BUY ORDINARY | 0.30 | 10733 | 0.9742 | 0.3872 | 0.3872 | 0.9820 | 0.0201 | 0.0176 | 0.0666 | -0.0482 | -0.4356 | 0.3873 | 0.5995 | 0.0133 | 0.0196 | 0.0446 | 0.5351 | 0.3707 |
| Sector Rotation BUY ORDINARY | 0.35 | 6337 | 0.5752 | 0.3896 | 0.3896 | 0.5834 | 0.0233 | 0.0205 | 0.0627 | -0.0423 | -0.3378 | 0.3898 | 0.5981 | 0.0123 | 0.0228 | 0.0585 | 0.6462 | 0.5155 |
| Sector Rotation BUY ORDINARY | 0.40 | 747 | 0.0678 | 0.4297 | 0.4297 | 0.0759 | 0.0377 | 0.0218 | 0.0769 | -0.0473 | -0.2816 | 0.4297 | 0.5649 | 0.0054 | 0.0372 | 0.1299 | 0.7430 | 0.3989 |
| Sector Rotation BUY ORDINARY | 0.45 | 28 | 0.0025 | 0.6071 | 0.6071 | 0.0040 | 0.0017 | 0.0044 | 0.0713 | -0.0576 | -0.1372 | 0.6071 | 0.3929 | 0.0000 | 0.0012 | 0.3214 | 1.0000 | 0.5000 |
| Sector Rotation BUY ORDINARY | 0.50 | 12 | 0.0011 | 0.7500 | 0.7500 | 0.0021 | -0.0142 | -0.0168 | 0.0754 | -0.0476 | -0.0943 | 0.7500 | 0.2500 | 0.0000 | -0.0147 | 0.5000 | 1.0000 | 0.8333 |
| Sector Rotation BUY ORDINARY | 0.55-0.60 | 4 | 0.0004 | 0.7500 | 0.7500 | 0.0007 | 0.0131 | 0.0167 | 0.0501 | -0.0293 | -0.0574 | 0.7500 | 0.2500 | 0.0000 | 0.0126 | 1.0000 | 1.0000 | 0.5000 |
| Sector Rotation BUY LEVERAGED_LONG | 0.30 | 1867 | 0.9744 | 0.3808 | 0.3808 | 0.9889 | 0.0504 | 0.0482 | 0.1748 | -0.1217 | -0.5091 | 0.3808 | 0.6042 | 0.0150 | 0.0499 | 0.2528 | 0.5356 | 0.3706 |
| Sector Rotation BUY LEVERAGED_LONG | 0.35 | 1162 | 0.6065 | 0.3795 | 0.3795 | 0.6134 | 0.0609 | 0.0554 | 0.1660 | -0.1048 | -0.4759 | 0.3795 | 0.6110 | 0.0095 | 0.0604 | 0.2539 | 0.6403 | 0.5611 |
| Sector Rotation BUY LEVERAGED_LONG | 0.40 | 304 | 0.1587 | 0.4441 | 0.4441 | 0.1878 | 0.0962 | 0.0929 | 0.1884 | -0.0959 | -0.3344 | 0.4441 | 0.5559 | 0.0000 | 0.0957 | 0.3684 | 0.7007 | 0.5362 |
| Sector Rotation BUY LEVERAGED_LONG | 0.45 | 27 | 0.0141 | 0.4444 | 0.4444 | 0.0167 | 0.0514 | -0.0225 | 0.1803 | -0.1254 | -0.2837 | 0.4444 | 0.5556 | 0.0000 | 0.0509 | 0.5556 | 0.9630 | 0.5556 |
| Sector Rotation BUY LEVERAGED_LONG | 0.50 | 10 | 0.0052 | 0.5000 | 0.5000 | 0.0070 | -0.0766 | -0.0711 | 0.1186 | -0.1653 | -0.2447 | 0.5000 | 0.5000 | 0.0000 | -0.0771 | 0.7000 | 1.0000 | 0.7000 |
| Sector Rotation BUY LEVERAGED_LONG | 0.55-0.60 | 3 | 0.0016 | 1.0000 | 1.0000 | 0.0042 | -0.0408 | -0.0471 | 0.1471 | -0.1064 | -0.1457 | 1.0000 | 0.0000 | 0.0000 | -0.0413 | 1.0000 | 1.0000 | 0.6667 |
| 10-day SELL/SHORT LI contexts | 0.30-0.60 | 0 | 0.0000 | N/A | N/A | 0.0000 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Probability Bucket Review

| Context | Row TBS p | Bucket | Bucket rows | Avg raw p | Avg cal p | Obs TBS | Avg ret | Avg MFE | Avg MAE | Target | Stop | Unres | Bucket classification |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Sector Rotation BUY LEVERAGED_INVERSE | 0.3521-0.3589 | Bucket 3 | 2721 | 0.3257 | 0.3510 | 0.2738 | -0.0411 | 0.1096 | -0.1276 | 0.2738 | 0.7045 | 0.0217 | CONSISTENT_WITH_BUCKET_EVIDENCE |
| Sector Rotation BUY INVERSE | 0.3589 | Bucket 3 | 937 | 0.3571 | 0.3565 | 0.2775 | -0.0100 | 0.0372 | -0.0431 | 0.2775 | 0.7076 | 0.0149 | CONSISTENT_WITH_BUCKET_EVIDENCE |
| Sector Rotation BUY ORDINARY | 0.3538-0.3947 | Bucket 3 | 9986 | 0.3442 | 0.3568 | 0.3840 | 0.0188 | 0.0658 | -0.0483 | 0.3841 | 0.6020 | 0.0139 | CONSISTENT_WITH_BUCKET_EVIDENCE |
| Sector Rotation BUY LEVERAGED_LONG | 0.3947 | Bucket 3 | 1563 | 0.3473 | 0.3608 | 0.3685 | 0.0415 | 0.1721 | -0.1267 | 0.3685 | 0.6136 | 0.0179 | CONSISTENT_WITH_BUCKET_EVIDENCE |
| 10-day SELL/SHORT LEVERAGED_INVERSE | 0.2613 | Bucket 2 | 2923 | 0.2814 | 0.2535 | 0.3035 | 0.0373 | 0.1081 | -0.0669 | 0.3035 | 0.5251 | 0.1714 | CONSISTENT_WITH_BUCKET_EVIDENCE |

Bucket interpretation:

- The top rows' TBS probabilities are consistent with their buckets.
- None of the selected buckets has observed TBS hit rate near 0.50.
- Ordinary Sector Rotation BUY and 10-day SELL/SHORT leveraged-inverse buckets show favorable average forward return while TBS hit remains weak. This is evidence of target/stop-policy mismatch, not model underconfidence.

## Row-Level Calibration Audit Summary

| Context | Rows | TBS hit | Avg raw p | Avg cal p | Dispersion | Top symbols | Year distribution | Regime distribution | Concentration warnings |
|---|---:|---:|---:|---:|---:|---|---|---|---|
| Sector Rotation BUY LEVERAGED_INVERSE | 2874 | 0.2700 | 0.3215 | 0.3464 | 0.0344 | QID/SDS/SOXS/SPXU/SQQQ, 479 each | 2023:1500; 2022:870; 2024:504 | uptrend_low_vol:1038; downtrend_high_vol:930; uptrend_high_vol:864; mixed:42 | year_concentration |
| Sector Rotation BUY INVERSE | 958 | 0.2777 | 0.3603 | 0.3578 | 0.0187 | RWM:479; SH:479 | 2023:500; 2022:290; 2024:168 | uptrend_low_vol:346; downtrend_high_vol:310; uptrend_high_vol:288; mixed:14 | symbol_concentration;year_concentration |
| Sector Rotation BUY ORDINARY | 11017 | 0.3841 | 0.3518 | 0.3583 | 0.0349 | AAPL/AMD/AMZN/DIA/GOOGL, 479 each | 2023:5750; 2022:3335; 2024:1932 | uptrend_low_vol:3979; downtrend_high_vol:3565; uptrend_high_vol:3311; mixed:162 | year_concentration |
| Sector Rotation BUY LEVERAGED_LONG | 1916 | 0.3753 | 0.3736 | 0.3690 | 0.0461 | SOXL/TNA/TQQQ/UPRO, 479 each | 2023:1000; 2022:580; 2024:336 | uptrend_low_vol:692; downtrend_high_vol:620; uptrend_high_vol:576; mixed:28 | symbol_concentration;year_concentration |
| 10-day SELL/SHORT LEVERAGED_INVERSE contexts | 2946 | 0.3011 | 0.2806 | 0.2515 | 0.0340 | QID/SDS/SOXS/SPXU/SQQQ, 491 each | 2023:1500; 2022:834; 2024:612 | uptrend_low_vol:1104; uptrend_high_vol:906; downtrend_high_vol:894; mixed:42 | year_concentration |

Calibration evidence is partly dominated by year in every relevant context. The INVERSE and LEVERAGED_LONG scopes also have symbol concentration because the product universe is narrow.

## Robust Analog Review

Analog outcomes do not override gates.

| Row group | Top-10 TBS | Top-25 TBS | Top-50 TBS | Robust conclusion |
|---|---:|---:|---:|---|
| TZA Sector Rotation BUY | 0.30 | 0.56 | 0.42 | Weak nearest-depth evidence; negative average return at all depths; not robust |
| SQQQ Sector Rotation BUY | 0.20 | 0.48 | 0.38 | Weak nearest-depth evidence; support remains below 0.50 at top-25 and top-50 |
| RWM Sector Rotation BUY | 0.60 | 0.48 | 0.42 | Mixed and decaying support; concentration warnings |
| AMZN Sector Rotation BUY | 0.00 | 0.04 | 0.10 | Mixed label is not TBS-supportive; analog evidence weak |
| SOXS 10-day SELL/SHORT contexts | 0.50 | 0.36 | 0.28 | Nearest depth is same-symbol/same-year concentrated; support decays with depth |

Answer to "Are analogs still weak after robust analog checks?": yes. No current TBS-blocked row has robust analog support. The SOXS cases are concentration artifacts, and the strongest non-SOXS cases decay or remain weak across depth.

## Top-Row TBS Blocker Classification

Each row is assigned exactly one classification.

| Signal ID | Ticker | Hypothesis | Scope | TBS p | Bucket observed TBS | Robust analog | Classification | Rationale |
|---|---|---|---|---:|---:|---|---|---|
| `0380a8a3771bff535b9688bf` | TZA | `sector_rotation_buy_20d` | LEVERAGED_INVERSE | 0.3589 | 0.2738 | WEAK_SUPPORT | ANALOG_WEAKNESS | Weak nearest-depth analogs and negative analog returns despite high expected return |
| `3421d9558bc50081c84808ca` | SQQQ | `sector_rotation_buy_20d` | LEVERAGED_INVERSE | 0.3521 | 0.2738 | WEAK_SUPPORT | ANALOG_WEAKNESS | Weak nearest-depth analogs; bucket TBS materially below 0.50 |
| `e5e063851858f2832fabe832` | RWM | `sector_rotation_buy_20d` | INVERSE | 0.3589 | 0.2775 | MIXED_SUPPORT | ANALOG_WEAKNESS | Top-10 analog support decays by top-50; bucket evidence weak |
| `f566f671abc1be70924f8886` | AMZN | `sector_rotation_buy_20d` | ORDINARY | 0.3947 | 0.3840 | MIXED_SUPPORT | ANALOG_WEAKNESS | Analog TBS hit is 0.00/0.04/0.10 by depth, despite ordinary-scope policy mismatch |
| `3049d5534cf722d50aa63338` | QID | `sector_rotation_buy_20d` | LEVERAGED_INVERSE | 0.3521 | 0.2738 | Not exported | VALID_BLOCKER | Bucket has low TBS hit and negative average return |
| `781296dcbf3a32ec65ac4f6d` | XLE | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.3840 | Not exported | TARGET_STOP_POLICY_MISMATCH | Ordinary bucket has positive average return but TBS remains below 0.50 |
| `c2957593d4c2d9d44668a4b8` | SPXU | `sector_rotation_buy_20d` | LEVERAGED_INVERSE | 0.3521 | 0.2738 | Not exported | VALID_BLOCKER | Bucket TBS and threshold evidence are weak |
| `75ab504bfcc6593c1cefd48a` | XLP | `sector_rotation_buy_20d` | ORDINARY | 0.3538 | 0.3840 | Not exported | TARGET_STOP_POLICY_MISMATCH | Positive forward-return bucket with sub-threshold TBS |
| `6272ec4052002b7f2db4c71f` | SDS | `sector_rotation_buy_20d` | LEVERAGED_INVERSE | 0.3521 | 0.2738 | Not exported | VALID_BLOCKER | Bucket TBS and threshold evidence are weak |
| `c66a2a3f0ca1ed9d7f23766a` | AAPL | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.3840 | Not exported | TARGET_STOP_POLICY_MISMATCH | Ordinary bucket has positive average return but weak TBS |
| `5eb57df1606dd64680951260` | SOXS | `breakdown_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | CONCENTRATION_ARTIFACT | ANALOG_WEAKNESS | Same-symbol/same-year analog concentration and support decay |
| `a6cc3d26e434b79b04f6cd33` | SOXS | `breadth_deterioration_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | CONCENTRATION_ARTIFACT | ANALOG_WEAKNESS | Same-symbol/same-year analog concentration and support decay |
| `944bdb7abc71d45cb1def65a` | SOXS | `trend_continuation_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | CONCENTRATION_ARTIFACT | ANALOG_WEAKNESS | Same-symbol/same-year analog concentration and support decay |
| `01b288093f7da77b3b2b1b47` | SOXS | `pullback_continuation_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | CONCENTRATION_ARTIFACT | ANALOG_WEAKNESS | Same-symbol/same-year analog concentration and support decay |
| `a2ee9a868b510c6ae473b9af` | SQQQ | `breadth_deterioration_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | Not exported | TARGET_STOP_POLICY_MISMATCH | SELL/SHORT bucket has positive average return but weak TBS |
| `d7a170d15412f5fad6df5fb1` | SQQQ | `trend_continuation_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | Not exported | TARGET_STOP_POLICY_MISMATCH | SELL/SHORT bucket has positive average return but weak TBS |
| `9f34455fb29106d6aa18a2c8` | SQQQ | `pullback_continuation_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | Not exported | TARGET_STOP_POLICY_MISMATCH | SELL/SHORT bucket has positive average return but weak TBS |
| `4b5d5fb4b14f5718efff69a0` | SQQQ | `breakdown_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | Not exported | TARGET_STOP_POLICY_MISMATCH | SELL/SHORT bucket has positive average return but weak TBS |
| `223fe7b7ff282c12c5e61e6a` | QID | `trend_continuation_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | Not exported | TARGET_STOP_POLICY_MISMATCH | SELL/SHORT bucket has positive average return but weak TBS |
| `d3327f0186b56f5589bd510b` | QID | `breadth_deterioration_sell_10d` | LEVERAGED_INVERSE | 0.2613 | 0.3035 | Not exported | TARGET_STOP_POLICY_MISMATCH | SELL/SHORT bucket has positive average return but weak TBS |
| XLY row | XLY | `sector_rotation_buy_20d` | ORDINARY | 0.3947 | 0.3840 | Not exported | TARGET_STOP_POLICY_MISMATCH | Same ordinary-sector bucket as AMZN |
| XLK row | XLK | `sector_rotation_buy_20d` | ORDINARY | 0.3947 | 0.3840 | Not exported | TARGET_STOP_POLICY_MISMATCH | Same ordinary-sector bucket as AMZN |
| TQQQ row | TQQQ | `sector_rotation_buy_20d` | LEVERAGED_LONG | 0.3947 | 0.3685 | Not exported | TARGET_STOP_POLICY_MISMATCH | Positive return/MFE bucket but TBS below 0.50 |
| XLB row | XLB | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.3840 | Not exported | TARGET_STOP_POLICY_MISMATCH | Same ordinary-sector bucket as AMZN |
| NVDA row | NVDA | `sector_rotation_buy_20d` | ORDINARY | 0.3589 | 0.3840 | Not exported | TARGET_STOP_POLICY_MISMATCH | Same ordinary-sector bucket as AMZN |

Classification counts:

- `TARGET_STOP_POLICY_MISMATCH`: 14
- `ANALOG_WEAKNESS`: 8
- `VALID_BLOCKER`: 3
- `MODEL_UNDERCONFIDENT`: 0
- `CALIBRATION_COLLAPSE`: 0
- `ARCHETYPE_POLICY_MISMATCH`: 0
- `INSUFFICIENT_EVIDENCE`: 0
- `ARTIFACT_MISSING`: 0

## Objective Answers

1. Does calibration evidence support the current 0.50 TBS threshold?

   It supports keeping the gate intact for the current top blocked rows, because their bucket TBS hit rates are 0.2738, 0.2775, 0.3840, 0.3685, and 0.3035. It does not prove that 0.50 is universally well-calibrated: exact 0.50 threshold support is absent or sparse in multiple scopes.

2. Are the top blocked rows truly weak by TBS evidence?

   Yes. None of the selected rows has a TBS probability near 0.50, and no selected bucket has observed TBS hit near 0.50.

3. Is any archetype showing model underconfidence?

   No row meets the underconfidence rule. Bucket observed TBS rates are not materially high enough relative to 0.50, and robust analog support is weak, mixed, concentrated, or absent.

4. Is calibration collapsing or distorting probabilities?

   Calibration compresses probabilities, especially in SELL/SHORT leveraged-inverse contexts, but no current top-row blocker is best explained by `CALIBRATION_COLLAPSE`. Rank correlations remain high and bucket evidence remains below 0.50.

5. Does the target/stop policy mismatch the archetype?

   Yes, for ordinary Sector Rotation BUY and 10-day SELL/SHORT leveraged-inverse contexts. These show positive forward-return and MFE evidence while TBS hit remains below threshold, suggesting profitable paths may not be captured by the current target-before-stop framing.

6. Are analogs still weak after robust analog checks?

   Yes. No selected TBS-blocked row has robust analog support. SOXS nearest analogs are concentrated artifacts, and TZA/SQQQ/RWM analog support decays or remains weak by depth.

7. Is there one archetype/scope/direction that deserves a targeted model correction?

   The strongest candidate for targeted follow-up is Sector Rotation BUY in ORDINARY scope, but this review does not support a threshold change. The evidence points first to a target/stop policy diagnostic, because the ordinary bucket has positive average return with only 0.3840 observed TBS hit.

## Root-Cause Summary

`VALID_MODEL_GATE`: Supported. The selected rows are below the 0.50 production TBS threshold, and bucket evidence does not show observed TBS hit near 0.50.

`TARGET_STOP_POLICY_MISMATCH`: Supported. Ordinary Sector Rotation BUY bucket evidence has average return 0.0188 and average MFE 0.0658 with TBS hit 0.3840. 10-day SELL/SHORT leveraged-inverse bucket evidence has average return 0.0373 and average MFE 0.1081 with TBS hit 0.3035.

`ANALOG_SUPPORT_NOT_ROBUST`: Supported. Robust analog labels are weak, mixed, or concentration artifacts. No selected row has robust support.

`PRODUCT_CLASS_INSTABILITY`: Supported. Calibration base rates and bucket behavior vary materially by scope: 0.2700 for leveraged-inverse Sector Rotation BUY, 0.2777 for inverse, 0.3841 for ordinary, and 0.3753 for leveraged-long. Narrow scopes also show symbol concentration.

`INSUFFICIENT_EVIDENCE`: Supported for high-threshold diagnostics in leveraged/inverse contexts. Several exact 0.50 diagnostic threshold rows have zero qualifying calibration observations.

`MODEL_UNDERCONFIDENCE`: Not supported. The row-level and bucket-level evidence does not show strong realized TBS rates at the selected probabilities, and analog robustness is not strong.

`CALIBRATION_COLLAPSE`: Not supported. Compression exists, but it does not explain the blocker as a false negative in this review.

`IMPLEMENTATION_DEFECT`: Not supported. No source-code or artifact defect was proven.

## Next Engineering Task

Add target/stop policy diagnostic for Sector Rotation BUY in ORDINARY scope.

## Immutability

This review used existing artifacts only. It did not run discovery, scanner, forward update, final-holdout update, daily cycle, model training, model promotion, or FMP updates.

Development Git status before:

```text
## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1
```

Development Git status after:

```text
## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1
?? docs/POST_GENERATION_TBS_CALIBRATION_EVIDENCE_REVIEW.md
```

Development SQLite before and after:

| Path | Size before | Size after | mtime_ns before | mtime_ns after | SHA256 before | SHA256 after |
|---|---:|---:|---:|---:|---|---|
| `state/engine.sqlite3` | 385888256 | 385888256 | 1782583720016271553 | 1782583720016271553 | `5646a5cb4abc0a4260e83f1c311a93c55267c5b622862807f78a2458d14a98bb` | `5646a5cb4abc0a4260e83f1c311a93c55267c5b622862807f78a2458d14a98bb` |

Representative artifact before and after:

| Path | Size before | Size after | mtime_ns before | mtime_ns after | SHA256 before | SHA256 after |
|---|---:|---:|---:|---:|---|---|
| `reports/signal_discovery_calibration_v1/calibration_artifact_manifest.json` | 1629 | 1629 | 1782776461203434757 | 1782776461203434757 | `2d8f931b79809660e9eb5e9e858a54170fd087b772ea7fc7f64a1b43a0d29881` | `2d8f931b79809660e9eb5e9e858a54170fd087b772ea7fc7f64a1b43a0d29881` |

Representative development model artifact before and after:

| Path | Size before | Size after | mtime_ns before | mtime_ns after | SHA256 before | SHA256 after |
|---|---:|---:|---:|---:|---|---|
| `artifacts/models/ab6b20afabb330bc6293beea.joblib` | 7002182 | 7002182 | 1782572633736498893 | 1782572633736498893 | `6720ec3748dbfd4a1104600aa400e963be6478be00fa5abb7c7110e979ab6a0b` | `6720ec3748dbfd4a1104600aa400e963be6478be00fa5abb7c7110e979ab6a0b` |

Development state counters:

| Counter | Before | After |
|---|---:|---:|
| Scanner snapshot count | 4 | 4 |
| Forward-event count | 26 | 26 |
| Final-holdout run count | 1 | 1 |
| Final-holdout event count | 24 | 24 |

Operational repository before and after:

| Item | Before | After |
|---|---|---|
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` |
| Final-holdout event count | 25 | 25 |

Operational SQLite immutability check:

| Path | Size before | Size after | mtime_ns before | mtime_ns after | SHA256 before | SHA256 after |
|---|---:|---:|---:|---:|---|---|
| `state/engine.sqlite3` | 250781696 | 250781696 | 1782585787422972957 | 1782585787422972957 | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |

Confirmed:

- No source files changed.
- No model artifacts changed.
- No SQLite state changed.
- No scanner state changed.
- No forward state changed.
- No final-holdout state changed.
- No operational state changed.
