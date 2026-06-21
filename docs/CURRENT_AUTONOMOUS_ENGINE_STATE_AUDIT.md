# Current Autonomous Engine State Audit

Generated UTC: `2026-06-20T23:34:37.270469+00:00`
Repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

## 1. Repository and Git State
- Absolute repository path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- Current branch: `feat/autonomous-swing-scanner-v1`
- Current HEAD: `a87f2fa5cde7b3936f7c489fb10390e1dfffb9bd`
- Latest 15 commits:
```text
a87f2fa docs: record model audit commit hashes
657dbac docs: document model evaluation and promotion audit
cb68c16 test: validate autonomous model evaluation integrity
b4280c7 feat: add model gate and calibration audit views
af65ec9 feat: persist canonical model quality gates
1318873 fix: separate prediction and portfolio model evaluation
3abf47a fix: complete scanner dashboard lifecycle evidence
e6b1c69 feat: complete autonomous scanner evidence gaps
6e20ea3 feat: harden autonomous scanner evidence pipeline
00717b7 docs: finalize autonomous scanner handoff
b5b985a feat: complete scanner diagnostics and forward lifecycle
ff244b1 docs: add autonomous scanner handoff
3880c73 feat: add autonomous swing scanner vertical slice
a808447 fix: correct gap-aware walk-forward split planning
3d9d4c8 fix: prevent dashboard reload loop
```
- Working-tree status before this report file was written:
```text
D docs/AUTONOMOUS_SCANNER_V1_HANDOFF.md
```
- `git status -sb`: ## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1 [ahead 6]
 D docs/AUTONOMOUS_SCANNER_V1_HANDOFF.md
- Modified files: none
- Added files: none
- Deleted files: ['docs/AUTONOMOUS_SCANNER_V1_HANDOFF.md']
- Untracked files before report creation: none
- Source changes remain uncommitted: NO
- Remote exists: YES
```text
origin	https://github.com/billyribeiro-ux/swing-self-machine-learning.git (fetch)
origin	https://github.com/billyribeiro-ux/swing-self-machine-learning.git (push)
```
- Push state from local refs: branch is ahead of `origin/feat/autonomous-swing-scanner-v1` by six commits; no fetch or push was performed in this audit, so this is based on current local remote refs.
```text
* feat/autonomous-swing-scanner-v1 a87f2fa [origin/feat/autonomous-swing-scanner-v1: ahead 6] docs: record model audit commit hashes
  feat/local-research-dashboard    a808447 [origin/feat/local-research-dashboard: ahead 1] fix: correct gap-aware walk-forward split planning
  main                             353b583 feat: add secure FMP daily data foundation
```
- Local commits not present in current local `origin/feat/autonomous-swing-scanner-v1` ref:
```text
a87f2fa docs: record model audit commit hashes
657dbac docs: document model evaluation and promotion audit
cb68c16 test: validate autonomous model evaluation integrity
b4280c7 feat: add model gate and calibration audit views
af65ec9 feat: persist canonical model quality gates
1318873 fix: separate prediction and portfolio model evaluation
```
- Model-evaluation audit commit presence:
| commit | in_current_branch |
| --- | --- |
| 1318873 | True |
| af65ec9 | True |
| b4280c7 | True |
| cb68c16 | True |
| 657dbac | True |
- Important current dirty item: `docs/AUTONOMOUS_SCANNER_V1_HANDOFF.md` is deleted in the working tree. This audit did not restore it because the user requested current-state reporting and no unrelated changes.

## 2. Code Review
- model evaluation: Findings above: portfolio same-date batching and scanner gate eligibility reliance.
- canonical quality gates: NO CONFIRMED FINDING
- portfolio drawdown: Finding above: drawdown source is daily equity, but same-date batch allocation remains order-dependent.
- chronological splitting: LOW metadata finding above; no confirmed leakage.
- research-date filtering: NO CONFIRMED FINDING
- label purging: NO CONFIRMED FINDING
- probability calibration: NO CONFIRMED FINDING
- model registry: NO CONFIRMED FINDING
- promotion eligibility: NO CONFIRMED FINDING
- scanner selection: Finding above: scanner should re-check persisted canonical gate eligibility before actionable use.
- attribution: NO CONFIRMED FINDING
- portfolio backtesting: Finding above: same-date decision batching.
- append-only paper forward testing: NO CONFIRMED FINDING
- dashboard Model Registry and Discovery Lab: LOW dashboard export clarity finding above.
- CLI model-audit exports: NO CONFIRMED FINDING

Confirmed findings:
| severity | file | line/function | description | why it matters | risk | recommended correction |
| --- | --- | --- | --- | --- | --- | --- |
| MEDIUM | src/swing_rsi/engine/portfolio.py | backtest_scanner_candidates, lines 265-372 | Candidate rows are sorted and processed one row at a time. Same-date candidates are not first grouped into a single portfolio decision set. | Order-dependent processing can change which same-date candidates enter when exposure, sector, or per-symbol limits bind. It can make portfolio holdout results depend on row order instead of a stable date-batch policy. | Misleading portfolio metrics; not confirmed leakage or state corruption. | Process one as_of_date at a time, expire positions once per date, rank that date's candidates deterministically, then allocate within that date batch and persist audit reasons for skipped rows. |
| MEDIUM | src/swing_rsi/application/engine_service.py and src/swing_rsi/engine/scanner.py | _scanner_models lines 291-320; run_scanner lines 164-178 | Scanner eligibility is based on persisted registry state strings. It does not directly recompute promotion eligibility from persisted canonical gate results before treating CHAMPION/CHALLENGER rows as actionable. | The current DB has no CHAMPION/CHALLENGER rows, so no current false actionable signal exists. However, if registry state is manually or accidentally changed, scanner actionability could diverge from canonical gate results. | Potential misleading scanner UI/actionability if registry state becomes inconsistent; no current corrupted state found. | Require promotion_eligibility(model.gate_results).eligible in _scanner_models/run_scanner before any model can produce ACTIONABLE_PAPER_CANDIDATE rows. |
| LOW | src/swing_rsi/engine/splits.py | chronological_train_calibration_holdout_split, lines 96-107 | The returned ChronologicalSplit records purge_sessions=horizon rather than a measured number of removed rows/sessions. | The purge itself uses label_end_date boundary checks and appears valid, but the metadata can be misread as proof of the exact number of purged sessions. | Misleading audit metadata; not confirmed leakage. | Persist measured purge counts and embargo dates for train->calibration and calibration->holdout boundaries. |
| LOW | dashboard/sections/model_registry.py | render_page, lines 281-363 | Full CSV/JSON export buttons are available only inside the selected model drilldown, not as one-click generation-wide exports from the dashboard. | CLI exports are complete, but dashboard users may think the page-level export covers only the selected model unless they use the CLI. | UI clarity limitation only; no leakage, false result, or state corruption found. | Add generation-wide model summary and gate-audit export buttons powered by build_model_audit/export_model_audit. |

