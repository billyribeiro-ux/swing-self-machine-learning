# Decision Log

## 2026-06-20 — Model promotion requires canonical portfolio-aware gates

Decision: Autonomous model promotion is computed only from persisted canonical gate records. Portfolio maximum drawdown must come from chronological daily portfolio equity. Cross-sectional selected-row compounding is retained only as `selected_row_sequence_drawdown` and cannot satisfy the portfolio drawdown gate.

Reason: Same-date panel predictions are not sequential full-capital trades. Using their compounded row sequence produced near--100% drawdowns that were mathematically invalid as portfolio evidence and obscured the real promotion blockers.

## 2026-06-20 — Scanner review mode uses newest candidate generation only

Decision: When no champion exists and scanner review mode is explicitly enabled with `--include-challengers`, load only the newest `CANDIDATE`/`CHALLENGER` generation for the active feature-manifest hash. Keep older model artifacts registered for audit history, but do not mix them into the current scanner run.

Reason: Multiple discovery runs can register immutable candidates against the same feature manifest. Scanner output should represent one coherent frozen model generation, not a blend of stale and current artifacts.

## 2026-06-20 — Discovery models expose a formal plugin interface

Decision: Model discovery now defines explicit `ModelPlugin` records containing classifier and regressor factories plus nonlinear-interaction metadata. Quality gates also include temporal-fold stability and exceptional-period concentration diagnostics.

Reason: The scanner must be able to add or retire model families without hiding preprocessing or ranking behavior. Stability and concentration checks reduce dependence on one exceptional period.

## 2026-06-20 — Drift and portfolio audit evidence are first-class outputs

Decision: Drift reports include relationship/regime, realized-performance, and calibration deterioration metrics when the required inputs are available. Portfolio scanner backtests retain rejected candidate audit rows and symbol-level contribution output.

Reason: Auto-adaptation must be evidence-driven and controlled. Rejected scanner candidates and unexplained drift are part of the research record and must not disappear from review.

## 2026-06-20 — Scanner uses only current feature-manifest model artifacts

Decision: Live scanner and drift checks filter registered models to the latest feature-manifest hash before loading artifacts. Feature-family attribution now maps every generated feature column to a known registry family, with residual/unexplained retained as a model-contribution bucket rather than an accidental unknown category.

Reason: Model artifacts trained against older feature schemas can fail or produce misleading attributions after feature discovery changes. Scanner output must be grounded in the current feature snapshot and must disclose unexplained residual influence without inventing a cause.

## 2026-06-20 — Forward paper events freeze risk policy after next-open fill

Decision: Actionable paper candidates still become next-open pending entries, but after the paper fill the event stream appends frozen `TARGET_UPDATED` and `STOP_UPDATED` events with price levels derived from the signal-time expected MFE/MAE policy. Position exits can then occur from target, stop, conservative same-bar ambiguity, or time exit.

Reason: Forward testing must preserve immutable policy state at the time it becomes knowable. This gives paper-forward records auditable stop/target context without allowing a later model version to rewrite old signals or positions.

## 2026-06-20 — Autonomous scanner models require diagnostics and append-only paper lifecycle

Decision: Include a naive historical base-rate classifier as a required discovery baseline, store bounded permutation-importance and feature-stability diagnostics with model metrics, and run drift checks as review signals rather than self-mutating model changes. Paper-forward updates now advance through next-session paper fills, daily marks, and time exits as append-only events.

Reason: The scanner must learn from observable data without treating any one strategy or model family as privileged. Diagnostics and drift alerts improve review quality, but auto-adaptation remains controlled. Forward testing must preserve exactly what was known and done at the time, so existing events are never rewritten.

## 2026-06-19 — RSI becomes a baseline feature family

Decision: Reframe the product as the Self-Learning Swing Trading Engine. RSI remains implemented and tested, but it is one feature family and legacy/baseline research view rather than the scanner strategy.

Reason: The original system goal is autonomous market discovery and attribution across price, volume, market, sector, breadth, inverse/leveraged ETF, relationship, and regime behavior. Treating RSI as the strategy would overfit the product to one indicator.

## 2026-06-19 — Local autonomous engine uses SQLite state and immutable artifacts

Decision: Store operational model registry, scanner snapshots, scanner candidates, forward events, and daily-cycle status in local SQLite under `state/engine.sqlite3`. Store model and scanner artifacts under `artifacts/`. Keep all generated state ignored by Git.

