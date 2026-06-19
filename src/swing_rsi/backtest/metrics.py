from __future__ import annotations

import math

import pandas as pd


def summarize_trades(
    trades: pd.DataFrame, minimum_trades: int = 30
) -> dict[str, float | int | bool]:
    if "net_return" not in trades.columns:
        raise ValueError("Trades must contain net_return")
    returns = pd.to_numeric(trades["net_return"], errors="coerce").dropna()
    count = int(returns.size)
    if count == 0:
        return {
            "trade_count": 0,
            "eligible": False,
            "win_rate": math.nan,
            "mean_return": math.nan,
            "median_return": math.nan,
            "return_std": math.nan,
            "profit_factor": math.nan,
            "max_drawdown": math.nan,
            "mean_mfe": math.nan,
            "mean_mae": math.nan,
            "positive_year_fraction": math.nan,
            "mean_return_lcb_90": math.nan,
            "score": -math.inf,
        }

    positive_sum = float(returns[returns > 0].sum())
    negative_sum = float(returns[returns < 0].sum())
    profit_factor = positive_sum / abs(negative_sum) if negative_sum < 0 else math.inf
    equity = (1.0 + returns).cumprod()
    drawdown = (equity / equity.cummax()) - 1.0
    standard_deviation = float(returns.std(ddof=1)) if count > 1 else 0.0
    standard_error = standard_deviation / math.sqrt(count) if count > 1 else 0.0
    mean_return = float(returns.mean())
    lower_confidence_bound = mean_return - (1.645 * standard_error)

    positive_year_fraction = math.nan
    if "signal_date" in trades.columns:
        signal_dates = pd.to_datetime(trades.loc[returns.index, "signal_date"])
        by_year = (
            pd.Series(returns.to_numpy(), index=signal_dates).groupby(signal_dates.dt.year).mean()
        )
        if not by_year.empty:
            positive_year_fraction = float((by_year > 0).mean())

    eligible = count >= minimum_trades
    score = lower_confidence_bound * math.log1p(count) if eligible else -math.inf
    return {
        "trade_count": count,
        "eligible": eligible,
        "win_rate": float((returns > 0).mean()),
        "mean_return": mean_return,
        "median_return": float(returns.median()),
        "return_std": standard_deviation,
        "profit_factor": profit_factor,
        "max_drawdown": float(drawdown.min()),
        "mean_mfe": float(pd.to_numeric(trades["mfe"], errors="coerce").mean()),
        "mean_mae": float(pd.to_numeric(trades["mae"], errors="coerce").mean()),
        "positive_year_fraction": positive_year_fraction,
        "mean_return_lcb_90": lower_confidence_bound,
        "score": score,
    }
