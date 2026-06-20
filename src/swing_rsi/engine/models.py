from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.feature_selection import mutual_info_classif
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from swing_rsi.engine.features import numeric_feature_columns, reject_label_columns
from swing_rsi.engine.manifest import current_commit_hash
from swing_rsi.engine.registry import ModelState, RegisteredModel, make_model_id, register_model
from swing_rsi.engine.splits import (
    ChronologicalSplit,
    chronological_train_calibration_holdout_split,
)


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
    random_seed: int = 42
    permutation_feature_limit: int = 12
    mutual_information_top_k: int = 60


@dataclass(frozen=True)
class DiscoveryResult:
    registered_models: tuple[RegisteredModel, ...]
    rejected_models: tuple[RegisteredModel, ...]
    best_challenger_id: str | None


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


def _candidate_pipelines(seed: int) -> dict[str, Any]:
    return {
        "naive_base_rate": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", BaseRateClassifier()),
            ]
        ),
        "logistic_regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(max_iter=500, class_weight="balanced", random_state=seed),
                ),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
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
        "extra_trees": Pipeline(
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
    }


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


def _profit_factor(returns: pd.Series) -> float:
    gains = float(returns[returns > 0].sum())
    losses = float(returns[returns < 0].sum())
    return gains / abs(losses) if losses < 0 else math.inf


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return math.nan
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    return float(((equity / equity.cummax()) - 1.0).min())


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


