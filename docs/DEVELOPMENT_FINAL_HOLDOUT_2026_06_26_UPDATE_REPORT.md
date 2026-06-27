# Development Final-Holdout 2026-06-26 Update Report

Generated: 2026-06-27

This report records the successful development-only prospective shadow final-holdout update for session `2026-06-26`. The FMP key was supplied transiently in the shell process and was not written to `.env`, source code, docs, or command output.

## Run Updated

| Field | Value |
| --- | --- |
| Run ID | `d25d6fa11a2e50daa430c15e` |
| Model ID | `5b3f37a96a7968bca8d2f398` |
| Scope | `POOLED` |
| Direction | `bull` |
| Family | `hist_gradient_boosting` |
| Generation ID | `2026-06-27T14:05:10.073173+00:00` |
| Baseline market date | `2026-06-25` |
| Processed session | `2026-06-26` |
| Mode | `SHADOW_FINAL_HOLDOUT` |
| Label | `Prospective shadow validation. Not a live trade recommendation.` |

## Commands Run

```bash
.venv/bin/python -m swing_rsi.cli universe-update
```

Result:

```text
Universe: core (6b1a74750684506e1a5b)
Enabled symbols: 35
Updated symbols: 35
Symbols with errors: 0
FMP data remains unaudited for corporate-action and historical-universe semantics.
```

All 35 enabled symbols updated through `2026-06-26`.

```bash
.venv/bin/python -m swing_rsi.cli build-features
```

Result:

```text
Universe: core (6b1a74750684506e1a5b)
Feature rows: 90,148
Label rows: 90,148
Modeling rows: 90,148
Feature manifest hash: 3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5
```

