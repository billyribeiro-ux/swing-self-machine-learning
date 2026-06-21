# Gate Evidence Retrain Handoff

## Acceptance Status

FAILED. One fresh immutable generation was created, but the fresh generation did not satisfy the gate-integrity acceptance condition because six canonical `temporal_fold_stability_min_050` rows persist unavailable evidence as `NOT_AVAILABLE` while status is `PASS`. I stopped before running the review-only scanner because that would create another scanner snapshot against a generation that already failed acceptance.

## Precondition Review

- Gate-fix commit: `fc7afd04c5c8e7228a0321d9d510ad6bb7570048`
- Parent reviewed: `7f9747c0143b0ef16455a970e4bb814843c57576`
- Branch: `feat/autonomous-swing-scanner-v1`
- Review result: no P1/P2 finding in the requested profit-factor, zero-selection, comparator, reason-text, dashboard/export, promotion, or legacy-artifact focus areas before retraining.
- Semantic probe result before retraining: PASS.

## Profit-Factor Truth Table Verification

| Case | Observed behavior |
| --- | --- |
| Learned selected gains and no losses | `actual = ∞`, evidence `AVAILABLE`, `profit_factor_min_090 = PASS`, reason: `Selected returns contain gains and no losses, so profit factor is positive infinity and satisfies the minimum 0.90.` |
| Learned zero selected rows | `actual = NOT_AVAILABLE`, `profit_factor_min_090 = FAIL`, reason: `Profit factor is unavailable because no selected observations exist.` |
| Naive zero selected rows | `actual = NOT_AVAILABLE`, `profit_factor_min_090 = NOT_APPLICABLE`, mandatory `False`; `not_naive_control = FAIL`, so promotion remains blocked. |
| All-zero selected returns | `actual = NOT_AVAILABLE`, `profit_factor_min_090 = FAIL`, reason: `Profit factor is undefined because all selected returns were zero.` |
| Concentration reasons | PASS uses `is within the maximum`; FAIL uses `exceeds the maximum`; NOT_APPLICABLE uses `is unavailable because no rows were selected.` |

## Verification Before Retraining

| Command | Result |
| --- | --- |
| `.venv/bin/pytest` | 138 collected, 138 passed, 0 failed, 0 skipped, 161 warnings |
| `.venv/bin/ruff check .` | PASS, `All checks passed!` |
| `.venv/bin/ruff format --check .` | PASS, `92 files already formatted` |
| `.venv/bin/mypy src` | PASS, `Success: no issues found in 54 source files` |

## Fresh Generation

- Discovery command executed exactly once: `.venv/bin/python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80`.
- Discovery CLI result: 8 models registered, 0 challengers, 8 candidates needing review, 0 rejected/experimental, no candidate promoted or silently deployed.
- Previous generation: `2026-06-21T04:34:49.525939+00:00`
- New generation: `2026-06-21T17:09:51.735316+00:00`
- Research dates: 2016-06-20 to 2026-06-18.
- New model IDs: `12e2e80f8f1179e4b994d95e`, `86a46589667781e683312acc`, `a558e32e410fa7f64e4eb045`, `9c821cc4e2808288924d266d`, `2f9313619ef9b897f07af9b9`, `5b1a73aede4f36ee4d06ae53`, `475c172d88103ebad9912d97`, `9eb5844427a07f6dc9a51c9e`
- Registry states: {'CANDIDATE': 8}
- OOD Governance V2 on all new models: True.
- Persisted selection policy on all new models: True.
- Canonical gate rows on all new models: True.
- No model promoted: True.
- Prior model count/generation count: 74 models across 10 generations.
- After discovery: 82 models across 11 generations.
- Prior generation counts unchanged: True.
- Prior artifact hash mismatches: 0.

## Complete Model Table

