from __future__ import annotations

from datetime import date

from dashboard.ui.charts import render_price_and_rsi
from dashboard.ui.components import render_page_header, repository_root, st
from swing_rsi.application.datasets import (
    discover_raw_datasets,
    load_raw_dataset,
    slice_date_window,
)
from swing_rsi.application.research_service import build_rsi_explorer_data, retail_control_rule
from swing_rsi.signals.rsi_reversal import RSIReversalRule


def _years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header("RSI Explorer", "Inspect close-known RSI swing-reversal candidates.")
    streamlit.caption("Display defaults are neutral visualization values, not optimized settings.")

    datasets = discover_raw_datasets(root)
    if not datasets:
        streamlit.info("No raw CSV files are available under data/raw/.")
        return

    labels = {f"{dataset.ticker} - {dataset.path.name}": dataset for dataset in datasets}
    selected_label = streamlit.selectbox("Ticker", options=tuple(labels.keys()))
    selected = labels[str(selected_label)]

    start = streamlit.date_input("Window start", value=_years_ago(5))
    end = streamlit.date_input("Window end", value=date.today())
    length = streamlit.slider("RSI length", min_value=2, max_value=50, value=10)
    lower_level = streamlit.slider("Lower reference level", min_value=5, max_value=60, value=35)
    trigger_mode = streamlit.selectbox(
        "Trigger mode", ("cross_above", "turn_up_below", "recent_reclaim")
    )
    slope_window = streamlit.selectbox("Slope window", (1, 2, 3, 5, 10), index=0)
    trend_filter = streamlit.selectbox(
        "Trend filter", ("none", "above_sma_50", "above_sma_200", "sma_50_above_200")
    )
    compare_control = streamlit.checkbox("Compare with retail control RSI(14)/30", value=False)

    try:
        frame = load_raw_dataset(selected.path)
        window = slice_date_window(frame, start=start, end=end)
        if len(window) < 260:
            streamlit.warning("The selected window is small for long moving-average features.")
        rule = RSIReversalRule(
            length=int(length),
            lower_level=float(lower_level),
            slope_window=int(slope_window),
            trigger_mode=str(trigger_mode),  # type: ignore[arg-type]
            trend_filter=str(trend_filter),  # type: ignore[arg-type]
        )
        explorer = build_rsi_explorer_data(window, rule)
    except (FileNotFoundError, ValueError) as exc:
        streamlit.error(str(exc))
        return

    streamlit.subheader("Bullish RSI swing-reversal candidate")
    render_price_and_rsi(explorer.features["Close"], explorer.rsi, float(lower_level))
    streamlit.write(f"Signal dates emitted by rule `{rule.rule_id}`")
    streamlit.dataframe(explorer.signal_table, width="stretch")

    if compare_control:
        streamlit.subheader("Retail Control RSI(14)/30")
        control = retail_control_rule()
        control_explorer = build_rsi_explorer_data(window, control)
        render_price_and_rsi(control_explorer.features["Close"], control_explorer.rsi, 30.0)
        streamlit.dataframe(control_explorer.signal_table, width="stretch")


if __name__ == "__main__":
    render_page()
