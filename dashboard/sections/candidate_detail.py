from __future__ import annotations

import json

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.application.dashboard_service import scanner_results_frame


def _json_frame(value: object) -> pd.DataFrame:
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


def _query_value(params: object, key: str) -> str:
    if not isinstance(params, dict):
        return ""
    value = params.get(key, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value)


def _clean_identifier_value(value: object) -> str:
    try:
        if bool(pd.isna(value)):  # type: ignore[arg-type]
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text in {"", "Not available", "None", "NaT", "nan"}:
        return ""
    return text


def _first_identifier_value(candidate: pd.Series, params: object, *keys: str) -> str:
    for key in keys:
        value = _clean_identifier_value(_query_value(params, key))
        if value:
            return value
    for key in keys:
        value = _clean_identifier_value(candidate.get(key, ""))
        if value:
            return value
    return "Not available"


def _raw_identifier_frame(candidate: pd.Series, params: object) -> pd.DataFrame:
    fields = (
        ("scan_id", "Scan ID", ("scan_id",)),
        ("ticker", "Ticker", ("ticker",)),
        ("direction", "Direction", ("direction",)),
        ("model_id", "Model ID", ("model_id", "model")),
        ("generation", "Generation", ("generation",)),
        ("run_id", "Run ID", ("run_id",)),
        ("event_id", "Event ID", ("event_id",)),
        ("event_type", "Event Type", ("event_type",)),
        ("status", "Status", ("status", "candidate_classification")),
        ("feature_snapshot_hash", "Feature Snapshot Hash", ("feature_snapshot_hash",)),
    )
    return pd.DataFrame(
        [
            {
                "field": field,
                "label": label,
                "value": _first_identifier_value(candidate, params, *keys),
            }
            for field, label, keys in fields
        ]
    )


def _identifier_copy_text(identifiers: pd.DataFrame) -> str:
    if identifiers.empty:
        return ""
    lines = []
    for _, row in identifiers.iterrows():
        value = _clean_identifier_value(row.get("value", ""))
        if value:
            lines.append(f"{row.get('field', '')}={value}")
    return "\n".join(lines)


def _selectbox_index(options: list[str], requested: str) -> int:
    return options.index(requested) if requested in options else 0


def _select_candidate(frame: pd.DataFrame) -> pd.Series | None:
    streamlit = st()
    if frame.empty:
        return None
    params = dict(streamlit.query_params)
    requested_scan = _query_value(params, "scan_id")
    requested_ticker = _query_value(params, "ticker")
    requested_model = _query_value(params, "model_id") or _query_value(params, "model")
    requested_direction = _query_value(params, "direction")
    columns = streamlit.columns(3)
    scan_options = sorted(frame.get("scan_id", pd.Series(dtype=str)).dropna().astype(str).unique())
    ticker_options = sorted(frame.get("ticker", pd.Series(dtype=str)).dropna().astype(str).unique())
    model_options = sorted(frame.get("model", pd.Series(dtype=str)).dropna().astype(str).unique())
    scan_id = (
        columns[0].selectbox(
            "Scan ID",
            scan_options,
            index=_selectbox_index(scan_options, requested_scan),
        )
        if scan_options
        else ""
    )
    ticker = (
        columns[1].selectbox(
            "Ticker",
            ticker_options,
            index=_selectbox_index(ticker_options, requested_ticker),
        )
        if ticker_options
        else ""
    )
    model = (
        columns[2].selectbox(
            "Model ID",
            model_options,
            index=_selectbox_index(model_options, requested_model),
        )
        if model_options
        else ""
    )
    filtered = frame.copy()
    if scan_id:
        filtered = filtered.loc[filtered["scan_id"].astype(str) == scan_id]
    if ticker:
        filtered = filtered.loc[filtered["ticker"].astype(str) == ticker]
    if model:
        filtered = filtered.loc[filtered["model"].astype(str) == model]
    if requested_direction and "direction" in filtered.columns:
        direction_filtered = filtered.loc[filtered["direction"].astype(str) == requested_direction]
        if not direction_filtered.empty:
            filtered = direction_filtered
    if filtered.empty:
        return None
    if requested_scan or requested_ticker or requested_model:
        streamlit.success("Opened from Signal Board selection.")
    index = streamlit.selectbox("Candidate row", filtered.index.astype(int).tolist())
    return filtered.loc[int(index)]


def _summary_frame(candidate: pd.Series) -> pd.DataFrame:
    fields = (
        "ticker",
        "direction",
        "status",
        "edge_status",
        "entry_rule",
        "as_of_date",
        "model",
        "scope",
        "generation",
    )
    return pd.DataFrame(
        [{"field": field, "value": str(candidate.get(field, ""))} for field in fields]
    )


