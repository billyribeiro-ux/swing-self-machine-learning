from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from swing_rsi.config import ProjectPaths
from swing_rsi.data.loader import load_ohlcv_csv
from swing_rsi.engine.forward import (
    advance_forward_positions,
    append_forward_event,
    create_pending_events_from_snapshot,
    list_forward_events,
)
from swing_rsi.engine.gates import (
    FINAL_HOLDOUT_PROMOTION_GATE_ID,
    FINAL_HOLDOUT_STATUS,
    GATE_VALUE_NOT_AVAILABLE,
    GateResult,
    configuration_hash,
    gate_results_to_jsonable,
    make_gate,
    promotion_eligibility,
    quality_gate_bool_map,
)
from swing_rsi.engine.manifest import current_commit_hash, hash_file
from swing_rsi.engine.models import load_model_bundle
from swing_rsi.engine.ood import PREDICTION_OOD_GOVERNANCE_VERSION
from swing_rsi.engine.registry import RegisteredModel, list_models
from swing_rsi.engine.scanner import (
    SCANNER_IDENTITY_SCHEMA_VERSION,
    ScannerConfig,
    run_scanner,
)
from swing_rsi.engine.storage import dumps, engine_connection, loads

FINAL_HOLDOUT_SCHEMA_VERSION = "prospective_final_holdout_v1"
SHADOW_FINAL_HOLDOUT_MODE = "SHADOW_FINAL_HOLDOUT"
FINAL_HOLDOUT_EVENT_PREFIX = "FINAL_HOLDOUT_"

RunStatus = Literal[
    "CREATED",
    "COLLECTING",
    "READY_FOR_EVALUATION",
    "EVALUATED_PASS",
    "EVALUATED_FAIL",
    "INVALIDATED",
    "CLOSED",
]


@dataclass(frozen=True)
class FinalHoldoutRun:
    run_id: str
    schema_version: str
    created_at_utc: str
    creation_git_commit: str | None
    baseline_market_date: str
    first_eligible_future_signal_date: str | None
    universe_snapshot_id: str
    feature_manifest_hash: str
    generation_id: str
    model_ids: tuple[str, ...]
    scanner_identity_version: int
    execution_policy_hash: str
    horizon: int
    direction: str
    status: RunStatus
    invalidation_reason: str | None
    latest_processed_market_date: str | None
    metadata: dict[str, object]


@dataclass(frozen=True)
class FinalHoldoutModel:
    run_id: str
    model_id: str
    generation_id: str
    artifact_path: str
    artifact_hash: str
    model_state_at_enrollment: str
    development_gate_eligible: bool
    research_only: bool
    selection_policy_hash: str
    calibration_governance_hash: str
    ood_governance_hash: str
    enrollment_blockers: tuple[str, ...]
    metadata: dict[str, object]


@dataclass(frozen=True)
class FinalHoldoutEnrollmentReport:
    run: FinalHoldoutRun | None
    enrolled_models: tuple[FinalHoldoutModel, ...]
    blockers_by_model: dict[str, tuple[str, ...]]
    message: str


@dataclass(frozen=True)
class FinalHoldoutUpdateResult:
    processed_sessions: tuple[str, ...]
    blocked_sessions: dict[str, str]
    events_inserted: int
    reports: tuple[Path, ...]


@dataclass(frozen=True)
class FinalHoldoutEvaluationResult:
    run_id: str
    status: RunStatus
    metrics_by_model: dict[str, dict[str, object]]
    gates_by_model: dict[str, tuple[GateResult, ...]]
    evidence_manifest_hashes: dict[str, str]


def _stable_hash(value: object, *, length: int = 24) -> str:
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()[:length]


