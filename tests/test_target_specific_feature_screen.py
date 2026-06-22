from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from swing_rsi.engine.feature_screen import screen_features_for_target


def _screen(
    frame: pd.DataFrame,
    target: pd.Series,
    *,
    families: dict[str, str] | None = None,
    max_selected: int = 60,
    seed: int = 42,
) -> object:
    return screen_features_for_target(
        frame,
        target,
        target_name=str(target.name or "label_bull_target_before_stop_10"),
        task_type="classification",
        feature_family_by_column=families or {column: "base" for column in frame.columns},
        max_selected_features=max_selected,
        random_seed=seed,
        correlation_threshold=0.97,
    )


def _screen_regression(
    frame: pd.DataFrame,
    target: pd.Series,
    *,
    head_name: str = "expected_return",
    families: dict[str, str] | None = None,
    max_selected: int = 60,
    seed: int = 42,
) -> object:
    return screen_features_for_target(
        frame,
        target,
        target_name=str(target.name or "label_bull_forward_return_10"),
        head_name=head_name,
        direction="bull",
        horizon=10,
        task_type="regression",
        schema_version="path_metric_target_specific_feature_screen_v1",
        feature_family_by_column=families or {column: "base" for column in frame.columns},
        max_selected_features=max_selected,
        random_seed=seed,
        correlation_threshold=0.97,
    )


def _signal_frame(rows: int = 220) -> pd.DataFrame:
    index = np.arange(rows)
    target = (index % 5 < 2).astype(int)
    primary = (index % 7 < 3).astype(int)
    data: dict[str, object] = {
        "Date": pd.date_range("2020-01-01", periods=rows, freq="B"),
        "symbol": ["AAPL"] * rows,
        "label_bull_positive_return_10": primary,
        "label_bull_target_before_stop_10": target,
    }
    for position in range(75):
        data[f"noise_{position:02d}"] = np.sin(index + position)
    data["late_target_signal"] = target + (index % 3) * 0.01
    data["primary_signal"] = primary + (index % 7) * 0.01
    return pd.DataFrame(data)


def _path_metric_frame(rows: int = 220) -> pd.DataFrame:
    index = np.arange(rows)
    expected_return = pd.Series(
        np.sin(index / 7.0) * 0.03,
        name="label_bull_forward_return_10",
    )
    mfe = pd.Series(
        0.04 + (np.cos(index / 5.0) * 0.02),
        name="label_bull_mfe_10",
    )
    mae = pd.Series(
        -0.03 + (np.sin(index / 11.0) * 0.015),
        name="label_bull_mae_10",
    )
    data: dict[str, object] = {
        "Date": pd.date_range("2020-01-01", periods=rows, freq="B"),
        "symbol": ["AAPL"] * rows,
        "label_bull_positive_return_10": (expected_return > 0).astype(int),
        "label_bull_target_before_stop_10": (mfe > 0.045).astype(int),
        "label_bull_forward_return_10": expected_return,
        "label_bull_mfe_10": mfe,
        "label_bull_mae_10": mae,
    }
    for position in range(75):
        data[f"noise_{position:02d}"] = np.random.default_rng(position).normal(size=rows)
    data["late_return_signal"] = expected_return + np.random.default_rng(501).normal(0, 0.001, rows)
    data["late_mfe_signal"] = mfe + np.random.default_rng(502).normal(0, 0.001, rows)
    data["late_mae_signal"] = mae + np.random.default_rng(503).normal(0, 0.001, rows)
    data["positive_return_signal"] = data["label_bull_positive_return_10"]
    data["tbs_signal"] = data["label_bull_target_before_stop_10"]
    return pd.DataFrame(data)


def test_target_before_stop_screen_uses_target_before_stop_not_positive_return() -> None:
    frame = _signal_frame()
    target = frame["label_bull_target_before_stop_10"]
    result = _screen(frame, target, max_selected=5)

    assert result.spec.target_name == "label_bull_target_before_stop_10"
    assert "late_target_signal" in result.selected_features
    assert "primary_signal" not in result.selected_features[:1]


