# Prediction OOD Governance V2 Handoff

## Governance Decision

Implemented governance schema `prediction_ood_governance_v2`.

The old mandatory `prediction_out_of_distribution_absent` rule is deprecated for new artifacts. It is retained only as legacy metadata and is not used for new promotion decisions. Legacy artifacts that lack V2 canonical OOD gates remain readable but are promotion-ineligible.

The `q01` / `q99` training target envelope is now a reference envelope, not an absolute mathematical domain. Raw predictions are never clipped or replaced.

For each regression head, direction, horizon, and model:

```text
L = training target q01
U = training target q99
R = max(U - L, epsilon)

low_overshoot = max(0, L - prediction) / R
high_overshoot = max(0, prediction - U) / R
ood_severity = max(low_overshoot, high_overshoot)
is_ood = ood_severity > 0
```

Calibration-derived OOD rate limit:

```text
z = 2.326347874
rate_limit = min(0.05, max(0.02, wilson_upper_99(k_calibration_ood, n_calibration) + 0.005))
```

Calibration-derived severity limit:

```text
calibration_q99_severity = 0 when calibration has no nonzero OOD severities
calibration_q99_severity = q99 of nonzero calibration OOD severities otherwise
severity_q99_limit = min(0.50, max(0.10, calibration_q99_severity + 0.05))
```

Zero-tolerance integrity gates now cover nonfinite predictions, probability values outside `[0, 1]`, decimal/percent unit misuse, wrong head-to-bound mapping, non-training OOD bounds, double inverse transformation, MFE predictions below zero, and MAE predictions above zero.

## Code Review Result

Focused implementation review found no P1/P2 defect after the V2 patch. Checked leakage boundaries, Wilson formula, head/direction/horizon bound mapping, percentage conversion, hidden clipping, scanner identity metadata, and legacy artifact promotion blocking.

One audit-evidence cleanup was made before commit: per-head finite prediction gates now report the combined calibration-plus-holdout nonfinite count.

## Implementation Summary

- Added `src/swing_rsi/engine/ood.py` for Wilson limits, per-head OOD metrics, severity calculations, probability contracts, live OOD checks, and scanner identity metadata.
- Replaced new model artifact OOD promotion logic with V2 canonical gate rows.
- Kept old zero-rule metadata as `legacy_prediction_out_of_distribution_absent_deprecated`, nonmandatory and `NOT_APPLICABLE`.
- Added calibration predictions for expected return, expected MFE, and expected MAE so rate/severity limits are frozen before holdout evaluation.
- Added scanner rejection for missing OOD metadata, nonfinite predictions, probability contract failure, path-metric sign failure, severity above frozen limit, and catastrophic severity above `1.00`.
- Added scanner OOD warnings for permitted q01/q99 exceedances.
- Bumped scanner identity schema to `3` and added model OOD governance metadata/hash to cache identity.
- Extended model-audit exports and dashboard surfaces with V2 fields.

## Fresh Generation

Command:

```bash
.venv/bin/python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80
```

Result:

- Generation ID: `2026-06-21T04:34:49.525939+00:00`
- Models registered: 8
- Challengers: 0
- Candidates: 8
- Rejected/experimental: 0
- No model was promoted.
- Discovery emitted NumPy/Pandas invalid-value runtime warnings but exited with status 0.

Research and split dates:

- Research start: `2016-06-20`
- Research end: `2026-06-18`
- Train: `2016-06-20` to `2022-04-28`
- Calibration: `2022-05-13` to `2024-04-17`
- Holdout: `2024-05-02` to `2026-04-22`
- Samples per model: train `41,884`, calibration `16,800`, holdout `17,069`

Model IDs:

