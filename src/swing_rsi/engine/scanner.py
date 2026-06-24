from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd

from swing_rsi.engine.attribution import explain_candidate
from swing_rsi.engine.models import (
    EXPECTED_RETURN_HEAD,
    LINEAR_PATH_HEAD_RETIREMENT_REASON,
    MAE_HEAD,
    MFE_HEAD,
    PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR,
    PATH_MAGNITUDE_HEADS,
    PATH_METRIC_HEADS,
    PATH_TARGET_ATR_FEATURE,
    PATH_TARGET_NORMALIZATION_SCHEMA_VERSION,
    TARGET_BEFORE_STOP_HEAD,
    ModelBundle,
    bundle_feature_screen_metadata,
    bundle_head_feature_manifest,
    bundle_path_domain_metadata,
    bundle_tbs_calibration_metadata,
    predict_bundle,
)
from swing_rsi.engine.ood import (
    HEAD_OUTPUT_COLUMNS,
    PREDICTION_OOD_GOVERNANCE_VERSION,
    REGRESSION_HEADS,
    bundle_ood_identity,
)
from swing_rsi.engine.selection import (
    CANONICAL_CANDIDATE_ORDER,
    CANONICAL_CANDIDATE_TIE_BREAKING_RULE,
    SelectionPolicy,
    effective_selection_policy,
    evaluate_candidate_policy,
    order_candidates,
    select_policy_cap_indexes,
    selection_policy_from_metrics,
)
from swing_rsi.engine.storage import dumps, engine_connection, loads

SCANNER_IDENTITY_SCHEMA_VERSION = 9
SCANNER_IMPLEMENTATION_VERSION = "scanner-cache-identity-v9-atr-path-targets"


@dataclass(frozen=True)
class ScannerConfig:
    probability_threshold: float = 0.55
    expected_return_threshold: float | None = None
    target_before_stop_threshold: float | None = None
    minimum_dollar_volume: float = 5_000_000.0
    top_n_per_direction: int = 25


@dataclass(frozen=True)
class ScannerSnapshot:
    scan_id: str
    as_of_date: str
    created_at_utc: str
    rows: pd.DataFrame
    csv_path: Path
    parquet_path: Path


@dataclass(frozen=True)
class ScanExecutionIdentity:
    payload: dict[str, object]

    def to_jsonable(self) -> dict[str, object]:
        return self.payload


def latest_common_session(
    frames: dict[str, pd.DataFrame], symbols: tuple[str, ...]
) -> pd.Timestamp:
    enabled = [
        frames[symbol].index for symbol in symbols if symbol in frames and not frames[symbol].empty
    ]
    if not enabled:
        raise ValueError("No enabled symbols have data")
    common = enabled[0]
    for index in enabled[1:]:
        common = common.intersection(index)
    if common.empty:
        raise ValueError("No common completed session across enabled universe data")
    return pd.Timestamp(common.max())


def feature_snapshot_hash(frame: pd.DataFrame) -> str:
    canonical = frame.sort_index(axis=1).copy()
    sort_columns = [column for column in ("Date", "symbol") if column in canonical.columns]
    if sort_columns:
        canonical = canonical.sort_values(sort_columns, kind="mergesort")
    else:
        canonical = canonical.sort_values(list(canonical.columns), kind="mergesort")
    canonical = canonical.reset_index(drop=True)
    payload = pd.util.hash_pandas_object(canonical, index=False).to_numpy().tobytes()
    return hashlib.sha256(payload).hexdigest()[:24]


def _stable_hash(payload: object) -> str:
    return hashlib.sha256(dumps(payload).encode("utf-8")).hexdigest()


def _scan_id_from_identity(identity: dict[str, object], *, conflict_index: int = 0) -> str:
    payload: dict[str, object] = {"identity": identity}
    if conflict_index:
        payload["identity_conflict_index"] = conflict_index
    return _stable_hash(payload)[:24]


def _normalized_scanner_config(config: ScannerConfig) -> dict[str, object]:
    return {
        "probability_threshold": float(config.probability_threshold),
        "expected_return_threshold": (
            None
            if config.expected_return_threshold is None
            else float(config.expected_return_threshold)
        ),
        "target_before_stop_threshold": (
            None
            if config.target_before_stop_threshold is None
            else float(config.target_before_stop_threshold)
        ),
        "minimum_dollar_volume": float(config.minimum_dollar_volume),
        "top_n_per_direction": int(config.top_n_per_direction),
    }


def _normalized_policy(policy: SelectionPolicy | None) -> dict[str, object] | None:
    if policy is None:
        return None
    return {
        "probability_threshold": float(policy.probability_threshold),
        "expected_return_threshold": (
            None
            if policy.expected_return_threshold is None
            else float(policy.expected_return_threshold)
        ),
        "target_before_stop_threshold": (
            None
            if policy.target_before_stop_threshold is None
            else float(policy.target_before_stop_threshold)
        ),
        "top_n_limit": None if policy.top_n_limit is None else int(policy.top_n_limit),
        "per_date_limit": None if policy.per_date_limit is None else int(policy.per_date_limit),
        "liquidity_threshold": (
            None if policy.liquidity_threshold is None else float(policy.liquidity_threshold)
        ),
        "selected_rate_ceiling": (
            None if policy.selected_rate_ceiling is None else float(policy.selected_rate_ceiling)
        ),
        "tie_breaking_rule": policy.tie_breaking_rule,
    }


def _bundle_metric_string(bundle: ModelBundle, key: str) -> str:
    value = bundle.metrics.get(key)
    return str(value) if value not in {None, ""} else ""


def _finite_float(value: object) -> float:
    try:
        numeric = float(str(value))
    except (TypeError, ValueError):
        return math.nan
    return numeric if math.isfinite(numeric) else math.nan


