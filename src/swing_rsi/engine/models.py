from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.feature_selection import mutual_info_classif
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, Ridge, TweedieRegressor
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from swing_rsi.engine.calibration_governance import (
    TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION,
    binary_probability_quality,
    build_probability_audit_frame,
    calibration_threshold_utility,
    probability_distribution_summary,
    select_tbs_calibrator,
    write_calibration_audit_artifacts,
)
from swing_rsi.engine.feature_screen import (
    FEATURE_SCREEN_SCHEMA_VERSION,
    PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
    FeatureScreenResult,
    screen_features_for_target,
)
from swing_rsi.engine.features import numeric_feature_columns, reject_label_columns
from swing_rsi.engine.gates import (
    DEVELOPMENT_HOLDOUT_STATUS,
    FINAL_HOLDOUT_PROMOTION_GATE_ID,
    FINAL_HOLDOUT_STATUS,
    GATE_VALUE_NOT_AVAILABLE,
    GATE_VALUE_POSITIVE_INFINITY,
    GateResult,
    GateStatus,
    compare_gate_values,
    configuration_hash,
    make_gate,
    profit_factor_result,
    promotion_eligibility,
    quality_gate_bool_map,
    temporal_fold_stability_result,
    threshold_reason,
)
from swing_rsi.engine.manifest import current_commit_hash
from swing_rsi.engine.ood import (
    PREDICTION_OOD_GOVERNANCE_VERSION,
    REGRESSION_HEADS,
    bundle_ood_identity,
    live_ood_check,
    probability_contract_metrics,
    regression_head_ood_metrics,
)
from swing_rsi.engine.portfolio import PortfolioBacktestConfig, backtest_scanner_candidates
from swing_rsi.engine.registry import ModelState, RegisteredModel, make_model_id, register_model
from swing_rsi.engine.selection import (
    SelectionPolicy,
    evaluate_candidate_policy,
    select_policy_cap_indexes,
)
from swing_rsi.engine.splits import (
    ChronologicalSplit,
    chronological_train_calibration_holdout_split,
)

TEMPORAL_FOLD_STABILITY_SCHEMA_VERSION = "temporal_fold_stability_v1"
TEMPORAL_FOLD_STABILITY_REQUESTED_FOLDS = 3
TEMPORAL_FOLD_STABILITY_THRESHOLD = 0.50
PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION = "path_metric_magnitude_domain_v1"
PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION = "path_metric_magnitude_sign_mapping_v1"
PATH_TARGET_NORMALIZATION_SCHEMA_VERSION = "atr_normalized_path_targets_v1"
PATH_TARGET_ATR_FEATURE = "atr_pct_14"
PATH_TARGET_PREDICTION_MAPPING_VERSION = "atr_units_to_decimal_return_v1"
LINEAR_PATH_HEAD_RETIREMENT_SCHEMA_VERSION = "linear_family_path_head_retirement_v1"
PATH_HEAD_CAPABILITY_ACTIVE = "ACTIVE"
PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR = "RETIRED_UNSUITABLE_ESTIMATOR"
LINEAR_PATH_HEAD_RETIREMENT_REASON = "linear_family_path_head_retired_unsuitable_estimator"
LINEAR_PATH_HEAD_RETIREMENT_FAMILIES = frozenset({"logistic_regression"})


@dataclass(frozen=True)
class ModelBundle:
    model_id: str
    direction: str
    horizon: int
    family: str
    feature_columns: tuple[str, ...]
    feature_family_by_column: dict[str, str]
    classifier: Any
    calibrator: Any
    target_before_stop_model: Any
    target_before_stop_calibrator: Any
    return_model: Any
    mfe_model: Any
    mae_model: Any
    training_medians: dict[str, float]
    training_means: dict[str, float]
    training_stds: dict[str, float]
    training_matrix: pd.DataFrame
    training_labels: pd.DataFrame
    metrics: dict[str, float | int | str | bool | None]
    calibration_metrics: dict[str, float | int | str | bool | None]
    gate_results: tuple[GateResult, ...] = ()
    head_feature_columns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    head_feature_manifests: dict[str, str] = field(default_factory=dict)
    feature_screen_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    feature_screen_records: dict[str, tuple[dict[str, object], ...]] = field(default_factory=dict)
    path_domain_metadata: dict[str, dict[str, object]] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveryConfig:
    horizons: tuple[int, ...] = (10,)
    directions: tuple[str, ...] = ("bull", "bear")
    minimum_training_samples: int = 200
    minimum_holdout_samples: int = 80
    max_features: int = 80
    correlation_threshold: float = 0.97
    probability_threshold: float = 0.55
    round_trip_cost_bps: float = 5.0
    slippage_bps: float = 2.0
    random_seed: int = 42
    permutation_feature_limit: int = 12
    mutual_information_top_k: int = 60
    research_start: str | None = "2016-06-20"
    research_end: str | None = None
    max_concurrent_positions: int = 5
    max_position_per_symbol: int = 1
    max_sector_fraction: float = 0.5
    max_gross_exposure: float = 1.0
    max_net_exposure: float = 1.0
    expected_return_threshold: float | None = 0.001
    target_before_stop_threshold: float | None = 0.50
    selection_top_n_limit: int | None = 5_000
    selection_per_date_limit: int | None = 5
    selection_minimum_dollar_volume: float | None = 5_000_000.0
    selection_rate_max: float | None = 0.20


PRIMARY_HEAD = "primary_positive_return"
TARGET_BEFORE_STOP_HEAD = "target_before_stop"
EXPECTED_RETURN_HEAD = "expected_return"
MFE_HEAD = "mfe"
MAE_HEAD = "mae"
PATH_METRIC_HEADS = (EXPECTED_RETURN_HEAD, MFE_HEAD, MAE_HEAD)
PATH_MAGNITUDE_HEADS = (MFE_HEAD, MAE_HEAD)
PATH_HEAD_TO_METRIC_PREFIX = {
    EXPECTED_RETURN_HEAD: "return",
    MFE_HEAD: "mfe",
    MAE_HEAD: "mae",
}
PATH_HEAD_TARGET_METRIC_KEYS = {
    EXPECTED_RETURN_HEAD: "expected_return",
    MFE_HEAD: "mfe",
    MAE_HEAD: "mae",
}
PATH_HEAD_OUTPUT_COLUMNS = {
    EXPECTED_RETURN_HEAD: "expected_return",
    MFE_HEAD: "expected_mfe",
    MAE_HEAD: "expected_mae",
}


@dataclass(frozen=True)
class PathMagnitudeEstimatorSpec:
    family: str
    head_name: str
    estimator_class: str
    loss: str
    hyperparameters: dict[str, object]
    schema_version: str = PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
    prediction_mapping_version: str = PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION

    @property
    def configuration_hash(self) -> str:
        return configuration_hash(asdict(self))


@dataclass(frozen=True)
class PathMagnitudePrediction:
    internal_magnitude: pd.Series
    canonical_signed: pd.Series
    nonfinite_count: int
    magnitude_domain_violation_count: int
    signed_domain_violation_count: int

    @property
    def valid(self) -> bool:
        return (
            self.nonfinite_count == 0
            and self.magnitude_domain_violation_count == 0
            and self.signed_domain_violation_count == 0
        )

    def diagnostics(self, prefix: str) -> dict[str, float | int | bool]:
        magnitude = pd.to_numeric(self.internal_magnitude, errors="coerce")
        signed = pd.to_numeric(self.canonical_signed, errors="coerce")
        return {
            f"{prefix}_internal_magnitude_prediction_min": _series_min(magnitude),
            f"{prefix}_internal_magnitude_prediction_max": _series_max(magnitude),
            f"{prefix}_internal_magnitude_atr_unit_prediction_min": _series_min(magnitude),
            f"{prefix}_internal_magnitude_atr_unit_prediction_max": _series_max(magnitude),
            f"{prefix}_canonical_prediction_min": _series_min(signed),
            f"{prefix}_canonical_prediction_max": _series_max(signed),
            f"{prefix}_prediction_nonfinite_count": self.nonfinite_count,
            f"{prefix}_magnitude_domain_violation_count": (self.magnitude_domain_violation_count),
            f"{prefix}_signed_domain_violation_count": self.signed_domain_violation_count,
            f"{prefix}_domain_integrity_valid": self.valid,
        }


@dataclass(frozen=True)
class PathTargetPrediction:
    internal_atr_units: pd.Series
    canonical_external: pd.Series
    atr_values: pd.Series
    nonfinite_count: int

    @property
    def valid(self) -> bool:
        return self.nonfinite_count == 0

    def diagnostics(self, prefix: str) -> dict[str, float | int | bool]:
        internal = pd.to_numeric(self.internal_atr_units, errors="coerce")
        canonical = pd.to_numeric(self.canonical_external, errors="coerce")
        return {
            f"{prefix}_internal_atr_unit_prediction_min": _series_min(internal),
            f"{prefix}_internal_atr_unit_prediction_max": _series_max(internal),
            f"{prefix}_canonical_prediction_min": _series_min(canonical),
            f"{prefix}_canonical_prediction_max": _series_max(canonical),
            f"{prefix}_prediction_nonfinite_count": self.nonfinite_count,
            f"{prefix}_domain_integrity_valid": self.valid,
        }


def _series_min(values: pd.Series) -> float:
    finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return float(finite.min()) if not finite.empty else math.nan


def _series_max(values: pd.Series) -> float:
    finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return float(finite.max()) if not finite.empty else math.nan


def bundle_head_feature_columns(bundle: ModelBundle, head: str) -> tuple[str, ...]:
    head_columns = getattr(bundle, "head_feature_columns", {}) or {}
    columns = head_columns.get(head)
    if columns:
        return tuple(str(column) for column in columns)
    return tuple(bundle.feature_columns)


def bundle_head_feature_manifest(bundle: ModelBundle, head: str) -> str:
    manifests = getattr(bundle, "head_feature_manifests", {}) or {}
    value = manifests.get(head)
    if value:
        return str(value)
    if head in PATH_METRIC_HEADS:
        return "legacy_shared_path_feature_screen"
    return "legacy_shared_feature_screen"


def bundle_feature_screen_metadata(bundle: ModelBundle, head: str) -> dict[str, object]:
    metadata = getattr(bundle, "feature_screen_metadata", {}) or {}
    value = metadata.get(head)
    return dict(value) if isinstance(value, dict) else {}


def bundle_feature_screen_records(bundle: ModelBundle, head: str) -> tuple[dict[str, object], ...]:
    records = getattr(bundle, "feature_screen_records", {}) or {}
    value = records.get(head)
    if not value:
        return ()
    return tuple(dict(record) for record in value if isinstance(record, dict))


def bundle_path_domain_metadata(bundle: ModelBundle, head: str) -> dict[str, object]:
    metadata = getattr(bundle, "path_domain_metadata", {}) or {}
    value = metadata.get(head)
    return dict(value) if isinstance(value, dict) else {}


def _target_normalization_metadata_from_screen(
    metadata: dict[str, object],
) -> dict[str, object]:
    if str(metadata.get("target_normalization_schema_version") or "") != (
        PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
    ):
        return {}
    return {
        "target_normalization_schema_version": str(
            metadata.get("target_normalization_schema_version") or ""
        ),
        "target_normalization_method": str(metadata.get("target_normalization_method") or ""),
        "atr_feature_name": str(metadata.get("atr_feature_name") or ""),
        "external_target_name": str(metadata.get("external_target_name") or ""),
        "internal_target_name": str(metadata.get("internal_target_name") or ""),
        "internal_target_unit": str(metadata.get("internal_target_unit") or ""),
        "canonical_external_unit": str(metadata.get("canonical_external_unit") or ""),
        "prediction_mapping_version": str(metadata.get("prediction_mapping_version") or ""),
        "target_normalization_hash": str(metadata.get("target_normalization_hash") or ""),
    }


def _target_normalization_metadata_for_bundle(bundle: ModelBundle, head: str) -> dict[str, object]:
    screen_metadata = _target_normalization_metadata_from_screen(
        bundle_feature_screen_metadata(bundle, head)
    )
    if screen_metadata:
        return screen_metadata
    domain_metadata = bundle_path_domain_metadata(bundle, head)
    target_normalization = domain_metadata.get("target_normalization")
    if isinstance(target_normalization, dict):
        return _target_normalization_metadata_from_screen(target_normalization)
    return _target_normalization_metadata_from_screen(domain_metadata)


def path_head_capability_state(bundle: ModelBundle, head: str) -> str:
    metadata = bundle_path_domain_metadata(bundle, head)
    state = str(metadata.get("path_head_capability_state") or "")
    if state:
        return state
    if str(metadata.get("domain_schema_version") or "") == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION:
        return PATH_HEAD_CAPABILITY_ACTIVE
    return "UNKNOWN"


def path_head_is_retired(bundle: ModelBundle, head: str) -> bool:
    return (
        path_head_capability_state(bundle, head)
        == PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
    )


def bundle_tbs_calibration_metadata(bundle: ModelBundle) -> dict[str, object]:
    metrics = getattr(bundle, "metrics", {}) or {}
    schema = metrics.get("target_before_stop_calibration_governance_schema")
    if not schema:
        return {}
    return {
        "schema_version": str(schema),
        "method": str(metrics.get("target_before_stop_calibration_method") or ""),
        "calibration_manifest_hash": str(
            metrics.get("target_before_stop_calibration_manifest_hash") or ""
        ),
        "calibrator_artifact_hash": str(
            metrics.get("target_before_stop_calibrator_artifact_hash") or ""
        ),
        "selection_reason": str(
            metrics.get("target_before_stop_calibration_selection_reason") or ""
        ),
    }


def selection_policy_from_config(config: DiscoveryConfig) -> SelectionPolicy:
    return SelectionPolicy(
        probability_threshold=config.probability_threshold,
        expected_return_threshold=config.expected_return_threshold,
        target_before_stop_threshold=config.target_before_stop_threshold,
        top_n_limit=config.selection_top_n_limit,
        per_date_limit=config.selection_per_date_limit,
        liquidity_threshold=config.selection_minimum_dollar_volume,
        selected_rate_ceiling=config.selection_rate_max,
    )


def _apply_selection_policy(
    holdout: pd.DataFrame,
    *,
    probability: np.ndarray,
    expected_return: pd.Series,
    target_before_stop_probability: np.ndarray,
    policy: SelectionPolicy,
) -> np.ndarray:
    candidates = pd.DataFrame(
        {
            "Date": pd.to_datetime(holdout["Date"]),
            "symbol": holdout["symbol"].astype(str),
            "calibrated_probability": np.asarray(probability, dtype=float),
            "expected_return": expected_return.to_numpy(dtype=float),
            "target_before_stop_probability": np.asarray(
                target_before_stop_probability, dtype=float
            ),
        },
        index=holdout.index,
    )
    if "dollar_volume" in holdout.columns:
        candidates["dollar_volume"] = holdout["dollar_volume"]
    candidates["composite_utility_score"] = (
        candidates["calibrated_probability"] * candidates["expected_return"]
    )

    mask = candidates.apply(
        lambda row: evaluate_candidate_policy(row.to_dict(), policy).passed,
        axis=1,
    )
    eligible = candidates.loc[mask].copy()
    selected_index = select_policy_cap_indexes(eligible, policy, date_column="Date")
    return np.asarray([index in selected_index for index in holdout.index], dtype=bool)


@dataclass(frozen=True)
class DiscoveryResult:
    registered_models: tuple[RegisteredModel, ...]
    rejected_models: tuple[RegisteredModel, ...]
    best_challenger_id: str | None


@dataclass(frozen=True)
class ModelPlugin:
    name: str
    classifier_factory: Callable[[int], Any]
    regressor_factory: Callable[[int], Any]
    nonlinear_interactions: bool


class BaseRateClassifier(ClassifierMixin, BaseEstimator):  # type: ignore[misc]
    """Naive historical base-rate classifier used as a discovery baseline."""

    def __init__(self) -> None:
        self.probability = 0.5
        self.classes_ = np.array([0, 1])
        self.is_fitted_ = False

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> BaseRateClassifier:
        _ = frame
        mean_probability = float(pd.to_numeric(target, errors="coerce").mean())
        self.probability = float(np.clip(mean_probability, 0.001, 0.999))
        self.classes_ = np.array([0, 1])
        self.is_fitted_ = True
        return self

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        positive = np.full(len(frame), self.probability, dtype=float)
        negative = 1.0 - positive
        return np.column_stack([negative, positive])


class MeanMagnitudeRegressor(RegressorMixin, BaseEstimator):  # type: ignore[misc]
    """Naive nonnegative magnitude regressor for path-metric controls."""

    def __init__(self) -> None:
        self.mean_ = 0.0
        self.is_fitted_ = False

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> MeanMagnitudeRegressor:
        _ = frame
        numeric = pd.to_numeric(target, errors="coerce").replace([np.inf, -np.inf], np.nan)
        if numeric.isna().any() or bool((numeric.dropna() < 0.0).any()):
            raise ValueError("MeanMagnitudeRegressor requires finite nonnegative targets")
        self.mean_ = float(numeric.mean())
        self.is_fitted_ = True
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.full(len(frame), self.mean_, dtype=float)


class RetiredPathHeadModel(RegressorMixin, BaseEstimator):  # type: ignore[misc]
    """Explicit placeholder for a required path head retired before estimator fitting."""

    def __init__(
        self,
        *,
        family: str,
        head_name: str,
        reason: str = LINEAR_PATH_HEAD_RETIREMENT_REASON,
    ) -> None:
        self.family = family
        self.head_name = head_name
        self.reason = reason
        self.capability_state = PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
        self.schema_version = LINEAR_PATH_HEAD_RETIREMENT_SCHEMA_VERSION

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> RetiredPathHeadModel:
        _ = (frame, target)
        raise RuntimeError(self.reason)

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        _ = frame
        raise RuntimeError(self.reason)


def _model_step(model: Any) -> Any:
    if isinstance(model, Pipeline):
        return model.steps[-1][1]
    return model


def _estimator_class_name(model: Any) -> str:
    return type(_model_step(model)).__name__


def _estimator_loss(model: Any) -> str:
    step = _model_step(model)
    loss = getattr(step, "loss", None)
    if loss is not None:
        return str(loss)
    if isinstance(step, TweedieRegressor):
        return f"tweedie_power_{step.power:g}_link_{step.link}"
    if isinstance(step, ExtraTreesRegressor):
        return "squared_error_leaf_average"
    if isinstance(step, MeanMagnitudeRegressor):
        return "training_mean_magnitude"
    return "unknown"


def _simple_estimator_params(model: Any) -> dict[str, object]:
    step = _model_step(model)
    keys = (
        "alpha",
        "fit_intercept",
        "link",
        "power",
        "max_iter",
        "tol",
        "loss",
        "learning_rate",
        "min_samples_leaf",
        "l2_regularization",
        "random_state",
        "n_estimators",
        "n_jobs",
    )
    params: dict[str, object] = {}
    for key in keys:
        if hasattr(step, key):
            value = getattr(step, key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                params[key] = value
    return params


def _pipeline_preprocessing_hash(model: Any) -> str:
    if not isinstance(model, Pipeline):
        return configuration_hash({"preprocessing": "none"})
    steps: list[dict[str, object]] = []
    for name, step in model.steps[:-1]:
        fitted_attrs: dict[str, object] = {}
        for attr in ("statistics_", "mean_", "scale_", "var_"):
            if hasattr(step, attr):
                value = getattr(step, attr)
                if isinstance(value, np.ndarray):
                    fitted_attrs[attr] = np.asarray(value, dtype=float).round(12).tolist()
        steps.append(
            {
                "name": name,
                "class": type(step).__name__,
                "params": {
                    key: value
                    for key, value in getattr(step, "get_params", lambda: {})().items()
                    if isinstance(value, (str, int, float, bool)) or value is None
                },
                "fitted_attrs": fitted_attrs,
            }
        )
    return configuration_hash(
        {
            "steps": steps,
        }
    )


def _estimator_hash(model: Any) -> str:
    step = _model_step(model)
    payload: dict[str, object] = {
        "class": type(step).__name__,
        "params": _simple_estimator_params(model),
        "fitted_object_hash": joblib.hash(model),
    }
    for attr in ("n_iter_", "train_score_", "mean_"):
        if hasattr(step, attr):
            value = getattr(step, attr)
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[attr] = value
            elif isinstance(value, np.ndarray):
                payload[attr] = np.asarray(value, dtype=float).round(12).tolist()[:10]
    return configuration_hash(payload)


def _convergence_diagnostics(model: Any) -> dict[str, object]:
    step = _model_step(model)
    diagnostics: dict[str, object] = {
        "estimator_class": type(step).__name__,
        "converged": True,
    }
    if hasattr(step, "n_iter_"):
        n_iter = int(step.n_iter_)
        diagnostics["n_iter"] = n_iter
        max_iter = getattr(step, "max_iter", None)
        if isinstance(max_iter, int):
            diagnostics["max_iter"] = max_iter
            diagnostics["converged"] = n_iter < max_iter
    return diagnostics


def build_path_magnitude_estimator(
    *,
    family: str,
    head_name: str,
    seed: int,
) -> tuple[Pipeline, PathMagnitudeEstimatorSpec]:
    if family in LINEAR_PATH_HEAD_RETIREMENT_FAMILIES and head_name in PATH_MAGNITUDE_HEADS:
        raise ValueError(LINEAR_PATH_HEAD_RETIREMENT_REASON)
    if family == "naive_base_rate":
        estimator = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", MeanMagnitudeRegressor()),
            ]
        )
    elif family == "hist_gradient_boosting":
        estimator = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        loss="poisson",
                        max_iter=80,
                        learning_rate=0.05,
                        min_samples_leaf=20,
                        l2_regularization=0.1,
                        random_state=seed,
                    ),
                ),
            ]
        )
    elif family == "extra_trees":
        estimator = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=120,
                        min_samples_leaf=10,
                        random_state=seed,
                        n_jobs=1,
                    ),
                ),
            ]
        )
    else:
        estimator = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    TweedieRegressor(
                        power=1.5,
                        link="log",
                        alpha=1.0,
                        max_iter=1000,
                        tol=1e-6,
                    ),
                ),
            ]
        )
    spec = PathMagnitudeEstimatorSpec(
        family=family,
        head_name=head_name,
        estimator_class=_estimator_class_name(estimator),
        loss=_estimator_loss(estimator),
        hyperparameters=_simple_estimator_params(estimator),
    )
    return estimator, spec


