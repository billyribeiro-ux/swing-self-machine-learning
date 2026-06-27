# Remaining OOD Source Diagnosis

- Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`
- Development branch: `feat/product-class-specialist-challengers-v1`
- Generation: `2026-06-26T23:52:15.769542+00:00`
- Strongest current challenger checked first: `ORDINARY bull ExtraTrees` `987fd84dd17220ce2ae3062f`
- Selected OOD source for deep diagnosis: `POOLED bull HistGradientBoosting MAE` `85b258623a68620ad108b08c`
- Evidence status: read-only development-holdout diagnostic; not promotion evidence.

## Executive Finding

No learned model in this generation has a failing OOD Governance V2 mandatory gate. The strongest challenger, `987fd84dd17220ce2ae3062f`, has zero OOD counts for expected return, MFE, and MAE. The only remaining learned-model OOD pattern is six MAE holdout warnings in the POOLED bull HistGradientBoosting model. Those six warnings pass the frozen OOD rate and q99-severity limits, so this is a localized warning source rather than a current scanner or promotion blocker.

## 1. Top OOD Blocker Ranking

### Learned-Model OOD Status

| model ID | scope | direction | family | head | OOD rate | OOD count | q99 severity | max severity | gate status | reason | promotion impact | scanner impact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 85b258623a68620ad108b08c | POOLED | bull | hist_gradient_boosting | mae | 0.035% | 6 | 0.072861 | 0.073748 | PASS | All OOD governance gates pass. | no OOD promotion block | no OOD scanner block |

### OOD-Related Failed Mandatory Gates

The generation contains OOD failed mandatory gates only on naive controls. They remain controls, not eligible challenger models.

| model ID | scope | direction | family | head | OOD rate | OOD count | q99 severity | max severity | status | exact gate reason | promotion impact | scanner impact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| d55e34ff5d7f30c7d6b78191 | POOLED | bear | naive_base_rate | return | 5.167% | 882 | 0.261249 | 0.308546 | FAIL | Expected Return calibration OOD rate exceeds the 5% maximum.; Expected Return holdout OOD rate exceeds the frozen calibration-derived limit. | control-only; not promotion eligible | control-only |
| 088722934407be2d7a4d388a | LEVERAGED_INVERSE | bear | naive_base_rate | return | 3.519% | 103 | 0.216773 | 0.284884 | FAIL | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |
| 86a6ceb25f61fb5c53082bd1 | LEVERAGED_INVERSE | bull | naive_base_rate | return | 2.836% | 83 | 0.159741 | 0.165835 | FAIL | Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |
| 1fc9ec0a7414cea0d841576e | LEVERAGED_LONG | bear | naive_base_rate | return | 31.816% | 622 | 0.828546 | 0.963173 | FAIL | Expected Return calibration OOD rate exceeds the 5% maximum.; Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |
| 81b12bb11dc541dc96a30bc7 | LEVERAGED_LONG | bull | naive_base_rate | return | 14.731% | 288 | 0.730291 | 0.825511 | FAIL | Expected Return calibration OOD rate exceeds the 5% maximum.; Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |
| c69b62b0485d727ac5bd05b4 | INVERSE | bull | naive_base_rate | return | 7.574% | 74 | 0.740991 | 0.821089 | FAIL | Expected Return calibration OOD rate exceeds the 5% maximum.; Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |
| 3c6158ab285b9d83aece32a0 | INVERSE | bear | naive_base_rate | return | 6.653% | 65 | 0.685264 | 0.742390 | FAIL | Expected Return calibration OOD rate exceeds the 5% maximum.; Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |
| 076cc48b73da9fb0874d00d6 | ORDINARY | bear | naive_base_rate | return | 15.868% | 1779 | 0.602865 | 0.659531 | FAIL | Expected Return calibration OOD rate exceeds the 5% maximum.; Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |
| b75c8106841a08b539248c25 | ORDINARY | bull | naive_base_rate | return | 10.178% | 1141 | 0.516039 | 0.543994 | FAIL | Expected Return calibration OOD rate exceeds the 5% maximum.; Expected Return holdout OOD rate exceeds the frozen calibration-derived limit.; Expected Return holdout OOD q99 severity exceeds the frozen limit. | control-only; not promotion eligible | control-only |

### Strongest Challenger OOD Check

| head | OOD count | OOD rate | q99 severity | max severity |
| --- | --- | --- | --- | --- |
| return | 0 | 0.000% | 0.000000 | 0.000000 |
| mfe | 0 | 0.000% | 0.000000 | 0.000000 |
| mae | 0 | 0.000% | 0.000000 | 0.000000 |

Selection rationale: the requested default model was checked first and is OOD-clean. The selected deep-diagnosis source is therefore the only learned-model nonzero OOD warning in the generation: `POOLED bull HistGradientBoosting MAE`, six holdout rows, max severity 0.073748, below the frozen q99 limit 0.10.

## 2. Model-Level Context

| field | value |
| --- | --- |
| model ID | 85b258623a68620ad108b08c |
| scope | POOLED |
| direction | bull |
| family | hist_gradient_boosting |
| horizon | 10 sessions |
| prediction head | MAE |
| registry state | CANDIDATE |
| promotion eligibility | NO |
| scanner eligibility | NO actionable scanner eligibility; model is unpromoted development candidate |
| failed mandatory gates | final_holdout_required_for_promotion: Model holdout status is DEVELOPMENT_HOLDOUT; only FINAL_HOLDOUT models can be promoted. |
| selected observations | 96 |
| selected rate | 0.562% |
| selected symbols | AAPL, AMZN, GOOGL, MSFT, NVDA, QID, RWM, SH, SOXL, SQQQ, TNA, TQQQ, TZA, UPRO, XLB, XLE, XLF, XLK, XLY |
| selected dates | 2024-05-14 to 2026-03-24 |
| selected sectors | communication_services, consumer_discretionary, energy, financials, inverse_market, inverse_small_caps, inverse_technology_growth, leveraged_market, leveraged_semiconductors, leveraged_small_caps, leveraged_technology_growth, materials, semiconductors, technology |
| selected regimes | downtrend_high_vol, uptrend_high_vol, uptrend_low_vol |
| development holdout rows | 17070 |
| training rows | 41954 |
| calibration rows | 16835 |

Occurrence location: the OOD source is present only in development-holdout diagnostics. Calibration OOD count is `0`. No selected candidate row is affected; all six rows fail row-level selection before caps.

## 3. Head-Specific OOD Audit

| field | value |
| --- | --- |
| canonical external target name | label_bull_mae_10 |
| internal target representation | label_bull_mae_10__adverse_magnitude_atr_units_atr_pct_14 |
| estimator class | HistGradientBoostingRegressor |
| estimator loss | poisson |
| feature manifest hash | aba0d3947f2995f90f8490b55d4a59b774f8e8766d0452c8715ff35a917b4b3c |
| selected feature count | 60 |
| selected feature families | {"breadth":4,"inverse_leveraged":5,"market_relative":6,"regime":2,"relationship_graph":23,"returns_momentum":2,"rsi_family":3,"sector_relative":1,"technical_primitives":6,"trend_structure":4,"volatility_range":2,"volume_participation":2} |
| calibration method | not applicable to regression MAE head |
| training q01 | 0.009346 |
| training q99 | 8.288072 |
| robust range R | 8.278726 |
| calibration OOD rate | 0.000% |
| frozen OOD rate limit | 2.000% |
| holdout OOD rate | 0.035% |
| calibration q99 severity | 0.000000 |
| frozen q99 severity limit | 0.100000 |
| holdout q99 severity | 0.072861 |
| holdout maximum severity | 0.073748 |
| catastrophic severity count | 0 |
| sign-contract failures | 0 |
| nonfinite predictions | 0 |
| raw/internal prediction min/max | 0.768994 / 8.898610 |
| canonical prediction min/max | -0.779820 / -0.010822 |
| target min/max | -0.000000 / 10.912631 internal ATR units |
| prediction/target variance ratio | 0.407589 |

Failure type: OOD warning by holdout prediction exceeding the training q99 upper bound. It is not an OOD rate gate failure, not a q99-severity gate failure, not catastrophic extrapolation, not a sign-contract failure, not nonfinite prediction, and not missing metadata.

## 4. Extreme Row Inspection

| Date | symbol | scope | product role | sector | regime | head | prediction internal | prediction canonical | realized internal | realized canonical | bound low | bound high | severity | selected | prob pass | return pass | TBS pass | liquidity pass | candidate status | rejection reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-10-31 | DIA | POOLED | broad_market_etf | industrials_large_cap | uptrend_high_vol | MAE | 8.898610 | -0.091993 | 2.295579 | -0.023732 | 0.009346 | 8.288072 | 0.073748 | NO | YES | NO | NO | YES | REJECTED | expected_return_below_threshold;target_before_stop_below_threshold |
| 2025-10-31 | AMZN | POOLED | stock | consumer_discretionary | uptrend_high_vol | MAE | 8.751752 | -0.245592 | 3.135676 | -0.087993 | 0.009346 | 8.288072 | 0.056009 | NO | NO | NO | NO | YES | REJECTED | probability_below_threshold;expected_return_below_threshold;target_before_stop_below_threshold |
| 2025-10-31 | UPRO | POOLED | leveraged_long_etf | leveraged_market | uptrend_high_vol | MAE | 8.631768 | -0.253696 | 3.611065 | -0.106133 | 0.009346 | 8.288072 | 0.041516 | NO | NO | NO | NO | YES | REJECTED | probability_below_threshold;expected_return_below_threshold;target_before_stop_below_threshold |
| 2025-10-31 | TQQQ | POOLED | leveraged_long_etf | leveraged_technology_growth | uptrend_high_vol | MAE | 8.473042 | -0.319165 | 4.694483 | -0.176833 | 0.009346 | 8.288072 | 0.022343 | NO | NO | NO | NO | YES | REJECTED | probability_below_threshold;expected_return_below_threshold;target_before_stop_below_threshold |
| 2025-10-31 | XLK | POOLED | sector_etf | technology | uptrend_high_vol | MAE | 8.460686 | -0.134271 | 4.828249 | -0.076624 | 0.009346 | 8.288072 | 0.020850 | NO | NO | NO | NO | YES | REJECTED | probability_below_threshold;expected_return_below_threshold;target_before_stop_below_threshold |
| 2025-10-31 | NVDA | POOLED | stock | semiconductors | uptrend_high_vol | MAE | 8.460144 | -0.258487 | 4.588238 | -0.140186 | 0.009346 | 8.288072 | 0.020785 | NO | YES | NO | NO | YES | REJECTED | expected_return_below_threshold;target_before_stop_below_threshold |

- Symbols most often: `{'AMZN': 1, 'DIA': 1, 'NVDA': 1, 'TQQQ': 1, 'UPRO': 1, 'XLK': 1}`
- Dates most often: `{'2025-10-31': 6}`
- Regimes most often: `{'uptrend_high_vol': 6}`
- Product roles most often: `{'stock': 2, 'broad_market_etf': 1, 'leveraged_long_etf': 2, 'sector_etf': 1}`
- Sectors most often: `{'consumer_discretionary': 1, 'industrials_large_cap': 1, 'semiconductors': 1, 'leveraged_technology_growth': 1, 'leveraged_market': 1, 'technology': 1}`
- Cluster assessment: all six rows occur on `2025-10-31`; the source is fully concentrated in one development-holdout date.

## 5. Feature Contribution And Feature Abnormality

### Top MAE Features By Train-Only Mutual Information

| feature | family | MI |
| --- | --- | --- |
| relationship_mutual_info_spy_sh_63 | relationship_graph | 0.130805 |
| relationship_mutual_info_xlk_soxs_63 | relationship_graph | 0.129906 |
| relationship_corr_spy_sh_63 | relationship_graph | 0.122467 |
| inverse_confirmation_xlk_soxs_63 | inverse_leveraged | 0.120517 |
| inverse_confirmation_iwm_tna_63 | inverse_leveraged | 0.119114 |
| relationship_mutual_info_spy_sds_63 | relationship_graph | 0.117954 |
| inverse_confirmation_iwm_rwm_63 | inverse_leveraged | 0.117161 |
| inverse_confirmation_iwm_tza_63 | inverse_leveraged | 0.117101 |
| inverse_confirmation_qqq_sqqq_63 | inverse_leveraged | 0.114154 |
| relationship_corr_spy_sds_63 | relationship_graph | 0.113277 |
| relationship_mutual_info_iwm_rwm_63 | relationship_graph | 0.113180 |
| market_regime_volatility_score | regime | 0.112657 |
| relationship_mutual_info_spy_upro_63 | relationship_graph | 0.110947 |
| relationship_mutual_info_spy_spxu_63 | relationship_graph | 0.110300 |
| relationship_corr_spy_upro_63 | relationship_graph | 0.109725 |
| relationship_divergence_spy_spxu_5 | relationship_graph | 0.107914 |
| relationship_corr_qqq_tqqq_63 | relationship_graph | 0.105632 |
| relationship_divergence_qqq_qid_5 | relationship_graph | 0.105617 |
| iwm_return_5 | technical_primitives | 0.104696 |
| breadth_skew_20 | breadth | 0.104511 |
| qqq_return_20 | technical_primitives | 0.101400 |
| dia_return_20 | technical_primitives | 0.100433 |
| relationship_corr_spy_spxu_63 | relationship_graph | 0.100159 |
| market_regime_trend_score | regime | 0.099119 |
| relationship_divergence_xlk_soxl_5 | relationship_graph | 0.099107 |

### OOD Row Feature Abnormality Versus Training Distribution

| feature | family | MI | OOD mean | non-OOD holdout mean | max abs train-z | median train percentile | OOD missing count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| relationship_corr_spy_sh_63 | relationship_graph | 0.122467 | -0.975959 | -0.977597 | 3.177310 | 98.8% | 0 |
| inverse_confirmation_qqq_sqqq_63 | inverse_leveraged | 0.114154 | 0.996799 | 0.996763 | 2.362202 | 2.9% | 0 |
| relationship_mutual_info_spy_sh_63 | relationship_graph | 0.130805 | 1.523466 | 1.681280 | 2.089588 | 1.2% | 0 |
| breadth_skew_20 | breadth | 0.104511 | 2.016449 | 0.180314 | 2.050189 | 96.1% | 0 |
| inverse_confirmation_iwm_rwm_63 | inverse_leveraged | 0.117161 | 0.994314 | 0.991062 | 1.333516 | 9.5% | 0 |
| relationship_mutual_info_iwm_rwm_63 | relationship_graph | 0.113180 | 2.239727 | 2.128870 | 1.319680 | 9.5% | 0 |
| relationship_corr_qqq_tqqq_63 | relationship_graph | 0.105632 | 0.999801 | 0.999627 | 1.002071 | 97.7% | 0 |
| relationship_mutual_info_spy_sds_63 | relationship_graph | 0.117954 | 2.086070 | 2.110518 | 0.971481 | 19.9% | 0 |
| inverse_confirmation_iwm_tna_63 | inverse_leveraged | 0.119114 | 0.999374 | 0.999217 | 0.918055 | 92.2% | 0 |
| relationship_divergence_xlk_soxl_5 | relationship_graph | 0.099107 | 0.132008 | 0.028035 | 0.761563 | 80.1% | 0 |
| relationship_corr_spy_sds_63 | relationship_graph | 0.113277 | -0.992260 | -0.991187 | 0.613813 | 80.1% | 0 |
| market_regime_trend_score | regime | 0.099119 | 0.080628 | 0.039324 | 0.613000 | 78.5% | 0 |
| relationship_mutual_info_spy_spxu_63 | relationship_graph | 0.110300 | 2.238156 | 2.301236 | 0.608890 | 22.8% | 0 |
| relationship_mutual_info_spy_upro_63 | relationship_graph | 0.110947 | 2.863149 | 2.926344 | 0.604855 | 65.8% | 0 |
| relationship_corr_spy_upro_63 | relationship_graph | 0.109725 | 0.998369 | 0.998533 | 0.565047 | 65.8% | 0 |
| inverse_confirmation_iwm_tza_63 | inverse_leveraged | 0.117101 | 0.998736 | 0.998619 | 0.525993 | 57.9% | 0 |
| relationship_divergence_qqq_qid_5 | relationship_graph | 0.105617 | -0.018158 | -0.003442 | 0.482509 | 29.2% | 0 |
| qqq_return_20 | technical_primitives | 0.101400 | 0.042923 | 0.015577 | 0.481928 | 66.7% | 0 |
| iwm_return_5 | technical_primitives | 0.104696 | -0.012829 | 0.003672 | 0.425488 | 26.0% | 0 |
| inverse_confirmation_xlk_soxs_63 | inverse_leveraged | 0.120517 | 0.874640 | 0.890225 | 0.215952 | 51.2% | 0 |
| dia_return_20 | technical_primitives | 0.100433 | 0.017454 | 0.009622 | 0.171884 | 53.5% | 0 |
| relationship_divergence_spy_spxu_5 | relationship_graph | 0.107914 | -0.011884 | -0.005700 | 0.123183 | 47.6% | 0 |
| relationship_corr_spy_spxu_63 | relationship_graph | 0.100159 | -0.994296 | -0.994434 | 0.099775 | 77.2% | 0 |
| market_regime_volatility_score | regime | 0.112657 | 0.009268 | 0.009122 | 0.078710 | 59.8% | 0 |
| relationship_mutual_info_xlk_soxs_63 | relationship_graph | 0.129906 | 0.724074 | 0.869285 | 0.035957 | 51.2% | 0 |

### Persisted MAE Permutation Importance By Family

| family | features | positive sum delta MAE | top feature | top delta MAE |
| --- | --- | --- | --- | --- |
| inverse_leveraged | 5 | 0.002124 | inverse_confirmation_iwm_rwm_63 | 0.001961 |
| relationship_graph | 23 | 0.000863 | relationship_mutual_info_xlk_soxs_63 | 0.000265 |
| market_relative | 6 | 0.000507 | rolling_corr_vs_dia_63 | 0.000389 |
| regime | 2 | 0.000451 | market_regime_volatility_score | 0.000451 |
| technical_primitives | 6 | 0.000398 | spy_return_20 | 0.000223 |
| trend_structure | 4 | 0.000365 | distance_prior_low_252 | 0.000180 |
| rsi_family | 3 | 0.000232 | rsi_26_percentile_252 | 0.000091 |
| volume_participation | 2 | 0.000137 | down_volume_proxy_20 | 0.000137 |
| sector_relative | 1 | 0.000113 | sector_momentum_mean_20 | 0.000113 |
| volatility_range | 2 | 0.000064 | volatility_expansion_20_63 | 0.000039 |
| breadth | 4 | 0.000045 | breadth_skew_20 | 0.000045 |
| returns_momentum | 2 | 0.000000 | return_40 | -0.000178 |

Feature-behavior classification: the warnings do not reduce to a single sanitized or nonfinite feature. The strongest abnormal finite values on the six rows come from the selected MAE feature set and appear as date/regime interactions in tree predictions. Tree-split path attribution is not persisted for HistGradientBoosting artifacts, so this report does not claim causal feature attribution.

## 6. Target Distribution And Product-Class Audit

| scope | split | count | min | p01 | p05 | p25 | median | p75 | p95 | p99 | max | mean | std | skew | kurtosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POOLED | training | 50785 | -0.000000 | 0.009346 | 0.102373 | 0.575865 | 1.313922 | 2.417049 | 4.806816 | 8.288072 | 18.033074 | 1.760964 | 1.726872 | 2.560910 | 11.435330 |
| POOLED | development_holdout | 17325 | -0.000000 | 0.014416 | 0.110405 | 0.594775 | 1.344776 | 2.378520 | 4.629205 | 6.909558 | 10.912631 | 1.708476 | 1.492423 | 1.637083 | 3.812567 |
| ORDINARY | training | 33205 | -0.000000 | 0.008245 | 0.093636 | 0.512320 | 1.234365 | 2.421036 | 5.093932 | 9.199393 | 18.033074 | 1.769228 | 1.854967 | 2.598968 | 10.871759 |
| ORDINARY | development_holdout | 11385 | -0.000000 | 0.014391 | 0.101715 | 0.557626 | 1.293378 | 2.395063 | 4.791529 | 7.206380 | 10.912631 | 1.717916 | 1.565382 | 1.693336 | 3.919981 |
| LEVERAGED_LONG | training | 5860 | -0.000000 | -0.000000 | 0.078893 | 0.508216 | 1.311480 | 2.557643 | 5.120937 | 8.837681 | 16.938722 | 1.821870 | 1.868374 | 2.420537 | 9.715266 |
| LEVERAGED_LONG | development_holdout | 1980 | -0.000000 | 0.015876 | 0.102526 | 0.587521 | 1.374623 | 2.568586 | 5.144983 | 6.916931 | 9.096901 | 1.796501 | 1.581026 | 1.353285 | 1.817351 |
| INVERSE | training | 2930 | -0.000000 | 0.000000 | 0.157291 | 0.789492 | 1.480552 | 2.351660 | 4.028918 | 5.620317 | 10.217843 | 1.707598 | 1.253173 | 1.334608 | 3.167776 |
| INVERSE | development_holdout | 990 | -0.000000 | -0.000000 | 0.155104 | 0.714879 | 1.451436 | 2.349840 | 3.992160 | 6.020657 | 8.377992 | 1.682228 | 1.283093 | 1.457391 | 3.707052 |
| LEVERAGED_INVERSE | training | 8790 | -0.000000 | 0.028413 | 0.178299 | 0.834021 | 1.507268 | 2.369553 | 3.889271 | 5.231607 | 9.915150 | 1.706933 | 1.172033 | 1.050964 | 1.668858 |
| LEVERAGED_INVERSE | development_holdout | 2970 | -0.000000 | 0.023039 | 0.140793 | 0.739146 | 1.429590 | 2.251810 | 3.737266 | 5.244174 | 8.349934 | 1.622356 | 1.170939 | 1.215142 | 2.456128 |

Realized-target support check: `0` of the six OOD rows have realized internal MAE above the training q99 bound. The OOD event is therefore prediction-support exceedance, not a realized-target tail breach on these rows.

## 7. Temporal And Regime Stability

### Chronological Segment

| group | rows | OOD count | OOD rate | mean severity | max severity | target mean | pred mean | error mean | error p95 | error p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| late | 5690 | 6 | 0.105% | 0.039208 | 0.073748 | 3.858882 | 8.612667 | 4.753785 | 6.356292 | 6.553683 |
| early | 5690 | 0 | 0.000% | 0.000000 | 0.000000 | nan | nan | nan | nan | nan |
| middle | 5690 | 0 | 0.000% | 0.000000 | 0.000000 | nan | nan | nan | nan | nan |

### Calendar Year

| group | rows | OOD count | OOD rate | mean severity | max severity | target mean | pred mean | error mean | error p95 | error p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025 | 8659 | 6 | 0.069% | 0.039208 | 0.073748 | 3.858882 | 8.612667 | 4.753785 | 6.356292 | 6.553683 |
| 2024 | 5678 | 0 | 0.000% | 0.000000 | 0.000000 | nan | nan | nan | nan | nan |
| 2026 | 2733 | 0 | 0.000% | 0.000000 | 0.000000 | nan | nan | nan | nan | nan |

### Month

| group | rows | OOD count | OOD rate | mean severity | max severity | target mean | pred mean | error mean | error p95 | error p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-10 | 791 | 6 | 0.759% | 0.039208 | 0.073748 | 3.858882 | 8.612667 | 4.753785 | 6.356292 | 6.553683 |

### Market Regime

| group | rows | OOD count | OOD rate | mean severity | max severity | target mean | pred mean | error mean | error p95 | error p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| uptrend_high_vol | 6084 | 6 | 0.099% | 0.039208 | 0.073748 | 3.858882 | 8.612667 | 4.753785 | 6.356292 | 6.553683 |
| downtrend_high_vol | 3035 | 0 | 0.000% | 0.000000 | 0.000000 | nan | nan | nan | nan | nan |
| mixed | 245 | 0 | 0.000% | 0.000000 | 0.000000 | nan | nan | nan | nan | nan |
| uptrend_low_vol | 7706 | 0 | 0.000% | 0.000000 | 0.000000 | nan | nan | nan | nan | nan |

### Volatility Regime

| group | rows | OOD count | OOD rate | mean severity | max severity | target mean | pred mean | error mean | error p95 | error p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mid_atr | 5690 | 4 | 0.070% | 0.034790 | 0.056009 | 4.040807 | 8.576088 | 4.535281 | 5.526771 | 5.598215 |
| low_atr | 5690 | 1 | 0.018% | 0.073748 | 0.073748 | 2.295579 | 8.898610 | 6.603031 | 6.603031 | 6.603031 |
| high_atr | 5690 | 1 | 0.018% | 0.022343 | 0.022343 | 4.694483 | 8.473042 | 3.778559 | 3.778559 | 3.778559 |

### Symbol

| group | rows | OOD count | OOD rate | mean severity | max severity | target mean | pred mean | error mean | error p95 | error p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AMZN | 495 | 1 | 0.202% | 0.056009 | 0.056009 | 3.135676 | 8.751752 | 5.616077 | 5.616077 | 5.616077 |
| DIA | 494 | 1 | 0.202% | 0.073748 | 0.073748 | 2.295579 | 8.898610 | 6.603031 | 6.603031 | 6.603031 |
| NVDA | 492 | 1 | 0.203% | 0.020785 | 0.020785 | 4.588238 | 8.460144 | 3.871906 | 3.871906 | 3.871906 |
| TQQQ | 490 | 1 | 0.204% | 0.022343 | 0.022343 | 4.694483 | 8.473042 | 3.778559 | 3.778559 | 3.778559 |
| UPRO | 487 | 1 | 0.205% | 0.041516 | 0.041516 | 3.611065 | 8.631768 | 5.020703 | 5.020703 | 5.020703 |
| XLK | 480 | 1 | 0.208% | 0.020850 | 0.020850 | 4.828249 | 8.460686 | 3.632436 | 3.632436 | 3.632436 |

### Sector

| group | rows | OOD count | OOD rate | mean severity | max severity | target mean | pred mean | error mean | error p95 | error p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| consumer_discretionary | 1472 | 1 | 0.068% | 0.056009 | 0.056009 | 3.135676 | 8.751752 | 5.616077 | 5.616077 | 5.616077 |
| industrials_large_cap | 494 | 1 | 0.202% | 0.073748 | 0.073748 | 2.295579 | 8.898610 | 6.603031 | 6.603031 | 6.603031 |
| leveraged_market | 487 | 1 | 0.205% | 0.041516 | 0.041516 | 3.611065 | 8.631768 | 5.020703 | 5.020703 | 5.020703 |
| leveraged_technology_growth | 490 | 1 | 0.204% | 0.022343 | 0.022343 | 4.694483 | 8.473042 | 3.778559 | 3.778559 | 3.778559 |
| semiconductors | 976 | 1 | 0.102% | 0.020785 | 0.020785 | 4.588238 | 8.460144 | 3.871906 | 3.871906 | 3.871906 |
| technology | 1447 | 1 | 0.069% | 0.020850 | 0.020850 | 4.828249 | 8.460686 | 3.632436 | 3.632436 | 3.632436 |

Temporal classification: concentrated in one period and one date, with mixed ordinary and leveraged-long symbols. It is not spread across the holdout and not tied exclusively to one ticker.

## 8. Comparison Against Matched Product-Class Specialists

The selected source is a POOLED model, so the requested specialist-versus-pooled comparison is not directly applicable. The relevant reverse comparison is POOLED bull HistGradientBoosting MAE against matching bull HistGradientBoosting specialists on the same product cohorts affected by the OOD rows.

| scope | specialist model | rows | pooled OOD count | pooled OOD rate | pooled q99 | pooled max | specialist OOD count | specialist OOD rate | specialist q99 | specialist max | pooled MAE error | specialist MAE error | specialist failed gates | specialist selected rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ORDINARY | d2cb923822ac85c39ef064fd | 11211 | 4 | 0.036% | 0.073216 | 0.073748 | 0 | 0.000% | 0.000000 | 0.000000 | 1.514390 | 1.286981 | 2 | 62 |
| LEVERAGED_LONG | 6a05487b4b50789bfa491001 | 1955 | 2 | 0.102% | 0.041324 | 0.041516 | 0 | 0.000% | 0.000000 | 0.000000 | 1.495106 | 1.231965 | 2 | 18 |

Specialization assessment: product-class specialization removes this exact pooled MAE OOD source on the affected ORDINARY and LEVERAGED_LONG cohorts. That does not make the specialists promotion-ready; their remaining blockers are development evidence and selected-sample gates, not this OOD source.

## 9. Root-Cause Classification

| classification | measured evidence |
| --- | --- |
| estimator extrapolation | HGB MAE internal predictions exceed the training q99 bound on six rows while realized targets do not exceed that bound. |
| product-class heterogeneity | The six pooled rows mix ordinary stock/ETF symbols and leveraged-long ETFs; matched ORDINARY and LEVERAGED_LONG specialists show zero MAE OOD rows on their same cohorts. |
| regime shift / localized date effect | All six warnings occur on 2025-10-31, so the pattern is date-concentrated rather than persistent across holdout. |
| model-family limitation | The source is specific to POOLED bull HistGradientBoosting MAE; other learned heads and the strongest ORDINARY bull ExtraTrees challenger have zero OOD counts. |
| not a feature-sanitization defect | Post-fix generation has finite predictions; selected model has post-sanitization invalid count 0 and no nonfinite predictions. |
| not an OOD bound-definition defect | Bounds are training-target q01/q99, direction/head/horizon mapping is valid, and q99/max severity remain within OOD Governance V2 limits. |

## 10. One Next Correction

Exactly one smallest next engineering correction: add robust target transformation for the POOLED bull HistGradientBoosting MAE head.

Rationale: the only learned OOD source is not nonfinite, not a label defect, not a gate failure, and not a realized target-tail breach. It is a small HGB MAE prediction-support exceedance concentrated in one date; a head-specific robust transformation is narrower than changing scopes, weakening OOD governance, or redesigning all path targets.

## 11. Immutability Verification

| item | value |
| --- | --- |
| development Git status before | ## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1 |
| development Git status after | ## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1 ?? docs/REMAINING_OOD_SOURCE_DIAGNOSIS.md |
| development SQLite size before/after | 275734528 / 275734528 |
| development SQLite mtime_ns before/after | 1782521879429638251 / 1782521879429638251 |
| representative artifact size before/after | 30692731 / 30692731 |
| representative artifact mtime_ns before/after | 1782518543075463537 / 1782518543075463537 |
| development scanner snapshot count before/after | 2 / 2 |
| development forward-event count before/after | 0 / 0 |
| development final-holdout run count before/after | 0 / 0 |
| operational HEAD before/after | 3f3c4f853cc183e6a0a4900dadc428162c400ef7 / 3f3c4f853cc183e6a0a4900dadc428162c400ef7 |
| operational Git status before | ## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1 |
| operational Git status after | ## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1 |
| operational prospective run ID before/after | 3493ee8ac37bf96475c362e1 / 3493ee8ac37bf96475c362e1 |
| operational final-holdout event count before/after | 0 / 0 |

Confirmations:

- no source files changed: `YES`
- no model artifacts changed: `YES`
- no SQLite state changed: `YES`
- no scanner state changed: `YES`
- no forward state changed: `YES`
- no final-holdout state changed: `YES`
- no operational state changed: `YES`

