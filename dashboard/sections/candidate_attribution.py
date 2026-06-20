from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.engine_service import latest_scanner_snapshot


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
    streamlit.subheader("Model Contribution Share")
    streamlit.write(row.get("top_attribution_categories", "n/a"))
    streamlit.subheader("Supporting Evidence")
    streamlit.write(row.get("supporting_evidence", "n/a"))
    streamlit.subheader("Relationships")
    streamlit.write(row.get("top_confirming_relationships", "n/a"))
    streamlit.subheader("Divergences")
    streamlit.write(row.get("top_divergences", "n/a"))
    streamlit.subheader("Raw Candidate Row")
    streamlit.dataframe(
        display_frame(pd.DataFrame([row.to_dict()])), width="stretch", hide_index=True
    )
