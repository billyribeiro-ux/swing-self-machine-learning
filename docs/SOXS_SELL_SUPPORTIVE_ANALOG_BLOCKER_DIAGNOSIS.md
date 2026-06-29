# SOXS SELL Supportive-Analog Blocker Diagnosis

Date: 2026-06-29

Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Development branch: `feat/product-class-specialist-challengers-v1`

Current commit reviewed: `278113a5355b0bcdef1c8e2f0f1f8769a6706c73`

Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Operational frozen run: `3493ee8ac37bf96475c362e1`

Signal-discovery generation: `signal_discovery_20260628T193012+0000_cf2753a58c47`

This is a read-only research diagnosis. The only repository write made for this task is this markdown report. No source code, SQLite state, model artifact, scanner artifact, FMP data, discovery output, forward state, or operational repository state was modified.

## Decision

Classification: **B. ANALOG_CONCENTRATION_ARTIFACT**

Measured reason:

- The first four SOXS 10-day SELL rows have strong top-10 analog outcomes, but the top-10 set is 10/10 SOXS and 10/10 from 2026.
- Expanding from top 10 to top 25 downgrades the recomputed support label from `SUPPORTIVE` to `MIXED`: win rate falls from 100.00% to 88.00%, average forward return falls from 56.07% to 33.28%, and target-before-stop hit rate falls from 50.00% to 36.00%.
- Expanding to top 50 keeps positive directional outcomes but remains concentrated: 48/50 analogs are SOXS, all 50 are same product scope, and target-before-stop hit rate falls to 28.00%.
- The 10-day model target-before-stop probability, 26.13%, is close to same-symbol, same-scope, same-regime, and all-row historical base rates of roughly 25.62% to 27.90%. It is not materially contradicted by the top-50 analog TBS rate of 28.00%.
- The 5-day volatility-expansion row is weaker: probability is below threshold, top-10 target-before-stop hit rate is 0.00%, and top-50 target-before-stop hit rate is 10.00%.

Secondary finding: there is a target/stop timing mismatch worth future diagnosis. Many analogs have positive forward returns despite `stop before target`, which means directional gains often arrived after early adverse movement or after target/stop sequencing failed. That does not override the primary concentration finding.

Exactly one next task: **expand analog robustness testing for leveraged inverse SELL footprints**.

## Rows Diagnosed

All five rows are SOXS, `LEVERAGED_INVERSE`, as-of `2026-06-26`, model family `extra_trees`, edge status `RESEARCH ONLY`, candidate status `RESEARCH_ONLY`, and not live actionable because no promoted multi-angle signal model exists.

| hypothesis_id | signal_id | archetype | horizon | score | probability | TBS probability | expected return | expected MFE | expected MAE | OOD feature rate | primary blocker |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `breakdown_sell_10d` | `30a17bdcfb48c4413b7fb568` | Breakout / Breakdown | 10 | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | `target_before_stop_probability_below_threshold` |
| `trend_continuation_sell_10d` | `78bbd5e4a00f14f32b11239b` | Trend Continuation | 10 | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | `target_before_stop_probability_below_threshold` |
| `breadth_deterioration_sell_10d` | `cc71717a722068d82e6c52a9` | Breadth Thrust / Breadth Deterioration | 10 | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | `target_before_stop_probability_below_threshold` |
| `pullback_continuation_sell_10d` | `bde9ac857dcdaf20ecf8f1de` | Pullback Continuation | 10 | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | `target_before_stop_probability_below_threshold` |
| `volatility_expansion_sell_5d` | `4b658b49367e91231b9c4c83` | Volatility Expansion | 5 | 0.539657 | 0.448905 | 0.146034 | 0.066307 | 0.167116 | -0.101209 | 0.166667 | `probability_below_threshold` |

Gate policy order is OOD feature rate, direction probability, target-before-stop probability, expected return after costs, then score. Thresholds are OOD feature rate <= 0.20, probability >= 0.55, target-before-stop probability >= 0.50, expected return >= 0.001, and signal score >= 0.55.

