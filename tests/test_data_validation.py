from __future__ import annotations

import pytest

from swing_rsi.data.validation import validate_ohlcv


def test_valid_frame_is_sorted(simple_ohlcv) -> None:  # type: ignore[no-untyped-def]
    result = validate_ohlcv(simple_ohlcv.sort_index(ascending=False))
    assert result.index.is_monotonic_increasing


def test_invalid_high_low_is_rejected(simple_ohlcv) -> None:  # type: ignore[no-untyped-def]
    frame = simple_ohlcv.copy()
    frame.iloc[10, frame.columns.get_loc("High")] = frame.iloc[10]["Low"] - 1
    with pytest.raises(ValueError, match="High cannot be below low"):
        validate_ohlcv(frame)
