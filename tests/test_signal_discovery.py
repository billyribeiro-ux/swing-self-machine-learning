from __future__ import annotations

import json
import math
from io import BytesIO
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from swing_rsi.application.dashboard_exports import to_xlsx_bytes
from swing_rsi.engine.signal_discovery import (
    CALIBRATION_DIAGNOSTIC_THRESHOLDS,
    MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
    SIGNAL_DISCOVERY_GENERATION_TYPE,
    SIGNAL_DISCOVERY_SCHEMA_VERSION,
    default_archetype_registry,
    default_hypothesis_registry,
    export_signal_discovery_blocker_report,
    export_signal_discovery_generation,
    historical_analog_robustness_frames_from_analogs,
    load_signal_discovery_frames,
    run_signal_discovery,
    signal_discovery_analog_robustness_frames,
    signal_discovery_blocked_analog_frames,
    signal_discovery_blocker_report_frames,
)


def _write_universe(root: Path) -> None:
    config_dir = root / "configs" / "universe"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "core.yaml").write_text(
        """
name: signal-discovery-test
provider: fmp
default_start: "2020-01-01"
symbols:
  - symbol: AAA
    enabled: true
    role: stock
    sector: test
  - symbol: BBB
    enabled: true
    role: stock
    sector: test
  - symbol: CCC
    enabled: true
    role: ordinary_etf
    sector: test
  - symbol: TZA
    enabled: true
    role: leveraged_inverse_etf
relationships:
  - source: IWM
    related: [TZA]
""",
        encoding="utf-8",
    )


def _write_config(
    root: Path,
    *,
    signal_score_threshold: float = 0.10,
    probability_threshold: float = 0.10,
    candidate_cap: int = 1,
) -> Path:
    config_dir = root / "configs" / "signal_discovery"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "test_v1.yaml"
    path.write_text(
        f"""
schema_version: multi_angle_signal_discovery_v1
enabled_hypotheses:
  - reversal_buy_5d
  - reversal_sell_5d
horizons: [5]
product_scopes: [POOLED, ORDINARY, LEVERAGED_INVERSE]
model_families:
  - hist_gradient_boosting
  - extra_trees
minimum_training_samples: 120
minimum_calibration_samples: 24
minimum_holdout_samples: 24
max_selected_features: 10
analog_count: 3
candidate_cap_per_hypothesis: {candidate_cap}
random_seed: 17
research_start: "2026-01-01"
research_end:
costs:
  round_trip_bps: 5.0
selection_policy:
  reference: signal_discovery_policy_test_v1
  probability: {probability_threshold}
  target_before_stop: 0.10
  expected_return: -0.10
  signal_score: {signal_score_threshold}
ood_policy:
  reference: prediction_ood_governance_test_v1
  feature_rate_limit: 1.00
""",
        encoding="utf-8",
    )
    return path