- `01a260bc4a63c41eada979ae` bull HistGradientBoosting
- `3d0b95ffea9724494114e6c4` bear naive base rate
- `5160add45d1b068f7f161aa7` bear ExtraTrees
- `8cafce9ea237b314c665ab7d` bull naive base rate
- `8fc3f715fad2d7abff9a8e32` bear HistGradientBoosting
- `970e03fddb196603a22d4a24` bear logistic regression
- `cc3b395baf3f6e06451ccdee` bull logistic regression
- `eec38153992ba94ed6aa6308` bull ExtraTrees

## Model Summary

```text
model_id                  dir   family                  selected  sel_rate   BSS       port_DD    failed  eligible
01a260bc4a63c41eada979ae  bull  hist_gradient_boosting  5         0.000293   0.007300  -0.015685  7       no
3d0b95ffea9724494114e6c4  bear  naive_base_rate         0         0.000000   0.000000  n/a        7       no
5160add45d1b068f7f161aa7  bear  extra_trees             6         0.000352   0.019367  -0.010237  6       no
8cafce9ea237b314c665ab7d  bull  naive_base_rate         0         0.000000   0.000000  n/a        5       no
8fc3f715fad2d7abff9a8e32  bear  hist_gradient_boosting  0         0.000000   0.004954  n/a        9       no
970e03fddb196603a22d4a24  bear  logistic_regression     0         0.000000   0.023860  n/a        11      no
cc3b395baf3f6e06451ccdee  bull  logistic_regression     0         0.000000   0.024079  n/a        9       no
eec38153992ba94ed6aa6308  bull  extra_trees             0         0.000000   0.019994  n/a        6       no
```

## Old Versus V2 OOD Results

The old zero-exceedance rule would fail every model because every model has at least one holdout q01/q99 exceedance:

```text
model_id                  old_zero_rule_ood_total  return  mfe  mae
01a260bc4a63c41eada979ae  13                       1       4    8
3d0b95ffea9724494114e6c4  120                      1       111  8
5160add45d1b068f7f161aa7  39                       14      25   0
8cafce9ea237b314c665ab7d  26                       0       9    17
8fc3f715fad2d7abff9a8e32  55                       27      26   2
970e03fddb196603a22d4a24  120                      1       111  8
cc3b395baf3f6e06451ccdee  26                       0       9    17
eec38153992ba94ed6aa6308  3                        0       0    3
```

Under V2, all classification probability, unit, finite-value, head mapping, training-only bounds, and OOD-rate gates passed. Promotion is still blocked by severity/catastrophic gates and other model-quality gates.

## Per-Head OOD Tables

Return head:

```text
model_id                  cal_rate  rate_limit  holdout_count  holdout_rate  sev_limit  holdout_q99  max_sev
01a260bc4a63c41eada979ae  0.000000  0.020000    1              0.000059      0.100000   0.005571     0.005571
3d0b95ffea9724494114e6c4  0.000000  0.020000    1              0.000059      0.100000   0.463355     0.463355
5160add45d1b068f7f161aa7  0.000119  0.020000    14             0.000820      0.100000   0.356301     0.380558
8cafce9ea237b314c665ab7d  0.000000  0.020000    0              0.000000      0.100000   0.000000     0.000000
8fc3f715fad2d7abff9a8e32  0.000119  0.020000    27             0.001582      0.179427   0.728576     0.805134
970e03fddb196603a22d4a24  0.000000  0.020000    1              0.000059      0.100000   0.463355     0.463355
cc3b395baf3f6e06451ccdee  0.000000  0.020000    0              0.000000      0.100000   0.000000     0.000000
eec38153992ba94ed6aa6308  0.000000  0.020000    0              0.000000      0.100000   0.000000     0.000000
```

MFE head:

```text
model_id                  cal_rate  rate_limit  holdout_count  holdout_rate  sev_limit  holdout_q99  max_sev
01a260bc4a63c41eada979ae  0.000238  0.020000    4              0.000234      0.173052   0.413912     0.420222
3d0b95ffea9724494114e6c4  0.002381  0.020000    111            0.006503      0.148746   0.807337     2.899998
5160add45d1b068f7f161aa7  0.000595  0.020000    25             0.001465      0.320470   0.897732     0.935572
8cafce9ea237b314c665ab7d  0.000000  0.020000    9              0.000527      0.100000   1.535420     1.634114
8fc3f715fad2d7abff9a8e32  0.001250  0.020000    26             0.001523      0.500000   2.466503     2.605459
970e03fddb196603a22d4a24  0.002381  0.020000    111            0.006503      0.148746   0.807337     2.899998
cc3b395baf3f6e06451ccdee  0.000000  0.020000    9              0.000527      0.100000   1.535420     1.634114
eec38153992ba94ed6aa6308  0.000000  0.020000    0              0.000000      0.100000   0.000000     0.000000
```

MAE head:

```text
model_id                  cal_rate  rate_limit  holdout_count  holdout_rate  sev_limit  holdout_q99  max_sev
01a260bc4a63c41eada979ae  0.000060  0.020000    8              0.000469      0.133584   0.164274     0.168750
3d0b95ffea9724494114e6c4  0.000000  0.020000    8              0.000469      0.100000   1.488203     1.573494
5160add45d1b068f7f161aa7  0.000000  0.020000    0              0.000000      0.100000   0.000000     0.000000
8cafce9ea237b314c665ab7d  0.000060  0.020000    17             0.000996      0.100000   2.113966     2.407967
8fc3f715fad2d7abff9a8e32  0.000000  0.020000    2              0.000117      0.100000   0.161885     0.163038
970e03fddb196603a22d4a24  0.000000  0.020000    8              0.000469      0.100000   1.488203     1.573494
cc3b395baf3f6e06451ccdee  0.000060  0.020000    17             0.000996      0.100000   2.113966     2.407967
eec38153992ba94ed6aa6308  0.000000  0.020000    3              0.000176      0.100000   0.136001     0.138650
```

## Integrity Gate Results

Across all 8 models:

- `prediction_ood_governance_schema_version`: 8 PASS
- Classification finite, probability contract, and unit contract: 8 PASS each
- Regression finite values: 8 PASS for return, MFE, and MAE
- Regression unit contracts: 8 PASS for return, MFE, and MAE
- Head-to-bound mapping: 8 PASS for return, MFE, and MAE
- Training-only bounds: 8 PASS for return, MFE, and MAE
- OOD rate gates: 8 PASS for return, MFE, and MAE
- Return catastrophic-extrapolation gate: 8 PASS
- MFE sign contract: 6 PASS, 2 FAIL
- MAE sign contract: 8 PASS
- Return q99 severity gate: 4 PASS, 4 FAIL
- MFE q99 severity gate: 1 PASS, 7 FAIL
- MFE catastrophic-extrapolation gate: 3 PASS, 5 FAIL
- MAE q99 severity gate: 1 PASS, 7 FAIL
- MAE catastrophic-extrapolation gate: 4 PASS, 4 FAIL

## Other Failed Mandatory Gates

