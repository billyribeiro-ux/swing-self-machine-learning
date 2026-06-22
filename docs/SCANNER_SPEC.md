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
- expected-return, MFE, and MAE feature-screen schemas and selected-feature manifest hashes;
- target-before-stop raw probability, calibration governance schema, selected calibrator method, calibration manifest hash, and calibrator artifact hash;
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

Expected-return, MFE, and MAE predictions must be generated from their own frozen selected-feature manifests. The scanner must not pass one shared feature matrix into all heads. If a required path-metric feature is missing from the latest snapshot, the candidate is rejected with `expected_return_required_feature_missing`, `mfe_required_feature_missing`, or `mae_required_feature_missing`, and the missing feature names remain auditable in the snapshot.

The target-before-stop probability must also use the model artifact's frozen selected calibrator. Identity leaves the raw target-before-stop probability unchanged, sigmoid uses the frozen sigmoid calibrator, and isotonic uses the frozen isotonic calibrator. A new-schema artifact missing calibration-governance metadata is rejected with `target_before_stop_calibration_metadata_missing`; legacy shared-screen artifacts remain labeled as legacy review artifacts rather than being treated as equivalent to new governance-aware artifacts.

Scanner cache identity includes the target-before-stop screening schema, selected-feature manifest hash, calibration governance schema, selected calibrator method, calibration manifest hash, calibrator artifact hash, and path-metric screening schemas and selected-feature manifest hashes for every loaded model. Changing the selected target-before-stop calibrator or any path-metric feature manifest changes the scanner snapshot identity.

## Prospective Final-Holdout Scanner Mode

Final-holdout updates run the scanner in `SHADOW_FINAL_HOLDOUT` mode against only the models enrolled in the selected final-holdout run. The scanner uses the same frozen model artifacts, target-before-stop feature manifests, selected calibrators, selection policies, and OOD metadata recorded at enrollment.

Shadow final-holdout scanner rows are evidence collection records. They are labeled "Prospective shadow validation. Not a live trade recommendation." Dashboard displays must keep them separate from ordinary live scanner recommendations and historical development-holdout metrics.

If an enrolled artifact, selection-policy hash, target-before-stop calibration hash, or OOD-governance hash changes after enrollment, the run is invalidated instead of silently scanning with drifted model identity.

Prospective final-holdout dashboards display sample-governance progress as counts against the frozen policy thresholds. `EARLY_DIAGNOSTIC_AVAILABLE`, `READY_FOR_EVALUATION`, evaluated status, and promotion eligibility must remain visually separate from ordinary scanner actionability.