def _clean_feature_columns(
    frame: pd.DataFrame, *, max_features: int, correlation_threshold: float
) -> list[str]:
    columns = numeric_feature_columns(frame)
    reject_label_columns(columns)
    data = frame[columns]
    missingness = data.isna().mean()
    columns = [column for column in columns if missingness[column] <= 0.4]
    variances = data[columns].var(numeric_only=True)
    columns = [
        column
        for column in columns
        if math.isfinite(float(variances[column])) and float(variances[column]) > 1e-12
    ]
    if not columns:
        raise ValueError("No usable numeric feature columns after filtering")
    corr = data[columns].corr(numeric_only=True).abs()
    selected: list[str] = []
    for column in columns:
        if len(selected) >= max_features:
            break
        if not selected:
            selected.append(column)
            continue
        correlation_row = cast(pd.Series, corr.loc[column])
        existing_corr = pd.to_numeric(correlation_row.reindex(selected), errors="coerce").to_numpy(
            dtype=float
        )
        if bool(np.all(existing_corr < correlation_threshold)):
            selected.append(column)
    return selected


def model_plugins() -> tuple[ModelPlugin, ...]:
    return (
        ModelPlugin(
            name="naive_base_rate",
            classifier_factory=lambda _seed: Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", BaseRateClassifier()),
                ]
            ),
            regressor_factory=lambda seed: _regressor(seed, "naive_base_rate"),
            nonlinear_interactions=False,
        ),
        ModelPlugin(
            name="logistic_regression",
            classifier_factory=lambda seed: Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            max_iter=500, class_weight="balanced", random_state=seed
                        ),
                    ),
                ]
            ),
            regressor_factory=lambda seed: _regressor(seed, "logistic_regression"),
            nonlinear_interactions=False,
        ),
        ModelPlugin(
            name="hist_gradient_boosting",
            classifier_factory=lambda seed: Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        HistGradientBoostingClassifier(
                            max_iter=80,
                            learning_rate=0.05,
                            min_samples_leaf=20,
                            l2_regularization=0.1,
                            random_state=seed,
                        ),
                    ),
                ]
            ),
            regressor_factory=lambda seed: _regressor(seed, "hist_gradient_boosting"),
            nonlinear_interactions=True,
        ),
        ModelPlugin(
            name="extra_trees",
            classifier_factory=lambda seed: Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        ExtraTreesClassifier(
                            n_estimators=120,
                            min_samples_leaf=10,
                            class_weight="balanced",
                            random_state=seed,
                            n_jobs=1,
                        ),
                    ),
                ]
            ),
            regressor_factory=lambda seed: _regressor(seed, "extra_trees"),
            nonlinear_interactions=True,
        ),
    )


def _candidate_pipelines(seed: int) -> dict[str, Any]:
    return {plugin.name: plugin.classifier_factory(seed) for plugin in model_plugins()}


def _regressor(seed: int, family: str) -> Pipeline:
    if family == "hist_gradient_boosting":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=80,
                        learning_rate=0.05,
                        min_samples_leaf=20,
                        l2_regularization=0.1,
                        random_state=seed,
                    ),
                ),
            ]
        )
    if family == "extra_trees":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=120,
                        min_samples_leaf=10,
                        random_state=seed,
                        n_jobs=1,
                    ),
                ),
            ]
        )
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=2.0)),
        ]
    )


def _positive_class_probability(model: Any, features: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)
        return np.asarray(probabilities[:, 1], dtype=float)
    scores = np.asarray(model.decision_function(features), dtype=float)
    return np.asarray(1.0 / (1.0 + np.exp(-scores)), dtype=float)


def _profit_factor_components(returns: pd.Series) -> tuple[int, float, float, int]:
    numeric = pd.to_numeric(returns, errors="coerce").dropna()
    selected_count = len(numeric)
    gains = float(numeric[numeric > 0.0].sum())
    loss_abs = float(abs(numeric[numeric < 0.0].sum()))
    zero_count = int((numeric == 0.0).sum())
    return selected_count, gains, loss_abs, zero_count


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return math.nan
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    return float(((equity / equity.cummax()) - 1.0).min())


