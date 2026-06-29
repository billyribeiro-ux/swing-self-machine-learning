# Historical Analog Robustness Guard V1 Handoff

Date: 2026-06-29

Development repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Development branch: `feat/product-class-specialist-challengers-v1`

Operational repository: `/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Signal-discovery generation:
`signal_discovery_20260628T193012+0000_cf2753a58c47`

## Why This Was Needed

The confirmed SOXS SELL diagnosis in
`docs/SOXS_SELL_SUPPORTIVE_ANALOG_BLOCKER_DIAGNOSIS.md` classified the first
strong SOXS SELL analog pattern as `ANALOG_CONCENTRATION_ARTIFACT`. Top-10
analogs looked supportive, but they were entirely SOXS from 2026; top-25 and
top-50 expansion degraded to mixed support and target-before-stop rates
converged toward same-symbol and same-scope base rates.

Historical Analog Robustness Guard V1 prevents this kind of concentrated top-10
cluster from being described as robust analog evidence.

## Confirmed SOXS Artifact

For `breakdown_sell_10d`, `trend_continuation_sell_10d`,
`breadth_deterioration_sell_10d`, and `pullback_continuation_sell_10d`:

- old top-10 analog label: `SUPPORTIVE`;
- robust label: `CONCENTRATION_ARTIFACT`;
- top-10 analogs: 10/10 SOXS and 10/10 from 2026;
- top-10 average forward return: 56.07%;
- top-10 win rate: 100.00%;
- top-10 target-before-stop hit rate: 50.00%;
- top-50 average forward return: 22.11%;
- top-50 win rate: 76.00%;
- top-50 target-before-stop hit rate: 28.00%;
- top-50 same-symbol share: 96.00%;
- active flags: `same_symbol_concentration`,
  `same_year_concentration`, `high_return_dispersion`,
  `high_mae_tail_risk`, `tbs_support_decay`, `support_decays_top25`,
  `support_decays_top50`, `analogs_mostly_same_event_cluster`.

`volatility_expansion_sell_5d` remains `MIXED_SUPPORT`, not robust support.

## Robustness Schema

Schema: `historical_analog_robustness_v1`

Each target row is summarized at top 10, top 25, and top 50. Each depth records
analog count, same-symbol/scope/archetype shares, same-year and same-regime
maximum shares, forward return statistics, win rate, target-before-stop hit
rate, MFE, MAE, return standard deviation, dispersion score, similarity, and
maximum distance.

The guard uses the existing blocked-row analog search path: pre-target rows
only, target row excluded, future rows excluded, `label_` columns excluded from
distance features, deterministic scaling on the historical pool, same-scope
preference, and cross-scope fallback labeling.

## Support Labels

Allowed robust labels:

- `ROBUST_SUPPORT`
- `SUPPORTIVE_BUT_CONCENTRATED`
- `MIXED_SUPPORT`
- `WEAK_SUPPORT`
- `INSUFFICIENT_ANALOGS`
- `CONCENTRATION_ARTIFACT`
- `DECAYS_WITH_DEPTH`

The latest generation produced 12 target rows:

- `ROBUST_SUPPORT`: 0
- `SUPPORTIVE_BUT_CONCENTRATED`: 0
- `MIXED_SUPPORT`: 5
- `WEAK_SUPPORT`: 3
- `INSUFFICIENT_ANALOGS`: 0
- `CONCENTRATION_ARTIFACT`: 4
- `DECAYS_WITH_DEPTH`: 0

## Caution Flags

Persisted caution flags:

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

## Before/After SOXS Example

Before: SOXS `breakdown_sell_10d` showed a top-10 `SUPPORTIVE` analog label with
10/10 positive outcomes and average forward return near 56.07%.

After: the same row shows `CONCENTRATION_ARTIFACT` because all top-10 analogs
were SOXS from 2026, top-25 and top-50 support downgraded to `MIXED`, and
target-before-stop support decayed from 50.00% to 28.00%.

This does not change SOXS row status. It remains research-only and blocked by
the existing model gates.

## Dashboard Changes

Candidate Detail now shows Historical Analog Robustness for blocked/research
rows:

- top-10 support;
- top-25 support;
- top-50 support;
- robust support label;
- caution flags;
- concentration summary;
- depth-decay explanation;
- explanatory-only warning.

Signal Board now includes compact `analog_status`, including
`Concentration Artifact`, `Mixed Analog Support`, `Weak Analog Support`, and
`Insufficient Analogs`.

Reports and Exports includes robustness sheets in the signal-discovery workbook.

## Export Files

Derived report files written under `reports/signal_discovery_v1/`:

- `analog_robustness.csv`
- `analog_robustness_summary.csv`
- `analog_depth_comparison.csv`
- `analog_caution_flags.csv`
- `analog_robustness.json`
- `analog_robustness.xlsx`

Signal-discovery CSV/XLSX exports include:

- `analog_robustness`
- `analog_robustness_summary`
- `analog_depth_comparison`
- `analog_caution_flags`

## Tests

Added and updated tests prove:

- concentrated top-10 same-symbol/year support that decays by top 25/50 becomes
  `CONCENTRATION_ARTIFACT`;
- diversified top-10/top-25/top-50 support becomes `ROBUST_SUPPORT`;
- top-10 support that weakens with depth becomes `DECAYS_WITH_DEPTH`;
- same-symbol, same-year, high-MAE-tail, low-count, and TBS-decay flags are set
  deterministically;
- future rows and target rows remain excluded from analog pools;
- `label_` columns remain excluded from distance features;
- analog outcomes do not change signal status;
- rejected rows remain rejected and shadow rows remain shadow-only;
- Candidate Detail displays robust labels and caution flags;
- Signal Board displays compact analog status;
- CSV and XLSX exports include robustness tables;
- no FMP calls occur;
- model artifacts, SQLite state, scanner state, forward state, final-holdout
  state, and operational state remain unchanged.

## Verification

Commands run:

- `.venv/bin/pytest` -> 366 passed, 11576 warnings.
- `.venv/bin/ruff check .` -> passed.
- `.venv/bin/ruff format --check .` -> passed.
- `.venv/bin/mypy src` -> passed.
- Streamlit AppTest targeted for Signal Board, Candidate Detail, and Reports and
  Exports -> 3 passed.
- Local HTTP smoke: `.venv/bin/streamlit run dashboard/app.py --server.headless true --server.port 8851`
  and `curl -I http://localhost:8851` -> HTTP 200 OK.

No FMP update, discovery run, scanner run, final-holdout update, forward update,
daily cycle, retraining, promotion, threshold change, gate change, OOD
governance change, label change, paper-forward event creation, or operational
write was performed.

## Operational Immutability Proof

Before and after values match unless noted as an equivalent count definition:

- operational HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7` before and
  after;
- operational Git status: clean before and after;
- SQLite SHA256:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` before
  and after;
- enrolled model artifact:
  `artifacts/models/b93b2258c10aea5cef81d291.joblib`;
- enrolled model artifact SHA256:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` before
  and after;
- ordinary scanner artifact count: 17 before and after;
- final-holdout scanner artifact count: 1 before and after;
- SQLite `scanner_snapshots` table count: 18 after; unchanged SQLite hash proves
  the table contents did not change;
- ordinary forward-event count: 285 before and after;
- final-holdout event count: 25 before and after;
- prospective run ID: `3493ee8ac37bf96475c362e1` before and after;
- baseline date: `2026-06-25` before and after;
- final-holdout run status: `COLLECTING` before and after.

Confirmed no operational source files, model artifacts, SQLite state, scanner
state, forward state, final-holdout state, or Git state changed.

## Next Task

expand analog robustness testing for leveraged inverse SELL footprints
