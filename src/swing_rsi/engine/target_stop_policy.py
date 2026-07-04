from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

from swing_rsi.data.validation import validate_ohlcv
from swing_rsi.engine.labels import _atr, _first_touch
from swing_rsi.engine.product_scope import (
    PRODUCT_CLASS_SCOPE_ORDINARY,
    ProductClassScope,
    product_class_scope_for_role,
)

TARGET_STOP_POLICY_SCHEMA_VERSION = "target_stop_policy_candidate_v1"
TARGET_STOP_POLICY_DIAGNOSTIC_NOTICE = (
    "Experimental target/stop policy. Development evidence only. Not a live signal."
)
SECTOR_ROTATION_BUY_ORDINARY_BASELINE_POLICY_ID = (
    "sector_rotation_buy_ordinary_20d_default_t2p0_s1p0"
)
SECTOR_ROTATION_BUY_ORDINARY_CANDIDATE_POLICY_ID = (
    "sector_rotation_buy_ordinary_20d_experimental_t2p0_s1p25"
)
SECTOR_ROTATION_BUY_ORDINARY_CANDIDATE_HYPOTHESIS_ID = (
    "sector_rotation_buy_ordinary_20d_target_stop_candidate_v1"
)
NO_CALIBRATION_SUPPORTED_POLICY_CANDIDATE = "NO_CALIBRATION_SUPPORTED_POLICY_CANDIDATE"

TargetStopPolicyStatus = Literal[
    "DEFAULT_BASELINE",
    "EXPERIMENTAL_CANDIDATE",
    "RETIRED",
    "RESEARCH_ONLY",
]


@dataclass(frozen=True)
class TargetStopPolicyCandidate:
    policy_id: str
    policy_name: str
    archetype: str
    action: str
    product_scope: ProductClassScope
    horizon: int
    target_multiple: float
    stop_multiple: float
    entry_timing: str
    signal_known_timing: str
    time_exit_behavior: str
    same_bar_target_stop_ambiguity_policy: str
    cost_slippage_policy_reference: str
    selection_source: str
    governance_status: TargetStopPolicyStatus
    created_timestamp: str
    policy_hash: str

    def to_record(self) -> dict[str, object]:
        record = asdict(self)
        record["schema_version"] = TARGET_STOP_POLICY_SCHEMA_VERSION
        record["diagnostic_only_notice"] = TARGET_STOP_POLICY_DIAGNOSTIC_NOTICE
        record["compact_display"] = target_stop_policy_compact_display(self)
        return record


