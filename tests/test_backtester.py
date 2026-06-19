from __future__ import annotations

import pandas as pd
import pytest

from swing_rsi.backtest.engine import backtest_fixed_horizon


def test_backtester_enters_next_open_and_prevents_overlap() -> None:
    dates = pd.bdate_range("2024-01-02", periods=8)
    frame = pd.DataFrame(
        {
            "Open": [10, 11, 12, 13, 14, 15, 16, 17],
            "High": [11, 12, 13, 14, 15, 16, 17, 18],
            "Low": [9, 10, 11, 12, 13, 14, 15, 16],
            "Close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5],
            "Volume": [1000] * 8,
        },
        index=dates.rename("Date"),
    )
    signals = pd.Series([False, True, False, True, True, False, False, False], index=dates)
    trades = backtest_fixed_horizon(frame, signals, holding_period=3, round_trip_cost_bps=0)

    assert len(trades) == 2
    first = trades.iloc[0]
    assert first["signal_date"] == dates[1]
    assert first["entry_date"] == dates[2]
    assert first["entry_price"] == pytest.approx(12.0)
    assert first["exit_date"] == dates[4]
    assert first["exit_price"] == pytest.approx(14.5)
    # Signal on index 3 is ignored while the first trade is open; index 4 is allowed at exit close.
    second = trades.iloc[1]
    assert second["signal_date"] == dates[4]
    assert second["entry_date"] == dates[5]
