from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from swing_rsi.application.datasets import download_daily_to_raw
from swing_rsi.application.engine_service import (
    build_autonomous_features,
    evaluate_final_holdout,
    final_holdout_status,
    forward_events,
    initialize_final_holdout,
    list_registered_models,
    promote_registered_model,
    run_daily_cycle,
    run_forward_update,
    run_live_scanner,
    run_model_discovery,
    update_final_holdout,
    update_universe_data,
)
from swing_rsi.application.research_service import run_research
from swing_rsi.backtest.engine import backtest_fixed_horizon
from swing_rsi.config import ProjectPaths
from swing_rsi.data.loader import load_ohlcv_csv, save_ohlcv_csv
from swing_rsi.data.providers.fmp import download_fmp_daily
from swing_rsi.engine.model_audit import audit_text, build_model_audit, export_model_audit
from swing_rsi.features.labels import add_swing_labels
from swing_rsi.features.price import build_price_features
from swing_rsi.features.rsi import wilder_rsi
from swing_rsi.reports.writer import atomic_write_csv
from swing_rsi.research.grid_search import (
    compact_demo_grid,
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
    result = download_daily_to_raw(
        Path.cwd(),
        args.ticker,
        start=args.start,
        end=args.end,
        provider=args.provider,
    )
    if args.output:
        frame = load_ohlcv_csv(result.saved_path)
        output = save_ohlcv_csv(frame, args.output)
    else:
        output = result.saved_path
    print(
        f"Updated {result.ticker}: downloaded {result.downloaded_rows:,} rows, "
        f"started with {result.existing_rows:,}, replaced {result.replaced_dates:,} dates, "
        f"inserted {result.inserted_dates:,}, final rows {result.final_rows:,} to {output}"
    )
    print("Provider data still requires corporate-action and historical-universe audits.")
    return 0


def command_research(args: argparse.Namespace) -> int:
    frame = load_ohlcv_csv(args.input)
    run = run_research(
        frame,
        ticker=args.ticker,
        start=None,
        end=None,
        holding_period=args.holding_period,
        round_trip_cost_bps=args.cost_bps,
        minimum_trades=args.minimum_trades,
        grid_preset="standard",
        reports_dir=Path(args.output).parent,
        report_path=Path(args.output),
    )
    print(f"Saved {len(run.results):,} candidate evaluations to {run.report_path}")
    if not run.results.empty:
        print(run.results.head(10).to_string(index=False))
    return 0


def command_universe_update(args: argparse.Namespace) -> int:
    result = update_universe_data(
        Path.cwd(),
        universe_path=args.universe,
        start=args.start,
        end=args.end,
        lookback_years=args.lookback_years,
    )
    updated = [row for row in result.results if row.status == "updated"]
    errors = [row for row in result.results if row.status == "error"]
    print(f"Universe: {result.universe.name} ({result.universe.snapshot_id})")
    print(f"Enabled symbols: {len(result.universe.enabled_symbols):,}")
    print(f"Updated symbols: {len(updated):,}")
    print(f"Symbols with errors: {len(errors):,}")
    for row in errors:
        print(f"- {row.symbol}: {row.message}")
    print("FMP data remains unaudited for corporate-action and historical-universe semantics.")
    return 0


def command_build_features(args: argparse.Namespace) -> int:
    result = build_autonomous_features(Path.cwd(), universe_path=args.universe)
    print(f"Universe: {result.universe.name} ({result.universe.snapshot_id})")
    print(f"Feature rows: {len(result.features.frame):,}")
    print(f"Label rows: {len(result.labels):,}")
    print(f"Modeling rows: {len(result.modeling_frame):,}")
    print(f"Feature manifest hash: {result.features.manifest_hash}")
    print(f"Features saved: {result.feature_path}")
    print(f"Labels saved: {result.labels_path}")
    print(f"Modeling frame saved: {result.modeling_path}")
    return 0


def command_discover_models(args: argparse.Namespace) -> int:
    models = run_model_discovery(
        Path.cwd(),
        universe_path=args.universe,
        minimum_training_samples=args.minimum_training_samples,
        minimum_holdout_samples=args.minimum_holdout_samples,
    )
    challengers = [model for model in models if model.state == "CHALLENGER"]
    candidates = [model for model in models if model.state == "CANDIDATE"]
    rejected = [model for model in models if model.state == "REJECTED"]
    print(f"Models registered this run: {len(models):,}")
    print(f"Challengers: {len(challengers):,}")
    print(f"Candidates needing review: {len(candidates):,}")
    print(f"Rejected/experimental: {len(rejected):,}")
    if challengers:
        best = max(
            challengers,
            key=lambda model: float(
                model.metrics.get("holdout_mean_return_lcb_90") or float("-inf")
            ),
        )
        print(f"Best challenger: {best.model_id}")
        print(f"Direction: {best.direction}; horizon: {best.horizon}; family: {best.family}")
    elif candidates:
        best = max(
            candidates,
            key=lambda model: float(
                model.metrics.get("holdout_mean_return_lcb_90") or float("-inf")
            ),
        )
        print(f"Best failed-gate candidate retained for inspection: {best.model_id}")
        print("No candidate was promoted or silently deployed.")
    else:
        print("No challenger passed all quality gates. Gates were not weakened.")
    return 0


def command_model_registry(_: argparse.Namespace) -> int:
    models = list_registered_models(Path.cwd())
    if not models:
        print("No models registered.")
        return 0
    rows = [
        {
            "model_id": model.model_id,
            "state": model.state,
            "direction": model.direction,
            "horizon": model.horizon,
            "family": model.family,
            "holdout_mean_net_return": model.metrics.get("holdout_mean_net_return"),
            "holdout_brier": model.calibration_metrics.get("holdout_brier"),
        }
        for model in models
    ]
    print(pd.DataFrame(rows).to_string(index=False))
    return 0


def command_model_audit(args: argparse.Namespace) -> int:
    result = build_model_audit(
        Path.cwd(),
        generation=args.generation,
        model_id=args.model_id,
    )
    print(audit_text(result))
    if args.export_dir:
        paths = export_model_audit(result, args.export_dir)
        print("Exports:")
        for path in paths:
            print(f"- {path}")
    return 0


def command_promote_model(args: argparse.Namespace) -> int:
    promoted = promote_registered_model(Path.cwd(), args.model_id)
    print(f"Promoted champion model: {promoted.model_id}")
    print(
        f"Direction: {promoted.direction}; horizon: {promoted.horizon}; family: {promoted.family}"
    )
    return 0


def command_scan(args: argparse.Namespace) -> int:
    if args.update_data:
        update = update_universe_data(Path.cwd(), universe_path=args.universe)
        updated = sum(1 for row in update.results if row.status == "updated")
        errors = sum(1 for row in update.results if row.status == "error")
        print(
            f"Updated universe before scan: {updated:,} symbols updated, "
            f"{errors:,} symbols with errors."
        )
    snapshot = run_live_scanner(
        Path.cwd(),
        include_challengers=args.include_challengers,
        universe_path=args.universe,
    )
    print(f"Scan ID: {snapshot.scan_id}")
    print(f"As-of date: {snapshot.as_of_date}")
    print(f"Rows: {len(snapshot.rows):,}")
    print(f"CSV: {snapshot.csv_path}")
    print(f"Parquet: {snapshot.parquet_path}")
    if not snapshot.rows.empty:
        print(snapshot.rows.head(20).to_string(index=False))
    return 0


def command_forward_update(_: argparse.Namespace) -> int:
    count = run_forward_update(Path.cwd())
    print(f"Forward events created from latest scanner snapshot: {count:,}")
    events = forward_events(Path.cwd())
    print(f"Total forward events: {len(events):,}")
    return 0


def command_final_holdout_init(args: argparse.Namespace) -> int:
    report = initialize_final_holdout(
        Path.cwd(),
        generation=args.generation,
        research_only=args.research_only,
    )
    print(report.message)
    if report.run is not None:
        print(f"Run ID: {report.run.run_id}")
        print(f"Baseline market date: {report.run.baseline_market_date}")
        print(f"First eligible future signal date: {report.run.first_eligible_future_signal_date}")
        print(f"Enrolled models: {len(report.enrolled_models):,}")
        print("Backfilled predictions: 0")
        print("Matured outcomes: 0")
    else:
        print("Enrollment blockers:")
        for model_id, blockers in sorted(report.blockers_by_model.items()):
            blocker_text = "; ".join(blockers) if blockers else "none"
            print(f"- {model_id}: {blocker_text}")
    return 0


def command_final_holdout_update(_: argparse.Namespace) -> int:
    result = update_final_holdout(Path.cwd())
    print(f"Processed sessions: {len(result.processed_sessions):,}")
    if result.processed_sessions:
        print(", ".join(result.processed_sessions))
    print(f"Blocked sessions: {len(result.blocked_sessions):,}")
    for session, reason in sorted(result.blocked_sessions.items()):
        print(f"- {session}: {reason}")
    print(f"Events inserted: {result.events_inserted:,}")
    for path in result.reports:
        print(f"Report: {path}")
    return 0


def command_final_holdout_status(_: argparse.Namespace) -> int:
    status = final_holdout_status(Path.cwd())
    if status.empty:
        print("No prospective final-holdout runs exist.")
        return 0
    print("Prospective shadow validation. Not a live trade recommendation.")
    print(status.to_string(index=False))
    return 0


def command_final_holdout_evaluate(args: argparse.Namespace) -> int:
    result = evaluate_final_holdout(
        Path.cwd(),
        run_id=args.run_id,
        diagnostic_only=args.diagnostic_only,
    )
    print(f"Run ID: {result.run_id}")
    print(f"Status: {result.status}")
    for model_id, metrics in sorted(result.metrics_by_model.items()):
        print(f"Model: {model_id}")
        print(f"  Evidence manifest: {result.evidence_manifest_hashes[model_id]}")
        print(f"  Matured outcomes: {metrics.get('final_holdout_matured_outcomes')}")
        gates = result.gates_by_model[model_id]
        blocked = [gate for gate in gates if gate.status != "PASS"]
        if blocked:
            print("  Blocking final-holdout gates:")
            for gate in blocked:
                print(f"  - {gate.gate_id}: {gate.status} - {gate.reason}")
        else:
            print("  Final-holdout gates: PASS")
    return 0


def command_daily_cycle(args: argparse.Namespace) -> int:
    result = run_daily_cycle(
        Path.cwd(),
        universe_path=args.universe,
        update_data=args.update_data,
        include_challengers=args.include_challengers,
    )
    print(f"Daily cycle status: {result.status}")
    print(f"Market date: {result.market_date}")
    print(result.summary)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swing-rsi",
        description="Self-Learning Swing Trading Engine.",
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

    universe_update = subparsers.add_parser(
        "universe-update",
        help="Update enabled universe symbols through the configured provider",
    )
    universe_update.add_argument("--universe", default=None)
    universe_update.add_argument("--start", default=None)
    universe_update.add_argument("--end", default=None)
    universe_update.add_argument("--lookback-years", type=int, default=10)
    universe_update.set_defaults(handler=command_universe_update)

    build_features = subparsers.add_parser(
        "build-features",
        help="Build autonomous feature, label, and modeling parquet files",
    )
    build_features.add_argument("--universe", default=None)
    build_features.set_defaults(handler=command_build_features)

    discover = subparsers.add_parser(
        "discover-models",
        help="Train and register autonomous candidate/challenger models",
    )
    discover.add_argument("--universe", default=None)
    discover.add_argument("--minimum-training-samples", type=int, default=200)
    discover.add_argument("--minimum-holdout-samples", type=int, default=80)
    discover.set_defaults(handler=command_discover_models)

    registry = subparsers.add_parser("model-registry", help="List registered models")
    registry.set_defaults(handler=command_model_registry)

    audit = subparsers.add_parser(
        "model-audit",
        help="Print and export canonical model evaluation gate audits",
    )
    audit.add_argument("--generation", default="latest")
    audit.add_argument("--model-id", default=None)
    audit.add_argument("--export-dir", default=None)
    audit.set_defaults(handler=command_model_audit)

    promote = subparsers.add_parser("promote-model", help="Promote a passed challenger model")
    promote.add_argument("--model-id", required=True)
    promote.set_defaults(handler=command_promote_model)

    scan = subparsers.add_parser("scan", help="Run the latest-session autonomous scanner")
    scan.add_argument("--universe", default=None)
    scan.add_argument(
        "--update-data",
        action="store_true",
        help="Update enabled universe symbols before scanning; does not print secrets",
    )
    scan.add_argument(
        "--include-challengers",
        action="store_true",
        help="Use challengers only when no champion exists; never a silent fallback",
    )
    scan.set_defaults(handler=command_scan)

    forward_update = subparsers.add_parser(
        "forward-update",
        help="Append paper-forward events from the latest scanner snapshot",
    )
    forward_update.set_defaults(handler=command_forward_update)

    final_init = subparsers.add_parser(
        "final-holdout-init",
        help="Enroll eligible frozen models into prospective final-holdout collection",
    )
    final_init.add_argument("--generation", default="latest")
    final_init.add_argument(
        "--research-only",
        action="store_true",
        help="Allow diagnostic enrollment that can never satisfy promotion eligibility",
    )
    final_init.set_defaults(handler=command_final_holdout_init)

    final_update = subparsers.add_parser(
        "final-holdout-update",
        help="Process genuinely new sessions for prospective shadow final holdout",
    )
    final_update.set_defaults(handler=command_final_holdout_update)

    final_status = subparsers.add_parser(
        "final-holdout-status",
        help="Show prospective final-holdout run state",
    )
    final_status.set_defaults(handler=command_final_holdout_status)

    final_evaluate = subparsers.add_parser(
        "final-holdout-evaluate",
        help="Evaluate a prospective final-holdout run without promotion",
    )
    final_evaluate.add_argument("--run-id", required=True)
    final_evaluate.add_argument(
        "--diagnostic-only",
        action="store_true",
        help="Allow non-promotable early diagnostics before sample sufficiency is complete",
    )
    final_evaluate.set_defaults(handler=command_final_holdout_evaluate)

    daily = subparsers.add_parser("daily-cycle", help="Run the local daily scanner cycle")
    daily.add_argument("--universe", default=None)
    daily.add_argument("--update-data", action="store_true")
    daily.add_argument("--include-challengers", action="store_true")
    daily.set_defaults(handler=command_daily_cycle)
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
