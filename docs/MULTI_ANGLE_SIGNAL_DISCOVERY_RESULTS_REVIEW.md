# Multi-Angle Signal Discovery Results Review

Review date: 2026-06-28

Source: latest existing local `signal_discovery_generation` artifacts and exported reports only.

No discovery, scanner, final-holdout update, FMP update, retraining, promotion, SQLite mutation, or operational repository mutation was performed.

## Latest Generation

| Field | Value |
| --- | --- |
| Generation ID | `signal_discovery_20260628T193012+0000_cf2753a58c47` |
| Schema | `multi_angle_signal_discovery_v1` |
| Generation type | `signal_discovery_generation` |
| Created UTC | `2026-06-28T19:30:12+00:00` |
| Latest decision date | `2026-06-26` |
| Feature manifest | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| Universe snapshot | `6b1a74750684506e1a5b` |
| Hypotheses evaluated | 15 |
| Product scopes | `POOLED`, `ORDINARY`, `INVERSE`, `LEVERAGED_LONG`, `LEVERAGED_INVERSE` |
| Model families | `hist_gradient_boosting`, `extra_trees` |

## Candidate Counts

| Output | Count |
| --- | ---: |
| BUY candidates | 0 |
| SELL/SHORT candidates | 0 |
| NO_SIGNAL rows | 497 |
| Rejected rows | 1 |
| Shadow-only rows | 0 |
| Research-only rows | 497 |
| Rejected-by-OOD rows | 1 |
| Selected candidates | 0 |

## Top BUY-Side Rows By Score

No row passed as a selected `BUY_CANDIDATE`. The highest BUY-direction review rows were:

| Rank | Ticker | Action | Status | Archetype | Hypothesis | Score | Probability | TBS probability | Expected return | Blocker |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | TZA | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.642860 | 0.580449 | 0.358930 | 0.086911 | target-before-stop below threshold |
| 2 | SQQQ | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.641488 | 0.580449 | 0.352071 | 0.061243 | target-before-stop below threshold |
| 3 | SOXS | BUY | REJECTED_BY_OOD | Sector Rotation | `sector_rotation_buy_20d` | 0.624110 | 0.580449 | 0.358930 | 0.162623 | OOD feature rate above limit |
| 4 | RWM | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.568312 | 0.580449 | 0.358930 | 0.015431 | target-before-stop below threshold |
| 5 | AMZN | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.546596 | 0.580449 | 0.394651 | 0.014207 | target-before-stop below threshold |
| 6 | QID | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.543995 | 0.580449 | 0.352071 | 0.018066 | target-before-stop below threshold |
| 7 | XLE | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.536824 | 0.580449 | 0.358930 | 0.015290 | target-before-stop below threshold |
| 8 | SPXU | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.533714 | 0.580449 | 0.352071 | 0.013715 | target-before-stop below threshold |
| 9 | XLP | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.532562 | 0.580449 | 0.353828 | 0.015290 | target-before-stop below threshold |
| 10 | SDS | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | `sector_rotation_buy_20d` | 0.532100 | 0.580449 | 0.352071 | 0.007432 | target-before-stop below threshold |

## Top SELL/SHORT-Side Rows By Score

No row passed as a selected `SELL_SHORT_CANDIDATE`. The highest SELL/SHORT-direction review rows were:

| Rank | Ticker | Action | Status | Archetype | Hypothesis | Score | Probability | TBS probability | Expected return | Blocker |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | SOXS | NO SIGNAL | RESEARCH_ONLY | Breakout / Breakdown | `breakdown_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | target-before-stop below threshold |
| 2 | SOXS | NO SIGNAL | RESEARCH_ONLY | Trend Continuation | `trend_continuation_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | target-before-stop below threshold |
| 3 | SOXS | NO SIGNAL | RESEARCH_ONLY | Breadth Thrust / Breadth Deterioration | `breadth_deterioration_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | target-before-stop below threshold |
| 4 | SOXS | NO SIGNAL | RESEARCH_ONLY | Pullback Continuation | `pullback_continuation_sell_10d` | 0.579257 | 0.619632 | 0.261255 | 0.036110 | target-before-stop below threshold |
| 5 | SOXS | NO SIGNAL | RESEARCH_ONLY | Volatility Expansion | `volatility_expansion_sell_5d` | 0.539657 | 0.448905 | 0.146034 | 0.066307 | probability below threshold |
| 6 | SOXS | NO SIGNAL | RESEARCH_ONLY | Failed Move / Liquidity Trap Proxy | `failed_breakout_sell_5d` | 0.539657 | 0.448905 | 0.146034 | 0.066307 | probability below threshold |
| 7 | SOXS | NO SIGNAL | RESEARCH_ONLY | Reversal / Exhaustion | `reversal_sell_5d` | 0.539657 | 0.448905 | 0.146034 | 0.066307 | probability below threshold |
| 8 | SOXL | NO SIGNAL | RESEARCH_ONLY | Pullback Continuation | `pullback_continuation_sell_10d` | 0.496463 | 0.405461 | 0.226496 | 0.033614 | probability below threshold |
| 9 | SOXL | NO SIGNAL | RESEARCH_ONLY | Breadth Thrust / Breadth Deterioration | `breadth_deterioration_sell_10d` | 0.496463 | 0.405461 | 0.226496 | 0.033614 | probability below threshold |
| 10 | SOXL | NO SIGNAL | RESEARCH_ONLY | Breakout / Breakdown | `breakdown_sell_10d` | 0.496463 | 0.405461 | 0.226496 | 0.033614 | probability below threshold |

## Highest-Scoring Blockers

| Rank | Ticker | Scope | Action | Status | Archetype | Score | Expected return | OOD rate | Blocker |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | TZA | LEVERAGED_INVERSE | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | 0.642860 | 0.086911 | 0.020833 | target-before-stop below threshold |
| 2 | SQQQ | LEVERAGED_INVERSE | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | 0.641488 | 0.061243 | 0.020833 | target-before-stop below threshold |
| 3 | SOXS | LEVERAGED_INVERSE | BUY | REJECTED_BY_OOD | Sector Rotation | 0.624110 | 0.162623 | 0.208333 | OOD feature rate above limit |
| 4 | SOXS | LEVERAGED_INVERSE | NO SIGNAL | RESEARCH_ONLY | Trend Continuation | 0.579257 | 0.036110 | 0.187500 | target-before-stop below threshold |
| 5 | SOXS | LEVERAGED_INVERSE | NO SIGNAL | RESEARCH_ONLY | Pullback Continuation | 0.579257 | 0.036110 | 0.187500 | target-before-stop below threshold |
| 6 | SOXS | LEVERAGED_INVERSE | NO SIGNAL | RESEARCH_ONLY | Breadth Deterioration | 0.579257 | 0.036110 | 0.187500 | target-before-stop below threshold |
| 7 | SOXS | LEVERAGED_INVERSE | NO SIGNAL | RESEARCH_ONLY | Breakdown | 0.579257 | 0.036110 | 0.187500 | target-before-stop below threshold |
| 8 | RWM | INVERSE | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | 0.568312 | 0.015431 | 0.020833 | target-before-stop below threshold |
| 9 | AMZN | ORDINARY | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | 0.546596 | 0.014207 | 0.020833 | target-before-stop below threshold |
| 10 | QID | LEVERAGED_INVERSE | NO SIGNAL | RESEARCH_ONLY | Sector Rotation | 0.543995 | 0.018066 | 0.020833 | target-before-stop below threshold |

## Archetype Review

Top archetypes by row count:

| Archetype | Rows | Note |
| --- | ---: | --- |
| Breakout / Breakdown | 70 | All NO_SIGNAL |
| Failed Move / Liquidity Trap Proxy | 70 | All NO_SIGNAL |
| Pullback Continuation | 70 | All NO_SIGNAL |
| Reversal / Exhaustion | 70 | All NO_SIGNAL |
| Trend Continuation | 70 | All NO_SIGNAL |
| Breadth Thrust / Breadth Deterioration | 35 | All NO_SIGNAL |
| Volatility Compression Release | 35 | All NO_SIGNAL |
| Volatility Expansion | 35 | All NO_SIGNAL |
| Sector Rotation | 35 | 34 NO_SIGNAL, 1 REJECTED_BY_OOD |
| Risk-On / Risk-Off | 8 | All NO_SIGNAL |

Weakest archetypes by average score:

| Archetype | Rows | Average score | Max score |
| --- | ---: | ---: | ---: |
| Volatility Expansion | 35 | 0.398147 | 0.539657 |
| Failed Move / Liquidity Trap Proxy | 70 | 0.421106 | 0.539657 |
| Reversal / Exhaustion | 70 | 0.421106 | 0.539657 |
| Breadth Thrust / Breadth Deterioration | 35 | 0.441149 | 0.579257 |
| Breakout / Breakdown | 70 | 0.456161 | 0.579257 |

Strongest average archetype was Sector Rotation with 35 rows, average score 0.509827, and max score 0.642860, but it still produced no selected candidate.

## Rejection And Blocker Reasons

| Reason | Rows |
| --- | ---: |
| `probability_below_threshold` | 280 |
| `target_before_stop_probability_below_threshold` | 217 |
| `ood_feature_rate_above_limit` | 1 |

Model and gate blockers:

| Evidence | Result |
| --- | --- |
| Minimum training samples | 15 PASS |
| Minimum calibration samples | 15 PASS |
| Minimum holdout samples | 15 PASS |
| Hypothesis/model statuses | 28 `CANDIDATE` rows blocked by `final_holdout_required_for_promotion`; 2 `REJECTED` rows blocked by `expected_utility_insufficient` |

## Signal Score Components

The score is transparent; components are persisted in `score_components.csv`.

| Component | Rows | Average | Min | Max |
| --- | ---: | ---: | ---: | ---: |
| signal_score | 498 | 0.446295 | 0.335877 | 0.642860 |
| direction_probability | 498 | 0.494267 | 0.365320 | 0.619632 |
| target_before_stop_probability | 498 | 0.243582 | 0.140150 | 0.394651 |
| expected_return | 498 | 0.002829 | -0.089255 | 0.162623 |
| expected_return_after_cost | 498 | 0.002329 | -0.089755 | 0.162123 |
| expected_mfe | 498 | 0.072040 | 0.019676 | 0.489043 |
| expected_mae | 498 | -0.059175 | -0.299568 | -0.019790 |
| footprint_support_score | 498 | 0.401518 | 0.297885 | 0.592890 |
| liquidity_score | 498 | 0.985304 | 0.921712 | 1.000000 |
| ood_feature_rate | 498 | 0.029284 | 0.020833 | 0.208333 |
| conflict_penalty | 498 | 0.000000 | 0.000000 | 0.000000 |
| concentration_penalty | 498 | 0.000000 | 0.000000 | 0.000000 |

Formula:

```text
signal_score =
  0.35 * direction_probability
