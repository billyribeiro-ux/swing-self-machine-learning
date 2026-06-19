from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_navigation, render_page_header, repository_root, st
from swing_rsi.application.project_status import collect_project_status


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    status = collect_project_status(root)
    render_page_header("Overview", "Local Streamlit presentation layer for Version 1 research.")

    left, right = streamlit.columns(2)
    with left:
        streamlit.metric("Project", status.project_name)
        streamlit.metric("Package version", status.package_version)
        streamlit.metric("Python", status.python_version)
        streamlit.write(f"Project root: `{status.project_root}`")
    with right:
        streamlit.metric("FMP API key configured", "yes" if status.fmp_configured else "no")
        streamlit.write(f"FMP base URL: `{status.fmp_base_url}`")
        streamlit.metric("Raw ticker CSV files", status.raw_ticker_csv_count)
        streamlit.metric("Saved reports", status.saved_report_count)

    render_navigation()

    streamlit.subheader("Raw Data Files")
    if not status.datasets:
        streamlit.info("No raw ticker CSV files found under data/raw/.")
        return
    rows = [{**dataset.__dict__, "path": str(dataset.path)} for dataset in status.datasets]
    streamlit.dataframe(pd.DataFrame(rows), width="stretch")
