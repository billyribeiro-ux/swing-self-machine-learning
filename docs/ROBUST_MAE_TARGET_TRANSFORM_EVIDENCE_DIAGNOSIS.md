# Robust MAE Target Transform Evidence Diagnosis

Generated: `2026-06-27T16:42:13.979298+00:00`

Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Development branch: `feat/product-class-specialist-challengers-v1`

Development HEAD: `7769a123ae399d71aae2d36dc6429aa18313731e`

New generation diagnosed: `2026-06-27T14:05:10.073173+00:00`

Baseline generation compared: `2026-06-26T23:52:15.769542+00:00`

Operational repository checked read-only: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

## Summary Verdict

Robust MAE Target Transformation V1 changed the diagnosed source and did not create broader promotion evidence.

- The scoped POOLED bull HistGradientBoosting MAE warning pattern was removed: MAE OOD count `6 -> 0`.
- The affected head still has no sign-contract violations and no nonfinite predictions.
- Selected-candidate and portfolio evidence for the affected model did not move: selected rows stayed `96`, lower 90% confidence bound stayed `0.0147344`, and portfolio max drawdown stayed `-0.0845721`.
- All `30` models in the new generation remain `CANDIDATE`; no model was promoted.
- The only failed gate on the transformed affected model remains `final_holdout_required_for_promotion`.
- This is development-holdout diagnostic evidence only, not final performance proof.

## Generation Integrity

| item | value |
| --- | --- |
| old generation model rows | 30 |
| new generation model rows | 30 |
| new generation states | {'CANDIDATE': 30} |
| new generation promoted models | 0 |
| scope counts | {'INVERSE': 6, 'LEVERAGED_INVERSE': 6, 'LEVERAGED_LONG': 6, 'ORDINARY': 6, 'POOLED': 6} |
| development scanner snapshots | 3 |
| development scanner candidates | 150 |
| development forward events | 0 |
| development final-holdout runs | 0 |

## Model Matrix

