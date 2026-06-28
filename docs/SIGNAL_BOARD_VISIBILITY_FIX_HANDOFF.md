# Signal Board Visibility Fix Handoff

## Root Cause

Signal Board previously rendered one mixed table with a prominent zero-live
notice above it. In a state with zero live actionable rows but one pending
shadow entry, that message could read as if the board had no useful rows, even
though the status cards correctly showed one shadow/paper signal and one
pending entry.

The table also did not explicitly separate live, shadow, pending, open, closed,
and rejected/research rows, so rejected scanner rows competed with the current
shadow lifecycle row.

## Final Default Display Behavior

Signal Board now displays rows in separate sections with row counts:

1. Live Actionable Signals
2. Shadow / Paper Signals
3. Pending Entries
4. Open Shadow Positions
5. Closed / Matured Outcomes
6. Rejected / Research Candidates

Default behavior:

- live rows are included;
- shadow rows are included;
- pending entries are included;
- open shadow positions are included;
- closed/matured rows are included;
- rejected/research rows are collapsed unless `Show rejected/research rows` is enabled.

When there are zero live rows, the page says:

```text
No live actionable signals. Shadow and pending rows remain visible below.
```

The live section says:

```text
No promoted live scanner signals are currently available.
```

Pending rows show:

- ticker;
- direction;
- model ID;
- generation;
- run ID;
- event ID;
- edge status;
- signal status;
- as-of date;
- pending entry date;
- entry rule;
- expected return;
- expected MFE;
- expected MAE;
- target-before-stop probability;
- OOD warning;
- why it is shadow-only;
- next required event;
- Open link.

Unavailable values display as `Not available`.

## Open Link Behavior

Each row has an `Open detail` link. The link routes to Candidate Detail and
carries available identifiers:

- `run_id`
- `event_id`
- `scan_id`
- `ticker`
- `model_id`
- `direction`
- `status`

Candidate Detail preselects the matching scan, ticker, and model when those
query parameters are present.

## Tests

Updated tests prove:

- zero live count does not hide the shadow row;
- pending entries are displayed by default;
- rejected/research rows are collapsed by default;
- missing MFE/MAE displays as `Not available`;
- the no-live message does not imply shadow rows are absent;
- pending row includes the next required event;
- pending row Open link includes run ID, event ID, model, ticker, and direction;
- Signal Board page load does not mutate SQLite;
- existing dashboard page-load tests still block FMP access and model/scanner mutation.

## Verification

Run from the development worktree:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

Focused Signal Board verification:

```bash
.venv/bin/pytest tests/test_streamlit_command_center.py::test_signal_first_tables_label_live_shadow_and_missing_paths tests/test_streamlit_command_center.py::test_signal_board_default_sections_keep_shadow_and_pending_visible tests/test_streamlit_command_center.py::test_signal_board_detail_links_preselect_candidate_detail
```

## Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

## Operational State

The operational repository remains read-only dashboard context. This fix does
not modify operational files, SQLite, artifacts, scanner snapshots, events, or
`.env`.
