# First Prospective Final-Holdout Enrollment

Generated: 2026-06-25T20:55:47.470070+00:00

This is an operational handoff for the first real Prospective Shadow Final-Holdout enrollment. No source code, tests, thresholds, gates, calibration, OOD governance, model artifacts, discovery run, ordinary scanner run, ordinary forward-update, or promotion was performed.

## Eligible Model

| Field | Value |
| --- | --- |
| Full model ID | b93b2258c10aea5cef81d291 |
| Direction | bull |
| Family | hist_gradient_boosting |
| Horizon | 10 sessions |
| Generation | 2026-06-25T13:11:51.610283+00:00 |
| Registry state | CANDIDATE |
| Learned model | yes |
| Development blockers from final-holdout eligibility | none |
| Promotion eligibility before prospective evidence | no |
| Scanner eligibility at enrollment | not run; ordinary scanner not invoked in this task |
| Final-holdout enrollment eligibility | yes |
| Target-Before-Stop calibrator | identity |
| Expected-return head | ACTIVE |
| MFE head | ACTIVE |
| MAE head | ACTIVE |

### Target-Specific Feature Manifests

| Head | Feature manifest hash |
| --- | --- |
| expected_return | 515d92e32d8124f0031b9f33837e0dfa8d64d7d2ec13f7a7c239f1049a4ee85e |
| mae | 893e750411f44673d5b5afc5ecb5df59eccc09a359466c1c7580e4d15a15327b |
| mfe | c553b8b67bb486ebbc6d0b962890be176c89f568bed72ee6227f9558f447442f |
| primary_classifier | 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5 |
| target_before_stop | bf2bb7a061e05e4f3d9d4a57db4e62b9d72f01c094a34a2170cefa9df9b3527d |

### Active Estimator Classes

| Head | Estimator class |
| --- | --- |
| expected_return | HistGradientBoostingRegressor |
| mae | HistGradientBoostingRegressor |
| mfe | HistGradientBoostingRegressor |
| primary_classifier | HistGradientBoostingClassifier |
| target_before_stop | HistGradientBoostingClassifier |
| target_before_stop_calibrator | IdentityProbabilityCalibrator |

### Mandatory Development Gate Table

