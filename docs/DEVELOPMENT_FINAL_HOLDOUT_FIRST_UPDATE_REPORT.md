# Development Final-Holdout First Update Report

Generated: 2026-06-27

This report records the first development-only attempt to advance the enrolled prospective shadow final-holdout run for the latest robust-transform challenger. It did not promote any model, change any gate, or modify the operational repository.

Follow-up: a transient FMP key was later supplied and the `2026-06-26` session was processed successfully. See `docs/DEVELOPMENT_FINAL_HOLDOUT_2026_06_26_UPDATE_REPORT.md` for the current final-holdout collection state.

## Enrolled Run

| Field | Value |
| --- | --- |
| Run ID | `d25d6fa11a2e50daa430c15e` |
| Model ID | `5b3f37a96a7968bca8d2f398` |
| Scope | `POOLED` |
| Direction | `bull` |
| Family | `hist_gradient_boosting` |
| Generation ID | `2026-06-27T14:05:10.073173+00:00` |
| Baseline market date | `2026-06-25` |
| Status before update attempt | `CREATED` |
| Latest processed market date before update attempt | `None` |

## Commands Run

```bash
.venv/bin/python -m swing_rsi.cli universe-update
```

Result:

```text
Universe: core (6b1a74750684506e1a5b)
Enabled symbols: 35
Updated symbols: 0
Symbols with errors: 35
```

Every enabled symbol reported `FMP_API_KEY is not configured. Run ./scripts/configure_fmp.sh from the project root.` The API key value was not opened, printed, or written.

Because no new raw data was ingested, no feature rebuild was run. The existing feature panel still ends on the baseline market date:

| Feature panel | Rows | Symbols | Min date | Max date |
| --- | ---: | ---: | --- | --- |
| `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet` | 90,113 | 35 | `2006-08-03` | `2026-06-25` |

The final-holdout updater was then run to confirm that no eligible post-baseline session existed:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-update
```

Result:

```text
Processed sessions: 0
Blocked sessions: 0
Events inserted: 0
```

Status after the update attempt:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-status
```

| Field | Value |
| --- | ---: |
| Run status | `CREATED` |
| Model status | `COLLECTING` |
| Matured outcomes | 0 of 100 |
| Distinct signal dates | 0 of 60 |
| Observation sessions | 0 of 126 |
| Calendar months | 0 of 4 |
| Positive outcomes | 0 of 20 |
| Negative outcomes | 0 of 20 |
| Pending entries | 0 |
| Open positions | 0 |
| Provenance failures | 0 |
| Blocked backfills | 0 |
| Invalidated outcomes | 0 |
| Artifact integrity status | `PASS` |
| Promotion eligible | false |
| Event count | 0 |
| Signals | 0 |
| Rejected signals | 0 |

Estimated remaining requirement: `calendar_months:4; matured:100; negative:20; observation_sessions:126; positive:20; signal_dates:60`.

## State Before And After This Update Attempt

| Item | Before | After |
| --- | --- | --- |
| Development SQLite | `state/engine.sqlite3`, 384,835,584 bytes, mtime Jun 27 13:44:59 2026 | `state/engine.sqlite3`, 384,835,584 bytes, mtime Jun 27 13:44:59 2026 |
| Representative model artifact | `artifacts/models/5b3f37a96a7968bca8d2f398.joblib`, 30,710,684 bytes, mtime Jun 27 10:15:26 2026 | unchanged |
| Feature parquet | 326,800,603 bytes, mtime Jun 25 17:17:09 2026 | unchanged |
| Development scanner snapshots | 3 | 3 |
| Development final-holdout scanner snapshots | 0 | 0 |
| Development forward events | 0 | 0 |
| Development final-holdout-prefixed forward events | 0 | 0 |
| Development final-holdout runs | 1 | 1 |
| Development final-holdout models | 1 | 1 |
| Development latest processed market date | `None` | `None` |
| Operational HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Operational Git status | clean | clean |
| Operational scanner snapshots | 17 | 17 |
| Operational forward events | 285 | 285 |
| Operational final-holdout runs | 1 | 1 |
| Operational final-holdout-prefixed forward events | 0 | 0 |

Representative raw files after the failed refresh attempt:

| File | Size | Mtime |
| --- | ---: | --- |
| `data/raw/SPY.csv` | 120,283 bytes | Jun 25 17:04:40 2026 |
| `data/raw/AAPL.csv` | 223,461 bytes | Jun 25 17:04:35 2026 |

## Guardrails Preserved

- No source files were changed.
- No model artifacts were changed.
- No SQLite state changed during this update attempt.
- No scanner snapshot was created.
- No forward event was created.
- No final-holdout event was created.
- No feature or label artifact was rebuilt.
- No model was retrained.
- No model was promoted.
- No thresholds, gates, OOD governance, final-holdout rules, or product scopes were changed.
- No operational repository state changed.

## Data Leakage Review

No post-baseline session entered the run because no local data after `2026-06-25` was available with valid ingestion provenance. The final-holdout updater inserted zero events and left `first_eligible_future_signal_date` and `latest_processed_market_date` as `None`.

## Known Limitation

Prospective evidence collection is blocked by missing development FMP configuration. This is an environment/configuration blocker, not a model-quality blocker.

## Next Task

See `docs/DEVELOPMENT_FINAL_HOLDOUT_2026_06_26_UPDATE_REPORT.md` for the current next task after the successful retry.
