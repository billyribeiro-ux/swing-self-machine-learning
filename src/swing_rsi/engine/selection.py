from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import pandas as pd

CANONICAL_CANDIDATE_TIE_BREAKING_RULE = "composite_utility_score_desc_then_symbol"
CANONICAL_CANDIDATE_ORDER = (
    "composite_utility_score descending",
    "symbol ascending",
    "direction ascending",
    "model_id ascending",
    "stable candidate identity hash ascending",
)


@dataclass(frozen=True)
class SelectionPolicy:
    probability_threshold: float = 0.55
    expected_return_threshold: float | None = 0.001
    target_before_stop_threshold: float | None = 0.50
    top_n_limit: int | None = 5_000
    per_date_limit: int | None = 5
    liquidity_threshold: float | None = 5_000_000.0
    selected_rate_ceiling: float | None = 0.20
    tie_breaking_rule: str = CANONICAL_CANDIDATE_TIE_BREAKING_RULE


@dataclass(frozen=True)
class SelectionCheckResult:
    metric_name: str
    threshold: float
    actual_value: float | None
    passed: bool
    rejection_reason: str | None


@dataclass(frozen=True)
class SelectionEvaluationResult:
    passed: bool
    checks: tuple[SelectionCheckResult, ...]
    rejection_reasons: tuple[str, ...]
    policy_hash: str | None = None


