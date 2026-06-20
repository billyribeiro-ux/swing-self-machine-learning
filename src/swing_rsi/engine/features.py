from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal, cast

import numpy as np
import pandas as pd

from swing_rsi.data.validation import validate_ohlcv
from swing_rsi.engine.universe import UniverseConfig, UniverseSymbol, symbol_metadata
from swing_rsi.features.rsi import wilder_average, wilder_rsi

FeatureFamily = Literal[
    "returns_momentum",
    "trend_structure",
    "volatility_range",
    "volume_participation",
    "candle_geometry",
    "rsi_family",
    "technical_primitives",
    "market_relative",
    "sector_relative",
    "inverse_leveraged",
    "breadth",
    "relationship_graph",
    "regime",
]


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    family: FeatureFamily
    parameters: dict[str, object]
    required_columns: tuple[str, ...]
    lookback: int
    as_of_timing: str
    cross_sectional_required: bool
    benchmark_required: bool
    version: str = "1"


@dataclass(frozen=True)
class FeatureBuildResult:
    frame: pd.DataFrame
    specs: tuple[FeatureSpec, ...]
    manifest_hash: str
    feature_family_by_column: dict[str, str]


RETURN_WINDOWS = (1, 2, 3, 5, 10, 20, 40, 63, 126, 252)
TREND_WINDOWS = (10, 20, 50, 100, 200)
ATR_WINDOWS = (5, 14, 20)
RSI_LENGTHS = tuple(range(2, 51))
PRIMARY_BENCHMARKS = ("SPY", "QQQ", "IWM", "DIA")


def _spec(
    name: str,
    family: FeatureFamily,
    *,
    parameters: dict[str, object] | None = None,
    lookback: int = 1,
    required_columns: tuple[str, ...] = ("Open", "High", "Low", "Close", "Volume"),
    cross_sectional_required: bool = False,
    benchmark_required: bool = False,
) -> FeatureSpec:
    return FeatureSpec(
        name=name,
        family=family,
        parameters=parameters or {},
        required_columns=required_columns,
        lookback=lookback,
        as_of_timing="daily_close_known_after_session_close",
        cross_sectional_required=cross_sectional_required,
        benchmark_required=benchmark_required,
    )


def base_feature_registry() -> tuple[FeatureSpec, ...]:
    specs: list[FeatureSpec] = []
    for window in RETURN_WINDOWS:
        specs.extend(
            [
                _spec(
                    f"return_{window}",
                    "returns_momentum",
                    parameters={"window": window},
                    lookback=window,
                ),
                _spec(
                    f"log_return_{window}",
                    "returns_momentum",
                    parameters={"window": window},
                    lookback=window,
                ),
            ]
        )
    for window in TREND_WINDOWS:
        specs.extend(
            [
                _spec(
                    f"distance_sma_{window}",
                    "trend_structure",
                    parameters={"window": window},
                    lookback=window,
                ),
                _spec(
                    f"sma_{window}_slope_5",
                    "trend_structure",
                    parameters={"window": window, "slope": 5},
                    lookback=window + 5,
                ),
            ]
        )
    for window in ATR_WINDOWS:
        specs.append(
            _spec(
                f"atr_pct_{window}",
                "volatility_range",
                parameters={"window": window},
                lookback=window,
            )
        )
    for length in RSI_LENGTHS:
        specs.extend(
            [
                _spec(
                    f"rsi_{length}",
                    "rsi_family",
                    parameters={"length": length},
                    lookback=length,
                ),
                _spec(
                    f"rsi_{length}_slope_3",
                    "rsi_family",
                    parameters={"length": length, "slope": 3},
                    lookback=length + 3,
                ),
            ]
        )
    for name, family in {
        "relative_volume_20": "volume_participation",
        "volume_zscore_20": "volume_participation",
        "dollar_volume": "volume_participation",
        "body_pct": "candle_geometry",
        "upper_wick_pct": "candle_geometry",
        "lower_wick_pct": "candle_geometry",
        "close_position": "candle_geometry",
        "stochastic_14": "technical_primitives",
        "macd_12_26": "technical_primitives",
        "bollinger_z_20": "technical_primitives",
        "keltner_distance_20": "technical_primitives",
        "cci_20": "technical_primitives",
        "mfi_14": "technical_primitives",
        "breadth_advance_pct": "breadth",
        "market_regime_trend_score": "regime",
    }.items():
        specs.append(
            _spec(
                name,
                cast(FeatureFamily, family),
                cross_sectional_required=family == "breadth",
            )
        )
    return tuple(specs)


