# Selection Policy Retrain Handoff

Generated: 2026-06-21

## Commit Review

Reviewed commit:

- `c0eba95420abdf9c0acc2f52b4e498ed39e1ace0`
- Parent: `f4aea0d103db0fa2b116ff9d06339c624e7d85e3`
- Commit message: `fix: include effective scanner config in snapshot identity`

Review focus:

- scanner execution identity completeness;
- effective-policy hashing;
- runtime threshold changes;
- cap changes;
- model-generation changes;
- feature/universe identity changes;
- legacy cache invalidation;
- snapshot immutability;
- exact-config idempotency.

Result: no P1 or P2 findings confirmed. The scanner identity now includes the effective policy bundle, raw runtime scanner config, model generation IDs, model artifact hashes when available, feature/universe identity, model state mode, include-challenger/include-candidate mode, canonical ordering version, and implementation/schema version. Cache reuse requires matching scan ID and matching persisted canonical identity metadata; legacy snapshots lacking identity metadata remain readable but are not reused.

## Commands Run

```bash
.venv/bin/python -m swing_rsi.cli discover-models \
  --minimum-training-samples 200 \
  --minimum-holdout-samples 80

.venv/bin/python -m swing_rsi.cli model-audit \
  --generation latest \
  --export-dir reports/selection_policy_retrain

.venv/bin/python -m swing_rsi.cli scan --include-challengers

.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

The run used existing local data only. No FMP update, model promotion, forward-update, or daily-cycle command was run.

## Fresh Generation

- Previous latest generation before this run: `2026-06-20T15:14:29.061490+00:00`
- New generation ID: `2026-06-21T02:34:35.295826+00:00`
- Research period persisted in metrics: `2016-06-20` through `2026-06-18`
- Model count: 8
- Registry states: 8 `CANDIDATE`, 0 `CHALLENGER`, 0 `CHAMPION`
- Previous model rows checked: 58
- Previous model row mismatches: 0
- Previous artifact hash mismatches: 0
- Model rows before/after: 58 to 66
- Scanner snapshots before/after: 7 to 8
- Forward events before/after: 285 to 285

Every new model persisted the complete selection policy:

- probability threshold: `0.55`
- expected-return threshold: `0.001`
- target-before-stop threshold: `0.50`
- liquidity threshold: `5000000.0`
- top-N limit: `5000`
- per-date limit: `5`
- selected-rate ceiling: `0.20`
- tie-breaking rule: `composite_utility_score_desc_then_symbol`
- selection policy hash: `ff689a7edf893b56`

The mandatory `selection_rate_policy_configured` gate is `PASS` for all 8 models and is no longer `NOT_CONFIGURED`.

## Model Table

All models use:

- train: `2016-06-20` to `2022-04-28`
- calibration: `2022-05-13` to `2024-04-17`
- holdout: `2024-05-02` to `2026-04-22`
- samples: 41,884 train / 16,800 calibration / 17,069 holdout

| model | dir | family | selected | rate | avg/max candidates per date | Brier / naive / skill | mean return / LCB / PF | portfolio return / max DD | OOD | promotion |
|---|---|---|---:|---:|---:|---|---|---|---:|---|
| `4e7655c871ece5238006e38c` | bull | hist_gradient_boosting | 5 | 0.029% | 1.00 / 1 | 0.247874 / 0.249697 / 0.007300 | 4.346% / -1.198% / 7.049 | -0.419% / -1.568% | 13 (0.076%) | no |
| `594020c7b2ea94757b34351d` | bull | naive_base_rate | 0 | 0.000% | 0.00 / 0 | 0.249534 / 0.249534 / 0.000000 | NA / NA / inf | NA / NA | 26 (0.152%) | no |
| `61c91fd5830d89e379ca33f7` | bull | extra_trees | 0 | 0.000% | 0.00 / 0 | 0.244704 / 0.249697 / 0.019994 | NA / NA / inf | NA / NA | 3 (0.018%) | no |
| `6b5f102c1cdebf946f0b959c` | bear | hist_gradient_boosting | 0 | 0.000% | 0.00 / 0 | 0.248393 / 0.249630 / 0.004954 | NA / NA / inf | NA / NA | 55 (0.322%) | no |
| `87b08e653db529893bbac3f6` | bull | logistic_regression | 0 | 0.000% | 0.00 / 0 | 0.243684 / 0.249697 / 0.024079 | NA / NA / inf | NA / NA | 26 (0.152%) | no |
| `a75df8d1c5f643547eda7992` | bear | extra_trees | 6 | 0.035% | 1.00 / 1 | 0.244796 / 0.249630 / 0.019366 | 4.448% / 3.083% / inf | 2.306% / -1.024% | 39 (0.228%) | no |
| `d95bc4cea6a158a344f85175` | bear | naive_base_rate | 0 | 0.000% | 0.00 / 0 | 0.249440 / 0.249440 / 0.000000 | NA / NA / inf | NA / NA | 120 (0.703%) | no |
| `e641a2ba34ed11f8bac8c3b0` | bear | logistic_regression | 0 | 0.000% | 0.00 / 0 | 0.243674 / 0.249630 / 0.023860 | NA / NA / inf | NA / NA | 120 (0.703%) | no |

## Gate Failures

Failed or not-configured mandatory gates by model:

- `4e7655c871ece5238006e38c`: `positive_expected_value_after_costs`, `symbol_concentration_max_050`, `sector_concentration_max_080`, `transaction_cost_sensitivity_not_collapsed`, `exceptional_period_concentration_max_060`, `prediction_out_of_distribution_absent`
- `594020c7b2ea94757b34351d`: `not_naive_control`, `prediction_out_of_distribution_absent`
- `61c91fd5830d89e379ca33f7`: `positive_expected_value_after_costs`, `profit_factor_min_090`, `portfolio_drawdown_available`, `portfolio_drawdown_not_worse_than_50pct`, `transaction_cost_sensitivity_not_collapsed`, `prediction_out_of_distribution_absent`
- `6b5f102c1cdebf946f0b959c`: `positive_expected_value_after_costs`, `profit_factor_min_090`, `portfolio_drawdown_available`, `portfolio_drawdown_not_worse_than_50pct`, `transaction_cost_sensitivity_not_collapsed`, `prediction_out_of_distribution_absent`
- `87b08e653db529893bbac3f6`: `positive_expected_value_after_costs`, `profit_factor_min_090`, `portfolio_drawdown_available`, `portfolio_drawdown_not_worse_than_50pct`, `transaction_cost_sensitivity_not_collapsed`, `prediction_out_of_distribution_absent`
- `a75df8d1c5f643547eda7992`: `profit_factor_min_090`, `symbol_concentration_max_050`, `sector_concentration_max_080`, `exceptional_period_concentration_max_060`, `prediction_out_of_distribution_absent`
- `d95bc4cea6a158a344f85175`: `not_naive_control`, `prediction_out_of_distribution_absent`
- `e641a2ba34ed11f8bac8c3b0`: `positive_expected_value_after_costs`, `profit_factor_min_090`, `portfolio_drawdown_available`, `portfolio_drawdown_not_worse_than_50pct`, `transaction_cost_sensitivity_not_collapsed`, `prediction_out_of_distribution_absent`

No model is promotion eligible.

## Selection And Portfolio Verification

- Selected-candidate threshold proof: the two models with selected rows have selected ledger rows that pass probability, expected-return, and target-before-stop thresholds.
- Models with zero selected rows have threshold proof marked not applicable because no actionable selected rows exist.
- Holdout cap policy persisted for every model: top-N `5000`, per-date `5`.
- Canonical deterministic tie-break persisted for every model: `composite_utility_score_desc_then_symbol`.
- Portfolio daily equity rows are chronological for the two models with selected portfolio simulations:
  - `4e7655c871ece5238006e38c`: 10 daily equity rows, equity start `0.9955555556`, equity end `0.9958110072`, minimum equity `0.9813581904`
  - `a75df8d1c5f643547eda7992`: 176 daily equity rows, equity start `1.0022299116`, equity end `1.0230550525`, minimum equity `1.0022299116`
- Models with no selected candidates have no portfolio drawdown; this remains non-passing for portfolio drawdown gates instead of being silently treated as success.

## Scanner Result

Review-only scanner command:

```bash
.venv/bin/python -m swing_rsi.cli scan --include-challengers
```

Snapshot:

- scan ID: `c9ad576e6177a329f0361a17`
- market as-of date: `2026-06-18`
- CSV: `artifacts/scanner/c9ad576e6177a329f0361a17_scanner.csv`
- Parquet: `artifacts/scanner/c9ad576e6177a329f0361a17_scanner.parquet`
- total rows: 50
- bullish rows: 25
- bearish rows: 25
- actionable rows: 0
- rejected rows: 50
- exact rejection reasons: `model_not_promoted` = 50

Scanner identity metadata persisted:

- scanner identity schema version: 2
- raw scanner config hash: present
- effective policy bundle hash: present
- canonical execution identity: present
- identity includes runtime config: yes
- identity includes effective selection policies: yes
- model generation IDs in snapshot all point to `2026-06-21T02:34:35.295826+00:00`

All scanner rows are from `CANDIDATE` models with `model_quality_gate_eligible=False`; therefore no gate-ineligible model produced an actionable row.

## Audit Exports

Generated under ignored report output:

- `reports/selection_policy_retrain/model_summary.csv`
- `reports/selection_policy_retrain/full_gate_audit.csv`
- `reports/selection_policy_retrain/full_gate_audit.json`
- `reports/selection_policy_retrain/calibration_table.csv`
- `reports/selection_policy_retrain/portfolio_daily_equity.csv`
- `reports/selection_policy_retrain/selected_candidate_ledger.csv`
- `reports/selection_policy_retrain/portfolio_trade_ledger.csv`

## Verification Results

```text
.venv/bin/pytest
115 passed, 161 warnings in 59.31s

