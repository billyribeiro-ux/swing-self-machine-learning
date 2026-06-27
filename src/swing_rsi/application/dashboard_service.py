from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pandas as pd

from swing_rsi.application.datasets import discover_raw_datasets
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
    PRODUCT_CLASS_SCOPES,
    build_product_class_scope_definitions,
    product_class_scope_for_role,
)
from swing_rsi.engine.registry import RegisteredModel
from swing_rsi.engine.registry import _row_to_model as registry_row_to_model
from swing_rsi.engine.universe import UniverseConfig, load_universe_config, universe_to_frame_rows
from swing_rsi.settings import get_fmp_api_key

DEVELOPMENT_REPOSITORY = Path("/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev")
OPERATIONAL_REPOSITORY = Path("/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner")
FROZEN_OPERATIONAL_RUN_ID = "3493ee8ac37bf96475c362e1"
FROZEN_OPERATIONAL_MODEL_ID = "b93b2258c10aea5cef81d291"
FROZEN_OPERATIONAL_BASELINE_DATE = "2026-06-25"


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
        "scan --include-challengers",
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
