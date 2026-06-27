# Development Final-Holdout Enrollment Report

Generated: 2026-06-27

This report records the completed development prospective shadow final-holdout enrollment for the latest robust-transform generation. It does not represent model promotion and does not contain final performance evidence.

## Command Executed

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation 2026-06-27T14:05:10.073173+00:00
```

Command output:

```text
Created prospective final-holdout run d25d6fa11a2e50daa430c15e.
Run ID: d25d6fa11a2e50daa430c15e
Baseline market date: 2026-06-25
First eligible future signal date: None
Enrolled models: 1
Backfilled predictions: 0
Matured outcomes: 0
```

## Enrolled Run

| Field | Value |
| --- | --- |
| Run ID | `d25d6fa11a2e50daa430c15e` |
| Schema version | `prospective_final_holdout_v1` |
| Created at UTC | `2026-06-27T17:44:59.273939+00:00` |
| Creation Git commit | `8e2b40effab1332f474ca47d720fcb8c21ca4912` |
| Baseline market date | `2026-06-25` |
| First eligible future signal date | `None` |
| Universe snapshot ID | `6b1a74750684506e1a5b` |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| Generation ID | `2026-06-27T14:05:10.073173+00:00` |
| Enrolled model IDs | `["5b3f37a96a7968bca8d2f398"]` |
| Scanner identity version | 12 |
| Execution-policy hash | `b31550c14429a01c` |
| Sample-policy version | `prospective_final_holdout_sample_v1` |
| Sample-policy hash | `4ae8415df04cd538` |
| Horizon | 10 |
| Direction | `bull` |
| Status | `CREATED` |
| Latest processed market date | `None` |

## Enrolled Model

| Field | Value |
| --- | --- |
| Model ID | `5b3f37a96a7968bca8d2f398` |
| Scope | `POOLED` |
| Direction | `bull` |
| Family | `hist_gradient_boosting` |
| Generation ID | `2026-06-27T14:05:10.073173+00:00` |
| Artifact hash | `8e77b20f634192d6b33d26663b6564c31086872cf47854869fc618d5ce818088` |
| Model state at enrollment | `CANDIDATE` |
| Development gate eligible | true |
| Research only | false |
| Selection-policy hash | `ff689a7edf893b56` |
| Calibration-governance hash | `ac9e2feb545c9e16` |
| OOD-governance hash | `56e33c072cba1b5f` |
| Enrollment blockers | `[]` |

## Status After Enrollment

`final-holdout-status` reports:

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

## Before And After State

| Item | Before | After |
| --- | --- | --- |
| Development SQLite | `state/engine.sqlite3`, 384,835,584 bytes, mtime Jun 27 11:08:26 2026 | `state/engine.sqlite3`, 384,835,584 bytes, mtime Jun 27 13:44:59 2026 |
| Representative model artifact | 30,710,684 bytes, mtime Jun 27 10:15:26 2026 | 30,710,684 bytes, mtime Jun 27 10:15:26 2026 |
| Development scanner snapshots | 3 | 3 |
| Development forward events | 0 | 0 |
| Development final-holdout runs | 0 | 1 |
| Development final-holdout models | 0 | 1 |
| Development final-holdout events | 0 | 0 |
| Operational HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Operational Git status | clean | clean |
| Operational final-holdout runs | 1 | 1 |
| Operational final-holdout events | 0 | 0 |
| Operational scanner snapshots | 17 | 17 |
| Operational forward events | 285 | 285 |

## Guardrails Preserved

- No scanner run was performed.
- No final-holdout update was performed.
- No signal, rejected-signal, pending-entry, mark, exit, or evaluated final-holdout event was created.
- No model was promoted.
- No thresholds, gates, OOD governance, product scope, scanner policy, or final-holdout rules were changed.
- No FMP update, feature rebuild, label rebuild, discovery run, forward update, or daily cycle was run.
- Operational repository state was not modified.

## Next Task

When a completed local market session later than `2026-06-25` is available with valid ingestion provenance, run the first development `final-holdout-update` for run `d25d6fa11a2e50daa430c15e`.
