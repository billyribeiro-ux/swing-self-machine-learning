from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Protocol

import httpx
import pandas as pd

from swing_rsi.data.validation import normalize_ohlcv_columns, validate_ohlcv
from swing_rsi.settings import get_fmp_api_key, get_fmp_base_url


class FMPAPIError(RuntimeError):
    """Raised when FMP returns an unusable response."""


class HTTPGet(Protocol):
    def __call__(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> httpx.Response: ...


def _validate_iso_date(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc
    return value


def _extract_rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        error_value = next(
            (payload[key] for key in ("Error Message", "error", "message") if payload.get(key)),
            None,
        )
        if error_value is not None:
            raise FMPAPIError(f"FMP rejected the request: {error_value}")

        nested = next(
            (
                payload[key]
                for key in ("historical", "data")
                if key in payload and isinstance(payload[key], list)
            ),
            None,
        )
        if nested is None:
            raise FMPAPIError("FMP returned an unexpected JSON object")
        rows = nested
    else:
        raise FMPAPIError("FMP returned an unexpected JSON payload")

    if not rows:
        raise FMPAPIError("FMP returned no historical rows")
    if not all(isinstance(row, dict) for row in rows):
        raise FMPAPIError("FMP historical rows were not JSON objects")
    return rows


def _frame_from_rows(rows: list[dict[str, object]], symbol: str) -> pd.DataFrame:
    data = normalize_ohlcv_columns(pd.DataFrame(rows))
    if "Date" not in data.columns:
        raise FMPAPIError(f"FMP response for {symbol} did not contain a date field")

    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    if data["Date"].isna().any():
        raise FMPAPIError(f"FMP response for {symbol} contained invalid dates")

    keep = [
        column
        for column in ("Date", "Open", "High", "Low", "Close", "Adj Close", "Volume")
        if column in data.columns
    ]
    data = data[keep].set_index("Date")
    validated = validate_ohlcv(data)
    validated.attrs["provider"] = "fmp"
    validated.attrs["symbol"] = symbol.upper()
    return validated


def download_fmp_daily(
    ticker: str,
    start: str | None = None,
    end: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 30.0,
    http_get: HTTPGet = httpx.get,
) -> pd.DataFrame:
    """Download FMP end-of-day OHLCV using header authentication.

    The returned frame is chronological, validated, duplicate-free, and indexed by session date.
    Provider data remains subject to the repository's corporate-action and quality audit.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker cannot be blank")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    start_date = _validate_iso_date(start, "start")
    end_date = _validate_iso_date(end, "end")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start must be on or before end")

    key = (api_key or get_fmp_api_key()).strip()
    if not key:
        raise RuntimeError("FMP_API_KEY is empty")
    endpoint_root = (base_url or get_fmp_base_url()).rstrip("/")

    params: dict[str, str] = {"symbol": symbol}
    if start_date is not None:
        params["from"] = start_date
    if end_date is not None:
        params["to"] = end_date

    try:
        response = http_get(
            f"{endpoint_root}/historical-price-eod/full",
            params=params,
            headers={"apikey": key, "accept": "application/json"},
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise FMPAPIError(f"FMP network request failed: {exc}") from exc

    if response.status_code == 429:
        raise FMPAPIError("FMP rate limit reached; wait and retry")
    if response.status_code in {401, 403}:
        raise FMPAPIError("FMP authentication or plan access was rejected")
    if response.status_code >= 400:
        raise FMPAPIError(f"FMP request failed with HTTP {response.status_code}")

    try:
        payload: object = response.json()
    except ValueError as exc:
        raise FMPAPIError("FMP returned invalid JSON") from exc

    return _frame_from_rows(_extract_rows(payload), symbol)
