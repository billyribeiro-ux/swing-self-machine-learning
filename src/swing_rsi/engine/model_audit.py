from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from swing_rsi.config import ProjectPaths
from swing_rsi.engine.gates import (
    gate_result_integrity_warning,
    gate_results_to_jsonable,
    machine_gate_value,
    promotion_eligibility,
)
from swing_rsi.engine.registry import RegisteredModel, list_models


@dataclass(frozen=True)
class ModelAuditResult:
    generation_id: str
    models: tuple[RegisteredModel, ...]
    summary: pd.DataFrame
    gates: pd.DataFrame
    calibration: pd.DataFrame
    portfolio_daily_equity: pd.DataFrame
    selected_candidate_ledger: pd.DataFrame
    trade_ledger: pd.DataFrame
    feature_screens: pd.DataFrame
    calibration_method_comparison: pd.DataFrame
    calibration_fold_metrics: pd.DataFrame
    calibration_probability_audit: pd.DataFrame
    isotonic_step_support: pd.DataFrame
    calibration_threshold_utility: pd.DataFrame
    calibration_governance: pd.DataFrame


def _safe_json_records(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _safe_json_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _machine_value(value: object) -> object:
    return machine_gate_value(value)


def _latest_generation(models: list[RegisteredModel]) -> tuple[str, tuple[RegisteredModel, ...]]:
    if not models:
        return "none", ()
    latest_created_at = max(model.created_at_utc for model in models)
    return latest_created_at, tuple(
        model for model in models if model.created_at_utc == latest_created_at
    )


def select_audit_models(
    root: str | Path,
    *,
    generation: str | None = "latest",
    model_id: str | None = None,
) -> tuple[str, tuple[RegisteredModel, ...]]:
    models = list_models(ProjectPaths(Path(root)).engine_db)
    if model_id:
        selected = tuple(model for model in models if model.model_id == model_id)
        if not selected:
            raise ValueError(f"Unknown model: {model_id}")
        return selected[0].created_at_utc, selected
    if generation in {None, "latest"}:
        generation_id, selected = _latest_generation(models)
        if not selected:
            raise ValueError("No models are registered")
        return generation_id, selected
    selected = tuple(model for model in models if model.created_at_utc == generation)
    if not selected:
        raise ValueError(f"No models found for generation: {generation}")
    assert generation is not None
    return generation, selected


def _summary_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        eligibility = promotion_eligibility(model.gate_results)
        metrics = model.metrics
        calibration = model.calibration_metrics
        head_columns = _safe_json_dict(metrics.get("head_feature_columns_json"))
        primary_columns = head_columns.get("primary_positive_return", [])
        row = {
            "model_id": model.model_id,
            "generation": model.created_at_utc,
            "state": model.state,
            "direction": model.direction,
            "horizon": model.horizon,
            "family": model.family,
            "research_start": metrics.get("research_start"),
            "research_end": metrics.get("research_end"),
            "train_start": model.training_start,
            "train_end": model.training_end,
            "calibration_start": model.validation_start,
            "calibration_end": model.validation_end,
            "holdout_start": model.holdout_start,
            "holdout_end": model.holdout_end,
            "holdout_status": metrics.get("holdout_status"),
            "holdout_status_reason": metrics.get("holdout_status_reason"),
            "holdout_samples": metrics.get("holdout_samples"),
            "selected_samples": metrics.get("selected_holdout_samples"),
            "selected_rate": metrics.get("selected_observation_rate"),
            "selected_row_sequence_drawdown": metrics.get("selected_row_sequence_drawdown"),
            "portfolio_total_return": metrics.get("portfolio_total_return"),
            "portfolio_annualized_return": metrics.get("portfolio_annualized_return"),
            "portfolio_max_drawdown": metrics.get("portfolio_max_drawdown"),
            "portfolio_exposure": metrics.get("portfolio_exposure"),
            "portfolio_turnover": metrics.get("portfolio_turnover"),
            "primary_selected_feature_count": len(primary_columns)
            if isinstance(primary_columns, list)
            else 0,
            "target_before_stop_selected_feature_count": metrics.get(
                "target_before_stop_selected_feature_count"
            ),
            "target_before_stop_screening_target": metrics.get(
                "target_before_stop_screening_target"
            ),
            "target_before_stop_screening_manifest_hash": metrics.get(
                "target_before_stop_screening_manifest_hash"
            ),
            "expected_return_selected_feature_count": metrics.get(
                "expected_return_selected_feature_count"
            ),
            "expected_return_screening_target": metrics.get("expected_return_screening_target"),
            "expected_return_screening_manifest_hash": metrics.get(
                "expected_return_screening_manifest_hash"
            ),
            "mfe_selected_feature_count": metrics.get("mfe_selected_feature_count"),
            "mfe_screening_target": metrics.get("mfe_screening_target"),
            "mfe_screening_manifest_hash": metrics.get("mfe_screening_manifest_hash"),
            "mae_selected_feature_count": metrics.get("mae_selected_feature_count"),
            "mae_screening_target": metrics.get("mae_screening_target"),
            "mae_screening_manifest_hash": metrics.get("mae_screening_manifest_hash"),
            "model_brier": calibration.get("holdout_brier"),
            "naive_brier": calibration.get("naive_brier"),
            "absolute_brier_improvement": calibration.get("absolute_brier_improvement"),
            "relative_brier_improvement": calibration.get("relative_brier_improvement"),
            "brier_skill_score": calibration.get("brier_skill_score"),
            "mean_selected_return": metrics.get("holdout_mean_net_return"),
            "lower_confidence_bound": metrics.get("holdout_mean_return_lcb_90"),
            "profit_factor": _machine_value(metrics.get("holdout_profit_factor")),
            "prediction_ood_governance_version": metrics.get("prediction_ood_governance_version"),
            "prediction_values_finite": metrics.get("prediction_values_finite"),
            "prediction_probability_contract_valid": metrics.get(
                "prediction_probability_contract_valid"
            ),
            "prediction_head_bound_mapping_valid": metrics.get(
                "prediction_head_bound_mapping_valid"
            ),
            "prediction_bounds_training_only": metrics.get("prediction_bounds_training_only"),
            "prediction_path_metric_sign_valid": metrics.get("prediction_path_metric_sign_valid"),
            "temporal_fold_schema_version": metrics.get("temporal_fold_schema_version"),
            "temporal_fold_folds_requested": metrics.get("temporal_fold_folds_requested"),
            "temporal_fold_folds_evaluated": metrics.get("temporal_fold_folds_evaluated"),
            "temporal_fold_folds_with_selected_observations": metrics.get(
                "temporal_fold_folds_with_selected_observations"
            ),
            "temporal_fold_selected_observations_per_fold": metrics.get(
                "temporal_fold_selected_observations_per_fold_json"
            ),
            "temporal_fold_records": metrics.get("temporal_fold_records_json"),
            "temporal_fold_evidence_status": metrics.get("temporal_fold_evidence_status"),
            "temporal_fold_positive_fraction": metrics.get("temporal_fold_positive_fraction"),
            "temporal_fold_evidence_unavailable_reason": metrics.get(
                "temporal_fold_evidence_unavailable_reason"
            ),
            "temporal_fold_threshold": metrics.get("temporal_fold_threshold"),
            "temporal_fold_evidence_gate_status": metrics.get("temporal_fold_evidence_gate_status"),
            "temporal_fold_threshold_gate_status": metrics.get(
                "temporal_fold_threshold_gate_status"
            ),
            "mandatory_gates_passed": eligibility.mandatory_passed,
            "mandatory_gates_failed": eligibility.mandatory_failed,
            "mandatory_gates_not_configured": eligibility.not_configured,
            "mandatory_gates_not_applicable": eligibility.not_applicable,
            "promotion_eligible": eligibility.eligible,
            "promotion_blocked_reason": " | ".join(eligibility.blocked_reasons),
        }
        for head in ("return", "mfe", "mae"):
            row.update(
                {
                    f"{head}_training_q01": metrics.get(f"{head}_train_target_q01"),
                    f"{head}_training_q99": metrics.get(f"{head}_train_target_q99"),
                    f"{head}_calibration_ood_count": metrics.get(f"{head}_calibration_ood_count"),
                    f"{head}_calibration_ood_rate": metrics.get(f"{head}_calibration_ood_rate"),
                    f"{head}_frozen_ood_rate_limit": metrics.get(
                        f"{head}_calibration_ood_rate_limit"
                    ),
                    f"{head}_holdout_ood_count": metrics.get(f"{head}_holdout_ood_count"),
                    f"{head}_holdout_ood_rate": metrics.get(f"{head}_holdout_ood_rate"),
                    f"{head}_calibration_q99_severity": metrics.get(
                        f"{head}_calibration_ood_q99_severity"
                    ),
                    f"{head}_frozen_q99_severity_limit": metrics.get(
                        f"{head}_ood_severity_q99_limit"
                    ),
                    f"{head}_holdout_q99_severity": metrics.get(f"{head}_holdout_ood_q99_severity"),
                    f"{head}_holdout_max_severity": metrics.get(f"{head}_holdout_ood_max_severity"),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _gate_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        for gate in model.gate_results:
            row = {
                "model_id": model.model_id,
                "generation": model.created_at_utc,
                **gate_results_to_jsonable((gate,))[0],
                "evidence_integrity_warning": gate_result_integrity_warning(gate),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def _calibration_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        records = _safe_json_records(model.metrics.get("calibration_table_json"))
        if not records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "reason": "calibration_table_not_persisted",
                }
            )
            continue
        for record in records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    **record,
                }
            )
    return pd.DataFrame(rows)