| model ID | direction | family | state | train | calibration | holdout | selected | selected rate | pos returns | neg returns | zero returns | gross profit | gross loss | PF evidence | PF | PF gate | PF reason | mean net | median net | LCB | win rate | portfolio return | portfolio max DD | model Brier | naive Brier | BSS | OOD warnings | OOD failed gates | symbol conc | sector conc | exceptional conc | failed mandatory gates | not-applicable gates | promotion eligible | promotion blocking reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12e2e80f8f1179e4b994d95e | bear | extra_trees | CANDIDATE | 41884 | 16800 | 17069 | 6 | 0.0352% | 6 | 0 | 0 | 0.266883 | 0.000000 | AVAILABLE | ∞ | PASS | Selected returns contain gains and no losses, so profit factor is positive infinity and satisfies the minimum 0.90. | 0.044481 | 0.050313 | 0.030830 | 100.0000% | 0.023055 | -0.010237 | 0.244796 | 0.249630 | 0.019366 | 39 | return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable | 83.3333% | 83.3333% | 100.0000% | symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable | legacy_prediction_out_of_distribution_absent_deprecated | False | symbol_concentration_max_050: Symbol concentration 83.33% exceeds the maximum 50.00%.<br>sector_concentration_max_080: Sector concentration 83.33% exceeds the maximum 80.00%.<br>exceptional_period_concentration_max_060: Exceptional-period concentration 100.00% exceeds the maximum 60.00%.<br>return_holdout_ood_q99_severity_acceptable: Expected Return holdout OOD q99 severity exceeds the frozen limit.<br>mfe_holdout_ood_q99_severity_acceptable: MFE holdout OOD q99 severity exceeds the frozen limit. |
| 86a46589667781e683312acc | bear | hist_gradient_boosting | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.0000% | 0 | 0 | 0 | 0.000000 | 0.000000 | UNAVAILABLE | NOT AVAILABLE | FAIL | Profit factor is unavailable because no selected observations exist. | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0.248393 | 0.249630 | 0.004954 | 55 | return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable | symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>legacy_prediction_out_of_distribution_absent_deprecated | False | positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.<br>profit_factor_min_090: Profit factor is unavailable because no selected observations exist.<br>portfolio_drawdown_available: Portfolio drawdown is missing.<br>portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.<br>transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.<br>return_holdout_ood_q99_severity_acceptable: Expected Return holdout OOD q99 severity exceeds the frozen limit.<br>mfe_holdout_ood_q99_severity_acceptable: MFE holdout OOD q99 severity exceeds the frozen limit.<br>mfe_catastrophic_prediction_extrapolation_absent: MFE maximum holdout OOD severity exceeds 1.00.<br>mae_holdout_ood_q99_severity_acceptable: MAE holdout OOD q99 severity exceeds the frozen limit.<br>symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.<br>sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.<br>exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |
| a558e32e410fa7f64e4eb045 | bear | logistic_regression | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.0000% | 0 | 0 | 0 | 0.000000 | 0.000000 | UNAVAILABLE | NOT AVAILABLE | FAIL | Profit factor is unavailable because no selected observations exist. | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0.243674 | 0.249630 | 0.023860 | 120 | return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>legacy_prediction_out_of_distribution_absent_deprecated | False | positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.<br>profit_factor_min_090: Profit factor is unavailable because no selected observations exist.<br>portfolio_drawdown_available: Portfolio drawdown is missing.<br>portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.<br>transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.<br>return_holdout_ood_q99_severity_acceptable: Expected Return holdout OOD q99 severity exceeds the frozen limit.<br>mfe_prediction_path_metric_sign_valid: MFE path-metric sign contract failed.<br>mfe_holdout_ood_q99_severity_acceptable: MFE holdout OOD q99 severity exceeds the frozen limit.<br>mfe_catastrophic_prediction_extrapolation_absent: MFE maximum holdout OOD severity exceeds 1.00.<br>mae_holdout_ood_q99_severity_acceptable: MAE holdout OOD q99 severity exceeds the frozen limit.<br>mae_catastrophic_prediction_extrapolation_absent: MAE maximum holdout OOD severity exceeds 1.00.<br>symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.<br>sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.<br>exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |
| 9c821cc4e2808288924d266d | bear | naive_base_rate | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.0000% | 0 | 0 | 0 | 0.000000 | 0.000000 | NOT_APPLICABLE | NOT APPLICABLE | NOT_APPLICABLE | Profit factor is not applicable because this naive control selected no rows; trading-performance evidence is not comparable for the zero-selection control. | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0.249440 | 0.249440 | 0.000000 | 120 | return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | not_naive_control<br>return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | selected_candidate_quality_available<br>profit_factor_min_090<br>symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>legacy_prediction_out_of_distribution_absent_deprecated | False | not_naive_control: Naive controls are never promotion eligible.<br>return_holdout_ood_q99_severity_acceptable: Expected Return holdout OOD q99 severity exceeds the frozen limit.<br>mfe_prediction_path_metric_sign_valid: MFE path-metric sign contract failed.<br>mfe_holdout_ood_q99_severity_acceptable: MFE holdout OOD q99 severity exceeds the frozen limit.<br>mfe_catastrophic_prediction_extrapolation_absent: MFE maximum holdout OOD severity exceeds 1.00.<br>mae_holdout_ood_q99_severity_acceptable: MAE holdout OOD q99 severity exceeds the frozen limit.<br>mae_catastrophic_prediction_extrapolation_absent: MAE maximum holdout OOD severity exceeds 1.00.<br>symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.<br>sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.<br>exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |
| 2f9313619ef9b897f07af9b9 | bull | extra_trees | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.0000% | 0 | 0 | 0 | 0.000000 | 0.000000 | UNAVAILABLE | NOT AVAILABLE | FAIL | Profit factor is unavailable because no selected observations exist. | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0.244704 | 0.249697 | 0.019994 | 3 | mae_holdout_ood_q99_severity_acceptable | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>mae_holdout_ood_q99_severity_acceptable | symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>legacy_prediction_out_of_distribution_absent_deprecated | False | positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.<br>profit_factor_min_090: Profit factor is unavailable because no selected observations exist.<br>portfolio_drawdown_available: Portfolio drawdown is missing.<br>portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.<br>transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.<br>mae_holdout_ood_q99_severity_acceptable: MAE holdout OOD q99 severity exceeds the frozen limit.<br>symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.<br>sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.<br>exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |
| 5b1a73aede4f36ee4d06ae53 | bull | hist_gradient_boosting | CANDIDATE | 41884 | 16800 | 17069 | 5 | 0.0293% | 3 | 2 | 0 | 0.253197 | 0.035921 | AVAILABLE | 7.048784 | PASS | Profit factor 7.05 meets the minimum 0.90. | 0.043455 | 0.020952 | -0.011979 | 60.0000% | -0.004189 | -0.015685 | 0.247874 | 0.249697 | 0.007300 | 13 | mfe_holdout_ood_q99_severity_acceptable<br>mae_holdout_ood_q99_severity_acceptable | 100.0000% | 100.0000% | 100.0000% | positive_expected_value_after_costs<br>symbol_concentration_max_050<br>sector_concentration_max_080<br>transaction_cost_sensitivity_not_collapsed<br>exceptional_period_concentration_max_060<br>mfe_holdout_ood_q99_severity_acceptable<br>mae_holdout_ood_q99_severity_acceptable | legacy_prediction_out_of_distribution_absent_deprecated | False | positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.<br>symbol_concentration_max_050: Symbol concentration 100.00% exceeds the maximum 50.00%.<br>sector_concentration_max_080: Sector concentration 100.00% exceeds the maximum 80.00%.<br>transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.<br>exceptional_period_concentration_max_060: Exceptional-period concentration 100.00% exceeds the maximum 60.00%.<br>mfe_holdout_ood_q99_severity_acceptable: MFE holdout OOD q99 severity exceeds the frozen limit.<br>mae_holdout_ood_q99_severity_acceptable: MAE holdout OOD q99 severity exceeds the frozen limit. |
| 475c172d88103ebad9912d97 | bull | logistic_regression | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.0000% | 0 | 0 | 0 | 0.000000 | 0.000000 | UNAVAILABLE | NOT AVAILABLE | FAIL | Profit factor is unavailable because no selected observations exist. | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0.243684 | 0.249697 | 0.024079 | 26 | mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>legacy_prediction_out_of_distribution_absent_deprecated | False | positive_expected_value_after_costs: Lower confidence bound is missing or below cost threshold.<br>profit_factor_min_090: Profit factor is unavailable because no selected observations exist.<br>portfolio_drawdown_available: Portfolio drawdown is missing.<br>portfolio_drawdown_not_worse_than_50pct: Portfolio drawdown is missing or worse than configured limit.<br>transaction_cost_sensitivity_not_collapsed: Double-cost lower confidence bound fails or is missing.<br>mfe_holdout_ood_q99_severity_acceptable: MFE holdout OOD q99 severity exceeds the frozen limit.<br>mfe_catastrophic_prediction_extrapolation_absent: MFE maximum holdout OOD severity exceeds 1.00.<br>mae_holdout_ood_q99_severity_acceptable: MAE holdout OOD q99 severity exceeds the frozen limit.<br>mae_catastrophic_prediction_extrapolation_absent: MAE maximum holdout OOD severity exceeds 1.00.<br>symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.<br>sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.<br>exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |
| 9eb5844427a07f6dc9a51c9e | bull | naive_base_rate | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.0000% | 0 | 0 | 0 | 0.000000 | 0.000000 | NOT_APPLICABLE | NOT APPLICABLE | NOT_APPLICABLE | Profit factor is not applicable because this naive control selected no rows; trading-performance evidence is not comparable for the zero-selection control. | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0.249534 | 0.249534 | 0.000000 | 26 | mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | not_naive_control<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | selected_candidate_quality_available<br>profit_factor_min_090<br>symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>legacy_prediction_out_of_distribution_absent_deprecated | False | not_naive_control: Naive controls are never promotion eligible.<br>mfe_holdout_ood_q99_severity_acceptable: MFE holdout OOD q99 severity exceeds the frozen limit.<br>mfe_catastrophic_prediction_extrapolation_absent: MFE maximum holdout OOD severity exceeds 1.00.<br>mae_holdout_ood_q99_severity_acceptable: MAE holdout OOD q99 severity exceeds the frozen limit.<br>mae_catastrophic_prediction_extrapolation_absent: MAE maximum holdout OOD severity exceeds 1.00.<br>symbol_concentration_max_050: Symbol concentration is unavailable because no rows were selected.<br>sector_concentration_max_080: Sector concentration is unavailable because no rows were selected.<br>exceptional_period_concentration_max_060: Exceptional-period concentration is unavailable because no rows were selected. |

