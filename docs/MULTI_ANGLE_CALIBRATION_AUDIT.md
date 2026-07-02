# Multi-Angle Calibration Audit Artifacts V1

Schema: `multi_angle_calibration_audit_v1`

## Purpose

Multi-Angle Calibration Audit Artifacts V1 persists calibration-slice evidence
for each evaluated Signal Discovery hypothesis and model family. The artifacts
answer calibration diagnostic questions that should not depend on ad hoc
notebooks or development-holdout threshold tuning:

- raw target-before-stop probability distribution;
- calibrated target-before-stop probability distribution;
- calibration compression, plateaus, and rank distortion;
- calibration row count and target-before-stop base rate;
- calibration-only threshold-region behavior;
- target/stop outcome behavior by probability bucket;
- product-scope and archetype evidence availability.

These artifacts are diagnostic only. They do not change production thresholds,
signal status, OOD governance, model promotion, scanner actionability,
paper-forward state, or final-holdout state.

Dashboard sections that display these artifacts must label them:

```text
Calibration diagnostic only. Not a threshold change and not proof of edge.
```

## Scope

Artifacts are produced during `discover-signals` from the existing
chronological calibration split. Training rows remain training-only, and
development-holdout rows remain development-holdout only.

For each fitted hypothesis/model family, the audit is persisted by:

- generation ID;
- hypothesis ID;
- archetype;
- action and direction;
- horizon;
- product scope;
- model family and model ID.

The row-level table contains calibration rows only. Label columns are persisted
only in diagnostic artifacts and remain excluded from feature matrices.

## Files

Generation-local files are written under:

```text
artifacts/signal_discovery/<generation_id>/
```

CLI export copies them to the requested report directory, such as:

```text
reports/signal_discovery_calibration_v1/
```

Required files:

- `calibration_summary.csv`
- `calibration_summary.json`
- `probability_distributions.csv`
- `probability_buckets.csv`
- `diagnostic_thresholds.csv`
- `row_level_calibration_audit.parquet`
- `row_level_calibration_audit.csv`
- `calibration_artifact_manifest.json`

Generated artifacts live under ignored paths and must not be committed.

## Calibration Summary

`calibration_summary.csv` records one row per hypothesis/model family/product
scope. It includes:

- calibration row count;
- positive and negative target-before-stop counts;
- target-before-stop base rate;
- target, stop, and unresolved probabilities;
- average forward return, MFE, and MAE;
- naive/base-rate Brier;
- model Brier and Brier skill;
- ROC-AUC and PR-AUC when both classes are present;
- ECE;
- calibration slope and intercept;
- raw-versus-calibrated rank correlation;
- unique calibrated probability count;
- largest calibrated plateau percentage;
- realized target-before-stop rate by decile;
- selected calibrator and calibration method;
- row-level and threshold-table hashes.

If a hypothesis cannot provide enough calibration evidence, the summary still
contains an explicit row with status such as
`INSUFFICIENT_CALIBRATION_EVIDENCE`. Hypotheses are not silently skipped.

## Probability Distributions

`probability_distributions.csv` records raw and calibrated target-before-stop
probability distributions. Each row includes min, p01, p05, p10, p25, median,
p75, p90, p95, p99, max, mean, standard deviation, and counts above:

- `0.30`
- `0.35`
- `0.40`
- `0.45`
- `0.50`
- `0.55`
- `0.60`

These thresholds are diagnostic only.

## Probability Buckets

`probability_buckets.csv` uses fixed calibrated-probability decile buckets.
Each bucket persists:

- row count;
- average raw and calibrated probability;
- observed target-before-stop hit rate;
- average forward return, MFE, and MAE;
- target, stop, and unresolved probabilities;
- average time to target and stop where available;
- transaction-cost-adjusted utility.

## Diagnostic Thresholds

`diagnostic_thresholds.csv` persists calibration-only threshold rows for:

```text
0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60
```

Each row records qualifying row count/rate, observed hit rate, precision,
recall, return/path statistics, concentration diagnostics, the active
production target-before-stop threshold, and `diagnostic_only = True`.

The table is not used to select or change production thresholds.

## Row-Level Audit

`row_level_calibration_audit.parquet` and the CSV companion persist one row per
calibration-slice row with:

- date and symbol;
- product scope;
- archetype, action, direction, and horizon;
- model family and model ID;
- raw and calibrated target-before-stop probability;
- target-before-stop label;
- forward return, MFE, and MAE;
- target/stop/unresolved flags;
- time to target and stop when available;
- regime and sector when available;
- selected feature manifest hash;
- calibration artifact hash.

This table is for diagnostics only and must never be joined into model feature
matrices.

## Dashboard

Candidate Detail displays, when available:

- model target-before-stop probability;
- same-archetype calibration base rate;
- same-scope calibration base rate;
- calibration evidence status;
- diagnostic threshold table;
- probability bucket evidence;
- diagnostic-only target-before-stop blocker assessment.

Reports and Exports includes the calibration audit tables in Signal Discovery
workbooks and exposes direct CSV/XLSX downloads.

Signal Board stays compact and does not show the full calibration audit.

