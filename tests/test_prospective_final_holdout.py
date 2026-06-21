from __future__ import annotations

import json
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from swing_rsi.engine.calibration_governance import TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION
from swing_rsi.engine.final_holdout import (
    FINAL_HOLDOUT_EVENT_PREFIX,
    FINAL_HOLDOUT_SCHEMA_VERSION,
    SHADOW_FINAL_HOLDOUT_MODE,
    evaluate_final_holdout_run,
    final_holdout_events,
    final_holdout_status_frame,
    initialize_final_holdout_run,
    list_final_holdout_models,
    list_final_holdout_runs,
    process_final_holdout_update,
    reconstruct_final_holdout_state,
)
from swing_rsi.engine.forward import append_forward_event
from swing_rsi.engine.gates import (
    DEVELOPMENT_HOLDOUT_STATUS,
    FINAL_HOLDOUT_PROMOTION_GATE_ID,
    FINAL_HOLDOUT_STATUS,
    configuration_hash,
    make_gate,
    promotion_eligibility,
)
from swing_rsi.engine.manifest import hash_file
from swing_rsi.engine.models import ModelBundle, save_model_bundle
from swing_rsi.engine.ood import PREDICTION_OOD_GOVERNANCE_VERSION
from swing_rsi.engine.registry import RegisteredModel, promote_model, register_model
from swing_rsi.engine.selection import SelectionPolicy
from swing_rsi.engine.storage import dumps, engine_connection, loads


class ConstantClassifier:
    def __init__(self, probability: float = 0.75) -> None:
        self.probability = probability

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return np.tile(np.array([[1.0 - self.probability, self.probability]]), (len(frame), 1))


class IdentityCalibrator:
    def predict(self, values: np.ndarray) -> np.ndarray:
        return np.asarray(values, dtype=float)


class ConstantRegressor:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.full(len(frame), self.value)


def _pass_gate(gate_id: str = "development_gate_passed") -> object:
    return make_gate(
        gate_id=gate_id,
        gate_name="Development Gate Passed",
        category="development",
        scope="model",
        metric_name=gate_id,
        threshold=True,
        comparator="is true",
        actual_value=True,
        status="PASS",
        mandatory=True,
        evidence_source="test",
        reason="Synthetic development gate passed.",
        configuration_hash_value="test-config",
    )


def _final_development_gate() -> object:
    return make_gate(
        gate_id=FINAL_HOLDOUT_PROMOTION_GATE_ID,
        gate_name="Final Holdout Required For Promotion",
        category="research integrity",
        scope="model",
        metric_name="holdout_status",
        threshold=FINAL_HOLDOUT_STATUS,
        comparator="equals",
        actual_value=DEVELOPMENT_HOLDOUT_STATUS,
        status="FAIL",
        mandatory=True,
        evidence_source="test",
        reason="Only a development holdout is available.",
        configuration_hash_value="test-config",
    )


def _ood_metrics() -> dict[str, object]:
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
    for head, low, high in (
        ("return", -0.10, 0.10),
        ("mfe", 0.0, 0.20),
        ("mae", -0.20, 0.0),
    ):
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
                f"{head}_ood_severity_q99_limit": 0.10,
                f"{head}_holdout_ood_rate": 0.0,
                f"{head}_holdout_ood_q99_severity": 0.0,
                f"{head}_holdout_ood_max_severity": 0.0,
                f"{head}_holdout_prediction_nonfinite_count": 0,
            }
        )
    return metrics


def _policy_metrics(
    *,
    policy_hash: str = "policy-hash-a",
    calibration_hash: str = "calibration-manifest-a",
) -> dict[str, object]:
    policy = SelectionPolicy()
    return {
        **_ood_metrics(),
        "selection_policy_json": json.dumps(asdict(policy), sort_keys=True),
        "selection_policy_configuration_hash": policy_hash,
        "target_before_stop_calibration_governance_schema": (
            TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION
        ),
        "target_before_stop_calibration_method": "identity",
        "target_before_stop_calibration_manifest_hash": calibration_hash,
        "target_before_stop_calibrator_artifact_hash": "calibrator-artifact-a",
        "target_before_stop_calibration_selection_reason": "test_identity",
        "holdout_status": DEVELOPMENT_HOLDOUT_STATUS,
    }


