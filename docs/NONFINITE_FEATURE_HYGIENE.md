# Nonfinite Feature Hygiene V1

## Purpose

Nonfinite Feature Hygiene V1 prevents invalid numeric feature values from reaching model feature screening, preprocessing, imputation, estimator fitting, calibration prediction, development-holdout prediction, and scanner prediction.

The confirmed trigger was `obv_change_20 = -inf` for `RWM` and `SH` on `2016-07-19` in the `INVERSE` bull cohort from generation `2026-06-26T12:37:53.103302+00:00`. The failure was a missing nonfinite feature-input guard with a contributing scope-specific data-quality issue.

## Policy

Schema: `model_feature_nonfinite_hygiene_v1`

The model feature matrix policy is:

- replace positive infinity with `NaN`;
- replace negative infinity with `NaN`;
- replace finite values whose absolute magnitude exceeds the configured float64 guard with `NaN`;
- preserve existing `NaN` values as missing values;
- never convert invalid values to zero by default;
- let the existing train-fitted preprocessing and imputation path handle sanitized missing values;
- reject the model artifact if invalid values remain after sanitization.

Rejection reason: `model_feature_matrix_nonfinite_after_sanitization`

Legacy artifacts trained before this schema remain readable and are labeled `legacy_pre_nonfinite_hygiene`.

## Feature Generation

`obv_change_20` now uses explicit safe percentage-change semantics instead of raw `pct_change`.

Safe denominator behavior:

- finite numerator divided by zero or near-zero denominator returns `NaN`;
- zero divided by zero returns `NaN`;
- no OBV-change calculation emits positive or negative infinity.

This preserves the economic meaning of OBV change while removing invalid nonfinite outputs.

## Model Matrix Boundary

The training pipeline sanitizes feature matrices before:

- primary feature screening;
- Target-Before-Stop feature screening;
- path-head feature screening;
- primary classifier fit;
- Target-Before-Stop classifier fit;
- expected-return regressor fit;
- MFE regressor fit;
- MAE regressor fit;
- calibration prediction;
- development-holdout prediction.

The same guard is also applied in shared prediction helpers so permutation importance, path-target prediction, path-magnitude prediction, and scanner prediction cannot send raw infinities into estimators.

## Artifact Metadata

Every new model bundle persists:

- hygiene schema;
- hygiene policy hash;
- pre-sanitization positive-infinity count;
- pre-sanitization negative-infinity count;
- pre-sanitization existing-NaN count;
- pre-sanitization too-large count;
- post-sanitization invalid count;
- post-sanitization missing count;
- affected columns;
- sanitized columns;
- affected feature families;
- affected symbols;
- affected dates;
- counts by split and stage;
- per-stage audit records.

Changing the policy changes the policy hash and scanner identity.

## Scanner Behavior

Scanner prediction uses the frozen artifact preprocessing path. If live features contain invalid values, the scanner:

- sanitizes them with the artifact hygiene policy;
- records a candidate-level hygiene warning;
- records sanitized columns, affected symbols, affected dates, and runtime hygiene metadata;
- rejects only when required features remain unavailable after the frozen preprocessing path or another existing policy gate fails.

No unpromoted development model becomes actionable because of hygiene.

## Dashboard And Audit

Model audit exports and dashboard drilldowns expose:

- hygiene schema and policy hash;
- pre- and post-sanitization counts;
- affected columns and families;
- affected symbol/date summaries;
- scanner runtime hygiene warnings.

The main tables remain compact; detailed evidence is available through Model Registry, Discovery Lab, Live Scanner, and Candidate Attribution views.

## Integrity Boundaries

Nonfinite hygiene does not:

- alter raw OHLCV;
- alter labels;
- alter product-class mappings;
- alter thresholds or quality gates;
- weaken Prediction OOD Governance V2;
- change calibration governance;
- promote models;
- initialize final holdout;
- mutate the frozen operational repository.
