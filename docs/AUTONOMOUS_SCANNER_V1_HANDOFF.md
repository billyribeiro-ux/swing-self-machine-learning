# Autonomous Scanner V1 Handoff

Generated: 2026-06-19 America/New_York

## Repository State

- Branch: `feat/autonomous-swing-scanner-v1`
- Implementation commit: `3880c73` (`feat: add autonomous swing scanner vertical slice`)
- Completion commit: `b5b985a` (`feat: complete scanner diagnostics and forward lifecycle`)
- Remote push: not pushed
- Secrets: `.env` was not opened, printed, staged, committed, or copied.
- Generated artifacts: raw data, feature parquet, model artifacts, scanner outputs, SQLite state, reports, logs, caches, and Streamlit local files are ignored.

## Architecture

The project is now titled **Self-Learning Swing Trading Engine**.

The implementation keeps the existing `swing_rsi` package and adds an autonomous engine under `src/swing_rsi/engine/`. Streamlit remains a local presentation layer and calls application services directly; it does not duplicate feature, label, model, scanner, attribution, portfolio, or forward-testing logic.

Main flow:

1. `configs/universe/core.yaml` defines enabled symbols and metadata.
2. `swing_rsi.application.engine_service.update_universe_data` updates local OHLCV through the existing secure FMP provider adapter.
3. `swing_rsi.engine.manifest` writes per-symbol raw-data provenance manifests.
4. `swing_rsi.engine.features.build_feature_panel` creates synchronized as-of feature rows.
5. `swing_rsi.engine.labels.build_label_panel` creates physically separated future `label_` columns.
6. `swing_rsi.engine.splits.chronological_train_calibration_holdout_split` creates chronological train, calibration, and holdout slices with purged overlapping label windows.
7. `swing_rsi.engine.models.discover_models` trains bounded model families and registers candidates.
8. `swing_rsi.engine.registry` persists immutable model metadata in SQLite.
9. `swing_rsi.engine.scanner.run_scanner` creates immutable bullish and bearish scanner snapshots.
10. `swing_rsi.engine.attribution.explain_candidate` produces feature-family contribution shares, evidence, relationship confirmations/divergences, and analogs.
11. `swing_rsi.engine.portfolio.backtest_scanner_candidates` backtests scanner outputs with next-open entries and portfolio limits.
12. `swing_rsi.engine.forward` appends paper-forward events and reconstructs position state.
13. `swing_rsi.application.engine_service.run_daily_cycle` coordinates a restartable local daily cycle.

## Modules Added

- `src/swing_rsi/engine/universe.py`: YAML/CSV universe parsing, symbol normalization, metadata, snapshot IDs.
- `src/swing_rsi/engine/manifest.py`: raw-file hashes, stale/missing-data status, retrieval manifests.
- `src/swing_rsi/engine/storage.py`: SQLite schema for models, scanner snapshots, scanner candidates, forward events, and daily cycles; includes scanner-candidate primary-key migration.
- `src/swing_rsi/engine/features.py`: declarative feature registry and feature panel builder.
- `src/swing_rsi/engine/labels.py`: bullish/bearish multi-horizon label engine.
- `src/swing_rsi/engine/splits.py`: chronological train/calibration/holdout split with label purging.
- `src/swing_rsi/engine/models.py`: logistic regression, HistGradientBoosting, ExtraTrees, Ridge expected-return/MFE/MAE models, calibration, quality gates, artifact writing.
- `src/swing_rsi/engine/drift.py`: feature-distribution and prediction-distribution drift reporting.
- `src/swing_rsi/engine/registry.py`: immutable model registration and explicit promotion.
- `src/swing_rsi/engine/scanner.py`: latest-session scanner snapshot persistence and candidate status gating.
- `src/swing_rsi/engine/attribution.py`: local perturbation contribution shares, evidence, relationships, analogs.
- `src/swing_rsi/engine/portfolio.py`: portfolio-level scanner-output backtester.
- `src/swing_rsi/engine/forward.py`: append-only paper-forward events, next-session paper fills, daily marks, time exits, and position reconstruction.
- `src/swing_rsi/application/engine_service.py`: shared CLI/dashboard orchestration service.

