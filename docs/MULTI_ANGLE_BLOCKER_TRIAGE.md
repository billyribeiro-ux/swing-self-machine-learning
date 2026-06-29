# Multi-Angle Discovery Blocker Triage

Date: 2026-06-29

Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

This is a read-only triage using only the latest existing signal-discovery
generation and existing analog-robustness reports. No discovery, scanner,
FMP update, retraining, final-holdout update, forward update, threshold change,
promotion, SQLite mutation, model-artifact mutation, or operational repository
write was performed.

## Latest Generation

Latest signal-discovery generation:
`signal_discovery_20260628T193012+0000_cf2753a58c47`

Created at: `2026-06-28T19:30:12+00:00`

Hypotheses evaluated: 15

Hypothesis-family artifact rows: 30, with 28 `CANDIDATE` rows and 2 `REJECTED`
rows. Minimum training, calibration, and holdout sample gates all passed for
the 15 evaluated hypotheses.

## Candidate Counts

| Metric | Count |
| --- | ---: |
| BUY candidates | 0 |
| SELL/SHORT candidates | 0 |
| Selected candidates | 0 |
| NO_SIGNAL rows | 497 |
| Rejected rows | 1 |
| Total blocked/research rows | 498 |

Direction rows in the candidate artifact:

| Direction | Rows | Max score | Mean score | Mean probability | Mean TBS probability | Mean expected return | Top blocker |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Bullish | 253 | 0.642860 | 0.469125 | 0.540006 | 0.281479 | 0.002924 | target-before-stop below threshold |
| Bearish | 245 | 0.579257 | 0.422719 | 0.447034 | 0.204448 | 0.002731 | probability below threshold |

Action rows:

| Action | Rows | Max score | Blockers |
| --- | ---: | ---: | --- |
| BUY | 1 | 0.624110 | OOD feature rate above limit: 1 |
| NO SIGNAL | 497 | 0.642860 | probability below threshold: 280; target-before-stop below threshold: 217 |

## Blocker Counts

Percentages use all 498 blocked/research rows as the denominator.

| Blocker reason | Count | Share |
| --- | ---: | ---: |
| `probability_below_threshold` | 280 | 56.22% |
| `target_before_stop_probability_below_threshold` | 217 | 43.57% |
| `ood_feature_rate_above_limit` | 1 | 0.20% |

Special focus:

- `probability_below_threshold` is the largest blocker and dominates Bearish
  rows.
- `target_before_stop_probability_below_threshold` is the second-largest blocker
  and dominates Bullish rows.
- `ood_feature_rate_above_limit` appears once, on SOXS sector-rotation BUY.
- `analog_concentration_artifact` appears in robustness diagnostics for four
  SOXS 10-day SELL rows.
- `weak_analog_support` appears for TZA, SQQQ, and SOXS sector-rotation BUY.
- `no_robust_analog_support` applies to the full robustness report: 0 rows are
  `ROBUST_SUPPORT` or `SUPPORTIVE_BUT_CONCENTRATED`.

## Top 25 Blocked/Research Rows By Signal Score

