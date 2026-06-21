# Target-Before-Stop Calibration and Policy Diagnosis

Generation: `2026-06-21T19:28:21.433666+00:00`

This is a read-only diagnosis. It did not retrain, update data, change thresholds, promote models, run scanner, run forward-update, or run daily-cycle. The only intended output is this Markdown report.

## Executive Summary

- The target-specific feature-screening defect is fixed in this generation: every learned TBS head has schema `target_specific_feature_screen_v1` and its own TBS feature-manifest hash.
- The remaining weakness is not one single software defect. The dominant evidence is weak raw discrimination, isotonic calibration plateaus/extreme steps in some models, temporal/product-class instability, and a fixed `0.50` policy that many calibrated heads rarely or never cross.
- Calibration is monotonic and rank-preserving in the formal sense; rank inversions were not found. However, isotonic calibration collapses many raw scores into repeated probability plateaus and sometimes creates poorly supported 0/1 outputs.
- The holdout is no longer a pristine final holdout. It is a development holdout repeatedly inspected during engineering diagnosis. It can support debugging and governance conclusions, not final performance claims.

## 1. Current Learned TBS Heads
|model|dir|family|target|TBS manifest|features|calibration|train|cal|hold|train +rate|cal +rate|hold +rate|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|bear|extra_trees|label_bear_target_before_stop_10|5686b06cd201d6de|60|isotonic|41884|16800|17069|0.2601|0.2580|0.2586|
|1384f70b|bear|hist_gradient_boosting|label_bear_target_before_stop_10|5686b06cd201d6de|60|isotonic|41884|16800|17069|0.2601|0.2580|0.2586|
|e03e236f|bear|logistic_regression|label_bear_target_before_stop_10|5686b06cd201d6de|60|isotonic|41884|16800|17069|0.2601|0.2580|0.2586|
|35780908|bull|extra_trees|label_bull_target_before_stop_10|16ac954d6e427a96|60|isotonic|41884|16800|17069|0.3006|0.2993|0.2928|
|217dea02|bull|hist_gradient_boosting|label_bull_target_before_stop_10|16ac954d6e427a96|60|isotonic|41884|16800|17069|0.3006|0.2993|0.2928|
|0d0332fb|bull|logistic_regression|label_bull_target_before_stop_10|16ac954d6e427a96|60|isotonic|41884|16800|17069|0.3006|0.2993|0.2928|

Naive models in this generation are controls only: `922c8390893c8adeb75f3a02`, `9ef9537bdfd9a3815defc635`.

### Selected Feature Families
|model|TBS selected families|
|---|---|
|8ff714ce|breadth:3; inverse_leveraged:7; market_relative:5; regime:2; relationship_graph:20; rsi_family:3; sector_relative:1; technical_primitives:7; trend_structure:4; volatility_range:5; volume_participation:3|
|1384f70b|breadth:3; inverse_leveraged:7; market_relative:5; regime:2; relationship_graph:20; rsi_family:3; sector_relative:1; technical_primitives:7; trend_structure:4; volatility_range:5; volume_participation:3|
|e03e236f|breadth:3; inverse_leveraged:7; market_relative:5; regime:2; relationship_graph:20; rsi_family:3; sector_relative:1; technical_primitives:7; trend_structure:4; volatility_range:5; volume_participation:3|
|35780908|breadth:2; inverse_leveraged:5; market_relative:4; regime:2; relationship_graph:23; rsi_family:5; sector_relative:1; technical_primitives:6; trend_structure:4; volatility_range:5; volume_participation:3|
|217dea02|breadth:2; inverse_leveraged:5; market_relative:4; regime:2; relationship_graph:23; rsi_family:5; sector_relative:1; technical_primitives:6; trend_structure:4; volatility_range:5; volume_participation:3|
|0d0332fb|breadth:2; inverse_leveraged:5; market_relative:4; regime:2; relationship_graph:23; rsi_family:5; sector_relative:1; technical_primitives:6; trend_structure:4; volatility_range:5; volume_participation:3|

Selected feature names are persisted in each artifact and in the model registry metric `target_before_stop_selected_features_json`. The screen selected all requested market/sector/inverse-breadth/relationship/regime families in this generation, but this is not evidence of a trading edge.

## 2. Raw Versus Calibrated Probability Distributions
### Calibration Distribution Summary
|model|dir|family|raw min|raw max|raw mean|raw std|raw uniq|raw plateau|raw >=.50|cal min|cal max|cal mean|cal std|cal uniq|cal plateau|cal >=.50|rank corr|inversions|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|bear|extra_trees|0.1885|0.5914|0.4146|0.0614|16800|1 (0.0%)|1151|0.0000|0.5000|0.2580|0.0110|6|16584 (98.7%)|4|0.1951|0|
|1384f70b|bear|hist_gradient_boosting|0.0402|0.7276|0.2856|0.1120|15715|10 (0.1%)|821|0.0000|0.2646|0.2580|0.0108|5|9837 (58.6%)|0|0.8613|0|
|e03e236f|bear|logistic_regression|0.0011|0.7580|0.2813|0.1777|16800|1 (0.0%)|1963|0.0000|1.0000|0.2580|0.0307|11|7226 (43.0%)|4|0.9333|0|
|35780908|bull|extra_trees|0.1934|0.5926|0.4084|0.0592|16800|1 (0.0%)|822|0.0000|0.7000|0.2993|0.0163|9|7342 (43.7%)|13|0.9331|0|
|217dea02|bull|hist_gradient_boosting|0.0636|0.6018|0.3098|0.0778|16343|4 (0.0%)|156|0.0000|0.5000|0.2993|0.0315|20|2650 (15.8%)|4|0.9940|0|
|0d0332fb|bull|logistic_regression|0.1625|0.8495|0.5524|0.1205|16800|1 (0.0%)|10875|0.0000|0.3554|0.2993|0.0451|15|6561 (39.1%)|0|0.9641|0|

