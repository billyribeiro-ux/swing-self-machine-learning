# Nonlinear Model Quality Diagnosis

Date: 2026-06-25

## Scope

This is a read-only diagnosis of the nonlinear learned models in the post-retirement generation:

`2026-06-25T13:11:51.610283+00:00`

The immutable comparison baseline remains:

`2026-06-22T18:07:43.648509+00:00`

No discovery, scanner, final-holdout init/update/evaluate, forward-update, daily-cycle, promotion, data update, artifact rewrite, or SQLite write command was run for this diagnosis.

## Summary

ATR-normalized path targets removed the prior nonlinear path-OOD blocker pattern. In this generation, all active ExtraTrees and HistGradientBoosting expected-return, MFE, and MAE predictions are finite, sign-valid, and within current q99 OOD limits.

Remaining blockers are now selected-candidate and validation-state blockers:

- ExtraTrees selected zero development-holdout observations in both directions.
- Bear HistGradientBoosting selected observations but failed temporal stability and exceptional-period concentration.
- Bull HistGradientBoosting has no development-gate blockers from `_development_gate_blockers`, but still cannot be promoted because it is a `DEVELOPMENT_HOLDOUT` candidate and no prospective final-holdout run exists.
- All scanner rows from these models remain non-actionable because no model was promoted.

## Analyzed Models

| Model ID | Direction | Family | State | Selected | Selected Rate | LCB90 | Profit Factor | Portfolio Drawdown | Temporal Positive Fraction | Exceptional Top |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `4d66c49b675803520298a243` | bear | extra_trees | CANDIDATE | 0 | 0.00% | NA | NOT_AVAILABLE | NA | NOT_AVAILABLE | NA |
| `4b25faeeca72518f3f435fa7` | bear | hist_gradient_boosting | CANDIDATE | 54 | 0.32% | 0.0056 | 2.7220 | -0.1907 | 0.3333 | 0.9210 |
| `108bc18cfa5be414666c2512` | bull | extra_trees | CANDIDATE | 0 | 0.00% | NA | NOT_AVAILABLE | NA | NOT_AVAILABLE | NA |
| `b93b2258c10aea5cef81d291` | bull | hist_gradient_boosting | CANDIDATE | 39 | 0.23% | 0.0018 | 2.3796 | -0.0522 | 1.0000 | 0.4514 |

All four models use:

- training window: 2016-06-20 through 2022-04-28
- calibration window: 2022-05-13 through 2024-04-17
- development holdout: 2024-05-02 through 2026-04-22
- holdout status: `DEVELOPMENT_HOLDOUT`

## Failed Mandatory Gates

| Model ID | Direction | Family | Scope | Gate | Actual | Threshold | Reason |
|---|---|---|---|---|---:|---:|---|
| `4d66c49b675803520298a243` | bear | extra_trees | model | `final_holdout_required_for_promotion` | DEVELOPMENT_HOLDOUT | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| `4d66c49b675803520298a243` | bear | extra_trees | selected_candidates | `positive_expected_value_after_costs` | NOT_AVAILABLE | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| `4d66c49b675803520298a243` | bear | extra_trees | selected_candidates | `profit_factor_min_090` | NOT_AVAILABLE | 0.9000 | Profit factor is unavailable because no selected observations exist. |
| `4d66c49b675803520298a243` | bear | extra_trees | portfolio_holdout | `portfolio_drawdown_available` | NOT_AVAILABLE | finite | Portfolio drawdown is missing. |
| `4d66c49b675803520298a243` | bear | extra_trees | portfolio_holdout | `portfolio_drawdown_not_worse_than_50pct` | NOT_AVAILABLE | -0.5000 | Portfolio drawdown is missing or worse than configured limit. |
| `4d66c49b675803520298a243` | bear | extra_trees | selected_candidates | `transaction_cost_sensitivity_not_collapsed` | NOT_AVAILABLE | -0.0010 | Double-cost lower confidence bound fails or is missing. |
| `4d66c49b675803520298a243` | bear | extra_trees | selected_candidates | `temporal_fold_stability_evidence_available` | UNAVAILABLE | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| `4b25faeeca72518f3f435fa7` | bear | hist_gradient_boosting | model | `final_holdout_required_for_promotion` | DEVELOPMENT_HOLDOUT | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| `4b25faeeca72518f3f435fa7` | bear | hist_gradient_boosting | selected_candidates | `temporal_fold_stability_min_050` | 0.3333 | 0.5000 | Temporal-fold positive fraction 33.33% is below the minimum 50.00%. |
| `4b25faeeca72518f3f435fa7` | bear | hist_gradient_boosting | selected_candidates | `exceptional_period_concentration_max_060` | 0.9210 | 0.6000 | Exceptional-period concentration 92.10% exceeds the maximum 60.00%. |
| `108bc18cfa5be414666c2512` | bull | extra_trees | model | `final_holdout_required_for_promotion` | DEVELOPMENT_HOLDOUT | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| `108bc18cfa5be414666c2512` | bull | extra_trees | selected_candidates | `positive_expected_value_after_costs` | NOT_AVAILABLE | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| `108bc18cfa5be414666c2512` | bull | extra_trees | selected_candidates | `profit_factor_min_090` | NOT_AVAILABLE | 0.9000 | Profit factor is unavailable because no selected observations exist. |
| `108bc18cfa5be414666c2512` | bull | extra_trees | portfolio_holdout | `portfolio_drawdown_available` | NOT_AVAILABLE | finite | Portfolio drawdown is missing. |
| `108bc18cfa5be414666c2512` | bull | extra_trees | portfolio_holdout | `portfolio_drawdown_not_worse_than_50pct` | NOT_AVAILABLE | -0.5000 | Portfolio drawdown is missing or worse than configured limit. |
| `108bc18cfa5be414666c2512` | bull | extra_trees | selected_candidates | `transaction_cost_sensitivity_not_collapsed` | NOT_AVAILABLE | -0.0010 | Double-cost lower confidence bound fails or is missing. |
| `108bc18cfa5be414666c2512` | bull | extra_trees | selected_candidates | `temporal_fold_stability_evidence_available` | UNAVAILABLE | AVAILABLE | Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations. |
| `b93b2258c10aea5cef81d291` | bull | hist_gradient_boosting | model | `final_holdout_required_for_promotion` | DEVELOPMENT_HOLDOUT | FINAL_HOLDOUT | Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |

