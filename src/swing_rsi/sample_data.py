from __future__ import annotations

import numpy as np
import pandas as pd


def generate_sample_ohlcv(rows: int = 1_200, seed: int = 42) -> pd.DataFrame:
    """Generate deterministic synthetic daily data for software plumbing tests only."""
    if rows < 260:
        raise ValueError("Generate at least 260 rows so long moving averages are available")
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-02", periods=rows)

    regime = np.where((np.arange(rows) // 160) % 2 == 0, 0.0005, -0.00015)
    cycle = 0.0012 * np.sin(np.arange(rows) / 17.0)
    shocks = rng.normal(0.0, 0.014, rows)
    log_returns = regime + cycle + shocks
    close = 100.0 * np.exp(np.cumsum(log_returns))

    prior_close = np.concatenate(([close[0]], close[:-1]))
    open_price = prior_close * (1.0 + rng.normal(0.0, 0.004, rows))
    intraday_width = np.abs(rng.normal(0.012, 0.005, rows))
    high = np.maximum(open_price, close) * (1.0 + intraday_width)
    low = np.minimum(open_price, close) * np.maximum(0.2, 1.0 - intraday_width)
    volume = rng.lognormal(mean=15.6, sigma=0.35, size=rows).round()

    return pd.DataFrame(
        {
            "Open": open_price,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=dates.rename("Date"),
    )
