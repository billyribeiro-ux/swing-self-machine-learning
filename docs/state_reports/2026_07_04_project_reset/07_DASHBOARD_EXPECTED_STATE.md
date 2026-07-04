# Dashboard Expected State

The dashboard was not run for this report pack. This is expected display based on inspected state only.

## Signal Board Expected

- latest market date: `2026-07-02`
- live actionable signals: 0
- operational shadow/paper signals: 0 accepted
- development final-holdout active signals: 0 because the development run is invalidated
- time-exit diagnostic observations: 23
- time-exit diagnostic pending entries: 23
- open positions: 0
- closed/matured outcomes: 0
- rejected/research rows: 516 NO_SIGNAL and 28 rejected in latest signal discovery
- regime cache status: `HIT` in development
- top visible time-exit diagnostic row: AMD
- old TZA row should appear only as historical invalidated final-holdout evidence, not active shadow

## Shadow Final Holdout Expected

- operational run `3493ee8ac37bf96475c362e1`: `COLLECTING`
- operational latest processed date: `2026-07-02`
- operational accepted/pending/open/matured: `0 / 0 / 0 / 0`
- development final-holdout run `d25d6fa11a2e50daa430c15e`: `INVALIDATED`
- time-exit diagnostic run `0e5facd1e8a164df2b586f64`: `CREATED` diagnostic state with 23 pending entries

## Candidate Detail Expected

- AMD time-exit row should be openable if dashboard links support it
- AMD signal ID: `56107721aed3504110dc7ece`
- full raw IDs should be available
- Time-Exit Utility Diagnostic section should be visible for AMD and related rows
- footprint evidence should be visible where generated

AMD detail should show:

- status: `RESEARCH_ONLY` / `NO_SIGNAL`
- TBS probability: 0.431830
- time-exit positive probability: 0.597391
- expected time-exit return: 0.047963
- expected time-exit utility: 1.292267
- blocker: `target_before_stop_probability_below_threshold`
- diagnostic-only warning

## Reports And Exports Expected

- latest signal-discovery export available: yes, `reports/latest_signal_discovery_after_2026_07_02_update`
- time-exit diagnostic export available: yes, `reports/time_exit_diagnostic_after_2026_07_02_update`
- July 2 data advance report available: yes, `docs/DATA_ADVANCE_TO_2026_07_02_STATUS.md`
- state reset report pack available after commit: yes, under `docs/state_reports/2026_07_04_project_reset/`