def test_primary_and_target_before_stop_heads_can_select_different_features() -> None:
    frame = _signal_frame()
    target_result = _screen(frame, frame["label_bull_target_before_stop_10"], max_selected=3)
    primary_target = frame["label_bull_positive_return_10"].rename("label_bull_positive_return_10")
    primary_result = _screen(frame, primary_target, max_selected=3)

    assert set(target_result.selected_features) != set(primary_result.selected_features)
    assert "late_target_signal" in target_result.selected_features
    assert "primary_signal" in primary_result.selected_features


@pytest.mark.parametrize(
    ("head", "target_column", "signal"),
    [
        ("expected_return", "label_bull_forward_return_10", "late_return_signal"),
        ("mfe", "label_bull_mfe_10", "late_mfe_signal"),
        ("mae", "label_bull_mae_10", "late_mae_signal"),
    ],
)
def test_path_metric_screen_uses_exact_continuous_target(
    head: str,
    target_column: str,
    signal: str,
) -> None:
    frame = _path_metric_frame()
    result = _screen_regression(
        frame,
        frame[target_column],
        head_name=head,
        max_selected=5,
    )

    assert result.spec.target_name == target_column
    assert result.spec.task_type == "regression"
    assert result.spec.schema_version == "path_metric_target_specific_feature_screen_v1"
    assert result.spec.head_name == head
    assert signal in result.selected_features


def test_path_metric_heads_do_not_screen_against_positive_or_tbs_labels() -> None:
    frame = _path_metric_frame()
    result = _screen_regression(
        frame,
        frame["label_bull_forward_return_10"],
        head_name="expected_return",
        max_selected=3,
    )

    reasons = {record.feature: record.rejection_reason for record in result.records}
    assert "late_return_signal" in result.selected_features
    assert "positive_return_signal" not in result.selected_features[:1]
    assert "tbs_signal" not in result.selected_features[:1]
    assert reasons["label_bull_positive_return_10"] == "label_column_prohibited"
    assert reasons["label_bull_target_before_stop_10"] == "label_column_prohibited"


def test_expected_return_mfe_and_mae_can_select_different_features() -> None:
    frame = _path_metric_frame()
    expected = _screen_regression(
        frame,
        frame["label_bull_forward_return_10"],
        head_name="expected_return",
        max_selected=3,
    )
    mfe = _screen_regression(frame, frame["label_bull_mfe_10"], head_name="mfe", max_selected=3)
    mae = _screen_regression(frame, frame["label_bull_mae_10"], head_name="mae", max_selected=3)

    assert "late_return_signal" in expected.selected_features
    assert "late_mfe_signal" in mfe.selected_features
    assert "late_mae_signal" in mae.selected_features
    assert set(expected.selected_features) != set(mfe.selected_features)
    assert set(mfe.selected_features) != set(mae.selected_features)


def test_every_eligible_feature_is_scored_before_cap_and_late_feature_can_win() -> None:
    frame = _signal_frame()
    result = _screen(frame, frame["label_bull_target_before_stop_10"], max_selected=5)
    scored = [record for record in result.records if record.mutual_information_score is not None]

    assert len(scored) >= 77
    assert "late_target_signal" in result.selected_features
    assert frame.columns.get_loc("late_target_signal") > 60


def test_regression_screen_scores_every_eligible_feature_before_cap() -> None:
    frame = _path_metric_frame()
    result = _screen_regression(
        frame,
        frame["label_bull_forward_return_10"],
        head_name="expected_return",
        max_selected=5,
    )
    scored = [record for record in result.records if record.mutual_information_score is not None]

    assert len(scored) >= 79
    assert "late_return_signal" in result.selected_features
    assert frame.columns.get_loc("late_return_signal") > 60


