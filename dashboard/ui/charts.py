from __future__ import annotations

import pandas as pd

from dashboard.ui.components import st
from swing_rsi.application.research_service import build_trade_curve


def render_price_and_rsi(close: pd.Series, rsi: pd.Series, lower_level: float) -> None:
    streamlit = st()
    price_tab, rsi_tab = streamlit.tabs(["Daily Close", "RSI"])
    with price_tab:
        streamlit.line_chart(close.rename("Close"))
    with rsi_tab:
        chart_frame = pd.DataFrame({"RSI": rsi, "Selected lower reference": lower_level})
        streamlit.line_chart(chart_frame)


def render_trade_curves(trades: pd.DataFrame) -> None:
    streamlit = st()
    curve = build_trade_curve(trades)
    if curve.empty:
        streamlit.info("No completed trades to chart for this candidate.")
        return
    streamlit.line_chart(curve.set_index("trade_number")[["equity"]])
    streamlit.line_chart(curve.set_index("trade_number")[["drawdown"]])
