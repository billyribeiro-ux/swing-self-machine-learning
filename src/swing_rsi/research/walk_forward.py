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


def expanding_splits(
    sample_count: int,
    n_splits: int = 5,
    test_size: int | None = None,
    gap: int = 1,
    minimum_train_size: int | None = None,
) -> list[ExpandingSplit]:
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2")
    if gap < 0:
        raise ValueError("gap cannot be negative")
    resolved_test_size = test_size or sample_count // (n_splits + 1)
    resolved_minimum = minimum_train_size or resolved_test_size
    first_test_start = sample_count - (n_splits * resolved_test_size)
    if first_test_start - gap < resolved_minimum:
        raise ValueError("Not enough samples for the requested split configuration")

    splits: list[ExpandingSplit] = []
    for fold in range(n_splits):
        test_start = first_test_start + (fold * resolved_test_size)
        test_end = min(test_start + resolved_test_size - 1, sample_count - 1)
        train_end = test_start - gap - 1
        splits.append(
            ExpandingSplit(
                fold=fold,
                train_start=0,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    return splits


def run_walk_forward(
    frame: pd.DataFrame,
    grid: RSIParameterGrid,
    holding_period: int,
    n_splits: int = 5,
    gap: int = 1,
    round_trip_cost_bps: float = 5.0,
    minimum_trades: int = 20,
) -> pd.DataFrame:
    """Select on prior data and evaluate each frozen rule on the next unseen window."""
    features = build_price_features(frame)
    splits = expanding_splits(len(features), n_splits=n_splits, gap=gap)
    fold_rows: list[dict[str, object]] = []

    for split in splits:
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
