from __future__ import annotations

import inspect
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from swing_rsi.engine.calibration_governance import TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION
from swing_rsi.engine.drift import build_drift_report
from swing_rsi.engine.features import (
    build_feature_panel,
    numeric_feature_columns,
    reject_label_columns,
)
from swing_rsi.engine.forward import (
    advance_forward_positions,
    create_pending_events_from_snapshot,
    list_forward_events,
)
from swing_rsi.engine.gates import (
    FINAL_HOLDOUT_PROMOTION_GATE_ID,
    FINAL_HOLDOUT_STATUS,
    GATE_VALUE_NOT_AVAILABLE,
    configuration_hash,
    make_gate,
    promotion_eligibility,
)
from swing_rsi.engine.labels import LabelConfig, build_label_panel, build_symbol_labels
from swing_rsi.engine.manifest import hash_file
from swing_rsi.engine.models import (
    EXPECTED_RETURN_HEAD,
    LINEAR_PATH_HEAD_RETIREMENT_REASON,
    MAE_HEAD,
    MFE_HEAD,
    PATH_HEAD_CAPABILITY_ACTIVE,
    PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR,
    PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION,
    PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION,
    PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
    PATH_TARGET_ATR_FEATURE,
    PATH_TARGET_NORMALIZATION_SCHEMA_VERSION,
    PATH_TARGET_PREDICTION_MAPPING_VERSION,
    TARGET_BEFORE_STOP_HEAD,
    BaseRateClassifier,
    DiscoveryConfig,
    ModelBundle,
    RetiredPathHeadModel,
    _path_atr_training_target,
    _path_magnitude_prediction,
    _path_target_prediction,
    build_path_magnitude_estimator,
    discover_models,
    load_model_bundle,
    model_plugins,
    predict_bundle,
)
from swing_rsi.engine.ood import PREDICTION_OOD_GOVERNANCE_VERSION
from swing_rsi.engine.portfolio import PortfolioBacktestConfig, backtest_scanner_candidates
from swing_rsi.engine.product_scope import (
    PRODUCT_CLASS_SCHEMA_VERSION,
    PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE,
    PRODUCT_CLASS_SCOPE_MISMATCH_REASON,
    PRODUCT_CLASS_SCOPE_ORDINARY,
    PRODUCT_CLASS_SCOPE_POOLED,
    PRODUCT_CLASS_SCOPES,
    build_product_class_scope_definition,
    build_product_class_scope_definitions,
    canonical_role_scope_mapping,
    filter_frame_for_product_class_scope,
    product_class_scope_for_role,
)
from swing_rsi.engine.registry import (
    FINAL_HOLDOUT_SAMPLE_GATE_IDS,
    RegisteredModel,
    promote_model,
    register_model,
)
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


class FeatureEchoRegressor:
    def __init__(self, feature: str) -> None:
        self.feature = feature

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return frame[self.feature].to_numpy(dtype=float)


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


def _product_scope_universe() -> UniverseConfig:
    return UniverseConfig(
        name="product-scope-test",
        provider="fmp",
        default_start="2018-01-02",
        symbols=(
            UniverseSymbol("ABC", role="stock", sector="technology", sector_proxy="XLK"),
            UniverseSymbol("SPY", role="broad_market_etf", sector="broad_market", benchmark=True),
            UniverseSymbol("XLK", role="sector_etf", sector="technology"),
            UniverseSymbol("SH", role="inverse_etf", sector="inverse_market"),
            UniverseSymbol("TQQQ", role="leveraged_long_etf", sector="leveraged_growth"),
            UniverseSymbol("ZZZ", role="leveraged_inverse_etf", sector="inverse_growth"),
        ),
        relationships={"SPY": ("SH", "TQQQ", "ZZZ")},
    )


def test_product_class_roles_map_deterministically_from_metadata() -> None:
    universe = _product_scope_universe()
    definitions = build_product_class_scope_definitions(universe, scopes=PRODUCT_CLASS_SCOPES)

    assert product_class_scope_for_role("stock") == PRODUCT_CLASS_SCOPE_ORDINARY
    assert product_class_scope_for_role("broad_market_etf") == PRODUCT_CLASS_SCOPE_ORDINARY
    assert product_class_scope_for_role("sector_etf") == PRODUCT_CLASS_SCOPE_ORDINARY
    assert product_class_scope_for_role("inverse_etf") == PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE
    assert product_class_scope_for_role("leveraged_long_etf") == (
        PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE
    )
    assert product_class_scope_for_role("leveraged_inverse_etf") == (
        PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE
    )
    assert definitions[PRODUCT_CLASS_SCOPE_POOLED].eligible_symbols == (
        "ABC",
        "SH",
        "SPY",
        "TQQQ",
        "XLK",
        "ZZZ",
    )
    assert definitions[PRODUCT_CLASS_SCOPE_ORDINARY].eligible_symbols == ("ABC", "SPY", "XLK")
    assert definitions[PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE].eligible_symbols == (
        "SH",
        "TQQQ",
        "ZZZ",
    )
    assert definitions[PRODUCT_CLASS_SCOPE_ORDINARY].role_scope_mapping_hash == (
        definitions[PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE].role_scope_mapping_hash
    )


def test_product_class_unknown_roles_are_rejected() -> None:
    universe = UniverseConfig(
        name="bad-role",
        provider="fmp",
        default_start="2018-01-02",
        symbols=(UniverseSymbol("AAPL", role="mystery_etf"),),
        relationships={},
    )

    with pytest.raises(ValueError, match="Unknown product-class universe role"):
        build_product_class_scope_definition(universe, PRODUCT_CLASS_SCOPE_ORDINARY)


def test_product_class_scope_is_not_ticker_name_heuristic() -> None:
    universe = UniverseConfig(
        name="ticker-agnostic",
        provider="fmp",
        default_start="2018-01-02",
        symbols=(
            UniverseSymbol("SOXL", role="stock", sector="technology"),
            UniverseSymbol("ABC", role="leveraged_inverse_etf", sector="inverse_market"),
        ),
        relationships={},
    )
    definitions = build_product_class_scope_definitions(universe, scopes=PRODUCT_CLASS_SCOPES)

    assert definitions[PRODUCT_CLASS_SCOPE_ORDINARY].eligible_symbols == ("SOXL",)
    assert definitions[PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE].eligible_symbols == ("ABC",)


def _scope_modeling_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    symbols = (
        ("ABC", "stock"),
        ("SPY", "broad_market_etf"),
        ("SH", "inverse_etf"),
        ("TQQQ", "leveraged_long_etf"),
    )
    dates = pd.bdate_range("2020-01-02", periods=80)
    for position, date_value in enumerate(dates):
        for symbol, role in symbols:
            rows.append(
                {
                    "Date": date_value,
                    "symbol": symbol,
                    "role": role,
                    "sector": "test",
                    "sector_proxy": "",
                    "market_regime_label": "mixed",
                    "Open": 100.0,
                    "High": 101.0,
                    "Low": 99.0,
                    "Close": 100.0,
                    "Volume": 1_000_000.0,
                    "dollar_volume": 20_000_000.0,
                    "market_context_signal": float(position),
                    "relationship_context_signal": float(position % 5),
                    PATH_TARGET_ATR_FEATURE: 1.0,
                    "label_bull_positive_return_10": float(position % 2),
                    "label_bull_forward_return_10": 0.01 if position % 2 else -0.01,
                    "label_bull_mfe_10": 0.02 + (0.001 * (position % 7)),
                    "label_bull_mae_10": -0.01 - (0.001 * (position % 5)),
                    "label_bull_target_before_stop_10": float(position % 3 == 0),
                    "label_end_date_10": date_value + pd.offsets.BDay(10),
                }
            )
    return pd.DataFrame(rows)


