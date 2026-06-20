from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest
from dashboard.sections.data_audit import dataset_display_label
from dashboard.ui.navigation import USER_FACING_SECTIONS, section_titles

from swing_rsi.application.datasets import DatasetSummary
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
        "dashboard.sections.data_audit",
        "dashboard.sections.rsi_explorer",
        "dashboard.sections.research_backtest",
        "dashboard.sections.walk_forward",
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
    assert "app" not in {title.lower() for title in section_titles()}
    assert [section.url_path for section in USER_FACING_SECTIONS] == [
        "overview",
        "data-audit",
        "rsi-explorer",
        "research-backtest",
        "walk-forward-validation",
    ]
    assert all("dashboard/sections" in section.path.as_posix() for section in USER_FACING_SECTIONS)
    assert not tuple(Path("dashboard/pages").glob("*.py"))


def test_dataset_display_label_uses_ticker_not_filename(tmp_path: Path) -> None:
    dataset = DatasetSummary(
        ticker="AAPL",
        path=tmp_path / "AAPL.csv",
        row_count=10,
        first_date="2020-01-02",
        latest_date="2020-01-15",
        modified_at_utc="2026-06-19T00:00:00+00:00",
    )

    assert dataset_display_label(dataset) == "AAPL"
    assert "AAPL.csv" not in dataset_display_label(dataset)
