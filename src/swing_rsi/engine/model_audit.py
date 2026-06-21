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
            "holdout_samples": metrics.get("holdout_samples"),
            "selected_samples": metrics.get("selected_holdout_samples"),
            "selected_rate": metrics.get("selected_observation_rate"),
            "selected_row_sequence_drawdown": metrics.get("selected_row_sequence_drawdown"),
            "portfolio_total_return": metrics.get("portfolio_total_return"),
            "portfolio_annualized_return": metrics.get("portfolio_annualized_return"),
            "portfolio_max_drawdown": metrics.get("portfolio_max_drawdown"),
            "portfolio_exposure": metrics.get("portfolio_exposure"),
            "portfolio_turnover": metrics.get("portfolio_turnover"),
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
    return ModelAuditResult(
        generation_id=generation_id,
        models=models,
        summary=summary,
        gates=gates,
        calibration=calibration,
        portfolio_daily_equity=portfolio_daily,
        selected_candidate_ledger=selected_ledger,
        trade_ledger=trade_ledger,
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