| model_id | scope | dir | family | state | h | train | cal | holdout | selected | MAE transform | MAE OOD | failed gates | promoted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 77d1a8380d530a1948befacf | INVERSE | bear | extra_trees | CANDIDATE | 10 | 2424 | 966 | 977 | 20 | none | 0 | 2 | NO |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | CANDIDATE | 10 | 2424 | 966 | 977 | 0 | none | 0 | 7 | NO |
| a42bd8862a72b965215e40c5 | INVERSE | bear | naive_base_rate | CANDIDATE | 10 | 2424 | 966 | 977 | 0 | none | 0 | 5 | NO |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | CANDIDATE | 10 | 2424 | 966 | 977 | 0 | none | 0 | 7 | NO |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | CANDIDATE | 10 | 2424 | 966 | 977 | 0 | none | 0 | 8 | NO |
| 4748157b5a0300d929ba6e24 | INVERSE | bull | naive_base_rate | CANDIDATE | 10 | 2424 | 966 | 977 | 0 | none | 0 | 5 | NO |
| cc03f04f0532cca6ce5d39fd | LEVERAGED_INVERSE | bear | extra_trees | CANDIDATE | 10 | 7219 | 2901 | 2927 | 109 | none | 0 | 2 | NO |
| 9618e114cade8b396bb1ec60 | LEVERAGED_INVERSE | bear | hist_gradient_boosting | CANDIDATE | 10 | 7219 | 2901 | 2927 | 87 | none | 0 | 3 | NO |
| ab6b20afabb330bc6293beea | LEVERAGED_INVERSE | bear | naive_base_rate | CANDIDATE | 10 | 7219 | 2901 | 2927 | 0 | none | 0 | 4 | NO |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | CANDIDATE | 10 | 7219 | 2901 | 2927 | 0 | none | 0 | 7 | NO |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | CANDIDATE | 10 | 7219 | 2901 | 2927 | 7 | none | 0 | 8 | NO |
| a06ce5c18ebf9632e6e4f6cc | LEVERAGED_INVERSE | bull | naive_base_rate | CANDIDATE | 10 | 7219 | 2901 | 2927 | 0 | none | 0 | 4 | NO |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | CANDIDATE | 10 | 4828 | 1932 | 1955 | 0 | none | 0 | 8 | NO |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | CANDIDATE | 10 | 4828 | 1932 | 1955 | 0 | none | 0 | 7 | NO |
| b32f46d83556d9983d14944e | LEVERAGED_LONG | bear | naive_base_rate | CANDIDATE | 10 | 4828 | 1932 | 1955 | 0 | none | 0 | 5 | NO |
| 7521f91e8dde523d189d29f8 | LEVERAGED_LONG | bull | extra_trees | CANDIDATE | 10 | 4828 | 1932 | 1955 | 8 | none | 0 | 3 | NO |
| d3912064315532441405d4cb | LEVERAGED_LONG | bull | hist_gradient_boosting | CANDIDATE | 10 | 4828 | 1932 | 1955 | 18 | none | 0 | 2 | NO |
| 6825a3ac15bcb325f37755ae | LEVERAGED_LONG | bull | naive_base_rate | CANDIDATE | 10 | 4828 | 1932 | 1955 | 0 | none | 0 | 5 | NO |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | CANDIDATE | 10 | 27483 | 11036 | 11211 | 0 | none | 0 | 8 | NO |
| 1a78f1917154bd1e14b2872b | ORDINARY | bear | hist_gradient_boosting | CANDIDATE | 10 | 27483 | 11036 | 11211 | 1 | none | 0 | 5 | NO |
| 1287bcd6f42a4190d9b73521 | ORDINARY | bear | naive_base_rate | CANDIDATE | 10 | 27483 | 11036 | 11211 | 0 | none | 0 | 5 | NO |
| 36a05aec82d71c902ad3e873 | ORDINARY | bull | extra_trees | CANDIDATE | 10 | 27483 | 11036 | 11211 | 67 | none | 0 | 2 | NO |
| e521f1bcffbbdc8047f6d183 | ORDINARY | bull | hist_gradient_boosting | CANDIDATE | 10 | 27483 | 11036 | 11211 | 62 | none | 0 | 2 | NO |
| 412e59d9e059890608eac4de | ORDINARY | bull | naive_base_rate | CANDIDATE | 10 | 27483 | 11036 | 11211 | 0 | none | 0 | 5 | NO |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | CANDIDATE | 10 | 41954 | 16835 | 17070 | 0 | none | 0 | 7 | NO |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | CANDIDATE | 10 | 41954 | 16835 | 17070 | 0 | none | 0 | 7 | NO |
| 8adb063ccf2ca5d0e5b04e3b | POOLED | bear | naive_base_rate | CANDIDATE | 10 | 41954 | 16835 | 17070 | 0 | none | 0 | 4 | NO |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | CANDIDATE | 10 | 41954 | 16835 | 17070 | 0 | none | 0 | 7 | NO |
| 5b3f37a96a7968bca8d2f398 | POOLED | bull | hist_gradient_boosting | CANDIDATE | 10 | 41954 | 16835 | 17070 | 96 | log1p | 0 | 1 | NO |
| c852c44ecddcd7300ca1ac0e | POOLED | bull | naive_base_rate | CANDIDATE | 10 | 41954 | 16835 | 17070 | 0 | none | 0 | 2 | NO |

## Transform Isolation

Exactly `1` model in the new generation has a non-`none` MAE target transform.