def test_product_class_row_filter_preserves_full_universe_context_columns() -> None:
    universe = _product_scope_universe()
    frame = _scope_modeling_frame()
    ordinary = build_product_class_scope_definition(universe, PRODUCT_CLASS_SCOPE_ORDINARY)
    leveraged = build_product_class_scope_definition(
        universe, PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE
    )

    ordinary_rows = filter_frame_for_product_class_scope(frame, ordinary)
    leveraged_rows = filter_frame_for_product_class_scope(frame, leveraged)

    assert set(ordinary_rows["role"]) == {"stock", "broad_market_etf"}
    assert set(leveraged_rows["role"]) == {"inverse_etf", "leveraged_long_etf"}
    assert "market_context_signal" in ordinary_rows.columns
    assert "relationship_context_signal" in leveraged_rows.columns
    assert "product_class_scope" not in numeric_feature_columns(ordinary_rows)
    assert "label_bull_forward_return_10" not in numeric_feature_columns(ordinary_rows)


def test_product_class_splits_remain_chronological_and_purged_within_scope() -> None:
    universe = _product_scope_universe()
    frame = _scope_modeling_frame()
    ordinary = filter_frame_for_product_class_scope(
        frame,
        build_product_class_scope_definition(universe, PRODUCT_CLASS_SCOPE_ORDINARY),
    )

    split = chronological_train_calibration_holdout_split(ordinary, horizon=10)

    assert pd.Timestamp(split.train["Date"].max()) < pd.Timestamp(split.calibration["Date"].min())
    assert pd.Timestamp(split.calibration["Date"].max()) < pd.Timestamp(split.holdout["Date"].min())
    assert pd.to_datetime(split.train["label_end_date_10"]).max() < pd.Timestamp(
        split.calibration_start
    )
    assert pd.to_datetime(split.calibration["label_end_date_10"]).max() < pd.Timestamp(
        split.holdout_start
    )
    assert set(split.train["role"]) == {"stock", "broad_market_etf"}


def test_discovery_persists_independent_product_class_specialist_artifacts(
    tmp_path: Path,
) -> None:
    frame = _scope_modeling_frame()
    family_map = {
        column: "market_relative"
        for column in frame.columns
        if not str(column).startswith("label_")
    }
    family_map["relationship_context_signal"] = "relationship_graph"
    family_map["market_context_signal"] = "market_relative"

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
            max_features=8,
            mutual_information_top_k=4,
            research_start=None,
            random_seed=7,
            product_class_scopes=(
                PRODUCT_CLASS_SCOPE_ORDINARY,
                PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE,
            ),
            model_families=("extra_trees",),
            include_naive_controls=False,
        ),
        code_root=tmp_path,
        universe=_product_scope_universe(),
    )

    assert len(result.registered_models) == 2
    by_scope = {model.metrics["product_class_scope"]: model for model in result.registered_models}
    ordinary = by_scope[PRODUCT_CLASS_SCOPE_ORDINARY]
    leveraged = by_scope[PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE]
    ordinary_bundle = load_model_bundle(ordinary.artifact_path)
    leveraged_bundle = load_model_bundle(leveraged.artifact_path)

    assert ordinary.model_id != leveraged.model_id
    assert ordinary.artifact_path != leveraged.artifact_path
    assert ordinary.metrics["product_class_schema_version"] == PRODUCT_CLASS_SCHEMA_VERSION
    assert ordinary_bundle.product_class_scope == PRODUCT_CLASS_SCOPE_ORDINARY
    assert leveraged_bundle.product_class_scope == PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE
    assert set(ordinary_bundle.training_labels["symbol"]) <= {"ABC", "SPY"}
    assert set(leveraged_bundle.training_labels["symbol"]) <= {"SH", "TQQQ"}
    assert ordinary_bundle.product_class_universe_scope_hash != (
        leveraged_bundle.product_class_universe_scope_hash
    )
    assert ordinary_bundle.classifier is not leveraged_bundle.classifier
    assert "product_class_scope" not in ordinary_bundle.feature_columns
    assert ordinary.metrics["product_class_development_evidence_label"] == (
        "DEVELOPMENT_HOLDOUT_DIAGNOSTIC"
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
    final_holdout_gate = make_gate(
        gate_id=FINAL_HOLDOUT_PROMOTION_GATE_ID,
        gate_name="Final Holdout Required For Promotion",
        category="research integrity",
        scope="model",
        metric_name="holdout_status",
        threshold=FINAL_HOLDOUT_STATUS,
        comparator="equals",
        actual_value=FINAL_HOLDOUT_STATUS,
        status="PASS",
        mandatory=True,
        evidence_source="test",
        reason="Synthetic registry fixture uses a final holdout.",
        configuration_hash_value="test",
    )
    sample_gates = tuple(
        make_gate(
            gate_id=gate_id,
            gate_name=gate_id.replace("_", " ").title(),
            category="final holdout sample governance",
            scope="model",
            metric_name=gate_id,
            threshold=True,
            comparator="is true",
            actual_value=True,
            status="PASS",
            mandatory=True,
            evidence_source="synthetic-test",
            reason="Synthetic final-holdout sample gate passed.",
            configuration_hash_value="synthetic-sample-policy",
        )
        for gate_id in FINAL_HOLDOUT_SAMPLE_GATE_IDS
    )
    gates = (final_holdout_gate, *sample_gates)
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
        metrics={
            "holdout_mean_return_lcb_90": 0.01,
            "holdout_status": FINAL_HOLDOUT_STATUS,
            "expected_return_feature_screen_schema_version": (
                PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION
            ),
            "expected_return_screening_manifest_hash": "return-manifest",
            "mfe_feature_screen_schema_version": PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
            "mfe_screening_manifest_hash": "mfe-manifest",
            "mae_feature_screen_schema_version": PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
            "mae_screening_manifest_hash": "mae-manifest",
            **_path_domain_metrics(),
        },
        calibration_metrics={"holdout_brier": 0.2},
        quality_gates={gate.gate_id: gate.status == "PASS" for gate in gates},
        gate_results=gates,
        artifact_path="artifact.joblib",
        code_commit_hash=None,
        created_at_utc=datetime.now(UTC).isoformat(),
    )


