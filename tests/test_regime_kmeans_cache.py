from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from swing_rsi.engine import features as feature_module
from swing_rsi.engine.features import (
    REGIME_KMEANS_CACHE_SCHEMA_VERSION,
    REGIME_KMEANS_OUTPUT_COLUMN,
    RegimeKMeansCacheConfig,
    _expanding_kmeans_regime,
    _expanding_kmeans_regime_with_cache,
    _regime_cache_path,
    build_feature_panel,
    numeric_feature_columns,
)
from swing_rsi.engine.labels import LabelConfig, build_label_panel, merge_features_and_labels
from swing_rsi.engine.universe import UniverseConfig, UniverseSymbol
from swing_rsi.sample_data import generate_sample_ohlcv


def _market_frame(rows: int = 140) -> pd.DataFrame:
    index = np.arange(rows, dtype=float)
    return pd.DataFrame(
        {
            "Date": pd.bdate_range("2020-01-02", periods=rows),
            "market_regime_trend_score": np.sin(index / 7.0) + index / 500.0,
            "market_regime_volatility_score": np.cos(index / 11.0) / 20.0 + 0.05,
            "breadth_advance_pct": 0.5 + np.sin(index / 5.0) / 10.0,
            "breadth_dispersion_20": 0.02 + np.cos(index / 13.0) / 100.0,
        }
    )


def _cache_config(tmp_path: Path, *, force: bool = False, snapshot: str = "test-snapshot"):
    return RegimeKMeansCacheConfig(
        cache_dir=tmp_path / "data" / "cache" / "regime",
        universe_snapshot_id=snapshot,
        force_rebuild=force,
    )


def _symbols(extra: str | None = None) -> tuple[str, ...]:
    values = ["AAPL", "QQQ", "SPY"]
    if extra is not None:
        values.append(extra)
    return tuple(sorted(values))


