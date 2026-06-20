from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from swing_rsi.engine.drift import build_drift_report
from swing_rsi.engine.features import build_feature_panel, reject_label_columns
from swing_rsi.engine.forward import (
    advance_forward_positions,
    create_pending_events_from_snapshot,
    list_forward_events,
)
from swing_rsi.engine.labels import LabelConfig, build_label_panel, build_symbol_labels
from swing_rsi.engine.models import BaseRateClassifier, ModelBundle, predict_bundle
from swing_rsi.engine.portfolio import PortfolioBacktestConfig, backtest_scanner_candidates
from swing_rsi.engine.registry import RegisteredModel, promote_model, register_model
from swing_rsi.engine.scanner import ScannerConfig, latest_common_session, run_scanner
from swing_rsi.engine.splits import chronological_train_calibration_holdout_split
from swing_rsi.engine.storage import engine_connection
from swing_rsi.engine.universe import UniverseConfig, UniverseSymbol, load_universe_config
from swing_rsi.sample_data import generate_sample_ohlcv


class ConstantClassifier:
    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return np.tile(np.array([[0.25, 0.75]]), (len(frame), 1))


class IdentityCalibrator:
    def predict(self, values: np.ndarray) -> np.ndarray:
        return values


class ConstantRegressor:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.full(len(frame), self.value)


def _universe() -> UniverseConfig:
    return UniverseConfig(
        name="test",
        provider="fmp",
        default_start="2018-01-02",
        symbols=(
            UniverseSymbol("AAPL", role="stock", sector="technology", sector_proxy="XLK"),
            UniverseSymbol("SPY", role="broad_market_etf", sector="broad_market", benchmark=True),
            UniverseSymbol("XLK", role="sector_etf", sector="technology"),
            UniverseSymbol("SQQQ", role="leveraged_inverse_etf", sector="inverse_technology"),
        ),
        relationships={"SPY": ("SQQQ",)},
    )


def _frames(rows: int = 520) -> dict[str, pd.DataFrame]:
    return {
        "AAPL": generate_sample_ohlcv(rows=rows, seed=1),
        "SPY": generate_sample_ohlcv(rows=rows, seed=2),
        "XLK": generate_sample_ohlcv(rows=rows, seed=3),
        "SQQQ": generate_sample_ohlcv(rows=rows, seed=4),
    }


def test_universe_parsing_and_symbol_normalization(tmp_path: Path) -> None:
    path = tmp_path / "core.yaml"
    path.write_text(
        """
name: demo
provider: fmp
default_start: "2018-01-02"
symbols:
  - symbol: aapl.csv
    enabled: true
    role: stock
    sector: technology
relationships: []
""",
        encoding="utf-8",
    )

    universe = load_universe_config(path)

    assert universe.enabled_symbols == ("AAPL",)
    assert universe.snapshot_id


def test_features_are_backward_looking_when_future_rows_change() -> None:
    frames = _frames()
    baseline = build_feature_panel(frames, _universe()).frame
    mutated = {symbol: frame.copy() for symbol, frame in frames.items()}
    cutoff = pd.Timestamp("2019-06-03")
    future_mask = mutated["AAPL"].index > cutoff
    mutated["AAPL"].loc[future_mask, ["Open", "High", "Low", "Close"]] *= 3.0
    rerun = build_feature_panel(mutated, _universe()).frame

    before = baseline[(baseline["symbol"] == "AAPL") & (pd.to_datetime(baseline["Date"]) <= cutoff)]
    after = rerun[(rerun["symbol"] == "AAPL") & (pd.to_datetime(rerun["Date"]) <= cutoff)]

    pd.testing.assert_frame_equal(
        before.reset_index(drop=True),
        after.reset_index(drop=True),
        check_exact=False,
        atol=1e-12,
        rtol=1e-12,
    )


