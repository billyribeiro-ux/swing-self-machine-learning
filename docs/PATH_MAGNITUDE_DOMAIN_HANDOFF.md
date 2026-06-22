# Path Magnitude Domain Modeling Handoff

Date: 2026-06-22

## Confirmed Defect

The previous path-metric MFE and MAE regressors modeled signed path labels directly with unconstrained regressors. MFE has a physical domain of `>= 0`, while MAE has a physical domain of `<= 0`. The baseline generation `2026-06-22T16:01:49.047908+00:00` violated that contract:

- Bear logistic-family MFE produced 8,714 negative development-holdout MFE predictions.
- Bear naive-control MFE produced 8,714 negative development-holdout MFE predictions.
- Bull logistic-family MAE produced 1,501 positive development-holdout MAE predictions.
- Bull naive-control MAE produced 1,501 positive development-holdout MAE predictions.

This was a modeling-domain defect, not a label defect.

## Unchanged Label Contract

Historical labels remain unchanged:

- Expected return: signed decimal directional return.
- MFE: favorable decimal return, `>= 0`.
- MAE: adverse decimal return, `<= 0`.
- Signal known after daily close.
- Entry at next completed session open.
- Horizon is ten completed sessions for this generation.

Internal training targets are derived only inside the MFE and MAE training heads:

- `mfe_magnitude_target = existing MFE label`
- `mae_magnitude_target = -1 * existing MAE label`

Canonical predictions are mapped back as:

- `mfe_prediction = predicted_mfe_magnitude`
- `mae_prediction = -1 * predicted_mae_magnitude`

## Architecture

Schema: `path_metric_magnitude_domain_v1`

The implementation adds typed domain-preserving path magnitude estimators:

- `PathMagnitudeEstimatorSpec`
- `PathMagnitudeModel` behavior through frozen estimators/pipelines
- `build_path_magnitude_estimator(...)`
- `PathMagnitudePrediction`

Family policy:

| Family | MFE / MAE magnitude estimator | Loss / behavior |
| --- | --- | --- |
| logistic_regression top-level family | `TweedieRegressor` | `power=1.5`, `link="log"` |
| hist_gradient_boosting | `HistGradientBoostingRegressor` | `loss="poisson"` |
| extra_trees | `ExtraTreesRegressor` | nonnegative leaf averages |
| naive_base_rate | `MeanMagnitudeRegressor` | training mean magnitude |

Expected-return modeling remains signed and unchanged.

## No-Clipping Proof

The prediction path validates domain integrity and rejects invalid outputs. It does not repair them with post-hoc clipping. Focused review found no `max(0, ...)`, `min(0, ...)`, `np.clip`, `pandas.clip`, or equivalent correction in the MFE/MAE magnitude mapping path. Existing `np.clip` references remain limited to older probability/classifier support paths, not path-magnitude prediction mapping.

OOD Governance V2 remains in canonical external units:

- MFE OOD checks compare nonnegative canonical MFE predictions to signed MFE training bounds.
- MAE OOD checks compare negative canonical MAE predictions to signed MAE training bounds.

## Implementation Review

Review checks completed:

- No hidden clipping in the MFE/MAE mapping path.
- No double sign conversion found.
- MFE and MAE use separate fitted estimators.
- Bull and bear use separate fitted estimators.
- Model families use separate fitted estimators.
- MFE and MAE target-specific screens use magnitude targets.
- MAE OOD receives canonical negative predictions.
- Scanner identity includes path-domain metadata, estimator hashes, schema, and mapping version.
- Legacy artifacts remain readable but lack `path_metric_magnitude_domain_v1` metadata and are promotion-ineligible under the new schema.

No P1/P2 implementation defect was found after review.

## Commits

- `55112b3` `feat: add domain-preserving path magnitude models`
- `ccdf335` `test: validate MFE and MAE domain preservation`
- `8c3f223` `docs: document path magnitude modeling`

The fresh generation records code commit `8c3f22334742c3eb149d3ab522c35e574243d6f7`.

## Fresh Generation

Generation ID: `2026-06-22T18:07:43.648509+00:00`

Research period: `2016-06-20` through `2026-06-18`

Development holdout: `2024-05-02` through `2026-04-22`

Models registered: 8

No model was promoted.

