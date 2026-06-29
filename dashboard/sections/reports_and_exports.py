from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import save_xlsx_report
from swing_rsi.application.dashboard_service import (
    candidate_detail_url,
    final_holdout_runs_frame,
    gate_audit_frame,
    model_registry_frame,
    product_class_comparison_frame,
    registered_models_readonly,
    reports_inventory_frame,
    save_complete_engine_snapshot,
    scanner_rows_frame,
    scanner_snapshot_list_frame,
    signal_discovery_blocker_frames,
    signal_discovery_generation_frames,
)

BLOCKER_TOP_ROW_COLUMNS: tuple[str, ...] = (
    "as_of_date",
    "ticker",
    "product_class_scope",
    "action",
    "candidate_status",
    "blocker_reason",
    "model_id",
    "hypothesis_id",
    "archetype",
    "signal_score",
    "direction_probability",
    "target_before_stop_probability",
    "expected_return",
    "expected_mfe",
    "expected_mae",
    "ood_feature_rate",
    "next_required_event",
    "open_url",
)


def _feature_families_from_models() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in registered_models_readonly(repository_root()):
        for key, value in model.metrics.items():
            if "feature" in key and ("count" in key or "famil" in key):
                rows.append({"model_id": model.model_id, "metric": key, "value": value})
    return pd.DataFrame(rows)


def _display_count(value: object) -> str:
    try:
        if pd.isna(value):
            return "Not available"
    except (TypeError, ValueError):
        pass
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "Not available"


def _display_text(value: object) -> str:
    try:
        if pd.isna(value):
            return "Not available"
    except (TypeError, ValueError):
        pass
    text = str(value or "").strip()
    return text if text else "Not available"


def _summary_row(frame: pd.DataFrame) -> dict[str, object]:
    if frame.empty:
        return {}
    return frame.iloc[0].to_dict()


def _top_blocker_rows(blockers: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    if blockers.empty:
        return blockers.copy()
    frame = blockers.copy()
    frame["open_url"] = [
        candidate_detail_url(
            scan_id=row.get("generation_id", ""),
            ticker=row.get("ticker", ""),
            model_id=row.get("model_id", ""),
            direction=row.get("direction", ""),
            status=row.get("candidate_status", ""),
        )
        for _, row in frame.iterrows()
    ]
    if "signal_score" in frame.columns:
        frame = frame.sort_values("signal_score", ascending=False, na_position="last")
    columns = [column for column in BLOCKER_TOP_ROW_COLUMNS if column in frame.columns]
    return frame[columns].head(limit).reset_index(drop=True)


def _display_top_blocker_rows(blockers: pd.DataFrame) -> pd.DataFrame:
    display = display_frame(_top_blocker_rows(blockers)).rename(columns={"Open Url": "Open"})
    return display


def _render_signal_discovery_blockers(root: Path) -> None:
    streamlit = st()
    blocker_frames = signal_discovery_blocker_frames(root)
    blocker_sheets = {name: frame for name, frame in blocker_frames.items() if not frame.empty}
    blockers = blocker_sheets.get("blocker_rows", pd.DataFrame())

    streamlit.subheader("Signal Discovery Blockers")
    if not blocker_sheets or blockers.empty:
        streamlit.info("No NO_SIGNAL or rejected signal discovery blockers are available locally.")
        return

    summary = _summary_row(blocker_sheets.get("summary", pd.DataFrame()))
    streamlit.caption(
        "Read-only blocker review for the latest signal discovery generation. This panel reads "
        "local generation artifacts only and does not run discovery, scanner, or FMP updates."
    )
    streamlit.metric("Blocker rows", _display_count(summary.get("blocker_rows")))
    metrics = streamlit.columns(7)
    cards = {
        "NO_SIGNAL rows": _display_count(summary.get("no_signal_rows")),
        "Rejected rows": _display_count(summary.get("rejected_rows")),
        "Distinct tickers": _display_count(summary.get("distinct_tickers")),
        "Distinct hypotheses": _display_count(summary.get("distinct_hypotheses")),
        "Top blocker reason": _display_text(summary.get("top_blocker_reason")),
        "Latest decision date": _display_text(summary.get("latest_decision_date")),
        "Generation ID": _display_text(summary.get("generation_id")),
    }
    for index, (label, value) in enumerate(cards.items()):
        metrics[index].metric(label, value)

    tabs = streamlit.tabs(
        [
            "By reason",
            "By hypothesis",
            "By archetype",
            "By ticker",
            "By scope",
            "Top blocked rows",
        ]
    )
    grouped_frames = [
        ("by_reason", tabs[0]),
        ("by_hypothesis", tabs[1]),
        ("by_archetype", tabs[2]),
        ("by_ticker", tabs[3]),
        ("by_scope", tabs[4]),
    ]
    for name, tab in grouped_frames:
        with tab:
            frame = blocker_sheets.get(name, pd.DataFrame())
            if frame.empty:
                streamlit.info("Not available")
            else:
                streamlit.dataframe(display_frame(frame.head(50)), width="stretch", hide_index=True)
    with tabs[5]:
        top_blockers = _display_top_blocker_rows(blockers)
        column_config = {}
        if "Open" in top_blockers.columns:
            column_config["Open"] = streamlit.column_config.LinkColumn(
                "Open",
                display_text="Open detail",
            )
        streamlit.dataframe(
            top_blockers,
            width="stretch",
            hide_index=True,
            column_config=column_config,
        )

    if streamlit.button("Create signal discovery blocker workbook"):
        output = save_xlsx_report(
            root,
            "signal_discovery_blockers.xlsx",
            blocker_sheets,
        )
        streamlit.success(f"Saved {output.relative_to(root)}")


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

    discovery_frames = signal_discovery_generation_frames(root, include_blocked_analogs=True)
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
            "blocked_row_analogs",
            "blocked_row_analog_summary",
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

    _render_signal_discovery_blockers(root)

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