Reason: The vertical slice needs persistent local state and idempotent orchestration without introducing a service database, deployment infrastructure, authentication, or a separate API.

## 2026-06-19 — Discovery never silently deploys a model

Decision: Discovery registers trained models as candidates/challengers/rejections. Only explicit promotion can create a champion. Scanner inspection may use retained candidates only when requested with `--include-challengers`.

Reason: Auto-adaptation must be controlled. A newly trained model is a challenger, not a silent replacement for the deployed champion.

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

## 2026-06-19 — FMP is the primary Version 1 data provider

Decision: Use Financial Modeling Prep's stable full end-of-day price endpoint for the first real daily OHLCV pipeline. Keep yfinance isolated as an optional fallback and comparison adapter only.

Reason: The user already has FMP access, and one explicit primary provider reduces ambiguity during ingestion, corporate-action, and data-quality auditing. Provider quality, adjustment semantics, delisted coverage, and point-in-time universe handling must still be tested rather than assumed.

## 2026-06-19 — API keys remain local and outside Git

Decision: Read `FMP_API_KEY` from a local `.env` file created by a hidden-input setup script. Never print, hardcode, commit, or place the key in request URLs.

Reason: This keeps credentials separate from research code and repository history while remaining straightforward to configure on a Mac.

## 2026-06-19 — Streamlit for the first local research dashboard

Decision: Build Dashboard V0.1 with Streamlit as a local-only presentation layer over reusable Python application services.

Reason: Streamlit provides the fastest path to inspect data quality, RSI candidates, in-sample research, and walk-forward folds without adding a separate API, JavaScript frontend, database, authentication, or deployment layer. The long-term commercial UI may later be replaced by SvelteKit over a typed FastAPI/OpenAPI boundary.

## 2026-06-19 — Dashboard data updates merge by date

Decision: Treat dashboard and CLI FMP downloads as non-destructive updates. Existing ticker CSVs are loaded, newly downloaded rows replace matching dates, new dates are inserted, the merged OHLCV frame is validated, and the final file is saved atomically.

Reason: A narrow refresh window must not silently truncate broader local history. Destructive replacement remains out of scope for Dashboard V0.1 unless it is later added as an explicit confirmed action.

## 2026-06-19 — Dashboard navigation and audit scopes are explicit

Decision: Dashboard V0.2 uses explicit `st.navigation` / `st.Page` registrations from `dashboard/app.py` and keeps page renderers in `dashboard/sections/`. Streamlit's auto-discovered `dashboard/pages/*.py` page files are not used.

Reason: Filename-derived page labels produced an unprofessional sidebar and exposed `app` as a user-facing page. The dashboard must show exactly the five research sections in the required order.

Decision: Data and Audit displays selected research-window audits separately from full raw-file audits.

Reason: A selected 10-year window must not show older raw-file rows or largest moves as if they belong to the selected window. Full raw history remains visible in its own tab for coverage review.

Decision: Ticker symbols are normalized through one application-level function before provider calls or storage naming.

Reason: A filename such as `AAPL.csv` is not a provider ticker. Normalization prevents accidental filename submission to FMP while preserving valid symbols such as `BRK.B` and `BRK-B`.

## 2026-06-20 — Walk-forward split planning reserves the configured gap

Decision: Automatically sized expanding walk-forward splits calculate test size from `sample_count - gap` before dividing by `n_splits + 1`, and the resulting canonical split plan is shared by dashboard preflight validation and actual execution.

Reason: The previous default calculation sized test folds from all samples and then subtracted the gap, which could reject valid configurations. The split plan must preserve the requested gap, keep chronological non-overlapping test folds, and end the final test fold at the final available sample without silently changing user-selected dates or fold settings.

## 2026-06-20 — Scanner actionability requires persisted gate eligibility

Decision: The autonomous model selection policy is explicitly configured and persisted with each model, and live scanner actionability now requires both promoted registry state and promotion-eligible canonical gate results.

Reason: Candidate rows must not become paper signals merely because a model has a favorable state string. Selection coverage, expected return, target-before-stop probability, liquidity, and date-level candidate caps are model-governance controls and must be evaluated from the same persisted gate results used by promotion.

Decision: Candidate policy checks and deterministic candidate ordering live in one shared selection module.

Reason: Holdout selection, live scanner actionability, scanner caps, and portfolio replay must not drift. The canonical order is composite utility descending, symbol ascending, direction ascending, model ID ascending, and stable candidate identity hash ascending.
