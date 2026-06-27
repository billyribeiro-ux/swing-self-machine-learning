# Development Candidate Gate Triage

Date: 2026-06-27

Mode: read-only diagnosis of persisted development evidence. No models were retrained, no discovery/scanner/forward/final-holdout commands were run, and no operational state was modified.

## 1. Latest Development Generation

- Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`
- Development branch: `feat/product-class-specialist-challengers-v1`
- Development HEAD observed before report write: `8e2b40effab1332f474ca47d720fcb8c21ca4912`
- Latest generation ID: `2026-06-27T14:05:10.073173+00:00`
- Creation time: `2026-06-27T14:05:10.073173+00:00`
- Newer than `2026-06-26T23:52:15.769542+00:00`: yes
- Model count: 30 total, 20 learned and 10 naive controls
- Scopes: `POOLED`, `ORDINARY`, `INVERSE`, `LEVERAGED_LONG`, `LEVERAGED_INVERSE`
- Directions: `bull`, `bear`
- Families: `extra_trees`, `hist_gradient_boosting`, `naive_base_rate`
- Registry states: `CANDIDATE` only
- Promoted models in generation: none
- Development final-holdout runs: none
- Development forward events: none
- Development scanner snapshots already present before diagnosis: 3

The robust-transform evidence is present in the qualified model: `5b3f37a96a7968bca8d2f398` has `mae_path_target_transform=log1p`, `mae_path_target_transform_schema_version=robust_path_target_transform_v1`, and `mae_path_target_transform_hash=c3c93ddb06ea5504`.

## 2. Complete Model Gate Triage

`TBS skill*` is derived for triage from the persisted target-before-stop development-holdout Brier score versus the persisted development-holdout target-before-stop base-rate Brier. It is not a persisted canonical gate. The persisted canonical TBS metric is the TBS Brier score.

Evidence shorthand:

- `ER ev`: expected-return lower confidence bound / double-cost lower confidence bound / expected-return OOD rate.
- `MFE ev`: selected mean MFE / portfolio average MFE / MFE OOD rate.
- `MAE ev`: selected mean MAE / portfolio average MAE / MAE OOD rate / MAE transform.

| model ID | scope | dir | family | sel obs | sel rate | port ret | port DD | Brier skill | TBS skill* | TBS Brier | ER ev | MFE ev | MAE ev | failed development gates | failed final-holdout gates | promotion eligible | scanner eligible | final-holdout enrollment eligible |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|---|
| `77d1a8380d530a1948befacf` | INVERSE | bear | extra_trees | 20 | 2.05% | 5.37% | -3.36% | 0.0266 | -0.0931 | 0.2124 | 3.27% / 3.22% / 0.00% | 6.44% / 4.77% / 0.00% | -2.15% / -3.08% / 0.00% / none | `exceptional_period_concentration_max_060` | `final_holdout_required_for_promotion` | no | no | no |
| `c85c4b8dabb1b19555dd1928` | INVERSE | bear | hist_gradient_boosting | 0 | 0.00% | NA | NA | 0.0003 | -0.0602 | 0.2060 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `48dc86e812a26c0d472924c8` | INVERSE | bull | extra_trees | 0 | 0.00% | NA | NA | 0.0215 | 0.0154 | 0.1978 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `a8d580bda4ba9364f4ca9bc9` | INVERSE | bull | hist_gradient_boosting | 0 | 0.00% | NA | NA | -0.0064 | 0.0055 | 0.1998 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | Brier skill, EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `cc03f04f0532cca6ce5d39fd` | LEVERAGED_INVERSE | bear | extra_trees | 109 | 3.72% | 30.83% | -33.31% | 0.0058 | -0.1606 | 0.2126 | 13.69% / 13.64% / 0.00% | 24.23% / 14.15% / 0.00% | -7.99% / -9.41% / 0.00% / none | `exceptional_period_concentration_max_060` | `final_holdout_required_for_promotion` | no | no | no |
| `9618e114cade8b396bb1ec60` | LEVERAGED_INVERSE | bear | hist_gradient_boosting | 87 | 2.97% | 81.58% | -13.26% | -0.0064 | -0.0537 | 0.1930 | 10.96% / 10.91% / 0.00% | 21.88% / 19.66% / 0.00% | -4.55% / -4.67% / 0.00% / none | `brier_skill_vs_naive_positive`, `exceptional_period_concentration_max_060` | `final_holdout_required_for_promotion` | no | no | no |
| `74ed8ea5d70b10bdeb63a043` | LEVERAGED_INVERSE | bull | extra_trees | 0 | 0.00% | NA | NA | 0.0035 | 0.0002 | 0.1969 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `8d15b9846da1e3f7568cbdfa` | LEVERAGED_INVERSE | bull | hist_gradient_boosting | 7 | 0.24% | 0.79% | -2.45% | -0.0032 | -0.0108 | 0.1990 | -5.50% / -5.55% / 0.00% | 6.29% / 5.12% / 0.00% | -7.71% / -5.51% / 0.00% / none | Brier skill, EV, PF, symbol concentration, cost sensitivity, temporal stability, exceptional concentration | `final_holdout_required_for_promotion` | no | no | no |
| `6a5985f41c142955c12f455e` | LEVERAGED_LONG | bear | extra_trees | 0 | 0.00% | NA | NA | -0.1349 | 0.0162 | 0.1980 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | Brier skill, EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `7b2d5fa67aed8f0d6f1872e5` | LEVERAGED_LONG | bear | hist_gradient_boosting | 0 | 0.00% | NA | NA | 0.0017 | -0.0605 | 0.2135 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `7521f91e8dde523d189d29f8` | LEVERAGED_LONG | bull | extra_trees | 8 | 0.41% | 15.73% | -5.66% | -0.0817 | -0.0264 | 0.2139 | 6.93% / 6.88% / 0.00% | 19.03% / 17.44% / 0.00% | -4.93% / -2.79% / 0.00% / none | `brier_skill_vs_naive_positive`, `exceptional_period_concentration_max_060` | `final_holdout_required_for_promotion` | no | no | no |
| `d3912064315532441405d4cb` | LEVERAGED_LONG | bull | hist_gradient_boosting | 18 | 0.92% | 5.50% | -9.59% | 0.0006 | -0.0688 | 0.2228 | 1.23% / 1.18% / 0.00% | 14.13% / 11.96% / 0.00% | -7.34% / -10.69% / 0.00% / none | `exceptional_period_concentration_max_060` | `final_holdout_required_for_promotion` | no | no | no |
| `41609c0ebb5988420f1e0c55` | ORDINARY | bear | extra_trees | 0 | 0.00% | NA | NA | -0.0039 | -0.0332 | 0.1988 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | Brier skill, EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `1a78f1917154bd1e14b2872b` | ORDINARY | bear | hist_gradient_boosting | 1 | 0.01% | 0.80% | -2.16% | 0.0003 | -0.0162 | 0.1955 | 5.57% / 5.52% / 0.00% | 8.28% / 8.28% / 0.00% | -7.69% / -7.69% / 0.00% / none | symbol concentration, sector concentration, temporal stability unavailable, exceptional concentration | `final_holdout_required_for_promotion` | no | no | no |
| `36a05aec82d71c902ad3e873` | ORDINARY | bull | extra_trees | 67 | 0.60% | 41.41% | -8.30% | -0.0013 | -0.0493 | 0.2197 | 3.76% / 3.71% / 0.00% | 8.45% / 8.95% / 0.00% | -2.62% / -3.00% / 0.00% / none | `brier_skill_vs_naive_positive` | `final_holdout_required_for_promotion` | no | no | no |
| `e521f1bcffbbdc8047f6d183` | ORDINARY | bull | hist_gradient_boosting | 62 | 0.55% | 32.62% | -3.18% | 0.0023 | -0.0209 | 0.2137 | 2.05% / 2.00% / 0.00% | 8.05% / 7.09% / 0.00% | -3.91% / -2.54% / 0.00% / none | `exceptional_period_concentration_max_060` | `final_holdout_required_for_promotion` | no | no | no |
| `585a7d6fb397dc36f665d319` | POOLED | bear | extra_trees | 0 | 0.00% | NA | NA | 0.0176 | -0.0047 | 0.1930 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `1da4716cec063e1534c7dd87` | POOLED | bear | hist_gradient_boosting | 0 | 0.00% | NA | NA | 0.0047 | 0.0000 | 0.1921 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `c12b498bb164db0290168d0c` | POOLED | bull | extra_trees | 0 | 0.00% | NA | NA | 0.0165 | -0.0001 | 0.2068 | NA / NA / 0.00% | NA / NA / 0.00% | NA / NA / 0.00% / none | EV, PF, portfolio DD unavailable, symbol/sector concentration unavailable, cost sensitivity, temporal stability unavailable, exceptional concentration unavailable | `final_holdout_required_for_promotion` | no | no | no |
| `5b3f37a96a7968bca8d2f398` | POOLED | bull | hist_gradient_boosting | 96 | 0.56% | 35.39% | -8.46% | 0.0076 | -0.0159 | 0.2100 | 1.47% / 1.42% / 0.00% | 8.40% / 9.67% / 0.00% | -4.37% / -4.73% / 0.00% / log1p | none | `final_holdout_required_for_promotion` | no | no | yes |

### Development-quality blockers

Most common development-quality blockers among learned models:

- `exceptional_period_concentration_max_060`: 18 models.
- `symbol_concentration_max_050`: 12 models.
- `temporal_fold_stability_min_050`: 12 models.
- `positive_expected_value_after_costs`: 11 models.
- `profit_factor_min_090`: 11 models.
- `sector_concentration_max_080`: 11 models.
- `transaction_cost_sensitivity_not_collapsed`: 11 models.
- `temporal_fold_stability_evidence_available`: 11 models.
- `portfolio_drawdown_available`: 10 models.
- `portfolio_drawdown_not_worse_than_50pct`: 10 models.
- `brier_skill_vs_naive_positive`: 7 models.

The single most common development-quality blocker is exceptional-period concentration. The most severe practical blocker is selected-sample scarcity: 10 learned models selected zero rows, causing EV, profit-factor, portfolio-drawdown, temporal-stability, and concentration evidence to be unavailable.

### Final-holdout-only blockers

Every learned model fails exactly one mandatory final-holdout-only gate:

- `final_holdout_required_for_promotion`: 20 models.

No development model has prospective final-holdout sample evidence because no development final-holdout run exists.

## 3. Classification Of Every Learned Model

| model ID | classification | exact reason |
|---|---|---|
| `5b3f37a96a7968bca8d2f398` | DEVELOPMENT_QUALIFIED_PENDING_FINAL_HOLDOUT | All mandatory development-quality gates pass; only prospective final-holdout evidence blocks promotion. |
| `77d1a8380d530a1948befacf` | NEEDS_MODEL_CORRECTION | Only development blocker is exceptional-period concentration at 73.24%; selected sample exists but concentration must be corrected. |
| `cc03f04f0532cca6ce5d39fd` | NEEDS_MODEL_CORRECTION | Only development blocker is exceptional-period concentration at 60.12%, just above the 60% cap. |
| `9618e114cade8b396bb1ec60` | NEEDS_MODEL_CORRECTION | Fails Brier skill versus naive control and exceptional-period concentration at 90.34%; otherwise has selected evidence. |
| `d3912064315532441405d4cb` | NEEDS_MODEL_CORRECTION | Only development blocker is exceptional-period concentration at 68.82%; selected sample is small but nonzero. |
| `36a05aec82d71c902ad3e873` | NEEDS_MODEL_CORRECTION | Only development blocker is Brier skill versus naive control. |
| `e521f1bcffbbdc8047f6d183` | NEEDS_MODEL_CORRECTION | Only development blocker is exceptional-period concentration at 99.63%; positive-year fraction is also weak at 50%. |
| `7521f91e8dde523d189d29f8` | RESEARCH_ONLY | Useful leveraged-long bullish diagnostic, but not near-term: Brier skill fails, exceptional concentration is 78.47%, and only 8 rows are selected. |
| `8d15b9846da1e3f7568cbdfa` | RETIRE_CANDIDATE | Only 7 selected rows and fails Brier skill, EV, profit factor, symbol concentration, cost sensitivity, temporal stability, and exceptional concentration. |
| `1a78f1917154bd1e14b2872b` | RETIRE_CANDIDATE | Only 1 selected row with 100% symbol, sector, and exceptional-period concentration; evidence is too scarce. |
| `c85c4b8dabb1b19555dd1928` | RETIRE_CANDIDATE | Zero selected rows; trading, concentration, temporal, and portfolio evidence unavailable. |
| `48dc86e812a26c0d472924c8` | RETIRE_CANDIDATE | Zero selected rows; trading, concentration, temporal, and portfolio evidence unavailable. |
| `a8d580bda4ba9364f4ca9bc9` | RETIRE_CANDIDATE | Zero selected rows plus Brier skill failure; no actionable development evidence. |
| `74ed8ea5d70b10bdeb63a043` | RETIRE_CANDIDATE | Zero selected rows; trading, concentration, temporal, and portfolio evidence unavailable. |
| `6a5985f41c142955c12f455e` | RETIRE_CANDIDATE | Zero selected rows plus Brier skill failure; no actionable development evidence. |
| `7b2d5fa67aed8f0d6f1872e5` | RETIRE_CANDIDATE | Zero selected rows; trading, concentration, temporal, and portfolio evidence unavailable. |
| `41609c0ebb5988420f1e0c55` | RETIRE_CANDIDATE | Zero selected rows plus Brier skill failure; no actionable development evidence. |
| `585a7d6fb397dc36f665d319` | RETIRE_CANDIDATE | Zero selected rows; trading, concentration, temporal, and portfolio evidence unavailable. |
| `1da4716cec063e1534c7dd87` | RETIRE_CANDIDATE | Zero selected rows; trading, concentration, temporal, and portfolio evidence unavailable. |
| `c12b498bb164db0290168d0c` | RETIRE_CANDIDATE | Zero selected rows; trading, concentration, temporal, and portfolio evidence unavailable. |

## 4. Development-Qualified Challenger

One model is development-qualified pending prospective final holdout:

- Model ID: `5b3f37a96a7968bca8d2f398`
- Scope: `POOLED`
- Direction: `bull`
- Family: `hist_gradient_boosting`
- Why it qualifies: every mandatory development-quality gate passes, including Brier skill versus naive, EV after costs, profit factor, portfolio drawdown, feature stability, concentration, transaction-cost sensitivity, selection-rate policy, temporal stability, comparison-control availability, active path heads, domain integrity, and OOD Governance V2 gates.
- Selected sample count: 96 rows over 51 selected trading dates.
- Portfolio evidence: portfolio total return 35.39%, max drawdown -8.46%, portfolio trade count 40, portfolio profit factor 4.5132, portfolio average MFE 9.67%, portfolio average MAE -4.73%.
- Concentration evidence: symbol concentration 33.33%, sector concentration 63.54%, exceptional-period concentration 41.36%.
- OOD status: expected return, MFE, and MAE holdout OOD rates are all 0.00%; max severities are all 0.00 under `prediction_ood_governance_v2`.
- Temporal stability: 100% positive temporal-fold fraction with selected observations `[32,32,32]`.
- Exact final-holdout blockers remaining: `final_holdout_required_for_promotion`; no prospective final-holdout run or sample evidence exists in development.

This model is final-holdout-enrollment eligible by the persisted development-gate blocker logic, but it is not promotion eligible and not scanner/actionability eligible because it remains a `CANDIDATE` with `DEVELOPMENT_HOLDOUT` evidence only.

## 5. Top 5 Research-Triage Candidates

Ranking below is for research triage only. It is not a promotion ranking and does not use win rate alone.

| rank | model ID | strongest evidence | weakest evidence | failed gates | selected stability | concentration | OOD behavior | calibration | portfolio drawdown | continued development justified |
|---:|---|---|---|---|---|---|---|---|---:|---|
| 1 | `5b3f37a96a7968bca8d2f398` | Only learned model with all mandatory development gates passing; 96 selected rows; portfolio return 35.39%; PF 3.5714; robust MAE transform active. | TBS derived skill is negative (-0.0159); sector concentration is 63.54%; selected symbols lean heavily to TZA/RWM. | final-holdout only: `final_holdout_required_for_promotion`. | 51 dates; temporal counts `[32,32,32]`; temporal positive fraction 100%. | symbol 33.33%, sector 63.54%, exceptional 41.36%. | return/MFE/MAE OOD rates 0.00%. | primary Brier skill 0.0076; TBS Brier 0.2100; TBS calibrator identity. | -8.46% | yes, prepare challenger enrollment package. |
| 2 | `cc03f04f0532cca6ce5d39fd` | 109 selected rows; ER LCB 13.69%; portfolio return 30.83%; PF 69.2392; temporal counts `[37,36,36]`. | Exceptional-period concentration narrowly fails at 60.12%; portfolio DD is materially larger at -33.31%; TBS derived skill is -0.1606. | `exceptional_period_concentration_max_060`, final holdout. | 32 dates; temporal positive fraction 100%. | symbol 22.02%, sector 40.37%, exceptional 60.12%. | return/MFE/MAE OOD rates 0.00%. | primary Brier skill 0.0058; TBS Brier 0.2126; identity calibrator. | -33.31% | yes, but only after exceptional-period concentration correction. |
| 3 | `36a05aec82d71c902ad3e873` | 67 selected rows; portfolio return 41.41%; max drawdown -8.30%; PF 12.0038; concentration gates pass. | Primary Brier skill fails at -0.0013; TBS derived skill -0.0493. | `brier_skill_vs_naive_positive`, final holdout. | 23 dates; temporal counts `[23,22,22]`; temporal positive fraction 100%. | symbol 14.93%, sector 23.88%, exceptional 57.70%. | return/MFE/MAE OOD rates 0.00%. | primary Brier skill negative; TBS Brier 0.2197; identity calibrator. | -8.30% | yes, if predictive-skill correction is targeted. |
| 4 | `e521f1bcffbbdc8047f6d183` | 62 selected rows; portfolio return 32.62%; max drawdown -3.18%; PF 5.4589; Brier skill positive. | Exceptional-period concentration is severe at 99.63%; positive-year fraction is only 50%. | `exceptional_period_concentration_max_060`, final holdout. | 23 dates; temporal counts `[21,21,20]`; temporal positive fraction 100%. | symbol 12.90%, sector 19.35%, exceptional 99.63%. | return/MFE/MAE OOD rates 0.00%. | primary Brier skill 0.0023; TBS Brier 0.2137; identity calibrator. | -3.18% | yes only as a focused concentration-stability correction; otherwise research-only. |
| 5 | `77d1a8380d530a1948befacf` | Best primary Brier skill among top candidates at 0.0266; PF 60.0422; max drawdown -3.36%. | Only 20 selected rows; exceptional concentration 73.24%; symbol concentration is exactly at the 50% cap. | `exceptional_period_concentration_max_060`, final holdout. | 16 dates; temporal counts `[7,7,6]`; temporal positive fraction 100%. | symbol 50.00%, sector 50.00%, exceptional 73.24%. | return/MFE/MAE OOD rates 0.00%. | primary Brier skill 0.0266; TBS Brier 0.2124; identity calibrator. | -3.36% | yes, but sample breadth and exceptional concentration are the limiting issues. |

## 6. Current Best Development Candidate

- Full model ID: `5b3f37a96a7968bca8d2f398`
- Scope: `POOLED`
- Direction: `bull`
- Family: `hist_gradient_boosting`
- Generation ID: `2026-06-27T14:05:10.073173+00:00`
- Selected rows: 96
- Selected symbols: `TZA:32`, `RWM:29`, `NVDA:8`, `SH:5`, `XLF:3`, `TQQQ:2`, `XLK:2`, `AMZN:2`, `GOOGL:2`, `XLY:2`, `AAPL:1`, `TNA:1`, `UPRO:1`, `XLB:1`, `XLE:1`, `SOXL:1`, `MSFT:1`, `QID:1`, `SQQQ:1`
- Selected dates: 2024-05-14 through 2026-03-24, 51 unique selected trading dates
- Selected years: `2024:26`, `2025:30`, `2026:40`
- Selected regimes: `uptrend_low_vol:63`, `uptrend_high_vol:23`, `downtrend_high_vol:10`
- Selected sector groups: `inverse_small_caps:61`, `semiconductors:8`, `inverse_market:5`, `technology:4`, `consumer_discretionary:4`, `financials:3`, `leveraged_technology_growth:2`, `communication_services:2`, `inverse_technology_growth:2`, plus one each in `leveraged_small_caps`, `leveraged_market`, `materials`, `energy`, and `leveraged_semiconductors`
- Final-holdout-enrollment ready: yes
- Promotion eligible: no
- Scanner/actionability eligible: no
- Exact next step for this model: prepare a challenger enrollment package; do not enroll it yet.

Passed mandatory gates:

`minimum_training_samples`, `minimum_unseen_observations`, `brier_skill_vs_naive_positive`, `holdout_brier_max_035`, `positive_expected_value_after_costs`, `profit_factor_min_090`, `portfolio_drawdown_available`, `portfolio_drawdown_not_worse_than_50pct`, `feature_stability_mean_abs_z_max_250`, `symbol_concentration_max_050`, `sector_concentration_max_080`, `transaction_cost_sensitivity_not_collapsed`, `prediction_turnover_max_050`, `selection_rate_policy_configured`, `temporal_fold_stability_evidence_available`, `temporal_fold_stability_min_050`, `exceptional_period_concentration_max_060`, `comparison_controls_available`, `not_naive_control`, `prediction_ood_governance_schema_version`, `classification_prediction_values_finite`, `classification_prediction_probability_contract_valid`, `classification_prediction_unit_contract_valid`, `return_prediction_values_finite`, `return_prediction_unit_contract_valid`, `return_prediction_head_bound_mapping_valid`, `return_prediction_bounds_training_only`, `return_prediction_path_metric_sign_valid`, `return_calibration_ood_rate_acceptable`, `return_holdout_ood_rate_acceptable`, `return_holdout_ood_q99_severity_acceptable`, `return_catastrophic_prediction_extrapolation_absent`, `mfe_prediction_values_finite`, `mfe_prediction_unit_contract_valid`, `mfe_prediction_head_bound_mapping_valid`, `mfe_prediction_bounds_training_only`, `mfe_prediction_path_metric_sign_valid`, `mfe_required_path_head_active`, `mfe_magnitude_domain_integrity_valid`, `mfe_calibration_ood_rate_acceptable`, `mfe_holdout_ood_rate_acceptable`, `mfe_holdout_ood_q99_severity_acceptable`, `mfe_catastrophic_prediction_extrapolation_absent`, `mae_prediction_values_finite`, `mae_prediction_unit_contract_valid`, `mae_prediction_head_bound_mapping_valid`, `mae_prediction_bounds_training_only`, `mae_prediction_path_metric_sign_valid`, `mae_required_path_head_active`, `mae_magnitude_domain_integrity_valid`, `mae_calibration_ood_rate_acceptable`, `mae_holdout_ood_rate_acceptable`, `mae_holdout_ood_q99_severity_acceptable`, `mae_catastrophic_prediction_extrapolation_absent`.

Failed mandatory gates:

`final_holdout_required_for_promotion`: model holdout status is `DEVELOPMENT_HOLDOUT`; only `FINAL_HOLDOUT` models can be promoted.

## 7. Operational Run Check

Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

- Operational branch observed before report write: `feat/autonomous-swing-scanner-v1`
- Operational HEAD before report write: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Operational Git status before report write: clean
- Frozen run ID present: `3493ee8ac37bf96475c362e1`
- Frozen run status: `CREATED`
- Enrolled model ID: `b93b2258c10aea5cef81d291`
- Baseline date: `2026-06-25`
- Operational final-holdout events before report write: 0
- Operational scanner snapshots before report write: 17
- Operational forward events before report write: 285

No operational command that mutates state was run.

## 8. Exactly One Next Task

Prepare a challenger enrollment package for `5b3f37a96a7968bca8d2f398`; do not enroll it yet.

## 9. Read-Only State Audit

Before values captured before writing this report:

- Development Git status before: clean
- Development SQLite before: `state/engine.sqlite3|384835584|1782572906|Jun 27 11:08:26 2026`
- Representative artifact before: `artifacts/models/5b3f37a96a7968bca8d2f398.joblib|30710684|1782569726|Jun 27 10:15:26 2026`
- Development scanner snapshot count before: 3
- Development forward-event count before: 0
- Development final-holdout run count before: 0
- Operational HEAD before: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Operational Git status before: clean
- Operational final-holdout event count before: 0
- Operational scanner snapshot count before: 17
- Operational forward-event count before: 285

Observed after values for stateful artifacts after writing only this report:

- Development Git status after: `?? docs/DEVELOPMENT_CANDIDATE_GATE_TRIAGE.md`
- Development SQLite after: `state/engine.sqlite3|384835584|1782572906|Jun 27 11:08:26 2026`
- Representative artifact after: `artifacts/models/5b3f37a96a7968bca8d2f398.joblib|30710684|1782569726|Jun 27 10:15:26 2026`
- Development scanner snapshot count after: 3
- Development forward-event count after: 0
- Development final-holdout run count after: 0
- Operational HEAD after: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Operational Git status after: clean
- Operational final-holdout event count after: 0
- Operational scanner snapshot count after: 17
- Operational forward-event count after: 285

Confirmed scope and state outcomes:

- No source files changed.
- No model artifacts changed.
- No SQLite state changed.
- No scanner state changed.
- No forward state changed.
- No final-holdout state changed.
- No operational state changed.
