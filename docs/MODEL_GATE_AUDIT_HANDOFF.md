# Model Gate Audit Handoff

Generated: 2026-06-20 America/New_York

## Scope

This was a focused model-evaluation integrity audit. It did not add options,
intraday data, NLP, broker execution, new indicators, new model families, or
new scanner features. No model was promoted.

Secrets were not opened or printed. `.env`, raw market data, processed feature
parquet, model artifacts, SQLite state, scanner outputs, reports, logs, caches,
and credentials remain ignored.

## Root Cause

The near--100% holdout maximum drawdown came from compounding selected
cross-sectional prediction rows as if every row were a sequential full-capital
trade:

```text
selected_row_sequence_equity = (1 + every_selected_row_return).cumprod()
selected_row_sequence_drawdown = selected_row_sequence_equity / running_peak - 1
```

That is invalid when many symbols can be selected on the same date. It treats
same-day panel rows as serial all-in trades and can approach -100% even when a
position-sized chronological portfolio would not lose nearly all capital.

The invalid value is now preserved only as:

```text
selected_row_sequence_drawdown
```

The model gate uses:

```text
portfolio_max_drawdown = min(daily_portfolio_equity / daily_peak - 1)
```

where daily portfolio equity comes from chronological scanner-candidate
portfolio simulation with position sizing, exposure limits, costs, slippage,
and next-open entry.

## Corrected Evaluation Layers

Prediction-level evaluation is calculated across every eligible holdout row.
Selected-candidate evaluation is calculated only on frozen-policy selected
rows. Portfolio-level holdout evaluation is calculated only by chronological
portfolio simulation.

Selected-candidate drawdown is not a portfolio drawdown gate.

## Research Date Correction

Latest corrected generation:

- generation ID: `2026-06-20T15:14:29.061490+00:00`
- research start: `2016-06-20`
- research end: `2026-06-18`
- holdout samples per model: `17,069`
- raw feature panel still begins before 2016 for warm-up history
- no eligible model row before `2016-06-20`
- no included label extends beyond `2026-06-18`

The earlier eight-model generation began train rows in 2006. That is preserved
as legacy evidence and superseded by the corrected generation.

## Latest Corrected Model Summary

| model_id | dir | family | selected | selected_rate | row_seq_dd | portfolio_dd | model_brier | naive_brier | brier_skill | failed mandatory gates | not configured |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `ee38240015f84c64b24686e2` | bear | extra_trees | 1,668 | 9.7721% | -99.9193% | -28.9845% | 0.244796 | 0.249630 | 0.019366 | prediction_out_of_distribution_absent | selection_rate_policy_configured |
| `97cb2d6393e395a27ea5cec3` | bear | hist_gradient_boosting | 718 | 4.2065% | -99.8358% | -38.6864% | 0.248393 | 0.249630 | 0.004954 | prediction_out_of_distribution_absent | selection_rate_policy_configured |
| `bb6519f162ca75ba211549de` | bear | logistic_regression | 2,049 | 12.0042% | -99.9998% | -48.0380% | 0.243674 | 0.249630 | 0.023860 | prediction_out_of_distribution_absent | selection_rate_policy_configured |
| `3d99c3f3540b6eb30ac52513` | bear | naive_base_rate | 0 | 0.0000% | n/a | n/a | 0.249440 | 0.249440 | 0.000000 | not_naive_control, prediction_out_of_distribution_absent | selection_rate_policy_configured |
| `d5560f3bf8c44135d0700ee1` | bull | extra_trees | 11,407 | 66.8288% | -100.0000% | -34.6327% | 0.244704 | 0.249697 | 0.019994 | prediction_turnover_max_050, prediction_out_of_distribution_absent | selection_rate_policy_configured |
| `790ac0b2f82362ac8df5a72e` | bull | hist_gradient_boosting | 11,882 | 69.6116% | -100.0000% | -27.8316% | 0.247874 | 0.249697 | 0.007300 | prediction_turnover_max_050, prediction_out_of_distribution_absent | selection_rate_policy_configured |
| `0163f5f828e82b49400c5088` | bull | logistic_regression | 13,066 | 76.5481% | -100.0000% | -41.5070% | 0.243684 | 0.249697 | 0.024079 | prediction_turnover_max_050, prediction_out_of_distribution_absent | selection_rate_policy_configured |
| `f19f87c9190893dea0466180` | bull | naive_base_rate | 0 | 0.0000% | n/a | n/a | 0.249534 | 0.249534 | 0.000000 | not_naive_control, prediction_out_of_distribution_absent | selection_rate_policy_configured |

