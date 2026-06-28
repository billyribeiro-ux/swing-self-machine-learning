from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from swing_rsi.config import ProjectPaths
from swing_rsi.engine.universe import load_universe_config

NOT_AVAILABLE = "Not available"
EVIDENCE_UNAVAILABLE = "Evidence unavailable"

FOOTPRINT_EVIDENCE_COLUMNS = [
    "Category",
    "Claim",
    "Evidence",
    "Value",
    "Window",
    "Percentile/Rank",
    "Comparison Instrument",
    "Feature",
    "Evidence Type",
    "Strength",
    "Missing Data Status",
]
FOOTPRINT_DISPLAY_COLUMNS = [
    "Category",
    "Claim",
    "Evidence",
    "Value",
    "Window",
    "Percentile/Rank",
    "Feature",
    "Evidence Type",
    "Strength",
]
MISSING_EVIDENCE_AUDIT_COLUMNS = [
    "Category",
    "Unavailable Evidence Rows",
    "Total Evidence Rows",
    "Unavailable Share",
    "Status",
]
ANALOG_COLUMNS = [
    "analog_date",
    "symbol",
    "scope",
    "regime",
    "similarity",
    "forward_return",
    "MFE",
    "MAE",
    "target_before_stop_result",
]


@dataclass(frozen=True)
class FootprintFrames:
    summary: pd.DataFrame
    evidence: pd.DataFrame
    supporting_evidence: pd.DataFrame
    conflicting_evidence: pd.DataFrame
    historical_analogs: pd.DataFrame
    residual_unexplained: pd.DataFrame


def footprint_evidence_frames(root: str | Path, candidate: pd.Series) -> FootprintFrames:
    project_root = Path(root)
    feature_frame = _latest_feature_frame(project_root)
    as_of = _candidate_date(candidate)
    ticker = _clean(candidate.get("ticker"))
    feature_row = _candidate_feature_row(feature_frame, ticker, as_of)
    prefix = _candidate_feature_prefix(feature_frame, ticker, as_of)
    same_date = _same_date_feature_rows(feature_frame, as_of)
    roles = _universe_roles(project_root)
    relationship_source = _relationship_source(project_root, ticker)

    evidence_rows: list[dict[str, object]] = []
    evidence_rows.extend(_inverse_strength_rows(candidate, feature_row, same_date, roles))
    evidence_rows.extend(_small_cap_relationship_rows(feature_row, relationship_source, ticker))
    evidence_rows.extend(_volatility_regime_rows(candidate, feature_row, prefix))
    evidence_rows.extend(_broad_market_rows(feature_row))

    analogs = _historical_analog_frame(candidate)
    evidence_rows.extend(_analog_evidence_rows(analogs))
    conflicts = _conflicting_rows(candidate, analogs, evidence_rows)
    evidence_rows.extend(conflicts)

    residual = _residual_frame(candidate)
    evidence_rows.extend(_residual_evidence_rows(residual))

    evidence = pd.DataFrame(evidence_rows, columns=FOOTPRINT_EVIDENCE_COLUMNS)
    supporting = _evidence_subset(evidence, "supportive", "supporting")
    conflicting = _evidence_subset(evidence, "conflicting", "conflicting")
    if conflicting.empty:
        conflicting = pd.DataFrame(
            [
                _row(
                    category="Conflicting evidence",
                    claim="Top conflicts are not available in local evidence.",
                    evidence=EVIDENCE_UNAVAILABLE,
                    value=EVIDENCE_UNAVAILABLE,
                    feature="top_divergences",
                    evidence_type="neutral",
                    strength="Unavailable",
                    missing=EVIDENCE_UNAVAILABLE,
                )
            ],
            columns=FOOTPRINT_EVIDENCE_COLUMNS,
        )
    summary = _summary_frame(candidate, evidence)
    return FootprintFrames(
        summary=summary,
        evidence=evidence,
        supporting_evidence=supporting,
        conflicting_evidence=conflicting,
        historical_analogs=analogs,
        residual_unexplained=residual,
    )


def signal_board_footprint_summary(row: pd.Series) -> str:
    role = _clean(row.get("row_product_class_role") or row.get("product_class_role")).lower()
    direction = _clean(row.get("direction")).lower()
    if "inverse" in role and direction.startswith("bull"):
        return "Risk-off inverse ETF footprint"
    if "leveraged_long" in role:
        return "Leveraged long ETF footprint"
    if "broad_market" in role:
        return "Broad-market ETF footprint"
    return "Model evidence footprint"


