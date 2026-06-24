# Path-Metric Model Diagnosis

Latest generation ID: `2026-06-21T20:51:00.841677+00:00`

Read-only scope: SQLite was opened with `mode=ro`; model artifacts and parquet panels were loaded read-only. The only file written by this diagnostic is this Markdown report.

## 1. Latest Learned Models
| model | direction | family | horizon | train | calibration | dev_holdout | return_estimator | mfe_estimator | mae_estimator |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9667744237fcebdd589a9c67 | bear | extra_trees | 10 | 2016-06-20..2022-04-28 | 2022-05-13..2024-04-17 | 2024-05-02..2026-04-22 | ExtraTreesRegressor | ExtraTreesRegressor | ExtraTreesRegressor |
| 8b7b96af23310d90768cbd53 | bear | hist_gradient_boosting | 10 | 2016-06-20..2022-04-28 | 2022-05-13..2024-04-17 | 2024-05-02..2026-04-22 | HistGradientBoostingRegressor | HistGradientBoostingRegressor | HistGradientBoostingRegressor |
| e5c7ce8b917c30030801fb58 | bear | logistic_regression | 10 | 2016-06-20..2022-04-28 | 2022-05-13..2024-04-17 | 2024-05-02..2026-04-22 | Ridge | Ridge | Ridge |
| c152bfa00503d94f86c74869 | bull | extra_trees | 10 | 2016-06-20..2022-04-28 | 2022-05-13..2024-04-17 | 2024-05-02..2026-04-22 | ExtraTreesRegressor | ExtraTreesRegressor | ExtraTreesRegressor |
| 14ca47d4c2760a6e3d8867c8 | bull | hist_gradient_boosting | 10 | 2016-06-20..2022-04-28 | 2022-05-13..2024-04-17 | 2024-05-02..2026-04-22 | HistGradientBoostingRegressor | HistGradientBoostingRegressor | HistGradientBoostingRegressor |
| 34665ce3f2b9f593f8fcc6b4 | bull | logistic_regression | 10 | 2016-06-20..2022-04-28 | 2022-05-13..2024-04-17 | 2024-05-02..2026-04-22 | Ridge | Ridge | Ridge |

Current failed return/MFE/MAE-related gates:
| model | dir | family | gate | actual | threshold | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 96677442 | bear | extra_trees | positive_expected_value_after_costs | NOT_AVAILABLE | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 96677442 | bear | extra_trees | transaction_cost_sensitivity_not_collapsed | NOT_AVAILABLE | -0.0010 | Double-cost lower confidence bound fails or is missing. |
| 96677442 | bear | extra_trees | return_holdout_ood_q99_severity_acceptable | 0.3563 | 0.1000 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 96677442 | bear | extra_trees | mfe_holdout_ood_q99_severity_acceptable | 0.8977 | 0.3205 | MFE holdout OOD q99 severity exceeds the frozen limit. |
| 8b7b96af | bear | hist_gradient_boosting | return_holdout_ood_q99_severity_acceptable | 0.7286 | 0.1794 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| 8b7b96af | bear | hist_gradient_boosting | mfe_holdout_ood_q99_severity_acceptable | 2.4665 | 0.5000 | MFE holdout OOD q99 severity exceeds the frozen limit. |
| 8b7b96af | bear | hist_gradient_boosting | mfe_catastrophic_prediction_extrapolation_absent | 2.6055 | 1.0000 | MFE maximum holdout OOD severity exceeds 1.00. |
| 8b7b96af | bear | hist_gradient_boosting | mae_holdout_ood_q99_severity_acceptable | 0.1619 | 0.1000 | MAE holdout OOD q99 severity exceeds the frozen limit. |
| e5c7ce8b | bear | logistic_regression | positive_expected_value_after_costs | NOT_AVAILABLE | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| e5c7ce8b | bear | logistic_regression | transaction_cost_sensitivity_not_collapsed | NOT_AVAILABLE | -0.0010 | Double-cost lower confidence bound fails or is missing. |
| e5c7ce8b | bear | logistic_regression | return_holdout_ood_q99_severity_acceptable | 0.4634 | 0.1000 | Expected Return holdout OOD q99 severity exceeds the frozen limit. |
| e5c7ce8b | bear | logistic_regression | mfe_prediction_path_metric_sign_valid | 0.0000 | 1.0000 | MFE path-metric sign contract failed. |
| e5c7ce8b | bear | logistic_regression | mfe_holdout_ood_q99_severity_acceptable | 0.8073 | 0.1487 | MFE holdout OOD q99 severity exceeds the frozen limit. |
| e5c7ce8b | bear | logistic_regression | mfe_catastrophic_prediction_extrapolation_absent | 2.9000 | 1.0000 | MFE maximum holdout OOD severity exceeds 1.00. |
| e5c7ce8b | bear | logistic_regression | mae_holdout_ood_q99_severity_acceptable | 1.4882 | 0.1000 | MAE holdout OOD q99 severity exceeds the frozen limit. |
| e5c7ce8b | bear | logistic_regression | mae_catastrophic_prediction_extrapolation_absent | 1.5735 | 1.0000 | MAE maximum holdout OOD severity exceeds 1.00. |
| c152bfa0 | bull | extra_trees | positive_expected_value_after_costs | NOT_AVAILABLE | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| c152bfa0 | bull | extra_trees | transaction_cost_sensitivity_not_collapsed | NOT_AVAILABLE | -0.0010 | Double-cost lower confidence bound fails or is missing. |
| c152bfa0 | bull | extra_trees | mae_holdout_ood_q99_severity_acceptable | 0.1360 | 0.1000 | MAE holdout OOD q99 severity exceeds the frozen limit. |
| 14ca47d4 | bull | hist_gradient_boosting | positive_expected_value_after_costs | -0.0089 | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 14ca47d4 | bull | hist_gradient_boosting | transaction_cost_sensitivity_not_collapsed | -0.0094 | -0.0010 | Double-cost lower confidence bound fails or is missing. |
| 14ca47d4 | bull | hist_gradient_boosting | mfe_holdout_ood_q99_severity_acceptable | 0.4139 | 0.1731 | MFE holdout OOD q99 severity exceeds the frozen limit. |
| 14ca47d4 | bull | hist_gradient_boosting | mae_holdout_ood_q99_severity_acceptable | 0.1643 | 0.1336 | MAE holdout OOD q99 severity exceeds the frozen limit. |
| 34665ce3 | bull | logistic_regression | positive_expected_value_after_costs | NOT_AVAILABLE | -0.0005 | Lower confidence bound is missing or below cost threshold. |
| 34665ce3 | bull | logistic_regression | transaction_cost_sensitivity_not_collapsed | NOT_AVAILABLE | -0.0010 | Double-cost lower confidence bound fails or is missing. |
| 34665ce3 | bull | logistic_regression | mfe_holdout_ood_q99_severity_acceptable | 1.5354 | 0.1000 | MFE holdout OOD q99 severity exceeds the frozen limit. |
| 34665ce3 | bull | logistic_regression | mfe_catastrophic_prediction_extrapolation_absent | 1.6341 | 1.0000 | MFE maximum holdout OOD severity exceeds 1.00. |
| 34665ce3 | bull | logistic_regression | mae_holdout_ood_q99_severity_acceptable | 2.1140 | 0.1000 | MAE holdout OOD q99 severity exceeds the frozen limit. |
| 34665ce3 | bull | logistic_regression | mae_catastrophic_prediction_extrapolation_absent | 2.4080 | 1.0000 | MAE maximum holdout OOD severity exceeds 1.00. |