def _bundle(model_id: str, metrics: dict[str, object]) -> ModelBundle:
    training = pd.DataFrame(
        {
            "f1": [0.0, 1.0, 2.0],
            "dollar_volume": [20_000_000.0, 20_000_000.0, 20_000_000.0],
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
        family="test_family",
        feature_columns=("f1", "dollar_volume"),
        feature_family_by_column={"f1": "test", "dollar_volume": "liquidity"},
        classifier=ConstantClassifier(0.75),
        calibrator=IdentityCalibrator(),
        target_before_stop_model=ConstantClassifier(0.75),
        target_before_stop_calibrator=IdentityCalibrator(),
        return_model=ConstantRegressor(0.02),
        mfe_model=ConstantRegressor(0.04),
        mae_model=ConstantRegressor(-0.015),
        training_medians={"f1": 1.0, "dollar_volume": 20_000_000.0},
        training_means={"f1": 1.0, "dollar_volume": 20_000_000.0},
        training_stds={"f1": 1.0, "dollar_volume": 1.0},
        training_matrix=training,
        training_labels=labels,
        metrics=metrics,
        calibration_metrics={},
        gate_results=(_pass_gate(), _final_development_gate()),
        head_feature_columns={
            "primary_positive_return": ("f1", "dollar_volume"),
            "target_before_stop": ("f1", "dollar_volume"),
            "expected_return": ("f1", "dollar_volume"),
            "mfe": ("f1", "dollar_volume"),
            "mae": ("f1", "dollar_volume"),
        },
        head_feature_manifests={
            "primary_positive_return": "primary-manifest",
            "target_before_stop": "target-manifest",
            "expected_return": "return-manifest",
            "mfe": "mfe-manifest",
            "mae": "mae-manifest",
        },
        feature_screen_metadata={
            "target_before_stop": {
                "screening_schema_version": "target_specific_feature_screen_v1",
                "selected_feature_count": 2,
                "selected_feature_families": {"test": 1, "liquidity": 1},
                "selected_feature_manifest_hash": "target-manifest",
            }
        },
    )


def _registered_model(
    root: Path,
    *,
    model_id: str = "model-final-holdout-a",
    family: str = "test_family",
    state: str = "CHALLENGER",
    metrics: dict[str, object] | None = None,
    created_at: str = "2026-06-21T19:28:21.433666+00:00",
) -> RegisteredModel:
    metrics = metrics or _policy_metrics()
    artifact = save_model_bundle(
        _bundle(model_id, metrics),
        root / "artifacts" / "models" / f"{model_id}.joblib",
    )
    return RegisteredModel(
        model_id=model_id,
        task="autonomous_swing_scanner",
        horizon=10,
        direction="bull",
        family=family,
        state=state,  # type: ignore[arg-type]
        training_start="2016-06-20",
        training_end="2022-05-12",
        validation_start="2022-05-13",
        validation_end="2024-04-17",
        holdout_start="2024-04-18",
        holdout_end="2026-06-18",
        universe_snapshot_id="test-universe",
        feature_manifest_hash="test-feature-manifest",
        raw_manifest_hashes=(),
        hyperparameters={},
        metrics=metrics,  # type: ignore[arg-type]
        calibration_metrics={},
        quality_gates={"development_gate_passed": True, FINAL_HOLDOUT_PROMOTION_GATE_ID: False},
        artifact_path=str(artifact),
        code_commit_hash=None,
        created_at_utc=created_at,
        gate_results=(_pass_gate(), _final_development_gate()),
    )


def _register(root: Path, model: RegisteredModel) -> None:
    register_model(root / "state" / "engine.sqlite3", model)


def _feature_panel(dates: list[str], *, available_at: str | None = None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for date in dates:
        row: dict[str, object] = {
            "Date": pd.Timestamp(date),
            "symbol": "AAPL",
            "f1": 2.0,
            "dollar_volume": 20_000_000.0,
            "sector": "technology",
            "market_regime_label": "mixed",
            "Close": 101.0,
        }
        if available_at is not None:
            row["local_available_at_utc"] = available_at
        rows.append(row)
    return pd.DataFrame(rows)


def _future_feature_panel(run_created_at: str, dates: list[str]) -> pd.DataFrame:
    available_at = (pd.Timestamp(run_created_at) + timedelta(minutes=5)).isoformat()
    return _feature_panel(dates, available_at=available_at)


def _ohlcv(dates: list[str]) -> pd.DataFrame:
    index = pd.to_datetime(dates)
    base = np.arange(len(index), dtype=float) + 100.0
    return pd.DataFrame(
        {
            "Open": base,
            "High": base + 2.0,
            "Low": base - 2.0,
            "Close": base + 1.0,
            "Volume": np.full(len(index), 1_000_000),
        },
        index=index,
    )


def _mutate_model_metrics(root: Path, model_id: str, updates: dict[str, object]) -> None:
    db = root / "state" / "engine.sqlite3"
    with engine_connection(db) as connection:
        row = connection.execute(
            "SELECT metrics_json FROM models WHERE model_id = ?",
            (model_id,),
        ).fetchone()
        assert row is not None
        metrics = dict(loads(str(row["metrics_json"])))
        metrics.update(updates)
        connection.execute(
            "UPDATE models SET metrics_json = ? WHERE model_id = ?",
            (dumps(metrics), model_id),
        )


def test_initialization_freezes_models_artifact_hashes_and_baseline(tmp_path: Path) -> None:
    model = _registered_model(tmp_path)
    _register(tmp_path, model)

    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )

    assert report.run is not None
    assert report.run.schema_version == FINAL_HOLDOUT_SCHEMA_VERSION
    assert report.run.baseline_market_date == "2026-06-18"
    assert report.run.model_ids == (model.model_id,)
    enrolled = list_final_holdout_models(tmp_path / "state" / "engine.sqlite3", report.run.run_id)
    assert len(enrolled) == 1
    assert enrolled[0].artifact_hash == hash_file(model.artifact_path)
    assert enrolled[0].selection_policy_hash == "policy-hash-a"
    assert enrolled[0].calibration_governance_hash == "calibration-manifest-a"


def test_default_enrollment_excludes_naive_and_development_gate_ineligible_models(
    tmp_path: Path,
) -> None:
    _register(tmp_path, _registered_model(tmp_path, model_id="model-good"))
    _register(
        tmp_path,
        _registered_model(tmp_path, model_id="model-naive", family="naive_base_rate"),
    )
    blocked = _registered_model(tmp_path, model_id="model-blocked")
    blocked = RegisteredModel(
        **{
            **asdict(blocked),
            "gate_results": (
                make_gate(
                    gate_id="development_gate_failed",
                    gate_name="Development Gate Failed",
                    category="development",
                    scope="model",
                    metric_name="development_gate_failed",
                    threshold=True,
                    comparator="is true",
                    actual_value=False,
                    status="FAIL",
                    mandatory=True,
                    evidence_source="test",
                    reason="Synthetic blocker.",
                    configuration_hash_value="test-config",
                ),
                _final_development_gate(),
            ),
        }
    )
    _register(tmp_path, blocked)

    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )

    assert report.run is not None
    assert report.run.model_ids == ("model-good",)
    assert "naive_control_excluded" in report.blockers_by_model["model-naive"]
    assert any(
        "development_gate_failed" in item for item in report.blockers_by_model["model-blocked"]
    )


