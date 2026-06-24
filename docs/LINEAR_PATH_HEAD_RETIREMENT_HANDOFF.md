# Linear-Family Path-Head Retirement V1 Handoff

Date: 2026-06-24

## Scope

Implemented Linear-Family Path-Head Retirement V1 after the immutable baseline generation:

`2026-06-22T18:07:43.648509+00:00`

This milestone did not rerun the previous domain-preserving magnitude-modeling task. The baseline remains immutable and was used only for comparison.

## Implementation

Logistic-family artifacts now keep these heads active:

- primary positive-return classifier
- Target-Before-Stop classifier
- expected-return regressor

Logistic-family artifacts now retire these required path heads:

- MFE: `RETIRED_UNSUITABLE_ESTIMATOR`
- MAE: `RETIRED_UNSUITABLE_ESTIMATOR`

Retirement schema:

`linear_family_path_head_retirement_v1`

Retirement reason:

`linear_family_path_head_retired_unsuitable_estimator`

The logistic MFE/MAE path uses `RetiredPathHeadModel` placeholders and does not fit or persist Tweedie MFE/MAE estimators. ExtraTrees and HistGradientBoosting MFE/MAE heads remain active and unchanged under `path_metric_magnitude_domain_v1`.

## Enforcement

Added mandatory gates:

- `mfe_required_path_head_active`
- `mae_required_path_head_active`

Added scanner rejection reasons for retired heads:

- `mfe_linear_family_path_head_retired_unsuitable_estimator`
- `mae_linear_family_path_head_retired_unsuitable_estimator`

Promotion and prospective final-holdout enrollment now reject retired required path heads explicitly.

Scanner identity now includes path-head capability state and retirement metadata.

## Implementation Review

Review result: clean.

Checked specifically for:

- hidden Tweedie MFE/MAE fitting in logistic artifacts: none found
- MFE/MAE placeholder prediction being called by scanner: not called
- primary/TBS/expected-return heads accidentally retired: not found
- nonlinear MFE/MAE heads accidentally retired: not found
- promotion bypass: blocked by mandatory required-head gates and registry metadata blockers
- scanner bypass: blocked by state/gate eligibility and retired-head prediction integrity
- final-holdout enrollment bypass: blocked by development-gate blockers

Implementation commit:

`df5c396caed1b9901194a418fd30bfc86d096271`

## Pre-Discovery Verification

Ran before the post-retirement discovery:

- `.venv/bin/pytest`: 268 passed
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed
- `.venv/bin/mypy src`: passed

## Post-Retirement Generation

Ran `discover-models` exactly once after the implementation commit:

`.venv/bin/python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80`

New generation:

`2026-06-24T12:38:43.122103+00:00`

This differs from the immutable baseline:

`2026-06-22T18:07:43.648509+00:00`

Models registered: 8

Challengers: 0

Candidates needing review: 8

Promoted models: 0

## New Model IDs

| Direction | Family | Model ID | State |
|---|---|---|---|
| bull | logistic_regression | `6368d67eaaa721101de5ceb4` | CANDIDATE |
| bear | logistic_regression | `49f255fd5496f5d7881499e6` | CANDIDATE |
| bull | extra_trees | `0ddd122a586fb6c797357ad5` | CANDIDATE |
| bear | extra_trees | `722fb3fda82754b5bd572e4c` | CANDIDATE |
| bull | hist_gradient_boosting | `d32c5d3e44372e91342e39d8` | CANDIDATE |
| bear | hist_gradient_boosting | `b2f4d14b22d11d5875700fee` | CANDIDATE |
| bull | naive_base_rate | `d881e09a3dc9f92bf6d4c96a` | CANDIDATE |
| bear | naive_base_rate | `5b6124023f68bcf60ec2d943` | CANDIDATE |

## Artifact Verification

| Direction | Family | MFE State | MFE Estimator | MAE State | MAE Estimator | Required-Head Gates |
|---|---|---|---|---|---|---|
| bull | logistic_regression | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | FAIL / FAIL |
| bear | logistic_regression | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | RETIRED_UNSUITABLE_ESTIMATOR | RetiredPathHeadModel | FAIL / FAIL |
| bull | extra_trees | ACTIVE | ExtraTreesRegressor | ACTIVE | ExtraTreesRegressor | PASS / PASS |
| bear | extra_trees | ACTIVE | ExtraTreesRegressor | ACTIVE | ExtraTreesRegressor | PASS / PASS |
| bull | hist_gradient_boosting | ACTIVE | HistGradientBoostingRegressor | ACTIVE | HistGradientBoostingRegressor | PASS / PASS |
| bear | hist_gradient_boosting | ACTIVE | HistGradientBoostingRegressor | ACTIVE | HistGradientBoostingRegressor | PASS / PASS |

