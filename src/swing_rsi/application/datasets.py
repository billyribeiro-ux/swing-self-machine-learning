from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from swing_rsi.config import ProjectPaths
from swing_rsi.data.loader import download_daily, load_ohlcv_csv
from swing_rsi.data.validation import REQUIRED_COLUMNS, normalize_ohlcv_columns, validate_ohlcv
from swing_rsi.reports.writer import atomic_write_csv

type DateLike = date | str | pd.Timestamp
type DailyDownloader = Callable[[str, str | None, str | None, str], pd.DataFrame]


@dataclass(frozen=True)
class DatasetSummary:
    ticker: str
    path: Path
    row_count: int | None
    first_date: str | None
    latest_date: str | None
    modified_at_utc: str
    error: str | None = None


@dataclass(frozen=True)
class DownloadResult:
    ticker: str
    downloaded_rows: int
    existing_rows: int
    replaced_dates: int
    inserted_dates: int
    final_rows: int
    first_date: str
    last_date: str
    saved_path: Path


@dataclass(frozen=True)
class StructuralAudit:
    path: Path
    row_count: int
    first_date: str | None
    last_date: str | None
    duplicate_dates: int
    missing_required_values: int
    missing_required_columns: tuple[str, ...]
    zero_volume_rows: int
    invalid_ohlc_rows: int
    nonpositive_price_rows: int
    largest_close_moves: pd.DataFrame
    first_rows: pd.DataFrame
    last_rows: pd.DataFrame


def _iso_date(value: date | datetime | str | pd.Timestamp | None) -> str | None:
    if value is None or str(value) in {"NaT", "nan", "None"}:
        return None
    timestamp = pd.Timestamp(value)
    return timestamp.date().isoformat()


def _file_modified_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def discover_raw_datasets(root: str | Path) -> tuple[DatasetSummary, ...]:
    raw_directory = ProjectPaths(Path(root)).raw_data
    if not raw_directory.exists():
        return ()

    summaries: list[DatasetSummary] = []
    for path in sorted(raw_directory.glob("*.csv")):
        ticker = path.stem.upper()
        try:
            frame = load_ohlcv_csv(path)
        except (FileNotFoundError, ValueError) as exc:
            summaries.append(
                DatasetSummary(
                    ticker=ticker,
                    path=path,
                    row_count=None,
                    first_date=None,
                    latest_date=None,
                    modified_at_utc=_file_modified_at(path),
                    error=str(exc),
                )
            )
            continue

        summaries.append(
            DatasetSummary(
                ticker=ticker,
                path=path,
                row_count=len(frame),
                first_date=_iso_date(frame.index.min()),
                latest_date=_iso_date(frame.index.max()),
                modified_at_utc=_file_modified_at(path),
            )
        )
    return tuple(summaries)


def load_raw_dataset(path: str | Path) -> pd.DataFrame:
    return load_ohlcv_csv(path)


def slice_date_window(
    frame: pd.DataFrame,
    start: DateLike | None = None,
    end: DateLike | None = None,
) -> pd.DataFrame:
    data = validate_ohlcv(frame).copy()
    if start is not None:
        data = data.loc[data.index >= pd.Timestamp(start)]
    if end is not None:
        data = data.loc[data.index <= pd.Timestamp(end)]
    return data.sort_index()


def _download_daily_frame(
    ticker: str,
    start: str | None,
    end: str | None,
    provider: str,
) -> pd.DataFrame:
    return download_daily(ticker, start=start, end=end, provider=provider)


def _merge_downloaded_history(
    existing: pd.DataFrame | None,
    downloaded: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int, int]:
    existing_rows = len(existing) if existing is not None else 0
    if existing is None:
        merged = downloaded.copy()
        return merged.sort_index(), existing_rows, 0, len(downloaded)

    existing_dates = set(existing.index)
    downloaded_dates = set(downloaded.index)
    replaced_dates = len(existing_dates & downloaded_dates)
    inserted_dates = len(downloaded_dates - existing_dates)
    preserved_existing = existing.loc[~existing.index.isin(downloaded.index)]
    merged = pd.concat([preserved_existing, downloaded], axis=0).sort_index()
    return merged, existing_rows, replaced_dates, inserted_dates


