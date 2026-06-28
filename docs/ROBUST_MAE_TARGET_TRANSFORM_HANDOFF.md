# Robust MAE Target Transform V1 Handoff

## Confirmed OOD Source

Diagnosis input generation: `2026-06-26T23:52:15.769542+00:00`

Affected model/head:

- model ID: `85b258623a68620ad108b08c`
- scope: `POOLED`
- direction: `bull`
- family: `hist_gradient_boosting`
- horizon: `10`
- head: `MAE`

The source was limited to POOLED bull HistGradientBoosting MAE prediction-support exceedance:

- learned-model OOD mandatory gate status: `PASS`
- development-holdout MAE OOD warning rows: `6`
- OOD rate: `0.000351493848857645`
- q99 severity: `0.0728609158926969`
- maximum severity: `0.07374787803597609`
- warning date cluster: `2025-10-31`
- selected candidate rows affected: `0`
- sign-contract violations: `0`
- nonfinite predictions: `0`

Root cause classification from the read-only diagnosis:

- estimator extrapolation;
- product-class heterogeneity;
- localized date/regime effect;
- model-family limitation specific to POOLED bull HistGradientBoosting MAE.

## Scoped Transform

Schema: `robust_path_target_transform_v1`

Applied only to:

- product scope: `POOLED`
- direction: `bull`
- family: `hist_gradient_boosting`
- head: `MAE`
- horizon: `10`

Transform:

```text
z = log1p(y)
y_hat = expm1(z_hat)
canonical_mae = -y_hat
```

Where `y` is the nonnegative internal adverse MAE magnitude target.

All other heads/scopes/families/directions persist:

```text
path_target_transform = none
```

The HistGradientBoosting loss remained `poisson` because the transformed `log1p(y)` target is still nonnegative and the inverse mapping is deterministic.

## No-Label-Change Proof

- Raw OHLCV was not rebuilt.
- Labels were not rebuilt or rewritten.
- `build-features` was not run during this task.
- The transform is applied only between MAE magnitude target validation and the scoped estimator fit.
- Scanner and holdout output still use canonical signed MAE, with MAE `<= 0`.
- Tests assert label values remain unchanged and canonical MAE sign output remains valid.

## Train-Only Transform Proof

- Transform metadata persists `fit_split = training`.
- Training target pre-transform distribution and post-transform distribution are persisted in the affected artifact.
- Calibration and development-holdout targets are not used to fit the transform.
- OOD Governance V2 remains in canonical internal MAE magnitude units after inverse transform.

Affected new artifact metadata:

- transformed model ID: `5b3f37a96a7968bca8d2f398`
- transform hash: `c3c93ddb06ea5504`
- estimator class: `HistGradientBoostingRegressor`
- estimator loss: `poisson`
- artifact SHA256: `8e77b20f634192d6b33d26663b6564c31086872cf47854869fc618d5ce818088`

## Commits

- `e58fbfd` - `feat: add robust MAE target transform for pooled bull HGB`
- `7bac98f` - `test: validate scoped path target transformation`
- `3e05d3a` - `docs: document scoped robust MAE transform`

## New Generation

Discovery was run exactly once after clean pre-discovery verification.

- generation ID: `2026-06-27T14:05:10.073173+00:00`
- model rows: `30`
- states: `30 CANDIDATE`, `0 REJECTED`, `0 CHALLENGER`
- promotions: `0`
- final-holdout runs created: `0`
- forward events created: `0`

New transformed affected model:

- model ID: `5b3f37a96a7968bca8d2f398`
- scope: `POOLED`
- direction: `bull`
- family: `hist_gradient_boosting`
- head: `MAE`

Audit exports:

- `reports/robust_mae_transform_v1/model_summary.csv`
- `reports/robust_mae_transform_v1/full_gate_audit.csv`
- `reports/robust_mae_transform_v1/affected_head_comparison.csv`
- `reports/robust_mae_transform_v1/model_matrix_transform.csv`
- `reports/robust_mae_transform_v1/robust_mae_transform_v1_audit.md`

## Affected Head Comparison