def _write_feature_data(root: Path, *, db_marker: bool = False) -> None:
    feature_dir = root / "data" / "features"
    feature_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir = root / "data" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "AAA.json").write_text('{"symbol":"AAA","hash":"raw"}', encoding="utf-8")
    if db_marker:
        state_dir = root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "engine.sqlite3").write_bytes(b"final-holdout-marker")

    dates = pd.bdate_range("2026-01-01", periods=90)
    symbols = ("AAA", "BBB", "CCC", "TZA")
    rows: list[dict[str, object]] = []
    for date_index, date in enumerate(dates):
        for symbol_index, symbol in enumerate(symbols):
            phase = date_index / 6.0 + symbol_index * 0.7
            role = "leveraged_inverse_etf" if symbol == "TZA" else "stock"
            return_5 = 0.025 * math.sin(phase)
            return_20 = 0.030 * math.cos(phase / 1.7)
            close_position = 0.50 + 0.40 * math.sin(phase / 2.1)
            atr = 0.018 + 0.012 * abs(math.sin(phase / 1.9))
            score = 0.70 * return_5 + 0.05 * (close_position - 0.50) - 0.25 * atr
            bull_forward = score + 0.010 * (1 if (date_index + symbol_index) % 3 == 0 else -0.4)
            bear_forward = -bull_forward + 0.004 * (
                1 if (date_index + symbol_index) % 4 == 0 else -0.2
            )
            rows.append(
                {
                    "Date": date,
                    "symbol": symbol,
                    "role": role,
                    "Open": 100.0 + date_index + symbol_index,
                    "High": 101.0 + date_index + symbol_index,
                    "Low": 99.0 + date_index + symbol_index,
                    "Close": 100.5 + date_index + symbol_index,
                    "Volume": 1_000_000 + date_index * 1000 + symbol_index,
                    "return_5": return_5,
                    "return_20": return_20,
                    "momentum_20_percentile_252": ((date_index + symbol_index) % 20) / 19,
                    "trend_persistence_20": return_20 * 2.0,
                    "range_position_20": close_position,
                    "distance_prior_high_20": 0.02 - return_5,
                    "atr_pct_14": atr,
                    "realized_vol_20": atr * 1.2,
                    "volatility_expansion_20_63": 0.9 + atr * 8.0,
                    "close_position": close_position,
                    "upper_wick_pct": 0.15 + 0.03 * symbol_index,
                    "lower_wick_pct": 0.20 - 0.02 * symbol_index,
                    "relative_volume_20": 1.0 + 0.01 * date_index,
                    "dollar_volume": 8_000_000 + 50_000 * date_index,
                    "relative_return_vs_spy_20": return_20 - 0.005,
                    "rolling_corr_vs_spy_63": 0.25,
                    "breadth_advance_pct": 0.45 + 0.01 * ((date_index + symbol_index) % 5),
                    "breadth_dispersion_20": 0.08 + atr,
                    "inverse_confirmation_iwm_tza_63": 0.80 if symbol == "TZA" else 0.10,
                    "relationship_mutual_info_iwm_tza_63": 1.4 if symbol == "TZA" else 0.2,
                    "relationship_breakdown_iwm_tza_63": 0.0,
                    "market_regime_trend_score": 0.3 + return_20,
                    "market_regime_volatility_score": atr * 10.0,
                    "rsi_14": 50.0 + return_5 * 100.0,
                    "label_bull_forward_return_5": bull_forward,
                    "label_bull_positive_return_5": int(bull_forward > 0.0),
                    "label_bull_mfe_5": max(bull_forward + 0.030, 0.002),
                    "label_bull_mae_5": min(bull_forward - 0.030, -0.002),
                    "label_bull_target_before_stop_5": int(bull_forward > -0.004),
                    "label_bull_time_to_target_5": 3 if bull_forward > -0.004 else 6,
                    "label_bull_time_to_stop_5": 6 if bull_forward > -0.004 else 3,
                    "label_bear_forward_return_5": bear_forward,
                    "label_bear_positive_return_5": int(bear_forward > 0.0),
                    "label_bear_mfe_5": max(bear_forward + 0.030, 0.002),
                    "label_bear_mae_5": min(bear_forward - 0.030, -0.002),
                    "label_bear_target_before_stop_5": int(bear_forward > -0.004),
                    "label_bear_time_to_target_5": 3 if bear_forward > -0.004 else 6,
                    "label_bear_time_to_stop_5": 6 if bear_forward > -0.004 else 3,
                    "label_end_date_5": dates[min(date_index + 5, len(dates) - 1)],
                }
            )
    modeling = pd.DataFrame(rows)
    feature_columns = [column for column in modeling.columns if not column.startswith("label_")]
    features = modeling[feature_columns].copy()
    features.to_parquet(feature_dir / "universehash_testfeatures_features.parquet", index=False)
    modeling.to_parquet(feature_dir / "universehash_testfeatures_modeling.parquet", index=False)


