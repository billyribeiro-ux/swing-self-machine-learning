from __future__ import annotations

from collections.abc import Mapping

import httpx
import pandas as pd
import pytest

from swing_rsi.data.providers.fmp import FMPAPIError, download_fmp_daily


class FakeGet:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.url: str | None = None
        self.params: Mapping[str, str] | None = None
        self.headers: Mapping[str, str] | None = None
        self.timeout: float | None = None

    def __call__(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> httpx.Response:
        self.url = url
        self.params = params
        self.headers = headers
        self.timeout = timeout
        return self.response


def test_download_fmp_daily_authenticates_by_header_and_sorts_rows() -> None:
    fake_get = FakeGet(
        httpx.Response(
            200,
            json=[
                {
                    "symbol": "AAPL",
                    "date": "2024-01-03",
                    "open": 102.0,
                    "high": 105.0,
                    "low": 101.0,
                    "close": 104.0,
                    "adjClose": 104.0,
                    "volume": 1_200_000,
                },
                {
                    "symbol": "AAPL",
                    "date": "2024-01-02",
                    "open": 100.0,
                    "high": 103.0,
                    "low": 99.0,
                    "close": 102.0,
                    "adjClose": 102.0,
                    "volume": 1_000_000,
                },
            ],
        )
    )

    frame = download_fmp_daily(
        "aapl",
        start="2024-01-01",
        end="2024-01-31",
        api_key="temporary-test-key",
        base_url="https://example.test/stable",
        http_get=fake_get,
    )

    assert fake_get.url == "https://example.test/stable/historical-price-eod/full"
    assert fake_get.params == {"symbol": "AAPL", "from": "2024-01-01", "to": "2024-01-31"}
    assert fake_get.headers is not None
    assert fake_get.headers["apikey"] == "temporary-test-key"
    assert "apikey" not in fake_get.params
    assert frame.index.equals(pd.DatetimeIndex(["2024-01-02", "2024-01-03"], name="Date"))
    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    assert frame.attrs["provider"] == "fmp"
    assert frame.attrs["symbol"] == "AAPL"


def test_download_fmp_daily_accepts_legacy_historical_wrapper() -> None:
    fake_get = FakeGet(
        httpx.Response(
            200,
            json={
                "symbol": "SPY",
                "historical": [
                    {
                        "date": "2024-01-02",
                        "open": 470.0,
                        "high": 474.0,
                        "low": 469.0,
                        "close": 473.0,
                        "volume": 50_000_000,
                    }
                ],
            },
        )
    )

    frame = download_fmp_daily("SPY", api_key="key", http_get=fake_get)
    assert len(frame) == 1
    assert float(frame.iloc[0]["Close"]) == 473.0


def test_download_fmp_daily_rejects_api_error_without_exposing_key() -> None:
    fake_get = FakeGet(httpx.Response(200, json={"Error Message": "Invalid API KEY."}))

    with pytest.raises(FMPAPIError, match="Invalid API KEY") as exc_info:
        download_fmp_daily("AAPL", api_key="secret-value", http_get=fake_get)

    assert "secret-value" not in str(exc_info.value)


def test_download_fmp_daily_rejects_bad_date_range() -> None:
    with pytest.raises(ValueError, match="start must be on or before end"):
        download_fmp_daily(
            "AAPL",
            start="2024-02-01",
            end="2024-01-01",
            api_key="key",
        )
