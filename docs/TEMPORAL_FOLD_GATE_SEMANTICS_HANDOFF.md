# Temporal Fold Gate Semantics Handoff

## Confirmed Defect

The fresh generation `2026-06-21T17:09:51.735316+00:00` contained six `temporal_fold_stability_min_050` rows with `actual = NOT_AVAILABLE`, comparator `>=`, threshold `0.50`, status `PASS`, and pass-sounding reason text. This allowed unavailable temporal-fold evidence to appear successful.

## Root Cause

The old single temporal-fold threshold gate evaluated `not math.isfinite(temporal_fraction) or temporal_fraction >= 0.50`, so `NaN`/unavailable fold evidence became `PASS`. There was no separate persisted evidence-availability gate to block learned models when fold evidence could not be computed.

## Old Behavior

- `_temporal_fold_stability` requested 3 chronological folds and returned `NaN` when selected rows were empty or fewer than 3.
- `_build_gate_results` treated that nonfinite metric as a passing mandatory threshold gate.
- The persisted reason said temporal stability passed or was not applicable, even for mandatory learned-model gates with no valid evidence.

## Corrected Two-Gate Semantics

| Scenario | Evidence gate | Threshold gate | Promotion effect |
| --- | --- | --- | --- |
| Learned model, valid finite fold evidence | PASS | PASS/FAIL from `actual >= 0.50` | Threshold result controls eligibility |
| Learned model, zero/insufficient selected rows | FAIL | NOT_APPLICABLE | Blocked by evidence gate |
| Learned model, missing/NaN/infinite metric | FAIL | NOT_APPLICABLE | Blocked by evidence gate |
| Naive control | NOT_APPLICABLE | NOT_APPLICABLE | Blocked by `not_naive_control` |

## Fold Evidence Definition

- Temporal fold schema: `temporal_fold_stability_v1`.
- Chronological folds requested: 3.
- Fold construction: selected holdout rows are sorted by signal date and partitioned with the existing `np.array_split` chronological layout.
- Existing sufficiency requirement made explicit: all 3 requested folds must contain selected observations and the fold positive fraction must be finite.
- Metric definition: `temporal_fold_positive_fraction = count(fold_mean_return > 0) / folds_evaluated`.
- Persisted evidence details: folds requested/evaluated/with selected observations, selected observations per fold, fold-level selected count, mean return, positive/negative result, evidence status, unavailable reason, threshold, and both temporal gate statuses.

## Tests

- Added temporal-fold tests for valid 0.75, exact 0.50, below-threshold 0.49, zero selected rows, insufficient rows, missing/NaN/infinite metrics, naive controls, status-aware reasons, dashboard display, CSV/JSON export states, promotion eligibility, scanner eligibility, legacy inconsistent rows, and no regression of positive-infinity profit factor.
- Automated tests make no FMP calls.

## Pre-Retrain Verification And Review

- `.venv/bin/pytest`: 155 collected, 155 passed, 0 failed, 0 skipped, 161 warnings.
- `.venv/bin/ruff check .`: PASS, `All checks passed!`.
- `.venv/bin/ruff format --check .`: PASS, `92 files already formatted`.
- `.venv/bin/mypy src`: PASS, `Success: no issues found in 54 source files`.
- Focused review result: clean; no P1 or P2 finding was found for unavailable evidence bypassing mandatory gates, NOT_APPLICABLE satisfying promotion, status/reason contradictions, missing evidence details, dashboard recomputation divergence, scanner/promotion divergence, valid-infinity profit-factor regression, or legacy artifact mutation.

## Fix Commit

- `d821ea4f8fddd75e43f0dde231a4b293117cae12` (`fix: correct temporal fold stability evidence semantics`)

## Fresh Generation

- New generation ID: `2026-06-21T17:44:33.265191+00:00`
- New model IDs: `1f47da026690ecc681d1ae1a`, `58ee8cd6b31fb509565898ef`, `94fce54c154b24e80c34e83e`, `ce54cc39317ba6fb033992c2`, `d90e8c92c47fb47e490c0979`, `7be25053a2032e48c91efe8f`, `49a8608f22994e639c6c94d3`, `d39d7d7413e9c7b9004a9dd7`
- Model count: 8
- Registry states: {'CANDIDATE': 8}
- Research dates: [['2016-06-20', '2026-06-18']]
- OOD Governance V2 on all models: True
- Persisted selection policy on all models: True
- No promotions: True
- Previous model artifacts changed: 0

## Complete Temporal-Fold Evidence Table

