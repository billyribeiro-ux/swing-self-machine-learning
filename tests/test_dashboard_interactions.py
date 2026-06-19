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
    save_ohlcv_csv(generate_sample_ohlcv(rows=1_205), raw / "DEMO.csv")
    monkeypatch.setattr("dashboard.ui.components.resolve_project_root", lambda _: tmp_path)

    def fail_download(*_: object, **__: object) -> None:
        raise AssertionError("Dashboard smoke test attempted an FMP download")

    monkeypatch.setattr("swing_rsi.data.loader.download_daily", fail_download)
    return tmp_path


def _assert_no_streamlit_exceptions(app: Any) -> None:
    assert not app.exception, [str(exception.value) for exception in app.exception]


def test_rsi_explorer_controls_smoke(demo_dashboard_root: Path) -> None:
    app = AppTest.from_file("dashboard/pages/rsi_explorer.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    app.selectbox[0].set_value("DEMO - DEMO.csv")
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


def test_quick_research_submission_and_candidate_selection_smoke(
    demo_dashboard_root: Path,
) -> None:
    app = AppTest.from_file("dashboard/pages/research_backtest.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    app.selectbox[0].set_value("DEMO - DEMO.csv")
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
    app = AppTest.from_file("dashboard/pages/walk_forward.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    app.selectbox[0].set_value("DEMO - DEMO.csv")
    app.number_input[2].set_value(5)
    app.button[0].click()
    app.run(timeout=120)

    _assert_no_streamlit_exceptions(app)
    assert any(
        subheader.value == "Out-of-sample walk-forward results" for subheader in app.subheader
    )
    assert len(app.dataframe) >= 3
