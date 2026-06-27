from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import scanner_rows_frame, scanner_snapshot_list_frame
from swing_rsi.application.engine_service import run_live_scanner


def _filter_rows(frame: pd.DataFrame) -> pd.DataFrame:
    streamlit = st()
    if frame.empty:
        return frame
    columns = streamlit.columns(5)
    scope = columns[0].multiselect(
        "Scope",
        sorted(
            frame.get("product_class_scope", pd.Series(dtype=str)).dropna().astype(str).unique()
        ),
    )
    direction = columns[1].multiselect(
        "Direction",
        sorted(frame.get("direction", pd.Series(dtype=str)).dropna().astype(str).unique()),
    )
    candidate_status = columns[2].multiselect(
        "Candidate status",
        sorted(frame.get("candidate_status", pd.Series(dtype=str)).dropna().astype(str).unique()),
    )
    rejection_reason = columns[3].multiselect(
        "Rejection reason",
        sorted(frame.get("exclusion_reason", pd.Series(dtype=str)).dropna().astype(str).unique()),
    )
    ticker = columns[4].text_input("Ticker", value="")
    filtered = frame.copy()
    if scope and "product_class_scope" in filtered:
        filtered = filtered.loc[filtered["product_class_scope"].astype(str).isin(scope)]
    if direction and "direction" in filtered:
        filtered = filtered.loc[filtered["direction"].astype(str).isin(direction)]
    if candidate_status and "candidate_status" in filtered:
        filtered = filtered.loc[filtered["candidate_status"].astype(str).isin(candidate_status)]
    if rejection_reason and "exclusion_reason" in filtered:
        filtered = filtered.loc[filtered["exclusion_reason"].astype(str).isin(rejection_reason)]
    if ticker and "ticker" in filtered:
        filtered = filtered.loc[filtered["ticker"].astype(str).str.contains(ticker.upper())]
    return filtered


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Scanner Snapshots",
        "Immutable scanner snapshots, candidate rows, rejection reasons, and attribution summaries.",
    )
    snapshots = scanner_snapshot_list_frame(root)
    streamlit.subheader("Snapshot List")
    streamlit.dataframe(display_frame(snapshots), width="stretch", hide_index=True)
    render_table_downloads(snapshots, basename="scanner_snapshots", label="snapshots")

    streamlit.subheader("Optional Scanner Run")
    streamlit.warning(
        "Development-only scanner run. This mutates development scanner artifacts and SQLite."
    )
    include_challengers = streamlit.checkbox("Include challengers", value=True)
    confirmed = streamlit.checkbox(
        "I understand this runs the scanner in the development worktree."
    )
    if streamlit.button("Run scanner", disabled=not confirmed):
        try:
            snapshot = run_live_scanner(root, include_challengers=include_challengers)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            streamlit.error(f"Scanner failed: {exc}")
        else:
            streamlit.success(f"Scanner snapshot saved: {snapshot.scan_id}")

    scan_ids = snapshots["scan_id"].astype(str).tolist() if not snapshots.empty else []
    selected_scan = streamlit.selectbox("Scan ID", scan_ids) if scan_ids else None
    rows = scanner_rows_frame(root, selected_scan)
    filtered = _filter_rows(rows)
    visible_columns = [
        "ticker",
        "scope",
        "product_class_scope",
        "direction",
        "model_id",
        "calibrated_probability",
        "expected_return",
        "expected_mfe",
        "expected_mae",
        "ood_warning",
        "candidate_status",
        "exclusion_reason",
        "top_attribution_categories",
        "feature_snapshot_hash",
        "selection_policy_result",
    ]
    visible = filtered[[column for column in visible_columns if column in filtered.columns]]
    streamlit.subheader("Snapshot Drilldown")
    streamlit.dataframe(display_frame(visible), width="stretch", hide_index=True)
    render_table_downloads(visible, basename="scanner_snapshot_rows", label="candidates")


if __name__ == "__main__":
    render_page()
