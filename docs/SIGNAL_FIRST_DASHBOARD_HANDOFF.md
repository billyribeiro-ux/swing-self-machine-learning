# Signal-First Dashboard Handoff

## Root Problem Fixed

The previous Command Center was technically useful but infrastructure-first. The
first screen did not immediately answer whether anything was live actionable,
shadow-only, rejected, pending, open, closed, or exportable.

The dashboard has been refactored so `dashboard/app.py` launches a
signal-first Streamlit navigation and the home page is `Signal Board`.

## Final Page List

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

Old primary labels are not registered in the visible sidebar:

- Discovery Lab
- Live Scanner
- Portfolio Backtests
- Baselines and Legacy RSI

## Signal Status Definitions

- `LIVE ACTIONABLE`: promoted model and gates allow scanner action.
- `SHADOW ONLY`: prospective validation or paper-review row only.
- `REJECTED`: scanner candidate failed policy, gate, promotion, OOD, or path-head checks.
- `PENDING ENTRY`: shadow/paper entry waits for the next session open.
- `OPEN SHADOW POSITION`: shadow position waits for target, stop, or time exit.
- `CLOSED`: outcome is closed or matured for review.
- `RESEARCH ONLY`: row is visible for research diagnostics only.

If no promoted model exists, Signal Board states:

```text
No promoted live scanner model exists yet.
Current signals are research/shadow validation only.
```

Signal Board default sections are:

1. Live Actionable Signals
2. Shadow / Paper Signals
3. Pending Entries
4. Open Shadow Positions
5. Closed / Matured Outcomes
6. Rejected / Research Candidates

Rejected/research candidates are collapsed by default. Shadow and pending rows
remain visible when there are zero live actionable rows.

## Edge Status Definitions

- `RESEARCH ONLY`: model exists but failed development gates or is diagnostic only.
- `DEVELOPMENT CANDIDATE`: model passed some research checks but still has blockers.
- `SHADOW VALIDATION`: model is frozen and collecting prospective evidence.
- `FINAL-HOLDOUT QUALIFIED`: model completed prospective evidence collection and passed final-holdout gates.
- `PROMOTED`: model was manually promoted and may produce live actionable scanner rows.

The dashboard does not call anything an edge unless it is at least
`SHADOW VALIDATION`, and it does not call a row live unless the model is promoted
and all gates allow it.

## Export Behavior

Every main table keeps CSV and XLSX downloads. `Export Complete Engine Snapshot`
is an explicit button on Reports and Exports and saves under:

```text
reports/dashboard_exports/
```

Snapshot sheets:

- `signal_board`
- `shadow_forward_status`
- `model_edge_status`
- `scanner_results`
- `gate_audit`
- `product_class_research`
- `candidate_attribution`
- `data_universe`
- `reports_index`

XLSX files use `openpyxl`, freeze the header row, enable filters, set readable
column widths, and redact API-key-like content.

## Command Behavior

Allowed commands require exact preview plus checkbox confirmation:

- `universe-update`
- `build-features`
- `final-holdout-update`
- `final-holdout-status`
- `scanner review run`
- `model-audit --generation latest`

Disabled commands:

- `discover-models`
- `promote-model`
- `final-holdout-init`
- `forward-update`

Disabled commands show:

```text
Disabled from dashboard V1 to prevent accidental model mutation or promotion.
```

Command logs are written under ignored `reports/dashboard_command_logs/`. The
runner refuses the operational repository.

## Candidate Detail Linking

Signal Board rows include an `Open detail` URL in the rendered table. The URL
uses query parameters:

- `run_id`
- `event_id`
- `scan_id`
- `ticker`
- `model_id`
- `direction`
- `status`

Candidate Detail reads those parameters and preselects the matching scan,
ticker, and model controls while preserving manual selector use.

## Tests

Added or updated coverage proves:

- `dashboard/app.py` registers the exact 12 Signal-First pages in order.
- Old primary labels are absent from the visible sidebar registry.
- Signal Board, Shadow Forward Test, Model Edge Status, Scanner Results,
  Candidate Detail, Product-Class Research, Gate Audit, Data and Universe,
  Reports and Exports, Engine Commands, Legacy Baselines, and Developer
  Diagnostics load through Streamlit AppTest.
- Page loads do not contact FMP and do not mutate SQLite, scanner CSV, or model artifacts.
- Live actionable count is zero when no model is promoted.
- Signal Board still shows shadow and pending rows when live actionable count is zero.
- Rejected/research rows are collapsed by default.
- Rejected scanner rows are not labeled `Trade signal`.
- Shadow rows are labeled `SHADOW ONLY`.
- Missing MFE/MAE displays as `Not available`.
- Pending rows include the next required event and Open link identifiers.
- Signal Board links preselect Candidate Detail through query parameters.
- Complete engine snapshot XLSX opens with `openpyxl` and contains required sheets.
- Command buttons require confirmation.
- Discovery, promotion, final-holdout-init, and forward-update controls are disabled.
- Startup is blocked from the operational repository.

## Verification Results

Focused dashboard verification completed during development:

- `.venv/bin/pytest tests/test_dashboard_imports.py tests/test_streamlit_command_center.py tests/test_dashboard_interactions.py`: 29 passed
- `.venv/bin/ruff check dashboard tests/test_dashboard_imports.py tests/test_streamlit_command_center.py tests/test_dashboard_interactions.py src/swing_rsi/application/dashboard_service.py`: passed

Full repository verification, browser DOM proof, screenshot path, and final
commit hashes are reported in the Codex completion report after the final test
run and commits.

## Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

## Known Limitations

- This remains a local Streamlit dashboard, not a deployed application.
- The dashboard reads local development state; it does not create final evidence.
- Product-class conclusions depend on available local model and report evidence.
- Complete snapshot creation is explicit because it can read larger local audit tables.
- Promotion and discovery remain outside dashboard V1.

## Next Smallest Task

Add browser smoke coverage for clicking an `Open detail` link in the rendered
Streamlit table, not just AppTest query-param preselection.