## Old Versus New Comparison

| direction | family | horizon | old model ID | new model ID | old selected | new selected | old PF | new PF | old PF status | new PF status | old PF reason | new PF reason | old symbol concentration | new symbol concentration | old sector concentration | new sector concentration | old exceptional period | new exceptional period | old mandatory failures | new mandatory failures | old promotion eligible | new promotion eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bear | extra_trees | 10 | 5160add45d1b068f7f161aa7 | 12e2e80f8f1179e4b994d95e | 6 | 6 | ∞ | ∞ | FAIL | PASS | Selected-row profit factor fails configured minimum. | Selected returns contain gains and no losses, so profit factor is positive infinity and satisfies the minimum 0.90. | FAIL: Symbol concentration is within cap or not applicable due no selected rows. | FAIL: Symbol concentration 83.33% exceeds the maximum 50.00%. | FAIL: Sector concentration is within cap or not applicable due no selected rows. | FAIL: Sector concentration 83.33% exceeds the maximum 80.00%. | FAIL: No single year dominates selected absolute return contribution. | FAIL: Exceptional-period concentration 100.00% exceeds the maximum 60.00%. | 6 | 5 | False | False |
| bear | hist_gradient_boosting | 10 | 8fc3f715fad2d7abff9a8e32 | 86a46589667781e683312acc | 0 | 0 | ∞ | NOT AVAILABLE | FAIL | FAIL | Selected-row profit factor fails configured minimum. | Profit factor is unavailable because no selected observations exist. | PASS: Symbol concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Symbol concentration is unavailable because no rows were selected. | PASS: Sector concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Sector concentration is unavailable because no rows were selected. | PASS: No single year dominates selected absolute return contribution. | NOT_APPLICABLE: Exceptional-period concentration is unavailable because no rows were selected. | 9 | 9 | False | False |
| bear | logistic_regression | 10 | 970e03fddb196603a22d4a24 | a558e32e410fa7f64e4eb045 | 0 | 0 | ∞ | NOT AVAILABLE | FAIL | FAIL | Selected-row profit factor fails configured minimum. | Profit factor is unavailable because no selected observations exist. | PASS: Symbol concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Symbol concentration is unavailable because no rows were selected. | PASS: Sector concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Sector concentration is unavailable because no rows were selected. | PASS: No single year dominates selected absolute return contribution. | NOT_APPLICABLE: Exceptional-period concentration is unavailable because no rows were selected. | 11 | 11 | False | False |
| bear | naive_base_rate | 10 | 3d0b95ffea9724494114e6c4 | 9c821cc4e2808288924d266d | 0 | 0 | ∞ | NOT APPLICABLE | MISSING | NOT_APPLICABLE | MISSING | Profit factor is not applicable because this naive control selected no rows; trading-performance evidence is not comparable for the zero-selection control. | PASS: Symbol concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Symbol concentration is unavailable because no rows were selected. | PASS: Sector concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Sector concentration is unavailable because no rows were selected. | PASS: No single year dominates selected absolute return contribution. | NOT_APPLICABLE: Exceptional-period concentration is unavailable because no rows were selected. | 7 | 7 | False | False |
| bull | extra_trees | 10 | eec38153992ba94ed6aa6308 | 2f9313619ef9b897f07af9b9 | 0 | 0 | ∞ | NOT AVAILABLE | FAIL | FAIL | Selected-row profit factor fails configured minimum. | Profit factor is unavailable because no selected observations exist. | PASS: Symbol concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Symbol concentration is unavailable because no rows were selected. | PASS: Sector concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Sector concentration is unavailable because no rows were selected. | PASS: No single year dominates selected absolute return contribution. | NOT_APPLICABLE: Exceptional-period concentration is unavailable because no rows were selected. | 6 | 6 | False | False |
| bull | hist_gradient_boosting | 10 | 01a260bc4a63c41eada979ae | 5b1a73aede4f36ee4d06ae53 | 5 | 5 | 7.048784 | 7.048784 | PASS | PASS | Selected-row profit factor meets configured minimum. | Profit factor 7.05 meets the minimum 0.90. | FAIL: Symbol concentration is within cap or not applicable due no selected rows. | FAIL: Symbol concentration 100.00% exceeds the maximum 50.00%. | FAIL: Sector concentration is within cap or not applicable due no selected rows. | FAIL: Sector concentration 100.00% exceeds the maximum 80.00%. | FAIL: No single year dominates selected absolute return contribution. | FAIL: Exceptional-period concentration 100.00% exceeds the maximum 60.00%. | 7 | 7 | False | False |
| bull | logistic_regression | 10 | cc3b395baf3f6e06451ccdee | 475c172d88103ebad9912d97 | 0 | 0 | ∞ | NOT AVAILABLE | FAIL | FAIL | Selected-row profit factor fails configured minimum. | Profit factor is unavailable because no selected observations exist. | PASS: Symbol concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Symbol concentration is unavailable because no rows were selected. | PASS: Sector concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Sector concentration is unavailable because no rows were selected. | PASS: No single year dominates selected absolute return contribution. | NOT_APPLICABLE: Exceptional-period concentration is unavailable because no rows were selected. | 9 | 9 | False | False |
| bull | naive_base_rate | 10 | 8cafce9ea237b314c665ab7d | 9eb5844427a07f6dc9a51c9e | 0 | 0 | ∞ | NOT APPLICABLE | MISSING | NOT_APPLICABLE | MISSING | Profit factor is not applicable because this naive control selected no rows; trading-performance evidence is not comparable for the zero-selection control. | PASS: Symbol concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Symbol concentration is unavailable because no rows were selected. | PASS: Sector concentration is within cap or not applicable due no selected rows. | NOT_APPLICABLE: Sector concentration is unavailable because no rows were selected. | PASS: No single year dominates selected absolute return contribution. | NOT_APPLICABLE: Exceptional-period concentration is unavailable because no rows were selected. | 5 | 5 | False | False |