def _write_blocked_analog_fixture(root: Path) -> None:
    feature_dir = root / "data" / "features"
    feature_dir.mkdir(parents=True, exist_ok=True)
    generation_id = "signal_discovery_20260628T193012+0000_fixture"
    generation_dir = root / "artifacts" / "signal_discovery" / generation_id
    generation_dir.mkdir(parents=True, exist_ok=True)
    labels = {
        "directional_return": "label_bull_forward_return_20",
        "positive_return": "label_bull_positive_return_20",
        "mfe": "label_bull_mfe_20",
        "mae": "label_bull_mae_20",
        "target_before_stop": "label_bull_target_before_stop_20",
        "time_to_target": "label_bull_time_to_target_20",
        "time_to_stop": "label_bull_time_to_stop_20",
        "label_end_date": "label_end_date_20",
    }
    selected_features = ["feature_a", "feature_b", "label_bull_forward_return_20"]
    target_payload = json.dumps({"feature_a": 0.0, "feature_b": 0.0})
    candidates = pd.DataFrame(
        [
            {
                "signal_id": "target-tza",
                "generation_id": generation_id,
                "as_of_date": "2026-06-26",
                "ticker": "TZA",
                "symbol": "TZA",
                "direction": "Bullish",
                "action": "NO SIGNAL",
                "decision": "NO_SIGNAL",
                "candidate_status": "RESEARCH_ONLY",
                "archetype": "Sector Rotation",
                "archetype_id": "sector_rotation",
                "hypothesis_id": "sector_rotation_buy_20d",
                "model_id": "sector_rotation_buy_20d:extra_trees",
                "model_family": "extra_trees",
                "scope": "LEVERAGED_INVERSE",
                "product_class_scope": "LEVERAGED_INVERSE",
                "selected_feature_values_json": target_payload,
                "signal_score": 0.90,
                "no_signal_reason": "target_before_stop_probability_below_threshold",
                "rejection_reason": "",
            },
            {
                "signal_id": "target-soxs",
                "generation_id": generation_id,
                "as_of_date": "2026-06-26",
                "ticker": "SOXS",
                "symbol": "SOXS",
                "direction": "Bullish",
                "action": "BUY",
                "decision": "REJECTED_BY_OOD",
                "candidate_status": "REJECTED_BY_OOD",
                "archetype": "Sector Rotation",
                "archetype_id": "sector_rotation",
                "hypothesis_id": "sector_rotation_buy_20d",
                "model_id": "sector_rotation_buy_20d:extra_trees",
                "model_family": "extra_trees",
                "scope": "LEVERAGED_INVERSE",
                "product_class_scope": "LEVERAGED_INVERSE",
                "selected_feature_values_json": json.dumps({"feature_a": 0.02, "feature_b": 0.01}),
                "signal_score": 0.80,
                "no_signal_reason": "",
                "rejection_reason": "ood_feature_rate_above_limit",
            },
            {
                "signal_id": "target-prob",
                "generation_id": generation_id,
                "as_of_date": "2026-06-26",
                "ticker": "AAA",
                "symbol": "AAA",
                "direction": "Bullish",
                "action": "NO SIGNAL",
                "decision": "NO_SIGNAL",
                "candidate_status": "RESEARCH_ONLY",
                "archetype": "Sector Rotation",
                "archetype_id": "sector_rotation",
                "hypothesis_id": "sector_rotation_buy_20d",
                "model_id": "sector_rotation_buy_20d:extra_trees",
                "model_family": "extra_trees",
                "scope": "ORDINARY",
                "product_class_scope": "ORDINARY",
                "selected_feature_values_json": json.dumps({"feature_a": 0.03, "feature_b": 0.02}),
                "signal_score": 0.70,
                "no_signal_reason": "probability_below_threshold",
                "rejection_reason": "",
            },
        ]
    )
    hypotheses = pd.DataFrame(
        [
            {
                "generation_id": generation_id,
                "hypothesis_id": "sector_rotation_buy_20d",
                "archetype": "Sector Rotation",
                "direction": "BUY",
                "horizon": 20,
                "family": "extra_trees",
                "status": "CANDIDATE",
                "outcome_labels": json.dumps(labels, sort_keys=True),
                "selected_features": json.dumps(selected_features),
            }
        ]
    )
    modeling_rows = [
        ("2026-06-22", "TZA", "leveraged_inverse_etf", 0.01, 0.00, 0.04, 0.09, -0.02, 1),
        ("2026-06-19", "SQQQ", "leveraged_inverse_etf", 0.30, 0.25, -0.02, 0.03, -0.05, 0),
        ("2026-06-18", "AAA", "stock", 0.00, 0.00, 0.03, 0.06, -0.01, 1),
        ("2026-06-17", "BBB", "stock", 0.04, 0.02, -0.01, 0.02, -0.04, 0),
        ("2026-06-26", "TZA", "leveraged_inverse_etf", 0.00, 0.00, 0.99, 1.20, -0.90, 1),
        ("2026-06-29", "SOXS", "leveraged_inverse_etf", 0.02, 0.01, 0.88, 1.10, -0.80, 1),
    ]
    modeling = pd.DataFrame(
        [
            {
                "Date": date,
                "symbol": symbol,
                "role": role,
                "feature_a": feature_a,
                "feature_b": feature_b,
                "market_regime_cluster_expanding": "fixture",
                "label_bull_forward_return_20": forward_return,
                "label_bull_positive_return_20": int(forward_return > 0.0),
                "label_bull_mfe_20": mfe,
                "label_bull_mae_20": mae,
                "label_bull_target_before_stop_20": tbs,
                "label_bull_time_to_target_20": 5,
                "label_bull_time_to_stop_20": 8,
                "label_end_date_20": "2026-07-24",
            }
            for (
                date,
                symbol,
                role,
                feature_a,
                feature_b,
                forward_return,
                mfe,
                mae,
                tbs,
            ) in modeling_rows
        ]
    )
    pd.DataFrame([{"generation_id": generation_id}]).to_csv(
        generation_dir / "summary.csv", index=False
    )
    hypotheses.to_csv(generation_dir / "hypotheses.csv", index=False)
    candidates.to_csv(generation_dir / "candidates.csv", index=False)
    candidates.loc[candidates["decision"].eq("NO_SIGNAL")].to_csv(
        generation_dir / "no_signal.csv", index=False
    )
    candidates.loc[candidates["decision"].str.startswith("REJECTED")].to_csv(
        generation_dir / "rejected.csv", index=False
    )
    pd.DataFrame().to_csv(generation_dir / "selected_candidates.csv", index=False)
    pd.DataFrame().to_csv(generation_dir / "footprint_evidence.csv", index=False)
    pd.DataFrame().to_csv(generation_dir / "historical_analogs.csv", index=False)
    pd.DataFrame().to_csv(generation_dir / "score_components.csv", index=False)
    pd.DataFrame().to_csv(generation_dir / "gate_results.csv", index=False)
    (generation_dir / "metadata.json").write_text(
        json.dumps({"generation_id": generation_id}, sort_keys=True), encoding="utf-8"
    )
    (generation_dir.parent / "latest.json").write_text(
        json.dumps({"generation_id": generation_id}, sort_keys=True), encoding="utf-8"
    )
    modeling.to_parquet(feature_dir / "fixturehash_blockedanalog_modeling.parquet", index=False)


