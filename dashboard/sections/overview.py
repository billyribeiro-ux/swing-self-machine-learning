from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    OPERATIONAL_REPOSITORY,
    operational_status_frame,
    overview_metrics,
    overview_sections,
    regime_cache_status_frame,
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


def _display_count(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "Not available"


def _display_seconds(value: object) -> str:
    try:
        return f"{float(value):.2f} seconds"
    except (TypeError, ValueError):
        return "Not available"


def _render_regime_cache_overview(root: str | Path) -> None:
    streamlit = st()
    frame = regime_cache_status_frame(root)
    streamlit.subheader("Regime KMeans Cache")
    streamlit.caption(
        "The regime cache preserves exact current feature semantics. It only avoids recomputing "
        "historical expanding KMeans labels when inputs and configuration are unchanged."
    )
    if frame.empty:
        streamlit.info("Regime cache: Not found. Run build-features once to create the cache.")
        return
    row = frame.iloc[0]
    status = str(row.get("status", "UNKNOWN"))
    if status == "NOT_FOUND":
        streamlit.info("Regime cache: Not found. Run build-features once to create the cache.")
    columns = streamlit.columns(5)
    columns[0].metric("Regime cache status", status)
    columns[1].metric("Last cached date", str(row.get("last_cached_date", "Not available")))
    columns[2].metric("KMeans fits avoided", _display_count(row.get("kmeans_fits_avoided")))
    columns[3].metric("Regime runtime", _display_seconds(row.get("regime_runtime_seconds")))
    columns[4].metric("Cache validity reason", str(row.get("validity_reason", "Not available")))
    streamlit.info(str(row.get("next_action", "Review regime cache metadata.")))


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
    _render_regime_cache_overview(root)

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
