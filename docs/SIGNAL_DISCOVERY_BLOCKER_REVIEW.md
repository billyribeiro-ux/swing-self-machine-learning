# Signal Discovery Blocker Review

Review date: 2026-06-28

Generation reviewed: `signal_discovery_20260628T193012+0000_cf2753a58c47`

Latest decision date: 2026-06-26

Schema: `signal_discovery_blocker_report_v1`

Source: ignored local development export under `reports/signal_discovery_blockers_v1/`

## Summary

The latest multi-angle signal discovery generation is behaving conservatively.
It evaluated 15 hypotheses across 35 tickers and produced no BUY or SELL_SHORT
candidate eligible for shadow/live action. The exported blocker report contains
498 blocked rows:

- 497 `NO_SIGNAL` / `RESEARCH_ONLY` rows.
- 1 `BUY` / `REJECTED_BY_OOD` row.
- 280 rows blocked by `probability_below_threshold`.
- 217 rows blocked by `target_before_stop_probability_below_threshold`.
- 1 row blocked by `ood_feature_rate_above_limit`.

This is not a training-sample failure. The generation passed the configured
minimum train, calibration, and development-holdout sample gates. The blocker
pattern is instead concentrated in signal-selection evidence: direction
probability, target-before-stop probability, and one OOD policy rejection.

## Blockers By Reason

| Blocker reason | Rows | Distinct tickers | Avg score | Max score | Avg expected return | Avg target-before-stop probability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `probability_below_threshold` | 280 | 35 | 0.4135 | 0.5397 | 0.0010 | 0.2080 |
| `target_before_stop_probability_below_threshold` | 217 | 35 | 0.4878 | 0.6429 | 0.0045 | 0.2890 |
| `ood_feature_rate_above_limit` | 1 | 1 | 0.6241 | 0.6241 | 0.1626 | 0.3589 |

Interpretation: the system is not simply rejecting everything because expected
return is negative. Several rows have positive expected-return estimates and
respectable composite scores, but target-before-stop probability remains below
the frozen `0.50` policy threshold, or direction probability remains below the
frozen `0.55` policy threshold.

## Blockers By Product Scope

| Product scope | Blocker reason | Rows | Distinct tickers | Avg score | Max score | Avg expected return | Avg target-before-stop probability |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `ORDINARY` | `probability_below_threshold` | 172 | 23 | 0.4070 | 0.4606 | -0.0005 | 0.2087 |
| `ORDINARY` | `target_before_stop_probability_below_threshold` | 150 | 23 | 0.4834 | 0.5466 | 0.0040 | 0.2898 |
| `LEVERAGED_INVERSE` | `probability_below_threshold` | 60 | 6 | 0.4214 | 0.5397 | 0.0013 | 0.2103 |
| `LEVERAGED_INVERSE` | `target_before_stop_probability_below_threshold` | 29 | 6 | 0.5107 | 0.6429 | 0.0105 | 0.2831 |
| `LEVERAGED_LONG` | `probability_below_threshold` | 28 | 4 | 0.4441 | 0.4965 | 0.0106 | 0.1946 |
| `LEVERAGED_LONG` | `target_before_stop_probability_below_threshold` | 28 | 4 | 0.4855 | 0.5243 | 0.0018 | 0.2915 |
| `INVERSE` | `probability_below_threshold` | 20 | 2 | 0.4034 | 0.4893 | -0.0006 | 0.2140 |
| `INVERSE` | `target_before_stop_probability_below_threshold` | 10 | 2 | 0.4937 | 0.5683 | 0.0022 | 0.2864 |
| `LEVERAGED_INVERSE` | `ood_feature_rate_above_limit` | 1 | 1 | 0.6241 | 0.6241 | 0.1626 | 0.3589 |

Interpretation: leveraged and inverse products are not being ignored. They have
some of the highest scores and expected-return estimates, but they are mostly
blocked by target-before-stop evidence or direction-probability evidence rather
than by product-scope policy alone.

## Blockers By Archetype

The heaviest direction-probability blockers are:

- Failed Move / Liquidity Trap Proxy: 44 rows, average score 0.4027.
- Reversal / Exhaustion: 44 rows, average score 0.4027.
- Breakout / Breakdown: 37 rows, average score 0.4200.
- Pullback Continuation: 37 rows, average score 0.4200.
- Trend Continuation: 37 rows, average score 0.4200.
- Volatility Expansion: 35 rows, average score 0.3981.

The heaviest target-before-stop blockers are:

- Breakout / Breakdown: 33 rows, average score 0.4968.
- Pullback Continuation: 33 rows, average score 0.4968.
- Sector Rotation: 33 rows, average score 0.5079.
- Trend Continuation: 33 rows, average score 0.4968.
- Failed Move / Liquidity Trap Proxy: 26 rows, average score 0.4523.
- Reversal / Exhaustion: 26 rows, average score 0.4523.
- Volatility Compression Release: 25 rows, average score 0.4981.

Interpretation: V1 is already testing multiple angles, but the latest snapshot
does not have enough measured support to convert those angles into selected
BUY/SELL candidates under the frozen policy.

## Highest-Scoring Blocked Rows

| Ticker | Scope | Action | Status | Blocker | Hypothesis | Score | Direction probability | Target-before-stop probability | Expected return | OOD feature rate |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| TZA | `LEVERAGED_INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `sector_rotation_buy_20d` | 0.6429 | 0.5804 | 0.3589 | 0.0869 | 0.0208 |
| SQQQ | `LEVERAGED_INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `sector_rotation_buy_20d` | 0.6415 | 0.5804 | 0.3521 | 0.0612 | 0.0208 |
| SOXS | `LEVERAGED_INVERSE` | `BUY` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` | `sector_rotation_buy_20d` | 0.6241 | 0.5804 | 0.3589 | 0.1626 | 0.2083 |
| SOXS | `LEVERAGED_INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `trend_continuation_sell_10d` | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.1875 |
| SOXS | `LEVERAGED_INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `pullback_continuation_sell_10d` | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.1875 |
| SOXS | `LEVERAGED_INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `breadth_deterioration_sell_10d` | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.1875 |
| SOXS | `LEVERAGED_INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `breakdown_sell_10d` | 0.5793 | 0.6196 | 0.2613 | 0.0361 | 0.1875 |
| RWM | `INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `sector_rotation_buy_20d` | 0.5683 | 0.5804 | 0.3589 | 0.0154 | 0.0208 |
| AMZN | `ORDINARY` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `sector_rotation_buy_20d` | 0.5466 | 0.5804 | 0.3947 | 0.0142 | 0.0208 |
| QID | `LEVERAGED_INVERSE` | `NO SIGNAL` | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` | `sector_rotation_buy_20d` | 0.5440 | 0.5804 | 0.3521 | 0.0181 | 0.0208 |

## TZA Readout

TZA's strongest latest row is not an actionable or shadow candidate. It is a
`NO_SIGNAL` / `RESEARCH_ONLY` row from `sector_rotation_buy_20d`.

- Signal score: 0.6429.
- Direction probability: 0.5804, above the default 0.55 direction threshold.
- Target-before-stop probability: 0.3589, below the default 0.50
  target-before-stop threshold.
- Expected return: 0.0869.
- Expected MFE: 0.4890.
- Expected MAE: -0.1306.
- OOD feature rate: 0.0208.

TZA also has a `risk_off_buy_inverse_10d` row with positive expected return
0.0407, but that row is blocked by direction probability 0.3653 and
target-before-stop probability 0.1717. The risk-off footprint is therefore
visible, but the current measured evidence is not strong enough to produce a
selected candidate under the frozen policy.

## OOD Finding

The single rejected row is SOXS under `sector_rotation_buy_20d`:

- Status: `REJECTED_BY_OOD`.
- Signal score: 0.6241.
- Direction probability: 0.5804.
- Target-before-stop probability: 0.3589.
- Expected return: 0.1626.
- OOD feature rate: 0.2083.

This should remain blocked. The high expected-return estimate is exactly why the
OOD warning matters; it is not a reason to weaken the OOD policy.

## Recommendation

Do not loosen thresholds, gates, OOD governance, product-class mappings, labels,
or feature definitions.

The next useful engineering move is to make blocker review easier inside the
dashboard and exports: show the same by-reason, by-hypothesis, by-archetype,
by-ticker, and by-scope blocker summaries next to Signal Discovery generation
status, with drilldowns into the highest-scoring blocked rows.

This is review tooling only. It should not change candidate selection,
promotion, final-holdout policy, scanner state, or paper-forward events.

## Data Leakage Review

- The review used persisted blocker exports from the latest development signal
  discovery generation.
- No model was retrained.
- No labels were moved into feature matrices.
- No threshold, gate, feature, label, product-class, or OOD policy was changed.
- No final-holdout, forward-update, scanner, daily-cycle, or discovery command
  was run during this review.
- The operational repository was not modified.

## Next Smallest Task

Add a read-only dashboard panel for Signal Discovery blockers using the existing
`signal_discovery_blocker_report_v1` export frames.
