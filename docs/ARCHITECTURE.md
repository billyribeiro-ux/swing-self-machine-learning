# Architecture

## Dependency flow

```text
FMP / CSV / optional comparison provider
   ↓
Raw-response provenance and provider adapter
   ↓
Normalization and OHLCV validation
   ↓
Universe snapshot and raw-data manifests
   ↓
Declarative autonomous feature registry
   ↓
Separated bullish/bearish label engine
   ↓
Chronological train / calibration / holdout split with purging
   ↓
Bounded model discovery and calibrated probabilities
   ↓
Model registry and immutable artifacts
   ↓
Latest-session scanner and attribution
   ↓
Portfolio scanner-output backtester
   ↓
Drift checks and append-only paper-forward lifecycle
   ↓
Prospective shadow final-holdout collection and evaluation
   ↓
Daily-cycle orchestration
```

## Package layout

```text
src/swing_rsi/
  settings.py               local environment and FMP configuration
  config.py                 YAML configuration and project paths
  data/
    providers/              FMP and future provider adapters
    loader.py               provider selection and CSV loading
    validation.py           OHLCV schema and market-data invariants
    storage.py              data persistence helpers
  features/                 trailing price features, RSI, and future labels
  signals/                  explicit candidate signal definitions
  backtest/                 execution timing, trades, and metrics
  research/                 candidate grids and walk-forward selection
  scanner/                  latest-bar evidence output
  forward/                  immutable signal and outcome journals
  engine/                   autonomous universe, features, labels, models, scanner, attribution, registry, paper forward testing, final holdout
  reports/                  atomic report writers
  application/              shared CLI/dashboard orchestration services
  sample_data.py            deterministic plumbing-only demo data
  cli.py                    user-facing commands
dashboard/                  local Streamlit presentation layer
  app.py                    explicit st.navigation entrypoint
  sections/                 primary engine pages and legacy RSI page renderers
  ui/                       local formatting, chart, cache, and error helpers
```

## Provider boundary

FMP is the primary Version 1 daily-data source, but research logic does not call FMP directly. Provider-specific responses are normalized at the ingestion boundary. This allows later comparison with another source without rewriting RSI, labeling, backtesting, or scanning logic.

API keys are loaded from `.env`, sent through request headers, and never printed or committed.

## Data separation

Feature columns contain only current and prior information. Future outcome columns must begin with `label_`. The scanner and signal generators must never accept `label_` columns as inputs.

The autonomous engine stores raw licensed data, processed features, model artifacts, scanner snapshots, SQLite state, logs, and generated reports outside Git.

## Execution timing

Version 1 signals are known only after a daily bar closes. The default simulated entry is the next session open. The fixed-horizon exit for an `H`-bar hold is the close of bar `t + H`, where `t` is the signal bar. No same-close fill is allowed.

## Persistence

- Raw and derived market data live under `data/` and are ignored by Git.
- Reports live under `reports/` and are ignored by Git.
- Forward signals, fills, marks, and exits are stored as append-only SQLite events.
- Methodology and decisions live under `docs/` and are the permanent source of truth.

## Autonomous engine boundary

The autonomous engine is implemented in typed Python modules under `src/swing_rsi/engine/` and shared through `src/swing_rsi/application/engine_service.py`.

Streamlit calls these services directly. It does not implement feature calculation, label creation, model training, scanner ranking, attribution, portfolio backtesting, or paper-forward event logic.

Model drift checks are review signals only. They do not mutate, replace, or promote deployed model versions.

## Local dashboard boundary

The Streamlit dashboard is a local-only presentation layer. It calls reusable Python services under `src/swing_rsi/application/` and does not duplicate market-data, RSI, signal, backtest, research, or walk-forward logic inside dashboard pages.

Dashboard navigation is explicit. `dashboard/app.py` registers the primary Signal-First Trading Research Dashboard sections with `st.navigation` / `st.Page`:

1. Signal Board
2. Shadow Forward Test
3. Model Edge Status
4. Scanner Results
5. Candidate Detail
6. Product-Class Research
7. Gate Audit
8. Data and Universe
9. Reports and Exports
10. Engine Commands
11. Legacy Baselines
12. Developer Diagnostics

Streamlit auto-discovered `dashboard/pages/*.py` page files are not used, because filename-derived labels caused confusing navigation.

The command-center dashboard reads development SQLite, artifacts, reports, raw data, feature data, manifests, and universe configuration through read-only application services for page loads. Mutating actions are restricted to explicit confirmed buttons and command wrappers. The dashboard refuses command execution from the operational worktree, displays the frozen operational run as read-only status, and keeps generated dashboard workbooks and command logs under ignored `reports/dashboard_exports/` and `reports/dashboard_command_logs/`.

The Data and Audit page uses `swing_rsi.application.datasets.structural_audit_frame` for both selected-window and full-raw-file audits. Selected-window metrics and tables are calculated only from the sliced dataframe; raw-file metrics and tables remain visibly separate.

Ticker input is normalized at the application boundary with `normalize_ticker`, which strips a single trailing `.csv`, uppercases the provider symbol, preserves valid period/hyphen symbols, and rejects path or traversal input.

The dashboard may cache deterministic local CSV reads by file path and modification time through `dashboard/ui/cache.py`. It does not cache API keys, FMP update requests, file writes, research runs, walk-forward runs, or append-only actions.

Expected dashboard errors are handled with concise user-facing messages. Unexpected dashboard errors are logged to ignored local files under `logs/`.

Walk-forward split arithmetic is centralized in `swing_rsi.research.walk_forward.plan_expanding_splits`. Dashboard preflight validation and actual walk-forward execution share the resulting split plan so a configuration cannot pass one path and fail the other. This remains legacy historical validation and is distinct from paper forward testing of frozen scanner models.

Streamlit is temporary local presentation infrastructure. The long-term UI may later be replaced by SvelteKit over a typed FastAPI/OpenAPI boundary, but no separate API or deployment layer exists in this milestone.

## Extension path

Once Version 1 is proven, additional indicators become candidate feature modules using the same interfaces. Sector, inverse ETF, market regime, news, options, and attribution layers are added only after the base validation loop is trustworthy.