| Gate ID | Category | Scope | Metric | Actual | Comparator | Threshold | Status | Reason | Evidence source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_holdout_required_for_promotion | research integrity | model | holdout_status | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | FAIL | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. | model_evaluation |
| minimum_training_samples | data sufficiency | prediction | training_samples | 41884 | >= | 200 | PASS | Training sample count meets configured minimum. | model_evaluation |
| minimum_unseen_observations | data sufficiency | prediction | holdout_samples | 17069 | >= | 80 | PASS | Holdout observation count meets configured minimum. | model_evaluation |
| brier_skill_vs_naive_positive | predictive skill | prediction | brier_skill_score | 0.00729969199504 | > | 0 | PASS | Model Brier is better than matching direction/horizon naive control. | model_evaluation |
| holdout_brier_max_035 | calibration | prediction | holdout_brier | 0.247874126013 | <= | 0.35 | PASS | Holdout Brier is within configured maximum. | model_evaluation |
| positive_expected_value_after_costs | selected-candidate quality | selected_candidates | holdout_mean_return_lcb_90 | 0.00178036121833 | > | -0.0005 | PASS | Lower confidence bound is above negative round-trip cost. | model_evaluation |
| profit_factor_min_090 | selected-candidate quality | selected_candidates | holdout_profit_factor | 2.37963857615 | >= | 0.9 | PASS | Profit factor 2.38 meets the minimum 0.90. | model_evaluation |
| portfolio_drawdown_available | portfolio performance | portfolio_holdout | portfolio_max_drawdown | -0.0521921770774 | is finite | finite | PASS | Portfolio drawdown was calculated from daily portfolio equity. | model_evaluation |
| portfolio_drawdown_not_worse_than_50pct | drawdown | portfolio_holdout | portfolio_max_drawdown | -0.0521921770774 | > | -0.5 | PASS | Portfolio drawdown passes configured limit. | model_evaluation |
| feature_stability_mean_abs_z_max_250 | feature stability | prediction | feature_stability_mean_abs_z | 0.0378749278954 | <= | 2.5 | PASS | Holdout feature distribution shift is within configured cap. | model_evaluation |
| symbol_concentration_max_050 | symbol concentration | selected_candidates | symbol_concentration_top | 0.333333333333 | <= | 0.5 | PASS | Symbol concentration 33.33% is within the maximum 50.00%. | model_evaluation |
| sector_concentration_max_080 | sector stability | selected_candidates | sector_concentration_top | 0.589743589744 | <= | 0.8 | PASS | Sector concentration 58.97% is within the maximum 80.00%. | model_evaluation |
| transaction_cost_sensitivity_not_collapsed | cost sensitivity | selected_candidates | holdout_double_cost_lcb_90 | 0.00128036121833 | > | -0.001 | PASS | Double-cost lower confidence bound remains above configured collapse threshold. | model_evaluation |
| prediction_turnover_max_050 | selection coverage | selected_candidates | prediction_turnover | 0.002284843869 | <= | 0.5 | PASS | Selected observation rate is within configured turnover cap. | model_evaluation |
| selection_rate_policy_configured | selection coverage | selected_candidates | selected_observation_rate | 0.002284843869 | <= configured max | 0.2 | PASS | Selected rate evaluated against configured maximum. | model_evaluation |
| temporal_fold_stability_evidence_available | temporal stability | selected_candidates | temporal_fold_evidence_status | AVAILABLE | is available | AVAILABLE | PASS | Temporal-fold stability evidence is available from 3 evaluable chronological folds. | model_evaluation |
| temporal_fold_stability_min_050 | temporal stability | selected_candidates | temporal_fold_positive_fraction | 1 | >= | 0.5 | PASS | Temporal-fold positive fraction 100.00% meets the minimum 50.00%. | model_evaluation |
| exceptional_period_concentration_max_060 | temporal stability | selected_candidates | exceptional_period_concentration_top | 0.451405374013 | <= | 0.6 | PASS | Exceptional-period concentration 45.14% is within the maximum 60.00%. | model_evaluation |
| comparison_controls_available | comparison control | prediction | rsi_control_columns_available | true | is true | true | PASS | RSI baseline/control columns are present. | model_evaluation |
| not_naive_control | comparison control | model | naive_control_family | false | is false | false | PASS | Model is not the naive control family. | model_evaluation |
| prediction_ood_governance_schema_version | prediction sanity | prediction | prediction_ood_governance_version | prediction_ood_governance_v2 | equals | prediction_ood_governance_v2 | PASS | Model artifact uses calibrated prediction OOD governance V2. | prediction_ood_governance_v2 |
| classification_prediction_values_finite | prediction sanity | classification | classification_prediction_nonfinite_count | 0 | == | 0 | PASS | All classification probabilities are finite. | prediction_ood_governance_v2 |
| classification_prediction_probability_contract_valid | prediction sanity | classification | classification_probability_out_of_range_count | 0 | == | 0 | PASS | Classification probabilities are finite and within [0, 1]. | prediction_ood_governance_v2 |
| classification_prediction_unit_contract_valid | prediction sanity | classification | prediction_unit_contract | decimal_return | equals | decimal_return | PASS | Scanner prediction units remain decimal returns for downstream evaluation. | prediction_ood_governance_v2 |
| return_prediction_values_finite | prediction sanity | regression:return | return_prediction_nonfinite_count | 0 | == | 0 | PASS | Expected Return predictions are finite. | prediction_ood_governance_v2 |
| return_prediction_unit_contract_valid | prediction sanity | regression:return | return_prediction_unit_contract | decimal_return | equals | decimal_return | PASS | Expected Return predictions use decimal-return units. | prediction_ood_governance_v2 |
| return_prediction_head_bound_mapping_valid | prediction sanity | regression:return | return_prediction_head_bound_mapping_valid | true | is true | true | PASS | Expected Return predictions use matching head, direction, and horizon bounds. | prediction_ood_governance_v2 |
| return_prediction_bounds_training_only | prediction sanity | regression:return | return_ood_bound_provenance | training_targets_only | equals | training_targets_only | PASS | Expected Return OOD bounds were fit from training targets only. | prediction_ood_governance_v2 |
| return_prediction_path_metric_sign_valid | prediction sanity | regression:return | return_prediction_path_metric_sign_valid | true | is true | true | PASS | Expected Return path-metric sign contract is valid. | prediction_ood_governance_v2 |
| return_calibration_ood_rate_acceptable | prediction sanity | regression:return | return_calibration_ood_rate | 0 | <= | 0.05 | PASS | Expected Return calibration OOD rate is within the 5% maximum. | prediction_ood_governance_v2 |
| return_holdout_ood_rate_acceptable | prediction sanity | regression:return | return_holdout_ood_rate | 0 | <= | 0.02 | PASS | Expected Return holdout OOD rate is within the frozen calibration-derived limit. | prediction_ood_governance_v2 |
| return_holdout_ood_q99_severity_acceptable | prediction sanity | regression:return | return_holdout_ood_q99_severity | 0 | <= | 0.1 | PASS | Expected Return holdout OOD q99 severity is within the frozen limit. | prediction_ood_governance_v2 |
| return_catastrophic_prediction_extrapolation_absent | prediction sanity | regression:return | return_holdout_ood_max_severity | 0 | <= | 1 | PASS | Expected Return maximum holdout OOD severity is not catastrophic. | prediction_ood_governance_v2 |
| mfe_prediction_values_finite | prediction sanity | regression:mfe | mfe_prediction_nonfinite_count | 0 | == | 0 | PASS | MFE predictions are finite. | prediction_ood_governance_v2 |
| mfe_prediction_unit_contract_valid | prediction sanity | regression:mfe | mfe_prediction_unit_contract | decimal_return | equals | decimal_return | PASS | MFE predictions use decimal-return units. | prediction_ood_governance_v2 |
| mfe_prediction_head_bound_mapping_valid | prediction sanity | regression:mfe | mfe_prediction_head_bound_mapping_valid | true | is true | true | PASS | MFE predictions use matching head, direction, and horizon bounds. | prediction_ood_governance_v2 |
| mfe_prediction_bounds_training_only | prediction sanity | regression:mfe | mfe_ood_bound_provenance | training_targets_only | equals | training_targets_only | PASS | MFE OOD bounds were fit from training targets only. | prediction_ood_governance_v2 |
| mfe_prediction_path_metric_sign_valid | prediction sanity | regression:mfe | mfe_prediction_path_metric_sign_valid | true | is true | true | PASS | MFE path-metric sign contract is valid. | prediction_ood_governance_v2 |
| mfe_required_path_head_active | prediction sanity | regression:mfe | mfe_path_head_capability_state | ACTIVE | equals | ACTIVE | PASS | MFE required path head is active. | linear_family_path_head_retirement_v1 |
| mfe_magnitude_domain_integrity_valid | prediction sanity | regression:mfe | mfe_domain_schema_version | path_metric_magnitude_domain_v1 | equals and diagnostics pass | path_metric_magnitude_domain_v1 | PASS | MFE uses domain-preserving magnitude modeling and valid signed outputs. | path_metric_magnitude_domain_v1 |
| mfe_calibration_ood_rate_acceptable | prediction sanity | regression:mfe | mfe_calibration_ood_rate | 0 | <= | 0.05 | PASS | MFE calibration OOD rate is within the 5% maximum. | prediction_ood_governance_v2 |
| mfe_holdout_ood_rate_acceptable | prediction sanity | regression:mfe | mfe_holdout_ood_rate | 0 | <= | 0.02 | PASS | MFE holdout OOD rate is within the frozen calibration-derived limit. | prediction_ood_governance_v2 |
| mfe_holdout_ood_q99_severity_acceptable | prediction sanity | regression:mfe | mfe_holdout_ood_q99_severity | 0 | <= | 0.1 | PASS | MFE holdout OOD q99 severity is within the frozen limit. | prediction_ood_governance_v2 |
| mfe_catastrophic_prediction_extrapolation_absent | prediction sanity | regression:mfe | mfe_holdout_ood_max_severity | 0 | <= | 1 | PASS | MFE maximum holdout OOD severity is not catastrophic. | prediction_ood_governance_v2 |
| mae_prediction_values_finite | prediction sanity | regression:mae | mae_prediction_nonfinite_count | 0 | == | 0 | PASS | MAE predictions are finite. | prediction_ood_governance_v2 |
| mae_prediction_unit_contract_valid | prediction sanity | regression:mae | mae_prediction_unit_contract | decimal_return | equals | decimal_return | PASS | MAE predictions use decimal-return units. | prediction_ood_governance_v2 |
| mae_prediction_head_bound_mapping_valid | prediction sanity | regression:mae | mae_prediction_head_bound_mapping_valid | true | is true | true | PASS | MAE predictions use matching head, direction, and horizon bounds. | prediction_ood_governance_v2 |
| mae_prediction_bounds_training_only | prediction sanity | regression:mae | mae_ood_bound_provenance | training_targets_only | equals | training_targets_only | PASS | MAE OOD bounds were fit from training targets only. | prediction_ood_governance_v2 |
| mae_prediction_path_metric_sign_valid | prediction sanity | regression:mae | mae_prediction_path_metric_sign_valid | true | is true | true | PASS | MAE path-metric sign contract is valid. | prediction_ood_governance_v2 |
| mae_required_path_head_active | prediction sanity | regression:mae | mae_path_head_capability_state | ACTIVE | equals | ACTIVE | PASS | MAE required path head is active. | linear_family_path_head_retirement_v1 |
| mae_magnitude_domain_integrity_valid | prediction sanity | regression:mae | mae_domain_schema_version | path_metric_magnitude_domain_v1 | equals and diagnostics pass | path_metric_magnitude_domain_v1 | PASS | MAE uses domain-preserving magnitude modeling and valid signed outputs. | path_metric_magnitude_domain_v1 |
| mae_calibration_ood_rate_acceptable | prediction sanity | regression:mae | mae_calibration_ood_rate | 0 | <= | 0.05 | PASS | MAE calibration OOD rate is within the 5% maximum. | prediction_ood_governance_v2 |
| mae_holdout_ood_rate_acceptable | prediction sanity | regression:mae | mae_holdout_ood_rate | 5.85857402308e-05 | <= | 0.02 | PASS | MAE holdout OOD rate is within the frozen calibration-derived limit. | prediction_ood_governance_v2 |
| mae_holdout_ood_q99_severity_acceptable | prediction sanity | regression:mae | mae_holdout_ood_q99_severity | 0.0779182905023 | <= | 0.1 | PASS | MAE holdout OOD q99 severity is within the frozen limit. | prediction_ood_governance_v2 |
| mae_catastrophic_prediction_extrapolation_absent | prediction sanity | regression:mae | mae_holdout_ood_max_severity | 0.0779182905023 | <= | 1 | PASS | MAE maximum holdout OOD severity is not catastrophic. | prediction_ood_governance_v2 |

