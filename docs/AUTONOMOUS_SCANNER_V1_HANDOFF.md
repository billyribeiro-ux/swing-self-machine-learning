# Autonomous Scanner V1 Handoff

Generated: 2026-06-20 America/New_York

## Repository State

- Branch: `feat/autonomous-swing-scanner-v1`
- Existing scanner commits:
  - `3880c73` — `feat: add autonomous swing scanner vertical slice`
  - `ff244b1` — `docs: add autonomous scanner handoff`
  - `b5b985a` — `feat: complete scanner diagnostics and forward lifecycle`
  - `00717b7` — `docs: finalize autonomous scanner handoff`
  - `6e20ea3` — `feat: harden autonomous scanner evidence pipeline`
- This document describes the verified state after the current completion pass. The final local completion commit hash is reported in the Codex conversation after the commit is created.
- Remote push: not pushed.
- Secrets: `.env` was not opened, printed, staged, committed, or copied.
- Generated artifacts: raw data, feature parquet, model artifacts, scanner outputs, SQLite state, reports, logs, caches, and Streamlit local files are ignored.

## Architecture

The visible product is now **Self-Learning Swing Trading Engine** with the subtitle **Autonomous Market Discovery, Attribution, Scanner, Backtester, and Paper Forward Tester**.

The implementation preserves the existing `swing_rsi` package and adds the autonomous engine under `src/swing_rsi/engine/`. RSI remains implemented and tested, but it is one feature family and a legacy/baseline view, not the scanner strategy. Streamlit remains a local presentation layer and calls Python application services directly.

Core flow:

1. `configs/universe/core.yaml` defines enabled symbols, roles, sectors, benchmarks, and inverse/leveraged relationships.
2. `swing_rsi.application.engine_service.update_universe_data` updates OHLCV through the existing secure FMP provider abstraction.
3. `swing_rsi.engine.manifest` writes per-symbol raw-data provenance manifests.
4. `swing_rsi.engine.features.build_feature_panel` builds synchronized as-of features.
5. `swing_rsi.engine.labels.build_label_panel` builds physically separated `label_` outcome columns.
6. `swing_rsi.engine.splits.chronological_train_calibration_holdout_split` creates chronological train/calibration/holdout slices and purges overlapping label horizons.
7. `swing_rsi.engine.models.discover_models` trains bounded candidate families, applies gates, and writes immutable artifacts.
8. `swing_rsi.engine.registry` persists model metadata and explicit promotions in SQLite.
9. `swing_rsi.engine.scanner.run_scanner` creates immutable bullish and bearish scanner snapshots.
10. `swing_rsi.engine.attribution.explain_candidate` computes model-contribution groups, supporting evidence, relationship evidence, residual/unexplained share, and historical analogs.
11. `swing_rsi.engine.portfolio.backtest_scanner_candidates` backtests scanner outputs with next-open entries, long/short returns, costs, slippage, stops/targets/trailing stops, portfolio limits, daily equity, drawdown, exposure, and return breakdowns.
12. `swing_rsi.engine.forward` appends paper-forward events, fills pending entries at next completed session open, freezes stop/target prices, marks positions, and exits from target/stop/ambiguity/time policies.
13. `swing_rsi.application.engine_service.run_daily_cycle` coordinates an idempotent local daily cycle and writes an ignored JSON daily report.

## Modules Added

- `src/swing_rsi/engine/universe.py`: YAML/CSV universe parsing, symbol normalization, metadata, snapshot IDs.
- `src/swing_rsi/engine/manifest.py`: raw-file hashes, stale/missing-data status, retrieval manifests.
- `src/swing_rsi/engine/storage.py`: SQLite schema for models, scanner snapshots, scanner candidates, forward events, and daily cycles.
- `src/swing_rsi/engine/features.py`: declarative feature registry and feature panel builder.
- `src/swing_rsi/engine/labels.py`: bullish/bearish multi-horizon label engine.
- `src/swing_rsi/engine/splits.py`: chronological train/calibration/holdout split with label purging.
- `src/swing_rsi/engine/models.py`: formal model plugin registry, base-rate, logistic regression, HistGradientBoosting, ExtraTrees, expected-return/MFE/MAE regressors, target-before-stop classifier, calibration, feature screening, temporal-fold and exceptional-period gates, artifact writing.
- `src/swing_rsi/engine/drift.py`: feature-distribution, relationship/regime, prediction-distribution, realized-performance, and calibration drift metrics.
- `src/swing_rsi/engine/registry.py`: immutable model registration and explicit promotion.
- `src/swing_rsi/engine/scanner.py`: latest common-session scanner snapshot persistence and candidate status gating.
- `src/swing_rsi/engine/attribution.py`: local perturbation contribution shares, evidence, relationships, and analogs.
- `src/swing_rsi/engine/portfolio.py`: portfolio-level scanner-output backtester with rejected/skipped candidate audit and symbol-level return output.
- `src/swing_rsi/engine/forward.py`: append-only paper-forward events, next-session fills, stop/target freezes, marks, exits, and position reconstruction.
- `src/swing_rsi/application/engine_service.py`: shared CLI/dashboard orchestration service, including current feature-manifest filtering and newest-generation candidate fallback for review-mode scans.