@dataclass(frozen=True)
class CalibrationPolicyEvidence:
    horizon: int
    target_multiple: float
    stop_multiple: float
    row_count: int
    target_before_stop_hit_rate: float
    stop_before_target_rate: float
    unresolved_rate: float
    average_forward_return: float
    median_forward_return: float
    average_mfe: float
    average_mae: float
    worst_mae: float
    expected_r: float
    cost_adjusted_utility: float
    symbol_concentration: float
    year_concentration: float
    regime_concentration: float
    evidence_source: str = "docs/SECTOR_ROTATION_BUY_ORDINARY_TARGET_STOP_DIAGNOSTIC.md"
    evidence_split: str = "calibration_only"

    def to_record(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TargetStopPolicySelectionResult:
    status: str
    reason: str
    baseline: CalibrationPolicyEvidence
    selected: CalibrationPolicyEvidence | None
    evidence_rows: tuple[CalibrationPolicyEvidence, ...]
    selected_policy: TargetStopPolicyCandidate | None


SECTOR_ROTATION_BUY_ORDINARY_CALIBRATION_EVIDENCE: tuple[CalibrationPolicyEvidence, ...] = (
    CalibrationPolicyEvidence(
        horizon=20,
        target_multiple=2.0,
        stop_multiple=1.0,
        row_count=11017,
        target_before_stop_hit_rate=0.3841,
        stop_before_target_rate=0.6016,
        unresolved_rate=0.0143,
        average_forward_return=0.0187,
        median_forward_return=0.0164,
        average_mfe=0.0665,
        average_mae=-0.0495,
        worst_mae=-0.4508,
        expected_r=0.1745,
        cost_adjusted_utility=0.0036,
        symbol_concentration=0.0435,
        year_concentration=0.5219,
        regime_concentration=0.3612,
    ),
    CalibrationPolicyEvidence(
        horizon=20,
        target_multiple=2.0,
        stop_multiple=1.25,
        row_count=11017,
        target_before_stop_hit_rate=0.4380,
        stop_before_target_rate=0.5360,
        unresolved_rate=0.0260,
        average_forward_return=0.0187,
        median_forward_return=0.0164,
        average_mfe=0.0665,
        average_mae=-0.0495,
        worst_mae=-0.4508,
        expected_r=0.2190,
        cost_adjusted_utility=0.0047,
        symbol_concentration=0.0435,
        year_concentration=0.5219,
        regime_concentration=0.3612,
    ),
    CalibrationPolicyEvidence(
        horizon=20,
        target_multiple=2.0,
        stop_multiple=1.5,
        row_count=11017,
        target_before_stop_hit_rate=0.4800,
        stop_before_target_rate=0.4820,
        unresolved_rate=0.0380,
        average_forward_return=0.0187,
        median_forward_return=0.0164,
        average_mfe=0.0665,
        average_mae=-0.0495,
        worst_mae=-0.4508,
        expected_r=0.2500,
        cost_adjusted_utility=0.0055,
        symbol_concentration=0.0435,
        year_concentration=0.5219,
        regime_concentration=0.3612,
    ),
    CalibrationPolicyEvidence(
        horizon=20,
        target_multiple=2.0,
        stop_multiple=2.0,
        row_count=11017,
        target_before_stop_hit_rate=0.5369,
        stop_before_target_rate=0.3874,
        unresolved_rate=0.0757,
        average_forward_return=0.0187,
        median_forward_return=0.0164,
        average_mfe=0.0665,
        average_mae=-0.0495,
        worst_mae=-0.4508,
        expected_r=0.3077,
        cost_adjusted_utility=0.0068,
        symbol_concentration=0.0435,
        year_concentration=0.5219,
        regime_concentration=0.3612,
    ),
)


def target_stop_policy_compact_display(policy: TargetStopPolicyCandidate) -> str:
    return (
        f"{policy.policy_name} · T{policy.target_multiple:g}/"
        f"S{policy.stop_multiple:g}/{policy.horizon}D"
    )


def sector_rotation_buy_ordinary_baseline_policy() -> TargetStopPolicyCandidate:
    return _make_policy(
        policy_id=SECTOR_ROTATION_BUY_ORDINARY_BASELINE_POLICY_ID,
        policy_name="Sector Rotation BUY Default Baseline",
        target_multiple=2.0,
        stop_multiple=1.0,
        governance_status="DEFAULT_BASELINE",
        selection_source="src/swing_rsi/engine/labels.py default LabelConfig",
    )


def target_stop_policy_registry() -> tuple[TargetStopPolicyCandidate, ...]:
    selection = select_sector_rotation_buy_ordinary_policy_candidate()
    policies = [sector_rotation_buy_ordinary_baseline_policy()]
    if selection.selected_policy is not None:
        policies.append(selection.selected_policy)
    return tuple(policies)


def select_sector_rotation_buy_ordinary_policy_candidate(
    evidence_rows: tuple[
        CalibrationPolicyEvidence, ...
    ] = SECTOR_ROTATION_BUY_ORDINARY_CALIBRATION_EVIDENCE,
) -> TargetStopPolicySelectionResult:
    baseline = _baseline_evidence(evidence_rows)
    wider_stop = sorted(
        (
            row
            for row in evidence_rows
            if row.horizon == baseline.horizon
            and row.target_multiple == baseline.target_multiple
            and row.stop_multiple > baseline.stop_multiple
        ),
        key=lambda row: row.stop_multiple,
    )
    for row in wider_stop:
        if _candidate_satisfies_selection_rule(row, baseline):
            return TargetStopPolicySelectionResult(
                status="CALIBRATION_SUPPORTED_POLICY_CANDIDATE",
                reason=(
                    "Smallest same-target same-horizon stop increase satisfying calibration-only "
                    "STOP_TOO_TIGHT selection rule."
                ),
                baseline=baseline,
                selected=row,
                evidence_rows=evidence_rows,
                selected_policy=_candidate_policy_from_evidence(row),
            )

    reduced_target = sorted(
        (
            row
            for row in evidence_rows
            if row.horizon == baseline.horizon
            and row.target_multiple < baseline.target_multiple
            and row.stop_multiple >= baseline.stop_multiple
        ),
        key=lambda row: (-row.target_multiple, row.stop_multiple),
    )
    for row in reduced_target:
        if _candidate_satisfies_selection_rule(row, baseline):
            return TargetStopPolicySelectionResult(
                status="CALIBRATION_SUPPORTED_POLICY_CANDIDATE",
                reason=(
                    "Target reduction fallback satisfying calibration-only selection rule after "
                    "no wider-stop candidate qualified."
                ),
                baseline=baseline,
                selected=row,
                evidence_rows=evidence_rows,
                selected_policy=_candidate_policy_from_evidence(row),
            )
    return TargetStopPolicySelectionResult(
        status=NO_CALIBRATION_SUPPORTED_POLICY_CANDIDATE,
        reason="No calibration-only target/stop grid row satisfied the precommitted rule.",
        baseline=baseline,
        selected=None,
        evidence_rows=evidence_rows,
        selected_policy=None,
    )


def candidate_policy_outcome_labels(
    policy: TargetStopPolicyCandidate,
) -> dict[str, str]:
    return {
        "target_before_stop": f"label_{policy.policy_id}_target_before_stop",
        "stop_before_target": f"label_{policy.policy_id}_stop_before_target",
        "unresolved": f"label_{policy.policy_id}_unresolved",
        "time_to_target": f"label_{policy.policy_id}_time_to_target",
        "time_to_stop": f"label_{policy.policy_id}_time_to_stop",
        "time_to_max_favorable_excursion": (
            f"label_{policy.policy_id}_time_to_max_favorable_excursion"
        ),
        "time_to_max_adverse_excursion": (
            f"label_{policy.policy_id}_time_to_max_adverse_excursion"
        ),
        "profitable_at_time_exit": f"label_{policy.policy_id}_profitable_at_time_exit",
        "profitable_at_horizon_despite_failing_tbs": (
            f"label_{policy.policy_id}_profitable_at_horizon_despite_failing_tbs"
        ),
    }


def augment_model_frame_with_policy_outcomes(
    model_frame: pd.DataFrame,
    policies: tuple[TargetStopPolicyCandidate, ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    derived = build_policy_outcomes(model_frame, policies)
    if derived.empty:
        return model_frame.copy(), derived
    augmented = model_frame.copy()
    label_columns = [
        column
        for column in derived.columns
        if str(column).startswith("label_") or column in {"Date", "symbol"}
    ]
    labels = derived[label_columns].copy()
    augmented["Date"] = pd.to_datetime(augmented["Date"], errors="coerce")
    labels["Date"] = pd.to_datetime(labels["Date"], errors="coerce")
    augmented = augmented.merge(labels, on=["Date", "symbol"], how="left", validate="one_to_one")
    return augmented, derived


def build_policy_outcomes(
    model_frame: pd.DataFrame,
    policies: tuple[TargetStopPolicyCandidate, ...],
    *,
    include_statuses: tuple[TargetStopPolicyStatus, ...] = ("EXPERIMENTAL_CANDIDATE",),
) -> pd.DataFrame:
    active = tuple(policy for policy in policies if policy.governance_status in include_statuses)
    if not active or model_frame.empty:
        return pd.DataFrame(columns=_derived_policy_outcome_columns(active))
    rows: list[dict[str, object]] = []
    for symbol, group in model_frame.groupby(model_frame["symbol"].astype(str), sort=True):
        scoped = group.copy()
        role = scoped["role"].iloc[0] if "role" in scoped.columns and not scoped.empty else ""
        if _scope_for_role(role) != PRODUCT_CLASS_SCOPE_ORDINARY:
            continue
        symbol_frame = scoped.sort_values("Date").reset_index(drop=True)
        for policy in active:
            rows.extend(_symbol_policy_outcome_rows(symbol, symbol_frame, policy))
    return pd.DataFrame(rows, columns=_derived_policy_outcome_columns(active))


def policy_registry_frame() -> pd.DataFrame:
    return pd.DataFrame([policy.to_record() for policy in target_stop_policy_registry()])


def calibration_selection_frame() -> pd.DataFrame:
    selection = select_sector_rotation_buy_ordinary_policy_candidate()
    selected_key = (
        (
            selection.selected.horizon,
            selection.selected.target_multiple,
            selection.selected.stop_multiple,
        )
        if selection.selected is not None
        else None
    )
    rows = []
    for row in selection.evidence_rows:
        key = (row.horizon, row.target_multiple, row.stop_multiple)
        rows.append(
            {
                "schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
                "selection_status": selection.status,
                "selection_reason": selection.reason,
                "selected": key == selected_key,
                "baseline": key
                == (
                    selection.baseline.horizon,
                    selection.baseline.target_multiple,
                    selection.baseline.stop_multiple,
                ),
                **row.to_record(),
            }
        )
    return pd.DataFrame(rows)


def sector_rotation_buy_ordinary_policy_comparison_frame() -> pd.DataFrame:
    selection = select_sector_rotation_buy_ordinary_policy_candidate()
    rows = [
        {
            "schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
            "policy_role": "baseline",
            "target_stop_policy_id": SECTOR_ROTATION_BUY_ORDINARY_BASELINE_POLICY_ID,
            "target_stop_policy_status": "DEFAULT_BASELINE",
            "selection_status": selection.status,
            **selection.baseline.to_record(),
        }
    ]
    if selection.selected is not None and selection.selected_policy is not None:
        rows.append(
            {
                "schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
                "policy_role": "experimental_candidate",
                "target_stop_policy_id": selection.selected_policy.policy_id,
                "target_stop_policy_status": selection.selected_policy.governance_status,
                "selection_status": selection.status,
                **selection.selected.to_record(),
            }
        )
    else:
        rows.append(
            {
                "schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
                "policy_role": "experimental_candidate",
                "target_stop_policy_id": "",
                "target_stop_policy_status": NO_CALIBRATION_SUPPORTED_POLICY_CANDIDATE,
                "selection_status": selection.status,
                "reason": selection.reason,
            }
        )
    return pd.DataFrame(rows)


DERIVED_POLICY_OUTCOME_COLUMNS = [
    "schema_version",
    "target_stop_policy_id",
    "target_stop_policy_name",
    "target_stop_policy_status",
    "target_stop_policy_hash",
    "archetype",
    "action",
    "scope",
    "horizon",
    "Date",
    "symbol",
    "entry_price",
    "target_price",
    "stop_price",
    "target_before_stop",
    "stop_before_target",
    "unresolved",
    "forward_return",
    "MFE",
    "MAE",
    "time_to_target",
    "time_to_stop",
    "time_to_max_favorable_excursion",
    "time_to_max_adverse_excursion",
    "profitable_at_time_exit",
    "profitable_at_horizon_despite_failing_tbs",
]


def _derived_policy_outcome_columns(
    policies: tuple[TargetStopPolicyCandidate, ...],
) -> list[str]:
    columns = list(DERIVED_POLICY_OUTCOME_COLUMNS)
    for policy in policies:
        for column in candidate_policy_outcome_labels(policy).values():
            if column not in columns:
                columns.append(column)
    return columns


def _make_policy(
    *,
    policy_id: str,
    policy_name: str,
    target_multiple: float,
    stop_multiple: float,
    governance_status: TargetStopPolicyStatus,
    selection_source: str,
) -> TargetStopPolicyCandidate:
    payload: dict[str, object] = {
        "policy_id": policy_id,
        "policy_name": policy_name,
        "archetype": "sector_rotation_buy",
        "action": "BUY",
        "product_scope": PRODUCT_CLASS_SCOPE_ORDINARY,
        "horizon": 20,
        "target_multiple": target_multiple,
        "stop_multiple": stop_multiple,
        "entry_timing": "next_session_open",
        "signal_known_timing": "daily_close_signal_known_after_close",
        "time_exit_behavior": "horizon_close_for_unresolved_rows",
        "same_bar_target_stop_ambiguity_policy": "stop_wins_when_target_and_stop_touch_same_bar",
        "cost_slippage_policy_reference": (
            "signal_discovery_round_trip_cost_5bps_slippage_not_in_tbs_label"
        ),
        "selection_source": selection_source,
        "governance_status": governance_status,
        "created_timestamp": "2026-06-30T00:00:00+00:00",
    }
    policy_hash = _stable_hash({"schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION, **payload})
    return TargetStopPolicyCandidate(
        policy_id=policy_id,
        policy_name=policy_name,
        archetype="sector_rotation_buy",
        action="BUY",
        product_scope=PRODUCT_CLASS_SCOPE_ORDINARY,
        horizon=20,
        target_multiple=target_multiple,
        stop_multiple=stop_multiple,
        entry_timing="next_session_open",
        signal_known_timing="daily_close_signal_known_after_close",
        time_exit_behavior="horizon_close_for_unresolved_rows",
        same_bar_target_stop_ambiguity_policy=("stop_wins_when_target_and_stop_touch_same_bar"),
        cost_slippage_policy_reference=(
            "signal_discovery_round_trip_cost_5bps_slippage_not_in_tbs_label"
        ),
        selection_source=selection_source,
        governance_status=governance_status,
        created_timestamp="2026-06-30T00:00:00+00:00",
        policy_hash=policy_hash,
    )


def _candidate_policy_from_evidence(
    evidence: CalibrationPolicyEvidence,
) -> TargetStopPolicyCandidate:
    return _make_policy(
        policy_id=SECTOR_ROTATION_BUY_ORDINARY_CANDIDATE_POLICY_ID,
        policy_name="Sector Rotation BUY Policy Candidate",
        target_multiple=evidence.target_multiple,
        stop_multiple=evidence.stop_multiple,
        governance_status="EXPERIMENTAL_CANDIDATE",
        selection_source=(
            "docs/SECTOR_ROTATION_BUY_ORDINARY_TARGET_STOP_DIAGNOSTIC.md "
            "calibration-only STOP_TOO_TIGHT grid"
        ),
    )


def _baseline_evidence(
    evidence_rows: tuple[CalibrationPolicyEvidence, ...],
) -> CalibrationPolicyEvidence:
    for row in evidence_rows:
        if row.horizon == 20 and row.target_multiple == 2.0 and row.stop_multiple == 1.0:
            return row
    raise ValueError("Missing Sector Rotation BUY ORDINARY baseline policy evidence")


def _candidate_satisfies_selection_rule(
    candidate: CalibrationPolicyEvidence,
    baseline: CalibrationPolicyEvidence,
) -> bool:
    if candidate.row_count != baseline.row_count or candidate.row_count <= 0:
        return False
    if candidate.target_before_stop_hit_rate <= baseline.target_before_stop_hit_rate:
        return False
    if candidate.stop_before_target_rate >= baseline.stop_before_target_rate:
        return False
    if candidate.average_forward_return < baseline.average_forward_return:
        return False
    if candidate.median_forward_return < baseline.median_forward_return:
        return False
    utility_better = candidate.cost_adjusted_utility > baseline.cost_adjusted_utility
    expected_r_better = candidate.expected_r > baseline.expected_r
    if not (utility_better or expected_r_better):
        return False
    return _concentration_not_materially_worse(candidate, baseline)


def _concentration_not_materially_worse(
    candidate: CalibrationPolicyEvidence,
    baseline: CalibrationPolicyEvidence,
) -> bool:
    tolerance = 0.05
    return (
        candidate.symbol_concentration <= baseline.symbol_concentration + tolerance
        and candidate.year_concentration <= baseline.year_concentration + tolerance
        and candidate.regime_concentration <= baseline.regime_concentration + tolerance
    )


def _symbol_policy_outcome_rows(
    symbol: str,
    frame: pd.DataFrame,
    policy: TargetStopPolicyCandidate,
) -> list[dict[str, object]]:
    data = frame.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"]).sort_values("Date").set_index("Date")
    if data.empty:
        return []
    validated = validate_ohlcv(data)
    atr = _atr(validated)
    horizon = int(policy.horizon)
    entry = validated["Open"].shift(-1)
    exit_close = validated["Close"].shift(-horizon)
    future_high = pd.concat(
        [validated["High"].shift(-offset) for offset in range(1, horizon + 1)],
        axis=1,
    )
    future_low = pd.concat(
        [validated["Low"].shift(-offset) for offset in range(1, horizon + 1)],
        axis=1,
    )
    target = entry + atr * float(policy.target_multiple)
    stop = entry - atr * float(policy.stop_multiple)
    labels = candidate_policy_outcome_labels(policy)
    rows: list[dict[str, object]] = []
    for position, date in enumerate(validated.index):
        if position + horizon >= len(validated) or position + 1 >= len(validated):
            rows.append(
                _empty_policy_outcome_row(
                    symbol,
                    date,
                    policy,
                    entry_price=_finite_or_nan(entry.iloc[position]),
                    target_price=_finite_or_nan(target.iloc[position]),
                    stop_price=_finite_or_nan(stop.iloc[position]),
                    labels=labels,
                )
            )
            continue
        high_slice = validated["High"].iloc[position + 1 : position + horizon + 1]
        low_slice = validated["Low"].iloc[position + 1 : position + horizon + 1]
        first_touch = _first_touch(
            high_slice,
            low_slice,
            float(target.iloc[position]),
            float(stop.iloc[position]),
            bullish=True,
        )
        entry_price = _finite_or_nan(entry.iloc[position])
        future_high_slice = future_high.iloc[position].dropna()
        future_low_slice = future_low.iloc[position].dropna()
        future_high_value = _safe_max(future_high_slice)
        future_low_value = _safe_min(future_low_slice)
        forward_return = _ratio_return(exit_close.iloc[position], entry_price)
        mfe = _ratio_return(future_high_value, entry_price)
        mae = _ratio_return(future_low_value, entry_price)
        tbs = bool(first_touch[0])
        stop_first = bool(first_touch[1])
        unresolved = not (tbs or stop_first)
        row = {
            "schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
            "target_stop_policy_id": policy.policy_id,
            "target_stop_policy_name": policy.policy_name,
            "target_stop_policy_status": policy.governance_status,
            "target_stop_policy_hash": policy.policy_hash,
            "archetype": policy.archetype,
            "action": policy.action,
            "scope": policy.product_scope,
            "horizon": policy.horizon,
            "Date": pd.Timestamp(date).date().isoformat(),
            "symbol": symbol,
            "entry_price": entry_price,
            "target_price": _finite_or_nan(target.iloc[position]),
            "stop_price": _finite_or_nan(stop.iloc[position]),
            "target_before_stop": float(tbs),
            "stop_before_target": float(stop_first),
            "unresolved": float(unresolved),
            "forward_return": forward_return,
            "MFE": mfe,
            "MAE": mae,
            "time_to_target": float(first_touch[2]) if first_touch[2] is not None else math.nan,
            "time_to_stop": float(first_touch[3]) if first_touch[3] is not None else math.nan,
            "time_to_max_favorable_excursion": _excursion_time(
                future_high_slice,
                want_max=True,
            ),
            "time_to_max_adverse_excursion": _excursion_time(
                future_low_slice,
                want_max=False,
            ),
            "profitable_at_time_exit": float(unresolved and forward_return > 0.0),
            "profitable_at_horizon_despite_failing_tbs": float((not tbs) and forward_return > 0.0),
        }
        for label_key, label_column in labels.items():
            source_key = _label_source_key(label_key)
            row[label_column] = row.get(source_key, math.nan)
        rows.append(row)
    return rows


def _empty_policy_outcome_row(
    symbol: str,
    date: object,
    policy: TargetStopPolicyCandidate,
    *,
    entry_price: float,
    target_price: float,
    stop_price: float,
    labels: dict[str, str],
) -> dict[str, object]:
    row: dict[str, object] = {
        "schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
        "target_stop_policy_id": policy.policy_id,
        "target_stop_policy_name": policy.policy_name,
        "target_stop_policy_status": policy.governance_status,
        "target_stop_policy_hash": policy.policy_hash,
        "archetype": policy.archetype,
        "action": policy.action,
        "scope": policy.product_scope,
        "horizon": policy.horizon,
        "Date": pd.Timestamp(str(date)).date().isoformat(),
        "symbol": symbol,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_price": stop_price,
        "target_before_stop": math.nan,
        "stop_before_target": math.nan,
        "unresolved": math.nan,
        "forward_return": math.nan,
        "MFE": math.nan,
        "MAE": math.nan,
        "time_to_target": math.nan,
        "time_to_stop": math.nan,
        "time_to_max_favorable_excursion": math.nan,
        "time_to_max_adverse_excursion": math.nan,
        "profitable_at_time_exit": math.nan,
        "profitable_at_horizon_despite_failing_tbs": math.nan,
    }
    for label_column in labels.values():
        row[label_column] = math.nan
    return row


def _scope_for_role(role: object) -> ProductClassScope:
    try:
        return product_class_scope_for_role(role)
    except ValueError:
        return "POOLED"


def _finite_or_nan(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return math.nan
    return numeric if math.isfinite(numeric) else math.nan


def _ratio_return(numerator: object, denominator: object) -> float:
    top = _finite_or_nan(numerator)
    bottom = _finite_or_nan(denominator)
    if not math.isfinite(top) or not math.isfinite(bottom) or bottom == 0.0:
        return math.nan
    return (top / bottom) - 1.0


def _safe_max(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.max()) if not numeric.empty else math.nan


def _safe_min(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.min()) if not numeric.empty else math.nan


def _excursion_time(series: pd.Series, *, want_max: bool) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return math.nan
    position = (
        int(np.argmax(numeric.to_numpy())) if want_max else int(np.argmin(numeric.to_numpy()))
    )
    return float(position + 1)


def _label_source_key(label_key: str) -> str:
    return {
        "target_before_stop": "target_before_stop",
        "stop_before_target": "stop_before_target",
        "unresolved": "unresolved",
        "time_to_target": "time_to_target",
        "time_to_stop": "time_to_stop",
        "time_to_max_favorable_excursion": "time_to_max_favorable_excursion",
        "time_to_max_adverse_excursion": "time_to_max_adverse_excursion",
        "profitable_at_time_exit": "profitable_at_time_exit",
        "profitable_at_horizon_despite_failing_tbs": ("profitable_at_horizon_despite_failing_tbs"),
    }[label_key]


def _stable_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
