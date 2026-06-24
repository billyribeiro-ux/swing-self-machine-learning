# Tweedie Path-Magnitude OOD Diagnosis

Date: 2026-06-24

## Scope

This is a read-only diagnosis of the linear-family Tweedie MFE and MAE magnitude heads in the latest registered generation.

No code, model artifacts, SQLite state, raw data, labels, thresholds, gates, scanner state, forward-test state, or final-holdout state were intentionally changed.

Latest generation from SQLite:

`2026-06-22T18:07:43.648509+00:00`

Tweedie path-magnitude heads diagnosed:

| Model ID | Direction | Family | Horizon |
| --- | --- | --- | ---: |
| `940ba78f13e1901d5dbed857` | bull | logistic_regression | 10 |
| `1b6b015139ad84f11ce087f6` | bear | logistic_regression | 10 |

The top-level family name remains `logistic_regression`, but the MFE and MAE path-magnitude estimators are `TweedieRegressor(power=1.5, link="log")` under `path_metric_magnitude_domain_v1`.

## Finding

The remaining MFE/MAE OOD failures are not caused by a sign-domain defect. They are caused by severe positive-link extrapolation when extreme leveraged/inverse ETF volatility features appear outside the training distribution.

The implementation fixed the physical domain:

- MFE signed-domain violations: 0
- MAE signed-domain violations: 0

But the log-link can still emit very large nonnegative magnitudes:

```text
prediction = exp(linear_predictor)
```

When standardized volatility/range features are far beyond the training distribution, moderate positive coefficients become very large canonical MFE or MAE magnitudes.

## Split Summary

| Model | Head | Split | OOD rows | OOD rate | Max severity | Prediction range |
| --- | --- | --- | ---: | ---: | ---: | --- |
| bull Tweedie | MFE | calibration | 0 | 0.0000 | 0.0000 | 0.0306 to 0.2379 |
| bull Tweedie | MFE | development holdout | 36 | 0.0021 | 18.7973 | 0.0306 to 6.7249 |
| bull Tweedie | MAE | calibration | 0 | 0.0000 | 0.0000 | -0.2513 to -0.0297 |
| bull Tweedie | MAE | development holdout | 40 | 0.0023 | 27.1694 | -8.1173 to -0.0299 |
| bear Tweedie | MFE | calibration | 0 | 0.0000 | 0.0000 | 0.0299 to 0.3554 |
| bear Tweedie | MFE | development holdout | 38 | 0.0022 | 39.3829 | 0.0295 to 16.3555 |
| bear Tweedie | MAE | calibration | 0 | 0.0000 | 0.0000 | -0.1838 to -0.0297 |
| bear Tweedie | MAE | development holdout | 36 | 0.0021 | 13.1119 | -3.5764 to -0.0295 |

Calibration had zero OOD exceedances for every Tweedie path head. The development holdout contains rare but extreme OOD rows, so the calibration-derived severity limits did not see this product/regime case before holdout.

## Worst Row

The worst row for all four Tweedie path heads is:

| Field | Value |
| --- | --- |
| Date | 2025-04-09 |
| Symbol | SOXS |
| Role | leveraged_inverse_etf |
| Sector | inverse_semiconductors |
| Regime | downtrend_high_vol |

Raw local OHLCV for SOXS on 2025-04-09:

```text
Open=919.4
High=944.0
Low=380.0
Close=414.0
Volume=8,475,130
```

This produces:

```text
range_pct = (944.0 - 380.0) / 414.0 = 1.36232
```

The training maximum for `range_pct` was `0.49004`; the training q99 was `0.119826`. The standardized value for this row was `54.456`.

## Worst-Row Predictions

| Model | Head | Target | Prediction | Training q99 bound | Severity |
| --- | --- | ---: | ---: | ---: | ---: |
| bull Tweedie | MFE | 0.2423 | 6.7249 | 0.3400 | 18.7973 |
| bull Tweedie | MAE | -0.1939 | -8.1173 | -0.2884 lower bound | 27.1694 |
| bear Tweedie | MFE | 0.2405 | 16.3555 | 0.4052 | 39.3829 |
| bear Tweedie | MAE | -0.1950 | -3.5764 | -0.2537 lower bound | 13.1119 |

The signed output is valid in every case. The magnitude is not credible relative to the training path-label distribution.

## Driver Features

Top contributors on SOXS 2025-04-09 are dominated by `volatility_range` features.

### Bull MFE

| Feature | Family | Value | Train q99 | Train max | Z | Coef | Eta contribution |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| range_pct | volatility_range | 1.3623 | 0.1198 | 0.4900 | 54.456 | 0.0386 | 2.104 |
| atr_pct_5 | volatility_range | 0.6327 | 0.1185 | 0.5423 | 23.415 | 0.0328 | 0.769 |
| downside_vol_20 | volatility_range | 0.1841 | 0.0584 | 0.1258 | 14.718 | 0.0267 | 0.393 |
| atr_pct_14 | volatility_range | 0.3325 | 0.1200 | 0.4780 | 11.857 | 0.0296 | 0.350 |

