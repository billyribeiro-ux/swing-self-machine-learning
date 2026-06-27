# Signal-First Trading Research Dashboard

## Purpose

The Signal-First Trading Research Dashboard V1 is the local Streamlit view for
the development engine. It is designed to answer the operational research
questions first:

- Are there any live actionable scanner rows?
- Are there shadow or paper validation rows?
- Are entries pending, open, closed, or matured?
- Which model produced the row?
- Why did the candidate appear?
- Why is it actionable, shadow-only, rejected, or research-only?
- What evidence still blocks the model?
- What can be exported?

This dashboard is not a trading application and does not place orders.

## Launch

Run from the development worktree only:

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

The app blocks startup from:

```text
/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner
```

That operational worktree remains read-only dashboard context.

## Visible Pages

`dashboard/app.py` uses explicit `st.navigation` registration. The visible
sidebar order is:

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

The old primary labels are not registered:

- Discovery Lab
- Live Scanner
- Portfolio Backtests
- Baselines and Legacy RSI

## Signal Status

Signal Board rows use these visible lifecycle labels:

- `LIVE ACTIONABLE`
- `SHADOW ONLY`
- `REJECTED`
- `PENDING ENTRY`
- `OPEN SHADOW POSITION`
- `CLOSED`
- `RESEARCH ONLY`

If no promoted model exists, the Signal Board displays:

```text
No promoted live scanner model exists yet.
Current signals are research/shadow validation only.
```

Missing MFE/MAE values display as `Not available`, not zero.

Each Signal Board row includes an `Open detail` link that routes to
Candidate Detail with `scan_id`, `ticker`, `model_id`, and `direction` query
parameters. Candidate Detail uses those parameters as selectbox defaults.

## Edge Status

Every model-facing row maps to one edge status:

- `RESEARCH ONLY`: model exists but failed development gates or is diagnostic only.
- `DEVELOPMENT CANDIDATE`: model passed some research checks but still has blockers.
- `SHADOW VALIDATION`: model is frozen and collecting prospective evidence.
- `FINAL-HOLDOUT QUALIFIED`: prospective evidence collection and gates passed.
- `PROMOTED`: model was manually promoted and may produce live actionable scanner rows.

The dashboard does not call anything an edge unless it is at least
`SHADOW VALIDATION`. It does not call anything live unless model state and gates
allow it.

## Exports

Major tables provide CSV and XLSX downloads. XLSX helpers live in:

```text
src/swing_rsi/application/dashboard_exports.py
```

Reusable helpers:

- `to_csv_bytes(...)`
- `to_xlsx_bytes(...)`
- `save_xlsx_report(...)`

The Reports and Exports page includes `Export Complete Engine Snapshot`, which
saves an XLSX workbook under:

```text
reports/dashboard_exports/
```

Workbook sheets:

- `signal_board`
- `shadow_forward_status`
- `model_edge_status`
- `scanner_results`
- `gate_audit`
- `product_class_research`
- `candidate_attribution`
- `data_universe`
- `reports_index`

The export helpers redact API-key-like content and do not include `.env`
contents or authenticated URLs.

## Command Behavior

Engine Commands are development-only and require:

- exact command preview;
- checkbox confirmation;
- development-only warning;
- captured stdout/stderr;
- log file under `reports/dashboard_command_logs/`.

Allowed buttons:

- `universe-update`
- `build-features`
- `final-holdout-update`
- `final-holdout-status`
- `scanner review run`
- `model-audit --generation latest`

Disabled buttons:

- `discover-models`
- `promote-model`
- `final-holdout-init`
- `forward-update`

Disabled commands show:

```text
Disabled from dashboard V1 to prevent accidental model mutation or promotion.
```

## Safety

Page load must not contact FMP, mutate SQLite, mutate artifacts, run scanner,
run final-holdout update, run forward update, run discovery, or promote models.
FMP universe update remains an explicit confirmed development action only.