All mandatory development gates pass except `final_holdout_required_for_promotion`, which fails because the model has only development-holdout evidence and has not yet collected prospective final-holdout evidence.

## Other Models In Generation

| Model ID | Direction | Family | Horizon | State | Why not enrolled |
| --- | --- | --- | --- | --- | --- |
| 108bc18cfa5be414666c2512 | bull | extra_trees | 10 | CANDIDATE | positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.; profit_factor_min_090: Profit factor is unavailable because no selected observations exist.; portfolio_drawdown_available: Portfolio drawdown is missing.; portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.; symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.; sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.; transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.; temporal_fold_stability_evidence_available: Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.; temporal_fold_stability_min_050: Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.; exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |
| 20ec5e2b936145463e2d22bf | bull | naive_base_rate | 10 | CANDIDATE | naive_control_excluded; symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.; sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.; exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected.; not_naive_control: Naive controls are never promotion eligible. |
| 4b25faeeca72518f3f435fa7 | bear | hist_gradient_boosting | 10 | CANDIDATE | temporal_fold_stability_min_050: Temporal-fold positive fraction 33.33% is below the minimum 50.00%.; exceptional_period_concentration_max_060: Exceptional-period concentration 92.10% exceeds the maximum 60.00%. |
| 4d66c49b675803520298a243 | bear | extra_trees | 10 | CANDIDATE | positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.; profit_factor_min_090: Profit factor is unavailable because no selected observations exist.; portfolio_drawdown_available: Portfolio drawdown is missing.; portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.; symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.; sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.; transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.; temporal_fold_stability_evidence_available: Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.; temporal_fold_stability_min_050: Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.; exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |
| 7a534a2fcf2a3e8f4e17a83f | bear | logistic_regression | 10 | CANDIDATE | mfe_path_head_retired_unsuitable_estimator; mae_path_head_retired_unsuitable_estimator; positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.; profit_factor_min_090: Profit factor is unavailable because no selected observations exist.; portfolio_drawdown_available: Portfolio drawdown is missing.; portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.; symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.; sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.; transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.; temporal_fold_stability_evidence_available: Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.; temporal_fold_stability_min_050: Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.; exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected.; return_calibration_ood_rate_acceptable: Expected Return calibration OOD rate exceeds the 5% maximum.; return_holdout_ood_rate_acceptable: Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; mfe_prediction_values_finite: MFE predictions include nonfinite values.; mfe_prediction_path_metric_sign_valid: MFE path-metric sign contract failed.; mfe_required_path_head_active: MFE required path head is not active: linear_family_path_head_retired_unsuitable_estimator.; mfe_magnitude_domain_integrity_valid: MFE is missing domain-preserving metadata or emitted invalid magnitude/signed predictions.; mfe_calibration_ood_rate_acceptable: MFE calibration OOD rate exceeds the 5% maximum.; mfe_holdout_ood_rate_acceptable: MFE holdout OOD rate exceeds the frozen calibration-derived limit.; mae_prediction_values_finite: MAE predictions include nonfinite values.; mae_prediction_path_metric_sign_valid: MAE path-metric sign contract failed.; mae_required_path_head_active: MAE required path head is not active: linear_family_path_head_retired_unsuitable_estimator.; mae_magnitude_domain_integrity_valid: MAE is missing domain-preserving metadata or emitted invalid magnitude/signed predictions.; mae_calibration_ood_rate_acceptable: MAE calibration OOD rate exceeds the 5% maximum.; mae_holdout_ood_rate_acceptable: MAE holdout OOD rate exceeds the frozen calibration-derived limit. |
| e502adcfe8cf8c25c3138ee3 | bear | naive_base_rate | 10 | CANDIDATE | naive_control_excluded; symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.; sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.; exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected.; not_naive_control: Naive controls are never promotion eligible.; return_calibration_ood_rate_acceptable: Expected Return calibration OOD rate exceeds the 5% maximum.; return_holdout_ood_rate_acceptable: Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| ed57a9e3a3be12fe39241f62 | bull | logistic_regression | 10 | CANDIDATE | mfe_path_head_retired_unsuitable_estimator; mae_path_head_retired_unsuitable_estimator; positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.; profit_factor_min_090: Profit factor is unavailable because no selected observations exist.; portfolio_drawdown_available: Portfolio drawdown is missing.; portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.; symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.; sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.; transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.; temporal_fold_stability_evidence_available: Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.; temporal_fold_stability_min_050: Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.; exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected.; mfe_prediction_values_finite: MFE predictions include nonfinite values.; mfe_prediction_path_metric_sign_valid: MFE path-metric sign contract failed.; mfe_required_path_head_active: MFE required path head is not active: linear_family_path_head_retired_unsuitable_estimator.; mfe_magnitude_domain_integrity_valid: MFE is missing domain-preserving metadata or emitted invalid magnitude/signed predictions.; mfe_calibration_ood_rate_acceptable: MFE calibration OOD rate exceeds the 5% maximum.; mfe_holdout_ood_rate_acceptable: MFE holdout OOD rate exceeds the frozen calibration-derived limit.; mae_prediction_values_finite: MAE predictions include nonfinite values.; mae_prediction_path_metric_sign_valid: MAE path-metric sign contract failed.; mae_required_path_head_active: MAE required path head is not active: linear_family_path_head_retired_unsuitable_estimator.; mae_magnitude_domain_integrity_valid: MAE is missing domain-preserving metadata or emitted invalid magnitude/signed predictions.; mae_calibration_ood_rate_acceptable: MAE calibration OOD rate exceeds the 5% maximum.; mae_holdout_ood_rate_acceptable: MAE holdout OOD rate exceeds the frozen calibration-derived limit. |

