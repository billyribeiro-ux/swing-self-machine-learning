from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

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
    regime_cache_report: RegimeKMeansCacheReport | None = None


RETURN_WINDOWS = (1, 2, 3, 5, 10, 20, 40, 63, 126, 252)
TREND_WINDOWS = (10, 20, 50, 100, 200)
ATR_WINDOWS = (5, 14, 20)
RSI_LENGTHS = tuple(range(2, 51))
PRIMARY_BENCHMARKS = ("SPY", "QQQ", "IWM", "DIA")
REGIME_KMEANS_INPUT_COLUMNS = (
    "market_regime_trend_score",
    "market_regime_volatility_score",
    "breadth_advance_pct",
    "breadth_dispersion_20",
)
REGIME_KMEANS_OUTPUT_COLUMN = "market_regime_cluster_expanding"
REGIME_KMEANS_MINIMUM_ROWS = 126
REGIME_KMEANS_N_CLUSTERS = 3
REGIME_KMEANS_RANDOM_STATE = 42
REGIME_KMEANS_N_INIT = 10
REGIME_KMEANS_CACHE_SCHEMA_VERSION = "expanding_kmeans_regime_cache_v1"
REGIME_KMEANS_CACHE_STATUS_SCHEMA_VERSION = "expanding_kmeans_regime_cache_status_v1"
REGIME_KMEANS_FEATURE_BUILDER_VERSION = "features.py:_expanding_kmeans_regime:v1"
REGIME_KMEANS_DATE_ORDERING = "market_daily_rows_as_received_after_groupby_date_reset_index"
REGIME_KMEANS_PREPROCESSING_CONFIG = {
    "scaler": "none",
    "infinity_policy": "replace_positive_and_negative_infinity_with_nan",
    "missing_value_policy": "expanding_history_median_then_zero",
    "date_label_policy": "fit_expanding_prefix_and_take_current_date_label",
}


@dataclass(frozen=True)
class RegimeKMeansCacheConfig:
    cache_dir: Path
    universe_snapshot_id: str
    force_rebuild: bool = False
    feature_builder_version: str = REGIME_KMEANS_FEATURE_BUILDER_VERSION


@dataclass(frozen=True)
class RegimeKMeansCacheReport:
    status: str
    reason: str
    cache_path: Path | None
    cached_dates_reused: int
    new_dates_computed: int
    kmeans_fits_avoided: int
    kmeans_fits_performed: int
    regime_runtime_seconds: float
    estimated_speedup: float | None
    cache_write_succeeded: bool
    cache_write_error: str | None = None


@dataclass(frozen=True)
class _RegimeKMeansComputation:
    labels: pd.Series
    kmeans_fits: int


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


def _lookback_from_name(name: str) -> int:
    values = [int(value) for value in re.findall(r"_(\d+)", name)]
    return max(values) if values else 1


def feature_specs_for_columns(
    columns: list[str], family_by_column: dict[str, str]
) -> tuple[FeatureSpec, ...]:
    base = {spec.name: spec for spec in base_feature_registry()}
    specs: list[FeatureSpec] = []
    for column in sorted(columns):
        if column in base:
            specs.append(base[column])
            continue
        family = cast(FeatureFamily, family_by_column.get(column, "technical_primitives"))
        specs.append(
            _spec(
                column,
                family,
                parameters={"generated_from": "bounded_autonomous_feature_builder"},
                lookback=_lookback_from_name(column),
                cross_sectional_required=family
                in {
                    "breadth",
                    "market_relative",
                    "sector_relative",
                    "inverse_leveraged",
                    "relationship_graph",
                    "regime",
                },
                benchmark_required=family
                in {"market_relative", "inverse_leveraged", "relationship_graph", "regime"},
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


def _safe_pct_change(series: pd.Series, periods: int, *, epsilon: float = 1e-12) -> pd.Series:
    prior = series.shift(periods)
    safe_prior = prior.where(prior.abs() > epsilon)
    return _safe_divide(series - prior, safe_prior)


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


def _gaussian_mutual_information(correlation: pd.Series) -> pd.Series:
    clipped = correlation.clip(lower=-0.999, upper=0.999)
    values = -0.5 * np.log(1.0 - clipped.pow(2))
    return pd.Series(values, index=correlation.index)


def _regime_kmeans_parameters() -> dict[str, object]:
    return {
        "n_clusters": REGIME_KMEANS_N_CLUSTERS,
        "random_state": REGIME_KMEANS_RANDOM_STATE,
        "n_init": REGIME_KMEANS_N_INIT,
    }


def _regime_cache_path(config: RegimeKMeansCacheConfig) -> Path:
    safe_snapshot = re.sub(r"[^A-Za-z0-9_.-]+", "_", config.universe_snapshot_id)
    return config.cache_dir / f"{safe_snapshot}_{REGIME_KMEANS_CACHE_SCHEMA_VERSION}.json"


def _regime_cache_status_path(config: RegimeKMeansCacheConfig) -> Path:
    safe_snapshot = re.sub(r"[^A-Za-z0-9_.-]+", "_", config.universe_snapshot_id)
    return config.cache_dir / f"{safe_snapshot}_{REGIME_KMEANS_CACHE_STATUS_SCHEMA_VERSION}.json"


def _jsonable_cache_value(value: object) -> object:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).date().isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if math.isnan(number):
            return None
        if math.isinf(number):
            return "Infinity" if number > 0 else "-Infinity"
        return number
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    return value


def _hash_records(records: list[dict[str, object]]) -> str:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _regime_input_records(market_frame: pd.DataFrame) -> list[dict[str, object]]:
    input_frame = market_frame[["Date", *REGIME_KMEANS_INPUT_COLUMNS]].copy()
    input_frame["Date"] = pd.to_datetime(input_frame["Date"]).dt.date.astype(str)
    records: list[dict[str, object]] = []
    for raw in input_frame.to_dict(orient="records"):
        records.append({str(key): _jsonable_cache_value(value) for key, value in raw.items()})
    return records


def _regime_input_hash(market_frame: pd.DataFrame) -> str:
    return _hash_records(_regime_input_records(market_frame))


def _regime_output_frame(labels: pd.Series, market_frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(market_frame["Date"]).dt.date.astype(str),
            REGIME_KMEANS_OUTPUT_COLUMN: labels,
        },
        index=market_frame.index,
    )


