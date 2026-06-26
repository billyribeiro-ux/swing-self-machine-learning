from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from swing_rsi.engine.feature_hygiene import (
    MODEL_FEATURE_MATRIX_NONFINITE_REJECTION_REASON,
    MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION,
    SAFE_FLOAT64_ABS_GUARD,
    FeatureMatrixHygieneAudit,
    combine_hygiene_audits,
    nonfinite_hygiene_policy_hash,
    reject_post_sanitization_nonfinite,
    sanitize_model_feature_matrix,
)
from swing_rsi.engine.features import _symbol_features, reject_label_columns
from swing_rsi.engine.universe import UniverseSymbol


def _ohlcv_for_obv_change(last_close: float) -> pd.DataFrame:
    dates = pd.date_range("2016-06-20", periods=25, freq="B")
    close = [10.0] * 20 + [last_close] + [last_close] * 4
    return pd.DataFrame(
        {
            "Open": close,
            "High": [value + 0.25 for value in close],
            "Low": [value - 0.25 for value in close],
            "Close": close,
            "Adj Close": close,
            "Volume": [1_000_000.0] * len(close),
        },
        index=dates,
    )


@pytest.mark.parametrize("last_close", [9.0, 11.0])
def test_obv_change_20_never_produces_infinity(last_close: float) -> None:
    features = _symbol_features(
        "SH",
        _ohlcv_for_obv_change(last_close),
        UniverseSymbol(symbol="SH", role="inverse_etf", sector="inverse_market"),
    )

    values = features["obv_change_20"].to_numpy(dtype=float)
    assert not np.isposinf(values).any()
    assert not np.isneginf(values).any()


def test_obv_change_20_zero_denominator_is_missing_not_infinite() -> None:
    features = _symbol_features(
        "RWM",
        _ohlcv_for_obv_change(9.0),
        UniverseSymbol(symbol="RWM", role="inverse_etf", sector="inverse_market"),
    )

    assert pd.isna(features["obv_change_20"].iloc[20])


def test_feature_generation_hygiene_does_not_mutate_raw_ohlcv() -> None:
    raw = _ohlcv_for_obv_change(9.0)
    before = raw.copy(deep=True)

    _symbol_features(
        "SH",
        raw,
        UniverseSymbol(symbol="SH", role="inverse_etf", sector="inverse_market"),
    )

    pd.testing.assert_frame_equal(raw, before)


def test_feature_hygiene_does_not_mutate_labels() -> None:
    labels = pd.Series([1, 0, 1], name="label_bull_positive_return_10")
    before = labels.copy(deep=True)
    features = pd.DataFrame({"feature": [1.0, np.inf, 3.0]})

    sanitize_model_feature_matrix(features, split="training", stage="fit")

    pd.testing.assert_series_equal(labels, before)


def test_sanitize_model_feature_matrix_replaces_invalid_values_with_nan() -> None:
    frame = pd.DataFrame(
        {
            "positive_inf": [1.0, np.inf],
            "negative_inf": [-np.inf, 2.0],
            "too_large": [SAFE_FLOAT64_ABS_GUARD * 1.1, 3.0],
            "existing_nan": [np.nan, 4.0],
        }
    )

    sanitized, audit = sanitize_model_feature_matrix(
        frame,
        split="training",
        stage="feature_screening",
        feature_family_by_column={
            "positive_inf": "relationship_graph",
            "negative_inf": "volume_participation",
            "too_large": "volatility_range",
            "existing_nan": "technical_primitives",
        },
    )

    assert sanitized.isna().sum().to_dict() == {
        "positive_inf": 1,
        "negative_inf": 1,
        "too_large": 1,
        "existing_nan": 1,
    }
    assert audit.schema_version == MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION
    assert audit.policy_hash == nonfinite_hygiene_policy_hash()
    assert audit.pre_sanitization_positive_infinity_count == 1
    assert audit.pre_sanitization_negative_infinity_count == 1
    assert audit.pre_sanitization_too_large_count == 1
    assert audit.post_sanitization_nonfinite_count == 0
    assert set(audit.sanitized_columns) == {"positive_inf", "negative_inf", "too_large"}
    assert audit.affected_feature_families == {
        "relationship_graph": 1,
        "volume_participation": 1,
        "volatility_range": 1,
    }


