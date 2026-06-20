from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from swing_rsi.engine.models import ModelBundle, predict_bundle


@dataclass(frozen=True)
class AttributionResult:
    contribution_share: dict[str, float]
    supporting_evidence: tuple[str, ...]
    relationship_confirmations: tuple[str, ...]
    relationship_divergences: tuple[str, ...]
    analogs: pd.DataFrame


def local_contribution_share(bundle: ModelBundle, row: pd.Series) -> dict[str, float]:
    base_frame = pd.DataFrame(
        [{column: row.get(column, np.nan) for column in bundle.feature_columns}]
    )
    base_frame.insert(0, "symbol", row.get("symbol", "UNKNOWN"))
    base_frame.insert(0, "Date", row.get("Date"))
    base_probability = float(predict_bundle(bundle, base_frame)["calibrated_probability"].iloc[0])

    deltas: dict[str, float] = {}
    families = sorted(set(bundle.feature_family_by_column.values()))
    for family in families:
        columns = [
            column
            for column, mapped_family in bundle.feature_family_by_column.items()
            if mapped_family == family and column in bundle.feature_columns
        ]
        if not columns:
            continue
        perturbed = base_frame.copy()
        for column in columns:
            perturbed[column] = bundle.training_medians.get(column, 0.0)
        probability = float(predict_bundle(bundle, perturbed)["calibrated_probability"].iloc[0])
        deltas[family] = abs(base_probability - probability)

    total = sum(deltas.values())
    if total <= 0:
        return {"residual/unexplained": 1.0}
    shares = {family: 0.9 * value / total for family, value in sorted(deltas.items()) if value > 0}
    shares["residual/unexplained"] = 1.0 - sum(shares.values())
    return shares


def supporting_evidence(bundle: ModelBundle, row: pd.Series, *, limit: int = 8) -> tuple[str, ...]:
    scored: list[tuple[float, str]] = []
    for column in bundle.feature_columns:
        value = row.get(column)
        if pd.isna(value):
            continue
        mean = bundle.training_means.get(column, 0.0)
        std = bundle.training_stds.get(column, 1.0)
        zscore = abs((float(value) - mean) / std)
        family = bundle.feature_family_by_column.get(column, "unknown")
        scored.append((zscore, f"{family}: {column}={float(value):.4f}"))
    return tuple(text for _, text in sorted(scored, reverse=True)[:limit])


def relationship_evidence(row: pd.Series) -> tuple[tuple[str, ...], tuple[str, ...]]:
    confirmations: list[str] = []
    divergences: list[str] = []
    for column, value in row.items():
        name = str(column)
        if not name.startswith("relationship_") or pd.isna(value):
            continue
        numeric = float(value)
        if "corr" in name and abs(numeric) >= 0.5:
            confirmations.append(f"{name} stable at {numeric:.2f}")
        elif "divergence" in name and abs(numeric) >= 0.03:
            divergences.append(f"{name} abnormal at {numeric:.2%}")
        elif "lead_lag" in name and abs(numeric) >= 0.4:
            confirmations.append(f"{name} lead-lag relation at {numeric:.2f}")
    return tuple(confirmations[:5]), tuple(divergences[:5])


def historical_analogs(
    bundle: ModelBundle,
    row: pd.Series,
    *,
    as_of_date: pd.Timestamp,
    limit: int = 5,
) -> pd.DataFrame:
    if bundle.training_matrix.empty:
        return pd.DataFrame()
    current = np.asarray(
        [
            (
                float(row.get(column, bundle.training_medians.get(column, 0.0)))
                - bundle.training_means.get(column, 0.0)
            )
            / bundle.training_stds.get(column, 1.0)
            for column in bundle.feature_columns
        ],
        dtype=float,
    )
    train = bundle.training_matrix[list(bundle.feature_columns)].copy()
    normalized = np.vstack(
        [
            (
                train[column].fillna(bundle.training_medians.get(column, 0.0)).to_numpy(dtype=float)
                - bundle.training_means.get(column, 0.0)
            )
            / bundle.training_stds.get(column, 1.0)
            for column in bundle.feature_columns
        ]
    ).T
    distances = np.linalg.norm(normalized - current, axis=1)
    labels = bundle.training_labels.copy()
    labels["distance"] = distances
    labels = labels[pd.to_datetime(labels["Date"]) < as_of_date]
    if labels.empty:
        return pd.DataFrame()
    return labels.sort_values("distance").head(limit).reset_index(drop=True)


def explain_candidate(bundle: ModelBundle, row: pd.Series) -> AttributionResult:
    as_of_date = pd.Timestamp(row["Date"])
    confirmations, divergences = relationship_evidence(row)
    return AttributionResult(
        contribution_share=local_contribution_share(bundle, row),
        supporting_evidence=supporting_evidence(bundle, row),
        relationship_confirmations=confirmations,
        relationship_divergences=divergences,
        analogs=historical_analogs(bundle, row, as_of_date=as_of_date),
    )
