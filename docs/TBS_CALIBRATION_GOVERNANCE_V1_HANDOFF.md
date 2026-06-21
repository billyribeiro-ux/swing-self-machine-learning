# Target-Before-Stop Calibration Governance V1 Handoff

Date: 2026-06-21

Baseline generation: `2026-06-21T19:28:21.433666+00:00`

Fresh generation: `2026-06-21T20:51:00.841677+00:00`

Holdout status: `DEVELOPMENT HOLDOUT DIAGNOSTIC`

## Confirmed Diagnosis

The target-specific feature-screening defect was already fixed before this milestone. The remaining Target-Before-Stop weakness was not treated as a software bug. The calibration diagnosis showed weak raw discrimination for several heads, sparse isotonic steps, large isotonic plateaus, occasional unsupported extremes, time/product-class instability, and no calibration-data proof that the frozen `0.50` decision threshold is optimal.

No implementation leakage or index-alignment defect was found in the old calibration path. The issue addressed here is governance: every Target-Before-Stop head now selects among precommitted calibration methods using chronological calibration data only.

## Architecture

Implemented reusable calibration governance in `src/swing_rsi/engine/calibration_governance.py`.

Supported candidates are exactly:

- `identity`: raw classifier positive-class probability unchanged.
- `sigmoid`: Platt/sigmoid probability calibration.
- `isotonic`: monotonic isotonic regression.

Each model family, direction, horizon, and Target-Before-Stop head gets its own independently selected and fitted calibrator. Calibrators are not shared across bull/bear, model families, horizons, or heads.

Schema version: `tbs_calibration_governance_v1`.

## Fold Design

Calibration method selection uses only the existing chronological calibration slice: `2022-05-13` through `2024-04-17`.

The selection process creates three deterministic forward-chaining internal folds where possible. For every fold, calibrator fit rows occur strictly before evaluation rows. Evaluation labels do not enter fitting, there is no shuffle, and development-holdout rows are not used. If fewer than two folds are evaluable for learned calibrators, identity is selected with `insufficient_calibration_folds_for_learned_calibrator`.

## One-Standard-Error Rule

Primary metric: mean chronological-fold Brier score.

Selection rule:

1. Find the candidate with the lowest mean fold Brier.
2. Compute `best_brier + one_standard_error`.
3. Keep all candidates within that boundary.
4. Select the simplest candidate from `identity < sigmoid < isotonic`.

Development-holdout metrics are diagnostics only and were not used for calibrator selection.

## Implementation Review

Focused review found no P1/P2 defects:

- No holdout labels feed calibration selection.
- Internal calibration folds are chronological.
- Future calibration segments do not affect earlier fold metrics.
- The one-standard-error rule is deterministic.
- Identity, sigmoid, and isotonic paths preserve finite `[0, 1]` probabilities.
- Scanner identity includes calibration schema, method, manifest hash, and calibrator hash.
- Missing governance metadata rejects new-schema rows with `target_before_stop_calibration_metadata_missing`.
- Legacy artifacts remain readable and review-only.

## Commits

- `6d2cd0e` - `feat: add target-before-stop calibration governance`
- `a946a0b` - `test: validate chronological calibrator selection`
- `a975f13` - `docs: document target-before-stop calibration governance`

No push was performed.

## Fresh Models

| Model ID | Direction | Family | Selected Calibrator | Selection Reason | TBS Calibration Manifest |
|---|---:|---|---|---|---|
| `9667744237fcebdd589a9c67` | bear | extra_trees | sigmoid | lowest_mean_chronological_fold_brier | `bd6a94bf81928967` |
| `8b7b96af23310d90768cbd53` | bear | hist_gradient_boosting | identity | one_standard_error_simplest_method | `650874d42176148b` |
| `e5c7ce8b917c30030801fb58` | bear | logistic_regression | sigmoid | lowest_mean_chronological_fold_brier | `012f2b9898cd12c5` |
| `c152bfa00503d94f86c74869` | bull | extra_trees | sigmoid | one_standard_error_simplest_method | `b3e0732c6a4b0fc5` |
| `14ca47d4c2760a6e3d8867c8` | bull | hist_gradient_boosting | identity | one_standard_error_simplest_method | `960b3a8998810405` |
| `34665ce3f2b9f593f8fcc6b4` | bull | logistic_regression | sigmoid | one_standard_error_simplest_method | `a4ae1f136d7f0e35` |

Naive controls were also generated and kept as controls: `779b253e4955f9fa93f4b9fb` bear, `1f3a62ae23d6897c1eaeab5a` bull.

## Method Comparison

