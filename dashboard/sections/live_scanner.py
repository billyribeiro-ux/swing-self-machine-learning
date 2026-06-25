from __future__ import annotations

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.engine_service import latest_scanner_snapshot, run_live_scanner


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header("Live Scanner", "Latest bullish and bearish model candidates.")
    streamlit.warning("Product-class specialist challenger. Development evidence only.")
    include_challengers = streamlit.checkbox(
        "Use challengers if no champion exists",
        value=False,
        help="Explicit fallback only. The scanner never silently replaces a champion.",
    )
    if streamlit.button("Run scanner"):
        try:
            snapshot = run_live_scanner(root, include_challengers=include_challengers)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            streamlit.error(f"Scanner failed: {exc}")
        else:
            streamlit.success(f"Scanner snapshot saved: {snapshot.scan_id}")

    rows = latest_scanner_snapshot(root)
    if rows.empty:
        streamlit.info("No scanner snapshot is available yet.")
        return
    scope_columns = [
        column
        for column in (
            "product_class_scope",
            "row_product_class_scope",
            "scanner_routing_result",
            "product_class_scope_match",
        )
        if column in rows.columns
    ]
    if scope_columns:
        streamlit.subheader("Product-Class Routing")
        streamlit.dataframe(
            display_frame(rows[[*scope_columns, "ticker", "model_id", "candidate_status"]]),
            width="stretch",
            hide_index=True,
        )
    for direction in ("Bullish", "Bearish"):
        streamlit.subheader(f"{direction} Rankings")
        subset = rows[rows["direction"] == direction]
        streamlit.dataframe(display_frame(subset), width="stretch", hide_index=True)


if __name__ == "__main__":
    render_page()
