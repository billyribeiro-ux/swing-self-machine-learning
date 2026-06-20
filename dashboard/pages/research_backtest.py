from __future__ import annotations

from datetime import date

from dashboard.ui.charts import render_trade_curves
from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import percent
from swing_rsi.application.datasets import (
    discover_raw_datasets,
    load_raw_dataset,
    slice_date_window,
)
from swing_rsi.application.research_service import (
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
    labels = {f"{dataset.ticker} - {dataset.path.name}": dataset for dataset in datasets}

    with streamlit.form("research_form"):
        selected_label = streamlit.selectbox(
            "Ticker",
            options=tuple(labels.keys()),
            key="research_input_ticker",
        )
        selected = labels[str(selected_label)]
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
        streamlit.write(f"Candidate rules to evaluate: {candidates:,}")
        submitted = streamlit.form_submit_button("Run research")

    if submitted:
        try:
            frame = load_raw_dataset(selected.path)
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
            streamlit.error(str(exc))
        else:
            streamlit.session_state["research_run"] = run
            streamlit.session_state["research_source_path"] = selected.path
            streamlit.session_state["research_holding_period"] = int(holding_period)
            streamlit.session_state["research_cost_bps"] = float(cost_bps)
            streamlit.session_state["research_start"] = start
            streamlit.session_state["research_end"] = end

    run = streamlit.session_state.get("research_run")
    if run is None:
        return

    streamlit.success(f"Saved research report to {run.report_path}")
    streamlit.metric("Candidate count", run.candidate_count)
    streamlit.metric("Eligible candidate count", run.eligible_candidate_count)

    if run.results.empty:
        streamlit.warning("No candidate rows were produced.")
        return

    streamlit.subheader("Highest-ranked in-sample candidate")
    highest = run.results.iloc[0]
    control = run.control.metrics
    compare = [
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
    streamlit.dataframe(compare, width="stretch")
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
    streamlit.dataframe(run.results[columns].head(25), width="stretch")

    selected_rule = streamlit.selectbox(
        "Candidate row",
        tuple(run.results["rule_id"].head(100)),
        key="research_candidate_row",
    )
    row = run.results[run.results["rule_id"] == selected_rule].iloc[0]
    source_path = streamlit.session_state["research_source_path"]
    frame = load_raw_dataset(source_path)
    window = slice_date_window(
        frame,
        start=streamlit.session_state["research_start"],
        end=streamlit.session_state["research_end"],
    )
    rule = rule_from_result_row(row)
    trades = build_rule_trade_ledger(
        window,
        rule,
        holding_period=int(streamlit.session_state["research_holding_period"]),
        round_trip_cost_bps=float(streamlit.session_state["research_cost_bps"]),
    )

    streamlit.subheader("Complete Trade Ledger")
    streamlit.dataframe(trades, width="stretch")
    streamlit.subheader("Sequential Trade Equity And Drawdown")
    render_trade_curves(trades)
    streamlit.subheader("Returns By Calendar Year")
    streamlit.dataframe(returns_by_calendar_year(trades), width="stretch")
    dist_tabs = streamlit.tabs(["Win/loss distribution", "MFE distribution", "MAE distribution"])
    with dist_tabs[0]:
        streamlit.bar_chart(trades.get("net_return", []))
    with dist_tabs[1]:
        streamlit.bar_chart(trades.get("mfe", []))
    with dist_tabs[2]:
        streamlit.bar_chart(trades.get("mae", []))


if __name__ == "__main__":
    render_page()
