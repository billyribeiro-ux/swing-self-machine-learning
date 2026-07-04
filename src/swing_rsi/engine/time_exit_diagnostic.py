from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from swing_rsi.config import ProjectPaths
from swing_rsi.data.loader import load_ohlcv_csv
from swing_rsi.data.validation import validate_ohlcv
from swing_rsi.engine.manifest import current_commit_hash
from swing_rsi.engine.signal_discovery import load_signal_discovery_frames
from swing_rsi.engine.storage import dumps, engine_connection, loads
from swing_rsi.engine.time_exit_utility import (
    SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID,
    TIME_EXIT_HORIZON,
    TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE,
    TIME_EXIT_UTILITY_EPSILON,
    TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION,
)

PROSPECTIVE_TIME_EXIT_DIAGNOSTIC_SCHEMA_VERSION = "prospective_time_exit_diagnostic_v1"
PROSPECTIVE_TIME_EXIT_ARCHETYPE = "sector_rotation_buy"
PROSPECTIVE_TIME_EXIT_ACTION = "BUY"
PROSPECTIVE_TIME_EXIT_SCOPE = "ORDINARY"
PROSPECTIVE_TIME_EXIT_BASELINE_POLICY_ID = "sector_rotation_buy_ordinary_20d_default_t2p0_s1p0"
PROSPECTIVE_TIME_EXIT_EXPERIMENTAL_POLICY_ID = (
    "sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25"
)
PROSPECTIVE_TIME_EXIT_POLICY_IDS = (
    PROSPECTIVE_TIME_EXIT_BASELINE_POLICY_ID,
    PROSPECTIVE_TIME_EXIT_EXPERIMENTAL_POLICY_ID,
)

DiagnosticRunStatus = Literal[
    "CREATED",
    "COLLECTING",
    "EARLY_DIAGNOSTIC_AVAILABLE",
    "READY_FOR_REVIEW",
    "CLOSED",
    "INVALIDATED",
]

DIAGNOSTIC_EVENT_OBSERVATION_CREATED = "DIAGNOSTIC_OBSERVATION_CREATED"
DIAGNOSTIC_EVENT_OBSERVATION_REJECTED = "DIAGNOSTIC_OBSERVATION_REJECTED"
DIAGNOSTIC_EVENT_ENTRY_PENDING = "DIAGNOSTIC_ENTRY_PENDING"
DIAGNOSTIC_EVENT_ENTRY_FILLED = "DIAGNOSTIC_ENTRY_FILLED"
DIAGNOSTIC_EVENT_POSITION_MARKED = "DIAGNOSTIC_POSITION_MARKED"
DIAGNOSTIC_EVENT_TIME_EXIT_MATURED = "DIAGNOSTIC_TIME_EXIT_MATURED"
DIAGNOSTIC_EVENT_STOP_TOUCHED = "DIAGNOSTIC_STOP_TOUCHED"
DIAGNOSTIC_EVENT_TARGET_TOUCHED = "DIAGNOSTIC_TARGET_TOUCHED"
DIAGNOSTIC_EVENT_BACKFILL_BLOCKED = "DIAGNOSTIC_BACKFILL_BLOCKED"
DIAGNOSTIC_EVENT_DATA_INVALIDATED = "DIAGNOSTIC_DATA_INVALIDATED"

DIAGNOSTIC_OBSERVATION_LABEL = "RESEARCH_OBSERVATION"
DIAGNOSTIC_ONLY_LABEL = "DIAGNOSTIC_ONLY"

EARLY_DIAGNOSTIC_MATURED_MINIMUM = 30
EARLY_DIAGNOSTIC_SIGNAL_DATES_MINIMUM = 20
STRONG_REVIEW_MATURED_MINIMUM = 100
STRONG_REVIEW_SIGNAL_DATES_MINIMUM = 60
STRONG_REVIEW_MONTHS_MINIMUM = 4
DEFAULT_ROUND_TRIP_COST_BPS = 5.0


@dataclass(frozen=True)
class ProspectiveTimeExitDiagnosticRun:
    diagnostic_run_id: str
    schema_version: str
    created_at_utc: str
    baseline_market_date: str
    first_eligible_future_as_of_date: str | None
    hypothesis_id: str
    archetype: str
    action: str
    product_scope: str
    horizon: int
    target_stop_policy_ids: tuple[str, ...]
    label_schema: str
    code_commit: str | None
    feature_manifest_hash: str
    signal_discovery_generation_id: str | None
    status: DiagnosticRunStatus
    latest_processed_market_date: str | None
    notes: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class ProspectiveTimeExitDiagnosticEvent:
    event_id: str
    unique_key: str
    diagnostic_run_id: str
    event_type: str
    event_time_utc: str
    market_as_of_date: str
    ticker: str
    signal_id: str | None
    payload: dict[str, object]
    inserted: bool


@dataclass(frozen=True)
class TimeExitDiagnosticInitResult:
    run: ProspectiveTimeExitDiagnosticRun
    created: bool
    message: str


@dataclass(frozen=True)
class TimeExitDiagnosticUpdateResult:
    diagnostic_run_id: str | None
    events_inserted: int
    observations_created: int
    rejected_observations: int
    pending_entries_created: int
    entries_filled: int
    position_marks_created: int
    matured_outcomes: int
    backfill_blocked: int
    status: DiagnosticRunStatus | str


def _stable_hash(value: object, *, length: int = 24) -> str:
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()[:length]


def _event_id(unique_key: str) -> str:
    return hashlib.sha256(unique_key.encode("utf-8")).hexdigest()[:24]


def _jsonable(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return cast(Any, value).isoformat()
    try:
        if bool(pd.isna(cast(Any, value))):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return cast(Any, value).item()
    return value


def _safe_float(value: object) -> float | None:
    try:
        numeric = float(cast(float, value))
    except (TypeError, ValueError):
        return None
    return numeric if pd.notna(numeric) else None


def _safe_text(value: object) -> str:
    try:
        if bool(pd.isna(cast(Any, value))):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value or "").strip()