### Holdout Distribution Summary
|model|dir|family|raw min|raw max|raw mean|raw std|raw uniq|raw plateau|raw >=.50|cal min|cal max|cal mean|cal std|cal uniq|cal plateau|cal >=.50|rank corr|inversions|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|bear|extra_trees|0.1931|0.6344|0.4228|0.0567|17069|1 (0.0%)|1135|0.0000|0.5000|0.2585|0.0137|12|16864 (98.8%)|30|0.1887|0|
|1384f70b|bear|hist_gradient_boosting|0.0403|0.7593|0.3223|0.1393|16720|3 (0.0%)|2100|0.0000|0.2646|0.2585|0.0155|16|8585 (50.3%)|0|0.8787|0|
|e03e236f|bear|logistic_regression|0.0003|0.8802|0.3665|0.1827|17069|1 (0.0%)|4044|0.0000|1.0000|0.2788|0.1008|126|6929 (40.6%)|335|0.9477|0|
|35780908|bull|extra_trees|0.1951|0.6193|0.4265|0.0496|17069|1 (0.0%)|779|0.0000|0.7000|0.3028|0.0276|14|8972 (52.6%)|80|0.9070|0|
|217dea02|bull|hist_gradient_boosting|0.1053|0.6751|0.3342|0.0822|16823|4 (0.0%)|488|0.1825|0.5000|0.3072|0.0310|36|4104 (24.0%)|67|0.9889|0|
|0d0332fb|bull|logistic_regression|0.1174|0.7998|0.5261|0.0847|17069|1 (0.0%)|10825|0.0000|0.3554|0.2959|0.0346|43|10120 (59.3%)|0|0.8865|0|

### Holdout Calibrated Percentiles
|model|p01|p05|p10|p25|p50|p75|p90|p95|p99|
|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|0.2508|0.2588|0.2588|0.2588|0.2588|0.2588|0.2588|0.2588|0.2588|
|1384f70b|0.2297|0.2548|0.2548|0.2548|0.2646|0.2646|0.2646|0.2646|0.2646|
|e03e236f|0.1814|0.1814|0.2575|0.2575|0.2613|0.2613|0.3064|0.3064|1.0000|
|35780908|0.2932|0.2932|0.2932|0.3010|0.3010|0.3053|0.3053|0.3053|0.3053|
|217dea02|0.1875|0.2687|0.2695|0.2917|0.3247|0.3295|0.3302|0.3302|0.3302|
|0d0332fb|0.1970|0.2450|0.2450|0.2755|0.3111|0.3111|0.3177|0.3203|0.3554|

Calibration is monotonic for all six learned heads: sampled rank inversions were zero. Ranking is therefore preserved except for ties introduced by isotonic plateaus. The practical damage is not non-monotonicity; it is compression and repeated-value plateaus, plus sparse extreme outputs in selected heads.

## 3. Raw Versus Calibrated Quality
|model|metric|raw|calibrated|cal-raw|result|
|---|---|---|---|---|---|
|8ff714ce|brier|0.2152|0.1915|-0.0236|better|
|8ff714ce|log_loss|0.6220|0.5730|-0.0490|better|
|8ff714ce|roc_auc|0.5873|0.5039|-0.0834|worse|
|8ff714ce|pr_auc|0.3169|0.2610|-0.0559|worse|
|8ff714ce|ece|0.1642|0.0408|-0.1234|better|
|8ff714ce|mce|0.1890|0.1427|-0.0463|better|
|8ff714ce|brier_skill|-0.1222|0.0011|0.1234|better|
|8ff714ce|precision_050|0.3463|0.6000|0.2537|better|
|8ff714ce|recall_050|0.0890|0.0041|-0.0850|worse|
|8ff714ce|specificity_050|0.9414|0.9991|0.0577|better|
|1384f70b|brier|0.1917|0.1910|-0.0008|better|
|1384f70b|log_loss|0.5680|0.5787|0.0106|worse|
|1384f70b|roc_auc|0.6276|0.5968|-0.0308|worse|
|1384f70b|pr_auc|0.3514|0.3067|-0.0447|worse|
|1384f70b|ece|0.0645|0.0708|0.0063|worse|
|1384f70b|mce|0.1888|0.1405|-0.0483|better|
|1384f70b|brier_skill|-0.0000|0.0040|0.0040|better|
|1384f70b|precision_050|0.3867|NA|NA|NA|
|1384f70b|recall_050|0.1840|0.0000|-0.1840|worse|
|1384f70b|specificity_050|0.8982|1.0000|0.1018|better|
|e03e236f|brier|0.2398|0.2010|-0.0389|better|
|e03e236f|log_loss|0.7280|0.9270|0.1990|worse|
|e03e236f|roc_auc|0.4896|0.4919|0.0022|better|
|e03e236f|pr_auc|0.2614|0.2581|-0.0033|worse|
|e03e236f|ece|0.1799|0.0742|-0.1057|better|
|e03e236f|mce|0.4393|0.1990|-0.2403|better|
|e03e236f|brier_skill|-0.2508|-0.0481|0.2026|better|
|e03e236f|precision_050|0.2451|0.3522|0.1072|better|
|e03e236f|recall_050|0.2245|0.0267|-0.1978|worse|
|e03e236f|specificity_050|0.7588|0.9829|0.2241|better|
|35780908|brier|0.2247|0.2074|-0.0174|better|
|35780908|log_loss|0.6418|0.6052|-0.0366|better|
|35780908|roc_auc|0.5302|0.5240|-0.0062|worse|
|35780908|pr_auc|0.3215|0.3043|-0.0172|worse|
|35780908|ece|0.1337|0.0306|-0.1031|better|
|35780908|mce|0.1788|0.0903|-0.0884|better|
|35780908|brier_skill|-0.0853|-0.0014|0.0839|better|
|35780908|precision_050|0.4005|0.4000|-0.0005|worse|
|35780908|recall_050|0.0624|0.0064|-0.0560|worse|
|35780908|specificity_050|0.9613|0.9960|0.0347|better|
|217dea02|brier|0.2126|0.2069|-0.0058|better|
|217dea02|log_loss|0.6165|0.6040|-0.0125|better|
|217dea02|roc_auc|0.5224|0.5223|-0.0001|worse|
|217dea02|pr_auc|0.3082|0.3042|-0.0040|worse|
|217dea02|ece|0.0613|0.0200|-0.0413|better|
|217dea02|mce|0.1644|0.0759|-0.0885|better|
|217dea02|brier_skill|-0.0269|0.0010|0.0279|better|
|217dea02|precision_050|0.3279|0.4030|0.0751|better|
|217dea02|recall_050|0.0320|0.0054|-0.0266|worse|
|217dea02|specificity_050|0.9728|0.9967|0.0239|better|
|0d0332fb|brier|0.2631|0.2060|-0.0571|better|
|0d0332fb|log_loss|0.7203|0.6017|-0.1186|better|
|0d0332fb|roc_auc|0.5427|0.5371|-0.0056|worse|
|0d0332fb|pr_auc|0.3176|0.3106|-0.0069|worse|
|0d0332fb|ece|0.2333|0.0192|-0.2141|better|
|0d0332fb|mce|0.3345|0.0497|-0.2849|better|
|0d0332fb|brier_skill|-0.2706|0.0051|0.2757|better|
|0d0332fb|precision_050|0.3125|NA|NA|NA|
|0d0332fb|recall_050|0.6769|0.0000|-0.6769|worse|
|0d0332fb|specificity_050|0.3835|1.0000|0.6165|better|