def _prediction_integrity_result(item: dict[str, object]) -> dict[str, object]:
    rejection_reasons: list[str] = []
    warning_heads: list[str] = []
    warning_details: list[dict[str, object]] = []
    expected_return_missing = bool(item.get("expected_return_required_feature_missing", False))
    if expected_return_missing:
        rejection_reasons.append("expected_return_required_feature_missing")
    mfe_missing = bool(item.get("mfe_required_feature_missing", False)) or bool(
        item.get("expected_mfe_required_feature_missing", False)
    )
    if mfe_missing:
        rejection_reasons.append("mfe_required_feature_missing")
    mae_missing = bool(item.get("mae_required_feature_missing", False)) or bool(
        item.get("expected_mae_required_feature_missing", False)
    )
    if mae_missing:
        rejection_reasons.append("mae_required_feature_missing")
    for head_name, reason in (
        ("expected_return", "expected_return_feature_screen_metadata_missing"),
        ("mfe", "mfe_feature_screen_metadata_missing"),
        ("mae", "mae_feature_screen_metadata_missing"),
    ):
        if bool(item.get(f"{head_name}_feature_screen_metadata_missing", False)):
            rejection_reasons.append(reason)
        feature_screen_schema = str(item.get(f"{head_name}_feature_screen_schema") or "")
        target_normalization_schema = str(
            item.get(f"{head_name}_target_normalization_schema_version") or ""
        )
        if (
            feature_screen_schema == "path_metric_target_specific_feature_screen_v1"
            and target_normalization_schema != PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
        ):
            rejection_reasons.append(f"{head_name}_target_normalization_metadata_missing")
    for head_name, output_column, metadata_reason, magnitude_reason, signed_reason in (
        (
            "mfe",
            "expected_mfe",
            "mfe_domain_metadata_missing",
            "mfe_magnitude_prediction_invalid",
            "mfe_prediction_sign_contract_failed",
        ),
        (
            "mae",
            "expected_mae",
            "mae_domain_metadata_missing",
            "mae_magnitude_prediction_invalid",
            "mae_prediction_sign_contract_failed",
        ),
    ):
        if (
            str(item.get(f"{head_name}_path_head_capability_state") or "")
            == PATH_HEAD_CAPABILITY_RETIRED_UNSUITABLE_ESTIMATOR
        ):
            retirement_reason = str(
                item.get(f"{head_name}_path_head_retirement_reason")
                or LINEAR_PATH_HEAD_RETIREMENT_REASON
            )
            rejection_reasons.append(f"{head_name}_{retirement_reason}")
        if bool(item.get(f"{head_name}_domain_metadata_missing", False)):
            rejection_reasons.append(metadata_reason)
        if bool(item.get(f"{output_column}_magnitude_prediction_invalid", False)):
            rejection_reasons.append(magnitude_reason)
        if bool(item.get(f"{output_column}_signed_prediction_invalid", False)):
            rejection_reasons.append(signed_reason)
    target_missing = bool(item.get("target_before_stop_required_feature_missing", False))
    if target_missing:
        rejection_reasons.append("target_before_stop_required_feature_missing")
    target_calibration_missing = bool(
        item.get("target_before_stop_calibration_metadata_missing", False)
    )
    if target_calibration_missing:
        rejection_reasons.append("target_before_stop_calibration_metadata_missing")
    for key in ("calibrated_probability", "target_before_stop_probability"):
        if key == "target_before_stop_probability" and (
            target_missing or target_calibration_missing
        ):
            continue
        probability = _finite_float(item.get(key))
        if not math.isfinite(probability) or probability < 0.0 or probability > 1.0:
            rejection_reasons.append("prediction_probability_contract_failed")
            break
    max_severity = 0.0
    for head in REGRESSION_HEADS:
        output_column = HEAD_OUTPUT_COLUMNS[head]
        if (
            (head == "return" and expected_return_missing)
            or (head == "mfe" and mfe_missing)
            or (head == "mae" and mae_missing)
        ):
            continue
        value = _finite_float(item.get(output_column))
        metadata_missing = bool(item.get(f"{output_column}_ood_metadata_missing", False))
        severity = _finite_float(item.get(f"{output_column}_ood_severity"))
        severity_limit = _finite_float(item.get(f"{output_column}_ood_severity_limit"))
        is_ood = bool(item.get(f"{output_column}_out_of_distribution", False))
        sign_valid = bool(item.get(f"{output_column}_sign_contract_valid", True))
        if metadata_missing:
            rejection_reasons.append("prediction_ood_metadata_missing")
        if not math.isfinite(value):
            rejection_reasons.append("nonfinite_prediction")
        if head == "mfe" and not sign_valid:
            rejection_reasons.append("mfe_prediction_sign_contract_failed")
        if head == "mae" and not sign_valid:
            rejection_reasons.append("mae_prediction_sign_contract_failed")
        if is_ood:
            warning_heads.append(head)
            if math.isfinite(severity):
                max_severity = max(max_severity, severity)
            warning_details.append(
                {
                    "head": head,
                    "raw_value": value,
                    "bound_low": item.get(f"{output_column}_ood_bound_low"),
                    "bound_high": item.get(f"{output_column}_ood_bound_high"),
                    "severity": severity,
                    "frozen_severity_limit": severity_limit,
                    "governance_version": item.get(f"{output_column}_ood_governance_version"),
                }
            )
            if not math.isfinite(severity) or not math.isfinite(severity_limit):
                rejection_reasons.append("prediction_ood_metadata_missing")
            elif severity > 1.0:
                rejection_reasons.append("catastrophic_prediction_extrapolation")
            elif severity > severity_limit:
                rejection_reasons.append(f"{head}_ood_severity_exceeds_frozen_limit")
    ordered_reasons = tuple(dict.fromkeys(rejection_reasons))
    return {
        "prediction_integrity_passed": not ordered_reasons,
        "prediction_integrity_rejection_reasons": ordered_reasons,
        "ood_warning": bool(warning_heads),
        "ood_affected_heads": tuple(dict.fromkeys(warning_heads)),
        "ood_warning_details": warning_details,
        "ood_max_severity": max_severity,
    }


