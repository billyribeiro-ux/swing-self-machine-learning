# Data Advance To 2026-07-02 Status

Date run: 2026-07-04

Objective: advance local market data and evidence tracking through the latest
completed U.S. equity session, expected `2026-07-02`. U.S. markets were closed
on `2026-07-03` for the observed Independence Day holiday.

## Result

July 2 data was obtained in both repositories.

Both development and operational local raw data now have latest common
completed local session `2026-07-02` across all 35 enabled `core` universe
symbols.

## Precheck

### Development

- path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`
- branch: `feat/product-class-specialist-challengers-v1`
- HEAD: `0118b5ca57630e59e642439f79e4a574f73e62c2`
- git status: `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1`
- latest common completed local session before update: `2026-06-26`
- final-holdout run count before update: 1
- time-exit diagnostic run count before update: 1
- source changes before update: none

### Operational

- path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- branch: `feat/autonomous-swing-scanner-v1`
- HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- git status: `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- latest common completed local session before update: `2026-06-26`
- frozen run ID: `3493ee8ac37bf96475c362e1`
- baseline date: `2026-06-25`
- latest processed market date before update: `2026-06-26`
- final-holdout event count before update: 25
- source changes before update: none

## Latest Raw Date By Symbol

After update, development and operational match:

| Symbol | Latest raw date |
| --- | --- |
| AAPL | 2026-07-02 |
| AMD | 2026-07-02 |
| AMZN | 2026-07-02 |
| DIA | 2026-07-02 |
| GOOGL | 2026-07-02 |
| IWM | 2026-07-02 |
| META | 2026-07-02 |
| MSFT | 2026-07-02 |
| NVDA | 2026-07-02 |
| QID | 2026-07-02 |
| QQQ | 2026-07-02 |
| RWM | 2026-07-02 |
| SDS | 2026-07-02 |
| SH | 2026-07-02 |
| SOXL | 2026-07-02 |
| SOXS | 2026-07-02 |
| SPXU | 2026-07-02 |
| SPY | 2026-07-02 |
| SQQQ | 2026-07-02 |
| TNA | 2026-07-02 |
| TQQQ | 2026-07-02 |
| TSLA | 2026-07-02 |
| TZA | 2026-07-02 |
| UPRO | 2026-07-02 |
| XLB | 2026-07-02 |
| XLC | 2026-07-02 |
| XLE | 2026-07-02 |
| XLF | 2026-07-02 |
| XLI | 2026-07-02 |
| XLK | 2026-07-02 |
| XLP | 2026-07-02 |
| XLRE | 2026-07-02 |
| XLU | 2026-07-02 |
| XLV | 2026-07-02 |
| XLY | 2026-07-02 |

## Operational Update

Commands run in operational repository:

```bash
.venv/bin/python -m swing_rsi.cli universe-update
.venv/bin/python -m swing_rsi.cli build-features
.venv/bin/python -m swing_rsi.cli final-holdout-update
.venv/bin/python -m swing_rsi.cli final-holdout-status
```

Commands not run: `discover-models`, `discover-signals`, scanner, forward
update, daily cycle, promotion.

### Universe Update

- symbols attempted: 35
- symbols updated: 35
- symbol errors: 0
- latest common completed local session after update: `2026-07-02`

### Feature Build

- feature rows: 90,288
- label rows: 90,288
- modeling rows: 90,288
- feature manifest hash:
  `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- regime cache status: not available in operational branch output
- KMeans fits avoided: not available in operational branch output

### Final-Holdout Update

- processed sessions: 4
- processed dates: `2026-06-29`, `2026-06-30`, `2026-07-01`,
  `2026-07-02`
- blocked sessions: 0
- events inserted: 100
- final-holdout event count before: 25
- final-holdout event count after: 125
- final-holdout run status: `COLLECTING`
- latest processed market date: `2026-07-02`
- pending entries: 0
- open positions: 0
- closed/matured outcomes: 0
- final-holdout status event count: 125
- signals: 0
- rejected signals: 125
- promotion eligible: false

### Operational State Delta

- SQLite hash before:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- SQLite hash after:
  `0f1f91478b544ba3de62e1eccdc5a735eb3719593d03fee8ba26f0c52c151d6c`
- SQLite size before: `250781696`
- SQLite size after: `253202432`
- scanner snapshot count before: 18
- scanner snapshot count after: 22
- ordinary forward-event count before: 285
- ordinary forward-event count after: 285
- final-holdout event count before: 25
- final-holdout event count after: 125
- enrolled model artifact hash before:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- enrolled model artifact hash after:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`

