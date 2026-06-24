# Changelog

## Unreleased

- Added Linear-Family Path-Head Retirement V1: logistic-family artifacts now keep the primary classifier, target-before-stop head, and expected-return regressor active while marking MFE and MAE heads `RETIRED_UNSUITABLE_ESTIMATOR` with explicit retirement metadata and no Tweedie MFE/MAE estimator fitting.
- Added mandatory required-path-head-active gates, scanner rejection reasons, scanner identity metadata, model-audit fields, promotion blockers, final-holdout enrollment blockers, and dashboard fields for retired path-head capability state.
- Added regression coverage proving retired logistic MFE/MAE heads are not fitted, remain scanner non-actionable, block promotion/final-holdout enrollment, and leave ExtraTrees/HistGradientBoosting path heads active.
- Added Domain-Preserving MFE and MAE Magnitude Modeling V1: MFE and MAE now train on nonnegative internal magnitudes, linear-family magnitude heads use Tweedie regression with a log link, HistGradientBoosting magnitude heads use Poisson loss, ExtraTrees trains on nonnegative magnitudes, and naive controls map nonnegative summaries back to canonical signed outputs.
- Added MFE/MAE domain metadata, estimator hashes, prediction mapping metadata, domain-integrity gates, scanner domain rejection reasons, scanner identity hashes for path-domain metadata, model-audit export fields, and promotion/final-holdout enrollment blockers for missing domain metadata.
- Added regression coverage for unchanged MFE/MAE labels, nonnegative magnitude targets, nonnegative magnitude predictions across current families, no clipping in prediction mapping, canonical MFE/MAE sign outputs, scanner rejection of missing/invalid domain metadata, and legacy unconstrained artifact readability.
- Added target-specific train-only feature screening for expected-return, MFE, and MAE regression heads, including path-head feature manifests, train-only mutual-information regression audits, scanner path-manifest identity, model-audit exports, and dashboard review tabs.
- Added regression coverage for path-head target isolation, full eligible-universe scoring before the cap, train-only filtering/imputation/correlation pruning, deterministic column-order behavior, scanner missing-feature rejection, scanner identity changes from path manifests, and legacy artifact promotion blocking.
- Added Prospective Final-Holdout Sample Governance V1: frozen run-level sample policy `prospective_final_holdout_sample_v1`, canonical sufficiency/provenance/integrity gates, non-promotable early diagnostics, diagnostic-only evaluation, status progress counts, promotion checks for sample gates, and regression coverage for threshold boundaries and bypass prevention.
- Added Prospective Final Holdout and Shadow Paper Forward Validation V1: final-holdout run/model registry tables, strict no-backfill enforcement with ingestion provenance, `SHADOW_FINAL_HOLDOUT` event lifecycle, final-holdout init/update/status/evaluate CLI commands, promotion evidence checks, and a dashboard section labeled as prospective shadow validation rather than a live recommendation.
- Added an explicit final-holdout promotion guard: new discovery artifacts persist `DEVELOPMENT_HOLDOUT`, canonical gates require `FINAL_HOLDOUT`, missing holdout-status metadata blocks eligibility, and manual promotion refuses non-final holdout models before mutating registry state.
- Added Target-Before-Stop Calibration Governance V1: target-before-stop heads now evaluate identity, sigmoid, and isotonic calibrators on chronological calibration-only folds and select with a precommitted one-standard-error rule before refitting the chosen calibrator on the full calibration slice.
- Persisted target-before-stop calibration governance metadata, calibration/audit artifact paths, method-comparison and fold diagnostics, plateau/step-support summaries, calibration manifest hashes, raw/calibrated probability audit exports, and development-holdout diagnostic labels.
- Updated scanner target-before-stop handling to use the frozen head-specific calibrator, reject new-schema artifacts missing calibration governance metadata, and include calibration method/manifest hashes in scanner cache identity.
- Added model-audit exports and dashboard review tabs for target-before-stop calibration method comparison, chronological fold metrics, step support, calibration-only threshold utility, and candidate-level calibration identity.
- Added regression coverage for chronological calibration-fold isolation, one-standard-error method selection, identity/sigmoid/isotonic probability contracts, holdout exclusion from selection, frozen scanner calibrator use, scanner identity changes from calibration metadata, missing-governance rejection, legacy readability, and audit exports.
- Added target-specific train-only feature screening for the target-before-stop head, including per-head feature manifests, screen audit metadata and hashes, scanner feature-manifest identity, model-audit exports, and dashboard review tabs.
- Added regression coverage for target-specific label use, full eligible-universe scoring before the feature cap, train-only missingness/variance/imputation/correlation pruning, deterministic column-order behavior, scanner missing-feature rejection, and legacy artifact readability.
- Documented target-specific screening requirements across model validation, governance, autonomous discovery, feature registry, and scanner specifications.
- Corrected temporal-fold stability gate evidence semantics: new artifacts now persist a separate temporal-fold evidence-availability gate, fold evidence details, and a threshold gate that becomes `NOT_APPLICABLE` when evidence is unavailable instead of passing missing evidence.
- Corrected canonical quality-gate evidence semantics for profit factor and concentration gates: positive-infinity profit factor now passes minimum thresholds when selected returns have gains and no losses, unavailable profit factor is represented explicitly instead of as infinity, concentration failure reasons now match status/threshold evidence, and dashboard/model-audit exports distinguish `Infinity` from `NOT_AVAILABLE`.
- Implemented `prediction_ood_governance_v2`: deprecated the old zero-exceedance OOD promotion rule for new artifacts, added per-head calibration-derived OOD rate/severity gates, hard prediction-integrity gates, training-only OOD bounds, scanner OOD warnings/rejections, OOD-aware scanner identity metadata, and model-audit export fields.
- Added regression coverage for Wilson OOD limits, head-to-bound mapping, decimal-return contracts, MFE/MAE sign contracts, training-only OOD bounds, live scanner OOD warnings/rejections, legacy OOD promotion blocking, and scanner identity changes from OOD metadata.
- Created one fresh local model generation under V2 governance (`2026-06-21T04:34:49.525939+00:00`) and a review-only scanner snapshot (`6e4ce9ccada34a0962d2bc20`); no model was promoted and no paper-forward update was run.
- Configured and persisted the autonomous candidate-selection policy, including expected-return, target-before-stop, liquidity, per-date, global top-N, and selected-rate controls.
- Changed live scanner actionability to require persisted canonical gate eligibility in addition to `CHAMPION` or `CHALLENGER` registry state.
- Date-batched portfolio candidate replay so same-date predictions are processed as one chronological decision set before daily-equity drawdown is calculated.
- Added latest-generation Model Registry export buttons for model summary and full canonical gate audits.
- Aligned scanner selection and portfolio replay with one canonical policy evaluator and deterministic candidate ordering helper.
- Hardened autonomous model evaluation: separated prediction, selected-candidate, and portfolio holdout diagnostics; replaced row-sequence drawdown gating with portfolio daily-equity drawdown; added canonical persisted gate results, model-audit CLI exports, prediction OOD audit fields, and Model Registry gate drilldowns.
- Compact the Model Registry dashboard table so default columns fit the screen while full IDs, hashes, artifacts, metrics, calibration values, and gates remain available in a selected-model details panel.
- Tightened scanner dashboard lifecycle evidence display: direct AppTest execution now runs every primary scanner section, Candidate Attribution displays recent price context, parsed historical analogs, and model/snapshot details, and Portfolio Backtests renders equity, drawdown, trade ledger, candidate audit, and return breakdowns from actionable scanner snapshots.
- Completed the remaining autonomous scanner audit gaps: added a formal model plugin registry, temporal-fold and exceptional-period quality gates, expanded drift checks for relationship/regime, realized-performance, and calibration shifts, target-before-stop outcomes in analog payloads, portfolio candidate-audit rows, and symbol-level return output.
- Changed scanner candidate fallback so `--include-challengers` uses only the newest candidate generation for the active feature manifest when no champion exists, preventing stale artifacts from mixing into current scanner evidence.
- Added explicit `scan --update-data` and `scan --universe` controls so universe updates can be part of the scanner workflow without making external provider calls on ordinary scans.
- Verified the latest local scanner snapshot `9ff465a229a0d4cd9e4e6b36` contains 50 review rows, 25 bullish and 25 bearish, 0 unknown attribution categories, and target-before-stop analog outcomes in every row.
- Completed the autonomous scanner evidence pass against the current feature manifest: every generated feature column is mapped to a registry family, relationship mutual-information and expanding unsupervised regime features are generated, model discovery uses bounded mutual-information screening, scanner models are filtered by current feature-manifest hash, and scanner attribution no longer emits an `unknown` category.
- Added separate target-before-stop probability modeling and scanner output, persisted compact historical analogs and signal close context in scanner snapshots, and verified the latest scanner artifact contains 25 bullish and 25 bearish review rows.
- Expanded paper-forward lifecycle events with frozen stop/target policy prices after next-open paper fill, while preserving append-only/idempotent event insertion.
- Expanded portfolio scanner backtesting with daily equity, exposure, yearly/sector/regime/model-version return tables, trailing-stop support, and corrected open-position capacity release after prior exits.
- Added deterministic daily-cycle JSON report output under ignored `reports/` and verified same-date reruns return `already_completed`.
- Added the Self-Learning Swing Trading Engine vertical slice with configurable universe, raw-data manifests, autonomous feature registry, bullish/bearish labels, chronological model discovery, model registry, scanner snapshots, attribution, portfolio scanner backtesting, append-only paper-forward events, and daily-cycle orchestration.
- Added primary Streamlit dashboard sections for Data and Universe, Discovery Lab, Live Scanner, Candidate Attribution, Portfolio Backtests, Paper Forward Test, Model Registry, and Baselines and Legacy RSI.
- Added CLI commands for `universe-update`, `build-features`, `discover-models`, `model-registry`, `promote-model`, `scan`, `forward-update`, and `daily-cycle`.
- Added `configs/universe/core.yaml` seed universe for large stocks, broad ETFs, sector ETFs, inverse ETFs, and leveraged ETFs.
- Added scikit-learn, joblib, and pyarrow dependencies for local model discovery and parquet artifacts.
- Added autonomous-engine regression tests for backward-looking features, label isolation, purged splits, registry immutability, scanner idempotency, scanner-candidate persistence, append-only forward events, and next-open portfolio entries.
- Added a naive historical base-rate classifier as an explicit model-discovery baseline.
- Added holdout permutation-importance and feature-stability diagnostics to registered model metrics.
- Added drift reporting for feature, relationship/regime, prediction, realized-performance, and calibration distributions; drift can alert and train challengers later, but it does not mutate or promote models.
- Completed the paper-forward vertical slice from latest scanner events through pending entries, next-session paper fills, position marks, and time exits with idempotent append-only events.
- Fixed `scripts/run_daily_cycle.sh` executable permissions and verified the wrapper returns idempotent daily-cycle status.
- Fixed walk-forward split planning so automatically calculated test folds reserve the configured gap before sizing test windows.
- Added a canonical split-plan object shared by dashboard preflight validation and actual walk-forward execution.
- Added dashboard split-plan details for requested dates, effective trading sessions, available sessions, initial training sessions, sessions per test fold, gap, folds, total required sessions, and validity status.
- Added regression tests for the confirmed 2,514-session, 5-fold, 10-gap AAPL configuration and for preview/execution split-plan identity.

