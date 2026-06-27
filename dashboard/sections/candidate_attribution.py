from __future__ import annotations

import json

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.application.dashboard_service import scanner_rows_frame, scanner_snapshot_list_frame


def _json_records(value: object) -> pd.DataFrame:
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


def _select_candidate(rows: pd.DataFrame) -> pd.Series | None:
    streamlit = st()
    if rows.empty:
        return None
    columns = streamlit.columns(3)
    ticker_options = sorted(rows.get("ticker", pd.Series(dtype=str)).dropna().astype(str).unique())
    model_options = sorted(rows.get("model_id", pd.Series(dtype=str)).dropna().astype(str).unique())
    direction_options = sorted(
        rows.get("direction", pd.Series(dtype=str)).dropna().astype(str).unique()
    )
    ticker = columns[0].selectbox("Ticker", ticker_options) if ticker_options else ""
    model = columns[1].selectbox("Model ID", model_options) if model_options else ""
    direction = columns[2].selectbox("Direction", direction_options) if direction_options else ""
    filtered = rows.copy()
    if ticker:
        filtered = filtered.loc[filtered["ticker"].astype(str) == ticker]
    if model:
        filtered = filtered.loc[filtered["model_id"].astype(str) == model]
    if direction:
        filtered = filtered.loc[filtered["direction"].astype(str) == direction]
    if filtered.empty:
        return None
    index = streamlit.selectbox("Candidate row", filtered.index.astype(int).tolist())
    return filtered.loc[int(index)]


def _head_frame(row: pd.Series, head: str, fields: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "head": head,
                "metric": field,
                "value": str(row.get(field, "")),
            }
            for field in fields
        ]
    )


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Candidate Attribution",
        "Candidate evidence, model contribution, supporting evidence, analogs, and residuals.",
    )
    streamlit.caption("Attribution is model evidence, not causal proof.")
    snapshots = scanner_snapshot_list_frame(root)
    if snapshots.empty:
        streamlit.info("No scanner snapshots are available.")
        return
    scan_id = streamlit.selectbox("Scan ID", snapshots["scan_id"].astype(str).tolist())
    rows = scanner_rows_frame(root, scan_id)
    candidate = _select_candidate(rows)
    if candidate is None:
        streamlit.info("No candidate matches the selected filters.")
        return

    summary_fields = [
        "scan_id",
        "as_of_date",
        "ticker",
        "product_class_scope",
        "direction",
        "model_id",
        "candidate_status",
        "exclusion_reason",
        "feature_snapshot_hash",
        "calibrated_probability",
        "expected_return",
        "expected_mfe",
        "expected_mae",
        "target_before_stop_probability",
    ]
    summary = pd.DataFrame(
        [{"metric": field, "value": str(candidate.get(field, ""))} for field in summary_fields]
    )
    streamlit.subheader("Candidate Summary")
    streamlit.dataframe(display_frame(summary), width="stretch", hide_index=True)

    streamlit.subheader("Model Prediction Values")
    heads = pd.concat(
        [
            _head_frame(
                candidate,
                "primary classifier",
                ("calibrated_probability", "top_attribution_categories"),
            ),
            _head_frame(
                candidate,
                "Target-Before-Stop",
                (
                    "target_before_stop_raw_probability",
                    "target_before_stop_probability",
                    "target_before_stop_calibration_method",
                ),
            ),
            _head_frame(
                candidate,
                "expected return",
                (
                    "expected_return",
                    "expected_return_feature_manifest_hash",
                    "expected_return_ood_severity",
                ),
            ),
            _head_frame(
                candidate,
                "MFE",
                ("expected_mfe", "mfe_feature_manifest_hash", "expected_mfe_ood_severity"),
            ),
            _head_frame(
                candidate,
                "MAE",
                ("expected_mae", "mae_feature_manifest_hash", "expected_mae_ood_severity"),
            ),
        ],
        ignore_index=True,
    )
    streamlit.dataframe(display_frame(heads), width="stretch", hide_index=True)

    evidence = pd.DataFrame(
        [
            {
                "section": "Model contribution",
                "value": str(candidate.get("top_attribution_categories", "")),
            },
            {
                "section": "Supporting evidence",
                "value": str(candidate.get("supporting_evidence", "")),
            },
            {"section": "Historical analog", "value": str(candidate.get("historical_analogs", ""))},
            {
                "section": "Residual/unexplained",
                "value": str(candidate.get("residual_unexplained", "")),
            },
            {
                "section": "OOD warnings",
                "value": str(
                    candidate.get("ood_warning_details", candidate.get("ood_warning", ""))
                ),
            },
            {
                "section": "Selection-policy checks",
                "value": str(candidate.get("selection_policy_result", "")),
            },
            {
                "section": "Gate eligibility",
                "value": str(candidate.get("model_quality_gate_eligible", "")),
            },
            {"section": "Divergences", "value": str(candidate.get("top_divergences", ""))},
        ]
    )
    streamlit.subheader("Evidence")
    streamlit.dataframe(display_frame(evidence), width="stretch", hide_index=True)

    analogs = _json_records(candidate.get("historical_analogs", ""))
    feature_snapshot = pd.DataFrame([candidate.to_dict()])
    streamlit.subheader("Historical Analogs")
    if analogs.empty:
        streamlit.info("No historical analog records are available for this candidate.")
    else:
        streamlit.dataframe(display_frame(analogs), width="stretch", hide_index=True)

    render_table_downloads(evidence, basename="candidate_attribution", label="attribution")
    render_table_downloads(analogs, basename="candidate_analogs", label="analogs")
    render_table_downloads(
        feature_snapshot,
        basename="candidate_feature_snapshot",
        label="feature_snapshot",
    )
    streamlit.download_button(
        "Download attribution workbook XLSX",
        data=to_xlsx_bytes(
            {
                "attribution": evidence,
                "analogs": analogs,
                "feature_snapshot": feature_snapshot,
            }
        ),
        file_name="candidate_attribution_workbook.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    render_page()
