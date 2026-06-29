# Historical Analog Robustness Guard V1

Date: 2026-06-29

Schema: `historical_analog_robustness_v1`

## Purpose

Historical Analog Robustness Guard V1 hardens blocked-row analog diagnostics so
research review does not overstate a strong nearest-neighbor cluster. The guard
evaluates analog outcomes at multiple depths, records concentration and tail-risk
flags, and replaces the simple top-10 analog support label with a robust support
classification.

This remains an explanatory layer only. It does not change signal status,
selection, gates, thresholds, OOD governance, labels, model artifacts, scanner
state, SQLite state, paper-forward events, or model promotion eligibility.

## Inputs

The guard reads existing local signal-discovery artifacts and the local modeling
parquet through the blocked-row analog diagnostic path. It does not run
discovery, scanner, FMP updates, retraining, final-holdout updates,
forward-update, or daily-cycle.

Analog search keeps the prior diagnostic contract:

- use only rows strictly before the target row `as_of_date`;
- exclude the target row and all future rows;
- use the matching hypothesis feature set;
- drop every `label_` column from distance features;
- fit deterministic scaling only on the historical analog pool;
- prefer same product scope and label cross-scope fallback rows;
- persist same-symbol, same-scope, same-archetype, and same-direction markers.

## Robustness Depths

Every blocked/research target row with analogs is summarized at:

- top 10;
- top 25;
- top 50.

If fewer rows exist for a requested depth, the actual count is preserved and
`low_analog_count` is raised. The production blocked-row analog table still
keeps its default top-10 row output; robustness uses expanded depths only for
diagnostic classification.

For each depth, the guard persists:

- analog count;
- same-symbol, same-scope, and same-archetype counts and shares;
- same-year and same-regime maximum counts and shares;
- average and median forward return;
- win rate;
- target-before-stop hit rate;
- average MFE and MAE;
- worst MAE and best MFE;
- return standard deviation;
- analog dispersion score;
- average similarity, minimum similarity, and maximum distance.

## Labels

Allowed robust labels:

- `ROBUST_SUPPORT`
- `SUPPORTIVE_BUT_CONCENTRATED`
- `MIXED_SUPPORT`
- `WEAK_SUPPORT`
- `INSUFFICIENT_ANALOGS`
- `CONCENTRATION_ARTIFACT`
- `DECAYS_WITH_DEPTH`

Rules are deterministic:

- `INSUFFICIENT_ANALOGS`: fewer than 10 valid pre-target analogs exist.
- `CONCENTRATION_ARTIFACT`: top-10 is supportive, concentration flags are active,
  and support or TBS evidence decays at top 25 or top 50.
- `DECAYS_WITH_DEPTH`: top-10 is supportive but top 25 or top 50 becomes mixed or
  weak without a dominant concentration flag.
- `SUPPORTIVE_BUT_CONCENTRATED`: support survives expanded depths, but
  concentration flags remain active.
- `ROBUST_SUPPORT`: support remains supportive across available depths without
  excessive concentration, return dispersion, or MAE tail risk.
- `WEAK_SUPPORT`: nearest-depth analog outcomes are weak.
- `MIXED_SUPPORT`: all other non-robust mixed evidence.

The rules are not tuned to make SOXS pass. The SOXS 10-day SELL cluster from the
2026-06-28 generation is classified as `CONCENTRATION_ARTIFACT`.

## Caution Flags

Caution flags are persisted separately from the support label. Multiple flags can
apply to one target row.

Required flags:

- `same_symbol_concentration`
- `same_year_concentration`
- `same_regime_concentration`
- `same_scope_scarcity`
- `low_analog_count`
- `high_return_dispersion`
- `high_mae_tail_risk`
- `tbs_support_decay`
- `support_decays_top25`
- `support_decays_top50`
- `ood_target_row`
- `analogs_mostly_same_event_cluster`

## Outputs

Derived report files are written under `reports/signal_discovery_v1/`:

- `analog_robustness.csv`
- `analog_robustness_summary.csv`
- `analog_depth_comparison.csv`
- `analog_caution_flags.csv`
- `analog_robustness.json`
- `analog_robustness.xlsx`

Signal-discovery exports include CSV files for:

- `analog_robustness`
- `analog_robustness_summary`
- `analog_depth_comparison`
- `analog_caution_flags`

Reports and Exports workbooks include XLSX sheets for the same tables.

Candidate Detail shows the original top-10 blocked-row analog table plus:

- top-10, top-25, and top-50 support labels;
- robust support label;
- caution flags;
- concentration summary;
- depth-decay explanation;
- the warning that historical analogs are explanatory only and do not override
  model gates.

Signal Board shows a compact analog status such as `Robust Analog Support`,
`Mixed Analog Support`, `Concentration Artifact`, or `Insufficient Analogs`.

## Current Generation Result

Generation:
`signal_discovery_20260628T193012+0000_cf2753a58c47`

Derived robustness summary:

- target rows: 12;
- `ROBUST_SUPPORT`: 0;
- `SUPPORTIVE_BUT_CONCENTRATED`: 0;
- `MIXED_SUPPORT`: 5;
- `WEAK_SUPPORT`: 3;
- `INSUFFICIENT_ANALOGS`: 0;
- `CONCENTRATION_ARTIFACT`: 4;
- `DECAYS_WITH_DEPTH`: 0.

SOXS 10-day SELL rows were the intended hardening case. Their old top-10 label
was `SUPPORTIVE`; the robust label is now `CONCENTRATION_ARTIFACT` because
10/10 top analogs were SOXS from 2026, top-25/top-50 support downgraded to
`MIXED`, and target-before-stop hit rate decayed from 50.00% at top 10 to
28.00% at top 50.

Analog support remains research evidence only and is not proof of edge.