The first four rows pass OOD and probability but fail the TBS threshold by 0.238745. The volatility-expansion row fails probability first by 0.101095; its TBS probability is also below the 0.50 threshold by 0.353966 but is not the primary blocker because of gate order.

## Analog Method Audited

The blocked-row analog function reads only existing signal-discovery artifacts and the latest local modeling parquet. For each target row it:

- Uses the row's hypothesis-selected feature set.
- Excludes `label_` columns from distance features. The audited five feature sets contain zero `label_` columns.
- Requires analog dates strictly before the target as-of date.
- Fits deterministic median imputation and standard-deviation scaling on the historical candidate pool before the target date.
- Prefers same product scope and labels any cross-scope fallback through `analog_pool`.
- Persists same-symbol, same-product-scope, same-archetype, and same-direction flags.

The first four 10-day rows use the same 48 selected features. The 5-day volatility row uses a related but not identical 48-feature set. Top TBS features and feature importances are not persisted in the current generation artifacts.

## Top-10 Analog Audit

The first four 10-day rows have the same top-10 analog set:

| rank | date | ticker | scope | regime | similarity | distance | forward return | MFE | MAE | TBS result |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | 2026-06-09 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.120977 | 7.266017 | 0.529412 | 0.896657 | -0.061654 | target before stop |
| 2 | 2026-06-11 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.120359 | 7.308452 | 0.181604 | 0.522796 | -0.027184 | stop before target |
| 3 | 2026-06-10 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.118892 | 7.411000 | 0.680441 | 0.854103 | 0.000000 | target before stop |
| 4 | 2026-06-08 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.114302 | 7.748771 | 0.299505 | 0.595745 | -0.261603 | stop before target |
| 5 | 2026-06-05 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.110560 | 8.044832 | 0.730303 | 0.735562 | -0.196906 | stop before target |
| 6 | 2026-05-21 | SOXS | LEVERAGED_INVERSE | uptrend_low_vol | 0.085659 | 10.674129 | 0.169591 | 0.659751 | -0.007444 | stop before target |
| 7 | 2026-05-19 | SOXS | LEVERAGED_INVERSE | uptrend_low_vol | 0.085191 | 10.738283 | 0.894094 | 0.929461 | -0.005348 | target before stop |
| 8 | 2026-05-20 | SOXS | LEVERAGED_INVERSE | uptrend_low_vol | 0.085141 | 10.745237 | 0.663462 | 0.794606 | -0.014806 | target before stop |
| 9 | 2026-05-18 | SOXS | LEVERAGED_INVERSE | uptrend_low_vol | 0.084050 | 10.897658 | 1.058027 | 1.066019 | -0.038844 | target before stop |
| 10 | 2026-05-15 | SOXS | LEVERAGED_INVERSE | uptrend_low_vol | 0.083373 | 10.994353 | 0.400958 | 0.504288 | -0.207769 | stop before target |

All 10 are same-symbol, same-scope, same-archetype, same-direction, and from 2026. Product class is `LEVERAGED_INVERSE` for every analog.

The 5-day volatility-expansion row has this top-10 set:

| rank | date | ticker | scope | regime | similarity | distance | forward return | MFE | MAE | TBS result |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | 2026-06-09 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.121576 | 7.225311 | 0.347732 | 0.595908 | -0.061654 | stop before target |
| 2 | 2026-06-11 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.120696 | 7.285266 | 0.395543 | 0.452174 | -0.027184 | stop before target |
| 3 | 2026-06-10 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.119652 | 7.357589 | 0.367713 | 0.560102 | 0.000000 | stop before target |
| 4 | 2026-06-08 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.114711 | 7.717587 | 0.329114 | 0.342711 | -0.261603 | stop before target |
| 5 | 2026-06-05 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.110426 | 8.055804 | 0.209746 | 0.257709 | -0.196906 | stop before target |
| 6 | 2026-06-16 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.105665 | 8.463916 | 0.022059 | 0.267477 | -0.065022 | stop before target |
| 7 | 2026-06-18 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.101935 | 8.810152 | -0.214623 | 0.012158 | -0.241458 | stop before target |
| 8 | 2026-06-12 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.099839 | 9.016076 | 0.233333 | 0.237082 | -0.124731 | stop before target |
| 9 | 2026-06-17 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.093347 | 9.712765 | 0.063361 | 0.173252 | -0.120729 | stop before target |
| 10 | 2026-06-15 | SOXS | LEVERAGED_INVERSE | uptrend_high_vol | 0.091995 | 9.870110 | -0.002475 | 0.224924 | -0.133333 | stop before target |

This row's top-10 set is also 10/10 same-symbol, same-scope, same-archetype, same-direction, and from 2026.

## Analog Expansion

The first four 10-day rows are identical on analog summaries:

| analog depth | win rate | avg forward return | median forward return | TBS hit rate | avg MFE | avg MAE | worst MAE | same-symbol | year concentration | support label |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 10 | 100.00% | 56.07% | 59.64% | 50.00% | 75.59% | -8.22% | -26.16% | 10/10 | 2026: 10/10 | SUPPORTIVE |
| 25 | 88.00% | 33.28% | 28.10% | 36.00% | 47.77% | -10.06% | -28.57% | 25/25 | 2026: 13/25 | MIXED |
| 50 | 76.00% | 22.11% | 17.56% | 28.00% | 34.43% | -10.98% | -29.97% | 48/50 | 2026: 17/50 | MIXED |

Top-50 ticker mix is SOXS 48 and TZA 2. Top-50 regime mix is `uptrend_high_vol` 30, `uptrend_low_vol` 16, and `downtrend_high_vol` 4.

The 5-day volatility-expansion row:

| analog depth | win rate | avg forward return | median forward return | TBS hit rate | avg MFE | avg MAE | worst MAE | same-symbol | year concentration | support label |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 10 | 80.00% | 17.52% | 22.15% | 0.00% | 31.23% | -12.33% | -26.16% | 10/10 | 2026: 10/10 | MIXED |
| 25 | 80.00% | 19.08% | 15.69% | 12.00% | 27.99% | -9.51% | -26.16% | 25/25 | 2026: 17/25 | MIXED |
| 50 | 72.00% | 12.78% | 9.94% | 10.00% | 20.80% | -8.97% | -26.16% | 49/50 | 2026: 23/50 | MIXED |

Top-50 ticker mix is SOXS 49 and TZA 1. Top-50 regime mix is `uptrend_high_vol` 31, `uptrend_low_vol` 16, and `downtrend_high_vol` 3.

## Target-Before-Stop Audit

The generation stores the calibrated candidate probability but does not persist the raw TBS probability, the fitted TBS calibrator object, calibration plateau diagnostics, calibration confidence, or TBS feature importances in the signal-discovery artifacts.

Source inspection shows the multi-angle discovery layer fits a target-before-stop classifier on the training split and applies an isotonic calibrator when calibration rows are sufficient; otherwise it uses raw probabilities. The exact raw-versus-calibrated decomposition for these rows is not available from persisted artifacts.

For the four 10-day rows:

- TBS probability: 0.261255.
- Threshold: 0.500000.
- Distance below threshold: 0.238745.
- Same-symbol SOXS historical TBS base rate before 2026-06-26: 0.278996 from 2,509 rows.
- Same-scope `LEVERAGED_INVERSE` base rate: 0.267703 from 15,054 rows.
- Same-regime base rate: 0.256779 from 59,156 rows.
- All pre-target rows for the same 10-day bear TBS label: 0.256186 from 89,798 rows.
- Analog TBS hit rate: 50.00% at top 10, 36.00% at top 25, 28.00% at top 50.