def test_model_registry_is_immutable_and_promotion_is_explicit(tmp_path: Path) -> None:
    db = tmp_path / "engine.sqlite3"
    artifact = tmp_path / "artifact.joblib"
    artifact.write_text("synthetic frozen artifact", encoding="utf-8")
    run_id = "synthetic-final-holdout-run"
    model = _registered_model("model-a")
    model = replace(
        model,
        artifact_path=str(artifact),
        metrics={
            **model.metrics,
            "final_holdout_run_id": run_id,
            "final_holdout_evidence_manifest_hash": "synthetic-evidence",
        },
    )

    register_model(db, model)
    with engine_connection(db) as connection:
        connection.execute(
            """
            INSERT INTO final_holdout_runs (
                run_id, schema_version, created_at_utc, creation_git_commit,
                baseline_market_date, first_eligible_future_signal_date, universe_snapshot_id,
                feature_manifest_hash, generation_id, model_ids_json, scanner_identity_version,
                execution_policy_hash, sample_policy_version, sample_policy_hash,
                sample_policy_json, horizon, direction, status, invalidation_reason,
                latest_processed_market_date, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "prospective_final_holdout_v1",
                model.created_at_utc,
                None,
                "2026-06-18",
                "2026-06-19",
                model.universe_snapshot_id,
                model.feature_manifest_hash,
                model.created_at_utc,
                json.dumps([model.model_id]),
                1,
                "synthetic-execution-policy",
                "prospective_final_holdout_sample_v1",
                "synthetic-sample-policy",
                json.dumps({"schema_version": "prospective_final_holdout_sample_v1"}),
                model.horizon,
                model.direction,
                "EVALUATED_PASS",
                None,
                "2026-12-18",
                "{}",
            ),
        )
        connection.execute(
            """
            INSERT INTO final_holdout_models (
                run_id, model_id, generation_id, artifact_path, artifact_hash,
                model_state_at_enrollment, development_gate_eligible, research_only,
                selection_policy_hash, calibration_governance_hash, ood_governance_hash,
                enrollment_blockers_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                model.model_id,
                model.created_at_utc,
                model.artifact_path,
                hash_file(model.artifact_path),
                model.state,
                1,
                0,
                "",
                "",
                configuration_hash({}),
                "[]",
                json.dumps(
                    {
                        "feature_manifest_hash": model.feature_manifest_hash,
                        "calibrator_artifact_hash": "",
                        "execution_policy_hash": "synthetic-execution-policy",
                    }
                ),
            ),
        )
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
            return_target = float(np.sin((position + symbol_offset) / 6.0) * 0.03)
            mfe_target = float(0.04 + np.cos((position + symbol_offset) / 5.0) * 0.02)
            mae_target = float(-0.03 + np.sin((position + symbol_offset) / 7.0) * 0.015)
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
                PATH_TARGET_ATR_FEATURE: 1.0,
                "primary_signal": float(positive_target),
                "late_market_relative_signal": float(tbs_target),
                "late_return_signal": return_target,
                "late_mfe_signal": mfe_target,
                "late_mae_signal": mae_target,
                "label_bull_positive_return_10": float(positive_target),
                "label_bull_forward_return_10": return_target,
                "label_bull_mfe_10": mfe_target,
                "label_bull_mae_10": mae_target,
                "label_bull_target_before_stop_10": float(tbs_target),
                "label_end_date_10": date_value + pd.offsets.BDay(10),
            }
            for index in range(70):
                row[f"noise_{index:02d}"] = float(np.sin(position + index))
            rows.append(row)
    frame = pd.DataFrame(rows)
    family_map = {column: "returns_momentum" for column in frame.columns}
    family_map["late_market_relative_signal"] = "market_relative"
    family_map["late_return_signal"] = "returns_momentum"
    family_map["late_mfe_signal"] = "volatility_range"
    family_map["late_mae_signal"] = "inverse_leveraged"
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
    assert learned.metrics["expected_return_screening_target"] == (
        "label_bull_forward_return_10__atr_units_atr_pct_14"
    )
    assert learned.metrics["mfe_screening_target"] == (
        "label_bull_mfe_10__favorable_magnitude_atr_units_atr_pct_14"
    )
    assert (
        learned.metrics["mae_screening_target"]
        == "label_bull_mae_10__adverse_magnitude_atr_units_atr_pct_14"
    )
    assert learned.metrics["expected_return_target_normalization_schema_version"] == (
        PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
    )
    assert learned.metrics["mfe_target_normalization_schema_version"] == (
        PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
    )
    assert learned.metrics["mae_target_normalization_schema_version"] == (
        PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
    )
    assert learned.metrics["mfe_external_target_name"] == "label_bull_mfe_10"
    assert learned.metrics["mae_external_target_name"] == "label_bull_mae_10"
    assert learned.metrics["mfe_domain_schema_version"] == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
    assert learned.metrics["mae_domain_schema_version"] == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
    assert learned.metrics["mfe_path_head_capability_state"] == (
        PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
    )
    assert learned.metrics["mae_path_head_capability_state"] == (
        PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
    )
    assert learned.metrics["mfe_path_head_retirement_reason"] == (
        LINEAR_PATH_HEAD_RETIREMENT_REASON
    )
    assert learned.metrics["mae_path_head_retirement_reason"] == (
        LINEAR_PATH_HEAD_RETIREMENT_REASON
    )
    assert learned.metrics["mfe_magnitude_estimator_class"] == "RetiredPathHeadModel"
    assert learned.metrics["mae_magnitude_estimator_class"] == "RetiredPathHeadModel"
    assert "TweedieRegressor" not in str(learned.metrics["mfe_magnitude_domain_metadata_json"])
    assert "TweedieRegressor" not in str(learned.metrics["mae_magnitude_domain_metadata_json"])
    assert isinstance(bundle.mfe_model, RetiredPathHeadModel)
    assert isinstance(bundle.mae_model, RetiredPathHeadModel)
    assert learned.metrics["mfe_holdout_signed_domain_violation_count"] == 0
    assert learned.metrics["mae_holdout_signed_domain_violation_count"] == 0
    gate_by_id = {gate.gate_id: gate for gate in learned.gate_results}
    assert gate_by_id["mfe_required_path_head_active"].status == "FAIL"
    assert gate_by_id["mae_required_path_head_active"].status == "FAIL"
    assert promotion_eligibility(learned.gate_results).eligible is False
    assert learned.metrics["expected_return_feature_screen_schema_version"] == (
        PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION
    )
    assert bundle.head_feature_columns["expected_return"]
    assert bundle.head_feature_columns["mfe"]
    assert bundle.head_feature_columns["mae"]
    assert "late_return_signal" in bundle.head_feature_columns["expected_return"]
    assert "late_mfe_signal" in bundle.head_feature_columns["mfe"]
    assert "late_mae_signal" in bundle.head_feature_columns["mae"]
    assert (
        learned.metrics["expected_return_screening_manifest_hash"]
        == bundle.head_feature_manifests["expected_return"]
    )
    nonlinear = next(model for model in result.registered_models if model.family == "extra_trees")
    nonlinear_bundle = load_model_bundle(nonlinear.artifact_path)
    assert nonlinear.metrics["mfe_path_head_capability_state"] == PATH_HEAD_CAPABILITY_ACTIVE
    assert nonlinear.metrics["mae_path_head_capability_state"] == PATH_HEAD_CAPABILITY_ACTIVE
    assert not isinstance(nonlinear_bundle.mfe_model, RetiredPathHeadModel)
    assert not isinstance(nonlinear_bundle.mae_model, RetiredPathHeadModel)


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
        "mae": (0.0, 0.20, 0.10),
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


def _target_normalization_payload(
    *,
    head: str,
    external_target: str,
    internal_target: str,
) -> dict[str, object]:
    return {
        "target_normalization_schema_version": PATH_TARGET_NORMALIZATION_SCHEMA_VERSION,
        "head_name": head,
        "target_normalization_method": "divide_by_signal_close_atr_pct_14",
        "atr_feature_name": PATH_TARGET_ATR_FEATURE,
        "atr_feature_timing": "signal_date_close_known",
        "external_target_name": external_target,
        "internal_target_name": internal_target,
        "internal_target_unit": "atr_units",
        "canonical_external_unit": "decimal_return",
        "prediction_mapping_version": PATH_TARGET_PREDICTION_MAPPING_VERSION,
        "target_normalization_hash": configuration_hash(
            {
                "schema_version": PATH_TARGET_NORMALIZATION_SCHEMA_VERSION,
                "head_name": head,
                "external_target_name": external_target,
                "internal_target_name": internal_target,
                "atr_feature_name": PATH_TARGET_ATR_FEATURE,
                "direction": "bull",
                "horizon": 10,
                "prediction_mapping_version": PATH_TARGET_PREDICTION_MAPPING_VERSION,
            }
        ),
    }


def _path_target_normalization_payloads() -> dict[str, dict[str, object]]:
    return {
        EXPECTED_RETURN_HEAD: _target_normalization_payload(
            head=EXPECTED_RETURN_HEAD,
            external_target="label_bull_forward_return_10",
            internal_target="label_bull_forward_return_10__atr_units_atr_pct_14",
        ),
        MFE_HEAD: _target_normalization_payload(
            head=MFE_HEAD,
            external_target="label_bull_mfe_10",
            internal_target="label_bull_mfe_10__favorable_magnitude_atr_units_atr_pct_14",
        ),
        MAE_HEAD: _target_normalization_payload(
            head=MAE_HEAD,
            external_target="label_bull_mae_10",
            internal_target="label_bull_mae_10__adverse_magnitude_atr_units_atr_pct_14",
        ),
    }


