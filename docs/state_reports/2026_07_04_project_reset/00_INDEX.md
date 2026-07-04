# Project State Reset Report Pack Index

Created UTC: `2026-07-04T19:43:13Z`

Development repo:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Operational repo:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

## Files In This Pack

- `00_INDEX.md`: plain-English index and high-level state.
- `01_REPO_AND_GIT_STATUS.md`: repo separation, branches, commits, status, and immutability counters.
- `02_OPERATIONAL_FINAL_HOLDOUT_STATUS.md`: operational frozen run only.
- `03_DEVELOPMENT_FINAL_HOLDOUT_STATUS.md`: invalidated development final-holdout run only.
- `04_TIME_EXIT_DIAGNOSTIC_STATUS.md`: prospective time-exit diagnostic ledger only.
- `05_SIGNAL_DISCOVERY_STATUS.md`: latest development signal-discovery generation only.
- `06_DATA_FEATURE_CACHE_STATUS.md`: local raw data, feature, label, modeling, and regime-cache state.
- `07_DASHBOARD_EXPECTED_STATE.md`: expected development dashboard display without running the dashboard.
- `08_NEXT_ACTIONS.md`: exact commands to run later and actions not to run.

## High-Level Current State

- Operational frozen final-holdout run `3493ee8ac37bf96475c362e1` is `COLLECTING`.
- Operational local data is current through `2026-07-02`.
- Operational final-holdout has `125` events, all `FINAL_HOLDOUT_SIGNAL_REJECTED`.
- Operational pending/open/matured counts are `0 / 0 / 0`.
- Development final-holdout run `d25d6fa11a2e50daa430c15e` is `INVALIDATED` because the current development code commit no longer matches the commit enrolled in that run.
- Development time-exit diagnostic run `0e5facd1e8a164df2b586f64` has `23` accepted observations, `23` pending entries, `23` baseline backfill-blocked rows, and `0` matured outcomes.
- Latest development signal-discovery generation is `signal_discovery_20260704T181757+0000_fa9987cfe9c2`.
- That generation produced `0` BUY candidates, `0` SELL candidates, `516` NO_SIGNAL rows, and `28` OOD-rejected rows.
- Both repositories have all `35` enabled core symbols through `2026-07-02`.

## Broken Or Waiting

Nothing currently indicates a model bug. The system is waiting for the next completed regular market session after `2026-07-02` to advance pending diagnostic entries and continue evidence collection.

