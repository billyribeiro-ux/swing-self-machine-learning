# Target-Specific Target-Before-Stop Screen Handoff

## Confirmed Root Cause

The target-before-stop classifier reused the primary positive-return classifier's selected feature set. That shared-screen behavior allowed the positive-return target to determine which columns were available to a different prediction head.

Manual label checks did not find a target-before-stop label defect. The correction is therefore a feature-screening correction, not a label, threshold, calibration, or model-family change.

## Implemented Architecture

The reusable feature-screening service is `swing_rsi.engine.feature_screen.screen_features_for_target`. It accepts a training feature frame, training target, target name, task type, feature-family mapping, maximum selected-feature count, deterministic seed, and screening configuration. It returns selected feature names, per-feature scores and ranks, feature families, missingness, variance, correlation-pruning outcomes, selected/rejected status, rejection reasons, training range, row count, schema version, configuration hash, and selected-feature manifest hash.

Model artifacts now support separate feature manifests for:

- `primary_positive_return`;
- `target_before_stop`;
- `expected_return`;
- `mfe`;
- `mae`.

Only the target-before-stop screening behavior changed in this task. The other heads retain their existing screening methodology and manifest behavior.

## Verification Scope

Before retraining, the required verification is:

- full test suite;
- `ruff check .`;
- `ruff format --check .`;
- `mypy src`;
- focused review for training/calibration/holdout leakage, target mismatch, feature-list reuse, column-order dependence, score-order correlation pruning, scanner feature mismatch, artifact hash omissions, legacy artifact mutation, and target-label feature entry.

After exactly one fresh discovery run, the required audit compares the baseline generation `2026-06-21T17:44:33.265191+00:00` with the new generation by direction, family, and horizon. Better feature coverage is not evidence of a trading edge; the correction succeeds only when all eligible features were screened correctly without leakage.

## Next Review Boundary

If the new generation still shows weak target-before-stop skill after clean screening, that is a model-quality or signal-availability result, not a reason to weaken the fixed `0.50` target-before-stop policy threshold.
