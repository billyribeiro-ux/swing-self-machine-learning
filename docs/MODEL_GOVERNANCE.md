# Model Governance

Models are registered in `state/engine.sqlite3` by `src/swing_rsi/engine/registry.py`.

## States

- `EXPERIMENTAL`
- `CANDIDATE`
- `CHALLENGER`
- `CHAMPION`
- `RETIRED`
- `REJECTED`

Only explicit promotion can create a `CHAMPION`. Discovery never silently replaces a deployed model.

## Stored Metadata

Each registered model stores immutable metadata:

- model ID;
- task, horizon, direction, and family;
- training, calibration, and holdout dates;
- universe snapshot ID;
- feature manifest hash;
- raw-data manifest hashes;
- hyperparameters;
- metrics and calibration metrics;
- canonical quality-gate results;
- artifact path;
- code commit hash when available;
- creation and promotion timestamps;
- retirement reason.

Artifacts are written under `artifacts/models/` and ignored by Git.

## Quality Gates

Each canonical gate stores gate ID, name, category, scope, metric name, threshold, comparator, actual value, status, mandatory flag, evidence source, reason, evaluation time, and configuration hash.

The current vertical slice gates on:

- minimum training samples;
- minimum unseen holdout observations;
- Brier skill versus matching naive control;
- positive expected value after costs;
- holdout Brier score;
- profit factor;
- portfolio maximum drawdown from daily portfolio equity;
- finite lower confidence bound;
- feature-stability cap;
- symbol concentration cap;
- sector concentration cap;
- transaction-cost sensitivity;
- prediction-turnover cap;
- temporal-fold stability;
- exceptional-period concentration;
- comparison-control availability.
- prediction-unit contract validity;
- calibrated prediction out-of-distribution rate and severity;
- selection-rate policy configuration.

Registered metrics also retain feature-stability summaries, bounded holdout permutation-importance summaries, target-before-stop calibration, positive year/regime/sector fractions, symbol/sector concentration, double-cost lower bound, prediction turnover, temporal-fold positive fraction, exceptional-period concentration, model plugin metadata, and naive/RSI-control availability for review. Those diagnostics do not override failed gates.

New model artifacts persist head-specific feature manifests. The target-before-stop head stores its own screening schema version, target label, selected features, selected-feature-family counts, full audit records, screen configuration hash, and selected-feature manifest hash. Legacy artifacts without this metadata remain readable and are labeled as using shared legacy feature screening; they are not equivalent to new target-specific artifacts.

New target-before-stop heads also persist calibration governance schema `tbs_calibration_governance_v1`. Each artifact stores the selected calibrator method, evaluated candidate methods, chronological internal fold definitions, fold-level metrics, candidate mean and standard-error metrics, the one-standard-error boundary, method complexity order, selection reason, final calibration fit dates, calibration audit artifact paths, raw and calibrated score distributions, plateau/step-support diagnostics, calibration manifest hash, and calibrator artifact hash. Identity calibration is stored as explicit metadata and an explicit immutable calibrator object, not as missing calibration metadata.

Registry metrics expose the selected target-before-stop calibration method, selected-method Brier/log loss/ECE, identity/sigmoid/isotonic fold Brier values, largest plateau percentage, minimum step support, selection reason, calibration manifest hash, and calibrator artifact hash. The current holdout is a development holdout for calibration-governance review and must not be presented as final validation evidence.

The configured default candidate-selection policy is persisted with each model artifact and registry row. It requires probability at least `0.55`, expected return at least `0.001` decimal return, target-before-stop probability at least `0.50`, dollar volume at least `5,000,000`, no more than five selected candidates per date, no more than 5,000 selected holdout rows globally, and selected holdout coverage no greater than `20%`. These defaults are methodology controls, not tuned approvals for any current model.

The selection evaluator is canonical for holdout model evaluation and scanner actionability. Missing or non-finite required policy metrics fail safely, and the scanner cannot relax persisted policy thresholds.

The selected row sequence drawdown is retained only as `selected_row_sequence_drawdown`. It is not a portfolio drawdown gate.

## Prediction OOD Governance

New autonomous model artifacts use governance schema `prediction_ood_governance_v2`.

