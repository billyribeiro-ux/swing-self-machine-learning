from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame, special_value_label
from swing_rsi.application.engine_service import list_registered_models, promote_registered_model
from swing_rsi.engine.gates import (
    display_gate_value,
    gate_result_integrity_warning,
    gate_results_to_jsonable,
    promotion_eligibility,
)
from swing_rsi.engine.model_audit import build_model_audit
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
    "random_forest": "RF",
}


def _short_identifier(value: object, *, prefix: int = 8) -> str:
    text = str(value or "").strip()
    if len(text) <= prefix:
        return text
    return f"{text[:prefix]}..."


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


def _compact_direction(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"bull", "bullish"}:
        return "Bull"
    if text in {"bear", "bearish"}:
        return "Bear"
    return str(value or "")


def _compact_state(value: object) -> str:
    return STATE_LABELS.get(str(value or "").strip().upper(), str(value or ""))


def _compact_family(value: object) -> str:
    text = str(value or "").strip()
    return FAMILY_LABELS.get(text, text.replace("_", " ").title())


def _finite_float(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _percent_label(value: object) -> str:
    numeric = _finite_float(value)
    return "" if numeric is None else f"{numeric:.1%}"


def _decimal_label(value: object, *, digits: int = 2) -> str:
    special = special_value_label(value)
    if special is not None:
        return special
    numeric = _finite_float(value)
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


def _model_option_label(model: RegisteredModel) -> str:
    return (
        f"{_short_identifier(model.model_id)} | {_compact_state(model.state)} | "
        f"{_compact_direction(model.direction)} h{model.horizon} | "
        f"{_compact_family(model.family)}"
    )


def _detail_rows(model: RegisteredModel) -> pd.DataFrame:
    rows: list[dict[str, object]] = [
        {"Field": "Full model ID", "Value": model.model_id},
        {"Field": "State", "Value": model.state},
        {"Field": "Task", "Value": model.task},
        {"Field": "Direction", "Value": model.direction},
        {"Field": "Horizon", "Value": model.horizon},
        {"Field": "Family", "Value": model.family},
        {
            "Field": "Product-class scope",
            "Value": model.metrics.get("product_class_scope", "POOLED"),
        },
        {
            "Field": "Product-class schema",
            "Value": model.metrics.get("product_class_schema_version", ""),
        },
        {
            "Field": "Product-class eligible roles",
            "Value": model.metrics.get("product_class_eligible_roles_json", ""),
        },
        {
            "Field": "Product-class scope hash",
            "Value": model.metrics.get("product_class_scope_configuration_hash", ""),
        },
        {
            "Field": "Product-class universe-scope hash",
            "Value": model.metrics.get("product_class_universe_scope_hash", ""),
        },
        {"Field": "Training window", "Value": f"{model.training_start} to {model.training_end}"},
        {
            "Field": "Calibration window",
            "Value": f"{model.validation_start} to {model.validation_end}",
        },
        {"Field": "Holdout window", "Value": f"{model.holdout_start} to {model.holdout_end}"},
        {"Field": "Universe snapshot", "Value": model.universe_snapshot_id},
        {"Field": "Feature manifest", "Value": model.feature_manifest_hash},
        {"Field": "Artifact path", "Value": model.artifact_path},
        {"Field": "Code commit", "Value": model.code_commit_hash or ""},
        {"Field": "Created UTC", "Value": model.created_at_utc},
        {"Field": "Promoted UTC", "Value": model.promoted_at_utc or ""},
        {"Field": "Retirement reason", "Value": model.retirement_reason or ""},
    ]
    return pd.DataFrame(rows)


def _metric_rows(title: str, values: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Group": title, "Metric": key, "Value": value} for key, value in values.items()]
    )


def _gate_audit_rows(model: RegisteredModel) -> pd.DataFrame:
    rows = []
    for gate in model.gate_results:
        item = gate_results_to_jsonable((gate,))[0]
        rows.append(
            {
                "Gate": item["gate_name"],
                "Actual": display_gate_value(item["actual_value"]),
                "Comparator": item["comparator"],
                "Threshold": display_gate_value(item["threshold"]),
                "Status": item["status"],
                "Reason": item["reason"],
                "Mandatory": item["mandatory"],
                "Evidence": item["evidence_source"],
                "Evidence warning": gate_result_integrity_warning(gate),
            }
        )
    return pd.DataFrame(rows)


def _json_records(value: object) -> pd.DataFrame:
    if not isinstance(value, str) or not value.strip():
        return pd.DataFrame()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return pd.DataFrame()
    if not isinstance(payload, list):
        return pd.DataFrame()
    return pd.DataFrame([item for item in payload if isinstance(item, dict)])


def _read_optional_csv(value: object) -> pd.DataFrame:
    if not isinstance(value, str) or not value.strip():
        return pd.DataFrame()
    path = Path(value)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame()


def _safe_parse_dict(value: object) -> dict[str, object]:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _metric_subset(model: RegisteredModel, patterns: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for group, values in (("Metrics", model.metrics), ("Calibration", model.calibration_metrics)):
        for key, value in values.items():
            if any(pattern in key for pattern in patterns):
                rows.append({"Group": group, "Metric": key, "Value": value})
    return pd.DataFrame(rows)


def _download_frame(label: str, frame: pd.DataFrame, filename: str) -> None:
    streamlit = st()
    csv = frame.to_csv(index=False).encode("utf-8")
    streamlit.download_button(
        label,
        data=csv,
        file_name=filename,
        mime="text/csv",
    )


def _render_generation_exports(root: str | Path) -> None:
    streamlit = st()
    try:
        audit = build_model_audit(root)
    except ValueError:
        return
    streamlit.caption(f"Latest generation audit export: {audit.generation_id}")
    columns = streamlit.columns(3)
    with columns[0]:
        _download_frame("Export model summary CSV", audit.summary, "latest_model_summary.csv")
    with columns[1]:
        _download_frame("Export gate audit CSV", audit.gates, "latest_gate_audit.csv")
    with columns[2]:
        streamlit.download_button(
            "Export gate audit JSON",
            data=json.dumps(
                audit.gates.to_dict(orient="records"),
                indent=2,
                sort_keys=True,
            ).encode("utf-8"),
            file_name="latest_gate_audit.json",
            mime="application/json",
        )


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Model Registry", "Champion, challenger, candidate, rejected, and retired model versions."
    )
    models = list_registered_models(root)
    if not models:
        streamlit.info("No model registry entries yet.")
        return
    streamlit.caption(
        "Compact default view. Select a row below to inspect full IDs, hashes, metrics, and gates."
    )
    streamlit.warning("Product-class specialist challenger. Development evidence only.")
    _render_generation_exports(root)
    streamlit.dataframe(
        compact_registry_rows(models),
        width="stretch",
        hide_index=True,
        column_config={
            "ID": streamlit.column_config.TextColumn(
                "ID",
                width="small",
                help="Short display ID. Full model ID is shown in Selected Model Details.",
            ),
            "State": streamlit.column_config.TextColumn(
                "State",
                width="small",
                help="EXP, CAND, CHAL, CHAMP, RET, or REJ.",
            ),
            "Dir": streamlit.column_config.TextColumn("Dir", width="small"),
            "Hz": streamlit.column_config.NumberColumn("Hz", width="small"),
            "Family": streamlit.column_config.TextColumn("Family", width="small"),
            "Scope": streamlit.column_config.TextColumn("Scope", width="small"),
            "Created": streamlit.column_config.TextColumn("Created", width="small"),
            "Train": streamlit.column_config.NumberColumn("Train", width="small"),
            "Holdout": streamlit.column_config.NumberColumn("Holdout", width="small"),
            "Sel": streamlit.column_config.NumberColumn(
                "Sel",
                width="small",
                help="Selected holdout observations.",
            ),
            "Sel%": streamlit.column_config.TextColumn("Sel%", width="small"),
            "Win": streamlit.column_config.TextColumn("Win", width="small"),
            "EV LCB": streamlit.column_config.TextColumn(
                "EV LCB",
                width="small",
                help="90% lower confidence bound of selected holdout mean return.",
            ),
            "PF": streamlit.column_config.TextColumn("PF", width="small"),
            "Port DD": streamlit.column_config.TextColumn(
                "Port DD",
                width="small",
                help="Portfolio maximum drawdown from daily equity, not row sequence.",
            ),
            "Brier": streamlit.column_config.TextColumn("Brier", width="small"),
            "BSS": streamlit.column_config.TextColumn("BSS", width="small"),
            "Fail": streamlit.column_config.NumberColumn("Fail", width="small"),
            "NCfg": streamlit.column_config.NumberColumn("NCfg", width="small"),
            "Elig": streamlit.column_config.TextColumn("Elig", width="small"),
        },
    )
    selected_model = streamlit.selectbox(
        "Selected model details",
        options=models,
        format_func=_model_option_label,
    )
    eligibility = promotion_eligibility(selected_model.gate_results)
    streamlit.caption(
        "Promotion eligible: "
        f"{'yes' if eligibility.eligible else 'no'}; "
        f"failed={eligibility.mandatory_failed}, "
        f"not configured={eligibility.not_configured}, "
        f"not applicable={eligibility.not_applicable}."
    )
    with streamlit.expander("Selected Model Audit", expanded=False):
        tabs = streamlit.tabs(
            [
                "Gate Audit",
                "Calibration",
                "Candidate Selection",
                "Portfolio Holdout",
                "Stability",
                "Feature Diagnostics",
                "Target-Before-Stop Screen",
                "Path-Metric Screens",
                "Target-Before-Stop Calibration",
                "Prediction Sanity",
                "Artifact Metadata",
            ]
        )
        gate_frame = _gate_audit_rows(selected_model)
        with tabs[0]:
            streamlit.dataframe(display_frame(gate_frame), width="stretch", hide_index=True)
            _download_frame(
                "Export full gate-audit CSV",
                gate_frame,
                f"{selected_model.model_id}_gate_audit.csv",
            )
            streamlit.download_button(
                "Export gate-audit JSON",
                data=json.dumps(
                    gate_results_to_jsonable(selected_model.gate_results),
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8"),
                file_name=f"{selected_model.model_id}_gate_audit.json",
                mime="application/json",
            )
        with tabs[1]:
            calibration_table = _json_records(selected_model.metrics.get("calibration_table_json"))
            calibration_metrics = _metric_rows("Calibration", selected_model.calibration_metrics)
            streamlit.dataframe(
                display_frame(calibration_metrics), width="stretch", hide_index=True
            )
            streamlit.dataframe(display_frame(calibration_table), width="stretch", hide_index=True)
            _download_frame(
                "Export calibration table",
                calibration_table,
                f"{selected_model.model_id}_calibration.csv",
            )
        with tabs[2]:
            selection = _metric_subset(
                selected_model,
                (
                    "selected",
                    "candidate",
                    "selection_policy",
                    "prediction_turnover",
                    "concentration",
                    "profit_factor",
                    "holdout_mean",
                ),
            )
            selected_ledger = _json_records(
                selected_model.metrics.get("selected_candidate_ledger_json")
            )
            streamlit.dataframe(display_frame(selection), width="stretch", hide_index=True)
            streamlit.dataframe(
                display_frame(selected_ledger.head(500)), width="stretch", hide_index=True
            )
            _download_frame(
                "Export selected candidate ledger",
                selected_ledger,
                f"{selected_model.model_id}_selected_candidates.csv",
            )
        with tabs[3]:
            portfolio = _metric_subset(
                selected_model,
                ("portfolio_", "selected_row_sequence_drawdown"),
            )
            daily_equity = _json_records(selected_model.metrics.get("portfolio_daily_equity_json"))
            streamlit.dataframe(display_frame(portfolio), width="stretch", hide_index=True)
            streamlit.dataframe(
                display_frame(daily_equity.head(500)), width="stretch", hide_index=True
            )
            _download_frame(
                "Export portfolio daily equity",
                daily_equity,
                f"{selected_model.model_id}_portfolio_daily_equity.csv",
            )
        with tabs[4]:
            stability = _metric_subset(
                selected_model,
                (
                    "stability",
                    "regime",
                    "sector",
                    "symbol",
                    "temporal",
                    "period",
                ),
            )
            streamlit.dataframe(display_frame(stability), width="stretch", hide_index=True)
        with tabs[5]:
            feature_counts = _json_records(
                selected_model.metrics.get("selected_feature_family_counts_json")
            )
            if feature_counts.empty:
                try:
                    parsed = json.loads(
                        str(selected_model.metrics.get("selected_feature_family_counts_json"))
                    )
                except (TypeError, json.JSONDecodeError):
                    feature_counts = pd.DataFrame()
                else:
                    if isinstance(parsed, dict):
                        feature_counts = pd.DataFrame(
                            [
                                {"Family": key, "Selected Features": value}
                                for key, value in parsed.items()
                            ]
                        )
            diagnostics = _metric_subset(
                selected_model,
                ("feature", "permutation", "mutual_information"),
            )
            streamlit.dataframe(display_frame(feature_counts), width="stretch", hide_index=True)
            streamlit.dataframe(display_frame(diagnostics), width="stretch", hide_index=True)
        with tabs[6]:
            screen_metadata = _json_records(
                selected_model.metrics.get("target_before_stop_feature_screen_audit_json")
            )
            top_mi = _json_records(
                selected_model.metrics.get("target_before_stop_top_25_train_mi_features_json")
            )
            tbs_feature_counts = _json_records(
                selected_model.metrics.get("target_before_stop_selected_feature_family_counts_json")
            )
            if tbs_feature_counts.empty:
                parsed = _safe_parse_dict(
                    selected_model.metrics.get(
                        "target_before_stop_selected_feature_family_counts_json"
                    )
                )
                tbs_feature_counts = pd.DataFrame(
                    [
                        {"Family": family, "Selected Features": count}
                        for family, count in parsed.items()
                    ]
                )
            screen_summary = _metric_subset(
                selected_model,
                (
                    "target_before_stop_feature_screen",
                    "target_before_stop_screening",
                    "target_before_stop_selected_feature",
                    "target_before_stop_top_25",
                    "target_before_stop_permutation",
                ),
            )
            streamlit.dataframe(display_frame(screen_summary), width="stretch", hide_index=True)
            streamlit.dataframe(display_frame(tbs_feature_counts), width="stretch", hide_index=True)
            streamlit.dataframe(display_frame(top_mi), width="stretch", hide_index=True)
            streamlit.dataframe(
                display_frame(screen_metadata.head(500)), width="stretch", hide_index=True
            )
            _download_frame(
                "Export target-before-stop feature screen",
                screen_metadata,
                f"{selected_model.model_id}_target_before_stop_feature_screen.csv",
            )
        with tabs[7]:
            path_rows: list[pd.DataFrame] = []
            for head, prefix in (
                ("Expected Return", "expected_return"),
                ("MFE", "mfe"),
                ("MAE", "mae"),
            ):
                summary = _metric_subset(
                    selected_model,
                    (
                        f"{prefix}_feature_screen",
                        f"{prefix}_screening",
                        f"{prefix}_selected_feature",
                        f"{prefix}_top_25",
                        f"{prefix}_permutation",
                        f"{prefix}_domain",
                        f"{prefix}_path_head",
                        f"{prefix}_external_target",
                        f"{prefix}_internal_magnitude",
                        f"{prefix}_internal_target",
                        f"{prefix}_magnitude_estimator",
                        f"{prefix}_prediction_mapping",
                        f"{prefix}_holdout_domain",
                    ),
                )
                if not summary.empty:
                    summary.insert(0, "Head", head)
                    path_rows.append(summary)
                top_mi = _json_records(
                    selected_model.metrics.get(f"{prefix}_top_25_train_mi_features_json")
                )
                if not top_mi.empty:
                    top_mi.insert(0, "Head", head)
                    path_rows.append(top_mi)
            path_screen_frame = (
                pd.concat(path_rows, ignore_index=True) if path_rows else pd.DataFrame()
            )
            streamlit.dataframe(
                display_frame(path_screen_frame.head(1_000)), width="stretch", hide_index=True
            )
            _download_frame(
                "Export path-metric feature screens",
                path_screen_frame,
                f"{selected_model.model_id}_path_metric_feature_screens.csv",
            )
        with tabs[8]:
            streamlit.warning(
                "Current holdout metrics are DEVELOPMENT HOLDOUT DIAGNOSTICS, not final validation."
            )
            method_comparison = _json_records(
                selected_model.metrics.get("target_before_stop_calibration_candidate_results_json")
            )
            fold_metrics = _json_records(
                selected_model.metrics.get("target_before_stop_calibration_fold_results_json")
            )
            step_support = _json_records(
                selected_model.metrics.get("target_before_stop_step_support_json")
            )
            threshold_utility = _read_optional_csv(
                selected_model.metrics.get("target_before_stop_calibration_threshold_utility_path")
            )
            calibration_summary = _metric_subset(
                selected_model,
                (
                    "target_before_stop_calibration",
                    "target_before_stop_raw_score_distribution",
                    "target_before_stop_calibrated_score_distribution",
                    "target_before_stop_plateau",
                    "target_before_stop_step_support",
                    "target_before_stop_development_holdout",
                ),
            )
            streamlit.dataframe(
                display_frame(calibration_summary), width="stretch", hide_index=True
            )
            streamlit.dataframe(display_frame(method_comparison), width="stretch", hide_index=True)
            streamlit.dataframe(display_frame(fold_metrics), width="stretch", hide_index=True)
            streamlit.dataframe(display_frame(step_support), width="stretch", hide_index=True)
            streamlit.dataframe(display_frame(threshold_utility), width="stretch", hide_index=True)
            _download_frame(
                "Export target-before-stop calibration methods",
                method_comparison,
                f"{selected_model.model_id}_target_before_stop_calibration_methods.csv",
            )
        with tabs[9]:
            sanity = _metric_subset(
                selected_model,
                (
                    "prediction",
                    "target",
                    "unit",
                    "return_",
                    "mfe_",
                    "mae_",
                ),
            )
            streamlit.dataframe(display_frame(sanity), width="stretch", hide_index=True)
        with tabs[10]:
            streamlit.dataframe(
                display_frame(_detail_rows(selected_model)),
                width="stretch",
                hide_index=True,
            )

    challengers = [model for model in models if model.state in {"CHALLENGER", "CANDIDATE"}]
    if challengers:
        with streamlit.form("promote_model_form"):
            selected = streamlit.selectbox(
                "Model to promote",
                options=challengers,
                format_func=_model_option_label,
            )
            selected_eligibility = promotion_eligibility(selected.gate_results)
            if not selected_eligibility.eligible:
                streamlit.caption(
                    "Promotion blocked: " + " | ".join(selected_eligibility.blocked_reasons[:3])
                )
            submitted = streamlit.form_submit_button(
                "Promote model",
                disabled=not selected_eligibility.eligible,
            )
        if submitted:
            try:
                promoted = promote_registered_model(root, selected.model_id)
            except ValueError as exc:
                streamlit.error(str(exc))
            else:
                streamlit.success(f"Promoted champion: {promoted.model_id}")


if __name__ == "__main__":
    render_page()
