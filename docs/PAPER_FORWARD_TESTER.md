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

The current vertical slice creates `SIGNAL_CREATED`, `SIGNAL_REJECTED`, and `ENTRY_PENDING` events from scanner snapshots. It also advances existing pending entries when later daily bars are available:

- `ENTRY_FILLED` uses the next completed session open after the signal as-of date.
- `POSITION_MARKED` records daily mark return, MFE, and MAE from completed bars after entry.
- `EXIT_FILLED` records a conservative time exit at the frozen horizon when the exit bar is available.

Stop/target update event types are reserved in the schema, but dynamic stop/target policy is not enabled in this milestone.

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
- planned stop and target policy;
- horizon and model version.

Old event rows are never updated. Position state is reconstructed from the event stream.

## Timing

Signals are created after the latest completed daily close. The default paper entry rule is the next completed session open. A close-known signal cannot enter at that same close.

Rerunning the same forward-update is idempotent and reports zero newly inserted events when nothing changed.

The latest governance-aware local acceptance run had no champion-approved actionable paper entries because no model passed every quality gate. It still recorded rejected signal events append-only so failed-gate candidates are visible rather than hidden.
