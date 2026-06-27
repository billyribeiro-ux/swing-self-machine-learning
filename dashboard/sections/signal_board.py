from __future__ import annotations

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
from swing_rsi.application.dashboard_service import (
    LIVE_ACTIONABLE,
    signal_board_frame,
    signal_board_metrics,
)


def _options(frame: pd.DataFrame, column: str) -> list[str]:
    if frame.empty or column not in frame.columns:
        return []
    return sorted(frame[column].dropna().astype(str).unique().tolist())


def _filtered(frame: pd.DataFrame) -> pd.DataFrame:
    streamlit = st()
    if frame.empty:
        return frame
    columns = streamlit.columns(4)
    classification = columns[0].multiselect(
        "Live/shadow/rejected",
        _options(frame, "live_shadow_rejected_classification"),
    )
    ticker = columns[1].multiselect("Ticker", _options(frame, "ticker"))
    direction = columns[2].multiselect("Direction", _options(frame, "direction"))
    model = columns[3].multiselect("Model", _options(frame, "model_id"))
    columns = streamlit.columns(4)
    scope = columns[0].multiselect("Scope", _options(frame, "scope"))
    status = columns[1].multiselect("Status", _options(frame, "signal_status"))
    rejection = columns[2].multiselect("Rejection reason", _options(frame, "rejection_reason"))
    lifecycle = columns[3].multiselect(
        "Pending/open/closed",
        _options(frame, "next_required_event"),
    )
    filtered = frame.copy()
    for column, values in (
        ("live_shadow_rejected_classification", classification),
        ("ticker", ticker),
        ("direction", direction),
        ("model_id", model),
        ("scope", scope),
        ("signal_status", status),
        ("rejection_reason", rejection),
        ("next_required_event", lifecycle),
    ):
        if values:
            filtered = filtered.loc[filtered[column].astype(str).isin(values)]
    return filtered


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Signal Board",
        "Signal-first view of live, shadow, rejected, pending, open, and closed rows.",
    )
    render_page_guidance(
        tells_you=(
            "Whether any scanner rows are live actionable, shadow-only, rejected, pending entry, "
            "open shadow positions, or closed outcomes."
        ),
        next_action=(
            "If live actionable count is zero, review rejection reasons, shadow evidence, and the "
            "next required event before exporting the board."
        ),
    )

    metrics = signal_board_metrics(root)
    render_status_cards(
        {
            "Live actionable signals": metrics["live_actionable_signals"],
            "Shadow/paper signals": metrics["shadow_paper_signals"],
            "Pending entries": metrics["pending_entries"],
            "Open shadow positions": metrics["open_shadow_positions"],
            "Closed shadow positions": metrics["closed_shadow_positions"],
            "Matured outcomes": metrics["matured_outcomes"],
            "Promoted models": metrics["promoted_models"],
            "Models collecting final-holdout evidence": metrics[
                "models_collecting_final_holdout_evidence"
            ],
            "Latest market date": metrics["latest_market_date"],
            "Development generation": metrics["development_generation"],
            "Operational run status": metrics["operational_run_status"],
        },
        columns=4,
    )
    if int(metrics["promoted_models"]) == 0:
        streamlit.warning(
            "No promoted live scanner model exists yet.\n\n"
            "Current signals are research/shadow validation only.\n\n"
            "No live actionable model is currently promoted.\n\n"
            "All current signals are research/shadow validation only."
        )

    frame = signal_board_frame(root)
    if frame.empty:
        streamlit.info(
            "No scanner candidates, shadow events, or signal rows are available locally."
        )
        return
    filtered = _filtered(frame)
    live_count = int(
        (
            filtered.get("live_shadow_rejected_classification", pd.Series(dtype=str)).astype(str)
            == LIVE_ACTIONABLE
        ).sum()
    )
    if live_count == 0:
        streamlit.info("No live actionable scanner rows are present in the current local state.")

    streamlit.subheader("Signal Board")
    streamlit.dataframe(display_frame(filtered), width="stretch", hide_index=True)
    render_table_downloads(filtered, basename="signal_board", label="signal_board")


if __name__ == "__main__":
    render_page()
