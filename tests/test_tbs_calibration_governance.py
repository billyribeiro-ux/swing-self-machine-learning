from __future__ import annotations

import inspect
from typing import cast

import numpy as np
import pandas as pd
import pytest

from swing_rsi.engine.calibration_governance import (
    CALIBRATION_METHODS,
    TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION,
    CalibrationCandidateResult,
    CalibrationMethod,
    IdentityProbabilityCalibrator,
    IsotonicProbabilityCalibrator,
    SigmoidProbabilityCalibrator,
    build_probability_audit_frame,
    select_method_by_one_standard_error,
    select_tbs_calibrator,
)


def _chronological_calibration_arrays(
    *,
    rows: int = 160,
) -> tuple[np.ndarray, np.ndarray, pd.Series]:
    raw = np.tile(np.linspace(0.05, 0.95, 40), rows // 40)
    target = (raw >= 0.55).astype(int)
    dates = pd.Series(pd.date_range("2022-05-13", periods=len(raw), freq="D"))
    return raw, target, dates


def _candidate(
    method: str,
    *,
    mean_brier: float,
    standard_error: float,
    eligible: bool = True,
) -> CalibrationCandidateResult:
    return CalibrationCandidateResult(
        method=cast(CalibrationMethod, method),
        evaluable_fold_count=3 if eligible else 1,
        mean_brier_score=mean_brier,
        brier_standard_error=standard_error,
        mean_log_loss=None,
        mean_expected_calibration_error=None,
        mean_maximum_calibration_error=None,
        mean_calibration_slope=None,
        mean_calibration_intercept=None,
        mean_roc_auc=None,
        mean_pr_auc=None,
        mean_rank_correlation=None,
        mean_unique_calibrated_value_count=None,
        mean_largest_plateau_percentage=None,
        minimum_isotonic_step_support=None,
        calibrated_probability_zero_count=0,
        calibrated_probability_one_count=0,
        eligible=eligible,
        reason="ok" if eligible else "fewer_than_two_evaluable_folds",
    )


def test_tbs_calibration_governance_evaluates_all_methods_chronologically() -> None:
    raw, target, dates = _chronological_calibration_arrays()

    result = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=11,
    )

    assert result.schema_version == TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION
    assert {candidate.method for candidate in result.candidate_results} == set(CALIBRATION_METHODS)
    assert all(candidate.evaluable_fold_count >= 2 for candidate in result.candidate_results)
    assert len(result.fold_definitions) == 3
    for fold in result.fold_definitions:
        assert pd.Timestamp(fold.fit_end) < pd.Timestamp(fold.evaluation_start)
        assert fold.fit_rows > 0
        assert fold.evaluation_rows > 0


def test_tbs_calibration_governance_is_deterministic_and_ignores_holdout() -> None:
    raw, target, dates = _chronological_calibration_arrays()

    first = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=17,
    )
    second = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=17,
    )

    assert set(inspect.signature(select_tbs_calibrator).parameters.keys()) == {
        "raw_probability",
        "target",
        "dates",
        "random_seed",
    }
    assert first.selected_method == second.selected_method
    assert first.calibration_manifest_hash == second.calibration_manifest_hash
    assert first.calibrator_artifact_hash == second.calibrator_artifact_hash


def test_future_calibration_rows_do_not_affect_earlier_fold_metrics() -> None:
    raw, target, dates = _chronological_calibration_arrays()
    mutated_target = target.copy()
    mutated_target[80:] = 1 - mutated_target[80:]

    baseline = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=23,
    )
    mutated = select_tbs_calibrator(
        raw_probability=raw,
        target=mutated_target,
        dates=dates,
        random_seed=23,
    )

    baseline_first_fold = next(
        fold for fold in baseline.fold_results if fold.fold_id == 1 and fold.method == "identity"
    )
    mutated_first_fold = next(
        fold for fold in mutated.fold_results if fold.fold_id == 1 and fold.method == "identity"
    )

    assert baseline_first_fold.fit_rows == mutated_first_fold.fit_rows
    assert baseline_first_fold.evaluation_rows == mutated_first_fold.evaluation_rows
    assert baseline_first_fold.brier_score == pytest.approx(mutated_first_fold.brier_score)


def test_independent_models_get_separate_calibrator_instances() -> None:
    raw, target, dates = _chronological_calibration_arrays()

    bull = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=29,
    )
    bear = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=29,
    )

    assert bull.selected_calibrator is not bear.selected_calibrator
    assert bull.calibration_manifest_hash == bear.calibration_manifest_hash