## 3. Current Verification Results
| command | collected | passed | failed | skipped | warnings | time | exit | result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| .venv/bin/pytest | 95 | 95 | 0 | 0 | 161 | 55.94s | 0 | passed |
| .venv/bin/ruff check . | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT AVAILABLE | 0 | All checks passed! |
| .venv/bin/ruff format --check . | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT AVAILABLE | 0 | 90 files already formatted |
| .venv/bin/mypy src | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT AVAILABLE | 0 | Success: no issues found in 52 source files |
| .venv/bin/pytest tests/test_model_evaluation_integrity.py tests/test_dashboard_model_registry.py tests/test_dashboard_interactions.py tests/test_autonomous_engine.py tests/test_application_services.py -q | 69 | 69 | 0 | 0 | 161 | 40.25s | 0 | passed |
| python -m swing_rsi.cli model-audit --generation latest --export-dir reports/current_state_audit_cli | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT AVAILABLE | 127 | command failed: zsh:1: command not found: python |
| .venv/bin/python -m swing_rsi.cli model-audit --generation latest --export-dir reports/current_state_audit_cli | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT AVAILABLE | 0 | passed; exported current CLI audit files |
| .venv/bin/python -m swing_rsi.cli model-registry | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT AVAILABLE | 0 | passed; listed current registry rows |

## 4. Current Model Generation
- generation_id: `2026-06-20T15:14:29.061490+00:00`
- generation_creation_time: `2026-06-20T15:14:29.061490+00:00`
- feature_manifest_hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- universe_snapshot_id: `6b1a74750684506e1a5b`
- research_start: `2016-06-20`
- research_end: `2026-06-18`
- raw_data_first_date: `2006-08-03`
- feature_warmup_first_date: `2006-08-03`
- first_generated_feature_date: `2006-08-03`
- first_model_eligible_observation_date: `2016-06-20`
- final_model_eligible_observation_date: `2026-06-04`
- first_label_date: `2006-08-03`
- final_label_date: `2026-06-18`
- train_start: `2016-06-20`
- train_end: `2022-04-28`
- calibration_start: `2022-05-13`
- calibration_end: `2024-04-17`
- holdout_start: `2024-05-02`
- holdout_end: `2026-04-22`
- model_count: `8`

Latest-generation models:
| model ID | direction | horizon | family | state | promotion eligible |
| --- | --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | bull | 10 | logistic_regression | CANDIDATE | NO |
| 3d99c3f3540b6eb30ac52513 | bear | 10 | naive_base_rate | CANDIDATE | NO |
| 790ac0b2f82362ac8df5a72e | bull | 10 | hist_gradient_boosting | CANDIDATE | NO |
| 97cb2d6393e395a27ea5cec3 | bear | 10 | hist_gradient_boosting | CANDIDATE | NO |
| bb6519f162ca75ba211549de | bear | 10 | logistic_regression | CANDIDATE | NO |
| d5560f3bf8c44135d0700ee1 | bull | 10 | extra_trees | CANDIDATE | NO |
| ee38240015f84c64b24686e2 | bear | 10 | extra_trees | CANDIDATE | NO |
| f19f87c9190893dea0466180 | bull | 10 | naive_base_rate | CANDIDATE | NO |

Legacy model ID status:
| legacy_model_id | in_latest_generation | registry_state | generation |
| --- | --- | --- | --- |
| 2bfd1ba248c6f489efb31664 | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |
| 342cf8a2d21a4bde57e65137 | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |
| 45abf4961fdd454ac47b3f2f | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |
| 774634752b24e4b914e59f2e | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |
| 81eb0d2483c8579fab58d9ef | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |
| d3e74e24f0dd2cae717f2107 | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |
| fbb4a81b062858abf0cf0fcc | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |
| fed5b8e40985892722bfa661 | NO | CANDIDATE | 2026-06-20T04:38:24.028225+00:00 |