Observed pattern: raw discrimination is weak for most heads before calibration. Isotonic calibration sometimes improves Brier slightly but does not create robust discrimination; in bear logistic and bull extra-trees it worsens holdout Brier skill. Calibration does not damage ranking by inversion, but it can collapse ranks into ties and create unstable threshold pass-through.

## 4. Calibrator Implementation Audit
|model|method|input|outside range|cal n|raw uniq|cal uniq|steps|min step|max step|support p=0|support p=1|steps <10|<25|<50|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|isotonic|classifier positive-class probability|clip|16800|16800|6|6|4|16584|11|0|1|4|4|
|1384f70b|isotonic|classifier positive-class probability|clip|16800|15715|5|5|21|9837|21|0|0|1|1|
|e03e236f|isotonic|classifier positive-class probability|clip|16800|16800|11|11|1|7226|1|4|2|3|4|
|35780908|isotonic|classifier positive-class probability|clip|16800|16800|9|9|3|7342|11|0|2|6|6|
|217dea02|isotonic|classifier positive-class probability|clip|16800|16343|20|20|3|2650|3|0|3|3|3|
|0d0332fb|isotonic|classifier positive-class probability|clip|16800|16800|15|15|16|6561|16|0|0|3|4|

Implementation findings: TBS calibration uses a separate `IsotonicRegression(out_of_bounds="clip")` per model, fitted only on the chronological calibration slice. It receives the TBS classifier positive-class probability as input. Bull and bear have separate calibrators, each model family has its own fitted calibrator, and the TBS head uses `target_before_stop_calibrator`, not the primary classifier calibrator. Holdout labels do not influence calibration. The calibration code predicts on unsorted calibration/holdout frames with aligned row order; no index/sorting mismatch was found.

For isotonic models, observations supporting each fitted output step are grouped by calibrated output value. Steps with support below 25 or 50 are a practical overfitting risk because a narrow raw-score interval can map to a policy-relevant probability with little evidence.

## 5. Calibration Stability
### Sequential Calibration-Slice Segments
|model|seg|start|end|rows|base|raw Brier|cal Brier|raw AUC|cal AUC|raw PR|cal PR|ECE|pred mean|pred std|>=.50|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|1|2022-05-13|2023-01-04|5600|0.2689|0.2177|0.1963|0.4500|0.5086|0.2437|0.2724|0.1012|0.2565|0.0184|3|
|8ff714ce|2|2023-01-04|2023-08-25|5600|0.2275|0.2168|0.1768|0.4592|0.4982|0.2079|0.2269|0.0598|0.2586|0.0035|0|
|8ff714ce|3|2023-08-25|2024-04-17|5600|0.2775|0.2334|0.2008|0.4594|0.5008|0.2565|0.2782|0.0861|0.2588|0.0034|1|
|1384f70b|1|2022-05-13|2023-01-04|5600|0.2689|0.2055|0.1963|0.5156|0.5262|0.2884|0.2808|0.0651|0.2547|0.0163|0|
|1384f70b|2|2023-01-04|2023-08-25|5600|0.2275|0.1894|0.1770|0.4585|0.4725|0.2011|0.2179|0.0781|0.2582|0.0063|0|
|1384f70b|3|2023-08-25|2024-04-17|5600|0.2775|0.2225|0.2007|0.4895|0.5155|0.2628|0.2840|0.0646|0.2610|0.0047|0|
|e03e236f|1|2022-05-13|2023-01-04|5600|0.2689|0.2268|0.1954|0.5156|0.5380|0.2888|0.2909|0.0901|0.2705|0.0266|4|
|e03e236f|2|2023-01-04|2023-08-25|5600|0.2275|0.2085|0.1768|0.4940|0.5253|0.2383|0.2404|0.1016|0.2653|0.0161|0|
|e03e236f|3|2023-08-25|2024-04-17|5600|0.2775|0.2301|0.1992|0.5550|0.5784|0.3102|0.3178|0.0702|0.2382|0.0356|0|
|35780908|1|2022-05-13|2023-01-04|5600|0.2809|0.2170|0.2026|0.4372|0.4634|0.2428|0.2667|0.0682|0.2957|0.0109|0|
|35780908|2|2023-01-04|2023-08-25|5600|0.2998|0.2246|0.2091|0.5408|0.5492|0.3328|0.3259|0.0397|0.3005|0.0235|10|
|35780908|3|2023-08-25|2024-04-17|5600|0.3171|0.2347|0.2167|0.4719|0.4845|0.2907|0.3107|0.0643|0.3016|0.0101|3|
|217dea02|1|2022-05-13|2023-01-04|5600|0.2809|0.2072|0.2017|0.5220|0.5262|0.2843|0.2901|0.0265|0.2828|0.0354|4|
|217dea02|2|2023-01-04|2023-08-25|5600|0.2998|0.2093|0.2084|0.5439|0.5467|0.3418|0.3314|0.0252|0.2955|0.0279|0|
|217dea02|3|2023-08-25|2024-04-17|5600|0.3171|0.2203|0.2160|0.5214|0.5295|0.3224|0.3329|0.0566|0.3196|0.0155|0|
|0d0332fb|1|2022-05-13|2023-01-04|5600|0.2809|0.2331|0.2007|0.5222|0.5430|0.2814|0.3014|0.0709|0.2658|0.0472|0|
|0d0332fb|2|2023-01-04|2023-08-25|5600|0.2998|0.2900|0.2065|0.5799|0.5787|0.3657|0.3529|0.0988|0.3119|0.0332|0|
|0d0332fb|3|2023-08-25|2024-04-17|5600|0.3171|0.3168|0.2159|0.5133|0.5260|0.3076|0.3268|0.0545|0.3202|0.0324|0|