## Pre-Operation State

| Item | Value |
| --- | --- |
| Git branch | feat/autonomous-swing-scanner-v1 |
| Git commit | 3f3c4f853cc183e6a0a4900dadc428162c400ef7 |
| Git status before operation | ?? docs/NONLINEAR_MODEL_QUALITY_DIAGNOSIS_2026_06_25.md |
| Source/test status before operation | (clean) |
| SQLite path | state/engine.sqlite3 |
| SQLite size before | 250183680 bytes |
| SQLite mtime before | 2026-06-25T13:47:57.796495+00:00 |
| Model artifact hash before | 86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e |
| Feature-manifest hash before | 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5 |
| Selection-policy hash before | ff689a7edf893b56 |
| Target-Before-Stop calibration hash before | 960b3a8998810405 |
| OOD-governance hash before | 7e01d1c511753fa0 |
| Path-head capability hash before | 4d1cf245922115a2 |
| final_holdout_runs count before | 0 |
| final-holdout event count before | 0 |
| ordinary forward-event count before | 285 |
| scanner snapshot count before | 17 |
| latest common completed local market session before | 2026-06-18 |

## Market Data And Feature Refresh

Commands run:

```bash
.venv/bin/python -m swing_rsi.cli universe-update
.venv/bin/python -m swing_rsi.cli build-features
```