def _train_family(
    *,
    family: str,
    classifier: Any,
    split: ChronologicalSplit,
    feature_columns: list[str],
    direction: str,
    horizon: int,
    config: DiscoveryConfig,
) -> tuple[ModelBundle, dict[str, bool]]:
    target = f"label_{direction}_positive_return_{horizon}"
    returns = f"label_{direction}_forward_return_{horizon}"
    mfe = f"label_{direction}_mfe_{horizon}"
    mae = f"label_{direction}_mae_{horizon}"
    target_before_stop = f"label_{direction}_target_before_stop_{horizon}"
    required = [target, returns, mfe, mae, target_before_stop]
    train = split.train.dropna(subset=[*feature_columns, *required]).copy()
    calibration = split.calibration.dropna(subset=[*feature_columns, *required]).copy()
    holdout = split.holdout.dropna(subset=[*feature_columns, *required]).copy()
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

    target_classifier = clone(classifier)
    target_y = train[target_before_stop].astype(int)
    if target_y.nunique() < 2:
        target_classifier = BaseRateClassifier()
    target_classifier.fit(x_train, target_y)
    target_calibration_raw = _positive_class_probability(
        target_classifier, calibration[feature_columns]
    )
    target_calibrator = IsotonicRegression(out_of_bounds="clip")
    target_calibrator.fit(target_calibration_raw, calibration[target_before_stop].astype(int))
    target_holdout_raw = _positive_class_probability(target_classifier, holdout[feature_columns])
    target_holdout_probability = np.asarray(
        target_calibrator.predict(target_holdout_raw), dtype=float
    )

    return_model = _regressor(config.random_seed, family)
    mfe_model = _regressor(config.random_seed + 1, family)
    mae_model = _regressor(config.random_seed + 2, family)
    return_model.fit(x_train, train[returns])
    mfe_model.fit(x_train, train[mfe])
    mae_model.fit(x_train, train[mae])
    expected_return = pd.Series(return_model.predict(holdout[feature_columns]), index=holdout.index)
    selected = holdout.loc[holdout_probability >= config.probability_threshold].copy()
    selected_returns = selected[returns] - (config.round_trip_cost_bps / 10_000.0)
    if selected_returns.empty:
        selected_returns = holdout[returns].head(0)

    calibration_brier = float(
        brier_score_loss(calibration[target].astype(int), calibration_probability)
    )
    holdout_brier = float(brier_score_loss(holdout[target].astype(int), holdout_probability))
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
    feature_stability_mean, feature_stability_top = _feature_stability_summary(
        train,
        holdout,
        feature_columns,
    )
    holdout_mae = float(mean_absolute_error(holdout[returns], expected_return))
    holdout_rmse = float(mean_squared_error(holdout[returns], expected_return) ** 0.5)
    mean_selected_return = (
        float(selected_returns.mean()) if not selected_returns.empty else math.nan
    )
    lower_bound = mean_selected_return
    if len(selected_returns) > 1:
        lower_bound = mean_selected_return - (
            1.645 * float(selected_returns.std(ddof=1)) / math.sqrt(len(selected_returns))
        )
    holdout_profit_factor = _profit_factor(selected_returns)
    holdout_max_drawdown = _max_drawdown(selected_returns)
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
    metrics: dict[str, float | int | str | bool | None] = {
        "training_samples": len(train),
        "calibration_samples": len(calibration),
        "holdout_samples": len(holdout),
        "selected_holdout_samples": len(selected_returns),
        "holdout_win_rate": float((selected_returns > 0).mean())
        if not selected_returns.empty
        else math.nan,
        "holdout_mean_net_return": mean_selected_return,
        "holdout_mean_return_lcb_90": lower_bound,
        "holdout_profit_factor": holdout_profit_factor,
        "holdout_max_drawdown": holdout_max_drawdown,
        "holdout_mae_return_model": holdout_mae,
        "holdout_rmse_return_model": holdout_rmse,
        "holdout_expected_return_mean": float(expected_return.mean()),
        "feature_stability_mean_abs_z": feature_stability_mean,
        "feature_stability_top": feature_stability_top,
        "permutation_importance_top": permutation_summary,
        "mutual_information_top": mutual_information_summary,
        "holdout_target_before_stop_brier": float(
            brier_score_loss(holdout[target_before_stop].astype(int), target_holdout_probability)
        ),
        "holdout_target_before_stop_probability_mean": float(np.mean(target_holdout_probability)),
        "holdout_double_cost_lcb_90": double_cost_lcb,
        "positive_year_fraction": year_fraction,
        "positive_regime_fraction": regime_fraction,
        "positive_sector_fraction": sector_fraction,
        "symbol_concentration_top": symbol_concentration,
        "sector_concentration_top": sector_concentration,
        "prediction_turnover": prediction_turnover,
        "rsi_control_columns_available": "rsi_14" in train.columns,
        "naive_control_family": family == "naive_base_rate",
    }
    calibration_metrics: dict[str, float | int | str | bool | None] = {
        "calibration_brier": calibration_brier,
        "holdout_brier": holdout_brier,
        "calibration_probability_mean": float(np.mean(calibration_probability)),
        "holdout_probability_mean": float(np.mean(holdout_probability)),
    }
    gates = {
        "minimum_training_samples": len(train) >= config.minimum_training_samples,
        "minimum_unseen_observations": len(holdout) >= config.minimum_holdout_samples,
        "positive_expected_value_after_costs": bool(
            math.isfinite(lower_bound) and lower_bound > -(config.round_trip_cost_bps / 10_000.0)
        ),
        "calibration_brier_max_035": holdout_brier <= 0.35,
        "profit_factor_min_090": bool(
            math.isfinite(holdout_profit_factor) and holdout_profit_factor >= 0.90
        ),
        "drawdown_not_worse_than_50pct": bool(
            math.isfinite(holdout_max_drawdown) and holdout_max_drawdown > -0.50
        ),
        "confidence_lower_bound_finite": math.isfinite(lower_bound),
        "feature_stability_mean_abs_z_max_250": bool(
            math.isfinite(feature_stability_mean) and feature_stability_mean <= 2.50
        ),
        "symbol_concentration_max_050": bool(
            not math.isfinite(symbol_concentration) or symbol_concentration <= 0.50
        ),
        "sector_concentration_max_080": bool(
            not math.isfinite(sector_concentration) or sector_concentration <= 0.80
        ),
        "transaction_cost_sensitivity_not_collapsed": bool(
            math.isfinite(double_cost_lcb)
            and double_cost_lcb > -((config.round_trip_cost_bps * 2.0) / 10_000.0)
        ),
        "prediction_turnover_max_050": bool(
            math.isfinite(prediction_turnover) and prediction_turnover <= 0.50
        ),
        "comparison_controls_available": bool("rsi_14" in train.columns),
    }
    medians = {column: float(x_train[column].median()) for column in feature_columns}
    means = {column: float(x_train[column].mean()) for column in feature_columns}
    stds = {
        column: float(x_train[column].std(ddof=0))
        if float(x_train[column].std(ddof=0)) > 0
        else 1.0
        for column in feature_columns
    }
    bundle = ModelBundle(
        model_id="pending",
        direction=direction,
        horizon=horizon,
        family=family,
        feature_columns=tuple(feature_columns),
        feature_family_by_column={},
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
        training_labels=train[["Date", "symbol", returns, mfe, mae]].reset_index(drop=True),
        metrics=metrics,
        calibration_metrics=calibration_metrics,
    )
    return bundle, gates


