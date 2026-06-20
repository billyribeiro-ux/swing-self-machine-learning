from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DriftMetric:
    name: str
    value: float
    threshold: float
    alert: bool


@dataclass(frozen=True)
class DriftReport:
    model_id: str
    as_of_date: str
    metrics: tuple[DriftMetric, ...]

    @property
    def alert_count(self) -> int:
        return sum(1 for metric in self.metrics if metric.alert)


def feature_distribution_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    feature_columns: tuple[str, ...],
    *,
    threshold: float = 2.5,
) -> DriftMetric:
    scores: list[float] = []
    for column in feature_columns:
        if column not in reference.columns or column not in current.columns:
            continue
        reference_values = pd.to_numeric(reference[column], errors="coerce")
        current_values = pd.to_numeric(current[column], errors="coerce")
        reference_std = float(reference_values.std(ddof=0))
        if not math.isfinite(reference_std) or reference_std <= 1e-12:
            continue
        score = abs(float(current_values.mean()) - float(reference_values.mean())) / reference_std
        if math.isfinite(score):
            scores.append(score)
    value = float(np.nanmean(scores)) if scores else math.nan
    return DriftMetric(
        name="feature_distribution_mean_abs_z",
        value=value,
        threshold=threshold,
        alert=bool(math.isfinite(value) and value > threshold),
    )


def prediction_distribution_drift(
    reference_probabilities: pd.Series | np.ndarray,
    current_probabilities: pd.Series | np.ndarray,
    *,
    threshold: float = 0.20,
) -> DriftMetric:
    reference = np.asarray(reference_probabilities, dtype=float)
    current = np.asarray(current_probabilities, dtype=float)
    value = abs(float(np.nanmean(current)) - float(np.nanmean(reference)))
    return DriftMetric(
        name="prediction_probability_mean_shift",
        value=value,
        threshold=threshold,
        alert=bool(math.isfinite(value) and value > threshold),
    )


def realized_performance_drift(
    reference_returns: pd.Series | np.ndarray,
    current_returns: pd.Series | np.ndarray,
    *,
    threshold: float = 0.02,
) -> DriftMetric:
    reference = np.asarray(reference_returns, dtype=float)
    current = np.asarray(current_returns, dtype=float)
    value = abs(float(np.nanmean(current)) - float(np.nanmean(reference)))
    return DriftMetric(
        name="realized_performance_mean_return_shift",
        value=value,
        threshold=threshold,
        alert=bool(math.isfinite(value) and value > threshold),
    )


def calibration_drift(
    reference_brier: float,
    current_brier: float,
    *,
    threshold: float = 0.05,
) -> DriftMetric:
    value = float(current_brier) - float(reference_brier)
    return DriftMetric(
        name="calibration_brier_deterioration",
        value=value,
        threshold=threshold,
        alert=bool(math.isfinite(value) and value > threshold),
    )


def relationship_regime_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    feature_columns: tuple[str, ...],
    *,
    threshold: float = 1.5,
) -> DriftMetric:
    relationship_columns = tuple(
        column
        for column in feature_columns
        if column.startswith("relationship_")
        or column.startswith("market_regime_")
        or column.startswith("regime_conditioned_")
    )
    if not relationship_columns:
        return DriftMetric(
            name="relationship_regime_mean_abs_z",
            value=math.nan,
            threshold=threshold,
            alert=False,
        )
    return DriftMetric(
        name="relationship_regime_mean_abs_z",
        value=feature_distribution_drift(
            reference,
            current,
            relationship_columns,
            threshold=threshold,
        ).value,
        threshold=threshold,
        alert=False,
    )


def build_drift_report(
    *,
    model_id: str,
    as_of_date: str,
    reference_features: pd.DataFrame,
    current_features: pd.DataFrame,
    feature_columns: tuple[str, ...],
    reference_probabilities: pd.Series | np.ndarray | None = None,
    current_probabilities: pd.Series | np.ndarray | None = None,
    reference_returns: pd.Series | np.ndarray | None = None,
    current_returns: pd.Series | np.ndarray | None = None,
    reference_brier: float | None = None,
    current_brier: float | None = None,
) -> DriftReport:
    metrics = [feature_distribution_drift(reference_features, current_features, feature_columns)]
    relationship_metric = relationship_regime_drift(
        reference_features,
        current_features,
        feature_columns,
    )
    if math.isfinite(relationship_metric.value):
        metrics.append(
            DriftMetric(
                name=relationship_metric.name,
                value=relationship_metric.value,
                threshold=relationship_metric.threshold,
                alert=relationship_metric.value > relationship_metric.threshold,
            )
        )
    if reference_probabilities is not None and current_probabilities is not None:
        metrics.append(
            prediction_distribution_drift(reference_probabilities, current_probabilities)
        )
    if reference_returns is not None and current_returns is not None:
        metrics.append(realized_performance_drift(reference_returns, current_returns))
    if reference_brier is not None and current_brier is not None:
        metrics.append(calibration_drift(reference_brier, current_brier))
    return DriftReport(model_id=model_id, as_of_date=as_of_date, metrics=tuple(metrics))