Logistic verification:

- no Tweedie MFE estimator artifact
- no Tweedie MAE estimator artifact
- MFE and MAE capability states retired
- primary feature manifests present
- Target-Before-Stop feature manifests present
- expected-return feature manifests present
- promotion eligibility false
- final-holdout enrollment blockers include retired MFE/MAE heads

## Baseline Comparison

| Direction | Family | Old MFE Estimator | New MFE Estimator | Old MAE Estimator | New MAE Estimator | Old Promo Eligible | New Promo Eligible |
|---|---|---|---|---|---|---|---|
| bull | logistic_regression | TweedieRegressor | RetiredPathHeadModel | TweedieRegressor | RetiredPathHeadModel | false | false |
| bear | logistic_regression | TweedieRegressor | RetiredPathHeadModel | TweedieRegressor | RetiredPathHeadModel | false | false |
| bull | extra_trees | ExtraTreesRegressor | ExtraTreesRegressor | ExtraTreesRegressor | ExtraTreesRegressor | false | false |
| bear | extra_trees | ExtraTreesRegressor | ExtraTreesRegressor | ExtraTreesRegressor | ExtraTreesRegressor | false | false |
| bull | hist_gradient_boosting | HistGradientBoostingRegressor | HistGradientBoostingRegressor | HistGradientBoostingRegressor | HistGradientBoostingRegressor | false | false |
| bear | hist_gradient_boosting | HistGradientBoostingRegressor | HistGradientBoostingRegressor | HistGradientBoostingRegressor | HistGradientBoostingRegressor | false | false |

## Failed Gates

All new models remain promotion-ineligible. Key blockers:

- all models: `final_holdout_required_for_promotion`
- logistic models: `mfe_required_path_head_active`, `mae_required_path_head_active`
- many selected-row-scarce models: expected-value, profit-factor, drawdown, concentration, and temporal-fold evidence gates
- nonlinear models: remaining OOD severity and selected-candidate quality gates
- naive controls: `not_naive_control`

## Review-Only Scanner

Ran:

`.venv/bin/python -m swing_rsi.cli scan --include-challengers`

Scan ID:

`4335c449dc0312d1280b5775`

As-of date:

`2026-06-18`

Rows: 50

Actionable rows: 0

Rejected rows: 50

Model states in scan: 50 CANDIDATE rows

Gate-eligible rows: 0

Retired MFE rows: 13

Retired MAE rows: 13

Rows with retired-head rejection reasons: 13

Top rejection patterns:

- 37 rows: `model_not_promoted`
- 13 rows: `model_not_promoted` plus retired MFE/MAE and nonfinite retired-head prediction reasons

## State Integrity

No model was promoted.

No forward-update or daily-cycle command was run.

No prospective final-holdout run was initialized.

Current SQLite state after verification:

- latest generation champions: 0
- final-holdout runs: 0
- forward events table still exists with prior events; this task did not run forward-update
- latest scanner snapshot: `4335c449dc0312d1280b5775`

## Audit Exports

Model audit export:

`reports/linear_path_head_retirement/`

Key files:

- `model_summary.csv`
- `full_gate_audit.csv`
- `feature_screen_audit.csv`
- `calibration_method_comparison.csv`
- `calibration_probability_audit.parquet`
- `calibration_governance.json`

These exports are ignored artifacts and were not committed.

## Assumptions

- Linear family means the repository's `logistic_regression` family.
- Retired required path heads should remain explicit artifact metadata, not missing metadata.
- Scanner non-actionability can be verified in review mode through rejected rows without creating paper-forward events.

## Known Limitations

- Retiring linear-family MFE/MAE heads does not improve nonlinear model quality.
- Logistic-family models remain useful only for historical audit/review because required path heads are unavailable.
- Current development holdout remains a development holdout, not final validation evidence.

## Data Leakage Review

No raw data, labels, feature definitions, thresholds, calibration methods, OOD governance, or research dates were changed.

No final-holdout data was created or used.

No forward-test outcomes were used.

The post-retirement discovery used existing local market data, existing feature panels, and existing labels.

## Scope Changes

No Version 1 scope expansion.

No options, intraday data, brokerage execution, reinforcement learning, or deep learning were added.

## Next Smallest Task

Perform a read-only diagnosis of the remaining nonlinear path-head OOD and selected-candidate gate failures in the post-retirement generation.
