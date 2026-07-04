# Next Actions

## A. Do Now

- Verify report pack integrity.
- Commit and push the report pack only after validation.
- Do not run more engine updates until a genuinely new completed market session exists.

## B. After Next Completed U.S. Equity Session Is Available Locally

The next expected regular U.S. equity session after `2026-07-02` is `2026-07-06`, because `2026-07-03` was the observed Independence Day market holiday.

Operational:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
.venv/bin/python -m swing_rsi.cli universe-update
.venv/bin/python -m swing_rsi.cli build-features
.venv/bin/python -m swing_rsi.cli final-holdout-update
.venv/bin/python -m swing_rsi.cli final-holdout-status
```

Development:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/python -m swing_rsi.cli universe-update
.venv/bin/python -m swing_rsi.cli build-features
.venv/bin/python -m swing_rsi.cli discover-signals
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-update
.venv/bin/python -m swing_rsi.cli time-exit-diagnostic-status
```

Only run the development `time-exit-diagnostic-update` after a new signal-discovery generation exists for a post-baseline completed session.

## C. Do Not Do

- Do not promote models.
- Do not lower gates.
- Do not lower probability thresholds.
- Do not lower TBS thresholds.
- Do not weaken OOD governance.
- Do not rerun discovery repeatedly without new data.
- Do not touch operational source.
- Do not confuse time-exit diagnostic rows with live signals.

## D. Next Engineering Task

If no bug is found, no engineering change is required before the next completed market session. The correct next action is evidence collection.

