from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class ForwardSignal:
    signal_id: str
    created_at_utc: str
    signal_date: str
    ticker: str
    signal_type: str
    model_version: str
    rule_id: str
    rule_parameters: str
    confirmation_stack: str
    entry_reference: str
    stop_reference: str
    target_reference: str
    historical_trade_count: int | None
    historical_win_rate: float | None
    historical_average_return: float | None
    confidence_score: float | None
    notes: str

    @classmethod
    def create(
        cls,
        *,
        signal_date: str,
        ticker: str,
        signal_type: str,
        model_version: str,
        rule_id: str,
        rule_parameters: dict[str, object],
        confirmation_stack: list[str],
        entry_reference: str = "next_session_open",
        stop_reference: str = "research_only_not_set",
        target_reference: str = "research_only_fixed_horizon",
        historical_trade_count: int | None = None,
        historical_win_rate: float | None = None,
        historical_average_return: float | None = None,
        confidence_score: float | None = None,
        notes: str = "",
    ) -> ForwardSignal:
        identity = f"{signal_date}|{ticker.upper()}|{model_version}|{rule_id}"
        signal_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        return cls(
            signal_id=signal_id,
            created_at_utc=datetime.now(UTC).isoformat(),
            signal_date=signal_date,
            ticker=ticker.upper(),
            signal_type=signal_type,
            model_version=model_version,
            rule_id=rule_id,
            rule_parameters=json.dumps(rule_parameters, sort_keys=True),
            confirmation_stack=json.dumps(confirmation_stack),
            entry_reference=entry_reference,
            stop_reference=stop_reference,
            target_reference=target_reference,
            historical_trade_count=historical_trade_count,
            historical_win_rate=historical_win_rate,
            historical_average_return=historical_average_return,
            confidence_score=confidence_score,
            notes=notes,
        )


@dataclass(frozen=True)
class ForwardOutcome:
    signal_id: str
    evaluated_at_utc: str
    horizon_days: int
    actual_return: float
    mfe: float
    mae: float
    result_label: str
    notes: str = ""

    @classmethod
    def create(
        cls,
        *,
        signal_id: str,
        horizon_days: int,
        actual_return: float,
        mfe: float,
        mae: float,
        result_label: str,
        notes: str = "",
    ) -> ForwardOutcome:
        return cls(
            signal_id=signal_id,
            evaluated_at_utc=datetime.now(UTC).isoformat(),
            horizon_days=horizon_days,
            actual_return=actual_return,
            mfe=mfe,
            mae=mae,
            result_label=result_label,
            notes=notes,
        )


def _existing_keys(path: Path, fields: tuple[str, ...]) -> set[tuple[str, ...]]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {tuple(row[field] for field in fields) for row in csv.DictReader(handle)}


def _append_dataclass(
    path: Path, record: ForwardSignal | ForwardOutcome, unique_fields: tuple[str, ...]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = asdict(record)
    key = tuple(str(row[field]) for field in unique_fields)
    if key in _existing_keys(path, unique_fields):
        raise ValueError(f"Append-only journal already contains key {key}")

    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def append_signal(path: str | Path, signal: ForwardSignal) -> None:
    _append_dataclass(Path(path), signal, unique_fields=("signal_id",))


def append_outcome(path: str | Path, outcome: ForwardOutcome) -> None:
    _append_dataclass(Path(path), outcome, unique_fields=("signal_id", "horizon_days"))