| Rank | Ticker | Direction | Action | Archetype | Hypothesis | Score | Probability | TBS probability | Expected return | Expected MFE | Expected MAE | OOD rate | Decision | Blocker |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | TZA | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.642860 | 0.580449 | 0.358930 | 0.086911 | 0.489043 | -0.130642 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 2 | SQQQ | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.641488 | 0.580449 | 0.352071 | 0.061243 | 0.245753 | -0.150198 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 3 | SOXS | Bullish | BUY | Sector Rotation | `sector_rotation_buy_20d` | 0.624110 | 0.580449 | 0.358930 | 0.162623 | 0.327055 | -0.177723 | 0.208333 | REJECTED_BY_OOD | OOD feature rate above limit |
| 4 | SOXS | Bearish | NO SIGNAL | Trend Continuation | `trend_continuation_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | NO_SIGNAL | target-before-stop below threshold |
| 5 | SOXS | Bearish | NO SIGNAL | Pullback Continuation | `pullback_continuation_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | NO_SIGNAL | target-before-stop below threshold |
| 6 | SOXS | Bearish | NO SIGNAL | Breadth Deterioration | `breadth_deterioration_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | NO_SIGNAL | target-before-stop below threshold |
| 7 | SOXS | Bearish | NO SIGNAL | Breakout / Breakdown | `breakdown_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | 0.261760 | -0.134235 | 0.187500 | NO_SIGNAL | target-before-stop below threshold |
| 8 | RWM | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.568312 | 0.580449 | 0.358930 | 0.015431 | 0.096605 | -0.057053 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 9 | AMZN | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.546596 | 0.580449 | 0.394651 | 0.014207 | 0.092275 | -0.089986 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 10 | QID | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.543995 | 0.580449 | 0.352071 | 0.018066 | 0.208333 | -0.130371 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 11 | SOXS | Bearish | NO SIGNAL | Reversal / Exhaustion | `reversal_sell_5d` | 0.539657 | 0.448905 | 0.146034 | 0.066307 | 0.167116 | -0.101209 | 0.166667 | NO_SIGNAL | probability below threshold |
| 12 | SOXS | Bearish | NO SIGNAL | Failed Move / Liquidity Trap | `failed_breakout_sell_5d` | 0.539657 | 0.448905 | 0.146034 | 0.066307 | 0.167116 | -0.101209 | 0.166667 | NO_SIGNAL | probability below threshold |
| 13 | SOXS | Bearish | NO SIGNAL | Volatility Expansion | `volatility_expansion_sell_5d` | 0.539657 | 0.448905 | 0.146034 | 0.066307 | 0.167116 | -0.101209 | 0.166667 | NO_SIGNAL | probability below threshold |
| 14 | XLE | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.536824 | 0.580449 | 0.358930 | 0.015290 | 0.046196 | -0.039540 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 15 | SPXU | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.533714 | 0.580449 | 0.352071 | 0.013715 | 0.322787 | -0.103835 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 16 | XLP | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.532562 | 0.580449 | 0.353828 | 0.015290 | 0.043080 | -0.039540 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 17 | SDS | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.532100 | 0.580449 | 0.352071 | 0.007432 | 0.263703 | -0.076072 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 18 | AAPL | Bullish | NO SIGNAL | Sector Rotation | `sector_rotation_buy_20d` | 0.529368 | 0.580449 | 0.358930 | 0.009765 | 0.086165 | -0.079089 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 19 | MSFT | Bullish | NO SIGNAL | Breakout / Breakdown | `breakout_buy_10d` | 0.528577 | 0.580596 | 0.329055 | 0.004208 | 0.085845 | -0.052427 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 20 | MSFT | Bullish | NO SIGNAL | Volatility Compression Release | `volatility_compression_release_buy_10d` | 0.528577 | 0.580596 | 0.329055 | 0.004208 | 0.085845 | -0.052427 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 21 | MSFT | Bullish | NO SIGNAL | Trend Continuation | `trend_continuation_buy_10d` | 0.528577 | 0.580596 | 0.329055 | 0.004208 | 0.085845 | -0.052427 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 22 | MSFT | Bullish | NO SIGNAL | Pullback Continuation | `pullback_continuation_buy_10d` | 0.528577 | 0.580596 | 0.329055 | 0.004208 | 0.085845 | -0.052427 | 0.020833 | NO_SIGNAL | target-before-stop below threshold |
| 23 | SOXL | Bullish | NO SIGNAL | Pullback Continuation | `pullback_continuation_buy_10d` | 0.524312 | 0.580596 | 0.329055 | 0.014727 | 0.165053 | -0.165608 | 0.125000 | NO_SIGNAL | target-before-stop below threshold |
| 24 | SOXL | Bullish | NO SIGNAL | Trend Continuation | `trend_continuation_buy_10d` | 0.524312 | 0.580596 | 0.329055 | 0.014727 | 0.165053 | -0.165608 | 0.125000 | NO_SIGNAL | target-before-stop below threshold |
| 25 | SOXL | Bullish | NO SIGNAL | Volatility Compression Release | `volatility_compression_release_buy_10d` | 0.524312 | 0.580596 | 0.329055 | 0.014727 | 0.165053 | -0.165608 | 0.125000 | NO_SIGNAL | target-before-stop below threshold |

## BUY Versus SELL Diagnostic

Bullish rows are closer to actionability on direction probability and dominate
the high-score list, but target-before-stop probability blocks the best Bullish
rows. TZA, SQQQ, RWM, AMZN, QID, XLE, SPXU, XLP, SDS, AAPL, MSFT, and SOXL all
have probabilities near or above 0.58 in the top-25 list, but TBS probabilities
cluster around 0.329 to 0.395.

Bearish rows have the most coherent single-ticker research cluster in SOXS. The
four best 10-day SELL rows pass direction probability at 0.619632 and have
positive expected returns, but TBS probability is 0.261255. The 5-day SOXS SELL
rows show positive expected returns but fail direction probability at 0.448905
and have TBS probability only 0.146034.

Conclusion: BUY-side blockers are mostly TBS confidence. SELL-side blockers are
mostly probability confidence, with one SOXS 10-day subset blocked by TBS and
then downgraded by analog concentration.

## Archetype Diagnostic

