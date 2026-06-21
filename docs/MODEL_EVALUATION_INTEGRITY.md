# Model Evaluation Integrity

Generated: 2026-06-20

## Evaluation Layers

Autonomous model evaluation is separated into three layers.

1. Prediction-level diagnostics evaluate every eligible holdout observation.
   These include Brier score, Brier skill versus the matching naive control,
   log loss, calibration intercept/slope, expected calibration error,
   calibration deciles, regression MAE/RMSE, rank correlation, and
   predicted-versus-realized return deciles.
2. Selected-candidate diagnostics evaluate rows that pass the frozen selection
   policy. These include selected count/rate, candidates per date, symbol,
   sector, year and regime concentration, mean/median returns, lower confidence
   bound, profit factor, expected MFE/MAE, transaction-cost sensitivity,
   threshold, and turnover. The selected row sequence drawdown is retained only
   as `selected_row_sequence_drawdown`.
3. Portfolio holdout diagnostics come only from chronological portfolio
   simulation. Portfolio maximum drawdown is calculated from daily portfolio
   equity, not from sequential compounding of cross-sectional rows.

## Research Dates

Raw data may begin before the research period for trailing-feature warm-up.
Eligible model rows must begin on or after the configured `research_start`, and
label end dates must not exceed `research_end`.

The current default research contract is:

- `research_start`: `2016-06-20`
- `research_end`: latest modeling date unless explicitly configured
- returns/MFE/MAE units: decimal returns, where `0.05` means 5%
- bearish returns and excursions are direction-adjusted explicitly in labels

## Portfolio Policy

The corrected holdout portfolio simulation:

- processes prediction dates chronologically;
- treats same-date predictions as one decision set;
- enters at next available open;
- supports bullish and bearish directions;
- enforces one active position per symbol unless configured otherwise;
- enforces maximum concurrent positions, sector fraction, gross exposure, and
  net exposure;
- includes round-trip cost and slippage;
- marks positions through daily equity;
- records rejected/skipped candidates with reasons;
- preserves deterministic conservative same-bar target/stop ambiguity handling.

Default discovery portfolio policy:

- horizon: 10 sessions
- round-trip cost: 5 bps
- slippage: 2 bps
- max concurrent positions: 5
- max position per symbol: 1
- max sector fraction: 50%
- max gross exposure: 100%
- max net exposure: 100%

## Quality Gates

Every registered model can store canonical gate records with:

- `gate_id`
- `gate_name`
- `category`
- `scope`
- `metric_name`
- `threshold`
- `comparator`
- `actual_value`
- `status`
- `mandatory`
- `evidence_source`
- `reason`
- `evaluated_at_utc`
- `configuration_hash`

Promotion eligibility is computed only from persisted canonical gates. Missing
canonical mandatory gates block promotion. `FAIL`, mandatory
`NOT_CONFIGURED`, and mandatory `NOT_APPLICABLE` all block promotion.

The selection-rate cap is intentionally `NOT_CONFIGURED` until a user-approved
policy threshold exists. Models remain inspectable as candidates but are not
promotion eligible.

## Prediction Sanity

Regression predictions store raw and transformed values separately. The current
transform method is `none`; no clipping is applied. Out-of-distribution flags
are computed against train-only robust target quantiles.

Scanner snapshots include raw, transformed, and OOD flag columns for expected
return, expected MFE, and expected MAE.

## Reproduction Commands

```bash
python -m swing_rsi.cli model-audit --generation latest
python -m swing_rsi.cli model-audit --model-id 2bfd1ba248c6f489efb31664 --export-dir reports/model_audit
```

Generated audit exports are written under ignored `reports/` paths and must not
be committed.
