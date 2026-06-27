# Challenger Enrollment Package: 5b3f37a96a7968bca8d2f398

Generated: 2026-06-27

Purpose: prepare and record the development prospective shadow final-holdout challenger enrollment. This document does not promote the model and did not create scanner, forward, or final-holdout event evidence.

## Candidate

| Field | Value |
| --- | --- |
| Full model ID | `5b3f37a96a7968bca8d2f398` |
| Generation ID | `2026-06-27T14:05:10.073173+00:00` |
| Development branch | `feat/product-class-specialist-challengers-v1` |
| Development HEAD at package preparation | `8e2b40effab1332f474ca47d720fcb8c21ca4912` |
| Registry state | `CANDIDATE` |
| Task | `swing_direction_probability` |
| Scope | `POOLED` |
| Direction | `bull` |
| Family | `hist_gradient_boosting` |
| Horizon | 10 sessions |
| Training window | 2016-06-20 through 2022-05-02 |
| Calibration window | 2022-05-17 through 2024-04-22 |
| Development-holdout window | 2024-05-07 through 2026-04-28 |
| Training samples | 41,954 |
| Calibration samples | 16,835 |
| Development-holdout samples | 17,070 |
| Selected development rows | 96 |
| Selected development trading dates | 51 |
| Development selected rate | 0.5624% |
| Promotion eligible now | no |
| Final-holdout enrollment ready | completed in development run `d25d6fa11a2e50daa430c15e` |

## Frozen Identity To Preserve

| Field | Value |
| --- | --- |
| Universe snapshot ID | `6b1a74750684506e1a5b` |
| Feature manifest hash | `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5` |
| Raw manifest count | 35 |
| Model artifact path | `artifacts/models/5b3f37a96a7968bca8d2f398.joblib` |
| Model artifact SHA256 | `8e77b20f634192d6b33d26663b6564c31086872cf47854869fc618d5ce818088` |
| Model training code commit | `3e05d3abf5b6baf027ed1369b62546fe59d2e1d8` |
| Selection-policy hash | `ff689a7edf893b56` |
| Portfolio-policy hash | `e52b788ebd53dc55` |
| Target-before-stop calibration schema | `tbs_calibration_governance_v1` |
| Target-before-stop calibration method | `identity` |
| Target-before-stop calibration manifest hash | `ac9e2feb545c9e16` |
| Target-before-stop calibrator artifact hash | `87dc04fafad6261f` |
| OOD governance version | `prediction_ood_governance_v2` |
| OOD governance hash prepared for enrollment audit | `56e33c072cba1b5f` |
| Path-head capability hash prepared for enrollment audit | `f9aa10594ea731eb` |
| Product-class schema | `product_class_specialist_v2` |
| Product-class scope hash | `f3f32ab6832bc0a5` |
| Product-class universe scope hash | `6411b9e8187af0a8` |
| Product-class role mapping hash | `7d2fe584f1a8a63e` |
| Prospective final-holdout sample policy | `prospective_final_holdout_sample_v1` |
| Sample-policy hash | `4ae8415df04cd538` |

## Head Manifests

| Head | Feature manifest hash |
| --- | --- |
| primary positive-return classifier | `8570ea9ddf529f8b` |
| target-before-stop classifier | `5a98554a95cb745bb755cbbf1ac016a21518683055df946e173e5b6bb3b98d42` |
| expected return | `02ba50fdd461b31a2160b7bb00c73634cf939807e294eb4b995100b825b00747` |
| MFE | `481accca0d038ce001798c8d3f5aa06dd2669beb99d8bbc18c549e43cbd95ea0` |
| MAE | `aba0d3947f2995f90f8490b55d4a59b774f8e8766d0452c8715ff35a917b4b3c` |

## Path-Head Status

| Head | Status |
| --- | --- |
| Expected return | active ATR-normalized path head |
| MFE | `ACTIVE`, `path_metric_magnitude_domain_v1` |
| MAE | `ACTIVE`, `path_metric_magnitude_domain_v1`, `robust_path_target_transform_v1` |
| MAE transform | `log1p`, hash `c3c93ddb06ea5504` |

## Selection Policy

| Policy field | Value |
| --- | ---: |
| Calibrated probability minimum | 0.55 |
| Expected return minimum | 0.001 |
| Target-before-stop probability minimum | 0.50 |
| Minimum dollar volume | 5,000,000 |
| Per-date selected-candidate limit | 5 |
| Global holdout top-N limit | 5,000 |
| Selected-rate ceiling | 20% |
| Tie-breaking | `composite_utility_score_desc_then_symbol` |

## Development Evidence Summary

