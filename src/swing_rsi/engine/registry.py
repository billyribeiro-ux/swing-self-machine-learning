from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from swing_rsi.engine.gates import (
    FINAL_HOLDOUT_PROMOTION_GATE_ID,
    GATE_VALUE_NOT_AVAILABLE,
    GateResult,
    configuration_hash,
    gate_results_from_jsonable,
    gate_results_to_jsonable,
    holdout_status_allows_promotion,
    holdout_status_block_reason,
    legacy_gate_results,
    normalized_holdout_status,
    promotion_eligibility,
)
from swing_rsi.engine.manifest import hash_file
from swing_rsi.engine.storage import dumps, engine_connection, loads

ModelState = Literal["EXPERIMENTAL", "CANDIDATE", "CHALLENGER", "CHAMPION", "RETIRED", "REJECTED"]
MetricValue = float | int | str | bool | None

FINAL_HOLDOUT_SAMPLE_GATE_IDS = (
    "final_holdout_policy_configured",
    "final_holdout_matured_outcomes_min_100",
    "final_holdout_distinct_signal_dates_min_60",
    "final_holdout_observation_sessions_min_126",
    "final_holdout_calendar_months_min_4",
    "final_holdout_positive_class_min_20",
    "final_holdout_negative_class_min_20",
    "final_holdout_provenance_valid",
    "final_holdout_backfill_absent",
    "final_holdout_data_integrity_valid",
    "final_holdout_frozen_artifacts_unchanged",
    "final_holdout_sample_sufficient",
)


@dataclass(frozen=True)
class RegisteredModel:
    model_id: str
    task: str
    horizon: int
    direction: str
    family: str
    state: ModelState
    training_start: str
    training_end: str
    validation_start: str
    validation_end: str
    holdout_start: str
    holdout_end: str
    universe_snapshot_id: str
    feature_manifest_hash: str
    raw_manifest_hashes: tuple[str, ...]
    hyperparameters: dict[str, object]
    metrics: dict[str, float | int | str | bool | None]
    calibration_metrics: dict[str, float | int | str | bool | None]
    quality_gates: dict[str, bool]
    artifact_path: str
    code_commit_hash: str | None
    created_at_utc: str
    promoted_at_utc: str | None = None
    retirement_reason: str | None = None
    gate_results: tuple[GateResult, ...] = ()


