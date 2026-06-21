# Target-Specific Feature Screening

## Purpose

The target-before-stop classifier predicts `label_{direction}_target_before_stop_{horizon}`. It must not inherit the primary positive-return classifier's feature list, because `label_{direction}_positive_return_{horizon}` and target-before-stop are separate prediction tasks.

This correction changes feature selection only. It does not change labels, target/stop multiples, probability thresholds, selection-policy thresholds, quality gates, model families, class weights, resampling, calibration, research dates, raw features, OOD Governance V2, or promotion behavior.

## Screening Order

Target-specific screening is fitted on training rows only:

1. Start from the full eligible numeric feature universe.
2. Reject target columns, every `label_` column, date/timestamp metadata, unsupported object/string columns, and registry-prohibited fields.
3. Fit missingness filtering on training rows.
4. Fit zero-variance and near-zero-variance filtering on training rows.
5. Fit imputation values on training rows.
6. Score every remaining feature against the supplied training target with deterministic mutual information.
7. Normalize invalid mutual-information values: reject NaN scores explicitly and clamp negative scores to zero.
8. Sort candidates by mutual-information score descending, then feature name ascending.
9. Apply deterministic correlation pruning in that score order using training rows only.
10. Stop after the configured maximum selected-feature count.

Calibration and holdout rows are never used for missingness filtering, variance filtering, imputation fitting, mutual-information scoring, correlation pruning, or selected-feature manifests.

## Metadata

Each new target-before-stop model artifact persists:

- screening schema version `target_specific_feature_screen_v1`;
- target label name, direction, horizon, task type, training dates, and training sample count;
- eligible, post-missingness, post-variance, scored, correlation-pruned, and selected counts;
- selected feature names, families, and scores;
- full per-feature audit records with selected/rejected status and reason;
- deterministic random seed and screening configuration;
- screening configuration hash;
- selected-feature manifest hash.

Registry metrics expose the target-before-stop selected-feature count, selected-feature-family counts, screening target, and selected-feature manifest hash.

## Scanner Contract

The scanner must use the target-before-stop head's own frozen selected-feature manifest when computing target-before-stop probability. Missing target-before-stop features reject the candidate with `target_before_stop_required_feature_missing`; another head's features must not be substituted.

Scanner identity includes the target-before-stop screening schema and selected-feature manifest hash. Candidate attribution must distinguish the primary classifier feature diagnostics from target-before-stop feature diagnostics.

## Legacy Artifacts

Existing artifacts remain readable and immutable. Artifacts without target-specific target-before-stop metadata are historical shared-screen artifacts. They may be displayed for audit, but they are not equivalent to new artifacts created with target-specific screening.