def test_feature_registry_covers_generated_columns_and_relationship_regime_features() -> None:
    result = build_feature_panel(_frames(), _universe())
    feature_columns = {
        column
        for column in result.frame.columns
        if column
        not in {
            "Date",
            "symbol",
            "role",
            "sector",
            "sector_proxy",
            "market_regime_label",
        }
        and not str(column).startswith("label_")
    }
    spec_names = {spec.name for spec in result.specs}

    assert feature_columns <= spec_names
    assert any(column.startswith("relationship_mutual_info_spy_sqqq") for column in feature_columns)
    assert "market_regime_cluster_expanding" in feature_columns


def test_label_engine_uses_next_open_and_separates_label_columns(
    simple_ohlcv: pd.DataFrame,
) -> None:
    labels = build_symbol_labels(simple_ohlcv, LabelConfig(horizons=(3,)))
    first_date = simple_ohlcv.index[0]
    expected = (simple_ohlcv["Close"].iloc[3] / simple_ohlcv["Open"].iloc[1]) - 1.0

    assert labels.loc[first_date, "label_bull_forward_return_3"] == pytest.approx(expected)
    with pytest.raises(ValueError):
        reject_label_columns(["return_1", "label_bull_forward_return_3"])


def test_chronological_split_purges_overlapping_label_windows() -> None:
    frames = _frames(rows=420)
    features = build_feature_panel(frames, _universe()).frame
    labels = build_label_panel(frames, LabelConfig(horizons=(10,)))
    modeling = features.merge(labels, on=["Date", "symbol"], how="inner")

    split = chronological_train_calibration_holdout_split(modeling, horizon=10)

    calibration_start = pd.Timestamp(split.calibration_start)
    holdout_start = pd.Timestamp(split.holdout_start)
    assert pd.to_datetime(split.train["label_end_date_10"]).max() < calibration_start
    assert pd.to_datetime(split.calibration["label_end_date_10"]).max() < holdout_start


def _registered_model(model_id: str, *, state: str = "CHALLENGER") -> RegisteredModel:
    return RegisteredModel(
        model_id=model_id,
        task="swing_direction_probability",
        horizon=10,
        direction="bull",
        family="test",
        state=state,  # type: ignore[arg-type]
        training_start="2020-01-01",
        training_end="2021-01-01",
        validation_start="2021-01-04",
        validation_end="2021-06-01",
        holdout_start="2021-06-02",
        holdout_end="2022-01-01",
        universe_snapshot_id="u",
        feature_manifest_hash="f",
        raw_manifest_hashes=(),
        hyperparameters={},
        metrics={"holdout_mean_return_lcb_90": 0.01},
        calibration_metrics={"holdout_brier": 0.2},
        quality_gates={"gate": True},
        artifact_path="artifact.joblib",
        code_commit_hash=None,
        created_at_utc=datetime.now(UTC).isoformat(),
    )


def test_model_registry_is_immutable_and_promotion_is_explicit(tmp_path: Path) -> None:
    db = tmp_path / "engine.sqlite3"
    model = _registered_model("model-a")

    register_model(db, model)
    with pytest.raises(ValueError):
        register_model(db, model)
    promoted = promote_model(db, "model-a")

    assert promoted.state == "CHAMPION"


def test_naive_base_rate_classifier_is_deterministic_baseline() -> None:
    classifier = BaseRateClassifier().fit(
        pd.DataFrame({"feature": [1.0, 2.0, 3.0, 4.0]}),
        pd.Series([0, 1, 1, 1]),
    )

    probabilities = classifier.predict_proba(pd.DataFrame({"feature": [10.0, 20.0]}))

    assert probabilities.shape == (2, 2)
    assert probabilities[:, 1].tolist() == pytest.approx([0.75, 0.75])


def test_drift_report_flags_shift_without_mutating_models() -> None:
    reference = pd.DataFrame({"feature_a": [0.0, 1.0, 2.0, 3.0], "feature_b": [10.0] * 4})
    current = pd.DataFrame({"feature_a": [10.0, 11.0], "feature_b": [10.0, 10.0]})

    report = build_drift_report(
        model_id="model-a",
        as_of_date="2024-01-02",
        reference_features=reference,
        current_features=current,
        feature_columns=("feature_a", "feature_b"),
        reference_probabilities=np.array([0.45, 0.50, 0.55]),
        current_probabilities=np.array([0.90, 0.92]),
    )

    assert report.model_id == "model-a"
    assert report.alert_count == 2
    assert {metric.name for metric in report.metrics} == {
        "feature_distribution_mean_abs_z",
        "prediction_probability_mean_shift",
    }


