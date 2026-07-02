# Multi-Angle Calibration Audit Artifacts V1 Handoff

Date: 2026-06-29

Development repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

Development branch: `feat/product-class-specialist-challengers-v1`

Operational repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

Operational frozen run: `3493ee8ac37bf96475c362e1`

Operational enrolled model: `b93b2258c10aea5cef81d291`

Operational baseline date: 2026-06-25

## Why This Was Needed

`docs/ARCHETYPE_TBS_CALIBRATION_DIAGNOSTIC.md` found that the current
target-before-stop blocker could not answer several calibration questions from
existing artifacts. The diagnostic classified the overall evidence as
`VALID_MODEL_GATE`, `ANALOG_SUPPORT_NOT_ROBUST`,
`PRODUCT_CLASS_INSTABILITY`, `INSUFFICIENT_EVIDENCE`, and
`TARGET_STOP_POLICY_MISMATCH`, while not proving model underconfidence,
calibration collapse, or an implementation defect.

The missing piece was persistent calibration-slice evidence for raw
probability distributions, calibrated probability distributions, probability
buckets, threshold regions, and row-level target/stop outcomes. This change
adds those artifacts without changing thresholds, gates, labels, OOD
governance, model artifacts, or operational state.

## Artifact Schema

Schema: `multi_angle_calibration_audit_v1`

Generated files:

- `calibration_summary.csv`
- `calibration_summary.json`
- `probability_distributions.csv`
- `probability_buckets.csv`
- `diagnostic_thresholds.csv`
- `row_level_calibration_audit.parquet`
- `row_level_calibration_audit.csv`
- `calibration_artifact_manifest.json`

All threshold rows are diagnostic only and include `diagnostic_only = True`.

## Files Created

- `docs/MULTI_ANGLE_CALIBRATION_AUDIT.md`
- `docs/MULTI_ANGLE_CALIBRATION_AUDIT_HANDOFF.md`

Generated ignored report/export files:

- `reports/signal_discovery_calibration_v1/calibration_summary.csv`
- `reports/signal_discovery_calibration_v1/calibration_summary.json`
- `reports/signal_discovery_calibration_v1/probability_distributions.csv`
- `reports/signal_discovery_calibration_v1/probability_buckets.csv`
- `reports/signal_discovery_calibration_v1/diagnostic_thresholds.csv`
- `reports/signal_discovery_calibration_v1/row_level_calibration_audit.parquet`
- `reports/signal_discovery_calibration_v1/row_level_calibration_audit.csv`
- `reports/signal_discovery_calibration_v1/calibration_artifact_manifest.json`

## Dashboard Changes

Candidate Detail now shows calibration diagnostics for Signal Discovery rows:

- model TBS probability;
- same-archetype calibration base rate;
- same-scope calibration base rate;
- calibration evidence status;
- diagnostic threshold table;
- probability bucket evidence;
- diagnostic-only blocker assessment.

Reports and Exports includes calibration audit frames in the Signal Discovery
workbook and exposes direct downloads for the audit tables.

Signal Board remains compact.

Every dashboard display uses the required warning:

```text
Calibration diagnostic only. Not a threshold change and not proof of edge.
```

## Signal-Discovery Generation

New generation ID: `signal_discovery_20260629T232550+0000_92147b091ad7`

Export directory: `reports/signal_discovery_calibration_v1`

Hypotheses evaluated: 15

Calibration artifacts created: yes

Rows in `calibration_summary`: 146

Rows in `diagnostic_thresholds`: 1,022

Rows in `probability_buckets`: 1,460

Rows in `row_level_calibration_audit`: 490,296

Previous N/A calibration fields now available: yes. The export includes raw
and calibrated TBS probability distributions, diagnostic thresholds,
probability buckets, row-level calibration rows, calibration base rates, Brier
metrics, AUC metrics, ECE, calibration slope/intercept, plateau counts, and
artifact hashes.

## Calibration Summary For Top Blocked Rows

Top blocked rows from the new generation now have same-hypothesis/family/scope
calibration summaries:

