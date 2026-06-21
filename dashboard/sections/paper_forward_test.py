from __future__ import annotations

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.engine_service import (
    final_holdout_event_history,
    final_holdout_status,
    forward_events,
    run_forward_update,
)
from swing_rsi.config import ProjectPaths
from swing_rsi.engine.forward import reconstruct_positions


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Paper Forward Test", "Append-only paper events for frozen model scanner signals."
    )
    if streamlit.button("Advance paper state and record latest scanner snapshot"):
        count = run_forward_update(root)
        streamlit.success(f"Created {count:,} new append-only paper-forward events.")
    positions = reconstruct_positions(ProjectPaths(root).engine_db)
    streamlit.subheader("Reconstructed Position State")
    if positions.empty:
        streamlit.info("No paper-forward position state yet.")
    else:
        streamlit.dataframe(display_frame(positions), width="stretch", hide_index=True)
    events = forward_events(root)
    streamlit.subheader("Event History")
    if events.empty:
        streamlit.info("No forward events yet.")
    else:
        streamlit.dataframe(
            display_frame(events.drop(columns=["payload"], errors="ignore")),
            width="stretch",
            hide_index=True,
        )

    streamlit.subheader("Prospective Final Holdout")
    streamlit.info("Prospective shadow validation. Not a live trade recommendation.")
    final_status = final_holdout_status(root)
    if final_status.empty:
        streamlit.info("No prospective final-holdout run is collecting yet.")
        return
    streamlit.caption(
        "Sample-governance progress is shown as actual counts with required-count columns. "
        "These prospective metrics are separate from development-holdout diagnostics."
    )
    streamlit.dataframe(display_frame(final_status), width="stretch", hide_index=True)
    final_events = final_holdout_event_history(root)
    if not final_events.empty:
        streamlit.dataframe(
            display_frame(final_events.drop(columns=["payload"], errors="ignore")),
            width="stretch",
            hide_index=True,
        )


if __name__ == "__main__":
    render_page()