## 5. Complete Model Summary Table
| model ID | direction | horizon | family | state | train | cal | holdout | selected | selected rate | avg/date | max/date | dates w/ candidates | model Brier | naive Brier | BSS | log loss | cal intercept | cal slope | ECE | reg MAE | reg RMSE | rank corr | mean net | median net | LCB | win | PF | row seq DD | port total | port ann | port max DD | port exposure | port turnover | symbol conc | sector conc | temporal + frac | period conc | OOD | mand pass | mand fail | not cfg | eligible | blocked reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | bull | 10 | logistic_regression | CANDIDATE | 41884 | 16800 | 17069 | 13066 | 76.55% | 26.449 | 32 | 100.00% | 0.243684 | 0.249697 | 0.024079 | 0.750426 | 0.064842 | 0.152637 | 0.044125 | 0.050758 | 0.081593 | 0.166280 | 0.90% | 0.61% | 0.79% | 56.21% | 1.480 | -100.00% | 147.90% | 58.02% | -41.51% | 100.00% | 3.690 | 3.77% | 10.89% | 100.00% | 49.23% | 26 / 0.05% | 17 | 2 | 1 | NO | prediction_turnover_max_050: Selected observation rate exceeds configured turnover cap. ; prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |
| 3d99c3f3540b6eb30ac52513 | bear | 10 | naive_base_rate | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.00% | 0.000 | 0 | 0.00% | 0.249440 | 0.249440 | 0.000000 | 0.692027 | -0.100579 | 0.014297 | 0.035652 | 0.052432 | 0.086635 | 0.133485 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | Infinity | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 120 / 0.23% | 11 | 2 | 1 | NO | not_naive_control: Naive controls are never promotion eligible. ; prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |
| 790ac0b2f82362ac8df5a72e | bull | 10 | hist_gradient_boosting | CANDIDATE | 41884 | 16800 | 17069 | 11882 | 69.61% | 24.053 | 31 | 100.00% | 0.247874 | 0.249697 | 0.007300 | 0.688885 | -0.099194 | 1.351021 | 0.052997 | 0.051363 | 0.081680 | 0.085185 | 0.72% | 0.47% | 0.60% | 54.70% | 1.348 | -100.00% | 230.14% | 82.57% | -27.83% | 100.00% | 4.550 | 3.77% | 9.84% | 100.00% | 50.32% | 13 / 0.03% | 17 | 2 | 1 | NO | prediction_turnover_max_050: Selected observation rate exceeds configured turnover cap. ; prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |
| 97cb2d6393e395a27ea5cec3 | bear | 10 | hist_gradient_boosting | CANDIDATE | 41884 | 16800 | 17069 | 718 | 4.21% | 2.034 | 6 | 71.46% | 0.248393 | 0.249630 | 0.004954 | 0.689925 | 0.103809 | 1.335533 | 0.052560 | 0.052065 | 0.086594 | 0.107856 | 3.03% | 1.15% | 2.20% | 57.80% | 2.177 | -99.84% | 26.93% | 12.97% | -38.69% | 97.16% | 2.109 | 26.74% | 49.72% | 100.00% | 58.38% | 55 / 0.11% | 18 | 1 | 1 | NO | prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |
| bb6519f162ca75ba211549de | bear | 10 | logistic_regression | CANDIDATE | 41884 | 16800 | 17069 | 2049 | 12.00% | 4.543 | 8 | 91.30% | 0.243674 | 0.249630 | 0.023860 | 0.705906 | -0.008970 | 0.662622 | 0.051642 | 0.052432 | 0.086635 | 0.133485 | 4.49% | 3.10% | 4.00% | 66.72% | 3.028 | -100.00% | 137.68% | 54.70% | -48.04% | 99.80% | 3.797 | 16.79% | 33.67% | 100.00% | 49.70% | 120 / 0.23% | 18 | 1 | 1 | NO | prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |
| d5560f3bf8c44135d0700ee1 | bull | 10 | extra_trees | CANDIDATE | 41884 | 16800 | 17069 | 11407 | 66.83% | 23.091 | 29 | 100.00% | 0.244704 | 0.249697 | 0.019994 | 0.682500 | -0.102896 | 1.480881 | 0.035887 | 0.051780 | 0.082506 | 0.097872 | 1.05% | 0.65% | 0.93% | 56.88% | 1.594 | -100.00% | 186.45% | 69.96% | -34.63% | 100.00% | 3.570 | 4.01% | 10.93% | 100.00% | 50.38% | 3 / 0.01% | 17 | 2 | 1 | NO | prediction_turnover_max_050: Selected observation rate exceeds configured turnover cap. ; prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |
| ee38240015f84c64b24686e2 | bear | 10 | extra_trees | CANDIDATE | 41884 | 16800 | 17069 | 1668 | 9.77% | 3.740 | 8 | 90.28% | 0.244796 | 0.249630 | 0.019366 | 0.682747 | 0.091439 | 1.364946 | 0.046404 | 0.052642 | 0.086525 | 0.102132 | 3.39% | 1.72% | 2.90% | 63.73% | 2.811 | -99.92% | 169.29% | 64.92% | -28.98% | 99.60% | 2.904 | 21.46% | 50.18% | 100.00% | 50.02% | 39 / 0.08% | 18 | 1 | 1 | NO | prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |
| f19f87c9190893dea0466180 | bull | 10 | naive_base_rate | CANDIDATE | 41884 | 16800 | 17069 | 0 | 0.00% | 0.000 | 0 | 0.00% | 0.249534 | 0.249534 | 0.000000 | 0.692215 | 0.093606 | 0.012701 | 0.035827 | 0.050758 | 0.081593 | 0.166280 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | Infinity | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 26 / 0.05% | 11 | 2 | 1 | NO | not_naive_control: Naive controls are never promotion eligible. ; prediction_out_of_distribution_absent: At least one regression prediction exceeds train-only robust target quantiles. ; selection_rate_policy_configured: No user-approved selection-rate maximum is configured. |

## 6. Complete Gate Audit
- Complete gate CSV: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/gate_audit.csv`
- Complete gate JSON: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/gate_audit.json`
- Canonical gate row count: `158`
- Failed/not-configured mandatory gates:
| model_id | failed mandatory gates | not configured mandatory gates | promotion eligible |
| --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | prediction_turnover_max_050, prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
| 3d99c3f3540b6eb30ac52513 | not_naive_control, prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
| 790ac0b2f82362ac8df5a72e | prediction_turnover_max_050, prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
| 97cb2d6393e395a27ea5cec3 | prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
| bb6519f162ca75ba211549de | prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
| d5560f3bf8c44135d0700ee1 | prediction_turnover_max_050, prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
| ee38240015f84c64b24686e2 | prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
| f19f87c9190893dea0466180 | not_naive_control, prediction_out_of_distribution_absent | selection_rate_policy_configured | NO |
- Verification of shared persisted gate use: dashboard Model Registry, Discovery Lab, CLI audit, exports, and promotion checks use persisted `gate_results_json`. Scanner actionability currently relies on registry state and is listed as a MEDIUM finding because it should also re-check persisted gate eligibility.

## 7. Portfolio Drawdown Audit
- Previous near--100% drawdown root cause: selected cross-sectional model rows were compounded as sequential full-capital trades with `(1 + selected_return).cumprod()` across symbols and same-date rows. That invalid sequence is now retained only as `selected_row_sequence_drawdown`.
- Current portfolio maximum drawdown source: `portfolio_max_drawdown`, from chronological daily portfolio equity exported in each model metric.
- Rows from multiple symbols on the same date are not compounded as full-capital sequential trades for portfolio drawdown. However, same-date candidate selection is still processed row-by-row, not as an explicit date batch; see MEDIUM finding.
| model_id | legacy_old_drawdown | selected_row_sequence_drawdown | portfolio_max_drawdown | portfolio_total_return | daily_equity_start | daily_equity_end | lowest_equity_value | maximum_concurrent_positions | maximum_gross_exposure | maximum_net_exposure | position_sizing_method | transaction_costs_bps | slippage_bps | holding_horizon | per_date_candidate_limit | per_symbol_limit | sector_limit | ambiguity_policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | NOT PRESERVED | -1.0 | -0.41506953205059827 | 1.4790265027436384 | 0.9951463403661391 | 2.4790265027436384 | 0.6962292324057341 | 5 | 1.0 | 1.0 | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |
| 3d99c3f3540b6eb30ac52513 | NOT PRESERVED | nan | nan | None | nan | nan | nan | 5 | nan | nan | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |
| 790ac0b2f82362ac8df5a72e | NOT PRESERVED | -1.0 | -0.2783162166617723 | 2.301428902270187 | 1.0123620511985825 | 3.301428902270187 | 0.9765796034300469 | 5 | 1.0 | 1.0 | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |
| 97cb2d6393e395a27ea5cec3 | NOT PRESERVED | -0.9983582022851835 | -0.386863682298363 | 0.26934714584788666 | 1.0016379553798362 | 1.2693471458478867 | 0.7612689906457213 | 5 | 1.0 | 1.0 | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |
| bb6519f162ca75ba211549de | NOT PRESERVED | -0.9999980964109273 | -0.4803799127128938 | 1.376774127501887 | 0.9978906954193969 | 2.376774127501887 | 0.7045373900744796 | 5 | 1.0 | 1.0 | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |
| d5560f3bf8c44135d0700ee1 | NOT PRESERVED | -1.0 | -0.34632673677362 | 1.8645246299907847 | 1.0076980875132764 | 2.8645246299907847 | 0.9588483767116909 | 5 | 1.0 | 1.0 | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |
| ee38240015f84c64b24686e2 | NOT PRESERVED | -0.9991926602337642 | -0.28984518294663975 | 1.6929445155297143 | 1.00428540755599 | 2.6929445155297143 | 0.9613060984479653 | 5 | 1.0 | 1.0 | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |
| f19f87c9190893dea0466180 | NOT PRESERVED | nan | nan | None | nan | nan | nan | 5 | nan | nan | equal_weight | 5.0 | 2.0 | 10 | NOT CONFIGURED | 1 | 0.5 | conservative stop first |

