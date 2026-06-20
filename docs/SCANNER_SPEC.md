# Scanner Specification

The live scanner is implemented in `src/swing_rsi/engine/scanner.py` and called through `swing_rsi.application.engine_service.run_live_scanner`.

## Inputs

- Latest local feature parquet from `data/features/`.
- Deployed champion model artifacts from the registry.
- Optional explicit `--include-challengers` flag for inspection when no champion exists.
- Universe snapshot metadata.

## Snapshot Behavior

The scanner:

1. Selects the latest completed session available in the feature panel.
2. Builds one as-of feature snapshot per symbol.
3. Loads champion model bundles, or review candidates only when explicitly requested.
4. Generates bullish and bearish predictions.
5. Applies probability, expected-return, and liquidity gates.
6. Creates attribution and relationship evidence.
7. Saves immutable CSV and Parquet scanner snapshots under `artifacts/scanner/`.
8. Writes snapshot and candidate rows to SQLite.
9. Returns an idempotent existing snapshot for the same date, model set, universe, and feature hash.

## Columns

Snapshots include:

- scan ID;
- as-of date;
- ticker;
- direction;
- horizon;
- calibrated probability;
- expected return;
- expected MFE and MAE;
- target-before-stop probability proxy;
- composite utility score;
- liquidity score;
- regime;
- sector;
- top attribution categories;
- confirming relationships;
- divergences;
- model ID;
- model state;
- feature snapshot hash;
- candidate status;
- exclusion reason.

Scanner predictions are candidates, not trades. Only rows that pass configured gates become actionable paper candidates.
