from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from numbers import Real

import pandas as pd

from swing_rsi.features.price import build_price_features
from swing_rsi.features.rsi import wilder_rsi
from swing_rsi.signals.rsi_reversal import RSIReversalRule, generate_rsi_reversal_signal


@dataclass(frozen=True)
class ScannerResult:
    date: str
    ticker: str
    signal_type: str
    model_version: str
    rule_id: str
    rule_parameters: str
    close: float
    rsi_value: float
    relative_volume_20: float | None
    close_position: float | None
    historical_trade_count: int | None
    historical_win_rate: float | None
    historical_mean_return: float | None
    research_score: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def scan_latest(
    frame: pd.DataFrame,
    ticker: str,
    rule: RSIReversalRule,
    model_version: str = "0.1.0",
    historical_stats: dict[str, object] | None = None,
) -> ScannerResult | None:
    features = build_price_features(frame)
    rsi = wilder_rsi(features["Close"], rule.length)
    signals = generate_rsi_reversal_signal(features, rule, rsi=rsi)
    if features.empty or not bool(signals.iloc[-1]):
        return None

    stats = historical_stats or {}

    def optional_float(name: str) -> float | None:
        value = stats.get(name)
        if not isinstance(value, Real):
            return None
        numeric = float(value)
        return None if math.isnan(numeric) else numeric

    def optional_int(name: str) -> int | None:
        value = stats.get(name)
        if not isinstance(value, Real):
            return None
        numeric = float(value)
        return None if math.isnan(numeric) else int(numeric)

    def frame_optional(column: str) -> float | None:
        if column not in features.columns:
            return None
        value = features[column].iloc[-1]
        if not isinstance(value, Real):
            return None
        numeric = float(value)
        return None if math.isnan(numeric) else numeric

    return ScannerResult(
        date=features.index[-1].date().isoformat(),
        ticker=ticker.upper(),
        signal_type="BULLISH_RSI_SWING_REVERSAL_CANDIDATE",
        model_version=model_version,
        rule_id=rule.rule_id,
        rule_parameters=json.dumps(rule.to_dict(), sort_keys=True),
        close=float(features["Close"].iloc[-1]),
        rsi_value=float(rsi.iloc[-1]),
        relative_volume_20=frame_optional("relative_volume_20"),
        close_position=frame_optional("close_position"),
        historical_trade_count=optional_int("trade_count"),
        historical_win_rate=optional_float("win_rate"),
        historical_mean_return=optional_float("mean_return"),
        research_score=optional_float("score"),
    )