| Metric | Value |
| --- | ---: |
| Primary Brier skill vs naive | 0.007555 |
| Model holdout Brier | 0.247857 |
| Naive holdout Brier | 0.249744 |
| Target-before-stop Brier | 0.210042 |
| Selected mean-return LCB 90 | 1.4734% |
| Double-cost LCB 90 | 1.4234% |
| Selected profit factor | 3.5714 |
| Portfolio total return | 35.3924% |
| Portfolio max drawdown | -8.4572% |
| Portfolio trade count | 40 |
| Portfolio profit factor | 4.5132 |
| Symbol concentration top | 33.3333% |
| Sector concentration top | 63.5417% |
| Exceptional-period concentration top | 41.3649% |
| Temporal fold positive fraction | 100% |
| Temporal fold selected observations | `[32,32,32]` |
| Expected-return holdout OOD rate | 0.00% |
| MFE holdout OOD rate | 0.00% |
| MAE holdout OOD rate | 0.00% |

All mandatory development-quality gates pass. The only failed mandatory gate is `final_holdout_required_for_promotion`, because evidence status is `DEVELOPMENT_HOLDOUT`, not `FINAL_HOLDOUT`.

## Evidence Caveats For Enrollment Review

- This remains development-holdout evidence only; it must not be described as final, live-ready, proven, safe, or profitable.
- Selected rows are heavily represented by inverse small-cap products: `TZA:32` and `RWM:29` account for 61 of 96 selected rows.
- The target-before-stop Brier skill used in triage was derived for review convenience and is not a persisted canonical gate.
- The development feature panel currently ends at 2026-06-25. If enrollment is later approved without refreshing features, the prospective baseline would be 2026-06-25 and eligible signals must have `as_of_date > 2026-06-25`.
- No future-session evidence exists in development yet.

## Pre-Enrollment Checklist Result

Completed before enrollment:

1. Confirmed the development checkout was the intended enrollment environment.
2. Confirmed artifact hash `8e77b20f634192d6b33d26663b6564c31086872cf47854869fc618d5ce818088`.
3. Confirmed feature manifest `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`.
4. Confirmed `final_holdout_runs` was empty in development before enrollment.
5. Confirmed no scanner or forward state was created between package preparation and enrollment.
6. Confirmed final-holdout sample policy `prospective_final_holdout_sample_v1` with hash `4ae8415df04cd538`.
7. Confirmed no-backfill rule is frozen as `as_of_date > baseline_market_date`.

## Executed Enrollment Command

Executed after preflight:

```bash
.venv/bin/python -m swing_rsi.cli final-holdout-init --generation 2026-06-27T14:05:10.073173+00:00
```

Result:

| Field | Value |
| --- | --- |
| Run ID | `d25d6fa11a2e50daa430c15e` |
| Created at UTC | `2026-06-27T17:44:59.273939+00:00` |
| Run status | `CREATED` |
| Model status | `COLLECTING` |
| Baseline market date | `2026-06-25` |
| First eligible future signal date | `None` |
| First eligible rule | `as_of_date > 2026-06-25` |
| Enrolled models | 1 |
| Backfilled predictions | 0 |
| Matured outcomes | 0 |
| Event count | 0 |
| Signals | 0 |
| Rejected signals | 0 |
| Artifact integrity | `PASS` |
| Promotion eligible | false |

The run enrolled only model `5b3f37a96a7968bca8d2f398`.

## State At Package Preparation

| Item | Value |
| --- | --- |
| Development Git status before package | `?? docs/DEVELOPMENT_CANDIDATE_GATE_TRIAGE.md` |
| Development SQLite | `state/engine.sqlite3`, 384,835,584 bytes, mtime Jun 27 11:08:26 2026 |
| Representative model artifact | `artifacts/models/5b3f37a96a7968bca8d2f398.joblib`, 30,710,684 bytes, mtime Jun 27 10:15:26 2026 |
| Development scanner snapshots | 3 |
| Development forward events | 0 |
| Development final-holdout runs before enrollment | 0 |
| Development final-holdout runs after enrollment | 1 |
| Development final-holdout events | 0 |
| Current feature panel | `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet` |
| Current feature rows | 90,113 |
| Current feature date range | 2006-08-03 through 2026-06-25 |
| Latest development scanner snapshot | `7394bc30e865a5c419311d51`, as-of 2026-06-25, 50 rows |

## Explicit Non-Actions

- Did not run `final-holdout-update`.
- Did not run scanner.
- Did not run forward-update.
- Did not run daily-cycle.
- Did not run discover-models.
- Did not rebuild features or labels.
- Did not update FMP data.
- Did not promote any model.
- Did not mutate SQLite, model artifacts, scanner state, forward state, final-holdout state, or operational state.