def _latest_feature_path(root: Path) -> Path:
    paths = ProjectPaths(root)
    candidates = sorted(
        paths.feature_data.glob("*_features.parquet"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        raise FileNotFoundError("No feature parquet file found. Run build-features first.")
    return candidates[-1]


def _feature_hash_from_path(path: Path) -> str:
    return str(path.name).split("_")[1] if "_" in path.name else "unknown"


def _latest_feature_panel(root: Path) -> tuple[pd.DataFrame, str]:
    feature_path = _latest_feature_path(root)
    return pd.read_parquet(feature_path), _feature_hash_from_path(feature_path)


def _latest_session(frame: pd.DataFrame) -> str:
    if frame.empty or "Date" not in frame.columns:
        raise ValueError("Feature panel has no completed market sessions")
    return pd.Timestamp(frame["Date"].max()).date().isoformat()


def _row_to_run(row: Any) -> FinalHoldoutRun:
    item = dict(row)
    return FinalHoldoutRun(
        run_id=str(item["run_id"]),
        schema_version=str(item["schema_version"]),
        created_at_utc=str(item["created_at_utc"]),
        creation_git_commit=str(item["creation_git_commit"])
        if item["creation_git_commit"]
        else None,
        baseline_market_date=str(item["baseline_market_date"]),
        first_eligible_future_signal_date=str(item["first_eligible_future_signal_date"])
        if item["first_eligible_future_signal_date"]
        else None,
        universe_snapshot_id=str(item["universe_snapshot_id"]),
        feature_manifest_hash=str(item["feature_manifest_hash"]),
        generation_id=str(item["generation_id"]),
        model_ids=tuple(str(value) for value in cast(list[object], loads(item["model_ids_json"]))),
        scanner_identity_version=int(item["scanner_identity_version"]),
        execution_policy_hash=str(item["execution_policy_hash"]),
        horizon=int(item["horizon"]),
        direction=str(item["direction"]),
        status=cast(RunStatus, str(item["status"])),
        invalidation_reason=str(item["invalidation_reason"])
        if item["invalidation_reason"]
        else None,
        latest_processed_market_date=str(item["latest_processed_market_date"])
        if item["latest_processed_market_date"]
        else None,
        metadata=cast(dict[str, object], loads(str(item["metadata_json"]))),
    )


def _row_to_model(row: Any) -> FinalHoldoutModel:
    item = dict(row)
    return FinalHoldoutModel(
        run_id=str(item["run_id"]),
        model_id=str(item["model_id"]),
        generation_id=str(item["generation_id"]),
        artifact_path=str(item["artifact_path"]),
        artifact_hash=str(item["artifact_hash"]),
        model_state_at_enrollment=str(item["model_state_at_enrollment"]),
        development_gate_eligible=bool(item["development_gate_eligible"]),
        research_only=bool(item["research_only"]),
        selection_policy_hash=str(item["selection_policy_hash"]),
        calibration_governance_hash=str(item["calibration_governance_hash"]),
        ood_governance_hash=str(item["ood_governance_hash"]),
        enrollment_blockers=tuple(
            str(value) for value in cast(list[object], loads(str(item["enrollment_blockers_json"])))
        ),
        metadata=cast(dict[str, object], loads(str(item["metadata_json"]))),
    )


def list_final_holdout_runs(db_path: str | Path) -> tuple[FinalHoldoutRun, ...]:
    with engine_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM final_holdout_runs ORDER BY created_at_utc, run_id"
        ).fetchall()
    return tuple(_row_to_run(row) for row in rows)


def list_final_holdout_models(
    db_path: str | Path, run_id: str | None = None
) -> tuple[FinalHoldoutModel, ...]:
    with engine_connection(db_path) as connection:
        if run_id is None:
            rows = connection.execute(
                "SELECT * FROM final_holdout_models ORDER BY run_id, model_id"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM final_holdout_models WHERE run_id = ? ORDER BY model_id",
                (run_id,),
            ).fetchall()
    return tuple(_row_to_model(row) for row in rows)


def final_holdout_events(db_path: str | Path, run_id: str | None = None) -> pd.DataFrame:
    events = list_forward_events(db_path)
    if events.empty:
        return events
    events = events.loc[events["event_type"].astype(str).str.startswith(FINAL_HOLDOUT_EVENT_PREFIX)]
    if run_id is not None and not events.empty:
        events = events.loc[
            events["payload"].apply(lambda payload: dict(payload).get("run_id") == run_id)
        ]
    return events.reset_index(drop=True)


def _calibration_hash(model: RegisteredModel) -> str:
    return str(model.metrics.get("target_before_stop_calibration_manifest_hash") or "")


def _ood_hash(model: RegisteredModel) -> str:
    payload: dict[str, object] = {
        key: value
        for key, value in sorted(model.metrics.items())
        if "ood" in key or key == "prediction_ood_governance_version"
    }
    return configuration_hash(payload)


def _development_gate_blockers(model: RegisteredModel) -> tuple[str, ...]:
    blockers: list[str] = []
    if model.family == "naive_base_rate":
        blockers.append("naive_control_excluded")
    if model.state in {"RETIRED", "REJECTED"}:
        blockers.append(f"model_state_ineligible:{model.state}")
    artifact_path = Path(model.artifact_path)
    if not artifact_path.exists():
        blockers.append("model_artifact_missing")
    if not model.feature_manifest_hash:
        blockers.append("feature_manifest_missing")
    if not model.metrics.get("selection_policy_configuration_hash"):
        blockers.append("selection_policy_missing")
    if not model.metrics.get("target_before_stop_calibration_governance_schema"):
        blockers.append("target_before_stop_calibration_governance_missing")
    if model.metrics.get("prediction_ood_governance_version") != PREDICTION_OOD_GOVERNANCE_VERSION:
        blockers.append("prediction_ood_governance_v2_missing")
    mandatory = [gate for gate in model.gate_results if gate.mandatory]
    if not mandatory:
        blockers.append("canonical_mandatory_gate_results_missing")
    final_gate_seen = False
    for gate in mandatory:
        if gate.gate_id == FINAL_HOLDOUT_PROMOTION_GATE_ID:
            final_gate_seen = True
            continue
        if gate.status != "PASS":
            blockers.append(f"{gate.gate_id}: {gate.reason}")
    if not final_gate_seen:
        blockers.append(f"{FINAL_HOLDOUT_PROMOTION_GATE_ID}: missing")
    return tuple(blockers)


def _latest_generation(models: list[RegisteredModel]) -> str:
    if not models:
        raise ValueError("No models are registered")
    return max(model.created_at_utc for model in models)


def _select_generation(
    models: list[RegisteredModel], generation: str
) -> tuple[RegisteredModel, ...]:
    generation_id = _latest_generation(models) if generation == "latest" else generation
    selected = tuple(model for model in models if model.created_at_utc == generation_id)
    if not selected:
        raise ValueError(f"No models found for generation: {generation}")
    return selected


def initialize_final_holdout_run(
    root: str | Path,
    *,
    generation: str = "latest",
    research_only: bool = False,
    feature_panel: pd.DataFrame | None = None,
) -> FinalHoldoutEnrollmentReport:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    feature_frame, feature_hash = (
        (feature_panel.copy(), "test-feature-manifest")
        if feature_panel is not None
        else _latest_feature_panel(project_root)
    )
    baseline = _latest_session(feature_frame)
    models = _select_generation(list_models(paths.engine_db), generation)
    blockers_by_model: dict[str, tuple[str, ...]] = {
        model.model_id: _development_gate_blockers(model) for model in models
    }
    eligible = tuple(model for model in models if not blockers_by_model[model.model_id])
    if research_only:
        eligible = tuple(
            model
            for model in models
            if model.family != "naive_base_rate"
            and model.state not in {"RETIRED", "REJECTED"}
            and Path(model.artifact_path).exists()
        )
    if not eligible:
        return FinalHoldoutEnrollmentReport(
            run=None,
            enrolled_models=(),
            blockers_by_model=blockers_by_model,
            message="No models qualified for prospective final-holdout enrollment.",
        )
    created_at = datetime.now(UTC).isoformat()
    generation_id = eligible[0].created_at_utc
    direction_values = sorted({model.direction for model in eligible})
    horizon_values = sorted({model.horizon for model in eligible})
    model_ids = tuple(sorted(model.model_id for model in eligible))
    execution_policy_hash = configuration_hash(
        {
            "mode": SHADOW_FINAL_HOLDOUT_MODE,
            "event_prefix": FINAL_HOLDOUT_EVENT_PREFIX,
            "round_trip_cost_bps": 5.0,
            "entry": "next_completed_session_open",
        }
    )
    run_id = _stable_hash(
        {
            "created_at": created_at,
            "baseline": baseline,
            "generation": generation_id,
            "models": model_ids,
            "research_only": research_only,
        }
    )
    run = FinalHoldoutRun(
        run_id=run_id,
        schema_version=FINAL_HOLDOUT_SCHEMA_VERSION,
        created_at_utc=created_at,
        creation_git_commit=current_commit_hash(project_root),
        baseline_market_date=baseline,
        first_eligible_future_signal_date=None,
        universe_snapshot_id=eligible[0].universe_snapshot_id,
        feature_manifest_hash=feature_hash,
        generation_id=generation_id,
        model_ids=model_ids,
        scanner_identity_version=SCANNER_IDENTITY_SCHEMA_VERSION,
        execution_policy_hash=execution_policy_hash,
        horizon=horizon_values[0],
        direction="mixed" if len(direction_values) > 1 else direction_values[0],
        status="CREATED",
        invalidation_reason=None,
        latest_processed_market_date=None,
        metadata={
            "research_only": research_only,
            "baseline_rule": "latest completed local feature session at enrollment",
            "no_backfill_rule": "as_of_date must be greater than baseline_market_date",
            "label": "Prospective shadow validation. Not a live trade recommendation.",
        },
    )
    enrolled: list[FinalHoldoutModel] = []
    with engine_connection(paths.engine_db) as connection:
        connection.execute(
            """
            INSERT INTO final_holdout_runs (
                run_id, schema_version, created_at_utc, creation_git_commit,
                baseline_market_date, first_eligible_future_signal_date, universe_snapshot_id,
                feature_manifest_hash, generation_id, model_ids_json, scanner_identity_version,
                execution_policy_hash, horizon, direction, status, invalidation_reason,
                latest_processed_market_date, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.schema_version,
                run.created_at_utc,
                run.creation_git_commit,
                run.baseline_market_date,
                run.first_eligible_future_signal_date,
                run.universe_snapshot_id,
                run.feature_manifest_hash,
                run.generation_id,
                dumps(run.model_ids),
                run.scanner_identity_version,
                run.execution_policy_hash,
                run.horizon,
                run.direction,
                run.status,
                run.invalidation_reason,
                run.latest_processed_market_date,
                dumps(run.metadata),
            ),
        )
        for model in eligible:
            artifact_hash = hash_file(model.artifact_path)
            item = FinalHoldoutModel(
                run_id=run_id,
                model_id=model.model_id,
                generation_id=model.created_at_utc,
                artifact_path=model.artifact_path,
                artifact_hash=artifact_hash,
                model_state_at_enrollment=model.state,
                development_gate_eligible=not blockers_by_model[model.model_id],
                research_only=research_only,
                selection_policy_hash=str(
                    model.metrics.get("selection_policy_configuration_hash") or ""
                ),
                calibration_governance_hash=_calibration_hash(model),
                ood_governance_hash=_ood_hash(model),
                enrollment_blockers=blockers_by_model[model.model_id],
                metadata={"family": model.family, "direction": model.direction},
            )
            enrolled.append(item)
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
                    item.run_id,
                    item.model_id,
                    item.generation_id,
                    item.artifact_path,
                    item.artifact_hash,
                    item.model_state_at_enrollment,
                    int(item.development_gate_eligible),
                    int(item.research_only),
                    item.selection_policy_hash,
                    item.calibration_governance_hash,
                    item.ood_governance_hash,
                    dumps(item.enrollment_blockers),
                    dumps(item.metadata),
                ),
            )
    return FinalHoldoutEnrollmentReport(
        run=run,
        enrolled_models=tuple(enrolled),
        blockers_by_model=blockers_by_model,
        message=f"Created prospective final-holdout run {run_id}.",
    )


def _active_runs(db_path: str | Path) -> tuple[FinalHoldoutRun, ...]:
    return tuple(
        run
        for run in list_final_holdout_runs(db_path)
        if run.status in {"CREATED", "COLLECTING", "READY_FOR_EVALUATION"}
    )


def _feature_frame_session_rows(feature_frame: pd.DataFrame, session: str) -> pd.DataFrame:
    return feature_frame.loc[pd.to_datetime(feature_frame["Date"]) == pd.Timestamp(session)]


def _manifest_session_availability(
    root: Path,
    rows: pd.DataFrame,
    session: str,
    run: FinalHoldoutRun,
) -> tuple[bool, str]:
    if "symbol" not in rows.columns:
        return False, "FINAL_HOLDOUT_BACKFILL_BLOCKED: missing symbol provenance key"
    manifest_dir = ProjectPaths(root).manifests
    symbols = sorted({str(symbol).upper() for symbol in rows["symbol"].dropna().unique()})
    if not symbols:
        return False, "FINAL_HOLDOUT_BACKFILL_BLOCKED: no symbols in feature session"
    created_at = pd.Timestamp(run.created_at_utc)
    for symbol in symbols:
        path = manifest_dir / f"{symbol}.json"
        if not path.exists():
            return False, f"FINAL_HOLDOUT_BACKFILL_BLOCKED: missing manifest for {symbol}"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False, f"FINAL_HOLDOUT_BACKFILL_BLOCKED: invalid manifest for {symbol}"
        retrieved = pd.to_datetime(payload.get("retrieval_timestamp_utc"), errors="coerce")
        actual_last = payload.get("actual_last_date")
        if pd.isna(retrieved) or actual_last is None:
            return False, f"FINAL_HOLDOUT_BACKFILL_BLOCKED: incomplete manifest for {symbol}"
        if pd.Timestamp(str(actual_last)).date().isoformat() < session:
            return False, f"FINAL_HOLDOUT_BACKFILL_BLOCKED: manifest does not cover {symbol}"
        if not bool(pd.Timestamp(retrieved) > created_at):
            return (
                False,
                f"FINAL_HOLDOUT_BACKFILL_BLOCKED: {symbol} manifest predates run creation",
            )
    return True, "ok"


def _session_availability(
    root: Path,
    feature_frame: pd.DataFrame,
    session: str,
    run: FinalHoldoutRun,
) -> tuple[bool, str]:
    rows = _feature_frame_session_rows(feature_frame, session)
    if rows.empty:
        return False, "FINAL_HOLDOUT_BACKFILL_BLOCKED: no feature rows for session"
    if "local_available_at_utc" not in feature_frame.columns:
        return _manifest_session_availability(root, rows, session, run)
    values = pd.to_datetime(rows["local_available_at_utc"], errors="coerce")
    if values.isna().any():
        return False, "FINAL_HOLDOUT_BACKFILL_BLOCKED: incomplete ingestion provenance"
    if not bool((values > pd.Timestamp(run.created_at_utc)).all()):
        return (
            False,
            "FINAL_HOLDOUT_BACKFILL_BLOCKED: session was locally available before run creation",
        )
    return True, "ok"


def _load_local_frames(root: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for path in ProjectPaths(root).raw_data.glob("*.csv"):
        frames[path.stem.upper()] = load_ohlcv_csv(path)
    return frames


def _append_run_event(
    db_path: str | Path,
    *,
    run: FinalHoldoutRun,
    event_type: str,
    market_as_of_date: str,
    reason: str,
    unique_suffix: str,
) -> int:
    event = append_forward_event(
        db_path,
        event_type=event_type,
        market_as_of_date=market_as_of_date,
        ticker="RUN",
        direction="n/a",
        model_id="run",
        scanner_snapshot_id=None,
        feature_snapshot_hash=run.feature_manifest_hash,
        payload={
            "run_id": run.run_id,
            "mode": SHADOW_FINAL_HOLDOUT_MODE,
            "reason": reason,
        },
        unique_suffix=f"{run.run_id}|{unique_suffix}",
    )
    return int(event.inserted)


def _verify_frozen_models(
    db_path: str | Path, run: FinalHoldoutRun
) -> tuple[bool, str, tuple[RegisteredModel, ...], tuple[FinalHoldoutModel, ...]]:
    enrolled = list_final_holdout_models(db_path, run.run_id)
    current = {model.model_id: model for model in list_models(db_path)}
    selected: list[RegisteredModel] = []
    for frozen in enrolled:
        model = current.get(frozen.model_id)
        if model is None:
            return False, f"enrolled model missing from registry: {frozen.model_id}", (), enrolled
        if not Path(frozen.artifact_path).exists():
            return False, f"artifact missing: {frozen.model_id}", (), enrolled
        if hash_file(frozen.artifact_path) != frozen.artifact_hash:
            return False, f"artifact hash changed: {frozen.model_id}", (), enrolled
        if str(model.metrics.get("selection_policy_configuration_hash") or "") != (
            frozen.selection_policy_hash
        ):
            return False, f"selection policy hash changed: {frozen.model_id}", (), enrolled
        if _calibration_hash(model) != frozen.calibration_governance_hash:
            return False, f"calibration governance hash changed: {frozen.model_id}", (), enrolled
        if _ood_hash(model) != frozen.ood_governance_hash:
            return False, f"OOD governance hash changed: {frozen.model_id}", (), enrolled
        selected.append(model)
    return True, "ok", tuple(selected), enrolled


def _truncate_frames(frames: dict[str, pd.DataFrame], session: str) -> dict[str, pd.DataFrame]:
    cutoff = pd.Timestamp(session)
    return {
        symbol: frame.loc[frame.index <= cutoff].copy()
        for symbol, frame in frames.items()
        if not frame.loc[frame.index <= cutoff].empty
    }


def process_final_holdout_update(
    root: str | Path,
    *,
    feature_panel: pd.DataFrame | None = None,
    frames: dict[str, pd.DataFrame] | None = None,
) -> FinalHoldoutUpdateResult:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    feature_frame, feature_hash = (
        (feature_panel.copy(), "test-feature-manifest")
        if feature_panel is not None
        else _latest_feature_panel(project_root)
    )
    frames = frames if frames is not None else _load_local_frames(project_root)
    processed: list[str] = []
    blocked: dict[str, str] = {}
    reports: list[Path] = []
    inserted = 0
    for run in _active_runs(paths.engine_db):
        dates = sorted(
            pd.Timestamp(value).date().isoformat() for value in feature_frame["Date"].unique()
        )
        candidates = [
            value
            for value in dates
            if value > run.baseline_market_date
            and (
                run.latest_processed_market_date is None or value > run.latest_processed_market_date
            )
        ]
        for session in candidates:
            available, reason = _session_availability(project_root, feature_frame, session, run)
            if not available:
                blocked[session] = reason
                inserted += _append_run_event(
                    paths.engine_db,
                    run=run,
                    event_type="FINAL_HOLDOUT_DATA_INVALIDATED",
                    market_as_of_date=session,
                    reason=reason,
                    unique_suffix=session,
                )
                continue
            ok, drift_reason, models, _ = _verify_frozen_models(paths.engine_db, run)
            if not ok:
                blocked[session] = drift_reason
                inserted += _append_run_event(
                    paths.engine_db,
                    run=run,
                    event_type="FINAL_HOLDOUT_DATA_INVALIDATED",
                    market_as_of_date=session,
                    reason=drift_reason,
                    unique_suffix=f"{session}|frozen_integrity",
                )
                with engine_connection(paths.engine_db) as connection:
                    connection.execute(
                        """
                        UPDATE final_holdout_runs
                        SET status = 'INVALIDATED', invalidation_reason = ?
                        WHERE run_id = ?
                        """,
                        (drift_reason, run.run_id),
                    )
                continue
            bounded_features = feature_frame.loc[
                pd.to_datetime(feature_frame["Date"]) <= pd.Timestamp(session)
            ].copy()
            bounded_frames = _truncate_frames(frames, session)
            inserted += advance_forward_positions(
                paths.engine_db,
                bounded_frames,
                event_prefix=FINAL_HOLDOUT_EVENT_PREFIX,
            )
            bundles = tuple(load_model_bundle(model.artifact_path) for model in models)
            snapshot = run_scanner(
                bounded_features,
                bundles=bundles,
                db_path=paths.engine_db,
                output_dir=paths.scanner_artifacts / "final_holdout",
                universe_snapshot_id=run.universe_snapshot_id,
                model_states={model.model_id: "CHALLENGER" for model in models},
                model_eligibility={model.model_id: True for model in models},
                feature_manifest_hash=feature_hash,
                model_artifact_hashes={
                    model.model_id: hash_file(model.artifact_path) for model in models
                },
                model_generation_ids={model.model_id: model.created_at_utc for model in models},
                model_state_mode=SHADOW_FINAL_HOLDOUT_MODE,
                include_challengers=True,
                include_candidates=True,
                config=ScannerConfig(),
            )
            inserted += create_pending_events_from_snapshot(
                paths.engine_db,
                snapshot.rows,
                event_prefix=FINAL_HOLDOUT_EVENT_PREFIX,
                payload_extra={
                    "run_id": run.run_id,
                    "generation_id": run.generation_id,
                    "mode": SHADOW_FINAL_HOLDOUT_MODE,
                    "not_live_trade_recommendation": True,
                },
                include_row_payload=True,
            )
            status: RunStatus = "COLLECTING"
            with engine_connection(paths.engine_db) as connection:
                connection.execute(
                    """
                    UPDATE final_holdout_runs
                    SET status = ?, latest_processed_market_date = ?,
                        first_eligible_future_signal_date = COALESCE(first_eligible_future_signal_date, ?)
                    WHERE run_id = ?
                    """,
                    (status, session, session, run.run_id),
                )
            report_path = paths.reports / "final_holdout" / f"{run.run_id}_{session}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            if not report_path.exists():
                report_path.write_text(
                    json.dumps(
                        {
                            "run_id": run.run_id,
                            "session": session,
                            "scan_id": snapshot.scan_id,
                            "rows": len(snapshot.rows),
                            "created_at_utc": datetime.now(UTC).isoformat(),
                            "label": "Prospective shadow validation. Not a live trade recommendation.",
                        },
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
            reports.append(report_path)
            processed.append(session)
    return FinalHoldoutUpdateResult(
        processed_sessions=tuple(processed),
        blocked_sessions=blocked,
        events_inserted=inserted,
        reports=tuple(reports),
    )


def reconstruct_final_holdout_state(db_path: str | Path, run_id: str) -> pd.DataFrame:
    events = final_holdout_events(db_path, run_id)
    if events.empty:
        return pd.DataFrame()
    rows: dict[str, dict[str, object]] = {}
    for _, event in events.iterrows():
        payload = dict(event["payload"])
        source = str(payload.get("source_pending_event_id", event["event_id"]))
        key = "|".join(
            [
                str(event["ticker"]),
                str(event["direction"]),
                str(event["model_id"]),
                str(event["scanner_snapshot_id"]),
                source,
            ]
        )
        rows.setdefault(
            key,
            {
                "run_id": run_id,
                "ticker": event["ticker"],
                "direction": event["direction"],
                "model_id": event["model_id"],
                "scanner_snapshot_id": event["scanner_snapshot_id"],
            },
        )
        rows[key]["status"] = str(event["event_type"]).replace(FINAL_HOLDOUT_EVENT_PREFIX, "")
        rows[key].update(payload)
    return pd.DataFrame(rows.values())


def _final_gate(
    gate_id: str,
    name: str,
    metric_name: str,
    threshold: object,
    comparator: str,
    actual: object,
    status: str,
    reason: str,
    config_hash: str,
) -> GateResult:
    return make_gate(
        gate_id=gate_id,
        gate_name=name,
        category="final holdout",
        scope="prospective_shadow_validation",
        metric_name=metric_name,
        threshold=cast(str | float | int | bool | None, threshold),
        comparator=comparator,
        actual_value=cast(str | float | int | bool | None, actual),
        status=cast(Literal["PASS", "FAIL", "NOT_APPLICABLE", "NOT_CONFIGURED"], status),
        mandatory=True,
        evidence_source=FINAL_HOLDOUT_SCHEMA_VERSION,
        reason=reason,
        configuration_hash_value=config_hash,
    )


def evaluate_final_holdout_run(
    root: str | Path,
    *,
    run_id: str,
    minimum_matured_outcomes: int | None = None,
) -> FinalHoldoutEvaluationResult:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    runs = {run.run_id: run for run in list_final_holdout_runs(paths.engine_db)}
    run = runs.get(run_id)
    if run is None:
        raise ValueError(f"Unknown final-holdout run: {run_id}")
    models = list_final_holdout_models(paths.engine_db, run_id)
    events = final_holdout_events(paths.engine_db, run_id)
    metrics_by_model: dict[str, dict[str, object]] = {}
    gates_by_model: dict[str, tuple[GateResult, ...]] = {}
    manifest_by_model: dict[str, str] = {}
    current_models = {model.model_id: model for model in list_models(paths.engine_db)}
    invalidated = bool(
        not events.empty and (events["event_type"] == "FINAL_HOLDOUT_DATA_INVALIDATED").any()
    )
    config_hash = configuration_hash(
        {
            "schema": FINAL_HOLDOUT_SCHEMA_VERSION,
            "minimum_matured_outcomes": minimum_matured_outcomes,
        }
    )
    all_pass = True
    for enrolled in models:
        model_events = (
            events.loc[events["model_id"] == enrolled.model_id] if not events.empty else events
        )
        exits = (
            model_events.loc[model_events["event_type"] == "FINAL_HOLDOUT_EXIT_FILLED"]
            if not model_events.empty
            else model_events
        )
        matured = len(exits)
        returns = (
            [
                float(dict(payload).get("net_realized_return", 0.0))
                for payload in exits["payload"].tolist()
            ]
            if not exits.empty
            else []
        )
        evidence_manifest = _stable_hash(
            {
                "run_id": run_id,
                "model_id": enrolled.model_id,
                "events": model_events["event_id"].tolist() if not model_events.empty else [],
                "matured": matured,
                "returns": returns,
            },
            length=16,
        )
        sample_status = (
            "NOT_CONFIGURED"
            if minimum_matured_outcomes is None
            else ("PASS" if matured >= minimum_matured_outcomes else "FAIL")
        )
        final_gates: tuple[GateResult, ...] = (
            make_gate(
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
                evidence_source=FINAL_HOLDOUT_SCHEMA_VERSION,
                reason="Prospective final-holdout evaluation completed for this model.",
                configuration_hash_value=config_hash,
            ),
            _final_gate(
                "final_holdout_provenance_valid",
                "Final Holdout Provenance Valid",
                "final_holdout_backfill_events",
                0,
                "==",
                int(invalidated),
                "FAIL" if invalidated else "PASS",
                "Prospective provenance passed; zero blocked backfill events were observed."
                if not invalidated
                else "At least one backfill or invalidation event exists.",
                config_hash,
            ),
            _final_gate(
                "final_holdout_sample_threshold_configured",
                "Final Holdout Sample Threshold Configured",
                "matured_outcomes",
                minimum_matured_outcomes if minimum_matured_outcomes is not None else "configured",
                ">=",
                matured,
                sample_status,
                "Final-holdout minimum matured-outcome threshold is not configured."
                if minimum_matured_outcomes is None
                else "Matured outcomes meet the configured minimum."
                if matured >= minimum_matured_outcomes
                else "Matured outcomes are below the configured minimum.",
                config_hash,
            ),
        )
        if enrolled.research_only:
            final_gates = (
                *final_gates,
                _final_gate(
                    "final_holdout_research_only_not_promotable",
                    "Research-Only Enrollment Not Promotable",
                    "research_only",
                    False,
                    "is false",
                    True,
                    "FAIL",
                    "Research-only final-holdout runs cannot satisfy promotion.",
                    config_hash,
                ),
            )
        metrics = {
            "holdout_status": FINAL_HOLDOUT_STATUS,
            "final_holdout_run_id": run_id,
            "final_holdout_evidence_manifest_hash": evidence_manifest,
            "final_holdout_matured_outcomes": matured,
            "final_holdout_mean_net_return": (
                float(pd.Series(returns).mean()) if returns else GATE_VALUE_NOT_AVAILABLE
            ),
            "final_holdout_schema_version": FINAL_HOLDOUT_SCHEMA_VERSION,
        }
        metrics_by_model[enrolled.model_id] = metrics
        gates_by_model[enrolled.model_id] = final_gates
        manifest_by_model[enrolled.model_id] = evidence_manifest
        if not promotion_eligibility(final_gates).eligible:
            all_pass = False
        model = current_models.get(enrolled.model_id)
        if model is not None:
            updated_metrics = {**model.metrics, **metrics}
            existing = [
                gate
                for gate in model.gate_results
                if gate.gate_id != FINAL_HOLDOUT_PROMOTION_GATE_ID
            ]
            updated_gates = tuple(existing) + final_gates
            with engine_connection(paths.engine_db) as connection:
                connection.execute(
                    """
                    UPDATE models
                    SET metrics_json = ?, gate_results_json = ?, quality_gates_json = ?
                    WHERE model_id = ?
                    """,
                    (
                        dumps(updated_metrics),
                        dumps(gate_results_to_jsonable(updated_gates)),
                        dumps(quality_gate_bool_map(updated_gates)),
                        enrolled.model_id,
                    ),
                )
                model_meta = {**enrolled.metadata, "final_holdout_metrics": metrics}
                connection.execute(
                    """
                    UPDATE final_holdout_models
                    SET metadata_json = ?
                    WHERE run_id = ? AND model_id = ?
                    """,
                    (dumps(model_meta), run_id, enrolled.model_id),
                )
    status: RunStatus = "EVALUATED_PASS" if all_pass else "EVALUATED_FAIL"
    with engine_connection(paths.engine_db) as connection:
        connection.execute(
            "UPDATE final_holdout_runs SET status = ? WHERE run_id = ?",
            (status, run_id),
        )
    append_forward_event(
        paths.engine_db,
        event_type="FINAL_HOLDOUT_EVALUATED",
        market_as_of_date=run.latest_processed_market_date or run.baseline_market_date,
        ticker="RUN",
        direction="n/a",
        model_id="run",
        scanner_snapshot_id=None,
        feature_snapshot_hash=run.feature_manifest_hash,
        payload={
            "run_id": run_id,
            "mode": SHADOW_FINAL_HOLDOUT_MODE,
            "status": status,
            "evidence_manifest_hashes": manifest_by_model,
        },
        unique_suffix=run_id,
    )
    return FinalHoldoutEvaluationResult(
        run_id=run_id,
        status=status,
        metrics_by_model=metrics_by_model,
        gates_by_model=gates_by_model,
        evidence_manifest_hashes=manifest_by_model,
    )


def final_holdout_status_frame(root: str | Path) -> pd.DataFrame:
    paths = ProjectPaths(Path(root))
    rows: list[dict[str, object]] = []
    events = final_holdout_events(paths.engine_db)
    for run in list_final_holdout_runs(paths.engine_db):
        current_run_id = run.run_id
        run_events = (
            events.loc[
                events["payload"].apply(
                    lambda payload, run_id=current_run_id: dict(payload).get("run_id") == run_id
                )
            ]
            if not events.empty
            else events
        )
        models = list_final_holdout_models(paths.engine_db, run.run_id)
        rows.append(
            {
                "run_id": run.run_id,
                "status": run.status,
                "baseline_market_date": run.baseline_market_date,
                "first_eligible_future_signal_date": run.first_eligible_future_signal_date,
                "latest_processed_market_date": run.latest_processed_market_date,
                "model_count": len(models),
                "event_count": len(run_events),
                "signals": int((run_events["event_type"] == "FINAL_HOLDOUT_SIGNAL_CREATED").sum())
                if not run_events.empty
                else 0,
                "rejected_signals": int(
                    (run_events["event_type"] == "FINAL_HOLDOUT_SIGNAL_REJECTED").sum()
                )
                if not run_events.empty
                else 0,
                "backfill_blocked_events": int(
                    (run_events["event_type"] == "FINAL_HOLDOUT_DATA_INVALIDATED").sum()
                )
                if not run_events.empty
                else 0,
                "label": "Prospective shadow validation. Not a live trade recommendation.",
            }
        )
    return pd.DataFrame(rows)