- `01a260bc4a63c41eada979ae`: positive EV after costs, symbol concentration, sector concentration, transaction-cost sensitivity, exceptional-period concentration, MFE q99 severity, MAE q99 severity.
- `3d0b95ffea9724494114e6c4`: naive control, return q99 severity, MFE sign, MFE q99 severity, MFE catastrophic extrapolation, MAE q99 severity, MAE catastrophic extrapolation.
- `5160add45d1b068f7f161aa7`: profit factor, symbol concentration, sector concentration, exceptional-period concentration, return q99 severity, MFE q99 severity.
- `8cafce9ea237b314c665ab7d`: naive control, MFE q99 severity, MFE catastrophic extrapolation, MAE q99 severity, MAE catastrophic extrapolation.
- `8fc3f715fad2d7abff9a8e32`: positive EV after costs, profit factor, missing portfolio drawdown, portfolio drawdown limit, transaction-cost sensitivity, return q99 severity, MFE q99 severity, MFE catastrophic extrapolation, MAE q99 severity.
- `970e03fddb196603a22d4a24`: positive EV after costs, profit factor, missing portfolio drawdown, portfolio drawdown limit, transaction-cost sensitivity, return q99 severity, MFE sign, MFE q99 severity, MFE catastrophic extrapolation, MAE q99 severity, MAE catastrophic extrapolation.
- `cc3b395baf3f6e06451ccdee`: positive EV after costs, profit factor, missing portfolio drawdown, portfolio drawdown limit, transaction-cost sensitivity, MFE q99 severity, MFE catastrophic extrapolation, MAE q99 severity, MAE catastrophic extrapolation.
- `eec38153992ba94ed6aa6308`: positive EV after costs, profit factor, missing portfolio drawdown, portfolio drawdown limit, transaction-cost sensitivity, MAE q99 severity.

## Promotion Eligibility

All 8 latest-generation models are `CANDIDATE`, promotion eligible: `no`.

No model was promoted. No champion or paper-forward deployment was changed.

## Scanner Results

Command:

```bash
.venv/bin/python -m swing_rsi.cli scan --include-challengers
```

Result:

- Scan ID: `6e4ce9ccada34a0962d2bc20`
- As-of date: `2026-06-18`
- Generation used: `2026-06-21T04:34:49.525939+00:00`
- Rows: 50
- Bullish rows: 25
- Bearish rows: 25
- Actionable rows: 0
- Rejected rows: 50
- Rejection reasons: `model_not_promoted` for all rows
- OOD-warning rows: 4
- OOD-rejected rows: 0
- Affected live heads: `mfe` on 4 rows
- Maximum live OOD severity: `0.140610`
- CSV: `artifacts/scanner/6e4ce9ccada34a0962d2bc20_scanner.csv`
- Parquet: `artifacts/scanner/6e4ce9ccada34a0962d2bc20_scanner.parquet`

The review-only scanner preserved OOD warnings for permitted live q01/q99 exceedances. Gate-ineligible candidate models remained non-actionable.

## Audit Exports

Generated under ignored `reports/ood_governance_v2/`:

- `model_summary.csv`
- `full_gate_audit.csv`
- `full_gate_audit.json`
- `calibration_table.csv`
- `portfolio_daily_equity.csv`
- `selected_candidate_ledger.csv`
- `portfolio_trade_ledger.csv`

## Verification

Final commands:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

Results:

- Pytest: 125 collected, 125 passed, 0 failed, 0 skipped, 161 warnings, 57.20s.
- Ruff check: passed.
- Ruff format check: 92 files already formatted.
- Mypy: success, 54 source files checked.

Focused pre-retrain tests:

- `tests/test_model_evaluation_integrity.py tests/test_autonomous_engine.py -q`: 56 passed, 161 warnings.

Automated tests did not call FMP.

## Commits

- `82ed1b3` docs: define calibrated prediction OOD governance
- `7d4950a` feat: implement calibrated prediction OOD gates
- `cfdc04e` test: validate prediction OOD governance
- final documentation commit to be recorded after this handoff is committed

## Remaining Blocker

No model is promotion eligible. The current blockers are not the deprecated zero-exceedance rule; they are persisted canonical failures including OOD severity/catastrophic extrapolation, MFE sign contract failures for two bearish models, missing portfolio drawdown where no holdout selections existed, selected-candidate quality, concentration, and cost-sensitivity gates.

## Smallest Next Task

Audit the V2 path-metric regression heads that fail severity or sign gates, especially bearish MFE and MAE heads, by tracing the trained regression predictions against their matching stored label distributions and model family behavior. Acceptance criteria: prove whether the failures are model extrapolation, label-distribution tails, or model-family calibration weakness; do not add new model families, weaken gates, or promote anything.
