from __future__ import annotations

from dashboard.ui.components import (
    configure_page,
    render_sidebar_settings,
    render_startup_guard,
    repository_root,
)
from dashboard.ui.navigation import streamlit_pages


def main() -> None:
    configure_page("Self-Learning Swing Trading Engine")
    import streamlit as st

    render_startup_guard()
    render_sidebar_settings(repository_root())
    page = st.navigation(streamlit_pages(st), position="sidebar")
    page.run()


if __name__ == "__main__":
    main()
