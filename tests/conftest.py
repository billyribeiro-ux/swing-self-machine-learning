from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def simple_ohlcv() -> pd.DataFrame:
    rows = 320
    dates = pd.bdate_range("2020-01-02", periods=rows)
    close = 100 + np.linspace(0, 35, rows) + 4 * np.sin(np.arange(rows) / 8)
    open_price = np.concatenate(([close[0]], close[:-1]))
    high = np.maximum(open_price, close) + 1.0
    low = np.minimum(open_price, close) - 1.0
    volume = np.full(rows, 1_000_000.0)
    return pd.DataFrame(
        {"Open": open_price, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates.rename("Date"),
    )
