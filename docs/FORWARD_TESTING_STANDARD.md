# Forward Testing Standard

## Principle

A forward prediction must exist before its outcome. Historical records must never be rewritten to make the system look better.

## Separate append-only records

### Signal record

Written when a frozen model scanner signal is generated:

- Signal ID
- Timestamp and ticker
- Model version and rule ID
- Model ID and feature snapshot hash
- Candidate attribution and supporting evidence
- Entry, stop, and target references
- Expected probability, return, MFE, MAE, and candidate status
- Confidence or research score
- Data version

### Position and outcome events

Written only when the corresponding paper event becomes knowable:

- `ENTRY_PENDING`
- `ENTRY_FILLED`
- `POSITION_MARKED`
- `STOP_UPDATED`
- `TARGET_UPDATED`
- `EXIT_FILLED`
- `POSITION_EXPIRED`
- `POSITION_CANCELED`
- `DATA_CORRECTION_RECORDED`

Signal, position, and outcome events are stored separately. Later events do not mutate the original signal record.

## No cherry-picking

- Log every eligible signal.
- Log no-signal days separately later if calibration requires them.
- Do not delete failed records.
- Do not change thresholds after seeing an outcome without creating a new model version.

## Paper forward testing versus historical walk-forward

Historical walk-forward validation is a research evaluation method. Paper forward testing starts after a model version is frozen and records only signals and position events that become knowable after deployment.

A newly trained model is a challenger. It may not silently alter champion predictions or rewrite open paper positions.

## Model versions

Any change to parameters, features, labels, costs, entry timing, or filtering rules requires a new model version.