## 0.1.2-dashboard-v0.2 — 2026-06-19

- Replaced Streamlit filename-derived multipage navigation with explicit `st.navigation` / `st.Page` registration.
- Moved active page renderers to `dashboard/sections/` and removed auto-discovered `dashboard/pages/*.py` source files.
- Added ticker normalization so filename input such as `AAPL.csv` becomes provider symbol `AAPL` and path/traversal input is rejected.
- Split Data and Audit into separate selected-window and full-raw-file audit scopes.
- Added pure dataframe structural auditing through `structural_audit_frame`.
- Added readable dashboard display formatting for dates, prices, percentages, volume, and table column names.
- Reworked Data and Audit download controls into explicit update-existing and custom-download workflows.
- Added mtime-keyed local CSV read caching and cache invalidation after successful dataset updates.
- Added dashboard error handling with concise UI messages and ignored local logs for unexpected exceptions.
- Added walk-forward configuration prevalidation in the application service wrapper.
- Added tests for navigation order, ticker normalization, selected-window audit behavior, formatting, cache invalidation, AppTest interactions, and no-network dashboard startup.
- Added `watchdog` to the optional `dashboard` dependency group so local Streamlit runs can use filesystem event watching and avoid the performance hint.
- Disabled Streamlit's automatic file watcher in `scripts/run_dashboard.sh` to prevent browser reload loops while local ignored artifacts change during dashboard use.