def _build_scan_execution_identity(
    *,
    as_of_date: str,
    model_ids: tuple[str, ...],
    model_states: dict[str, str],
    model_eligibility: dict[str, bool],
    model_policy_hashes: dict[str, str],
    effective_policies: dict[str, SelectionPolicy],
    model_ood_metadata: dict[str, dict[str, object]],
    model_target_before_stop_feature_metadata: dict[str, dict[str, object]],
    model_target_before_stop_calibration_metadata: dict[str, dict[str, object]],
    model_path_feature_metadata: dict[str, dict[str, object]],
    model_path_domain_metadata: dict[str, dict[str, object]],
    scanner_config: ScannerConfig,
    universe_snapshot_id: str,
    feature_manifest_hash: str,
    feature_snapshot_hash_value: str,
    model_artifact_hashes: dict[str, str],
    model_generation_ids: dict[str, str],
    model_state_mode: str,
    include_challengers: bool,
    include_candidates: bool,
) -> tuple[ScanExecutionIdentity, dict[str, object]]:
    raw_config = _normalized_scanner_config(scanner_config)
    raw_config_hash = _stable_hash(raw_config)
    effective_policy_payload = {
        model_id: _normalized_policy(effective_policies.get(model_id)) for model_id in model_ids
    }
    effective_policy_bundle_hash = _stable_hash(effective_policy_payload)
    persisted_policy_hashes = {
        model_id: str(model_policy_hashes.get(model_id, "")) for model_id in model_ids
    }
    ood_metadata_payload = {
        model_id: model_ood_metadata.get(model_id, {}) for model_id in model_ids
    }
    ood_metadata_hash = _stable_hash(ood_metadata_payload)
    tbs_feature_metadata_payload = {
        model_id: model_target_before_stop_feature_metadata.get(model_id, {})
        for model_id in model_ids
    }
    tbs_feature_metadata_hash = _stable_hash(tbs_feature_metadata_payload)
    tbs_calibration_metadata_payload = {
        model_id: model_target_before_stop_calibration_metadata.get(model_id, {})
        for model_id in model_ids
    }
    tbs_calibration_metadata_hash = _stable_hash(tbs_calibration_metadata_payload)
    path_feature_metadata_payload = {
        model_id: model_path_feature_metadata.get(model_id, {}) for model_id in model_ids
    }
    path_feature_metadata_hash = _stable_hash(path_feature_metadata_payload)
    path_domain_metadata_payload = {
        model_id: model_path_domain_metadata.get(model_id, {}) for model_id in model_ids
    }
    path_domain_metadata_hash = _stable_hash(path_domain_metadata_payload)
    identity_payload: dict[str, object] = {
        "scanner_identity_schema_version": SCANNER_IDENTITY_SCHEMA_VERSION,
        "scanner_implementation_version": SCANNER_IMPLEMENTATION_VERSION,
        "prediction_ood_governance_schema_version": PREDICTION_OOD_GOVERNANCE_VERSION,
        "market_as_of_date": as_of_date,
        "universe_snapshot_id": universe_snapshot_id,
        "feature_manifest_hash": feature_manifest_hash,
        "feature_snapshot_hash": feature_snapshot_hash_value,
        "model_ids": list(model_ids),
        "model_artifact_hashes": {
            model_id: str(model_artifact_hashes.get(model_id, "")) for model_id in model_ids
        },
        "model_generation_ids": {
            model_id: str(model_generation_ids.get(model_id, "")) for model_id in model_ids
        },
        "model_states": {
            model_id: str(model_states.get(model_id, "UNKNOWN")) for model_id in model_ids
        },
        "model_eligibility": {
            model_id: bool(model_eligibility.get(model_id, False)) for model_id in model_ids
        },
        "model_state_mode": model_state_mode,
        "include_challengers": bool(include_challengers),
        "include_candidates": bool(include_candidates),
        "persisted_selection_policy_hashes": persisted_policy_hashes,
        "model_ood_governance_metadata": ood_metadata_payload,
        "model_ood_governance_metadata_hash": ood_metadata_hash,
        "target_before_stop_feature_metadata": tbs_feature_metadata_payload,
        "target_before_stop_feature_metadata_hash": tbs_feature_metadata_hash,
        "target_before_stop_calibration_metadata": tbs_calibration_metadata_payload,
        "target_before_stop_calibration_metadata_hash": tbs_calibration_metadata_hash,
        "path_metric_feature_metadata": path_feature_metadata_payload,
        "path_metric_feature_metadata_hash": path_feature_metadata_hash,
        "path_metric_domain_metadata": path_domain_metadata_payload,
        "path_metric_domain_metadata_hash": path_domain_metadata_hash,
        "effective_selection_policies": effective_policy_payload,
        "raw_scanner_config": raw_config,
        "raw_scanner_config_hash": raw_config_hash,
        "effective_policy_bundle_hash": effective_policy_bundle_hash,
        "canonical_candidate_ordering_version": CANONICAL_CANDIDATE_TIE_BREAKING_RULE,
        "canonical_candidate_ordering": list(CANONICAL_CANDIDATE_ORDER),
    }
    metadata = {
        "scanner_identity_schema_version": SCANNER_IDENTITY_SCHEMA_VERSION,
        "scanner_implementation_version": SCANNER_IMPLEMENTATION_VERSION,
        "raw_scanner_config_json": dumps(raw_config),
        "raw_scanner_config_hash": raw_config_hash,
        "persisted_model_policy_hashes": persisted_policy_hashes,
        "model_ood_governance_metadata_json": dumps(ood_metadata_payload),
        "model_ood_governance_metadata_hash": ood_metadata_hash,
        "target_before_stop_feature_metadata_json": dumps(tbs_feature_metadata_payload),
        "target_before_stop_feature_metadata_hash": tbs_feature_metadata_hash,
        "target_before_stop_calibration_metadata_json": dumps(tbs_calibration_metadata_payload),
        "target_before_stop_calibration_metadata_hash": tbs_calibration_metadata_hash,
        "path_metric_feature_metadata_json": dumps(path_feature_metadata_payload),
        "path_metric_feature_metadata_hash": path_feature_metadata_hash,
        "path_metric_domain_metadata_json": dumps(path_domain_metadata_payload),
        "path_metric_domain_metadata_hash": path_domain_metadata_hash,
        "effective_model_policy_json": dumps(effective_policy_payload),
        "effective_policy_bundle_hash": effective_policy_bundle_hash,
        "canonical_scan_execution_identity": identity_payload,
        "canonical_scan_execution_identity_json": dumps(identity_payload),
        "feature_manifest_hash": feature_manifest_hash,
        "feature_snapshot_hash": feature_snapshot_hash_value,
        "universe_snapshot_id": universe_snapshot_id,
        "model_generation_ids": identity_payload["model_generation_ids"],
        "model_ids": list(model_ids),
    }
    return ScanExecutionIdentity(identity_payload), metadata


