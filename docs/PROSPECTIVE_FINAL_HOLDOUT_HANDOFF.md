# Prospective Final Holdout Handoff

## Architecture

Prospective final holdout is implemented as `prospective_final_holdout_v1`.

The workflow is intentionally separate from historical development holdout:

1. `final-holdout-init` freezes eligible model identity after a baseline market date.
2. `final-holdout-update` processes only sessions after that baseline date.
3. Shadow events reuse the append-only paper-forward engine with `FINAL_HOLDOUT_` event names.
4. `final-holdout-status` reports collection state.
5. `final-holdout-evaluate --run-id <RUN_ID>` persists final-holdout metrics and canonical gates, but does not promote.

The current historical holdout remains `DEVELOPMENT_HOLDOUT`.

## No-Backfill Proof

Enrollment records `baseline_market_date` from the latest completed local feature session at initialization.

`final-holdout-update` rejects any signal session unless all are true:

- session date is later than `baseline_market_date`;
- session date has not already been processed by the run;
- feature rows carry `local_available_at_utc` later than run creation, or raw-data manifests for all symbols prove retrieval after run creation and coverage through the session;
- enrolled artifact hash, selection-policy hash, target-before-stop calibration hash, and OOD-governance hash still match enrollment.

Missing or stale provenance appends `FINAL_HOLDOUT_DATA_INVALIDATED` with `FINAL_HOLDOUT_BACKFILL_BLOCKED`. It does not create final-holdout signal evidence.

## Run Schema

`final_holdout_runs` persists:

- run ID;
- schema version;
- creation timestamp UTC;
- creation Git commit;
- baseline market date;
- first eligible future signal date;
- universe snapshot ID;
- feature-manifest hash;
- generation ID;
- enrolled model IDs;
- scanner identity version;
- execution-policy hash;
- horizon and direction;
- status;
- invalidation reason;
- latest processed market date;
- metadata.

`final_holdout_models` persists:

- run ID;
- model ID;
- generation ID;
- artifact path and hash;
- model state at enrollment;
- development-gate eligibility;
- research-only flag;
- selection-policy hash;
- target-before-stop calibration-governance hash;
- OOD-governance hash;
- enrollment blockers;
- metadata.

Run statuses are `CREATED`, `COLLECTING`, `READY_FOR_EVALUATION`, `EVALUATED_PASS`, `EVALUATED_FAIL`, `INVALIDATED`, and `CLOSED`.

## Event Lifecycle

Shadow final-holdout events are:

- `FINAL_HOLDOUT_SIGNAL_CREATED`
- `FINAL_HOLDOUT_SIGNAL_REJECTED`
- `FINAL_HOLDOUT_ENTRY_PENDING`
- `FINAL_HOLDOUT_ENTRY_FILLED`
- `FINAL_HOLDOUT_POSITION_MARKED`
- `FINAL_HOLDOUT_STOP_UPDATED`
- `FINAL_HOLDOUT_TARGET_UPDATED`
- `FINAL_HOLDOUT_EXIT_FILLED`
- `FINAL_HOLDOUT_POSITION_EXPIRED`
- `FINAL_HOLDOUT_DATA_INVALIDATED`
- `FINAL_HOLDOUT_EVALUATED`

Events are append-only through `forward_events` and state is reconstructed from the event stream.

## CLI Commands

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation latest
.venv/bin/python -m swing_rsi.cli final-holdout-update
.venv/bin/python -m swing_rsi.cli final-holdout-status
.venv/bin/python -m swing_rsi.cli final-holdout-evaluate --run-id <RUN_ID>
```

`final-holdout-evaluate` does not accept an ad hoc sample threshold. The current final-holdout sample threshold is not governed, so evaluation persists a mandatory `NOT_CONFIGURED` gate until that governance decision is made.

## Dashboard Behavior

Paper Forward Test now includes a Prospective Final Holdout section. It displays:

- run ID;
- status;
- baseline market date;
- first eligible future signal date;
- latest processed market date;
- model count;
- event count;
- signal and rejection counts;
- backfill-blocked events.

It displays the persistent label:

```text
Prospective shadow validation. Not a live trade recommendation.
```

## Promotion Integration

Manual promotion now requires:

- `holdout_status = FINAL_HOLDOUT`;
- final-holdout run ID;
- final-holdout evidence manifest hash;
- final-holdout enrollment row;
- non-research-only enrollment;
- artifact hash unchanged since enrollment;
- selection-policy hash unchanged since enrollment;
- target-before-stop calibration hash unchanged since enrollment;
- OOD-governance hash unchanged since enrollment;
- all mandatory gates passing;
- no mandatory `NOT_CONFIGURED` or `NOT_APPLICABLE`.

Development-holdout evidence cannot satisfy promotion.

## Review Findings

Focused review covered:

- historical backfill;
- event mutation;
- retraining leakage;
- calibration leakage;
- artifact drift;
- idempotency;
- promotion bypass;
- development/final metric mixing.

Findings:

- No training, calibration, feature screening, retraining, or scanner threshold changes were introduced.
- No source path uses final-holdout outcomes for model fitting.
- No scanner, forward-update, daily-cycle, model promotion, or FMP update was run.
- A review issue was fixed: CLI evaluation no longer accepts an ad hoc matured-outcome threshold.
- A review issue was fixed: final-holdout session provenance can be proven from raw-data manifests when `local_available_at_utc` is absent; missing manifests still block.

## Tests

Final verification:

```text
.venv/bin/pytest
213 passed, 166 warnings

