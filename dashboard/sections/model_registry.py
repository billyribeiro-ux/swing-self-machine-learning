from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    gate_audit_frame,
    model_generations_frame,
    model_registry_frame,
    registered_models_readonly,
)
from swing_rsi.engine.gates import promotion_eligibility
from swing_rsi.engine.registry import RegisteredModel

STATE_LABELS = {
    "EXPERIMENTAL": "EXP",
    "CANDIDATE": "CAND",
    "CHALLENGER": "CHAL",
    "CHAMPION": "CHAMP",
    "RETIRED": "RET",
    "REJECTED": "REJ",
}

FAMILY_LABELS = {
    "naive_base_rate": "Base",
    "logistic_regression": "LogReg",
    "hist_gradient_boosting": "HGB",
    "extra_trees": "ExtraTrees",
}


def _short_identifier(value: object, *, prefix: int = 8) -> str:
    text = str(value or "").strip()
    return text if len(text) <= prefix else f"{text[:prefix]}..."


def _compact_state(value: object) -> str:
    return STATE_LABELS.get(str(value or "").strip().upper(), str(value or ""))


def _compact_direction(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"bull", "bullish"}:
        return "Bull"
    if text in {"bear", "bearish"}:
        return "Bear"
    return str(value or "")


def _compact_family(value: object) -> str:
    text = str(value or "").strip()
    return FAMILY_LABELS.get(text, text.replace("_", " ").title())


def _date_only(value: object) -> str:
    if value in {None, ""}:
        return ""
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(timestamp):
        return ""
    return timestamp.date().isoformat()


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent_label(value: object) -> str:
    numeric = _float_or_none(value)
    return "" if numeric is None else f"{numeric:.1%}"


def _decimal_label(value: object, *, digits: int = 2) -> str:
    numeric = _float_or_none(value)
    if numeric is not None and math.isinf(numeric):
        return "∞" if numeric > 0.0 else "-∞"
    return "" if numeric is None else f"{numeric:.{digits}f}"


