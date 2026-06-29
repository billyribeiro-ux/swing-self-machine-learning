# Archetype-Specific Target-Before-Stop Calibration Diagnostic

Date: 2026-06-29

Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Generation: `signal_discovery_20260628T193012+0000_cf2753a58c47`

Operational frozen run: `3493ee8ac37bf96475c362e1`; enrolled model
`b93b2258c10aea5cef81d291`; baseline date `2026-06-25`.

This diagnostic used existing artifacts only. It did not run discovery, scanner,
model discovery, retraining, final-holdout update, forward update, daily cycle,
FMP update, threshold changes, gate changes, OOD-governance changes, promotion,
SQLite mutation, model-artifact mutation, scanner-state mutation, forward-state
mutation, final-holdout-state mutation, or operational-repository writes.

## Scope And Evidence Boundary

Rows analyzed are the ten requested high-scoring blocked rows. Additional
archetype rows are summarized only at the calibration-label level for the 15
hypotheses already evaluated in the generation.

Important evidence limitation: `multi_angle_signal_discovery_v1` persisted latest
candidate probabilities and development-holdout hypothesis metrics, but it did
not persist calibration-slice raw or calibrated probability audits for the
transient per-hypothesis models. Reconstructing those distributions would require
refitting the ephemeral signal-discovery models, which is prohibited by this
read-only request. Therefore model Brier, ROC-AUC, PR-AUC, ECE, calibration
slope/intercept, calibrated plateaus, threshold exceedance counts, probability
buckets, and raw-versus-calibrated rank correlation are marked `N/A` when they
would require calibration predictions.

The calibration-label split was reconstructed from the existing modeling parquet
using the repository's chronological split rule. Reconstructed calibration row
counts match the persisted hypothesis `calibration_rows`: `True`.

## Rows Analyzed

| Ticker | Hypothesis | Direction | Archetype | Signal score | TBS probability | Blocker |
| --- | --- | --- | --- | ---: | ---: | --- |
| TZA | `sector_rotation_buy_20d` | Bullish | Sector Rotation | 0.642860 | 35.89% | `target_before_stop_probability_below_threshold` |
| SQQQ | `sector_rotation_buy_20d` | Bullish | Sector Rotation | 0.641488 | 35.21% | `target_before_stop_probability_below_threshold` |
| RWM | `sector_rotation_buy_20d` | Bullish | Sector Rotation | 0.568312 | 35.89% | `target_before_stop_probability_below_threshold` |
| AMZN | `sector_rotation_buy_20d` | Bullish | Sector Rotation | 0.546596 | 39.47% | `target_before_stop_probability_below_threshold` |
| QID | `sector_rotation_buy_20d` | Bullish | Sector Rotation | 0.543995 | 35.21% | `target_before_stop_probability_below_threshold` |
| SOXS | `trend_continuation_sell_10d` | Bearish | Trend Continuation | 0.579257 | 26.13% | `target_before_stop_probability_below_threshold` |
| SOXS | `pullback_continuation_sell_10d` | Bearish | Pullback Continuation | 0.579257 | 26.13% | `target_before_stop_probability_below_threshold` |
| SOXS | `breadth_deterioration_sell_10d` | Bearish | Breadth Thrust / Breadth Deterioration | 0.579257 | 26.13% | `target_before_stop_probability_below_threshold` |
| SOXS | `breakdown_sell_10d` | Bearish | Breakout / Breakdown | 0.579257 | 26.13% | `target_before_stop_probability_below_threshold` |
| SOXS | `volatility_expansion_sell_5d` | Bearish | Volatility Expansion | 0.539657 | 14.60% | `probability_below_threshold` |

## Current Blocker Context

| Metric | Count |
| --- | ---: |
| Hypotheses evaluated | 15 |
| BUY candidates | 0 |
| SELL/SHORT candidates | 0 |
| NO_SIGNAL rows | 497 |
| OOD-rejected rows | 1 |
| `probability_below_threshold` | 280 |
| `target_before_stop_probability_below_threshold` | 217 |
| `ood_feature_rate_above_limit` | 1 |

Root cause entering this diagnostic:
`MODEL_GATE_BLOCKED_WITH_NO_ROBUST_ANALOG_CONFIRMATION`.