| Item | Value |
| --- | --- |
| Symbols attempted | 35 |
| Symbols successfully updated | 35 |
| Symbol errors | 0 |
| Latest common completed session | 2026-06-25 |
| Feature snapshot as-of date | 2026-06-25 |
| Feature manifest hash after refresh | 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5 |
| Feature rows | 90113 |
| Model artifact hash changed | False |
| Selection policy changed | False |
| TBS calibration changed | False |
| OOD governance changed | False |
| Path-head capability changed | False |
| Model artifact inventory changed | False |

### Latest Date By Enabled Symbol

| Symbol | Latest raw date |
| --- | --- |
| AAPL | 2026-06-25 |
| AMD | 2026-06-25 |
| AMZN | 2026-06-25 |
| DIA | 2026-06-25 |
| GOOGL | 2026-06-25 |
| IWM | 2026-06-25 |
| META | 2026-06-25 |
| MSFT | 2026-06-25 |
| NVDA | 2026-06-25 |
| QID | 2026-06-25 |
| QQQ | 2026-06-25 |
| RWM | 2026-06-25 |
| SDS | 2026-06-25 |
| SH | 2026-06-25 |
| SOXL | 2026-06-25 |
| SOXS | 2026-06-25 |
| SPXU | 2026-06-25 |
| SPY | 2026-06-25 |
| SQQQ | 2026-06-25 |
| TNA | 2026-06-25 |
| TQQQ | 2026-06-25 |
| TSLA | 2026-06-25 |
| TZA | 2026-06-25 |
| UPRO | 2026-06-25 |
| XLB | 2026-06-25 |
| XLC | 2026-06-25 |
| XLE | 2026-06-25 |
| XLF | 2026-06-25 |
| XLI | 2026-06-25 |
| XLK | 2026-06-25 |
| XLP | 2026-06-25 |
| XLRE | 2026-06-25 |
| XLU | 2026-06-25 |
| XLV | 2026-06-25 |
| XLY | 2026-06-25 |