| Model ID | Direction | Family | State | Selected rows | Mandatory failures |
| --- | --- | --- | --- | ---: | ---: |
| `47652793a6fe81d03febd902` | bull | naive_base_rate | CANDIDATE | 0 | 3 |
| `940ba78f13e1901d5dbed857` | bull | logistic_regression | CANDIDATE | 0 | 12 |
| `4fa02a7da4b56369c8239395` | bull | hist_gradient_boosting | CANDIDATE | 190 | 6 |
| `ec18c13e9609dc83dc86f71f` | bull | extra_trees | CANDIDATE | 0 | 8 |
| `64dba41ff80db83a36cc5db3` | bear | naive_base_rate | CANDIDATE | 0 | 3 |
| `1b6b015139ad84f11ce087f6` | bear | logistic_regression | CANDIDATE | 0 | 12 |
| `6882025340645e11212ec56d` | bear | hist_gradient_boosting | CANDIDATE | 42 | 5 |
| `cda4b498175ea6d2d7f6400b` | bear | extra_trees | CANDIDATE | 0 | 9 |

## Feature Families

Path feature screening remains target-specific and train-only. MFE screens against favorable magnitude targets. MAE screens against adverse magnitude targets.

| Direction | Head | Selected feature families |
| --- | --- | --- |
| bear | expected_return | inverse_leveraged:1; market_relative:9; regime:1; relationship_graph:1; returns_momentum:18; sector_relative:1; technical_primitives:5; trend_structure:14; volatility_range:9; volume_participation:1 |
| bear | mfe | inverse_leveraged:2; market_relative:4; regime:2; relationship_graph:13; returns_momentum:7; technical_primitives:9; trend_structure:14; volatility_range:9 |
| bear | mae | market_relative:6; regime:1; relationship_graph:1; returns_momentum:17; sector_relative:1; technical_primitives:8; trend_structure:17; volatility_range:9 |
| bull | expected_return | inverse_leveraged:1; market_relative:8; regime:1; relationship_graph:1; returns_momentum:18; sector_relative:1; technical_primitives:5; trend_structure:15; volatility_range:9; volume_participation:1 |
| bull | mfe | market_relative:6; regime:2; relationship_graph:2; returns_momentum:17; sector_relative:1; technical_primitives:6; trend_structure:17; volatility_range:9 |
| bull | mae | inverse_leveraged:3; market_relative:6; regime:2; relationship_graph:6; returns_momentum:15; technical_primitives:5; trend_structure:14; volatility_range:9 |

## Estimator And Domain Results

| Direction | Family | Head | Estimator | Loss | Prediction min | Prediction max | Sign violations |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| bull | logistic_regression | MFE | TweedieRegressor | tweedie_power_1.5_link_log | 0.030650 | 6.724878 | 0 |
| bull | logistic_regression | MAE | TweedieRegressor | tweedie_power_1.5_link_log | -8.117339 | -0.029948 | 0 |
| bull | hist_gradient_boosting | MFE | HistGradientBoostingRegressor | poisson | 0.015042 | 0.457544 | 0 |
| bull | hist_gradient_boosting | MAE | HistGradientBoostingRegressor | poisson | -0.316877 | -0.014020 | 0 |
| bull | extra_trees | MFE | ExtraTreesRegressor | squared_error_leaf_average | 0.011948 | 0.330464 | 0 |
| bull | extra_trees | MAE | ExtraTreesRegressor | squared_error_leaf_average | -0.359505 | -0.011424 | 0 |
| bull | naive_base_rate | MFE | MeanMagnitudeRegressor | training_mean_magnitude | 0.050767 | 0.050767 | 0 |
| bull | naive_base_rate | MAE | MeanMagnitudeRegressor | training_mean_magnitude | -0.046877 | -0.046877 | 0 |
| bear | logistic_regression | MFE | TweedieRegressor | tweedie_power_1.5_link_log | 0.029515 | 16.355476 | 0 |
| bear | logistic_regression | MAE | TweedieRegressor | tweedie_power_1.5_link_log | -3.576365 | -0.029506 | 0 |
| bear | hist_gradient_boosting | MFE | HistGradientBoostingRegressor | poisson | 0.015160 | 0.639525 | 0 |
| bear | hist_gradient_boosting | MAE | HistGradientBoostingRegressor | poisson | -0.248290 | -0.014534 | 0 |
| bear | extra_trees | MFE | ExtraTreesRegressor | squared_error_leaf_average | 0.011097 | 0.696223 | 0 |
| bear | extra_trees | MAE | ExtraTreesRegressor | squared_error_leaf_average | -0.243371 | -0.011313 | 0 |
| bear | naive_base_rate | MFE | MeanMagnitudeRegressor | training_mean_magnitude | 0.054398 | 0.054398 | 0 |
| bear | naive_base_rate | MAE | MeanMagnitudeRegressor | training_mean_magnitude | -0.045123 | -0.045123 | 0 |

