from __future__ import annotations

import pandas as pd

from dashboard.ui.components import render_page_header, repository_root, st
from dashboard.ui.formatting import display_frame
from swing_rsi.application.engine_service import list_registered_models, promote_registered_model


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Model Registry", "Champion, challenger, candidate, rejected, and retired model versions."
    )
    models = list_registered_models(root)
    if not models:
        streamlit.info("No model registry entries yet.")
        return
    rows = pd.DataFrame(
        [
            {
                "model_id": model.model_id,
                "state": model.state,
                "direction": model.direction,
                "horizon": model.horizon,
                "family": model.family,
                "created_at_utc": model.created_at_utc,
                "promoted_at_utc": model.promoted_at_utc,
                **model.metrics,
                **model.calibration_metrics,
            }
            for model in models
        ]
    )
    streamlit.dataframe(display_frame(rows), width="stretch", hide_index=True)
    challengers = [model.model_id for model in models if model.state in {"CHALLENGER", "CANDIDATE"}]
    if challengers:
        with streamlit.form("promote_model_form"):
            selected = streamlit.selectbox("Model to promote", options=challengers)
            submitted = streamlit.form_submit_button("Promote model")
        if submitted:
            try:
                promoted = promote_registered_model(root, str(selected))
            except ValueError as exc:
                streamlit.error(str(exc))
            else:
                streamlit.success(f"Promoted champion: {promoted.model_id}")