### Holdout Stability by Product Class
|model|product class|rows|base|raw Brier|cal Brier|raw AUC|cal AUC|cal ECE|cal mean|cal std|>=.50|
|---|---|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|inverse_etf|3908|0.2454|0.2126|0.1844|0.5454|0.5114|0.0583|0.2585|0.0249|24|
|8ff714ce|leveraged_etf|1959|0.2787|0.2138|0.2012|0.6016|0.5056|0.0871|0.2580|0.0092|0|
|8ff714ce|ordinary_etf|7302|0.2634|0.2162|0.1941|0.5996|0.5012|0.0693|0.2585|0.0057|1|
|8ff714ce|ordinary_stock|3900|0.2528|0.2164|0.1889|0.5909|0.5005|0.0653|0.2589|0.0100|5|
|1384f70b|inverse_etf|3908|0.2454|0.1845|0.1853|0.5763|0.5531|0.0946|0.2565|0.0136|0|
|1384f70b|leveraged_etf|1959|0.2787|0.1940|0.1999|0.6829|0.6413|0.1125|0.2595|0.0166|0|
|1384f70b|ordinary_etf|7302|0.2634|0.1918|0.1931|0.6472|0.6071|0.0758|0.2588|0.0170|0|
|1384f70b|ordinary_stock|3900|0.2528|0.1976|0.1882|0.6010|0.5841|0.0679|0.2596|0.0134|0|
|e03e236f|inverse_etf|3908|0.2454|0.2274|0.1921|0.5521|0.5525|0.0760|0.2876|0.1240|120|
|e03e236f|leveraged_etf|1959|0.2787|0.2548|0.2138|0.4371|0.4456|0.1156|0.2750|0.0938|31|
|e03e236f|ordinary_etf|7302|0.2634|0.2396|0.2026|0.4975|0.4965|0.0685|0.2782|0.0962|132|
|e03e236f|ordinary_stock|3900|0.2528|0.2450|0.2003|0.4419|0.4475|0.0789|0.2731|0.0847|52|
|35780908|inverse_etf|3908|0.2715|0.2106|0.1978|0.6395|0.6172|0.0751|0.3002|0.0108|1|
|35780908|leveraged_etf|1959|0.2976|0.2311|0.2097|0.4611|0.4804|0.0751|0.3028|0.0255|8|
|35780908|ordinary_etf|7302|0.2931|0.2273|0.2079|0.5099|0.5056|0.0370|0.3039|0.0331|51|
|35780908|ordinary_stock|3900|0.3113|0.2309|0.2148|0.4890|0.4875|0.0654|0.3033|0.0287|20|
|217dea02|inverse_etf|3908|0.2715|0.2005|0.1955|0.6263|0.6204|0.0766|0.3169|0.0373|61|
|217dea02|leveraged_etf|1959|0.2976|0.2186|0.2104|0.4769|0.4782|0.0547|0.3005|0.0316|3|
|217dea02|ordinary_etf|7302|0.2931|0.2130|0.2075|0.5054|0.5067|0.0205|0.3042|0.0274|3|
|217dea02|ordinary_stock|3900|0.3113|0.2211|0.2154|0.4899|0.4914|0.0319|0.3063|0.0275|0|
|0d0332fb|inverse_etf|3908|0.2715|0.2318|0.1934|0.6048|0.5923|0.0586|0.2741|0.0468|0|
|0d0332fb|leveraged_etf|1959|0.2976|0.2851|0.2100|0.5212|0.5060|0.0761|0.3072|0.0272|0|
|0d0332fb|ordinary_etf|7302|0.2931|0.2643|0.2068|0.5469|0.5370|0.0276|0.2992|0.0277|0|
|0d0332fb|ordinary_stock|3900|0.3113|0.2813|0.2152|0.4851|0.4928|0.0617|0.3056|0.0244|0|

Calibration is not stable enough to support final performance claims. Several segment/product-class tables show policy-threshold pass-through dominated by inverse/leveraged products or one segment. This is a stability and governance concern, not a proven implementation defect.

## 6. Class-Imbalance Diagnosis
|direction|split|rows|positives|positive rate|
|---|---|---|---|---|
|bull|training|51157|15116|0.2955|
|bull|calibration|16940|5064|0.2989|
|bull|holdout|17290|5063|0.2928|
|bear|training|51157|12944|0.2530|
|bear|calibration|16940|4362|0.2575|
|bear|holdout|17290|4465|0.2582|

