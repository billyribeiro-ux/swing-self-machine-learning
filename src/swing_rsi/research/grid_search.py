from __future__ import annotations

import math
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from numbers import Real

import pandas as pd

from swing_rsi.backtest.engine import backtest_fixed_horizon
from swing_rsi.backtest.metrics import summarize_trades
from swing_rsi.features.price import build_price_features
from swing_rsi.features.rsi import wilder_rsi
from swing_rsi.signals.rsi_reversal import RSIReversalRule, generate_rsi_reversal_signal


@dataclass(frozen=True)
class RSIParameterGrid:
    lengths: tuple[int, ...]
    lower_levels: tuple[float, ...]
    slope_windows: tuple[int, ...] = (1, 2, 3, 5)
    trigger_modes: tuple[str, ...] = ("cross_above",)
    trend_filters: tuple[str, ...] = ("none",)
    relative_volume_minimums: tuple[float | None, ...] = (None,)
    close_position_minimums: tuple[float | None, ...] = (None,)

    def rules(self) -> Iterator[RSIReversalRule]:
        for length in self.lengths:
            for lower_level in self.lower_levels:
                for slope_window in self.slope_windows:
                    for trigger_mode in self.trigger_modes:
                        for trend_filter in self.trend_filters:
                            for relative_volume in self.relative_volume_minimums:
                                for close_position in self.close_position_minimums:
                                    yield RSIReversalRule(
                                        length=length,
                                        lower_level=lower_level,
                                        slope_window=slope_window,
                                        trigger_mode=trigger_mode,  # type: ignore[arg-type]
                                        trend_filter=trend_filter,  # type: ignore[arg-type]
                                        min_relative_volume=relative_volume,
                                        min_close_position=close_position,
                                    )


def run_grid_search(
    frame: pd.DataFrame,
    grid: RSIParameterGrid,
    holding_period: int,
    round_trip_cost_bps: float = 5.0,
    minimum_trades: int = 30,
) -> pd.DataFrame:
    features = build_price_features(frame)
    rsi_cache = {length: wilder_rsi(features["Close"], length) for length in grid.lengths}
    rows: list[dict[str, object]] = []

    for rule in grid.rules():
        signals = generate_rsi_reversal_signal(features, rule, rsi=rsi_cache[rule.length])
        trades = backtest_fixed_horizon(
            features,
            signals,
            holding_period=holding_period,
            round_trip_cost_bps=round_trip_cost_bps,
        )
        metrics = summarize_trades(trades, minimum_trades=minimum_trades)
        rows.append(
            {
                "rule_id": rule.rule_id,
                **rule.to_dict(),
                "holding_period": holding_period,
                "round_trip_cost_bps": round_trip_cost_bps,
                **metrics,
            }
        )

    results = pd.DataFrame(rows)
    if results.empty:
        return results
    return results.sort_values(
        ["eligible", "score", "trade_count", "mean_return"],
        ascending=[False, False, False, False],
        na_position="last",
    ).reset_index(drop=True)


def rule_from_result(row: pd.Series) -> RSIReversalRule:
    def optional_float(value: object) -> float | None:
        if not isinstance(value, Real):
            return None
        numeric = float(value)
        return None if math.isnan(numeric) else numeric

    return RSIReversalRule(
        length=int(row["length"]),
        lower_level=float(row["lower_level"]),
        slope_window=int(row["slope_window"]),
        trigger_mode=str(row["trigger_mode"]),  # type: ignore[arg-type]
        trend_filter=str(row["trend_filter"]),  # type: ignore[arg-type]
        min_relative_volume=optional_float(row.get("min_relative_volume")),
        min_close_position=optional_float(row.get("min_close_position")),
    )


def default_research_grid() -> RSIParameterGrid:
    return RSIParameterGrid(
        lengths=tuple(range(2, 31)),
        lower_levels=tuple(float(value) for value in range(10, 56, 5)),
        slope_windows=(1, 2, 3, 5, 10),
        trigger_modes=("cross_above", "turn_up_below", "recent_reclaim"),
        trend_filters=("none", "above_sma_50", "above_sma_200", "sma_50_above_200"),
    )


def compact_demo_grid() -> RSIParameterGrid:
    return RSIParameterGrid(
        lengths=(2, 3, 5, 8, 14, 21),
        lower_levels=(20.0, 25.0, 30.0, 35.0, 40.0, 45.0),
        slope_windows=(1, 2, 3),
        trigger_modes=("cross_above", "turn_up_below"),
        trend_filters=("none", "above_sma_200"),
    )


def control_rules() -> Iterable[RSIReversalRule]:
    yield RSIReversalRule(length=14, lower_level=30.0, slope_window=1)
