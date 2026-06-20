from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from swing_rsi.backtest.engine import backtest_fixed_horizon
from swing_rsi.backtest.metrics import summarize_trades
from swing_rsi.features.price import build_price_features
from swing_rsi.research.grid_search import RSIParameterGrid, rule_from_result, run_grid_search
from swing_rsi.signals.rsi_reversal import generate_rsi_reversal_signal


@dataclass(frozen=True)
class ExpandingSplit:
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True)
class ExpandingSplitPlan:
    sample_count: int
    n_splits: int
    gap: int
    test_size: int
    minimum_train_size: int
    first_test_start: int
    actual_initial_train_size: int
    available_after_gap: int
    required_samples: int
    splits: tuple[ExpandingSplit, ...]


def _split_error(
    *,
    sample_count: int,
    n_splits: int,
    gap: int,
    test_size: int,
    minimum_train_size: int,
    reason: str,
) -> ValueError:
    required_samples = minimum_train_size + gap + (n_splits * max(test_size, 1))
    remaining_after_training_gap = sample_count - minimum_train_size - gap
    nearest_test_size = (
        remaining_after_training_gap // n_splits
        if n_splits > 0 and remaining_after_training_gap >= n_splits
        else None
    )
    nearest_folds = remaining_after_training_gap if remaining_after_training_gap >= 2 else None

    nearest_parts: list[str] = []
    if nearest_test_size is not None and nearest_test_size >= 1:
        nearest_parts.append(
            f"use at most {nearest_test_size} sessions per test fold with {n_splits} folds"
        )
    if nearest_folds is not None and nearest_folds >= 2:
        nearest_parts.append(f"or use at most {nearest_folds} folds with 1 session per test fold")
    nearest = "; ".join(nearest_parts) if nearest_parts else "reduce folds, gap, or training size"
    arithmetic = (
        f"minimum_train_size ({minimum_train_size}) + gap ({gap}) + "
        f"n_splits ({n_splits}) * test_size ({max(test_size, 1)}) = {required_samples}"
    )
    return ValueError(
        "Invalid walk-forward split configuration: "
        f"{reason}. Available sessions={sample_count}; required sessions={required_samples}. "
        f"Arithmetic: {arithmetic}. Nearest valid configuration: {nearest}."
    )


def plan_expanding_splits(
    sample_count: int,
    n_splits: int = 5,
    test_size: int | None = None,
    gap: int = 1,
    minimum_train_size: int | None = None,
) -> ExpandingSplitPlan:
    if sample_count <= 0:
        raise ValueError("sample_count must be greater than 0")
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2")
    if gap < 0:
        raise ValueError("gap cannot be negative")
    if test_size is not None and test_size < 1:
        raise ValueError("test_size must be at least 1")

    available_after_gap = sample_count - gap
    if test_size is None:
        resolved_test_size = available_after_gap // (n_splits + 1)
        if resolved_test_size < 1:
            resolved_minimum_for_error = minimum_train_size or 1
            raise _split_error(
                sample_count=sample_count,
                n_splits=n_splits,
                gap=gap,
                test_size=1,
                minimum_train_size=resolved_minimum_for_error,
                reason="the gap leaves too few sessions to allocate a test fold",
            )
    else:
        resolved_test_size = test_size

    resolved_minimum = minimum_train_size or resolved_test_size
    if resolved_minimum < 1:
        raise ValueError("minimum_train_size must be at least 1")

    required_samples = resolved_minimum + gap + (n_splits * resolved_test_size)
    if sample_count < required_samples:
        raise _split_error(
            sample_count=sample_count,
            n_splits=n_splits,
            gap=gap,
            test_size=resolved_test_size,
            minimum_train_size=resolved_minimum,
            reason="not enough sessions for the requested folds",
        )

    first_test_start = sample_count - (n_splits * resolved_test_size)
    actual_initial_train_size = first_test_start - gap
    if actual_initial_train_size < resolved_minimum:
        raise _split_error(
            sample_count=sample_count,
            n_splits=n_splits,
            gap=gap,
            test_size=resolved_test_size,
            minimum_train_size=resolved_minimum,
            reason="the first training range is smaller than the required minimum",
        )

    splits: list[ExpandingSplit] = []
    for fold in range(n_splits):
        test_start = first_test_start + (fold * resolved_test_size)
        test_end = test_start + resolved_test_size - 1
        train_end = test_start - gap - 1
        split = ExpandingSplit(
            fold=fold,
            train_start=0,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
        )
        if split.train_end < split.train_start:
            raise ValueError("every train range must be nonempty")
        if split.test_end < split.test_start:
            raise ValueError("every test range must be nonempty")
        if split.test_end >= sample_count:
            raise ValueError("test index is outside the available frame")
        if split.test_start - split.train_end - 1 != gap:
            raise ValueError("every fold must preserve the requested gap")
        if splits and split.test_start <= splits[-1].test_end:
            raise ValueError("test folds must be chronological and non-overlapping")
        splits.append(split)

    if splits[-1].test_end != sample_count - 1:
        raise ValueError("final test fold must end at the final available sample")

    return ExpandingSplitPlan(
        sample_count=sample_count,
        n_splits=n_splits,
        gap=gap,
        test_size=resolved_test_size,
        minimum_train_size=resolved_minimum,
        first_test_start=first_test_start,
        actual_initial_train_size=actual_initial_train_size,
        available_after_gap=available_after_gap,
        required_samples=required_samples,
        splits=tuple(splits),
    )


