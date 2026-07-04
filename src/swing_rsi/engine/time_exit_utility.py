from __future__ import annotations

import math
from typing import Any

import pandas as pd

from swing_rsi.engine.product_scope import PRODUCT_CLASS_SCOPE_ORDINARY
from swing_rsi.engine.splits import chronological_train_calibration_holdout_split
from swing_rsi.engine.target_stop_policy import (
    SECTOR_ROTATION_BUY_ORDINARY_BASELINE_POLICY_ID,
    TargetStopPolicyCandidate,
    build_policy_outcomes,
    candidate_policy_outcome_labels,
)

TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION = "sector_rotation_buy_ordinary_time_exit_utility_v1"
TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE = (
    "Time-exit utility is diagnostic. It does not override gates or create a live signal."
)
SECTOR_ROTATION_BUY_ORDINARY_TIME_EXIT_HYPOTHESIS_ID = (
    "sector_rotation_buy_ordinary_20d_time_exit_utility_v1"
)
TIME_EXIT_BASELINE_POLICY_ALIAS = "default_t2p0_s1p0_20d"
TIME_EXIT_UTILITY_EPSILON = 1e-6
TIME_EXIT_HORIZON = 20

TIME_EXIT_UTILITY_LABEL_COLUMNS = [
    "schema_version",
    "target_stop_policy_id",
    "target_stop_policy_alias",
    "target_stop_policy_name",
    "target_stop_policy_status",
    "target_stop_policy_hash",
    "archetype",
    "action",
    "scope",
    "horizon",
    "Date",
    "symbol",
    "sector",
    "regime",
    "entry_price",
    "exit_price",
    "target_price",
    "stop_price",
    "atr_pct_at_signal",
    "stop_distance_pct",
    "target_before_stop",
    "stop_before_target",
    "unresolved",
    "time_exit_gross_return_20d",
    "time_exit_net_return_20d",
    "time_exit_positive_after_cost_20d",
    "time_exit_utility_20d",
    "profitable_despite_failed_tbs_20d",
    "early_adverse_recovery_20d",
    "early_adverse_recovery_rule",
    "time_exit_quality_bucket_20d",
    "MFE_20d",
    "MAE_20d",
    "time_to_target",
    "time_to_stop",
    "time_to_max_favorable_excursion_20d",
    "time_to_max_adverse_excursion_20d",
    "round_trip_cost_return",
    "label_end_date_20",
]

TIME_EXIT_UTILITY_CALIBRATION_SUMMARY_COLUMNS = [
    "schema_version",
    "evidence_split",
    "development_holdout_diagnostic_only",
    "target_stop_policy_id",
    "target_stop_policy_alias",
    "target_stop_policy_status",
    "archetype",
    "action",
    "scope",
    "horizon",
    "sample_count",
    "start_date",
    "end_date",
    "time_exit_positive_rate",
    "average_time_exit_net_return",
    "median_time_exit_net_return",
    "average_time_exit_utility",
    "median_time_exit_utility",
    "profitable_despite_failed_tbs_rate",
    "early_adverse_recovery_rate",
    "average_mfe",
    "average_mae",
    "worst_mae",
    "average_time_to_max_favorable_excursion",
    "average_time_to_max_adverse_excursion",
    "symbol_concentration",
    "year_concentration",
    "regime_concentration",
    "diagnostic_only_notice",
]


def time_exit_utility_outcome_labels(
    policy: TargetStopPolicyCandidate,
) -> dict[str, str]:
    prefix = f"label_{_label_safe_policy_id(policy.policy_id)}"
    policy_labels = candidate_policy_outcome_labels(policy)
    return {
        "directional_return": f"{prefix}_time_exit_net_return_20d",
        "positive_return": f"{prefix}_time_exit_positive_after_cost_20d",
        "time_exit_net_return": f"{prefix}_time_exit_net_return_20d",
        "time_exit_positive_after_cost": f"{prefix}_time_exit_positive_after_cost_20d",
        "time_exit_utility": f"{prefix}_time_exit_utility_20d",
        "profitable_despite_failed_tbs": f"{prefix}_profitable_despite_failed_tbs_20d",
        "early_adverse_recovery": f"{prefix}_early_adverse_recovery_20d",
        "mfe": f"{prefix}_mfe_20d",
        "mae": f"{prefix}_mae_20d",
        "target_before_stop": policy_labels["target_before_stop"],
        "time_to_target": policy_labels["time_to_target"],
        "time_to_stop": policy_labels["time_to_stop"],
        "time_to_max_favorable_excursion": (policy_labels["time_to_max_favorable_excursion"]),
        "time_to_max_adverse_excursion": policy_labels["time_to_max_adverse_excursion"],
        "label_end_date": "label_end_date_20",
    }


