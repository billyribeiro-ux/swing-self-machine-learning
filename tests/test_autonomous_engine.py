from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from swing_rsi.engine.calibration_governance import TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION
from swing_rsi.engine.drift import build_drift_report
from swing_rsi.engine.features import build_feature_panel, reject_label_columns
from swing_rsi.engine.forward import (
    advance_forward_positions,
    create_pending_events_from_snapshot,
    list_forward_events,
)
from swing_rsi.engine.gates import GATE_VALUE_NOT_AVAILABLE, make_gate, promotion_eligibility
from swing_rsi.engine.labels import LabelConfig, build_label_panel, build_symbol_labels
from swing_rsi.engine.models import (
    TARGET_BEFORE_STOP_HEAD,
    BaseRateClassifier,
    DiscoveryConfig,
    ModelBundle,
    discover_models,
    load_model_bundle,
    model_plugins,
    predict_bundle,
)
from swing_rsi.engine.ood import PREDICTION_OOD_GOVERNANCE_VERSION
from swing_rsi.engine.portfolio import PortfolioBacktestConfig, backtest_scanner_candidates
from swing_rsi.engine.registry import RegisteredModel, promote_model, register_model
from swing_rsi.engine.scanner import ScannerConfig, latest_common_session, run_scanner
from swing_rsi.engine.selection import SelectionPolicy
from swing_rsi.engine.splits import chronological_train_calibration_holdout_split
from swing_rsi.engine.storage import engine_connection
from swing_rsi.engine.universe import UniverseConfig, UniverseSymbol, load_universe_config
from swing_rsi.sample_data import generate_sample_ohlcv


class ConstantClassifier:
    def __init__(self, probability: float = 0.75) -> None:
        self.probability = probability

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return np.tile(np.array([[1.0 - self.probability, self.probability]]), (len(frame), 1))


class FeatureEchoClassifier:
    def __init__(self, feature: str) -> None:
        self.feature = feature

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        positive = frame[self.feature].to_numpy(dtype=float)
        positive = np.clip(positive, 0.0, 1.0)
        return np.column_stack([1.0 - positive, positive])


class IdentityCalibrator:
    def predict(self, values: np.ndarray) -> np.ndarray:
        return values


class MultiplierCalibrator:
    def __init__(self, multiplier: float) -> None:
        self.multiplier = multiplier

    def predict(self, values: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(values, dtype=float) * self.multiplier, 0.0, 1.0)


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


def test_model_plugins_define_classifier_and_regressor_interfaces() -> None:
    plugins = {plugin.name: plugin for plugin in model_plugins()}

    assert set(plugins) == {
        "naive_base_rate",
        "logistic_regression",
        "hist_gradient_boosting",
        "extra_trees",
    }
    for plugin in plugins.values():
        assert plugin.classifier_factory(42) is not None
        assert plugin.regressor_factory(42) is not None


def test_discovery_persists_target_before_stop_feature_screen_metadata(tmp_path: Path) -> None:
    dates = pd.date_range("2019-01-02", periods=80, freq="B")
    rows: list[dict[str, object]] = []
    for symbol_offset, symbol in enumerate(("AAPL", "MSFT")):
        for position, date_value in enumerate(dates):
            tbs_target = int((position + symbol_offset) % 4 == 0)
            positive_target = int((position + symbol_offset) % 5 < 3)
            row: dict[str, object] = {
                "Date": date_value,
                "symbol": symbol,
                "role": "stock",
                "sector": "technology",
                "sector_proxy": "XLK",
                "market_regime_label": "mixed",
                "Open": 100.0 + position,
                "High": 101.0 + position,
                "Low": 99.0 + position,
                "Close": 100.5 + position,
                "Volume": 1_000_000.0,
                "dollar_volume": 100_000_000.0,
                "primary_signal": float(positive_target),
                "late_market_relative_signal": float(tbs_target),
                "label_bull_positive_return_10": float(positive_target),
                "label_bull_forward_return_10": 0.02 if positive_target else -0.01,
                "label_bull_mfe_10": 0.04,
                "label_bull_mae_10": -0.02,
                "label_bull_target_before_stop_10": float(tbs_target),
                "label_end_date_10": date_value + pd.offsets.BDay(10),
            }
            for index in range(70):
                row[f"noise_{index:02d}"] = float(np.sin(position + index))
            rows.append(row)
    frame = pd.DataFrame(rows)
    family_map = {column: "returns_momentum" for column in frame.columns}
    family_map["late_market_relative_signal"] = "market_relative"
    family_map["primary_signal"] = "returns_momentum"

    result = discover_models(
        frame,
        db_path=tmp_path / "engine.sqlite3",
        artifact_dir=tmp_path / "models",
        universe_snapshot_id="u",
        feature_manifest_hash="features",
        feature_family_by_column=family_map,
        config=DiscoveryConfig(
            horizons=(10,),
            directions=("bull",),
            minimum_training_samples=20,
            minimum_holdout_samples=10,
            max_features=20,
            mutual_information_top_k=8,
            research_start=None,
            random_seed=7,
        ),
        code_root=tmp_path,
    )
    learned = next(
        model for model in result.registered_models if model.family == "logistic_regression"
    )
    bundle = load_model_bundle(learned.artifact_path)

    bundle_head_target = bundle.head_feature_columns[TARGET_BEFORE_STOP_HEAD]
    assert bundle_head_target
    assert "late_market_relative_signal" in bundle_head_target
    assert learned.metrics["target_before_stop_selected_feature_count"] == len(bundle_head_target)
    assert learned.metrics["target_before_stop_screening_target"] == (
        "label_bull_target_before_stop_10"
    )
    assert (
        learned.metrics["target_before_stop_screening_manifest_hash"]
        == (bundle.head_feature_manifests[TARGET_BEFORE_STOP_HEAD])
    )
    assert "late_market_relative_signal" in str(
        learned.metrics["target_before_stop_feature_screen_audit_json"]
    )


