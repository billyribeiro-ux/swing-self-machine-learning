# Product-Class Specialist Challenger V1 Handoff

## Status
- Implementation completed in the development worktree only.
- Operational worktree was used only for read-only immutability verification.
- No FMP update, ordinary forward-update, daily-cycle, promotion, or prospective final-holdout initialization was run.
- Discovery was run exactly once in development after clean pre-discovery checks.
- Review-only scanner was run once in development; actionable rows were 0.

## Motivation
Prior diagnostics showed ordinary stocks/ordinary ETFs and leveraged/inverse ETFs have materially different path-return, MFE, MAE, OOD, and calibration behavior. This implementation creates challenger artifacts that filter target rows by governed product-class scope while retaining full-universe market context.

## Scope Mapping
- `POOLED`: all enabled governed symbols.
- `ORDINARY`: `stock`, `broad_market_etf`, `sector_etf`, `ordinary_etf`.
- `LEVERAGED_INVERSE`: `inverse_etf`, `leveraged_inverse_etf`, `leveraged_long_etf`.
- Mapping is role-based from `configs/universe/core.yaml`; production code does not classify by ticker-name heuristics.
- Unknown or ambiguous roles fail universe validation.

## Architecture
- Schema: `product_class_specialist_v1`.
- Discovery trains active nonlinear families only: `hist_gradient_boosting` and `extra_trees`.
- Trained heads per learned model: primary classifier, Target-Before-Stop classifier, expected-return regressor, MFE regressor, MAE regressor.
- Logistic specialist challengers are intentionally excluded because logistic MFE/MAE heads are retired.
- POOLED controls and per-scope naive controls were created where data sufficed.
- Scope-specific feature screens, calibrators, OOD bounds, preprocessors, and artifacts are independent.
- Full-universe context features remain available; only eligible target rows are filtered by scope.
- Scanner review routing rejects product-class scope mismatches with `product_class_scope_mismatch`; POOLED models may score all scopes.

## Commits
- `140874f` feat: add product class specialist model scopes
- `46c426b` test: validate product class isolation
- `84b7780` docs: document specialist challenger architecture

## Generation
- Generation ID: `2026-06-25T23:02:16.478522+00:00`
- Models registered: 18
- Learned nonlinear models: 12
- Naive controls: 6
- Challengers: 0
- Candidates needing review: 18
- Promoted models: 0
- Rejected/experimental: 0

### Learned Model IDs
| model_id | product_class_scope | family | direction | horizon | registry_state | training_count | calibration_count | development_holdout_count | mfe_path_head_capability_state | mae_path_head_capability_state | promotion_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5902be0760c859a9f94be5eb | LEVERAGED_INVERSE | extra_trees | bear | 10 | CANDIDATE | 14471 | 5799 | 5859 | ACTIVE | ACTIVE | False |
| 34484c2b2201af3659da3f20 | LEVERAGED_INVERSE | extra_trees | bull | 10 | CANDIDATE | 14471 | 5799 | 5859 | ACTIVE | ACTIVE | False |
| 4a54311203043e27e568cab4 | LEVERAGED_INVERSE | hist_gradient_boosting | bear | 10 | CANDIDATE | 14471 | 5799 | 5859 | ACTIVE | ACTIVE | False |
| 98dd966d1b0dde983e730fa6 | LEVERAGED_INVERSE | hist_gradient_boosting | bull | 10 | CANDIDATE | 14471 | 5799 | 5859 | ACTIVE | ACTIVE | False |
| d2da145c98bbe7c50315524f | ORDINARY | extra_trees | bear | 10 | CANDIDATE | 27483 | 11036 | 11211 | ACTIVE | ACTIVE | False |
| c0e7a54ffa92e6d825f7c094 | ORDINARY | extra_trees | bull | 10 | CANDIDATE | 27483 | 11036 | 11211 | ACTIVE | ACTIVE | False |
| 675b0cb01b95ee101bc7a420 | ORDINARY | hist_gradient_boosting | bear | 10 | CANDIDATE | 27483 | 11036 | 11211 | ACTIVE | ACTIVE | False |
| fc8aba70b0de5556b51bc18d | ORDINARY | hist_gradient_boosting | bull | 10 | CANDIDATE | 27483 | 11036 | 11211 | ACTIVE | ACTIVE | False |
| 192d570f9cf1bcc61a01b969 | POOLED | extra_trees | bear | 10 | CANDIDATE | 41954 | 16835 | 17070 | ACTIVE | ACTIVE | False |
| 7e216b2de0beb63d6c7df590 | POOLED | extra_trees | bull | 10 | CANDIDATE | 41954 | 16835 | 17070 | ACTIVE | ACTIVE | False |
| c7ae8e8123d3cde9861e0095 | POOLED | hist_gradient_boosting | bear | 10 | CANDIDATE | 41954 | 16835 | 17070 | ACTIVE | ACTIVE | False |
| 5260dd129e51b244e11ce341 | POOLED | hist_gradient_boosting | bull | 10 | CANDIDATE | 41954 | 16835 | 17070 | ACTIVE | ACTIVE | False |

