from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from swing_rsi.application.datasets import (
    discover_raw_datasets,
    download_daily_to_raw,
    slice_date_window,
    structural_audit_csv,
)
from swing_rsi.application.project_status import collect_project_status
from swing_rsi.application.research_service import (
    candidate_rule_count,
    grid_for_preset,
    research_report_path,
    retail_control_rule,
    save_research_report,
)
from swing_rsi.application.validation_service import aggregate_walk_forward_results
from swing_rsi.data.loader import load_ohlcv_csv, save_ohlcv_csv


def _synthetic_ohlcv(start: str = "2014-01-02", rows: int = 2_520) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=rows)
    close = pd.Series(range(rows), index=dates, dtype=float) * 0.05 + 100.0
    open_price = close - 0.10
    high = close + 1.00
    low = open_price - 1.00
    volume = pd.Series(1_000_000.0, index=dates)
    return pd.DataFrame(
        {
            "Open": open_price,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=dates.rename("Date"),
    )


def _fixed_downloader(frame: pd.DataFrame):
    def download(
        _ticker: str,
        _start: str | None,
        _end: str | None,
        _provider: str,
    ) -> pd.DataFrame:
        return frame.copy()

    return download


def test_project_status_never_returns_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "src" / "swing_rsi").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.setenv("FMP_API_KEY", "super-secret-status-key")

    status = collect_project_status(tmp_path)

    assert status.fmp_configured is True
    assert "super-secret-status-key" not in str(status)


def test_dataset_discovery_ignores_unsupported_files(
    tmp_path: Path,
    simple_ohlcv: pd.DataFrame,
) -> None:
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    save_ohlcv_csv(simple_ohlcv, raw / "AAPL.csv")
    (raw / "notes.txt").write_text("ignore", encoding="utf-8")
    (raw / "MSFT.parquet").write_text("ignore", encoding="utf-8")
    (raw / ".gitkeep").write_text("", encoding="utf-8")

    discovered = discover_raw_datasets(tmp_path)

    assert [dataset.ticker for dataset in discovered] == ["AAPL"]


def test_date_window_slicing_is_chronological(simple_ohlcv: pd.DataFrame) -> None:
    frame = simple_ohlcv.sort_index(ascending=False)

    window = slice_date_window(frame, start="2020-03-01", end="2020-04-01")

    assert window.index.is_monotonic_increasing
    assert window.index.min() >= pd.Timestamp("2020-03-01")
    assert window.index.max() <= pd.Timestamp("2020-04-01")