def test_drift_report_flags_shift_without_mutating_models() -> None:
    reference = pd.DataFrame(
        {
            "feature_a": [0.0, 1.0, 2.0, 3.0],
            "feature_b": [10.0] * 4,
            "relationship_corr_spy_sqqq_63": [0.1, 0.2, 0.1, 0.2],
        }
    )
    current = pd.DataFrame(
        {
            "feature_a": [10.0, 11.0],
            "feature_b": [10.0, 10.0],
            "relationship_corr_spy_sqqq_63": [2.0, 2.1],
        }
    )

    report = build_drift_report(
        model_id="model-a",
        as_of_date="2024-01-02",
        reference_features=reference,
        current_features=current,
        feature_columns=("feature_a", "feature_b", "relationship_corr_spy_sqqq_63"),
        reference_probabilities=np.array([0.45, 0.50, 0.55]),
        current_probabilities=np.array([0.90, 0.92]),
        reference_returns=np.array([0.01, 0.02, 0.00]),
        current_returns=np.array([-0.05, -0.04]),
        reference_brier=0.20,
        current_brier=0.31,
    )

    assert report.model_id == "model-a"
    assert report.alert_count >= 4
    assert {metric.name for metric in report.metrics} == {
        "feature_distribution_mean_abs_z",
        "relationship_regime_mean_abs_z",
        "prediction_probability_mean_shift",
        "realized_performance_mean_return_shift",
        "calibration_brier_deterioration",
    }


def _ood_metrics(
    *,
    return_low: float = -0.10,
    return_high: float = 0.10,
    return_severity_limit: float = 0.10,
) -> dict[str, object]:
    metrics: dict[str, object] = {
        "prediction_ood_governance_version": PREDICTION_OOD_GOVERNANCE_VERSION,
        "prediction_unit_contract": "decimal_return",
        "prediction_values_finite": True,
        "prediction_probability_contract_valid": True,
        "prediction_head_bound_mapping_valid": True,
        "prediction_bounds_training_only": True,
        "prediction_path_metric_sign_valid": True,
        "classification_prediction_values_finite": True,
        "classification_probability_contract_valid": True,
        "classification_prediction_nonfinite_count": 0,
        "classification_probability_out_of_range_count": 0,
    }
    head_bounds = {
        "return": (return_low, return_high, return_severity_limit),
        "mfe": (0.0, 0.20, 0.10),
        "mae": (-0.20, 0.0, 0.10),
    }
    for head, (low, high, severity_limit) in head_bounds.items():
        metrics.update(
            {
                f"{head}_prediction_ood_governance_version": PREDICTION_OOD_GOVERNANCE_VERSION,
                f"{head}_prediction_unit_contract": "decimal_return",
                f"{head}_prediction_bound_low_train_q01": low,
                f"{head}_prediction_bound_high_train_q99": high,
                f"{head}_prediction_bound_robust_range_train_q01_q99": high - low,
                f"{head}_ood_bound_provenance": "training_targets_only",
                f"{head}_ood_bound_head": head,
                f"{head}_ood_bound_direction": "bull",
                f"{head}_ood_bound_horizon": 10,
                f"{head}_prediction_head_bound_mapping_valid": True,
                f"{head}_prediction_bounds_training_only": True,
                f"{head}_prediction_values_finite": True,
                f"{head}_prediction_path_metric_sign_valid": True,
                f"{head}_calibration_ood_rate": 0.0,
                f"{head}_calibration_ood_rate_limit": 0.02,
                f"{head}_calibration_ood_q99_severity": 0.0,
                f"{head}_ood_severity_q99_limit": severity_limit,
                f"{head}_holdout_ood_rate": 0.0,
                f"{head}_holdout_ood_q99_severity": 0.0,
                f"{head}_holdout_ood_max_severity": 0.0,
                f"{head}_holdout_prediction_nonfinite_count": 0,
            }
        )
    return metrics


