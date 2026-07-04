# Prospective Time-Exit Diagnostic Handoff

## Purpose

Prospective Time-Exit Diagnostic Ledger V1 was added to collect future,
research-only evidence for:

```text
sector_rotation_buy_ordinary_20d_time_exit_utility_v1
```

The prior time-exit utility generation showed time-exit evidence that was
stronger than target-before-stop evidence, but all rows remained `NO_SIGNAL` /
`RESEARCH_ONLY` and the main blocker remained
`target_before_stop_probability_below_threshold`. The correct next step is
prospective evidence collection, not weakening gates, thresholds, OOD
governance, target/stop policy, or promotion policy.

## Schema

Schema version: `prospective_time_exit_diagnostic_v1`

State is stored in development SQLite using:

- `prospective_time_exit_diagnostic_runs`
- `prospective_time_exit_diagnostic_events`

Events are append-only. Current observation, entry, open-position, matured, and
rejected state is reconstructed from events.

Supported event types:

- `DIAGNOSTIC_OBSERVATION_CREATED`
- `DIAGNOSTIC_OBSERVATION_REJECTED`
- `DIAGNOSTIC_ENTRY_PENDING`
- `DIAGNOSTIC_ENTRY_FILLED`
- `DIAGNOSTIC_POSITION_MARKED`
- `DIAGNOSTIC_TIME_EXIT_MATURED`
- `DIAGNOSTIC_STOP_TOUCHED`
- `DIAGNOSTIC_TARGET_TOUCHED`
- `DIAGNOSTIC_BACKFILL_BLOCKED`
- `DIAGNOSTIC_DATA_INVALIDATED`

## Commands

Initialize:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-init \
  --hypothesis sector_rotation_buy_ordinary_20d_time_exit_utility_v1 \
  --generation signal_discovery_20260704T155444+0000_ed38c60cf1ad
```

Update after a genuinely newer signal-discovery generation and newer local
market sessions exist:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-update
```

Status:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-status
```

Export:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-export \
  --output reports/time_exit_diagnostic_v1
```

## Initialized Run

- diagnostic run ID: `0e5facd1e8a164df2b586f64`
- status: `CREATED`
- baseline market date: `2026-06-26`
- first eligible future as-of date: `None`
- hypothesis ID: `sector_rotation_buy_ordinary_20d_time_exit_utility_v1`
- archetype: `sector_rotation_buy`
- action: `BUY`
- product scope: `ORDINARY`
- horizon: 20 sessions
- target/stop policy IDs:
  `sector_rotation_buy_ordinary_20d_default_t2p0_s1p0`,
  `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`
