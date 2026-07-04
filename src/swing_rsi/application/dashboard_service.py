from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlencode

import pandas as pd

from swing_rsi.application.datasets import discover_raw_datasets
from swing_rsi.application.footprint_attribution import signal_board_footprint_summary
from swing_rsi.config import ProjectPaths
from swing_rsi.engine.gates import (
    GATE_VALUE_NOT_APPLICABLE,
    GATE_VALUE_NOT_AVAILABLE,
    display_gate_value,
    gate_result_integrity_warning,
    promotion_eligibility,
)
from swing_rsi.engine.manifest import hash_file
from swing_rsi.engine.product_scope import (
    PRODUCT_CLASS_SCOPE_POOLED,
    PRODUCT_CLASS_SCOPES,
    build_product_class_scope_definitions,
    product_class_scope_for_role,
)
from swing_rsi.engine.registry import RegisteredModel
from swing_rsi.engine.registry import _row_to_model as registry_row_to_model
from swing_rsi.engine.signal_discovery import (
    load_signal_discovery_frames,
    signal_discovery_analog_robustness_frames,
    signal_discovery_blocked_analog_frames,
    signal_discovery_blocker_report_frames,
)
from swing_rsi.engine.time_exit_diagnostic import (
    DIAGNOSTIC_EVENT_BACKFILL_BLOCKED,
    DIAGNOSTIC_EVENT_ENTRY_FILLED,
    DIAGNOSTIC_EVENT_OBSERVATION_CREATED,
    DIAGNOSTIC_EVENT_OBSERVATION_REJECTED,
    DIAGNOSTIC_EVENT_TIME_EXIT_MATURED,
)
from swing_rsi.engine.time_exit_utility import (
    TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE,
)
from swing_rsi.engine.universe import UniverseConfig, load_universe_config, universe_to_frame_rows
from swing_rsi.settings import get_fmp_api_key

DEVELOPMENT_REPOSITORY = Path("/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev")
OPERATIONAL_REPOSITORY = Path("/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner")
FROZEN_OPERATIONAL_RUN_ID = "3493ee8ac37bf96475c362e1"
FROZEN_OPERATIONAL_MODEL_ID = "b93b2258c10aea5cef81d291"
FROZEN_OPERATIONAL_BASELINE_DATE = "2026-06-25"

EDGE_RESEARCH_ONLY = "RESEARCH ONLY"
EDGE_DEVELOPMENT_CANDIDATE = "DEVELOPMENT CANDIDATE"
EDGE_SHADOW_VALIDATION = "SHADOW VALIDATION"
EDGE_FINAL_HOLDOUT_QUALIFIED = "FINAL-HOLDOUT QUALIFIED"
EDGE_PROMOTED = "PROMOTED"

LIVE_ACTIONABLE = "LIVE ACTIONABLE"
SHADOW_ONLY = "SHADOW ONLY"
REJECTED = "REJECTED"
PENDING_ENTRY = "PENDING ENTRY"
OPEN_SHADOW_POSITION = "OPEN SHADOW POSITION"
CLOSED = "CLOSED"
RESEARCH_ONLY = "RESEARCH ONLY"
NOT_AVAILABLE = "Not available"

SIGNAL_FIRST_PAGE_TITLES: tuple[str, ...] = (
    "Signal Board",
    "Shadow Forward Test",
    "Model Edge Status",
    "Scanner Results",
    "Candidate Detail",
    "Product-Class Research",
    "Gate Audit",
    "Data and Universe",
    "Reports and Exports",
    "Engine Commands",
    "Legacy Baselines",
    "Developer Diagnostics",
)
REGIME_KMEANS_CACHE_SCHEMA_VERSION = "expanding_kmeans_regime_cache_v1"
REGIME_KMEANS_CACHE_STATUS_SCHEMA_VERSION = "expanding_kmeans_regime_cache_status_v1"
REGIME_CACHE_ALLOWED_STATUSES = {"HIT", "MISS", "PARTIAL_APPEND", "INVALIDATED"}
REGIME_CACHE_SUMMARY_COLUMNS = [
    "status",
    "cache_validity_status",
    "validity_reason",
    "cache_schema_version",
    "universe_snapshot_id",
    "feature_manifest_hash",
    "first_cached_date",
    "last_cached_date",
    "dates_covered",
    "rows_covered",
    "cached_dates_reused",
    "new_dates_computed",
    "kmeans_fits_avoided",
    "kmeans_fits_performed",
    "regime_runtime_seconds",
    "cache_age",
    "updated_at_utc",
    "cache_file",
    "status_file",
    "next_action",
    "forced_rebuild_method",
]


@dataclass(frozen=True)
class DashboardStartupState:
    cwd: Path
    development_repository: Path
    operational_repository: Path
    is_development_worktree: bool
    is_operational_repository: bool
    requires_confirmation: bool
    message: str


@dataclass(frozen=True)
class CommandSpec:
    key: str
    label: str
    argv: tuple[str, ...]
    mutates: bool
    requires_fmp: bool = False

    @property
    def command_text(self) -> str:
        return " ".join(self.argv)


@dataclass(frozen=True)
class CommandResult:
    command: str
    return_code: int
    stdout: str
    stderr: str
    log_path: Path


@dataclass(frozen=True)
class FmpSettingsUpdateResult:
    env_path: Path
    fmp_configured: bool
    base_url_configured: bool
    message: str


ALLOWED_COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "build-features",
        "build-features",
        (sys.executable, "-m", "swing_rsi.cli", "build-features"),
        mutates=True,
    ),
    CommandSpec(
        "universe-update",
        "universe-update",
        (sys.executable, "-m", "swing_rsi.cli", "universe-update"),
        mutates=True,
        requires_fmp=True,
    ),
    CommandSpec(
        "scan-include-challengers",
        "scanner review run",
        (sys.executable, "-m", "swing_rsi.cli", "scan", "--include-challengers"),
        mutates=True,
    ),
    CommandSpec(
        "final-holdout-status",
        "final-holdout-status",
        (sys.executable, "-m", "swing_rsi.cli", "final-holdout-status"),
        mutates=False,
    ),
    CommandSpec(
        "final-holdout-update",
        "final-holdout-update",
        (sys.executable, "-m", "swing_rsi.cli", "final-holdout-update"),
        mutates=True,
    ),
    CommandSpec(
        "model-audit-latest",
        "model-audit --generation latest",
        (sys.executable, "-m", "swing_rsi.cli", "model-audit", "--generation", "latest"),
        mutates=False,
    ),
)


def dashboard_startup_state(cwd: str | Path | None = None) -> DashboardStartupState:
    current = Path(cwd or Path.cwd()).resolve()
    development = DEVELOPMENT_REPOSITORY.resolve()
    operational = OPERATIONAL_REPOSITORY.resolve()
    is_development = current == development
    is_operational = current == operational
    if is_operational:
        message = "Blocked: this dashboard must not run from the frozen operational repository."
    elif is_development:
        message = "Development worktree confirmed."
    else:
        message = "Current working directory is not the configured development worktree."
    return DashboardStartupState(
        cwd=current,
        development_repository=development,
        operational_repository=operational,
        is_development_worktree=is_development,
        is_operational_repository=is_operational,
        requires_confirmation=not is_development and not is_operational,
        message=message,
    )


def default_universe_path(root: str | Path) -> Path:
    return Path(root) / "configs" / "universe" / "core.yaml"


def load_dashboard_universe(root: str | Path) -> UniverseConfig:
    return load_universe_config(default_universe_path(root))


def fmp_key_configured(root: str | Path) -> bool:
    try:
        get_fmp_api_key(Path(root))
    except RuntimeError:
        return False
    return True


def save_development_fmp_settings(
    root: str | Path,
    *,
    api_key: str,
    base_url: str = "https://financialmodelingprep.com/stable",
) -> FmpSettingsUpdateResult:
    project_root = Path(root).resolve()
    if project_root == OPERATIONAL_REPOSITORY.resolve():
        raise ValueError("FMP settings cannot be written from the operational repository.")
    if project_root != DEVELOPMENT_REPOSITORY.resolve():
        raise ValueError("FMP settings can only be saved in the configured development worktree.")
    cleaned_key = api_key.strip()
    cleaned_base_url = base_url.strip().rstrip("/")
    if not cleaned_key:
        raise ValueError("FMP API key is required.")
    if "\n" in cleaned_key or "\r" in cleaned_key:
        raise ValueError("FMP API key must be a single line.")
    if not cleaned_base_url.startswith("https://financialmodelingprep.com/"):
        raise ValueError("FMP base URL must use the Financial Modeling Prep HTTPS host.")
    if "apikey" in cleaned_base_url.lower():
        raise ValueError("FMP base URL must not contain credentials.")

    env_path = project_root / ".env"
    existing_lines: list[str] = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()
    values = {
        "FMP_API_KEY": cleaned_key,
        "FMP_BASE_URL": cleaned_base_url,
    }
    seen: set[str] = set()
    output_lines: list[str] = []
    for line in existing_lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in values:
            output_lines.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            output_lines.append(line)
    for key, value in values.items():
        if key not in seen:
            output_lines.append(f"{key}={value}")
    temp_path = env_path.with_name(".env.dashboard.tmp")
    temp_path.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8")
    temp_path.chmod(0o600)
    temp_path.replace(env_path)
    env_path.chmod(0o600)
    os.environ["FMP_API_KEY"] = cleaned_key
    os.environ["FMP_BASE_URL"] = cleaned_base_url
    return FmpSettingsUpdateResult(
        env_path=env_path,
        fmp_configured=True,
        base_url_configured=True,
        message="FMP settings saved for the development dashboard.",
    )


def _db_path(root: str | Path) -> Path:
    return ProjectPaths(Path(root)).engine_db


def _connect_readonly(db_path: Path) -> sqlite3.Connection | None:
    if not db_path.exists():
        return None
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _read_rows(db_path: Path, query: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
    connection = _connect_readonly(db_path)
    if connection is None:
        return []
    try:
        return list(connection.execute(query, params).fetchall())
    finally:
        connection.close()


def _read_rows_optional(
    db_path: Path,
    query: str,
    params: tuple[object, ...] = (),
) -> list[sqlite3.Row]:
    try:
        return _read_rows(db_path, query, params)
    except sqlite3.OperationalError:
        return []


def _json_loads(value: object, fallback: object) -> object:
    if value is None:
        return fallback
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return fallback


def _read_models(root: str | Path) -> list[RegisteredModel]:
    rows = _read_rows(_db_path(root), "SELECT * FROM models ORDER BY created_at_utc DESC, model_id")
    return [registry_row_to_model(row) for row in rows]


def registered_models_readonly(root: str | Path) -> list[RegisteredModel]:
    return _read_models(root)


def latest_generation_id(models: list[RegisteredModel]) -> str | None:
    if not models:
        return None
    return max(model.created_at_utc for model in models)


def _latest_models(models: list[RegisteredModel]) -> list[RegisteredModel]:
    latest = latest_generation_id(models)
    if latest is None:
        return []
    return [model for model in models if model.created_at_utc == latest]


def _safe_metric(model: RegisteredModel, *names: str) -> object:
    for name in names:
        if name in model.metrics:
            return model.metrics.get(name)
        if name in model.calibration_metrics:
            return model.calibration_metrics.get(name)
    return ""


def _model_scope(model: RegisteredModel | None) -> str:
    return "" if model is None else str(model.metrics.get("product_class_scope") or "POOLED")


def _safe_int(value: object) -> int:
    try:
        if bool(pd.isna(cast(Any, value))):
            return 0
    except (TypeError, ValueError):
        pass
    try:
        return int(float(cast(Any, value)))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: object) -> float | None:
    try:
        if bool(pd.isna(cast(Any, value))):
            return None
    except (TypeError, ValueError):
        pass
    try:
        numeric = float(cast(Any, value))
    except (TypeError, ValueError):
        return None
    return numeric if pd.notna(numeric) else None


def _display_value(value: object) -> object:
    if value in {"", None, GATE_VALUE_NOT_AVAILABLE, GATE_VALUE_NOT_APPLICABLE}:
        return NOT_AVAILABLE
    try:
        if bool(pd.isna(cast(Any, value))):
            return NOT_AVAILABLE
    except (TypeError, ValueError):
        pass
    return value


def _clean_text(value: object) -> str:
    if _display_value(value) == NOT_AVAILABLE:
        return ""
    return str(value).strip()


def _short_identifier(value: object, *, length: int) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return text[:length]


def _scope_label(value: object) -> str:
    text = _clean_text(value).upper()
    labels = {
        "ORDINARY": "ORD",
        "POOLED": "POOL",
        "INVERSE": "INV",
        "LEVERAGED_LONG": "LEV",
        "LEVERAGED_INVERSE": "LEV INV",
    }
    if text in labels:
        return labels[text]
    return text.replace("_", " ") if text else ""


def _direction_label(value: object) -> str:
    text = _clean_text(value).lower()
    if text.startswith("bull"):
        return "Bull"
    if text.startswith("bear"):
        return "Bear"
    return text.title() if text else ""


def _family_label(value: object) -> str:
    text = _clean_text(value).lower()
    labels = {
        "hist_gradient_boosting": "HGB",
        "extra_trees": "XT",
        "logistic_regression": "LOG",
        "naive_base_rate": "BASE",
    }
    if text in labels:
        return labels[text]
    parts = [part for part in text.replace("-", "_").split("_") if part]
    if not parts:
        return ""
    initials = "".join(part[0].upper() for part in parts)
    return initials[:4]


