from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame, whole
from swing_rsi.application.engine_service import (
    build_autonomous_features,
    list_registered_models,
    run_model_discovery,
)
from swing_rsi.engine.gates import promotion_eligibility


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Discovery Lab", "Build features, create labels, train candidates, and review gates."
    )

    with streamlit.form("feature_build_form"):
        build_clicked = streamlit.form_submit_button("Build feature and label tables")
    if build_clicked:
        try:
            result = build_autonomous_features(root)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            streamlit.error(f"Feature build failed: {exc}")
        else:
            streamlit.success("Feature and label tables built.")
            streamlit.write(f"Feature rows: {whole(len(result.features.frame))}")
            streamlit.write(f"Modeling rows: {whole(len(result.modeling_frame))}")
            streamlit.write(f"Feature manifest: `{result.features.manifest_hash}`")

    with streamlit.form("discovery_form"):
        minimum_training = streamlit.number_input(
            "Minimum training samples", min_value=20, value=200
        )
        minimum_holdout = streamlit.number_input("Minimum holdout samples", min_value=20, value=80)
        discover_clicked = streamlit.form_submit_button("Discover models")
    if discover_clicked:
        try:
            models = run_model_discovery(
                root,
                minimum_training_samples=int(minimum_training),
                minimum_holdout_samples=int(minimum_holdout),
            )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            streamlit.error(f"Discovery failed: {exc}")
        else:
            streamlit.success(f"Registered {len(models):,} candidate records.")

    models = list_registered_models(root)
    streamlit.subheader("Candidate Models")
    if not models:
        streamlit.info("No model registry entries yet.")
        return
    rows: list[dict[str, object]] = []
    for model in models:
        eligibility = promotion_eligibility(model.gate_results)
        rows.append(
            {
                "model_id": model.model_id,
                "state": model.state,
                "direction": model.direction,
                "horizon": model.horizon,
                "family": model.family,
                "research_start": model.metrics.get("research_start"),
                "research_end": model.metrics.get("research_end"),
                "holdout_samples": model.metrics.get("holdout_samples"),
                "selected_samples": model.metrics.get("selected_holdout_samples"),
                "selected_rate": model.metrics.get("selected_observation_rate"),
                "model_brier": model.calibration_metrics.get("holdout_brier"),
                "naive_brier": model.calibration_metrics.get("naive_brier"),
                "brier_skill_score": model.calibration_metrics.get("brier_skill_score"),
                "mean_selected_return": model.metrics.get("holdout_mean_net_return"),
                "lower_confidence_bound": model.metrics.get("holdout_mean_return_lcb_90"),
                "profit_factor": model.metrics.get("holdout_profit_factor"),
                "portfolio_max_drawdown": model.metrics.get("portfolio_max_drawdown"),
                "selected_row_sequence_drawdown": model.metrics.get(
                    "selected_row_sequence_drawdown"
                ),
                "temporal_fold_evidence_status": model.metrics.get("temporal_fold_evidence_status"),
                "temporal_fold_folds_requested": model.metrics.get("temporal_fold_folds_requested"),
                "temporal_fold_folds_evaluated": model.metrics.get("temporal_fold_folds_evaluated"),
                "temporal_fold_folds_with_selected_observations": model.metrics.get(
                    "temporal_fold_folds_with_selected_observations"
                ),
                "temporal_fold_selected_observations_per_fold": model.metrics.get(
                    "temporal_fold_selected_observations_per_fold_json"
                ),
                "temporal_fold_positive_fraction": model.metrics.get(
                    "temporal_fold_positive_fraction"
                ),
                "temporal_fold_threshold": model.metrics.get("temporal_fold_threshold"),
                "temporal_fold_evidence_gate_status": model.metrics.get(
                    "temporal_fold_evidence_gate_status"
                ),
                "temporal_fold_threshold_gate_status": model.metrics.get(
                    "temporal_fold_threshold_gate_status"
                ),
                "temporal_fold_evidence_unavailable_reason": model.metrics.get(
                    "temporal_fold_evidence_unavailable_reason"
                ),
                "ood_governance": model.metrics.get("prediction_ood_governance_version"),
                "prediction_ood_total": model.metrics.get("prediction_sanity_ood_total"),
                "prediction_values_finite": model.metrics.get("prediction_values_finite"),
                "probability_contract_valid": model.metrics.get(
                    "prediction_probability_contract_valid"
                ),
                "mandatory_gates_failed": eligibility.mandatory_failed,
                "mandatory_gates_not_configured": eligibility.not_configured,
                "promotion_eligible": eligibility.eligible,
            }
        )
    streamlit.dataframe(
        display_frame(pd.DataFrame(rows)),
        width="stretch",
        hide_index=True,
    )


if __name__ == "__main__":
    render_page()
