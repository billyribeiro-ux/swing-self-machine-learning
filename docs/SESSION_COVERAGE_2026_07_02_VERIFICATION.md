# Session Coverage 2026-07-02 Verification

Created UTC: `2026-07-04`

This report was created from read-only local inspection. No update, feature-build,
final-holdout, signal-discovery, scanner, forward, daily-cycle, or diagnostic
update command was run.

## Verdict

`SESSION_COVERAGE_VERDICT: CURRENT_THROUGH_2026_07_02`

NO UPDATE NEEDED.
BOTH REPOS ARE CURRENT THROUGH 2026-07-02.
NO NEWER COMPLETED LOCAL SESSION IS AVAILABLE.

## Development Repository

- path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`
- branch: `feat/product-class-specialist-challengers-v1`
- HEAD: `b7835bb71d09ffcbadc4e336d73f8de793a936f9`
- git status before report creation:

```text
## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1
```

### Local Data Coverage

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
- KMeans fits avoided: 2,522
- KMeans fits performed: 0

All enabled development symbols have latest raw date `2026-07-02`:

```text
AAPL, AMD, AMZN, DIA, GOOGL, IWM, META, MSFT, NVDA, QID, QQQ, RWM, SDS, SH,
SOXL, SOXS, SPXU, SPY, SQQQ, TNA, TQQQ, TSLA, TZA, UPRO, XLB, XLC, XLE,
XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY
```

### Development Evidence Runs

Development final-holdout run:

- run ID: `d25d6fa11a2e50daa430c15e`
- status: `INVALIDATED`
- latest processed market date: `2026-06-26`
- invalidation reason: `code commit hash changed since enrollment`

Latest signal-discovery generation:

- generation ID: `signal_discovery_20260704T192734+0000_caa051802201`
- created at: `2026-07-04T19:27:34+00:00`
- latest signal-discovery as-of date: `2026-07-02`
- hypotheses evaluated: 17
- selected candidates: 0
- NO_SIGNAL rows: 516
- rejected rows: 28

Time-exit diagnostic run:

- run ID: `0e5facd1e8a164df2b586f64`
- baseline date: `2026-06-26`
- status: `CREATED`
- run-row latest processed market date: null
- latest diagnostic event market date: `2026-07-02`
- observations: 46
- pending entries: 46
- matured outcomes: 0
- backfill-blocked rows: 23

The diagnostic ledger has local events through `2026-07-02`; no diagnostic event
or signal-discovery row indicates a later local completed session.

## Operational Repository

- path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- branch: `feat/autonomous-swing-scanner-v1`
- HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- git status:

```text
## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1
```

### Local Data Coverage

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
- regime cache status: not available from an on-disk operational cache-status artifact

All enabled operational symbols have latest raw date `2026-07-02`:

```text
AAPL, AMD, AMZN, DIA, GOOGL, IWM, META, MSFT, NVDA, QID, QQQ, RWM, SDS, SH,
SOXL, SOXS, SPXU, SPY, SQQQ, TNA, TQQQ, TSLA, TZA, UPRO, XLB, XLC, XLE,
XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY
```

### Operational Final-Holdout Run

- run ID: `3493ee8ac37bf96475c362e1`
- enrolled model ID: `b93b2258c10aea5cef81d291`
- baseline date: `2026-06-25`
- run status: `COLLECTING`
- latest processed market date: `2026-07-02`
- pending entries: 0
- open positions: 0
- matured outcomes: 0
- final-holdout event count: 125
- final-holdout event types:
  - `FINAL_HOLDOUT_SIGNAL_REJECTED`: 125

## No Newer Local Session Evidence

- Development raw data max date: `2026-07-02`
- Development feature/label/modeling max date: `2026-07-02`
- Development latest signal-discovery as-of date: `2026-07-02`
- Operational raw data max date: `2026-07-02`
- Operational feature/label/modeling max date: `2026-07-02`
- Operational final-holdout latest processed market date: `2026-07-02`

No local raw data, feature parquet, modeling parquet, signal-discovery metadata,
or final-holdout state shows a completed session later than `2026-07-02`.

## Commands Skipped

Because both repos are current through `2026-07-02`, the following were not run:

- `universe-update`
- `build-features`
- `final-holdout-update`
- `discover-signals`
- `time-exit-diagnostic-update`
- `scanner`
- `forward-update`
- `daily-cycle`
- `discover-models`

## Next Command Later

Run this only after a genuinely newer completed U.S. equity session is available
locally, expected after the next regular session `2026-07-06` completes:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
.venv/bin/python -m swing_rsi.cli universe-update
```

## Immutability Report

Operational before/after this verification:

| Field | Before | After |
| --- | --- | --- |
| git status | `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1` | unchanged |
| SQLite hash | `0f1f91478b544ba3de62e1eccdc5a735eb3719593d03fee8ba26f0c52c151d6c` | unchanged |
| enrolled model artifact hash | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` | unchanged |
| scanner snapshot count | 22 | unchanged |
| ordinary forward-event count | 285 | unchanged |
| final-holdout event count | 125 | unchanged |
| prospective run ID | `3493ee8ac37bf96475c362e1` | unchanged |
| baseline date | `2026-06-25` | unchanged |

Development before/after this verification, excluding this new Markdown report:

| Field | Before | After |
| --- | --- | --- |
| git status | `## feat/product-class-specialist-challengers-v1...origin/feat/product-class-specialist-challengers-v1` | same plus untracked `docs/SESSION_COVERAGE_2026_07_02_VERIFICATION.md` |
| SQLite size | 386162688 | unchanged |
| SQLite mtime ns | 1783194267387808026 | unchanged |
| scanner snapshot count | 4 | unchanged |
| forward-event count | 30 | unchanged |
| final-holdout run count | 1 | unchanged |
| final-holdout event count | 30 | unchanged |
| time-exit diagnostic event count | 115 | unchanged |

## Safety Confirmation

- no source files changed
- no model artifacts changed
- no thresholds changed
- no gates changed
- no OOD governance changed
- no promotion occurred
- `.env` was not opened or printed
