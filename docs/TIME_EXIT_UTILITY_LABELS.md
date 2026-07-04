# Time-Exit Utility Labels

Schema: `sector_rotation_buy_ordinary_time_exit_utility_v1`

This schema records label-side time-exit utility diagnostics for Sector Rotation
BUY rows in `ORDINARY` scope at the 20-session horizon.

The labels are experimental diagnostics. They do not replace
target-before-stop labels, do not lower probability gates, do not bypass OOD
governance, and do not create live actionable signals.

## Eligible Rows

- archetype: `sector_rotation_buy`
- action: `BUY`
- product scope: `ORDINARY`
- horizon: 20 sessions
- entry timing: next-session open
- exit timing: horizon close

## Policy Association

Rows are keyed by:

- `target_stop_policy_id`
- `target_stop_policy_alias`
- `archetype`
- `action`
- `scope`
- `horizon`
- `Date`
- `symbol`

Supported policies:

- baseline registry ID:
  `sector_rotation_buy_ordinary_20d_default_t2p0_s1p0`
- baseline compatibility alias: `default_t2p0_s1p0_20d`
- experimental candidate:
  `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`

The baseline registry ID remains unchanged. The short baseline ID is stored as
an alias in time-exit artifacts for compatibility with diagnostic language.

## Label Definitions

`time_exit_net_return_20d`:

- `(horizon_close / next_session_open) - 1.0 - round_trip_cost_return`

`time_exit_positive_after_cost_20d`:

- `1` when `time_exit_net_return_20d > 0`
- otherwise `0`

`time_exit_utility_20d`:

```text
time_exit_net_return_20d
/ max(abs(MAE_20d), ATR_pct_at_signal, 0.000001)
```

`profitable_despite_failed_tbs_20d`:

- `1` when target-before-stop is false under the associated policy and
  `time_exit_net_return_20d > 0`
- otherwise `0`

`early_adverse_recovery_20d`:

- `1` when `MAE_20d <= -abs(entry_price - stop_price) / entry_price` and
  `time_exit_net_return_20d > 0`
- otherwise `0`

## Quality Buckets

Buckets are deterministic and are not tuned from development holdout.

- `STRONG_POSITIVE_TIME_EXIT`: net return `>= 0.02`
- `MODEST_POSITIVE_TIME_EXIT`: net return `> 0` and `< 0.02`
- `FLAT_TIME_EXIT`: net return `>= -0.002` and `<= 0`
- `NEGATIVE_TIME_EXIT`: net return `< -0.002` and `> -0.05`
- `SEVERE_NEGATIVE_TIME_EXIT`: net return `<= -0.05`

## Feature Separation

Time-exit labels are label-side outcomes. Columns containing `time_exit`,
`utility`, `profitable_despite_failed_tbs`, or `early_adverse_recovery` are
blocked from feature matrices, even when they do not start with `label_`.

Candidate label columns remain physically separate from existing baseline
labels and are merged only into the in-memory discovery modeling frame. Existing
label parquet files are not overwritten.
