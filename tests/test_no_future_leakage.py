from __future__ import annotations

from pandas.testing import assert_frame_equal

from swing_rsi.features.labels import add_swing_labels, assert_no_label_features
from swing_rsi.features.price import build_price_features


def test_trailing_features_do_not_change_when_later_bars_change(simple_ohlcv) -> None:  # type: ignore[no-untyped-def]
    cutoff = 220
    original = build_price_features(simple_ohlcv)
    mutated = simple_ohlcv.copy()
    mutated.iloc[cutoff + 1 :, mutated.columns.get_loc("Close")] *= 2.0
    mutated.iloc[cutoff + 1 :, mutated.columns.get_loc("Open")] *= 2.0
    mutated.iloc[cutoff + 1 :, mutated.columns.get_loc("High")] *= 2.0
    mutated.iloc[cutoff + 1 :, mutated.columns.get_loc("Low")] *= 2.0
    changed = build_price_features(mutated)
    assert_frame_equal(original.iloc[: cutoff + 1], changed.iloc[: cutoff + 1])


def test_future_labels_are_explicit_and_incomplete_tail_is_nan(simple_ohlcv) -> None:  # type: ignore[no-untyped-def]
    labeled = add_swing_labels(simple_ohlcv, horizons=(10,))
    assert labeled["label_return_10d"].tail(10).isna().all()
    assert labeled["label_return_10d"].iloc[:-10].notna().all()


def test_label_columns_are_rejected_as_features() -> None:
    try:
        assert_no_label_features(["rsi_8", "label_return_10d"])
    except ValueError as exc:
        assert "label_return_10d" in str(exc)
    else:
        raise AssertionError("Expected label leakage guard to raise")