def _latest_feature_path(root: Path) -> Path:
    paths = ProjectPaths(root)
    candidates = sorted(
        paths.feature_data.glob("*_features.parquet"),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError("No feature parquet file found. Run build-features first.")
    return candidates[-1]


def _feature_hash_from_path(path: Path) -> str:
    parts = path.name.split("_")
    return parts[1] if len(parts) > 1 else "unknown"


def _latest_feature_panel(root: Path) -> tuple[pd.DataFrame, str]:
    path = _latest_feature_path(root)
    return pd.read_parquet(path), _feature_hash_from_path(path)


def _latest_session(frame: pd.DataFrame) -> str:
    if frame.empty or "Date" not in frame.columns:
        raise ValueError("Feature panel has no completed market sessions")
    return pd.Timestamp(frame["Date"].max()).date().isoformat()


def _first_session_after(frame: pd.DataFrame, baseline_date: str) -> str | None:
    if frame.empty or "Date" not in frame.columns:
        return None
    sessions = sorted(
        pd.to_datetime(frame["Date"], errors="coerce").dropna().dt.date.astype(str).unique()
    )
    return next((session for session in sessions if session > baseline_date), None)


def _metadata_map(frames: dict[str, pd.DataFrame]) -> dict[str, object]:
    metadata = frames.get("metadata", pd.DataFrame())
    if metadata.empty or not {"field", "value"}.issubset(metadata.columns):
        return {}
    return {str(row["field"]): row["value"] for _, row in metadata.iterrows()}


def _generation_id_from_frames(frames: dict[str, pd.DataFrame], generation: str) -> str:
    metadata = _metadata_map(frames)
    generation_id = _safe_text(metadata.get("generation_id"))
    if generation_id:
        return generation_id
    summary = frames.get("summary", pd.DataFrame())
    if not summary.empty and "generation_id" in summary.columns:
        return _safe_text(summary.iloc[0].get("generation_id")) or generation
    return generation


def _target_policy_ids_from_frames(
    frames: dict[str, pd.DataFrame], hypothesis_id: str
) -> tuple[str, ...]:
    hypotheses = frames.get("hypotheses", pd.DataFrame())
    if hypotheses.empty or "hypothesis_id" not in hypotheses.columns:
        return PROSPECTIVE_TIME_EXIT_POLICY_IDS
    matched = hypotheses.loc[hypotheses["hypothesis_id"].astype(str) == hypothesis_id]
    ids = tuple(
        sorted(
            {
                _safe_text(value)
                for value in matched.get("target_stop_policy_id", pd.Series(dtype=object))
                if _safe_text(value)
            }.union(PROSPECTIVE_TIME_EXIT_POLICY_IDS)
        )
    )
    return ids or PROSPECTIVE_TIME_EXIT_POLICY_IDS


def _row_to_run(row: Any) -> ProspectiveTimeExitDiagnosticRun:
    item = dict(row)
    target_policy_ids = loads(str(item["target_stop_policy_ids_json"]))
    metadata = loads(str(item["metadata_json"]))
    return ProspectiveTimeExitDiagnosticRun(
        diagnostic_run_id=str(item["diagnostic_run_id"]),
        schema_version=str(item["schema_version"]),
        created_at_utc=str(item["created_at_utc"]),
        baseline_market_date=str(item["baseline_market_date"]),
        first_eligible_future_as_of_date=str(item["first_eligible_future_as_of_date"])
        if item["first_eligible_future_as_of_date"]
        else None,
        hypothesis_id=str(item["hypothesis_id"]),
        archetype=str(item["archetype"]),
        action=str(item["action"]),
        product_scope=str(item["product_scope"]),
        horizon=int(item["horizon"]),
        target_stop_policy_ids=tuple(str(value) for value in target_policy_ids),
        label_schema=str(item["label_schema"]),
        code_commit=str(item["code_commit"]) if item["code_commit"] else None,
        feature_manifest_hash=str(item["feature_manifest_hash"]),
        signal_discovery_generation_id=str(item["signal_discovery_generation_id"])
        if item["signal_discovery_generation_id"]
        else None,
        status=cast(DiagnosticRunStatus, str(item["status"])),
        latest_processed_market_date=str(item["latest_processed_market_date"])
        if item["latest_processed_market_date"]
        else None,
        notes=str(item["notes"]),
        metadata=metadata if isinstance(metadata, dict) else {},
    )


def list_time_exit_diagnostic_runs(
    db_path: str | Path,
) -> tuple[ProspectiveTimeExitDiagnosticRun, ...]:
    with engine_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM prospective_time_exit_diagnostic_runs
            ORDER BY created_at_utc, diagnostic_run_id
            """
        ).fetchall()
    return tuple(_row_to_run(row) for row in rows)


def active_time_exit_diagnostic_run(
    db_path: str | Path,
    *,
    hypothesis_id: str = SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID,
) -> ProspectiveTimeExitDiagnosticRun | None:
    runs = [
        run
        for run in list_time_exit_diagnostic_runs(db_path)
        if run.hypothesis_id == hypothesis_id
        and run.status
        in {"CREATED", "COLLECTING", "EARLY_DIAGNOSTIC_AVAILABLE", "READY_FOR_REVIEW"}
    ]
    return runs[-1] if runs else None


def initialize_time_exit_diagnostic_run(
    root: str | Path,
    *,
    hypothesis: str = SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID,
    generation: str = "latest",
    baseline_date: str | None = None,
    feature_panel: pd.DataFrame | None = None,
) -> TimeExitDiagnosticInitResult:
    if hypothesis != SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID:
        raise ValueError(f"Unsupported time-exit diagnostic hypothesis: {hypothesis}")
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    existing = active_time_exit_diagnostic_run(paths.engine_db, hypothesis_id=hypothesis)
    if existing is not None:
        return TimeExitDiagnosticInitResult(
            run=existing,
            created=False,
            message=f"Existing prospective time-exit diagnostic run {existing.diagnostic_run_id}.",
        )
    feature_frame, feature_hash = (
        (feature_panel.copy(), "test-feature-manifest")
        if feature_panel is not None
        else _latest_feature_panel(project_root)
    )
    baseline = baseline_date or _latest_session(feature_frame)
    first_eligible = _first_session_after(feature_frame, baseline)
    frames = load_signal_discovery_frames(project_root, generation=generation)
    metadata = _metadata_map(frames)
    generation_id = _generation_id_from_frames(frames, generation)
    feature_manifest_hash = _safe_text(metadata.get("feature_manifest_hash")) or feature_hash
    target_policy_ids = _target_policy_ids_from_frames(frames, hypothesis)
    created_at = datetime.now(UTC).isoformat()
    run_id = _stable_hash(
        {
            "schema": PROSPECTIVE_TIME_EXIT_DIAGNOSTIC_SCHEMA_VERSION,
            "created_at": created_at,
            "baseline": baseline,
            "hypothesis": hypothesis,
            "generation": generation_id,
        }
    )
    run = ProspectiveTimeExitDiagnosticRun(
        diagnostic_run_id=run_id,
        schema_version=PROSPECTIVE_TIME_EXIT_DIAGNOSTIC_SCHEMA_VERSION,
        created_at_utc=created_at,
        baseline_market_date=baseline,
        first_eligible_future_as_of_date=first_eligible,
        hypothesis_id=hypothesis,
        archetype=PROSPECTIVE_TIME_EXIT_ARCHETYPE,
        action=PROSPECTIVE_TIME_EXIT_ACTION,
        product_scope=PROSPECTIVE_TIME_EXIT_SCOPE,
        horizon=TIME_EXIT_HORIZON,
        target_stop_policy_ids=target_policy_ids,
        label_schema=TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION,
        code_commit=current_commit_hash(project_root),
        feature_manifest_hash=feature_manifest_hash,
        signal_discovery_generation_id=generation_id,
        status="CREATED",
        latest_processed_market_date=None,
        notes=(
            "Prospective diagnostic ledger. DIAGNOSTIC_ONLY / RESEARCH_OBSERVATION; "
            "not a live signal and not final-holdout evidence."
        ),
        metadata={
            "baseline_rule": "latest completed local feature session unless explicit override",
            "no_backfill_rule": "as_of_date must be greater than baseline_market_date",
            "diagnostic_notice": TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE,
            "sample_thresholds": {
                "early_diagnostic_matured_outcomes": EARLY_DIAGNOSTIC_MATURED_MINIMUM,
                "early_diagnostic_distinct_signal_dates": EARLY_DIAGNOSTIC_SIGNAL_DATES_MINIMUM,
                "strong_review_matured_outcomes": STRONG_REVIEW_MATURED_MINIMUM,
                "strong_review_distinct_signal_dates": STRONG_REVIEW_SIGNAL_DATES_MINIMUM,
                "strong_review_minimum_months": STRONG_REVIEW_MONTHS_MINIMUM,
            },
        },
    )
    with engine_connection(paths.engine_db) as connection:
        connection.execute(
            """
            INSERT INTO prospective_time_exit_diagnostic_runs (
                diagnostic_run_id, schema_version, created_at_utc, baseline_market_date,
                first_eligible_future_as_of_date, hypothesis_id, archetype, action,
                product_scope, horizon, target_stop_policy_ids_json, label_schema,
                code_commit, feature_manifest_hash, signal_discovery_generation_id,
                status, latest_processed_market_date, notes, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.diagnostic_run_id,
                run.schema_version,
                run.created_at_utc,
                run.baseline_market_date,
                run.first_eligible_future_as_of_date,
                run.hypothesis_id,
                run.archetype,
                run.action,
                run.product_scope,
                run.horizon,
                dumps(run.target_stop_policy_ids),
                run.label_schema,
                run.code_commit,
                run.feature_manifest_hash,
                run.signal_discovery_generation_id,
                run.status,
                run.latest_processed_market_date,
                run.notes,
                dumps(run.metadata),
            ),
        )
    return TimeExitDiagnosticInitResult(
        run=run,
        created=True,
        message=f"Created prospective time-exit diagnostic run {run_id}.",
    )


