# Scanner Specification

The live scanner is implemented in `src/swing_rsi/engine/scanner.py` and called through `swing_rsi.application.engine_service.run_live_scanner`.

## Inputs

- Latest local feature parquet from `data/features/`.
- Deployed champion model artifacts from the registry, filtered to the current feature-manifest hash.
- Optional explicit `--include-challengers` flag for inspection when no champion exists.
- Optional explicit `scan --update-data` flag to update enabled universe symbols before scanning; ordinary scans do not make provider calls.
- Optional `scan --universe` path for a non-default universe file.
- Universe snapshot metadata.

## Snapshot Behavior

The scanner:

1. Selects the latest common completed session available across enabled local universe symbols.
2. Builds one as-of feature snapshot per symbol.
3. Loads champion model bundles that match the current feature manifest, or the newest review candidate generation only when explicitly requested and no champion exists.
4. Generates bullish and bearish predictions.
5. Applies registry state, persisted canonical gate eligibility, frozen selection-policy gates, and deterministic selection caps.
6. Creates attribution, relationship evidence, and compact historical analog records.
7. Saves immutable CSV and Parquet scanner snapshots under `artifacts/scanner/`.
8. Writes snapshot and candidate rows to SQLite.
9. Returns an idempotent existing snapshot for the same date, model set, universe, and feature hash.

## Columns

Snapshots include:

- scan ID;
- as-of date;
- ticker;
- direction;
- horizon;
- signal close context;
- calibrated probability;
- expected return;
- expected MFE and MAE;
- target-before-stop probability from the separate target-before-stop classifier;
- target-before-stop feature-screen schema and selected-feature manifest hash;
- composite utility score;
- liquidity score;
- regime;
- sector;
- top attribution categories;
- confirming relationships;
- divergences;
- model ID;
- model state;
- model quality-gate eligibility;
- feature snapshot hash;
- candidate status;
- exclusion reason.
- supporting evidence;
- compact historical analog records.

Compact analog records include directional forward return, MFE, MAE, and target-before-stop outcome fields from the stored training labels.

Scanner predictions are candidates, not trades. Only rows from a `CHAMPION` or `CHALLENGER` whose persisted canonical gate results are promotion-eligible can become actionable paper candidates. Candidate-generation review rows remain visible, but they are rejected for paper trading with explicit exclusion reasons.

Runtime scanner configuration may make a model's persisted selection policy stricter, but never looser. Minimum thresholds use `max(persisted_threshold, runtime_threshold)`. Maximum caps use `min(persisted_cap, runtime_cap)` when both values are configured. Missing persisted selection policy rejects the row with `persisted_selection_policy_missing`.

The target-before-stop probability must be generated from the target-before-stop head's own frozen selected-feature manifest. The scanner must not substitute the primary positive-return feature matrix for that head. If a required target-before-stop feature is missing from the latest snapshot, the candidate is rejected with `target_before_stop_required_feature_missing`, and the missing feature names remain auditable in the snapshot.

Scanner cache identity includes the target-before-stop screening schema and selected-feature manifest hash for every loaded model. Artifacts without target-specific target-before-stop screening metadata are legacy audit artifacts and are not treated as equivalent to new target-specific artifacts.
