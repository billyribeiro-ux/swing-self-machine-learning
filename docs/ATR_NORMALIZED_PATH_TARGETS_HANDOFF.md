# ATR-Normalized Path Targets V1 Handoff

Date: 2026-06-24

Baseline generation: `2026-06-24T12:38:43.122103+00:00`

Post-implementation generation: `2026-06-24T15:38:06.427124+00:00`

Implementation commit: `5d5217c` (`feat: add ATR-normalized path targets`)

## Confirmed Correction

The correction addresses raw-percentage path-target heterogeneity across ordinary stocks, ETFs, leveraged ETFs, inverse ETFs, regimes, and years.

Historical labels remain canonical and unchanged:

- Expected return remains signed directional decimal return.
- MFE remains favorable decimal return and must be `>= 0`.
- MAE remains adverse decimal return and must be `<= 0`.

New internal training targets use close-known signal-date `atr_pct_14`:

- Expected return: `label_{direction}_forward_return_{horizon} / atr_pct_14`
- MFE: `label_{direction}_mfe_{horizon} / atr_pct_14`
- MAE: `-label_{direction}_mae_{horizon} / atr_pct_14`

Predictions are mapped back to canonical decimal returns before scanner output, selection policy, attribution, portfolio backtesting, and paper-forward handling.

## Architecture

Schema: `atr_normalized_path_targets_v1`

Prediction mapping: `atr_units_to_decimal_return_v1`

ATR source: close-known `atr_pct_14` from the signal row.

Active path heads train in normalized model space. Canonical outputs are still persisted and validated separately:

- Expected-return active heads train on signed ATR units, then multiply predictions by signal-date ATR.
- MFE active heads train on favorable magnitude ATR units, then multiply by signal-date ATR.
- MAE active heads train on adverse magnitude ATR units, multiply by signal-date ATR, then map back to negative signed MAE.
- Logistic-family MFE and MAE heads remain `RETIRED_UNSUITABLE_ESTIMATOR`.

OOD Governance V2 remains in place. New path OOD gates evaluate active heads in normalized model space, while canonical decimal output still receives sign/domain integrity validation.

## Implementation Review

Focused review checked:

- target normalization uses only signal-row `atr_pct_14`;
- labels are not rewritten;
- no target/stop, threshold, gate, family, calibration, or OOD weakening was introduced;
- logistic MFE/MAE retirement remains active;
- active path heads do not reuse canonical raw-percent targets;
- scanner converts normalized predictions back to canonical decimal returns before policy use;
- MAE OOD uses normalized adverse magnitude model space, not signed canonical MAE bounds;
- no post-hoc clipping was introduced;
- scanner identity includes normalization schema/hash/ATR feature.

Result: no P1/P2 defects found.

## New Generation

Discovery command run exactly once after verification:

```bash
.venv/bin/python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80
```

Result:

- Models registered: 8
- Challengers: 0
- Candidates needing review: 8
- Promoted models: 0
- Best failed-gate candidate retained: `669b7774ce536cffd60a78d7`

Model IDs:

| Direction | Family | Model ID | Selected rows | Failed mandatory gates | Promotion eligible |
|---|---|---:|---:|---:|---|
| Bull | Logistic Regression | `483852b90d8d1dae4e8bb8ad` | 0 | 19 | No |
| Bear | Logistic Regression | `039f90f41a439884b6ff2b25` | 0 | 21 | No |
| Bull | ExtraTrees | `60283a5137cc99cdb93c7270` | 0 | 7 | No |
| Bear | ExtraTrees | `b3d065c851dd3229241db1a9` | 0 | 7 | No |
| Bull | HistGradientBoosting | `9ffff76316aca00cdfe2e7ec` | 39 | 1 | No |
| Bear | HistGradientBoosting | `eac4afd35a416b1a20d4c6ae` | 54 | 3 | No |
| Bull | Naive base-rate | `669b7774ce536cffd60a78d7` | 0 | 2 | No |
| Bear | Naive base-rate | `b36ec2b93ce78e4850675e93` | 0 | 4 | No |

## Normalized-Target Audit

Audit command:

```bash
.venv/bin/python -m swing_rsi.cli model-audit --generation latest --export-dir reports/atr_normalized_path_targets_v1
```

Every new model summary contains `atr_normalized_path_targets_v1` path metadata and `atr_pct_14` as the ATR feature.

Path target hashes:

| Direction | Expected return hash | MFE hash | MAE hash |
|---|---:|---:|---:|
| Bull | `898e2bc6f77dfb3a` | `8a54fb3ca7e15ab6` | `ab9b1857d67bbfba` |
| Bear | `033fa5d40724464c` | `6768cca8470b4c1b` | `9d3fb961d8afd6d0` |

Active nonlinear path heads:

| Direction | Family | Expected-return OOD rate | MFE OOD rate | MAE OOD rate | MFE sign violations | MAE sign violations |
|---|---|---:|---:|---:|---:|---:|
| Bull | ExtraTrees | 0.000000 | 0.000000 | 0.000000 | 0 | 0 |
| Bear | ExtraTrees | 0.000000 | 0.000000 | 0.000000 | 0 | 0 |
| Bull | HistGradientBoosting | 0.000000 | 0.000000 | 0.000059 | 0 | 0 |
| Bear | HistGradientBoosting | 0.000000 | 0.000000 | 0.000000 | 0 | 0 |

Logistic path retirement remained intact:

- Bull logistic MFE/MAE: `RETIRED_UNSUITABLE_ESTIMATOR`
- Bear logistic MFE/MAE: `RETIRED_UNSUITABLE_ESTIMATOR`
- No logistic MFE/MAE path head became promotion eligible.

## Feature Screens

Path screens use ATR-normalized target names:

- Bull expected return: `label_bull_forward_return_10__atr_units_atr_pct_14`
- Bear expected return: `label_bear_forward_return_10__atr_units_atr_pct_14`
- Bull MFE: `label_bull_mfe_10__favorable_magnitude_atr_units_atr_pct_14`
- Bear MFE: `label_bear_mfe_10__favorable_magnitude_atr_units_atr_pct_14`
- Bull MAE: `label_bull_mae_10__adverse_magnitude_atr_units_atr_pct_14`
- Bear MAE: `label_bear_mae_10__adverse_magnitude_atr_units_atr_pct_14`

Selected feature families include market-relative, sector-relative, inverse/leveraged, breadth, relationship graph, regime, volatility/range, volume participation, trend structure, returns/momentum, and RSI families. No family quota was introduced.

## Baseline Comparison

Baseline audit command:

```bash
.venv/bin/python -m swing_rsi.cli model-audit --generation 2026-06-24T12:38:43.122103+00:00 --export-dir reports/atr_normalized_path_targets_v1_baseline
```

| Direction | Family | Old model | New model | Old path normalization | New path normalization | Old selected | New selected | Old failed gates | New failed gates | Old/New promotion |
|---|---|---:|---:|---|---|---:|---:|---:|---:|---|
| Bull | ExtraTrees | `0ddd122a586fb6c797357ad5` | `60283a5137cc99cdb93c7270` | none | `atr_normalized_path_targets_v1` | 0 | 0 | 8 | 7 | No / No |
| Bear | ExtraTrees | `722fb3fda82754b5bd572e4c` | `b3d065c851dd3229241db1a9` | none | `atr_normalized_path_targets_v1` | 0 | 0 | 9 | 7 | No / No |
| Bull | HistGradientBoosting | `d32c5d3e44372e91342e39d8` | `9ffff76316aca00cdfe2e7ec` | none | `atr_normalized_path_targets_v1` | 190 | 39 | 6 | 1 | No / No |
| Bear | HistGradientBoosting | `b2f4d14b22d11d5875700fee` | `eac4afd35a416b1a20d4c6ae` | none | `atr_normalized_path_targets_v1` | 42 | 54 | 5 | 3 | No / No |
| Bull | Logistic Regression | `6368d67eaaa721101de5ceb4` | `483852b90d8d1dae4e8bb8ad` | none | `atr_normalized_path_targets_v1` | 0 | 0 | 18 | 19 | No / No |
| Bear | Logistic Regression | `49f255fd5496f5d7881499e6` | `039f90f41a439884b6ff2b25` | none | `atr_normalized_path_targets_v1` | 0 | 0 | 18 | 21 | No / No |

Implementation success is based on correct normalized-target training, frozen metadata, canonical mapping, OOD/sign integrity, and scanner integration. It is not a claim of trading edge.

## Failed Gates

Primary remaining learned-model blockers:

- Logistic models: expected-return OOD plus retired required MFE/MAE heads, no selected-evidence portfolio metrics, and final-holdout requirement.
- ExtraTrees models: no selected rows, missing selected-evidence portfolio metrics, temporal-fold evidence unavailable, and final-holdout requirement.
- Bull HistGradientBoosting: final-holdout requirement only.
- Bear HistGradientBoosting: final-holdout requirement, temporal-fold stability below threshold, and exceptional-period concentration above threshold.

No model was promoted.

## Scanner Review

Scanner command:

```bash
.venv/bin/python -m swing_rsi.cli scan --include-challengers
```

Result:

- Scan ID: `f0cb07148bc8b8e6ced4249d`
- As-of date: `2026-06-18`
- Rows: 50
- Actionable rows: 0
- Rejected rows: 50
- OOD-warning rows: 0

Rejection reasons:

| Reason | Rows |
|---|---:|
| `model_not_promoted` | 37 |
| `model_not_promoted;mfe_linear_family_path_head_retired_unsuitable_estimator;mfe_magnitude_prediction_invalid;mfe_prediction_sign_contract_failed;mae_linear_family_path_head_retired_unsuitable_estimator;mae_magnitude_prediction_invalid;mae_prediction_sign_contract_failed;nonfinite_prediction` | 13 |

The scanner output includes normalized internal ATR-unit fields and canonical decimal output fields. Gate-ineligible models remained non-actionable.

## Verification

Pre-discovery verification:

- `.venv/bin/pytest` passed: 272 tests, 166 warnings.
- `.venv/bin/ruff check .` passed.
- `.venv/bin/ruff format --check .` passed.
- `.venv/bin/mypy src` passed.

Final verification after discovery, audit, and scanner:

- `.venv/bin/pytest` passed: 272 tests, 166 warnings.
- `.venv/bin/ruff check .` passed.
- `.venv/bin/ruff format --check .` passed.
- `.venv/bin/mypy src` passed.

No FMP update was run. No forward-update or daily-cycle was run. No model was promoted. No final-holdout run was initialized. Generated reports, model artifacts, SQLite state, and scanner artifacts remain outside the implementation commit.

## Next Task

Exactly one smallest next engineering task: fix scanner handling of retired required path heads so retired logistic MFE/MAE heads produce a single explicit retirement rejection without also surfacing generic `nonfinite_prediction` or sign-contract rejection noise.
