from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from swing_rsi.application.datasets import download_daily_to_raw, normalize_ticker
from swing_rsi.config import ProjectPaths
from swing_rsi.data.loader import load_ohlcv_csv
from swing_rsi.engine.drift import DriftReport, build_drift_report
from swing_rsi.engine.features import (
    FeatureBuildResult,
    build_feature_panel,
    feature_family_map_for_columns,
    numeric_feature_columns,
)
from swing_rsi.engine.final_holdout import (
    FinalHoldoutEnrollmentReport,
    FinalHoldoutEvaluationResult,
    FinalHoldoutUpdateResult,
    evaluate_final_holdout_run,
    final_holdout_events,
    final_holdout_status_frame,
    initialize_final_holdout_run,
    process_final_holdout_update,
)
from swing_rsi.engine.forward import (
    advance_forward_positions,
    create_pending_events_from_snapshot,
    list_forward_events,
)
from swing_rsi.engine.gates import promotion_eligibility
from swing_rsi.engine.labels import LabelConfig, build_label_panel, merge_features_and_labels
from swing_rsi.engine.manifest import create_manifest, hash_file, write_manifest
from swing_rsi.engine.models import (
    NONLINEAR_SPECIALIST_MODEL_FAMILIES,
    DiscoveryConfig,
    discover_models,
    load_model_bundle,
)
from swing_rsi.engine.product_scope import PRODUCT_CLASS_SCOPES
from swing_rsi.engine.registry import (
    RegisteredModel,
    champion_models,
    list_models,
    promote_model,
)
from swing_rsi.engine.scanner import (
    ScannerConfig,
    ScannerSnapshot,
    latest_common_session,
    run_scanner,
)
from swing_rsi.engine.storage import dumps, engine_connection, initialize_engine_db
from swing_rsi.engine.universe import UniverseConfig, load_universe_config, universe_to_frame_rows


@dataclass(frozen=True)
class SymbolUpdateResult:
    symbol: str
    status: str
    message: str
    rows: int | None = None
    first_date: str | None = None
    last_date: str | None = None


@dataclass(frozen=True)
class UniverseUpdateResult:
    universe: UniverseConfig
    results: tuple[SymbolUpdateResult, ...]


@dataclass(frozen=True)
class FeaturePipelineResult:
    universe: UniverseConfig
    features: FeatureBuildResult
    labels: pd.DataFrame
    modeling_frame: pd.DataFrame
    feature_path: Path
    labels_path: Path
    modeling_path: Path
    raw_manifest_hashes: tuple[str, ...]


@dataclass(frozen=True)
class DailyCycleResult:
    market_date: str
    status: str
    summary: dict[str, object]


def default_universe_path(root: str | Path) -> Path:
    return Path(root) / "configs" / "universe" / "core.yaml"


def load_engine_universe(
    root: str | Path, universe_path: str | Path | None = None
) -> UniverseConfig:
    return load_universe_config(universe_path or default_universe_path(root))


def load_universe_frames(root: str | Path, universe: UniverseConfig) -> dict[str, pd.DataFrame]:
    paths = ProjectPaths(Path(root))
    frames: dict[str, pd.DataFrame] = {}
    for symbol in universe.enabled_symbols:
        path = paths.raw_data / f"{symbol}.csv"
        if not path.exists():
            continue
        frames[symbol] = load_ohlcv_csv(path)
    return frames


