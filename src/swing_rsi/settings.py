from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_FMP_BASE_URL = "https://financialmodelingprep.com/stable"


def load_project_environment(root: str | Path | None = None) -> Path | None:
    """Load the nearest project .env without overwriting existing environment values."""
    search_root = Path(root) if root is not None else Path.cwd()
    env_path = search_root / ".env"
    if not env_path.exists():
        return None
    load_dotenv(dotenv_path=env_path, override=False)
    return env_path


def get_fmp_api_key(root: str | Path | None = None) -> str:
    """Return the configured FMP key without ever logging or embedding it."""
    load_project_environment(root)
    api_key = os.getenv("FMP_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "FMP_API_KEY is not configured. Run ./scripts/configure_fmp.sh from the project root."
        )
    return api_key


def get_fmp_base_url(root: str | Path | None = None) -> str:
    load_project_environment(root)
    return os.getenv("FMP_BASE_URL", DEFAULT_FMP_BASE_URL).strip().rstrip("/")
