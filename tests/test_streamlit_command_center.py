from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl
import pandas as pd
import pytest
from dashboard.sections.candidate_detail import (
    _candidate_detail_deep_link,
    _deep_link_frame,
    _identifier_copy_text,
    _raw_identifier_frame,
)
from dashboard.sections.signal_board import _display_section as signal_board_display_section

from swing_rsi.application.dashboard_exports import (
    normalize_table_for_export,
    save_xlsx_report,
    to_csv_bytes,
    to_xlsx_bytes,
)
from swing_rsi.application.dashboard_service import (
    CommandSpec,
    candidate_detail_url,
    command_specs,
    complete_engine_snapshot_frames,
    dashboard_startup_state,
    gate_audit_frame,
    model_edge_status_frame,
    model_registry_frame,
    regime_cache_detail_frames,
    run_dashboard_command,
    save_development_fmp_settings,
    scanner_results_frame,
    signal_board_frame,
    signal_board_metrics,
    signal_discovery_generation_frames,
)
from swing_rsi.application.footprint_attribution import (
    EVIDENCE_UNAVAILABLE,
    footprint_evidence_frames,
    missing_evidence_audit_frame,
)
from swing_rsi.data.loader import save_ohlcv_csv
from swing_rsi.engine.gates import make_gate
from swing_rsi.engine.registry import RegisteredModel, register_model
from swing_rsi.engine.storage import engine_connection, initialize_engine_db

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest


def _assert_no_streamlit_exceptions(app: Any) -> None:
    assert not app.exception, [str(exception.value) for exception in app.exception]


def _sample_frame(rows: int = 40) -> pd.DataFrame:
    dates = pd.bdate_range("2026-04-01", periods=rows)
    close = pd.Series(range(rows), index=dates, dtype=float) + 100.0
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000.0,
        },
        index=dates.rename("Date"),
    )