| Archetype | Rows | Max score | Mean score | Mean probability | Mean TBS probability | Mean expected return | Top blockers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Sector Rotation | 35 | 0.642860 | 0.509827 | 0.578298 | 0.358769 | 0.009160 | TBS: 33; probability: 1; OOD: 1 |
| Breadth Deterioration | 35 | 0.579257 | 0.441149 | 0.457696 | 0.250150 | 0.004034 | probability: 27; TBS: 8 |
| Breakout / Breakdown | 70 | 0.579257 | 0.456161 | 0.496519 | 0.284631 | 0.002379 | probability: 37; TBS: 33 |
| Pullback Continuation | 70 | 0.579257 | 0.456161 | 0.496519 | 0.284631 | 0.002379 | probability: 37; TBS: 33 |
| Trend Continuation | 70 | 0.579257 | 0.456161 | 0.496519 | 0.284631 | 0.002379 | probability: 37; TBS: 33 |
| Failed Move / Liquidity Trap | 70 | 0.539657 | 0.421106 | 0.491485 | 0.161815 | 0.001261 | probability: 44; TBS: 26 |
| Reversal / Exhaustion | 70 | 0.539657 | 0.421106 | 0.491485 | 0.161815 | 0.001261 | probability: 44; TBS: 26 |
| Volatility Expansion | 35 | 0.539657 | 0.398147 | 0.432817 | 0.143512 | 0.000995 | probability: 35 |
| Volatility Compression Release | 35 | 0.528577 | 0.471174 | 0.535342 | 0.319112 | 0.000724 | TBS: 25; probability: 10 |
| Risk-On / Risk-Off | 8 | 0.514791 | 0.474478 | 0.365320 | 0.171685 | 0.026385 | probability: 8 |

Sector Rotation is the strongest archetype by score and mean probability, but
its best rows are TBS-blocked and analog robustness is weak or mixed. SOXS SELL
archetypes are the best directional research lead, but the robust analog guard
classifies the four formerly supportive 10-day rows as concentration artifacts.

## Signal Score Component Audit

Mean component values:

| Component | All rows mean | Top-25 mean |
| --- | ---: | ---: |
| direction probability | 0.494267 | 0.570974 |
| target-before-stop probability | 0.243582 | 0.309517 |
| expected return | 0.002829 | 0.032974 |
| expected return after cost | 0.002329 | 0.032474 |
| expected return score | 0.317336 | 0.631514 |
| expected MFE | 0.072040 | 0.184317 |
| expected MFE score | 0.587291 | 0.923081 |
| expected MAE | -0.059175 | -0.104846 |
| expected MAE score | 0.454323 | 0.163604 |
| liquidity score | 0.985304 | 0.989474 |
| footprint support score | 0.401518 | 0.512192 |
| OOD feature rate / penalty | 0.029284 | 0.085000 |
| conflict penalty | 0.000000 | 0.000000 |
| concentration penalty | 0.000000 | 0.000000 |
| signal score | 0.446295 | 0.554207 |

The top rows score well because expected return, expected MFE, liquidity, and
direction probability are strong. They remain blocked because TBS probability is
low and expected MAE is heavy. The scoring formula is surfacing interesting
research rows, but the current gates require confidence in both direction and
target-before-stop sequencing.

## Footprint Quality Audit

Footprint evidence artifact:

- rows: 497;
- missing-data status: 497 `available`;
- evidence type: 497 `neutral`;
- category: 497 `NO_SIGNAL decision`.

Interpretation: footprint plumbing is available for every NO_SIGNAL row, but
the persisted evidence is decision-level neutral evidence, not rich supporting
or conflicting footprint evidence. This limits post-hoc triage quality. The
analog robustness report now supplies stronger blocked-row context for 12 top
rows, but broad footprint quality still needs more measured support/conflict
detail for blocked rows.

## Analog Robustness Impact

Robustness report rows: 12

| Robust label | Count |
| --- | ---: |
| `MIXED_SUPPORT` | 5 |
| `CONCENTRATION_ARTIFACT` | 4 |
| `WEAK_SUPPORT` | 3 |
| `ROBUST_SUPPORT` | 0 |
| `SUPPORTIVE_BUT_CONCENTRATED` | 0 |
| `INSUFFICIENT_ANALOGS` | 0 |
| `DECAYS_WITH_DEPTH` | 0 |

Caution flags:

| Flag | Count |
| --- | ---: |
| `high_mae_tail_risk` | 11 |
| `same_year_concentration` | 9 |
| `same_symbol_concentration` | 8 |
| `high_return_dispersion` | 8 |
| `analogs_mostly_same_event_cluster` | 7 |
| `same_regime_concentration` | 6 |
| `tbs_support_decay` | 5 |
| `support_decays_top25` | 4 |
| `support_decays_top50` | 4 |
| `ood_target_row` | 1 |

