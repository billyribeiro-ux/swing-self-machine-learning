# Multi-Angle Signal Discovery V1

Schema: `multi_angle_signal_discovery_v1`

Generation type: `signal_discovery_generation`

## Purpose

Autonomous Multi-Angle Signal Discovery V1 broadens scanner research beyond one
target-before-stop path. It evaluates multiple typed signal hypotheses across
market footprints, directions, horizons, model families, and product scopes,
then persists auditable BUY, SELL, NO_SIGNAL, rejected, shadow-only, and
research-only rows.

No V1 output is live actionable by itself. Promotion still requires the existing
model governance, OOD, scanner, and prospective final-holdout gates.

## Archetypes

The default registry includes these discovery lenses:

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

These are discovery hypotheses, not hardcoded trading rules.

## Hypothesis Spec

Each `SignalHypothesisSpec` records:

- `archetype_id`
- direction: `BUY` or `SELL_SHORT`
- horizon
- eligible product scopes
- required and candidate feature families
- outcome label names
- model tasks
- selection policy
- validation policy
- footprint categories
- explanation template
- governance version

The default config evaluates BUY and SELL/SHORT hypotheses, including examples
such as `trend_continuation_buy_10d`, `reversal_sell_5d`,
`risk_off_buy_inverse_10d`, and `sector_rotation_buy_20d`.

RSI is not required by any default hypothesis. It is one candidate feature
family among many.

## Chronology

For each hypothesis:

1. Build eligible rows from the local modeling parquet.
2. Apply chronological train/calibration/development-holdout splits.
3. Fit feature screening on training rows only.
4. Fit preprocessing on training rows only.
5. Train model heads on training rows only.
6. Fit probability calibration on calibration rows only.
7. Evaluate on development holdout rows only.
8. Score latest rows using the fitted development model.
9. Persist selected, no-signal, rejected, evidence, analog, and gate rows.

No random split is used. Label columns remain separate from feature matrices.

## Model Families

V1 supports:

- `hist_gradient_boosting`
- `extra_trees`

Naive/base-rate behavior is retained as a comparison concept through holdout
skill metrics. Unsupported model family requests are rejected by config
validation.

## Score

The persisted composite score is transparent:

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

All components are persisted in `score_components.csv`. The score does not hide
promotion state. A strong research score is still not live actionable without a
promoted model and existing live gates.

## Decisions

Latest symbol/date/hypothesis rows resolve to:

- `BUY_CANDIDATE`
- `SELL_SHORT_CANDIDATE`
- `NO_SIGNAL`
- `REJECTED_BY_POLICY`
- `REJECTED_BY_GATE`
- `REJECTED_BY_OOD`
- `REJECTED_BY_CONFLICT`
- `SHADOW_ONLY`
- `RESEARCH_ONLY`

In the current implementation, BUY/SELL candidates are classified as
`SHADOW_ONLY`; NO_SIGNAL rows are classified as `RESEARCH_ONLY`.

## Historical Analogs

For selected BUY/SELL candidates, nearest analogs are computed from rows before
the candidate date using the same hypothesis feature set. Analog rows include
forward return, MFE, MAE, target-before-stop result, and a similarity score.

Analog outcomes are explanatory only and are not used to change the selected
signal after the fact.

Blocked/research rows now have a separate read-only diagnostic export:
`blocked_row_analogs.csv` and `blocked_row_analog_summary.csv`. These rows are
computed from existing local generation artifacts and the latest local modeling
parquet without rerunning discovery or models. They use the matching hypothesis
feature set, exclude `label_` columns from distance calculations, use only rows
strictly before the target row date, prefer same-product-scope analogs, and
label cross-scope fallback rows when same-scope history is too small. Blocked
analog support is explanatory only and cannot change row status, gates,
thresholds, OOD governance, model promotion, paper-forward events, or scanner
selection.

## Artifacts

Generation artifacts are written under ignored local paths:

```text
artifacts/signal_discovery/<generation_id>/
reports/signal_discovery_<generation_id>.json
reports/signal_discovery_v1/
```

Core files:

- `metadata.json`
- `summary.csv`
- `hypotheses.csv`
- `candidates.csv`
- `selected_candidates.csv`
- `no_signal.csv`
- `rejected.csv`
- `footprint_evidence.csv`
- `historical_analogs.csv`
- `blocked_row_analogs.csv` when exported
- `blocked_row_analog_summary.csv` when exported
- `score_components.csv`
- `gate_results.csv`

Parquet copies are also written for generation-local artifact use.

## CLI

Run one local discovery generation:

```bash
.venv/bin/python -m swing_rsi.cli discover-signals
```

Inspect latest status:

```bash
.venv/bin/python -m swing_rsi.cli signal-discovery-status
```

Export latest generation:

```bash
.venv/bin/python -m swing_rsi.cli signal-discovery-export --generation latest --output reports/signal_discovery_v1
```

Summarize latest blockers without rerunning discovery:

```bash
.venv/bin/python -m swing_rsi.cli signal-discovery-blockers --generation latest --limit 10
```

Export blocker summary sheets:

```bash
.venv/bin/python -m swing_rsi.cli signal-discovery-blockers-export --generation latest --output reports/signal_discovery_blockers_v1
```

These commands do not promote models, run final-holdout updates, run
forward-update, run daily-cycle, or contact FMP.

## Dashboard

Signal Board now supports discovery rows with:

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

Candidate Detail shows the signal score breakdown and carries full raw IDs into
detail links and exports.

Reports and Exports can create a Signal Discovery Generation workbook with
summary, metadata, hypotheses, candidates, selected candidates, no-signal rows,
rejected rows, footprint evidence, historical analogs, blocked-row analogs,
blocked-row analog summaries, score components, and gate results.

Reports and Exports can also create a Signal Discovery Blockers workbook with:

- `summary`
- `metadata`
- `blocker_rows`
- `by_reason`
- `by_hypothesis`
- `by_archetype`
- `by_ticker`
- `by_scope`

The same Reports and Exports page also renders a read-only blocker review panel
with summary cards, by-reason/by-hypothesis/by-archetype/by-ticker/by-scope
drilldowns, and the highest-scoring blocked rows. Highest-scoring blocked rows
include Candidate Detail links built from the raw generation, ticker, model, and
direction identifiers. The panel reads local signal discovery generation
artifacts only; it does not run discovery, scanner, FMP updates, final-holdout
updates, forward updates, or daily-cycle commands.

## Current V1 Generation

Latest validation generation:

`signal_discovery_20260628T193012+0000_cf2753a58c47`

Feature manifest:

`3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`

Results:

- Hypotheses evaluated: 15
- BUY candidates: 0
- SELL candidates: 0
- NO_SIGNAL rows: 497
- Rejected rows: 1
- Selected candidates: 0

The top NO_SIGNAL blockers were target-before-stop probability below threshold
and probability below threshold. One row, SOXS under `sector_rotation_buy_20d`,
was rejected by OOD.

Current blocker report:

- Blocker rows: 498
- NO_SIGNAL rows: 497
- Rejected rows: 1
- Distinct tickers: 35
- Distinct hypotheses: 15
- Top blocker reason: `probability_below_threshold`
- `probability_below_threshold`: 280 rows
- `target_before_stop_probability_below_threshold`: 217 rows
- `ood_feature_rate_above_limit`: 1 row

## Limitations

- V1 produced no BUY/SELL candidates under the current governed policy.
- Selected-candidate analog artifacts are empty when no BUY/SELL candidate is
  selected; blocked-row analog diagnostics remain available as read-only
  explanatory reports when enough historical local modeling rows exist.
- Time-to-target and time-to-stop labels are optional evaluation metrics because
  they are sparse path fields; they are not required to co-occur for model
  fitting.
- This layer is not wired to promotion, final-holdout enrollment, forward
  updates, scanner mutation, or daily-cycle automation.