## Calibration-Only Threshold Table

Diagnostic thresholds: `0.30`, `0.35`, `0.40`, `0.45`, `0.50`, `0.55`, `0.60`.
No production threshold is changed or recommended from this table.

| Threshold | Raw calibration probability count above | Calibrated calibration probability count above | Evidence status |
| ---: | ---: | ---: | --- |
| 0.30 | N/A | N/A | Not persisted for multi-angle calibration slice; computing would require refitting ephemeral models. |
| 0.35 | N/A | N/A | Not persisted for multi-angle calibration slice; computing would require refitting ephemeral models. |
| 0.40 | N/A | N/A | Not persisted for multi-angle calibration slice; computing would require refitting ephemeral models. |
| 0.45 | N/A | N/A | Not persisted for multi-angle calibration slice; computing would require refitting ephemeral models. |
| 0.50 | N/A | N/A | Not persisted for multi-angle calibration slice; computing would require refitting ephemeral models. |
| 0.55 | N/A | N/A | Not persisted for multi-angle calibration slice; computing would require refitting ephemeral models. |
| 0.60 | N/A | N/A | Not persisted for multi-angle calibration slice; computing would require refitting ephemeral models. |

## Calibration-Only Archetype Label Summary

These rows use observed calibration-slice labels only, not development holdout.
They are valid for base-rate and target/stop-policy inspection, but they are not
model-calibration performance metrics.

| Archetype | Direction | Horizon | Hypothesis | Cal rows | TBS positive | TBS negative | Base TBS hit rate | Target hit probability | Stop hit probability | Unresolved probability | Avg forward return | Avg MFE | Avg MAE |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Breadth Thrust / Breadth Deterioration | Bearish | 10 | `breadth_deterioration_sell_10d` | 17185 | 4314 | 12871 | 25.10% | 25.11% | 63.47% | 11.42% | 0.18% | 5.65% | -5.01% |
| Breakout / Breakdown | Bearish | 10 | `breakdown_sell_10d` | 17185 | 4314 | 12871 | 25.10% | 25.11% | 63.47% | 11.42% | 0.18% | 5.65% | -5.01% |
| Breakout / Breakdown | Bullish | 10 | `breakout_buy_10d` | 17185 | 5179 | 12006 | 30.14% | 30.15% | 58.01% | 11.85% | 0.47% | 5.62% | -4.97% |
| Failed Move / Liquidity Trap Proxy | Bearish | 5 | `failed_breakout_sell_5d` | 17395 | 2610 | 14785 | 15.00% | 15.01% | 50.19% | 34.80% | 0.08% | 3.80% | -3.48% |
| Failed Move / Liquidity Trap Proxy | Bullish | 5 | `failed_breakdown_buy_5d` | 17395 | 3016 | 14379 | 17.34% | 17.36% | 45.91% | 36.75% | 0.23% | 3.78% | -3.48% |
| Pullback Continuation | Bearish | 10 | `pullback_continuation_sell_10d` | 17185 | 4314 | 12871 | 25.10% | 25.11% | 63.47% | 11.42% | 0.18% | 5.65% | -5.01% |
| Pullback Continuation | Bullish | 10 | `pullback_continuation_buy_10d` | 17185 | 5179 | 12006 | 30.14% | 30.15% | 58.01% | 11.85% | 0.47% | 5.62% | -4.97% |
| Reversal / Exhaustion | Bearish | 5 | `reversal_sell_5d` | 17395 | 2610 | 14785 | 15.00% | 15.01% | 50.19% | 34.80% | 0.08% | 3.80% | -3.48% |
| Reversal / Exhaustion | Bullish | 5 | `reversal_buy_5d` | 17395 | 3016 | 14379 | 17.34% | 17.36% | 45.91% | 36.75% | 0.23% | 3.78% | -3.48% |
| Risk-On / Risk-Off | Bullish | 10 | `risk_off_buy_inverse_10d` | 3928 | 878 | 3050 | 22.35% | 22.40% | 66.50% | 11.15% | -1.85% | 6.41% | -7.52% |
| Sector Rotation | Bullish | 20 | `sector_rotation_buy_20d` | 16765 | 5993 | 10772 | 35.75% | 35.76% | 62.62% | 1.63% | 0.96% | 8.50% | -7.17% |
| Trend Continuation | Bearish | 10 | `trend_continuation_sell_10d` | 17185 | 4314 | 12871 | 25.10% | 25.11% | 63.47% | 11.42% | 0.18% | 5.65% | -5.01% |
| Trend Continuation | Bullish | 10 | `trend_continuation_buy_10d` | 17185 | 5179 | 12006 | 30.14% | 30.15% | 58.01% | 11.85% | 0.47% | 5.62% | -4.97% |
| Volatility Compression Release | Bullish | 10 | `volatility_compression_release_buy_10d` | 17185 | 5179 | 12006 | 30.14% | 30.15% | 58.01% | 11.85% | 0.47% | 5.62% | -4.97% |
| Volatility Expansion | Bearish | 5 | `volatility_expansion_sell_5d` | 17395 | 2610 | 14785 | 15.00% | 15.01% | 50.19% | 34.80% | 0.08% | 3.80% | -3.48% |