## Frozen Final-Holdout Run

Command run:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation 2026-06-25T13:11:51.610283+00:00
```

| Item | Value |
| --- | --- |
| Run ID | 3493ee8ac37bf96475c362e1 |
| Enrolled model ID | b93b2258c10aea5cef81d291 |
| Model generation | 2026-06-25T13:11:51.610283+00:00 |
| Direction | bull |
| Horizon | 10 sessions |
| Creation timestamp UTC | 2026-06-25T20:51:56.242498+00:00 |
| Baseline market date | 2026-06-25 |
| First eligible future signal date | None |
| First eligible rule | as_of_date > 2026-06-25 |
| Frozen universe snapshot ID | 6b1a74750684506e1a5b |
| Frozen feature schema/manifest hash | 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5 |
| Frozen model artifact hash | 86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e |
| Frozen selection-policy hash | ff689a7edf893b56 |
| Frozen calibration-governance hash | 960b3a8998810405 |
| Frozen OOD-governance hash | 7e01d1c511753fa0 |
| Frozen path-head capability hash | 4d1cf245922115a2 |
| Frozen execution-policy hash | b31550c14429a01c |
| Frozen code commit hash | 3f3c4f853cc183e6a0a4900dadc428162c400ef7 |
| Model training code commit hash | 67b4e17787d7d40cef7bd05118dc94165151a6c7 |
| Final-holdout sample-governance version | prospective_final_holdout_sample_v1 |
| Final-holdout sample-governance hash | 4ae8415df04cd538 |
| Baseline equals latest common completed session | True |

No signal with `as_of_date <= 2026-06-25` is eligible under the frozen rule `as_of_date > 2026-06-25`.

## No-Backfill Verification

| Item | Value |
| --- | --- |
| Historical signals created | 0 |
| Historical predictions backfilled | 0 |
| Pending entries | 0 |
| Open positions | 0 |
| Closed positions | 0 |
| Matured outcomes | 0 |
| Final-holdout events created from prior sessions | 0 |
| Backfill-blocked events | 0 |
| Run status | CREATED |
| Model sample status | COLLECTING |

## Status Output

Command run:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-status
```

