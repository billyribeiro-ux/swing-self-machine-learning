from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from dashboard.sections.model_registry import compact_registry_rows
from dashboard.ui.formatting import decimal, display_frame

import swing_rsi.engine.models as model_module
import swing_rsi.engine.scanner as scanner_module
import swing_rsi.engine.selection as selection_module
from swing_rsi.config import ProjectPaths
from swing_rsi.engine.gates import (
    GATE_VALUE_NOT_APPLICABLE,
    GATE_VALUE_NOT_AVAILABLE,
    compare_gate_values,
    gate_result_integrity_warning,
    gate_results_integrity_warnings,
    make_gate,
    profit_factor_result,
    promotion_eligibility,
)
from swing_rsi.engine.labels import LabelConfig, build_symbol_labels
from swing_rsi.engine.model_audit import build_model_audit, export_model_audit
from swing_rsi.engine.models import (
    DiscoveryConfig,
    ModelBundle,
    SelectionPolicy,
    _apply_selection_policy,
    _build_gate_results,
    eligible_modeling_frame,
    predict_bundle,
    selection_policy_from_config,
)
from swing_rsi.engine.ood import (
    PREDICTION_OOD_GOVERNANCE_VERSION,
    ood_rate_limit,
    probability_contract_metrics,
    regression_head_ood_metrics,
    severity_q99_limit,
    wilson_upper_99,
)
from swing_rsi.engine.portfolio import PortfolioBacktestConfig, backtest_scanner_candidates
from swing_rsi.engine.registry import RegisteredModel, list_models, promote_model, register_model
from swing_rsi.engine.selection import (
    CANONICAL_CANDIDATE_TIE_BREAKING_RULE,
    evaluate_candidate_policy,
)
from swing_rsi.engine.storage import dumps, engine_connection


class ConstantClassifier:
    def __init__(self, probability: float = 0.75) -> None:
        self.probability = probability

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        positive = np.full(len(frame), self.probability)
        return np.column_stack([1.0 - positive, positive])


class IdentityCalibrator:
    def predict(self, values: np.ndarray) -> np.ndarray:
        return values


class ConstantRegressor:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.full(len(frame), self.value)


def _loss_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=6)
    return pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
            "High": [101.0, 101.0, 101.0, 101.0, 101.0, 101.0],
            "Low": [99.0, 99.0, 49.0, 49.0, 49.0, 49.0],
            "Close": [100.0, 100.0, 50.0, 50.0, 50.0, 50.0],
            "Volume": [1_000_000.0] * 6,
        },
        index=dates.rename("Date"),
    )


def _candidate_rows(
    symbols: tuple[str, ...],
    *,
    status: str = "ACTIONABLE_PAPER_CANDIDATE",
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "as_of_date": "2024-01-02",
                "ticker": symbol,
                "direction": "Bullish",
                "candidate_status": status,
                "exclusion_reason": "" if status == "ACTIONABLE_PAPER_CANDIDATE" else "rejected",
                "composite_utility_score": 1.0 - index / 100.0,
                "model_id": "model-a",
                "sector": "technology",
            }
            for index, symbol in enumerate(symbols)
        ]
    )


def test_cross_sectional_row_compounding_is_not_portfolio_drawdown() -> None:
    symbols = tuple(f"S{index}" for index in range(20))
    selected_row_returns = pd.Series([-0.50] * len(symbols))
    invalid_row_sequence_drawdown = float(
        (
            (
                (1.0 + selected_row_returns).cumprod()
                / (1.0 + selected_row_returns).cumprod().cummax()
            )
            - 1.0
        ).min()
    )

    result = backtest_scanner_candidates(
        {symbol: _loss_frame() for symbol in symbols},
        _candidate_rows(symbols),
        config=PortfolioBacktestConfig(
            horizon=2,
            max_concurrent_positions=5,
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            round_trip_cost_bps=0.0,
            slippage_bps=0.0,
        ),
    )

    assert invalid_row_sequence_drawdown < -0.999
    assert result.metrics["max_drawdown"] > -0.999
    assert result.metrics["max_gross_exposure"] <= 1.0


def test_same_date_predictions_share_one_portfolio_decision_set() -> None:
    symbols = tuple(f"S{index}" for index in range(10))
    result = backtest_scanner_candidates(
        {symbol: _loss_frame() for symbol in symbols},
        _candidate_rows(symbols),
        config=PortfolioBacktestConfig(
            horizon=2,
            max_concurrent_positions=3,
            max_gross_exposure=1.0,
            max_sector_fraction=1.0,
            round_trip_cost_bps=0.0,
            slippage_bps=0.0,
        ),
    )

    assert len(result.trades) == 3
    assert result.metrics["max_gross_exposure"] <= 1.0
    assert result.candidate_audit["audit_reason"].tolist().count("max_concurrent_positions") == 7
    assert result.equity["Date"].tolist() == sorted(result.equity["Date"].tolist())


def test_rejected_candidates_do_not_enter_and_portfolio_is_deterministic() -> None:
    symbols = ("A", "B", "C")
    candidates = pd.concat(
        [
            _candidate_rows(("A", "B")),
            _candidate_rows(("C",), status="REJECTED"),
        ],
        ignore_index=True,
    )
    frames = {symbol: _loss_frame() for symbol in symbols}
    config = PortfolioBacktestConfig(
        horizon=2,
        max_concurrent_positions=3,
        max_sector_fraction=1.0,
    )

    first = backtest_scanner_candidates(frames, candidates, config=config)
    second = backtest_scanner_candidates(frames, candidates, config=config)

    assert len(first.trades) == 2
    assert "rejected" in set(first.candidate_audit["audit_reason"])
    pd.testing.assert_frame_equal(first.equity, second.equity)
    pd.testing.assert_frame_equal(first.trades, second.trades)


def test_same_date_candidate_ranking_is_order_independent() -> None:
    symbols = tuple(f"S{index}" for index in range(8))
    candidates = _candidate_rows(symbols)
    shuffled = candidates.sample(frac=1.0, random_state=11).reset_index(drop=True)
    frames = {symbol: _loss_frame() for symbol in symbols}
    config = PortfolioBacktestConfig(
        horizon=2,
        max_concurrent_positions=4,
        max_gross_exposure=1.0,
        max_sector_fraction=1.0,
        round_trip_cost_bps=0.0,
        slippage_bps=0.0,
    )

    baseline = backtest_scanner_candidates(frames, candidates, config=config)
    rerun = backtest_scanner_candidates(frames, shuffled, config=config)

    assert baseline.trades["ticker"].tolist() == rerun.trades["ticker"].tolist()
    assert baseline.candidate_audit["audit_reason"].tolist().count("max_concurrent_positions") == 4


def test_same_date_equal_utility_portfolio_replay_is_order_independent() -> None:
    symbols = ("D", "B", "A", "C")
    candidates = _candidate_rows(symbols)
    candidates["composite_utility_score"] = 1.0
    shuffled = candidates.sample(frac=1.0, random_state=29).reset_index(drop=True)
    frames = {symbol: _loss_frame() for symbol in symbols}
    config = PortfolioBacktestConfig(
        horizon=2,
        max_concurrent_positions=2,
        max_gross_exposure=1.0,
        max_sector_fraction=1.0,
        round_trip_cost_bps=0.0,
        slippage_bps=0.0,
    )

    baseline = backtest_scanner_candidates(frames, candidates, config=config)
    rerun = backtest_scanner_candidates(frames, shuffled, config=config)

    assert baseline.trades["ticker"].tolist() == ["A", "B"]
    assert rerun.trades["ticker"].tolist() == ["A", "B"]
    pd.testing.assert_frame_equal(baseline.trades, rerun.trades)
    pd.testing.assert_frame_equal(baseline.equity, rerun.equity)
    pd.testing.assert_frame_equal(baseline.candidate_audit, rerun.candidate_audit)
    assert baseline.metrics == rerun.metrics


