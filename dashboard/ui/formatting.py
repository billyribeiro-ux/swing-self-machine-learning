from __future__ import annotations

import math
from typing import Any

import pandas as pd


def percent(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if math.isnan(numeric):
        return "n/a"
    return f"{numeric:.2%}"


def decimal(value: Any, digits: int = 4) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if math.isnan(numeric):
        return "n/a"
    return f"{numeric:.{digits}f}"


def whole(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if math.isnan(numeric):
        return "n/a"
    return f"{int(numeric):,}"


def date_label(value: Any) -> str:
    if value is None or str(value) in {"NaT", "nan", "None"}:
        return "n/a"
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return "n/a"
    if pd.isna(timestamp):
        return "n/a"
    return timestamp.date().isoformat()


def price(value: Any) -> str:
    return decimal(value, digits=2)


def ratio(value: Any) -> str:
    return decimal(value, digits=2)


def humanize_column_name(name: object) -> str:
    text = str(name).strip().replace("_", " ")
    if text.lower() == "rsi":
        return "RSI"
    if text.lower() == "mfe":
        return "MFE"
    if text.lower() == "mae":
        return "MAE"
    if text.lower() == "ohlc":
        return "OHLC"
    return " ".join(part.upper() if part in {"id"} else part.capitalize() for part in text.split())


def display_frame(
    frame: pd.DataFrame,
    *,
    date_columns: tuple[str, ...] = ("Date", "signal_date", "entry_date", "exit_date"),
    price_columns: tuple[str, ...] = (
        "Open",
        "High",
        "Low",
        "Close",
        "close",
        "entry_open",
        "exit_close",
    ),
    percent_columns: tuple[str, ...] = (
        "close_to_close_return",
        "abs_close_to_close_return",
        "win_rate",
        "mean_return",
        "median_return",
        "mean_return_lcb_90",
        "max_drawdown",
        "mean_mfe",
        "mean_mae",
        "positive_year_fraction",
        "net_return",
        "gross_return",
        "mfe",
        "mae",
        "compounded_return",
        "weighted_unseen_win_rate",
        "weighted_unseen_mean_return",
        "median_fold_return",
        "fraction_positive_test_folds",
        "test_win_rate",
        "test_mean_return",
        "test_max_drawdown",
        "test_mean_mfe",
        "test_mean_mae",
    ),
    volume_columns: tuple[str, ...] = ("Volume", "volume"),
    decimal_columns: tuple[str, ...] = (
        "RSI",
        "relative_volume_20",
        "close_position",
        "profit_factor",
        "test_profit_factor",
        "score",
        "training_score",
    ),
) -> pd.DataFrame:
    """Return a copy formatted for display only."""
    if frame.empty:
        return frame.copy()

    display = frame.copy()
    for column in display.columns:
        if column in date_columns or str(column).endswith("_date"):
            display[column] = display[column].map(date_label)
        elif column in price_columns:
            display[column] = display[column].map(price)
        elif column in percent_columns or str(column).endswith("_return"):
            display[column] = display[column].map(percent)
        elif column in decimal_columns:
            display[column] = display[column].map(decimal)
        elif column in volume_columns or "volume" in str(column).lower():
            display[column] = display[column].map(whole)

    display = display.rename(
        columns={column: humanize_column_name(column) for column in display.columns}
    )
    return display