def _regime_output_records(
    labels: pd.Series, market_frame: pd.DataFrame
) -> list[dict[str, object]]:
    output = _regime_output_frame(labels, market_frame)
    records: list[dict[str, object]] = []
    for raw in output.to_dict(orient="records"):
        records.append({str(key): _jsonable_cache_value(value) for key, value in raw.items()})
    return records


def _regime_output_hash(labels: pd.Series, market_frame: pd.DataFrame) -> str:
    return _hash_records(_regime_output_records(labels, market_frame))


def _market_dates(market_frame: pd.DataFrame) -> list[str]:
    return pd.to_datetime(market_frame["Date"]).dt.date.astype(str).tolist()


def _series_from_cache_records(records: list[dict[str, object]], index: pd.Index) -> pd.Series:
    values = [record.get(REGIME_KMEANS_OUTPUT_COLUMN) for record in records]
    labels = [
        math.nan if value is None else float(cast(float | int | str, value)) for value in values
    ]
    return pd.Series(labels, index=index, name=REGIME_KMEANS_OUTPUT_COLUMN)


def _write_regime_cache_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _regime_cache_payload(
    *,
    config: RegimeKMeansCacheConfig,
    market_frame: pd.DataFrame,
    labels: pd.Series,
    symbols_covered: tuple[str, ...],
    creation_timestamp_utc: str | None,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    input_hash = _regime_input_hash(market_frame)
    dates = _market_dates(market_frame)
    records = _regime_output_records(labels, market_frame)
    return {
        "schema_version": REGIME_KMEANS_CACHE_SCHEMA_VERSION,
        "universe_snapshot_id": config.universe_snapshot_id,
        "regime_input_columns": list(REGIME_KMEANS_INPUT_COLUMNS),
        "kmeans_parameters": _regime_kmeans_parameters(),
        "random_seed": REGIME_KMEANS_RANDOM_STATE,
        "scaler_preprocessing_configuration": REGIME_KMEANS_PREPROCESSING_CONFIG,
        "minimum_sample_requirement": REGIME_KMEANS_MINIMUM_ROWS,
        "feature_builder_code_version": config.feature_builder_version,
        "date_ordering": REGIME_KMEANS_DATE_ORDERING,
        "input_prefix_hash": input_hash,
        "full_input_hash": input_hash,
        "dates_covered": dates,
        "last_cached_date": dates[-1] if dates else None,
        "row_count": len(dates),
        "symbols_covered": list(symbols_covered),
        "output_column_names": ["Date", REGIME_KMEANS_OUTPUT_COLUMN],
        "output_dataframe_hash": _regime_output_hash(labels, market_frame),
        "creation_timestamp_utc": creation_timestamp_utc or now,
        "update_timestamp_utc": now,
        "cache_validity_status": "VALID",
        "records": records,
    }


def _regime_cache_status_payload(
    *,
    config: RegimeKMeansCacheConfig,
    market_frame: pd.DataFrame,
    report: RegimeKMeansCacheReport,
    symbols_covered: tuple[str, ...],
    feature_manifest_hash: str | None = None,
) -> dict[str, object]:
    dates = _market_dates(market_frame)
    timestamp = datetime.now(UTC).isoformat()
    return {
        "schema_version": REGIME_KMEANS_CACHE_STATUS_SCHEMA_VERSION,
        "cache_schema_version": REGIME_KMEANS_CACHE_SCHEMA_VERSION,
        "universe_snapshot_id": config.universe_snapshot_id,
        "feature_manifest_hash": feature_manifest_hash,
        "feature_builder_version": config.feature_builder_version,
        "status": report.status,
        "reason": report.reason,
        "cache_validity_status": "VALID" if report.cache_write_succeeded else "WRITE_FAILED",
        "cache_path": str(report.cache_path) if report.cache_path is not None else "",
        "last_cached_date": dates[-1] if dates else None,
        "dates_covered_count": len(dates),
        "row_count": len(market_frame),
        "symbols_covered": list(symbols_covered),
        "cached_dates_reused": report.cached_dates_reused,
        "new_dates_computed": report.new_dates_computed,
        "kmeans_fits_avoided": report.kmeans_fits_avoided,
        "kmeans_fits_performed": report.kmeans_fits_performed,
        "regime_runtime_seconds": report.regime_runtime_seconds,
        "estimated_speedup": report.estimated_speedup,
        "cache_write_succeeded": report.cache_write_succeeded,
        "cache_write_error": report.cache_write_error,
        "update_timestamp_utc": timestamp,
    }


def _write_regime_cache_status(
    *,
    config: RegimeKMeansCacheConfig,
    market_frame: pd.DataFrame,
    report: RegimeKMeansCacheReport,
    symbols_covered: tuple[str, ...],
    feature_manifest_hash: str | None = None,
) -> None:
    payload = _regime_cache_status_payload(
        config=config,
        market_frame=market_frame,
        report=report,
        symbols_covered=symbols_covered,
        feature_manifest_hash=feature_manifest_hash,
    )
    _write_regime_cache_atomic(_regime_cache_status_path(config), payload)


def annotate_regime_kmeans_cache_status(
    config: RegimeKMeansCacheConfig,
    *,
    feature_manifest_hash: str,
) -> None:
    status_path = _regime_cache_status_path(config)
    if not status_path.exists():
        return
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    payload["feature_manifest_hash"] = feature_manifest_hash
    payload["update_timestamp_utc"] = datetime.now(UTC).isoformat()
    try:
        _write_regime_cache_atomic(status_path, payload)
    except OSError:
        return


def _load_regime_cache(
    *,
    config: RegimeKMeansCacheConfig,
    market_frame: pd.DataFrame,
    symbols_covered: tuple[str, ...],
) -> tuple[dict[str, object] | None, pd.Series | None, str]:
    if config.force_rebuild:
        return None, None, "forced_rebuild"
    path = _regime_cache_path(config)
    if not path.exists():
        return None, None, "cache_missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, None, f"cache_corrupt:{exc}"
    if not isinstance(payload, dict):
        return None, None, "cache_payload_not_mapping"

    expected_fields: dict[str, object] = {
        "schema_version": REGIME_KMEANS_CACHE_SCHEMA_VERSION,
        "universe_snapshot_id": config.universe_snapshot_id,
        "regime_input_columns": list(REGIME_KMEANS_INPUT_COLUMNS),
        "kmeans_parameters": _regime_kmeans_parameters(),
        "random_seed": REGIME_KMEANS_RANDOM_STATE,
        "scaler_preprocessing_configuration": REGIME_KMEANS_PREPROCESSING_CONFIG,
        "minimum_sample_requirement": REGIME_KMEANS_MINIMUM_ROWS,
        "feature_builder_code_version": config.feature_builder_version,
        "date_ordering": REGIME_KMEANS_DATE_ORDERING,
        "symbols_covered": list(symbols_covered),
        "output_column_names": ["Date", REGIME_KMEANS_OUTPUT_COLUMN],
        "cache_validity_status": "VALID",
    }
    for field, expected in expected_fields.items():
        if payload.get(field) != expected:
            return None, None, f"{field}_mismatch"

    records = payload.get("records")
    dates_covered = payload.get("dates_covered")
    row_count = payload.get("row_count")
    if not isinstance(records, list) or not isinstance(dates_covered, list):
        return None, None, "cache_records_missing"
    if row_count != len(records) or row_count != len(dates_covered):
        return None, None, "cache_row_count_mismatch"

    current_dates = _market_dates(market_frame)
    if len(dates_covered) > len(current_dates):
        return None, None, "cache_longer_than_current_input"
    if current_dates[: len(dates_covered)] != dates_covered:
        return None, None, "date_prefix_mismatch"

    prefix = market_frame.iloc[: len(dates_covered)].copy()
    prefix_hash = _regime_input_hash(prefix)
    if payload.get("input_prefix_hash") != prefix_hash:
        return None, None, "input_prefix_hash_mismatch"
    if payload.get("full_input_hash") != prefix_hash:
        return None, None, "full_input_hash_mismatch"

    labels = _series_from_cache_records(records, market_frame.index[: len(records)])
    output_hash = _regime_output_hash(labels, prefix)
    if payload.get("output_dataframe_hash") != output_hash:
        return None, None, "output_dataframe_hash_mismatch"
    if payload.get("last_cached_date") != (dates_covered[-1] if dates_covered else None):
        return None, None, "last_cached_date_mismatch"
    return payload, labels, "valid"


def _regime_values(market_frame: pd.DataFrame) -> pd.DataFrame:
    return market_frame[list(REGIME_KMEANS_INPUT_COLUMNS)].replace([np.inf, -np.inf], np.nan)


def _compute_expanding_kmeans_regime(
    market_frame: pd.DataFrame,
    *,
    start_position: int = 0,
    cached_labels: pd.Series | None = None,
) -> _RegimeKMeansComputation:
    values = _regime_values(market_frame)
    clusters: list[float] = []
    if cached_labels is not None:
        clusters.extend(float(value) if pd.notna(value) else math.nan for value in cached_labels)
    fits = 0
    for position in range(start_position, len(values)):
        history = values.iloc[: position + 1].copy()
        if len(history) < REGIME_KMEANS_MINIMUM_ROWS:
            clusters.append(math.nan)
            continue
        medians = history.median(numeric_only=True).fillna(0.0)
        filled = history.fillna(medians)
        if len(filled.drop_duplicates()) < REGIME_KMEANS_N_CLUSTERS:
            clusters.append(math.nan)
            continue
        model = KMeans(
            n_clusters=REGIME_KMEANS_N_CLUSTERS,
            random_state=REGIME_KMEANS_RANDOM_STATE,
            n_init=REGIME_KMEANS_N_INIT,
        )
        labels = model.fit_predict(filled)
        fits += 1
        clusters.append(float(labels[-1]))
    series = pd.Series(clusters, index=market_frame.index, name=REGIME_KMEANS_OUTPUT_COLUMN)
    return _RegimeKMeansComputation(labels=series, kmeans_fits=fits)


def _count_expanding_kmeans_fits(market_frame: pd.DataFrame) -> int:
    values = _regime_values(market_frame)
    fits = 0
    for position in range(len(values)):
        history = values.iloc[: position + 1].copy()
        if len(history) < REGIME_KMEANS_MINIMUM_ROWS:
            continue
        medians = history.median(numeric_only=True).fillna(0.0)
        filled = history.fillna(medians)
        if len(filled.drop_duplicates()) < REGIME_KMEANS_N_CLUSTERS:
            continue
        fits += 1
    return fits


def _expanding_kmeans_regime(market_frame: pd.DataFrame) -> pd.Series:
    return _compute_expanding_kmeans_regime(market_frame).labels


def _expanding_kmeans_regime_with_cache(
    market_frame: pd.DataFrame,
    *,
    cache_config: RegimeKMeansCacheConfig | None,
    symbols_covered: tuple[str, ...],
) -> tuple[pd.Series, RegimeKMeansCacheReport | None]:
    if cache_config is None:
        return _expanding_kmeans_regime(market_frame), None

    start_time = time.perf_counter()
    cache_path = _regime_cache_path(cache_config)
    cached_payload, cached_labels, cache_reason = _load_regime_cache(
        config=cache_config,
        market_frame=market_frame,
        symbols_covered=symbols_covered,
    )
    full_fit_count = _count_expanding_kmeans_fits(market_frame)

    status = "MISS"
    reason = cache_reason
    write_succeeded = True
    write_error: str | None = None
    creation_timestamp = None
    cached_dates_reused = 0
    new_dates_computed = len(market_frame)
    if cached_payload is None or cached_labels is None:
        status = "INVALIDATED" if cache_path.exists() or cache_config.force_rebuild else "MISS"
        total_full = _compute_expanding_kmeans_regime(market_frame)
        labels = total_full.labels
        fits_performed = total_full.kmeans_fits
    elif len(cached_labels) == len(market_frame):
        status = "HIT"
        reason = "cache_valid"
        labels = cached_labels.reindex(market_frame.index)
        fits_performed = 0
        cached_dates_reused = len(cached_labels)
        new_dates_computed = 0
        creation_timestamp = str(cached_payload.get("creation_timestamp_utc") or "")
    else:
        status = "PARTIAL_APPEND"
        reason = "historical_prefix_valid"
        start_position = len(cached_labels)
        appended = _compute_expanding_kmeans_regime(
            market_frame,
            start_position=start_position,
            cached_labels=cached_labels,
        )
        labels = appended.labels
        fits_performed = appended.kmeans_fits
        cached_dates_reused = len(cached_labels)
        new_dates_computed = len(market_frame) - len(cached_labels)
        creation_timestamp = str(cached_payload.get("creation_timestamp_utc") or "")

    if status != "HIT":
        payload = _regime_cache_payload(
            config=cache_config,
            market_frame=market_frame,
            labels=labels,
            symbols_covered=symbols_covered,
            creation_timestamp_utc=creation_timestamp,
        )
        try:
            _write_regime_cache_atomic(cache_path, payload)
        except OSError as exc:
            write_succeeded = False
            write_error = str(exc)
            reason = f"{reason};cache_write_failed"

    elapsed = time.perf_counter() - start_time
    fits_avoided = max(0, full_fit_count - fits_performed)
    estimated_speedup = float(full_fit_count / fits_performed) if fits_performed > 0 else None
    report = RegimeKMeansCacheReport(
        status=status,
        reason=reason,
        cache_path=cache_path,
        cached_dates_reused=cached_dates_reused,
        new_dates_computed=new_dates_computed,
        kmeans_fits_avoided=fits_avoided,
        kmeans_fits_performed=fits_performed,
        regime_runtime_seconds=elapsed,
        estimated_speedup=estimated_speedup,
        cache_write_succeeded=write_succeeded,
        cache_write_error=write_error,
    )
    with suppress(OSError):
        _write_regime_cache_status(
            config=cache_config,
            market_frame=market_frame,
            report=report,
            symbols_covered=symbols_covered,
        )
    return labels, report


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
    feature_columns: dict[str, pd.Series] = {
        "Open": data["Open"],
        "High": data["High"],
        "Low": data["Low"],
        "Close": data["Close"],
        "Volume": data["Volume"],
    }

    for window in RETURN_WINDOWS:
        feature_columns[f"return_{window}"] = close.pct_change(window)
        feature_columns[f"log_return_{window}"] = pd.Series(
            np.log(close / close.shift(window)), index=data.index
        )
    feature_columns["return_accel_5_20"] = (
        feature_columns["return_5"] - feature_columns["return_20"]
    )
    feature_columns["return_5_lag_1"] = feature_columns["return_5"].shift(1)
    feature_columns["return_20_lag_1"] = feature_columns["return_20"].shift(1)
    feature_columns["return_5_change_5"] = feature_columns["return_5"] - feature_columns[
        "return_5"
    ].shift(5)
    prior_return_20_mean = feature_columns["return_20"].shift(1).rolling(252, min_periods=60).mean()
    prior_return_20_std = feature_columns["return_20"].shift(1).rolling(252, min_periods=60).std()
    feature_columns["return_20_zscore_252"] = _safe_divide(
        feature_columns["return_20"] - prior_return_20_mean, prior_return_20_std
    )
    up = close > prior_close
    down = close < prior_close
    feature_columns["up_streak_5"] = up.rolling(5, min_periods=1).sum()
    feature_columns["down_streak_5"] = down.rolling(5, min_periods=1).sum()
    feature_columns["momentum_20_percentile_252"] = _rolling_percentile(
        feature_columns["return_20"], 252, 60
    )

    for window in (20, 63, 126, 252):
        prior_high = high.shift(1).rolling(window, min_periods=max(5, min(window, 20))).max()
        prior_low = low.shift(1).rolling(window, min_periods=max(5, min(window, 20))).min()
        feature_columns[f"distance_prior_high_{window}"] = _safe_divide(close, prior_high) - 1.0
        feature_columns[f"distance_prior_low_{window}"] = _safe_divide(close, prior_low) - 1.0
        feature_columns[f"range_position_{window}"] = _safe_divide(
            close - prior_low, prior_high - prior_low
        )

    for window in TREND_WINDOWS:
        sma = close.rolling(window, min_periods=window).mean()
        feature_columns[f"distance_sma_{window}"] = _safe_divide(close, sma) - 1.0
        feature_columns[f"sma_{window}_slope_5"] = sma.pct_change(5)
    feature_columns["trend_persistence_20"] = (
        (close > close.rolling(20, min_periods=20).mean()).rolling(20, min_periods=5).mean()
    )
    feature_columns["pullback_depth_20"] = (
        _safe_divide(close, high.shift(1).rolling(20, min_periods=20).max()) - 1.0
    )
    feature_columns["recovery_pct_20"] = _safe_divide(
        close - low.shift(1).rolling(20, min_periods=20).min(),
        high.shift(1).rolling(20, min_periods=20).max()
        - low.shift(1).rolling(20, min_periods=20).min(),
    )
    feature_columns["gap_pct"] = _safe_divide(open_price, prior_close) - 1.0
    feature_columns["support_proximity_20"] = (
        _safe_divide(
            close,
            low.shift(1).rolling(20, min_periods=20).min(),
        )
        - 1.0
    )
    feature_columns["resistance_proximity_20"] = (
        _safe_divide(
            close,
            high.shift(1).rolling(20, min_periods=20).max(),
        )
        - 1.0
    )

    for window in ATR_WINDOWS:
        atr = wilder_average(true_range, window)
        feature_columns[f"atr_{window}"] = atr
        feature_columns[f"atr_pct_{window}"] = _safe_divide(atr, close)
    returns_1 = close.pct_change()
    for window in (10, 20, 63):
        feature_columns[f"realized_vol_{window}"] = returns_1.rolling(
            window, min_periods=window
        ).std()
    feature_columns["upside_vol_20"] = (
        returns_1.where(returns_1 > 0).rolling(20, min_periods=5).std()
    )
    feature_columns["downside_vol_20"] = (
        returns_1.where(returns_1 < 0).rolling(20, min_periods=5).std()
    )
    feature_columns["range_pct"] = _safe_divide(high - low, close)
    feature_columns["range_percentile_63"] = _rolling_percentile(
        feature_columns["range_pct"], 63, 20
    )
    feature_columns["volatility_compression_20_100"] = _safe_divide(
        feature_columns["realized_vol_20"],
        feature_columns["realized_vol_63"].rolling(100, min_periods=40).median(),
    )
    feature_columns["volatility_expansion_20_63"] = _safe_divide(
        feature_columns["realized_vol_20"], feature_columns["realized_vol_63"]
    )
    feature_columns["overnight_gap_vol_20"] = (
        feature_columns["gap_pct"].rolling(20, min_periods=20).std()
    )
    feature_columns["intraday_range_relative_20"] = _safe_divide(
        feature_columns["range_pct"],
        feature_columns["range_pct"].shift(1).rolling(20, min_periods=10).median(),
    )

    prior_volume_mean = volume.shift(1).rolling(20, min_periods=10).mean()
    prior_volume_std = volume.shift(1).rolling(20, min_periods=10).std()
    feature_columns["relative_volume_20"] = _safe_divide(volume, prior_volume_mean)
    feature_columns["volume_zscore_20"] = _safe_divide(volume - prior_volume_mean, prior_volume_std)
    feature_columns["dollar_volume"] = close * volume
    feature_columns["volume_trend_20"] = volume.rolling(20, min_periods=20).mean().pct_change(5)
    feature_columns["up_volume_proxy_20"] = (
        volume.where(close >= prior_close, 0.0).rolling(20, min_periods=5).sum()
    )
    feature_columns["down_volume_proxy_20"] = (
        volume.where(close < prior_close, 0.0).rolling(20, min_periods=5).sum()
    )
    feature_columns["price_volume_agreement_5"] = np.sign(feature_columns["return_5"]) * np.sign(
        feature_columns["volume_trend_20"]
    )
    feature_columns["return_volume_interaction_20"] = (
        feature_columns["return_20"] * feature_columns["relative_volume_20"]
    )
    obv_step = np.sign(close.diff()).fillna(0.0) * volume
    feature_columns["obv_change_20"] = _safe_pct_change(obv_step.cumsum(), 20)
    feature_columns["volume_expansion_after_compression"] = (
        feature_columns["relative_volume_20"]
        / feature_columns["relative_volume_20"].shift(1).rolling(20, min_periods=10).median()
    )

    session_range = (high - low).replace(0, np.nan)
    body = (close - open_price).abs()
    feature_columns["body_pct"] = _safe_divide(body, session_range)
    feature_columns["upper_wick_pct"] = _safe_divide(
        high - pd.concat([open_price, close], axis=1).max(axis=1), session_range
    )
    feature_columns["lower_wick_pct"] = _safe_divide(
        pd.concat([open_price, close], axis=1).min(axis=1) - low, session_range
    )
    feature_columns["close_position"] = _safe_divide(close - low, session_range)
    feature_columns["inside_bar"] = ((high < high.shift(1)) & (low > low.shift(1))).astype(float)
    feature_columns["outside_bar"] = ((high > high.shift(1)) & (low < low.shift(1))).astype(float)
    feature_columns["expansion_bar"] = (
        feature_columns["range_pct"]
        > feature_columns["range_pct"].shift(1).rolling(20, min_periods=10).quantile(0.8)
    ).astype(float)
    feature_columns["lower_rejection_bar"] = (
        (feature_columns["lower_wick_pct"] > 0.45) & (feature_columns["close_position"] > 0.55)
    ).astype(float)

    for length in RSI_LENGTHS:
        rsi = wilder_rsi(close, length)
        feature_columns[f"rsi_{length}"] = rsi
        feature_columns[f"rsi_{length}_slope_3"] = rsi.diff(3)
        feature_columns[f"rsi_{length}_accel"] = rsi.diff(3).diff(3)
        rsi_low = rsi.shift(1).rolling(252, min_periods=60).quantile(0.2)
        rsi_high = rsi.shift(1).rolling(252, min_periods=60).quantile(0.8)
        feature_columns[f"rsi_{length}_percentile_252"] = _rolling_percentile(rsi, 252, 60)
        feature_columns[f"rsi_{length}_distance_low_zone"] = rsi - rsi_low
        feature_columns[f"rsi_{length}_distance_high_zone"] = rsi - rsi_high

    feature_columns["roc_10"] = close.pct_change(10)
    low_14 = low.shift(1).rolling(14, min_periods=14).min()
    high_14 = high.shift(1).rolling(14, min_periods=14).max()
    feature_columns["stochastic_14"] = _safe_divide(close - low_14, high_14 - low_14)
    ema_12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema_26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    feature_columns["macd_12_26"] = _safe_divide(ema_12 - ema_26, close)
    feature_columns["macd_12_26_slope_5"] = feature_columns["macd_12_26"].diff(5)
    sma_20 = close.rolling(20, min_periods=20).mean()
    std_20 = close.rolling(20, min_periods=20).std()
    feature_columns["bollinger_z_20"] = _safe_divide(close - sma_20, std_20)
    feature_columns["keltner_distance_20"] = _safe_divide(close - sma_20, feature_columns["atr_20"])
    typical = (high + low + close) / 3.0
    typical_mean = typical.rolling(20, min_periods=20).mean()
    mean_dev = (typical - typical_mean).abs().rolling(20, min_periods=20).mean()
    feature_columns["cci_20"] = _safe_divide(typical - typical_mean, 0.015 * mean_dev)
    money_flow = typical * volume
    positive_flow = (
        money_flow.where(typical > typical.shift(1), 0.0).rolling(14, min_periods=14).sum()
    )
    negative_flow = (
        money_flow.where(typical < typical.shift(1), 0.0).rolling(14, min_periods=14).sum()
    )
    money_ratio = _safe_divide(positive_flow, negative_flow)
    feature_columns["mfi_14"] = 100.0 - (100.0 / (1.0 + money_ratio))
    plus_dm = (high.diff()).where((high.diff() > low.diff().abs()) & (high.diff() > 0), 0.0)
    minus_dm = (low.diff().abs()).where((low.diff().abs() > high.diff()) & (low.diff() < 0), 0.0)
    atr_14 = feature_columns["atr_14"].replace(0, np.nan)
    feature_columns["plus_di_14"] = 100.0 * _safe_divide(wilder_average(plus_dm, 14), atr_14)
    feature_columns["minus_di_14"] = 100.0 * _safe_divide(wilder_average(minus_dm, 14), atr_14)
    dx = 100.0 * _safe_divide(
        (feature_columns["plus_di_14"] - feature_columns["minus_di_14"]).abs(),
        feature_columns["plus_di_14"] + feature_columns["minus_di_14"],
    )
    feature_columns["adx_14"] = wilder_average(dx, 14)

    feature_columns["symbol"] = pd.Series(symbol, index=data.index)
    feature_columns["role"] = pd.Series(metadata.role if metadata else "stock", index=data.index)
    feature_columns["sector"] = pd.Series(
        metadata.sector if metadata and metadata.sector else "unknown", index=data.index
    )
    feature_columns["sector_proxy"] = pd.Series(
        metadata.sector_proxy if metadata and metadata.sector_proxy else "", index=data.index
    )
    feature_columns["is_benchmark"] = pd.Series(
        float(bool(metadata.benchmark)) if metadata else 0.0, index=data.index
    )
    result = pd.DataFrame(feature_columns, index=data.index).copy()
    return result.reset_index().rename(columns={"index": "Date"})


def _add_cross_sectional_features(
    panel: pd.DataFrame,
    universe: UniverseConfig,
    *,
    regime_cache_config: RegimeKMeansCacheConfig | None = None,
) -> tuple[pd.DataFrame, RegimeKMeansCacheReport | None]:
    data = panel.copy()
    rank_columns: dict[str, pd.Series] = {}
    for window in (5, 20, 63):
        column = f"return_{window}"
        if column in data.columns:
            rank_columns[f"relative_strength_rank_{window}"] = data.groupby("Date")[column].rank(
                pct=True
            )
    if rank_columns:
        data = pd.concat([data, pd.DataFrame(rank_columns, index=data.index)], axis=1)

    breadth = data.groupby("Date").agg(
        breadth_advance_pct=("return_1", lambda values: float((values > 0).mean())),
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
    breadth_up_volume_pct = (up_volume / total_volume).rename("breadth_up_volume_pct")
    breadth = pd.concat(
        [
            breadth[["breadth_advance_pct"]],
            breadth_up_volume_pct,
            breadth[
                [
                    "breadth_above_sma_50_pct",
                    "breadth_high_20_pct",
                    "breadth_low_20_pct",
                    "breadth_dispersion_20",
                    "breadth_skew_20",
                ]
            ],
        ],
        axis=1,
    )
    data = data.merge(breadth.reset_index(), on="Date", how="left")
    sector_daily = (
        data.groupby(["Date", "sector"])
        .agg(
            sector_breadth_advance_pct=("return_1", lambda values: float((values > 0).mean())),
            sector_participation_sma50_pct=(
                "distance_sma_50",
                lambda values: float((values > 0).mean()),
            ),
            sector_momentum_mean_20=("return_20", "mean"),
        )
        .reset_index()
    )
    sector_momentum_rank_20 = (
        sector_daily.groupby("Date")["sector_momentum_mean_20"]
        .rank(pct=True)
        .rename("sector_momentum_rank_20")
    )
    sector_daily = pd.concat([sector_daily, sector_momentum_rank_20], axis=1)
    data = data.merge(sector_daily, on=["Date", "sector"], how="left")

    pivot_returns = data.pivot(index="Date", columns="symbol", values="return_1")
    pivot_close = data.pivot(index="Date", columns="symbol", values="Close")
    market_columns: dict[str, pd.Series] = {}
    for benchmark in PRIMARY_BENCHMARKS:
        if benchmark not in pivot_returns.columns:
            continue
        benchmark_return = pivot_returns[benchmark]
        for window in (5, 20):
            bench_window = pivot_close[benchmark].pct_change(window)
            benchmark_column = f"{benchmark.lower()}_return_{window}"
            market_columns[benchmark_column] = data["Date"].map(bench_window)
            market_columns[f"relative_return_vs_{benchmark.lower()}_{window}"] = (
                data[f"return_{window}"] - market_columns[benchmark_column]
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
        beta_column = pd.Series(np.nan, index=data.index, dtype=float)
        corr_column = pd.Series(np.nan, index=data.index, dtype=float)
        residual_column = pd.Series(np.nan, index=data.index, dtype=float)
        trend_agreement_column = pd.Series(np.nan, index=data.index, dtype=float)
        benchmark_return_5 = market_columns[f"{benchmark.lower()}_return_5"]
        benchmark_trend = data.loc[
            data["symbol"] == benchmark, ["Date", "distance_sma_50"]
        ].set_index("Date")["distance_sma_50"]
        for symbol in pivot_returns.columns:
            mask = data["symbol"] == symbol
            if not bool(mask.any()):
                continue
            beta_values = data.loc[mask, "Date"].map(beta[symbol])
            corr_values = data.loc[mask, "Date"].map(corr[symbol])
            beta_column.loc[mask] = beta_values
            corr_column.loc[mask] = corr_values
            residual_column.loc[mask] = (
                data.loc[mask, "return_1"]
                - beta_values * benchmark_return_5.loc[mask].fillna(0.0) / 5.0
            )
            trend_agreement_column.loc[mask] = np.sign(data.loc[mask, "distance_sma_50"]) * np.sign(
                data.loc[mask, "Date"].map(benchmark_trend)
            )
        market_columns[f"rolling_beta_vs_{benchmark.lower()}_63"] = beta_column
        market_columns[f"rolling_corr_vs_{benchmark.lower()}_63"] = corr_column
        market_columns[f"residual_return_vs_{benchmark.lower()}_1"] = residual_column
        market_columns[f"benchmark_trend_agreement_vs_{benchmark.lower()}"] = trend_agreement_column
    if market_columns:
        data = pd.concat([data, pd.DataFrame(market_columns, index=data.index)], axis=1)

    sector_returns = {
        row.symbol: row.sector_proxy
        for row in universe.symbols
        if row.enabled and row.sector_proxy and row.sector_proxy in pivot_close.columns
    }
    if sector_returns:
        sector_return_20 = pd.Series(np.nan, index=data.index, dtype=float)
        relative_return_vs_sector_20 = pd.Series(np.nan, index=data.index, dtype=float)
        sector_trend_agreement = pd.Series(np.nan, index=data.index, dtype=float)
        sector_divergence_20 = pd.Series(np.nan, index=data.index, dtype=float)
        for symbol, proxy in sector_returns.items():
            mask = data["symbol"] == symbol
            proxy_return_20 = pivot_close[proxy].pct_change(20)
            sector_values = data.loc[mask, "Date"].map(proxy_return_20)
            sector_return_20.loc[mask] = sector_values
            relative_values = data.loc[mask, "return_20"] - sector_values
            relative_return_vs_sector_20.loc[mask] = relative_values
            proxy_trend = data.loc[data["symbol"] == proxy, ["Date", "distance_sma_50"]].set_index(
                "Date"
            )["distance_sma_50"]
            sector_trend_agreement.loc[mask] = np.sign(data.loc[mask, "distance_sma_50"]) * np.sign(
                data.loc[mask, "Date"].map(proxy_trend)
            )
            sector_divergence_20.loc[mask] = relative_values
        data = pd.concat(
            [
                data,
                pd.DataFrame(
                    {
                        "sector_return_20": sector_return_20,
                        "relative_return_vs_sector_20": relative_return_vs_sector_20,
                        "sector_trend_agreement": sector_trend_agreement,
                        "sector_divergence_20": sector_divergence_20,
                    },
                    index=data.index,
                ),
            ],
            axis=1,
        )

    relationship_frames: list[pd.DataFrame] = []
    for source, related_symbols in universe.relationships.items():
        if source not in pivot_returns.columns:
            continue
        source_return = pivot_returns[source]
        for related in related_symbols:
            if related not in pivot_returns.columns:
                continue
            related_return = pivot_returns[related]
            corr_column_name = f"relationship_corr_{source.lower()}_{related.lower()}_63"
            relationship_corr = source_return.rolling(63, min_periods=40).corr(related_return)
            relationship = pd.DataFrame(
                {
                    "Date": source_return.index,
                    corr_column_name: relationship_corr,
                    f"relationship_divergence_{source.lower()}_{related.lower()}_5": source_return.rolling(
                        5, min_periods=5
                    ).sum()
                    + related_return.rolling(5, min_periods=5).sum(),
                    f"relationship_lead_lag_{source.lower()}_{related.lower()}_5": source_return.shift(
                        1
                    )
                    .rolling(5, min_periods=5)
                    .corr(related_return),
                    f"relationship_mutual_info_{source.lower()}_{related.lower()}_63": (
                        _gaussian_mutual_information(relationship_corr)
                    ),
                    f"inverse_confirmation_{source.lower()}_{related.lower()}_63": (
                        relationship_corr.abs()
                    ),
                    f"relationship_breakdown_{source.lower()}_{related.lower()}_63": (
                        relationship_corr.abs() < 0.4
                    ).astype(float),
                }
            ).reset_index(drop=True)
            relationship_frames.append(relationship)
    if relationship_frames:
        relationship_daily = pd.concat(
            [frame.set_index("Date") for frame in relationship_frames], axis=1
        ).reset_index()
        data = data.merge(relationship_daily, on="Date", how="left")

    if "SPY" in pivot_close.columns:
        spy_trend = pivot_close["SPY"].pct_change(63)
        spy_vol = pivot_returns["SPY"].rolling(20, min_periods=20).std()
        market_regime_trend_score = data["Date"].map(spy_trend)
        market_regime_volatility_score = data["Date"].map(spy_vol)
    else:
        market_regime_trend_score = data.groupby("Date")["return_20"].transform("mean")
        market_regime_volatility_score = data.groupby("Date")["return_1"].transform("std")
    market_regime_label = pd.Series(
        np.select(
            [
                (market_regime_trend_score > 0)
                & (market_regime_volatility_score <= market_regime_volatility_score.median()),
                (market_regime_trend_score > 0),
                (market_regime_trend_score <= 0)
                & (market_regime_volatility_score > market_regime_volatility_score.median()),
            ],
            ["uptrend_low_vol", "uptrend_high_vol", "downtrend_high_vol"],
            default="mixed",
        ),
        index=data.index,
    )
    data = pd.concat(
        [
            data,
            pd.DataFrame(
                {
                    "market_regime_trend_score": market_regime_trend_score,
                    "market_regime_volatility_score": market_regime_volatility_score,
                    "market_regime_label": market_regime_label,
                },
                index=data.index,
            ),
        ],
        axis=1,
    )
    market_daily = (
        data.groupby("Date")
        .agg(
            market_regime_trend_score=("market_regime_trend_score", "first"),
            market_regime_volatility_score=("market_regime_volatility_score", "first"),
            breadth_advance_pct=("breadth_advance_pct", "first"),
            breadth_dispersion_20=("breadth_dispersion_20", "first"),
        )
        .reset_index()
    )
    symbols_covered = tuple(sorted(str(symbol) for symbol in data["symbol"].dropna().unique()))
    market_regime_cluster_expanding, regime_cache_report = _expanding_kmeans_regime_with_cache(
        market_daily,
        cache_config=regime_cache_config,
        symbols_covered=symbols_covered,
    )
    market_daily = pd.concat([market_daily, market_regime_cluster_expanding], axis=1)
    cluster_by_date = market_daily.set_index("Date")["market_regime_cluster_expanding"]
    data = pd.concat(
        [
            data,
            pd.DataFrame(
                {
                    "market_regime_cluster_expanding": data["Date"].map(cluster_by_date),
                    "regime_conditioned_return_20": data["return_20"]
                    * data["market_regime_trend_score"].fillna(0.0),
                },
                index=data.index,
            ),
        ],
        axis=1,
    )
    return data.sort_values(["Date", "symbol"]).reset_index(drop=True).copy(), regime_cache_report


def _family_map(columns: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for column in columns:
        if column in {"Open", "High", "Low", "Close"}:
            mapping[column] = "trend_structure"
        elif column == "Volume":
            mapping[column] = "volume_participation"
        elif column.startswith(("return_", "log_return_", "momentum_", "up_streak", "down_streak")):
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
            (
                "roc_",
                "stochastic",
                "macd",
                "bollinger",
                "keltner",
                "cci",
                "mfi",
                "adx_",
                "plus_di_",
                "minus_di_",
            )
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
        elif column.startswith("inverse_"):
            mapping[column] = "inverse_leveraged"
        elif column.startswith("relationship_"):
            mapping[column] = "relationship_graph"
        elif column.startswith("breadth_"):
            mapping[column] = "breadth"
        elif column.startswith("market_regime"):
            mapping[column] = "regime"
        else:
            mapping[column] = "technical_primitives"
    return mapping


def feature_family_map_for_columns(columns: list[str]) -> dict[str, str]:
    return _family_map(columns)


def build_feature_panel(
    frames: dict[str, pd.DataFrame],
    universe: UniverseConfig,
    *,
    regime_cache_config: RegimeKMeansCacheConfig | None = None,
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
    panel, regime_cache_report = _add_cross_sectional_features(
        panel,
        universe,
        regime_cache_config=regime_cache_config,
    )
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
    family_by_column = _family_map(feature_columns)
    specs = feature_specs_for_columns(feature_columns, family_by_column)
    manifest = feature_manifest_hash(specs, tuple(sorted(feature_columns)))
    return FeatureBuildResult(
        frame=panel,
        specs=specs,
        manifest_hash=manifest,
        feature_family_by_column=family_by_column,
        regime_cache_report=regime_cache_report,
    )


LABEL_SIDE_COLUMN_FRAGMENTS = (
    "time_exit",
    "utility",
    "profitable_despite_failed_tbs",
    "early_adverse_recovery",
)


def _is_label_side_column(name: str) -> bool:
    lowered = name.lower()
    return name.startswith("label_") or any(
        fragment in lowered for fragment in LABEL_SIDE_COLUMN_FRAGMENTS
    )


def numeric_feature_columns(frame: pd.DataFrame) -> list[str]:
    blocked = {"Date", "symbol", "role", "sector", "sector_proxy", "market_regime_label"}
    columns: list[str] = []
    for column in frame.columns:
        name = str(column)
        if name in blocked or _is_label_side_column(name):
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            columns.append(name)
    return columns


def reject_label_columns(columns: list[str]) -> None:
    labels = [column for column in columns if _is_label_side_column(str(column))]
    if labels:
        raise ValueError(
            "Label columns cannot enter the feature matrix; "
            f"Label-side columns cannot enter the feature matrix: {labels[:5]}"
        )