| Ticker | Hypothesis | Scope | TBS probability | Calibration rows | TBS base rate | Model Brier | Naive Brier |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| TZA | `sector_rotation_buy_20d` | `LEVERAGED_INVERSE` | 0.358930 | 2,874 | 0.270007 | 0.201272 | 0.197103 |
| SQQQ | `sector_rotation_buy_20d` | `LEVERAGED_INVERSE` | 0.352071 | 2,874 | 0.270007 | 0.201272 | 0.197103 |
| SOXS | `breakdown_sell_10d` | `LEVERAGED_INVERSE` | 0.261255 | 2,946 | 0.301086 | 0.211206 | 0.210433 |
| SOXS | `pullback_continuation_sell_10d` | `LEVERAGED_INVERSE` | 0.261255 | 2,946 | 0.301086 | 0.211206 | 0.210433 |
| SOXS | `trend_continuation_sell_10d` | `LEVERAGED_INVERSE` | 0.261255 | 2,946 | 0.301086 | 0.211206 | 0.210433 |
| SOXS | `breadth_deterioration_sell_10d` | `LEVERAGED_INVERSE` | 0.261255 | 2,946 | 0.301086 | 0.211206 | 0.210433 |
| RWM | `sector_rotation_buy_20d` | `INVERSE` | 0.358930 | 958 | 0.277662 | 0.205365 | 0.200566 |
| AMZN | `sector_rotation_buy_20d` | `ORDINARY` | 0.394651 | 11,017 | 0.384134 | 0.236749 | 0.236575 |
| QID | `sector_rotation_buy_20d` | `LEVERAGED_INVERSE` | 0.352071 | 2,874 | 0.270007 | 0.201272 | 0.197103 |
| SOXS | `volatility_expansion_sell_5d` | `LEVERAGED_INVERSE` | 0.146034 | 2,982 | 0.169014 | 0.140689 | 0.140448 |

## Tests

Focused tests run before final verification:

- `.venv/bin/pytest tests/test_signal_discovery.py`
- `.venv/bin/pytest tests/test_streamlit_command_center.py -k "candidate_detail or reports_and_exports"`
- `.venv/bin/mypy src`

Full verification:

- `.venv/bin/pytest` -> 367 passed, 11,576 warnings.
- `.venv/bin/ruff check .` -> passed.
- `.venv/bin/ruff format --check .` -> passed.
- `.venv/bin/mypy src` -> passed.
- Streamlit AppTest coverage for Candidate Detail and Reports/Exports passed
  through `tests/test_streamlit_command_center.py`.
- Local HTTP smoke test: `.venv/bin/streamlit run dashboard/app.py
  --server.headless true --server.port 8765 --server.address 127.0.0.1`
  plus `curl -I http://127.0.0.1:8765` -> `HTTP/1.1 200 OK`.

## Operational Immutability Proof

Before implementation:

- operational HEAD:
  `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- operational Git status:
  `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- operational SQLite hash:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- enrolled model artifact hash:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- scanner snapshot count: `18`
- ordinary forward-event count: `285`
- final-holdout event count: `25`
- prospective run ID: `3493ee8ac37bf96475c362e1`
- baseline date: `2026-06-25`

After verification:

- operational HEAD:
  `3f3c4f853cc183e6a0a4900dadc428162c400ef7`
- operational Git status:
  `## feat/autonomous-swing-scanner-v1...origin/feat/autonomous-swing-scanner-v1`
- operational SQLite hash:
  `b2ae5fbf6ad4cf7e98a23cc0bc4dfad904203c211b8acf476526f835760e69e8`
- enrolled model artifact hash:
  `86f0f99ed3d3ef1107067844d69a368d044f0af2d2fd6604614e0355d0c2ce0e`
- scanner snapshot count: `18`
- ordinary forward-event count: `285`
- final-holdout event count: `25`
- prospective run ID: `3493ee8ac37bf96475c362e1`
- baseline date: `2026-06-25`

The before and after values match.

## Safety Confirmation

This implementation is diagnostic-only. It does not:

- change signal status;
- override gates;
- lower thresholds;
- promote models;
- create shadow entries;
- create live actionable signals;
- update FMP data;
- mutate operational repository state.

## Next Engineering Task

Use the new calibration audit artifacts to produce a read-only post-generation
calibration evidence review for the highest-scoring target-before-stop blocked
rows, without changing thresholds or gates.