The guard materially changes the interpretation of SOXS SELL rows. The old
top-10 label was `SUPPORTIVE`; after robustness expansion, all four 10-day SOXS
SELL rows are `CONCENTRATION_ARTIFACT`. The rows still look like research leads
because top-50 directional outcomes remain positive, but they are not robust
analog support and do not contradict the TBS blocker.

Top-50 analog depth confirms the broader picture:

| Target | Hypothesis | Top-50 support | Avg return | Win rate | TBS hit rate | Same-symbol share | Same-year max share | Worst MAE |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TZA | `sector_rotation_buy_20d` | WEAK | -1.72% | 36.00% | 42.00% | 32.00% | 34.00% | -29.15% |
| SQQQ | `sector_rotation_buy_20d` | MIXED | -0.16% | 46.00% | 38.00% | 34.00% | 30.00% | -40.02% |
| SOXS BUY | `sector_rotation_buy_20d` | WEAK | -20.59% | 18.00% | 20.00% | 98.00% | 30.00% | -67.34% |
| SOXS SELL 10-day group | `breakdown/trend/breadth/pullback_sell_10d` | MIXED | 22.11% | 76.00% | 28.00% | 96.00% | 34.00% | -29.97% |
| SOXS SELL 5-day group | `failed_breakout/reversal/volatility_sell_5d` | MIXED | 12.78% | 72.00% | 10.00% | 98.00% | 46.00% | -26.16% |
| RWM | `sector_rotation_buy_20d` | WEAK | -0.46% | 36.00% | 42.00% | 46.00% | 24.00% | -11.81% |
| AMZN | `sector_rotation_buy_20d` | WEAK | -0.48% | 42.00% | 10.00% | 8.00% | 42.00% | -24.67% |

## Root-Cause Classification

Classification:
`MODEL_GATE_BLOCKED_WITH_NO_ROBUST_ANALOG_CONFIRMATION`

Reason:

- no selected candidates exist because every row is blocked by current policy:
  280 fail direction probability, 217 fail TBS probability, and 1 fails OOD;
- the highest BUY-side scores are TBS-blocked and have weak or mixed analog
  robustness;
- the strongest SELL-side research cluster is SOXS, but robust analog
  diagnostics classify the previously supportive 10-day cluster as a
  concentration artifact;
- no target row has `ROBUST_SUPPORT` or `SUPPORTIVE_BUT_CONCENTRATED`;
- footprint evidence is available but too neutral at the blocked-row level to
  independently strengthen the case.

This is not a threshold problem by itself. The current evidence says the engine
found interesting but unconfirmed research rows, and the gates are doing their
job by preventing BUY/SELL selection without robust probability, TBS, OOD, and
analog confirmation.

## Immutability Proof

Before/after values:

| Item | Before | After |
| --- | --- | --- |
| Development SQLite size | 385,888,256 bytes | 385,888,256 bytes |
| Development SQLite mtime | 2026-06-27T14:08:40 | 2026-06-27T14:08:40 |
| Development representative artifact | `artifacts/models/ab6b20afabb330bc6293beea.joblib`, 7,002,182 bytes, 2026-06-27T11:03:53 | unchanged |
| Development scanner snapshot count | 4 SQLite rows; 3 ordinary scanner artifacts | unchanged |
| Development forward-event count | 26 | unchanged |
| Development final-holdout run count | 1 | unchanged |
| Operational HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Operational Git status | clean `feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` | unchanged |
| Operational final-holdout event count | 25 | 25 |

Confirmed no source files, model artifacts, SQLite state, scanner state,
forward state, final-holdout state, or operational state were modified. The only
development write for this task is this markdown report.

## Plain-English Summary

1. What the scanner currently found: It found high-scoring research rows, led by
   TZA and SQQQ sector-rotation BUY setups and SOXS SELL setups.
2. What it rejected: It rejected one SOXS sector-rotation BUY row for OOD
   feature rate and left all other rows as `NO_SIGNAL`.
3. What looks promising: SOXS SELL remains the most interesting directional
   research lead, and Sector Rotation remains the strongest BUY-side archetype
   by score.
4. What is still blocking BUY/SELL candidates: Probability confidence,
   target-before-stop confidence, OOD on one SOXS BUY row, weak analog support,
   analog concentration artifacts, and no robust analog support.
5. What single thing should improve next: Add an archetype-specific
   calibration-only TBS diagnostic for the highest-scoring blocked rows.

## Next Engineering Task

Add an archetype-specific calibration-only TBS diagnostic for the highest-scoring
blocked rows.
