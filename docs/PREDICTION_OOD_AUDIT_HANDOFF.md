# Prediction OOD Audit Handoff

Generated: 2026-06-21

## Scope

This was a focused regression prediction out-of-distribution audit on the latest model generation created after the persisted selection-policy fixes.

No FMP update, model promotion, forward-update, daily-cycle run, feature addition, model-family addition, data-source addition, gate weakening, or prior-artifact mutation was performed. `.env` was not opened or printed.

## Latest Generation

- Generation ID: `2026-06-21T02:34:35.295826+00:00`
- Modeling parquet: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`
- Feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- Eligible model row date range: `2016-06-20` to `2026-04-22`
- Research end persisted in model metrics: `2026-06-18`
- Raw / feature warm-up first date from model metrics: `2006-08-03`

The eligible model row range ends before the research end because the 10-session labels must have complete future data inside the research window. Rows before `2016-06-20` are warm-up only for trailing features.

Model IDs:

- `4e7655c871ece5238006e38c` bull hist_gradient_boosting horizon 10
- `594020c7b2ea94757b34351d` bull naive_base_rate horizon 10
- `61c91fd5830d89e379ca33f7` bull extra_trees horizon 10
- `6b5f102c1cdebf946f0b959c` bear hist_gradient_boosting horizon 10
- `87b08e653db529893bbac3f6` bull logistic_regression horizon 10
- `a75df8d1c5f643547eda7992` bear extra_trees horizon 10
- `d95bc4cea6a158a344f85175` bear naive_base_rate horizon 10
- `e641a2ba34ed11f8bac8c3b0` bear logistic_regression horizon 10

All 8 models remain `CANDIDATE`. No model is promotion eligible.

## Current Gate Definition

Implementation evidence:

- `src/swing_rsi/engine/models.py:500-522`: `_prediction_sanity_metrics`
- `src/swing_rsi/engine/models.py:1331-1357`: calls the sanity function separately for return, MFE, and MAE
- `src/swing_rsi/engine/models.py:1125-1138`: canonical gate `prediction_out_of_distribution_absent`
- `src/swing_rsi/engine/models.py:1724-1745`: scanner prediction OOD flags use the stored per-head bounds

Current rule:

1. For each regression head, compute train-target quantiles from the matching directional target only.
2. Bound low = training target q01.
3. Bound high = training target q99.
4. OOD if holdout prediction `< q01` or `> q99`.
5. `prediction_sanity_ood_total = return_ood_count + mfe_ood_count + mae_ood_count`.
6. Mandatory gate passes only when `prediction_sanity_ood_total == 0`.

Raw and transformed predictions are identical:

- `*_prediction_transform_method = "none"`
- raw prediction = transformed prediction
- dashboard/scanner display converts decimals to percentages only for display

## Confirmed Root Cause

No implementation bug was confirmed.

Findings by candidate cause:

- Unit/sign bug: not confirmed. Values are decimal returns; `0.05` means 5%.
- Wrong target bounds applied to regression head: not confirmed. Return, MFE, and MAE each use their matching target distribution.
- Calibration/holdout leakage: not confirmed. Bounds use training targets only; holdout target percentiles are not used to define OOD bounds.
- Incorrect direction transformation: not confirmed. Bull and bear label recomputation matched stored labels exactly for audited rows.
- Overly broad model extrapolation: confirmed for several heads, especially leveraged ETF tail predictions.
- Mathematically invalid zero-tolerance gate: the gate is not a coding error, but it is not statistically meaningful as a universal promotion criterion without an explicit governance decision. It requires zero q01/q99 exceedances across tens of thousands of predictions. If predictions were sampled like the training target distribution, q01/q99 bounds define a central 98% interval, so some exceedance would be expected by construction. The current rule is therefore a strict safety policy, not a calibrated statistical quality test.
- Legitimate model failure: yes under the current mandatory gate. The models genuinely emit predictions outside the train-only robust bounds, so promotion remains blocked.

No code correction was made. No tests were added because no code was changed. No fresh generation was created.

## Unit And Sign Audit

Verified:

- `0.05` means 5%.
- Bullish forward return uses `horizon_close / next_open - 1`.
- Bearish forward return uses `next_open / horizon_close - 1`.
- Bullish MFE uses `future_high / next_open - 1`.
- Bearish MFE uses `next_open / future_low - 1`.
- Bullish MAE uses `future_low / next_open - 1`.
- Bearish MAE uses `next_open / future_high - 1`.
- MFE is the favorable excursion and is normally nonnegative, though it can cross zero when no favorable price occurs after the next open.
- MAE is the adverse excursion and is normally nonpositive, though it can cross zero when all future bars remain favorable versus the next open.
- No display percentage is fed back into model evaluation.
- No inverse transform is applied; transform method is `none`.
- All audited holdout predictions are finite.

## Complete Per-Head OOD Table

Column format for distributions: `min/q01/q05/q50/q95/q99/max`.

| model | head | train n | train target | calibration target | holdout target | holdout prediction | OOD | max beyond |
|---|---|---:|---|---|---|---|---:|---:|
| `4e7655c871ece5238006e38c` bull hist_gradient_boosting | return | 41884 | -0.7617/-0.2341/-0.1231/0.0048/0.1258/0.2566/1.3512 | -0.4615/-0.2361/-0.1293/0.0046/0.1382/0.2639/0.6811 | -0.5936/-0.2285/-0.1182/0.0027/0.1261/0.2626/1.0267 | -0.2368/-0.0502/-0.0151/0.0046/0.0309/0.0614/0.1712 | 1 (0.006%) | 0.0027 |
| `4e7655c871ece5238006e38c` bull hist_gradient_boosting | mfe | 41884 | 0.0000/0.0003/0.0024/0.0314/0.1842/0.3400/1.4550 | 0.0000/0.0006/0.0032/0.0370/0.1932/0.3319/0.8560 | 0.0000/0.0004/0.0025/0.0316/0.1818/0.3573/1.3600 | 0.0177/0.0195/0.0206/0.0396/0.1229/0.1752/0.4827 | 4 (0.023%) | 0.1427 |
| `4e7655c871ece5238006e38c` bull hist_gradient_boosting | mae | 41884 | -0.7992/-0.2884/-0.1714/-0.0293/-0.0019/-0.0002/0.0000 | -0.5452/-0.2778/-0.1708/-0.0333/-0.0025/-0.0004/0.0000 | -0.6529/-0.2866/-0.1673/-0.0295/-0.0022/-0.0003/0.0000 | -0.3370/-0.1582/-0.1110/-0.0372/-0.0204/-0.0185/-0.0169 | 8 (0.047%) | 0.0486 |
| `594020c7b2ea94757b34351d` bull naive_base_rate | return | 41884 | -0.7617/-0.2341/-0.1231/0.0048/0.1258/0.2566/1.3512 | -0.4615/-0.2361/-0.1293/0.0046/0.1382/0.2639/0.6811 | -0.5936/-0.2285/-0.1182/0.0027/0.1261/0.2626/1.0267 | -0.1686/-0.0578/-0.0305/0.0040/0.0317/0.0696/0.1497 | 0 (0.000%) | 0.0000 |
| `594020c7b2ea94757b34351d` bull naive_base_rate | mfe | 41884 | 0.0000/0.0003/0.0024/0.0314/0.1842/0.3400/1.4550 | 0.0000/0.0006/0.0032/0.0370/0.1932/0.3319/0.8560 | 0.0000/0.0004/0.0025/0.0316/0.1818/0.3573/1.3600 | 0.0002/0.0121/0.0182/0.0402/0.1286/0.1850/0.8950 | 9 (0.053%) | 0.5551 |
| `594020c7b2ea94757b34351d` bull naive_base_rate | mae | 41884 | -0.7992/-0.2884/-0.1714/-0.0293/-0.0019/-0.0002/0.0000 | -0.5452/-0.2778/-0.1708/-0.0333/-0.0025/-0.0004/0.0000 | -0.6529/-0.2866/-0.1673/-0.0295/-0.0022/-0.0003/0.0000 | -0.9822/-0.1741/-0.1197/-0.0374/-0.0161/-0.0110/-0.0009 | 17 (0.100%) | 0.6939 |
| `61c91fd5830d89e379ca33f7` bull extra_trees | return | 41884 | -0.7617/-0.2341/-0.1231/0.0048/0.1258/0.2566/1.3512 | -0.4615/-0.2361/-0.1293/0.0046/0.1382/0.2639/0.6811 | -0.5936/-0.2285/-0.1182/0.0027/0.1261/0.2626/1.0267 | -0.1884/-0.0599/-0.0255/0.0031/0.0367/0.0613/0.1433 | 0 (0.000%) | 0.0000 |
| `61c91fd5830d89e379ca33f7` bull extra_trees | mfe | 41884 | 0.0000/0.0003/0.0024/0.0314/0.1842/0.3400/1.4550 | 0.0000/0.0006/0.0032/0.0370/0.1932/0.3319/0.8560 | 0.0000/0.0004/0.0025/0.0316/0.1818/0.3573/1.3600 | 0.0101/0.0145/0.0185/0.0397/0.1275/0.1739/0.3376 | 0 (0.000%) | 0.0000 |
| `61c91fd5830d89e379ca33f7` bull extra_trees | mae | 41884 | -0.7992/-0.2884/-0.1714/-0.0293/-0.0019/-0.0002/0.0000 | -0.5452/-0.2778/-0.1708/-0.0333/-0.0025/-0.0004/0.0000 | -0.6529/-0.2866/-0.1673/-0.0295/-0.0022/-0.0003/0.0000 | -0.3283/-0.1673/-0.1186/-0.0394/-0.0185/-0.0149/-0.0081 | 3 (0.018%) | 0.0400 |
| `6b5f102c1cdebf946f0b959c` bear hist_gradient_boosting | return | 41884 | -0.5747/-0.2042/-0.1117/-0.0048/0.1404/0.3056/3.1967 | -0.4052/-0.2088/-0.1214/-0.0046/0.1485/0.3091/0.8570 | -0.5066/-0.2080/-0.1120/-0.0027/0.1340/0.2961/1.4606 | -0.1858/-0.0420/-0.0188/-0.0023/0.0279/0.0929/0.7161 | 27 (0.158%) | 0.4105 |
| `6b5f102c1cdebf946f0b959c` bear hist_gradient_boosting | mfe | 41884 | 0.0000/0.0002/0.0019/0.0302/0.2068/0.4052/3.9812 | 0.0000/0.0004/0.0025/0.0344/0.2060/0.3846/1.1986 | 0.0000/0.0003/0.0022/0.0303/0.2009/0.4017/1.8811 | 0.0088/0.0207/0.0221/0.0395/0.1336/0.2300/1.4604 | 26 (0.152%) | 1.0552 |
| `6b5f102c1cdebf946f0b959c` bear hist_gradient_boosting | mae | 41884 | -0.5927/-0.2537/-0.1555/-0.0305/-0.0024/-0.0003/0.0000 | -0.4612/-0.2492/-0.1619/-0.0357/-0.0032/-0.0006/0.0000 | -0.5763/-0.2632/-0.1539/-0.0306/-0.0025/-0.0004/0.0000 | -0.2950/-0.1383/-0.1043/-0.0368/-0.0197/-0.0188/-0.0163 | 2 (0.012%) | 0.0413 |
| `87b08e653db529893bbac3f6` bull logistic_regression | return | 41884 | -0.7617/-0.2341/-0.1231/0.0048/0.1258/0.2566/1.3512 | -0.4615/-0.2361/-0.1293/0.0046/0.1382/0.2639/0.6811 | -0.5936/-0.2285/-0.1182/0.0027/0.1261/0.2626/1.0267 | -0.1686/-0.0578/-0.0305/0.0040/0.0317/0.0696/0.1497 | 0 (0.000%) | 0.0000 |
| `87b08e653db529893bbac3f6` bull logistic_regression | mfe | 41884 | 0.0000/0.0003/0.0024/0.0314/0.1842/0.3400/1.4550 | 0.0000/0.0006/0.0032/0.0370/0.1932/0.3319/0.8560 | 0.0000/0.0004/0.0025/0.0316/0.1818/0.3573/1.3600 | 0.0002/0.0121/0.0182/0.0402/0.1286/0.1850/0.8950 | 9 (0.053%) | 0.5551 |
| `87b08e653db529893bbac3f6` bull logistic_regression | mae | 41884 | -0.7992/-0.2884/-0.1714/-0.0293/-0.0019/-0.0002/0.0000 | -0.5452/-0.2778/-0.1708/-0.0333/-0.0025/-0.0004/0.0000 | -0.6529/-0.2866/-0.1673/-0.0295/-0.0022/-0.0003/0.0000 | -0.9822/-0.1741/-0.1197/-0.0374/-0.0161/-0.0110/-0.0009 | 17 (0.100%) | 0.6939 |
| `a75df8d1c5f643547eda7992` bear extra_trees | return | 41884 | -0.5747/-0.2042/-0.1117/-0.0048/0.1404/0.3056/3.1967 | -0.4052/-0.2088/-0.1214/-0.0046/0.1485/0.3091/0.8570 | -0.5066/-0.2080/-0.1120/-0.0027/0.1340/0.2961/1.4606 | -0.0948/-0.0435/-0.0233/0.0002/0.0435/0.0996/0.4996 | 14 (0.082%) | 0.1940 |
| `a75df8d1c5f643547eda7992` bear extra_trees | mfe | 41884 | 0.0000/0.0002/0.0019/0.0302/0.2068/0.4052/3.9812 | 0.0000/0.0004/0.0025/0.0344/0.2060/0.3846/1.1986 | 0.0000/0.0003/0.0022/0.0303/0.2009/0.4017/1.8811 | 0.0083/0.0154/0.0192/0.0425/0.1474/0.2357/0.7841 | 25 (0.146%) | 0.3789 |
| `a75df8d1c5f643547eda7992` bear extra_trees | mae | 41884 | -0.5927/-0.2537/-0.1555/-0.0305/-0.0024/-0.0003/0.0000 | -0.4612/-0.2492/-0.1619/-0.0357/-0.0032/-0.0006/0.0000 | -0.5763/-0.2632/-0.1539/-0.0306/-0.0025/-0.0004/0.0000 | -0.2323/-0.1337/-0.1029/-0.0372/-0.0180/-0.0139/-0.0098 | 0 (0.000%) | 0.0000 |
| `d95bc4cea6a158a344f85175` bear naive_base_rate | return | 41884 | -0.5747/-0.2042/-0.1117/-0.0048/0.1404/0.3056/3.1967 | -0.4052/-0.2088/-0.1214/-0.0046/0.1485/0.3091/0.8570 | -0.5066/-0.2080/-0.1120/-0.0027/0.1340/0.2961/1.4606 | -0.1390/-0.0536/-0.0255/-0.0003/0.0523/0.1025/0.5418 | 1 (0.006%) | 0.2362 |
| `d95bc4cea6a158a344f85175` bear naive_base_rate | mfe | 41884 | 0.0000/0.0002/0.0019/0.0302/0.2068/0.4052/3.9812 | 0.0000/0.0004/0.0025/0.0344/0.2060/0.3846/1.1986 | 0.0000/0.0003/0.0022/0.0303/0.2009/0.4017/1.8811 | -0.0144/0.0035/0.0114/0.0412/0.1598/0.2496/1.5797 | 111 (0.650%) | 1.1745 |
| `d95bc4cea6a158a344f85175` bear naive_base_rate | mae | 41884 | -0.5927/-0.2537/-0.1555/-0.0305/-0.0024/-0.0003/0.0000 | -0.4612/-0.2492/-0.1619/-0.0357/-0.0032/-0.0006/0.0000 | -0.5763/-0.2632/-0.1539/-0.0306/-0.0025/-0.0004/0.0000 | -0.6525/-0.1501/-0.1053/-0.0368/-0.0192/-0.0145/-0.0055 | 8 (0.047%) | 0.3987 |
| `e641a2ba34ed11f8bac8c3b0` bear logistic_regression | return | 41884 | -0.5747/-0.2042/-0.1117/-0.0048/0.1404/0.3056/3.1967 | -0.4052/-0.2088/-0.1214/-0.0046/0.1485/0.3091/0.8570 | -0.5066/-0.2080/-0.1120/-0.0027/0.1340/0.2961/1.4606 | -0.1390/-0.0536/-0.0255/-0.0003/0.0523/0.1025/0.5418 | 1 (0.006%) | 0.2362 |
| `e641a2ba34ed11f8bac8c3b0` bear logistic_regression | mfe | 41884 | 0.0000/0.0002/0.0019/0.0302/0.2068/0.4052/3.9812 | 0.0000/0.0004/0.0025/0.0344/0.2060/0.3846/1.1986 | 0.0000/0.0003/0.0022/0.0303/0.2009/0.4017/1.8811 | -0.0144/0.0035/0.0114/0.0412/0.1598/0.2496/1.5797 | 111 (0.650%) | 1.1745 |
| `e641a2ba34ed11f8bac8c3b0` bear logistic_regression | mae | 41884 | -0.5927/-0.2537/-0.1555/-0.0305/-0.0024/-0.0003/0.0000 | -0.4612/-0.2492/-0.1619/-0.0357/-0.0032/-0.0006/0.0000 | -0.5763/-0.2632/-0.1539/-0.0306/-0.0025/-0.0004/0.0000 | -0.6525/-0.1501/-0.1053/-0.0368/-0.0192/-0.0145/-0.0055 | 8 (0.047%) | 0.3987 |

The recomputed OOD counts match the persisted registry metrics exactly.

## Ten Most Extreme Predictions Per Head

Values are raw decimals with display percentages in parentheses. `d=` is distance beyond the matching training q01/q99 bound.

- `4e7655c871ece5238006e38c` return: SOXL 2024-07-29 -0.2368 (-23.68%) d=0.0027; AAPL 2024-05-02 0.0035 (0.35%) d=0.0000; AAPL 2024-05-03 -0.0040 (-0.40%) d=0.0000; AAPL 2024-05-06 0.0019 (0.19%) d=0.0000; AAPL 2024-05-07 -0.0009 (-0.09%) d=0.0000; AAPL 2024-05-08 -0.0034 (-0.34%) d=0.0000; AAPL 2024-05-09 -0.0067 (-0.67%) d=0.0000; AAPL 2024-05-10 -0.0029 (-0.29%) d=0.0000; AAPL 2024-05-13 -0.0042 (-0.42%) d=0.0000; AAPL 2024-05-14 -0.0041 (-0.41%) d=0.0000
- `4e7655c871ece5238006e38c` mfe: SOXS 2024-07-31 0.4827 (48.27%) d=0.1427; SOXL 2025-04-16 0.4113 (41.13%) d=0.0713; SOXS 2024-07-29 0.3882 (38.82%) d=0.0483; SOXL 2025-04-14 0.3618 (36.18%) d=0.0218; AAPL 2024-05-02 0.0316 (3.16%) d=0.0000; AAPL 2024-05-03 0.0394 (3.94%) d=0.0000; AAPL 2024-05-06 0.0358 (3.58%) d=0.0000; AAPL 2024-05-07 0.0402 (4.02%) d=0.0000; AAPL 2024-05-08 0.0322 (3.22%) d=0.0000; AAPL 2024-05-09 0.0318 (3.18%) d=0.0000
- `4e7655c871ece5238006e38c` mae: SOXL 2024-07-29 -0.3370 (-33.70%) d=0.0486; SOXL 2024-07-30 -0.3186 (-31.86%) d=0.0302; SOXL 2024-08-01 -0.3125 (-31.25%) d=0.0241; SOXS 2024-08-07 -0.3105 (-31.05%) d=0.0222; SOXL 2024-08-02 -0.2966 (-29.66%) d=0.0082; SOXS 2025-04-21 -0.2924 (-29.24%) d=0.0040; SOXS 2024-08-06 -0.2911 (-29.11%) d=0.0027; SOXS 2025-04-16 -0.2890 (-28.90%) d=0.0007; AAPL 2024-05-02 -0.0362 (-3.62%) d=0.0000; AAPL 2024-05-03 -0.0513 (-5.13%) d=0.0000
- `594020c7b2ea94757b34351d` return: no OOD rows; largest distances are 0.0000.
- `594020c7b2ea94757b34351d` mfe: SOXS 2025-04-09 0.8950 (89.50%) d=0.5551; SOXS 2025-04-07 0.4760 (47.60%) d=0.1360; SQQQ 2025-04-09 0.4436 (44.36%) d=0.1036; SOXS 2025-04-08 0.4307 (43.07%) d=0.0907; TZA 2025-04-09 0.3858 (38.58%) d=0.0459; SPXU 2025-04-09 0.3564 (35.64%) d=0.0164; SOXL 2025-04-07 0.3437 (34.37%) d=0.0037; SOXL 2025-04-09 0.3437 (34.37%) d=0.0037; SPY 2026-01-21 0.0002 (0.02%) d=0.0001; AAPL 2024-05-02 0.0299 (2.99%) d=0.0000
- `594020c7b2ea94757b34351d` mae: SOXS 2025-04-09 -0.9822 (-98.22%) d=0.6939; SQQQ 2025-04-09 -0.4527 (-45.27%) d=0.1644; SOXL 2025-04-09 -0.4287 (-42.87%) d=0.1403; SOXS 2025-04-07 -0.4031 (-40.31%) d=0.1148; TZA 2025-04-09 -0.3861 (-38.61%) d=0.0978; SOXL 2025-04-07 -0.3823 (-38.23%) d=0.0939; SOXL 2025-04-08 -0.3779 (-37.79%) d=0.0895; SOXS 2025-04-10 -0.3609 (-36.09%) d=0.0725; SPXU 2025-04-09 -0.3582 (-35.82%) d=0.0698; SOXS 2025-04-16 -0.3499 (-34.99%) d=0.0615
- `61c91fd5830d89e379ca33f7` return: no OOD rows; largest distances are 0.0000.
- `61c91fd5830d89e379ca33f7` mfe: no OOD rows; largest distances are 0.0000.
- `61c91fd5830d89e379ca33f7` mae: SOXL 2024-08-05 -0.3283 (-32.83%) d=0.0400; SOXS 2025-04-14 -0.2902 (-29.02%) d=0.0018; SOXS 2025-04-16 -0.2899 (-28.99%) d=0.0015; remaining top-distance rows are inside bounds.
- `6b5f102c1cdebf946f0b959c` return: SOXL 2024-08-01 0.7161 (71.61%) d=0.4105; SOXL 2024-08-02 0.5660 (56.60%) d=0.2604; SOXS 2025-04-22 0.4886 (48.86%) d=0.1830; SOXS 2025-04-21 0.4773 (47.73%) d=0.1717; SOXS 2025-04-23 0.3996 (39.96%) d=0.0939; SOXL 2024-07-31 0.3918 (39.18%) d=0.0862; SOXS 2024-08-07 0.3832 (38.32%) d=0.0776; SOXL 2024-07-29 0.3740 (37.40%) d=0.0684; SOXS 2025-04-16 0.3563 (35.63%) d=0.0507; SOXS 2024-08-05 0.3514 (35.14%) d=0.0458
- `6b5f102c1cdebf946f0b959c` mfe: SOXL 2024-07-29 1.4604 (146.04%) d=1.0552; SOXL 2024-07-26 1.2353 (123.53%) d=0.8301; SOXL 2024-07-31 1.1685 (116.85%) d=0.7633; SOXL 2024-08-01 0.7155 (71.55%) d=0.3102; SOXL 2024-07-24 0.7152 (71.52%) d=0.3100; SOXL 2024-09-10 0.6421 (64.21%) d=0.2369; SOXS 2026-04-14 0.5878 (58.78%) d=0.1826; SOXL 2024-09-11 0.5637 (56.37%) d=0.1585; SOXL 2025-04-03 0.5292 (52.92%) d=0.1240; SOXS 2026-04-13 0.5172 (51.72%) d=0.1120
- `6b5f102c1cdebf946f0b959c` mae: SOXL 2025-04-16 -0.2950 (-29.50%) d=0.0413; SOXL 2025-04-14 -0.2658 (-26.58%) d=0.0121; remaining top-distance rows are inside bounds.
- `87b08e653db529893bbac3f6` return: no OOD rows; largest distances are 0.0000.
- `87b08e653db529893bbac3f6` mfe: same top OOD rows as `594020c7b2ea94757b34351d` MFE.
- `87b08e653db529893bbac3f6` mae: same top OOD rows as `594020c7b2ea94757b34351d` MAE.
- `a75df8d1c5f643547eda7992` return: SOXL 2024-07-29 0.4996 (49.96%) d=0.1940; SOXL 2024-07-26 0.4045 (40.45%) d=0.0989; SOXL 2024-07-30 0.3884 (38.84%) d=0.0828; SOXL 2024-08-01 0.3845 (38.45%) d=0.0789; SOXL 2024-07-31 0.3740 (37.40%) d=0.0684; SOXS 2025-04-22 0.3721 (37.21%) d=0.0665; SOXS 2025-04-21 0.3697 (36.97%) d=0.0641; SOXS 2025-04-16 0.3611 (36.11%) d=0.0555; SOXS 2025-04-23 0.3535 (35.35%) d=0.0479; SOXL 2024-08-02 0.3363 (33.63%) d=0.0307
- `a75df8d1c5f643547eda7992` mfe: SOXL 2024-08-02 0.7841 (78.41%) d=0.3789; SOXL 2024-07-29 0.7203 (72.03%) d=0.3151; SOXL 2024-08-05 0.7021 (70.21%) d=0.2969; SOXL 2024-07-30 0.6817 (68.17%) d=0.2765; SOXL 2024-08-01 0.6808 (68.08%) d=0.2756; SOXL 2024-07-31 0.5911 (59.11%) d=0.1859; SOXL 2024-08-06 0.5670 (56.70%) d=0.1618; SOXL 2024-07-25 0.5530 (55.30%) d=0.1478; SOXS 2025-04-23 0.5254 (52.54%) d=0.1202; SOXS 2025-04-14 0.5036 (50.36%) d=0.0984
- `a75df8d1c5f643547eda7992` mae: no OOD rows; largest distances are 0.0000.
- `d95bc4cea6a158a344f85175` return: SOXS 2025-04-09 0.5418 (54.18%) d=0.2362; remaining top-distance rows are inside bounds.
- `d95bc4cea6a158a344f85175` mfe: SOXS 2025-04-09 1.5797 (157.97%) d=1.1745; SOXL 2025-04-09 0.7349 (73.49%) d=0.3297; SQQQ 2025-04-09 0.7077 (70.77%) d=0.3025; SOXL 2025-04-08 0.6156 (61.56%) d=0.2104; SOXL 2025-04-07 0.6081 (60.81%) d=0.2029; TZA 2025-04-09 0.5970 (59.70%) d=0.1918; SOXL 2025-04-10 0.5889 (58.89%) d=0.1837; SOXS 2025-04-07 0.5682 (56.82%) d=0.1630; SPXU 2025-04-09 0.5497 (54.97%) d=0.1445; SOXS 2025-04-10 0.5460 (54.60%) d=0.1408
- `d95bc4cea6a158a344f85175` mae: SOXS 2025-04-09 -0.6525 (-65.25%) d=0.3987; SOXS 2025-04-07 -0.3437 (-34.37%) d=0.0900; SQQQ 2025-04-09 -0.3297 (-32.97%) d=0.0760; SOXS 2025-04-08 -0.3064 (-30.64%) d=0.0527; SOXL 2025-04-09 -0.2870 (-28.70%) d=0.0333; TZA 2025-04-09 -0.2858 (-28.58%) d=0.0321; SPXU 2025-04-09 -0.2656 (-26.56%) d=0.0119; SOXL 2025-04-07 -0.2611 (-26.11%) d=0.0074; remaining top-distance rows are inside bounds.
- `e641a2ba34ed11f8bac8c3b0` return: same top OOD row as `d95bc4cea6a158a344f85175` return.
- `e641a2ba34ed11f8bac8c3b0` mfe: same top OOD rows as `d95bc4cea6a158a344f85175` MFE.
- `e641a2ba34ed11f8bac8c3b0` mae: same top OOD rows as `d95bc4cea6a158a344f85175` MAE.

## Label Recomputation From Raw OHLCV

Manual recomputation used `data/raw/<symbol>.csv`, next-session open as entry, horizon 10 close as exit, and future high/low over bars `t+1` through `t+10`.

| category | symbol | date | dir | source head | pred | stored ret/mfe/mae | manual ret/mfe/mae | max diff | match |
|---|---|---|---|---|---:|---|---|---:|---|
| normal | AAPL | 2024-05-02 | bull | return | 0.0035 (0.35%) | 0.0171/0.0238/-0.0334 | 0.0171/0.0238/-0.0334 | 0.00e+00 | True |
| normal | AMD | 2024-05-02 | bull | return | 0.0494 (4.94%) | 0.0932/0.1298/-0.0102 | 0.0932/0.1298/-0.0102 | 0.00e+00 | True |
| normal | AMZN | 2024-05-02 | bull | return | 0.0097 (0.97%) | -0.0180/0.0252/-0.0228 | -0.0180/0.0252/-0.0228 | 0.00e+00 | True |
| normal | AAPL | 2024-05-02 | bear | return | -0.0006 (-0.06%) | -0.0168/0.0345/-0.0233 | -0.0168/0.0345/-0.0233 | 0.00e+00 | True |
| normal | AMD | 2024-05-02 | bear | return | -0.0508 (-5.08%) | -0.0853/0.0103/-0.1149 | -0.0853/0.0103/-0.1149 | 0.00e+00 | True |
| ood, most_extreme_bearish, leveraged_etf_example | SOXS | 2025-04-09 | bear | mfe | 1.5797 (157.97%) | 0.2353/0.2405/-0.1950 | 0.2353/0.2405/-0.1950 | 0.00e+00 | True |
| ood | SOXL | 2024-07-29 | bear | mfe | 1.4604 (146.04%) | 0.3493/0.8034/-0.0532 | 0.3493/0.8034/-0.0532 | 0.00e+00 | True |
| ood | SOXL | 2024-07-26 | bear | mfe | 1.2353 (123.53%) | 0.3986/0.8455/-0.0362 | 0.3986/0.8455/-0.0362 | 0.00e+00 | True |
| ood | SOXL | 2024-07-31 | bear | mfe | 1.1685 (116.85%) | 0.1997/0.7894/-0.0316 | 0.1997/0.7894/-0.0316 | 0.00e+00 | True |
| ood, most_extreme_bullish | SOXS | 2025-04-09 | bull | mae | -0.9822 (-98.22%) | -0.1905/0.2423/-0.1939 | -0.1905/0.2423/-0.1939 | 0.00e+00 | True |
| stock_example | AMD | 2025-04-08 | bear | mfe | 0.4223 (42.23%) | -0.1236/0.0044/-0.1909 | -0.1236/0.0044/-0.1909 | 0.00e+00 | True |

All 11 audited rows matched stored labels exactly.

## Before Versus After OOD Counts

No code bug was confirmed, so there is no corrected generation and no after-count. The current counts remain the authoritative counts for generation `2026-06-21T02:34:35.295826+00:00`.

## Proposed Governance Replacement

Do not implement this without an explicit methodology decision.

A scientifically defensible replacement would separate implementation sanity from statistical extrapolation:

1. Mandatory hard-fail gates:
   - nonfinite prediction count must be zero;
   - head-to-target-bound mapping must be verified;
   - decimal/percentage unit contract must be verified;
   - raw/transformed prediction lineage must be auditable;
   - bounds must be fit from training data only.
2. Configured OOD severity gates:
   - per-head robust-bound exceedance rate must be below a predeclared threshold;
   - maximum exceedance beyond the training q01/q99 bound must be below a predeclared severity threshold;
   - predictions outside training min/max or outside economic feasibility bounds should be a separate mandatory failure.
3. Review-only diagnostics:
   - q01/q99 exceedance tables by symbol, sector, instrument role, and leveraged/inverse flag.

Rationale: q01/q99 bounds intentionally exclude 2% of the training target distribution. A zero-exceedance requirement across tens of thousands of predictions is a strict safety policy, not a calibrated statistical test.

## Verification Results

```text
.venv/bin/pytest
115 passed, 161 warnings in 57.16s

.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check .
91 files already formatted

.venv/bin/mypy src
Success: no issues found in 53 source files
```

Warnings were existing pandas fragmentation warnings in feature construction and one joblib core-count warning. No automated test contacted FMP.

## Promotion Eligibility

Promotion eligibility remains `NO` for every model in the latest generation. `prediction_out_of_distribution_absent` remains a failed mandatory gate for all eight models.

## Smallest Next Task

Make an explicit model-governance decision for the prediction OOD gate.

Acceptance criteria:

- decide whether zero q01/q99 exceedance is intended as a hard safety rule;
- if not, define precommitted per-head OOD rate and severity thresholds;
- define separate hard failures for nonfinite values, unit/sign defects, wrong head-bound mapping, and training-only-bound violations;
- update `docs/MODEL_VALIDATION_STANDARD.md` and `docs/MODEL_GOVERNANCE.md`;
- only then implement the gate change with tests and rerun discovery once.