def update_universe_data(
    root: str | Path,
    *,
    universe_path: str | Path | None = None,
    start: str | None = None,
    end: str | None = None,
    lookback_years: int = 10,
) -> UniverseUpdateResult:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    universe = load_engine_universe(project_root, universe_path)
    request_start = start or (
        date.today().replace(year=date.today().year - lookback_years).isoformat()
    )
    results: list[SymbolUpdateResult] = []
    for symbol in universe.enabled_symbols:
        try:
            update = download_daily_to_raw(
                project_root,
                symbol,
                start=request_start,
                end=end,
                provider=universe.provider,
            )
            frame = load_ohlcv_csv(update.saved_path)
            manifest = create_manifest(
                provider=universe.provider,
                symbol=symbol,
                requested_start=request_start,
                requested_end=end,
                raw_path=update.saved_path,
                frame=frame,
                root=project_root,
            )
            write_manifest(manifest, paths.manifests)
            results.append(
                SymbolUpdateResult(
                    symbol=symbol,
                    status="updated",
                    message=(
                        f"downloaded={update.downloaded_rows}, replaced={update.replaced_dates}, "
                        f"inserted={update.inserted_dates}"
                    ),
                    rows=update.final_rows,
                    first_date=update.first_date,
                    last_date=update.last_date,
                )
            )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            results.append(SymbolUpdateResult(symbol=symbol, status="error", message=str(exc)))
            continue
    universe_rows = pd.DataFrame(universe_to_frame_rows(universe))
    universe_rows.to_parquet(
        paths.universe_data / f"{universe.snapshot_id}_universe.parquet", index=False
    )
    return UniverseUpdateResult(universe=universe, results=tuple(results))


def _ensure_manifests(
    root: Path, universe: UniverseConfig, frames: dict[str, pd.DataFrame]
) -> tuple[str, ...]:
    paths = ProjectPaths(root)
    hashes: list[str] = []
    for symbol, frame in sorted(frames.items()):
        raw_path = paths.raw_data / f"{normalize_ticker(symbol)}.csv"
        if not raw_path.exists():
            continue
        manifest = create_manifest(
            provider=universe.provider,
            symbol=normalize_ticker(symbol),
            requested_start=None,
            requested_end=None,
            raw_path=raw_path,
            frame=frame,
            root=root,
        )
        manifest_path = write_manifest(manifest, paths.manifests)
        hashes.append(hash_file(manifest_path))
    return tuple(hashes)


def build_autonomous_features(
    root: str | Path,
    *,
    universe_path: str | Path | None = None,
) -> FeaturePipelineResult:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    universe = load_engine_universe(project_root, universe_path)
    frames = load_universe_frames(project_root, universe)
    if not frames:
        raise ValueError("No raw OHLCV files are available for the enabled universe")
    features = build_feature_panel(frames, universe)
    labels = build_label_panel(frames, LabelConfig())
    modeling = merge_features_and_labels(features.frame, labels)
    feature_path = (
        paths.feature_data / f"{universe.snapshot_id}_{features.manifest_hash}_features.parquet"
    )
    labels_path = (
        paths.feature_data / f"{universe.snapshot_id}_{features.manifest_hash}_labels.parquet"
    )
    modeling_path = (
        paths.feature_data / f"{universe.snapshot_id}_{features.manifest_hash}_modeling.parquet"
    )
    features.frame.to_parquet(feature_path, index=False)
    labels.to_parquet(labels_path, index=False)
    modeling.to_parquet(modeling_path, index=False)
    manifest_hashes = _ensure_manifests(project_root, universe, frames)
    return FeaturePipelineResult(
        universe=universe,
        features=features,
        labels=labels,
        modeling_frame=modeling,
        feature_path=feature_path,
        labels_path=labels_path,
        modeling_path=modeling_path,
        raw_manifest_hashes=manifest_hashes,
    )


