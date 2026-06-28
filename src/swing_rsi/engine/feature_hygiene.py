from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from swing_rsi.engine.gates import configuration_hash

MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION = "model_feature_nonfinite_hygiene_v1"
LEGACY_PRE_NONFINITE_HYGIENE_SCHEMA_VERSION = "legacy_pre_nonfinite_hygiene"
MODEL_FEATURE_MATRIX_NONFINITE_REJECTION_REASON = (
    "model_feature_matrix_nonfinite_after_sanitization"
)
SAFE_FLOAT64_ABS_GUARD = 1.0e308


@dataclass(frozen=True)
class FeatureMatrixHygieneAudit:
    schema_version: str
    split: str
    stage: str
    row_count: int
    column_count: int
    safe_float64_abs_guard: float
    pre_sanitization_positive_infinity_count: int
    pre_sanitization_negative_infinity_count: int
    pre_sanitization_nan_count: int
    pre_sanitization_too_large_count: int
    pre_sanitization_nonfinite_count: int
    pre_sanitization_invalid_count: int
    post_sanitization_positive_infinity_count: int
    post_sanitization_negative_infinity_count: int
    post_sanitization_too_large_count: int
    post_sanitization_nonfinite_count: int
    post_sanitization_nan_count: int
    affected_columns: tuple[str, ...]
    sanitized_columns: tuple[str, ...]
    affected_feature_families: dict[str, int]
    affected_symbols: tuple[str, ...]
    affected_dates: tuple[str, ...]
    rows_with_invalid_values: int
    policy_hash: str

    def to_jsonable(self) -> dict[str, object]:
        return asdict(self)


def nonfinite_hygiene_policy() -> dict[str, object]:
    return {
        "schema_version": MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION,
        "safe_float64_abs_guard": SAFE_FLOAT64_ABS_GUARD,
        "positive_infinity_policy": "replace_with_nan",
        "negative_infinity_policy": "replace_with_nan",
        "too_large_policy": "replace_with_nan",
        "nan_policy": "preserve_for_train_fitted_imputation",
        "zero_fill_policy": "never_default",
    }


def nonfinite_hygiene_policy_hash() -> str:
    return configuration_hash(nonfinite_hygiene_policy())


def legacy_nonfinite_hygiene_metadata() -> dict[str, object]:
    return {
        "schema_version": LEGACY_PRE_NONFINITE_HYGIENE_SCHEMA_VERSION,
        "policy_hash": "",
    }


def sanitize_model_feature_matrix(
    frame: pd.DataFrame,
    *,
    split: str,
    stage: str,
    feature_family_by_column: dict[str, str] | None = None,
    context_frame: pd.DataFrame | None = None,
    safe_abs_guard: float = SAFE_FLOAT64_ABS_GUARD,
) -> tuple[pd.DataFrame, FeatureMatrixHygieneAudit]:
    """Replace invalid feature values with NaN before train-fitted imputation.

    The post-sanitization nonfinite count intentionally counts only values that
    must never reach estimators as raw inputs: infinities and finite magnitudes
    beyond the configured float64 guard. NaNs are tracked separately because the
    project treats them as missing values for train-fitted imputers.
    """

    numeric = frame.apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float, copy=True)
    positive_inf = np.isposinf(values)
    negative_inf = np.isneginf(values)
    nan_values = np.isnan(values)
    too_large = np.isfinite(values) & (np.abs(values) > safe_abs_guard)
    invalid = positive_inf | negative_inf | too_large
    values[invalid] = np.nan
    sanitized = pd.DataFrame(values, index=frame.index, columns=frame.columns)

    post_values = sanitized.to_numpy(dtype=float, copy=False)
    post_positive_inf = np.isposinf(post_values)
    post_negative_inf = np.isneginf(post_values)
    post_too_large = np.isfinite(post_values) & (np.abs(post_values) > safe_abs_guard)
    post_invalid = post_positive_inf | post_negative_inf | post_too_large

    pre_nonfinite = positive_inf | negative_inf | nan_values
    affected_columns = tuple(
        str(column)
        for index, column in enumerate(frame.columns)
        if bool(pre_nonfinite[:, index].any())
    )
    sanitized_columns = tuple(
        str(column) for index, column in enumerate(frame.columns) if bool(invalid[:, index].any())
    )
    family_counts: dict[str, int] = {}
    families = feature_family_by_column or {}
    for index, column in enumerate(frame.columns):
        count = int(invalid[:, index].sum())
        if count <= 0:
            continue
        family = families.get(str(column), "unknown")
        family_counts[family] = family_counts.get(family, 0) + count

    row_invalid = invalid.any(axis=1) if len(frame.columns) else np.zeros(len(frame), dtype=bool)
    affected_symbols: tuple[str, ...] = ()
    affected_dates: tuple[str, ...] = ()
    if context_frame is not None and len(context_frame) == len(frame):
        context = (
            context_frame.loc[frame.index]
            if frame.index.isin(context_frame.index).all()
            else context_frame
        )
        if "symbol" in context.columns:
            affected_symbols = tuple(
                sorted(str(value) for value in context.loc[row_invalid, "symbol"].dropna().unique())
            )
        if "Date" in context.columns:
            dates = pd.to_datetime(context.loc[row_invalid, "Date"], errors="coerce").dropna()
            affected_dates = tuple(sorted(date.date().isoformat() for date in dates.unique()))

    policy_hash = nonfinite_hygiene_policy_hash()
    audit = FeatureMatrixHygieneAudit(
        schema_version=MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION,
        split=split,
        stage=stage,
        row_count=len(frame),
        column_count=len(frame.columns),
        safe_float64_abs_guard=float(safe_abs_guard),
        pre_sanitization_positive_infinity_count=int(positive_inf.sum()),
        pre_sanitization_negative_infinity_count=int(negative_inf.sum()),
        pre_sanitization_nan_count=int(nan_values.sum()),
        pre_sanitization_too_large_count=int(too_large.sum()),
        pre_sanitization_nonfinite_count=int(pre_nonfinite.sum()),
        pre_sanitization_invalid_count=int(invalid.sum()),
        post_sanitization_positive_infinity_count=int(post_positive_inf.sum()),
        post_sanitization_negative_infinity_count=int(post_negative_inf.sum()),
        post_sanitization_too_large_count=int(post_too_large.sum()),
        post_sanitization_nonfinite_count=int(post_invalid.sum()),
        post_sanitization_nan_count=int(np.isnan(post_values).sum()),
        affected_columns=affected_columns,
        sanitized_columns=sanitized_columns,
        affected_feature_families=family_counts,
        affected_symbols=affected_symbols,
        affected_dates=affected_dates,
        rows_with_invalid_values=int(row_invalid.sum()),
        policy_hash=policy_hash,
    )
    reject_post_sanitization_nonfinite(audit)
    return sanitized, audit