def expanding_splits(
    sample_count: int,
    n_splits: int = 5,
    test_size: int | None = None,
    gap: int = 1,
    minimum_train_size: int | None = None,
) -> list[ExpandingSplit]:
    return list(
        plan_expanding_splits(
            sample_count,
            n_splits=n_splits,
            test_size=test_size,
            gap=gap,
            minimum_train_size=minimum_train_size,
        ).splits
    )


def run_walk_forward(
    frame: pd.DataFrame,
    grid: RSIParameterGrid,
    holding_period: int,
    n_splits: int = 5,
    gap: int = 1,
    round_trip_cost_bps: float = 5.0,
    minimum_trades: int = 20,
    split_plan: ExpandingSplitPlan | None = None,
) -> pd.DataFrame:
    """Select on prior data and evaluate each frozen rule on the next unseen window."""
    features = build_price_features(frame)
    plan = split_plan or plan_expanding_splits(len(features), n_splits=n_splits, gap=gap)
    if plan.sample_count != len(features):
        raise ValueError("split plan sample count does not match the feature frame")
    if plan.n_splits != n_splits or plan.gap != gap:
        raise ValueError("split plan does not match requested walk-forward settings")
    fold_rows: list[dict[str, object]] = []

    for split in plan.splits:
        train = features.iloc[split.train_start : split.train_end + 1]
        train_results = run_grid_search(
            train,
            grid,
            holding_period=holding_period,
            round_trip_cost_bps=round_trip_cost_bps,
            minimum_trades=minimum_trades,
        )
        eligible = train_results[train_results["eligible"]]
        if eligible.empty:
            fold_rows.append({"fold": split.fold, "status": "no_eligible_training_rule"})
            continue

        best = eligible.iloc[0]
        rule = rule_from_result(best)
        full_signals = generate_rsi_reversal_signal(features, rule)
        test_mask = pd.Series(False, index=features.index)
        test_mask.iloc[split.test_start : split.test_end + 1] = True
        test_signals = full_signals & test_mask
        trades = backtest_fixed_horizon(
            features,
            test_signals,
            holding_period=holding_period,
            round_trip_cost_bps=round_trip_cost_bps,
        )
        if not trades.empty:
            final_test_date = features.index[split.test_end]
            trades = trades[trades["exit_date"] <= final_test_date].reset_index(drop=True)
        metrics = summarize_trades(trades, minimum_trades=1)
        fold_rows.append(
            {
                "fold": split.fold,
                "status": "evaluated",
                "train_end": features.index[split.train_end],
                "test_start": features.index[split.test_start],
                "test_end": features.index[split.test_end],
                "selected_rule_id": rule.rule_id,
                **rule.to_dict(),
                "training_trade_count": int(best["trade_count"]),
                "training_score": float(best["score"]),
                **{f"test_{key}": value for key, value in metrics.items()},
            }
        )

    return pd.DataFrame(fold_rows)