## Archetype-Specific TBS Quality

`TBS Brier`, `ROC-AUC`, `PR-AUC`, `ECE`, calibration slope/intercept,
raw-versus-calibrated rank correlation, plateau size, unique calibrated
probability count, probability distribution, and realized TBS rate by decile are
not persisted for the transient multi-angle calibration slice. The table below
therefore reports the available base-rate Brier and explicitly marks model
quality fields as unavailable.

| Archetype | Direction | Horizon | Hypothesis | TBS Brier | Naive/base-rate Brier | Brier skill | ROC-AUC | PR-AUC | ECE | Calibration slope | Calibration intercept | Raw/cal rank corr | Largest plateau | Unique calibrated probabilities | Realized TBS rate |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Breadth Thrust / Breadth Deterioration | Bearish | 10 | `breadth_deterioration_sell_10d` | N/A | 0.188015 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 25.10% |
| Breakout / Breakdown | Bearish | 10 | `breakdown_sell_10d` | N/A | 0.188015 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 25.10% |
| Breakout / Breakdown | Bullish | 10 | `breakout_buy_10d` | N/A | 0.210545 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 30.14% |
| Failed Move / Liquidity Trap Proxy | Bearish | 5 | `failed_breakout_sell_5d` | N/A | 0.127530 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 15.00% |
| Failed Move / Liquidity Trap Proxy | Bullish | 5 | `failed_breakdown_buy_5d` | N/A | 0.143321 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 17.34% |
| Pullback Continuation | Bearish | 10 | `pullback_continuation_sell_10d` | N/A | 0.188015 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 25.10% |
| Pullback Continuation | Bullish | 10 | `pullback_continuation_buy_10d` | N/A | 0.210545 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 30.14% |
| Reversal / Exhaustion | Bearish | 5 | `reversal_sell_5d` | N/A | 0.127530 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 15.00% |
| Reversal / Exhaustion | Bullish | 5 | `reversal_buy_5d` | N/A | 0.143321 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 17.34% |
| Risk-On / Risk-Off | Bullish | 10 | `risk_off_buy_inverse_10d` | N/A | 0.173561 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 22.35% |
| Sector Rotation | Bullish | 20 | `sector_rotation_buy_20d` | N/A | 0.229685 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 35.75% |
| Trend Continuation | Bearish | 10 | `trend_continuation_sell_10d` | N/A | 0.188015 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 25.10% |
| Trend Continuation | Bullish | 10 | `trend_continuation_buy_10d` | N/A | 0.210545 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 30.14% |
| Volatility Compression Release | Bullish | 10 | `volatility_compression_release_buy_10d` | N/A | 0.210545 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 30.14% |
| Volatility Expansion | Bearish | 5 | `volatility_expansion_sell_5d` | N/A | 0.127530 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 15.00% |

## Product, Symbol, Regime, And Year Segmentation

Compact segmentation is shown for the requested hypotheses. Rates are
calibration-label base TBS rates.

