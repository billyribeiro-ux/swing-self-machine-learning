# Sector Rotation BUY ORDINARY Policy Candidate Handoff

Date: 2026-06-30

Development repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Development branch: `feat/product-class-specialist-challengers-v1`

Operational repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Operational frozen run: `3493ee8ac37bf96475c362e1`

Operational enrolled model: `b93b2258c10aea5cef81d291`

Operational baseline date: 2026-06-25

## Diagnostic Conclusion

`docs/SECTOR_ROTATION_BUY_ORDINARY_TARGET_STOP_DIAGNOSTIC.md` classified the
Sector Rotation BUY `ORDINARY` 20-session target/stop policy as
`STOP_TOO_TIGHT`.

Current baseline policy:

- target: `2.0 ATR`
- stop: `1.0 ATR`
- horizon: 20 sessions
- target-before-stop hit rate: `38.41%`
- stop-before-target rate: `60.16%`
- profitable despite failed TBS: `44.51%`
- average time to target: `8.60` sessions
- average time to stop: `5.22` sessions

No model underconfidence, calibration collapse, or implementation defect was
proven.

## Selected Candidate Policy

Selection status: `CALIBRATION_SUPPORTED_POLICY_CANDIDATE`

Candidate policy:

- policy ID: `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`
- policy name: `Sector Rotation BUY Policy Candidate`
- schema: `target_stop_policy_candidate_v1`
- archetype: `sector_rotation_buy`
- action: `BUY`
- product scope: `ORDINARY`
- horizon: 20 sessions
- target: `2.0 ATR`
- stop: `1.25 ATR`
- status: `EXPERIMENTAL_CANDIDATE`
- policy hash:
  `b4aa8260a7d90f574b0c2677b96ff947a810aeb81242120399aed9fa12ba400b`

Selection reason: the precommitted calibration-only rule preferred the same
target and same horizon, then selected the smallest stop increase above
`1.0 ATR` that improved target-before-stop hit rate, reduced
stop-before-target rate, preserved forward-return evidence, improved expected
R and utility, and did not worsen symbol/year/regime concentration.

Development-holdout diagnostics were not used to choose this policy.

## Policy Registry Schema

The registry is documented in `docs/TARGET_STOP_POLICY_REGISTRY.md`.

Required fields:

- `policy_id`
- `policy_name`
- `archetype`
- `action`
- `product_scope`
- `horizon`
- `target_multiple`
- `stop_multiple`
- `entry_timing`
- `signal_known_timing`
- `time_exit_behavior`
- `same_bar_target_stop_ambiguity_policy`
- `cost_slippage_policy_reference`
- `selection_source`
- `governance_status`
- `created_timestamp`
- `policy_hash`

Allowed statuses:

- `DEFAULT_BASELINE`
- `EXPERIMENTAL_CANDIDATE`
- `RETIRED`
- `RESEARCH_ONLY`

The default baseline policy remains registered separately as
`sector_rotation_buy_ordinary_20d_default_t2p0_s1p0` and remains unchanged.

## Calibration-Only Selection Evidence

Calibration split: `calibration_only`

Evidence source:
`docs/SECTOR_ROTATION_BUY_ORDINARY_TARGET_STOP_DIAGNOSTIC.md`

| Policy | Target | Stop | Horizon | Rows | TBS hit rate | Stop-before-target | Unresolved | Expected R | Utility | Symbol conc | Year conc | Regime conc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 2.0 | 1.0 | 20 | 11,017 | 0.3841 | 0.6016 | 0.0143 | 0.1745 | 0.0036 | 0.0435 | 0.5219 | 0.3612 |
| Candidate | 2.0 | 1.25 | 20 | 11,017 | 0.4380 | 0.5360 | 0.0260 | 0.2190 | 0.0047 | 0.0435 | 0.5219 | 0.3612 |

The candidate also preserved the same average forward return, median forward
return, average MFE, average MAE, and worst MAE as the baseline because those
path-distribution fields are measured on the same calibration rows.

## Implementation Summary

New policy support:

- added typed target/stop policy registry in
  `src/swing_rsi/engine/target_stop_policy.py`;
- added separate baseline and experimental policy definitions;
- added calibration-only selection result persistence;
- derived candidate-policy outcomes without overwriting existing labels;
- kept candidate labels prefixed with `label_`;
- kept label columns excluded from model features;
- added policy IDs, status, names, and hashes to hypotheses, candidate rows,
  gate rows, calibration artifacts, score components, and exports;
