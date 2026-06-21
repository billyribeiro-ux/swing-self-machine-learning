# Target-Before-Stop Model Diagnosis

- Generation audited: `2026-06-21T17:44:33.265191+00:00`
- Report generated: `2026-06-21` from local persisted artifacts only
- Modeling panel: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`
- Registry: `state/engine.sqlite3`
- Constraints honored: no code change, no retrain, no data update, no threshold change, no promotion, no forward-update.
- Learned models means `logistic_regression`, `hist_gradient_boosting`, and `extra_trees`; `naive_base_rate` rows from the same generation are treated only as controls.

## Executive finding

The target-before-stop head is not selecting from the feature families that the project added to explain market, sector, inverse/leveraged ETF, breadth, relationship, or regime behavior. All six learned target-before-stop heads use only price/trend, returns, volatility, volume, candle, and a few RSI columns. The generated panel contains those richer families, but the model feature screen chose the first bounded feature set and the mutual-information screen is keyed to the positive-return classifier target, not to `label_{direction}_target_before_stop_10`.

The immediate selection bottleneck is the frozen `target_before_stop_probability >= 0.50` gate. Four of six learned models produce zero holdout rows through that gate. The two models that do pass it select only leveraged inverse ETFs, with 100% of selected rows in 2024 or 2026. Manual label checks matched the stored labels, so this diagnosis did not find a target-before-stop label computation defect.

## Model set
|model|state|train|calibration|holdout|artifact|failed_mandatory_gates|
|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|CANDIDATE|2016-06-20 to 2022-04-28|2022-05-13 to 2024-04-17|2024-05-02 to 2026-04-22|1f47da026690ecc681d1ae1a.joblib|5|
|bear/hist_gradient_boosting/58ee8cd6|CANDIDATE|2016-06-20 to 2022-04-28|2022-05-13 to 2024-04-17|2024-05-02 to 2026-04-22|58ee8cd6b31fb509565898ef.joblib|14|
|bear/logistic_regression/94fce54c|CANDIDATE|2016-06-20 to 2022-04-28|2022-05-13 to 2024-04-17|2024-05-02 to 2026-04-22|94fce54c154b24e80c34e83e.joblib|16|
|bull/extra_trees/d90e8c92|CANDIDATE|2016-06-20 to 2022-04-28|2022-05-13 to 2024-04-17|2024-05-02 to 2026-04-22|d90e8c92c47fb47e490c0979.joblib|11|
|bull/hist_gradient_boosting/7be25053|CANDIDATE|2016-06-20 to 2022-04-28|2022-05-13 to 2024-04-17|2024-05-02 to 2026-04-22|7be25053a2032e48c91efe8f.joblib|7|
|bull/logistic_regression/49a8608f|CANDIDATE|2016-06-20 to 2022-04-28|2022-05-13 to 2024-04-17|2024-05-02 to 2026-04-22|49a8608f22994e639c6c94d3.joblib|14|

## Complete Failed Mandatory-Gate Tables
### bear/extra_trees/1f47da02
|gate_id|status|scope|metric|actual|comparator|threshold|reason|
|---|---|---|---|---|---|---|---|
|symbol_concentration_max_050|FAIL|selected_candidates|symbol_concentration_top|0.8333333333333334|<=|0.5|Symbol concentration 83.33% exceeds the maximum 50.00%.|
|sector_concentration_max_080|FAIL|selected_candidates|sector_concentration_top|0.8333333333333334|<=|0.8|Sector concentration 83.33% exceeds the maximum 80.00%.|
|exceptional_period_concentration_max_060|FAIL|selected_candidates|exceptional_period_concentration_top|1.0|<=|0.6|Exceptional-period concentration 100.00% exceeds the maximum 60.00%.|
|return_holdout_ood_q99_severity_acceptable|FAIL|regression:return|return_holdout_ood_q99_severity|0.3563008268417328|<=|0.1|Expected Return holdout OOD q99 severity exceeds the frozen limit.|
|mfe_holdout_ood_q99_severity_acceptable|FAIL|regression:mfe|mfe_holdout_ood_q99_severity|0.8977322741430462|<=|0.3204703337427404|MFE holdout OOD q99 severity exceeds the frozen limit.|

### bear/hist_gradient_boosting/58ee8cd6
|gate_id|status|scope|metric|actual|comparator|threshold|reason|
|---|---|---|---|---|---|---|---|
|positive_expected_value_after_costs|FAIL|selected_candidates|holdout_mean_return_lcb_90|NOT_AVAILABLE|>|-0.0005|Lower confidence bound is missing or below cost threshold.|
|profit_factor_min_090|FAIL|selected_candidates|holdout_profit_factor|NOT_AVAILABLE|>=|0.9|Profit factor is unavailable because no selected observations exist.|
|portfolio_drawdown_available|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|is finite|finite|Portfolio drawdown is missing.|
|portfolio_drawdown_not_worse_than_50pct|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|>|-0.5|Portfolio drawdown is missing or worse than configured limit.|
|symbol_concentration_max_050|NOT_APPLICABLE|selected_candidates|symbol_concentration_top|NOT_AVAILABLE|<=|0.5|Symbol concentration is unavailable because no rows were selected.|
|sector_concentration_max_080|NOT_APPLICABLE|selected_candidates|sector_concentration_top|NOT_AVAILABLE|<=|0.8|Sector concentration is unavailable because no rows were selected.|
|transaction_cost_sensitivity_not_collapsed|FAIL|selected_candidates|holdout_double_cost_lcb_90|NOT_AVAILABLE|>|-0.001|Double-cost lower confidence bound fails or is missing.|
|temporal_fold_stability_evidence_available|FAIL|selected_candidates|temporal_fold_evidence_status|UNAVAILABLE|is available|AVAILABLE|Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.|
|temporal_fold_stability_min_050|NOT_APPLICABLE|selected_candidates|temporal_fold_positive_fraction|NOT_AVAILABLE|>=|0.5|Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.|
|exceptional_period_concentration_max_060|NOT_APPLICABLE|selected_candidates|exceptional_period_concentration_top|NOT_AVAILABLE|<=|0.6|Exceptional-period concentration is unavailable because no rows were selected.|
|return_holdout_ood_q99_severity_acceptable|FAIL|regression:return|return_holdout_ood_q99_severity|0.7285757828135856|<=|0.1794269354370951|Expected Return holdout OOD q99 severity exceeds the frozen limit.|
|mfe_holdout_ood_q99_severity_acceptable|FAIL|regression:mfe|mfe_holdout_ood_q99_severity|2.4665029869961637|<=|0.5|MFE holdout OOD q99 severity exceeds the frozen limit.|
|mfe_catastrophic_prediction_extrapolation_absent|FAIL|regression:mfe|mfe_holdout_ood_max_severity|2.605458913426661|<=|1.0|MFE maximum holdout OOD severity exceeds 1.00.|
|mae_holdout_ood_q99_severity_acceptable|FAIL|regression:mae|mae_holdout_ood_q99_severity|0.16188464585860188|<=|0.1|MAE holdout OOD q99 severity exceeds the frozen limit.|

### bear/logistic_regression/94fce54c
|gate_id|status|scope|metric|actual|comparator|threshold|reason|
|---|---|---|---|---|---|---|---|
|positive_expected_value_after_costs|FAIL|selected_candidates|holdout_mean_return_lcb_90|NOT_AVAILABLE|>|-0.0005|Lower confidence bound is missing or below cost threshold.|
|profit_factor_min_090|FAIL|selected_candidates|holdout_profit_factor|NOT_AVAILABLE|>=|0.9|Profit factor is unavailable because no selected observations exist.|
|portfolio_drawdown_available|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|is finite|finite|Portfolio drawdown is missing.|
|portfolio_drawdown_not_worse_than_50pct|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|>|-0.5|Portfolio drawdown is missing or worse than configured limit.|
|symbol_concentration_max_050|NOT_APPLICABLE|selected_candidates|symbol_concentration_top|NOT_AVAILABLE|<=|0.5|Symbol concentration is unavailable because no rows were selected.|
|sector_concentration_max_080|NOT_APPLICABLE|selected_candidates|sector_concentration_top|NOT_AVAILABLE|<=|0.8|Sector concentration is unavailable because no rows were selected.|
|transaction_cost_sensitivity_not_collapsed|FAIL|selected_candidates|holdout_double_cost_lcb_90|NOT_AVAILABLE|>|-0.001|Double-cost lower confidence bound fails or is missing.|
|temporal_fold_stability_evidence_available|FAIL|selected_candidates|temporal_fold_evidence_status|UNAVAILABLE|is available|AVAILABLE|Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.|
|temporal_fold_stability_min_050|NOT_APPLICABLE|selected_candidates|temporal_fold_positive_fraction|NOT_AVAILABLE|>=|0.5|Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.|
|exceptional_period_concentration_max_060|NOT_APPLICABLE|selected_candidates|exceptional_period_concentration_top|NOT_AVAILABLE|<=|0.6|Exceptional-period concentration is unavailable because no rows were selected.|
|return_holdout_ood_q99_severity_acceptable|FAIL|regression:return|return_holdout_ood_q99_severity|0.4633549536683444|<=|0.1|Expected Return holdout OOD q99 severity exceeds the frozen limit.|
|mfe_prediction_path_metric_sign_valid|FAIL|regression:mfe|mfe_prediction_path_metric_sign_valid|False|is true|True|MFE path-metric sign contract failed.|
|mfe_holdout_ood_q99_severity_acceptable|FAIL|regression:mfe|mfe_holdout_ood_q99_severity|0.8073367572935206|<=|0.14874613277193705|MFE holdout OOD q99 severity exceeds the frozen limit.|
|mfe_catastrophic_prediction_extrapolation_absent|FAIL|regression:mfe|mfe_holdout_ood_max_severity|2.8999983480153424|<=|1.0|MFE maximum holdout OOD severity exceeds 1.00.|
|mae_holdout_ood_q99_severity_acceptable|FAIL|regression:mae|mae_holdout_ood_q99_severity|1.4882029007490931|<=|0.1|MAE holdout OOD q99 severity exceeds the frozen limit.|
|mae_catastrophic_prediction_extrapolation_absent|FAIL|regression:mae|mae_holdout_ood_max_severity|1.573494329448852|<=|1.0|MAE maximum holdout OOD severity exceeds 1.00.|

### bull/extra_trees/d90e8c92
|gate_id|status|scope|metric|actual|comparator|threshold|reason|
|---|---|---|---|---|---|---|---|
|positive_expected_value_after_costs|FAIL|selected_candidates|holdout_mean_return_lcb_90|NOT_AVAILABLE|>|-0.0005|Lower confidence bound is missing or below cost threshold.|
|profit_factor_min_090|FAIL|selected_candidates|holdout_profit_factor|NOT_AVAILABLE|>=|0.9|Profit factor is unavailable because no selected observations exist.|
|portfolio_drawdown_available|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|is finite|finite|Portfolio drawdown is missing.|
|portfolio_drawdown_not_worse_than_50pct|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|>|-0.5|Portfolio drawdown is missing or worse than configured limit.|
|symbol_concentration_max_050|NOT_APPLICABLE|selected_candidates|symbol_concentration_top|NOT_AVAILABLE|<=|0.5|Symbol concentration is unavailable because no rows were selected.|
|sector_concentration_max_080|NOT_APPLICABLE|selected_candidates|sector_concentration_top|NOT_AVAILABLE|<=|0.8|Sector concentration is unavailable because no rows were selected.|
|transaction_cost_sensitivity_not_collapsed|FAIL|selected_candidates|holdout_double_cost_lcb_90|NOT_AVAILABLE|>|-0.001|Double-cost lower confidence bound fails or is missing.|
|temporal_fold_stability_evidence_available|FAIL|selected_candidates|temporal_fold_evidence_status|UNAVAILABLE|is available|AVAILABLE|Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.|
|temporal_fold_stability_min_050|NOT_APPLICABLE|selected_candidates|temporal_fold_positive_fraction|NOT_AVAILABLE|>=|0.5|Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.|
|exceptional_period_concentration_max_060|NOT_APPLICABLE|selected_candidates|exceptional_period_concentration_top|NOT_AVAILABLE|<=|0.6|Exceptional-period concentration is unavailable because no rows were selected.|
|mae_holdout_ood_q99_severity_acceptable|FAIL|regression:mae|mae_holdout_ood_q99_severity|0.13600065927970195|<=|0.1|MAE holdout OOD q99 severity exceeds the frozen limit.|

### bull/hist_gradient_boosting/7be25053
|gate_id|status|scope|metric|actual|comparator|threshold|reason|
|---|---|---|---|---|---|---|---|
|positive_expected_value_after_costs|FAIL|selected_candidates|holdout_mean_return_lcb_90|-0.011979439801812507|>|-0.0005|Lower confidence bound is missing or below cost threshold.|
|symbol_concentration_max_050|FAIL|selected_candidates|symbol_concentration_top|1.0|<=|0.5|Symbol concentration 100.00% exceeds the maximum 50.00%.|
|sector_concentration_max_080|FAIL|selected_candidates|sector_concentration_top|1.0|<=|0.8|Sector concentration 100.00% exceeds the maximum 80.00%.|
|transaction_cost_sensitivity_not_collapsed|FAIL|selected_candidates|holdout_double_cost_lcb_90|-0.012479439801812507|>|-0.001|Double-cost lower confidence bound fails or is missing.|
|exceptional_period_concentration_max_060|FAIL|selected_candidates|exceptional_period_concentration_top|1.0|<=|0.6|Exceptional-period concentration 100.00% exceeds the maximum 60.00%.|
|mfe_holdout_ood_q99_severity_acceptable|FAIL|regression:mfe|mfe_holdout_ood_q99_severity|0.41391221894428215|<=|0.17305160176769163|MFE holdout OOD q99 severity exceeds the frozen limit.|
|mae_holdout_ood_q99_severity_acceptable|FAIL|regression:mae|mae_holdout_ood_q99_severity|0.16427361187315|<=|0.13358435606463998|MAE holdout OOD q99 severity exceeds the frozen limit.|

### bull/logistic_regression/49a8608f
|gate_id|status|scope|metric|actual|comparator|threshold|reason|
|---|---|---|---|---|---|---|---|
|positive_expected_value_after_costs|FAIL|selected_candidates|holdout_mean_return_lcb_90|NOT_AVAILABLE|>|-0.0005|Lower confidence bound is missing or below cost threshold.|
|profit_factor_min_090|FAIL|selected_candidates|holdout_profit_factor|NOT_AVAILABLE|>=|0.9|Profit factor is unavailable because no selected observations exist.|
|portfolio_drawdown_available|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|is finite|finite|Portfolio drawdown is missing.|
|portfolio_drawdown_not_worse_than_50pct|FAIL|portfolio_holdout|portfolio_max_drawdown|NOT_AVAILABLE|>|-0.5|Portfolio drawdown is missing or worse than configured limit.|
|symbol_concentration_max_050|NOT_APPLICABLE|selected_candidates|symbol_concentration_top|NOT_AVAILABLE|<=|0.5|Symbol concentration is unavailable because no rows were selected.|
|sector_concentration_max_080|NOT_APPLICABLE|selected_candidates|sector_concentration_top|NOT_AVAILABLE|<=|0.8|Sector concentration is unavailable because no rows were selected.|
|transaction_cost_sensitivity_not_collapsed|FAIL|selected_candidates|holdout_double_cost_lcb_90|NOT_AVAILABLE|>|-0.001|Double-cost lower confidence bound fails or is missing.|
|temporal_fold_stability_evidence_available|FAIL|selected_candidates|temporal_fold_evidence_status|UNAVAILABLE|is available|AVAILABLE|Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.|
|temporal_fold_stability_min_050|NOT_APPLICABLE|selected_candidates|temporal_fold_positive_fraction|NOT_AVAILABLE|>=|0.5|Temporal-fold stability threshold cannot be evaluated because valid temporal-fold evidence is unavailable.|
|exceptional_period_concentration_max_060|NOT_APPLICABLE|selected_candidates|exceptional_period_concentration_top|NOT_AVAILABLE|<=|0.6|Exceptional-period concentration is unavailable because no rows were selected.|
|mfe_holdout_ood_q99_severity_acceptable|FAIL|regression:mfe|mfe_holdout_ood_q99_severity|1.5354204130261455|<=|0.1|MFE holdout OOD q99 severity exceeds the frozen limit.|
|mfe_catastrophic_prediction_extrapolation_absent|FAIL|regression:mfe|mfe_holdout_ood_max_severity|1.634114138390293|<=|1.0|MFE maximum holdout OOD severity exceeds 1.00.|
|mae_holdout_ood_q99_severity_acceptable|FAIL|regression:mae|mae_holdout_ood_q99_severity|2.1139662596739446|<=|0.1|MAE holdout OOD q99 severity exceeds the frozen limit.|
|mae_catastrophic_prediction_extrapolation_absent|FAIL|regression:mae|mae_holdout_ood_max_severity|2.407967075369824|<=|1.0|MAE maximum holdout OOD severity exceeds 1.00.|

## Selection Funnel

Counts are cumulative in the order shown. `selected_after_caps` applies the persisted top-N/per-date caps after all threshold checks.
|model|holdout_rows|pass_probability_threshold|pass_expected_return_threshold|pass_target_before_stop_threshold|pass_liquidity_threshold|pass_all_thresholds|selected_after_caps|
|---|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|17069|1668|1467|6|6|6|6|
|bear/hist_gradient_boosting/58ee8cd6|17069|718|676|0|0|0|0|
|bear/logistic_regression/94fce54c|17069|2049|1965|0|0|0|0|
|bull/extra_trees/d90e8c92|17069|11407|7831|0|0|0|0|
|bull/hist_gradient_boosting/7be25053|17069|11882|10624|5|5|5|5|
|bull/logistic_regression/49a8608f|17069|13066|9548|0|0|0|0|

## Target-Before-Stop Head Audit

### Label Base Rate and Class Balance
|model|split|rows|positive|negative|positive_rate|
|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|training|41884|10894|30990|0.260099|
|bear/extra_trees/1f47da02|calibration|16800|4334|12466|0.257976|
|bear/extra_trees/1f47da02|holdout|17069|4414|12655|0.258597|
|bear/hist_gradient_boosting/58ee8cd6|training|41884|10894|30990|0.260099|
|bear/hist_gradient_boosting/58ee8cd6|calibration|16800|4334|12466|0.257976|
|bear/hist_gradient_boosting/58ee8cd6|holdout|17069|4414|12655|0.258597|
|bear/logistic_regression/94fce54c|training|41884|10894|30990|0.260099|
|bear/logistic_regression/94fce54c|calibration|16800|4334|12466|0.257976|
|bear/logistic_regression/94fce54c|holdout|17069|4414|12655|0.258597|
|bull/extra_trees/d90e8c92|training|41884|12589|29295|0.300568|
|bull/extra_trees/d90e8c92|calibration|16800|5028|11772|0.299286|
|bull/extra_trees/d90e8c92|holdout|17069|4998|12071|0.292812|
|bull/hist_gradient_boosting/7be25053|training|41884|12589|29295|0.300568|
|bull/hist_gradient_boosting/7be25053|calibration|16800|5028|11772|0.299286|
|bull/hist_gradient_boosting/7be25053|holdout|17069|4998|12071|0.292812|
|bull/logistic_regression/49a8608f|training|41884|12589|29295|0.300568|
|bull/logistic_regression/49a8608f|calibration|16800|5028|11772|0.299286|
|bull/logistic_regression/49a8608f|holdout|17069|4998|12071|0.292812|

### Holdout Prediction Metrics
|model|label_base_rate_eligible|holdout_base_rate|pred_min|pred_max|pred_mean|pred_median|pred_std|brier|naive_brier|brier_skill|roc_auc|pr_auc|ece_decile|pred_ge_0_50|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|0.255033|0.258597|0|1|0.258164|0.258619|0.036838|0.191452|0.191727|0.001434|0.548222|0.280422|0.03481|8|
|bear/hist_gradient_boosting/58ee8cd6|0.255033|0.258597|0|0.383333|0.258444|0.25915|0.027339|0.191125|0.191727|0.003139|0.52817|0.271593|0.033053|0|
|bear/logistic_regression/94fce54c|0.255033|0.258597|0|0.454545|0.257934|0.259737|0.023173|0.191048|0.191727|0.003539|0.531285|0.274305|0.047753|0|
|bull/extra_trees/d90e8c92|0.295283|0.292812|0|0.379845|0.296811|0.308595|0.02851|0.206665|0.207133|0.002259|0.544013|0.321878|0.022549|0|
|bull/hist_gradient_boosting/7be25053|0.295283|0.292812|0|1|0.299239|0.281761|0.042228|0.206028|0.207133|0.005337|0.543318|0.323179|0.028187|7|
|bull/logistic_regression/49a8608f|0.295283|0.292812|0|0.317829|0.297782|0.300981|0.026667|0.207165|0.207133|-0.000152|0.51967|0.303227|0.03144|0|

### Holdout Prediction Percentiles
|model|p0|p01|p05|p10|p25|p50|p75|p90|p95|p99|p100|
|---|---|---|---|---|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|0|0.111111|0.212885|0.258619|0.258619|0.258619|0.264057|0.264057|0.266417|0.4|1|
|bear/hist_gradient_boosting/58ee8cd6|0|0.13964|0.245675|0.255215|0.25915|0.25915|0.25915|0.269381|0.269381|0.33121|0.383333|
|bear/logistic_regression/94fce54c|0|0.197183|0.231788|0.259737|0.259737|0.259737|0.259737|0.259737|0.265367|0.283276|0.454545|
|bull/extra_trees/d90e8c92|0|0.186813|0.255064|0.255064|0.283435|0.308595|0.312012|0.313837|0.313837|0.379845|0.379845|
|bull/hist_gradient_boosting/7be25053|0|0.12|0.281761|0.281761|0.281761|0.281761|0.315654|0.34902|0.364146|0.473684|1|
|bull/logistic_regression/49a8608f|0|0.172414|0.300981|0.300981|0.300981|0.300981|0.300981|0.300981|0.300981|0.317829|0.317829|

### Calibration by Probability Decile: bear/extra_trees/1f47da02
|decile|rows|pred_mean|actual_rate|abs_error|pred_min|pred_max|
|---|---|---|---|---|---|---|
|1|1707|0.194314|0.202695|0.008381|0|0.258619|
|2|1707|0.258619|0.229057|0.029562|0.258619|0.258619|
|3|1707|0.258619|0.310486|0.051867|0.258619|0.258619|
|4|1707|0.258619|0.151142|0.107476|0.258619|0.258619|
|5|1707|0.258619|0.223784|0.034834|0.258619|0.258619|
|6|1706|0.259948|0.266706|0.006758|0.258619|0.264057|
|7|1707|0.264057|0.318102|0.054045|0.264057|0.264057|
|8|1707|0.264057|0.265964|0.001907|0.264057|0.264057|
|9|1707|0.264057|0.311658|0.047601|0.264057|0.264057|
|10|1707|0.300737|0.306385|0.005648|0.264057|1|

### Calibration by Probability Decile: bear/hist_gradient_boosting/58ee8cd6
|decile|rows|pred_mean|actual_rate|abs_error|pred_min|pred_max|
|---|---|---|---|---|---|---|
|1|1707|0.214579|0.205038|0.009541|0|0.255215|
|2|1707|0.255525|0.216169|0.039356|0.255215|0.258185|
|3|1707|0.258739|0.284124|0.025385|0.258185|0.25915|
|4|1707|0.25915|0.255419|0.003732|0.25915|0.25915|
|5|1707|0.25915|0.338606|0.079455|0.25915|0.25915|
|6|1706|0.25915|0.173505|0.085645|0.25915|0.25915|
|7|1707|0.25915|0.268307|0.009156|0.25915|0.25915|
|8|1707|0.260996|0.291154|0.030158|0.25915|0.269381|
|9|1707|0.269381|0.243117|0.026265|0.269381|0.269381|
|10|1707|0.288621|0.310486|0.021865|0.269381|0.383333|

### Calibration by Probability Decile: bear/logistic_regression/94fce54c
|decile|rows|pred_mean|actual_rate|abs_error|pred_min|pred_max|
|---|---|---|---|---|---|---|
|1|1707|0.223803|0.17809|0.045712|0|0.259737|
|2|1707|0.259737|0.287053|0.027316|0.259737|0.259737|
|3|1707|0.259737|0.210896|0.048841|0.259737|0.259737|
|4|1707|0.259737|0.318102|0.058365|0.259737|0.259737|
|5|1707|0.259737|0.318102|0.058365|0.259737|0.259737|
|6|1706|0.259737|0.119578|0.140159|0.259737|0.259737|
|7|1707|0.259737|0.269479|0.009741|0.259737|0.259737|
|8|1707|0.259737|0.258934|0.000804|0.259737|0.259737|
|9|1707|0.259737|0.315173|0.055435|0.259737|0.259737|
|10|1707|0.277642|0.310486|0.032844|0.259737|0.454545|

### Calibration by Probability Decile: bull/extra_trees/d90e8c92
|decile|rows|pred_mean|actual_rate|abs_error|pred_min|pred_max|
|---|---|---|---|---|---|---|
|1|1707|0.240015|0.254247|0.014232|0|0.255064|
|2|1707|0.275785|0.267135|0.00865|0.255064|0.277388|
|3|1707|0.280449|0.25952|0.020929|0.277388|0.283435|
|4|1707|0.290892|0.264206|0.026686|0.283435|0.308595|
|5|1707|0.308595|0.297598|0.010997|0.308595|0.308595|
|6|1706|0.308651|0.268464|0.040187|0.308595|0.312012|
|7|1707|0.312012|0.295255|0.016757|0.312012|0.312012|
|8|1707|0.312012|0.303456|0.008556|0.312012|0.312012|
|9|1707|0.313729|0.366725|0.052996|0.312012|0.313837|
|10|1707|0.325981|0.351494|0.025513|0.313837|0.379845|

### Calibration by Probability Decile: bull/hist_gradient_boosting/7be25053
|decile|rows|pred_mean|actual_rate|abs_error|pred_min|pred_max|
|---|---|---|---|---|---|---|
|1|1707|0.258021|0.299356|0.041334|0|0.281761|
|2|1707|0.281761|0.274165|0.007596|0.281761|0.281761|
|3|1707|0.281761|0.237844|0.043917|0.281761|0.281761|
|4|1707|0.281761|0.22437|0.057391|0.281761|0.281761|
|5|1707|0.281761|0.241945|0.039816|0.281761|0.281761|
|6|1706|0.282885|0.340563|0.057678|0.281761|0.283455|
|7|1707|0.30068|0.298184|0.002496|0.283455|0.304894|
|8|1707|0.319443|0.314587|0.004856|0.304894|0.325672|
|9|1707|0.327619|0.337434|0.009815|0.325672|0.34902|
|10|1707|0.376687|0.359695|0.016991|0.34902|1|

### Calibration by Probability Decile: bull/logistic_regression/49a8608f
|decile|rows|pred_mean|actual_rate|abs_error|pred_min|pred_max|
|---|---|---|---|---|---|---|
|1|1707|0.263849|0.258348|0.005502|0|0.300981|
|2|1707|0.300981|0.364382|0.0634|0.300981|0.300981|
|3|1707|0.300981|0.272994|0.027988|0.300981|0.300981|
|4|1707|0.300981|0.301113|0.000132|0.300981|0.300981|
|5|1707|0.300981|0.222027|0.078955|0.300981|0.300981|
|6|1706|0.300981|0.297186|0.003795|0.300981|0.300981|
|7|1707|0.300981|0.299941|0.00104|0.300981|0.300981|
|8|1707|0.300981|0.285296|0.015686|0.300981|0.300981|
|9|1707|0.300981|0.251904|0.049078|0.300981|0.300981|
|10|1707|0.306117|0.374927|0.06881|0.300981|0.317829|

### Results by Symbol: bear/extra_trees/1f47da02
|symbol|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|AMZN|494|107|0.216599|0.25937|0.258619|0|0.171583|0.58218|0.25475|
|DIA|493|119|0.241379|0.269893|0.264057|0|0.185995|0.542163|0.252112|
|IWM|493|128|0.259635|0.2616|0.258619|0|0.190937|0.621244|0.321039|
|NVDA|493|130|0.263692|0.262167|0.258619|0|0.192535|0.60676|0.336781|
|TNA|493|130|0.263692|0.253108|0.258619|0|0.191099|0.640814|0.363033|
|TZA|493|119|0.241379|0.253458|0.258619|0|0.183086|0.54569|0.26374|
|QQQ|492|132|0.268293|0.269542|0.264057|0|0.195335|0.595023|0.313664|
|RWM|492|130|0.264228|0.261981|0.258619|0|0.194245|0.530822|0.283898|
|XLE|492|132|0.268293|0.261457|0.258619|0|0.197504|0.453146|0.254122|
|GOOGL|491|125|0.254582|0.261624|0.258619|0|0.190626|0.482055|0.250122|
|QID|491|122|0.248473|0.258674|0.258619|1|0.185707|0.544882|0.278039|
|TQQQ|491|137|0.279022|0.254616|0.258619|0|0.199427|0.579983|0.348897|
|XLV|491|145|0.295316|0.263714|0.258619|1|0.210599|0.513773|0.297538|
|MSFT|490|134|0.273469|0.26281|0.261338|0|0.199296|0.541747|0.290008|
|XLI|490|120|0.244898|0.26161|0.258619|0|0.185728|0.495574|0.242909|
|XLP|490|109|0.222449|0.262196|0.258619|0|0.174903|0.536757|0.235103|
|XLRE|490|123|0.25102|0.259843|0.258619|0|0.187229|0.516138|0.274785|
|SOXL|489|129|0.263804|0.239177|0.258619|0|0.193378|0.515848|0.274136|
|SQQQ|488|113|0.231557|0.245418|0.258619|0|0.17744|0.563575|0.259433|
|XLY|488|141|0.288934|0.259867|0.258619|0|0.208413|0.555665|0.323837|
|AMD|487|125|0.256674|0.258279|0.258619|0|0.187586|0.634066|0.353286|
|SOXS|487|124|0.25462|0.194505|0.258619|0|0.188748|0.613825|0.322059|
|TSLA|487|121|0.24846|0.257983|0.258619|0|0.187571|0.481134|0.251173|
|SDS|486|115|0.236626|0.272525|0.258619|5|0.18124|0.566846|0.287528|
|SPXU|486|110|0.226337|0.254454|0.258619|0|0.175203|0.562802|0.256087|
|SPY|486|145|0.298354|0.272279|0.264057|1|0.213839|0.507028|0.297142|
|UPRO|486|150|0.308642|0.260528|0.258619|0|0.216221|0.546042|0.329382|
|SH|485|126|0.259794|0.264527|0.264057|0|0.192263|0.552571|0.282918|
|META|483|121|0.250518|0.257392|0.258619|0|0.186631|0.511678|0.255863|
|XLF|483|124|0.256729|0.259686|0.258619|0|0.190345|0.568728|0.30286|
|XLK|483|135|0.279503|0.259124|0.258619|0|0.200826|0.537995|0.311477|
|XLB|482|144|0.298755|0.258157|0.258619|0|0.210637|0.529493|0.311924|
|XLC|481|126|0.261954|0.260174|0.258619|0|0.192394|0.578203|0.306425|
|AAPL|475|123|0.258947|0.263|0.258619|0|0.192125|0.48807|0.266559|
|XLU|468|100|0.213675|0.261008|0.258619|0|0.16984|0.54144|0.251769|

### Results by Sector: bear/extra_trees/1f47da02
|sector|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|consumer_discretionary|1469|369|0.251191|0.259075|0.258619|0|0.189118|0.539893|0.272954|
|inverse_market|1457|351|0.240906|0.263835|0.258619|5|0.182896|0.56205|0.275413|
|communication_services|1455|372|0.25567|0.25974|0.258619|0|0.189884|0.523626|0.267198|
|technology|1448|392|0.270718|0.261643|0.258619|0|0.197454|0.525102|0.281739|
|inverse_small_caps|985|249|0.252792|0.257715|0.258619|0|0.18866|0.540624|0.27356|
|semiconductors|980|255|0.260204|0.260235|0.258619|0|0.190076|0.620798|0.340979|
|inverse_technology_growth|979|235|0.240041|0.252066|0.258619|1|0.181586|0.554945|0.268838|
|industrials_large_cap|493|119|0.241379|0.269893|0.264057|0|0.185995|0.542163|0.252112|
|leveraged_small_caps|493|130|0.263692|0.253108|0.258619|0|0.191099|0.640814|0.363033|
|small_caps|493|128|0.259635|0.2616|0.258619|0|0.190937|0.621244|0.321039|
|energy|492|132|0.268293|0.261457|0.258619|0|0.197504|0.453146|0.254122|
|technology_growth|492|132|0.268293|0.269542|0.264057|0|0.195335|0.595023|0.313664|
|health_care|491|145|0.295316|0.263714|0.258619|1|0.210599|0.513773|0.297538|
|leveraged_technology_growth|491|137|0.279022|0.254616|0.258619|0|0.199427|0.579983|0.348897|
|consumer_staples|490|109|0.222449|0.262196|0.258619|0|0.174903|0.536757|0.235103|
|industrials|490|120|0.244898|0.26161|0.258619|0|0.185728|0.495574|0.242909|
|real_estate|490|123|0.25102|0.259843|0.258619|0|0.187229|0.516138|0.274785|
|leveraged_semiconductors|489|129|0.263804|0.239177|0.258619|0|0.193378|0.515848|0.274136|
|inverse_semiconductors|487|124|0.25462|0.194505|0.258619|0|0.188748|0.613825|0.322059|
|broad_market|486|145|0.298354|0.272279|0.264057|1|0.213839|0.507028|0.297142|
|leveraged_market|486|150|0.308642|0.260528|0.258619|0|0.216221|0.546042|0.329382|
|financials|483|124|0.256729|0.259686|0.258619|0|0.190345|0.568728|0.30286|
|materials|482|144|0.298755|0.258157|0.258619|0|0.210637|0.529493|0.311924|
|utilities|468|100|0.213675|0.261008|0.258619|0|0.16984|0.54144|0.251769|

### Results by Regime: bear/extra_trees/1f47da02
|market_regime_label|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|uptrend_low_vol|7706|2206|0.28627|0.260535|0.258619|0|0.205119|0.539254|0.30509|
|uptrend_high_vol|6083|1408|0.231465|0.260225|0.258619|8|0.17754|0.56585|0.261843|
|downtrend_high_vol|3070|707|0.230293|0.247768|0.258619|0|0.178413|0.537204|0.245705|
|mixed|210|93|0.442857|0.263446|0.258619|0|0.283551|0.395|0.396959|

### Results by Year: bear/extra_trees/1f47da02
|year|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|2025|8659|2060|0.237903|0.254616|0.258619|0|0.180621|0.568895|0.271141|
|2024|5783|1576|0.272523|0.262322|0.258619|8|0.197315|0.555568|0.300535|
|2026|2627|778|0.296155|0.260709|0.258619|0|0.214247|0.45908|0.275218|

### Results by Symbol: bear/hist_gradient_boosting/58ee8cd6
|symbol|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|AMZN|494|107|0.216599|0.260593|0.25915|0|0.171812|0.519428|0.224018|
|DIA|493|119|0.241379|0.282783|0.269381|0|0.188064|0.455961|0.224689|
|IWM|493|128|0.259635|0.260531|0.25915|0|0.191828|0.576338|0.295468|
|NVDA|493|130|0.263692|0.260669|0.25915|0|0.19422|0.526976|0.275253|
|TNA|493|130|0.263692|0.254524|0.25915|0|0.192886|0.626478|0.33379|
|TZA|493|119|0.241379|0.251817|0.258185|0|0.181648|0.568463|0.272831|
|QQQ|492|132|0.268293|0.267083|0.269381|0|0.194712|0.580955|0.310701|
|RWM|492|130|0.264228|0.260776|0.25915|0|0.194424|0.499841|0.265912|
|XLE|492|132|0.268293|0.258707|0.25915|0|0.196205|0.45685|0.258221|
|GOOGL|491|125|0.254582|0.262222|0.25915|0|0.190125|0.460339|0.239777|
|QID|491|122|0.248473|0.25723|0.25915|0|0.187274|0.494713|0.25306|
|TQQQ|491|137|0.279022|0.253868|0.25915|0|0.198259|0.581622|0.355189|
|XLV|491|145|0.295316|0.263314|0.25915|0|0.210553|0.437502|0.270688|
|MSFT|490|134|0.273469|0.263737|0.25915|0|0.198633|0.549388|0.296288|
|XLI|490|120|0.244898|0.260726|0.25915|0|0.1853|0.50152|0.247625|
|XLP|490|109|0.222449|0.261457|0.25915|0|0.174323|0.482518|0.220324|
|XLRE|490|123|0.25102|0.259671|0.25915|0|0.187834|0.515363|0.276994|
|SOXL|489|129|0.263804|0.233747|0.258185|0|0.19124|0.535777|0.280985|
|SQQQ|488|113|0.231557|0.25045|0.258185|0|0.176811|0.55187|0.274567|
|XLY|488|141|0.288934|0.261038|0.25915|0|0.205944|0.517669|0.300152|
|AMD|487|125|0.256674|0.258979|0.25915|0|0.188565|0.631845|0.33682|
|SOXS|487|124|0.25462|0.203906|0.255215|0|0.185251|0.632598|0.351303|
|TSLA|487|121|0.24846|0.259882|0.25915|0|0.18992|0.434539|0.223541|
|SDS|486|115|0.236626|0.259315|0.25915|0|0.180378|0.563483|0.287767|
|SPXU|486|110|0.226337|0.2563|0.25915|0|0.175155|0.553651|0.255592|
|SPY|486|145|0.298354|0.274463|0.269381|0|0.206202|0.583568|0.36043|
|UPRO|486|150|0.308642|0.262742|0.25915|0|0.212483|0.53997|0.343788|
|SH|485|126|0.259794|0.262429|0.25915|0|0.19215|0.501404|0.26333|
|META|483|121|0.250518|0.263357|0.25915|0|0.188926|0.478928|0.244506|
|XLF|483|124|0.256729|0.26114|0.25915|0|0.191744|0.474335|0.247299|
|XLK|483|135|0.279503|0.262569|0.25915|0|0.200773|0.559398|0.313222|
|XLB|482|144|0.298755|0.256817|0.25915|0|0.210474|0.504037|0.298496|
|XLC|481|126|0.261954|0.257911|0.25915|0|0.192377|0.553521|0.284671|
|AAPL|475|123|0.258947|0.261018|0.25915|0|0.191842|0.513766|0.262848|
|XLU|468|100|0.213675|0.259671|0.25915|0|0.170746|0.456861|0.203489|

### Results by Sector: bear/hist_gradient_boosting/58ee8cd6
|sector|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|consumer_discretionary|1469|369|0.251191|0.260505|0.25915|0|0.189154|0.486107|0.245338|
|inverse_market|1457|351|0.240906|0.259346|0.25915|0|0.182555|0.543682|0.267204|
|communication_services|1455|372|0.25567|0.261174|0.25915|0|0.190471|0.496319|0.252823|
|technology|1448|392|0.270718|0.262455|0.25915|0|0.197119|0.539854|0.287162|
|inverse_small_caps|985|249|0.252792|0.256292|0.25915|0|0.188029|0.536636|0.26876|
|semiconductors|980|255|0.260204|0.259829|0.25915|0|0.19141|0.580527|0.302012|
|inverse_technology_growth|979|235|0.240041|0.253851|0.25915|0|0.182059|0.527239|0.264073|
|industrials_large_cap|493|119|0.241379|0.282783|0.269381|0|0.188064|0.455961|0.224689|
|leveraged_small_caps|493|130|0.263692|0.254524|0.25915|0|0.192886|0.626478|0.33379|
|small_caps|493|128|0.259635|0.260531|0.25915|0|0.191828|0.576338|0.295468|
|energy|492|132|0.268293|0.258707|0.25915|0|0.196205|0.45685|0.258221|
|technology_growth|492|132|0.268293|0.267083|0.269381|0|0.194712|0.580955|0.310701|
|health_care|491|145|0.295316|0.263314|0.25915|0|0.210553|0.437502|0.270688|
|leveraged_technology_growth|491|137|0.279022|0.253868|0.25915|0|0.198259|0.581622|0.355189|
|consumer_staples|490|109|0.222449|0.261457|0.25915|0|0.174323|0.482518|0.220324|
|industrials|490|120|0.244898|0.260726|0.25915|0|0.1853|0.50152|0.247625|
|real_estate|490|123|0.25102|0.259671|0.25915|0|0.187834|0.515363|0.276994|
|leveraged_semiconductors|489|129|0.263804|0.233747|0.258185|0|0.19124|0.535777|0.280985|
|inverse_semiconductors|487|124|0.25462|0.203906|0.255215|0|0.185251|0.632598|0.351303|
|broad_market|486|145|0.298354|0.274463|0.269381|0|0.206202|0.583568|0.36043|
|leveraged_market|486|150|0.308642|0.262742|0.25915|0|0.212483|0.53997|0.343788|
|financials|483|124|0.256729|0.26114|0.25915|0|0.191744|0.474335|0.247299|
|materials|482|144|0.298755|0.256817|0.25915|0|0.210474|0.504037|0.298496|
|utilities|468|100|0.213675|0.259671|0.25915|0|0.170746|0.456861|0.203489|

### Results by Regime: bear/hist_gradient_boosting/58ee8cd6
|market_regime_label|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|uptrend_low_vol|7706|2206|0.28627|0.260465|0.25915|0|0.204843|0.518558|0.296026|
|uptrend_high_vol|6083|1408|0.231465|0.259775|0.25915|0|0.177762|0.533446|0.248685|
|downtrend_high_vol|3070|707|0.230293|0.25056|0.25915|0|0.177033|0.544924|0.246868|
|mixed|210|93|0.442857|0.261048|0.25915|0|0.280837|0.458506|0.430613|

### Results by Year: bear/hist_gradient_boosting/58ee8cd6
|year|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|2025|8659|2060|0.237903|0.256736|0.25915|0|0.180853|0.538039|0.254412|
|2024|5783|1576|0.272523|0.260518|0.25915|0|0.197638|0.514693|0.28257|
|2026|2627|778|0.296155|0.259509|0.25915|0|0.210649|0.517879|0.30369|

### Results by Symbol: bear/logistic_regression/94fce54c
|symbol|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|AMZN|494|107|0.216599|0.259625|0.259737|0|0.171317|0.528798|0.227274|
|DIA|493|119|0.241379|0.259616|0.259737|0|0.183393|0.507909|0.245367|
|IWM|493|128|0.259635|0.259653|0.259737|0|0.19207|0.525107|0.275597|
|NVDA|493|130|0.263692|0.26176|0.259737|0|0.194038|0.550201|0.285148|
|TNA|493|130|0.263692|0.256843|0.259737|0|0.193013|0.603232|0.322455|
|TZA|493|119|0.241379|0.25899|0.259737|0|0.181006|0.606783|0.306997|
|QQQ|492|132|0.268293|0.260106|0.259737|0|0.196445|0.494886|0.266493|
|RWM|492|130|0.264228|0.260809|0.259737|0|0.19417|0.559403|0.297751|
|XLE|492|132|0.268293|0.25986|0.259737|0|0.196339|0.503304|0.270513|
|GOOGL|491|125|0.254582|0.260917|0.259737|0|0.18964|0.465301|0.253721|
|QID|491|122|0.248473|0.260147|0.259737|0|0.186544|0.536374|0.265244|
|TQQQ|491|137|0.279022|0.251532|0.259737|0|0.199721|0.588591|0.326855|
|XLV|491|145|0.295316|0.26006|0.259737|0|0.209403|0.493113|0.293223|
|MSFT|490|134|0.273469|0.259916|0.259737|0|0.198907|0.496562|0.279708|
|XLI|490|120|0.244898|0.259462|0.259737|0|0.185156|0.508874|0.249284|
|XLP|490|109|0.222449|0.259738|0.259737|0|0.174314|0.502516|0.223501|
|XLRE|490|123|0.25102|0.259754|0.259737|0|0.188142|0.48796|0.247892|
|SOXL|489|129|0.263804|0.242738|0.259737|0|0.190066|0.577799|0.311284|
|SQQQ|488|113|0.231557|0.256193|0.259737|0|0.175734|0.547894|0.274468|
|XLY|488|141|0.288934|0.259662|0.259737|0|0.206196|0.508605|0.297902|
|AMD|487|125|0.256674|0.25931|0.259737|0|0.188204|0.593569|0.320855|
|SOXS|487|124|0.25462|0.225145|0.234742|0|0.184464|0.631021|0.372177|
|TSLA|487|121|0.24846|0.262534|0.259737|0|0.18817|0.459863|0.248716|
|SDS|486|115|0.236626|0.260885|0.259737|0|0.181271|0.556487|0.264022|
|SPXU|486|110|0.226337|0.260957|0.259737|0|0.174722|0.59734|0.280436|
|SPY|486|145|0.298354|0.260997|0.259737|0|0.210733|0.497988|0.302806|
|UPRO|486|150|0.308642|0.254977|0.259737|0|0.215512|0.559692|0.339226|
|SH|485|126|0.259794|0.260529|0.259737|0|0.192323|0.500232|0.259959|
|META|483|121|0.250518|0.258149|0.259737|0|0.18701|0.521312|0.278584|
|XLF|483|124|0.256729|0.259591|0.259737|0|0.190687|0.521475|0.266725|
|XLK|483|135|0.279503|0.258939|0.259737|0|0.201589|0.520754|0.291787|
|XLB|482|144|0.298755|0.259546|0.259737|0|0.210911|0.51205|0.306376|
|XLC|481|126|0.261954|0.259409|0.259737|0|0.193247|0.503778|0.263563|
|AAPL|475|123|0.258947|0.259858|0.259737|0|0.191818|0.50753|0.264011|
|XLU|468|100|0.213675|0.259508|0.259737|0|0.170175|0.492921|0.215633|

### Results by Sector: bear/logistic_regression/94fce54c
|sector|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|consumer_discretionary|1469|369|0.251191|0.260602|0.259737|0|0.188491|0.496248|0.253952|
|inverse_market|1457|351|0.240906|0.26079|0.259737|0|0.182766|0.551911|0.265342|
|communication_services|1455|372|0.25567|0.2595|0.259737|0|0.189959|0.496666|0.262431|
|technology|1448|392|0.270718|0.259571|0.259737|0|0.197476|0.507873|0.275114|
|inverse_small_caps|985|249|0.252792|0.259899|0.259737|0|0.187582|0.58506|0.302305|
|semiconductors|980|255|0.260204|0.260542|0.259737|0|0.191139|0.571897|0.296445|
|inverse_technology_growth|979|235|0.240041|0.258176|0.259737|0|0.181156|0.541987|0.26639|
|industrials_large_cap|493|119|0.241379|0.259616|0.259737|0|0.183393|0.507909|0.245367|
|leveraged_small_caps|493|130|0.263692|0.256843|0.259737|0|0.193013|0.603232|0.322455|
|small_caps|493|128|0.259635|0.259653|0.259737|0|0.19207|0.525107|0.275597|
|energy|492|132|0.268293|0.25986|0.259737|0|0.196339|0.503304|0.270513|
|technology_growth|492|132|0.268293|0.260106|0.259737|0|0.196445|0.494886|0.266493|
|health_care|491|145|0.295316|0.26006|0.259737|0|0.209403|0.493113|0.293223|
|leveraged_technology_growth|491|137|0.279022|0.251532|0.259737|0|0.199721|0.588591|0.326855|
|consumer_staples|490|109|0.222449|0.259738|0.259737|0|0.174314|0.502516|0.223501|
|industrials|490|120|0.244898|0.259462|0.259737|0|0.185156|0.508874|0.249284|
|real_estate|490|123|0.25102|0.259754|0.259737|0|0.188142|0.48796|0.247892|
|leveraged_semiconductors|489|129|0.263804|0.242738|0.259737|0|0.190066|0.577799|0.311284|
|inverse_semiconductors|487|124|0.25462|0.225145|0.234742|0|0.184464|0.631021|0.372177|
|broad_market|486|145|0.298354|0.260997|0.259737|0|0.210733|0.497988|0.302806|
|leveraged_market|486|150|0.308642|0.254977|0.259737|0|0.215512|0.559692|0.339226|
|financials|483|124|0.256729|0.259591|0.259737|0|0.190687|0.521475|0.266725|
|materials|482|144|0.298755|0.259546|0.259737|0|0.210911|0.51205|0.306376|
|utilities|468|100|0.213675|0.259508|0.259737|0|0.170175|0.492921|0.215633|

### Results by Regime: bear/logistic_regression/94fce54c
|market_regime_label|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|uptrend_low_vol|7706|2206|0.28627|0.258382|0.259737|0|0.204543|0.543189|0.308998|
|uptrend_high_vol|6083|1408|0.231465|0.258777|0.259737|0|0.177887|0.522205|0.250987|
|downtrend_high_vol|3070|707|0.230293|0.254876|0.259737|0|0.177034|0.524465|0.240062|
|mixed|210|93|0.442857|0.261809|0.259737|0|0.281977|0.375701|0.425328|

### Results by Year: bear/logistic_regression/94fce54c
|year|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|2025|8659|2060|0.237903|0.256371|0.259737|0|0.180686|0.536298|0.257689|
|2024|5783|1576|0.272523|0.2593|0.259737|0|0.197949|0.539076|0.29262|
|2026|2627|778|0.296155|0.260081|0.259737|0|0.210016|0.492253|0.296803|

### Results by Symbol: bull/extra_trees/d90e8c92
|symbol|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|AMZN|494|141|0.285425|0.298215|0.308595|0|0.204269|0.519589|0.324887|
|DIA|493|153|0.310345|0.29286|0.308595|0|0.211337|0.603479|0.369508|
|IWM|493|136|0.275862|0.300063|0.308595|0|0.198899|0.569729|0.331446|
|NVDA|493|161|0.326572|0.297681|0.308595|0|0.21814|0.594019|0.409138|
|TNA|493|145|0.294118|0.302357|0.308595|0|0.207953|0.55983|0.34656|
|TZA|493|121|0.245436|0.296674|0.308595|0|0.185451|0.60856|0.304214|
|QQQ|492|141|0.286585|0.290221|0.289474|0|0.206779|0.493716|0.286976|
|RWM|492|127|0.25813|0.29961|0.308595|0|0.191702|0.581253|0.316234|
|XLE|492|177|0.359756|0.304424|0.312012|0|0.231812|0.593328|0.427767|
|GOOGL|491|162|0.329939|0.302684|0.308595|0|0.219965|0.572066|0.388936|
|QID|491|131|0.266802|0.290072|0.289474|0|0.193168|0.618978|0.382962|
|TQQQ|491|147|0.299389|0.297469|0.308595|0|0.212108|0.526044|0.326973|
|XLV|491|129|0.262729|0.304242|0.308595|0|0.19745|0.494786|0.268173|
|MSFT|490|150|0.306122|0.298718|0.308595|0|0.213097|0.523118|0.353944|
|XLI|490|139|0.283673|0.30085|0.308595|0|0.204579|0.528049|0.322678|
|XLP|490|151|0.308163|0.310832|0.312012|0|0.215263|0.466389|0.290866|
|XLRE|490|131|0.267347|0.303758|0.312012|0|0.197026|0.547683|0.293278|
|SOXL|489|166|0.339468|0.286363|0.289474|0|0.228153|0.514771|0.370204|
|SQQQ|488|126|0.258197|0.290235|0.308595|0|0.188724|0.597047|0.313545|
|XLY|488|144|0.295082|0.300831|0.308595|0|0.209476|0.539385|0.324297|
|AMD|487|160|0.328542|0.302178|0.308595|0|0.22045|0.548394|0.361688|
|SOXS|487|124|0.25462|0.251735|0.255064|0|0.18696|0.540234|0.277667|
|TSLA|487|146|0.299795|0.302449|0.308595|0|0.209499|0.542522|0.317851|
|SDS|486|144|0.296296|0.285344|0.283435|0|0.207861|0.534824|0.319347|
|SPXU|486|143|0.294239|0.289926|0.289474|0|0.203632|0.597005|0.365528|
|SPY|486|124|0.255144|0.289991|0.289474|0|0.192531|0.542706|0.286681|
|UPRO|486|125|0.257202|0.294869|0.308595|0|0.192722|0.555657|0.307266|
|SH|485|145|0.298969|0.290781|0.289474|0|0.208688|0.535355|0.31717|
|META|483|145|0.300207|0.296892|0.308595|0|0.212477|0.460355|0.2855|
|XLF|483|155|0.320911|0.306917|0.312012|0|0.217237|0.550148|0.366887|
|XLK|483|146|0.302277|0.297405|0.308595|0|0.213105|0.499045|0.300108|
|XLB|482|134|0.278008|0.302884|0.312012|0|0.199919|0.575956|0.326768|
|XLC|481|150|0.31185|0.302024|0.312012|0|0.215714|0.543494|0.345509|
|AAPL|475|149|0.313684|0.300206|0.308595|0|0.214455|0.518528|0.326338|
|XLU|468|130|0.277778|0.306948|0.312012|0|0.202929|0.45561|0.262055|

### Results by Sector: bull/extra_trees/d90e8c92
|sector|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|consumer_discretionary|1469|431|0.293397|0.300488|0.308595|0|0.207733|0.535349|0.317419|
|inverse_market|1457|432|0.2965|0.288682|0.289474|0|0.206725|0.555705|0.331171|
|communication_services|1455|457|0.314089|0.300543|0.308595|0|0.216074|0.527622|0.337864|
|technology|1448|445|0.30732|0.298768|0.308595|0|0.213545|0.515712|0.31962|
|inverse_small_caps|985|248|0.251777|0.298141|0.308595|0|0.188573|0.594627|0.310024|
|semiconductors|980|321|0.327551|0.299916|0.308595|0|0.219288|0.573875|0.385076|
|inverse_technology_growth|979|257|0.262513|0.290153|0.289474|0|0.190953|0.608031|0.34173|
|industrials_large_cap|493|153|0.310345|0.29286|0.308595|0|0.211337|0.603479|0.369508|
|leveraged_small_caps|493|145|0.294118|0.302357|0.308595|0|0.207953|0.55983|0.34656|
|small_caps|493|136|0.275862|0.300063|0.308595|0|0.198899|0.569729|0.331446|
|energy|492|177|0.359756|0.304424|0.312012|0|0.231812|0.593328|0.427767|
|technology_growth|492|141|0.286585|0.290221|0.289474|0|0.206779|0.493716|0.286976|
|health_care|491|129|0.262729|0.304242|0.308595|0|0.19745|0.494786|0.268173|
|leveraged_technology_growth|491|147|0.299389|0.297469|0.308595|0|0.212108|0.526044|0.326973|
|consumer_staples|490|151|0.308163|0.310832|0.312012|0|0.215263|0.466389|0.290866|
|industrials|490|139|0.283673|0.30085|0.308595|0|0.204579|0.528049|0.322678|
|real_estate|490|131|0.267347|0.303758|0.312012|0|0.197026|0.547683|0.293278|
|leveraged_semiconductors|489|166|0.339468|0.286363|0.289474|0|0.228153|0.514771|0.370204|
|inverse_semiconductors|487|124|0.25462|0.251735|0.255064|0|0.18696|0.540234|0.277667|
|broad_market|486|124|0.255144|0.289991|0.289474|0|0.192531|0.542706|0.286681|
|leveraged_market|486|125|0.257202|0.294869|0.308595|0|0.192722|0.555657|0.307266|
|financials|483|155|0.320911|0.306917|0.312012|0|0.217237|0.550148|0.366887|
|materials|482|134|0.278008|0.302884|0.312012|0|0.199919|0.575956|0.326768|
|utilities|468|130|0.277778|0.306948|0.312012|0|0.202929|0.45561|0.262055|

### Results by Regime: bull/extra_trees/d90e8c92
|market_regime_label|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|uptrend_low_vol|7706|2322|0.301324|0.301636|0.308595|0|0.209941|0.550394|0.333768|
|uptrend_high_vol|6083|1794|0.29492|0.294427|0.308595|0|0.206043|0.574489|0.347741|
|downtrend_high_vol|3070|844|0.274919|0.288749|0.308595|0|0.202129|0.489202|0.274224|
|mixed|210|38|0.180952|0.306727|0.312012|0|0.170802|0.183675|0.120885|

### Results by Year: bull/extra_trees/d90e8c92
|year|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|2025|8659|2363|0.272895|0.296651|0.308595|0|0.197567|0.585289|0.334421|
|2024|5783|1825|0.31558|0.296736|0.308595|0|0.215354|0.548302|0.345226|
|2026|2627|810|0.308337|0.297506|0.308595|0|0.217527|0.423086|0.271126|

### Results by Symbol: bull/hist_gradient_boosting/7be25053
|symbol|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|AMZN|494|141|0.285425|0.293623|0.281761|0|0.202021|0.523095|0.341389|
|DIA|493|153|0.310345|0.286554|0.281761|0|0.213695|0.565907|0.342081|
|IWM|493|136|0.275862|0.29433|0.281761|0|0.19788|0.575857|0.338183|
|NVDA|493|161|0.326572|0.300555|0.281761|0|0.216245|0.598284|0.411|
|TNA|493|145|0.294118|0.305658|0.304894|0|0.208205|0.535781|0.331505|
|TZA|493|121|0.245436|0.342924|0.325672|5|0.197179|0.546299|0.277022|
|QQQ|492|141|0.286585|0.286801|0.281761|0|0.20335|0.536633|0.329484|
|RWM|492|127|0.25813|0.363374|0.34902|2|0.196256|0.615468|0.335242|
|XLE|492|177|0.359756|0.300606|0.283455|0|0.229673|0.631396|0.450485|
|GOOGL|491|162|0.329939|0.304386|0.283455|0|0.220745|0.545414|0.361394|
|QID|491|131|0.266802|0.305303|0.304894|0|0.194372|0.542218|0.338978|
|TQQQ|491|147|0.299389|0.297298|0.281787|0|0.21176|0.515089|0.345302|
|XLV|491|129|0.262729|0.30053|0.283455|0|0.194945|0.525279|0.285761|
|MSFT|490|150|0.306122|0.28733|0.281761|0|0.214431|0.4625|0.294357|
|XLI|490|139|0.283673|0.302168|0.283455|0|0.204339|0.541044|0.318118|
|XLP|490|151|0.308163|0.309996|0.315654|0|0.21375|0.495761|0.316191|
|XLRE|490|131|0.267347|0.305162|0.304894|0|0.195826|0.557018|0.331143|
|SOXL|489|166|0.339468|0.281657|0.281761|0|0.225062|0.536853|0.359411|
|SQQQ|488|126|0.258197|0.287064|0.281761|0|0.184851|0.60221|0.365699|
|XLY|488|144|0.295082|0.299467|0.281761|0|0.206598|0.544271|0.338472|
|AMD|487|160|0.328542|0.298515|0.281761|0|0.219795|0.579941|0.371582|
|SOXS|487|124|0.25462|0.253021|0.281761|0|0.184548|0.560384|0.285293|
|TSLA|487|146|0.299795|0.291515|0.281761|0|0.208873|0.578576|0.333309|
|SDS|486|144|0.296296|0.294161|0.281761|0|0.206914|0.500599|0.330723|
|SPXU|486|143|0.294239|0.289246|0.281787|0|0.203748|0.579298|0.355219|
|SPY|486|124|0.255144|0.287297|0.281761|0|0.189922|0.530142|0.284503|
|UPRO|486|125|0.257202|0.293364|0.281761|0|0.19117|0.56472|0.340001|
|SH|485|145|0.298969|0.301464|0.283455|0|0.206431|0.58857|0.370157|
|META|483|145|0.300207|0.2877|0.281761|0|0.211999|0.484575|0.291647|
|XLF|483|155|0.320911|0.313606|0.315654|0|0.216706|0.550865|0.36534|
|XLK|483|146|0.302277|0.304716|0.281761|0|0.21152|0.509725|0.31622|
|XLB|482|134|0.278008|0.302479|0.283455|0|0.19916|0.578723|0.325292|
|XLC|481|150|0.31185|0.30144|0.283455|0|0.213555|0.593867|0.388918|
|AAPL|475|149|0.313684|0.295686|0.281761|0|0.214675|0.56137|0.337153|
|XLU|468|130|0.277778|0.303602|0.283455|0|0.200771|0.498339|0.315182|

### Results by Sector: bull/hist_gradient_boosting/7be25053
|sector|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|consumer_discretionary|1469|431|0.293397|0.294865|0.281761|0|0.205813|0.547804|0.332062|
|inverse_market|1457|432|0.2965|0.294953|0.281761|0|0.205697|0.557633|0.352525|
|communication_services|1455|457|0.314089|0.297873|0.281761|0|0.215465|0.541779|0.344365|
|technology|1448|445|0.30732|0.295871|0.281761|0|0.21354|0.510367|0.31211|
|inverse_small_caps|985|248|0.251777|0.353139|0.330479|7|0.196718|0.5807|0.30334|
|semiconductors|980|321|0.327551|0.299541|0.281761|0|0.218009|0.588376|0.388247|
|inverse_technology_growth|979|257|0.262513|0.296211|0.283455|0|0.189626|0.569713|0.345077|
|industrials_large_cap|493|153|0.310345|0.286554|0.281761|0|0.213695|0.565907|0.342081|
|leveraged_small_caps|493|145|0.294118|0.305658|0.304894|0|0.208205|0.535781|0.331505|
|small_caps|493|136|0.275862|0.29433|0.281761|0|0.19788|0.575857|0.338183|
|energy|492|177|0.359756|0.300606|0.283455|0|0.229673|0.631396|0.450485|
|technology_growth|492|141|0.286585|0.286801|0.281761|0|0.20335|0.536633|0.329484|
|health_care|491|129|0.262729|0.30053|0.283455|0|0.194945|0.525279|0.285761|
|leveraged_technology_growth|491|147|0.299389|0.297298|0.281787|0|0.21176|0.515089|0.345302|
|consumer_staples|490|151|0.308163|0.309996|0.315654|0|0.21375|0.495761|0.316191|
|industrials|490|139|0.283673|0.302168|0.283455|0|0.204339|0.541044|0.318118|
|real_estate|490|131|0.267347|0.305162|0.304894|0|0.195826|0.557018|0.331143|
|leveraged_semiconductors|489|166|0.339468|0.281657|0.281761|0|0.225062|0.536853|0.359411|
|inverse_semiconductors|487|124|0.25462|0.253021|0.281761|0|0.184548|0.560384|0.285293|
|broad_market|486|124|0.255144|0.287297|0.281761|0|0.189922|0.530142|0.284503|
|leveraged_market|486|125|0.257202|0.293364|0.281761|0|0.19117|0.56472|0.340001|
|financials|483|155|0.320911|0.313606|0.315654|0|0.216706|0.550865|0.36534|
|materials|482|134|0.278008|0.302479|0.283455|0|0.19916|0.578723|0.325292|
|utilities|468|130|0.277778|0.303602|0.283455|0|0.200771|0.498339|0.315182|

### Results by Regime: bull/hist_gradient_boosting/7be25053
|market_regime_label|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|uptrend_low_vol|7706|2322|0.301324|0.304911|0.283455|7|0.209674|0.545396|0.329717|
|uptrend_high_vol|6083|1794|0.29492|0.295784|0.281761|0|0.205453|0.565557|0.346958|
|downtrend_high_vol|3070|844|0.274919|0.291709|0.281761|0|0.200703|0.495921|0.277306|
|mixed|210|38|0.180952|0.301284|0.283455|0|0.166734|0.380431|0.16063|

### Results by Year: bull/hist_gradient_boosting/7be25053
|year|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|2025|8659|2363|0.272895|0.300598|0.283455|0|0.196572|0.579888|0.328463|
|2024|5783|1825|0.31558|0.29582|0.281761|2|0.215034|0.535625|0.346996|
|2026|2627|810|0.308337|0.302287|0.281761|5|0.217367|0.468941|0.29192|

### Results by Symbol: bull/logistic_regression/49a8608f
|symbol|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|AMZN|494|141|0.285425|0.301172|0.300981|0|0.204154|0.504993|0.29233|
|DIA|493|153|0.310345|0.301124|0.300981|0|0.213969|0.514869|0.327436|
|IWM|493|136|0.275862|0.301053|0.300981|0|0.200342|0.505952|0.281609|
|NVDA|493|161|0.326572|0.300247|0.300981|0|0.219587|0.550223|0.367124|
|TNA|493|145|0.294118|0.299242|0.300981|0|0.206979|0.548355|0.333143|
|TZA|493|121|0.245436|0.293342|0.300981|0|0.187905|0.556429|0.267733|
|QQQ|492|141|0.286585|0.30095|0.300981|0|0.204597|0.50496|0.292225|
|RWM|492|127|0.25813|0.300981|0.300981|0|0.193335|0.5|0.25813|
|XLE|492|177|0.359756|0.300019|0.300981|0|0.233263|0.519048|0.36875|
|GOOGL|491|162|0.329939|0.300668|0.300981|0|0.222027|0.495403|0.328409|
|QID|491|131|0.266802|0.300012|0.300981|0|0.196229|0.527778|0.278132|
|TQQQ|491|147|0.299389|0.300871|0.300981|0|0.209269|0.540381|0.319948|
|XLV|491|129|0.262729|0.301029|0.300981|0|0.1951|0.507752|0.27416|
|MSFT|490|150|0.306122|0.301101|0.300981|0|0.212463|0.497451|0.305415|
|XLI|490|139|0.283673|0.301543|0.300981|0|0.203447|0.505995|0.287606|
|XLP|490|151|0.308163|0.301101|0.300981|0|0.213228|0.502198|0.30938|
|XLRE|490|131|0.267347|0.301005|0.300981|0|0.197018|0.498607|0.267347|
|SOXL|489|166|0.339468|0.270006|0.300981|0|0.240217|0.563841|0.401071|
|SQQQ|488|126|0.258197|0.293335|0.300981|0|0.189812|0.581097|0.29599|
|XLY|488|144|0.295082|0.301077|0.300981|0|0.208006|0.504037|0.297928|
|AMD|487|160|0.328542|0.300367|0.300981|0|0.221222|0.508907|0.331896|
|SOXS|487|124|0.25462|0.2531|0.300981|0|0.180998|0.593964|0.298319|
|TSLA|487|146|0.299795|0.29152|0.300981|0|0.218272|0.445236|0.279616|
|SDS|486|144|0.296296|0.300413|0.300981|0|0.2082|0.516082|0.303158|
|SPXU|486|143|0.294239|0.296909|0.300981|0|0.205804|0.557453|0.32037|
|SPY|486|124|0.255144|0.300422|0.300981|0|0.191937|0.508399|0.258377|
|UPRO|486|125|0.257202|0.300869|0.300981|0|0.19265|0.536532|0.27948|
|SH|485|145|0.298969|0.300925|0.300981|0|0.209558|0.501471|0.299587|
|META|483|145|0.300207|0.301482|0.300981|0|0.210252|0.480575|0.29875|
|XLF|483|155|0.320911|0.300974|0.300981|0|0.218225|0.507956|0.330331|
|XLK|483|146|0.302277|0.301274|0.300981|0|0.210679|0.522906|0.32512|
|XLB|482|134|0.278008|0.30099|0.300981|0|0.201112|0.51113|0.28635|
|XLC|481|150|0.31185|0.301103|0.300981|0|0.214598|0.511823|0.324868|
|AAPL|475|149|0.313684|0.300944|0.300981|0|0.215497|0.496943|0.312798|
|XLU|468|130|0.277778|0.301317|0.300981|0|0.20089|0.528744|0.308843|

### Results by Sector: bull/logistic_regression/49a8608f
|sector|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|consumer_discretionary|1469|431|0.293397|0.297941|0.300981|0|0.210114|0.484033|0.28745|
|inverse_market|1457|432|0.2965|0.299415|0.300981|0|0.207853|0.525138|0.307404|
|communication_services|1455|457|0.314089|0.301082|0.300981|0|0.215662|0.495437|0.312896|
|technology|1448|445|0.30732|0.301107|0.300981|0|0.212863|0.505607|0.310886|
|inverse_small_caps|985|248|0.251777|0.297158|0.300981|0|0.190617|0.530226|0.263033|
|semiconductors|980|321|0.327551|0.300307|0.300981|0|0.220399|0.529727|0.347799|
|inverse_technology_growth|979|257|0.262513|0.296684|0.300981|0|0.19303|0.554542|0.286684|
|industrials_large_cap|493|153|0.310345|0.301124|0.300981|0|0.213969|0.514869|0.327436|
|leveraged_small_caps|493|145|0.294118|0.299242|0.300981|0|0.206979|0.548355|0.333143|
|small_caps|493|136|0.275862|0.301053|0.300981|0|0.200342|0.505952|0.281609|
|energy|492|177|0.359756|0.300019|0.300981|0|0.233263|0.519048|0.36875|
|technology_growth|492|141|0.286585|0.30095|0.300981|0|0.204597|0.50496|0.292225|
|health_care|491|129|0.262729|0.301029|0.300981|0|0.1951|0.507752|0.27416|
|leveraged_technology_growth|491|147|0.299389|0.300871|0.300981|0|0.209269|0.540381|0.319948|
|consumer_staples|490|151|0.308163|0.301101|0.300981|0|0.213228|0.502198|0.30938|
|industrials|490|139|0.283673|0.301543|0.300981|0|0.203447|0.505995|0.287606|
|real_estate|490|131|0.267347|0.301005|0.300981|0|0.197018|0.498607|0.267347|
|leveraged_semiconductors|489|166|0.339468|0.270006|0.300981|0|0.240217|0.563841|0.401071|
|inverse_semiconductors|487|124|0.25462|0.2531|0.300981|0|0.180998|0.593964|0.298319|
|broad_market|486|124|0.255144|0.300422|0.300981|0|0.191937|0.508399|0.258377|
|leveraged_market|486|125|0.257202|0.300869|0.300981|0|0.19265|0.536532|0.27948|
|financials|483|155|0.320911|0.300974|0.300981|0|0.218225|0.507956|0.330331|
|materials|482|134|0.278008|0.30099|0.300981|0|0.201112|0.51113|0.28635|
|utilities|468|130|0.277778|0.301317|0.300981|0|0.20089|0.528744|0.308843|

### Results by Regime: bull/logistic_regression/49a8608f
|market_regime_label|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|uptrend_low_vol|7706|2322|0.301324|0.298902|0.300981|0|0.210727|0.525618|0.316439|
|uptrend_high_vol|6083|1794|0.29492|0.298403|0.300981|0|0.207908|0.511873|0.300291|
|downtrend_high_vol|3070|844|0.274919|0.293547|0.300981|0|0.199827|0.51716|0.282457|
|mixed|210|38|0.180952|0.300594|0.300981|0|0.162171|0.52578|0.193211|

### Results by Year: bull/logistic_regression/49a8608f
|year|rows|positives|actual_rate|pred_mean|pred_median|pred_ge_0_50|brier|roc_auc|pr_auc|
|---|---|---|---|---|---|---|---|---|---|
|2025|8659|2363|0.272895|0.296676|0.300981|0|0.198863|0.528421|0.28815|
|2024|5783|1825|0.31558|0.298645|0.300981|0|0.216529|0.512749|0.322634|
|2026|2627|810|0.308337|0.299525|0.300981|0|0.213914|0.50784|0.313368|

## Probability Diagnosis
|model|poorly_calibrated|nearly_constant|class_imbalance|feature_selection_failure|label_definition_defect|legitimate_scarcity|notes|
|---|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|yes|yes|yes|yes|no evidence found|yes, but not sufficient alone|TBS pass rows=6; max TBS p=1; Brier skill=0.001434; ROC-AUC=0.548222|
|bear/hist_gradient_boosting/58ee8cd6|yes|yes|yes|yes|no evidence found|yes, but not sufficient alone|TBS pass rows=0; max TBS p=0.383333; Brier skill=0.003139; ROC-AUC=0.52817|
|bear/logistic_regression/94fce54c|yes|yes|yes|yes|no evidence found|yes, but not sufficient alone|TBS pass rows=0; max TBS p=0.454545; Brier skill=0.003539; ROC-AUC=0.531285|
|bull/extra_trees/d90e8c92|yes|yes|yes|yes|no evidence found|yes, but not sufficient alone|TBS pass rows=0; max TBS p=0.379845; Brier skill=0.002259; ROC-AUC=0.544013|
|bull/hist_gradient_boosting/7be25053|borderline|mostly compressed with rare spikes|yes|yes|no evidence found|yes, but not sufficient alone|TBS pass rows=5; max TBS p=1; Brier skill=0.005337; ROC-AUC=0.543318|
|bull/logistic_regression/49a8608f|yes|yes|yes|yes|no evidence found|yes, but not sufficient alone|TBS pass rows=0; max TBS p=0.317829; Brier skill=-0.000152; ROC-AUC=0.51967|

Interpretation: the probabilities are compressed around the split base rates, with rare isotonic extremes in the tree models. Brier skill is effectively zero for every target-before-stop head (`-0.00015` to `0.00534`), and ROC-AUC is only `0.5197` to `0.5482`. Class imbalance is present because positives are about `25.86%` for bear and `29.28%` for bull in holdout, but the base rates are not so low that they alone explain zero target-threshold pass-through. The stronger blocker is that the target-before-stop head inherits features selected for the positive-return head and receives no market-relative, sector-relative, inverse ETF, breadth, relationship, or regime features.

## Concentration Audit
|dimension|counts|
|---|---|
|symbols|SDS=5, TZA=5, QID=1|
|sectors|inverse_market=5, inverse_small_caps=5, inverse_technology_growth=1|
|years|2024=6, 2026=5|
|roles|leveraged_inverse_etf=11|

### Selected Rows
|Date|symbol|role|sector|year|direction|family|model|primary_p|expected_return|tbs_p|
|---|---|---|---|---|---|---|---|---|---|---|
|2024-05-03|SDS|leveraged_inverse_etf|inverse_market|2024|bear|extra_trees|1f47da02|0.599783|0.030625|0.5|
|2024-05-06|SDS|leveraged_inverse_etf|inverse_market|2024|bear|extra_trees|1f47da02|0.599783|0.030791|0.957066|
|2024-05-07|SDS|leveraged_inverse_etf|inverse_market|2024|bear|extra_trees|1f47da02|0.599783|0.032822|1|
|2024-05-08|SDS|leveraged_inverse_etf|inverse_market|2024|bear|extra_trees|1f47da02|0.599783|0.020529|0.961377|
|2024-05-10|QID|leveraged_inverse_etf|inverse_technology_growth|2024|bear|extra_trees|1f47da02|0.599783|0.015228|0.5|
|2024-12-31|SDS|leveraged_inverse_etf|inverse_market|2024|bear|extra_trees|1f47da02|0.599783|0.023736|0.5|
|2026-01-13|TZA|leveraged_inverse_etf|inverse_small_caps|2026|bull|hist_gradient_boosting|7be25053|0.550082|0.021002|1|
|2026-01-15|TZA|leveraged_inverse_etf|inverse_small_caps|2026|bull|hist_gradient_boosting|7be25053|0.556522|0.024706|1|
|2026-01-16|TZA|leveraged_inverse_etf|inverse_small_caps|2026|bull|hist_gradient_boosting|7be25053|0.552288|0.024749|1|
|2026-01-20|TZA|leveraged_inverse_etf|inverse_small_caps|2026|bull|hist_gradient_boosting|7be25053|0.550082|0.014085|0.795736|
|2026-01-22|TZA|leveraged_inverse_etf|inverse_small_caps|2026|bull|hist_gradient_boosting|7be25053|0.550082|0.019397|1|

Why leveraged/inverse ETFs dominate: the selected rows must clear expected return, target-before-stop probability, and liquidity simultaneously. Leveraged inverse ETFs have larger daily path ranges and higher model-predicted returns/MFE, so they are more likely to clear a `2 ATR target before 1 ATR stop` probability screen while also passing the dollar-volume requirement. The frozen caps are per-date/global, not per role, sector, inverse/leveraged class, or correlation cluster. Because the selected sample is only 11 rows, this creates extreme concentration: SDS/QID in 2024 for bear extra trees and TZA in 2026 for bull hist-gradient boosting.

## Feature-Family Audit

### Generated Numeric Features by Family
|family|generated_numeric_features|
|---|---|
|breadth|6|
|candle_geometry|8|
|inverse_leveraged|12|
|market_relative|20|
|regime|3|
|relationship_graph|60|
|returns_momentum|29|
|rsi_family|294|
|sector_relative|8|
|technical_primitives|29|
|trend_structure|32|
|volatility_range|16|
|volume_participation|11|

### Selected Features by Family
|model|selected_total|returns_momentum|trend_structure|volatility_range|volume_participation|candle_geometry|rsi_family|market_relative|sector_relative|inverse_leveraged|breadth|relationship_graph|regime|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|60|16|23|9|6|3|3|0|0|0|0|0|0|
|bear/hist_gradient_boosting/58ee8cd6|60|16|23|9|6|3|3|0|0|0|0|0|0|
|bear/logistic_regression/94fce54c|60|16|23|9|6|3|3|0|0|0|0|0|0|
|bull/extra_trees/d90e8c92|60|16|23|8|6|3|4|0|0|0|0|0|0|
|bull/hist_gradient_boosting/7be25053|60|16|23|8|6|3|4|0|0|0|0|0|0|
|bull/logistic_regression/49a8608f|60|16|23|8|6|3|4|0|0|0|0|0|0|

### Target-Before-Stop Permutation Importance by Family
Positive `delta_brier` means shuffling that family made target-before-stop Brier worse; negative values mean shuffling improved Brier for that run.
|model|family|features|sum_delta_brier|positive_sum_delta_brier|top_feature|top_delta_brier|
|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|candle_geometry|3|-0.00004938|0.00004235|close_position|0.00004235|
|bear/extra_trees/1f47da02|returns_momentum|16|-0.00146762|0.00007379|return_10|0.00005187|
|bear/extra_trees/1f47da02|rsi_family|3|-0.00026631|0.0000549|rsi_2_slope_3|0.0000549|
|bear/extra_trees/1f47da02|trend_structure|23|-0.0006297|0.00082498|trend_persistence_20|0.00055784|
|bear/extra_trees/1f47da02|volatility_range|9|-0.00044948|0.00006817|range_pct|0.0000448|
|bear/extra_trees/1f47da02|volume_participation|6|-0.00030579|0.00001738|down_volume_proxy_20|0.00001738|
|bear/hist_gradient_boosting/58ee8cd6|candle_geometry|3|-0.00015186|0.00000269|upper_wick_pct|0.00000269|
|bear/hist_gradient_boosting/58ee8cd6|returns_momentum|16|0.00036111|0.00048147|return_126|0.0001953|
|bear/hist_gradient_boosting/58ee8cd6|rsi_family|3|0.00002068|0.00004106|rsi_2_slope_3|0.00002211|
|bear/hist_gradient_boosting/58ee8cd6|trend_structure|23|0.00089601|0.00135514|trend_persistence_20|0.0004121|
|bear/hist_gradient_boosting/58ee8cd6|volatility_range|9|0.00077291|0.00099047|volatility_compression_20_100|0.00038668|
|bear/hist_gradient_boosting/58ee8cd6|volume_participation|6|-0.00003373|0.00006156|down_volume_proxy_20|0.00003332|
|bear/logistic_regression/94fce54c|candle_geometry|3|-0.00000557|0.00002986|upper_wick_pct|0.00002045|
|bear/logistic_regression/94fce54c|returns_momentum|16|0.00111897|0.00132725|return_126|0.00059817|
|bear/logistic_regression/94fce54c|rsi_family|3|0.00000736|0.00006188|rsi_2_accel|0.00005442|
|bear/logistic_regression/94fce54c|trend_structure|23|0.00922158|0.00977504|distance_sma_100|0.00533028|
|bear/logistic_regression/94fce54c|volatility_range|9|0.00138415|0.00138415|realized_vol_63|0.00075971|
|bear/logistic_regression/94fce54c|volume_participation|6|0.00014921|0.00029722|Volume|0.00015316|
|bull/extra_trees/d90e8c92|candle_geometry|3|-0.00006067|0|upper_wick_pct|-0.00000681|
|bull/extra_trees/d90e8c92|returns_momentum|16|-0.00053119|0.00024766|return_126|0.00015917|
|bull/extra_trees/d90e8c92|rsi_family|4|-0.00014284|0.00009836|rsi_2_accel|0.00009836|
|bull/extra_trees/d90e8c92|trend_structure|23|-0.00028435|0.00044928|distance_prior_high_63|0.00012266|
|bull/extra_trees/d90e8c92|volatility_range|8|0.00013623|0.00032871|volatility_compression_20_100|0.00010494|
|bull/extra_trees/d90e8c92|volume_participation|6|0.00010064|0.00016898|dollar_volume|0.0000819|
|bull/hist_gradient_boosting/7be25053|candle_geometry|3|0.00002224|0.00007735|upper_wick_pct|0.00004457|
|bull/hist_gradient_boosting/7be25053|returns_momentum|16|0.00111659|0.00143255|return_252|0.00045809|
|bull/hist_gradient_boosting/7be25053|rsi_family|4|-0.00015087|0.00005703|rsi_2_accel|0.00004061|
|bull/hist_gradient_boosting/7be25053|trend_structure|23|0.00203338|0.00262404|trend_persistence_20|0.00068601|
|bull/hist_gradient_boosting/7be25053|volatility_range|8|0.00220237|0.00224358|volatility_compression_20_100|0.00103142|
|bull/hist_gradient_boosting/7be25053|volume_participation|6|0.00035966|0.00037928|up_volume_proxy_20|0.0001913|
|bull/logistic_regression/49a8608f|candle_geometry|3|-0.00005382|0|upper_wick_pct|-0.00001309|
|bull/logistic_regression/49a8608f|returns_momentum|16|0.01236624|0.01327849|return_63|0.00427849|
|bull/logistic_regression/49a8608f|rsi_family|4|-0.00045309|0|rsi_2_accel|-0.00002713|
|bull/logistic_regression/49a8608f|trend_structure|23|0.01410081|0.01598102|distance_sma_20|0.00811907|
|bull/logistic_regression/49a8608f|volatility_range|8|0.00400296|0.00427363|realized_vol_20|0.00238301|
|bull/logistic_regression/49a8608f|volume_participation|6|-0.00003985|0.00011402|up_volume_proxy_20|0.00011344|

### Are the Added Market/Relationship Families Used?
|model|used_added_families|missing_added_families|
|---|---|---|
|bear/extra_trees/1f47da02|none|market_relative, sector_relative, inverse_leveraged, breadth, relationship_graph, regime|
|bear/hist_gradient_boosting/58ee8cd6|none|market_relative, sector_relative, inverse_leveraged, breadth, relationship_graph, regime|
|bear/logistic_regression/94fce54c|none|market_relative, sector_relative, inverse_leveraged, breadth, relationship_graph, regime|
|bull/extra_trees/d90e8c92|none|market_relative, sector_relative, inverse_leveraged, breadth, relationship_graph, regime|
|bull/hist_gradient_boosting/7be25053|none|market_relative, sector_relative, inverse_leveraged, breadth, relationship_graph, regime|
|bull/logistic_regression/49a8608f|none|market_relative, sector_relative, inverse_leveraged, breadth, relationship_graph, regime|

The answer is no: none of the six target-before-stop heads uses market-relative, sector-relative, inverse ETF, breadth, relationship, or regime features. This is true even though the generated panel contains 109 numeric columns from those families (`market_relative`, `sector_relative`, `inverse_leveraged`, `breadth`, `relationship_graph`, and `regime`).

## Manual Target-Before-Stop Label Verification

Manual definition used: signal at close, next-session open entry, signal-date ATR(14), target at `2 * ATR`, stop at `1 * ATR`, future bars from `t+1` through `t+10`, and same-bar target/stop ambiguity counted as stop-first. Near-threshold rejected rows are the closest rejected rows below the frozen `0.50` target-before-stop threshold after primary probability, expected-return, and liquidity filters when such rows exist; otherwise they are the closest rejected rows below `0.50`. Ordinary rejected rows are deterministic, evenly spaced nonselected holdout rows outside the near-threshold sample.
|model|bucket|Date|symbol|primary_p|expected_return|tbs_p|entry_date|entry_open|atr14|target|stop|target_at|target_date|stop_at|stop_date|same_bar|stored_label|manual_label|matches|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|bear/extra_trees/1f47da02|selected|2024-05-07|SDS|0.599783|0.032822|1|2024-05-08|129.35|3.1002|123.1497|132.4502|6|2024-05-15|||False|1|1|True|
|bear/extra_trees/1f47da02|selected|2024-05-06|SDS|0.599783|0.030791|0.957066|2024-05-07|128.15|3.254|121.6419|131.404|||||False|0|0|True|
|bear/extra_trees/1f47da02|selected|2024-05-03|SDS|0.599783|0.030625|0.5|2024-05-06|130.05|3.3005|123.449|133.3505|8|2024-05-15|||False|1|1|True|
|bear/extra_trees/1f47da02|selected|2024-12-31|SDS|0.599783|0.023736|0.5|2025-01-02|97.25|2.2659|92.7182|99.5159|||1|2025-01-02|False|0|0|True|
|bear/extra_trees/1f47da02|selected|2024-05-08|SDS|0.599783|0.020529|0.961377|2024-05-09|128.45|2.968|122.514|131.418|5|2024-05-15|||False|1|1|True|
|bear/extra_trees/1f47da02|near_threshold_rejected|2024-08-07|SOXS|0.599783|0.206909|0.4|2024-08-08|669.6|73.7024|522.1951|743.3024|4|2024-08-13|||False|1|1|True|
|bear/extra_trees/1f47da02|near_threshold_rejected|2024-05-02|SOXS|0.599783|0.144682|0.4|2024-05-03|708.2|62.7505|582.6989|770.9505|9|2024-05-15|||False|1|1|True|
|bear/extra_trees/1f47da02|near_threshold_rejected|2024-11-14|SOXS|0.599783|0.134813|0.4|2024-11-15|482.2|30.6686|420.8628|512.8686|||9|2024-11-27|False|0|0|True|
|bear/extra_trees/1f47da02|near_threshold_rejected|2026-03-26|SOXS|0.599783|0.128912|0.4|2026-03-27|41.94|3.8388|34.2625|45.7788|||2|2026-03-30|False|0|0|True|
|bear/extra_trees/1f47da02|near_threshold_rejected|2024-11-26|SOXS|0.599783|0.095735|0.4|2024-11-27|481|31.1561|418.6878|512.1561|||1|2024-11-27|False|0|0|True|
|bear/extra_trees/1f47da02|ordinary_rejected|2024-05-02|AAPL|0.480198|0.013052|0.258619|2024-05-03|186.65|3.4771|179.6958|190.1271|||9|2024-05-15|False|0|0|True|
|bear/extra_trees/1f47da02|ordinary_rejected|2024-10-28|XLB|0.440906|-0.002368|0.264057|2024-10-29|47.14|0.544|46.0519|47.684|||7|2024-11-06|False|0|0|True|
|bear/extra_trees/1f47da02|ordinary_rejected|2025-04-29|NVDA|0.440906|0.016806|0.264057|2025-04-30|104.47|6.4111|91.6478|110.8811|||2|2025-05-01|False|0|0|True|
|bear/extra_trees/1f47da02|ordinary_rejected|2025-10-22|RWM|0.482881|0.018488|0.264057|2025-10-23|16.64|0.315|16.01|16.955|||||False|0|0|True|
|bear/extra_trees/1f47da02|ordinary_rejected|2026-04-22|XLY|0.440906|0.014014|0.258619|2026-04-23|118.22|2.3|113.6201|120.52|||10|2026-05-06|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|selected|n/a|n/a||||||||||||||n/a|n/a|not_available (selected rows=0)|
|bear/hist_gradient_boosting/58ee8cd6|near_threshold_rejected|2025-10-15|AMD|0.561122|0.058928|0.383333|2025-10-16|236.29|12.1963|211.8973|248.4863|||7|2025-10-24|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|near_threshold_rejected|2024-07-10|AAPL|0.561122|0.054634|0.383333|2024-07-11|231.39|4.6602|222.0695|236.0502|||3|2024-07-15|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|near_threshold_rejected|2025-10-08|AMD|0.561122|0.047929|0.383333|2025-10-09|236.3|11.2228|213.8545|247.5228|2|2025-10-10|||False|1|1|True|
|bear/hist_gradient_boosting/58ee8cd6|near_threshold_rejected|2024-05-02|SOXS|0.777778|0.125854|0.33121|2024-05-03|708.2|62.7505|582.6989|770.9505|9|2024-05-15|||False|1|1|True|
|bear/hist_gradient_boosting/58ee8cd6|near_threshold_rejected|2024-11-26|SOXS|0.561122|0.099877|0.33121|2024-11-27|481|31.1561|418.6878|512.1561|||1|2024-11-27|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|ordinary_rejected|2024-05-02|AAPL|0.470513|-0.000611|0.25915|2024-05-03|186.65|3.4771|179.6958|190.1271|||9|2024-05-15|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|ordinary_rejected|2024-10-28|TQQQ|0.44973|-0.011359|0.25915|2024-10-29|37.47|1.4084|34.6533|38.8784|||7|2024-11-06|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|ordinary_rejected|2025-04-29|XLU|0.457143|0.01125|0.25915|2025-04-30|39.49|0.8437|37.8026|40.3337|||5|2025-05-06|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|ordinary_rejected|2025-10-23|AAPL|0.44973|-0.004699|0.25915|2025-10-24|261.19|5.1906|250.8089|266.3806|||2|2025-10-27|False|0|0|True|
|bear/hist_gradient_boosting/58ee8cd6|ordinary_rejected|2026-04-22|XLY|0.44973|0.005529|0.25915|2026-04-23|118.22|2.3|113.6201|120.52|||10|2026-05-06|False|0|0|True|
|bear/logistic_regression/94fce54c|selected|n/a|n/a||||||||||||||n/a|n/a|not_available (selected rows=0)|
|bear/logistic_regression/94fce54c|near_threshold_rejected|2025-04-08|SOXS|1|0.137732|0.454545|2025-04-09|919.4|104.8753|709.6494|1,024|1|2025-04-09|||False|1|1|True|
|bear/logistic_regression/94fce54c|near_threshold_rejected|2025-04-09|SPXU|0.563636|0.180597|0.454545|2025-04-10|107.56|12.5752|82.4096|120.1352|||1|2025-04-10|False|0|0|True|
|bear/logistic_regression/94fce54c|near_threshold_rejected|2025-04-07|SOXS|0.563636|0.156879|0.454545|2025-04-08|748|90.3734|567.2533|838.3734|||1|2025-04-08|False|0|0|True|
|bear/logistic_regression/94fce54c|near_threshold_rejected|2024-08-05|SOXS|0.563636|0.151866|0.454545|2024-08-06|677|66.746|543.5079|743.746|6|2024-08-13|||False|1|1|True|
|bear/logistic_regression/94fce54c|near_threshold_rejected|2024-12-18|SOXS|0.563636|0.120571|0.454545|2024-12-19|455|34.6794|385.6411|489.6794|||2|2024-12-20|False|0|0|True|
|bear/logistic_regression/94fce54c|ordinary_rejected|2024-05-02|AAPL|0.496098|0.014707|0.259737|2024-05-03|186.65|3.4771|179.6958|190.1271|||9|2024-05-15|False|0|0|True|
|bear/logistic_regression/94fce54c|ordinary_rejected|2024-10-24|TZA|0.496098|0.048234|0.259737|2024-10-25|13.46|0.616|12.228|14.076|||5|2024-10-31|False|0|0|True|
|bear/logistic_regression/94fce54c|ordinary_rejected|2025-04-25|GOOGL|0.445257|0.000877|0.259737|2025-04-28|162.43|5.9294|150.5712|168.3594|8|2025-05-07|||False|1|1|True|
|bear/logistic_regression/94fce54c|ordinary_rejected|2025-10-20|XLK|0.445257|0.01232|0.259737|2025-10-21|144.01|2.4259|139.1583|146.4359|||4|2025-10-24|False|0|0|True|
|bear/logistic_regression/94fce54c|ordinary_rejected|2026-04-22|XLY|0.440256|-0.019937|0.253996|2026-04-23|118.22|2.3|113.6201|120.52|||10|2026-05-06|False|0|0|True|
|bull/extra_trees/d90e8c92|selected|n/a|n/a||||||||||||||n/a|n/a|not_available (selected rows=0)|
|bull/extra_trees/d90e8c92|near_threshold_rejected|2026-03-26|SOXL|0.666667|0.128|0.379845|2026-03-27|48.04|5.5069|59.0538|42.5331|||2|2026-03-30|False|0|0|True|
|bull/extra_trees/d90e8c92|near_threshold_rejected|2025-03-10|TSLA|0.564516|0.083237|0.379845|2025-03-11|225.31|20.9176|267.1451|204.3924|10|2025-03-24|||False|1|1|True|
|bull/extra_trees/d90e8c92|near_threshold_rejected|2025-11-05|QID|0.555145|0.077234|0.379845|2025-11-06|20.08|0.5843|21.2487|19.4957|2|2025-11-07|||False|1|1|True|
|bull/extra_trees/d90e8c92|near_threshold_rejected|2025-07-22|NVDA|0.564516|0.072325|0.379845|2025-07-23|169.53|3.9924|177.5148|165.5376|5|2025-07-29|||False|1|1|True|
|bull/extra_trees/d90e8c92|near_threshold_rejected|2025-11-04|SQQQ|0.555145|0.064865|0.379845|2025-11-05|69.2|3.021|75.242|66.179|3|2025-11-07|||False|1|1|True|
|bull/extra_trees/d90e8c92|ordinary_rejected|2024-05-02|AAPL|0.555145|-0.018657|0.308595|2024-05-03|186.65|3.4771|193.6042|183.1729|||1|2024-05-03|False|0|0|True|
|bull/extra_trees/d90e8c92|ordinary_rejected|2024-10-21|UPRO|0.555145|-0.002956|0.308595|2024-10-22|88.63|2.3002|93.2304|86.3298|||2|2024-10-23|False|0|0|True|
|bull/extra_trees/d90e8c92|ordinary_rejected|2025-04-17|TZA|0.457405|-0.059726|0.277388|2025-04-21|19.39|2.1722|23.7345|17.2178|||3|2025-04-23|False|0|0|True|
|bull/extra_trees/d90e8c92|ordinary_rejected|2025-10-20|XLP|0.555145|-0.003107|0.312012|2025-10-21|79.8|0.7981|81.3962|79.0019|||2|2025-10-22|False|0|0|True|
|bull/extra_trees/d90e8c92|ordinary_rejected|2026-04-22|XLY|0.561822|-0.005184|0.283435|2026-04-23|118.22|2.3|122.8199|115.92|||||False|0|0|True|
|bull/hist_gradient_boosting/7be25053|selected|2026-01-15|TZA|0.556522|0.024706|1|2026-01-16|5.99|0.2972|6.5843|5.6928|||4|2026-01-22|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|selected|2026-01-16|TZA|0.552288|0.024749|1|2026-01-20|6.3|0.2881|6.8762|6.0119|||2|2026-01-21|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|selected|2026-01-13|TZA|0.550082|0.021002|1|2026-01-14|6.3|0.3038|6.9076|5.9962|||2|2026-01-15|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|selected|2026-01-22|TZA|0.550082|0.019397|1|2026-01-23|5.76|0.2962|6.3524|5.4638|5|2026-01-29|||False|1|1|True|
|bull/hist_gradient_boosting/7be25053|selected|2026-01-20|TZA|0.550082|0.014085|0.795736|2026-01-21|6.06|0.2896|6.6393|5.7704|||2|2026-01-22|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|near_threshold_rejected|2025-04-04|TNA|0.550082|0.113719|0.473684|2025-04-07|18.91|2.5694|24.0489|16.3406|1|2025-04-07|||False|1|1|True|
|bull/hist_gradient_boosting/7be25053|near_threshold_rejected|2025-10-20|SOXS|0.550082|0.101497|0.473684|2025-10-21|77.8|7.7891|93.3781|70.0109|||5|2025-10-27|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|near_threshold_rejected|2025-05-12|TZA|0.556522|0.090435|0.473684|2025-05-13|13.27|1.4434|16.1567|11.8266|||||False|0|0|True|
|bull/hist_gradient_boosting/7be25053|near_threshold_rejected|2025-10-23|SOXS|0.550082|0.069977|0.473684|2025-10-24|74|7.7242|89.4484|66.2758|||4|2025-10-29|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|near_threshold_rejected|2025-02-25|TSLA|0.556522|0.06766|0.473684|2025-02-26|303.71|19.5062|342.7225|284.2038|||2|2025-02-27|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|ordinary_rejected|2024-05-02|AAPL|0.522914|0.00347|0.281761|2024-05-03|186.65|3.4771|193.6042|183.1729|||1|2024-05-03|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|ordinary_rejected|2024-10-17|SDS|0.439741|-0.007279|0.304894|2024-10-18|100.2|2.0642|104.3284|98.1358|10|2024-10-31|||False|1|1|True|
|bull/hist_gradient_boosting/7be25053|ordinary_rejected|2025-04-10|XLY|0.522914|-0.001246|0.281761|2025-04-11|93.75|4.2962|102.3423|89.4538|||6|2025-04-21|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|ordinary_rejected|2025-10-23|UPRO|0.550082|0.000197|0.281761|2025-10-24|115.45|3.5107|122.4714|111.9393|||10|2025-11-06|False|0|0|True|
|bull/hist_gradient_boosting/7be25053|ordinary_rejected|2026-04-22|XLY|0.550082|-0.003349|0.281761|2026-04-23|118.22|2.3|122.8199|115.92|||||False|0|0|True|
|bull/logistic_regression/49a8608f|selected|n/a|n/a||||||||||||||n/a|n/a|not_available (selected rows=0)|
|bull/logistic_regression/49a8608f|near_threshold_rejected|2025-06-16|SOXL|1|0.149721|0.317829|2025-06-17|21.61|1.4909|24.5918|20.1191|6|2025-06-25|||False|1|1|True|
|bull/logistic_regression/49a8608f|near_threshold_rejected|2025-06-12|SOXL|1|0.143923|0.317829|2025-06-13|20.32|1.4062|23.1324|18.9138|7|2025-06-24|||False|1|1|True|
|bull/logistic_regression/49a8608f|near_threshold_rejected|2025-06-11|SOXL|1|0.142606|0.317829|2025-06-12|21.24|1.439|24.118|19.801|9|2025-06-25|||False|1|1|True|
|bull/logistic_regression/49a8608f|near_threshold_rejected|2025-06-13|SOXL|1|0.141193|0.317829|2025-06-16|20.83|1.4379|23.7058|19.3921|6|2025-06-24|||False|1|1|True|
|bull/logistic_regression/49a8608f|near_threshold_rejected|2025-06-17|SOXL|1|0.134449|0.317829|2025-06-18|21.72|1.4694|24.6589|20.2506|6|2025-06-26|||False|1|1|True|
|bull/logistic_regression/49a8608f|ordinary_rejected|2024-05-02|AAPL|0.502041|-0.009653|0.300981|2024-05-03|186.65|3.4771|193.6042|183.1729|||1|2024-05-03|False|0|0|True|
|bull/logistic_regression/49a8608f|ordinary_rejected|2024-10-24|UPRO|0.557204|0.013276|0.300981|2024-10-25|88.69|2.3448|93.3796|86.3452|||5|2024-10-31|False|0|0|True|
|bull/logistic_regression/49a8608f|ordinary_rejected|2025-04-23|UPRO|0.558017|0.080783|0.300981|2025-04-24|61.41|6.03|73.47|55.38|||||False|0|0|True|
|bull/logistic_regression/49a8608f|ordinary_rejected|2025-10-28|SOXL|0.557204|0.005469|0.300981|2025-10-29|49.37|3.0595|55.489|46.3105|||5|2025-11-04|False|0|0|True|
|bull/logistic_regression/49a8608f|ordinary_rejected|2026-04-22|XLY|0.557204|0.019342|0.300981|2026-04-23|118.22|2.3|122.8199|115.92|||||False|0|0|True|

Manual label result: `70/70` checked rows matched stored labels. Rows marked `not_available` indicate that the model had fewer than five selected rows in that bucket, not a label failure.

## Root-Cause Classification

- Implementation defect: not found for target-before-stop label computation or gate replay. Manual labels matched stored labels. The implementation does, however, route target-before-stop through a feature set selected for a different target; that is classified below as a feature-selection problem.
- Label-definition defect: not found. The label is intentionally asymmetric (`2 ATR` target before `1 ATR` stop) and conservative on same-bar ambiguity. That definition creates scarcity, but the stored labels match the documented implementation.
- Probability-calibration defect: contributory. Target-head Brier skill is approximately zero, decile calibration errors remain material, and several models never produce a target-before-stop probability above `0.50`.
- Class-imbalance problem: contributory. Holdout positives are about `25.86%` for bear and `29.28%` for bull. This is a minority class, but not rare enough to explain the failure without the feature and calibration evidence.
- Feature-selection problem: primary root cause. Target-before-stop uses features screened for positive-return prediction and excludes every generated market-relative, sector-relative, inverse ETF, breadth, relationship, and regime feature.
- Model-family limitation: contributory. With the current selected feature set, the tested linear/tree families extract little target-before-stop skill; this does not prove the families would fail after target-specific feature selection.
- Legitimate absence of predictive signal: not established. Current holdout evidence shows near-zero skill, but the feature-selection failure prevents concluding that the richer feature space has no signal.

## Data Leakage Review

The replay used persisted model bundles and the existing modeling parquet. No model was fit. No thresholds were changed. No data files were refreshed. Manual label verification intentionally looked forward from historical signal dates only to audit stored labels; those future bars were not used as model inputs. Feature rows remain close-known, and target labels remain `label_` columns outside feature matrices.

## Exact Assumptions Introduced

- `learned model` excludes `naive_base_rate` controls.
- Selection funnel counts are cumulative in frozen policy order.
- Target-before-stop prediction diagnostics are holdout diagnostics unless the table explicitly says training or calibration.
- Near-threshold rejected rows are defined by closeness below the frozen target-before-stop threshold as described in the manual verification section.
- Ordinary rejected rows are deterministic nonselected holdout samples and are not claimed to be representative performance estimates.

## Known Limitations

- This is a read-only diagnosis; it does not test whether a corrected target-specific feature-selection pipeline improves performance.
- The report does not use a new untouched holdout and does not make a live-forward claim.
- Group-level ROC-AUC/PR-AUC is `nan` where a group has only one observed class.
- No `pytest`, `ruff`, `ruff format --check`, or `mypy` runs were performed because no code was changed and the user requested diagnosis only.

## Scope Changes

None. No options, intraday data, news/NLP, brokerage execution, reinforcement learning, deep learning, provider changes, threshold changes, promotion, retraining, or forward-update occurred.

## One Smallest Engineering Correction

Change the target-before-stop head to perform its own train-only feature screening against `label_{direction}_target_before_stop_{horizon}` instead of reusing the positive-return classifier feature screen.