No model is promotion eligible.

## Complete Latest Gate Matrix

Short ID mapping:

- `0163f5`: `0163f5f828e82b49400c5088`
- `3d99c3`: `3d99c3f3540b6eb30ac52513`
- `790ac0`: `790ac0b2f82362ac8df5a72e`
- `97cb2d`: `97cb2d6393e395a27ea5cec3`
- `bb6519`: `bb6519f162ca75ba211549de`
- `d5560f`: `d5560f3bf8c44135d0700ee1`
- `ee3824`: `ee38240015f84c64b24686e2`
- `f19f87`: `f19f87c9190893dea0466180`

| gate_id | 0163f5 | 3d99c3 | 790ac0 | 97cb2d | bb6519 | d5560f | ee3824 | f19f87 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| brier_skill_vs_naive_positive | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL |
| comparison_controls_available | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| exceptional_period_concentration_max_060 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| feature_stability_mean_abs_z_max_250 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| holdout_brier_max_035 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| minimum_training_samples | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| minimum_unseen_observations | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| not_naive_control | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL |
| portfolio_drawdown_available | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL |
| portfolio_drawdown_not_worse_than_50pct | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL |
| positive_expected_value_after_costs | PASS | n/a | PASS | PASS | PASS | PASS | PASS | n/a |
| prediction_out_of_distribution_absent | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| prediction_turnover_max_050 | FAIL | PASS | FAIL | PASS | PASS | FAIL | PASS | PASS |
| prediction_units_verified | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| profit_factor_min_090 | PASS | n/a | PASS | PASS | PASS | PASS | PASS | n/a |
| sector_concentration_max_080 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| selected_candidate_quality_available | n/a | NOT_APPLICABLE | n/a | n/a | n/a | n/a | n/a | NOT_APPLICABLE |
| selection_rate_policy_configured | NOT_CONFIGURED | NOT_CONFIGURED | NOT_CONFIGURED | NOT_CONFIGURED | NOT_CONFIGURED | NOT_CONFIGURED | NOT_CONFIGURED | NOT_CONFIGURED |
| symbol_concentration_max_050 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| temporal_fold_stability_min_050 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| transaction_cost_sensitivity_not_collapsed | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL |

Full exports:

- `reports/model_audit_latest/model_summary.csv`
- `reports/model_audit_latest/full_gate_audit.csv`
- `reports/model_audit_latest/full_gate_audit.json`
- `reports/model_audit_latest/calibration_table.csv`
- `reports/model_audit_latest/portfolio_daily_equity.csv`
- `reports/model_audit_latest/selected_candidate_ledger.csv`
- `reports/model_audit_latest/portfolio_trade_ledger.csv`

Export sizes:

- full gate audit: 158 rows plus header
- model summary: 8 rows plus header
- portfolio daily equity: 2,994 rows plus header
- selected candidate ledger: 40,792 rows plus header

## Legacy `2bfd1ba248c6f489efb31664` Audit

Legacy model:

- model ID: `2bfd1ba248c6f489efb31664`
- direction/family: bear ExtraTrees
- holdout observations: 34,488
- selected observations: 2,858
- old holdout max drawdown: `-0.9999998201168752`
- holdout Brier: `0.24843625537501401`
- canonical gate records: not present in original row
- loader-exported legacy gate rows: 15
- legacy failed gate: `drawdown_not_worse_than_50pct`