def _records_frame(
    models: tuple[RegisteredModel, ...],
    metric_name: str,
    *,
    missing_reason: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        records = _safe_json_records(model.metrics.get(metric_name))
        if not records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "reason": missing_reason,
                }
            )
            continue
        for record in records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    **record,
                }
            )
    return pd.DataFrame(rows)


def _feature_screen_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    head_metric_prefix = {
        "target_before_stop": "target_before_stop",
        "expected_return": "expected_return",
        "mfe": "mfe",
        "mae": "mae",
    }
    for model in models:
        metrics = model.metrics
        head_columns = _safe_json_dict(metrics.get("head_feature_columns_json"))
        feature_sets = {
            head: set(columns if isinstance(columns, list) else [])
            for head, columns in head_columns.items()
        }
        primary_set = feature_sets.get("primary_positive_return", set())
        tbs_set = feature_sets.get("target_before_stop", set())
        path_sets = {
            head: feature_sets.get(head, set()) for head in ("expected_return", "mfe", "mae")
        }
        for head, metric_prefix in head_metric_prefix.items():
            selected_set = feature_sets.get(head, set())
            primary_overlap = len(selected_set & primary_set)
            primary_union = len(selected_set | primary_set)
            tbs_overlap = len(selected_set & tbs_set)
            tbs_union = len(selected_set | tbs_set)
            other_path_overlaps = {
                other_head: len(selected_set & other_set)
                for other_head, other_set in path_sets.items()
                if other_head != head
            }
            metadata_records = _safe_json_records(
                metrics.get(f"{metric_prefix}_top_25_train_mi_features_json")
            )
            audit_records = _safe_json_records(
                metrics.get(f"{metric_prefix}_feature_screen_audit_json")
            )
            manifest = metrics.get(f"{metric_prefix}_screening_manifest_hash")
            config_hash = metrics.get(f"{metric_prefix}_screening_configuration_hash")
            if not audit_records:
                rows.append(
                    {
                        "model_id": model.model_id,
                        "generation": model.created_at_utc,
                        "direction": model.direction,
                        "family": model.family,
                        "horizon": model.horizon,
                        "head": head,
                        "reason": (
                            f"{head}_feature_screen_not_persisted_for_legacy_artifact"
                            if head == "target_before_stop"
                            else "legacy_shared_path_feature_screen"
                        ),
                        "primary_feature_count": len(primary_set),
                        "head_feature_count": len(selected_set),
                        "primary_overlap_count": primary_overlap,
                        "primary_jaccard": primary_overlap / primary_union
                        if primary_union
                        else 0.0,
                        "target_before_stop_overlap_count": tbs_overlap,
                        "target_before_stop_jaccard": tbs_overlap / tbs_union if tbs_union else 0.0,
                        "other_path_overlap_counts_json": json.dumps(
                            other_path_overlaps, sort_keys=True
                        ),
                        "selected_feature_manifest_hash": manifest,
                        "screen_configuration_hash": config_hash,
                    }
                )
                continue
            top_rank_by_feature = {
                str(record.get("feature")): int(record.get("rank") or 0)
                for record in metadata_records
            }
            for record in audit_records:
                rows.append(
                    {
                        "model_id": model.model_id,
                        "generation": model.created_at_utc,
                        "direction": model.direction,
                        "family": model.family,
                        "horizon": model.horizon,
                        "head": head,
                        "primary_feature_count": len(primary_set),
                        "head_feature_count": len(selected_set),
                        "primary_overlap_count": primary_overlap,
                        "primary_jaccard": primary_overlap / primary_union
                        if primary_union
                        else 0.0,
                        "target_before_stop_overlap_count": tbs_overlap,
                        "target_before_stop_jaccard": tbs_overlap / tbs_union if tbs_union else 0.0,
                        "other_path_overlap_counts_json": json.dumps(
                            other_path_overlaps, sort_keys=True
                        ),
                        "selected_feature_manifest_hash": manifest,
                        "screen_configuration_hash": config_hash,
                        "top_25_train_mi_rank": top_rank_by_feature.get(
                            str(record.get("feature")), ""
                        ),
                        **record,
                    }
                )
    return pd.DataFrame(rows)


