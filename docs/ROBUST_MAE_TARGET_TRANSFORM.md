# Robust MAE Target Transformation V1

## Scope

`robust_path_target_transform_v1` applies only to:

- product-class scope: `POOLED`
- direction: `bull`
- model family: `hist_gradient_boosting`
- prediction head: `mae`
- horizon: `10`

Every other product scope, direction, model family, horizon, and prediction head persists:

```text
path_target_transform = none
```

## Motivation

The remaining OOD source diagnosis for generation `2026-06-26T23:52:15.769542+00:00` found no failed learned-model OOD Governance V2 mandatory gate. The only repeated learned-model OOD pattern was a small warning cluster in the POOLED bull HistGradientBoosting MAE head:

- six development-holdout OOD warnings;
- OOD rate `0.035%`;
- q99 severity `0.072861`;
- maximum severity `0.073748`;
- all warnings on `2025-10-31`;
- no selected candidate row affected;
- no sign-contract failure;
- no nonfinite prediction;
- no realized-target tail breach;
- no OOD-bound mapping defect.

The diagnosis classified the source as estimator extrapolation with product-class heterogeneity, a localized date/regime effect, and a model-family limitation specific to POOLED bull HistGradientBoosting MAE.

## Transform

The external label contract is unchanged. Canonical MAE remains signed adverse path output and must remain `<= 0`.

The internal MAE estimator target remains adverse magnitude and must remain `>= 0`.

For the scoped head only, the estimator fit target is:

```text
z = log1p(y)
```

where `y` is the training-row internal adverse MAE magnitude.

Runtime prediction uses:

```text
y_hat = expm1(z_hat)
canonical_mae = -y_hat
```

The transform is deterministic, monotonic, and fitted from training rows only. Calibration and development-holdout targets are not used to fit or tune the transform.

## Governance

OOD Governance V2 is unchanged.

OOD checks use the inverse-transformed internal MAE magnitude in canonical model units, not log-space predictions. The scanner and model audit persist:

- transform schema;
- transform name;
- transform hash;
- fit split;
- pre-transform training target distribution;
- post-transform training target distribution;
- transformed prediction distribution;
- inverse-transformed magnitude distribution;
- canonical signed MAE distribution.

Changing the transform metadata changes the model artifact identity through artifact content and changes scanner identity through the path-target-transform hash.

## Scanner Behavior

Scanner prediction for the scoped head:

1. Builds the frozen MAE feature matrix.
2. Predicts transformed MAE magnitude.
3. Applies the frozen inverse transform.
4. Maps to canonical signed MAE.
5. Validates sign contract.
6. Applies OOD Governance V2 in canonical units.
7. Persists transform metadata in scanner candidate rows.

If a transformed head declares the new transform schema but omits required transform metadata, scanner prediction rejects the row with:

```text
path_target_transform_metadata_missing
```

## Non-Changes

This correction does not change:

- raw OHLCV;
- labels;
- target/stop definitions;
- product-class mappings;
- feature definitions;
- selection thresholds;
- quality gates;
- OOD Governance V2;
- calibration governance;
- final-holdout rules;
- model promotion behavior.