### Naive Controls
| model_id | product_class_scope | direction | horizon | registry_state | training_count | calibration_count | development_holdout_count | promotion_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a58814d4a73e39f08476b391 | LEVERAGED_INVERSE | bear | 10 | CANDIDATE | 14471 | 5799 | 5859 | False |
| 47e36feb6ff65549a9d3b304 | LEVERAGED_INVERSE | bull | 10 | CANDIDATE | 14471 | 5799 | 5859 | False |
| 38e8fd27aaa204e2bdee98d6 | ORDINARY | bear | 10 | CANDIDATE | 27483 | 11036 | 11211 | False |
| 0103685f3dafa1feae400907 | ORDINARY | bull | 10 | CANDIDATE | 27483 | 11036 | 11211 | False |
| 21a6ae66b788dc398dc90fdb | POOLED | bear | 10 | CANDIDATE | 41954 | 16835 | 17070 | False |
| 81577cfdf17f4e19f7b214e9 | POOLED | bull | 10 | CANDIDATE | 41954 | 16835 | 17070 | False |

## Pooled Versus Specialist
POOLED models were re-scored on the matching specialist development-holdout rows. These results are diagnostic only, not promotion evidence.
| comparison_scope | family | direction | pooled_model_id | specialist_model_id | pooled_primary_brier | specialist_primary_brier | delta_specialist_minus_pooled_primary_brier | pooled_target_before_stop_calibrated_brier | specialist_target_before_stop_calibrated_brier | pooled_expected_return_ood_rate | specialist_expected_return_ood_rate | pooled_selected_after_caps | specialist_selected_after_caps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LEVERAGED_INVERSE | extra_trees | bear | 192d570f9cf1bcc61a01b969 | 5902be0760c859a9f94be5eb | 0.24523 | 0.242747 | -0.0024834 | 0.19157 | 0.190947 | 0 | 0 | 0 | 0 |
| LEVERAGED_INVERSE | extra_trees | bull | 7e216b2de0beb63d6c7df590 | 34484c2b2201af3659da3f20 | 0.247085 | 0.242465 | -0.00462001 | 0.202031 | 0.199051 | 0 | 0 | 0 | 0 |
| LEVERAGED_INVERSE | hist_gradient_boosting | bear | c7ae8e8123d3cde9861e0095 | 4a54311203043e27e568cab4 | 0.254113 | 0.24599 | -0.00812367 | 0.192108 | 0.205895 | 0 | 0 | 0 | 223 |
| LEVERAGED_INVERSE | hist_gradient_boosting | bull | 5260dd129e51b244e11ce341 | 98dd966d1b0dde983e730fa6 | 0.252727 | 0.246239 | -0.00648828 | 0.199612 | 0.198392 | 0 | 0 | 62 | 5 |
| ORDINARY | extra_trees | bear | 192d570f9cf1bcc61a01b969 | d2da145c98bbe7c50315524f | 0.245363 | 0.244697 | -0.000665305 | 0.187564 | 0.189984 | 0 | 0 | 0 | 0 |
| ORDINARY | extra_trees | bull | 7e216b2de0beb63d6c7df590 | c0e7a54ffa92e6d825f7c094 | 0.24529 | 0.244606 | -0.000683734 | 0.214507 | 0.22336 | 0 | 0 | 0 | 197 |
| ORDINARY | hist_gradient_boosting | bear | c7ae8e8123d3cde9861e0095 | 675b0cb01b95ee101bc7a420 | 0.245551 | 0.244314 | -0.00123639 | 0.19457 | 0.200471 | 0 | 0 | 0 | 1 |
| ORDINARY | hist_gradient_boosting | bull | 5260dd129e51b244e11ce341 | fc8aba70b0de5556b51bc18d | 0.245635 | 0.244198 | -0.0014379 | 0.219806 | 0.220315 | 0 | 0 | 41 | 148 |

