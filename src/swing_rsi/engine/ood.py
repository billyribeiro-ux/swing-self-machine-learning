from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

PREDICTION_OOD_GOVERNANCE_VERSION = "prediction_ood_governance_v2"
WILSON_Z_99 = 2.326347874
OOD_EPSILON = 1e-12
REGRESSION_HEADS = ("return", "mfe", "mae")
HEAD_OUTPUT_COLUMNS = {
    "return": "expected_return",
    "mfe": "expected_mfe",
    "mae": "expected_mae",
}


@dataclass(frozen=True)
class LiveOodCheck:
    head: str
    output_column: str
    value: float
    lower_bound: float
    upper_bound: float
    robust_range: float
    is_ood: bool
    severity: float
    severity_limit: float
    rate_limit: float
    governance_version: str
    metadata_missing: bool


def _numeric_series(values: pd.Series | np.ndarray | list[object]) -> pd.Series:
    return pd.to_numeric(pd.Series(values), errors="coerce")


def _finite_values(values: pd.Series | np.ndarray | list[object]) -> pd.Series:
    numeric = _numeric_series(values)
    finite = np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan))
    return pd.Series(numeric.loc[finite])


def _coerce_float(value: object) -> float:
    return float(str(value))


def quantile_metrics(
    prefix: str, values: pd.Series | np.ndarray | list[object]
) -> dict[str, float]:
    numeric = _finite_values(values)
    if numeric.empty:
        return {
            f"{prefix}_count": 0.0,
            f"{prefix}_min": math.nan,
            f"{prefix}_max": math.nan,
            f"{prefix}_mean": math.nan,
            f"{prefix}_median": math.nan,
            f"{prefix}_std": math.nan,
            f"{prefix}_q01": math.nan,
            f"{prefix}_q05": math.nan,
            f"{prefix}_q95": math.nan,
            f"{prefix}_q99": math.nan,
        }
    return {
        f"{prefix}_count": float(len(numeric)),
        f"{prefix}_min": float(numeric.min()),
        f"{prefix}_max": float(numeric.max()),
        f"{prefix}_mean": float(numeric.mean()),
        f"{prefix}_median": float(numeric.median()),
        f"{prefix}_std": float(numeric.std(ddof=0)),
        f"{prefix}_q01": float(numeric.quantile(0.01)),
        f"{prefix}_q05": float(numeric.quantile(0.05)),
        f"{prefix}_q95": float(numeric.quantile(0.95)),
        f"{prefix}_q99": float(numeric.quantile(0.99)),
    }


def wilson_upper_99(k: int, n: int, *, z: float = WILSON_Z_99) -> float:
    if n <= 0:
        return math.nan
    successes = min(max(int(k), 0), int(n))
    denominator = 1.0 + ((z * z) / n)
    phat = successes / n
    center = phat + ((z * z) / (2.0 * n))
    radius = z * math.sqrt((phat * (1.0 - phat) / n) + ((z * z) / (4.0 * n * n)))
    return float((center + radius) / denominator)


def ood_rate_limit(k_calibration_ood: int, n_calibration: int) -> float:
    upper = wilson_upper_99(k_calibration_ood, n_calibration)
    if not math.isfinite(upper):
        return math.nan
    return float(min(0.05, max(0.02, upper + 0.005)))


def ood_severity_values(
    predictions: pd.Series | np.ndarray | list[object],
    *,
    lower_bound: float,
    upper_bound: float,
    epsilon: float = OOD_EPSILON,
) -> pd.Series:
    numeric = _numeric_series(predictions)
    robust_range = max(float(upper_bound) - float(lower_bound), float(epsilon))
    low_overshoot = np.maximum(0.0, float(lower_bound) - numeric.to_numpy(dtype=float))
    high_overshoot = np.maximum(0.0, numeric.to_numpy(dtype=float) - float(upper_bound))
    severity = np.maximum(low_overshoot, high_overshoot) / robust_range
    return pd.Series(severity, index=numeric.index)