## 2. Label Contract Audit
- Signal is known after daily close; entry is next-session open via `Open.shift(-1)`.
- Horizon is exactly 10 completed sessions for this generation.
- Decimal units are used: `0.05` means 5%. Display percentages are not training targets.
- Bull return: `exit_close / next_open - 1`; bear return: `next_open / exit_close - 1`.
- Bull MFE: `future_high / next_open - 1`; bull MAE: `future_low / next_open - 1`.
- Bear MFE: `next_open / future_low - 1`; bear MAE: `next_open / future_high - 1`.
- MFE labels are favorable and nonnegative; MAE labels are adverse and nonpositive by construction.
- `label_end_date_10` is purged to stay within the research end; target/stop first-touch labels are separate and do not alter MFE/MAE.
- Manual raw-OHLCV recomputation checked 156 rows; mismatches: 0.

## 3. Target Distributions
| direction | head | split | count | min | max | mean | std | p01 | p50 | p99 | skew | kurt | zero_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bull | return | training | 51157 | -0.7617 | 1.3512 | 0.0034 | 0.0781 | -0.2245 | 0.0044 | 0.2495 | 0.3769 | 11.7726 | 0.30% |
| bull | return | calibration | 16940 | -0.4615 | 0.6811 | 0.0037 | 0.0847 | -0.2359 | 0.0046 | 0.2637 | 0.3694 | 4.8244 | 0.16% |
| bull | return | development_holdout | 17290 | -0.5936 | 1.0267 | 0.0036 | 0.0834 | -0.2297 | 0.0026 | 0.2663 | 0.9246 | 13.1182 | 0.18% |
| bull | mfe | training | 51157 | 0.0000 | 1.4550 | 0.0508 | 0.0669 | 0.0003 | 0.0292 | 0.3272 | 4.0215 | 31.9932 | 0.78% |
| bull | mfe | calibration | 16940 | 0.0000 | 0.8560 | 0.0580 | 0.0681 | 0.0006 | 0.0369 | 0.3318 | 3.0036 | 13.7850 | 0.41% |
| bull | mfe | development_holdout | 17290 | 0.0000 | 1.3600 | 0.0540 | 0.0736 | 0.0004 | 0.0315 | 0.3618 | 4.4447 | 35.1144 | 0.47% |
| bull | mae | training | 51157 | -0.7992 | 0.0000 | -0.0469 | 0.0582 | -0.2747 | -0.0269 | -0.0002 | -3.0246 | 15.1890 | 0.83% |
| bull | mae | calibration | 16940 | -0.5452 | 0.0000 | -0.0524 | 0.0579 | -0.2770 | -0.0333 | -0.0004 | -2.2955 | 7.2536 | 0.44% |
| bull | mae | development_holdout | 17290 | -0.6529 | 0.0000 | -0.0490 | 0.0599 | -0.2884 | -0.0293 | -0.0003 | -2.9900 | 13.3303 | 0.53% |
| bear | return | training | 51157 | -0.5747 | 3.1967 | 0.0031 | 0.0887 | -0.1997 | -0.0044 | 0.2895 | 5.5661 | 118.7855 | 0.30% |
| bear | return | calibration | 16940 | -0.4052 | 0.8570 | 0.0035 | 0.0881 | -0.2087 | -0.0045 | 0.3088 | 1.3729 | 8.1806 | 0.16% |
| bear | return | development_holdout | 17290 | -0.5066 | 1.4606 | 0.0034 | 0.0882 | -0.2103 | -0.0026 | 0.2982 | 2.5045 | 25.2189 | 0.18% |
| bear | mfe | training | 51157 | 0.0000 | 3.9812 | 0.0544 | 0.0916 | 0.0002 | 0.0276 | 0.3788 | 10.4527 | 254.8617 | 0.83% |
| bear | mfe | calibration | 16940 | 0.0000 | 1.1986 | 0.0600 | 0.0781 | 0.0004 | 0.0344 | 0.3831 | 3.5324 | 20.5893 | 0.44% |
| bear | mfe | development_holdout | 17290 | 0.0000 | 1.8811 | 0.0569 | 0.0890 | 0.0003 | 0.0302 | 0.4053 | 5.9168 | 63.7259 | 0.53% |
| bear | mae | training | 51157 | -0.5927 | 0.0000 | -0.0451 | 0.0508 | -0.2465 | -0.0284 | -0.0003 | -2.5211 | 9.1121 | 0.78% |
| bear | mae | calibration | 16940 | -0.4612 | 0.0000 | -0.0515 | 0.0525 | -0.2491 | -0.0356 | -0.0006 | -2.1494 | 6.1334 | 0.41% |
| bear | mae | development_holdout | 17290 | -0.5763 | 0.0000 | -0.0476 | 0.0538 | -0.2657 | -0.0306 | -0.0004 | -2.7123 | 10.6950 | 0.47% |

