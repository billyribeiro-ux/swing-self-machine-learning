from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from dashboard.ui.cache import clear_dataset_cache, load_dataset_cached
from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.errors import show_expected_error, show_unexpected_error
from dashboard.ui.formatting import date_label, display_frame, whole
from swing_rsi.application.datasets import (
    DatasetSummary,
    DownloadResult,
    StructuralAudit,
    discover_raw_datasets,
    download_daily_to_raw,
    normalize_ticker,
    slice_date_window,
    structural_audit_frame,
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


def _ticker_map(datasets: tuple[DatasetSummary, ...]) -> dict[str, DatasetSummary]:
    return {dataset.ticker: dataset for dataset in datasets}


def dataset_display_label(dataset: DatasetSummary) -> str:
    return dataset.ticker


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return pd.Timestamp(value).date()


def _stale_days(latest_date: str | None) -> int | None:
    latest = _parse_date(latest_date)
    if latest is None:
        return None
    return max((date.today() - latest).days, 0)


def _default_update_start(dataset: DatasetSummary) -> date:
    latest = _parse_date(dataset.latest_date)
    if latest is None:
        return _years_ago(10)
    return latest - timedelta(days=14)


def _render_dataset_status(datasets: tuple[DatasetSummary, ...]) -> None:
    streamlit = st()
    valid = [dataset for dataset in datasets if dataset.error is None]
    latest_dates = [pd.Timestamp(dataset.latest_date) for dataset in valid if dataset.latest_date]
    oldest_dates = [pd.Timestamp(dataset.first_date) for dataset in valid if dataset.first_date]
    columns = streamlit.columns(4)
    columns[0].metric("Datasets", len(valid))
    columns[1].metric(
        "Oldest stored date",
        date_label(min(oldest_dates)) if oldest_dates else "n/a",
    )
    columns[2].metric(
        "Newest stored date",
        date_label(max(latest_dates)) if latest_dates else "n/a",
    )
    columns[3].metric(
        "Files with load errors", len([dataset for dataset in datasets if dataset.error])
    )


def _result_rows(result: DownloadResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Metric": "Normalized ticker", "Value": result.ticker},
            {"Metric": "Existing rows", "Value": whole(result.existing_rows)},
            {"Metric": "Downloaded rows", "Value": whole(result.downloaded_rows)},
            {"Metric": "Replaced dates", "Value": whole(result.replaced_dates)},
            {"Metric": "Inserted dates", "Value": whole(result.inserted_dates)},
            {"Metric": "Final rows", "Value": whole(result.final_rows)},
            {"Metric": "First final date", "Value": result.first_date},
            {"Metric": "Last final date", "Value": result.last_date},
            {"Metric": "Saved path", "Value": str(result.saved_path)},
        ]
    )


def _run_update(
    root: Path,
    *,
    ticker: str,
    start: date,
    end: date,
    use_end: bool,
) -> DownloadResult:
    result = download_daily_to_raw(
        root,
        ticker,
        start=start.isoformat(),
        end=end.isoformat() if use_end else None,
        provider="fmp",
    )
    clear_dataset_cache()
    return result


