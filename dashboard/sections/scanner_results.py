from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    scanner_results_frame,
    scanner_snapshot_list_frame,
)

REJECTION_REASONS: tuple[str, ...] = (
    "model_not_promoted",
    "required_path_heads_unavailable",
    "OOD rejection",
    "product_class_scope_mismatch",
    "final_holdout_missing",
    "gate failure",
    "policy threshold failure",
)


def _options(frame: pd.DataFrame, column: str) -> list[str]:
    if frame.empty or column not in frame.columns:
        return []
    return sorted(frame[column].dropna().astype(str).unique().tolist())


def _filter(frame: pd.DataFrame) -> pd.DataFrame:
    streamlit = st()
    if frame.empty:
        return frame
    columns = streamlit.columns(5)
    scan_id = columns[0].multiselect("Scan ID", _options(frame, "scan_id"))
    scope = columns[1].multiselect("Scope", _options(frame, "scope"))
    direction = columns[2].multiselect("Direction", _options(frame, "direction"))
    status = columns[3].multiselect("Status", _options(frame, "status"))
    classification = columns[4].multiselect(
        "Candidate classification",
        _options(frame, "candidate_classification"),
    )
    columns = streamlit.columns(3)
    ticker = columns[0].multiselect("Ticker", _options(frame, "ticker"))
    model = columns[1].multiselect("Model", _options(frame, "model"))
    rejection = columns[2].multiselect("Rejection reason", _options(frame, "rejection_reason"))
    filtered = frame.copy()
    for column, values in (
        ("scan_id", scan_id),
        ("scope", scope),
        ("direction", direction),
        ("status", status),
        ("candidate_classification", classification),
        ("ticker", ticker),
        ("model", model),
        ("rejection_reason", rejection),
    ):
        if values:
            filtered = filtered.loc[filtered[column].astype(str).isin(values)]
    return filtered


def _rejection_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if frame.empty or "rejection_reason" not in frame.columns:
        return pd.DataFrame({"reason": REJECTION_REASONS, "count": [0] * len(REJECTION_REASONS)})
    text = frame["rejection_reason"].fillna("").astype(str)
    for reason in REJECTION_REASONS:
        count = int(text.str.contains(reason, case=False, regex=False).sum())
        rows.append({"reason": reason, "count": count})
    return pd.DataFrame(rows)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Scanner Results",
        "Scanner candidate rows, shadow/rejected classification, OOD warnings, and rejection reasons.",
    )
    render_page_guidance(
        tells_you=(
            "Which scanner candidates were actionable, shadow-only, rejected, or research-only in "
            "local snapshots and prospective events."
        ),
        next_action=(
            "Use rejection summaries to understand why candidates did not become live actionable, "
            "then open Candidate Detail for row-level evidence."
        ),
    )
    streamlit.info(
        "Use Scanner candidate for research rows. Rejected rows are not labeled signals."
    )

    snapshots = scanner_snapshot_list_frame(root)
    streamlit.subheader("Snapshot List")
    streamlit.dataframe(display_frame(snapshots), width="stretch", hide_index=True)
    render_table_downloads(snapshots, basename="scanner_snapshot_list", label="snapshots")

    frame = scanner_results_frame(root)
    filtered = _filter(frame)
    streamlit.subheader("Scanner Candidates")
    streamlit.dataframe(display_frame(filtered), width="stretch", hide_index=True)
    render_table_downloads(filtered, basename="scanner_results", label="scanner_results")

    streamlit.subheader("Rejection Summary")
    summary = _rejection_summary(filtered)
    streamlit.dataframe(display_frame(summary), width="stretch", hide_index=True)
    render_table_downloads(summary, basename="scanner_rejection_summary", label="rejections")


if __name__ == "__main__":
    render_page()
