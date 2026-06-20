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

Registered metrics also retain feature-stability summaries and bounded holdout permutation-importance summaries for review. Those diagnostics do not override failed gates.

The model report retains failed gates instead of weakening them. A model that does not pass every mandatory gate remains a `CANDIDATE` or `REJECTED`.

## Drift Policy

`src/swing_rsi/engine/drift.py` compares train-reference feature distributions and optional prediction distributions with the latest as-of snapshot.

Drift alerts are evidence for review and possible challenger training. They never mutate an existing model, never silently promote a challenger, and never alter paper-forward events already recorded by a frozen model version.

## Champion Policy

Champion promotion requires:

1. The model is a candidate/challenger in the registry.
2. Every quality gate passes.
3. Promotion is explicit through `python -m swing_rsi.cli promote-model --model-id ...`.

Existing champion models for the same task, direction, and horizon are retired with a recorded reason.
