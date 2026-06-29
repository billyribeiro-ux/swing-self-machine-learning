# Blocked Row Historical Analogs

Date: 2026-06-28

Schema addition: `blocked_row_analogs` and `blocked_row_analog_summary`

## Purpose

The current multi-angle signal discovery generation selected no BUY or
SELL/SHORT candidates, so `historical_analogs.csv` is empty. That is correct
for selected-candidate artifacts, but it leaves high-scoring blocked research
rows without historical context.

Blocked-row historical analogs are a read-only diagnostic layer for research
review. They do not change candidate status, selection, gates, thresholds, OOD
governance, labels, model artifacts, scanner artifacts, SQLite state,
paper-forward events, or promotion eligibility.

## Method

For each top blocked target row, the diagnostic reads the existing local signal
discovery generation artifacts and the latest local modeling parquet. It does
not run discovery, scanner, FMP updates, retraining, final-holdout updates,
forward updates, or daily-cycle commands.

Target rows are selected from existing `NO_SIGNAL` and `REJECTED_*` discovery
rows:

- top five Bullish blocked rows by `signal_score`;
- top five Bearish blocked rows by `signal_score`;
- top rows for `probability_below_threshold`;
- top rows for `target_before_stop_probability_below_threshold`;
- top rows for `ood_feature_rate_above_limit`.

For each target row, the diagnostic:

1. Uses the matching hypothesis and model-family `selected_features`.
2. Drops every `label_` column from the distance feature set.
3. Uses only historical rows dated strictly before the target `as_of_date`.
4. Excludes the target row and all future rows by date.
5. Fits deterministic median imputation and standard-deviation scaling on the
   historical candidate pool only.
6. Prefers same-product-scope analog rows.
7. Adds cross-scope rows only when same-scope history is insufficient, marking
   those rows as `cross_scope_fallback`.
8. Persists whether each analog is same-symbol, same-product-scope,
   same-archetype, and same-direction.

The current artifacts do not persist historical prediction rows for every prior
date, so `analog_would_have_passed_current_thresholds` and
`analog_rejection_reason` are explicitly marked
`not_available_existing_artifacts_only`. The diagnostic does not rerun models to
fill those fields.

## Outputs

Generation export now includes:

- `blocked_row_analogs.csv`
- `blocked_row_analog_summary.csv`
- `analog_robustness.csv`
- `analog_robustness_summary.csv`
- `analog_depth_comparison.csv`
- `analog_caution_flags.csv`

Reports and Exports includes matching XLSX sheets:

- `blocked_row_analogs`
- `blocked_row_analog_summary`
- `analog_robustness`
- `analog_robustness_summary`
- `analog_depth_comparison`
- `analog_caution_flags`

Candidate Detail shows a dedicated **Historical Analogs for Blocked Row**
section when a blocked/research row has analog diagnostics. The section includes
summary cards, a row-level analog table, and this warning:

> Historical analogs are explanatory only and do not override model gates.

## Latest Generation Summary

Generation reviewed:
`signal_discovery_20260628T193012+0000_cf2753a58c47`

The diagnostic produced 120 analog rows and 12 target-row summary rows.

| Target | Hypothesis | Blocker | Analogs | Same-scope | Avg return | TBS hit rate | Avg MFE | Worst MAE | Label | Caution |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| TZA | `sector_rotation_buy_20d` | target-before-stop below threshold | 10 | 10 | -1.52% | 30.00% | 26.62% | -21.14% | WEAK | high analog dispersion |
| SQQQ | `sector_rotation_buy_20d` | target-before-stop below threshold | 10 | 10 | -4.99% | 20.00% | 43.16% | -40.02% | WEAK | concentrated in one year |
| SOXS BUY | `sector_rotation_buy_20d` | OOD feature rate above limit | 10 | 10 | -47.38% | 0.00% | 10.43% | -65.06% | WEAK | OOD target row |
| SOXS SELL/SHORT | `breakdown_sell_10d` | target-before-stop below threshold | 10 | 10 | 56.07% | 50.00% | 75.59% | -26.16% | SUPPORTIVE | concentrated in one ticker |
| SOXS SELL/SHORT | `trend_continuation_sell_10d` | target-before-stop below threshold | 10 | 10 | 56.07% | 50.00% | 75.59% | -26.16% | SUPPORTIVE | concentrated in one ticker |
| SOXS SELL/SHORT | `breadth_deterioration_sell_10d` | target-before-stop below threshold | 10 | 10 | 56.07% | 50.00% | 75.59% | -26.16% | SUPPORTIVE | concentrated in one ticker |
| SOXS SELL/SHORT | `pullback_continuation_sell_10d` | target-before-stop below threshold | 10 | 10 | 56.07% | 50.00% | 75.59% | -26.16% | SUPPORTIVE | concentrated in one ticker |
| SOXS SELL/SHORT | `volatility_expansion_sell_5d` | probability below threshold | 10 | 10 | 17.52% | 0.00% | 31.23% | -26.16% | MIXED | concentrated in one ticker |
| RWM | `sector_rotation_buy_20d` | target-before-stop below threshold | 10 | 10 | 0.32% | 60.00% | 6.06% | -3.28% | MIXED | concentrated in one ticker |
| AMZN | `sector_rotation_buy_20d` | target-before-stop below threshold | 10 | 10 | 0.29% | 0.00% | 3.75% | -23.55% | MIXED | concentrated in one year |

Analog support labels are research summaries only, not proof of edge.

## Robustness Guard

Historical Analog Robustness Guard V1 adds depth-aware support classification on
top of the blocked-row analog output. It recomputes analog summaries at top 10,
top 25, and top 50, persists concentration and tail-risk caution flags, and
replaces simple support language with robust labels:

- `ROBUST_SUPPORT`
- `SUPPORTIVE_BUT_CONCENTRATED`
- `MIXED_SUPPORT`
- `WEAK_SUPPORT`
- `INSUFFICIENT_ANALOGS`
- `CONCENTRATION_ARTIFACT`
- `DECAYS_WITH_DEPTH`

For the latest generation, the SOXS 10-day SELL rows that looked `SUPPORTIVE`
at top 10 are now classified as `CONCENTRATION_ARTIFACT`: the top-10 analogs
were all SOXS from 2026, top-25 and top-50 support fell to `MIXED`, and
target-before-stop hit rate decayed from 50.00% at top 10 to 28.00% at top 50.

The robust label is still explanatory only. It does not change blocked row
status, rejected status, gates, thresholds, OOD governance, scanner state, model
artifacts, or paper-forward events.
