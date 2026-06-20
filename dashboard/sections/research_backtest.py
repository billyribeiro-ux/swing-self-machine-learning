from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.ui.cache import load_dataset_cached
from dashboard.ui.charts import render_trade_curves
from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.errors import show_expected_error, show_unexpected_error
from dashboard.ui.formatting import display_frame, percent, whole
from swing_rsi.application.datasets import DatasetSummary, discover_raw_datasets, slice_date_window
from swing_rsi.application.research_service import (
    ResearchRun,
    build_rule_trade_ledger,
    candidate_rule_count,
    grid_for_preset,
    returns_by_calendar_year,
    rule_from_result_row,
    run_research,
)


def _years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


def _preset_value(label: str) -> str:
    return "quick" if label.startswith("Quick") else "standard"


def _ticker_map(datasets: tuple[DatasetSummary, ...]) -> dict[str, DatasetSummary]:
    return {dataset.ticker: dataset for dataset in datasets}


def _config(
    *,
    ticker: str,
    path: Path,
    start: date,
    end: date,
    holding_period: int,
    cost_bps: float,
    minimum_trades: int,
    preset: str,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "path": str(path),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "holding_period": holding_period,
        "cost_bps": cost_bps,
        "minimum_trades": minimum_trades,
        "preset": preset,
    }


def _compare_rows(run: ResearchRun) -> pd.DataFrame:
    highest = run.results.iloc[0]
    control = run.control.metrics
    return pd.DataFrame(
        [
            {
                "label": "Highest-ranked in-sample candidate",
                "rule_id": highest["rule_id"],
                "trade_count": highest["trade_count"],
                "win_rate": highest["win_rate"],
                "mean_return": highest["mean_return"],
                "median_return": highest["median_return"],
                "mean_return_lcb_90": highest["mean_return_lcb_90"],
                "profit_factor": highest["profit_factor"],
                "max_drawdown": highest["max_drawdown"],
                "mean_mfe": highest["mean_mfe"],
                "mean_mae": highest["mean_mae"],
                "positive_year_fraction": highest["positive_year_fraction"],
                "score": highest["score"],
            },
            {
                "label": "RSI(14)/30 control",
                "rule_id": run.control.rule.rule_id,
                "trade_count": control["trade_count"],
                "win_rate": control["win_rate"],
                "mean_return": control["mean_return"],
                "median_return": control["median_return"],
                "mean_return_lcb_90": control["mean_return_lcb_90"],
                "profit_factor": control["profit_factor"],
                "max_drawdown": control["max_drawdown"],
                "mean_mfe": control["mean_mfe"],
                "mean_mae": control["mean_mae"],
                "positive_year_fraction": control["positive_year_fraction"],
                "score": control["score"],
            },
        ]
    )


def _render_run_summary(run: ResearchRun, config: dict[str, Any]) -> None:
    streamlit = st()
    columns = streamlit.columns(4)
    columns[0].metric("Ticker", run.ticker)
    columns[1].metric("Research window", f"{run.window_start} to {run.window_end}")
    columns[2].metric("Holding period", whole(config["holding_period"]))
    columns[3].metric("Cost", f"{config['cost_bps']:.1f} bps")
    columns = streamlit.columns(4)
    columns[0].metric("Rules tested", whole(run.candidate_count))
    columns[1].metric("Eligible rules", whole(run.eligible_candidate_count))
    columns[2].metric("Run ID", run.report_path.stem)
    columns[3].metric("Minimum trades", whole(config["minimum_trades"]))
    streamlit.caption(f"Saved report path: `{run.report_path}`")