## 8. Research-Date Audit
- raw_data_first_date: `2006-08-03`
- feature_warmup_first_date: `2006-08-03`
- first_generated_feature_date: `2006-08-03`
- first_model_eligible_observation_date: `2016-06-20`
- final_model_eligible_observation_date: `2026-06-04`
- first_label_date: `2006-08-03`
- final_label_date: `2026-06-18`
- train_start: `2016-06-20`
- train_end: `2022-04-28`
- calibration_start: `2022-05-13`
- calibration_end: `2024-04-17`
- holdout_start: `2024-05-02`
- holdout_end: `2026-04-22`
| statement | status | evidence |
| --- | --- | --- |
| Data before 2016-06-20 used only for feature warm-up | PASS | raw starts 2006-08-03; eligible starts 2016-06-20 |
| No training observation before 2016-06-20 | PASS | train_start=2016-06-20 |
| No calibration observation before 2016-06-20 | PASS | calibration_start=2022-05-13 |
| No holdout observation before 2016-06-20 | PASS | holdout_start=2024-05-02 |
| No label extends beyond 2026-06-18 | PASS | max eligible label_end_date_10=2026-06-18 |
| Scanner snapshots are not restricted by historical label availability | PASS | latest scanner as_of=2026-06-18, research_end=2026-06-18 |

