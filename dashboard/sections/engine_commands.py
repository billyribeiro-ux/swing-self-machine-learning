from __future__ import annotations

from dashboard.ui.components import render_page_header, repository_root, st
from swing_rsi.application.dashboard_service import (
    command_specs,
    fmp_key_configured,
    run_dashboard_command,
)


def render_page() -> None:
    streamlit = st()
    root = repository_root()
    render_page_header(
        "Engine Commands",
        "Confirmed local development commands with captured output and dashboard command logs.",
    )
    streamlit.warning(
        "Commands run from the development worktree only. Secrets are redacted from captured output."
    )
    configured = fmp_key_configured(root)
    specs = command_specs(fmp_configured=configured)
    selected = streamlit.selectbox("Allowed command", specs, format_func=lambda spec: spec.label)
    streamlit.code(selected.command_text, language="bash")
    streamlit.write(f"Mutates development state: {'yes' if selected.mutates else 'no'}")
    confirmed = streamlit.checkbox("I confirm I want to run this development command.")
    if streamlit.button("Run selected command", disabled=not confirmed):
        try:
            result = run_dashboard_command(root, selected)
        except ValueError as exc:
            streamlit.error(str(exc))
        else:
            if result.return_code == 0:
                streamlit.success(f"Command completed. Log: {result.log_path.relative_to(root)}")
            else:
                streamlit.error(
                    f"Command exited with {result.return_code}. Log: "
                    f"{result.log_path.relative_to(root)}"
                )
            streamlit.subheader("stdout")
            streamlit.code(result.stdout or "", language="text")
            streamlit.subheader("stderr")
            streamlit.code(result.stderr or "", language="text")

    streamlit.subheader("Disabled Commands")
    streamlit.button(
        "discover-models disabled",
        disabled=True,
        help="Dashboard V1 must not run discovery.",
    )
    streamlit.button(
        "promote-model disabled",
        disabled=True,
        help="Dashboard V1 must not promote models.",
    )
    if not configured:
        streamlit.info("FMP key configured: no. The universe-update command is disabled.")


if __name__ == "__main__":
    render_page()