| Hypothesis | Product-scope rates | Largest ticker samples | Regime rates | Largest year samples |
| --- | --- | --- | --- | --- |
| `breadth_deterioration_sell_10d` | ORDINARY: n=11293, rate=23.65%; LEVERAGED_INVERSE: n=2946, rate=30.11%; LEVERAGED_LONG: n=1964, rate=23.22%; INVERSE: n=982, rate=30.55% | AAPL: n=491, rate=21.79%; AMD: n=491, rate=26.07%; AMZN: n=491, rate=21.18%; DIA: n=491, rate=22.61%; GOOGL: n=491, rate=21.79% | uptrend_low_vol: n=6440, rate=27.45%; uptrend_high_vol: n=5285, rate=25.24%; downtrend_high_vol: n=5215, rate=21.80%; mixed: n=245, rate=30.61% | 2023: n=8750, rate=25.14%; 2022: n=4865, rate=25.16%; 2024: n=3570, rate=24.93% |
| `breakdown_sell_10d` | ORDINARY: n=11293, rate=23.65%; LEVERAGED_INVERSE: n=2946, rate=30.11%; LEVERAGED_LONG: n=1964, rate=23.22%; INVERSE: n=982, rate=30.55% | AAPL: n=491, rate=21.79%; AMD: n=491, rate=26.07%; AMZN: n=491, rate=21.18%; DIA: n=491, rate=22.61%; GOOGL: n=491, rate=21.79% | uptrend_low_vol: n=6440, rate=27.45%; uptrend_high_vol: n=5285, rate=25.24%; downtrend_high_vol: n=5215, rate=21.80%; mixed: n=245, rate=30.61% | 2023: n=8750, rate=25.14%; 2022: n=4865, rate=25.16%; 2024: n=3570, rate=24.93% |
| `pullback_continuation_sell_10d` | ORDINARY: n=11293, rate=23.65%; LEVERAGED_INVERSE: n=2946, rate=30.11%; LEVERAGED_LONG: n=1964, rate=23.22%; INVERSE: n=982, rate=30.55% | AAPL: n=491, rate=21.79%; AMD: n=491, rate=26.07%; AMZN: n=491, rate=21.18%; DIA: n=491, rate=22.61%; GOOGL: n=491, rate=21.79% | uptrend_low_vol: n=6440, rate=27.45%; uptrend_high_vol: n=5285, rate=25.24%; downtrend_high_vol: n=5215, rate=21.80%; mixed: n=245, rate=30.61% | 2023: n=8750, rate=25.14%; 2022: n=4865, rate=25.16%; 2024: n=3570, rate=24.93% |
| `sector_rotation_buy_20d` | ORDINARY: n=11017, rate=38.41%; LEVERAGED_INVERSE: n=2874, rate=27.00%; LEVERAGED_LONG: n=1916, rate=37.53%; INVERSE: n=958, rate=27.77% | AAPL: n=479, rate=45.30%; AMD: n=479, rate=35.07%; AMZN: n=479, rate=39.46%; DIA: n=479, rate=40.29%; GOOGL: n=479, rate=36.33% | uptrend_low_vol: n=6055, rate=34.88%; downtrend_high_vol: n=5425, rate=38.65%; uptrend_high_vol: n=5040, rate=33.73%; mixed: n=245, rate=34.29% | 2023: n=8750, rate=36.91%; 2022: n=5075, rate=33.87%; 2024: n=2940, rate=35.51% |
| `trend_continuation_sell_10d` | ORDINARY: n=11293, rate=23.65%; LEVERAGED_INVERSE: n=2946, rate=30.11%; LEVERAGED_LONG: n=1964, rate=23.22%; INVERSE: n=982, rate=30.55% | AAPL: n=491, rate=21.79%; AMD: n=491, rate=26.07%; AMZN: n=491, rate=21.18%; DIA: n=491, rate=22.61%; GOOGL: n=491, rate=21.79% | uptrend_low_vol: n=6440, rate=27.45%; uptrend_high_vol: n=5285, rate=25.24%; downtrend_high_vol: n=5215, rate=21.80%; mixed: n=245, rate=30.61% | 2023: n=8750, rate=25.14%; 2022: n=4865, rate=25.16%; 2024: n=3570, rate=24.93% |
| `volatility_expansion_sell_5d` | ORDINARY: n=11431, rate=14.43%; LEVERAGED_INVERSE: n=2982, rate=16.90%; LEVERAGED_LONG: n=1988, rate=14.39%; INVERSE: n=994, rate=17.10% | AAPL: n=497, rate=12.07%; AMD: n=497, rate=12.68%; AMZN: n=497, rate=11.87%; DIA: n=497, rate=15.69%; GOOGL: n=497, rate=12.27% | uptrend_low_vol: n=6755, rate=16.31%; uptrend_high_vol: n=5285, rate=13.70%; downtrend_high_vol: n=5110, rate=14.17%; mixed: n=245, rate=24.49% | 2023: n=8750, rate=14.55%; 2022: n=4760, rate=15.86%; 2024: n=3885, rate=14.98% |

