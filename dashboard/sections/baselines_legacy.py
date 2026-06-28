from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame


def render_page() -> None:
    streamlit = st()
    render_page_header("Legacy Baselines", "Legacy baselines and controls.")
    render_page_guidance(
        tells_you="Legacy RSI and older baseline research outputs separated from autonomous models.",
        next_action="Use these controls only for baseline comparison, not scanner signal operation.",
    )
    streamlit.info("RSI and old baseline views are separate from autonomous scanner models.")
    section = streamlit.selectbox(
        "Legacy tool",
        (
            "Overview of baselines",
            "Data and Audit",
            "RSI Explorer",
            "Research and Backtest",
            "Walk-Forward Validation",
        ),
    )
    if section == "Overview of baselines":
        streamlit.write(
            "RSI is retained as a baseline feature family and control workflow. "
            "RSI(14)/30 is not treated as a privileged scanner strategy."
        )
        root = repository_root()
        reports = [
            {
                "path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted((root / "reports").glob("*rsi*"))
            if path.is_file()
        ]
        frame = pd.DataFrame(reports)
        streamlit.subheader("RSI Research Runs")
        streamlit.dataframe(display_frame(frame), width="stretch", hide_index=True)
        render_table_downloads(frame, basename="legacy_baselines", label="legacy")
        return
    if section == "Data and Audit":
        from dashboard.sections.data_audit import render_page as render_legacy
    elif section == "RSI Explorer":
        from dashboard.sections.rsi_explorer import render_page as render_legacy
    elif section == "Research and Backtest":
        from dashboard.sections.research_backtest import render_page as render_legacy
    else:
        from dashboard.sections.walk_forward import render_page as render_legacy
    render_legacy()


if __name__ == "__main__":
    render_page()