| Metric | Before | After |
|---|---:|---:|
| Model ID | `85b258623a68620ad108b08c` | `5b3f37a96a7968bca8d2f398` |
| MAE transform | `legacy/untransformed` | `log1p` |
| MAE OOD count | `6` | `0` |
| MAE OOD rate | `0.000351493848857645` | `0.0` |
| MAE q99 severity | `0.0728609158926969` | `0.0` |
| MAE max severity | `0.07374787803597609` | `0.0` |
| Sign violations | `0` | `0` |
| MAE error | `0.038103027277450345` | `0.031578345094619716` |
| Selected rows | `96` | `96` |
| Mean selected net return | `0.02854326606285741` | `0.02854326606285741` |
| Lower 90% confidence bound | `0.014734419817726744` | `0.014734419817726744` |
| Profit factor | `3.5714138402556634` | `3.5714138402556634` |
| Portfolio total return | `0.35392443235437376` | `0.35392443235437376` |
| Portfolio max drawdown | `-0.08457210212906996` | `-0.08457210212906996` |
| Failed mandatory gates | `final_holdout_required_for_promotion` | `final_holdout_required_for_promotion` |

Result: the diagnosed POOLED bull HistGradientBoosting MAE OOD warnings did not recur. This does not make the model promotion eligible because final-holdout evidence is still unavailable.

## Unaffected Checks

- ORDINARY bull ExtraTrees remains OOD-clean for expected return, MFE, and MAE.
- Unaffected HistGradientBoosting specialists persist `path_target_transform = none`.
- ExtraTrees models persist `path_target_transform = none`.
- Bear models persist `path_target_transform = none`.
- MFE heads persist `path_target_transform = none`.
- Expected-return and Target-Before-Stop heads were not transformed.

## Review-Only Scanner

Command run:

```text
.venv/bin/python -m swing_rsi.cli scan --include-challengers
```

Result:

- scan ID: `7394bc30e865a5c419311d51`
- as-of date: `2026-06-25`
- rows: `50`
- rows by status: `50 REJECTED`
- actionable rows: `0`
- rejection reason: `model_not_promoted` for all rows
- rows by direction: `25 Bullish`, `25 Bearish`
- rows by scope: `POOLED 23`, `ORDINARY 5`, `INVERSE 3`, `LEVERAGED_LONG 9`, `LEVERAGED_INVERSE 10`
- MAE transform rows: `log1p 2`, `none 48`
- scanner identity schema version: `12`
- scanner path-domain metadata hash: `931a0ffb2b71f7f9ed2e875a515732912029547b466bd07ce5ff21e011ba6651`

No forward-update was run.

## Operational Immutability Proof

Operational repository:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

Final read-only verification:

- operational HEAD: `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- operational branch: `feat/autonomous-swing-scanner-v1`
- operational Git status: clean
- frozen run ID: `3493ee8ac37bf96475c362e1`
- run status: `CREATED`
- enrolled model ID: `b93b2258c10aea5cef81d291`
- enrolled generation: `2026-06-25T13:11:51.610283+00:00`
- frozen artifact hash: `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- baseline market date: `2026-06-25`
- final-holdout events for run: `0`
- operational scanner snapshot count: `17`
- operational forward-event count: `285`

No operational discovery, scanner, forward-update, final-holdout-update, final-holdout-init, data update, feature build, source edit, or artifact edit was run.

## Verification

Pre-discovery verification:

- `.venv/bin/pytest`: `306 passed`
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed
- `.venv/bin/mypy src`: passed

Final post-discovery verification:

- `.venv/bin/pytest`: `306 passed`
- `.venv/bin/ruff check .`: passed
- `.venv/bin/ruff format --check .`: passed
- `.venv/bin/mypy src`: passed

## Known Limitations

- Development-holdout evidence remains diagnostic only.
- No model was promoted.
- No prospective final-holdout run was initialized.
- The transform fixed the diagnosed MAE OOD warning source, but it is not final performance proof.
- One scanner OOD warning remains in review output on a return head, unrelated to this MAE transform.

## Next Task

Perform a read-only evidence diagnosis for generation `2026-06-27T14:05:10.073173+00:00` to confirm whether Robust MAE Target Transformation V1 changed only the diagnosed POOLED bull HistGradientBoosting MAE OOD warning source or also materially changed broader model evidence.