Development-holdout product-class tails:
| direction | head | product_class | count | mean | std | p99_abs | max_abs | tail_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bull | return | inverse_etf | 3952 | -0.0192 | 0.1029 | 0.3715 | 1.0267 | 40.46% |
| bull | return | leveraged_etf | 1976 | 0.0240 | 0.1445 | 0.4796 | 0.9895 | 47.40% |
| bull | return | ordinary_etf | 7410 | 0.0054 | 0.0338 | 0.1021 | 0.1877 | 0.00% |
| bull | return | ordinary_stock | 3952 | 0.0129 | 0.0804 | 0.2626 | 0.4990 | 12.14% |
| bull | mfe | inverse_etf | 3952 | 0.0712 | 0.0999 | 0.4875 | 1.3600 | 51.15% |
| bull | mfe | leveraged_etf | 1976 | 0.1053 | 0.1072 | 0.5363 | 0.9956 | 34.48% |
| bull | mfe | ordinary_etf | 7410 | 0.0266 | 0.0220 | 0.1023 | 0.1717 | 0.00% |
| bull | mfe | ordinary_stock | 3952 | 0.0626 | 0.0630 | 0.2973 | 0.5010 | 14.37% |
| bull | mae | inverse_etf | 3952 | -0.0682 | 0.0715 | 0.3521 | 0.6214 | 42.77% |
| bull | mae | leveraged_etf | 1976 | -0.0946 | 0.0940 | 0.4410 | 0.6529 | 55.49% |
| bull | mae | ordinary_etf | 7410 | -0.0249 | 0.0251 | 0.1333 | 0.2077 | 0.00% |
| bull | mae | ordinary_stock | 3952 | -0.0521 | 0.0497 | 0.2339 | 0.3298 | 1.73% |
| bear | return | inverse_etf | 3952 | 0.0310 | 0.1143 | 0.4348 | 1.1791 | 52.60% |
| bear | return | leveraged_etf | 1976 | -0.0030 | 0.1536 | 0.5506 | 1.4606 | 43.93% |
| bear | return | ordinary_etf | 7410 | -0.0042 | 0.0340 | 0.1028 | 0.2310 | 0.00% |
| bear | return | ordinary_stock | 3952 | -0.0067 | 0.0777 | 0.2457 | 0.4721 | 3.47% |
| bear | mfe | inverse_etf | 3952 | 0.0812 | 0.1081 | 0.5435 | 1.6416 | 42.77% |
| bear | mfe | leveraged_etf | 1976 | 0.1207 | 0.1629 | 0.7888 | 1.8811 | 55.49% |
| bear | mfe | ordinary_etf | 7410 | 0.0263 | 0.0284 | 0.1538 | 0.2622 | 0.00% |
| bear | mfe | ordinary_stock | 3952 | 0.0581 | 0.0619 | 0.3054 | 0.4920 | 1.73% |
| bear | mae | inverse_etf | 3952 | -0.0603 | 0.0682 | 0.3277 | 0.5763 | 51.15% |
| bear | mae | leveraged_etf | 1976 | -0.0881 | 0.0745 | 0.3491 | 0.4989 | 34.48% |
| bear | mae | ordinary_etf | 7410 | -0.0255 | 0.0203 | 0.0928 | 0.1466 | 0.00% |
| bear | mae | ordinary_stock | 3952 | -0.0560 | 0.0499 | 0.2292 | 0.3338 | 14.37% |

Top symbol target tails:
| direction | head | symbol | count | mean_abs | max_abs |
| --- | --- | --- | --- | --- | --- |
| bull | return | SOXS | 494 | 0.1562 | 1.0267 |
| bull | return | SOXL | 494 | 0.1673 | 0.9895 |
| bull | return | TZA | 494 | 0.0936 | 0.6219 |
| bull | return | SQQQ | 494 | 0.0856 | 0.5921 |
| bull | return | SPXU | 494 | 0.0615 | 0.5015 |
| bull | mfe | SOXS | 494 | 0.1577 | 1.3600 |
| bull | mfe | SOXL | 494 | 0.1744 | 0.9956 |
| bull | mfe | SQQQ | 494 | 0.0896 | 0.7373 |
| bull | mfe | TZA | 494 | 0.0972 | 0.7074 |
| bull | mfe | SPXU | 494 | 0.0675 | 0.6284 |
| bull | mae | SOXL | 494 | 0.1421 | 0.6529 |
| bull | mae | SOXS | 494 | 0.1594 | 0.6214 |
| bull | mae | TQQQ | 494 | 0.0836 | 0.4748 |
| bull | mae | TNA | 494 | 0.0893 | 0.4638 |
| bull | mae | UPRO | 494 | 0.0633 | 0.4337 |
| bear | return | SOXL | 494 | 0.1667 | 1.4606 |
| bear | return | SOXS | 494 | 0.1807 | 1.1791 |
| bear | return | TNA | 494 | 0.0951 | 0.7385 |
| bear | return | TQQQ | 494 | 0.0868 | 0.7131 |
| bear | return | UPRO | 494 | 0.0630 | 0.5935 |
| bear | mfe | SOXL | 494 | 0.1994 | 1.8811 |
| bear | mfe | SOXS | 494 | 0.2153 | 1.6416 |
| bear | mfe | TQQQ | 494 | 0.1013 | 0.9040 |
| bear | mfe | TNA | 494 | 0.1082 | 0.8651 |
| bear | mfe | UPRO | 494 | 0.0741 | 0.7657 |
| bear | mae | SOXS | 494 | 0.1206 | 0.5763 |
| bear | mae | SOXL | 494 | 0.1363 | 0.4989 |
| bear | mae | SQQQ | 494 | 0.0759 | 0.4244 |
| bear | mae | TZA | 494 | 0.0821 | 0.4143 |
| bear | mae | SPXU | 494 | 0.0589 | 0.3859 |