def _calibration_method_comparison_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        records = _safe_json_records(
            model.metrics.get("target_before_stop_calibration_candidate_results_json")
        )
        if not records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "reason": "target_before_stop_calibration_governance_not_persisted",
                }
            )
            continue
        selected_method = model.metrics.get("target_before_stop_calibration_method")
        boundary = model.metrics.get("target_before_stop_calibration_one_standard_error_boundary")
        reason = model.metrics.get("target_before_stop_calibration_selection_reason")
        for record in records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "direction": model.direction,
                    "family": model.family,
                    "horizon": model.horizon,
                    "selected_method": selected_method,
                    "one_standard_error_boundary": boundary,
                    "selection_reason": reason,
                    **record,
                }
            )
    return pd.DataFrame(rows)


def _calibration_fold_metrics_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        records = _safe_json_records(
            model.metrics.get("target_before_stop_calibration_fold_results_json")
        )
        if not records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "reason": "target_before_stop_calibration_fold_metrics_not_persisted",
                }
            )
            continue
        for record in records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "direction": model.direction,
                    "family": model.family,
                    "horizon": model.horizon,
                    **record,
                }
            )
    return pd.DataFrame(rows)


def _calibration_step_support_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        records = _safe_json_records(model.metrics.get("target_before_stop_step_support_json"))
        if not records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "reason": "target_before_stop_step_support_not_persisted",
                }
            )
            continue
        for record in records:
            rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "direction": model.direction,
                    "family": model.family,
                    "horizon": model.horizon,
                    **record,
                }
            )
    return pd.DataFrame(rows)


