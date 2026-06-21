# Paper Forward Tester

Paper forward testing is implemented in `src/swing_rsi/engine/forward.py`.

It is separate from historical walk-forward validation.

## Event Model

Forward testing uses append-only events in SQLite:

- `SIGNAL_CREATED`
- `SIGNAL_REJECTED`
- `ENTRY_PENDING`
- `ENTRY_FILLED`
- `STOP_UPDATED`
- `TARGET_UPDATED`
- `POSITION_MARKED`
- `EXIT_FILLED`
- `POSITION_EXPIRED`
- `POSITION_CANCELED`
- `DATA_CORRECTION_RECORDED`

Prospective final-holdout runs reuse the same event engine with `FINAL_HOLDOUT_` event names:

- `FINAL_HOLDOUT_SIGNAL_CREATED`
- `FINAL_HOLDOUT_SIGNAL_REJECTED`
- `FINAL_HOLDOUT_ENTRY_PENDING`
- `FINAL_HOLDOUT_ENTRY_FILLED`
- `FINAL_HOLDOUT_POSITION_MARKED`
- `FINAL_HOLDOUT_STOP_UPDATED`
- `FINAL_HOLDOUT_TARGET_UPDATED`
- `FINAL_HOLDOUT_EXIT_FILLED`
- `FINAL_HOLDOUT_POSITION_EXPIRED`
- `FINAL_HOLDOUT_DATA_INVALIDATED`
- `FINAL_HOLDOUT_EVALUATED`

The current vertical slice creates `SIGNAL_CREATED`, `SIGNAL_REJECTED`, and `ENTRY_PENDING` events from scanner snapshots. It also advances existing pending entries when later daily bars are available:

- `ENTRY_FILLED` uses the next completed session open after the signal as-of date.
- `TARGET_UPDATED` and `STOP_UPDATED` freeze policy prices after the next-open paper fill. Current policy derives bounded target/stop returns from signal-time expected return, MFE, and MAE and records the resulting prices as immutable events.
- `POSITION_MARKED` records daily mark return, MFE, and MAE from completed bars after entry.
- `EXIT_FILLED` records target, stop, conservative same-bar ambiguity, or frozen-horizon time exits when the relevant completed bar is available.

## Frozen Signal Context

Each event stores:

- event ID and unique key;
- event time;
- market as-of date;
- ticker and direction;
- model ID;
- scanner snapshot ID;
- feature snapshot hash;
- expected metrics;
- entry rule;
- signal price context when present;
- planned stop and target policy;
- frozen stop and target prices after entry fill;
- horizon and model version.

Old event rows are never updated. Position state is reconstructed from the event stream.

## Timing

Signals are created after the latest completed daily close. The default paper entry rule is the next completed session open. A close-known signal cannot enter at that same close.

Rerunning the same forward-update is idempotent and reports zero newly inserted events when nothing changed.

The latest governance-aware local acceptance run had no champion-approved actionable paper entries because no model passed every quality gate. It still recorded rejected signal events append-only so failed-gate candidates are visible rather than hidden.

## Shadow Final Holdout

`SHADOW_FINAL_HOLDOUT` is prospective validation, not a live trade recommendation. It records predictions only after a model is frozen and enrolled, and only for sessions after the enrollment baseline market date.

The update command is:

```bash
python -m swing_rsi.cli final-holdout-update
```

The command fills pending entries from newly available completed sessions, marks and exits open shadow positions, scans the close-known feature snapshot with the enrolled frozen models, appends accepted or rejected final-holdout signal events, creates next-open pending entries, and writes an ignored immutable daily report.

Historical sessions may not be backfilled. If feature-row `local_available_at_utc` or raw-data manifests cannot prove that the session arrived after run creation, the session is rejected from final-holdout evidence and a `FINAL_HOLDOUT_DATA_INVALIDATED` event records `FINAL_HOLDOUT_BACKFILL_BLOCKED`.