## Bearish ExtraTrees Confirmation

- New bearish ExtraTrees model: `12e2e80f8f1179e4b994d95e`.
- Reproduces prior condition: True.
- Selected gains: 6; selected losses: 0; profit factor: ∞; profit-factor gate status: PASS.

## Gate-Contradiction Validation

| Metric | Count |
| --- | ---: |
| Total gate rows | 400 |
| Contradictory gate rows from `gate_result_integrity_warning` | 0 |
| Status/reason mismatches for profit-factor/concentration gates | 0 |
| Unavailable/infinity mismatches | 6 |
| Comparator/status mismatches | 0 |

Expected contradictory rows: 0. Observed acceptance-blocking rows: 6 unavailable-evidence PASS rows.

| model ID | gate | actual | comparator | threshold | status | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 86a46589667781e683312acc | temporal_fold_stability_min_050 | NOT_AVAILABLE | >= | 0.500000 | PASS | Temporal fold stability passes or is not applicable due insufficient selected rows. |
| a558e32e410fa7f64e4eb045 | temporal_fold_stability_min_050 | NOT_AVAILABLE | >= | 0.500000 | PASS | Temporal fold stability passes or is not applicable due insufficient selected rows. |
| 9c821cc4e2808288924d266d | temporal_fold_stability_min_050 | NOT_AVAILABLE | >= | 0.500000 | PASS | Temporal fold stability passes or is not applicable due insufficient selected rows. |
| 2f9313619ef9b897f07af9b9 | temporal_fold_stability_min_050 | NOT_AVAILABLE | >= | 0.500000 | PASS | Temporal fold stability passes or is not applicable due insufficient selected rows. |
| 475c172d88103ebad9912d97 | temporal_fold_stability_min_050 | NOT_AVAILABLE | >= | 0.500000 | PASS | Temporal fold stability passes or is not applicable due insufficient selected rows. |
| 9eb5844427a07f6dc9a51c9e | temporal_fold_stability_min_050 | NOT_AVAILABLE | >= | 0.500000 | PASS | Temporal fold stability passes or is not applicable due insufficient selected rows. |

