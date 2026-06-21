from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Literal, cast

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression

from swing_rsi.engine.features import reject_label_columns
from swing_rsi.engine.gates import configuration_hash

FEATURE_SCREEN_SCHEMA_VERSION = "target_specific_feature_screen_v1"
FeatureScreenTask = Literal["classification", "regression"]

BLOCKED_FEATURE_COLUMNS = {
    "Date",
    "date",
    "timestamp",
    "symbol",
    "ticker",
    "role",
    "sector",
    "sector_proxy",
    "market_regime_label",
}


@dataclass(frozen=True)
class FeatureScreenSpec:
    target_name: str
    task_type: FeatureScreenTask
    max_selected_features: int
    random_seed: int
    missingness_threshold: float = 0.40
    variance_threshold: float = 1e-12
    correlation_threshold: float = 0.97
    schema_version: str = FEATURE_SCREEN_SCHEMA_VERSION

    def configuration(self) -> dict[str, object]:
        return asdict(self)

    @property
    def configuration_hash(self) -> str:
        return configuration_hash(self.configuration())


@dataclass(frozen=True)
class FeatureScreenRecord:
    feature: str
    feature_family: str
    target_name: str
    task_type: FeatureScreenTask
    missingness: float | None
    missingness_result: str
    variance: float | None
    variance_result: str
    mutual_information_score: float | None
    rank: int | None
    correlation_pruning_result: str
    selected: bool
    status: str
    rejection_reason: str
    correlated_with: str | None = None
    absolute_correlation: float | None = None

    def to_jsonable(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FeatureScreenResult:
    spec: FeatureScreenSpec
    selected_features: tuple[str, ...]
    records: tuple[FeatureScreenRecord, ...]
    training_start: str | None
    training_end: str | None
    training_row_count: int
    full_eligible_feature_count: int
    post_missingness_feature_count: int
    post_variance_feature_count: int
    scored_feature_count: int
    correlation_pruned_feature_count: int
    selected_feature_manifest_hash: str

    @property
    def selected_feature_families(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            if not record.selected:
                continue
            counts[record.feature_family] = counts.get(record.feature_family, 0) + 1
        return counts

    @property
    def selected_scores(self) -> dict[str, float]:
        return {
            record.feature: float(record.mutual_information_score or 0.0)
            for record in self.records
            if record.selected
        }

    def metadata(self) -> dict[str, object]:
        return {
            "screening_schema_version": self.spec.schema_version,
            "target_label_name": self.spec.target_name,
            "task_type": self.spec.task_type,
            "training_start": self.training_start,
            "training_end": self.training_end,
            "training_sample_count": self.training_row_count,
            "full_eligible_feature_count": self.full_eligible_feature_count,
            "post_missingness_feature_count": self.post_missingness_feature_count,
            "post_variance_feature_count": self.post_variance_feature_count,
            "scored_feature_count": self.scored_feature_count,
            "correlation_pruned_count": self.correlation_pruned_feature_count,
            "selected_feature_count": len(self.selected_features),
            "selected_feature_names": list(self.selected_features),
            "selected_feature_families": self.selected_feature_families,
            "selected_feature_scores": self.selected_scores,
            "deterministic_random_seed": self.spec.random_seed,
            "screen_configuration": self.spec.configuration(),
            "screen_configuration_hash": self.spec.configuration_hash,
            "selected_feature_manifest_hash": self.selected_feature_manifest_hash,
        }

    def audit_records(self) -> list[dict[str, object]]:
        metadata = self.metadata()
        return [
            {
                **record.to_jsonable(),
                "screening_schema_version": self.spec.schema_version,
                "training_start": self.training_start,
                "training_end": self.training_end,
                "training_sample_count": self.training_row_count,
                "screen_configuration_hash": metadata["screen_configuration_hash"],
                "selected_feature_manifest_hash": self.selected_feature_manifest_hash,
            }
            for record in self.records
        ]


def _json_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def selected_feature_manifest_hash(
    *,
    spec: FeatureScreenSpec,
    selected_features: tuple[str, ...],
    feature_family_by_column: dict[str, str],
) -> str:
    return _json_hash(
        {
            "schema_version": spec.schema_version,
            "target_name": spec.target_name,
            "task_type": spec.task_type,
            "screen_configuration_hash": spec.configuration_hash,
            "selected_features": list(selected_features),
            "selected_feature_families": {
                feature: feature_family_by_column.get(feature, "unknown")
                for feature in selected_features
            },
        }
    )


def _training_date_range(frame: pd.DataFrame) -> tuple[str | None, str | None]:
    if "Date" not in frame.columns or frame.empty:
        return None, None
    dates = pd.to_datetime(frame["Date"], errors="coerce").dropna()
    if dates.empty:
        return None, None
    return dates.min().date().isoformat(), dates.max().date().isoformat()


def _empty_record(
    *,
    column: str,
    family: str,
    spec: FeatureScreenSpec,
    status: str,
    reason: str,
) -> FeatureScreenRecord:
    return FeatureScreenRecord(
        feature=column,
        feature_family=family,
        target_name=spec.target_name,
        task_type=spec.task_type,
        missingness=None,
        missingness_result="not_evaluated",
        variance=None,
        variance_result="not_evaluated",
        mutual_information_score=None,
        rank=None,
        correlation_pruning_result="not_evaluated",
        selected=False,
        status=status,
        rejection_reason=reason,
    )


def _candidate_columns(
    frame: pd.DataFrame,
    *,
    spec: FeatureScreenSpec,
    family_by_column: dict[str, str],
) -> tuple[list[str], list[FeatureScreenRecord]]:
    candidates: list[str] = []
    rejected: list[FeatureScreenRecord] = []
    for column in frame.columns:
        name = str(column)
        family = family_by_column.get(name, "unknown")
        if name == spec.target_name:
            rejected.append(
                _empty_record(
                    column=name,
                    family=family,
                    spec=spec,
                    status="rejected",
                    reason="target_column_prohibited",
                )
            )
            continue
        if name.startswith("label_"):
            rejected.append(
                _empty_record(
                    column=name,
                    family=family,
                    spec=spec,
                    status="rejected",
                    reason="label_column_prohibited",
                )
            )
            continue
        if name in BLOCKED_FEATURE_COLUMNS:
            rejected.append(
                _empty_record(
                    column=name,
                    family=family,
                    spec=spec,
                    status="rejected",
                    reason="metadata_column_prohibited",
                )
            )
            continue
        if not pd.api.types.is_numeric_dtype(frame[column]):
            rejected.append(
                _empty_record(
                    column=name,
                    family=family,
                    spec=spec,
                    status="rejected",
                    reason="unsupported_non_numeric_column",
                )
            )
            continue
        candidates.append(name)
    reject_label_columns([column for column in candidates if str(column).startswith("label_")])
    return candidates, rejected


def _score_features(
    frame: pd.DataFrame,
    target: pd.Series,
    columns: list[str],
    *,
    spec: FeatureScreenSpec,
) -> dict[str, float | None]:
    if not columns:
        return {}
    if target.nunique(dropna=True) < 2:
        return {column: None for column in columns}
    x = frame[columns].replace([np.inf, -np.inf], np.nan)
    medians = x.median(numeric_only=True)
    x = x.fillna(medians).fillna(0.0)
    y = target.astype(int) if spec.task_type == "classification" else target.astype(float)
    try:
        if spec.task_type == "classification":
            scores = mutual_info_classif(x, y, random_state=spec.random_seed)
        else:
            scores = mutual_info_regression(x, y, random_state=spec.random_seed)
    except ValueError:
        return {column: None for column in columns}
    output: dict[str, float | None] = {}
    for column, raw_score in zip(columns, scores, strict=True):
        score = float(raw_score)
        if not math.isfinite(score):
            output[column] = None
        else:
            output[column] = max(0.0, score)
    return output


def screen_features_for_target(
    training_frame: pd.DataFrame,
    training_target: pd.Series,
    *,
    target_name: str,
    task_type: FeatureScreenTask,
    feature_family_by_column: dict[str, str],
    max_selected_features: int,
    random_seed: int,
    missingness_threshold: float = 0.40,
    variance_threshold: float = 1e-12,
    correlation_threshold: float = 0.97,
) -> FeatureScreenResult:
    spec = FeatureScreenSpec(
        target_name=target_name,
        task_type=task_type,
        max_selected_features=max_selected_features,
        random_seed=random_seed,
        missingness_threshold=missingness_threshold,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
    )
    target = pd.to_numeric(training_target, errors="coerce")
    valid_target = target.notna()
    frame = training_frame.loc[valid_target].copy()
    target = target.loc[valid_target]
    train_start, train_end = _training_date_range(frame)
    candidate_columns, initial_rejections = _candidate_columns(
        frame,
        spec=spec,
        family_by_column=feature_family_by_column,
    )
    full_eligible_count = len(candidate_columns)
    working = frame[candidate_columns].replace([np.inf, -np.inf], np.nan)
    missingness = working.isna().mean() if candidate_columns else pd.Series(dtype=float)

    records_by_feature: dict[str, FeatureScreenRecord] = {}
    post_missingness: list[str] = []
    for column in candidate_columns:
        missing = float(cast(float, missingness[column]))
        family = feature_family_by_column.get(column, "unknown")
        if not math.isfinite(missing) or missing > spec.missingness_threshold:
            records_by_feature[column] = FeatureScreenRecord(
                feature=column,
                feature_family=family,
                target_name=spec.target_name,
                task_type=spec.task_type,
                missingness=missing,
                missingness_result="fail",
                variance=None,
                variance_result="not_evaluated",
                mutual_information_score=None,
                rank=None,
                correlation_pruning_result="not_evaluated",
                selected=False,
                status="rejected",
                rejection_reason="missingness_above_threshold",
            )
        else:
            post_missingness.append(column)

    variances = (
        working[post_missingness].var(numeric_only=True)
        if post_missingness
        else pd.Series(dtype=float)
    )
    post_variance: list[str] = []
    for column in post_missingness:
        variance = float(cast(float, variances[column]))
        family = feature_family_by_column.get(column, "unknown")
        if not math.isfinite(variance) or variance <= spec.variance_threshold:
            records_by_feature[column] = FeatureScreenRecord(
                feature=column,
                feature_family=family,
                target_name=spec.target_name,
                task_type=spec.task_type,
                missingness=float(cast(float, missingness[column])),
                missingness_result="pass",
                variance=variance,
                variance_result="fail",
                mutual_information_score=None,
                rank=None,
                correlation_pruning_result="not_evaluated",
                selected=False,
                status="rejected",
                rejection_reason="near_zero_variance",
            )
        else:
            post_variance.append(column)

    scores = _score_features(working, target, post_variance, spec=spec)
    scored_columns = [column for column in post_variance if scores.get(column) is not None]
    sorted_scored = sorted(
        scored_columns,
        key=lambda column: (-(scores[column] or 0.0), column),
    )
    ranks = {column: rank for rank, column in enumerate(sorted_scored, start=1)}
    for column in post_variance:
        if scores.get(column) is None:
            records_by_feature[column] = FeatureScreenRecord(
                feature=column,
                feature_family=feature_family_by_column.get(column, "unknown"),
                target_name=spec.target_name,
                task_type=spec.task_type,
                missingness=float(cast(float, missingness[column])),
                missingness_result="pass",
                variance=float(cast(float, variances[column])),
                variance_result="pass",
                mutual_information_score=None,
                rank=None,
                correlation_pruning_result="not_evaluated",
                selected=False,
                status="rejected",
                rejection_reason="mutual_information_score_unavailable",
            )

    imputed = working[post_variance].copy()
    if post_variance:
        medians = imputed.median(numeric_only=True)
        imputed = imputed.fillna(medians).fillna(0.0)
    selected: list[str] = []
    reached_cap = False
    for column in sorted_scored:
        score = scores[column]
        assert score is not None
        family = feature_family_by_column.get(column, "unknown")
        if len(selected) >= spec.max_selected_features:
            reached_cap = True
            records_by_feature[column] = FeatureScreenRecord(
                feature=column,
                feature_family=family,
                target_name=spec.target_name,
                task_type=spec.task_type,
                missingness=float(cast(float, missingness[column])),
                missingness_result="pass",
                variance=float(cast(float, variances[column])),
                variance_result="pass",
                mutual_information_score=score,
                rank=ranks[column],
                correlation_pruning_result="not_evaluated_after_cap",
                selected=False,
                status="rejected",
                rejection_reason="max_selected_features_reached",
            )
            continue
        correlated_with: str | None = None
        absolute_correlation: float | None = None
        if selected:
            correlations = imputed[selected].corrwith(imputed[column]).abs()
            if not correlations.empty:
                max_corr = float(correlations.max())
                if math.isfinite(max_corr):
                    absolute_correlation = max_corr
                    correlated_with = str(correlations.idxmax())
        if (
            absolute_correlation is not None
            and math.isfinite(absolute_correlation)
            and absolute_correlation >= spec.correlation_threshold
        ):
            records_by_feature[column] = FeatureScreenRecord(
                feature=column,
                feature_family=family,
                target_name=spec.target_name,
                task_type=spec.task_type,
                missingness=float(cast(float, missingness[column])),
                missingness_result="pass",
                variance=float(cast(float, variances[column])),
                variance_result="pass",
                mutual_information_score=score,
                rank=ranks[column],
                correlation_pruning_result="fail",
                selected=False,
                status="rejected",
                rejection_reason="correlated_with_higher_ranked_feature",
                correlated_with=correlated_with,
                absolute_correlation=absolute_correlation,
            )
            continue
        selected.append(column)
        records_by_feature[column] = FeatureScreenRecord(
            feature=column,
            feature_family=family,
            target_name=spec.target_name,
            task_type=spec.task_type,
            missingness=float(cast(float, missingness[column])),
            missingness_result="pass",
            variance=float(cast(float, variances[column])),
            variance_result="pass",
            mutual_information_score=score,
            rank=ranks[column],
            correlation_pruning_result="pass",
            selected=True,
            status="selected",
            rejection_reason="",
        )

    selected_tuple = tuple(selected)
    manifest_hash = selected_feature_manifest_hash(
        spec=spec,
        selected_features=selected_tuple,
        feature_family_by_column=feature_family_by_column,
    )
    records = [
        *initial_rejections,
        *[
            records_by_feature[column]
            for column in candidate_columns
            if column in records_by_feature
        ],
    ]
    return FeatureScreenResult(
        spec=spec,
        selected_features=selected_tuple,
        records=tuple(records),
        training_start=train_start,
        training_end=train_end,
        training_row_count=len(frame),
        full_eligible_feature_count=full_eligible_count,
        post_missingness_feature_count=len(post_missingness),
        post_variance_feature_count=len(post_variance),
        scored_feature_count=len(scored_columns),
        correlation_pruned_feature_count=len(selected_tuple)
        if reached_cap
        else sum(
            1
            for record in records_by_feature.values()
            if record.correlation_pruning_result == "pass"
        ),
        selected_feature_manifest_hash=manifest_hash,
    )
