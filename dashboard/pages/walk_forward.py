from __future__ import annotations

from dataclasses import asdict
from datetime import date

from dashboard.ui.components import render_page_header, repository_root, st
from swing_rsi.application.datasets import discover_raw_datasets, load_raw_dataset
from swing_rsi.application.research_service import candidate_rule_count, grid_for_preset
from swing_rsi.application.validation_service import run_walk_forward_validation


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
        "Walk-Forward Validation",
        "Select parameters on prior data and evaluate frozen rules on unseen folds.",
    )

    datasets = discover_raw_datasets(root)
    if not datasets:
        streamlit.info("No raw CSV files are available under data/raw/.")
        return
    labels = {f"{dataset.ticker} - {dataset.path.name}": dataset for dataset in datasets}

    with streamlit.form("walk_forward_form"):
        selected_label = streamlit.selectbox(
            "Ticker",
            options=tuple(labels.keys()),
            key="walk_forward_ticker",
        )
        selected = labels[str(selected_label)]
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
        streamlit.write(f"Candidate rules per training fold: {candidates:,}")
        submitted = streamlit.form_submit_button("Run walk-forward")

    if submitted:
        try:
            frame = load_raw_dataset(selected.path)
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
            streamlit.error(str(exc))
        else:
            streamlit.session_state["walk_forward_run"] = run

    run = streamlit.session_state.get("walk_forward_run")
    if run is None:
        return

    streamlit.subheader("Out-of-sample walk-forward results")
    aggregate = run.aggregate
    summary = asdict(aggregate)
    summary.pop("parameter_stability")
    streamlit.dataframe([summary], width="stretch")
    streamlit.subheader("Parameter Stability Across Folds")
    streamlit.dataframe(aggregate.parameter_stability, width="stretch")
    streamlit.subheader("Every Fold")
    streamlit.dataframe(run.folds, width="stretch")


if __name__ == "__main__":
    render_page()
