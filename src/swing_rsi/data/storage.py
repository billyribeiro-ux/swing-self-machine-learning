from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_frame(frame: pd.DataFrame, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(output, index=True)
    elif suffix == ".parquet":
        frame.to_parquet(output, index=True)
    else:
        raise ValueError("Supported storage formats are .csv and .parquet")
    return output


def load_frame(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source, index_col=0, parse_dates=True)
    elif source.suffix.lower() == ".parquet":
        frame = pd.read_parquet(source)
    else:
        raise ValueError("Supported storage formats are .csv and .parquet")
    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index)
    return frame
