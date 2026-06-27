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


def _model_registry() -> None:
    from dashboard.sections.model_registry import render_page

    render_page()


def _gate_audit() -> None:
    from dashboard.sections.gate_audit import render_page

    render_page()


def _product_class_specialists() -> None:
    from dashboard.sections.product_class_specialists import render_page

    render_page()


def _scanner_snapshots() -> None:
    from dashboard.sections.scanner_snapshots import render_page

    render_page()


def _candidate_attribution() -> None:
    from dashboard.sections.candidate_attribution import render_page

    render_page()


def _shadow_final_holdout() -> None:
    from dashboard.sections.shadow_final_holdout import render_page

    render_page()


def _paper_forward_test() -> None:
    from dashboard.sections.paper_forward_test import render_page

    render_page()


def _reports_and_exports() -> None:
    from dashboard.sections.reports_and_exports import render_page

    render_page()


def _engine_commands() -> None:
    from dashboard.sections.engine_commands import render_page

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
        "Model Registry",
        Path("dashboard/sections/model_registry.py"),
        "model-registry",
        _model_registry,
    ),
    DashboardSection(
        "Gate Audit",
        Path("dashboard/sections/gate_audit.py"),
        "gate-audit",
        _gate_audit,
    ),
    DashboardSection(
        "Product-Class Specialists",
        Path("dashboard/sections/product_class_specialists.py"),
        "product-class-specialists",
        _product_class_specialists,
    ),
    DashboardSection(
        "Scanner Snapshots",
        Path("dashboard/sections/scanner_snapshots.py"),
        "scanner-snapshots",
        _scanner_snapshots,
    ),
    DashboardSection(
        "Candidate Attribution",
        Path("dashboard/sections/candidate_attribution.py"),
        "candidate-attribution",
        _candidate_attribution,
    ),
    DashboardSection(
        "Shadow Final Holdout",
        Path("dashboard/sections/shadow_final_holdout.py"),
        "shadow-final-holdout",
        _shadow_final_holdout,
    ),
    DashboardSection(
        "Paper Forward Test",
        Path("dashboard/sections/paper_forward_test.py"),
        "paper-forward-test",
        _paper_forward_test,
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
