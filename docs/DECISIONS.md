# Decision Log

## 2026-06-25 — Product-class specialist scopes separate inverse and leveraged instruments

Decision: Advance product-class specialist metadata to `product_class_specialist_v2` and replace the mixed non-ordinary target bucket with separate `INVERSE`, `LEVERAGED_LONG`, and `LEVERAGED_INVERSE` scopes. `inverse_etf` rows map to `INVERSE`, `leveraged_long_etf` rows map to `LEVERAGED_LONG`, and `leveraged_inverse_etf` rows map to `LEVERAGED_INVERSE`. `POOLED` and `ORDINARY` remain unchanged. Scope membership continues to derive only from governed universe roles, and full-universe context features remain available before target rows are filtered by scope.

Reason: The product-class evidence diagnosis showed that the combined leveraged/inverse cohort still mixed mechanically different instruments. SOXL/SOXS-related path errors and mixed specialist evidence justify testing narrower target distributions without changing labels, thresholds, quality gates, OOD Governance V2, feature construction, or the frozen operational prospective model.

## 2026-06-25 — Product-class specialist challengers separate target rows from market context

Decision: Add `product_class_specialist_v1` challenger scope metadata with `POOLED`, `ORDINARY`, and `LEVERAGED_INVERSE` scopes derived only from governed universe roles. Specialist discovery filters eligible prediction rows by scope after full-universe feature construction, so market, sector, breadth, relationship, inverse/leveraged, and regime context remain available while ordinary and leveraged/inverse target distributions are no longer pooled indiscriminately. The first specialist generation trains only active nonlinear learned families, with matching naive controls where data is sufficient; logistic-family specialist challengers are excluded because their MFE/MAE path heads are retired.

Reason: Read-only nonlinear diagnostics showed leveraged and inverse ETFs materially affected path-return, MFE, MAE, OOD, calibration, and concentration behavior. Product specialization tests that heterogeneity without touching the frozen pooled operational model, weakening quality gates, changing labels, changing thresholds, or using development evidence as final-holdout proof.

## 2026-06-22 — Path-metric heads use target-specific train-only feature screens

Decision: Expected-return, MFE, and MAE regressors now use independent train-only feature screens keyed to their exact continuous path targets. The screens start from the complete eligible numeric feature universe, exclude labels and prohibited metadata, fit missingness/variance/imputation on training rows only, score surviving features with `mutual_info_regression`, prune correlations in score order, and persist separate manifests under `path_metric_target_specific_feature_screen_v1`.

Reason: The path-metric diagnosis found no label or unit defect, but did find that expected return, MFE, and MAE reused the primary positive-return classifier's feature screen. These regression heads predict different targets, so reusing classifier-selected columns can exclude eligible features before target-specific scoring. This correction changes feature selection only; it does not change labels, ATR normalization, regression estimators, losses, target/stop definitions, quality gates, or OOD Governance V2.

## 2026-06-21 — Prospective final-holdout sample sufficiency is precommitted

Decision: Prospective final-holdout runs now freeze sample governance policy `prospective_final_holdout_sample_v1` at run creation. A model becomes ready for final-holdout evaluation only after 100 matured outcomes, 60 distinct signal dates, 126 completed market sessions, 4 calendar months, 20 positive and 20 negative target-before-stop outcomes, valid provenance for every included prediction, zero backfilled predictions, zero unresolved data-integrity events, and unchanged frozen artifacts/governance hashes. Early diagnostics are non-promotable and require 30 matured outcomes and 20 signal dates.

Reason: The sample requirement must be known before prospective outcomes exist. Freezing the policy into each run prevents post-outcome threshold edits, keeps existing runs immutable when global policy changes, and preserves the distinction between evidence status, performance gates, and manual promotion.

## 2026-06-21 — Final holdout is prospective shadow validation only

Decision: The only valid `FINAL_HOLDOUT` evidence is prospective. A model must be frozen and enrolled with artifact hash, feature manifest, selection policy, target-before-stop calibrator, OOD metadata, universe, scanner identity, execution policy, and baseline market date before final-holdout collection starts. No signal with `as_of_date <= baseline_market_date` may enter the run, and later sessions require local ingestion provenance showing they arrived after run creation. Final-holdout events reuse the append-only paper-forward lifecycle under `SHADOW_FINAL_HOLDOUT` and are not live trade recommendations. Evaluation may mark evidence as `FINAL_HOLDOUT`, but mandatory final-holdout gates still decide pass/fail and `NOT_CONFIGURED` sample thresholds block promotion.