def append_time_exit_diagnostic_event(
    db_path: str | Path,
    *,
    diagnostic_run_id: str,
    event_type: str,
    market_as_of_date: str,
    ticker: str,
    signal_id: str | None,
    payload: dict[str, object],
    unique_suffix: str = "",
) -> ProspectiveTimeExitDiagnosticEvent:
    unique_key = "|".join(
        [
            diagnostic_run_id,
            event_type,
            market_as_of_date,
            ticker.upper(),
            signal_id or "",
            unique_suffix,
        ]
    )
    event = ProspectiveTimeExitDiagnosticEvent(
        event_id=_event_id(unique_key),
        unique_key=unique_key,
        diagnostic_run_id=diagnostic_run_id,
        event_type=event_type,
        event_time_utc=datetime.now(UTC).isoformat(),
        market_as_of_date=market_as_of_date,
        ticker=ticker.upper(),
        signal_id=signal_id,
        payload={str(key): _jsonable(value) for key, value in payload.items()},
        inserted=False,
    )
    with engine_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO prospective_time_exit_diagnostic_events (
                event_id, unique_key, diagnostic_run_id, event_type, event_time_utc,
                market_as_of_date, ticker, signal_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.unique_key,
                event.diagnostic_run_id,
                event.event_type,
                event.event_time_utc,
                event.market_as_of_date,
                event.ticker,
                event.signal_id,
                dumps(event.payload),
            ),
        )
    return ProspectiveTimeExitDiagnosticEvent(
        event_id=event.event_id,
        unique_key=event.unique_key,
        diagnostic_run_id=event.diagnostic_run_id,
        event_type=event.event_type,
        event_time_utc=event.event_time_utc,
        market_as_of_date=event.market_as_of_date,
        ticker=event.ticker,
        signal_id=event.signal_id,
        payload=event.payload,
        inserted=cursor.rowcount == 1,
    )


