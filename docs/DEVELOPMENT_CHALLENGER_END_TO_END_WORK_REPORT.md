# Development Challenger End-To-End Work Report

Generated: 2026-06-27

This report consolidates all work performed on the latest robust-transform development generation and its prospective shadow final-holdout enrollment/update path. It is a work log and state report, not a promotion recommendation.

## Repositories

| Repository | Path | Branch | HEAD |
| --- | --- | --- | --- |
| Development | `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev` | `feat/product-class-specialist-challengers-v1` | `8e2b40effab1332f474ca47d720fcb8c21ca4912` |
| Operational | `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner` | `feat/autonomous-swing-scanner-v1` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |

The operational repository was checked read-only throughout this work and remains clean.

## 1. Latest Generation Identified

Latest development generation after Robust MAE Target Transformation V1:

| Field | Value |
| --- | --- |
| Generation ID | `2026-06-27T14:05:10.073173+00:00` |
| Newer than required timestamp | yes, newer than `2026-06-26T23:52:15.769542+00:00` |
| Model count | 30 total: 20 learned, 10 naive controls |
| Scopes | `POOLED`, `ORDINARY`, `INVERSE`, `LEVERAGED_LONG`, `LEVERAGED_INVERSE` |
| Directions | `bull`, `bear` |
| Learned families | `extra_trees`, `hist_gradient_boosting` |
| Control family | `naive_base_rate` |
| Model promoted | no |
| Development final-holdout run before enrollment | none |
| Development forward events before enrollment | none |

The complete learned-model gate triage is recorded in `docs/DEVELOPMENT_CANDIDATE_GATE_TRIAGE.md`.

## 2. Gate Triage Outcome

One learned model was classified as `DEVELOPMENT_QUALIFIED_PENDING_FINAL_HOLDOUT`:

| Field | Value |
| --- | --- |
| Model ID | `5b3f37a96a7968bca8d2f398` |
| Scope | `POOLED` |
| Direction | `bull` |
| Family | `hist_gradient_boosting` |
| Selected rows | 96 |
| Selected trading dates | 51 |
| Selected rate | 0.5624% |
| Portfolio total return | 35.3924% |
| Portfolio max drawdown | -8.4572% |
| Development-quality blockers | none |
| Final-holdout-only blocker | `final_holdout_required_for_promotion` |

This made the model eligible for prospective final-holdout enrollment, not promotion.

## 3. Challenger Enrollment Package

Prepared `docs/CHALLENGER_ENROLLMENT_PACKAGE_5b3f37a96a7968bca8d2f398.md`.

Frozen identity captured:

| Field | Value |
| --- | --- |
| Model artifact SHA256 | `8e77b20f634192d6b33d26663b6564c31086872cf47854869fc618d5ce818088` |
| Universe snapshot ID | `6b1a74750684506e1a5b` |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| Selection-policy hash | `ff689a7edf893b56` |
| TBS calibration manifest hash | `ac9e2feb545c9e16` |
| TBS calibrator artifact hash | `87dc04fafad6261f` |
| OOD governance hash | `56e33c072cba1b5f` |
| Path-head capability hash | `f9aa10594ea731eb` |
| Sample policy | `prospective_final_holdout_sample_v1` |
| Sample-policy hash | `4ae8415df04cd538` |

## 4. Development Final-Holdout Enrollment

Command run:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation 2026-06-27T14:05:10.073173+00:00
```

Result:

| Field | Value |
| --- | --- |
| Run ID | `d25d6fa11a2e50daa430c15e` |
| Baseline market date | `2026-06-25` |
| Enrolled models | 1 |
| Enrolled model | `5b3f37a96a7968bca8d2f398` |
| Backfilled predictions | 0 |
| Matured outcomes | 0 |
| Status after enrollment | `CREATED` |

Enrollment details are recorded in `docs/DEVELOPMENT_FINAL_HOLDOUT_ENROLLMENT_REPORT.md`.

## 5. First Update Attempt

Initial `universe-update` was attempted before a configured API key was available in the process environment.

Result:

| Field | Value |
| --- | ---: |
| Enabled symbols | 35 |
| Updated symbols | 0 |
| Symbols with errors | 35 |
| Final-holdout processed sessions | 0 |
| Events inserted | 0 |

No `.env` file was opened or printed. No SQLite, scanner, forward, artifact, or operational state changed during that failed attempt. The attempt is recorded in `docs/DEVELOPMENT_FINAL_HOLDOUT_FIRST_UPDATE_REPORT.md`.

## 6. Successful Development Data Refresh

An FMP key was supplied transiently as an environment variable to the shell process. It was not written to `.env`, source code, docs, artifacts, or command output.

Command run:

```bash
.venv/bin/python -m swing_rsi.cli universe-update
```

Result:

| Field | Value |
| --- | ---: |
| Enabled symbols | 35 |
| Updated symbols | 35 |
| Symbols with errors | 0 |
| Raw data max date after refresh | `2026-06-26` |

Representative raw files:

| File | Before | After |
| --- | --- | --- |
| `data/raw/SPY.csv` | 120,283 bytes, mtime Jun 25 17:04:40 2026, max date `2026-06-25` | 120,331 bytes, mtime Jun 27 14:04:28 2026, max date `2026-06-26` |
| `data/raw/AAPL.csv` | 223,461 bytes, mtime Jun 25 17:04:35 2026, max date `2026-06-25` | 223,509 bytes, mtime Jun 27 14:04:21 2026, max date `2026-06-26` |

## 7. Feature Rebuild

Command run:

```bash
.venv/bin/python -m swing_rsi.cli build-features
```

Result:

| Field | Before | After |
| --- | ---: | ---: |
| Feature rows | 90,113 | 90,148 |
| Label rows | 90,113 | 90,148 |
| Modeling rows | 90,113 | 90,148 |
| Feature max date | `2026-06-25` | `2026-06-26` |
| Symbols | 35 | 35 |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` | unchanged |