@pytest.mark.parametrize(
    ("feature", "family"),
    [
        ("relative_return_vs_spy_20", "market_relative"),
        ("relative_return_vs_sector_20", "sector_relative"),
        ("inverse_confirmation_spy_sqqq_63", "inverse_leveraged"),
        ("breadth_advance_pct", "breadth"),
        ("relationship_corr_spy_sqqq_63", "relationship_graph"),
        ("market_regime_trend_score", "regime"),
    ],
)
def test_late_cross_market_family_feature_can_be_selected(feature: str, family: str) -> None:
    rows = 180
    target = pd.Series(
        (np.arange(rows) % 4 == 0).astype(int), name="label_bull_target_before_stop_10"
    )
    data = {f"noise_{i:02d}": np.random.default_rng(i).normal(size=rows) for i in range(70)}
    data[feature] = target.to_numpy(dtype=float)
    frame = pd.DataFrame(data)
    families = {column: "returns_momentum" for column in frame.columns}
    families[feature] = family

    result = _screen(frame, target, families=families, max_selected=3)

    assert feature in result.selected_features
    assert result.selected_feature_families[family] == 1


@pytest.mark.parametrize(
    ("head", "feature", "family"),
    [
        ("expected_return", "relative_return_vs_spy_20", "market_relative"),
        ("mfe", "relative_return_vs_sector_20", "sector_relative"),
        ("mae", "inverse_confirmation_spy_sqqq_63", "inverse_leveraged"),
        ("expected_return", "breadth_advance_pct", "breadth"),
        ("mfe", "relationship_corr_spy_sqqq_63", "relationship_graph"),
        ("mae", "market_regime_trend_score", "regime"),
    ],
)
def test_path_metric_cross_market_family_feature_can_be_selected(
    head: str,
    feature: str,
    family: str,
) -> None:
    rows = 180
    target = pd.Series(
        np.sin(np.arange(rows) / 9.0),
        name={
            "expected_return": "label_bull_forward_return_10",
            "mfe": "label_bull_mfe_10",
            "mae": "label_bull_mae_10",
        }[head],
    )
    data = {f"noise_{i:02d}": np.random.default_rng(i).normal(size=rows) for i in range(70)}
    data[feature] = target.to_numpy(dtype=float)
    frame = pd.DataFrame(data)
    families = {column: "returns_momentum" for column in frame.columns}
    families[feature] = family

    result = _screen_regression(frame, target, head_name=head, families=families, max_selected=3)

    assert feature in result.selected_features
    assert result.selected_feature_families[family] == 1


def test_no_feature_family_is_forced_when_it_has_no_signal() -> None:
    rows = 180
    target = pd.Series((np.arange(rows) % 2).astype(int), name="label_bull_target_before_stop_10")
    frame = pd.DataFrame(
        {
            "signal": target,
            "relationship_noise": np.random.default_rng(11).normal(size=rows),
        }
    )
    families = {"signal": "returns_momentum", "relationship_noise": "relationship_graph"}

    result = _screen(frame, target, families=families, max_selected=1)

    assert result.selected_features == ("signal",)
    assert "relationship_graph" not in result.selected_feature_families


def test_regression_screen_does_not_force_unsignaled_families() -> None:
    rows = 180
    target = pd.Series(
        np.sin(np.arange(rows) / 5.0),
        name="label_bull_forward_return_10",
    )
    frame = pd.DataFrame(
        {
            "signal": target,
            "relationship_noise": np.random.default_rng(11).normal(size=rows),
        }
    )
    families = {"signal": "returns_momentum", "relationship_noise": "relationship_graph"}

    result = _screen_regression(frame, target, families=families, max_selected=1)

    assert result.selected_features == ("signal",)
    assert "relationship_graph" not in result.selected_feature_families