def missing_evidence_audit_frame(evidence: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty:
        return pd.DataFrame(
            [
                {
                    "Category": "All categories",
                    "Unavailable Evidence Rows": 0,
                    "Total Evidence Rows": 0,
                    "Unavailable Share": "0.00%",
                    "Status": "No footprint evidence rows",
                }
            ],
            columns=MISSING_EVIDENCE_AUDIT_COLUMNS,
        )
    frame = evidence.copy()
    for column in FOOTPRINT_EVIDENCE_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    missing = (
        frame["Missing Data Status"].astype(str).eq(EVIDENCE_UNAVAILABLE)
        | frame["Evidence"].astype(str).eq(EVIDENCE_UNAVAILABLE)
        | frame["Value"].astype(str).eq(EVIDENCE_UNAVAILABLE)
    )
    audit_rows = []
    for category, group in frame.assign(_missing=missing).groupby("Category", sort=True):
        total = len(group)
        unavailable = int(group["_missing"].sum())
        share = unavailable / total if total else 0.0
        audit_rows.append(
            {
                "Category": str(category),
                "Unavailable Evidence Rows": unavailable,
                "Total Evidence Rows": total,
                "Unavailable Share": _format_percent(share),
                "Status": "Evidence unavailable" if unavailable else "Complete",
            }
        )
    audit = pd.DataFrame(audit_rows, columns=MISSING_EVIDENCE_AUDIT_COLUMNS)
    return audit.sort_values(
        ["Unavailable Evidence Rows", "Category"],
        ascending=[False, True],
    ).reset_index(drop=True)


def _latest_feature_frame(root: Path) -> pd.DataFrame:
    paths = sorted(ProjectPaths(root).feature_data.glob("*_features.parquet"))
    if not paths:
        return pd.DataFrame()
    latest = max(paths, key=lambda path: path.stat().st_mtime)
    try:
        return pd.read_parquet(latest)
    except (FileNotFoundError, OSError, ValueError):
        return pd.DataFrame()


def _candidate_date(candidate: pd.Series) -> pd.Timestamp | None:
    text = _clean(candidate.get("as_of_date"))
    if not text:
        return None
    try:
        timestamp = pd.Timestamp(text)
    except (TypeError, ValueError):
        return None
    if pd.isna(timestamp):
        return None
    return timestamp.normalize()


def _feature_date_series(frame: pd.DataFrame) -> pd.Series:
    if "Date" not in frame.columns:
        return pd.Series(pd.NaT, index=frame.index)
    return pd.to_datetime(frame["Date"], errors="coerce").dt.normalize()


def _candidate_feature_row(
    frame: pd.DataFrame,
    ticker: str,
    as_of: pd.Timestamp | None,
) -> pd.Series | None:
    if frame.empty or not ticker or "symbol" not in frame.columns:
        return None
    rows = frame.loc[frame["symbol"].astype(str) == ticker].copy()
    if rows.empty:
        return None
    if as_of is not None:
        dates = _feature_date_series(rows)
        same_date = rows.loc[dates == as_of]
        if not same_date.empty:
            return same_date.iloc[-1]
        prior = rows.loc[dates <= as_of]
        if not prior.empty:
            return prior.iloc[-1]
    return rows.iloc[-1]


def _candidate_feature_prefix(
    frame: pd.DataFrame,
    ticker: str,
    as_of: pd.Timestamp | None,
) -> pd.DataFrame:
    if frame.empty or not ticker or "symbol" not in frame.columns:
        return pd.DataFrame()
    rows = frame.loc[frame["symbol"].astype(str) == ticker].copy()
    if rows.empty or as_of is None:
        return rows
    dates = _feature_date_series(rows)
    return rows.loc[dates <= as_of]


def _same_date_feature_rows(frame: pd.DataFrame, as_of: pd.Timestamp | None) -> pd.DataFrame:
    if frame.empty or as_of is None or "Date" not in frame.columns:
        return pd.DataFrame()
    dates = _feature_date_series(frame)
    return frame.loc[dates == as_of].copy()


def _universe_roles(root: Path) -> dict[str, str]:
    path = root / "configs" / "universe" / "core.yaml"
    if not path.exists():
        return {}
    try:
        universe = load_universe_config(path)
    except (FileNotFoundError, ValueError, OSError):
        return {}
    return {symbol.symbol: symbol.role for symbol in universe.symbols if symbol.enabled}


def _relationship_source(root: Path, ticker: str) -> str:
    path = root / "configs" / "universe" / "core.yaml"
    if path.exists():
        try:
            universe = load_universe_config(path)
        except (FileNotFoundError, ValueError, OSError):
            universe = None
        if universe is not None:
            for source, related in universe.relationships.items():
                if ticker in related:
                    return source
    return "IWM" if ticker.upper() in {"TZA", "RWM", "TNA"} else ""


def _inverse_strength_rows(
    candidate: pd.Series,
    feature_row: pd.Series | None,
    same_date: pd.DataFrame,
    roles: dict[str, str],
) -> list[dict[str, object]]:
    ticker = _clean(candidate.get("ticker")) or "candidate"
    rows = []
    for period in (1, 5, 10, 20):
        feature = f"return_{period}"
        value = _series_value(feature_row, feature)
        rows.append(
            _metric_row(
                category="Expanding inverse ETF strength",
                claim=f"{ticker} {period}-session return is measured from local features.",
                metric=f"{ticker} return",
                value=value,
                window=f"{period} sessions",
                feature=feature,
                evidence_type=_signed_evidence_type(value, positive_supports=True),
                strength=_signed_strength(value),
            )
        )
    for feature, claim, lookback in (
        (
            "momentum_20_percentile_252",
            f"{ticker} 20-session momentum percentile is measured against its trailing history.",
            "252 sessions",
        ),
        (
            "relative_volume_20",
            f"{ticker} volume confirmation is measured against its 20-session baseline.",
            "20 sessions",
        ),
        (
            "range_percentile_63",
            f"{ticker} range participation is measured against its 63-session range history.",
            "63 sessions",
        ),
    ):
        value = _series_value(feature_row, feature)
        rows.append(
            _metric_row(
                category="Expanding inverse ETF strength",
                claim=claim,
                metric=feature,
                value=value,
                window=lookback,
                feature=feature,
                evidence_type=_threshold_type(value, high=0.6, low=0.4)
                if "percentile" in feature
                else _threshold_type(value, high=1.0, low=0.8),
                strength=_threshold_strength(value, high=0.6 if "percentile" in feature else 1.0),
            )
        )
    rows.append(_peer_rank_row(ticker, same_date, roles, "return_20"))
    return rows


def _peer_rank_row(
    ticker: str,
    same_date: pd.DataFrame,
    roles: dict[str, str],
    feature: str,
) -> dict[str, object]:
    if same_date.empty or "symbol" not in same_date.columns or feature not in same_date.columns:
        return _row(
            category="Expanding inverse ETF strength",
            claim="Inverse ETF peer rank requires same-date feature rows.",
            evidence=EVIDENCE_UNAVAILABLE,
            value=EVIDENCE_UNAVAILABLE,
            window="same session",
            feature=feature,
            evidence_type="neutral",
            strength="Unavailable",
            missing=EVIDENCE_UNAVAILABLE,
        )
    peers = same_date.loc[
        same_date["symbol"].astype(str).map(roles).isin({"inverse_etf", "leveraged_inverse_etf"})
    ].copy()
    peers[feature] = pd.to_numeric(peers[feature], errors="coerce")
    peers = peers.dropna(subset=[feature])
    own = peers.loc[peers["symbol"].astype(str) == ticker]
    if peers.empty or own.empty:
        return _row(
            category="Expanding inverse ETF strength",
            claim="Inverse ETF peer rank requires candidate and peer feature rows.",
            evidence=EVIDENCE_UNAVAILABLE,
            value=EVIDENCE_UNAVAILABLE,
            window="same session",
            feature=feature,
            evidence_type="neutral",
            strength="Unavailable",
            missing=EVIDENCE_UNAVAILABLE,
        )
    sorted_peers = peers.sort_values(feature, ascending=False).reset_index(drop=True)
    rank = int(sorted_peers.index[sorted_peers["symbol"].astype(str) == ticker][0]) + 1
    count = len(sorted_peers)
    value = float(own.iloc[0][feature])
    return _row(
        category="Expanding inverse ETF strength",
        claim=f"{ticker} 20-session return rank is measured versus inverse ETF peers.",
        evidence="Inverse peer return rank",
        value=_format_percent(value),
        window="20 sessions",
        percentile_rank=f"rank {rank}/{count}",
        comparison="inverse ETF peer group",
        feature=feature,
        evidence_type="supportive" if rank <= max(1, math.ceil(count / 3)) else "neutral",
        strength="moderate" if rank <= max(1, math.ceil(count / 3)) else "weak",
    )


def _small_cap_relationship_rows(
    feature_row: pd.Series | None,
    source: str,
    ticker: str,
) -> list[dict[str, object]]:
    if not source:
        return [
            _row(
                category="Small-cap risk-off relationship",
                claim="Comparison instrument is unavailable for this ticker.",
                evidence=EVIDENCE_UNAVAILABLE,
                value=EVIDENCE_UNAVAILABLE,
                feature="relationship_source",
                evidence_type="neutral",
                strength="Unavailable",
                missing=EVIDENCE_UNAVAILABLE,
            )
        ]
    source_lower = source.lower()
    ticker_lower = ticker.lower()
    rows = []
    for window in (5, 20):
        feature = f"{source_lower}_return_{window}"
        value = _series_value(feature_row, feature)
        rows.append(
            _metric_row(
                category="Small-cap risk-off relationship",
                claim=f"{source} {window}-session return is measured for the comparison leg.",
                metric=f"{source} return",
                value=value,
                window=f"{window} sessions",
                comparison=source,
                feature=feature,
                evidence_type=_signed_evidence_type(value, positive_supports=False),
                strength=_signed_strength(value),
            )
        )
    for feature, claim, metric, evidence_type, strength in (
        (
            f"relationship_corr_{source_lower}_{ticker_lower}_63",
            f"{ticker} inverse relationship to {source} is measured by rolling correlation.",
            "rolling correlation",
            "supportive",
            "strong",
        ),
        (
            f"inverse_confirmation_{source_lower}_{ticker_lower}_63",
            f"{ticker} inverse confirmation versus {source} is measured directly.",
            "inverse confirmation",
            "supportive",
            "strong",
        ),
        (
            f"relationship_mutual_info_{source_lower}_{ticker_lower}_63",
            f"{ticker}-{source} relationship stability is measured by mutual information.",
            "mutual information",
            "supportive",
            "moderate",
        ),
        (
            f"relationship_divergence_{source_lower}_{ticker_lower}_5",
            f"{ticker}-{source} relationship divergence is measured over five sessions.",
            "relationship divergence",
            "neutral",
            "weak",
        ),
        (
            f"relationship_breakdown_{source_lower}_{ticker_lower}_63",
            f"{ticker}-{source} relationship breakdown flag is measured over 63 sessions.",
            "relationship breakdown",
            "conflicting",
            "moderate",
        ),
    ):
        value = _series_value(feature_row, feature)
        value_type = evidence_type
        value_strength = strength
        if "corr" in feature and value is not None:
            value_type = "supportive" if value <= -0.5 else "conflicting"
            value_strength = "strong" if abs(value) >= 0.8 else "moderate"
        if "inverse_confirmation" in feature and value is not None:
            value_type = "supportive" if value >= 0.5 else "conflicting"
            value_strength = "strong" if value >= 0.8 else "moderate"
        if "breakdown" in feature and value is not None:
            value_type = "conflicting" if value > 0 else "supportive"
            value_strength = "moderate" if value > 0 else "weak"
        rows.append(
            _metric_row(
                category="Small-cap risk-off relationship",
                claim=claim,
                metric=metric,
                value=value,
                window="63 sessions" if not feature.endswith("_5") else "5 sessions",
                comparison=source,
                feature=feature,
                evidence_type=value_type,
                strength=value_strength,
            )
        )
    return rows


def _volatility_regime_rows(
    candidate: pd.Series,
    feature_row: pd.Series | None,
    prefix: pd.DataFrame,
) -> list[dict[str, object]]:
    rows = []
    for feature, metric, claim, window, high, low in (
        (
            "atr_pct_14",
            "ATR percent of price",
            "ATR is measured as a current volatility input.",
            "14 sessions",
            0.05,
            0.025,
        ),
        (
            "realized_vol_20",
            "realized volatility",
            "Realized volatility is measured from recent returns.",
            "20 sessions",
            0.03,
            0.015,
        ),
        (
            "range_percentile_63",
            "range percentile",
            "Daily range is measured against the 63-session range distribution.",
            "63 sessions",
            0.6,
            0.4,
        ),
        (
            "volatility_expansion_20_63",
            "volatility expansion",
            "20-session volatility is compared with 63-session volatility.",
            "20 / 63 sessions",
            1.0,
            0.8,
        ),
    ):
        value = _series_value(feature_row, feature)
        rows.append(
            _metric_row(
                category="Elevated volatility/range regime",
                claim=claim,
                metric=metric,
                value=value,
                window=window,
                percentile_rank=_historical_percentile(prefix, feature, value),
                feature=feature,
                evidence_type=_threshold_type(value, high=high, low=low),
                strength=_threshold_strength(value, high=high),
            )
        )
    regime = _clean(_series_value_raw(feature_row, "market_regime_label")) or _clean(
        candidate.get("regime")
    )
    rows.append(
        _row(
            category="Elevated volatility/range regime",
            claim="Current regime label is read from the local feature/scanner snapshot.",
            evidence="market regime label",
            value=regime or EVIDENCE_UNAVAILABLE,
            window="current session",
            feature="market_regime_label",
            evidence_type="supportive" if "high_vol" in regime else "neutral",
            strength="moderate" if regime else "Unavailable",
            missing="available" if regime else EVIDENCE_UNAVAILABLE,
        )
    )
    value = _series_value(feature_row, "regime_conditioned_return_20")
    rows.append(
        _metric_row(
            category="Elevated volatility/range regime",
            claim="Regime-conditioned 20-session return is measured for the current state.",
            metric="regime-conditioned return",
            value=value,
            window="20 sessions",
            feature="regime_conditioned_return_20",
            evidence_type=_signed_evidence_type(value, positive_supports=True),
            strength=_signed_strength(value),
        )
    )
    return rows


def _broad_market_rows(feature_row: pd.Series | None) -> list[dict[str, object]]:
    rows = []
    for symbol in ("SPY", "QQQ", "IWM", "DIA"):
        for window in (5, 20):
            feature = f"{symbol.lower()}_return_{window}"
            value = _series_value(feature_row, feature)
            rows.append(
                _metric_row(
                    category="Broad-market relationship deterioration",
                    claim=f"{symbol} {window}-session return is measured as broad-market context.",
                    metric=f"{symbol} return",
                    value=value,
                    window=f"{window} sessions",
                    comparison=symbol,
                    feature=feature,
                    evidence_type=_signed_evidence_type(value, positive_supports=False),
                    strength=_signed_strength(value),
                )
            )
    for symbol in ("SPY", "QQQ", "IWM", "DIA"):
        feature = f"relative_return_vs_{symbol.lower()}_20"
        value = _series_value(feature_row, feature)
        rows.append(
            _metric_row(
                category="Broad-market relationship deterioration",
                claim=f"Candidate relative movement versus {symbol} is measured over 20 sessions.",
                metric="relative return",
                value=value,
                window="20 sessions",
                comparison=symbol,
                feature=feature,
                evidence_type=_signed_evidence_type(value, positive_supports=True),
                strength=_signed_strength(value),
            )
        )
    return rows


def _historical_analog_frame(candidate: pd.Series) -> pd.DataFrame:
    payload = _clean(candidate.get("historical_analogs"))
    if not payload:
        return pd.DataFrame(columns=ANALOG_COLUMNS)
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return pd.DataFrame(columns=ANALOG_COLUMNS)
    if not isinstance(loaded, list):
        return pd.DataFrame(columns=ANALOG_COLUMNS)
    rows = []
    scope = _clean(candidate.get("scope")) or _clean(candidate.get("product_class_scope"))
    regime = _clean(candidate.get("regime"))
    for item in loaded:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "analog_date": _date_string(item.get("Date")),
                "symbol": _clean(item.get("symbol")) or NOT_AVAILABLE,
                "scope": _clean(item.get("scope")) or scope or NOT_AVAILABLE,
                "regime": _clean(item.get("regime")) or regime or NOT_AVAILABLE,
                "similarity": _format_number(item.get("similarity", item.get("distance"))),
                "forward_return": _format_percent(item.get("label_bull_forward_return_10")),
                "MFE": _format_percent(item.get("label_bull_mfe_10")),
                "MAE": _format_percent(item.get("label_bull_mae_10")),
                "target_before_stop_result": _target_before_stop_label(
                    item.get("label_bull_target_before_stop_10")
                ),
            }
        )
    return pd.DataFrame(rows, columns=ANALOG_COLUMNS)


