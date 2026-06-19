from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from swing_rsi.application.datasets import DateLike, slice_date_window
from swing_rsi.application.research_service import GridPreset, candidate_rule_count, grid_for_preset
from swing_rsi.research.walk_forward import run_walk_forward


@dataclass(frozen=True)
class WalkForwardAggregate:
    folds_evaluated: int
    folds_without_eligible_rules: int
    total_unseen_trades: int
    weighted_unseen_win_rate: float
    weighted_unseen_mean_return: float
    median_fold_return: float
    fraction_positive_test_folds: float
    parameter_stability: pd.DataFrame


@dataclass(frozen=True)
class WalkForwardRun:
    folds: pd.DataFrame
    aggregate: WalkForwardAggregate
    candidate_count: int


def _empty_parameter_stability() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["parameter", "unique_values", "most_common_value", "most_common_count"]
    )


def aggregate_walk_forward_results(folds: pd.DataFrame) -> WalkForwardAggregate:
    if folds.empty:
        return WalkForwardAggregate(
            folds_evaluated=0,
            folds_without_eligible_rules=0,
            total_unseen_trades=0,
            weighted_unseen_win_rate=math.nan,
            weighted_unseen_mean_return=math.nan,
            median_fold_return=math.nan,
            fraction_positive_test_folds=math.nan,
            parameter_stability=_empty_parameter_stability(),
        )

    status = folds["status"] if "status" in folds.columns else pd.Series("", index=folds.index)
    evaluated = folds[status == "evaluated"].copy()
    without_rules = int((status == "no_eligible_training_rule").sum())

    if evaluated.empty:
        return WalkForwardAggregate(
            folds_evaluated=0,
            folds_without_eligible_rules=without_rules,
            total_unseen_trades=0,
            weighted_unseen_win_rate=math.nan,
            weighted_unseen_mean_return=math.nan,
            median_fold_return=math.nan,
            fraction_positive_test_folds=math.nan,
            parameter_stability=_empty_parameter_stability(),
        )

    trade_counts = pd.to_numeric(
        evaluated.get("test_trade_count", pd.Series(0, index=evaluated.index)),
        errors="coerce",
    ).fillna(0)
    test_win_rates = pd.to_numeric(
        evaluated.get("test_win_rate", pd.Series(math.nan, index=evaluated.index)),
        errors="coerce",
    )
    test_mean_returns = pd.to_numeric(
        evaluated.get("test_mean_return", pd.Series(math.nan, index=evaluated.index)),
        errors="coerce",
    )
    total_trades = int(trade_counts.sum())

    if total_trades > 0:
        weighted_win_rate = float((test_win_rates.fillna(0) * trade_counts).sum() / total_trades)
        weighted_mean_return = float(
            (test_mean_returns.fillna(0) * trade_counts).sum() / total_trades
        )
    else:
        weighted_win_rate = math.nan
        weighted_mean_return = math.nan

    non_null_returns = test_mean_returns.dropna()
    stability_rows: list[dict[str, object]] = []
    for column in ("length", "lower_level", "slope_window", "trigger_mode", "trend_filter"):
        if column not in evaluated.columns:
            continue
        counts = evaluated[column].astype(str).value_counts()
        if counts.empty:
            continue
        stability_rows.append(
            {
                "parameter": column,
                "unique_values": int(counts.size),
                "most_common_value": str(counts.index[0]),
                "most_common_count": int(counts.iloc[0]),
            }
        )

    return WalkForwardAggregate(
        folds_evaluated=len(evaluated),
        folds_without_eligible_rules=without_rules,
        total_unseen_trades=total_trades,
        weighted_unseen_win_rate=weighted_win_rate,
        weighted_unseen_mean_return=weighted_mean_return,
        median_fold_return=float(non_null_returns.median())
        if not non_null_returns.empty
        else math.nan,
        fraction_positive_test_folds=(
            float((non_null_returns > 0).mean()) if not non_null_returns.empty else math.nan
        ),
        parameter_stability=pd.DataFrame(stability_rows)
        if stability_rows
        else _empty_parameter_stability(),
    )


def run_walk_forward_validation(
    frame: pd.DataFrame,
    *,
    start: DateLike | None,
    end: DateLike | None,
    holding_period: int,
    round_trip_cost_bps: float,
    minimum_training_trades: int,
    n_splits: int,
    gap: int,
    grid_preset: GridPreset,
) -> WalkForwardRun:
    window = slice_date_window(frame, start=start, end=end)
    if window.empty:
        raise ValueError("Selected walk-forward window contains no rows")
    grid = grid_for_preset(grid_preset)
    folds = run_walk_forward(
        window,
        grid,
        holding_period=holding_period,
        n_splits=n_splits,
        gap=gap,
        round_trip_cost_bps=round_trip_cost_bps,
        minimum_trades=minimum_training_trades,
    )
    return WalkForwardRun(
        folds=folds,
        aggregate=aggregate_walk_forward_results(folds),
        candidate_count=candidate_rule_count(grid),
    )