## Development Update

Commands run in development repository:

```bash
.venv/bin/python -m swing_rsi.cli universe-update
.venv/bin/python -m swing_rsi.cli build-features
.venv/bin/python -m swing_rsi.cli final-holdout-update
.venv/bin/python -m swing_rsi.cli final-holdout-status
```

Commands not run in this phase: `discover-models`, scanner, forward update,
daily cycle, promotion.

### Universe Update

- symbols attempted: 35
- symbols updated: 35
- symbol errors: 0
- latest common completed local session after update: `2026-07-02`

### Feature Build

- feature rows: 90,288
- label rows: 90,288
- modeling rows: 90,288
- feature manifest hash:
  `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- regime cache status: `HIT`
- regime cache reason: `cache_valid`
- cached dates reused: 5,009
- new dates computed: 0
- KMeans fits avoided: 2,522
- KMeans fits performed: 0
- regime cache runtime: 2.76 seconds
- last cached date: `2026-07-02`

### Development Final-Holdout Update

- processed sessions: 0
- blocked sessions: 0
- events inserted by command summary: 0
- append-only invalidation events present after status: 4
- final-holdout event count before: 26
- final-holdout event count after: 30
- run ID: `d25d6fa11a2e50daa430c15e`
- run status after update: `INVALIDATED`
- invalidation reason: `code commit hash changed since enrollment`
- latest processed market date remained: `2026-06-26`
- pending entries: 1
- open positions: 0
- matured outcomes: 0
- invalidated outcomes: 4
- event types after update:
  - `FINAL_HOLDOUT_DATA_INVALIDATED`: 4
  - `FINAL_HOLDOUT_ENTRY_PENDING`: 1
  - `FINAL_HOLDOUT_SIGNAL_CREATED`: 1
  - `FINAL_HOLDOUT_SIGNAL_REJECTED`: 24

The development pending TZA entry did not advance. No fill date, fill price,
position status, mark, or exit was created. The run invalidated before normal
entry processing because the code commit hash differs from the enrolled run's
frozen commit.

## Development Signal Discovery

Development data advanced beyond the prior time-exit diagnostic baseline
(`2026-06-26`) and reached a genuinely newer completed session
(`2026-07-02`), so one and only one `discover-signals` run was executed.

Command:

```bash
.venv/bin/python -m swing_rsi.cli discover-signals
```

Export command:

```bash
.venv/bin/python -m swing_rsi.cli signal-discovery-export \
  --generation latest \
  --output reports/latest_signal_discovery_after_2026_07_02_update
```

Result:

- new generation ID: `signal_discovery_20260704T181757+0000_fa9987cfe9c2`
- newer than prior generation
  `signal_discovery_20260704T155444+0000_ed38c60cf1ad`: yes
- latest decision date: `2026-07-02`
- hypotheses evaluated: 17
- BUY candidates: 0
- SELL/SHORT candidates: 0
- NO_SIGNAL rows: 516
- rejected rows: 28
- selected candidates: 0
- exported files: 35

### Top BUY-Side Rows

All top BUY-side research rows were OOD rejected, not candidates.

| Ticker | Hypothesis | Score | TBS probability | Decision | Reason |
| --- | --- | ---: | ---: | --- | --- |
| SOXS | `reversal_buy_5d` | 0.456095 | 0.167834 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXS | `failed_breakdown_buy_5d` | 0.456095 | 0.167834 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `reversal_buy_5d` | 0.422256 | 0.167834 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `failed_breakdown_buy_5d` | 0.422256 | 0.167834 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `trend_continuation_buy_10d` | 0.412681 | 0.308151 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |

### Top SELL-Side Rows

All top SELL-side research rows were OOD rejected, not candidates.

| Ticker | Hypothesis | Score | TBS probability | Decision | Reason |
| --- | --- | ---: | ---: | --- | --- |
| SOXL | `trend_continuation_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `breakdown_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `pullback_continuation_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXL | `breadth_deterioration_sell_10d` | 0.552241 | 0.290771 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |
| SOXS | `trend_continuation_sell_10d` | 0.531998 | 0.236962 | `REJECTED_BY_OOD` | `ood_feature_rate_above_limit` |

### Top Blockers

- `probability_below_threshold`: 329 rows
- `target_before_stop_probability_below_threshold`: 177 rows
- `expected_value_insufficient_after_cost`: 10 rows
- `ood_feature_rate_above_limit`: 28 rejected rows

### Sector Rotation BUY ORDINARY Time-Exit Rows