Feature artifacts:

| Artifact | Before | After |
| --- | --- | --- |
| Features parquet | 326,800,603 bytes, mtime Jun 25 17:17:09 2026 | 326,929,564 bytes, mtime Jun 27 14:07:50 2026 |
| Labels parquet | 36,587,509 bytes, mtime Jun 25 17:17:09 2026 | 36,601,268 bytes, mtime Jun 27 14:07:50 2026 |
| Modeling parquet | 363,335,649 bytes, mtime Jun 25 17:17:09 2026 | 363,478,361 bytes, mtime Jun 27 14:07:51 2026 |

The build emitted existing pandas `PerformanceWarning` messages about DataFrame fragmentation; it completed successfully.

## 8. Successful Final-Holdout Update

Command run:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-update
```

Result:

| Field | Value |
| --- | --- |
| Processed sessions | `2026-06-26` |
| Blocked sessions | 0 |
| Events inserted | 26 |
| Session report | `reports/final_holdout/d25d6fa11a2e50daa430c15e_2026-06-26.json` |
| Shadow scanner snapshot | `dbc51686179c4291a0c890dd` |
| Shadow scanner rows | 25 |

Event breakdown:

| Event type | Count |
| --- | ---: |
| `FINAL_HOLDOUT_SIGNAL_CREATED` | 1 |
| `FINAL_HOLDOUT_ENTRY_PENDING` | 1 |
| `FINAL_HOLDOUT_SIGNAL_REJECTED` | 24 |

The single pending entry is `TZA` bullish, with `signal_as_of_date = 2026-06-26`, entry rule `next_completed_session_open`, expected return `0.022293996654081303`, calibrated probability `0.576112412177986`, expected MFE `0.16168030149520782`, expected MAE `-0.08419057351975164`, planned target return `0.08084015074760391`, planned stop return `0.08419057351975164`, and round-trip cost `5.0` bps.

Rejected-signal reason totals:

| Reason | Count |
| --- | ---: |
| `below_expected_return_threshold;below_target_before_stop_threshold` | 11 |
| `below_target_before_stop_threshold` | 7 |
| `below_probability_threshold;below_expected_return_threshold;below_target_before_stop_threshold` | 4 |
| `below_probability_threshold;below_target_before_stop_threshold` | 2 |

The successful update is recorded in `docs/DEVELOPMENT_FINAL_HOLDOUT_2026_06_26_UPDATE_REPORT.md`.

## 9. Current Final-Holdout Status

| Field | Value |
| --- | ---: |
| Run ID | `d25d6fa11a2e50daa430c15e` |
| Run status | `COLLECTING` |
| Model status | `COLLECTING` |
| Baseline market date | `2026-06-25` |
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

## 10. Final State Deltas

Development state:

| Item | Before work | Current |
| --- | --- | --- |
| Development SQLite | 384,835,584 bytes, mtime Jun 27 11:08:26 2026 | 385,888,256 bytes, mtime Jun 27 14:08:40 2026 |
| Representative model artifact | 30,710,684 bytes, mtime Jun 27 10:15:26 2026 | unchanged |
| Development scanner snapshots | 3 | 4 |
| Development final-holdout scanner snapshots | 0 | 1 |
| Development forward events | 0 | 26 |
| Development final-holdout-prefixed forward events | 0 | 26 |
| Development final-holdout runs | 0 | 1 |
| Development final-holdout models | 0 | 1 |
| Development feature max date | `2026-06-25` | `2026-06-26` |

Generated final-holdout artifacts:

| Artifact | Size | Mtime |
| --- | ---: | --- |
| `artifacts/scanner/final_holdout/dbc51686179c4291a0c890dd_scanner.csv` | 294,396 bytes | Jun 27 14:08:39 2026 |
| `artifacts/scanner/final_holdout/dbc51686179c4291a0c890dd_scanner.parquet` | 160,694 bytes | Jun 27 14:08:39 2026 |
| `reports/final_holdout/d25d6fa11a2e50daa430c15e_2026-06-26.json` | 258 bytes | Jun 27 14:08:41 2026 |

Operational state:

| Item | Before | Current |
| --- | --- | --- |
| Operational HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | unchanged |
| Operational Git status | clean | clean |
| Operational scanner snapshots | 17 | 17 |
| Operational forward events | 285 | 285 |
| Operational final-holdout runs | 1 | 1 |
| Operational final-holdout-prefixed forward events | 0 | 0 |
| Operational run ID | `3493ee8ac37bf96475c362e1` | unchanged |

## 11. Files And Artifacts Created

Tracked documentation created:

- `docs/DEVELOPMENT_CANDIDATE_GATE_TRIAGE.md`
- `docs/CHALLENGER_ENROLLMENT_PACKAGE_5b3f37a96a7968bca8d2f398.md`
- `docs/DEVELOPMENT_FINAL_HOLDOUT_ENROLLMENT_REPORT.md`
- `docs/DEVELOPMENT_FINAL_HOLDOUT_FIRST_UPDATE_REPORT.md`
- `docs/DEVELOPMENT_FINAL_HOLDOUT_2026_06_26_UPDATE_REPORT.md`
- `docs/DEVELOPMENT_CHALLENGER_END_TO_END_WORK_REPORT.md`

Tracked documentation updated:

- `docs/CHANGELOG.md`

Generated development state/artifacts:

- raw CSV files under `data/raw/` refreshed through `2026-06-26`;
- feature, label, and modeling parquet artifacts rebuilt under `data/features/`;
- SQLite state updated under `state/engine.sqlite3`;
- shadow final-holdout scanner artifacts created under `artifacts/scanner/final_holdout/`;
- session report created under `reports/final_holdout/`.

No source, test, config, dashboard, script, dependency, or README file was changed.

## 12. Commands And Checks Run

Commands run:

- `.venv/bin/python -m swing_rsi.cli final-holdout-init --generation 2026-06-27T14:05:10.073173+00:00`
- `.venv/bin/python -m swing_rsi.cli universe-update`
- `.venv/bin/python -m swing_rsi.cli build-features`
- `.venv/bin/python -m swing_rsi.cli final-holdout-update`
- `.venv/bin/python -m swing_rsi.cli final-holdout-status`

Read-only verification checks run:

- development and operational `git status --short`;
- development and operational `git rev-parse HEAD`;
- SQLite read-only count queries for scanner snapshots, forward events, final-holdout runs, models, and final-holdout-prefixed events;
- file `stat` checks for SQLite, model artifact, raw data, feature artifacts, and generated scanner/report artifacts;
- parquet coverage checks for feature rows, symbols, min date, and max date.

`pytest`, `ruff`, and `mypy` were not run because no source behavior changed.

## 13. Guardrails And Integrity

- No model was promoted.
- No model was retrained.
- No `discover-models` command was run.
- No ordinary scanner run was performed.
- No ordinary forward update was performed.
- No daily cycle was run.
- No final-holdout evaluation was run.
- No thresholds, gates, OOD governance, product scopes, scanner policy, or final-holdout rules were changed.
- No operational repository state changed.
- The supplied FMP key was used only transiently and was not persisted or printed.

## 14. Data Leakage Review

The enrolled baseline market date is `2026-06-25`. The only processed final-holdout session is `2026-06-26`, strictly after the baseline. The update accepted the refreshed raw-data provenance and inserted no backfill-blocked or invalidated outcomes. The `TZA` signal created on `2026-06-26` remains pending for the next completed session open, preserving the rule that a daily-close signal is not filled at the same close.

## 15. Assumptions And Limitations

Assumptions introduced:

- The transient FMP key was authorized for development-only data refresh.
- The configured FMP provider response and existing ingestion manifests are the accepted local provenance source for prospective final-holdout update eligibility.

Known limitations:

- The run has only one prospective observation session.
- There are zero matured outcomes.
- The pending `TZA` entry has not filled because no later completed session is locally available yet.
- This is shadow final-holdout collection only and cannot satisfy promotion.

## 16. Next Task

After the next completed trading session is locally available, rerun the development-only `universe-update`, `build-features`, and `final-holdout-update` sequence to fill the pending `TZA` entry or continue collecting shadow evidence.
