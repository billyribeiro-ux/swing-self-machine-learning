from __future__ import annotations

from pathlib import Path
from typing import Any

from dashboard.ui.navigation import section_titles
from swing_rsi.application.dashboard_service import (
    OPERATIONAL_REPOSITORY,
    dashboard_startup_state,
    fmp_key_configured,
    save_development_fmp_settings,
)
from swing_rsi.application.project_status import resolve_project_root

COMMAND_CENTER_TITLE = "Self-Learning Swing Trading Engine"
COMMAND_CENTER_SUBTITLE = "Autonomous Discovery, Scanner, Attribution, and Shadow Forward Testing"
RESEARCH_WARNING = (
    "Experimental research system. Results are not financial advice and are not evidence of a "
    "live trading edge."
)
STATE_LABEL = "Development dashboard. Operational frozen run remains separate."
DEVELOPMENT_REPOSITORY_LABEL = "/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev"
DATA_WARNING = (
    "FMP corporate-action and historical-universe semantics have not yet been fully audited."
)
BADGE_COLORS: dict[str, str] = {
    "LIVE ACTIONABLE": "#0f7b45",
    "SHADOW ONLY": "#6b5b00",
    "REJECTED": "#9f2f2f",
    "PENDING ENTRY": "#6b5b00",
    "OPEN SHADOW POSITION": "#1f5f8b",
    "CLOSED": "#4b5563",
    "RESEARCH ONLY": "#52525b",
    "DEVELOPMENT CANDIDATE": "#1d4ed8",
    "SHADOW VALIDATION": "#7c3aed",
    "FINAL-HOLDOUT QUALIFIED": "#047857",
    "PROMOTED": "#047857",
}


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
    streamlit.info(STATE_LABEL)
    streamlit.caption(DATA_WARNING)


def render_page_header(title: str, caption: str | None = None) -> None:
    streamlit = st()
    streamlit.title(COMMAND_CENTER_TITLE)
    streamlit.caption(COMMAND_CENTER_SUBTITLE)
    if caption:
        streamlit.header(title)
        streamlit.caption(caption)
    elif title != COMMAND_CENTER_TITLE:
        streamlit.header(title)
    render_integrity_banner()


def render_page_guidance(*, tells_you: str, next_action: str) -> None:
    streamlit = st()
    columns = streamlit.columns(2)
    with columns[0]:
        streamlit.subheader("What this page tells you")
        streamlit.info(tells_you)
    with columns[1]:
        streamlit.subheader("What to do next")
        streamlit.info(next_action)


def status_badge(label: object) -> str:
    text = str(label or "").strip() or "Not available"
    color = BADGE_COLORS.get(text.upper(), "#4b5563")
    return (
        f'<span style="background:{color};color:white;border-radius:4px;'
        f'padding:0.15rem 0.4rem;font-size:0.78rem;font-weight:700;">{text}</span>'
    )


def render_status_cards(cards: dict[str, object], *, columns: int = 4) -> None:
    streamlit = st()
    if not cards:
        return
    layout = streamlit.columns(columns)
    for index, (label, value) in enumerate(cards.items()):
        layout[index % columns].metric(label, value)


def render_startup_guard() -> bool:
    streamlit = st()
    state = dashboard_startup_state(Path.cwd())
    streamlit.sidebar.caption("Repository Safety")
    streamlit.sidebar.write(f"Development repository: `{state.development_repository}`")
    streamlit.sidebar.write(f"Operational repository: `{state.operational_repository}`")
    if state.is_operational_repository:
        streamlit.error(
            "Blocked startup: run this dashboard from the development worktree, not the frozen "
            f"operational repository `{OPERATIONAL_REPOSITORY}`."
        )
        streamlit.stop()
        return False
    if state.requires_confirmation:
        streamlit.warning(state.message)
        confirmed = streamlit.checkbox(
            "I understand this is not the configured development worktree.",
            value=False,
        )
        if not confirmed:
            streamlit.stop()
            return False
    return True


def render_sidebar_settings(root: Path) -> None:
    streamlit = st()
    configured = fmp_key_configured(root)
    with streamlit.sidebar.expander("Settings", expanded=False):
        streamlit.write(f"FMP key configured: {'yes' if configured else 'no'}")
        api_key = streamlit.text_input("FMP API key", type="password", value="")
        base_url = streamlit.text_input(
            "FMP base URL",
            value="https://financialmodelingprep.com/stable",
        )
        confirmed = streamlit.checkbox(
            "Save this key to the development .env only.",
            value=False,
        )
        if streamlit.button("Save FMP settings", disabled=not confirmed or not api_key.strip()):
            try:
                result = save_development_fmp_settings(
                    root,
                    api_key=api_key,
                    base_url=base_url,
                )
            except ValueError as exc:
                streamlit.error(str(exc))
            else:
                streamlit.success(result.message)


def render_navigation() -> None:
    streamlit = st()
    items = "\n".join(f"- {title}" for title in section_titles())
    streamlit.markdown(
        f"""
        **Dashboard Pages**

        {items}
        """
    )