.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check .
91 files already formatted

.venv/bin/mypy src
Success: no issues found in 53 source files
```

Warnings are existing pandas fragmentation warnings from feature construction and one joblib core-count warning. No automated test contacted FMP.

## Required Verification Checklist

- New model generation created: PASS, `2026-06-21T02:34:35.295826+00:00`
- Previous generations and artifacts unchanged: PASS, 58 prior model rows checked, 0 row mismatches, 0 prior artifact hash mismatches
- Every learned model contains complete persisted selection policy: PASS
- Selection-policy configuration no longer `NOT_CONFIGURED`: PASS, `selection_rate_policy_configured` is `PASS` for all 8 models
- Holdout selection applies probability, expected-return, target-before-stop, and liquidity thresholds: PASS, persisted policy and selected ledger evidence
- Per-date and global caps use canonical deterministic order: PASS, persisted policy plus passing regression tests from `pytest`
- Portfolio replay groups same-date candidates deterministically: PASS, passing regression tests from `pytest`
- Portfolio drawdown uses chronological daily equity: PASS, portfolio daily equity export and passing tests
- Scanner identity contains effective selection policy and runtime config: PASS
- Gate-ineligible models cannot produce actionable rows: PASS, 0 actionable rows, all new models `CANDIDATE` and gate-ineligible in scanner output
- No model automatically promoted: PASS, all 8 new models are `CANDIDATE`
- No paper-forward event created: PASS, forward event count remained 285 before and after

## Smallest Confirmed Next Task

Investigate and correct the regression prediction out-of-distribution gate failures using only the existing data, model families, and gate framework.

Why this is next: every new model failed `prediction_out_of_distribution_absent`, which blocks promotion even for the models with selected candidates and acceptable portfolio drawdown. This should be handled before any promotion or scanner actionability work.

Acceptance criteria:

- identify which regression head or target distribution causes each OOD count;
- preserve raw and transformed predictions;
- keep bounds fitted on training data only;
- do not weaken OOD or quality gates;
- rerun discovery and model-audit on existing local data;
- either eliminate unjustified OOD failures or document why the model remains ineligible;
- all verification commands pass.