Reason: The historical 2016-2026 holdout is now a development holdout because it has been repeatedly inspected during engineering diagnosis. Creating another historical holdout from that same period would not restore final out-of-sample integrity. Prospective collection preserves chronology: predictions are stored before outcomes exist, frozen model identity is auditable, and promotion remains explicit.

## 2026-06-21 — Promotion requires explicit final-holdout status

Decision: Champion promotion now requires canonical holdout status `FINAL_HOLDOUT`. Discovery artifacts produced from the repeatedly inspected chronological holdout persist `DEVELOPMENT_HOLDOUT`, receive a mandatory `final_holdout_required_for_promotion` gate failure, and cannot become challengers or champions. Missing holdout-status metadata is treated as not final. The manual registry promotion path checks the persisted holdout status before ordinary gate eligibility.

Reason: The current holdout has been repeatedly examined during engineering diagnosis and is no longer a pristine final holdout. Promotion must not depend on development-holdout diagnostics or on legacy artifacts without explicit final-validation provenance.

## 2026-06-21 — Target-before-stop calibrator selection is governed by calibration-only folds

Decision: Target-before-stop heads now use calibration governance schema `tbs_calibration_governance_v1`. Each model family, direction, horizon, and target-before-stop head independently evaluates exactly `identity`, `sigmoid`, and `isotonic` calibrators on forward-chaining chronological folds inside the existing calibration slice. Selection uses mean fold Brier with the precommitted one-standard-error rule and simplicity order `identity < sigmoid < isotonic`. The selected method is then refit on the complete calibration slice only and persisted with fold diagnostics, candidate diagnostics, plateau/step-support records, raw/calibrated probability audit paths, and calibration manifest hashes.

Reason: The calibration diagnosis found no implementation leakage but did find large isotonic plateaus, sparse step support, occasional unsupported extremes, temporal/product-class instability, and weak raw signal. Calibrator choice must therefore be governed by calibration data only instead of assuming isotonic is always appropriate. The repeatedly inspected holdout is now a development holdout and cannot select calibrators, optimize thresholds, promote models, or support final out-of-sample claims.

## 2026-06-21 — Target-before-stop uses its own train-only feature screen

Decision: The target-before-stop classifier now owns a separate train-only feature screen keyed to `label_{direction}_target_before_stop_{horizon}`. The primary positive-return classifier, target-before-stop classifier, expected-return head, MFE head, and MAE head persist separate head feature manifests, with legacy artifacts labeled as shared-screen artifacts when target-specific metadata is absent.

Reason: Positive-return classification and target-before-stop classification are different prediction tasks. Reusing the primary classifier's selected columns for target-before-stop can exclude eligible families before they receive a fair target-specific score. The correction is target-specific screening without changing labels, thresholds, calibration, model families, target/stop multiples, or OOD Governance V2.

## 2026-06-21 — Temporal-fold stability separates evidence availability from threshold comparison

Decision: Temporal-fold stability now persists a mandatory learned-model evidence-availability gate separately from the `temporal_fold_stability_min_050` threshold gate. The existing three chronological fold layout and 0.50 positive-fold threshold remain unchanged. If selected-row evidence is missing, nonfinite, zero-selection, or insufficient to populate all requested folds, the evidence gate fails for learned models and the threshold gate is `NOT_APPLICABLE`; naive zero-selection controls mark both temporal-fold gates `NOT_APPLICABLE` and remain blocked by `not_naive_control`.

Reason: A threshold comparison cannot pass when the metric is unavailable. Separating evidence availability from threshold satisfaction keeps gate status, actual value, comparator, threshold, reason text, promotion eligibility, dashboard display, and model-audit exports internally consistent while preserving legacy artifacts for audit.

## 2026-06-21 — Canonical gate evidence uses explicit profit-factor availability