### Bear MFE

| Feature | Family | Value | Train q99 | Train max | Z | Coef | Eta contribution |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| range_pct | volatility_range | 1.3623 | 0.1198 | 0.4900 | 54.456 | 0.0452 | 2.459 |
| atr_pct_5 | volatility_range | 0.6327 | 0.1185 | 0.5423 | 23.415 | 0.0406 | 0.951 |
| downside_vol_20 | volatility_range | 0.1841 | 0.0584 | 0.1258 | 14.718 | 0.0348 | 0.512 |
| realized_vol_10 | volatility_range | 0.2323 | 0.0901 | 0.2854 | 10.968 | 0.0358 | 0.393 |

The log-link makes these eta shifts multiplicative. For bear MFE, the linear predictor reaches `2.79456`, which maps to:

```text
exp(2.79456) = 16.3555
```

## OOD Concentration

Holdout OOD rows are narrowly concentrated:

| Model | Head | Main symbols | Product class | Main month | Main regime |
| --- | --- | --- | --- | --- | --- |
| bull MFE | MFE | SOXL 18, SOXS 16 | leveraged/inverse ETFs | 2025-04: 35 of 36 | downtrend_high_vol: 36 of 36 |
| bull MAE | MAE | SOXS 20, SOXL 17 | leveraged/inverse ETFs | 2025-04: 37 of 40 | downtrend_high_vol: 39 of 40 |
| bear MFE | MFE | SOXS 19, SOXL 16 | leveraged/inverse ETFs | 2025-04: 34 of 38 | downtrend_high_vol: 35 of 38 |
| bear MAE | MAE | SOXL 18, SOXS 16 | leveraged/inverse ETFs | 2025-04: 35 of 36 | downtrend_high_vol: 36 of 36 |

The issue is not distributed across ordinary stocks. It is concentrated in extreme leveraged semiconductor ETF observations and a few other inverse/leveraged ETF rows.

## Ruled Out

### Sign-domain defect

Ruled out for this generation. MFE remains nonnegative and MAE remains nonpositive.

### Label mutation

Ruled out by the previous label regression check: 52,440 label values recomputed from raw OHLCV with zero mismatches.

### OOD bound head mismatch

No evidence found. MFE is evaluated against MFE bounds and MAE against signed MAE bounds in canonical external units.

### Calibration leakage

No evidence found in this diagnosis. The OOD severity failure appears because calibration did not contain the later extreme feature state, not because holdout leaked into calibration.

## Not Fully Ruled Out

### Provider/corporate-action artifact

The raw SOXS 2025-04-09 OHLCV row is extreme but internally valid under the current OHLCV schema. It may represent real leveraged ETF volatility, adjustment semantics, reverse-split handling, or provider-specific historical adjustment behavior. This diagnosis does not prove which one. It only proves that the model and feature pipeline consumed that row as locally available valid OHLCV.

Because SOXS, SOXL, SQQQ, SPXU, and TZA are leveraged/inverse products, provider adjustment semantics remain a live data-quality risk.

## Root Cause Classification

| Cause | Classification | Evidence |
| --- | --- | --- |
| implementation defect | Not proven | Domain mapping, sign checks, and OOD head mapping behaved as designed. |
| label-definition defect | Not found | Prior raw-OHLCV recomputation found zero label mismatches. |
| unit/sign defect | Not found | Predictions are decimal returns and signed outputs obey MFE/MAE contracts. |
| probability-calibration defect | Not applicable | This is path-regression OOD, not TBS probability calibration. |
| feature-screen defect | Not found | Path heads use target-specific screens against magnitude targets. |
| model-family limitation | Primary | `TweedieRegressor(link="log")` is unbounded above and exponentiates extreme linear predictors. |
| product-class instability | Primary | OOD rows are concentrated in leveraged/inverse ETFs, especially SOXL/SOXS. |
| temporal instability | Contributing | Calibration had zero OOD; April 2025 holdout produced rare severe OOD. |
| raw-percentage target heterogeneity | Contributing | Leveraged/inverse ETF raw percentage path targets and volatility features have much wider tails than ordinary stocks. |
| legitimate extreme market behavior | Possible | The local raw rows are extreme but schema-valid; provider adjustment semantics still need audit. |
| legitimate absence of predictive signal | Not the main issue here | The main failure is magnitude extrapolation, not just weak ranking. |

## Conclusion

Domain-preserving magnitude modeling solved invalid signs but did not solve extrapolation. The linear-family Tweedie heads are unsuitable as currently configured for pooled raw-percentage MFE/MAE magnitude prediction across ordinary stocks, ETFs, leveraged ETFs, and inverse ETFs. The log-link is particularly fragile when volatility/range features exceed the training support.

Prediction OOD Governance V2 correctly blocks these models through severity and catastrophic-extrapolation gates. The gate failures should not be weakened.

## One Next Correction

Retire the linear-family Tweedie MFE and MAE magnitude heads from promotion-eligible path-metric modeling, while leaving nonlinear domain-preserving path heads and all existing artifacts readable for audit.