def _horizon_label(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    try:
        horizon = int(float(text))
    except ValueError:
        return text
    return f"{horizon}D"


def _model_display(
    *,
    model: RegisteredModel | None,
    row: pd.Series,
    model_id: object,
) -> str:
    short_id = _short_identifier(model_id, length=7)
    if not short_id:
        return NOT_AVAILABLE
    scope = _scope_label(row.get("product_class_scope") or _model_scope(model))
    direction = _direction_label(row.get("direction") or ("" if model is None else model.direction))
    family = _family_label(row.get("family") or ("" if model is None else model.family))
    horizon = _horizon_label(row.get("horizon") or ("" if model is None else model.horizon))
    prefix = " ".join(part for part in (scope, direction, family, horizon) if part)
    return f"{prefix} · {short_id}" if prefix else short_id


def _generation_display(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return NOT_AVAILABLE
    try:
        timestamp = pd.Timestamp(text)
    except (TypeError, ValueError):
        return f"Gen {_short_identifier(text, length=16)}"
    if pd.isna(timestamp):
        return NOT_AVAILABLE
    return f"Gen {timestamp.strftime('%Y-%m-%d %H:%M')}"


def _run_display(value: object) -> str:
    short_id = _short_identifier(value, length=8)
    return f"Dev Shadow Run · {short_id}" if short_id else NOT_AVAILABLE


def _event_display(*, signal_status: object, event_id: object) -> str:
    short_id = _short_identifier(event_id, length=8)
    if not short_id:
        return NOT_AVAILABLE
    status = _clean_text(signal_status).replace("_", " ").lower().title()
    return f"{status or 'Event'} · {short_id}"


def candidate_detail_url(
    *,
    scan_id: object,
    ticker: object,
    model_id: object,
    direction: object = "",
    run_id: object = "",
    event_id: object = "",
    status: object = "",
) -> str:
    params = {
        key: text
        for key, text in (
            ("scan_id", _clean_text(scan_id)),
            ("ticker", _clean_text(ticker)),
            ("model_id", _clean_text(model_id)),
            ("direction", _clean_text(direction)),
            ("run_id", _clean_text(run_id)),
            ("event_id", _clean_text(event_id)),
            ("status", _clean_text(status)),
        )
        if text
    }
    return f"/candidate-detail?{urlencode(params)}" if params else "/candidate-detail"


def _first_available(*values: object) -> object:
    for value in values:
        if _display_value(value) != NOT_AVAILABLE:
            return value
    return NOT_AVAILABLE


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y", "pass"}


def _model_maps(
    root: str | Path,
) -> tuple[dict[str, RegisteredModel], dict[str, dict[str, object]]]:
    models = {model.model_id: model for model in registered_models_readonly(root)}
    final_rows = _read_rows(
        _db_path(root),
        """
        SELECT fm.model_id, fm.run_id, fm.research_only, fm.development_gate_eligible,
               fr.status, fr.baseline_market_date, fr.first_eligible_future_signal_date
        FROM final_holdout_models fm
        JOIN final_holdout_runs fr ON fr.run_id = fm.run_id
        ORDER BY fr.created_at_utc DESC
        """,
    )
    final_map: dict[str, dict[str, object]] = {}
    for row in final_rows:
        final_map.setdefault(
            str(row["model_id"]),
            {
                "run_id": row["run_id"],
                "status": row["status"],
                "research_only": bool(row["research_only"]),
                "development_gate_eligible": bool(row["development_gate_eligible"]),
                "baseline_market_date": row["baseline_market_date"],
                "first_eligible_future_signal_date": row["first_eligible_future_signal_date"],
            },
        )
    return models, final_map


def edge_status_for_model(
    model: RegisteredModel | None,
    final_holdout: dict[str, object] | None = None,
) -> str:
    if model is None:
        return RESEARCH_ONLY
    eligibility = promotion_eligibility(model.gate_results)
    holdout_status = str(
        model.metrics.get("holdout_status") or model.metrics.get("final_holdout_status") or ""
    ).upper()
    if model.promoted_at_utc or (
        model.state == "CHAMPION" and eligibility.eligible and holdout_status == "FINAL_HOLDOUT"
    ):
        return EDGE_PROMOTED
    if holdout_status == "FINAL_HOLDOUT" and eligibility.eligible:
        return EDGE_FINAL_HOLDOUT_QUALIFIED
    if final_holdout and str(final_holdout.get("status", "")).upper() not in {
        "INVALIDATED",
        "CLOSED",
    }:
        return EDGE_SHADOW_VALIDATION
    if model.state in {"CANDIDATE", "CHALLENGER"}:
        return EDGE_DEVELOPMENT_CANDIDATE
    return EDGE_RESEARCH_ONLY


def _model_edge_status_map(root: str | Path) -> dict[str, str]:
    models, final_map = _model_maps(root)
    return {
        model_id: edge_status_for_model(model, final_map.get(model_id))
        for model_id, model in models.items()
    }


def _next_model_blocker(
    model: RegisteredModel | None, final_holdout: dict[str, object] | None
) -> str:
    if model is None:
        return "Model is not registered in local development state."
    eligibility = promotion_eligibility(model.gate_results)
    if eligibility.eligible and not final_holdout:
        return "Development-qualified. Needs prospective final-holdout evidence."
    failed = [
        gate.reason or gate.gate_name
        for gate in model.gate_results
        if gate.mandatory and gate.status != "PASS"
    ]
    if failed:
        return str(failed[0])
    if final_holdout:
        status = str(final_holdout.get("status") or "")
        return f"Prospective final-holdout status: {status}."
    return "No current blocker recorded."


def model_edge_status_frame(root: str | Path) -> pd.DataFrame:
    models, final_map = _model_maps(root)
    columns = [
        "model_id",
        "generation",
        "scope",
        "direction",
        "family",
        "edge_status",
        "selected_rows",
        "selected_rate",
        "portfolio_return",
        "max_drawdown",
        "brier_skill",
        "tbs_brier_skill",
        "expected_return_evidence",
        "mfe_status",
        "mae_status",
        "ood_status",
        "failed_development_gates",
        "failed_final_holdout_gates",
        "final_holdout_enrolled",
        "promotion_eligible",
        "next_blocker",
    ]
    rows: list[dict[str, object]] = []
    for model in models.values():
        eligibility = promotion_eligibility(model.gate_results)
        failed_development = [
            gate.gate_id
            for gate in model.gate_results
            if gate.mandatory and gate.status != "PASS" and "final_holdout" not in gate.gate_id
        ]
        failed_final = [
            gate.gate_id
            for gate in model.gate_results
            if gate.mandatory and gate.status != "PASS" and "final_holdout" in gate.gate_id
        ]
        final_holdout = final_map.get(model.model_id)
        edge_status = edge_status_for_model(model, final_holdout)
        rows.append(
            {
                "model_id": model.model_id,
                "generation": model.created_at_utc,
                "scope": _model_scope(model),
                "direction": model.direction,
                "family": model.family,
                "edge_status": edge_status,
                "selected_rows": _safe_metric(
                    model, "selected_holdout_samples", "selected_samples"
                ),
                "selected_rate": _safe_metric(model, "selected_observation_rate"),
                "portfolio_return": _safe_metric(model, "portfolio_total_return"),
                "max_drawdown": _safe_metric(model, "portfolio_max_drawdown"),
                "brier_skill": _safe_metric(model, "brier_skill_score"),
                "tbs_brier_skill": _safe_metric(
                    model,
                    "target_before_stop_brier_skill_score",
                    "target_before_stop_development_holdout_brier_skill_score",
                ),
                "expected_return_evidence": _safe_metric(
                    model, "holdout_mean_return_lcb_90", "mean_selected_return"
                ),
                "mfe_status": _safe_metric(
                    model,
                    "mfe_path_head_capability_state",
                    "mfe_holdout_ood_status",
                    "mfe_ood_status",
                ),
                "mae_status": _safe_metric(
                    model,
                    "mae_path_head_capability_state",
                    "mae_holdout_ood_status",
                    "mae_ood_status",
                ),
                "ood_status": _safe_metric(model, "prediction_ood_status", "ood_status"),
                "failed_development_gates": "; ".join(failed_development[:8]),
                "failed_final_holdout_gates": "; ".join(failed_final[:8]),
                "final_holdout_enrolled": "yes" if final_holdout else "no",
                "promotion_eligible": eligibility.eligible,
                "next_blocker": _next_model_blocker(model, final_holdout),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _signal_event_keys(events: pd.DataFrame) -> dict[str, dict[str, pd.Series]]:
    signal_events = {
        "pending": events.loc[
            events["event_type"].isin(["ENTRY_PENDING", "FINAL_HOLDOUT_ENTRY_PENDING"])
        ]
        if not events.empty
        else events,
        "filled": events.loc[
            events["event_type"].isin(["ENTRY_FILLED", "FINAL_HOLDOUT_ENTRY_FILLED"])
        ]
        if not events.empty
        else events,
        "closed": events.loc[
            events["event_type"].isin(
                [
                    "EXIT_FILLED",
                    "POSITION_EXPIRED",
                    "POSITION_CANCELED",
                    "FINAL_HOLDOUT_EXIT_FILLED",
                    "FINAL_HOLDOUT_POSITION_EXPIRED",
                ]
            )
        ]
        if not events.empty
        else events,
    }
    maps: dict[str, dict[str, pd.Series]] = {"pending": {}, "filled": {}, "closed": {}}
    for group, frame in signal_events.items():
        for _, event in frame.iterrows():
            key = _event_match_key(event)
            maps[group][key] = event
    return maps


def _event_match_key(event: pd.Series) -> str:
    return "|".join(
        [
            str(event.get("scanner_snapshot_id", "")),
            str(event.get("market_as_of_date", "")),
            str(event.get("ticker", "")),
            str(event.get("direction", "")),
            str(event.get("model_id", "")),
        ]
    )


def _row_match_key(row: pd.Series) -> str:
    return "|".join(
        [
            str(row.get("scan_id", row.get("scanner_snapshot_id", ""))),
            str(row.get("as_of_date", row.get("market_as_of_date", ""))),
            str(row.get("ticker", "")),
            str(row.get("direction", "")),
            str(row.get("model_id", "")),
        ]
    )


def _scanner_rows_from_signal_events(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if events.empty:
        return pd.DataFrame()
    signal_events = events.loc[
        events["event_type"].isin(
            [
                "SIGNAL_CREATED",
                "SIGNAL_REJECTED",
                "FINAL_HOLDOUT_SIGNAL_CREATED",
                "FINAL_HOLDOUT_SIGNAL_REJECTED",
            ]
        )
    ]
    for _, event in signal_events.iterrows():
        payload = event.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        scanner_row = payload.get("scanner_row")
        base = scanner_row if isinstance(scanner_row, dict) else {}
        row = dict(base)
        row.setdefault("scan_id", event.get("scanner_snapshot_id", ""))
        row.setdefault("as_of_date", event.get("market_as_of_date", ""))
        row.setdefault("ticker", event.get("ticker", ""))
        row.setdefault("direction", event.get("direction", ""))
        row.setdefault("model_id", event.get("model_id", ""))
        row.setdefault("feature_snapshot_hash", event.get("feature_snapshot_hash", ""))
        row["event_id"] = event.get("event_id", "")
        row["event_type"] = event.get("event_type", "")
        row["event_time_utc"] = event.get("event_time_utc", "")
        row["run_id"] = payload.get("run_id", "")
        row["mode"] = payload.get("mode", "")
        row["not_live_trade_recommendation"] = payload.get("not_live_trade_recommendation", "")
        row["exclusion_reason"] = payload.get("exclusion_reason") or row.get("exclusion_reason", "")
        rows.append(row)
    return pd.DataFrame(rows)


def _scanner_rows_with_events(root: str | Path) -> pd.DataFrame:
    events = forward_events_frame(root, final_holdout_only=None)
    event_rows = _scanner_rows_from_signal_events(events)
    scanner_rows = scanner_rows_frame(root)
    if event_rows.empty:
        return scanner_rows
    if scanner_rows.empty:
        return event_rows
    combined = pd.concat([event_rows, scanner_rows], ignore_index=True, sort=False)
    keys = combined.apply(_row_match_key, axis=1)
    return combined.loc[~keys.duplicated()].reset_index(drop=True)


def _candidate_classification(
    *,
    row: pd.Series,
    edge_status: str,
    gate_eligible: bool,
    shadow_context: bool,
    lifecycle_status: str,
) -> tuple[str, str]:
    candidate_status = _clean_text(row.get("candidate_status")).upper()
    rejection_reason = _clean_text(row.get("exclusion_reason"))
    if lifecycle_status in {PENDING_ENTRY, OPEN_SHADOW_POSITION, CLOSED}:
        return lifecycle_status, SHADOW_ONLY
    if candidate_status == "REJECTED" or rejection_reason:
        return REJECTED, REJECTED
    if (
        candidate_status == "ACTIONABLE_PAPER_CANDIDATE"
        and edge_status == EDGE_PROMOTED
        and gate_eligible
    ):
        return LIVE_ACTIONABLE, LIVE_ACTIONABLE
    if shadow_context or edge_status in {EDGE_SHADOW_VALIDATION, EDGE_FINAL_HOLDOUT_QUALIFIED}:
        return SHADOW_ONLY, SHADOW_ONLY
    return RESEARCH_ONLY, RESEARCH_ONLY


def _lifecycle_status(row: pd.Series, event_maps: dict[str, dict[str, pd.Series]]) -> str:
    key = _row_match_key(row)
    if key in event_maps["closed"]:
        return CLOSED
    if key in event_maps["filled"]:
        return OPEN_SHADOW_POSITION
    if key in event_maps["pending"]:
        return PENDING_ENTRY
    return ""


def _event_payload_value(event: pd.Series | None, *names: str) -> object:
    if event is None:
        return NOT_AVAILABLE
    payload = event.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    for name in names:
        if name in payload:
            return payload[name]
    return NOT_AVAILABLE


def _event_value(event: pd.Series | None, name: str) -> object:
    if event is None:
        return NOT_AVAILABLE
    return event.get(name, NOT_AVAILABLE)


def _first_event(*events: pd.Series | None) -> pd.Series | None:
    return next((event for event in events if event is not None), None)


def _signal_next_required_event(
    classification: str,
    lifecycle_status: str,
    rejection_reason: object,
) -> str:
    if lifecycle_status == PENDING_ENTRY:
        return "Pending entry waits for next session open."
    if lifecycle_status == OPEN_SHADOW_POSITION:
        return "Open position waits for target, stop, or time exit."
    if lifecycle_status == CLOSED:
        return "Outcome matured; review forward evidence."
    if classification == LIVE_ACTIONABLE:
        return "Review/export. No brokerage order is placed by this dashboard."
    if classification == SHADOW_ONLY:
        return "Collect prospective shadow evidence; not a live recommendation."
    if classification == REJECTED:
        reason = _clean_text(rejection_reason)
        return f"Rejected: {reason}" if reason else "Rejected; no entry."
    return "Development research review only; not eligible for live action."


def _why_shadow_only(classification: str, lifecycle_status: str) -> str:
    if lifecycle_status == PENDING_ENTRY:
        return (
            "This row is waiting for the next eligible session open. "
            "It is not a live trade recommendation."
        )
    if lifecycle_status == OPEN_SHADOW_POSITION:
        return (
            "This shadow position is waiting for target, stop, or time exit. "
            "It is not a live trade recommendation."
        )
    if lifecycle_status == CLOSED:
        return "This row is closed prospective evidence, not a live trade recommendation."
    if classification == SHADOW_ONLY:
        return "Shadow rows are paper-validation events used to collect prospective evidence."
    return NOT_AVAILABLE


def signal_discovery_generation_frames(
    root: str | Path, *, include_blocked_analogs: bool = False
) -> dict[str, pd.DataFrame]:
    frames = load_signal_discovery_frames(root)
    if include_blocked_analogs:
        blocked_frames = signal_discovery_blocked_analog_frames(root)
        frames.update(blocked_frames)
        frames.update(signal_discovery_analog_robustness_frames(root))
    return frames


def signal_discovery_summary_frame(root: str | Path) -> pd.DataFrame:
    return signal_discovery_generation_frames(root).get("summary", pd.DataFrame())


def signal_discovery_candidates_frame(root: str | Path) -> pd.DataFrame:
    return signal_discovery_generation_frames(root).get("candidates", pd.DataFrame())


def signal_discovery_blocker_frames(root: str | Path) -> dict[str, pd.DataFrame]:
    return signal_discovery_blocker_report_frames(root)


def _records_json_by_signal(frame: pd.DataFrame) -> dict[str, str]:
    if frame.empty or "signal_id" not in frame.columns:
        return {}
    records: dict[str, str] = {}
    for signal_id, group in frame.groupby(frame["signal_id"].astype(str), sort=False):
        records[str(signal_id)] = json.dumps(group.to_dict(orient="records"), default=str)
    return records


def _single_record_json_by_signal(frame: pd.DataFrame) -> dict[str, str]:
    if frame.empty:
        return {}
    signal_column = "signal_id" if "signal_id" in frame.columns else "target_signal_id"
    if signal_column not in frame.columns:
        return {}
    records: dict[str, str] = {}
    for _, row in frame.iterrows():
        records[str(row.get(signal_column, ""))] = json.dumps(row.to_dict(), default=str)
    return records


def _blocked_analog_support_by_signal(summary: pd.DataFrame) -> dict[str, str]:
    if summary.empty or "target_signal_id" not in summary.columns:
        return {}
    output: dict[str, str] = {}
    for _, row in summary.iterrows():
        signal_id = str(row.get("target_signal_id", ""))
        label = _display_value(row.get("analog_support_label"))
        count = _display_value(row.get("analog_count"))
        average = _display_value(row.get("average_forward_return"))
        output[signal_id] = (
            f"{label} blocked-row analog support from {count} analogs; "
            f"average forward return {average}; explanatory only."
        )
    return output


def _analog_robustness_support_by_signal(robustness: pd.DataFrame) -> dict[str, str]:
    if robustness.empty or "target_signal_id" not in robustness.columns:
        return {}
    output: dict[str, str] = {}
    for _, row in robustness.iterrows():
        signal_id = str(row.get("target_signal_id", ""))
        status = str(_display_value(row.get("analog_compact_status")))
        explanation = str(_display_value(row.get("robustness_explanation")))
        output[signal_id] = f"{status}. {explanation}".strip()
    return output


def _analog_robustness_status_by_signal(robustness: pd.DataFrame) -> dict[str, str]:
    if robustness.empty or "target_signal_id" not in robustness.columns:
        return {}
    output: dict[str, str] = {}
    for _, row in robustness.iterrows():
        signal_id = str(row.get("target_signal_id", ""))
        output[signal_id] = str(_display_value(row.get("analog_compact_status")))
    return output


def _calibration_scope_for_candidate(row: pd.Series) -> str:
    scope = _clean_text(row.get("product_class_scope")) or _clean_text(row.get("scope"))
    return scope if scope else PRODUCT_CLASS_SCOPE_POOLED


def _calibration_candidate_slice(frame: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    hypothesis_id = _clean_text(row.get("hypothesis_id"))
    family = _clean_text(row.get("model_family")) or _clean_text(row.get("family"))
    scope = _calibration_scope_for_candidate(row)
    if "hypothesis_id" in output.columns and hypothesis_id:
        output = output.loc[output["hypothesis_id"].astype(str).eq(hypothesis_id)]
    if "model_family" in output.columns and family:
        output = output.loc[output["model_family"].astype(str).eq(family)]
    if "product_scope" not in output.columns or output.empty:
        return output
    scoped = output.loc[output["product_scope"].astype(str).eq(scope)]
    if not scoped.empty:
        return scoped
    pooled = output.loc[output["product_scope"].astype(str).eq(PRODUCT_CLASS_SCOPE_POOLED)]
    return pooled if not pooled.empty else output


def _calibration_records_json(frame: pd.DataFrame, row: pd.Series) -> str:
    sliced = _calibration_candidate_slice(frame, row)
    if sliced.empty:
        return ""
    return json.dumps(sliced.to_dict(orient="records"), default=str)


def _calibration_single_record_json(frame: pd.DataFrame, row: pd.Series) -> str:
    sliced = _calibration_candidate_slice(frame, row)
    if sliced.empty:
        return ""
    return json.dumps(sliced.iloc[0].to_dict(), default=str)


def _policy_records_json(frame: pd.DataFrame, row: pd.Series) -> str:
    if frame.empty:
        return ""
    output = frame.copy()
    policy_id = _clean_text(row.get("target_stop_policy_id"))
    if policy_id and "target_stop_policy_id" in output.columns:
        scoped = output.loc[output["target_stop_policy_id"].astype(str).eq(policy_id)]
        if not scoped.empty:
            output = scoped
    return json.dumps(output.to_dict(orient="records"), default=str)


def _policy_exact_row_json(frame: pd.DataFrame, row: pd.Series) -> str:
    if frame.empty:
        return ""
    output = frame.copy()
    for candidate_column, frame_column in (
        ("target_stop_policy_id", "target_stop_policy_id"),
        ("ticker", "symbol"),
        ("as_of_date", "Date"),
    ):
        value = _clean_text(row.get(candidate_column))
        if value and frame_column in output.columns:
            output = output.loc[output[frame_column].astype(str).eq(value)]
    if output.empty:
        return ""
    return json.dumps(output.head(25).to_dict(orient="records"), default=str)


def _weighted_calibration_base_rate(frame: pd.DataFrame) -> float | None:
    if frame.empty or not {"tbs_base_rate", "calibration_row_count"}.issubset(frame.columns):
        return None
    rates = pd.to_numeric(frame["tbs_base_rate"], errors="coerce")
    counts = pd.to_numeric(frame["calibration_row_count"], errors="coerce").fillna(0.0)
    valid = rates.notna() & counts.gt(0.0)
    if not valid.any():
        return None
    return float((rates.loc[valid] * counts.loc[valid]).sum() / counts.loc[valid].sum())


def _same_archetype_calibration_base_rate(summary: pd.DataFrame, row: pd.Series) -> float | None:
    if summary.empty:
        return None
    frame = summary.copy()
    archetype_id = _clean_text(row.get("archetype_id"))
    horizon = _clean_text(row.get("horizon"))
    direction = _clean_text(row.get("direction"))
    action = "BUY" if direction == "Bullish" else "SELL_SHORT" if direction == "Bearish" else ""
    if "product_scope" in frame.columns:
        pooled = frame.loc[frame["product_scope"].astype(str).eq(PRODUCT_CLASS_SCOPE_POOLED)]
        frame = pooled if not pooled.empty else frame
    if "archetype_id" in frame.columns and archetype_id:
        frame = frame.loc[frame["archetype_id"].astype(str).eq(archetype_id)]
    if "horizon" in frame.columns and horizon:
        frame = frame.loc[frame["horizon"].astype(str).eq(horizon)]
    if "action" in frame.columns and action:
        frame = frame.loc[frame["action"].astype(str).eq(action)]
    return _weighted_calibration_base_rate(frame)


def _same_scope_calibration_base_rate(summary: pd.DataFrame, row: pd.Series) -> float | None:
    if summary.empty:
        return None
    frame = summary.copy()
    scope = _calibration_scope_for_candidate(row)
    horizon = _clean_text(row.get("horizon"))
    direction = _clean_text(row.get("direction"))
    action = "BUY" if direction == "Bullish" else "SELL_SHORT" if direction == "Bearish" else ""
    if "product_scope" in frame.columns:
        scoped = frame.loc[frame["product_scope"].astype(str).eq(scope)]
        frame = (
            scoped
            if not scoped.empty
            else frame.loc[frame["product_scope"].astype(str).eq(PRODUCT_CLASS_SCOPE_POOLED)]
        )
    if "horizon" in frame.columns and horizon:
        frame = frame.loc[frame["horizon"].astype(str).eq(horizon)]
    if "action" in frame.columns and action:
        frame = frame.loc[frame["action"].astype(str).eq(action)]
    return _weighted_calibration_base_rate(frame)


def _calibration_status(summary: pd.DataFrame, row: pd.Series) -> str:
    sliced = _calibration_candidate_slice(summary, row)
    if sliced.empty:
        return "Not available"
    return str(_display_value(sliced.iloc[0].get("status", "Not available")))


def _calibration_blocker_assessment(summary: pd.DataFrame, row: pd.Series) -> str:
    reason = (
        _clean_text(row.get("no_signal_reason")) or _clean_text(row.get("rejection_reason"))
    ).lower()
    if "target_before_stop" not in reason:
        return "Not a TBS blocker; calibration diagnostic shown for context."
    sliced = _calibration_candidate_slice(summary, row)
    if sliced.empty:
        return "INSUFFICIENT_EVIDENCE_DIAGNOSTIC_ONLY"
    status = str(sliced.iloc[0].get("status", ""))
    if status != "AVAILABLE":
        return "INSUFFICIENT_EVIDENCE_DIAGNOSTIC_ONLY"
    probability = _safe_float(row.get("target_before_stop_probability"))
    base_rate = _safe_float(sliced.iloc[0].get("tbs_base_rate"))
    if probability is not None and probability < 0.50 and (base_rate is None or base_rate < 0.50):
        return "VALID_BLOCKER_DIAGNOSTIC_ONLY"
    return "REVIEW_REQUIRED_DIAGNOSTIC_ONLY"


def _signal_discovery_scanner_rows(root: str | Path) -> pd.DataFrame:
    frames = signal_discovery_generation_frames(root)
    candidates = frames.get("candidates", pd.DataFrame())
    if candidates.empty:
        return pd.DataFrame()
    blocked_frames = signal_discovery_blocked_analog_frames(root)
    robustness_frames = signal_discovery_analog_robustness_frames(root)
    blocked_analogs_by_signal = _records_json_by_signal(
        blocked_frames.get("blocked_row_analogs", pd.DataFrame()).rename(
            columns={"target_signal_id": "signal_id"}
        )
    )
    blocked_summary = blocked_frames.get("blocked_row_analog_summary", pd.DataFrame())
    robustness = robustness_frames.get("analog_robustness", pd.DataFrame())
    depth_comparison = robustness_frames.get("analog_depth_comparison", pd.DataFrame())
    caution_flags = robustness_frames.get("analog_caution_flags", pd.DataFrame())
    calibration_summary = frames.get("calibration_summary", pd.DataFrame())
    diagnostic_thresholds = frames.get("diagnostic_thresholds", pd.DataFrame())
    probability_buckets = frames.get("probability_buckets", pd.DataFrame())
    policy_registry = frames.get("target_stop_policy_registry", pd.DataFrame())
    policy_selection = frames.get("calibration_selection", pd.DataFrame())
    policy_comparison = frames.get(
        "sector_rotation_buy_ordinary_policy_comparison",
        pd.DataFrame(),
    )
    derived_outcomes = frames.get("derived_policy_outcomes", pd.DataFrame())
    signal_policy_comparison = frames.get(
        "signal_discovery_policy_comparison",
        pd.DataFrame(),
    )
    time_exit_labels = frames.get("time_exit_utility_labels", pd.DataFrame())
    time_exit_summary = frames.get("time_exit_utility_calibration_summary", pd.DataFrame())
    time_exit_signal_rows = frames.get("time_exit_utility_signal_rows", pd.DataFrame())
    time_exit_policy_comparison = frames.get(
        "time_exit_utility_policy_comparison",
        pd.DataFrame(),
    )
    diagnostic_observations = time_exit_diagnostic_observations_frame(root)
    diagnostic_matured = time_exit_diagnostic_matured_outcomes_frame(root)
    diagnostic_observation_by_signal = _single_record_json_by_signal(diagnostic_observations)
    diagnostic_matured_by_signal = _single_record_json_by_signal(diagnostic_matured)
    blocked_summary_by_signal = _single_record_json_by_signal(blocked_summary)
    blocked_support_by_signal = _blocked_analog_support_by_signal(blocked_summary)
    robustness_by_signal = _single_record_json_by_signal(robustness)
    robustness_support_by_signal = _analog_robustness_support_by_signal(robustness)
    robustness_status_by_signal = _analog_robustness_status_by_signal(robustness)
    depth_by_signal = _records_json_by_signal(
        depth_comparison.rename(columns={"target_signal_id": "signal_id"})
    )
    flags_by_signal = _records_json_by_signal(
        caution_flags.rename(columns={"target_signal_id": "signal_id"})
    )
    blocked_footprint_by_signal = (
        blocked_summary.set_index("target_signal_id")["analog_footprint_summary"]
        .astype(str)
        .to_dict()
        if not blocked_summary.empty and "target_signal_id" in blocked_summary.columns
        else {}
    )
    analogs_by_signal = _records_json_by_signal(frames.get("historical_analogs", pd.DataFrame()))
    evidence_by_signal = _records_json_by_signal(frames.get("footprint_evidence", pd.DataFrame()))
    rows: list[dict[str, object]] = []
    for _, row in candidates.iterrows():
        signal_id = str(_display_value(row.get("signal_id")))
        decision = _clean_text(row.get("decision"))
        candidate_status = _clean_text(row.get("candidate_status")) or RESEARCH_ONLY
        historical_analogs = analogs_by_signal.get(
            signal_id,
            blocked_analogs_by_signal.get(
                signal_id,
                _display_value(row.get("historical_analog_support")),
            ),
        )
        analog_support = blocked_support_by_signal.get(
            signal_id, _display_value(row.get("historical_analog_support"))
        )
        robust_support = robustness_support_by_signal.get(signal_id, analog_support)
        footprint_summary = blocked_footprint_by_signal.get(
            signal_id, _display_value(row.get("footprint_summary"))
        )
        rows.append(
            {
                "signal_id": signal_id,
                "scan_id": _display_value(row.get("generation_id")),
                "as_of_date": _display_value(row.get("as_of_date")),
                "ticker": _display_value(row.get("ticker")),
                "direction": _display_value(row.get("direction")),
                "action": _display_value(row.get("action")),
                "archetype": _display_value(row.get("archetype")),
                "archetype_id": _display_value(row.get("archetype_id")),
                "hypothesis_id": _display_value(row.get("hypothesis_id")),
                "signal_score": _display_value(row.get("signal_score")),
                "scope": _display_value(row.get("scope")),
                "model": _display_value(row.get("model_id")),
                "model_id": _display_value(row.get("model_id")),
                "family": _display_value(row.get("model_family")),
                "target_stop_policy": _display_value(row.get("target_stop_policy_display")),
                "target_stop_policy_display": _display_value(row.get("target_stop_policy_display")),
                "target_stop_policy_id": _display_value(row.get("target_stop_policy_id")),
                "target_stop_policy_name": _display_value(row.get("target_stop_policy_name")),
                "target_stop_policy_status": _display_value(row.get("target_stop_policy_status")),
                "target_stop_policy_hash": _display_value(row.get("target_stop_policy_hash")),
                "target_stop_policy_target_multiple": _display_value(
                    row.get("target_stop_policy_target_multiple")
                ),
                "target_stop_policy_stop_multiple": _display_value(
                    row.get("target_stop_policy_stop_multiple")
                ),
                "target_stop_policy_notice": _display_value(row.get("target_stop_policy_notice")),
                "target_stop_policy_registry_json": _policy_records_json(
                    policy_registry,
                    row,
                ),
                "target_stop_policy_selection_evidence": json.dumps(
                    policy_selection.to_dict(orient="records"),
                    default=str,
                )
                if not policy_selection.empty
                else "",
                "target_stop_policy_comparison_json": json.dumps(
                    policy_comparison.to_dict(orient="records"),
                    default=str,
                )
                if not policy_comparison.empty
                else "",
                "derived_policy_outcome_json": _policy_exact_row_json(
                    derived_outcomes,
                    row,
                ),
                "signal_discovery_policy_comparison_json": _policy_records_json(
                    signal_policy_comparison,
                    row,
                ),
                "generation": _display_value(row.get("generation_id")),
                "feature_snapshot_hash": _display_value(row.get("feature_snapshot_hash")),
                "row_product_class_role": _display_value(row.get("row_product_class_role")),
                "horizon": _display_value(row.get("horizon")),
                "liquidity_score": _display_value(row.get("liquidity_score")),
                "composite_utility_score": _display_value(row.get("risk_adjusted_utility")),
                "edge_status": _display_value(row.get("edge_status")),
                "status": candidate_status,
                "candidate_classification": candidate_status,
                "probability": _display_value(row.get("probability")),
                "expected_return": _display_value(row.get("expected_return")),
                "expected_mfe": _display_value(row.get("expected_mfe")),
                "expected_mae": _display_value(row.get("expected_mae")),
                "target_before_stop_probability": _display_value(
                    row.get("target_before_stop_probability")
                ),
                "time_exit_label_schema_version": _display_value(
                    row.get("time_exit_label_schema_version")
                ),
                "time_exit_label_notice": _display_value(row.get("time_exit_label_notice")),
                "time_exit_positive_probability": _display_value(
                    row.get("time_exit_positive_probability")
                ),
                "expected_time_exit_return": _display_value(row.get("expected_time_exit_return")),
                "expected_time_exit_utility": _display_value(row.get("expected_time_exit_utility")),
                "profitable_despite_failed_tbs_probability": _display_value(
                    row.get("profitable_despite_failed_tbs_probability")
                ),
                "early_adverse_recovery_probability": _display_value(
                    row.get("early_adverse_recovery_probability")
                ),
                "time_exit_positive_probability_component": _display_value(
                    row.get("time_exit_positive_probability_component")
                ),
                "expected_time_exit_return_component": _display_value(
                    row.get("expected_time_exit_return_component")
                ),
                "time_exit_utility_component": _display_value(
                    row.get("time_exit_utility_component")
                ),
                "failed_tbs_but_profitable_component": _display_value(
                    row.get("failed_tbs_but_profitable_component")
                ),
                "adverse_recovery_penalty": _display_value(row.get("adverse_recovery_penalty")),
                "time_exit_utility_labels_json": _policy_exact_row_json(
                    time_exit_labels,
                    row,
                ),
                "time_exit_utility_calibration_summary_json": _policy_records_json(
                    time_exit_summary,
                    row,
                ),
                "time_exit_utility_signal_row_json": _policy_exact_row_json(
                    time_exit_signal_rows,
                    row,
                ),
                "time_exit_utility_policy_comparison_json": _policy_records_json(
                    time_exit_policy_comparison,
                    row,
                ),
                "time_exit_diagnostic_observation_json": diagnostic_observation_by_signal.get(
                    signal_id,
                    "",
                ),
                "time_exit_diagnostic_matured_outcome_json": diagnostic_matured_by_signal.get(
                    signal_id,
                    "",
                ),
                "top_attribution_category": _display_value(row.get("top_support")),
                "top_confirming_relationships": _display_value(row.get("top_support")),
                "supporting_evidence": _display_value(row.get("top_support")),
                "historical_analogs": historical_analogs,
                "top_divergences": _display_value(row.get("top_conflict")),
                "top_support": _display_value(row.get("top_support")),
                "top_conflict": _display_value(row.get("top_conflict")),
                "historical_analog_support": robust_support,
                "analog_status": robustness_status_by_signal.get(signal_id, "Not available"),
                "analog_robustness": robustness_by_signal.get(signal_id, ""),
                "analog_depth_comparison": depth_by_signal.get(signal_id, ""),
                "analog_caution_flags": flags_by_signal.get(signal_id, ""),
                "analog_robustness_explanation": robust_support,
                "blocked_row_analog_summary": blocked_summary_by_signal.get(signal_id, ""),
                "calibration_diagnostic_notice": (
                    "Calibration diagnostic only. Not a threshold change and not proof of edge."
                ),
                "calibration_evidence_status": _calibration_status(calibration_summary, row),
                "same_archetype_calibration_base_rate": _display_value(
                    _same_archetype_calibration_base_rate(calibration_summary, row)
                ),
                "same_scope_calibration_base_rate": _display_value(
                    _same_scope_calibration_base_rate(calibration_summary, row)
                ),
                "calibration_summary_json": _calibration_single_record_json(
                    calibration_summary,
                    row,
                ),
                "calibration_diagnostic_threshold_table": _calibration_records_json(
                    diagnostic_thresholds,
                    row,
                ),
                "calibration_probability_bucket_evidence": _calibration_records_json(
                    probability_buckets,
                    row,
                ),
                "tbs_blocker_calibration_assessment": _calibration_blocker_assessment(
                    calibration_summary,
                    row,
                ),
                "footprint_evidence_json": evidence_by_signal.get(signal_id, ""),
                "footprint_summary": footprint_summary,
                "rejection_reason": _display_value(
                    row.get("rejection_reason") or row.get("no_signal_reason")
                ),
                "no_signal_reason": _display_value(row.get("no_signal_reason")),
                "candidate_status": decision,
                "signal_source": "multi_angle_signal_discovery_v1",
            }
        )
    return pd.DataFrame(rows)


def _signal_discovery_board_rows(root: str | Path) -> pd.DataFrame:
    candidates = signal_discovery_candidates_frame(root)
    if candidates.empty:
        return pd.DataFrame()
    robustness = signal_discovery_analog_robustness_frames(root).get(
        "analog_robustness", pd.DataFrame()
    )
    robustness_support_by_signal = _analog_robustness_support_by_signal(robustness)
    robustness_status_by_signal = _analog_robustness_status_by_signal(robustness)
    rows: list[dict[str, object]] = []
    for _, row in candidates.iterrows():
        signal_id = str(_display_value(row.get("signal_id")))
        status = _display_value(row.get("candidate_status"))
        model_id = _display_value(row.get("model_id"))
        generation = _display_value(row.get("generation_id"))
        rows.append(
            {
                "ticker": _display_value(row.get("ticker")),
                "direction": _display_value(row.get("direction")),
                "action": _display_value(row.get("action")),
                "archetype": _display_value(row.get("archetype")),
                "signal_score": _display_value(row.get("signal_score")),
                "footprint_summary": _display_value(row.get("footprint_summary")),
                "top_support": _display_value(row.get("top_support")),
                "top_conflict": _display_value(row.get("top_conflict")),
                "historical_analog_support": robustness_support_by_signal.get(
                    signal_id, _display_value(row.get("historical_analog_support"))
                ),
                "analog_status": robustness_status_by_signal.get(signal_id, "Not available"),
                "scan_id": generation,
                "run_id": NOT_AVAILABLE,
                "run_display": "Signal Discovery",
                "event_id": NOT_AVAILABLE,
                "event_display": _display_value(row.get("decision")),
                "signal_status": status,
                "live_shadow_rejected_classification": status,
                "edge_status": _display_value(row.get("edge_status")),
                "model_id": model_id,
                "model_display": str(model_id),
                "scope": _display_value(row.get("scope")),
                "family": _display_value(row.get("model_family")),
                "target_stop_policy": _display_value(row.get("target_stop_policy_display")),
                "target_stop_policy_display": _display_value(row.get("target_stop_policy_display")),
                "target_stop_policy_status": _display_value(row.get("target_stop_policy_status")),
                "target_stop_policy_target_multiple": _display_value(
                    row.get("target_stop_policy_target_multiple")
                ),
                "target_stop_policy_stop_multiple": _display_value(
                    row.get("target_stop_policy_stop_multiple")
                ),
                "horizon": _display_value(row.get("horizon")),
                "generation": generation,
                "generation_display": _generation_display(generation),
                "as_of_date": _display_value(row.get("as_of_date")),
                "entry_rule": "next session open after future promotion only",
                "pending_entry_date": NOT_AVAILABLE,
                "entry_price_if_filled": NOT_AVAILABLE,
                "expected_return": _display_value(row.get("expected_return")),
                "expected_mfe": _display_value(row.get("expected_mfe")),
                "expected_mae": _display_value(row.get("expected_mae")),
                "target_before_stop_probability": _display_value(
                    row.get("target_before_stop_probability")
                ),
                "time_exit_positive_probability": _display_value(
                    row.get("time_exit_positive_probability")
                ),
                "expected_time_exit_utility": _display_value(row.get("expected_time_exit_utility")),
                "ood_warning": _display_value(row.get("ood_feature_rate")),
                "gate_status": "BLOCKED",
                "rejection_reason": _display_value(
                    row.get("rejection_reason") or row.get("no_signal_reason")
                ),
                "why_shadow_only": _display_value(row.get("not_live_actionable_reason")),
                "next_required_event": _display_value(row.get("next_required_event")),
                "open_url": candidate_detail_url(
                    scan_id=generation,
                    ticker=row.get("ticker"),
                    model_id=model_id,
                    direction=row.get("direction"),
                    status=status,
                ),
                "candidate_detail_url": candidate_detail_url(
                    scan_id=generation,
                    ticker=row.get("ticker"),
                    model_id=model_id,
                    direction=row.get("direction"),
                    status=status,
                ),
                "export": False,
                "signal_source": "multi_angle_signal_discovery_v1",
            }
        )
    return pd.DataFrame(rows)


def scanner_results_frame(root: str | Path) -> pd.DataFrame:
    models, final_map = _model_maps(root)
    edge_map = {
        model_id: edge_status_for_model(model, final_map.get(model_id))
        for model_id, model in models.items()
    }
    rows = _scanner_rows_with_events(root)
    signal_rows = _signal_discovery_scanner_rows(root)
    if rows.empty:
        empty = pd.DataFrame(
            columns=[
                "scan_id",
                "as_of_date",
                "ticker",
                "direction",
                "scope",
                "model",
                "status",
                "candidate_classification",
                "probability",
                "expected_return",
                "expected_mfe",
                "expected_mae",
                "target_before_stop_probability",
                "top_attribution_category",
                "ood_warning",
                "rejection_reason",
            ]
        )
        return signal_rows if not signal_rows.empty else empty
    events = forward_events_frame(root, final_holdout_only=None)
    event_maps = _signal_event_keys(events)
    records: list[dict[str, object]] = []
    for _, row in rows.iterrows():
        model_id = _clean_text(row.get("model_id"))
        model = models.get(model_id)
        edge_status = edge_map.get(model_id, RESEARCH_ONLY)
        shadow_context = _clean_text(row.get("mode")).upper() == "SHADOW_FINAL_HOLDOUT" or bool(
            final_map.get(model_id)
        )
        lifecycle = _lifecycle_status(row, event_maps)
        gate_eligible = _as_bool(
            _first_available(row.get("model_quality_gate_eligible"), False)
        ) or bool(model and promotion_eligibility(model.gate_results).eligible)
        status, classification = _candidate_classification(
            row=row,
            edge_status=edge_status,
            gate_eligible=gate_eligible,
            shadow_context=shadow_context,
            lifecycle_status=lifecycle,
        )
        records.append(
            {
                "scan_id": _display_value(row.get("scan_id")),
                "as_of_date": _display_value(row.get("as_of_date")),
                "ticker": _display_value(row.get("ticker")),
                "direction": _display_value(row.get("direction")),
                "scope": _display_value(row.get("product_class_scope")),
                "model": model_id,
                "model_id": model_id,
                "run_id": _display_value(row.get("run_id")),
                "event_id": _display_value(row.get("event_id")),
                "event_type": _display_value(row.get("event_type")),
                "feature_snapshot_hash": _display_value(row.get("feature_snapshot_hash")),
                "row_product_class_role": _display_value(row.get("row_product_class_role")),
                "regime": _display_value(row.get("regime")),
                "horizon": _display_value(row.get("horizon")),
                "signal_close": _display_value(row.get("signal_close")),
                "liquidity_score": _display_value(row.get("liquidity_score")),
                "composite_utility_score": _display_value(row.get("composite_utility_score")),
                "family": "" if model is None else model.family,
                "generation": "" if model is None else model.created_at_utc,
                "edge_status": edge_status,
                "status": status,
                "candidate_classification": classification,
                "probability": _display_value(row.get("calibrated_probability")),
                "expected_return": _display_value(row.get("expected_return")),
                "expected_mfe": _display_value(row.get("expected_mfe")),
                "expected_mae": _display_value(row.get("expected_mae")),
                "target_before_stop_probability": _display_value(
                    row.get("target_before_stop_probability")
                ),
                "top_attribution_category": _display_value(row.get("top_attribution_categories")),
                "top_confirming_relationships": _display_value(
                    row.get("top_confirming_relationships")
                ),
                "supporting_evidence": _display_value(row.get("supporting_evidence")),
                "historical_analogs": _display_value(row.get("historical_analogs")),
                "top_divergences": _display_value(row.get("top_divergences")),
                "ood_warning": _display_value(row.get("ood_warning")),
                "ood_warning_details": _display_value(row.get("ood_warning_details")),
                "rejection_reason": _display_value(row.get("exclusion_reason")),
                "candidate_status": _display_value(row.get("candidate_status")),
            }
        )
    scanner_frame = pd.DataFrame(records)
    if signal_rows.empty:
        return scanner_frame
    return pd.concat([scanner_frame, signal_rows], ignore_index=True, sort=False)


def signal_board_frame(root: str | Path) -> pd.DataFrame:
    models, final_map = _model_maps(root)
    rows = _scanner_rows_with_events(root)
    events = forward_events_frame(root, final_holdout_only=None)
    event_maps = _signal_event_keys(events)
    records: list[dict[str, object]] = []
    for _, row in rows.iterrows():
        model_id = _clean_text(row.get("model_id"))
        model = models.get(model_id)
        edge_status = edge_status_for_model(model, final_map.get(model_id))
        shadow_context = _clean_text(row.get("mode")).upper() == "SHADOW_FINAL_HOLDOUT" or bool(
            final_map.get(model_id)
        )
        lifecycle = _lifecycle_status(row, event_maps)
        gate_eligible = _as_bool(
            _first_available(row.get("model_quality_gate_eligible"), False)
        ) or bool(model and promotion_eligibility(model.gate_results).eligible)
        signal_status, classification = _candidate_classification(
            row=row,
            edge_status=edge_status,
            gate_eligible=gate_eligible,
            shadow_context=shadow_context,
            lifecycle_status=lifecycle,
        )
        key = _row_match_key(row)
        pending = event_maps["pending"].get(key)
        filled = event_maps["filled"].get(key)
        closed = event_maps["closed"].get(key)
        linked_event = _first_event(pending, filled, closed)
        event_id = _first_available(_event_value(linked_event, "event_id"), row.get("event_id"))
        run_id = _first_available(
            _event_payload_value(linked_event, "run_id"),
            row.get("run_id"),
        )
        generation = _display_value(
            row.get("generation_id") or ("" if model is None else model.created_at_utc)
        )
        records.append(
            {
                "ticker": _display_value(row.get("ticker")),
                "direction": _display_value(row.get("direction")),
                "scan_id": _display_value(row.get("scan_id")),
                "run_id": _display_value(run_id),
                "run_display": _run_display(run_id),
                "event_id": _display_value(event_id),
                "event_display": _event_display(
                    signal_status=signal_status,
                    event_id=event_id,
                ),
                "signal_status": signal_status,
                "live_shadow_rejected_classification": classification,
                "edge_status": edge_status,
                "model_id": model_id,
                "model_display": _model_display(model=model, row=row, model_id=model_id),
                "footprint_summary": signal_board_footprint_summary(row),
                "scope": _display_value(row.get("product_class_scope") or _model_scope(model)),
                "family": "" if model is None else model.family,
                "horizon": _display_value(
                    row.get("horizon") or ("" if model is None else model.horizon)
                ),
                "generation": generation,
                "generation_display": _generation_display(generation),
                "as_of_date": _display_value(row.get("as_of_date")),
                "entry_rule": _display_value(
                    _event_payload_value(pending, "entry_rule", "paper_entry_rule")
                ),
                "pending_entry_date": _display_value(
                    _event_payload_value(
                        pending,
                        "pending_entry_date",
                        "planned_entry_date",
                        "entry_date",
                    )
                ),
                "entry_price_if_filled": _display_value(
                    _event_payload_value(filled, "entry_price", "fill_price", "entry_open")
                ),
                "expected_return": _display_value(row.get("expected_return")),
                "expected_mfe": _display_value(row.get("expected_mfe")),
                "expected_mae": _display_value(row.get("expected_mae")),
                "target_before_stop_probability": _display_value(
                    row.get("target_before_stop_probability")
                ),
                "ood_warning": _display_value(row.get("ood_warning")),
                "gate_status": "PASS" if gate_eligible else "BLOCKED",
                "rejection_reason": _display_value(row.get("exclusion_reason")),
                "why_shadow_only": _why_shadow_only(classification, lifecycle),
                "next_required_event": _signal_next_required_event(
                    classification, lifecycle, row.get("exclusion_reason")
                ),
                "open_url": candidate_detail_url(
                    scan_id=row.get("scan_id"),
                    ticker=row.get("ticker"),
                    model_id=model_id,
                    direction=row.get("direction"),
                    run_id=run_id,
                    event_id=event_id,
                    status=signal_status,
                ),
                "candidate_detail_url": candidate_detail_url(
                    scan_id=row.get("scan_id"),
                    ticker=row.get("ticker"),
                    model_id=model_id,
                    direction=row.get("direction"),
                    run_id=run_id,
                    event_id=event_id,
                    status=signal_status,
                ),
                "export": False,
            }
        )
    frame = pd.DataFrame(records)
    signal_rows = _signal_discovery_board_rows(root)
    if signal_rows.empty:
        return frame
    return pd.concat([frame, signal_rows], ignore_index=True, sort=False)


def signal_board_metrics(root: str | Path) -> dict[str, object]:
    board = signal_board_frame(root)
    models = registered_models_readonly(root)
    final_runs = final_holdout_runs_frame(root)
    time_exit_status = time_exit_diagnostic_status_frame(root)
    operational = operational_status_frame()
    latest_generation = latest_generation_id(models)
    status = (
        "unavailable"
        if operational.empty or "current_status" not in operational.columns
        else str(operational.iloc[0]["current_status"])
    )
    return {
        "live_actionable_signals": int(
            (
                board.get("live_shadow_rejected_classification", pd.Series(dtype=str))
                == LIVE_ACTIONABLE
            ).sum()
        )
        if not board.empty
        else 0,
        "shadow_paper_signals": int(
            (
                board.get("live_shadow_rejected_classification", pd.Series(dtype=str))
                == SHADOW_ONLY
            ).sum()
        )
        if not board.empty
        else 0,
        "pending_entries": int(
            (board.get("signal_status", pd.Series(dtype=str)) == PENDING_ENTRY).sum()
        )
        if not board.empty
        else 0,
        "open_shadow_positions": int(
            (board.get("signal_status", pd.Series(dtype=str)) == OPEN_SHADOW_POSITION).sum()
        )
        if not board.empty
        else 0,
        "closed_shadow_positions": int(
            (board.get("signal_status", pd.Series(dtype=str)) == CLOSED).sum()
        )
        if not board.empty
        else 0,
        "matured_outcomes": int(
            final_runs.get("matured_outcomes", pd.Series(dtype=int)).map(_safe_int).sum()
        )
        if not final_runs.empty
        else 0,
        "time_exit_diagnostic_observations": int(
            time_exit_status.get("observations_created", pd.Series(dtype=int)).map(_safe_int).sum()
        )
        if not time_exit_status.empty
        else 0,
        "time_exit_diagnostic_matured": int(
            time_exit_status.get("matured_outcomes", pd.Series(dtype=int)).map(_safe_int).sum()
        )
        if not time_exit_status.empty
        else 0,
        "promoted_models": sum(1 for model in models if model.promoted_at_utc),
        "models_collecting_final_holdout_evidence": int(
            final_runs.get("status", pd.Series(dtype=str))
            .astype(str)
            .isin(["CREATED", "COLLECTING", "EARLY_DIAGNOSTIC_AVAILABLE", "READY_FOR_EVALUATION"])
            .sum()
        )
        if not final_runs.empty
        else 0,
        "latest_market_date": latest_market_date(root) or NOT_AVAILABLE,
        "development_generation": latest_generation or NOT_AVAILABLE,
        "operational_run_status": status,
    }


def model_generations_frame(root: str | Path) -> pd.DataFrame:
    models = registered_models_readonly(root)
    if not models:
        return pd.DataFrame(
            columns=[
                "generation_id",
                "created_timestamp",
                "schema_versions",
                "model_count",
                "scopes",
                "directions",
                "families",
                "candidate_count",
                "challenger_count",
                "champion_count",
                "development_holdout_status",
                "final_holdout_status",
                "promoted_count",
                "scanner_eligibility_count",
                "final_holdout_eligibility_count",
            ]
        )
    rows: list[dict[str, object]] = []
    for generation, group in sorted(
        (
            (value, [model for model in models if model.created_at_utc == value])
            for value in {model.created_at_utc for model in models}
        ),
        reverse=True,
    ):
        eligibilities = [promotion_eligibility(model.gate_results) for model in group]
        rows.append(
            {
                "generation_id": generation,
                "created_timestamp": generation,
                "schema_versions": ", ".join(
                    sorted(
                        {
                            str(model.metrics.get("product_class_schema_version") or "")
                            for model in group
                            if model.metrics.get("product_class_schema_version")
                        }
                    )
                ),
                "model_count": len(group),
                "scopes": ", ".join(
                    sorted(
                        {
                            str(model.metrics.get("product_class_scope") or "POOLED")
                            for model in group
                        }
                    )
                ),
                "directions": ", ".join(sorted({model.direction for model in group})),
                "families": ", ".join(sorted({model.family for model in group})),
                "candidate_count": sum(1 for model in group if model.state == "CANDIDATE"),
                "challenger_count": sum(1 for model in group if model.state == "CHALLENGER"),
                "champion_count": sum(1 for model in group if model.state == "CHAMPION"),
                "development_holdout_status": ", ".join(
                    sorted(
                        {
                            str(model.metrics.get("holdout_status") or "")
                            for model in group
                            if model.metrics.get("holdout_status")
                        }
                    )
                ),
                "final_holdout_status": ", ".join(
                    sorted(
                        {
                            str(model.metrics.get("final_holdout_status") or "")
                            for model in group
                            if model.metrics.get("final_holdout_status")
                        }
                    )
                ),
                "promoted_count": sum(1 for model in group if model.promoted_at_utc),
                "scanner_eligibility_count": sum(1 for item in eligibilities if item.eligible),
                "final_holdout_eligibility_count": sum(
                    1
                    for model in group
                    if model.metrics.get("final_holdout_run_id")
                    or model.metrics.get("final_holdout_eligible")
                ),
            }
        )
    return pd.DataFrame(rows)


def model_registry_frame(root: str | Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in registered_models_readonly(root):
        eligibility = promotion_eligibility(model.gate_results)
        failed = [
            gate.gate_id for gate in model.gate_results if gate.mandatory and gate.status != "PASS"
        ]
        final_blocker = next(
            (
                gate.reason
                for gate in model.gate_results
                if gate.gate_id == "final_holdout_required_for_promotion"
            ),
            str(model.metrics.get("holdout_status_reason") or ""),
        )
        rows.append(
            {
                "model_id": model.model_id,
                "generation_id": model.created_at_utc,
                "scope": model.metrics.get("product_class_scope", "POOLED"),
                "direction": model.direction,
                "family": model.family,
                "horizon": model.horizon,
                "state": model.state,
                "selected_observations": _safe_metric(
                    model, "selected_holdout_samples", "selected_samples"
                ),
                "selected_rate": _safe_metric(model, "selected_observation_rate"),
                "brier_skill": _safe_metric(model, "brier_skill_score"),
                "tbs_brier_skill": _safe_metric(
                    model,
                    "target_before_stop_brier_skill_score",
                    "target_before_stop_development_holdout_brier_skill_score",
                ),
                "expected_return_evidence": _safe_metric(
                    model, "holdout_mean_return_lcb_90", "mean_selected_return"
                ),
                "mfe_ood_status": _safe_metric(model, "mfe_holdout_ood_status", "mfe_ood_status"),
                "mae_ood_status": _safe_metric(model, "mae_holdout_ood_status", "mae_ood_status"),
                "portfolio_return": _safe_metric(model, "portfolio_total_return"),
                "max_drawdown": _safe_metric(model, "portfolio_max_drawdown"),
                "failed_mandatory_gates": "; ".join(failed[:8]),
                "failed_mandatory_gate_count": len(failed),
                "final_holdout_blocker": final_blocker,
                "promotion_eligible": eligibility.eligible,
                "scanner_eligible": eligibility.eligible
                and model.state in {"CHAMPION", "CHALLENGER"},
            }
        )
    return pd.DataFrame(rows)


def gate_audit_frame(root: str | Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in registered_models_readonly(root):
        for gate in model.gate_results:
            rows.append(
                {
                    "generation_id": model.created_at_utc,
                    "model_id": model.model_id,
                    "scope": model.metrics.get("product_class_scope", "POOLED"),
                    "direction": model.direction,
                    "family": model.family,
                    "gate_id": gate.gate_id,
                    "gate_name": gate.gate_name,
                    "gate_category": gate.category,
                    "actual": display_gate_value(gate.actual_value),
                    "actual_raw": gate.actual_value,
                    "comparator": gate.comparator,
                    "threshold": display_gate_value(gate.threshold),
                    "threshold_raw": gate.threshold,
                    "status": gate.status,
                    "mandatory": gate.mandatory,
                    "reason": gate.reason,
                    "evidence_source": gate.evidence_source,
                    "policy_version_hash": gate.configuration_hash,
                    "integrity_warning": gate_result_integrity_warning(gate),
                }
            )
    return pd.DataFrame(rows)


def gate_contradiction_audit(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=["check", "status", "count", "example_model_id", "example_gate_id"]
        )
    checks = {
        "unavailable evidence marked PASS": frame[
            (frame["status"] == "PASS")
            & frame["actual_raw"].isin([None, GATE_VALUE_NOT_AVAILABLE, GATE_VALUE_NOT_APPLICABLE])
        ],
        "comparator/status contradictions": frame[
            frame["integrity_warning"]
            .astype(str)
            .str.contains("actual/comparator/threshold", na=False)
        ],
        "status/reason contradictions": frame[
            frame["integrity_warning"].astype(str).str.contains("reason contradicts", na=False)
        ],
        "missing mandatory evidence": frame[
            frame["mandatory"]
            & frame["actual_raw"].isin([None, GATE_VALUE_NOT_AVAILABLE, "Not available"])
        ],
        "invalid infinity/unavailable representation": frame[
            frame["actual"].astype(str).str.lower().isin({"inf", "-inf", "nan"})
        ],
    }
    rows: list[dict[str, object]] = []
    for check, subset in checks.items():
        example = subset.iloc[0] if not subset.empty else None
        rows.append(
            {
                "check": check,
                "status": "PASS" if subset.empty else "FAIL",
                "count": len(subset),
                "example_model_id": "" if example is None else example["model_id"],
                "example_gate_id": "" if example is None else example["gate_id"],
            }
        )
    return pd.DataFrame(rows)


def _manifest_for_symbol(paths: ProjectPaths, symbol: str) -> dict[str, object]:
    path = paths.manifests / f"{symbol}.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def universe_health_frame(root: str | Path) -> pd.DataFrame:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    universe = load_dashboard_universe(project_root)
    dataset_by_symbol = {dataset.ticker: dataset for dataset in discover_raw_datasets(project_root)}
    rows: list[dict[str, object]] = []
    for item in universe_to_frame_rows(universe):
        symbol = str(item["symbol"])
        dataset = dataset_by_symbol.get(symbol)
        manifest = _manifest_for_symbol(paths, symbol)
        try:
            product_class: object = product_class_scope_for_role(str(item.get("role") or ""))
        except ValueError:
            product_class = ""
        rows.append(
            {
                "symbol": symbol,
                "enabled": bool(item.get("enabled")),
                "role": item.get("role"),
                "product_class": product_class,
                "sector": item.get("sector"),
                "latest_raw_date": manifest.get("actual_last_date")
                or (dataset.latest_date if dataset else None),
                "row_count": manifest.get("row_count") or (dataset.row_count if dataset else None),
                "stale_status": manifest.get("stale_data_status")
                or ("missing_raw_data" if dataset is None else "manifest_missing"),
                "manifest_hash": manifest.get("raw_file_hash"),
                "provider": manifest.get("provider") or universe.provider,
                "last_retrieval_timestamp": manifest.get("retrieval_timestamp_utc"),
            }
        )
    return pd.DataFrame(rows)


def _artifact_latest_by_glob(root: str | Path, pattern: str) -> Path | None:
    candidates = sorted(Path(root).glob(pattern), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def latest_feature_snapshot_hash(root: str | Path) -> str:
    path = _artifact_latest_by_glob(root, "data/features/*_features.parquet")
    if path is None:
        return ""
    parts = path.name.split("_")
    return parts[1] if len(parts) > 2 else ""


def latest_market_date(root: str | Path) -> str:
    universe = universe_health_frame(root)
    if universe.empty or "latest_raw_date" not in universe.columns:
        return ""
    dates = pd.to_datetime(universe["latest_raw_date"], errors="coerce").dropna()
    if dates.empty:
        return ""
    return pd.Timestamp(dates.max()).date().isoformat()


def scanner_snapshot_list_frame(root: str | Path) -> pd.DataFrame:
    rows = _read_rows(
        _db_path(root),
        """
        SELECT scan_id, as_of_date, created_at_utc, model_ids_json, feature_snapshot_hash,
               row_count, metadata_json
        FROM scanner_snapshots
        ORDER BY created_at_utc DESC, scan_id
        """,
    )
    records: list[dict[str, object]] = []
    for row in rows:
        metadata = cast(dict[str, object], _json_loads(row["metadata_json"], {}))
        model_states = metadata.get("model_states") or metadata.get("model_state_mode") or ""
        rejection_summary = (
            metadata.get("rejection_summary") or metadata.get("candidate_counts") or ""
        )
        records.append(
            {
                "scan_id": row["scan_id"],
                "generation_id": metadata.get("generation_id")
                or metadata.get("model_generation_ids")
                or "",
                "as_of_date": row["as_of_date"],
                "created_timestamp": row["created_at_utc"],
                "rows": row["row_count"],
                "actionable_rows": metadata.get("actionable_rows", ""),
                "rejected_rows": metadata.get("rejected_rows", ""),
                "model_states": model_states,
                "scopes": metadata.get("product_class_scopes", ""),
                "identity_hash": row["feature_snapshot_hash"],
                "scanner_schema": metadata.get("scanner_identity_version", ""),
                "rejection_summary": json.dumps(rejection_summary, sort_keys=True)
                if isinstance(rejection_summary, dict)
                else rejection_summary,
            }
        )
    if records:
        return pd.DataFrame(records)
    latest = _artifact_latest_by_glob(root, "artifacts/scanner/*_scanner.csv")
    if latest is None:
        return pd.DataFrame(
            columns=[
                "scan_id",
                "generation_id",
                "as_of_date",
                "created_timestamp",
                "rows",
                "actionable_rows",
                "rejected_rows",
                "model_states",
                "scopes",
                "identity_hash",
                "scanner_schema",
                "rejection_summary",
            ]
        )
    frame = pd.read_csv(latest)
    return pd.DataFrame(
        [
            {
                "scan_id": str(frame.get("scan_id", pd.Series([latest.stem])).iloc[0])
                if not frame.empty
                else latest.stem,
                "generation_id": "",
                "as_of_date": str(frame.get("as_of_date", pd.Series([""])).iloc[0])
                if not frame.empty
                else "",
                "created_timestamp": datetime.fromtimestamp(
                    latest.stat().st_mtime, tz=UTC
                ).isoformat(),
                "rows": len(frame),
                "actionable_rows": int(
                    (
                        frame.get("candidate_status", pd.Series(dtype=str))
                        == "ACTIONABLE_PAPER_CANDIDATE"
                    ).sum()
                ),
                "rejected_rows": int(
                    (
                        frame.get("candidate_status", pd.Series(dtype=str))
                        != "ACTIONABLE_PAPER_CANDIDATE"
                    ).sum()
                ),
                "model_states": ", ".join(
                    sorted(
                        set(
                            frame.get("model_state", pd.Series(dtype=str))
                            .dropna()
                            .astype(str)
                            .tolist()
                        )
                    )
                ),
                "scopes": ", ".join(
                    sorted(
                        set(
                            frame.get("product_class_scope", pd.Series(dtype=str))
                            .dropna()
                            .astype(str)
                            .tolist()
                        )
                    )
                ),
                "identity_hash": str(frame.get("feature_snapshot_hash", pd.Series([""])).iloc[0])
                if not frame.empty
                else "",
                "scanner_schema": "",
                "rejection_summary": "",
            }
        ]
    )


def scanner_rows_frame(root: str | Path, scan_id: str | None = None) -> pd.DataFrame:
    snapshots = _read_rows(
        _db_path(root),
        "SELECT scan_id, csv_path FROM scanner_snapshots ORDER BY created_at_utc DESC",
    )
    path: Path | None = None
    for row in snapshots:
        if scan_id is None or str(row["scan_id"]) == scan_id:
            candidate = Path(str(row["csv_path"]))
            path = candidate if candidate.exists() else Path(root) / candidate
            break
    if path is None:
        path = _artifact_latest_by_glob(root, "artifacts/scanner/*_scanner.csv")
    if path is None or not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if scan_id and "scan_id" in frame.columns:
        frame = frame.loc[frame["scan_id"].astype(str) == scan_id]
    return frame.reset_index(drop=True)


def product_class_summary_frame(root: str | Path) -> pd.DataFrame:
    universe = load_dashboard_universe(root)
    definitions = build_product_class_scope_definitions(universe)
    models = registered_models_readonly(root)
    rows: list[dict[str, object]] = []
    for scope in PRODUCT_CLASS_SCOPES:
        definition = definitions[scope]
        scoped_models = [
            model
            for model in models
            if str(model.metrics.get("product_class_scope") or "POOLED") == scope
        ]
        rows.append(
            {
                "scope": scope,
                "symbol_count": len(definition.eligible_symbols),
                "roles": ", ".join(definition.eligible_roles),
                "training_rows": sum(
                    int(model.metrics.get("product_class_training_count") or 0)
                    for model in scoped_models
                ),
                "calibration_rows": sum(
                    int(model.metrics.get("product_class_calibration_count") or 0)
                    for model in scoped_models
                ),
                "development_holdout_rows": sum(
                    int(model.metrics.get("product_class_development_holdout_count") or 0)
                    for model in scoped_models
                ),
                "base_rates": json.dumps(
                    {
                        model.model_id: model.calibration_metrics.get("naive_brier")
                        for model in scoped_models[:8]
                    },
                    sort_keys=True,
                ),
                "target_distributions": "; ".join(
                    str(model.metrics.get("product_class_target_distributions_json") or "")
                    for model in scoped_models[:3]
                ),
                "failed_models": sum(1 for model in scoped_models if model.state == "REJECTED"),
                "candidate_models": sum(1 for model in scoped_models if model.state == "CANDIDATE"),
            }
        )
    return pd.DataFrame(rows)


def product_class_comparison_frame(root: str | Path) -> pd.DataFrame:
    models = registered_models_readonly(root)
    pooled = [
        model for model in models if model.metrics.get("product_class_scope", "POOLED") == "POOLED"
    ]
    rows: list[dict[str, object]] = []
    for scope in ("ORDINARY", "INVERSE", "LEVERAGED_LONG", "LEVERAGED_INVERSE"):
        specialists = [
            model
            for model in models
            if str(model.metrics.get("product_class_scope") or "") == scope
        ]
        comparison = f"POOLED vs {scope}"
        selected_models = [*pooled, *specialists]
        failed_gates = sum(
            promotion_eligibility(model.gate_results).mandatory_failed for model in selected_models
        )
        rows.append(
            {
                "comparison": comparison,
                "brier_skill": _mean_metric(selected_models, "brier_skill_score"),
                "roc_auc": _mean_metric(selected_models, "holdout_roc_auc"),
                "pr_auc": _mean_metric(selected_models, "holdout_pr_auc"),
                "expected_return_mae": _mean_metric(selected_models, "expected_return_holdout_mae"),
                "mfe_ood_rate": _mean_metric(selected_models, "mfe_holdout_ood_rate"),
                "mae_ood_rate": _mean_metric(selected_models, "mae_holdout_ood_rate"),
                "selected_rows": sum(
                    int(model.metrics.get("selected_holdout_samples") or 0)
                    for model in selected_models
                ),
                "mean_net_return": _mean_metric(selected_models, "holdout_mean_net_return"),
                "lower_confidence_bound": _mean_metric(
                    selected_models, "holdout_mean_return_lcb_90"
                ),
                "drawdown": _mean_metric(selected_models, "portfolio_max_drawdown"),
                "concentration": _mean_metric(selected_models, "symbol_concentration_top_1"),
                "failed_gates": failed_gates,
            }
        )
    report_path = (
        Path(root)
        / "reports"
        / "product_class_specialist_v1"
        / "pooled_vs_specialist_comparison.csv"
    )
    if report_path.exists():
        try:
            report = pd.read_csv(report_path)
        except (OSError, pd.errors.ParserError):
            return pd.DataFrame(rows)
        if not report.empty:
            return report
    return pd.DataFrame(rows)


def product_class_research_frame(root: str | Path) -> pd.DataFrame:
    summary = product_class_summary_frame(root)
    comparisons = product_class_comparison_frame(root)
    edge = model_edge_status_frame(root)
    rows: list[dict[str, object]] = []
    for scope in PRODUCT_CLASS_SCOPES:
        scoped_models = (
            edge.loc[edge["scope"].astype(str) == scope].copy() if not edge.empty else edge
        )
        candidate_models = (
            scoped_models.loc[
                scoped_models["edge_status"]
                .astype(str)
                .isin([EDGE_DEVELOPMENT_CANDIDATE, EDGE_SHADOW_VALIDATION])
            ]
            if not scoped_models.empty
            else scoped_models
        )
        best = candidate_models.sort_values(
            by=["edge_status", "selected_rows"], ascending=[False, False]
        ).head(1)
        failed_gates = (
            scoped_models.get("failed_development_gates", pd.Series(dtype=str))
            .astype(str)
            .replace("", pd.NA)
            .dropna()
            .head(5)
            .tolist()
            if not scoped_models.empty
            else []
        )
        summary_row = (
            summary.loc[summary["scope"].astype(str) == scope].iloc[0].to_dict()
            if not summary.empty and scope in set(summary["scope"].astype(str))
            else {}
        )
        if not comparisons.empty and "comparison" in comparisons.columns:
            comparison_mask = comparisons["comparison"].astype(str).str.endswith(scope)
            comparison_row = comparisons.loc[comparison_mask].head(1).to_dict("records")
        else:
            comparison_row = []
        rows.append(
            {
                "scope": scope,
                "symbols": summary_row.get("symbol_count", 0),
                "row_count": _safe_int(summary_row.get("development_holdout_rows", 0))
                + _safe_int(summary_row.get("training_rows", 0))
                + _safe_int(summary_row.get("calibration_rows", 0)),
                "models": len(scoped_models),
                "best_current_candidate": "" if best.empty else str(best.iloc[0]["model_id"]),
                "weakest_blockers": "; ".join(failed_gates) or NOT_AVAILABLE,
                "comparison_versus_pooled": json.dumps(
                    comparison_row[0] if comparison_row else {}, sort_keys=True
                ),
                "selected_rows": int(
                    scoped_models.get("selected_rows", pd.Series(dtype=int)).map(_safe_int).sum()
                )
                if not scoped_models.empty
                else 0,
                "failed_gates": "; ".join(failed_gates) or NOT_AVAILABLE,
                "ood_status": _display_value(
                    ", ".join(
                        sorted(
                            {
                                str(value)
                                for value in scoped_models.get(
                                    "ood_status", pd.Series(dtype=object)
                                ).tolist()
                                if _display_value(value) != NOT_AVAILABLE
                            }
                        )
                    )
                    if not scoped_models.empty
                    else ""
                ),
                "concentration_status": _display_value(
                    "; ".join(gate for gate in failed_gates if "concentration" in gate.lower())
                ),
            }
        )
    return pd.DataFrame(rows)


def product_class_conclusion(root: str | Path) -> str:
    research = product_class_research_frame(root)
    if research.empty:
        return "Product-class research evidence is not available yet."
    non_empty = research.loc[research["best_current_candidate"].astype(str) != ""]
    if non_empty.empty:
        return "No product-class specialist currently stands out as promotion-ready."
    top = non_empty.iloc[0]
    return (
        f"{top['scope']} model {top['best_current_candidate']} is the strongest current "
        "development challenger by available dashboard evidence, but it still requires "
        "prospective shadow evidence before any promotion."
    )


def _mean_metric(models: list[RegisteredModel], metric: str) -> float | None:
    values: list[float] = []
    for model in models:
        raw = model.metrics.get(metric, model.calibration_metrics.get(metric))
        try:
            value = float(cast(float, raw))
        except (TypeError, ValueError):
            continue
        if pd.notna(value):
            values.append(value)
    return float(sum(values) / len(values)) if values else None


def forward_events_frame(
    root: str | Path, *, final_holdout_only: bool | None = None
) -> pd.DataFrame:
    rows = _read_rows(
        _db_path(root),
        "SELECT * FROM forward_events ORDER BY event_time_utc, event_id",
    )
    records: list[dict[str, object]] = []
    for row in rows:
        event_type = str(row["event_type"])
        if final_holdout_only is True and not event_type.startswith("FINAL_HOLDOUT_"):
            continue
        if final_holdout_only is False and event_type.startswith("FINAL_HOLDOUT_"):
            continue
        payload = cast(dict[str, object], _json_loads(row["payload_json"], {}))
        records.append(
            {
                "event_id": row["event_id"],
                "unique_key": row["unique_key"],
                "event_type": event_type,
                "event_time_utc": row["event_time_utc"],
                "market_as_of_date": row["market_as_of_date"],
                "ticker": row["ticker"],
                "direction": row["direction"],
                "model_id": row["model_id"],
                "scanner_snapshot_id": row["scanner_snapshot_id"],
                "feature_snapshot_hash": row["feature_snapshot_hash"],
                "payload": payload,
                "run_id": payload.get("run_id", ""),
                "source_pending_event_id": payload.get("source_pending_event_id", ""),
                "exit_reason": payload.get("exit_reason", ""),
            }
        )
    return pd.DataFrame(records)


def time_exit_diagnostic_events_frame(root: str | Path) -> pd.DataFrame:
    rows = _read_rows_optional(
        _db_path(root),
        """
        SELECT * FROM prospective_time_exit_diagnostic_events
        ORDER BY event_time_utc, event_id
        """,
    )
    records: list[dict[str, object]] = []
    for row in rows:
        payload = cast(dict[str, object], _json_loads(row["payload_json"], {}))
        records.append(
            {
                "event_id": row["event_id"],
                "unique_key": row["unique_key"],
                "diagnostic_run_id": row["diagnostic_run_id"],
                "event_type": row["event_type"],
                "event_time_utc": row["event_time_utc"],
                "market_as_of_date": row["market_as_of_date"],
                "ticker": row["ticker"],
                "signal_id": row["signal_id"],
                "payload": payload,
                "label": payload.get("label", ""),
                "reason": payload.get("reason", ""),
            }
        )
    return pd.DataFrame(records)


def _time_exit_runs_rows(root: str | Path) -> list[sqlite3.Row]:
    return _read_rows_optional(
        _db_path(root),
        """
        SELECT * FROM prospective_time_exit_diagnostic_runs
        ORDER BY created_at_utc, diagnostic_run_id
        """,
    )


def _time_exit_event_ids(events: pd.DataFrame, event_type: str) -> set[str]:
    if events.empty:
        return set()
    return {
        _clean_text(value)
        for value in events.loc[events["event_type"].astype(str) == event_type, "signal_id"]
        if _clean_text(value)
    }


def time_exit_diagnostic_observations_frame(root: str | Path) -> pd.DataFrame:
    events = time_exit_diagnostic_events_frame(root)
    if events.empty:
        return pd.DataFrame()
    filled_ids = _time_exit_event_ids(events, DIAGNOSTIC_EVENT_ENTRY_FILLED)
    matured_ids = _time_exit_event_ids(events, DIAGNOSTIC_EVENT_TIME_EXIT_MATURED)
    rejected_ids = _time_exit_event_ids(events, DIAGNOSTIC_EVENT_OBSERVATION_REJECTED)
    backfill_ids = _time_exit_event_ids(events, DIAGNOSTIC_EVENT_BACKFILL_BLOCKED)
    rows: list[dict[str, object]] = []
    source = events.loc[
        events["event_type"]
        .astype(str)
        .isin(
            [
                DIAGNOSTIC_EVENT_OBSERVATION_CREATED,
                DIAGNOSTIC_EVENT_OBSERVATION_REJECTED,
                DIAGNOSTIC_EVENT_BACKFILL_BLOCKED,
            ]
        )
    ]
    for _, event in source.iterrows():
        signal_id = _clean_text(event.get("signal_id"))
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        status = "Diagnostic Pending Entry"
        if signal_id in matured_ids:
            status = "Diagnostic Matured"
        elif signal_id in filled_ids:
            status = "Diagnostic Open"
        if signal_id in rejected_ids:
            status = "Diagnostic Rejected"
        if signal_id in backfill_ids:
            status = "Diagnostic Backfill Blocked"
        rows.append(
            {
                "diagnostic_run_id": event.get("diagnostic_run_id"),
                "signal_id": signal_id,
                "observation_status": status,
                "as_of_date": payload.get("as_of_date", event.get("market_as_of_date")),
                "ticker": event.get("ticker"),
                "hypothesis_id": payload.get("hypothesis_id", ""),
                "model_id": payload.get("model_id", ""),
                "label": payload.get("label", ""),
                "target_before_stop_probability": payload.get("target_before_stop_probability", ""),
                "time_exit_positive_probability": payload.get("time_exit_positive_probability", ""),
                "expected_time_exit_return": payload.get("expected_time_exit_return", ""),
                "expected_time_exit_utility": payload.get("expected_time_exit_utility", ""),
                "blocker_reason": payload.get("blocker_reason", ""),
                "reason": payload.get("reason", ""),
                "diagnostic_notice": payload.get(
                    "diagnostic_notice",
                    TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE,
                ),
            }
        )
    return pd.DataFrame(rows)


def time_exit_diagnostic_matured_outcomes_frame(root: str | Path) -> pd.DataFrame:
    events = time_exit_diagnostic_events_frame(root)
    if events.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    matured = events.loc[events["event_type"].astype(str) == DIAGNOSTIC_EVENT_TIME_EXIT_MATURED]
    for _, event in matured.iterrows():
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        rows.append(
            {
                "diagnostic_run_id": event.get("diagnostic_run_id"),
                "signal_id": event.get("signal_id"),
                "ticker": event.get("ticker"),
                "as_of_date": payload.get("as_of_date", ""),
                "entry_date": payload.get("entry_date", ""),
                "entry_price": payload.get("entry_price", ""),
                "exit_date": payload.get("exit_date", ""),
                "exit_price": payload.get("exit_price", ""),
                "time_exit_net_return": payload.get("time_exit_net_return", ""),
                "time_exit_positive": payload.get("time_exit_positive", ""),
                "time_exit_utility": payload.get("time_exit_utility", ""),
                "MFE": payload.get("MFE", ""),
                "MAE": payload.get("MAE", ""),
                "baseline_target_touched": payload.get("baseline_target_touched", ""),
                "baseline_stop_touched": payload.get("baseline_stop_touched", ""),
                "baseline_profitable_despite_failed_tbs": payload.get(
                    "baseline_profitable_despite_failed_tbs", ""
                ),
                "baseline_early_adverse_recovery": payload.get(
                    "baseline_early_adverse_recovery", ""
                ),
                "experimental_target_touched": payload.get("experimental_target_touched", ""),
                "experimental_stop_touched": payload.get("experimental_stop_touched", ""),
                "experimental_profitable_despite_failed_tbs": payload.get(
                    "experimental_profitable_despite_failed_tbs", ""
                ),
                "experimental_early_adverse_recovery": payload.get(
                    "experimental_early_adverse_recovery", ""
                ),
            }
        )
    return pd.DataFrame(rows)


def time_exit_diagnostic_status_frame(root: str | Path) -> pd.DataFrame:
    run_rows = _time_exit_runs_rows(root)
    events = time_exit_diagnostic_events_frame(root)
    observations = time_exit_diagnostic_observations_frame(root)
    matured = time_exit_diagnostic_matured_outcomes_frame(root)
    records: list[dict[str, object]] = []
    for run in run_rows:
        run_id = str(run["diagnostic_run_id"])
        run_events = (
            events.loc[events["diagnostic_run_id"].astype(str) == run_id]
            if not events.empty
            else events
        )
        run_obs = (
            observations.loc[observations["diagnostic_run_id"].astype(str) == run_id]
            if not observations.empty
            else observations
        )
        run_matured = (
            matured.loc[matured["diagnostic_run_id"].astype(str) == run_id]
            if not matured.empty
            else matured
        )
        status = str(run["status"])
        if not run_matured.empty:
            signal_dates = (
                run_matured.get("as_of_date", pd.Series(dtype=str)).dropna().astype(str).unique()
            )
            if len(run_matured) >= 100 and len(signal_dates) >= 60:
                status = "READY_FOR_REVIEW"
            elif len(run_matured) >= 30 and len(signal_dates) >= 20:
                status = "EARLY_DIAGNOSTIC_AVAILABLE"
            else:
                status = "COLLECTING"
        latest_processed = (
            max(run_events["market_as_of_date"].astype(str).tolist())
            if not run_events.empty
            else run["latest_processed_market_date"]
        )
        records.append(
            {
                "diagnostic_run_id": run_id,
                "schema_version": run["schema_version"],
                "status": status,
                "baseline_market_date": run["baseline_market_date"],
                "first_eligible_future_as_of_date": run["first_eligible_future_as_of_date"],
                "latest_processed_market_date": latest_processed,
                "hypothesis_id": run["hypothesis_id"],
                "archetype": run["archetype"],
                "action": run["action"],
                "product_scope": run["product_scope"],
                "horizon": run["horizon"],
                "label_schema": run["label_schema"],
                "feature_manifest_hash": run["feature_manifest_hash"],
                "signal_discovery_generation_id": run["signal_discovery_generation_id"],
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
                        run_obs.get("observation_status", pd.Series(dtype=str))
                        == "Diagnostic Pending Entry"
                    ).sum()
                )
                if not run_obs.empty
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
                        run_obs.get("observation_status", pd.Series(dtype=str)) == "Diagnostic Open"
                    ).sum()
                )
                if not run_obs.empty
                else 0,
                "matured_outcomes": len(run_matured),
                "positive_time_exit_outcomes": int(
                    run_matured.get("time_exit_positive", pd.Series(dtype=bool)).fillna(False).sum()
                )
                if not run_matured.empty
                else 0,
                "negative_time_exit_outcomes": int(
                    len(run_matured)
                    - run_matured.get("time_exit_positive", pd.Series(dtype=bool))
                    .fillna(False)
                    .sum()
                )
                if not run_matured.empty
                else 0,
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
                "diagnostic_only": True,
                "promotion_eligible": False,
                "final_holdout_evidence": False,
            }
        )
    return pd.DataFrame(records)


def final_holdout_runs_frame(root: str | Path) -> pd.DataFrame:
    run_rows = _read_rows(
        _db_path(root), "SELECT * FROM final_holdout_runs ORDER BY created_at_utc"
    )
    enrolled_rows = _read_rows(
        _db_path(root),
        "SELECT * FROM final_holdout_models ORDER BY run_id, model_id",
    )
    models = {model.model_id: model for model in registered_models_readonly(root)}
    events = forward_events_frame(root, final_holdout_only=True)
    records: list[dict[str, object]] = []
    for enrolled in enrolled_rows:
        run = next((item for item in run_rows if item["run_id"] == enrolled["run_id"]), None)
        if run is None:
            continue
        model = models.get(str(enrolled["model_id"]))
        run_events = (
            events.loc[events["run_id"].astype(str) == str(run["run_id"])]
            if not events.empty
            else events
        )
        model_events = (
            run_events.loc[run_events["model_id"].astype(str) == str(enrolled["model_id"])]
            if not run_events.empty
            else run_events
        )
        exits = (
            model_events.loc[model_events["event_type"] == "FINAL_HOLDOUT_EXIT_FILLED"]
            if not model_events.empty
            else model_events
        )
        pending = (
            model_events.loc[model_events["event_type"] == "FINAL_HOLDOUT_ENTRY_PENDING"]
            if not model_events.empty
            else model_events
        )
        filled = (
            model_events.loc[model_events["event_type"] == "FINAL_HOLDOUT_ENTRY_FILLED"]
            if not model_events.empty
            else model_events
        )
        invalidated = (
            run_events.loc[run_events["event_type"] == "FINAL_HOLDOUT_DATA_INVALIDATED"]
            if not run_events.empty
            else run_events
        )
        signal_dates = {
            str(payload.get("signal_as_of_date") or date_value)
            for payload, date_value in zip(
                exits.get("payload", pd.Series(dtype=object)),
                exits.get("market_as_of_date", pd.Series(dtype=object)),
                strict=False,
            )
        }
        months = {
            pd.Timestamp(str(payload.get("exit_date"))).strftime("%Y-%m")
            for payload in exits.get("payload", pd.Series(dtype=object))
            if isinstance(payload, dict) and payload.get("exit_date")
        }
        positive = int((exits.get("exit_reason", pd.Series(dtype=object)) == "target").sum())
        negative = max(0, len(exits) - positive)
        pending_ids = set(pending.get("event_id", pd.Series(dtype=object)).astype(str).tolist())
        filled_source_ids = set(
            filled.get("source_pending_event_id", pd.Series(dtype=object)).astype(str).tolist()
        )
        exit_source_ids = set(
            exits.get("source_pending_event_id", pd.Series(dtype=object)).astype(str).tolist()
        )
        records.append(
            {
                "run_id": run["run_id"],
                "model_id": enrolled["model_id"],
                "generation": enrolled["generation_id"],
                "scope": ""
                if model is None
                else model.metrics.get("product_class_scope", "POOLED"),
                "direction": run["direction"],
                "family": "" if model is None else model.family,
                "baseline_date": run["baseline_market_date"],
                "first_eligible_date": run["first_eligible_future_signal_date"],
                "status": run["status"],
                "matured_outcomes": len(exits),
                "distinct_signal_dates": len(signal_dates),
                "observation_sessions": _processed_session_count(run, run_events),
                "calendar_months": len(months),
                "positive_outcomes": positive,
                "negative_outcomes": negative,
                "promotion_eligible": False
                if model is None
                else promotion_eligibility(model.gate_results).eligible,
                "pending_entries": len(pending_ids - filled_source_ids),
                "open_positions": len(filled_source_ids - exit_source_ids),
                "closed_positions": len(exits),
                "backfill_blocked_events": int(
                    invalidated.get("payload", pd.Series(dtype=object))
                    .map(lambda payload: "FINAL_HOLDOUT_BACKFILL_BLOCKED" in str(payload))
                    .sum()
                )
                if not invalidated.empty
                else 0,
                "artifact_integrity": _artifact_integrity_label(enrolled),
            }
        )
    return pd.DataFrame(records)


def shadow_forward_status_frame(root: str | Path) -> pd.DataFrame:
    frame = final_holdout_runs_frame(root)
    if frame.empty:
        return frame
    output = frame.copy()
    output["final_holdout_sample_progress"] = output.apply(
        lambda row: (
            f"{_safe_int(row.get('matured_outcomes'))}/100 matured, "
            f"{_safe_int(row.get('distinct_signal_dates'))}/60 signal dates, "
            f"{_safe_int(row.get('observation_sessions'))}/126 sessions, "
            f"{_safe_int(row.get('calendar_months'))}/4 months, "
            f"{_safe_int(row.get('positive_outcomes'))}/20 positive, "
            f"{_safe_int(row.get('negative_outcomes'))}/20 negative"
        ),
        axis=1,
    )
    return output


def shadow_forward_events_frame(root: str | Path) -> pd.DataFrame:
    events = forward_events_frame(root, final_holdout_only=True)
    if events.empty:
        return pd.DataFrame(
            columns=[
                "event_type",
                "event_time",
                "market_date",
                "ticker",
                "direction",
                "model",
                "entry",
                "stop",
                "target",
                "exit",
                "realized_return",
                "mfe",
                "mae",
                "status",
            ]
        )
    rows: list[dict[str, object]] = []
    for _, event in events.iterrows():
        payload = event.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        scanner_row = payload.get("scanner_row")
        scanner_row = scanner_row if isinstance(scanner_row, dict) else {}
        rows.append(
            {
                "event_type": event.get("event_type"),
                "event_time": event.get("event_time_utc"),
                "market_date": event.get("market_as_of_date"),
                "ticker": event.get("ticker"),
                "direction": event.get("direction"),
                "model": event.get("model_id"),
                "entry": _display_value(
                    _first_available(
                        payload.get("entry_price"),
                        payload.get("fill_price"),
                        payload.get("entry_open"),
                    )
                ),
                "stop": _display_value(
                    _first_available(payload.get("stop_price"), payload.get("frozen_stop_price"))
                ),
                "target": _display_value(
                    _first_available(
                        payload.get("target_price"), payload.get("frozen_target_price")
                    )
                ),
                "exit": _display_value(
                    _first_available(payload.get("exit_price"), payload.get("exit_close"))
                ),
                "realized_return": _display_value(
                    _first_available(
                        payload.get("realized_return"),
                        payload.get("net_return"),
                        payload.get("gross_return"),
                    )
                ),
                "mfe": _display_value(
                    _first_available(payload.get("mfe"), scanner_row.get("expected_mfe"))
                ),
                "mae": _display_value(
                    _first_available(payload.get("mae"), scanner_row.get("expected_mae"))
                ),
                "status": _display_value(
                    _first_available(payload.get("status"), payload.get("exclusion_reason"))
                ),
                "run_id": _display_value(payload.get("run_id")),
            }
        )
    return pd.DataFrame(rows)


def shadow_position_frames(root: str | Path) -> dict[str, pd.DataFrame]:
    events = forward_events_frame(root, final_holdout_only=True)
    if events.empty:
        empty = pd.DataFrame()
        return {"pending": empty, "open": empty, "closed": empty}
    pending = events.loc[events["event_type"] == "FINAL_HOLDOUT_ENTRY_PENDING"].copy()
    filled = events.loc[events["event_type"] == "FINAL_HOLDOUT_ENTRY_FILLED"].copy()
    closed = events.loc[
        events["event_type"].isin(["FINAL_HOLDOUT_EXIT_FILLED", "FINAL_HOLDOUT_POSITION_EXPIRED"])
    ].copy()
    filled_sources = set(
        filled.get("source_pending_event_id", pd.Series(dtype=object)).astype(str).tolist()
    )
    closed_sources = set(
        closed.get("source_pending_event_id", pd.Series(dtype=object)).astype(str).tolist()
    )
    pending_open = pending.loc[~pending["event_id"].astype(str).isin(filled_sources)]
    open_positions = filled.loc[~filled["source_pending_event_id"].astype(str).isin(closed_sources)]
    return {
        "pending": pending_open.drop(columns=["payload"], errors="ignore"),
        "open": open_positions.drop(columns=["payload"], errors="ignore"),
        "closed": closed.drop(columns=["payload"], errors="ignore"),
    }


def shadow_next_steps_frame(root: str | Path) -> pd.DataFrame:
    status = shadow_forward_status_frame(root)
    if status.empty:
        return pd.DataFrame(
            [
                {
                    "what_happens_next": "No development shadow final-holdout run is available.",
                    "reason": "Enrollments are created outside the dashboard.",
                }
            ]
        )
    rows: list[dict[str, object]] = []
    for _, run in status.iterrows():
        if _safe_int(run.get("pending_entries")) > 0:
            message = "Pending entry waits for next session open."
        elif _safe_int(run.get("open_positions")) > 0:
            message = "Open position waits for target, stop, or time exit."
        elif _safe_int(run.get("matured_outcomes")) < 100:
            message = "Run needs more matured outcomes."
        elif not bool(run.get("promotion_eligible")):
            message = "Not eligible for promotion yet."
        else:
            message = "Ready for manual governance review."
        rows.append(
            {
                "run_id": run.get("run_id"),
                "model_id": run.get("model_id"),
                "what_happens_next": message,
                "sample_progress": run.get("final_holdout_sample_progress"),
            }
        )
    return pd.DataFrame(rows)


def _processed_session_count(run: sqlite3.Row, events: pd.DataFrame) -> int:
    metadata = cast(dict[str, object], _json_loads(run["metadata_json"], {}))
    processed = metadata.get("processed_sessions")
    if isinstance(processed, list):
        return len({str(value) for value in processed})
    if events.empty:
        return 0
    signals = events.loc[
        events["event_type"].isin(["FINAL_HOLDOUT_SIGNAL_CREATED", "FINAL_HOLDOUT_SIGNAL_REJECTED"])
    ]
    return len(set(signals.get("market_as_of_date", pd.Series(dtype=object)).astype(str)))


def _artifact_integrity_label(enrolled: sqlite3.Row) -> str:
    path = Path(str(enrolled["artifact_path"]))
    if not path.exists():
        return "missing"
    try:
        return "pass" if hash_file(path) == str(enrolled["artifact_hash"]) else "hash_mismatch"
    except OSError:
        return "unavailable"


def paper_forward_state_frames(root: str | Path) -> dict[str, pd.DataFrame]:
    events = forward_events_frame(root, final_holdout_only=False)
    if events.empty:
        empty = pd.DataFrame()
        return {
            "pending_entries": empty,
            "open_positions": empty,
            "closed_positions": empty,
            "event_history": empty,
            "model_versions": pd.DataFrame(columns=["model_id", "state", "generation_id"]),
        }
    pending = events.loc[events["event_type"] == "ENTRY_PENDING"].copy()
    filled = events.loc[events["event_type"] == "ENTRY_FILLED"].copy()
    closed = events.loc[
        events["event_type"].isin(["EXIT_FILLED", "POSITION_EXPIRED", "POSITION_CANCELED"])
    ].copy()
    filled_source_ids = set(
        filled.get("source_pending_event_id", pd.Series(dtype=object)).astype(str)
    )
    closed_source_ids = set(
        closed.get("source_pending_event_id", pd.Series(dtype=object)).astype(str)
    )
    pending_entries = pending.loc[~pending["event_id"].astype(str).isin(filled_source_ids)]
    open_positions = filled.loc[
        ~filled["source_pending_event_id"].astype(str).isin(closed_source_ids)
    ]
    model_versions = pd.DataFrame(
        [
            {
                "model_id": model.model_id,
                "state": model.state,
                "generation_id": model.created_at_utc,
                "family": model.family,
                "direction": model.direction,
            }
            for model in registered_models_readonly(root)
        ]
    )
    return {
        "pending_entries": pending_entries,
        "open_positions": open_positions,
        "closed_positions": closed,
        "event_history": events.drop(columns=["payload"], errors="ignore"),
        "model_versions": model_versions,
    }


def overview_metrics(root: str | Path) -> dict[str, object]:
    models = registered_models_readonly(root)
    scanner_snapshots = scanner_snapshot_list_frame(root)
    final_runs = final_holdout_runs_frame(root)
    forward_events = forward_events_frame(root, final_holdout_only=None)
    latest_generation = latest_generation_id(models)
    return {
        "development_git_branch": _git_output(Path(root), ("branch", "--show-current")),
        "development_head": _git_output(Path(root), ("rev-parse", "--short", "HEAD")),
        "development_working_tree": "dirty"
        if _git_output(Path(root), ("status", "--short"))
        else "clean",
        "latest_model_generation": latest_generation or "n/a",
        "model_count": len(models),
        "candidate_count": sum(1 for model in models if model.state == "CANDIDATE"),
        "challenger_count": sum(1 for model in models if model.state == "CHALLENGER"),
        "champion_count": sum(1 for model in models if model.state == "CHAMPION"),
        "promoted_models": sum(1 for model in models if model.promoted_at_utc),
        "scanner_snapshot_count": len(scanner_snapshots),
        "final_holdout_run_count": len(set(final_runs.get("run_id", pd.Series(dtype=str)))),
        "forward_event_count": len(forward_events),
        "latest_market_date": latest_market_date(root),
        "latest_feature_snapshot_hash": latest_feature_snapshot_hash(root),
        "fmp_configured": "yes" if fmp_key_configured(root) else "no",
    }


def overview_sections(root: str | Path) -> dict[str, pd.DataFrame]:
    models = registered_models_readonly(root)
    latest_models = _latest_models(models)
    registry = model_registry_frame(root)
    latest_generation = latest_generation_id(models)
    gates = gate_audit_frame(root)
    failed = (
        gates.loc[(gates["mandatory"]) & (gates["status"] != "PASS")] if not gates.empty else gates
    )
    scanner = scanner_snapshot_list_frame(root).head(1)
    final_status = final_holdout_runs_frame(root)
    return {
        "newest_generation_summary": registry.loc[
            registry["generation_id"].astype(str) == str(latest_generation)
        ]
        if latest_models and latest_generation is not None and not registry.empty
        else pd.DataFrame(),
        "latest_scanner_snapshot_summary": scanner,
        "latest_final_holdout_status": final_status.head(10),
        "key_blockers": failed[["model_id", "gate_id", "status", "reason"]].head(20)
        if not failed.empty
        else pd.DataFrame(columns=["model_id", "gate_id", "status", "reason"]),
        "next_operational_command": pd.DataFrame(
            [
                {
                    "next_operational_command": "final-holdout-status"
                    if not final_status.empty
                    else "model-audit --generation latest",
                    "reason": "Read-only review before any mutation.",
                }
            ]
        ),
    }


def live_signal_blockers_frame(root: str | Path) -> pd.DataFrame:
    gates = gate_audit_frame(root)
    models = registered_models_readonly(root)
    board = signal_board_frame(root)
    rows: list[dict[str, object]] = []
    if not any(model.promoted_at_utc for model in models):
        rows.append(
            {
                "blocker": "no promoted model",
                "count": 1,
                "plain_english": "No promoted live scanner model exists yet.",
            }
        )
    final_missing = (
        gates.loc[
            gates["gate_id"].astype(str).str.contains("final_holdout", na=False)
            & (gates["status"].astype(str) != "PASS")
        ]
        if not gates.empty
        else gates
    )
    if not final_missing.empty:
        rows.append(
            {
                "blocker": "final-holdout evidence missing",
                "count": len(final_missing),
                "plain_english": "Prospective final-holdout evidence has not passed required gates.",
            }
        )
    if not board.empty:
        rejected = board.loc[board["live_shadow_rejected_classification"].astype(str) == REJECTED]
        if not rejected.empty:
            reasons = rejected["rejection_reason"].astype(str)
            for token in (
                "model_not_promoted",
                "selected-sample scarcity",
                "OOD",
                "concentration",
                "temporal stability",
                "gate failure",
            ):
                count = int(reasons.str.contains(token, case=False, regex=False).sum())
                if count:
                    rows.append(
                        {
                            "blocker": token,
                            "count": count,
                            "plain_english": f"{count} scanner candidate rows cite {token}.",
                        }
                    )
    return pd.DataFrame(rows)


def reports_inventory_frame(root: str | Path) -> pd.DataFrame:
    base = Path(root)
    patterns = [
        ("reports", "reports/**/*"),
        ("docs generated diagnosis docs", "docs/*DIAGNOSIS*.md"),
        ("docs generated diagnosis docs", "docs/*HANDOFF*.md"),
        ("model audit exports", "reports/**/model_*.csv"),
        ("scanner exports", "artifacts/scanner/*"),
        ("final-holdout exports", "reports/final_holdout/*"),
    ]
    rows: list[dict[str, object]] = []
    seen: set[Path] = set()
    for category, pattern in patterns:
        for path in sorted(base.glob(pattern)):
            if path.is_dir() or path in seen:
                continue
            seen.add(path)
            rows.append(
                {
                    "category": category,
                    "path": str(path.relative_to(base)),
                    "suffix": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                    "modified_at_utc": datetime.fromtimestamp(
                        path.stat().st_mtime, tz=UTC
                    ).isoformat(),
                }
            )
    return pd.DataFrame(rows)


def _relative_display_path(root: Path, value: object) -> str:
    if value in {"", None}:
        return ""
    path = Path(str(value))
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _read_json_dict(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _not_available(value: object) -> object:
    if value in {"", None}:
        return NOT_AVAILABLE
    try:
        if bool(pd.isna(cast(Any, value))):
            return NOT_AVAILABLE
    except (TypeError, ValueError):
        pass
    return value


def _date_count(payload: dict[str, object] | None) -> object:
    dates = payload.get("dates_covered") if payload else None
    if isinstance(dates, list):
        return len(dates)
    return _not_available(None)


def _first_cached_date(payload: dict[str, object] | None) -> object:
    dates = payload.get("dates_covered") if payload else None
    if isinstance(dates, list) and dates:
        return dates[0]
    return _not_available(None)


def _cache_metadata_sort_key(item: tuple[Path, dict[str, object]]) -> tuple[str, str, str, str]:
    _, payload = item
    return (
        str(payload.get("update_timestamp_utc") or ""),
        str(payload.get("last_cached_date") or ""),
        str(payload.get("feature_manifest_hash") or ""),
        str(payload.get("schema_version") or ""),
    )


def _latest_payload(
    cache_dir: Path,
    pattern: str,
    *,
    schema_version: str,
) -> tuple[Path, dict[str, object]] | None:
    candidates: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(cache_dir.glob(pattern)):
        payload = _read_json_dict(path)
        if payload is None or payload.get("schema_version") != schema_version:
            continue
        candidates.append((path, payload))
    if not candidates:
        return None
    return max(candidates, key=_cache_metadata_sort_key)


def _cache_age_label(updated_at: object) -> object:
    if _not_available(updated_at) == NOT_AVAILABLE:
        return NOT_AVAILABLE
    try:
        timestamp = pd.Timestamp(str(updated_at))
    except ValueError:
        return NOT_AVAILABLE
    if pd.isna(timestamp):
        return NOT_AVAILABLE
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(UTC)
    seconds = max(0.0, (datetime.now(UTC) - timestamp.to_pydatetime()).total_seconds())
    if seconds < 120:
        return f"{seconds:.0f} seconds"
    minutes = seconds / 60.0
    if minutes < 120:
        return f"{minutes:.1f} minutes"
    hours = minutes / 60.0
    if hours < 72:
        return f"{hours:.1f} hours"
    return f"{hours / 24.0:.1f} days"


def _regime_next_action(status: str) -> str:
    if status == "HIT":
        return "Nothing required. build-features is using the exact regime cache."
    if status == "NOT_FOUND":
        return "Run build-features to create the regime cache."
    if status == "INVALIDATED":
        return "Run build-features. The engine will recompute and write a fresh cache."
    if status == "PARTIAL_APPEND":
        return "No action required after this run. New dates were appended to the exact cache."
    if status == "MISS":
        return "No action required after this run. The cache was created from a full recompute."
    return "Review cache metadata, then run build-features if the cache should be refreshed."


def _status_label(value: object) -> str:
    text = str(value or "").strip().upper()
    return text if text in REGIME_CACHE_ALLOWED_STATUSES else "UNKNOWN"


def _regime_cache_summary_row(
    root: Path,
    *,
    cache_path: Path | None,
    cache_payload: dict[str, object] | None,
    status_path: Path | None,
    status_payload: dict[str, object] | None,
    status_override: str | None = None,
    validity_reason_override: str | None = None,
) -> dict[str, object]:
    if status_override is not None:
        status = status_override
    elif status_payload is not None:
        status = _status_label(status_payload.get("status"))
    elif cache_payload is not None:
        status = "UNKNOWN"
    else:
        status = "NOT_FOUND"
    validity_reason = (
        validity_reason_override
        or (status_payload or {}).get("reason")
        or ("latest_build_run_status_unavailable" if cache_payload is not None else "cache_missing")
    )
    updated_at = (status_payload or {}).get("update_timestamp_utc") or (cache_payload or {}).get(
        "update_timestamp_utc"
    )
    feature_manifest_hash = (status_payload or {}).get("feature_manifest_hash") or (
        cache_payload or {}
    ).get("feature_manifest_hash")
    return {
        "status": status,
        "cache_validity_status": _not_available(
            (status_payload or {}).get("cache_validity_status")
            or (cache_payload or {}).get("cache_validity_status")
        ),
        "validity_reason": _not_available(validity_reason),
        "cache_schema_version": _not_available(
            (cache_payload or {}).get("schema_version")
            or (status_payload or {}).get("cache_schema_version")
        ),
        "universe_snapshot_id": _not_available(
            (cache_payload or {}).get("universe_snapshot_id")
            or (status_payload or {}).get("universe_snapshot_id")
        ),
        "feature_manifest_hash": _not_available(feature_manifest_hash),
        "first_cached_date": _not_available(_first_cached_date(cache_payload)),
        "last_cached_date": _not_available(
            (cache_payload or {}).get("last_cached_date")
            or (status_payload or {}).get("last_cached_date")
        ),
        "dates_covered": _not_available(_date_count(cache_payload)),
        "rows_covered": _not_available((cache_payload or {}).get("row_count")),
        "cached_dates_reused": _not_available((status_payload or {}).get("cached_dates_reused")),
        "new_dates_computed": _not_available((status_payload or {}).get("new_dates_computed")),
        "kmeans_fits_avoided": _not_available((status_payload or {}).get("kmeans_fits_avoided")),
        "kmeans_fits_performed": _not_available(
            (status_payload or {}).get("kmeans_fits_performed")
        ),
        "regime_runtime_seconds": _not_available(
            (status_payload or {}).get("regime_runtime_seconds")
        ),
        "cache_age": _cache_age_label(updated_at),
        "updated_at_utc": _not_available(updated_at),
        "cache_file": _relative_display_path(root, cache_path or ""),
        "status_file": _relative_display_path(root, status_path or ""),
        "next_action": _regime_next_action(status),
        "forced_rebuild_method": (
            "SWING_RSI_REBUILD_REGIME_CACHE=1 .venv/bin/python -m swing_rsi.cli build-features"
        ),
    }


def _flatten_metadata(
    root: Path,
    *,
    cache_path: Path | None,
    cache_payload: dict[str, object] | None,
    status_path: Path | None,
    status_payload: dict[str, object] | None,
) -> pd.DataFrame:
    summary = _regime_cache_summary_row(
        root,
        cache_path=cache_path,
        cache_payload=cache_payload,
        status_path=status_path,
        status_payload=status_payload,
    )
    rows: list[dict[str, object]] = [
        {"field": field, "value": value} for field, value in summary.items()
    ]
    for prefix, payload in (("cache", cache_payload), ("latest_run", status_payload)):
        if payload is None:
            continue
        for key, value in sorted(payload.items()):
            if key == "records":
                value = f"{len(value):,} cached label records" if isinstance(value, list) else value
            rows.append(
                {
                    "field": f"{prefix}.{key}",
                    "value": _not_available(_stringify_export_safe(value)),
                }
            )
    return pd.DataFrame(rows, columns=["field", "value"])


def _stringify_export_safe(value: object) -> object:
    if isinstance(value, dict | list | tuple):
        return json.dumps(value, sort_keys=True, default=str)
    return value


def _input_columns_frame(cache_payload: dict[str, object] | None) -> pd.DataFrame:
    columns = (cache_payload or {}).get("regime_input_columns")
    rows = (
        [{"position": index + 1, "column": column} for index, column in enumerate(columns)]
        if isinstance(columns, list)
        else [{"position": NOT_AVAILABLE, "column": NOT_AVAILABLE}]
    )
    return pd.DataFrame(rows, columns=["position", "column"])


def _kmeans_config_frame(cache_payload: dict[str, object] | None) -> pd.DataFrame:
    payload = cache_payload or {}
    parameters = payload.get("kmeans_parameters")
    rows: list[dict[str, object]] = []
    if isinstance(parameters, dict):
        rows.extend({"field": key, "value": value} for key, value in sorted(parameters.items()))
    rows.extend(
        [
            {"field": "random_seed", "value": _not_available(payload.get("random_seed"))},
            {
                "field": "minimum_sample_requirement",
                "value": _not_available(payload.get("minimum_sample_requirement")),
            },
            {
                "field": "scaler_preprocessing_configuration",
                "value": _not_available(
                    _stringify_export_safe(payload.get("scaler_preprocessing_configuration"))
                ),
            },
        ]
    )
    return pd.DataFrame(rows, columns=["field", "value"])


def regime_cache_detail_frames(root: str | Path) -> dict[str, pd.DataFrame]:
    project_root = Path(root)
    cache_dir = ProjectPaths(project_root).regime_cache
    latest_cache = _latest_payload(
        cache_dir,
        f"*_{REGIME_KMEANS_CACHE_SCHEMA_VERSION}.json",
        schema_version=REGIME_KMEANS_CACHE_SCHEMA_VERSION,
    )
    latest_status = _latest_payload(
        cache_dir,
        f"*_{REGIME_KMEANS_CACHE_STATUS_SCHEMA_VERSION}.json",
        schema_version=REGIME_KMEANS_CACHE_STATUS_SCHEMA_VERSION,
    )
    cache_path, cache_payload = latest_cache if latest_cache is not None else (None, None)
    status_path, status_payload = latest_status if latest_status is not None else (None, None)
    if cache_path is None and status_path is not None and status_payload is not None:
        referenced_cache = status_payload.get("cache_path")
        if referenced_cache:
            candidate = Path(str(referenced_cache))
            payload = _read_json_dict(candidate)
            if payload and payload.get("schema_version") == REGIME_KMEANS_CACHE_SCHEMA_VERSION:
                cache_path, cache_payload = candidate, payload
    status_override = "NOT_FOUND" if cache_payload is None and status_payload is None else None
    summary = pd.DataFrame(
        [
            _regime_cache_summary_row(
                project_root,
                cache_path=cache_path,
                cache_payload=cache_payload,
                status_path=status_path,
                status_payload=status_payload,
                status_override=status_override,
            )
        ],
        columns=REGIME_CACHE_SUMMARY_COLUMNS,
    )
    return {
        "summary": summary,
        "metadata": _flatten_metadata(
            project_root,
            cache_path=cache_path,
            cache_payload=cache_payload,
            status_path=status_path,
            status_payload=status_payload,
        ),
        "input_columns": _input_columns_frame(cache_payload),
        "kmeans_config": _kmeans_config_frame(cache_payload),
    }


def regime_cache_status_frame(root: str | Path) -> pd.DataFrame:
    return regime_cache_detail_frames(root)["summary"]


def complete_engine_snapshot_frames(root: str | Path) -> dict[str, pd.DataFrame]:
    scanner = scanner_results_frame(root)
    frames = {
        "signal_board": signal_board_frame(root),
        "shadow_forward_status": shadow_forward_status_frame(root),
        "model_edge_status": model_edge_status_frame(root),
        "scanner_results": scanner,
        "gate_audit": gate_audit_frame(root),
        "product_class_research": product_class_research_frame(root),
        "candidate_attribution": scanner[
            [
                column
                for column in (
                    "scan_id",
                    "ticker",
                    "direction",
                    "model_id",
                    "edge_status",
                    "status",
                    "top_attribution_category",
                    "supporting_evidence",
                    "historical_analogs",
                    "top_divergences",
                )
                if column in scanner.columns
            ]
        ]
        if not scanner.empty
        else pd.DataFrame(),
        "data_universe": universe_health_frame(root),
        "reports_index": reports_inventory_frame(root),
        "time_exit_diagnostic_status": time_exit_diagnostic_status_frame(root),
        "time_exit_diagnostic_events": time_exit_diagnostic_events_frame(root),
        "time_exit_diagnostic_observations": time_exit_diagnostic_observations_frame(root),
        "time_exit_diagnostic_matured_outcomes": time_exit_diagnostic_matured_outcomes_frame(root),
    }
    discovery = signal_discovery_generation_frames(root)
    for name in (
        "summary",
        "hypotheses",
        "candidates",
        "no_signal",
        "rejected",
        "target_stop_policy_registry",
        "calibration_selection",
        "sector_rotation_buy_ordinary_policy_comparison",
        "derived_policy_outcomes",
        "signal_discovery_policy_comparison",
        "time_exit_utility_labels",
        "time_exit_utility_calibration_summary",
        "time_exit_utility_signal_rows",
        "time_exit_utility_policy_comparison",
    ):
        frame = discovery.get(name)
        if frame is not None and not frame.empty:
            frames[f"signal_discovery_{name}"] = frame
    return frames


def save_complete_engine_snapshot(root: str | Path) -> Path:
    from swing_rsi.application.dashboard_exports import save_xlsx_report

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return save_xlsx_report(
        root,
        f"complete_engine_snapshot_{timestamp}.xlsx",
        complete_engine_snapshot_frames(root),
    )


def operational_status_frame() -> pd.DataFrame:
    root = OPERATIONAL_REPOSITORY
    db_path = ProjectPaths(root).engine_db
    run_rows = _read_rows(
        db_path,
        "SELECT * FROM final_holdout_runs WHERE run_id = ?",
        (FROZEN_OPERATIONAL_RUN_ID,),
    )
    event_rows = _read_rows(
        db_path,
        "SELECT event_type, COUNT(*) AS count FROM forward_events GROUP BY event_type",
    )
    model_rows = _read_rows(
        db_path,
        "SELECT * FROM final_holdout_models WHERE run_id = ? AND model_id = ?",
        (FROZEN_OPERATIONAL_RUN_ID, FROZEN_OPERATIONAL_MODEL_ID),
    )
    artifact_integrity = "unavailable"
    if model_rows:
        artifact_integrity = _artifact_integrity_label(model_rows[0])
    event_counts = {str(row["event_type"]): int(row["count"]) for row in event_rows}
    run = run_rows[0] if run_rows else None
    return pd.DataFrame(
        [
            {
                "run_id": FROZEN_OPERATIONAL_RUN_ID,
                "enrolled_model_id": FROZEN_OPERATIONAL_MODEL_ID,
                "baseline_date": FROZEN_OPERATIONAL_BASELINE_DATE,
                "current_status": "unavailable" if run is None else run["status"],
                "event_counts": json.dumps(event_counts, sort_keys=True),
                "operational_git_head": _git_output(root, ("rev-parse", "--short", "HEAD")),
                "operational_git_status": _git_output(root, ("status", "--short")),
                "artifact_integrity": artifact_integrity,
            }
        ]
    )


def _git_output(root: Path, args: tuple[str, ...]) -> str:
    try:
        result = subprocess.run(
            ("git", *args),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return (result.stdout or result.stderr).strip()


def command_specs(*, fmp_configured: bool) -> tuple[CommandSpec, ...]:
    return tuple(spec for spec in ALLOWED_COMMANDS if not spec.requires_fmp or fmp_configured)


def assert_command_root_allowed(root: str | Path) -> None:
    resolved = Path(root).resolve()
    if resolved == OPERATIONAL_REPOSITORY.resolve():
        raise ValueError("Command runner refuses to run from the operational repository.")
    if resolved != DEVELOPMENT_REPOSITORY.resolve():
        raise ValueError("Command runner only runs from the configured development worktree.")


def _redact_command_output(value: str) -> str:
    redacted = value.replace("FMP_API_KEY", "[redacted]")
    redacted = redacted.replace("apikey=", "apikey=[redacted]")
    return redacted


def run_dashboard_command(root: str | Path, spec: CommandSpec) -> CommandResult:
    project_root = Path(root).resolve()
    assert_command_root_allowed(project_root)
    log_dir = ProjectPaths(project_root).reports / "dashboard_command_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"{started}_{spec.key}.log"
    result = subprocess.run(
        spec.argv,
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60 * 60,
        env={**os.environ, "PYTHONPATH": f"{project_root / 'src'}:{project_root}"},
    )
    stdout = _redact_command_output(result.stdout)
    stderr = _redact_command_output(result.stderr)
    payload = (
        f"command: {spec.command_text}\n"
        f"return_code: {result.returncode}\n"
        "stdout:\n"
        f"{stdout}\n"
        "stderr:\n"
        f"{stderr}\n"
    )
    log_path.write_text(payload, encoding="utf-8")
    return CommandResult(
        command=spec.command_text,
        return_code=result.returncode,
        stdout=stdout,
        stderr=stderr,
        log_path=log_path,
    )


def sqlite_fingerprint(path: str | Path) -> tuple[str, int | None]:
    db = Path(path)
    return str(db), db.stat().st_mtime_ns if db.exists() else None