def _analog_evidence_rows(analogs: pd.DataFrame) -> list[dict[str, object]]:
    if analogs.empty:
        return [
            _row(
                category="Historical analog behavior",
                claim="Historical analog records are required for analog claims.",
                evidence=EVIDENCE_UNAVAILABLE,
                value=EVIDENCE_UNAVAILABLE,
                feature="historical_analogs",
                evidence_type="neutral",
                strength="Unavailable",
                missing=EVIDENCE_UNAVAILABLE,
            )
        ]
    returns = analogs["forward_return"].map(_parse_percent)
    tbs = analogs["target_before_stop_result"].astype(str).str.lower().eq("target before stop")
    hit_rate = float(tbs.mean()) if len(tbs) else None
    return [
        _row(
            category="Historical analog behavior",
            claim="Analog count is measured from scanner analog payload.",
            evidence="analog count",
            value=str(len(analogs)),
            window="model training analog search",
            feature="historical_analogs",
            evidence_type="supportive" if len(analogs) >= 5 else "neutral",
            strength="moderate" if len(analogs) >= 5 else "weak",
        ),
        _row(
            category="Historical analog behavior",
            claim="Analog target-before-stop hit rate is measured from analog outcomes.",
            evidence="analog target-before-stop hit rate",
            value=_format_percent(hit_rate),
            window="10 sessions",
            feature="label_bull_target_before_stop_10",
            evidence_type=_threshold_type(hit_rate, high=0.5, low=0.35),
            strength=_threshold_strength(hit_rate, high=0.5),
        ),
        _row(
            category="Historical analog behavior",
            claim="Analog average forward return is measured from analog outcomes.",
            evidence="analog average forward return",
            value=_format_percent(float(returns.mean()))
            if returns.notna().any()
            else EVIDENCE_UNAVAILABLE,
            window="10 sessions",
            feature="label_bull_forward_return_10",
            evidence_type=_signed_evidence_type(
                float(returns.mean()) if returns.notna().any() else None,
                positive_supports=True,
            ),
            strength=_signed_strength(float(returns.mean()) if returns.notna().any() else None),
            missing="available" if returns.notna().any() else EVIDENCE_UNAVAILABLE,
        ),
        _row(
            category="Historical analog behavior",
            claim="Analog median forward return is measured from analog outcomes.",
            evidence="analog median forward return",
            value=_format_percent(float(returns.median()))
            if returns.notna().any()
            else EVIDENCE_UNAVAILABLE,
            window="10 sessions",
            feature="label_bull_forward_return_10",
            evidence_type=_signed_evidence_type(
                float(returns.median()) if returns.notna().any() else None,
                positive_supports=True,
            ),
            strength=_signed_strength(float(returns.median()) if returns.notna().any() else None),
            missing="available" if returns.notna().any() else EVIDENCE_UNAVAILABLE,
        ),
    ]