Complete legacy gate export:

- `reports/model_audit_legacy_2bfd/full_gate_audit.csv`
- `reports/model_audit_legacy_2bfd/full_gate_audit.json`

## SOXL Prediction Magnitude Audit

Observed legacy scanner artifact:

- file: `artifacts/scanner/9ff465a229a0d4cd9e4e6b36_scanner.csv`
- SOXL bearish logistic model `d3e74e24f0dd2cae717f2107`:
  - expected return: `0.290930` displayed as `29.09%`
  - expected MFE: `0.856482` displayed as `85.65%`
  - expected MAE: `-0.357388` displayed as `-35.74%`
- SOXL bearish naive model `81eb0d2483c8579fab58d9ef` had the same regression outputs because the old naive family used ridge regressors for return/MFE/MAE.
- SOXL bearish ExtraTrees `2bfd1ba248c6f489efb31664`:
  - expected return: `0.171508`
  - expected MFE: `0.263398`
  - expected MAE: `-0.120499`

Training target quantiles for the legacy SOXL bearish models:

| target | min | q01 | q05 | median | q95 | q99 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| return | -0.248603 | -0.145134 | -0.093414 | -0.005038 | 0.103307 | 0.213573 | 0.445483 |
| MFE | 0.000000 | 0.000000 | 0.001463 | 0.024511 | 0.149517 | 0.300723 | 0.524297 |
| MAE | -0.298276 | -0.190363 | -0.117216 | -0.026616 | -0.001996 | -0.000205 | 0.000000 |

Root cause: not a percent/decimal conversion error and not a bearish sign
conversion error. The values are decimal returns from regression heads applied
to an extreme leveraged-ETF feature snapshot. The logistic/naive SOXL return
and MFE predictions exceed train-only robust q99 ranges, so the corrected audit
flags them as prediction-sanity failures instead of clipping or suppressing
them.

New review scanner snapshot:

- scan ID: `6bf9b09ea1930cddcb4ad4cb`
- as-of date: `2026-06-18`
- rows: 50
- all rows are `REJECTED` because their models are `CANDIDATE`, not promoted
- SOXL bear ExtraTrees `ee38240015f84c64b24686e2`:
  - expected return raw/transformed: `0.227075`
  - expected MFE raw/transformed: `0.462163`
  - expected MAE raw/transformed: `-0.088748`
  - return OOD: `False`
  - MFE OOD: `True`
  - MAE OOD: `False`

## RSI Feature-Family Diagnostic

Generated feature count still includes many RSI-family columns. The latest
model selected-feature diagnostics show RSI raw count does not imply model
importance; selected feature-family counts and permutation summaries are now
persisted per model. The review scanner attribution for the top SOXL bearish
row was dominated by volatility and trend structure with residual/unexplained
explicitly shown, not RSI.

## Dashboard and CLI Changes

CLI:

```bash
python -m swing_rsi.cli model-audit --generation latest
python -m swing_rsi.cli model-audit --model-id 2bfd1ba248c6f489efb31664 --export-dir reports/model_audit
```

Model Registry dashboard:

- compact columns fit the screen using abbreviated labels;
- detailed tabs expose Gate Audit, Calibration, Candidate Selection, Portfolio
  Holdout, Stability, Feature Diagnostics, Prediction Sanity, and Artifact
  Metadata;
- promotion button is disabled when canonical mandatory gates fail, are not
  configured, are not applicable, or are missing;
- gate-audit, calibration, selected-candidate, and portfolio equity exports are
  available.

Discovery Lab now shows the same portfolio-aware model summary and promotion
eligibility fields instead of dumping every raw metric into a wide table.

## Verification Results

Commands already run during this audit:

- `.venv/bin/pytest`: 95 collected, 95 passed, 0 failed, 0 skipped, 161 warnings.
- `.venv/bin/pytest tests/test_model_evaluation_integrity.py tests/test_dashboard_model_registry.py -q`: 13 passed.
- `.venv/bin/pytest tests/test_dashboard_interactions.py tests/test_dashboard_model_registry.py tests/test_dashboard_imports.py -q`: 14 passed.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: passed.
- `.venv/bin/mypy src`: passed, 52 source files checked.
- `python -m swing_rsi.cli model-audit --generation latest`: passed.
- `python -m swing_rsi.cli model-audit --model-id 2bfd1ba248c6f489efb31664 --export-dir reports/model_audit_legacy_2bfd`: passed.
- `python -m swing_rsi.cli model-audit --generation latest --export-dir reports/model_audit_latest`: passed.
- `python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80`: passed; registered 8 candidates, 0 challengers, 0 promoted.
- `python -m swing_rsi.cli scan --include-challengers`: passed; snapshot `6bf9b09ea1930cddcb4ad4cb`, 50 rows, all rejected review rows.
- `curl -I http://localhost:8501`: returned `HTTP/1.1 200 OK`.

## Tests Added

- `tests/test_model_evaluation_integrity.py`
  - reproduces invalid cross-sectional row compounding;
  - verifies same-date portfolio decision sets;
  - verifies exposure limits;
  - verifies rejected candidates do not enter;
  - verifies deterministic daily equity;
  - verifies research rows before `2016-06-20` are excluded;
  - verifies warm-up history remains possible;
  - verifies labels do not extend beyond research end;
  - verifies bearish decimal return/MFE/MAE conventions;
  - verifies worse-than-naive Brier gate failure;
  - verifies naive zero-selection trading gates are not applicable;
  - verifies mandatory `NOT_CONFIGURED` blocks promotion;
  - verifies persisted gate export;
  - verifies failed mandatory gate blocks promotion;
  - verifies missing canonical gates block promotion;
  - verifies OOD prediction flags use train-only bounds and preserve raw values.
- `tests/test_dashboard_model_registry.py`
  - verifies compact registry labels and columns fit the default dashboard view.

Existing dashboard interaction tests also cover Model Registry rendering.

## Files Changed

Core code:

- `src/swing_rsi/engine/gates.py`
- `src/swing_rsi/engine/model_audit.py`
- `src/swing_rsi/engine/models.py`
- `src/swing_rsi/engine/portfolio.py`
- `src/swing_rsi/engine/registry.py`
- `src/swing_rsi/engine/scanner.py`
- `src/swing_rsi/engine/storage.py`
- `src/swing_rsi/cli.py`

Dashboard:

- `dashboard/sections/discovery_lab.py`
- `dashboard/sections/model_registry.py`

Tests:

- `tests/test_model_evaluation_integrity.py`
- `tests/test_dashboard_model_registry.py`
- `tests/test_dashboard_interactions.py`

Docs:

- `docs/MODEL_EVALUATION_INTEGRITY.md`
- `docs/MODEL_GATE_AUDIT_HANDOFF.md`
- `docs/MODEL_VALIDATION_STANDARD.md`
- `docs/MODEL_GOVERNANCE.md`
- `docs/BACKTESTING_STANDARD.md`
- `docs/AUTONOMOUS_SCANNER_V1_HANDOFF.md`
- `docs/CHANGELOG.md`
- `docs/DECISIONS.md`

## Remaining Limitations

- The selection-rate ceiling remains intentionally unconfigured; this blocks
  promotion.
- Prediction OOD gates fail for every latest model; no clipping or transform
  was introduced.
- The current broad bullish candidate coverage remains a research concern and
  is flagged by turnover and selection-policy gates.
- Legacy model rows have only legacy boolean gates; the loader can export them
  as legacy gate rows, but they do not contain canonical thresholds.
- Generated reports, model artifacts, scanner outputs, and SQLite state are
  ignored and not committed.

## Git

Planned local audit commits:

1. `fix: separate prediction and portfolio model evaluation`
2. `feat: persist canonical model quality gates`
3. `feat: add model gate and calibration audit views`
4. `test: validate autonomous model evaluation integrity`
5. `docs: document model evaluation and promotion audit`

Do not push.
