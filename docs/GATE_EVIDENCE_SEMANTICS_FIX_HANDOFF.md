# Gate Evidence Semantics Fix Handoff

## Confirmed Defects

- `profit_factor_min_090` could persist contradictory evidence: `actual_value = inf`, `comparator = >=`, `threshold = 0.9`, and `status = FAIL`.
- `symbol_concentration_max_050`, `sector_concentration_max_080`, and `exceptional_period_concentration_max_060` could fail while retaining pass-sounding reason text.

## Previous Behavior

- Profit factor encoded every no-loss selected-return set as positive infinity, including zero selected rows and all-zero selected returns.
- The profit-factor gate required `math.isfinite()` before evaluating the stored comparator, so valid positive infinity failed.
- Concentration gates used one generic reason string for pass and fail cases.
- Dashboard and audit exports did not clearly distinguish valid positive infinity from unavailable profit-factor evidence.

## Corrected Profit-Factor Truth Table

| Case | Evidence | Actual value | Gate status | Reason behavior |
| --- | --- | --- | --- | --- |
| Selected rows, gains > 0, gross loss = 0 | AVAILABLE | `Infinity` | PASS for `>= 0.90` | States gains exist and no losses occurred. |
| Selected rows with gains and losses | AVAILABLE | gross profit / gross loss | Comparator result | States whether value meets or misses minimum. |
| Selected rows, no gains, no losses | UNAVAILABLE | `NOT_AVAILABLE` | FAIL for learned models | States all selected returns were zero. |
| Learned model, zero selected rows | UNAVAILABLE | `NOT_AVAILABLE` | FAIL | States no selected observations exist. |
| Naive control, zero selected rows | NOT_APPLICABLE | `NOT_AVAILABLE` | NOT_APPLICABLE, non-mandatory | States trading-performance evidence is not comparable for the zero-selection control. |

## Comparator Behavior

- `>=` accepts finite values above or equal to the threshold and accepts positive infinity.
- `>=` rejects negative infinity, NaN, missing values, and unavailable evidence.
- `<=` accepts finite values below or equal to the threshold and mathematically evaluates infinities instead of treating all nonfinite values the same.
- Metric-specific availability is resolved before comparator evaluation.

## Reason-Text Behavior

- Profit-factor reasons are generated from canonical evidence status and comparator result.
- Concentration reasons now match status:
  - FAIL: actual concentration exceeds the maximum.
  - PASS: actual concentration is within the maximum.
  - NOT_APPLICABLE: concentration is unavailable because no rows were selected.
- `GateResult` exports include a non-mutating `evidence_integrity_warning` for legacy rows whose status contradicts actual/comparator/threshold evidence.

## Dashboard and Export Representation

- Dashboard:
  - Valid positive infinity displays as `Infinity` in source data and as `∞` in Model Registry tables.
  - Unavailable evidence displays as `Not available`.
- CSV/JSON exports:
  - Valid positive infinity is represented as the explicit string `Infinity`.
  - Unavailable evidence is represented as `NOT_AVAILABLE`.
  - Legacy contradictory rows remain readable and unchanged; warnings are added only to audit/export views.

## Tests

Added coverage for:

- Positive-infinity profit factor from `[0.01, 0.02]`.
- Positive infinity passing `>= 0.9`.
- Positive infinity not failing because it is nonfinite.
- Finite gain/loss profit factor calculation.
- Finite profit factor equal to `0.9` passing.
- Finite profit factor below `0.9` failing.
- Zero selected rows for learned models producing unavailable evidence and FAIL.
- Zero selected rows for naive controls producing NOT_APPLICABLE.
- All-zero selected returns producing unavailable evidence.
- NaN and negative infinity not passing a minimum gate.
- Status-matched symbol, sector, and exceptional-period concentration reasons.
- Dashboard display distinguishing infinity from unavailable.
- CSV/JSON export representation distinguishing infinity from unavailable.
- Promotion eligibility using corrected gate results.
- Legacy contradictory gate rows remaining readable and unmutated.
- Focused gate evidence tests making no FMP calls.

## Verification Results

- `.venv/bin/pytest`: collected 138; passed 138; failed 0; skipped 0; warnings 161.
- Focused tests: `.venv/bin/pytest tests/test_model_evaluation_integrity.py tests/test_dashboard_model_registry.py tests/test_dashboard_interactions.py::test_model_registry_renders_compact_table_with_registered_models -q`: passed 41.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: passed; 92 files already formatted.
- `.venv/bin/mypy src`: passed; no issues in 54 source files.

## Commit Hash

- Final local commit hash is reported by Codex after commit creation. A committed file cannot contain its own final hash without changing that hash.

## Remaining Limitations

- Existing immutable model artifacts and historical gate rows are not rewritten. Legacy contradictions remain in stored evidence but are flagged in audit/export views.
- No models were retrained, no FMP data was updated, no scanner or forward-update was run against persistent state, and no model was promoted.
- MFE/MAE regression behavior and OOD governance were not changed.
