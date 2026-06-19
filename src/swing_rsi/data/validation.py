from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def normalize_ohlcv_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize common provider column spellings without changing price semantics."""
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    aliases = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "adj close": "Adj Close",
        "adj_close": "Adj Close",
        "adjclose": "Adj Close",
        "adjusted close": "Adj Close",
        "volume": "Volume",
        "date": "Date",
        "datetime": "Date",
        "timestamp": "Date",
    }
    renamed = {
        column: aliases.get(str(column).strip().lower(), str(column).strip())
        for column in data.columns
    }
    return data.rename(columns=renamed)


def _require_columns(columns: Iterable[str]) -> None:
    available = set(columns)
    missing = [column for column in REQUIRED_COLUMNS if column not in available]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {missing}")


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Return sorted, numeric, duplicate-free daily OHLCV or raise a clear error."""
    data = normalize_ohlcv_columns(frame)
    _require_columns(data.columns)

    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("OHLCV frame must use a DatetimeIndex")

    data = data.sort_index()
    if data.index.has_duplicates:
        duplicates = data.index[data.index.duplicated()].unique()
        raise ValueError(f"Duplicate session dates found: {duplicates[:5].tolist()}")

    for column in (*REQUIRED_COLUMNS, "Adj Close"):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    if data[list(REQUIRED_COLUMNS)].isna().any().any():
        bad = data.index[data[list(REQUIRED_COLUMNS)].isna().any(axis=1)]
        raise ValueError(f"Missing or non-numeric OHLCV values at: {bad[:5].tolist()}")

    prices = data[["Open", "High", "Low", "Close"]]
    if (prices <= 0).any().any():
        raise ValueError("Open, high, low, and close must be positive")
    if (data["Volume"] < 0).any():
        raise ValueError("Volume cannot be negative")
    if (data["High"] < data["Low"]).any():
        raise ValueError("High cannot be below low")

    tolerance = np.maximum(data["High"].abs() * 1e-10, 1e-10)
    if (data["Open"] > data["High"] + tolerance).any() or (
        data["Close"] > data["High"] + tolerance
    ).any():
        raise ValueError("Open and close must not exceed high")
    if (data["Open"] < data["Low"] - tolerance).any() or (
        data["Close"] < data["Low"] - tolerance
    ).any():
        raise ValueError("Open and close must not be below low")

    # Daily research uses session dates; remove timezone while preserving the date label.
    date_index = pd.DatetimeIndex(data.index)
    if date_index.tz is not None:
        date_index = date_index.tz_localize(None)
    data.index = date_index
    data.index.name = "Date"
    return data
