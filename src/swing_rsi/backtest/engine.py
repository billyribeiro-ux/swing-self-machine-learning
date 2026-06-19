from __future__ import annotations

import pandas as pd

from swing_rsi.data.validation import validate_ohlcv

TRADE_COLUMNS = [
    "signal_date",
    "entry_date",
    "exit_date",
    "entry_price",
    "exit_price",
    "holding_period",
    "gross_return",
    "net_return",
    "mfe",
    "mae",
]


def backtest_fixed_horizon(
    frame: pd.DataFrame,
    signals: pd.Series,
    holding_period: int,
    round_trip_cost_bps: float = 5.0,
) -> pd.DataFrame:
    """Backtest close-known signals with next-open entry and non-overlapping trades."""
    data = validate_ohlcv(frame)
    if holding_period < 1:
        raise ValueError("Holding period must be positive")
    if round_trip_cost_bps < 0:
        raise ValueError("Costs cannot be negative")

    aligned = signals.reindex(data.index, fill_value=False).astype(bool)
    signal_positions = [int(position) for position in aligned.to_numpy().nonzero()[0]]
    trades: list[dict[str, object]] = []
    next_eligible_signal_position = 0
    cost_fraction = round_trip_cost_bps / 10_000.0

    for signal_position in signal_positions:
        if signal_position < next_eligible_signal_position:
            continue
        entry_position = signal_position + 1
        exit_position = signal_position + holding_period
        if entry_position >= len(data) or exit_position >= len(data):
            continue

        entry_price = float(data["Open"].iloc[entry_position])
        exit_price = float(data["Close"].iloc[exit_position])
        gross_return = (exit_price / entry_price) - 1.0
        net_return = gross_return - cost_fraction
        high_window = data["High"].iloc[entry_position : exit_position + 1]
        low_window = data["Low"].iloc[entry_position : exit_position + 1]

        trades.append(
            {
                "signal_date": data.index[signal_position],
                "entry_date": data.index[entry_position],
                "exit_date": data.index[exit_position],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "holding_period": holding_period,
                "gross_return": gross_return,
                "net_return": net_return,
                "mfe": (float(high_window.max()) / entry_price) - 1.0,
                "mae": (float(low_window.min()) / entry_price) - 1.0,
            }
        )
        # A signal at the exit close can legitimately enter on the following session.
        next_eligible_signal_position = exit_position

    return pd.DataFrame(trades, columns=TRADE_COLUMNS)