## 9. Selection-Policy Audit
- Selection-policy CSV: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/selection_policy.csv`
- Current selected-rate ceiling: NOT CONFIGURED for every latest model.
- PROMOTION BLOCKED: MANDATORY SELECTION POLICY NOT CONFIGURED
- Bullish broad coverage remains present in the latest generation: ExtraTrees 66.83%, HistGradientBoosting 69.61%, LogisticRegression 76.55%. Reason: frozen selection policy only requires calibrated probability >= 0.55 and does not configure top-N, expected-return, target-before-stop, per-date, liquidity, or selected-rate ceiling gates for discovery evaluation.
| model_id | probability_threshold | expected_return_threshold | target_before_stop_threshold | top_n_limit | per_date_limit | liquidity_requirement | direction | horizon | tie_breaking_rule | selected_rate_ceiling | selected_rate_ceiling_configured | selected_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | 0.55 | None | None | None | None | None | bull | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.7654812818559963 |
| 3d99c3f3540b6eb30ac52513 | 0.55 | None | None | None | None | None | bear | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.0 |
| 790ac0b2f82362ac8df5a72e | 0.55 | None | None | None | None | None | bull | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.6961157654226962 |
| 97cb2d6393e395a27ea5cec3 | 0.55 | None | None | None | None | None | bear | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.04206456148573437 |
| bb6519f162ca75ba211549de | 0.55 | None | None | None | None | None | bear | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.1200421817329662 |
| d5560f3bf8c44135d0700ee1 | 0.55 | None | None | None | None | None | bull | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.6682875388130529 |
| ee38240015f84c64b24686e2 | 0.55 | None | None | None | None | None | bear | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.0977210147050208 |
| f19f87c9190893dea0466180 | 0.55 | None | None | None | None | None | bull | 10 | composite_utility_score_desc_then_symbol | NOT CONFIGURED | False | 0.0 |

## 10. Brier and Calibration Audit
- Configured minimum Brier skill gate: Brier skill score > 0.0. This is code-defaulted in `src/swing_rsi/engine/models.py`, not a user-approved material-improvement threshold.
- Models with trivial improvement: bear HistGradientBoosting BSS 0.004954, bull HistGradientBoosting BSS 0.007300. These are not described as material.
- Models worse than naive in the latest generation: none among non-naive families; naive controls are not promotion eligible.
| model_id | family | model_brier | naive_brier | abs_improvement | rel_improvement | BSS | cal_brier | holdout_brier | ECE | assessment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | logistic_regression | 0.243684 | 0.249697 | 0.006012 | 2.408% | 0.024079 | 0.247102 | 0.243684 | 0.044125 | better than naive, still blocked by other mandatory gates |
| 3d99c3f3540b6eb30ac52513 | naive_base_rate | 0.249440 | 0.249440 | 0.000000 | 0.000% | 0.000000 | 0.248741 | 0.249440 | 0.035652 | naive control; not promotion eligible |
| 790ac0b2f82362ac8df5a72e | hist_gradient_boosting | 0.247874 | 0.249697 | 0.001823 | 0.730% | 0.007300 | 0.247702 | 0.247874 | 0.052997 | trivially better than naive |
| 97cb2d6393e395a27ea5cec3 | hist_gradient_boosting | 0.248393 | 0.249630 | 0.001237 | 0.495% | 0.004954 | 0.247802 | 0.248393 | 0.052560 | trivially better than naive |
| bb6519f162ca75ba211549de | logistic_regression | 0.243674 | 0.249630 | 0.005956 | 2.386% | 0.023860 | 0.247042 | 0.243674 | 0.051642 | better than naive, still blocked by other mandatory gates |
| d5560f3bf8c44135d0700ee1 | extra_trees | 0.244704 | 0.249697 | 0.004992 | 1.999% | 0.019994 | 0.246816 | 0.244704 | 0.035887 | better than naive, still blocked by other mandatory gates |
| ee38240015f84c64b24686e2 | extra_trees | 0.244796 | 0.249630 | 0.004834 | 1.937% | 0.019366 | 0.246707 | 0.244796 | 0.046404 | better than naive, still blocked by other mandatory gates |
| f19f87c9190893dea0466180 | naive_base_rate | 0.249534 | 0.249534 | 0.000000 | 0.000% | 0.000000 | 0.248853 | 0.249534 | 0.035827 | naive control; not promotion eligible |

Probability decile table:
| model_id | decile | count | predicted_probability | realized_rate | absolute_error |
| --- | --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | 1 | 1707 | 0.412172 | 0.304628 | 0.107544 |
| 0163f5f828e82b49400c5088 | 2 | 1707 | 0.476109 | 0.412419 | 0.063689 |
| 0163f5f828e82b49400c5088 | 3 | 1707 | 0.538440 | 0.548916 | 0.010477 |
| 0163f5f828e82b49400c5088 | 4 | 1707 | 0.554403 | 0.530170 | 0.024233 |
| 0163f5f828e82b49400c5088 | 5 | 1707 | 0.556043 | 0.551845 | 0.004198 |
| 0163f5f828e82b49400c5088 | 6 | 1706 | 0.557204 | 0.482415 | 0.074789 |
| 0163f5f828e82b49400c5088 | 7 | 1707 | 0.557204 | 0.593439 | 0.036234 |
| 0163f5f828e82b49400c5088 | 8 | 1707 | 0.557453 | 0.590510 | 0.033057 |
| 0163f5f828e82b49400c5088 | 9 | 1707 | 0.558017 | 0.636204 | 0.078186 |
| 0163f5f828e82b49400c5088 | 10 | 1707 | 0.596442 | 0.587581 | 0.008861 |
| 3d99c3f3540b6eb30ac52513 | 1 | 1707 | 0.464524 | 0.449912 | 0.014612 |
| 3d99c3f3540b6eb30ac52513 | 2 | 1707 | 0.464524 | 0.456942 | 0.007582 |
| 3d99c3f3540b6eb30ac52513 | 3 | 1707 | 0.464524 | 0.454599 | 0.009925 |
| 3d99c3f3540b6eb30ac52513 | 4 | 1707 | 0.464524 | 0.535442 | 0.070918 |
| 3d99c3f3540b6eb30ac52513 | 5 | 1707 | 0.464524 | 0.538371 | 0.073848 |
| 3d99c3f3540b6eb30ac52513 | 6 | 1706 | 0.464524 | 0.385111 | 0.079412 |
| 3d99c3f3540b6eb30ac52513 | 7 | 1707 | 0.464524 | 0.446983 | 0.017541 |
| 3d99c3f3540b6eb30ac52513 | 8 | 1707 | 0.464524 | 0.492091 | 0.027568 |
| 3d99c3f3540b6eb30ac52513 | 9 | 1707 | 0.464524 | 0.476860 | 0.012336 |
| 3d99c3f3540b6eb30ac52513 | 10 | 1707 | 0.464524 | 0.507323 | 0.042799 |
| 790ac0b2f82362ac8df5a72e | 1 | 1707 | 0.447304 | 0.419449 | 0.027854 |
| 790ac0b2f82362ac8df5a72e | 2 | 1707 | 0.520891 | 0.474517 | 0.046374 |
| 790ac0b2f82362ac8df5a72e | 3 | 1707 | 0.535628 | 0.483890 | 0.051738 |
| 790ac0b2f82362ac8df5a72e | 4 | 1707 | 0.549699 | 0.560633 | 0.010934 |
| 790ac0b2f82362ac8df5a72e | 5 | 1707 | 0.550082 | 0.561219 | 0.011136 |
| 790ac0b2f82362ac8df5a72e | 6 | 1706 | 0.550082 | 0.397421 | 0.152661 |
| 790ac0b2f82362ac8df5a72e | 7 | 1707 | 0.550082 | 0.669010 | 0.118928 |
| 790ac0b2f82362ac8df5a72e | 8 | 1707 | 0.550082 | 0.541301 | 0.008782 |
| 790ac0b2f82362ac8df5a72e | 9 | 1707 | 0.550082 | 0.512009 | 0.038073 |
| 790ac0b2f82362ac8df5a72e | 10 | 1707 | 0.555081 | 0.618629 | 0.063548 |
| 97cb2d6393e395a27ea5cec3 | 1 | 1707 | 0.449730 | 0.414177 | 0.035553 |
| 97cb2d6393e395a27ea5cec3 | 2 | 1707 | 0.449730 | 0.414763 | 0.034967 |
| 97cb2d6393e395a27ea5cec3 | 3 | 1707 | 0.449730 | 0.584066 | 0.134336 |
| 97cb2d6393e395a27ea5cec3 | 4 | 1707 | 0.449730 | 0.343878 | 0.105852 |
| 97cb2d6393e395a27ea5cec3 | 5 | 1707 | 0.449730 | 0.427651 | 0.022079 |
| 97cb2d6393e395a27ea5cec3 | 6 | 1706 | 0.449730 | 0.458382 | 0.008652 |
| 97cb2d6393e395a27ea5cec3 | 7 | 1707 | 0.450471 | 0.519039 | 0.068569 |
| 97cb2d6393e395a27ea5cec3 | 8 | 1707 | 0.469181 | 0.513767 | 0.044586 |
| 97cb2d6393e395a27ea5cec3 | 9 | 1707 | 0.470513 | 0.509080 | 0.038567 |
| 97cb2d6393e395a27ea5cec3 | 10 | 1707 | 0.526464 | 0.558875 | 0.032411 |
| bb6519f162ca75ba211549de | 1 | 1707 | 0.429157 | 0.356766 | 0.072391 |
| bb6519f162ca75ba211549de | 2 | 1707 | 0.440256 | 0.445811 | 0.005556 |
| bb6519f162ca75ba211549de | 3 | 1707 | 0.440256 | 0.483890 | 0.043634 |
| bb6519f162ca75ba211549de | 4 | 1707 | 0.440256 | 0.305214 | 0.135042 |
| bb6519f162ca75ba211549de | 5 | 1707 | 0.440256 | 0.474517 | 0.034261 |
| bb6519f162ca75ba211549de | 6 | 1706 | 0.441696 | 0.490621 | 0.048926 |
| bb6519f162ca75ba211549de | 7 | 1707 | 0.445257 | 0.451670 | 0.006413 |
| bb6519f162ca75ba211549de | 8 | 1707 | 0.460348 | 0.478617 | 0.018269 |
| bb6519f162ca75ba211549de | 9 | 1707 | 0.519500 | 0.588166 | 0.068666 |
| bb6519f162ca75ba211549de | 10 | 1707 | 0.585166 | 0.668424 | 0.083258 |
| d5560f3bf8c44135d0700ee1 | 1 | 1707 | 0.406152 | 0.355009 | 0.051143 |
| d5560f3bf8c44135d0700ee1 | 2 | 1707 | 0.488005 | 0.422964 | 0.065041 |
| d5560f3bf8c44135d0700ee1 | 3 | 1707 | 0.524596 | 0.477446 | 0.047150 |
| d5560f3bf8c44135d0700ee1 | 4 | 1707 | 0.546625 | 0.526655 | 0.019970 |
| d5560f3bf8c44135d0700ee1 | 5 | 1707 | 0.555145 | 0.519625 | 0.035520 |
| d5560f3bf8c44135d0700ee1 | 6 | 1706 | 0.555145 | 0.548066 | 0.007079 |
| d5560f3bf8c44135d0700ee1 | 7 | 1707 | 0.561607 | 0.572935 | 0.011328 |
| d5560f3bf8c44135d0700ee1 | 8 | 1707 | 0.562333 | 0.593439 | 0.031106 |
| d5560f3bf8c44135d0700ee1 | 9 | 1707 | 0.562477 | 0.636204 | 0.073726 |
| d5560f3bf8c44135d0700ee1 | 10 | 1707 | 0.569035 | 0.585823 | 0.016788 |
| ee38240015f84c64b24686e2 | 1 | 1707 | 0.414071 | 0.373169 | 0.040902 |
| ee38240015f84c64b24686e2 | 2 | 1707 | 0.440906 | 0.448740 | 0.007835 |
| ee38240015f84c64b24686e2 | 3 | 1707 | 0.440906 | 0.492677 | 0.051771 |
| ee38240015f84c64b24686e2 | 4 | 1707 | 0.440906 | 0.301699 | 0.139207 |
| ee38240015f84c64b24686e2 | 5 | 1707 | 0.440906 | 0.496778 | 0.055872 |
| ee38240015f84c64b24686e2 | 6 | 1706 | 0.443851 | 0.442556 | 0.001296 |
| ee38240015f84c64b24686e2 | 7 | 1707 | 0.444444 | 0.442296 | 0.002148 |
| ee38240015f84c64b24686e2 | 8 | 1707 | 0.473727 | 0.514353 | 0.040626 |
| ee38240015f84c64b24686e2 | 9 | 1707 | 0.518654 | 0.591095 | 0.072441 |
| ee38240015f84c64b24686e2 | 10 | 1707 | 0.588391 | 0.640305 | 0.051914 |
| f19f87c9190893dea0466180 | 1 | 1707 | 0.533869 | 0.547745 | 0.013876 |
| f19f87c9190893dea0466180 | 2 | 1707 | 0.533869 | 0.542472 | 0.008603 |
| f19f87c9190893dea0466180 | 3 | 1707 | 0.533869 | 0.542472 | 0.008603 |
| f19f87c9190893dea0466180 | 4 | 1707 | 0.533869 | 0.462800 | 0.071069 |
| f19f87c9190893dea0466180 | 5 | 1707 | 0.533869 | 0.460457 | 0.073412 |
| f19f87c9190893dea0466180 | 6 | 1706 | 0.533869 | 0.613130 | 0.079261 |
| f19f87c9190893dea0466180 | 7 | 1707 | 0.533869 | 0.552431 | 0.018562 |
| f19f87c9190893dea0466180 | 8 | 1707 | 0.533869 | 0.506151 | 0.027718 |
| f19f87c9190893dea0466180 | 9 | 1707 | 0.533869 | 0.519625 | 0.014244 |
| f19f87c9190893dea0466180 | 10 | 1707 | 0.533869 | 0.490920 | 0.042949 |

## 11. Prediction Magnitude and OOD Audit
- Unit contract: decimal returns; `0.05` means 5%.
- Bullish labels: forward return = horizon close / next open - 1; MFE = future high / next open - 1; MAE = future low / next open - 1.
- Bearish labels: forward return = next open / horizon close - 1; MFE = next open / future low - 1; MAE = next open / future high - 1.
- Clipping/bounded transform: none for regression predictions; raw and transformed values are identical and stored separately. OOD bounds use training-only q01/q99 target ranges.
- Current prediction sanity CSV: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/prediction_sanity.csv`
- SOXL bearish extreme row status:
| scan_id | artifact | model_id | model_state | expected_return_raw | expected_return_display | expected_mfe_raw | expected_mfe_display | expected_mae_raw | expected_mae_display | return_train_min/max | return_train_q01/q05/q50/q95/q99 | mfe_train_q99 | mae_train_q01 | OOD flags | status | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1401ad50283ab923c5c85b9c | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/1401ad50283ab923c5c85b9c_scanner.csv | bec08149ba24c3952b521480 | CANDIDATE | 0.290930 | 29.09% | 0.856482 | 85.65% | -0.357388 | -35.74% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 1401ad50283ab923c5c85b9c | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/1401ad50283ab923c5c85b9c_scanner.csv | f2cfece679d2b8239adc570d | CANDIDATE | 0.290930 | 29.09% | 0.856482 | 85.65% | -0.357388 | -35.74% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 290a4f850dbb93d567e3b918 | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/290a4f850dbb93d567e3b918_scanner.csv | 7c8c35398ba7831e34b99143 | None | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | ACTIONABLE_PAPER_CANDIDATE | nan |
| 290a4f850dbb93d567e3b918 | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/290a4f850dbb93d567e3b918_scanner.csv | 362b9c7cf9213fb1f195e2c2 | None | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | ACTIONABLE_PAPER_CANDIDATE | nan |
| 290a4f850dbb93d567e3b918 | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/290a4f850dbb93d567e3b918_scanner.csv | 74298fe2e5c138aef7f9ae3a | None | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | probability_below_threshold |
| 72c827f555d0992da1c85d4c | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/72c827f555d0992da1c85d4c_scanner.csv | 7c8c35398ba7831e34b99143 | CANDIDATE | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 72c827f555d0992da1c85d4c | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/72c827f555d0992da1c85d4c_scanner.csv | 362b9c7cf9213fb1f195e2c2 | CANDIDATE | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 72c827f555d0992da1c85d4c | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/72c827f555d0992da1c85d4c_scanner.csv | 74298fe2e5c138aef7f9ae3a | CANDIDATE | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 8e63cc0bbc6242eb5b38856e | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/8e63cc0bbc6242eb5b38856e_scanner.csv | cf2a851af2d1ff92f3e9ad80 | CANDIDATE | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 8e63cc0bbc6242eb5b38856e | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/8e63cc0bbc6242eb5b38856e_scanner.csv | 7c8c35398ba7831e34b99143 | CANDIDATE | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 8e63cc0bbc6242eb5b38856e | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/8e63cc0bbc6242eb5b38856e_scanner.csv | fd62c772eaac1ab1fbc5f7c0 | CANDIDATE | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
| 8e63cc0bbc6242eb5b38856e | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/8e63cc0bbc6242eb5b38856e_scanner.csv | 362b9c7cf9213fb1f195e2c2 | CANDIDATE | 0.225974 | 22.60% | 0.824221 | 82.42% | -0.391191 | -39.12% | NOT AVAILABLE / NOT AVAILABLE | NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE/NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | ret=None, mfe=None, mae=None | REJECTED | model_not_promoted_or_quality_gates_failed |
- Root cause: confirmed as leveraged-ETF tail/extrapolation plus review-mode candidate use, not a decimal/percent unit bug and not a bearish sign-convention bug. Current logic flags OOD when predictions exceed train-only robust target quantiles; it does not suppress or clip the value.