Decision: Profit-factor quality gates distinguish available, unavailable, and not-applicable evidence before applying the comparator. Selected returns with gains and no losses have profit factor `Infinity` and pass `>= 0.90`. Zero selected rows and all-zero selected returns are unavailable for learned models and fail mandatory profit-factor evidence. Zero-selection naive controls mark profit factor `NOT_APPLICABLE` while remaining promotion-ineligible through the existing naive-control gate. Concentration gates now generate status-aware reasons for pass, fail, and not-applicable evidence.

Reason: Gate status, actual value, comparator, threshold, and reason must not contradict one another. Positive infinity is a valid mathematical profit factor when losses are zero and gains exist; unavailable evidence must not be encoded as infinity.

## 2026-06-21 — Prediction OOD governance uses calibrated rate and severity limits

Decision: Replace the zero-tolerance `prediction_out_of_distribution_absent` promotion rule for new artifacts with governance schema `prediction_ood_governance_v2`. Training `q01` / `q99` remains the reference OOD envelope, but ordinary exceedances are evaluated by per-head OOD rate and severity limits derived from calibration predictions. Integrity defects remain mandatory zero-tolerance failures: nonfinite predictions, probability values outside `[0, 1]`, decimal/percent unit misuse, wrong head-to-bound mapping, non-training OOD bounds, double inverse transformation, MFE predictions below zero, and MAE predictions above zero. Raw predictions are never clipped.

Reason: A robust `q01` / `q99` envelope is a diagnostic reference, not an absolute mathematical domain. Requiring zero exceedances across thousands of predictions makes one normal tail estimate fail an entire model and masks the more important distinction between ordinary tails, severe extrapolation, and implementation defects. Calibration-derived limits keep the rule fixed before holdout evaluation while preserving every exceedance for audit.

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

## 2026-06-22 — MFE and MAE use domain-preserving magnitude models

Decision: Preserve historical MFE and MAE labels unchanged, but train MFE on favorable magnitude and MAE on adverse magnitude under `path_metric_magnitude_domain_v1`. Linear-family path-magnitude heads use Tweedie regression with a log link, HistGradientBoosting uses Poisson loss, ExtraTrees trains directly on nonnegative magnitudes, and naive controls use nonnegative magnitude summaries.

Reason: MFE is physically nonnegative and MAE is physically nonpositive. The previous unconstrained path regressors could emit negative MFE or positive MAE predictions. Domain correctness must be achieved by target representation and estimator choice, not post-hoc clipping.

## 2026-06-24 — Linear-family path MFE/MAE heads are retired

Decision: Logistic-family model artifacts keep the primary positive-return classifier, target-before-stop classifier, and expected-return regressor active, but mark MFE and MAE path heads `RETIRED_UNSUITABLE_ESTIMATOR` under `linear_family_path_head_retirement_v1`. They fit no Tweedie MFE/MAE estimator and fail mandatory required-path-head-active promotion gates. ExtraTrees and HistGradientBoosting path heads remain active under the existing magnitude-domain contract.

Reason: The baseline domain-preserving generation still showed the linear path heads as unsuitable for required MFE/MAE magnitude modeling. Retiring the unsuitable heads is safer than preserving a formally domain-valid but unsuitable estimator, and it keeps scanner actionability, promotion, and prospective final-holdout enrollment aligned with required path-head availability.

## 2026-06-24 — Path heads train in ATR-normalized target units

Decision: Preserve historical expected-return, MFE, and MAE labels unchanged, but train active path heads on internal targets divided by close-known signal-date `atr_pct_14` under `atr_normalized_path_targets_v1`. Expected return uses signed ATR units, MFE uses favorable magnitude ATR units, and MAE uses adverse magnitude ATR units. Predictions are mapped back to canonical decimal returns before scanner output, selection policy, attribution, portfolio replay, and paper-forward testing. Logistic-family MFE/MAE heads remain retired.

Reason: The nonlinear diagnosis found raw-percentage path targets were heterogeneous across ordinary stocks, ETFs, leveraged ETFs, inverse ETFs, regimes, and years. ATR normalization addresses the target-unit heterogeneity directly while preserving label history, target/stop definitions, model families, selection thresholds, and OOD Governance V2 thresholds.
