from __future__ import annotations

from dashboard.ui.components import render_page_guidance, render_page_header, repository_root, st
from dashboard.ui.downloads import render_table_downloads
from dashboard.ui.formatting import display_frame
from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.application.dashboard_service import (
    product_class_comparison_frame,
    product_class_conclusion,
    product_class_research_frame,
)

PRODUCT_CLASS_SCOPES: tuple[str, ...] = (
    "POOLED",
    "ORDINARY",
    "INVERSE",
    "LEVERAGED_LONG",
    "LEVERAGED_INVERSE",
)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Product-Class Research",
        "Specialist scope evidence, pooled comparisons, blockers, and current challengers.",
    )
    render_page_guidance(
        tells_you=(
            "Which product-class specialists look promising in development evidence and what still "
            "blocks them."
        ),
        next_action=(
            "Read the conclusion panel first, then compare specialist scopes against pooled models "
            "before drilling into gates."
        ),
    )
    streamlit.warning("Development evidence only. Not final validation.")
    streamlit.info(product_class_conclusion(root))

    research = product_class_research_frame(root)
    comparison = product_class_comparison_frame(root)

    for scope in PRODUCT_CLASS_SCOPES:
        streamlit.subheader(scope)
        if not research.empty and "scope" in research.columns:
            scoped = research.loc[research["scope"].astype(str) == scope]
        else:
            scoped = research
        if scoped.empty:
            streamlit.caption("No local development evidence for this scope.")
        else:
            streamlit.dataframe(display_frame(scoped), width="stretch", hide_index=True)

    streamlit.subheader("Comparison Versus Pooled")
    streamlit.dataframe(display_frame(comparison), width="stretch", hide_index=True)
    render_table_downloads(comparison, basename="product_class_comparison", label="comparison")

    streamlit.subheader("Product-Class Research Table")
    streamlit.dataframe(display_frame(research), width="stretch", hide_index=True)
    render_table_downloads(research, basename="product_class_research", label="product_class")

    streamlit.download_button(
        "Download product-class workbook XLSX",
        data=to_xlsx_bytes(
            {
                "product_class_research": research,
                "comparison": comparison,
            }
        ),
        file_name="product_class_research.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=research.empty and comparison.empty,
    )


if __name__ == "__main__":
    render_page()
