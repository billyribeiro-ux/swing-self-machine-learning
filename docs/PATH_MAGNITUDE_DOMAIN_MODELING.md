# Path Magnitude Domain Modeling

Schema: `path_metric_magnitude_domain_v1`

## Contract

Historical path labels remain unchanged:

- expected return is a signed directional decimal return;
- MFE is favorable decimal return and must be `>= 0`;
- MAE is adverse decimal return and must be `<= 0`.

MFE and MAE models train on internal nonnegative magnitudes without rewriting the stored label panel:

- `mfe_magnitude_target = existing MFE label`;
- `mae_magnitude_target = -1 * existing MAE label`.

Prediction maps back to canonical external units:

- `mfe_prediction = predicted_mfe_magnitude`;
- `mae_prediction = -1 * predicted_mae_magnitude`.

No post-hoc clipping is part of the path. Invalid estimator output is an integrity failure.

## Estimator Policy

Path-magnitude heads use family-specific domain-preserving estimators:

- linear-family discovery models use `TweedieRegressor(power=1.5, link="log")`;
- HistGradientBoosting path-magnitude heads use `HistGradientBoostingRegressor(loss="poisson")`;
- ExtraTrees path-magnitude heads fit `ExtraTreesRegressor` directly on nonnegative magnitudes;
- naive controls use the training mean of nonnegative magnitudes and remain non-promotable.

Expected-return regression is unchanged and remains signed.

## Screening

The existing target-specific path feature screening remains train-only.

- Expected-return screens against the signed expected-return label.
- MFE screens against the internal favorable magnitude target.
- MAE screens against the internal adverse magnitude target.

Screening still starts from the complete eligible numeric feature universe and excludes all `label_` columns from feature matrices.

## Artifact Metadata

Each new MFE and MAE head persists:

- domain schema version;
- external target name;
- internal magnitude target name and definition;
- estimator class, loss, hyperparameters, preprocessing hash, and estimator hash;
- selected-feature manifest hash;
- prediction mapping version;
- internal magnitude diagnostics;
- canonical signed-output diagnostics;
- convergence diagnostics;
- domain-integrity gate evidence.

Legacy unconstrained path artifacts remain readable for audit and are labeled `legacy_unconstrained_path_metric_model`.

## Scanner Behavior

The scanner uses the frozen head-specific feature matrix, predicts the internal magnitude, validates it, maps to canonical signed output, validates that output, and then applies OOD Governance V2 in canonical signed units.

Scanner rejection reasons include:

- `mfe_domain_metadata_missing`;
- `mae_domain_metadata_missing`;
- `mfe_magnitude_prediction_invalid`;
- `mae_magnitude_prediction_invalid`;
- `mfe_prediction_sign_contract_failed`;
- `mae_prediction_sign_contract_failed`.

Scanner identity includes the domain schema, estimator hashes, prediction mapping version, and magnitude target metadata.
