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

The current vertical slice creates `SIGNAL_CREATED`, `SIGNAL_REJECTED`, and `ENTRY_PENDING` events from scanner snapshots. Entry resolution, marking, and exit events are prepared by schema and reconstruction logic but remain intentionally limited until another daily bar arrives after deployment.

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
