from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal, cast

GateStatus = Literal["PASS", "FAIL", "NOT_APPLICABLE", "NOT_CONFIGURED"]
type GateValue = str | float | int | bool | None
EvidenceStatus = Literal["AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE"]

GATE_VALUE_NOT_AVAILABLE = "NOT_AVAILABLE"
GATE_VALUE_NOT_APPLICABLE = "NOT_APPLICABLE"
GATE_VALUE_POSITIVE_INFINITY = "Infinity"
GATE_VALUE_NEGATIVE_INFINITY = "-Infinity"


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    gate_name: str
    category: str
    scope: str
    metric_name: str
    threshold: GateValue
    comparator: str
    actual_value: GateValue
    status: GateStatus
    mandatory: bool
    evidence_source: str
    reason: str
    evaluated_at_utc: str
    configuration_hash: str


@dataclass(frozen=True)
class PromotionEligibility:
    eligible: bool
    mandatory_passed: int
    mandatory_failed: int
    not_configured: int
    not_applicable: int
    blocked_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProfitFactorResult:
    selected_count: int
    gross_profit: float
    gross_loss_abs: float
    zero_return_count: int
    naive_control: bool
    actual_value: GateValue
    evidence_status: EvidenceStatus
    status: GateStatus
    reason: str


@dataclass(frozen=True)
class TemporalFoldStabilityResult:
    folds_requested: int
    folds_evaluated: int
    folds_with_selected_observations: int
    selected_observations_per_fold: tuple[int, ...]
    actual_value: GateValue
    evidence_status: EvidenceStatus
    evidence_gate_status: GateStatus
    threshold_gate_status: GateStatus
    evidence_reason: str
    threshold_reason: str
    evidence_unavailable_reason: str


def configuration_hash(config: dict[str, object]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def make_gate(
    *,
    gate_id: str,
    gate_name: str,
    category: str,
    scope: str,
    metric_name: str,
    threshold: GateValue,
    comparator: str,
    actual_value: GateValue,
    status: GateStatus,
    mandatory: bool,
    evidence_source: str,
    reason: str,
    configuration_hash_value: str,
    evaluated_at_utc: str | None = None,
) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        gate_name=gate_name,
        category=category,
        scope=scope,
        metric_name=metric_name,
        threshold=threshold,
        comparator=comparator,
        actual_value=actual_value,
        status=status,
        mandatory=mandatory,
        evidence_source=evidence_source,
        reason=reason,
        evaluated_at_utc=evaluated_at_utc or datetime.now(UTC).isoformat(),
        configuration_hash=configuration_hash_value,
    )


def _coerce_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def compare_gate_values(actual: object, comparator: str, threshold: object) -> bool:
    actual_value = _coerce_float(actual)
    threshold_value = _coerce_float(threshold)
    if actual_value is None or threshold_value is None:
        return False
    if math.isnan(actual_value) or math.isnan(threshold_value):
        return False
    if math.isinf(threshold_value):
        return False
    if comparator == ">=":
        return actual_value >= threshold_value or math.isclose(actual_value, threshold_value)
    if comparator == ">":
        return actual_value > threshold_value
    if comparator == "<=":
        return actual_value <= threshold_value or math.isclose(actual_value, threshold_value)
    if comparator == "<":
        return actual_value < threshold_value
    if comparator == "==":
        return actual_value == threshold_value
    return False


def _percent(value: float) -> str:
    return f"{value:.2%}"


def _profit_factor_value_label(value: float) -> str:
    if math.isinf(value):
        return "positive infinity" if value > 0.0 else "negative infinity"
    return f"{value:.2f}"