Required implementation result:

- MFE sign-contract violations: 0
- MAE sign-contract violations: 0

This does not prove a trading edge.

## OOD Results

Domain correctness eliminated sign-contract failures, but OOD failures remain.

| Model ID | Direction | Family | MFE OOD rate | MFE q99 severity | MFE max severity | MAE OOD rate | MAE q99 severity | MAE max severity |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `940ba78f13e1901d5dbed857` | bull | logistic_regression | 0.002109 | 12.8301 | 18.7973 | 0.002343 | 17.5067 | 27.1694 |
| `4fa02a7da4b56369c8239395` | bull | hist_gradient_boosting | 0.000234 | 0.3384 | 0.3461 | 0.000117 | 0.0984 | 0.0989 |
| `ec18c13e9609dc83dc86f71f` | bull | extra_trees | 0.000000 | 0.0000 | 0.0000 | 0.000586 | 0.2447 | 0.2469 |
| `1b6b015139ad84f11ce087f6` | bear | logistic_regression | 0.002226 | 25.8431 | 39.3829 | 0.002109 | 9.0791 | 13.1119 |
| `6882025340645e11212ec56d` | bear | hist_gradient_boosting | 0.000879 | 0.5737 | 0.5785 | 0.000000 | 0.0000 | 0.0000 |
| `cda4b498175ea6d2d7f6400b` | bear | extra_trees | 0.001582 | 0.7140 | 0.7185 | 0.000000 | 0.0000 | 0.0000 |

Naive controls had zero path OOD severity after magnitude-domain modeling, but remain non-promotable controls.

## Baseline Comparison

Matched by direction, family, horizon, and head.

| Direction | Family | Head | Old estimator | New estimator | Old sign violations | New sign violations | Old prediction range | New prediction range | Old MAE | New MAE | Old RMSE | New RMSE |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| bear | logistic_regression | MFE | legacy unconstrained | TweedieRegressor | 8714 | 0 | -0.222649 to 1.29623 | 0.029515 to 16.3555 | 0.066887 | 0.042733 | 0.103642 | 0.147477 |
| bear | logistic_regression | MAE | legacy unconstrained | TweedieRegressor | 0 | 0 | -0.556500 to -0.009830 | -3.57636 to -0.029506 | 0.029371 | 0.030938 | 0.045584 | 0.054451 |
| bull | logistic_regression | MFE | legacy unconstrained | TweedieRegressor | 0 | 0 | 0.007164 to 0.752003 | 0.030650 to 6.72488 | 0.037459 | 0.037322 | 0.063937 | 0.083006 |
| bull | logistic_regression | MAE | legacy unconstrained | TweedieRegressor | 1501 | 0 | -0.822391 to 0.074482 | -8.11734 to -0.029948 | 0.035402 | 0.034128 | 0.054204 | 0.080763 |
| bear | hist_gradient_boosting | MFE | legacy unconstrained | HistGradientBoostingRegressor | 0 | 0 | 0.016010 to 0.875942 | 0.015160 to 0.639525 | 0.049010 | 0.046486 | 0.081442 | 0.077270 |
| bear | hist_gradient_boosting | MAE | legacy unconstrained | HistGradientBoostingRegressor | 0 | 0 | -0.254106 to -0.016791 | -0.248290 to -0.014534 | 0.029229 | 0.029017 | 0.044693 | 0.044462 |
| bull | hist_gradient_boosting | MFE | legacy unconstrained | HistGradientBoostingRegressor | 0 | 0 | 0.013525 to 0.405552 | 0.015042 to 0.457544 | 0.036643 | 0.036250 | 0.063099 | 0.062910 |
| bull | hist_gradient_boosting | MAE | legacy unconstrained | HistGradientBoostingRegressor | 0 | 0 | -0.345176 to -0.014847 | -0.316877 to -0.014020 | 0.039561 | 0.036931 | 0.054190 | 0.051616 |
| bear | extra_trees | MFE | legacy unconstrained | ExtraTreesRegressor | 0 | 0 | 0.011097 to 0.696223 | 0.011097 to 0.696223 | 0.049023 | 0.049023 | 0.079037 | 0.079037 |
| bear | extra_trees | MAE | legacy unconstrained | ExtraTreesRegressor | 0 | 0 | -0.251865 to -0.011227 | -0.243371 to -0.011313 | 0.029215 | 0.029274 | 0.044681 | 0.044752 |
| bull | extra_trees | MFE | legacy unconstrained | ExtraTreesRegressor | 0 | 0 | 0.011948 to 0.330464 | 0.011948 to 0.330464 | 0.036158 | 0.036158 | 0.062973 | 0.062973 |
| bull | extra_trees | MAE | legacy unconstrained | ExtraTreesRegressor | 0 | 0 | -0.337872 to -0.012223 | -0.359505 to -0.011424 | 0.037982 | 0.038082 | 0.052177 | 0.052351 |

