# Model Validation Standard

## Chronological separation

Random shuffling is prohibited for time-series validation. Training observations must precede test observations.

## Walk-forward selection

For each fold:

1. Search and select parameters using the training window only.
2. Leave the configured gap between training and testing.
3. Freeze the selected rule.
4. Evaluate only on the next unseen test window.
5. Preserve every fold, including failures.

Historical walk-forward validation is legacy research evaluation. It is not the same as paper forward testing of a frozen deployed scanner model.

## Final holdout

Before any model is promoted, it must complete prospective final-holdout validation. The existing 2016-2026 chronological holdout has been repeatedly inspected and is labeled `DEVELOPMENT_HOLDOUT`; it cannot be reclassified as final evidence and cannot satisfy promotion.

A valid final holdout now means:

1. A model version is frozen and enrolled into a prospective final-holdout run.
2. The artifact hash, feature manifest, selection policy, target-before-stop calibrator, OOD metadata, universe, scanner identity, execution policy, and code commit are recorded.
3. A baseline market date is recorded at enrollment.
4. No signal with `as_of_date <= baseline_market_date` may enter the run.
5. Later sessions require local ingestion provenance proving they became available after run creation.
6. Signals are written before outcomes exist and are advanced through the append-only paper-forward event lifecycle.
7. Final-holdout events never enter training, calibration, feature screening, threshold choice, policy selection, or retraining.
8. Evaluation uses only events belonging to the prospective run and persists canonical final-holdout gates.

Prospective final-holdout sample sufficiency is governed by `prospective_final_holdout_sample_v1` and frozen into each run at creation. Per enrolled model, direction, and horizon, evaluation requires at least 100 matured outcomes, 60 distinct signal dates, 126 completed market sessions from the first eligible future signal date, 4 calendar months of matured outcomes, at least 20 positive and 20 negative target-before-stop outcomes, valid provenance for every included prediction, zero backfilled predictions, zero unresolved data-integrity events, and unchanged artifact, feature-manifest, selection-policy, calibrator, OOD-governance, execution-policy, and code hashes.

`EARLY_DIAGNOSTIC_AVAILABLE` is non-promotable and requires at least 30 matured outcomes and 20 distinct signal dates. Diagnostic-only evaluation before full sample sufficiency cannot set `holdout_status = FINAL_HOLDOUT`, cannot satisfy promotion gates, and cannot select thresholds or mutate model artifacts.

`FINAL_HOLDOUT` means evidence came from a valid prospective period and evaluation completed. It does not mean the model passed its performance gates.

## Evaluation layers

Autonomous scanner validation separates:

- prediction-level diagnostics over every eligible holdout row;
- selected-candidate diagnostics over rows passing the frozen selection policy;
- portfolio-level diagnostics from chronological portfolio simulation only.

The default frozen selection policy is explicit and persisted: probability threshold `0.55`, expected-return threshold `0.001`, target-before-stop threshold `0.50`, minimum dollar volume `5,000,000`, per-date limit `5`, global holdout top-N limit `5,000`, and selected-rate ceiling `20%`. A model that breaches the selected-rate ceiling fails the mandatory selection-coverage gate.

Candidate ordering is canonical and shared by holdout selection, scanner caps, and portfolio replay: composite utility descending, symbol ascending, direction ascending, model ID ascending, then stable candidate identity hash ascending. Probability and expected return are not tie-breakers unless the persisted tie-breaking policy is explicitly changed.

Maximum drawdown used for promotion gates must come from daily portfolio equity. Sequential compounding of selected cross-sectional rows is allowed only as the diagnostic `selected_row_sequence_drawdown`.

## Research date eligibility

Raw data may begin before `research_start` for trailing-feature warm-up. Model-eligible training, calibration, holdout, label, quality, and historical portfolio rows must begin on or after the configured research start and must not use labels extending beyond the configured research end.

The current autonomous default research start is `2016-06-20`.

## Predictive skill

Every classifier is compared against the matching naive control on the exact same holdout rows. Store model Brier, naive Brier, absolute Brier improvement, relative Brier improvement, and Brier skill score. A model with worse holdout Brier than the matching naive control fails the mandatory predictive-skill gate.