The feature manifest hash remained unchanged while the panel extended from `2026-06-25` to `2026-06-26`.

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-update
```

Result:

```text
Processed sessions: 1
2026-06-26
Blocked sessions: 0
Events inserted: 26
Report: /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev/reports/final_holdout/d25d6fa11a2e50daa430c15e_2026-06-26.json
```

## Final-Holdout Status After Update

| Field | Value |
| --- | ---: |
| Run status | `COLLECTING` |
| Model status | `COLLECTING` |
| First eligible future signal date | `2026-06-26` |
| Latest processed market date | `2026-06-26` |
| Matured outcomes | 0 of 100 |
| Distinct signal dates | 0 of 60 |
| Observation sessions | 1 of 126 |
| Calendar months | 0 of 4 |
| Positive outcomes | 0 of 20 |
| Negative outcomes | 0 of 20 |
| Pending entries | 1 |
| Open positions | 0 |
| Provenance failures | 0 |
| Blocked backfills | 0 |
| Invalidated outcomes | 0 |
| Artifact integrity status | `PASS` |
| Promotion eligible | false |
| Event count | 26 |
| Signals | 1 |
| Rejected signals | 24 |

Estimated remaining requirement: `calendar_months:4; matured:100; negative:20; observation_sessions:125; positive:20; signal_dates:60`.

## Shadow Scanner And Events

| Item | Value |
| --- | --- |
| Shadow scanner snapshot ID | `dbc51686179c4291a0c890dd` |
| Shadow scanner rows | 25 |
| Shadow scanner CSV | `artifacts/scanner/final_holdout/dbc51686179c4291a0c890dd_scanner.csv` |
| Shadow scanner parquet | `artifacts/scanner/final_holdout/dbc51686179c4291a0c890dd_scanner.parquet` |
| Session report | `reports/final_holdout/d25d6fa11a2e50daa430c15e_2026-06-26.json` |

Event breakdown:

| Event type | Count |
| --- | ---: |
| `FINAL_HOLDOUT_SIGNAL_CREATED` | 1 |
| `FINAL_HOLDOUT_ENTRY_PENDING` | 1 |
| `FINAL_HOLDOUT_SIGNAL_REJECTED` | 24 |

The single pending entry is `TZA` bullish, with `signal_as_of_date = 2026-06-26`, entry rule `next_completed_session_open`, expected return `0.022293996654081303`, calibrated probability `0.576112412177986`, expected MFE `0.16168030149520782`, expected MAE `-0.08419057351975164`, planned target return `0.08084015074760391`, planned stop return `0.08419057351975164`, and round-trip cost `5.0` bps. The entry remains pending because the next completed session was not available.

Rejected-signal reasons:

| Reason | Count |
| --- | ---: |
| `below_expected_return_threshold;below_target_before_stop_threshold` | 11 |
| `below_target_before_stop_threshold` | 7 |
| `below_probability_threshold;below_expected_return_threshold;below_target_before_stop_threshold` | 4 |
| `below_probability_threshold;below_target_before_stop_threshold` | 2 |

These are shadow validation events only. They are not live trade recommendations.

## State Before And After This Session Update

| Item | Before | After |
| --- | --- | --- |
| Development SQLite | 384,835,584 bytes, mtime Jun 27 13:44:59 2026 | 385,888,256 bytes, mtime Jun 27 14:08:40 2026 |
| Representative model artifact | 30,710,684 bytes, mtime Jun 27 10:15:26 2026 | unchanged |
| Raw `SPY.csv` | 120,283 bytes, mtime Jun 25 17:04:40 2026, max date `2026-06-25` | 120,331 bytes, mtime Jun 27 14:04:28 2026, max date `2026-06-26` |
| Raw `AAPL.csv` | 223,461 bytes, mtime Jun 25 17:04:35 2026, max date `2026-06-25` | 223,509 bytes, mtime Jun 27 14:04:21 2026, max date `2026-06-26` |
| Feature rows | 90,113, max date `2026-06-25` | 90,148, max date `2026-06-26` |
| Feature parquet | 326,800,603 bytes, mtime Jun 25 17:17:09 2026 | 326,929,564 bytes, mtime Jun 27 14:07:50 2026 |
| Label parquet | 36,587,509 bytes, mtime Jun 25 17:17:09 2026 | 36,601,268 bytes, mtime Jun 27 14:07:50 2026 |
| Modeling parquet | 363,335,649 bytes, mtime Jun 25 17:17:09 2026 | 363,478,361 bytes, mtime Jun 27 14:07:51 2026 |
| Development scanner snapshots | 3 | 4 |
| Development final-holdout scanner snapshots | 0 | 1 |
| Development forward events | 0 | 26 |
| Development final-holdout-prefixed forward events | 0 | 26 |
| Development final-holdout runs | 1 | 1 |
| Development final-holdout models | 1 | 1 |
| Development first eligible future signal date | `None` | `2026-06-26` |
| Development latest processed market date | `None` | `2026-06-26` |
| Operational HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Operational Git status | clean | clean |
| Operational scanner snapshots | 17 | 17 |
| Operational forward events | 285 | 285 |
| Operational final-holdout runs | 1 | 1 |
| Operational final-holdout-prefixed forward events | 0 | 0 |

Generated final-holdout artifacts:

| Artifact | Size | Mtime |
| --- | ---: | --- |
| `artifacts/scanner/final_holdout/dbc51686179c4291a0c890dd_scanner.csv` | 294,396 bytes | Jun 27 14:08:39 2026 |
| `artifacts/scanner/final_holdout/dbc51686179c4291a0c890dd_scanner.parquet` | 160,694 bytes | Jun 27 14:08:39 2026 |
| `reports/final_holdout/d25d6fa11a2e50daa430c15e_2026-06-26.json` | 258 bytes | Jun 27 14:08:41 2026 |

## Guardrails Preserved

- No source files changed.
- No model artifacts changed.
- No model was retrained.
- No model was promoted.
- No ordinary scanner run was performed.
- No ordinary forward update was performed.
- No daily cycle was run.
- No thresholds, gates, OOD governance, product scope, scanner policy, or final-holdout rule was changed.
- No operational repository state changed.
- The supplied FMP key was not persisted or printed.

## Data Leakage Review

The enrolled baseline market date is `2026-06-25`. The only processed session was `2026-06-26`, which is strictly after the baseline. Raw-data manifests were refreshed after the run was created, and the final-holdout updater accepted the session provenance. The pending `TZA` entry uses `next_completed_session_open`, so no same-close fill was created.

## Known Limitations

- This is one prospective observation session with zero matured outcomes.
- The pending entry cannot be filled until a later completed session is locally available.
- The run remains non-promotable and is not final evidence.

## Next Task

After the next completed trading session is available locally, rerun the development-only `universe-update`, `build-features`, and `final-holdout-update` sequence to either fill the pending `TZA` entry or continue collecting shadow evidence.