def _path_target_normalization_metrics() -> dict[str, object]:
    payloads = _path_target_normalization_payloads()
    metrics: dict[str, object] = {}
    for head, metric_prefix in (
        (EXPECTED_RETURN_HEAD, "expected_return"),
        (MFE_HEAD, "mfe"),
        (MAE_HEAD, "mae"),
    ):
        metadata = payloads[head]
        metrics.update(
            {
                f"{metric_prefix}_target_normalization_schema_version": metadata[
                    "target_normalization_schema_version"
                ],
                f"{metric_prefix}_target_normalization_method": metadata[
                    "target_normalization_method"
                ],
                f"{metric_prefix}_target_normalization_atr_feature_name": metadata[
                    "atr_feature_name"
                ],
                f"{metric_prefix}_target_normalization_hash": metadata["target_normalization_hash"],
                f"{metric_prefix}_internal_target_name": metadata["internal_target_name"],
                f"{metric_prefix}_internal_target_unit": metadata["internal_target_unit"],
                f"{metric_prefix}_canonical_external_unit": metadata["canonical_external_unit"],
                f"{metric_prefix}_target_prediction_mapping_version": metadata[
                    "prediction_mapping_version"
                ],
            }
        )
    return metrics


def _path_domain_metrics() -> dict[str, object]:
    payload: dict[str, object] = {}
    target_normalization_payloads = _path_target_normalization_payloads()
    for head, external_target, internal_target, definition in (
        (
            "mfe",
            "label_bull_mfe_10",
            "label_bull_mfe_10__favorable_magnitude_atr_units_atr_pct_14",
            "favorable_magnitude_equals_existing_mfe_divided_by_signal_close_atr_pct_14",
        ),
        (
            "mae",
            "label_bull_mae_10",
            "label_bull_mae_10__adverse_magnitude_atr_units_atr_pct_14",
            "adverse_magnitude_equals_negative_existing_mae_divided_by_signal_close_atr_pct_14",
        ),
    ):
        normalization = target_normalization_payloads[head]
        payload.update(
            {
                f"{head}_domain_schema_version": PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION,
                f"{head}_path_head_capability_state": PATH_HEAD_CAPABILITY_ACTIVE,
                f"{head}_path_head_retirement_schema_version": "",
                f"{head}_path_head_retirement_reason": "",
                f"{head}_external_target_name": external_target,
                f"{head}_internal_magnitude_target_name": internal_target,
                f"{head}_internal_target_definition": definition,
                f"{head}_magnitude_estimator_class": "ConstantRegressor",
                f"{head}_magnitude_estimator_loss": "test_constant_magnitude",
                f"{head}_magnitude_estimator_hash": f"{head}-estimator-hash",
                f"{head}_prediction_mapping_version": (PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION),
                f"{head}_target_normalization_schema_version": (
                    normalization["target_normalization_schema_version"]
                ),
                f"{head}_target_normalization_method": normalization["target_normalization_method"],
                f"{head}_target_normalization_atr_feature_name": normalization["atr_feature_name"],
                f"{head}_target_normalization_hash": normalization["target_normalization_hash"],
                f"{head}_internal_target_unit": normalization["internal_target_unit"],
                f"{head}_canonical_external_unit": normalization["canonical_external_unit"],
                f"{head}_calibration_domain_integrity_valid": True,
                f"{head}_holdout_domain_integrity_valid": True,
            }
        )
    return payload


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
        **_path_domain_metrics(),
        **_path_target_normalization_metrics(),
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
    expected_return_feature_columns: tuple[str, ...] | None = None,
    mfe_feature_columns: tuple[str, ...] | None = None,
    mae_feature_columns: tuple[str, ...] | None = None,
    target_classifier: object | None = None,
    target_calibrator: object | None = None,
    return_model: object | None = None,
    mfe_model: object | None = None,
    mae_model: object | None = None,
    target_manifest: str = "target-before-stop-manifest",
    return_manifest: str = "return-manifest",
    mfe_manifest: str = "mfe-manifest",
    mae_manifest: str = "mae-manifest",
    include_tbs_calibration: bool = True,
    calibration_method: str = "identity",
    calibration_manifest_hash: str = "calibration-manifest-a",
    calibrator_artifact_hash: str = "calibrator-artifact-a",
    include_feature_screen_metadata: bool = True,
    include_path_domain_metadata: bool = True,
    product_class_scope: str = PRODUCT_CLASS_SCOPE_POOLED,
    product_class_scope_hash: str = "scope-hash-pooled",
    product_class_universe_scope_hash: str = "universe-scope-hash-pooled",
    product_class_role_mapping_hash: str = "role-mapping-hash",
) -> ModelBundle:
    target_feature_columns = target_feature_columns or ("f1", "dollar_volume")
    expected_return_feature_columns = expected_return_feature_columns or ("f1", "dollar_volume")
    mfe_feature_columns = mfe_feature_columns or ("f1", "dollar_volume")
    mae_feature_columns = mae_feature_columns or ("f1", "dollar_volume")
    target_normalization_payloads = _path_target_normalization_payloads()
    if product_class_scope == PRODUCT_CLASS_SCOPE_ORDINARY:
        product_roles = ("broad_market_etf", "ordinary_etf", "sector_etf", "stock")
        product_symbols = ("AAPL", "MSFT")
    elif product_class_scope == PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE:
        product_roles = ("inverse_etf", "leveraged_inverse_etf", "leveraged_long_etf")
        product_symbols = ("SH", "SQQQ", "TQQQ")
    else:
        product_roles = tuple(sorted(canonical_role_scope_mapping()))
        product_symbols = ("AAPL", "MSFT", "SH", "SQQQ", "TQQQ")
    product_scope_metrics = {
        "product_class_schema_version": PRODUCT_CLASS_SCHEMA_VERSION,
        "product_class_scope": product_class_scope,
        "product_class_scope_configuration_hash": product_class_scope_hash,
        "product_class_universe_scope_hash": product_class_universe_scope_hash,
        "product_class_role_scope_mapping_hash": product_class_role_mapping_hash,
        "product_class_eligible_roles_json": json.dumps(list(product_roles), sort_keys=True),
        "product_class_eligible_symbols_json": json.dumps(list(product_symbols), sort_keys=True),
        "product_class_eligible_symbol_count": len(product_symbols),
        "product_class_development_evidence_label": "DEVELOPMENT_HOLDOUT_DIAGNOSTIC",
    }
    training = pd.DataFrame(
        {
            "f1": [0.0, 1.0, 2.0],
            "target_signal": [0.25, 0.75, 0.90],
            "return_signal": [0.01, 0.02, 0.03],
            "mfe_signal": [0.03, 0.04, 0.05],
            "mae_signal": [0.01, 0.02, 0.03],
            PATH_TARGET_ATR_FEATURE: [1.0, 1.0, 1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0, 1.0, 1.0],
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
            PATH_TARGET_ATR_FEATURE: "volatility_range",
        },
        classifier=ConstantClassifier(probability),
        calibrator=IdentityCalibrator(),
        target_before_stop_model=target_classifier or ConstantClassifier(target_probability),
        target_before_stop_calibrator=target_calibrator or IdentityCalibrator(),
        return_model=return_model or ConstantRegressor(expected_return),
        mfe_model=mfe_model or ConstantRegressor(0.04),
        mae_model=mae_model or ConstantRegressor(0.015),
        training_medians={"f1": 1.0, "dollar_volume": 10_000_000.0, PATH_TARGET_ATR_FEATURE: 1.0},
        training_means={"f1": 1.0, "dollar_volume": 10_000_000.0, PATH_TARGET_ATR_FEATURE: 1.0},
        training_stds={"f1": 1.0, "dollar_volume": 1.0, PATH_TARGET_ATR_FEATURE: 1.0},
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
            | product_scope_metrics
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
                **_path_domain_metrics(),
                **_path_target_normalization_metrics(),
                **product_scope_metrics,
            }
        ),
        calibration_metrics={},
        head_feature_columns={
            "primary_positive_return": ("f1", "dollar_volume"),
            TARGET_BEFORE_STOP_HEAD: target_feature_columns,
            "expected_return": expected_return_feature_columns,
            "mfe": mfe_feature_columns,
            "mae": mae_feature_columns,
        },
        head_feature_manifests={
            "primary_positive_return": "primary-manifest",
            TARGET_BEFORE_STOP_HEAD: target_manifest,
            "expected_return": return_manifest,
            "mfe": mfe_manifest,
            "mae": mae_manifest,
        },
        feature_screen_metadata=(
            {
                TARGET_BEFORE_STOP_HEAD: {
                    "screening_schema_version": "target_specific_feature_screen_v1",
                    "selected_feature_count": len(target_feature_columns),
                    "selected_feature_families": {"test": len(target_feature_columns)},
                    "selected_feature_manifest_hash": target_manifest,
                },
                EXPECTED_RETURN_HEAD: {
                    "screening_schema_version": PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
                    "selected_feature_count": len(expected_return_feature_columns),
                    "selected_feature_families": {"test": len(expected_return_feature_columns)},
                    "selected_feature_manifest_hash": return_manifest,
                    **target_normalization_payloads[EXPECTED_RETURN_HEAD],
                },
                MFE_HEAD: {
                    "screening_schema_version": PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
                    "selected_feature_count": len(mfe_feature_columns),
                    "selected_feature_families": {"test": len(mfe_feature_columns)},
                    "selected_feature_manifest_hash": mfe_manifest,
                    **target_normalization_payloads[MFE_HEAD],
                },
                MAE_HEAD: {
                    "screening_schema_version": PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
                    "selected_feature_count": len(mae_feature_columns),
                    "selected_feature_families": {"test": len(mae_feature_columns)},
                    "selected_feature_manifest_hash": mae_manifest,
                    **target_normalization_payloads[MAE_HEAD],
                },
            }
            if include_feature_screen_metadata
            else {}
        ),
        path_domain_metadata=(
            {
                MFE_HEAD: {
                    "domain_schema_version": PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION,
                    "path_head_capability_state": PATH_HEAD_CAPABILITY_ACTIVE,
                    "path_head_retirement_schema_version": "",
                    "path_head_retirement_reason": "",
                    "head_name": MFE_HEAD,
                    "external_target_name": "label_bull_mfe_10",
                    "internal_magnitude_target_name": (
                        "label_bull_mfe_10__favorable_magnitude_atr_units_atr_pct_14"
                    ),
                    "internal_target_definition": (
                        "favorable_magnitude_equals_existing_mfe_divided_by_signal_close_atr_pct_14"
                    ),
                    "estimator_class": type(mfe_model or ConstantRegressor(0.04)).__name__,
                    "estimator_loss": "test_constant_magnitude",
                    "estimator_hash": "mfe-estimator-hash",
                    "selected_feature_manifest_hash": mfe_manifest,
                    "prediction_mapping_version": (PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION),
                    "target_normalization": target_normalization_payloads[MFE_HEAD],
                    "target_normalization_schema_version": (
                        PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
                    ),
                    "target_normalization_method": "divide_by_signal_close_atr_pct_14",
                    "atr_feature_name": PATH_TARGET_ATR_FEATURE,
                    "target_normalization_hash": target_normalization_payloads[MFE_HEAD][
                        "target_normalization_hash"
                    ],
                    "internal_target_unit": "atr_units",
                    "canonical_external_unit": "decimal_return",
                },
                MAE_HEAD: {
                    "domain_schema_version": PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION,
                    "path_head_capability_state": PATH_HEAD_CAPABILITY_ACTIVE,
                    "path_head_retirement_schema_version": "",
                    "path_head_retirement_reason": "",
                    "head_name": MAE_HEAD,
                    "external_target_name": "label_bull_mae_10",
                    "internal_magnitude_target_name": (
                        "label_bull_mae_10__adverse_magnitude_atr_units_atr_pct_14"
                    ),
                    "internal_target_definition": (
                        "adverse_magnitude_equals_negative_existing_mae_divided_by_"
                        "signal_close_atr_pct_14"
                    ),
                    "estimator_class": type(mae_model or ConstantRegressor(0.015)).__name__,
                    "estimator_loss": "test_constant_magnitude",
                    "estimator_hash": "mae-estimator-hash",
                    "selected_feature_manifest_hash": mae_manifest,
                    "prediction_mapping_version": (PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION),
                    "target_normalization": target_normalization_payloads[MAE_HEAD],
                    "target_normalization_schema_version": (
                        PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
                    ),
                    "target_normalization_method": "divide_by_signal_close_atr_pct_14",
                    "atr_feature_name": PATH_TARGET_ATR_FEATURE,
                    "target_normalization_hash": target_normalization_payloads[MAE_HEAD][
                        "target_normalization_hash"
                    ],
                    "internal_target_unit": "atr_units",
                    "canonical_external_unit": "decimal_return",
                },
            }
            if include_path_domain_metadata
            else {}
        ),
        product_class_schema_version=PRODUCT_CLASS_SCHEMA_VERSION,
        product_class_scope=product_class_scope,
        product_class_eligible_roles=product_roles,
        product_class_eligible_symbols=product_symbols,
        product_class_role_scope_mapping={
            key: str(value) for key, value in canonical_role_scope_mapping().items()
        },
        product_class_role_scope_mapping_hash=product_class_role_mapping_hash,
        product_class_scope_configuration_hash=product_class_scope_hash,
        product_class_universe_scope_hash=product_class_universe_scope_hash,
        product_class_scope_metadata={
            "schema_version": PRODUCT_CLASS_SCHEMA_VERSION,
            "scope": product_class_scope,
            "eligible_roles": list(product_roles),
            "eligible_symbols": list(product_symbols),
        },
    )