## Universe

Configured seed universe: 35 enabled symbols.

Initial symbols include:

- Stocks: AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA, AMD.
- Broad ETFs: SPY, QQQ, IWM, DIA.
- Sector ETFs: XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLB, XLU, XLRE, XLC.
- Inverse/leveraged ETFs: SH, SDS, SPXU, UPRO, QID, SQQQ, TQQQ, RWM, TZA, TNA, SOXS, SOXL.

Universe membership is configurable in `configs/universe/core.yaml`.

## Feature Counts

Latest real local run:

- Feature rows: 89,973
- Modeling rows: 89,973
- Feature columns: 472
- Feature manifest hash: `b5679396f3a0ef45f0551a26435c7d78241d36a6bc29eaa03810117cde0ed329`

Registry spec counts:

- breadth: 1
- candle geometry: 4
- regime: 1
- returns/momentum: 20
- RSI family: 98
- technical primitives: 6
- trend/structure: 10
- volatility/range: 3
- volume/participation: 3

Additional generated columns include market-relative, sector-relative, inverse/leveraged ETF, breadth, relationship, and regime features.

## Labels

Implemented horizons:

- 3 sessions
- 5 sessions
- 10 sessions
- 20 sessions
- 40 sessions

For each symbol/date/horizon the label engine creates:

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

## Model Families

Classifier candidates:

- naive historical base-rate classifier;
- logistic regression;
- HistGradientBoosting classifier;
- ExtraTrees classifier.

Regression heads:

- Ridge expected forward return;
- Ridge expected MFE;
- Ridge expected MAE.

Preprocessing and calibration:

- train-only median imputation;
- train-only scaling where used;
- separate chronological calibration slice with isotonic probability calibration;
- no random train/test shuffling.

Diagnostics:

- bounded holdout permutation-importance summaries;
- train-vs-holdout feature-stability summaries;
- drift reports comparing training reference features with the latest as-of feature snapshot.

## Split and Purge Methodology

`chronological_train_calibration_holdout_split` sorts by date and creates train, calibration, and holdout slices. Training and calibration rows whose `label_end_date_{horizon}` overlaps the next slice are purged. This prevents training labels near boundaries from using future validation or holdout prices.

Historical walk-forward validation remains legacy research tooling and is separate from paper forward testing.

## Quality Gates

Current mandatory gates:

- minimum training samples;
- minimum unseen holdout observations;
- positive expected value after costs;
- holdout Brier score <= 0.35;
- profit factor >= 0.90;
- max drawdown better than -50%.

No candidate is promoted automatically. Promotion requires:

```bash
python -m swing_rsi.cli promote-model --model-id <model_id>
```

## Accepted and Rejected Models

Latest local registry state after the final real local acceptance run:

- `CANDIDATE`: 14
- `REJECTED`: 12
- `CHALLENGER`: 0
- `CHAMPION`: 0

No model passed all quality gates, so no champion was promoted. The scanner can inspect candidate outputs with `--include-challengers`, but failed-gate `CANDIDATE` models are not allowed to create actionable paper entries.

## Latest Scanner Results

Latest governance-aware scanner snapshot:

- Scan ID: `8e63cc0bbc6242eb5b38856e`
- As-of date: `2026-06-18`
- Rows: 50
- Bullish rows: 25
- Bearish rows: 25
- Candidate status: 50 `REJECTED`
- Model state: 50 `CANDIDATE`
- Rejection reason: `model_not_promoted_or_quality_gates_failed`

Prior inspection snapshots exist in ignored local artifacts. The current snapshot is the latest governance-correct one.

## Attribution Example

Sample latest candidate:

- Ticker: SOXL
- Direction: Bearish
- Horizon: 10
- Calibrated probability: 0.5689935065
- Expected return: 0.2259736009
- Expected MFE: 0.8242213431
- Expected MAE: -0.3911907876
- Model state: `CANDIDATE`
- Candidate status: `REJECTED`
- Exclusion reason: `model_not_promoted_or_quality_gates_failed`

Contribution categories:

- trend_structure: 62.7%
- returns_momentum: 16.6%
- residual/unexplained: 10.0%
- volatility_range: 5.5%

Relationship evidence in the snapshot included stable SPY/inverse and QQQ/inverse relationships plus multiple inverse/leveraged ETF divergences. These are model evidence, not causal claims.

## Analog Example

Historical analogs are generated inside `engine.attribution.explain_candidate` from the model bundle's stored training matrix and labels using train-fitted scaling. The scanner output persists attribution categories and relationship evidence; richer analog display is available through the Candidate Attribution dashboard section and remains subject to the same no-future-data rule.

## Portfolio Backtest Summary

The portfolio backtester is implemented and covered by tests for next-open entries and short returns.

A real latest-snapshot backtest produced:

- Trades: 0
- Reason: latest as-of date was the newest local session, so no subsequent next-open bar existed yet.

This is correct timing behavior; the latest scanner snapshot is for paper-forward observation, not a completed historical trade.

## Paper Forward-Test State

SQLite forward events after local acceptance:

- Total forward events: 185
- Latest governance-aware forward update inserted: 50 rejected-signal events
- Immediate rerun inserted: 0 new events

There are no champion-approved pending entries because no model passed quality gates.

The forward engine now fills pending entries at the next completed session open when later bars exist, records `POSITION_MARKED` events with mark return/MFE/MAE, and records time-exit `EXIT_FILLED` events at the frozen horizon. This behavior is covered by regression tests and remains append-only/idempotent.

## Daily-Cycle Behavior

Daily cycle command:

```bash
python -m swing_rsi.cli daily-cycle --include-challengers
```

Wrapper:

```bash
./scripts/run_daily_cycle.sh --include-challengers
```

Verified behavior:

- First run completed with feature rows, modeling rows, scanner rows, and forward-event summary.
- Rerun for the same market date returned `already_completed`.
- Lock file prevents simultaneous daily cycles.
- Forward-event insertion is idempotent.
- The wrapper script is executable and returned `already_completed` for the existing local daily cycle.
- Drift checks ran separately after the stored daily-cycle summary was already completed: 14 model reports, 0 alerts.

## Database Schema

SQLite path: `state/engine.sqlite3` (ignored by Git).

Tables:

- `models`
- `scanner_snapshots`
- `scanner_candidates`
- `forward_events`
- `daily_cycles`

Final local counts:

- models: 26
- scanner_snapshots: 3
- scanner_candidates: 150
- forward_events: 185
- daily_cycles: 1

Generated SQLite state is not committed.

## CLI Commands Added

```bash
python -m swing_rsi.cli universe-update
python -m swing_rsi.cli build-features
python -m swing_rsi.cli discover-models
python -m swing_rsi.cli model-registry
python -m swing_rsi.cli promote-model
python -m swing_rsi.cli scan
python -m swing_rsi.cli forward-update
python -m swing_rsi.cli daily-cycle
```

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

Legacy RSI dashboard pages remain accessible under Baselines and Legacy RSI.

Launch command:

```bash
./scripts/run_dashboard.sh
```

## Verification Commands

Automated:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

Results:

- pytest: 74 collected, 74 passed
- Ruff: all checks passed
- Ruff format: 86 files already formatted
- mypy: success, no issues in 50 source files

Streamlit/App tests:

- AppTest interactions were included in pytest and passed.
- Local Streamlit startup smoke required sandbox escalation to bind `127.0.0.1:8765`.
- HTTP smoke: `curl -I http://127.0.0.1:8765` returned `HTTP/1.1 200 OK`.
- Clean shutdown: process on port 8765 was killed and subsequent curl failed to connect, confirming the port closed.
- In-app Browser MCP was unavailable in this session (`iab` not exposed), so browser DOM verification could not be completed. AppTest plus HTTP smoke were completed.

