from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from swing_rsi.backtest.engine import backtest_fixed_horizon
from swing_rsi.config import ProjectPaths
from swing_rsi.data.loader import download_daily, load_ohlcv_csv, save_ohlcv_csv
from swing_rsi.data.providers.fmp import download_fmp_daily
from swing_rsi.features.labels import add_swing_labels
from swing_rsi.features.price import build_price_features
from swing_rsi.features.rsi import wilder_rsi
from swing_rsi.reports.writer import atomic_write_csv
from swing_rsi.research.grid_search import (
    compact_demo_grid,
    default_research_grid,
    rule_from_result,
    run_grid_search,
)
from swing_rsi.sample_data import generate_sample_ohlcv
from swing_rsi.scanner.service import scan_latest
from swing_rsi.settings import get_fmp_api_key, get_fmp_base_url, load_project_environment
from swing_rsi.signals.rsi_reversal import generate_rsi_reversal_signal


def _project_paths() -> ProjectPaths:
    paths = ProjectPaths(Path.cwd())
    paths.ensure()
    return paths


def command_demo(_: argparse.Namespace) -> int:
    paths = _project_paths()
    raw_path = paths.raw_data / "DEMO.csv"
    frame = generate_sample_ohlcv()
    save_ohlcv_csv(frame, raw_path)

    results = run_grid_search(
        frame,
        compact_demo_grid(),
        holding_period=10,
        round_trip_cost_bps=5.0,
        minimum_trades=8,
    )
    atomic_write_csv(results, paths.reports / "demo_grid_search.csv")
    if results.empty:
        raise RuntimeError("Demo grid search produced no results")

    best = results.iloc[0]
    best_rule = rule_from_result(best)
    features = build_price_features(frame)
    rsi = wilder_rsi(features["Close"], best_rule.length)
    signals = generate_rsi_reversal_signal(features, best_rule, rsi=rsi)
    trades = backtest_fixed_horizon(features, signals, holding_period=10, round_trip_cost_bps=5.0)
    atomic_write_csv(trades, paths.reports / "demo_best_trades.csv")

    labeled = add_swing_labels(frame, horizons=(3, 5, 10, 20, 30))
    labeled = build_price_features(labeled[["Open", "High", "Low", "Close", "Volume"]]).join(
        labeled[[column for column in labeled.columns if column.startswith("label_")]]
    )
    atomic_write_csv(labeled.reset_index(), paths.reports / "demo_features_and_labels.csv")

    scan = scan_latest(
        frame,
        ticker="DEMO",
        rule=best_rule,
        historical_stats={str(key): value for key, value in best.to_dict().items()},
    )
    scanner_frame = pd.DataFrame([] if scan is None else [scan.to_dict()])
    atomic_write_csv(scanner_frame, paths.reports / "demo_scanner_results.csv")

    print("Demo completed successfully.")
    print(f"Synthetic data: {raw_path}")
    print(f"Candidate rules tested: {len(results):,}")
    print(f"Best rule ID: {best_rule.rule_id}")
    print(f"Best rule: {best_rule.to_dict()}")
    print(f"Trades: {int(best['trade_count'])}")
    print(f"Win rate (not sufficient by itself): {float(best['win_rate']):.2%}")
    print(f"Mean net return: {float(best['mean_return']):.2%}")
    print("Synthetic results are not evidence of a real trading edge.")
    return 0


def command_doctor(_: argparse.Namespace) -> int:
    env_path = load_project_environment()
    print(f"Project root: {Path.cwd()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Local .env found: {'yes' if env_path is not None else 'no'}")
    try:
        get_fmp_api_key()
    except RuntimeError:
        configured = "no"
    else:
        configured = "yes"
    print(f"FMP API key configured: {configured}")
    print(f"FMP base URL: {get_fmp_base_url()}")
    print("The API key value is never printed.")
    return 0


def command_fmp_check(args: argparse.Namespace) -> int:
    end_date = date.today()
    start_date = end_date - timedelta(days=args.lookback_days)
    frame = download_fmp_daily(
        args.ticker,
        start=start_date.isoformat(),
        end=end_date.isoformat(),
    )
    first = frame.index.min().date().isoformat()
    last = frame.index.max().date().isoformat()
    print(f"FMP connection successful for {args.ticker.upper()}.")
    print(f"Received {len(frame):,} validated daily rows from {first} through {last}.")
    print("The key itself was not displayed or written to source code.")
    return 0


def command_download(args: argparse.Namespace) -> int:
    paths = _project_paths()
    frame = download_daily(
        args.ticker,
        start=args.start,
        end=args.end,
        provider=args.provider,
    )
    output = Path(args.output) if args.output else paths.raw_data / f"{args.ticker.upper()}.csv"
    save_ohlcv_csv(frame, output)
    print(f"Saved {len(frame):,} validated daily rows from {args.provider} to {output}")
    print("Provider data still requires corporate-action and historical-universe audits.")
    return 0


def command_research(args: argparse.Namespace) -> int:
    frame = load_ohlcv_csv(args.input)
    results = run_grid_search(
        frame,
        default_research_grid(),
        holding_period=args.holding_period,
        round_trip_cost_bps=args.cost_bps,
        minimum_trades=args.minimum_trades,
    )
    output = Path(args.output)
    atomic_write_csv(results, output)
    print(f"Saved {len(results):,} candidate evaluations to {output}")
    if not results.empty:
        print(results.head(10).to_string(index=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swing-rsi",
        description="Daily swing RSI discovery and validation research engine.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the deterministic synthetic plumbing demo")
    demo.set_defaults(handler=command_demo)

    doctor = subparsers.add_parser("doctor", help="Check local project and FMP configuration")
    doctor.set_defaults(handler=command_doctor)

    fmp_check = subparsers.add_parser("fmp-check", help="Test FMP with a small daily-data request")
    fmp_check.add_argument("--ticker", default="AAPL")
    fmp_check.add_argument("--lookback-days", type=int, default=45)
    fmp_check.set_defaults(handler=command_fmp_check)

    download = subparsers.add_parser("download", help="Download validated daily OHLCV")
    download.add_argument("--ticker", required=True)
    download.add_argument("--provider", choices=("fmp", "yfinance"), default="fmp")
    download.add_argument("--start", default="2010-01-01")
    download.add_argument("--end", default=None)
    download.add_argument("--output", default=None)
    download.set_defaults(handler=command_download)

    research = subparsers.add_parser("research", help="Run the starter RSI grid search on a CSV")
    research.add_argument("--input", required=True)
    research.add_argument("--ticker", required=True)
    research.add_argument("--holding-period", type=int, default=10)
    research.add_argument("--cost-bps", type=float, default=5.0)
    research.add_argument("--minimum-trades", type=int, default=30)
    research.add_argument("--output", required=True)
    research.set_defaults(handler=command_research)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        exit_code = int(arguments.handler(arguments))
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
        return
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