def make_model_id(
    *,
    task: str,
    horizon: int,
    direction: str,
    family: str,
    universe_snapshot_id: str,
    feature_manifest_hash: str,
    created_at_utc: str,
) -> str:
    payload = "|".join(
        [
            task,
            str(horizon),
            direction,
            family,
            universe_snapshot_id,
            feature_manifest_hash,
            created_at_utc,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def register_model(db_path: str | Path, model: RegisteredModel) -> None:
    with engine_connection(db_path) as connection:
        existing = connection.execute(
            "SELECT model_id FROM models WHERE model_id = ?",
            (model.model_id,),
        ).fetchone()
        if existing is not None:
            raise ValueError(f"Model already registered: {model.model_id}")
        connection.execute(
            """
            INSERT INTO models (
                model_id, task, horizon, direction, family, state, training_start, training_end,
                validation_start, validation_end, holdout_start, holdout_end, universe_snapshot_id,
                feature_manifest_hash, raw_manifest_hashes_json, hyperparameters_json, metrics_json,
                calibration_metrics_json, quality_gates_json, gate_results_json, artifact_path,
                code_commit_hash, created_at_utc, promoted_at_utc, retirement_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model.model_id,
                model.task,
                model.horizon,
                model.direction,
                model.family,
                model.state,
                model.training_start,
                model.training_end,
                model.validation_start,
                model.validation_end,
                model.holdout_start,
                model.holdout_end,
                model.universe_snapshot_id,
                model.feature_manifest_hash,
                dumps(model.raw_manifest_hashes),
                dumps(model.hyperparameters),
                dumps(model.metrics),
                dumps(model.calibration_metrics),
                dumps(model.quality_gates),
                dumps(gate_results_to_jsonable(model.gate_results)),
                model.artifact_path,
                model.code_commit_hash,
                model.created_at_utc,
                model.promoted_at_utc,
                model.retirement_reason,
            ),
        )


def _object_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value if isinstance(value, dict) else {})


def _metric_dict(value: object) -> dict[str, MetricValue]:
    return cast(dict[str, MetricValue], _object_dict(value))


def _row_to_model(row: Any) -> RegisteredModel:
    keys = row.keys()
    item = {key: row[key] for key in keys}
    state = cast(ModelState, str(item["state"]))
    metrics = _metric_dict(loads(str(item["metrics_json"])))
    calibration_metrics = _metric_dict(loads(str(item["calibration_metrics_json"])))
    quality_gates = {
        str(key): bool(value)
        for key, value in _object_dict(loads(str(item["quality_gates_json"]))).items()
    }
    gate_payload = loads(str(item["gate_results_json"])) if "gate_results_json" in item else []
    gates = gate_results_from_jsonable(gate_payload)
    if not gates and quality_gates:
        gates = legacy_gate_results(quality_gates)
    return RegisteredModel(
        model_id=str(item["model_id"]),
        task=str(item["task"]),
        horizon=int(item["horizon"]),
        direction=str(item["direction"]),
        family=str(item["family"]),
        state=state,
        training_start=str(item["training_start"]),
        training_end=str(item["training_end"]),
        validation_start=str(item["validation_start"]),
        validation_end=str(item["validation_end"]),
        holdout_start=str(item["holdout_start"]),
        holdout_end=str(item["holdout_end"]),
        universe_snapshot_id=str(item["universe_snapshot_id"]),
        feature_manifest_hash=str(item["feature_manifest_hash"]),
        raw_manifest_hashes=tuple(
            str(value) for value in cast(list[object], loads(str(item["raw_manifest_hashes_json"])))
        ),
        hyperparameters=_object_dict(loads(str(item["hyperparameters_json"]))),
        metrics=metrics,
        calibration_metrics=calibration_metrics,
        quality_gates=quality_gates,
        gate_results=gates,
        artifact_path=str(item["artifact_path"]),
        code_commit_hash=str(item["code_commit_hash"]) if item["code_commit_hash"] else None,
        created_at_utc=str(item["created_at_utc"]),
        promoted_at_utc=str(item["promoted_at_utc"]) if item["promoted_at_utc"] else None,
        retirement_reason=str(item["retirement_reason"]) if item["retirement_reason"] else None,
    )


def list_models(db_path: str | Path) -> list[RegisteredModel]:
    with engine_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM models ORDER BY created_at_utc DESC, model_id"
        ).fetchall()
    return [_row_to_model(row) for row in rows]


def champion_models(db_path: str | Path) -> list[RegisteredModel]:
    return [model for model in list_models(db_path) if model.state == "CHAMPION"]


def challenger_models(db_path: str | Path) -> list[RegisteredModel]:
    return [model for model in list_models(db_path) if model.state == "CHALLENGER"]


def _registered_holdout_status(model: RegisteredModel) -> str:
    metric_status = normalized_holdout_status(model.metrics.get("holdout_status"))
    if metric_status != GATE_VALUE_NOT_AVAILABLE:
        return metric_status
    gate = next(
        (
            result
            for result in model.gate_results
            if result.gate_id == FINAL_HOLDOUT_PROMOTION_GATE_ID
        ),
        None,
    )
    if gate is None:
        return metric_status
    return normalized_holdout_status(gate.actual_value)


def _model_ood_hash(model: RegisteredModel) -> str:
    payload: dict[str, object] = {
        key: value
        for key, value in sorted(model.metrics.items())
        if "ood" in key or key == "prediction_ood_governance_version"
    }
    return configuration_hash(payload)


def _final_holdout_freeze_blocker(db_path: str | Path, model: RegisteredModel) -> str | None:
    run_id = model.metrics.get("final_holdout_run_id")
    evidence_hash = model.metrics.get("final_holdout_evidence_manifest_hash")
    if not run_id or not evidence_hash:
        return "missing final-holdout run ID or evidence manifest hash"
    gates_by_id = {gate.gate_id: gate for gate in model.gate_results}
    missing_sample_gates = [
        gate_id for gate_id in FINAL_HOLDOUT_SAMPLE_GATE_IDS if gate_id not in gates_by_id
    ]
    if missing_sample_gates:
        return f"missing final-holdout sample gates: {missing_sample_gates}"
    failing_sample_gates = [
        f"{gate_id}:{gates_by_id[gate_id].status}"
        for gate_id in FINAL_HOLDOUT_SAMPLE_GATE_IDS
        if gates_by_id[gate_id].status != "PASS"
    ]
    if failing_sample_gates:
        return f"final-holdout sample gates are not passing: {failing_sample_gates}"
    with engine_connection(db_path) as connection:
        run_row = connection.execute(
            """
            SELECT execution_policy_hash
            FROM final_holdout_runs
            WHERE run_id = ?
            """,
            (str(run_id),),
        ).fetchone()
        row = connection.execute(
            """
            SELECT artifact_path, artifact_hash, selection_policy_hash,
                   calibration_governance_hash, ood_governance_hash, research_only,
                   metadata_json
            FROM final_holdout_models
            WHERE run_id = ? AND model_id = ?
            """,
            (str(run_id), model.model_id),
        ).fetchone()
    if run_row is None:
        return "missing final-holdout run record"
    if row is None:
        return "missing final-holdout enrollment record"
    if bool(row["research_only"]):
        return "research-only final-holdout enrollment is not promotable"
    frozen_metadata = cast(dict[str, object], loads(str(row["metadata_json"])))
    artifact_path = Path(str(row["artifact_path"]))
    if not artifact_path.exists():
        return "frozen final-holdout artifact is missing"
    if hash_file(artifact_path) != str(row["artifact_hash"]):
        return "frozen final-holdout artifact hash changed"
    if model.feature_manifest_hash != str(frozen_metadata.get("feature_manifest_hash") or ""):
        return "frozen final-holdout feature-manifest hash changed"
    if str(model.metrics.get("selection_policy_configuration_hash") or "") != str(
        row["selection_policy_hash"]
    ):
        return "frozen final-holdout selection-policy hash changed"
    if str(model.metrics.get("target_before_stop_calibration_manifest_hash") or "") != str(
        row["calibration_governance_hash"]
    ):
        return "frozen final-holdout calibration-governance hash changed"
    if str(model.metrics.get("target_before_stop_calibrator_artifact_hash") or "") != str(
        frozen_metadata.get("calibrator_artifact_hash") or ""
    ):
        return "frozen final-holdout calibrator artifact hash changed"
    if _model_ood_hash(model) != str(row["ood_governance_hash"]):
        return "frozen final-holdout OOD-governance hash changed"
    frozen_execution_policy = str(frozen_metadata.get("execution_policy_hash") or "")
    if frozen_execution_policy and frozen_execution_policy != str(run_row["execution_policy_hash"]):
        return "frozen final-holdout execution-policy hash changed"
    frozen_code_hash = frozen_metadata.get("code_commit_hash")
    if frozen_code_hash and model.code_commit_hash != str(frozen_code_hash):
        return "frozen final-holdout code hash changed"
    return None


def promote_model(db_path: str | Path, model_id: str) -> RegisteredModel:
    models = list_models(db_path)
    selected = next((model for model in models if model.model_id == model_id), None)
    if selected is None:
        raise ValueError(f"Unknown model: {model_id}")
    if selected.state not in {"CHALLENGER", "CANDIDATE"}:
        raise ValueError(f"Only challenger/candidate models can be promoted, not {selected.state}")
    holdout_status = _registered_holdout_status(selected)
    if not holdout_status_allows_promotion(holdout_status):
        raise ValueError(
            "Model cannot be promoted because holdout status blocks promotion: "
            f"{holdout_status_block_reason(holdout_status)}"
        )
    eligibility = promotion_eligibility(selected.gate_results)
    if not eligibility.eligible:
        raise ValueError(
            "Model cannot be promoted because mandatory gate results block promotion: "
            f"{list(eligibility.blocked_reasons)}"
        )
    freeze_blocker = _final_holdout_freeze_blocker(db_path, selected)
    if freeze_blocker is not None:
        raise ValueError(
            "Model cannot be promoted because final-holdout evidence is not valid: "
            f"{freeze_blocker}"
        )

    promoted_at = datetime.now(UTC).isoformat()
    with engine_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE models
            SET state = 'RETIRED', retirement_reason = ?
            WHERE state = 'CHAMPION'
              AND horizon = ?
              AND direction = ?
              AND task = ?
            """,
            (
                f"Replaced by champion {model_id}",
                selected.horizon,
                selected.direction,
                selected.task,
            ),
        )
        connection.execute(
            "UPDATE models SET state = 'CHAMPION', promoted_at_utc = ? WHERE model_id = ?",
            (promoted_at, model_id),
        )
    return next(model for model in list_models(db_path) if model.model_id == model_id)


def model_to_row(model: RegisteredModel) -> dict[str, object]:
    return asdict(model)
