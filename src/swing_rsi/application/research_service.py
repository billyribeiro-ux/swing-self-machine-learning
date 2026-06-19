from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from swing_rsi.application.datasets import DateLike, slice_date_window
from swing_rsi.backtest.engine import backtest_fixed_horizon
from swing_rsi.backtest.metrics import summarize_trades
from swing_rsi.features.price import build_price_features
from swing_rsi.features.rsi import wilder_rsi
from swing_rsi.reports.writer import atomic_write_csv
from swing_rsi.research.grid_search import (
    RSIParameterGrid,
    compact_demo_grid,
    control_rules,
    default_research_grid,
    rule_from_result,
    run_grid_search,
)
from swing_rsi.signals.rsi_reversal import RSIReversalRule, generate_rsi_reversal_signal

GridPreset = Literal["quick", "standard"]


@dataclass(frozen=True)
class ControlEvaluation:
    rule: RSIReversalRule
    trades: pd.DataFrame
    metrics: dict[str, float | int | bool]


@dataclass(frozen=True)
class ResearchRun:
    ticker: str
    report_path: Path
    window_start: str | None
    window_end: str | None
    candidate_count: int
    eligible_candidate_count: int
    results: pd.DataFrame
    control: ControlEvaluation


@dataclass(frozen=True)
class RSIExplorerData:
    features: pd.DataFrame
    rsi: pd.Series
    signals: pd.Series
    signal_table: pd.DataFrame


def grid_for_preset(preset: GridPreset) -> RSIParameterGrid:
    if preset == "quick":
        return compact_demo_grid()
    if preset == "standard":
        return default_research_grid()
    raise ValueError(f"Unsupported grid preset: {preset}")


def candidate_rule_count(grid: RSIParameterGrid) -> int:
    return sum(1 for _ in grid.rules())


def retail_control_rule() -> RSIReversalRule:
    return next(iter(control_rules()))


def evaluate_retail_control(
    frame: pd.DataFrame,
    holding_period: int,
    round_trip_cost_bps: float,
    minimum_trades: int,
) -> ControlEvaluation:
    rule = retail_control_rule()
    trades = build_rule_trade_ledger(
        frame,
        rule,
        holding_period=holding_period,
        round_trip_cost_bps=round_trip_cost_bps,
    )
    metrics = summarize_trades(trades, minimum_trades=minimum_trades)
    return ControlEvaluation(rule=rule, trades=trades, metrics=metrics)


def build_rule_trade_ledger(
    frame: pd.DataFrame,
    rule: RSIReversalRule,
    holding_period: int,
    round_trip_cost_bps: float,
) -> pd.DataFrame:
    features = build_price_features(frame)
    rsi = wilder_rsi(features["Close"], rule.length)
    signals = generate_rsi_reversal_signal(features, rule, rsi=rsi)
    trades = backtest_fixed_horizon(
        features,
        signals,
        holding_period=holding_period,
        round_trip_cost_bps=round_trip_cost_bps,
    ).copy()
    trades.insert(0, "rule_id", rule.rule_id)
    return trades


def _safe_token(value: object) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    return token.strip("-") or "na"


def build_research_run_id(
    ticker: str,
    start: str | None,
    end: str | None,
    holding_period: int,
    *,
    created_at: datetime | None = None,
    unique_suffix: str | None = None,
) -> str:
    timestamp = created_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    stamp = timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = unique_suffix or uuid.uuid4().hex[:8]
    return "_".join(
        (
            _safe_token(ticker.upper()),
            _safe_token(start or "full-start"),
            _safe_token(end or "full-end"),
            f"hp{holding_period}",
            stamp,
            _safe_token(suffix),
        )
    )


def research_report_path(
    reports_dir: str | Path,
    ticker: str,
    start: str | None,
    end: str | None,
    holding_period: int,
    *,
    created_at: datetime | None = None,
    unique_suffix: str | None = None,
) -> Path:
    run_id = build_research_run_id(
        ticker,
        start,
        end,
        holding_period,
        created_at=created_at,
        unique_suffix=unique_suffix,
    )
    return Path(reports_dir) / f"{run_id}_grid_search.csv"


def save_research_report(frame: pd.DataFrame, path: str | Path) -> Path:
    output = Path(path)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing research report: {output}")
    return atomic_write_csv(frame, output, index=False)


