from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from swing_rsi.data.loader import load_ohlcv_csv, save_ohlcv_csv
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


def _write_demo_scanner_snapshot(root: Path) -> Path:
    frame = load_ohlcv_csv(root / "data" / "raw" / "DEMO.csv")
    as_of = pd.Timestamp(frame.index[-20])
    analog_date = pd.Timestamp(frame.index[-120]).date().isoformat()
    output = root / "artifacts" / "scanner"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "demo_scanner.csv"
    pd.DataFrame(
        [
            {
                "scan_id": "scan-demo",
                "as_of_date": as_of.date().isoformat(),
                "ticker": "DEMO",
                "direction": "Bullish",
                "horizon": 10,
                "signal_close": float(frame.loc[as_of, "Close"]),
                "calibrated_probability": 0.64,
                "expected_return": 0.023,
                "expected_mfe": 0.041,
                "expected_mae": -0.014,
                "target_before_stop_probability": 0.58,
                "composite_utility_score": 0.01472,
                "liquidity_score": 25_000_000.0,
                "regime": "demo_regime",
                "sector": "demo",
                "top_attribution_categories": (
                    "stock_price_structure:32.0%; residual/unexplained:6.0%"
                ),
                "top_confirming_relationships": "DEMO above own 20-session baseline",
                "top_divergences": "No material divergence",
                "model_id": "model-demo",
                "model_state": "CHAMPION",
                "feature_snapshot_hash": "feature-demo",
                "candidate_status": "ACTIONABLE_PAPER_CANDIDATE",
                "exclusion_reason": "",
                "supporting_evidence": "Relative volume above rolling context",
                "historical_analogs": json.dumps(
                    [
                        {
                            "Date": analog_date,
                            "symbol": "DEMO",
                            "regime": "demo_regime",
                            "label_forward_return_10": 0.018,
                            "label_mfe_10": 0.035,
                            "label_mae_10": -0.012,
                            "label_target_before_stop_10": 1,
                        }
                    ]
                ),
            }
        ]
    ).to_csv(path, index=False)
    return path


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


def test_candidate_attribution_renders_scanner_evidence(
    demo_dashboard_root: Path,
) -> None:
    _write_demo_scanner_snapshot(demo_dashboard_root)

    app = AppTest.from_file("dashboard/sections/candidate_attribution.py").run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    subheaders = {subheader.value for subheader in app.subheader}
    assert "Recent Price Context" in subheaders
    assert "Historical Analogs" in subheaders
    assert "Model And Snapshot Details" in subheaders
    assert app.selectbox[0].value == "DEMO Bullish h10 model-demo"
    assert len(app.dataframe) >= 2


def test_portfolio_backtest_renders_actionable_scanner_replay(
    demo_dashboard_root: Path,
) -> None:
    _write_demo_scanner_snapshot(demo_dashboard_root)
    app = AppTest.from_file("dashboard/sections/portfolio_backtests.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    app.button[0].click()
    app.run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    subheaders = {subheader.value for subheader in app.subheader}
    assert "Equity" in subheaders
    assert "Drawdown" in subheaders
    assert "Trade Ledger" in subheaders
    assert "Candidate Audit" in subheaders
    assert len(app.dataframe) >= 3