## Universe

Configured seed universe: 35 enabled symbols.

- Stocks: AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA, AMD.
- Broad ETFs: SPY, QQQ, IWM, DIA.
- Sector ETFs: XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLB, XLU, XLRE, XLC.
- Inverse/leveraged ETFs: SH, SDS, SPXU, UPRO, QID, SQQQ, TQQQ, RWM, TZA, TNA, SOXS, SOXL.

Universe membership is configurable in `configs/universe/core.yaml`.

## Latest Feature Panel

Verified real local feature parquet:

- File: `6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet`
- Feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- Feature rows: 89,973
- Feature columns: 534
- Symbols represented: 35
- Feature date range: 2006-08-03 through 2026-06-18

Feature-family counts for numeric columns:

- `rsi_family`: 294
- `relationship_graph`: 60
- `trend_structure`: 32
- `returns_momentum`: 29
- `technical_primitives`: 29
- `market_relative`: 20
- `volatility_range`: 16
- `inverse_leveraged`: 12
- `volume_participation`: 11
- `candle_geometry`: 8
- `sector_relative`: 8
- `breadth`: 6
- `regime`: 3

All generated numeric feature columns are mapped to a known family. Scanner attribution retains `residual/unexplained` as an explicit bucket, not as an accidental missing family.

## Labels

Implemented horizons:

- 3 sessions
- 5 sessions
- 10 sessions
- 20 sessions
- 40 sessions

For each symbol/date/horizon, labels include:

- next-open-to-horizon-close bullish and bearish returns;
- positive-return flags;
- MFE and MAE;
- target-before-stop and stop-before-target outcomes;
- time-to-target and time-to-stop;
- continuation and reversal flags;
- return rank versus same-date universe;
- risk-adjusted utility;
- label end date for purge logic.

All future-derived columns are prefixed with `label_`.

## Models and Governance

Implemented model families:

- naive historical base-rate classifier;
- logistic regression classifier;
- HistGradientBoosting classifier/regressor;
- ExtraTrees classifier/regressor;
- Ridge-style linear regression for linear-family expected return, MFE, and MAE heads.

Each accepted artifact stores train-only imputers/scalers, selected feature set, model bundle, calibration, feature-family map, training matrix, and training labels needed for attribution and analogs.

Quality gates include:

- minimum training samples;
- minimum unseen holdout observations;
- positive expected value after costs;
- holdout Brier score;
- profit factor;
- maximum drawdown;
- finite lower confidence bound;
- feature-stability cap;
- symbol concentration cap;
- sector concentration cap;
- transaction-cost sensitivity;
- prediction-turnover cap;
- temporal-fold stability;
- exceptional-period concentration;
- comparison-control availability.

Latest model registry counts:

- `CANDIDATE`: 38
- `REJECTED`: 12
- `CHALLENGER`: 0
- `CHAMPION`: 0

Latest discovery run:

- Created at: 2026-06-20T04:38:24.028225+00:00
- Models registered: 8
- Latest model IDs: `2bfd1ba248c6f489efb31664`, `342cf8a2d21a4bde57e65137`, `45abf4961fdd454ac47b3f2f`, `774634752b24e4b914e59f2e`, `81eb0d2483c8579fab58d9ef`, `d3e74e24f0dd2cae717f2107`, `fbb4a81b062858abf0cf0fcc`, `fed5b8e40985892722bfa661`
- Latest run states: 8 `CANDIDATE`
- Latest metrics include model plugin metadata, temporal-fold positive fraction, and exceptional-period concentration.
- Latest gates include temporal-fold stability and exceptional-period concentration.

