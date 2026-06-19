from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest
from dashboard.ui.navigation import USER_FACING_SECTIONS, section_titles

from swing_rsi.data.loader import save_ohlcv_csv


def test_dashboard_imports_do_not_mutate_data_or_call_fmp(
    tmp_path: Path,
    simple_ohlcv: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    path = raw / "DEMO.csv"
    save_ohlcv_csv(simple_ohlcv, path)
    before = path.read_bytes()

    def fail_download(*_: object, **__: object) -> None:
        raise AssertionError("Dashboard import attempted a data download")

    monkeypatch.setattr("swing_rsi.data.loader.download_daily", fail_download)

    modules = (
        "dashboard.app",
        "dashboard.sections.overview",
        "dashboard.pages.data_audit",
        "dashboard.pages.rsi_explorer",
        "dashboard.pages.research_backtest",
        "dashboard.pages.walk_forward",
    )
    for module in modules:
        importlib.import_module(module)

    assert path.read_bytes() == before


def test_dashboard_registers_exactly_five_user_facing_sections() -> None:
    assert section_titles() == (
        "Overview",
        "Data and Audit",
        "RSI Explorer",
        "Research and Backtest",
        "Walk-Forward Validation",
    )
    assert len(USER_FACING_SECTIONS) == 5

    page_files = {
        path.name for path in Path("dashboard/pages").glob("*.py") if path.name != "__init__.py"
    }
    assert page_files == {
        "data_audit.py",
        "rsi_explorer.py",
        "research_backtest.py",
        "walk_forward.py",
    }