Blocker classification for the 10-day rows: **analog overconfidence plus concentration artifact, not confirmed model underconfidence**. The model TBS probability is low, but it aligns with same-symbol, same-scope, same-regime, and top-50 analog evidence.

For the 5-day volatility row:

- TBS probability: 0.146034.
- Threshold: 0.500000.
- Distance below threshold: 0.353966.
- Same-symbol SOXS base rate: 0.135640 from 2,514 rows.
- Same-scope `LEVERAGED_INVERSE` base rate: 0.135640 from 15,084 rows.
- Same-regime base rate: 0.158924 from 59,261 rows.
- All pre-target rows for the same 5-day bear TBS label: 0.160982 from 89,973 rows.
- Analog TBS hit rate: 0.00% at top 10, 12.00% at top 25, 10.00% at top 50.

Blocker classification for the volatility row: **true TBS risk plus probability weakness**.

## Directional Return Versus TBS

For the four 10-day rows, top-10 average forward return is 56.07%, but only 5/10 hit target before stop. Average time to stop is 1.67 sessions, while average time to target is 6.40 sessions. Five of the 10 top analogs are positive forward-return outcomes without TBS success.

At top 50, 38/50 outcomes are positive, but only 14/50 hit target before stop. There are 24 positive forward-return outcomes without TBS success, average time to stop is 3.00 sessions, and average time to target is 6.57 sessions. This supports a possible target/stop timing mismatch, but the analog evidence remains dominated by SOXS self-similarity.

For the 5-day volatility row, 8/10 top analogs have positive forward returns, but 0/10 hit target before stop. At top 50, 36/50 are positive but only 5/50 hit target before stop. This is not a supportive TBS pattern.

## Archetype Comparison

| archetype | analog support | strongest score | strongest expected return | lowest MAE risk | highest TBS evidence | concentration | OOD status | ranking |
|---|---|---|---|---|---|---|---|---|
| Breakout / Breakdown | Same as 10-day group | tied | tied | tied | tied | high | below 0.20 limit | KEEP_AS_RESEARCH_LEAD |
| Trend Continuation | Same as 10-day group | tied | tied | tied | tied | high | below 0.20 limit | KEEP_AS_RESEARCH_LEAD |
| Breadth Deterioration | Same as 10-day group | tied | tied | tied | tied | high | below 0.20 limit | KEEP_AS_RESEARCH_LEAD |
| Pullback Continuation | Same as 10-day group | tied | tied | tied | tied | high | below 0.20 limit | KEEP_AS_RESEARCH_LEAD |
| Volatility Expansion | weaker | lower | highest row expected return, but lower probability | nominally lower expected MAE | weak | high | below 0.20 limit | INSUFFICIENT_EVIDENCE |

The first four archetypes are research leads only because their directional-return analogs remain positive at top 50. They are not validated archetype edges because independence is weak and TBS support collapses toward the historical base rate.

## Footprint And Feature Audit

Measured footprint evidence repeats across the SOXS SELL rows:

- Price structure: `trend_persistence_20=0.0000`, same-scope percentile 22.79%.
- Volume/participation: `relative_volume_20=0.9745`, percentile 50.72%; `down_volume_proxy_20=6.895B`, percentile 99.98%; `up_volume_proxy_20=7.561B`, percentile 100.00%.
- Broad market: `relative_return_vs_spy_20=-0.2941`, percentile 7.00%; `spy_return_20=-0.0339`.
- Sector: `sector_momentum_mean_20=-0.3281`, percentile 2.29%.
- Inverse/leveraged ETF context: `inverse_confirmation_iwm_tza_63=0.9972`, percentile 17.43%; SOXS/XLK relationship features are present.
- Breadth: `breadth_advance_pct=0.6000`, percentile 68.51%; `breadth_up_volume_pct=0.7628`, percentile 66.24%.
- Volatility/range: `atr_pct_14=0.2364`, percentile 99.59%; `downside_vol_20=0.0762`, percentile 98.68%; `upside_vol_20=0.1059`, percentile 99.65%.
- Regime: `market_regime_trend_score=0.1301`, percentile 95.56%; analog regimes are mostly uptrend-high-vol and uptrend-low-vol.
- Relationship graph: `rolling_beta_vs_qqq_63=-6.4491`, percentile 0.00%; `rolling_corr_vs_qqq_63=-0.8940`, percentile 64.68%.
- Residual/unexplained: no separate residual score is persisted for these blocked rows.

