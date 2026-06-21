from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd

from swing_rsi.data.validation import validate_ohlcv
from swing_rsi.engine.selection import order_candidates


@dataclass(frozen=True)
class PortfolioBacktestConfig:
    horizon: int = 10
    round_trip_cost_bps: float = 5.0
    slippage_bps: float = 2.0
    target_return: float | None = None
    stop_return: float | None = None
    trailing_stop_return: float | None = None
    max_concurrent_positions: int = 5
    max_position_per_symbol: int = 1
    max_sector_fraction: float = 0.5
    max_gross_exposure: float = 1.0
    max_net_exposure: float = 1.0
    equal_weight: bool = True
    volatility_adjusted_position_sizing: bool = False
    conservative_intraday_ambiguity: bool = True


@dataclass(frozen=True)
class PortfolioBacktestResult:
    trades: pd.DataFrame
    equity: pd.DataFrame
    metrics: dict[str, float | int]
    yearly_returns: pd.DataFrame
    regime_returns: pd.DataFrame
    sector_returns: pd.DataFrame
    symbol_returns: pd.DataFrame
    model_version_returns: pd.DataFrame
    candidate_audit: pd.DataFrame


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
    peak_price = entry_price
    trough_price = entry_price
    for position in range(entry_position, exit_limit + 1):
        high = float(data["High"].iloc[position])
        low = float(data["Low"].iloc[position])
        peak_price = max(peak_price, high)
        trough_price = min(trough_price, low)
        target_hit = False
        stop_hit = False
        trailing_stop_hit = False
        if direction == "Bullish":
            target_hit = target_price is not None and high >= target_price
            stop_hit = stop_price is not None and low <= stop_price
            trailing_price = (
                peak_price * (1.0 - config.trailing_stop_return)
                if config.trailing_stop_return is not None
                else None
            )
            trailing_stop_hit = trailing_price is not None and low <= trailing_price
        else:
            target_hit = target_price is not None and low <= target_price
            stop_hit = stop_price is not None and high >= stop_price
            trailing_price = (
                trough_price * (1.0 + config.trailing_stop_return)
                if config.trailing_stop_return is not None
                else None
            )
            trailing_stop_hit = trailing_price is not None and high >= trailing_price
        if (
            (target_hit and stop_hit)
            or (target_hit and trailing_stop_hit)
            or (stop_hit and trailing_stop_hit)
        ) and config.conservative_intraday_ambiguity:
            conservative_price = stop_price if stop_hit else trailing_price
            assert conservative_price is not None
            exit_position = position
            exit_reason = "stop_intraday_ambiguous"
            exit_price = float(conservative_price)
            break
        if stop_hit:
            assert stop_price is not None
            exit_position = position
            exit_reason = "stop"
            exit_price = float(stop_price)
            break
        if trailing_stop_hit:
            assert trailing_price is not None
            exit_position = position
            exit_reason = "trailing_stop"
            exit_price = float(trailing_price)
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


def _empty_result() -> PortfolioBacktestResult:
    return PortfolioBacktestResult(
        pd.DataFrame(),
        pd.DataFrame(),
        {"trade_count": 0},
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )


def _position_weight(frame: pd.DataFrame, config: PortfolioBacktestConfig) -> float:
    base = 1.0 / max(config.max_concurrent_positions, 1)
    if not config.volatility_adjusted_position_sizing:
        return base
    data = validate_ohlcv(frame)
    realized = data["Close"].pct_change().rolling(20, min_periods=10).std().iloc[-1]
    if pd.isna(realized) or float(realized) <= 0:
        return base
    target_daily_volatility = 0.015
    return float(
        min(
            base,
            target_daily_volatility / float(realized) / max(config.max_concurrent_positions, 1),
        )
    )


