from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.ui.components import st
from swing_rsi.application.datasets import dataset_cache_key, load_raw_dataset


def load_dataset_cached(path: str | Path) -> pd.DataFrame:
    key = dataset_cache_key(path)
    return _load_dataset_cached(str(key.path), key.modified_ns).copy()


def clear_dataset_cache() -> None:
    _load_dataset_cached.clear()


@st().cache_data(show_spinner=False)
def _load_dataset_cached(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    return load_raw_dataset(path)
