from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import save_xlsx_report
from swing_rsi.application.dashboard_service import (
    final_holdout_runs_frame,
    gate_audit_frame,
    model_registry_frame,
    product_class_comparison_frame,
    registered_models_readonly,
    reports_inventory_frame,
    save_complete_engine_snapshot,
    scanner_rows_frame,
    scanner_snapshot_list_frame,
    signal_discovery_generation_frames,
)


def _feature_families_from_models() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in registered_models_readonly(repository_root()):
        for key, value in model.metrics.items():
            if "feature" in key and ("count" in key or "famil" in key):
                rows.append({"model_id": model.model_id, "metric": key, "value": value})
    return pd.DataFrame(rows)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Reports and Exports",
        "Local generated reports, audit files, scanner exports, and dashboard Excel workbooks.",
    )
    render_page_guidance(
        tells_you=(
            "Which local reports are available and which CSV/XLSX workbooks can be generated for "
            "offline review."
        ),
        next_action=(
            "Download existing artifacts or explicitly create a workbook. Workbook creation writes "
            "only under reports/dashboard_exports/."
        ),
    )
    inventory = reports_inventory_frame(root)
    streamlit.subheader("Available Reports")
    streamlit.dataframe(display_frame(inventory), width="stretch", hide_index=True)
    render_table_downloads(inventory, basename="reports_inventory", label="reports")

    if not inventory.empty:
        selected = streamlit.selectbox(
            "Download report file", inventory["path"].astype(str).tolist()
        )
        path = root / selected
        if path.exists() and path.is_file():
            streamlit.download_button(
                "Download selected report",
                data=path.read_bytes(),
                file_name=path.name,
            )

    streamlit.subheader("Create Excel Workbook")
    if streamlit.button("Export Complete Engine Snapshot"):
        output = save_complete_engine_snapshot(root)
        streamlit.success(f"Saved {output.relative_to(root)}")
    if streamlit.button("Create latest generation summary workbook"):
        output = save_xlsx_report(
            root,
            "latest_generation_summary.xlsx",
            {
                "models": model_registry_frame(root),
                "gates": gate_audit_frame(root),
                "scanner": scanner_rows_frame(root),
                "final_holdout": final_holdout_runs_frame(root),
                "product_class": product_class_comparison_frame(root),
                "feature_families": _feature_families_from_models(),
            },
        )
        streamlit.success(f"Saved {output.relative_to(root)}")

    discovery_frames = signal_discovery_generation_frames(root)
    discovery_sheets = {
        name: frame
        for name, frame in discovery_frames.items()
        if name
        in {
            "summary",
            "metadata",
            "hypotheses",
            "candidates",
            "selected_candidates",
            "no_signal",
            "rejected",
            "footprint_evidence",
            "historical_analogs",
            "score_components",
            "gate_results",
        }
        and not frame.empty
    }
    streamlit.subheader("Signal Discovery Generation")
    if discovery_sheets:
        streamlit.dataframe(
            display_frame(discovery_sheets.get("summary", pd.DataFrame())),
            width="stretch",
            hide_index=True,
        )
        if streamlit.button("Create signal discovery generation workbook"):
            output = save_xlsx_report(
                root,
                "signal_discovery_generation.xlsx",
                discovery_sheets,
            )
            streamlit.success(f"Saved {output.relative_to(root)}")
    else:
        streamlit.info("No signal discovery generation is available locally.")

    models = registered_models_readonly(root)
    if models:
        selected_model = streamlit.selectbox(
            "Selected model audit workbook",
            models,
            format_func=lambda model: model.model_id,
        )
        if streamlit.button("Create selected model audit workbook"):
            model_rows = model_registry_frame(root)
            gates = gate_audit_frame(root)
            output = save_xlsx_report(
                root,
                f"{selected_model.model_id}_audit.xlsx",
                {
                    "summary": model_rows.loc[
                        model_rows["model_id"].astype(str) == selected_model.model_id
                    ],
                    "gates": gates.loc[gates["model_id"].astype(str) == selected_model.model_id],
                    "calibration": pd.DataFrame(
                        [
                            {"metric": key, "value": value}
                            for key, value in selected_model.calibration_metrics.items()
                        ]
                    ),
                    "OOD": pd.DataFrame(
                        [
                            {"metric": key, "value": value}
                            for key, value in selected_model.metrics.items()
                            if "ood" in key.lower()
                        ]
                    ),
                    "features": pd.DataFrame(
                        [
                            {"metric": key, "value": value}
                            for key, value in selected_model.metrics.items()
                            if "feature" in key.lower()
                        ]
                    ),
                    "portfolio": pd.DataFrame(
                        [
                            {"metric": key, "value": value}
                            for key, value in selected_model.metrics.items()
                            if "portfolio" in key.lower()
                        ]
                    ),
                    "scanner_rows": scanner_rows_frame(root).loc[
                        lambda frame: (
                            frame.get("model_id", pd.Series(dtype=str)).astype(str)
                            == selected_model.model_id
                        )
                    ],
                },
            )
            streamlit.success(f"Saved {output.relative_to(root)}")

    snapshots = scanner_snapshot_list_frame(root)
    if not snapshots.empty:
        selected_scan = streamlit.selectbox(
            "Selected scanner snapshot workbook",
            snapshots["scan_id"].astype(str).tolist(),
        )
        if streamlit.button("Create selected scanner snapshot workbook"):
            candidates = scanner_rows_frame(root, selected_scan)
            output = save_xlsx_report(
                root,
                f"{selected_scan}_scanner.xlsx",
                {
                    "candidates": candidates,
                    "rejection_summary": candidates.get("exclusion_reason", pd.Series(dtype=str))
                    .value_counts()
                    .reset_index(),
                    "attribution": candidates[
                        [
                            column
                            for column in (
                                "ticker",
                                "model_id",
                                "top_attribution_categories",
                                "supporting_evidence",
                            )
                            if column in candidates.columns
                        ]
                    ],
                    "analogs": candidates[
                        [
                            column
                            for column in ("ticker", "model_id", "historical_analogs")
                            if column in candidates.columns
                        ]
                    ],
                },
            )
            streamlit.success(f"Saved {output.relative_to(root)}")


if __name__ == "__main__":
    render_page()