def test_insufficient_evaluable_folds_select_identity() -> None:
    raw = np.linspace(0.10, 0.90, 80)
    target = np.ones(80, dtype=int)
    dates = pd.Series(pd.date_range("2022-05-13", periods=80, freq="D"))

    result = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=5,
    )

    assert result.selected_method == "identity"
    assert result.selection_reason == "insufficient_calibration_folds_for_learned_calibrator"
    assert all(not candidate.eligible for candidate in result.candidate_results)


def test_one_standard_error_rule_selects_simplest_method_inside_boundary() -> None:
    selected, boundary, reason = select_method_by_one_standard_error(
        (
            _candidate("identity", mean_brier=0.205, standard_error=0.001),
            _candidate("sigmoid", mean_brier=0.198, standard_error=0.001),
            _candidate("isotonic", mean_brier=0.195, standard_error=0.012),
        )
    )

    assert selected == "identity"
    assert boundary == pytest.approx(0.207)
    assert reason == "one_standard_error_simplest_method"


def test_sigmoid_can_win_when_outside_identity_one_standard_error_boundary() -> None:
    selected, boundary, reason = select_method_by_one_standard_error(
        (
            _candidate("identity", mean_brier=0.250, standard_error=0.001),
            _candidate("sigmoid", mean_brier=0.190, standard_error=0.004),
            _candidate("isotonic", mean_brier=0.205, standard_error=0.001),
        )
    )

    assert selected == "sigmoid"
    assert boundary == pytest.approx(0.194)
    assert reason == "lowest_mean_chronological_fold_brier"


def test_isotonic_can_win_only_when_simpler_methods_are_outside_boundary() -> None:
    selected, boundary, reason = select_method_by_one_standard_error(
        (
            _candidate("identity", mean_brier=0.250, standard_error=0.001),
            _candidate("sigmoid", mean_brier=0.240, standard_error=0.001),
            _candidate("isotonic", mean_brier=0.200, standard_error=0.005),
        )
    )

    assert selected == "isotonic"
    assert boundary == pytest.approx(0.205)
    assert reason == "lowest_mean_chronological_fold_brier"


def test_calibrator_probability_contracts() -> None:
    raw, target, _ = _chronological_calibration_arrays()

    identity = IdentityProbabilityCalibrator().fit(raw, target)
    sigmoid = SigmoidProbabilityCalibrator(random_seed=3).fit(raw, target)
    isotonic = IsotonicProbabilityCalibrator().fit(raw, target)

    np.testing.assert_allclose(identity.predict(raw), raw)
    for calibrator in (sigmoid, isotonic):
        probabilities = calibrator.predict(raw)
        assert np.all(np.isfinite(probabilities))
        assert np.all(probabilities >= 0.0)
        assert np.all(probabilities <= 1.0)


def test_invalid_raw_probabilities_fail_hard() -> None:
    raw, target, dates = _chronological_calibration_arrays()
    raw = raw.copy()
    raw[4] = np.nan

    with pytest.raises(ValueError, match="probability contract"):
        select_tbs_calibrator(
            raw_probability=raw,
            target=target,
            dates=dates,
            random_seed=7,
        )


def test_probability_audit_preserves_raw_and_selected_calibrated_probabilities() -> None:
    raw, target, dates = _chronological_calibration_arrays()
    selection = select_tbs_calibrator(
        raw_probability=raw,
        target=target,
        dates=dates,
        random_seed=19,
    )
    calibration = pd.DataFrame(
        {
            "Date": dates,
            "symbol": ["AAPL"] * len(raw),
            "label_bull_target_before_stop_10": target,
        }
    )
    holdout = calibration.iloc[:10].copy()
    calibrated = selection.selected_calibrator.predict(raw)

    audit = build_probability_audit_frame(
        calibration_frame=calibration,
        development_holdout_frame=holdout,
        calibration_raw_probability=raw,
        calibration_calibrated_probability=calibrated,
        development_holdout_raw_probability=raw[:10],
        development_holdout_calibrated_probability=calibrated[:10],
        target_column="label_bull_target_before_stop_10",
        selection=selection,
        model_id="model-a",
        direction="bull",
        horizon=10,
    )

    assert {
        "raw_classifier_probability",
        "selected_calibrated_probability",
        "target_label",
        "calibrator_method",
        "calibration_manifest_hash",
    } <= set(audit.columns)
    assert set(audit["split"]) == {"calibration", "development_holdout"}
    assert audit["calibration_manifest_hash"].nunique() == 1