def _conflicting_rows(
    candidate: pd.Series,
    analogs: pd.DataFrame,
    evidence_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    divergences = _split_semicolon(candidate.get("top_divergences"))
    for item in divergences[:5]:
        rows.append(
            _row(
                category="Conflicting evidence",
                claim="Scanner reported a relationship divergence.",
                evidence=item,
                value=_trailing_number(item) or NOT_AVAILABLE,
                window="reported by scanner",
                feature=item.split()[0] if item else "top_divergences",
                evidence_type="conflicting",
                strength="moderate",
            )
        )
    if _clean(candidate.get("ood_warning")).lower() in {"true", "1"}:
        rows.append(
            _row(
                category="Conflicting evidence",
                claim="Candidate has an OOD warning.",
                evidence="OOD warning",
                value=_clean(candidate.get("ood_warning_details")) or "true",
                feature="ood_warning",
                evidence_type="conflicting",
                strength="strong",
            )
        )
    if not analogs.empty:
        concentration = analogs["symbol"].value_counts(normalize=True).iloc[0]
        if concentration >= 0.6:
            rows.append(
                _row(
                    category="Conflicting evidence",
                    claim="Analog evidence is concentrated in one symbol.",
                    evidence="analog symbol concentration",
                    value=_format_percent(float(concentration)),
                    window="model training analog search",
                    feature="historical_analogs",
                    evidence_type="conflicting",
                    strength="moderate",
                )
            )
    unavailable_count = sum(
        1
        for row in evidence_rows
        if str(row.get("Missing Data Status", "")) == EVIDENCE_UNAVAILABLE
    )
    if unavailable_count:
        rows.append(
            _row(
                category="Conflicting evidence",
                claim="Some footprint measurements are unavailable.",
                evidence="missing evidence count",
                value=str(unavailable_count),
                feature="footprint_evidence",
                evidence_type="conflicting",
                strength="weak",
            )
        )
    if "model_not_promoted" in _clean(candidate.get("rejection_reason")).lower():
        rows.append(
            _row(
                category="Conflicting evidence",
                claim="Model is not promoted; row remains non-live shadow/research evidence.",
                evidence="model promotion status",
                value="model_not_promoted",
                feature="rejection_reason",
                evidence_type="conflicting",
                strength="strong",
            )
        )
    return rows


def _residual_frame(candidate: pd.Series) -> pd.DataFrame:
    categories = _attribution_categories(candidate.get("top_attribution_category"))
    if "residual/unexplained" not in categories:
        categories = _attribution_categories(candidate.get("top_attribution_categories"))
    residual = categories.get("residual/unexplained")
    value = _format_percent(residual / 100.0) if residual is not None else EVIDENCE_UNAVAILABLE
    return pd.DataFrame(
        [
            {
                "component": "residual/unexplained",
                "score": value,
                "reason": (
                    "Model attribution retains an unexplained component; the dashboard does not "
                    "force a 100% explanation."
                ),
                "missing_data_status": "available"
                if residual is not None
                else EVIDENCE_UNAVAILABLE,
            }
        ]
    )


def _residual_evidence_rows(residual: pd.DataFrame) -> list[dict[str, object]]:
    row = residual.iloc[0]
    return [
        _row(
            category="Residual / unexplained",
            claim="Residual attribution is reported instead of forcing full explanation.",
            evidence=str(row["reason"]),
            value=str(row["score"]),
            feature="top_attribution_categories",
            evidence_type="neutral",
            strength="moderate" if row["missing_data_status"] == "available" else "Unavailable",
            missing=str(row["missing_data_status"]),
        )
    ]


def _summary_frame(candidate: pd.Series, evidence: pd.DataFrame) -> pd.DataFrame:
    supportive = int((evidence["Evidence Type"] == "supportive").sum()) if not evidence.empty else 0
    conflicting = (
        int((evidence["Evidence Type"] == "conflicting").sum()) if not evidence.empty else 0
    )
    unavailable = (
        int((evidence["Missing Data Status"] == EVIDENCE_UNAVAILABLE).sum())
        if not evidence.empty
        else 0
    )
    ticker = _clean(candidate.get("ticker")) or "Candidate"
    direction = _clean(candidate.get("direction")) or NOT_AVAILABLE
    status = _clean(candidate.get("status")) or _clean(candidate.get("candidate_classification"))
    status = status or NOT_AVAILABLE
    if supportive > conflicting:
        summary = "Measured footprint leans supportive, with conflicts listed separately."
    elif conflicting > supportive:
        summary = "Measured footprint is mixed or conflict-heavy; review conflicts before use."
    else:
        summary = "Measured footprint is balanced or insufficient; review evidence rows."
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "direction": direction,
                "status": status,
                "summary": summary,
                "supportive_evidence_rows": supportive,
                "conflicting_evidence_rows": conflicting,
                "unavailable_evidence_rows": unavailable,
                "safety_language": "shadow validation; not live actionable",
            }
        ]
    )


