from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal, cast

GateStatus = Literal["PASS", "FAIL", "NOT_APPLICABLE", "NOT_CONFIGURED"]
type GateValue = str | float | int | bool | None


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


def gate_results_to_jsonable(results: tuple[GateResult, ...]) -> list[dict[str, object]]:
    return [asdict(result) for result in results]


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
    return {
        result.gate_id: result.status in {"PASS", "NOT_APPLICABLE"}
        for result in results
        if result.mandatory
    }


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
        and not (has_legacy_ood_gate and not has_v2_ood_schema_gate),
        mandatory_passed=len(passed),
        mandatory_failed=len(failed),
        not_configured=len(not_configured),
        not_applicable=len(not_applicable),
        blocked_reasons=tuple(blocked),
    )