def _bundle(model_id: str = "model-a") -> ModelBundle:
    training = pd.DataFrame({"f1": [0.0, 1.0, 2.0], "dollar_volume": [10_000_000.0] * 3})
    labels = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "symbol": ["AAPL", "AAPL", "AAPL"],
            "label_bull_forward_return_10": [0.01, 0.02, -0.01],
            "label_bull_mfe_10": [0.03, 0.04, 0.01],
            "label_bull_mae_10": [-0.01, -0.02, -0.03],
        }
    )
    return ModelBundle(
        model_id=model_id,
        direction="bull",
        horizon=10,
        family="test",
        feature_columns=("f1", "dollar_volume"),
        feature_family_by_column={
            "f1": "stock-specific price structure",
            "dollar_volume": "volume participation",
        },
        classifier=ConstantClassifier(),
        calibrator=IdentityCalibrator(),
        target_before_stop_model=ConstantClassifier(),
        target_before_stop_calibrator=IdentityCalibrator(),
        return_model=ConstantRegressor(0.02),
        mfe_model=ConstantRegressor(0.04),
        mae_model=ConstantRegressor(-0.015),
        training_medians={"f1": 1.0, "dollar_volume": 10_000_000.0},
        training_means={"f1": 1.0, "dollar_volume": 10_000_000.0},
        training_stds={"f1": 1.0, "dollar_volume": 1.0},
        training_matrix=training,
        training_labels=labels,
        metrics={},
        calibration_metrics={},
    )


def test_predict_bundle_outputs_separate_target_before_stop_probability() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [2.0],
            "dollar_volume": [20_000_000.0],
        }
    )

    prediction = predict_bundle(_bundle(), frame)

    assert "target_before_stop_probability" in prediction.columns
    assert prediction["target_before_stop_probability"].iloc[0] == pytest.approx(0.75)


def test_scanner_snapshot_is_idempotent_and_contains_residual_attribution(tmp_path: Path) -> None:
    feature_panel = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [2.0],
            "dollar_volume": [20_000_000.0],
            "sector": ["technology"],
            "market_regime_label": ["mixed"],
        }
    )

    first = run_scanner(
        feature_panel,
        bundles=(_bundle(), _bundle("model-b")),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        config=ScannerConfig(probability_threshold=0.5),
    )
    second = run_scanner(
        feature_panel,
        bundles=(_bundle(), _bundle("model-b")),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        config=ScannerConfig(probability_threshold=0.5),
    )

    assert first.scan_id == second.scan_id
    assert len(first.rows) == 2
    assert "residual/unexplained" in first.rows["top_attribution_categories"].iloc[0]
    assert "historical_analogs" in first.rows.columns
    assert "signal_close" in first.rows.columns
    with engine_connection(tmp_path / "engine.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM scanner_candidates").fetchone()[0] == 2


def test_latest_common_session_uses_all_enabled_symbol_histories() -> None:
    frames = _frames(rows=300)
    frames["SQQQ"] = frames["SQQQ"].iloc[:-5]

    common = latest_common_session(frames, _universe().enabled_symbols)

    assert common == frames["SQQQ"].index.max()
    assert common < frames["AAPL"].index.max()


