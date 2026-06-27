from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest
from dashboard.sections.data_audit import dataset_display_label
from dashboard.ui.navigation import USER_FACING_SECTIONS, section_titles

from swing_rsi.application.datasets import DatasetSummary
from swing_rsi.data.loader import save_ohlcv_csv

REQUIRED_SIGNAL_FIRST_PAGE_TITLES = (
    "Signal Board",
    "Shadow Forward Test",
    "Model Edge Status",
    "Scanner Results",
    "Candidate Detail",
    "Product-Class Research",
    "Gate Audit",
    "Data and Universe",
    "Reports and Exports",
    "Engine Commands",
    "Legacy Baselines",
    "Developer Diagnostics",
)

LEGACY_PRIMARY_PAGE_TITLES = {
    "Discovery Lab",
    "Live Scanner",
    "Portfolio Backtests",
    "Baselines and Legacy RSI",
}


class _StreamlitStop(RuntimeError):
    pass


class _FakeSidebar:
    def __init__(self, captured: dict[str, object]) -> None:
        self._captured = captured

    def caption(self, value: str) -> None:
        self._captured.setdefault("sidebar_captions", []).append(value)

    def write(self, value: str) -> None:
        self._captured.setdefault("sidebar_writes", []).append(value)

    def expander(self, *_: object, **__: object) -> _FakeExpander:
        return _FakeExpander()


class _FakeExpander:
    def __enter__(self) -> _FakeExpander:
        return self

    def __exit__(self, *_: object) -> bool:
        return False


def _install_fake_streamlit(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}
    fake_streamlit = ModuleType("streamlit")
    fake_streamlit.sidebar = _FakeSidebar(captured)

    def page(
        renderer: object,
        *,
        title: str,
        url_path: str,
        default: bool = False,
        **_: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            renderer=renderer,
            title=title,
            url_path=url_path,
            default=default,
        )

    def navigation(pages: list[object], *, position: str, **_: object) -> SimpleNamespace:
        captured["pages"] = list(pages)
        captured["position"] = position
        return SimpleNamespace(run=lambda: captured.__setitem__("run_called", True))

    def stop() -> None:
        captured["stopped"] = True
        raise _StreamlitStop()

    fake_streamlit.set_page_config = lambda *args, **kwargs: captured.__setitem__(
        "page_config", (args, kwargs)
    )
    fake_streamlit.Page = page
    fake_streamlit.navigation = navigation
    fake_streamlit.error = lambda value: captured.setdefault("errors", []).append(value)
    fake_streamlit.warning = lambda value: captured.setdefault("warnings", []).append(value)
    fake_streamlit.checkbox = lambda *_args, **_kwargs: False
    fake_streamlit.stop = stop
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    return captured


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
        "dashboard.sections.signal_board",
        "dashboard.sections.shadow_forward_test",
        "dashboard.sections.model_edge_status",
        "dashboard.sections.scanner_results",
        "dashboard.sections.candidate_detail",
        "dashboard.sections.product_class_research",
        "dashboard.sections.gate_audit",
        "dashboard.sections.data_universe",
        "dashboard.sections.reports_and_exports",
        "dashboard.sections.engine_commands",
        "dashboard.sections.baselines_legacy",
        "dashboard.sections.developer_diagnostics",
        "dashboard.sections.overview",
        "dashboard.sections.model_registry",
        "dashboard.sections.product_class_specialists",
        "dashboard.sections.scanner_snapshots",
        "dashboard.sections.candidate_attribution",
        "dashboard.sections.shadow_final_holdout",
        "dashboard.sections.paper_forward_test",
        "dashboard.sections.data_audit",
        "dashboard.sections.discovery_lab",
        "dashboard.sections.live_scanner",
        "dashboard.sections.portfolio_backtests",
        "dashboard.sections.rsi_explorer",
        "dashboard.sections.research_backtest",
        "dashboard.sections.walk_forward",
    )
    for module in modules:
        importlib.import_module(module)

    assert path.read_bytes() == before


def test_dashboard_registers_autonomous_engine_sections() -> None:
    assert section_titles() == REQUIRED_SIGNAL_FIRST_PAGE_TITLES
    assert len(USER_FACING_SECTIONS) == 12
    assert "app" not in {title.lower() for title in section_titles()}
    assert not LEGACY_PRIMARY_PAGE_TITLES.intersection(section_titles())
    assert [section.url_path for section in USER_FACING_SECTIONS] == [
        "signal-board",
        "shadow-forward-test",
        "model-edge-status",
        "scanner-results",
        "candidate-detail",
        "product-class-research",
        "gate-audit",
        "data-universe",
        "reports-and-exports",
        "engine-commands",
        "legacy-baselines",
        "developer-diagnostics",
    ]
    assert all("dashboard/sections" in section.path.as_posix() for section in USER_FACING_SECTIONS)
    assert not tuple(Path("dashboard/pages").glob("*.py"))


def test_dashboard_app_entrypoint_registers_command_center_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_fake_streamlit(monkeypatch)
    import dashboard.app as app_module

    monkeypatch.setattr(app_module, "render_startup_guard", lambda: True)
    monkeypatch.setattr(app_module, "render_sidebar_settings", lambda _root: None)
    monkeypatch.setattr(app_module, "repository_root", lambda: Path("/tmp/dev"))

    app_module.main()

    pages = captured["pages"]
    assert [page.title for page in pages] == list(REQUIRED_SIGNAL_FIRST_PAGE_TITLES)
    assert not LEGACY_PRIMARY_PAGE_TITLES.intersection({page.title for page in pages})
    assert [page.url_path for page in pages] == [
        "signal-board",
        "shadow-forward-test",
        "model-edge-status",
        "scanner-results",
        "candidate-detail",
        "product-class-research",
        "gate-audit",
        "data-universe",
        "reports-and-exports",
        "engine-commands",
        "legacy-baselines",
        "developer-diagnostics",
    ]
    assert [page.default for page in pages] == [True] + [False] * 11
    assert captured["position"] == "sidebar"
    assert captured["run_called"] is True


def test_dashboard_app_entrypoint_blocks_operational_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_fake_streamlit(monkeypatch)
    import dashboard.app as app_module
    import dashboard.ui.components as components

    from swing_rsi.application import dashboard_service as service

    development = tmp_path / "dev"
    operational = tmp_path / "ops"
    development.mkdir()
    operational.mkdir()
    monkeypatch.setattr(service, "DEVELOPMENT_REPOSITORY", development)
    monkeypatch.setattr(service, "OPERATIONAL_REPOSITORY", operational)
    monkeypatch.setattr(components, "OPERATIONAL_REPOSITORY", operational)
    monkeypatch.chdir(operational)

    with pytest.raises(_StreamlitStop):
        app_module.main()

    assert captured["stopped"] is True
    assert "pages" not in captured
    assert any("Blocked startup" in message for message in captured.get("errors", []))


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
