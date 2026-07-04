# Target/Stop Policy Registry

Schema: `target_stop_policy_candidate_v1`

The target/stop policy registry records target-before-stop policy definitions
used by Multi-Angle Signal Discovery. Policies are diagnostic/modeling
configuration, not live-trading permission.

## Fields

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

## Current Registered Policies

Default baseline:

- `sector_rotation_buy_ordinary_20d_default_t2p0_s1p0`
- Sector Rotation BUY, `ORDINARY`, 20 sessions
- target `2.0 ATR`, stop `1.0 ATR`
- status `DEFAULT_BASELINE`

Experimental candidate:

- `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`
- Sector Rotation BUY, `ORDINARY`, 20 sessions
- target `2.0 ATR`, stop `1.25 ATR`
- status `EXPERIMENTAL_CANDIDATE`
- selected from calibration-only STOP_TOO_TIGHT evidence in
  `docs/SECTOR_ROTATION_BUY_ORDINARY_TARGET_STOP_DIAGNOSTIC.md`

## Governance

Experimental target/stop policies:

- do not replace the default policy;
- do not lower the TBS probability gate;
- do not weaken OOD governance;
- do not produce live actionable rows;
- do not promote models;
- require future prospective validation before any production eligibility.

Derived candidate-policy outcomes are versioned and separate from baseline
labels. They are added to the discovery modeling frame in memory and persisted
as generated diagnostic artifacts, while existing label parquet and model
artifacts are left unchanged.

Time-exit utility diagnostics use the same policy association but persist an
additional baseline compatibility alias:

- baseline registry ID: `sector_rotation_buy_ordinary_20d_default_t2p0_s1p0`
- baseline time-exit alias: `default_t2p0_s1p0_20d`
- experimental candidate ID:
  `sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25`

The alias is recorded only in time-exit utility artifacts. It does not replace
the registry ID.
