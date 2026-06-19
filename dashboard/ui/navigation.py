from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DashboardSection:
    title: str
    path: Path


USER_FACING_SECTIONS: tuple[DashboardSection, ...] = (
    DashboardSection("Overview", Path("dashboard/app.py")),
    DashboardSection("Data and Audit", Path("dashboard/pages/data_audit.py")),
    DashboardSection("RSI Explorer", Path("dashboard/pages/rsi_explorer.py")),
    DashboardSection("Research and Backtest", Path("dashboard/pages/research_backtest.py")),
    DashboardSection("Walk-Forward Validation", Path("dashboard/pages/walk_forward.py")),
)


def section_titles() -> tuple[str, ...]:
    return tuple(section.title for section in USER_FACING_SECTIONS)