def _count_ood(severity: pd.Series) -> int:
    finite = severity[np.isfinite(severity.to_numpy(dtype=float, na_value=np.nan))]
    return int((finite > 0.0).sum())


def _ood_rate(severity: pd.Series) -> float:
    finite = severity[np.isfinite(severity.to_numpy(dtype=float, na_value=np.nan))]
    if finite.empty:
        return math.nan
    return float((finite > 0.0).mean())


def _nonzero_q99(severity: pd.Series) -> float:
    finite = severity[np.isfinite(severity.to_numpy(dtype=float, na_value=np.nan))]
    nonzero = finite.loc[finite > 0.0]
    if nonzero.empty:
        return 0.0
    return float(nonzero.quantile(0.99))


def _max_severity(severity: pd.Series) -> float:
    finite = severity[np.isfinite(severity.to_numpy(dtype=float, na_value=np.nan))]
    if finite.empty:
        return 0.0
    return float(finite.max())


def _nonfinite_count(values: pd.Series | np.ndarray | list[object]) -> int:
    numeric = _numeric_series(values)
    finite = np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan))
    return int((~finite).sum())


def path_metric_sign_valid(head: str, predictions: pd.Series | np.ndarray | list[object]) -> bool:
    numeric = _finite_values(predictions)
    if head == "mfe":
        return bool((numeric >= 0.0).all())
    if head == "mae":
        return bool((numeric <= 0.0).all())
    return True


def severity_q99_limit(calibration_q99_severity: float) -> float:
    if not math.isfinite(calibration_q99_severity):
        return math.nan
    return float(min(0.50, max(0.10, calibration_q99_severity + 0.05)))