def run_research(
    frame: pd.DataFrame,
    *,
    ticker: str,
    start: DateLike | None,
    end: DateLike | None,
    holding_period: int,
    round_trip_cost_bps: float,
    minimum_trades: int,
    grid_preset: GridPreset,
    reports_dir: str | Path,
    report_path: str | Path | None = None,
) -> ResearchRun:
    window = slice_date_window(frame, start=start, end=end)
    if window.empty:
        raise ValueError("Selected research window contains no rows")

    grid = grid_for_preset(grid_preset)
    results = run_grid_search(
        window,
        grid,
        holding_period=holding_period,
        round_trip_cost_bps=round_trip_cost_bps,
        minimum_trades=minimum_trades,
    )
    saved = results.copy()
    saved.insert(0, "ticker", ticker.upper())
    saved.insert(1, "window_start", _window_bound(window, "min"))
    saved.insert(2, "window_end", _window_bound(window, "max"))
    saved.insert(3, "grid_preset", grid_preset)
    output = (
        Path(report_path)
        if report_path is not None
        else research_report_path(
            reports_dir,
            ticker,
            _window_bound(window, "min"),
            _window_bound(window, "max"),
            holding_period,
        )
    )
    save_research_report(saved, output)

    eligible_count = int(results["eligible"].sum()) if "eligible" in results.columns else 0
    return ResearchRun(
        ticker=ticker.upper(),
        report_path=output,
        window_start=_window_bound(window, "min"),
        window_end=_window_bound(window, "max"),
        candidate_count=candidate_rule_count(grid),
        eligible_candidate_count=eligible_count,
        results=results,
        control=evaluate_retail_control(
            window,
            holding_period=holding_period,
            round_trip_cost_bps=round_trip_cost_bps,
            minimum_trades=minimum_trades,
        ),
    )


def _window_bound(frame: pd.DataFrame, method: Literal["min", "max"]) -> str | None:
    if frame.empty:
        return None
    value = frame.index.min() if method == "min" else frame.index.max()
    return pd.Timestamp(value).date().isoformat()


def rule_from_result_row(row: pd.Series) -> RSIReversalRule:
    return rule_from_result(row)


def build_trade_curve(trades: pd.DataFrame) -> pd.DataFrame:
    returns = pd.to_numeric(trades.get("net_return", pd.Series(dtype=float)), errors="coerce")
    returns = returns.dropna().reset_index(drop=True)
    if returns.empty:
        return pd.DataFrame(columns=["trade_number", "equity", "drawdown"])
    equity = (1.0 + returns).cumprod()
    drawdown = (equity / equity.cummax()) - 1.0
    return pd.DataFrame(
        {
            "trade_number": range(1, len(returns) + 1),
            "equity": equity,
            "drawdown": drawdown,
        }
    )


def returns_by_calendar_year(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty or "signal_date" not in trades.columns or "net_return" not in trades.columns:
        return pd.DataFrame(columns=["year", "trade_count", "mean_return", "compounded_return"])
    data = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(trades["signal_date"]),
            "net_return": pd.to_numeric(trades["net_return"], errors="coerce"),
        }
    ).dropna()
    if data.empty:
        return pd.DataFrame(columns=["year", "trade_count", "mean_return", "compounded_return"])
    data["year"] = data["signal_date"].dt.year
    grouped = data.groupby("year")["net_return"]

    def compounded(values: pd.Series) -> float:
        numeric = pd.to_numeric(values, errors="coerce").dropna()
        product = 1.0
        for value in numeric.to_numpy(dtype=float):
            product *= 1.0 + float(value)
        return product - 1.0

    return pd.DataFrame(
        {
            "year": grouped.mean().index,
            "trade_count": grouped.count().to_numpy(),
            "mean_return": grouped.mean().to_numpy(),
            "compounded_return": grouped.apply(compounded).to_numpy(),
        }
    ).reset_index(drop=True)


def build_rsi_explorer_data(frame: pd.DataFrame, rule: RSIReversalRule) -> RSIExplorerData:
    features = build_price_features(frame)
    rsi = wilder_rsi(features["Close"], rule.length)
    signals = generate_rsi_reversal_signal(features, rule, rsi=rsi)
    signal_rows = features.loc[signals, ["Close"]].copy()
    signal_rows["RSI"] = rsi.loc[signals]
    signal_rows["relative_volume_20"] = features.loc[signals, "relative_volume_20"]
    signal_rows["close_position"] = features.loc[signals, "close_position"]
    signal_rows = signal_rows.reset_index().rename(
        columns={"Date": "signal_date", "Close": "close"}
    )
    return RSIExplorerData(
        features=features,
        rsi=rsi,
        signals=signals,
        signal_table=signal_rows,
    )


def metric_value(metrics: dict[str, float | int | bool], name: str) -> float:
    value = metrics.get(name, math.nan)
    if isinstance(value, bool):
        return float(value)
    return float(value)
