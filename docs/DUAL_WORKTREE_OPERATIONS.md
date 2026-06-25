# Dual Worktree Operations

This repository now uses two separate Git worktrees so the prospective final-holdout operation stays frozen while challenger development can continue independently.

## Frozen Operational Checkout

Path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Frozen prospective run:

| Field | Value |
| --- | --- |
| Run ID | `3493ee8ac37bf96475c362e1` |
| Model ID | `b93b2258c10aea5cef81d291` |
| Generation | `2026-06-25T13:11:51.610283+00:00` |
| Baseline market date | `2026-06-25` |
| First eligible prediction date | strictly after `2026-06-25` |
| Frozen commit | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |

The operational checkout is for prospective final-holdout collection only. Do not make model-development commits, discovery runs, scanner runs, ordinary forward updates, threshold changes, calibration changes, OOD-governance changes, or model artifact changes in this checkout.

Daily operational sequence after each genuinely later completed market session:

```bash
.venv/bin/python -m swing_rsi.cli universe-update
.venv/bin/python -m swing_rsi.cli build-features
.venv/bin/python -m swing_rsi.cli final-holdout-update
.venv/bin/python -m swing_rsi.cli final-holdout-status
```

The final-holdout update must process only sessions later than the frozen baseline. No signal with `as_of_date <= 2026-06-25` is eligible for this run.

## Active Development Checkout

Path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Branch: `feat/product-class-specialist-challengers-v1`

All development commands, model experiments, discovery runs, generated research reports, and new commits must run only in this development worktree. This checkout has its own `.venv`, `state/`, `artifacts/`, `reports/`, logs, caches, and generated feature outputs.

Safe research inputs copied into this worktree:

- `data/raw/`
- `data/manifests/`
- `data/universes/`

Directories and files deliberately not copied from operations:

- `.env`
- `.venv/`
- `state/engine.sqlite3`
- final-holdout state
- forward events
- scanner snapshots
- generated reports
- model artifacts
- active operational locks
- operational SQLite state

The two worktrees must never share mutable SQLite, model-artifact, scanner, or forward-event files. Copy non-secret input data when needed; do not symlink mutable state between them.

## Commit Discipline

Commit operational documentation and development changes only from the development checkout unless a future operational procedure explicitly requires otherwise. Keep the operational checkout clean and pinned to its enrolled commit while the prospective final-holdout run is collecting evidence.