def reject_post_sanitization_nonfinite(audit: FeatureMatrixHygieneAudit) -> None:
    if audit.post_sanitization_nonfinite_count:
        raise ValueError(MODEL_FEATURE_MATRIX_NONFINITE_REJECTION_REASON)


def sanitize_model_feature_matrix_only(frame: pd.DataFrame) -> pd.DataFrame:
    sanitized, _ = sanitize_model_feature_matrix(
        frame,
        split="runtime",
        stage="prediction",
        feature_family_by_column=None,
        context_frame=None,
    )
    return sanitized


def combine_hygiene_audits(audits: list[FeatureMatrixHygieneAudit]) -> dict[str, object]:
    if not audits:
        return {
            "schema_version": MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION,
            "policy_hash": nonfinite_hygiene_policy_hash(),
            "records": [],
        }
    by_split: dict[str, int] = {}
    by_stage: dict[str, int] = {}
    by_family: dict[str, int] = {}
    columns: set[str] = set()
    sanitized_columns: set[str] = set()
    symbols: set[str] = set()
    dates: set[str] = set()
    for audit in audits:
        by_split[audit.split] = by_split.get(audit.split, 0) + audit.pre_sanitization_invalid_count
        by_stage[audit.stage] = by_stage.get(audit.stage, 0) + audit.pre_sanitization_invalid_count
        columns.update(audit.affected_columns)
        sanitized_columns.update(audit.sanitized_columns)
        symbols.update(audit.affected_symbols)
        dates.update(audit.affected_dates)
        for family, count in audit.affected_feature_families.items():
            by_family[family] = by_family.get(family, 0) + int(count)
    return {
        "schema_version": MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION,
        "policy": nonfinite_hygiene_policy(),
        "policy_hash": nonfinite_hygiene_policy_hash(),
        "record_count": len(audits),
        "pre_sanitization_positive_infinity_count": sum(
            audit.pre_sanitization_positive_infinity_count for audit in audits
        ),
        "pre_sanitization_negative_infinity_count": sum(
            audit.pre_sanitization_negative_infinity_count for audit in audits
        ),
        "pre_sanitization_nan_count": sum(audit.pre_sanitization_nan_count for audit in audits),
        "pre_sanitization_too_large_count": sum(
            audit.pre_sanitization_too_large_count for audit in audits
        ),
        "pre_sanitization_nonfinite_count": sum(
            audit.pre_sanitization_nonfinite_count for audit in audits
        ),
        "pre_sanitization_invalid_count": sum(
            audit.pre_sanitization_invalid_count for audit in audits
        ),
        "post_sanitization_nonfinite_count": sum(
            audit.post_sanitization_nonfinite_count for audit in audits
        ),
        "post_sanitization_nan_count": sum(audit.post_sanitization_nan_count for audit in audits),
        "columns_containing_nonfinite": tuple(sorted(columns)),
        "columns_sanitized": tuple(sorted(sanitized_columns)),
        "affected_feature_families": dict(sorted(by_family.items())),
        "affected_symbols": tuple(sorted(symbols)),
        "affected_dates": tuple(sorted(dates)),
        "pre_sanitization_invalid_count_by_split": dict(sorted(by_split.items())),
        "pre_sanitization_invalid_count_by_stage": dict(sorted(by_stage.items())),
        "records": [audit.to_jsonable() for audit in audits],
    }