def _daily_equity(ledger: pd.DataFrame, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame()
    start = pd.Timestamp(ledger["entry_date"].min())
    end = pd.Timestamp(ledger["exit_date"].max())
    sessions = sorted(
        {
            pd.Timestamp(index)
            for frame in frames.values()
            for index in validate_ohlcv(frame).index
            if start <= pd.Timestamp(index) <= end
        }
    )
    if not sessions:
        sessions = list(pd.date_range(start, end, freq="B"))
    daily = pd.DataFrame({"Date": sessions})
    daily["daily_return"] = 0.0
    daily["gross_exposure"] = 0.0
    daily["net_exposure"] = 0.0
    for _, trade in ledger.iterrows():
        ticker = str(trade["ticker"])
        frame = frames.get(ticker)
        if frame is None:
            continue
        data = validate_ohlcv(frame)
        entry_date = pd.Timestamp(str(trade["entry_date"]))
        exit_date = pd.Timestamp(str(trade["exit_date"]))
        weight = float(trade.get("position_weight", 0.0))
        direction_sign = 1.0 if str(trade["direction"]) == "Bullish" else -1.0
        open_mask = (daily["Date"] >= entry_date) & (daily["Date"] <= exit_date)
        daily.loc[open_mask, "gross_exposure"] += abs(weight)
        daily.loc[open_mask, "net_exposure"] += direction_sign * weight
        sessions = [pd.Timestamp(value) for value in daily.loc[open_mask, "Date"]]
        previous_price = float(trade["entry_price"])
        total_cost = float(trade["gross_return"]) - float(trade["net_return"])
        for session in sessions:
            if session == exit_date:
                mark_price = float(trade["exit_price"])
            elif session in data.index:
                mark_price = float(cast(float, data.at[session, "Close"]))
            else:
                continue
            if previous_price <= 0:
                continue
            period_return = direction_sign * ((mark_price / previous_price) - 1.0)
            if session == exit_date:
                period_return -= total_cost
            daily.loc[daily["Date"] == session, "daily_return"] += weight * period_return
            previous_price = mark_price
    daily["equity"] = (1.0 + daily["daily_return"]).cumprod()
    daily["drawdown"] = (daily["equity"] / daily["equity"].cummax()) - 1.0
    daily["Date"] = daily["Date"].dt.date.astype(str)
    return daily


def _group_returns(ledger: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    if ledger.empty or column not in ledger:
        return pd.DataFrame(columns=[label, "trade_count", "weighted_net_return"])
    grouped = (
        ledger.assign(weighted_net_return=pd.to_numeric(ledger["weighted_net_return"]))
        .groupby(column, dropna=False)
        .agg(
            trade_count=("weighted_net_return", "size"),
            weighted_net_return=("weighted_net_return", "sum"),
        )
        .reset_index()
        .rename(columns={column: label})
    )
    return grouped


def backtest_scanner_candidates(
    frames: dict[str, pd.DataFrame],
    candidate_rows: pd.DataFrame,
    *,
    config: PortfolioBacktestConfig | None = None,
) -> PortfolioBacktestResult:
    config = config or PortfolioBacktestConfig()
    if candidate_rows.empty:
        return _empty_result()
    candidates = order_candidates(candidate_rows, date_column="as_of_date")
    open_positions: list[dict[str, object]] = []
    trades: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    for as_of_date, date_candidates in candidates.groupby("as_of_date", sort=True):
        signal_date = pd.Timestamp(str(as_of_date))
        open_positions = [
            position
            for position in open_positions
            if pd.Timestamp(str(position["exit_date"])) > signal_date
        ]
        for _, candidate in date_candidates.iterrows():
            audit: dict[str, object] = {
                "as_of_date": candidate.get("as_of_date", ""),
                "ticker": candidate.get("ticker", ""),
                "direction": candidate.get("direction", ""),
                "model_id": candidate.get("model_id", ""),
                "candidate_status": candidate.get("candidate_status", ""),
                "included_as_trade": False,
                "audit_reason": "",
            }
            if candidate.get("candidate_status") != "ACTIONABLE_PAPER_CANDIDATE":
                audit["audit_reason"] = candidate.get("exclusion_reason", "candidate_rejected")
                audit_rows.append(audit)
                continue
            ticker = str(candidate["ticker"])
            symbol_open_count = sum(
                1 for position in open_positions if position["ticker"] == ticker
            )
            if symbol_open_count >= config.max_position_per_symbol:
                audit["audit_reason"] = "max_position_per_symbol"
                audit_rows.append(audit)
                continue
            if len(open_positions) >= config.max_concurrent_positions:
                audit["audit_reason"] = "max_concurrent_positions"
                audit_rows.append(audit)
                continue
            sector = str(candidate.get("sector", "unknown"))
            sector_count = sum(1 for position in open_positions if position.get("sector") == sector)
            if (sector_count + 1) / max(
                config.max_concurrent_positions, 1
            ) > config.max_sector_fraction:
                audit["audit_reason"] = "sector_concentration_limit"
                audit_rows.append(audit)
                continue
            frame = frames.get(ticker)
            if frame is None:
                audit["audit_reason"] = "missing_symbol_frame"
                audit_rows.append(audit)
                continue
            data = validate_ohlcv(frame)
            positions = np.where(data.index == signal_date)[0]
            if len(positions) == 0:
                audit["audit_reason"] = "signal_date_not_in_frame"
                audit_rows.append(audit)
                continue
            trade = _exit_trade(
                data,
                signal_position=int(positions[0]),
                direction=str(candidate["direction"]),
                config=config,
            )
            if trade is None:
                audit["audit_reason"] = "no_future_entry_or_exit_bar"
                audit_rows.append(audit)
                continue
            weight = _position_weight(data, config)
            direction_sign = 1.0 if trade["direction"] == "Bullish" else -1.0
            projected_gross = sum(
                abs(float(cast(float, position["weight"]))) for position in open_positions
            ) + abs(weight)
            projected_net = (
                sum(
                    float(cast(float, position["weight"]))
                    * float(cast(float, position["direction_sign"]))
                    for position in open_positions
                )
                + weight * direction_sign
            )
            if (
                projected_gross > config.max_gross_exposure
                or abs(projected_net) > config.max_net_exposure
            ):
                audit["audit_reason"] = "exposure_limit"
                audit_rows.append(audit)
                continue
            trade["ticker"] = ticker
            trade["model_id"] = candidate.get("model_id", "")
            trade["sector"] = candidate.get("sector", "")
            trade["regime"] = candidate.get("regime", "")
            trade["model_version"] = candidate.get("model_id", "")
            trade["position_weight"] = weight
            trade["weighted_net_return"] = float(cast(float, trade["net_return"])) * weight
            trades.append(trade)
            audit["included_as_trade"] = True
            audit["audit_reason"] = "included"
            audit["entry_date"] = trade["entry_date"]
            audit["exit_date"] = trade["exit_date"]
            audit["net_return"] = trade["net_return"]
            audit_rows.append(audit)
            open_positions.append(
                {
                    "ticker": ticker,
                    "sector": sector,
                    "exit_date": str(trade["exit_date"]),
                    "weight": weight,
                    "direction_sign": direction_sign,
                }
            )

    ledger = pd.DataFrame(trades)
    if ledger.empty:
        empty = _empty_result()
        return PortfolioBacktestResult(
            empty.trades,
            empty.equity,
            empty.metrics,
            empty.yearly_returns,
            empty.regime_returns,
            empty.sector_returns,
            empty.symbol_returns,
            empty.model_version_returns,
            pd.DataFrame(audit_rows),
        )
    returns = pd.to_numeric(ledger["net_return"], errors="coerce").fillna(0.0)
    weighted_returns = pd.to_numeric(ledger["weighted_net_return"], errors="coerce").fillna(0.0)
    equity = _daily_equity(ledger, frames)
    negative = returns[returns < 0]
    daily_returns = (
        pd.to_numeric(equity["daily_return"], errors="coerce").fillna(0.0)
        if not equity.empty
        else pd.Series(dtype=float)
    )
    downside = daily_returns[daily_returns < 0]
    annualized_return = (
        float(equity["equity"].iloc[-1] ** (252 / max(len(equity), 1)) - 1.0)
        if not equity.empty
        else 0.0
    )
    volatility = float(daily_returns.std(ddof=0) * math.sqrt(252)) if len(daily_returns) else 0.0
    downside_volatility = float(downside.std(ddof=0) * math.sqrt(252)) if len(downside) else 0.0
    underwater = equity.loc[equity["drawdown"] < 0].copy() if not equity.empty else pd.DataFrame()
    recovery_time = len(underwater) if not underwater.empty else 0
    metrics: dict[str, float | int] = {
        "trade_count": len(ledger),
        "total_return": float(equity["equity"].iloc[-1] - 1.0),
        "annualized_return": annualized_return,
        "volatility": volatility,
        "sharpe": float(annualized_return / volatility) if volatility > 0 else 0.0,
        "sortino": float(annualized_return / downside_volatility)
        if downside_volatility > 0
        else 0.0,
        "win_rate": float((returns > 0).mean()),
        "expectancy": float(returns.mean()),
        "weighted_expectancy": float(weighted_returns.mean()),
        "profit_factor": float(returns[returns > 0].sum() / abs(negative.sum()))
        if float(negative.sum()) < 0
        else math.inf,
        "max_drawdown": float(equity["drawdown"].min()),
        "recovery_time_sessions": recovery_time,
        "average_mfe": float(pd.to_numeric(ledger["mfe"]).mean()),
        "average_mae": float(pd.to_numeric(ledger["mae"]).mean()),
        "turnover": float(weighted_returns.abs().sum()),
        "average_gross_exposure": float(equity["gross_exposure"].mean()),
        "max_gross_exposure": float(equity["gross_exposure"].max()),
        "average_net_exposure": float(equity["net_exposure"].mean()),
        "max_abs_net_exposure": float(equity["net_exposure"].abs().max()),
        "exposure": float((equity["gross_exposure"] > 0).mean()),
    }
    yearly = _group_returns(
        ledger.assign(exit_year=pd.to_datetime(ledger["exit_date"]).dt.year.astype(str)),
        "exit_year",
        "year",
    )
    return PortfolioBacktestResult(
        ledger,
        equity,
        metrics,
        yearly,
        _group_returns(ledger, "regime", "regime"),
        _group_returns(ledger, "sector", "sector"),
        _group_returns(ledger, "ticker", "ticker"),
        _group_returns(ledger, "model_version", "model_version"),
        pd.DataFrame(audit_rows),
    )
