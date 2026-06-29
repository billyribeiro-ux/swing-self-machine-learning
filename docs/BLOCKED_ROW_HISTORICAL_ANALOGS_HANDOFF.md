# Blocked Row Historical Analogs Handoff

Date: 2026-06-28

## Why This Was Needed

The latest multi-angle signal discovery generation selected no BUY or
SELL/SHORT candidates. Existing historical analog rows were emitted only for
selected candidates, so the analog file had 0 rows even though high-scoring
blocked research rows existed.

This work adds read-only historical analog diagnostics for top blocked rows.
The diagnostics are explanatory only and do not override selection gates.

## Rows Analyzed

Generation:
`signal_discovery_20260628T193012+0000_cf2753a58c47`

Rows included:

- TZA `sector_rotation_buy_20d`, blocked by target-before-stop probability.
- SQQQ `sector_rotation_buy_20d`, blocked by target-before-stop probability.
- SOXS `sector_rotation_buy_20d`, rejected by OOD feature rate.
- RWM `sector_rotation_buy_20d`, blocked by target-before-stop probability.
- AMZN `sector_rotation_buy_20d`, blocked by target-before-stop probability.
- SOXS `breakdown_sell_10d`, blocked by target-before-stop probability.
- SOXS `trend_continuation_sell_10d`, blocked by target-before-stop probability.
- SOXS `breadth_deterioration_sell_10d`, blocked by target-before-stop probability.
- SOXS `pullback_continuation_sell_10d`, blocked by target-before-stop probability.
- SOXS `volatility_expansion_sell_5d`, blocked by probability.
- Highest-scoring additional probability blockers:
  `failed_breakout_sell_5d` and `reversal_sell_5d`.

All minimum requested rows were available in the current artifacts.

## Analog Method

The diagnostic reads only existing local generation artifacts and the latest
local modeling parquet. It does not run discovery, scanner, retraining, FMP
updates, final-holdout updates, forward updates, daily-cycle, or promotion.

For each target row, analog search uses the same hypothesis selected-feature
set, drops `label_` columns, fits deterministic scaling only on rows dated
strictly before the target date, and excludes target/future rows. Same-product
scope analogs are preferred. Cross-scope analogs are included only when
same-scope history is insufficient and are labeled `cross_scope_fallback`.

Outcome labels are used only for explanatory analog outcomes. Historical
threshold pass/fail is marked `not_available_existing_artifacts_only` because
the generation does not persist historical prediction rows for every prior
date, and rerunning models was out of scope.

## TZA Analog Summary

TZA `sector_rotation_buy_20d`:

- Analog count: 10
- Same-scope count: 10
- Average forward return: -1.52%
- Median forward return: -3.83%
- Positive outcomes: 3/10
- Target-before-stop hit rate: 30.00%
- Average MFE: 26.62%
- Average MAE: -9.46%
- Worst MAE: -21.14%
- Best MFE: 48.13%
- Analog support label: WEAK
- Key caution: high analog dispersion

Measured summary:

> TZA sector rotation BUY footprint remains research-only because target before
> stop probability below threshold. Historical analogs are weak with 3/10
> positive forward outcomes and average forward return -1.52%, but this is
> explanatory only and does not override the gate.

## SQQQ Analog Summary

SQQQ `sector_rotation_buy_20d`:

- Analog count: 10
- Same-scope count: 10
- Average forward return: -4.99%
- Median forward return: -8.57%
- Positive outcomes: 3/10
- Target-before-stop hit rate: 20.00%
- Average MFE: 43.16%
- Average MAE: -14.34%
- Worst MAE: -40.02%
- Best MFE: 75.99%
- Analog support label: WEAK
- Key caution: concentrated in one year

## SOXS Analog Summary

SOXS `sector_rotation_buy_20d` rejected by OOD:

- Analog count: 10
- Same-scope count: 10
- Average forward return: -47.38%
- Median forward return: -53.50%
- Positive outcomes: 0/10
- Target-before-stop hit rate: 0.00%
- Average MFE: 10.43%
- Average MAE: -50.78%
- Worst MAE: -65.06%
- Best MFE: 41.87%
- Analog support label: WEAK
- Key caution: OOD target row

SOXS SELL/SHORT target-before-stop blockers under breakdown, trend
continuation, breadth deterioration, and pullback continuation each had 10
same-scope analogs, 10/10 positive forward outcomes, 50.00%
target-before-stop hit rate, average forward return 56.07%, analog support
label SUPPORTIVE, and key caution concentrated in one ticker.

SOXS `volatility_expansion_sell_5d` probability blocker had 10 same-scope
analogs, 8/10 positive forward outcomes, 0.00% target-before-stop hit rate,
average forward return 17.52%, analog support label MIXED, and key caution
concentrated in one ticker.

## Dashboard Changes

Candidate Detail now shows **Historical Analogs for Blocked Row** when a
blocked/research discovery row has analog diagnostics.

The section includes:

- warning that analogs are explanatory only and do not override model gates;
- summary cards for analog count, average forward return,
  target-before-stop hit rate, average MFE, worst MAE, and analog support
  label;
- row-level analog table with rank, date, ticker, scope, archetype,
  similarity, forward return, MFE, MAE, target-before-stop result, same scope,
  and same archetype.

## Export Files

Signal discovery generation export now writes:

- `blocked_row_analogs.csv`
- `blocked_row_analog_summary.csv`

Reports and Exports generation workbooks include:

- `blocked_row_analogs`
- `blocked_row_analog_summary`

## Tests

Added/updated tests for:

- future-row exclusion;
- target-row exclusion;
- label-column exclusion from distance features;
- same-scope analog preference;
- cross-scope fallback labeling;
- explanation-only outcomes that do not change signal status;
- TZA blocked-row analog availability;
- SOXS OOD row analog availability and OOD caution;
- average forward return, MFE, MAE, and target-before-stop summary stats;
- deterministic analog support labels;
- Candidate Detail blocked-row analog display;
- CSV and XLSX export inclusion;
- no FMP calls in the diagnostic path;
- no model artifact mutation;
- operational repository immutability via untouched external marker in tests.

Focused verification already passed:

```bash
.venv/bin/pytest tests/test_signal_discovery.py tests/test_streamlit_command_center.py -q
```

Result: 41 passed.

Full required verification passed after the final run.

## Verification

Final required verification:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

Results:

- `.venv/bin/pytest`: 362 passed, 11576 warnings.
- `.venv/bin/ruff check .`: all checks passed.
- `.venv/bin/ruff format --check .`: 122 files already formatted.
- `.venv/bin/mypy src`: success, no issues in 63 source files.

Streamlit AppTest coverage for Candidate Detail and Reports and Exports is in
`tests/test_streamlit_command_center.py`.

Local HTTP smoke test:

```bash
.venv/bin/streamlit run dashboard/app.py --server.headless true --server.port 8507
curl -I http://localhost:8507
```

Result: `HTTP/1.1 200 OK`. The Streamlit server was stopped after the smoke
test.

No FMP update, discovery run, final-holdout update, forward update, daily-cycle,
model promotion, threshold change, gate change, label change, model-artifact
mutation, or SQLite mutation was performed.

## Operational Immutability Proof

Operational repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Initial proof captured during this task:

- Git status: clean on `feat/autonomous-swing-scanner-v1`
- HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- SQLite SHA256:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`

Final proof after verification:

- Git status: clean on `feat/autonomous-swing-scanner-v1`
- HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- SQLite SHA256:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`

The operational repository HEAD and SQLite hash were unchanged.

## Next Task

Add a compact blocked-row analog filter to Candidate Detail so reviewers can
toggle same-symbol, same-scope, and cross-scope fallback analog rows.