@pytest.fixture()
def command_center_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "src" / "swing_rsi").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    save_ohlcv_csv(_sample_frame(), raw / "DEMO.csv")
    (tmp_path / "data" / "manifests").mkdir(parents=True)
    (tmp_path / "data" / "manifests" / "DEMO.json").write_text(
        json.dumps(
            {
                "symbol": "DEMO",
                "provider": "fmp",
                "actual_last_date": "2026-05-26",
                "row_count": 40,
                "stale_data_status": "fresh_within_3_calendar_days",
                "raw_file_hash": "rawhash",
                "retrieval_timestamp_utc": "2026-05-26T20:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    config_dir = tmp_path / "configs" / "universe"
    config_dir.mkdir(parents=True)
    (config_dir / "core.yaml").write_text(
        """
name: command-center-test
provider: fmp
default_start: "2020-01-01"
symbols:
  - symbol: DEMO
    enabled: true
    role: stock
    sector: test
relationships: []
""",
        encoding="utf-8",
    )
    artifact = tmp_path / "artifacts" / "models" / "model.joblib"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("artifact", encoding="utf-8")
    db = tmp_path / "state" / "engine.sqlite3"
    initialize_engine_db(db)
    gate = make_gate(
        gate_id="profit_factor_min_090",
        gate_name="Profit Factor Minimum",
        category="performance",
        scope="development_holdout",
        metric_name="holdout_profit_factor",
        threshold=0.9,
        comparator=">=",
        actual_value=0.5,
        status="FAIL",
        mandatory=True,
        evidence_source="test",
        reason="Profit factor is below the minimum.",
        configuration_hash_value="policyhash",
    )
    register_model(
        db,
        RegisteredModel(
            model_id="model-demo",
            task="probability_positive_return",
            horizon=10,
            direction="bull",
            family="hist_gradient_boosting",
            state="CANDIDATE",
            training_start="2020-01-01",
            training_end="2021-01-01",
            validation_start="2021-01-04",
            validation_end="2021-06-01",
            holdout_start="2021-06-02",
            holdout_end="2022-01-01",
            universe_snapshot_id="universe",
            feature_manifest_hash="featurehash",
            raw_manifest_hashes=("rawhash",),
            hyperparameters={},
            metrics={
                "product_class_scope": "POOLED",
                "holdout_status": "DEVELOPMENT_HOLDOUT",
                "selected_holdout_samples": 3,
                "selected_observation_rate": 0.1,
                "holdout_mean_return_lcb_90": -0.01,
                "portfolio_max_drawdown": -0.02,
                "portfolio_total_return": 0.03,
            },
            calibration_metrics={"brier_skill_score": -0.1, "holdout_brier": 0.24},
            quality_gates={"profit_factor_min_090": False},
            artifact_path=str(artifact),
            code_commit_hash="abcdef",
            created_at_utc="2026-06-27T12:00:00+00:00",
            gate_results=(gate,),
        ),
    )
    scanner_dir = tmp_path / "artifacts" / "scanner"
    scanner_dir.mkdir(parents=True)
    scanner_path = scanner_dir / "scan-demo_scanner.csv"
    rejected_row = {
        "scan_id": "scan-demo",
        "as_of_date": "2026-05-26",
        "ticker": "DEMO",
        "product_class_scope": "POOLED",
        "direction": "Bullish",
        "horizon": 10,
        "model_id": "model-demo",
        "calibrated_probability": 0.61,
        "expected_return": 0.02,
        "expected_mfe": 0.04,
        "expected_mae": -0.01,
        "target_before_stop_probability": 0.55,
        "candidate_status": "REJECTED",
        "exclusion_reason": "model_not_promoted; failed_gate",
        "top_attribution_categories": "Model contribution",
        "supporting_evidence": "Supporting evidence",
        "historical_analogs": "[]",
        "feature_snapshot_hash": "featurehash",
    }
    shadow_row = {
        "scan_id": "scan-demo",
        "as_of_date": "2026-05-26",
        "ticker": "DEMO2",
        "product_class_scope": "POOLED",
        "direction": "Bullish",
        "horizon": 10,
        "model_id": "model-demo",
        "calibrated_probability": 0.63,
        "expected_return": 0.03,
        "expected_mfe": None,
        "expected_mae": None,
        "target_before_stop_probability": 0.57,
        "candidate_status": "ACTIONABLE_PAPER_CANDIDATE",
        "exclusion_reason": "",
        "top_attribution_categories": "Model contribution",
        "supporting_evidence": "Supporting evidence",
        "historical_analogs": "[]",
        "feature_snapshot_hash": "featurehash",
    }
    pd.DataFrame(
        [
            rejected_row,
            shadow_row,
        ]
    ).to_csv(scanner_path, index=False)
    with engine_connection(db) as connection:
        connection.execute(
            """
            INSERT INTO scanner_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "scan-demo",
                "2026-05-26",
                "2026-06-27T12:30:00+00:00",
                json.dumps(["model-demo"]),
                "universe",
                "featurehash",
                str(scanner_path),
                str(scanner_path.with_suffix(".parquet")),
                2,
                json.dumps({"rejected_rows": 1, "actionable_rows": 1}),
            ),
        )
        connection.execute(
            """
            INSERT INTO final_holdout_runs (
                run_id, schema_version, created_at_utc, creation_git_commit,
                baseline_market_date, first_eligible_future_signal_date, universe_snapshot_id,
                feature_manifest_hash, generation_id, model_ids_json, scanner_identity_version,
                execution_policy_hash, sample_policy_version, sample_policy_hash,
                sample_policy_json, horizon, direction, status, invalidation_reason,
                latest_processed_market_date, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-demo",
                "prospective_final_holdout_v1",
                "2026-06-27T12:40:00+00:00",
                "abcdef",
                "2026-06-25",
                "2026-06-26",
                "universe",
                "featurehash",
                "2026-06-27T12:00:00+00:00",
                json.dumps(["model-demo"]),
                1,
                "executionhash",
                "prospective_final_holdout_sample_v1",
                "samplehash",
                json.dumps({}),
                10,
                "bull",
                "COLLECTING",
                None,
                "2026-06-26",
                json.dumps({"processed_sessions": ["2026-06-26"]}),
            ),
        )
        connection.execute(
            """
            INSERT INTO final_holdout_models VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-demo",
                "model-demo",
                "2026-06-27T12:00:00+00:00",
                str(artifact),
                "bad-hash",
                "CANDIDATE",
                0,
                1,
                "selectionhash",
                "calhash",
                "oodhash",
                json.dumps(["development_gate_failed"]),
                json.dumps({"feature_manifest_hash": "featurehash"}),
            ),
        )
        shadow_payload = {
            "run_id": "run-demo",
            "mode": "SHADOW_FINAL_HOLDOUT",
            "not_live_trade_recommendation": True,
            "scanner_row": shadow_row,
            "entry_rule": "next_completed_session_open",
            "planned_entry_date": "2026-05-27",
            "expected_return": shadow_row["expected_return"],
            "expected_mfe": shadow_row["expected_mfe"],
            "expected_mae": shadow_row["expected_mae"],
            "target_before_stop_probability": shadow_row["target_before_stop_probability"],
        }
        for event_id, unique_key, event_type in (
            (
                "signal-demo2-event",
                "signal|scan-demo|DEMO2|Bullish|model-demo",
                "FINAL_HOLDOUT_SIGNAL_CREATED",
            ),
            (
                "pending-demo2-event",
                "pending|scan-demo|DEMO2|Bullish|model-demo",
                "FINAL_HOLDOUT_ENTRY_PENDING",
            ),
        ):
            connection.execute(
                """
                INSERT INTO forward_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    unique_key,
                    event_type,
                    "2026-06-27T12:45:00+00:00",
                    "2026-05-26",
                    "DEMO2",
                    "Bullish",
                    "model-demo",
                    "scan-demo",
                    "featurehash",
                    json.dumps(shadow_payload),
                ),
            )
    monkeypatch.setattr("dashboard.ui.components.resolve_project_root", lambda _: tmp_path)

    def fail_download(*_: object, **__: object) -> None:
        raise AssertionError("Command Center page load attempted an FMP download")

    monkeypatch.setattr("swing_rsi.data.loader.download_daily", fail_download)
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    return tmp_path


def _write_regime_cache_metadata(
    root: Path,
    *,
    include_latest_run_fields: bool = True,
    reason: str = "cache_valid",
) -> tuple[Path, Path]:
    cache_dir = root / "data" / "cache" / "regime"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "universe-cache_expanding_kmeans_regime_cache_v1.json"
    status_path = cache_dir / "universe-cache_expanding_kmeans_regime_cache_status_v1.json"
    cache_path.write_text(
        json.dumps(
            {
                "schema_version": "expanding_kmeans_regime_cache_v1",
                "universe_snapshot_id": "universe-cache",
                "feature_manifest_hash": (
                    "3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5"
                ),
                "regime_input_columns": [
                    "market_regime_trend_score",
                    "market_regime_volatility_score",
                    "breadth_advance_pct",
                    "breadth_dispersion_20",
                ],
                "kmeans_parameters": {
                    "n_clusters": 3,
                    "n_init": 10,
                    "random_state": 42,
                },
                "random_seed": 42,
                "scaler_preprocessing_configuration": {"scaler": "none"},
                "minimum_sample_requirement": 126,
                "input_prefix_hash": "input-prefix-hash",
                "full_input_hash": "full-input-hash",
                "output_dataframe_hash": "output-dataframe-hash",
                "dates_covered": ["2026-06-24", "2026-06-25", "2026-06-26"],
                "last_cached_date": "2026-06-26",
                "row_count": 5005,
                "symbols_covered": ["AAPL", "SPY"],
                "output_column_names": ["Date", "market_regime_cluster_expanding"],
                "creation_timestamp_utc": "2026-06-28T00:00:00+00:00",
                "update_timestamp_utc": "2026-06-28T00:01:00+00:00",
                "cache_validity_status": "VALID",
                "records": [],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    status_payload: dict[str, object] = {
        "schema_version": "expanding_kmeans_regime_cache_status_v1",
        "cache_schema_version": "expanding_kmeans_regime_cache_v1",
        "universe_snapshot_id": "universe-cache",
        "feature_manifest_hash": "3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5",
        "feature_builder_version": "features.py:_expanding_kmeans_regime:v1",
        "status": "HIT",
        "reason": reason,
        "cache_validity_status": "VALID",
        "cache_path": str(cache_path),
        "last_cached_date": "2026-06-26",
        "row_count": 5005,
        "update_timestamp_utc": "2026-06-28T00:02:00+00:00",
    }
    if include_latest_run_fields:
        status_payload.update(
            {
                "cached_dates_reused": 5005,
                "new_dates_computed": 0,
                "kmeans_fits_avoided": 2518,
                "kmeans_fits_performed": 0,
                "regime_runtime_seconds": 2.5,
            }
        )
    status_path.write_text(json.dumps(status_payload, sort_keys=True), encoding="utf-8")
    return cache_path, status_path


def _write_signal_discovery_generation(root: Path) -> str:
    generation_id = "signal_discovery_20260627T140500Z_fixture"
    signal_id = "signal-fixture-1"
    generation_dir = root / "artifacts" / "signal_discovery" / generation_id
    generation_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": "multi_angle_signal_discovery_v1",
        "generation_type": "signal_discovery_generation",
        "generation_id": generation_id,
        "created_at_utc": "2026-06-27T14:05:00+00:00",
        "feature_manifest_hash": "featurehash",
        "hypotheses_evaluated": 2,
    }
    candidate = {
        "signal_id": signal_id,
        "generation_id": generation_id,
        "scan_id": generation_id,
        "as_of_date": "2026-05-26",
        "ticker": "DEMO3",
        "symbol": "DEMO3",
        "direction": "Bullish",
        "action": "BUY",
        "decision": "BUY_CANDIDATE",
        "candidate_status": "SHADOW_ONLY",
        "candidate_classification": "SHADOW_ONLY",
        "edge_status": "SHADOW VALIDATION",
        "archetype": "Reversal / Exhaustion",
        "archetype_id": "reversal_exhaustion",
        "hypothesis_id": "reversal_buy_5d",
        "model_id": "reversal_buy_5d:extra_trees",
        "model_family": "extra_trees",
        "family": "extra_trees",
        "horizon": 5,
        "scope": "POOLED",
        "product_class_scope": "POOLED",
        "row_product_class_role": "stock",
        "generation": generation_id,
        "feature_snapshot_hash": "featurehash",
        "calibrated_probability": 0.68,
        "probability": 0.68,
        "target_before_stop_probability": 0.61,
        "expected_return": 0.024,
        "expected_mfe": 0.052,
        "expected_mae": -0.018,
        "signal_score": 0.72,
        "composite_signal_score": 0.72,
        "risk_adjusted_utility": 0.030,
        "ood_feature_rate": 0.0,
        "liquidity_score": 0.74,
        "footprint_support_score": 0.69,
        "historical_analog_support_score": "explanatory_only",
        "conflict_penalty": 0.0,
        "concentration_penalty": 0.0,
        "top_support": "volatility_range: atr_pct_14=0.0275",
        "top_conflict": "candle_geometry: weak local movement",
        "historical_analog_support": "Computed after selection; explanatory only.",
        "footprint_summary": "BUY reversal exhaustion footprint",
        "supporting_evidence": "volatility_range: atr_pct_14=0.0275",
        "top_divergences": "candle_geometry: weak local movement",
        "rejection_reason": "",
        "no_signal_reason": "",
        "next_required_event": "Collect prospective evidence; not live actionable without promotion.",
        "not_live_actionable_reason": "No promoted multi-angle signal model exists.",
    }
    no_signal = {
        **candidate,
        "signal_id": "signal-fixture-2",
        "ticker": "DEMO4",
        "decision": "NO_SIGNAL",
        "action": "NO SIGNAL",
        "candidate_status": "RESEARCH_ONLY",
        "candidate_classification": "RESEARCH_ONLY",
        "no_signal_reason": "probability_below_threshold",
        "footprint_summary": "reversal_buy_5d footprint incomplete or below policy threshold",
    }
    hypothesis = {
        "generation_id": generation_id,
        "schema_version": "multi_angle_signal_discovery_v1",
        "hypothesis_id": "reversal_buy_5d",
        "archetype": "Reversal / Exhaustion",
        "direction": "BUY",
        "horizon": 5,
        "family": "extra_trees",
        "status": "CANDIDATE",
        "selected_features": json.dumps(["atr_pct_14", "close_position"]),
        "train_rows": 100,
        "calibration_rows": 30,
        "holdout_rows": 30,
    }
    evidence = pd.DataFrame(
        [
            {
                "signal_id": signal_id,
                "generation_id": generation_id,
                "hypothesis_id": "reversal_buy_5d",
                "Category": "Top support",
                "Claim": "Signal footprint support is measured.",
                "Evidence": "atr_pct_14",
                "Value": "0.0275",
                "Window": "5 sessions",
                "Percentile/Rank": "Not available",
                "Comparison Instrument": "Not available",
                "Feature": "atr_pct_14",
                "Evidence Type": "supportive",
                "Strength": "moderate",
                "Missing Data Status": "available",
            },
            {
                "signal_id": signal_id,
                "generation_id": generation_id,
                "hypothesis_id": "reversal_buy_5d",
                "Category": "Top conflict",
                "Claim": "Conflicting evidence is retained.",
                "Evidence": "weak local movement",
                "Value": "weak local movement",
                "Window": "5 sessions",
                "Percentile/Rank": "Not available",
                "Comparison Instrument": "Not available",
                "Feature": "conflict_stack",
                "Evidence Type": "conflicting",
                "Strength": "moderate",
                "Missing Data Status": "available",
            },
            {
                "signal_id": signal_id,
                "generation_id": generation_id,
                "hypothesis_id": "reversal_buy_5d",
                "Category": "Residual / unexplained",
                "Claim": "Residual explanation is retained.",
                "Evidence": "unexplained component",
                "Value": "10.00%",
                "Window": "current signal",
                "Percentile/Rank": "Not available",
                "Comparison Instrument": "Not available",
                "Feature": "residual_unexplained",
                "Evidence Type": "neutral",
                "Strength": "moderate",
                "Missing Data Status": "available",
            },
        ]
    )
    analogs = pd.DataFrame(
        [
            {
                "signal_id": signal_id,
                "generation_id": generation_id,
                "hypothesis_id": "reversal_buy_5d",
                "analog_rank": 1,
                "analog_date": "2026-04-15",
                "symbol": "AAA",
                "scope": "POOLED",
                "regime": "1",
                "similarity": 0.42,
                "forward_return": 0.031,
                "MFE": 0.060,
                "MAE": -0.015,
                "target_before_stop_result": "target before stop",
                "outcome_labels_used_for_explanation_only": True,
            }
        ]
    )
    frames = {
        "summary": pd.DataFrame(
            [
                {
                    "generation_id": generation_id,
                    "created_at_utc": "2026-06-27T14:05:00+00:00",
                    "hypotheses_evaluated": 2,
                    "buy_candidates": 1,
                    "sell_candidates": 0,
                    "no_signal_rows": 1,
                    "rejected_rows": 0,
                    "top_archetypes": '{"Reversal / Exhaustion": 1}',
                }
            ]
        ),
        "hypotheses": pd.DataFrame([hypothesis]),
        "candidates": pd.DataFrame([candidate, no_signal]),
        "selected_candidates": pd.DataFrame([candidate]),
        "no_signal": pd.DataFrame([no_signal]),
        "rejected": pd.DataFrame(),
        "footprint_evidence": evidence,
        "historical_analogs": analogs,
        "score_components": pd.DataFrame(
            [
                {
                    "signal_id": signal_id,
                    "generation_id": generation_id,
                    "hypothesis_id": "reversal_buy_5d",
                    "component": "signal_score",
                    "value": 0.72,
                    "used_in_score": True,
                }
            ]
        ),
        "gate_results": pd.DataFrame(
            [
                {
                    "generation_id": generation_id,
                    "hypothesis_id": "reversal_buy_5d",
                    "gate_id": "minimum_training_samples",
                    "actual": 100,
                    "threshold": 20,
                    "status": "PASS",
                    "mandatory": True,
                    "evidence_source": "chronological_split",
                }
            ]
        ),
    }
    for name, frame in frames.items():
        frame.to_csv(generation_dir / f"{name}.csv", index=False)
    (generation_dir / "metadata.json").write_text(
        json.dumps(metadata, sort_keys=True), encoding="utf-8"
    )
    (generation_dir.parent / "latest.json").write_text(
        json.dumps({"generation_id": generation_id}, sort_keys=True), encoding="utf-8"
    )
    return generation_id


def test_dashboard_blocks_startup_from_operational_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    from swing_rsi.application import dashboard_service as service

    monkeypatch.setattr(service, "OPERATIONAL_REPOSITORY", Path("/tmp/ops"))
    monkeypatch.setattr(service, "DEVELOPMENT_REPOSITORY", Path("/tmp/dev"))
    state = dashboard_startup_state("/tmp/ops")
    assert state.is_operational_repository is True
    assert "Blocked" in state.message


def test_dashboard_identifies_development_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    from swing_rsi.application import dashboard_service as service

    monkeypatch.setattr(service, "DEVELOPMENT_REPOSITORY", Path("/tmp/dev"))
    monkeypatch.setattr(service, "OPERATIONAL_REPOSITORY", Path("/tmp/ops"))
    state = dashboard_startup_state("/tmp/dev")
    assert state.is_development_worktree is True
    assert state.requires_confirmation is False


def test_pages_load_without_fmp_key_or_mutation(
    command_center_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = command_center_root / "state" / "engine.sqlite3"
    scanner = command_center_root / "artifacts" / "scanner" / "scan-demo_scanner.csv"
    artifact = command_center_root / "artifacts" / "models" / "model.joblib"
    before_db = db.read_bytes()
    before_scanner = scanner.read_bytes()
    before_artifact = artifact.read_bytes()

    def fail_build_features(*_: object, **__: object) -> None:
        raise AssertionError("Dashboard page load attempted to run build-features")

    monkeypatch.setattr(
        "swing_rsi.application.engine_service.build_autonomous_features",
        fail_build_features,
    )
    for page in (
        "dashboard/sections/overview.py",
        "dashboard/sections/signal_board.py",
        "dashboard/sections/shadow_forward_test.py",
        "dashboard/sections/model_edge_status.py",
        "dashboard/sections/scanner_results.py",
        "dashboard/sections/candidate_detail.py",
        "dashboard/sections/product_class_research.py",
        "dashboard/sections/gate_audit.py",
        "dashboard/sections/data_universe.py",
        "dashboard/sections/reports_and_exports.py",
        "dashboard/sections/engine_commands.py",
        "dashboard/sections/baselines_legacy.py",
        "dashboard/sections/developer_diagnostics.py",
    ):
        app = AppTest.from_file(page).run(timeout=30)
        _assert_no_streamlit_exceptions(app)
    assert db.read_bytes() == before_db
    assert scanner.read_bytes() == before_scanner
    assert artifact.read_bytes() == before_artifact


def test_signal_board_displays_regime_cache_status(command_center_root: Path) -> None:
    _write_regime_cache_metadata(command_center_root)

    app = AppTest.from_file("dashboard/sections/signal_board.py").run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Regime cache status"] == "HIT"
    assert metrics["Last cached date"] == "2026-06-26"
    assert metrics["KMeans fits avoided"] == "2,518"
    assert metrics["Regime runtime"] == "2.50 seconds"
    assert metrics["Cache validity reason"] == "cache_valid"
    assert any(
        "Regime cache preserves exact feature semantics" in caption.value for caption in app.caption
    )


def test_developer_diagnostics_displays_regime_cache_section(
    command_center_root: Path,
) -> None:
    _write_regime_cache_metadata(command_center_root)

    app = AppTest.from_file("dashboard/sections/developer_diagnostics.py").run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    assert "Regime KMeans Cache" in {subheader.value for subheader in app.subheader}
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Regime cache status"] == "HIT"
    assert metrics["KMeans fits avoided"] == "2,518"
    assert metrics["KMeans fits performed"] == "0"
    assert metrics["Regime runtime"] == "2.50 seconds"
    assert any("Nothing required. build-features is using" in info.value for info in app.info)


def test_missing_regime_cache_metadata_displays_not_found(
    command_center_root: Path,
) -> None:
    frames = regime_cache_detail_frames(command_center_root)
    summary = frames["summary"].iloc[0]

    assert summary["status"] == "NOT_FOUND"
    assert summary["validity_reason"] == "cache_missing"

    app = AppTest.from_file("dashboard/sections/signal_board.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Regime cache status"] == "Not found"
    assert metrics["Last cached date"] == "Not available"
    assert metrics["KMeans fits avoided"] == "Not available"
    assert metrics["Regime runtime"] == "Not available"
    assert metrics["Cache validity reason"] == "Not available"


def test_regime_cache_missing_fields_display_not_available(command_center_root: Path) -> None:
    _write_regime_cache_metadata(command_center_root, include_latest_run_fields=False)

    summary = regime_cache_detail_frames(command_center_root)["summary"].iloc[0]

    assert summary["status"] == "HIT"
    assert summary["validity_reason"] == "cache_valid"
    assert summary["kmeans_fits_avoided"] == "Not available"
    assert summary["kmeans_fits_performed"] == "Not available"
    assert summary["regime_runtime_seconds"] == "Not available"


def test_regime_cache_exports_csv_and_xlsx_without_secrets(command_center_root: Path) -> None:
    _write_regime_cache_metadata(
        command_center_root,
        reason="cache_valid; apikey=secret-token; FMP_API_KEY=secret-token",
    )
    frames = regime_cache_detail_frames(command_center_root)

    csv_bytes = to_csv_bytes(frames["metadata"])
    xlsx_bytes = to_xlsx_bytes(frames)
    workbook = openpyxl.load_workbook(BytesIO(xlsx_bytes))

    assert csv_bytes.startswith(b"field,value")
    assert set(workbook.sheetnames) == {"summary", "metadata", "input_columns", "kmeans_config"}
    assert b"secret-token" not in csv_bytes
    assert b"secret-token" not in xlsx_bytes
    assert b"FMP_API_KEY" not in csv_bytes
    assert b"apikey=secret-token" not in csv_bytes


def test_app_shell_exposes_password_only_fmp_settings(command_center_root: Path) -> None:
    app = AppTest.from_file("dashboard/app.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)
    labels = {widget.label for widget in app.text_input}
    assert "FMP API key" in labels
    source = Path("dashboard/ui/components.py").read_text(encoding="utf-8")
    assert 'streamlit.text_input("FMP API key", type="password", value="")' in source


def test_model_registry_and_gate_audit_load_local_state(command_center_root: Path) -> None:
    models = model_registry_frame(command_center_root)
    gates = gate_audit_frame(command_center_root)
    edges = model_edge_status_frame(command_center_root)
    assert "model-demo" in set(models["model_id"])
    assert "FAIL" in set(gates["status"])
    assert "SHADOW VALIDATION" in set(edges["edge_status"])


def test_signal_first_tables_label_live_shadow_and_missing_paths(
    command_center_root: Path,
) -> None:
    metrics = signal_board_metrics(command_center_root)
    board = signal_board_frame(command_center_root)
    scanner = scanner_results_frame(command_center_root)

    assert metrics["live_actionable_signals"] == 0
    assert metrics["shadow_paper_signals"] == 1
    assert metrics["pending_entries"] == 1
    assert "REJECTED" in set(board["live_shadow_rejected_classification"])
    assert "SHADOW ONLY" in set(board["live_shadow_rejected_classification"])
    shadow = board.loc[board["ticker"].astype(str) == "DEMO2"].iloc[0]
    assert shadow["signal_status"] == "PENDING ENTRY"
    assert shadow["model_display"] == "POOL Bull HGB 10D · model-d"
    assert shadow["generation_display"] == "Gen 2026-06-27 12:00"
    assert shadow["run_display"] == "Dev Shadow Run · run-demo"
    assert shadow["event_display"] == "Pending Entry · pending-"
    assert shadow["model_id"] == "model-demo"
    assert shadow["run_id"] == "run-demo"
    assert shadow["event_id"] == "pending-demo2-event"
    assert shadow["expected_mfe"] == "Not available"
    assert shadow["expected_mae"] == "Not available"
    assert shadow["next_required_event"] == "Pending entry waits for next session open."
    assert (
        shadow["why_shadow_only"] == "This row is waiting for the next eligible session open. "
        "It is not a live trade recommendation."
    )
    joined = " ".join(scanner.astype(str).stack().tolist())
    assert "Trade signal" not in joined
    rejected = scanner.loc[scanner["candidate_classification"].astype(str) == "REJECTED"]
    assert not rejected.empty


def test_signal_board_visible_table_uses_friendly_ids_but_exports_raw_ids(
    command_center_root: Path,
) -> None:
    board = signal_board_frame(command_center_root)
    visible = signal_board_display_section(board)
    visible_shadow = visible.loc[visible["Ticker"].astype(str) == "DEMO2"].iloc[0]

    assert "Model" in visible.columns
    assert "Footprint Summary" in visible.columns
    assert "Generation" in visible.columns
    assert "Run" in visible.columns
    assert "Event" in visible.columns
    assert "Footprint Evidence" not in visible.columns
    assert "Value" not in visible.columns
    assert "Model Id" not in visible.columns
    assert "Run Id" not in visible.columns
    assert "Event Id" not in visible.columns
    assert visible_shadow["Model"] == "POOL Bull HGB 10D · model-d"
    assert visible_shadow["Footprint Summary"] == "Model evidence footprint"
    assert visible_shadow["Generation"] == "Gen 2026-06-27 12:00"
    assert visible_shadow["Run"] == "Dev Shadow Run · run-demo"
    assert visible_shadow["Event"] == "Pending Entry · pending-"

    csv_bytes = to_csv_bytes(board)
    xlsx_bytes = to_xlsx_bytes({"signal_board": board})
    workbook = openpyxl.load_workbook(BytesIO(xlsx_bytes))
    headers = [cell.value for cell in workbook["signal_board"][1]]

    assert b"model_id" in csv_bytes
    assert b"model-demo" in csv_bytes
    assert b"run_id" in csv_bytes
    assert b"run-demo" in csv_bytes
    assert b"event_id" in csv_bytes
    assert b"pending-demo2-event" in csv_bytes
    assert "model_id" in headers
    assert "run_id" in headers
    assert "event_id" in headers


def test_signal_board_displays_multi_angle_action_and_archetype(
    command_center_root: Path,
) -> None:
    generation_id = _write_signal_discovery_generation(command_center_root)

    board = signal_board_frame(command_center_root)
    visible = signal_board_display_section(board)
    discovery = visible.loc[visible["Ticker"].astype(str) == "DEMO3"].iloc[0]

    assert discovery["Action"] == "BUY"
    assert discovery["Archetype"] == "Reversal / Exhaustion"
    assert str(discovery["Signal Score"]) == "0.72"
    assert discovery["Footprint Summary"] == "BUY reversal exhaustion footprint"
    assert discovery["Top Support"] == "volatility_range: atr_pct_14=0.0275"
    assert discovery["Top Conflict"] == "candle_geometry: weak local movement"
    assert str(discovery["Open"]).startswith("/candidate-detail?")
    assert f"scan_id={generation_id}" in str(discovery["Open"])
    assert "model_id=reversal_buy_5d%3Aextra_trees" in str(discovery["Open"])


def test_signal_board_default_sections_keep_shadow_and_pending_visible(
    command_center_root: Path,
) -> None:
    db = command_center_root / "state" / "engine.sqlite3"
    before_db = db.read_bytes()

    app = AppTest.from_file("dashboard/sections/signal_board.py").run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    assert db.read_bytes() == before_db
    assert app.toggle[0].label == "Show rejected/research rows"
    assert app.toggle[0].value is False
    subheaders = {subheader.value for subheader in app.subheader}
    assert "Live Actionable Signals: 0 rows" in subheaders
    assert "Shadow / Paper Signals: 1 row" in subheaders
    assert "Pending Entries: 1 row" in subheaders
    assert "Open Shadow Positions: 0 rows" in subheaders
    assert "Closed / Matured Outcomes: 0 rows" in subheaders
    assert any(
        "No live actionable signals. Shadow and pending rows remain visible below." in info.value
        for info in app.info
    )
    assert any(
        "This row is waiting for the next eligible session open. "
        "It is not a live trade recommendation." in info.value
        for info in app.info
    )


def test_signal_board_detail_links_preselect_candidate_detail(
    command_center_root: Path,
) -> None:
    board = signal_board_frame(command_center_root)
    linked = board.loc[board["ticker"].astype(str) == "DEMO2"].iloc[0]

    assert linked["candidate_detail_url"] == candidate_detail_url(
        scan_id="scan-demo",
        ticker="DEMO2",
        model_id="model-demo",
        direction="Bullish",
        run_id="run-demo",
        event_id="pending-demo2-event",
        status="PENDING ENTRY",
    )
    assert linked["open_url"] == linked["candidate_detail_url"]
    assert linked["candidate_detail_url"].startswith("/candidate-detail?")
    assert "run_id=run-demo" in linked["open_url"]
    assert "event_id=pending-demo2-event" in linked["open_url"]
    assert "model_id=model-demo" in linked["open_url"]
    assert "ticker=DEMO2" in linked["open_url"]
    assert "direction=Bullish" in linked["open_url"]

    app = AppTest.from_file("dashboard/sections/candidate_detail.py")
    app.query_params["scan_id"] = "scan-demo"
    app.query_params["ticker"] = "DEMO2"
    app.query_params["model_id"] = "model-demo"
    app.query_params["direction"] = "Bullish"
    app.run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    assert app.selectbox[0].label == "Scan ID"
    assert app.selectbox[0].value == "scan-demo"
    assert app.selectbox[1].label == "Ticker"
    assert app.selectbox[1].value == "DEMO2"
    assert app.selectbox[2].label == "Model ID"
    assert app.selectbox[2].value == "model-demo"
    assert any(success.value == "Opened from Signal Board selection." for success in app.success)
    subheaders = {subheader.value for subheader in app.subheader}
    assert "Full Raw Identifiers" in subheaders
    assert "Footprint Evidence Table" in subheaders
    assert "Supporting Evidence" in subheaders
    assert "Conflicting Evidence" in subheaders
    assert "Historical Analogs" in subheaders
    assert "Residual / Unexplained" in subheaders
    metrics = {metric.label: metric.value for metric in app.metric}
    assert "Missing evidence rows" in metrics
    assert "Categories affected" in metrics
    assert "Top missing category" in metrics


def test_candidate_detail_displays_signal_discovery_score_breakdown(
    command_center_root: Path,
) -> None:
    generation_id = _write_signal_discovery_generation(command_center_root)
    db = command_center_root / "state" / "engine.sqlite3"
    artifact = command_center_root / "artifacts" / "models" / "model.joblib"
    before_db = db.read_bytes()
    before_artifact = artifact.read_bytes()

    app = AppTest.from_file("dashboard/sections/candidate_detail.py")
    app.query_params["scan_id"] = generation_id
    app.query_params["ticker"] = "DEMO3"
    app.query_params["model_id"] = "reversal_buy_5d:extra_trees"
    app.query_params["direction"] = "Bullish"
    app.run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    assert db.read_bytes() == before_db
    assert artifact.read_bytes() == before_artifact
    subheaders = {subheader.value for subheader in app.subheader}
    assert "Signal Score Breakdown" in subheaders
    assert "Footprint Evidence Table" in subheaders
    assert "Conflicting Evidence" in subheaders
    assert "Residual / Unexplained" in subheaders
    assert "Historical Analogs" in subheaders
    assert app.selectbox[0].value == generation_id
    assert app.selectbox[1].value == "DEMO3"
    assert app.selectbox[2].value == "reversal_buy_5d:extra_trees"


def test_candidate_detail_raw_identifier_copy_block_and_exports(
    command_center_root: Path,
) -> None:
    scanner = scanner_results_frame(command_center_root)
    candidate = scanner.loc[scanner["ticker"].astype(str) == "DEMO2"].iloc[0]
    params = {
        "scan_id": "scan-demo",
        "ticker": "DEMO2",
        "model_id": "model-demo",
        "direction": "Bullish",
        "run_id": "run-demo",
        "event_id": "pending-demo2-event",
        "status": "PENDING ENTRY",
    }

    identifiers = _raw_identifier_frame(candidate, params)
    values = dict(zip(identifiers["field"], identifiers["value"], strict=True))
    copy_text = _identifier_copy_text(identifiers)
    deep_link = _candidate_detail_deep_link(identifiers)
    deep_link_frame = _deep_link_frame(deep_link)
    xlsx_bytes = to_xlsx_bytes(
        {
            "raw_identifiers": identifiers,
            "deep_link": deep_link_frame,
        }
    )
    workbook = openpyxl.load_workbook(BytesIO(xlsx_bytes))

    assert values["scan_id"] == "scan-demo"
    assert values["ticker"] == "DEMO2"
    assert values["model_id"] == "model-demo"
    assert values["run_id"] == "run-demo"
    assert values["event_id"] == "pending-demo2-event"
    assert values["status"] == "PENDING ENTRY"
    assert values["feature_snapshot_hash"] == "featurehash"
    assert "run_id=run-demo" in copy_text
    assert "event_id=pending-demo2-event" in copy_text
    assert "model_id=model-demo" in copy_text
    assert deep_link == (
        "/candidate-detail?scan_id=scan-demo&ticker=DEMO2&model_id=model-demo"
        "&direction=Bullish&run_id=run-demo&event_id=pending-demo2-event"
        "&status=PENDING+ENTRY"
    )
    assert workbook["raw_identifiers"]["A1"].value == "field"
    assert workbook["deep_link"]["A1"].value == "field"
    assert workbook["deep_link"]["B2"].value == deep_link
    workbook_values = [
        workbook["raw_identifiers"].cell(row=row, column=3).value
        for row in range(2, workbook["raw_identifiers"].max_row + 1)
    ]
    assert "pending-demo2-event" in workbook_values


def _write_tza_footprint_fixture(root: Path) -> pd.Series:
    feature_dir = root / "data" / "features"
    feature_dir.mkdir(parents=True, exist_ok=True)
    config_dir = root / "configs" / "universe"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "core.yaml").write_text(
        """
name: footprint-test
provider: fmp
default_start: "2020-01-01"
symbols:
  - symbol: TZA
    enabled: true
    role: leveraged_inverse_etf
  - symbol: RWM
    enabled: true
    role: inverse_etf
  - symbol: IWM
    enabled: true
    role: broad_market_etf
  - symbol: SPY
    enabled: true
    role: broad_market_etf
  - symbol: QQQ
    enabled: true
    role: broad_market_etf
  - symbol: DIA
    enabled: true
    role: broad_market_etf
relationships:
  - source: IWM
    related: [RWM, TZA]
""",
        encoding="utf-8",
    )
    date = pd.Timestamp("2026-06-26")
    rows = [
        {
            "Date": date,
            "symbol": "TZA",
            "return_1": 0.031,
            "return_5": 0.082,
            "return_10": 0.121,
            "return_20": 0.184,
            "momentum_20_percentile_252": 0.92,
            "relative_volume_20": 1.44,
            "range_percentile_63": 0.81,
            "iwm_return_5": -0.024,
            "iwm_return_20": -0.071,
            "spy_return_5": -0.011,
            "spy_return_20": -0.032,
            "qqq_return_5": -0.015,
            "qqq_return_20": -0.041,
            "dia_return_5": -0.006,
            "dia_return_20": -0.019,
            "relative_return_vs_spy_20": 0.216,
            "relative_return_vs_qqq_20": 0.225,
            "relative_return_vs_iwm_20": 0.255,
            "relative_return_vs_dia_20": 0.203,
            "relationship_corr_iwm_tza_63": -0.94,
            "relationship_divergence_iwm_tza_5": 0.018,
            "relationship_mutual_info_iwm_tza_63": 2.12,
            "inverse_confirmation_iwm_tza_63": 0.94,
            "relationship_breakdown_iwm_tza_63": 0.0,
            "atr_pct_14": 0.071,
            "realized_vol_20": 0.046,
            "volatility_expansion_20_63": 1.23,
            "market_regime_label": "uptrend_high_vol",
            "regime_conditioned_return_20": 0.028,
        },
        {
            "Date": date,
            "symbol": "RWM",
            "return_20": 0.052,
        },
        {
            "Date": date,
            "symbol": "IWM",
            "return_20": -0.071,
        },
        {
            "Date": date,
            "symbol": "SPY",
            "return_20": -0.032,
        },
        {
            "Date": date,
            "symbol": "QQQ",
            "return_20": -0.041,
        },
        {
            "Date": date,
            "symbol": "DIA",
            "return_20": -0.019,
        },
    ]
    pd.DataFrame(rows).to_parquet(feature_dir / "footprint_features.parquet", index=False)
    analogs = [
        {
            "Date": "2024-05-01T00:00:00",
            "symbol": "TZA",
            "scope": "POOLED",
            "regime": "uptrend_high_vol",
            "distance": 1.25,
            "label_bull_forward_return_10": 0.071,
            "label_bull_mfe_10": 0.119,
            "label_bull_mae_10": -0.041,
            "label_bull_target_before_stop_10": 1.0,
        },
        {
            "Date": "2024-05-02T00:00:00",
            "symbol": "RWM",
            "scope": "POOLED",
            "regime": "uptrend_high_vol",
            "distance": 1.75,
            "label_bull_forward_return_10": -0.014,
            "label_bull_mfe_10": 0.033,
            "label_bull_mae_10": -0.052,
            "label_bull_target_before_stop_10": 0.0,
        },
    ]
    return pd.Series(
        {
            "ticker": "TZA",
            "direction": "Bullish",
            "as_of_date": "2026-06-26",
            "status": "PENDING ENTRY",
            "scope": "POOLED",
            "regime": "uptrend_high_vol",
            "rejection_reason": "model_not_promoted",
            "historical_analogs": json.dumps(analogs),
            "top_divergences": "relationship_divergence_iwm_tza_5 abnormal at 1.80%",
            "top_attribution_category": (
                "inverse_leveraged:35.0%; relationship_graph:25.0%; "
                "regime:20.0%; residual/unexplained:20.0%"
            ),
        }
    )


def test_footprint_evidence_quantifies_tza_shadow_candidate(tmp_path: Path) -> None:
    candidate = _write_tza_footprint_fixture(tmp_path)
    frames = footprint_evidence_frames(tmp_path, candidate)
    evidence = frames.evidence

    assert not evidence.empty
    assert evidence["Claim"].str.strip().ne("").all()
    assert evidence["Evidence"].astype(str).str.strip().ne("").all()
    assert set(evidence["Missing Data Status"]).issubset({"available", EVIDENCE_UNAVAILABLE})
    inverse = evidence.loc[evidence["Category"] == "Expanding inverse ETF strength"]
    assert not inverse.empty
    assert "return_5" in set(inverse["Feature"])
    assert inverse.loc[inverse["Feature"] == "return_5", "Value"].iloc[0] == "8.20%"
    relationship = evidence.loc[evidence["Feature"] == "relationship_corr_iwm_tza_63"].iloc[0]
    assert relationship["Value"] == "-0.9400"
    assert relationship["Evidence Type"] == "supportive"
    assert not frames.conflicting_evidence.empty
    assert not frames.residual_unexplained.empty


def test_missing_evidence_audit_counts_unavailable_rows_by_category(tmp_path: Path) -> None:
    candidate = pd.Series(
        {
            "ticker": "TZA",
            "direction": "Bullish",
            "as_of_date": "2026-06-26",
            "status": "PENDING ENTRY",
        }
    )
    frames = footprint_evidence_frames(tmp_path, candidate)
    audit = missing_evidence_audit_frame(frames.evidence)

    assert not audit.empty
    assert audit["Unavailable Evidence Rows"].sum() > 0
    assert audit["Status"].eq("Evidence unavailable").any()
    inverse = audit.loc[audit["Category"] == "Expanding inverse ETF strength"].iloc[0]
    assert inverse["Unavailable Evidence Rows"] > 0
    assert inverse["Total Evidence Rows"] > 0
    assert str(inverse["Unavailable Share"]).endswith("%")


def test_footprint_analogs_conflicts_residual_and_exports(tmp_path: Path) -> None:
    candidate = _write_tza_footprint_fixture(tmp_path)
    frames = footprint_evidence_frames(tmp_path, candidate)
    workbook = openpyxl.load_workbook(
        BytesIO(
            to_xlsx_bytes(
                {
                    "footprint_summary": frames.summary,
                    "footprint_evidence": frames.evidence,
                    "supporting_evidence": frames.supporting_evidence,
                    "conflicting_evidence": frames.conflicting_evidence,
                    "historical_analogs": frames.historical_analogs,
                    "residual_unexplained": frames.residual_unexplained,
                }
            )
        )
    )

    assert set(
        [
            "footprint_summary",
            "footprint_evidence",
            "supporting_evidence",
            "conflicting_evidence",
            "historical_analogs",
            "residual_unexplained",
        ]
    ).issubset(set(workbook.sheetnames))
    assert {
        "analog_date",
        "symbol",
        "similarity",
        "forward_return",
        "MFE",
        "MAE",
        "target_before_stop_result",
    }.issubset(frames.historical_analogs.columns)
    assert "target before stop" in set(frames.historical_analogs["target_before_stop_result"])
    assert frames.conflicting_evidence["Category"].eq("Conflicting evidence").any()
    assert frames.residual_unexplained["score"].iloc[0] == "20.00%"


def test_complete_engine_snapshot_export_contains_required_sheets(
    command_center_root: Path,
    tmp_path: Path,
) -> None:
    frames = complete_engine_snapshot_frames(command_center_root)
    xlsx_bytes = to_xlsx_bytes(frames)
    workbook_path = tmp_path / "complete_snapshot.xlsx"
    workbook_path.write_bytes(xlsx_bytes)
    workbook = openpyxl.load_workbook(workbook_path)
    assert set(workbook.sheetnames) == {
        "signal_board",
        "shadow_forward_status",
        "model_edge_status",
        "scanner_results",
        "gate_audit",
        "product_class_research",
        "candidate_attribution",
        "data_universe",
        "reports_index",
    }
    assert workbook["signal_board"]["A1"].value == "ticker"
    assert "secret" not in workbook_path.read_bytes().decode("latin1", errors="ignore")


def test_reports_and_exports_displays_signal_discovery_generation(
    command_center_root: Path,
) -> None:
    _write_signal_discovery_generation(command_center_root)

    frames = signal_discovery_generation_frames(command_center_root)
    app = AppTest.from_file("dashboard/sections/reports_and_exports.py").run(timeout=30)

    _assert_no_streamlit_exceptions(app)
    assert "Signal Discovery Generation" in {subheader.value for subheader in app.subheader}
    assert not frames["candidates"].empty
    workbook = openpyxl.load_workbook(
        BytesIO(
            to_xlsx_bytes(
                {
                    "summary": frames["summary"],
                    "metadata": frames["metadata"],
                    "hypotheses": frames["hypotheses"],
                    "candidates": frames["candidates"],
                    "selected_candidates": frames["selected_candidates"],
                    "no_signal": frames["no_signal"],
                    "rejected": frames["rejected"],
                    "footprint_evidence": frames["footprint_evidence"],
                    "historical_analogs": frames["historical_analogs"],
                    "score_components": frames["score_components"],
                    "gate_results": frames["gate_results"],
                }
            )
        )
    )
    assert {
        "summary",
        "metadata",
        "hypotheses",
        "candidates",
        "selected_candidates",
        "no_signal",
        "rejected",
        "footprint_evidence",
        "historical_analogs",
        "score_components",
        "gate_results",
    }.issubset(set(workbook.sheetnames))


def test_exports_create_csv_and_xlsx_without_secrets(tmp_path: Path) -> None:
    frame = pd.DataFrame([{"model_id": "m1", "return": 0.12, "note": "apikey=secret"}])
    csv_bytes = to_csv_bytes(frame)
    assert b"apikey=secret" not in csv_bytes
    xlsx_bytes = to_xlsx_bytes({"models": frame, "gates": frame})
    workbook_path = tmp_path / "test.xlsx"
    workbook_path.write_bytes(xlsx_bytes)
    workbook = openpyxl.load_workbook(workbook_path)
    assert set(workbook.sheetnames) == {"models", "gates"}
    assert workbook["models"]["A1"].value == "model_id"
    assert "secret" not in workbook_path.read_bytes().decode("latin1", errors="ignore")


def test_mixed_value_export_normalization_is_arrow_safe(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "Metric": [
                "text",
                "int",
                "float",
                "bool",
                "none",
                "nan",
                "positive_inf",
                "negative_inf",
                "secret",
            ],
            "Value": [
                "alpha",
                np.int64(7),
                3.25,
                True,
                None,
                np.nan,
                np.inf,
                -np.inf,
                "FMP_API_KEY=super-secret",
            ],
        }
    )

    normalized = normalize_table_for_export(frame)

    assert str(normalized["Value"].dtype) == "string"
    values = normalized["Value"].tolist()
    assert "0" not in values
    assert "Not available" in values
    assert "∞" in values
    assert "-∞" in values
    assert "7" in values
    assert "3.25" in values
    assert "True" in values
    assert not any("FMP_API_KEY" in value or "super-secret" in value for value in values)

    csv_bytes = to_csv_bytes(frame)
    assert b"Not available" in csv_bytes
    assert b"FMP_API_KEY" not in csv_bytes
    assert b"super-secret" not in csv_bytes

    xlsx_bytes = to_xlsx_bytes({"mixed": frame})
    workbook_path = tmp_path / "mixed.xlsx"
    workbook_path.write_bytes(xlsx_bytes)
    workbook = openpyxl.load_workbook(workbook_path)
    sheet_values = [cell.value for cell in workbook["mixed"]["B"][1:]]
    assert "Not available" in sheet_values
    assert "∞" in sheet_values
    assert "-∞" in sheet_values

    parquet_buffer = BytesIO()
    normalized.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)
    round_trip = pd.read_parquet(parquet_buffer)
    assert round_trip["Value"].tolist() == values


def test_export_normalization_preserves_numeric_tables() -> None:
    frame = pd.DataFrame(
        {
            "metric": ["a", "b", "c"],
            "value": [1, 2, 3],
            "rate": [0.1, np.nan, 0.3],
        }
    )

    normalized = normalize_table_for_export(frame)

    assert pd.api.types.is_integer_dtype(normalized["value"])
    assert pd.api.types.is_float_dtype(normalized["rate"])
    assert pd.isna(normalized.loc[1, "rate"])


def test_save_xlsx_report_uses_ignored_dashboard_export_directory(tmp_path: Path) -> None:
    output = save_xlsx_report(tmp_path, "sample.xlsx", pd.DataFrame([{"a": 1}]))
    assert output.relative_to(tmp_path).as_posix() == "reports/dashboard_exports/sample.xlsx"


def test_dashboard_export_directory_is_git_ignored() -> None:
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "reports/dashboard_exports/" in ignore
    assert "reports/dashboard_command_logs/" in ignore


def test_engine_commands_exclude_discovery_and_promotion(command_center_root: Path) -> None:
    labels = {spec.label for spec in command_specs(fmp_configured=False)}
    assert "discover-models" not in labels
    assert "promote-model" not in labels
    assert "universe-update" not in labels


def test_engine_command_buttons_require_confirmation_and_disable_mutations(
    command_center_root: Path,
) -> None:
    app = AppTest.from_file("dashboard/sections/engine_commands.py").run(timeout=30)
    _assert_no_streamlit_exceptions(app)

    buttons = {button.label: button for button in app.button}
    assert buttons["Run selected command"].disabled is True
    for label in (
        "discover-models disabled",
        "promote-model disabled",
        "final-holdout-init disabled",
        "forward-update disabled",
    ):
        assert buttons[label].disabled is True

    app.checkbox[0].set_value(True)
    app.run(timeout=30)
    _assert_no_streamlit_exceptions(app)
    buttons = {button.label: button for button in app.button}
    assert buttons["Run selected command"].disabled is False


def test_command_runner_refuses_operational_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    from swing_rsi.application import dashboard_service as service

    monkeypatch.setattr(service, "OPERATIONAL_REPOSITORY", Path("/tmp/ops"))
    monkeypatch.setattr(service, "DEVELOPMENT_REPOSITORY", Path("/tmp/dev"))
    spec = CommandSpec("test", "test", (sys.executable, "-c", "print('ok')"), mutates=False)
    with pytest.raises(ValueError, match="operational"):
        run_dashboard_command("/tmp/ops", spec)


def test_command_runner_captures_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from swing_rsi.application import dashboard_service as service

    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(service, "DEVELOPMENT_REPOSITORY", tmp_path)
    monkeypatch.setattr(service, "OPERATIONAL_REPOSITORY", tmp_path / "ops")
    spec = CommandSpec("test", "test", (sys.executable, "-c", "print('ok')"), mutates=False)
    result = run_dashboard_command(tmp_path, spec)
    assert result.return_code == 0
    assert "ok" in result.stdout
    assert result.log_path.exists()


def test_fmp_settings_button_backend_writes_dev_env_without_echoing_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from swing_rsi.application import dashboard_service as service

    monkeypatch.setattr(service, "DEVELOPMENT_REPOSITORY", tmp_path)
    monkeypatch.setattr(service, "OPERATIONAL_REPOSITORY", tmp_path / "ops")
    result = save_development_fmp_settings(root=tmp_path, api_key="abc123")
    assert result.fmp_configured is True
    assert "abc123" not in str(result)
    assert (tmp_path / ".env").exists()
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("FMP_BASE_URL", raising=False)