def _load_cache(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_first_run_without_cache_recomputes_and_writes_valid_cache(tmp_path: Path) -> None:
    market = _market_frame()
    config = _cache_config(tmp_path)

    labels, report = _expanding_kmeans_regime_with_cache(
        market, cache_config=config, symbols_covered=_symbols()
    )

    assert report is not None
    assert report.status == "MISS"
    assert report.kmeans_fits_performed > 0
    assert report.kmeans_fits_avoided == 0
    assert report.cache_write_succeeded
    pd.testing.assert_series_equal(labels, _expanding_kmeans_regime(market))

    cache_path = _regime_cache_path(config)
    payload = _load_cache(cache_path)
    assert payload["schema_version"] == REGIME_KMEANS_CACHE_SCHEMA_VERSION
    assert payload["cache_validity_status"] == "VALID"
    assert payload["row_count"] == len(market)
    assert payload["last_cached_date"] == str(market["Date"].iloc[-1].date())
    assert payload["output_column_names"] == ["Date", REGIME_KMEANS_OUTPUT_COLUMN]


def test_identical_second_run_reuses_cache_with_zero_kmeans_fits(tmp_path: Path) -> None:
    market = _market_frame()
    config = _cache_config(tmp_path)
    full_labels = _expanding_kmeans_regime(market)
    _expanding_kmeans_regime_with_cache(market, cache_config=config, symbols_covered=_symbols())

    labels, report = _expanding_kmeans_regime_with_cache(
        market, cache_config=config, symbols_covered=_symbols()
    )

    assert report is not None
    assert report.status == "HIT"
    assert report.cached_dates_reused == len(market)
    assert report.new_dates_computed == 0
    assert report.kmeans_fits_performed == 0
    assert report.kmeans_fits_avoided > 0
    pd.testing.assert_series_equal(labels, full_labels)


def test_appending_one_new_date_computes_only_new_date_and_matches_full_recompute(
    tmp_path: Path,
) -> None:
    original = _market_frame(140)
    appended = _market_frame(141)
    config = _cache_config(tmp_path)
    _expanding_kmeans_regime_with_cache(original, cache_config=config, symbols_covered=_symbols())

    labels, report = _expanding_kmeans_regime_with_cache(
        appended, cache_config=config, symbols_covered=_symbols()
    )
    full = _expanding_kmeans_regime(appended)

    assert report is not None
    assert report.status == "PARTIAL_APPEND"
    assert report.cached_dates_reused == len(original)
    assert report.new_dates_computed == 1
    assert report.kmeans_fits_performed == 1
    pd.testing.assert_series_equal(labels, full)


def test_historical_prefix_change_invalidates_cache(tmp_path: Path) -> None:
    market = _market_frame()
    config = _cache_config(tmp_path)
    _expanding_kmeans_regime_with_cache(market, cache_config=config, symbols_covered=_symbols())
    changed = market.copy()
    changed.loc[10, "market_regime_trend_score"] += 1.0

    _, report = _expanding_kmeans_regime_with_cache(
        changed, cache_config=config, symbols_covered=_symbols()
    )

    assert report is not None
    assert report.status == "INVALIDATED"
    assert "input_prefix_hash_mismatch" in report.reason
    assert report.kmeans_fits_performed > 0


def test_kmeans_config_random_seed_input_columns_and_symbols_invalidate_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    market = _market_frame()
    config = _cache_config(tmp_path)
    _expanding_kmeans_regime_with_cache(market, cache_config=config, symbols_covered=_symbols())

    monkeypatch.setattr(feature_module, "REGIME_KMEANS_N_CLUSTERS", 4)
    _, report = _expanding_kmeans_regime_with_cache(
        market, cache_config=config, symbols_covered=_symbols()
    )
    assert report is not None
    assert report.status == "INVALIDATED"
    assert "kmeans_parameters_mismatch" in report.reason
    monkeypatch.setattr(feature_module, "REGIME_KMEANS_N_CLUSTERS", 3)

    monkeypatch.setattr(feature_module, "REGIME_KMEANS_RANDOM_STATE", 7)
    _, report = _expanding_kmeans_regime_with_cache(
        market, cache_config=config, symbols_covered=_symbols()
    )
    assert report is not None
    assert report.status == "INVALIDATED"
    assert "kmeans_parameters_mismatch" in report.reason
    monkeypatch.setattr(feature_module, "REGIME_KMEANS_RANDOM_STATE", 42)

    changed_columns = (*feature_module.REGIME_KMEANS_INPUT_COLUMNS, "extra_regime_input")
    market_with_extra = market.copy()
    market_with_extra["extra_regime_input"] = np.linspace(0.0, 1.0, len(market))
    monkeypatch.setattr(feature_module, "REGIME_KMEANS_INPUT_COLUMNS", changed_columns)
    _, report = _expanding_kmeans_regime_with_cache(
        market_with_extra, cache_config=config, symbols_covered=_symbols()
    )
    assert report is not None
    assert report.status == "INVALIDATED"
    assert "regime_input_columns_mismatch" in report.reason
    monkeypatch.setattr(
        feature_module,
        "REGIME_KMEANS_INPUT_COLUMNS",
        changed_columns[:-1],
    )

    _expanding_kmeans_regime_with_cache(market, cache_config=config, symbols_covered=_symbols())
    _, report = _expanding_kmeans_regime_with_cache(
        market, cache_config=config, symbols_covered=_symbols("XLK")
    )
    assert report is not None
    assert report.status == "INVALIDATED"
    assert "symbols_covered_mismatch" in report.reason


def test_corrupt_cache_is_ignored_and_recomputed(tmp_path: Path) -> None:
    market = _market_frame()
    config = _cache_config(tmp_path)
    _expanding_kmeans_regime_with_cache(market, cache_config=config, symbols_covered=_symbols())
    _regime_cache_path(config).write_text("{bad json", encoding="utf-8")

    labels, report = _expanding_kmeans_regime_with_cache(
        market, cache_config=config, symbols_covered=_symbols()
    )

    assert report is not None
    assert report.status == "INVALIDATED"
    assert "cache_corrupt" in report.reason
    assert report.kmeans_fits_performed > 0
    pd.testing.assert_series_equal(labels, _expanding_kmeans_regime(market))


def test_atomic_write_failure_preserves_previous_valid_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _market_frame(140)
    appended = _market_frame(141)
    config = _cache_config(tmp_path)
    _expanding_kmeans_regime_with_cache(original, cache_config=config, symbols_covered=_symbols())
    cache_path = _regime_cache_path(config)
    before = cache_path.read_text(encoding="utf-8")

    def fail_replace(source: Path | str, target: Path | str) -> None:
        raise OSError(f"synthetic failure replacing {source} -> {target}")

    monkeypatch.setattr(feature_module.os, "replace", fail_replace)
    labels, report = _expanding_kmeans_regime_with_cache(
        appended, cache_config=config, symbols_covered=_symbols()
    )

    assert report is not None
    assert report.status == "PARTIAL_APPEND"
    assert not report.cache_write_succeeded
    assert "cache_write_failed" in report.reason
    assert cache_path.read_text(encoding="utf-8") == before
    assert _load_cache(cache_path)["row_count"] == len(original)
    pd.testing.assert_series_equal(labels, _expanding_kmeans_regime(appended))


def test_forced_rebuild_ignores_cache_and_rewrites_it(tmp_path: Path) -> None:
    market = _market_frame()
    config = _cache_config(tmp_path)
    _expanding_kmeans_regime_with_cache(market, cache_config=config, symbols_covered=_symbols())
    forced = _cache_config(tmp_path, force=True)

    _, report = _expanding_kmeans_regime_with_cache(
        market, cache_config=forced, symbols_covered=_symbols()
    )

    assert report is not None
    assert report.status == "INVALIDATED"
    assert report.reason == "forced_rebuild"
    assert report.kmeans_fits_performed > 0
    assert _load_cache(_regime_cache_path(forced))["row_count"] == len(market)


def _universe() -> UniverseConfig:
    return UniverseConfig(
        name="cache-test",
        provider="fmp",
        default_start="2018-01-02",
        symbols=(
            UniverseSymbol("AAPL", role="stock", sector="technology", sector_proxy="XLK"),
            UniverseSymbol("SPY", role="broad_market_etf", sector="broad_market", benchmark=True),
            UniverseSymbol("XLK", role="sector_etf", sector="technology"),
            UniverseSymbol("SQQQ", role="leveraged_inverse_etf", sector="inverse_technology"),
        ),
        relationships={"SPY": ("SQQQ",)},
    )


def _frames(rows: int = 260) -> dict[str, pd.DataFrame]:
    return {
        "AAPL": generate_sample_ohlcv(rows=rows, seed=11),
        "SPY": generate_sample_ohlcv(rows=rows, seed=12),
        "XLK": generate_sample_ohlcv(rows=rows, seed=13),
        "SQQQ": generate_sample_ohlcv(rows=rows, seed=14),
    }


def test_feature_panel_cache_hit_preserves_outputs_manifest_and_model_matrix_hygiene(
    tmp_path: Path,
) -> None:
    frames = _frames()
    universe = _universe()
    baseline = build_feature_panel(frames, universe)
    cache_config = _cache_config(tmp_path, snapshot=universe.snapshot_id)
    first = build_feature_panel(frames, universe, regime_cache_config=cache_config)
    second = build_feature_panel(frames, universe, regime_cache_config=cache_config)

    assert first.regime_cache_report is not None
    assert first.regime_cache_report.status == "MISS"
    assert second.regime_cache_report is not None
    assert second.regime_cache_report.status == "HIT"
    assert second.regime_cache_report.kmeans_fits_performed == 0
    assert baseline.manifest_hash == first.manifest_hash == second.manifest_hash
    pd.testing.assert_frame_equal(baseline.frame, first.frame)
    pd.testing.assert_frame_equal(baseline.frame, second.frame)

    regime_columns = [
        "market_regime_label",
        "market_regime_cluster_expanding",
        "regime_conditioned_return_20",
    ]
    pd.testing.assert_frame_equal(baseline.frame[regime_columns], second.frame[regime_columns])
    labels = build_label_panel(frames, LabelConfig(horizons=(10,)))
    modeling = merge_features_and_labels(second.frame, labels)
    assert len(modeling) == len(second.frame)
    assert not any(
        str(column).startswith("label_") for column in numeric_feature_columns(second.frame)
    )
    numeric = second.frame.select_dtypes(include="number")
    assert int(np.isposinf(numeric.to_numpy()).sum()) == 0
    assert int(np.isneginf(numeric.to_numpy()).sum()) == 0


def test_regime_cache_path_is_git_ignored() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "check-ignore", "data/cache/regime/example.json"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
