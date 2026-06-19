from __future__ import annotations

from pathlib import Path

import pandas as pd

from swing_rsi.data.validation import normalize_ohlcv_columns, validate_ohlcv


def load_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    data = normalize_ohlcv_columns(pd.read_csv(csv_path))
    if "Date" not in data.columns:
        raise ValueError(f"{csv_path} must contain a Date column")
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    if data["Date"].isna().any():
        raise ValueError(f"{csv_path} contains invalid dates")
    data = data.set_index("Date")
    return validate_ohlcv(data)


def save_ohlcv_csv(frame: pd.DataFrame, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    validate_ohlcv(frame).to_csv(output, index=True)
    return output


def download_yfinance_daily(
    ticker: str,
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """Bootstrap adapter only; production data quality must be audited separately."""
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            'Install the market-data extra first: pip install -e ".[market-data]"'
        ) from exc

    data = yf.download(
        ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if data.empty:
        raise ValueError(f"No daily data returned for {ticker}")
    data = normalize_ohlcv_columns(data)
    return validate_ohlcv(data)