def _max_threshold(left: float | None, right: float | None) -> float | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _min_cap(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def effective_selection_policy(
    persisted: SelectionPolicy,
    *,
    probability_threshold: float | None = None,
    expected_return_threshold: float | None = None,
    target_before_stop_threshold: float | None = None,
    liquidity_threshold: float | None = None,
    top_n_limit: int | None = None,
    per_date_limit: int | None = None,
) -> SelectionPolicy:
    return SelectionPolicy(
        probability_threshold=_max_threshold(persisted.probability_threshold, probability_threshold)
        or persisted.probability_threshold,
        expected_return_threshold=_max_threshold(
            persisted.expected_return_threshold, expected_return_threshold
        ),
        target_before_stop_threshold=_max_threshold(
            persisted.target_before_stop_threshold, target_before_stop_threshold
        ),
        liquidity_threshold=_max_threshold(persisted.liquidity_threshold, liquidity_threshold),
        top_n_limit=_min_cap(persisted.top_n_limit, top_n_limit),
        per_date_limit=_min_cap(persisted.per_date_limit, per_date_limit),
        selected_rate_ceiling=persisted.selected_rate_ceiling,
        tie_breaking_rule=persisted.tie_breaking_rule,
    )


def selection_policy_from_metrics(
    metrics: Mapping[str, object],
) -> tuple[SelectionPolicy | None, str | None]:
    payload = metrics.get("selection_policy_json")
    if not isinstance(payload, str) or not payload.strip():
        return None, None
    try:
        values = json.loads(payload)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(values, dict):
        return None, None
    if "liquidity_threshold" not in values and "liquidity_requirement" in values:
        values["liquidity_threshold"] = values.pop("liquidity_requirement")
    allowed = set(SelectionPolicy.__dataclass_fields__)
    policy_values = {key: value for key, value in values.items() if key in allowed}
    try:
        return (
            SelectionPolicy(**policy_values),
            str(metrics.get("selection_policy_configuration_hash") or "") or None,
        )
    except (TypeError, ValueError):
        return None, None


def _metric_value(candidate: Mapping[str, object], aliases: tuple[str, ...]) -> object:
    for alias in aliases:
        if alias in candidate:
            return candidate[alias]
    return None


def _as_finite_float(value: object) -> float | None:
    try:
        numeric = float(cast(Any, value))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _check_minimum(
    *,
    candidate: Mapping[str, object],
    metric_name: str,
    aliases: tuple[str, ...],
    threshold: float | None,
    below_reason: str,
) -> SelectionCheckResult | None:
    if threshold is None:
        return None
    raw_value = _metric_value(candidate, aliases)
    if raw_value is None:
        return SelectionCheckResult(
            metric_name=metric_name,
            threshold=threshold,
            actual_value=None,
            passed=False,
            rejection_reason="required_policy_metric_missing",
        )
    value = _as_finite_float(raw_value)
    if value is None:
        return SelectionCheckResult(
            metric_name=metric_name,
            threshold=threshold,
            actual_value=None,
            passed=False,
            rejection_reason="required_policy_metric_nonfinite",
        )
    if value < threshold:
        return SelectionCheckResult(
            metric_name=metric_name,
            threshold=threshold,
            actual_value=value,
            passed=False,
            rejection_reason=below_reason,
        )
    return SelectionCheckResult(
        metric_name=metric_name,
        threshold=threshold,
        actual_value=value,
        passed=True,
        rejection_reason=None,
    )


def evaluate_candidate_policy(
    candidate: Mapping[str, object],
    policy: SelectionPolicy,
    *,
    policy_hash: str | None = None,
) -> SelectionEvaluationResult:
    checks = tuple(
        check
        for check in (
            _check_minimum(
                candidate=candidate,
                metric_name="calibrated_probability",
                aliases=("calibrated_probability", "probability"),
                threshold=policy.probability_threshold,
                below_reason="below_probability_threshold",
            ),
            _check_minimum(
                candidate=candidate,
                metric_name="expected_return",
                aliases=("expected_return",),
                threshold=policy.expected_return_threshold,
                below_reason="below_expected_return_threshold",
            ),
            _check_minimum(
                candidate=candidate,
                metric_name="target_before_stop_probability",
                aliases=("target_before_stop_probability",),
                threshold=policy.target_before_stop_threshold,
                below_reason="below_target_before_stop_threshold",
            ),
            _check_minimum(
                candidate=candidate,
                metric_name="liquidity",
                aliases=("liquidity_score", "dollar_volume"),
                threshold=policy.liquidity_threshold,
                below_reason="below_liquidity_threshold",
            ),
        )
        if check is not None
    )
    reasons = tuple(check.rejection_reason for check in checks if check.rejection_reason)
    return SelectionEvaluationResult(
        passed=not reasons,
        checks=checks,
        rejection_reasons=reasons,
        policy_hash=policy_hash,
    )


def _first_existing_column(frame: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in frame.columns:
            return name
    return None


def _stable_identity(row: pd.Series) -> str:
    payload = json.dumps(
        {str(key): _jsonable(value) for key, value in row.to_dict().items()},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _jsonable(value: object) -> object:
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def order_candidates(
    frame: pd.DataFrame,
    *,
    date_column: str | None = None,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    ordered = frame.copy()
    symbol_column = _first_existing_column(ordered, ("symbol", "ticker"))
    if symbol_column is None:
        ordered["_candidate_symbol"] = ""
    else:
        ordered["_candidate_symbol"] = ordered[symbol_column].astype(str)
    direction_column = _first_existing_column(ordered, ("direction",))
    ordered["_candidate_direction"] = (
        ordered[direction_column].astype(str) if direction_column else ""
    )
    model_column = _first_existing_column(ordered, ("model_id",))
    ordered["_candidate_model_id"] = ordered[model_column].astype(str) if model_column else ""
    score_source = (
        ordered["composite_utility_score"]
        if "composite_utility_score" in ordered.columns
        else pd.Series(float("-inf"), index=ordered.index)
    )
    ordered["_candidate_score"] = pd.to_numeric(score_source, errors="coerce").fillna(float("-inf"))
    ordered["_candidate_identity"] = ordered.apply(_stable_identity, axis=1)

    sort_columns = [
        "_candidate_score",
        "_candidate_symbol",
        "_candidate_direction",
        "_candidate_model_id",
        "_candidate_identity",
    ]
    ascending = [False, True, True, True, True]
    if date_column is not None:
        ordered["_candidate_date"] = pd.to_datetime(ordered[date_column], errors="coerce")
        sort_columns.insert(0, "_candidate_date")
        ascending.insert(0, True)
    ordered = ordered.sort_values(sort_columns, ascending=ascending, kind="mergesort")
    return ordered.drop(
        columns=[
            column
            for column in (
                "_candidate_date",
                "_candidate_score",
                "_candidate_symbol",
                "_candidate_direction",
                "_candidate_model_id",
                "_candidate_identity",
            )
            if column in ordered.columns
        ]
    )


def select_policy_cap_indexes(
    candidates: pd.DataFrame,
    policy: SelectionPolicy,
    *,
    date_column: str | None = None,
) -> set[Any]:
    eligible = order_candidates(candidates)
    if policy.per_date_limit is not None and date_column is not None:
        eligible = (
            eligible.groupby(date_column, group_keys=False, sort=True)
            .head(policy.per_date_limit)
            .copy()
        )
    if policy.top_n_limit is not None:
        eligible = order_candidates(eligible).head(policy.top_n_limit)
    return set(eligible.index)