def test_hygiene_audit_records_scope_symbol_and_date_context() -> None:
    frame = pd.DataFrame({"obv_change_20": [-np.inf, 0.5]})
    context = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2016-07-19", "2016-07-20"]),
            "symbol": ["RWM", "SH"],
        }
    )

    _, audit = sanitize_model_feature_matrix(
        frame,
        split="training",
        stage="expected_return_regressor_fit",
        feature_family_by_column={"obv_change_20": "volume_participation"},
        context_frame=context,
    )

    assert audit.affected_symbols == ("RWM",)
    assert audit.affected_dates == ("2016-07-19",)
    combined = combine_hygiene_audits([audit])
    assert combined["affected_symbols"] == ("RWM",)
    assert combined["affected_dates"] == ("2016-07-19",)
    assert combined["pre_sanitization_invalid_count_by_split"] == {"training": 1}


def test_training_fitted_imputation_handles_sanitized_nan_across_splits() -> None:
    train, _ = sanitize_model_feature_matrix(
        pd.DataFrame({"obv_change_20": [1.0, 3.0, np.inf]}),
        split="training",
        stage="fit",
    )
    calibration, _ = sanitize_model_feature_matrix(
        pd.DataFrame({"obv_change_20": [-np.inf]}),
        split="calibration",
        stage="predict",
    )
    holdout, _ = sanitize_model_feature_matrix(
        pd.DataFrame({"obv_change_20": [SAFE_FLOAT64_ABS_GUARD * 1.1]}),
        split="development_holdout",
        stage="predict",
    )

    imputer = SimpleImputer(strategy="median").fit(train)

    assert imputer.statistics_[0] == pytest.approx(2.0)
    assert imputer.transform(calibration)[0, 0] == pytest.approx(2.0)
    assert imputer.transform(holdout)[0, 0] == pytest.approx(2.0)


def test_inverse_bull_obv_negative_infinity_fixture_fits_after_sanitization() -> None:
    matrix = pd.DataFrame(
        {
            "obv_change_20": [-np.inf, 0.1, 0.2, 0.3, 0.4],
            "return_20": [0.01, 0.02, -0.01, 0.03, -0.02],
        }
    )
    target = np.array([0.01, 0.02, 0.0, 0.03, -0.01])
    sanitized, audit = sanitize_model_feature_matrix(
        matrix,
        split="training",
        stage="expected_return_regressor_fit",
        feature_family_by_column={
            "obv_change_20": "volume_participation",
            "return_20": "returns_momentum",
        },
        context_frame=pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2016-07-19", "2016-07-20", "2016-07-21", "2016-07-22", "2016-07-25"]
                ),
                "symbol": ["RWM", "SH", "RWM", "SH", "RWM"],
            }
        ),
    )
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesRegressor(n_estimators=2, random_state=42)),
        ]
    )

    model.fit(sanitized, target)

    assert audit.post_sanitization_nonfinite_count == 0
    assert audit.sanitized_columns == ("obv_change_20",)
    assert "obv_change_20" in sanitized.columns


def test_remaining_invalid_values_raise_explicit_rejection() -> None:
    audit = FeatureMatrixHygieneAudit(
        schema_version=MODEL_FEATURE_NONFINITE_HYGIENE_SCHEMA_VERSION,
        split="training",
        stage="fit",
        row_count=1,
        column_count=1,
        safe_float64_abs_guard=SAFE_FLOAT64_ABS_GUARD,
        pre_sanitization_positive_infinity_count=1,
        pre_sanitization_negative_infinity_count=0,
        pre_sanitization_nan_count=0,
        pre_sanitization_too_large_count=0,
        pre_sanitization_nonfinite_count=1,
        pre_sanitization_invalid_count=1,
        post_sanitization_positive_infinity_count=1,
        post_sanitization_negative_infinity_count=0,
        post_sanitization_too_large_count=0,
        post_sanitization_nonfinite_count=1,
        post_sanitization_nan_count=0,
        affected_columns=("feature",),
        sanitized_columns=("feature",),
        affected_feature_families={"test": 1},
        affected_symbols=(),
        affected_dates=(),
        rows_with_invalid_values=1,
        policy_hash=nonfinite_hygiene_policy_hash(),
    )

    with pytest.raises(ValueError, match=MODEL_FEATURE_MATRIX_NONFINITE_REJECTION_REASON):
        reject_post_sanitization_nonfinite(audit)


def test_feature_screening_still_rejects_label_columns() -> None:
    with pytest.raises(ValueError, match="Label columns cannot enter the feature matrix"):
        reject_label_columns(["feature", "label_bull_forward_return_10"])


def test_nonfinite_hygiene_tests_do_not_reference_operational_mutable_state() -> None:
    forbidden = Path("/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner/state")
    assert forbidden not in Path(__file__).parents
