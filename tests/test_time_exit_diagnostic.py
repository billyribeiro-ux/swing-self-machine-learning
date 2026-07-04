from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from swing_rsi.config import ProjectPaths
from swing_rsi.data.loader import save_ohlcv_csv
from swing_rsi.engine.storage import initialize_engine_db
from swing_rsi.engine.time_exit_diagnostic import (
    DIAGNOSTIC_EVENT_BACKFILL_BLOCKED,
    DIAGNOSTIC_EVENT_ENTRY_FILLED,
    DIAGNOSTIC_EVENT_OBSERVATION_CREATED,
    DIAGNOSTIC_EVENT_OBSERVATION_REJECTED,
    DIAGNOSTIC_EVENT_TIME_EXIT_MATURED,
    PROSPECTIVE_TIME_EXIT_DIAGNOSTIC_SCHEMA_VERSION,
    export_time_exit_diagnostic,
    initialize_time_exit_diagnostic_run,
    list_time_exit_diagnostic_events,
    process_time_exit_diagnostic_update,
    time_exit_diagnostic_matured_outcomes_frame,
    time_exit_diagnostic_observations_frame,
    time_exit_diagnostic_status_frame,
)
from swing_rsi.engine.time_exit_utility import (
    SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID,
    TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION,
)


def _write_market_data(root: Path) -> pd.DatetimeIndex:
    paths = ProjectPaths(root)
    paths.ensure()
    dates = pd.bdate_range("2026-06-22", periods=45)
    rows: list[dict[str, float]] = []
    for index, _ in enumerate(dates):
        close = 100.0 + index * 0.12
        open_price = close - 0.05
        high = close + 0.30
        low = close - 0.30
        rows.append(
            {
                "Open": open_price,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": 2_000_000.0,
            }
        )
    frame = pd.DataFrame(rows, index=dates.rename("Date"))
    signal_position = dates.get_loc(pd.Timestamp("2026-06-29"))
    entry_position = signal_position + 1
    frame.iloc[entry_position + 1, frame.columns.get_loc("Low")] = 97.00
    frame.iloc[signal_position + 20, frame.columns.get_loc("Close")] = 103.00
    frame.iloc[signal_position + 20, frame.columns.get_loc("High")] = 103.30
    save_ohlcv_csv(frame, paths.raw_data / "AAPL.csv")
    feature = pd.DataFrame(
        {
            "Date": dates.date.astype(str),
            "symbol": "AAPL",
            "atr_pct_14": 0.02,
        }
    )
    feature.to_parquet(paths.feature_data / "fixture_featurehash_features.parquet", index=False)
    return dates


def _signal_row(
    *,
    signal_id: str,
    as_of_date: str,
    ticker: str = "AAPL",
    source: str = "no_signal",
) -> dict[str, object]:
    return {
        "signal_id": signal_id,
        "generation_id": "fixture_generation",
        "scan_id": "fixture_generation",
        "as_of_date": as_of_date,
        "ticker": ticker,
        "symbol": ticker,
        "direction": "Bullish",
        "action": "NO SIGNAL",
        "decision": "NO_SIGNAL" if source != "rejected" else "REJECTED",
        "candidate_status": "RESEARCH_ONLY",
        "candidate_classification": "RESEARCH_ONLY",
        "edge_status": "RESEARCH ONLY",
        "archetype": "Sector Rotation",
        "archetype_id": "sector_rotation",
        "hypothesis_id": SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID,
        "model_id": f"{SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID}:extra_trees",
        "model_family": "extra_trees",
        "family": "extra_trees",
        "target_stop_policy_id": "sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25",
        "target_stop_policy_status": "EXPERIMENTAL_CANDIDATE",
        "horizon": 20,
        "scope": "ORDINARY",
        "product_class_scope": "ORDINARY",
        "feature_snapshot_hash": "featurehash",
        "target_before_stop_probability": 0.4184,
        "time_exit_positive_probability": 0.5837,
        "expected_time_exit_return": 0.0049,
        "expected_time_exit_utility": 0.9810,
        "expected_return": 0.0049,
        "expected_mfe": 0.08,
        "expected_mae": -0.05,
        "signal_score": 0.55,
        "ood_feature_rate": 0.01,
        "footprint_summary": "sector rotation time-exit diagnostic fixture",
        "historical_analog_support": "MIXED_SUPPORT",
        "rejection_reason": "ood_feature_rate_above_limit" if source == "rejected" else "",
        "no_signal_reason": "target_before_stop_probability_below_threshold",
        "not_live_actionable_reason": "Time-exit utility is diagnostic.",
    }


def _write_generation(root: Path, generation_id: str, rows: list[dict[str, object]]) -> None:
    generation_dir = root / "artifacts" / "signal_discovery" / generation_id
    generation_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": "multi_angle_signal_discovery_v1",
        "generation_id": generation_id,
        "feature_manifest_hash": "featurehash",
        "time_exit_utility_label_schema_version": TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION,
    }
    (generation_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "generation_id": generation_id,
                "hypothesis_id": SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID,
                "target_stop_policy_id": (
                    "sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25"
                ),
                "target_stop_policy_status": "EXPERIMENTAL_CANDIDATE",
                "time_exit_label_schema_version": TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION,
            }
        ]
    ).to_csv(generation_dir / "hypotheses.csv", index=False)
    no_signal = [row for row in rows if row["decision"] != "REJECTED"]
    rejected = [row for row in rows if row["decision"] == "REJECTED"]
    pd.DataFrame(rows).to_csv(generation_dir / "candidates.csv", index=False)
    pd.DataFrame(no_signal).to_csv(generation_dir / "no_signal.csv", index=False)
    pd.DataFrame(rejected).to_csv(generation_dir / "rejected.csv", index=False)
    pd.DataFrame(
        [
            {
                "generation_id": generation_id,
                "hypotheses_evaluated": 1,
                "buy_candidates": 0,
                "sell_candidates": 0,
                "no_signal_rows": len(no_signal),
                "rejected_rows": len(rejected),
            }
        ]
    ).to_csv(generation_dir / "summary.csv", index=False)


