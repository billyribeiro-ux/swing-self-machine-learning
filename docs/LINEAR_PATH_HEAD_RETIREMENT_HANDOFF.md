# Linear-Family Path-Head Retirement V1 Handoff

Date: 2026-06-25

## Scope

Implemented and verified Linear-Family Path-Head Retirement V1 after the immutable baseline generation:

`2026-06-22T18:07:43.648509+00:00`

That baseline generation remains immutable and was not rerun. It is only a comparison baseline from the earlier domain-preserving magnitude-modeling task.

## Implementation

Logistic-family artifacts keep these heads active:

- primary positive-return classifier
- Target-Before-Stop classifier
- expected-return regressor

Logistic-family artifacts retire these required path heads:

- MFE: `RETIRED_UNSUITABLE_ESTIMATOR`
- MAE: `RETIRED_UNSUITABLE_ESTIMATOR`

Retirement schema:

`linear_family_path_head_retirement_v1`

Retirement reason:

`linear_family_path_head_retired_unsuitable_estimator`

The logistic MFE/MAE path uses `RetiredPathHeadModel` placeholders and fits no Tweedie MFE/MAE estimator. ExtraTrees and HistGradientBoosting MFE/MAE heads remain active under `path_metric_magnitude_domain_v1`.

## Implementation Commit

Retirement cleanup commit reviewed before discovery:

`67b4e17787d7d40cef7bd05118dc94165151a6c7`

Review result: clean.

Checked specifically for:

- hidden logistic Tweedie MFE/MAE fitting: none found
- primary/TBS/expected-return heads accidentally retired: not found
- nonlinear MFE/MAE heads accidentally retired: not found
- scanner bypass for retired heads: blocked with explicit retired-head reasons
- generic retired-head scanner noise: removed from scanner exclusion reasons
- final-holdout enrollment bypass: blocked by required path-head blockers and mandatory gate failures

## Pre-Discovery Verification

Ran before the post-retirement discovery:

- `.venv/bin/pytest`: 272 passed, 166 warnings
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed
- `.venv/bin/mypy src`: passed

## Post-Retirement Discovery

Ran `discover-models` exactly once after the implementation commit and review:

`.venv/bin/python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80`

New post-retirement generation:

`2026-06-25T13:11:51.610283+00:00`

This differs from the immutable baseline:

`2026-06-22T18:07:43.648509+00:00`

Result:

- Models registered this run: 8
- Challengers: 0
- Candidates needing review: 8
- Rejected/experimental: 0
- Promoted models: 0
- Best failed-gate candidate retained for inspection: `20ec5e2b936145463e2d22bf`

## New Model IDs

| Direction | Family | Model ID | State |
|---|---|---|---|
| bear | extra_trees | `4d66c49b675803520298a243` | CANDIDATE |
| bear | hist_gradient_boosting | `4b25faeeca72518f3f435fa7` | CANDIDATE |
| bear | logistic_regression | `7a534a2fcf2a3e8f4e17a83f` | CANDIDATE |
| bear | naive_base_rate | `e502adcfe8cf8c25c3138ee3` | CANDIDATE |
| bull | extra_trees | `108bc18cfa5be414666c2512` | CANDIDATE |
| bull | hist_gradient_boosting | `b93b2258c10aea5cef81d291` | CANDIDATE |
| bull | logistic_regression | `ed57a9e3a3be12fe39241f62` | CANDIDATE |
| bull | naive_base_rate | `20ec5e2b936145463e2d22bf` | CANDIDATE |

## Artifact Verification

| Direction | Family | MFE State | MFE Estimator | MAE State | MAE Estimator | Required-Head Gates |
|---|---|---|---|---|---|---|
| bear | logistic_regression | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | FAIL / FAIL |
| bull | logistic_regression | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | FAIL / FAIL |
| bear | extra_trees | ACTIVE | ExtraTreesRegressor | ACTIVE | ExtraTreesRegressor | PASS / PASS |
| bull | extra_trees | ACTIVE | ExtraTreesRegressor | ACTIVE | ExtraTreesRegressor | PASS / PASS |
| bear | hist_gradient_boosting | ACTIVE | HistGradientBoostingRegressor | ACTIVE | HistGradientBoostingRegressor | PASS / PASS |
| bull | hist_gradient_boosting | ACTIVE | HistGradientBoostingRegressor | ACTIVE | HistGradientBoostingRegressor | PASS / PASS |

