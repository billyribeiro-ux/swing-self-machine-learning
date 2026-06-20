from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from swing_rsi.data.loader import save_ohlcv_csv
from swing_rsi.sample_data import generate_sample_ohlcv

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest


@pytest.fixture()
def demo_dashboard_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    config_dir = tmp_path / "configs" / "universe"
    config_dir.mkdir(parents=True)
    (config_dir / "core.yaml").write_text(
        """
name: demo
provider: fmp
default_start: "2018-01-02"
symbols:
  - symbol: DEMO
    enabled: true
    role: stock
    sector: demo
relationships: []
""",
        encoding="utf-8",
    )
    save_ohlcv_csv(generate_sample_ohlcv(rows=1_205), raw / "DEMO.csv")
    monkeypatch.setattr("dashboard.ui.components.resolve_project_root", lambda _: tmp_path)

    def fail_download(*_: object, **__: object) -> None:
        raise AssertionError("Dashboard smoke test attempted an FMP download")

    monkeypatch.setattr("swing_rsi.data.loader.download_daily", fail_download)
    return tmp_path


def _assert_no_streamlit_exceptions(app: Any) -> None:
    assert not app.exception, [str(exception.value) for exception in app.exception]


def test_rsi_explorer_controls_smoke(demo_dashboard_root: Path) -> None:
    app = AppTest.from_file("dashboard/sections/rsi_explorer.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    assert "DEMO" in app.selectbox[0].options
    assert all(".csv" not in str(option).lower() for option in app.selectbox[0].options)
    app.selectbox[0].set_value("DEMO")
    app.slider[0].set_value(12)
    app.slider[1].set_value(38)
    app.selectbox[1].set_value("turn_up_below")
    app.selectbox[2].set_value(app.selectbox[2].options[2])
    app.selectbox[3].set_value("above_sma_50")
    app.checkbox[0].set_value(True)
    app.run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    assert any(
        subheader.value == "Bullish RSI swing-reversal candidate" for subheader in app.subheader
    )
    assert any(subheader.value == "Retail Control RSI(14)/30" for subheader in app.subheader)


def test_data_audit_end_date_stays_editable_when_optional(
    demo_dashboard_root: Path,
) -> None:
    app = AppTest.from_file("dashboard/sections/data_audit.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    end_date = next(widget for widget in app.date_input if widget.label == "Request end date")
    custom_end_date = next(widget for widget in app.date_input if widget.label == "End date")
    assert end_date.disabled is False
    assert custom_end_date.disabled is False
    assert app.checkbox[0].label == "Use end date in request"
    assert app.checkbox[0].value is True

    app.checkbox[0].set_value(False)
    app.run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    end_date = next(widget for widget in app.date_input if widget.label == "Request end date")
    assert end_date.disabled is False
    assert app.checkbox[0].value is False
    assert "DEMO" in app.selectbox[0].options
    assert "DEMO.csv" not in {str(option) for option in app.selectbox[0].options}


def test_quick_research_submission_and_candidate_selection_smoke(
    demo_dashboard_root: Path,
) -> None:
    app = AppTest.from_file("dashboard/sections/research_backtest.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    app.selectbox[0].set_value("DEMO")
    app.number_input[2].set_value(5)
    app.button[0].click()
    app.run(timeout=120)

    _assert_no_streamlit_exceptions(app)
    assert app.success
    assert len(app.selectbox) >= 3

    candidate_options = list(app.selectbox[2].options)
    assert candidate_options
    app.selectbox[2].set_value(candidate_options[min(1, len(candidate_options) - 1)])
    app.run(timeout=120)

    _assert_no_streamlit_exceptions(app)
    assert app.selectbox[2].value in candidate_options


def test_walk_forward_submission_smoke(demo_dashboard_root: Path) -> None:
    app = AppTest.from_file("dashboard/sections/walk_forward.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    app.selectbox[0].set_value("DEMO")
    app.number_input[2].set_value(5)
    app.button[0].click()
    app.run(timeout=120)

    _assert_no_streamlit_exceptions(app)
    assert any(
        subheader.value == "Out-of-sample walk-forward results" for subheader in app.subheader
    )
    assert len(app.dataframe) >= 3


def test_dashboard_app_startup_smoke_no_network(demo_dashboard_root: Path) -> None:
    app = AppTest.from_file("dashboard/app.py").run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    assert any(title.value == "Self-Learning Swing Trading Engine" for title in app.title)


def test_every_dashboard_section_renders_without_streamlit_exceptions(
    demo_dashboard_root: Path,
) -> None:
    for path in (
        "dashboard/sections/overview.py",
        "dashboard/sections/data_universe.py",
        "dashboard/sections/discovery_lab.py",
        "dashboard/sections/live_scanner.py",
        "dashboard/sections/candidate_attribution.py",
        "dashboard/sections/portfolio_backtests.py",
        "dashboard/sections/paper_forward_test.py",
        "dashboard/sections/model_registry.py",
        "dashboard/sections/baselines_legacy.py",
        "dashboard/sections/data_audit.py",
        "dashboard/sections/rsi_explorer.py",
        "dashboard/sections/research_backtest.py",
        "dashboard/sections/walk_forward.py",
    ):
        app = AppTest.from_file(path).run(timeout=30)
        _assert_no_streamlit_exceptions(app)
