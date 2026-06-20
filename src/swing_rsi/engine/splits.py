from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ChronologicalSplit:
    train: pd.DataFrame
    calibration: pd.DataFrame
    holdout: pd.DataFrame
    train_start: str
    train_end: str
    calibration_start: str
    calibration_end: str
    holdout_start: str
    holdout_end: str
    purge_sessions: int
    embargo_sessions: int


def _date_label(value: pd.Timestamp) -> str:
    return value.date().isoformat()


def _purge_before(
    data: pd.DataFrame,
    *,
    boundary: pd.Timestamp,
    label_end_column: str,
    embargo_sessions: int,
    dates: list[pd.Timestamp],
) -> pd.DataFrame:
    if data.empty:
        return data.copy()
    embargo_start_position = max(dates.index(boundary) - embargo_sessions, 0)
    embargo_start = dates[embargo_start_position]
    label_end = pd.to_datetime(data[label_end_column])
    keep = (label_end < boundary) & (pd.to_datetime(data["Date"]) < embargo_start)
    return data.loc[keep].copy()


def chronological_train_calibration_holdout_split(
    frame: pd.DataFrame,
    *,
    horizon: int,
    validation_fraction: float = 0.2,
    holdout_fraction: float = 0.2,
    embargo_sessions: int = 1,
) -> ChronologicalSplit:
    if frame.empty:
        raise ValueError("Cannot split an empty frame")
    if not 0 < validation_fraction < 0.5 or not 0 < holdout_fraction < 0.5:
        raise ValueError("Validation and holdout fractions must be between 0 and 0.5")
    label_end_column = f"label_end_date_{horizon}"
    if label_end_column not in frame.columns:
        raise ValueError(f"Missing required label end column: {label_end_column}")

    data = frame.dropna(subset=["Date", label_end_column]).copy()
    dates = [pd.Timestamp(value) for value in sorted(pd.to_datetime(data["Date"]).unique())]
    if len(dates) < 30:
        raise ValueError("Need at least 30 unique dates for chronological validation")
    holdout_count = max(int(len(dates) * holdout_fraction), horizon + 2)
    calibration_count = max(int(len(dates) * validation_fraction), horizon + 2)
    train_count = len(dates) - holdout_count - calibration_count
    if train_count <= horizon + embargo_sessions:
        raise ValueError("Not enough unique dates after reserving calibration and holdout windows")

    calibration_start = dates[train_count]
    holdout_start = dates[train_count + calibration_count]
    date_values = pd.to_datetime(data["Date"])
    train_raw = data.loc[date_values < calibration_start].copy()
    calibration_raw = data.loc[
        (date_values >= calibration_start) & (date_values < holdout_start)
    ].copy()
    holdout = data.loc[date_values >= holdout_start].copy()

    train = _purge_before(
        train_raw,
        boundary=calibration_start,
        label_end_column=label_end_column,
        embargo_sessions=embargo_sessions,
        dates=dates,
    )
    calibration = _purge_before(
        calibration_raw,
        boundary=holdout_start,
        label_end_column=label_end_column,
        embargo_sessions=embargo_sessions,
        dates=dates,
    )
    if train.empty or calibration.empty or holdout.empty:
        raise ValueError("Chronological split produced an empty train, calibration, or holdout set")

    return ChronologicalSplit(
        train=train.reset_index(drop=True),
        calibration=calibration.reset_index(drop=True),
        holdout=holdout.reset_index(drop=True),
        train_start=_date_label(pd.Timestamp(train["Date"].min())),
        train_end=_date_label(pd.Timestamp(train["Date"].max())),
        calibration_start=_date_label(pd.Timestamp(calibration["Date"].min())),
        calibration_end=_date_label(pd.Timestamp(calibration["Date"].max())),
        holdout_start=_date_label(pd.Timestamp(holdout["Date"].min())),
        holdout_end=_date_label(pd.Timestamp(holdout["Date"].max())),
        purge_sessions=horizon,
        embargo_sessions=embargo_sessions,
    )
