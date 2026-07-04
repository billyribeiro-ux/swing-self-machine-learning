from __future__ import annotations

import json

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.application.dashboard_service import (
    candidate_detail_url,
    scanner_results_frame,
    time_exit_diagnostic_status_frame,
)
from swing_rsi.application.footprint_attribution import (
    FOOTPRINT_DISPLAY_COLUMNS,
    footprint_evidence_frames,
    missing_evidence_audit_frame,
)

BLOCKED_ANALOG_TABLE_COLUMNS = [
    "analog_rank",
    "analog_date",
    "ticker",
    "scope",
    "archetype",
    "similarity",
    "forward_return",
    "MFE",
    "MAE",
    "target_before_stop_result",
    "same_product_scope",
    "same_archetype",
]


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


def _identifier_lookup(identifiers: pd.DataFrame) -> dict[str, str]:
    if identifiers.empty:
        return {}
    return {
        str(row.get("field", "")): _clean_identifier_value(row.get("value", ""))
        for _, row in identifiers.iterrows()
    }


def _candidate_detail_deep_link(identifiers: pd.DataFrame) -> str:
    values = _identifier_lookup(identifiers)
    return candidate_detail_url(
        scan_id=values.get("scan_id", ""),
        ticker=values.get("ticker", ""),
        model_id=values.get("model_id", ""),
        direction=values.get("direction", ""),
        run_id=values.get("run_id", ""),
        event_id=values.get("event_id", ""),
        status=values.get("status", ""),
    )


def _deep_link_frame(deep_link: str) -> pd.DataFrame:
    return pd.DataFrame([{"field": "candidate_detail_url", "value": deep_link}])


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
        "target_stop_policy_display",
        "target_stop_policy_status",
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
        ("stop/target policy", candidate.get("target_stop_policy_display", "")),
        ("time horizon", candidate.get("horizon", "")),
        ("drawdown/gate limitations", candidate.get("gate_status", "")),
    )
    return pd.DataFrame([{"risk": label, "value": str(value)} for label, value in fields])


def _policy_overview_frame(candidate: pd.Series) -> pd.DataFrame:
    if not _clean_identifier_value(candidate.get("target_stop_policy_display", "")):
        return pd.DataFrame()
    fields = (
        ("Target/Stop Policy", candidate.get("target_stop_policy_display", "")),
        ("Policy status", candidate.get("target_stop_policy_status", "")),
        ("Target ATR multiple", candidate.get("target_stop_policy_target_multiple", "")),
        ("Stop ATR multiple", candidate.get("target_stop_policy_stop_multiple", "")),
        ("Horizon", candidate.get("horizon", "")),
        ("Policy ID", candidate.get("target_stop_policy_id", "")),
        ("Policy hash", candidate.get("target_stop_policy_hash", "")),
        (
            "Why this policy exists",
            "STOP_TOO_TIGHT calibration diagnostic for Sector Rotation BUY ORDINARY.",
        ),
    )
    return pd.DataFrame(
        [
            {"field": field, "value": _clean_identifier_value(value)}
            for field, value in fields
            if _clean_identifier_value(value)
        ]
    )


def _blocked_row_analog_summary_frame(candidate: pd.Series) -> pd.DataFrame:
    raw = candidate.get("blocked_row_analog_summary", "")
    if not isinstance(raw, str) or not raw.strip():
        return pd.DataFrame()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return pd.DataFrame()
    if not isinstance(payload, dict):
        return pd.DataFrame()
    return pd.DataFrame([payload])


def _single_json_frame(candidate: pd.Series, field: str) -> pd.DataFrame:
    raw = candidate.get(field, "")
    if not isinstance(raw, str) or not raw.strip():
        return pd.DataFrame()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return pd.DataFrame()
    if not isinstance(payload, dict):
        return pd.DataFrame()
    return pd.DataFrame([payload])


