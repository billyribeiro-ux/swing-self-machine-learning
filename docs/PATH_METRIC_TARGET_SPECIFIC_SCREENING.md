# Path-Metric Target-Specific Feature Screening

Path-metric regression heads predict continuous targets that are distinct from the primary positive-return classifier target. New artifacts therefore screen features independently for:

- expected directional return;
- maximum favorable excursion, MFE;
- maximum adverse excursion, MAE.

## Schema

The path-metric screening schema is:

`path_metric_target_specific_feature_screen_v1`

Each screen persists:

- head name;
- exact target label;
- direction and horizon;
- task type `regression`;
- training date range and row count;
- eligible, post-missingness, post-variance, scored, correlation-pruned, and selected feature counts;
- selected features and families;
- train-only mutual-information scores and ranks;
- rejection reasons;
- selected-feature manifest hash;
- screen configuration hash;
- deterministic seed.

## Train-Only Order

For each path head, discovery:

1. Starts from the complete eligible numeric feature universe.
2. Excludes `label_` columns, future-derived fields, dates/timestamps, unsupported objects, identifiers not governed as features, the target itself, and registry-prohibited fields.
3. Fits missingness filtering on training rows only.
4. Fits zero-variance and near-zero-variance filtering on training rows only.
5. Fits imputation values on training rows only.
6. Scores every surviving feature against the head's own continuous training target with `mutual_info_regression`.
7. Normalizes invalid scores explicitly.
8. Sorts by score descending and feature name ascending.
9. Applies correlation pruning on training data in score order.
10. Stops after the configured maximum selected-feature count.

Calibration and development-holdout rows cannot affect screening, imputation, score ordering, correlation pruning, or selected manifests.

## Artifact And Scanner Contract

Artifacts persist separate metadata for:

- `expected_return_feature_screen`;
- `mfe_feature_screen`;
- `mae_feature_screen`.

The scanner builds separate frozen feature matrices for the primary classifier, Target-Before-Stop classifier, expected-return regressor, MFE regressor, and MAE regressor. Missing required path-head features reject safely with:

- `expected_return_required_feature_missing`;
- `mfe_required_feature_missing`;
- `mae_required_feature_missing`.

Scanner identity includes the path-head screen schemas and manifest hashes, so changing any path-head manifest changes the scanner snapshot ID.

## Legacy Artifacts

Artifacts without path-specific feature-screen metadata remain readable for historical audit and are labeled `legacy_shared_path_feature_screen`. They are not equivalent to new-schema artifacts and cannot satisfy the new promotion artifact contract.