def test_research_date_filter_preserves_warmup_but_excludes_pre_start_rows() -> None:
    dates = pd.bdate_range("2015-01-02", "2026-06-18")
    frame = pd.DataFrame(
        {
            "Date": dates,
            "symbol": "AAPL",
            "feature": np.arange(len(dates), dtype=float),
            "label_end_date_10": dates + pd.offsets.BDay(10),
        }
    )

    eligible = eligible_modeling_frame(
        frame,
        DiscoveryConfig(research_start="2016-06-20", research_end="2026-06-18"),
    )

    assert pd.Timestamp(frame["Date"].min()) < pd.Timestamp("2016-06-20")
    assert pd.Timestamp(eligible["Date"].min()) >= pd.Timestamp("2016-06-20")
    assert pd.Timestamp(eligible["label_end_date_10"].max()) <= pd.Timestamp("2026-06-18")
    assert pd.Timestamp(frame["Date"].min()) == pd.Timestamp("2015-01-02")


def test_bearish_label_units_and_sign_conventions_are_decimal_returns() -> None:
    dates = pd.bdate_range("2024-01-02", periods=5)
    frame = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 94.0, 92.0, 91.0],
            "High": [101.0, 101.0, 96.0, 93.0, 92.0],
            "Low": [99.0, 95.0, 90.0, 88.0, 87.0],
            "Close": [100.0, 95.0, 92.0, 90.0, 89.0],
            "Volume": [1_000_000.0] * 5,
        },
        index=dates.rename("Date"),
    )

    labels = build_symbol_labels(frame, LabelConfig(horizons=(3,)))
    value = labels.iloc[0]

    assert value["label_bear_forward_return_3"] == pytest.approx((100.0 / 90.0) - 1.0)
    assert value["label_bear_mfe_3"] > 0
    assert value["label_bear_mae_3"] <= 0