|model|group type|group|rows|TBS positive rate|
|---|---|---|---|---|
|8ff714ce|instrument_class|ordinary_etf|7302|0.2634|
|8ff714ce|instrument_class|inverse_etf|3908|0.2454|
|8ff714ce|instrument_class|ordinary_stock|3900|0.2528|
|8ff714ce|instrument_class|leveraged_etf|1959|0.2787|
|8ff714ce|inverse_or_leveraged|ordinary|11202|0.2597|
|8ff714ce|inverse_or_leveraged|inverse_or_leveraged|5867|0.2565|
|8ff714ce|market_regime_label|uptrend_low_vol|7706|0.2863|
|8ff714ce|market_regime_label|uptrend_high_vol|6083|0.2315|
|8ff714ce|market_regime_label|downtrend_high_vol|3070|0.2303|
|8ff714ce|market_regime_label|mixed|210|0.4429|
|1384f70b|instrument_class|ordinary_etf|7302|0.2634|
|1384f70b|instrument_class|inverse_etf|3908|0.2454|
|1384f70b|instrument_class|ordinary_stock|3900|0.2528|
|1384f70b|instrument_class|leveraged_etf|1959|0.2787|
|1384f70b|inverse_or_leveraged|ordinary|11202|0.2597|
|1384f70b|inverse_or_leveraged|inverse_or_leveraged|5867|0.2565|
|1384f70b|market_regime_label|uptrend_low_vol|7706|0.2863|
|1384f70b|market_regime_label|uptrend_high_vol|6083|0.2315|
|1384f70b|market_regime_label|downtrend_high_vol|3070|0.2303|
|1384f70b|market_regime_label|mixed|210|0.4429|
|e03e236f|instrument_class|ordinary_etf|7302|0.2634|
|e03e236f|instrument_class|inverse_etf|3908|0.2454|
|e03e236f|instrument_class|ordinary_stock|3900|0.2528|
|e03e236f|instrument_class|leveraged_etf|1959|0.2787|
|e03e236f|inverse_or_leveraged|ordinary|11202|0.2597|
|e03e236f|inverse_or_leveraged|inverse_or_leveraged|5867|0.2565|
|e03e236f|market_regime_label|uptrend_low_vol|7706|0.2863|
|e03e236f|market_regime_label|uptrend_high_vol|6083|0.2315|
|e03e236f|market_regime_label|downtrend_high_vol|3070|0.2303|
|e03e236f|market_regime_label|mixed|210|0.4429|
|35780908|instrument_class|ordinary_etf|7302|0.2931|
|35780908|instrument_class|inverse_etf|3908|0.2715|
|35780908|instrument_class|ordinary_stock|3900|0.3113|
|35780908|instrument_class|leveraged_etf|1959|0.2976|
|35780908|inverse_or_leveraged|ordinary|11202|0.2994|
|35780908|inverse_or_leveraged|inverse_or_leveraged|5867|0.2802|
|35780908|market_regime_label|uptrend_low_vol|7706|0.3013|
|35780908|market_regime_label|uptrend_high_vol|6083|0.2949|
|35780908|market_regime_label|downtrend_high_vol|3070|0.2749|
|35780908|market_regime_label|mixed|210|0.1810|
|217dea02|instrument_class|ordinary_etf|7302|0.2931|
|217dea02|instrument_class|inverse_etf|3908|0.2715|
|217dea02|instrument_class|ordinary_stock|3900|0.3113|
|217dea02|instrument_class|leveraged_etf|1959|0.2976|
|217dea02|inverse_or_leveraged|ordinary|11202|0.2994|
|217dea02|inverse_or_leveraged|inverse_or_leveraged|5867|0.2802|
|217dea02|market_regime_label|uptrend_low_vol|7706|0.3013|
|217dea02|market_regime_label|uptrend_high_vol|6083|0.2949|
|217dea02|market_regime_label|downtrend_high_vol|3070|0.2749|
|217dea02|market_regime_label|mixed|210|0.1810|
|0d0332fb|instrument_class|ordinary_etf|7302|0.2931|
|0d0332fb|instrument_class|inverse_etf|3908|0.2715|
|0d0332fb|instrument_class|ordinary_stock|3900|0.3113|
|0d0332fb|instrument_class|leveraged_etf|1959|0.2976|
|0d0332fb|inverse_or_leveraged|ordinary|11202|0.2994|
|0d0332fb|inverse_or_leveraged|inverse_or_leveraged|5867|0.2802|
|0d0332fb|market_regime_label|uptrend_low_vol|7706|0.3013|
|0d0332fb|market_regime_label|uptrend_high_vol|6083|0.2949|
|0d0332fb|market_regime_label|downtrend_high_vol|3070|0.2749|
|0d0332fb|market_regime_label|mixed|210|0.1810|

Model fitting uses `class_weight="balanced"` for logistic regression and extra trees; histogram gradient boosting has no class weights in this implementation. No sample weights, oversampling, undersampling, or balanced subsampling path was found. Imbalance contributes to probability compression because base rates sit near 0.26 for bear and 0.29 for bull, but this is not extreme enough to explain the failures alone.

## 7. Fixed 0.50 Policy Diagnosis
The `0.50` TBS policy is both a code default and explicitly user-governed in this task family: the user repeatedly instructed not to change it. It is not learned from calibration. It aligns with ordinary binary probability convention and can be argued from a 2 ATR target / 1 ATR stop payoff as a conservative target-before-stop confidence filter, but this diagnosis did not find a calibration-data proof that `0.50` is optimal. No threshold is recommended from holdout results.
### Holdout Threshold Grid: 8ff714ce bear extra_trees
|thr|n|rate|obs TBS|precision|recall|mean ret|med ret|mean MFE|mean MAE|sym conc|sector conc|year conc|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0.30|31|0.2%|0.6129|0.6129|0.0043|0.2183|0.1384|0.3900|-0.0697|0.1290|0.2581|1.0000|
|0.35|31|0.2%|0.6129|0.6129|0.0043|0.2183|0.1384|0.3900|-0.0697|0.1290|0.2581|1.0000|
|0.40|30|0.2%|0.6000|0.6000|0.0041|0.2227|0.1583|0.3994|-0.0718|0.1333|0.2667|1.0000|
|0.45|30|0.2%|0.6000|0.6000|0.0041|0.2227|0.1583|0.3994|-0.0718|0.1333|0.2667|1.0000|
|0.50|30|0.2%|0.6000|0.6000|0.0041|0.2227|0.1583|0.3994|-0.0718|0.1333|0.2667|1.0000|
|0.55|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.60|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.65|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.70|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|

### Holdout Threshold Grid: 1384f70b bear hist_gradient_boosting
|thr|n|rate|obs TBS|precision|recall|mean ret|med ret|mean MFE|mean MAE|sym conc|sector conc|year conc|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0.30|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.35|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.40|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.45|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.50|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.55|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.60|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.65|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.70|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|