def regression_head_ood_metrics(
    *,
    name: str,
    direction: str,
    horizon: int,
    train_target: pd.Series,
    calibration_target: pd.Series,
    holdout_target: pd.Series,
    calibration_prediction: pd.Series,
    holdout_prediction: pd.Series,
) -> dict[str, float | int | str | bool]:
    metrics: dict[str, float | int | str | bool] = {
        f"{name}_prediction_ood_governance_version": PREDICTION_OOD_GOVERNANCE_VERSION,
        f"{name}_ood_bound_provenance": "training_targets_only",
        f"{name}_ood_bound_head": name,
        f"{name}_ood_bound_direction": direction,
        f"{name}_ood_bound_horizon": int(horizon),
        f"{name}_prediction_transform_method": "none",
        f"{name}_prediction_unit_contract": "decimal_return",
        f"{name}_prediction_head_bound_mapping_valid": True,
        f"{name}_prediction_bounds_training_only": True,
    }
    metrics.update(quantile_metrics(f"{name}_train_target", train_target))
    metrics.update(quantile_metrics(f"{name}_calibration_target", calibration_target))
    metrics.update(quantile_metrics(f"{name}_holdout_target", holdout_target))
    metrics.update(quantile_metrics(f"{name}_calibration_prediction_raw", calibration_prediction))
    metrics.update(quantile_metrics(f"{name}_holdout_prediction_raw", holdout_prediction))
    metrics.update(quantile_metrics(f"{name}_holdout_prediction_transformed", holdout_prediction))
    low = float(metrics[f"{name}_train_target_q01"])
    high = float(metrics[f"{name}_train_target_q99"])
    robust_range = max(high - low, OOD_EPSILON) if math.isfinite(high - low) else math.nan
    calibration_severity = ood_severity_values(
        calibration_prediction,
        lower_bound=low,
        upper_bound=high,
    )
    holdout_severity = ood_severity_values(
        holdout_prediction,
        lower_bound=low,
        upper_bound=high,
    )
    calibration_count = len(_finite_values(calibration_prediction))
    holdout_count = len(_finite_values(holdout_prediction))
    calibration_ood_count = _count_ood(calibration_severity)
    holdout_ood_count = _count_ood(holdout_severity)
    calibration_ood_rate = _ood_rate(calibration_severity)
    holdout_ood_rate = _ood_rate(holdout_severity)
    frozen_rate_limit = ood_rate_limit(calibration_ood_count, calibration_count)
    calibration_q99 = _nonzero_q99(calibration_severity)
    frozen_severity_limit = severity_q99_limit(calibration_q99)
    holdout_q99 = _nonzero_q99(holdout_severity)
    holdout_max = _max_severity(holdout_severity)
    metrics.update(
        {
            f"{name}_prediction_bound_low_train_q01": low,
            f"{name}_prediction_bound_high_train_q99": high,
            f"{name}_prediction_bound_robust_range_train_q01_q99": robust_range,
            f"{name}_calibration_prediction_count": calibration_count,
            f"{name}_calibration_prediction_nonfinite_count": _nonfinite_count(
                calibration_prediction
            ),
            f"{name}_calibration_ood_count": calibration_ood_count,
            f"{name}_calibration_ood_rate": calibration_ood_rate,
            f"{name}_calibration_ood_rate_limit": frozen_rate_limit,
            f"{name}_calibration_ood_q99_severity": calibration_q99,
            f"{name}_ood_severity_q99_limit": frozen_severity_limit,
            f"{name}_holdout_prediction_count": holdout_count,
            f"{name}_holdout_prediction_nonfinite_count": _nonfinite_count(holdout_prediction),
            f"{name}_holdout_ood_count": holdout_ood_count,
            f"{name}_holdout_ood_rate": holdout_ood_rate,
            f"{name}_holdout_ood_q99_severity": holdout_q99,
            f"{name}_holdout_ood_max_severity": holdout_max,
            f"{name}_prediction_ood_count": holdout_ood_count,
            f"{name}_prediction_ood_rate": holdout_ood_rate,
            f"{name}_prediction_values_finite": _nonfinite_count(holdout_prediction) == 0
            and _nonfinite_count(calibration_prediction) == 0,
            f"{name}_prediction_path_metric_sign_valid": path_metric_sign_valid(
                name, calibration_prediction
            )
            and path_metric_sign_valid(name, holdout_prediction),
            f"{name}_calibration_ood_rate_acceptable": math.isfinite(calibration_ood_rate)
            and calibration_ood_rate <= 0.05,
            f"{name}_holdout_ood_rate_acceptable": math.isfinite(holdout_ood_rate)
            and math.isfinite(frozen_rate_limit)
            and holdout_ood_rate <= frozen_rate_limit,
            f"{name}_holdout_ood_q99_severity_acceptable": math.isfinite(holdout_q99)
            and math.isfinite(frozen_severity_limit)
            and holdout_q99 <= frozen_severity_limit,
            f"{name}_catastrophic_prediction_extrapolation_absent": holdout_max <= 1.0,
        }
    )
    return metrics


def probability_contract_metrics(
    *,
    calibration_probability: np.ndarray,
    holdout_probability: np.ndarray,
    target_calibration_probability: np.ndarray,
    target_holdout_probability: np.ndarray,
) -> dict[str, float | int | str | bool]:
    values = np.concatenate(
        [
            np.asarray(calibration_probability, dtype=float),
            np.asarray(holdout_probability, dtype=float),
            np.asarray(target_calibration_probability, dtype=float),
            np.asarray(target_holdout_probability, dtype=float),
        ]
    )
    finite_mask = np.isfinite(values)
    out_of_range = finite_mask & ((values < 0.0) | (values > 1.0))
    finite_values = values[finite_mask]
    return {
        "classification_prediction_count": len(values),
        "classification_prediction_nonfinite_count": int((~finite_mask).sum()),
        "classification_probability_out_of_range_count": int(out_of_range.sum()),
        "classification_prediction_values_finite": bool(finite_mask.all()),
        "classification_probability_contract_valid": bool(
            finite_mask.all() and not out_of_range.any()
        ),
        "classification_probability_min": float(finite_values.min())
        if finite_values.size
        else math.nan,
        "classification_probability_max": float(finite_values.max())
        if finite_values.size
        else math.nan,
    }