def test_prediction_ood_v2_allows_single_ordinary_exceedance() -> None:
    train_target = pd.Series(np.linspace(-0.10, 0.10, 1_000))
    calibration_prediction = pd.Series(np.linspace(-0.02, 0.02, 500))
    holdout_prediction = pd.Series([0.101, *([0.0] * 199)])
    head_metrics = regression_head_ood_metrics(
        name="return",
        direction="bull",
        horizon=10,
        train_target=train_target,
        calibration_target=train_target.tail(500),
        holdout_target=train_target.tail(200).reset_index(drop=True),
        calibration_prediction=calibration_prediction,
        holdout_prediction=holdout_prediction,
    )
    gates = _build_gate_results(
        metrics=_base_gate_metrics(**head_metrics, prediction_sanity_ood_total=1),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    old_gate = next(
        result
        for result in gates
        if result.gate_id == "legacy_prediction_out_of_distribution_absent_deprecated"
    )
    rate_gate = next(
        result for result in gates if result.gate_id == "return_holdout_ood_rate_acceptable"
    )
    severity_gate = next(
        result for result in gates if result.gate_id == "return_holdout_ood_q99_severity_acceptable"
    )

    assert head_metrics["return_prediction_ood_count"] == 1
    assert old_gate.mandatory is False
    assert old_gate.status == "NOT_APPLICABLE"
    assert rate_gate.status == "PASS"
    assert severity_gate.status == "PASS"


def test_prediction_ood_hard_integrity_gates_fail() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            prediction_unit_contract="percent_return",
            classification_prediction_values_finite=False,
            classification_probability_contract_valid=False,
            classification_prediction_nonfinite_count=1,
            classification_probability_out_of_range_count=1,
            return_prediction_unit_contract="percent_return",
            return_prediction_values_finite=False,
            return_prediction_head_bound_mapping_valid=False,
            return_prediction_bounds_training_only=False,
            return_prediction_path_metric_sign_valid=False,
            return_holdout_prediction_nonfinite_count=1,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    statuses = {gate.gate_id: gate.status for gate in gates}

    assert statuses["classification_prediction_values_finite"] == "FAIL"
    assert statuses["classification_prediction_probability_contract_valid"] == "FAIL"
    assert statuses["classification_prediction_unit_contract_valid"] == "FAIL"
    assert statuses["return_prediction_values_finite"] == "FAIL"
    assert statuses["return_prediction_unit_contract_valid"] == "FAIL"
    assert statuses["return_prediction_head_bound_mapping_valid"] == "FAIL"
    assert statuses["return_prediction_bounds_training_only"] == "FAIL"
    assert statuses["return_prediction_path_metric_sign_valid"] == "FAIL"


def test_prediction_ood_bounds_and_limits_are_training_and_calibration_only() -> None:
    train = pd.Series(np.linspace(-0.10, 0.10, 1_000))
    calibration_prediction = pd.Series(np.linspace(-0.02, 0.02, 500))
    baseline = regression_head_ood_metrics(
        name="return",
        direction="bull",
        horizon=10,
        train_target=train,
        calibration_target=train.tail(500),
        holdout_target=pd.Series(np.linspace(-0.05, 0.05, 200)),
        calibration_prediction=calibration_prediction,
        holdout_prediction=pd.Series(np.linspace(-0.05, 0.05, 200)),
    )
    mutated_holdout = regression_head_ood_metrics(
        name="return",
        direction="bull",
        horizon=10,
        train_target=train,
        calibration_target=train.tail(500),
        holdout_target=pd.Series(np.linspace(-5.0, 5.0, 200)),
        calibration_prediction=calibration_prediction,
        holdout_prediction=pd.Series(np.linspace(-5.0, 5.0, 200)),
    )

    assert mutated_holdout["return_prediction_bound_low_train_q01"] == pytest.approx(
        baseline["return_prediction_bound_low_train_q01"]
    )
    assert mutated_holdout["return_prediction_bound_high_train_q99"] == pytest.approx(
        baseline["return_prediction_bound_high_train_q99"]
    )
    assert mutated_holdout["return_calibration_ood_rate_limit"] == pytest.approx(
        baseline["return_calibration_ood_rate_limit"]
    )
    assert mutated_holdout["return_ood_severity_q99_limit"] == pytest.approx(
        baseline["return_ood_severity_q99_limit"]
    )


def test_prediction_ood_head_direction_sign_and_probability_contracts() -> None:
    return_metrics = regression_head_ood_metrics(
        name="return",
        direction="bear",
        horizon=10,
        train_target=pd.Series(np.linspace(-0.05, 0.08, 100)),
        calibration_target=pd.Series(np.linspace(-0.03, 0.06, 50)),
        holdout_target=pd.Series(np.linspace(-0.02, 0.04, 50)),
        calibration_prediction=pd.Series(np.linspace(-0.02, 0.04, 50)),
        holdout_prediction=pd.Series(np.linspace(-0.02, 0.04, 50)),
    )
    mfe_metrics = regression_head_ood_metrics(
        name="mfe",
        direction="bear",
        horizon=10,
        train_target=pd.Series(np.linspace(0.00, 0.30, 100)),
        calibration_target=pd.Series(np.linspace(0.00, 0.20, 50)),
        holdout_target=pd.Series(np.linspace(0.00, 0.20, 50)),
        calibration_prediction=pd.Series(np.linspace(0.00, 0.20, 50)),
        holdout_prediction=pd.Series([-0.01, 0.02, 0.03]),
    )
    mae_metrics = regression_head_ood_metrics(
        name="mae",
        direction="bull",
        horizon=10,
        train_target=pd.Series(np.linspace(-0.30, 0.00, 100)),
        calibration_target=pd.Series(np.linspace(-0.20, 0.00, 50)),
        holdout_target=pd.Series(np.linspace(-0.20, 0.00, 50)),
        calibration_prediction=pd.Series(np.linspace(-0.20, 0.00, 50)),
        holdout_prediction=pd.Series([0.01, -0.02, -0.03]),
    )
    probability_metrics = probability_contract_metrics(
        calibration_probability=np.array([0.0, 0.5, 1.0]),
        holdout_probability=np.array([1.2]),
        target_calibration_probability=np.array([0.2]),
        target_holdout_probability=np.array([np.nan]),
    )

    assert return_metrics["return_ood_bound_direction"] == "bear"
    assert return_metrics["return_ood_bound_horizon"] == 10
    assert return_metrics["return_prediction_bound_high_train_q99"] != pytest.approx(
        mfe_metrics["mfe_prediction_bound_high_train_q99"]
    )
    assert mfe_metrics["mfe_prediction_path_metric_sign_valid"] is False
    assert mae_metrics["mae_prediction_path_metric_sign_valid"] is False
    assert probability_metrics["classification_probability_contract_valid"] is False
    assert probability_metrics["classification_prediction_nonfinite_count"] == 1
    assert probability_metrics["classification_probability_out_of_range_count"] == 1


def test_prediction_ood_rate_and_severity_limit_formulas() -> None:
    assert wilson_upper_99(0, 100) == pytest.approx(0.05134, rel=1e-3)
    assert ood_rate_limit(0, 1_000) == pytest.approx(0.02)
    assert ood_rate_limit(100, 100) == pytest.approx(0.05)
    assert severity_q99_limit(0.0) == pytest.approx(0.10)
    assert severity_q99_limit(1.0) == pytest.approx(0.50)


def test_prediction_ood_rate_and_severity_gates_are_inclusive() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            return_calibration_ood_rate=0.05,
            return_calibration_ood_rate_limit=0.02,
            return_holdout_ood_rate=0.02,
            return_ood_severity_q99_limit=0.10,
            return_holdout_ood_q99_severity=0.10,
            return_holdout_ood_max_severity=1.0,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    statuses = {gate.gate_id: gate.status for gate in gates}

    assert statuses["return_calibration_ood_rate_acceptable"] == "PASS"
    assert statuses["return_holdout_ood_rate_acceptable"] == "PASS"
    assert statuses["return_holdout_ood_q99_severity_acceptable"] == "PASS"
    assert statuses["return_catastrophic_prediction_extrapolation_absent"] == "PASS"

    failing = _build_gate_results(
        metrics=_base_gate_metrics(
            return_holdout_ood_rate=0.021,
            return_ood_severity_q99_limit=0.10,
            return_holdout_ood_q99_severity=0.101,
            return_holdout_ood_max_severity=1.01,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    failing_statuses = {gate.gate_id: gate.status for gate in failing}

    assert failing_statuses["return_holdout_ood_rate_acceptable"] == "FAIL"
    assert failing_statuses["return_holdout_ood_q99_severity_acceptable"] == "FAIL"
    assert failing_statuses["return_catastrophic_prediction_extrapolation_absent"] == "FAIL"


def test_legacy_prediction_ood_gate_blocks_promotion_without_v2_schema() -> None:
    legacy_gate = make_gate(
        gate_id="prediction_out_of_distribution_absent",
        gate_name="No OOD Predictions",
        category="prediction sanity",
        scope="prediction",
        metric_name="prediction_sanity_ood_total",
        threshold=0,
        comparator="==",
        actual_value=0,
        status="PASS",
        mandatory=True,
        evidence_source="legacy",
        reason="Legacy gate passed.",
        configuration_hash_value="legacy",
    )

    eligibility = promotion_eligibility((legacy_gate,))

    assert eligibility.eligible is False
    assert "legacy OOD artifacts lack V2" in " | ".join(eligibility.blocked_reasons)


def _base_gate_metrics(**overrides: object) -> dict[str, object]:
    metrics: dict[str, object] = {
        "training_samples": 300,
        "holdout_samples": 100,
        "selected_holdout_samples": 10,
        "holdout_mean_return_lcb_90": 0.01,
        "holdout_profit_factor": 1.2,
        "holdout_profit_factor_evidence_status": "AVAILABLE",
        "holdout_positive_return_sum": 0.06,
        "holdout_negative_return_abs_sum": 0.05,
        "holdout_zero_return_count": 0,
        "portfolio_max_drawdown": -0.10,
        "feature_stability_mean_abs_z": 0.5,
        "symbol_concentration_top": 0.2,
        "sector_concentration_top": 0.4,
        "holdout_double_cost_lcb_90": 0.005,
        "prediction_turnover": 0.1,
        "temporal_fold_schema_version": "temporal_fold_stability_v1",
        "temporal_fold_folds_requested": 3,
        "temporal_fold_folds_evaluated": 3,
        "temporal_fold_folds_with_selected_observations": 3,
        "temporal_fold_selected_observations_per_fold_json": "[4, 3, 3]",
        "temporal_fold_records_json": (
            '[{"fold":1,"selected_count":4,"mean_return":0.01,"positive":true,'
            '"result":"positive"},'
            '{"fold":2,"selected_count":3,"mean_return":0.02,"positive":true,'
            '"result":"positive"},'
            '{"fold":3,"selected_count":3,"mean_return":-0.01,"positive":false,'
            '"result":"negative_or_zero"}]'
        ),
        "temporal_fold_positive_fraction": 0.7,
        "temporal_fold_evidence_status": "AVAILABLE",
        "temporal_fold_evidence_unavailable_reason": "",
        "temporal_fold_threshold": 0.5,
        "temporal_fold_evidence_gate_status": "PASS",
        "temporal_fold_threshold_gate_status": "PASS",
        "exceptional_period_concentration_top": 0.3,
        "rsi_control_columns_available": True,
        "prediction_unit_contract": "decimal_return",
        "prediction_ood_governance_version": PREDICTION_OOD_GOVERNANCE_VERSION,
        "prediction_values_finite": True,
        "prediction_probability_contract_valid": True,
        "prediction_head_bound_mapping_valid": True,
        "prediction_bounds_training_only": True,
        "prediction_path_metric_sign_valid": True,
        "classification_prediction_values_finite": True,
        "classification_probability_contract_valid": True,
        "classification_prediction_nonfinite_count": 0,
        "classification_probability_out_of_range_count": 0,
        "prediction_sanity_ood_total": 0,
        "selected_observation_rate": 0.1,
    }
    for head in ("return", "mfe", "mae"):
        metrics.update(
            {
                f"{head}_prediction_ood_governance_version": PREDICTION_OOD_GOVERNANCE_VERSION,
                f"{head}_prediction_unit_contract": "decimal_return",
                f"{head}_prediction_head_bound_mapping_valid": True,
                f"{head}_prediction_bounds_training_only": True,
                f"{head}_prediction_values_finite": True,
                f"{head}_prediction_path_metric_sign_valid": True,
                f"{head}_ood_bound_provenance": "training_targets_only",
                f"{head}_calibration_ood_rate": 0.0,
                f"{head}_calibration_ood_rate_limit": 0.02,
                f"{head}_holdout_ood_rate": 0.0,
                f"{head}_ood_severity_q99_limit": 0.10,
                f"{head}_holdout_ood_q99_severity": 0.0,
                f"{head}_holdout_ood_max_severity": 0.0,
                f"{head}_holdout_prediction_nonfinite_count": 0,
            }
        )
    metrics.update(overrides)
    return metrics


def _profit_gate(gates: tuple[Any, ...]) -> Any:
    return next(gate for gate in gates if gate.gate_id == "profit_factor_min_090")


def _symbol_concentration_gate(gates: tuple[Any, ...]) -> Any:
    return next(gate for gate in gates if gate.gate_id == "symbol_concentration_max_050")


def _sector_concentration_gate(gates: tuple[Any, ...]) -> Any:
    return next(gate for gate in gates if gate.gate_id == "sector_concentration_max_080")


def _exceptional_period_gate(gates: tuple[Any, ...]) -> Any:
    return next(
        gate for gate in gates if gate.gate_id == "exceptional_period_concentration_max_060"
    )


def _temporal_evidence_gate(gates: tuple[Any, ...]) -> Any:
    return next(
        gate for gate in gates if gate.gate_id == "temporal_fold_stability_evidence_available"
    )


def _temporal_threshold_gate(gates: tuple[Any, ...]) -> Any:
    return next(gate for gate in gates if gate.gate_id == "temporal_fold_stability_min_050")


def test_profit_factor_gains_without_losses_is_positive_infinity_and_passes() -> None:
    returns = pd.Series([0.01, 0.02])
    count, gains, losses, zeros = model_module._profit_factor_components(returns)
    result = profit_factor_result(
        selected_count=count,
        positive_return_sum=gains,
        negative_return_abs_sum=losses,
        zero_return_count=zeros,
        naive_control=False,
    )
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=count,
            holdout_profit_factor=result.actual_value,
            holdout_profit_factor_evidence_status=result.evidence_status,
            holdout_positive_return_sum=gains,
            holdout_negative_return_abs_sum=losses,
            holdout_zero_return_count=zeros,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    gate = _profit_gate(gates)

    assert result.actual_value == math.inf
    assert compare_gate_values(result.actual_value, ">=", 0.9) is True
    assert gate.status == "PASS"
    assert gate.actual_value == math.inf
    assert "gains and no losses" in gate.reason


def test_profit_factor_with_gains_and_losses_compares_normally() -> None:
    returns = pd.Series([0.03, -0.01, 0.02, -0.01])
    count, gains, losses, zeros = model_module._profit_factor_components(returns)
    result = profit_factor_result(
        selected_count=count,
        positive_return_sum=gains,
        negative_return_abs_sum=losses,
        zero_return_count=zeros,
        naive_control=False,
    )

    assert result.actual_value == pytest.approx(2.5)
    assert result.status == "PASS"


def test_profit_factor_equal_to_minimum_passes_and_below_minimum_fails() -> None:
    equal = profit_factor_result(
        selected_count=2,
        positive_return_sum=0.09,
        negative_return_abs_sum=0.10,
        zero_return_count=0,
        naive_control=False,
    )
    below = profit_factor_result(
        selected_count=2,
        positive_return_sum=0.08,
        negative_return_abs_sum=0.10,
        zero_return_count=0,
        naive_control=False,
    )

    assert equal.actual_value == pytest.approx(0.9)
    assert equal.status == "PASS"
    assert below.status == "FAIL"


def test_profit_factor_zero_selected_learned_model_is_unavailable_and_fails() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=0,
            holdout_profit_factor=GATE_VALUE_NOT_AVAILABLE,
            holdout_profit_factor_evidence_status="UNAVAILABLE",
            holdout_positive_return_sum=0.0,
            holdout_negative_return_abs_sum=0.0,
            holdout_zero_return_count=0,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    gate = _profit_gate(gates)

    assert gate.actual_value == GATE_VALUE_NOT_AVAILABLE
    assert gate.status == "FAIL"
    assert "no selected observations" in gate.reason


def test_profit_factor_zero_selected_naive_control_is_not_applicable() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=0,
            holdout_profit_factor=GATE_VALUE_NOT_AVAILABLE,
            holdout_profit_factor_evidence_status="NOT_APPLICABLE",
            holdout_positive_return_sum=0.0,
            holdout_negative_return_abs_sum=0.0,
            holdout_zero_return_count=0,
        ),
        calibration_metrics={"brier_skill_score": 0.0, "holdout_brier": 0.25},
        family="naive_base_rate",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    gate = _profit_gate(gates)

    assert gate.actual_value == GATE_VALUE_NOT_AVAILABLE
    assert gate.status == "NOT_APPLICABLE"
    assert gate.mandatory is False
    assert "naive control selected no rows" in gate.reason


def test_profit_factor_all_zero_selected_returns_is_unavailable() -> None:
    returns = pd.Series([0.0, 0.0, 0.0])
    count, gains, losses, zeros = model_module._profit_factor_components(returns)
    result = profit_factor_result(
        selected_count=count,
        positive_return_sum=gains,
        negative_return_abs_sum=losses,
        zero_return_count=zeros,
        naive_control=False,
    )

    assert result.actual_value == GATE_VALUE_NOT_AVAILABLE
    assert result.status == "FAIL"
    assert "all selected returns were zero" in result.reason


def test_nan_and_negative_infinity_do_not_pass_minimum_profit_factor_gate() -> None:
    assert compare_gate_values(float("nan"), ">=", 0.9) is False
    assert compare_gate_values(float("-inf"), ">=", 0.9) is False
    assert compare_gate_values(float("inf"), ">=", 0.9) is True

    nan_result = profit_factor_result(
        selected_count=1,
        positive_return_sum=float("nan"),
        negative_return_abs_sum=0.0,
        zero_return_count=0,
        naive_control=False,
    )
    assert nan_result.status == "FAIL"
    assert nan_result.actual_value == GATE_VALUE_NOT_AVAILABLE


def test_concentration_reason_text_matches_status() -> None:
    failed = _build_gate_results(
        metrics=_base_gate_metrics(
            symbol_concentration_top=0.8333,
            sector_concentration_top=0.9,
            exceptional_period_concentration_top=0.7,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    passed = _build_gate_results(
        metrics=_base_gate_metrics(
            symbol_concentration_top=0.42,
            sector_concentration_top=0.70,
            exceptional_period_concentration_top=0.55,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _symbol_concentration_gate(failed).status == "FAIL"
    assert "exceeds the maximum 50.00%" in _symbol_concentration_gate(failed).reason
    assert _symbol_concentration_gate(passed).status == "PASS"
    assert "is within the maximum 50.00%" in _symbol_concentration_gate(passed).reason
    assert _sector_concentration_gate(failed).status == "FAIL"
    assert "exceeds the maximum 80.00%" in _sector_concentration_gate(failed).reason
    assert _sector_concentration_gate(passed).status == "PASS"
    assert "is within the maximum 80.00%" in _sector_concentration_gate(passed).reason
    assert _exceptional_period_gate(failed).status == "FAIL"
    assert "exceeds the maximum 60.00%" in _exceptional_period_gate(failed).reason
    assert _exceptional_period_gate(passed).status == "PASS"
    assert "is within the maximum 60.00%" in _exceptional_period_gate(passed).reason


def test_temporal_fold_valid_fraction_above_minimum_passes_both_gates() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(temporal_fold_positive_fraction=0.75),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _temporal_evidence_gate(gates).status == "PASS"
    assert "available from 3 evaluable chronological folds" in _temporal_evidence_gate(gates).reason
    assert _temporal_threshold_gate(gates).status == "PASS"
    assert "75.00% meets the minimum 50.00%" in _temporal_threshold_gate(gates).reason


def test_temporal_fold_valid_fraction_equal_to_minimum_passes_threshold() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(temporal_fold_positive_fraction=0.50),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _temporal_evidence_gate(gates).status == "PASS"
    assert _temporal_threshold_gate(gates).status == "PASS"


def test_temporal_fold_valid_fraction_below_minimum_fails_threshold_only() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(temporal_fold_positive_fraction=0.49),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _temporal_evidence_gate(gates).status == "PASS"
    assert _temporal_threshold_gate(gates).status == "FAIL"
    assert "49.00% is below the minimum 50.00%" in _temporal_threshold_gate(gates).reason


def test_temporal_fold_zero_selected_rows_fails_evidence_and_blocks_promotion() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=0,
            temporal_fold_folds_evaluated=0,
            temporal_fold_folds_with_selected_observations=0,
            temporal_fold_selected_observations_per_fold_json="[0, 0, 0]",
            temporal_fold_records_json="[]",
            temporal_fold_positive_fraction=GATE_VALUE_NOT_AVAILABLE,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    eligibility = promotion_eligibility(gates)

    assert _temporal_evidence_gate(gates).status == "FAIL"
    assert _temporal_threshold_gate(gates).status == "NOT_APPLICABLE"
    assert _temporal_threshold_gate(gates).actual_value == GATE_VALUE_NOT_AVAILABLE
    assert eligibility.eligible is False
    assert any(
        "temporal_fold_stability_evidence_available" in item for item in eligibility.blocked_reasons
    )


def test_temporal_fold_insufficient_selected_rows_fails_evidence() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=2,
            temporal_fold_folds_evaluated=2,
            temporal_fold_folds_with_selected_observations=2,
            temporal_fold_selected_observations_per_fold_json="[1, 1, 0]",
            temporal_fold_records_json="[]",
            temporal_fold_positive_fraction=GATE_VALUE_NOT_AVAILABLE,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _temporal_evidence_gate(gates).status == "FAIL"
    assert "only 2 folds contained selected observations" in _temporal_evidence_gate(gates).reason
    assert _temporal_threshold_gate(gates).status == "NOT_APPLICABLE"
    assert promotion_eligibility(gates).eligible is False


@pytest.mark.parametrize(
    ("value", "reason_fragment"),
    [
        (None, "fold metric is missing"),
        (float("nan"), "fold metric is nonfinite"),
        (float("inf"), "fold metric is nonfinite"),
        (float("-inf"), "fold metric is nonfinite"),
    ],
)
def test_temporal_fold_missing_nan_or_infinite_metric_fails_evidence(
    value: object,
    reason_fragment: str,
) -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(temporal_fold_positive_fraction=value),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _temporal_evidence_gate(gates).status == "FAIL"
    assert reason_fragment in _temporal_evidence_gate(gates).reason
    assert _temporal_threshold_gate(gates).status == "NOT_APPLICABLE"


def test_temporal_fold_naive_control_is_not_applicable_and_not_promotable() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=0,
            temporal_fold_folds_evaluated=0,
            temporal_fold_folds_with_selected_observations=0,
            temporal_fold_selected_observations_per_fold_json="[0, 0, 0]",
            temporal_fold_positive_fraction=GATE_VALUE_NOT_AVAILABLE,
        ),
        calibration_metrics={"brier_skill_score": 0.0, "holdout_brier": 0.25},
        family="naive_base_rate",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    eligibility = promotion_eligibility(gates)

    assert _temporal_evidence_gate(gates).status == "NOT_APPLICABLE"
    assert _temporal_threshold_gate(gates).status == "NOT_APPLICABLE"
    assert _temporal_evidence_gate(gates).mandatory is False
    assert _temporal_threshold_gate(gates).mandatory is False
    assert eligibility.eligible is False
    assert any("not_naive_control" in item for item in eligibility.blocked_reasons)


def test_quantitative_gate_unavailable_or_not_applicable_actual_cannot_pass() -> None:
    unavailable = make_gate(
        gate_id="temporal_fold_stability_min_050",
        gate_name="Temporal Fold Positive Fraction Minimum",
        category="temporal stability",
        scope="selected_candidates",
        metric_name="temporal_fold_positive_fraction",
        threshold=0.50,
        comparator=">=",
        actual_value=GATE_VALUE_NOT_AVAILABLE,
        status="PASS",
        mandatory=True,
        evidence_source="legacy",
        reason="Temporal fold stability passes or is not applicable due insufficient selected rows.",
        configuration_hash_value="legacy",
    )
    not_applicable = make_gate(
        gate_id="temporal_fold_stability_min_050",
        gate_name="Temporal Fold Positive Fraction Minimum",
        category="temporal stability",
        scope="selected_candidates",
        metric_name="temporal_fold_positive_fraction",
        threshold=0.50,
        comparator=">=",
        actual_value=GATE_VALUE_NOT_APPLICABLE,
        status="PASS",
        mandatory=True,
        evidence_source="legacy",
        reason="Temporal fold stability passes.",
        configuration_hash_value="legacy",
    )

    assert "unavailable or inapplicable" in gate_result_integrity_warning(unavailable)
    assert "unavailable or inapplicable" in gate_result_integrity_warning(not_applicable)


def test_status_aware_temporal_fold_reasons_match_status() -> None:
    passed = _build_gate_results(
        metrics=_base_gate_metrics(temporal_fold_positive_fraction=0.75),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    failed = _build_gate_results(
        metrics=_base_gate_metrics(temporal_fold_positive_fraction=0.25),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    not_applicable = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=0,
            temporal_fold_folds_evaluated=0,
            temporal_fold_folds_with_selected_observations=0,
            temporal_fold_selected_observations_per_fold_json="[0, 0, 0]",
            temporal_fold_positive_fraction=GATE_VALUE_NOT_AVAILABLE,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _temporal_threshold_gate(passed).status == "PASS"
    assert "meets the minimum" in _temporal_threshold_gate(passed).reason
    assert _temporal_threshold_gate(failed).status == "FAIL"
    assert "below the minimum" in _temporal_threshold_gate(failed).reason
    assert _temporal_threshold_gate(not_applicable).status == "NOT_APPLICABLE"
    assert "cannot be evaluated" in _temporal_threshold_gate(not_applicable).reason


def test_dashboard_display_distinguishes_temporal_fold_evidence_states() -> None:
    frame = pd.DataFrame(
        {
            "temporal_fold_positive_fraction": [
                0.75,
                GATE_VALUE_NOT_AVAILABLE,
                GATE_VALUE_NOT_APPLICABLE,
            ]
        }
    )

    display = display_frame(frame)

    assert display["Temporal Fold Positive Fraction"].tolist() == [
        "75.00%",
        "Not available",
        "Not applicable",
    ]


def test_model_audit_exports_preserve_temporal_fold_evidence_states(tmp_path: Path) -> None:
    gates = (
        make_gate(
            gate_id="temporal_fold_stability_evidence_available",
            gate_name="Temporal Fold Stability Evidence Available",
            category="temporal stability",
            scope="selected_candidates",
            metric_name="temporal_fold_evidence_status",
            threshold="AVAILABLE",
            comparator="is available",
            actual_value="AVAILABLE",
            status="PASS",
            mandatory=True,
            evidence_source="test",
            reason="Temporal-fold stability evidence is available from 3 evaluable chronological folds.",
            configuration_hash_value="test",
        ),
        make_gate(
            gate_id="temporal_fold_stability_evidence_unavailable",
            gate_name="Temporal Fold Stability Evidence Available",
            category="temporal stability",
            scope="selected_candidates",
            metric_name="temporal_fold_evidence_status",
            threshold="AVAILABLE",
            comparator="is available",
            actual_value="UNAVAILABLE",
            status="FAIL",
            mandatory=True,
            evidence_source="test",
            reason="Temporal-fold stability evidence is unavailable because only 0 folds contained selected observations.",
            configuration_hash_value="test",
        ),
        make_gate(
            gate_id="temporal_fold_stability_evidence_not_applicable",
            gate_name="Temporal Fold Stability Evidence Available",
            category="temporal stability",
            scope="selected_candidates",
            metric_name="temporal_fold_evidence_status",
            threshold="AVAILABLE",
            comparator="is available",
            actual_value=GATE_VALUE_NOT_APPLICABLE,
            status="NOT_APPLICABLE",
            mandatory=False,
            evidence_source="test",
            reason="Temporal-fold trading stability is not applicable to the naive zero-selection control.",
            configuration_hash_value="test",
        ),
    )
    db = ProjectPaths(tmp_path).engine_db
    register_model(db, _audit_model("model-temporal-export", gates))

    audit = build_model_audit(tmp_path, model_id="model-temporal-export")
    export_paths = export_model_audit(audit, tmp_path / "reports" / "model_audit")
    csv_path = next(path for path in export_paths if path.name == "full_gate_audit.csv")
    json_path = next(path for path in export_paths if path.name == "full_gate_audit.json")
    csv_text = csv_path.read_text(encoding="utf-8")
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    actual_values = {row["actual_value"] for row in json_rows}

    assert {"AVAILABLE", "UNAVAILABLE", GATE_VALUE_NOT_APPLICABLE} <= actual_values
    assert "AVAILABLE" in csv_text
    assert "UNAVAILABLE" in csv_text
    assert GATE_VALUE_NOT_APPLICABLE in csv_text


def test_promotion_eligibility_uses_temporal_fold_evidence_gate() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            selected_holdout_samples=0,
            temporal_fold_folds_evaluated=0,
            temporal_fold_folds_with_selected_observations=0,
            temporal_fold_selected_observations_per_fold_json="[0, 0, 0]",
            temporal_fold_positive_fraction=GATE_VALUE_NOT_AVAILABLE,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    eligibility = promotion_eligibility(gates)

    assert _temporal_evidence_gate(gates).status == "FAIL"
    assert eligibility.eligible is False
    assert any(
        reason.startswith("temporal_fold_stability_evidence_available")
        for reason in eligibility.blocked_reasons
    )


def test_legacy_temporal_fold_inconsistent_row_remains_unchanged_and_blocks() -> None:
    legacy_gate = make_gate(
        gate_id="temporal_fold_stability_min_050",
        gate_name="Temporal Fold Positive Fraction Minimum",
        category="temporal stability",
        scope="selected_candidates",
        metric_name="temporal_fold_positive_fraction",
        threshold=0.50,
        comparator=">=",
        actual_value=GATE_VALUE_NOT_AVAILABLE,
        status="PASS",
        mandatory=True,
        evidence_source="legacy_model_evaluation",
        reason="Temporal fold stability passes or is not applicable due insufficient selected rows.",
        configuration_hash_value="legacy",
    )

    eligibility = promotion_eligibility((legacy_gate,))

    assert legacy_gate.status == "PASS"
    assert legacy_gate.actual_value == GATE_VALUE_NOT_AVAILABLE
    assert gate_result_integrity_warning(legacy_gate)
    assert eligibility.eligible is False
    assert gate_results_integrity_warnings((legacy_gate,))


def test_dashboard_display_distinguishes_infinity_from_unavailable() -> None:
    frame = pd.DataFrame({"profit_factor": [math.inf, GATE_VALUE_NOT_AVAILABLE]})
    display = display_frame(frame)
    assert display["Profit Factor"].tolist() == ["∞", "Not available"]
    assert decimal(math.inf) == "∞"
    assert decimal(GATE_VALUE_NOT_AVAILABLE) == "Not available"

    model = _audit_model(
        "model-inf",
        (
            make_gate(
                gate_id="minimum_training_samples",
                gate_name="Minimum Training Samples",
                category="data sufficiency",
                scope="prediction",
                metric_name="training_samples",
                threshold=200,
                comparator=">=",
                actual_value=300,
                status="PASS",
                mandatory=True,
                evidence_source="test",
                reason="Training sample count meets configured minimum.",
                configuration_hash_value="test",
            ),
        ),
    )
    model = RegisteredModel(
        **{**model.__dict__, "metrics": {**model.metrics, "holdout_profit_factor": math.inf}}
    )
    assert compact_registry_rows([model]).iloc[0]["PF"] == "∞"


def test_csv_and_json_exports_distinguish_infinity_from_unavailable(tmp_path: Path) -> None:
    inf_gate = make_gate(
        gate_id="profit_factor_min_090",
        gate_name="Profit Factor Minimum",
        category="selected-candidate quality",
        scope="selected_candidates",
        metric_name="holdout_profit_factor",
        threshold=0.9,
        comparator=">=",
        actual_value=math.inf,
        status="PASS",
        mandatory=True,
        evidence_source="test",
        reason="Selected returns contain gains and no losses.",
        configuration_hash_value="test",
    )
    unavailable_gate = make_gate(
        gate_id="profit_factor_min_090_unavailable",
        gate_name="Profit Factor Minimum",
        category="selected-candidate quality",
        scope="selected_candidates",
        metric_name="holdout_profit_factor",
        threshold=0.9,
        comparator=">=",
        actual_value=GATE_VALUE_NOT_AVAILABLE,
        status="FAIL",
        mandatory=True,
        evidence_source="test",
        reason="Profit factor is unavailable because no selected observations exist.",
        configuration_hash_value="test",
    )
    db = ProjectPaths(tmp_path).engine_db
    register_model(db, _audit_model("model-export", (inf_gate, unavailable_gate)))

    audit = build_model_audit(tmp_path, model_id="model-export")
    export_paths = export_model_audit(audit, tmp_path / "reports" / "model_audit")
    csv_path = next(path for path in export_paths if path.name == "full_gate_audit.csv")
    json_path = next(path for path in export_paths if path.name == "full_gate_audit.json")
    csv_text = csv_path.read_text(encoding="utf-8")
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))

    assert "Infinity" in csv_text
    assert GATE_VALUE_NOT_AVAILABLE in csv_text
    assert {row["actual_value"] for row in json_rows} == {"Infinity", GATE_VALUE_NOT_AVAILABLE}


def test_promotion_eligibility_uses_corrected_profit_factor_gate_result() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(
            holdout_profit_factor=math.inf,
            holdout_positive_return_sum=0.03,
            holdout_negative_return_abs_sum=0.0,
            holdout_zero_return_count=0,
        ),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )
    eligibility = promotion_eligibility(gates)

    assert _profit_gate(gates).status == "PASS"
    assert eligibility.eligible is True


def test_existing_legacy_artifact_gate_row_remains_unchanged_but_warns(tmp_path: Path) -> None:
    legacy_gate = make_gate(
        gate_id="profit_factor_min_090",
        gate_name="Profit Factor Minimum",
        category="selected-candidate quality",
        scope="selected_candidates",
        metric_name="holdout_profit_factor",
        threshold=0.9,
        comparator=">=",
        actual_value=math.inf,
        status="FAIL",
        mandatory=True,
        evidence_source="legacy_model_evaluation",
        reason="Selected-row profit factor fails configured minimum.",
        configuration_hash_value="legacy",
    )
    db = ProjectPaths(tmp_path).engine_db
    legacy_model = _audit_model("model-legacy", ())
    legacy_payload = {
        "gate_id": legacy_gate.gate_id,
        "gate_name": legacy_gate.gate_name,
        "category": legacy_gate.category,
        "scope": legacy_gate.scope,
        "metric_name": legacy_gate.metric_name,
        "threshold": legacy_gate.threshold,
        "comparator": legacy_gate.comparator,
        "actual_value": legacy_gate.actual_value,
        "status": legacy_gate.status,
        "mandatory": legacy_gate.mandatory,
        "evidence_source": legacy_gate.evidence_source,
        "reason": legacy_gate.reason,
        "evaluated_at_utc": legacy_gate.evaluated_at_utc,
        "configuration_hash": legacy_gate.configuration_hash,
    }
    with engine_connection(db) as connection:
        connection.execute(
            """
            INSERT INTO models (
                model_id, task, horizon, direction, family, state, training_start, training_end,
                validation_start, validation_end, holdout_start, holdout_end, universe_snapshot_id,
                feature_manifest_hash, raw_manifest_hashes_json, hyperparameters_json, metrics_json,
                calibration_metrics_json, quality_gates_json, gate_results_json, artifact_path,
                code_commit_hash, created_at_utc, promoted_at_utc, retirement_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                legacy_model.model_id,
                legacy_model.task,
                legacy_model.horizon,
                legacy_model.direction,
                legacy_model.family,
                legacy_model.state,
                legacy_model.training_start,
                legacy_model.training_end,
                legacy_model.validation_start,
                legacy_model.validation_end,
                legacy_model.holdout_start,
                legacy_model.holdout_end,
                legacy_model.universe_snapshot_id,
                legacy_model.feature_manifest_hash,
                dumps(legacy_model.raw_manifest_hashes),
                dumps(legacy_model.hyperparameters),
                dumps(legacy_model.metrics),
                dumps(legacy_model.calibration_metrics),
                dumps(legacy_model.quality_gates),
                dumps([legacy_payload]),
                legacy_model.artifact_path,
                legacy_model.code_commit_hash,
                legacy_model.created_at_utc,
                legacy_model.promoted_at_utc,
                legacy_model.retirement_reason,
            ),
        )

    loaded = list_models(db)[0]
    audit = build_model_audit(tmp_path, model_id="model-legacy")

    assert loaded.gate_results[0].status == "FAIL"
    assert loaded.gate_results[0].actual_value == math.inf
    assert gate_result_integrity_warning(loaded.gate_results[0])
    assert "contradicts" in audit.gates.iloc[0]["evidence_integrity_warning"]


def test_gate_evidence_tests_make_no_fmp_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_fmp(*_: object, **__: object) -> None:
        raise AssertionError("gate evidence tests attempted an FMP call")

    monkeypatch.setattr("swing_rsi.data.providers.fmp.download_fmp_daily", fail_fmp)
    gates = _build_gate_results(
        metrics=_base_gate_metrics(),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    assert _profit_gate(gates).status == "PASS"


def test_worse_than_naive_brier_fails_mandatory_predictive_gate() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(),
        calibration_metrics={"brier_skill_score": -0.01, "holdout_brier": 0.26},
        family="extra_trees",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    gate = next(result for result in gates if result.gate_id == "brier_skill_vs_naive_positive")

    assert gate.status == "FAIL"
    assert gate.mandatory is True


def test_naive_zero_selection_trading_gate_is_not_applicable() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(selected_holdout_samples=0),
        calibration_metrics={"brier_skill_score": 0.0, "holdout_brier": 0.25},
        family="naive_base_rate",
        config=DiscoveryConfig(),
        config_hash="test",
    )

    gate = next(
        result for result in gates if result.gate_id == "selected_candidate_quality_available"
    )
    naive_gate = next(result for result in gates if result.gate_id == "not_naive_control")

    assert gate.status == "NOT_APPLICABLE"
    assert gate.mandatory is False
    assert naive_gate.status == "FAIL"


def test_not_configured_selection_rate_blocks_promotion() -> None:
    gates = _build_gate_results(
        metrics=_base_gate_metrics(),
        calibration_metrics={"brier_skill_score": 0.05, "holdout_brier": 0.20},
        family="extra_trees",
        config=DiscoveryConfig(selection_rate_max=None),
        config_hash="test",
    )

    eligibility = promotion_eligibility(gates)

    assert eligibility.eligible is False
    assert eligibility.not_configured == 1


def test_configured_selection_policy_persists_all_candidate_controls() -> None:
    policy = selection_policy_from_config(DiscoveryConfig())

    assert policy == SelectionPolicy(
        probability_threshold=0.55,
        expected_return_threshold=0.001,
        target_before_stop_threshold=0.50,
        top_n_limit=5_000,
        per_date_limit=5,
        liquidity_threshold=5_000_000.0,
        selected_rate_ceiling=0.20,
    )
    assert policy.tie_breaking_rule == CANONICAL_CANDIDATE_TIE_BREAKING_RULE


def test_selection_policy_evaluator_threshold_edges_and_bad_values() -> None:
    policy = SelectionPolicy(
        probability_threshold=0.55,
        expected_return_threshold=0.001,
        target_before_stop_threshold=0.50,
        liquidity_threshold=5_000_000.0,
    )

    passing = evaluate_candidate_policy(
        {
            "calibrated_probability": 0.55,
            "expected_return": 0.001,
            "target_before_stop_probability": 0.50,
            "liquidity_score": 5_000_000.0,
        },
        policy,
        policy_hash="policy-hash",
    )
    missing = evaluate_candidate_policy(
        {
            "calibrated_probability": 0.55,
            "target_before_stop_probability": 0.50,
            "liquidity_score": 5_000_000.0,
        },
        policy,
    )
    nonfinite = evaluate_candidate_policy(
        {
            "calibrated_probability": 0.55,
            "expected_return": float("nan"),
            "target_before_stop_probability": 0.50,
            "liquidity_score": 5_000_000.0,
        },
        policy,
    )

    assert passing.passed is True
    assert passing.policy_hash == "policy-hash"
    assert missing.passed is False
    assert "required_policy_metric_missing" in missing.rejection_reasons
    assert nonfinite.passed is False
    assert "required_policy_metric_nonfinite" in nonfinite.rejection_reasons


def test_scanner_and_holdout_selection_share_canonical_policy_evaluator() -> None:
    assert model_module.evaluate_candidate_policy is selection_module.evaluate_candidate_policy
    assert scanner_module.evaluate_candidate_policy is selection_module.evaluate_candidate_policy


def test_selection_policy_enforces_thresholds_and_per_date_limit() -> None:
    holdout = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"] * 5 + ["2024-01-03"]),
            "symbol": ["A", "B", "C", "D", "E", "F"],
            "dollar_volume": [
                10_000_000.0,
                9_000_000.0,
                8_000_000.0,
                7_000_000.0,
                1.0,
                9_000_000.0,
            ],
        }
    )
    probability = np.array([0.80, 0.75, 0.70, 0.65, 0.95, 0.80])
    expected_return = pd.Series([0.02, 0.01, -0.01, 0.03, 0.04, 0.02])
    target_probability = np.array([0.70, 0.65, 0.80, 0.40, 0.90, 0.70])
    policy = SelectionPolicy(
        probability_threshold=0.60,
        expected_return_threshold=0.001,
        target_before_stop_threshold=0.50,
        top_n_limit=None,
        per_date_limit=2,
        liquidity_threshold=5_000_000.0,
        selected_rate_ceiling=0.20,
    )

    selected = _apply_selection_policy(
        holdout,
        probability=probability,
        expected_return=expected_return,
        target_before_stop_probability=target_probability,
        policy=policy,
    )

    assert holdout.loc[selected, "symbol"].tolist() == ["A", "B", "F"]


def test_equal_utility_holdout_caps_use_symbol_before_probability_or_return() -> None:
    holdout = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02"] * 3),
            "symbol": ["C", "A", "B"],
            "dollar_volume": [10_000_000.0] * 3,
        }
    )
    probability = np.array([0.375, 0.75, 0.50])
    expected_return = pd.Series([0.50, 0.25, 0.375])
    target_probability = np.array([0.80, 0.80, 0.80])
    policy = SelectionPolicy(
        probability_threshold=0.30,
        expected_return_threshold=0.001,
        target_before_stop_threshold=0.50,
        top_n_limit=None,
        per_date_limit=2,
        liquidity_threshold=5_000_000.0,
    )

    first = _apply_selection_policy(
        holdout,
        probability=probability,
        expected_return=expected_return,
        target_before_stop_probability=target_probability,
        policy=policy,
    )
    shuffled = holdout.sample(frac=1.0, random_state=17)
    shuffled_probability = (
        pd.Series(probability, index=holdout.index).loc[shuffled.index].to_numpy()
    )
    shuffled_expected = expected_return.loc[shuffled.index]
    shuffled_target = (
        pd.Series(target_probability, index=holdout.index).loc[shuffled.index].to_numpy()
    )
    second = _apply_selection_policy(
        shuffled,
        probability=shuffled_probability,
        expected_return=shuffled_expected,
        target_before_stop_probability=shuffled_target,
        policy=policy,
    )

    assert sorted(holdout.loc[first, "symbol"].tolist()) == ["A", "B"]
    assert sorted(shuffled.loc[second, "symbol"].tolist()) == ["A", "B"]
    assert "C" not in set(holdout.loc[first, "symbol"])


def _audit_model(model_id: str, gates: tuple[Any, ...]) -> RegisteredModel:
    return RegisteredModel(
        model_id=model_id,
        task="swing_direction_probability",
        horizon=10,
        direction="bull",
        family="extra_trees",
        state="CANDIDATE",
        training_start="2016-06-20",
        training_end="2020-01-01",
        validation_start="2020-01-02",
        validation_end="2022-01-01",
        holdout_start="2022-01-03",
        holdout_end="2026-06-18",
        universe_snapshot_id="u",
        feature_manifest_hash="f",
        raw_manifest_hashes=(),
        hyperparameters={"probability_threshold": 0.55, "top_n_limit": None},
        metrics={
            "research_start": "2016-06-20",
            "research_end": "2026-06-18",
            "holdout_samples": 100,
            "selected_holdout_samples": 10,
            "selected_observation_rate": 0.1,
            "holdout_mean_net_return": 0.01,
            "holdout_mean_return_lcb_90": 0.005,
            "holdout_profit_factor": 1.2,
            "portfolio_max_drawdown": -0.1,
            "portfolio_daily_equity_json": '[{"Date":"2024-01-03","equity":1.0}]',
            "selected_candidate_ledger_json": '[{"ticker":"AAPL","as_of_date":"2024-01-02"}]',
        },
        calibration_metrics={
            "holdout_brier": 0.2,
            "naive_brier": 0.21,
            "brier_skill_score": 1.0 - (0.2 / 0.21),
        },
        quality_gates={gate.gate_id: gate.status == "PASS" for gate in gates},
        artifact_path="artifact.joblib",
        code_commit_hash="test",
        created_at_utc=datetime.now(UTC).isoformat(),
        gate_results=gates,
    )


def test_gate_results_persist_export_and_block_failed_promotion(tmp_path: Path) -> None:
    gate = make_gate(
        gate_id="predictive_skill_failed",
        gate_name="Predictive Skill Failed",
        category="predictive skill",
        scope="prediction",
        metric_name="brier_skill_score",
        threshold=0.0,
        comparator=">",
        actual_value=-0.01,
        status="FAIL",
        mandatory=True,
        evidence_source="test",
        reason="Worse than naive control.",
        configuration_hash_value="test",
    )
    db = ProjectPaths(tmp_path).engine_db
    register_model(db, _audit_model("model-a", (gate,)))

    loaded = list_models(db)[0]
    audit = build_model_audit(tmp_path, model_id="model-a")
    paths = export_model_audit(audit, tmp_path / "reports" / "model_audit")

    assert loaded.gate_results[0].gate_id == "predictive_skill_failed"
    assert audit.gates["gate_id"].tolist() == ["predictive_skill_failed"]
    assert any(path.name == "full_gate_audit.json" for path in paths)
    with pytest.raises(ValueError, match="mandatory gate results block promotion"):
        promote_model(db, "model-a")


def test_missing_canonical_gate_results_block_promotion() -> None:
    eligibility = promotion_eligibility(())

    assert eligibility.eligible is False
    assert "missing" in eligibility.blocked_reasons[0]


def test_prediction_ood_flags_use_training_only_bounds() -> None:
    bundle = ModelBundle(
        model_id="model-a",
        direction="bear",
        horizon=10,
        family="test",
        feature_columns=("feature",),
        feature_family_by_column={"feature": "price"},
        classifier=ConstantClassifier(),
        calibrator=IdentityCalibrator(),
        target_before_stop_model=ConstantClassifier(),
        target_before_stop_calibrator=IdentityCalibrator(),
        return_model=ConstantRegressor(0.29),
        mfe_model=ConstantRegressor(0.85),
        mae_model=ConstantRegressor(-0.36),
        training_medians={"feature": 1.0},
        training_means={"feature": 1.0},
        training_stds={"feature": 1.0},
        training_matrix=pd.DataFrame({"feature": [1.0]}),
        training_labels=pd.DataFrame(),
        metrics={
            "return_prediction_bound_low_train_q01": -0.05,
            "return_prediction_bound_high_train_q99": 0.10,
            "mfe_prediction_bound_low_train_q01": 0.00,
            "mfe_prediction_bound_high_train_q99": 0.30,
            "mae_prediction_bound_low_train_q01": -0.20,
            "mae_prediction_bound_high_train_q99": 0.00,
            "return_prediction_transform_method": "none",
            "mfe_prediction_transform_method": "none",
            "mae_prediction_transform_method": "none",
        },
        calibration_metrics={},
    )
    frame = pd.DataFrame(
        {"Date": [pd.Timestamp("2026-06-18")], "symbol": ["SOXL"], "feature": [2.0]}
    )

    prediction = predict_bundle(bundle, frame).iloc[0]

    assert prediction["expected_return"] == pytest.approx(0.29)
    assert prediction["expected_return_raw"] == pytest.approx(0.29)
    assert prediction["expected_return_transformed"] == pytest.approx(0.29)
    assert bool(prediction["expected_return_out_of_distribution"]) is True
    assert bool(prediction["expected_mfe_out_of_distribution"]) is True
    assert bool(prediction["expected_mae_out_of_distribution"]) is True
