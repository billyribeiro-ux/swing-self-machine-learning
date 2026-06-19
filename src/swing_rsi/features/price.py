from __future__ import annotations

import numpy as np
import pandas as pd

from swing_rsi.data.validation import validate_ohlcv
from swing_rsi.features.rsi import wilder_average


def build_price_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create trailing-only daily price, volume, trend, and volatility features."""
    data = validate_ohlcv(frame).copy()
    close = data["Close"]
    prior_close = close.shift(1)

    for window in (20, 50, 100, 200):
        sma = close.rolling(window=window, min_periods=window).mean()
        data[f"sma_{window}"] = sma
        data[f"distance_sma_{window}"] = (close / sma) - 1.0
        data[f"sma_{window}_slope_5"] = sma.pct_change(5)

    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - prior_close).abs(),
            (data["Low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    data["atr_14"] = wilder_average(true_range, 14)
    data["atr_pct_14"] = data["atr_14"] / close
    data["atr_percentile_252"] = (
        data["atr_pct_14"]
        .rolling(252, min_periods=60)
        .apply(lambda values: float(np.mean(values <= values[-1])), raw=True)
    )

    prior_average_volume = data["Volume"].shift(1).rolling(20, min_periods=10).mean()
    data["relative_volume_20"] = data["Volume"] / prior_average_volume

    session_range = data["High"] - data["Low"]
    data["close_position"] = np.where(
        session_range > 0,
        (close - data["Low"]) / session_range,
        0.5,
    )
    data["gap_pct"] = (data["Open"] / prior_close) - 1.0
    data["return_1d"] = close.pct_change()
    data["red_day"] = close < prior_close
    data["pullback_count_3"] = data["red_day"].rolling(3, min_periods=3).sum()
    data["pullback_count_5"] = data["red_day"].rolling(5, min_periods=5).sum()

    for window in (20, 50, 252):
        prior_high = data["High"].shift(1).rolling(window, min_periods=window).max()
        prior_low = data["Low"].shift(1).rolling(window, min_periods=window).min()
        data[f"drawdown_from_high_{window}"] = (close / prior_high) - 1.0
        data[f"bounce_from_low_{window}"] = (close / prior_low) - 1.0

    prior_low_20 = data["Low"].shift(1).rolling(20, min_periods=20).min()
    data["failed_breakdown_20"] = (data["Low"] < prior_low_20) & (close > prior_low_20)
    return data
