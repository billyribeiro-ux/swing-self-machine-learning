# Footprint Attribution Engine

## Purpose

Footprint Attribution V1 turns Candidate Detail footprint language into measured
dashboard evidence. It is a display and export layer over existing scanner,
feature, universe, and analog artifacts. It does not change features, labels,
models, gates, thresholds, scanner selection, or paper-forward state.

## Evidence Contract

Every footprint claim must have either:

- a measured evidence row; or
- explicit `Evidence unavailable` status.

The dashboard must not present missing evidence as confirmed. Footprint evidence
is model evidence, not causal proof and not live trading guidance.

## Data Sources

The evidence layer reads local development artifacts only:

- selected Candidate Detail scanner row;
- latest local feature parquet under `data/features/`;
- local universe configuration under `configs/universe/core.yaml`;
- compact historical analog payloads already stored in scanner rows.

It does not contact FMP, run `build-features`, run discovery, run the scanner,
mutate SQLite, or modify model artifacts during page load.

## Categories

V1 emits measured rows for:

- expanding inverse ETF strength;
- small-cap risk-off relationship;
- elevated volatility/range regime;
- broad-market relationship deterioration;
- historical analog behavior;
- conflicting evidence;
- residual / unexplained attribution.

Each row records:

- category;
- claim;
- evidence metric;
- value;
- lookback window;
- percentile or rank when available;
- comparison instrument when applicable;
- supporting feature name;
- evidence type: `supportive`, `conflicting`, or `neutral`;
- strength label;
- missing-data status.

## Candidate Detail Display

Candidate Detail renders:

1. Missing Evidence Audit badge and category table
2. Footprint Evidence Table
3. Supporting Evidence
4. Conflicting Evidence
5. Historical Analogs
6. Residual / Unexplained

The Missing Evidence Audit counts `Evidence unavailable` footprint rows by
category. Missing measurements remain explicit and are not treated as
confirmed evidence.

The Signal Board remains compact and shows only a short footprint summary such
as `Risk-off inverse ETF footprint`.

## Exports

Candidate Detail workbook exports include:

- `footprint_summary`
- `footprint_evidence`
- `supporting_evidence`
- `conflicting_evidence`
- `historical_analogs`
- `residual_unexplained`

CSV exports are available for the same measured tables.

## Safety Language

Allowed wording includes:

- model evidence;
- supporting evidence;
- conflicting evidence;
- historical analog;
- shadow validation;
- not live actionable;
- prospective evidence collecting.

Avoid wording that implies proof, causality, promotion, or trading instruction.
