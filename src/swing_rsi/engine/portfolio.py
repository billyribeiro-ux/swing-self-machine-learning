from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from swing_rsi.data.validation import validate_ohlcv


@dataclass(frozen=True)
class PortfolioBacktestConfig:
    horizon: int = 10
    round_trip_cost_bps: float = 5.0
    slippage_bps: float = 2.0
    target_return: float | None = None
    stop_return: float | None = None
    max_concurrent_positions: int = 5
    max_position_per_symbol: int = 1
    equal_weight: bool = True
    conservative_intraday_ambiguity: bool = True


@dataclass(frozen=True)
class PortfolioBacktestResult:
    trades: pd.DataFrame
    equity: pd.DataFrame
    metrics: dict[str, float | int]


def _exit_trade(
    frame: pd.DataFrame,
    *,
    signal_position: int,
    direction: str,
    config: PortfolioBacktestConfig,
) -> dict[str, object] | None:
    data = validate_ohlcv(frame)
    entry_position = signal_position + 1
    if entry_position >= len(data):
        return None
    exit_limit = min(signal_position + config.horizon, len(data) - 1)
    if exit_limit <= entry_position:
        return None
    entry_price = float(data["Open"].iloc[entry_position])
    direction_sign = 1.0 if direction == "Bullish" else -1.0
    target_price = (
        entry_price * (1.0 + direction_sign * config.target_return)
        if config.target_return is not None
        else None
    )
    stop_price = (
        entry_price * (1.0 - direction_sign * config.stop_return)
        if config.stop_return is not None
        else None
    )
    exit_position = exit_limit
    exit_reason = "time_exit"
    exit_price = float(data["Close"].iloc[exit_limit])
    for position in range(entry_position, exit_limit + 1):
        high = float(data["High"].iloc[position])
        low = float(data["Low"].iloc[position])
        target_hit = False
        stop_hit = False
        if direction == "Bullish":
            target_hit = target_price is not None and high >= target_price
            stop_hit = stop_price is not None and low <= stop_price
        else:
            target_hit = target_price is not None and low <= target_price
            stop_hit = stop_price is not None and high >= stop_price
        if target_hit and stop_hit and config.conservative_intraday_ambiguity:
            assert stop_price is not None
            exit_position = position
            exit_reason = "stop_intraday_ambiguous"
            exit_price = float(stop_price)
            break
        if stop_hit:
            assert stop_price is not None
            exit_position = position
            exit_reason = "stop"
            exit_price = float(stop_price)
            break
        if target_hit:
            assert target_price is not None
            exit_position = position
            exit_reason = "target"
            exit_price = float(target_price)
            break
    gross = direction_sign * ((exit_price / entry_price) - 1.0)
    costs = (config.round_trip_cost_bps + config.slippage_bps) / 10_000.0
    window = data.iloc[entry_position : exit_position + 1]
    if direction == "Bullish":
        mfe = (float(window["High"].max()) / entry_price) - 1.0
        mae = (float(window["Low"].min()) / entry_price) - 1.0
    else:
        mfe = (entry_price / float(window["Low"].min())) - 1.0
        mae = (entry_price / float(window["High"].max())) - 1.0
    return {
        "signal_date": data.index[signal_position].date().isoformat(),
        "entry_date": data.index[entry_position].date().isoformat(),
        "exit_date": data.index[exit_position].date().isoformat(),
        "direction": direction,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "gross_return": gross,
        "net_return": gross - costs,
        "mfe": mfe,
        "mae": mae,
    }


def backtest_scanner_candidates(
    frames: dict[str, pd.DataFrame],
    candidate_rows: pd.DataFrame,
    *,
    config: PortfolioBacktestConfig | None = None,
) -> PortfolioBacktestResult:
    config = config or PortfolioBacktestConfig()
    if candidate_rows.empty:
        return PortfolioBacktestResult(pd.DataFrame(), pd.DataFrame(), {"trade_count": 0})
    candidates = candidate_rows.sort_values(
        ["as_of_date", "composite_utility_score"],
        ascending=[True, False],
    )
    open_by_symbol: dict[str, int] = {}
    open_until: list[pd.Timestamp] = []
    trades: list[dict[str, object]] = []
    for _, candidate in candidates.iterrows():
        if candidate.get("candidate_status") != "ACTIONABLE_PAPER_CANDIDATE":
            continue
        ticker = str(candidate["ticker"])
        if open_by_symbol.get(ticker, 0) >= config.max_position_per_symbol:
            continue
        signal_date = pd.Timestamp(candidate["as_of_date"])
        open_until = [date for date in open_until if date > signal_date]
        if len(open_until) >= config.max_concurrent_positions:
            continue
        frame = frames.get(ticker)
        if frame is None:
            continue
        data = validate_ohlcv(frame)
        positions = np.where(data.index == signal_date)[0]
        if len(positions) == 0:
            continue
        trade = _exit_trade(
            data,
            signal_position=int(positions[0]),
            direction=str(candidate["direction"]),
            config=config,
        )
        if trade is None:
            continue
        trade["ticker"] = ticker
        trade["model_id"] = candidate.get("model_id", "")
        trade["sector"] = candidate.get("sector", "")
        trades.append(trade)
        open_until.append(pd.Timestamp(str(trade["exit_date"])))
        open_by_symbol[ticker] = open_by_symbol.get(ticker, 0) + 1

    ledger = pd.DataFrame(trades)
    if ledger.empty:
        return PortfolioBacktestResult(ledger, pd.DataFrame(), {"trade_count": 0})
    returns = pd.to_numeric(ledger["net_return"], errors="coerce").fillna(0.0)
    equity = pd.DataFrame(
        {
            "trade_number": range(1, len(returns) + 1),
            "equity": (1.0 + returns).cumprod(),
        }
    )
    equity["drawdown"] = (equity["equity"] / equity["equity"].cummax()) - 1.0
    negative = returns[returns < 0]
    metrics: dict[str, float | int] = {
        "trade_count": len(ledger),
        "total_return": float(equity["equity"].iloc[-1] - 1.0),
        "win_rate": float((returns > 0).mean()),
        "expectancy": float(returns.mean()),
        "profit_factor": float(returns[returns > 0].sum() / abs(negative.sum()))
        if float(negative.sum()) < 0
        else math.inf,
        "max_drawdown": float(equity["drawdown"].min()),
        "average_mfe": float(pd.to_numeric(ledger["mfe"]).mean()),
        "average_mae": float(pd.to_numeric(ledger["mae"]).mean()),
        "turnover": float(len(ledger)),
        "exposure": float(min(1.0, len(ledger) / max(len(candidate_rows), 1))),
    }
    return PortfolioBacktestResult(ledger, equity, metrics)
