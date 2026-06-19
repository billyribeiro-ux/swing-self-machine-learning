from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from swing_rsi.data.validation import validate_ohlcv


def _target_name(target: float) -> str:
    return f"{target * 100:g}pct".replace(".", "p")


def add_swing_labels(
    frame: pd.DataFrame,
    horizons: Iterable[int] = (3, 5, 10, 20, 30),
    targets: Iterable[float] = (0.03, 0.05),
) -> pd.DataFrame:
    """Add explicitly future-looking labels using next-session-open entry."""
    data = validate_ohlcv(frame).copy()
    entry = data["Open"].shift(-1)

    for horizon in horizons:
        if horizon < 1:
            raise ValueError("Label horizons must be positive")
        exit_close = data["Close"].shift(-horizon)
        future_high = pd.concat(
            [data["High"].shift(-offset) for offset in range(1, horizon + 1)], axis=1
        ).max(axis=1)
        future_low = pd.concat(
            [data["Low"].shift(-offset) for offset in range(1, horizon + 1)], axis=1
        ).min(axis=1)
        complete = entry.notna() & exit_close.notna()

        returns = (exit_close / entry) - 1.0
        mfe = (future_high / entry) - 1.0
        mae = (future_low / entry) - 1.0
        data[f"label_return_{horizon}d"] = returns.where(complete)
        data[f"label_mfe_{horizon}d"] = mfe.where(complete)
        data[f"label_mae_{horizon}d"] = mae.where(complete)
        data[f"label_positive_{horizon}d"] = (returns > 0).where(complete)
        for target in targets:
            if target <= 0:
                raise ValueError("Targets must be positive")
            data[f"label_hit_{_target_name(target)}_within_{horizon}d"] = (mfe >= target).where(
                complete
            )

    return data


def feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return columns that are safe candidates for model inputs."""
    return [column for column in frame.columns if not column.startswith("label_")]


def assert_no_label_features(columns: Iterable[str]) -> None:
    leaked = [column for column in columns if column.startswith("label_")]
    if leaked:
        raise ValueError(f"Future label columns cannot be model features: {leaked}")
