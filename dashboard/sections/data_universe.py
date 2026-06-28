from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    fmp_key_configured,
    load_dashboard_universe,
    universe_health_frame,
)
from swing_rsi.application.engine_service import update_universe_data


def _apply_filters(frame: pd.DataFrame) -> pd.DataFrame:
    streamlit = st()
    if frame.empty:
        return frame
    columns = streamlit.columns(5)
    enabled_only = columns[0].checkbox("Enabled only", value=True)
    product_class = columns[1].multiselect(
        "Product class",
        sorted(frame["product_class"].dropna().astype(str).unique().tolist()),
    )
    role = columns[2].multiselect("Role", sorted(frame["role"].dropna().astype(str).unique()))
    sector = columns[3].multiselect("Sector", sorted(frame["sector"].dropna().astype(str).unique()))
    stale_only = columns[4].checkbox("Stale only", value=False)
    filtered = frame.copy()
    if enabled_only:
        filtered = filtered.loc[filtered["enabled"].astype(bool)]
    if product_class:
        filtered = filtered.loc[filtered["product_class"].astype(str).isin(product_class)]
    if role:
        filtered = filtered.loc[filtered["role"].astype(str).isin(role)]
    if sector:
        filtered = filtered.loc[filtered["sector"].astype(str).isin(sector)]
    if stale_only:
        filtered = filtered.loc[
            ~filtered["stale_status"].astype(str).str.contains("fresh", case=False, na=False)
        ]
    return filtered


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Data and Universe",
        "Configured symbols, local OHLCV coverage, manifest health, and explicit data updates.",
    )
    render_page_guidance(
        tells_you=(
            "Whether the local universe is enabled, fresh, manifest-backed, and ready for research "
            "review."
        ),
        next_action=(
            "Use read-only refresh for local status. Only run FMP update after confirmation when "
            "development raw data should be mutated."
        ),
    )
    universe = load_dashboard_universe(root)
    streamlit.caption(f"Universe snapshot: `{universe.snapshot_id}`")
    streamlit.write(f"FMP key configured: {'yes' if fmp_key_configured(root) else 'no'}")

    if streamlit.button("Read-only refresh local status"):
        streamlit.rerun()

    health = universe_health_frame(root)
    filtered = _apply_filters(health)
    streamlit.dataframe(display_frame(filtered), width="stretch", hide_index=True)
    render_table_downloads(filtered, basename="data_universe", label="universe")

    streamlit.subheader("Optional FMP Universe Update")
    streamlit.warning("This mutates development raw data and manifests only.")
    configured = fmp_key_configured(root)
    confirmed = streamlit.checkbox("I understand this updates development raw data only.")
    disabled = not configured or not confirmed
    if not configured:
        streamlit.info("FMP key configured: no")
    if streamlit.button("Update enabled universe from FMP", disabled=disabled):
        try:
            result = update_universe_data(root, start=universe.default_start)
        except (RuntimeError, ValueError) as exc:
            streamlit.error(f"Universe update failed: {exc}")
        else:
            rows = pd.DataFrame([row.__dict__ for row in result.results])
            attempted = len(rows)
            updated = int((rows["status"] == "updated").sum()) if not rows.empty else 0
            errors = int((rows["status"] == "error").sum()) if not rows.empty else 0
            latest = rows["last_date"].dropna().min() if "last_date" in rows else ""
            streamlit.success(
                f"Attempted {attempted:,}; updated {updated:,}; errors {errors:,}; "
                f"latest common session {latest or 'n/a'}."
            )
            streamlit.dataframe(display_frame(rows), width="stretch", hide_index=True)
            render_table_downloads(rows, basename="data_universe_update", label="update")


if __name__ == "__main__":
    render_page()
