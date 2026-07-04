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
- target/stop policy ID, status, hash, target multiple, and stop multiple when
  a hypothesis uses an explicit policy

The default config evaluates BUY and SELL/SHORT hypotheses, including examples
such as `trend_continuation_buy_10d`, `reversal_sell_5d`,
`risk_off_buy_inverse_10d`, and `sector_rotation_buy_20d`.

RSI is not required by any default hypothesis. It is one candidate feature
family among many.

## Target/Stop Policy Candidates

Signal Discovery now supports versioned target/stop policy definitions under
`target_stop_policy_candidate_v1`.

The default Sector Rotation BUY 20-day hypothesis remains available as:

- `sector_rotation_buy_20d`
- baseline policy `sector_rotation_buy_ordinary_20d_default_t2p0_s1p0`
- target `2.0 ATR`, stop `1.0 ATR`, horizon 20 sessions

The experimental candidate is:

- `sector_rotation_buy_ordinary_20d_target_stop_candidate_v1`
- policy `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`
- `ORDINARY` scope only
- BUY action only
- Sector Rotation archetype only
- target `2.0 ATR`, stop `1.25 ATR`, horizon 20 sessions
- status `EXPERIMENTAL_CANDIDATE`

The candidate was selected by the precommitted calibration-only rule from
`docs/SECTOR_ROTATION_BUY_ORDINARY_TARGET_STOP_DIAGNOSTIC.md`: same target and
horizon first, then the smallest wider stop that improves TBS hit rate, lowers
stop-before-target rate, preserves forward-return evidence, improves expected R
or utility, and does not worsen concentration.

The candidate does not replace the default policy, lower thresholds, weaken
OOD governance, bypass gates, create live actionable rows, or promote models.

## Time-Exit Utility Diagnostics

Signal Discovery also supports
`sector_rotation_buy_ordinary_time_exit_utility_v1` as a label-side diagnostic
schema for Sector Rotation BUY `ORDINARY` rows at the 20-session horizon.

The experimental hypothesis is:

- `sector_rotation_buy_ordinary_20d_time_exit_utility_v1`
- `ORDINARY` scope only
- BUY action only
- Sector Rotation archetype only
- 20-session horizon
- associated with
  `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`

The hypothesis persists both target-before-stop evidence and time-exit evidence:

- TBS probability remains present and gated.
- Time-exit positive probability is modeled as an additional diagnostic target.
- Expected time-exit net return is modeled as a diagnostic return target.
- Expected time-exit utility is modeled as a diagnostic utility target.
- Profitable-despite-failed-TBS and early-adverse-recovery probabilities are
  persisted as separate components when the labels have class support.

Time-exit labels do not replace TBS labels, do not lower thresholds, do not
weaken OOD governance, do not bypass gates, and do not create live actionable
signals.

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

Experimental policy outcomes are derived in memory for the discovery run and
persisted as generated artifacts. Existing label parquet files are not
overwritten. Candidate-policy label columns remain prefixed with `label_`, and
feature selection still rejects every `label_` column before model fitting.
Time-exit label-side columns containing `time_exit`, `utility`,
`profitable_despite_failed_tbs`, or `early_adverse_recovery` are also blocked
from feature matrices.

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

Historical Analog Robustness Guard V1 adds depth-aware diagnostics for blocked
rows. It evaluates top 10, top 25, and top 50 analog sets, persists
concentration and tail-risk caution flags, and classifies evidence as
`ROBUST_SUPPORT`, `SUPPORTIVE_BUT_CONCENTRATED`, `MIXED_SUPPORT`,
`WEAK_SUPPORT`, `INSUFFICIENT_ANALOGS`, `CONCENTRATION_ARTIFACT`, or
`DECAYS_WITH_DEPTH`. A strong top-10 cluster no longer receives robust-support
language when support decays with depth or depends on one ticker, year, regime,
scope, or local event cluster.

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
- `analog_robustness.csv` when exported
- `analog_robustness_summary.csv` when exported
- `analog_depth_comparison.csv` when exported
- `analog_caution_flags.csv` when exported
- `score_components.csv`
- `gate_results.csv`
- `calibration_summary.csv`
- `calibration_summary.json`
- `probability_distributions.csv`
- `probability_buckets.csv`
- `diagnostic_thresholds.csv`
- `row_level_calibration_audit.parquet`
- `row_level_calibration_audit.csv`
- `calibration_artifact_manifest.json`

Parquet copies are also written for generation-local artifact use.

Calibration audit artifacts use schema
`multi_angle_calibration_audit_v1`. They are created from the chronological
calibration slice only and are diagnostic only. They do not change target-before-
stop thresholds, gates, OOD governance, signal status, model promotion, scanner
state, paper-forward events, or final-holdout state. See
`docs/MULTI_ANGLE_CALIBRATION_AUDIT.md`.

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
- Analog Status
- Edge Status
- Candidate Status
- Next Required Event

Candidate Detail keeps the original historical analog table, adds blocked-row
robustness cards for top-10/top-25/top-50 support, robust support label, caution
flags, concentration summary, depth-decay explanation, and adds calibration
diagnostics for model TBS probability, same-archetype/scope calibration base
rates, diagnostic thresholds, and probability buckets. Calibration sections are
explicitly labeled diagnostic only.

Candidate Detail shows the signal score breakdown and carries full raw IDs into
detail links and exports.

Reports and Exports can create a Signal Discovery Generation workbook with
summary, metadata, hypotheses, candidates, selected candidates, no-signal rows,
rejected rows, footprint evidence, historical analogs, blocked-row analogs,
blocked-row analog summaries, score components, gate results, and calibration
audit frames.

Policy-candidate exports include:

- `target_stop_policy_registry.csv`
- `target_stop_policy_registry.json`
- `calibration_selection.csv`
- `sector_rotation_buy_ordinary_policy_comparison.csv`
- `derived_policy_outcomes.csv`
- `signal_discovery_policy_comparison.csv`

Time-exit utility exports include:

- `time_exit_utility_labels.csv`
- `time_exit_utility_calibration_summary.csv`
- `time_exit_utility_signal_rows.csv`
- `time_exit_utility_policy_comparison.csv`

Dashboard workbooks expose the policy sheets as `policy_registry`,
`calibration_selection`, `baseline_vs_candidate`, `derived_outcomes`,
`signal_rows`, and `gates` when data is available. Time-exit utility workbook
sheets include `time_exit_labels`, `calibration_summary`, `signal_rows`, and
`policy_comparison`.

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
