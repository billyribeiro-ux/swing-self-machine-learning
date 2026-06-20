from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import date_label, whole
from swing_rsi.application.project_status import collect_project_status


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    status = collect_project_status(root)
    render_page_header("Overview", "Local Streamlit presentation layer for Version 1 research.")

    valid = [dataset for dataset in status.datasets if dataset.error is None]
    newest = [pd.Timestamp(dataset.latest_date) for dataset in valid if dataset.latest_date]
    oldest = [pd.Timestamp(dataset.first_date) for dataset in valid if dataset.first_date]

    columns = streamlit.columns(4)
    columns[0].metric("Project version", status.package_version)
    columns[1].metric("Python", status.python_version)
    columns[2].metric("FMP configured", "yes" if status.fmp_configured else "no")
    columns[3].metric("Saved reports", whole(status.saved_report_count))
    columns = streamlit.columns(4)
    columns[0].metric("Datasets", whole(status.raw_ticker_csv_count))
    columns[1].metric("Oldest market-data date", date_label(min(oldest)) if oldest else "n/a")
    columns[2].metric("Newest market-data date", date_label(max(newest)) if newest else "n/a")
    columns[3].metric("Files with load errors", whole(len(status.datasets) - len(valid)))

    streamlit.write(f"Project: **{status.project_name}**")
    streamlit.write(f"Project root: `{status.project_root}`")
    streamlit.write(f"FMP base URL: `{status.fmp_base_url}`")

    streamlit.subheader("Raw Data Files")
    if not status.datasets:
        streamlit.info("No raw ticker CSV files found under data/raw/.")
        return
    rows = [
        {
            "ticker": dataset.ticker,
            "row_count": dataset.row_count,
            "first_date": dataset.first_date,
            "latest_date": dataset.latest_date,
            "file_modified_at_utc": dataset.modified_at_utc,
            "load_status": dataset.error or "ok",
        }
        for dataset in status.datasets
    ]
    display = pd.DataFrame(rows).rename(
        columns={
            "ticker": "Ticker",
            "row_count": "Row count",
            "first_date": "First date",
            "latest_date": "Latest date",
            "file_modified_at_utc": "File modified time",
            "load_status": "Load status",
        }
    )
    streamlit.dataframe(display, width="stretch", hide_index=True)
