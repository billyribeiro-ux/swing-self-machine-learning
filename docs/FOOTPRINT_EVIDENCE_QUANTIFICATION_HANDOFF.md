# Footprint Evidence Quantification Handoff

Date: 2026-06-28

## Summary

Footprint Attribution V1 now requires each dashboard footprint claim to be backed by a measured evidence row or an explicit `Evidence unavailable` status. Candidate Detail keeps the plain-English summary at the top, then shows quantified evidence, top supportive items, top conflicts, historical analog outcomes, and a residual/unexplained component.

Signal Board stays compact. It only shows a short footprint summary such as `Risk-off inverse ETF footprint`; detailed evidence is available through Open -> Candidate Detail.

## Before / After TZA Example

Before:

> TZA is showing a bullish risk-off setup in shadow validation. The footprint is driven by expanding inverse ETF strength, active small-cap risk-off relationships, elevated volatility/range regime, broad-market relationship deterioration, and similar historical analog behavior.

After:

TZA remains a bullish shadow-validation / pending-entry candidate, but the dashboard now marks the footprint as measured and mixed. The current local Candidate Detail evidence shows:

- TZA 1-session return: `0.78%`; 5-session return: `-3.23%`; 10-session return: `-8.90%`; 20-session return: `-8.47%`.
- TZA relative volume over 20 sessions: `1.2193`.
- TZA 20-session return rank versus inverse ETF peers: `rank 7/8`.
- IWM comparison leg returns: 5 sessions `1.43%`, 20 sessions `2.67%`.
- TZA/IWM rolling correlation over 63 sessions: `-0.9972`.
- TZA/IWM inverse confirmation over 63 sessions: `0.9972`.
- ATR percent of price: `6.72%`, 14-session window, `76.18%` historical percentile.
- Realized volatility: `0.0413`, 20-session window, `65.59%` historical percentile.
- Volatility expansion: `106.73%`, 20/63-session comparison, `65.47%` historical percentile.
- Market regime label: `uptrend_high_vol`.
- Regime-conditioned return over 20 sessions: `-1.10%`.
- SPY returns: 5 sessions `-2.38%`, 20 sessions `-3.39%`.
- QQQ returns: 5 sessions `-4.60%`, 20 sessions `-3.95%`.
- IWM and DIA were conflicting broad-market evidence because their 5/20-session returns were positive.
- Historical analog count: `5`; target-before-stop hit rate: `20.00%`; average forward return: `8.61%`; median forward return: `10.89%`.
- Analog rows include date, symbol, scope, regime, similarity, forward return, MFE, MAE, and target-before-stop result.
- Residual/unexplained component: `10.00%`.

The summary remains safety-framed as shadow validation and not live actionable.

## Evidence Categories

- Expanding inverse ETF strength.
- Small-cap risk-off relationship.
- Elevated volatility/range regime.
- Broad-market relationship deterioration.
- Historical analog behavior.
- Conflicting evidence.
- Residual / unexplained.

Each evidence row carries category, claim, evidence metric, value, lookback window, percentile/rank when available, comparison instrument when applicable, supporting feature name, evidence type, strength, and missing-data status.

## Dashboard Changes

- Candidate Detail now renders:
  - `Footprint Evidence Table`
  - `Supporting Evidence`
  - `Conflicting Evidence`
  - `Historical Analogs`
  - `Residual / Unexplained`
- Signal Board now includes only the compact `Footprint Summary` column and does not expose measured evidence columns in the main board.
- Raw model/run/event identifiers remain available in Candidate Detail and CSV/XLSX exports.
- Missing measured fields continue to display `Not available` or `Evidence unavailable`, not zero.

## Exports

Candidate Detail XLSX exports now include these footprint sheets:

- `footprint_summary`
- `footprint_evidence`
- `supporting_evidence`
- `conflicting_evidence`
- `historical_analogs`
- `residual_unexplained`

Candidate Detail also exposes CSV downloads for each footprint table. Existing export sanitization remains in place for secrets/API-key-looking values.

## Tests

Added or updated tests in `tests/test_streamlit_command_center.py` covering:

- Every quantified footprint row has a non-empty claim and measured evidence or explicit unavailable status.
- TZA shadow/pending fixture shows quantified inverse ETF evidence.
- Historical analog tables include analog outcomes.
- Conflicting evidence always renders.
- Residual/unexplained evidence always renders.
- Candidate Detail shows measured footprint values below the summary.
- Signal Board stays compact and omits detailed footprint evidence columns.
- XLSX exports include all required footprint sheets.
- Rejected/shadow rows retain their existing labels and safety wording.
- Dashboard page load does not run build-features.
- Dashboard page load does not contact FMP.
- Dashboard page load does not mutate SQLite, scanner snapshots, or model artifacts.

The Streamlit AppTest coverage is included in `tests/test_streamlit_command_center.py` for Signal Board and Candidate Detail.

## Verification

Commands run in the development worktree:

- `.venv/bin/pytest` -> `349 passed, 11576 warnings in 117.00s`
- `.venv/bin/ruff check .` -> `All checks passed!`
- `.venv/bin/ruff format --check .` -> `120 files already formatted`
- `.venv/bin/mypy src` -> `Success: no issues found in 62 source files`

No FMP data update, discovery, scanner, final-holdout update, forward update, daily cycle, retraining, model promotion, or model-artifact mutation was run.

## Operational Immutability Proof

Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

- Operational HEAD before verification: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Operational status before verification: clean on `feat/autonomous-swing-scanner-v1`
- Operational HEAD after verification: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Operational status after verification: clean on `feat/autonomous-swing-scanner-v1`

Only read-only Git status/HEAD checks were run against the operational repository.

## Known Limitations

- Evidence is limited to local scanner payloads, local feature parquet, and local universe metadata; missing local metrics are displayed as unavailable.
- Historical analogs depend on analog payloads already present in scanner/candidate data.
- Percentile/rank fields are shown only where local data supports deterministic calculation.
- This work does not change model logic, feature definitions, labels, gates, thresholds, promotion rules, or signal ranking.

## Data Leakage Review

- Candidate Detail reads already-materialized local feature rows and scanner payloads.
- It does not recompute features, train models, call providers, or alter signal lifecycle state.
- It does not add label columns to a feature matrix.
- Historical analog outcomes are displayed as explanation evidence from existing candidate payloads, not used to change model predictions or dashboard ranking.

## Scope Changes

None. This is dashboard attribution evidence and export visibility only.

## Next Smallest Task

Add a compact missing-evidence audit badge to Candidate Detail that counts unavailable footprint rows by category.
