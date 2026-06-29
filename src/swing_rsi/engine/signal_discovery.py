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
from sklearn.metrics import brier_score_loss, mean_absolute_error, mean_squared_error

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
from swing_rsi.engine.universe import load_universe_config

SIGNAL_DISCOVERY_SCHEMA_VERSION = "multi_angle_signal_discovery_v1"
SIGNAL_DISCOVERY_GENERATION_TYPE = "signal_discovery_generation"
SIGNAL_DISCOVERY_BLOCKER_REPORT_SCHEMA_VERSION = "signal_discovery_blocker_report_v1"
SIGNAL_DISCOVERY_DIR = "signal_discovery"
DEFAULT_SIGNAL_DISCOVERY_CONFIG = Path("configs/signal_discovery/v1.yaml")
DEFAULT_BLOCKED_ROW_ANALOG_COUNT = 10

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
) -> SignalHypothesisSpec:
    labels = _outcome_labels(direction, horizon)
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
    )


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
    return {
        spec.hypothesis_id: spec
        for spec in (
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
        )
    }


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
    }
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
    blocked_frames = signal_discovery_blocked_analog_frames(root, generation=generation)
    for name in ("blocked_row_analogs", "blocked_row_analog_summary"):
        target = output_dir / f"{name}.csv"
        blocked_frames.get(name, pd.DataFrame()).to_csv(target, index=False)
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


def _empty_blocked_analog_frames() -> dict[str, pd.DataFrame]:
    return {
        "blocked_row_analogs": pd.DataFrame(columns=BLOCKED_ROW_ANALOG_COLUMNS),
        "blocked_row_analog_summary": pd.DataFrame(columns=BLOCKED_ROW_ANALOG_SUMMARY_COLUMNS),
    }


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
    for family in config.model_families:
        fitted = _fit_family_model(
            family,
            spec,
            feature_screen,
            split.train,
            split.calibration,
            split.holdout,
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
                }
            )
            continue
        family_results.append(fitted)
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
    }


def _fit_family_model(
    family: str,
    spec: SignalHypothesisSpec,
    feature_screen: FeatureScreenResult,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    holdout: pd.DataFrame,
    *,
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
    )


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
            "not_live_actionable_reason": "No promoted multi-angle signal model exists.",
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
                "gate_id": "hypothesis_supported",
                "actual": 0,
                "threshold": 1,
                "status": "FAIL",
                "mandatory": True,
                "evidence_source": reason,
            }
        ],
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
