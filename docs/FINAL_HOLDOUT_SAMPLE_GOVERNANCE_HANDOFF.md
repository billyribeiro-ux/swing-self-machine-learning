# Prospective Final-Holdout Sample Governance Handoff

Date: 2026-06-21

## Policy

Schema: `prospective_final_holdout_sample_v1`

Frozen config path:

```text
configs/governance/prospective_final_holdout_v1.yaml
```

Per enrolled model ID, direction, and horizon, `READY_FOR_EVALUATION` requires:

- matured outcomes: minimum 100
- distinct signal dates represented by matured outcomes: minimum 60
- prospective observation span: minimum 126 completed market sessions
- calendar coverage: minimum 4 distinct calendar months
- target-before-stop positives: minimum 20
- target-before-stop negatives: minimum 20
- prospective ingestion provenance: valid for every included prediction
- backfill: zero backfilled predictions
- data integrity: zero unresolved data-integrity events included
- frozen integrity: artifact, feature manifest, selection policy, calibrator, OOD governance, execution policy, and code hashes match enrollment

`EARLY_DIAGNOSTIC_AVAILABLE` requires 30 matured outcomes and 20 distinct signal dates. It is display-only and cannot set `FINAL_HOLDOUT`, satisfy promotion, select thresholds, or mutate model artifacts.

## Rationale

The sample requirement is now precommitted before any prospective outcomes exist. The policy is normalized and hashed at run creation, then stored on `final_holdout_runs`; later global policy changes require a new run and do not rewrite existing run evidence.

## Status Transitions

Supported statuses:

- `CREATED`
- `COLLECTING`
- `EARLY_DIAGNOSTIC_AVAILABLE`
- `READY_FOR_EVALUATION`
- `EVALUATED_PASS`
- `EVALUATED_FAIL`
- `INVALIDATED`
- `CLOSED`

`READY_FOR_EVALUATION` requires every mandatory sample, provenance, and integrity gate to pass. `FINAL_HOLDOUT` is assigned only by completed non-diagnostic evaluation and remains evidence status, not model-quality pass.

## Gate Definitions

Canonical sample gates:

- `final_holdout_policy_configured`
- `final_holdout_matured_outcomes_min_100`
- `final_holdout_distinct_signal_dates_min_60`
- `final_holdout_observation_sessions_min_126`
- `final_holdout_calendar_months_min_4`
- `final_holdout_positive_class_min_20`
- `final_holdout_negative_class_min_20`
- `final_holdout_provenance_valid`
- `final_holdout_backfill_absent`
- `final_holdout_data_integrity_valid`
- `final_holdout_frozen_artifacts_unchanged`
- `final_holdout_sample_sufficient`

Every gate stores threshold, actual value, comparator, status, mandatory flag, reason, policy version, and policy hash.

## CLI Behavior

`python -m swing_rsi.cli final-holdout-status` now displays per-model:

- matured outcomes / 100
- distinct signal dates / 60
- completed observation sessions / 126
- calendar months / 4
- positive outcomes / 20
- negative outcomes / 20
- pending entries
- open positions
- provenance failures
- blocked backfills
- invalidated outcomes
- artifact-integrity status
- estimated remaining requirement
- promotion eligibility

`python -m swing_rsi.cli final-holdout-evaluate --run-id <RUN_ID>` refuses evaluation until sample sufficiency is complete.

`--diagnostic-only` allows non-promotable early diagnostics after the early threshold is reached.

## Dashboard Behavior

The Paper Forward Test page keeps prospective final-holdout metrics separate from historical/development diagnostics and displays:

```text
Prospective shadow validation. Not a live trade recommendation.
```

The final-holdout status table shows actual counts next to required-count columns and separates collecting, early diagnostic, ready, evaluated, and promotion eligibility states.

## Implementation Review

Review result: clean after fixes.

Reviewed risks:

- post-outcome policy changes: frozen run policy hash and JSON prevent active-run mutation
- sample counting errors: matured outcomes require pending, fill, and exit event linkage
- duplicate matured outcomes: append-only unique event keys preserve idempotency
- pending versus matured confusion: pending and rejected signals do not count as matured
- backfill bypass: blocked-backfill events fail sufficiency
- provenance bypass: missing prospective provenance fails sufficiency
- diagnostic promotion bypass: diagnostic-only evaluation cannot set `FINAL_HOLDOUT`
- active-run policy mutation: later global policy edits do not alter stored run policy
- `FINAL_HOLDOUT` mistaken for PASS: separate failed model-quality gates still block promotion

One production bug was found and fixed during tests: matured exits were initially matching fill events by fill event ID rather than by the pending event ID referenced in the fill payload. The corrected reconstruction uses `source_pending_event_id`.

## Commits

- `07df036` `feat: define prospective final holdout sample governance`
- `7f312ee` `test: validate prospective final holdout sufficiency`
- docs commit: this commit, `docs: document final holdout sample requirements`

## Tests

Verification run:

- `.venv/bin/pytest`: 230 passed, 166 warnings
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed
- `.venv/bin/mypy src`: passed

Focused final-holdout regression run:

- `tests/test_prospective_final_holdout.py` plus registry promotion fixture: 37 passed

Automated tests make no FMP calls.

## Real Initialization Result

Command run once:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation latest
```

Result:

- no model qualified
- no prospective final-holdout run was created
- `final_holdout_runs` count remained 0
- no research-only run was initialized

## Current Learned-Model Blockers

Latest generation: `2026-06-21T20:51:00.841677+00:00`

Learned models:

- `14ca47d4c2760a6e3d8867c8` bull `hist_gradient_boosting`: positive EV, transaction-cost sensitivity, temporal-fold stability, MFE OOD q99 severity, MAE OOD q99 severity, missing final-holdout gate
- `34665ce3f2b9f593f8fcc6b4` bull `logistic_regression`: positive EV, profit factor unavailable, portfolio drawdown unavailable/failing, symbol/sector concentration unavailable, transaction-cost sensitivity, temporal-fold evidence unavailable, exceptional-period concentration unavailable, MFE OOD q99/catastrophic severity, MAE OOD q99/catastrophic severity, missing final-holdout gate
- `8b7b96af23310d90768cbd53` bear `hist_gradient_boosting`: exceptional-period concentration, expected-return OOD q99 severity, MFE OOD q99/catastrophic severity, MAE OOD q99 severity, missing final-holdout gate
- `9667744237fcebdd589a9c67` bear `extra_trees`: positive EV, profit factor unavailable, portfolio drawdown unavailable/failing, symbol/sector concentration unavailable, transaction-cost sensitivity, temporal-fold evidence unavailable, exceptional-period concentration unavailable, expected-return OOD q99 severity, MFE OOD q99 severity, missing final-holdout gate
- `c152bfa00503d94f86c74869` bull `extra_trees`: positive EV, profit factor unavailable, portfolio drawdown unavailable/failing, symbol/sector concentration unavailable, transaction-cost sensitivity, temporal-fold evidence unavailable, exceptional-period concentration unavailable, MAE OOD q99 severity, missing final-holdout gate
- `e5c7ce8b917c30030801fb58` bear `logistic_regression`: positive EV, profit factor unavailable, portfolio drawdown unavailable/failing, symbol/sector concentration unavailable, transaction-cost sensitivity, temporal-fold evidence unavailable, exceptional-period concentration unavailable, expected-return OOD q99 severity, MFE sign contract, MFE OOD q99/catastrophic severity, MAE OOD q99/catastrophic severity, missing final-holdout gate

Naive controls remain excluded from enrollment by design.

## Next Model-Quality Task

Perform a read-only MFE/MAE OOD severity and sign-contract diagnosis for the latest learned models.
