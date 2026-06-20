from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.datasets import discover_raw_datasets
from swing_rsi.application.engine_service import load_engine_universe, update_universe_data
from swing_rsi.engine.universe import universe_to_frame_rows


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Data and Universe", "Configured symbols, local data health, and safe updates."
    )
    universe = load_engine_universe(root)
    streamlit.caption(f"Universe snapshot: `{universe.snapshot_id}`")

    streamlit.subheader("Configured Universe")
    streamlit.dataframe(
        display_frame(pd.DataFrame(universe_to_frame_rows(universe))),
        width="stretch",
        hide_index=True,
    )

    streamlit.subheader("Local Raw Data")
    datasets = discover_raw_datasets(root)
    if datasets:
        streamlit.dataframe(
            display_frame(pd.DataFrame([dataset.__dict__ for dataset in datasets])),
            width="stretch",
            hide_index=True,
        )
    else:
        streamlit.info("No local raw data files are available.")

    with streamlit.form("universe_update_form"):
        streamlit.write("Update enabled symbols through the configured FMP provider.")
        start = streamlit.text_input("Start date", value=universe.default_start)
        submitted = streamlit.form_submit_button("Update universe data")
    if submitted:
        try:
            result = update_universe_data(root, start=start)
        except (RuntimeError, ValueError) as exc:
            streamlit.error(f"Universe update failed: {exc}")
        else:
            rows = pd.DataFrame([row.__dict__ for row in result.results])
            streamlit.success("Universe update completed. Symbols with errors were recorded.")
            streamlit.dataframe(display_frame(rows), width="stretch", hide_index=True)