def _evidence_subset(evidence: pd.DataFrame, evidence_type: str, label: str) -> pd.DataFrame:
    if evidence.empty:
        return pd.DataFrame(columns=FOOTPRINT_EVIDENCE_COLUMNS)
    subset = evidence.loc[evidence["Evidence Type"] == evidence_type].copy()
    if subset.empty:
        return pd.DataFrame(
            [
                _row(
                    category=f"{label.title()} evidence",
                    claim=f"No {label} measured evidence available.",
                    evidence=EVIDENCE_UNAVAILABLE,
                    value=EVIDENCE_UNAVAILABLE,
                    evidence_type="neutral",
                    strength="Unavailable",
                    missing=EVIDENCE_UNAVAILABLE,
                )
            ],
            columns=FOOTPRINT_EVIDENCE_COLUMNS,
        )
    return subset.head(12).reset_index(drop=True)


def _metric_row(
    *,
    category: str,
    claim: str,
    metric: str,
    value: float | None,
    window: str,
    feature: str,
    evidence_type: str,
    strength: str,
    percentile_rank: str = "",
    comparison: str = "",
) -> dict[str, object]:
    if value is None:
        return _row(
            category=category,
            claim=claim,
            evidence=EVIDENCE_UNAVAILABLE,
            value=EVIDENCE_UNAVAILABLE,
            window=window,
            percentile_rank=percentile_rank,
            comparison=comparison,
            feature=feature,
            evidence_type="neutral",
            strength="Unavailable",
            missing=EVIDENCE_UNAVAILABLE,
        )
    return _row(
        category=category,
        claim=claim,
        evidence=metric,
        value=_format_metric_value(feature, value),
        window=window,
        percentile_rank=percentile_rank,
        comparison=comparison,
        feature=feature,
        evidence_type=evidence_type,
        strength=strength,
    )