| model_id | scope | MAE transform | MAE transform hash | MFE transform | return OOD | MFE OOD | MAE OOD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | none | 5529c7b1f2b7d409 | none | 0 | 0 | 0 |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | none | 3b8ea8445112b99b | none | 0 | 0 | 0 |
| d3912064315532441405d4cb | LEVERAGED_LONG | none | 22699adc98d7dd6b | none | 0 | 0 | 0 |
| e521f1bcffbbdc8047f6d183 | ORDINARY | none | 30f7bb744d0fdd42 | none | 0 | 0 | 0 |
| 5b3f37a96a7968bca8d2f398 | POOLED | log1p | c3c93ddb06ea5504 | none | 0 | 0 | 0 |

Conclusion: the transform is isolated to the intended POOLED bull HistGradientBoosting MAE head. Other bull HistGradientBoosting scopes remain untransformed; ExtraTrees, bear, MFE, expected-return, Target-Before-Stop, and naive controls are not transformed.

## Affected Head Old Versus New

| metric | baseline | post-transform |
| --- | --- | --- |
| model_id | 85b258623a68620ad108b08c | 5b3f37a96a7968bca8d2f398 |
| MAE transform | legacy | log1p |
| MAE transform hash |  | c3c93ddb06ea5504 |
| MAE OOD count | 6 | 0 |
| MAE OOD rate | 0.000351494 | 0 |
| MAE q99 severity | 0.0728609 | 0 |
| MAE max severity | 0.0737479 | 0 |
| MAE signed-domain violations | 0 | 0 |
| MAE nonfinite predictions | 0 | 0 |
| MAE error | 0.038103 | 0.0315783 |
| MAE RMSE | 0.0575066 | 0.0496293 |
| selected rows | 96 | 96 |
| mean selected net return | 0.0285433 | 0.0285433 |
| LCB 90 | 0.0147344 | 0.0147344 |
| profit factor | 3.57141 | 3.57141 |
| portfolio total return | 0.353924 | 0.353924 |
| portfolio max drawdown | -0.0845721 | -0.0845721 |
| failed mandatory gates | final_holdout_required_for_promotion | final_holdout_required_for_promotion |

Interpretation:

- The six development-holdout MAE prediction-support warnings did not recur.
- The fix reduced the affected head MAE error and RMSE, but the selected candidate set and portfolio evidence are unchanged.
- The model did not become promotion eligible; prospective final-holdout evidence is still absent.

## Broader Evidence Check

Pairing key: `product_class_scope + direction + family + horizon`.

| item | count |
| --- | --- |
| pairs | 30 |
| state_changes | 0 |
| promotion_changes | 0 |
| selected_count_changes | 0 |
| failed_gate_count_changes | 0 |
| mae_ood_count_changes | 1 |
| return_ood_count_changes | 0 |
| mfe_ood_count_changes | 0 |
| material_metric_changes | 1 |

Changed metric pairs:

| scope | dir | family | old model | new model | old selected | new selected | old brier skill | new brier skill | old return rank | new return rank | old return MAE | new return MAE | old MAE OOD | new MAE OOD | old MAE max sev | new MAE max sev | old failed | new failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POOLED | bull | hist_gradient_boosting | 85b258623a68620ad108b08c | 5b3f37a96a7968bca8d2f398 | 96 | 96 | 0.00755501 | 0.00755501 | 0.1427 | 0.1427 | 0.0547823 | 0.0547823 | 6 | 0 | 0.0737479 | 0 | 1 | 1 |

Classification: `FIT_AND_OOD_SOURCE_CORRECTION_ONLY`.

Reason: the only material tracked evidence change is the intended POOLED bull HistGradientBoosting MAE path-head prediction distribution and its OOD warning count. Registry states, promotion status, forward/final-holdout state, and selected evidence did not improve into an operationally eligible state.

## Failed Mandatory Gates

