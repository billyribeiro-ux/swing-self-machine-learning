from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from swing_rsi.engine.attribution import explain_candidate
from swing_rsi.engine.models import ModelBundle, predict_bundle
from swing_rsi.engine.selection import (
    SelectionPolicy,
    effective_selection_policy,
    evaluate_candidate_policy,
    order_candidates,
    select_policy_cap_indexes,
    selection_policy_from_metrics,
)
from swing_rsi.engine.storage import dumps, engine_connection


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
    payload = pd.util.hash_pandas_object(frame.sort_index(axis=1), index=True).to_numpy().tobytes()
    return hashlib.sha256(payload).hexdigest()[:24]


def _scan_id(
    *,
    as_of_date: str,
    model_ids: tuple[str, ...],
    model_states: dict[str, str],
    model_eligibility: dict[str, bool],
    model_policy_hashes: dict[str, str],
    universe_snapshot_id: str,
    snapshot_hash: str,
) -> str:
    payload = dumps(
        {
            "as_of_date": as_of_date,
            "model_ids": model_ids,
            "model_states": model_states,
            "model_eligibility": model_eligibility,
            "model_policy_hashes": model_policy_hashes,
            "universe_snapshot_id": universe_snapshot_id,
            "snapshot_hash": snapshot_hash,
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


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
    config: ScannerConfig | None = None,
) -> ScannerSnapshot:
    config = config or ScannerConfig()
    model_states = model_states or {bundle.model_id: "CHAMPION" for bundle in bundles}
    if model_eligibility is None:
        model_eligibility = {bundle.model_id: True for bundle in bundles}
    if not bundles:
        raise ValueError("No deployed champion models are available for scanning")
    bundles_by_id = {bundle.model_id: bundle for bundle in bundles}
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
    scan_id = _scan_id(
        as_of_date=as_of.date().isoformat(),
        model_ids=model_ids,
        model_states={model_id: model_states.get(model_id, "UNKNOWN") for model_id in model_ids},
        model_eligibility={
            model_id: bool(model_eligibility.get(model_id, False)) for model_id in model_ids
        },
        model_policy_hashes={
            model_id: str(model_policy_hashes.get(model_id) or "") for model_id in model_ids
        },
        universe_snapshot_id=universe_snapshot_id,
        snapshot_hash=snapshot_hash,
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / f"{scan_id}_scanner.csv"
    parquet_path = output / f"{scan_id}_scanner.parquet"

    with engine_connection(db_path) as connection:
        existing = connection.execute(
            "SELECT csv_path, parquet_path FROM scanner_snapshots WHERE scan_id = ?",
            (scan_id,),
        ).fetchone()
        if existing is not None and Path(existing["csv_path"]).exists():
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
        item = row.to_dict()
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
        bundle = bundles_by_id[model_id]
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
                "expected_return_out_of_distribution": bool(
                    item.get("expected_return_out_of_distribution", False)
                ),
                "expected_mfe": float(item["expected_mfe"]),
                "expected_mfe_raw": float(item.get("expected_mfe_raw", item["expected_mfe"])),
                "expected_mfe_transformed": float(
                    item.get("expected_mfe_transformed", item["expected_mfe"])
                ),
                "expected_mfe_out_of_distribution": bool(
                    item.get("expected_mfe_out_of_distribution", False)
                ),
                "expected_mae": float(item["expected_mae"]),
                "expected_mae_raw": float(item.get("expected_mae_raw", item["expected_mae"])),
                "expected_mae_transformed": float(
                    item.get("expected_mae_transformed", item["expected_mae"])
                ),
                "expected_mae_out_of_distribution": bool(
                    item.get("expected_mae_out_of_distribution", False)
                ),
                "target_before_stop_probability": target_before_stop_probability,
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
                dumps(asdict(config)),
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