def feature_manifest_hash(specs: tuple[FeatureSpec, ...], columns: tuple[str, ...]) -> str:
    payload = json.dumps(
        {
            "specs": [asdict(spec) for spec in specs],
            "columns": columns,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0, np.nan)


def _rolling_percentile(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    return series.rolling(window=window, min_periods=min_periods).apply(
        lambda values: float(np.mean(values <= values[-1])),
        raw=True,
    )


def _true_range(data: pd.DataFrame) -> pd.Series:
    prior_close = data["Close"].shift(1)
    return pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - prior_close).abs(),
            (data["Low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _symbol_features(
    symbol: str, frame: pd.DataFrame, metadata: UniverseSymbol | None
) -> pd.DataFrame:
    data = validate_ohlcv(frame).copy()
    close = data["Close"]
    open_price = data["Open"]
    high = data["High"]
    low = data["Low"]
    volume = data["Volume"]
    prior_close = close.shift(1)
    true_range = _true_range(data)
    result = data[["Open", "High", "Low", "Close", "Volume"]].copy()

    for window in RETURN_WINDOWS:
        result[f"return_{window}"] = close.pct_change(window)
        result[f"log_return_{window}"] = np.log(close / close.shift(window))
    result["return_accel_5_20"] = result["return_5"] - result["return_20"]
    up = close > prior_close
    down = close < prior_close
    result["up_streak_5"] = up.rolling(5, min_periods=1).sum()
    result["down_streak_5"] = down.rolling(5, min_periods=1).sum()
    result["momentum_20_percentile_252"] = _rolling_percentile(result["return_20"], 252, 60)

    for window in (20, 63, 126, 252):
        prior_high = high.shift(1).rolling(window, min_periods=max(5, min(window, 20))).max()
        prior_low = low.shift(1).rolling(window, min_periods=max(5, min(window, 20))).min()
        result[f"distance_prior_high_{window}"] = _safe_divide(close, prior_high) - 1.0
        result[f"distance_prior_low_{window}"] = _safe_divide(close, prior_low) - 1.0
        result[f"range_position_{window}"] = _safe_divide(close - prior_low, prior_high - prior_low)

    for window in TREND_WINDOWS:
        sma = close.rolling(window, min_periods=window).mean()
        result[f"distance_sma_{window}"] = _safe_divide(close, sma) - 1.0
        result[f"sma_{window}_slope_5"] = sma.pct_change(5)
    result["trend_persistence_20"] = (
        (close > close.rolling(20, min_periods=20).mean()).rolling(20, min_periods=5).mean()
    )
    result["pullback_depth_20"] = (
        _safe_divide(close, high.shift(1).rolling(20, min_periods=20).max()) - 1.0
    )
    result["recovery_pct_20"] = _safe_divide(
        close - low.shift(1).rolling(20, min_periods=20).min(),
        high.shift(1).rolling(20, min_periods=20).max()
        - low.shift(1).rolling(20, min_periods=20).min(),
    )
    result["gap_pct"] = _safe_divide(open_price, prior_close) - 1.0
    result["support_proximity_20"] = (
        _safe_divide(
            close,
            low.shift(1).rolling(20, min_periods=20).min(),
        )
        - 1.0
    )
    result["resistance_proximity_20"] = (
        _safe_divide(
            close,
            high.shift(1).rolling(20, min_periods=20).max(),
        )
        - 1.0
    )

    for window in ATR_WINDOWS:
        atr = wilder_average(true_range, window)
        result[f"atr_{window}"] = atr
        result[f"atr_pct_{window}"] = _safe_divide(atr, close)
    returns_1 = close.pct_change()
    for window in (10, 20, 63):
        result[f"realized_vol_{window}"] = returns_1.rolling(window, min_periods=window).std()
    result["upside_vol_20"] = returns_1.where(returns_1 > 0).rolling(20, min_periods=5).std()
    result["downside_vol_20"] = returns_1.where(returns_1 < 0).rolling(20, min_periods=5).std()
    result["range_pct"] = _safe_divide(high - low, close)
    result["range_percentile_63"] = _rolling_percentile(result["range_pct"], 63, 20)
    result["volatility_compression_20_100"] = _safe_divide(
        result["realized_vol_20"], result["realized_vol_63"].rolling(100, min_periods=40).median()
    )
    result["overnight_gap_vol_20"] = result["gap_pct"].rolling(20, min_periods=20).std()

    prior_volume_mean = volume.shift(1).rolling(20, min_periods=10).mean()
    prior_volume_std = volume.shift(1).rolling(20, min_periods=10).std()
    result["relative_volume_20"] = _safe_divide(volume, prior_volume_mean)
    result["volume_zscore_20"] = _safe_divide(volume - prior_volume_mean, prior_volume_std)
    result["dollar_volume"] = close * volume
    result["volume_trend_20"] = volume.rolling(20, min_periods=20).mean().pct_change(5)
    result["up_volume_proxy_20"] = (
        volume.where(close >= prior_close, 0.0).rolling(20, min_periods=5).sum()
    )
    result["down_volume_proxy_20"] = (
        volume.where(close < prior_close, 0.0).rolling(20, min_periods=5).sum()
    )
    result["price_volume_agreement_5"] = np.sign(result["return_5"]) * np.sign(
        result["volume_trend_20"]
    )
    obv_step = np.sign(close.diff()).fillna(0.0) * volume
    result["obv_change_20"] = obv_step.cumsum().pct_change(20)
    result["volume_expansion_after_compression"] = (
        result["relative_volume_20"]
        / result["relative_volume_20"].shift(1).rolling(20, min_periods=10).median()
    )

    session_range = (high - low).replace(0, np.nan)
    body = (close - open_price).abs()
    result["body_pct"] = _safe_divide(body, session_range)
    result["upper_wick_pct"] = _safe_divide(
        high - pd.concat([open_price, close], axis=1).max(axis=1), session_range
    )
    result["lower_wick_pct"] = _safe_divide(
        pd.concat([open_price, close], axis=1).min(axis=1) - low, session_range
    )
    result["close_position"] = _safe_divide(close - low, session_range)
    result["inside_bar"] = ((high < high.shift(1)) & (low > low.shift(1))).astype(float)
    result["outside_bar"] = ((high > high.shift(1)) & (low < low.shift(1))).astype(float)
    result["expansion_bar"] = (
        result["range_pct"] > result["range_pct"].shift(1).rolling(20, min_periods=10).quantile(0.8)
    ).astype(float)
    result["lower_rejection_bar"] = (
        (result["lower_wick_pct"] > 0.45) & (result["close_position"] > 0.55)
    ).astype(float)

    rsi_columns: dict[str, pd.Series] = {}
    for length in RSI_LENGTHS:
        rsi = wilder_rsi(close, length)
        rsi_columns[f"rsi_{length}"] = rsi
        rsi_columns[f"rsi_{length}_slope_3"] = rsi.diff(3)
        rsi_columns[f"rsi_{length}_accel"] = rsi.diff(3).diff(3)
        rsi_low = rsi.shift(1).rolling(252, min_periods=60).quantile(0.2)
        rsi_high = rsi.shift(1).rolling(252, min_periods=60).quantile(0.8)
        rsi_columns[f"rsi_{length}_percentile_252"] = _rolling_percentile(rsi, 252, 60)
        rsi_columns[f"rsi_{length}_distance_low_zone"] = rsi - rsi_low
        rsi_columns[f"rsi_{length}_distance_high_zone"] = rsi - rsi_high
    result = pd.concat([result, pd.DataFrame(rsi_columns, index=data.index)], axis=1)

    result["roc_10"] = close.pct_change(10)
    low_14 = low.shift(1).rolling(14, min_periods=14).min()
    high_14 = high.shift(1).rolling(14, min_periods=14).max()
    result["stochastic_14"] = _safe_divide(close - low_14, high_14 - low_14)
    ema_12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema_26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    result["macd_12_26"] = _safe_divide(ema_12 - ema_26, close)
    sma_20 = close.rolling(20, min_periods=20).mean()
    std_20 = close.rolling(20, min_periods=20).std()
    result["bollinger_z_20"] = _safe_divide(close - sma_20, std_20)
    result["keltner_distance_20"] = _safe_divide(close - sma_20, result["atr_20"])
    typical = (high + low + close) / 3.0
    typical_mean = typical.rolling(20, min_periods=20).mean()
    mean_dev = (typical - typical_mean).abs().rolling(20, min_periods=20).mean()
    result["cci_20"] = _safe_divide(typical - typical_mean, 0.015 * mean_dev)
    money_flow = typical * volume
    positive_flow = (
        money_flow.where(typical > typical.shift(1), 0.0).rolling(14, min_periods=14).sum()
    )
    negative_flow = (
        money_flow.where(typical < typical.shift(1), 0.0).rolling(14, min_periods=14).sum()
    )
    money_ratio = _safe_divide(positive_flow, negative_flow)
    result["mfi_14"] = 100.0 - (100.0 / (1.0 + money_ratio))

    result["symbol"] = symbol
    result["role"] = metadata.role if metadata else "stock"
    result["sector"] = metadata.sector if metadata and metadata.sector else "unknown"
    result["sector_proxy"] = metadata.sector_proxy if metadata and metadata.sector_proxy else ""
    result["is_benchmark"] = float(bool(metadata.benchmark)) if metadata else 0.0
    return result.reset_index().rename(columns={"index": "Date"})


def _add_cross_sectional_features(panel: pd.DataFrame, universe: UniverseConfig) -> pd.DataFrame:
    data = panel.copy()
    for window in (5, 20, 63):
        column = f"return_{window}"
        if column in data.columns:
            data[f"relative_strength_rank_{window}"] = data.groupby("Date")[column].rank(pct=True)

    breadth = data.groupby("Date").agg(
        breadth_advance_pct=("return_1", lambda values: float((values > 0).mean())),
        breadth_up_volume_pct=("Volume", "sum"),
        breadth_above_sma_50_pct=("distance_sma_50", lambda values: float((values > 0).mean())),
        breadth_high_20_pct=("distance_prior_high_20", lambda values: float((values >= 0).mean())),
        breadth_low_20_pct=("distance_prior_low_20", lambda values: float((values <= 0).mean())),
        breadth_dispersion_20=("return_20", "std"),
        breadth_skew_20=("return_20", "skew"),
    )
    up_volume = (
        data.assign(_up_volume=data["Volume"].where(data["return_1"] > 0, 0.0))
        .groupby("Date")["_up_volume"]
        .sum()
    )
    total_volume = data.groupby("Date")["Volume"].sum().replace(0, np.nan)
    breadth["breadth_up_volume_pct"] = up_volume / total_volume
    data = data.merge(breadth.reset_index(), on="Date", how="left")

    pivot_returns = data.pivot(index="Date", columns="symbol", values="return_1")
    pivot_close = data.pivot(index="Date", columns="symbol", values="Close")
    for benchmark in PRIMARY_BENCHMARKS:
        if benchmark not in pivot_returns.columns:
            continue
        benchmark_return = pivot_returns[benchmark]
        for window in (5, 20):
            bench_window = pivot_close[benchmark].pct_change(window)
            data = data.merge(
                pd.DataFrame(
                    {
                        "Date": bench_window.index,
                        f"{benchmark.lower()}_return_{window}": bench_window,
                    }
                ).reset_index(drop=True),
                on="Date",
                how="left",
            )
            data[f"relative_return_vs_{benchmark.lower()}_{window}"] = (
                data[f"return_{window}"] - data[f"{benchmark.lower()}_return_{window}"]
            )
        benchmark_return_for_beta = benchmark_return
        benchmark_return_for_corr = benchmark_return
        benchmark_variance = benchmark_return_for_beta.rolling(63, min_periods=40).var()
        beta = pivot_returns.apply(
            lambda values, benchmark_values=benchmark_return_for_beta, variance=benchmark_variance: (
                values.rolling(63, min_periods=40).cov(benchmark_values) / variance
            )
        )
        corr = pivot_returns.apply(
            lambda values, benchmark_values=benchmark_return_for_corr: values.rolling(
                63, min_periods=40
            ).corr(benchmark_values)
        )
        for symbol in pivot_returns.columns:
            mask = data["symbol"] == symbol
            if not bool(mask.any()):
                continue
            data.loc[mask, f"rolling_beta_vs_{benchmark.lower()}_63"] = data.loc[mask, "Date"].map(
                beta[symbol]
            )
            data.loc[mask, f"rolling_corr_vs_{benchmark.lower()}_63"] = data.loc[mask, "Date"].map(
                corr[symbol]
            )
            data.loc[mask, f"residual_return_vs_{benchmark.lower()}_1"] = (
                data.loc[mask, "return_1"]
                - data.loc[mask, f"rolling_beta_vs_{benchmark.lower()}_63"]
                * data.loc[mask, f"{benchmark.lower()}_return_5"].fillna(0.0)
                / 5.0
            )

    sector_returns = {
        row.symbol: row.sector_proxy
        for row in universe.symbols
        if row.enabled and row.sector_proxy and row.sector_proxy in pivot_close.columns
    }
    for symbol, proxy in sector_returns.items():
        mask = data["symbol"] == symbol
        proxy_return_20 = pivot_close[proxy].pct_change(20)
        data.loc[mask, "sector_return_20"] = data.loc[mask, "Date"].map(proxy_return_20)
        data.loc[mask, "relative_return_vs_sector_20"] = (
            data.loc[mask, "return_20"] - data.loc[mask, "sector_return_20"]
        )
        proxy_trend = data.loc[data["symbol"] == proxy, ["Date", "distance_sma_50"]].set_index(
            "Date"
        )["distance_sma_50"]
        data.loc[mask, "sector_trend_agreement"] = np.sign(
            data.loc[mask, "distance_sma_50"]
        ) * np.sign(data.loc[mask, "Date"].map(proxy_trend))

    for source, related_symbols in universe.relationships.items():
        if source not in pivot_returns.columns:
            continue
        source_return = pivot_returns[source]
        for related in related_symbols:
            if related not in pivot_returns.columns:
                continue
            related_return = pivot_returns[related]
            relationship = pd.DataFrame(
                {
                    "Date": source_return.index,
                    f"relationship_corr_{source.lower()}_{related.lower()}_63": source_return.rolling(
                        63, min_periods=40
                    ).corr(related_return),
                    f"relationship_divergence_{source.lower()}_{related.lower()}_5": source_return.rolling(
                        5, min_periods=5
                    ).sum()
                    + related_return.rolling(5, min_periods=5).sum(),
                    f"relationship_lead_lag_{source.lower()}_{related.lower()}_5": source_return.shift(
                        1
                    )
                    .rolling(5, min_periods=5)
                    .corr(related_return),
                }
            ).reset_index(drop=True)
            data = data.merge(relationship, on="Date", how="left")

    if "SPY" in pivot_close.columns:
        spy_trend = pivot_close["SPY"].pct_change(63)
        spy_vol = pivot_returns["SPY"].rolling(20, min_periods=20).std()
        regime = pd.DataFrame(
            {
                "Date": spy_trend.index,
                "market_regime_trend_score": spy_trend,
                "market_regime_volatility_score": spy_vol,
            }
        ).reset_index(drop=True)
        data = data.merge(regime, on="Date", how="left")
    else:
        data["market_regime_trend_score"] = data.groupby("Date")["return_20"].transform("mean")
        data["market_regime_volatility_score"] = data.groupby("Date")["return_1"].transform("std")
    data["market_regime_label"] = np.select(
        [
            (data["market_regime_trend_score"] > 0)
            & (
                data["market_regime_volatility_score"]
                <= data["market_regime_volatility_score"].median()
            ),
            (data["market_regime_trend_score"] > 0),
            (data["market_regime_trend_score"] <= 0)
            & (
                data["market_regime_volatility_score"]
                > data["market_regime_volatility_score"].median()
            ),
        ],
        ["uptrend_low_vol", "uptrend_high_vol", "downtrend_high_vol"],
        default="mixed",
    )
    return data.sort_values(["Date", "symbol"]).reset_index(drop=True)


def _family_map(columns: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for column in columns:
        if column.startswith(("return_", "log_return_", "momentum_", "up_streak", "down_streak")):
            mapping[column] = "returns_momentum"
        elif column.startswith(
            (
                "distance_sma",
                "sma_",
                "trend_",
                "pullback",
                "recovery",
                "gap_",
                "support",
                "resistance",
                "range_position",
                "distance_prior",
            )
        ):
            mapping[column] = "trend_structure"
        elif column.startswith(
            (
                "atr_",
                "atr_pct",
                "realized_vol",
                "upside_vol",
                "downside_vol",
                "range_pct",
                "range_percentile",
                "volatility",
                "overnight",
            )
        ):
            mapping[column] = "volatility_range"
        elif "volume" in column or column.startswith(("obv", "price_volume")):
            mapping[column] = "volume_participation"
        elif column.startswith(
            (
                "body",
                "upper_wick",
                "lower_wick",
                "close_position",
                "inside_bar",
                "outside_bar",
                "expansion_bar",
                "lower_rejection",
            )
        ):
            mapping[column] = "candle_geometry"
        elif column.startswith("rsi_"):
            mapping[column] = "rsi_family"
        elif column.startswith(
            ("roc_", "stochastic", "macd", "bollinger", "keltner", "cci", "mfi")
        ):
            mapping[column] = "technical_primitives"
        elif column.startswith(
            (
                "relative_return_vs_spy",
                "relative_return_vs_qqq",
                "relative_return_vs_iwm",
                "relative_return_vs_dia",
                "rolling_beta",
                "rolling_corr",
                "residual_return",
            )
        ):
            mapping[column] = "market_relative"
        elif "sector" in column:
            mapping[column] = "sector_relative"
        elif column.startswith("relationship_"):
            mapping[column] = "relationship_graph"
        elif column.startswith("breadth_"):
            mapping[column] = "breadth"
        elif column.startswith("market_regime"):
            mapping[column] = "regime"
    return mapping


def build_feature_panel(
    frames: dict[str, pd.DataFrame],
    universe: UniverseConfig,
) -> FeatureBuildResult:
    metadata = symbol_metadata(universe)
    rows: list[pd.DataFrame] = []
    for symbol in universe.enabled_symbols:
        frame = frames.get(symbol)
        if frame is None or frame.empty:
            continue
        rows.append(_symbol_features(symbol, frame, metadata.get(symbol)))
    if not rows:
        raise ValueError("No enabled universe symbols have usable OHLCV data")

    panel = (
        pd.concat(rows, ignore_index=True).sort_values(["Date", "symbol"]).reset_index(drop=True)
    )
    panel = _add_cross_sectional_features(panel, universe)
    feature_columns = [
        column
        for column in panel.columns
        if column
        not in {
            "Date",
            "symbol",
            "role",
            "sector",
            "sector_proxy",
            "market_regime_label",
        }
        and not str(column).startswith("label_")
    ]
    specs = base_feature_registry()
    family_by_column = _family_map(feature_columns)
    manifest = feature_manifest_hash(specs, tuple(sorted(feature_columns)))
    return FeatureBuildResult(
        frame=panel,
        specs=specs,
        manifest_hash=manifest,
        feature_family_by_column=family_by_column,
    )


def numeric_feature_columns(frame: pd.DataFrame) -> list[str]:
    blocked = {"Date", "symbol", "role", "sector", "sector_proxy", "market_regime_label"}
    columns: list[str] = []
    for column in frame.columns:
        name = str(column)
        if name in blocked or name.startswith("label_"):
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            columns.append(name)
    return columns


def reject_label_columns(columns: list[str]) -> None:
    labels = [column for column in columns if str(column).startswith("label_")]
    if labels:
        raise ValueError(f"Label columns cannot enter the feature matrix: {labels[:5]}")