### Holdout Threshold Grid: e03e236f bear logistic_regression
|thr|n|rate|obs TBS|precision|recall|mean ret|med ret|mean MFE|mean MAE|sym conc|sector conc|year conc|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0.30|3925|23.0%|0.2428|0.2428|0.2159|-0.0017|-0.0042|0.0497|-0.0488|0.0377|0.1009|0.5279|
|0.35|359|2.1%|0.3565|0.3565|0.0290|0.0180|0.0054|0.0803|-0.0495|0.0641|0.1532|0.7354|
|0.40|353|2.1%|0.3541|0.3541|0.0283|0.0176|0.0036|0.0806|-0.0501|0.0652|0.1530|0.7365|
|0.45|346|2.0%|0.3555|0.3555|0.0279|0.0180|0.0039|0.0815|-0.0503|0.0665|0.1561|0.7370|
|0.50|335|2.0%|0.3522|0.3522|0.0267|0.0179|0.0042|0.0815|-0.0508|0.0657|0.1552|0.7373|
|0.55|328|1.9%|0.3537|0.3537|0.0263|0.0179|0.0039|0.0825|-0.0514|0.0671|0.1524|0.7439|
|0.60|320|1.9%|0.3625|0.3625|0.0263|0.0185|0.0043|0.0840|-0.0517|0.0656|0.1531|0.7375|
|0.65|315|1.8%|0.3683|0.3683|0.0263|0.0185|0.0036|0.0848|-0.0520|0.0667|0.1556|0.7365|
|0.70|310|1.8%|0.3710|0.3710|0.0261|0.0177|0.0035|0.0847|-0.0521|0.0645|0.1548|0.7419|

### Holdout Threshold Grid: 35780908 bull extra_trees
|thr|n|rate|obs TBS|precision|recall|mean ret|med ret|mean MFE|mean MAE|sym conc|sector conc|year conc|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0.30|14204|83.2%|0.2996|0.2996|0.8515|0.0053|0.0034|0.0542|-0.0480|0.0330|0.0869|0.4770|
|0.35|80|0.5%|0.4000|0.4000|0.0064|0.0395|0.0258|0.0901|-0.0585|0.0500|0.1250|0.8625|
|0.40|80|0.5%|0.4000|0.4000|0.0064|0.0395|0.0258|0.0901|-0.0585|0.0500|0.1250|0.8625|
|0.45|80|0.5%|0.4000|0.4000|0.0064|0.0395|0.0258|0.0901|-0.0585|0.0500|0.1250|0.8625|
|0.50|80|0.5%|0.4000|0.4000|0.0064|0.0395|0.0258|0.0901|-0.0585|0.0500|0.1250|0.8625|
|0.55|80|0.5%|0.4000|0.4000|0.0064|0.0395|0.0258|0.0901|-0.0585|0.0500|0.1250|0.8625|
|0.60|80|0.5%|0.4000|0.4000|0.0064|0.0395|0.0258|0.0901|-0.0585|0.0500|0.1250|0.8625|
|0.65|79|0.5%|0.3924|0.3924|0.0062|0.0392|0.0254|0.0905|-0.0591|0.0506|0.1266|0.8734|
|0.70|71|0.4%|0.3662|0.3662|0.0052|0.0379|0.0216|0.0906|-0.0613|0.0563|0.1268|0.8873|

### Holdout Threshold Grid: 217dea02 bull hist_gradient_boosting
|thr|n|rate|obs TBS|precision|recall|mean ret|med ret|mean MFE|mean MAE|sym conc|sector conc|year conc|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0.30|8838|51.8%|0.3107|0.3107|0.5494|0.0034|0.0009|0.0579|-0.0508|0.0472|0.1100|0.4079|
|0.35|72|0.4%|0.3750|0.3750|0.0054|-0.0108|0.0015|0.0399|-0.0382|0.3194|0.6944|0.5139|
|0.40|70|0.4%|0.3857|0.3857|0.0054|-0.0107|0.0017|0.0410|-0.0387|0.3143|0.6857|0.5286|
|0.45|68|0.4%|0.3971|0.3971|0.0054|-0.0093|0.0017|0.0420|-0.0369|0.3235|0.6912|0.5294|
|0.50|67|0.4%|0.4030|0.4030|0.0054|-0.0093|0.0017|0.0426|-0.0372|0.3134|0.6866|0.5373|
|0.55|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.60|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.65|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.70|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|

### Holdout Threshold Grid: 0d0332fb bull logistic_regression
|thr|n|rate|obs TBS|precision|recall|mean ret|med ret|mean MFE|mean MAE|sym conc|sector conc|year conc|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0.30|12604|73.8%|0.3086|0.3086|0.7783|0.0062|0.0042|0.0526|-0.0469|0.0357|0.1007|0.4723|
|0.35|438|2.6%|0.3196|0.3196|0.0280|-0.0098|-0.0067|0.0676|-0.0869|0.1233|0.1575|0.8379|
|0.40|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.45|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.50|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.55|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.60|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.65|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|
|0.70|0|0.0%|NA|NA|0.0000|NA|NA|NA|NA|NA|NA|NA|

## 8. Calibration-Only Decision Evidence
The table below uses calibration data only. Expected payoff is diagnostic ATR-unit payoff `2 * target_hit_probability - 1 * stop_hit_probability`; transaction-cost-adjusted utility subtracts the configured 5 bps round-trip cost as a small proxy. It is not an implemented decision rule.
### Calibration Utility Grid: 8ff714ce bear extra_trees
|thr|n|target prob|stop prob|unresolved|payoff ATR|cost adj|95% target CI|sym conc|sector conc|
|---|---|---|---|---|---|---|---|---|---|
|0.30|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.35|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.40|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.45|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.50|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.55|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.60|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.65|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.70|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|

### Calibration Utility Grid: 1384f70b bear hist_gradient_boosting
|thr|n|target prob|stop prob|unresolved|payoff ATR|cost adj|95% target CI|sym conc|sector conc|
|---|---|---|---|---|---|---|---|---|---|
|0.30|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.35|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.40|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.45|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.50|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.55|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.60|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.65|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.70|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|

### Calibration Utility Grid: e03e236f bear logistic_regression
|thr|n|target prob|stop prob|unresolved|payoff ATR|cost adj|95% target CI|sym conc|sector conc|
|---|---|---|---|---|---|---|---|---|---|
|0.30|1865|0.3078|0.5995|0.0928|0.0161|0.0156|0.2872..0.3291|0.0713|0.1796|
|0.35|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|
|0.40|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|
|0.45|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|
|0.50|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|
|0.55|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|
|0.60|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|
|0.65|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|
|0.70|4|1.0000|0.0000|0.0000|2.0000|1.9995|0.5101..1.0000|0.2500|0.5000|