## 0.1.2 — 2026-06-19

- Added local Streamlit research dashboard scaffold with overview, data audit, RSI explorer, research/backtest, and walk-forward pages.
- Added shared application services for project status, dataset discovery, structural audits, research runs, report naming, RSI explorer data, and walk-forward aggregation.
- Added no-overwrite research report saving with collision-resistant run IDs.
- Added `dashboard` optional dependency group and `scripts/run_dashboard.sh`.
- Updated CLI download and research commands to reuse application services.
- Added tests for dashboard-support services, import safety, report overwrite prevention, and test-only walk-forward aggregation.
- Documented the dashboard scope, temporary Streamlit boundary, and launch command.
- Hardened Dashboard V0.1 navigation to expose exactly five user-facing sections without a duplicate Overview page.
- Changed dashboard/CLI data downloads from overwrite saves to atomic merge updates that preserve existing ticker history.
- Added walk-forward boundary regression tests and form interaction smoke tests for RSI Explorer, research submission, candidate selection, and walk-forward submission.

## 0.1.1 — 2026-06-19

- Selected FMP as the initial primary daily-data provider.
- Added stable FMP end-of-day OHLCV adapter with header authentication.
- Added secure `.env` loading and a hidden-input Mac configuration script.
- Added `doctor`, `fmp-check`, and provider-selectable `download` commands.
- Added mocked FMP response, authentication, date, schema, and secret-exposure tests.
- Kept yfinance isolated as an optional fallback/comparison source.
- Updated Mac setup, milestones, Codex assignment, decisions, and provider documentation.

## 0.1.0 — 2026-06-19

- Created the canonical Version 1 repository.
- Locked scope to daily swing trading and RSI self-discovery.
- Added OHLCV ingestion and validation.
- Added exact Wilder RSI, trailing price features, and isolated forward labels.
- Added next-open fixed-horizon backtesting and metrics.
- Added grid-search and expanding walk-forward scaffolding.
- Added latest-bar scanner and append-only forward signal/outcome records.
- Added deterministic synthetic demo data and automated tests.
