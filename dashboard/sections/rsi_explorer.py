from __future__ import annotations

from datetime import date

from dashboard.ui.cache import load_dataset_cached
from dashboard.ui.charts import render_price_and_rsi
from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.errors import show_expected_error, show_unexpected_error
from dashboard.ui.formatting import display_frame, whole
from swing_rsi.application.datasets import (
    DatasetSummary,
    discover_raw_datasets,
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


def _ticker_map(datasets: tuple[DatasetSummary, ...]) -> dict[str, DatasetSummary]:
    return {dataset.ticker: dataset for dataset in datasets}


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header("RSI Explorer", "Inspect close-known RSI swing-reversal candidates.")
    streamlit.caption(
        "Display defaults are neutral visualization values, not optimized parameters."
    )

    datasets = discover_raw_datasets(root)
    if not datasets:
        streamlit.info("No raw CSV files are available under data/raw/.")
        return

    by_ticker = _ticker_map(datasets)
    selected_ticker = streamlit.selectbox(
        "Ticker",
        options=tuple(by_ticker.keys()),
        key="rsi_ticker",
    )
    selected = by_ticker[str(selected_ticker)]

    start = streamlit.date_input("Window start", value=_years_ago(5), key="rsi_window_start")
    end = streamlit.date_input("Window end", value=date.today(), key="rsi_window_end")
    length = streamlit.slider("RSI length", min_value=2, max_value=50, value=10, key="rsi_length")
    lower_level = streamlit.slider(
        "Lower reference level",
        min_value=5,
        max_value=60,
        value=35,
        key="rsi_lower_level",
    )
    trigger_mode = streamlit.selectbox(
        "Trigger mode",
        ("cross_above", "turn_up_below", "recent_reclaim"),
        key="rsi_trigger_mode",
    )
    slope_window = streamlit.selectbox(
        "Slope window",
        (1, 2, 3, 5, 10),
        index=0,
        key="rsi_slope_window",
    )
    trend_filter = streamlit.selectbox(
        "Trend filter",
        ("none", "above_sma_50", "above_sma_200", "sma_50_above_200"),
        key="rsi_trend_filter",
    )
    compare_control = streamlit.checkbox(
        "Compare with retail control RSI(14)/30",
        value=False,
        key="rsi_compare_control",
    )

    if start > end:
        streamlit.error("Window start must be on or before window end.")
        return

    try:
        frame = load_dataset_cached(selected.path)
        window = slice_date_window(frame, start=start, end=end)
        if window.empty:
            streamlit.warning("The selected window contains no available rows.")
            return
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
        show_expected_error(f"RSI Explorer cannot load this configuration: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive dashboard guard
        show_unexpected_error(exc, context="rsi_explorer")
        return

    streamlit.subheader("Bullish RSI swing-reversal candidate")
    streamlit.caption(
        f"Selected display rule: `{rule.rule_id}`. Close-known candidates are not same-close "
        "entries."
    )
    render_price_and_rsi(explorer.features["Close"], explorer.rsi, float(lower_level))
    streamlit.write(
        f"Candidate dates emitted by selected rule: {whole(len(explorer.signal_table))}"
    )
    streamlit.dataframe(display_frame(explorer.signal_table), width="stretch", hide_index=True)

    if compare_control:
        streamlit.subheader("Retail Control RSI(14)/30")
        streamlit.caption("Control comparison only; not a primary dashboard default.")
        control = retail_control_rule()
        control_explorer = build_rsi_explorer_data(window, control)
        render_price_and_rsi(control_explorer.features["Close"], control_explorer.rsi, 30.0)
        streamlit.dataframe(
            display_frame(control_explorer.signal_table),
            width="stretch",
            hide_index=True,
        )


if __name__ == "__main__":
    render_page()
