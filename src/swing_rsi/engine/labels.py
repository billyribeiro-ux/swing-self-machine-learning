from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from swing_rsi.data.validation import validate_ohlcv
from swing_rsi.engine.features import reject_label_columns

DEFAULT_HORIZONS = (3, 5, 10, 20, 40)


@dataclass(frozen=True)
class LabelConfig:
    horizons: tuple[int, ...] = DEFAULT_HORIZONS
    target_atr_multiple: float = 2.0
    stop_atr_multiple: float = 1.0
    atr_column: str = "atr_14"


def _atr(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    data = validate_ohlcv(frame)
    prior_close = data["Close"].shift(1)
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - prior_close).abs(),
            (data["Low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def _first_touch(
    highs: pd.Series,
    lows: pd.Series,
    target: float,
    stop: float,
    *,
    bullish: bool,
) -> tuple[bool, bool, int | None, int | None]:
    target_hit_at: int | None = None
    stop_hit_at: int | None = None
    for offset, (_, high, low) in enumerate(zip(highs.index, highs, lows, strict=True), start=1):
        if bullish:
            target_hit = float(high) >= target
            stop_hit = float(low) <= stop
        else:
            target_hit = float(low) <= target
            stop_hit = float(high) >= stop
        if target_hit and target_hit_at is None:
            target_hit_at = offset
        if stop_hit and stop_hit_at is None:
            stop_hit_at = offset
        if target_hit_at is not None or stop_hit_at is not None:
            break
    return (
        target_hit_at is not None and (stop_hit_at is None or target_hit_at < stop_hit_at),
        stop_hit_at is not None and (target_hit_at is None or stop_hit_at <= target_hit_at),
        target_hit_at,
        stop_hit_at,
    )


def build_symbol_labels(frame: pd.DataFrame, config: LabelConfig | None = None) -> pd.DataFrame:
    config = config or LabelConfig()
    data = validate_ohlcv(frame)
    atr = _atr(data)
    label_columns: dict[str, object] = {}

    for horizon in config.horizons:
        entry = data["Open"].shift(-1)
        exit_close = data["Close"].shift(-horizon)
        high_future = pd.concat(
            [data["High"].shift(-offset) for offset in range(1, horizon + 1)],
            axis=1,
        )
        low_future = pd.concat(
            [data["Low"].shift(-offset) for offset in range(1, horizon + 1)],
            axis=1,
        )
        future_high = high_future.max(axis=1)
        future_low = low_future.min(axis=1)

        bull_return = (exit_close / entry) - 1.0
        bear_return = (entry / exit_close) - 1.0
        label_columns[f"label_bull_forward_return_{horizon}"] = bull_return
        label_columns[f"label_bear_forward_return_{horizon}"] = bear_return
        label_columns[f"label_bull_positive_return_{horizon}"] = (bull_return > 0).astype(float)
        label_columns[f"label_bear_positive_return_{horizon}"] = (bear_return > 0).astype(float)
        label_columns[f"label_bull_mfe_{horizon}"] = (future_high / entry) - 1.0
        label_columns[f"label_bull_mae_{horizon}"] = (future_low / entry) - 1.0
        label_columns[f"label_bear_mfe_{horizon}"] = (entry / future_low) - 1.0
        label_columns[f"label_bear_mae_{horizon}"] = (entry / future_high) - 1.0
        label_columns[f"label_bull_continuation_{horizon}"] = (
            bull_return > data["Close"].pct_change(horizon).rolling(252, min_periods=60).median()
        ).astype(float)
        label_columns[f"label_bear_continuation_{horizon}"] = (
            bear_return > (-data["Close"].pct_change(horizon)).rolling(252, min_periods=60).median()
        ).astype(float)
        label_columns[f"label_bull_reversal_{horizon}"] = (
            (data["Close"].pct_change(5) < 0) & (bull_return > 0)
        ).astype(float)
        label_columns[f"label_bear_reversal_{horizon}"] = (
            (data["Close"].pct_change(5) > 0) & (bear_return > 0)
        ).astype(float)

        target_distance = atr * config.target_atr_multiple
        stop_distance = atr * config.stop_atr_multiple
        bull_target = entry + target_distance
        bull_stop = entry - stop_distance
        bear_target = entry - target_distance
        bear_stop = entry + stop_distance
        bull_target_before_stop: list[float] = []
        bull_stop_before_target: list[float] = []
        bear_target_before_stop: list[float] = []
        bear_stop_before_target: list[float] = []
        bull_time_to_target: list[float] = []
        bull_time_to_stop: list[float] = []
        bear_time_to_target: list[float] = []
        bear_time_to_stop: list[float] = []
        for position in range(len(data)):
            if position + horizon >= len(data) or position + 1 >= len(data):
                bull_target_before_stop.append(np.nan)
                bull_stop_before_target.append(np.nan)
                bear_target_before_stop.append(np.nan)
                bear_stop_before_target.append(np.nan)
                bull_time_to_target.append(np.nan)
                bull_time_to_stop.append(np.nan)
                bear_time_to_target.append(np.nan)
                bear_time_to_stop.append(np.nan)
                continue
            high_slice = data["High"].iloc[position + 1 : position + horizon + 1]
            low_slice = data["Low"].iloc[position + 1 : position + horizon + 1]
            bull = _first_touch(
                high_slice,
                low_slice,
                float(bull_target.iloc[position]),
                float(bull_stop.iloc[position]),
                bullish=True,
            )
            bear = _first_touch(
                high_slice,
                low_slice,
                float(bear_target.iloc[position]),
                float(bear_stop.iloc[position]),
                bullish=False,
            )
            bull_target_before_stop.append(float(bull[0]))
            bull_stop_before_target.append(float(bull[1]))
            bull_time_to_target.append(float(bull[2]) if bull[2] is not None else np.nan)
            bull_time_to_stop.append(float(bull[3]) if bull[3] is not None else np.nan)
            bear_target_before_stop.append(float(bear[0]))
            bear_stop_before_target.append(float(bear[1]))
            bear_time_to_target.append(float(bear[2]) if bear[2] is not None else np.nan)
            bear_time_to_stop.append(float(bear[3]) if bear[3] is not None else np.nan)

        label_columns[f"label_bull_target_before_stop_{horizon}"] = bull_target_before_stop
        label_columns[f"label_bull_stop_before_target_{horizon}"] = bull_stop_before_target
        label_columns[f"label_bear_target_before_stop_{horizon}"] = bear_target_before_stop
        label_columns[f"label_bear_stop_before_target_{horizon}"] = bear_stop_before_target
        label_columns[f"label_bull_time_to_target_{horizon}"] = bull_time_to_target
        label_columns[f"label_bull_time_to_stop_{horizon}"] = bull_time_to_stop
        label_columns[f"label_bear_time_to_target_{horizon}"] = bear_time_to_target
        label_columns[f"label_bear_time_to_stop_{horizon}"] = bear_time_to_stop
        label_columns[f"label_end_date_{horizon}"] = data.index.to_series().shift(-horizon).values

    labels = pd.DataFrame(label_columns, index=data.index)
    labels.index.name = "Date"
    return labels


def build_label_panel(
    frames: dict[str, pd.DataFrame],
    config: LabelConfig | None = None,
) -> pd.DataFrame:
    config = config or LabelConfig()
    rows: list[pd.DataFrame] = []
    for symbol, frame in sorted(frames.items()):
        labels = build_symbol_labels(frame, config)
        symbol_column = pd.Series(symbol, index=labels.index, name="symbol")
        rows.append(pd.concat([labels, symbol_column], axis=1).reset_index())
    if not rows:
        raise ValueError("No OHLCV frames supplied for labels")
    panel = (
        pd.concat(rows, ignore_index=True).sort_values(["Date", "symbol"]).reset_index(drop=True)
    )
    derived_columns: dict[str, pd.Series] = {}
    for horizon in config.horizons:
        for direction in ("bull", "bear"):
            ret = f"label_{direction}_forward_return_{horizon}"
            rank = f"label_{direction}_return_rank_vs_universe_{horizon}"
            utility = f"label_{direction}_risk_adjusted_utility_{horizon}"
            mae = f"label_{direction}_mae_{horizon}"
            derived_columns[rank] = panel.groupby("Date")[ret].rank(pct=True)
            derived_columns[utility] = panel[ret] / panel[mae].abs().replace(0, np.nan)
    if derived_columns:
        panel = pd.concat([panel, pd.DataFrame(derived_columns, index=panel.index)], axis=1)
    return panel.copy()


def merge_features_and_labels(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    reject_label_columns(
        [column for column in features.columns if str(column).startswith("label_")]
    )
    return features.merge(labels, on=["Date", "symbol"], how="inner", validate="one_to_one")
