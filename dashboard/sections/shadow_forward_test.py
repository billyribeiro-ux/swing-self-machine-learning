from __future__ import annotations

import pandas as pd

from dashboard.ui.components import (
    render_page_guidance,
    render_page_header,
    repository_root,
    st,
)
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.application.dashboard_service import (
    operational_status_frame,
    shadow_forward_events_frame,
    shadow_forward_status_frame,
    shadow_next_steps_frame,
    shadow_position_frames,
)

PROGRESS_TARGETS: tuple[tuple[str, str, int], ...] = (
    ("matured_outcomes", "100 matured outcomes", 100),
    ("distinct_signal_dates", "60 distinct signal dates", 60),
    ("observation_sessions", "126 sessions", 126),
    ("calendar_months", "4 months", 4),
    ("positive_outcomes", "20 positive outcomes", 20),
    ("negative_outcomes", "20 negative outcomes", 20),
)


def _progress_value(value: object, target: int) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(numeric / float(target), 1.0))


def _render_progress(frame: pd.DataFrame) -> None:
    streamlit = st()
    if frame.empty:
        streamlit.info("No development shadow final-holdout runs are available.")
        return
    selected_run = streamlit.selectbox("Progress run", frame["run_id"].astype(str).tolist())
    row = frame.loc[frame["run_id"].astype(str) == selected_run].iloc[0]
    for column, label, target in PROGRESS_TARGETS:
        value = row.get(column, 0)
        streamlit.progress(
            _progress_value(value, target),
            text=f"{label}: {value}/{target}",
        )


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Shadow Forward Test",
        "Prospective shadow validation runs, events, pending entries, and matured outcomes.",
    )
    render_page_guidance(
        tells_you=(
            "Which models are collecting prospective final-holdout evidence and whether rows are "
            "pending, open, closed, or matured."
        ),
        next_action=(
            "Use the progress bars and next-event table to see what evidence is still missing. "
            "Updates remain manual from Engine Commands."
        ),
    )
    streamlit.warning(
        "Ordinary paper forward test is separate from prospective final holdout. "
        "Development shadow validation only. No brokerage order is placed."
    )

    status = shadow_forward_status_frame(root)
    operational = operational_status_frame()
    events = shadow_forward_events_frame(root)
    positions = shadow_position_frames(root)
    next_steps = shadow_next_steps_frame(root)

    streamlit.subheader("Development Shadow Runs")
    streamlit.dataframe(display_frame(status), width="stretch", hide_index=True)
    render_table_downloads(status, basename="shadow_forward_status", label="run_status")

    streamlit.subheader("Operational Frozen Run Status")
    streamlit.dataframe(display_frame(operational), width="stretch", hide_index=True)

    streamlit.subheader("Final-Holdout Sample Progress")
    _render_progress(status)

    streamlit.subheader("What happens next?")
    streamlit.dataframe(display_frame(next_steps), width="stretch", hide_index=True)

    streamlit.subheader("Event History")
    streamlit.dataframe(display_frame(events), width="stretch", hide_index=True)
    render_table_downloads(events, basename="shadow_forward_events", label="events")

    for name, frame in positions.items():
        streamlit.subheader(name.replace("_", " ").title())
        streamlit.dataframe(display_frame(frame), width="stretch", hide_index=True)
        render_table_downloads(frame, basename=f"shadow_{name}", label=name)

    streamlit.download_button(
        "Download shadow forward workbook XLSX",
        data=to_xlsx_bytes(
            {
                "run_status": status,
                "events": events,
                "pending_entries": positions.get("pending_entries", pd.DataFrame()),
                "open_positions": positions.get("open_positions", pd.DataFrame()),
                "closed_positions": positions.get("closed_positions", pd.DataFrame()),
            }
        ),
        file_name="shadow_forward_test.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=status.empty and events.empty,
    )


if __name__ == "__main__":
    render_page()
