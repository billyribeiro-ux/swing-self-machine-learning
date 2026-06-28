from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.engine_service import (
    latest_scanner_snapshot,
    load_engine_universe,
    load_universe_frames,
)
from swing_rsi.engine.portfolio import PortfolioBacktestConfig, backtest_scanner_candidates


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Portfolio Backtests", "Portfolio-level replay of scanner outputs with next-open entries."
    )
    rows = latest_scanner_snapshot(root)
    if rows.empty:
        streamlit.info("No scanner snapshot is available for portfolio replay.")
        return
    streamlit.warning("Product-class specialist challenger. Development evidence only.")
    if {"product_class_scope", "row_product_class_scope"}.issubset(rows.columns):
        streamlit.subheader("Product-Class Candidate Mix")
        streamlit.dataframe(
            display_frame(
                rows.groupby(
                    ["product_class_scope", "row_product_class_scope", "candidate_status"],
                    dropna=False,
                )
                .size()
                .reset_index(name="rows")
            ),
            width="stretch",
            hide_index=True,
        )
    if streamlit.button("Run portfolio replay on latest snapshot"):
        universe = load_engine_universe(root)
        frames = load_universe_frames(root, universe)
        result = backtest_scanner_candidates(frames, rows, config=PortfolioBacktestConfig())
        streamlit.session_state["portfolio_backtest_result"] = result
    result = streamlit.session_state.get("portfolio_backtest_result")
    if result is None:
        return
    streamlit.subheader("Metrics")
    streamlit.dataframe(
        display_frame(pd.DataFrame([result.metrics])), width="stretch", hide_index=True
    )
    streamlit.subheader("Equity")
    if not result.equity.empty:
        equity = result.equity.copy()
        if "Date" in equity.columns and "equity" in equity.columns:
            streamlit.line_chart(equity.set_index("Date")["equity"])
        if "Date" in equity.columns and "drawdown" in equity.columns:
            streamlit.subheader("Drawdown")
            streamlit.line_chart(equity.set_index("Date")["drawdown"])
    streamlit.subheader("Trade Ledger")
    streamlit.dataframe(display_frame(result.trades), width="stretch", hide_index=True)
    streamlit.subheader("Candidate Audit")
    streamlit.dataframe(display_frame(result.candidate_audit), width="stretch", hide_index=True)
    for title, frame in (
        ("Yearly Results", result.yearly_returns),
        ("Regime Results", result.regime_returns),
        ("Sector Results", result.sector_returns),
        ("Symbol Results", result.symbol_returns),
        ("Model Version Results", result.model_version_returns),
    ):
        streamlit.subheader(title)
        if frame.empty:
            streamlit.info("No rows available for this breakdown.")
        else:
            streamlit.dataframe(display_frame(frame), width="stretch", hide_index=True)


if __name__ == "__main__":
    render_page()