def profit_factor_result(
    *,
    selected_count: int,
    positive_return_sum: float,
    negative_return_abs_sum: float,
    zero_return_count: int,
    naive_control: bool,
    threshold: float = 0.90,
) -> ProfitFactorResult:
    gross_profit = float(positive_return_sum)
    gross_loss_abs = float(negative_return_abs_sum)
    zeros = int(zero_return_count)
    selected = int(selected_count)
    if selected <= 0 and naive_control:
        return ProfitFactorResult(
            selected_count=selected,
            gross_profit=gross_profit,
            gross_loss_abs=gross_loss_abs,
            zero_return_count=zeros,
            naive_control=naive_control,
            actual_value=GATE_VALUE_NOT_AVAILABLE,
            evidence_status="NOT_APPLICABLE",
            status="NOT_APPLICABLE",
            reason=(
                "Profit factor is not applicable because this naive control selected no rows; "
                "trading-performance evidence is not comparable for the zero-selection control."
            ),
        )
    if selected <= 0:
        return ProfitFactorResult(
            selected_count=selected,
            gross_profit=gross_profit,
            gross_loss_abs=gross_loss_abs,
            zero_return_count=zeros,
            naive_control=naive_control,
            actual_value=GATE_VALUE_NOT_AVAILABLE,
            evidence_status="UNAVAILABLE",
            status="FAIL",
            reason="Profit factor is unavailable because no selected observations exist.",
        )
    if (
        not math.isfinite(gross_profit)
        or not math.isfinite(gross_loss_abs)
        or gross_profit < 0.0
        or gross_loss_abs < 0.0
    ):
        return ProfitFactorResult(
            selected_count=selected,
            gross_profit=gross_profit,
            gross_loss_abs=gross_loss_abs,
            zero_return_count=zeros,
            naive_control=naive_control,
            actual_value=GATE_VALUE_NOT_AVAILABLE,
            evidence_status="UNAVAILABLE",
            status="FAIL",
            reason="Profit factor is unavailable because selected return sums are invalid.",
        )
    if gross_profit == 0.0 and gross_loss_abs == 0.0:
        return ProfitFactorResult(
            selected_count=selected,
            gross_profit=gross_profit,
            gross_loss_abs=gross_loss_abs,
            zero_return_count=zeros,
            naive_control=naive_control,
            actual_value=GATE_VALUE_NOT_AVAILABLE,
            evidence_status="UNAVAILABLE",
            status="FAIL",
            reason="Profit factor is undefined because all selected returns were zero.",
        )
    actual = math.inf if gross_loss_abs == 0.0 else gross_profit / gross_loss_abs
    passed = compare_gate_values(actual, ">=", threshold)
    if math.isinf(actual) and actual > 0.0:
        reason = (
            "Selected returns contain gains and no losses, so profit factor is positive "
            f"infinity and satisfies the minimum {threshold:.2f}."
        )
    elif passed:
        reason = (
            f"Profit factor {_profit_factor_value_label(actual)} meets the minimum {threshold:.2f}."
        )
    else:
        reason = (
            f"Profit factor {_profit_factor_value_label(actual)} is below the minimum "
            f"{threshold:.2f}."
        )
    return ProfitFactorResult(
        selected_count=selected,
        gross_profit=gross_profit,
        gross_loss_abs=gross_loss_abs,
        zero_return_count=zeros,
        naive_control=naive_control,
        actual_value=actual,
        evidence_status="AVAILABLE",
        status="PASS" if passed else "FAIL",
        reason=reason,
    )