def compact_registry_rows(models: list[RegisteredModel]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in models:
        eligibility = promotion_eligibility(model.gate_results)
        rows.append(
            {
                "ID": _short_identifier(model.model_id),
                "State": _compact_state(model.state),
                "Dir": _compact_direction(model.direction),
                "Hz": model.horizon,
                "Family": _compact_family(model.family),
                "Scope": str(model.metrics.get("product_class_scope", "POOLED")),
                "Created": _date_only(model.created_at_utc),
                "Train": model.metrics.get("training_samples", ""),
                "Holdout": model.metrics.get("holdout_samples", ""),
                "Sel": model.metrics.get("selected_holdout_samples", ""),
                "Sel%": _percent_label(model.metrics.get("selected_observation_rate")),
                "Win": _percent_label(model.metrics.get("holdout_win_rate")),
                "EV LCB": _percent_label(model.metrics.get("holdout_mean_return_lcb_90")),
                "PF": _decimal_label(model.metrics.get("holdout_profit_factor")),
                "Port DD": _percent_label(model.metrics.get("portfolio_max_drawdown")),
                "Brier": _decimal_label(model.calibration_metrics.get("holdout_brier"), digits=3),
                "BSS": _decimal_label(model.calibration_metrics.get("brier_skill_score"), digits=3),
                "Fail": eligibility.mandatory_failed,
                "NCfg": eligibility.not_configured,
                "Elig": "Y" if eligibility.eligible else "N",
            }
        )
    return pd.DataFrame(rows)


def _metric_rows(model: RegisteredModel, tokens: tuple[str, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for group, values in (("metrics", model.metrics), ("calibration", model.calibration_metrics)):
        for key, value in values.items():
            if any(token in key for token in tokens):
                rows.append({"group": group, "metric": key, "value": value})
    return pd.DataFrame(rows)


def _json_frame(value: Any) -> pd.DataFrame:
    if not isinstance(value, str) or not value.strip():
        return pd.DataFrame()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return pd.DataFrame()
    if isinstance(payload, list):
        return pd.DataFrame([item for item in payload if isinstance(item, dict)])
    if isinstance(payload, dict):
        return pd.DataFrame([{"key": key, "value": item} for key, item in payload.items()])
    return pd.DataFrame()


def _render_drilldown(model: RegisteredModel, gates: pd.DataFrame) -> None:
    streamlit = st()
    tabs = streamlit.tabs(
        [
            "Summary",
            "Gates",
            "Feature Manifests",
            "Calibration",
            "OOD",
            "Path Heads",
            "Portfolio Evidence",
            "Artifacts",
        ]
    )
    with tabs[0]:
        summary = pd.DataFrame(
            [
                {"field": "model_id", "value": model.model_id},
                {"field": "generation_id", "value": model.created_at_utc},
                {"field": "scope", "value": model.metrics.get("product_class_scope", "POOLED")},
                {"field": "state", "value": model.state},
                {"field": "direction", "value": model.direction},
                {"field": "family", "value": model.family},
                {"field": "horizon", "value": model.horizon},
                {"field": "holdout_status", "value": model.metrics.get("holdout_status", "")},
                {"field": "feature_manifest_hash", "value": model.feature_manifest_hash},
            ]
        )
        streamlit.dataframe(display_frame(summary), width="stretch", hide_index=True)
        render_table_downloads(summary, basename=f"{model.model_id}_summary", label="summary")
    with tabs[1]:
        model_gates = gates.loc[gates["model_id"] == model.model_id] if not gates.empty else gates
        streamlit.dataframe(display_frame(model_gates), width="stretch", hide_index=True)
        render_table_downloads(model_gates, basename=f"{model.model_id}_gates", label="gates")
    with tabs[2]:
        features = _metric_rows(
            model,
            (
                "feature",
                "manifest",
                "screening",
                "selected_feature",
            ),
        )
        streamlit.dataframe(display_frame(features), width="stretch", hide_index=True)
        render_table_downloads(features, basename=f"{model.model_id}_features", label="features")
    with tabs[3]:
        calibration = _metric_rows(model, ("calibration", "brier", "isotonic", "sigmoid", "tbs"))
        streamlit.dataframe(display_frame(calibration), width="stretch", hide_index=True)
        render_table_downloads(
            calibration, basename=f"{model.model_id}_calibration", label="calibration"
        )
    with tabs[4]:
        ood = _metric_rows(model, ("ood", "prediction_", "severity", "bounds"))
        streamlit.dataframe(display_frame(ood), width="stretch", hide_index=True)
        render_table_downloads(ood, basename=f"{model.model_id}_ood", label="ood")
    with tabs[5]:
        path_heads = _metric_rows(
            model,
            (
                "expected_return",
                "mfe",
                "mae",
                "path_head",
                "domain",
                "target_normalization",
            ),
        )
        streamlit.dataframe(display_frame(path_heads), width="stretch", hide_index=True)
        render_table_downloads(
            path_heads, basename=f"{model.model_id}_path_heads", label="path_heads"
        )
    with tabs[6]:
        portfolio = _metric_rows(
            model,
            ("portfolio", "profit_factor", "drawdown", "selected", "return"),
        )
        ledger = _json_frame(model.metrics.get("selected_candidate_ledger_json"))
        streamlit.dataframe(display_frame(portfolio), width="stretch", hide_index=True)
        streamlit.dataframe(display_frame(ledger.head(500)), width="stretch", hide_index=True)
        render_table_downloads(portfolio, basename=f"{model.model_id}_portfolio", label="portfolio")
    with tabs[7]:
        artifacts = pd.DataFrame(
            [
                {"field": "artifact_path", "value": model.artifact_path},
                {"field": "code_commit_hash", "value": model.code_commit_hash or ""},
                {"field": "raw_manifest_hashes", "value": ", ".join(model.raw_manifest_hashes)},
                {"field": "hyperparameters", "value": json.dumps(model.hyperparameters)},
            ]
        )
        streamlit.dataframe(display_frame(artifacts), width="stretch", hide_index=True)
        render_table_downloads(artifacts, basename=f"{model.model_id}_artifacts", label="artifacts")


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Model Registry",
        "Generations, model states, gate blockers, scanner eligibility, and artifact drilldowns.",
    )
    models = registered_models_readonly(root)
    generations = model_generations_frame(root)
    model_table = model_registry_frame(root)
    gates = gate_audit_frame(root)

    streamlit.subheader("Generations")
    streamlit.dataframe(display_frame(generations), width="stretch", hide_index=True)
    render_table_downloads(generations, basename="model_generations", label="generations")

    streamlit.subheader("Models")
    streamlit.dataframe(display_frame(model_table), width="stretch", hide_index=True)
    render_table_downloads(model_table, basename="model_registry", label="models")

    streamlit.button(
        "Manual promotion not available in dashboard.",
        disabled=True,
        help="Use the audited CLI path after final-holdout evidence and gates pass.",
    )

    if not models:
        streamlit.info("No registered models are available.")
        return
    selected = streamlit.selectbox(
        "Model drilldown",
        options=models,
        format_func=lambda model: (
            f"{_short_identifier(model.model_id)} | {model.state} | "
            f"{model.direction} | {model.family}"
        ),
    )
    _render_drilldown(selected, gates)


if __name__ == "__main__":
    render_page()
