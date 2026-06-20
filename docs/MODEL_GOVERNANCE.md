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
- quality-gate results;
- artifact path;
- code commit hash when available;
- creation and promotion timestamps;
- retirement reason.

Artifacts are written under `artifacts/models/` and ignored by Git.

## Quality Gates

The current vertical slice gates on:

- minimum training samples;
- minimum unseen holdout observations;
- positive expected value after costs;
- holdout Brier score;
- profit factor;
- maximum drawdown.
- finite lower confidence bound;
- feature-stability cap;
- symbol concentration cap;
- sector concentration cap;
- transaction-cost sensitivity;
- prediction-turnover cap;
- temporal-fold stability;
- exceptional-period concentration;
- comparison-control availability.

Registered metrics also retain feature-stability summaries, bounded holdout permutation-importance summaries, target-before-stop calibration, positive year/regime/sector fractions, symbol/sector concentration, double-cost lower bound, prediction turnover, temporal-fold positive fraction, exceptional-period concentration, model plugin metadata, and naive/RSI-control availability for review. Those diagnostics do not override failed gates.

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
2. Every quality gate passes.
3. Promotion is explicit through `python -m swing_rsi.cli promote-model --model-id ...`.

Existing champion models for the same task, direction, and horizon are retired with a recorded reason.
