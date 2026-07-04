# Signal Discovery Status

Repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

## Latest Generation

- latest generation ID: `signal_discovery_20260704T181757+0000_fa9987cfe9c2`
- this is the current `artifacts/signal_discovery/latest.json` generation
- created timestamp: `2026-07-04T18:17:57+00:00`
- latest decision date: `2026-07-02`
- hypotheses evaluated: 17
- BUY candidates: 0
- SELL/SHORT candidates: 0
- NO_SIGNAL rows: 516
- rejected rows: 28
- selected candidates: 0
- research-only rows: 516
- shadow-only rows: none separately identified in the export
- live actionable rows: 0
- all rows remain research/rejected only: yes

## Top Blockers

- `probability_below_threshold`: 329
- `target_before_stop_probability_below_threshold`: 177
- `expected_value_insufficient_after_cost`: 10
- `ood_feature_rate_above_limit`: 28 rejected rows

## Top Bullish Rows

| Ticker | Hypothesis | Score | TBS p | Status | Reason |
| --- | --- | ---: | ---: | --- | --- |
| AMD | `sector_rotation_buy_ordinary_20d_time_exit_utility_v1` | 0.691781 | 0.431830 | `RESEARCH_ONLY` | `target_before_stop_probability_below_threshold` |
| SH | `risk_off_buy_inverse_10d` | 0.614201 | 0.272997 | `RESEARCH_ONLY` | `probability_below_threshold` |
| RWM | `risk_off_buy_inverse_10d` | 0.609552 | 0.279213 | `RESEARCH_ONLY` | `probability_below_threshold` |
| SDS | `risk_off_buy_inverse_10d` | 0.598603 | 0.272997 | `RESEARCH_ONLY` | `probability_below_threshold` |
| SPXU | `risk_off_buy_inverse_10d` | 0.586769 | 0.279213 | `RESEARCH_ONLY` | `probability_below_threshold` |

## Top Bearish Rows

| Ticker | Hypothesis | Score | TBS p | Status | Reason |
| --- | --- | ---: | ---: | --- | --- |
| XLK | `trend_continuation_sell_10d` | 0.596392 | 0.298013 | `RESEARCH_ONLY` | `probability_below_threshold` |
| XLK | `pullback_continuation_sell_10d` | 0.596392 | 0.298013 | `RESEARCH_ONLY` | `probability_below_threshold` |
| XLK | `breakdown_sell_10d` | 0.596392 | 0.298013 | `RESEARCH_ONLY` | `probability_below_threshold` |
| XLK | `breadth_deterioration_sell_10d` | 0.596392 | 0.298013 | `RESEARCH_ONLY` | `probability_below_threshold` |
| UPRO | `breadth_deterioration_sell_10d` | 0.588205 | 0.316995 | `RESEARCH_ONLY` | `probability_below_threshold` |

## Sector Rotation BUY ORDINARY Time-Exit Rows

- row count: 23
- tickers: AAPL, AMD, AMZN, DIA, GOOGL, IWM, META, MSFT, NVDA, QQQ, SPY, TSLA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY
- all status: `RESEARCH_ONLY` / `NO_SIGNAL`
- all blocker: `target_before_stop_probability_below_threshold`
- all TBS probability: 0.431830
- all time-exit positive probability: 0.597391

Top Sector Rotation BUY ORDINARY time-exit rows:

| Ticker | Signal ID | Score | TBS p | Time-exit positive p | Expected return | Expected utility | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| AMD | `56107721aed3504110dc7ece` | 0.691781 | 0.431830 | 0.597391 | 0.047963 | 1.292267 | `RESEARCH_ONLY` |
| XLK | `47d35a0cb512866d1999bb01` | 0.487219 | 0.431830 | 0.597391 | -0.010481 | 1.159368 | `RESEARCH_ONLY` |
| XLV | `0fef4cb710d0f5ed6da52f05` | 0.466989 | 0.431830 | 0.597391 | -0.016145 | 1.105654 | `RESEARCH_ONLY` |
| META | `199441c69cd6ae85a6ee8508` | 0.463245 | 0.431830 | 0.597391 | -0.016610 | 1.111941 | `RESEARCH_ONLY` |
| NVDA | `bcda15f26853b5e77e5aba61` | 0.462748 | 0.431830 | 0.597391 | -0.017333 | 1.149285 | `RESEARCH_ONLY` |

AMD is present and is the top time-exit row.

## Interpretation

Latest signal discovery did not create BUY or SELL candidates. There are no live-actionable rows. The main blockers are probability and target-before-stop gates. Current state is gate-protection plus evidence collection, not a proven model-quality bug.