No model passed every gate, so no champion was promoted and no model was silently deployed.

## Split and Purge Methodology

`chronological_train_calibration_holdout_split` sorts by date and creates train, calibration, and holdout slices. Training and calibration rows whose `label_end_date_{horizon}` overlaps the next slice are purged. Model preprocessing and probability calibration are fit only on their intended chronological slices.

Historical walk-forward validation remains separate legacy research tooling. Paper-forward testing is live append-only testing of frozen model versions.

## Latest Scanner Results

Latest verified scanner snapshot:

- Scan ID: `9ff465a229a0d4cd9e4e6b36`
- As-of date: 2026-06-18
- Rows: 50
- Bullish rows: 25
- Bearish rows: 25
- Candidate status: 50 `REJECTED`
- Rejection reason: `model_not_promoted_or_quality_gates_failed`
- Model states: 50 `CANDIDATE`
- Model IDs used: latest 8-model generation listed above.
- Unknown attribution categories: 0
- Rows with residual/unexplained attribution: 45
- Historical analog records present: 50 rows
- Rows with target-before-stop outcomes in analog payloads: 50
- Signal close context present: yes
- CSV: `artifacts/scanner/9ff465a229a0d4cd9e4e6b36_scanner.csv`
- Parquet: `artifacts/scanner/9ff465a229a0d4cd9e4e6b36_scanner.parquet`

The scanner uses the latest common completed session across enabled local universe symbols, filters model artifacts to the current feature-manifest hash, and in review mode loads only the newest candidate/challenger generation for that manifest.

## Attribution Example

Sample latest scanner row:

- Ticker: SOXL
- Direction: Bearish
- Horizon: 10
- Calibrated probability: 55.10%
- Expected return: 29.09%
- Expected MFE: 85.65%
- Expected MAE: -35.74%
- Target-before-stop probability: 43.64%
- Model state: `CANDIDATE`
- Candidate status: `REJECTED`

Model contribution share:

- returns/momentum: 57.0%
- volatility/range: 18.9%
- trend/structure: 14.1%
- residual/unexplained: 10.0%

The relationship evidence showed stable broad-market/inverse ETF correlations and several inverse/leveraged ETF divergences. These are model evidence and relationship observations, not causal claims.

## Analog Example

The SOXL bearish scanner row persisted five historical analog records. The nearest analog in the latest artifact was:

- Date: 2017-11-06
- Symbol: SOXL
- Distance: 75.93
- Bear 10-session forward return: -1.10%
- Bear MFE: 9.50%
- Bear MAE: -1.63%
- Bear target-before-stop: 1.0

Analogs are drawn from the model bundle's training matrix and labels using train-fitted scaling, and future/current rows are excluded from the historical distance set.

## Portfolio Backtester

Implemented behavior:

- signal after close, entry at next session open;
- bullish and bearish candidates;
- configurable horizon, target, stop, trailing stop, costs, and slippage;
- max concurrent positions;
- max position per symbol;
- sector concentration limit;
- gross and net exposure limits;
- equal weight or volatility-adjusted sizing;
- conservative same-bar target/stop ambiguity handling;
- complete trade ledger;
- daily equity, daily drawdown, exposure;
- yearly, regime, sector, symbol, and model-version return breakdowns;
- candidate audit output retaining rejected and skipped scanner rows with reasons.

Automated tests verify next-open entries, short returns, daily equity columns, yearly/sector outputs, and release of same-symbol capacity after a prior position exits.

Latest real scanner snapshot had no actionable paper candidates because every model remains `CANDIDATE`; therefore the latest governance-correct real portfolio backtest has zero trades unless a model is explicitly promoted after passing gates.

Manual latest-snapshot portfolio evidence:

- Scanner rows: 50
- Trades: 0
- Candidate audit rows: 50
- Audit reason: 50 `model_not_promoted_or_quality_gates_failed`
- Symbol return rows: 0 because no trade was eligible.

## Paper Forward Tester

SQLite forward events after the latest pass:

- Total forward events: 285
- Latest forward update inserted: 50 rejected-signal events for scan `9ff465a229a0d4cd9e4e6b36`.
- Immediate rerun inserted: 0 new events.
- Latest snapshot event types: 50 `SIGNAL_REJECTED`.

Implemented event behavior:

