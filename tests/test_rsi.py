from __future__ import annotations

import pandas as pd
import pytest

from swing_rsi.features.rsi import wilder_rsi


def test_rsi_is_100_for_monotonic_increase_after_seed() -> None:
    close = pd.Series(range(1, 40), dtype=float)
    result = wilder_rsi(close, 14)
    assert result.iloc[14:].eq(100.0).all()


def test_rsi_is_zero_for_monotonic_decrease_after_seed() -> None:
    close = pd.Series(range(40, 1, -1), dtype=float)
    result = wilder_rsi(close, 14)
    assert result.iloc[14:].eq(0.0).all()


def test_rsi_is_neutral_for_constant_price() -> None:
    close = pd.Series([100.0] * 40)
    result = wilder_rsi(close, 14)
    assert result.iloc[14:].eq(50.0).all()


def test_rsi_rejects_invalid_length() -> None:
    with pytest.raises(ValueError):
        wilder_rsi(pd.Series([1.0, 2.0, 3.0]), 1)
