from __future__ import annotations

import hashlib
import json
import math
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)

from swing_rsi.config import ProjectPaths
from swing_rsi.engine.feature_screen import (
    FeatureScreenResult,
    screen_features_for_target,
)
from swing_rsi.engine.features import (
    feature_family_map_for_columns,
    numeric_feature_columns,
    reject_label_columns,
)
from swing_rsi.engine.gates import configuration_hash
from swing_rsi.engine.manifest import current_commit_hash, hash_file
from swing_rsi.engine.product_scope import (
    PRODUCT_CLASS_SCOPE_POOLED,
    PRODUCT_CLASS_SCOPES,
    ProductClassScope,
    build_product_class_scope_definitions,
    filter_frame_for_product_class_scope,
    normalize_product_class_scope,
    product_class_scope_for_role,
)
from swing_rsi.engine.splits import chronological_train_calibration_holdout_split
from swing_rsi.engine.target_stop_policy import (
    SECTOR_ROTATION_BUY_ORDINARY_CANDIDATE_HYPOTHESIS_ID,
    TARGET_STOP_POLICY_DIAGNOSTIC_NOTICE,
    TARGET_STOP_POLICY_SCHEMA_VERSION,
    TargetStopPolicyCandidate,
    augment_model_frame_with_policy_outcomes,
    calibration_selection_frame,
    candidate_policy_outcome_labels,
    policy_registry_frame,
    sector_rotation_buy_ordinary_baseline_policy,
    sector_rotation_buy_ordinary_policy_comparison_frame,
    select_sector_rotation_buy_ordinary_policy_candidate,
    target_stop_policy_registry,
)
from swing_rsi.engine.universe import load_universe_config

SIGNAL_DISCOVERY_SCHEMA_VERSION = "multi_angle_signal_discovery_v1"
SIGNAL_DISCOVERY_GENERATION_TYPE = "signal_discovery_generation"
SIGNAL_DISCOVERY_BLOCKER_REPORT_SCHEMA_VERSION = "signal_discovery_blocker_report_v1"
HISTORICAL_ANALOG_ROBUSTNESS_SCHEMA_VERSION = "historical_analog_robustness_v1"
MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION = "multi_angle_calibration_audit_v1"
SIGNAL_DISCOVERY_DIR = "signal_discovery"
DEFAULT_SIGNAL_DISCOVERY_CONFIG = Path("configs/signal_discovery/v1.yaml")
DEFAULT_BLOCKED_ROW_ANALOG_COUNT = 10
ANALOG_ROBUSTNESS_DEPTHS = (10, 25, 50)
CALIBRATION_DIAGNOSTIC_THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60)
TARGET_STOP_POLICY_AUDIT_COLUMNS = [
    "target_stop_policy_id",
    "target_stop_policy_name",
    "target_stop_policy_status",
    "target_stop_policy_hash",
]

SignalDirection = Literal["BUY", "SELL_SHORT"]
SignalAction = Literal["BUY", "SELL", "NO SIGNAL"]

MODEL_FAMILIES = ("hist_gradient_boosting", "extra_trees")
NAIVE_FAMILY = "naive_control"
DEFAULT_HORIZONS = (3, 5, 10, 20)
ALL_FEATURE_FAMILIES = (
    "returns_momentum",
    "trend_structure",
    "volatility_range",
    "volume_participation",
    "candle_geometry",
    "rsi_family",
    "technical_primitives",
    "market_relative",
    "sector_relative",
    "inverse_leveraged",
    "breadth",
    "relationship_graph",
    "regime",
)

BLOCKED_ROW_ANALOG_COLUMNS = [
    "target_row_id",
    "target_signal_id",
    "generation_id",
    "target_as_of_date",
    "target_ticker",
    "target_direction",
    "target_archetype",
    "target_action",
    "target_status",
    "target_score",
    "target_blocker_reason",
    "target_hypothesis_id",
    "target_model_id",
    "target_product_scope",
    "target_selection_reason",
    "analog_rank",
    "analog_date",
    "analog_ticker",
    "analog_scope",
    "analog_direction",
    "analog_archetype",
    "analog_pool",
    "similarity_score",
    "distance_score",
    "same_symbol",
    "same_product_scope",
    "same_archetype",
    "same_direction",
    "market_regime",
    "forward_return",
    "MFE",
    "MAE",
    "target_before_stop_result",
    "analog_would_have_passed_current_thresholds",
    "analog_rejection_reason",
    "outcome_labels_used_for_explanation_only",
]

BLOCKED_ROW_ANALOG_SUMMARY_COLUMNS = [
    "target_row_id",
    "target_signal_id",
    "generation_id",
    "target_as_of_date",
    "target_ticker",
    "target_direction",
    "target_archetype",
    "target_action",
    "target_status",
    "target_score",
    "target_blocker_reason",
    "target_hypothesis_id",
    "target_model_id",
    "target_product_scope",
    "target_selection_reason",
    "analog_count",
    "requested_analog_count",
    "same_scope_analog_count",
    "same_archetype_analog_count",
    "average_forward_return",
    "median_forward_return",
    "win_rate",
    "target_before_stop_hit_rate",
    "average_MFE",
    "average_MAE",
    "worst_MAE",
    "best_MFE",
    "analog_support_label",
    "key_caution",
    "positive_forward_outcomes",
    "analog_count_note",
    "analog_footprint_summary",
]

ANALOG_DEPTH_COMPARISON_COLUMNS = [
    "schema_version",
    "target_row_id",
    "target_signal_id",
    "generation_id",
    "target_as_of_date",
    "target_ticker",
    "target_direction",
    "target_archetype",
    "target_action",
    "target_status",
    "target_score",
    "target_blocker_reason",
    "target_hypothesis_id",
    "target_model_id",
    "target_product_scope",
    "requested_depth",
    "analog_count",
    "depth_support_label",
    "same_symbol_count",
    "same_symbol_share",
    "same_scope_count",
    "same_scope_share",
    "same_archetype_count",
    "same_archetype_share",
    "same_year_max_count",
    "same_year_max_share",
    "same_regime_max_count",
    "same_regime_max_share",
    "average_forward_return",
    "median_forward_return",
    "win_rate",
    "target_before_stop_hit_rate",
    "average_MFE",
    "average_MAE",
    "worst_MAE",
    "best_MFE",
    "return_standard_deviation",
    "analog_dispersion_score",
    "average_similarity",
    "minimum_similarity",
    "maximum_distance",
    "coverage_note",
]

ANALOG_ROBUSTNESS_COLUMNS = [
    "schema_version",
    "target_row_id",
    "target_signal_id",
    "generation_id",
    "target_as_of_date",
    "target_ticker",
    "target_direction",
    "target_archetype",
    "target_action",
    "target_status",
    "target_score",
    "target_blocker_reason",
    "target_hypothesis_id",
    "target_model_id",
    "target_product_scope",
    "original_analog_support_label",
    "robust_analog_support_label",
    "analog_compact_status",
    "top_10_summary_json",
    "top_25_summary_json",
    "top_50_summary_json",
    "caution_flags",
    "robustness_explanation",
    "analog_evidence_usable_for_research",
    "analog_evidence_too_concentrated",
    "analog_evidence_contradicts_signal_score",
]

ANALOG_CAUTION_FLAG_COLUMNS = [
    "schema_version",
    "target_row_id",
    "target_signal_id",
    "generation_id",
    "target_ticker",
    "target_hypothesis_id",
    "caution_flag",
    "evidence",
]

ANALOG_ROBUSTNESS_SUMMARY_COLUMNS = [
    "schema_version",
    "generation_id",
    "target_rows",
    "robust_support_count",
    "supportive_but_concentrated_count",
    "mixed_support_count",
    "weak_support_count",
    "insufficient_analogs_count",
    "concentration_artifact_count",
    "decays_with_depth_count",
]

CALIBRATION_AUDIT_FRAME_NAMES = (
    "calibration_summary",
    "probability_distributions",
    "probability_buckets",
    "diagnostic_thresholds",
    "row_level_calibration_audit",
)

CALIBRATION_SUMMARY_COLUMNS = [
    "schema_version",
    "generation_id",
    "hypothesis_id",
    "archetype_id",
    "archetype",
    "action",
    "direction",
    "horizon",
    "product_scope",
    "model_family",
    "model_id",
    *TARGET_STOP_POLICY_AUDIT_COLUMNS,
    "status",
    "reason",
    "calibration_start_date",
    "calibration_end_date",
    "calibration_row_count",
    "positive_tbs_count",
    "negative_tbs_count",
    "tbs_base_rate",
    "target_hit_probability",
    "stop_hit_probability",
    "unresolved_probability",
    "average_forward_return",
    "average_mfe",
    "average_mae",
    "naive_base_rate_brier",
    "model_brier",
    "brier_skill",
    "roc_auc",
    "pr_auc",
    "ece",
    "calibration_slope",
    "calibration_intercept",
    "raw_versus_calibrated_rank_correlation",
    "unique_calibrated_probability_count",
    "largest_calibrated_plateau_percentage",
    "realized_tbs_rate_by_decile_json",
    "selected_calibrator",
    "calibration_method",
    "selected_feature_manifest_hash",
    "calibration_diagnostic_threshold_table_hash",
    "row_level_calibration_audit_hash",
    "artifact_hash",
]

PROBABILITY_DISTRIBUTION_COLUMNS = [
    "schema_version",
    "generation_id",
    "hypothesis_id",
    "archetype_id",
    "archetype",
    "action",
    "direction",
    "horizon",
    "product_scope",
    "model_family",
    "model_id",
    *TARGET_STOP_POLICY_AUDIT_COLUMNS,
    "probability_type",
    "min",
    "p01",
    "p05",
    "p10",
    "p25",
    "median",
    "p75",
    "p90",
    "p95",
    "p99",
    "max",
    "mean",
    "standard_deviation",
    "count_ge_030",
    "count_ge_035",
    "count_ge_040",
    "count_ge_045",
    "count_ge_050",
    "count_ge_055",
    "count_ge_060",
]

PROBABILITY_BUCKET_COLUMNS = [
    "schema_version",
    "generation_id",
    "hypothesis_id",
    "archetype_id",
    "archetype",
    "action",
    "direction",
    "horizon",
    "product_scope",
    "model_family",
    "model_id",
    *TARGET_STOP_POLICY_AUDIT_COLUMNS,
    "bucket_id",
    "bucket_lower_bound",
    "bucket_upper_bound",
    "row_count",
    "average_raw_probability",
    "average_calibrated_probability",
    "observed_tbs_hit_rate",
    "average_forward_return",
    "average_mfe",
    "average_mae",
    "target_hit_probability",
    "stop_hit_probability",
    "unresolved_probability",
    "average_time_to_target",
    "average_time_to_stop",
    "transaction_cost_adjusted_utility",
]

DIAGNOSTIC_THRESHOLD_COLUMNS = [
    "schema_version",
    "generation_id",
    "hypothesis_id",
    "archetype_id",
    "archetype",
    "action",
    "direction",
    "horizon",
    "product_scope",
    "model_family",
    "model_id",
    *TARGET_STOP_POLICY_AUDIT_COLUMNS,
    "threshold",
    "qualifying_row_count",
    "qualifying_row_rate",
    "observed_tbs_hit_rate",
    "precision",
    "recall",
    "average_forward_return",
    "median_forward_return",
    "average_mfe",
    "average_mae",
    "worst_mae",
    "target_hit_probability",
    "stop_hit_probability",
    "unresolved_probability",
    "transaction_cost_adjusted_utility",
    "symbol_concentration",
    "year_concentration",
    "regime_concentration",
    "diagnostic_only",
    "production_target_before_stop_threshold",
]

ROW_LEVEL_CALIBRATION_AUDIT_COLUMNS = [
    "schema_version",
    "generation_id",
    "hypothesis_id",
    "Date",
    "symbol",
    "product_scope",
    "archetype",
    "archetype_id",
    "action",
    "direction",
    "horizon",
    "model_family",
    "model_id",
    *TARGET_STOP_POLICY_AUDIT_COLUMNS,
    "raw_probability",
    "calibrated_probability",
    "TBS_label",
    "forward_return",
    "MFE",
    "MAE",
    "target_hit",
    "stop_hit",
    "unresolved",
    "time_to_target",
    "time_to_stop",
    "regime",
    "sector",
    "selected_feature_manifest_hash",
    "calibration_artifact_hash",
]