- label schema: `sector_rotation_buy_ordinary_time_exit_utility_v1`
- feature manifest hash:
  `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- source generation:
  `signal_discovery_20260704T155444+0000_ed38c60cf1ad`

## No-Backfill Proof

Initialization created the run only. It did not ingest the current generation
and did not create historical observations.

Status immediately after initialization:

- observations created: 0
- rejected observations: 0
- pending entries: 0
- filled entries: 0
- open diagnostic positions: 0
- matured outcomes: 0
- positive time-exit outcomes: 0
- negative time-exit outcomes: 0
- early adverse recovery count: 0
- profitable despite failed TBS count: 0
- backfill-blocked count: 0
- distinct signal dates: 0
- calendar months: 0
- promotion eligible: false
- final-holdout evidence: false

No `time-exit-diagnostic-update` command was run because there was no
genuinely newer signal-discovery generation after the frozen baseline.

## Dashboard Changes

Signal Board now includes a separate `Time-Exit Diagnostic Observations`
section with statuses for diagnostic pending entry, open, matured, rejected,
and backfill-blocked observations. These rows are separate from live actionable
signals and shadow final-holdout rows.

Candidate Detail now shows `Prospective Time-Exit Diagnostic` when a selected
signal row has a matching ledger observation or matured outcome. The section is
labeled diagnostic-only and displays run status, observation state, entry/fill
state when available, matured time-exit result when available, utility score,
profitable-despite-failed-TBS flags, early-adverse-recovery flags, and baseline
versus experimental policy touch outcomes.

Reports and Exports now includes Prospective Time-Exit Diagnostic downloads and
complete-engine snapshot sheets for ledger status, events, observations, and
matured outcomes.

Dashboard page-load reads use optional, read-only table access for the ledger
tables so missing diagnostic tables do not trigger SQLite mutation.

## Exports

Export directory:

```text
reports/time_exit_diagnostic_v1
```

Files:

- `time_exit_diagnostic_status.csv`: 1 data row
- `time_exit_diagnostic_events.csv`: 0 data rows
- `time_exit_diagnostic_observations.csv`: 0 data rows
- `time_exit_diagnostic_matured_outcomes.csv`: 0 data rows
- `time_exit_diagnostic_policy_comparison.csv`: 2 data rows

Generated report files are ignored by `.gitignore`.

## Tests And Verification

Verification run:

- `.venv/bin/pytest`: 376 passed
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed
- `.venv/bin/mypy src`: passed
- Streamlit AppTest coverage:
  - Signal Board
  - Candidate Detail
  - Reports and Exports
- local HTTP smoke:
  - `curl -I http://127.0.0.1:8519`
  - result: `HTTP/1.1 200 OK`

Focused ledger tests prove:

- initialization freezes the baseline market date;
- rows at or before baseline are blocked as backfill on update;
- future matching research rows are observed;
- OOD-rejected rows are rejected, not observed as valid observations;
- entry uses next eligible session open;
- maturity uses 20-session horizon close;
- costs, MFE, MAE, policy touches, profitable-despite-failed-TBS, and early
  adverse recovery are calculated;
- events are append-only and update is idempotent;
- state reconstructs from events;
- diagnostic rows do not become live actionable, do not satisfy final-holdout
  gates, and cannot promote models;
- exports work;
- dashboard displays diagnostic status separately;
- no FMP calls occur in tests.

## Operational Immutability Proof

Operational repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

Before and after values match:

- HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- branch: `feat/autonomous-swing-scanner-v1`
- git status: `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- SQLite size: `250781696`
- SQLite mtime ns: `1782585787422972957`
- SQLite SHA256:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- enrolled model artifact:
  `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/artifacts/models/b93b2258c10aea5cef81d291.joblib`
- enrolled model artifact size: `30529057`
- enrolled model artifact mtime ns: `1782393801212695748`
- enrolled model artifact SHA256:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- scanner snapshot count: `18`
- ordinary forward-event count: `285`
- final-holdout event count: `25`
- prospective run ID: `3493ee8ac37bf96475c362e1`
- baseline date: `2026-06-25`
- latest processed market date: `2026-06-26`
- final-holdout run status: `COLLECTING`

No operational source files, SQLite state, scanner state, forward state,
final-holdout state, model artifacts, or data artifacts were modified.

## Daily Operating Sequence

1. Wait for a genuinely new local completed market session and a new
   signal-discovery generation after `2026-06-26`.
2. Run:

   ```bash
   .venv/bin/python -m swing_rsi.cli time-exit-diagnostic-update
   ```

3. Review:

   ```bash
   .venv/bin/python -m swing_rsi.cli time-exit-diagnostic-status
   ```

4. Export:

   ```bash
   .venv/bin/python -m swing_rsi.cli time-exit-diagnostic-export \
     --output reports/time_exit_diagnostic_v1
   ```

5. Review dashboard sections as diagnostic evidence only.
6. Do not use the ledger to lower gates, bypass TBS, promote a model, change
   target/stop policy, or claim final-holdout evidence.

## Next Task

Run the first diagnostic update only after the next genuinely new
signal-discovery generation and local market session after the `2026-06-26`
baseline.
