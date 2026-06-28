from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.ui.components import (
    render_page_guidance,
    render_page_header,
    render_status_cards,
    repository_root,
    st,
)
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_csv_bytes, to_xlsx_bytes
from swing_rsi.application.dashboard_service import (
    final_holdout_runs_frame,
    model_generations_frame,
    operational_status_frame,
    overview_metrics,
    regime_cache_detail_frames,
    reports_inventory_frame,
    scanner_snapshot_list_frame,
)


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


def _render_regime_cache_section(root: str | Path) -> None:
    streamlit = st()
    details = regime_cache_detail_frames(root)
    summary = details["summary"]
    streamlit.subheader("Regime KMeans Cache")
    streamlit.caption(
        "The regime cache preserves exact current feature semantics. It only avoids recomputing "
        "historical expanding KMeans labels when inputs and configuration are unchanged."
    )
    if summary.empty:
        streamlit.info("Regime cache: Not found. Run build-features once to create the cache.")
        return
    latest = summary.iloc[0]
    status = str(latest.get("status", "UNKNOWN"))
    if status == "NOT_FOUND":
        streamlit.info("Regime cache: Not found. Run build-features once to create the cache.")
    render_status_cards(
        {
            "Regime cache status": status,
            "Last cached date": latest.get("last_cached_date", "Not available"),
            "KMeans fits avoided": _display_count(latest.get("kmeans_fits_avoided")),
            "KMeans fits performed": _display_count(latest.get("kmeans_fits_performed")),
            "Regime runtime": _display_seconds(latest.get("regime_runtime_seconds")),
            "Validity reason": latest.get("validity_reason", "Not available"),
        },
        columns=3,
    )
    streamlit.info(str(latest.get("next_action", "Review regime cache metadata.")))
    streamlit.caption(
        f"Forced rebuild method: `{latest.get('forced_rebuild_method', 'Not available')}`"
    )
    streamlit.dataframe(display_frame(summary), width="stretch", hide_index=True)
    streamlit.subheader("Regime Cache Metadata")
    streamlit.dataframe(display_frame(details["metadata"]), width="stretch", hide_index=True)
    streamlit.subheader("Regime Input Columns")
    streamlit.dataframe(display_frame(details["input_columns"]), width="stretch", hide_index=True)
    streamlit.subheader("Regime KMeans Configuration")
    streamlit.dataframe(display_frame(details["kmeans_config"]), width="stretch", hide_index=True)
    columns = streamlit.columns(2)
    columns[0].download_button(
        "Download regime cache CSV",
        data=to_csv_bytes(details["metadata"]),
        file_name="regime_kmeans_cache_metadata.csv",
        mime="text/csv",
        disabled=details["metadata"].empty,
    )
    columns[1].download_button(
        "Download regime cache XLSX",
        data=to_xlsx_bytes(details),
        file_name="regime_kmeans_cache_diagnostics.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not any(not frame.empty for frame in details.values()),
    )


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Developer Diagnostics",
        "Read-only repository, generation, scanner, final-holdout, and report diagnostics.",
    )
    render_page_guidance(
        tells_you=(
            "Development infrastructure state that supports the signal-first pages without making "
            "it the home view."
        ),
        next_action=(
            "Use this page only when validating local state, troubleshooting reports, or checking "
            "the frozen operational run summary."
        ),
    )

    metrics = overview_metrics(root)
    metric_table = pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()])
    streamlit.subheader("Development Metrics")
    streamlit.dataframe(display_frame(metric_table), width="stretch", hide_index=True)
    render_table_downloads(metric_table, basename="developer_metrics", label="metrics")

    _render_regime_cache_section(root)

    generations = model_generations_frame(root)
    streamlit.subheader("Model Generations")
    streamlit.dataframe(display_frame(generations), width="stretch", hide_index=True)
    render_table_downloads(generations, basename="developer_generations", label="generations")

    snapshots = scanner_snapshot_list_frame(root)
    streamlit.subheader("Scanner Snapshots")
    streamlit.dataframe(display_frame(snapshots), width="stretch", hide_index=True)
    render_table_downloads(snapshots, basename="developer_scanner_snapshots", label="snapshots")

    final_holdout = final_holdout_runs_frame(root)
    streamlit.subheader("Final-Holdout Runs")
    streamlit.dataframe(display_frame(final_holdout), width="stretch", hide_index=True)
    render_table_downloads(final_holdout, basename="developer_final_holdout", label="final_holdout")

    operational = operational_status_frame()
    streamlit.subheader("Operational Frozen Run Read-Only")
    streamlit.dataframe(display_frame(operational), width="stretch", hide_index=True)

    reports = reports_inventory_frame(root)
    streamlit.subheader("Reports Inventory")
    streamlit.dataframe(display_frame(reports), width="stretch", hide_index=True)


if __name__ == "__main__":
    render_page()