## 4. Raw Percent Versus ATR-Normalized Targets
| direction | head | raw_class_mean_cv | atr_norm_class_mean_cv | cv_change | raw_lev_inv_tail_share | atr_norm_lev_inv_tail_share |
| --- | --- | --- | --- | --- | --- | --- |
| bull | return | 2.7462 | 1.8887 | -0.8575 | 87.86% | 34.68% |
| bull | mfe | 0.4211 | 0.0403 | -0.3808 | 85.63% | 56.07% |
| bull | mae | 0.4219 | 0.0341 | -0.3878 | 98.27% | 19.08% |
| bear | return | 3.6199 | 9.6506 | 6.0306 | 96.53% | 40.46% |
| bear | mfe | 0.4809 | 0.0813 | -0.3996 | 98.27% | 42.20% |
| bear | mae | 0.3863 | 0.0504 | -0.3359 | 85.63% | 42.20% |

Interpretation: ATR normalization is diagnostic-only here. It generally reduces class-mean dispersion for path magnitudes, but leveraged/inverse products still occupy a large share of the extreme tails; normalization alone will not fix feature-screen reuse or unconstrained loss/domain issues.

## 5. Feature-Screen Audit By Head
| model | head | features | manifest | independent_screen | same_as_primary | same_as_tbs | overlap_primary | overlap_tbs | schema |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9667744237fcebdd589a9c67 | return | 60 | 8bf8caa924b5b7cf | False | True | False | 60 | 8 | none |
| 9667744237fcebdd589a9c67 | mfe | 60 | 5bb0028911ab8a9f | False | True | False | 60 | 8 | none |
| 9667744237fcebdd589a9c67 | mae | 60 | f0d381e509d2a721 | False | True | False | 60 | 8 | none |
| 8b7b96af23310d90768cbd53 | return | 60 | 8bf8caa924b5b7cf | False | True | False | 60 | 8 | none |
| 8b7b96af23310d90768cbd53 | mfe | 60 | 5bb0028911ab8a9f | False | True | False | 60 | 8 | none |
| 8b7b96af23310d90768cbd53 | mae | 60 | f0d381e509d2a721 | False | True | False | 60 | 8 | none |
| e5c7ce8b917c30030801fb58 | return | 60 | 8bf8caa924b5b7cf | False | True | False | 60 | 8 | none |
| e5c7ce8b917c30030801fb58 | mfe | 60 | 5bb0028911ab8a9f | False | True | False | 60 | 8 | none |
| e5c7ce8b917c30030801fb58 | mae | 60 | f0d381e509d2a721 | False | True | False | 60 | 8 | none |
| c152bfa00503d94f86c74869 | return | 60 | ec4fe8bd815867f5 | False | True | False | 60 | 8 | none |
| c152bfa00503d94f86c74869 | mfe | 60 | 7a7972048ecf5d4f | False | True | False | 60 | 8 | none |
| c152bfa00503d94f86c74869 | mae | 60 | a6a7c0e1df96accb | False | True | False | 60 | 8 | none |
| 14ca47d4c2760a6e3d8867c8 | return | 60 | ec4fe8bd815867f5 | False | True | False | 60 | 8 | none |
| 14ca47d4c2760a6e3d8867c8 | mfe | 60 | 7a7972048ecf5d4f | False | True | False | 60 | 8 | none |
| 14ca47d4c2760a6e3d8867c8 | mae | 60 | a6a7c0e1df96accb | False | True | False | 60 | 8 | none |
| 34665ce3f2b9f593f8fcc6b4 | return | 60 | ec4fe8bd815867f5 | False | True | False | 60 | 8 | none |
| 34665ce3f2b9f593f8fcc6b4 | mfe | 60 | 7a7972048ecf5d4f | False | True | False | 60 | 8 | none |
| 34665ce3f2b9f593f8fcc6b4 | mae | 60 | a6a7c0e1df96accb | False | True | False | 60 | 8 | none |

Eligible versus selected families across regression heads:
| head | family | eligible | selected_min | selected_max |
| --- | --- | --- | --- | --- |
| mae | breadth | 6 | 0 | 0 |
| mae | inverse_leveraged | 12 | 0 | 0 |
| mae | market_relative | 20 | 0 | 0 |
| mae | regime | 3 | 0 | 0 |
| mae | relationship_graph | 60 | 0 | 0 |
| mae | returns_momentum | 29 | 16 | 16 |
| mae | rsi_family | 294 | 3 | 4 |
| mae | sector_relative | 8 | 0 | 0 |
| mae | trend_structure | 32 | 23 | 23 |
| mae | volatility_range | 16 | 8 | 9 |
| mae | volume_participation | 11 | 6 | 6 |
| mfe | breadth | 6 | 0 | 0 |
| mfe | inverse_leveraged | 12 | 0 | 0 |
| mfe | market_relative | 20 | 0 | 0 |
| mfe | regime | 3 | 0 | 0 |
| mfe | relationship_graph | 60 | 0 | 0 |
| mfe | returns_momentum | 29 | 16 | 16 |
| mfe | rsi_family | 294 | 3 | 4 |
| mfe | sector_relative | 8 | 0 | 0 |
| mfe | trend_structure | 32 | 23 | 23 |
| mfe | volatility_range | 16 | 8 | 9 |
| mfe | volume_participation | 11 | 6 | 6 |
| return | breadth | 6 | 0 | 0 |
| return | inverse_leveraged | 12 | 0 | 0 |
| return | market_relative | 20 | 0 | 0 |
| return | regime | 3 | 0 | 0 |
| return | relationship_graph | 60 | 0 | 0 |
| return | returns_momentum | 29 | 16 | 16 |
| return | rsi_family | 294 | 3 | 4 |
| return | sector_relative | 8 | 0 | 0 |
| return | trend_structure | 32 | 23 | 23 |
| return | volatility_range | 16 | 8 | 9 |
| return | volume_participation | 11 | 6 | 6 |

Finding: return, MFE, and MAE all reuse the positive-return feature screen. Their manifests differ only by head name/hash, not by target-specific screening records. This is an implementation/design defect for path-metric heads.