def _scanner_feature_panel(symbols: tuple[str, ...] = ("AAPL",)) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"] * len(symbols)),
            "symbol": list(symbols),
            "f1": [2.0] * len(symbols),
            "target_signal": [0.75] * len(symbols),
            "return_signal": [0.021] * len(symbols),
            "mfe_signal": [0.052] * len(symbols),
            "mae_signal": [0.018] * len(symbols),
            PATH_TARGET_ATR_FEATURE: [1.0] * len(symbols),
            "dollar_volume": [20_000_000.0] * len(symbols),
            "sector": ["technology"] * len(symbols),
            "market_regime_label": ["mixed"] * len(symbols),
        }
    )


def _product_scope_scanner_panel() -> pd.DataFrame:
    frame = _scanner_feature_panel(("ABC", "SH"))
    frame["role"] = ["stock", "inverse_etf"]
    frame["sector"] = ["technology", "inverse_market"]
    return frame


def test_scanner_routes_specialists_only_to_matching_product_scope(tmp_path: Path) -> None:
    universe = _product_scope_universe()
    ordinary = _bundle(
        "ordinary-model",
        product_class_scope=PRODUCT_CLASS_SCOPE_ORDINARY,
        product_class_scope_hash="ordinary-scope-hash",
        product_class_universe_scope_hash="ordinary-universe-scope-hash",
    )
    leveraged = _bundle(
        "leveraged-model",
        product_class_scope=PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE,
        product_class_scope_hash="leveraged-scope-hash",
        product_class_universe_scope_hash="leveraged-universe-scope-hash",
    )

    snapshot = run_scanner(
        _product_scope_scanner_panel(),
        bundles=(ordinary, leveraged),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id=universe.snapshot_id,
        model_states={"ordinary-model": "CHAMPION", "leveraged-model": "CHAMPION"},
        model_eligibility={"ordinary-model": True, "leveraged-model": True},
        config=ScannerConfig(probability_threshold=0.5),
        universe=universe,
    )

    mismatch = snapshot.rows[
        snapshot.rows["exclusion_reason"]
        .astype(str)
        .str.contains(PRODUCT_CLASS_SCOPE_MISMATCH_REASON)
    ]
    assert len(mismatch) == 2
    assert set(mismatch["scanner_routing_result"]) == {PRODUCT_CLASS_SCOPE_MISMATCH_REASON}
    assert bool(
        snapshot.rows.loc[
            (snapshot.rows["model_id"] == "ordinary-model") & (snapshot.rows["ticker"] == "ABC"),
            "product_class_scope_match",
        ].iloc[0]
    )
    assert (
        snapshot.rows.loc[
            (snapshot.rows["model_id"] == "leveraged-model") & (snapshot.rows["ticker"] == "SH"),
            "row_product_class_scope",
        ].iloc[0]
        == PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE
    )
    assert (
        snapshot.rows.loc[
            (snapshot.rows["model_id"] == "ordinary-model") & (snapshot.rows["ticker"] == "SH"),
            "candidate_status",
        ].iloc[0]
        == "REJECTED"
    )