+ 0.20 * target_before_stop_probability
+ 0.20 * expected_return_score
+ 0.10 * expected_mfe_score
+ 0.08 * expected_mae_score
+ 0.07 * liquidity_score
- 0.10 * ood_penalty
- 0.05 * conflict_penalty
- 0.03 * concentration_penalty
```

## Footprint Summaries

Top scored rows had measured footprint text attached:

- TZA: `sector_rotation_buy_20d footprint incomplete or below policy threshold`; support included sector-relative and market-relative evidence.
- SQQQ: `sector_rotation_buy_20d footprint incomplete or below policy threshold`; support included sector-relative and market-relative evidence.
- SOXS rejected BUY row: `sector_rotation_buy_20d rejected by discovery policy`; support included sector-relative and market-relative evidence.
- SOXS bearish rows: trend, pullback, breadth deterioration, and breakdown footprints were present but below policy thresholds.

Top conflict fields were unavailable in the current generation for the leading rows, so no conflicting-evidence claim should be treated as confirmed.

## Historical Analogs

Historical analog file rows: 0.

Reason: analog rows are currently emitted for selected BUY/SELL candidates. This generation selected no BUY or SELL/SHORT candidates, so there are no analog examples to report. The dashboard correctly displays historical analog support as explanatory-only and unavailable unless selection exists.

## Blocker Open Links

The blocker panel's highest-scoring row now resolves correctly to Candidate Detail.

Example generated link:

```text
/candidate-detail?scan_id=signal_discovery_20260628T193012%2B0000_cf2753a58c47&ticker=TZA&model_id=sector_rotation_buy_20d%3Ahist_gradient_boosting&direction=Bullish&status=RESEARCH_ONLY
```

Resolution check:

- Query generation ID: `signal_discovery_20260628T193012+0000_cf2753a58c47`
- Query ticker: `TZA`
- Query model ID: `sector_rotation_buy_20d:hist_gradient_boosting`
- Query direction: `Bullish`
- Matching Candidate Detail row count: 1

## Dashboard Pages Updated

- Signal Board: shows discovery rows with action, archetype, score, footprint summary, support/conflict, analog support, edge status, candidate status, and next event.
- Candidate Detail: shows signal score breakdown, footprint evidence, raw identifiers, and deep links.
- Reports and Exports: exports signal discovery generation data and shows the blocker review panel with Candidate Detail links.

## Export Files Available

Latest export directory: `reports/signal_discovery_v1/`

Files:

- `metadata.json`
- `summary.csv`
- `hypotheses.csv`
- `candidates.csv`
- `selected_candidates.csv`
- `no_signal.csv`
- `rejected.csv`
- `footprint_evidence.csv`
- `historical_analogs.csv`
- `score_components.csv`
- `gate_results.csv`

## Current Best Candidate

There is no selected BUY or SELL/SHORT candidate.

The strongest review row is TZA under `sector_rotation_buy_20d`, with score 0.642860 and expected return 0.086911, but it is `NO_SIGNAL / RESEARCH_ONLY` because target-before-stop probability is 0.358930, below the frozen policy threshold.

The strongest rejected row is SOXS under `sector_rotation_buy_20d`, with score 0.624110 and expected return 0.162623, but it is `REJECTED_BY_OOD` because OOD feature rate is 0.208333.

## Why Nothing Is Live Actionable Yet

Nothing is live actionable because:

- no BUY or SELL/SHORT row passed selection;
- no promoted multi-angle signal model exists;
- final-holdout evidence is still required for promotion;
- most rows are blocked by direction probability or target-before-stop probability;
- the one apparent BUY row is rejected by OOD policy;
- gates and thresholds were not weakened.

## Operational Immutability Proof

Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

| Check | Before | After |
| --- | --- | --- |
| HEAD | `3f3c4f8 docs: add nonlinear model quality diagnosis` | `3f3c4f8 docs: add nonlinear model quality diagnosis` |
| Git status | clean on `feat/autonomous-swing-scanner-v1` | clean on `feat/autonomous-swing-scanner-v1` |
| SQLite SHA256 | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |
| Scanner snapshots | 18 | 18 |
| Scanner candidates | 875 | 875 |
| Forward events | 310 | 310 |
| Final-holdout runs | 1 | 1 |

No operational code, SQLite rows, artifacts, scanner state, forward state, or final-holdout state were modified.

## Next Task

Add historical analog examples for the top blocked research rows in a read-only diagnostic mode, clearly marked explanatory-only and not used for selection or promotion.

## Plain-English Summary

1. What the scanner currently found: it found several high-scoring research footprints, especially sector-rotation and inverse/leveraged inverse setups such as TZA, SQQQ, and SOXS.
2. What it rejected: it rejected one SOXS BUY row because the OOD feature rate was too high, and it held 497 rows at NO_SIGNAL.
3. What looks promising: TZA and SQQQ sector-rotation BUY-direction rows have the strongest scores, but they remain research-only.
4. What is still blocking live signals: target-before-stop probability, direction probability, OOD governance, missing final-holdout evidence, and no promoted multi-angle model.
5. What single thing should improve next: add read-only historical analog diagnostics for top blocked rows so reviewers can see similar past footprints without changing selection, gates, or promotion policy.