def _policy_metrics(
    policy: SelectionPolicy | None = None,
    *,
    policy_hash: str = "policy-hash",
    generation: str = "generation-a",
    artifact_hash: str = "artifact-a",
    include_ood: bool = True,
    return_high: float = 0.10,
    return_severity_limit: float = 0.10,
    include_tbs_calibration: bool = True,
    calibration_method: str = "identity",
    calibration_manifest_hash: str = "calibration-manifest-a",
    calibrator_artifact_hash: str = "calibrator-artifact-a",
) -> dict[str, object]:
    policy = policy or SelectionPolicy()
    metrics = {
        **(
            _ood_metrics(
                return_high=return_high,
                return_severity_limit=return_severity_limit,
            )
            if include_ood
            else {}
        ),
        "selection_policy_json": json.dumps(asdict(policy), sort_keys=True),
        "selection_policy_configuration_hash": policy_hash,
        "generation": generation,
        "artifact_hash": artifact_hash,
    }
    if include_tbs_calibration:
        metrics.update(
            _tbs_calibration_metrics(
                calibration_method=calibration_method,
                calibration_manifest_hash=calibration_manifest_hash,
                calibrator_artifact_hash=calibrator_artifact_hash,
            )
        )
    return metrics


def _tbs_calibration_metrics(
    *,
    calibration_method: str = "identity",
    calibration_manifest_hash: str = "calibration-manifest-a",
    calibrator_artifact_hash: str = "calibrator-artifact-a",
) -> dict[str, object]:
    return {
        "target_before_stop_calibration_governance_schema": (
            TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION
        ),
        "target_before_stop_calibration_method": calibration_method,
        "target_before_stop_calibration_manifest_hash": calibration_manifest_hash,
        "target_before_stop_calibrator_artifact_hash": calibrator_artifact_hash,
        "target_before_stop_calibration_selection_reason": "test_identity",
    }


def _bundle(
    model_id: str = "model-a",
    *,
    probability: float = 0.75,
    target_probability: float = 0.75,
    expected_return: float = 0.02,
    policy: SelectionPolicy | None = None,
    include_policy: bool = True,
    include_ood: bool = True,
    policy_hash: str = "policy-hash",
    generation: str = "generation-a",
    artifact_hash: str = "artifact-a",
    return_high: float = 0.10,
    return_severity_limit: float = 0.10,
    target_feature_columns: tuple[str, ...] | None = None,
    target_classifier: object | None = None,
    target_calibrator: object | None = None,
    target_manifest: str = "target-before-stop-manifest",
    include_tbs_calibration: bool = True,
    calibration_method: str = "identity",
    calibration_manifest_hash: str = "calibration-manifest-a",
    calibrator_artifact_hash: str = "calibrator-artifact-a",
    include_feature_screen_metadata: bool = True,
) -> ModelBundle:
    target_feature_columns = target_feature_columns or ("f1", "dollar_volume")
    training = pd.DataFrame(
        {
            "f1": [0.0, 1.0, 2.0],
            "target_signal": [0.25, 0.75, 0.90],
            "dollar_volume": [10_000_000.0] * 3,
        }
    )
    labels = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "symbol": ["AAPL", "AAPL", "AAPL"],
            "label_bull_forward_return_10": [0.01, 0.02, -0.01],
            "label_bull_mfe_10": [0.03, 0.04, 0.01],
            "label_bull_mae_10": [-0.01, -0.02, -0.03],
            "label_bull_target_before_stop_10": [1.0, 1.0, 0.0],
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
        classifier=ConstantClassifier(probability),
        calibrator=IdentityCalibrator(),
        target_before_stop_model=target_classifier or ConstantClassifier(target_probability),
        target_before_stop_calibrator=target_calibrator or IdentityCalibrator(),
        return_model=ConstantRegressor(expected_return),
        mfe_model=ConstantRegressor(0.04),
        mae_model=ConstantRegressor(-0.015),
        training_medians={"f1": 1.0, "dollar_volume": 10_000_000.0},
        training_means={"f1": 1.0, "dollar_volume": 10_000_000.0},
        training_stds={"f1": 1.0, "dollar_volume": 1.0},
        training_matrix=training,
        training_labels=labels,
        metrics=(
            _policy_metrics(
                policy,
                policy_hash=policy_hash,
                generation=generation,
                artifact_hash=artifact_hash,
                include_ood=include_ood,
                return_high=return_high,
                return_severity_limit=return_severity_limit,
                include_tbs_calibration=include_tbs_calibration,
                calibration_method=calibration_method,
                calibration_manifest_hash=calibration_manifest_hash,
                calibrator_artifact_hash=calibrator_artifact_hash,
            )
            if include_policy
            else {
                **(
                    _ood_metrics(
                        return_high=return_high,
                        return_severity_limit=return_severity_limit,
                    )
                    if include_ood
                    else {}
                ),
                **(
                    _tbs_calibration_metrics(
                        calibration_method=calibration_method,
                        calibration_manifest_hash=calibration_manifest_hash,
                        calibrator_artifact_hash=calibrator_artifact_hash,
                    )
                    if include_tbs_calibration
                    else {}
                ),
            }
        ),
        calibration_metrics={},
        head_feature_columns={
            "primary_positive_return": ("f1", "dollar_volume"),
            TARGET_BEFORE_STOP_HEAD: target_feature_columns,
            "expected_return": ("f1", "dollar_volume"),
            "mfe": ("f1", "dollar_volume"),
            "mae": ("f1", "dollar_volume"),
        },
        head_feature_manifests={
            "primary_positive_return": "primary-manifest",
            TARGET_BEFORE_STOP_HEAD: target_manifest,
            "expected_return": "return-manifest",
            "mfe": "mfe-manifest",
            "mae": "mae-manifest",
        },
        feature_screen_metadata=(
            {
                TARGET_BEFORE_STOP_HEAD: {
                    "screening_schema_version": "target_specific_feature_screen_v1",
                    "selected_feature_count": len(target_feature_columns),
                    "selected_feature_families": {"test": len(target_feature_columns)},
                    "selected_feature_manifest_hash": target_manifest,
                }
            }
            if include_feature_screen_metadata
            else {}
        ),
    )


