# Product-Class Specialist Challenger V1

## Status

Product-class specialist challenger. Development evidence only.

This architecture creates development challengers only. It does not modify the frozen operational model, change labels, change thresholds, weaken OOD Governance V2, promote a model, initialize prospective final holdout, run ordinary forward update, or create live/actionable scanner signals.

## Motivation

Read-only nonlinear diagnostics found that ordinary stocks and ordinary ETFs have materially different path-return, MFE, MAE, calibration, OOD, and concentration behavior from leveraged and inverse ETFs. Leveraged and inverse products, especially SOXL and SOXS during extreme volatility periods, contributed materially to target heterogeneity and extrapolation risk.

The frozen operational pooled bull HistGradientBoosting model remains untouched in prospective validation. V1 creates independent challengers to test whether product-class specialization reduces heterogeneity without changing methodology controls.

## Scope Schema

Schema version: `product_class_specialist_v1`

Scopes:

- `POOLED`: all enabled configured symbols.
- `ORDINARY`: ordinary stocks and non-leveraged, non-inverse ETFs.
- `LEVERAGED_INVERSE`: leveraged and inverse ETFs only.

Canonical role mapping:

- `stock` -> `ORDINARY`
- `broad_market_etf` -> `ORDINARY`
- `sector_etf` -> `ORDINARY`
- `ordinary_etf` -> `ORDINARY`
- `inverse_etf` -> `LEVERAGED_INVERSE`
- `leveraged_inverse_etf` -> `LEVERAGED_INVERSE`
- `leveraged_long_etf` -> `LEVERAGED_INVERSE`

Universe role metadata is the only source of product-class membership. Ticker-name heuristics are not allowed. Unknown or ambiguous roles raise validation errors before training.

## Context And Rows

Feature construction remains full-universe. Market-relative, sector-relative, inverse/leveraged, breadth, relationship-graph, regime, volatility, trend, momentum, and RSI context features may still use the complete enabled universe.

Product specialization applies only after feature and label construction:

- `ORDINARY` models train/calibrate/evaluate only on ordinary target rows.
- `LEVERAGED_INVERSE` models train/calibrate/evaluate only on leveraged/inverse target rows.
- `POOLED` controls train/calibrate/evaluate on all eligible target rows.

The constant scope label is not added as a predictive feature.

## Model Families

Specialist learned families:

- HistGradientBoosting
- ExtraTrees

Trained heads per learned model:

- primary positive-return classifier
- Target-Before-Stop classifier
- expected-return regressor
- MFE regressor
- MAE regressor

Logistic-family specialists are excluded from this milestone because logistic MFE and MAE path heads are retired. Naive controls are created per direction and scope when data sufficiency allows.

## Isolation Contracts

Each scope/family/direction/horizon owns independent:

- chronological train/calibration/development-holdout splits
- target-specific feature screens
- selected-feature manifests
- preprocessing
- estimators
- Target-Before-Stop calibration governance
- OOD Governance V2 reference distributions and limits
- selection-policy manifest
- path-head capability metadata
- model artifact identity

Changing the role mapping, scope configuration, or universe-scope snapshot changes the persisted hashes and model identity.

## Scanner Routing

Review scanner routing is scope-aware:

- `POOLED` models may score every eligible symbol.
- `ORDINARY` specialists may score only ordinary symbols.
- `LEVERAGED_INVERSE` specialists may score only leveraged/inverse symbols.

Scope mismatches are explicit review rejections with reason:

```text
product_class_scope_mismatch
```

Scanner identity includes product-class schema, model scope, role mapping hash, universe-scope hash, and scope metadata. Development candidates remain non-actionable unless the existing registry state and persisted quality gates independently allow actionability. This milestone does not promote any model.

## Evidence Label

All comparisons from this architecture are:

```text
DEVELOPMENT_HOLDOUT_DIAGNOSTIC
```

They are not final-holdout evidence and cannot satisfy promotion.