`_development_gate_blockers` returned no blockers for `b93b2258c10aea5cef81d291`. That model is the current nonlinear model closest to prospective final-holdout enrollment, but it still has no final-holdout evidence and remains a non-promoted candidate.

## Path-Head State

| Model ID | Direction | Family | Return OOD q99/max | MFE State / Estimator / Loss / OOD q99/max | MAE State / Estimator / Loss / OOD q99/max | Finite / Sign Valid |
|---|---|---|---|---|---|---|
| `4d66c49b675803520298a243` | bear | extra_trees | 0.0000 / 0.0000 | ACTIVE / ExtraTreesRegressor / squared_error_leaf_average / 0.0000 / 0.0000 | ACTIVE / ExtraTreesRegressor / squared_error_leaf_average / 0.0000 / 0.0000 | return true/true, MFE true/true, MAE true/true |
| `4b25faeeca72518f3f435fa7` | bear | hist_gradient_boosting | 0.0000 / 0.0000 | ACTIVE / HistGradientBoostingRegressor / poisson / 0.0000 / 0.0000 | ACTIVE / HistGradientBoostingRegressor / poisson / 0.0000 / 0.0000 | return true/true, MFE true/true, MAE true/true |
| `108bc18cfa5be414666c2512` | bull | extra_trees | 0.0000 / 0.0000 | ACTIVE / ExtraTreesRegressor / squared_error_leaf_average / 0.0000 / 0.0000 | ACTIVE / ExtraTreesRegressor / squared_error_leaf_average / 0.0000 / 0.0000 | return true/true, MFE true/true, MAE true/true |
| `b93b2258c10aea5cef81d291` | bull | hist_gradient_boosting | 0.0000 / 0.0000 | ACTIVE / HistGradientBoostingRegressor / poisson / 0.0000 / 0.0000 | ACTIVE / HistGradientBoostingRegressor / poisson / 0.0779 / 0.0779 | return true/true, MFE true/true, MAE true/true |

The remaining nonlinear work is no longer a path-head retirement or sign-domain issue. It is a candidate-selection and prospective-validation issue.

## Scanner State

Latest scanner snapshot used for read-only verification:

- scan ID: `9a0c6eb95e2551a716d16e2b`
- as-of date: 2026-06-18
- rows: 50
- actionable rows from these nonlinear models: 0

| Model ID | Scanner Rows | Status / Reason |
|---|---:|---|
| `4d66c49b675803520298a243` | 5 | REJECTED / `model_not_promoted` |
| `4b25faeeca72518f3f435fa7` | 10 | REJECTED / `model_not_promoted` |
| `108bc18cfa5be414666c2512` | 3 | REJECTED / `model_not_promoted` |
| `b93b2258c10aea5cef81d291` | 7 | REJECTED / `model_not_promoted` |

State counts remained:

- final-holdout runs: 0
- forward events: 285

## Data Leakage Review

This diagnosis read only persisted registry rows, model metrics JSON, gate results JSON, scanner snapshots, scanner candidates, and final-holdout blocker results derived from those persisted artifacts.

No label definitions, features, training windows, calibration windows, holdout windows, signal timestamps, entries, exits, costs, failed trades, model artifacts, or scanner artifacts were changed.

No final-holdout outcomes or forward-test outcomes were used.

## Next Smallest Milestone

Prepare prospective final-holdout enrollment for `b93b2258c10aea5cef81d291` only after explicitly deciding that its development-holdout evidence is sufficient for a prospective shadow validation run. Keep ExtraTrees and bear HistGradientBoosting in diagnosis until they clear selected-candidate gates.