def bundle_ood_identity(metrics: dict[str, Any]) -> dict[str, object]:
    heads: dict[str, dict[str, object]] = {}
    for head in REGRESSION_HEADS:
        heads[head] = {
            "governance_version": metrics.get(f"{head}_prediction_ood_governance_version"),
            "bound_low": metrics.get(f"{head}_prediction_bound_low_train_q01"),
            "bound_high": metrics.get(f"{head}_prediction_bound_high_train_q99"),
            "robust_range": metrics.get(f"{head}_prediction_bound_robust_range_train_q01_q99"),
            "bound_provenance": metrics.get(f"{head}_ood_bound_provenance"),
            "bound_head": metrics.get(f"{head}_ood_bound_head"),
            "bound_direction": metrics.get(f"{head}_ood_bound_direction"),
            "bound_horizon": metrics.get(f"{head}_ood_bound_horizon"),
            "rate_limit": metrics.get(f"{head}_calibration_ood_rate_limit"),
            "severity_q99_limit": metrics.get(f"{head}_ood_severity_q99_limit"),
            "head_bound_mapping_valid": metrics.get(f"{head}_prediction_head_bound_mapping_valid"),
            "bounds_training_only": metrics.get(f"{head}_prediction_bounds_training_only"),
        }
    return {
        "governance_schema_version": metrics.get("prediction_ood_governance_version"),
        "unit_contract": metrics.get("prediction_unit_contract"),
        "heads": heads,
    }


def live_ood_check(
    *,
    metrics: dict[str, Any],
    head: str,
    value: float,
) -> LiveOodCheck:
    output_column = HEAD_OUTPUT_COLUMNS[head]
    version = metrics.get(f"{head}_prediction_ood_governance_version")
    low = metrics.get(f"{head}_prediction_bound_low_train_q01")
    high = metrics.get(f"{head}_prediction_bound_high_train_q99")
    robust_range = metrics.get(f"{head}_prediction_bound_robust_range_train_q01_q99")
    severity_limit = metrics.get(f"{head}_ood_severity_q99_limit")
    rate_limit = metrics.get(f"{head}_calibration_ood_rate_limit")
    missing = (
        version != PREDICTION_OOD_GOVERNANCE_VERSION
        or low is None
        or high is None
        or robust_range is None
        or severity_limit is None
        or rate_limit is None
    )
    try:
        lower = _coerce_float(low)
        upper = _coerce_float(high)
        range_value = max(_coerce_float(robust_range), OOD_EPSILON)
        limit_value = _coerce_float(severity_limit)
        rate_limit_value = _coerce_float(rate_limit)
    except (TypeError, ValueError):
        lower = math.nan
        upper = math.nan
        range_value = math.nan
        limit_value = math.nan
        rate_limit_value = math.nan
        missing = True
    numeric = float(value)
    if missing or not math.isfinite(numeric):
        severity = math.nan
        is_ood = False
    else:
        low_overshoot = max(0.0, lower - numeric) / range_value
        high_overshoot = max(0.0, numeric - upper) / range_value
        severity = float(max(low_overshoot, high_overshoot))
        is_ood = severity > 0.0
    return LiveOodCheck(
        head=head,
        output_column=output_column,
        value=numeric,
        lower_bound=lower,
        upper_bound=upper,
        robust_range=range_value,
        is_ood=is_ood,
        severity=severity,
        severity_limit=limit_value,
        rate_limit=rate_limit_value,
        governance_version=str(version or ""),
        metadata_missing=missing,
    )
