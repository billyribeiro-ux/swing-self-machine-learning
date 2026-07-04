# Operational Final-Holdout Status

Repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

## Run Identity

- run ID: `3493ee8ac37bf96475c362e1`
- enrolled model ID: `b93b2258c10aea5cef81d291`
- run status: `COLLECTING`
- model state at enrollment: `CANDIDATE`
- baseline market date: `2026-06-25`
- first eligible future signal date: `2026-06-26`
- latest processed market date: `2026-07-02`
- latest local data date: `2026-07-02`
- feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- artifact hash: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- artifact integrity status: `PASS`
- promotion eligibility: false

## Data Rows

- feature rows: 90,288
- label rows: 90,288
- modeling rows: 90,288

## Event State

- total final-holdout event count: 125
- event count by type:
  - `FINAL_HOLDOUT_SIGNAL_REJECTED`: 125
- signals created: 0
- rejected signals: 125
- accepted signals: 0
- pending entries: 0
- open positions: 0
- closed positions: 0
- matured outcomes: 0
- provenance failures: 0 observed
- blocked backfills: 0
- invalidated outcomes: 0

## July 2 Advance Breakdown

Events added by the July 2 data advance:

| Session | Events added | Event types |
| --- | ---: | --- |
| 2026-06-29 | 25 | all `FINAL_HOLDOUT_SIGNAL_REJECTED` |
| 2026-06-30 | 25 | all `FINAL_HOLDOUT_SIGNAL_REJECTED` |
| 2026-07-01 | 25 | all `FINAL_HOLDOUT_SIGNAL_REJECTED` |
| 2026-07-02 | 25 | all `FINAL_HOLDOUT_SIGNAL_REJECTED` |

All 100 events added by the July 2 advance were `FINAL_HOLDOUT_SIGNAL_REJECTED`.

Rejection reasons by session:

| Session | Rejection reason | Count |
| --- | --- | ---: |
| 2026-06-29 | `below_target_before_stop_threshold` | 4 |
| 2026-06-29 | `below_probability_threshold;below_target_before_stop_threshold` | 3 |
| 2026-06-29 | `below_expected_return_threshold;below_target_before_stop_threshold` | 16 |
| 2026-06-29 | `below_probability_threshold;below_expected_return_threshold;below_target_before_stop_threshold` | 2 |
| 2026-06-30 | `below_target_before_stop_threshold` | 3 |
| 2026-06-30 | `below_probability_threshold;below_target_before_stop_threshold` | 4 |
| 2026-06-30 | `below_expected_return_threshold;below_target_before_stop_threshold` | 14 |
| 2026-06-30 | `below_probability_threshold;below_expected_return_threshold;below_target_before_stop_threshold` | 4 |
| 2026-07-01 | `below_target_before_stop_threshold` | 4 |
| 2026-07-01 | `below_probability_threshold;below_target_before_stop_threshold` | 3 |
| 2026-07-01 | `below_expected_return_threshold;below_target_before_stop_threshold` | 14 |
| 2026-07-01 | `below_probability_threshold;below_expected_return_threshold;below_target_before_stop_threshold` | 4 |
| 2026-07-02 | `below_target_before_stop_threshold` | 3 |
| 2026-07-02 | `below_probability_threshold;below_target_before_stop_threshold` | 4 |
| 2026-07-02 | `below_expected_return_threshold;below_target_before_stop_threshold` | 13 |
| 2026-07-02 | `below_probability_threshold;below_expected_return_threshold;below_target_before_stop_threshold` | 5 |

Tickers involved in the July 2 advance:

- `2026-06-29`: DIA, IWM, META, MSFT, QID, QQQ, RWM, SDS, SH, SOXS, SPXU, SPY, SQQQ, TNA, TZA, XLB, XLC, XLE, XLF, XLI, XLP, XLRE, XLU, XLV, XLY
- `2026-06-30`: DIA, IWM, META, NVDA, QID, QQQ, RWM, SDS, SH, SOXS, SPXU, SPY, SQQQ, TZA, UPRO, XLB, XLC, XLE, XLF, XLI, XLP, XLRE, XLU, XLV, XLY
- `2026-07-01`: AAPL, DIA, IWM, META, MSFT, NVDA, QID, RWM, SDS, SH, SOXS, SPXU, SPY, SQQQ, TZA, XLB, XLC, XLE, XLF, XLI, XLP, XLRE, XLU, XLV, XLY
- `2026-07-02`: AAPL, DIA, IWM, META, MSFT, NVDA, QID, RWM, SDS, SH, SOXS, SPXU, SPY, SQQQ, TZA, XLB, XLC, XLE, XLF, XLI, XLP, XLRE, XLU, XLV, XLY

Pending/open/matured remain zero because every evaluated operational final-holdout row was rejected by gates. No operational entry became pending, no entry filled, and no position matured.

## Remaining Sample Requirements

The run still needs prospective evidence before promotion can be considered:

- early diagnostic matured outcomes minimum: 30
- stronger matured outcomes minimum: 100
- early distinct signal dates minimum: 20
- stronger distinct signal dates minimum: 60
- observation sessions minimum: 126
- calendar months minimum: 4
- positive class minimum: 20
- negative class minimum: 20

Current matured outcomes: 0.

## Status Conclusion

The operational run is healthy and append-only. Nothing is accepted, nothing is actionable, and promotion is not eligible.

Next valid operational command: after the next completed regular market session is locally available, run `universe-update`, `build-features`, `final-holdout-update`, and `final-holdout-status` in the operational repo.

