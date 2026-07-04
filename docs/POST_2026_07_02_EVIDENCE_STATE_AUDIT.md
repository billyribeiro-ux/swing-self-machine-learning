# Post 2026-07-02 Evidence-State Audit

Date run: 2026-07-04

This audit is read-only after committing the July 2 data-advance status report.
No source code, SQLite rows, model artifacts, scanner state, forward state,
final-holdout state, thresholds, gates, OOD governance, FMP data, discovery
state, or dashboard state were changed by the audit itself.

## July 2 Report Commit

- committed report:
  `docs/DATA_ADVANCE_TO_2026_07_02_STATUS.md`
- commit hash:
  `105ac87d9c82ddf717a232b28eb8a1976e738b79`
- commit message:
  `docs: add data advance to july 2 status report`
- pushed branch:
  `feat/product-class-specialist-challengers-v1`

## Operational Final-Holdout Event Audit

Repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Run:
`3493ee8ac37bf96475c362e1`

Model:
`b93b2258c10aea5cef81d291`

### Run And Model State

- run status: `COLLECTING`
- model status from final-holdout status view: `COLLECTING`
- model state at enrollment: `CANDIDATE`
- baseline date: `2026-06-25`
- first eligible future signal date: `2026-06-26`
- latest processed market date: `2026-07-02`
- artifact integrity status: `PASS`
- promotion eligibility: false
- enrolled model artifact hash:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`

### Event Counts

- reconstructable final-holdout event count before July 2 update: 25
- current final-holdout event count: 125
- events added by July 2 update: 100
- all final-holdout events after update:
  - `FINAL_HOLDOUT_SIGNAL_REJECTED`: 125

The 100 inserted events are exactly 25 rejected shadow validation rows for each
of four processed sessions. They are append-only event rows. No prior events
were rewritten.

### Events Added By Session

| Session | Events | Signal created | Signal rejected | Entry pending | Entry filled | Position marked | Exit filled | Position expired | Backfill blocked | Data invalidated | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-06-29 | 25 | 0 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-06-30 | 25 | 0 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-07-01 | 25 | 0 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-07-02 | 25 | 0 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Tickers Involved

- `2026-06-29`: DIA, IWM, META, MSFT, QID, QQQ, RWM, SDS, SH,
  SOXS, SPXU, SPY, SQQQ, TNA, TZA, XLB, XLC, XLE, XLF, XLI, XLP,
  XLRE, XLU, XLV, XLY
- `2026-06-30`: DIA, IWM, META, NVDA, QID, QQQ, RWM, SDS, SH,
  SOXS, SPXU, SPY, SQQQ, TZA, UPRO, XLB, XLC, XLE, XLF, XLI, XLP,
  XLRE, XLU, XLV, XLY
- `2026-07-01`: AAPL, DIA, IWM, META, MSFT, NVDA, QID, RWM, SDS,
  SH, SOXS, SPXU, SPY, SQQQ, TZA, XLB, XLC, XLE, XLF, XLI, XLP,
  XLRE, XLU, XLV, XLY
- `2026-07-02`: AAPL, DIA, IWM, META, MSFT, NVDA, QID, RWM, SDS,
  SH, SOXS, SPXU, SPY, SQQQ, TZA, XLB, XLC, XLE, XLF, XLI, XLP,
  XLRE, XLU, XLV, XLY

### Rejection Reasons

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

### Operational Interpretation

- accepted final-holdout signals for the four new sessions: 0
- pending entries created for the four new sessions: 0
- entries filled for the four new sessions: 0
- position marks: 0
- exits / expirations: 0
- backfill-blocked events: 0
- data-invalidated events: 0

Pending/open/matured are all zero in the operational final-holdout status
because every evaluated row for the processed dates was rejected. No
`FINAL_HOLDOUT_SIGNAL_CREATED`, `FINAL_HOLDOUT_ENTRY_PENDING`, or
`FINAL_HOLDOUT_ENTRY_FILLED` event exists for the new sessions.

No operational bug detected.

## Development Final-Holdout Invalidation Audit

Repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Run:
`d25d6fa11a2e50daa430c15e`

### Invalidation Facts

- original enrolled code commit:
  `8e2b40effab1332f474ca47d720fcb8c21ca4912`
- current development commit at audit:
  `105ac87d9c82ddf717a232b28eb8a1976e738b79`
- exact mismatch:
  `8e2b40effab1332f474ca47d720fcb8c21ca4912 != 105ac87d9c82ddf717a232b28eb8a1976e738b79`
- run status: `INVALIDATED`
- invalidation reason: `code commit hash changed since enrollment`
- latest processed market date remains: `2026-06-26`
- event types:
  - `FINAL_HOLDOUT_SIGNAL_CREATED`: 1
  - `FINAL_HOLDOUT_ENTRY_PENDING`: 1
  - `FINAL_HOLDOUT_SIGNAL_REJECTED`: 24
  - `FINAL_HOLDOUT_DATA_INVALIDATED`: 4

### Invalidation Events

| Market date | Event type | Event ID | Timestamp UTC | Reason |
| --- | --- | --- | --- | --- |
| 2026-06-29 | `FINAL_HOLDOUT_DATA_INVALIDATED` | `bc77733b0893a7208617358c` | `2026-07-04T18:13:49.162277+00:00` | code commit hash changed since enrollment |
| 2026-06-30 | `FINAL_HOLDOUT_DATA_INVALIDATED` | `4cf384958eaf8174240ac3a3` | `2026-07-04T18:13:50.582104+00:00` | code commit hash changed since enrollment |
| 2026-07-01 | `FINAL_HOLDOUT_DATA_INVALIDATED` | `9bb40623c0fc620c4a595bd7` | `2026-07-04T18:13:51.999438+00:00` | code commit hash changed since enrollment |
| 2026-07-02 | `FINAL_HOLDOUT_DATA_INVALIDATED` | `101184c317f351f803e595de` | `2026-07-04T18:13:53.444537+00:00` | code commit hash changed since enrollment |

### Pending TZA Entry

The historical TZA events remain visible:

| Event type | Event ID | Market date | Ticker | Notes |
| --- | --- | --- | --- | --- |
| `FINAL_HOLDOUT_SIGNAL_CREATED` | `2acdbdee5fb355bc94566f9a` | 2026-06-26 | TZA | calibrated probability 0.576112; expected return 0.022294; horizon 10 |
| `FINAL_HOLDOUT_ENTRY_PENDING` | `b75bad88ada4dd671a60e514` | 2026-06-26 | TZA | entry rule `next_completed_session_open` |

No prior events were rewritten. The run should remain `INVALIDATED` as
append-only evidence. It should not be repaired or reinitialized as part of
this audit.

No development final-holdout bug detected.

## Time-Exit Diagnostic Ledger Audit

Repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Run:
`0e5facd1e8a164df2b586f64`

### Run State

- run status: `CREATED`
- baseline date: `2026-06-26`
- first eligible future as-of date: `None`
- source generation frozen at initialization:
  `signal_discovery_20260704T155444+0000_ed38c60cf1ad`
- latest processed market date from status view: `2026-07-02`
- schema: `prospective_time_exit_diagnostic_v1`
- hypothesis:
  `sector_rotation_buy_ordinary_20d_time_exit_utility_v1`
- product scope: `ORDINARY`
- horizon: 20 sessions

### Event Counts

| Event type | Count |
| --- | ---: |
| `DIAGNOSTIC_OBSERVATION_CREATED` | 23 |
| `DIAGNOSTIC_ENTRY_PENDING` | 23 |
| `DIAGNOSTIC_BACKFILL_BLOCKED` | 23 |

Status counts:

- observations created: 23
- rejected observations: 0
- pending entries: 23
- open diagnostic positions: 0
- matured outcomes: 0
- backfill-blocked events: 23

The apparent ambiguity is expected:

- 23 accepted observations are from the new `2026-07-02` generation rows.
- 23 pending entries correspond one-for-one with those 23 accepted observations.
- 23 backfill-blocked rows are separate rows from `2026-06-26`, which is equal
  to the ledger baseline and therefore not eligible for prospective insertion.

### Accepted Observations

Every accepted observation has as-of date `2026-07-02`, which is greater than
the `2026-06-26` baseline.

| Ticker | Signal ID | TBS p | Time-exit positive p | Expected time-exit return | Expected utility | Pending event ID | Planned entry date |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| AAPL | `79b03aa7f27f6d0cc7f09d9f` | 0.431830 | 0.597391 | -0.018122 | 1.151776 | `9a1015c64e5550bb68e746c8` | not locally available |
| AMD | `56107721aed3504110dc7ece` | 0.431830 | 0.597391 | 0.047963 | 1.292267 | `5a23e06e82e16316c27d7dea` | not locally available |
| AMZN | `b1059e36d73958b7f39087cd` | 0.431830 | 0.597391 | -0.024224 | 1.063706 | `f3bd3b8d6bc0fa5513663497` | not locally available |
| DIA | `94a55020db0006796bcf445d` | 0.431830 | 0.597391 | -0.028970 | 1.105654 | `0be4357ec2084f2dba9c6d49` | not locally available |
| GOOGL | `63928b85569dafec8c872239` | 0.431830 | 0.597391 | -0.022474 | 1.066197 | `9ecd2cf6658d2e0d52f285ef` | not locally available |
| IWM | `18cb47d6b39b5e938624c7e5` | 0.431830 | 0.597391 | -0.027065 | 1.055093 | `e4be49dba9caf3d204a14562` | not locally available |
| META | `199441c69cd6ae85a6ee8508` | 0.431830 | 0.597391 | -0.016610 | 1.111941 | `3771e368fc5e8e786755de56` | not locally available |
| MSFT | `4f3dbf2b985887e9b585c437` | 0.431830 | 0.597391 | -0.018514 | 1.063706 | `fed3e1a6da1d6e43954a3763` | not locally available |
| NVDA | `bcda15f26853b5e77e5aba61` | 0.431830 | 0.597391 | -0.017333 | 1.149285 | `e678906054c4719c75ad09ac` | not locally available |
| QQQ | `5e9e52b57b5114bb97b75c9c` | 0.431830 | 0.597391 | -0.028259 | 1.066197 | `8f972ede125d11f097597d13` | not locally available |
| SPY | `7e09fdec8314d675fa9057db` | 0.431830 | 0.597391 | -0.031966 | 1.063706 | `7e93715294e3a8a22c2ea514` | not locally available |
| TSLA | `8ddb55c4a1ed50e86c0dc43d` | 0.431830 | 0.597391 | -0.020945 | 1.103327 | `07bded6d2756e7cc3abd5b79` | not locally available |
| XLB | `2f18c0520561e29eb84455a5` | 0.431830 | 0.597391 | -0.021394 | 1.061216 | `d3ee7dd19da82091789845f9` | not locally available |
| XLC | `bc5f81fe4015112a9d98c1a1` | 0.431830 | 0.597391 | -0.028910 | 1.072320 | `ca73ff106a7070e24574d853` | not locally available |
| XLE | `ab6f31e75f62dbf9af3472e3` | 0.431830 | 0.597391 | -0.028425 | 1.081122 | `cfa764ed131fa208b477a8a5` | not locally available |
| XLF | `f8102d446d5880ab31a88498` | 0.431830 | 0.597391 | -0.030986 | 1.105654 | `0a866dbaf9e720ad6bc4588f` | not locally available |
| XLI | `950eb0c6b8e74025b0dbd6fe` | 0.431830 | 0.597391 | -0.026320 | 1.052602 | `9f5dedd91b0e8fd165f20c6d` | not locally available |
| XLK | `47d35a0cb512866d1999bb01` | 0.431830 | 0.597391 | -0.010481 | 1.159368 | `577f160670a4021d04f576ad` | not locally available |
| XLP | `8cb88425b4855e60930b3a2a` | 0.431830 | 0.597391 | -0.027049 | 1.061216 | `d5d47725c915a48004ed1556` | not locally available |
| XLRE | `db5f8c04463c2e35f0221143` | 0.431830 | 0.597391 | -0.027049 | 1.061216 | `e7c237b39e75b8bfea5defb0` | not locally available |
| XLU | `4e470f44ec16d1c9f0ac6926` | 0.431830 | 0.597391 | -0.028217 | 1.061216 | `42e434bbf683846e9577ab87` | not locally available |
| XLV | `0fef4cb710d0f5ed6da52f05` | 0.431830 | 0.597391 | -0.016145 | 1.105654 | `9876fe94b9ba2040f6d6fb80` | not locally available |
| XLY | `b9441e826f371384bba256e5` | 0.431830 | 0.597391 | -0.028910 | 1.072320 | `9131ac9c3668378879915ed7` | not locally available |

The planned entry date is not materialized yet because the next completed local
session after `2026-07-02` is not present in local data. Given the observed
July 3 market holiday and the weekend, the next expected eligible session is
`2026-07-06`, once that session exists locally.

### Backfill-Blocked Rows

Every blocked row has as-of date `2026-06-26`, which is `<=` the baseline date
`2026-06-26`.

Blocked tickers: AAPL, AMD, AMZN, DIA, GOOGL, IWM, META, MSFT, NVDA, QQQ, SPY,
TSLA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY.

- reason: `DIAGNOSTIC_BACKFILL_BLOCKED`
- blocked rows after baseline: 0

### Pending Entries

Every accepted observation has exactly one pending entry. No duplicate pending
entries exist. Pending entries use `next_completed_session_open`.

- pending entries: 23
- entry fills: 0
- matured outcomes: 0

No matured outcome exists because the 20-session horizon has not elapsed and no
entry has filled yet.

No time-exit diagnostic bug detected.

## New Signal-Discovery Generation Audit

Generation:
`signal_discovery_20260704T181757+0000_fa9987cfe9c2`

- created at: `2026-07-04T18:17:57+00:00`
- latest decision date: `2026-07-02`
- hypotheses evaluated: 17
- BUY candidates: 0
- SELL/SHORT candidates: 0
- NO_SIGNAL rows: 516
- rejected rows: 28
- selected candidates: 0
- live actionable rows: 0
- all rows remain research/shadow/rejected only: yes

### Top Blockers

- `probability_below_threshold`: 329
- `target_before_stop_probability_below_threshold`: 177
- `expected_value_insufficient_after_cost`: 10
- `ood_feature_rate_above_limit`: 28 rejected rows

### Top BUY Rows

| Ticker | Hypothesis | Score | TBS p | Decision | Status | Reason |
| --- | --- | ---: | ---: | --- | --- | --- |
| SOXS | `reversal_buy_5d` | 0.456095 | 0.167834 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXS | `failed_breakdown_buy_5d` | 0.456095 | 0.167834 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `reversal_buy_5d` | 0.422256 | 0.167834 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `failed_breakdown_buy_5d` | 0.422256 | 0.167834 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `trend_continuation_buy_10d` | 0.412681 | 0.308151 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |

### Top SELL Rows

| Ticker | Hypothesis | Score | TBS p | Decision | Status | Reason |
| --- | --- | ---: | ---: | --- | --- | --- |
| SOXL | `trend_continuation_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `breakdown_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `pullback_continuation_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `breadth_deterioration_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXS | `trend_continuation_sell_10d` | 0.531998 | 0.236962 | `REJECTED_BY_OOD` | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |

### Sector Rotation BUY ORDINARY Time-Exit Rows

- row count: 23
- tickers: AMD, XLK, XLV, META, NVDA, AAPL, MSFT, XLE, XLU, XLP, XLI,
  XLF, XLY, IWM, GOOGL, AMZN, XLC, XLB, SPY, QQQ, DIA, TSLA, XLRE
- all status: `RESEARCH_ONLY` / `NO_SIGNAL`
- all blocker: `target_before_stop_probability_below_threshold`
- all TBS probability: 0.431830
- all time-exit positive probability: 0.597391

Verified top row:

- ticker: AMD
- signal ID: `56107721aed3504110dc7ece`
- signal score: 0.691781
- TBS probability: 0.431830
- time-exit positive probability: 0.597391
- expected time-exit return: 0.047963
- expected time-exit utility: 1.292267
- blocker: `target_before_stop_probability_below_threshold`
- status: `RESEARCH_ONLY` / `NO_SIGNAL`

No signal-discovery bug detected.

## Dashboard Expected State

This is expected display only. The dashboard was not run during this audit.

### Signal Board

Expected development display:

- latest market date: `2026-07-02`
- live actionable count: 0
- shadow/paper count: 0 development final-holdout active rows, because the
  development final-holdout run is invalidated
- final-holdout pending entries: historical TZA pending entry remains visible
  in event history, but the run is invalidated
- open positions: 0
- matured outcomes: 0
- time-exit diagnostic observations: 23
- time-exit diagnostic pending entries: 23
- time-exit diagnostic open positions: 0
- time-exit diagnostic matured outcomes: 0
- regime cache status: `HIT`
- no live actionable signal should be displayed

Expected operational display if pointed at operational state:

- latest market date: `2026-07-02`
- final-holdout run: `COLLECTING`
- final-holdout accepted signals/pending/open/matured for the new sessions:
  `0 / 0 / 0 / 0`
- rejected final-holdout events: 125 total

### Shadow Forward Test

Expected operational summary:

- run `3493ee8ac37bf96475c362e1`
- status `COLLECTING`
- baseline `2026-06-25`
- latest processed `2026-07-02`
- event count 125
- matured outcomes 0
- promotion eligible false

Expected development summary:

- run `d25d6fa11a2e50daa430c15e`
- status `INVALIDATED`
- invalidation reason `code commit hash changed since enrollment`
- historical TZA pending event remains visible
- no repair or reinitialization should be implied

Time-exit diagnostic, if displayed:

- run `0e5facd1e8a164df2b586f64`
- observations 23
- pending entries 23
- open positions 0
- matured outcomes 0
- backfill-blocked 23
- diagnostic only, not live and not final-holdout evidence

### Candidate Detail

The AMD time-exit row should be openable from the latest signal-discovery
generation using signal ID `56107721aed3504110dc7ece`.

Candidate Detail should show:

- Sector Rotation BUY ORDINARY time-exit utility evidence
- TBS probability 0.431830
- time-exit positive probability 0.597391
- expected time-exit return 0.047963
- expected time-exit utility 1.292267
- `RESEARCH_ONLY` / `NO_SIGNAL`
- prospective time-exit diagnostic observation and pending-entry evidence
- diagnostic-only warning

## Immutability Proof

The audit itself did not run update/discovery/scanner/dashboard commands and did
not mutate SQLite or artifacts. Before and after values for the read-only audit
were identical. The only new workspace change after the audit is this requested
uncommitted markdown report.

### Development

| Field | Before audit | After audit |
| --- | --- | --- |
| git status | `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1` | same, plus untracked `docs/POST_2026_07_02_EVIDENCE_STATE_AUDIT.md` after report creation |
| SQLite size | 386064384 | 386064384 |
| SQLite mtime ns | 1783190123159191345 | 1783190123159191345 |
| scanner snapshot count | 4 | 4 |
| forward-event count | 30 | 30 |
| final-holdout run count | 1 | 1 |
| final-holdout event count | 30 | 30 |
| time-exit diagnostic event count | 69 | 69 |

### Operational

| Field | Before audit | After audit |
| --- | --- | --- |
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | same |
| git status | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` | same |
| SQLite hash | `0f1f91478b544ba3de62e1eccdc5a735eb3719593d03fee8ba26f0c52c151d6c` | same |
| enrolled model artifact hash | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` | same |
| scanner snapshot count | 22 | 22 |
| ordinary forward-event count | 285 | 285 |
| final-holdout event count | 125 | 125 |
| prospective run ID | `3493ee8ac37bf96475c362e1` | same |
| baseline date | `2026-06-25` | same |

## Next Commands

Exact next operational command after the next completed session is locally
available:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
.venv/bin/python -m swing_rsi.cli universe-update
```

Exact next development command after the next completed session is locally
available:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/python -m swing_rsi.cli universe-update
```

Do not run promotion, gate changes, threshold changes, OOD changes,
discover-models, scanner, forward-update, daily-cycle, or diagnostic update
until the next data-advance step explicitly calls for them.

## Bug Statement

No bug detected in:

- operational final-holdout event insertion;
- development final-holdout invalidation behavior;
- time-exit diagnostic backfill blocking;
- time-exit diagnostic pending-entry creation;
- latest signal-discovery generation classification.

One operational caveat remains intentional governance behavior: the development
shadow final-holdout run is invalidated and should remain invalidated evidence
unless a separate explicit task enrolls a new run under the current code commit.
