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

Signal Board defaults to sectioned visibility:

1. Live Actionable Signals
2. Shadow / Paper Signals
3. Pending Entries
4. Open Shadow Positions
5. Closed / Matured Outcomes
6. Rejected / Research Candidates

Rejected and research-only candidates are collapsed by default behind `Show
rejected/research rows`. Shadow, pending, open, and closed rows remain visible
even when live actionable count is zero.

Each Signal Board row includes an `Open detail` link that routes to Candidate
Detail with `run_id`, `event_id`, `scan_id`, `ticker`, `model_id`, `direction`,
and `status` where available. Candidate Detail uses those parameters as
selectbox defaults.

Signal Board uses friendly display identifiers in the visible table:

- model: product scope, direction, model family, horizon, and short model ID;
- generation: timestamp rounded to minute precision;
- run: development shadow run label plus short run ID;
- event: lifecycle label plus short event ID.

The full raw `model_id`, generation timestamp, `run_id`, and `event_id` remain
in Candidate Detail routing and CSV/XLSX exports. The friendly labels are
display-only and do not alter scanner identity, event identity, model identity,
or export audit fields.

Candidate Detail includes a compact `Full Raw Identifiers` section. It displays
the selected candidate's raw scan, model, generation, run, event, status, and
feature-snapshot identifiers in both a table and a copyable text block. The
same section also displays a copyable `/candidate-detail?...` deep link built
from the full raw identifiers. The Candidate Detail workbook includes the same
fields on a `raw_identifiers` sheet and the URL on a `deep_link` sheet.

Candidate Detail also includes quantified footprint evidence. Every footprint
claim must have a measured evidence row or explicit `Evidence unavailable`
status. The evidence tables show category, claim, metric, value, window,
percentile/rank when available, comparison instrument, supporting feature,
evidence type, strength, and missing-data status. The dashboard separates
supporting evidence, conflicting evidence, historical analog outcomes, and
residual/unexplained attribution. Signal Board stays compact and shows only a
short footprint summary.

For Multi-Angle Signal Discovery rows, Candidate Detail also displays
calibration diagnostics when the generation includes
`multi_angle_calibration_audit_v1` artifacts:

- model target-before-stop probability;
- same-archetype calibration base rate;
- same-scope calibration base rate;
- calibration evidence status;
- diagnostic threshold table;
- probability bucket evidence;
- diagnostic-only TBS blocker assessment.

The section is always labeled:

```text
Calibration diagnostic only. Not a threshold change and not proof of edge.
```

These diagnostics do not change row status, thresholds, gates, OOD governance,
model promotion, scanner actionability, paper-forward state, or final-holdout
state.

For Sector Rotation BUY `ORDINARY` time-exit utility research rows, the
dashboard also surfaces prospective diagnostic ledger evidence when available.
Signal Board shows a separate `Time-Exit Diagnostic Observations` section with
diagnostic pending, open, matured, rejected, and backfill-blocked statuses.
These rows are visually separate from live actionable signals and shadow
final-holdout rows.

Candidate Detail shows `Prospective Time-Exit Diagnostic` for rows that have a
matching ledger observation or matured outcome. The section includes diagnostic
run status, observation state, entry/fill details when available, time-exit
result when matured, utility score, profitable-despite-failed-TBS flags, early
adverse recovery flags, and baseline-versus-experimental policy touch outcomes.
It is labeled:

```text
Prospective time-exit diagnostic is DIAGNOSTIC_ONLY / RESEARCH_OBSERVATION. It is not a live signal and not final-holdout evidence.
```

The dashboard reads these ledger tables without mutating SQLite on page load.

## Signal Board Regime Cache Status

Signal Board shows compact Regime KMeans Cache cards near the top status-card
area so development users can see whether the most recent `build-features` run
used the fast exact cache path. The cards show:

- regime cache status;
- last cached date;
- KMeans fits avoided;
- regime runtime;
- cache validity reason.

The panel reads local cache metadata only and does not run `build-features` on
page load. If metadata is missing, Signal Board displays `Regime cache status:
Not found` and shows the other cache-card fields as `Not available`.

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

- `normalize_table_for_export(...)`
- `to_csv_bytes(...)`
- `to_xlsx_bytes(...)`
- `save_xlsx_report(...)`

All CSV/XLSX workbook exports normalize tables before serialization. Numeric
tables stay numeric, date columns stay date-like, and mixed diagnostic display
columns such as `Value`, `Actual`, and `Threshold` become redacted strings. This
prevents Arrow/Parquet conversion failures from mixed object values without
turning unavailable values into zeros.

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
- `time_exit_diagnostic_status`
- `time_exit_diagnostic_events`
- `time_exit_diagnostic_observations`
- `time_exit_diagnostic_matured_outcomes`

Reports and Exports also includes a dedicated Prospective Time-Exit Diagnostic
section with CSV downloads and an XLSX workbook for the ledger status, events,
observations, and matured outcomes. XLSX sheet names may be truncated to
Excel's 31-character sheet-name limit.

The export helpers redact API-key-like content and do not include `.env`
contents or authenticated URLs.

Developer Diagnostics adds Regime KMeans Cache CSV and XLSX exports. The XLSX
workbook contains `summary`, `metadata`, `input_columns`, and `kmeans_config`
sheets.

Candidate Detail workbook exports include measured footprint sheets:

- `footprint_summary`
- `footprint_evidence`
- `supporting_evidence`
- `conflicting_evidence`
- `historical_analogs`
- `calibration_overview`
- `calibration_summary`
- `calibration_thresholds`
- `calibration_buckets`
- `target_stop_policy`
- `policy_registry`
- `calibration_selection`
- `baseline_vs_candidate`
- `derived_outcomes`
- `signal_policy_comparison`
- `time_exit_labels`
- `time_exit_calibration`
- `time_exit_signal_rows`
- `time_exit_policy_comparison`
- `residual_unexplained`

Reports and Exports includes Signal Discovery calibration audit sheets when
available:

- `calibration_summary`
- `probability_distributions`
- `probability_buckets`
- `diagnostic_thresholds`
- `row_level_calibration_audit`
- `calibration_artifact_manifest`
- `target_stop_policy_registry`
- `calibration_selection`
- `sector_rotation_buy_ordinary_policy_comparison`
- `derived_policy_outcomes`
- `signal_discovery_policy_comparison`
- `time_exit_utility_labels`
- `time_exit_utility_calibration_summary`
- `time_exit_utility_signal_rows`
- `time_exit_utility_policy_comparison`

Signal Board keeps target/stop policy display compact. Candidate Detail shows
baseline-versus-experimental policy metrics, calibration-only selection
evidence, exact derived policy outcomes when available, and the warning:

```text
Experimental target/stop policy. Development evidence only. Not a live signal.
```

When time-exit utility diagnostics are available, Signal Board shows compact
time-exit positive probability and utility fields. Candidate Detail shows a
Time-Exit Utility Diagnostic section with TBS probability, time-exit positive
probability, expected time-exit return, expected time-exit utility,
profitable-despite-failed-TBS evidence, early-adverse-recovery evidence,
label-side rows, calibration summaries, and the warning:

```text
Time-exit utility is diagnostic. It does not override gates or create a live signal.
```

Gate Audit keeps canonical model gates unchanged and adds a separate Signal
Discovery policy-gate table when local generation artifacts include policy
fields.

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