def latest_modeling_path(root: str | Path) -> Path:
    paths = ProjectPaths(Path(root))
    candidates = sorted(
        paths.feature_data.glob("*_modeling.parquet"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        raise FileNotFoundError("No modeling parquet file found. Run build-features first.")
    return candidates[-1]


def latest_features_path(root: str | Path) -> Path:
    paths = ProjectPaths(Path(root))
    candidates = sorted(
        paths.feature_data.glob("*_features.parquet"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        raise FileNotFoundError("No feature parquet file found. Run build-features first.")
    return candidates[-1]


def run_model_discovery(
    root: str | Path,
    *,
    universe_path: str | Path | None = None,
    modeling_path: str | Path | None = None,
    minimum_training_samples: int = 200,
    minimum_holdout_samples: int = 80,
) -> tuple[RegisteredModel, ...]:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    universe = load_engine_universe(project_root, universe_path)
    model_frame = pd.read_parquet(modeling_path or latest_modeling_path(project_root))
    feature_path = latest_features_path(project_root)
    feature_hash = str(feature_path.name).split("_")[1] if "_" in feature_path.name else "unknown"
    feature_frame = pd.read_parquet(feature_path)
    family_map = feature_family_map_for_columns(numeric_feature_columns(feature_frame))
    manifests = tuple(hash_file(path) for path in sorted(paths.manifests.glob("*.json")))
    result = discover_models(
        model_frame,
        db_path=paths.engine_db,
        artifact_dir=paths.model_artifacts,
        universe_snapshot_id=universe.snapshot_id,
        feature_manifest_hash=feature_hash,
        feature_family_by_column=family_map,
        raw_manifest_hashes=manifests,
        config=DiscoveryConfig(
            minimum_training_samples=minimum_training_samples,
            minimum_holdout_samples=minimum_holdout_samples,
            product_class_scopes=PRODUCT_CLASS_SCOPES,
            model_families=NONLINEAR_SPECIALIST_MODEL_FAMILIES,
            include_naive_controls=True,
        ),
        code_root=project_root,
        universe=universe,
    )
    return (*result.registered_models, *result.rejected_models)


def list_registered_models(root: str | Path) -> list[RegisteredModel]:
    paths = ProjectPaths(Path(root))
    initialize_engine_db(paths.engine_db)
    return list_models(paths.engine_db)


def promote_registered_model(root: str | Path, model_id: str) -> RegisteredModel:
    return promote_model(ProjectPaths(Path(root)).engine_db, model_id)


def _feature_hash_from_path(path: Path) -> str:
    return str(path.name).split("_")[1] if "_" in path.name else "unknown"


def _scanner_models(
    root: Path,
    *,
    include_challengers: bool,
    feature_manifest_hash: str | None = None,
) -> tuple[RegisteredModel, ...]:
    paths = ProjectPaths(root)
    models: tuple[RegisteredModel, ...] = tuple(
        model
        for model in champion_models(paths.engine_db)
        if feature_manifest_hash is None or model.feature_manifest_hash == feature_manifest_hash
    )
    if not models and include_challengers:
        reviewable = tuple(
            model
            for model in list_models(paths.engine_db)
            if model.state in {"CHALLENGER", "CANDIDATE"}
            and (
                feature_manifest_hash is None
                or model.feature_manifest_hash == feature_manifest_hash
            )
        )
        if reviewable:
            latest_created_at = max(model.created_at_utc for model in reviewable)
            models = tuple(
                model for model in reviewable if model.created_at_utc == latest_created_at
            )
    if not models:
        raise ValueError("No champion model is deployed. Promote a challenger before scanning.")
    return tuple(models)


def _has_reviewable_models(root: Path) -> bool:
    paths = ProjectPaths(root)
    return any(
        model.state in {"CHAMPION", "CHALLENGER", "CANDIDATE"}
        for model in list_models(paths.engine_db)
    )


def run_live_scanner(
    root: str | Path,
    *,
    include_challengers: bool = False,
    universe_path: str | Path | None = None,
) -> ScannerSnapshot:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    universe = load_engine_universe(project_root, universe_path)
    frames = load_universe_frames(project_root, universe)
    common_session = latest_common_session(frames, universe.enabled_symbols)
    feature_path = latest_features_path(project_root)
    feature_hash = _feature_hash_from_path(feature_path)
    feature_frame = pd.read_parquet(feature_path)
    feature_frame = feature_frame.loc[pd.to_datetime(feature_frame["Date"]) <= common_session]
    models = _scanner_models(
        project_root,
        include_challengers=include_challengers,
        feature_manifest_hash=feature_hash,
    )
    bundles = tuple(load_model_bundle(model.artifact_path) for model in models)
    return run_scanner(
        feature_frame,
        bundles=bundles,
        db_path=paths.engine_db,
        output_dir=paths.scanner_artifacts,
        universe_snapshot_id=universe.snapshot_id,
        model_states={model.model_id: model.state for model in models},
        model_eligibility={
            model.model_id: promotion_eligibility(model.gate_results).eligible for model in models
        },
        feature_manifest_hash=feature_hash,
        model_artifact_hashes={
            model.model_id: hash_file(Path(model.artifact_path)) for model in models
        },
        model_generation_ids={model.model_id: model.created_at_utc for model in models},
        model_state_mode="review" if include_challengers else "champions-only",
        include_challengers=include_challengers,
        include_candidates=include_challengers,
        config=ScannerConfig(),
        universe=universe,
    )


def run_drift_checks(
    root: str | Path,
    *,
    include_challengers: bool = False,
) -> tuple[DriftReport, ...]:
    project_root = Path(root)
    feature_path = latest_features_path(project_root)
    feature_hash = _feature_hash_from_path(feature_path)
    feature_frame = pd.read_parquet(feature_path)
    as_of = pd.Timestamp(feature_frame["Date"].max()).date().isoformat()
    current = feature_frame.loc[pd.to_datetime(feature_frame["Date"]) == pd.Timestamp(as_of)]
    reports: list[DriftReport] = []
    for model in _scanner_models(
        project_root,
        include_challengers=include_challengers,
        feature_manifest_hash=feature_hash,
    ):
        bundle = load_model_bundle(model.artifact_path)
        reports.append(
            build_drift_report(
                model_id=model.model_id,
                as_of_date=as_of,
                reference_features=bundle.training_matrix,
                current_features=current,
                feature_columns=bundle.feature_columns,
            )
        )
    return tuple(reports)


def latest_scanner_snapshot(root: str | Path) -> pd.DataFrame:
    paths = ProjectPaths(Path(root))
    candidates = sorted(
        paths.scanner_artifacts.glob("*_scanner.csv"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        return pd.DataFrame()
    return pd.read_csv(candidates[-1])


def run_forward_update(
    root: str | Path,
    scanner_rows: pd.DataFrame | None = None,
    *,
    advance_existing: bool = True,
) -> int:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    inserted = 0
    if advance_existing:
        universe = load_engine_universe(project_root)
        inserted += advance_forward_positions(
            paths.engine_db,
            load_universe_frames(project_root, universe),
        )
    rows = scanner_rows if scanner_rows is not None else latest_scanner_snapshot(root)
    if rows.empty:
        return inserted
    return inserted + create_pending_events_from_snapshot(paths.engine_db, rows)


def forward_events(root: str | Path) -> pd.DataFrame:
    return list_forward_events(ProjectPaths(Path(root)).engine_db)


def initialize_final_holdout(
    root: str | Path,
    *,
    generation: str = "latest",
    research_only: bool = False,
) -> FinalHoldoutEnrollmentReport:
    return initialize_final_holdout_run(
        root,
        generation=generation,
        research_only=research_only,
    )


def update_final_holdout(root: str | Path) -> FinalHoldoutUpdateResult:
    return process_final_holdout_update(root)


def final_holdout_status(root: str | Path) -> pd.DataFrame:
    return final_holdout_status_frame(root)


def final_holdout_event_history(root: str | Path, run_id: str | None = None) -> pd.DataFrame:
    return final_holdout_events(ProjectPaths(Path(root)).engine_db, run_id)


def evaluate_final_holdout(
    root: str | Path,
    *,
    run_id: str,
    diagnostic_only: bool = False,
) -> FinalHoldoutEvaluationResult:
    return evaluate_final_holdout_run(
        root,
        run_id=run_id,
        diagnostic_only=diagnostic_only,
    )


def latest_daily_cycle_summary(root: str | Path) -> dict[str, object]:
    paths = ProjectPaths(Path(root))
    with engine_connection(paths.engine_db) as connection:
        row = connection.execute(
            """
            SELECT market_date, status, summary_json
            FROM daily_cycles
            ORDER BY started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return {}
    summary = json.loads(str(row["summary_json"]))
    return {
        "market_date": str(row["market_date"]),
        "status": str(row["status"]),
        **dict(summary),
    }


def _lock_path(root: Path) -> Path:
    return ProjectPaths(root).state / "daily_cycle.lock"


def _write_daily_cycle_report(
    paths: ProjectPaths, market_date: str, summary: dict[str, object]
) -> Path:
    paths.reports.mkdir(parents=True, exist_ok=True)
    report_path = paths.reports / f"daily_cycle_{market_date}.json"
    if not report_path.exists():
        payload = {
            "market_date": market_date,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "summary": summary,
            "note": "Generated local immutable daily-cycle report. Does not contain secrets.",
        }
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return report_path


def run_daily_cycle(
    root: str | Path,
    *,
    universe_path: str | Path | None = None,
    update_data: bool = False,
    include_challengers: bool = True,
) -> DailyCycleResult:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    lock = _lock_path(project_root)
    if lock.exists():
        raise RuntimeError("Daily cycle lock exists. Another cycle may be running.")
    market_date = date.today().isoformat()
    with engine_connection(paths.engine_db) as connection:
        existing = connection.execute(
            "SELECT status, summary_json FROM daily_cycles WHERE market_date = ? AND status = 'completed'",
            (market_date,),
        ).fetchone()
        if existing is not None:
            return DailyCycleResult(
                market_date=market_date,
                status="already_completed",
                summary=json.loads(str(existing["summary_json"])),
            )
    try:
        lock.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
        summary: dict[str, object] = {}
        with engine_connection(paths.engine_db) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO daily_cycles VALUES (?, ?, ?, ?, ?)",
                (market_date, datetime.now(UTC).isoformat(), None, "running", "{}"),
            )
        if update_data:
            updated = update_universe_data(
                project_root,
                universe_path=universe_path,
                start=(date.today() - timedelta(days=14)).isoformat(),
            )
            summary["updated_symbols"] = len(
                [row for row in updated.results if row.status == "updated"]
            )
            summary["update_errors"] = len(
                [row for row in updated.results if row.status == "error"]
            )
        existing_forward_events = advance_forward_positions(
            paths.engine_db,
            load_universe_frames(project_root, load_engine_universe(project_root, universe_path)),
        )
        summary["existing_forward_events_created"] = existing_forward_events
        features = build_autonomous_features(project_root, universe_path=universe_path)
        summary["feature_rows"] = len(features.features.frame)
        summary["modeling_rows"] = len(features.modeling_frame)
        if not _has_reviewable_models(project_root):
            discovered = run_model_discovery(
                project_root,
                universe_path=universe_path,
                minimum_training_samples=50,
                minimum_holdout_samples=20,
            )
            summary["models_registered"] = len(discovered)
        scan = run_live_scanner(project_root, include_challengers=include_challengers)
        summary["scanner_rows"] = len(scan.rows)
        summary["scan_id"] = scan.scan_id
        drift_reports = run_drift_checks(project_root, include_challengers=include_challengers)
        summary["drift_alerts"] = sum(report.alert_count for report in drift_reports)
        summary["forward_events_created"] = run_forward_update(
            project_root,
            scan.rows,
            advance_existing=False,
        )
        report_path = _write_daily_cycle_report(paths, market_date, summary)
        summary["daily_report_path"] = str(report_path)
        with engine_connection(paths.engine_db) as connection:
            connection.execute(
                "UPDATE daily_cycles SET completed_at_utc = ?, status = ?, summary_json = ? WHERE market_date = ?",
                (datetime.now(UTC).isoformat(), "completed", dumps(summary), market_date),
            )
        return DailyCycleResult(market_date=market_date, status="completed", summary=summary)
    finally:
        if lock.exists():
            lock.unlink()
