from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from swing_rsi.engine.storage import dumps, engine_connection, loads

ModelState = Literal["EXPERIMENTAL", "CANDIDATE", "CHALLENGER", "CHAMPION", "RETIRED", "REJECTED"]
MetricValue = float | int | str | bool | None


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
                calibration_metrics_json, quality_gates_json, artifact_path, code_commit_hash,
                created_at_utc, promoted_at_utc, retirement_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        metrics=_metric_dict(loads(str(item["metrics_json"]))),
        calibration_metrics=_metric_dict(loads(str(item["calibration_metrics_json"]))),
        quality_gates={
            str(key): bool(value)
            for key, value in _object_dict(loads(str(item["quality_gates_json"]))).items()
        },
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


def promote_model(db_path: str | Path, model_id: str) -> RegisteredModel:
    models = list_models(db_path)
    selected = next((model for model in models if model.model_id == model_id), None)
    if selected is None:
        raise ValueError(f"Unknown model: {model_id}")
    if selected.state not in {"CHALLENGER", "CANDIDATE"}:
        raise ValueError(f"Only challenger/candidate models can be promoted, not {selected.state}")
    failed = [name for name, passed in selected.quality_gates.items() if not passed]
    if failed:
        raise ValueError(f"Model cannot be promoted because quality gates failed: {failed}")

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