def temporal_fold_stability_result(
    *,
    selected_count: int,
    folds_requested: int,
    folds_evaluated: int,
    folds_with_selected_observations: int,
    selected_observations_per_fold: tuple[int, ...],
    positive_fraction: object,
    naive_control: bool,
    threshold: float = 0.50,
) -> TemporalFoldStabilityResult:
    requested = int(folds_requested)
    evaluated = int(folds_evaluated)
    with_selected = int(folds_with_selected_observations)
    selected = int(selected_count)
    counts = tuple(int(value) for value in selected_observations_per_fold)
    if naive_control:
        reason = (
            "Temporal-fold trading stability is not applicable to the naive zero-selection control."
        )
        return TemporalFoldStabilityResult(
            folds_requested=requested,
            folds_evaluated=evaluated,
            folds_with_selected_observations=with_selected,
            selected_observations_per_fold=counts,
            actual_value=GATE_VALUE_NOT_AVAILABLE,
            evidence_status="NOT_APPLICABLE",
            evidence_gate_status="NOT_APPLICABLE",
            threshold_gate_status="NOT_APPLICABLE",
            evidence_reason=reason,
            threshold_reason=reason,
            evidence_unavailable_reason=reason,
        )
    actual = _coerce_float(positive_fraction)
    if selected <= 0:
        unavailable = (
            "Temporal-fold stability evidence is unavailable because only 0 folds contained "
            "selected observations."
        )
    elif with_selected < requested:
        unavailable = (
            "Temporal-fold stability evidence is unavailable because only "
            f"{with_selected} folds contained selected observations."
        )
    elif positive_fraction in {None, GATE_VALUE_NOT_AVAILABLE, ""} or actual is None:
        unavailable = (
            "Temporal-fold stability evidence is unavailable because the fold metric is missing."
        )
    elif math.isnan(actual) or math.isinf(actual):
        unavailable = (
            "Temporal-fold stability evidence is unavailable because the fold metric is nonfinite."
        )
    else:
        unavailable = ""
    if unavailable:
        return TemporalFoldStabilityResult(
            folds_requested=requested,
            folds_evaluated=evaluated,
            folds_with_selected_observations=with_selected,
            selected_observations_per_fold=counts,
            actual_value=GATE_VALUE_NOT_AVAILABLE,
            evidence_status="UNAVAILABLE",
            evidence_gate_status="FAIL",
            threshold_gate_status="NOT_APPLICABLE",
            evidence_reason=unavailable,
            threshold_reason=(
                "Temporal-fold stability threshold cannot be evaluated because valid "
                "temporal-fold evidence is unavailable."
            ),
            evidence_unavailable_reason=unavailable,
        )
    assert actual is not None
    passed = compare_gate_values(actual, ">=", threshold)
    actual_label = _percent(actual)
    threshold_label = _percent(threshold)
    return TemporalFoldStabilityResult(
        folds_requested=requested,
        folds_evaluated=evaluated,
        folds_with_selected_observations=with_selected,
        selected_observations_per_fold=counts,
        actual_value=actual,
        evidence_status="AVAILABLE",
        evidence_gate_status="PASS",
        threshold_gate_status="PASS" if passed else "FAIL",
        evidence_reason=(
            "Temporal-fold stability evidence is available from "
            f"{evaluated} evaluable chronological folds."
        ),
        threshold_reason=(
            f"Temporal-fold positive fraction {actual_label} meets the minimum {threshold_label}."
            if passed
            else f"Temporal-fold positive fraction {actual_label} is below the minimum "
            f"{threshold_label}."
        ),
        evidence_unavailable_reason="",
    )


def threshold_reason(
    *,
    metric_label: str,
    actual_value: object,
    comparator: str,
    threshold: object,
    status: GateStatus,
    unavailable_reason: str,
    not_configured_reason: str | None = None,
    percent: bool = False,
) -> str:
    if status == "NOT_CONFIGURED":
        return not_configured_reason or f"{metric_label} threshold is not configured."
    if status == "NOT_APPLICABLE":
        return unavailable_reason
    actual = _coerce_float(actual_value)
    required = _coerce_float(threshold)
    if actual is None or required is None or math.isnan(actual) or math.isnan(required):
        return unavailable_reason
    actual_label = _percent(actual) if percent else f"{actual:.2f}"
    threshold_label = _percent(required) if percent else f"{required:.2f}"
    if status == "PASS":
        if comparator == "<=":
            return f"{metric_label} {actual_label} is within the maximum {threshold_label}."
        if comparator == ">=":
            return f"{metric_label} {actual_label} meets the minimum {threshold_label}."
        if comparator == ">":
            return f"{metric_label} {actual_label} is above the required {threshold_label}."
        if comparator == "<":
            return f"{metric_label} {actual_label} is below the required {threshold_label}."
        if comparator == "==":
            return f"{metric_label} equals the required {threshold_label}."
    if comparator == "<=":
        return f"{metric_label} {actual_label} exceeds the maximum {threshold_label}."
    if comparator == ">=":
        return f"{metric_label} {actual_label} is below the minimum {threshold_label}."
    if comparator == ">":
        return f"{metric_label} {actual_label} is not above the required {threshold_label}."
    if comparator == "<":
        return f"{metric_label} {actual_label} is not below the required {threshold_label}."
    if comparator == "==":
        return f"{metric_label} {actual_label} does not equal the required {threshold_label}."
    return unavailable_reason


def export_gate_value(value: object) -> object:
    numeric = _coerce_float(value)
    if numeric is not None:
        if math.isnan(numeric):
            return GATE_VALUE_NOT_AVAILABLE
        if math.isinf(numeric):
            return GATE_VALUE_POSITIVE_INFINITY if numeric > 0.0 else GATE_VALUE_NEGATIVE_INFINITY
    return value