## OOD Comparison
| model_id | product_class_scope | family | direction | return_holdout_ood_count | return_holdout_ood_rate | mfe_holdout_ood_count | mfe_holdout_ood_rate | mae_holdout_ood_count | mae_holdout_ood_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 192d570f9cf1bcc61a01b969 | POOLED | extra_trees | bear | 0 | 0 | 0 | 0 | 0 | 0 |
| 34484c2b2201af3659da3f20 | LEVERAGED_INVERSE | extra_trees | bull | 0 | 0 | 0 | 0 | 0 | 0 |
| 4a54311203043e27e568cab4 | LEVERAGED_INVERSE | hist_gradient_boosting | bear | 0 | 0 | 0 | 0 | 0 | 0 |
| 5260dd129e51b244e11ce341 | POOLED | hist_gradient_boosting | bull | 0 | 0 | 0 | 0 | 6 | 0.000351494 |
| 5902be0760c859a9f94be5eb | LEVERAGED_INVERSE | extra_trees | bear | 0 | 0 | 0 | 0 | 0 | 0 |
| 675b0cb01b95ee101bc7a420 | ORDINARY | hist_gradient_boosting | bear | 0 | 0 | 0 | 0 | 0 | 0 |
| 7e216b2de0beb63d6c7df590 | POOLED | extra_trees | bull | 0 | 0 | 0 | 0 | 0 | 0 |
| 98dd966d1b0dde983e730fa6 | LEVERAGED_INVERSE | hist_gradient_boosting | bull | 0 | 0 | 0 | 0 | 0 | 0 |
| c0e7a54ffa92e6d825f7c094 | ORDINARY | extra_trees | bull | 0 | 0 | 0 | 0 | 0 | 0 |
| c7ae8e8123d3cde9861e0095 | POOLED | hist_gradient_boosting | bear | 0 | 0 | 0 | 0 | 0 | 0 |
| d2da145c98bbe7c50315524f | ORDINARY | extra_trees | bear | 0 | 0 | 0 | 0 | 0 | 0 |
| fc8aba70b0de5556b51bc18d | ORDINARY | hist_gradient_boosting | bull | 0 | 0 | 0 | 0 | 0 | 0 |

