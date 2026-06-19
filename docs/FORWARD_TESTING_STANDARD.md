# Forward Testing Standard

## Principle

A forward prediction must exist before its outcome. Historical records must never be rewritten to make the system look better.

## Separate append-only records

### Signal record

Written when a signal is generated:

- Signal ID
- Timestamp and ticker
- Model version and rule ID
- RSI settings
- Confirmation stack
- Entry, stop, and target references
- Historical sample size and metrics
- Confidence or research score
- Data version

### Outcome record

Written only after a horizon is fully observable:

- Signal ID
- Evaluation timestamp
- Horizon
- Actual return
- MFE and MAE
- Result label
- Notes

Signals and outcomes are stored separately. Outcomes do not mutate the original signal record.

## No cherry-picking

- Log every eligible signal.
- Log no-signal days separately later if calibration requires them.
- Do not delete failed records.
- Do not change thresholds after seeing an outcome without creating a new model version.

## Model versions

Any change to parameters, features, labels, costs, entry timing, or filtering rules requires a new model version.
