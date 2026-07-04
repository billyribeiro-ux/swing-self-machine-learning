# Session Coverage And Bugfix Verification 2026-07-02

Created UTC: `2026-07-04`

This report answers the current session coverage question from current local
raw data, feature/label/modeling parquet files, SQLite state, and read-only
status commands. It does not rely on old Markdown reports.

## Verdict

`SESSION_COVERAGE_VERDICT: CURRENT_THROUGH_2026_07_02`

NO BUG FOUND.
NO UPDATE NEEDED.
BOTH REPOS ARE CURRENT THROUGH `2026-07-02`.
NO NEWER COMPLETED LOCAL SESSION IS AVAILABLE.

## Read-Only Precheck Result

### Operational Repository

- path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- branch: `feat/autonomous-swing-scanner-v1`
- HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- git status:

```text
## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1
```

- enabled universe symbol count: 35
- latest common completed local session: `2026-07-02`
- latest raw max date: `2026-07-02`
- feature rows: 90,288
- label rows: 90,288
- modeling rows: 90,288
- feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- feature parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet`
- labels parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_labels.parquet`
- modeling parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`

Latest raw date for every enabled operational symbol:

```text
AAPL 2026-07-02
AMD 2026-07-02
AMZN 2026-07-02
DIA 2026-07-02
GOOGL 2026-07-02
IWM 2026-07-02
META 2026-07-02
MSFT 2026-07-02
NVDA 2026-07-02
QID 2026-07-02
QQQ 2026-07-02
RWM 2026-07-02
SDS 2026-07-02
SH 2026-07-02
SOXL 2026-07-02
SOXS 2026-07-02
SPXU 2026-07-02
SPY 2026-07-02
SQQQ 2026-07-02
TNA 2026-07-02
TQQQ 2026-07-02
TSLA 2026-07-02
TZA 2026-07-02
UPRO 2026-07-02
XLB 2026-07-02
XLC 2026-07-02
XLE 2026-07-02
XLF 2026-07-02
XLI 2026-07-02
XLK 2026-07-02
XLP 2026-07-02
XLRE 2026-07-02
XLU 2026-07-02
XLV 2026-07-02
XLY 2026-07-02
```

Operational final-holdout:

- run ID: `3493ee8ac37bf96475c362e1`
- enrolled model ID: `b93b2258c10aea5cef81d291`
- baseline date: `2026-06-25`
- run status: `COLLECTING`
- latest processed market date: `2026-07-02`
- pending entries: 0
- open positions: 0
- matured outcomes: 0
- final-holdout event count since `2026-06-26`: 125
- final-holdout event count by type since `2026-06-26`:
  - `FINAL_HOLDOUT_SIGNAL_REJECTED`: 125

### Development Repository

- path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`
- branch: `feat/product-class-specialist-challengers-v1`
- HEAD: `b7835bb71d09ffcbadc4e336d73f8de793a936f9`
- git status before this report:

```text
## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1
```

- enabled universe symbol count: 35
- latest common completed local session: `2026-07-02`
- latest raw max date: `2026-07-02`
- feature rows: 90,288
- label rows: 90,288
- modeling rows: 90,288
- feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- feature parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet`
- labels parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_labels.parquet`
- modeling parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`
- regime cache status: `HIT`
- regime cache reason: `cache_valid`
- regime cache last cached date: `2026-07-02`

Latest raw date for every enabled development symbol:

```text
AAPL 2026-07-02
AMD 2026-07-02
AMZN 2026-07-02
DIA 2026-07-02
GOOGL 2026-07-02
IWM 2026-07-02
META 2026-07-02
MSFT 2026-07-02
NVDA 2026-07-02
QID 2026-07-02
QQQ 2026-07-02
RWM 2026-07-02
SDS 2026-07-02
SH 2026-07-02
SOXL 2026-07-02
SOXS 2026-07-02
SPXU 2026-07-02
SPY 2026-07-02
SQQQ 2026-07-02
TNA 2026-07-02
TQQQ 2026-07-02
TSLA 2026-07-02
TZA 2026-07-02
UPRO 2026-07-02
XLB 2026-07-02
XLC 2026-07-02
XLE 2026-07-02
XLF 2026-07-02
XLI 2026-07-02
XLK 2026-07-02
XLP 2026-07-02
XLRE 2026-07-02
XLU 2026-07-02
XLV 2026-07-02
XLY 2026-07-02
```

Latest signal discovery:

- generation ID: `signal_discovery_20260704T192734+0000_caa051802201`
- created at: `2026-07-04T19:27:34+00:00`
- latest signal-discovery as-of date: `2026-07-02`
- hypotheses evaluated: 17
- selected candidates: 0
- NO_SIGNAL rows: 516
- rejected rows: 28

Time-exit diagnostic:

- run ID: `0e5facd1e8a164df2b586f64`
- baseline date: `2026-06-26`
- status: `CREATED`
- status-command latest processed market date: `2026-07-02`
- observations: 46
- pending entries: 46
- matured outcomes: 0
- event count by type:
  - `DIAGNOSTIC_OBSERVATION_CREATED`: 46
  - `DIAGNOSTIC_ENTRY_PENDING`: 46
  - `DIAGNOSTIC_BACKFILL_BLOCKED`: 23

The time-exit diagnostic has pending entries, but local data stops at
`2026-07-02`. These entries require the next eligible session open after
`2026-07-02`, expected `2026-07-06`, so they should remain pending now.

## Bug Detection Result

Bug found: no.

Bug rule review:

- A. Data exists through `2026-07-02` and read-only status commands report `2026-07-02`: no bug.
- B. Raw symbol dates and feature/modeling dates agree at `2026-07-02`: no bug.
- C. No newer completed local session exists: no bug.
- D. Operational final-holdout latest processed date equals local data date: no bug.
- E. Time-exit pending entries do not have next-session open data available locally yet: no bug.
- F. Inspection used the requested repositories, current SQLite files, current feature directories, and current signal-discovery metadata: no bug.
- G. This report uses current local state, not old Markdown reports: no bug.
- H. Enabled symbols are not mixed or stale; all are `2026-07-02`: no bug.
- I. No command or artifact claims no newer session while raw data contains a later completed date: no bug.

No source-code bug was confirmed, so no code was changed.

## Updates

Updates run: no.

Skipped because both repositories are already current through `2026-07-02` and
no newer completed local session is available:

- `universe-update`
- `build-features`
- `final-holdout-update`
- `discover-signals`
- `time-exit-diagnostic-update`
- `scanner`
- `forward-update`
- `daily-cycle`

## Tests

No code was changed, so the code test suite was not run.

Read-only commands used:

- Git branch, HEAD, and status checks.
- Raw CSV date inspection.
- Feature/label/modeling parquet row and max-date inspection.
- SQLite read-only event/run inspection.
- `.venv/bin/python -m swing_rsi.cli final-holdout-status`
- `.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-status`

## Next Command And Date Condition

Run the next command only after a genuinely newer completed regular U.S. equity
session is locally available. The next expected regular session after
`2026-07-02` is `2026-07-06`.

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
.venv/bin/python -m swing_rsi.cli universe-update
```

## Safety Confirmation

- no source files changed
- no operational source modified
- no model artifacts changed
- no SQLite state intentionally mutated
- no scanner snapshots mutated
- no forward events mutated
- no final-holdout events mutated
- no time-exit diagnostic events mutated
- no thresholds changed
- no gates changed
- no OOD governance changed
- no promotion occurred
- `.env` was not opened or printed

