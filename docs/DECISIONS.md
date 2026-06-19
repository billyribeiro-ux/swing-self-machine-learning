# Decision Log

## 2026-06-19 — Build one complete scanner first

Decision: Begin with daily swing trading rather than attempting scalping, day trading, swing trading, portfolio, options, and attribution simultaneously.

Reason: A narrow end-to-end loop is easier to validate, debug, and perfect. The architecture can then be reused.

## 2026-06-19 — Python as the Version 1 language

Decision: Use Python with NumPy, pandas, scikit-learn, Optuna, and related research tooling.

Reason: Python provides a mature ecosystem for time-series research, ML, optimization, reporting, and later NLP.

## 2026-06-19 — RSI is a learnable structure

Decision: Do not hardcode RSI(14), 70/30 as the signal. Search lengths, regions, slopes, reclaims, contexts, and confirmation features. Keep the standard setting as a control and crowd-behavior hypothesis.

## 2026-06-19 — No options in Version 1

Decision: Exclude all options-derived inputs until the daily stock/ETF research loop works honestly end to end.

## 2026-06-19 — Next-open default entry

Decision: A signal calculated from a completed daily bar enters no earlier than the next session open.

Reason: This prevents impossible same-close fills and look-ahead execution.

## 2026-06-19 — Separate immutable forward signals and outcomes

Decision: Store forward signal records separately from later outcome records.

Reason: This preserves what the engine actually knew at signal time and prevents retrospective rewriting.
