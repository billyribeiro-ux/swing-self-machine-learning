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
    CLOSED,
    LIVE_ACTIONABLE,
    OPEN_SHADOW_POSITION,
    PENDING_ENTRY,
    REJECTED,
    RESEARCH_ONLY,
    SHADOW_ONLY,
    signal_board_frame,
    signal_board_metrics,
)

SIGNAL_COLUMNS: tuple[str, ...] = (
    "ticker",
    "direction",
    "model_id",
    "generation",
    "run_id",
    "event_id",
    "edge_status",
    "signal_status",
    "live_shadow_rejected_classification",
    "as_of_date",
    "pending_entry_date",
    "entry_rule",
    "expected_return",
    "expected_mfe",
    "expected_mae",
    "target_before_stop_probability",
    "ood_warning",
    "why_shadow_only",
    "next_required_event",
    "open_url",
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


def _section_frame(frame: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if frame.empty:
        return frame
    return frame.loc[mask.reindex(frame.index, fill_value=False)].copy()


def _display_section(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in SIGNAL_COLUMNS if column in frame.columns]
    display = display_frame(frame[columns]).rename(columns={"Open Url": "Open"})
    return display


def _row_count_label(count: int) -> str:
    return f"{count:,} row" if count == 1 else f"{count:,} rows"


def _render_section(title: str, frame: pd.DataFrame, *, empty_message: str) -> None:
    streamlit = st()
    streamlit.subheader(f"{title}: {_row_count_label(len(frame))}")
    if frame.empty:
        streamlit.info(empty_message)
        return
    display = _display_section(frame)
    column_config = {}
    if "Open" in display.columns:
        column_config["Open"] = streamlit.column_config.LinkColumn(
            "Open",
            display_text="Open detail",
        )
    streamlit.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_config=column_config,
    )
    render_table_downloads(
        frame,
        basename=title.lower().replace("/", "").replace(" ", "_"),
        label=title.lower().replace("/", "").replace(" ", "_"),
    )


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
    streamlit.info(
        "Live actionable signals require a promoted model. No model is promoted yet. "
        "Shadow rows are paper-validation events used to collect prospective evidence."
    )
    show_rejected_research = streamlit.toggle(
        "Show rejected/research rows",
        value=False,
        help="Off by default so shadow, pending, open, and closed rows stay visible first.",
    )
    filtered = _filtered(frame)
    live_count = int(
        (
            filtered.get("live_shadow_rejected_classification", pd.Series(dtype=str)).astype(str)
            == LIVE_ACTIONABLE
        ).sum()
    )
    if live_count == 0:
        streamlit.info("No live actionable signals. Shadow and pending rows remain visible below.")

    classification = filtered.get(
        "live_shadow_rejected_classification", pd.Series(dtype=str, index=filtered.index)
    ).astype(str)
    signal_status = filtered.get(
        "signal_status", pd.Series(dtype=str, index=filtered.index)
    ).astype(str)
    live = _section_frame(filtered, classification == LIVE_ACTIONABLE)
    shadow = _section_frame(filtered, classification == SHADOW_ONLY)
    pending = _section_frame(filtered, signal_status == PENDING_ENTRY)
    open_positions = _section_frame(filtered, signal_status == OPEN_SHADOW_POSITION)
    closed = _section_frame(filtered, signal_status == CLOSED)
    rejected_research = _section_frame(
        filtered,
        classification.isin([REJECTED, RESEARCH_ONLY]),
    )

    _render_section(
        "Live Actionable Signals",
        live,
        empty_message="No promoted live scanner signals are currently available.",
    )
    _render_section(
        "Shadow / Paper Signals",
        shadow,
        empty_message="No shadow or paper-validation rows match the current filters.",
    )
    if not pending.empty:
        streamlit.info(
            "This row is waiting for the next eligible session open. "
            "It is not a live trade recommendation."
        )
    _render_section(
        "Pending Entries",
        pending,
        empty_message="No pending shadow entries match the current filters.",
    )
    _render_section(
        "Open Shadow Positions",
        open_positions,
        empty_message="No open shadow positions match the current filters.",
    )
    _render_section(
        "Closed / Matured Outcomes",
        closed,
        empty_message="No closed or matured shadow outcomes match the current filters.",
    )

    with streamlit.expander(
        f"Rejected / Research Candidates: {_row_count_label(len(rejected_research))}",
        expanded=show_rejected_research,
    ):
        if show_rejected_research:
            _render_section(
                "Rejected / Research Candidates",
                rejected_research,
                empty_message="No rejected or research-only rows match the current filters.",
            )
        else:
            streamlit.caption("Enable Show rejected/research rows to inspect these candidates.")

    render_table_downloads(filtered, basename="signal_board", label="signal_board")


if __name__ == "__main__":
    render_page()