## 12. Feature-Family Audit
- Feature-family diagnostics CSV: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/feature_family_diagnostics.csv`
Generated feature counts by family:
| family | generated_count |
| --- | --- |
| breadth | 6 |
| candle_geometry | 8 |
| inverse_leveraged | 12 |
| market_relative | 20 |
| regime | 3 |
| relationship_graph | 60 |
| returns_momentum | 29 |
| rsi_family | 294 |
| sector_relative | 8 |
| technical_primitives | 29 |
| trend_structure | 32 |
| volatility_range | 16 |
| volume_participation | 11 |
RSI selected/importance diagnostic by latest model:
| model_id | RSI selected | selected total | RSI selected % | RSI perm share |
| --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | 4 | 60 | 6.67% | 0.00% |
| 3d99c3f3540b6eb30ac52513 | 3 | 60 | 5.00% | NOT AVAILABLE |
| 790ac0b2f82362ac8df5a72e | 4 | 60 | 6.67% | 0.00% |
| 97cb2d6393e395a27ea5cec3 | 3 | 60 | 5.00% | 0.00% |
| bb6519f162ca75ba211549de | 3 | 60 | 5.00% | 0.00% |
| d5560f3bf8c44135d0700ee1 | 4 | 60 | 6.67% | 0.00% |
| ee38240015f84c64b24686e2 | 3 | 60 | 5.00% | 0.00% |
| f19f87c9190893dea0466180 | 4 | 60 | 6.67% | NOT AVAILABLE |
- Total generated RSI-family features: `294`
- Current finding: RSI has the largest generated family count, but latest selected-feature counts are spread across families. The generated count alone does not prove RSI dominates model behavior. Top attribution in current scanner artifacts is mixed and residual/volatility/trend-heavy depending on candidate.

## 13. Scanner State
- Scanner state CSV: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/scanner_state.csv`
| scan_id | created_at_utc | market_as_of_date | feature_snapshot_hash | model_ids_json | row_count_db | row_count_csv | bullish_rows | bearish_rows | actionable_rows | rejected_rows | candidate_statuses | rejection_reasons | model_states | csv_path | parquet_path | metadata_json |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6bf9b09ea1930cddcb4ad4cb | 2026-06-20T19:25:02.871221+00:00 | 2026-06-18 | 3efa428fbd1e6d2db906aaad | ["0163f5f828e82b49400c5088","3d99c3f3540b6eb30ac52513","790ac0b2f82362ac8df5a72e","97cb2d6393e395a27ea5cec3","bb6519f162ca75ba211549de","d5560f3bf8c44135d0700ee1","ee38240015f84c64b24686e2","f19f87c9190893dea0466180"] | 50 | 50 | 25 | 25 | 0 | 50 | {"REJECTED": 50} | {"model_not_promoted_or_quality_gates_failed": 50} | {"CANDIDATE": 50} | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/6bf9b09ea1930cddcb4ad4cb_scanner.csv | /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/scanner/6bf9b09ea1930cddcb4ad4cb_scanner.parquet | {"minimum_dollar_volume":5000000.0,"probability_threshold":0.55,"top_n_per_direction":25} |
- Scanner mode: current latest snapshot used CANDIDATE models in review mode; every row is rejected, so there are no actionable paper signals.