| model | scope | dir | family | gate | category | actual | cmp | threshold | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 77d1a8380d530a1948befacf | INVERSE | bear | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 77d1a8380d530a1948befacf | INVERSE | bear | extra_trees | exceptional_period_concentration_max_060 | temporal stability | 0.732405 | <= | 0.6 | Exceptional-period concentration 73.24% exceeds the maximum 60.00%. |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| c85c4b8dabb1b19555dd1928 | INVERSE | bear | hist_gradient_boosting | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| a42bd8862a72b965215e40c5 | INVERSE | bear | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| a42bd8862a72b965215e40c5 | INVERSE | bear | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| a42bd8862a72b965215e40c5 | INVERSE | bear | naive_base_rate | return_calibration_ood_rate_acceptable | prediction sanity | 0.180124 | <= | 0.05 | Expected Return calibration OOD rate exceeds the 5% maximum. |
| a42bd8862a72b965215e40c5 | INVERSE | bear | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.0665302 | <= | 0.05 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| a42bd8862a72b965215e40c5 | INVERSE | bear | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.685264 | <= | 0.5 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 48dc86e812a26c0d472924c8 | INVERSE | bull | extra_trees | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | brier_skill_vs_naive_positive | predictive skill | -0.00637986 | > | 0 | Model Brier is not better than the matching naive control. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| a8d580bda4ba9364f4ca9bc9 | INVERSE | bull | hist_gradient_boosting | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| 4748157b5a0300d929ba6e24 | INVERSE | bull | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 4748157b5a0300d929ba6e24 | INVERSE | bull | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| 4748157b5a0300d929ba6e24 | INVERSE | bull | naive_base_rate | return_calibration_ood_rate_acceptable | prediction sanity | 0.196687 | <= | 0.05 | Expected Return calibration OOD rate exceeds the 5% maximum. |
| 4748157b5a0300d929ba6e24 | INVERSE | bull | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.0757421 | <= | 0.05 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| 4748157b5a0300d929ba6e24 | INVERSE | bull | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.740991 | <= | 0.5 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| cc03f04f0532cca6ce5d39fd | LEVERAGED_INVERSE | bear | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| cc03f04f0532cca6ce5d39fd | LEVERAGED_INVERSE | bear | extra_trees | exceptional_period_concentration_max_060 | temporal stability | 0.601158 | <= | 0.6 | Exceptional-period concentration 60.12% exceeds the maximum 60.00%. |
| 9618e114cade8b396bb1ec60 | LEVERAGED_INVERSE | bear | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 9618e114cade8b396bb1ec60 | LEVERAGED_INVERSE | bear | hist_gradient_boosting | brier_skill_vs_naive_positive | predictive skill | -0.00644428 | > | 0 | Model Brier is not better than the matching naive control. |
| 9618e114cade8b396bb1ec60 | LEVERAGED_INVERSE | bear | hist_gradient_boosting | exceptional_period_concentration_max_060 | temporal stability | 0.903355 | <= | 0.6 | Exceptional-period concentration 90.34% exceeds the maximum 60.00%. |
| ab6b20afabb330bc6293beea | LEVERAGED_INVERSE | bear | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| ab6b20afabb330bc6293beea | LEVERAGED_INVERSE | bear | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| ab6b20afabb330bc6293beea | LEVERAGED_INVERSE | bear | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.0351896 | <= | 0.02318 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| ab6b20afabb330bc6293beea | LEVERAGED_INVERSE | bear | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.216773 | <= | 0.142978 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 74ed8ea5d70b10bdeb63a043 | LEVERAGED_INVERSE | bull | extra_trees | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | brier_skill_vs_naive_positive | predictive skill | -0.00317158 | > | 0 | Model Brier is not better than the matching naive control. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | positive_expected_value_after_costs | selected-candidate quality | -0.0550243 | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | profit_factor_min_090 | selected-candidate quality | 0.602999 | >= | 0.9 | Profit factor 0.60 is below the minimum 0.90. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | symbol_concentration_max_050 | symbol concentration | 0.714286 | <= | 0.5 | Symbol concentration 71.43% exceeds the maximum 50.00%. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | transaction_cost_sensitivity_not_collapsed | cost sensitivity | -0.0555243 | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | temporal_fold_stability_min_050 | temporal stability | 0.333333 | >= | 0.5 | Temporal-fold positive fraction 33.33% is below the minimum 50.00%. |
| 8d15b9846da1e3f7568cbdfa | LEVERAGED_INVERSE | bull | hist_gradient_boosting | exceptional_period_concentration_max_060 | temporal stability | 0.782686 | <= | 0.6 | Exceptional-period concentration 78.27% exceeds the maximum 60.00%. |
| a06ce5c18ebf9632e6e4f6cc | LEVERAGED_INVERSE | bull | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| a06ce5c18ebf9632e6e4f6cc | LEVERAGED_INVERSE | bull | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| a06ce5c18ebf9632e6e4f6cc | LEVERAGED_INVERSE | bull | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.0283567 | <= | 0.02 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| a06ce5c18ebf9632e6e4f6cc | LEVERAGED_INVERSE | bull | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.159741 | <= | 0.1 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | brier_skill_vs_naive_positive | predictive skill | -0.134936 | > | 0 | Model Brier is not better than the matching naive control. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 6a5985f41c142955c12f455e | LEVERAGED_LONG | bear | extra_trees | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 7b2d5fa67aed8f0d6f1872e5 | LEVERAGED_LONG | bear | hist_gradient_boosting | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| b32f46d83556d9983d14944e | LEVERAGED_LONG | bear | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| b32f46d83556d9983d14944e | LEVERAGED_LONG | bear | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| b32f46d83556d9983d14944e | LEVERAGED_LONG | bear | naive_base_rate | return_calibration_ood_rate_acceptable | prediction sanity | 0.336957 | <= | 0.05 | Expected Return calibration OOD rate exceeds the 5% maximum. |
| b32f46d83556d9983d14944e | LEVERAGED_LONG | bear | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.318159 | <= | 0.05 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| b32f46d83556d9983d14944e | LEVERAGED_LONG | bear | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.828546 | <= | 0.5 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 7521f91e8dde523d189d29f8 | LEVERAGED_LONG | bull | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 7521f91e8dde523d189d29f8 | LEVERAGED_LONG | bull | extra_trees | brier_skill_vs_naive_positive | predictive skill | -0.0816998 | > | 0 | Model Brier is not better than the matching naive control. |
| 7521f91e8dde523d189d29f8 | LEVERAGED_LONG | bull | extra_trees | exceptional_period_concentration_max_060 | temporal stability | 0.784728 | <= | 0.6 | Exceptional-period concentration 78.47% exceeds the maximum 60.00%. |
| d3912064315532441405d4cb | LEVERAGED_LONG | bull | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| d3912064315532441405d4cb | LEVERAGED_LONG | bull | hist_gradient_boosting | exceptional_period_concentration_max_060 | temporal stability | 0.688205 | <= | 0.6 | Exceptional-period concentration 68.82% exceeds the maximum 60.00%. |
| 6825a3ac15bcb325f37755ae | LEVERAGED_LONG | bull | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 6825a3ac15bcb325f37755ae | LEVERAGED_LONG | bull | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| 6825a3ac15bcb325f37755ae | LEVERAGED_LONG | bull | naive_base_rate | return_calibration_ood_rate_acceptable | prediction sanity | 0.229296 | <= | 0.05 | Expected Return calibration OOD rate exceeds the 5% maximum. |
| 6825a3ac15bcb325f37755ae | LEVERAGED_LONG | bull | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.147315 | <= | 0.05 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| 6825a3ac15bcb325f37755ae | LEVERAGED_LONG | bull | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.730291 | <= | 0.5 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | brier_skill_vs_naive_positive | predictive skill | -0.00388394 | > | 0 | Model Brier is not better than the matching naive control. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 41609c0ebb5988420f1e0c55 | ORDINARY | bear | extra_trees | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| 1a78f1917154bd1e14b2872b | ORDINARY | bear | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 1a78f1917154bd1e14b2872b | ORDINARY | bear | hist_gradient_boosting | symbol_concentration_max_050 | symbol concentration | 1 | <= | 0.5 | Symbol concentration 100.00% exceeds the maximum 50.00%. |
| 1a78f1917154bd1e14b2872b | ORDINARY | bear | hist_gradient_boosting | sector_concentration_max_080 | sector stability | 1 | <= | 0.8 | Sector concentration 100.00% exceeds the maximum 80.00%. |
| 1a78f1917154bd1e14b2872b | ORDINARY | bear | hist_gradient_boosting | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 1 folds contained selected observations. |
| 1a78f1917154bd1e14b2872b | ORDINARY | bear | hist_gradient_boosting | exceptional_period_concentration_max_060 | temporal stability | 1 | <= | 0.6 | Exceptional-period concentration 100.00% exceeds the maximum 60.00%. |
| 1287bcd6f42a4190d9b73521 | ORDINARY | bear | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 1287bcd6f42a4190d9b73521 | ORDINARY | bear | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| 1287bcd6f42a4190d9b73521 | ORDINARY | bear | naive_base_rate | return_calibration_ood_rate_acceptable | prediction sanity | 0.193911 | <= | 0.05 | Expected Return calibration OOD rate exceeds the 5% maximum. |
| 1287bcd6f42a4190d9b73521 | ORDINARY | bear | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.158683 | <= | 0.05 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| 1287bcd6f42a4190d9b73521 | ORDINARY | bear | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.602865 | <= | 0.5 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 36a05aec82d71c902ad3e873 | ORDINARY | bull | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 36a05aec82d71c902ad3e873 | ORDINARY | bull | extra_trees | brier_skill_vs_naive_positive | predictive skill | -0.00125895 | > | 0 | Model Brier is not better than the matching naive control. |
| e521f1bcffbbdc8047f6d183 | ORDINARY | bull | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| e521f1bcffbbdc8047f6d183 | ORDINARY | bull | hist_gradient_boosting | exceptional_period_concentration_max_060 | temporal stability | 0.996347 | <= | 0.6 | Exceptional-period concentration 99.63% exceeds the maximum 60.00%. |
| 412e59d9e059890608eac4de | ORDINARY | bull | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 412e59d9e059890608eac4de | ORDINARY | bull | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| 412e59d9e059890608eac4de | ORDINARY | bull | naive_base_rate | return_calibration_ood_rate_acceptable | prediction sanity | 0.153226 | <= | 0.05 | Expected Return calibration OOD rate exceeds the 5% maximum. |
| 412e59d9e059890608eac4de | ORDINARY | bull | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.101775 | <= | 0.05 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| 412e59d9e059890608eac4de | ORDINARY | bull | naive_base_rate | return_holdout_ood_q99_severity_acceptable | prediction sanity | 0.516039 | <= | 0.5 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 585a7d6fb397dc36f665d319 | POOLED | bear | extra_trees | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| 1da4716cec063e1534c7dd87 | POOLED | bear | hist_gradient_boosting | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| 8adb063ccf2ca5d0e5b04e3b | POOLED | bear | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| 8adb063ccf2ca5d0e5b04e3b | POOLED | bear | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |
| 8adb063ccf2ca5d0e5b04e3b | POOLED | bear | naive_base_rate | return_calibration_ood_rate_acceptable | prediction sanity | 0.0951589 | <= | 0.05 | Expected Return calibration OOD rate exceeds the 5% maximum. |
| 8adb063ccf2ca5d0e5b04e3b | POOLED | bear | naive_base_rate | return_holdout_ood_rate_acceptable | prediction sanity | 0.0516696 | <= | 0.05 | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | positive_expected_value_after_costs | selected-candidate quality | NOT_AVAILABLE | > | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | profit_factor_min_090 | selected-candidate quality | NOT_AVAILABLE | >= | 0.9 | Profit factor is unavailable because no selected observations exist. |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | portfolio_drawdown_available | portfolio performance | NOT_AVAILABLE | is finite | finite | Portfolio drawdown is missing. |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | portfolio_drawdown_not_worse_than_50pct | drawdown | NOT_AVAILABLE | > | -0.5 | Portfolio drawdown is missing or worse than configured limit. |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | transaction_cost_sensitivity_not_collapsed | cost sensitivity | NOT_AVAILABLE | > | -0.001 | Double-cost lower confidence bound fails or is missing. |
| c12b498bb164db0290168d0c | POOLED | bull | extra_trees | temporal_fold_stability_evidence_available | temporal stability | UNAVAILABLE | is available | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| 5b3f37a96a7968bca8d2f398 | POOLED | bull | hist_gradient_boosting | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| c852c44ecddcd7300ca1ac0e | POOLED | bull | naive_base_rate | final_holdout_required_for_promotion | research integrity | DEVELOPMENT_HOLDOUT | equals | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| c852c44ecddcd7300ca1ac0e | POOLED | bull | naive_base_rate | not_naive_control | comparison control | YES | is false | NO | Naive controls are never promotion eligible. |