def _analog_row(
    rank: int,
    *,
    target: str = "target-robust",
    ticker: str,
    year: int,
    day: int,
    regime: str,
    forward_return: float,
    tbs: bool,
    mae: float = -0.03,
    same_symbol: bool = False,
) -> dict[str, object]:
    return {
        "target_row_id": target,
        "target_signal_id": target,
        "generation_id": "robustness-fixture",
        "target_as_of_date": "2026-06-26",
        "target_ticker": "SOXS",
        "target_direction": "Bearish",
        "target_archetype": "Breakout / Breakdown",
        "target_action": "NO SIGNAL",
        "target_status": "RESEARCH_ONLY",
        "target_score": 0.70,
        "target_blocker_reason": "target_before_stop_probability_below_threshold",
        "target_hypothesis_id": "breakdown_sell_10d",
        "target_model_id": "breakdown_sell_10d:extra_trees",
        "target_product_scope": "LEVERAGED_INVERSE",
        "target_selection_reason": "top_bearish",
        "analog_rank": rank,
        "analog_date": f"{year}-01-{day:02d}",
        "analog_ticker": ticker,
        "analog_scope": "LEVERAGED_INVERSE",
        "analog_direction": "Bearish",
        "analog_archetype": "Breakout / Breakdown",
        "analog_pool": "same_scope",
        "similarity_score": max(0.05, 0.90 - rank * 0.01),
        "distance_score": float(rank),
        "same_symbol": same_symbol,
        "same_product_scope": True,
        "same_archetype": True,
        "same_direction": True,
        "market_regime": regime,
        "forward_return": forward_return,
        "MFE": max(forward_return + 0.05, 0.01),
        "MAE": mae,
        "target_before_stop_result": "target before stop" if tbs else "stop before target",
        "analog_would_have_passed_current_thresholds": "not_available_existing_artifacts_only",
        "analog_rejection_reason": "not_available_existing_artifacts_only",
        "outcome_labels_used_for_explanation_only": True,
    }


def _concentrated_decay_analogs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for rank in range(1, 11):
        rows.append(
            _analog_row(
                rank,
                ticker="SOXS",
                year=2026,
                day=rank,
                regime="event_cluster",
                forward_return=0.12,
                tbs=True,
                same_symbol=True,
            )
        )
    for rank in range(11, 51):
        rows.append(
            _analog_row(
                rank,
                ticker="SOXS" if rank <= 48 else "TZA",
                year=2025 if rank <= 30 else 2024,
                day=((rank - 1) % 28) + 1,
                regime="other_regime",
                forward_return=-0.08 if rank % 2 else 0.02,
                tbs=False,
                mae=-0.25 if rank == 25 else -0.04,
                same_symbol=rank <= 48,
            )
        )
    return pd.DataFrame(rows)


def _diversified_supportive_analogs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for rank in range(1, 51):
        rows.append(
            _analog_row(
                rank,
                ticker=f"SYM{rank % 12}",
                year=2017 + (rank % 8),
                day=((rank - 1) % 28) + 1,
                regime=f"regime_{rank % 4}",
                forward_return=0.04 + (rank % 3) * 0.002,
                tbs=rank % 4 != 0,
                mae=-0.025,
                same_symbol=False,
            )
        )
    return pd.DataFrame(rows)


def _diversified_decay_analogs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for rank in range(1, 11):
        rows.append(
            _analog_row(
                rank,
                ticker=f"SYM{rank}",
                year=2016 + rank,
                day=rank,
                regime=f"regime_{rank % 5}",
                forward_return=0.08,
                tbs=True,
                same_symbol=False,
            )
        )
    for rank in range(11, 51):
        rows.append(
            _analog_row(
                rank,
                ticker=f"SYM{rank % 20}",
                year=2017 + (rank % 8),
                day=((rank - 1) % 28) + 1,
                regime=f"regime_{rank % 5}",
                forward_return=-0.05,
                tbs=False,
                same_symbol=False,
            )
        )
    return pd.DataFrame(rows)


@pytest.fixture()
def signal_discovery_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "dev"
    _write_universe(root)
    _write_feature_data(root, db_marker=True)
    config = _write_config(root)
    return root, config


def test_hypothesis_registry_loads_required_archetypes_without_privileged_rsi() -> None:
    archetypes = default_archetype_registry()
    hypotheses = default_hypothesis_registry()

    assert len(archetypes) == 10
    assert "risk_on_risk_off" in archetypes
    assert "failed_move_liquidity_trap" in archetypes
    assert any(spec.direction == "BUY" for spec in hypotheses.values())
    assert any(spec.direction == "SELL_SHORT" for spec in hypotheses.values())
    for spec in hypotheses.values():
        assert spec.archetype_id
        assert spec.direction in {"BUY", "SELL_SHORT"}
        assert spec.horizon in {3, 5, 10, 20}
        assert spec.outcome_labels
        assert spec.candidate_feature_families
        assert "rsi_family" not in spec.required_feature_families
        assert spec.validation_policy["feature_screen_split"] == "training_only"
        assert spec.validation_policy["calibration_split"] == "calibration_only"
        assert spec.validation_policy["holdout_usage"] == "evaluation_only"


