# Feature Build Fragmentation Fix Handoff

## Root Cause

`build-features` completed successfully, but pandas emitted repeated
`PerformanceWarning: DataFrame is highly fragmented` messages because feature
construction inserted many columns one at a time into already-wide DataFrames.

Primary source:

- `_symbol_features(...)` in `src/swing_rsi/engine/features.py`

This function built one-symbol technical features by repeatedly assigning into
`result["new_column"]`. The warning appeared late in the function around
`mfi_14`, `plus_di_14`, `minus_di_14`, `adx_14`, and metadata columns because
the frame was already fragmented by earlier return, trend, volatility, volume,
candle, RSI, and technical feature inserts.

Secondary source:

- `_add_cross_sectional_features(...)` in `src/swing_rsi/engine/features.py`

This function added rank, market-relative, sector-relative, relationship, and
regime columns through direct `data[...] = ...`, repeated masked assignments,
and repeated relationship merges.

## Functions Changed

- `_symbol_features(...)`
- `_add_cross_sectional_features(...)`

No model code, labels, thresholds, gates, product-class mappings, scanner logic,
promotion logic, FMP ingestion, operational state, or final-holdout state was
changed.

## Refactor Pattern

One-symbol features now use an ordered `feature_columns` dictionary:

1. seed base OHLCV series;
2. compute derived feature series in the original column order;
3. add metadata as full-length series;
4. create one DataFrame from the dictionary;
5. return the same `Date`/`symbol` aligned output.

Cross-sectional features now batch logical groups:

- relative-strength ranks;
- breadth/sector daily aggregates;
- market-relative benchmark columns;
- sector-relative columns;
- relationship graph columns;
- regime columns.

The function concatenates each logical group once and returns a final `.copy()`
after sorting to keep the frame defragmented.

No warnings are suppressed. The fix removes the insert pattern that triggered
the warnings.

## Before/After Warning Behavior

Before:

- The deterministic fixture emitted repeated pandas `PerformanceWarning`
  messages at the late `_symbol_features(...)` assignments.
- Full `build-features` terminal output was noisy even though the build
  succeeded.

After:

- The same deterministic fixture runs with
  `warnings.simplefilter("error", pandas.errors.PerformanceWarning)` and passes.
- Full development `build-features` completed without any fragmentation warning
  output.

## Output Equivalence

Deterministic local fixture before refactor:

- shape: `(2080, 444)`
- manifest: `e0cc2fce506e6d7d97f6cdcb449ef6f911cadc5dab9e0473e73181c10975357b`

Deterministic local fixture after refactor:

- shape: `(2080, 444)`
- manifest: `e0cc2fce506e6d7d97f6cdcb449ef6f911cadc5dab9e0473e73181c10975357b`
- same column order;
- same `Date` values;
- same `symbol` values;
- same numeric values within `1e-12`;
- same object values;
- same null locations;
- no new positive or negative infinity values.

Current development `build-features` before refactor, from the observed issue:

- feature rows: `90,148`
- label rows: `90,148`
- modeling rows: `90,148`
- feature manifest hash:
  `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`

Current development `build-features` after refactor:

- feature rows: `90,148`
- label rows: `90,148`
- modeling rows: `90,148`
- feature manifest hash:
  `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`

Output files written by the allowed development smoke:

- `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet`
- `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_labels.parquet`
- `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`

The feature manifest hash did not change.

## Tests Added

Updated `tests/test_autonomous_engine.py` with:

- a focused `PerformanceWarning` escalation test for `build_feature_panel(...)`;
- a hot-path source regression test checking the refactored functions do not
  use repeated DataFrame insert-style mutation;
- representative value checks for technical, market-relative, sector-relative,
  relationship, and regime-conditioned columns;
- metadata checks for `symbol`, `role`, `sector`, `sector_proxy`, and
  `is_benchmark`;
- label/modeling row-count checks on the representative fixture;
- no-label-column and no-infinity checks.

Focused test command:

```bash
.venv/bin/pytest tests/test_autonomous_engine.py -k "feature_builder_emits_no_fragmentation_warning or feature_hot_paths_avoid_repeated_dataframe_insert_mutation or batched_feature_builder_preserves_representative_values or feature_registry_covers_generated_columns" -q
```

Focused result:

```text
4 passed
```

## Verification Results

Full verification:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

Results:

```text
330 passed
All checks passed!
118 files already formatted
Success: no issues found in 61 source files
```

## Build-Features Smoke Result

Command:

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

No pandas `PerformanceWarning` output appeared during the final-code smoke.
Elapsed time was not separately instrumented; observed wall-clock runtime was
approximately 2 minutes 41 seconds in the Codex tool session.

## Operational Immutability Proof

Operational repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

Read-only status:

- operational HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- operational Git status: clean on `feat/autonomous-swing-scanner-v1`
- operational prospective run ID:
  `3493ee8ac37bf96475c362e1`
- operational run status: `COLLECTING`
- operational final-holdout event count: `25`
- operational scanner snapshot count: `18`
- operational forward event count: `310`

Counts were read from operational SQLite using a read-only connection
(`mode=ro`). No operational command was run.

## Known Limitations

- This is a fragmentation/noise cleanup, not a broader feature-builder
  performance redesign.
- The expanding KMeans regime calculation remains intentionally unchanged.
- The development feature parquet files were rebuilt by the allowed smoke, but
  they are ignored artifacts and the manifest hash remained unchanged.

## Exact Next Task

Profile `build-features` wall-clock time by feature block and identify the
single slowest remaining block without changing feature definitions.
