from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.ui.cache import load_dataset_cached
from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.errors import show_expected_error, show_unexpected_error
from dashboard.ui.formatting import display_frame, whole
from swing_rsi.application.datasets import DatasetSummary, discover_raw_datasets, slice_date_window
from swing_rsi.application.research_service import candidate_rule_count, grid_for_preset
from swing_rsi.application.validation_service import (
    run_walk_forward_validation,
    validate_walk_forward_configuration,
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
    minimum_training_trades: int,
    folds: int,
    gap: int,
    preset: str,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "path": str(path),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "holding_period": holding_period,
        "cost_bps": cost_bps,
        "minimum_training_trades": minimum_training_trades,
        "folds": folds,
        "gap": gap,
        "preset": preset,
    }


def _training_columns(folds: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "fold",
        "status",
        "train_end",
        "test_start",
        "test_end",
        "selected_rule_id",
        "length",
        "lower_level",
        "slope_window",
        "trigger_mode",
        "trend_filter",
        "training_trade_count",
        "training_score",
    ]
    return folds[[column for column in columns if column in folds.columns]]


def _test_columns(folds: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "fold",
        "status",
        "test_trade_count",
        "test_win_rate",
        "test_mean_return",
        "test_profit_factor",
        "test_max_drawdown",
        "test_mean_mfe",
        "test_mean_mae",
    ]
    return folds[[column for column in columns if column in folds.columns]]


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Walk-Forward Validation",
        "Select parameters on prior data and evaluate frozen rules on unseen folds.",
    )

    datasets = discover_raw_datasets(root)
    if not datasets:
        streamlit.info("No raw CSV files are available under data/raw/.")
        return
    by_ticker = _ticker_map(datasets)

    with streamlit.form("walk_forward_form"):
        selected_ticker = streamlit.selectbox(
            "Ticker",
            options=tuple(by_ticker.keys()),
            key="walk_forward_ticker",
        )
        selected = by_ticker[str(selected_ticker)]
        start = streamlit.date_input(
            "Research start",
            value=_years_ago(10),
            key="walk_forward_start",
        )
        end = streamlit.date_input(
            "Research end",
            value=date.today(),
            key="walk_forward_end",
        )
        holding_period = streamlit.number_input(
            "Holding period",
            min_value=1,
            value=10,
            step=1,
            key="walk_forward_holding_period",
        )
        cost_bps = streamlit.number_input(
            "Round-trip cost in basis points",
            min_value=0.0,
            value=5.0,
            step=0.5,
            key="walk_forward_cost_bps",
        )
        minimum_training_trades = streamlit.number_input(
            "Minimum training trades",
            min_value=1,
            value=20,
            key="walk_forward_minimum_training_trades",
        )
        folds = streamlit.number_input(
            "Number of folds",
            min_value=2,
            value=5,
            key="walk_forward_folds",
        )
        gap = streamlit.number_input("Gap", min_value=0, value=1, key="walk_forward_gap")
        streamlit.caption(
            "Gap is the number of sessions left unused between training and test windows. "
            "Training trades that cannot enter and exit inside the training slice are skipped."
        )
        preset_label = streamlit.selectbox(
            "Grid preset",
            ("Quick plumbing grid", "Standard research grid"),
            key="walk_forward_grid_preset",
        )
        preset = _preset_value(str(preset_label))
        candidates = candidate_rule_count(grid_for_preset(preset))  # type: ignore[arg-type]
        streamlit.write(f"Candidate rules per training fold: {whole(candidates)}")
        submitted = streamlit.form_submit_button("Run walk-forward")

    current_config = _config(
        ticker=selected.ticker,
        path=selected.path,
        start=start,
        end=end,
        holding_period=int(holding_period),
        cost_bps=float(cost_bps),
        minimum_training_trades=int(minimum_training_trades),
        folds=int(folds),
        gap=int(gap),
        preset=preset,
    )

    if start > end:
        streamlit.error("Research start must be on or before research end.")
        return

    if submitted:
        try:
            frame = load_dataset_cached(selected.path)
            window = slice_date_window(frame, start=start, end=end)
            validate_walk_forward_configuration(len(window), n_splits=int(folds), gap=int(gap))
            with streamlit.spinner("Running walk-forward validation..."):
                run = run_walk_forward_validation(
                    frame,
                    start=start,
                    end=end,
                    holding_period=int(holding_period),
                    round_trip_cost_bps=float(cost_bps),
                    minimum_training_trades=int(minimum_training_trades),
                    n_splits=int(folds),
                    gap=int(gap),
                    grid_preset=preset,  # type: ignore[arg-type]
                )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            show_expected_error(f"Walk-forward run failed: {exc}")
        except Exception as exc:  # pragma: no cover - defensive dashboard guard
            show_unexpected_error(exc, context="walk_forward")
        else:
            streamlit.session_state["walk_forward_run"] = run
            streamlit.session_state["walk_forward_run_config"] = current_config

    run = streamlit.session_state.get("walk_forward_run")
    run_config = streamlit.session_state.get("walk_forward_run_config")
    if run is None:
        return
    if run_config != current_config:
        streamlit.warning(
            "A previous walk-forward run exists, but it does not match the current form settings. "
            "Submit the form again to refresh results."
        )
        return

    streamlit.subheader("Out-of-sample walk-forward results")
    aggregate = run.aggregate
    summary = asdict(aggregate)
    summary.pop("parameter_stability")
    streamlit.dataframe(display_frame(pd.DataFrame([summary])), width="stretch", hide_index=True)
    streamlit.subheader("Parameter Stability Across Folds")
    streamlit.dataframe(
        display_frame(aggregate.parameter_stability), width="stretch", hide_index=True
    )
    streamlit.subheader("Frozen Training Selection By Fold")
    streamlit.dataframe(
        display_frame(_training_columns(run.folds)), width="stretch", hide_index=True
    )
    streamlit.subheader("Unseen Test Metrics By Fold")
    streamlit.dataframe(display_frame(_test_columns(run.folds)), width="stretch", hide_index=True)


if __name__ == "__main__":
    render_page()
