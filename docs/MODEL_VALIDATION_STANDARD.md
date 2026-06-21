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

Before any model is promoted, reserve a final untouched time period that was not used for feature design, parameter ranges, threshold tuning, or model selection.

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