def _row(
    *,
    category: str,
    claim: str,
    evidence: object,
    value: object,
    window: str = "",
    percentile_rank: str = "",
    comparison: str = "",
    feature: str = "",
    evidence_type: str,
    strength: str,
    missing: str = "available",
) -> dict[str, object]:
    return {
        "Category": category,
        "Claim": claim,
        "Evidence": evidence,
        "Value": value,
        "Window": window or NOT_AVAILABLE,
        "Percentile/Rank": percentile_rank or NOT_AVAILABLE,
        "Comparison Instrument": comparison or NOT_AVAILABLE,
        "Feature": feature or NOT_AVAILABLE,
        "Evidence Type": evidence_type,
        "Strength": strength,
        "Missing Data Status": missing,
    }


def _series_value(row: pd.Series | None, feature: str) -> float | None:
    value = _series_value_raw(row, feature)
    if value is None:
        return None
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _series_value_raw(row: pd.Series | None, feature: str) -> object | None:
    if row is None or feature not in row.index:
        return None
    value = row.get(feature)
    return None if _is_missing_scalar(value) else value


def _historical_percentile(
    prefix: pd.DataFrame,
    feature: str,
    value: float | None,
) -> str:
    if value is None or prefix.empty or feature not in prefix.columns:
        return NOT_AVAILABLE
    series = pd.to_numeric(prefix[feature], errors="coerce").dropna()
    if series.empty:
        return NOT_AVAILABLE
    percentile = float((series <= value).mean())
    return _format_percent(percentile)


