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


def _signal_board() -> None:
    from dashboard.sections.signal_board import render_page

    render_page()


def _shadow_forward_test() -> None:
    from dashboard.sections.shadow_forward_test import render_page

    render_page()


def _model_edge_status() -> None:
    from dashboard.sections.model_edge_status import render_page

    render_page()


def _scanner_results() -> None:
    from dashboard.sections.scanner_results import render_page

    render_page()


def _candidate_detail() -> None:
    from dashboard.sections.candidate_detail import render_page

    render_page()


def _product_class_research() -> None:
    from dashboard.sections.product_class_research import render_page

    render_page()


def _gate_audit() -> None:
    from dashboard.sections.gate_audit import render_page

    render_page()


def _data_universe() -> None:
    from dashboard.sections.data_universe import render_page

    render_page()


def _reports_and_exports() -> None:
    from dashboard.sections.reports_and_exports import render_page

    render_page()


def _engine_commands() -> None:
    from dashboard.sections.engine_commands import render_page

    render_page()


def _legacy_baselines() -> None:
    from dashboard.sections.baselines_legacy import render_page

    render_page()


def _developer_diagnostics() -> None:
    from dashboard.sections.developer_diagnostics import render_page

    render_page()


USER_FACING_SECTIONS: tuple[DashboardSection, ...] = (
    DashboardSection(
        "Signal Board",
        Path("dashboard/sections/signal_board.py"),
        "signal-board",
        _signal_board,
    ),
    DashboardSection(
        "Shadow Forward Test",
        Path("dashboard/sections/shadow_forward_test.py"),
        "shadow-forward-test",
        _shadow_forward_test,
    ),
    DashboardSection(
        "Model Edge Status",
        Path("dashboard/sections/model_edge_status.py"),
        "model-edge-status",
        _model_edge_status,
    ),
    DashboardSection(
        "Scanner Results",
        Path("dashboard/sections/scanner_results.py"),
        "scanner-results",
        _scanner_results,
    ),
    DashboardSection(
        "Candidate Detail",
        Path("dashboard/sections/candidate_detail.py"),
        "candidate-detail",
        _candidate_detail,
    ),
    DashboardSection(
        "Product-Class Research",
        Path("dashboard/sections/product_class_research.py"),
        "product-class-research",
        _product_class_research,
    ),
    DashboardSection(
        "Gate Audit",
        Path("dashboard/sections/gate_audit.py"),
        "gate-audit",
        _gate_audit,
    ),
    DashboardSection(
        "Data and Universe",
        Path("dashboard/sections/data_universe.py"),
        "data-universe",
        _data_universe,
    ),
    DashboardSection(
        "Reports and Exports",
        Path("dashboard/sections/reports_and_exports.py"),
        "reports-and-exports",
        _reports_and_exports,
    ),
    DashboardSection(
        "Engine Commands",
        Path("dashboard/sections/engine_commands.py"),
        "engine-commands",
        _engine_commands,
    ),
    DashboardSection(
        "Legacy Baselines",
        Path("dashboard/sections/baselines_legacy.py"),
        "legacy-baselines",
        _legacy_baselines,
    ),
    DashboardSection(
        "Developer Diagnostics",
        Path("dashboard/sections/developer_diagnostics.py"),
        "developer-diagnostics",
        _developer_diagnostics,
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
