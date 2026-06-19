from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd


def atomic_write_csv(frame: pd.DataFrame, path: str | Path, index: bool = False) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".csv",
        dir=output.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        frame.to_csv(handle, index=index)
    temporary.replace(output)
    return output