def _signed_evidence_type(value: float | None, *, positive_supports: bool) -> str:
    if value is None:
        return "neutral"
    if abs(value) < 1e-12:
        return "neutral"
    supportive = value > 0 if positive_supports else value < 0
    return "supportive" if supportive else "conflicting"


def _signed_strength(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    magnitude = abs(value)
    if magnitude >= 0.05:
        return "strong"
    if magnitude >= 0.02:
        return "moderate"
    return "weak"


def _threshold_type(value: float | None, *, high: float, low: float | None = None) -> str:
    if value is None:
        return "neutral"
    lower = low if low is not None else high * 0.8
    if value >= high:
        return "supportive"
    if value < lower:
        return "conflicting"
    return "neutral"


def _threshold_strength(value: float | None, *, high: float) -> str:
    if value is None:
        return "Unavailable"
    if value >= high * 1.5:
        return "strong"
    if value >= high:
        return "moderate"
    return "weak"


def _format_metric_value(feature: str, value: float) -> str:
    lowered = feature.lower()
    if (
        "return" in lowered
        or "pct" in lowered
        or "percentile" in lowered
        or "volume_" in lowered
        or "range_" in lowered
        or "volatility_" in lowered
    ):
        return _format_percent(value) if "volume_" not in lowered else _format_number(value)
    return _format_number(value)


def _format_percent(value: object) -> str:
    numeric = _as_float(value)
    if numeric is None:
        return EVIDENCE_UNAVAILABLE
    return f"{numeric:.2%}"


def _format_number(value: object) -> str:
    numeric = _as_float(value)
    if numeric is None:
        return EVIDENCE_UNAVAILABLE
    return f"{numeric:.4f}"


def _as_float(value: object) -> float | None:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _parse_percent(value: object) -> float | None:
    text = _clean(value).replace("%", "")
    if not text:
        return None
    try:
        return float(text) / 100.0
    except ValueError:
        return None


def _target_before_stop_label(value: object) -> str:
    numeric = _as_float(value)
    if numeric is None:
        return EVIDENCE_UNAVAILABLE
    return "target before stop" if numeric >= 0.5 else "stop before target"


def _split_semicolon(value: object) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    return [part.strip() for part in text.split(";") if part.strip()]


def _trailing_number(value: str) -> str:
    tokens = value.replace("%", " %").split()
    for token in reversed(tokens):
        cleaned = token.replace("%", "")
        try:
            numeric = float(cleaned)
        except ValueError:
            continue
        return f"{numeric:.2f}%" if "%" in value else f"{numeric:.4f}"
    return ""


def _attribution_categories(value: object) -> dict[str, float]:
    categories: dict[str, float] = {}
    for part in _split_semicolon(value):
        if ":" not in part:
            continue
        name, raw_value = part.split(":", 1)
        cleaned = raw_value.strip().replace("%", "")
        try:
            categories[name.strip()] = float(cleaned)
        except ValueError:
            continue
    return categories


def _date_string(value: object) -> str:
    text = _clean(value)
    if not text:
        return NOT_AVAILABLE
    try:
        timestamp = pd.Timestamp(text)
    except (TypeError, ValueError):
        return NOT_AVAILABLE
    if pd.isna(timestamp):
        return NOT_AVAILABLE
    return timestamp.date().isoformat()


def _clean(value: object) -> str:
    if _is_missing_scalar(value):
        return ""
    text = str(value).strip()
    return "" if text in {"", "None", "nan", "NaT", "<NA>", NOT_AVAILABLE} else text


def _is_missing_scalar(value: object) -> bool:
    if value is None or value is pd.NaT:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    text = str(value).strip()
    return text in {"", "None", "nan", "NaT", "<NA>", NOT_AVAILABLE}
