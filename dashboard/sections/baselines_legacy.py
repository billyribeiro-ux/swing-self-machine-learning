from __future__ import annotations

from dashboard.ui.components import render_page_header, st


def render_page() -> None:
    streamlit = st()
    render_page_header(
        "Baselines and Legacy RSI", "RSI controls and the historical V0 research dashboard."
    )
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
