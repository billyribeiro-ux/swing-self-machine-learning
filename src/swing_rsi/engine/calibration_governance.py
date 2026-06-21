from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Protocol, cast

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from swing_rsi.engine.gates import configuration_hash

TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION = "tbs_calibration_governance_v1"
CalibrationMethod = Literal["identity", "sigmoid", "isotonic"]
CALIBRATION_METHODS: tuple[CalibrationMethod, ...] = ("identity", "sigmoid", "isotonic")
CALIBRATION_METHOD_COMPLEXITY: tuple[CalibrationMethod, ...] = (
    "identity",
    "sigmoid",
    "isotonic",
)
CALIBRATION_THRESHOLD_GRID: tuple[float, ...] = (
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
)


class ProbabilityCalibrator(Protocol):
    method: CalibrationMethod

    def fit(self, raw_probability: np.ndarray, target: np.ndarray) -> ProbabilityCalibrator: ...

    def predict(self, raw_probability: np.ndarray) -> np.ndarray: ...

    def parameters(self) -> dict[str, object]: ...


@dataclass
class IdentityProbabilityCalibrator:
    method: CalibrationMethod = "identity"

    def fit(self, raw_probability: np.ndarray, target: np.ndarray) -> IdentityProbabilityCalibrator:
        _ = raw_probability, target
        return self

    def predict(self, raw_probability: np.ndarray) -> np.ndarray:
        return np.asarray(np.clip(np.asarray(raw_probability, dtype=float), 0.0, 1.0), dtype=float)

    def parameters(self) -> dict[str, object]:
        return {"method": self.method}


