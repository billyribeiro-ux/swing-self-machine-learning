from __future__ import annotations

import json

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.engine_service import (
    latest_scanner_snapshot,
    load_engine_universe,
    load_universe_frames,
)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Candidate Attribution", "Evidence groups, relationships, divergences, and analog context."
    )
    rows = latest_scanner_snapshot(root)
    if rows.empty:
        streamlit.info("No scanner candidates are available yet.")
        return
    options = [
        f"{row.ticker} {row.direction} h{row.horizon} {row.model_id}"
        for row in rows.itertuples(index=False)
    ]
    selected = streamlit.selectbox("Candidate", options=options)
    row = rows.iloc[options.index(str(selected))]
    columns = streamlit.columns(3)
    columns[0].metric("Probability", f"{float(row['calibrated_probability']):.2%}")
    columns[1].metric("Expected return", f"{float(row['expected_return']):.2%}")
    columns[2].metric("Utility", f"{float(row['composite_utility_score']):.4f}")
    streamlit.subheader("Recent Price Context")
    try:
        universe = load_engine_universe(root)
        frame = load_universe_frames(root, universe).get(str(row["ticker"]))
    except (FileNotFoundError, RuntimeError, ValueError):
        frame = None
    if frame is None or frame.empty:
        streamlit.info("No local OHLCV frame is available for this ticker.")
    else:
        price = frame.loc[frame.index <= pd.Timestamp(str(row["as_of_date"]))].tail(252)
        streamlit.line_chart(price[["Close"]])
    streamlit.subheader("Model Contribution Share")
    streamlit.write(row.get("top_attribution_categories", "n/a"))
    streamlit.subheader("Supporting Evidence")
    streamlit.write(row.get("supporting_evidence", "n/a"))
    streamlit.subheader("Relationships")
    streamlit.write(row.get("top_confirming_relationships", "n/a"))
    streamlit.subheader("Divergences")
    streamlit.write(row.get("top_divergences", "n/a"))
    streamlit.subheader("Prediction OOD Governance")
    ood_fields = [
        "ood_warning",
        "ood_affected_heads",
        "ood_max_severity",
        "ood_warning_details",
        "expected_return_ood_severity",
        "expected_return_ood_bound_low",
        "expected_return_ood_bound_high",
        "expected_return_ood_severity_limit",
        "expected_mfe_ood_severity",
        "expected_mfe_ood_bound_low",
        "expected_mfe_ood_bound_high",
        "expected_mfe_ood_severity_limit",
        "expected_mae_ood_severity",
        "expected_mae_ood_bound_low",
        "expected_mae_ood_bound_high",
        "expected_mae_ood_severity_limit",
    ]
    streamlit.dataframe(
        display_frame(
            pd.DataFrame([{"Metric": field, "Value": row.get(field, "")} for field in ood_fields])
        ),
        width="stretch",
        hide_index=True,
    )
    streamlit.subheader("Target-Before-Stop Calibration")
    calibration_fields = [
        "target_before_stop_raw_probability",
        "target_before_stop_probability",
        "target_before_stop_calibration_governance_schema",
        "target_before_stop_calibration_method",
        "target_before_stop_calibration_manifest_hash",
        "target_before_stop_calibrator_artifact_hash",
        "target_before_stop_calibration_metadata_missing",
        "target_before_stop_feature_screen_schema",
        "target_before_stop_feature_manifest_hash",
    ]
    streamlit.dataframe(
        display_frame(
            pd.DataFrame(
                [{"Metric": field, "Value": row.get(field, "")} for field in calibration_fields]
            )
        ),
        width="stretch",
        hide_index=True,
    )
    streamlit.subheader("Historical Analogs")
    try:
        analogs = pd.DataFrame(json.loads(str(row.get("historical_analogs", "[]"))))
    except json.JSONDecodeError:
        analogs = pd.DataFrame()
    if analogs.empty:
        streamlit.info("No compact analog records are available for this candidate.")
    else:
        streamlit.dataframe(display_frame(analogs), width="stretch", hide_index=True)
    streamlit.subheader("Model And Snapshot Details")
    streamlit.dataframe(
        display_frame(
            pd.DataFrame(
                [
                    {
                        "model_id": row.get("model_id"),
                        "model_state": row.get("model_state"),
                        "feature_snapshot_hash": row.get("feature_snapshot_hash"),
                        "candidate_status": row.get("candidate_status"),
                        "exclusion_reason": row.get("exclusion_reason"),
                        "target_before_stop_raw_probability": row.get(
                            "target_before_stop_raw_probability"
                        ),
                        "target_before_stop_probability": row.get("target_before_stop_probability"),
                        "target_before_stop_calibration_method": row.get(
                            "target_before_stop_calibration_method"
                        ),
                        "expected_mfe": row.get("expected_mfe"),
                        "expected_mae": row.get("expected_mae"),
                    }
                ]
            )
        ),
        width="stretch",
        hide_index=True,
    )
    streamlit.subheader("Raw Candidate Row")
    streamlit.dataframe(
        display_frame(pd.DataFrame([row.to_dict()])), width="stretch", hide_index=True
    )


if __name__ == "__main__":
    render_page()
