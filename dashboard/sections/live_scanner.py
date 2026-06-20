from __future__ import annotations

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.engine_service import latest_scanner_snapshot, run_live_scanner


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header("Live Scanner", "Latest bullish and bearish model candidates.")
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
    for direction in ("Bullish", "Bearish"):
        streamlit.subheader(f"{direction} Rankings")
        subset = rows[rows["direction"] == direction]
        streamlit.dataframe(display_frame(subset), width="stretch", hide_index=True)