.venv/bin/ruff check .
All checks passed

.venv/bin/ruff format --check .
98 files already formatted

.venv/bin/mypy src
Success: no issues found in 57 source files
```

The warnings are existing pandas fragmentation/joblib/core-count/constant-input warnings in existing tests.

## Commit Hashes

- `3a10a09d3cd06b716a128c4531a0efb9b5360240` - `feat: add prospective final holdout registry`
- `cb521a8113ae44b3da2d87fb48a0238faa2bac58` - `feat: add shadow final holdout event lifecycle`
- `48c2a2283fdb8aa6d5ae8fa6f7200f8ac7067736` - `feat: add final holdout evaluation and promotion integration`
- `63324c54c3d4a7ad78b58414ff726deb7dafd9a4` - `test: validate prospective final holdout integrity`
- Docs/final-review commit hash is printed in the Codex handoff because a commit cannot include its own final hash.

## Real Initialization Result

Command run exactly once:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation latest
```

Result:

```text
No models qualified for prospective final-holdout enrollment.
No prospective final-holdout runs exist.
```

No fake enrollment was created. Backfilled predictions: `0`. Matured outcomes: `0`.

Exact blockers by model:

- `14ca47d4c2760a6e3d8867c8`: positive expected value failed; transaction-cost sensitivity failed; temporal-fold stability below 50%; MFE and MAE OOD severity failed; final-holdout gate missing.
- `1f3a62ae23d6897c1eaeab5a`: naive control excluded; zero-selection concentration gates unavailable; not-naive gate failed; MFE and MAE OOD severity/catastrophic extrapolation failed; final-holdout gate missing.
- `34665ce3f2b9f593f8fcc6b4`: positive expected value failed; profit factor unavailable; portfolio drawdown missing; symbol/sector concentration unavailable; transaction-cost sensitivity failed; temporal-fold evidence unavailable; exceptional-period concentration unavailable; MFE and MAE OOD severity/catastrophic extrapolation failed; final-holdout gate missing.
- `779b253e4955f9fa93f4b9fb`: naive control excluded; zero-selection concentration gates unavailable; not-naive gate failed; expected-return OOD severity failed; MFE sign contract failed; MFE and MAE OOD severity/catastrophic extrapolation failed; final-holdout gate missing.
- `8b7b96af23310d90768cbd53`: exceptional-period concentration exceeded 60%; expected-return OOD severity failed; MFE OOD severity/catastrophic extrapolation failed; MAE OOD severity failed; final-holdout gate missing.
- `9667744237fcebdd589a9c67`: positive expected value failed; profit factor unavailable; portfolio drawdown missing; symbol/sector concentration unavailable; transaction-cost sensitivity failed; temporal-fold evidence unavailable; exceptional-period concentration unavailable; expected-return and MFE OOD severity failed; final-holdout gate missing.
- `c152bfa00503d94f86c74869`: positive expected value failed; profit factor unavailable; portfolio drawdown missing; symbol/sector concentration unavailable; transaction-cost sensitivity failed; temporal-fold evidence unavailable; exceptional-period concentration unavailable; MAE OOD severity failed; final-holdout gate missing.
- `e5c7ce8b917c30030801fb58`: positive expected value failed; profit factor unavailable; portfolio drawdown missing; symbol/sector concentration unavailable; transaction-cost sensitivity failed; temporal-fold evidence unavailable; exceptional-period concentration unavailable; expected-return OOD severity failed; MFE sign contract failed; MFE and MAE OOD severity/catastrophic extrapolation failed; final-holdout gate missing.

## Exact Next Operational Command

After a future model generation has all mandatory development gates passing except `final_holdout_required_for_promotion`, run:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation latest
```

## One Smallest Next Engineering Task

Define and persist the governed minimum prospective final-holdout matured-outcome threshold so `final_holdout_sample_threshold_configured` no longer remains `NOT_CONFIGURED`.
