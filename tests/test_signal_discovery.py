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
    SIGNAL_DISCOVERY_GENERATION_TYPE,
    SIGNAL_DISCOVERY_SCHEMA_VERSION,
    default_archetype_registry,
    default_hypothesis_registry,
    export_signal_discovery_blocker_report,
    export_signal_discovery_generation,
    load_signal_discovery_frames,
    run_signal_discovery,
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


def test_signal_discovery_persists_candidates_rejections_scores_and_analogs(
    signal_discovery_root: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = signal_discovery_root
    before_db = (root / "state" / "engine.sqlite3").read_bytes()

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
    selected_feature_payloads = frames["hypotheses"]["selected_features"].dropna()
    assert not selected_feature_payloads.empty
    for payload in selected_feature_payloads:
        selected = json.loads(payload)
        assert not any(str(feature).startswith("label_") for feature in selected)
    assert (root / "state" / "engine.sqlite3").read_bytes() == before_db


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
                }
            )
        )
    )

    assert "candidates.csv" in written_names
    assert "metadata.json" in written_names
    assert {
        "signal_discovery_summary",
        "hypothesis_summary",
        "candidate_rows",
        "no_signal_rows",
        "rejected_rows",
        "footprint_evidence",
        "historical_analogs",
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