- added the experimental hypothesis
  `sector_rotation_buy_ordinary_20d_target_stop_candidate_v1`;
- kept the default `sector_rotation_buy_20d` hypothesis available as the
  baseline.

The experimental policy does not replace the default policy, lower thresholds,
weaken gates, weaken OOD governance, promote models, or create live actionable
signals.

## Generated Discovery Result

Exactly one discovery generation was run after tests passed.

Generation ID: `signal_discovery_20260630T125903+0000_874cd03874d2`

Export directory:
`reports/sector_rotation_buy_ordinary_policy_candidate_v1`

Generation summary:

- hypotheses evaluated: `16`
- BUY candidates: `0`
- SELL/SHORT candidates: `0`
- NO_SIGNAL rows: `520`
- rejected rows: `1`
- selected candidates: `0`

Every experimental-policy row remained research/shadow only.

## Baseline Versus Candidate Discovery Comparison

| Hypothesis | Scope | Rows | Selected | NO_SIGNAL | Rejected | TBS-blocked | Avg score | Avg TBS p | Avg expected return |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `sector_rotation_buy_20d` | `ORDINARY` | 23 | 0 | 23 | 0 | 22 | 0.4973 | 0.3593 | 0.0031 |
| `sector_rotation_buy_ordinary_20d_target_stop_candidate_v1` | `ORDINARY` | 23 | 0 | 23 | 0 | 23 | 0.4746 | 0.4606 | -0.0300 |

The candidate policy raised average model TBS probability in current
`ORDINARY` Sector Rotation rows, but it did not pass the current 0.50
target-before-stop probability gate and did not create BUY candidates.

Top experimental-policy rows:

| Ticker | Score | TBS p | Expected return | Expected MFE | Expected MAE | Reason |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| IWM | 0.5228 | 0.4560 | -0.0227 | 0.1243 | -0.0660 | `target_before_stop_probability_below_threshold` |
| XLK | 0.4928 | 0.4560 | -0.0149 | 0.1359 | -0.1233 | `target_before_stop_probability_below_threshold` |
| XLF | 0.4896 | 0.4560 | -0.0214 | 0.0570 | -0.0537 | `target_before_stop_probability_below_threshold` |
| XLE | 0.4861 | 0.4560 | -0.0257 | 0.0567 | -0.0577 | `target_before_stop_probability_below_threshold` |
| SPY | 0.4843 | 0.4710 | -0.0296 | 0.0553 | -0.0594 | `target_before_stop_probability_below_threshold` |

## Calibration Summary For Candidate Hypothesis

For `sector_rotation_buy_ordinary_20d_target_stop_candidate_v1`,
`ORDINARY` scope:

| Model family | Rows | Positive TBS | Negative TBS | Base rate | Model Brier | Naive Brier | Brier skill | ROC-AUC | PR-AUC | ECE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `hist_gradient_boosting` | 11,017 | 4,825 | 6,192 | 0.4380 | 0.2439 | 0.2462 | 0.0023 | 0.5298 | 0.4560 | 0.0000 |
| `extra_trees` | 11,017 | 4,825 | 6,192 | 0.4380 | 0.2453 | 0.2462 | 0.0008 | 0.5167 | 0.4496 | 0.0000 |

## Dashboard Changes

Signal Board:

- keeps display compact with `target_stop_policy_display`.

Candidate Detail:

- shows Target/Stop Policy details;
- shows baseline versus candidate metrics;
- shows calibration-only selection evidence;
- shows exact derived policy outcomes when available;
- includes the warning:

```text
Experimental target/stop policy. Development evidence only. Not a live signal.
```

Reports and Exports:

- includes policy frames in the Signal Discovery workbook;
- exposes the new generated policy CSV/JSON artifacts.

Gate Audit:

- keeps canonical model gates unchanged;
- adds a separate Signal Discovery policy-gate view when policy fields are
  available.

## Exports

The export directory contains policy-specific files:

- `target_stop_policy_registry.csv`
- `target_stop_policy_registry.json`
- `calibration_selection.csv`
- `sector_rotation_buy_ordinary_policy_comparison.csv`
- `derived_policy_outcomes.csv`
- `signal_discovery_policy_comparison.csv`

Export row counts:

- `target_stop_policy_registry.csv`: `2`
- `calibration_selection.csv`: `4`
- `sector_rotation_buy_ordinary_policy_comparison.csv`: `2`
- `derived_policy_outcomes.csv`: `59,920`
- `signal_discovery_policy_comparison.csv`: `5`
- `calibration_summary.csv`: `150`
- `diagnostic_thresholds.csv`: `1,050`
- `probability_buckets.csv`: `1,500`
- `row_level_calibration_audit.csv`: `512,330`

The export command completed successfully. It emitted pandas mixed-type
`DtypeWarning` messages while loading wide CSV artifacts; no export file was
missing and the process exited successfully.

## Tests And Verification

Tests added or updated:

- default policy remains unchanged;
- experimental policy is registered separately;
- experimental policy is `ORDINARY` / Sector Rotation / BUY only;
- policy selection uses calibration-only evidence;
- development holdout cannot choose the policy;
- no-candidate cases persist explicit status;
- candidate labels are separate from baseline labels;
- existing label parquet is not overwritten in place;
- policy ID is persisted on derived outcomes, hypothesis results, and gate rows;
- policy ID appears in Signal Board rows;
- Candidate Detail shows baseline versus candidate policy;
- label columns do not enter feature matrices;
- chronological splits and OOD governance remain unchanged;
- experimental policy cannot produce live actionable rows or promote models;
- CSV/XLSX exports work;
- no FMP calls occur in tests;
- no model artifacts are mutated in tests;
- operational repository remains untouched in tests.

Verification run:

- `.venv/bin/pytest` -> `370 passed, 11576 warnings`
- `.venv/bin/ruff check .` -> passed
- `.venv/bin/ruff format --check .` -> `123 files already formatted`
- `.venv/bin/mypy src` -> passed
- Streamlit AppTest coverage for Signal Board, Candidate Detail, and Reports
  and Exports passed through `tests/test_streamlit_command_center.py`
- Local HTTP smoke:
  `.venv/bin/streamlit run dashboard/app.py --server.headless true --server.port 8766 --server.address 127.0.0.1`
  plus `curl -I http://127.0.0.1:8766` -> `HTTP/1.1 200 OK`

## Operational Immutability Proof

Before implementation:

- operational HEAD:
  `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- operational Git status:
  `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- operational SQLite size: `250781696`
- operational SQLite mtime ns: `1782585787422972957`
- operational SQLite hash:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- enrolled model artifact size: `30529057`
- enrolled model artifact mtime ns: `1782393801212695748`
- enrolled model artifact hash:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- scanner snapshot count: `18`
- ordinary forward-event count: `285`
- final-holdout event count: `25`
- prospective run ID: `3493ee8ac37bf96475c362e1`
- baseline date: `2026-06-25`

After verification:

- operational HEAD:
  `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- operational Git status:
  `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- operational SQLite size: `250781696`
- operational SQLite mtime ns: `1782585787422972957`
- operational SQLite hash:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- enrolled model artifact size: `30529057`
- enrolled model artifact mtime ns: `1782393801212695748`
- enrolled model artifact hash:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- scanner snapshot count: `18`
- ordinary forward-event count: `285`
- final-holdout event count: `25`
- prospective run ID: `3493ee8ac37bf96475c362e1`
- baseline date: `2026-06-25`

All before and after values match.

## Safety Confirmation

Confirmed:

- no operational repository files were modified;
- no operational SQLite state changed;
- no operational model artifact changed;
- no FMP update ran;
- no scanner ran in the operational repository;
- no final-holdout update ran;
- no forward update ran;
- no daily cycle ran;
- no production thresholds or gates were weakened;
- no model was promoted;
- no live actionable signal was created by the experimental policy.

## Data Leakage Review

The experimental policy keeps the existing chronology rules:

- signal rows remain daily-close-known;
- default entry remains next trading session open;
- feature selection is fit on training data only;
- calibrators are fit on calibration data only;
- development holdout is evaluation only;
- candidate-policy labels are versioned diagnostics and remain outside feature
  matrices.

## Known Limitations

- The candidate did not create selected BUY or SELL/SHORT candidates in the
  new generation.
- Current candidate rows remain below the existing `0.50` TBS probability
  gate.
- The current live cohort is still concentrated in `uptrend_high_vol`.
- The export command emitted non-fatal pandas mixed-type warnings while
  reading wide CSV artifacts.
- The policy is not production eligible without future prospective validation.

## Next Engineering Task

Add a time-exit utility label for Sector Rotation BUY `ORDINARY`.