- `SIGNAL_REJECTED` preserves failed-gate scanner rows.
- `SIGNAL_CREATED` and `ENTRY_PENDING` are created only for actionable paper candidates.
- `ENTRY_FILLED` uses the next completed session open.
- `TARGET_UPDATED` and `STOP_UPDATED` freeze policy prices after entry fill.
- `POSITION_MARKED` stores mark return, MFE, and MAE.
- `EXIT_FILLED` records target, stop, conservative same-bar ambiguity, or time exits.
- Existing event rows are never updated.
- Current position state is reconstructed from the append-only event stream.

There are no champion-approved pending entries in the current real state because no model passed every quality gate.

## Daily Cycle

Verified command:

```bash
python -m swing_rsi.cli daily-cycle --include-challengers
```

Latest completed cycle:

- Market date: 2026-06-20
- Status: `completed`
- Feature rows: 89,973
- Modeling rows: 89,973
- Scanner rows: 50
- Scan ID: `a905e44c801fbe7f58b80ddb`
- Drift alerts: 0
- Forward events created during cycle: 0
- Daily report: `reports/daily_cycle_2026-06-20.json`

Immediate rerun returned:

- Status: `already_completed`
- Same market date: 2026-06-20
- Same stored daily-cycle scan ID and report path.

The latest manual scanner/forward evidence was generated after the daily-cycle record for that same market date. The daily-cycle idempotency guard correctly did not overwrite or duplicate the completed 2026-06-20 cycle.

The lock file under `state/daily_cycle.lock` prevents concurrent cycles.

## Database Schema

SQLite path: `state/engine.sqlite3` (ignored by Git).

Tables:

- `models`
- `scanner_snapshots`
- `scanner_candidates`
- `forward_events`
- `daily_cycles`

Current local counts:

- models: 50
- scanner_snapshots: 6
- scanner_candidates: 300
- forward_events: 285
- daily_cycles: 2

Generated SQLite state is not committed.

## Dashboard

Primary sections:

1. Overview
2. Data and Universe
3. Discovery Lab
4. Live Scanner
5. Candidate Attribution
6. Portfolio Backtests
7. Paper Forward Test
8. Model Registry
9. Baselines and Legacy RSI

Legacy RSI tools remain under Baselines and Legacy RSI.

Launch command:

```bash
./scripts/run_dashboard.sh
```

## CLI Commands

```bash
python -m swing_rsi.cli universe-update
python -m swing_rsi.cli build-features
python -m swing_rsi.cli discover-models
python -m swing_rsi.cli model-registry
python -m swing_rsi.cli promote-model
python -m swing_rsi.cli scan
python -m swing_rsi.cli scan --update-data --include-challengers
python -m swing_rsi.cli forward-update
python -m swing_rsi.cli daily-cycle
```

Daily wrapper:

```bash
./scripts/run_daily_cycle.sh --include-challengers
```

## Verification Results

Automated tests:

- Command: `.venv/bin/pytest`
- Result: 79 collected, 79 passed, 0 failed, 0 skipped.
- Warnings: 161. They are pandas fragmentation warnings in feature construction plus one joblib CPU-count warning in the sandbox.

Quality checks:

- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: 86 files already formatted.
- `.venv/bin/mypy src`: success, no issues in 50 source files.

Focused autonomous tests:

- Command: `.venv/bin/pytest tests/test_autonomous_engine.py tests/test_application_services.py`
- Result: 47 collected, 47 passed, 161 warnings.

CLI smoke checks:

- `python -m swing_rsi.cli doctor`: succeeded; reported FMP key configured yes/no without printing the key.
- `python -m swing_rsi.cli model-registry`: succeeded; current candidates listed.
- `python -m swing_rsi.cli scan --help`: succeeded; exposes `--universe`, `--update-data`, and `--include-challengers`.
- `python -m swing_rsi.cli scan --include-challengers`: succeeded; returned existing idempotent scan `9ff465a229a0d4cd9e4e6b36`.
- `python -m swing_rsi.cli forward-update`: succeeded; latest scanner inserted 50 rejected-signal events, and the immediate idempotent rerun inserted 0 events and left total at 285.

Real local-data pipeline:

- `python -m swing_rsi.cli universe-update --start 2016-06-20`: 35 enabled symbols, 35 updated, 0 errors.
- `python -m swing_rsi.cli build-features`: produced 89,973 feature rows, 89,973 label rows, 89,973 modeling rows.
- `python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80`: registered 8 current-feature candidates, 0 challengers, 0 rejected/experimental in the latest run, no silent promotion.
- `python -m swing_rsi.cli scan --include-challengers`: produced scan `9ff465a229a0d4cd9e4e6b36`, 50 rows, 25 bullish, 25 bearish.
- `python -m swing_rsi.cli forward-update`: inserted 50 events; immediate rerun inserted 0.
- `python -m swing_rsi.cli daily-cycle --include-challengers`: completed once for 2026-06-20 and reran as `already_completed`.

Streamlit smoke:

- Command: `.venv/bin/streamlit run dashboard/app.py --server.headless true --server.port 8774 --browser.gatherUsageStats false`
- Startup: succeeded on port 8774.
- HTTP check: `curl -I http://localhost:8774` returned `HTTP/1.1 200 OK`.
- Shutdown: local process on port 8774 was stopped; subsequent port check returned no process.

Dashboard AppTest:

- Included in `.venv/bin/pytest` via `tests/test_dashboard_interactions.py`.
- Six dashboard interaction tests passed.

## Security Audit

PASS:

- `.env` is ignored and was not opened or printed.
- `.venv` is ignored.
- `data/raw/*`, `data/features/*`, `data/manifests/*`, `data/universes/*`, `artifacts/*`, `state/*`, and `reports/*` are ignored except `.gitkeep` files.
- API keys and authenticated URLs are not printed by CLI/dashboard paths used here.
- Automated tests do not call FMP.
- Dashboard imports do not make FMP requests.
- Generated raw data, model artifacts, scanner outputs, SQLite state, reports, logs, caches, and Streamlit local files are not committed.

## Leakage Audit

PASS:

- Features are trailing or same-date as-of values.
- Future-row mutation tests confirm prior features do not change.
- Cross-sectional ranks and breadth use same-date data only.
- Labels are prefixed with `label_` and physically separated from features.
- `reject_label_columns` prevents label columns entering model matrices.
- Chronological splits purge overlapping label windows before calibration/holdout.
- Calibration is separate from training and holdout.
- Scanner rows use latest as-of features and no labels.
- Scanner uses the latest common completed local session.
- Close-known signals do not enter at the same close; portfolio and forward paths use next-session/next-completed-session open semantics.
- Rejected candidates and failed signals are retained with exclusion reasons.
- Forward events are append-only and idempotent.

## Known Limitations

- No model passed every quality gate, so there is no champion and no champion-approved paper pending entry.
- Scanner output using `--include-challengers` is review-only when models are still `CANDIDATE`.
- Real-data portfolio backtest has zero actionable trades until a model passes gates and is explicitly promoted.
- Feature construction is correct but currently emits pandas fragmentation performance warnings; this is a performance/refactor target.
- Regime labels are bounded unsupervised state candidates, not causal bull/bear labels.
- Attribution is perturbation/evidence based and probabilistic; it is not causal proof.
- Drift checks include feature, relationship/regime, prediction, realized-performance, and calibration metric functions. Realized-performance and calibration drift need enough champion/live forward history to become operationally meaningful.
- Historical analog display exists but remains compact in scanner artifacts and dashboard.
- FMP corporate-action semantics, delisted coverage, and point-in-time historical-universe membership remain unaudited.
- Current-universe historical tests may contain survivorship bias.
- No options, NLP, intraday data, brokerage execution, authentication, deployment, FastAPI, SvelteKit, or database server were added.

## User Commands

Open the dashboard:

```bash
./scripts/run_dashboard.sh
```

Run the daily cycle:

```bash
./scripts/run_daily_cycle.sh --include-challengers
```

Run the autonomous scanner pipeline manually:

```bash
python -m swing_rsi.cli universe-update --start 2016-06-20
python -m swing_rsi.cli build-features
python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80
python -m swing_rsi.cli scan --include-challengers
python -m swing_rsi.cli forward-update
```

To update enabled universe symbols as part of scanning, use the explicit update flag:

```bash
python -m swing_rsi.cli scan --update-data --include-challengers
```

## Next Smallest Milestone

Do not add new data domains. The next smallest sensible milestone is to make model-review and promotion stricter and easier to audit: add dashboard gate drilldowns, calibration tables/plots, feature-stability tables, and a manual champion-promotion checklist tied to the existing daily scanner and forward-test state.
