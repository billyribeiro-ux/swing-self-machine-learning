# Time-Exit Diagnostic Status

Repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

## Run Identity

- run ID: `0e5facd1e8a164df2b586f64`
- schema: `prospective_time_exit_diagnostic_v1`
- status: `CREATED`
- baseline market date: `2026-06-26`
- first eligible future as-of date: not materialized in the run row
- source generation: `signal_discovery_20260704T155444+0000_ed38c60cf1ad`
- latest processed market date: `2026-07-02`
- hypothesis: `sector_rotation_buy_ordinary_20d_time_exit_utility_v1`
- product scope: `ORDINARY`
- horizon: 20 sessions

## Event Counts

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
- invalidated events: 0

## Ambiguity Resolution

- The 23 accepted observations are all dated `2026-07-02`, which is after the `2026-06-26` baseline.
- The 23 pending entries correspond one-for-one with those accepted observations.
- The 23 backfill-blocked rows are separate rows dated `2026-06-26`, equal to the ledger baseline, and therefore correctly blocked by the no-backfill rule.
- No post-baseline row was incorrectly blocked.
- No baseline-or-earlier row was incorrectly accepted.
- No duplicate pending entries were detected.

Matured outcomes are expected to remain zero right now because no diagnostic entry has filled and the 20-session horizon has not elapsed.

## Accepted Observations

| Signal ID | As-of date | Ticker | TBS p | Time-exit positive p | Expected return | Expected utility | Pending entry event ID | Planned entry date |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `79b03aa7f27f6d0cc7f09d9f` | 2026-07-02 | AAPL | 0.431830 | 0.597391 | -0.018122 | 1.151776 | `9a1015c64e5550bb68e746c8` | not materialized |
| `56107721aed3504110dc7ece` | 2026-07-02 | AMD | 0.431830 | 0.597391 | 0.047963 | 1.292267 | `5a23e06e82e16316c27d7dea` | not materialized |
| `b1059e36d73958b7f39087cd` | 2026-07-02 | AMZN | 0.431830 | 0.597391 | -0.024224 | 1.063706 | `f3bd3b8d6bc0fa5513663497` | not materialized |
| `94a55020db0006796bcf445d` | 2026-07-02 | DIA | 0.431830 | 0.597391 | -0.028970 | 1.105654 | `0be4357ec2084f2dba9c6d49` | not materialized |
| `63928b85569dafec8c872239` | 2026-07-02 | GOOGL | 0.431830 | 0.597391 | -0.022474 | 1.066197 | `9ecd2cf6658d2e0d52f285ef` | not materialized |
| `18cb47d6b39b5e938624c7e5` | 2026-07-02 | IWM | 0.431830 | 0.597391 | -0.027065 | 1.055093 | `e4be49dba9caf3d204a14562` | not materialized |
| `199441c69cd6ae85a6ee8508` | 2026-07-02 | META | 0.431830 | 0.597391 | -0.016610 | 1.111941 | `3771e368fc5e8e786755de56` | not materialized |
| `4f3dbf2b985887e9b585c437` | 2026-07-02 | MSFT | 0.431830 | 0.597391 | -0.018514 | 1.063706 | `fed3e1a6da1d6e43954a3763` | not materialized |
| `bcda15f26853b5e77e5aba61` | 2026-07-02 | NVDA | 0.431830 | 0.597391 | -0.017333 | 1.149285 | `e678906054c4719c75ad09ac` | not materialized |
| `5e9e52b57b5114bb97b75c9c` | 2026-07-02 | QQQ | 0.431830 | 0.597391 | -0.028259 | 1.066197 | `8f972ede125d11f097597d13` | not materialized |
| `7e09fdec8314d675fa9057db` | 2026-07-02 | SPY | 0.431830 | 0.597391 | -0.031966 | 1.063706 | `7e93715294e3a8a22c2ea514` | not materialized |
| `8ddb55c4a1ed50e86c0dc43d` | 2026-07-02 | TSLA | 0.431830 | 0.597391 | -0.020945 | 1.103327 | `07bded6d2756e7cc3abd5b79` | not materialized |
| `2f18c0520561e29eb84455a5` | 2026-07-02 | XLB | 0.431830 | 0.597391 | -0.021394 | 1.061216 | `d3ee7dd19da82091789845f9` | not materialized |
| `bc5f81fe4015112a9d98c1a1` | 2026-07-02 | XLC | 0.431830 | 0.597391 | -0.028910 | 1.072320 | `ca73ff106a7070e24574d853` | not materialized |
| `ab6f31e75f62dbf9af3472e3` | 2026-07-02 | XLE | 0.431830 | 0.597391 | -0.028425 | 1.081122 | `cfa764ed131fa208b477a8a5` | not materialized |
| `f8102d446d5880ab31a88498` | 2026-07-02 | XLF | 0.431830 | 0.597391 | -0.030986 | 1.105654 | `0a866dbaf9e720ad6bc4588f` | not materialized |
| `950eb0c6b8e74025b0dbd6fe` | 2026-07-02 | XLI | 0.431830 | 0.597391 | -0.026320 | 1.052602 | `9f5dedd91b0e8fd165f20c6d` | not materialized |
| `47d35a0cb512866d1999bb01` | 2026-07-02 | XLK | 0.431830 | 0.597391 | -0.010481 | 1.159368 | `577f160670a4021d04f576ad` | not materialized |
| `8cb88425b4855e60930b3a2a` | 2026-07-02 | XLP | 0.431830 | 0.597391 | -0.027049 | 1.061216 | `d5d47725c915a48004ed1556` | not materialized |
| `db5f8c04463c2e35f0221143` | 2026-07-02 | XLRE | 0.431830 | 0.597391 | -0.027049 | 1.061216 | `e7c237b39e75b8bfea5defb0` | not materialized |
| `4e470f44ec16d1c9f0ac6926` | 2026-07-02 | XLU | 0.431830 | 0.597391 | -0.028217 | 1.061216 | `42e434bbf683846e9577ab87` | not materialized |
| `0fef4cb710d0f5ed6da52f05` | 2026-07-02 | XLV | 0.431830 | 0.597391 | -0.016145 | 1.105654 | `9876fe94b9ba2040f6d6fb80` | not materialized |
| `b9441e826f371384bba256e5` | 2026-07-02 | XLY | 0.431830 | 0.597391 | -0.028910 | 1.072320 | `9131ac9c3668378879915ed7` | not materialized |