## Target-specific feature screening

Each prediction head that owns a distinct target must use a train-only feature screen fitted to that target. The target-before-stop classifier uses `label_{direction}_target_before_stop_{horizon}` for missingness filtering, variance filtering, mutual-information scoring, and correlation pruning. Path-metric regressors use internal ATR-normalized targets under `atr_normalized_path_targets_v1`: expected return uses signed directional return divided by close-known signal-date `atr_pct_14`; MFE uses favorable magnitude divided by `atr_pct_14`; MAE uses adverse magnitude divided by `atr_pct_14`. No head may reuse the positive-return classifier's selected feature list unless the independent screen naturally selects the same columns.

The screen starts from the full eligible numeric feature universe, excludes `label_` columns and metadata columns, scores every surviving feature on training rows only, sorts by mutual-information score descending and feature name ascending, then applies correlation pruning in that score order before enforcing the configured feature cap. Classification heads use `mutual_info_classif`; regression heads use `mutual_info_regression`. Calibration and holdout rows must not affect screening, imputation values, score ordering, or selected-feature manifests.

## Path magnitude domain modeling

Historical path labels are not rewritten. Their external contract remains expected return as signed decimal directional return, MFE `>= 0`, and MAE `<= 0` in decimal-return units. Model training derives internal ATR-unit targets from close-known signal-date `atr_pct_14`:

- `expected_return_atr_target = existing expected return / atr_pct_14`;
- `mfe_magnitude_atr_target = existing MFE label / atr_pct_14`;
- `mae_magnitude_atr_target = (-1 * existing MAE label) / atr_pct_14`.

Under `path_metric_magnitude_domain_v1`, linear-family path-magnitude heads use `TweedieRegressor(power=1.5, link="log")`, HistGradientBoosting path-magnitude heads use `HistGradientBoostingRegressor(loss="poisson")`, ExtraTrees path-magnitude heads train directly on nonnegative magnitudes, and naive controls use nonnegative training-magnitude summaries. Expected-return modeling remains signed.

Predictions are mapped back to canonical decimal-return units before scanner output, selection policy, attribution, portfolio replay, and paper-forward testing. Invalid magnitude output or invalid signed output is a hard integrity failure; no post-prediction clipping may be used to repair it.

## Target-before-stop calibration governance

New target-before-stop heads use calibration governance schema `tbs_calibration_governance_v1`. Each model family, direction, horizon, and prediction head selects its own calibrator independently; calibrators are never shared across bull/bear, model families, horizons, or heads.

Only the chronological calibration slice may select the target-before-stop calibration method. The current calibration period is split into three deterministic forward-chaining internal folds when possible. For each internal fold, calibrator fit rows strictly precede evaluation rows; evaluation labels, holdout labels, and future calibration rows cannot enter calibrator fitting for an earlier fold.

The only supported candidates are `identity`, `sigmoid`, and `isotonic`. Candidate selection uses mean chronological-fold Brier score with a precommitted one-standard-error rule: find the lowest mean Brier, add that candidate's Brier standard error, then choose the simplest method within that boundary using `identity < sigmoid < isotonic`. At least two evaluable chronological folds are required to select a learned calibrator; otherwise identity is selected with reason `insufficient_calibration_folds_for_learned_calibrator`.

After selection, the chosen calibrator is refit on the complete calibration slice only. Development holdout metrics are persisted and displayed only as `DEVELOPMENT HOLDOUT DIAGNOSTIC`; they must not select calibrators, optimize thresholds, promote models, or support final out-of-sample claims.

## Prediction OOD governance V2

Autonomous model artifacts created under `prediction_ood_governance_v2` no longer require zero predictions outside the training `q01` / `q99` reference envelope. The `q01` / `q99` range remains the out-of-distribution reference envelope, but it is not an absolute mathematical domain. Requiring zero exceedances across thousands of holdout predictions makes one ordinary tail estimate fail an otherwise auditable model, so the old `prediction_out_of_distribution_absent` gate is deprecated for new artifacts.

Every exceedance remains visible and auditable. Raw predictions are never silently clipped, replaced, or hidden.

For each regression head, direction, horizon, and model artifact:

- heads are evaluated independently: expected return, expected MFE, and expected MAE;
- external scanner outputs are decimal returns, so `0.05` means `5%`;
- active path heads are compared in normalized model space against ATR-unit training-target bounds;
- expected return is compared only with expected-return ATR-target bounds;
- expected MFE is compared only with MFE favorable-magnitude ATR-target bounds;
- expected MAE is compared only with MAE adverse-magnitude ATR-target bounds;
- canonical decimal-return outputs are separately validated for finite values and MFE/MAE sign contracts;
- bullish and bearish heads use the matching direction and horizon target distributions;
- bounds are fitted from training targets only.

For each head:

```text
L = training target q01
U = training target q99
R = max(U - L, epsilon)

low_overshoot = max(0, L - prediction) / R
high_overshoot = max(0, prediction - U) / R
ood_severity = max(low_overshoot, high_overshoot)
is_ood = ood_severity > 0
```

The fixed Wilson constant for calibration-derived rate limits is:

```text
z = 2.326347874
```

For each head, calibration predictions define the frozen OOD rate limit:

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

The calibration OOD rate must be no greater than `0.05`. The holdout OOD rate must be no greater than the frozen `rate_limit`. The formula is fixed before inspecting holdout results and the limit is stored with the immutable artifact.

For each head, calibration predictions also define the frozen severity limit:

```text
calibration_q99_severity = 0
    when there are no nonzero calibration OOD severities

calibration_q99_severity =
    q99 of nonzero calibration OOD severities otherwise

severity_q99_limit =
    min(
        0.50,
        max(
            0.10,
            calibration_q99_severity + 0.05
        )
    )
```

The holdout q99 OOD severity must be no greater than the frozen `severity_q99_limit`. The maximum holdout OOD severity must be no greater than `1.00`. A severity greater than `1.00` means the prediction exceeded the `q01` / `q99` boundary by more than one full robust training-target span and is a catastrophic-extrapolation failure.

The following integrity defects remain zero-tolerance mandatory failures:

- nonfinite predictions;
- probability predictions outside `[0, 1]`;
- unit-contract failures, including percent values fed into model evaluation;
- double inverse transformations;
- wrong head-to-bound mapping;
- wrong direction or horizon target bounds;
- OOD bounds derived from calibration, holdout, scanner, or future data;
- MFE predictions below zero;
- MAE predictions above zero.

Scanner rows use the frozen artifact metadata. A live prediction outside the `q01` / `q99` reference envelope may remain eligible only when it passes every integrity gate and its severity is within the frozen per-head severity limit. The scanner must retain the OOD warning, affected head, raw value, reference bound, severity, and frozen limit.

## Stability requirements

Prefer broad stable feature/model behavior over one isolated optimum. RSI parameter stability remains a baseline diagnostic; autonomous models must also report feature stability, calibration, symbol concentration, sector concentration, year/regime stability, and cost sensitivity.

## Minimum sample

A configurable minimum trade count is mandatory. The minimum is a filter, not proof of adequacy. Confidence intervals and effective independence must also be considered.

## Regime robustness

Evaluate across:

- Bull, bear, and sideways markets
- High and low volatility
- Different sectors and liquidity profiles
- Multiple calendar periods

## Edge decay

Track rolling expectancy, hit rate, drawdown, and calibration. A model can be downgraded, paused, or retired when forward evidence deteriorates.

## Promotion states

```text
EXPERIMENTAL
CANDIDATE
CHALLENGER
CHAMPION
RETIRED
REJECTED
```

Only explicit promotion can create a champion. Discovery never silently replaces a deployed model.

Legacy RSI reports may still use older research labels, but the autonomous registry uses the states above.

Promotion eligibility is computed only from persisted canonical gate results. Missing mandatory gates, failed mandatory gates, mandatory `NOT_CONFIGURED`, and mandatory `NOT_APPLICABLE` block promotion.

Promotion also requires an explicit `FINAL_HOLDOUT` status. A repeatedly inspected development holdout must be labeled `DEVELOPMENT_HOLDOUT` and is never sufficient for champion promotion, threshold optimization, or final performance claims. Missing holdout-status metadata is treated as not final.
