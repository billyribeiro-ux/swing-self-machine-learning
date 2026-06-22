# Path-Metric Target-Specific Screen Handoff

## Confirmed Root Cause

The path-metric diagnosis found no path-label or decimal/percentage unit defect. Expected return, MFE, and MAE reused the primary positive-return classifier's selected feature screen. That was an implementation/design defect because each regression head predicts a different continuous target.

## Old Behavior

Baseline generation `2026-06-21T20:51:00.841677+00:00` had no path-specific feature-screen metadata for expected return, MFE, or MAE. Model audit labels those heads as legacy shared-screen behavior. The path heads used the primary classifier feature set for convenience rather than screening against their own regression targets.

## New Architecture

The reusable `screen_features_for_target(...)` service now supports both:

- binary classification with `mutual_info_classif`;
- continuous regression with `mutual_info_regression`.

Path-metric heads persist schema `path_metric_target_specific_feature_screen_v1`. Every new model artifact stores separate expected-return, MFE, and MAE feature-screen metadata, selected features, feature-family counts, scores, ranks, rejection reasons, configuration hash, and selected-feature manifest hash.

The scanner now builds separate frozen feature matrices for:

- primary positive-return classifier;
- Target-Before-Stop classifier;
- expected-return regressor;
- MFE regressor;
- MAE regressor.

Missing path-head features reject with `expected_return_required_feature_missing`, `mfe_required_feature_missing`, or `mae_required_feature_missing`. Scanner identity includes the path-head schemas and manifest hashes.

## Train-Only Screening Order

Each path head:

1. Starts from the complete eligible numeric feature universe.
2. Excludes labels, target columns, date/timestamp metadata, unsupported objects, identifiers not governed as features, and registry-prohibited fields.
3. Fits missingness filtering on training rows only.
4. Fits zero-variance and near-zero-variance filtering on training rows only.
5. Fits imputation values on training rows only.
6. Scores surviving features against the head's own continuous training target with `mutual_info_regression`.
7. Normalizes invalid scores explicitly.
8. Sorts by score descending, then feature name ascending.
9. Applies correlation pruning on training rows in score order.
10. Stops after the configured 60-feature cap.

Calibration and development-holdout rows do not affect feature selection or preprocessing.

## Review Result

Focused review found no P1/P2 defects for target-label mismatch, train/calibration/holdout leakage, shared feature-list reuse, shared preprocessing reuse, column-order dependence, target columns entering feature matrices, scanner wrong-feature-frame routing, scanner manifest identity omissions, legacy artifact mutation, or dashboard feature-explanation merging.

## Commits

- `fc0864d` - `fix: add target-specific path metric screening`
- `d4764dd` - `test: validate path metric feature isolation`
- `2f6af2b` - `docs: document path metric feature screening`

## Fresh Generation

- Fresh generation ID: `2026-06-22T16:01:49.047908+00:00`
- Discovery command run exactly once.
- Registered models: 8
- Learned models: 6
- Naive controls: 2
- Challengers: 0
- Candidates needing review: 8
- Promoted models: 0

Learned model IDs:

| Direction | Family | Model ID |
| --- | --- | --- |
| bear | extra_trees | `61fa3756fa70da1c5b504bd0` |
| bear | hist_gradient_boosting | `9d32eb45bdfc83302d488d7a` |
| bear | logistic_regression | `fb938244d86ccf9208fc578b` |
| bull | extra_trees | `222619b5ab718e35a1044086` |
| bull | hist_gradient_boosting | `86eba769fa8643c8fd1c289d` |
| bull | logistic_regression | `33c9cc8d6ba9676fce514a3a` |

## Feature Families Selected

Every path head selected 60 features. Selected family counts are identical across model families for the same direction/head because screening is deterministic and model-family independent.

| Direction | Head | Selected family counts |
| --- | --- | --- |
| bear | expected_return | market_relative 9, sector_relative 1, inverse_leveraged 1, relationship_graph 1, regime 1, volatility_range 9, volume_participation 1, trend_structure 14, returns_momentum 18, technical_primitives 5 |
| bear | MFE | market_relative 4, inverse_leveraged 2, relationship_graph 13, regime 2, volatility_range 9, trend_structure 14, returns_momentum 7, technical_primitives 9 |
| bear | MAE | market_relative 6, sector_relative 1, relationship_graph 1, regime 1, volatility_range 9, trend_structure 17, returns_momentum 17, technical_primitives 8 |
| bull | expected_return | market_relative 8, sector_relative 1, inverse_leveraged 1, relationship_graph 1, regime 1, volatility_range 9, volume_participation 1, trend_structure 15, returns_momentum 18, technical_primitives 5 |
| bull | MFE | market_relative 6, sector_relative 1, relationship_graph 2, regime 2, volatility_range 9, trend_structure 17, returns_momentum 17, technical_primitives 6 |
| bull | MAE | market_relative 6, inverse_leveraged 3, relationship_graph 6, regime 2, volatility_range 9, trend_structure 14, returns_momentum 15, technical_primitives 5 |

Breadth and RSI-family features were considered but selected zero path-head features in this generation. No family was forced.

## Baseline Comparison

Baseline path-head feature count was `legacy_shared` for expected return, MFE, and MAE. New count is 60 for every path head.