The prior bear linear MFE negative predictions and bull linear MAE positive predictions are eliminated. Predictive quality remains mixed, and linear-family Tweedie path heads now have larger OOD severity due to heavy-tailed positive-link outputs.

## Label Regression Check

Panel checked:

`data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`

Rows checked:

- 5 ordinary-stock rows.
- 5 ordinary ETF rows.
- 5 leveraged/inverse rows.
- 5 extreme bull MFE rows.
- 5 extreme bear MFE rows.
- 8,715 unique rows associated with legacy sign-contract prediction failures.

Total checked:

- Unique symbol-date rows: 8,740
- Label values recomputed from raw OHLCV: 52,440
- Stored-label mismatches: 0

Historical labels were not changed.

## Scanner Review

Command:

`.venv/bin/python -m swing_rsi.cli scan --include-challengers`

Result:

- Scan ID: `b8d10d0bf478bae78f500f80`
- As-of date: `2026-06-18`
- Rows: 50
- Actionable rows: 0
- Rejected rows: 50
- MFE magnitude-domain rejections: 0
- MAE magnitude-domain rejections: 0
- MFE sign-contract rejections: 0
- MAE sign-contract rejections: 0
- OOD warning rows: 3
- OOD affected heads: `mfe;mae`
- Exact rejection reasons: `model_not_promoted` on all 50 rows; `mfe_ood_severity_exceeds_frozen_limit` and `mae_ood_severity_exceeds_frozen_limit` on 3 rows.

Gate-ineligible models remained non-actionable.

## Failed Gates

All models remain promotion-ineligible. Common blockers include:

- `final_holdout_required_for_promotion`
- `positive_expected_value_after_costs`
- `transaction_cost_sensitivity_not_collapsed`
- `return_holdout_ood_q99_severity_acceptable`
- Path OOD severity or catastrophic extrapolation failures on several learned models
- `not_naive_control` for naive controls

The new MFE/MAE domain gates passed for every model:

- `mfe_magnitude_domain_integrity_valid`: 8 PASS
- `mae_magnitude_domain_integrity_valid`: 8 PASS
- `mfe_prediction_path_metric_sign_valid`: 8 PASS
- `mae_prediction_path_metric_sign_valid`: 8 PASS

## Tests And Checks

Pre-retrain verification:

- `.venv/bin/pytest`: 265 passed
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed
- `.venv/bin/mypy src`: passed

Fresh generation:

- `.venv/bin/python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80`
- Run exactly once.
- Models registered: 8.
- Promoted: 0.

Audit:

- `.venv/bin/python -m swing_rsi.cli model-audit --generation latest --export-dir reports/path_magnitude_domain_v1`

Final verification was run after scanner review and handoff creation.

## State Integrity

- No FMP update was run.
- Raw features and labels were not rebuilt.
- No historical labels were modified.
- Prior model artifacts were not rewritten.
- No model was promoted.
- No final-holdout run was initialized.
- No forward-update or daily-cycle was run.
- No paper-forward event was created by this milestone.

## Next Task

Exactly one smallest confirmed next task:

Perform a read-only OOD extrapolation diagnosis of the new Tweedie path-magnitude heads before changing path targets, estimators, or OOD policy.
