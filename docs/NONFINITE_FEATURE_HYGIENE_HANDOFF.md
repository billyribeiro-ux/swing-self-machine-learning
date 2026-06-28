# Nonfinite Feature Hygiene V1 Handoff

## Scope

Implemented `model_feature_nonfinite_hygiene_v1` in the development worktree:

- Repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`
- Branch: `feat/product-class-specialist-challengers-v1`
- Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- Frozen operational run: `3493ee8ac37bf96475c362e1`
- Frozen operational model: `b93b2258c10aea5cef81d291`
- Frozen operational baseline date: `2026-06-25`

No FMP update, forward-update, daily-cycle, model promotion, or final-holdout initialization was run.

## Confirmed Root Cause

The Product-Class Specialist V2 generation `2026-06-26T12:37:53.103302+00:00` rejected the three `INVERSE` bull models because a model input matrix contained nonfinite feature values.

Confirmed trigger:

- Feature: `obv_change_20`
- Symbols: `RWM`, `SH`
- Date: `2016-07-19`
- Value: `-inf`
- Root cause: missing nonfinite model-input hygiene
- Contributing cause: scope-specific data-quality issue in the small `INVERSE` bull cohort

The defect was reproduced from persisted local development state before implementation.

## Feature-Generation Fix

`obv_change_20` no longer uses raw `pct_change(20)`. It now uses the project safe-divide semantics:

- finite numerator divided by zero or near-zero denominator returns `NaN`
- zero divided by zero returns `NaN`
- no positive or negative infinity is produced

Raw OHLCV and labels are not modified by this hygiene policy.

## Model-Matrix Guard

Added `src/swing_rsi/engine/feature_hygiene.py` with schema:

`model_feature_nonfinite_hygiene_v1`

Policy:

- `+inf` becomes `NaN`
- `-inf` becomes `NaN`
- finite values with absolute magnitude above `1.0e308` become `NaN`
- existing `NaN` remains missing
- default zero-fill is never used
- train-fitted missingness and imputation handle sanitized values

The guard is applied before feature screening, preprocessing, imputation, estimator fit, calibration prediction, development-holdout prediction, scanner prediction, permutation importance, and path-head helper predictions.

Artifacts now persist:

- hygiene schema and policy hash
- pre-sanitization invalid counts
- post-sanitization invalid counts
- affected columns
- affected feature families
- affected symbols and dates
- split and stage records

Post-sanitization invalid values reject the artifact with:

`model_feature_matrix_nonfinite_after_sanitization`

Legacy artifacts remain readable and are labeled:

`legacy_pre_nonfinite_hygiene`

## Scanner Behavior

Scanner prediction uses the frozen artifact hygiene policy and training-fitted preprocessing path. Scanner identity now includes the hygiene metadata hash.

Scanner identity details:

- Schema version: `11`
- Implementation version: `scanner-cache-identity-v11-nonfinite-hygiene`
- Hygiene policy hash: `d04a54687983b7c6`

Live scanner rows record hygiene warnings and runtime hygiene metadata. Nonfinite values do not reach estimators.

## Tests

Added coverage for:

- `obv_change_20` cannot produce positive infinity
- `obv_change_20` cannot produce negative infinity
- zero or near-zero OBV denominator produces `NaN`
- raw OHLCV is not mutated
- labels are not mutated
- feature matrices sanitize `+inf`, `-inf`, and too-large float64 values
- train-fitted imputation handles sanitized values
- calibration and holdout use train-fitted imputation
- scanner uses frozen artifact preprocessing
- no estimator receives infinity
- hygiene counts persist in artifact metadata
- post-sanitization invalid values reject explicitly
- synthetic `INVERSE` bull `obv_change_20=-inf` fixture fits after sanitization
- feature screening still rejects labels and remains train-only
- scanner identity changes when hygiene metadata changes
- tests do not mutate operational state
- automated tests make no FMP calls

## Commits

Implementation commits:

- `7638400` - `fix: sanitize nonfinite model features`
- `3858b92` - `test: validate nonfinite feature hygiene`
- `4d4ef7e` - `docs: document nonfinite feature hygiene`

Additional defect fix required before the successful generation:

- `b6f4abd` - `fix: preserve dtype-safe screening hygiene`

The first discovery attempt failed before generation registration because sanitized float matrices were assigned back into integer-typed screening columns. Commit `b6f4abd` fixed that dtype-safe screening boundary. The successful discovery run happened after that fix.

## Verification

Final development checks:

- `.venv/bin/pytest`: `294 passed, 10522 warnings`
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: `101 files already formatted`
- `.venv/bin/mypy src`: passed, `59 source files`

No source verification failure remains.

## New Development Generation

Exactly one successful post-fix discovery generation was created:

`2026-06-26T23:52:15.769542+00:00`

Generation result:

- Models registered: `30`
- States: `30 CANDIDATE`
- Rejected models: `0`
- Scopes: `POOLED 6`, `ORDINARY 6`, `INVERSE 6`, `LEVERAGED_LONG 6`, `LEVERAGED_INVERSE 6`
- Families: `ExtraTrees 10`, `HistGradientBoosting 10`, `naive_base_rate 10`
- Promotions: `0`
- Prospective final-holdout runs created: `0`
- Forward events created: `0`

Audit export:

- `reports/nonfinite_feature_hygiene_v1/model_matrix.csv`
- `reports/nonfinite_feature_hygiene_v1/nonfinite_records.csv`
- `reports/nonfinite_feature_hygiene_v1/failed_gates.csv`
- `reports/nonfinite_feature_hygiene_v1/old_vs_new_inverse_bull.csv`
- `reports/nonfinite_feature_hygiene_v1/audit_summary.md`

Generation-level nonfinite hygiene:

- Pre-sanitization invalid counts by scope: `INVERSE 12`, all other scopes `0`
- Post-sanitization invalid counts by scope: all scopes `0`
- Pre-sanitization invalid feature: `obv_change_20`
- Affected symbols/dates: `RWM 2016-07-19`, `SH 2016-07-19`

## Old Versus New INVERSE Bull

| Family | Old model | Old state | New model | New state | Artifact created | Pre invalid | Post invalid | Sanitized columns | Fixed blocker |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| ExtraTrees | `e69014f0935f168bfc634ced` | `REJECTED` | `08bba055822c6a3ec3e3eee4` | `CANDIDATE` | yes | 4 | 0 | `obv_change_20` | yes |
| HistGradientBoosting | `d8575e49ecbdaf5c2d632d28` | `REJECTED` | `04790e90bc24fe007ed1327d` | `CANDIDATE` | yes | 4 | 0 | `obv_change_20` | yes |
| Naive base rate | `b73235138085ed2e82fbc22b` | `REJECTED` | `c69b62b0485d727ac5bd05b4` | `CANDIDATE` | yes | 4 | 0 | `obv_change_20` | yes |

The previous unhandled-infinity rejection did not recur. This is a fit-integrity improvement, not evidence of model-quality improvement.

## Review-Only Scanner

One development review-only scanner snapshot was run after gate-integrity checks:

- Scan ID: `014743b90ec3913cd252a5cf`
- As-of date: `2026-06-25`
- Generation model set: `2026-06-26T23:52:15.769542+00:00`
- Total rows: `50`
- Rows by scope: `POOLED 23`, `ORDINARY 5`, `INVERSE 3`, `LEVERAGED_LONG 9`, `LEVERAGED_INVERSE 10`
- Rows by direction: `Bearish 25`, `Bullish 25`
- Candidate status: `REJECTED 50`
- Rejection reason: `model_not_promoted 50`
- Actionable rows: `0`
- Scope mismatch rejections: `0`
- Scanner hygiene warning rows: `0`
- Scanner pre-sanitization invalid total: `0`
- Scanner post-sanitization invalid total: `0`

No ordinary forward-update was run.

## Development State

Before discovery:

- SQLite size: `167120896`
- SQLite mtime ns: `1782480834262170674`
- Scanner snapshots: `1`
- Forward events: `0`
- Final-holdout runs: `0`

After final verification:

- SQLite size: `275734528`
- SQLite mtime ns: `1782521879429638251`
- Scanner snapshots: `2`
- Forward events: `0`
- Final-holdout runs: `0`
- Representative artifact: `artifacts/models/a7dfa02734a3631d1add7ea1.joblib`
- Representative artifact size: `337292738`
- Representative artifact mtime ns: `1782518265820518922`
- Representative artifact SHA256: `c18e30c07da6804d3dac1900e5b9a824636a55d57f1a808270b34a2a9496b181`

Development Git status after checks contains only preserved untracked prior diagnostic documents:

- `docs/PRODUCT_CLASS_SPECIALIST_CHALLENGER_V1_HANDOFF.md`
- `docs/PRODUCT_CLASS_SPECIALIST_EVIDENCE_DIAGNOSIS.md`
- `docs/PRODUCT_CLASS_SPECIALIST_V2_EVIDENCE_DIAGNOSIS.md`

This handoff file is newly created by the current task.

## Operational Immutability Proof

Operational checkout:

- Path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Git status: clean
- SQLite size: `250183680`
- SQLite mtime ns: `1782420716279369529`
- Scanner snapshots: `17`
- Forward events: `285`
- Final-holdout runs: `1`

Frozen run:

- Run ID: `3493ee8ac37bf96475c362e1`
- Status: `CREATED`
- Generation: `2026-06-25T13:11:51.610283+00:00`
- Baseline market date: `2026-06-25`
- Creation commit: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Enrolled model: `b93b2258c10aea5cef81d291`
- Development gate eligible at enrollment: `1`
- Research only: `0`
- Frozen artifact hash: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- Frozen artifact SHA256: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- Frozen artifact size: `30529057`
- Frozen artifact mtime ns: `1782393801212695748`

Operational repository was not modified. No operational discovery artifact, scanner snapshot, forward event, or final-holdout event was created by this development task.

## Data Leakage Review

- Feature rows remain close-known and trailing.
- Label columns remain excluded from feature matrices.
- Feature screening remains train-only.
- Imputation remains train-fitted and is applied to calibration, development holdout, and scanner rows.
- Sanitized nonfinite values become missing feature values, not zero-valued market signals.
- Raw OHLCV and labels are unchanged.
- The generated evidence is still `DEVELOPMENT_HOLDOUT`, not final-holdout proof.

## Assumptions Introduced

- `1.0e308` is the safe finite float64 guard for model feature matrices.
- Positive infinity, negative infinity, and too-large finite values are invalid feature inputs and should be treated as missing values.
- Existing train-fitted missingness and imputation policy is the correct downstream handling for sanitized invalid feature inputs.

## Known Limitations

- The fix proves input hygiene and fit integrity, not predictive quality.
- Development artifacts generated after this change are new artifacts; legacy artifacts are read-only and labeled rather than rewritten.
- The scanner review snapshot stayed non-actionable because all models remain unpromoted candidates.
- The first discovery attempt failed before a generation was registered; the dtype-safe screening fix was required before the successful single post-fix generation.

## Scope Changes

No V1 boundary expansion occurred. No options, intraday data, NLP, live execution, broker integration, deep learning, reinforcement learning, label changes, gate weakening, calibration-governance changes, OOD-governance weakening, or threshold changes were introduced.

## Next Smallest Task

Perform a read-only evidence diagnosis on generation `2026-06-26T23:52:15.769542+00:00` to confirm whether Nonfinite Feature Hygiene V1 changed only fit integrity or also materially changed specialist development evidence.