| Direction | Family | Head | Old MAE | New MAE | Old RMSE | New RMSE | New sign valid |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| bear | extra_trees | expected_return | 0.052642 | 0.059716 | 0.086525 | 0.094974 | true |
| bear | extra_trees | MFE | n/a | 0.049079 | n/a | 0.079110 | true |
| bear | extra_trees | MAE | n/a | 0.029158 | n/a | 0.044510 | true |
| bear | hist_gradient_boosting | expected_return | 0.052065 | 0.056524 | 0.086594 | 0.092504 | true |
| bear | hist_gradient_boosting | MFE | n/a | 0.049120 | n/a | 0.081534 | true |
| bear | hist_gradient_boosting | MAE | n/a | 0.029192 | n/a | 0.044557 | true |
| bear | logistic_regression | expected_return | 0.052432 | 0.052288 | 0.086635 | 0.087337 | true |
| bear | logistic_regression | MFE | n/a | 0.066730 | n/a | 0.103478 | false |
| bear | logistic_regression | MAE | n/a | 0.029362 | n/a | 0.045525 | true |
| bull | extra_trees | expected_return | 0.051780 | 0.056896 | 0.082506 | 0.088230 | true |
| bull | extra_trees | MFE | n/a | 0.036072 | n/a | 0.062749 | true |
| bull | extra_trees | MAE | n/a | 0.038016 | n/a | 0.052185 | true |
| bull | hist_gradient_boosting | expected_return | 0.051363 | 0.054064 | 0.081680 | 0.086232 | true |
| bull | hist_gradient_boosting | MFE | n/a | 0.036560 | n/a | 0.062893 | true |
| bull | hist_gradient_boosting | MAE | n/a | 0.039600 | n/a | 0.054171 | true |
| bull | logistic_regression | expected_return | 0.050758 | 0.050829 | 0.081593 | 0.082480 | true |
| bull | logistic_regression | MFE | n/a | 0.037434 | n/a | 0.063867 | true |
| bull | logistic_regression | MAE | n/a | 0.035390 | n/a | 0.054147 | false |

Selection counts changed only for HistGradientBoosting:

- bull HistGradientBoosting: 204 old selected rows, 190 new selected rows.
- bear HistGradientBoosting: 48 old selected rows, 42 new selected rows.
- all other learned models: 0 old and 0 new selected rows.

No model became promotion eligible.

## Label Regression

Stored labels were recomputed from raw OHLCV without modifying data.

- Ordinary stock rows checked: 5
- Ordinary ETF rows checked: 5
- Leveraged/inverse rows checked: 5
- Prior extreme MFE rows checked: 5
- Prior extreme MAE rows checked: 5
- Sign-violation-associated prediction rows checked: 10,215
- Unique symbol/date rows checked: 8,735
- Stored-vs-rebuilt label value comparisons: 52,410
- Label mismatches: 0

Sign-violation-associated rows came from:

- bear logistic regression: 8,714 rows
- bull logistic regression: 1,501 rows

The feature-screen correction did not change labels.

## OOD And Sign Results

All new artifacts use OOD Governance V2. Sign-contract failures remain in logistic path heads:

- bear logistic MFE sign invalid;
- bull logistic MAE sign invalid.

Several models still fail OOD severity or catastrophic extrapolation gates. These failures are model-quality/governance results, not evidence that the feature-screen implementation failed.

## Failed Gates And Promotion

All learned models remain `CANDIDATE` and promotion-ineligible. Every model fails `final_holdout_required_for_promotion` because the current holdout is `DEVELOPMENT_HOLDOUT`.

Mandatory failed-gate counts:

| Direction | Family | Failed mandatory gates |
| --- | --- | ---: |
| bear | extra_trees | 9 |
| bear | hist_gradient_boosting | 6 |
| bear | logistic_regression | 14 |
| bull | extra_trees | 8 |
| bull | hist_gradient_boosting | 5 |
| bull | logistic_regression | 14 |

Canonical full gate details are exported under `reports/path_metric_target_specific_screen/full_gate_audit.csv`.

## Scanner Review

Review-only scanner command:

`.venv/bin/python -m swing_rsi.cli scan --include-challengers`

Result:

- Scan ID: `560534168163d3ca4d07b40c`
- As-of date: `2026-06-18`
- Rows: 50
- Bullish rows: 25
- Bearish rows: 25
- Actionable rows: 0
- Rejected rows: 50
- Rejection reason: `model_not_promoted` for all rows
- OOD warning rows: 4
- Required path-feature rejections: 0 expected-return, 0 MFE, 0 MAE
- Path-screen schema in scanner rows: `path_metric_target_specific_feature_screen_v1`

Gate-ineligible models remained non-actionable. No forward-update was run.

## Verification

Pre-retrain verification:

- `.venv/bin/pytest` - 252 passed
- `.venv/bin/ruff check .` - passed
- `.venv/bin/ruff format --check .` - 98 files already formatted
- `.venv/bin/mypy src` - passed

Final verification:

- `.venv/bin/pytest` - 252 passed
- `.venv/bin/ruff check .` - passed
- `.venv/bin/ruff format --check .` - 98 files already formatted
- `.venv/bin/mypy src` - passed

No model was promoted. No final-holdout run was initialized. No forward-update or daily-cycle command was run.

## Next Smallest Task

Model MFE and MAE as domain-preserving magnitudes so MFE cannot be negative and MAE cannot be positive, without changing labels, gates, target/stop definitions, or the 0.50 Target-Before-Stop threshold.