## 6. Regression Model Audit
| model | head | estimator | loss | steps | constrained | can_emit_invalid_sign | can_extrapolate | params |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9667744237fcebdd589a9c67 | return | ExtraTreesRegressor | squared_error | imputer,model | no | n/a | mostly bounded by leaf averages | {"criterion": "squared_error", "min_samples_leaf": 10, "n_estimators": 120, "random_state": 42} |
| 9667744237fcebdd589a9c67 | mfe | ExtraTreesRegressor | squared_error | imputer,model | no | yes | mostly bounded by leaf averages | {"criterion": "squared_error", "min_samples_leaf": 10, "n_estimators": 120, "random_state": 43} |
| 9667744237fcebdd589a9c67 | mae | ExtraTreesRegressor | squared_error | imputer,model | no | yes | mostly bounded by leaf averages | {"criterion": "squared_error", "min_samples_leaf": 10, "n_estimators": 120, "random_state": 44} |
| 8b7b96af23310d90768cbd53 | return | HistGradientBoostingRegressor | squared_error | imputer,model | no | n/a | yes | {"l2_regularization": 0.1, "learning_rate": 0.05, "max_iter": 80, "min_samples_leaf": 20, "random_state": 42} |
| 8b7b96af23310d90768cbd53 | mfe | HistGradientBoostingRegressor | squared_error | imputer,model | no | yes | yes | {"l2_regularization": 0.1, "learning_rate": 0.05, "max_iter": 80, "min_samples_leaf": 20, "random_state": 43} |
| 8b7b96af23310d90768cbd53 | mae | HistGradientBoostingRegressor | squared_error | imputer,model | no | yes | yes | {"l2_regularization": 0.1, "learning_rate": 0.05, "max_iter": 80, "min_samples_leaf": 20, "random_state": 44} |
| e5c7ce8b917c30030801fb58 | return | Ridge | squared_error | imputer,scaler,model | no | n/a | yes | {"alpha": 2.0, "max_iter": null, "random_state": null} |
| e5c7ce8b917c30030801fb58 | mfe | Ridge | squared_error | imputer,scaler,model | no | yes | yes | {"alpha": 2.0, "max_iter": null, "random_state": null} |
| e5c7ce8b917c30030801fb58 | mae | Ridge | squared_error | imputer,scaler,model | no | yes | yes | {"alpha": 2.0, "max_iter": null, "random_state": null} |
| c152bfa00503d94f86c74869 | return | ExtraTreesRegressor | squared_error | imputer,model | no | n/a | mostly bounded by leaf averages | {"criterion": "squared_error", "min_samples_leaf": 10, "n_estimators": 120, "random_state": 42} |
| c152bfa00503d94f86c74869 | mfe | ExtraTreesRegressor | squared_error | imputer,model | no | yes | mostly bounded by leaf averages | {"criterion": "squared_error", "min_samples_leaf": 10, "n_estimators": 120, "random_state": 43} |
| c152bfa00503d94f86c74869 | mae | ExtraTreesRegressor | squared_error | imputer,model | no | yes | mostly bounded by leaf averages | {"criterion": "squared_error", "min_samples_leaf": 10, "n_estimators": 120, "random_state": 44} |
| 14ca47d4c2760a6e3d8867c8 | return | HistGradientBoostingRegressor | squared_error | imputer,model | no | n/a | yes | {"l2_regularization": 0.1, "learning_rate": 0.05, "max_iter": 80, "min_samples_leaf": 20, "random_state": 42} |
| 14ca47d4c2760a6e3d8867c8 | mfe | HistGradientBoostingRegressor | squared_error | imputer,model | no | yes | yes | {"l2_regularization": 0.1, "learning_rate": 0.05, "max_iter": 80, "min_samples_leaf": 20, "random_state": 43} |
| 14ca47d4c2760a6e3d8867c8 | mae | HistGradientBoostingRegressor | squared_error | imputer,model | no | yes | yes | {"l2_regularization": 0.1, "learning_rate": 0.05, "max_iter": 80, "min_samples_leaf": 20, "random_state": 44} |
| 34665ce3f2b9f593f8fcc6b4 | return | Ridge | squared_error | imputer,scaler,model | no | n/a | yes | {"alpha": 2.0, "max_iter": null, "random_state": null} |
| 34665ce3f2b9f593f8fcc6b4 | mfe | Ridge | squared_error | imputer,scaler,model | no | yes | yes | {"alpha": 2.0, "max_iter": null, "random_state": null} |
| 34665ce3f2b9f593f8fcc6b4 | mae | Ridge | squared_error | imputer,scaler,model | no | yes | yes | {"alpha": 2.0, "max_iter": null, "random_state": null} |

MFE/MAE sharing checks: return, MFE, and MAE use distinct fitted pipeline objects; bull and bear models use separate artifacts; model families use separate artifacts. Target transforms are `none`, so no inverse transform can be double-applied. Negative MFE predictions occur where an unconstrained Ridge regressor crosses the nonnegative MFE domain.