def _scanner_feature_panel(symbols: tuple[str, ...] = ("AAPL",)) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"] * len(symbols)),
            "symbol": list(symbols),
            "f1": [2.0] * len(symbols),
            "target_signal": [0.75] * len(symbols),
            "dollar_volume": [20_000_000.0] * len(symbols),
            "sector": ["technology"] * len(symbols),
            "market_regime_label": ["mixed"] * len(symbols),
        }
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


def test_target_before_stop_classifier_receives_own_selected_columns() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            "target_signal": [0.82],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(
        target_feature_columns=("target_signal",),
        target_classifier=FeatureEchoClassifier("target_signal"),
    )

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["calibrated_probability"] == pytest.approx(0.75)
    assert prediction["target_before_stop_probability"] == pytest.approx(0.82)
    assert prediction["target_before_stop_feature_manifest_hash"] == "target-before-stop-manifest"


def test_target_before_stop_prediction_uses_frozen_selected_calibrator() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            "target_signal": [0.80],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(
        target_feature_columns=("target_signal",),
        target_classifier=FeatureEchoClassifier("target_signal"),
        target_calibrator=MultiplierCalibrator(0.50),
        calibration_method="sigmoid",
        calibration_manifest_hash="calibration-manifest-sigmoid",
        calibrator_artifact_hash="calibrator-artifact-sigmoid",
    )

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["target_before_stop_raw_probability"] == pytest.approx(0.80)
    assert prediction["target_before_stop_probability"] == pytest.approx(0.40)
    assert prediction["target_before_stop_calibration_method"] == "sigmoid"
    assert (
        prediction["target_before_stop_calibration_manifest_hash"] == "calibration-manifest-sigmoid"
    )


def test_predict_bundle_flags_missing_target_before_stop_features_without_substitution() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(
        target_feature_columns=("target_signal",),
        target_classifier=FeatureEchoClassifier("target_signal"),
    )

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert bool(prediction["target_before_stop_required_feature_missing"]) is True
    assert prediction["target_before_stop_missing_features"] == "target_signal"
    assert pd.isna(prediction["target_before_stop_probability"])


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
    assert "label_bull_target_before_stop_10" in first.rows["historical_analogs"].iloc[0]
    with engine_connection(tmp_path / "engine.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM scanner_candidates").fetchone()[0] == 2