## Top-Row TBS Comparison

Analog outcomes are explanatory only and do not override gates.

| Ticker | Direction | Hypothesis | Score | Model TBS probability | Same-archetype cal base | Same-scope cal base | Same-symbol cal base | Top-10 analog TBS | Top-25 analog TBS | Top-50 analog TBS | Robust analog label | Caution flags | Classification | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| TZA | Bullish | `sector_rotation_buy_20d` | 0.642860 | 35.89% | 35.75% | 27.00% (2874) | 30.48% (479) | 30.00% | 56.00% | 42.00% | WEAK_SUPPORT | high_return_dispersion; high_mae_tail_risk | VALID_BLOCKER | analog support weak |
| SQQQ | Bullish | `sector_rotation_buy_20d` | 0.641488 | 35.21% | 35.75% | 27.00% (2874) | 27.77% (479) | 20.00% | 48.00% | 38.00% | WEAK_SUPPORT | high_return_dispersion; high_mae_tail_risk | VALID_BLOCKER | analog support weak |
| RWM | Bullish | `sector_rotation_buy_20d` | 0.568312 | 35.89% | 35.75% | 27.77% (958) | 30.69% (479) | 60.00% | 48.00% | 42.00% | MIXED_SUPPORT | same_regime_concentration; high_return_dispersion; tbs_support_decay | VALID_BLOCKER | calibration base rate supports current gate |
| AMZN | Bullish | `sector_rotation_buy_20d` | 0.546596 | 39.47% | 35.75% | 38.41% (11017) | 39.46% (479) | 0.00% | 4.00% | 10.00% | MIXED_SUPPORT | same_year_concentration; same_regime_concentration; high_return_dispersion; high_mae_tail_risk | VALID_BLOCKER | calibration base rate supports current gate |
| QID | Bullish | `sector_rotation_buy_20d` | 0.543995 | 35.21% | 35.75% | 27.00% (2874) | 27.35% (479) | N/A | N/A | N/A | N/A | N/A | INSUFFICIENT_EVIDENCE | exact row not selected into analog robustness artifact |
| SOXS | Bearish | `trend_continuation_sell_10d` | 0.579257 | 26.13% | 25.10% | 30.11% (2946) | 29.33% (491) | 50.00% | 36.00% | 28.00% | CONCENTRATION_ARTIFACT | same_symbol_concentration; same_year_concentration; high_return_dispersion; high_mae_tail_risk; tbs_support_decay; support_decays_top25; support_decays_top50; analogs_mostly_same_event_cluster | ANALOG_WEAKNESS | top-10 analog support decays into concentration artifact |
| SOXS | Bearish | `pullback_continuation_sell_10d` | 0.579257 | 26.13% | 25.10% | 30.11% (2946) | 29.33% (491) | 50.00% | 36.00% | 28.00% | CONCENTRATION_ARTIFACT | same_symbol_concentration; same_year_concentration; high_return_dispersion; high_mae_tail_risk; tbs_support_decay; support_decays_top25; support_decays_top50; analogs_mostly_same_event_cluster | ANALOG_WEAKNESS | top-10 analog support decays into concentration artifact |
| SOXS | Bearish | `breadth_deterioration_sell_10d` | 0.579257 | 26.13% | 25.10% | 30.11% (2946) | 29.33% (491) | 50.00% | 36.00% | 28.00% | CONCENTRATION_ARTIFACT | same_symbol_concentration; same_year_concentration; high_return_dispersion; high_mae_tail_risk; tbs_support_decay; support_decays_top25; support_decays_top50; analogs_mostly_same_event_cluster | ANALOG_WEAKNESS | top-10 analog support decays into concentration artifact |
| SOXS | Bearish | `breakdown_sell_10d` | 0.579257 | 26.13% | 25.10% | 30.11% (2946) | 29.33% (491) | 50.00% | 36.00% | 28.00% | CONCENTRATION_ARTIFACT | same_symbol_concentration; same_year_concentration; high_return_dispersion; high_mae_tail_risk; tbs_support_decay; support_decays_top25; support_decays_top50; analogs_mostly_same_event_cluster | ANALOG_WEAKNESS | top-10 analog support decays into concentration artifact |
| SOXS | Bearish | `volatility_expansion_sell_5d` | 0.539657 | 14.60% | 15.00% | 16.90% (2982) | 14.69% (497) | 0.00% | 12.00% | 10.00% | MIXED_SUPPORT | same_symbol_concentration; same_year_concentration; same_regime_concentration; high_mae_tail_risk; analogs_mostly_same_event_cluster | VALID_BLOCKER | calibration base rate supports current gate |

