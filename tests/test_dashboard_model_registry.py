from __future__ import annotations

from dashboard.sections.model_registry import (
    _compact_direction,
    _compact_family,
    _compact_state,
    _short_identifier,
    compact_registry_rows,
)

from swing_rsi.engine.registry import RegisteredModel


def _model() -> RegisteredModel:
    return RegisteredModel(
        model_id="1234567890abcdef12345678",
        task="probability_positive_return",
        horizon=10,
        direction="bull",
        family="hist_gradient_boosting",
        state="CANDIDATE",
        training_start="2020-01-01",
        training_end="2021-01-01",
        validation_start="2021-01-04",
        validation_end="2021-06-01",
        holdout_start="2021-06-02",
        holdout_end="2022-01-01",
        universe_snapshot_id="universe-snapshot-hash",
        feature_manifest_hash="feature-manifest-hash",
        raw_manifest_hashes=(),
        hyperparameters={},
        metrics={
            "training_samples": 1200,
            "holdout_samples": 300,
            "selected_holdout_samples": 42,
            "holdout_win_rate": 0.571,
            "holdout_mean_return_lcb_90": -0.0123,
            "holdout_profit_factor": 1.234,
            "holdout_max_drawdown": -0.0876,
            "portfolio_max_drawdown": -0.0876,
            "selected_observation_rate": 0.14,
        },
        calibration_metrics={"holdout_brier": 0.2174, "brier_skill_score": 0.0123},
        quality_gates={"minimum_training_samples": True, "profit_factor_min_090": False},
        artifact_path="artifacts/models/model.joblib",
        code_commit_hash="abcdef",
        created_at_utc="2026-06-20T12:34:56+00:00",
    )


def test_registry_compact_labels_are_short_and_readable() -> None:
    assert _short_identifier("1234567890abcdef") == "12345678..."
    assert _compact_state("CANDIDATE") == "CAND"
    assert _compact_direction("bull") == "Bull"
    assert _compact_family("hist_gradient_boosting") == "HGB"


def test_compact_registry_rows_fit_default_dashboard_table() -> None:
    rows = compact_registry_rows([_model()])

    assert rows.columns.tolist() == [
        "ID",
        "State",
        "Dir",
        "Hz",
        "Family",
        "Created",
        "Train",
        "Holdout",
        "Sel",
        "Sel%",
        "Win",
        "EV LCB",
        "PF",
        "Port DD",
        "Brier",
        "BSS",
        "Fail",
        "NCfg",
        "Elig",
    ]
    item = rows.iloc[0].to_dict()
    assert item["ID"] == "12345678..."
    assert item["State"] == "CAND"
    assert item["Dir"] == "Bull"
    assert item["Family"] == "HGB"
    assert item["Created"] == "2026-06-20"
    assert item["Win"] == "57.1%"
    assert item["EV LCB"] == "-1.2%"
    assert item["PF"] == "1.23"
    assert item["Sel%"] == "14.0%"
    assert item["Port DD"] == "-8.8%"
    assert item["Brier"] == "0.217"
    assert item["BSS"] == "0.012"
    assert item["Elig"] == "N"