def _render_download_forms(
    root: Path,
    datasets: tuple[DatasetSummary, ...],
    *,
    fmp_configured: bool,
) -> None:
    streamlit = st()
    update_tab, custom_tab = streamlit.tabs(
        ["Update Existing Dataset", "Download New or Custom Range"]
    )

    result: DownloadResult | None = None
    ticker_error: str | None = None

    with update_tab:
        if not datasets:
            streamlit.info("No existing datasets are available to update.")
        else:
            by_ticker = _ticker_map(datasets)
            selected_ticker = streamlit.selectbox(
                "Existing ticker",
                options=tuple(by_ticker.keys()),
                key="update_existing_ticker",
            )
            selected = by_ticker[str(selected_ticker)]
            columns = streamlit.columns(4)
            columns[0].metric("Ticker", selected.ticker)
            columns[1].metric("Current first date", selected.first_date or "n/a")
            columns[2].metric("Current latest date", selected.latest_date or "n/a")
            columns[3].metric("Rows", whole(selected.row_count))
            stale = _stale_days(selected.latest_date)
            if stale is not None:
                streamlit.info(
                    f"Stored data is {stale:,} calendar days behind today's date. "
                    "This is not an exchange-calendar completeness check."
                )
            with streamlit.form("update_existing_dataset_form"):
                start = streamlit.date_input(
                    "Request start date",
                    value=_default_update_start(selected),
                    key="update_existing_start",
                )
                end = streamlit.date_input(
                    "Request end date",
                    value=date.today(),
                    key="update_existing_end",
                )
                use_end = streamlit.checkbox(
                    "Use end date in request",
                    value=True,
                    key="update_existing_use_end",
                )
                streamlit.caption(
                    "Update merges the requested FMP rows into the existing CSV. Older stored "
                    "history is preserved and overlapping dates are replaced by the new download."
                )
                submitted = streamlit.form_submit_button(
                    "Update Existing Dataset",
                    disabled=not fmp_configured,
                )
            if submitted:
                if start > end:
                    show_expected_error("Update request start date must be on or before end date.")
                else:
                    try:
                        result = _run_update(
                            root,
                            ticker=selected.ticker,
                            start=start,
                            end=end,
                            use_end=use_end,
                        )
                    except (FileNotFoundError, RuntimeError, ValueError) as exc:
                        show_expected_error(f"Update failed: {exc}")
                    except Exception as exc:  # pragma: no cover - defensive dashboard guard
                        show_unexpected_error(exc, context="update_existing_dataset")

    with custom_tab:
        with streamlit.form("download_custom_range_form"):
            raw_symbol = streamlit.text_input(
                "Ticker",
                value="AAPL",
                key="download_custom_ticker",
                autocomplete="off",
            )
            streamlit.text_input(
                "Provider",
                value="FMP",
                disabled=True,
                key="download_custom_provider",
                autocomplete="off",
            )
            try:
                normalized_symbol = normalize_ticker(raw_symbol)
                streamlit.caption(f"Normalized provider symbol: {normalized_symbol}")
            except ValueError as exc:
                normalized_symbol = ""
                ticker_error = str(exc)
                streamlit.warning(ticker_error)
            start = streamlit.date_input(
                "Start date",
                value=_years_ago(10),
                key="download_custom_start",
            )
            end = streamlit.date_input(
                "End date",
                value=date.today(),
                key="download_custom_end",
            )
            use_end = streamlit.checkbox(
                "Use end date in request",
                value=True,
                key="download_custom_use_end",
            )
            streamlit.caption(
                "Custom downloads use the same merge-safe storage service. Existing history for "
                "the ticker is not destroyed."
            )
            submitted = streamlit.form_submit_button(
                "Download New or Custom Range",
                disabled=(not fmp_configured or ticker_error is not None),
            )
        if submitted and normalized_symbol:
            if start > end:
                show_expected_error("Download request start date must be on or before end date.")
            else:
                try:
                    result = _run_update(
                        root,
                        ticker=normalized_symbol,
                        start=start,
                        end=end,
                        use_end=use_end,
                    )
                except (FileNotFoundError, RuntimeError, ValueError) as exc:
                    show_expected_error(f"Download failed: {exc}")
                except Exception as exc:  # pragma: no cover - defensive dashboard guard
                    show_unexpected_error(exc, context="download_custom_range")

    if not fmp_configured:
        streamlit.info("FMP is not configured. Run `./scripts/configure_fmp.sh` first.")
    if result is not None:
        streamlit.success(f"Saved merged dataset for {result.ticker}.")
        streamlit.dataframe(_result_rows(result), width="stretch", hide_index=True)


def _audit_checks(audit: StructuralAudit) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Metric": "Row count", "Value": whole(audit.row_count)},
            {"Metric": "First date", "Value": audit.first_date or "n/a"},
            {"Metric": "Last date", "Value": audit.last_date or "n/a"},
            {"Metric": "Duplicate-date rows", "Value": whole(audit.duplicate_dates)},
            {
                "Metric": "Missing required values",
                "Value": whole(audit.missing_required_values),
            },
            {"Metric": "Zero-volume rows", "Value": whole(audit.zero_volume_rows)},
            {"Metric": "Invalid OHLC rows", "Value": whole(audit.invalid_ohlc_rows)},
            {
                "Metric": "Nonpositive-price rows",
                "Value": whole(audit.nonpositive_price_rows),
            },
            {
                "Metric": "Missing required columns",
                "Value": ", ".join(audit.missing_required_columns) or "none",
            },
        ]
    )