## 7. Prediction And Residual Audit
| model | dir | family | head | pred_min | pred_max | MAE | RMSE | rank | slope | var_ratio | ood_q99 | ood_max | sign_fail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 96677442 | bear | extra_trees | return | -0.0948 | 0.4996 | 0.0526 | 0.0865 | 0.1021 | 0.6764 | 0.0905 | 0.4022 | 0.4295 | 0 |
| 96677442 | bear | extra_trees | mfe | 0.0083 | 0.7841 | 0.0409 | 0.0763 | 0.4762 | 0.9481 | 0.2985 | 1.0200 | 1.0706 | 0 |
| 96677442 | bear | extra_trees | mae | -0.2323 | -0.0098 | 0.0291 | 0.0445 | 0.5020 | 1.0682 | 0.2759 | 0.0000 | 0.0000 | 0 |
| 8b7b96af | bear | hist_gradient_boosting | return | -0.1858 | 0.7161 | 0.0521 | 0.0866 | 0.1079 | 0.6801 | 0.0857 | 0.7891 | 0.8719 | 0 |
| 8b7b96af | bear | hist_gradient_boosting | mfe | 0.0088 | 1.4604 | 0.0399 | 0.0768 | 0.4787 | 0.9444 | 0.2893 | 2.6488 | 2.8568 | 0 |
| 8b7b96af | bear | hist_gradient_boosting | mae | -0.2950 | -0.0163 | 0.0293 | 0.0450 | 0.5003 | 1.0231 | 0.2856 | 0.1958 | 0.1970 | 0 |
| e5c7ce8b | bear | logistic_regression | return | -0.1390 | 0.5418 | 0.0524 | 0.0866 | 0.1335 | 0.6534 | 0.0959 | 0.5158 | 0.5158 | 0 |
| e5c7ce8b | bear | logistic_regression | mfe | -0.0144 | 1.5797 | 0.0416 | 0.0791 | 0.4742 | 0.7911 | 0.3634 | 0.9284 | 3.1719 | 78 |
| e5c7ce8b | bear | logistic_regression | mae | -0.6525 | -0.0055 | 0.0293 | 0.0452 | 0.4928 | 0.9805 | 0.3028 | 1.5355 | 1.6483 | 0 |
| c152bfa0 | bull | extra_trees | return | -0.1884 | 0.1433 | 0.0518 | 0.0825 | 0.0979 | 0.6163 | 0.0607 | 0.0000 | 0.0000 | 0 |
| c152bfa0 | bull | extra_trees | mfe | 0.0101 | 0.3376 | 0.0354 | 0.0620 | 0.5029 | 1.0791 | 0.2479 | 0.0315 | 0.0318 | 0 |
| c152bfa0 | bull | extra_trees | mae | -0.3283 | -0.0081 | 0.0324 | 0.0496 | 0.4794 | 0.9822 | 0.3276 | 0.1841 | 0.1952 | 0 |
| 14ca47d4 | bull | hist_gradient_boosting | return | -0.2368 | 0.1712 | 0.0514 | 0.0817 | 0.0852 | 0.8822 | 0.0450 | 0.0259 | 0.0259 | 0 |
| 14ca47d4 | bull | hist_gradient_boosting | mfe | 0.0177 | 0.4827 | 0.0355 | 0.0630 | 0.5007 | 1.0400 | 0.2446 | 0.4626 | 0.4758 | 0 |
| 14ca47d4 | bull | hist_gradient_boosting | mae | -0.3370 | -0.0169 | 0.0319 | 0.0496 | 0.4778 | 1.0483 | 0.2849 | 0.2194 | 0.2268 | 0 |
| 34665ce3 | bull | logistic_regression | return | -0.1686 | 0.1497 | 0.0508 | 0.0816 | 0.1663 | 0.7839 | 0.0631 | 0.0000 | 0.0000 | 0 |
| 34665ce3 | bull | logistic_regression | mfe | 0.0002 | 0.8950 | 0.0358 | 0.0633 | 0.4865 | 0.9807 | 0.2682 | 1.6216 | 1.7370 | 0 |
| 34665ce3 | bull | logistic_regression | mae | -0.9822 | -0.0009 | 0.0319 | 0.0502 | 0.4902 | 0.8981 | 0.3716 | 2.0755 | 2.5769 | 0 |

Top error breakdowns:
| group | direction | head | value | count | mean_abs_error | max_abs_error |
| --- | --- | --- | --- | --- | --- | --- |
| product_class | bear | return | leveraged_etf | 5877 | 0.1038 | 1.4973 |
| product_class | bull | return | leveraged_etf | 5877 | 0.0994 | 0.9106 |
| product_class | bear | mfe | leveraged_etf | 5877 | 0.0924 | 1.7956 |
| product_class | bear | return | inverse_etf | 11724 | 0.0685 | 1.1177 |
| product_class | bull | return | inverse_etf | 11724 | 0.0667 | 1.0538 |
| product_class | bull | mae | leveraged_etf | 5877 | 0.0638 | 0.5652 |
| product_class | bull | mfe | leveraged_etf | 5877 | 0.0617 | 0.8093 |
| product_class | bull | return | ordinary_stock | 11700 | 0.0587 | 0.4744 |
| product_class | bear | return | ordinary_stock | 11700 | 0.0585 | 0.5270 |
| product_class | bull | mfe | inverse_etf | 11724 | 0.0546 | 1.2429 |
| product_class | bear | mfe | inverse_etf | 11724 | 0.0478 | 1.3838 |
| product_class | bear | mae | leveraged_etf | 5877 | 0.0474 | 0.3774 |
| market_regime_label | bear | return | mixed | 630 | 0.0791 | 0.3893 |
| market_regime_label | bull | return | mixed | 630 | 0.0772 | 0.3324 |
| market_regime_label | bear | return | downtrend_high_vol | 9210 | 0.0753 | 1.4973 |
| market_regime_label | bull | return | downtrend_high_vol | 9210 | 0.0722 | 1.0538 |
| market_regime_label | bear | mfe | downtrend_high_vol | 9210 | 0.0671 | 1.7956 |
| market_regime_label | bull | mfe | downtrend_high_vol | 9210 | 0.0510 | 1.2429 |
| market_regime_label | bear | return | uptrend_high_vol | 18249 | 0.0480 | 0.9740 |
| market_regime_label | bull | mae | downtrend_high_vol | 9210 | 0.0475 | 0.7883 |
| market_regime_label | bull | return | uptrend_high_vol | 18249 | 0.0468 | 0.7901 |
| market_regime_label | bear | return | uptrend_low_vol | 23118 | 0.0460 | 0.7751 |
| market_regime_label | bull | return | uptrend_low_vol | 23118 | 0.0458 | 0.6088 |
| market_regime_label | bear | mfe | mixed | 630 | 0.0452 | 0.2393 |
| year | bull | return | 2026 | 7881 | 0.0576 | 0.9106 |
| year | bear | return | 2026 | 7881 | 0.0576 | 1.1177 |
| year | bear | return | 2024 | 17349 | 0.0520 | 0.9740 |
| year | bear | return | 2025 | 25977 | 0.0510 | 1.4973 |
| year | bull | return | 2024 | 17349 | 0.0509 | 0.7901 |
| year | bull | return | 2025 | 25977 | 0.0497 | 1.0538 |
| year | bear | mfe | 2025 | 25977 | 0.0423 | 1.7956 |
| year | bear | mfe | 2026 | 7881 | 0.0408 | 0.9636 |
| year | bull | mfe | 2026 | 7881 | 0.0387 | 0.8093 |
| year | bear | mfe | 2024 | 17349 | 0.0385 | 0.9435 |
| year | bull | mfe | 2025 | 25977 | 0.0354 | 1.2429 |
| year | bull | mfe | 2024 | 17349 | 0.0344 | 0.6103 |

