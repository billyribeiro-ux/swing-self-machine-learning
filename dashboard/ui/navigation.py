from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DashboardSection:
    title: str
    path: Path
    url_path: str
    renderer: Callable[[], None]


def _overview() -> None:
    from dashboard.sections.overview import render_page

    render_page()


def _data_audit() -> None:
    from dashboard.sections.data_audit import render_page

    render_page()


def _rsi_explorer() -> None:
    from dashboard.sections.rsi_explorer import render_page

    render_page()


def _research_backtest() -> None:
    from dashboard.sections.research_backtest import render_page

    render_page()


def _walk_forward() -> None:
    from dashboard.sections.walk_forward import render_page

    render_page()


USER_FACING_SECTIONS: tuple[DashboardSection, ...] = (
    DashboardSection("Overview", Path("dashboard/sections/overview.py"), "overview", _overview),
    DashboardSection(
        "Data and Audit",
        Path("dashboard/sections/data_audit.py"),
        "data-audit",
        _data_audit,
    ),
    DashboardSection(
        "RSI Explorer",
        Path("dashboard/sections/rsi_explorer.py"),
        "rsi-explorer",
        _rsi_explorer,
    ),
    DashboardSection(
        "Research and Backtest",
        Path("dashboard/sections/research_backtest.py"),
        "research-backtest",
        _research_backtest,
    ),
    DashboardSection(
        "Walk-Forward Validation",
        Path("dashboard/sections/walk_forward.py"),
        "walk-forward-validation",
        _walk_forward,
    ),
)


def section_titles() -> tuple[str, ...]:
    return tuple(section.title for section in USER_FACING_SECTIONS)


def streamlit_pages(streamlit: Any) -> list[Any]:
    return [
        streamlit.Page(
            section.renderer,
            title=section.title,
            url_path=section.url_path,
            default=index == 0,
        )
        for index, section in enumerate(USER_FACING_SECTIONS)
    ]