def _render_candidate_details(run: ResearchRun, config: dict[str, Any]) -> None:
    streamlit = st()
    selected_rule = streamlit.selectbox(
        "Candidate row",
        tuple(run.results["rule_id"].head(100)),
        key="research_candidate_row",
    )
    row = run.results[run.results["rule_id"] == selected_rule].iloc[0]
    frame = load_dataset_cached(config["path"])
    window = slice_date_window(frame, start=config["start"], end=config["end"])
    rule = rule_from_result_row(row)
    trades = build_rule_trade_ledger(
        window,
        rule,
        holding_period=int(config["holding_period"]),
        round_trip_cost_bps=float(config["cost_bps"]),
    )

    streamlit.subheader("Complete Trade Ledger")
    streamlit.dataframe(display_frame(trades), width="stretch", hide_index=True)
    streamlit.subheader("Sequential Trade Equity And Drawdown")
    render_trade_curves(trades)
    streamlit.subheader("Returns By Calendar Year")
    streamlit.dataframe(
        display_frame(returns_by_calendar_year(trades)),
        width="stretch",
        hide_index=True,
    )
    dist_tabs = streamlit.tabs(["Win/Loss Distribution", "MFE Distribution", "MAE Distribution"])
    with dist_tabs[0]:
        streamlit.bar_chart(trades.get("net_return", pd.Series(dtype=float)))
    with dist_tabs[1]:
        streamlit.bar_chart(trades.get("mfe", pd.Series(dtype=float)))
    with dist_tabs[2]:
        streamlit.bar_chart(trades.get("mae", pd.Series(dtype=float)))


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Research and Backtest",
        "Run in-sample RSI candidate research with next-session-open execution.",
    )

    datasets = discover_raw_datasets(root)
    if not datasets:
        streamlit.info("No raw CSV files are available under data/raw/.")
        return
    by_ticker = _ticker_map(datasets)

    with streamlit.form("research_form"):
        selected_ticker = streamlit.selectbox(
            "Ticker",
            options=tuple(by_ticker.keys()),
            key="research_input_ticker",
        )
        selected = by_ticker[str(selected_ticker)]
        start = streamlit.date_input(
            "Research start",
            value=_years_ago(10),
            key="research_input_start",
        )
        end = streamlit.date_input(
            "Research end",
            value=date.today(),
            key="research_input_end",
        )
        holding_period = streamlit.number_input(
            "Holding period",
            min_value=1,
            value=10,
            step=1,
            key="research_input_holding_period",
        )
        cost_bps = streamlit.number_input(
            "Round-trip cost in basis points",
            min_value=0.0,
            value=5.0,
            step=0.5,
            key="research_input_cost_bps",
        )
        minimum_trades = streamlit.number_input(
            "Minimum trade count",
            min_value=1,
            value=30,
            key="research_input_minimum_trades",
        )
        preset_label = streamlit.selectbox(
            "Grid preset",
            ("Quick plumbing grid", "Standard research grid"),
            key="research_input_grid_preset",
        )
        preset = _preset_value(str(preset_label))
        candidates = candidate_rule_count(grid_for_preset(preset))  # type: ignore[arg-type]
        streamlit.write(f"Candidate rules to evaluate: {whole(candidates)}")
        submitted = streamlit.form_submit_button("Run research")

    current_config = _config(
        ticker=selected.ticker,
        path=selected.path,
        start=start,
        end=end,
        holding_period=int(holding_period),
        cost_bps=float(cost_bps),
        minimum_trades=int(minimum_trades),
        preset=preset,
    )

    if start > end:
        streamlit.error("Research start must be on or before research end.")
        return

    if submitted:
        try:
            frame = load_dataset_cached(selected.path)
            with streamlit.spinner("Running in-sample research..."):
                run = run_research(
                    frame,
                    ticker=selected.ticker,
                    start=start,
                    end=end,
                    holding_period=int(holding_period),
                    round_trip_cost_bps=float(cost_bps),
                    minimum_trades=int(minimum_trades),
                    grid_preset=preset,  # type: ignore[arg-type]
                    reports_dir=root / "reports",
                )
        except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as exc:
            show_expected_error(f"Research run failed: {exc}")
        except Exception as exc:  # pragma: no cover - defensive dashboard guard
            show_unexpected_error(exc, context="research_backtest")
        else:
            streamlit.session_state["research_run"] = run
            streamlit.session_state["research_run_config"] = current_config

    run = streamlit.session_state.get("research_run")
    run_config = streamlit.session_state.get("research_run_config")
    if run is None:
        return
    if run_config != current_config:
        streamlit.warning(
            "A previous research run exists, but it does not match the current form settings. "
            "Submit the form again to refresh results."
        )
        return

    streamlit.success(f"Saved research report to {run.report_path}")
    _render_run_summary(run, current_config)

    if run.results.empty:
        streamlit.warning("No candidate rows were produced.")
        return
    if run.eligible_candidate_count == 0:
        streamlit.warning("No rules met the minimum-trade requirement for this run.")

    streamlit.subheader("Highest-ranked in-sample candidate")
    streamlit.dataframe(display_frame(_compare_rows(run)), width="stretch", hide_index=True)
    control = run.control.metrics
    streamlit.caption(f"Control win rate: {percent(control['win_rate'])}")

    columns = [
        "rule_id",
        "length",
        "lower_level",
        "slope_window",
        "trigger_mode",
        "trend_filter",
        "trade_count",
        "eligible",
        "win_rate",
        "mean_return",
        "median_return",
        "mean_return_lcb_90",
        "profit_factor",
        "max_drawdown",
        "mean_mfe",
        "mean_mae",
        "positive_year_fraction",
        "score",
    ]
    streamlit.subheader("Top Candidate Table")
    streamlit.dataframe(
        display_frame(run.results[columns].head(25)), width="stretch", hide_index=True
    )
    _render_candidate_details(run, current_config)


if __name__ == "__main__":
    render_page()
