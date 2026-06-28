from __future__ import annotations

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_service import (
    product_class_comparison_frame,
    product_class_summary_frame,
)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Product-Class Specialists",
        "Pooled, ordinary, inverse, leveraged-long, and leveraged-inverse model evidence.",
    )
    streamlit.warning("Development evidence only. Not final validation.")

    summary = product_class_summary_frame(root)
    streamlit.subheader("Product-Class Scope Summary")
    streamlit.dataframe(display_frame(summary), width="stretch", hide_index=True)
    render_table_downloads(summary, basename="product_class_scope_summary", label="scopes")

    comparison = product_class_comparison_frame(root)
    streamlit.subheader("Pooled Versus Specialist Comparison")
    streamlit.dataframe(display_frame(comparison), width="stretch", hide_index=True)
    render_table_downloads(
        comparison,
        basename="product_class_specialist_comparison",
        label="comparison",
    )


if __name__ == "__main__":
    render_page()
