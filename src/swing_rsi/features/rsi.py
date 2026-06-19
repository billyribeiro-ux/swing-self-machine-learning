from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_gain == 0.0 and avg_loss == 0.0:
        return 50.0
    if avg_loss == 0.0:
        return 100.0
    if avg_gain == 0.0:
        return 0.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def wilder_rsi(close: pd.Series, length: int) -> pd.Series:
    """Calculate Wilder RSI with an explicit simple-average seed."""
    if length < 2:
        raise ValueError("RSI length must be at least 2")
    values = pd.to_numeric(close, errors="coerce").to_numpy(dtype=float)
    if np.isnan(values).any():
        raise ValueError("RSI input contains missing or non-numeric values")

    result = np.full(values.size, np.nan, dtype=float)
    if values.size <= length:
        return pd.Series(result, index=close.index, name=f"rsi_{length}")

    deltas = np.diff(values)
    gains = np.where(deltas > 0.0, deltas, 0.0)
    losses = np.where(deltas < 0.0, -deltas, 0.0)

    avg_gain = float(gains[:length].mean())
    avg_loss = float(losses[:length].mean())
    result[length] = _rsi_from_averages(avg_gain, avg_loss)

    for position in range(length + 1, values.size):
        change = values[position] - values[position - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = ((avg_gain * (length - 1)) + gain) / length
        avg_loss = ((avg_loss * (length - 1)) + loss) / length
        result[position] = _rsi_from_averages(avg_gain, avg_loss)

    return pd.Series(result, index=close.index, name=f"rsi_{length}")


def wilder_average(values: pd.Series, length: int) -> pd.Series:
    """Wilder recursive average with a simple-average seed."""
    if length < 1:
        raise ValueError("Length must be positive")
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    result = np.full(numeric.size, np.nan, dtype=float)
    if numeric.size < length:
        return pd.Series(result, index=values.index)

    first_valid = 0
    while first_valid < numeric.size and np.isnan(numeric[first_valid]):
        first_valid += 1
    seed_end = first_valid + length
    if seed_end > numeric.size:
        return pd.Series(result, index=values.index)

    seed = numeric[first_valid:seed_end]
    if np.isnan(seed).any():
        return pd.Series(result, index=values.index)
    average = float(seed.mean())
    result[seed_end - 1] = average

    for position in range(seed_end, numeric.size):
        value = numeric[position]
        if np.isnan(value):
            result[position] = np.nan
            continue
        average = ((average * (length - 1)) + value) / length
        result[position] = average
    return pd.Series(result, index=values.index)