def _metadata_matches_scan_identity(
    row: Any,
    *,
    scan_id: str,
    expected_metadata: dict[str, object],
) -> bool:
    try:
        metadata = loads(str(row["metadata_json"]))
    except (json.JSONDecodeError, TypeError, KeyError):
        return False
    if not isinstance(metadata, dict):
        return False
    actual_model_ids = metadata.get("model_ids")
    expected_model_ids = expected_metadata.get("model_ids")
    if not isinstance(actual_model_ids, list) or not isinstance(expected_model_ids, list):
        return False
    return (
        metadata.get("final_scan_id") == scan_id
        and metadata.get("scanner_identity_schema_version") == SCANNER_IDENTITY_SCHEMA_VERSION
        and metadata.get("canonical_scan_execution_identity")
        == expected_metadata["canonical_scan_execution_identity"]
        and metadata.get("raw_scanner_config_hash") == expected_metadata["raw_scanner_config_hash"]
        and metadata.get("effective_policy_bundle_hash")
        == expected_metadata["effective_policy_bundle_hash"]
        and metadata.get("model_ood_governance_metadata_hash")
        == expected_metadata["model_ood_governance_metadata_hash"]
        and metadata.get("target_before_stop_feature_metadata_hash")
        == expected_metadata["target_before_stop_feature_metadata_hash"]
        and metadata.get("target_before_stop_calibration_metadata_hash")
        == expected_metadata["target_before_stop_calibration_metadata_hash"]
        and metadata.get("path_metric_feature_metadata_hash")
        == expected_metadata["path_metric_feature_metadata_hash"]
        and metadata.get("path_metric_domain_metadata_hash")
        == expected_metadata["path_metric_domain_metadata_hash"]
        and metadata.get("feature_manifest_hash") == expected_metadata["feature_manifest_hash"]
        and metadata.get("universe_snapshot_id") == expected_metadata["universe_snapshot_id"]
        and metadata.get("model_generation_ids") == expected_metadata["model_generation_ids"]
        and actual_model_ids == expected_model_ids
    )


def _resolve_scan_id_and_cached_row(
    connection: Any,
    *,
    identity: ScanExecutionIdentity,
    metadata: dict[str, object],
) -> tuple[str, Any | None]:
    identity_payload = identity.to_jsonable()
    conflict_index = 0
    while True:
        scan_id = _scan_id_from_identity(identity_payload, conflict_index=conflict_index)
        existing = connection.execute(
            "SELECT csv_path, parquet_path, metadata_json FROM scanner_snapshots WHERE scan_id = ?",
            (scan_id,),
        ).fetchone()
        if existing is None:
            return scan_id, None
        if (
            Path(existing["csv_path"]).exists()
            and Path(existing["parquet_path"]).exists()
            and _metadata_matches_scan_identity(
                existing,
                scan_id=scan_id,
                expected_metadata=metadata,
            )
        ):
            return scan_id, existing
        conflict_index += 1


