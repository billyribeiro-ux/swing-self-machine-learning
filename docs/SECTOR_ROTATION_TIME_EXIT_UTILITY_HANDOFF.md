# Sector Rotation Time-Exit Utility Handoff

Date: 2026-07-04

Development repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Development branch: `feat/product-class-specialist-challengers-v1`

Operational repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Operational frozen run: `3493ee8ac37bf96475c362e1`

Operational enrolled model: `b93b2258c10aea5cef81d291`

Operational baseline date: 2026-06-25

## Why This Label Was Needed

The Sector Rotation BUY `ORDINARY` target/stop diagnostic classified the
current 20-session `2.0 ATR` target / `1.0 ATR` stop policy as
`STOP_TOO_TIGHT`. The diagnostic also found that `44.51%` of rows that failed
target-before-stop were still profitable at the 20-session time exit.

That pattern required a label-side diagnostic view of time-exit utility rather
than a weaker target-before-stop gate, a lower probability threshold, or a live
policy change.

## Label Definitions

Schema: `sector_rotation_buy_ordinary_time_exit_utility_v1`

Eligible rows:

- archetype: `sector_rotation_buy`
- action: `BUY`
- product scope: `ORDINARY`
- horizon: 20 sessions
- entry: next-session open
- exit: 20-session horizon close

Derived fields:

- `time_exit_net_return_20d`: horizon-close return from next-session open, net
  of configured round-trip costs.
- `time_exit_positive_after_cost_20d`: `1` when
  `time_exit_net_return_20d > 0`.
- `time_exit_utility_20d`: `time_exit_net_return_20d / max(abs(MAE_20d),
  ATR_pct_at_signal, 0.000001)`.
- `profitable_despite_failed_tbs_20d`: `1` when target-before-stop is false
  under the associated policy and time-exit return is positive after costs.
- `early_adverse_recovery_20d`: `1` when MAE breaches the associated stop
  distance before horizon and final time-exit return is positive.
- `time_exit_quality_bucket_20d`: deterministic bucket for strong positive,
  modest positive, flat, negative, or severe negative time-exit outcomes.

The labels are diagnostic outcomes. Columns containing `time_exit`, `utility`,
`profitable_despite_failed_tbs`, or `early_adverse_recovery` are explicitly
blocked from model feature matrices.

## Policy Association

Time-exit labels are keyed by:

- `target_stop_policy_id`
- `target_stop_policy_alias`
- `archetype`
- `action`
- `scope`
- `horizon`
- `Date`
- `symbol`

Supported policies:

| Policy | Registry ID | Alias | Target | Stop | Horizon | Status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Baseline | `sector_rotation_buy_ordinary_20d_default_t2p0_s1p0` | `default_t2p0_s1p0_20d` | 2.0 ATR | 1.0 ATR | 20 | `DEFAULT_BASELINE` |
| Experimental | `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25` | `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25` | 2.0 ATR | 1.25 ATR | 20 | `EXPERIMENTAL_CANDIDATE` |

Existing baseline labels and prior model artifacts are not overwritten.

## Calibration-Only Summary

Evidence split: `calibration_only`

| Policy | Rows | Time-exit positive | Avg net return | Median net return | Avg utility | Median utility | Profitable despite failed TBS | Early adverse recovery | Avg MFE | Avg MAE | Worst MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 22,471 | 0.6150 | 0.0146 | 0.0163 | 1.1602 | 0.5176 | 0.2982 | 0.3024 | 0.0646 | -0.0556 | -0.6156 |
| Experimental | 22,471 | 0.6150 | 0.0146 | 0.0163 | 1.1602 | 0.5176 | 0.2582 | 0.2490 | 0.0646 | -0.0556 | -0.6156 |

Concentration was unchanged across the two policies because both are evaluated
on the same calibration rows:

- symbol concentration: `0.0435`
- year concentration: `0.2590`
- regime concentration: `0.4166`

Development-holdout rows were reported only as
`DEVELOPMENT_HOLDOUT_DIAGNOSTIC_ONLY` and were not used to choose or tune the
label.

## New Signal-Discovery Generation

Exactly one discovery generation was run after tests passed.

Generation ID: `signal_discovery_20260704T155444+0000_ed38c60cf1ad`

Export directory:
`reports/sector_rotation_buy_ordinary_time_exit_utility_v1`

Generation summary:

- hypotheses evaluated: `17`
- BUY candidates: `0`
- SELL/SHORT candidates: `0`
- selected candidates: `0`
- NO_SIGNAL rows: `543`
- rejected rows: `1`
- latest decision date: `2026-06-26`

The generation persisted the time-exit schema version:
`sector_rotation_buy_ordinary_time_exit_utility_v1`.

## Time-Exit Hypothesis Results

Hypothesis: `sector_rotation_buy_ordinary_20d_time_exit_utility_v1`

Rows:

- time-exit signal rows: `23`
- decision: `NO_SIGNAL` for all `23`
- candidate status: `RESEARCH_ONLY` for all `23`
- time-exit positive probability populated: `23`
- live actionable rows: `0`
- promoted models: `0`

All time-exit rows carried this warning:

```text
Time-exit utility is diagnostic. It does not override gates, create a live signal, or make the hypothesis eligible for promotion without future validation.
```

## TBS Versus Time-Exit Comparison

The time-exit channel found favorable diagnostic evidence, but it did not clear
the existing TBS gate.

Current time-exit hypothesis rows:

- mean TBS probability: `0.4184`
- mean time-exit positive probability: `0.5837`
- mean expected time-exit return: `0.0049`
- mean expected time-exit utility: `0.9810`
- mean profitable-despite-failed-TBS probability: `0.2280`
- mean early-adverse-recovery probability: `0.2316`