25 largest development-holdout prediction errors:
| date | symbol | class | model | dir | head | pred | realized | target_pct | atr_norm | ood_bound | severity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-03-24 | SOXL | leveraged_etf | e5c7ce8b | bear | mfe | 0.0855 | 1.8811 | 100.00% | 18.7398 | [0.0002,0.3788] | 0.0000 |
| 2025-03-24 | SOXL | leveraged_etf | 8b7b96af | bear | mfe | 0.1071 | 1.8811 | 100.00% | 18.7398 | [0.0002,0.3788] | 0.0000 |
| 2025-03-24 | SOXL | leveraged_etf | 96677442 | bear | mfe | 0.1520 | 1.8811 | 100.00% | 18.7398 | [0.0002,0.3788] | 0.0000 |
| 2025-03-25 | SOXL | leveraged_etf | e5c7ce8b | bear | mfe | 0.0834 | 1.8077 | 99.99% | 18.5262 | [0.0002,0.3788] | 0.0000 |
| 2025-03-25 | SOXL | leveraged_etf | 8b7b96af | bear | mfe | 0.0868 | 1.8077 | 99.99% | 18.5262 | [0.0002,0.3788] | 0.0000 |
| 2025-03-25 | SOXL | leveraged_etf | 96677442 | bear | mfe | 0.1394 | 1.8077 | 99.99% | 18.5262 | [0.0002,0.3788] | 0.0000 |
| 2025-03-25 | SOXL | leveraged_etf | 8b7b96af | bear | return | -0.0367 | 1.4606 | 100.00% | 14.9687 | [-0.1997,0.2895] | 0.0000 |
| 2025-03-25 | SOXL | leveraged_etf | e5c7ce8b | bear | return | -0.0332 | 1.4606 | 100.00% | 14.9687 | [-0.1997,0.2895] | 0.0000 |
| 2025-03-25 | SOXL | leveraged_etf | 96677442 | bear | return | -0.0218 | 1.4606 | 100.00% | 14.9687 | [-0.1997,0.2895] | 0.0000 |
| 2025-03-21 | SOXL | leveraged_etf | e5c7ce8b | bear | mfe | 0.0933 | 1.5037 | 99.98% | 13.7442 | [0.0002,0.3788] | 0.0000 |
| 2025-03-21 | SOXL | leveraged_etf | e5c7ce8b | bear | return | -0.0530 | 1.3459 | 99.99% | 12.3024 | [-0.1997,0.2895] | 0.0000 |
| 2025-04-04 | SOXS | inverse_etf | e5c7ce8b | bear | mfe | 0.2578 | 1.6416 | 99.99% | 22.0570 | [0.0002,0.3788] | 0.0000 |
| 2025-03-21 | SOXL | leveraged_etf | 8b7b96af | bear | mfe | 0.1284 | 1.5037 | 99.98% | 13.7442 | [0.0002,0.3788] | 0.0000 |
| 2025-03-21 | SOXL | leveraged_etf | 96677442 | bear | return | -0.0183 | 1.3459 | 99.99% | 12.3024 | [-0.1997,0.2895] | 0.0000 |
| 2025-03-26 | SOXL | leveraged_etf | 96677442 | bear | mfe | 0.1555 | 1.5131 | 99.98% | 14.0069 | [0.0002,0.3788] | 0.0000 |
| 2025-03-21 | SOXL | leveraged_etf | 96677442 | bear | mfe | 0.1501 | 1.5037 | 99.98% | 13.7442 | [0.0002,0.3788] | 0.0000 |
| 2025-03-26 | SOXL | leveraged_etf | e5c7ce8b | bear | mfe | 0.1609 | 1.5131 | 99.98% | 14.0069 | [0.0002,0.3788] | 0.0000 |
| 2025-03-26 | SOXL | leveraged_etf | 8b7b96af | bear | mfe | 0.1711 | 1.5131 | 99.98% | 14.0069 | [0.0002,0.3788] | 0.0000 |
| 2025-03-21 | SOXL | leveraged_etf | 8b7b96af | bear | return | 0.0041 | 1.3459 | 99.99% | 12.3024 | [-0.1997,0.2895] | 0.0000 |
| 2025-04-09 | SOXS | inverse_etf | e5c7ce8b | bear | mfe | 1.5797 | 0.2405 | 96.50% | 0.7233 | [0.0002,0.3788] | 3.1719 |
| 2025-03-24 | SOXL | leveraged_etf | e5c7ce8b | bear | return | -0.0461 | 1.2765 | 99.99% | 12.7170 | [-0.1997,0.2895] | 0.0000 |
| 2025-03-24 | SOXL | leveraged_etf | 8b7b96af | bear | return | -0.0353 | 1.2765 | 99.99% | 12.7170 | [-0.1997,0.2895] | 0.0000 |
| 2025-03-27 | SOXL | leveraged_etf | e5c7ce8b | bear | mfe | 0.0946 | 1.3970 | 99.96% | 12.4861 | [0.0002,0.3788] | 0.0000 |
| 2025-04-04 | SOXS | inverse_etf | 8b7b96af | bear | mfe | 0.3432 | 1.6416 | 99.99% | 22.0570 | [0.0002,0.3788] | 0.0000 |
| 2025-03-24 | SOXL | leveraged_etf | 96677442 | bear | return | -0.0167 | 1.2765 | 99.99% | 12.7170 | [-0.1997,0.2895] | 0.0000 |

