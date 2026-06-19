from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

import pandas as pd

from swing_rsi.features.rsi import wilder_rsi

TriggerMode = Literal["cross_above", "turn_up_below", "recent_reclaim"]
TrendFilter = Literal["none", "above_sma_50", "above_sma_200", "sma_50_above_200"]


@dataclass(frozen=True)
class RSIReversalRule:
    length: int
    lower_level: float
    slope_window: int = 1
    trigger_mode: TriggerMode = "cross_above"
    trend_filter: TrendFilter = "none"
    min_relative_volume: float | None = None
    min_close_position: float | None = None

    def __post_init__(self) -> None:
        if self.length < 2:
            raise ValueError("RSI length must be at least 2")
        if not 0.0 < self.lower_level < 100.0:
            raise ValueError("Lower level must be between 0 and 100")
        if self.slope_window < 1:
            raise ValueError("Slope window must be positive")
        if self.min_relative_volume is not None and self.min_relative_volume < 0:
            raise ValueError("Minimum relative volume cannot be negative")
        if self.min_close_position is not None and not 0 <= self.min_close_position <= 1:
            raise ValueError("Minimum close position must be between 0 and 1")

    @property
    def rule_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def generate_rsi_reversal_signal(
    frame: pd.DataFrame,
    rule: RSIReversalRule,
    rsi: pd.Series | None = None,
) -> pd.Series:
    """Generate a close-known bullish RSI reversal candidate without future data."""
    required = {"Close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing signal columns: {sorted(missing)}")

    oscillator = wilder_rsi(frame["Close"], rule.length) if rsi is None else rsi
    slope = oscillator - oscillator.shift(rule.slope_window)

    if rule.trigger_mode == "cross_above":
        trigger = (oscillator.shift(1) <= rule.lower_level) & (oscillator > rule.lower_level)
    elif rule.trigger_mode == "turn_up_below":
        trigger = (oscillator <= rule.lower_level) & (slope > 0)
    elif rule.trigger_mode == "recent_reclaim":
        recently_below = pd.concat(
            [(oscillator.shift(offset) <= rule.lower_level) for offset in (1, 2, 3)], axis=1
        ).any(axis=1)
        trigger = recently_below & (oscillator > rule.lower_level) & (slope > 0)
    else:  # pragma: no cover - Literal and dataclass validation protect this
        raise ValueError(f"Unsupported trigger mode: {rule.trigger_mode}")

    signal = trigger & (slope > 0)

    if rule.trend_filter == "above_sma_50":
        signal &= frame["Close"] > frame["sma_50"]
    elif rule.trend_filter == "above_sma_200":
        signal &= frame["Close"] > frame["sma_200"]
    elif rule.trend_filter == "sma_50_above_200":
        signal &= frame["sma_50"] > frame["sma_200"]
    elif rule.trend_filter != "none":  # pragma: no cover
        raise ValueError(f"Unsupported trend filter: {rule.trend_filter}")

    if rule.min_relative_volume is not None:
        signal &= frame["relative_volume_20"] >= rule.min_relative_volume
    if rule.min_close_position is not None:
        signal &= frame["close_position"] >= rule.min_close_position

    signal = signal.fillna(False).astype(bool)
    signal.name = f"signal_{rule.rule_id}"
    return signal