## Review Scanner State

Latest development scanner snapshot was produced during the implementation handoff and was not rerun for this diagnosis.

| item | value |
| --- | --- |
| latest scan id | 7394bc30e865a5c419311d51 |
| latest scan as-of date | 2026-06-25 |
| latest scan row count | 50 |
| expected actionable rows from handoff | 0 |

## Immutability Verification

Development SQLite and model artifacts were read with SQLite `mode=ro`; no discovery, scanner, feature build, FMP update, forward-update, daily-cycle, promotion, or final-holdout command was run for this diagnosis.

| item | value |
| --- | --- |
| development Git status before report | ## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1 |
| development SQLite size before | 384835584 |
| development SQLite mtime before UTC | 2026-06-27T15:08:26.849415+00:00 |
| development SQLite size after | 384835584 |
| development SQLite mtime after UTC | 2026-06-27T15:08:26.849415+00:00 |
| representative artifact | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev/artifacts/models/5b3f37a96a7968bca8d2f398.joblib |
| representative artifact size | 30710684 |
| representative artifact mtime UTC | 2026-06-27T14:15:26.030944+00:00 |
| representative artifact size after | 30710684 |
| representative artifact mtime after UTC | 2026-06-27T14:15:26.030944+00:00 |
| development scanner snapshots after | 3 |
| development scanner candidates after | 150 |
| development forward events after | 0 |
| development final-holdout runs after | 0 |
| operational HEAD | 3f3c4f853cc183e6a0a4900dadc428162c400ef7 |
| operational Git status | ## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1 |
| operational scanner snapshots | 17 |
| operational forward events | 285 |
| operational final-holdout runs | 1 |
| operational frozen run | {'run_id': '3493ee8ac37bf96475c362e1', 'status': 'CREATED', 'baseline_market_date': '2026-06-25', 'model_ids_json': '["b93b2258c10aea5cef81d291"]'} |

Confirmed:

- no source files were changed by the diagnosis script;
- no model artifacts were changed by the diagnosis script;
- no SQLite state was changed by the diagnosis script;
- no scanner, forward, or final-holdout state was changed by the diagnosis script;
- no operational state was changed.

## Conclusion

1. Robust MAE Target Transformation V1 fixed the localized POOLED bull HistGradientBoosting MAE OOD warning source.
2. It did not create a promotion-eligible model.
3. It did not change the selected-candidate evidence for the affected model.
4. It should be treated as a scoped estimator-stability correction, not as proof of improved trading performance.

## Exactly One Next Task

Run a read-only challenger prioritization review for generation `2026-06-27T14:05:10.073173+00:00` and decide whether development should continue with the transformed POOLED bull HistGradientBoosting model or remain focused on the stronger ORDINARY bull ExtraTrees challenger.