## 8. Model-Family Suitability
| family | return | mfe | mae | reason |
| --- | --- | --- | --- | --- |
| Ridge/linear regression | conditionally suitable | unsuitable | conditionally suitable | unconstrained linear squared-error fit can cross MFE/MAE domains and underfits heavy tails |
| ExtraTrees | conditionally suitable | conditionally suitable | conditionally suitable | handles nonlinearities and mostly bounds leaf averages but is not sign/domain constrained |
| HistGradientBoosting | conditionally suitable | conditionally suitable | conditionally suitable | captures nonlinearities but squared-error loss is not tail/domain aware and can produce OOD magnitudes |

## 9. Target-Specific Signal Quality
| model | head | monotonicity | diagnosis |
| --- | --- | --- | --- |
| 96677442 | return | 0.9152 | useful ranking but magnitude still noisy |
| 96677442 | mfe | 1.0000 | useful ranking but magnitude still noisy |
| 96677442 | mae | 1.0000 | useful ranking but magnitude still noisy |
| 8b7b96af | return | 0.9394 | useful ranking but magnitude still noisy |
| 8b7b96af | mfe | 1.0000 | useful ranking but magnitude still noisy |
| 8b7b96af | mae | 1.0000 | useful ranking but magnitude still noisy |
| e5c7ce8b | return | 0.9030 | useful ranking but magnitude still noisy |
| e5c7ce8b | mfe | 1.0000 | useful ranking but magnitude still noisy |
| e5c7ce8b | mae | 1.0000 | useful ranking but magnitude still noisy |
| c152bfa0 | return | 0.8788 | useful ranking but magnitude still noisy |
| c152bfa0 | mfe | 1.0000 | useful ranking but magnitude still noisy |
| c152bfa0 | mae | 1.0000 | useful ranking but magnitude still noisy |
| 14ca47d4 | return | 0.4909 | weak/moderate ranking |
| 14ca47d4 | mfe | 1.0000 | useful ranking but magnitude still noisy |
| 14ca47d4 | mae | 1.0000 | useful ranking but magnitude still noisy |
| 34665ce3 | return | 0.9636 | useful ranking but magnitude still noisy |
| 34665ce3 | mfe | 1.0000 | useful ranking but magnitude still noisy |
| 34665ce3 | mae | 1.0000 | useful ranking but magnitude still noisy |

Most MFE/MAE heads show decile monotonicity, while return ranking is weaker for some families; magnitude calibration remains compressed/noisy and unstable by product class.

## 10. Root-Cause Classification
| model | gate | causes | evidence |
| --- | --- | --- | --- |
| 96677442 | positive_expected_value_after_costs | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| 96677442 | transaction_cost_sensitivity_not_collapsed | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| 96677442 | return_holdout_ood_q99_severity_acceptable | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal; model extrapolation; product-class instability; legitimate extreme market behavior | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 96677442 | mfe_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 8b7b96af | return_holdout_ood_q99_severity_acceptable | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal; model extrapolation; product-class instability; legitimate extreme market behavior | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 8b7b96af | mfe_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 8b7b96af | mfe_catastrophic_prediction_extrapolation_absent | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 8b7b96af | mae_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| e5c7ce8b | positive_expected_value_after_costs | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| e5c7ce8b | transaction_cost_sensitivity_not_collapsed | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| e5c7ce8b | return_holdout_ood_q99_severity_acceptable | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal; model extrapolation; product-class instability; legitimate extreme market behavior | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| e5c7ce8b | mfe_prediction_path_metric_sign_valid | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; unit/sign defect; model-family limitation | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels MFE target is nonnegative but Ridge can emit negative predictions |
| e5c7ce8b | mfe_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| e5c7ce8b | mfe_catastrophic_prediction_extrapolation_absent | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| e5c7ce8b | mae_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| e5c7ce8b | mae_catastrophic_prediction_extrapolation_absent | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| c152bfa0 | positive_expected_value_after_costs | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| c152bfa0 | transaction_cost_sensitivity_not_collapsed | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| c152bfa0 | mae_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 14ca47d4 | positive_expected_value_after_costs | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| 14ca47d4 | transaction_cost_sensitivity_not_collapsed | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| 14ca47d4 | mfe_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 14ca47d4 | mae_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 34665ce3 | positive_expected_value_after_costs | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| 34665ce3 | transaction_cost_sensitivity_not_collapsed | shared feature-screen defect; raw-percentage target heterogeneity; insufficient predictive signal | return heads reuse the primary positive-return feature screen; holdout rank correlations are weak |
| 34665ce3 | mfe_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 34665ce3 | mfe_catastrophic_prediction_extrapolation_absent | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 34665ce3 | mae_holdout_ood_q99_severity_acceptable | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |
| 34665ce3 | mae_catastrophic_prediction_extrapolation_absent | shared feature-screen defect; unsuitable loss/domain; raw-percentage target heterogeneity; model extrapolation; product-class instability; legitimate extreme market behavior | path heads are unconstrained squared-error regressors on heavy-tailed raw percent labels predictions exceed training q01/q99 bounds or target tails are dominated by high-volatility ETFs |

Summary classification:
- No label-definition or decimal-unit defect was found.
- A shared feature-screen implementation/design defect is proven for all three path-metric heads.
- MFE/MAE domain violations are possible because current regressors/losses are unconstrained.
- Raw percentage targets mix ordinary stocks, ordinary ETFs, leveraged ETFs, and inverse ETFs; this materially contributes to tail heterogeneity.
- OOD failures are a mix of tight training q01/q99 bounds, high-volatility product tails, model extrapolation for unconstrained families, and legitimate extreme market behavior.
- Several heads still show weak ranking signal, so model quality remains separate from the implementation defect.

## 11. Exactly One Next Correction
Give each path-metric head target-specific train-only feature screening.

Reason: this is the smallest proven engineering correction. Expected return, MFE, and MAE currently reuse the positive-return feature screen even though they optimize different continuous targets. Domain-preserving MFE/MAE methods and ATR-normalized targets may still be needed later, but the first correction should ensure every path-metric head receives a fair target-specific feature screen without changing labels, gates, thresholds, model families, or data.

## Read-Only Confirmation
- no source files changed by this task
- no model artifacts changed
- no SQLite state changed
- no scanner state changed
- no final-holdout state changed