@dataclass(frozen=True)
class SignalArchetypeSpec:
    archetype_id: str
    name: str
    bullish_lens: str
    bearish_lens: str
    footprint_categories: tuple[str, ...]

    def to_jsonable(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SignalHypothesisSpec:
    hypothesis_id: str
    archetype_id: str
    direction: SignalDirection
    horizon: int
    eligible_product_scopes: tuple[ProductClassScope, ...]
    required_feature_families: tuple[str, ...]
    candidate_feature_families: tuple[str, ...]
    outcome_labels: dict[str, str]
    model_tasks: tuple[str, ...]
    selection_policy: dict[str, object]
    validation_policy: dict[str, object]
    footprint_categories: tuple[str, ...]
    explanation_template: str
    governance_version: str = SIGNAL_DISCOVERY_SCHEMA_VERSION
    target_stop_policy_id: str = ""
    target_stop_policy_name: str = ""
    target_stop_policy_status: str = ""
    target_stop_policy_hash: str = ""
    target_stop_policy_schema_version: str = ""
    target_stop_policy_notice: str = ""
    target_stop_policy_target_multiple: float | None = None
    target_stop_policy_stop_multiple: float | None = None

    @property
    def label_direction(self) -> str:
        return "bull" if self.direction == "BUY" else "bear"

    @property
    def action_label(self) -> SignalAction:
        return "BUY" if self.direction == "BUY" else "SELL"

    def to_jsonable(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SignalDiscoveryConfig:
    schema_version: str
    enabled_hypotheses: tuple[str, ...]
    horizons: tuple[int, ...]
    product_scopes: tuple[ProductClassScope, ...]
    model_families: tuple[str, ...]
    minimum_training_samples: int
    minimum_calibration_samples: int
    minimum_holdout_samples: int
    max_selected_features: int
    analog_count: int
    candidate_cap_per_hypothesis: int
    round_trip_cost_bps: float
    probability_threshold: float
    target_before_stop_threshold: float
    expected_return_threshold: float
    signal_score_threshold: float
    ood_feature_rate_limit: float
    random_seed: int
    research_start: str | None
    research_end: str | None
    ood_policy_reference: str
    selection_policy_reference: str

    @property
    def cost_return(self) -> float:
        return self.round_trip_cost_bps / 10_000.0

    @property
    def configuration_hash(self) -> str:
        return configuration_hash(asdict(self))


@dataclass(frozen=True)
class FittedSignalModel:
    family: str
    hypothesis: SignalHypothesisSpec
    selected_features: tuple[str, ...]
    feature_screen: FeatureScreenResult
    imputer: SimpleImputer
    train_q01: dict[str, float]
    train_q99: dict[str, float]
    primary_classifier: Any
    primary_calibrator: Any
    tbs_classifier: Any
    tbs_calibrator: Any
    return_regressor: Any
    mfe_regressor: Any
    mae_regressor: Any
    train_frame: pd.DataFrame
    holdout_metrics: dict[str, object]
    calibration_audit: dict[str, pd.DataFrame]


@dataclass(frozen=True)
class SignalDiscoveryRun:
    generation_id: str
    generation_dir: Path
    metadata: dict[str, object]
    hypotheses: pd.DataFrame
    candidates: pd.DataFrame
    selected_candidates: pd.DataFrame
    no_signal: pd.DataFrame
    rejected: pd.DataFrame
    footprint_evidence: pd.DataFrame
    analogs: pd.DataFrame
    score_components: pd.DataFrame
    gate_results: pd.DataFrame


def default_archetype_registry() -> dict[str, SignalArchetypeSpec]:
    return {
        "trend_continuation": SignalArchetypeSpec(
            "trend_continuation",
            "Trend Continuation",
            "Strong relative return, trend persistence, supportive market/sector context.",
            "Persistent weakness, failed recoveries, market/sector pressure.",
            ("returns_momentum", "trend_structure", "market_relative", "sector_relative"),
        ),
        "reversal_exhaustion": SignalArchetypeSpec(
            "reversal_exhaustion",
            "Reversal / Exhaustion",
            "Selloff exhaustion, stabilization, recovery from low range, divergence.",
            "Upside exhaustion, failed breakout, rejection near highs, deteriorating support.",
            ("trend_structure", "volatility_range", "candle_geometry", "market_relative"),
        ),
        "breakout_breakdown": SignalArchetypeSpec(
            "breakout_breakdown",
            "Breakout / Breakdown",
            "Breakout above rolling range with volume/range expansion and regime support.",
            "Breakdown below rolling range with market, sector, or inverse confirmation.",
            ("trend_structure", "volume_participation", "volatility_range", "regime"),
        ),
        "pullback_continuation": SignalArchetypeSpec(
            "pullback_continuation",
            "Pullback Continuation",
            "Strong trend, controlled pullback, compression, and recovery signal.",
            "Weak trend, controlled bounce into resistance, continuation lower.",
            ("trend_structure", "returns_momentum", "volatility_range", "candle_geometry"),
        ),
        "risk_on_risk_off": SignalArchetypeSpec(
            "risk_on_risk_off",
            "Risk-On / Risk-Off",
            "Broad-market strength, sector participation, inverse ETFs weak, breadth improving.",
            "Inverse ETFs strengthening, leveraged longs weakening, breadth deteriorating.",
            ("breadth", "inverse_leveraged", "market_relative", "relationship_graph"),
        ),
        "sector_rotation": SignalArchetypeSpec(
            "sector_rotation",
            "Sector Rotation",
            "Instrument outperforming sector and market with improving sector leadership.",
            "Instrument underperforming sector and market during rotation away.",
            ("sector_relative", "market_relative", "returns_momentum", "breadth"),
        ),
        "volatility_expansion": SignalArchetypeSpec(
            "volatility_expansion",
            "Volatility Expansion",
            "ATR/range expansion with directional follow-through and regime support.",
            "ATR/range expansion with downside follow-through and regime support.",
            ("volatility_range", "trend_structure", "regime", "volume_participation"),
        ),
        "volatility_compression_release": SignalArchetypeSpec(
            "volatility_compression_release",
            "Volatility Compression Release",
            "Compression followed by directional expansion and analog support.",
            "Compression followed by downside expansion and analog support.",
            ("volatility_range", "trend_structure", "candle_geometry", "regime"),
        ),
        "breadth_thrust_deterioration": SignalArchetypeSpec(
            "breadth_thrust_deterioration",
            "Breadth Thrust / Breadth Deterioration",
            "Broad participation expansion.",
            "Participation deterioration, concentration risk, and risk-off breadth.",
            ("breadth", "market_relative", "sector_relative", "inverse_leveraged"),
        ),
        "failed_move_liquidity_trap": SignalArchetypeSpec(
            "failed_move_liquidity_trap",
            "Failed Move / Liquidity Trap Proxy",
            "Failed breakdown, reclaim behavior, and reversal from prior low.",
            "Failed breakout, rejection behavior, and reversal from prior high.",
            ("trend_structure", "candle_geometry", "volatility_range", "volume_participation"),
        ),
    }


def _outcome_labels(direction: SignalDirection, horizon: int) -> dict[str, str]:
    prefix = "bull" if direction == "BUY" else "bear"
    return {
        "directional_return": f"label_{prefix}_forward_return_{horizon}",
        "positive_return": f"label_{prefix}_positive_return_{horizon}",
        "mfe": f"label_{prefix}_mfe_{horizon}",
        "mae": f"label_{prefix}_mae_{horizon}",
        "target_before_stop": f"label_{prefix}_target_before_stop_{horizon}",
        "time_to_target": f"label_{prefix}_time_to_target_{horizon}",
        "time_to_stop": f"label_{prefix}_time_to_stop_{horizon}",
        "label_end_date": f"label_end_date_{horizon}",
    }


def _hypothesis(
    hypothesis_id: str,
    archetype_id: str,
    direction: SignalDirection,
    horizon: int,
    scopes: tuple[ProductClassScope, ...],
    required: tuple[str, ...],
    explanation: str,
    *,
    outcome_labels: dict[str, str] | None = None,
    target_stop_policy: TargetStopPolicyCandidate | None = None,
) -> SignalHypothesisSpec:
    labels = outcome_labels or _outcome_labels(direction, horizon)
    return SignalHypothesisSpec(
        hypothesis_id=hypothesis_id,
        archetype_id=archetype_id,
        direction=direction,
        horizon=horizon,
        eligible_product_scopes=scopes,
        required_feature_families=required,
        candidate_feature_families=ALL_FEATURE_FAMILIES,
        outcome_labels=labels,
        model_tasks=(
            "direction_probability",
            "target_before_stop_probability",
            "expected_return",
            "expected_mfe",
            "expected_mae",
        ),
        selection_policy={
            "probability_threshold": 0.55,
            "target_before_stop_threshold": 0.50,
            "expected_return_threshold": 0.001,
            "live_action_requires_promoted_model": True,
        },
        validation_policy={
            "split": "chronological_train_calibration_holdout",
            "feature_screen_split": "training_only",
            "calibration_split": "calibration_only",
            "holdout_usage": "evaluation_only",
        },
        footprint_categories=required,
        explanation_template=explanation,
        target_stop_policy_id=target_stop_policy.policy_id if target_stop_policy else "",
        target_stop_policy_name=target_stop_policy.policy_name if target_stop_policy else "",
        target_stop_policy_status=(
            target_stop_policy.governance_status if target_stop_policy else ""
        ),
        target_stop_policy_hash=target_stop_policy.policy_hash if target_stop_policy else "",
        target_stop_policy_schema_version=TARGET_STOP_POLICY_SCHEMA_VERSION
        if target_stop_policy
        else "",
        target_stop_policy_notice=TARGET_STOP_POLICY_DIAGNOSTIC_NOTICE
        if target_stop_policy
        else "",
        target_stop_policy_target_multiple=(
            target_stop_policy.target_multiple if target_stop_policy else None
        ),
        target_stop_policy_stop_multiple=(
            target_stop_policy.stop_multiple if target_stop_policy else None
        ),
    )


def _policy_context_fields(spec: SignalHypothesisSpec) -> dict[str, object]:
    return {
        "target_stop_policy_id": spec.target_stop_policy_id,
        "target_stop_policy_name": spec.target_stop_policy_name,
        "target_stop_policy_status": spec.target_stop_policy_status,
        "target_stop_policy_hash": spec.target_stop_policy_hash,
    }


def _target_stop_policy_display(spec: SignalHypothesisSpec) -> str:
    if not spec.target_stop_policy_id:
        return ""
    target = spec.target_stop_policy_target_multiple
    stop = spec.target_stop_policy_stop_multiple
    target_text = f"{target:g}" if target is not None else "?"
    stop_text = f"{stop:g}" if stop is not None else "?"
    name = spec.target_stop_policy_name or spec.target_stop_policy_id
    return f"{name} · T{target_text}/S{stop_text}/{spec.horizon}D"


def _sector_rotation_candidate_outcome_labels(
    policy: TargetStopPolicyCandidate,
) -> dict[str, str]:
    labels = _outcome_labels("BUY", policy.horizon)
    candidate_labels = candidate_policy_outcome_labels(policy)
    labels["target_before_stop"] = candidate_labels["target_before_stop"]
    labels["time_to_target"] = candidate_labels["time_to_target"]
    labels["time_to_stop"] = candidate_labels["time_to_stop"]
    return labels


def default_hypothesis_registry() -> dict[str, SignalHypothesisSpec]:
    ordinary_scopes: tuple[ProductClassScope, ...] = (
        PRODUCT_CLASS_SCOPE_POOLED,
        "ORDINARY",
        "LEVERAGED_LONG",
    )
    inverse_scopes: tuple[ProductClassScope, ...] = (
        "INVERSE",
        "LEVERAGED_INVERSE",
    )
    baseline_policy = sector_rotation_buy_ordinary_baseline_policy()
    policy_selection = select_sector_rotation_buy_ordinary_policy_candidate()
    specs = [
        _hypothesis(
            "trend_continuation_buy_10d",
            "trend_continuation",
            "BUY",
            10,
            ordinary_scopes,
            ("returns_momentum", "trend_structure", "market_relative"),
            "Trend continuation buy lens with market/sector confirmation.",
        ),
        _hypothesis(
            "trend_continuation_sell_10d",
            "trend_continuation",
            "SELL_SHORT",
            10,
            ordinary_scopes,
            ("returns_momentum", "trend_structure", "market_relative"),
            "Trend continuation sell/short lens with market pressure.",
        ),
        _hypothesis(
            "reversal_buy_5d",
            "reversal_exhaustion",
            "BUY",
            5,
            ordinary_scopes,
            ("trend_structure", "volatility_range", "candle_geometry"),
            "Bullish exhaustion/reclaim lens after selloff pressure.",
        ),
        _hypothesis(
            "reversal_sell_5d",
            "reversal_exhaustion",
            "SELL_SHORT",
            5,
            ordinary_scopes,
            ("trend_structure", "volatility_range", "candle_geometry"),
            "Bearish exhaustion/rejection lens after upside pressure.",
        ),
        _hypothesis(
            "breakout_buy_10d",
            "breakout_breakdown",
            "BUY",
            10,
            ordinary_scopes,
            ("trend_structure", "volume_participation", "volatility_range"),
            "Breakout buy lens using range/volume expansion.",
        ),
        _hypothesis(
            "breakdown_sell_10d",
            "breakout_breakdown",
            "SELL_SHORT",
            10,
            ordinary_scopes,
            ("trend_structure", "volume_participation", "volatility_range"),
            "Breakdown sell/short lens using range/volume expansion.",
        ),
        _hypothesis(
            "pullback_continuation_buy_10d",
            "pullback_continuation",
            "BUY",
            10,
            ordinary_scopes,
            ("trend_structure", "returns_momentum", "volatility_range"),
            "Controlled pullback buy lens inside a stronger trend.",
        ),
        _hypothesis(
            "pullback_continuation_sell_10d",
            "pullback_continuation",
            "SELL_SHORT",
            10,
            ordinary_scopes,
            ("trend_structure", "returns_momentum", "volatility_range"),
            "Controlled bounce sell/short lens inside a weaker trend.",
        ),
        _hypothesis(
            "risk_off_buy_inverse_10d",
            "risk_on_risk_off",
            "BUY",
            10,
            inverse_scopes,
            ("inverse_leveraged", "breadth", "market_relative", "relationship_graph"),
            "Risk-off inverse ETF buy lens.",
        ),
        _hypothesis(
            "sector_rotation_buy_20d",
            "sector_rotation",
            "BUY",
            20,
            ordinary_scopes,
            ("sector_relative", "market_relative", "returns_momentum"),
            "Sector leadership and relative strength buy lens.",
            target_stop_policy=baseline_policy,
        ),
        _hypothesis(
            "volatility_expansion_sell_5d",
            "volatility_expansion",
            "SELL_SHORT",
            5,
            ordinary_scopes,
            ("volatility_range", "trend_structure", "regime"),
            "Downside volatility expansion sell/short lens.",
        ),
        _hypothesis(
            "volatility_compression_release_buy_10d",
            "volatility_compression_release",
            "BUY",
            10,
            ordinary_scopes,
            ("volatility_range", "trend_structure", "candle_geometry"),
            "Bullish compression release lens.",
        ),
        _hypothesis(
            "breadth_deterioration_sell_10d",
            "breadth_thrust_deterioration",
            "SELL_SHORT",
            10,
            ordinary_scopes,
            ("breadth", "market_relative", "inverse_leveraged"),
            "Breadth deterioration sell/short lens.",
        ),
        _hypothesis(
            "failed_breakdown_buy_5d",
            "failed_move_liquidity_trap",
            "BUY",
            5,
            ordinary_scopes,
            ("trend_structure", "candle_geometry", "volatility_range"),
            "Failed breakdown and reclaim buy lens.",
        ),
        _hypothesis(
            "failed_breakout_sell_5d",
            "failed_move_liquidity_trap",
            "SELL_SHORT",
            5,
            ordinary_scopes,
            ("trend_structure", "candle_geometry", "volatility_range"),
            "Failed breakout and rejection sell/short lens.",
        ),
    ]
    if policy_selection.selected_policy is not None:
        candidate_policy = policy_selection.selected_policy
        specs.append(
            _hypothesis(
                SECTOR_ROTATION_BUY_ORDINARY_CANDIDATE_HYPOTHESIS_ID,
                "sector_rotation",
                "BUY",
                candidate_policy.horizon,
                ("ORDINARY",),
                ("sector_relative", "market_relative", "returns_momentum"),
                "Experimental Sector Rotation BUY ORDINARY target/stop policy candidate.",
                outcome_labels=_sector_rotation_candidate_outcome_labels(candidate_policy),
                target_stop_policy=candidate_policy,
            )
        )
    return {spec.hypothesis_id: spec for spec in specs}


def load_signal_discovery_config(path: str | Path | None = None) -> SignalDiscoveryConfig:
    config_path = Path(path or DEFAULT_SIGNAL_DISCOVERY_CONFIG)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected signal discovery YAML mapping in {config_path}")
    if str(payload.get("schema_version")) != SIGNAL_DISCOVERY_SCHEMA_VERSION:
        raise ValueError("Unsupported signal discovery config schema")
    model_families = tuple(str(item) for item in payload.get("model_families", MODEL_FAMILIES))
    unsupported = sorted(set(model_families) - set(MODEL_FAMILIES))
    if unsupported:
        raise ValueError("Unsupported signal discovery model families: " + ", ".join(unsupported))
    return SignalDiscoveryConfig(
        schema_version=SIGNAL_DISCOVERY_SCHEMA_VERSION,
        enabled_hypotheses=tuple(str(item) for item in payload.get("enabled_hypotheses", ())),
        horizons=tuple(int(item) for item in payload.get("horizons", DEFAULT_HORIZONS)),
        product_scopes=tuple(
            normalize_product_class_scope(item)
            for item in payload.get("product_scopes", PRODUCT_CLASS_SCOPES)
        ),
        model_families=model_families,
        minimum_training_samples=int(payload.get("minimum_training_samples", 200)),
        minimum_calibration_samples=int(payload.get("minimum_calibration_samples", 80)),
        minimum_holdout_samples=int(payload.get("minimum_holdout_samples", 80)),
        max_selected_features=int(payload.get("max_selected_features", 48)),
        analog_count=int(payload.get("analog_count", 5)),
        candidate_cap_per_hypothesis=int(payload.get("candidate_cap_per_hypothesis", 12)),
        round_trip_cost_bps=float(payload.get("costs", {}).get("round_trip_bps", 5.0)),
        probability_threshold=float(payload.get("selection_policy", {}).get("probability", 0.55)),
        target_before_stop_threshold=float(
            payload.get("selection_policy", {}).get("target_before_stop", 0.50)
        ),
        expected_return_threshold=float(
            payload.get("selection_policy", {}).get("expected_return", 0.001)
        ),
        signal_score_threshold=float(payload.get("selection_policy", {}).get("signal_score", 0.55)),
        ood_feature_rate_limit=float(payload.get("ood_policy", {}).get("feature_rate_limit", 0.20)),
        random_seed=int(payload.get("random_seed", 42)),
        research_start=payload.get("research_start", "2016-06-20"),
        research_end=payload.get("research_end"),
        ood_policy_reference=str(
            payload.get("ood_policy", {}).get("reference", "prediction_ood_governance_v2")
        ),
        selection_policy_reference=str(
            payload.get("selection_policy", {}).get("reference", "signal_discovery_policy_v1")
        ),
    )


def latest_signal_discovery_generation_dir(root: str | Path) -> Path | None:
    base = ProjectPaths(Path(root)).artifacts / SIGNAL_DISCOVERY_DIR
    if not base.exists():
        return None
    candidates = sorted(
        (path for path in base.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def load_signal_discovery_frames(
    root: str | Path, generation: str = "latest"
) -> dict[str, pd.DataFrame]:
    generation_dir = _resolve_generation_dir(root, generation)
    if generation_dir is None:
        return {}
    frames: dict[str, pd.DataFrame] = {}
    for name in (
        "hypotheses",
        "candidates",
        "selected_candidates",
        "no_signal",
        "rejected",
        "footprint_evidence",
        "historical_analogs",
        "blocked_row_analogs",
        "blocked_row_analog_summary",
        "score_components",
        "gate_results",
        "calibration_summary",
        "probability_distributions",
        "probability_buckets",
        "diagnostic_thresholds",
        "row_level_calibration_audit",
        "target_stop_policy_registry",
        "calibration_selection",
        "sector_rotation_buy_ordinary_policy_comparison",
        "derived_policy_outcomes",
        "signal_discovery_policy_comparison",
        "summary",
    ):
        path = generation_dir / f"{name}.csv"
        if not path.exists():
            frames[name] = pd.DataFrame()
            continue
        try:
            frames[name] = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            frames[name] = pd.DataFrame()
    metadata_path = generation_dir / "metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        frames["metadata"] = pd.DataFrame(
            [{"field": key, "value": value} for key, value in sorted(metadata.items())]
        )
    manifest_path = generation_dir / "calibration_artifact_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest.get("files", []) if isinstance(manifest, dict) else []
        frames["calibration_artifact_manifest"] = pd.DataFrame(
            files if isinstance(files, list) else []
        )
    else:
        frames["calibration_artifact_manifest"] = pd.DataFrame()
    return frames


def _resolve_generation_dir(root: str | Path, generation: str) -> Path | None:
    if generation == "latest":
        return latest_signal_discovery_generation_dir(root)
    base = ProjectPaths(Path(root)).artifacts / SIGNAL_DISCOVERY_DIR
    direct = base / generation
    if direct.exists() and direct.is_dir():
        return direct
    matches = sorted(path for path in base.glob(f"*{generation}*") if path.is_dir())
    return matches[-1] if matches else None


def run_signal_discovery(
    root: str | Path,
    *,
    config_path: str | Path | None = None,
    universe_path: str | Path | None = None,
) -> SignalDiscoveryRun:
    project_root = Path(root)
    paths = ProjectPaths(project_root)
    paths.ensure()
    config = load_signal_discovery_config(
        config_path or project_root / DEFAULT_SIGNAL_DISCOVERY_CONFIG
    )
    universe = load_universe_config(universe_path or project_root / "configs/universe/core.yaml")
    model_frame, modeling_path = _latest_modeling_frame(paths)
    feature_frame, feature_path = _latest_feature_frame(paths)
    policy_selection = select_sector_rotation_buy_ordinary_policy_candidate()
    policies = target_stop_policy_registry()
    model_frame, derived_policy_outcomes = augment_model_frame_with_policy_outcomes(
        model_frame,
        policies,
    )
    feature_manifest_hash = _feature_hash_from_path(feature_path)
    feature_family_by_column = feature_family_map_for_columns(
        numeric_feature_columns(feature_frame)
    )
    raw_manifest_hashes = tuple(hash_file(path) for path in sorted(paths.manifests.glob("*.json")))
    archetypes = default_archetype_registry()
    hypotheses = default_hypothesis_registry()
    enabled_ids = config.enabled_hypotheses or tuple(hypotheses)
    unknown_ids = sorted(set(enabled_ids) - set(hypotheses))
    if unknown_ids:
        raise ValueError("Unknown signal discovery hypotheses: " + ", ".join(unknown_ids))
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    generation_id = _generation_id(created_at, config.configuration_hash, feature_manifest_hash)
    generation_dir = paths.artifacts / SIGNAL_DISCOVERY_DIR / generation_id
    if generation_dir.exists():
        raise FileExistsError(f"Signal discovery generation already exists: {generation_dir}")
    temp_dir = generation_dir.with_name(f".{generation_dir.name}.tmp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    latest_date = pd.Timestamp(model_frame["Date"].max()).normalize()
    candidates: list[dict[str, object]] = []
    hypotheses_rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    analog_rows: list[dict[str, object]] = []
    component_rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    calibration_summary_rows: list[dict[str, object]] = []
    probability_distribution_rows: list[dict[str, object]] = []
    probability_bucket_rows: list[dict[str, object]] = []
    diagnostic_threshold_rows: list[dict[str, object]] = []
    row_level_calibration_frames: list[pd.DataFrame] = []

    scope_definitions = build_product_class_scope_definitions(
        universe, scopes=config.product_scopes
    )
    for hypothesis_id in enabled_ids:
        spec = hypotheses[hypothesis_id]
        if spec.horizon not in config.horizons:
            continue
        result = _evaluate_hypothesis(
            spec,
            archetypes[spec.archetype_id],
            model_frame=model_frame,
            latest_date=latest_date,
            feature_family_by_column=feature_family_by_column,
            scope_definitions=scope_definitions,
            config=config,
            generation_id=generation_id,
            feature_manifest_hash=feature_manifest_hash,
        )
        hypotheses_rows.extend(result["hypotheses"])
        candidates.extend(result["candidates"])
        evidence_rows.extend(result["evidence"])
        analog_rows.extend(result["analogs"])
        component_rows.extend(result["components"])
        gate_rows.extend(result["gates"])
        calibration_summary_rows.extend(result["calibration_summary"])
        probability_distribution_rows.extend(result["probability_distributions"])
        probability_bucket_rows.extend(result["probability_buckets"])
        diagnostic_threshold_rows.extend(result["diagnostic_thresholds"])
        row_level = pd.DataFrame(result["row_level_calibration_audit"])
        if not row_level.empty:
            row_level_calibration_frames.append(row_level)

    candidates_frame = pd.DataFrame(candidates)
    if not candidates_frame.empty:
        candidates_frame = _apply_candidate_caps(candidates_frame, config)
    selected = candidates_frame.loc[
        candidates_frame.get("candidate_status", pd.Series(dtype=str)).astype(str) == "SHADOW_ONLY"
    ].copy()
    no_signal = candidates_frame.loc[
        candidates_frame.get("decision", pd.Series(dtype=str)).astype(str) == "NO_SIGNAL"
    ].copy()
    rejected = candidates_frame.loc[
        candidates_frame.get("decision", pd.Series(dtype=str))
        .astype(str)
        .str.startswith("REJECTED")
    ].copy()
    summary = _summary_frame(
        generation_id=generation_id,
        created_at=created_at,
        candidates=candidates_frame,
        hypotheses=pd.DataFrame(hypotheses_rows),
    )
    metadata: dict[str, object] = {
        "schema_version": SIGNAL_DISCOVERY_SCHEMA_VERSION,
        "generation_type": SIGNAL_DISCOVERY_GENERATION_TYPE,
        "generation_id": generation_id,
        "created_at_utc": created_at,
        "code_commit": current_commit_hash(project_root) or "",
        "universe_snapshot_id": universe.snapshot_id,
        "feature_manifest_hash": feature_manifest_hash,
        "feature_path": str(feature_path.relative_to(project_root)),
        "modeling_path": str(modeling_path.relative_to(project_root)),
        "raw_manifest_hashes": list(raw_manifest_hashes),
        "config_hash": config.configuration_hash,
        "hypotheses_evaluated": len(set(pd.DataFrame(hypotheses_rows).get("hypothesis_id", []))),
        "horizons": list(config.horizons),
        "model_families": list(config.model_families),
        "product_scopes": list(config.product_scopes),
        "latest_decision_date": latest_date.date().isoformat(),
        "no_signal_rows": len(no_signal),
        "selected_candidates": len(selected),
        "rejected_rows": len(rejected),
        "target_stop_policy_schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
        "target_stop_policy_candidate_status": policy_selection.status,
        "target_stop_policy_candidate_reason": policy_selection.reason,
        "target_stop_policy_candidate_id": policy_selection.selected_policy.policy_id
        if policy_selection.selected_policy is not None
        else "",
        "artifact_hashes": {},
    }

    frames = {
        "summary": summary,
        "hypotheses": pd.DataFrame(hypotheses_rows),
        "candidates": candidates_frame,
        "selected_candidates": selected,
        "no_signal": no_signal,
        "rejected": rejected,
        "footprint_evidence": pd.DataFrame(evidence_rows),
        "historical_analogs": pd.DataFrame(analog_rows),
        "score_components": pd.DataFrame(component_rows),
        "gate_results": pd.DataFrame(gate_rows),
        "calibration_summary": pd.DataFrame(
            calibration_summary_rows,
            columns=CALIBRATION_SUMMARY_COLUMNS,
        ),
        "probability_distributions": pd.DataFrame(
            probability_distribution_rows,
            columns=PROBABILITY_DISTRIBUTION_COLUMNS,
        ),
        "probability_buckets": pd.DataFrame(
            probability_bucket_rows,
            columns=PROBABILITY_BUCKET_COLUMNS,
        ),
        "diagnostic_thresholds": pd.DataFrame(
            diagnostic_threshold_rows,
            columns=DIAGNOSTIC_THRESHOLD_COLUMNS,
        ),
        "row_level_calibration_audit": pd.concat(
            row_level_calibration_frames,
            ignore_index=True,
            sort=False,
        )
        if row_level_calibration_frames
        else pd.DataFrame(columns=ROW_LEVEL_CALIBRATION_AUDIT_COLUMNS),
        "target_stop_policy_registry": policy_registry_frame(),
        "calibration_selection": calibration_selection_frame(),
        "sector_rotation_buy_ordinary_policy_comparison": (
            sector_rotation_buy_ordinary_policy_comparison_frame()
        ),
        "derived_policy_outcomes": derived_policy_outcomes,
    }
    frames["signal_discovery_policy_comparison"] = _signal_discovery_policy_comparison_frame(
        candidates_frame
    )
    _write_generation(temp_dir, metadata, frames)
    metadata["artifact_hashes"] = {
        path.name: hash_file(path)
        for path in sorted(temp_dir.glob("*"))
        if path.is_file() and path.name != "metadata.json"
    }
    (temp_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    temp_dir.replace(generation_dir)
    _write_latest_pointer(paths.artifacts / SIGNAL_DISCOVERY_DIR, generation_id)
    _write_report(paths.reports, metadata, summary)
    return SignalDiscoveryRun(
        generation_id=generation_id,
        generation_dir=generation_dir,
        metadata=metadata,
        hypotheses=frames["hypotheses"],
        candidates=frames["candidates"],
        selected_candidates=frames["selected_candidates"],
        no_signal=frames["no_signal"],
        rejected=frames["rejected"],
        footprint_evidence=frames["footprint_evidence"],
        analogs=frames["historical_analogs"],
        score_components=frames["score_components"],
        gate_results=frames["gate_results"],
    )


def export_signal_discovery_generation(
    root: str | Path,
    *,
    generation: str = "latest",
    output: str | Path,
) -> tuple[Path, ...]:
    generation_dir = _resolve_generation_dir(root, generation)
    if generation_dir is None:
        raise FileNotFoundError("No signal discovery generation is available to export")
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for source in sorted(generation_dir.glob("*.csv")):
        target = output_dir / source.name
        shutil.copyfile(source, target)
        written.append(target)
    for name in (
        "row_level_calibration_audit.parquet",
        "calibration_summary.json",
        "calibration_artifact_manifest.json",
        "target_stop_policy_registry.json",
    ):
        source = generation_dir / name
        if source.exists():
            target = output_dir / source.name
            shutil.copyfile(source, target)
            written.append(target)
    blocked_frames = signal_discovery_blocked_analog_frames(root, generation=generation)
    for name in ("blocked_row_analogs", "blocked_row_analog_summary"):
        target = output_dir / f"{name}.csv"
        blocked_frames.get(name, pd.DataFrame()).to_csv(target, index=False)
        written.append(target)
    robustness_frames = signal_discovery_analog_robustness_frames(root, generation=generation)
    for name in (
        "analog_robustness",
        "analog_robustness_summary",
        "analog_depth_comparison",
        "analog_caution_flags",
    ):
        target = output_dir / f"{name}.csv"
        robustness_frames.get(name, pd.DataFrame()).to_csv(target, index=False)
        written.append(target)
    metadata_source = generation_dir / "metadata.json"
    if metadata_source.exists():
        target = output_dir / metadata_source.name
        shutil.copyfile(metadata_source, target)
        written.append(target)
    return tuple(written)


def signal_discovery_blocked_analog_frames(
    root: str | Path,
    *,
    generation: str = "latest",
    analog_count: int = DEFAULT_BLOCKED_ROW_ANALOG_COUNT,
) -> dict[str, pd.DataFrame]:
    frames = load_signal_discovery_frames(root, generation=generation)
    if not frames:
        return _empty_blocked_analog_frames()
    candidates = frames.get("candidates", pd.DataFrame())
    hypotheses = frames.get("hypotheses", pd.DataFrame())
    if candidates.empty or hypotheses.empty:
        return _empty_blocked_analog_frames()
    try:
        modeling, _ = _latest_modeling_frame(ProjectPaths(Path(root)))
    except FileNotFoundError:
        return _empty_blocked_analog_frames()

    target_rows = _blocked_analog_target_rows(candidates)
    analog_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for _, target in target_rows.iterrows():
        target_analogs = _blocked_analogs_for_target(
            target,
            hypotheses,
            modeling,
            analog_count=analog_count,
        )
        analog_rows.extend(target_analogs)
        summary_rows.append(
            _blocked_analog_summary_for_target(
                target,
                target_analogs,
                requested_analog_count=analog_count,
            )
        )
    return {
        "blocked_row_analogs": pd.DataFrame(
            analog_rows,
            columns=BLOCKED_ROW_ANALOG_COLUMNS,
        ),
        "blocked_row_analog_summary": pd.DataFrame(
            summary_rows,
            columns=BLOCKED_ROW_ANALOG_SUMMARY_COLUMNS,
        ),
    }


def signal_discovery_analog_robustness_frames(
    root: str | Path,
    *,
    generation: str = "latest",
) -> dict[str, pd.DataFrame]:
    frames = signal_discovery_blocked_analog_frames(
        root,
        generation=generation,
        analog_count=max(ANALOG_ROBUSTNESS_DEPTHS),
    )
    return historical_analog_robustness_frames_from_analogs(
        frames.get("blocked_row_analogs", pd.DataFrame())
    )


def historical_analog_robustness_frames_from_analogs(
    analogs: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    if analogs.empty or "target_signal_id" not in analogs.columns:
        return _empty_analog_robustness_frames()

    robustness_rows: list[dict[str, object]] = []
    depth_rows: list[dict[str, object]] = []
    flag_rows: list[dict[str, object]] = []
    for _, group in analogs.groupby(analogs["target_signal_id"].astype(str), sort=False):
        ordered = group.sort_values("analog_rank", kind="mergesort").copy()
        target = _analog_target_payload(ordered.iloc[0])
        summaries = {
            depth: _analog_depth_summary(target, ordered.head(depth), requested_depth=depth)
            for depth in ANALOG_ROBUSTNESS_DEPTHS
        }
        depth_rows.extend(summaries.values())
        flags = _analog_robustness_flags(target, summaries, ordered)
        label = _robust_analog_support_label(summaries, flags)
        flag_rows.extend(
            {
                "schema_version": HISTORICAL_ANALOG_ROBUSTNESS_SCHEMA_VERSION,
                "target_row_id": target["target_row_id"],
                "target_signal_id": target["target_signal_id"],
                "generation_id": target["generation_id"],
                "target_ticker": target["target_ticker"],
                "target_hypothesis_id": target["target_hypothesis_id"],
                "caution_flag": flag,
                "evidence": evidence,
            }
            for flag, evidence in flags.items()
        )
        robustness_rows.append(
            _analog_robustness_row(
                target=target,
                summaries=summaries,
                flags=tuple(flags),
                robust_label=label,
            )
        )

    robustness = pd.DataFrame(robustness_rows, columns=ANALOG_ROBUSTNESS_COLUMNS)
    depth_comparison = pd.DataFrame(depth_rows, columns=ANALOG_DEPTH_COMPARISON_COLUMNS)
    caution_flags = pd.DataFrame(flag_rows, columns=ANALOG_CAUTION_FLAG_COLUMNS)
    summary = _analog_robustness_summary(robustness)
    return {
        "analog_robustness": robustness,
        "analog_depth_comparison": depth_comparison,
        "analog_caution_flags": caution_flags,
        "analog_robustness_summary": summary,
    }


def write_signal_discovery_analog_robustness_report(
    root: str | Path,
    *,
    generation: str = "latest",
) -> tuple[Path, ...]:
    project_root = Path(root)
    frames = signal_discovery_analog_robustness_frames(project_root, generation=generation)
    output_dir = ProjectPaths(project_root).reports / "signal_discovery_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    csv_names = {
        "analog_robustness": "analog_robustness.csv",
        "analog_robustness_summary": "analog_robustness_summary.csv",
        "analog_depth_comparison": "analog_depth_comparison.csv",
        "analog_caution_flags": "analog_caution_flags.csv",
    }
    for name, filename in csv_names.items():
        path = output_dir / filename
        frames.get(name, pd.DataFrame()).to_csv(path, index=False)
        written.append(path)

    json_path = output_dir / "analog_robustness.json"
    json_payload = {
        "schema_version": HISTORICAL_ANALOG_ROBUSTNESS_SCHEMA_VERSION,
        "generation": generation,
        "frames": {name: frame.to_dict(orient="records") for name, frame in frames.items()},
    }
    json_path.write_text(
        json.dumps(json_payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    written.append(json_path)

    xlsx_path = output_dir / "analog_robustness.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for name, frame in frames.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)
    written.append(xlsx_path)
    return tuple(written)


def _empty_blocked_analog_frames() -> dict[str, pd.DataFrame]:
    return {
        "blocked_row_analogs": pd.DataFrame(columns=BLOCKED_ROW_ANALOG_COLUMNS),
        "blocked_row_analog_summary": pd.DataFrame(columns=BLOCKED_ROW_ANALOG_SUMMARY_COLUMNS),
    }


def _empty_analog_robustness_frames() -> dict[str, pd.DataFrame]:
    return {
        "analog_robustness": pd.DataFrame(columns=ANALOG_ROBUSTNESS_COLUMNS),
        "analog_depth_comparison": pd.DataFrame(columns=ANALOG_DEPTH_COMPARISON_COLUMNS),
        "analog_caution_flags": pd.DataFrame(columns=ANALOG_CAUTION_FLAG_COLUMNS),
        "analog_robustness_summary": pd.DataFrame(columns=ANALOG_ROBUSTNESS_SUMMARY_COLUMNS),
    }


def _analog_target_payload(row: pd.Series) -> dict[str, object]:
    return {
        "target_row_id": str(row.get("target_row_id") or row.get("target_signal_id") or ""),
        "target_signal_id": str(row.get("target_signal_id") or row.get("target_row_id") or ""),
        "generation_id": str(row.get("generation_id") or ""),
        "target_as_of_date": str(row.get("target_as_of_date") or ""),
        "target_ticker": str(row.get("target_ticker") or ""),
        "target_direction": str(row.get("target_direction") or ""),
        "target_archetype": str(row.get("target_archetype") or ""),
        "target_action": str(row.get("target_action") or ""),
        "target_status": str(row.get("target_status") or ""),
        "target_score": _as_float(row.get("target_score"), default=math.nan),
        "target_blocker_reason": str(row.get("target_blocker_reason") or ""),
        "target_hypothesis_id": str(row.get("target_hypothesis_id") or ""),
        "target_model_id": str(row.get("target_model_id") or ""),
        "target_product_scope": str(row.get("target_product_scope") or ""),
    }


def _share(count: int, total: int) -> float:
    return float(count / total) if total else math.nan


def _max_count_and_share(series: pd.Series, count: int) -> tuple[int, float]:
    values = series.dropna().astype(str)
    values = values.loc[values.str.len() > 0]
    if values.empty:
        return 0, math.nan
    max_count = int(values.value_counts().iloc[0])
    return max_count, _share(max_count, count)


def _analog_depth_summary(
    target: dict[str, object],
    analogs: pd.DataFrame,
    *,
    requested_depth: int,
) -> dict[str, object]:
    count = len(analogs)
    returns = pd.to_numeric(analogs.get("forward_return", pd.Series(dtype=float)), errors="coerce")
    mfes = pd.to_numeric(analogs.get("MFE", pd.Series(dtype=float)), errors="coerce")
    maes = pd.to_numeric(analogs.get("MAE", pd.Series(dtype=float)), errors="coerce")
    similarity = pd.to_numeric(
        analogs.get("similarity_score", pd.Series(dtype=float)), errors="coerce"
    )
    distance = pd.to_numeric(analogs.get("distance_score", pd.Series(dtype=float)), errors="coerce")
    tbs = (
        analogs.get("target_before_stop_result", pd.Series(dtype=str))
        .astype(str)
        .str.lower()
        .eq("target before stop")
    )
    years = pd.to_datetime(
        analogs.get("analog_date", pd.Series(dtype=str)), errors="coerce"
    ).dt.year
    same_symbol = int(analogs.get("same_symbol", pd.Series(dtype=bool)).eq(True).sum())
    same_scope = int(analogs.get("same_product_scope", pd.Series(dtype=bool)).eq(True).sum())
    same_archetype = int(analogs.get("same_archetype", pd.Series(dtype=bool)).eq(True).sum())
    same_year_count, same_year_share = _max_count_and_share(years, count)
    same_regime_count, same_regime_share = _max_count_and_share(
        analogs.get("market_regime", pd.Series(dtype=str)),
        count,
    )
    average_return = _safe_mean(returns)
    return_std = float(returns.dropna().std(ddof=0)) if not returns.dropna().empty else math.nan
    dispersion = (
        return_std / max(abs(average_return), 0.01)
        if math.isfinite(return_std) and math.isfinite(average_return)
        else math.nan
    )
    win_rate = _safe_mean((returns > 0.0).astype(float)) if count else math.nan
    tbs_hit_rate = _safe_mean(tbs.astype(float)) if count else math.nan
    depth_label = _analog_support_label(
        count=count,
        average_return=average_return,
        win_rate=win_rate,
        tbs_hit_rate=tbs_hit_rate,
    )
    return {
        "schema_version": HISTORICAL_ANALOG_ROBUSTNESS_SCHEMA_VERSION,
        **target,
        "requested_depth": requested_depth,
        "analog_count": count,
        "depth_support_label": depth_label,
        "same_symbol_count": same_symbol,
        "same_symbol_share": _share(same_symbol, count),
        "same_scope_count": same_scope,
        "same_scope_share": _share(same_scope, count),
        "same_archetype_count": same_archetype,
        "same_archetype_share": _share(same_archetype, count),
        "same_year_max_count": same_year_count,
        "same_year_max_share": same_year_share,
        "same_regime_max_count": same_regime_count,
        "same_regime_max_share": same_regime_share,
        "average_forward_return": average_return,
        "median_forward_return": _safe_median(returns),
        "win_rate": win_rate,
        "target_before_stop_hit_rate": tbs_hit_rate,
        "average_MFE": _safe_mean(mfes),
        "average_MAE": _safe_mean(maes),
        "worst_MAE": _safe_min(maes),
        "best_MFE": _safe_max(mfes),
        "return_standard_deviation": return_std,
        "analog_dispersion_score": dispersion,
        "average_similarity": _safe_mean(similarity),
        "minimum_similarity": _safe_min(similarity),
        "maximum_distance": _safe_max(distance),
        "coverage_note": _analog_count_note(count, requested_depth),
    }


def _summary_float(summary: dict[str, object], key: str) -> float:
    return _as_float(summary.get(key), default=math.nan)


def _max_finite(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return max(finite) if finite else math.nan


def _min_finite(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return min(finite) if finite else math.nan


def _depth_is_supportive(summary: dict[str, object]) -> bool:
    return str(summary.get("depth_support_label") or "") == "SUPPORTIVE"


def _depth_available(summary: dict[str, object]) -> bool:
    return int(_as_float(summary.get("analog_count"), default=0.0)) >= int(
        _as_float(summary.get("requested_depth"), default=0.0)
    )


def _analog_robustness_flags(
    target: dict[str, object],
    summaries: dict[int, dict[str, object]],
    analogs: pd.DataFrame,
) -> dict[str, str]:
    flags: dict[str, str] = {}
    max_same_symbol = _max_finite(
        [_summary_float(summary, "same_symbol_share") for summary in summaries.values()]
    )
    max_same_year = _max_finite(
        [_summary_float(summary, "same_year_max_share") for summary in summaries.values()]
    )
    max_same_regime = _max_finite(
        [_summary_float(summary, "same_regime_max_share") for summary in summaries.values()]
    )
    min_same_scope = _min_finite(
        [_summary_float(summary, "same_scope_share") for summary in summaries.values()]
    )
    max_return_std = _max_finite(
        [_summary_float(summary, "return_standard_deviation") for summary in summaries.values()]
    )
    max_dispersion = _max_finite(
        [_summary_float(summary, "analog_dispersion_score") for summary in summaries.values()]
    )
    worst_mae = _min_finite(
        [_summary_float(summary, "worst_MAE") for summary in summaries.values()]
    )
    top10 = summaries[10]
    if max_same_symbol >= 0.70:
        flags["same_symbol_concentration"] = (
            f"Maximum same-symbol share is {max_same_symbol:.2%} across robustness depths."
        )
    if max_same_year >= 0.70:
        flags["same_year_concentration"] = (
            f"Maximum same-year share is {max_same_year:.2%} across robustness depths."
        )
    if max_same_regime >= 0.80:
        flags["same_regime_concentration"] = (
            f"Maximum same-regime share is {max_same_regime:.2%} across robustness depths."
        )
    if math.isfinite(min_same_scope) and min_same_scope < 0.80:
        flags["same_scope_scarcity"] = (
            f"Minimum same-scope share is {min_same_scope:.2%}; cross-scope fallback affects analog support."
        )
    if any(not _depth_available(summary) for summary in summaries.values()):
        flags["low_analog_count"] = (
            "At least one requested robustness depth had fewer analogs than requested."
        )
    if (
        math.isfinite(max_return_std)
        and math.isfinite(max_dispersion)
        and (max_return_std >= 0.25 or max_dispersion >= 1.50)
    ):
        flags["high_return_dispersion"] = (
            f"Maximum return standard deviation is {max_return_std:.2%}; "
            f"maximum dispersion score is {max_dispersion:.2f}."
        )
    if math.isfinite(worst_mae) and worst_mae <= -0.20:
        flags["high_mae_tail_risk"] = f"Worst analog MAE is {worst_mae:.2%}."
    top10_tbs = _summary_float(top10, "target_before_stop_hit_rate")
    for depth in (25, 50):
        depth_tbs = _summary_float(summaries[depth], "target_before_stop_hit_rate")
        if math.isfinite(top10_tbs) and math.isfinite(depth_tbs) and top10_tbs - depth_tbs >= 0.15:
            flags["tbs_support_decay"] = (
                f"Target-before-stop hit rate decays from {top10_tbs:.2%} at top 10 "
                f"to {depth_tbs:.2%} at top {depth}."
            )
            break
    if _depth_is_supportive(top10) and not _depth_is_supportive(summaries[25]):
        flags["support_decays_top25"] = "Top-10 support does not remain SUPPORTIVE at top 25."
    if _depth_is_supportive(top10) and not _depth_is_supportive(summaries[50]):
        flags["support_decays_top50"] = "Top-10 support does not remain SUPPORTIVE at top 50."
    target_text = " ".join(
        str(target.get(key) or "") for key in ("target_status", "target_blocker_reason")
    ).lower()
    if "ood" in target_text:
        flags["ood_target_row"] = "Target row is rejected or blocked by OOD policy."
    top10_analogs = analogs.head(10).copy()
    if len(top10_analogs) >= 3:
        dates = pd.to_datetime(
            top10_analogs.get("analog_date", pd.Series(dtype=str)), errors="coerce"
        )
        valid_dates = dates.dropna()
        span = (valid_dates.max() - valid_dates.min()).days if len(valid_dates) >= 2 else 0
        if (
            _summary_float(top10, "same_symbol_share") >= 0.80
            and _summary_float(top10, "same_year_max_share") >= 0.80
            and span <= 45
        ):
            flags["analogs_mostly_same_event_cluster"] = (
                f"Top-10 analogs are mostly one ticker/year over a {span}-day window."
            )
    return flags


def _robust_analog_support_label(
    summaries: dict[int, dict[str, object]],
    flags: dict[str, str],
) -> str:
    top10 = summaries[10]
    if int(_as_float(top10.get("analog_count"), default=0.0)) < 10:
        return "INSUFFICIENT_ANALOGS"
    top10_supportive = _depth_is_supportive(top10)
    concentration_flags = {
        "same_symbol_concentration",
        "same_year_concentration",
        "same_regime_concentration",
        "analogs_mostly_same_event_cluster",
    }
    decay_flags = {"support_decays_top25", "support_decays_top50", "tbs_support_decay"}
    risk_flags = {"high_return_dispersion", "high_mae_tail_risk"}
    has_concentration = bool(concentration_flags.intersection(flags))
    has_decay = bool(decay_flags.intersection(flags))
    if top10_supportive and has_concentration and has_decay:
        return "CONCENTRATION_ARTIFACT"
    if top10_supportive and has_decay:
        return "DECAYS_WITH_DEPTH"
    support_survives = top10_supportive and all(
        _depth_is_supportive(summary) for summary in summaries.values() if _depth_available(summary)
    )
    if support_survives:
        if bool(risk_flags.intersection(flags)):
            return "MIXED_SUPPORT"
        if has_concentration:
            return "SUPPORTIVE_BUT_CONCENTRATED"
        return "ROBUST_SUPPORT"
    if str(top10.get("depth_support_label") or "") == "WEAK":
        return "WEAK_SUPPORT"
    return "MIXED_SUPPORT"


def _analog_compact_status(label: str) -> str:
    return {
        "ROBUST_SUPPORT": "Robust Analog Support",
        "SUPPORTIVE_BUT_CONCENTRATED": "Supportive But Concentrated",
        "MIXED_SUPPORT": "Mixed Analog Support",
        "WEAK_SUPPORT": "Weak Analog Support",
        "INSUFFICIENT_ANALOGS": "Insufficient Analogs",
        "CONCENTRATION_ARTIFACT": "Concentration Artifact",
        "DECAYS_WITH_DEPTH": "Decays With Depth",
    }.get(label, label.replace("_", " ").title())


def _analog_robustness_explanation(
    target: dict[str, object],
    summaries: dict[int, dict[str, object]],
    flags: tuple[str, ...],
    label: str,
) -> str:
    ticker = str(target.get("target_ticker") or "Target")
    top10 = summaries[10]
    top25 = summaries[25]
    top50 = summaries[50]
    if label == "CONCENTRATION_ARTIFACT":
        return (
            f"Top-10 analogs looked {str(top10.get('depth_support_label')).lower()}, but "
            f"{int(_as_float(top10.get('same_symbol_count'), default=0.0))}/"
            f"{int(_as_float(top10.get('analog_count'), default=0.0))} were {ticker} and "
            f"the same-year max share was {_summary_float(top10, 'same_year_max_share'):.2%}. "
            "Support degraded at expanded depths, so this is classified as a concentration "
            "artifact rather than robust evidence."
        )
    if label == "DECAYS_WITH_DEPTH":
        return (
            "Top-10 analogs were supportive, but support decayed at top-25 or top-50 without "
            "a dominant concentration flag. Analog evidence is explanatory and non-robust."
        )
    if label == "SUPPORTIVE_BUT_CONCENTRATED":
        return (
            "Analog support remains positive across available depths, but concentration flags "
            "remain active. Treat as research-only support, not independent confirmation."
        )
    if label == "ROBUST_SUPPORT":
        return (
            "Analog support remains supportive across available depths without excessive "
            "symbol/year/regime concentration, return dispersion, or MAE tail risk."
        )
    if label == "INSUFFICIENT_ANALOGS":
        return "Fewer than 10 valid pre-target analogs were available; robustness is insufficient."
    if label == "WEAK_SUPPORT":
        return "Analog outcomes are weak at the nearest depth and do not support the target row."
    if top10.get("depth_support_label") == "SUPPORTIVE":
        return (
            f"Top-10 analogs were supportive, but top-25 is {top25.get('depth_support_label')} "
            f"and top-50 is {top50.get('depth_support_label')}. Evidence remains mixed."
        )
    if flags:
        return "Analog evidence is mixed with caution flags: " + ", ".join(flags) + "."
    return "Analog evidence is mixed and remains explanatory only."


def _analog_robustness_row(
    *,
    target: dict[str, object],
    summaries: dict[int, dict[str, object]],
    flags: tuple[str, ...],
    robust_label: str,
) -> dict[str, object]:
    flag_text = ";".join(flags)
    original = str(summaries[10].get("depth_support_label") or "INSUFFICIENT_ANALOGS")
    concentration_flags = {
        "same_symbol_concentration",
        "same_year_concentration",
        "same_regime_concentration",
        "analogs_mostly_same_event_cluster",
    }
    too_concentrated = robust_label == "CONCENTRATION_ARTIFACT" or bool(
        concentration_flags.intersection(flags)
    )
    target_score = _as_float(target.get("target_score"), default=math.nan)
    contradicts_score = (
        math.isfinite(target_score)
        and target_score >= 0.55
        and robust_label in {"WEAK_SUPPORT", "INSUFFICIENT_ANALOGS"}
    )
    usable = robust_label not in {
        "CONCENTRATION_ARTIFACT",
        "INSUFFICIENT_ANALOGS",
        "WEAK_SUPPORT",
    }
    explanation = _analog_robustness_explanation(target, summaries, flags, robust_label)
    return {
        "schema_version": HISTORICAL_ANALOG_ROBUSTNESS_SCHEMA_VERSION,
        **target,
        "original_analog_support_label": original,
        "robust_analog_support_label": robust_label,
        "analog_compact_status": _analog_compact_status(robust_label),
        "top_10_summary_json": json.dumps(summaries[10], sort_keys=True, default=str),
        "top_25_summary_json": json.dumps(summaries[25], sort_keys=True, default=str),
        "top_50_summary_json": json.dumps(summaries[50], sort_keys=True, default=str),
        "caution_flags": flag_text,
        "robustness_explanation": explanation,
        "analog_evidence_usable_for_research": usable,
        "analog_evidence_too_concentrated": too_concentrated,
        "analog_evidence_contradicts_signal_score": contradicts_score,
    }


def _analog_robustness_summary(robustness: pd.DataFrame) -> pd.DataFrame:
    counts = (
        robustness.get("robust_analog_support_label", pd.Series(dtype=str))
        .astype(str)
        .value_counts()
        .to_dict()
    )
    generation_id = (
        str(robustness.iloc[0].get("generation_id"))
        if not robustness.empty and "generation_id" in robustness.columns
        else ""
    )
    return pd.DataFrame(
        [
            {
                "schema_version": HISTORICAL_ANALOG_ROBUSTNESS_SCHEMA_VERSION,
                "generation_id": generation_id,
                "target_rows": len(robustness),
                "robust_support_count": int(counts.get("ROBUST_SUPPORT", 0)),
                "supportive_but_concentrated_count": int(
                    counts.get("SUPPORTIVE_BUT_CONCENTRATED", 0)
                ),
                "mixed_support_count": int(counts.get("MIXED_SUPPORT", 0)),
                "weak_support_count": int(counts.get("WEAK_SUPPORT", 0)),
                "insufficient_analogs_count": int(counts.get("INSUFFICIENT_ANALOGS", 0)),
                "concentration_artifact_count": int(counts.get("CONCENTRATION_ARTIFACT", 0)),
                "decays_with_depth_count": int(counts.get("DECAYS_WITH_DEPTH", 0)),
            }
        ],
        columns=ANALOG_ROBUSTNESS_SUMMARY_COLUMNS,
    )


def _blocked_analog_target_rows(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=candidates.columns)
    frame = candidates.copy()
    frame["_decision"] = frame.get("decision", pd.Series(dtype=str)).astype(str)
    blocked = frame.loc[
        frame["_decision"].eq("NO_SIGNAL") | frame["_decision"].str.startswith("REJECTED")
    ].copy()
    if blocked.empty:
        return blocked.drop(columns=["_decision"], errors="ignore")
    blocked["_score_rank"] = pd.to_numeric(
        blocked.get("signal_score", pd.Series(dtype=float)), errors="coerce"
    ).fillna(-math.inf)
    blocked["_blocker_reason"] = [_target_blocker_reason(row) for _, row in blocked.iterrows()]
    selections: list[pd.DataFrame] = []
    direction_series = (
        blocked["direction"].astype(str)
        if "direction" in blocked.columns
        else pd.Series("", index=blocked.index, dtype=str)
    )
    for direction in ("Bullish", "Bearish"):
        direction_rows = blocked.loc[direction_series == direction]
        if not direction_rows.empty:
            selected = direction_rows.sort_values(
                ["_score_rank", "ticker", "hypothesis_id"],
                ascending=[False, True, True],
            ).head(5)
            selections.append(selected.assign(_target_selection_reason=f"top_{direction.lower()}"))
    for reason in (
        "probability_below_threshold",
        "target_before_stop_probability_below_threshold",
        "ood_feature_rate_above_limit",
    ):
        reason_rows = blocked.loc[blocked["_blocker_reason"].astype(str).eq(reason)]
        if not reason_rows.empty:
            selections.append(
                reason_rows.sort_values(
                    ["_score_rank", "ticker", "hypothesis_id"],
                    ascending=[False, True, True],
                )
                .head(3)
                .assign(_target_selection_reason=f"top_{reason}")
            )
    if not selections:
        return blocked.iloc[0:0].drop(columns=["_decision"], errors="ignore")
    selected = pd.concat(selections, ignore_index=False, sort=False)
    selected = (
        selected.sort_values(
            ["_score_rank", "ticker", "hypothesis_id"], ascending=[False, True, True]
        )
        .loc[lambda output: ~output.index.duplicated(keep="first")]
        .copy()
    )
    if "_target_selection_reason" not in selected.columns:
        selected["_target_selection_reason"] = "top_blocked_row"
    return selected.drop(columns=["_decision"], errors="ignore").reset_index(drop=True)


def _blocked_analogs_for_target(
    target: pd.Series,
    hypotheses: pd.DataFrame,
    modeling: pd.DataFrame,
    *,
    analog_count: int,
) -> list[dict[str, object]]:
    features = _hypothesis_selected_features_for_target(target, hypotheses)
    features = _distance_feature_columns(features, modeling.columns)
    labels = _hypothesis_outcome_labels_for_target(target, hypotheses)
    required_labels = [
        labels.get("directional_return", ""),
        labels.get("mfe", ""),
        labels.get("mae", ""),
        labels.get("target_before_stop", ""),
    ]
    if not features or any(label not in modeling.columns for label in required_labels):
        return []
    target_date = pd.Timestamp(str(target.get("as_of_date"))).normalize()
    if pd.isna(target_date):
        return []
    dated = modeling.copy()
    date_values = dated["Date"] if "Date" in dated.columns else pd.Series(pd.NaT, index=dated.index)
    dated["_analog_date"] = pd.to_datetime(date_values, errors="coerce").dt.normalize()
    historical = dated.loc[dated["_analog_date"] < target_date].copy()
    historical = historical.dropna(subset=["_analog_date", "symbol", *required_labels])
    if historical.empty:
        return []
    target_payload = {str(key): value for key, value in target.to_dict().items()}
    current_values = _candidate_selected_feature_values(target_payload, tuple(features))
    if current_values is None:
        current_values = _target_feature_values_from_modeling(target, dated, features)
    if current_values is None:
        return []

    feature_frame = _numeric_feature_frame(historical, features)
    current_frame = _numeric_feature_frame(pd.DataFrame([current_values]), features)
    medians = feature_frame.median(axis=0, skipna=True)
    feature_frame = feature_frame.fillna(medians).fillna(0.0)
    current_row = current_frame.fillna(medians).fillna(0.0).iloc[0]
    scale = feature_frame.std(axis=0, ddof=0).replace(0.0, np.nan).fillna(1.0)
    distances = (((feature_frame - current_row) / scale) ** 2).sum(axis=1).pow(0.5)
    scored = historical.copy()
    scored["_distance_score"] = distances
    scored["_analog_scope"] = scored.apply(_row_scope, axis=1)
    target_scope = str(
        target.get("product_class_scope") or target.get("scope") or PRODUCT_CLASS_SCOPE_POOLED
    )
    same_scope = scored.loc[scored["_analog_scope"].astype(str).eq(target_scope)].copy()
    cross_scope = scored.loc[~scored["_analog_scope"].astype(str).eq(target_scope)].copy()
    selected_same = _nearest_analog_rows(same_scope, limit=analog_count)
    remaining = max(analog_count - len(selected_same), 0)
    selected_cross = (
        _nearest_analog_rows(cross_scope, limit=remaining) if remaining else cross_scope.iloc[0:0]
    )
    selected_same = selected_same.assign(_analog_pool="same_scope")
    selected_cross = selected_cross.assign(_analog_pool="cross_scope_fallback")
    selected = pd.concat([selected_same, selected_cross], ignore_index=False, sort=False)
    if selected.empty:
        return []

    rows: list[dict[str, object]] = []
    for rank, (_, row) in enumerate(selected.iterrows(), start=1):
        distance = _as_float(row.get("_distance_score"), default=math.nan)
        similarity = 1.0 / (1.0 + distance) if math.isfinite(distance) else math.nan
        analog_scope = str(row.get("_analog_scope") or PRODUCT_CLASS_SCOPE_POOLED)
        analog_symbol = str(row.get("symbol") or "")
        target_ticker = str(target.get("ticker") or target.get("symbol") or "")
        target_direction = str(target.get("direction") or "")
        target_archetype = str(target.get("archetype") or "")
        rows.append(
            {
                "target_row_id": str(target.get("signal_id") or ""),
                "target_signal_id": str(target.get("signal_id") or ""),
                "generation_id": str(target.get("generation_id") or ""),
                "target_as_of_date": target_date.date().isoformat(),
                "target_ticker": target_ticker,
                "target_direction": target_direction,
                "target_archetype": target_archetype,
                "target_action": str(target.get("action") or ""),
                "target_status": str(
                    target.get("candidate_status") or target.get("decision") or ""
                ),
                "target_score": _as_float(target.get("signal_score"), default=math.nan),
                "target_blocker_reason": _target_blocker_reason(target),
                "target_hypothesis_id": str(target.get("hypothesis_id") or ""),
                "target_model_id": str(target.get("model_id") or ""),
                "target_product_scope": target_scope,
                "target_selection_reason": str(
                    target.get("_target_selection_reason") or "top_blocked_row"
                ),
                "analog_rank": rank,
                "analog_date": pd.Timestamp(row["_analog_date"]).date().isoformat(),
                "analog_ticker": analog_symbol,
                "analog_scope": analog_scope,
                "analog_direction": target_direction,
                "analog_archetype": target_archetype,
                "analog_pool": str(row.get("_analog_pool") or ""),
                "similarity_score": similarity,
                "distance_score": distance,
                "same_symbol": analog_symbol == target_ticker,
                "same_product_scope": analog_scope == target_scope,
                "same_archetype": True,
                "same_direction": True,
                "market_regime": str(
                    row.get(
                        "market_regime_label",
                        row.get("market_regime_cluster_expanding", ""),
                    )
                ),
                "forward_return": _as_float(
                    row.get(labels["directional_return"]), default=math.nan
                ),
                "MFE": _as_float(row.get(labels["mfe"]), default=math.nan),
                "MAE": _as_float(row.get(labels["mae"]), default=math.nan),
                "target_before_stop_result": _target_before_stop_text(
                    row.get(labels["target_before_stop"])
                ),
                "analog_would_have_passed_current_thresholds": (
                    "not_available_existing_artifacts_only"
                ),
                "analog_rejection_reason": "not_available_existing_artifacts_only",
                "outcome_labels_used_for_explanation_only": True,
            }
        )
    return rows


def _nearest_analog_rows(frame: pd.DataFrame, *, limit: int) -> pd.DataFrame:
    if frame.empty or limit <= 0:
        return frame.iloc[0:0].copy()
    return frame.sort_values(
        ["_distance_score", "_analog_date", "symbol"],
        ascending=[True, False, True],
    ).head(limit)


def _blocked_analog_summary_for_target(
    target: pd.Series,
    analogs: list[dict[str, object]],
    *,
    requested_analog_count: int,
) -> dict[str, object]:
    frame = pd.DataFrame(analogs)
    returns = pd.to_numeric(frame.get("forward_return", pd.Series(dtype=float)), errors="coerce")
    mfes = pd.to_numeric(frame.get("MFE", pd.Series(dtype=float)), errors="coerce")
    maes = pd.to_numeric(frame.get("MAE", pd.Series(dtype=float)), errors="coerce")
    tbs = (
        frame.get("target_before_stop_result", pd.Series(dtype=str))
        .astype(str)
        .str.lower()
        .eq("target before stop")
    )
    count = len(frame)
    positive = int((returns > 0.0).sum()) if not returns.empty else 0
    same_scope = int(frame.get("same_product_scope", pd.Series(dtype=bool)).eq(True).sum())
    same_archetype = int(frame.get("same_archetype", pd.Series(dtype=bool)).eq(True).sum())
    support_label = _analog_support_label(
        count=count,
        average_return=_safe_mean(returns),
        win_rate=_safe_mean((returns > 0.0).astype(float)) if count else math.nan,
        tbs_hit_rate=_safe_mean(tbs.astype(float)) if count else math.nan,
    )
    reason = _target_blocker_reason(target)
    summary = {
        "target_row_id": str(target.get("signal_id") or ""),
        "target_signal_id": str(target.get("signal_id") or ""),
        "generation_id": str(target.get("generation_id") or ""),
        "target_as_of_date": str(target.get("as_of_date") or ""),
        "target_ticker": str(target.get("ticker") or target.get("symbol") or ""),
        "target_direction": str(target.get("direction") or ""),
        "target_archetype": str(target.get("archetype") or ""),
        "target_action": str(target.get("action") or ""),
        "target_status": str(target.get("candidate_status") or target.get("decision") or ""),
        "target_score": _as_float(target.get("signal_score"), default=math.nan),
        "target_blocker_reason": reason,
        "target_hypothesis_id": str(target.get("hypothesis_id") or ""),
        "target_model_id": str(target.get("model_id") or ""),
        "target_product_scope": str(
            target.get("product_class_scope") or target.get("scope") or PRODUCT_CLASS_SCOPE_POOLED
        ),
        "target_selection_reason": str(target.get("_target_selection_reason") or "top_blocked_row"),
        "analog_count": count,
        "requested_analog_count": requested_analog_count,
        "same_scope_analog_count": same_scope,
        "same_archetype_analog_count": same_archetype,
        "average_forward_return": _safe_mean(returns),
        "median_forward_return": _safe_median(returns),
        "win_rate": _safe_mean((returns > 0.0).astype(float)) if count else math.nan,
        "target_before_stop_hit_rate": _safe_mean(tbs.astype(float)) if count else math.nan,
        "average_MFE": _safe_mean(mfes),
        "average_MAE": _safe_mean(maes),
        "worst_MAE": _safe_min(maes),
        "best_MFE": _safe_max(mfes),
        "analog_support_label": support_label,
        "key_caution": _analog_key_caution(target, frame, returns, same_scope),
        "positive_forward_outcomes": positive,
        "analog_count_note": _analog_count_note(count, requested_analog_count),
        "analog_footprint_summary": "",
    }
    summary["analog_footprint_summary"] = _blocked_analog_footprint_summary(summary)
    return summary


def _hypothesis_selected_features_for_target(
    target: pd.Series, hypotheses: pd.DataFrame
) -> tuple[str, ...]:
    if hypotheses.empty:
        return ()
    hypothesis_id = str(target.get("hypothesis_id") or "")
    model_family = str(target.get("model_family") or target.get("family") or "")
    hypothesis_ids = (
        hypotheses["hypothesis_id"].astype(str)
        if "hypothesis_id" in hypotheses.columns
        else pd.Series("", index=hypotheses.index, dtype=str)
    )
    matches = hypotheses.loc[hypothesis_ids.eq(hypothesis_id)]
    if model_family and "family" in matches.columns:
        family_matches = matches.loc[matches["family"].astype(str).eq(model_family)]
        if not family_matches.empty:
            matches = family_matches
    if matches.empty or "selected_features" not in matches.columns:
        return ()
    raw = matches.iloc[0].get("selected_features")
    try:
        parsed = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return ()
    if not isinstance(parsed, list):
        return ()
    return tuple(str(feature) for feature in parsed if str(feature))


def _hypothesis_outcome_labels_for_target(
    target: pd.Series, hypotheses: pd.DataFrame
) -> dict[str, str]:
    hypothesis_id = str(target.get("hypothesis_id") or "")
    hypothesis_ids = (
        hypotheses["hypothesis_id"].astype(str)
        if "hypothesis_id" in hypotheses.columns
        else pd.Series("", index=hypotheses.index, dtype=str)
    )
    matches = hypotheses.loc[hypothesis_ids.eq(hypothesis_id)]
    raw = matches.iloc[0].get("outcome_labels") if not matches.empty else None
    try:
        parsed = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    if isinstance(parsed, dict) and parsed:
        return {str(key): str(value) for key, value in parsed.items()}
    spec = default_hypothesis_registry().get(hypothesis_id)
    return dict(spec.outcome_labels) if spec is not None else {}


def _distance_feature_columns(
    selected_features: tuple[str, ...], available_columns: pd.Index
) -> tuple[str, ...]:
    available = set(str(column) for column in available_columns)
    return tuple(
        feature
        for feature in selected_features
        if feature in available and not feature.startswith("label_")
    )


def _target_feature_values_from_modeling(
    target: pd.Series,
    modeling: pd.DataFrame,
    features: tuple[str, ...],
) -> dict[str, float | None] | None:
    target_date = pd.Timestamp(str(target.get("as_of_date"))).normalize()
    ticker = str(target.get("ticker") or target.get("symbol") or "")
    rows = modeling.loc[
        modeling["_analog_date"].eq(target_date) & modeling["symbol"].astype(str).eq(ticker)
    ]
    if rows.empty:
        return None
    row = rows.iloc[0]
    values: dict[str, float | None] = {}
    for feature in features:
        numeric = pd.to_numeric(pd.Series([row.get(feature)]), errors="coerce").iloc[0]
        values[feature] = (
            float(numeric) if pd.notna(numeric) and math.isfinite(float(numeric)) else None
        )
    return values


def _numeric_feature_frame(frame: pd.DataFrame, features: tuple[str, ...]) -> pd.DataFrame:
    output = pd.DataFrame(index=frame.index)
    for feature in features:
        values = (
            frame[feature]
            if feature in frame.columns
            else pd.Series(np.nan, index=frame.index, dtype=float)
        )
        output[feature] = pd.to_numeric(values, errors="coerce")
    return output.replace([np.inf, -np.inf], np.nan)


def _target_blocker_reason(row: pd.Series) -> str:
    decision = str(row.get("decision") or "")
    if decision.startswith("REJECTED"):
        reason = str(row.get("rejection_reason") or "").strip()
    else:
        reason = str(row.get("no_signal_reason") or "").strip()
    return reason or decision or "blocker_reason_unavailable"


def _safe_mean(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.mean()) if not numeric.empty else math.nan


def _safe_median(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.median()) if not numeric.empty else math.nan


def _safe_min(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.min()) if not numeric.empty else math.nan


def _safe_max(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.max()) if not numeric.empty else math.nan


def _analog_support_label(
    *,
    count: int,
    average_return: float,
    win_rate: float,
    tbs_hit_rate: float,
) -> str:
    if count < 3:
        return "INSUFFICIENT_ANALOGS"
    if average_return > 0.0 and win_rate >= 0.55 and tbs_hit_rate >= 0.50:
        return "SUPPORTIVE"
    if average_return <= 0.0 and win_rate < 0.45 and tbs_hit_rate < 0.45:
        return "WEAK"
    return "MIXED"


def _analog_key_caution(
    target: pd.Series,
    analogs: pd.DataFrame,
    returns: pd.Series,
    same_scope_count: int,
) -> str:
    reason = _target_blocker_reason(target).lower()
    if "ood" in reason:
        return "OOD target row"
    if analogs.empty:
        return "insufficient same-scope analogs"
    if same_scope_count < min(len(analogs), DEFAULT_BLOCKED_ROW_ANALOG_COUNT):
        return "insufficient same-scope analogs"
    ticker_share = (
        analogs.get("analog_ticker", pd.Series(dtype=str)).astype(str).value_counts(normalize=True)
    )
    if not ticker_share.empty and float(ticker_share.iloc[0]) >= 0.50:
        return "concentrated in one ticker"
    years = pd.to_datetime(
        analogs.get("analog_date", pd.Series(dtype=str)), errors="coerce"
    ).dt.year
    year_share = years.dropna().astype(int).astype(str).value_counts(normalize=True)
    if not year_share.empty and float(year_share.iloc[0]) >= 0.50:
        return "concentrated in one year"
    numeric_returns = pd.to_numeric(returns, errors="coerce").dropna()
    if len(numeric_returns) >= 3 and float(numeric_returns.std(ddof=0)) >= 0.10:
        return "high analog dispersion"
    similarity = pd.to_numeric(
        analogs.get("similarity_score", pd.Series(dtype=float)), errors="coerce"
    ).dropna()
    if not similarity.empty and float(similarity.mean()) < 0.20:
        return "low similarity"
    return "high analog dispersion" if numeric_returns.empty else "low similarity"


def _analog_count_note(count: int, requested: int) -> str:
    if count >= requested:
        return ""
    return (
        f"Only {count} valid historical analog rows were available before the target date; "
        f"{requested} were requested."
    )


def _blocked_analog_footprint_summary(summary: dict[str, object]) -> str:
    ticker = str(summary.get("target_ticker") or "Candidate")
    archetype = str(summary.get("target_archetype") or "signal").lower().replace(" / ", "-")
    direction = (
        str(summary.get("target_direction") or "")
        .replace("Bullish", "BUY")
        .replace("Bearish", "SELL/SHORT")
    )
    reason = str(summary.get("target_blocker_reason") or "policy blocker").replace("_", " ")
    count = int(_as_float(summary.get("analog_count"), default=0.0))
    positives = int(_as_float(summary.get("positive_forward_outcomes"), default=0.0))
    label = str(summary.get("analog_support_label") or "INSUFFICIENT_ANALOGS").lower()
    average = _as_float(summary.get("average_forward_return"), default=math.nan)
    average_text = f"{average:.2%}" if math.isfinite(average) else "unavailable"
    return (
        f"{ticker} {archetype} {direction} footprint remains research-only because "
        f"{reason}. Historical analogs are {label} with {positives}/{count} positive "
        f"forward outcomes and average forward return {average_text}, but this is "
        "explanatory only and does not override the gate."
    )


def signal_discovery_blocker_report_frames(
    root: str | Path, generation: str = "latest"
) -> dict[str, pd.DataFrame]:
    frames = load_signal_discovery_frames(root, generation=generation)
    blockers = _signal_discovery_blocker_rows(frames)
    metadata = _signal_discovery_blocker_metadata(frames, blockers)
    return {
        "summary": _signal_discovery_blocker_summary(metadata, blockers),
        "metadata": metadata,
        "blocker_rows": blockers,
        "by_reason": _blocker_group(blockers, ["blocker_reason", "blocker_family"]),
        "by_hypothesis": _blocker_group(
            blockers,
            ["hypothesis_id", "archetype", "action", "blocker_reason"],
        ),
        "by_archetype": _blocker_group(blockers, ["archetype", "action", "blocker_reason"]),
        "by_ticker": _blocker_group(blockers, ["ticker", "blocker_reason"]),
        "by_scope": _blocker_group(blockers, ["product_class_scope", "blocker_reason"]),
    }


def export_signal_discovery_blocker_report(
    root: str | Path,
    *,
    generation: str = "latest",
    output: str | Path,
) -> tuple[Path, ...]:
    report = signal_discovery_blocker_report_frames(root, generation=generation)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, frame in report.items():
        path = output_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        written.append(path)
    metadata_json = output_dir / "metadata.json"
    metadata_json.write_text(
        json.dumps(report["metadata"].to_dict(orient="records"), indent=2, default=str),
        encoding="utf-8",
    )
    written.append(metadata_json)
    return tuple(written)


def _signal_discovery_blocker_rows(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    candidates = frames.get("candidates", pd.DataFrame())
    if candidates.empty:
        return pd.DataFrame(columns=_blocker_columns())
    rows: list[dict[str, object]] = []
    for _, row in candidates.iterrows():
        decision = str(row.get("decision") or "")
        candidate_status = str(row.get("candidate_status") or "")
        is_blocked = decision == "NO_SIGNAL" or decision.startswith("REJECTED")
        if not is_blocked:
            continue
        reason = (
            str(row.get("rejection_reason") or "").strip()
            if decision.startswith("REJECTED")
            else str(row.get("no_signal_reason") or "").strip()
        )
        if not reason:
            reason = decision or candidate_status or "blocker_reason_unavailable"
        rows.append(
            {
                "generation_id": row.get("generation_id", ""),
                "signal_id": row.get("signal_id", ""),
                "as_of_date": row.get("as_of_date", ""),
                "ticker": row.get("ticker", row.get("symbol", "")),
                "action": row.get("action", ""),
                "direction": row.get("direction", ""),
                "archetype": row.get("archetype", ""),
                "archetype_id": row.get("archetype_id", ""),
                "hypothesis_id": row.get("hypothesis_id", ""),
                "model_id": row.get("model_id", ""),
                "model_family": row.get("model_family", row.get("family", "")),
                "product_class_scope": row.get("product_class_scope", row.get("scope", "")),
                "decision": decision,
                "candidate_status": candidate_status,
                "blocker_reason": reason,
                "blocker_family": _blocker_family(reason),
                "signal_score": _as_float(row.get("signal_score"), default=math.nan),
                "direction_probability": _as_float(
                    row.get("probability", row.get("calibrated_probability")),
                    default=math.nan,
                ),
                "target_before_stop_probability": _as_float(
                    row.get("target_before_stop_probability"), default=math.nan
                ),
                "expected_return": _as_float(row.get("expected_return"), default=math.nan),
                "expected_mfe": _as_float(row.get("expected_mfe"), default=math.nan),
                "expected_mae": _as_float(row.get("expected_mae"), default=math.nan),
                "ood_feature_rate": _as_float(row.get("ood_feature_rate"), default=math.nan),
                "next_required_event": row.get("next_required_event", ""),
            }
        )
    return pd.DataFrame(rows, columns=_blocker_columns())


def _blocker_columns() -> list[str]:
    return [
        "generation_id",
        "signal_id",
        "as_of_date",
        "ticker",
        "action",
        "direction",
        "archetype",
        "archetype_id",
        "hypothesis_id",
        "model_id",
        "model_family",
        "product_class_scope",
        "decision",
        "candidate_status",
        "blocker_reason",
        "blocker_family",
        "signal_score",
        "direction_probability",
        "target_before_stop_probability",
        "expected_return",
        "expected_mfe",
        "expected_mae",
        "ood_feature_rate",
        "next_required_event",
    ]


def _blocker_family(reason: str) -> str:
    text = reason.lower()
    if "target_before_stop" in text:
        return "target_before_stop"
    if "probability" in text:
        return "direction_probability"
    if "expected_value" in text or "expected_return" in text:
        return "expected_value"
    if "signal_score" in text:
        return "signal_score"
    if "ood" in text:
        return "ood"
    if "cap" in text:
        return "candidate_cap"
    if "conflict" in text:
        return "conflict"
    return "other"


def _signal_discovery_blocker_metadata(
    frames: dict[str, pd.DataFrame], blockers: pd.DataFrame
) -> pd.DataFrame:
    metadata = frames.get("metadata", pd.DataFrame())
    values: dict[str, object] = {
        "schema_version": SIGNAL_DISCOVERY_BLOCKER_REPORT_SCHEMA_VERSION,
        "blocker_rows": len(blockers),
        "distinct_tickers": _distinct_count(blockers, "ticker"),
        "distinct_hypotheses": _distinct_count(blockers, "hypothesis_id"),
        "distinct_archetypes": _distinct_count(blockers, "archetype"),
    }
    if not metadata.empty and {"field", "value"}.issubset(metadata.columns):
        values.update(
            {
                str(row["field"]): row["value"]
                for _, row in metadata.iterrows()
                if str(row.get("field") or "")
            }
        )
    return pd.DataFrame([{"field": key, "value": value} for key, value in sorted(values.items())])


def _signal_discovery_blocker_summary(
    metadata: pd.DataFrame, blockers: pd.DataFrame
) -> pd.DataFrame:
    fields = {
        str(row["field"]): row["value"]
        for _, row in metadata.iterrows()
        if {"field", "value"}.issubset(metadata.columns)
    }
    return pd.DataFrame(
        [
            {
                "schema_version": SIGNAL_DISCOVERY_BLOCKER_REPORT_SCHEMA_VERSION,
                "generation_id": fields.get("generation_id", ""),
                "latest_decision_date": fields.get("latest_decision_date", ""),
                "blocker_rows": len(blockers),
                "no_signal_rows": int((blockers["decision"] == "NO_SIGNAL").sum())
                if "decision" in blockers.columns
                else 0,
                "rejected_rows": int(
                    blockers.get("decision", pd.Series(dtype=str))
                    .astype(str)
                    .str.startswith("REJECTED")
                    .sum()
                )
                if "decision" in blockers.columns
                else 0,
                "distinct_tickers": _distinct_count(blockers, "ticker"),
                "distinct_hypotheses": _distinct_count(blockers, "hypothesis_id"),
                "top_blocker_reason": _top_value(blockers, "blocker_reason"),
            }
        ]
    )


def _blocker_group(blockers: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    output_columns = [
        *group_columns,
        "rows",
        "distinct_tickers",
        "average_signal_score",
        "max_signal_score",
        "average_expected_return",
        "average_target_before_stop_probability",
    ]
    if blockers.empty:
        return pd.DataFrame(columns=output_columns)
    frame = blockers.copy()
    for column in group_columns:
        if column not in frame.columns:
            frame[column] = ""
    grouped = frame.groupby(group_columns, dropna=False)
    output = grouped.agg(
        rows=("ticker", "size"),
        distinct_tickers=("ticker", "nunique"),
        average_signal_score=("signal_score", "mean"),
        max_signal_score=("signal_score", "max"),
        average_expected_return=("expected_return", "mean"),
        average_target_before_stop_probability=(
            "target_before_stop_probability",
            "mean",
        ),
    ).reset_index()
    return output.sort_values(
        ["rows", *group_columns], ascending=[False, *([True] * len(group_columns))]
    ).reset_index(drop=True)


def _distinct_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    return int(frame[column].dropna().astype(str).nunique())


def _top_value(frame: pd.DataFrame, column: str) -> str:
    if frame.empty or column not in frame.columns:
        return ""
    counts = frame[column].dropna().astype(str).value_counts()
    return str(counts.index[0]) if not counts.empty else ""


def _evaluate_hypothesis(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    model_frame: pd.DataFrame,
    latest_date: pd.Timestamp,
    feature_family_by_column: dict[str, str],
    scope_definitions: dict[ProductClassScope, Any],
    config: SignalDiscoveryConfig,
    generation_id: str,
    feature_manifest_hash: str,
) -> dict[str, list[dict[str, object]]]:
    labels = spec.outcome_labels
    required_labels = tuple(labels.values())
    missing_labels = [label for label in required_labels if label not in model_frame.columns]
    base_record = _hypothesis_base_record(spec, archetype, generation_id)
    if missing_labels:
        return _unsupported_result(
            spec,
            base_record,
            reason="missing_labels:" + ",".join(missing_labels),
            generation_id=generation_id,
        )
    frame = _filter_for_hypothesis(model_frame, spec, scope_definitions, config)
    target_label = labels["positive_return"]
    fit_required_labels = tuple(
        labels[key]
        for key in (
            "directional_return",
            "positive_return",
            "mfe",
            "mae",
            "target_before_stop",
            "label_end_date",
        )
    )
    usable = frame.dropna(subset=["Date", "symbol", *fit_required_labels]).copy()
    if len(usable) < (
        config.minimum_training_samples
        + config.minimum_calibration_samples
        + config.minimum_holdout_samples
    ):
        return _unsupported_result(
            spec,
            base_record,
            reason="insufficient_total_samples",
            generation_id=generation_id,
        )
    try:
        split = chronological_train_calibration_holdout_split(
            usable,
            horizon=spec.horizon,
            validation_fraction=0.2,
            holdout_fraction=0.2,
        )
    except ValueError as exc:
        return _unsupported_result(
            spec,
            base_record,
            reason=f"split_failed:{exc}",
            generation_id=generation_id,
        )
    gates = _sample_gate_rows(spec, split, config, generation_id)
    if (
        len(split.train) < config.minimum_training_samples
        or len(split.calibration) < config.minimum_calibration_samples
        or len(split.holdout) < config.minimum_holdout_samples
    ):
        status = (
            "INSUFFICIENT_CALIBRATION_EVIDENCE"
            if len(split.calibration) < config.minimum_calibration_samples
            else "INSUFFICIENT_SPLIT_EVIDENCE"
        )
        return {
            "hypotheses": [
                {
                    **base_record,
                    "family": "",
                    "status": "REJECTED",
                    "rejection_reason": "minimum_split_samples_failed",
                    "train_rows": len(split.train),
                    "calibration_rows": len(split.calibration),
                    "holdout_rows": len(split.holdout),
                }
            ],
            "candidates": [],
            "evidence": [],
            "analogs": [],
            "components": [],
            "gates": gates,
            "calibration_summary": [
                _insufficient_calibration_summary_row(
                    spec,
                    base_record,
                    generation_id=generation_id,
                    family="",
                    status=status,
                    reason="minimum_split_samples_failed",
                    row_count=len(split.calibration),
                    required_minimum=config.minimum_calibration_samples,
                )
            ],
            "probability_distributions": [],
            "probability_buckets": [],
            "diagnostic_thresholds": [],
            "row_level_calibration_audit": [],
        }
    feature_columns = _candidate_feature_columns(split.train, spec, feature_family_by_column)
    missing_families = [
        family
        for family in spec.required_feature_families
        if not any(feature_family_by_column.get(column) == family for column in feature_columns)
    ]
    if missing_families:
        return _unsupported_result(
            spec,
            base_record,
            reason="missing_required_feature_families:" + ",".join(missing_families),
            generation_id=generation_id,
        )
    screen_frame = split.train[["Date", "symbol", *feature_columns]].copy()
    feature_screen = screen_features_for_target(
        screen_frame,
        split.train[target_label],
        target_name=target_label,
        task_type="classification",
        feature_family_by_column=feature_family_by_column,
        max_selected_features=config.max_selected_features,
        random_seed=config.random_seed,
        head_name=spec.hypothesis_id,
        direction=spec.direction,
        horizon=spec.horizon,
        schema_version="multi_angle_signal_feature_screen_v1",
    )
    if not feature_screen.selected_features:
        return _unsupported_result(
            spec,
            base_record,
            reason="feature_screen_selected_zero_features",
            generation_id=generation_id,
        )
    family_results: list[FittedSignalModel] = []
    hypothesis_rows: list[dict[str, object]] = []
    calibration_summary_rows: list[dict[str, object]] = []
    probability_distribution_rows: list[dict[str, object]] = []
    probability_bucket_rows: list[dict[str, object]] = []
    diagnostic_threshold_rows: list[dict[str, object]] = []
    row_level_calibration_rows: list[dict[str, object]] = []
    for family in config.model_families:
        fitted = _fit_family_model(
            family,
            spec,
            archetype,
            feature_screen,
            split.train,
            split.calibration,
            split.holdout,
            generation_id=generation_id,
            config=config,
        )
        if fitted is None:
            hypothesis_rows.append(
                {
                    **base_record,
                    "family": family,
                    "status": "REJECTED",
                    "rejection_reason": "model_fit_failed",
                    "selected_feature_count": len(feature_screen.selected_features),
                    "selected_features": json.dumps(list(feature_screen.selected_features)),
                    "selected_feature_manifest_hash": feature_screen.selected_feature_manifest_hash,
                    "train_rows": len(split.train),
                    "calibration_rows": len(split.calibration),
                    "holdout_rows": len(split.holdout),
                    **_calibration_metadata_fields(
                        status="MODEL_FIT_FAILED",
                        row_count=len(split.calibration),
                        base_rate=math.nan,
                        artifact_hash="",
                        threshold_hash="",
                        row_level_hash="",
                    ),
                }
            )
            calibration_summary_rows.append(
                _insufficient_calibration_summary_row(
                    spec,
                    base_record,
                    generation_id=generation_id,
                    family=family,
                    status="MODEL_FIT_FAILED",
                    reason="model_fit_failed",
                    row_count=len(split.calibration),
                    required_minimum=config.minimum_calibration_samples,
                )
            )
            continue
        family_results.append(fitted)
        calibration_summary = fitted.calibration_audit["calibration_summary"]
        probability_distributions = fitted.calibration_audit["probability_distributions"]
        probability_buckets = fitted.calibration_audit["probability_buckets"]
        diagnostic_thresholds = fitted.calibration_audit["diagnostic_thresholds"]
        row_level_calibration = fitted.calibration_audit["row_level_calibration_audit"]
        calibration_summary_rows.extend(_frame_records(calibration_summary))
        probability_distribution_rows.extend(_frame_records(probability_distributions))
        probability_bucket_rows.extend(_frame_records(probability_buckets))
        diagnostic_threshold_rows.extend(_frame_records(diagnostic_thresholds))
        row_level_calibration_rows.extend(_frame_records(row_level_calibration))
        pooled_summary = _pooled_calibration_summary(calibration_summary)
        hypothesis_rows.append(
            {
                **base_record,
                "family": family,
                "status": _hypothesis_status(fitted.holdout_metrics),
                "rejection_reason": _hypothesis_rejection_reason(fitted.holdout_metrics),
                "selected_feature_count": len(feature_screen.selected_features),
                "selected_features": json.dumps(list(feature_screen.selected_features)),
                "selected_feature_manifest_hash": feature_screen.selected_feature_manifest_hash,
                "selected_feature_families": json.dumps(feature_screen.selected_feature_families),
                "feature_screen_training_start": feature_screen.training_start,
                "feature_screen_training_end": feature_screen.training_end,
                "feature_screen_training_rows": feature_screen.training_row_count,
                "train_rows": len(split.train),
                "calibration_rows": len(split.calibration),
                "holdout_rows": len(split.holdout),
                **_calibration_metadata_fields(
                    status=str(pooled_summary.get("status", "AVAILABLE")),
                    row_count=int(
                        _as_float(pooled_summary.get("calibration_row_count"), default=0.0)
                    ),
                    base_rate=_as_float(pooled_summary.get("tbs_base_rate"), default=math.nan),
                    artifact_hash=str(pooled_summary.get("artifact_hash") or ""),
                    threshold_hash=str(
                        pooled_summary.get("calibration_diagnostic_threshold_table_hash") or ""
                    ),
                    row_level_hash=str(
                        pooled_summary.get("row_level_calibration_audit_hash") or ""
                    ),
                ),
                **fitted.holdout_metrics,
            }
        )
    if not family_results:
        return {
            "hypotheses": hypothesis_rows,
            "candidates": [],
            "evidence": [],
            "analogs": [],
            "components": [],
            "gates": gates,
            "calibration_summary": calibration_summary_rows,
            "probability_distributions": probability_distribution_rows,
            "probability_buckets": probability_bucket_rows,
            "diagnostic_thresholds": diagnostic_threshold_rows,
            "row_level_calibration_audit": row_level_calibration_rows,
        }
    best = _best_family_result(family_results)
    latest_rows = frame.loc[pd.to_datetime(frame["Date"]).dt.normalize() == latest_date].copy()
    candidates, components = _latest_decisions(
        best,
        latest_rows,
        config=config,
        archetype=archetype,
        generation_id=generation_id,
        feature_manifest_hash=feature_manifest_hash,
    )
    analogs: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for candidate in candidates:
        if str(candidate.get("decision")) in {"BUY_CANDIDATE", "SELL_SHORT_CANDIDATE"}:
            candidate_analogs = _candidate_analogs(best, candidate, config)
            analogs.extend(candidate_analogs)
            evidence.extend(_footprint_evidence_rows(candidate, candidate_analogs, best))
        elif str(candidate.get("decision")) == "NO_SIGNAL":
            evidence.append(_no_signal_evidence(candidate, best))
    return {
        "hypotheses": hypothesis_rows,
        "candidates": candidates,
        "evidence": evidence,
        "analogs": analogs,
        "components": components,
        "gates": gates,
        "calibration_summary": calibration_summary_rows,
        "probability_distributions": probability_distribution_rows,
        "probability_buckets": probability_bucket_rows,
        "diagnostic_thresholds": diagnostic_threshold_rows,
        "row_level_calibration_audit": row_level_calibration_rows,
    }


def _fit_family_model(
    family: str,
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    feature_screen: FeatureScreenResult,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    holdout: pd.DataFrame,
    *,
    generation_id: str,
    config: SignalDiscoveryConfig,
) -> FittedSignalModel | None:
    selected = tuple(feature_screen.selected_features)
    train_targets = _target_frame(train, spec)
    calibration_targets = _target_frame(calibration, spec)
    holdout_targets = _target_frame(holdout, spec)
    if train_targets.empty or calibration_targets.empty or holdout_targets.empty:
        return None
    if train_targets["positive_return"].nunique(dropna=True) < 2:
        return None
    if train_targets["target_before_stop"].nunique(dropna=True) < 2:
        return None
    train_fit = train.loc[train_targets.index].copy()
    calibration_fit = calibration.loc[calibration_targets.index].copy()
    holdout_fit = holdout.loc[holdout_targets.index].copy()
    x_train_raw = train_fit[list(selected)].replace([np.inf, -np.inf], np.nan)
    imputer = SimpleImputer(strategy="median")
    x_train = pd.DataFrame(
        imputer.fit_transform(x_train_raw),
        columns=selected,
        index=train_fit.index,
    )
    q01 = x_train.quantile(0.01).to_dict()
    q99 = x_train.quantile(0.99).to_dict()
    x_cal = _transform_features(calibration_fit, selected, imputer)
    x_holdout = _transform_features(holdout_fit, selected, imputer)
    try:
        primary = _classifier(family, config.random_seed)
        primary.fit(x_train, train_targets["positive_return"].astype(int))
        primary_calibrator = _fit_probability_calibrator(
            _predict_probability(primary, x_cal),
            calibration_targets["positive_return"],
        )
        tbs = _classifier(family, config.random_seed + 7)
        tbs.fit(x_train, train_targets["target_before_stop"].astype(int))
        tbs_calibrator = _fit_probability_calibrator(
            _predict_probability(tbs, x_cal),
            calibration_targets["target_before_stop"],
        )
        return_model = _regressor(family, config.random_seed + 11)
        return_model.fit(x_train, train_targets["directional_return"].astype(float))
        mfe_model = _regressor(family, config.random_seed + 13)
        mfe_model.fit(x_train, train_targets["mfe"].astype(float))
        mae_model = _regressor(family, config.random_seed + 17)
        mae_model.fit(x_train, train_targets["mae"].astype(float))
    except ValueError:
        return None

    calibration_tbs_raw = _predict_probability(tbs, x_cal)
    calibration_tbs = _apply_probability_calibrator(tbs_calibrator, calibration_tbs_raw)
    calibration_audit = _calibration_audit_frames(
        spec,
        archetype,
        family=family,
        feature_screen=feature_screen,
        calibration=calibration_fit,
        targets=calibration_targets,
        raw_tbs_probability=calibration_tbs_raw,
        calibrated_tbs_probability=calibration_tbs,
        calibrator=tbs_calibrator,
        generation_id=generation_id,
        config=config,
    )

    holdout_primary_raw = _predict_probability(primary, x_holdout)
    holdout_primary = _apply_probability_calibrator(primary_calibrator, holdout_primary_raw)
    holdout_tbs_raw = _predict_probability(tbs, x_holdout)
    holdout_tbs = _apply_probability_calibrator(tbs_calibrator, holdout_tbs_raw)
    holdout_return = pd.Series(return_model.predict(x_holdout), index=holdout.index)
    holdout_mfe = pd.Series(mfe_model.predict(x_holdout), index=holdout.index)
    holdout_mae = pd.Series(mae_model.predict(x_holdout), index=holdout.index)
    metrics = _holdout_metrics(
        spec,
        holdout_fit,
        holdout_targets,
        holdout_primary,
        holdout_tbs,
        holdout_return,
        holdout_mfe,
        holdout_mae,
        config=config,
    )
    return FittedSignalModel(
        family=family,
        hypothesis=spec,
        selected_features=selected,
        feature_screen=feature_screen,
        imputer=imputer,
        train_q01={str(key): float(value) for key, value in q01.items()},
        train_q99={str(key): float(value) for key, value in q99.items()},
        primary_classifier=primary,
        primary_calibrator=primary_calibrator,
        tbs_classifier=tbs,
        tbs_calibrator=tbs_calibrator,
        return_regressor=return_model,
        mfe_regressor=mfe_model,
        mae_regressor=mae_model,
        train_frame=train_fit.copy(),
        holdout_metrics=metrics,
        calibration_audit=calibration_audit,
    )


def _calibration_metadata_fields(
    *,
    status: str,
    row_count: int,
    base_rate: float,
    artifact_hash: str,
    threshold_hash: str,
    row_level_hash: str,
) -> dict[str, object]:
    return {
        "calibration_audit_schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
        "calibration_evidence_status": status,
        "calibration_audit_artifact_paths": json.dumps(
            _calibration_audit_artifact_paths(),
            sort_keys=True,
        ),
        "calibration_audit_artifact_hashes": json.dumps(
            {
                "calibration_artifact_hash": artifact_hash,
                "calibration_diagnostic_threshold_table_hash": threshold_hash,
                "row_level_calibration_audit_hash": row_level_hash,
            },
            sort_keys=True,
        ),
        "calibration_audit_row_count": row_count,
        "calibration_audit_base_rate": base_rate,
        "calibration_diagnostic_threshold_table_hash": threshold_hash,
        "row_level_calibration_audit_hash": row_level_hash,
    }


def _calibration_audit_artifact_paths() -> dict[str, str]:
    return {
        "calibration_summary": "calibration_summary.csv",
        "calibration_summary_json": "calibration_summary.json",
        "probability_distributions": "probability_distributions.csv",
        "probability_buckets": "probability_buckets.csv",
        "diagnostic_thresholds": "diagnostic_thresholds.csv",
        "row_level_calibration_audit_parquet": "row_level_calibration_audit.parquet",
        "row_level_calibration_audit_csv": "row_level_calibration_audit.csv",
        "calibration_artifact_manifest": "calibration_artifact_manifest.json",
    }


def _pooled_calibration_summary(summary: pd.DataFrame) -> pd.Series:
    if summary.empty:
        return pd.Series(dtype=object)
    pooled = summary.loc[summary["product_scope"].astype(str).eq(PRODUCT_CLASS_SCOPE_POOLED)]
    return pooled.iloc[0] if not pooled.empty else summary.iloc[0]


def _insufficient_calibration_summary_row(
    spec: SignalHypothesisSpec,
    base_record: dict[str, object],
    *,
    generation_id: str,
    family: str,
    status: str,
    reason: str,
    row_count: int,
    required_minimum: int,
) -> dict[str, object]:
    del required_minimum
    action = _audit_action(spec)
    return {
        "schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
        "generation_id": generation_id,
        "hypothesis_id": spec.hypothesis_id,
        "archetype_id": spec.archetype_id,
        "archetype": str(base_record.get("archetype") or spec.archetype_id),
        "action": action,
        "direction": spec.direction,
        "horizon": spec.horizon,
        "product_scope": PRODUCT_CLASS_SCOPE_POOLED,
        "model_family": family,
        "model_id": _audit_model_id(spec, family),
        **_policy_context_fields(spec),
        "status": status,
        "reason": reason,
        "calibration_start_date": "",
        "calibration_end_date": "",
        "calibration_row_count": row_count,
        "positive_tbs_count": 0,
        "negative_tbs_count": 0,
        "tbs_base_rate": math.nan,
        "target_hit_probability": math.nan,
        "stop_hit_probability": math.nan,
        "unresolved_probability": math.nan,
        "average_forward_return": math.nan,
        "average_mfe": math.nan,
        "average_mae": math.nan,
        "naive_base_rate_brier": math.nan,
        "model_brier": math.nan,
        "brier_skill": math.nan,
        "roc_auc": math.nan,
        "pr_auc": math.nan,
        "ece": math.nan,
        "calibration_slope": math.nan,
        "calibration_intercept": math.nan,
        "raw_versus_calibrated_rank_correlation": math.nan,
        "unique_calibrated_probability_count": 0,
        "largest_calibrated_plateau_percentage": math.nan,
        "realized_tbs_rate_by_decile_json": "{}",
        "selected_calibrator": "",
        "calibration_method": "",
        "selected_feature_manifest_hash": "",
        "calibration_diagnostic_threshold_table_hash": "",
        "row_level_calibration_audit_hash": "",
        "artifact_hash": "",
    }


def _calibration_audit_frames(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    feature_screen: FeatureScreenResult,
    calibration: pd.DataFrame,
    targets: pd.DataFrame,
    raw_tbs_probability: pd.Series,
    calibrated_tbs_probability: pd.Series,
    calibrator: Any,
    generation_id: str,
    config: SignalDiscoveryConfig,
) -> dict[str, pd.DataFrame]:
    row_level = _row_level_calibration_audit_frame(
        spec,
        archetype,
        family=family,
        feature_screen=feature_screen,
        calibration=calibration,
        targets=targets,
        raw_tbs_probability=raw_tbs_probability,
        calibrated_tbs_probability=calibrated_tbs_probability,
        generation_id=generation_id,
    )
    row_hash = _frame_content_hash(
        row_level.drop(columns=["calibration_artifact_hash"], errors="ignore")
    )
    row_level["calibration_artifact_hash"] = row_hash

    summary_rows: list[dict[str, object]] = []
    distribution_rows: list[dict[str, object]] = []
    bucket_rows: list[dict[str, object]] = []
    threshold_rows: list[dict[str, object]] = []
    for product_scope, group in _calibration_scope_groups(row_level):
        thresholds = _diagnostic_threshold_rows(
            spec,
            archetype,
            family=family,
            product_scope=product_scope,
            group=group,
            generation_id=generation_id,
            config=config,
        )
        threshold_hash = _frame_content_hash(
            pd.DataFrame(thresholds, columns=DIAGNOSTIC_THRESHOLD_COLUMNS)
        )
        artifact_hash = _stable_audit_hash(
            {
                "generation_id": generation_id,
                "hypothesis_id": spec.hypothesis_id,
                "family": family,
                "product_scope": product_scope,
                "row_level_hash": row_hash,
                "threshold_hash": threshold_hash,
            }
        )
        summary_rows.append(
            _calibration_summary_row(
                spec,
                archetype,
                family=family,
                product_scope=product_scope,
                group=group,
                selected_feature_manifest_hash=feature_screen.selected_feature_manifest_hash,
                calibrator=calibrator,
                generation_id=generation_id,
                threshold_hash=threshold_hash,
                row_level_hash=row_hash,
                artifact_hash=artifact_hash,
            )
        )
        distribution_rows.extend(
            _probability_distribution_rows(
                spec,
                archetype,
                family=family,
                product_scope=product_scope,
                group=group,
                generation_id=generation_id,
            )
        )
        bucket_rows.extend(
            _probability_bucket_rows(
                spec,
                archetype,
                family=family,
                product_scope=product_scope,
                group=group,
                generation_id=generation_id,
                config=config,
            )
        )
        threshold_rows.extend(thresholds)

    return {
        "calibration_summary": pd.DataFrame(summary_rows, columns=CALIBRATION_SUMMARY_COLUMNS),
        "probability_distributions": pd.DataFrame(
            distribution_rows,
            columns=PROBABILITY_DISTRIBUTION_COLUMNS,
        ),
        "probability_buckets": pd.DataFrame(bucket_rows, columns=PROBABILITY_BUCKET_COLUMNS),
        "diagnostic_thresholds": pd.DataFrame(
            threshold_rows,
            columns=DIAGNOSTIC_THRESHOLD_COLUMNS,
        ),
        "row_level_calibration_audit": row_level[ROW_LEVEL_CALIBRATION_AUDIT_COLUMNS],
    }


def _row_level_calibration_audit_frame(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    feature_screen: FeatureScreenResult,
    calibration: pd.DataFrame,
    targets: pd.DataFrame,
    raw_tbs_probability: pd.Series,
    calibrated_tbs_probability: pd.Series,
    generation_id: str,
) -> pd.DataFrame:
    target_time = pd.to_numeric(
        targets.get("time_to_target", pd.Series(dtype=float)), errors="coerce"
    )
    stop_time = pd.to_numeric(targets.get("time_to_stop", pd.Series(dtype=float)), errors="coerce")
    target_hit = target_time.le(float(spec.horizon)) & target_time.notna()
    stop_hit = stop_time.le(float(spec.horizon)) & stop_time.notna()
    rows: list[dict[str, object]] = []
    action = _audit_action(spec)
    model_id = _audit_model_id(spec, family)
    for index, row in calibration.loc[targets.index].iterrows():
        target_row = targets.loc[cast(Any, index)]
        rows.append(
            {
                "schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
                "generation_id": generation_id,
                "hypothesis_id": spec.hypothesis_id,
                "Date": pd.Timestamp(str(row.get("Date"))).date().isoformat(),
                "symbol": str(row.get("symbol") or ""),
                "product_scope": _row_scope(row),
                "archetype": archetype.name,
                "archetype_id": spec.archetype_id,
                "action": action,
                "direction": spec.direction,
                "horizon": spec.horizon,
                "model_family": family,
                "model_id": model_id,
                **_policy_context_fields(spec),
                "raw_probability": _as_float(raw_tbs_probability.get(index), default=math.nan),
                "calibrated_probability": _as_float(
                    calibrated_tbs_probability.get(index),
                    default=math.nan,
                ),
                "TBS_label": int(_as_float(target_row.get("target_before_stop"), default=0.0)),
                "forward_return": _as_float(target_row.get("directional_return"), default=math.nan),
                "MFE": _as_float(target_row.get("mfe"), default=math.nan),
                "MAE": _as_float(target_row.get("mae"), default=math.nan),
                "target_hit": bool(target_hit.get(index, False)),
                "stop_hit": bool(stop_hit.get(index, False)),
                "unresolved": not bool(target_hit.get(index, False) or stop_hit.get(index, False)),
                "time_to_target": _as_float(target_row.get("time_to_target"), default=math.nan),
                "time_to_stop": _as_float(target_row.get("time_to_stop"), default=math.nan),
                "regime": str(
                    row.get(
                        "market_regime_label",
                        row.get("market_regime_cluster_expanding", ""),
                    )
                ),
                "sector": str(row.get("sector", row.get("sector_name", "")) or ""),
                "selected_feature_manifest_hash": feature_screen.selected_feature_manifest_hash,
                "calibration_artifact_hash": "",
            }
        )
    return pd.DataFrame(rows, columns=ROW_LEVEL_CALIBRATION_AUDIT_COLUMNS)


def _calibration_scope_groups(frame: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    groups: list[tuple[str, pd.DataFrame]] = [(PRODUCT_CLASS_SCOPE_POOLED, frame.copy())]
    if "product_scope" not in frame.columns:
        return groups
    for scope, group in frame.groupby(frame["product_scope"].astype(str), sort=True):
        scope_text = str(scope)
        if scope_text == PRODUCT_CLASS_SCOPE_POOLED:
            continue
        groups.append((scope_text, group.copy()))
    return groups


def _calibration_summary_row(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    product_scope: str,
    group: pd.DataFrame,
    selected_feature_manifest_hash: str,
    calibrator: Any,
    generation_id: str,
    threshold_hash: str,
    row_level_hash: str,
    artifact_hash: str,
) -> dict[str, object]:
    labels = pd.to_numeric(group["TBS_label"], errors="coerce")
    calibrated = pd.to_numeric(group["calibrated_probability"], errors="coerce")
    raw = pd.to_numeric(group["raw_probability"], errors="coerce")
    positive_count = int(labels.eq(1).sum())
    negative_count = int(labels.eq(0).sum())
    base_rate = _safe_mean(labels)
    naive_brier = _safe_brier(labels, pd.Series(base_rate, index=labels.index))
    model_brier = _safe_brier(labels, calibrated)
    slope, intercept = _calibration_line(calibrated, labels)
    return {
        "schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
        "generation_id": generation_id,
        "hypothesis_id": spec.hypothesis_id,
        "archetype_id": spec.archetype_id,
        "archetype": archetype.name,
        "action": _audit_action(spec),
        "direction": spec.direction,
        "horizon": spec.horizon,
        "product_scope": product_scope,
        "model_family": family,
        "model_id": _audit_model_id(spec, family),
        **_policy_context_fields(spec),
        "status": "AVAILABLE" if len(group) else "INSUFFICIENT_CALIBRATION_EVIDENCE",
        "reason": "" if len(group) else "empty_calibration_slice",
        "calibration_start_date": _date_min(group.get("Date", pd.Series(dtype=str))),
        "calibration_end_date": _date_max(group.get("Date", pd.Series(dtype=str))),
        "calibration_row_count": len(group),
        "positive_tbs_count": positive_count,
        "negative_tbs_count": negative_count,
        "tbs_base_rate": base_rate,
        "target_hit_probability": _safe_mean(group["target_hit"].astype(float)),
        "stop_hit_probability": _safe_mean(group["stop_hit"].astype(float)),
        "unresolved_probability": _safe_mean(group["unresolved"].astype(float)),
        "average_forward_return": _safe_mean(group["forward_return"]),
        "average_mfe": _safe_mean(group["MFE"]),
        "average_mae": _safe_mean(group["MAE"]),
        "naive_base_rate_brier": naive_brier,
        "model_brier": model_brier,
        "brier_skill": naive_brier - model_brier
        if math.isfinite(naive_brier) and math.isfinite(model_brier)
        else math.nan,
        "roc_auc": _safe_roc_auc(labels, calibrated),
        "pr_auc": _safe_pr_auc(labels, calibrated),
        "ece": _expected_calibration_error(calibrated, labels),
        "calibration_slope": slope,
        "calibration_intercept": intercept,
        "raw_versus_calibrated_rank_correlation": _rank_correlation(raw, calibrated),
        "unique_calibrated_probability_count": _unique_probability_count(calibrated),
        "largest_calibrated_plateau_percentage": _largest_plateau_share(calibrated),
        "realized_tbs_rate_by_decile_json": _realized_tbs_by_decile_json(calibrated, labels),
        "selected_calibrator": _calibrator_name(calibrator),
        "calibration_method": _calibration_method(calibrator),
        "selected_feature_manifest_hash": selected_feature_manifest_hash,
        "calibration_diagnostic_threshold_table_hash": threshold_hash,
        "row_level_calibration_audit_hash": row_level_hash,
        "artifact_hash": artifact_hash,
    }


def _probability_distribution_rows(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    product_scope: str,
    group: pd.DataFrame,
    generation_id: str,
) -> list[dict[str, object]]:
    return [
        _probability_distribution_row(
            spec,
            archetype,
            family=family,
            product_scope=product_scope,
            probability_type="raw_tbs",
            probabilities=pd.to_numeric(group["raw_probability"], errors="coerce"),
            generation_id=generation_id,
        ),
        _probability_distribution_row(
            spec,
            archetype,
            family=family,
            product_scope=product_scope,
            probability_type="calibrated_tbs",
            probabilities=pd.to_numeric(group["calibrated_probability"], errors="coerce"),
            generation_id=generation_id,
        ),
    ]


def _probability_distribution_row(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    product_scope: str,
    probability_type: str,
    probabilities: pd.Series,
    generation_id: str,
) -> dict[str, object]:
    values = pd.to_numeric(probabilities, errors="coerce").dropna()
    quantiles = values.quantile([0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
    row: dict[str, object] = {
        "schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
        "generation_id": generation_id,
        "hypothesis_id": spec.hypothesis_id,
        "archetype_id": spec.archetype_id,
        "archetype": archetype.name,
        "action": _audit_action(spec),
        "direction": spec.direction,
        "horizon": spec.horizon,
        "product_scope": product_scope,
        "model_family": family,
        "model_id": _audit_model_id(spec, family),
        **_policy_context_fields(spec),
        "probability_type": probability_type,
        "min": _safe_min(values),
        "p01": _quantile_value(quantiles, 0.01),
        "p05": _quantile_value(quantiles, 0.05),
        "p10": _quantile_value(quantiles, 0.10),
        "p25": _quantile_value(quantiles, 0.25),
        "median": _quantile_value(quantiles, 0.50),
        "p75": _quantile_value(quantiles, 0.75),
        "p90": _quantile_value(quantiles, 0.90),
        "p95": _quantile_value(quantiles, 0.95),
        "p99": _quantile_value(quantiles, 0.99),
        "max": _safe_max(values),
        "mean": _safe_mean(values),
        "standard_deviation": float(values.std(ddof=0)) if not values.empty else math.nan,
    }
    for threshold in CALIBRATION_DIAGNOSTIC_THRESHOLDS:
        row[f"count_ge_{int(threshold * 100):03d}"] = int(values.ge(threshold).sum())
    return row


def _probability_bucket_rows(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    product_scope: str,
    group: pd.DataFrame,
    generation_id: str,
    config: SignalDiscoveryConfig,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    calibrated = pd.to_numeric(group["calibrated_probability"], errors="coerce")
    for bucket_id in range(10):
        lower = bucket_id / 10.0
        upper = (bucket_id + 1) / 10.0
        mask = calibrated.ge(lower) & (
            calibrated.lt(upper) if bucket_id < 9 else calibrated.le(upper)
        )
        bucket = group.loc[mask].copy()
        rows.append(
            {
                **_audit_row_context(
                    spec,
                    archetype,
                    family=family,
                    product_scope=product_scope,
                    generation_id=generation_id,
                ),
                "bucket_id": bucket_id,
                "bucket_lower_bound": lower,
                "bucket_upper_bound": upper,
                "row_count": len(bucket),
                "average_raw_probability": _safe_mean(
                    bucket.get("raw_probability", pd.Series(dtype=float))
                ),
                "average_calibrated_probability": _safe_mean(
                    bucket.get("calibrated_probability", pd.Series(dtype=float))
                ),
                "observed_tbs_hit_rate": _safe_mean(
                    bucket.get("TBS_label", pd.Series(dtype=float))
                ),
                "average_forward_return": _safe_mean(
                    bucket.get("forward_return", pd.Series(dtype=float))
                ),
                "average_mfe": _safe_mean(bucket.get("MFE", pd.Series(dtype=float))),
                "average_mae": _safe_mean(bucket.get("MAE", pd.Series(dtype=float))),
                "target_hit_probability": _safe_mean(
                    bucket.get("target_hit", pd.Series(dtype=float)).astype(float)
                )
                if not bucket.empty
                else math.nan,
                "stop_hit_probability": _safe_mean(
                    bucket.get("stop_hit", pd.Series(dtype=float)).astype(float)
                )
                if not bucket.empty
                else math.nan,
                "unresolved_probability": _safe_mean(
                    bucket.get("unresolved", pd.Series(dtype=float)).astype(float)
                )
                if not bucket.empty
                else math.nan,
                "average_time_to_target": _safe_mean(
                    bucket.get("time_to_target", pd.Series(dtype=float))
                ),
                "average_time_to_stop": _safe_mean(
                    bucket.get("time_to_stop", pd.Series(dtype=float))
                ),
                "transaction_cost_adjusted_utility": _safe_mean(
                    bucket.get("forward_return", pd.Series(dtype=float)) - config.cost_return
                )
                if not bucket.empty
                else math.nan,
            }
        )
    return rows


def _diagnostic_threshold_rows(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    product_scope: str,
    group: pd.DataFrame,
    generation_id: str,
    config: SignalDiscoveryConfig,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    calibrated = pd.to_numeric(group["calibrated_probability"], errors="coerce")
    labels = pd.to_numeric(group["TBS_label"], errors="coerce")
    positives = int(labels.eq(1).sum())
    for threshold in CALIBRATION_DIAGNOSTIC_THRESHOLDS:
        qualified = group.loc[calibrated.ge(threshold)].copy()
        qualified_labels = pd.to_numeric(
            qualified.get("TBS_label", pd.Series(dtype=float)), errors="coerce"
        )
        row_count = len(qualified)
        hit_rate = _safe_mean(qualified_labels)
        rows.append(
            {
                **_audit_row_context(
                    spec,
                    archetype,
                    family=family,
                    product_scope=product_scope,
                    generation_id=generation_id,
                ),
                "threshold": threshold,
                "qualifying_row_count": row_count,
                "qualifying_row_rate": float(row_count / len(group)) if len(group) else math.nan,
                "observed_tbs_hit_rate": hit_rate,
                "precision": hit_rate,
                "recall": float(qualified_labels.eq(1).sum() / positives)
                if positives
                else math.nan,
                "average_forward_return": _safe_mean(
                    qualified.get("forward_return", pd.Series(dtype=float))
                ),
                "median_forward_return": _safe_median(
                    qualified.get("forward_return", pd.Series(dtype=float))
                ),
                "average_mfe": _safe_mean(qualified.get("MFE", pd.Series(dtype=float))),
                "average_mae": _safe_mean(qualified.get("MAE", pd.Series(dtype=float))),
                "worst_mae": _safe_min(qualified.get("MAE", pd.Series(dtype=float))),
                "target_hit_probability": _safe_mean(
                    qualified.get("target_hit", pd.Series(dtype=float)).astype(float)
                )
                if not qualified.empty
                else math.nan,
                "stop_hit_probability": _safe_mean(
                    qualified.get("stop_hit", pd.Series(dtype=float)).astype(float)
                )
                if not qualified.empty
                else math.nan,
                "unresolved_probability": _safe_mean(
                    qualified.get("unresolved", pd.Series(dtype=float)).astype(float)
                )
                if not qualified.empty
                else math.nan,
                "transaction_cost_adjusted_utility": _safe_mean(
                    qualified.get("forward_return", pd.Series(dtype=float)) - config.cost_return
                )
                if not qualified.empty
                else math.nan,
                "symbol_concentration": _value_concentration(
                    qualified.get("symbol", pd.Series(dtype=str))
                ),
                "year_concentration": _year_concentration(
                    qualified.get("Date", pd.Series(dtype=str))
                ),
                "regime_concentration": _value_concentration(
                    qualified.get("regime", pd.Series(dtype=str))
                ),
                "diagnostic_only": True,
                "production_target_before_stop_threshold": config.target_before_stop_threshold,
            }
        )
    return rows


def _audit_row_context(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    *,
    family: str,
    product_scope: str,
    generation_id: str,
) -> dict[str, object]:
    return {
        "schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
        "generation_id": generation_id,
        "hypothesis_id": spec.hypothesis_id,
        "archetype_id": spec.archetype_id,
        "archetype": archetype.name,
        "action": _audit_action(spec),
        "direction": spec.direction,
        "horizon": spec.horizon,
        "product_scope": product_scope,
        "model_family": family,
        "model_id": _audit_model_id(spec, family),
        **_policy_context_fields(spec),
    }


def _audit_action(spec: SignalHypothesisSpec) -> str:
    return "BUY" if spec.direction == "BUY" else "SELL_SHORT"


def _audit_model_id(spec: SignalHypothesisSpec, family: str) -> str:
    return f"{spec.hypothesis_id}:{family}" if family else spec.hypothesis_id


def _safe_brier(labels: pd.Series, probabilities: pd.Series) -> float:
    frame = pd.DataFrame({"label": labels, "probability": probabilities}).dropna()
    if frame.empty:
        return math.nan
    return float(
        brier_score_loss(
            frame["label"].astype(int),
            frame["probability"].astype(float).clip(0.0, 1.0),
        )
    )


def _safe_roc_auc(labels: pd.Series, probabilities: pd.Series) -> float:
    frame = pd.DataFrame({"label": labels, "probability": probabilities}).dropna()
    if frame.empty or frame["label"].nunique() < 2:
        return math.nan
    return float(roc_auc_score(frame["label"].astype(int), frame["probability"].astype(float)))


def _safe_pr_auc(labels: pd.Series, probabilities: pd.Series) -> float:
    frame = pd.DataFrame({"label": labels, "probability": probabilities}).dropna()
    if frame.empty or frame["label"].nunique() < 2:
        return math.nan
    return float(
        average_precision_score(
            frame["label"].astype(int),
            frame["probability"].astype(float),
        )
    )


def _expected_calibration_error(probabilities: pd.Series, labels: pd.Series) -> float:
    frame = pd.DataFrame({"probability": probabilities, "label": labels}).dropna()
    if frame.empty:
        return math.nan
    total = len(frame)
    error = 0.0
    for bucket_id in range(10):
        lower = bucket_id / 10.0
        upper = (bucket_id + 1) / 10.0
        mask = frame["probability"].ge(lower) & (
            frame["probability"].lt(upper) if bucket_id < 9 else frame["probability"].le(upper)
        )
        bucket = frame.loc[mask]
        if bucket.empty:
            continue
        error += (len(bucket) / total) * abs(
            float(bucket["probability"].mean()) - float(bucket["label"].mean())
        )
    return float(error)


def _calibration_line(probabilities: pd.Series, labels: pd.Series) -> tuple[float, float]:
    frame = pd.DataFrame({"probability": probabilities, "label": labels}).dropna()
    if len(frame) < 2 or frame["probability"].nunique() < 2:
        return math.nan, math.nan
    slope, intercept = np.polyfit(
        frame["probability"].to_numpy(dtype=float),
        frame["label"].to_numpy(dtype=float),
        1,
    )
    return float(slope), float(intercept)


def _rank_correlation(raw: pd.Series, calibrated: pd.Series) -> float:
    frame = pd.DataFrame({"raw": raw, "calibrated": calibrated}).dropna()
    if len(frame) < 2 or frame["raw"].nunique() < 2 or frame["calibrated"].nunique() < 2:
        return math.nan
    value = (
        frame["raw"]
        .rank(method="average")
        .corr(
            frame["calibrated"].rank(method="average"),
            method="spearman",
        )
    )
    return _as_float(value, default=math.nan)


def _unique_probability_count(probabilities: pd.Series) -> int:
    values = pd.to_numeric(probabilities, errors="coerce").dropna().round(12)
    return int(values.nunique())


def _largest_plateau_share(probabilities: pd.Series) -> float:
    values = pd.to_numeric(probabilities, errors="coerce").dropna().round(12)
    if values.empty:
        return math.nan
    return float(values.value_counts().iloc[0] / len(values))


def _realized_tbs_by_decile_json(probabilities: pd.Series, labels: pd.Series) -> str:
    frame = pd.DataFrame({"probability": probabilities, "label": labels}).dropna()
    payload: dict[str, float | None] = {}
    for bucket_id in range(10):
        lower = bucket_id / 10.0
        upper = (bucket_id + 1) / 10.0
        key = f"{lower:.1f}-{upper:.1f}"
        mask = frame["probability"].ge(lower) & (
            frame["probability"].lt(upper) if bucket_id < 9 else frame["probability"].le(upper)
        )
        bucket = frame.loc[mask]
        payload[key] = float(bucket["label"].mean()) if not bucket.empty else None
    return json.dumps(payload, sort_keys=True)


def _calibrator_name(calibrator: Any) -> str:
    return "identity" if calibrator is None else type(calibrator).__name__


def _calibration_method(calibrator: Any) -> str:
    return "raw_probability_passthrough" if calibrator is None else "isotonic_regression"


def _quantile_value(quantiles: pd.Series, quantile: float) -> float:
    if quantiles.empty:
        return math.nan
    return _as_float(quantiles.get(quantile), default=math.nan)


def _date_min(series: pd.Series) -> str:
    values = pd.to_datetime(series, errors="coerce").dropna()
    return values.min().date().isoformat() if not values.empty else ""


def _date_max(series: pd.Series) -> str:
    values = pd.to_datetime(series, errors="coerce").dropna()
    return values.max().date().isoformat() if not values.empty else ""


def _value_concentration(series: pd.Series) -> float:
    values = series.dropna().astype(str)
    values = values.loc[values.str.len() > 0]
    if values.empty:
        return math.nan
    return float(values.value_counts(normalize=True).iloc[0])


def _year_concentration(series: pd.Series) -> float:
    years = pd.to_datetime(series, errors="coerce").dt.year.dropna()
    if years.empty:
        return math.nan
    return float(years.astype(int).astype(str).value_counts(normalize=True).iloc[0])


def _stable_audit_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _frame_content_hash(frame: pd.DataFrame) -> str:
    records = json.loads(frame.to_json(orient="records", date_format="iso"))
    return _stable_audit_hash(records)


def _frame_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], frame.to_dict(orient="records"))


def _latest_decisions(
    fitted: FittedSignalModel,
    latest_rows: pd.DataFrame,
    *,
    config: SignalDiscoveryConfig,
    archetype: SignalArchetypeSpec,
    generation_id: str,
    feature_manifest_hash: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if latest_rows.empty:
        return [], []
    selected = fitted.selected_features
    x_latest = _transform_features(latest_rows, selected, fitted.imputer)
    direction_probability = _apply_probability_calibrator(
        fitted.primary_calibrator,
        _predict_probability(fitted.primary_classifier, x_latest),
    )
    tbs_probability = _apply_probability_calibrator(
        fitted.tbs_calibrator,
        _predict_probability(fitted.tbs_classifier, x_latest),
    )
    expected_return = pd.Series(fitted.return_regressor.predict(x_latest), index=latest_rows.index)
    expected_mfe = pd.Series(fitted.mfe_regressor.predict(x_latest), index=latest_rows.index)
    expected_mae = pd.Series(fitted.mae_regressor.predict(x_latest), index=latest_rows.index)
    ood_rate = _ood_rate(x_latest, fitted.train_q01, fitted.train_q99)
    liquidity = _liquidity_score(latest_rows)

    rows: list[dict[str, object]] = []
    component_rows: list[dict[str, object]] = []
    for position, (_, row) in enumerate(latest_rows.iterrows()):
        components = _signal_score_components(
            direction_probability=float(direction_probability.iloc[position]),
            target_before_stop_probability=float(tbs_probability.iloc[position]),
            expected_return=float(expected_return.iloc[position]),
            expected_mfe=float(expected_mfe.iloc[position]),
            expected_mae=float(expected_mae.iloc[position]),
            ood_rate=float(ood_rate.iloc[position]),
            liquidity_score=float(liquidity.iloc[position]),
            cost_return=config.cost_return,
        )
        decision, reason = _decision_from_components(components, config, fitted.hypothesis)
        action = fitted.hypothesis.action_label if decision != "NO_SIGNAL" else "NO SIGNAL"
        candidate_status = _candidate_status_from_decision(decision)
        signal_id = _stable_id(
            {
                "generation_id": generation_id,
                "hypothesis_id": fitted.hypothesis.hypothesis_id,
                "family": fitted.family,
                "symbol": row.get("symbol"),
                "date": row.get("Date"),
            }
        )
        top_support, top_conflict = _top_support_conflict(row, fitted.hypothesis)
        record: dict[str, object] = {
            "signal_id": signal_id,
            "generation_id": generation_id,
            "scan_id": generation_id,
            "as_of_date": pd.Timestamp(str(row.get("Date"))).date().isoformat(),
            "ticker": str(row.get("symbol")),
            "symbol": str(row.get("symbol")),
            "direction": "Bullish" if fitted.hypothesis.direction == "BUY" else "Bearish",
            "action": action,
            "decision": decision,
            "candidate_status": candidate_status,
            "candidate_classification": candidate_status,
            "edge_status": "SHADOW VALIDATION"
            if candidate_status == "SHADOW_ONLY"
            else "RESEARCH ONLY",
            "archetype": archetype.name,
            "archetype_id": fitted.hypothesis.archetype_id,
            "hypothesis_id": fitted.hypothesis.hypothesis_id,
            "model_id": f"{fitted.hypothesis.hypothesis_id}:{fitted.family}",
            "model_family": fitted.family,
            "family": fitted.family,
            **_policy_context_fields(fitted.hypothesis),
            "target_stop_policy_schema_version": fitted.hypothesis.target_stop_policy_schema_version,
            "target_stop_policy_notice": fitted.hypothesis.target_stop_policy_notice,
            "target_stop_policy_target_multiple": (
                fitted.hypothesis.target_stop_policy_target_multiple
            ),
            "target_stop_policy_stop_multiple": (
                fitted.hypothesis.target_stop_policy_stop_multiple
            ),
            "target_stop_policy_horizon": fitted.hypothesis.horizon
            if fitted.hypothesis.target_stop_policy_id
            else "",
            "target_stop_policy_display": _target_stop_policy_display(fitted.hypothesis),
            "horizon": fitted.hypothesis.horizon,
            "scope": _row_scope(row),
            "product_class_scope": _row_scope(row),
            "row_product_class_role": str(row.get("role", "")),
            "generation": generation_id,
            "feature_snapshot_hash": feature_manifest_hash,
            "calibrated_probability": components["direction_probability"],
            "probability": components["direction_probability"],
            "target_before_stop_probability": components["target_before_stop_probability"],
            "expected_return": components["expected_return"],
            "expected_mfe": components["expected_mfe"],
            "expected_mae": components["expected_mae"],
            "signal_score": components["signal_score"],
            "composite_signal_score": components["signal_score"],
            "risk_adjusted_utility": components["risk_adjusted_utility"],
            "ood_feature_rate": components["ood_feature_rate"],
            "liquidity_score": components["liquidity_score"],
            "footprint_support_score": components["footprint_support_score"],
            "historical_analog_support_score": "explanatory_only",
            "conflict_penalty": components["conflict_penalty"],
            "concentration_penalty": components["concentration_penalty"],
            "top_support": top_support,
            "top_conflict": top_conflict,
            "historical_analog_support": "Computed after selection; explanatory only.",
            "footprint_summary": _footprint_summary_text(fitted.hypothesis, action, decision),
            "supporting_evidence": top_support,
            "top_divergences": top_conflict,
            "selected_feature_values_json": _selected_feature_values_json(row, selected),
            "rejection_reason": reason if decision.startswith("REJECTED") else "",
            "no_signal_reason": reason if decision == "NO_SIGNAL" else "",
            "next_required_event": _next_required_event(decision),
            "not_live_actionable_reason": _not_live_actionable_reason(fitted.hypothesis),
            "open_url": "",
            "candidate_detail_url": "",
        }
        rows.append(record)
        for component, value in components.items():
            component_rows.append(
                {
                    "signal_id": signal_id,
                    "generation_id": generation_id,
                    "hypothesis_id": fitted.hypothesis.hypothesis_id,
                    "model_family": fitted.family,
                    **_policy_context_fields(fitted.hypothesis),
                    "ticker": str(row.get("symbol")),
                    "component": component,
                    "value": value,
                    "used_in_score": component
                    not in {"historical_analog_support_score", "analog_forward_return_mean"},
                }
            )
    return rows, component_rows


def _apply_candidate_caps(frame: pd.DataFrame, config: SignalDiscoveryConfig) -> pd.DataFrame:
    if frame.empty:
        return frame
    output = frame.copy()
    output["_rank_score"] = pd.to_numeric(output["signal_score"], errors="coerce").fillna(-1.0)
    for _hypothesis_id, indexes in output.groupby("hypothesis_id").groups.items():
        group = output.loc[list(indexes)]
        eligible = group.loc[group["decision"].isin(["BUY_CANDIDATE", "SELL_SHORT_CANDIDATE"])]
        keep = set(
            eligible.sort_values(
                ["_rank_score", "ticker"],
                ascending=[False, True],
            )
            .head(config.candidate_cap_per_hypothesis)
            .index
        )
        reject_indexes = [index for index in eligible.index if index not in keep]
        output.loc[reject_indexes, "decision"] = "REJECTED_BY_POLICY"
        output.loc[reject_indexes, "candidate_status"] = "REJECTED_BY_POLICY"
        output.loc[reject_indexes, "candidate_classification"] = "REJECTED_BY_POLICY"
        output.loc[reject_indexes, "rejection_reason"] = "candidate_cap_per_hypothesis"
        output.loc[reject_indexes, "next_required_event"] = "Rejected by candidate cap policy."
    return output.drop(columns=["_rank_score"])


def _holdout_metrics(
    spec: SignalHypothesisSpec,
    holdout: pd.DataFrame,
    targets: pd.DataFrame,
    direction_probability: pd.Series,
    tbs_probability: pd.Series,
    expected_return: pd.Series,
    expected_mfe: pd.Series,
    expected_mae: pd.Series,
    *,
    config: SignalDiscoveryConfig,
) -> dict[str, object]:
    actual = pd.to_numeric(targets["directional_return"], errors="coerce")
    positive = pd.to_numeric(targets["positive_return"], errors="coerce")
    tbs = pd.to_numeric(targets["target_before_stop"], errors="coerce")
    naive_positive = float(positive.mean()) if len(positive) else 0.5
    naive_tbs = float(tbs.mean()) if len(tbs) else 0.5
    brier = float(brier_score_loss(positive.astype(int), direction_probability.clip(0, 1)))
    naive_brier = float(
        brier_score_loss(positive.astype(int), np.full(len(positive), naive_positive))
    )
    tbs_brier = float(brier_score_loss(tbs.astype(int), tbs_probability.clip(0, 1)))
    naive_tbs_brier = float(brier_score_loss(tbs.astype(int), np.full(len(tbs), naive_tbs)))
    net_actual = actual - config.cost_return
    benchmark = _benchmark_returns(holdout, spec)
    return {
        "holdout_rows": len(holdout),
        "holdout_brier": brier,
        "holdout_naive_brier": naive_brier,
        "holdout_brier_skill": naive_brier - brier,
        "holdout_tbs_brier": tbs_brier,
        "holdout_naive_tbs_brier": naive_tbs_brier,
        "holdout_tbs_brier_skill": naive_tbs_brier - tbs_brier,
        "holdout_mean_forward_return": float(actual.mean()),
        "holdout_median_forward_return": float(actual.median()),
        "holdout_mean_net_utility_after_costs": float(net_actual.mean()),
        "holdout_mae_return_model": float(mean_absolute_error(actual, expected_return)),
        "holdout_mse_return_model": float(mean_squared_error(actual, expected_return)),
        "holdout_mfe_mae": float(
            mean_absolute_error(pd.to_numeric(targets["mfe"], errors="coerce"), expected_mfe)
        ),
        "holdout_mae_mae": float(
            mean_absolute_error(pd.to_numeric(targets["mae"], errors="coerce"), expected_mae)
        ),
        "holdout_target_before_stop_rate": float(tbs.mean()),
        "holdout_positive_return_rate": float(positive.mean()),
        "holdout_average_rank_vs_universe": _average_rank_vs_universe(holdout, actual),
        "holdout_beat_cash_rate": float((net_actual > 0).mean()),
        "holdout_beat_benchmark_rate": _beat_benchmark_rate(actual, benchmark),
        "holdout_mean_time_to_target": _mean_label(targets["time_to_target"]),
        "holdout_mean_time_to_stop": _mean_label(targets["time_to_stop"]),
        "holdout_status": "DEVELOPMENT_HOLDOUT",
        "final_holdout_status": "NOT_ENROLLED",
    }


def _target_frame(frame: pd.DataFrame, spec: SignalHypothesisSpec) -> pd.DataFrame:
    labels = spec.outcome_labels
    targets = pd.DataFrame(
        {
            key: pd.to_numeric(frame[label], errors="coerce")
            for key, label in labels.items()
            if key != "label_end_date"
        },
        index=frame.index,
    )
    return targets.dropna(
        subset=[
            "directional_return",
            "positive_return",
            "mfe",
            "mae",
            "target_before_stop",
        ]
    )


def _classifier(family: str, seed: int) -> Any:
    if family == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            max_iter=48,
            learning_rate=0.08,
            max_leaf_nodes=15,
            l2_regularization=0.01,
            random_state=seed,
        )
    if family == "extra_trees":
        return ExtraTreesClassifier(
            n_estimators=48,
            max_depth=8,
            min_samples_leaf=30,
            n_jobs=-1,
            random_state=seed,
        )
    raise ValueError(f"Unsupported family: {family}")


def _regressor(family: str, seed: int) -> Any:
    if family == "hist_gradient_boosting":
        return HistGradientBoostingRegressor(
            max_iter=48,
            learning_rate=0.08,
            max_leaf_nodes=15,
            l2_regularization=0.01,
            random_state=seed,
        )
    if family == "extra_trees":
        return ExtraTreesRegressor(
            n_estimators=48,
            max_depth=8,
            min_samples_leaf=30,
            n_jobs=-1,
            random_state=seed,
        )
    raise ValueError(f"Unsupported family: {family}")


def _predict_probability(model: Any, frame: pd.DataFrame) -> pd.Series:
    probabilities = model.predict_proba(frame)
    values = (
        probabilities[:, 1]
        if probabilities.ndim == 2 and probabilities.shape[1] > 1
        else probabilities
    )
    return pd.Series(values, index=frame.index, dtype=float).clip(0.0, 1.0)


def _fit_probability_calibrator(raw_probability: pd.Series, target: pd.Series) -> Any:
    y = pd.to_numeric(target, errors="coerce").dropna().astype(int)
    raw = raw_probability.loc[y.index].astype(float)
    if len(y) < 30 or y.nunique() < 2 or raw.nunique() < 3:
        return None
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(raw.to_numpy(dtype=float), y.to_numpy(dtype=int))
    return calibrator


def _apply_probability_calibrator(calibrator: Any, raw_probability: pd.Series) -> pd.Series:
    raw = raw_probability.astype(float).clip(0.0, 1.0)
    if calibrator is None:
        return raw
    values = calibrator.predict(raw.to_numpy(dtype=float))
    return pd.Series(values, index=raw.index, dtype=float).clip(0.0, 1.0)


def _transform_features(
    frame: pd.DataFrame, selected: tuple[str, ...], imputer: SimpleImputer
) -> pd.DataFrame:
    raw = frame[list(selected)].replace([np.inf, -np.inf], np.nan)
    return pd.DataFrame(imputer.transform(raw), columns=selected, index=frame.index)


def _signal_score_components(
    *,
    direction_probability: float,
    target_before_stop_probability: float,
    expected_return: float,
    expected_mfe: float,
    expected_mae: float,
    ood_rate: float,
    liquidity_score: float,
    cost_return: float,
) -> dict[str, float]:
    expected_return_after_cost = expected_return - cost_return
    expected_return_score = _clip01((expected_return_after_cost + 0.02) / 0.07)
    mfe_score = _clip01(expected_mfe / 0.10)
    mae_score = _clip01(1.0 - abs(expected_mae) / 0.10)
    ood_penalty = _clip01(ood_rate)
    conflict_penalty = 0.0
    concentration_penalty = 0.0
    footprint_support_score = _clip01(
        0.35 * direction_probability
        + 0.25 * target_before_stop_probability
        + 0.20 * expected_return_score
        + 0.10 * mfe_score
        + 0.10 * mae_score
    )
    risk_adjusted_utility = (
        expected_return_after_cost + max(expected_mfe, 0.0) * 0.25 - abs(expected_mae) * 0.35
    )
    signal_score = _clip01(
        0.35 * direction_probability
        + 0.20 * target_before_stop_probability
        + 0.20 * expected_return_score
        + 0.10 * mfe_score
        + 0.08 * mae_score
        + 0.07 * liquidity_score
        - 0.10 * ood_penalty
        - 0.05 * conflict_penalty
        - 0.03 * concentration_penalty
    )
    return {
        "direction_probability": direction_probability,
        "target_before_stop_probability": target_before_stop_probability,
        "expected_return": expected_return,
        "expected_return_after_cost": expected_return_after_cost,
        "expected_return_score": expected_return_score,
        "expected_mfe": expected_mfe,
        "expected_mfe_score": mfe_score,
        "expected_mae": expected_mae,
        "expected_mae_score": mae_score,
        "risk_adjusted_utility": risk_adjusted_utility,
        "ood_feature_rate": ood_rate,
        "ood_penalty": ood_penalty,
        "liquidity_score": liquidity_score,
        "footprint_support_score": footprint_support_score,
        "conflict_penalty": conflict_penalty,
        "concentration_penalty": concentration_penalty,
        "signal_score": signal_score,
    }


def _decision_from_components(
    components: dict[str, float],
    config: SignalDiscoveryConfig,
    spec: SignalHypothesisSpec,
) -> tuple[str, str]:
    if components["ood_feature_rate"] > config.ood_feature_rate_limit:
        return "REJECTED_BY_OOD", "ood_feature_rate_above_limit"
    if components["direction_probability"] < config.probability_threshold:
        return "NO_SIGNAL", "probability_below_threshold"
    if components["target_before_stop_probability"] < config.target_before_stop_threshold:
        return "NO_SIGNAL", "target_before_stop_probability_below_threshold"
    if components["expected_return_after_cost"] < config.expected_return_threshold:
        return "NO_SIGNAL", "expected_value_insufficient_after_cost"
    if components["signal_score"] < config.signal_score_threshold:
        return "NO_SIGNAL", "signal_score_below_threshold"
    return ("BUY_CANDIDATE" if spec.direction == "BUY" else "SELL_SHORT_CANDIDATE"), (
        "model_not_promoted_final_holdout_missing"
    )


def _candidate_status_from_decision(decision: str) -> str:
    if decision in {"BUY_CANDIDATE", "SELL_SHORT_CANDIDATE"}:
        return "SHADOW_ONLY"
    if decision == "NO_SIGNAL":
        return "RESEARCH_ONLY"
    return decision


def _not_live_actionable_reason(spec: SignalHypothesisSpec) -> str:
    if spec.target_stop_policy_status == "EXPERIMENTAL_CANDIDATE":
        return (
            "Experimental target/stop policy. Development evidence only. "
            "Not a live signal and not eligible for promotion without future validation."
        )
    return "No promoted multi-angle signal model exists."


def _candidate_analogs(
    fitted: FittedSignalModel,
    candidate: dict[str, object],
    config: SignalDiscoveryConfig,
) -> list[dict[str, object]]:
    ticker = str(candidate["ticker"])
    as_of = pd.Timestamp(str(candidate["as_of_date"]))
    train = fitted.train_frame.loc[
        pd.to_datetime(fitted.train_frame["Date"]).dt.normalize() < as_of.normalize()
    ].copy()
    if train.empty:
        return []
    selected = fitted.selected_features
    train_x = _transform_features(train, selected, fitted.imputer)
    current_values = _candidate_selected_feature_values(candidate, selected)
    if current_values is None:
        current_symbol = train.loc[train["symbol"].astype(str) == ticker]
        current = train.iloc[-1] if current_symbol.empty else current_symbol.iloc[-1]
        current_frame = pd.DataFrame([current])
    else:
        current_frame = pd.DataFrame([current_values], columns=selected)
    current_x = _transform_features(current_frame, selected, fitted.imputer).iloc[0]
    std = train_x.std(axis=0).replace(0.0, np.nan).fillna(1.0)
    distance = (((train_x - current_x) / std) ** 2).sum(axis=1).pow(0.5)
    nearest_positions = np.argsort(distance.to_numpy(dtype=float))[: config.analog_count]
    labels = fitted.hypothesis.outcome_labels
    rows: list[dict[str, object]] = []
    for rank, position in enumerate(nearest_positions, start=1):
        row = train.iloc[int(position)]
        similarity = float(distance.iloc[int(position)])
        rows.append(
            {
                "signal_id": candidate["signal_id"],
                "generation_id": candidate["generation_id"],
                "hypothesis_id": fitted.hypothesis.hypothesis_id,
                "analog_rank": rank,
                "analog_date": pd.Timestamp(str(row["Date"])).date().isoformat(),
                "symbol": str(row["symbol"]),
                "scope": _row_scope(row),
                "regime": str(
                    row.get("market_regime_label", row.get("market_regime_cluster_expanding", ""))
                ),
                "similarity": similarity,
                "forward_return": _as_float(
                    row.get(labels["directional_return"], math.nan), default=math.nan
                ),
                "MFE": _as_float(row.get(labels["mfe"], math.nan), default=math.nan),
                "MAE": _as_float(row.get(labels["mae"], math.nan), default=math.nan),
                "target_before_stop_result": _target_before_stop_text(
                    row.get(labels["target_before_stop"])
                ),
                "outcome_labels_used_for_explanation_only": True,
            }
        )
    return rows


def _footprint_evidence_rows(
    candidate: dict[str, object],
    analogs: list[dict[str, object]],
    fitted: FittedSignalModel,
) -> list[dict[str, object]]:
    support = str(candidate.get("top_support") or "")
    conflict = str(candidate.get("top_conflict") or "")
    analog_return = _mean([row.get("forward_return") for row in analogs])
    analog_hit_rate = _mean(
        [
            1.0 if row.get("target_before_stop_result") == "target before stop" else 0.0
            for row in analogs
        ]
    )
    rows = [
        {
            "signal_id": candidate["signal_id"],
            "generation_id": candidate["generation_id"],
            "hypothesis_id": fitted.hypothesis.hypothesis_id,
            "Category": "Top support",
            "Claim": "Signal footprint support is measured from selected hypothesis families.",
            "Evidence": support or "Evidence unavailable",
            "Value": support or "Evidence unavailable",
            "Window": f"{fitted.hypothesis.horizon} sessions",
            "Percentile/Rank": "Not available",
            "Comparison Instrument": "Not available",
            "Feature": "selected_feature_families",
            "Evidence Type": "supportive" if support else "neutral",
            "Strength": "moderate" if support else "Unavailable",
            "Missing Data Status": "available" if support else "Evidence unavailable",
        },
        {
            "signal_id": candidate["signal_id"],
            "generation_id": candidate["generation_id"],
            "hypothesis_id": fitted.hypothesis.hypothesis_id,
            "Category": "Top conflict",
            "Claim": "Conflicting evidence is retained separately from support.",
            "Evidence": conflict or "Evidence unavailable",
            "Value": conflict or "Evidence unavailable",
            "Window": f"{fitted.hypothesis.horizon} sessions",
            "Percentile/Rank": "Not available",
            "Comparison Instrument": "Not available",
            "Feature": "conflict_stack",
            "Evidence Type": "conflicting" if conflict else "neutral",
            "Strength": "moderate" if conflict else "Unavailable",
            "Missing Data Status": "available" if conflict else "Evidence unavailable",
        },
        {
            "signal_id": candidate["signal_id"],
            "generation_id": candidate["generation_id"],
            "hypothesis_id": fitted.hypothesis.hypothesis_id,
            "Category": "Historical analog behavior",
            "Claim": "Analog outcomes are computed from prior rows and are explanatory only.",
            "Evidence": "analog average forward return",
            "Value": analog_return if analog_return is not None else "Evidence unavailable",
            "Window": f"{fitted.hypothesis.horizon} sessions",
            "Percentile/Rank": f"{len(analogs)} analogs",
            "Comparison Instrument": "same hypothesis feature set",
            "Feature": "historical_analogs",
            "Evidence Type": "supportive" if (analog_return or 0.0) > 0.0 else "conflicting",
            "Strength": "moderate" if analogs else "Unavailable",
            "Missing Data Status": "available" if analogs else "Evidence unavailable",
        },
        {
            "signal_id": candidate["signal_id"],
            "generation_id": candidate["generation_id"],
            "hypothesis_id": fitted.hypothesis.hypothesis_id,
            "Category": "Residual / unexplained",
            "Claim": "Residual explanation is retained instead of forcing complete attribution.",
            "Evidence": "unexplained component",
            "Value": "10.00%",
            "Window": "current signal",
            "Percentile/Rank": "Not available",
            "Comparison Instrument": "Not available",
            "Feature": "residual_unexplained",
            "Evidence Type": "neutral",
            "Strength": "moderate",
            "Missing Data Status": "available",
        },
    ]
    if analog_hit_rate is not None:
        rows.append(
            {
                "signal_id": candidate["signal_id"],
                "generation_id": candidate["generation_id"],
                "hypothesis_id": fitted.hypothesis.hypothesis_id,
                "Category": "Historical analog behavior",
                "Claim": "Analog target-before-stop rate is explanatory and not used for selection.",
                "Evidence": "analog target-before-stop hit rate",
                "Value": analog_hit_rate,
                "Window": f"{fitted.hypothesis.horizon} sessions",
                "Percentile/Rank": f"{len(analogs)} analogs",
                "Comparison Instrument": "same hypothesis feature set",
                "Feature": "historical_analogs",
                "Evidence Type": "supportive" if analog_hit_rate >= 0.5 else "conflicting",
                "Strength": "moderate",
                "Missing Data Status": "available",
            }
        )
    return rows


def _no_signal_evidence(
    candidate: dict[str, object], fitted: FittedSignalModel
) -> dict[str, object]:
    return {
        "signal_id": candidate["signal_id"],
        "generation_id": candidate["generation_id"],
        "hypothesis_id": fitted.hypothesis.hypothesis_id,
        "Category": "NO_SIGNAL decision",
        "Claim": "No-signal rows preserve the blocking reason.",
        "Evidence": candidate.get("no_signal_reason") or "Evidence unavailable",
        "Value": candidate.get("no_signal_reason") or "Evidence unavailable",
        "Window": f"{fitted.hypothesis.horizon} sessions",
        "Percentile/Rank": "Not available",
        "Comparison Instrument": "Not available",
        "Feature": "signal_policy",
        "Evidence Type": "neutral",
        "Strength": "moderate",
        "Missing Data Status": "available",
    }


def _sample_gate_rows(
    spec: SignalHypothesisSpec,
    split: Any,
    config: SignalDiscoveryConfig,
    generation_id: str,
) -> list[dict[str, object]]:
    checks = (
        ("minimum_training_samples", len(split.train), config.minimum_training_samples),
        ("minimum_calibration_samples", len(split.calibration), config.minimum_calibration_samples),
        ("minimum_holdout_samples", len(split.holdout), config.minimum_holdout_samples),
    )
    return [
        {
            "generation_id": generation_id,
            "hypothesis_id": spec.hypothesis_id,
            **_policy_context_fields(spec),
            "gate_id": gate_id,
            "actual": actual,
            "threshold": threshold,
            "status": "PASS" if actual >= threshold else "FAIL",
            "mandatory": True,
            "evidence_source": "chronological_split",
        }
        for gate_id, actual, threshold in checks
    ]


def _candidate_feature_columns(
    frame: pd.DataFrame,
    spec: SignalHypothesisSpec,
    feature_family_by_column: dict[str, str],
) -> list[str]:
    allowed_families = set(spec.candidate_feature_families)
    columns = [
        column
        for column in numeric_feature_columns(frame)
        if feature_family_by_column.get(column) in allowed_families
    ]
    reject_label_columns(columns)
    return columns


def _filter_for_hypothesis(
    frame: pd.DataFrame,
    spec: SignalHypothesisSpec,
    scope_definitions: dict[ProductClassScope, Any],
    config: SignalDiscoveryConfig,
) -> pd.DataFrame:
    output = frame.copy()
    if config.research_start is not None:
        output = output.loc[pd.to_datetime(output["Date"]) >= pd.Timestamp(config.research_start)]
    if config.research_end is not None:
        output = output.loc[pd.to_datetime(output["Date"]) <= pd.Timestamp(config.research_end)]
    if PRODUCT_CLASS_SCOPE_POOLED in spec.eligible_product_scopes:
        return output
    scoped = []
    for scope in spec.eligible_product_scopes:
        definition = scope_definitions.get(scope)
        if definition is not None:
            scoped.append(filter_frame_for_product_class_scope(output, definition))
    return pd.concat(scoped, ignore_index=True, sort=False) if scoped else output.iloc[0:0].copy()


def _best_family_result(results: list[FittedSignalModel]) -> FittedSignalModel:
    return max(
        results,
        key=lambda item: (
            _as_float(
                item.holdout_metrics.get("holdout_mean_net_utility_after_costs"),
                default=-999.0,
            ),
            _as_float(item.holdout_metrics.get("holdout_brier_skill"), default=-999.0),
        ),
    )


def _hypothesis_status(metrics: dict[str, object]) -> str:
    skill = _as_float(metrics.get("holdout_brier_skill"))
    utility = _as_float(metrics.get("holdout_mean_net_utility_after_costs"))
    return "CANDIDATE" if skill >= 0.0 and utility > -0.01 else "REJECTED"


def _hypothesis_rejection_reason(metrics: dict[str, object]) -> str:
    if _hypothesis_status(metrics) == "CANDIDATE":
        return "final_holdout_required_for_promotion"
    if _as_float(metrics.get("holdout_brier_skill")) < 0.0:
        return "worse_than_naive_control"
    return "expected_utility_insufficient"


def _unsupported_result(
    spec: SignalHypothesisSpec,
    base_record: dict[str, object],
    *,
    reason: str,
    generation_id: str,
) -> dict[str, list[dict[str, object]]]:
    return {
        "hypotheses": [
            {**base_record, "family": "", "status": "UNSUPPORTED", "rejection_reason": reason}
        ],
        "candidates": [],
        "evidence": [],
        "analogs": [],
        "components": [],
        "gates": [
            {
                "generation_id": generation_id,
                "hypothesis_id": spec.hypothesis_id,
                **_policy_context_fields(spec),
                "gate_id": "hypothesis_supported",
                "actual": 0,
                "threshold": 1,
                "status": "FAIL",
                "mandatory": True,
                "evidence_source": reason,
            }
        ],
        "calibration_summary": [
            _insufficient_calibration_summary_row(
                spec,
                base_record,
                generation_id=generation_id,
                family="",
                status="INSUFFICIENT_CALIBRATION_EVIDENCE"
                if "calibration" in reason or "sample" in reason or "insufficient" in reason
                else "UNSUPPORTED",
                reason=reason,
                row_count=0,
                required_minimum=0,
            )
        ],
        "probability_distributions": [],
        "probability_buckets": [],
        "diagnostic_thresholds": [],
        "row_level_calibration_audit": [],
    }


def _hypothesis_base_record(
    spec: SignalHypothesisSpec,
    archetype: SignalArchetypeSpec,
    generation_id: str,
) -> dict[str, object]:
    return {
        "generation_id": generation_id,
        "schema_version": SIGNAL_DISCOVERY_SCHEMA_VERSION,
        "hypothesis_id": spec.hypothesis_id,
        "archetype_id": spec.archetype_id,
        "archetype": archetype.name,
        "direction": spec.direction,
        "horizon": spec.horizon,
        "eligible_product_scopes": json.dumps(list(spec.eligible_product_scopes)),
        "required_feature_families": json.dumps(list(spec.required_feature_families)),
        "candidate_feature_families": json.dumps(list(spec.candidate_feature_families)),
        "outcome_labels": json.dumps(spec.outcome_labels, sort_keys=True),
        "model_tasks": json.dumps(list(spec.model_tasks)),
        "selection_policy": json.dumps(spec.selection_policy, sort_keys=True),
        "validation_policy": json.dumps(spec.validation_policy, sort_keys=True),
        "target_stop_policy_schema_version": spec.target_stop_policy_schema_version,
        "target_stop_policy_id": spec.target_stop_policy_id,
        "target_stop_policy_name": spec.target_stop_policy_name,
        "target_stop_policy_status": spec.target_stop_policy_status,
        "target_stop_policy_hash": spec.target_stop_policy_hash,
        "target_stop_policy_target_multiple": spec.target_stop_policy_target_multiple,
        "target_stop_policy_stop_multiple": spec.target_stop_policy_stop_multiple,
        "target_stop_policy_horizon": spec.horizon if spec.target_stop_policy_id else "",
        "target_stop_policy_notice": spec.target_stop_policy_notice,
        "target_stop_policy_display": _target_stop_policy_display(spec),
        "footprint_categories": json.dumps(list(spec.footprint_categories)),
        "explanation_template": spec.explanation_template,
        "governance_version": spec.governance_version,
    }


def _summary_frame(
    *,
    generation_id: str,
    created_at: str,
    candidates: pd.DataFrame,
    hypotheses: pd.DataFrame,
) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(
            [
                {
                    "generation_id": generation_id,
                    "created_at_utc": created_at,
                    "hypotheses_evaluated": len(hypotheses),
                    "buy_candidates": 0,
                    "sell_candidates": 0,
                    "no_signal_rows": 0,
                    "rejected_rows": 0,
                    "top_archetypes": "",
                }
            ]
        )
    selected = candidates.loc[
        candidates["decision"].isin(["BUY_CANDIDATE", "SELL_SHORT_CANDIDATE"])
    ]
    top_archetypes = (
        selected["archetype"].value_counts().head(5).to_dict() if not selected.empty else {}
    )
    return pd.DataFrame(
        [
            {
                "generation_id": generation_id,
                "created_at_utc": created_at,
                "hypotheses_evaluated": int(candidates["hypothesis_id"].nunique()),
                "buy_candidates": int((candidates["decision"] == "BUY_CANDIDATE").sum()),
                "sell_candidates": int((candidates["decision"] == "SELL_SHORT_CANDIDATE").sum()),
                "no_signal_rows": int((candidates["decision"] == "NO_SIGNAL").sum()),
                "rejected_rows": int(
                    candidates["decision"].astype(str).str.startswith("REJECTED").sum()
                ),
                "top_archetypes": json.dumps(top_archetypes, sort_keys=True),
            }
        ]
    )


def _signal_discovery_policy_comparison_frame(candidates: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "target_stop_policy_id",
        "target_stop_policy_name",
        "target_stop_policy_status",
        "target_stop_policy_hash",
        "hypothesis_id",
        "horizon",
        "scope",
        "row_count",
        "selected_rows",
        "no_signal_rows",
        "rejected_rows",
        "tbs_blocked_rows",
        "average_signal_score",
        "average_target_before_stop_probability",
        "average_expected_return",
        "average_expected_mfe",
        "average_expected_mae",
        "research_only",
        "diagnostic_notice",
    ]
    if candidates.empty or "target_stop_policy_id" not in candidates.columns:
        return pd.DataFrame(columns=columns)
    frame = candidates.loc[candidates["target_stop_policy_id"].astype(str).str.len().gt(0)].copy()
    if frame.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    group_columns = [
        "target_stop_policy_id",
        "target_stop_policy_name",
        "target_stop_policy_status",
        "target_stop_policy_hash",
        "hypothesis_id",
        "horizon",
        "scope",
    ]
    for keys, group in frame.groupby(group_columns, dropna=False, sort=True):
        key_map = dict(zip(group_columns, keys, strict=True))
        decision = group.get("decision", pd.Series(dtype=str)).astype(str)
        reason = (
            group.get("no_signal_reason", pd.Series(dtype=str)).astype(str)
            + " "
            + group.get("rejection_reason", pd.Series(dtype=str)).astype(str)
        )
        rows.append(
            {
                **key_map,
                "row_count": len(group),
                "selected_rows": int(
                    decision.isin(["BUY_CANDIDATE", "SELL_SHORT_CANDIDATE"]).sum()
                ),
                "no_signal_rows": int(decision.eq("NO_SIGNAL").sum()),
                "rejected_rows": int(decision.str.startswith("REJECTED").sum()),
                "tbs_blocked_rows": int(
                    reason.str.contains(
                        "target_before_stop_probability_below_threshold",
                        regex=False,
                    ).sum()
                ),
                "average_signal_score": _safe_mean(
                    group.get("signal_score", pd.Series(dtype=float))
                ),
                "average_target_before_stop_probability": _safe_mean(
                    group.get("target_before_stop_probability", pd.Series(dtype=float))
                ),
                "average_expected_return": _safe_mean(
                    group.get("expected_return", pd.Series(dtype=float))
                ),
                "average_expected_mfe": _safe_mean(
                    group.get("expected_mfe", pd.Series(dtype=float))
                ),
                "average_expected_mae": _safe_mean(
                    group.get("expected_mae", pd.Series(dtype=float))
                ),
                "research_only": True,
                "diagnostic_notice": TARGET_STOP_POLICY_DIAGNOSTIC_NOTICE,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _write_generation(
    directory: Path,
    metadata: dict[str, object],
    frames: dict[str, pd.DataFrame],
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(directory / f"{name}.csv", index=False)
        _parquet_safe_frame(frame).to_parquet(directory / f"{name}.parquet", index=False)
    (directory / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    _write_calibration_audit_json_artifacts(directory, metadata, frames)
    _write_target_stop_policy_json_artifacts(directory, metadata, frames)


def _write_target_stop_policy_json_artifacts(
    directory: Path,
    metadata: dict[str, object],
    frames: dict[str, pd.DataFrame],
) -> None:
    registry = frames.get("target_stop_policy_registry", pd.DataFrame())
    if registry.empty:
        return
    (directory / "target_stop_policy_registry.json").write_text(
        json.dumps(
            {
                "schema_version": TARGET_STOP_POLICY_SCHEMA_VERSION,
                "generation_id": metadata.get("generation_id", ""),
                "diagnostic_only": True,
                "notice": TARGET_STOP_POLICY_DIAGNOSTIC_NOTICE,
                "records": registry.to_dict(orient="records"),
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )


def _write_calibration_audit_json_artifacts(
    directory: Path,
    metadata: dict[str, object],
    frames: dict[str, pd.DataFrame],
) -> None:
    if "calibration_summary" not in frames:
        return
    summary = frames.get("calibration_summary", pd.DataFrame())
    (directory / "calibration_summary.json").write_text(
        json.dumps(
            {
                "schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
                "generation_id": metadata.get("generation_id", ""),
                "records": summary.to_dict(orient="records"),
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    manifest_files: list[dict[str, object]] = []
    for name in (
        "calibration_summary.csv",
        "calibration_summary.json",
        "probability_distributions.csv",
        "probability_buckets.csv",
        "diagnostic_thresholds.csv",
        "row_level_calibration_audit.parquet",
        "row_level_calibration_audit.csv",
    ):
        path = directory / name
        if not path.exists():
            continue
        frame_name = path.stem
        row_count = len(frames.get(frame_name, pd.DataFrame()))
        manifest_files.append(
            {
                "path": path.name,
                "sha256": hash_file(path),
                "size_bytes": path.stat().st_size,
                "row_count": row_count,
            }
        )
    manifest = {
        "schema_version": MULTI_ANGLE_CALIBRATION_AUDIT_SCHEMA_VERSION,
        "generation_id": metadata.get("generation_id", ""),
        "diagnostic_only": True,
        "notice": "Calibration diagnostic only. Not a threshold change and not proof of edge.",
        "files": manifest_files,
    }
    (directory / "calibration_artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def _parquet_safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty and len(frame.columns) == 0:
        return pd.DataFrame({"empty": pd.Series(dtype=str)})
    output = frame.copy()
    for column in output.columns:
        if not pd.api.types.is_object_dtype(output[column]):
            continue
        output[column] = output[column].map(_parquet_safe_value)
    return output


def _parquet_safe_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def _write_latest_pointer(base_dir: Path, generation_id: str) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "latest.json").write_text(
        json.dumps({"generation_id": generation_id}, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_report(reports_dir: Path, metadata: dict[str, object], summary: pd.DataFrame) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": metadata,
        "summary": summary.to_dict(orient="records"),
        "note": "Signal discovery generation is research/shadow only; no promotion occurred.",
    }
    path = reports_dir / f"signal_discovery_{metadata['generation_id']}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _latest_modeling_frame(paths: ProjectPaths) -> tuple[pd.DataFrame, Path]:
    candidates = sorted(
        paths.feature_data.glob("*_modeling.parquet"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        raise FileNotFoundError("No modeling parquet file found. Run build-features first.")
    path = candidates[-1]
    return pd.read_parquet(path), path


def _latest_feature_frame(paths: ProjectPaths) -> tuple[pd.DataFrame, Path]:
    candidates = sorted(
        paths.feature_data.glob("*_features.parquet"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        raise FileNotFoundError("No feature parquet file found. Run build-features first.")
    path = candidates[-1]
    return pd.read_parquet(path), path


def _feature_hash_from_path(path: Path) -> str:
    parts = path.name.split("_")
    return parts[1] if len(parts) > 1 else "unknown"


def _generation_id(created_at: str, config_hash: str, feature_hash: str) -> str:
    digest = hashlib.sha256(f"{created_at}|{config_hash}|{feature_hash}".encode()).hexdigest()[:12]
    timestamp = created_at.replace("-", "").replace(":", "").replace("+00:00", "Z")
    return f"signal_discovery_{timestamp}_{digest}"


def _stable_id(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]


def _clip01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return min(max(value, 0.0), 1.0)


def _ood_rate(frame: pd.DataFrame, q01: dict[str, float], q99: dict[str, float]) -> pd.Series:
    flags = pd.DataFrame(index=frame.index)
    for column in frame.columns:
        low = q01.get(str(column), -math.inf)
        high = q99.get(str(column), math.inf)
        values = pd.to_numeric(frame[column], errors="coerce")
        flags[column] = (values < low) | (values > high)
    return flags.mean(axis=1) if not flags.empty else pd.Series(0.0, index=frame.index)


def _liquidity_score(frame: pd.DataFrame) -> pd.Series:
    if "dollar_volume" in frame.columns:
        values = pd.to_numeric(frame["dollar_volume"], errors="coerce").fillna(0.0)
        score = np.log10(values.clip(lower=1.0)) / 9.0
        return pd.Series(score, index=frame.index).clip(0.0, 1.0)
    return pd.Series(0.5, index=frame.index)


def _top_support_conflict(row: pd.Series, spec: SignalHypothesisSpec) -> tuple[str, str]:
    support_parts: list[str] = []
    conflict_parts: list[str] = []
    for family in spec.required_feature_families:
        features = _family_support_features(family)
        available = [feature for feature in features if feature in row.index]
        if not available:
            conflict_parts.append(f"{family}: evidence unavailable")
            continue
        values = [
            pd.to_numeric(pd.Series([row[feature]]), errors="coerce").iloc[0]
            for feature in available
        ]
        finite = [
            float(value) for value in values if pd.notna(value) and math.isfinite(float(value))
        ]
        if not finite:
            conflict_parts.append(f"{family}: nonfinite local values")
            continue
        mean_abs = float(np.mean(np.abs(finite)))
        if mean_abs > 0:
            support_parts.append(f"{family}: {available[0]}={finite[0]:.4f}")
        else:
            conflict_parts.append(f"{family}: weak local movement")
    return "; ".join(support_parts[:4]), "; ".join(conflict_parts[:4])


def _selected_feature_values_json(row: pd.Series, selected: tuple[str, ...]) -> str:
    values: dict[str, float | None] = {}
    for feature in selected:
        numeric = pd.to_numeric(pd.Series([row.get(feature)]), errors="coerce").iloc[0]
        if pd.isna(numeric) or not math.isfinite(float(numeric)):
            values[feature] = None
        else:
            values[feature] = float(numeric)
    return json.dumps(values, sort_keys=True)


def _candidate_selected_feature_values(
    candidate: dict[str, object], selected: tuple[str, ...]
) -> dict[str, float | None] | None:
    raw = candidate.get("selected_feature_values_json")
    if not raw:
        return None
    try:
        payload = json.loads(str(raw))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    values: dict[str, float | None] = {}
    for feature in selected:
        value = payload.get(feature)
        if value is None:
            values[feature] = None
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            values[feature] = None
            continue
        values[feature] = numeric if math.isfinite(numeric) else None
    return values


def _family_support_features(family: str) -> tuple[str, ...]:
    return {
        "returns_momentum": ("return_5", "return_20", "momentum_20_percentile_252"),
        "trend_structure": ("trend_persistence_20", "range_position_20", "distance_prior_high_20"),
        "volatility_range": ("atr_pct_14", "realized_vol_20", "volatility_expansion_20_63"),
        "volume_participation": ("relative_volume_20", "volume_zscore_20", "dollar_volume"),
        "candle_geometry": ("close_position", "upper_wick_pct", "lower_wick_pct"),
        "market_relative": ("relative_return_vs_spy_20", "spy_return_20", "rolling_corr_vs_spy_63"),
        "sector_relative": ("relative_return_vs_sector_20", "sector_momentum_rank_20"),
        "inverse_leveraged": (
            "inverse_confirmation_iwm_tza_63",
            "relationship_divergence_iwm_tza_5",
        ),
        "breadth": ("breadth_advance_pct", "breadth_dispersion_20"),
        "relationship_graph": (
            "relationship_mutual_info_iwm_tza_63",
            "relationship_breakdown_iwm_tza_63",
        ),
        "regime": ("market_regime_trend_score", "market_regime_volatility_score"),
    }.get(family, ())


def _footprint_summary_text(spec: SignalHypothesisSpec, action: str, decision: str) -> str:
    if decision == "NO_SIGNAL":
        return f"{spec.hypothesis_id} footprint incomplete or below policy threshold"
    if decision.startswith("REJECTED"):
        return f"{spec.hypothesis_id} rejected by discovery policy"
    return f"{action} {spec.archetype_id.replace('_', ' ')} footprint"


def _next_required_event(decision: str) -> str:
    if decision in {"BUY_CANDIDATE", "SELL_SHORT_CANDIDATE"}:
        return "Collect prospective evidence; not live actionable without promotion."
    if decision == "NO_SIGNAL":
        return "No signal; wait for a stronger measured footprint."
    return "Rejected by research policy; review reason before reuse."


def _row_scope(row: pd.Series | dict[str, object]) -> str:
    role = row.get("role")
    if role in {None, ""}:
        return PRODUCT_CLASS_SCOPE_POOLED
    try:
        return product_class_scope_for_role(role)
    except ValueError:
        return PRODUCT_CLASS_SCOPE_POOLED


def _target_before_stop_text(value: object) -> str:
    try:
        numeric = float(cast(Any, value))
    except (TypeError, ValueError):
        return "Evidence unavailable"
    return "target before stop" if numeric >= 0.5 else "stop before target"


def _average_rank_vs_universe(holdout: pd.DataFrame, actual: pd.Series) -> float:
    frame = holdout[["Date"]].copy()
    frame["_actual"] = actual
    ranks = frame.groupby("Date")["_actual"].rank(pct=True)
    return float(ranks.mean()) if not ranks.empty else math.nan


def _benchmark_returns(holdout: pd.DataFrame, spec: SignalHypothesisSpec) -> pd.Series:
    label = spec.outcome_labels["directional_return"]
    if "symbol" not in holdout.columns or label not in holdout.columns:
        return pd.Series(math.nan, index=holdout.index)
    benchmark_rows = holdout.loc[holdout["symbol"].astype(str) == "SPY", ["Date", label]].copy()
    if benchmark_rows.empty:
        return pd.Series(math.nan, index=holdout.index)
    mapping = benchmark_rows.drop_duplicates("Date").set_index("Date")[label]
    return holdout["Date"].map(mapping)


def _beat_benchmark_rate(actual: pd.Series, benchmark: pd.Series) -> float:
    valid = actual.notna() & benchmark.notna()
    return float((actual.loc[valid] > benchmark.loc[valid]).mean()) if valid.any() else math.nan


def _mean_label(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.mean()) if not numeric.empty else math.nan


def _mean(values: list[object]) -> float | None:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(numeric.mean()) if not numeric.empty else None


def _as_float(value: object, *, default: float = 0.0) -> float:
    try:
        numeric = float(cast(Any, value))
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default