## Dashboard And Export Representation

- Dashboard valid positive infinity display: `∞`.
- Dashboard unavailable display: `Not available`.
- `display_frame` profit-factor values: `['∞', 'Not available']`.
- JSON profit-factor actual values in export: `['7.048783787503008', 'Infinity', 'NOT_AVAILABLE']`.
- CSV contains explicit `Infinity`: True.
- CSV contains explicit `NOT_AVAILABLE`: True.

## Failed Mandatory Gates And Promotion Eligibility

- Every new model remains promotion-ineligible from canonical persisted gates.
- No model state is `CHALLENGER` or `CHAMPION`; all 8 new models are `CANDIDATE`.
- The corrected profit-factor gate reduces the bearish ExtraTrees mandatory failure count from 6 to 5, but concentration and OOD gates still block promotion.
- The six `temporal_fold_stability_min_050` PASS rows with unavailable evidence are not counted as blockers because their persisted status is PASS; this is the remaining confirmed evidence defect.

## Review-Only Scanner Results

| Field | Result |
| --- | --- |
| Command | NOT RUN |
| Reason | Gate-integrity validation failed before scanner execution; running `scan --include-challengers` would create a scanner snapshot for a generation that already failed acceptance. |
| Scan ID | NOT RUN |
| Generation ID | NOT RUN |
| As-of date | NOT RUN |
| Total rows / bullish / bearish / actionable / rejected | NOT RUN |
| Rejection reasons / model states / model IDs / OOD rows | NOT RUN |