def test_scanner_identity_includes_product_class_scope_metadata(tmp_path: Path) -> None:
    universe = _product_scope_universe()
    ordinary = _bundle(
        product_class_scope=PRODUCT_CLASS_SCOPE_ORDINARY,
        product_class_scope_hash="ordinary-scope-hash-a",
        product_class_universe_scope_hash="ordinary-universe-scope-hash",
    )

    snapshot = run_scanner(
        _product_scope_scanner_panel(),
        bundles=(ordinary,),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id=universe.snapshot_id,
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        universe=universe,
    )

    with engine_connection(tmp_path / "engine.sqlite3") as connection:
        row = connection.execute(
            "SELECT metadata_json FROM scanner_snapshots WHERE scan_id = ?",
            (snapshot.scan_id,),
        ).fetchone()
    metadata = json.loads(row["metadata_json"])
    identity = metadata["canonical_scan_execution_identity"]
    assert metadata["scanner_identity_schema_version"] == 10
    assert metadata["product_class_scope_metadata_hash"]
    assert identity["product_class_schema_version"] == PRODUCT_CLASS_SCHEMA_VERSION
    assert identity["product_class_scope_metadata"]["model-a"]["scope"] == (
        PRODUCT_CLASS_SCOPE_ORDINARY
    )


def test_scanner_identity_changes_when_product_scope_hash_changes(tmp_path: Path) -> None:
    universe = _product_scope_universe()
    base_kwargs = {
        "feature_panel": _product_scope_scanner_panel(),
        "db_path": tmp_path / "engine.sqlite3",
        "output_dir": tmp_path / "scanner",
        "universe_snapshot_id": universe.snapshot_id,
        "model_states": {"model-a": "CHAMPION"},
        "model_eligibility": {"model-a": True},
        "universe": universe,
    }

    first = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                product_class_scope=PRODUCT_CLASS_SCOPE_ORDINARY,
                product_class_scope_hash="ordinary-scope-hash-a",
            ),
        ),
    )
    second = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                product_class_scope=PRODUCT_CLASS_SCOPE_ORDINARY,
                product_class_scope_hash="ordinary-scope-hash-b",
            ),
        ),
    )

    assert first.scan_id != second.scan_id


def test_predict_bundle_outputs_separate_target_before_stop_probability() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [2.0],
            PATH_TARGET_ATR_FEATURE: [1.0],
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


def test_path_metric_heads_receive_own_selected_columns() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            "target_signal": [0.82],
            "return_signal": [0.031],
            "mfe_signal": [0.064],
            "mae_signal": [0.027],
            PATH_TARGET_ATR_FEATURE: [1.0],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(
        expected_return_feature_columns=("return_signal",),
        mfe_feature_columns=("mfe_signal",),
        mae_feature_columns=("mae_signal",),
        return_model=FeatureEchoRegressor("return_signal"),
        mfe_model=FeatureEchoRegressor("mfe_signal"),
        mae_model=FeatureEchoRegressor("mae_signal"),
    )

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["expected_return"] == pytest.approx(0.031)
    assert prediction["expected_mfe"] == pytest.approx(0.064)
    assert prediction["expected_mae"] == pytest.approx(-0.027)
    assert prediction["expected_mae_internal_magnitude"] == pytest.approx(0.027)
    assert prediction["expected_return_feature_manifest_hash"] == "return-manifest"
    assert prediction["mfe_feature_manifest_hash"] == "mfe-manifest"
    assert prediction["mae_feature_manifest_hash"] == "mae-manifest"


def test_path_targets_train_in_atr_units_without_changing_labels() -> None:
    labels = pd.Series([0.02, -0.01, 0.04], name="label_bull_forward_return_10")
    mfe_labels = pd.Series([0.03, 0.00, 0.06], name="label_bull_mfe_10")
    mae_labels = pd.Series([-0.02, 0.00, -0.05], name="label_bull_mae_10")
    atr = pd.Series([0.01, 0.02, 0.04], name=PATH_TARGET_ATR_FEATURE)

    return_target = _path_atr_training_target(
        labels,
        atr,
        head_name=EXPECTED_RETURN_HEAD,
        external_target_name=str(labels.name),
    )
    mfe_target = _path_atr_training_target(
        mfe_labels,
        atr,
        head_name=MFE_HEAD,
        external_target_name=str(mfe_labels.name),
    )
    mae_target = _path_atr_training_target(
        mae_labels,
        atr,
        head_name=MAE_HEAD,
        external_target_name=str(mae_labels.name),
    )

    assert labels.tolist() == [0.02, -0.01, 0.04]
    assert mfe_labels.tolist() == [0.03, 0.0, 0.06]
    assert mae_labels.tolist() == [-0.02, 0.0, -0.05]
    assert return_target.tolist() == pytest.approx([2.0, -0.5, 1.0])
    assert mfe_target.tolist() == pytest.approx([3.0, 0.0, 1.5])
    assert mae_target.tolist() == pytest.approx([2.0, -0.0, 1.25])
    assert return_target.name == "label_bull_forward_return_10__atr_units_atr_pct_14"


def test_predict_bundle_maps_atr_unit_path_predictions_to_canonical_returns() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            PATH_TARGET_ATR_FEATURE: [0.04],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(
        expected_return=1.5,
        mfe_model=ConstantRegressor(2.0),
        mae_model=ConstantRegressor(1.25),
    )

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["expected_return_internal_atr_units"] == pytest.approx(1.5)
    assert prediction["expected_return"] == pytest.approx(0.06)
    assert prediction["expected_mfe_internal_magnitude_atr_units"] == pytest.approx(2.0)
    assert prediction["expected_mfe"] == pytest.approx(0.08)
    assert prediction["expected_mae_internal_magnitude_atr_units"] == pytest.approx(1.25)
    assert prediction["expected_mae"] == pytest.approx(-0.05)
    assert bool(prediction["expected_mfe_signed_prediction_invalid"]) is False
    assert bool(prediction["expected_mae_signed_prediction_invalid"]) is False


def test_prediction_ood_uses_atr_unit_model_space_not_canonical_output() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            PATH_TARGET_ATR_FEATURE: [4.0],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(expected_return=0.5, return_high=1.0)

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["expected_return"] == pytest.approx(2.0)
    assert prediction["expected_return_internal_atr_units"] == pytest.approx(0.5)
    assert bool(prediction["expected_return_out_of_distribution"]) is False


def test_predict_bundle_rejects_missing_atr_for_normalized_path_heads() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            "dollar_volume": [20_000_000.0],
        }
    )

    prediction = predict_bundle(_bundle(), frame).iloc[0]

    assert bool(prediction["expected_return_required_feature_missing"]) is True
    assert bool(prediction["mfe_required_feature_missing"]) is True
    assert bool(prediction["mae_required_feature_missing"]) is True
    assert PATH_TARGET_ATR_FEATURE in str(prediction["expected_return_missing_features"])
    assert PATH_TARGET_ATR_FEATURE in str(prediction["mfe_missing_features"])
    assert PATH_TARGET_ATR_FEATURE in str(prediction["mae_missing_features"])
    assert pd.isna(prediction["expected_return"])
    assert pd.isna(prediction["expected_mfe"])
    assert pd.isna(prediction["expected_mae"])


