from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    OPERATIONAL_REPOSITORY,
    operational_status_frame,
    overview_metrics,
    overview_sections,
)


def _metric_grid(values: dict[str, object]) -> None:
    streamlit = st()
    items = list(values.items())
    for offset in range(0, len(items), 4):
        columns = streamlit.columns(4)
        for column, (label, value) in zip(columns, items[offset : offset + 4], strict=False):
            column.metric(label.replace("_", " ").title(), str(value))


def _section_table(title: str, frame: pd.DataFrame, basename: str) -> None:
    streamlit = st()
    streamlit.subheader(title)
    if frame.empty:
        streamlit.info("No local records available.")
        return
    streamlit.dataframe(display_frame(frame), width="stretch", hide_index=True)
    render_table_downloads(frame, basename=basename, label=title.lower().replace(" ", "_"))


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Overview",
        "Development state, frozen operational status, blockers, and next review command.",
    )
    streamlit.write(f"Development repository: `{root}`")
    streamlit.write(f"Operational repository: `{OPERATIONAL_REPOSITORY}`")

    metrics = overview_metrics(root)
    operational = operational_status_frame()
    if not operational.empty:
        metrics["operational_run_status_read_only"] = operational.iloc[0]["current_status"]
    _metric_grid(metrics)

    streamlit.subheader("Operational Frozen Run Summary")
    streamlit.dataframe(display_frame(operational), width="stretch", hide_index=True)

    sections = overview_sections(root)
    _section_table(
        "Newest Generation Summary",
        sections["newest_generation_summary"],
        "overview_newest_generation_summary",
    )
    _section_table(
        "Latest Scanner Snapshot Summary",
        sections["latest_scanner_snapshot_summary"],
        "overview_latest_scanner_snapshot",
    )
    _section_table(
        "Latest Final-Holdout Status",
        sections["latest_final_holdout_status"],
        "overview_latest_final_holdout",
    )
    _section_table("Key Blockers", sections["key_blockers"], "overview_key_blockers")
    _section_table(
        "Next Operational Command",
        sections["next_operational_command"],
        "overview_next_operational_command",
    )


if __name__ == "__main__":
    render_page()