def test_no_eligible_models_creates_no_fake_enrollment(tmp_path: Path) -> None:
    _register(
        tmp_path,
        _registered_model(tmp_path, model_id="model-naive-only", family="naive_base_rate"),
    )

    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )

    assert report.run is None
    assert not list_final_holdout_runs(tmp_path / "state" / "engine.sqlite3")
    assert "naive_control_excluded" in report.blockers_by_model["model-naive-only"]


def test_existing_historical_session_without_provenance_is_blocked(tmp_path: Path) -> None:
    _register(tmp_path, _registered_model(tmp_path))
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None

    result = process_final_holdout_update(
        tmp_path,
        feature_panel=_feature_panel(["2026-06-18", "2026-06-19"]),
        frames={"AAPL": _ohlcv(["2026-06-18", "2026-06-19"])},
    )

    assert result.processed_sessions == ()
    assert result.blocked_sessions["2026-06-19"].startswith("FINAL_HOLDOUT_BACKFILL_BLOCKED")
    events = final_holdout_events(tmp_path / "state" / "engine.sqlite3", report.run.run_id)
    assert set(events["event_type"]) == {"FINAL_HOLDOUT_DATA_INVALIDATED"}


def test_future_session_with_provenance_processes_and_rerun_is_idempotent(
    tmp_path: Path,
) -> None:
    _register(tmp_path, _registered_model(tmp_path))
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None
    feature_panel = _future_feature_panel(report.run.created_at_utc, ["2026-06-18", "2026-06-19"])
    frames = {"AAPL": _ohlcv(["2026-06-18", "2026-06-19"])}

    first = process_final_holdout_update(tmp_path, feature_panel=feature_panel, frames=frames)
    second = process_final_holdout_update(tmp_path, feature_panel=feature_panel, frames=frames)

    assert first.processed_sessions == ("2026-06-19",)
    assert first.events_inserted > 0
    assert second.processed_sessions == ()
    assert second.events_inserted == 0
    status = final_holdout_status_frame(tmp_path)
    assert status.loc[0, "signals"] == 1