## Calibration Comparison
| model_id | product_class_scope | family | direction | model_brier | naive_brier | brier_skill_score | selected_method | calibration_manifest_hash | mandatory_gates_failed | promotion_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 192d570f9cf1bcc61a01b969 | POOLED | extra_trees | bear | 0.24529 | 0.24968 | 0.0175838 | sigmoid | cf6b31ebb0532642 | 7 | False |
| 34484c2b2201af3659da3f20 | LEVERAGED_INVERSE | extra_trees | bull | 0.241025 | 0.246228 | 0.0211311 | sigmoid | 5952167bc3ada927 | 7 | False |
| 4a54311203043e27e568cab4 | LEVERAGED_INVERSE | hist_gradient_boosting | bear | 0.244167 | 0.246512 | 0.00951251 | identity | f9b167f32f0f1c47 | 1 | False |
| 5260dd129e51b244e11ce341 | POOLED | hist_gradient_boosting | bull | 0.247857 | 0.249744 | 0.00755501 | identity | ac9e2feb545c9e16 | 1 | False |
| 5902be0760c859a9f94be5eb | LEVERAGED_INVERSE | extra_trees | bear | 0.240921 | 0.246512 | 0.0226825 | sigmoid | d08af138faa1df9c | 7 | False |
| 675b0cb01b95ee101bc7a420 | ORDINARY | hist_gradient_boosting | bear | 0.245986 | 0.24607 | 0.000341675 | identity | ddecc63dc97c6cc9 | 5 | False |
| 7e216b2de0beb63d6c7df590 | POOLED | extra_trees | bull | 0.24562 | 0.249744 | 0.0165105 | sigmoid | d51bce3d87e85229 | 7 | False |
| 98dd966d1b0dde983e730fa6 | LEVERAGED_INVERSE | hist_gradient_boosting | bull | 0.243469 | 0.246228 | 0.0112063 | identity | 8f8758ac58b82e1d | 7 | False |
| c0e7a54ffa92e6d825f7c094 | ORDINARY | extra_trees | bull | 0.246547 | 0.246237 | -0.00125895 | identity | 332550e2bc74b4a2 | 2 | False |
| c7ae8e8123d3cde9861e0095 | POOLED | hist_gradient_boosting | bear | 0.248511 | 0.24968 | 0.00468087 | identity | d49a27d8ea04db51 | 7 | False |
| d2da145c98bbe7c50315524f | ORDINARY | extra_trees | bear | 0.247026 | 0.24607 | -0.00388394 | sigmoid | d385b632ac8066df | 8 | False |
| fc8aba70b0de5556b51bc18d | ORDINARY | hist_gradient_boosting | bull | 0.245663 | 0.246237 | 0.00233228 | identity | d6cda3fdcb68524e | 2 | False |

## Target Distribution Comparison
| scope | split | directional_return_std | directional_return_max | mfe_max | mae_min | positive_return_positive_rate | target_before_stop_positive_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| POOLED | development_holdout | 0.0879761 | 1.46061 | 1.88105 | -0.576268 | 0.475103 | 0.259285 |
| LEVERAGED_INVERSE | development_holdout | 0.119676 | 1.02672 | 1.35998 | -0.652904 | 0.438471 | 0.279911 |
| ORDINARY | development_holdout | 0.0532835 | 0.472068 | 0.492024 | -0.333786 | 0.431184 | 0.260012 |

## Selection And Concentration
| model_id | product_class_scope | family | direction | selected_samples | selected_rate | mean_selected_return | lower_confidence_bound | profit_factor | portfolio_total_return | portfolio_max_drawdown | mandatory_gates_failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 192d570f9cf1bcc61a01b969 | POOLED | extra_trees | bear | 0 | 0 |  |  | NOT_AVAILABLE |  |  | 7 |
| 34484c2b2201af3659da3f20 | LEVERAGED_INVERSE | extra_trees | bull | 0 | 0 |  |  | NOT_AVAILABLE |  |  | 7 |
| 4a54311203043e27e568cab4 | LEVERAGED_INVERSE | hist_gradient_boosting | bear | 214 | 0.036525 | 0.0496131 | 0.0311229 | 2.978265069868827 | 0.43932 | -0.358931 | 1 |
| 5260dd129e51b244e11ce341 | POOLED | hist_gradient_boosting | bull | 96 | 0.0056239 | 0.0285433 | 0.0147344 | 3.5714138402556634 | 0.353924 | -0.0845721 | 1 |
| 5902be0760c859a9f94be5eb | LEVERAGED_INVERSE | extra_trees | bear | 0 | 0 |  |  | NOT_AVAILABLE |  |  | 7 |
| 675b0cb01b95ee101bc7a420 | ORDINARY | hist_gradient_boosting | bear | 1 | 8.91981e-05 | 0.0557334 | 0.0557334 | Infinity | 0.00802994 | -0.0216203 | 5 |
| 7e216b2de0beb63d6c7df590 | POOLED | extra_trees | bull | 0 | 0 |  |  | NOT_AVAILABLE |  |  | 7 |
| 98dd966d1b0dde983e730fa6 | LEVERAGED_INVERSE | hist_gradient_boosting | bull | 0 | 0 |  |  | NOT_AVAILABLE |  |  | 7 |
| c0e7a54ffa92e6d825f7c094 | ORDINARY | extra_trees | bull | 67 | 0.00597627 | 0.0496719 | 0.0376034 | 12.003754776868579 | 0.414098 | -0.0829987 | 2 |
| c7ae8e8123d3cde9861e0095 | POOLED | hist_gradient_boosting | bear | 0 | 0 |  |  | NOT_AVAILABLE |  |  | 7 |
| d2da145c98bbe7c50315524f | ORDINARY | extra_trees | bear | 0 | 0 |  |  | NOT_AVAILABLE |  |  | 8 |
| fc8aba70b0de5556b51bc18d | ORDINARY | hist_gradient_boosting | bull | 62 | 0.00553028 | 0.0337796 | 0.0204667 | 5.458931452450569 | 0.326168 | -0.0317999 | 2 |