- rows: 23
- status: all `RESEARCH_ONLY` / `NO_SIGNAL`
- blocker: `target_before_stop_probability_below_threshold`
- TBS probability: 0.431830 for all 23 rows
- time-exit positive probability: 0.597391 for all 23 rows
- top row: AMD, score 0.691781, expected time-exit return 0.047963,
  expected time-exit utility 1.292267

## Development Time-Exit Diagnostic Ledger

Because a genuinely new signal-discovery generation was created after the
diagnostic baseline, the diagnostic ledger was updated once.

Commands:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-update
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-status
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-export \
  --output reports/time_exit_diagnostic_after_2026_07_02_update
```

Result:

- diagnostic run ID: `0e5facd1e8a164df2b586f64`
- baseline market date: `2026-06-26`
- observations created: 23
- rejected observations: 0
- pending entries: 23
- filled entries: 0
- open diagnostic positions: 0
- matured outcomes: 0
- backfill-blocked count: 23
- latest processed market date from status view: `2026-07-02`
- rows dated `<= 2026-06-26` were blocked: yes
- event count before: 0
- event count after: 69
- event types:
  - `DIAGNOSTIC_OBSERVATION_CREATED`: 23
  - `DIAGNOSTIC_ENTRY_PENDING`: 23
  - `DIAGNOSTIC_BACKFILL_BLOCKED`: 23

Diagnostic rows remain `DIAGNOSTIC_ONLY` / `RESEARCH_OBSERVATION`. They did not
become live actionable and were not used for promotion.

## Dashboard Smoke

Command:

```bash
.venv/bin/streamlit run dashboard/app.py --server.port 8502 --server.headless true
curl -I http://localhost:8502
```

Result:

- HTTP smoke: `HTTP/1.1 200 OK`
- Streamlit process stopped after smoke.

Dashboard should now show:

- latest market date: `2026-07-02`
- regime cache: `HIT`
- development final-holdout status: `INVALIDATED`
- operational final-holdout status, if pointed at operational state:
  `COLLECTING`, latest processed `2026-07-02`
- time-exit diagnostic status: 23 observations, 23 pending entries, 0 open,
  0 matured, 23 backfill-blocked
- development final-holdout counts: 1 pending entry, 0 open positions,
  0 matured outcomes, 4 invalidated outcomes

## Final Git And State

### Development

- git status:
  `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1`
- untracked files before this report: none
- generated report directories:
  - `reports/latest_signal_discovery_after_2026_07_02_update`
  - `reports/time_exit_diagnostic_after_2026_07_02_update`
- SQLite size before: `385908736`
- SQLite size after: `386064384`
- SQLite mtime ns before: `1783187542190144543`
- SQLite mtime ns after: `1783190123159191345`
- scanner snapshot count before: 4
- scanner snapshot count after: 4
- forward-event count before: 26
- forward-event count after: 30
- final-holdout event count before: 26
- final-holdout event count after: 30
- time-exit diagnostic event count before: 0
- time-exit diagnostic event count after: 69

### Operational

- git status:
  `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- SQLite hash before:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- SQLite hash after:
  `0f1f91478b544ba3de62e1eccdc5a735eb3719593d03fee8ba26f0c52c151d6c`
- enrolled model artifact hash before:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- enrolled model artifact hash after:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- scanner snapshot count before: 18
- scanner snapshot count after: 22
- ordinary forward-event count before: 285
- ordinary forward-event count after: 285
- final-holdout event count before: 25
- final-holdout event count after: 125
- run status: `COLLECTING`
- latest processed market date: `2026-07-02`

## Remaining Blockers

1. Operational frozen run is still collecting prospective evidence. It has no
   matured outcomes yet and remains ineligible for promotion.
2. Operational final-holdout inserted only rejected final-holdout signal rows
   for the newly processed dates; no final-holdout signal was created.
3. Development final-holdout run `d25d6fa11a2e50daa430c15e` is invalidated
   because the code commit hash changed since enrollment.
4. Development signal discovery still produced zero BUY and zero SELL/SHORT
   candidates. Main blockers remain probability, target-before-stop, expected
   value after cost, and OOD.
5. Time-exit diagnostic evidence is pending entry only. No next-session fills
   or matured outcomes exist yet.

## Exact Next Command To Run Later

After the next genuinely completed U.S. equity session is locally available,
start the next data-advance cycle with:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
.venv/bin/python -m swing_rsi.cli universe-update
```

Do not run promotion, final-holdout enrollment, or gate changes until the
current blockers above are explicitly addressed.
