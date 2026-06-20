from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame, whole
from swing_rsi.application.engine_service import (
    build_autonomous_features,
    list_registered_models,
    run_model_discovery,
)


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
    streamlit.dataframe(
        display_frame(
            pd.DataFrame(
                [
                    {
                        "model_id": model.model_id,
                        "state": model.state,
                        "direction": model.direction,
                        "horizon": model.horizon,
                        "family": model.family,
                        **model.metrics,
                        **model.calibration_metrics,
                    }
                    for model in models
                ]
            )
        ),
        width="stretch",
        hide_index=True,
    )


if __name__ == "__main__":
    render_page()