def _records_json_frame(candidate: pd.Series, field: str) -> pd.DataFrame:
    raw = candidate.get(field, "")
    if not isinstance(raw, str) or not raw.strip():
        return pd.DataFrame()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return pd.DataFrame()
    if not isinstance(payload, list):
        return pd.DataFrame()
    return pd.DataFrame(payload)


def _blocked_analog_table(analogs: pd.DataFrame) -> pd.DataFrame:
    if analogs.empty:
        return pd.DataFrame(columns=BLOCKED_ANALOG_TABLE_COLUMNS)
    output = analogs.copy()
    if "ticker" not in output.columns and "symbol" in output.columns:
        output["ticker"] = output["symbol"]
    for column in BLOCKED_ANALOG_TABLE_COLUMNS:
        if column not in output.columns:
            output[column] = "Not available"
    return output[BLOCKED_ANALOG_TABLE_COLUMNS]


def _calibration_overview_frame(candidate: pd.Series) -> pd.DataFrame:
    has_calibration_artifact = any(
        _clean_identifier_value(candidate.get(field, ""))
        for field in (
            "calibration_summary_json",
            "calibration_diagnostic_threshold_table",
            "calibration_probability_bucket_evidence",
        )
    )
    if not has_calibration_artifact:
        return pd.DataFrame()
    fields = (
        ("model TBS probability", candidate.get("target_before_stop_probability", "")),
        (
            "same-archetype calibration base rate",
            candidate.get("same_archetype_calibration_base_rate", ""),
        ),
        ("same-scope calibration base rate", candidate.get("same_scope_calibration_base_rate", "")),
        ("calibration evidence status", candidate.get("calibration_evidence_status", "")),
        (
            "TBS blocker calibration assessment",
            candidate.get("tbs_blocker_calibration_assessment", ""),
        ),
    )
    return pd.DataFrame(
        [
            {"field": field, "value": _clean_identifier_value(value)}
            for field, value in fields
            if _clean_identifier_value(value)
        ]
    )


def _metric_percent(value: object) -> str:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "Not available"
    if pd.isna(numeric):
        return "Not available"
    return f"{numeric:.2%}"


def _signal_score_frame(candidate: pd.Series) -> pd.DataFrame:
    fields = (
        ("action", "Action"),
        ("archetype", "Archetype"),
        ("hypothesis_id", "Hypothesis ID"),
        ("signal_score", "Signal Score"),
        ("probability", "Direction Probability"),
        ("target_before_stop_probability", "Target-Before-Stop Probability"),
        ("expected_return", "Expected Return"),
        ("expected_mfe", "Expected MFE"),
        ("expected_mae", "Expected MAE"),
        ("composite_utility_score", "Risk-Adjusted Utility"),
        ("liquidity_score", "Liquidity Score"),
        ("top_support", "Top Support"),
        ("top_conflict", "Top Conflict"),
        ("historical_analog_support", "Historical Analog Support"),
        ("target_stop_policy_display", "Target/Stop Policy"),
        ("target_stop_policy_status", "Policy Status"),
        ("no_signal_reason", "No-Signal Reason"),
        ("rejection_reason", "Rejection Reason"),
        ("signal_source", "Signal Source"),
    )
    rows = [
        {"component": label, "value": _clean_identifier_value(candidate.get(field, ""))}
        for field, label in fields
        if _clean_identifier_value(candidate.get(field, ""))
    ]
    return pd.DataFrame(rows)


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


def _footprint_summary_text(summary: pd.DataFrame) -> str:
    if summary.empty:
        return "Footprint evidence is unavailable. Review measured evidence rows below."
    row = summary.iloc[0]
    return (
        f"{row.get('ticker', 'Candidate')} {row.get('direction', '')}: "
        f"{row.get('summary', '')} "
        "This is model evidence for shadow validation, not live actionable guidance."
    ).strip()