def augment_model_frame_with_time_exit_utility_labels(
    model_frame: pd.DataFrame,
    policies: tuple[TargetStopPolicyCandidate, ...],
    *,
    cost_return: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = build_time_exit_utility_labels(model_frame, policies, cost_return=cost_return)
    if labels.empty:
        return model_frame.copy(), labels
    label_columns = [
        column
        for column in labels.columns
        if column in {"Date", "symbol"}
        or (str(column).startswith("label_") and column not in model_frame.columns)
    ]
    wide_labels = (
        labels[label_columns]
        .copy()
        .assign(Date=lambda frame: pd.to_datetime(frame["Date"], errors="coerce"))
        .groupby(["Date", "symbol"], as_index=False, sort=True)
        .first()
    )
    augmented = model_frame.copy()
    augmented["Date"] = pd.to_datetime(augmented["Date"], errors="coerce")
    augmented = augmented.merge(
        wide_labels,
        on=["Date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    return augmented, labels


def build_time_exit_utility_labels(
    model_frame: pd.DataFrame,
    policies: tuple[TargetStopPolicyCandidate, ...],
    *,
    cost_return: float,
) -> pd.DataFrame:
    relevant_policies = _time_exit_policies(policies)
    if model_frame.empty or not relevant_policies:
        return pd.DataFrame(columns=_time_exit_columns(relevant_policies))
    outcomes = build_policy_outcomes(
        model_frame,
        relevant_policies,
        include_statuses=("DEFAULT_BASELINE", "EXPERIMENTAL_CANDIDATE"),
    )
    if outcomes.empty:
        return pd.DataFrame(columns=_time_exit_columns(relevant_policies))
    enriched = _attach_signal_metadata(outcomes, model_frame)
    rows: list[dict[str, object]] = []
    policy_by_id = {policy.policy_id: policy for policy in relevant_policies}
    for _, row in enriched.iterrows():
        policy_id = str(row.get("target_stop_policy_id") or "")
        policy = policy_by_id.get(policy_id)
        if policy is None:
            continue
        rows.append(_time_exit_label_row(row, policy, cost_return=cost_return))
    return pd.DataFrame(rows, columns=_time_exit_columns(relevant_policies))


def time_exit_utility_calibration_summary_frame(labels: pd.DataFrame) -> pd.DataFrame:
    if labels.empty:
        return pd.DataFrame(columns=TIME_EXIT_UTILITY_CALIBRATION_SUMMARY_COLUMNS)
    rows: list[dict[str, object]] = []
    grouped = labels.dropna(subset=["Date", "symbol", "label_end_date_20"]).copy()
    for _policy_id, group in grouped.groupby("target_stop_policy_id", sort=True):
        usable = group.dropna(
            subset=[
                "time_exit_net_return_20d",
                "time_exit_positive_after_cost_20d",
                "time_exit_utility_20d",
            ]
        ).copy()
        if usable.empty:
            continue
        try:
            split = chronological_train_calibration_holdout_split(
                usable,
                horizon=TIME_EXIT_HORIZON,
                validation_fraction=0.2,
                holdout_fraction=0.2,
            )
        except ValueError:
            continue
        rows.append(
            _summary_row(
                split.calibration,
                evidence_split="calibration_only",
                development_holdout_diagnostic_only=False,
            )
        )
        rows.append(
            _summary_row(
                split.holdout,
                evidence_split="DEVELOPMENT_HOLDOUT_DIAGNOSTIC_ONLY",
                development_holdout_diagnostic_only=True,
            )
        )
    return pd.DataFrame(rows, columns=TIME_EXIT_UTILITY_CALIBRATION_SUMMARY_COLUMNS)


def time_exit_utility_policy_comparison_frame(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=TIME_EXIT_UTILITY_CALIBRATION_SUMMARY_COLUMNS)
    return summary.copy()


def time_exit_utility_signal_rows_frame(candidates: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "signal_id",
        "generation_id",
        "as_of_date",
        "ticker",
        "hypothesis_id",
        "target_stop_policy_id",
        "target_stop_policy_status",
        "decision",
        "candidate_status",
        "signal_score",
        "target_before_stop_probability",
        "time_exit_positive_probability",
        "expected_time_exit_return",
        "expected_time_exit_utility",
        "profitable_despite_failed_tbs_probability",
        "early_adverse_recovery_probability",
        "no_signal_reason",
        "rejection_reason",
        "not_live_actionable_reason",
    ]
    if candidates.empty or "time_exit_label_schema_version" not in candidates.columns:
        return pd.DataFrame(columns=columns)
    frame = candidates.loc[
        candidates["time_exit_label_schema_version"]
        .astype(str)
        .eq(TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION)
    ].copy()
    if frame.empty:
        return pd.DataFrame(columns=columns)
    return frame[[column for column in columns if column in frame.columns]].copy()


def time_exit_quality_bucket(net_return: float) -> str:
    if not math.isfinite(net_return):
        return ""
    if net_return >= 0.02:
        return "STRONG_POSITIVE_TIME_EXIT"
    if net_return > 0.0:
        return "MODEST_POSITIVE_TIME_EXIT"
    if net_return >= -0.002:
        return "FLAT_TIME_EXIT"
    if net_return <= -0.05:
        return "SEVERE_NEGATIVE_TIME_EXIT"
    return "NEGATIVE_TIME_EXIT"


def _time_exit_policies(
    policies: tuple[TargetStopPolicyCandidate, ...],
) -> tuple[TargetStopPolicyCandidate, ...]:
    return tuple(
        policy
        for policy in policies
        if policy.archetype == "sector_rotation_buy"
        and policy.action == "BUY"
        and policy.product_scope == PRODUCT_CLASS_SCOPE_ORDINARY
        and policy.horizon == TIME_EXIT_HORIZON
        and policy.governance_status in {"DEFAULT_BASELINE", "EXPERIMENTAL_CANDIDATE"}
    )


def _time_exit_columns(policies: tuple[TargetStopPolicyCandidate, ...]) -> list[str]:
    columns = list(TIME_EXIT_UTILITY_LABEL_COLUMNS)
    for policy in policies:
        for label_column in time_exit_utility_outcome_labels(policy).values():
            if label_column not in columns:
                columns.append(label_column)
    return columns


def _attach_signal_metadata(outcomes: pd.DataFrame, model_frame: pd.DataFrame) -> pd.DataFrame:
    metadata_columns = [
        column
        for column in (
            "Date",
            "symbol",
            "atr_pct_14",
            "sector",
            "sector_name",
            "market_regime_label",
            "market_regime_cluster_expanding",
            "label_end_date_20",
        )
        if column in model_frame.columns
    ]
    metadata = model_frame[metadata_columns].copy()
    metadata["Date"] = pd.to_datetime(metadata["Date"], errors="coerce")
    metadata = metadata.drop_duplicates(["Date", "symbol"], keep="last")
    enriched = outcomes.copy()
    enriched["Date"] = pd.to_datetime(enriched["Date"], errors="coerce")
    return enriched.merge(metadata, on=["Date", "symbol"], how="left", validate="many_to_one")


def _time_exit_label_row(
    row: pd.Series,
    policy: TargetStopPolicyCandidate,
    *,
    cost_return: float,
) -> dict[str, object]:
    gross_return = _as_float(row.get("forward_return"), default=math.nan)
    net_return = gross_return - cost_return if math.isfinite(gross_return) else math.nan
    mae = _as_float(row.get("MAE"), default=math.nan)
    mfe = _as_float(row.get("MFE"), default=math.nan)
    atr_pct = _atr_pct(row, policy)
    stop_distance = _stop_distance_pct(row)
    denominator = max(
        abs(mae) if math.isfinite(mae) else 0.0,
        atr_pct if math.isfinite(atr_pct) else 0.0,
        TIME_EXIT_UTILITY_EPSILON,
    )
    utility = net_return / denominator if math.isfinite(net_return) else math.nan
    target_before_stop = _as_bool(row.get("target_before_stop"))
    positive = math.isfinite(net_return) and net_return > 0.0
    stop_breached = (
        math.isfinite(mae)
        and math.isfinite(stop_distance)
        and stop_distance > 0.0
        and mae <= -stop_distance
    )
    profitable_failed_tbs = (not target_before_stop) and positive
    early_adverse_recovery = stop_breached and positive
    exit_price = _exit_price(row, gross_return)
    labels = time_exit_utility_outcome_labels(policy)
    record: dict[str, object] = {
        "schema_version": TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION,
        "target_stop_policy_id": policy.policy_id,
        "target_stop_policy_alias": _policy_alias(policy),
        "target_stop_policy_name": policy.policy_name,
        "target_stop_policy_status": policy.governance_status,
        "target_stop_policy_hash": policy.policy_hash,
        "archetype": policy.archetype,
        "action": policy.action,
        "scope": policy.product_scope,
        "horizon": policy.horizon,
        "Date": pd.Timestamp(str(row.get("Date"))).date().isoformat(),
        "symbol": str(row.get("symbol") or ""),
        "sector": str(row.get("sector", row.get("sector_name", "")) or ""),
        "regime": str(
            row.get("market_regime_label", row.get("market_regime_cluster_expanding", "")) or ""
        ),
        "entry_price": _as_float(row.get("entry_price"), default=math.nan),
        "exit_price": exit_price,
        "target_price": _as_float(row.get("target_price"), default=math.nan),
        "stop_price": _as_float(row.get("stop_price"), default=math.nan),
        "atr_pct_at_signal": atr_pct,
        "stop_distance_pct": stop_distance,
        "target_before_stop": float(target_before_stop),
        "stop_before_target": _as_float(row.get("stop_before_target"), default=math.nan),
        "unresolved": _as_float(row.get("unresolved"), default=math.nan),
        "time_exit_gross_return_20d": gross_return,
        "time_exit_net_return_20d": net_return,
        "time_exit_positive_after_cost_20d": float(positive),
        "time_exit_utility_20d": utility,
        "profitable_despite_failed_tbs_20d": float(profitable_failed_tbs),
        "early_adverse_recovery_20d": float(early_adverse_recovery),
        "early_adverse_recovery_rule": (
            "MAE_20d <= -abs(entry_price - stop_price) / entry_price "
            "and time_exit_net_return_20d > 0"
        ),
        "time_exit_quality_bucket_20d": time_exit_quality_bucket(net_return),
        "MFE_20d": mfe,
        "MAE_20d": mae,
        "time_to_target": _as_float(row.get("time_to_target"), default=math.nan),
        "time_to_stop": _as_float(row.get("time_to_stop"), default=math.nan),
        "time_to_max_favorable_excursion_20d": _as_float(
            row.get("time_to_max_favorable_excursion"),
            default=math.nan,
        ),
        "time_to_max_adverse_excursion_20d": _as_float(
            row.get("time_to_max_adverse_excursion"),
            default=math.nan,
        ),
        "round_trip_cost_return": cost_return,
        "label_end_date_20": row.get("label_end_date_20", ""),
    }
    record[labels["directional_return"]] = net_return
    record[labels["positive_return"]] = float(positive)
    record[labels["time_exit_utility"]] = utility
    record[labels["profitable_despite_failed_tbs"]] = float(profitable_failed_tbs)
    record[labels["early_adverse_recovery"]] = float(early_adverse_recovery)
    record[labels["mfe"]] = mfe
    record[labels["mae"]] = mae
    for label_key in (
        "target_before_stop",
        "time_to_target",
        "time_to_stop",
        "time_to_max_favorable_excursion",
        "time_to_max_adverse_excursion",
    ):
        record[labels[label_key]] = record[_record_key_for_label(label_key)]
    return record


def _summary_row(
    frame: pd.DataFrame,
    *,
    evidence_split: str,
    development_holdout_diagnostic_only: bool,
) -> dict[str, object]:
    first = frame.iloc[0]
    net = pd.to_numeric(frame["time_exit_net_return_20d"], errors="coerce")
    utility = pd.to_numeric(frame["time_exit_utility_20d"], errors="coerce")
    return {
        "schema_version": TIME_EXIT_UTILITY_LABEL_SCHEMA_VERSION,
        "evidence_split": evidence_split,
        "development_holdout_diagnostic_only": development_holdout_diagnostic_only,
        "target_stop_policy_id": str(first.get("target_stop_policy_id") or ""),
        "target_stop_policy_alias": str(first.get("target_stop_policy_alias") or ""),
        "target_stop_policy_status": str(first.get("target_stop_policy_status") or ""),
        "archetype": str(first.get("archetype") or ""),
        "action": str(first.get("action") or ""),
        "scope": str(first.get("scope") or ""),
        "horizon": int(_as_float(first.get("horizon"), default=TIME_EXIT_HORIZON)),
        "sample_count": len(frame),
        "start_date": _date_min(frame.get("Date", pd.Series(dtype=str))),
        "end_date": _date_max(frame.get("Date", pd.Series(dtype=str))),
        "time_exit_positive_rate": _safe_mean(frame["time_exit_positive_after_cost_20d"]),
        "average_time_exit_net_return": _safe_mean(net),
        "median_time_exit_net_return": _safe_median(net),
        "average_time_exit_utility": _safe_mean(utility),
        "median_time_exit_utility": _safe_median(utility),
        "profitable_despite_failed_tbs_rate": _safe_mean(
            frame["profitable_despite_failed_tbs_20d"]
        ),
        "early_adverse_recovery_rate": _safe_mean(frame["early_adverse_recovery_20d"]),
        "average_mfe": _safe_mean(frame["MFE_20d"]),
        "average_mae": _safe_mean(frame["MAE_20d"]),
        "worst_mae": _safe_min(frame["MAE_20d"]),
        "average_time_to_max_favorable_excursion": _safe_mean(
            frame["time_to_max_favorable_excursion_20d"]
        ),
        "average_time_to_max_adverse_excursion": _safe_mean(
            frame["time_to_max_adverse_excursion_20d"]
        ),
        "symbol_concentration": _value_concentration(frame.get("symbol", pd.Series(dtype=str))),
        "year_concentration": _year_concentration(frame.get("Date", pd.Series(dtype=str))),
        "regime_concentration": _value_concentration(frame.get("regime", pd.Series(dtype=str))),
        "diagnostic_only_notice": TIME_EXIT_UTILITY_DIAGNOSTIC_NOTICE,
    }


def _record_key_for_label(label_key: str) -> str:
    return {
        "target_before_stop": "target_before_stop",
        "time_to_target": "time_to_target",
        "time_to_stop": "time_to_stop",
        "time_to_max_favorable_excursion": "time_to_max_favorable_excursion_20d",
        "time_to_max_adverse_excursion": "time_to_max_adverse_excursion_20d",
    }[label_key]


def _policy_alias(policy: TargetStopPolicyCandidate) -> str:
    if policy.policy_id == SECTOR_ROTATION_BUY_ORDINARY_BASELINE_POLICY_ID:
        return TIME_EXIT_BASELINE_POLICY_ALIAS
    return policy.policy_id


def _label_safe_policy_id(policy_id: str) -> str:
    return policy_id.replace("-", "_")


def _atr_pct(row: pd.Series, policy: TargetStopPolicyCandidate) -> float:
    atr_pct = _as_float(row.get("atr_pct_14"), default=math.nan)
    if math.isfinite(atr_pct) and atr_pct > 0.0:
        return atr_pct
    entry = _as_float(row.get("entry_price"), default=math.nan)
    target = _as_float(row.get("target_price"), default=math.nan)
    if (
        math.isfinite(entry)
        and entry != 0.0
        and math.isfinite(target)
        and policy.target_multiple > 0.0
    ):
        return abs(target - entry) / entry / float(policy.target_multiple)
    return math.nan


def _stop_distance_pct(row: pd.Series) -> float:
    entry = _as_float(row.get("entry_price"), default=math.nan)
    stop = _as_float(row.get("stop_price"), default=math.nan)
    if not math.isfinite(entry) or entry == 0.0 or not math.isfinite(stop):
        return math.nan
    return abs(entry - stop) / entry


def _exit_price(row: pd.Series, gross_return: float) -> float:
    entry = _as_float(row.get("entry_price"), default=math.nan)
    if not math.isfinite(entry) or not math.isfinite(gross_return):
        return math.nan
    return entry * (1.0 + gross_return)


def _as_float(value: Any, *, default: float = math.nan) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def _as_bool(value: Any) -> bool:
    return _as_float(value, default=0.0) >= 0.5


def _safe_mean(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.mean()) if not numeric.empty else math.nan


def _safe_median(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.median()) if not numeric.empty else math.nan


def _safe_min(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.min()) if not numeric.empty else math.nan


def _value_concentration(values: pd.Series) -> float:
    series = values.dropna().astype(str)
    series = series.loc[series.str.len() > 0]
    if series.empty:
        return math.nan
    counts = series.value_counts()
    return float(counts.iloc[0] / counts.sum())


def _year_concentration(values: pd.Series) -> float:
    dates = pd.to_datetime(values, errors="coerce").dropna()
    if dates.empty:
        return math.nan
    counts = dates.dt.year.value_counts()
    return float(counts.iloc[0] / counts.sum())


def _date_min(values: pd.Series) -> str:
    dates = pd.to_datetime(values, errors="coerce").dropna()
    return dates.min().date().isoformat() if not dates.empty else ""


def _date_max(values: pd.Series) -> str:
    dates = pd.to_datetime(values, errors="coerce").dropna()
    return dates.max().date().isoformat() if not dates.empty else ""
