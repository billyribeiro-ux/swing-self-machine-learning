from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from swing_rsi.application.datasets import DateLike, slice_date_window
from swing_rsi.application.research_service import GridPreset, candidate_rule_count, grid_for_preset
from swing_rsi.research.walk_forward import (
    ExpandingSplitPlan,
    plan_expanding_splits,
    run_walk_forward,
)


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
    split_plan: ExpandingSplitPlan


@dataclass(frozen=True)
class WalkForwardConfigurationPreview:
    requested_start: str | None
    requested_end: str | None
    effective_first_session: str | None
    effective_last_session: str | None
    available_sessions: int
    initial_training_sessions: int | None
    sessions_per_test_fold: int | None
    gap_sessions: int
    n_splits: int
    total_required_sessions: int | None
    status: str
    message: str | None
    split_plan: ExpandingSplitPlan | None


def _iso(value: DateLike | None) -> str | None:
    if value is None:
        return None
    return pd.Timestamp(value).date().isoformat()


def _window_bound(value: pd.Timestamp | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    return value.date().isoformat()


def validate_walk_forward_configuration(
    sample_count: int,
    n_splits: int,
    gap: int,
    test_size: int | None = None,
    minimum_train_size: int | None = None,
) -> ExpandingSplitPlan:
    if sample_count <= 0:
        raise ValueError("Selected walk-forward window contains no rows")
    return plan_expanding_splits(
        sample_count,
        n_splits=n_splits,
        test_size=test_size,
        gap=gap,
        minimum_train_size=minimum_train_size,
    )


def preview_walk_forward_configuration(
    frame: pd.DataFrame,
    *,
    start: DateLike | None,
    end: DateLike | None,
    n_splits: int,
    gap: int,
    test_size: int | None = None,
    minimum_train_size: int | None = None,
) -> WalkForwardConfigurationPreview:
    window = slice_date_window(frame, start=start, end=end)
    effective_first = _window_bound(window.index.min()) if not window.empty else None
    effective_last = _window_bound(window.index.max()) if not window.empty else None

    try:
        plan = validate_walk_forward_configuration(
            len(window),
            n_splits=n_splits,
            gap=gap,
            test_size=test_size,
            minimum_train_size=minimum_train_size,
        )
    except ValueError as exc:
        return WalkForwardConfigurationPreview(
            requested_start=_iso(start),
            requested_end=_iso(end),
            effective_first_session=effective_first,
            effective_last_session=effective_last,
            available_sessions=len(window),
            initial_training_sessions=None,
            sessions_per_test_fold=test_size,
            gap_sessions=gap,
            n_splits=n_splits,
            total_required_sessions=None,
            status="Invalid",
            message=str(exc),
            split_plan=None,
        )

    return WalkForwardConfigurationPreview(
        requested_start=_iso(start),
        requested_end=_iso(end),
        effective_first_session=effective_first,
        effective_last_session=effective_last,
        available_sessions=len(window),
        initial_training_sessions=plan.actual_initial_train_size,
        sessions_per_test_fold=plan.test_size,
        gap_sessions=gap,
        n_splits=n_splits,
        total_required_sessions=plan.required_samples,
        status="Valid",
        message=None,
        split_plan=plan,
    )


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
    split_plan = validate_walk_forward_configuration(len(window), n_splits=n_splits, gap=gap)
    grid = grid_for_preset(grid_preset)
    folds = run_walk_forward(
        window,
        grid,
        holding_period=holding_period,
        n_splits=n_splits,
        gap=gap,
        round_trip_cost_bps=round_trip_cost_bps,
        minimum_trades=minimum_training_trades,
        split_plan=split_plan,
    )
    return WalkForwardRun(
        folds=folds,
        aggregate=aggregate_walk_forward_results(folds),
        candidate_count=candidate_rule_count(grid),
        split_plan=split_plan,
    )
