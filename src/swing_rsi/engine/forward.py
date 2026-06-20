from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from swing_rsi.engine.storage import dumps, engine_connection, loads


@dataclass(frozen=True)
class ForwardEvent:
    event_id: str
    unique_key: str
    event_type: str
    event_time_utc: str
    market_as_of_date: str
    ticker: str
    direction: str
    model_id: str
    scanner_snapshot_id: str | None
    feature_snapshot_hash: str | None
    payload: dict[str, object]
    inserted: bool


def make_event_id(unique_key: str) -> str:
    return hashlib.sha256(unique_key.encode("utf-8")).hexdigest()[:24]


def append_forward_event(
    db_path: str | Path,
    *,
    event_type: str,
    market_as_of_date: str,
    ticker: str,
    direction: str,
    model_id: str,
    scanner_snapshot_id: str | None,
    feature_snapshot_hash: str | None,
    payload: dict[str, object],
    unique_suffix: str = "",
) -> ForwardEvent:
    unique_key = "|".join(
        [
            event_type,
            market_as_of_date,
            ticker.upper(),
            direction,
            model_id,
            scanner_snapshot_id or "",
            unique_suffix,
        ]
    )
    event = ForwardEvent(
        event_id=make_event_id(unique_key),
        unique_key=unique_key,
        event_type=event_type,
        event_time_utc=datetime.now(UTC).isoformat(),
        market_as_of_date=market_as_of_date,
        ticker=ticker.upper(),
        direction=direction,
        model_id=model_id,
        scanner_snapshot_id=scanner_snapshot_id,
        feature_snapshot_hash=feature_snapshot_hash,
        payload=payload,
        inserted=False,
    )
    with engine_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO forward_events (
                event_id, unique_key, event_type, event_time_utc, market_as_of_date,
                ticker, direction, model_id, scanner_snapshot_id, feature_snapshot_hash, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.unique_key,
                event.event_type,
                event.event_time_utc,
                event.market_as_of_date,
                event.ticker,
                event.direction,
                event.model_id,
                event.scanner_snapshot_id,
                event.feature_snapshot_hash,
                dumps(event.payload),
            ),
        )
    return ForwardEvent(
        event_id=event.event_id,
        unique_key=event.unique_key,
        event_type=event.event_type,
        event_time_utc=event.event_time_utc,
        market_as_of_date=event.market_as_of_date,
        ticker=event.ticker,
        direction=event.direction,
        model_id=event.model_id,
        scanner_snapshot_id=event.scanner_snapshot_id,
        feature_snapshot_hash=event.feature_snapshot_hash,
        payload=event.payload,
        inserted=cursor.rowcount == 1,
    )


def list_forward_events(db_path: str | Path) -> pd.DataFrame:
    with engine_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM forward_events ORDER BY event_time_utc, event_id"
        ).fetchall()
    if not rows:
        return pd.DataFrame()
    records: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = loads(str(item.pop("payload_json")))
        records.append(item)
    return pd.DataFrame(records)


def reconstruct_positions(db_path: str | Path) -> pd.DataFrame:
    events = list_forward_events(db_path)
    if events.empty:
        return pd.DataFrame()
    positions: dict[tuple[str, str, str], dict[str, object]] = {}
    for _, event in events.iterrows():
        key = (str(event["ticker"]), str(event["direction"]), str(event["model_id"]))
        payload = dict(event["payload"])
        if event["event_type"] in {"SIGNAL_CREATED", "ENTRY_PENDING", "ENTRY_FILLED"}:
            positions[key] = {
                "ticker": event["ticker"],
                "direction": event["direction"],
                "model_id": event["model_id"],
                "scanner_snapshot_id": event["scanner_snapshot_id"],
                "status": event["event_type"],
                **payload,
            }
        elif (
            event["event_type"] in {"EXIT_FILLED", "POSITION_EXPIRED", "POSITION_CANCELED"}
            and key in positions
        ):
            positions[key]["status"] = event["event_type"]
            positions[key].update(payload)
    return pd.DataFrame(positions.values())


def create_pending_events_from_snapshot(db_path: str | Path, scanner_rows: pd.DataFrame) -> int:
    count = 0
    for _, row in scanner_rows.iterrows():
        if row.get("candidate_status") != "ACTIONABLE_PAPER_CANDIDATE":
            event = append_forward_event(
                db_path,
                event_type="SIGNAL_REJECTED",
                market_as_of_date=str(row["as_of_date"]),
                ticker=str(row["ticker"]),
                direction=str(row["direction"]),
                model_id=str(row["model_id"]),
                scanner_snapshot_id=str(row["scan_id"]),
                feature_snapshot_hash=str(row["feature_snapshot_hash"]),
                payload={"exclusion_reason": str(row.get("exclusion_reason", ""))},
                unique_suffix=str(row["horizon"]),
            )
            count += int(event.inserted)
            continue
        payload = {
            "entry_rule": "next_completed_session_open",
            "planned_stop": "frozen_model_policy_at_signal_time",
            "planned_target": "frozen_model_policy_at_signal_time",
            "expected_return": float(row["expected_return"]),
            "expected_mfe": float(row["expected_mfe"]),
            "expected_mae": float(row["expected_mae"]),
            "calibrated_probability": float(row["calibrated_probability"]),
            "horizon": int(row["horizon"]),
        }
        signal = append_forward_event(
            db_path,
            event_type="SIGNAL_CREATED",
            market_as_of_date=str(row["as_of_date"]),
            ticker=str(row["ticker"]),
            direction=str(row["direction"]),
            model_id=str(row["model_id"]),
            scanner_snapshot_id=str(row["scan_id"]),
            feature_snapshot_hash=str(row["feature_snapshot_hash"]),
            payload=payload,
            unique_suffix=str(row["horizon"]),
        )
        pending = append_forward_event(
            db_path,
            event_type="ENTRY_PENDING",
            market_as_of_date=str(row["as_of_date"]),
            ticker=str(row["ticker"]),
            direction=str(row["direction"]),
            model_id=str(row["model_id"]),
            scanner_snapshot_id=str(row["scan_id"]),
            feature_snapshot_hash=str(row["feature_snapshot_hash"]),
            payload=payload,
            unique_suffix=str(row["horizon"]),
        )
        count += int(signal.inserted) + int(pending.inserted)
    return count
