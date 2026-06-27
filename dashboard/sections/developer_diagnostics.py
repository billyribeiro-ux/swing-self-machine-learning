from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    final_holdout_runs_frame,
    model_generations_frame,
    operational_status_frame,
    overview_metrics,
    reports_inventory_frame,
    scanner_snapshot_list_frame,
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
