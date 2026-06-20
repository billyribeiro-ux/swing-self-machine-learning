from __future__ import annotations

from itertools import pairwise

import pandas as pd
import pytest

from swing_rsi.application.validation_service import run_walk_forward_validation
from swing_rsi.backtest.engine import backtest_fixed_horizon
from swing_rsi.research.walk_forward import expanding_splits, plan_expanding_splits
from swing_rsi.sample_data import generate_sample_ohlcv


def test_gap_aware_default_split_plan_matches_confirmed_aapl_window() -> None:
    plan = plan_expanding_splits(2_514, n_splits=5, gap=10)

    assert len(plan.splits) == 5
    assert plan.available_after_gap == 2_504
    assert plan.test_size == 417
    assert plan.first_test_start == 429
    assert plan.actual_initial_train_size == 419
    assert plan.required_samples == 2_512
    assert plan.splits[-1].test_end == 2_513

    previous_test_end = -1
    for split in plan.splits:
        assert split.test_start - split.train_end - 1 == 10
        assert split.test_start > previous_test_end
        assert split.test_end < plan.sample_count
        previous_test_end = split.test_end


def test_expanding_splits_are_chronological_and_gapped() -> None:
    splits = expanding_splits(600, n_splits=5, test_size=60, gap=2, minimum_train_size=200)
    assert len(splits) == 5
    for split in splits:
        assert split.train_end < split.test_start
        assert split.test_start - split.train_end - 1 == 2
    assert all(current.train_end < following.train_end for current, following in pairwise(splits))


def test_explicit_impossible_split_reports_required_and_available_sessions() -> None:
    with pytest.raises(ValueError, match="Available sessions=100; required sessions=180"):
        plan_expanding_splits(
            100,
            n_splits=5,
            test_size=30,
            gap=10,
            minimum_train_size=20,
        )


def test_exact_aapl_walk_forward_configuration_does_not_raise_generic_split_failure() -> None:
    frame = generate_sample_ohlcv(rows=2_514)

    result = run_walk_forward_validation(
        frame,
        start=None,
        end=None,
        holding_period=10,
        round_trip_cost_bps=5.0,
        minimum_training_trades=20,
        n_splits=5,
        gap=10,
        grid_preset="quick",
    )

    assert result.split_plan.test_size == 417
    assert result.split_plan.actual_initial_train_size == 419
    assert len(result.split_plan.splits) == 5
    assert len(result.folds) == 5
    assert set(result.folds["status"]).issubset({"evaluated", "no_eligible_training_rule"})


def test_future_test_window_price_changes_do_not_change_prior_training_selection() -> None:
    frame = generate_sample_ohlcv(rows=905)
    baseline = run_walk_forward_validation(
        frame,
        start=None,
        end=None,
        holding_period=10,
        round_trip_cost_bps=5.0,
        minimum_training_trades=5,
        n_splits=3,
        gap=1,
        grid_preset="quick",
    )
    evaluated = baseline.folds[baseline.folds["status"] == "evaluated"]
    assert not evaluated.empty
    target = evaluated.iloc[0]
    test_start = pd.Timestamp(target["test_start"])
    test_end = pd.Timestamp(target["test_end"])

    mutated = frame.copy()
    future_mask = (mutated.index >= test_start) & (mutated.index <= test_end)
    mutated.loc[future_mask, ["Open", "High", "Low", "Close"]] *= 25.0
    rerun = run_walk_forward_validation(
        mutated,
        start=None,
        end=None,
        holding_period=10,
        round_trip_cost_bps=5.0,
        minimum_training_trades=5,
        n_splits=3,
        gap=1,
        grid_preset="quick",
    )

    compare_columns = [
        "selected_rule_id",
        "length",
        "lower_level",
        "slope_window",
        "trigger_mode",
        "trend_filter",
        "training_trade_count",
        "training_score",
    ]
    before_test_window = baseline.folds["status"].eq("evaluated") & (
        pd.to_datetime(baseline.folds["train_end"]) < test_start
    )
    baseline_training = baseline.folds.loc[before_test_window, compare_columns].reset_index(
        drop=True
    )
    rerun_training = rerun.folds.loc[before_test_window, compare_columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(baseline_training, rerun_training)


def test_training_slice_skips_trades_that_would_exit_in_test_window() -> None:
    dates = pd.bdate_range("2024-01-02", periods=8)
    close = pd.Series([100.0, 101.0, 102.0, 103.0, 250.0, 260.0, 270.0, 280.0], index=dates)
    frame = pd.DataFrame(
        {
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000.0,
        },
        index=dates.rename("Date"),
    )
    train = frame.iloc[:4]
    train_signals = pd.Series(False, index=train.index)
    train_signals.iloc[-1] = True

    training_trades = backtest_fixed_horizon(train, train_signals, holding_period=3)
    full_window_trades = backtest_fixed_horizon(
        frame,
        train_signals.reindex(frame.index, fill_value=False),
        holding_period=3,
    )

    assert training_trades.empty
    assert not full_window_trades.empty
    assert full_window_trades["exit_date"].iloc[0] > train.index.max()