def _checks_frame(candidate: pd.Series) -> pd.DataFrame:
    checks = (
        ("probability check", candidate.get("probability", "")),
        ("expected-return check", candidate.get("expected_return", "")),
        ("Target-Before-Stop check", candidate.get("target_before_stop_probability", "")),
        ("liquidity check", candidate.get("liquidity_status", "Not available")),
        (
            "path-risk check",
            f"MFE {candidate.get('expected_mfe', '')}; MAE {candidate.get('expected_mae', '')}",
        ),
        ("OOD check", candidate.get("ood_warning", "")),
        ("gate check", candidate.get("gate_status", "")),
    )
    return pd.DataFrame(
        [
            {
                "check": check,
                "evidence": str(value) if str(value).strip() else "Not available",
            }
            for check, value in checks
        ]
    )


def _attribution_frame(candidate: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "section": "Model contribution",
                "value": str(candidate.get("top_attribution_category", "")),
            },
            {
                "section": "Supporting evidence",
                "value": str(candidate.get("supporting_evidence", "")),
            },
            {"section": "Divergences", "value": str(candidate.get("top_divergences", ""))},
            {
                "section": "Historical analog",
                "value": str(candidate.get("historical_analogs", "")),
            },
            {
                "section": "Residual/unexplained",
                "value": str(candidate.get("residual_unexplained", "")),
            },
        ]
    )


def _risk_frame(candidate: pd.Series) -> pd.DataFrame:
    fields = (
        ("expected MFE", candidate.get("expected_mfe", "")),
        ("expected MAE", candidate.get("expected_mae", "")),
        ("stop/target policy", candidate.get("selection_policy_result", "")),
        ("time horizon", candidate.get("horizon", "")),
        ("drawdown/gate limitations", candidate.get("gate_status", "")),
    )
    return pd.DataFrame([{"risk": label, "value": str(value)} for label, value in fields])


def _plain_english(candidate: pd.Series) -> str:
    classification = str(candidate.get("candidate_classification", ""))
    reason = str(candidate.get("rejection_reason", ""))
    if "model_not_promoted" in reason:
        return (
            "This row is rejected because the model is not promoted. "
            "It is visible for research review only."
        )
    if classification == "SHADOW ONLY":
        return "This row is shadow-only because it is collecting prospective validation evidence."
    if classification == "LIVE ACTIONABLE":
        return "This row is live actionable because the model and gates allow scanner action."
    if classification == "RESEARCH ONLY":
        return "This row is research-only and should not be treated as a live signal."
    return "This candidate is shown for model review. Attribution is evidence, not causal proof."


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Candidate Detail",
        "Plain-English row explanation, checks, attribution, analogs, and risk evidence.",
    )
    render_page_guidance(
        tells_you="Why a scanner candidate appeared and why it is actionable, shadow-only, or rejected.",
        next_action=(
            "Read the plain-English reason first, then inspect checks, attribution, analogs, and "
            "risk diagnostics before exporting."
        ),
    )
    streamlit.caption("Attribution does not imply causality.")

    frame = scanner_results_frame(root)
    candidate = _select_candidate(frame)
    if candidate is None:
        streamlit.info("No candidate matches the selected filters.")
        return

    streamlit.info(_plain_english(candidate))

    identifiers = _raw_identifier_frame(candidate, dict(streamlit.query_params))
    summary = _summary_frame(candidate)
    checks = _checks_frame(candidate)
    attribution = _attribution_frame(candidate)
    analogs = _json_frame(candidate.get("historical_analogs", ""))
    feature_snapshot = pd.DataFrame([candidate.to_dict()])
    risk = _risk_frame(candidate)

    streamlit.subheader("Full Raw Identifiers")
    with streamlit.expander("Full Raw Identifier Copy Block", expanded=False):
        streamlit.dataframe(display_frame(identifiers), width="stretch", hide_index=True)
        streamlit.code(_identifier_copy_text(identifiers), language="text")

    streamlit.subheader("Signal Summary")
    streamlit.dataframe(display_frame(summary), width="stretch", hide_index=True)

    streamlit.subheader("Why this appeared")
    streamlit.dataframe(display_frame(checks), width="stretch", hide_index=True)

    streamlit.subheader("Attribution")
    streamlit.dataframe(display_frame(attribution), width="stretch", hide_index=True)

    streamlit.subheader("Risk")
    streamlit.dataframe(display_frame(risk), width="stretch", hide_index=True)

    streamlit.subheader("Historical Analogs")
    if analogs.empty:
        streamlit.info("No historical analog records are available for this candidate.")
    else:
        streamlit.dataframe(display_frame(analogs), width="stretch", hide_index=True)

    render_table_downloads(
        attribution, basename="candidate_detail_attribution", label="attribution"
    )
    render_table_downloads(analogs, basename="candidate_detail_analogs", label="analogs")
    render_table_downloads(
        feature_snapshot,
        basename="candidate_detail_feature_snapshot",
        label="feature_snapshot",
    )
    render_table_downloads(
        identifiers,
        basename="candidate_detail_raw_identifiers",
        label="raw_identifiers",
    )
    streamlit.download_button(
        "Download candidate detail workbook XLSX",
        data=to_xlsx_bytes(
            {
                "raw_identifiers": identifiers,
                "attribution": attribution,
                "analogs": analogs,
                "feature_snapshot": feature_snapshot,
            }
        ),
        file_name="candidate_detail_workbook.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    render_page()