## 14. Paper Forward-Test State
- Forward state CSV: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/forward_state.csv`
| total_events | event_counts | pending_entries | open_positions | closed_positions | rejected_signals | latest_event_timestamp | latest_processed_market_date | model_ids_represented | duplicate_event_ids | duplicate_unique_keys | append_only_evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 285 | {"ENTRY_PENDING": 35, "SIGNAL_CREATED": 35, "SIGNAL_REJECTED": 215} | 35 | 0 | 0 | 215 | 2026-06-20T04:44:09.733590+00:00 | 2026-06-18 | ["0671a689a94a620a4bb8380e", "27f4594194dbc2f81d76b8ce", "2bfd1ba248c6f489efb31664", "342cf8a2d21a4bde57e65137", "362b9c7cf9213fb1f195e2c2", "3ae11a3532a1f98f0c72940f", "3ea62aea606decfc6949f58b", "45abf4961fdd454ac47b3f2f", "482f71d978c4650beb17495d", "53af0905715b3b3cfac257bd", "598deb3c6421068c5462d962", "5bfb45df712a9a78ddb7e79f", "708273ab1d1c6da2859d9c26", "74298fe2e5c138aef7f9ae3a", "774634752b24e4b914e59f2e", "7c8c35398ba7831e34b99143", "818dba0ea12dee222d3e217c", "81eb0d2483c8579fab58d9ef", "91f8a60f44337c75b6b299aa", "a748ec4a043487f15e8fc1a7", "cc6daf3fb5a9f971a3a43c2f", "cf2a851af2d1ff92f3e9ad80", "d0862047c7c558dc2f1cbdca", "d3e74e24f0dd2cae717f2107", "ec46faaa2ab40fc66d40b9cd", "f0b4c2433b868fc2fe4bc827", "fa98c0a3849a8bd3a281d915", "fbb4a81b062858abf0cf0fcc", "fd62c772eaac1ab1fbc5f7c0", "fed5b8e40985892722bfa661"] | 0 | 0 | forward_events has event_id primary key and unique_key unique constraint; source appends with INSERT OR IGNORE |
- Actual paper entry exists: NO. Reason if none: latest scanner rows are rejected review rows and no champion/challenger actionable model is deployed.
- Historical walk-forward validation is separate and was not used for this paper-forward state.

## 15. Model Registry and Promotion State
| state | count |
| --- | --- |
| EXPERIMENTAL | 0 |
| CANDIDATE | 46 |
| CHALLENGER | 0 |
| CHAMPION | 0 |
| RETIRED | 0 |
| REJECTED | 12 |
| model_id | state | mandatory_gate_failures | mandatory_not_configured | promotion_eligible | scanner_eligible | forward_test_eligible |
| --- | --- | --- | --- | --- | --- | --- |
| 0163f5f828e82b49400c5088 | CANDIDATE | 2 | 1 | NO | NO | NO |
| 3d99c3f3540b6eb30ac52513 | CANDIDATE | 2 | 1 | NO | NO | NO |
| 790ac0b2f82362ac8df5a72e | CANDIDATE | 2 | 1 | NO | NO | NO |
| 97cb2d6393e395a27ea5cec3 | CANDIDATE | 1 | 1 | NO | NO | NO |
| bb6519f162ca75ba211549de | CANDIDATE | 1 | 1 | NO | NO | NO |
| d5560f3bf8c44135d0700ee1 | CANDIDATE | 2 | 1 | NO | NO | NO |
| ee38240015f84c64b24686e2 | CANDIDATE | 1 | 1 | NO | NO | NO |
| f19f87c9190893dea0466180 | CANDIDATE | 2 | 1 | NO | NO | NO |
- Manual promotion bypass: NO CONFIRMED BYPASS. CLI `promote-model` calls `promote_model`, which blocks if persisted mandatory gates fail, are missing, NOT_CONFIGURED, or NOT_APPLICABLE.
- Automatic promotion bypass: NO CONFIRMED BYPASS. Discovery registers CANDIDATE unless all persisted gates pass; no current model is CHALLENGER or CHAMPION.

## 16. Dashboard State
| order | section |
| --- | --- |
| 1 | Overview |
| 2 | Data and Universe |
| 3 | Discovery Lab |
| 4 | Live Scanner |
| 5 | Candidate Attribution |
| 6 | Portfolio Backtests |
| 7 | Paper Forward Test |
| 8 | Model Registry |
| 9 | Baselines and Legacy RSI |
- Dashboard load verification: focused tests including `tests/test_dashboard_interactions.py` and `tests/test_dashboard_model_registry.py` passed in the current run.
- Discovery Lab displays portfolio-aware model metrics, Brier comparison, selection coverage, canonical gate failures, promotion eligibility, and research dates. Prediction OOD is available primarily in Model Registry drilldown, not the Discovery Lab summary.
- Model Registry displays compact screen-fitting rows plus drilldown tabs for gate audit, calibration, candidate selection, portfolio holdout, stability, feature diagnostics, prediction sanity, and artifact metadata.
- Missing/misleading/stale dashboard fields: generation-wide dashboard exports are not one-click; scanner eligibility should directly re-check canonical gate eligibility before actionable use; no stale result calculation was confirmed.

## 17. Security and Leakage Audit
| item | status | evidence |
| --- | --- | --- |
| .env ignored | PASS | git check-ignore includes .env |
| API key not printed | PASS | No command opened .env; tests use fake/test keys only. |
| API key not committed | PASS | tracked sensitive files excluding .gitkeep: none |
| raw data ignored | PASS | git check-ignore includes data/raw/AAPL.csv |
| processed features ignored | PASS | git check-ignore includes feature/processed parquet paths |
| model artifacts ignored | PASS | git check-ignore includes artifacts/models/x.joblib |
| SQLite state ignored | PASS | git check-ignore includes state/engine.sqlite3 |
| reports ignored | PASS | git check-ignore includes reports/current_state_audit/x.csv |
| no FMP calls in tests | PASS | Full tests passed; tests/test_fmp_provider.py injects fake http_get and dashboard smoke raises if FMP download is attempted. |
| no future feature leakage | PASS | tests/test_no_future_leakage.py and test_autonomous_engine future-row mutation checks passed. |
| no label columns in features | PASS | Feature parquet columns checked. |
| chronological train/calibration/holdout | PASS | 2016-06-20..2022-04-28 < 2022-05-13..2024-04-17 < 2024-05-02..2026-04-22 |
| overlapping labels purged | PASS | split purge uses label_end_date_10 before boundary; date audit passed max eligible label end. |
| train-only preprocessing | PASS | pipelines fit on split.train only in models.py lines 1133-1168. |
| separate calibration slice | PASS | calibrator fit on split.calibration only in models.py lines 1139-1144. |
| next-open execution | PASS | labels and portfolio use next-session Open; tests passed. |
| append-only forward events | PASS | forward_events primary/unique keys and no duplicates in current DB. |
| scanner uses latest completed session | PASS | latest scanner as_of=2026-06-18 |
| rejected candidates retained | PASS | latest rejected rows=50 |

## 18. Current Limitations
| classification | limitation |
| --- | --- |
| BLOCKS MODEL PROMOTION | Mandatory selection-rate policy is NOT_CONFIGURED for every latest model. |
| BLOCKS MODEL PROMOTION | Latest models have failed mandatory gates, especially prediction OOD and broad selection turnover for bullish models; naive controls also fail not_naive_control. |
| BLOCKS ACTIONABLE SCANNER SIGNALS | No CHAMPION or CHALLENGER model exists; latest scanner snapshot uses CANDIDATE models in review mode and rejects all rows. |
| BLOCKS PAPER FORWARD TRADES | No actionable scanner rows exist, so no ENTRY_PENDING or ENTRY_FILLED paper events are present. |
| RESEARCH LIMITATION | Current universe is a current configured universe and may contain survivorship bias; corporate-action and historical-universe semantics remain provider limitations. |
| RESEARCH LIMITATION | Brier skill gate only requires > 0.0 and is code-defaulted; no user-approved material improvement threshold is configured. |
| PERFORMANCE LIMITATION | Feature builder triggers pandas fragmentation warnings in tests. |
| UI LIMITATION | Dashboard lacks generation-wide one-click model audit exports. |
| DATA LIMITATION | Raw FMP daily data is present locally but provider corporate-action semantics are not independently verified in this audit. |
| FUTURE SCOPE | No options, intraday data, NLP, brokers, or live execution are implemented, by scope. |

## 19. Exact Next Step
Recommended next task: implement an explicit, user-approved candidate selection policy configuration and enforce it consistently in discovery evaluation, scanner eligibility, dashboard display, and promotion gates.
Why this is next: the current confirmed promotion blocker present on every latest model is `selection_rate_policy_configured = NOT_CONFIGURED`. Without this policy, broad-coverage bullish models can select 66% to 77% of holdout observations, and no model can be promoted honestly.
Acceptance criteria: define selection-rate ceiling, top-N/per-date limits, expected-return threshold, target-before-stop threshold, and liquidity gate in config; persist the policy hash with every model; re-run discovery without weakening existing gates; prove broad-coverage models fail when exceeding configured policy; prove scanner actionability requires both eligible state and persisted canonical gate eligibility; all verification commands pass.

## 20. Output Files
| path | exists |
| --- | --- |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/docs/CURRENT_AUTONOMOUS_ENGINE_STATE_AUDIT.md | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/model_summary.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/gate_audit.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/gate_audit.json | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/calibration.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/selection_policy.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/portfolio_metrics.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/prediction_sanity.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/feature_family_diagnostics.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/scanner_state.csv | True |
| /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/reports/current_state_audit/forward_state.csv | True |
- Generated CSV/JSON reports are under `reports/current_state_audit/`, which is Git-ignored. The Markdown audit under `docs/` is intentionally created per user request and is not ignored.