def _render_missing_evidence_audit(audit: pd.DataFrame) -> None:
    streamlit = st()
    unavailable = 0
    affected = 0
    top_category = "None"
    if not audit.empty and "Unavailable Evidence Rows" in audit.columns:
        counts = pd.to_numeric(audit["Unavailable Evidence Rows"], errors="coerce").fillna(0)
        unavailable = int(counts.sum())
        affected = int((counts > 0).sum())
        if unavailable:
            top_category = str(audit.iloc[int(counts.idxmax())]["Category"])
    columns = streamlit.columns(3)
    columns[0].metric("Missing evidence rows", f"{unavailable:,}")
    columns[1].metric("Categories affected", f"{affected:,}")
    columns[2].metric("Top missing category", top_category)
    if unavailable:
        streamlit.warning(
            "Evidence unavailable rows are explicit; missing data is not treated as confirmed."
        )
    else:
        streamlit.success(
            "Missing evidence audit: all displayed footprint evidence rows have values."
        )
    with streamlit.expander("Missing Evidence Audit", expanded=bool(unavailable)):
        streamlit.dataframe(display_frame(audit), width="stretch", hide_index=True)


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
    deep_link = _candidate_detail_deep_link(identifiers)
    deep_link_export = _deep_link_frame(deep_link)
    footprint = footprint_evidence_frames(root, candidate)
    missing_audit = missing_evidence_audit_frame(footprint.evidence)
    summary = _summary_frame(candidate)
    signal_score = _signal_score_frame(candidate)
    checks = _checks_frame(candidate)
    attribution = _attribution_frame(candidate)
    analogs = footprint.historical_analogs
    blocked_analog_summary = _blocked_row_analog_summary_frame(candidate)
    analog_robustness = _single_json_frame(candidate, "analog_robustness")
    analog_depth_comparison = _records_json_frame(candidate, "analog_depth_comparison")
    analog_caution_flags = _records_json_frame(candidate, "analog_caution_flags")
    calibration_overview = _calibration_overview_frame(candidate)
    calibration_summary = _single_json_frame(candidate, "calibration_summary_json")
    calibration_thresholds = _records_json_frame(
        candidate, "calibration_diagnostic_threshold_table"
    )
    calibration_buckets = _records_json_frame(candidate, "calibration_probability_bucket_evidence")
    policy_overview = _policy_overview_frame(candidate)
    policy_registry = _records_json_frame(candidate, "target_stop_policy_registry_json")
    policy_selection = _records_json_frame(candidate, "target_stop_policy_selection_evidence")
    policy_comparison = _records_json_frame(candidate, "target_stop_policy_comparison_json")
    derived_policy_outcome = _records_json_frame(candidate, "derived_policy_outcome_json")
    signal_policy_comparison = _records_json_frame(
        candidate,
        "signal_discovery_policy_comparison_json",
    )
    time_exit_labels = _records_json_frame(candidate, "time_exit_utility_labels_json")
    time_exit_summary = _records_json_frame(
        candidate,
        "time_exit_utility_calibration_summary_json",
    )
    time_exit_signal_rows = _records_json_frame(candidate, "time_exit_utility_signal_row_json")
    time_exit_policy_comparison = _records_json_frame(
        candidate,
        "time_exit_utility_policy_comparison_json",
    )
    prospective_time_exit_observation = _single_json_frame(
        candidate,
        "time_exit_diagnostic_observation_json",
    )
    prospective_time_exit_matured = _single_json_frame(
        candidate,
        "time_exit_diagnostic_matured_outcome_json",
    )
    prospective_time_exit_status = time_exit_diagnostic_status_frame(root)
    feature_snapshot = pd.DataFrame([candidate.to_dict()])
    risk = _risk_frame(candidate)

    streamlit.info(_footprint_summary_text(footprint.summary))
    _render_missing_evidence_audit(missing_audit)
    if not signal_score.empty:
        streamlit.subheader("Signal Score Breakdown")
        streamlit.dataframe(display_frame(signal_score), width="stretch", hide_index=True)

    streamlit.subheader("Full Raw Identifiers")
    with streamlit.expander("Full Raw Identifier Copy Block", expanded=False):
        streamlit.dataframe(display_frame(identifiers), width="stretch", hide_index=True)
        streamlit.code(_identifier_copy_text(identifiers), language="text")
        streamlit.caption("Candidate Detail deep link")
        streamlit.code(deep_link, language="text")

    streamlit.subheader("Footprint Evidence Table")
    streamlit.dataframe(
        footprint.evidence[FOOTPRINT_DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
    )
    render_table_downloads(
        footprint.summary,
        basename="candidate_detail_footprint_summary",
        label="footprint_summary",
    )
    render_table_downloads(
        footprint.evidence,
        basename="candidate_detail_footprint_evidence",
        label="footprint_evidence",
    )

    streamlit.subheader("Supporting Evidence")
    streamlit.dataframe(
        footprint.supporting_evidence[FOOTPRINT_DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
    )
    render_table_downloads(
        footprint.supporting_evidence,
        basename="candidate_detail_supporting_evidence",
        label="supporting_evidence",
    )

    streamlit.subheader("Conflicting Evidence")
    streamlit.dataframe(
        footprint.conflicting_evidence[FOOTPRINT_DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
    )
    render_table_downloads(
        footprint.conflicting_evidence,
        basename="candidate_detail_conflicting_evidence",
        label="conflicting_evidence",
    )

    streamlit.subheader("Signal Summary")
    streamlit.dataframe(display_frame(summary), width="stretch", hide_index=True)

    streamlit.subheader("Why this appeared")
    streamlit.dataframe(display_frame(checks), width="stretch", hide_index=True)

    streamlit.subheader("Attribution")
    streamlit.dataframe(display_frame(attribution), width="stretch", hide_index=True)

    streamlit.subheader("Risk")
    streamlit.dataframe(display_frame(risk), width="stretch", hide_index=True)

    if not policy_overview.empty:
        streamlit.subheader("Target/Stop Policy")
        streamlit.warning(
            "Experimental target/stop policy. Development evidence only. Not a live signal."
        )
        streamlit.dataframe(display_frame(policy_overview), width="stretch", hide_index=True)
        if not policy_comparison.empty:
            streamlit.caption("Baseline versus experimental policy")
            streamlit.dataframe(display_frame(policy_comparison), width="stretch", hide_index=True)
        if not policy_selection.empty:
            streamlit.caption("Calibration-only selection evidence")
            streamlit.dataframe(display_frame(policy_selection), width="stretch", hide_index=True)
        if not derived_policy_outcome.empty:
            streamlit.caption("Target/stop path diagnostics")
            streamlit.dataframe(
                display_frame(derived_policy_outcome),
                width="stretch",
                hide_index=True,
            )
        if not signal_policy_comparison.empty:
            streamlit.caption("Signal-discovery policy comparison")
            streamlit.dataframe(
                display_frame(signal_policy_comparison),
                width="stretch",
                hide_index=True,
            )
        render_table_downloads(
            policy_overview,
            basename="candidate_detail_target_stop_policy",
            label="target_stop_policy",
        )
        render_table_downloads(
            policy_registry,
            basename="candidate_detail_target_stop_policy_registry",
            label="target_stop_policy_registry",
        )
        render_table_downloads(
            policy_comparison,
            basename="candidate_detail_policy_comparison",
            label="policy_comparison",
        )
        render_table_downloads(
            policy_selection,
            basename="candidate_detail_policy_selection",
            label="policy_selection",
        )
        render_table_downloads(
            derived_policy_outcome,
            basename="candidate_detail_derived_policy_outcome",
            label="derived_policy_outcome",
        )

    if (
        _clean_identifier_value(candidate.get("time_exit_label_schema_version", ""))
        or not time_exit_labels.empty
        or not time_exit_summary.empty
    ):
        streamlit.subheader("Time-Exit Utility Diagnostic")
        streamlit.warning(
            "Time-exit utility is diagnostic. It does not override gates or create a live signal."
        )
        overview = pd.DataFrame(
            [
                {
                    "Metric": "TBS probability",
                    "Value": candidate.get("target_before_stop_probability", ""),
                },
                {
                    "Metric": "Time-exit positive probability",
                    "Value": candidate.get("time_exit_positive_probability", ""),
                },
                {
                    "Metric": "Expected time-exit return",
                    "Value": candidate.get("expected_time_exit_return", ""),
                },
                {
                    "Metric": "Expected time-exit utility",
                    "Value": candidate.get("expected_time_exit_utility", ""),
                },
                {
                    "Metric": "Profitable despite failed TBS probability",
                    "Value": candidate.get("profitable_despite_failed_tbs_probability", ""),
                },
                {
                    "Metric": "Early adverse recovery probability",
                    "Value": candidate.get("early_adverse_recovery_probability", ""),
                },
                {
                    "Metric": "Why not live actionable",
                    "Value": candidate.get("not_live_actionable_reason", ""),
                },
            ]
        )
        streamlit.dataframe(display_frame(overview), width="stretch", hide_index=True)
        if not time_exit_labels.empty:
            streamlit.caption("Baseline and experimental policy label-side outcomes")
            streamlit.dataframe(display_frame(time_exit_labels), width="stretch", hide_index=True)
        if not time_exit_summary.empty:
            streamlit.caption("Calibration-only and development-holdout diagnostic summary")
            streamlit.dataframe(display_frame(time_exit_summary), width="stretch", hide_index=True)
        if not time_exit_policy_comparison.empty:
            streamlit.caption("Policy comparison")
            streamlit.dataframe(
                display_frame(time_exit_policy_comparison),
                width="stretch",
                hide_index=True,
            )
        if not time_exit_signal_rows.empty:
            streamlit.caption("Time-exit signal row")
            streamlit.dataframe(
                display_frame(time_exit_signal_rows),
                width="stretch",
                hide_index=True,
            )
        render_table_downloads(
            time_exit_labels,
            basename="candidate_detail_time_exit_utility_labels",
            label="time_exit_utility_labels",
        )
        render_table_downloads(
            time_exit_summary,
            basename="candidate_detail_time_exit_utility_calibration_summary",
            label="time_exit_utility_calibration_summary",
        )
        render_table_downloads(
            time_exit_signal_rows,
            basename="candidate_detail_time_exit_utility_signal_rows",
            label="time_exit_utility_signal_rows",
        )

    if not prospective_time_exit_observation.empty or not prospective_time_exit_matured.empty:
        streamlit.subheader("Prospective Time-Exit Diagnostic")
        streamlit.warning(
            "Prospective time-exit diagnostic is DIAGNOSTIC_ONLY / RESEARCH_OBSERVATION. "
            "It is not a live signal and not final-holdout evidence."
        )
        if not prospective_time_exit_status.empty:
            streamlit.caption("Diagnostic run status")
            streamlit.dataframe(
                display_frame(prospective_time_exit_status),
                width="stretch",
                hide_index=True,
            )
        if not prospective_time_exit_observation.empty:
            streamlit.caption("Observation state")
            streamlit.dataframe(
                display_frame(prospective_time_exit_observation),
                width="stretch",
                hide_index=True,
            )
        if not prospective_time_exit_matured.empty:
            streamlit.caption("Matured time-exit result")
            streamlit.dataframe(
                display_frame(prospective_time_exit_matured),
                width="stretch",
                hide_index=True,
            )
        render_table_downloads(
            prospective_time_exit_observation,
            basename="candidate_detail_prospective_time_exit_observation",
            label="prospective_time_exit_observation",
        )
        render_table_downloads(
            prospective_time_exit_matured,
            basename="candidate_detail_prospective_time_exit_matured",
            label="prospective_time_exit_matured",
        )

    if not calibration_overview.empty:
        streamlit.subheader("Calibration Diagnostics")
        streamlit.warning(
            "Calibration diagnostic only. Not a threshold change and not proof of edge."
        )
        streamlit.dataframe(
            display_frame(calibration_overview),
            width="stretch",
            hide_index=True,
        )
        if not calibration_thresholds.empty:
            streamlit.caption("Diagnostic threshold table")
            streamlit.dataframe(
                display_frame(calibration_thresholds),
                width="stretch",
                hide_index=True,
            )
        if not calibration_buckets.empty:
            streamlit.caption("Probability bucket evidence")
            streamlit.dataframe(
                display_frame(calibration_buckets),
                width="stretch",
                hide_index=True,
            )
        render_table_downloads(
            calibration_overview,
            basename="candidate_detail_calibration_overview",
            label="calibration_overview",
        )
        render_table_downloads(
            calibration_summary,
            basename="candidate_detail_calibration_summary",
            label="calibration_summary",
        )
        render_table_downloads(
            calibration_thresholds,
            basename="candidate_detail_calibration_thresholds",
            label="calibration_thresholds",
        )
        render_table_downloads(
            calibration_buckets,
            basename="candidate_detail_calibration_buckets",
            label="calibration_buckets",
        )

    if not blocked_analog_summary.empty:
        blocked_summary_row = blocked_analog_summary.iloc[0]
        streamlit.subheader("Historical Analogs for Blocked Row")
        streamlit.warning(
            "Historical analogs are explanatory only and do not override model gates."
        )
        metric_columns = streamlit.columns(6)
        metric_cards = [
            ("analog count", str(blocked_summary_row.get("analog_count", "Not available"))),
            (
                "average forward return",
                _metric_percent(blocked_summary_row.get("average_forward_return")),
            ),
            (
                "target-before-stop hit rate",
                _metric_percent(blocked_summary_row.get("target_before_stop_hit_rate")),
            ),
            ("average MFE", _metric_percent(blocked_summary_row.get("average_MFE"))),
            ("worst MAE", _metric_percent(blocked_summary_row.get("worst_MAE"))),
            (
                "analog support label",
                str(blocked_summary_row.get("analog_support_label", "Not available")),
            ),
        ]
        for index, (label, value) in enumerate(metric_cards):
            metric_columns[index].metric(label, value)
        if not analog_robustness.empty:
            robustness_row = analog_robustness.iloc[0]
            streamlit.subheader("Historical Analog Robustness")
            robust_columns = streamlit.columns(6)
            depth_labels = {}
            if not analog_depth_comparison.empty and "requested_depth" in analog_depth_comparison:
                for _, depth_row in analog_depth_comparison.iterrows():
                    depth = str(depth_row.get("requested_depth", ""))
                    depth_labels[depth] = str(depth_row.get("depth_support_label", "Not available"))
            robust_cards = [
                ("top-10 support", depth_labels.get("10", "Not available")),
                ("top-25 support", depth_labels.get("25", "Not available")),
                ("top-50 support", depth_labels.get("50", "Not available")),
                (
                    "robust support label",
                    str(robustness_row.get("robust_analog_support_label", "Not available")),
                ),
                (
                    "caution flags",
                    str(robustness_row.get("caution_flags", "") or "None"),
                ),
                (
                    "too concentrated",
                    str(robustness_row.get("analog_evidence_too_concentrated", "Not available")),
                ),
            ]
            for index, (label, value) in enumerate(robust_cards):
                robust_columns[index].metric(label, value)
            explanation = str(robustness_row.get("robustness_explanation", "Not available"))
            if str(robustness_row.get("robust_analog_support_label")) == "CONCENTRATION_ARTIFACT":
                streamlit.warning(
                    "Top-10 analogs are not robust because they are concentrated and "
                    f"support degrades when expanded. {explanation}"
                )
            else:
                streamlit.info(explanation)
            if not analog_depth_comparison.empty:
                streamlit.caption("Analog depth comparison")
                streamlit.dataframe(
                    display_frame(analog_depth_comparison),
                    width="stretch",
                    hide_index=True,
                )
            if not analog_caution_flags.empty:
                streamlit.caption("Analog caution flags")
                streamlit.dataframe(
                    display_frame(analog_caution_flags),
                    width="stretch",
                    hide_index=True,
                )
        blocked_table = _blocked_analog_table(analogs)
        if blocked_table.empty:
            streamlit.info("No blocked-row analog records are available for this candidate.")
        else:
            streamlit.dataframe(display_frame(blocked_table), width="stretch", hide_index=True)
        render_table_downloads(
            blocked_table,
            basename="candidate_detail_blocked_row_analogs",
            label="blocked_row_analogs",
        )
        render_table_downloads(
            blocked_analog_summary,
            basename="candidate_detail_blocked_row_analog_summary",
            label="blocked_row_analog_summary",
        )
        render_table_downloads(
            analog_robustness,
            basename="candidate_detail_analog_robustness",
            label="analog_robustness",
        )
        render_table_downloads(
            analog_depth_comparison,
            basename="candidate_detail_analog_depth_comparison",
            label="analog_depth_comparison",
        )
        render_table_downloads(
            analog_caution_flags,
            basename="candidate_detail_analog_caution_flags",
            label="analog_caution_flags",
        )
    else:
        streamlit.subheader("Historical Analogs")
        if analogs.empty:
            streamlit.info("No historical analog records are available for this candidate.")
        else:
            streamlit.dataframe(analogs, width="stretch", hide_index=True)
    render_table_downloads(
        analogs,
        basename="candidate_detail_historical_analogs",
        label="historical_analogs",
    )

    streamlit.subheader("Residual / Unexplained")
    streamlit.dataframe(
        display_frame(footprint.residual_unexplained),
        width="stretch",
        hide_index=True,
    )
    render_table_downloads(
        footprint.residual_unexplained,
        basename="candidate_detail_residual_unexplained",
        label="residual_unexplained",
    )

    render_table_downloads(
        attribution, basename="candidate_detail_attribution", label="attribution"
    )
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
    render_table_downloads(
        deep_link_export,
        basename="candidate_detail_deep_link",
        label="deep_link",
    )
    streamlit.download_button(
        "Download candidate detail workbook XLSX",
        data=to_xlsx_bytes(
            {
                "raw_identifiers": identifiers,
                "deep_link": deep_link_export,
                "footprint_summary": footprint.summary,
                "footprint_evidence": footprint.evidence,
                "supporting_evidence": footprint.supporting_evidence,
                "conflicting_evidence": footprint.conflicting_evidence,
                "historical_analogs": analogs,
                "blocked_row_analogs": _blocked_analog_table(analogs),
                "blocked_row_analog_summary": blocked_analog_summary,
                "analog_robustness": analog_robustness,
                "analog_depth_comparison": analog_depth_comparison,
                "analog_caution_flags": analog_caution_flags,
                "calibration_overview": calibration_overview,
                "calibration_summary": calibration_summary,
                "calibration_thresholds": calibration_thresholds,
                "calibration_buckets": calibration_buckets,
                "target_stop_policy": policy_overview,
                "policy_registry": policy_registry,
                "calibration_selection": policy_selection,
                "baseline_vs_candidate": policy_comparison,
                "derived_outcomes": derived_policy_outcome,
                "signal_policy_comparison": signal_policy_comparison,
                "time_exit_labels": time_exit_labels,
                "time_exit_calibration": time_exit_summary,
                "time_exit_signal_rows": time_exit_signal_rows,
                "time_exit_policy_comparison": time_exit_policy_comparison,
                "prospective_time_exit_status": prospective_time_exit_status,
                "prospective_time_exit_observation": prospective_time_exit_observation,
                "prospective_time_exit_matured": prospective_time_exit_matured,
                "residual_unexplained": footprint.residual_unexplained,
                "signal_score_breakdown": signal_score,
                "attribution": attribution,
                "feature_snapshot": feature_snapshot,
            }
        ),
        file_name="candidate_detail_workbook.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    render_page()