def test_analog_robustness_classifies_concentrated_top10_decay_as_artifact() -> None:
    frames = historical_analog_robustness_frames_from_analogs(_concentrated_decay_analogs())
    robustness = frames["analog_robustness"].iloc[0]
    flags = set(frames["analog_caution_flags"]["caution_flag"].astype(str))

    assert robustness["original_analog_support_label"] == "SUPPORTIVE"
    assert robustness["robust_analog_support_label"] == "CONCENTRATION_ARTIFACT"
    assert bool(robustness["analog_evidence_too_concentrated"]) is True
    assert "same_symbol_concentration" in flags
    assert "same_year_concentration" in flags
    assert "analogs_mostly_same_event_cluster" in flags
    assert "support_decays_top25" in flags
    assert "support_decays_top50" in flags
    assert "tbs_support_decay" in flags
    assert "high_mae_tail_risk" in flags


def test_analog_robustness_classifies_diversified_depth_support_as_robust() -> None:
    frames = historical_analog_robustness_frames_from_analogs(_diversified_supportive_analogs())
    robustness = frames["analog_robustness"].iloc[0]
    flags = set(frames["analog_caution_flags"]["caution_flag"].astype(str))

    assert robustness["original_analog_support_label"] == "SUPPORTIVE"
    assert robustness["robust_analog_support_label"] == "ROBUST_SUPPORT"
    assert bool(robustness["analog_evidence_usable_for_research"]) is True
    assert "same_symbol_concentration" not in flags
    assert "same_year_concentration" not in flags


def test_analog_robustness_classifies_diversified_depth_decay() -> None:
    frames = historical_analog_robustness_frames_from_analogs(_diversified_decay_analogs())
    robustness = frames["analog_robustness"].iloc[0]
    flags = set(frames["analog_caution_flags"]["caution_flag"].astype(str))

    assert robustness["original_analog_support_label"] == "SUPPORTIVE"
    assert robustness["robust_analog_support_label"] == "DECAYS_WITH_DEPTH"
    assert "support_decays_top25" in flags
    assert "support_decays_top50" in flags
    assert "same_symbol_concentration" not in flags


def test_analog_robustness_low_count_is_insufficient() -> None:
    frame = _diversified_supportive_analogs().head(5)
    frames = historical_analog_robustness_frames_from_analogs(frame)
    robustness = frames["analog_robustness"].iloc[0]
    flags = set(frames["analog_caution_flags"]["caution_flag"].astype(str))

    assert robustness["robust_analog_support_label"] == "INSUFFICIENT_ANALOGS"
    assert "low_analog_count" in flags


