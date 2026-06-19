from __future__ import annotations

from pathlib import Path
from typing import Any

from dashboard.ui.navigation import section_titles
from swing_rsi.application.project_status import resolve_project_root

RESEARCH_WARNING = (
    "Experimental research system. Results are not financial advice and are not evidence "
    "of a live trading edge."
)
DATA_WARNING = (
    "FMP corporate-action and historical-universe semantics have not yet been fully audited."
)


def st() -> Any:
    import streamlit as streamlit

    return streamlit


def repository_root() -> Path:
    return resolve_project_root(Path(__file__).resolve())


def configure_page(title: str) -> None:
    streamlit = st()
    streamlit.set_page_config(page_title=title, layout="wide")


def render_integrity_banner() -> None:
    streamlit = st()
    streamlit.warning(RESEARCH_WARNING)
    streamlit.info(DATA_WARNING)


def render_page_header(title: str, caption: str | None = None) -> None:
    streamlit = st()
    streamlit.title(title)
    if caption:
        streamlit.caption(caption)
    render_integrity_banner()


def render_navigation() -> None:
    streamlit = st()
    items = "\n".join(f"- {title}" for title in section_titles())
    streamlit.markdown(
        f"""
        **Dashboard Pages**

        {items}
        """
    )