def test_signal_is_recorded_before_future_entry_outcome(tmp_path: Path) -> None:
    _register(tmp_path, _registered_model(tmp_path))
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None
    feature_panel = _future_feature_panel(
        report.run.created_at_utc,
        ["2026-06-18", "2026-06-19", "2026-06-22"],
    )

    process_final_holdout_update(
        tmp_path,
        feature_panel=feature_panel,
        frames={"AAPL": _ohlcv(["2026-06-18", "2026-06-19", "2026-06-22"])},
    )

    events = final_holdout_events(tmp_path / "state" / "engine.sqlite3", report.run.run_id)
    signal = events.loc[events["event_type"] == "FINAL_HOLDOUT_SIGNAL_CREATED"].iloc[0]
    fill = events.loc[events["event_type"] == "FINAL_HOLDOUT_ENTRY_FILLED"].iloc[0]
    assert signal["market_as_of_date"] == "2026-06-19"
    assert fill["market_as_of_date"] == "2026-06-22"
    assert dict(signal["payload"])["mode"] == SHADOW_FINAL_HOLDOUT_MODE


@pytest.mark.parametrize(
    ("drift_kind", "mutation"),
    [
        ("artifact", {}),
        ("selection", {"selection_policy_configuration_hash": "changed-policy"}),
        ("calibration", {"target_before_stop_calibration_manifest_hash": "changed-calibration"}),
        ("ood", {"return_holdout_ood_rate": 0.50}),
    ],
)
def test_frozen_artifacts_and_governance_hashes_cannot_silently_change(
    tmp_path: Path,
    drift_kind: str,
    mutation: dict[str, object],
) -> None:
    model = _registered_model(tmp_path)
    _register(tmp_path, model)
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None
    if drift_kind == "artifact":
        Path(model.artifact_path).write_bytes(Path(model.artifact_path).read_bytes() + b"drift")
    else:
        _mutate_model_metrics(tmp_path, model.model_id, mutation)

    result = process_final_holdout_update(
        tmp_path,
        feature_panel=_future_feature_panel(
            report.run.created_at_utc, ["2026-06-18", "2026-06-19"]
        ),
        frames={"AAPL": _ohlcv(["2026-06-18", "2026-06-19"])},
    )

    assert "2026-06-19" in result.blocked_sessions
    assert (
        "changed" in result.blocked_sessions["2026-06-19"]
        or "hash" in result.blocked_sessions["2026-06-19"]
    )
    runs = list_final_holdout_runs(tmp_path / "state" / "engine.sqlite3")
    assert runs[0].status == "INVALIDATED"


def test_state_reconstructs_from_append_only_events(tmp_path: Path) -> None:
    _register(tmp_path, _registered_model(tmp_path))
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None
    process_final_holdout_update(
        tmp_path,
        feature_panel=_future_feature_panel(
            report.run.created_at_utc,
            ["2026-06-18", "2026-06-19", "2026-06-22"],
        ),
        frames={"AAPL": _ohlcv(["2026-06-18", "2026-06-19", "2026-06-22"])},
    )

    state = reconstruct_final_holdout_state(
        tmp_path / "state" / "engine.sqlite3",
        report.run.run_id,
    )

    assert not state.empty
    assert set(state["run_id"]) == {report.run.run_id}
    assert any(status in {"ENTRY_FILLED", "ENTRY_PENDING"} for status in state["status"])


def test_research_only_enrollment_cannot_become_promotion_eligible(tmp_path: Path) -> None:
    blocked = _registered_model(tmp_path, model_id="model-research-only")
    blocked = RegisteredModel(
        **{
            **asdict(blocked),
            "gate_results": (
                make_gate(
                    gate_id="development_gate_failed",
                    gate_name="Development Gate Failed",
                    category="development",
                    scope="model",
                    metric_name="development_gate_failed",
                    threshold=True,
                    comparator="is true",
                    actual_value=False,
                    status="FAIL",
                    mandatory=True,
                    evidence_source="test",
                    reason="Synthetic blocker.",
                    configuration_hash_value="test-config",
                ),
                _final_development_gate(),
            ),
        }
    )
    _register(tmp_path, blocked)
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        research_only=True,
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None

    evaluation = evaluate_final_holdout_run(
        tmp_path,
        run_id=report.run.run_id,
        minimum_matured_outcomes=0,
    )

    gates = evaluation.gates_by_model["model-research-only"]
    assert any(gate.gate_id == "final_holdout_research_only_not_promotable" for gate in gates)
    assert not promotion_eligibility(gates).eligible