def list_time_exit_diagnostic_events(db_path: str | Path) -> pd.DataFrame:
    with engine_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM prospective_time_exit_diagnostic_events
            ORDER BY event_time_utc, event_id
            """
        ).fetchall()
    records: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = loads(str(item.pop("payload_json")))
        records.append(item)
    return pd.DataFrame(records)


def _event_payload(event: pd.Series) -> dict[str, object]:
    payload = event.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def _active_runs(db_path: str | Path) -> tuple[ProspectiveTimeExitDiagnosticRun, ...]:
    return tuple(
        run
        for run in list_time_exit_diagnostic_runs(db_path)
        if run.status in {"CREATED", "COLLECTING", "EARLY_DIAGNOSTIC_AVAILABLE", "READY_FOR_REVIEW"}
    )


def _load_feature_atr_map(root: Path) -> dict[tuple[str, str], float]:
    try:
        feature_frame, _ = _latest_feature_panel(root)
    except FileNotFoundError:
        return {}
    if feature_frame.empty or not {"Date", "symbol", "atr_pct_14"}.issubset(feature_frame.columns):
        return {}
    frame = feature_frame[["Date", "symbol", "atr_pct_14"]].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.date.astype(str)
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    return {
        (str(row["Date"]), str(row["symbol"])): float(row["atr_pct_14"])
        for _, row in frame.dropna(subset=["Date", "symbol", "atr_pct_14"]).iterrows()
    }


def _raw_frame(root: Path, ticker: str) -> pd.DataFrame | None:
    path = ProjectPaths(root).raw_data / f"{ticker.upper()}.csv"
    if not path.exists():
        return None
    return load_ohlcv_csv(path)


def _next_session_after(frame: pd.DataFrame, as_of_date: str) -> pd.Timestamp | None:
    data = validate_ohlcv(frame)
    future_sessions = data.index[data.index > pd.Timestamp(as_of_date)]
    if future_sessions.empty:
        return None
    return pd.Timestamp(future_sessions[0])


def _time_exit_date(
    frame: pd.DataFrame, *, signal_as_of_date: str, horizon: int
) -> pd.Timestamp | None:
    data = validate_ohlcv(frame)
    try:
        location = data.index.get_loc(pd.Timestamp(signal_as_of_date))
    except KeyError:
        return None
    if not isinstance(location, int):
        return None
    exit_position = int(location) + horizon
    if exit_position >= len(data):
        return None
    return pd.Timestamp(data.index[exit_position])


def _path_stats(
    frame: pd.DataFrame,
    *,
    entry_date: str,
    entry_price: float,
    exit_date: str,
    cost_bps: float,
) -> dict[str, object]:
    data = validate_ohlcv(frame)
    window = data.loc[pd.Timestamp(entry_date) : pd.Timestamp(exit_date)]
    if window.empty:
        raise ValueError("No daily bars are available for diagnostic outcome window.")
    exit_price = float(window["Close"].iloc[-1])
    gross = (exit_price / entry_price) - 1.0
    net = gross - (cost_bps / 10_000.0)
    favorable = (window["High"] / entry_price) - 1.0
    adverse = (window["Low"] / entry_price) - 1.0
    mfe = float(favorable.max())
    mae = float(adverse.min())
    max_fav_date = pd.Timestamp(favorable.idxmax())
    max_adv_date = pd.Timestamp(adverse.idxmin())
    entry_ts = pd.Timestamp(entry_date)
    sessions = list(pd.Timestamp(index) for index in window.index)
    time_to_max_fav = sessions.index(max_fav_date) if max_fav_date in sessions else None
    time_to_max_adv = sessions.index(max_adv_date) if max_adv_date in sessions else None
    denominator = max(abs(mae), TIME_EXIT_UTILITY_EPSILON)
    return {
        "exit_date": pd.Timestamp(exit_date).date().isoformat(),
        "exit_price": exit_price,
        "time_exit_gross_return": gross,
        "time_exit_net_return": net,
        "time_exit_positive": net > 0.0,
        "time_exit_utility": net / denominator,
        "MFE": mfe,
        "MAE": mae,
        "time_to_max_favorable": time_to_max_fav,
        "time_to_max_adverse": time_to_max_adv,
        "entry_to_exit_sessions": max(0, (pd.Timestamp(exit_date) - entry_ts).days),
        "round_trip_cost_bps": cost_bps,
    }


def _policy_touch_outcome(
    frame: pd.DataFrame,
    *,
    entry_date: str,
    entry_price: float,
    exit_date: str,
    atr_pct_at_signal: float | None,
    target_multiple: float,
    stop_multiple: float,
) -> dict[str, object]:
    if atr_pct_at_signal is None or atr_pct_at_signal <= 0.0:
        return {
            "target_price": None,
            "stop_price": None,
            "target_touched": None,
            "stop_touched": None,
            "target_before_stop": None,
            "time_to_target": None,
            "time_to_stop": None,
            "same_bar_ambiguity": False,
            "reason": "atr_pct_at_signal_unavailable",
        }
    target_distance = target_multiple * atr_pct_at_signal
    stop_distance = stop_multiple * atr_pct_at_signal
    target_price = entry_price * (1.0 + target_distance)
    stop_price = entry_price * (1.0 - stop_distance)
    data = validate_ohlcv(frame)
    window = data.loc[pd.Timestamp(entry_date) : pd.Timestamp(exit_date)]
    target_touched = False
    stop_touched = False
    target_before_stop = False
    time_to_target: int | None = None
    time_to_stop: int | None = None
    same_bar_ambiguity = False
    for offset, (_, bar) in enumerate(window.iterrows()):
        high = float(bar["High"])
        low = float(bar["Low"])
        target_hit = high >= target_price
        stop_hit = low <= stop_price
        if target_hit and time_to_target is None:
            target_touched = True
            time_to_target = offset
        if stop_hit and time_to_stop is None:
            stop_touched = True
            time_to_stop = offset
        if target_hit and stop_hit:
            same_bar_ambiguity = True
            target_before_stop = False
            break
        if stop_hit:
            target_before_stop = False
            break
        if target_hit:
            target_before_stop = True
            break
    return {
        "target_price": target_price,
        "stop_price": stop_price,
        "target_touched": target_touched,
        "stop_touched": stop_touched,
        "target_before_stop": target_before_stop,
        "time_to_target": time_to_target,
        "time_to_stop": time_to_stop,
        "same_bar_ambiguity": same_bar_ambiguity,
        "reason": "available",
    }


def _policy_outcomes(
    frame: pd.DataFrame,
    *,
    entry_date: str,
    entry_price: float,
    exit_date: str,
    atr_pct_at_signal: float | None,
    net_return: float,
) -> dict[str, object]:
    policies = {
        "baseline": (PROSPECTIVE_TIME_EXIT_BASELINE_POLICY_ID, 2.0, 1.0),
        "experimental": (PROSPECTIVE_TIME_EXIT_EXPERIMENTAL_POLICY_ID, 2.0, 1.25),
    }
    outputs: dict[str, object] = {}
    for prefix, (policy_id, target_multiple, stop_multiple) in policies.items():
        outcome = _policy_touch_outcome(
            frame,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date,
            atr_pct_at_signal=atr_pct_at_signal,
            target_multiple=target_multiple,
            stop_multiple=stop_multiple,
        )
        target_before_stop = outcome.get("target_before_stop")
        stop_touched = (
            bool(outcome.get("stop_touched")) if outcome.get("stop_touched") is not None else False
        )
        outputs[f"{prefix}_target_stop_policy_id"] = policy_id
        outputs[f"{prefix}_target_multiple"] = target_multiple
        outputs[f"{prefix}_stop_multiple"] = stop_multiple
        for key, value in outcome.items():
            outputs[f"{prefix}_{key}"] = value
        outputs[f"{prefix}_profitable_despite_failed_tbs"] = (
            bool(target_before_stop is False and net_return > 0.0)
            if target_before_stop is not None
            else None
        )
        outputs[f"{prefix}_early_adverse_recovery"] = (
            bool(stop_touched and net_return > 0.0)
            if outcome.get("stop_touched") is not None
            else None
        )
    return outputs


def _events_for_run(events: pd.DataFrame, run_id: str) -> pd.DataFrame:
    if events.empty:
        return events
    return events.loc[events["diagnostic_run_id"].astype(str) == run_id].copy()


def _event_signal_ids(events: pd.DataFrame, event_type: str) -> set[str]:
    if events.empty:
        return set()
    return {
        _safe_text(value)
        for value in events.loc[events["event_type"] == event_type, "signal_id"].tolist()
        if _safe_text(value)
    }


def _fill_pending_entries(
    root: Path,
    db_path: Path,
    run: ProspectiveTimeExitDiagnosticRun,
    events: pd.DataFrame,
) -> int:
    pending = _events_for_run(events, run.diagnostic_run_id)
    if pending.empty:
        return 0
    pending = pending.loc[pending["event_type"] == DIAGNOSTIC_EVENT_ENTRY_PENDING]
    filled_signal_ids = _event_signal_ids(events, DIAGNOSTIC_EVENT_ENTRY_FILLED)
    inserted = 0
    for _, event in pending.iterrows():
        signal_id = _safe_text(event.get("signal_id"))
        if not signal_id or signal_id in filled_signal_ids:
            continue
        ticker = _safe_text(event.get("ticker"))
        frame = _raw_frame(root, ticker)
        if frame is None:
            continue
        entry_date = _next_session_after(frame, _safe_text(event.get("market_as_of_date")))
        if entry_date is None:
            continue
        data = validate_ohlcv(frame)
        entry_price = _safe_float(data.at[entry_date, "Open"])
        if entry_price is None:
            continue
        payload = _event_payload(event)
        fill = append_time_exit_diagnostic_event(
            db_path,
            diagnostic_run_id=run.diagnostic_run_id,
            event_type=DIAGNOSTIC_EVENT_ENTRY_FILLED,
            market_as_of_date=entry_date.date().isoformat(),
            ticker=ticker,
            signal_id=signal_id,
            payload={
                **payload,
                "label": DIAGNOSTIC_ONLY_LABEL,
                "source_pending_event_id": _safe_text(event.get("event_id")),
                "entry_date": entry_date.date().isoformat(),
                "entry_price": entry_price,
                "fill_rule": "next_completed_session_open",
            },
            unique_suffix=_safe_text(event.get("event_id")),
        )
        inserted += int(fill.inserted)
    return inserted


def _mark_and_mature_positions(
    root: Path,
    db_path: Path,
    run: ProspectiveTimeExitDiagnosticRun,
    events: pd.DataFrame,
) -> tuple[int, int, int]:
    filled = _events_for_run(events, run.diagnostic_run_id)
    if filled.empty:
        return (0, 0, 0)
    filled = filled.loc[filled["event_type"] == DIAGNOSTIC_EVENT_ENTRY_FILLED]
    matured_signal_ids = _event_signal_ids(events, DIAGNOSTIC_EVENT_TIME_EXIT_MATURED)
    mark_inserted = 0
    matured_inserted = 0
    touch_inserted = 0
    for _, event in filled.iterrows():
        signal_id = _safe_text(event.get("signal_id"))
        if not signal_id:
            continue
        payload = _event_payload(event)
        ticker = _safe_text(event.get("ticker"))
        frame = _raw_frame(root, ticker)
        if frame is None:
            continue
        data = validate_ohlcv(frame)
        signal_as_of_date = _safe_text(payload.get("signal_as_of_date")) or _safe_text(
            payload.get("as_of_date")
        )
        entry_date = _safe_text(payload.get("entry_date"))
        if not signal_as_of_date or not entry_date:
            continue
        exit_date = _time_exit_date(frame, signal_as_of_date=signal_as_of_date, horizon=run.horizon)
        latest_date = pd.Timestamp(data.index.max())
        last_mark = min(latest_date, exit_date) if exit_date is not None else latest_date
        mark_dates = data.index[
            (data.index >= pd.Timestamp(entry_date)) & (data.index <= last_mark)
        ]
        entry_price = float(cast(float, payload["entry_price"]))
        for mark_date in mark_dates:
            stats = _path_stats(
                frame,
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=mark_date.date().isoformat(),
                cost_bps=DEFAULT_ROUND_TRIP_COST_BPS,
            )
            mark = append_time_exit_diagnostic_event(
                db_path,
                diagnostic_run_id=run.diagnostic_run_id,
                event_type=DIAGNOSTIC_EVENT_POSITION_MARKED,
                market_as_of_date=mark_date.date().isoformat(),
                ticker=ticker,
                signal_id=signal_id,
                payload={
                    **payload,
                    "label": DIAGNOSTIC_ONLY_LABEL,
                    "mark_date": mark_date.date().isoformat(),
                    "mark_return": stats["time_exit_gross_return"],
                    "mark_net_return": stats["time_exit_net_return"],
                    "MFE": stats["MFE"],
                    "MAE": stats["MAE"],
                },
                unique_suffix=f"{_safe_text(event.get('event_id'))}|{mark_date.date().isoformat()}",
            )
            mark_inserted += int(mark.inserted)
        if exit_date is None or latest_date < exit_date or signal_id in matured_signal_ids:
            continue
        stats = _path_stats(
            frame,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date.date().isoformat(),
            cost_bps=DEFAULT_ROUND_TRIP_COST_BPS,
        )
        atr_pct = _safe_float(payload.get("atr_pct_at_signal"))
        policy = _policy_outcomes(
            frame,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date.date().isoformat(),
            atr_pct_at_signal=atr_pct,
            net_return=float(cast(float, stats["time_exit_net_return"])),
        )
        maturity_payload = {
            **payload,
            **stats,
            **policy,
            "label": DIAGNOSTIC_ONLY_LABEL,
            "maturity_rule": "20_session_horizon_close",
            "diagnostic_result": "TIME_EXIT_POSITIVE"
            if bool(stats["time_exit_positive"])
            else "TIME_EXIT_NEGATIVE",
        }
        matured = append_time_exit_diagnostic_event(
            db_path,
            diagnostic_run_id=run.diagnostic_run_id,
            event_type=DIAGNOSTIC_EVENT_TIME_EXIT_MATURED,
            market_as_of_date=exit_date.date().isoformat(),
            ticker=ticker,
            signal_id=signal_id,
            payload=maturity_payload,
            unique_suffix=_safe_text(event.get("event_id")),
        )
        matured_inserted += int(matured.inserted)
        for event_type, key in (
            (DIAGNOSTIC_EVENT_TARGET_TOUCHED, "experimental_target_touched"),
            (DIAGNOSTIC_EVENT_STOP_TOUCHED, "experimental_stop_touched"),
        ):
            if not bool(policy.get(key)):
                continue
            touched = append_time_exit_diagnostic_event(
                db_path,
                diagnostic_run_id=run.diagnostic_run_id,
                event_type=event_type,
                market_as_of_date=exit_date.date().isoformat(),
                ticker=ticker,
                signal_id=signal_id,
                payload=maturity_payload,
                unique_suffix=f"{_safe_text(event.get('event_id'))}|{event_type}",
            )
            touch_inserted += int(touched.inserted)
    return mark_inserted, matured_inserted, touch_inserted


def _generation_dirs(root: Path) -> tuple[Path, ...]:
    base = ProjectPaths(root).artifacts / "signal_discovery"
    if not base.exists():
        return ()
    return tuple(sorted(path for path in base.iterdir() if path.is_dir()))


def _matching_rows(frames: dict[str, pd.DataFrame], hypothesis_id: str) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for name in ("candidates", "no_signal", "rejected"):
        frame = frames.get(name, pd.DataFrame())
        if frame.empty or "hypothesis_id" not in frame.columns:
            continue
        matched = frame.loc[frame["hypothesis_id"].astype(str) == hypothesis_id].copy()
        if not matched.empty:
            matched["source_frame"] = name
            rows.append(matched)
    if not rows:
        return pd.DataFrame()
    combined = pd.concat(rows, ignore_index=True, sort=False)
    if "scope" in combined.columns:
        combined = combined.loc[combined["scope"].astype(str) == PROSPECTIVE_TIME_EXIT_SCOPE]
    if "candidate_status" in combined.columns or "decision" in combined.columns:
        status = combined.get(
            "candidate_status",
            pd.Series("", index=combined.index, dtype=str),
        ).astype(str)
        decision = combined.get(
            "decision",
            pd.Series("", index=combined.index, dtype=str),
        ).astype(str)
        source = combined.get(
            "source_frame",
            pd.Series("", index=combined.index, dtype=str),
        ).astype(str)
        combined = combined.loc[
            status.isin(["RESEARCH_ONLY", "NO_SIGNAL"])
            | decision.isin(["NO_SIGNAL"])
            | source.eq("rejected")
        ]
    if "signal_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["signal_id"], keep="first")
    return combined


def _is_ood_rejected(row: pd.Series) -> bool:
    text = " ".join(
        _safe_text(row.get(column)).lower()
        for column in ("rejection_reason", "no_signal_reason", "ood_status", "next_required_event")
    )
    source = _safe_text(row.get("source_frame")).lower()
    return "ood" in text or source == "rejected"


def _row_payload(
    row: pd.Series, run: ProspectiveTimeExitDiagnosticRun, atr_pct: float | None
) -> dict[str, object]:
    signal_id = _safe_text(row.get("signal_id"))
    as_of_date = _safe_text(row.get("as_of_date"))
    ticker = _safe_text(row.get("ticker") or row.get("symbol")).upper()
    return {
        "label": DIAGNOSTIC_OBSERVATION_LABEL,
        "diagnostic_run_id": run.diagnostic_run_id,
        "schema_version": run.schema_version,
        "signal_id": signal_id,
        "signal_as_of_date": as_of_date,
        "as_of_date": as_of_date,
        "ticker": ticker,
        "hypothesis_id": _safe_text(row.get("hypothesis_id")),
        "model_id": _safe_text(row.get("model_id")),
        "model_family": _safe_text(row.get("model_family") or row.get("family")),
        "generation_id": _safe_text(row.get("generation_id") or row.get("generation")),
        "action": _safe_text(row.get("action")),
        "scope": _safe_text(row.get("scope") or row.get("product_class_scope")),
        "decision": _safe_text(row.get("decision")),
        "candidate_status": _safe_text(row.get("candidate_status")),
        "target_stop_policy_id": _safe_text(row.get("target_stop_policy_id")),
        "target_stop_policy_status": _safe_text(row.get("target_stop_policy_status")),
        "target_before_stop_probability": _safe_float(row.get("target_before_stop_probability")),
        "time_exit_positive_probability": _safe_float(row.get("time_exit_positive_probability")),
        "expected_time_exit_return": _safe_float(row.get("expected_time_exit_return")),
        "expected_time_exit_utility": _safe_float(row.get("expected_time_exit_utility")),
        "expected_return": _safe_float(row.get("expected_return")),
        "expected_mfe": _safe_float(row.get("expected_mfe")),
        "expected_mae": _safe_float(row.get("expected_mae")),
        "signal_score": _safe_float(row.get("signal_score")),
        "blocker_reason": _safe_text(row.get("rejection_reason") or row.get("no_signal_reason")),
        "ood_feature_rate": _safe_float(row.get("ood_feature_rate")),
        "robust_analog_label": _safe_text(
            row.get("robust_analog_support_label") or row.get("historical_analog_support")
        ),
        "footprint_summary": _safe_text(row.get("footprint_summary")),
        "atr_pct_at_signal": atr_pct,
        "diagnostic_notice": TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE,
        "not_live_actionable": True,
    }


def _ingest_signal_discovery_rows(
    root: Path,
    db_path: Path,
    run: ProspectiveTimeExitDiagnosticRun,
    events: pd.DataFrame,
) -> tuple[int, int, int, int]:
    observed_ids = _event_signal_ids(events, DIAGNOSTIC_EVENT_OBSERVATION_CREATED)
    rejected_ids = _event_signal_ids(events, DIAGNOSTIC_EVENT_OBSERVATION_REJECTED)
    backfill_ids = _event_signal_ids(events, DIAGNOSTIC_EVENT_BACKFILL_BLOCKED)
    atr_map = _load_feature_atr_map(root)
    observations = 0
    rejected = 0
    pending = 0
    backfilled = 0
    for generation_dir in _generation_dirs(root):
        frames = load_signal_discovery_frames(root, generation=generation_dir.name)
        rows = _matching_rows(frames, run.hypothesis_id)
        if rows.empty:
            continue
        for _, row in rows.iterrows():
            signal_id = _safe_text(row.get("signal_id"))
            as_of_date = _safe_text(row.get("as_of_date"))
            ticker = _safe_text(row.get("ticker") or row.get("symbol")).upper()
            if not signal_id or not as_of_date or not ticker:
                continue
            atr_pct = atr_map.get((as_of_date, ticker))
            payload = _row_payload(row, run, atr_pct)
            if as_of_date <= run.baseline_market_date:
                if signal_id in backfill_ids:
                    continue
                event = append_time_exit_diagnostic_event(
                    db_path,
                    diagnostic_run_id=run.diagnostic_run_id,
                    event_type=DIAGNOSTIC_EVENT_BACKFILL_BLOCKED,
                    market_as_of_date=as_of_date,
                    ticker=ticker,
                    signal_id=signal_id,
                    payload={
                        **payload,
                        "label": DIAGNOSTIC_ONLY_LABEL,
                        "reason": "DIAGNOSTIC_BACKFILL_BLOCKED",
                        "baseline_market_date": run.baseline_market_date,
                    },
                    unique_suffix=signal_id,
                )
                backfilled += int(event.inserted)
                continue
            if _is_ood_rejected(row):
                if signal_id in rejected_ids:
                    continue
                event = append_time_exit_diagnostic_event(
                    db_path,
                    diagnostic_run_id=run.diagnostic_run_id,
                    event_type=DIAGNOSTIC_EVENT_OBSERVATION_REJECTED,
                    market_as_of_date=as_of_date,
                    ticker=ticker,
                    signal_id=signal_id,
                    payload={
                        **payload,
                        "label": DIAGNOSTIC_ONLY_LABEL,
                        "reason": "diagnostic_observation_ood_rejected",
                    },
                    unique_suffix=signal_id,
                )
                rejected += int(event.inserted)
                continue
            if signal_id in observed_ids:
                continue
            observed = append_time_exit_diagnostic_event(
                db_path,
                diagnostic_run_id=run.diagnostic_run_id,
                event_type=DIAGNOSTIC_EVENT_OBSERVATION_CREATED,
                market_as_of_date=as_of_date,
                ticker=ticker,
                signal_id=signal_id,
                payload=payload,
                unique_suffix=signal_id,
            )
            observations += int(observed.inserted)
            pending_event = append_time_exit_diagnostic_event(
                db_path,
                diagnostic_run_id=run.diagnostic_run_id,
                event_type=DIAGNOSTIC_EVENT_ENTRY_PENDING,
                market_as_of_date=as_of_date,
                ticker=ticker,
                signal_id=signal_id,
                payload={
                    **payload,
                    "label": DIAGNOSTIC_ONLY_LABEL,
                    "entry_rule": "next_completed_session_open",
                    "horizon": run.horizon,
                    "planned_round_trip_cost_bps": DEFAULT_ROUND_TRIP_COST_BPS,
                },
                unique_suffix=signal_id,
            )
            pending += int(pending_event.inserted)
    return observations, rejected, pending, backfilled


def process_time_exit_diagnostic_update(root: str | Path) -> TimeExitDiagnosticUpdateResult:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    runs = _active_runs(paths.engine_db)
    if not runs:
        return TimeExitDiagnosticUpdateResult(
            diagnostic_run_id=None,
            events_inserted=0,
            observations_created=0,
            rejected_observations=0,
            pending_entries_created=0,
            entries_filled=0,
            position_marks_created=0,
            matured_outcomes=0,
            backfill_blocked=0,
            status="NO_ACTIVE_RUN",
        )
    run = runs[-1]
    before = list_time_exit_diagnostic_events(paths.engine_db)
    fills = _fill_pending_entries(project_root, paths.engine_db, run, before)
    after_fills = list_time_exit_diagnostic_events(paths.engine_db)
    marks, matured, touches = _mark_and_mature_positions(
        project_root,
        paths.engine_db,
        run,
        after_fills,
    )
    after_mature = list_time_exit_diagnostic_events(paths.engine_db)
    observations, rejected, pending, backfilled = _ingest_signal_discovery_rows(
        project_root,
        paths.engine_db,
        run,
        after_mature,
    )
    status = time_exit_diagnostic_status_frame(project_root)
    status_value: DiagnosticRunStatus | str = (
        _safe_text(status.iloc[0].get("status")) if not status.empty else run.status
    )
    return TimeExitDiagnosticUpdateResult(
        diagnostic_run_id=run.diagnostic_run_id,
        events_inserted=(
            fills + marks + matured + touches + observations + rejected + pending + backfilled
        ),
        observations_created=observations,
        rejected_observations=rejected,
        pending_entries_created=pending,
        entries_filled=fills,
        position_marks_created=marks,
        matured_outcomes=matured,
        backfill_blocked=backfilled,
        status=status_value,
    )


def _run_events(events: pd.DataFrame, run_id: str) -> pd.DataFrame:
    if events.empty:
        return events
    return events.loc[events["diagnostic_run_id"].astype(str) == run_id].copy()


def _months_between(first: str | None, last: str | None) -> int:
    if not first or not last:
        return 0
    start = pd.Timestamp(first)
    end = pd.Timestamp(last)
    return max(0, (end.year - start.year) * 12 + (end.month - start.month) + 1)


def _status_from_counts(
    *,
    matured_count: int,
    distinct_signal_dates: int,
    calendar_months: int,
    invalidated_count: int,
    run_status: DiagnosticRunStatus,
) -> DiagnosticRunStatus:
    if run_status in {"CLOSED", "INVALIDATED"}:
        return run_status
    if invalidated_count:
        return "INVALIDATED"
    if (
        matured_count >= STRONG_REVIEW_MATURED_MINIMUM
        and distinct_signal_dates >= STRONG_REVIEW_SIGNAL_DATES_MINIMUM
        and calendar_months >= STRONG_REVIEW_MONTHS_MINIMUM
    ):
        return "READY_FOR_REVIEW"
    if (
        matured_count >= EARLY_DIAGNOSTIC_MATURED_MINIMUM
        and distinct_signal_dates >= EARLY_DIAGNOSTIC_SIGNAL_DATES_MINIMUM
    ):
        return "EARLY_DIAGNOSTIC_AVAILABLE"
    if matured_count or distinct_signal_dates:
        return "COLLECTING"
    return run_status


def time_exit_diagnostic_events_frame(root: str | Path) -> pd.DataFrame:
    return list_time_exit_diagnostic_events(ProjectPaths(Path(root)).engine_db)


def time_exit_diagnostic_observations_frame(root: str | Path) -> pd.DataFrame:
    runs = list_time_exit_diagnostic_runs(ProjectPaths(Path(root)).engine_db)
    events = time_exit_diagnostic_events_frame(root)
    if not runs or events.empty:
        return pd.DataFrame()
    records: list[dict[str, object]] = []
    for run in runs:
        run_events = _run_events(events, run.diagnostic_run_id)
        if run_events.empty:
            continue
        filled_ids = _event_signal_ids(run_events, DIAGNOSTIC_EVENT_ENTRY_FILLED)
        matured_ids = _event_signal_ids(run_events, DIAGNOSTIC_EVENT_TIME_EXIT_MATURED)
        rejected_ids = _event_signal_ids(run_events, DIAGNOSTIC_EVENT_OBSERVATION_REJECTED)
        backfill_ids = _event_signal_ids(run_events, DIAGNOSTIC_EVENT_BACKFILL_BLOCKED)
        for _, event in run_events.loc[
            run_events["event_type"].isin(
                [
                    DIAGNOSTIC_EVENT_OBSERVATION_CREATED,
                    DIAGNOSTIC_EVENT_OBSERVATION_REJECTED,
                    DIAGNOSTIC_EVENT_BACKFILL_BLOCKED,
                ]
            )
        ].iterrows():
            signal_id = _safe_text(event.get("signal_id"))
            payload = _event_payload(event)
            status = "Diagnostic Pending Entry"
            if signal_id in matured_ids:
                status = "Diagnostic Matured"
            elif signal_id in filled_ids:
                status = "Diagnostic Open"
            if signal_id in rejected_ids:
                status = "Diagnostic Rejected"
            if signal_id in backfill_ids:
                status = "Diagnostic Backfill Blocked"
            records.append(
                {
                    "diagnostic_run_id": run.diagnostic_run_id,
                    "schema_version": run.schema_version,
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                    "observation_status": status,
                    "signal_id": signal_id,
                    "as_of_date": payload.get("as_of_date", event.get("market_as_of_date")),
                    "ticker": event.get("ticker"),
                    "hypothesis_id": payload.get("hypothesis_id", run.hypothesis_id),
                    "label": payload.get("label", DIAGNOSTIC_OBSERVATION_LABEL),
                    "target_before_stop_probability": payload.get("target_before_stop_probability"),
                    "time_exit_positive_probability": payload.get("time_exit_positive_probability"),
                    "expected_time_exit_return": payload.get("expected_time_exit_return"),
                    "expected_time_exit_utility": payload.get("expected_time_exit_utility"),
                    "blocker_reason": payload.get("blocker_reason"),
                    "reason": payload.get("reason", ""),
                    "diagnostic_notice": payload.get(
                        "diagnostic_notice",
                        TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE,
                    ),
                }
            )
    return pd.DataFrame(records)


def time_exit_diagnostic_matured_outcomes_frame(root: str | Path) -> pd.DataFrame:
    events = time_exit_diagnostic_events_frame(root)
    if events.empty:
        return pd.DataFrame()
    matured = events.loc[events["event_type"] == DIAGNOSTIC_EVENT_TIME_EXIT_MATURED].copy()
    records: list[dict[str, object]] = []
    for _, event in matured.iterrows():
        payload = _event_payload(event)
        records.append(
            {
                "diagnostic_run_id": event.get("diagnostic_run_id"),
                "event_id": event.get("event_id"),
                "signal_id": event.get("signal_id"),
                "ticker": event.get("ticker"),
                "as_of_date": payload.get("as_of_date"),
                "entry_date": payload.get("entry_date"),
                "entry_price": payload.get("entry_price"),
                "exit_date": payload.get("exit_date"),
                "exit_price": payload.get("exit_price"),
                "time_exit_net_return": payload.get("time_exit_net_return"),
                "time_exit_positive": payload.get("time_exit_positive"),
                "time_exit_utility": payload.get("time_exit_utility"),
                "MFE": payload.get("MFE"),
                "MAE": payload.get("MAE"),
                "time_to_max_favorable": payload.get("time_to_max_favorable"),
                "time_to_max_adverse": payload.get("time_to_max_adverse"),
                "baseline_target_touched": payload.get("baseline_target_touched"),
                "baseline_stop_touched": payload.get("baseline_stop_touched"),
                "baseline_target_before_stop": payload.get("baseline_target_before_stop"),
                "baseline_profitable_despite_failed_tbs": payload.get(
                    "baseline_profitable_despite_failed_tbs"
                ),
                "baseline_early_adverse_recovery": payload.get("baseline_early_adverse_recovery"),
                "experimental_target_touched": payload.get("experimental_target_touched"),
                "experimental_stop_touched": payload.get("experimental_stop_touched"),
                "experimental_target_before_stop": payload.get("experimental_target_before_stop"),
                "experimental_profitable_despite_failed_tbs": payload.get(
                    "experimental_profitable_despite_failed_tbs"
                ),
                "experimental_early_adverse_recovery": payload.get(
                    "experimental_early_adverse_recovery"
                ),
            }
        )
    return pd.DataFrame(records)


def time_exit_diagnostic_policy_comparison_frame(root: str | Path) -> pd.DataFrame:
    matured = time_exit_diagnostic_matured_outcomes_frame(root)
    if matured.empty:
        return pd.DataFrame(
            [
                {
                    "policy": "baseline",
                    "target_stop_policy_id": PROSPECTIVE_TIME_EXIT_BASELINE_POLICY_ID,
                    "matured_outcomes": 0,
                },
                {
                    "policy": "experimental",
                    "target_stop_policy_id": PROSPECTIVE_TIME_EXIT_EXPERIMENTAL_POLICY_ID,
                    "matured_outcomes": 0,
                },
            ]
        )
    rows: list[dict[str, object]] = []
    for prefix, policy_id in (
        ("baseline", PROSPECTIVE_TIME_EXIT_BASELINE_POLICY_ID),
        ("experimental", PROSPECTIVE_TIME_EXIT_EXPERIMENTAL_POLICY_ID),
    ):
        rows.append(
            {
                "policy": prefix,
                "target_stop_policy_id": policy_id,
                "matured_outcomes": len(matured),
                "target_touched_rate": matured[f"{prefix}_target_touched"].mean(),
                "stop_touched_rate": matured[f"{prefix}_stop_touched"].mean(),
                "target_before_stop_rate": matured[f"{prefix}_target_before_stop"].mean(),
                "profitable_despite_failed_tbs_rate": matured[
                    f"{prefix}_profitable_despite_failed_tbs"
                ].mean(),
                "early_adverse_recovery_rate": matured[f"{prefix}_early_adverse_recovery"].mean(),
            }
        )
    return pd.DataFrame(rows)


def time_exit_diagnostic_status_frame(root: str | Path) -> pd.DataFrame:
    db_path = ProjectPaths(Path(root)).engine_db
    runs = list_time_exit_diagnostic_runs(db_path)
    events = time_exit_diagnostic_events_frame(root)
    matured = time_exit_diagnostic_matured_outcomes_frame(root)
    rows: list[dict[str, object]] = []
    for run in runs:
        run_events = _run_events(events, run.diagnostic_run_id)
        run_matured = (
            matured.loc[matured["diagnostic_run_id"].astype(str) == run.diagnostic_run_id]
            if not matured.empty
            else matured
        )
        observations = time_exit_diagnostic_observations_frame(root)
        run_observations = (
            observations.loc[observations["diagnostic_run_id"].astype(str) == run.diagnostic_run_id]
            if not observations.empty
            else observations
        )
        signal_dates = (
            sorted(
                run_matured.get("as_of_date", pd.Series(dtype=str)).dropna().astype(str).unique()
            )
            if not run_matured.empty
            else []
        )
        matured_count = len(run_matured)
        positive = (
            int(run_matured.get("time_exit_positive", pd.Series(dtype=bool)).fillna(False).sum())
            if not run_matured.empty
            else 0
        )
        negative = matured_count - positive
        latest_processed = (
            max(run_events["market_as_of_date"].astype(str).tolist())
            if not run_events.empty
            else run.latest_processed_market_date
        )
        calendar_months = _months_between(
            signal_dates[0] if signal_dates else None, latest_processed
        )
        invalidated = (
            int(
                (
                    run_events.get("event_type", pd.Series(dtype=str))
                    == DIAGNOSTIC_EVENT_DATA_INVALIDATED
                ).sum()
            )
            if not run_events.empty
            else 0
        )
        status = _status_from_counts(
            matured_count=matured_count,
            distinct_signal_dates=len(signal_dates),
            calendar_months=calendar_months,
            invalidated_count=invalidated,
            run_status=run.status,
        )
        rows.append(
            {
                "diagnostic_run_id": run.diagnostic_run_id,
                "schema_version": run.schema_version,
                "status": status,
                "baseline_market_date": run.baseline_market_date,
                "first_eligible_future_as_of_date": run.first_eligible_future_as_of_date,
                "latest_processed_market_date": latest_processed,
                "hypothesis_id": run.hypothesis_id,
                "archetype": run.archetype,
                "action": run.action,
                "product_scope": run.product_scope,
                "horizon": run.horizon,
                "label_schema": run.label_schema,
                "feature_manifest_hash": run.feature_manifest_hash,
                "signal_discovery_generation_id": run.signal_discovery_generation_id,
                "observations_created": int(
                    (
                        run_events.get("event_type", pd.Series(dtype=str))
                        == DIAGNOSTIC_EVENT_OBSERVATION_CREATED
                    ).sum()
                )
                if not run_events.empty
                else 0,
                "rejected_observations": int(
                    (
                        run_events.get("event_type", pd.Series(dtype=str))
                        == DIAGNOSTIC_EVENT_OBSERVATION_REJECTED
                    ).sum()
                )
                if not run_events.empty
                else 0,
                "pending_entries": int(
                    (
                        run_observations.get("observation_status", pd.Series(dtype=str))
                        == "Diagnostic Pending Entry"
                    ).sum()
                )
                if not run_observations.empty
                else 0,
                "filled_entries": int(
                    (
                        run_events.get("event_type", pd.Series(dtype=str))
                        == DIAGNOSTIC_EVENT_ENTRY_FILLED
                    ).sum()
                )
                if not run_events.empty
                else 0,
                "open_diagnostic_positions": int(
                    (
                        run_observations.get("observation_status", pd.Series(dtype=str))
                        == "Diagnostic Open"
                    ).sum()
                )
                if not run_observations.empty
                else 0,
                "matured_outcomes": matured_count,
                "positive_time_exit_outcomes": positive,
                "negative_time_exit_outcomes": negative,
                "average_realized_time_exit_return": run_matured.get(
                    "time_exit_net_return", pd.Series(dtype=float)
                ).mean()
                if not run_matured.empty
                else None,
                "average_utility": run_matured.get(
                    "time_exit_utility", pd.Series(dtype=float)
                ).mean()
                if not run_matured.empty
                else None,
                "early_adverse_recovery_count": int(
                    run_matured.get(
                        "experimental_early_adverse_recovery",
                        pd.Series(dtype=bool),
                    )
                    .fillna(False)
                    .sum()
                )
                if not run_matured.empty
                else 0,
                "profitable_despite_failed_tbs_count": int(
                    run_matured.get(
                        "experimental_profitable_despite_failed_tbs",
                        pd.Series(dtype=bool),
                    )
                    .fillna(False)
                    .sum()
                )
                if not run_matured.empty
                else 0,
                "backfill_blocked_count": int(
                    (
                        run_events.get("event_type", pd.Series(dtype=str))
                        == DIAGNOSTIC_EVENT_BACKFILL_BLOCKED
                    ).sum()
                )
                if not run_events.empty
                else 0,
                "distinct_signal_dates": len(signal_dates),
                "calendar_months": calendar_months,
                "diagnostic_only": True,
                "promotion_eligible": False,
                "final_holdout_evidence": False,
                "notes": run.notes,
            }
        )
    return pd.DataFrame(rows)


def export_time_exit_diagnostic(root: str | Path, *, output: str | Path) -> tuple[Path, ...]:
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = {
        "time_exit_diagnostic_status": time_exit_diagnostic_status_frame(root),
        "time_exit_diagnostic_events": time_exit_diagnostic_events_frame(root),
        "time_exit_diagnostic_observations": time_exit_diagnostic_observations_frame(root),
        "time_exit_diagnostic_matured_outcomes": time_exit_diagnostic_matured_outcomes_frame(root),
        "time_exit_diagnostic_policy_comparison": time_exit_diagnostic_policy_comparison_frame(
            root
        ),
    }
    written: list[Path] = []
    for name, frame in frames.items():
        path = output_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        written.append(path)
    return tuple(written)
