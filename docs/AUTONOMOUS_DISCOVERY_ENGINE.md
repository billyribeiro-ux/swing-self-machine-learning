# Autonomous Discovery Engine

The Self-Learning Swing Trading Engine extends the original RSI research loop into a daily cross-sectional discovery pipeline.

The implemented vertical slice lives under `src/swing_rsi/engine/` and is orchestrated by `src/swing_rsi/application/engine_service.py`.

## Pipeline

1. Load the configurable universe from `configs/universe/core.yaml`.
2. Update enabled daily OHLCV files through the existing FMP adapter and merge-safe raw storage.
3. Write raw-data manifests with provider, symbol, requested range, actual coverage, row count, file hash, stale status, and code commit where available.
4. Build synchronized feature rows from current and prior daily data only.
5. Build physically separated `label_` outcome columns for future swing behavior.
6. Merge features and labels only for historical model discovery.
7. Split chronologically into train, calibration, and holdout slices with purge/embargo of overlapping label horizons.
8. Train baseline and nonlinear local models, including the naive historical base-rate control.
9. Fit head-specific train-only feature screens where heads use different targets. The target-before-stop classifier screens against `label_{direction}_target_before_stop_{horizon}`. Expected-return screens against the signed directional return target; MFE and MAE screen against their internal nonnegative magnitude targets.
10. Train MFE and MAE with domain-preserving path-magnitude estimators under `path_metric_magnitude_domain_v1`, then map predictions back to canonical signed external units before OOD, scanner, and gate evaluation.
11. Calibrate classification probability on the calibration slice. The target-before-stop head selects among identity, sigmoid, and isotonic calibrators using only internal chronological folds inside the calibration slice and the precommitted one-standard-error rule.
12. Evaluate holdout quality gates. Target-before-stop holdout metrics from the current repeatedly inspected split are labeled development-holdout diagnostics.
13. Register model artifacts as `CANDIDATE`, `CHALLENGER`, or `REJECTED` with quality gates, feature-stability diagnostics, per-head target-specific screen diagnostics, target-before-stop calibration-governance metadata, and holdout permutation-importance summaries.
14. Scan the latest feature snapshot with champion models, or with review candidates only when explicitly requested.
15. Persist immutable scanner snapshots, append-only paper-forward events, and drift-check summaries.
16. Enroll eligible frozen models into prospective final-holdout runs only after a baseline market date is recorded.
16. Collect shadow final-holdout events only from later locally available sessions with ingestion provenance; never backfill existing historical sessions.

## Scope

This milestone uses daily stock and ETF OHLCV only. It does not include options, intraday data, NLP/news, brokerage connectivity, live trading, authentication, deployment, or a database server.

RSI is one feature family and baseline control. It is not the scanner strategy and is not privileged at length 14.

## Key Modules

- `engine/universe.py`: YAML/CSV universe parsing and symbol metadata.
- `engine/manifest.py`: raw-data provenance and hashing.
- `engine/features.py`: declarative feature registry and feature panel builder.
- `engine/labels.py`: forward swing labels for bullish and bearish outcomes.
- `engine/splits.py`: chronological split and purge logic.
- `engine/models.py`: bounded model discovery, train-only preprocessing, calibration, and gates.
- `engine/calibration_governance.py`: target-before-stop calibration-method evaluation, chronological fold diagnostics, selected calibrator refit, and ignored audit artifact writers.
- `engine/drift.py`: feature-distribution and prediction-distribution drift checks.
- `engine/registry.py`: persistent model governance in SQLite.
- `engine/scanner.py`: latest-session scanner snapshots.
- `engine/attribution.py`: per-candidate model contribution groups and evidence.
- `engine/portfolio.py`: portfolio-level scanner-output backtester.
- `engine/forward.py`: append-only paper-forward event log, next-session paper fills, position marks, time exits, and position reconstruction.
- `engine/final_holdout.py`: prospective final-holdout run registry, no-backfill enforcement, shadow event lifecycle, evaluation, and promotion-evidence integration.

## Integrity Rules

Feature rows are as-of close-known rows. A close-known prediction cannot enter at that same close. Default paper entry is next completed session open.

Label columns are future-looking by design and must remain prefixed with `label_`. `reject_label_columns` prevents label/future columns from entering model feature matrices.

Historical walk-forward validation remains legacy research tooling. Paper forward testing means frozen model versions scanning data that arrived after deployment and recording append-only events before outcomes are known.
