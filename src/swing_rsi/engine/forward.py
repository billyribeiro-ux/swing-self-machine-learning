from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from numbers import Integral
from pathlib import Path
from typing import Any, cast

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


def _jsonable(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return cast(Any, value).isoformat()
    try:
        if bool(pd.isna(cast(Any, value))):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return cast(Any, value).item()
    return value


def _event_name(event_prefix: str, event_type: str) -> str:
    return f"{event_prefix}{event_type}" if event_prefix else event_type


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


def create_pending_events_from_snapshot(
    db_path: str | Path,
    scanner_rows: pd.DataFrame,
    *,
    event_prefix: str = "",
    payload_extra: dict[str, object] | None = None,
    include_row_payload: bool = False,
) -> int:
    count = 0
    payload_extra = payload_extra or {}
    for _, row in scanner_rows.iterrows():
        if row.get("candidate_status") != "ACTIONABLE_PAPER_CANDIDATE":
            payload: dict[str, object] = {
                **payload_extra,
                "exclusion_reason": str(row.get("exclusion_reason", "")),
            }
            if include_row_payload:
                payload["scanner_row"] = _jsonable(row.to_dict())
            event = append_forward_event(
                db_path,
                event_type=_event_name(event_prefix, "SIGNAL_REJECTED"),
                market_as_of_date=str(row["as_of_date"]),
                ticker=str(row["ticker"]),
                direction=str(row["direction"]),
                model_id=str(row["model_id"]),
                scanner_snapshot_id=str(row["scan_id"]),
                feature_snapshot_hash=str(row["feature_snapshot_hash"]),
                payload=payload,
                unique_suffix=str(row["horizon"]),
            )
            count += int(event.inserted)
            continue
        expected_return = float(row["expected_return"])
        expected_mfe = float(row["expected_mfe"])
        expected_mae = float(row["expected_mae"])
        signal_close = row.get("signal_close")
        signal_price_context = (
            None if signal_close is None or pd.isna(signal_close) else float(signal_close)
        )
        planned_target_return = max(expected_return, max(expected_mfe, 0.0) * 0.5, 0.005)
        planned_stop_return = max(abs(expected_mae), 0.005)
        payload = {
            **payload_extra,
            "entry_rule": "next_completed_session_open",
            "signal_price_context": signal_price_context,
            "planned_stop_return": planned_stop_return,
            "planned_target_return": planned_target_return,
            "planned_stop": "entry_price_adjusted_after_next_open_fill",
            "planned_target": "entry_price_adjusted_after_next_open_fill",
            "planned_round_trip_cost_bps": 5.0,
            "signal_as_of_date": str(row["as_of_date"]),
            "expected_return": expected_return,
            "expected_mfe": expected_mfe,
            "expected_mae": expected_mae,
            "calibrated_probability": float(row["calibrated_probability"]),
            "horizon": int(row["horizon"]),
        }
        if include_row_payload:
            payload["scanner_row"] = _jsonable(row.to_dict())
        signal = append_forward_event(
            db_path,
            event_type=_event_name(event_prefix, "SIGNAL_CREATED"),
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
            event_type=_event_name(event_prefix, "ENTRY_PENDING"),
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


def _risk_policy_prices(
    *,
    direction: str,
    entry_price: float,
    payload: dict[str, object],
) -> tuple[float | None, float | None]:
    target_return = float(cast(float, payload.get("planned_target_return", 0.0) or 0.0))
    stop_return = float(cast(float, payload.get("planned_stop_return", 0.0) or 0.0))
    target_price: float | None = None
    stop_price: float | None = None
    if target_return > 0:
        target_price = (
            entry_price * (1.0 + target_return)
            if direction == "Bullish"
            else entry_price * (1.0 - target_return)
        )
    if stop_return > 0:
        stop_price = (
            entry_price * (1.0 - stop_return)
            if direction == "Bullish"
            else entry_price * (1.0 + stop_return)
        )
    return target_price, stop_price


def _first_policy_exit(
    frame: pd.DataFrame,
    *,
    direction: str,
    entry_date: str,
    entry_price: float,
    through_date: str,
    payload: dict[str, object],
) -> tuple[pd.Timestamp, str, float] | None:
    target_price, stop_price = _risk_policy_prices(
        direction=direction,
        entry_price=entry_price,
        payload=payload,
    )
    if target_price is None and stop_price is None:
        return None
    data = validate_ohlcv(frame)
    window = data.loc[pd.Timestamp(entry_date) : pd.Timestamp(through_date)]
    for index, bar in window.iterrows():
        high = float(bar["High"])
        low = float(bar["Low"])
        if direction == "Bullish":
            target_hit = target_price is not None and high >= target_price
            stop_hit = stop_price is not None and low <= stop_price
        else:
            target_hit = target_price is not None and low <= target_price
            stop_hit = stop_price is not None and high >= stop_price
        if target_hit and stop_hit:
            assert stop_price is not None
            return pd.Timestamp(str(index)), "stop_intraday_ambiguous", float(stop_price)
        if stop_hit:
            assert stop_price is not None
            return pd.Timestamp(str(index)), "stop", float(stop_price)
        if target_hit:
            assert target_price is not None
            return pd.Timestamp(str(index)), "target", float(target_price)
    return None


def _realized_return_from_price(
    *,
    direction: str,
    entry_price: float,
    exit_price: float,
    cost_bps: float,
) -> tuple[float, float]:
    gross = (
        (exit_price / entry_price) - 1.0
        if direction == "Bullish"
        else (entry_price / exit_price) - 1.0
    )
    costs = cost_bps / 10_000.0
    return gross, gross - costs


def advance_forward_positions(
    db_path: str | Path,
    frames: dict[str, pd.DataFrame],
    *,
    event_prefix: str = "",
) -> int:
    events = list_forward_events(db_path)
    if events.empty:
        return 0
    inserted = 0

    pending_entries = events.loc[events["event_type"] == _event_name(event_prefix, "ENTRY_PENDING")]
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
        target_price, stop_price = _risk_policy_prices(
            direction=str(pending["direction"]),
            entry_price=entry_price,
            payload=payload,
        )
        payload["planned_target_price"] = target_price
        payload["planned_stop_price"] = stop_price
        event = append_forward_event(
            db_path,
            event_type=_event_name(event_prefix, "ENTRY_FILLED"),
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
        for event_type, price_key in (
            ("TARGET_UPDATED", "planned_target_price"),
            ("STOP_UPDATED", "planned_stop_price"),
        ):
            price = payload.get(price_key)
            if price is None:
                continue
            policy_event = append_forward_event(
                db_path,
                event_type=_event_name(event_prefix, event_type),
                market_as_of_date=entry_date.date().isoformat(),
                ticker=ticker,
                direction=str(pending["direction"]),
                model_id=str(pending["model_id"]),
                scanner_snapshot_id=str(pending["scanner_snapshot_id"]),
                feature_snapshot_hash=str(pending["feature_snapshot_hash"]),
                payload={
                    **payload,
                    "policy_event": event_type,
                    "frozen_price": float(cast(float, price)),
                },
                unique_suffix=f"{pending['event_id']}|{event_type}",
            )
            inserted += int(policy_event.inserted)

    events = list_forward_events(db_path)
    filled_entries = events.loc[events["event_type"] == _event_name(event_prefix, "ENTRY_FILLED")]
    exit_sources = {
        str(dict(event["payload"]).get("source_pending_event_id"))
        for _, event in events.loc[
            events["event_type"].isin(
                {
                    _event_name(event_prefix, "EXIT_FILLED"),
                    _event_name(event_prefix, "POSITION_EXPIRED"),
                }
            )
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
        policy_exit = _first_policy_exit(
            frame,
            direction=str(filled["direction"]),
            entry_date=entry_date_label,
            entry_price=float(cast(float, payload["entry_price"])),
            through_date=last_mark_date.date().isoformat(),
            payload=payload,
        )
        actual_exit_date = exit_date
        actual_exit_reason = "time_exit"
        actual_exit_price: float | None = None
        if policy_exit is not None:
            actual_exit_date, actual_exit_reason, actual_exit_price = policy_exit
        if actual_exit_date is not None:
            last_mark_date = min(last_mark_date, actual_exit_date)
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
                event_type=_event_name(event_prefix, "POSITION_MARKED"),
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
        if actual_exit_date is not None and latest_date >= actual_exit_date:
            exit_price = (
                actual_exit_price
                if actual_exit_price is not None
                else float(cast(float, data.at[actual_exit_date, "Close"]))
            )
            realized_return, mfe, mae = _trade_window_stats(
                frame,
                direction=str(filled["direction"]),
                entry_date=entry_date_label,
                entry_price=float(cast(float, payload["entry_price"])),
                through_date=actual_exit_date.date().isoformat(),
            )
            gross_return, net_return = _realized_return_from_price(
                direction=str(filled["direction"]),
                entry_price=float(cast(float, payload["entry_price"])),
                exit_price=float(exit_price),
                cost_bps=float(payload.get("planned_round_trip_cost_bps", 0.0) or 0.0),
            )
            exit_payload = {
                **payload,
                "exit_date": actual_exit_date.date().isoformat(),
                "exit_reason": actual_exit_reason,
                "actual_paper_fill": float(exit_price),
                "mark_to_close_return": realized_return,
                "realized_return": gross_return,
                "net_realized_return": net_return,
                "mfe": mfe,
                "mae": mae,
            }
            event = append_forward_event(
                db_path,
                event_type=_event_name(event_prefix, "EXIT_FILLED"),
                market_as_of_date=actual_exit_date.date().isoformat(),
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