| Model | Identity Brier | Sigmoid Brier | Isotonic Brier | 1SE Boundary |
|---|---:|---:|---:|---:|
| bear extra_trees | 0.222598 | 0.187326 | 0.188452 | 0.201953 |
| bear hist_gradient_boosting | 0.200275 | 0.191750 | 0.199700 | 0.203498 |
| bear logistic_regression | 0.219290 | 0.192386 | 0.214620 | 0.209731 |
| bull extra_trees | 0.226737 | 0.214216 | 0.211583 | 0.221147 |
| bull hist_gradient_boosting | 0.210923 | 0.211632 | 0.210526 | 0.219465 |
| bull logistic_regression | 0.293543 | 0.210224 | 0.209440 | 0.218478 |

## Selected Features By Family

Bull heads selected:

`breadth:2; inverse_leveraged:5; market_relative:4; regime:2; relationship_graph:23; rsi_family:5; sector_relative:1; technical_primitives:6; trend_structure:4; volatility_range:5; volume_participation:3`

Bear heads selected:

`breadth:3; inverse_leveraged:7; market_relative:5; regime:2; relationship_graph:20; rsi_family:3; sector_relative:1; technical_primitives:7; trend_structure:4; volatility_range:5; volume_participation:3`

The presence of these families confirms they were available under target-specific screening; it is not evidence of a trading edge.

## Development-Holdout Diagnostics

All metrics in this section are `DEVELOPMENT HOLDOUT DIAGNOSTIC`, not final out-of-sample proof.

| Model | Raw Brier | Cal Brier | Raw ROC | Cal ROC | Raw PR | Cal PR | Cal ECE | Cal >= 0.50 | Selected Rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bear extra_trees | 0.215160 | 0.194774 | 0.5873 | 0.4127 | 0.3169 | 0.2126 | 0.0636 | 0 | 0 |
| bear hist_gradient_boosting | 0.191728 | 0.191728 | 0.6276 | 0.6276 | 0.3514 | 0.3514 | 0.0645 | 2100 | 48 |
| bear logistic_regression | 0.239806 | 0.191843 | 0.4896 | 0.4896 | 0.2614 | 0.2614 | 0.0208 | 0 | 0 |
| bull extra_trees | 0.224726 | 0.207279 | 0.5302 | 0.4698 | 0.3215 | 0.2711 | 0.0221 | 0 | 0 |
| bull hist_gradient_boosting | 0.212650 | 0.212650 | 0.5224 | 0.5224 | 0.3082 | 0.3082 | 0.0613 | 488 | 204 |
| bull logistic_regression | 0.263115 | 0.206107 | 0.5427 | 0.5427 | 0.3176 | 0.3176 | 0.0092 | 0 | 0 |

## Plateau And Step-Support Comparison

| Match | Old Method | New Method | Old Plateau | New Plateau | Old Unique Outputs | New Unique Outputs |
|---|---|---|---:|---:|---:|---:|
| bear/extra_trees/10 | isotonic_legacy | sigmoid | 0.988 | 0.000 | 12 | 17069 |
| bear/hist_gradient_boosting/10 | isotonic_legacy | identity | 0.503 | 0.000 | 16 | 16720 |
| bear/logistic_regression/10 | isotonic_legacy | sigmoid | 0.406 | 0.000 | 126 | 17069 |
| bull/extra_trees/10 | isotonic_legacy | sigmoid | 0.526 | 0.000 | 14 | 17069 |
| bull/hist_gradient_boosting/10 | isotonic_legacy | identity | 0.240 | 0.000 | 36 | 16823 |
| bull/logistic_regression/10 | isotonic_legacy | sigmoid | 0.593 | 0.000 | 43 | 17069 |

Isotonic support diagnostics were exported to `reports/tbs_calibration_governance_v1/isotonic_step_support.csv`. The selected calibrators removed the large selected-probability plateaus in this generation, but this is not a claim of improved trading performance.

## Baseline Versus New

| Match | Old -> New Calibrator | Brier | Log Loss | ROC-AUC | PR-AUC | ECE | >= 0.50 | Selected |
|---|---|---|---|---|---|---|---|---|
| bear/extra_trees/10 | isotonic_legacy -> sigmoid | 0.191511 -> 0.194774 | 0.572973 -> 0.579547 | 0.5039 -> 0.4127 | 0.2610 -> 0.2126 | 0.0408 -> 0.0636 | 30 -> 0 | 7 -> 0 |
| bear/hist_gradient_boosting/10 | isotonic_legacy -> identity | 0.190967 -> 0.191728 | 0.578685 -> 0.568041 | 0.5968 -> 0.6276 | 0.3067 -> 0.3514 | 0.0708 -> 0.0645 | 0 -> 2100 | 0 -> 48 |
| bear/logistic_regression/10 | isotonic_legacy -> sigmoid | 0.200953 -> 0.191843 | 0.927017 -> 0.571894 | 0.4919 -> 0.4896 | 0.2581 -> 0.2614 | 0.0742 -> 0.0208 | 335 -> 0 | 68 -> 0 |
| bull/extra_trees/10 | isotonic_legacy -> sigmoid | 0.207359 -> 0.207279 | 0.605211 -> 0.605141 | 0.5240 -> 0.4698 | 0.3043 -> 0.2711 | 0.0306 -> 0.0221 | 80 -> 0 | 20 -> 0 |
| bull/hist_gradient_boosting/10 | isotonic_legacy -> identity | 0.206864 -> 0.212650 | 0.604018 -> 0.616491 | 0.5223 -> 0.5224 | 0.3042 -> 0.3082 | 0.0200 -> 0.0613 | 67 -> 488 | 17 -> 204 |
| bull/logistic_regression/10 | isotonic_legacy -> sigmoid | 0.206018 -> 0.206107 | 0.601692 -> 0.602242 | 0.5371 -> 0.5427 | 0.3106 -> 0.3176 | 0.0192 -> 0.0092 | 0 -> 0 | 0 -> 0 |