Top supporting evidence by row:

- Breakdown: trend persistence, relative volume, ATR percentage.
- Trend continuation: 5-day return, trend persistence, relative return versus SPY.
- Breadth deterioration: breadth advance percentage, relative return versus SPY, inverse confirmation for IWM/TZA.
- Pullback continuation: trend persistence, 5-day return, ATR percentage.
- Volatility expansion: ATR percentage, trend persistence, market-regime trend score.

Conflicting categories are not explicitly listed in the artifacts for these five rows. OOD feature rates are below the 0.20 limit but close enough to remain a caution: 0.1875 for the four 10-day rows and 0.1667 for the volatility row.

## Limitations

- Raw TBS probabilities, calibration plateau diagnostics, calibration confidence, and TBS feature importances are not persisted in the current signal-discovery generation.
- Analog archetype equality is inherited from the target hypothesis in the blocked-row analog export. Historical modeling rows do not independently carry archetype labels.
- The analog pool is dominated by SOXS and recent 2026 observations. It does not provide strong independent cross-symbol evidence.
- These are development-holdout/research diagnostics only and are not final-holdout evidence.
- Analog outcomes are explanatory only. They do not change signal status, thresholds, gates, OOD governance, labels, promotion eligibility, scanner state, or paper-forward events.

## Read-Only Verification

Before-state snapshot:

| item | development before | operational before |
|---|---|---|
| Git HEAD | `278113a5355b0bcdef1c8e2f0f1f8769a6706c73` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | clean branch `feat/product-class-specialist-challengers-v1` | clean branch `feat/autonomous-swing-scanner-v1` |
| SQLite size | 385,888,256 bytes | 250,781,696 bytes |
| SQLite mtime | 2026-06-27T14:08:40 | 2026-06-27T14:43:07 |
| Representative model artifact | `artifacts/models/ab6b20afabb330bc6293beea.joblib`, 7,002,182 bytes, 2026-06-27T11:03:53 | `artifacts/models/4d66c49b675803520298a243.joblib`, 332,921,033 bytes, 2026-06-25T09:45:53 |
| Scanner snapshot count | 3 | 17 |
| Forward-event count | 26 | 310 |
| Final-holdout run count | 1 | 1 |
| Final-holdout event count | 26 | 25 |

After-state snapshot:

| item | development after | operational after |
|---|---|---|
| Git HEAD | `278113a5355b0bcdef1c8e2f0f1f8769a6706c73` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | branch `feat/product-class-specialist-challengers-v1` with only this untracked report | clean branch `feat/autonomous-swing-scanner-v1` |
| SQLite size | 385,888,256 bytes | 250,781,696 bytes |
| SQLite mtime | 2026-06-27T14:08:40 | 2026-06-27T14:43:07 |
| Representative model artifact | `artifacts/models/ab6b20afabb330bc6293beea.joblib`, 7,002,182 bytes, 2026-06-27T11:03:53 | `artifacts/models/4d66c49b675803520298a243.joblib`, 332,921,033 bytes, 2026-06-25T09:45:53 |
| Scanner snapshot count | 3 | 17 |
| Forward-event count | 26 | 310 |
| Final-holdout run count | 1 | 1 |
| Final-holdout event count | 26 | 25 |

Confirmation:

- No source files changed.
- No model artifacts changed.
- No SQLite state changed.
- No scanner state changed.
- No forward state changed.
- No final-holdout state changed.
- No operational state changed.