def _render_audit_scope(audit: StructuralAudit) -> None:
    streamlit = st()
    metric_columns = streamlit.columns(4)
    metric_columns[0].metric("Rows", whole(audit.row_count))
    metric_columns[1].metric("First date", audit.first_date or "n/a")
    metric_columns[2].metric("Last date", audit.last_date or "n/a")
    metric_columns[3].metric("Duplicate-date rows", whole(audit.duplicate_dates))

    streamlit.dataframe(_audit_checks(audit), width="stretch", hide_index=True)
    streamlit.subheader("Ten Largest Absolute Close-To-Close Moves")
    streamlit.dataframe(display_frame(audit.largest_close_moves), width="stretch", hide_index=True)
    first_tab, last_tab = streamlit.tabs(["First Five Rows", "Last Five Rows"])
    with first_tab:
        streamlit.dataframe(display_frame(audit.first_rows), width="stretch", hide_index=True)
    with last_tab:
        streamlit.dataframe(display_frame(audit.last_rows), width="stretch", hide_index=True)


def _render_window_notice(
    frame: pd.DataFrame,
    window: pd.DataFrame,
    *,
    requested_start: date,
    requested_end: date,
) -> None:
    streamlit = st()
    raw_first = pd.Timestamp(frame.index.min()).date()
    raw_last = pd.Timestamp(frame.index.max()).date()
    effective_start = pd.Timestamp(window.index.min()).date() if not window.empty else None
    effective_end = pd.Timestamp(window.index.max()).date() if not window.empty else None
    columns = streamlit.columns(4)
    columns[0].metric("Requested start", requested_start.isoformat())
    columns[1].metric("Requested end", requested_end.isoformat())
    columns[2].metric("Effective start", effective_start.isoformat() if effective_start else "n/a")
    columns[3].metric("Effective end", effective_end.isoformat() if effective_end else "n/a")
    if requested_start < raw_first or requested_end > raw_last:
        streamlit.warning(
            "The requested research window extends outside raw-file coverage. The selected-window "
            "audit uses only available rows and does not modify the raw CSV."
        )


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    status = collect_project_status(root)
    render_page_header("Data and Audit", "Download FMP daily bars and inspect CSV structure.")
    streamlit.caption("No exchange-calendar completeness audit exists yet.")

    datasets = discover_raw_datasets(root)
    streamlit.subheader("Dataset Status Summary")
    _render_dataset_status(datasets)

    streamlit.subheader("Dataset Download And Update")
    _render_download_forms(root, datasets, fmp_configured=status.fmp_configured)

    datasets = discover_raw_datasets(root)
    if not datasets:
        streamlit.info("No raw CSV files are available under data/raw/.")
        return

    streamlit.subheader("Dataset Selector")
    by_ticker = _ticker_map(datasets)
    selected_ticker = streamlit.selectbox(
        "Dataset",
        options=tuple(by_ticker.keys()),
        key="audit_dataset",
    )
    selected = by_ticker[str(selected_ticker)]
    stale = _stale_days(selected.latest_date)
    columns = streamlit.columns(4)
    columns[0].metric("Ticker", dataset_display_label(selected))
    columns[1].metric("Raw first date", selected.first_date or "n/a")
    columns[2].metric("Raw latest date", selected.latest_date or "n/a")
    columns[3].metric("Calendar days stale", whole(stale) if stale is not None else "n/a")

    streamlit.subheader("Research-Window Controls")
    preset = streamlit.selectbox(
        "Research-window preset",
        ("3 years", "5 years", "10 years", "15 years", "Custom"),
        index=2,
        key="audit_window_preset",
    )
    if preset == "Custom":
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
    if window_start > window_end:
        streamlit.error("Custom research-window start must be on or before the end date.")
        return

    try:
        frame = load_dataset_cached(selected.path)
        window = slice_date_window(frame, start=window_start, end=window_end)
    except (FileNotFoundError, ValueError) as exc:
        show_expected_error(f"Dataset cannot be loaded: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive dashboard guard
        show_unexpected_error(exc, context="load_audit_dataset")
        return

    streamlit.write(
        f"Full raw-file coverage: {date_label(frame.index.min())} through "
        f"{date_label(frame.index.max())}; rows: {whole(len(frame))}."
    )
    _render_window_notice(
        frame,
        window,
        requested_start=window_start,
        requested_end=window_end,
    )
    if window.empty:
        streamlit.warning("The selected research window contains no available rows.")

    selected_audit = structural_audit_frame(window)
    raw_audit = structural_audit_frame(frame, path=selected.path)
    selected_tab, raw_tab = streamlit.tabs(["Selected Research Window", "Full Raw File"])
    with selected_tab:
        _render_audit_scope(selected_audit)
    with raw_tab:
        _render_audit_scope(raw_audit)


if __name__ == "__main__":
    render_page()
