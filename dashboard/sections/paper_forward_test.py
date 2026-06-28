from __future__ import annotations

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.application.dashboard_service import paper_forward_state_frames


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Paper Forward Test",
        "Ordinary append-only paper-forward state for frozen scanner signals.",
    )
    streamlit.warning("Ordinary paper forward test is separate from prospective final holdout.")
    frames = paper_forward_state_frames(root)
    for label in (
        "pending_entries",
        "open_positions",
        "closed_positions",
        "event_history",
        "model_versions",
    ):
        streamlit.subheader(label.replace("_", " ").title())
        frame = frames[label]
        if frame.empty:
            streamlit.info("No rows available.")
        else:
            streamlit.dataframe(display_frame(frame), width="stretch", hide_index=True)
        render_table_downloads(frame, basename=f"paper_forward_{label}", label=label)

    streamlit.download_button(
        "Download paper-forward workbook XLSX",
        data=to_xlsx_bytes(frames),
        file_name="paper_forward_test.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    render_page()