### Calibration Utility Grid: 35780908 bull extra_trees
|thr|n|target prob|stop prob|unresolved|payoff ATR|cost adj|95% target CI|sym conc|sector conc|
|---|---|---|---|---|---|---|---|---|---|
|0.30|11433|0.3030|0.5910|0.1060|0.0150|0.0145|0.2946..0.3115|0.0385|0.0870|
|0.35|13|0.6923|0.3077|0.0000|1.0769|1.0764|0.4237..0.8732|0.1538|0.1538|
|0.40|13|0.6923|0.3077|0.0000|1.0769|1.0764|0.4237..0.8732|0.1538|0.1538|
|0.45|13|0.6923|0.3077|0.0000|1.0769|1.0764|0.4237..0.8732|0.1538|0.1538|
|0.50|13|0.6923|0.3077|0.0000|1.0769|1.0764|0.4237..0.8732|0.1538|0.1538|
|0.55|13|0.6923|0.3077|0.0000|1.0769|1.0764|0.4237..0.8732|0.1538|0.1538|
|0.60|13|0.6923|0.3077|0.0000|1.0769|1.0764|0.4237..0.8732|0.1538|0.1538|
|0.65|13|0.6923|0.3077|0.0000|1.0769|1.0764|0.4237..0.8732|0.1538|0.1538|
|0.70|10|0.7000|0.3000|0.0000|1.1000|1.0995|0.3968..0.8922|0.2000|0.2000|

### Calibration Utility Grid: 217dea02 bull hist_gradient_boosting
|thr|n|target prob|stop prob|unresolved|payoff ATR|cost adj|95% target CI|sym conc|sector conc|
|---|---|---|---|---|---|---|---|---|---|
|0.30|6859|0.3279|0.5784|0.0937|0.0774|0.0769|0.3169..0.3391|0.0394|0.0853|
|0.35|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.40|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.45|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.50|4|0.5000|0.5000|0.0000|0.5000|0.4995|0.1500..0.8500|0.2500|0.2500|
|0.55|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.60|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.65|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.70|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|

### Calibration Utility Grid: 0d0332fb bull logistic_regression
|thr|n|target prob|stop prob|unresolved|payoff ATR|cost adj|95% target CI|sym conc|sector conc|
|---|---|---|---|---|---|---|---|---|---|
|0.30|12171|0.3230|0.5788|0.0982|0.0671|0.0666|0.3147..0.3313|0.0373|0.0977|
|0.35|2676|0.3554|0.5680|0.0766|0.1428|0.1423|0.3375..0.3737|0.0740|0.1274|
|0.40|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.45|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.50|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.55|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.60|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.65|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|
|0.70|0|NA|NA|NA|NA|NA|NA..NA|NA|NA|

Calibration-only evidence does not cleanly support replacing the governed fixed threshold. Some heads have no usable observations near higher thresholds; others have high concentration or sparse support. The evidence is more consistent with no reliable threshold yet because the model/calibration signal is unstable.

## 9. Feature-Screen Stability
|direction|selected overlap vs full|Jaccard vs full|family Jaccard|top20 Jaccard|mean MI CV|selected every|selected once|classification|
|---|---|---|---|---|---|---|---|---|
|bear|43;47;50|0.5584;0.6438;0.7143|0.9167;1.0000;1.0000|0.4286;0.4815;0.5385|0.0823|37|21|moderately unstable|
|bull|46;48;54|0.6216;0.6667;0.8182|1.0000;1.0000;1.0000|0.6667;0.6000;0.6000|0.0700|38|16|moderately unstable|

- `bear` selected in every resample: atr_20, breadth_dispersion_20, breadth_skew_20, breadth_up_volume_pct, down_volume_proxy_20, downside_vol_20, inverse_confirmation_qqq_qid_63, inverse_confirmation_qqq_sqqq_63, inverse_confirmation_qqq_tqqq_63, inverse_confirmation_spy_sds_63, iwm_return_20, market_regime_trend_score, market_regime_volatility_score, qqq_return_20, realized_vol_63, relationship_corr_iwm_tza_63, relationship_corr_spy_spxu_63, relationship_corr_spy_upro_63, relationship_divergence_iwm_rwm_5, relationship_divergence_spy_sh_5; plus 17 more
- `bear` selected only once: High, Low, distance_prior_high_126, distance_prior_low_126, inverse_confirmation_spy_sh_63, inverse_confirmation_xlk_soxl_63, momentum_20_percentile_252, relationship_divergence_iwm_tna_5, relationship_divergence_qqq_sqqq_5, rolling_corr_vs_spy_63, rsi_14_percentile_252, rsi_20, rsi_26_percentile_252, rsi_44, rsi_45, rsi_45_percentile_252, rsi_46_percentile_252, rsi_48, rsi_50_percentile_252, rsi_9_accel; plus 1 more
- `bull` selected in every resample: breadth_dispersion_20, breadth_skew_20, breadth_up_volume_pct, dia_return_5, down_volume_proxy_20, downside_vol_20, inverse_confirmation_iwm_rwm_63, inverse_confirmation_iwm_tza_63, inverse_confirmation_qqq_sqqq_63, iwm_return_20, iwm_return_5, market_regime_trend_score, market_regime_volatility_score, qqq_return_20, range_position_252, realized_vol_63, relationship_corr_iwm_tna_63, relationship_corr_qqq_qid_63, relationship_corr_spy_sh_63, relationship_corr_spy_upro_63; plus 18 more
- `bull` selected only once: atr_pct_14, inverse_confirmation_spy_spxu_63, relationship_corr_qqq_tqqq_63, relationship_corr_spy_sds_63, relationship_divergence_spy_upro_5, relationship_lead_lag_qqq_tqqq_5, relationship_lead_lag_xlk_soxs_5, relationship_mutual_info_xlk_soxs_63, rolling_beta_vs_qqq_63, rolling_corr_vs_spy_63, rsi_12_percentile_252, rsi_30, rsi_32_percentile_252, rsi_3_percentile_252, rsi_44_accel, rsi_9

