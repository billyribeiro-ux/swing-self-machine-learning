# Prospective Time-Exit Diagnostic Ledger

Schema: `prospective_time_exit_diagnostic_v1`

This ledger records prospective, diagnostic-only evidence for the Sector
Rotation BUY `ORDINARY` time-exit utility hypothesis:

```text
sector_rotation_buy_ordinary_20d_time_exit_utility_v1
```

It is not a live trading system, not final-holdout evidence, and not a
promotion path. Ledger rows are labeled `DIAGNOSTIC_ONLY` or
`RESEARCH_OBSERVATION`.

## Purpose

The ledger answers what happens after future research-only appearances of the
time-exit utility hypothesis:

- whether the row entered at the next eligible session open;
- whether it finished positive at the 20-session time exit;
- whether it recovered after early adverse movement;
- whether target/stop touches differed between baseline and experimental
  policies;
- whether enough prospective evidence exists to justify a later research
  review.

The ledger does not weaken target-before-stop gates, lower probability
thresholds, change OOD governance, change target/stop policy, promote models,
or create live actionable signals.

## No-Backfill Rule

Initialization freezes:

- baseline market date;
- first eligible future as-of date;
- current code commit;
- hypothesis ID;
- product scope;
- target/stop policy IDs;
- label schema;
- feature manifest hash;
- signal-discovery generation ID;
- created timestamp UTC.

Signal-discovery rows with `as_of_date <= baseline_market_date` are rejected as
`DIAGNOSTIC_BACKFILL_BLOCKED`. They are not inserted as prospective
observations.

## Run State

The run table stores one append-only diagnostic run identity:

- `diagnostic_run_id`;
- `schema_version`;
- `created_at_utc`;
- `baseline_market_date`;
- `first_eligible_future_as_of_date`;
- `hypothesis_id`;
- `archetype`;
- `action`;
- `product_scope`;
- `horizon`;
- `target_stop_policy_ids_json`;
- `label_schema`;
- `code_commit`;
- `feature_manifest_hash`;
- `signal_discovery_generation_id`;
- `status`;
- `latest_processed_market_date`;
- `notes`;
- `metadata_json`.

Statuses are:

- `CREATED`;
- `COLLECTING`;
- `EARLY_DIAGNOSTIC_AVAILABLE`;
- `READY_FOR_REVIEW`;
- `CLOSED`;
- `INVALIDATED`.

## Event Types

Events are append-only. Current state is reconstructed from event rows.

- `DIAGNOSTIC_OBSERVATION_CREATED`
- `DIAGNOSTIC_OBSERVATION_REJECTED`
- `DIAGNOSTIC_ENTRY_PENDING`
- `DIAGNOSTIC_ENTRY_FILLED`
- `DIAGNOSTIC_POSITION_MARKED`
- `DIAGNOSTIC_TIME_EXIT_MATURED`
- `DIAGNOSTIC_STOP_TOUCHED`
- `DIAGNOSTIC_TARGET_TOUCHED`
- `DIAGNOSTIC_BACKFILL_BLOCKED`
- `DIAGNOSTIC_DATA_INVALIDATED`

No existing event row is updated in place.

## Observation Selection

Future signal-discovery rows are eligible when they match:

- `hypothesis_id = sector_rotation_buy_ordinary_20d_time_exit_utility_v1`
- action `BUY`
- scope `ORDINARY`
- `NO_SIGNAL` or `RESEARCH_ONLY`
- `as_of_date > baseline_market_date`

Rows do not need `target_before_stop_probability >= 0.50`; this is diagnostic
tracking. OOD-rejected rows are rejected into the ledger with reason
`diagnostic_observation_ood_rejected`.

## Entry And Outcome Rules

- Signal is known after the as-of close.
- Diagnostic entry is the next eligible session open.
- No brokerage order is created.
- Horizon is 20 sessions.
- Time exit is the horizon close.
- Net return subtracts configured round-trip costs.
- MFE, MAE, time to max favorable, and time to max adverse are computed from
  local daily OHLCV.
- Baseline and experimental policy target/stop touches are computed separately.
- Same-bar target/stop ambiguity uses the existing conservative rule.
- A row matures only after the full 20-session horizon exists locally.

## Policy Comparison

The ledger compares:

- baseline policy:
  `sector_rotation_buy_ordinary_20d_default_t2p0_s1p0`;
- experimental policy:
  `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`.

For each matured row, it stores target touched, stop touched,
target-before-stop, stop-before-target, unresolved, profitable despite failed
TBS, and early adverse recovery for each policy.

## Commands

Initialize one diagnostic run:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-init \
  --hypothesis sector_rotation_buy_ordinary_20d_time_exit_utility_v1 \
  --generation signal_discovery_20260704T155444+0000_ed38c60cf1ad
```

Update after a genuinely newer signal-discovery generation and newer local
market sessions exist:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-update
```

Check status:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-status
```

Export:

```bash
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-export \
  --output reports/time_exit_diagnostic_v1
```

## Exports

The export command writes:

- `time_exit_diagnostic_status.csv`
- `time_exit_diagnostic_events.csv`
- `time_exit_diagnostic_observations.csv`
- `time_exit_diagnostic_matured_outcomes.csv`
- `time_exit_diagnostic_policy_comparison.csv`

These files are generated reports and remain outside source control.

## Sample Sufficiency

Research-review progress thresholds are diagnostic only:

- early diagnostic: 30 matured outcomes and 20 distinct signal dates;
- stronger review: 100 matured outcomes, 60 distinct signal dates, and at
  least 4 months.

These thresholds do not permit promotion and do not satisfy final-holdout
requirements.
