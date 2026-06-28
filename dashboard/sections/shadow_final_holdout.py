from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.application.dashboard_service import final_holdout_runs_frame, forward_events_frame
from swing_rsi.application.engine_service import update_final_holdout

PROGRESS_TARGETS = {
    "matured_outcomes": 100,
    "distinct_signal_dates": 60,
    "observation_sessions": 126,
    "calendar_months": 4,
    "positive_outcomes": 20,
    "negative_outcomes": 20,
}


def _progress_bars(row: pd.Series) -> None:
    streamlit = st()
    for metric, target in PROGRESS_TARGETS.items():
        value = int(row.get(metric, 0) or 0)
        streamlit.progress(
            min(value / target, 1.0),
            text=f"{metric.replace('_', ' ')}: {value:,} / {target:,}",
        )


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Shadow Final Holdout",
        "Prospective development final-holdout collection, sample sufficiency, and event state.",
    )
    streamlit.info("Development shadow validation only. No brokerage order is placed.")
    if streamlit.button("Refresh status read-only"):
        streamlit.rerun()

    status = final_holdout_runs_frame(root)
    events = forward_events_frame(root, final_holdout_only=True)
    streamlit.subheader("Runs")
    streamlit.dataframe(display_frame(status), width="stretch", hide_index=True)
    render_table_downloads(status, basename="shadow_final_holdout_runs", label="run_status")

    confirmed = streamlit.checkbox(
        "I understand this processes development shadow validation events only."
    )
    if streamlit.button("Run final-holdout-update", disabled=not confirmed):
        try:
            result = update_final_holdout(root)
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            streamlit.error(f"Final-holdout update failed: {exc}")
        else:
            streamlit.success(
                f"Processed {len(result.processed_sessions):,} sessions; "
                f"inserted {result.events_inserted:,} events; "
                f"blocked {len(result.blocked_sessions):,} sessions."
            )

    if status.empty:
        streamlit.info("No development final-holdout runs exist.")
        return
    selected_run = streamlit.selectbox("Run ID", status["run_id"].astype(str).unique().tolist())
    run_status = status.loc[status["run_id"].astype(str) == selected_run]
    selected_row = run_status.iloc[0]
    _progress_bars(selected_row)

    run_events = (
        events.loc[events["run_id"].astype(str) == selected_run] if not events.empty else events
    )
    pending = (
        run_events.loc[run_events["event_type"] == "FINAL_HOLDOUT_ENTRY_PENDING"]
        if not run_events.empty
        else run_events
    )
    open_positions = (
        run_events.loc[run_events["event_type"] == "FINAL_HOLDOUT_ENTRY_FILLED"]
        if not run_events.empty
        else run_events
    )
    closed = (
        run_events.loc[run_events["event_type"] == "FINAL_HOLDOUT_EXIT_FILLED"]
        if not run_events.empty
        else run_events
    )
    gates = pd.DataFrame(
        [
            {"gate": metric, "actual": int(selected_row.get(metric, 0) or 0), "required": target}
            for metric, target in PROGRESS_TARGETS.items()
        ]
    )
    integrity = pd.DataFrame(
        [
            {
                "run_id": selected_run,
                "artifact_integrity": selected_row.get("artifact_integrity", ""),
                "backfill_blocked_events": selected_row.get("backfill_blocked_events", 0),
            }
        ]
    )
    tabs = streamlit.tabs(
        [
            "Status",
            "Events",
            "Pending Entries",
            "Open Positions",
            "Closed Positions",
            "Sample Sufficiency",
            "Gate Results",
            "Artifact Integrity",
        ]
    )
    frames = [
        run_status,
        run_events.drop(columns=["payload"], errors="ignore"),
        pending.drop(columns=["payload"], errors="ignore"),
        open_positions.drop(columns=["payload"], errors="ignore"),
        closed.drop(columns=["payload"], errors="ignore"),
        gates,
        gates,
        integrity,
    ]
    for tab, frame in zip(tabs, frames, strict=True):
        with tab:
            streamlit.dataframe(display_frame(frame), width="stretch", hide_index=True)

    positions = pd.concat([pending, open_positions, closed], ignore_index=True)
    streamlit.download_button(
        "Download final-holdout workbook XLSX",
        data=to_xlsx_bytes(
            {
                "run_status": run_status,
                "events": run_events.drop(columns=["payload"], errors="ignore"),
                "positions": positions.drop(columns=["payload"], errors="ignore"),
            }
        ),
        file_name="shadow_final_holdout.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    render_page()