def test_predict_bundle_marks_retired_logistic_path_heads_without_predicting() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            PATH_TARGET_ATR_FEATURE: [1.0],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(
        mfe_model=RetiredPathHeadModel(family="logistic_regression", head_name=MFE_HEAD),
        mae_model=RetiredPathHeadModel(family="logistic_regression", head_name=MAE_HEAD),
    )
    metadata = {head: dict(value) for head, value in bundle.path_domain_metadata.items()}
    for head in (MFE_HEAD, MAE_HEAD):
        metadata[head].update(
            {
                "path_head_capability_state": (PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR),
                "path_head_retirement_schema_version": "linear_family_path_head_retirement_v1",
                "path_head_retirement_reason": LINEAR_PATH_HEAD_RETIREMENT_REASON,
                "estimator_class": "RetiredPathHeadModel",
                "estimator_loss": "not_applicable_retired_path_head",
            }
        )
    retired_bundle = replace(
        bundle,
        family="logistic_regression",
        path_domain_metadata=metadata,
    )

    prediction = predict_bundle(retired_bundle, frame).iloc[0]

    assert bool(prediction["mfe_path_head_retired"]) is True
    assert bool(prediction["mae_path_head_retired"]) is True
    assert prediction["mfe_path_head_retirement_reason"] == LINEAR_PATH_HEAD_RETIREMENT_REASON
    assert prediction["mae_path_head_retirement_reason"] == LINEAR_PATH_HEAD_RETIREMENT_REASON
    assert pd.isna(prediction["expected_mfe"])
    assert pd.isna(prediction["expected_mae"])
    assert bool(prediction["expected_mfe_magnitude_prediction_invalid"]) is False
    assert bool(prediction["expected_mfe_signed_prediction_invalid"]) is False
    assert bool(prediction["expected_mfe_magnitude_domain_valid"]) is False
    assert bool(prediction["expected_mfe_signed_domain_valid"]) is False
    assert bool(prediction["expected_mfe_sign_contract_valid"]) is True
    assert bool(prediction["expected_mae_magnitude_prediction_invalid"]) is False
    assert bool(prediction["expected_mae_signed_prediction_invalid"]) is False
    assert bool(prediction["expected_mae_magnitude_domain_valid"]) is False
    assert bool(prediction["expected_mae_signed_domain_valid"]) is False
    assert bool(prediction["expected_mae_sign_contract_valid"]) is True


@pytest.mark.parametrize(
    "family",
    ["naive_base_rate", "hist_gradient_boosting", "extra_trees"],
)
@pytest.mark.parametrize("head", [MFE_HEAD, MAE_HEAD])
def test_path_magnitude_estimators_emit_nonnegative_magnitudes(
    family: str,
    head: str,
) -> None:
    frame = pd.DataFrame(
        {
            "feature_a": np.linspace(0.0, 1.0, 40),
            "feature_b": np.sin(np.linspace(0.0, 4.0, 40)),
        }
    )
    target = pd.Series(np.linspace(0.001, 0.08, 40), name=f"{head}_magnitude")
    estimator, spec = build_path_magnitude_estimator(family=family, head_name=head, seed=17)

    estimator.fit(frame, target)
    prediction = estimator.predict(frame)

    assert spec.schema_version == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
    assert np.isfinite(prediction).all()
    assert (prediction >= 0.0).all()
    if family == "hist_gradient_boosting":
        assert spec.loss == "poisson"


@pytest.mark.parametrize("head", [MFE_HEAD, MAE_HEAD])
def test_logistic_path_magnitude_estimator_factory_refuses_retired_heads(head: str) -> None:
    with pytest.raises(ValueError, match=LINEAR_PATH_HEAD_RETIREMENT_REASON):
        build_path_magnitude_estimator(family="logistic_regression", head_name=head, seed=17)


def test_predict_bundle_rejects_invalid_magnitude_without_clipping() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            PATH_TARGET_ATR_FEATURE: [1.0],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(mfe_model=ConstantRegressor(-0.02), mae_model=ConstantRegressor(-0.03))

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["expected_mfe_internal_magnitude"] == pytest.approx(-0.02)
    assert prediction["expected_mfe"] == pytest.approx(-0.02)
    assert bool(prediction["expected_mfe_magnitude_prediction_invalid"]) is True
    assert bool(prediction["expected_mfe_signed_prediction_invalid"]) is True
    assert prediction["expected_mae_internal_magnitude"] == pytest.approx(-0.03)
    assert prediction["expected_mae"] == pytest.approx(0.03)
    assert bool(prediction["expected_mae_magnitude_prediction_invalid"]) is True
    assert bool(prediction["expected_mae_signed_prediction_invalid"]) is True


def test_path_magnitude_prediction_mapping_uses_no_clipping() -> None:
    source = inspect.getsource(_path_magnitude_prediction)
    target_source = inspect.getsource(_path_target_prediction)

    assert ".clip" not in source
    assert "np.clip" not in source
    assert ".clip" not in target_source
    assert "np.clip" not in target_source


def test_predict_bundle_marks_missing_path_domain_metadata_for_legacy_artifacts() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            PATH_TARGET_ATR_FEATURE: [1.0],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(include_path_domain_metadata=False, mae_model=ConstantRegressor(-0.015))

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["mfe_domain_schema_version"] == "legacy_unconstrained_path_metric_model"
    assert bool(prediction["mfe_domain_metadata_missing"]) is True
    assert bool(prediction["mae_domain_metadata_missing"]) is True
    assert prediction["expected_mae"] == pytest.approx(-0.015)


def test_predict_bundle_flags_missing_path_metric_features_without_substitution() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [0.05],
            "target_signal": [0.82],
            PATH_TARGET_ATR_FEATURE: [1.0],
            "dollar_volume": [20_000_000.0],
        }
    )
    bundle = _bundle(
        expected_return_feature_columns=("return_signal",),
        mfe_feature_columns=("mfe_signal",),
        mae_feature_columns=("mae_signal",),
        return_model=FeatureEchoRegressor("return_signal"),
        mfe_model=FeatureEchoRegressor("mfe_signal"),
        mae_model=FeatureEchoRegressor("mae_signal"),
    )

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert bool(prediction["expected_return_required_feature_missing"]) is True
    assert bool(prediction["mfe_required_feature_missing"]) is True
    assert bool(prediction["mae_required_feature_missing"]) is True
    assert prediction["expected_return_missing_features"] == "return_signal"
    assert prediction["mfe_missing_features"] == "mfe_signal"
    assert prediction["mae_missing_features"] == "mae_signal"
    assert pd.isna(prediction["expected_return"])
    assert pd.isna(prediction["expected_mfe"])
    assert pd.isna(prediction["expected_mae"])


def test_scanner_snapshot_is_idempotent_and_contains_residual_attribution(tmp_path: Path) -> None:
    feature_panel = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [2.0],
            PATH_TARGET_ATR_FEATURE: [1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0],
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


