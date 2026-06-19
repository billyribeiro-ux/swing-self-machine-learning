from __future__ import annotations

import csv

import pytest

from swing_rsi.forward.journal import (
    ForwardOutcome,
    ForwardSignal,
    append_outcome,
    append_signal,
)


def test_forward_records_are_append_only_and_separate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    signal_path = tmp_path / "signals.csv"
    outcome_path = tmp_path / "outcomes.csv"
    signal = ForwardSignal.create(
        signal_date="2026-06-19",
        ticker="AAPL",
        signal_type="BULLISH_RSI_SWING_REVERSAL_CANDIDATE",
        model_version="0.1.0",
        rule_id="abc123",
        rule_parameters={"length": 8, "lower_level": 35},
        confirmation_stack=["RSI reclaim"],
    )
    append_signal(signal_path, signal)
    with pytest.raises(ValueError, match="already contains"):
        append_signal(signal_path, signal)

    outcome = ForwardOutcome.create(
        signal_id=signal.signal_id,
        horizon_days=10,
        actual_return=0.04,
        mfe=0.06,
        mae=-0.02,
        result_label="POSITIVE",
    )
    append_outcome(outcome_path, outcome)
    with pytest.raises(ValueError, match="already contains"):
        append_outcome(outcome_path, outcome)

    with signal_path.open(newline="", encoding="utf-8") as handle:
        signal_rows = list(csv.DictReader(handle))
    with outcome_path.open(newline="", encoding="utf-8") as handle:
        outcome_rows = list(csv.DictReader(handle))
    assert len(signal_rows) == 1
    assert len(outcome_rows) == 1
    assert signal_rows[0]["signal_id"] == outcome_rows[0]["signal_id"]