def test_forward_events_are_append_only_and_idempotent(tmp_path: Path) -> None:
    scanner_rows = pd.DataFrame(
        [
            {
                "candidate_status": "ACTIONABLE_PAPER_CANDIDATE",
                "as_of_date": "2024-01-02",
                "ticker": "AAPL",
                "direction": "Bullish",
                "model_id": "model-a",
                "scan_id": "scan-a",
                "feature_snapshot_hash": "hash-a",
                "expected_return": 0.02,
                "expected_mfe": 0.04,
                "expected_mae": -0.01,
                "calibrated_probability": 0.75,
                "horizon": 10,
            }
        ]
    )

    assert create_pending_events_from_snapshot(tmp_path / "engine.sqlite3", scanner_rows) == 2
    assert create_pending_events_from_snapshot(tmp_path / "engine.sqlite3", scanner_rows) == 0
    events = list_forward_events(tmp_path / "engine.sqlite3")

    assert len(events) == 2
    assert set(events["event_type"]) == {"SIGNAL_CREATED", "ENTRY_PENDING"}


def test_forward_positions_fill_mark_exit_and_remain_idempotent(
    tmp_path: Path,
    simple_ohlcv: pd.DataFrame,
) -> None:
    scanner_rows = pd.DataFrame(
        [
            {
                "candidate_status": "ACTIONABLE_PAPER_CANDIDATE",
                "as_of_date": simple_ohlcv.index[10].date().isoformat(),
                "ticker": "AAPL",
                "direction": "Bullish",
                "model_id": "model-a",
                "scan_id": "scan-a",
                "feature_snapshot_hash": "hash-a",
                "expected_return": 0.02,
                "expected_mfe": 0.04,
                "expected_mae": -0.01,
                "calibrated_probability": 0.75,
                "horizon": 5,
            }
        ]
    )
    db_path = tmp_path / "engine.sqlite3"

    assert create_pending_events_from_snapshot(db_path, scanner_rows) == 2
    inserted = advance_forward_positions(db_path, {"AAPL": simple_ohlcv})
    assert inserted > 0
    assert advance_forward_positions(db_path, {"AAPL": simple_ohlcv}) == 0
    events = list_forward_events(db_path)

    assert "ENTRY_FILLED" in set(events["event_type"])
    assert "TARGET_UPDATED" in set(events["event_type"])
    assert "STOP_UPDATED" in set(events["event_type"])
    assert "POSITION_MARKED" in set(events["event_type"])
    assert "EXIT_FILLED" in set(events["event_type"])
    target_event = events.loc[events["event_type"] == "TARGET_UPDATED"].iloc[0]
    assert dict(target_event["payload"])["frozen_price"] > 0
    exit_event = events.loc[events["event_type"] == "EXIT_FILLED"].iloc[0]
    payload = dict(exit_event["payload"])
    assert payload["entry_date"] == simple_ohlcv.index[11].date().isoformat()
    assert payload["exit_reason"] in {"target", "stop", "stop_intraday_ambiguous", "time_exit"}
    assert "net_realized_return" in payload


def test_portfolio_backtester_enters_next_open_and_handles_shorts(
    simple_ohlcv: pd.DataFrame,
) -> None:
    candidates = pd.DataFrame(
        [
            {
                "as_of_date": simple_ohlcv.index[10].date().isoformat(),
                "ticker": "AAPL",
                "direction": "Bearish",
                "candidate_status": "ACTIONABLE_PAPER_CANDIDATE",
                "composite_utility_score": 1.0,
                "model_id": "model-a",
                "sector": "technology",
            },
            {
                "as_of_date": simple_ohlcv.index[25].date().isoformat(),
                "ticker": "AAPL",
                "direction": "Bullish",
                "candidate_status": "ACTIONABLE_PAPER_CANDIDATE",
                "composite_utility_score": 0.9,
                "model_id": "model-a",
                "sector": "technology",
            },
        ]
    )

    result = backtest_scanner_candidates(
        {"AAPL": simple_ohlcv},
        candidates,
        config=PortfolioBacktestConfig(horizon=5),
    )

    assert len(result.trades) == 2
    assert result.trades["entry_date"].iloc[0] == simple_ohlcv.index[11].date().isoformat()
    assert result.trades["direction"].iloc[0] == "Bearish"
    assert {"Date", "daily_return", "equity", "drawdown", "gross_exposure", "net_exposure"} <= set(
        result.equity.columns
    )
    assert "annualized_return" in result.metrics
    assert not result.yearly_returns.empty
    assert not result.sector_returns.empty
