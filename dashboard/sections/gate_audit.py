from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_csv_bytes, to_xlsx_bytes
from swing_rsi.application.dashboard_service import (
    gate_audit_frame,
    gate_contradiction_audit,
    live_signal_blockers_frame,
    signal_discovery_generation_frames,
)


def _options(frame: pd.DataFrame, column: str) -> list[str]:
    if frame.empty or column not in frame.columns:
        return []
    return sorted(frame[column].dropna().astype(str).unique().tolist())


def _filtered(frame: pd.DataFrame) -> pd.DataFrame:
    streamlit = st()
    if frame.empty:
        return frame
    columns = streamlit.columns(4)
    generation = columns[0].selectbox("Generation", ["All", *_options(frame, "generation_id")])
    model = columns[1].selectbox("Model ID", ["All", *_options(frame, "model_id")])
    scope = columns[2].selectbox("Scope", ["All", *_options(frame, "scope")])
    status = columns[3].selectbox("Status", ["All", *_options(frame, "status")])
    columns = streamlit.columns(4)
    direction = columns[0].selectbox("Direction", ["All", *_options(frame, "direction")])
    family = columns[1].selectbox("Family", ["All", *_options(frame, "family")])
    category = columns[2].selectbox("Gate category", ["All", *_options(frame, "gate_category")])
    mandatory_only = columns[3].checkbox("Mandatory only", value=False)
    failed_only = streamlit.checkbox("Failed only", value=False)
    filtered = frame.copy()
    for column, value in (
        ("generation_id", generation),
        ("model_id", model),
        ("scope", scope),
        ("direction", direction),
        ("family", family),
        ("gate_category", category),
        ("status", status),
    ):
        if value != "All":
            filtered = filtered.loc[filtered[column].astype(str) == value]
    if mandatory_only:
        filtered = filtered.loc[filtered["mandatory"].astype(bool)]
    if failed_only:
        filtered = filtered.loc[filtered["status"].astype(str) != "PASS"]
    return filtered


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Gate Audit",
        "Canonical gate evidence, failed mandatory blockers, and contradiction checks.",
    )
    render_page_guidance(
        tells_you=(
            "Why candidates fail model-quality, OOD, final-holdout, concentration, or policy gates."
        ),
        next_action=(
            "Start with the top blocker list before using filters to inspect exact gate evidence."
        ),
    )
    blockers = live_signal_blockers_frame(root)
    streamlit.subheader("Why no live signal?")
    if blockers.empty:
        streamlit.success("No top-level live-signal blocker summary is present.")
    else:
        streamlit.dataframe(display_frame(blockers), width="stretch", hide_index=True)
    frame = gate_audit_frame(root)
    filtered = _filtered(frame)
    audit = gate_contradiction_audit(frame)

    streamlit.subheader("Gate Contradiction Audit")
    failures = int((audit["status"] == "FAIL").sum()) if not audit.empty else 0
    streamlit.metric("Contradiction checks failed", failures)
    streamlit.dataframe(display_frame(audit), width="stretch", hide_index=True)

    streamlit.subheader("Filtered Gates")
    display_columns = [
        "model_id",
        "gate_id",
        "gate_name",
        "gate_category",
        "actual",
        "comparator",
        "threshold",
        "status",
        "mandatory",
        "reason",
        "evidence_source",
        "policy_version_hash",
    ]
    visible = filtered[[column for column in display_columns if column in filtered.columns]]
    streamlit.dataframe(display_frame(visible), width="stretch", hide_index=True)
    render_table_downloads(visible, basename="filtered_gate_audit", label="filtered_gates")

    discovery_gates = signal_discovery_generation_frames(root).get("gate_results", pd.DataFrame())
    if not discovery_gates.empty:
        streamlit.subheader("Signal Discovery Policy Gates")
        discovery_columns = [
            "generation_id",
            "hypothesis_id",
            "target_stop_policy_id",
            "target_stop_policy_name",
            "target_stop_policy_status",
            "target_stop_policy_hash",
            "gate_id",
            "actual",
            "threshold",
            "status",
            "mandatory",
            "evidence_source",
        ]
        discovery_visible = discovery_gates[
            [column for column in discovery_columns if column in discovery_gates.columns]
        ]
        streamlit.dataframe(
            display_frame(discovery_visible),
            width="stretch",
            hide_index=True,
        )
        render_table_downloads(
            discovery_visible,
            basename="signal_discovery_policy_gates",
            label="signal_discovery_policy_gates",
        )

    columns = streamlit.columns(2)
    columns[0].download_button(
        "Download full gate audit CSV",
        data=to_csv_bytes(frame),
        file_name="full_gate_audit.csv",
        mime="text/csv",
        disabled=frame.empty,
    )
    columns[1].download_button(
        "Download full gate audit XLSX",
        data=to_xlsx_bytes({"gates": frame, "contradictions": audit}),
        file_name="full_gate_audit.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=frame.empty,
    )


if __name__ == "__main__":
    render_page()