## Target/Stop Policy Mismatch Check

The basis is same-symbol calibration when at least 20 calibration rows exist;
otherwise same-scope or same-archetype calibration is used. `Profitable after
adverse movement` means the share of positive-return calibration rows with MAE
worse than `-1%` before or during the horizon.

| Ticker | Hypothesis | Basis | Rows | TBS hit rate | Avg forward return | Median forward return | Avg time to target | Avg time to stop | Avg MFE | Avg MAE | Worst MAE | Profitable after adverse movement | Policy mismatch read |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| TZA | `sector_rotation_buy_20d` | same-symbol calibration | 479 | 30.48% | -2.19% | -2.81% | 7.03 | 4.68 | 13.71% | -13.85% | -38.03% | 91.55% | NO_CLEAR_MISMATCH |
| SQQQ | `sector_rotation_buy_20d` | same-symbol calibration | 479 | 27.77% | -5.56% | -7.94% | 6.81 | 4.44 | 12.08% | -14.74% | -42.42% | 89.44% | NO_CLEAR_MISMATCH |
| RWM | `sector_rotation_buy_20d` | same-symbol calibration | 479 | 30.69% | -0.70% | -0.72% | 6.69 | 4.48 | 4.43% | -4.78% | -14.39% | 67.26% | NO_CLEAR_MISMATCH |
| AMZN | `sector_rotation_buy_20d` | same-symbol calibration | 479 | 39.46% | 2.54% | 3.22% | 7.60 | 4.04 | 8.83% | -6.26% | -28.43% | 82.02% | NO_CLEAR_MISMATCH |
| QID | `sector_rotation_buy_20d` | same-symbol calibration | 479 | 27.35% | -3.69% | -4.99% | 6.47 | 4.34 | 7.96% | -10.00% | -30.24% | 85.81% | NO_CLEAR_MISMATCH |
| SOXS | `trend_continuation_sell_10d` | same-symbol calibration | 491 | 29.33% | 8.39% | 5.81% | 5.45 | 3.78 | 20.47% | -10.54% | -41.09% | 90.13% | POSSIBLE_LOCAL_MISMATCH |
| SOXS | `pullback_continuation_sell_10d` | same-symbol calibration | 491 | 29.33% | 8.39% | 5.81% | 5.45 | 3.78 | 20.47% | -10.54% | -41.09% | 90.13% | POSSIBLE_LOCAL_MISMATCH |
| SOXS | `breadth_deterioration_sell_10d` | same-symbol calibration | 491 | 29.33% | 8.39% | 5.81% | 5.45 | 3.78 | 20.47% | -10.54% | -41.09% | 90.13% | POSSIBLE_LOCAL_MISMATCH |
| SOXS | `breakdown_sell_10d` | same-symbol calibration | 491 | 29.33% | 8.39% | 5.81% | 5.45 | 3.78 | 20.47% | -10.54% | -41.09% | 90.13% | POSSIBLE_LOCAL_MISMATCH |
| SOXS | `volatility_expansion_sell_5d` | same-symbol calibration | 497 | 14.69% | 4.22% | 3.12% | 3.51 | 2.75 | 12.68% | -7.87% | -34.86% | 86.35% | POSSIBLE_LOCAL_MISMATCH |