def test_scanner_rejects_missing_target_before_stop_features_explicitly(tmp_path: Path) -> None:
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

    snapshot = run_scanner(
        feature_panel,
        bundles=(
            _bundle(
                target_feature_columns=("target_signal",),
                target_classifier=FeatureEchoClassifier("target_signal"),
            ),
        ),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert "target_before_stop_required_feature_missing" in row["exclusion_reason"]
    assert bool(row["target_before_stop_required_feature_missing"]) is True


def test_scanner_rejects_missing_target_before_stop_calibration_metadata(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(_bundle(include_tbs_calibration=False),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert "target_before_stop_calibration_metadata_missing" in row["exclusion_reason"]
    assert bool(row["target_before_stop_calibration_metadata_missing"]) is True


def test_legacy_shared_screen_artifact_is_not_marked_new_calibration_missing() -> None:
    prediction = predict_bundle(
        _bundle(include_tbs_calibration=False, include_feature_screen_metadata=False),
        _scanner_feature_panel(),
    ).iloc[0]

    assert prediction["target_before_stop_feature_screen_schema"] == "legacy_shared_feature_screen"
    assert bool(prediction["target_before_stop_calibration_metadata_missing"]) is False


def test_scanner_uses_frozen_target_before_stop_calibrator(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(
            _bundle(
                target_feature_columns=("target_signal",),
                target_classifier=FeatureEchoClassifier("target_signal"),
                target_calibrator=MultiplierCalibrator(0.50),
                calibration_method="sigmoid",
                calibration_manifest_hash="calibration-manifest-sigmoid",
                calibrator_artifact_hash="calibrator-artifact-sigmoid",
            ),
        ),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert row["target_before_stop_raw_probability"] == pytest.approx(0.75)
    assert row["target_before_stop_probability"] == pytest.approx(0.375)
    assert row["target_before_stop_calibration_method"] == "sigmoid"
    assert row["target_before_stop_calibration_manifest_hash"] == "calibration-manifest-sigmoid"


def test_scanner_rejects_promoted_model_without_gate_eligibility(tmp_path: Path) -> None:
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

    snapshot = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": False},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert row["exclusion_reason"] == "model_quality_gates_failed"
    assert bool(row["model_quality_gate_eligible"]) is False


def test_scanner_eligibility_uses_persisted_temporal_fold_gates(tmp_path: Path) -> None:
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
    gates = (
        make_gate(
            gate_id="temporal_fold_stability_evidence_available",
            gate_name="Temporal Fold Stability Evidence Available",
            category="temporal stability",
            scope="selected_candidates",
            metric_name="temporal_fold_evidence_status",
            threshold="AVAILABLE",
            comparator="is available",
            actual_value="UNAVAILABLE",
            status="FAIL",
            mandatory=True,
            evidence_source="test",
            reason=(
                "Temporal-fold stability evidence is unavailable because only 0 folds contained "
                "selected observations."
            ),
            configuration_hash_value="test",
        ),
        make_gate(
            gate_id="temporal_fold_stability_min_050",
            gate_name="Temporal Fold Positive Fraction Minimum",
            category="temporal stability",
            scope="selected_candidates",
            metric_name="temporal_fold_positive_fraction",
            threshold=0.50,
            comparator=">=",
            actual_value=GATE_VALUE_NOT_AVAILABLE,
            status="NOT_APPLICABLE",
            mandatory=True,
            evidence_source="test",
            reason=(
                "Temporal-fold stability threshold cannot be evaluated because valid "
                "temporal-fold evidence is unavailable."
            ),
            configuration_hash_value="test",
        ),
    )
    eligible = promotion_eligibility(gates).eligible

    snapshot = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": eligible},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert eligible is False
    assert row["candidate_status"] == "REJECTED"
    assert row["exclusion_reason"] == "model_quality_gates_failed"


def test_scanner_applies_persisted_expected_return_threshold(tmp_path: Path) -> None:
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

    snapshot = run_scanner(
        feature_panel,
        bundles=(_bundle(expected_return=0.0005),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(expected_return_threshold=0.0),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert row["exclusion_reason"] == "below_expected_return_threshold"


def test_scanner_applies_persisted_target_before_stop_threshold(tmp_path: Path) -> None:
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

    snapshot = run_scanner(
        feature_panel,
        bundles=(_bundle(target_probability=0.49),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert row["exclusion_reason"] == "below_target_before_stop_threshold"


def test_scanner_threshold_equality_passes_and_runtime_can_only_tighten(
    tmp_path: Path,
) -> None:
    feature_panel = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [2.0],
            "dollar_volume": [5_000_000.0],
            "sector": ["technology"],
            "market_regime_label": ["mixed"],
        }
    )

    equal = run_scanner(
        feature_panel,
        bundles=(_bundle(probability=0.55, target_probability=0.50, expected_return=0.001),),
        db_path=tmp_path / "equal.sqlite3",
        output_dir=tmp_path / "equal",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )
    stricter = run_scanner(
        feature_panel,
        bundles=(_bundle(expected_return=0.02),),
        db_path=tmp_path / "stricter.sqlite3",
        output_dir=tmp_path / "stricter",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(expected_return_threshold=0.03),
    )

    assert equal.rows.iloc[0]["candidate_status"] == "ACTIONABLE_PAPER_CANDIDATE"
    assert stricter.rows.iloc[0]["candidate_status"] == "REJECTED"
    assert stricter.rows.iloc[0]["exclusion_reason"] == "below_expected_return_threshold"


def test_scanner_rejects_missing_persisted_selection_policy(tmp_path: Path) -> None:
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

    snapshot = run_scanner(
        feature_panel,
        bundles=(_bundle(include_policy=False),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    assert snapshot.rows.iloc[0]["candidate_status"] == "REJECTED"
    assert snapshot.rows.iloc[0]["exclusion_reason"] == "persisted_selection_policy_missing"


def test_scanner_rejects_missing_ood_metadata_for_actionable_model(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(_bundle(include_ood=False),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert "prediction_ood_metadata_missing" in row["exclusion_reason"]


def test_scanner_retains_permitted_ood_warning_without_clipping(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(_bundle(expected_return=0.02, return_high=0.01, return_severity_limit=0.20),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(expected_return_threshold=0.001),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "ACTIONABLE_PAPER_CANDIDATE"
    assert bool(row["ood_warning"]) is True
    assert row["ood_affected_heads"] == "return"
    assert row["expected_return"] == pytest.approx(0.02)
    assert row["expected_return_raw"] == pytest.approx(0.02)
    assert row["expected_return_ood_severity"] > 0.0
    assert row["expected_return_ood_severity"] <= row["expected_return_ood_severity_limit"]


def test_scanner_rejects_ood_severity_above_frozen_limit(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(_bundle(expected_return=0.20, return_high=0.01, return_severity_limit=0.10),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert "catastrophic_prediction_extrapolation" in row["exclusion_reason"]


def test_scanner_caps_are_order_independent_for_equal_utility_rows(tmp_path: Path) -> None:
    policy = SelectionPolicy(per_date_limit=2, top_n_limit=None)
    feature_panel = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"] * 3),
            "symbol": ["C", "A", "B"],
            "f1": [2.0, 2.0, 2.0],
            "dollar_volume": [20_000_000.0] * 3,
            "sector": ["technology"] * 3,
            "market_regime_label": ["mixed"] * 3,
        }
    )
    shuffled = feature_panel.sample(frac=1.0, random_state=23).reset_index(drop=True)

    first = run_scanner(
        feature_panel,
        bundles=(_bundle(policy=policy, expected_return=0.02),),
        db_path=tmp_path / "first.sqlite3",
        output_dir=tmp_path / "first",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )
    second = run_scanner(
        shuffled,
        bundles=(_bundle(policy=policy, expected_return=0.02),),
        db_path=tmp_path / "second.sqlite3",
        output_dir=tmp_path / "second",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    first_status = first.rows.set_index("ticker")["candidate_status"].to_dict()
    second_status = second.rows.set_index("ticker")["candidate_status"].to_dict()

    assert first_status == second_status
    assert first_status == {
        "A": "ACTIONABLE_PAPER_CANDIDATE",
        "B": "ACTIONABLE_PAPER_CANDIDATE",
        "C": "REJECTED",
    }


def test_scanner_cache_identity_rejects_stricter_expected_return_run(
    tmp_path: Path,
) -> None:
    feature_panel = _scanner_feature_panel()
    db_path = tmp_path / "engine.sqlite3"
    output_dir = tmp_path / "scanner"

    loose = run_scanner(
        feature_panel,
        bundles=(_bundle(expected_return=0.02),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(expected_return_threshold=0.0),
    )
    old_csv_text = loose.csv_path.read_text(encoding="utf-8")
    strict = run_scanner(
        feature_panel,
        bundles=(_bundle(expected_return=0.02),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(expected_return_threshold=0.03),
    )

    assert loose.scan_id != strict.scan_id
    assert strict.created_at_utc != "existing"
    assert loose.rows.iloc[0]["candidate_status"] == "ACTIONABLE_PAPER_CANDIDATE"
    assert strict.rows.iloc[0]["candidate_status"] == "REJECTED"
    assert strict.rows.iloc[0]["exclusion_reason"] == "below_expected_return_threshold"
    assert loose.csv_path.read_text(encoding="utf-8") == old_csv_text
    with engine_connection(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM scanner_snapshots").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM scanner_candidates").fetchone()[0] == 2


def test_scanner_identity_changes_for_behavior_affecting_config(
    tmp_path: Path,
) -> None:
    feature_panel = _scanner_feature_panel()
    base_kwargs = {
        "feature_panel": feature_panel,
        "bundles": (_bundle(),),
        "db_path": tmp_path / "engine.sqlite3",
        "output_dir": tmp_path / "scanner",
        "universe_snapshot_id": "u",
        "model_states": {"model-a": "CHAMPION"},
        "model_eligibility": {"model-a": True},
    }

    base = run_scanner(**base_kwargs)
    target = run_scanner(
        **base_kwargs,
        config=ScannerConfig(target_before_stop_threshold=0.80),
    )
    probability = run_scanner(
        **base_kwargs,
        config=ScannerConfig(probability_threshold=0.80),
    )
    liquidity = run_scanner(
        **base_kwargs,
        config=ScannerConfig(minimum_dollar_volume=30_000_000.0),
    )
    global_cap = run_scanner(
        **base_kwargs,
        config=ScannerConfig(top_n_per_direction=1),
    )

    assert (
        len(
            {
                base.scan_id,
                target.scan_id,
                probability.scan_id,
                liquidity.scan_id,
                global_cap.scan_id,
            }
        )
        == 5
    )


def test_scanner_identity_changes_for_policy_generation_feature_and_universe(
    tmp_path: Path,
) -> None:
    feature_panel = _scanner_feature_panel(("AAPL", "MSFT"))
    base_kwargs = {
        "feature_panel": feature_panel,
        "db_path": tmp_path / "engine.sqlite3",
        "output_dir": tmp_path / "scanner",
        "model_states": {"model-a": "CHAMPION"},
        "model_eligibility": {"model-a": True},
    }

    base = run_scanner(
        **base_kwargs,
        bundles=(_bundle(policy=SelectionPolicy(per_date_limit=2)),),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    per_date_cap = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                policy=SelectionPolicy(per_date_limit=1),
                policy_hash="policy-hash-cap-1",
            ),
        ),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    policy_hash = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                policy=SelectionPolicy(per_date_limit=2),
                policy_hash="policy-hash-new",
            ),
        ),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    generation = run_scanner(
        **base_kwargs,
        bundles=(_bundle(policy=SelectionPolicy(per_date_limit=2)),),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-b"},
    )
    feature_manifest = run_scanner(
        **base_kwargs,
        bundles=(_bundle(policy=SelectionPolicy(per_date_limit=2)),),
        universe_snapshot_id="u",
        feature_manifest_hash="features-b",
        model_generation_ids={"model-a": "generation-a"},
    )
    universe = run_scanner(
        **base_kwargs,
        bundles=(_bundle(policy=SelectionPolicy(per_date_limit=2)),),
        universe_snapshot_id="u2",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    ood_metadata = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                policy=SelectionPolicy(per_date_limit=2),
                return_severity_limit=0.20,
            ),
        ),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    target_manifest = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                policy=SelectionPolicy(per_date_limit=2),
                target_manifest="target-before-stop-manifest-b",
            ),
        ),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    calibration_manifest = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                policy=SelectionPolicy(per_date_limit=2),
                calibration_manifest_hash="calibration-manifest-b",
            ),
        ),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )

    assert (
        len(
            {
                base.scan_id,
                per_date_cap.scan_id,
                policy_hash.scan_id,
                generation.scan_id,
                feature_manifest.scan_id,
                universe.scan_id,
                ood_metadata.scan_id,
                target_manifest.scan_id,
                calibration_manifest.scan_id,
            }
        )
        == 9
    )


def test_scanner_identity_is_stable_for_model_and_row_order(
    tmp_path: Path,
) -> None:
    feature_panel = _scanner_feature_panel(("C", "A", "B"))
    shuffled_features = feature_panel.sample(frac=1.0, random_state=11).reset_index(drop=True)
    db_path = tmp_path / "engine.sqlite3"
    output_dir = tmp_path / "scanner"

    first = run_scanner(
        feature_panel,
        bundles=(_bundle("model-b"), _bundle("model-a")),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION", "model-b": "CHAMPION"},
        model_eligibility={"model-a": True, "model-b": True},
    )
    second = run_scanner(
        shuffled_features,
        bundles=(_bundle("model-a"), _bundle("model-b")),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION", "model-b": "CHAMPION"},
        model_eligibility={"model-a": True, "model-b": True},
    )

    assert first.scan_id == second.scan_id
    assert second.created_at_utc == "existing"
    first_rows = first.rows.sort_values(["ticker", "model_id"]).reset_index(drop=True).fillna("")
    second_rows = second.rows.sort_values(["ticker", "model_id"]).reset_index(drop=True).fillna("")
    pd.testing.assert_frame_equal(first_rows, second_rows, check_dtype=False)


def test_scanner_exact_same_identity_reuses_cache_without_duplicate_rows(
    tmp_path: Path,
) -> None:
    feature_panel = _scanner_feature_panel()
    db_path = tmp_path / "engine.sqlite3"
    output_dir = tmp_path / "scanner"

    first = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )
    second = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    assert first.scan_id == second.scan_id
    assert second.created_at_utc == "existing"
    with engine_connection(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM scanner_snapshots").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM scanner_candidates").fetchone()[0] == 1


def test_scanner_legacy_or_mismatched_cached_metadata_is_not_reused(
    tmp_path: Path,
) -> None:
    feature_panel = _scanner_feature_panel()
    db_path = tmp_path / "engine.sqlite3"
    output_dir = tmp_path / "scanner"
    baseline = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )
    with engine_connection(db_path) as connection:
        connection.execute(
            "UPDATE scanner_snapshots SET metadata_json = ? WHERE scan_id = ?",
            ("{}", baseline.scan_id),
        )

    rerun = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    assert rerun.scan_id != baseline.scan_id
    assert rerun.created_at_utc != "existing"
    with engine_connection(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM scanner_snapshots").fetchone()[0] == 2

    with engine_connection(db_path) as connection:
        row = connection.execute(
            "SELECT metadata_json FROM scanner_snapshots WHERE scan_id = ?",
            (rerun.scan_id,),
        ).fetchone()
        metadata = json.loads(row["metadata_json"])
        metadata["raw_scanner_config_hash"] = "mismatched"
        connection.execute(
            "UPDATE scanner_snapshots SET metadata_json = ? WHERE scan_id = ?",
            (json.dumps(metadata, sort_keys=True), rerun.scan_id),
        )

    mismatched_config = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    assert mismatched_config.scan_id not in {baseline.scan_id, rerun.scan_id}
    assert mismatched_config.created_at_utc != "existing"

    with engine_connection(db_path) as connection:
        row = connection.execute(
            "SELECT metadata_json FROM scanner_snapshots WHERE scan_id = ?",
            (mismatched_config.scan_id,),
        ).fetchone()
        metadata = json.loads(row["metadata_json"])
        metadata["effective_policy_bundle_hash"] = "mismatched"
        connection.execute(
            "UPDATE scanner_snapshots SET metadata_json = ? WHERE scan_id = ?",
            (json.dumps(metadata, sort_keys=True), mismatched_config.scan_id),
        )

    mismatched_policy = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    assert mismatched_policy.scan_id not in {
        baseline.scan_id,
        rerun.scan_id,
        mismatched_config.scan_id,
    }
    assert mismatched_policy.created_at_utc != "existing"

    with engine_connection(db_path) as connection:
        row = connection.execute(
            "SELECT metadata_json FROM scanner_snapshots WHERE scan_id = ?",
            (mismatched_policy.scan_id,),
        ).fetchone()
        metadata = json.loads(row["metadata_json"])
        metadata["model_ood_governance_metadata_hash"] = "mismatched"
        connection.execute(
            "UPDATE scanner_snapshots SET metadata_json = ? WHERE scan_id = ?",
            (json.dumps(metadata, sort_keys=True), mismatched_policy.scan_id),
        )

    mismatched_ood = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    assert mismatched_ood.scan_id not in {
        baseline.scan_id,
        rerun.scan_id,
        mismatched_config.scan_id,
        mismatched_policy.scan_id,
    }
    assert mismatched_ood.created_at_utc != "existing"


def test_scanner_snapshot_persists_canonical_identity_metadata(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(_bundle(),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
        model_artifact_hashes={"model-a": "artifact-hash-a"},
    )

    with engine_connection(tmp_path / "engine.sqlite3") as connection:
        row = connection.execute(
            "SELECT metadata_json FROM scanner_snapshots WHERE scan_id = ?",
            (snapshot.scan_id,),
        ).fetchone()
    metadata = json.loads(row["metadata_json"])

    assert metadata["final_scan_id"] == snapshot.scan_id
    assert metadata["scanner_identity_schema_version"] == 5
    assert metadata["raw_scanner_config_json"]
    assert metadata["raw_scanner_config_hash"]
    assert metadata["effective_model_policy_json"]
    assert metadata["effective_policy_bundle_hash"]
    assert metadata["model_ood_governance_metadata_json"]
    assert metadata["model_ood_governance_metadata_hash"]
    assert metadata["target_before_stop_feature_metadata_json"]
    assert metadata["target_before_stop_feature_metadata_hash"]
    assert metadata["target_before_stop_calibration_metadata_json"]
    assert metadata["target_before_stop_calibration_metadata_hash"]
    assert metadata["persisted_model_policy_hashes"] == {"model-a": "policy-hash"}
    identity = metadata["canonical_scan_execution_identity"]
    assert identity["prediction_ood_governance_schema_version"] == PREDICTION_OOD_GOVERNANCE_VERSION
    assert identity["feature_manifest_hash"] == "features-a"
    assert identity["model_generation_ids"] == {"model-a": "generation-a"}
    assert identity["model_artifact_hashes"] == {"model-a": "artifact-hash-a"}
    assert identity["model_ood_governance_metadata"]["model-a"]["governance_schema_version"] == (
        PREDICTION_OOD_GOVERNANCE_VERSION
    )
    assert (
        identity["target_before_stop_feature_metadata"]["model-a"][
            "target_before_stop_feature_manifest_hash"
        ]
        == "target-before-stop-manifest"
    )
    assert identity["target_before_stop_calibration_metadata"]["model-a"]["method"] == "identity"
    assert (
        identity["target_before_stop_calibration_metadata"]["model-a"]["calibration_manifest_hash"]
        == "calibration-manifest-a"
    )
    assert identity["effective_selection_policies"]["model-a"]["expected_return_threshold"] == 0.001
    assert identity["raw_scanner_config"]["minimum_dollar_volume"] == 5_000_000.0


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
            {
                "as_of_date": simple_ohlcv.index[30].date().isoformat(),
                "ticker": "AAPL",
                "direction": "Bullish",
                "candidate_status": "REJECTED",
                "exclusion_reason": "model_not_promoted_or_quality_gates_failed",
                "composite_utility_score": 0.1,
                "model_id": "model-b",
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
    assert not result.symbol_returns.empty
    assert "model_not_promoted_or_quality_gates_failed" in set(
        result.candidate_audit["audit_reason"]
    )