def _persist_scanner_candidates(db_path: str | Path, rows: pd.DataFrame) -> None:
    with engine_connection(db_path) as connection:
        for _, row in rows.iterrows():
            item = row.to_dict()
            connection.execute(
                """
                INSERT OR IGNORE INTO scanner_candidates (
                    scan_id, ticker, direction, horizon, model_id, candidate_status,
                    exclusion_reason, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["scan_id"],
                    item["ticker"],
                    item["direction"],
                    int(item["horizon"]),
                    item["model_id"],
                    item["candidate_status"],
                    item.get("exclusion_reason", ""),
                    dumps(item),
                ),
            )


def _apply_scanner_caps(
    rows: pd.DataFrame,
    *,
    policies: dict[str, SelectionPolicy],
) -> pd.DataFrame:
    capped = rows.copy()
    for model_id, policy in policies.items():
        model_mask = capped["model_id"].astype(str) == model_id
        actionable_mask = model_mask & (capped["candidate_status"] == "ACTIONABLE_PAPER_CANDIDATE")
        candidates = capped.loc[actionable_mask]
        if candidates.empty:
            continue
        kept_indexes = select_policy_cap_indexes(candidates, policy, date_column="as_of_date")
        rejected = actionable_mask & ~capped.index.isin(kept_indexes)
        capped.loc[rejected, "candidate_status"] = "REJECTED"
        capped.loc[rejected, "exclusion_reason"] = "exceeds_selection_cap"
    return capped


def run_scanner(
    feature_panel: pd.DataFrame,
    *,
    bundles: tuple[ModelBundle, ...],
    db_path: str | Path,
    output_dir: str | Path,
    universe_snapshot_id: str,
    model_states: dict[str, str] | None = None,
    model_eligibility: dict[str, bool] | None = None,
    feature_manifest_hash: str = "unknown",
    model_artifact_hashes: dict[str, str] | None = None,
    model_generation_ids: dict[str, str] | None = None,
    model_state_mode: str = "explicit",
    include_challengers: bool = False,
    include_candidates: bool = False,
    config: ScannerConfig | None = None,
) -> ScannerSnapshot:
    config = config or ScannerConfig()
    model_states = model_states or {bundle.model_id: "CHAMPION" for bundle in bundles}
    if model_eligibility is None:
        model_eligibility = {bundle.model_id: True for bundle in bundles}
    if not bundles:
        raise ValueError("No deployed champion models are available for scanning")
    bundles = tuple(sorted(bundles, key=lambda bundle: bundle.model_id))
    bundles_by_id = {bundle.model_id: bundle for bundle in bundles}
    model_artifact_hashes = model_artifact_hashes or {}
    model_generation_ids = model_generation_ids or {}
    model_policies: dict[str, SelectionPolicy | None] = {}
    model_policy_hashes: dict[str, str | None] = {}
    effective_policies: dict[str, SelectionPolicy] = {}
    for bundle in bundles:
        policy, policy_hash = selection_policy_from_metrics(bundle.metrics)
        model_policies[bundle.model_id] = policy
        model_policy_hashes[bundle.model_id] = policy_hash
        if policy is not None:
            effective_policies[bundle.model_id] = effective_selection_policy(
                policy,
                probability_threshold=config.probability_threshold,
                expected_return_threshold=config.expected_return_threshold,
                target_before_stop_threshold=config.target_before_stop_threshold,
                liquidity_threshold=config.minimum_dollar_volume,
                top_n_limit=config.top_n_per_direction,
            )
    as_of = pd.Timestamp(feature_panel["Date"].max())
    latest = feature_panel.loc[pd.to_datetime(feature_panel["Date"]) == as_of].copy()
    if latest.empty:
        raise ValueError("No latest feature rows available for scanning")
    snapshot_hash = feature_snapshot_hash(latest)
    model_ids = tuple(sorted(bundle.model_id for bundle in bundles))
    normalized_model_states = {
        model_id: model_states.get(model_id, "UNKNOWN") for model_id in model_ids
    }
    normalized_model_eligibility = {
        model_id: bool(model_eligibility.get(model_id, False)) for model_id in model_ids
    }
    normalized_policy_hashes = {
        model_id: str(model_policy_hashes.get(model_id) or "") for model_id in model_ids
    }
    normalized_artifact_hashes = {
        model_id: str(
            model_artifact_hashes.get(model_id)
            or _bundle_metric_string(bundles_by_id[model_id], "artifact_hash")
        )
        for model_id in model_ids
    }
    normalized_generation_ids = {
        model_id: str(
            model_generation_ids.get(model_id)
            or _bundle_metric_string(bundles_by_id[model_id], "generation")
        )
        for model_id in model_ids
    }
    normalized_ood_metadata = {
        model_id: bundle_ood_identity(bundles_by_id[model_id].metrics) for model_id in model_ids
    }
    normalized_tbs_feature_metadata = {
        model_id: {
            "schema_version": bundle_feature_screen_metadata(
                bundles_by_id[model_id], TARGET_BEFORE_STOP_HEAD
            ).get("screening_schema_version", "legacy_shared_feature_screen"),
            "target_before_stop_feature_manifest_hash": bundle_head_feature_manifest(
                bundles_by_id[model_id], TARGET_BEFORE_STOP_HEAD
            ),
        }
        for model_id in model_ids
    }
    normalized_tbs_calibration_metadata = {
        model_id: bundle_tbs_calibration_metadata(bundles_by_id[model_id]) for model_id in model_ids
    }
    normalized_path_feature_metadata = {}
    normalized_path_domain_metadata = {}
    for model_id in model_ids:
        bundle = bundles_by_id[model_id]
        head_payload: dict[str, object] = {}
        for head in PATH_METRIC_HEADS:
            metadata = bundle_feature_screen_metadata(bundle, head)
            head_payload[head] = {
                "schema_version": metadata.get(
                    "screening_schema_version", "legacy_shared_path_feature_screen"
                ),
                "target_label_name": metadata.get("target_label_name", ""),
                "external_target_name": metadata.get("external_target_name", ""),
                "internal_target_name": metadata.get("internal_target_name", ""),
                "internal_magnitude_target_name": metadata.get(
                    "internal_magnitude_target_name", ""
                ),
                "target_normalization_schema_version": metadata.get(
                    "target_normalization_schema_version", ""
                ),
                "target_normalization_method": metadata.get("target_normalization_method", ""),
                "target_normalization_atr_feature_name": metadata.get(
                    "atr_feature_name", PATH_TARGET_ATR_FEATURE
                )
                if metadata.get("target_normalization_schema_version")
                == PATH_TARGET_NORMALIZATION_SCHEMA_VERSION
                else "",
                "target_normalization_hash": metadata.get("target_normalization_hash", ""),
                "prediction_mapping_version": metadata.get("prediction_mapping_version", ""),
                "selected_feature_count": metadata.get("selected_feature_count", ""),
                "selected_feature_families": metadata.get("selected_feature_families", {}),
                "selected_feature_manifest_hash": bundle_head_feature_manifest(bundle, head),
            }
        normalized_path_feature_metadata[model_id] = head_payload
        domain_payload: dict[str, object] = {}
        for head in PATH_MAGNITUDE_HEADS:
            metadata = bundle_path_domain_metadata(bundle, head)
            domain_payload[head] = {
                "domain_schema_version": metadata.get(
                    "domain_schema_version", "legacy_unconstrained_path_metric_model"
                ),
                "external_target_name": metadata.get("external_target_name", ""),
                "internal_magnitude_target_name": metadata.get(
                    "internal_magnitude_target_name", ""
                ),
                "estimator_class": metadata.get("estimator_class", ""),
                "estimator_loss": metadata.get("estimator_loss", ""),
                "estimator_hash": metadata.get("estimator_hash", ""),
                "prediction_mapping_version": metadata.get("prediction_mapping_version", ""),
                "target_normalization_schema_version": metadata.get(
                    "target_normalization_schema_version", ""
                ),
                "target_normalization_atr_feature_name": metadata.get("atr_feature_name", ""),
                "target_normalization_hash": metadata.get("target_normalization_hash", ""),
                "internal_target_unit": metadata.get("internal_target_unit", ""),
                "canonical_external_unit": metadata.get("canonical_external_unit", ""),
                "path_head_capability_state": metadata.get("path_head_capability_state", ""),
                "path_head_retirement_schema_version": metadata.get(
                    "path_head_retirement_schema_version", ""
                ),
                "path_head_retirement_reason": metadata.get("path_head_retirement_reason", ""),
                "selected_feature_manifest_hash": metadata.get(
                    "selected_feature_manifest_hash", ""
                ),
            }
        normalized_path_domain_metadata[model_id] = domain_payload
    identity, metadata = _build_scan_execution_identity(
        as_of_date=as_of.date().isoformat(),
        model_ids=model_ids,
        model_states=normalized_model_states,
        model_eligibility=normalized_model_eligibility,
        model_policy_hashes=normalized_policy_hashes,
        effective_policies=effective_policies,
        model_ood_metadata=normalized_ood_metadata,
        model_target_before_stop_feature_metadata=normalized_tbs_feature_metadata,
        model_target_before_stop_calibration_metadata=normalized_tbs_calibration_metadata,
        model_path_feature_metadata=normalized_path_feature_metadata,
        model_path_domain_metadata=normalized_path_domain_metadata,
        scanner_config=config,
        universe_snapshot_id=universe_snapshot_id,
        feature_manifest_hash=feature_manifest_hash,
        feature_snapshot_hash_value=snapshot_hash,
        model_artifact_hashes=normalized_artifact_hashes,
        model_generation_ids=normalized_generation_ids,
        model_state_mode=model_state_mode,
        include_challengers=include_challengers,
        include_candidates=include_candidates,
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    with engine_connection(db_path) as connection:
        scan_id, existing = _resolve_scan_id_and_cached_row(
            connection,
            identity=identity,
            metadata=metadata,
        )
        if existing is not None:
            existing_rows = pd.read_csv(existing["csv_path"])
            _persist_scanner_candidates(db_path, existing_rows)
            return ScannerSnapshot(
                scan_id=scan_id,
                as_of_date=as_of.date().isoformat(),
                created_at_utc="existing",
                rows=existing_rows,
                csv_path=Path(existing["csv_path"]),
                parquet_path=Path(existing["parquet_path"]),
            )
    csv_path = output / f"{scan_id}_scanner.csv"
    parquet_path = output / f"{scan_id}_scanner.parquet"

    candidate_frames: list[pd.DataFrame] = []
    for bundle in bundles:
        predictions = predict_bundle(bundle, latest)
        candidate_frames.append(predictions)
    predictions = pd.concat(candidate_frames, ignore_index=True)
    enriched = predictions.merge(
        latest,
        on=["Date", "symbol"],
        how="left",
        suffixes=("", "_feature"),
    )
    rows: list[dict[str, object]] = []
    for _, row in enriched.iterrows():
        item = {str(key): value for key, value in row.to_dict().items()}
        dollar_volume = float(item.get("dollar_volume", 0.0) or 0.0)
        probability = float(item["calibrated_probability"])
        target_before_stop_probability = float(item["target_before_stop_probability"])
        expected_return = float(item["expected_return"])
        model_id = str(item["model_id"])
        model_state = model_states.get(model_id, "UNKNOWN")
        quality_eligible = bool(model_eligibility.get(model_id, False))
        persisted_policy = model_policies.get(model_id)
        effective_policy = effective_policies.get(model_id)
        policy_hash = model_policy_hashes.get(model_id)
        prediction_integrity = _prediction_integrity_result(item)
        status = "ACTIONABLE_PAPER_CANDIDATE"
        exclusion = ""
        if model_state not in {"CHAMPION", "CHALLENGER"}:
            status = "REJECTED"
            exclusion = "model_not_promoted"
        elif not quality_eligible:
            status = "REJECTED"
            exclusion = "model_quality_gates_failed"
        elif persisted_policy is None or effective_policy is None:
            status = "REJECTED"
            exclusion = "persisted_selection_policy_missing"
        else:
            policy_values = {str(key): value for key, value in item.items()}
            policy_values.update(
                {
                    "calibrated_probability": probability,
                    "expected_return": expected_return,
                    "target_before_stop_probability": target_before_stop_probability,
                    "liquidity_score": dollar_volume,
                }
            )
            selection_result = evaluate_candidate_policy(
                policy_values,
                effective_policy,
                policy_hash=policy_hash,
            )
            if not selection_result.passed:
                status = "REJECTED"
                exclusion = ";".join(selection_result.rejection_reasons)
        if not bool(prediction_integrity["prediction_integrity_passed"]):
            rejection_reasons = cast(
                tuple[object, ...],
                prediction_integrity["prediction_integrity_rejection_reasons"],
            )
            integrity_exclusion = ";".join(str(reason) for reason in rejection_reasons)
            status = "REJECTED"
            exclusion = (
                integrity_exclusion if not exclusion else f"{exclusion};{integrity_exclusion}"
            )
        bundle = bundles_by_id[model_id]
        path_screen_metadata = {
            EXPECTED_RETURN_HEAD: bundle_feature_screen_metadata(bundle, EXPECTED_RETURN_HEAD),
            MFE_HEAD: bundle_feature_screen_metadata(bundle, MFE_HEAD),
            MAE_HEAD: bundle_feature_screen_metadata(bundle, MAE_HEAD),
        }
        path_domain_metadata = {
            MFE_HEAD: bundle_path_domain_metadata(bundle, MFE_HEAD),
            MAE_HEAD: bundle_path_domain_metadata(bundle, MAE_HEAD),
        }
        path_selected_families_text: dict[str, str] = {}
        for head, screen_metadata in path_screen_metadata.items():
            selected_families = screen_metadata.get("selected_feature_families", {})
            path_selected_families_text[head] = (
                "; ".join(
                    f"{family}:{count}"
                    for family, count in sorted(cast(dict[str, object], selected_families).items())
                )
                if isinstance(selected_families, dict)
                else ""
            )
        tbs_screen_metadata = bundle_feature_screen_metadata(bundle, TARGET_BEFORE_STOP_HEAD)
        tbs_selected_families = tbs_screen_metadata.get("selected_feature_families", {})
        tbs_selected_families_text = (
            "; ".join(
                f"{family}:{count}"
                for family, count in sorted(cast(dict[str, object], tbs_selected_families).items())
            )
            if isinstance(tbs_selected_families, dict)
            else ""
        )
        attribution = explain_candidate(bundle, row)
        top_categories = sorted(
            attribution.contribution_share.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:4]
        analog_records: list[dict[str, object]] = []
        if not attribution.analogs.empty:
            for record in attribution.analogs.head(5).to_dict(orient="records"):
                analog_records.append(
                    {
                        str(key): (value.isoformat() if hasattr(value, "isoformat") else value)
                        for key, value in record.items()
                    }
                )
        utility = probability * expected_return
        rows.append(
            {
                "scan_id": scan_id,
                "as_of_date": as_of.date().isoformat(),
                "ticker": item["symbol"],
                "direction": "Bullish" if item["direction"] == "bull" else "Bearish",
                "horizon": int(item["horizon"]),
                "signal_close": float(item.get("Close", float("nan"))),
                "calibrated_probability": probability,
                "expected_return": expected_return,
                "expected_return_raw": float(item.get("expected_return_raw", expected_return)),
                "expected_return_transformed": float(
                    item.get("expected_return_transformed", expected_return)
                ),
                "expected_return_internal_atr_units": item.get(
                    "expected_return_internal_atr_units"
                ),
                "expected_return_target_normalization_schema_version": item.get(
                    "expected_return_target_normalization_schema_version", ""
                ),
                "expected_return_target_normalization_hash": item.get(
                    "expected_return_target_normalization_hash", ""
                ),
                "expected_return_target_normalization_atr_feature_name": item.get(
                    "expected_return_target_normalization_atr_feature_name", ""
                ),
                "expected_return_target_prediction_mapping_version": item.get(
                    "expected_return_target_prediction_mapping_version", ""
                ),
                "expected_return_out_of_distribution": bool(
                    item.get("expected_return_out_of_distribution", False)
                ),
                "expected_return_ood_severity": item.get("expected_return_ood_severity"),
                "expected_return_ood_bound_low": item.get("expected_return_ood_bound_low"),
                "expected_return_ood_bound_high": item.get("expected_return_ood_bound_high"),
                "expected_return_ood_severity_limit": item.get(
                    "expected_return_ood_severity_limit"
                ),
                "expected_return_feature_screen_schema": item.get(
                    "expected_return_feature_screen_schema", ""
                ),
                "expected_return_feature_manifest_hash": item.get(
                    "expected_return_feature_manifest_hash", ""
                ),
                "expected_return_selected_feature_count": path_screen_metadata[
                    EXPECTED_RETURN_HEAD
                ].get("selected_feature_count", ""),
                "expected_return_selected_feature_families": path_selected_families_text[
                    EXPECTED_RETURN_HEAD
                ],
                "expected_return_required_feature_missing": bool(
                    item.get("expected_return_required_feature_missing", False)
                ),
                "expected_return_missing_features": item.get(
                    "expected_return_missing_features", ""
                ),
                "expected_return_feature_screen_metadata_missing": bool(
                    item.get("expected_return_feature_screen_metadata_missing", False)
                ),
                "expected_mfe": float(item["expected_mfe"]),
                "expected_mfe_raw": float(item.get("expected_mfe_raw", item["expected_mfe"])),
                "expected_mfe_transformed": float(
                    item.get("expected_mfe_transformed", item["expected_mfe"])
                ),
                "expected_mfe_internal_magnitude": float(
                    item.get("expected_mfe_internal_magnitude", float("nan"))
                ),
                "expected_mfe_internal_magnitude_atr_units": item.get(
                    "expected_mfe_internal_magnitude_atr_units"
                ),
                "mfe_target_normalization_schema_version": item.get(
                    "mfe_target_normalization_schema_version", ""
                ),
                "mfe_target_normalization_hash": item.get("mfe_target_normalization_hash", ""),
                "mfe_target_normalization_atr_feature_name": item.get(
                    "mfe_target_normalization_atr_feature_name", ""
                ),
                "expected_mfe_magnitude_prediction_invalid": bool(
                    item.get("expected_mfe_magnitude_prediction_invalid", False)
                ),
                "expected_mfe_signed_prediction_invalid": bool(
                    item.get("expected_mfe_signed_prediction_invalid", False)
                ),
                "expected_mfe_magnitude_domain_valid": bool(
                    item.get("expected_mfe_magnitude_domain_valid", False)
                ),
                "expected_mfe_signed_domain_valid": bool(
                    item.get("expected_mfe_signed_domain_valid", False)
                ),
                "expected_mfe_out_of_distribution": bool(
                    item.get("expected_mfe_out_of_distribution", False)
                ),
                "expected_mfe_ood_severity": item.get("expected_mfe_ood_severity"),
                "expected_mfe_ood_bound_low": item.get("expected_mfe_ood_bound_low"),
                "expected_mfe_ood_bound_high": item.get("expected_mfe_ood_bound_high"),
                "expected_mfe_ood_severity_limit": item.get("expected_mfe_ood_severity_limit"),
                "mfe_feature_screen_schema": item.get("mfe_feature_screen_schema", ""),
                "mfe_feature_manifest_hash": item.get("mfe_feature_manifest_hash", ""),
                "mfe_selected_feature_count": path_screen_metadata[MFE_HEAD].get(
                    "selected_feature_count", ""
                ),
                "mfe_selected_feature_families": path_selected_families_text[MFE_HEAD],
                "mfe_required_feature_missing": bool(
                    item.get("mfe_required_feature_missing", False)
                    or item.get("expected_mfe_required_feature_missing", False)
                ),
                "mfe_missing_features": item.get(
                    "mfe_missing_features", item.get("expected_mfe_missing_features", "")
                ),
                "mfe_feature_screen_metadata_missing": bool(
                    item.get("mfe_feature_screen_metadata_missing", False)
                ),
                "mfe_domain_schema_version": item.get("mfe_domain_schema_version", ""),
                "mfe_path_head_capability_state": item.get("mfe_path_head_capability_state", ""),
                "mfe_path_head_retired": bool(item.get("mfe_path_head_retired", False)),
                "mfe_path_head_retirement_schema_version": item.get(
                    "mfe_path_head_retirement_schema_version", ""
                ),
                "mfe_path_head_retirement_reason": item.get("mfe_path_head_retirement_reason", ""),
                "mfe_domain_metadata_missing": bool(item.get("mfe_domain_metadata_missing", False)),
                "mfe_external_target_name": item.get("mfe_external_target_name", ""),
                "mfe_internal_magnitude_target_name": item.get(
                    "mfe_internal_magnitude_target_name", ""
                ),
                "mfe_internal_target_definition": item.get("mfe_internal_target_definition", ""),
                "mfe_magnitude_estimator_class": item.get("mfe_magnitude_estimator_class", ""),
                "mfe_magnitude_estimator_loss": item.get("mfe_magnitude_estimator_loss", ""),
                "mfe_magnitude_estimator_hash": item.get("mfe_magnitude_estimator_hash", ""),
                "mfe_prediction_mapping_version": item.get("mfe_prediction_mapping_version", ""),
                "mfe_domain_metadata_hash": (
                    _stable_hash(path_domain_metadata[MFE_HEAD])
                    if path_domain_metadata[MFE_HEAD]
                    else ""
                ),
                "expected_mae": float(item["expected_mae"]),
                "expected_mae_raw": float(item.get("expected_mae_raw", item["expected_mae"])),
                "expected_mae_transformed": float(
                    item.get("expected_mae_transformed", item["expected_mae"])
                ),
                "expected_mae_internal_magnitude": float(
                    item.get("expected_mae_internal_magnitude", float("nan"))
                ),
                "expected_mae_internal_magnitude_atr_units": item.get(
                    "expected_mae_internal_magnitude_atr_units"
                ),
                "mae_target_normalization_schema_version": item.get(
                    "mae_target_normalization_schema_version", ""
                ),
                "mae_target_normalization_hash": item.get("mae_target_normalization_hash", ""),
                "mae_target_normalization_atr_feature_name": item.get(
                    "mae_target_normalization_atr_feature_name", ""
                ),
                "expected_mae_magnitude_prediction_invalid": bool(
                    item.get("expected_mae_magnitude_prediction_invalid", False)
                ),
                "expected_mae_signed_prediction_invalid": bool(
                    item.get("expected_mae_signed_prediction_invalid", False)
                ),
                "expected_mae_magnitude_domain_valid": bool(
                    item.get("expected_mae_magnitude_domain_valid", False)
                ),
                "expected_mae_signed_domain_valid": bool(
                    item.get("expected_mae_signed_domain_valid", False)
                ),
                "expected_mae_out_of_distribution": bool(
                    item.get("expected_mae_out_of_distribution", False)
                ),
                "expected_mae_ood_severity": item.get("expected_mae_ood_severity"),
                "expected_mae_ood_bound_low": item.get("expected_mae_ood_bound_low"),
                "expected_mae_ood_bound_high": item.get("expected_mae_ood_bound_high"),
                "expected_mae_ood_severity_limit": item.get("expected_mae_ood_severity_limit"),
                "mae_feature_screen_schema": item.get("mae_feature_screen_schema", ""),
                "mae_feature_manifest_hash": item.get("mae_feature_manifest_hash", ""),
                "mae_selected_feature_count": path_screen_metadata[MAE_HEAD].get(
                    "selected_feature_count", ""
                ),
                "mae_selected_feature_families": path_selected_families_text[MAE_HEAD],
                "mae_required_feature_missing": bool(
                    item.get("mae_required_feature_missing", False)
                    or item.get("expected_mae_required_feature_missing", False)
                ),
                "mae_missing_features": item.get(
                    "mae_missing_features", item.get("expected_mae_missing_features", "")
                ),
                "mae_feature_screen_metadata_missing": bool(
                    item.get("mae_feature_screen_metadata_missing", False)
                ),
                "mae_domain_schema_version": item.get("mae_domain_schema_version", ""),
                "mae_path_head_capability_state": item.get("mae_path_head_capability_state", ""),
                "mae_path_head_retired": bool(item.get("mae_path_head_retired", False)),
                "mae_path_head_retirement_schema_version": item.get(
                    "mae_path_head_retirement_schema_version", ""
                ),
                "mae_path_head_retirement_reason": item.get("mae_path_head_retirement_reason", ""),
                "mae_domain_metadata_missing": bool(item.get("mae_domain_metadata_missing", False)),
                "mae_external_target_name": item.get("mae_external_target_name", ""),
                "mae_internal_magnitude_target_name": item.get(
                    "mae_internal_magnitude_target_name", ""
                ),
                "mae_internal_target_definition": item.get("mae_internal_target_definition", ""),
                "mae_magnitude_estimator_class": item.get("mae_magnitude_estimator_class", ""),
                "mae_magnitude_estimator_loss": item.get("mae_magnitude_estimator_loss", ""),
                "mae_magnitude_estimator_hash": item.get("mae_magnitude_estimator_hash", ""),
                "mae_prediction_mapping_version": item.get("mae_prediction_mapping_version", ""),
                "mae_domain_metadata_hash": (
                    _stable_hash(path_domain_metadata[MAE_HEAD])
                    if path_domain_metadata[MAE_HEAD]
                    else ""
                ),
                "target_before_stop_probability": target_before_stop_probability,
                "target_before_stop_raw_probability": item.get(
                    "target_before_stop_raw_probability"
                ),
                "target_before_stop_feature_screen_schema": item.get(
                    "target_before_stop_feature_screen_schema", ""
                ),
                "target_before_stop_feature_manifest_hash": item.get(
                    "target_before_stop_feature_manifest_hash", ""
                ),
                "target_before_stop_selected_feature_count": tbs_screen_metadata.get(
                    "selected_feature_count", ""
                ),
                "target_before_stop_selected_feature_families": tbs_selected_families_text,
                "target_before_stop_required_feature_missing": bool(
                    item.get("target_before_stop_required_feature_missing", False)
                ),
                "target_before_stop_missing_features": item.get(
                    "target_before_stop_missing_features", ""
                ),
                "target_before_stop_calibration_governance_schema": item.get(
                    "target_before_stop_calibration_governance_schema", ""
                ),
                "target_before_stop_calibration_method": item.get(
                    "target_before_stop_calibration_method", ""
                ),
                "target_before_stop_calibration_manifest_hash": item.get(
                    "target_before_stop_calibration_manifest_hash", ""
                ),
                "target_before_stop_calibrator_artifact_hash": item.get(
                    "target_before_stop_calibrator_artifact_hash", ""
                ),
                "target_before_stop_calibration_metadata_missing": bool(
                    item.get("target_before_stop_calibration_metadata_missing", False)
                ),
                "ood_warning": bool(prediction_integrity["ood_warning"]),
                "ood_affected_heads": ";".join(
                    str(head)
                    for head in cast(tuple[object, ...], prediction_integrity["ood_affected_heads"])
                ),
                "ood_warning_details": dumps(prediction_integrity["ood_warning_details"]),
                "ood_max_severity": prediction_integrity["ood_max_severity"],
                "composite_utility_score": utility,
                "liquidity_score": dollar_volume,
                "regime": item.get("market_regime_label", "unknown"),
                "sector": item.get("sector", "unknown"),
                "top_attribution_categories": "; ".join(
                    f"{name}:{share:.1%}" for name, share in top_categories
                ),
                "top_confirming_relationships": "; ".join(attribution.relationship_confirmations),
                "top_divergences": "; ".join(attribution.relationship_divergences),
                "model_id": item["model_id"],
                "model_state": model_state,
                "model_quality_gate_eligible": quality_eligible,
                "selection_policy_hash": policy_hash or "",
                "feature_snapshot_hash": snapshot_hash,
                "candidate_status": status,
                "exclusion_reason": exclusion,
                "supporting_evidence": "; ".join(attribution.supporting_evidence[:5]),
                "historical_analogs": dumps(analog_records),
            }
        )
    result = pd.DataFrame(rows)
    result = _apply_scanner_caps(result, policies=effective_policies)
    result = (
        order_candidates(result)
        .groupby("direction", group_keys=False)
        .head(config.top_n_per_direction)
    )
    result.to_csv(csv_path, index=False)
    result.to_parquet(parquet_path, index=False)
    created_at = datetime.now(UTC).isoformat()
    persisted_metadata = {
        **metadata,
        "final_scan_id": scan_id,
    }
    with engine_connection(db_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO scanner_snapshots (
                scan_id, as_of_date, created_at_utc, model_ids_json, universe_snapshot_id,
                feature_snapshot_hash, csv_path, parquet_path, row_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                as_of.date().isoformat(),
                created_at,
                dumps(model_ids),
                universe_snapshot_id,
                snapshot_hash,
                str(csv_path),
                str(parquet_path),
                len(result),
                dumps(persisted_metadata),
            ),
        )
    _persist_scanner_candidates(db_path, result)
    return ScannerSnapshot(
        scan_id=scan_id,
        as_of_date=as_of.date().isoformat(),
        created_at_utc=created_at,
        rows=result,
        csv_path=csv_path,
        parquet_path=parquet_path,
    )