def test_structural_audit_counts_known_errors(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    pd.DataFrame(
        {
            "Date": [
                "2024-01-02",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
            ],
            "Open": [10.0, 10.0, None, 10.0, -1.0],
            "High": [11.0, 12.0, 12.0, 8.0, 2.0],
            "Low": [9.0, 9.0, 10.0, 9.0, -2.0],
            "Close": [10.5, 11.0, 11.0, 10.0, 1.0],
            "Volume": [1000, 1000, 0, 1000, 1000],
        }
    ).to_csv(path, index=False)

    audit = structural_audit_csv(path)

    assert audit.row_count == 5
    assert audit.duplicate_dates == 2
    assert audit.missing_required_values == 1
    assert audit.zero_volume_rows == 1
    assert audit.invalid_ohlc_rows == 1
    assert audit.nonpositive_price_rows == 1
    assert len(audit.largest_close_moves) > 0


def test_candidate_grid_count_is_correct() -> None:
    assert candidate_rule_count(grid_for_preset("quick")) == 432


def test_download_update_preserves_existing_history_for_short_range(tmp_path: Path) -> None:
    existing = _synthetic_ohlcv()
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    path = raw / "AAPL.csv"
    save_ohlcv_csv(existing, path)
    downloaded = existing.tail(30).copy()
    downloaded[["Open", "High", "Low", "Close"]] += 10.0

    result = download_daily_to_raw(
        tmp_path,
        "AAPL",
        start=downloaded.index.min().date().isoformat(),
        end=downloaded.index.max().date().isoformat(),
        downloader=_fixed_downloader(downloaded),
    )

    saved = load_ohlcv_csv(path)
    assert result.existing_rows == len(existing)
    assert result.downloaded_rows == 30
    assert result.replaced_dates == 30
    assert result.inserted_dates == 0
    assert result.final_rows == len(existing)
    assert saved.index.min() == existing.index.min()
    assert saved.index.max() == existing.index.max()
    assert saved.loc[downloaded.index[0], "Close"] == pytest.approx(downloaded.iloc[0]["Close"])


def test_download_update_replaces_overlap_once_and_keeps_unique_dates(tmp_path: Path) -> None:
    existing = _synthetic_ohlcv(rows=100)
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    path = raw / "AAPL.csv"
    save_ohlcv_csv(existing, path)
    future = _synthetic_ohlcv(
        start=(existing.index.max() + pd.offsets.BDay(1)).date().isoformat(),
        rows=5,
    )
    future[["Open", "High", "Low", "Close"]] += 100.0
    overlap = existing.tail(10).copy()
    overlap["Open"] = 998.0
    overlap["High"] = 1000.0
    overlap["Low"] = 997.0
    overlap["Close"] = 999.0
    downloaded = pd.concat([overlap, future], axis=0)

    result = download_daily_to_raw(
        tmp_path,
        "AAPL",
        start=downloaded.index.min().date().isoformat(),
        end=downloaded.index.max().date().isoformat(),
        downloader=_fixed_downloader(downloaded),
    )

    saved = load_ohlcv_csv(path)
    assert result.replaced_dates == 10
    assert result.inserted_dates == 5
    assert result.final_rows == len(existing) + 5
    assert not saved.index.has_duplicates
    assert saved.loc[existing.tail(1).index[0], "Close"] == pytest.approx(999.0)


def test_download_update_failed_validation_does_not_damage_original_csv(
    tmp_path: Path,
) -> None:
    existing = _synthetic_ohlcv(rows=100)
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    path = raw / "AAPL.csv"
    save_ohlcv_csv(existing, path)
    before = path.read_bytes()
    invalid = existing.tail(5).copy()
    invalid.iloc[0, invalid.columns.get_loc("Close")] = -1.0

    with pytest.raises(ValueError):
        download_daily_to_raw(
            tmp_path,
            "AAPL",
            start=invalid.index.min().date().isoformat(),
            end=invalid.index.max().date().isoformat(),
            downloader=_fixed_downloader(invalid),
        )

    assert path.read_bytes() == before


def test_download_update_does_not_mutate_unrelated_ticker_files(tmp_path: Path) -> None:
    existing = _synthetic_ohlcv(rows=100)
    unrelated = _synthetic_ohlcv(start="2021-01-04", rows=60)
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    save_ohlcv_csv(existing, raw / "AAPL.csv")
    unrelated_path = raw / "MSFT.csv"
    save_ohlcv_csv(unrelated, unrelated_path)
    before_unrelated = unrelated_path.read_bytes()
    downloaded = existing.tail(5).copy()
    downloaded[["Open", "High", "Low", "Close"]] += 2.0

    download_daily_to_raw(
        tmp_path,
        "AAPL",
        start=downloaded.index.min().date().isoformat(),
        end=downloaded.index.max().date().isoformat(),
        downloader=_fixed_downloader(downloaded),
    )

    assert unrelated_path.read_bytes() == before_unrelated


def test_research_report_naming_does_not_overwrite(tmp_path: Path) -> None:
    path = research_report_path(
        tmp_path,
        "AAPL",
        "2020-01-01",
        "2021-01-01",
        10,
        created_at=datetime(2026, 6, 19, tzinfo=UTC),
        unique_suffix="fixed",
    )

    save_research_report(pd.DataFrame({"a": [1]}), path)

    with pytest.raises(FileExistsError):
        save_research_report(pd.DataFrame({"a": [2]}), path)


def test_rsi_control_uses_14_30_only_as_control() -> None:
    rule = retail_control_rule()

    assert rule.length == 14
    assert rule.lower_level == 30.0


def test_walk_forward_aggregation_uses_test_metrics_only() -> None:
    folds = pd.DataFrame(
        [
            {
                "fold": 0,
                "status": "evaluated",
                "training_trade_count": 9_999,
                "training_score": 1_000_000.0,
                "test_trade_count": 10,
                "test_win_rate": 0.2,
                "test_mean_return": 0.01,
                "length": 8,
                "lower_level": 35.0,
                "slope_window": 1,
                "trigger_mode": "cross_above",
                "trend_filter": "none",
            },
            {
                "fold": 1,
                "status": "evaluated",
                "training_trade_count": 8_888,
                "training_score": 2_000_000.0,
                "test_trade_count": 30,
                "test_win_rate": 0.6,
                "test_mean_return": 0.03,
                "length": 8,
                "lower_level": 40.0,
                "slope_window": 1,
                "trigger_mode": "cross_above",
                "trend_filter": "none",
            },
            {"fold": 2, "status": "no_eligible_training_rule"},
        ]
    )

    aggregate = aggregate_walk_forward_results(folds)

    assert aggregate.folds_evaluated == 2
    assert aggregate.folds_without_eligible_rules == 1
    assert aggregate.total_unseen_trades == 40
    assert aggregate.weighted_unseen_win_rate == pytest.approx(0.5)
    assert aggregate.weighted_unseen_mean_return == pytest.approx(0.025)
    assert aggregate.median_fold_return == pytest.approx(0.02)
    assert aggregate.fraction_positive_test_folds == pytest.approx(1.0)


def test_date_window_selection_does_not_modify_raw_csv(
    tmp_path: Path,
    simple_ohlcv: pd.DataFrame,
) -> None:
    path = tmp_path / "AAPL.csv"
    save_ohlcv_csv(simple_ohlcv, path)
    before = path.read_bytes()

    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    _ = slice_date_window(frame, start="2020-03-01", end="2020-04-01")

    assert path.read_bytes() == before