Blocking reason:

- `target_before_stop_probability_below_threshold`

Interpretation: time-exit evidence is now visible and persisted, but it remains
diagnostic evidence only. It does not override the target-before-stop gate.

## Top Rows

Top time-exit hypothesis rows by signal score:

| Ticker | Score | TBS p | Time-exit positive p | Expected time-exit return | Expected time-exit utility | Profitable failed-TBS p | Early recovery p | Reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| NVDA | 0.5679 | 0.4184 | 0.5837 | 0.0136 | 0.9348 | 0.2280 | 0.2351 | `target_before_stop_probability_below_threshold` |
| XLK | 0.5635 | 0.4184 | 0.5837 | 0.0111 | 1.0283 | 0.2280 | 0.2351 | `target_before_stop_probability_below_threshold` |
| AMD | 0.5530 | 0.4184 | 0.5837 | 0.0093 | 1.1444 | 0.2280 | 0.2271 | `target_before_stop_probability_below_threshold` |
| XLF | 0.5462 | 0.4184 | 0.5837 | 0.0063 | 0.9988 | 0.2280 | 0.2351 | `target_before_stop_probability_below_threshold` |
| AAPL | 0.5438 | 0.4184 | 0.5837 | 0.0068 | 0.9348 | 0.2280 | 0.2271 | `target_before_stop_probability_below_threshold` |
| AMZN | 0.5430 | 0.4184 | 0.5837 | 0.0065 | 0.9348 | 0.2280 | 0.2271 | `target_before_stop_probability_below_threshold` |
| XLV | 0.5406 | 0.4184 | 0.5837 | 0.0048 | 0.9988 | 0.2280 | 0.2351 | `target_before_stop_probability_below_threshold` |
| XLI | 0.5395 | 0.4184 | 0.5837 | 0.0044 | 1.0059 | 0.2280 | 0.2351 | `target_before_stop_probability_below_threshold` |
| GOOGL | 0.5392 | 0.4184 | 0.5837 | 0.0042 | 1.0283 | 0.2280 | 0.2271 | `target_before_stop_probability_below_threshold` |
| IWM | 0.5382 | 0.4184 | 0.5837 | 0.0040 | 1.0993 | 0.2280 | 0.2271 | `target_before_stop_probability_below_threshold` |

## Dashboard Changes

Signal Board:

- adds compact time-exit columns when available:
  `time_exit_positive_probability` and `expected_time_exit_utility`.

Candidate Detail:

- adds `Time-Exit Utility Diagnostic`;
- shows baseline and experimental policy evidence;
- shows time-exit labels, calibration summary, policy comparison, and signal
  rows;
- displays the diagnostic-only warning.

Reports and Exports:

- includes the time-exit CSV frames;
- includes workbook sheets for time-exit labels, calibration summary, signal
  rows, and policy comparison.

## Exports

The export directory contains:

- `time_exit_utility_labels.csv`
- `time_exit_utility_calibration_summary.csv`
- `time_exit_utility_signal_rows.csv`
- `time_exit_utility_policy_comparison.csv`

The complete signal-discovery export produced `35` files.

## Tests

Verification completed:

- `.venv/bin/pytest`
- `.venv/bin/ruff check .`
- `.venv/bin/ruff format --check .`
- `.venv/bin/mypy src`

Focused Streamlit AppTest coverage was included for:

- Signal Board
- Candidate Detail
- Reports and Exports

Local HTTP smoke test:

- `.venv/bin/streamlit run dashboard/app.py --server.headless true --server.port 8767 --server.address 127.0.0.1`
- `curl -I http://127.0.0.1:8767`
- result: `HTTP/1.1 200 OK`

## Verification

Full test result:

- `374 passed`

Static checks:

- Ruff check: passed
- Ruff format check: passed
- Mypy: passed with no issues in `65` source files

Discovery and export:

- one discovery generation was run;
- one export was run;
- no rerun was performed;
- no model was promoted;
- no final-holdout update was run;
- no forward update was run;
- no daily cycle was run;
- no FMP update was run.

## Operational Immutability Proof

Operational before and after values matched.

| Field | Before | After |
| --- | --- | --- |
| HEAD | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` | `3f3c4f853cc183e6a0a4900dadc428162c400ef7` |
| Git status | clean on `feat/autonomous-swing-scanner-v1` | clean on `feat/autonomous-swing-scanner-v1` |
| SQLite hash | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` | `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8` |
| SQLite size | `250781696` | `250781696` |
| SQLite mtime ns | `1782585787422972957` | `1782585787422972957` |
| Enrolled model hash | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` | `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e` |
| Enrolled model size | `30529057` | `30529057` |
| Enrolled model mtime ns | `1782393801212695748` | `1782393801212695748` |
| Scanner snapshot count | `18` | `18` |
| Ordinary forward-event count | `285` | `285` |
| Final-holdout event count | `25` | `25` |
| Prospective run ID | `3493ee8ac37bf96475c362e1` | `3493ee8ac37bf96475c362e1` |
| Baseline date | `2026-06-25` | `2026-06-25` |
| Latest processed market date | `2026-06-26` | `2026-06-26` |
| Run status | `COLLECTING` | `COLLECTING` |

Confirmed:

- no operational source files changed;
- no operational SQLite state changed;
- no operational model artifacts changed;
- no operational scanner state changed;
- no operational forward state changed;
- no operational final-holdout state changed.

## Next Task

Collect prospective time-exit evidence before changing gates, promotion policy,
or target/stop policy.