def test_time_exit_diagnostic_lifecycle_blocks_backfill_and_matures_outcomes(
    tmp_path: Path,
) -> None:
    dates = _write_market_data(tmp_path)
    db = ProjectPaths(tmp_path).engine_db
    initialize_engine_db(db)
    _write_generation(
        tmp_path,
        "signal_discovery_20260704T155444+0000_old",
        [_signal_row(signal_id="old-signal", as_of_date="2026-06-26")],
    )
    init = initialize_time_exit_diagnostic_run(
        tmp_path,
        hypothesis=SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID,
        generation="signal_discovery_20260704T155444+0000_old",
        baseline_date="2026-06-26",
    )

    assert init.created is True
    assert init.run.schema_version == PROSPECTIVE_TIME_EXIT_DIAGNOSTIC_SCHEMA_VERSION
    assert init.run.baseline_market_date == "2026-06-26"
    assert init.run.label_schema == TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION
    assert time_exit_diagnostic_status_frame(tmp_path).iloc[0]["observations_created"] == 0
    assert list_time_exit_diagnostic_events(db).empty

    _write_generation(
        tmp_path,
        "signal_discovery_20260705T120000+0000_future",
        [
            _signal_row(signal_id="future-signal", as_of_date="2026-06-29"),
            _signal_row(signal_id="future-ood", as_of_date="2026-06-29", source="rejected"),
        ],
    )

    first_update = process_time_exit_diagnostic_update(tmp_path)
    events = list_time_exit_diagnostic_events(db)
    assert first_update.observations_created == 1
    assert first_update.rejected_observations == 1
    assert first_update.pending_entries_created == 1
    assert first_update.backfill_blocked == 1
    assert set(events["event_type"]) >= {
        DIAGNOSTIC_EVENT_OBSERVATION_CREATED,
        DIAGNOSTIC_EVENT_OBSERVATION_REJECTED,
        DIAGNOSTIC_EVENT_BACKFILL_BLOCKED,
    }
    observations = time_exit_diagnostic_observations_frame(tmp_path)
    assert "Diagnostic Backfill Blocked" in set(observations["observation_status"])
    assert "Diagnostic Rejected" in set(observations["observation_status"])
    assert "Diagnostic Pending Entry" in set(observations["observation_status"])

    second_update = process_time_exit_diagnostic_update(tmp_path)
    matured = time_exit_diagnostic_matured_outcomes_frame(tmp_path)
    assert second_update.entries_filled == 1
    assert second_update.matured_outcomes == 1
    assert len(matured) == 1
    outcome = matured.iloc[0]
    signal_location = dates.get_loc(pd.Timestamp("2026-06-29"))
    expected_entry = dates[signal_location + 1].date().isoformat()
    expected_exit = dates[signal_location + 20].date().isoformat()
    assert outcome["entry_date"] == expected_entry
    assert outcome["exit_date"] == expected_exit
    assert float(outcome["time_exit_net_return"]) > 0.0
    assert bool(outcome["time_exit_positive"]) is True
    assert float(outcome["MFE"]) > 0.0
    assert float(outcome["MAE"]) < 0.0
    assert bool(outcome["baseline_profitable_despite_failed_tbs"]) is True
    assert bool(outcome["experimental_profitable_despite_failed_tbs"]) is True
    assert bool(outcome["baseline_early_adverse_recovery"]) is True
    assert bool(outcome["experimental_early_adverse_recovery"]) is True
    assert DIAGNOSTIC_EVENT_ENTRY_FILLED in set(list_time_exit_diagnostic_events(db)["event_type"])
    assert DIAGNOSTIC_EVENT_TIME_EXIT_MATURED in set(
        list_time_exit_diagnostic_events(db)["event_type"]
    )

    count_after_second = len(list_time_exit_diagnostic_events(db))
    third_update = process_time_exit_diagnostic_update(tmp_path)
    assert third_update.events_inserted == 0
    assert len(list_time_exit_diagnostic_events(db)) == count_after_second

    status = time_exit_diagnostic_status_frame(tmp_path).iloc[0]
    assert status["matured_outcomes"] == 1
    assert bool(status["promotion_eligible"]) is False
    assert bool(status["final_holdout_evidence"]) is False
    assert status["backfill_blocked_count"] == 1

    output = tmp_path / "reports" / "time_exit_diagnostic"
    written = export_time_exit_diagnostic(tmp_path, output=output)
    assert {path.name for path in written} >= {
        "time_exit_diagnostic_status.csv",
        "time_exit_diagnostic_events.csv",
        "time_exit_diagnostic_observations.csv",
        "time_exit_diagnostic_matured_outcomes.csv",
        "time_exit_diagnostic_policy_comparison.csv",
    }
