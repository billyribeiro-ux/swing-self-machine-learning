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
- read-only blocked-row analog payloads computed from existing signal discovery
  generation artifacts and local modeling parquet.

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
6. Historical Analogs for Blocked Row when available
7. Historical Analog Robustness when blocked-row analogs are available
8. Residual / Unexplained

The Missing Evidence Audit counts `Evidence unavailable` footprint rows by
category. Missing measurements remain explicit and are not treated as
confirmed evidence.

Blocked-row analog sections must display the warning: `Historical analogs are
explanatory only and do not override model gates.`

Historical Analog Robustness shows top-10, top-25, and top-50 support, robust
support label, caution flags, concentration summary, and depth-decay
explanation. A top-10 analog cluster can be marked `CONCENTRATION_ARTIFACT` when
it is concentrated in one ticker/year/regime/event cluster and support degrades
with expanded analog depth.

The Signal Board remains compact and shows only a short footprint summary such
as `Risk-off inverse ETF footprint`, plus a compact analog status such as
`Mixed Analog Support` or `Concentration Artifact`.

## Exports

Candidate Detail workbook exports include:

- `footprint_summary`
- `footprint_evidence`
- `supporting_evidence`
- `conflicting_evidence`
- `historical_analogs`
- `blocked_row_analogs`
- `blocked_row_analog_summary`
- `analog_robustness`
- `analog_depth_comparison`
- `analog_caution_flags`
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