def test_signal_discovery_persists_candidates_rejections_scores_and_analogs(
    signal_discovery_root: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = signal_discovery_root
    before_db = (root / "state" / "engine.sqlite3").read_bytes()
    model_artifact = root / "artifacts" / "models" / "model.joblib"
    model_artifact.parent.mkdir(parents=True, exist_ok=True)
    model_artifact.write_text("model-artifact-do-not-touch", encoding="utf-8")
    before_model_artifact = model_artifact.read_text(encoding="utf-8")

    def fail_download(*_: object, **__: object) -> None:
        raise AssertionError("Signal discovery attempted an FMP request")

    monkeypatch.setattr("swing_rsi.data.loader.download_daily", fail_download)
    run = run_signal_discovery(root, config_path=config)
    frames = load_signal_discovery_frames(root)

    assert run.metadata["schema_version"] == SIGNAL_DISCOVERY_SCHEMA_VERSION
    assert run.metadata["generation_type"] == SIGNAL_DISCOVERY_GENERATION_TYPE
    assert not frames["candidates"].empty
    assert not frames["selected_candidates"].empty
    assert not frames["rejected"].empty
    assert frames["rejected"]["rejection_reason"].astype(str).str.len().gt(0).all()
    assert not frames["score_components"].empty
    assert set(frames["candidates"]["candidate_status"]) <= {
        "SHADOW_ONLY",
        "RESEARCH_ONLY",
        "REJECTED_BY_POLICY",
        "REJECTED_BY_OOD",
    }
    assert "LIVE_ACTIONABLE" not in set(frames["candidates"]["candidate_status"])
    assert frames["selected_candidates"]["footprint_summary"].astype(str).str.len().gt(0).all()
    assert not frames["historical_analogs"].empty
    assert frames["historical_analogs"]["outcome_labels_used_for_explanation_only"].eq(True).all()
    candidates_by_signal = frames["candidates"].set_index("signal_id")
    for _, analog in frames["historical_analogs"].iterrows():
        candidate_date = pd.Timestamp(candidates_by_signal.loc[analog["signal_id"], "as_of_date"])
        assert pd.Timestamp(analog["analog_date"]) < candidate_date
    assert not frames["footprint_evidence"].empty
    assert "Top conflict" in set(frames["footprint_evidence"]["Category"])
    assert "Residual / unexplained" in set(frames["footprint_evidence"]["Category"])
    calibration_summary = frames["calibration_summary"]
    distributions = frames["probability_distributions"]
    thresholds = frames["diagnostic_thresholds"]
    buckets = frames["probability_buckets"]
    row_level = frames["row_level_calibration_audit"]
    manifest = frames["calibration_artifact_manifest"]
    assert not calibration_summary.empty
    assert not distributions.empty
    assert not thresholds.empty
    assert not buckets.empty
    assert not row_level.empty
    assert not manifest.empty
    assert (
        calibration_summary["schema_version"].eq(MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION).all()
    )
    evaluated = set(
        frames["hypotheses"]
        .loc[
            frames["hypotheses"]["family"].astype(str).str.len().gt(0), ["hypothesis_id", "family"]
        ]
        .itertuples(index=False, name=None)
    )
    audited = set(
        calibration_summary.loc[
            calibration_summary["model_family"].astype(str).str.len().gt(0),
            ["hypothesis_id", "model_family"],
        ].itertuples(index=False, name=None)
    )
    assert evaluated.issubset(audited)
    assert {"raw_tbs", "calibrated_tbs"}.issubset(set(distributions["probability_type"]))
    assert {
        "count_ge_030",
        "count_ge_035",
        "count_ge_040",
        "count_ge_045",
        "count_ge_050",
        "count_ge_055",
        "count_ge_060",
    }.issubset(distributions.columns)
    assert set(CALIBRATION_DIAGNOSTIC_THRESHOLDS).issubset(set(thresholds["threshold"].round(2)))
    assert thresholds["diagnostic_only"].eq(True).all()
    assert thresholds["production_target_before_stop_threshold"].eq(0.10).all()
    assert set(row_level["schema_version"]) == {MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION}
    assert "TBS_label" in row_level.columns
    assert row_level["calibration_artifact_hash"].astype(str).str.len().gt(0).all()
    assert (
        pd.to_datetime(row_level["Date"])
        .le(pd.to_datetime(calibration_summary["calibration_end_date"]).max())
        .all()
    )
    assert (
        pd.to_datetime(row_level["Date"])
        .lt(pd.to_datetime(frames["candidates"]["as_of_date"]).max())
        .all()
    )
    selected_feature_payloads = frames["hypotheses"]["selected_features"].dropna()
    assert not selected_feature_payloads.empty
    for payload in selected_feature_payloads:
        selected = json.loads(payload)
        assert not any(str(feature).startswith("label_") for feature in selected)
    assert (root / "state" / "engine.sqlite3").read_bytes() == before_db
    assert model_artifact.read_text(encoding="utf-8") == before_model_artifact


def test_signal_discovery_persists_insufficient_calibration_evidence(tmp_path: Path) -> None:
    root = tmp_path / "insufficient-calibration"
    _write_universe(root)
    _write_feature_data(root)
    config = _write_config(root)
    text = config.read_text(encoding="utf-8")
    text = text.replace("minimum_training_samples: 120", "minimum_training_samples: 20")
    text = text.replace("minimum_calibration_samples: 24", "minimum_calibration_samples: 200")
    text = text.replace("minimum_holdout_samples: 24", "minimum_holdout_samples: 20")
    config.write_text(text, encoding="utf-8")

    run_signal_discovery(root, config_path=config)
    frames = load_signal_discovery_frames(root)
    summary = frames["calibration_summary"]

    assert not summary.empty
    assert set(summary["status"]) == {"INSUFFICIENT_CALIBRATION_EVIDENCE"}
    assert set(summary["reason"]) == {"minimum_split_samples_failed"}
    assert summary["calibration_row_count"].lt(200).all()
    assert frames["probability_distributions"].empty
    assert frames["row_level_calibration_audit"].empty


def test_signal_discovery_persists_no_signal_rows(tmp_path: Path) -> None:
    root = tmp_path / "strict"
    _write_universe(root)
    _write_feature_data(root)
    config = _write_config(
        root,
        signal_score_threshold=0.99,
        probability_threshold=0.99,
        candidate_cap=10,
    )

    run_signal_discovery(root, config_path=config)
    frames = load_signal_discovery_frames(root)

    assert not frames["no_signal"].empty
    assert frames["no_signal"]["decision"].eq("NO_SIGNAL").all()
    assert frames["no_signal"]["no_signal_reason"].astype(str).str.len().gt(0).all()


def test_signal_discovery_export_and_dashboard_workbook_sheets(
    signal_discovery_root: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    root, config = signal_discovery_root
    run_signal_discovery(root, config_path=config)

    output_dir = tmp_path / "exports"
    written = export_signal_discovery_generation(root, generation="latest", output=output_dir)
    written_names = {path.name for path in written}
    frames = load_signal_discovery_frames(root)
    blocked_frames = signal_discovery_blocked_analog_frames(root)
    robustness_frames = signal_discovery_analog_robustness_frames(root)
    workbook = openpyxl.load_workbook(
        BytesIO(
            to_xlsx_bytes(
                {
                    "signal_discovery_summary": frames["summary"],
                    "hypothesis_summary": frames["hypotheses"],
                    "candidate_rows": frames["candidates"],
                    "no_signal_rows": frames["no_signal"],
                    "rejected_rows": frames["rejected"],
                    "footprint_evidence": frames["footprint_evidence"],
                    "historical_analogs": frames["historical_analogs"],
                    "blocked_row_analogs": blocked_frames["blocked_row_analogs"],
                    "blocked_row_analog_summary": blocked_frames["blocked_row_analog_summary"],
                    "analog_robustness": robustness_frames["analog_robustness"],
                    "analog_robustness_summary": robustness_frames["analog_robustness_summary"],
                    "analog_depth_comparison": robustness_frames["analog_depth_comparison"],
                    "analog_caution_flags": robustness_frames["analog_caution_flags"],
                    "calibration_summary": frames["calibration_summary"],
                    "probability_distributions": frames["probability_distributions"],
                    "probability_buckets": frames["probability_buckets"],
                    "diagnostic_thresholds": frames["diagnostic_thresholds"],
                    "row_level_calibration_audit": frames["row_level_calibration_audit"],
                    "calibration_artifact_manifest": frames["calibration_artifact_manifest"],
                }
            )
        )
    )

    assert "candidates.csv" in written_names
    assert "blocked_row_analogs.csv" in written_names
    assert "blocked_row_analog_summary.csv" in written_names
    assert "analog_robustness.csv" in written_names
    assert "analog_robustness_summary.csv" in written_names
    assert "analog_depth_comparison.csv" in written_names
    assert "analog_caution_flags.csv" in written_names
    assert "calibration_summary.csv" in written_names
    assert "calibration_summary.json" in written_names
    assert "probability_distributions.csv" in written_names
    assert "probability_buckets.csv" in written_names
    assert "diagnostic_thresholds.csv" in written_names
    assert "row_level_calibration_audit.csv" in written_names
    assert "row_level_calibration_audit.parquet" in written_names
    assert "calibration_artifact_manifest.json" in written_names
    assert "metadata.json" in written_names
    assert {
        "signal_discovery_summary",
        "hypothesis_summary",
        "candidate_rows",
        "no_signal_rows",
        "rejected_rows",
        "footprint_evidence",
        "historical_analogs",
        "blocked_row_analogs",
        "blocked_row_analog_summary",
        "analog_robustness",
        "analog_robustness_summary",
        "analog_depth_comparison",
        "analog_caution_flags",
        "calibration_summary",
        "probability_distributions",
        "probability_buckets",
        "diagnostic_thresholds",
        "row_level_calibration_audit",
        "calibration_artifact_manifest",
    }.issubset(set(workbook.sheetnames))


def test_signal_discovery_blocker_report_summarizes_reasons_and_groups(
    signal_discovery_root: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    root, config = signal_discovery_root
    run_signal_discovery(root, config_path=config)
    report = signal_discovery_blocker_report_frames(root)

    assert not report["summary"].empty
    assert not report["blocker_rows"].empty
    assert not report["by_reason"].empty
    assert not report["by_hypothesis"].empty
    assert not report["by_archetype"].empty
    assert not report["by_ticker"].empty
    assert not report["by_scope"].empty
    assert {"NO_SIGNAL", "REJECTED_BY_POLICY"}.intersection(
        set(report["blocker_rows"]["decision"].astype(str))
    )
    assert "blocker_reason" in report["by_reason"].columns
    assert "hypothesis_id" in report["by_hypothesis"].columns
    assert "archetype" in report["by_archetype"].columns
    assert "ticker" in report["by_ticker"].columns
    assert "product_class_scope" in report["by_scope"].columns
    assert "signal_id" in report["blocker_rows"].columns
    assert "model_id" in report["blocker_rows"].columns
    assert report["blocker_rows"]["model_id"].astype(str).str.len().gt(0).all()
    assert report["summary"]["blocker_rows"].iloc[0] == len(report["blocker_rows"])

    output_dir = tmp_path / "blocker_export"
    written = export_signal_discovery_blocker_report(
        root,
        generation="latest",
        output=output_dir,
    )
    names = {path.name for path in written}
    workbook = openpyxl.load_workbook(BytesIO(to_xlsx_bytes(report)))

    assert "by_reason.csv" in names
    assert "blocker_rows.csv" in names
    assert "metadata.json" in names
    assert {
        "summary",
        "metadata",
        "blocker_rows",
        "by_reason",
        "by_hypothesis",
        "by_archetype",
        "by_ticker",
        "by_scope",
    }.issubset(set(workbook.sheetnames))


def test_blocked_row_analogs_are_chronological_scope_labeled_and_explanatory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "blocked"
    _write_blocked_analog_fixture(root)
    artifact = root / "artifacts" / "models" / "model.joblib"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("do-not-touch", encoding="utf-8")
    operational = tmp_path / "operational"
    operational.mkdir()
    marker = operational / "state-marker.txt"
    marker.write_text("operational-untouched", encoding="utf-8")

    def fail_download(*_: object, **__: object) -> None:
        raise AssertionError("Blocked-row analog diagnostics attempted an FMP request")

    monkeypatch.setattr("swing_rsi.data.loader.download_daily", fail_download)
    before_artifact = artifact.read_text(encoding="utf-8")
    before_marker = marker.read_text(encoding="utf-8")

    frames = signal_discovery_blocked_analog_frames(root, analog_count=4)
    robustness_frames = signal_discovery_analog_robustness_frames(root)
    analogs = frames["blocked_row_analogs"]
    summary = frames["blocked_row_analog_summary"]
    robustness = robustness_frames["analog_robustness"]
    depth = robustness_frames["analog_depth_comparison"]
    tza_analogs = analogs.loc[analogs["target_ticker"].eq("TZA")]
    tza_summary = summary.loc[summary["target_ticker"].eq("TZA")].iloc[0]

    assert len(tza_analogs) == 4
    assert pd.to_datetime(tza_analogs["analog_date"]).lt(pd.Timestamp("2026-06-26")).all()
    assert "2026-06-26" not in set(tza_analogs["analog_date"].astype(str))
    assert "2026-06-29" not in set(analogs["analog_date"].astype(str))
    assert tza_analogs.iloc[0]["analog_ticker"] == "TZA"
    assert tza_analogs.head(2)["same_product_scope"].eq(True).all()
    assert "cross_scope_fallback" in set(tza_analogs["analog_pool"])
    assert tza_analogs["outcome_labels_used_for_explanation_only"].eq(True).all()
    assert tza_summary["same_scope_analog_count"] == 2
    assert math.isclose(float(tza_summary["average_forward_return"]), 0.01)
    assert math.isclose(float(tza_summary["average_MFE"]), 0.05)
    assert math.isclose(float(tza_summary["average_MAE"]), -0.03)
    assert math.isclose(float(tza_summary["target_before_stop_hit_rate"]), 0.5)
    assert tza_summary["analog_support_label"] == "MIXED"
    assert "explanatory only" in str(tza_summary["analog_footprint_summary"])
    assert set(summary.loc[summary["target_ticker"].eq("SOXS"), "key_caution"]) == {
        "OOD target row"
    }
    assert set(summary["target_status"]) <= {"RESEARCH_ONLY", "REJECTED_BY_OOD"}
    assert set(robustness["target_status"]) <= {"RESEARCH_ONLY", "REJECTED_BY_OOD"}
    assert set(robustness["robust_analog_support_label"]).issubset(
        {
            "INSUFFICIENT_ANALOGS",
            "MIXED_SUPPORT",
            "CONCENTRATION_ARTIFACT",
            "DECAYS_WITH_DEPTH",
            "ROBUST_SUPPORT",
            "SUPPORTIVE_BUT_CONCENTRATED",
            "WEAK_SUPPORT",
        }
    )
    assert pd.to_datetime(analogs["analog_date"]).lt(pd.Timestamp("2026-06-26")).all()
    assert depth["target_signal_id"].isin(set(robustness["target_signal_id"])).all()
    assert artifact.read_text(encoding="utf-8") == before_artifact
    assert marker.read_text(encoding="utf-8") == before_marker


def test_blocked_row_analog_exports_include_csv_and_workbook_sheets(tmp_path: Path) -> None:
    root = tmp_path / "blocked_export"
    _write_blocked_analog_fixture(root)

    output = tmp_path / "export"
    written = export_signal_discovery_generation(root, generation="latest", output=output)
    names = {path.name for path in written}
    frames = signal_discovery_blocked_analog_frames(root)
    robustness_frames = signal_discovery_analog_robustness_frames(root)
    workbook = openpyxl.load_workbook(
        BytesIO(
            to_xlsx_bytes(
                {
                    "blocked_row_analogs": frames["blocked_row_analogs"],
                    "blocked_row_analog_summary": frames["blocked_row_analog_summary"],
                    "analog_robustness": robustness_frames["analog_robustness"],
                    "analog_robustness_summary": robustness_frames["analog_robustness_summary"],
                    "analog_depth_comparison": robustness_frames["analog_depth_comparison"],
                    "analog_caution_flags": robustness_frames["analog_caution_flags"],
                }
            )
        )
    )

    assert "blocked_row_analogs.csv" in names
    assert "blocked_row_analog_summary.csv" in names
    assert "analog_robustness.csv" in names
    assert "analog_robustness_summary.csv" in names
    assert "analog_depth_comparison.csv" in names
    assert "analog_caution_flags.csv" in names
    assert {
        "blocked_row_analogs",
        "blocked_row_analog_summary",
        "analog_robustness",
        "analog_robustness_summary",
        "analog_depth_comparison",
        "analog_caution_flags",
    }.issubset(set(workbook.sheetnames))


def test_signal_discovery_leaves_operational_like_path_untouched(tmp_path: Path) -> None:
    operational = tmp_path / "operational"
    operational.mkdir()
    marker = operational / "state-marker.txt"
    marker.write_text("do-not-touch", encoding="utf-8")
    root = tmp_path / "dev"
    _write_universe(root)
    _write_feature_data(root)
    config = _write_config(root)

    before = marker.read_text(encoding="utf-8")
    run_signal_discovery(root, config_path=config)

    assert marker.read_text(encoding="utf-8") == before