def _read_csv_artifact_records(
    models: tuple[RegisteredModel, ...],
    metric_name: str,
    *,
    missing_reason: str,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    missing_rows: list[dict[str, object]] = []
    for model in models:
        value = model.metrics.get(metric_name)
        path = Path(str(value)) if value else None
        if path is None or not path.exists():
            missing_rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "reason": missing_reason,
                }
            )
            continue
        frame = pd.read_csv(path)
        frame.insert(0, "generation", model.created_at_utc)
        rows.append(frame)
    if rows:
        return pd.concat(rows, ignore_index=True)
    return pd.DataFrame(missing_rows)


def _read_probability_audit(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    missing_rows: list[dict[str, object]] = []
    for model in models:
        value = model.metrics.get("target_before_stop_calibration_audit_probability_path")
        path = Path(str(value)) if value else None
        if path is None or not path.exists():
            missing_rows.append(
                {
                    "model_id": model.model_id,
                    "generation": model.created_at_utc,
                    "reason": "target_before_stop_probability_audit_not_persisted",
                }
            )
            continue
        frame = pd.read_parquet(path)
        frame.insert(0, "generation", model.created_at_utc)
        rows.append(frame)
    if rows:
        return pd.concat(rows, ignore_index=True)
    return pd.DataFrame(missing_rows)


def _calibration_governance_frame(models: tuple[RegisteredModel, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        metadata = _safe_json_dict(
            model.metrics.get("target_before_stop_calibration_governance_json")
        )
        if not metadata:
            metadata = {
                "calibration_governance_schema": model.metrics.get(
                    "target_before_stop_calibration_governance_schema"
                ),
                "selected_method": model.metrics.get("target_before_stop_calibration_method"),
                "selection_reason": model.metrics.get(
                    "target_before_stop_calibration_selection_reason"
                ),
                "calibration_manifest_hash": model.metrics.get(
                    "target_before_stop_calibration_manifest_hash"
                ),
                "calibrator_artifact_hash": model.metrics.get(
                    "target_before_stop_calibrator_artifact_hash"
                ),
            }
        rows.append(
            {
                "model_id": model.model_id,
                "generation": model.created_at_utc,
                "direction": model.direction,
                "family": model.family,
                "horizon": model.horizon,
                **metadata,
            }
        )
    return pd.DataFrame(rows)


def build_model_audit(
    root: str | Path,
    *,
    generation: str | None = "latest",
    model_id: str | None = None,
) -> ModelAuditResult:
    generation_id, models = select_audit_models(root, generation=generation, model_id=model_id)
    summary = _summary_frame(models)
    gates = _gate_frame(models)
    calibration = _calibration_frame(models)
    portfolio_daily = _records_frame(
        models,
        "portfolio_daily_equity_json",
        missing_reason="portfolio_daily_equity_not_persisted_for_legacy_artifact",
    )
    selected_ledger = _records_frame(
        models,
        "selected_candidate_ledger_json",
        missing_reason="selected_candidate_ledger_not_persisted_for_legacy_artifact",
    )
    trade_ledger = _records_frame(
        models,
        "portfolio_trade_ledger_json",
        missing_reason="portfolio_trade_ledger_not_persisted_for_legacy_artifact",
    )
    feature_screens = _feature_screen_frame(models)
    calibration_method_comparison = _calibration_method_comparison_frame(models)
    calibration_fold_metrics = _calibration_fold_metrics_frame(models)
    calibration_probability_audit = _read_probability_audit(models)
    isotonic_step_support = _calibration_step_support_frame(models)
    calibration_threshold_utility = _read_csv_artifact_records(
        models,
        "target_before_stop_calibration_threshold_utility_path",
        missing_reason="target_before_stop_calibration_threshold_utility_not_persisted",
    )
    calibration_governance = _calibration_governance_frame(models)
    return ModelAuditResult(
        generation_id=generation_id,
        models=models,
        summary=summary,
        gates=gates,
        calibration=calibration,
        portfolio_daily_equity=portfolio_daily,
        selected_candidate_ledger=selected_ledger,
        trade_ledger=trade_ledger,
        feature_screens=feature_screens,
        calibration_method_comparison=calibration_method_comparison,
        calibration_fold_metrics=calibration_fold_metrics,
        calibration_probability_audit=calibration_probability_audit,
        isotonic_step_support=isotonic_step_support,
        calibration_threshold_utility=calibration_threshold_utility,
        calibration_governance=calibration_governance,
    )


def export_model_audit(result: ModelAuditResult, export_dir: str | Path) -> tuple[Path, ...]:
    output = Path(export_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "model_summary.csv": result.summary,
        "full_gate_audit.csv": result.gates,
        "calibration_table.csv": result.calibration,
        "portfolio_daily_equity.csv": result.portfolio_daily_equity,
        "selected_candidate_ledger.csv": result.selected_candidate_ledger,
        "portfolio_trade_ledger.csv": result.trade_ledger,
        "feature_screen_audit.csv": result.feature_screens,
        "calibration_method_comparison.csv": result.calibration_method_comparison,
        "calibration_fold_metrics.csv": result.calibration_fold_metrics,
        "isotonic_step_support.csv": result.isotonic_step_support,
        "calibration_threshold_utility.csv": result.calibration_threshold_utility,
    }
    written: list[Path] = []
    for name, frame in paths.items():
        path = output / name
        frame.to_csv(path, index=False)
        written.append(path)
    gate_json = output / "full_gate_audit.json"
    gate_json.write_text(
        json.dumps(result.gates.to_dict(orient="records"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written.append(gate_json)
    feature_screen_json = output / "feature_screen_audit.json"
    feature_screen_json.write_text(
        json.dumps(result.feature_screens.to_dict(orient="records"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written.append(feature_screen_json)
    probability_audit = output / "calibration_probability_audit.parquet"
    result.calibration_probability_audit.to_parquet(probability_audit, index=False)
    written.append(probability_audit)
    calibration_governance_json = output / "calibration_governance.json"
    calibration_governance_json.write_text(
        json.dumps(
            result.calibration_governance.to_dict(orient="records"), indent=2, sort_keys=True
        ),
        encoding="utf-8",
    )
    written.append(calibration_governance_json)
    return tuple(written)


def audit_text(result: ModelAuditResult) -> str:
    if result.summary.empty:
        return f"Generation ID: {result.generation_id}\nModel count: 0"
    lines = [
        f"Generation ID: {result.generation_id}",
        f"Model count: {len(result.models):,}",
    ]
    research_starts = sorted(
        str(value) for value in result.summary["research_start"].dropna().unique() if str(value)
    )
    research_ends = sorted(
        str(value) for value in result.summary["research_end"].dropna().unique() if str(value)
    )
    if research_starts or research_ends:
        lines.append(
            "Research dates: "
            f"{research_starts[0] if research_starts else 'unknown'} to "
            f"{research_ends[-1] if research_ends else 'unknown'}"
        )
    display_columns = [
        "model_id",
        "state",
        "direction",
        "horizon",
        "family",
        "holdout_samples",
        "selected_samples",
        "selected_rate",
        "model_brier",
        "naive_brier",
        "brier_skill_score",
        "portfolio_max_drawdown",
        "mandatory_gates_failed",
        "mandatory_gates_not_configured",
        "promotion_eligible",
    ]
    existing = [column for column in display_columns if column in result.summary.columns]
    lines.append(result.summary[existing].to_string(index=False))
    return "\n".join(lines)