All accepted observations use hypothesis `sector_rotation_buy_ordinary_20d_time_exit_utility_v1`.

## Pending Entries

Each pending entry uses rule `next_completed_session_open`. The planned entry date is not materialized because local data stops at `2026-07-02`. The next required market session is the next completed regular session after `2026-07-02`, expected `2026-07-06`.

| Event ID | Ticker | As-of date | Pending entry date | Entry rule | Next required market session |
| --- | --- | --- | --- | --- | --- |
| `9a1015c64e5550bb68e746c8` | AAPL | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `5a23e06e82e16316c27d7dea` | AMD | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `f3bd3b8d6bc0fa5513663497` | AMZN | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `0be4357ec2084f2dba9c6d49` | DIA | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `9ecd2cf6658d2e0d52f285ef` | GOOGL | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `e4be49dba9caf3d204a14562` | IWM | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `3771e368fc5e8e786755de56` | META | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `fed3e1a6da1d6e43954a3763` | MSFT | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `e678906054c4719c75ad09ac` | NVDA | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `8f972ede125d11f097597d13` | QQQ | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `7e93715294e3a8a22c2ea514` | SPY | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `07bded6d2756e7cc3abd5b79` | TSLA | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `d3ee7dd19da82091789845f9` | XLB | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `ca73ff106a7070e24574d853` | XLC | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `cfa764ed131fa208b477a8a5` | XLE | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `0a866dbaf9e720ad6bc4588f` | XLF | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `9f5dedd91b0e8fd165f20c6d` | XLI | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `577f160670a4021d04f576ad` | XLK | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `d5d47725c915a48004ed1556` | XLP | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `e7c237b39e75b8bfea5defb0` | XLRE | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `42e434bbf683846e9577ab87` | XLU | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `9876fe94b9ba2040f6d6fb80` | XLV | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |
| `9131ac9c3668378879915ed7` | XLY | 2026-07-02 | not materialized | `next_completed_session_open` | 2026-07-06 completed data |

## Next Command

After the next completed session is available locally, run in development:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-update
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-status
```

Do not run this before a genuinely newer completed session exists.