| model ID | family | direction | selected | folds requested | folds evaluated | folds with selected | selected per fold | evidence status | positive fraction | evidence gate | threshold gate | threshold reason | other failed mandatory gates | promotion eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1f47da026690ecc681d1ae1a | extra_trees | bear | 6 | 3 | 3 | 3 | [2,2,2] | AVAILABLE | 1.000000 | PASS | PASS | Temporal-fold positive fraction 100.00% meets the minimum 50.00%. | symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable | False |
| 58ee8cd6b31fb509565898ef | hist_gradient_boosting | bear | 0 | 3 | 0 | 0 | [0,0,0] | UNAVAILABLE | NOT_APPLICABLE | FAIL | NOT_APPLICABLE | Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable. | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable | False |
| 94fce54c154b24e80c34e83e | logistic_regression | bear | 0 | 3 | 0 | 0 | [0,0,0] | UNAVAILABLE | NOT_APPLICABLE | FAIL | NOT_APPLICABLE | Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable. | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | False |
| ce54cc39317ba6fb033992c2 | naive_base_rate | bear | 0 | 3 | 0 | 0 | [0,0,0] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | Temporal-fold trading stability is not applicable to the naive zero-selection control. | not_naive_control<br>return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | False |
| d90e8c92c47fb47e490c0979 | extra_trees | bull | 0 | 3 | 0 | 0 | [0,0,0] | UNAVAILABLE | NOT_APPLICABLE | FAIL | NOT_APPLICABLE | Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable. | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>mae_holdout_ood_q99_severity_acceptable | False |
| 7be25053a2032e48c91efe8f | hist_gradient_boosting | bull | 5 | 3 | 3 | 3 | [2,2,1] | AVAILABLE | 1.000000 | PASS | PASS | Temporal-fold positive fraction 100.00% meets the minimum 50.00%. | positive_expected_value_after_costs<br>symbol_concentration_max_050<br>sector_concentration_max_080<br>transaction_cost_sensitivity_not_collapsed<br>exceptional_period_concentration_max_060<br>mfe_holdout_ood_q99_severity_acceptable<br>mae_holdout_ood_q99_severity_acceptable | False |
| 49a8608f22994e639c6c94d3 | logistic_regression | bull | 0 | 3 | 0 | 0 | [0,0,0] | UNAVAILABLE | NOT_APPLICABLE | FAIL | NOT_APPLICABLE | Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable. | positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | False |
| d39d7d7413e9c7b9004a9dd7 | naive_base_rate | bull | 0 | 3 | 0 | 0 | [0,0,0] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | Temporal-fold trading stability is not applicable to the naive zero-selection control. | not_naive_control<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent | False |

## Contradiction-Audit Results

| Check | Count |
| --- | ---: |
| Total gate rows | 408 |
| Unavailable-evidence PASS rows | 0 |
| NOT_APPLICABLE-evidence PASS rows | 0 |
| Comparator/status contradictions | 0 |
| Status/reason contradictions | 0 |
| Valid infinity/unavailable mismatches | 0 |
| Mandatory learned temporal evidence missing without blocking availability gate | 0 |

## Failed Mandatory Gates And Promotion Eligibility

- `1f47da026690ecc681d1ae1a`: eligible=False; failed mandatory gates=symbol_concentration_max_050<br>sector_concentration_max_080<br>exceptional_period_concentration_max_060<br>return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable
- `58ee8cd6b31fb509565898ef`: eligible=False; failed mandatory gates=positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>temporal_fold_stability_evidence_available<br>return_holdout_ood_q99_severity_acceptable<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable
- `94fce54c154b24e80c34e83e`: eligible=False; failed mandatory gates=positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>temporal_fold_stability_evidence_available<br>return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent
- `ce54cc39317ba6fb033992c2`: eligible=False; failed mandatory gates=not_naive_control<br>return_holdout_ood_q99_severity_acceptable<br>mfe_prediction_path_metric_sign_valid<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent
- `d90e8c92c47fb47e490c0979`: eligible=False; failed mandatory gates=positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>temporal_fold_stability_evidence_available<br>mae_holdout_ood_q99_severity_acceptable
- `7be25053a2032e48c91efe8f`: eligible=False; failed mandatory gates=positive_expected_value_after_costs<br>symbol_concentration_max_050<br>sector_concentration_max_080<br>transaction_cost_sensitivity_not_collapsed<br>exceptional_period_concentration_max_060<br>mfe_holdout_ood_q99_severity_acceptable<br>mae_holdout_ood_q99_severity_acceptable
- `49a8608f22994e639c6c94d3`: eligible=False; failed mandatory gates=positive_expected_value_after_costs<br>profit_factor_min_090<br>portfolio_drawdown_available<br>portfolio_drawdown_not_worse_than_50pct<br>transaction_cost_sensitivity_not_collapsed<br>temporal_fold_stability_evidence_available<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent
- `d39d7d7413e9c7b9004a9dd7`: eligible=False; failed mandatory gates=not_naive_control<br>mfe_holdout_ood_q99_severity_acceptable<br>mfe_catastrophic_prediction_extrapolation_absent<br>mae_holdout_ood_q99_severity_acceptable<br>mae_catastrophic_prediction_extrapolation_absent

## Review-Only Scanner Result

- Scan ID: `3e4297cbfc8dc03078dc2bd1`
- Generation ID: `2026-06-21T17:44:33.265191+00:00`
- As-of date: `2026-06-18`
- Rows: 50
- Actionable rows: 0
- Rejected rows: 50
- Model states: {'CANDIDATE': 50}
- Rejection reasons: {'model_not_promoted': 50}
- Model quality-gate eligible rows: {'false': 50}
- OOD-warning rows: 4

## Final Verification Results

| Command | Result |
| --- | --- |
| `.venv/bin/pytest` | 155 collected, 155 passed, 0 failed, 0 skipped, 161 warnings |
| `.venv/bin/ruff check .` | PASS, `All checks passed!` |
| `.venv/bin/ruff format --check .` | PASS, `92 files already formatted` |
| `.venv/bin/mypy src` | PASS, `Success: no issues found in 54 source files` |

No `forward-update` or `daily-cycle` command was run. No model was promoted. No paper-forward event was created by this task.

## Exactly One Smallest Confirmed Next Task

Add a reusable CLI-accessible gate-integrity audit command that runs the same contradiction checks used here against any selected model generation before scanner execution.