Real local-data pipeline:

```bash
python -m swing_rsi.cli universe-update --start 2016-06-20
python -m swing_rsi.cli build-features
python -m swing_rsi.cli discover-models --minimum-training-samples 200 --minimum-holdout-samples 80
python -m swing_rsi.cli scan --include-challengers
python -m swing_rsi.cli forward-update
```

Real update included all configured 35 symbols through the existing FMP provider abstraction. The API key and `.env` contents were never printed.

Additional verified commands:

```bash
python -m swing_rsi.cli forward-update
python -m swing_rsi.cli daily-cycle --include-challengers
./scripts/run_daily_cycle.sh --include-challengers
```

Results:

- Second `forward-update`: 0 new events, 185 total forward events.
- Daily cycle: `already_completed` for `2026-06-19`, no duplicate cycle.
- Wrapper: `already_completed` for `2026-06-19`, no duplicate cycle.
- Drift check service: 14 reports, 0 alerts; PyArrow printed sandbox CPU-info warnings only.

## Security Audit

PASS:

- `.env` is ignored and was not opened or printed.
- `.venv` is ignored.
- `data/raw/*` is ignored.
- `data/features/*` is ignored.
- `artifacts/*` is ignored except `.gitkeep`.
- `state/*` is ignored except `.gitkeep`.
- reports, logs, caches, and Streamlit local files are ignored.
- No API key or authenticated URL was staged or committed.
- Automated tests do not call FMP.
- Dashboard imports do not make FMP requests.

## Leakage Audit

PASS:

- Feature calculations are trailing or same-date only.
- Future rows mutation test confirms prior features are unchanged.
- Labels are prefixed with `label_` and physically separated.
- `reject_label_columns` prevents label columns from entering model features.
- Chronological split purges rows whose label horizon overlaps calibration or holdout windows.
- Train-only preprocessing and calibration separation are used.
- Scanner uses latest as-of feature rows and no label columns.
- Close-known signals cannot enter at the same close; portfolio and forward rules use next-session/next-completed-session open semantics.
- Failed trades/signals are retained; rejected scanner rows include exclusion reasons.
- Forward fills, marks, and exits are appended as new events; old event rows are not rewritten.

## Known Limitations

- No model passed all quality gates, so there is no champion and no champion-approved paper pending entry.
- Scanner outputs from `--include-challengers` are review-only when models are `CANDIDATE`.
- Feature families are broad but still a first bounded vertical slice; mutual information screening is not yet implemented, and permutation/drift diagnostics are intentionally bounded.
- Regime labels are basic unsupervised states and are not named bull/bear causes.
- Historical analogs are implemented in attribution but dashboard presentation is minimal.
- Dynamic stop/target and trailing-stop paper-forward policies are not enabled yet; the current lifecycle uses frozen next-open entry and horizon time exits.
- Portfolio backtester is implemented but latest real scanner snapshot has no subsequent next-open bar yet, so real latest-snapshot trades are zero.
- No options, NLP, intraday data, brokerage execution, authentication, deployment, FastAPI, SvelteKit, or database server were added.
- FMP corporate-action semantics, delisted coverage, and point-in-time historical universe membership remain unaudited.
- Current-universe historical tests may contain survivorship bias.
- PyArrow emitted sandbox-specific `sysctlbyname` CPU-info warnings during one inspection script; tests and pipeline still completed.

## Commands for Users

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
python -m swing_rsi.cli discover-models
python -m swing_rsi.cli scan --include-challengers
python -m swing_rsi.cli forward-update
```

## Next Smallest Milestone

Tighten model quality gates and diagnostics for the current daily scanner: add richer gate reporting, feature-stability summaries, calibration plots/tables, and a clear champion-promotion review workflow without adding new data domains or execution capabilities.
