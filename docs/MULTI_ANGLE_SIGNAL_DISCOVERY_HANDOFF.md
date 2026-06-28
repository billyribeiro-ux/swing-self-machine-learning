# Multi-Angle Signal Discovery V1 Handoff

Date: 2026-06-28

Development branch: `feat/product-class-specialist-challengers-v1`

Operational frozen run: `3493ee8ac37bf96475c362e1`

## Why This Was Needed

The existing infrastructure was strong, but scanner discovery was concentrated
around one target-before-stop path. V1 adds a governed self-learning discovery
layer that evaluates multiple signal hypotheses across different market
footprints while preserving chronology, label isolation, OOD governance, and
promotion/final-holdout boundaries.

## Implemented Hypotheses

Schema: `multi_angle_signal_discovery_v1`

Default archetypes:

- Trend Continuation
- Reversal / Exhaustion
- Breakout / Breakdown
- Pullback Continuation
- Risk-On / Risk-Off
- Sector Rotation
- Volatility Expansion
- Volatility Compression Release
- Breadth Thrust / Breadth Deterioration
- Failed Move / Liquidity Trap Proxy

Default hypotheses include BUY and SELL/SHORT variants such as:

- `trend_continuation_buy_10d`
- `trend_continuation_sell_10d`
- `reversal_buy_5d`
- `reversal_sell_5d`
- `breakout_buy_10d`
- `breakdown_sell_10d`
- `risk_off_buy_inverse_10d`
- `sector_rotation_buy_20d`
- `volatility_expansion_sell_5d`
- `failed_breakout_sell_5d`

RSI is not required by any default hypothesis. It is only one candidate feature
family.

## BUY / SELL / NO_SIGNAL Definitions

- `BUY_CANDIDATE`: BUY hypothesis passes research selection policy.
- `SELL_SHORT_CANDIDATE`: SELL/SHORT hypothesis passes research selection policy.
- `NO_SIGNAL`: evidence is below policy threshold or incomplete.
- `REJECTED_BY_OOD`: OOD feature rate is above policy limit.
- `REJECTED_BY_POLICY`: candidate cap or explicit policy rejects the row.
- `SHADOW_ONLY`: candidate is research/shadow only, not live actionable.
- `RESEARCH_ONLY`: no-signal or unsupported research row.

No row is live actionable without a promoted model and existing live gates.

## Signal Score Formula

The persisted score is transparent:

```text
signal_score =
  0.35 * direction_probability
+ 0.20 * target_before_stop_probability
+ 0.20 * expected_return_score
+ 0.10 * expected_mfe_score
+ 0.08 * expected_mae_score
+ 0.07 * liquidity_score
- 0.10 * ood_penalty
- 0.05 * conflict_penalty
- 0.03 * concentration_penalty
```

All components are persisted in `score_components.csv`.

## Footprint Integration

Signal Board now shows compact all-angle fields:

- Action
- Archetype
- Signal Score
- Footprint Summary
- Top Support
- Top Conflict
- Historical Analog Support
- Edge Status
- Candidate Status
- Next Required Event

Candidate Detail shows signal score breakdown plus footprint evidence,
supporting/conflicting evidence, historical analogs, residual/unexplained, and
raw identifiers. Discovery candidates carry artifact-backed evidence and analog
JSON into Candidate Detail.

## Historical Analog Method

For selected BUY/SELL candidates, analogs are computed from rows strictly before
the candidate date using the same selected hypothesis feature set. Analog rows
include analog date, symbol, scope, regime, similarity, forward return, MFE, MAE,
and target-before-stop result.

Analog outcomes are explanatory only and are not used to change selection.

The latest V1 generation selected no BUY/SELL candidates, so analog files are
empty for that generation.

## CLI Commands

```bash
.venv/bin/python -m swing_rsi.cli discover-signals
.venv/bin/python -m swing_rsi.cli signal-discovery-status
.venv/bin/python -m swing_rsi.cli signal-discovery-export --generation latest --output reports/signal_discovery_v1
```

These commands do not promote models, run scanner, run final-holdout-update, run
forward-update, run daily-cycle, update FMP data, or mutate operational state.

## Dashboard Changes

- Signal Board supports all-angle rows and filters by Action and Archetype.
- Candidate Detail displays `Signal Score Breakdown`.
- Reports and Exports includes a Signal Discovery Generation export section.
- Full raw IDs remain available in Candidate Detail and exports.
- Page load reads local artifacts only.

## Generation Results

Latest valid generation:

`signal_discovery_20260628T193012+0000_cf2753a58c47`

Feature manifest:

`3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`

Latest decision date: `2026-06-26`

Summary:

- Hypotheses evaluated: 15
- BUY candidates: 0
- SELL candidates: 0
- NO_SIGNAL rows: 497
- Rejected rows: 1
- Selected candidates: 0

Hypothesis/model-family statuses:

- `CANDIDATE` / `final_holdout_required_for_promotion`: 28
- `REJECTED` / `expected_utility_insufficient`: 2

Latest-row decisions:

- `NO_SIGNAL` / `RESEARCH_ONLY`: 497
- `REJECTED_BY_OOD`: 1

Top NO_SIGNAL archetypes:

- Trend Continuation: 70
- Reversal / Exhaustion: 70
- Breakout / Breakdown: 70
- Pullback Continuation: 70
- Failed Move / Liquidity Trap Proxy: 70
- Volatility Expansion: 35
- Volatility Compression Release: 35
- Breadth Thrust / Breadth Deterioration: 35
- Sector Rotation: 34
- Risk-On / Risk-Off: 8

Top rows by score were still blocked:

- TZA, Sector Rotation BUY, score `0.642860`, blocked by target-before-stop probability below threshold.
- SQQQ, Sector Rotation BUY, score `0.641488`, blocked by target-before-stop probability below threshold.
- SOXS, Breakdown SELL, score `0.579257`, blocked by target-before-stop probability below threshold.
- SOXS, Pullback Continuation SELL, score `0.579257`, blocked by target-before-stop probability below threshold.
- SOXS, Trend Continuation SELL, score `0.579257`, blocked by target-before-stop probability below threshold.

Rejected row:

- SOXS, Sector Rotation BUY, `REJECTED_BY_OOD`, reason `ood_feature_rate_above_limit`, score `0.62411`.

Gate results:

- `minimum_training_samples`: 15 PASS
- `minimum_calibration_samples`: 15 PASS
- `minimum_holdout_samples`: 15 PASS

Export:

`reports/signal_discovery_v1/` with 11 files:

- `metadata.json`
- `summary.csv`
- `hypotheses.csv`
- `candidates.csv`
- `selected_candidates.csv`
- `no_signal.csv`
- `rejected.csv`
- `footprint_evidence.csv`
- `historical_analogs.csv`
- `score_components.csv`
- `gate_results.csv`

## Tests Added

- `tests/test_signal_discovery.py`
- Streamlit Command Center tests for Signal Board, Candidate Detail, and Reports/Exports discovery visibility.

Coverage proves:

- registry loads;
- every hypothesis has direction, horizon, labels, and feature families;
- BUY and SELL hypotheses both exist;
- RSI is not privileged or required;
- labels do not enter selected feature matrices;
- feature screening is training-only;
- calibration is calibration-only;
- holdout is evaluation-only;
- analogs exclude future rows;
- analog outcomes are explanatory only;
- NO_SIGNAL rows persist;
- rejected rows preserve reasons;
- no row becomes live actionable without promotion;
- score components persist;
- dashboard shows action/archetype and signal score breakdown;
- CSV/XLSX export works;
- no FMP calls are made by tests;
- SQLite and model artifacts are not mutated by page load;
- operational-like paths are untouched.

## Verification

Commands run in development:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
.venv/bin/pytest tests/test_streamlit_command_center.py -k "signal_board or candidate_detail or reports_and_exports"
curl -I http://localhost:8765
```

Results:

- `pytest`: 358 passed, 11576 warnings.
- `ruff check .`: all checks passed.
- `ruff format --check .`: 122 files already formatted.
- `mypy src`: success, no issues in 63 source files.
- Streamlit AppTest subset: 8 passed.
- HTTP smoke: `HTTP/1.1 200 OK`.

No pandas PerformanceWarning was observed during verification. No FMP request was
made by the new tests or dashboard page loads.

## Operational Immutability Proof

Before and after values match.

- Operational HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- Operational Git status: clean on `feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- SQLite hash: `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- Enrolled model artifact hash in SQLite: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- Enrolled model artifact file hash: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- Scanner snapshot count: 18
- Ordinary forward-event count: 285
- Final-holdout event count: 25
- Prospective run ID: `3493ee8ac37bf96475c362e1`
- Baseline date: `2026-06-25`
- Run status: `COLLECTING`
- Latest processed market date: `2026-06-26`

No operational source file, SQLite row, model artifact, scanner snapshot,
forward event, or final-holdout event was modified.

## Data Leakage Review

- No random split is used.
- Feature screen fits on training rows only.
- Imputer and OOD reference quantiles fit on training rows only.
- Probability calibration fits on calibration rows only.
- Development holdout is used for evaluation only.
- Historical analogs use rows before the candidate date only.
- Label columns remain physically separated from feature matrices.
- Analog outcomes are explanatory only.

## Known Limitations

- Current V1 policy produced no BUY/SELL candidates on the latest local snapshot.
- Latest selected-candidate, footprint-evidence, and analog files are empty
  because no BUY/SELL row passed selection.
- Time-to-target and time-to-stop labels are sparse and optional evaluation
  fields; they are not required to co-occur for model fitting.
- The dashboard reads existing generation artifacts only; it does not run
  discovery automatically.
- No model was promoted and no final-holdout run was initialized.

## Launch Command

```bash
.venv/bin/streamlit run dashboard/app.py --server.headless true --server.port 8765
```

## Files Changed

- `configs/signal_discovery/v1.yaml`
- `src/swing_rsi/engine/signal_discovery.py`
- `src/swing_rsi/application/engine_service.py`
- `src/swing_rsi/application/dashboard_service.py`
- `src/swing_rsi/application/footprint_attribution.py`
- `src/swing_rsi/cli.py`
- `dashboard/sections/signal_board.py`
- `dashboard/sections/candidate_detail.py`
- `dashboard/sections/reports_and_exports.py`
- `tests/test_signal_discovery.py`
- `tests/test_streamlit_command_center.py`
- `docs/MULTI_ANGLE_SIGNAL_DISCOVERY.md`
- `docs/MULTI_ANGLE_SIGNAL_DISCOVERY_HANDOFF.md`
- `docs/CHANGELOG.md`
- `docs/DECISIONS.md`

## Exact Assumptions Introduced

- Existing local modeling parquet is the only training/evaluation source.
- Path timing labels are valid when present but sparse; they are evaluation
  diagnostics, not required fit labels.
- BUY/SELL discovery candidates are shadow/research only unless future promoted
  model governance explicitly qualifies them.

## Scope Changes

No Version 1 scope expansion. No options, intraday data, brokerage execution,
deep learning, reinforcement learning, news/NLP, or new external model library
was added.

## Next Smallest Task

Add a read-only signal-discovery blocker report that summarizes NO_SIGNAL and
REJECTED reasons by hypothesis, archetype, ticker, and product scope.
