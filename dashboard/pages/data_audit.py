from __future__ import annotations

from datetime import date

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from swing_rsi.application.datasets import (
    discover_raw_datasets,
    download_daily_to_raw,
    load_raw_dataset,
    slice_date_window,
    structural_audit_csv,
)
from swing_rsi.application.project_status import collect_project_status


def _years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


def _window_start_from_preset(preset: str) -> date:
    if preset == "3 years":
        return _years_ago(3)
    if preset == "5 years":
        return _years_ago(5)
    if preset == "15 years":
        return _years_ago(15)
    return _years_ago(10)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    status = collect_project_status(root)
    render_page_header("Data and Audit", "Download FMP daily bars and inspect raw CSV structure.")

    streamlit.subheader("Download Or Update")
    with streamlit.form("download_form"):
        ticker = (
            streamlit.text_input(
                "Ticker",
                value="AAPL",
                key="download_ticker",
                autocomplete="off",
            )
            .strip()
            .upper()
        )
        streamlit.text_input(
            "Provider",
            value="FMP",
            disabled=True,
            key="download_provider",
            autocomplete="off",
        )
        start = streamlit.date_input("Start date", value=_years_ago(10), key="download_start")
        end = streamlit.date_input("End date", value=date.today(), key="download_end")
        use_end = streamlit.checkbox(
            "Use end date in download request",
            value=True,
            key="download_use_end",
        )
        streamlit.caption(
            "The end date stays editable. Uncheck this only when the provider request should omit "
            "an end date."
        )
        submitted = streamlit.form_submit_button(
            "Download/update", disabled=not status.fmp_configured
        )

    if not status.fmp_configured:
        streamlit.info("FMP is not configured. Run `./scripts/configure_fmp.sh` first.")
    if submitted:
        try:
            result = download_daily_to_raw(
                root,
                ticker,
                start=start.isoformat(),
                end=end.isoformat() if use_end else None,
                provider="fmp",
            )
        except (RuntimeError, ValueError) as exc:
            streamlit.error(str(exc))
        else:
            streamlit.success(
                f"Updated {result.ticker}: downloaded {result.downloaded_rows:,} rows, "
                f"started with {result.existing_rows:,}, replaced {result.replaced_dates:,} "
                f"dates, inserted {result.inserted_dates:,}, final rows {result.final_rows:,} "
                f"from {result.first_date} through {result.last_date} to {result.saved_path}"
            )

    streamlit.subheader("Structural Audit")
    datasets = discover_raw_datasets(root)
    if not datasets:
        streamlit.info("No raw CSV files are available under data/raw/.")
        return

    labels = {f"{dataset.ticker} - {dataset.path.name}": dataset for dataset in datasets}
    selected_label = streamlit.selectbox(
        "Raw CSV",
        options=tuple(labels.keys()),
        key="audit_raw_csv",
    )
    selected = labels[str(selected_label)]
    streamlit.write(
        f"Raw-file coverage: {selected.first_date or 'n/a'} through "
        f"{selected.latest_date or 'n/a'}; rows: {selected.row_count or 'n/a'}"
    )

    preset = streamlit.selectbox(
        "Research-window preset",
        ("3 years", "5 years", "10 years", "15 years", "custom"),
        index=2,
        key="audit_window_preset",
    )
    if preset == "custom":
        window_start = streamlit.date_input(
            "Custom start",
            value=_years_ago(10),
            key="audit_custom_start",
        )
        window_end = streamlit.date_input(
            "Custom end",
            value=date.today(),
            key="audit_custom_end",
        )
    else:
        window_start = _window_start_from_preset(str(preset))
        window_end = date.today()
        streamlit.caption(f"Selected research window: {window_start} through {window_end}")

    try:
        audit = structural_audit_csv(selected.path)
        frame = load_raw_dataset(selected.path)
        window = slice_date_window(frame, start=window_start, end=window_end)
    except (FileNotFoundError, ValueError) as exc:
        streamlit.error(str(exc))
        return

    metric_columns = streamlit.columns(4)
    metric_columns[0].metric("Rows", audit.row_count)
    metric_columns[1].metric("First date", audit.first_date or "n/a")
    metric_columns[2].metric("Last date", audit.last_date or "n/a")
    metric_columns[3].metric("Rows in selected window", len(window))

    checks = pd.DataFrame(
        [
            {"metric": "Duplicate date rows", "value": str(audit.duplicate_dates)},
            {"metric": "Missing required values", "value": str(audit.missing_required_values)},
            {"metric": "Zero-volume rows", "value": str(audit.zero_volume_rows)},
            {"metric": "Invalid OHLC rows", "value": str(audit.invalid_ohlc_rows)},
            {"metric": "Nonpositive-price rows", "value": str(audit.nonpositive_price_rows)},
            {
                "metric": "Missing required columns",
                "value": ", ".join(audit.missing_required_columns) or "none",
            },
        ]
    )
    streamlit.dataframe(checks, width="stretch")

    streamlit.subheader("Ten Largest Absolute Close-To-Close Moves")
    streamlit.dataframe(audit.largest_close_moves, width="stretch")
    first_tab, last_tab = streamlit.tabs(["First five rows", "Last five rows"])
    with first_tab:
        streamlit.dataframe(audit.first_rows, width="stretch")
    with last_tab:
        streamlit.dataframe(audit.last_rows, width="stretch")


if __name__ == "__main__":
    render_page()