No improvement claim is made from these development-holdout diagnostics.

## Failed Gates

No fresh model is promotion eligible.

| Model | Failed Mandatory Gates |
|---|---|
| bear extra_trees | `positive_expected_value_after_costs; profit_factor_min_090; portfolio_drawdown_available; portfolio_drawdown_not_worse_than_50pct; transaction_cost_sensitivity_not_collapsed; temporal_fold_stability_evidence_available; return_holdout_ood_q99_severity_acceptable; mfe_holdout_ood_q99_severity_acceptable` |
| bear hist_gradient_boosting | `exceptional_period_concentration_max_060; return_holdout_ood_q99_severity_acceptable; mfe_holdout_ood_q99_severity_acceptable; mfe_catastrophic_prediction_extrapolation_absent; mae_holdout_ood_q99_severity_acceptable` |
| bear logistic_regression | `positive_expected_value_after_costs; profit_factor_min_090; portfolio_drawdown_available; portfolio_drawdown_not_worse_than_50pct; transaction_cost_sensitivity_not_collapsed; temporal_fold_stability_evidence_available; return_holdout_ood_q99_severity_acceptable; mfe_prediction_path_metric_sign_valid; mfe_holdout_ood_q99_severity_acceptable; mfe_catastrophic_prediction_extrapolation_absent; mae_holdout_ood_q99_severity_acceptable; mae_catastrophic_prediction_extrapolation_absent` |
| bull extra_trees | `positive_expected_value_after_costs; profit_factor_min_090; portfolio_drawdown_available; portfolio_drawdown_not_worse_than_50pct; transaction_cost_sensitivity_not_collapsed; temporal_fold_stability_evidence_available; mae_holdout_ood_q99_severity_acceptable` |
| bull hist_gradient_boosting | `positive_expected_value_after_costs; transaction_cost_sensitivity_not_collapsed; temporal_fold_stability_min_050; mfe_holdout_ood_q99_severity_acceptable; mae_holdout_ood_q99_severity_acceptable` |
| bull logistic_regression | `positive_expected_value_after_costs; profit_factor_min_090; portfolio_drawdown_available; portfolio_drawdown_not_worse_than_50pct; transaction_cost_sensitivity_not_collapsed; temporal_fold_stability_evidence_available; mfe_holdout_ood_q99_severity_acceptable; mfe_catastrophic_prediction_extrapolation_absent; mae_holdout_ood_q99_severity_acceptable; mae_catastrophic_prediction_extrapolation_absent` |

## Scanner Review

Gate-integrity contradictions: `0`.

Command run: `.venv/bin/python -m swing_rsi.cli scan --include-challengers`

Scan ID: `06553acc8d4ddd1e688006e5`

Generation used: `2026-06-21T20:51:00.841677+00:00`

Rows: `50`

Bullish rows: `25`

Bearish rows: `25`

Actionable rows: `0`

Rejected rows: `50`

OOD-warning rows: `4`

Rejection reasons: `model_not_promoted` for all 50 rows.

Target-before-stop calibration metadata missing rejections: `0`.

No gate-ineligible model became actionable.

## Tests And Checks

Pre-retrain:

- `.venv/bin/pytest` - `191 passed, 166 warnings`
- `.venv/bin/ruff check .` - passed
- `.venv/bin/ruff format --check .` - passed
- `.venv/bin/mypy src` - passed

Post-audit/scanner:

- `.venv/bin/pytest` - `191 passed, 166 warnings`
- `.venv/bin/ruff check .` - passed
- `.venv/bin/ruff format --check .` - passed
- `.venv/bin/mypy src` - passed

No FMP update, forward-update, daily-cycle, model promotion, or threshold change was performed. No `.env` contents were opened or printed.

## Remaining Blockers

- The current holdout is a development holdout, not pristine final validation.
- Every fresh model failed mandatory promotion gates.
- Several heads still show weak or unstable Target-Before-Stop discrimination.
- The frozen `0.50` policy threshold was not changed and is not justified by this milestone.
- Scanner output remained review-only because all models are candidates.

## Next Smallest Engineering Task

Add an explicit promotion guard that blocks promotion whenever a model's holdout status is not `FINAL_HOLDOUT`.