Screen stability is classified from chronological training-only resamples, with no artifact creation. A moderately or highly unstable screen means the target-specific correction is working mechanically but the estimated feature ranking is sample-sensitive.

## 10. Holdout Status
The current holdout is a development holdout, not a pristine final holdout. It has been repeatedly inspected during feature-screening and calibration diagnosis. It can support implementation audits, failure triage, and governance observations. It cannot support a final claim of trading edge, final model quality, or threshold optimality. This task did not create a new split or retrain.

## 11. Root-Cause Table
|model|dir|family|implementation defect|raw signal|calibrator collapse|overfit|temporal instability|class imbalance|0.50 mismatch|screen stability|family limit|signal scarcity|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|8ff714ce|bear|extra_trees|No: separate TBS model/calibrator/manifest; monotonic isotonic; holdout labels not used for fit.|Mixed|Yes|Yes|Yes|Contributory: base rate near 0.26 bear / 0.29 bull, not severe enough alone.|Yes|moderately unstable|Contributory: families produce materially different calibration/ranking failure modes.|Plausible: out-of-sample TBS skill remains near zero for most heads.|
|1384f70b|bear|hist_gradient_boosting|No: separate TBS model/calibrator/manifest; monotonic isotonic; holdout labels not used for fit.|Mixed|Yes|Yes|Yes|Contributory: base rate near 0.26 bear / 0.29 bull, not severe enough alone.|Yes|moderately unstable|Contributory: families produce materially different calibration/ranking failure modes.|Plausible: out-of-sample TBS skill remains near zero for most heads.|
|e03e236f|bear|logistic_regression|No: separate TBS model/calibrator/manifest; monotonic isotonic; holdout labels not used for fit.|Mixed|No/Mixed|Yes|Yes|Contributory: base rate near 0.26 bear / 0.29 bull, not severe enough alone.|Mixed|moderately unstable|Contributory: families produce materially different calibration/ranking failure modes.|Plausible: out-of-sample TBS skill remains near zero for most heads.|
|35780908|bull|extra_trees|No: separate TBS model/calibrator/manifest; monotonic isotonic; holdout labels not used for fit.|Mixed|Yes|Yes|Yes|Contributory: base rate near 0.26 bear / 0.29 bull, not severe enough alone.|Yes|moderately unstable|Contributory: families produce materially different calibration/ranking failure modes.|Plausible: out-of-sample TBS skill remains near zero for most heads.|
|217dea02|bull|hist_gradient_boosting|No: separate TBS model/calibrator/manifest; monotonic isotonic; holdout labels not used for fit.|Mixed|No/Mixed|Yes|No/Mixed|Contributory: base rate near 0.26 bear / 0.29 bull, not severe enough alone.|Yes|moderately unstable|Contributory: families produce materially different calibration/ranking failure modes.|Plausible: out-of-sample TBS skill remains near zero for most heads.|
|0d0332fb|bull|logistic_regression|No: separate TBS model/calibrator/manifest; monotonic isotonic; holdout labels not used for fit.|Mixed|Yes|Yes|No/Mixed|Contributory: base rate near 0.26 bear / 0.29 bull, not severe enough alone.|Yes|moderately unstable|Contributory: families produce materially different calibration/ranking failure modes.|Plausible: out-of-sample TBS skill remains near zero for most heads.|

Do not classify weak target-before-stop performance itself as a software bug. The measured implementation path is coherent; the remaining issue is evidence quality, calibration stability, and policy fit.

## Model-Level Conclusions
- `8ff714ce` `bear` `extra_trees`: raw ROC-AUC 0.5873, calibrated ROC-AUC 0.5039, raw/cal Brier skill -0.1222/0.0011, calibrated >=0.50 count 30, unique calibrated outputs 12, largest plateau 16864 (98.8%), isotonic steps <25 support 4. Root cause: Mixed; calibration collapse: Yes; 0.50 mismatch: Yes.
- `1384f70b` `bear` `hist_gradient_boosting`: raw ROC-AUC 0.6276, calibrated ROC-AUC 0.5968, raw/cal Brier skill -0.0000/0.0040, calibrated >=0.50 count 0, unique calibrated outputs 16, largest plateau 8585 (50.3%), isotonic steps <25 support 1. Root cause: Mixed; calibration collapse: Yes; 0.50 mismatch: Yes.
- `e03e236f` `bear` `logistic_regression`: raw ROC-AUC 0.4896, calibrated ROC-AUC 0.4919, raw/cal Brier skill -0.2508/-0.0481, calibrated >=0.50 count 335, unique calibrated outputs 126, largest plateau 6929 (40.6%), isotonic steps <25 support 3. Root cause: Mixed; calibration collapse: No/Mixed; 0.50 mismatch: Mixed.
- `35780908` `bull` `extra_trees`: raw ROC-AUC 0.5302, calibrated ROC-AUC 0.5240, raw/cal Brier skill -0.0853/-0.0014, calibrated >=0.50 count 80, unique calibrated outputs 14, largest plateau 8972 (52.6%), isotonic steps <25 support 6. Root cause: Mixed; calibration collapse: Yes; 0.50 mismatch: Yes.
- `217dea02` `bull` `hist_gradient_boosting`: raw ROC-AUC 0.5224, calibrated ROC-AUC 0.5223, raw/cal Brier skill -0.0269/0.0010, calibrated >=0.50 count 67, unique calibrated outputs 36, largest plateau 4104 (24.0%), isotonic steps <25 support 3. Root cause: Mixed; calibration collapse: No/Mixed; 0.50 mismatch: Yes.
- `0d0332fb` `bull` `logistic_regression`: raw ROC-AUC 0.5427, calibrated ROC-AUC 0.5371, raw/cal Brier skill -0.2706/0.0051, calibrated >=0.50 count 0, unique calibrated outputs 43, largest plateau 10120 (59.3%), isotonic steps <25 support 3. Root cause: Mixed; calibration collapse: Yes; 0.50 mismatch: Yes.

## Smallest Engineering Correction
Add a read-only calibration audit export that persists raw target-before-stop scores, calibrated probabilities, isotonic step support, and calibration-slice threshold utility tables for each generated model. Do not change thresholds, calibration method, model families, or training behavior as part of that correction.
