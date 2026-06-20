from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from numbers import Integral
from pathlib import Path
from typing import cast

import pandas as pd

from swing_rsi.data.validation import validate_ohlcv
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
    positions: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    for _, event in events.iterrows():
        payload = dict(event["payload"])
        source_id = str(payload.get("source_pending_event_id", event["event_id"]))
        key = (
            str(event["ticker"]),
            str(event["direction"]),
            str(event["model_id"]),
            str(event.get("scanner_snapshot_id", "")),
            source_id,
        )
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
            "signal_as_of_date": str(row["as_of_date"]),
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


def _next_session_after(frame: pd.DataFrame, as_of_date: str) -> pd.Timestamp | None:
    data = validate_ohlcv(frame)
    future_sessions = data.index[data.index > pd.Timestamp(as_of_date)]
    if future_sessions.empty:
        return None
    return pd.Timestamp(future_sessions[0])


def _trade_window_stats(
    frame: pd.DataFrame,
    *,
    direction: str,
    entry_date: str,
    entry_price: float,
    through_date: str,
) -> tuple[float, float, float]:
    data = validate_ohlcv(frame)
    window = data.loc[pd.Timestamp(entry_date) : pd.Timestamp(through_date)]
    if window.empty:
        return 0.0, 0.0, 0.0
    close_price = float(window["Close"].iloc[-1])
    if direction == "Bullish":
        mark_return = (close_price / entry_price) - 1.0
        mfe = (float(window["High"].max()) / entry_price) - 1.0
        mae = (float(window["Low"].min()) / entry_price) - 1.0
    else:
        mark_return = (entry_price / close_price) - 1.0
        mfe = (entry_price / float(window["Low"].min())) - 1.0
        mae = (entry_price / float(window["High"].max())) - 1.0
    return mark_return, mfe, mae


def _time_exit_date(
    frame: pd.DataFrame, *, signal_as_of_date: str, horizon: int
) -> pd.Timestamp | None:
    data = validate_ohlcv(frame)
    try:
        location = data.index.get_loc(pd.Timestamp(signal_as_of_date))
    except KeyError:
        return None
    if not isinstance(location, Integral):
        return None
    exit_position = int(location) + horizon
    if exit_position >= len(data):
        return None
    return pd.Timestamp(data.index[exit_position])


def advance_forward_positions(db_path: str | Path, frames: dict[str, pd.DataFrame]) -> int:
    events = list_forward_events(db_path)
    if events.empty:
        return 0
    inserted = 0

    pending_entries = events.loc[events["event_type"] == "ENTRY_PENDING"]
    for _, pending in pending_entries.iterrows():
        ticker = str(pending["ticker"])
        frame = frames.get(ticker)
        if frame is None:
            continue
        entry_date = _next_session_after(frame, str(pending["market_as_of_date"]))
        if entry_date is None:
            continue
        data = validate_ohlcv(frame)
        entry_price = float(cast(float, data.at[entry_date, "Open"]))
        pending_payload = dict(pending["payload"])
        payload = {
            **pending_payload,
            "source_pending_event_id": str(pending["event_id"]),
            "entry_date": entry_date.date().isoformat(),
            "entry_price": entry_price,
            "actual_paper_fill": entry_price,
            "fill_rule": "next_completed_session_open",
        }
        event = append_forward_event(
            db_path,
            event_type="ENTRY_FILLED",
            market_as_of_date=entry_date.date().isoformat(),
            ticker=ticker,
            direction=str(pending["direction"]),
            model_id=str(pending["model_id"]),
            scanner_snapshot_id=str(pending["scanner_snapshot_id"]),
            feature_snapshot_hash=str(pending["feature_snapshot_hash"]),
            payload=payload,
            unique_suffix=f"{pending['event_id']}|{pending_payload.get('horizon', '')}",
        )
        inserted += int(event.inserted)

    events = list_forward_events(db_path)
    filled_entries = events.loc[events["event_type"] == "ENTRY_FILLED"]
    exit_sources = {
        str(dict(event["payload"]).get("source_pending_event_id"))
        for _, event in events.loc[
            events["event_type"].isin({"EXIT_FILLED", "POSITION_EXPIRED"})
        ].iterrows()
    }
    for _, filled in filled_entries.iterrows():
        payload = dict(filled["payload"])
        source_id = str(payload.get("source_pending_event_id", filled["event_id"]))
        if source_id in exit_sources:
            continue
        ticker = str(filled["ticker"])
        frame = frames.get(ticker)
        if frame is None:
            continue
        data = validate_ohlcv(frame)
        entry_date_label = str(payload["entry_date"])
        horizon = int(payload.get("horizon", 0))
        signal_date = str(payload.get("signal_as_of_date", filled["market_as_of_date"]))
        exit_date = _time_exit_date(frame, signal_as_of_date=signal_date, horizon=horizon)
        latest_date = pd.Timestamp(data.index.max())
        last_mark_date = min(latest_date, exit_date) if exit_date is not None else latest_date
        mark_dates = data.index[
            (data.index >= pd.Timestamp(entry_date_label)) & (data.index <= last_mark_date)
        ]
        for mark_date in mark_dates:
            mark_return, mfe, mae = _trade_window_stats(
                frame,
                direction=str(filled["direction"]),
                entry_date=entry_date_label,
                entry_price=float(cast(float, payload["entry_price"])),
                through_date=mark_date.date().isoformat(),
            )
            mark_payload = {
                **payload,
                "mark_date": mark_date.date().isoformat(),
                "mark_return": mark_return,
                "mfe": mfe,
                "mae": mae,
            }
            event = append_forward_event(
                db_path,
                event_type="POSITION_MARKED",
                market_as_of_date=mark_date.date().isoformat(),
                ticker=ticker,
                direction=str(filled["direction"]),
                model_id=str(filled["model_id"]),
                scanner_snapshot_id=str(filled["scanner_snapshot_id"]),
                feature_snapshot_hash=str(filled["feature_snapshot_hash"]),
                payload=mark_payload,
                unique_suffix=f"{source_id}|{mark_date.date().isoformat()}",
            )
            inserted += int(event.inserted)
        if exit_date is not None and latest_date >= exit_date:
            realized_return, mfe, mae = _trade_window_stats(
                frame,
                direction=str(filled["direction"]),
                entry_date=entry_date_label,
                entry_price=float(cast(float, payload["entry_price"])),
                through_date=exit_date.date().isoformat(),
            )
            exit_payload = {
                **payload,
                "exit_date": exit_date.date().isoformat(),
                "exit_reason": "time_exit",
                "actual_paper_fill": float(cast(float, data.at[exit_date, "Close"])),
                "realized_return": realized_return,
                "mfe": mfe,
                "mae": mae,
            }
            event = append_forward_event(
                db_path,
                event_type="EXIT_FILLED",
                market_as_of_date=exit_date.date().isoformat(),
                ticker=ticker,
                direction=str(filled["direction"]),
                model_id=str(filled["model_id"]),
                scanner_snapshot_id=str(filled["scanner_snapshot_id"]),
                feature_snapshot_hash=str(filled["feature_snapshot_hash"]),
                payload=exit_payload,
                unique_suffix=source_id,
            )
            inserted += int(event.inserted)
    return inserted