def load_model_bundle(path: str | Path) -> ModelBundle:
    loaded = joblib.load(path)
    if not isinstance(loaded, ModelBundle):
        raise ValueError("Model artifact is not a trusted autonomous scanner bundle")
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
    feature_columns = _clean_feature_columns(
        frame,
        max_features=config.max_features,
        correlation_threshold=config.correlation_threshold,
    )
    created_at = datetime.now(UTC).isoformat()
    for horizon in config.horizons:
        split = chronological_train_calibration_holdout_split(frame, horizon=horizon)
        for direction in config.directions:
            for family, classifier in _candidate_pipelines(config.random_seed).items():
                try:
                    bundle, gates = _train_family(
                        family=family,
                        classifier=classifier,
                        split=split,
                        feature_columns=feature_columns,
                        direction=direction,
                        horizon=horizon,
                        config=config,
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
                        artifact_path="",
                        code_commit_hash=current_commit_hash(code_root or Path.cwd()),
                        created_at_utc=created_at,
                    )
                    register_model(db_path, model)
                    rejected.append(model)
                    continue

                model_id = make_model_id(
                    task="swing_direction_probability",
                    horizon=horizon,
                    direction=direction,
                    family=family,
                    universe_snapshot_id=universe_snapshot_id,
                    feature_manifest_hash=feature_manifest_hash,
                    created_at_utc=f"{created_at}|{family}|{direction}|{horizon}",
                )
                bundle = ModelBundle(
                    model_id=model_id,
                    direction=bundle.direction,
                    horizon=bundle.horizon,
                    family=bundle.family,
                    feature_columns=bundle.feature_columns,
                    feature_family_by_column={
                        column: feature_family_by_column.get(column, "unknown")
                        for column in bundle.feature_columns
                    },
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
                )
                artifact_path = Path(artifact_dir) / f"{model_id}.joblib"
                save_model_bundle(bundle, artifact_path)
                state: ModelState = "CHALLENGER" if all(gates.values()) else "CANDIDATE"
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
                    hyperparameters={"family": family, "max_features": config.max_features},
                    metrics=bundle.metrics,
                    calibration_metrics=bundle.calibration_metrics,
                    quality_gates=gates,
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
    missing = [column for column in bundle.feature_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Feature frame is missing required model columns: {missing[:5]}")
    x = frame[list(bundle.feature_columns)]
    raw = _positive_class_probability(bundle.classifier, x)
    probability = np.asarray(bundle.calibrator.predict(raw), dtype=float)
    output = frame[["Date", "symbol"]].copy()
    output["direction"] = bundle.direction
    output["horizon"] = bundle.horizon
    output["model_id"] = bundle.model_id
    output["calibrated_probability"] = probability
    target_raw = _positive_class_probability(bundle.target_before_stop_model, x)
    output["target_before_stop_probability"] = np.asarray(
        bundle.target_before_stop_calibrator.predict(target_raw), dtype=float
    )
    output["expected_return"] = bundle.return_model.predict(x)
    output["expected_mfe"] = bundle.mfe_model.predict(x)
    output["expected_mae"] = bundle.mae_model.predict(x)
    return output
