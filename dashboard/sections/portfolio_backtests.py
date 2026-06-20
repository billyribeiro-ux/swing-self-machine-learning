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
        streamlit.line_chart(result.equity.set_index("trade_number")["equity"])
    streamlit.subheader("Trade Ledger")
    streamlit.dataframe(display_frame(result.trades), width="stretch", hide_index=True)
