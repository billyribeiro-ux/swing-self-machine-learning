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
    from dashboard.sections.data_universe import render_page

    render_page()


def _discovery_lab() -> None:
    from dashboard.sections.discovery_lab import render_page

    render_page()


def _live_scanner() -> None:
    from dashboard.sections.live_scanner import render_page

    render_page()


def _candidate_attribution() -> None:
    from dashboard.sections.candidate_attribution import render_page

    render_page()


def _portfolio_backtests() -> None:
    from dashboard.sections.portfolio_backtests import render_page

    render_page()


def _paper_forward_test() -> None:
    from dashboard.sections.paper_forward_test import render_page

    render_page()


def _model_registry() -> None:
    from dashboard.sections.model_registry import render_page

    render_page()


def _baselines_legacy() -> None:
    from dashboard.sections.baselines_legacy import render_page

    render_page()


USER_FACING_SECTIONS: tuple[DashboardSection, ...] = (
    DashboardSection("Overview", Path("dashboard/sections/overview.py"), "overview", _overview),
    DashboardSection(
        "Data and Universe",
        Path("dashboard/sections/data_universe.py"),
        "data-universe",
        _data_audit,
    ),
    DashboardSection(
        "Discovery Lab",
        Path("dashboard/sections/discovery_lab.py"),
        "discovery-lab",
        _discovery_lab,
    ),
    DashboardSection(
        "Live Scanner",
        Path("dashboard/sections/live_scanner.py"),
        "live-scanner",
        _live_scanner,
    ),
    DashboardSection(
        "Candidate Attribution",
        Path("dashboard/sections/candidate_attribution.py"),
        "candidate-attribution",
        _candidate_attribution,
    ),
    DashboardSection(
        "Portfolio Backtests",
        Path("dashboard/sections/portfolio_backtests.py"),
        "portfolio-backtests",
        _portfolio_backtests,
    ),
    DashboardSection(
        "Paper Forward Test",
        Path("dashboard/sections/paper_forward_test.py"),
        "paper-forward-test",
        _paper_forward_test,
    ),
    DashboardSection(
        "Model Registry",
        Path("dashboard/sections/model_registry.py"),
        "model-registry",
        _model_registry,
    ),
    DashboardSection(
        "Baselines and Legacy RSI",
        Path("dashboard/sections/baselines_legacy.py"),
        "baselines-legacy-rsi",
        _baselines_legacy,
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
