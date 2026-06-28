from __future__ import annotations

import pandas as pd

from dashboard.ui.components import (
    render_page_guidance,
    render_page_header,
    repository_root,
    st,
)
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    EDGE_DEVELOPMENT_CANDIDATE,
    EDGE_PROMOTED,
    EDGE_RESEARCH_ONLY,
    EDGE_SHADOW_VALIDATION,
    model_edge_status_frame,
)

SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("Development-qualified models", EDGE_DEVELOPMENT_CANDIDATE),
    ("Shadow-validation models", EDGE_SHADOW_VALIDATION),
    ("Models blocked by development gates", "BLOCKED"),
    ("Research-only models", EDGE_RESEARCH_ONLY),
    ("Retired/diagnostic models", "RETIRED"),
)


def _section_frame(frame: pd.DataFrame, status: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    if status == "BLOCKED":
        return frame.loc[
            frame["failed_development_gates"].astype(str).str.strip().ne("")
            & frame["edge_status"].astype(str).ne(EDGE_SHADOW_VALIDATION)
        ]
    if status == "RETIRED":
        return frame.loc[frame["edge_status"].astype(str).str.contains("RETIRED|DIAGNOSTIC")]
    return frame.loc[frame["edge_status"].astype(str) == status]


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Model Edge Status",
        "Model readiness, shadow evidence state, promotion eligibility, and next blockers.",
    )
    render_page_guidance(
        tells_you="Which models are closest to becoming useful and why they are blocked.",
        next_action=(
            "Review development candidates and shadow-validation models first, then inspect the "
            "Gate Audit only for blocker detail."
        ),
    )
    streamlit.info(
        "Edge statuses: RESEARCH ONLY, DEVELOPMENT CANDIDATE, SHADOW VALIDATION, "
        "FINAL-HOLDOUT QUALIFIED, PROMOTED. Nothing is called live unless the model is promoted."
    )
    frame = model_edge_status_frame(root)
    if frame.empty:
        streamlit.info("No registered models are available in local development state.")
        return
    promoted = frame.loc[frame["edge_status"].astype(str) == EDGE_PROMOTED]
    if promoted.empty:
        streamlit.warning("No model currently qualifies for promotion or live scanning.")

    filters = streamlit.columns(4)
    scope = filters[0].multiselect(
        "Scope",
        sorted(frame["scope"].dropna().astype(str).unique().tolist()),
    )
    direction = filters[1].multiselect(
        "Direction",
        sorted(frame["direction"].dropna().astype(str).unique().tolist()),
    )
    family = filters[2].multiselect(
        "Family",
        sorted(frame["family"].dropna().astype(str).unique().tolist()),
    )
    edge_status = filters[3].multiselect(
        "Edge status",
        sorted(frame["edge_status"].dropna().astype(str).unique().tolist()),
    )
    filtered = frame.copy()
    for column, values in (
        ("scope", scope),
        ("direction", direction),
        ("family", family),
        ("edge_status", edge_status),
    ):
        if values:
            filtered = filtered.loc[filtered[column].astype(str).isin(values)]

    streamlit.subheader("All Model Edge Status")
    streamlit.dataframe(display_frame(filtered), width="stretch", hide_index=True)
    render_table_downloads(filtered, basename="model_edge_status", label="model_edge_status")

    for title, status in SECTION_ORDER:
        section = _section_frame(filtered, status)
        streamlit.subheader(title)
        if section.empty:
            streamlit.caption("No rows in this section.")
        else:
            streamlit.dataframe(display_frame(section), width="stretch", hide_index=True)


if __name__ == "__main__":
    render_page()