def test_column_order_and_repeated_seed_are_deterministic() -> None:
    frame = _signal_frame()
    target = frame["label_bull_target_before_stop_10"]
    first = _screen(frame, target, max_selected=8, seed=7)
    second = _screen(frame.sample(frac=1.0, axis=1, random_state=1), target, max_selected=8, seed=7)
    third = _screen(frame, target, max_selected=8, seed=7)

    assert first.selected_features == second.selected_features
    assert first.selected_features == third.selected_features
    assert first.selected_feature_manifest_hash == third.selected_feature_manifest_hash


def test_regression_screen_column_order_and_seed_are_deterministic() -> None:
    frame = _path_metric_frame()
    target = frame["label_bull_forward_return_10"]
    first = _screen_regression(frame, target, max_selected=8, seed=7)
    second = _screen_regression(
        frame.sample(frac=1.0, axis=1, random_state=1),
        target,
        max_selected=8,
        seed=7,
    )
    third = _screen_regression(frame, target, max_selected=8, seed=7)

    assert first.selected_features == second.selected_features
    assert first.selected_features == third.selected_features
    assert first.selected_feature_manifest_hash == third.selected_feature_manifest_hash


def test_calibration_holdout_and_future_rows_do_not_affect_train_only_screen() -> None:
    frame = _signal_frame(rows=260)
    train = frame.iloc[:180].copy()
    target = train["label_bull_target_before_stop_10"]
    baseline = _screen(train, target, max_selected=8)
    mutated_full = frame.copy()
    mutated_full.loc[mutated_full.index >= 180, "late_target_signal"] *= -100.0
    mutated_train = mutated_full.iloc[:180].copy()
    rerun = _screen(mutated_train, target, max_selected=8)

    assert baseline.selected_features == rerun.selected_features
    assert baseline.selected_feature_manifest_hash == rerun.selected_feature_manifest_hash


def test_regression_screen_ignores_calibration_holdout_and_future_rows() -> None:
    frame = _path_metric_frame(rows=260)
    train = frame.iloc[:180].copy()
    target = train["label_bull_forward_return_10"]
    baseline = _screen_regression(train, target, max_selected=8)
    mutated_full = frame.copy()
    mutated_full.loc[mutated_full.index >= 180, "late_return_signal"] *= -100.0
    mutated_train = mutated_full.iloc[:180].copy()
    rerun = _screen_regression(mutated_train, target, max_selected=8)

    assert baseline.selected_features == rerun.selected_features
    assert baseline.selected_feature_manifest_hash == rerun.selected_feature_manifest_hash


def test_label_columns_are_rejected_and_holdout_labels_cannot_enter_screening() -> None:
    frame = _signal_frame()
    target = frame["label_bull_target_before_stop_10"]
    result = _screen(frame, target, max_selected=5)
    reasons = {record.feature: record.rejection_reason for record in result.records}

    assert reasons["label_bull_target_before_stop_10"] == "target_column_prohibited"
    assert reasons["label_bull_positive_return_10"] == "label_column_prohibited"
    assert all(not feature.startswith("label_") for feature in result.selected_features)


def test_regression_screen_rejects_all_label_columns() -> None:
    frame = _path_metric_frame()
    target = frame["label_bull_mfe_10"]
    result = _screen_regression(frame, target, head_name="mfe", max_selected=5)
    reasons = {record.feature: record.rejection_reason for record in result.records}

    assert reasons["label_bull_mfe_10"] == "target_column_prohibited"
    assert reasons["label_bull_forward_return_10"] == "label_column_prohibited"
    assert reasons["label_bull_target_before_stop_10"] == "label_column_prohibited"
    assert all(not feature.startswith("label_") for feature in result.selected_features)