## Review-Only Scanner
- Scan ID: `6250ac060e12933471c64676`
- As-of date: `2026-06-25`
- Total rows: 50
- Actionable rows: 0
- Scope mismatch rejections: 0
- Model states: CANDIDATE:50

Rows by scope:
| product_class_scope | row_product_class_scope | rows |
| --- | --- | --- |
| LEVERAGED_INVERSE | LEVERAGED_INVERSE | 18 |
| ORDINARY | ORDINARY | 6 |
| POOLED | LEVERAGED_INVERSE | 17 |
| POOLED | ORDINARY | 9 |

Rejection reasons:
| candidate_status | exclusion_reason | rows |
| --- | --- | --- |
| REJECTED | model_not_promoted | 50 |

## Operational Immutability Proof
- Operational path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`.
- Operational branch: `feat/autonomous-swing-scanner-v1`.
- Operational HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`.
- Operational Git status: clean from `GIT_OPTIONAL_LOCKS=0 git status --short`.
- Prospective run count: 1.
- Prospective run ID: `3493ee8ac37bf96475c362e1`.
- Run status: `CREATED`.
- Enrolled model ID: `b93b2258c10aea5cef81d291`.
- Frozen generation: `2026-06-25T13:11:51.610283+00:00`.
- Baseline market date: `2026-06-25`.
- Frozen model artifact hash in DB: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`.
- Current operational artifact SHA-256: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`.
- Final-holdout-prefixed forward events: 0.
- Operational scanner snapshots: 17 existing; no development scanner artifact was created in operations.
- Operational forward events: 285 existing; no ordinary forward-update was run by this task.

## Verification
- Pre-discovery: `pytest` 281 passed; `ruff check .` passed; `ruff format --check .` passed; `mypy src` passed.
- Post-discovery/scanner: `pytest` 281 passed; `ruff check .` passed; `ruff format --check .` passed; `mypy src` passed.
- `doctor` in development reported local `.env` absent and FMP key not configured.
- No FMP request command was run.
- No model was promoted.
- No prospective final-holdout run was created in development.
- No ordinary forward event was created in development.

## Exported Reports
- `reports/product_class_specialist_v1/PRODUCT_CLASS_SPECIALIST_V1_AUDIT.md`
- `reports/product_class_specialist_v1/product_class_model_inventory.csv`
- `reports/product_class_specialist_v1/nonlinear_mandatory_gate_table.csv`
- `reports/product_class_specialist_v1/nonlinear_failed_mandatory_gates.csv`
- `reports/product_class_specialist_v1/target_distribution_comparison.csv`
- `reports/product_class_specialist_v1/fair_scope_sliced_model_metrics.csv`
- `reports/product_class_specialist_v1/pooled_vs_ordinary_specialist.csv`
- `reports/product_class_specialist_v1/pooled_vs_leveraged_inverse_specialist.csv`
- `reports/product_class_specialist_v1/ood_comparison.csv`
- `reports/product_class_specialist_v1/calibration_comparison.csv`
- `reports/product_class_specialist_v1/selection_concentration_comparison.csv`
- `reports/product_class_specialist_v1/feature_family_comparison.csv`
- `reports/product_class_specialist_v1/review_scanner_summary.csv`
- `reports/product_class_specialist_v1/review_scanner_rows_by_scope.csv`
- `reports/product_class_specialist_v1/review_scanner_rejection_reasons.csv`

## Next Smallest Task
Run a read-only diagnostic review of `reports/product_class_specialist_v1/` to decide whether the specialist-vs-pooled evidence is consistent enough across metrics and chronological segments to justify a follow-up experiment.
