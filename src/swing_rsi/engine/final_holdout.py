from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from swing_rsi.config import ProjectPaths, load_yaml
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
FINAL_HOLDOUT_SAMPLE_POLICY_VERSION = "prospective_final_holdout_sample_v1"
SHADOW_FINAL_HOLDOUT_MODE = "SHADOW_FINAL_HOLDOUT"
FINAL_HOLDOUT_EVENT_PREFIX = "FINAL_HOLDOUT_"
PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION = "path_metric_magnitude_domain_v1"
PATH_HEAD_CAPABILITY_ACTIVE = "ACTIVE"
PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR = "RETIRED_UNSUITABLE_ESTIMATOR"

RunStatus = Literal[
    "CREATED",
    "COLLECTING",
    "EARLY_DIAGNOSTIC_AVAILABLE",
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
    sample_policy_version: str
    sample_policy_hash: str
    sample_policy: dict[str, object]
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


@dataclass(frozen=True)
class FinalHoldoutSamplePolicy:
    schema_version: str = FINAL_HOLDOUT_SAMPLE_POLICY_VERSION
    matured_outcomes_minimum: int = 100
    distinct_signal_dates_minimum: int = 60
    observation_sessions_minimum: int = 126
    calendar_months_minimum: int = 4
    positive_class_minimum: int = 20
    negative_class_minimum: int = 20
    early_diagnostic_matured_outcomes_minimum: int = 30
    early_diagnostic_distinct_signal_dates_minimum: int = 20

    def normalized(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "matured_outcomes_minimum": self.matured_outcomes_minimum,
            "distinct_signal_dates_minimum": self.distinct_signal_dates_minimum,
            "observation_sessions_minimum": self.observation_sessions_minimum,
            "calendar_months_minimum": self.calendar_months_minimum,
            "positive_class_minimum": self.positive_class_minimum,
            "negative_class_minimum": self.negative_class_minimum,
            "early_diagnostic_matured_outcomes_minimum": (
                self.early_diagnostic_matured_outcomes_minimum
            ),
            "early_diagnostic_distinct_signal_dates_minimum": (
                self.early_diagnostic_distinct_signal_dates_minimum
            ),
        }

    @property
    def policy_hash(self) -> str:
        return configuration_hash(self.normalized())


@dataclass(frozen=True)
class FinalHoldoutSampleState:
    run_id: str
    model_id: str
    status: str
    matured_outcomes: int
    distinct_signal_dates: int
    observation_sessions: int
    calendar_months: int
    positive_outcomes: int
    negative_outcomes: int
    pending_entries: int
    open_positions: int
    provenance_failures: int
    blocked_backfills: int
    invalidated_outcomes: int
    artifact_integrity_passed: bool
    artifact_integrity_reason: str
    sample_sufficient: bool
    early_diagnostic_available: bool
    estimated_remaining_requirement: str
    gates: tuple[GateResult, ...]


def _stable_hash(value: object, *, length: int = 24) -> str:
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()[:length]


def _sample_policy_path(root: Path) -> Path:
    return root / "configs" / "governance" / "prospective_final_holdout_v1.yaml"


def load_final_holdout_sample_policy(root: str | Path) -> FinalHoldoutSamplePolicy:
    path = _sample_policy_path(Path(root))
    if not path.exists():
        path = _sample_policy_path(Path(__file__).resolve().parents[3])
    values = load_yaml(path)
    schema_version = str(values.get("schema_version", FINAL_HOLDOUT_SAMPLE_POLICY_VERSION))
    if schema_version != FINAL_HOLDOUT_SAMPLE_POLICY_VERSION:
        raise ValueError(f"Unsupported prospective final-holdout sample policy: {schema_version}")
    return FinalHoldoutSamplePolicy(
        schema_version=schema_version,
        matured_outcomes_minimum=int(values.get("matured_outcomes_minimum", 100)),
        distinct_signal_dates_minimum=int(values.get("distinct_signal_dates_minimum", 60)),
        observation_sessions_minimum=int(values.get("observation_sessions_minimum", 126)),
        calendar_months_minimum=int(values.get("calendar_months_minimum", 4)),
        positive_class_minimum=int(values.get("positive_class_minimum", 20)),
        negative_class_minimum=int(values.get("negative_class_minimum", 20)),
        early_diagnostic_matured_outcomes_minimum=int(
            values.get("early_diagnostic_matured_outcomes_minimum", 30)
        ),
        early_diagnostic_distinct_signal_dates_minimum=int(
            values.get("early_diagnostic_distinct_signal_dates_minimum", 20)
        ),
    )


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
        sample_policy_version=str(item["sample_policy_version"]),
        sample_policy_hash=str(item["sample_policy_hash"]),
        sample_policy=cast(dict[str, object], loads(str(item["sample_policy_json"]))),
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


def _calibrator_artifact_hash(model: RegisteredModel) -> str:
    return str(model.metrics.get("target_before_stop_calibrator_artifact_hash") or "")


def _ood_hash(model: RegisteredModel) -> str:
    payload: dict[str, object] = {
        key: value
        for key, value in sorted(model.metrics.items())
        if "ood" in key or key == "prediction_ood_governance_version"
    }
    return configuration_hash(payload)


def _execution_policy_hash() -> str:
    return configuration_hash(
        {
            "mode": SHADOW_FINAL_HOLDOUT_MODE,
            "event_prefix": FINAL_HOLDOUT_EVENT_PREFIX,
            "round_trip_cost_bps": 5.0,
            "entry": "next_completed_session_open",
        }
    )


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
    for prefix in ("mfe", "mae"):
        capability_state = str(model.metrics.get(f"{prefix}_path_head_capability_state") or "")
        if capability_state == PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR:
            blockers.append(f"{prefix}_path_head_retired_unsuitable_estimator")
            continue
        if capability_state != PATH_HEAD_CAPABILITY_ACTIVE:
            blockers.append(f"{prefix}_path_head_capability_state_missing")
        if model.metrics.get(f"{prefix}_domain_schema_version") != (
            PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
        ):
            blockers.append(f"{prefix}_domain_metadata_missing")
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
    sample_policy = load_final_holdout_sample_policy(project_root)
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
    execution_policy_hash = _execution_policy_hash()
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
        sample_policy_version=sample_policy.schema_version,
        sample_policy_hash=sample_policy.policy_hash,
        sample_policy=sample_policy.normalized(),
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
                execution_policy_hash, sample_policy_version, sample_policy_hash,
                sample_policy_json, horizon, direction, status, invalidation_reason,
                latest_processed_market_date, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                run.sample_policy_version,
                run.sample_policy_hash,
                dumps(run.sample_policy),
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
                metadata={
                    "family": model.family,
                    "direction": model.direction,
                    "feature_manifest_hash": model.feature_manifest_hash,
                    "calibrator_artifact_hash": _calibrator_artifact_hash(model),
                    "code_commit_hash": model.code_commit_hash,
                    "execution_policy_hash": execution_policy_hash,
                },
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
        if run.status
        in {"CREATED", "COLLECTING", "EARLY_DIAGNOSTIC_AVAILABLE", "READY_FOR_EVALUATION"}
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


def _sample_policy_from_run(run: FinalHoldoutRun) -> FinalHoldoutSamplePolicy:
    def policy_int(key: str, default: int) -> int:
        return int(str(run.sample_policy.get(key, default)))

    if run.sample_policy:
        return FinalHoldoutSamplePolicy(
            schema_version=str(
                run.sample_policy.get("schema_version", FINAL_HOLDOUT_SAMPLE_POLICY_VERSION)
            ),
            matured_outcomes_minimum=policy_int("matured_outcomes_minimum", 100),
            distinct_signal_dates_minimum=policy_int("distinct_signal_dates_minimum", 60),
            observation_sessions_minimum=policy_int("observation_sessions_minimum", 126),
            calendar_months_minimum=policy_int("calendar_months_minimum", 4),
            positive_class_minimum=policy_int("positive_class_minimum", 20),
            negative_class_minimum=policy_int("negative_class_minimum", 20),
            early_diagnostic_matured_outcomes_minimum=policy_int(
                "early_diagnostic_matured_outcomes_minimum",
                30,
            ),
            early_diagnostic_distinct_signal_dates_minimum=policy_int(
                "early_diagnostic_distinct_signal_dates_minimum",
                20,
            ),
        )
    return FinalHoldoutSamplePolicy()


def _sample_gate(
    gate_id: str,
    name: str,
    metric_name: str,
    threshold: object,
    comparator: str,
    actual: object,
    status: str,
    reason: str,
    policy: FinalHoldoutSamplePolicy,
) -> GateResult:
    return make_gate(
        gate_id=gate_id,
        gate_name=name,
        category="final holdout sample governance",
        scope="prospective_shadow_validation",
        metric_name=metric_name,
        threshold=cast(str | float | int | bool | None, threshold),
        comparator=comparator,
        actual_value=cast(str | float | int | bool | None, actual),
        status=cast(Literal["PASS", "FAIL", "NOT_APPLICABLE", "NOT_CONFIGURED"], status),
        mandatory=True,
        evidence_source=policy.schema_version,
        reason=f"{reason} Policy version: {policy.schema_version}.",
        configuration_hash_value=policy.policy_hash,
    )


def _pass_fail(value: int, threshold: int) -> str:
    return "PASS" if value >= threshold else "FAIL"


def _threshold_reason(label: str, value: int, threshold: int) -> str:
    if value >= threshold:
        return f"{label} {value} meets the minimum {threshold}."
    return f"{label} {value} is below the minimum {threshold}."


def _processed_sessions(run: FinalHoldoutRun, events: pd.DataFrame) -> tuple[str, ...]:
    raw = run.metadata.get("processed_sessions")
    if isinstance(raw, list):
        values = tuple(sorted({str(value) for value in raw}))
        if values:
            return values
    if events.empty:
        return ()
    observed = events.loc[
        events["event_type"].isin({"FINAL_HOLDOUT_SIGNAL_CREATED", "FINAL_HOLDOUT_SIGNAL_REJECTED"})
    ]
    return tuple(sorted({str(value) for value in observed["market_as_of_date"].tolist()}))


def _target_before_stop_class(exit_reason: str) -> int:
    return 1 if exit_reason == "target" else 0


def _event_payloads_by_id(events: pd.DataFrame, event_type: str) -> dict[str, dict[str, object]]:
    if events.empty:
        return {}
    rows = events.loc[events["event_type"] == event_type]
    return {str(row["event_id"]): dict(row["payload"]) for _, row in rows.iterrows()}


def _matured_exit_rows(events: pd.DataFrame, model_id: str) -> pd.DataFrame:
    if events.empty:
        return events
    return events.loc[
        (events["model_id"] == model_id) & (events["event_type"] == "FINAL_HOLDOUT_EXIT_FILLED")
    ].copy()


def _estimate_remaining(deficits: dict[str, int]) -> str:
    pending = {name: value for name, value in deficits.items() if value > 0}
    if not pending:
        return "ready"
    return "; ".join(f"{name}:{value}" for name, value in sorted(pending.items()))


def _sample_state_for_model(
    root: str | Path,
    run: FinalHoldoutRun,
    enrolled: FinalHoldoutModel,
    events: pd.DataFrame,
    policy: FinalHoldoutSamplePolicy,
) -> FinalHoldoutSampleState:
    run_events = (
        events.loc[
            events["payload"].apply(lambda payload: dict(payload).get("run_id") == run.run_id)
        ]
        if not events.empty
        else events
    )
    model_events = (
        run_events.loc[run_events["model_id"] == enrolled.model_id]
        if not run_events.empty
        else run_events
    )
    pending_payloads = _event_payloads_by_id(model_events, "FINAL_HOLDOUT_ENTRY_PENDING")
    filled_payloads = _event_payloads_by_id(model_events, "FINAL_HOLDOUT_ENTRY_FILLED")
    filled_source_ids = {
        str(dict(payload).get("source_pending_event_id"))
        for payload in filled_payloads.values()
        if dict(payload).get("source_pending_event_id")
    }
    exit_rows = _matured_exit_rows(run_events, enrolled.model_id)
    invalidated = (
        run_events.loc[run_events["event_type"] == "FINAL_HOLDOUT_DATA_INVALIDATED"]
        if not run_events.empty
        else run_events
    )
    invalidated_source_ids = (
        {
            str(dict(payload).get("source_pending_event_id"))
            for payload in invalidated["payload"].tolist()
            if dict(payload).get("source_pending_event_id")
        }
        if not invalidated.empty
        else set()
    )
    valid_exits: list[dict[str, object]] = []
    provenance_failures = 0
    for _, row in exit_rows.iterrows():
        payload = dict(row["payload"])
        source_id = str(payload.get("source_pending_event_id", ""))
        if not source_id or source_id in invalidated_source_ids:
            continue
        pending_payload = pending_payloads.get(source_id, {})
        required_fields = (
            "entry_date",
            "exit_date",
            "exit_reason",
            "mfe",
            "mae",
            "realized_return",
        )
        if not all(field in payload for field in required_fields):
            continue
        if source_id not in filled_source_ids:
            continue
        if pending_payload.get("prospective_provenance_valid") is not True:
            provenance_failures += 1
        valid_exits.append(payload)
    matured = len(valid_exits)
    signal_dates = {
        str(payload.get("signal_as_of_date"))
        for payload in valid_exits
        if payload.get("signal_as_of_date")
    }
    months = {
        pd.Timestamp(str(payload.get("exit_date"))).strftime("%Y-%m")
        for payload in valid_exits
        if payload.get("exit_date")
    }
    classes = [
        _target_before_stop_class(str(payload.get("exit_reason", ""))) for payload in valid_exits
    ]
    positive = sum(classes)
    negative = len(classes) - positive
    processed_sessions = _processed_sessions(run, run_events)
    pending_entries = len(
        set(pending_payloads)
        - {
            str(dict(payload).get("source_pending_event_id"))
            for payload in filled_payloads.values()
            if dict(payload).get("source_pending_event_id")
        }
    )
    exit_source_ids = {
        str(payload.get("source_pending_event_id"))
        for payload in valid_exits
        if payload.get("source_pending_event_id")
    }
    open_positions = len(
        {
            str(dict(payload).get("source_pending_event_id"))
            for payload in filled_payloads.values()
            if dict(payload).get("source_pending_event_id")
        }
        - exit_source_ids
    )
    blocked_backfills = (
        int(
            invalidated["payload"]
            .apply(
                lambda payload: (
                    "FINAL_HOLDOUT_BACKFILL_BLOCKED" in str(dict(payload).get("reason", ""))
                )
            )
            .sum()
        )
        if not invalidated.empty
        else 0
    )
    invalidated_outcomes = (
        len(invalidated_source_ids) if invalidated_source_ids else len(invalidated)
    )
    ok, artifact_reason, _, _ = _verify_frozen_models(root, ProjectPaths(Path(root)).engine_db, run)
    policy_configured = (
        run.sample_policy_version == policy.schema_version
        and run.sample_policy_hash == policy.policy_hash
    )
    gates: list[GateResult] = [
        _sample_gate(
            "final_holdout_policy_configured",
            "Final Holdout Policy Configured",
            "sample_policy_hash",
            policy.policy_hash,
            "equals",
            run.sample_policy_hash,
            "PASS" if policy_configured else "FAIL",
            "Frozen sample policy matches the configured schema and hash."
            if policy_configured
            else "Frozen sample policy is missing or does not match the configured hash.",
            policy,
        ),
        _sample_gate(
            "final_holdout_matured_outcomes_min_100",
            "Final Holdout Matured Outcomes Minimum",
            "matured_outcomes",
            policy.matured_outcomes_minimum,
            ">=",
            matured,
            _pass_fail(matured, policy.matured_outcomes_minimum),
            _threshold_reason("Matured outcomes", matured, policy.matured_outcomes_minimum),
            policy,
        ),
        _sample_gate(
            "final_holdout_distinct_signal_dates_min_60",
            "Final Holdout Distinct Signal Dates Minimum",
            "distinct_signal_dates",
            policy.distinct_signal_dates_minimum,
            ">=",
            len(signal_dates),
            _pass_fail(len(signal_dates), policy.distinct_signal_dates_minimum),
            _threshold_reason(
                "Distinct signal dates", len(signal_dates), policy.distinct_signal_dates_minimum
            ),
            policy,
        ),
        _sample_gate(
            "final_holdout_observation_sessions_min_126",
            "Final Holdout Observation Sessions Minimum",
            "observation_sessions",
            policy.observation_sessions_minimum,
            ">=",
            len(processed_sessions),
            _pass_fail(len(processed_sessions), policy.observation_sessions_minimum),
            _threshold_reason(
                "Observation sessions", len(processed_sessions), policy.observation_sessions_minimum
            ),
            policy,
        ),
        _sample_gate(
            "final_holdout_calendar_months_min_4",
            "Final Holdout Calendar Months Minimum",
            "calendar_months",
            policy.calendar_months_minimum,
            ">=",
            len(months),
            _pass_fail(len(months), policy.calendar_months_minimum),
            _threshold_reason("Calendar months", len(months), policy.calendar_months_minimum),
            policy,
        ),
        _sample_gate(
            "final_holdout_positive_class_min_20",
            "Final Holdout Positive Class Minimum",
            "positive_outcomes",
            policy.positive_class_minimum,
            ">=",
            positive,
            _pass_fail(positive, policy.positive_class_minimum),
            _threshold_reason("Positive outcomes", positive, policy.positive_class_minimum),
            policy,
        ),
        _sample_gate(
            "final_holdout_negative_class_min_20",
            "Final Holdout Negative Class Minimum",
            "negative_outcomes",
            policy.negative_class_minimum,
            ">=",
            negative,
            _pass_fail(negative, policy.negative_class_minimum),
            _threshold_reason("Negative outcomes", negative, policy.negative_class_minimum),
            policy,
        ),
        _sample_gate(
            "final_holdout_provenance_valid",
            "Final Holdout Provenance Valid",
            "provenance_failures",
            0,
            "==",
            provenance_failures,
            "PASS" if provenance_failures == 0 else "FAIL",
            "Every included prediction has prospective ingestion provenance."
            if provenance_failures == 0
            else "At least one included prediction lacks prospective ingestion provenance.",
            policy,
        ),
        _sample_gate(
            "final_holdout_backfill_absent",
            "Final Holdout Backfill Absent",
            "blocked_backfills",
            0,
            "==",
            blocked_backfills,
            "PASS" if blocked_backfills == 0 else "FAIL",
            "No blocked backfill events are included."
            if blocked_backfills == 0
            else "At least one blocked backfill event exists.",
            policy,
        ),
        _sample_gate(
            "final_holdout_data_integrity_valid",
            "Final Holdout Data Integrity Valid",
            "invalidated_outcomes",
            0,
            "==",
            invalidated_outcomes,
            "PASS" if invalidated_outcomes == 0 else "FAIL",
            "Data-integrity event count is zero."
            if invalidated_outcomes == 0
            else "At least one unresolved data-invalidated event is included.",
            policy,
        ),
        _sample_gate(
            "final_holdout_frozen_artifacts_unchanged",
            "Final Holdout Frozen Artifacts Unchanged",
            "artifact_integrity_passed",
            True,
            "is true",
            ok,
            "PASS" if ok else "FAIL",
            "Frozen artifact, feature, policy, calibrator, OOD, execution, and code hashes match enrollment."
            if ok
            else artifact_reason,
            policy,
        ),
    ]
    sample_sufficient = all(gate.status == "PASS" for gate in gates)
    gates.append(
        _sample_gate(
            "final_holdout_sample_sufficient",
            "Final Holdout Sample Sufficient",
            "sample_sufficient",
            True,
            "is true",
            sample_sufficient,
            "PASS" if sample_sufficient else "FAIL",
            "Every mandatory sample, provenance, and integrity gate passes."
            if sample_sufficient
            else "At least one mandatory sample, provenance, or integrity gate fails.",
            policy,
        )
    )
    early = (
        matured >= policy.early_diagnostic_matured_outcomes_minimum
        and len(signal_dates) >= policy.early_diagnostic_distinct_signal_dates_minimum
    )
    deficits = {
        "matured": policy.matured_outcomes_minimum - matured,
        "signal_dates": policy.distinct_signal_dates_minimum - len(signal_dates),
        "observation_sessions": policy.observation_sessions_minimum - len(processed_sessions),
        "calendar_months": policy.calendar_months_minimum - len(months),
        "positive": policy.positive_class_minimum - positive,
        "negative": policy.negative_class_minimum - negative,
    }
    status = (
        "READY_FOR_EVALUATION"
        if sample_sufficient
        else "EARLY_DIAGNOSTIC_AVAILABLE"
        if early
        else "COLLECTING"
    )
    return FinalHoldoutSampleState(
        run_id=run.run_id,
        model_id=enrolled.model_id,
        status=status,
        matured_outcomes=matured,
        distinct_signal_dates=len(signal_dates),
        observation_sessions=len(processed_sessions),
        calendar_months=len(months),
        positive_outcomes=positive,
        negative_outcomes=negative,
        pending_entries=pending_entries,
        open_positions=open_positions,
        provenance_failures=provenance_failures,
        blocked_backfills=blocked_backfills,
        invalidated_outcomes=invalidated_outcomes,
        artifact_integrity_passed=ok,
        artifact_integrity_reason=artifact_reason,
        sample_sufficient=sample_sufficient,
        early_diagnostic_available=early,
        estimated_remaining_requirement=_estimate_remaining(deficits),
        gates=tuple(gates),
    )


def final_holdout_sample_states(
    root: str | Path,
    run_id: str | None = None,
) -> tuple[FinalHoldoutSampleState, ...]:
    paths = ProjectPaths(Path(root))
    events = final_holdout_events(paths.engine_db)
    states: list[FinalHoldoutSampleState] = []
    for run in list_final_holdout_runs(paths.engine_db):
        if run_id is not None and run.run_id != run_id:
            continue
        policy = _sample_policy_from_run(run)
        for enrolled in list_final_holdout_models(paths.engine_db, run.run_id):
            states.append(_sample_state_for_model(root, run, enrolled, events, policy))
    return tuple(states)


def _refresh_run_status(root: str | Path, run: FinalHoldoutRun) -> None:
    if run.status in {"EVALUATED_PASS", "EVALUATED_FAIL", "INVALIDATED", "CLOSED"}:
        return
    states = final_holdout_sample_states(root, run.run_id)
    if not states:
        return
    next_status: RunStatus
    if all(state.sample_sufficient for state in states):
        next_status = "READY_FOR_EVALUATION"
    elif any(state.early_diagnostic_available for state in states):
        next_status = "EARLY_DIAGNOSTIC_AVAILABLE"
    elif run.latest_processed_market_date is not None:
        next_status = "COLLECTING"
    else:
        next_status = "CREATED"
    with engine_connection(ProjectPaths(Path(root)).engine_db) as connection:
        connection.execute(
            "UPDATE final_holdout_runs SET status = ? WHERE run_id = ?",
            (next_status, run.run_id),
        )


def _verify_frozen_models(
    root: str | Path, db_path: str | Path, run: FinalHoldoutRun
) -> tuple[bool, str, tuple[RegisteredModel, ...], tuple[FinalHoldoutModel, ...]]:
    enrolled = list_final_holdout_models(db_path, run.run_id)
    current = {model.model_id: model for model in list_models(db_path)}
    current_commit = current_commit_hash(root)
    if run.creation_git_commit and current_commit != run.creation_git_commit:
        return False, "code commit hash changed since enrollment", (), enrolled
    if run.execution_policy_hash != _execution_policy_hash():
        return False, "execution policy hash changed since enrollment", (), enrolled
    selected: list[RegisteredModel] = []
    for frozen in enrolled:
        model = current.get(frozen.model_id)
        if model is None:
            return False, f"enrolled model missing from registry: {frozen.model_id}", (), enrolled
        if not Path(frozen.artifact_path).exists():
            return False, f"artifact missing: {frozen.model_id}", (), enrolled
        if hash_file(frozen.artifact_path) != frozen.artifact_hash:
            return False, f"artifact hash changed: {frozen.model_id}", (), enrolled
        if model.feature_manifest_hash != str(frozen.metadata.get("feature_manifest_hash") or ""):
            return False, f"feature manifest hash changed: {frozen.model_id}", (), enrolled
        if str(model.metrics.get("selection_policy_configuration_hash") or "") != (
            frozen.selection_policy_hash
        ):
            return False, f"selection policy hash changed: {frozen.model_id}", (), enrolled
        if _calibration_hash(model) != frozen.calibration_governance_hash:
            return False, f"calibration governance hash changed: {frozen.model_id}", (), enrolled
        if _calibrator_artifact_hash(model) != str(
            frozen.metadata.get("calibrator_artifact_hash") or ""
        ):
            return False, f"calibrator artifact hash changed: {frozen.model_id}", (), enrolled
        if _ood_hash(model) != frozen.ood_governance_hash:
            return False, f"OOD governance hash changed: {frozen.model_id}", (), enrolled
        frozen_code_hash = frozen.metadata.get("code_commit_hash")
        if frozen_code_hash and model.code_commit_hash != str(frozen_code_hash):
            return False, f"model code hash changed: {frozen.model_id}", (), enrolled
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
            ok, drift_reason, models, _ = _verify_frozen_models(project_root, paths.engine_db, run)
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
                    "prospective_provenance_valid": True,
                    "provenance_source": "final_holdout_run_session_availability",
                },
                include_row_payload=True,
            )
            metadata = dict(run.metadata)
            raw_processed = metadata.get("processed_sessions", [])
            existing_processed = (
                {str(value) for value in raw_processed}
                if isinstance(raw_processed, list)
                else set()
            )
            processed_sessions = sorted({*existing_processed, session})
            metadata["processed_sessions"] = processed_sessions
            status: RunStatus = "COLLECTING"
            with engine_connection(paths.engine_db) as connection:
                connection.execute(
                    """
                    UPDATE final_holdout_runs
                    SET status = ?, latest_processed_market_date = ?,
                        first_eligible_future_signal_date = COALESCE(first_eligible_future_signal_date, ?),
                        metadata_json = ?
                    WHERE run_id = ?
                    """,
                    (status, session, session, dumps(metadata), run.run_id),
                )
            refreshed_run = FinalHoldoutRun(
                **{
                    **run.__dict__,
                    "status": status,
                    "latest_processed_market_date": session,
                    "first_eligible_future_signal_date": (
                        run.first_eligible_future_signal_date or session
                    ),
                    "metadata": metadata,
                }
            )
            _refresh_run_status(project_root, refreshed_run)
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
    diagnostic_only: bool = False,
) -> FinalHoldoutEvaluationResult:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    runs = {run.run_id: run for run in list_final_holdout_runs(paths.engine_db)}
    run = runs.get(run_id)
    if run is None:
        raise ValueError(f"Unknown final-holdout run: {run_id}")
    models = list_final_holdout_models(paths.engine_db, run_id)
    events = final_holdout_events(paths.engine_db, run_id)
    sample_states = {state.model_id: state for state in final_holdout_sample_states(root, run_id)}
    if not diagnostic_only and any(not state.sample_sufficient for state in sample_states.values()):
        raise ValueError(
            "Final-holdout evaluation requires complete sample sufficiency. "
            "Use --diagnostic-only for non-promotable early diagnostics."
        )
    if diagnostic_only and not any(
        state.early_diagnostic_available or state.sample_sufficient
        for state in sample_states.values()
    ):
        raise ValueError(
            "Diagnostic-only final-holdout evaluation requires early diagnostic evidence."
        )
    metrics_by_model: dict[str, dict[str, object]] = {}
    gates_by_model: dict[str, tuple[GateResult, ...]] = {}
    manifest_by_model: dict[str, str] = {}
    current_models = {model.model_id: model for model in list_models(paths.engine_db)}
    config_hash = configuration_hash(
        {
            "schema": FINAL_HOLDOUT_SCHEMA_VERSION,
            "diagnostic_only": diagnostic_only,
        }
    )
    all_pass = True
    for enrolled in models:
        sample_state = sample_states[enrolled.model_id]
        model_events = (
            events.loc[events["model_id"] == enrolled.model_id] if not events.empty else events
        )
        exits = (
            model_events.loc[model_events["event_type"] == "FINAL_HOLDOUT_EXIT_FILLED"]
            if not model_events.empty
            else model_events
        )
        matured = sample_state.matured_outcomes
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
        final_gate_status: Literal["PASS", "FAIL"] = "FAIL" if diagnostic_only else "PASS"
        final_gate_actual = sample_state.status if diagnostic_only else FINAL_HOLDOUT_STATUS
        final_gates: tuple[GateResult, ...] = (
            make_gate(
                gate_id=FINAL_HOLDOUT_PROMOTION_GATE_ID,
                gate_name="Final Holdout Required For Promotion",
                category="research integrity",
                scope="model",
                metric_name="holdout_status",
                threshold=FINAL_HOLDOUT_STATUS,
                comparator="equals",
                actual_value=final_gate_actual,
                status=final_gate_status,
                mandatory=True,
                evidence_source=FINAL_HOLDOUT_SCHEMA_VERSION,
                reason="Diagnostic-only evaluation cannot set FINAL_HOLDOUT."
                if diagnostic_only
                else "Prospective final-holdout evaluation completed for this model.",
                configuration_hash_value=config_hash,
            ),
            *sample_state.gates,
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
            "final_holdout_run_id": run_id,
            "final_holdout_evidence_manifest_hash": evidence_manifest,
            "final_holdout_matured_outcomes": matured,
            "final_holdout_mean_net_return": (
                float(pd.Series(returns).mean()) if returns else GATE_VALUE_NOT_AVAILABLE
            ),
            "final_holdout_schema_version": FINAL_HOLDOUT_SCHEMA_VERSION,
            "final_holdout_sample_policy_version": run.sample_policy_version,
            "final_holdout_sample_policy_hash": run.sample_policy_hash,
        }
        if not diagnostic_only:
            metrics["holdout_status"] = FINAL_HOLDOUT_STATUS
        else:
            metrics["final_holdout_diagnostic_status"] = sample_state.status
        metrics_by_model[enrolled.model_id] = metrics
        gates_by_model[enrolled.model_id] = final_gates
        manifest_by_model[enrolled.model_id] = evidence_manifest
        if not promotion_eligibility(final_gates).eligible:
            all_pass = False
        model = current_models.get(enrolled.model_id)
        if model is not None and not diagnostic_only:
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
    status: RunStatus = (
        run.status if diagnostic_only else ("EVALUATED_PASS" if all_pass else "EVALUATED_FAIL")
    )
    if not diagnostic_only:
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
            "diagnostic_only": diagnostic_only,
            "evidence_manifest_hashes": manifest_by_model,
        },
        unique_suffix=f"{run_id}|diagnostic={diagnostic_only}",
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
    states = {(state.run_id, state.model_id): state for state in final_holdout_sample_states(root)}
    registry_models = {model.model_id: model for model in list_models(paths.engine_db)}
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
        policy = _sample_policy_from_run(run)
        for model in models:
            state = states[(run.run_id, model.model_id)]
            registered = registry_models.get(model.model_id)
            if registered is None:
                promotion_eligible = False
            else:
                promotion_eligible = (
                    not model.research_only
                    and registered.metrics.get("holdout_status") == FINAL_HOLDOUT_STATUS
                    and promotion_eligibility(registered.gate_results).eligible
                )
            rows.append(
                {
                    "run_id": run.run_id,
                    "model_id": model.model_id,
                    "run_status": run.status,
                    "model_status": state.status,
                    "baseline_market_date": run.baseline_market_date,
                    "first_eligible_future_signal_date": run.first_eligible_future_signal_date,
                    "latest_processed_market_date": run.latest_processed_market_date,
                    "matured_outcomes": state.matured_outcomes,
                    "matured_outcomes_required": policy.matured_outcomes_minimum,
                    "distinct_signal_dates": state.distinct_signal_dates,
                    "distinct_signal_dates_required": policy.distinct_signal_dates_minimum,
                    "observation_sessions": state.observation_sessions,
                    "observation_sessions_required": policy.observation_sessions_minimum,
                    "calendar_months": state.calendar_months,
                    "calendar_months_required": policy.calendar_months_minimum,
                    "positive_outcomes": state.positive_outcomes,
                    "positive_outcomes_required": policy.positive_class_minimum,
                    "negative_outcomes": state.negative_outcomes,
                    "negative_outcomes_required": policy.negative_class_minimum,
                    "pending_entries": state.pending_entries,
                    "open_positions": state.open_positions,
                    "provenance_failures": state.provenance_failures,
                    "blocked_backfills": state.blocked_backfills,
                    "invalidated_outcomes": state.invalidated_outcomes,
                    "artifact_integrity_status": (
                        "PASS" if state.artifact_integrity_passed else "FAIL"
                    ),
                    "estimated_remaining_requirement": state.estimated_remaining_requirement,
                    "promotion_eligible": promotion_eligible,
                    "event_count": len(run_events),
                    "signals": int(
                        (run_events["event_type"] == "FINAL_HOLDOUT_SIGNAL_CREATED").sum()
                    )
                    if not run_events.empty
                    else 0,
                    "rejected_signals": int(
                        (run_events["event_type"] == "FINAL_HOLDOUT_SIGNAL_REJECTED").sum()
                    )
                    if not run_events.empty
                    else 0,
                    "label": "Prospective shadow validation. Not a live trade recommendation.",
                }
            )
    return pd.DataFrame(rows)