The legacy mandatory gate `prediction_out_of_distribution_absent` is deprecated for new artifacts. Legacy artifacts remain readable for audit, but a legacy artifact that lacks the V2 canonical prediction gates is not promotion eligible. The old gate is excluded from new promotion decisions and must be labeled as legacy when displayed or exported.

V2 keeps training `q01` / `q99` as a reference envelope, not an absolute domain. Every exceedance is persisted with raw prediction value, head, direction, horizon, bound provenance, reference bounds, severity, and governance version.

For each regression head:

```text
L = training target q01
U = training target q99
R = max(U - L, epsilon)

low_overshoot = max(0, L - prediction) / R
high_overshoot = max(0, prediction - U) / R
ood_severity = max(low_overshoot, high_overshoot)
is_ood = ood_severity > 0
```

Each artifact freezes a calibration-derived OOD rate limit using `z = 2.326347874`:

```text
rate_limit =
    min(
        0.05,
        max(
            0.02,
            wilson_upper_99(k_calibration_ood, n_calibration) + 0.005
        )
    )
```

The mandatory rate gates are:

- calibration OOD rate `<= 0.05`;
- holdout OOD rate `<= frozen rate_limit`.

Each artifact freezes a calibration-derived severity limit:

```text
severity_q99_limit =
    min(
        0.50,
        max(
            0.10,
            calibration_q99_severity + 0.05
        )
    )
```

where `calibration_q99_severity` is zero when calibration has no nonzero OOD severities, otherwise it is the q99 of nonzero calibration OOD severities.

The mandatory severity gates are:

- holdout q99 OOD severity `<= frozen severity_q99_limit`;
- maximum holdout OOD severity `<= 1.00`.

The following hard integrity gates are mandatory and zero tolerance:

- `prediction_values_finite`;
- `prediction_unit_contract_valid`;
- `prediction_head_bound_mapping_valid`;
- `prediction_bounds_training_only`;
- `prediction_path_metric_sign_valid`;
- `prediction_probability_contract_valid`.

The path-metric sign contract is explicit: expected MFE predictions must be `>= 0`, and expected MAE predictions must be `<= 0`. The engine does not silently clip invalid predictions.

Live scanner eligibility uses the frozen OOD metadata stored with the model artifact. Rows are rejected when required OOD metadata is missing, a hard integrity contract fails, severity exceeds `1.00`, or severity exceeds the frozen per-head severity limit. Rows with permitted OOD warnings remain auditable and must display the warning rather than treating it as an explanation or causal claim.

## Model Plugin Interface

`src/swing_rsi/engine/models.py` exposes `ModelPlugin` metadata for every discovery family. Each plugin defines:

- a classifier factory;
- a regressor factory;
- whether the family can capture nonlinear interactions.

The current plugin set is `naive_base_rate`, `logistic_regression`, `hist_gradient_boosting`, and `extra_trees`.

The model report retains failed gates instead of weakening them. A model that does not pass every mandatory gate remains a `CANDIDATE` or `REJECTED`.

## Drift Policy

`src/swing_rsi/engine/drift.py` compares train-reference feature distributions, relationship/regime feature distributions, optional prediction distributions, optional realized-performance returns, and optional calibration Brier deterioration with the latest as-of or forward-test evidence.

Drift alerts are evidence for review and possible challenger training. They never mutate an existing model, never silently promote a challenger, and never alter paper-forward events already recorded by a frozen model version.

## Champion Policy

Champion promotion requires:

1. The model is a candidate/challenger in the registry.
2. Persisted canonical mandatory gates exist.
3. The model holdout status is explicitly `FINAL_HOLDOUT`.
4. Every mandatory quality gate passes.
5. No mandatory gate is `NOT_CONFIGURED` or `NOT_APPLICABLE`.
6. Promotion is explicit through `python -m swing_rsi.cli promote-model --model-id ...`.

Models labeled `DEVELOPMENT_HOLDOUT` or missing holdout-status metadata are promotion-ineligible even if their other gates pass. The manual promotion path checks the persisted holdout status before changing registry state.

Existing champion models for the same task, direction, and horizon are retired with a recorded reason.

The live scanner re-checks the same persisted canonical gate results before marking a row actionable. Registry state alone is insufficient: a `CHAMPION` or `CHALLENGER` with failed, missing, not-configured, or not-applicable mandatory gates is rejected for paper action.
