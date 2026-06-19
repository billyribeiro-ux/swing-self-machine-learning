"""Market-data provider adapters."""

from swing_rsi.data.providers.fmp import FMPAPIError, download_fmp_daily

__all__ = ["FMPAPIError", "download_fmp_daily"]