def test_missingness_variance_and_imputation_are_training_only() -> None:
    rows = 160
    target = pd.Series((np.arange(rows) % 2).astype(int), name="label_bull_target_before_stop_10")
    frame = pd.DataFrame(
        {
            "signal_with_missing": target.astype(float),
            "too_missing": [np.nan] * 100 + list(range(60)),
            "constant": [1.0] * rows,
        }
    )
    frame.loc[::10, "signal_with_missing"] = np.nan

    result = _screen(frame, target, max_selected=3)
    reasons = {record.feature: record.rejection_reason for record in result.records}

    assert "signal_with_missing" in result.selected_features
    assert reasons["too_missing"] == "missingness_above_threshold"
    assert reasons["constant"] == "near_zero_variance"


def test_regression_missingness_variance_and_imputation_are_training_only() -> None:
    rows = 160
    target = pd.Series(np.sin(np.arange(rows) / 7.0), name="label_bull_forward_return_10")
    frame = pd.DataFrame(
        {
            "signal_with_missing": target.astype(float),
            "too_missing": [np.nan] * 100 + list(range(60)),
            "constant": [1.0] * rows,
        }
    )
    frame.loc[::10, "signal_with_missing"] = np.nan

    result = _screen_regression(frame, target, max_selected=3)
    reasons = {record.feature: record.rejection_reason for record in result.records}

    assert "signal_with_missing" in result.selected_features
    assert reasons["too_missing"] == "missingness_above_threshold"
    assert reasons["constant"] == "near_zero_variance"


def test_correlation_pruning_traverses_score_order_not_dataframe_order() -> None:
    rows = 180
    target = pd.Series(
        (np.arange(rows) % 3 == 0).astype(int), name="label_bull_target_before_stop_10"
    )
    frame = pd.DataFrame(
        {
            "lower_score_duplicate": target + np.random.default_rng(1).normal(0, 0.01, rows),
            "higher_score_exact": target.astype(float),
        }
    )

    result = _screen(frame, target, max_selected=2)
    reasons = {record.feature: record.rejection_reason for record in result.records}

    assert result.selected_features[0] == "higher_score_exact"
    assert reasons["lower_score_duplicate"] == "correlated_with_higher_ranked_feature"


def test_regression_correlation_pruning_traverses_score_order() -> None:
    rows = 180
    target = pd.Series(np.sin(np.arange(rows) / 5.0), name="label_bull_forward_return_10")
    frame = pd.DataFrame(
        {
            "lower_score_duplicate": target + np.random.default_rng(1).normal(0, 0.01, rows),
            "higher_score_exact": target.astype(float),
        }
    )

    result = _screen_regression(frame, target, max_selected=2)
    reasons = {record.feature: record.rejection_reason for record in result.records}

    assert result.selected_features[0] == "higher_score_exact"
    assert reasons["lower_score_duplicate"] == "correlated_with_higher_ranked_feature"


def test_screen_metadata_and_hashes_are_json_serializable() -> None:
    frame = _signal_frame()
    result = _screen(frame, frame["label_bull_target_before_stop_10"], max_selected=5)

    payload = result.metadata()
    json.dumps(payload, sort_keys=True)
    json.dumps(result.audit_records(), sort_keys=True)
    assert payload["screening_schema_version"] == "target_specific_feature_screen_v1"
    assert payload["selected_feature_manifest_hash"] == result.selected_feature_manifest_hash


def test_path_metric_screen_metadata_and_hashes_are_json_serializable() -> None:
    frame = _path_metric_frame()
    result = _screen_regression(
        frame,
        frame["label_bull_mae_10"],
        head_name="mae",
        max_selected=5,
    )

    payload = result.metadata()
    json.dumps(payload, sort_keys=True)
    json.dumps(result.audit_records(), sort_keys=True)
    assert payload["screening_schema_version"] == "path_metric_target_specific_feature_screen_v1"
    assert payload["head_name"] == "mae"
    assert payload["target_label_name"] == "label_bull_mae_10"
    assert payload["selected_feature_manifest_hash"] == result.selected_feature_manifest_hash