Logistic verification:

- no Tweedie MFE estimator artifact
- no Tweedie MAE estimator artifact
- MFE and MAE capability states are retired
- loaded primary classifier remains an active pipeline
- loaded Target-Before-Stop classifier remains an active pipeline
- loaded expected-return regressor remains an active pipeline
- `mfe_required_path_head_active` fails
- `mae_required_path_head_active` fails
- final-holdout enrollment blockers include `mfe_path_head_retired_unsuitable_estimator` and `mae_path_head_retired_unsuitable_estimator`

Nonlinear verification:

- ExtraTrees MFE/MAE heads load as `ExtraTreesRegressor`
- HistGradientBoosting MFE/MAE heads load as `HistGradientBoostingRegressor`
- nonlinear required-path-head gates pass

## Scanner Verification

Ran review-only scanner after the post-retirement discovery:

`.venv/bin/python -m swing_rsi.cli scan --include-challengers`

Result:

- Scan ID: `9a0c6eb95e2551a716d16e2b`
- As-of date: `2026-06-18`
- Rows: 50
- Actionable rows: 0
- Rejected rows: 50
- Retired-head rows: 13

Scanner exclusion patterns:

| Exclusion reason | Rows |
|---|---:|
| `model_not_promoted` | 37 |
| `model_not_promoted;mfe_linear_family_path_head_retired_unsuitable_estimator;mae_linear_family_path_head_retired_unsuitable_estimator` | 13 |

Generic retired-head scanner noise:

- `nonfinite_prediction`: 0 rows
- `mfe_magnitude_prediction_invalid`: 0 rows
- `mae_magnitude_prediction_invalid`: 0 rows
- `mfe_prediction_sign_contract_failed`: 0 rows
- `mae_prediction_sign_contract_failed`: 0 rows

## State Integrity

No model was promoted.

No `forward-update`, `daily-cycle`, or `final-holdout-init` command was run.

No prospective final-holdout run was created.

State after verification:

- latest generation: `2026-06-25T13:11:51.610283+00:00`
- total model rows: 146
- latest generation rows: 8
- latest generation states: 8 `CANDIDATE`, 0 `CHALLENGER`, 0 `CHAMPION`
- final-holdout runs: 0
- forward events: 285, unchanged from the pre-discovery count
- scanner snapshot created for verification only: `9a0c6eb95e2551a716d16e2b`

## Data Leakage Review

No raw data, labels, feature definitions, thresholds, calibration methods, OOD governance, research dates, signal timestamps, entries, exits, costs, or failed trades were changed.

No discovery was run before the implementation commit review.

No FMP update was run.

No final-holdout data was created or used.

No forward-test outcomes were used.

The post-retirement discovery used existing local market data, existing feature panels, and existing labels.

## Assumptions

- Linear family means the repository's `logistic_regression` family.
- Retired required path heads are explicit artifact metadata, not missing metadata.
- Scanner non-actionability can be verified in review mode through rejected rows without creating paper-forward events.

## Known Limitations

- Retiring logistic-family MFE/MAE heads does not improve nonlinear model quality.
- Logistic-family models remain review/audit artifacts because required MFE/MAE path heads are unavailable.
- The current holdout remains `DEVELOPMENT_HOLDOUT`, not final validation evidence.

## Scope Changes

No Version 1 scope expansion.

No options, intraday data, market internals, brokerage execution, reinforcement learning, or deep learning were added.

## Next Smallest Milestone

Perform a read-only diagnosis of the remaining nonlinear model quality and selected-candidate gate failures in the new post-retirement generation.