@dataclass
class SigmoidProbabilityCalibrator:
    random_seed: int = 42
    method: CalibrationMethod = "sigmoid"

    def __post_init__(self) -> None:
        self.model = LogisticRegression(
            C=1_000_000.0, solver="lbfgs", random_state=self.random_seed
        )
        self.is_fitted = False

    def fit(self, raw_probability: np.ndarray, target: np.ndarray) -> SigmoidProbabilityCalibrator:
        x = np.asarray(raw_probability, dtype=float).reshape(-1, 1)
        y = np.asarray(target, dtype=int)
        if len(np.unique(y)) < 2:
            raise ValueError("sigmoid calibration requires both target classes")
        self.model.fit(x, y)
        self.is_fitted = True
        return self

    def predict(self, raw_probability: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("sigmoid calibrator is not fitted")
        x = np.asarray(raw_probability, dtype=float).reshape(-1, 1)
        probability = self.model.predict_proba(x)[:, 1]
        return np.asarray(np.clip(np.asarray(probability, dtype=float), 0.0, 1.0), dtype=float)

    def parameters(self) -> dict[str, object]:
        coef = getattr(self.model, "coef_", np.array([[math.nan]]))
        intercept = getattr(self.model, "intercept_", np.array([math.nan]))
        return {
            "method": self.method,
            "coefficient": float(coef[0][0]),
            "intercept": float(intercept[0]),
        }


@dataclass
class IsotonicProbabilityCalibrator:
    method: CalibrationMethod = "isotonic"
    out_of_bounds: str = "clip"

    def __post_init__(self) -> None:
        self.model = IsotonicRegression(out_of_bounds=self.out_of_bounds)
        self.is_fitted = False

    def fit(self, raw_probability: np.ndarray, target: np.ndarray) -> IsotonicProbabilityCalibrator:
        x = np.asarray(raw_probability, dtype=float)
        y = np.asarray(target, dtype=int)
        if len(np.unique(y)) < 2:
            raise ValueError("isotonic calibration requires both target classes")
        self.model.fit(x, y)
        self.is_fitted = True
        return self

    def predict(self, raw_probability: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("isotonic calibrator is not fitted")
        probability = self.model.predict(np.asarray(raw_probability, dtype=float))
        return np.asarray(np.clip(np.asarray(probability, dtype=float), 0.0, 1.0), dtype=float)

    def parameters(self) -> dict[str, object]:
        return {
            "method": self.method,
            "out_of_bounds": self.out_of_bounds,
            "x_thresholds": [
                float(value) for value in getattr(self.model, "X_thresholds_", np.array([]))
            ],
            "y_thresholds": [
                float(value) for value in getattr(self.model, "y_thresholds_", np.array([]))
            ],
        }


@dataclass(frozen=True)
class CalibrationFoldDefinition:
    fold_id: int
    fit_start: str
    fit_end: str
    evaluation_start: str
    evaluation_end: str
    fit_rows: int
    evaluation_rows: int
    evaluable: bool
    reason: str


@dataclass(frozen=True)
class CalibrationFoldResult:
    method: CalibrationMethod
    fold_id: int
    status: str
    reason: str
    fit_rows: int
    evaluation_rows: int
    brier_score: float | None
    log_loss: float | None
    expected_calibration_error: float | None
    maximum_calibration_error: float | None
    calibration_slope: float | None
    calibration_intercept: float | None
    roc_auc: float | None
    pr_auc: float | None
    rank_correlation: float | None
    unique_calibrated_value_count: int | None
    largest_plateau_percentage: float | None
    minimum_isotonic_step_support: int | None
    calibrated_probability_zero_count: int | None
    calibrated_probability_one_count: int | None


@dataclass(frozen=True)
class CalibrationCandidateResult:
    method: CalibrationMethod
    evaluable_fold_count: int
    mean_brier_score: float | None
    brier_standard_error: float | None
    mean_log_loss: float | None
    mean_expected_calibration_error: float | None
    mean_maximum_calibration_error: float | None
    mean_calibration_slope: float | None
    mean_calibration_intercept: float | None
    mean_roc_auc: float | None
    mean_pr_auc: float | None
    mean_rank_correlation: float | None
    mean_unique_calibrated_value_count: float | None
    mean_largest_plateau_percentage: float | None
    minimum_isotonic_step_support: int | None
    calibrated_probability_zero_count: int
    calibrated_probability_one_count: int
    eligible: bool
    reason: str


@dataclass(frozen=True)
class CalibrationSelectionResult:
    schema_version: str
    selected_method: CalibrationMethod
    selected_calibrator: ProbabilityCalibrator
    candidate_results: tuple[CalibrationCandidateResult, ...]
    fold_results: tuple[CalibrationFoldResult, ...]
    fold_definitions: tuple[CalibrationFoldDefinition, ...]
    selection_reason: str
    one_standard_error_boundary: float | None
    method_complexity_order: tuple[CalibrationMethod, ...]
    final_fit_start: str
    final_fit_end: str
    final_fit_rows: int
    calibration_manifest_hash: str
    calibrator_artifact_hash: str
    raw_score_distribution: dict[str, object]
    calibrated_score_distribution: dict[str, object]
    plateau_diagnostics: dict[str, object]
    step_support_records: tuple[dict[str, object], ...]

    def metadata(self) -> dict[str, object]:
        return {
            "calibration_governance_schema": self.schema_version,
            "selected_method": self.selected_method,
            "candidate_methods_evaluated": list(CALIBRATION_METHODS),
            "fold_definitions": [asdict(item) for item in self.fold_definitions],
            "fold_results": [asdict(item) for item in self.fold_results],
            "candidate_results": [asdict(item) for item in self.candidate_results],
            "one_standard_error_boundary": self.one_standard_error_boundary,
            "method_complexity_order": list(self.method_complexity_order),
            "selection_reason": self.selection_reason,
            "final_fit_start": self.final_fit_start,
            "final_fit_end": self.final_fit_end,
            "final_fit_rows": self.final_fit_rows,
            "calibration_manifest_hash": self.calibration_manifest_hash,
            "calibrator_artifact_hash": self.calibrator_artifact_hash,
            "raw_score_distribution": self.raw_score_distribution,
            "calibrated_score_distribution": self.calibrated_score_distribution,
            "plateau_diagnostics": self.plateau_diagnostics,
            "step_support_records": list(self.step_support_records),
        }


@dataclass(frozen=True)
class CalibrationAuditArtifact:
    probability_audit_path: str
    method_comparison_path: str
    fold_metrics_path: str
    step_support_path: str
    threshold_utility_path: str
    governance_json_path: str
    calibration_manifest_hash: str


def _calibrator_for_method(method: CalibrationMethod, random_seed: int) -> ProbabilityCalibrator:
    if method == "identity":
        return IdentityProbabilityCalibrator()
    if method == "sigmoid":
        return SigmoidProbabilityCalibrator(random_seed=random_seed)
    return IsotonicProbabilityCalibrator()


def _coerce_int(value: object) -> int:
    return int(cast(int | float | str, value))


def _coerce_float(value: object) -> float:
    return float(cast(int | float | str, value))


def _finite_probability_contract(values: np.ndarray) -> bool:
    data = np.asarray(values, dtype=float)
    return bool(np.all(np.isfinite(data)) and np.all(data >= 0.0) and np.all(data <= 1.0))


def _mean(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return float(np.mean(finite)) if finite else None


def _standard_error(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not finite:
        return None
    if len(finite) == 1:
        return 0.0
    return float(np.std(finite, ddof=1) / math.sqrt(len(finite)))


def _score_distribution(values: np.ndarray) -> dict[str, object]:
    data = np.asarray(values, dtype=float)
    data = data[np.isfinite(data)]
    if len(data) == 0:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "unique_value_count": 0,
            "largest_plateau_count": 0,
            "largest_plateau_percentage": None,
            "zero_count": 0,
            "one_count": 0,
        }
    rounded = np.round(data, 12)
    counts = pd.Series(rounded).value_counts()
    largest_count = int(counts.iloc[0]) if not counts.empty else 0
    return {
        "count": len(data),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "median": float(np.median(data)),
        "std": float(np.std(data)),
        "p01": float(np.percentile(data, 1)),
        "p05": float(np.percentile(data, 5)),
        "p10": float(np.percentile(data, 10)),
        "p25": float(np.percentile(data, 25)),
        "p50": float(np.percentile(data, 50)),
        "p75": float(np.percentile(data, 75)),
        "p90": float(np.percentile(data, 90)),
        "p95": float(np.percentile(data, 95)),
        "p99": float(np.percentile(data, 99)),
        "unique_value_count": len(counts),
        "largest_plateau_count": largest_count,
        "largest_plateau_percentage": float(largest_count / len(data)),
        "zero_count": int(np.sum(data == 0.0)),
        "one_count": int(np.sum(data == 1.0)),
    }


def _calibration_table_errors(target: np.ndarray, probability: np.ndarray) -> tuple[float, float]:
    frame = pd.DataFrame({"target": target.astype(float), "probability": probability}).dropna()
    if frame.empty:
        return math.nan, math.nan
    frame["decile"] = pd.qcut(
        frame["probability"].rank(method="first"),
        q=min(10, len(frame)),
        labels=False,
        duplicates="drop",
    )
    total = len(frame)
    expected_error = 0.0
    maximum_error = 0.0
    for _, group in frame.groupby("decile", dropna=True):
        error = abs(float(group["probability"].mean()) - float(group["target"].mean()))
        expected_error += (len(group) / total) * error
        maximum_error = max(maximum_error, error)
    return float(expected_error), float(maximum_error)


def _calibration_intercept_slope(
    target: np.ndarray, probability: np.ndarray
) -> tuple[float, float]:
    target = np.asarray(target, dtype=int)
    probability = np.asarray(probability, dtype=float)
    mask = np.isfinite(probability)
    target = target[mask]
    probability = probability[mask]
    if len(target) == 0 or len(np.unique(target)) < 2:
        return math.nan, math.nan
    clipped = np.clip(probability, 1e-6, 1.0 - 1e-6)
    logits = np.log(clipped / (1.0 - clipped))
    model = LogisticRegression(C=1_000_000.0, solver="lbfgs")
    model.fit(logits.reshape(-1, 1), target)
    return float(model.intercept_[0]), float(model.coef_[0][0])


def _rank_correlation(raw: np.ndarray, calibrated: np.ndarray) -> float | None:
    raw_series = pd.Series(np.asarray(raw, dtype=float))
    calibrated_series = pd.Series(np.asarray(calibrated, dtype=float))
    value = raw_series.corr(calibrated_series, method="spearman")
    return float(value) if value is not None and math.isfinite(float(value)) else None


def _binary_metrics(
    target: np.ndarray,
    raw_probability: np.ndarray,
    calibrated_probability: np.ndarray,
    *,
    method: CalibrationMethod,
) -> dict[str, float | int | None]:
    target = np.asarray(target, dtype=int)
    probability = np.asarray(calibrated_probability, dtype=float)
    ece, mce = _calibration_table_errors(target, probability)
    intercept, slope = _calibration_intercept_slope(target, probability)
    try:
        roc_auc = float(roc_auc_score(target, probability))
    except ValueError:
        roc_auc = math.nan
    try:
        pr_auc = float(average_precision_score(target, probability))
    except ValueError:
        pr_auc = math.nan
    try:
        loss = float(log_loss(target, np.clip(probability, 1e-15, 1.0 - 1e-15), labels=[0, 1]))
    except ValueError:
        loss = math.nan
    distribution = _score_distribution(probability)
    minimum_step_support = None
    if method == "isotonic":
        support = _step_support_records(raw_probability, probability, target)
        supports = [_coerce_int(record["step_support"]) for record in support]
        minimum_step_support = min(supports) if supports else None
    return {
        "brier_score": float(brier_score_loss(target, probability)),
        "log_loss": loss,
        "expected_calibration_error": ece,
        "maximum_calibration_error": mce,
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "rank_correlation": _rank_correlation(raw_probability, probability),
        "unique_calibrated_value_count": _coerce_int(distribution["unique_value_count"]),
        "largest_plateau_percentage": cast(
            float | None, distribution["largest_plateau_percentage"]
        ),
        "minimum_isotonic_step_support": minimum_step_support,
        "calibrated_probability_zero_count": _coerce_int(distribution["zero_count"]),
        "calibrated_probability_one_count": _coerce_int(distribution["one_count"]),
    }


def _step_support_records(
    raw_probability: np.ndarray,
    calibrated_probability: np.ndarray,
    target: np.ndarray,
) -> list[dict[str, object]]:
    frame = pd.DataFrame(
        {
            "raw_probability": np.asarray(raw_probability, dtype=float),
            "calibrated_probability": np.asarray(calibrated_probability, dtype=float),
            "target": np.asarray(target, dtype=int),
        }
    ).dropna()
    if frame.empty:
        return []
    frame["plateau_key"] = frame["calibrated_probability"].round(12)
    records: list[dict[str, object]] = []
    grouped = frame.groupby("plateau_key", sort=True)
    for step_id, (_, group) in enumerate(grouped, start=1):
        records.append(
            {
                "step_id": step_id,
                "calibrated_probability": float(group["calibrated_probability"].mean()),
                "step_support": len(group),
                "positive_count": int(group["target"].sum()),
                "raw_score_min": float(group["raw_probability"].min()),
                "raw_score_max": float(group["raw_probability"].max()),
            }
        )
    return records


def _chronological_fold_definitions(
    dates: pd.Series,
    *,
    fold_count: int = 3,
) -> tuple[
    tuple[tuple[pd.Timestamp, pd.Timestamp], ...],
    tuple[CalibrationFoldDefinition, ...],
]:
    date_values = pd.to_datetime(dates)
    unique_dates = [pd.Timestamp(value) for value in sorted(date_values.dropna().unique())]
    if len(unique_dates) < fold_count + 1:
        return (), ()
    segments: list[list[pd.Timestamp]] = [
        [unique_dates[int(index)] for index in segment]
        for segment in np.array_split(np.arange(len(unique_dates)), fold_count + 1)
    ]
    definitions: list[CalibrationFoldDefinition] = []
    boundaries: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for index in range(1, len(segments)):
        fit_dates = [date for segment in segments[:index] for date in segment]
        eval_dates = segments[index]
        if not fit_dates or not eval_dates:
            continue
        fit_start = fit_dates[0]
        fit_end = fit_dates[-1]
        eval_start = eval_dates[0]
        eval_end = eval_dates[-1]
        fit_rows = int(((date_values >= fit_start) & (date_values <= fit_end)).sum())
        eval_rows = int(((date_values >= eval_start) & (date_values <= eval_end)).sum())
        definitions.append(
            CalibrationFoldDefinition(
                fold_id=index,
                fit_start=fit_start.date().isoformat(),
                fit_end=fit_end.date().isoformat(),
                evaluation_start=eval_start.date().isoformat(),
                evaluation_end=eval_end.date().isoformat(),
                fit_rows=fit_rows,
                evaluation_rows=eval_rows,
                evaluable=True,
                reason="evaluable",
            )
        )
        boundaries.append((eval_start, eval_end))
    return tuple(boundaries), tuple(definitions)


def _fold_result_unavailable(
    *,
    method: CalibrationMethod,
    definition: CalibrationFoldDefinition,
    reason: str,
) -> CalibrationFoldResult:
    return CalibrationFoldResult(
        method=method,
        fold_id=definition.fold_id,
        status="unevaluable",
        reason=reason,
        fit_rows=definition.fit_rows,
        evaluation_rows=definition.evaluation_rows,
        brier_score=None,
        log_loss=None,
        expected_calibration_error=None,
        maximum_calibration_error=None,
        calibration_slope=None,
        calibration_intercept=None,
        roc_auc=None,
        pr_auc=None,
        rank_correlation=None,
        unique_calibrated_value_count=None,
        largest_plateau_percentage=None,
        minimum_isotonic_step_support=None,
        calibrated_probability_zero_count=None,
        calibrated_probability_one_count=None,
    )


def select_method_by_one_standard_error(
    candidate_results: tuple[CalibrationCandidateResult, ...],
) -> tuple[CalibrationMethod, float | None, str]:
    eligible_candidates = [
        item
        for item in candidate_results
        if item.eligible
        and item.mean_brier_score is not None
        and math.isfinite(item.mean_brier_score)
    ]
    if len(eligible_candidates) < 2:
        return "identity", None, "insufficient_calibration_folds_for_learned_calibrator"
    best = min(eligible_candidates, key=lambda item: cast(float, item.mean_brier_score))
    boundary = cast(float, best.mean_brier_score) + float(best.brier_standard_error or 0.0)
    within_boundary = [
        item
        for item in eligible_candidates
        if cast(float, item.mean_brier_score) <= boundary + 1e-15
    ]
    selected_method = min(
        (item.method for item in within_boundary),
        key=lambda method: CALIBRATION_METHOD_COMPLEXITY.index(method),
    )
    reason = (
        "one_standard_error_simplest_method"
        if selected_method != best.method
        else "lowest_mean_chronological_fold_brier"
    )
    return selected_method, boundary, reason


def select_tbs_calibrator(
    *,
    raw_probability: np.ndarray,
    target: np.ndarray,
    dates: pd.Series,
    random_seed: int,
) -> CalibrationSelectionResult:
    raw = np.asarray(raw_probability, dtype=float)
    y = np.asarray(target, dtype=int)
    date_values = pd.to_datetime(dates).reset_index(drop=True)
    if len(raw) != len(y) or len(raw) != len(date_values):
        raise ValueError("Calibration raw probabilities, target, and dates are misaligned")
    if not _finite_probability_contract(raw):
        raise ValueError("Raw calibration probabilities violate the probability contract")
    _, definitions = _chronological_fold_definitions(date_values)
    fold_results: list[CalibrationFoldResult] = []
    by_method: dict[CalibrationMethod, list[CalibrationFoldResult]] = {
        method: [] for method in CALIBRATION_METHODS
    }
    for definition in definitions:
        fit_start = pd.Timestamp(definition.fit_start)
        fit_end = pd.Timestamp(definition.fit_end)
        evaluation_start = pd.Timestamp(definition.evaluation_start)
        evaluation_end = pd.Timestamp(definition.evaluation_end)
        fit_mask = (date_values >= fit_start) & (date_values <= fit_end)
        eval_mask = (date_values >= evaluation_start) & (date_values <= evaluation_end)
        fit_y = y[np.asarray(fit_mask, dtype=bool)]
        eval_y = y[np.asarray(eval_mask, dtype=bool)]
        if len(np.unique(fit_y)) < 2:
            for method in CALIBRATION_METHODS:
                result = _fold_result_unavailable(
                    method=method,
                    definition=definition,
                    reason="fit_fold_lacks_both_target_classes",
                )
                fold_results.append(result)
                by_method[method].append(result)
            continue
        if len(np.unique(eval_y)) < 2:
            for method in CALIBRATION_METHODS:
                result = _fold_result_unavailable(
                    method=method,
                    definition=definition,
                    reason="evaluation_fold_lacks_both_target_classes",
                )
                fold_results.append(result)
                by_method[method].append(result)
            continue
        fit_raw = raw[np.asarray(fit_mask, dtype=bool)]
        eval_raw = raw[np.asarray(eval_mask, dtype=bool)]
        for method in CALIBRATION_METHODS:
            try:
                calibrator = _calibrator_for_method(method, random_seed)
                calibrator.fit(fit_raw, fit_y)
                prediction = calibrator.predict(eval_raw)
                if not _finite_probability_contract(prediction):
                    raise ValueError("calibrated predictions violate probability contract")
                metrics = _binary_metrics(eval_y, eval_raw, prediction, method=method)
                result = CalibrationFoldResult(
                    method=method,
                    fold_id=definition.fold_id,
                    status="evaluable",
                    reason="ok",
                    fit_rows=definition.fit_rows,
                    evaluation_rows=definition.evaluation_rows,
                    brier_score=cast(float, metrics["brier_score"]),
                    log_loss=cast(float, metrics["log_loss"]),
                    expected_calibration_error=cast(float, metrics["expected_calibration_error"]),
                    maximum_calibration_error=cast(float, metrics["maximum_calibration_error"]),
                    calibration_slope=cast(float, metrics["calibration_slope"]),
                    calibration_intercept=cast(float, metrics["calibration_intercept"]),
                    roc_auc=cast(float, metrics["roc_auc"]),
                    pr_auc=cast(float, metrics["pr_auc"]),
                    rank_correlation=cast(float | None, metrics["rank_correlation"]),
                    unique_calibrated_value_count=cast(
                        int, metrics["unique_calibrated_value_count"]
                    ),
                    largest_plateau_percentage=cast(
                        float | None, metrics["largest_plateau_percentage"]
                    ),
                    minimum_isotonic_step_support=cast(
                        int | None, metrics["minimum_isotonic_step_support"]
                    ),
                    calibrated_probability_zero_count=cast(
                        int, metrics["calibrated_probability_zero_count"]
                    ),
                    calibrated_probability_one_count=cast(
                        int, metrics["calibrated_probability_one_count"]
                    ),
                )
            except ValueError as exc:
                result = _fold_result_unavailable(
                    method=method,
                    definition=definition,
                    reason=str(exc),
                )
            fold_results.append(result)
            by_method[method].append(result)

    candidate_results: list[CalibrationCandidateResult] = []
    for method in CALIBRATION_METHODS:
        method_folds = [item for item in by_method[method] if item.status == "evaluable"]
        briers = [item.brier_score for item in method_folds]
        min_support_values = [
            int(item.minimum_isotonic_step_support)
            for item in method_folds
            if item.minimum_isotonic_step_support is not None
        ]
        candidate_results.append(
            CalibrationCandidateResult(
                method=method,
                evaluable_fold_count=len(method_folds),
                mean_brier_score=_mean(briers),
                brier_standard_error=_standard_error(briers),
                mean_log_loss=_mean([item.log_loss for item in method_folds]),
                mean_expected_calibration_error=_mean(
                    [item.expected_calibration_error for item in method_folds]
                ),
                mean_maximum_calibration_error=_mean(
                    [item.maximum_calibration_error for item in method_folds]
                ),
                mean_calibration_slope=_mean([item.calibration_slope for item in method_folds]),
                mean_calibration_intercept=_mean(
                    [item.calibration_intercept for item in method_folds]
                ),
                mean_roc_auc=_mean([item.roc_auc for item in method_folds]),
                mean_pr_auc=_mean([item.pr_auc for item in method_folds]),
                mean_rank_correlation=_mean([item.rank_correlation for item in method_folds]),
                mean_unique_calibrated_value_count=_mean(
                    [
                        float(item.unique_calibrated_value_count)
                        if item.unique_calibrated_value_count is not None
                        else None
                        for item in method_folds
                    ]
                ),
                mean_largest_plateau_percentage=_mean(
                    [item.largest_plateau_percentage for item in method_folds]
                ),
                minimum_isotonic_step_support=min(min_support_values)
                if min_support_values
                else None,
                calibrated_probability_zero_count=sum(
                    int(item.calibrated_probability_zero_count or 0) for item in method_folds
                ),
                calibrated_probability_one_count=sum(
                    int(item.calibrated_probability_one_count or 0) for item in method_folds
                ),
                eligible=len(method_folds) >= 2,
                reason="ok" if len(method_folds) >= 2 else "fewer_than_two_evaluable_folds",
            )
        )

    selected_method, boundary, reason = select_method_by_one_standard_error(
        tuple(candidate_results)
    )

    final_calibrator = _calibrator_for_method(selected_method, random_seed)
    final_calibrator.fit(raw, y)
    calibrated = final_calibrator.predict(raw)
    if not _finite_probability_contract(calibrated):
        raise ValueError("Final calibrated probabilities violate the probability contract")
    step_support = tuple(_step_support_records(raw, calibrated, y))
    raw_distribution = _score_distribution(raw)
    calibrated_distribution = _score_distribution(calibrated)
    support_values = [_coerce_int(record["step_support"]) for record in step_support]
    plateau_diagnostics = {
        "step_count": len(step_support),
        "smallest_step_support": min(support_values) if support_values else None,
        "largest_step_support": max(support_values) if support_values else None,
        "largest_plateau_percentage": calibrated_distribution["largest_plateau_percentage"],
        "support_probability_0": sum(
            _coerce_int(record["step_support"])
            for record in step_support
            if _coerce_float(record["calibrated_probability"]) == 0.0
        ),
        "support_probability_1": sum(
            _coerce_int(record["step_support"])
            for record in step_support
            if _coerce_float(record["calibrated_probability"]) == 1.0
        ),
    }
    fit_dates = pd.to_datetime(dates).reset_index(drop=True)
    manifest_payload: dict[str, object] = {
        "schema_version": TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION,
        "selected_method": selected_method,
        "candidate_results": [asdict(item) for item in candidate_results],
        "fold_definitions": [asdict(item) for item in definitions],
        "selection_reason": reason,
        "one_standard_error_boundary": boundary,
        "final_fit_start": fit_dates.min().date().isoformat(),
        "final_fit_end": fit_dates.max().date().isoformat(),
        "final_fit_rows": len(raw),
    }
    manifest_hash = configuration_hash(manifest_payload)
    artifact_hash = configuration_hash(
        {
            "schema_version": TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION,
            "calibrator_parameters": final_calibrator.parameters(),
        }
    )
    return CalibrationSelectionResult(
        schema_version=TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION,
        selected_method=selected_method,
        selected_calibrator=final_calibrator,
        candidate_results=tuple(candidate_results),
        fold_results=tuple(fold_results),
        fold_definitions=definitions,
        selection_reason=reason,
        one_standard_error_boundary=boundary,
        method_complexity_order=CALIBRATION_METHOD_COMPLEXITY,
        final_fit_start=fit_dates.min().date().isoformat(),
        final_fit_end=fit_dates.max().date().isoformat(),
        final_fit_rows=len(raw),
        calibration_manifest_hash=manifest_hash,
        calibrator_artifact_hash=artifact_hash,
        raw_score_distribution=raw_distribution,
        calibrated_score_distribution=calibrated_distribution,
        plateau_diagnostics=plateau_diagnostics,
        step_support_records=step_support,
    )


def _fold_id_for_date(
    value: pd.Timestamp,
    definitions: tuple[CalibrationFoldDefinition, ...],
) -> int | None:
    for definition in definitions:
        if (
            pd.Timestamp(definition.evaluation_start)
            <= value
            <= pd.Timestamp(definition.evaluation_end)
        ):
            return definition.fold_id
    return None


def _step_lookup(step_support: tuple[dict[str, object], ...]) -> dict[float, dict[str, object]]:
    return {
        round(_coerce_float(record["calibrated_probability"]), 12): record
        for record in step_support
    }


def build_probability_audit_frame(
    *,
    calibration_frame: pd.DataFrame,
    development_holdout_frame: pd.DataFrame,
    calibration_raw_probability: np.ndarray,
    calibration_calibrated_probability: np.ndarray,
    development_holdout_raw_probability: np.ndarray,
    development_holdout_calibrated_probability: np.ndarray,
    target_column: str,
    selection: CalibrationSelectionResult,
    model_id: str,
    direction: str,
    horizon: int,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    lookup = _step_lookup(selection.step_support_records)
    for split_name, frame, raw, calibrated in (
        (
            "calibration",
            calibration_frame,
            calibration_raw_probability,
            calibration_calibrated_probability,
        ),
        (
            "development_holdout",
            development_holdout_frame,
            development_holdout_raw_probability,
            development_holdout_calibrated_probability,
        ),
    ):
        item = frame[["Date", "symbol", target_column]].copy()
        item["split"] = split_name
        item["raw_classifier_probability"] = np.asarray(raw, dtype=float)
        item["selected_calibrated_probability"] = np.asarray(calibrated, dtype=float)
        item["target_label"] = item[target_column]
        item["calibrator_method"] = selection.selected_method
        item["calibration_fold_id"] = (
            [
                _fold_id_for_date(pd.Timestamp(value), selection.fold_definitions)
                for value in pd.to_datetime(item["Date"])
            ]
            if split_name == "calibration"
            else None
        )
        step_ids: list[int | None] = []
        step_supports: list[int | None] = []
        for probability in item["selected_calibrated_probability"].astype(float):
            step = lookup.get(round(float(probability), 12))
            step_ids.append(_coerce_int(step["step_id"]) if step else None)
            step_supports.append(_coerce_int(step["step_support"]) if step else None)
        item["probability_plateau_or_step_id"] = step_ids
        item["step_support"] = step_supports
        item["model_id"] = model_id
        item["direction"] = direction
        item["horizon"] = horizon
        item["calibration_manifest_hash"] = selection.calibration_manifest_hash
        rows.append(item.drop(columns=[target_column]))
    return pd.concat(rows, ignore_index=True)


def calibration_threshold_utility(
    *,
    frame: pd.DataFrame,
    calibrated_probability: np.ndarray,
    direction: str,
    horizon: int,
    model_id: str,
) -> list[dict[str, object]]:
    target_column = f"label_{direction}_target_before_stop_{horizon}"
    stop_column = f"label_{direction}_stop_before_target_{horizon}"
    returns_column = f"label_{direction}_forward_return_{horizon}"
    data = frame.copy()
    data["calibrated_probability"] = np.asarray(calibrated_probability, dtype=float)
    rows: list[dict[str, object]] = []
    for threshold in CALIBRATION_THRESHOLD_GRID:
        selected = data.loc[data["calibrated_probability"] >= threshold]
        if selected.empty:
            rows.append(
                {
                    "model_id": model_id,
                    "threshold": threshold,
                    "observations": 0,
                    "target_hit_probability": None,
                    "stop_hit_probability": None,
                    "unresolved_probability": None,
                    "expected_payoff_atr_units": None,
                    "transaction_cost_adjusted_utility": None,
                    "mean_directional_return": None,
                    "symbol_concentration": None,
                    "sector_concentration": None,
                }
            )
            continue
        target_rate = float(selected[target_column].astype(float).mean())
        stop_rate = (
            float(selected[stop_column].astype(float).mean()) if stop_column in selected else 0.0
        )
        unresolved_rate = max(0.0, 1.0 - target_rate - stop_rate)
        payoff = 2.0 * target_rate - stop_rate
        rows.append(
            {
                "model_id": model_id,
                "threshold": threshold,
                "observations": len(selected),
                "target_hit_probability": target_rate,
                "stop_hit_probability": stop_rate,
                "unresolved_probability": unresolved_rate,
                "expected_payoff_atr_units": payoff,
                "transaction_cost_adjusted_utility": payoff - 0.0005,
                "mean_directional_return": float(selected[returns_column].mean())
                if returns_column in selected
                else None,
                "symbol_concentration": float(
                    selected["symbol"].value_counts(normalize=True).iloc[0]
                )
                if "symbol" in selected
                else None,
                "sector_concentration": float(
                    selected["sector"].value_counts(normalize=True).iloc[0]
                )
                if "sector" in selected
                else None,
            }
        )
    return rows


def write_calibration_audit_artifacts(
    *,
    audit_dir: str | Path,
    selection: CalibrationSelectionResult,
    probability_audit: pd.DataFrame,
    threshold_utility: list[dict[str, object]],
    model_id: str,
    direction: str,
    horizon: int,
) -> CalibrationAuditArtifact:
    output = Path(audit_dir)
    output.mkdir(parents=True, exist_ok=True)
    prefix = f"{model_id}_tbs_calibration"
    probability_path = output / f"{prefix}_probability_audit.parquet"
    comparison_path = output / f"{prefix}_method_comparison.csv"
    fold_path = output / f"{prefix}_fold_metrics.csv"
    step_path = output / f"{prefix}_step_support.csv"
    utility_path = output / f"{prefix}_threshold_utility.csv"
    governance_path = output / f"{prefix}_governance.json"

    probability_audit.to_parquet(probability_path, index=False)
    pd.DataFrame([asdict(item) for item in selection.candidate_results]).to_csv(
        comparison_path, index=False
    )
    pd.DataFrame([asdict(item) for item in selection.fold_results]).to_csv(fold_path, index=False)
    pd.DataFrame(list(selection.step_support_records)).to_csv(step_path, index=False)
    pd.DataFrame(threshold_utility).to_csv(utility_path, index=False)
    governance_payload = {
        **selection.metadata(),
        "model_id": model_id,
        "direction": direction,
        "horizon": horizon,
        "probability_audit_path": str(probability_path),
        "method_comparison_path": str(comparison_path),
        "fold_metrics_path": str(fold_path),
        "step_support_path": str(step_path),
        "threshold_utility_path": str(utility_path),
    }
    governance_path.write_text(
        json.dumps(governance_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return CalibrationAuditArtifact(
        probability_audit_path=str(probability_path),
        method_comparison_path=str(comparison_path),
        fold_metrics_path=str(fold_path),
        step_support_path=str(step_path),
        threshold_utility_path=str(utility_path),
        governance_json_path=str(governance_path),
        calibration_manifest_hash=selection.calibration_manifest_hash,
    )


def binary_probability_quality(
    target: np.ndarray,
    raw_probability: np.ndarray,
    calibrated_probability: np.ndarray,
    *,
    method: CalibrationMethod,
) -> dict[str, float | int | None]:
    return _binary_metrics(
        np.asarray(target, dtype=int),
        np.asarray(raw_probability, dtype=float),
        np.asarray(calibrated_probability, dtype=float),
        method=method,
    )


def probability_distribution_summary(values: np.ndarray) -> dict[str, object]:
    return _score_distribution(np.asarray(values, dtype=float))
