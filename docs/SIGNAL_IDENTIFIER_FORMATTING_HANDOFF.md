# Signal Identifier Formatting Handoff

Date: 2026-06-28

## Summary

Signal Board now shows friendly display identifiers for model, generation, run,
and event columns while preserving full raw IDs for audit paths.

Visible examples from the current development Signal Board:

- Model: `POOL Bull HGB 10D · 5b3f37a`
- Generation: `Gen 2026-06-27 14:05`
- Run: `Dev Shadow Run · d25d6fa1`
- Event: `Pending Entry · b75bad88`

The model example is `POOL` because the current displayed development model is a
pooled product-class model. Ordinary product-class models display as `ORD`.

## Files Changed

- `src/swing_rsi/application/dashboard_service.py`
- `dashboard/sections/signal_board.py`
- `tests/test_streamlit_command_center.py`
- `docs/SIGNAL_FIRST_DASHBOARD.md`
- `docs/CHANGELOG.md`
- `docs/SIGNAL_IDENTIFIER_FORMATTING_HANDOFF.md`

## Implementation

`signal_board_frame` now returns display-only fields alongside the raw fields:

- `model_display`
- `generation_display`
- `run_display`
- `event_display`

Raw fields remain present:

- `model_id`
- `generation`
- `run_id`
- `event_id`

Signal Board visible tables use the display-only fields and rename them to
`Model`, `Generation`, `Run`, and `Event`. The backing frame used by CSV/XLSX
exports remains unchanged except for the added display columns, so raw full IDs
remain exportable.

`Open detail` links still call `candidate_detail_url(...)` with full raw
identifiers. Candidate Detail query parameters continue to receive full
`scan_id`, `ticker`, `model_id`, `direction`, `run_id`, `event_id`, and
`status` values.

Missing MFE/MAE display behavior is unchanged: missing values render as
`Not available`, not zero.

## Tests Added Or Updated

- Extended `test_signal_first_tables_label_live_shadow_and_missing_paths` to
  verify friendly model, generation, run, and event labels plus raw ID retention.
- Added `test_signal_board_visible_table_uses_friendly_ids_but_exports_raw_ids`
  to verify:
  - visible Signal Board columns use friendly labels;
  - raw ID columns are not shown in the compact visible table;
  - CSV export retains `model_id`, `run_id`, and `event_id`;
  - XLSX export retains `model_id`, `run_id`, and `event_id`.
- Existing page-load safety tests still cover no build-features execution, no
  FMP download, and no SQLite/model-artifact mutation during dashboard page load.
- Existing Candidate Detail link test still verifies full raw identifiers are
  passed through the `Open detail` URL.

## Verification Results

Final verification on the formatted tree:

- `.venv/bin/pytest`
  - Result: `346 passed, 11576 warnings in 138.19s`
  - Warnings were existing pandas constant-input and joblib NumPy deprecation
    warnings.
- `.venv/bin/ruff check .`
  - Result: `All checks passed!`
- `.venv/bin/ruff format --check .`
  - Result: `119 files already formatted`
- `.venv/bin/mypy src`
  - Result: `Success: no issues found in 61 source files`

Focused dashboard verification before the full run:

- `.venv/bin/pytest tests/test_streamlit_command_center.py -q`
  - Result: `25 passed in 3.48s`

Read-only development Signal Board sample confirmed:

- full raw model ID remained `5b3f37a96a7968bca8d2f398`;
- full raw run ID remained `d25d6fa11a2e50daa430c15e`;
- full raw pending event ID remained `b75bad88ada4dd671a60e514`;
- `open_url` continued to include those full raw identifiers.

## Operational Immutability

Operational repository:

- Path: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`
- HEAD before work: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- HEAD after verification: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Status before work: clean on `feat/autonomous-swing-scanner-v1`
- Status after verification: clean on `feat/autonomous-swing-scanner-v1`

No operational files were edited. No operational SQLite, artifacts, scanner
snapshots, forward events, or final-holdout state were mutated.

## Data Leakage Review

This task changed dashboard presentation only. It did not modify feature
definitions, labels, model code, thresholds, gates, scanner logic, product-class
mappings, or event lifecycle rules. Friendly labels are derived only from
existing local scanner/model/event metadata already present in the Signal Board
data path.

## Assumptions Introduced

- Product-class display abbreviations:
  - `ORDINARY` -> `ORD`
  - `POOLED` -> `POOL`
  - `INVERSE` -> `INV`
  - `LEVERAGED_LONG` -> `LEV`
  - `LEVERAGED_INVERSE` -> `LEV INV`
- Model short ID uses the first 7 characters.
- Run and event short IDs use the first 8 characters.
- Generation labels display minute precision from the stored timestamp.
- The visible run label is `Dev Shadow Run` for run-linked Signal Board rows.

## Known Limitations

- Unknown model families fall back to uppercase initials rather than a curated
  abbreviation.
- Rows without run or event identifiers display `Not available` for the
  corresponding friendly label.
- This does not add a hover/copy control for full IDs in the compact Signal
  Board table; full IDs remain available through Candidate Detail and exports.

## Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

## Scope Changes

None. This is dashboard visibility and export-preservation work only.

## Next Smallest Task

Add a compact copy-to-clipboard affordance for full raw IDs in Candidate Detail.