## Interpretation

1. True weak TBS evidence: supported for the BUY-side sector-rotation rows. Their
   same-archetype calibration base rate is below the production TBS gate, and
   the persisted analog evidence is weak, mixed, or not available for exact QID.
2. TBS model underconfidence: not proven. Calibration probability audits are not
   persisted, and refitting models is prohibited. Some SOXS SELL analog returns
   look directionally positive, but their TBS rates are low or concentrated.
3. Calibration collapse: not proven for this generation because calibration
   raw/calibrated distributions are not persisted for the ephemeral multi-angle
   heads.
4. Archetype-specific calibration mismatch: possible but unproven. The strongest
   evidence is that Sector Rotation BUY and SOXS SELL rows have materially
   different TBS behavior by product/symbol, but the model-calibration audit
   needed to prove mismatch is unavailable without retraining.
5. Product-class or symbol-specific behavior: supported. Leveraged-inverse rows
   show concentrated SOXS/TZA/SQQQ behavior, and ordinary AMZN sector rotation
   has a very different same-symbol/analog profile.
6. Target/stop policy mismatch: localized possibility for SOXS SELL rows only.
   Same-symbol and analog evidence can show positive directional return while
   TBS stays low, meaning the target-before-stop framing may be stricter than the
   return lens for that product/symbol. This is not a threshold-change
   recommendation.
7. Analog evidence weaker than first appeared: supported. Robustness summary:
   `0` robust support rows,
   `0` supportive-but-concentrated rows,
   `4` concentration artifacts.
8. Insufficient evidence: supported for model-calibration quality fields because
   the required calibration prediction audits were not persisted.

## Root-Cause Classification

Overall TBS blocker evidence is classified as:
`VALID_MODEL_GATE, ANALOG_SUPPORT_NOT_ROBUST, PRODUCT_CLASS_INSTABILITY, INSUFFICIENT_EVIDENCE, TARGET_STOP_POLICY_MISMATCH`.

Not classified as `IMPLEMENTATION_DEFECT`: no specific bug was proven. The main
limitation is artifact coverage for calibration diagnostics, not evidence of a
calculation defect.

## Conclusion

The TBS gate is behaving as a valid model gate under the evidence currently
persisted. BUY-side sector-rotation rows have calibration base rates and analog
support that do not justify overriding the TBS blocker. SOXS SELL rows remain the
most interesting research lead, but the robust analog guard downgrades their
nearest-neighbor support because it is concentrated and because target-before-
stop support decays with depth. The diagnostic cannot prove model
underconfidence or calibration collapse without calibration-slice probability
audits, and retraining to recreate them is outside the request.

## Next Engineering Task

Persist read-only multi-angle calibration audit artifacts for each evaluated
hypothesis and family: calibration raw TBS probability, calibrated TBS
probability, label, ticker, product scope, regime, year, forward return, MFE,
MAE, time to target, and time to stop.

## Immutability Review

| Item | Before | After |
| --- | --- | --- |
| Development Git status | `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1` | `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1`<br>`?? docs/ARCHETYPE_TBS_CALIBRATION_DIAGNOSTIC.md` |
| Development SQLite size | 385888256 bytes | 385888256 bytes |
| Development SQLite mtime | 2026-06-27T14:08:40 | 2026-06-27T14:08:40 |
| Representative artifact | `artifacts/models/ab6b20afabb330bc6293beea.joblib`, 7002182 bytes, 2026-06-27T11:03:53 | `artifacts/models/ab6b20afabb330bc6293beea.joblib`, 7002182 bytes, 2026-06-27T11:03:53 |
| Development scanner snapshot count | 4 | 4 |
| Development forward-event count | 26 | 26 |
| Development final-holdout run count | 1 | 1 |
| Operational HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Operational Git status | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` |
| Operational final-holdout event count | 25 | 25 |

Confirmed unchanged: source files, model artifacts, SQLite state, scanner state,
forward state, final-holdout state, and operational state. The only intended
write is this markdown report in the development repository.