def gate_results_to_jsonable(results: tuple[GateResult, ...]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        item = asdict(result)
        item["actual_value"] = export_gate_value(item["actual_value"])
        item["threshold"] = export_gate_value(item["threshold"])
        rows.append(item)
    return rows


def gate_result_integrity_warning(result: GateResult) -> str:
    if result.status == "PASS" and result.actual_value in {
        None,
        GATE_VALUE_NOT_AVAILABLE,
        GATE_VALUE_NOT_APPLICABLE,
        "Not available",
        "Not applicable",
    }:
        return (
            "Legacy gate evidence warning: PASS status uses unavailable or inapplicable evidence."
        )
    actual = _coerce_float(result.actual_value)
    threshold = _coerce_float(result.threshold)
    if result.status == "PASS" and actual is not None:
        if math.isnan(actual):
            return "Legacy gate evidence warning: PASS status uses unavailable or NaN evidence."
        if math.isinf(actual) and not _valid_infinite_pass(result, actual):
            return "Legacy gate evidence warning: PASS status uses unsupported nonfinite evidence."
    reason_warning = _status_reason_integrity_warning(result)
    if reason_warning:
        return reason_warning
    if actual is None or threshold is None or math.isnan(actual) or math.isnan(threshold):
        return ""
    if result.comparator in {">=", ">", "<=", "<", "=="}:
        comparison = compare_gate_values(actual, result.comparator, threshold)
        if result.status == "PASS" and not comparison:
            return (
                "Legacy gate evidence warning: PASS status contradicts actual/comparator/threshold."
            )
        if result.status == "FAIL" and comparison:
            return (
                "Legacy gate evidence warning: FAIL status contradicts actual/comparator/threshold."
            )
    return ""


def _valid_infinite_pass(result: GateResult, actual: float) -> bool:
    return (
        result.gate_id == "profit_factor_min_090"
        and result.metric_name == "holdout_profit_factor"
        and result.comparator in {">=", ">"}
        and actual > 0.0
    )


def _status_reason_integrity_warning(result: GateResult) -> str:
    reason = result.reason.lower()
    if result.status == "PASS" and any(
        phrase in reason
        for phrase in (
            "unavailable",
            "not applicable",
            "cannot be evaluated",
            "is below the minimum",
            "exceeds the maximum",
            "fails",
            "missing",
            "invalid",
        )
    ):
        return "Legacy gate evidence warning: PASS reason contradicts status."
    if result.status == "FAIL" and any(
        phrase in reason
        for phrase in (
            "passes",
            "meets the minimum",
            "is within the maximum",
            "is available from",
        )
    ):
        return "Legacy gate evidence warning: FAIL reason contradicts status."
    if result.status == "NOT_APPLICABLE" and any(
        phrase in reason for phrase in ("passes", "meets the minimum", "is within the maximum")
    ):
        return "Legacy gate evidence warning: NOT_APPLICABLE reason contradicts status."
    return ""


def gate_results_integrity_warnings(results: tuple[GateResult, ...]) -> tuple[str, ...]:
    warnings = [
        f"{result.gate_id}: {warning}"
        for result in results
        if result.mandatory and (warning := gate_result_integrity_warning(result))
    ]
    gates = {result.gate_id: result for result in results}
    temporal_threshold = gates.get("temporal_fold_stability_min_050")
    temporal_evidence = gates.get("temporal_fold_stability_evidence_available")
    not_naive = gates.get("not_naive_control")
    learned_model = not_naive is None or not_naive.status == "PASS"
    if (
        learned_model
        and temporal_threshold is not None
        and temporal_threshold.mandatory
        and temporal_threshold.actual_value
        in {None, GATE_VALUE_NOT_AVAILABLE, GATE_VALUE_NOT_APPLICABLE}
        and (temporal_evidence is None or temporal_evidence.status != "FAIL")
    ):
        warnings.append(
            "temporal_fold_stability_evidence_available: mandatory learned-model temporal "
            "evidence is missing without a failing availability gate"
        )
    return tuple(warnings)


def display_gate_value(value: object) -> str:
    exported = export_gate_value(value)
    if exported == GATE_VALUE_NOT_AVAILABLE:
        return "Not available"
    if exported == GATE_VALUE_NOT_APPLICABLE:
        return "Not applicable"
    if exported == GATE_VALUE_POSITIVE_INFINITY:
        return "∞"
    if exported == GATE_VALUE_NEGATIVE_INFINITY:
        return "-∞"
    return str(exported)


def machine_gate_value(value: object) -> object:
    return export_gate_value(value)


def gate_results_from_jsonable(rows: object) -> tuple[GateResult, ...]:
    if not isinstance(rows, list):
        return ()
    results: list[GateResult] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", ""))
        if status not in {"PASS", "FAIL", "NOT_APPLICABLE", "NOT_CONFIGURED"}:
            continue
        try:
            results.append(
                GateResult(
                    gate_id=str(item["gate_id"]),
                    gate_name=str(item["gate_name"]),
                    category=str(item["category"]),
                    scope=str(item["scope"]),
                    metric_name=str(item["metric_name"]),
                    threshold=item.get("threshold"),
                    comparator=str(item["comparator"]),
                    actual_value=item.get("actual_value"),
                    status=cast(GateStatus, status),
                    mandatory=bool(item["mandatory"]),
                    evidence_source=str(item["evidence_source"]),
                    reason=str(item["reason"]),
                    evaluated_at_utc=str(item["evaluated_at_utc"]),
                    configuration_hash=str(item["configuration_hash"]),
                )
            )
        except KeyError:
            continue
    return tuple(results)


def legacy_gate_results(quality_gates: dict[str, bool]) -> tuple[GateResult, ...]:
    config_hash = configuration_hash({"legacy_quality_gates": tuple(sorted(quality_gates))})
    evaluated_at = datetime.now(UTC).isoformat()
    return tuple(
        make_gate(
            gate_id=gate_id,
            gate_name=gate_id.replace("_", " ").title(),
            category="legacy",
            scope="legacy_model",
            metric_name=gate_id,
            threshold="legacy boolean gate",
            comparator="is true",
            actual_value=passed,
            status="PASS" if passed else "FAIL",
            mandatory=True,
            evidence_source="quality_gates_json",
            reason="Legacy boolean gate without canonical threshold metadata.",
            configuration_hash_value=config_hash,
            evaluated_at_utc=evaluated_at,
        )
        for gate_id, passed in quality_gates.items()
    )


def quality_gate_bool_map(results: tuple[GateResult, ...]) -> dict[str, bool]:
    return {result.gate_id: result.status == "PASS" for result in results if result.mandatory}


def promotion_eligibility(results: tuple[GateResult, ...]) -> PromotionEligibility:
    mandatory = [result for result in results if result.mandatory]
    if not mandatory:
        return PromotionEligibility(
            eligible=False,
            mandatory_passed=0,
            mandatory_failed=0,
            not_configured=1,
            not_applicable=0,
            blocked_reasons=("canonical mandatory gate results are missing",),
        )
    failed = [result for result in mandatory if result.status == "FAIL"]
    not_configured = [result for result in mandatory if result.status == "NOT_CONFIGURED"]
    not_applicable = [result for result in mandatory if result.status == "NOT_APPLICABLE"]
    passed = [result for result in mandatory if result.status == "PASS"]
    blocked = [
        f"{result.gate_id}: {result.reason}"
        for result in (*failed, *not_configured, *not_applicable)
    ]
    integrity_warnings = gate_results_integrity_warnings(tuple(mandatory))
    blocked.extend(integrity_warnings)
    prediction_gate_ids = {
        result.gate_id for result in results if result.category == "prediction sanity"
    }
    has_legacy_ood_gate = "prediction_out_of_distribution_absent" in prediction_gate_ids
    has_v2_ood_schema_gate = "prediction_ood_governance_schema_version" in prediction_gate_ids
    if has_legacy_ood_gate and not has_v2_ood_schema_gate:
        blocked.append(
            "prediction_ood_governance_schema_version: legacy OOD artifacts lack V2 "
            "canonical prediction gates"
        )
    return PromotionEligibility(
        eligible=not failed
        and not not_configured
        and not not_applicable
        and not integrity_warnings
        and not (has_legacy_ood_gate and not has_v2_ood_schema_gate),
        mandatory_passed=len(passed),
        mandatory_failed=len(failed),
        not_configured=len(not_configured),
        not_applicable=len(not_applicable),
        blocked_reasons=tuple(blocked),
    )