def download_daily_to_raw(
    root: str | Path,
    ticker: str,
    start: str,
    end: str | None = None,
    *,
    provider: str = "fmp",
    downloader: DailyDownloader = _download_daily_frame,
) -> DownloadResult:
    normalized_provider = provider.strip().lower()
    if normalized_provider != "fmp":
        raise ValueError("Version 1 dashboard downloads are fixed to FMP")

    paths = ProjectPaths(Path(root))
    paths.ensure()
    symbol = ticker.strip().upper()
    output = paths.raw_data / f"{symbol}.csv"

    existing = load_ohlcv_csv(output) if output.exists() else None
    downloaded = validate_ohlcv(downloader(symbol, start, end, "fmp"))
    merged, existing_rows, replaced_dates, inserted_dates = _merge_downloaded_history(
        existing,
        downloaded,
    )
    validated = validate_ohlcv(merged)
    atomic_write_csv(validated, output, index=True)
    return DownloadResult(
        ticker=symbol,
        downloaded_rows=len(downloaded),
        existing_rows=existing_rows,
        replaced_dates=replaced_dates,
        inserted_dates=inserted_dates,
        final_rows=len(validated),
        first_date=_iso_date(validated.index.min()) or "",
        last_date=_iso_date(validated.index.max()) or "",
        saved_path=output,
    )


def structural_audit_csv(path: str | Path) -> StructuralAudit:
    source = Path(path)
    raw = normalize_ohlcv_columns(pd.read_csv(source))
    row_count = len(raw)
    missing_columns = tuple(column for column in REQUIRED_COLUMNS if column not in raw.columns)

    dates = (
        pd.to_datetime(raw["Date"], errors="coerce")
        if "Date" in raw.columns
        else pd.Series(pd.NaT, index=raw.index)
    )
    duplicate_dates = int(dates.duplicated(keep=False).sum()) if "Date" in raw.columns else 0

    numeric: dict[str, pd.Series] = {}
    missing_required_values = 0
    for column in REQUIRED_COLUMNS:
        if column not in raw.columns:
            missing_required_values += row_count
            continue
        values = pd.to_numeric(raw[column], errors="coerce")
        numeric[column] = values
        missing_required_values += int(values.isna().sum())

    zero_volume_rows = int((numeric["Volume"] == 0).sum()) if "Volume" in numeric else 0

    price_columns = ("Open", "High", "Low", "Close")
    if all(column in numeric for column in price_columns):
        prices = pd.DataFrame({column: numeric[column] for column in price_columns})
        nonpositive_price_rows = int((prices <= 0).any(axis=1).sum())
        invalid_ohlc = (
            (prices["High"] < prices["Low"])
            | (prices["Open"] > prices["High"])
            | (prices["Close"] > prices["High"])
            | (prices["Open"] < prices["Low"])
            | (prices["Close"] < prices["Low"])
        )
        invalid_ohlc_rows = int(invalid_ohlc.sum())
    else:
        nonpositive_price_rows = 0
        invalid_ohlc_rows = 0

    close_moves = pd.DataFrame()
    if "Close" in numeric:
        close_frame = pd.DataFrame({"Date": dates, "Close": numeric["Close"]}).sort_values("Date")
        close_frame["close_to_close_return"] = close_frame["Close"].pct_change()
        close_frame["abs_close_to_close_return"] = close_frame["close_to_close_return"].abs()
        close_moves = (
            close_frame.dropna(subset=["abs_close_to_close_return"])
            .sort_values("abs_close_to_close_return", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

    dated = raw.copy()
    if "Date" in dated.columns:
        dated["Date"] = dates
    sorted_raw = dated.sort_values("Date") if "Date" in dated.columns else dated
    valid_dates = dates.dropna()

    return StructuralAudit(
        path=source,
        row_count=row_count,
        first_date=_iso_date(valid_dates.min()) if not valid_dates.empty else None,
        last_date=_iso_date(valid_dates.max()) if not valid_dates.empty else None,
        duplicate_dates=duplicate_dates,
        missing_required_values=missing_required_values,
        missing_required_columns=missing_columns,
        zero_volume_rows=zero_volume_rows,
        invalid_ohlc_rows=invalid_ohlc_rows,
        nonpositive_price_rows=nonpositive_price_rows,
        largest_close_moves=close_moves,
        first_rows=sorted_raw.head(5).reset_index(drop=True),
        last_rows=sorted_raw.tail(5).reset_index(drop=True),
    )