## Final Verification

| Command | Result |
| --- | --- |
| `.venv/bin/pytest` | 138 collected, 138 passed, 0 failed, 0 skipped, 161 warnings |
| `.venv/bin/ruff check .` | PASS, `All checks passed!` |
| `.venv/bin/ruff format --check .` | PASS, `92 files already formatted` |
| `.venv/bin/mypy src` | PASS, `Success: no issues found in 54 source files` |
| Focused tests: `tests/test_model_evaluation_integrity.py tests/test_dashboard_model_registry.py tests/test_dashboard_interactions.py tests/test_autonomous_engine.py` | 80 collected, 80 passed, 0 failed, 0 skipped, 161 warnings |

## Acceptance Conditions

| Condition | Result |
| --- | --- |
| One fresh immutable generation exists | PASS |
| Previous generations remain unchanged | PASS |
| Valid positive infinity passes minimum profit-factor gate | PASS |
| Learned zero-selection evidence unavailable and fails | PASS |
| Naive zero-selection evidence not applicable | PASS |
| Concentration-gate reasons agree with status | PASS |
| No contradictory canonical gate rows exist | FAIL: six `temporal_fold_stability_min_050` unavailable-evidence PASS rows |
| Dashboard and exports represent infinity/unavailable correctly | PASS for profit-factor evidence |
| Promotion eligibility uses corrected canonical gates | PASS, but temporal-fold PASS rows remain a confirmed evidence defect |
| No model automatically promoted | PASS |
| No paper-forward event created | PASS: `forward-update` was not run |
| All tests/static checks pass | PASS |

## Remaining Confirmed Blockers

- `temporal_fold_stability_min_050` currently allows missing/nonfinite temporal-fold evidence to pass as a mandatory gate. In the fresh generation, six rows have `actual = NOT_AVAILABLE`, comparator `>=`, threshold `0.5`, status `PASS`, and reason `Temporal fold stability passes or is not applicable due insufficient selected rows.` This violates the acceptance rule that missing/NaN evidence must not pass a mandatory gate and creates status/evidence ambiguity.

## Exactly One Smallest Next Engineering Task

Fix `temporal_fold_stability_min_050` evidence semantics so insufficient or nonfinite temporal-fold evidence persists as `NOT_APPLICABLE` with status-aware reason text instead of `PASS`, and add focused tests for zero/insufficient selected-row temporal-fold evidence.