| run_id | model_id | run_status | model_status | baseline_market_date | first_eligible_future_signal_date | latest_processed_market_date | matured_outcomes | matured_outcomes_required | distinct_signal_dates | distinct_signal_dates_required | observation_sessions | observation_sessions_required | calendar_months | calendar_months_required | positive_outcomes | positive_outcomes_required | negative_outcomes | negative_outcomes_required | pending_entries | open_positions | provenance_failures | blocked_backfills | invalidated_outcomes | artifact_integrity_status | estimated_remaining_requirement | promotion_eligible | event_count | signals | rejected_signals | label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3493ee8ac37bf96475c362e1 | b93b2258c10aea5cef81d291 | CREATED | COLLECTING | 2026-06-25 |  |  | 0 | 100 | 0 | 60 | 0 | 126 | 0 | 4 | 0 | 20 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | PASS | calendar_months:4; matured:100; negative:20; observation_sessions:126; positive:20; signal_dates:60 | false | 0 | 0 | 0 | Prospective shadow validation. Not a live trade recommendation. |

### Progress Requirements

| Requirement | Current | Required |
| --- | ---: | ---: |
| Matured outcomes | 0 | 100 |
| Distinct signal dates | 0 | 60 |
| Observation sessions | 0 | 126 |
| Calendar months | 0 | 4 |
| Positive outcomes | 0 | 20 |
| Negative outcomes | 0 | 20 |
| Provenance failures | 0 | 0 |
| Blocked backfills | 0 | 0 |
| Data invalidations | 0 | 0 |

| Item | Value |
| --- | --- |
| Artifact-integrity status | PASS |
| Artifact-integrity reason | ok |
| Early-diagnostic status | False |
| Final-evaluation readiness | False |
| Promotion eligibility | NO |
| Promotion blocked reasons | final_holdout_required_for_promotion: Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |

### Sample-Governance Gates

| Gate ID | Actual | Status | Reason |
| --- | --- | --- | --- |
| final_holdout_policy_configured | 4ae8415df04cd538 | PASS | Frozen sample policy matches the configured schema and hash. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_matured_outcomes_min_100 | 0 | FAIL | Matured outcomes 0 is below the minimum 100. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_distinct_signal_dates_min_60 | 0 | FAIL | Distinct signal dates 0 is below the minimum 60. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_observation_sessions_min_126 | 0 | FAIL | Observation sessions 0 is below the minimum 126. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_calendar_months_min_4 | 0 | FAIL | Calendar months 0 is below the minimum 4. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_positive_class_min_20 | 0 | FAIL | Positive outcomes 0 is below the minimum 20. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_negative_class_min_20 | 0 | FAIL | Negative outcomes 0 is below the minimum 20. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_provenance_valid | 0 | PASS | Every included prediction has prospective ingestion provenance. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_backfill_absent | 0 | PASS | No blocked backfill events are included. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_data_integrity_valid | 0 | PASS | Data-integrity event count is zero. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_frozen_artifacts_unchanged | true | PASS | Frozen artifact, feature, policy, calibrator, OOD, execution, and code hashes match enrollment. Policy version: prospective_final_holdout_sample_v1. |
| final_holdout_sample_sufficient | false | FAIL | At least one mandatory sample, provenance, or integrity gate fails. Policy version: prospective_final_holdout_sample_v1. |

## Daily Operating Procedure

After each genuinely later completed daily session, run exactly this prospective cycle:

```bash
.venv/bin/python -m swing_rsi.cli universe-update
.venv/bin/python -m swing_rsi.cli build-features
.venv/bin/python -m swing_rsi.cli final-holdout-update
.venv/bin/python -m swing_rsi.cli final-holdout-status
```

Supported command notes confirmed from the repository CLI:

| Command | Supported arguments |
| --- | --- |
| `universe-update` | optional `--universe`, `--start`, `--end`, `--lookback-years` |
| `build-features` | optional `--universe` |
| `final-holdout-update` | no required arguments |
| `final-holdout-status` | no required arguments |

No future-session cycle was run during this enrollment. The run has no `latest_processed_market_date`; a final-holdout update should process only a completed market session later than `2026-06-25`.

## State-Integrity Verification

| Item | Before | After | Result |
| --- | ---: | ---: | --- |
| final_holdout_runs | 0 | 1 | exactly one new run |
| final-holdout events | 0 | 0 | unchanged |
| ordinary forward events | 285 | 285 | unchanged |
| scanner snapshots | 17 | 17 | unchanged |
| model artifact inventory hash | 3f6fa647774c4fcd32ba2d710b6ac095ce98e6c8478a7e58fc206aec15215ea5 | 3f6fa647774c4fcd32ba2d710b6ac095ce98e6c8478a7e58fc206aec15215ea5 | unchanged |
| scanner artifact inventory hash | 12d6af24c84b7f91eff50b183d7a0ae52424d434554476a4ac455d0b8c6cc80d | 12d6af24c84b7f91eff50b183d7a0ae52424d434554476a4ac455d0b8c6cc80d | unchanged |

| Check | Result |
| --- | --- |
| Source files changed | 0 |
| Test files changed | 0 |
| Source/test Git status after operation | (clean) |
| Model artifacts changed | 0 |
| Old scanner snapshots changed | 0 |
| Old ordinary forward events changed | 0 |
| Old final-holdout events changed | 0 |
| Prior model generations changed | 0 |
| Model promoted | no |
| Paper trade opened | no |
| Backfilled prediction created | no |
| Final Git status before handoff file write | ?? docs/NONLINEAR_MODEL_QUALITY_DIAGNOSIS_2026_06_25.md |

SQLite changed only because the operational enrollment inserted the new prospective final-holdout run. Market data and feature snapshots changed only through the explicitly requested universe and feature refresh. These generated operational artifacts were not committed.