def test_scanner_rejects_missing_path_metric_features_explicitly(tmp_path: Path) -> None:
    feature_panel = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"]),
            "symbol": ["AAPL"],
            "f1": [2.0],
            "target_signal": [0.75],
            PATH_TARGET_ATR_FEATURE: [1.0],
            "dollar_volume": [20_000_000.0],
            "sector": ["technology"],
            "market_regime_label": ["mixed"],
        }
    )

    snapshot = run_scanner(
        feature_panel,
        bundles=(
            _bundle(
                expected_return_feature_columns=("return_signal",),
                mfe_feature_columns=("mfe_signal",),
                mae_feature_columns=("mae_signal",),
                return_model=FeatureEchoRegressor("return_signal"),
                mfe_model=FeatureEchoRegressor("mfe_signal"),
                mae_model=FeatureEchoRegressor("mae_signal"),
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
    assert "expected_return_required_feature_missing" in row["exclusion_reason"]
    assert "mfe_required_feature_missing" in row["exclusion_reason"]
    assert "mae_required_feature_missing" in row["exclusion_reason"]
    assert bool(row["expected_return_required_feature_missing"]) is True
    assert bool(row["mfe_required_feature_missing"]) is True
    assert bool(row["mae_required_feature_missing"]) is True


def test_scanner_rejects_missing_path_domain_metadata_explicitly(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(_bundle(include_path_domain_metadata=False, mae_model=ConstantRegressor(-0.015)),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert "mfe_domain_metadata_missing" in row["exclusion_reason"]
    assert "mae_domain_metadata_missing" in row["exclusion_reason"]
    assert bool(row["mfe_domain_metadata_missing"]) is True
    assert bool(row["mae_domain_metadata_missing"]) is True


def test_scanner_rejects_retired_logistic_path_heads_explicitly(tmp_path: Path) -> None:
    bundle = _bundle(
        model_id="model-a",
        mfe_model=RetiredPathHeadModel(family="logistic_regression", head_name=MFE_HEAD),
        mae_model=RetiredPathHeadModel(family="logistic_regression", head_name=MAE_HEAD),
    )
    metadata = {head: dict(value) for head, value in bundle.path_domain_metadata.items()}
    for head in (MFE_HEAD, MAE_HEAD):
        metadata[head].update(
            {
                "path_head_capability_state": (PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR),
                "path_head_retirement_schema_version": "linear_family_path_head_retirement_v1",
                "path_head_retirement_reason": LINEAR_PATH_HEAD_RETIREMENT_REASON,
                "estimator_class": "RetiredPathHeadModel",
                "estimator_loss": "not_applicable_retired_path_head",
            }
        )
    retired_bundle = replace(
        bundle,
        family="logistic_regression",
        path_domain_metadata=metadata,
    )

    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(retired_bundle,),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert f"mfe_{LINEAR_PATH_HEAD_RETIREMENT_REASON}" in row["exclusion_reason"]
    assert f"mae_{LINEAR_PATH_HEAD_RETIREMENT_REASON}" in row["exclusion_reason"]
    assert "mfe_magnitude_prediction_invalid" not in row["exclusion_reason"]
    assert "mae_magnitude_prediction_invalid" not in row["exclusion_reason"]
    assert "mfe_prediction_sign_contract_failed" not in row["exclusion_reason"]
    assert "mae_prediction_sign_contract_failed" not in row["exclusion_reason"]
    assert "nonfinite_prediction" not in row["exclusion_reason"]
    assert row["mfe_path_head_capability_state"] == (
        PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
    )
    assert row["mae_path_head_capability_state"] == (
        PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
    )
    assert bool(row["expected_mfe_magnitude_prediction_invalid"]) is False
    assert bool(row["expected_mfe_signed_prediction_invalid"]) is False
    assert bool(row["expected_mfe_magnitude_domain_valid"]) is False
    assert bool(row["expected_mfe_signed_domain_valid"]) is False
    assert bool(row["expected_mae_magnitude_prediction_invalid"]) is False
    assert bool(row["expected_mae_signed_prediction_invalid"]) is False
    assert bool(row["expected_mae_magnitude_domain_valid"]) is False
    assert bool(row["expected_mae_signed_domain_valid"]) is False


def test_scanner_rejects_invalid_path_magnitude_predictions_explicitly(tmp_path: Path) -> None:
    snapshot = run_scanner(
        _scanner_feature_panel(),
        bundles=(_bundle(mfe_model=ConstantRegressor(-0.02), mae_model=ConstantRegressor(-0.03)),),
        db_path=tmp_path / "engine.sqlite3",
        output_dir=tmp_path / "scanner",
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
        config=ScannerConfig(probability_threshold=0.5),
    )

    row = snapshot.rows.iloc[0]
    assert row["candidate_status"] == "REJECTED"
    assert "mfe_magnitude_prediction_invalid" in row["exclusion_reason"]
    assert "mae_magnitude_prediction_invalid" in row["exclusion_reason"]
    assert "mfe_prediction_sign_contract_failed" in row["exclusion_reason"]
    assert "mae_prediction_sign_contract_failed" in row["exclusion_reason"]
    assert bool(row["expected_mfe_magnitude_prediction_invalid"]) is True
    assert bool(row["expected_mae_magnitude_prediction_invalid"]) is True


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
            PATH_TARGET_ATR_FEATURE: [1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0],
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
            PATH_TARGET_ATR_FEATURE: [1.0, 1.0, 1.0],
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
    path_manifest = run_scanner(
        **base_kwargs,
        bundles=(
            _bundle(
                policy=SelectionPolicy(per_date_limit=2),
                return_manifest="return-manifest-b",
            ),
        ),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    domain_bundle = _bundle(policy=SelectionPolicy(per_date_limit=2))
    domain_metadata = {
        key: dict(value) for key, value in domain_bundle.path_domain_metadata.items()
    }
    domain_metadata[MAE_HEAD]["estimator_hash"] = "changed-mae-estimator-hash"
    path_domain = run_scanner(
        **base_kwargs,
        bundles=(replace(domain_bundle, path_domain_metadata=domain_metadata),),
        universe_snapshot_id="u",
        feature_manifest_hash="features-a",
        model_generation_ids={"model-a": "generation-a"},
    )
    normalization_bundle = _bundle(policy=SelectionPolicy(per_date_limit=2))
    screen_metadata = {
        key: dict(value) for key, value in normalization_bundle.feature_screen_metadata.items()
    }
    screen_metadata[EXPECTED_RETURN_HEAD]["target_normalization_hash"] = (
        "changed-return-target-normalization-hash"
    )
    target_normalization = run_scanner(
        **base_kwargs,
        bundles=(replace(normalization_bundle, feature_screen_metadata=screen_metadata),),
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
                path_manifest.scan_id,
                path_domain.scan_id,
                target_normalization.scan_id,
            }
        )
        == 12
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
    with engine_connection(db_path) as connection:
        row = connection.execute(
            "SELECT metadata_json FROM scanner_snapshots WHERE scan_id = ?",
            (mismatched_ood.scan_id,),
        ).fetchone()
        metadata = json.loads(row["metadata_json"])
        metadata["path_metric_domain_metadata_hash"] = "mismatched"
        connection.execute(
            "UPDATE scanner_snapshots SET metadata_json = ? WHERE scan_id = ?",
            (json.dumps(metadata, sort_keys=True), mismatched_ood.scan_id),
        )

    mismatched_domain = run_scanner(
        feature_panel,
        bundles=(_bundle(),),
        db_path=db_path,
        output_dir=output_dir,
        universe_snapshot_id="u",
        model_states={"model-a": "CHAMPION"},
        model_eligibility={"model-a": True},
    )

    assert mismatched_domain.scan_id not in {
        baseline.scan_id,
        rerun.scan_id,
        mismatched_config.scan_id,
        mismatched_policy.scan_id,
        mismatched_ood.scan_id,
    }
    assert mismatched_domain.created_at_utc != "existing"


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
    assert metadata["scanner_identity_schema_version"] == 10
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
    assert metadata["path_metric_feature_metadata_json"]
    assert metadata["path_metric_feature_metadata_hash"]
    assert metadata["path_metric_domain_metadata_json"]
    assert metadata["path_metric_domain_metadata_hash"]
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
    assert (
        identity["path_metric_feature_metadata"]["model-a"]["expected_return"][
            "selected_feature_manifest_hash"
        ]
        == "return-manifest"
    )
    assert (
        identity["path_metric_feature_metadata"]["model-a"]["expected_return"][
            "target_normalization_schema_version"
        ]
        == PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
    )
    assert (
        identity["path_metric_feature_metadata"]["model-a"]["expected_return"][
            "target_normalization_atr_feature_name"
        ]
        == PATH_TARGET_ATR_FEATURE
    )
    assert (
        identity["path_metric_domain_metadata"]["model-a"]["mae"]["prediction_mapping_version"]
        == PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION
    )
    assert (
        identity["path_metric_domain_metadata"]["model-a"]["mae"]["target_normalization_hash"]
        == _path_target_normalization_payloads()[MAE_HEAD]["target_normalization_hash"]
    )
    assert (
        identity["path_metric_domain_metadata"]["model-a"]["mfe"]["path_head_capability_state"]
        == PATH_HEAD_CAPABILITY_ACTIVE
    )
    assert (
        identity["path_metric_domain_metadata"]["model-a"]["mae"]["path_head_capability_state"]
        == PATH_HEAD_CAPABILITY_ACTIVE
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