def test_final_holdout_status_requires_evaluation_and_does_not_imply_pass(
    tmp_path: Path,
) -> None:
    model = _registered_model(tmp_path)
    _register(tmp_path, model)
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None

    before = promote_model
    with pytest.raises(ValueError, match="holdout status blocks promotion"):
        before(tmp_path / "state" / "engine.sqlite3", model.model_id)

    evaluation = evaluate_final_holdout_run(tmp_path, run_id=report.run.run_id)
    metrics = evaluation.metrics_by_model[model.model_id]
    gates = evaluation.gates_by_model[model.model_id]

    assert metrics["holdout_status"] == FINAL_HOLDOUT_STATUS
    assert any(gate.status == "NOT_CONFIGURED" for gate in gates)
    assert not promotion_eligibility(gates).eligible
    with pytest.raises(ValueError, match="mandatory gate results block promotion"):
        promote_model(tmp_path / "state" / "engine.sqlite3", model.model_id)


def test_missing_final_holdout_evidence_blocks_manual_promotion(tmp_path: Path) -> None:
    metrics = {
        **_policy_metrics(),
        "holdout_status": FINAL_HOLDOUT_STATUS,
    }
    final_gate = make_gate(
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
        reason="Synthetic final-holdout gate pass without evidence.",
        configuration_hash_value="test-config",
    )
    model = _registered_model(tmp_path, metrics=metrics)
    model = RegisteredModel(**{**asdict(model), "gate_results": (_pass_gate(), final_gate)})
    _register(tmp_path, model)

    with pytest.raises(ValueError, match="missing final-holdout run ID"):
        promote_model(tmp_path / "state" / "engine.sqlite3", model.model_id)


def test_manual_promotion_remains_required_after_passing_final_holdout_gates(
    tmp_path: Path,
) -> None:
    model = _registered_model(tmp_path)
    _register(tmp_path, model)
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None

    evaluation = evaluate_final_holdout_run(
        tmp_path,
        run_id=report.run.run_id,
        minimum_matured_outcomes=0,
    )

    assert evaluation.status == "EVALUATED_PASS"
    with engine_connection(tmp_path / "state" / "engine.sqlite3") as connection:
        row = connection.execute(
            "SELECT state FROM models WHERE model_id = ?",
            (model.model_id,),
        ).fetchone()
    assert row is not None
    assert row["state"] == "CHALLENGER"


def test_final_holdout_events_are_append_only(tmp_path: Path) -> None:
    _register(tmp_path, _registered_model(tmp_path))
    report = initialize_final_holdout_run(
        tmp_path,
        generation="latest",
        feature_panel=_feature_panel(["2026-06-18"]),
    )
    assert report.run is not None
    db = tmp_path / "state" / "engine.sqlite3"

    first = append_forward_event(
        db,
        event_type=f"{FINAL_HOLDOUT_EVENT_PREFIX}DATA_INVALIDATED",
        market_as_of_date="2026-06-19",
        ticker="RUN",
        direction="n/a",
        model_id="run",
        scanner_snapshot_id=None,
        feature_snapshot_hash=report.run.feature_manifest_hash,
        payload={"run_id": report.run.run_id, "reason": "test"},
        unique_suffix=f"{report.run.run_id}|same",
    )
    second = append_forward_event(
        db,
        event_type=f"{FINAL_HOLDOUT_EVENT_PREFIX}DATA_INVALIDATED",
        market_as_of_date="2026-06-19",
        ticker="RUN",
        direction="n/a",
        model_id="run",
        scanner_snapshot_id=None,
        feature_snapshot_hash=report.run.feature_manifest_hash,
        payload={"run_id": report.run.run_id, "reason": "changed"},
        unique_suffix=f"{report.run.run_id}|same",
    )

    assert first.inserted
    assert not second.inserted
    events = final_holdout_events(db, report.run.run_id)
    assert len(events) == 1
    assert dict(events.iloc[0]["payload"])["reason"] == "test"


def test_development_holdout_cannot_satisfy_promotion(tmp_path: Path) -> None:
    model = _registered_model(tmp_path)
    _register(tmp_path, model)

    with pytest.raises(ValueError, match="DEVELOPMENT_HOLDOUT"):
        promote_model(tmp_path / "state" / "engine.sqlite3", model.model_id)


def test_final_holdout_configuration_hash_is_stable_for_test_fixture() -> None:
    assert configuration_hash({"schema": FINAL_HOLDOUT_SCHEMA_VERSION}) == configuration_hash(
        {"schema": FINAL_HOLDOUT_SCHEMA_VERSION}
    )