def _json_dumps(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _date_label(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).date().isoformat()


def _research_end(frame: pd.DataFrame, config: DiscoveryConfig) -> str:
    if config.research_end:
        return config.research_end
    return pd.Timestamp(frame["Date"].max()).date().isoformat()


def eligible_modeling_frame(frame: pd.DataFrame, config: DiscoveryConfig) -> pd.DataFrame:
    data = frame.copy()
    date_values = pd.to_datetime(data["Date"])
    if config.research_start is not None:
        data = data.loc[date_values >= pd.Timestamp(config.research_start)].copy()
        date_values = pd.to_datetime(data["Date"])
    research_end = pd.Timestamp(_research_end(frame, config))
    data = data.loc[date_values <= research_end].copy()
    label_end_columns = [
        column for column in data.columns if str(column).startswith("label_end_date_")
    ]
    for column in label_end_columns:
        data = data.loc[pd.to_datetime(data[column]) <= research_end].copy()
    return data.sort_values(["Date", "symbol"]).reset_index(drop=True)


def _portfolio_frames_from_modeling(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    required = ["Open", "High", "Low", "Close", "Volume"]
    frames: dict[str, pd.DataFrame] = {}
    for symbol, group in frame.groupby("symbol"):
        data = group[["Date", *required]].copy()
        data["Date"] = pd.to_datetime(data["Date"])
        frames[str(symbol)] = data.set_index("Date").sort_index()
    return frames


def _calibration_table(
    y_true: pd.Series,
    probability: np.ndarray,
    *,
    bins: int = 10,
) -> list[dict[str, float | int]]:
    data = pd.DataFrame({"actual": y_true.astype(float), "probability": probability}).dropna()
    if data.empty:
        return []
    data["decile"] = pd.qcut(
        data["probability"].rank(method="first"),
        q=min(bins, len(data)),
        labels=False,
        duplicates="drop",
    )
    grouped = data.groupby("decile", dropna=True)
    return [
        {
            "decile": index,
            "count": len(group),
            "predicted_probability": float(group["probability"].mean()),
            "realized_rate": float(group["actual"].mean()),
            "absolute_error": abs(
                float(group["probability"].mean()) - float(group["actual"].mean())
            ),
        }
        for index, (_, group) in enumerate(grouped, start=1)
    ]


def _expected_calibration_error(table: list[dict[str, float | int]], total: int) -> float:
    if total <= 0 or not table:
        return math.nan
    return float(sum((int(row["count"]) / total) * float(row["absolute_error"]) for row in table))


def _calibration_intercept_slope(y_true: pd.Series, probability: np.ndarray) -> tuple[float, float]:
    data = pd.DataFrame({"actual": y_true.astype(int), "probability": probability}).dropna()
    if data.empty or data["actual"].nunique() < 2:
        return math.nan, math.nan
    clipped = np.clip(data["probability"].to_numpy(dtype=float), 1e-6, 1.0 - 1e-6)
    logits = np.log(clipped / (1.0 - clipped))
    model = LogisticRegression(C=1_000_000.0, solver="lbfgs")
    model.fit(logits.reshape(-1, 1), data["actual"].to_numpy(dtype=int))
    return float(model.intercept_[0]), float(model.coef_[0][0])


def _prediction_deciles(
    realized: pd.Series,
    prediction: pd.Series,
) -> list[dict[str, float | int]]:
    data = pd.DataFrame({"realized": realized.astype(float), "prediction": prediction}).dropna()
    if data.empty:
        return []
    data["decile"] = pd.qcut(
        data["prediction"].rank(method="first"),
        q=min(10, len(data)),
        labels=False,
        duplicates="drop",
    )
    return [
        {
            "decile": index,
            "count": len(group),
            "predicted_mean": float(group["prediction"].mean()),
            "realized_mean": float(group["realized"].mean()),
        }
        for index, (_, group) in enumerate(data.groupby("decile", dropna=True), start=1)
    ]


def _quantile_metrics(prefix: str, values: pd.Series) -> dict[str, float]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {
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


def _prediction_sanity_metrics(
    *,
    name: str,
    train_target: pd.Series,
    calibration_target: pd.Series | None = None,
    holdout_target: pd.Series,
    calibration_prediction: pd.Series | None = None,
    holdout_prediction: pd.Series,
    direction: str = "unknown",
    horizon: int = 0,
) -> dict[str, float | int | str | bool]:
    calibration_target = calibration_target if calibration_target is not None else train_target
    calibration_prediction = (
        calibration_prediction if calibration_prediction is not None else holdout_prediction.head(0)
    )
    return regression_head_ood_metrics(
        name=name,
        direction=direction,
        horizon=horizon,
        train_target=train_target,
        calibration_target=calibration_target,
        holdout_target=holdout_target,
        calibration_prediction=calibration_prediction,
        holdout_prediction=holdout_prediction,
    )


def _mean_absolute_error_or_nan(target: pd.Series, prediction: pd.Series) -> float:
    target_values = pd.to_numeric(target, errors="coerce").to_numpy(dtype=float)
    prediction_values = pd.to_numeric(prediction, errors="coerce").to_numpy(dtype=float)
    if len(target_values) != len(prediction_values):
        return math.nan
    mask = np.isfinite(target_values) & np.isfinite(prediction_values)
    if not mask.all():
        return math.nan
    return float(mean_absolute_error(target_values, prediction_values))


def _rmse_or_nan(target: pd.Series, prediction: pd.Series) -> float:
    target_values = pd.to_numeric(target, errors="coerce").to_numpy(dtype=float)
    prediction_values = pd.to_numeric(prediction, errors="coerce").to_numpy(dtype=float)
    if len(target_values) != len(prediction_values):
        return math.nan
    mask = np.isfinite(target_values) & np.isfinite(prediction_values)
    if not mask.all():
        return math.nan
    return float(mean_squared_error(target_values, prediction_values) ** 0.5)


def _selection_diagnostics(
    *,
    holdout: pd.DataFrame,
    selected: pd.DataFrame,
    horizon: int,
) -> dict[str, float | int | str]:
    if selected.empty:
        return {
            "selected_observation_count": 0,
            "selected_observation_rate": 0.0,
            "selected_trading_dates": 0,
            "average_candidates_per_date": 0.0,
            "candidate_count_p50_per_date": 0.0,
            "candidate_count_p90_per_date": 0.0,
            "candidate_count_p99_per_date": 0.0,
            "maximum_candidates_on_one_date": 0,
            "percent_dates_with_candidate": 0.0,
            "average_holding_overlap": 0.0,
            "maximum_concurrent_candidate_count": 0,
        }
    counts = selected.groupby("Date")["symbol"].size()
    all_dates = pd.to_datetime(holdout["Date"]).nunique()
    date_counts = counts.astype(float)
    event_rows: list[tuple[pd.Timestamp, int]] = []
    for value in pd.to_datetime(selected["Date"]):
        event_rows.append((pd.Timestamp(value), 1))
        event_rows.append((pd.Timestamp(value) + pd.offsets.BDay(horizon), -1))
    current = 0
    max_overlap = 0
    overlap_values: list[int] = []
    for _, change in sorted(event_rows, key=lambda item: (item[0], -item[1])):
        current += change
        max_overlap = max(max_overlap, current)
        overlap_values.append(current)
    return {
        "selected_observation_count": len(selected),
        "selected_observation_rate": float(len(selected) / len(holdout))
        if len(holdout)
        else math.nan,
        "selected_trading_dates": int(counts.size),
        "average_candidates_per_date": float(date_counts.mean()),
        "candidate_count_p50_per_date": float(date_counts.quantile(0.50)),
        "candidate_count_p90_per_date": float(date_counts.quantile(0.90)),
        "candidate_count_p99_per_date": float(date_counts.quantile(0.99)),
        "maximum_candidates_on_one_date": int(counts.max()),
        "percent_dates_with_candidate": float(counts.size / all_dates) if all_dates else math.nan,
        "average_holding_overlap": float(np.mean(overlap_values)) if overlap_values else 0.0,
        "maximum_concurrent_candidate_count": int(max_overlap),
    }


def _candidate_rows_for_portfolio(
    *,
    holdout: pd.DataFrame,
    selected_mask: np.ndarray,
    direction: str,
    horizon: int,
    model_id: str,
    probability: np.ndarray,
    expected_return: pd.Series,
    target_before_stop_probability: np.ndarray,
) -> pd.DataFrame:
    rows = holdout[["Date", "symbol", "sector", "market_regime_label"]].copy()
    rows["as_of_date"] = pd.to_datetime(rows["Date"]).dt.date.astype(str)
    rows["ticker"] = rows["symbol"]
    rows["direction"] = "Bullish" if direction == "bull" else "Bearish"
    rows["horizon"] = horizon
    rows["model_id"] = model_id
    rows["calibrated_probability"] = probability
    rows["expected_return"] = expected_return.to_numpy(dtype=float)
    rows["target_before_stop_probability"] = target_before_stop_probability
    rows["composite_utility_score"] = rows["calibrated_probability"] * rows["expected_return"]
    rows["regime"] = rows["market_regime_label"]
    rows["candidate_status"] = np.where(selected_mask, "ACTIONABLE_PAPER_CANDIDATE", "REJECTED")
    rows["exclusion_reason"] = np.where(
        selected_mask,
        "",
        "below_frozen_selection_policy",
    )
    return rows[
        [
            "as_of_date",
            "ticker",
            "direction",
            "horizon",
            "model_id",
            "sector",
            "regime",
            "calibrated_probability",
            "expected_return",
            "target_before_stop_probability",
            "composite_utility_score",
            "candidate_status",
            "exclusion_reason",
        ]
    ]


def _permutation_importance_summary(
    *,
    classifier: Any,
    calibrator: Any,
    holdout: pd.DataFrame,
    feature_columns: list[str],
    target: str,
    baseline_brier: float,
    seed: int,
    limit: int,
) -> str:
    rng = np.random.default_rng(seed)
    importances: list[tuple[str, float]] = []
    selected_columns = feature_columns[: max(0, min(limit, len(feature_columns)))]
    for column in selected_columns:
        permuted = holdout[feature_columns].copy()
        values = permuted[column].to_numpy(copy=True)
        rng.shuffle(values)
        permuted[column] = values
        raw = _positive_class_probability(classifier, permuted)
        probability = np.asarray(calibrator.predict(raw), dtype=float)
        brier = float(brier_score_loss(holdout[target].astype(int), probability))
        delta = brier - baseline_brier
        if math.isfinite(delta):
            importances.append((column, delta))
    top = sorted(importances, key=lambda item: item[1], reverse=True)[:8]
    return "; ".join(f"{column}={value:.6f}" for column, value in top)


def _permutation_importance_by_family(
    *,
    classifier: Any,
    calibrator: Any,
    holdout: pd.DataFrame,
    feature_columns: tuple[str, ...],
    feature_family_by_column: dict[str, str],
    target: str,
    baseline_brier: float,
    seed: int,
) -> list[dict[str, float | int | str]]:
    rng = np.random.default_rng(seed)
    family_records: dict[str, dict[str, float | int | str]] = {}
    for column in feature_columns:
        permuted = holdout[list(feature_columns)].copy()
        values = permuted[column].to_numpy(copy=True)
        rng.shuffle(values)
        permuted[column] = values
        raw = _positive_class_probability(classifier, permuted)
        probability = np.asarray(calibrator.predict(raw), dtype=float)
        delta = float(brier_score_loss(holdout[target].astype(int), probability) - baseline_brier)
        if not math.isfinite(delta):
            continue
        family = feature_family_by_column.get(column, "unknown")
        record = family_records.setdefault(
            family,
            {
                "family": family,
                "features": 0,
                "sum_delta_brier": 0.0,
                "positive_sum_delta_brier": 0.0,
                "top_feature": "",
                "top_delta_brier": -math.inf,
            },
        )
        record["features"] = int(record["features"]) + 1
        record["sum_delta_brier"] = float(record["sum_delta_brier"]) + delta
        record["positive_sum_delta_brier"] = float(record["positive_sum_delta_brier"]) + max(
            0.0, delta
        )
        if delta > float(record["top_delta_brier"]):
            record["top_delta_brier"] = delta
            record["top_feature"] = column
    return sorted(family_records.values(), key=lambda item: str(item["family"]))


def _regression_permutation_importance_by_family(
    *,
    regressor: Any,
    holdout: pd.DataFrame,
    feature_columns: tuple[str, ...],
    feature_family_by_column: dict[str, str],
    target: str,
    baseline_mae: float,
    seed: int,
    prediction_sign: float = 1.0,
    prediction_scale: pd.Series | None = None,
) -> list[dict[str, float | int | str]]:
    rng = np.random.default_rng(seed)
    family_records: dict[str, dict[str, float | int | str]] = {}
    if not feature_columns or not math.isfinite(baseline_mae):
        return []
    for column in feature_columns:
        permuted = holdout[list(feature_columns)].copy()
        values = permuted[column].to_numpy(copy=True)
        rng.shuffle(values)
        permuted[column] = values
        raw_prediction = pd.Series(
            np.asarray(regressor.predict(permuted), dtype=float), index=holdout.index
        )
        if prediction_scale is not None:
            scale = pd.to_numeric(prediction_scale, errors="coerce").reindex(holdout.index)
            raw_prediction = raw_prediction * scale
        prediction = pd.Series(
            raw_prediction.to_numpy(dtype=float) * prediction_sign, index=holdout.index
        )
        delta = float(mean_absolute_error(holdout[target], prediction) - baseline_mae)
        if not math.isfinite(delta):
            continue
        family = feature_family_by_column.get(column, "unknown")
        record = family_records.setdefault(
            family,
            {
                "family": family,
                "features": 0,
                "sum_delta_mae": 0.0,
                "positive_sum_delta_mae": 0.0,
                "top_feature": "",
                "top_delta_mae": -math.inf,
            },
        )
        record["features"] = int(record["features"]) + 1
        record["sum_delta_mae"] = float(record["sum_delta_mae"]) + delta
        record["positive_sum_delta_mae"] = float(record["positive_sum_delta_mae"]) + max(0.0, delta)
        if delta > float(record["top_delta_mae"]):
            record["top_delta_mae"] = delta
            record["top_feature"] = column
    return sorted(family_records.values(), key=lambda item: str(item["family"]))


def _screen_top_features(
    screen: FeatureScreenResult,
    *,
    limit: int = 25,
) -> list[dict[str, object]]:
    rows = [
        record.to_jsonable()
        for record in screen.records
        if record.mutual_information_score is not None
    ]
    rows = sorted(
        rows,
        key=lambda record: (
            -float(cast(float | int, record["mutual_information_score"] or 0.0)),
            str(record["feature"]),
        ),
    )
    return rows[:limit]


def _feature_stability_summary(
    train: pd.DataFrame,
    holdout: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[float, str]:
    scores: list[tuple[str, float]] = []
    for column in feature_columns:
        train_values = pd.to_numeric(train[column], errors="coerce")
        holdout_values = pd.to_numeric(holdout[column], errors="coerce")
        train_std = float(train_values.std(ddof=0))
        if not math.isfinite(train_std) or train_std <= 1e-12:
            continue
        score = abs(float(holdout_values.mean()) - float(train_values.mean())) / train_std
        if math.isfinite(score):
            scores.append((column, score))
    if not scores:
        return math.nan, ""
    top = sorted(scores, key=lambda item: item[1], reverse=True)[:8]
    mean_score = float(np.mean([score for _, score in scores]))
    return mean_score, "; ".join(f"{column}={score:.4f}" for column, score in top)


def _mutual_information_screen(
    train: pd.DataFrame,
    feature_columns: list[str],
    target: str,
    *,
    seed: int,
    top_k: int,
) -> tuple[list[str], str]:
    if top_k <= 0 or len(feature_columns) <= top_k:
        return feature_columns, ""
    target_values = train[target].astype(int)
    if target_values.nunique() < 2:
        return feature_columns, ""
    x = train[feature_columns].replace([np.inf, -np.inf], np.nan)
    x = x.fillna(x.median(numeric_only=True)).fillna(0.0)
    scores = mutual_info_classif(x, target_values, random_state=seed)
    ranked = sorted(
        zip(feature_columns, scores, strict=True),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    selected = [column for column, _ in ranked[:top_k]]
    summary = "; ".join(f"{column}={float(score):.6f}" for column, score in ranked[:10])
    return selected, summary


def _screen_path_metric_head(
    *,
    training_frame: pd.DataFrame,
    target: pd.Series,
    target_name: str,
    head_name: str,
    direction: str,
    horizon: int,
    feature_family_by_column: dict[str, str],
    config: DiscoveryConfig,
    seed_offset: int,
) -> FeatureScreenResult:
    screen = screen_features_for_target(
        training_frame,
        target.rename(target_name),
        target_name=target_name,
        head_name=head_name,
        direction=direction,
        horizon=horizon,
        task_type="regression",
        schema_version=PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION,
        feature_family_by_column=feature_family_by_column,
        max_selected_features=config.mutual_information_top_k,
        random_seed=config.random_seed + seed_offset,
        missingness_threshold=0.40,
        variance_threshold=1e-12,
        correlation_threshold=config.correlation_threshold,
    )
    if not screen.selected_features:
        raise ValueError(f"{head_name} feature screen selected no features")
    return screen


def _path_magnitude_target_name(*, external_target: str, head_name: str) -> str:
    if head_name == MFE_HEAD:
        return f"{external_target}__favorable_magnitude"
    if head_name == MAE_HEAD:
        return f"{external_target}__adverse_magnitude"
    raise ValueError(f"Unsupported path magnitude head: {head_name}")


def _path_atr_target_name(*, external_target: str, head_name: str) -> str:
    if head_name == EXPECTED_RETURN_HEAD:
        return f"{external_target}__atr_units_{PATH_TARGET_ATR_FEATURE}"
    if head_name == MFE_HEAD:
        return f"{external_target}__favorable_magnitude_atr_units_{PATH_TARGET_ATR_FEATURE}"
    if head_name == MAE_HEAD:
        return f"{external_target}__adverse_magnitude_atr_units_{PATH_TARGET_ATR_FEATURE}"
    raise ValueError(f"Unsupported path target head: {head_name}")


def _path_atr_values(frame: pd.DataFrame) -> pd.Series:
    if PATH_TARGET_ATR_FEATURE not in frame.columns:
        raise ValueError("path_target_atr_feature_missing")
    values = pd.to_numeric(frame[PATH_TARGET_ATR_FEATURE], errors="coerce")
    finite = np.isfinite(values.to_numpy(dtype=float, na_value=np.nan))
    if not bool(finite.all()) or bool((values <= 0.0).any()):
        raise ValueError("path_target_atr_feature_invalid")
    return values.astype(float)


def _path_atr_training_target(
    external_target: pd.Series,
    atr_values: pd.Series,
    *,
    head_name: str,
    external_target_name: str,
) -> pd.Series:
    target = pd.to_numeric(external_target, errors="coerce")
    atr = pd.to_numeric(atr_values, errors="coerce").reindex(target.index)
    if head_name in {EXPECTED_RETURN_HEAD, MFE_HEAD}:
        normalized = target / atr
    elif head_name == MAE_HEAD:
        normalized = -target / atr
    else:
        raise ValueError(f"Unsupported path target head: {head_name}")
    normalized.name = _path_atr_target_name(
        external_target=external_target_name,
        head_name=head_name,
    )
    return normalized


def _path_target_normalization_hash(
    *,
    head_name: str,
    external_target_name: str,
    internal_target_name: str,
    direction: str,
    horizon: int,
) -> str:
    return configuration_hash(
        {
            "schema_version": PATH_TARGET_NORMALIZATION_SCHEMA_VERSION,
            "head_name": head_name,
            "external_target_name": external_target_name,
            "internal_target_name": internal_target_name,
            "atr_feature_name": PATH_TARGET_ATR_FEATURE,
            "direction": direction,
            "horizon": horizon,
            "prediction_mapping_version": PATH_TARGET_PREDICTION_MAPPING_VERSION,
        }
    )


def _path_target_normalization_metadata(
    *,
    head_name: str,
    external_target_name: str,
    internal_target_name: str,
    direction: str,
    horizon: int,
) -> dict[str, object]:
    return {
        "target_normalization_schema_version": PATH_TARGET_NORMALIZATION_SCHEMA_VERSION,
        "head_name": head_name,
        "target_normalization_method": "divide_by_signal_close_atr_pct_14",
        "atr_feature_name": PATH_TARGET_ATR_FEATURE,
        "atr_feature_timing": "signal_date_close_known",
        "external_target_name": external_target_name,
        "internal_target_name": internal_target_name,
        "internal_target_unit": "atr_units",
        "canonical_external_unit": "decimal_return",
        "prediction_mapping_version": PATH_TARGET_PREDICTION_MAPPING_VERSION,
        "target_normalization_hash": _path_target_normalization_hash(
            head_name=head_name,
            external_target_name=external_target_name,
            internal_target_name=internal_target_name,
            direction=direction,
            horizon=horizon,
        ),
    }


def _path_internal_target_definition(head_name: str) -> str:
    if head_name == EXPECTED_RETURN_HEAD:
        return "signed_directional_return_divided_by_signal_close_atr_pct_14"
    if head_name == MFE_HEAD:
        return "favorable_magnitude_equals_existing_mfe_divided_by_signal_close_atr_pct_14"
    if head_name == MAE_HEAD:
        return "adverse_magnitude_equals_negative_existing_mae_divided_by_signal_close_atr_pct_14"
    raise ValueError(f"Unsupported path target head: {head_name}")


def _path_magnitude_target(
    external_target: pd.Series,
    *,
    head_name: str,
    external_target_name: str,
) -> pd.Series:
    numeric = pd.to_numeric(external_target, errors="coerce")
    if head_name == MFE_HEAD:
        magnitude = numeric.copy()
    elif head_name == MAE_HEAD:
        magnitude = -numeric
    else:
        raise ValueError(f"Unsupported path magnitude head: {head_name}")
    magnitude.name = _path_magnitude_target_name(
        external_target=external_target_name,
        head_name=head_name,
    )
    return magnitude


def _validate_path_magnitude_training_target(
    *,
    feature_frame: pd.DataFrame,
    magnitude_target: pd.Series,
    head_name: str,
) -> None:
    if len(feature_frame) != len(magnitude_target) or not feature_frame.index.equals(
        magnitude_target.index
    ):
        raise ValueError("path_magnitude_target_alignment_failed")
    reject_label_columns([str(column) for column in feature_frame.columns])
    numeric = pd.to_numeric(magnitude_target, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("path_magnitude_target_nonfinite")
    if bool((values < 0.0).any()):
        reason = (
            "mfe_magnitude_target_invalid"
            if head_name == MFE_HEAD
            else "mae_magnitude_target_invalid"
        )
        raise ValueError(f"{reason}: path_magnitude_target_negative")
    if not bool((values > 0.0).any()):
        raise ValueError("path_magnitude_target_all_zero")


def _path_magnitude_prediction(
    estimator: Any,
    features: pd.DataFrame,
    *,
    head_name: str,
    index: pd.Index,
    atr_values: pd.Series | None = None,
) -> PathMagnitudePrediction:
    magnitude = pd.Series(
        np.asarray(estimator.predict(features), dtype=float),
        index=index,
    )
    if atr_values is not None:
        atr = pd.to_numeric(atr_values, errors="coerce").reindex(index).astype(float)
        external_magnitude = magnitude * atr
    else:
        external_magnitude = magnitude
    canonical = external_magnitude if head_name == MFE_HEAD else -external_magnitude
    canonical = pd.Series(np.asarray(canonical, dtype=float), index=index)
    magnitude_values = magnitude.to_numpy(dtype=float, na_value=np.nan)
    signed_values = canonical.to_numpy(dtype=float, na_value=np.nan)
    nonfinite_count = int((~np.isfinite(magnitude_values)).sum())
    nonfinite_count += int((~np.isfinite(signed_values)).sum())
    magnitude_violation = int((np.isfinite(magnitude_values) & (magnitude_values < 0.0)).sum())
    if head_name == MFE_HEAD:
        signed_violation = int((np.isfinite(signed_values) & (signed_values < 0.0)).sum())
    elif head_name == MAE_HEAD:
        signed_violation = int((np.isfinite(signed_values) & (signed_values > 0.0)).sum())
    else:
        raise ValueError(f"Unsupported path magnitude head: {head_name}")
    return PathMagnitudePrediction(
        internal_magnitude=magnitude,
        canonical_signed=canonical,
        nonfinite_count=nonfinite_count,
        magnitude_domain_violation_count=magnitude_violation,
        signed_domain_violation_count=signed_violation,
    )


def _path_target_prediction(
    estimator: Any,
    features: pd.DataFrame,
    *,
    atr_values: pd.Series,
    index: pd.Index,
) -> PathTargetPrediction:
    internal = pd.Series(
        np.asarray(estimator.predict(features), dtype=float),
        index=index,
    )
    atr = pd.to_numeric(atr_values, errors="coerce").reindex(index).astype(float)
    canonical = pd.Series(np.asarray(internal * atr, dtype=float), index=index)
    internal_values = internal.to_numpy(dtype=float, na_value=np.nan)
    canonical_values = canonical.to_numpy(dtype=float, na_value=np.nan)
    nonfinite_count = int((~np.isfinite(internal_values)).sum())
    nonfinite_count += int((~np.isfinite(canonical_values)).sum())
    return PathTargetPrediction(
        internal_atr_units=internal,
        canonical_external=canonical,
        atr_values=atr,
        nonfinite_count=nonfinite_count,
    )


def _should_retire_path_head(family: str, head_name: str) -> bool:
    return family in LINEAR_PATH_HEAD_RETIREMENT_FAMILIES and head_name in PATH_MAGNITUDE_HEADS


def _retired_path_prediction(index: pd.Index, *, head_name: str) -> PathMagnitudePrediction:
    magnitude = pd.Series(np.full(len(index), math.nan), index=index, dtype=float)
    canonical = pd.Series(np.full(len(index), math.nan), index=index, dtype=float)
    return PathMagnitudePrediction(
        internal_magnitude=magnitude,
        canonical_signed=canonical,
        nonfinite_count=int(len(index) * 2),
        magnitude_domain_violation_count=0,
        signed_domain_violation_count=0,
    )


def _path_domain_metadata(
    *,
    head_name: str,
    external_target_name: str,
    magnitude_target: pd.Series,
    estimator: Any,
    spec: PathMagnitudeEstimatorSpec,
    selected_feature_manifest_hash: str,
    calibration_prediction: PathMagnitudePrediction,
    holdout_prediction: PathMagnitudePrediction,
    target_normalization_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    target_values = pd.to_numeric(magnitude_target, errors="coerce")
    definition = _path_internal_target_definition(head_name)
    normalization = dict(target_normalization_metadata or {})
    return {
        "domain_schema_version": PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION,
        "path_head_capability_state": PATH_HEAD_CAPABILITY_ACTIVE,
        "path_head_retirement_schema_version": "",
        "path_head_retirement_reason": "",
        "path_head_required_for_promotion": True,
        "head_name": head_name,
        "external_target_name": external_target_name,
        "internal_magnitude_target_name": str(magnitude_target.name),
        "internal_target_definition": definition,
        "estimator_class": spec.estimator_class,
        "estimator_loss": spec.loss,
        "estimator_hyperparameters": spec.hyperparameters,
        "selected_feature_manifest_hash": selected_feature_manifest_hash,
        "preprocessing_hash": _pipeline_preprocessing_hash(estimator),
        "estimator_hash": _estimator_hash(estimator),
        "prediction_mapping_version": PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION,
        "transformation_chain": (
            f"{external_target_name} -> {magnitude_target.name} -> "
            f"{spec.estimator_class} -> internal_magnitude_atr_unit_prediction -> "
            "canonical_signed_decimal_output"
        ),
        "target_normalization": normalization,
        "target_normalization_schema_version": str(
            normalization.get("target_normalization_schema_version") or ""
        ),
        "target_normalization_method": str(normalization.get("target_normalization_method") or ""),
        "atr_feature_name": str(normalization.get("atr_feature_name") or ""),
        "target_normalization_hash": str(normalization.get("target_normalization_hash") or ""),
        "internal_target_unit": str(normalization.get("internal_target_unit") or ""),
        "canonical_external_unit": str(normalization.get("canonical_external_unit") or ""),
        "training_target_min": _series_min(target_values),
        "training_target_max": _series_max(target_values),
        "training_target_positive_count": int((target_values > 0.0).sum()),
        "convergence_diagnostics": _convergence_diagnostics(estimator),
        "calibration_domain_diagnostics": calibration_prediction.diagnostics(
            f"{head_name}_calibration"
        ),
        "holdout_domain_diagnostics": holdout_prediction.diagnostics(f"{head_name}_holdout"),
    }


def _retired_path_domain_metadata(
    *,
    family: str,
    head_name: str,
    external_target_name: str,
    magnitude_target: pd.Series,
    selected_feature_manifest_hash: str,
    calibration_prediction: PathMagnitudePrediction,
    holdout_prediction: PathMagnitudePrediction,
    target_normalization_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    target_values = pd.to_numeric(magnitude_target, errors="coerce")
    internal_definition = _path_internal_target_definition(head_name)
    normalization = dict(target_normalization_metadata or {})
    estimator_payload: dict[str, object] = {
        "schema_version": LINEAR_PATH_HEAD_RETIREMENT_SCHEMA_VERSION,
        "family": family,
        "head_name": head_name,
        "capability_state": PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR,
        "reason": LINEAR_PATH_HEAD_RETIREMENT_REASON,
    }
    return {
        "domain_schema_version": PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION,
        "path_head_capability_state": PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR,
        "path_head_retirement_schema_version": LINEAR_PATH_HEAD_RETIREMENT_SCHEMA_VERSION,
        "path_head_retirement_reason": LINEAR_PATH_HEAD_RETIREMENT_REASON,
        "path_head_required_for_promotion": True,
        "head_name": head_name,
        "external_target_name": external_target_name,
        "internal_magnitude_target_name": str(magnitude_target.name),
        "internal_target_definition": internal_definition,
        "estimator_class": "RetiredPathHeadModel",
        "estimator_loss": "not_applicable_retired_path_head",
        "estimator_hyperparameters": estimator_payload,
        "selected_feature_manifest_hash": selected_feature_manifest_hash,
        "preprocessing_hash": "",
        "estimator_hash": configuration_hash(estimator_payload),
        "prediction_mapping_version": PATH_MAGNITUDE_PREDICTION_MAPPING_VERSION,
        "transformation_chain": (
            f"{external_target_name} -> {magnitude_target.name} -> "
            "RETIRED_UNSUITABLE_ESTIMATOR -> no_prediction"
        ),
        "target_normalization": normalization,
        "target_normalization_schema_version": str(
            normalization.get("target_normalization_schema_version") or ""
        ),
        "target_normalization_method": str(normalization.get("target_normalization_method") or ""),
        "atr_feature_name": str(normalization.get("atr_feature_name") or ""),
        "target_normalization_hash": str(normalization.get("target_normalization_hash") or ""),
        "internal_target_unit": str(normalization.get("internal_target_unit") or ""),
        "canonical_external_unit": str(normalization.get("canonical_external_unit") or ""),
        "training_target_min": _series_min(target_values),
        "training_target_max": _series_max(target_values),
        "training_target_positive_count": int((target_values > 0.0).sum()),
        "convergence_diagnostics": {
            "estimator_class": "RetiredPathHeadModel",
            "converged": False,
            "retired": True,
            "reason": LINEAR_PATH_HEAD_RETIREMENT_REASON,
        },
        "calibration_domain_diagnostics": calibration_prediction.diagnostics(
            f"{head_name}_calibration"
        ),
        "holdout_domain_diagnostics": holdout_prediction.diagnostics(f"{head_name}_holdout"),
    }


def _path_domain_metric_payload(
    *,
    head_name: str,
    metadata: dict[str, object],
) -> dict[str, float | int | str | bool | None]:
    prefix = head_name
    convergence = metadata.get("convergence_diagnostics")
    convergence_payload = convergence if isinstance(convergence, dict) else {}
    calibration_diag = metadata.get("calibration_domain_diagnostics")
    holdout_diag = metadata.get("holdout_domain_diagnostics")
    calibration_payload = calibration_diag if isinstance(calibration_diag, dict) else {}
    holdout_payload = holdout_diag if isinstance(holdout_diag, dict) else {}
    training_min = metadata.get("training_target_min")
    training_max = metadata.get("training_target_max")
    training_positive = metadata.get("training_target_positive_count")
    return {
        f"{prefix}_domain_schema_version": str(metadata.get("domain_schema_version") or ""),
        f"{prefix}_path_head_capability_state": str(
            metadata.get("path_head_capability_state") or ""
        ),
        f"{prefix}_path_head_retirement_schema_version": str(
            metadata.get("path_head_retirement_schema_version") or ""
        ),
        f"{prefix}_path_head_retirement_reason": str(
            metadata.get("path_head_retirement_reason") or ""
        ),
        f"{prefix}_external_target_name": str(metadata.get("external_target_name") or ""),
        f"{prefix}_internal_magnitude_target_name": str(
            metadata.get("internal_magnitude_target_name") or ""
        ),
        f"{prefix}_internal_target_definition": str(
            metadata.get("internal_target_definition") or ""
        ),
        f"{prefix}_magnitude_estimator_class": str(metadata.get("estimator_class") or ""),
        f"{prefix}_magnitude_estimator_loss": str(metadata.get("estimator_loss") or ""),
        f"{prefix}_magnitude_estimator_hyperparameters_json": _json_dumps(
            metadata.get("estimator_hyperparameters") or {}
        ),
        f"{prefix}_magnitude_preprocessing_hash": str(metadata.get("preprocessing_hash") or ""),
        f"{prefix}_magnitude_estimator_hash": str(metadata.get("estimator_hash") or ""),
        f"{prefix}_prediction_mapping_version": str(
            metadata.get("prediction_mapping_version") or ""
        ),
        f"{prefix}_target_normalization_schema_version": str(
            metadata.get("target_normalization_schema_version") or ""
        ),
        f"{prefix}_target_normalization_method": str(
            metadata.get("target_normalization_method") or ""
        ),
        f"{prefix}_target_normalization_atr_feature_name": str(
            metadata.get("atr_feature_name") or ""
        ),
        f"{prefix}_target_normalization_hash": str(metadata.get("target_normalization_hash") or ""),
        f"{prefix}_internal_target_unit": str(metadata.get("internal_target_unit") or ""),
        f"{prefix}_canonical_external_unit": str(metadata.get("canonical_external_unit") or ""),
        f"{prefix}_magnitude_training_target_min": float(training_min)
        if isinstance(training_min, (int, float))
        else None,
        f"{prefix}_magnitude_training_target_max": float(training_max)
        if isinstance(training_max, (int, float))
        else None,
        f"{prefix}_magnitude_training_target_positive_count": int(training_positive)
        if isinstance(training_positive, int)
        else None,
        f"{prefix}_magnitude_convergence_status": bool(convergence_payload.get("converged", True)),
        f"{prefix}_magnitude_convergence_diagnostics_json": _json_dumps(convergence_payload),
        f"{prefix}_magnitude_domain_metadata_json": _json_dumps(metadata),
        **{
            str(key): value
            for key, value in calibration_payload.items()
            if isinstance(value, (float, int, bool)) or value is None
        },
        **{
            str(key): value
            for key, value in holdout_payload.items()
            if isinstance(value, (float, int, bool)) or value is None
        },
    }


def _path_target_normalization_metric_payload(
    *,
    head_name: str,
    metadata: dict[str, object],
) -> dict[str, float | int | str | bool | None]:
    metric_key = PATH_HEAD_TARGET_METRIC_KEYS[head_name]
    return {
        f"{metric_key}_target_normalization_schema_version": str(
            metadata.get("target_normalization_schema_version") or ""
        ),
        f"{metric_key}_target_normalization_method": str(
            metadata.get("target_normalization_method") or ""
        ),
        f"{metric_key}_target_normalization_atr_feature_name": str(
            metadata.get("atr_feature_name") or ""
        ),
        f"{metric_key}_target_normalization_hash": str(
            metadata.get("target_normalization_hash") or ""
        ),
        f"{metric_key}_internal_target_name": str(metadata.get("internal_target_name") or ""),
        f"{metric_key}_internal_target_unit": str(metadata.get("internal_target_unit") or ""),
        f"{metric_key}_canonical_external_unit": str(metadata.get("canonical_external_unit") or ""),
        f"{metric_key}_target_prediction_mapping_version": str(
            metadata.get("prediction_mapping_version") or ""
        ),
        f"{metric_key}_target_normalization_metadata_json": _json_dumps(metadata),
    }


def _positive_group_fraction(frame: pd.DataFrame, returns: pd.Series, group: str) -> float:
    if frame.empty or group not in frame.columns:
        return math.nan
    grouped = pd.DataFrame({"group": frame[group], "return": returns}).dropna()
    if grouped.empty:
        return math.nan
    means = grouped.groupby("group")["return"].mean()
    return float((means > 0).mean()) if not means.empty else math.nan


def _max_concentration(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return math.nan
    shares = frame[column].value_counts(normalize=True, dropna=True)
    return float(shares.max()) if not shares.empty else math.nan


def _empty_temporal_fold_details(folds: int) -> dict[str, object]:
    return {
        "schema_version": TEMPORAL_FOLD_STABILITY_SCHEMA_VERSION,
        "folds_requested": folds,
        "folds_evaluated": 0,
        "folds_with_selected_observations": 0,
        "selected_observations_per_fold": [0 for _ in range(folds)],
        "fold_records": [],
        "positive_fraction": GATE_VALUE_NOT_AVAILABLE,
    }


def _temporal_fold_stability_details(
    frame: pd.DataFrame,
    returns: pd.Series,
    *,
    folds: int = TEMPORAL_FOLD_STABILITY_REQUESTED_FOLDS,
) -> dict[str, object]:
    details = _empty_temporal_fold_details(folds)
    if frame.empty or returns.empty:
        return details
    if "Date" not in frame.columns:
        return details
    ordered = pd.DataFrame(
        {
            "Date": pd.to_datetime(frame["Date"], errors="coerce"),
            "return": pd.to_numeric(returns, errors="coerce").to_numpy(dtype=float),
        }
    ).dropna()
    if ordered.empty:
        return details
    ordered = ordered.sort_values("Date").reset_index(drop=True)
    fold_indices = np.array_split(np.arange(len(ordered)), folds)
    selected_counts = [len(indices) for indices in fold_indices]
    fold_records: list[dict[str, object]] = []
    fold_positive_results: list[bool] = []
    for position, indices in enumerate(fold_indices, start=1):
        if len(indices) == 0:
            continue
        fold_returns = ordered.iloc[indices]["return"]
        mean_return = float(fold_returns.mean())
        positive = bool(mean_return > 0.0)
        fold_positive_results.append(positive)
        fold_records.append(
            {
                "fold": position,
                "selected_count": len(indices),
                "mean_return": mean_return,
                "positive": positive,
                "result": "positive" if positive else "negative_or_zero",
            }
        )
    folds_with_selected = int(sum(1 for count in selected_counts if count > 0))
    details.update(
        {
            "folds_evaluated": len(fold_records),
            "folds_with_selected_observations": folds_with_selected,
            "selected_observations_per_fold": selected_counts,
            "fold_records": fold_records,
        }
    )
    if len(ordered) < folds:
        return details
    if not fold_positive_results:
        return details
    details["positive_fraction"] = float(
        sum(1 for positive in fold_positive_results if positive) / len(fold_positive_results)
    )
    return details


def _temporal_fold_stability(
    frame: pd.DataFrame,
    returns: pd.Series,
    *,
    folds: int = TEMPORAL_FOLD_STABILITY_REQUESTED_FOLDS,
) -> float:
    positive_fraction = _temporal_fold_stability_details(
        frame,
        returns,
        folds=folds,
    )["positive_fraction"]
    try:
        if isinstance(positive_fraction, str | int | float):
            return float(positive_fraction)
    except (TypeError, ValueError):
        return math.nan
    return math.nan


def _period_concentration(frame: pd.DataFrame, returns: pd.Series) -> float:
    if frame.empty or returns.empty or "Date" not in frame.columns:
        return math.nan
    data = pd.DataFrame({"Date": pd.to_datetime(frame["Date"]), "return": returns}).dropna()
    if data.empty:
        return math.nan
    yearly_abs = (
        data.assign(year=data["Date"].dt.year.astype(str))
        .groupby("year")["return"]
        .apply(lambda series: series.abs().sum())
    )
    total = float(yearly_abs.sum())
    if total <= 0:
        return math.nan
    return float(yearly_abs.max() / total)


def _status_from_bool(value: bool) -> GateStatus:
    return "PASS" if value else "FAIL"


def _float_metric(values: dict[str, float | int | str | bool | None], key: str) -> float:
    value = values.get(key)
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return math.nan


def _build_gate_results(
    *,
    metrics: dict[str, float | int | str | bool | None],
    calibration_metrics: dict[str, float | int | str | bool | None],
    family: str,
    config: DiscoveryConfig,
    config_hash: str,
) -> tuple[GateResult, ...]:
    gates: list[GateResult] = []
    now = datetime.now(UTC).isoformat()

    def add(
        gate_id: str,
        name: str,
        category: str,
        scope: str,
        metric_name: str,
        threshold: str | float | int | bool | None,
        comparator: str,
        actual: str | float | int | bool | None,
        status: GateStatus,
        mandatory: bool,
        reason: str,
        evidence: str = "model_evaluation",
    ) -> None:
        gates.append(
            make_gate(
                gate_id=gate_id,
                gate_name=name,
                category=category,
                scope=scope,
                metric_name=metric_name,
                threshold=threshold,
                comparator=comparator,
                actual_value=actual,
                status=status,
                mandatory=mandatory,
                evidence_source=evidence,
                reason=reason,
                configuration_hash_value=config_hash,
                evaluated_at_utc=now,
            )
        )

    training_samples = int(metrics.get("training_samples") or 0)
    holdout_samples = int(metrics.get("holdout_samples") or 0)
    selected_count = int(metrics.get("selected_holdout_samples") or 0)
    lcb = _float_metric(metrics, "holdout_mean_return_lcb_90")
    brier_skill = _float_metric(calibration_metrics, "brier_skill_score")
    holdout_brier = _float_metric(calibration_metrics, "holdout_brier")
    portfolio_drawdown = _float_metric(metrics, "portfolio_max_drawdown")
    feature_stability = _float_metric(metrics, "feature_stability_mean_abs_z")
    symbol_concentration = _float_metric(metrics, "symbol_concentration_top")
    sector_concentration = _float_metric(metrics, "sector_concentration_top")
    double_cost_lcb = _float_metric(metrics, "holdout_double_cost_lcb_90")
    turnover = _float_metric(metrics, "prediction_turnover")
    period_concentration = _float_metric(metrics, "exceptional_period_concentration_top")
    prediction_ood = int(metrics.get("prediction_sanity_ood_total") or 0)
    selected_rate = float(metrics.get("selected_observation_rate") or 0.0)
    holdout_status = str(metrics.get("holdout_status") or GATE_VALUE_NOT_AVAILABLE)
    symbol_concentration_status: GateStatus = (
        "NOT_APPLICABLE"
        if not math.isfinite(symbol_concentration)
        else _status_from_bool(compare_gate_values(symbol_concentration, "<=", 0.50))
    )
    sector_concentration_status: GateStatus = (
        "NOT_APPLICABLE"
        if not math.isfinite(sector_concentration)
        else _status_from_bool(compare_gate_values(sector_concentration, "<=", 0.80))
    )
    period_concentration_status: GateStatus = (
        "NOT_APPLICABLE"
        if not math.isfinite(period_concentration)
        else _status_from_bool(compare_gate_values(period_concentration, "<=", 0.60))
    )
    profit_factor = profit_factor_result(
        selected_count=selected_count,
        positive_return_sum=_float_metric(metrics, "holdout_positive_return_sum"),
        negative_return_abs_sum=_float_metric(metrics, "holdout_negative_return_abs_sum"),
        zero_return_count=int(metrics.get("holdout_zero_return_count") or 0),
        naive_control=family == "naive_base_rate",
        threshold=0.90,
    )
    temporal_fold = temporal_fold_stability_result(
        selected_count=selected_count,
        folds_requested=int(
            metrics.get("temporal_fold_folds_requested") or TEMPORAL_FOLD_STABILITY_REQUESTED_FOLDS
        ),
        folds_evaluated=int(metrics.get("temporal_fold_folds_evaluated") or 0),
        folds_with_selected_observations=int(
            metrics.get("temporal_fold_folds_with_selected_observations") or 0
        ),
        selected_observations_per_fold=tuple(
            cast(
                list[int],
                json.loads(str(metrics.get("temporal_fold_selected_observations_per_fold_json")))
                if metrics.get("temporal_fold_selected_observations_per_fold_json")
                else [],
            )
        ),
        positive_fraction=metrics.get("temporal_fold_positive_fraction"),
        naive_control=family == "naive_base_rate",
        threshold=TEMPORAL_FOLD_STABILITY_THRESHOLD,
    )

    add(
        FINAL_HOLDOUT_PROMOTION_GATE_ID,
        "Final Holdout Required For Promotion",
        "research integrity",
        "model",
        "holdout_status",
        FINAL_HOLDOUT_STATUS,
        "equals",
        holdout_status,
        _status_from_bool(holdout_status == FINAL_HOLDOUT_STATUS),
        True,
        "Model has a final holdout and may be considered for promotion."
        if holdout_status == FINAL_HOLDOUT_STATUS
        else (
            f"Model holdout status is {holdout_status}; only {FINAL_HOLDOUT_STATUS} "
            "models can be promoted."
        ),
    )
    add(
        "minimum_training_samples",
        "Minimum Training Samples",
        "data sufficiency",
        "prediction",
        "training_samples",
        config.minimum_training_samples,
        ">=",
        training_samples,
        _status_from_bool(training_samples >= config.minimum_training_samples),
        True,
        "Training sample count meets configured minimum."
        if training_samples >= config.minimum_training_samples
        else "Training sample count is below configured minimum.",
    )
    add(
        "minimum_unseen_observations",
        "Minimum Unseen Holdout Observations",
        "data sufficiency",
        "prediction",
        "holdout_samples",
        config.minimum_holdout_samples,
        ">=",
        holdout_samples,
        _status_from_bool(holdout_samples >= config.minimum_holdout_samples),
        True,
        "Holdout observation count meets configured minimum."
        if holdout_samples >= config.minimum_holdout_samples
        else "Holdout observation count is below configured minimum.",
    )
    add(
        "brier_skill_vs_naive_positive",
        "Brier Skill Versus Naive Control",
        "predictive skill",
        "prediction",
        "brier_skill_score",
        0.0,
        ">",
        brier_skill,
        _status_from_bool(math.isfinite(brier_skill) and brier_skill > 0.0),
        family != "naive_base_rate",
        "Model Brier is better than matching direction/horizon naive control."
        if math.isfinite(brier_skill) and brier_skill > 0.0
        else "Model Brier is not better than the matching naive control.",
    )
    add(
        "holdout_brier_max_035",
        "Holdout Brier Maximum",
        "calibration",
        "prediction",
        "holdout_brier",
        0.35,
        "<=",
        holdout_brier,
        _status_from_bool(math.isfinite(holdout_brier) and holdout_brier <= 0.35),
        True,
        "Holdout Brier is within configured maximum."
        if math.isfinite(holdout_brier) and holdout_brier <= 0.35
        else "Holdout Brier exceeds configured maximum.",
    )
    if family == "naive_base_rate" and selected_count == 0:
        add(
            "selected_candidate_quality_available",
            "Selected Candidate Trading Metrics Available",
            "selected-candidate quality",
            "selected_candidates",
            "selected_holdout_samples",
            0,
            "> 0",
            selected_count,
            "NOT_APPLICABLE",
            False,
            "Naive control selected zero rows; trading metrics are not comparable.",
        )
    if family != "naive_base_rate" or selected_count > 0:
        add(
            "positive_expected_value_after_costs",
            "Positive Expected Value After Costs",
            "selected-candidate quality",
            "selected_candidates",
            "holdout_mean_return_lcb_90",
            -(config.round_trip_cost_bps / 10_000.0),
            ">",
            lcb,
            _status_from_bool(
                math.isfinite(lcb) and lcb > -(config.round_trip_cost_bps / 10_000.0)
            ),
            True,
            "Lower confidence bound is above negative round-trip cost."
            if math.isfinite(lcb) and lcb > -(config.round_trip_cost_bps / 10_000.0)
            else "Lower confidence bound is missing or below cost threshold.",
        )
        add(
            "profit_factor_min_090",
            "Profit Factor Minimum",
            "selected-candidate quality",
            "selected_candidates",
            "holdout_profit_factor",
            0.90,
            ">=",
            profit_factor.actual_value,
            profit_factor.status,
            family != "naive_base_rate",
            profit_factor.reason,
        )
    elif family == "naive_base_rate" and selected_count == 0:
        add(
            "profit_factor_min_090",
            "Profit Factor Minimum",
            "selected-candidate quality",
            "selected_candidates",
            "holdout_profit_factor",
            0.90,
            ">=",
            profit_factor.actual_value,
            profit_factor.status,
            False,
            profit_factor.reason,
        )
    add(
        "portfolio_drawdown_available",
        "Portfolio Drawdown Available",
        "portfolio performance",
        "portfolio_holdout",
        "portfolio_max_drawdown",
        "finite",
        "is finite",
        portfolio_drawdown,
        _status_from_bool(math.isfinite(portfolio_drawdown)),
        family != "naive_base_rate",
        "Portfolio drawdown was calculated from daily portfolio equity."
        if math.isfinite(portfolio_drawdown)
        else "Portfolio drawdown is missing.",
    )
    add(
        "portfolio_drawdown_not_worse_than_50pct",
        "Portfolio Drawdown Not Worse Than 50%",
        "drawdown",
        "portfolio_holdout",
        "portfolio_max_drawdown",
        -0.50,
        ">",
        portfolio_drawdown,
        _status_from_bool(math.isfinite(portfolio_drawdown) and portfolio_drawdown > -0.50),
        family != "naive_base_rate",
        "Portfolio drawdown passes configured limit."
        if math.isfinite(portfolio_drawdown) and portfolio_drawdown > -0.50
        else "Portfolio drawdown is missing or worse than configured limit.",
    )
    add(
        "feature_stability_mean_abs_z_max_250",
        "Feature Stability Mean Abs Z Maximum",
        "feature stability",
        "prediction",
        "feature_stability_mean_abs_z",
        2.50,
        "<=",
        feature_stability,
        _status_from_bool(math.isfinite(feature_stability) and feature_stability <= 2.50),
        True,
        "Holdout feature distribution shift is within configured cap."
        if math.isfinite(feature_stability) and feature_stability <= 2.50
        else "Holdout feature distribution shift exceeds configured cap.",
    )
    add(
        "symbol_concentration_max_050",
        "Symbol Concentration Maximum",
        "symbol concentration",
        "selected_candidates",
        "symbol_concentration_top",
        0.50,
        "<=",
        symbol_concentration,
        symbol_concentration_status,
        True,
        threshold_reason(
            metric_label="Symbol concentration",
            actual_value=symbol_concentration,
            comparator="<=",
            threshold=0.50,
            status=symbol_concentration_status,
            unavailable_reason="Symbol concentration is unavailable because no rows were selected.",
            percent=True,
        ),
    )
    add(
        "sector_concentration_max_080",
        "Sector Concentration Maximum",
        "sector stability",
        "selected_candidates",
        "sector_concentration_top",
        0.80,
        "<=",
        sector_concentration,
        sector_concentration_status,
        True,
        threshold_reason(
            metric_label="Sector concentration",
            actual_value=sector_concentration,
            comparator="<=",
            threshold=0.80,
            status=sector_concentration_status,
            unavailable_reason="Sector concentration is unavailable because no rows were selected.",
            percent=True,
        ),
    )
    add(
        "transaction_cost_sensitivity_not_collapsed",
        "Double-Cost Lower Bound Not Collapsed",
        "cost sensitivity",
        "selected_candidates",
        "holdout_double_cost_lcb_90",
        -((config.round_trip_cost_bps * 2.0) / 10_000.0),
        ">",
        double_cost_lcb,
        _status_from_bool(
            math.isfinite(double_cost_lcb)
            and double_cost_lcb > -((config.round_trip_cost_bps * 2.0) / 10_000.0)
        ),
        family != "naive_base_rate",
        "Double-cost lower confidence bound remains above configured collapse threshold."
        if math.isfinite(double_cost_lcb)
        and double_cost_lcb > -((config.round_trip_cost_bps * 2.0) / 10_000.0)
        else "Double-cost lower confidence bound fails or is missing.",
    )
    add(
        "prediction_turnover_max_050",
        "Prediction Turnover Maximum",
        "selection coverage",
        "selected_candidates",
        "prediction_turnover",
        0.50,
        "<=",
        turnover,
        _status_from_bool(math.isfinite(turnover) and turnover <= 0.50),
        True,
        "Selected observation rate is within configured turnover cap."
        if math.isfinite(turnover) and turnover <= 0.50
        else "Selected observation rate exceeds configured turnover cap.",
    )
    add(
        "selection_rate_policy_configured",
        "Selection-Rate Policy Configured",
        "selection coverage",
        "selected_candidates",
        "selected_observation_rate",
        config.selection_rate_max,
        "<= configured max",
        selected_rate,
        "NOT_CONFIGURED"
        if config.selection_rate_max is None
        else _status_from_bool(selected_rate <= config.selection_rate_max),
        True,
        "No user-approved selection-rate maximum is configured."
        if config.selection_rate_max is None
        else "Selected rate evaluated against configured maximum.",
    )
    add(
        "temporal_fold_stability_evidence_available",
        "Temporal Fold Stability Evidence Available",
        "temporal stability",
        "selected_candidates",
        "temporal_fold_evidence_status",
        "AVAILABLE",
        "is available",
        temporal_fold.evidence_status,
        temporal_fold.evidence_gate_status,
        family != "naive_base_rate",
        temporal_fold.evidence_reason,
    )
    add(
        "temporal_fold_stability_min_050",
        "Temporal Fold Positive Fraction Minimum",
        "temporal stability",
        "selected_candidates",
        "temporal_fold_positive_fraction",
        TEMPORAL_FOLD_STABILITY_THRESHOLD,
        ">=",
        temporal_fold.actual_value,
        temporal_fold.threshold_gate_status,
        family != "naive_base_rate",
        temporal_fold.threshold_reason,
    )
    add(
        "exceptional_period_concentration_max_060",
        "Exceptional Period Concentration Maximum",
        "temporal stability",
        "selected_candidates",
        "exceptional_period_concentration_top",
        0.60,
        "<=",
        period_concentration,
        period_concentration_status,
        True,
        threshold_reason(
            metric_label="Exceptional-period concentration",
            actual_value=period_concentration,
            comparator="<=",
            threshold=0.60,
            status=period_concentration_status,
            unavailable_reason=(
                "Exceptional-period concentration is unavailable because no rows were selected."
            ),
            percent=True,
        ),
    )
    add(
        "comparison_controls_available",
        "Comparison Controls Available",
        "comparison control",
        "prediction",
        "rsi_control_columns_available",
        True,
        "is true",
        bool(metrics.get("rsi_control_columns_available")),
        _status_from_bool(bool(metrics.get("rsi_control_columns_available"))),
        True,
        "RSI baseline/control columns are present."
        if bool(metrics.get("rsi_control_columns_available"))
        else "RSI baseline/control columns are missing.",
    )
    add(
        "not_naive_control",
        "Model Is Not Naive Control",
        "comparison control",
        "model",
        "naive_control_family",
        False,
        "is false",
        family == "naive_base_rate",
        _status_from_bool(family != "naive_base_rate"),
        True,
        "Naive controls are never promotion eligible."
        if family == "naive_base_rate"
        else "Model is not the naive control family.",
    )
    add(
        "prediction_ood_governance_schema_version",
        "Prediction OOD Governance Schema Version",
        "prediction sanity",
        "prediction",
        "prediction_ood_governance_version",
        PREDICTION_OOD_GOVERNANCE_VERSION,
        "equals",
        metrics.get("prediction_ood_governance_version"),
        _status_from_bool(
            metrics.get("prediction_ood_governance_version") == PREDICTION_OOD_GOVERNANCE_VERSION
        ),
        True,
        "Model artifact uses calibrated prediction OOD governance V2."
        if metrics.get("prediction_ood_governance_version") == PREDICTION_OOD_GOVERNANCE_VERSION
        else "Model artifact is missing calibrated prediction OOD governance V2 metadata.",
        evidence="prediction_ood_governance_v2",
    )
    add(
        "classification_prediction_values_finite",
        "Classification Prediction Values Finite",
        "prediction sanity",
        "classification",
        "classification_prediction_nonfinite_count",
        0,
        "==",
        int(metrics.get("classification_prediction_nonfinite_count") or 0),
        _status_from_bool(bool(metrics.get("classification_prediction_values_finite"))),
        True,
        "All classification probabilities are finite."
        if bool(metrics.get("classification_prediction_values_finite"))
        else "At least one classification probability is nonfinite.",
        evidence="prediction_ood_governance_v2",
    )
    add(
        "classification_prediction_probability_contract_valid",
        "Classification Probability Contract Valid",
        "prediction sanity",
        "classification",
        "classification_probability_out_of_range_count",
        0,
        "==",
        int(metrics.get("classification_probability_out_of_range_count") or 0),
        _status_from_bool(bool(metrics.get("classification_probability_contract_valid"))),
        True,
        "Classification probabilities are finite and within [0, 1]."
        if bool(metrics.get("classification_probability_contract_valid"))
        else "At least one classification probability is outside [0, 1] or nonfinite.",
        evidence="prediction_ood_governance_v2",
    )
    add(
        "classification_prediction_unit_contract_valid",
        "Classification Prediction Unit Contract Valid",
        "prediction sanity",
        "classification",
        "prediction_unit_contract",
        "decimal_return",
        "equals",
        metrics.get("prediction_unit_contract"),
        _status_from_bool(metrics.get("prediction_unit_contract") == "decimal_return"),
        True,
        "Scanner prediction units remain decimal returns for downstream evaluation.",
        evidence="prediction_ood_governance_v2",
    )
    for head in REGRESSION_HEADS:
        head_title = head.upper() if head in {"mfe", "mae"} else "Expected Return"
        finite = bool(metrics.get(f"{head}_prediction_values_finite"))
        unit_valid = metrics.get(f"{head}_prediction_unit_contract") == "decimal_return"
        mapping_valid = bool(metrics.get(f"{head}_prediction_head_bound_mapping_valid"))
        bounds_training_only = bool(metrics.get(f"{head}_prediction_bounds_training_only"))
        sign_valid = bool(metrics.get(f"{head}_prediction_path_metric_sign_valid"))
        calibration_rate = _float_metric(metrics, f"{head}_calibration_ood_rate")
        calibration_rate_limit = 0.05
        holdout_rate = _float_metric(metrics, f"{head}_holdout_ood_rate")
        holdout_rate_limit = _float_metric(metrics, f"{head}_calibration_ood_rate_limit")
        holdout_q99_severity = _float_metric(metrics, f"{head}_holdout_ood_q99_severity")
        severity_limit = _float_metric(metrics, f"{head}_ood_severity_q99_limit")
        holdout_max_severity = _float_metric(metrics, f"{head}_holdout_ood_max_severity")
        nonfinite_count = int(metrics.get(f"{head}_calibration_prediction_nonfinite_count") or 0)
        nonfinite_count += int(metrics.get(f"{head}_holdout_prediction_nonfinite_count") or 0)
        add(
            f"{head}_prediction_values_finite",
            f"{head_title} Prediction Values Finite",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_prediction_nonfinite_count",
            0,
            "==",
            nonfinite_count,
            _status_from_bool(finite),
            True,
            f"{head_title} predictions are finite."
            if finite
            else f"{head_title} predictions include nonfinite values.",
            evidence="prediction_ood_governance_v2",
        )
        add(
            f"{head}_prediction_unit_contract_valid",
            f"{head_title} Prediction Unit Contract Valid",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_prediction_unit_contract",
            "decimal_return",
            "equals",
            metrics.get(f"{head}_prediction_unit_contract"),
            _status_from_bool(unit_valid),
            True,
            f"{head_title} predictions use decimal-return units."
            if unit_valid
            else f"{head_title} prediction unit contract is invalid.",
            evidence="prediction_ood_governance_v2",
        )
        add(
            f"{head}_prediction_head_bound_mapping_valid",
            f"{head_title} Head Bound Mapping Valid",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_prediction_head_bound_mapping_valid",
            True,
            "is true",
            mapping_valid,
            _status_from_bool(mapping_valid),
            True,
            f"{head_title} predictions use matching head, direction, and horizon bounds."
            if mapping_valid
            else f"{head_title} predictions use mismatched OOD bounds.",
            evidence="prediction_ood_governance_v2",
        )
        add(
            f"{head}_prediction_bounds_training_only",
            f"{head_title} Bounds Training Only",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_ood_bound_provenance",
            "training_targets_only",
            "equals",
            metrics.get(f"{head}_ood_bound_provenance"),
            _status_from_bool(bounds_training_only),
            True,
            f"{head_title} OOD bounds were fit from training targets only."
            if bounds_training_only
            else f"{head_title} OOD bounds were not training-only.",
            evidence="prediction_ood_governance_v2",
        )
        add(
            f"{head}_prediction_path_metric_sign_valid",
            f"{head_title} Path Metric Sign Valid",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_prediction_path_metric_sign_valid",
            True,
            "is true",
            sign_valid,
            _status_from_bool(sign_valid),
            True,
            f"{head_title} path-metric sign contract is valid."
            if sign_valid
            else f"{head_title} path-metric sign contract failed.",
            evidence="prediction_ood_governance_v2",
        )
        if head in PATH_MAGNITUDE_HEADS:
            capability_state = str(metrics.get(f"{head}_path_head_capability_state") or "")
            capability_active = capability_state == PATH_HEAD_CAPABILITY_ACTIVE
            add(
                f"{head}_required_path_head_active",
                f"{head_title} Required Path Head Active",
                "prediction sanity",
                f"regression:{head}",
                f"{head}_path_head_capability_state",
                PATH_HEAD_CAPABILITY_ACTIVE,
                "equals",
                capability_state,
                _status_from_bool(capability_active),
                True,
                f"{head_title} required path head is active."
                if capability_active
                else (
                    f"{head_title} required path head is not active: "
                    f"{metrics.get(f'{head}_path_head_retirement_reason') or capability_state}."
                ),
                evidence=LINEAR_PATH_HEAD_RETIREMENT_SCHEMA_VERSION,
            )
            schema_valid = (
                metrics.get(f"{head}_domain_schema_version") == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
            )
            calibration_domain_valid = bool(
                metrics.get(f"{head}_calibration_domain_integrity_valid")
            )
            holdout_domain_valid = bool(metrics.get(f"{head}_holdout_domain_integrity_valid"))
            domain_valid = schema_valid and calibration_domain_valid and holdout_domain_valid
            add(
                f"{head}_magnitude_domain_integrity_valid",
                f"{head_title} Magnitude Domain Integrity Valid",
                "prediction sanity",
                f"regression:{head}",
                f"{head}_domain_schema_version",
                PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION,
                "equals and diagnostics pass",
                metrics.get(f"{head}_domain_schema_version"),
                _status_from_bool(domain_valid),
                True,
                f"{head_title} uses domain-preserving magnitude modeling and valid signed outputs."
                if domain_valid
                else (
                    f"{head_title} is missing domain-preserving metadata or emitted invalid "
                    "magnitude/signed predictions."
                ),
                evidence="path_metric_magnitude_domain_v1",
            )
        add(
            f"{head}_calibration_ood_rate_acceptable",
            f"{head_title} Calibration OOD Rate Acceptable",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_calibration_ood_rate",
            calibration_rate_limit,
            "<=",
            calibration_rate,
            _status_from_bool(math.isfinite(calibration_rate) and calibration_rate <= 0.05),
            True,
            f"{head_title} calibration OOD rate is within the 5% maximum."
            if math.isfinite(calibration_rate) and calibration_rate <= 0.05
            else f"{head_title} calibration OOD rate exceeds the 5% maximum.",
            evidence="prediction_ood_governance_v2",
        )
        add(
            f"{head}_holdout_ood_rate_acceptable",
            f"{head_title} Holdout OOD Rate Acceptable",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_holdout_ood_rate",
            holdout_rate_limit,
            "<=",
            holdout_rate,
            _status_from_bool(
                math.isfinite(holdout_rate)
                and math.isfinite(holdout_rate_limit)
                and holdout_rate <= holdout_rate_limit
            ),
            True,
            f"{head_title} holdout OOD rate is within the frozen calibration-derived limit."
            if math.isfinite(holdout_rate)
            and math.isfinite(holdout_rate_limit)
            and holdout_rate <= holdout_rate_limit
            else f"{head_title} holdout OOD rate exceeds the frozen calibration-derived limit.",
            evidence="prediction_ood_governance_v2",
        )
        add(
            f"{head}_holdout_ood_q99_severity_acceptable",
            f"{head_title} Holdout OOD Q99 Severity Acceptable",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_holdout_ood_q99_severity",
            severity_limit,
            "<=",
            holdout_q99_severity,
            _status_from_bool(
                math.isfinite(holdout_q99_severity)
                and math.isfinite(severity_limit)
                and holdout_q99_severity <= severity_limit
            ),
            True,
            f"{head_title} holdout OOD q99 severity is within the frozen limit."
            if math.isfinite(holdout_q99_severity)
            and math.isfinite(severity_limit)
            and holdout_q99_severity <= severity_limit
            else f"{head_title} holdout OOD q99 severity exceeds the frozen limit.",
            evidence="prediction_ood_governance_v2",
        )
        add(
            f"{head}_catastrophic_prediction_extrapolation_absent",
            f"{head_title} Catastrophic Extrapolation Absent",
            "prediction sanity",
            f"regression:{head}",
            f"{head}_holdout_ood_max_severity",
            1.0,
            "<=",
            holdout_max_severity,
            _status_from_bool(math.isfinite(holdout_max_severity) and holdout_max_severity <= 1.0),
            True,
            f"{head_title} maximum holdout OOD severity is not catastrophic."
            if math.isfinite(holdout_max_severity) and holdout_max_severity <= 1.0
            else f"{head_title} maximum holdout OOD severity exceeds 1.00.",
            evidence="prediction_ood_governance_v2",
        )
    add(
        "legacy_prediction_out_of_distribution_absent_deprecated",
        "Legacy No OOD Regression Predictions Deprecated",
        "legacy",
        "prediction",
        "prediction_sanity_ood_total",
        0,
        "deprecated",
        prediction_ood,
        "NOT_APPLICABLE",
        False,
        "The zero-exceedance OOD rule is deprecated under prediction_ood_governance_v2.",
        evidence="prediction_ood_governance_v2",
    )
    return tuple(gates)


def _train_family(
    *,
    model_id: str,
    family: str,
    classifier: Any,
    split: ChronologicalSplit,
    full_frame: pd.DataFrame,
    feature_columns: list[str],
    feature_family_by_column: dict[str, str],
    direction: str,
    horizon: int,
    config: DiscoveryConfig,
    calibration_audit_dir: str | Path,
) -> ModelBundle:
    target = f"label_{direction}_positive_return_{horizon}"
    returns = f"label_{direction}_forward_return_{horizon}"
    mfe = f"label_{direction}_mfe_{horizon}"
    mae = f"label_{direction}_mae_{horizon}"
    target_before_stop = f"label_{direction}_target_before_stop_{horizon}"
    required = [target, returns, mfe, mae, target_before_stop]
    path_required = [*required, PATH_TARGET_ATR_FEATURE]
    train = split.train.dropna(subset=[*feature_columns, *path_required]).copy()
    calibration = split.calibration.dropna(subset=[*feature_columns, *path_required]).copy()
    holdout = split.holdout.dropna(subset=[*feature_columns, *path_required]).copy()
    if train.empty or calibration.empty or holdout.empty:
        raise ValueError("Training, calibration, and holdout sets must be nonempty")
    feature_columns, mutual_information_summary = _mutual_information_screen(
        train,
        feature_columns,
        target,
        seed=config.random_seed,
        top_k=config.mutual_information_top_k,
    )

    x_train = train[feature_columns]
    y_train = train[target].astype(int)
    if y_train.nunique() < 2:
        raise ValueError("Training target contains only one class")
    classifier.fit(x_train, y_train)

    calibration_raw = _positive_class_probability(classifier, calibration[feature_columns])
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(calibration_raw, calibration[target].astype(int))
    calibration_probability = np.asarray(calibrator.predict(calibration_raw), dtype=float)
    holdout_raw = _positive_class_probability(classifier, holdout[feature_columns])
    holdout_probability = np.asarray(calibrator.predict(holdout_raw), dtype=float)

    target_train = split.train.dropna(subset=required).copy()
    target_screen = screen_features_for_target(
        target_train,
        target_train[target_before_stop],
        target_name=target_before_stop,
        head_name=TARGET_BEFORE_STOP_HEAD,
        direction=direction,
        horizon=horizon,
        task_type="classification",
        feature_family_by_column=feature_family_by_column,
        max_selected_features=config.mutual_information_top_k,
        random_seed=config.random_seed,
        missingness_threshold=0.40,
        variance_threshold=1e-12,
        correlation_threshold=config.correlation_threshold,
    )
    target_feature_columns = target_screen.selected_features
    if not target_feature_columns:
        raise ValueError("Target-before-stop feature screen selected no features")
    target_classifier = clone(classifier)
    target_y = target_train[target_before_stop].astype(int)
    if target_y.nunique() < 2:
        target_classifier = BaseRateClassifier()
    target_classifier.fit(target_train[list(target_feature_columns)], target_y)
    target_calibration_raw = _positive_class_probability(
        target_classifier, calibration[list(target_feature_columns)]
    )
    target_calibration_selection = select_tbs_calibrator(
        raw_probability=target_calibration_raw,
        target=calibration[target_before_stop].astype(int).to_numpy(),
        dates=calibration["Date"],
        random_seed=config.random_seed,
    )
    target_calibrator = target_calibration_selection.selected_calibrator
    target_calibration_probability = np.asarray(
        target_calibrator.predict(target_calibration_raw), dtype=float
    )
    target_holdout_raw = _positive_class_probability(
        target_classifier, holdout[list(target_feature_columns)]
    )
    target_holdout_probability = np.asarray(
        target_calibrator.predict(target_holdout_raw), dtype=float
    )
    target_calibration_probability_audit = build_probability_audit_frame(
        calibration_frame=calibration,
        development_holdout_frame=holdout,
        calibration_raw_probability=target_calibration_raw,
        calibration_calibrated_probability=target_calibration_probability,
        development_holdout_raw_probability=target_holdout_raw,
        development_holdout_calibrated_probability=target_holdout_probability,
        target_column=target_before_stop,
        selection=target_calibration_selection,
        model_id=model_id,
        direction=direction,
        horizon=horizon,
    )
    target_calibration_threshold_utility = calibration_threshold_utility(
        frame=calibration,
        calibrated_probability=target_calibration_probability,
        direction=direction,
        horizon=horizon,
        model_id=model_id,
    )
    target_calibration_audit = write_calibration_audit_artifacts(
        audit_dir=calibration_audit_dir,
        selection=target_calibration_selection,
        probability_audit=target_calibration_probability_audit,
        threshold_utility=target_calibration_threshold_utility,
        model_id=model_id,
        direction=direction,
        horizon=horizon,
    )

    plugin_by_name = {plugin.name: plugin for plugin in model_plugins()}
    plugin = plugin_by_name[family]
    path_screen_train = split.train.dropna(subset=path_required).copy()
    path_train_atr = _path_atr_values(path_screen_train)
    calibration_atr = _path_atr_values(calibration)
    holdout_atr = _path_atr_values(holdout)
    return_atr_train = _path_atr_training_target(
        path_screen_train[returns],
        path_train_atr,
        head_name=EXPECTED_RETURN_HEAD,
        external_target_name=returns,
    )
    mfe_magnitude_train = _path_atr_training_target(
        path_screen_train[mfe],
        path_train_atr,
        head_name=MFE_HEAD,
        external_target_name=mfe,
    )
    mae_magnitude_train = _path_atr_training_target(
        path_screen_train[mae],
        path_train_atr,
        head_name=MAE_HEAD,
        external_target_name=mae,
    )
    return_atr_calibration = _path_atr_training_target(
        calibration[returns],
        calibration_atr,
        head_name=EXPECTED_RETURN_HEAD,
        external_target_name=returns,
    )
    mfe_atr_calibration = _path_atr_training_target(
        calibration[mfe],
        calibration_atr,
        head_name=MFE_HEAD,
        external_target_name=mfe,
    )
    mae_atr_calibration = _path_atr_training_target(
        calibration[mae],
        calibration_atr,
        head_name=MAE_HEAD,
        external_target_name=mae,
    )
    return_atr_holdout = _path_atr_training_target(
        holdout[returns],
        holdout_atr,
        head_name=EXPECTED_RETURN_HEAD,
        external_target_name=returns,
    )
    mfe_atr_holdout = _path_atr_training_target(
        holdout[mfe],
        holdout_atr,
        head_name=MFE_HEAD,
        external_target_name=mfe,
    )
    mae_atr_holdout = _path_atr_training_target(
        holdout[mae],
        holdout_atr,
        head_name=MAE_HEAD,
        external_target_name=mae,
    )
    return_normalization_metadata = _path_target_normalization_metadata(
        head_name=EXPECTED_RETURN_HEAD,
        external_target_name=returns,
        internal_target_name=str(return_atr_train.name),
        direction=direction,
        horizon=horizon,
    )
    mfe_normalization_metadata = _path_target_normalization_metadata(
        head_name=MFE_HEAD,
        external_target_name=mfe,
        internal_target_name=str(mfe_magnitude_train.name),
        direction=direction,
        horizon=horizon,
    )
    mae_normalization_metadata = _path_target_normalization_metadata(
        head_name=MAE_HEAD,
        external_target_name=mae,
        internal_target_name=str(mae_magnitude_train.name),
        direction=direction,
        horizon=horizon,
    )
    return_screen = _screen_path_metric_head(
        training_frame=path_screen_train,
        target=return_atr_train,
        target_name=str(return_atr_train.name),
        head_name=EXPECTED_RETURN_HEAD,
        direction=direction,
        horizon=horizon,
        feature_family_by_column=feature_family_by_column,
        config=config,
        seed_offset=10,
    )
    mfe_screen = _screen_path_metric_head(
        training_frame=path_screen_train,
        target=mfe_magnitude_train,
        target_name=str(mfe_magnitude_train.name),
        head_name=MFE_HEAD,
        direction=direction,
        horizon=horizon,
        feature_family_by_column=feature_family_by_column,
        config=config,
        seed_offset=11,
    )
    mae_screen = _screen_path_metric_head(
        training_frame=path_screen_train,
        target=mae_magnitude_train,
        target_name=str(mae_magnitude_train.name),
        head_name=MAE_HEAD,
        direction=direction,
        horizon=horizon,
        feature_family_by_column=feature_family_by_column,
        config=config,
        seed_offset=12,
    )
    return_feature_columns = return_screen.selected_features
    mfe_feature_columns = mfe_screen.selected_features
    mae_feature_columns = mae_screen.selected_features
    return_model = plugin.regressor_factory(config.random_seed)
    mfe_retired = _should_retire_path_head(family, MFE_HEAD)
    mae_retired = _should_retire_path_head(family, MAE_HEAD)
    mfe_model: Any
    mae_model: Any
    mfe_estimator_spec: PathMagnitudeEstimatorSpec | None = None
    mae_estimator_spec: PathMagnitudeEstimatorSpec | None = None
    if mfe_retired:
        mfe_model = RetiredPathHeadModel(family=family, head_name=MFE_HEAD)
    else:
        mfe_model, mfe_estimator_spec = build_path_magnitude_estimator(
            family=family,
            head_name=MFE_HEAD,
            seed=config.random_seed + 1,
        )
    if mae_retired:
        mae_model = RetiredPathHeadModel(family=family, head_name=MAE_HEAD)
    else:
        mae_model, mae_estimator_spec = build_path_magnitude_estimator(
            family=family,
            head_name=MAE_HEAD,
            seed=config.random_seed + 2,
        )
    return_model.fit(path_screen_train[list(return_feature_columns)], return_atr_train)
    mfe_train_features = path_screen_train[list(mfe_feature_columns)]
    mae_train_features = path_screen_train[list(mae_feature_columns)]
    _validate_path_magnitude_training_target(
        feature_frame=mfe_train_features,
        magnitude_target=mfe_magnitude_train,
        head_name=MFE_HEAD,
    )
    _validate_path_magnitude_training_target(
        feature_frame=mae_train_features,
        magnitude_target=mae_magnitude_train,
        head_name=MAE_HEAD,
    )
    if not mfe_retired:
        mfe_model.fit(mfe_train_features, mfe_magnitude_train)
    if not mae_retired:
        mae_model.fit(mae_train_features, mae_magnitude_train)
    calibration_return_prediction = _path_target_prediction(
        return_model,
        calibration[list(return_feature_columns)],
        atr_values=calibration_atr,
        index=calibration.index,
    )
    calibration_mfe_prediction = (
        _retired_path_prediction(calibration.index, head_name=MFE_HEAD)
        if mfe_retired
        else _path_magnitude_prediction(
            mfe_model,
            calibration[list(mfe_feature_columns)],
            head_name=MFE_HEAD,
            index=calibration.index,
            atr_values=calibration_atr,
        )
    )
    calibration_mae_prediction = (
        _retired_path_prediction(calibration.index, head_name=MAE_HEAD)
        if mae_retired
        else _path_magnitude_prediction(
            mae_model,
            calibration[list(mae_feature_columns)],
            head_name=MAE_HEAD,
            index=calibration.index,
            atr_values=calibration_atr,
        )
    )
    holdout_return_prediction = _path_target_prediction(
        return_model,
        holdout[list(return_feature_columns)],
        atr_values=holdout_atr,
        index=holdout.index,
    )
    expected_return = holdout_return_prediction.canonical_external
    holdout_mfe_prediction = (
        _retired_path_prediction(holdout.index, head_name=MFE_HEAD)
        if mfe_retired
        else _path_magnitude_prediction(
            mfe_model,
            holdout[list(mfe_feature_columns)],
            head_name=MFE_HEAD,
            index=holdout.index,
            atr_values=holdout_atr,
        )
    )
    holdout_mae_prediction = (
        _retired_path_prediction(holdout.index, head_name=MAE_HEAD)
        if mae_retired
        else _path_magnitude_prediction(
            mae_model,
            holdout[list(mae_feature_columns)],
            head_name=MAE_HEAD,
            index=holdout.index,
            atr_values=holdout_atr,
        )
    )
    expected_mfe = holdout_mfe_prediction.canonical_signed
    expected_mae = holdout_mae_prediction.canonical_signed
    selection_policy = selection_policy_from_config(config)
    selected_mask = _apply_selection_policy(
        holdout,
        probability=holdout_probability,
        expected_return=expected_return,
        target_before_stop_probability=target_holdout_probability,
        policy=selection_policy,
    )
    selected = holdout.loc[selected_mask].copy()
    selected_returns = selected[returns] - (config.round_trip_cost_bps / 10_000.0)
    if selected_returns.empty:
        selected_returns = holdout[returns].head(0)

    calibration_brier = float(
        brier_score_loss(calibration[target].astype(int), calibration_probability)
    )
    holdout_brier = float(brier_score_loss(holdout[target].astype(int), holdout_probability))
    naive_probability = np.full(len(holdout), float(train[target].astype(float).mean()))
    naive_brier = (
        holdout_brier
        if family == "naive_base_rate"
        else float(brier_score_loss(holdout[target].astype(int), naive_probability))
    )
    brier_improvement = naive_brier - holdout_brier
    brier_skill_score = (
        float(1.0 - (holdout_brier / naive_brier))
        if math.isfinite(naive_brier) and naive_brier > 0
        else math.nan
    )
    try:
        holdout_log_loss = float(log_loss(holdout[target].astype(int), holdout_probability))
    except ValueError:
        holdout_log_loss = math.nan
    calibration_table = _calibration_table(holdout[target].astype(int), holdout_probability)
    calibration_intercept, calibration_slope = _calibration_intercept_slope(
        holdout[target].astype(int), holdout_probability
    )
    prediction_deciles = _prediction_deciles(holdout[returns], expected_return)
    permutation_summary = _permutation_importance_summary(
        classifier=classifier,
        calibrator=calibrator,
        holdout=holdout,
        feature_columns=feature_columns,
        target=target,
        baseline_brier=holdout_brier,
        seed=config.random_seed,
        limit=config.permutation_feature_limit,
    )
    target_before_stop_brier = float(
        brier_score_loss(holdout[target_before_stop].astype(int), target_holdout_probability)
    )
    target_before_stop_development_raw_quality = binary_probability_quality(
        holdout[target_before_stop].astype(int).to_numpy(),
        target_holdout_raw,
        target_holdout_raw,
        method="identity",
    )
    target_before_stop_development_calibrated_quality = binary_probability_quality(
        holdout[target_before_stop].astype(int).to_numpy(),
        target_holdout_raw,
        target_holdout_probability,
        method=target_calibration_selection.selected_method,
    )
    target_before_stop_raw_distribution = probability_distribution_summary(target_holdout_raw)
    target_before_stop_calibrated_distribution = probability_distribution_summary(
        target_holdout_probability
    )
    target_before_stop_permutation_by_family = _permutation_importance_by_family(
        classifier=target_classifier,
        calibrator=target_calibrator,
        holdout=holdout,
        feature_columns=target_feature_columns,
        feature_family_by_column=feature_family_by_column,
        target=target_before_stop,
        baseline_brier=target_before_stop_brier,
        seed=config.random_seed,
    )
    target_before_stop_permutation_top = "; ".join(
        f"{record['family']}={float(record['positive_sum_delta_brier']):.6f}"
        for record in sorted(
            target_before_stop_permutation_by_family,
            key=lambda item: float(item["positive_sum_delta_brier"]),
            reverse=True,
        )[:8]
    )
    feature_stability_mean, feature_stability_top = _feature_stability_summary(
        train,
        holdout,
        feature_columns,
    )
    holdout_mae = _mean_absolute_error_or_nan(holdout[returns], expected_return)
    holdout_rmse = _rmse_or_nan(holdout[returns], expected_return)
    holdout_mfe_mae = _mean_absolute_error_or_nan(holdout[mfe], expected_mfe)
    holdout_mfe_rmse = _rmse_or_nan(holdout[mfe], expected_mfe)
    holdout_mae_mae = _mean_absolute_error_or_nan(holdout[mae], expected_mae)
    holdout_mae_rmse = _rmse_or_nan(holdout[mae], expected_mae)
    path_permutation_by_head = {
        EXPECTED_RETURN_HEAD: _regression_permutation_importance_by_family(
            regressor=return_model,
            holdout=holdout,
            feature_columns=return_feature_columns,
            feature_family_by_column=feature_family_by_column,
            target=returns,
            baseline_mae=holdout_mae,
            seed=config.random_seed + 30,
            prediction_scale=holdout_atr,
        ),
        MFE_HEAD: []
        if mfe_retired
        else _regression_permutation_importance_by_family(
            regressor=mfe_model,
            holdout=holdout,
            feature_columns=mfe_feature_columns,
            feature_family_by_column=feature_family_by_column,
            target=mfe,
            baseline_mae=holdout_mfe_mae,
            seed=config.random_seed + 31,
            prediction_sign=1.0,
            prediction_scale=holdout_atr,
        ),
        MAE_HEAD: []
        if mae_retired
        else _regression_permutation_importance_by_family(
            regressor=mae_model,
            holdout=holdout,
            feature_columns=mae_feature_columns,
            feature_family_by_column=feature_family_by_column,
            target=mae,
            baseline_mae=holdout_mae_mae,
            seed=config.random_seed + 32,
            prediction_sign=-1.0,
            prediction_scale=holdout_atr,
        ),
    }
    mean_selected_return = (
        float(selected_returns.mean()) if not selected_returns.empty else math.nan
    )
    lower_bound = mean_selected_return
    if len(selected_returns) > 1:
        lower_bound = mean_selected_return - (
            1.645 * float(selected_returns.std(ddof=1)) / math.sqrt(len(selected_returns))
        )
    pf_selected_count, pf_gross_profit, pf_gross_loss_abs, pf_zero_count = (
        _profit_factor_components(selected_returns)
    )
    profit_factor_evidence = profit_factor_result(
        selected_count=pf_selected_count,
        positive_return_sum=pf_gross_profit,
        negative_return_abs_sum=pf_gross_loss_abs,
        zero_return_count=pf_zero_count,
        naive_control=family == "naive_base_rate",
        threshold=0.90,
    )
    if profit_factor_evidence.evidence_status == "AVAILABLE":
        holdout_profit_factor = (
            GATE_VALUE_POSITIVE_INFINITY
            if profit_factor_evidence.actual_value == math.inf
            else profit_factor_evidence.actual_value
        )
    else:
        holdout_profit_factor = GATE_VALUE_NOT_AVAILABLE
    selected_row_sequence_drawdown = _max_drawdown(selected_returns)
    double_cost_returns = selected[returns] - ((config.round_trip_cost_bps * 2.0) / 10_000.0)
    double_cost_lcb = (
        float(double_cost_returns.mean())
        if len(double_cost_returns) <= 1
        else float(double_cost_returns.mean())
        - (1.645 * float(double_cost_returns.std(ddof=1)) / math.sqrt(len(double_cost_returns)))
    )
    year_fraction = math.nan
    if "Date" in selected.columns and not selected.empty:
        selected = selected.assign(_year=pd.to_datetime(selected["Date"]).dt.year.astype(str))
        year_fraction = _positive_group_fraction(selected, selected_returns, "_year")
    regime_fraction = _positive_group_fraction(selected, selected_returns, "market_regime_label")
    sector_fraction = _positive_group_fraction(selected, selected_returns, "sector")
    symbol_concentration = _max_concentration(selected, "symbol")
    sector_concentration = _max_concentration(selected, "sector")
    prediction_turnover = len(selected_returns) / len(holdout) if len(holdout) else math.nan
    temporal_fold_details = _temporal_fold_stability_details(
        selected,
        selected_returns,
        folds=TEMPORAL_FOLD_STABILITY_REQUESTED_FOLDS,
    )
    temporal_folds_requested = int(cast(int, temporal_fold_details["folds_requested"]))
    temporal_folds_evaluated = int(cast(int, temporal_fold_details["folds_evaluated"]))
    temporal_folds_with_selected = int(
        cast(int, temporal_fold_details["folds_with_selected_observations"])
    )
    temporal_selected_observations_per_fold = tuple(
        int(value)
        for value in cast(
            list[int],
            temporal_fold_details["selected_observations_per_fold"],
        )
    )
    temporal_fold = temporal_fold_stability_result(
        selected_count=pf_selected_count,
        folds_requested=temporal_folds_requested,
        folds_evaluated=temporal_folds_evaluated,
        folds_with_selected_observations=temporal_folds_with_selected,
        selected_observations_per_fold=temporal_selected_observations_per_fold,
        positive_fraction=temporal_fold_details["positive_fraction"],
        naive_control=family == "naive_base_rate",
        threshold=TEMPORAL_FOLD_STABILITY_THRESHOLD,
    )
    period_concentration = _period_concentration(selected, selected_returns)
    selection_metrics = _selection_diagnostics(
        holdout=holdout,
        selected=selected,
        horizon=horizon,
    )
    candidate_rows = _candidate_rows_for_portfolio(
        holdout=holdout,
        selected_mask=selected_mask,
        direction=direction,
        horizon=horizon,
        model_id=model_id,
        probability=holdout_probability,
        expected_return=expected_return,
        target_before_stop_probability=target_holdout_probability,
    )
    portfolio_config = PortfolioBacktestConfig(
        horizon=horizon,
        round_trip_cost_bps=config.round_trip_cost_bps,
        slippage_bps=config.slippage_bps,
        max_concurrent_positions=config.max_concurrent_positions,
        max_position_per_symbol=config.max_position_per_symbol,
        max_sector_fraction=config.max_sector_fraction,
        max_gross_exposure=config.max_gross_exposure,
        max_net_exposure=config.max_net_exposure,
    )
    portfolio = backtest_scanner_candidates(
        _portfolio_frames_from_modeling(full_frame),
        candidate_rows,
        config=portfolio_config,
    )
    portfolio_metrics = {f"portfolio_{key}": value for key, value in portfolio.metrics.items()}
    portfolio_max_drawdown = float(portfolio.metrics.get("max_drawdown", math.nan))
    selected_mean_mfe = float(selected[mfe].mean()) if not selected.empty else math.nan
    selected_mean_mae = float(selected[mae].mean()) if not selected.empty else math.nan
    prediction_metrics: dict[str, float | int | str | bool] = {}
    prediction_metrics.update(
        _prediction_sanity_metrics(
            name="return",
            direction=direction,
            horizon=horizon,
            train_target=return_atr_train,
            calibration_target=return_atr_calibration,
            holdout_target=return_atr_holdout,
            calibration_prediction=calibration_return_prediction.internal_atr_units,
            holdout_prediction=holdout_return_prediction.internal_atr_units,
        )
    )
    prediction_metrics.update(
        _prediction_sanity_metrics(
            name="mfe",
            direction=direction,
            horizon=horizon,
            train_target=mfe_magnitude_train,
            calibration_target=mfe_atr_calibration,
            holdout_target=mfe_atr_holdout,
            calibration_prediction=calibration_mfe_prediction.internal_magnitude,
            holdout_prediction=holdout_mfe_prediction.internal_magnitude,
        )
    )
    prediction_metrics.update(
        _prediction_sanity_metrics(
            name="mae",
            direction=direction,
            horizon=horizon,
            train_target=mae_magnitude_train,
            calibration_target=mae_atr_calibration,
            holdout_target=mae_atr_holdout,
            calibration_prediction=calibration_mae_prediction.internal_magnitude,
            holdout_prediction=holdout_mae_prediction.internal_magnitude,
        )
    )
    prediction_metrics.update(
        {
            "return_prediction_unit_contract": "decimal_return",
            "return_prediction_ood_unit_contract": "atr_units",
            "return_prediction_transform_method": PATH_TARGET_PREDICTION_MAPPING_VERSION,
            "return_prediction_path_metric_sign_valid": holdout_return_prediction.valid
            and calibration_return_prediction.valid,
            "mfe_prediction_unit_contract": "decimal_return",
            "mfe_prediction_ood_unit_contract": "atr_units",
            "mfe_prediction_transform_method": PATH_TARGET_PREDICTION_MAPPING_VERSION,
            "mfe_prediction_path_metric_sign_valid": bool(
                calibration_mfe_prediction.valid and holdout_mfe_prediction.valid
            ),
            "mae_prediction_unit_contract": "decimal_return",
            "mae_prediction_ood_unit_contract": "atr_units",
            "mae_prediction_transform_method": PATH_TARGET_PREDICTION_MAPPING_VERSION,
            "mae_prediction_path_metric_sign_valid": bool(
                calibration_mae_prediction.valid and holdout_mae_prediction.valid
            ),
        }
    )
    prediction_metrics.update(calibration_return_prediction.diagnostics("return_calibration"))
    prediction_metrics.update(holdout_return_prediction.diagnostics("return_holdout"))
    prediction_metrics.update(
        probability_contract_metrics(
            calibration_probability=calibration_probability,
            holdout_probability=holdout_probability,
            target_calibration_probability=target_calibration_probability,
            target_holdout_probability=target_holdout_probability,
        )
    )
    prediction_ood_total = int(
        int(prediction_metrics.get("return_prediction_ood_count") or 0)
        + int(prediction_metrics.get("mfe_prediction_ood_count") or 0)
        + int(prediction_metrics.get("mae_prediction_ood_count") or 0)
    )
    regression_finite = all(
        bool(prediction_metrics.get(f"{head}_prediction_values_finite"))
        for head in REGRESSION_HEADS
    )
    head_mapping_valid = all(
        bool(prediction_metrics.get(f"{head}_prediction_head_bound_mapping_valid"))
        for head in REGRESSION_HEADS
    )
    training_bounds_only = all(
        bool(prediction_metrics.get(f"{head}_prediction_bounds_training_only"))
        for head in REGRESSION_HEADS
    )
    path_metric_sign_valid_result = all(
        bool(prediction_metrics.get(f"{head}_prediction_path_metric_sign_valid"))
        for head in REGRESSION_HEADS
    )
    selected_feature_family_counts: dict[str, int] = {}
    for column in feature_columns:
        family_name = feature_family_by_column.get(column, "unknown")
        selected_feature_family_counts[family_name] = (
            selected_feature_family_counts.get(family_name, 0) + 1
        )
    target_feature_family_counts = target_screen.selected_feature_families
    path_screens = {
        EXPECTED_RETURN_HEAD: return_screen,
        MFE_HEAD: mfe_screen,
        MAE_HEAD: mae_screen,
    }
    head_feature_columns = {
        PRIMARY_HEAD: tuple(feature_columns),
        TARGET_BEFORE_STOP_HEAD: tuple(target_feature_columns),
        EXPECTED_RETURN_HEAD: tuple(return_feature_columns),
        MFE_HEAD: tuple(mfe_feature_columns),
        MAE_HEAD: tuple(mae_feature_columns),
    }
    head_feature_manifests = {
        PRIMARY_HEAD: configuration_hash(
            {
                "head": PRIMARY_HEAD,
                "features": list(feature_columns),
                "legacy_screen": "primary_positive_return_existing_v1",
            }
        ),
        TARGET_BEFORE_STOP_HEAD: target_screen.selected_feature_manifest_hash,
        EXPECTED_RETURN_HEAD: return_screen.selected_feature_manifest_hash,
        MFE_HEAD: mfe_screen.selected_feature_manifest_hash,
        MAE_HEAD: mae_screen.selected_feature_manifest_hash,
    }
    feature_screen_metadata = {
        TARGET_BEFORE_STOP_HEAD: {
            **target_screen.metadata(),
            "direction": direction,
            "horizon": horizon,
        },
        EXPECTED_RETURN_HEAD: {
            **return_screen.metadata(),
            **return_normalization_metadata,
            "external_target_name": returns,
            "internal_target_definition": _path_internal_target_definition(EXPECTED_RETURN_HEAD),
        },
        MFE_HEAD: {
            **mfe_screen.metadata(),
            **mfe_normalization_metadata,
            "external_target_name": mfe,
            "internal_target_definition": _path_internal_target_definition(MFE_HEAD),
            "internal_magnitude_target_name": str(mfe_magnitude_train.name),
        },
        MAE_HEAD: {
            **mae_screen.metadata(),
            **mae_normalization_metadata,
            "external_target_name": mae,
            "internal_target_definition": _path_internal_target_definition(MAE_HEAD),
            "internal_magnitude_target_name": str(mae_magnitude_train.name),
        },
    }
    feature_screen_records = {
        TARGET_BEFORE_STOP_HEAD: tuple(target_screen.audit_records()),
        EXPECTED_RETURN_HEAD: tuple(return_screen.audit_records()),
        MFE_HEAD: tuple(mfe_screen.audit_records()),
        MAE_HEAD: tuple(mae_screen.audit_records()),
    }
    path_domain_metadata = {
        MFE_HEAD: _retired_path_domain_metadata(
            family=family,
            head_name=MFE_HEAD,
            external_target_name=mfe,
            magnitude_target=mfe_magnitude_train,
            selected_feature_manifest_hash=head_feature_manifests[MFE_HEAD],
            calibration_prediction=calibration_mfe_prediction,
            holdout_prediction=holdout_mfe_prediction,
            target_normalization_metadata=mfe_normalization_metadata,
        )
        if mfe_retired
        else _path_domain_metadata(
            head_name=MFE_HEAD,
            external_target_name=mfe,
            magnitude_target=mfe_magnitude_train,
            estimator=mfe_model,
            spec=cast(PathMagnitudeEstimatorSpec, mfe_estimator_spec),
            selected_feature_manifest_hash=head_feature_manifests[MFE_HEAD],
            calibration_prediction=calibration_mfe_prediction,
            holdout_prediction=holdout_mfe_prediction,
            target_normalization_metadata=mfe_normalization_metadata,
        ),
        MAE_HEAD: _retired_path_domain_metadata(
            family=family,
            head_name=MAE_HEAD,
            external_target_name=mae,
            magnitude_target=mae_magnitude_train,
            selected_feature_manifest_hash=head_feature_manifests[MAE_HEAD],
            calibration_prediction=calibration_mae_prediction,
            holdout_prediction=holdout_mae_prediction,
            target_normalization_metadata=mae_normalization_metadata,
        )
        if mae_retired
        else _path_domain_metadata(
            head_name=MAE_HEAD,
            external_target_name=mae,
            magnitude_target=mae_magnitude_train,
            estimator=mae_model,
            spec=cast(PathMagnitudeEstimatorSpec, mae_estimator_spec),
            selected_feature_manifest_hash=head_feature_manifests[MAE_HEAD],
            calibration_prediction=calibration_mae_prediction,
            holdout_prediction=holdout_mae_prediction,
            target_normalization_metadata=mae_normalization_metadata,
        ),
    }
    portfolio_policy_hash = configuration_hash(asdict(portfolio_config))
    selection_policy_hash = configuration_hash(asdict(selection_policy))
    config_hash = configuration_hash(
        {
            "discovery": asdict(config),
            "selection_policy": asdict(selection_policy),
            "portfolio_policy": asdict(portfolio_config),
        }
    )
    path_domain_metric_payload: dict[str, float | int | str | bool | None] = {}
    for head_name, metadata in path_domain_metadata.items():
        path_domain_metric_payload.update(
            _path_domain_metric_payload(head_name=head_name, metadata=metadata)
        )
    path_screen_metric_payload: dict[str, float | int | str | bool | None] = {}
    for head_name, screen in path_screens.items():
        metric_key = PATH_HEAD_TARGET_METRIC_KEYS[head_name]
        head_metadata = feature_screen_metadata.get(head_name, screen.metadata())
        permutation_by_family = path_permutation_by_head[head_name]
        permutation_top = "; ".join(
            f"{record['family']}={float(record['positive_sum_delta_mae']):.6f}"
            for record in sorted(
                permutation_by_family,
                key=lambda item: float(item["positive_sum_delta_mae"]),
                reverse=True,
            )[:8]
        )
        path_screen_metric_payload.update(
            {
                f"{metric_key}_feature_screen_schema_version": screen.spec.schema_version,
                f"{metric_key}_screening_target": screen.spec.target_name,
                f"{metric_key}_screening_task_type": screen.spec.task_type,
                f"{metric_key}_screening_manifest_hash": screen.selected_feature_manifest_hash,
                f"{metric_key}_screening_configuration_hash": screen.spec.configuration_hash,
                f"{metric_key}_selected_feature_count": len(screen.selected_features),
                f"{metric_key}_selected_features_json": _json_dumps(list(screen.selected_features)),
                f"{metric_key}_selected_feature_family_counts_json": _json_dumps(
                    screen.selected_feature_families
                ),
                f"{metric_key}_selected_feature_scores_json": _json_dumps(screen.selected_scores),
                f"{metric_key}_feature_screen_metadata_json": _json_dumps(head_metadata),
                f"{metric_key}_feature_screen_audit_json": _json_dumps(screen.audit_records()),
                f"{metric_key}_top_25_train_mi_features_json": _json_dumps(
                    _screen_top_features(screen, limit=25)
                ),
                f"{metric_key}_permutation_importance_by_family_json": _json_dumps(
                    permutation_by_family
                ),
                f"{metric_key}_permutation_importance_top": permutation_top,
            }
        )
        path_screen_metric_payload.update(
            _path_target_normalization_metric_payload(
                head_name=head_name,
                metadata=head_metadata,
            )
        )
    metrics: dict[str, float | int | str | bool | None] = {
        "training_samples": len(train),
        "calibration_samples": len(calibration),
        "holdout_samples": len(holdout),
        "holdout_status": DEVELOPMENT_HOLDOUT_STATUS,
        "holdout_status_reason": (
            "This chronological holdout has been repeatedly inspected during engineering "
            "diagnosis and is not a pristine final validation holdout."
        ),
        "selected_holdout_samples": len(selected_returns),
        "raw_data_first_date": _date_label(pd.Timestamp(full_frame["Date"].min())),
        "feature_warmup_first_date": _date_label(pd.Timestamp(full_frame["Date"].min())),
        "model_eligible_first_date": _date_label(pd.Timestamp(split.train["Date"].min())),
        "research_start": config.research_start,
        "research_end": _research_end(full_frame, config),
        "holdout_win_rate": float((selected_returns > 0).mean())
        if not selected_returns.empty
        else math.nan,
        "holdout_mean_net_return": mean_selected_return,
        "holdout_median_net_return": float(selected_returns.median())
        if not selected_returns.empty
        else math.nan,
        "holdout_mean_return_lcb_90": lower_bound,
        "holdout_profit_factor": holdout_profit_factor,
        "holdout_profit_factor_evidence_status": profit_factor_evidence.evidence_status,
        "holdout_positive_return_sum": pf_gross_profit,
        "holdout_negative_return_abs_sum": pf_gross_loss_abs,
        "holdout_zero_return_count": pf_zero_count,
        "selected_row_sequence_drawdown": selected_row_sequence_drawdown,
        "holdout_max_drawdown": portfolio_max_drawdown,
        "portfolio_max_drawdown": portfolio_max_drawdown,
        "holdout_mae_return_model": holdout_mae,
        "holdout_rmse_return_model": holdout_rmse,
        "holdout_mae_mfe_model": holdout_mfe_mae,
        "holdout_rmse_mfe_model": holdout_mfe_rmse,
        "holdout_mae_mae_model": holdout_mae_mae,
        "holdout_rmse_mae_model": holdout_mae_rmse,
        "holdout_expected_return_mean": float(expected_return.mean()),
        "holdout_rank_correlation_predicted_realized_return": float(
            pd.Series(expected_return).corr(holdout[returns], method="spearman")
        ),
        "feature_stability_mean_abs_z": feature_stability_mean,
        "feature_stability_top": feature_stability_top,
        "permutation_importance_top": permutation_summary,
        "mutual_information_top": mutual_information_summary,
        "selected_feature_family_counts_json": _json_dumps(selected_feature_family_counts),
        "selection_policy_json": _json_dumps(asdict(selection_policy)),
        "selection_policy_configuration_hash": selection_policy_hash,
        "selection_probability_threshold": selection_policy.probability_threshold,
        "selection_expected_return_threshold": selection_policy.expected_return_threshold,
        "selection_target_before_stop_threshold": selection_policy.target_before_stop_threshold,
        "selection_top_n_limit": selection_policy.top_n_limit,
        "selection_per_date_limit": selection_policy.per_date_limit,
        "selection_liquidity_threshold": selection_policy.liquidity_threshold,
        "selection_rate_ceiling": selection_policy.selected_rate_ceiling,
        "portfolio_policy_json": _json_dumps(asdict(portfolio_config)),
        "portfolio_policy_configuration_hash": portfolio_policy_hash,
        "holdout_target_before_stop_brier": target_before_stop_brier,
        "holdout_target_before_stop_probability_mean": float(np.mean(target_holdout_probability)),
        "target_before_stop_development_holdout_label": "DEVELOPMENT HOLDOUT DIAGNOSTIC",
        "target_before_stop_calibration_governance_schema": TBS_CALIBRATION_GOVERNANCE_SCHEMA_VERSION,
        "target_before_stop_calibration_method": target_calibration_selection.selected_method,
        "target_before_stop_calibration_candidate_methods_json": _json_dumps(
            [candidate.method for candidate in target_calibration_selection.candidate_results]
        ),
        "target_before_stop_calibration_fold_definitions_json": _json_dumps(
            [asdict(item) for item in target_calibration_selection.fold_definitions]
        ),
        "target_before_stop_calibration_fold_results_json": _json_dumps(
            [asdict(item) for item in target_calibration_selection.fold_results]
        ),
        "target_before_stop_calibration_candidate_results_json": _json_dumps(
            [asdict(item) for item in target_calibration_selection.candidate_results]
        ),
        "target_before_stop_calibration_one_standard_error_boundary": (
            target_calibration_selection.one_standard_error_boundary
        ),
        "target_before_stop_calibration_method_complexity_order_json": _json_dumps(
            list(target_calibration_selection.method_complexity_order)
        ),
        "target_before_stop_calibration_selection_reason": (
            target_calibration_selection.selection_reason
        ),
        "target_before_stop_calibration_final_fit_start": (
            target_calibration_selection.final_fit_start
        ),
        "target_before_stop_calibration_final_fit_end": target_calibration_selection.final_fit_end,
        "target_before_stop_calibration_final_fit_rows": target_calibration_selection.final_fit_rows,
        "target_before_stop_calibration_audit_probability_path": (
            target_calibration_audit.probability_audit_path
        ),
        "target_before_stop_calibration_method_comparison_path": (
            target_calibration_audit.method_comparison_path
        ),
        "target_before_stop_calibration_fold_metrics_path": (
            target_calibration_audit.fold_metrics_path
        ),
        "target_before_stop_calibration_step_support_path": (
            target_calibration_audit.step_support_path
        ),
        "target_before_stop_calibration_threshold_utility_path": (
            target_calibration_audit.threshold_utility_path
        ),
        "target_before_stop_calibration_governance_json_path": (
            target_calibration_audit.governance_json_path
        ),
        "target_before_stop_calibration_manifest_hash": (
            target_calibration_selection.calibration_manifest_hash
        ),
        "target_before_stop_calibrator_artifact_hash": (
            target_calibration_selection.calibrator_artifact_hash
        ),
        "target_before_stop_raw_score_distribution_json": _json_dumps(
            target_calibration_selection.raw_score_distribution
        ),
        "target_before_stop_calibrated_score_distribution_json": _json_dumps(
            target_calibration_selection.calibrated_score_distribution
        ),
        "target_before_stop_plateau_diagnostics_json": _json_dumps(
            target_calibration_selection.plateau_diagnostics
        ),
        "target_before_stop_step_support_json": _json_dumps(
            list(target_calibration_selection.step_support_records)
        ),
        "target_before_stop_identity_fold_brier": next(
            (
                candidate.mean_brier_score
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == "identity"
            ),
            math.nan,
        ),
        "target_before_stop_sigmoid_fold_brier": next(
            (
                candidate.mean_brier_score
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == "sigmoid"
            ),
            math.nan,
        ),
        "target_before_stop_isotonic_fold_brier": next(
            (
                candidate.mean_brier_score
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == "isotonic"
            ),
            math.nan,
        ),
        "target_before_stop_selected_method_brier": next(
            (
                candidate.mean_brier_score
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == target_calibration_selection.selected_method
            ),
            math.nan,
        ),
        "target_before_stop_selected_method_log_loss": next(
            (
                candidate.mean_log_loss
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == target_calibration_selection.selected_method
            ),
            math.nan,
        ),
        "target_before_stop_selected_method_ece": next(
            (
                candidate.mean_expected_calibration_error
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == target_calibration_selection.selected_method
            ),
            math.nan,
        ),
        "target_before_stop_selected_method_largest_plateau_percentage": next(
            (
                candidate.mean_largest_plateau_percentage
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == target_calibration_selection.selected_method
            ),
            math.nan,
        ),
        "target_before_stop_selected_method_minimum_step_support": next(
            (
                candidate.minimum_isotonic_step_support
                for candidate in target_calibration_selection.candidate_results
                if candidate.method == target_calibration_selection.selected_method
            ),
            math.nan,
        ),
        "target_before_stop_development_holdout_raw_quality_json": _json_dumps(
            target_before_stop_development_raw_quality
        ),
        "target_before_stop_development_holdout_calibrated_quality_json": _json_dumps(
            target_before_stop_development_calibrated_quality
        ),
        "target_before_stop_development_holdout_raw_distribution_json": _json_dumps(
            target_before_stop_raw_distribution
        ),
        "target_before_stop_development_holdout_calibrated_distribution_json": _json_dumps(
            target_before_stop_calibrated_distribution
        ),
        "target_before_stop_feature_screen_schema_version": FEATURE_SCREEN_SCHEMA_VERSION,
        "target_before_stop_screening_target": target_before_stop,
        "target_before_stop_screening_task_type": "classification",
        "target_before_stop_screening_manifest_hash": target_screen.selected_feature_manifest_hash,
        "target_before_stop_screening_configuration_hash": target_screen.spec.configuration_hash,
        "target_before_stop_selected_feature_count": len(target_feature_columns),
        "target_before_stop_selected_features_json": _json_dumps(list(target_feature_columns)),
        "target_before_stop_selected_feature_family_counts_json": _json_dumps(
            target_feature_family_counts
        ),
        "target_before_stop_selected_feature_scores_json": _json_dumps(
            target_screen.selected_scores
        ),
        "target_before_stop_feature_screen_metadata_json": _json_dumps(
            {
                **target_screen.metadata(),
                "direction": direction,
                "horizon": horizon,
            }
        ),
        "target_before_stop_feature_screen_audit_json": _json_dumps(target_screen.audit_records()),
        "target_before_stop_top_25_train_mi_features_json": _json_dumps(
            _screen_top_features(target_screen, limit=25)
        ),
        "target_before_stop_permutation_importance_by_family_json": _json_dumps(
            target_before_stop_permutation_by_family
        ),
        "target_before_stop_permutation_importance_top": target_before_stop_permutation_top,
        "head_feature_columns_json": _json_dumps(
            {head: list(columns) for head, columns in head_feature_columns.items()}
        ),
        "head_feature_manifest_hashes_json": _json_dumps(head_feature_manifests),
        "holdout_double_cost_lcb_90": double_cost_lcb,
        "selected_mean_mfe": selected_mean_mfe,
        "selected_mean_mae": selected_mean_mae,
        "positive_year_fraction": year_fraction,
        "positive_regime_fraction": regime_fraction,
        "positive_sector_fraction": sector_fraction,
        "symbol_concentration_top": symbol_concentration,
        "sector_concentration_top": sector_concentration,
        "prediction_turnover": prediction_turnover,
        "temporal_fold_schema_version": TEMPORAL_FOLD_STABILITY_SCHEMA_VERSION,
        "temporal_fold_folds_requested": temporal_folds_requested,
        "temporal_fold_folds_evaluated": temporal_folds_evaluated,
        "temporal_fold_folds_with_selected_observations": temporal_folds_with_selected,
        "temporal_fold_selected_observations_per_fold_json": _json_dumps(
            temporal_fold_details["selected_observations_per_fold"]
        ),
        "temporal_fold_records_json": _json_dumps(temporal_fold_details["fold_records"]),
        "temporal_fold_positive_fraction": temporal_fold.actual_value,
        "temporal_fold_evidence_status": temporal_fold.evidence_status,
        "temporal_fold_evidence_unavailable_reason": temporal_fold.evidence_unavailable_reason,
        "temporal_fold_threshold": TEMPORAL_FOLD_STABILITY_THRESHOLD,
        "temporal_fold_evidence_gate_status": temporal_fold.evidence_gate_status,
        "temporal_fold_threshold_gate_status": temporal_fold.threshold_gate_status,
        "exceptional_period_concentration_top": period_concentration,
        "rsi_control_columns_available": "rsi_14" in train.columns,
        "naive_control_family": family == "naive_base_rate",
        "model_plugin_name": plugin.name,
        "model_plugin_nonlinear_interactions": plugin.nonlinear_interactions,
        "prediction_unit_contract": "decimal_return",
        "prediction_ood_governance_version": PREDICTION_OOD_GOVERNANCE_VERSION,
        "prediction_values_finite": regression_finite
        and bool(prediction_metrics.get("classification_prediction_values_finite")),
        "prediction_probability_contract_valid": bool(
            prediction_metrics.get("classification_probability_contract_valid")
        ),
        "prediction_head_bound_mapping_valid": head_mapping_valid,
        "prediction_bounds_training_only": training_bounds_only,
        "prediction_path_metric_sign_valid": path_metric_sign_valid_result,
        "prediction_sanity_ood_total": prediction_ood_total,
        "prediction_ood_metadata_json": _json_dumps(
            bundle_ood_identity(
                {
                    "prediction_ood_governance_version": PREDICTION_OOD_GOVERNANCE_VERSION,
                    "prediction_unit_contract": "decimal_return",
                    **prediction_metrics,
                }
            )
        ),
        "calibration_table_json": _json_dumps(calibration_table),
        "predicted_vs_realized_return_deciles_json": _json_dumps(prediction_deciles),
        "portfolio_daily_equity_json": _json_dumps(portfolio.equity.to_dict(orient="records")),
        "portfolio_trade_ledger_json": _json_dumps(portfolio.trades.to_dict(orient="records")),
        "selected_candidate_ledger_json": _json_dumps(
            candidate_rows.loc[selected_mask].to_dict(orient="records")
        ),
        "candidate_ledger_rows": len(portfolio.trades),
        "candidate_audit_rows": len(portfolio.candidate_audit),
        **selection_metrics,
        **portfolio_metrics,
        **prediction_metrics,
        **path_domain_metric_payload,
        **path_screen_metric_payload,
    }
    calibration_metrics: dict[str, float | int | str | bool | None] = {
        "calibration_brier": calibration_brier,
        "holdout_brier": holdout_brier,
        "naive_brier": naive_brier,
        "absolute_brier_improvement": brier_improvement,
        "relative_brier_improvement": (brier_improvement / naive_brier)
        if math.isfinite(naive_brier) and naive_brier > 0
        else math.nan,
        "brier_skill_score": brier_skill_score,
        "holdout_log_loss": holdout_log_loss,
        "calibration_intercept": calibration_intercept,
        "calibration_slope": calibration_slope,
        "expected_calibration_error": _expected_calibration_error(calibration_table, len(holdout)),
        "classification_base_rate": float(holdout[target].astype(float).mean()),
        "calibration_probability_mean": float(np.mean(calibration_probability)),
        "holdout_probability_mean": float(np.mean(holdout_probability)),
    }
    gate_results = _build_gate_results(
        metrics=metrics,
        calibration_metrics=calibration_metrics,
        family=family,
        config=config,
        config_hash=config_hash,
    )
    medians = {column: float(x_train[column].median()) for column in feature_columns}
    means = {column: float(x_train[column].mean()) for column in feature_columns}
    stds = {
        column: float(x_train[column].std(ddof=0))
        if float(x_train[column].std(ddof=0)) > 0
        else 1.0
        for column in feature_columns
    }
    bundle = ModelBundle(
        model_id=model_id,
        direction=direction,
        horizon=horizon,
        family=family,
        feature_columns=tuple(feature_columns),
        feature_family_by_column={
            column: feature_family_by_column.get(column, "unknown")
            for column in tuple(
                dict.fromkeys(
                    [
                        *feature_columns,
                        *target_feature_columns,
                        *return_feature_columns,
                        *mfe_feature_columns,
                        *mae_feature_columns,
                    ]
                )
            )
        },
        classifier=classifier,
        calibrator=calibrator,
        target_before_stop_model=target_classifier,
        target_before_stop_calibrator=target_calibrator,
        return_model=return_model,
        mfe_model=mfe_model,
        mae_model=mae_model,
        training_medians=medians,
        training_means=means,
        training_stds=stds,
        training_matrix=x_train.reset_index(drop=True),
        training_labels=train[
            ["Date", "symbol", returns, mfe, mae, target_before_stop, PATH_TARGET_ATR_FEATURE]
        ].reset_index(drop=True),
        metrics=metrics,
        calibration_metrics=calibration_metrics,
        gate_results=gate_results,
        head_feature_columns=head_feature_columns,
        head_feature_manifests=head_feature_manifests,
        feature_screen_metadata=feature_screen_metadata,
        feature_screen_records=feature_screen_records,
        path_domain_metadata=path_domain_metadata,
    )
    return bundle


def load_model_bundle(path: str | Path) -> ModelBundle:
    loaded = joblib.load(path)
    if not isinstance(loaded, ModelBundle):
        raise ValueError("Model artifact is not a trusted autonomous scanner bundle")
    if not hasattr(loaded, "head_feature_columns"):
        object.__setattr__(loaded, "head_feature_columns", {})
    if not hasattr(loaded, "head_feature_manifests"):
        object.__setattr__(loaded, "head_feature_manifests", {})
    if not hasattr(loaded, "feature_screen_metadata"):
        object.__setattr__(loaded, "feature_screen_metadata", {})
    if not hasattr(loaded, "feature_screen_records"):
        object.__setattr__(loaded, "feature_screen_records", {})
    if not hasattr(loaded, "path_domain_metadata"):
        object.__setattr__(loaded, "path_domain_metadata", {})
    return loaded


def save_model_bundle(bundle: ModelBundle, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    joblib.dump(bundle, output)
    return output


def discover_models(
    frame: pd.DataFrame,
    *,
    db_path: str | Path,
    artifact_dir: str | Path,
    universe_snapshot_id: str,
    feature_manifest_hash: str,
    feature_family_by_column: dict[str, str],
    raw_manifest_hashes: tuple[str, ...] = (),
    config: DiscoveryConfig | None = None,
    code_root: str | Path | None = None,
) -> DiscoveryResult:
    config = config or DiscoveryConfig()
    registered: list[RegisteredModel] = []
    rejected: list[RegisteredModel] = []
    eligible_frame = eligible_modeling_frame(frame, config)
    if eligible_frame.empty:
        raise ValueError("No eligible modeling rows remain after applying research date bounds")
    research_end = pd.Timestamp(_research_end(frame, config))
    warmup_frame = frame.loc[pd.to_datetime(frame["Date"]) <= research_end].copy()
    feature_columns = _clean_feature_columns(
        eligible_frame,
        max_features=config.max_features,
        correlation_threshold=config.correlation_threshold,
    )
    created_at = datetime.now(UTC).isoformat()
    for horizon in config.horizons:
        split = chronological_train_calibration_holdout_split(eligible_frame, horizon=horizon)
        for direction in config.directions:
            for family, classifier in _candidate_pipelines(config.random_seed).items():
                model_id = make_model_id(
                    task="swing_direction_probability",
                    horizon=horizon,
                    direction=direction,
                    family=family,
                    universe_snapshot_id=universe_snapshot_id,
                    feature_manifest_hash=feature_manifest_hash,
                    created_at_utc=f"{created_at}|{family}|{direction}|{horizon}",
                )
                try:
                    bundle = _train_family(
                        model_id=model_id,
                        family=family,
                        classifier=classifier,
                        split=split,
                        full_frame=warmup_frame,
                        feature_columns=feature_columns,
                        feature_family_by_column=feature_family_by_column,
                        direction=direction,
                        horizon=horizon,
                        config=config,
                        calibration_audit_dir=Path(artifact_dir).parent / "calibration",
                    )
                except ValueError as exc:
                    model_id = make_model_id(
                        task="swing_direction_probability",
                        horizon=horizon,
                        direction=direction,
                        family=family,
                        universe_snapshot_id=universe_snapshot_id,
                        feature_manifest_hash=feature_manifest_hash,
                        created_at_utc=f"{created_at}|rejected|{exc}",
                    )
                    model = RegisteredModel(
                        model_id=model_id,
                        task="swing_direction_probability",
                        horizon=horizon,
                        direction=direction,
                        family=family,
                        state="REJECTED",
                        training_start="n/a",
                        training_end="n/a",
                        validation_start="n/a",
                        validation_end="n/a",
                        holdout_start="n/a",
                        holdout_end="n/a",
                        universe_snapshot_id=universe_snapshot_id,
                        feature_manifest_hash=feature_manifest_hash,
                        raw_manifest_hashes=raw_manifest_hashes,
                        hyperparameters={"reason": str(exc)},
                        metrics={},
                        calibration_metrics={},
                        quality_gates={"trainable": False},
                        gate_results=(),
                        artifact_path="",
                        code_commit_hash=current_commit_hash(code_root or Path.cwd()),
                        created_at_utc=created_at,
                    )
                    register_model(db_path, model)
                    rejected.append(model)
                    continue

                bundle = ModelBundle(
                    model_id=model_id,
                    direction=bundle.direction,
                    horizon=bundle.horizon,
                    family=bundle.family,
                    feature_columns=bundle.feature_columns,
                    feature_family_by_column=bundle.feature_family_by_column,
                    classifier=bundle.classifier,
                    calibrator=bundle.calibrator,
                    target_before_stop_model=bundle.target_before_stop_model,
                    target_before_stop_calibrator=bundle.target_before_stop_calibrator,
                    return_model=bundle.return_model,
                    mfe_model=bundle.mfe_model,
                    mae_model=bundle.mae_model,
                    training_medians=bundle.training_medians,
                    training_means=bundle.training_means,
                    training_stds=bundle.training_stds,
                    training_matrix=bundle.training_matrix,
                    training_labels=bundle.training_labels,
                    metrics=bundle.metrics,
                    calibration_metrics=bundle.calibration_metrics,
                    gate_results=bundle.gate_results,
                    head_feature_columns=bundle.head_feature_columns,
                    head_feature_manifests=bundle.head_feature_manifests,
                    feature_screen_metadata=bundle.feature_screen_metadata,
                    feature_screen_records=bundle.feature_screen_records,
                    path_domain_metadata=bundle.path_domain_metadata,
                )
                artifact_path = Path(artifact_dir) / f"{model_id}.joblib"
                save_model_bundle(bundle, artifact_path)
                eligibility = promotion_eligibility(bundle.gate_results)
                state: ModelState = "CHALLENGER" if eligibility.eligible else "CANDIDATE"
                model = RegisteredModel(
                    model_id=model_id,
                    task="swing_direction_probability",
                    horizon=horizon,
                    direction=direction,
                    family=family,
                    state=state,
                    training_start=split.train_start,
                    training_end=split.train_end,
                    validation_start=split.calibration_start,
                    validation_end=split.calibration_end,
                    holdout_start=split.holdout_start,
                    holdout_end=split.holdout_end,
                    universe_snapshot_id=universe_snapshot_id,
                    feature_manifest_hash=feature_manifest_hash,
                    raw_manifest_hashes=raw_manifest_hashes,
                    hyperparameters={
                        "family": family,
                        "max_features": config.max_features,
                        "research_start": config.research_start,
                        "research_end": _research_end(frame, config),
                        "selection_policy": asdict(selection_policy_from_config(config)),
                        "portfolio_policy": bundle.metrics.get("portfolio_policy_json"),
                    },
                    metrics=bundle.metrics,
                    calibration_metrics=bundle.calibration_metrics,
                    quality_gates=quality_gate_bool_map(bundle.gate_results),
                    gate_results=bundle.gate_results,
                    artifact_path=str(artifact_path),
                    code_commit_hash=current_commit_hash(code_root or Path.cwd()),
                    created_at_utc=created_at,
                )
                register_model(db_path, model)
                if state == "CHALLENGER":
                    registered.append(model)
                else:
                    registered.append(model)
    best = sorted(
        registered,
        key=lambda model: float(model.metrics.get("holdout_mean_return_lcb_90") or -math.inf),
        reverse=True,
    )
    return DiscoveryResult(
        registered_models=tuple(registered),
        rejected_models=tuple(rejected),
        best_challenger_id=best[0].model_id if best else None,
    )


def predict_bundle(bundle: ModelBundle, frame: pd.DataFrame) -> pd.DataFrame:
    primary_features = bundle_head_feature_columns(bundle, PRIMARY_HEAD)
    target_before_stop_features = bundle_head_feature_columns(bundle, TARGET_BEFORE_STOP_HEAD)
    expected_return_features = bundle_head_feature_columns(bundle, EXPECTED_RETURN_HEAD)
    mfe_features = bundle_head_feature_columns(bundle, MFE_HEAD)
    mae_features = bundle_head_feature_columns(bundle, MAE_HEAD)
    missing = [column for column in primary_features if column not in frame.columns]
    if missing:
        raise ValueError(f"Feature frame is missing required model columns: {missing[:5]}")
    x = frame[list(primary_features)]
    raw = _positive_class_probability(bundle.classifier, x)
    probability = np.asarray(bundle.calibrator.predict(raw), dtype=float)
    output = frame[["Date", "symbol"]].copy()
    output["direction"] = bundle.direction
    output["horizon"] = bundle.horizon
    output["model_id"] = bundle.model_id
    output["calibrated_probability"] = probability
    output["primary_feature_manifest_hash"] = bundle_head_feature_manifest(bundle, PRIMARY_HEAD)
    for head_name, output_prefix in (
        (EXPECTED_RETURN_HEAD, "expected_return"),
        (MFE_HEAD, "mfe"),
        (MAE_HEAD, "mae"),
    ):
        metadata = bundle_feature_screen_metadata(bundle, head_name)
        schema = str(
            metadata.get(
                "screening_schema_version",
                "legacy_shared_path_feature_screen",
            )
        )
        output[f"{output_prefix}_feature_manifest_hash"] = bundle_head_feature_manifest(
            bundle, head_name
        )
        output[f"{output_prefix}_feature_screen_schema"] = schema
        output[f"{output_prefix}_feature_screen_metadata_missing"] = (
            not bool(metadata) or schema != PATH_METRIC_FEATURE_SCREEN_SCHEMA_VERSION
        )
        target_normalization_metadata = _target_normalization_metadata_for_bundle(bundle, head_name)
        output[f"{output_prefix}_target_normalization_schema_version"] = str(
            target_normalization_metadata.get("target_normalization_schema_version") or ""
        )
        output[f"{output_prefix}_target_normalization_method"] = str(
            target_normalization_metadata.get("target_normalization_method") or ""
        )
        output[f"{output_prefix}_target_normalization_atr_feature_name"] = str(
            target_normalization_metadata.get("atr_feature_name") or ""
        )
        output[f"{output_prefix}_target_normalization_hash"] = str(
            target_normalization_metadata.get("target_normalization_hash") or ""
        )
        output[f"{output_prefix}_target_prediction_mapping_version"] = str(
            target_normalization_metadata.get("prediction_mapping_version") or ""
        )
        output[f"{output_prefix}_internal_target_name"] = str(
            target_normalization_metadata.get("internal_target_name") or ""
        )
        output[f"{output_prefix}_internal_target_unit"] = str(
            target_normalization_metadata.get("internal_target_unit") or ""
        )
        output[f"{output_prefix}_canonical_external_unit"] = str(
            target_normalization_metadata.get("canonical_external_unit") or ""
        )
    output["target_before_stop_feature_manifest_hash"] = bundle_head_feature_manifest(
        bundle, TARGET_BEFORE_STOP_HEAD
    )
    output["target_before_stop_feature_screen_schema"] = str(
        bundle_feature_screen_metadata(bundle, TARGET_BEFORE_STOP_HEAD).get(
            "screening_schema_version", "legacy_shared_feature_screen"
        )
    )
    tbs_feature_screen_schema = (
        str(output["target_before_stop_feature_screen_schema"].iloc[0])
        if len(output)
        else "legacy_shared_feature_screen"
    )
    tbs_calibration_metadata = bundle_tbs_calibration_metadata(bundle)
    output["target_before_stop_calibration_governance_schema"] = str(
        tbs_calibration_metadata.get("schema_version", "")
    )
    output["target_before_stop_calibration_method"] = str(
        tbs_calibration_metadata.get("method", "")
    )
    output["target_before_stop_calibration_manifest_hash"] = str(
        tbs_calibration_metadata.get("calibration_manifest_hash", "")
    )
    output["target_before_stop_calibrator_artifact_hash"] = str(
        tbs_calibration_metadata.get("calibrator_artifact_hash", "")
    )
    output["target_before_stop_calibration_metadata_missing"] = bool(
        tbs_feature_screen_schema == FEATURE_SCREEN_SCHEMA_VERSION and not tbs_calibration_metadata
    )
    missing_target_features = [
        column for column in target_before_stop_features if column not in frame.columns
    ]
    output["target_before_stop_required_feature_missing"] = bool(missing_target_features)
    output["target_before_stop_missing_features"] = ";".join(missing_target_features[:10])
    if missing_target_features:
        output["target_before_stop_raw_probability"] = np.full(len(frame), math.nan)
        output["target_before_stop_probability"] = np.full(len(frame), math.nan)
    else:
        target_x = frame[list(target_before_stop_features)]
        target_raw = _positive_class_probability(bundle.target_before_stop_model, target_x)
        output["target_before_stop_raw_probability"] = np.asarray(target_raw, dtype=float)
        output["target_before_stop_probability"] = np.asarray(
            bundle.target_before_stop_calibrator.predict(target_raw), dtype=float
        )

    path_atr_valid = False
    if PATH_TARGET_ATR_FEATURE in frame.columns:
        path_atr_numeric = pd.to_numeric(frame[PATH_TARGET_ATR_FEATURE], errors="coerce")
        path_atr_values = path_atr_numeric.to_numpy(dtype=float, na_value=np.nan)
        path_atr_valid = bool(np.isfinite(path_atr_values).all() and (path_atr_values > 0.0).all())

    def add_regression_prediction(
        output_column: str,
        metric_prefix: str,
        values: np.ndarray | None,
        missing_features: list[str],
        domain_metadata: dict[str, object] | None = None,
        domain_prediction: PathMagnitudePrediction | None = None,
        target_prediction: PathTargetPrediction | None = None,
        ood_values: np.ndarray | pd.Series | None = None,
    ) -> None:
        output[f"{output_column}_required_feature_missing"] = bool(missing_features)
        output[f"{output_column}_missing_features"] = ";".join(missing_features[:10])
        if metric_prefix in {"mfe", "mae"}:
            output[f"{metric_prefix}_required_feature_missing"] = bool(missing_features)
            output[f"{metric_prefix}_missing_features"] = ";".join(missing_features[:10])
            domain = domain_metadata or {}
            domain_schema = str(
                domain.get("domain_schema_version") or "legacy_unconstrained_path_metric_model"
            )
            capability_state = str(domain.get("path_head_capability_state") or "")
            if not capability_state and domain_schema == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION:
                capability_state = PATH_HEAD_CAPABILITY_ACTIVE
            output[f"{metric_prefix}_domain_schema_version"] = domain_schema
            output[f"{metric_prefix}_path_head_capability_state"] = capability_state
            output[f"{metric_prefix}_path_head_retirement_schema_version"] = str(
                domain.get("path_head_retirement_schema_version") or ""
            )
            output[f"{metric_prefix}_path_head_retirement_reason"] = str(
                domain.get("path_head_retirement_reason") or ""
            )
            output[f"{metric_prefix}_path_head_retired"] = (
                capability_state == PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
            )
            output[f"{metric_prefix}_domain_metadata_missing"] = (
                domain_schema != PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
            )
            output[f"{metric_prefix}_external_target_name"] = str(
                domain.get("external_target_name") or ""
            )
            output[f"{metric_prefix}_internal_magnitude_target_name"] = str(
                domain.get("internal_magnitude_target_name") or ""
            )
            output[f"{metric_prefix}_internal_target_definition"] = str(
                domain.get("internal_target_definition") or ""
            )
            output[f"{metric_prefix}_magnitude_estimator_class"] = str(
                domain.get("estimator_class") or ""
            )
            output[f"{metric_prefix}_magnitude_estimator_loss"] = str(
                domain.get("estimator_loss") or ""
            )
            output[f"{metric_prefix}_magnitude_estimator_hash"] = str(
                domain.get("estimator_hash") or ""
            )
            output[f"{metric_prefix}_prediction_mapping_version"] = str(
                domain.get("prediction_mapping_version") or ""
            )
        if values is None:
            numeric = np.full(len(frame), math.nan)
        else:
            numeric = np.asarray(values, dtype=float)
        output[output_column] = numeric
        output[f"{output_column}_raw"] = numeric
        output[f"{output_column}_transformed"] = numeric
        output[f"{output_column}_transform_method"] = str(
            bundle.metrics.get(f"{metric_prefix}_prediction_transform_method") or "none"
        )
        if target_prediction is not None:
            output[f"{output_column}_internal_atr_units"] = (
                target_prediction.internal_atr_units.to_numpy(dtype=float)
            )
            output[f"{output_column}_atr_pct_14"] = target_prediction.atr_values.to_numpy(
                dtype=float
            )
        low_value = bundle.metrics.get(f"{metric_prefix}_prediction_bound_low_train_q01")
        high_value = bundle.metrics.get(f"{metric_prefix}_prediction_bound_high_train_q99")
        ood_numeric = (
            np.asarray(ood_values, dtype=float)
            if ood_values is not None
            else np.asarray(numeric, dtype=float)
        )
        checks = [
            live_ood_check(metrics=bundle.metrics, head=metric_prefix, value=float(value))
            for value in ood_numeric
        ]
        try:
            if low_value is None or high_value is None:
                raise ValueError
            low = float(str(low_value))
            high = float(str(high_value))
        except (TypeError, ValueError):
            legacy_ood = np.full(len(numeric), False)
        else:
            legacy_ood = (ood_numeric < low) | (ood_numeric > high)
        output[f"{output_column}_out_of_distribution"] = legacy_ood
        output[f"{output_column}_ood_warning"] = legacy_ood
        output[f"{output_column}_ood_severity"] = [check.severity for check in checks]
        output[f"{output_column}_ood_bound_low"] = [check.lower_bound for check in checks]
        output[f"{output_column}_ood_bound_high"] = [check.upper_bound for check in checks]
        output[f"{output_column}_ood_robust_range"] = [check.robust_range for check in checks]
        output[f"{output_column}_ood_severity_limit"] = [check.severity_limit for check in checks]
        output[f"{output_column}_ood_rate_limit"] = [check.rate_limit for check in checks]
        output[f"{output_column}_ood_governance_version"] = [
            check.governance_version for check in checks
        ]
        output[f"{output_column}_ood_metadata_missing"] = [
            check.metadata_missing for check in checks
        ]
        if metric_prefix == "mfe":
            output[f"{output_column}_sign_contract_valid"] = numeric >= 0.0
        elif metric_prefix == "mae":
            output[f"{output_column}_sign_contract_valid"] = numeric <= 0.0
        else:
            output[f"{output_column}_sign_contract_valid"] = True
        if metric_prefix in {"mfe", "mae"}:
            if domain_prediction is None:
                magnitude = np.full(len(frame), math.nan)
                magnitude_nonfinite = np.full(len(frame), False)
                magnitude_violation = np.full(len(frame), False)
            else:
                magnitude = domain_prediction.internal_magnitude.to_numpy(dtype=float)
                magnitude_nonfinite = ~np.isfinite(magnitude)
                magnitude_violation = np.isfinite(magnitude) & (magnitude < 0.0)
            signed_nonfinite = ~np.isfinite(numeric)
            if metric_prefix == "mfe":
                signed_violation = np.isfinite(numeric) & (numeric < 0.0)
            else:
                signed_violation = np.isfinite(numeric) & (numeric > 0.0)
            output[f"{output_column}_internal_magnitude"] = magnitude
            output[f"{output_column}_internal_magnitude_atr_units"] = magnitude
            output[f"{output_column}_magnitude_prediction_invalid"] = (
                magnitude_nonfinite | magnitude_violation
            )
            output[f"{output_column}_signed_prediction_invalid"] = (
                signed_nonfinite | signed_violation
            )
            output[f"{output_column}_magnitude_domain_valid"] = ~(
                magnitude_nonfinite | magnitude_violation
            )
            output[f"{output_column}_signed_domain_valid"] = ~(signed_nonfinite | signed_violation)
            output[f"{output_column}_magnitude_domain_violation"] = magnitude_violation
            output[f"{output_column}_signed_domain_violation"] = signed_violation

    return_target_normalization = _target_normalization_metadata_for_bundle(
        bundle, EXPECTED_RETURN_HEAD
    )
    return_normalized = bool(return_target_normalization)
    expected_return_missing_features = [
        column for column in expected_return_features if column not in frame.columns
    ]
    if return_normalized and not path_atr_valid:
        expected_return_missing_features.append(PATH_TARGET_ATR_FEATURE)
    expected_return_missing_features = list(dict.fromkeys(expected_return_missing_features))
    return_prediction: PathTargetPrediction | None = None
    if expected_return_missing_features:
        expected_return_values = None
        expected_return_ood_values = None
    elif return_normalized:
        return_prediction = _path_target_prediction(
            bundle.return_model,
            frame[list(expected_return_features)],
            atr_values=_path_atr_values(frame),
            index=frame.index,
        )
        expected_return_values = return_prediction.canonical_external.to_numpy(dtype=float)
        expected_return_ood_values = return_prediction.internal_atr_units
    else:
        expected_return_values = bundle.return_model.predict(frame[list(expected_return_features)])
        expected_return_ood_values = expected_return_values
    add_regression_prediction(
        "expected_return",
        "return",
        expected_return_values,
        expected_return_missing_features,
        target_prediction=return_prediction,
        ood_values=expected_return_ood_values,
    )
    mfe_target_normalization = _target_normalization_metadata_for_bundle(bundle, MFE_HEAD)
    mfe_missing_features = [column for column in mfe_features if column not in frame.columns]
    if mfe_target_normalization and not path_atr_valid:
        mfe_missing_features.append(PATH_TARGET_ATR_FEATURE)
    mfe_missing_features = list(dict.fromkeys(mfe_missing_features))
    mfe_domain_metadata = bundle_path_domain_metadata(bundle, MFE_HEAD)
    mfe_retired = (
        str(mfe_domain_metadata.get("path_head_capability_state") or "")
        == PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
    )
    mfe_has_domain = (
        str(mfe_domain_metadata.get("domain_schema_version") or "")
        == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
    )
    mfe_domain_prediction: PathMagnitudePrediction | None = None
    mfe_ood_values: np.ndarray | pd.Series | None
    if mfe_missing_features:
        mfe_values = None
        mfe_ood_values = None
    elif mfe_retired:
        mfe_domain_prediction = _retired_path_prediction(frame.index, head_name=MFE_HEAD)
        mfe_values = mfe_domain_prediction.canonical_signed.to_numpy(dtype=float)
        mfe_ood_values = mfe_domain_prediction.internal_magnitude
    elif mfe_has_domain:
        mfe_domain_prediction = _path_magnitude_prediction(
            bundle.mfe_model,
            frame[list(mfe_features)],
            head_name=MFE_HEAD,
            index=frame.index,
            atr_values=_path_atr_values(frame) if mfe_target_normalization else None,
        )
        mfe_values = mfe_domain_prediction.canonical_signed.to_numpy(dtype=float)
        mfe_ood_values = (
            mfe_domain_prediction.internal_magnitude if mfe_target_normalization else mfe_values
        )
    else:
        mfe_values = bundle.mfe_model.predict(frame[list(mfe_features)])
        mfe_ood_values = mfe_values
    add_regression_prediction(
        "expected_mfe",
        "mfe",
        mfe_values,
        mfe_missing_features,
        domain_metadata=mfe_domain_metadata,
        domain_prediction=mfe_domain_prediction,
        ood_values=mfe_ood_values,
    )
    mae_target_normalization = _target_normalization_metadata_for_bundle(bundle, MAE_HEAD)
    mae_missing_features = [column for column in mae_features if column not in frame.columns]
    if mae_target_normalization and not path_atr_valid:
        mae_missing_features.append(PATH_TARGET_ATR_FEATURE)
    mae_missing_features = list(dict.fromkeys(mae_missing_features))
    mae_domain_metadata = bundle_path_domain_metadata(bundle, MAE_HEAD)
    mae_retired = (
        str(mae_domain_metadata.get("path_head_capability_state") or "")
        == PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
    )
    mae_has_domain = (
        str(mae_domain_metadata.get("domain_schema_version") or "")
        == PATH_MAGNITUDE_DOMAIN_SCHEMA_VERSION
    )
    mae_domain_prediction: PathMagnitudePrediction | None = None
    mae_ood_values: np.ndarray | pd.Series | None
    if mae_missing_features:
        mae_values = None
        mae_ood_values = None
    elif mae_retired:
        mae_domain_prediction = _retired_path_prediction(frame.index, head_name=MAE_HEAD)
        mae_values = mae_domain_prediction.canonical_signed.to_numpy(dtype=float)
        mae_ood_values = mae_domain_prediction.internal_magnitude
    elif mae_has_domain:
        mae_domain_prediction = _path_magnitude_prediction(
            bundle.mae_model,
            frame[list(mae_features)],
            head_name=MAE_HEAD,
            index=frame.index,
            atr_values=_path_atr_values(frame) if mae_target_normalization else None,
        )
        mae_values = mae_domain_prediction.canonical_signed.to_numpy(dtype=float)
        mae_ood_values = (
            mae_domain_prediction.internal_magnitude if mae_target_normalization else mae_values
        )
    else:
        mae_values = bundle.mae_model.predict(frame[list(mae_features)])
        mae_ood_values = mae_values
    add_regression_prediction(
        "expected_mae",
        "mae",
        mae_values,
        mae_missing_features,
        domain_metadata=mae_domain_metadata,
        domain_prediction=mae_domain_prediction,
        ood_values=mae_ood_values,
    )
    return output
