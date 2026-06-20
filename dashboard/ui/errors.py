from __future__ import annotations

import logging
from pathlib import Path

from dashboard.ui.components import repository_root, st


def _logger() -> logging.Logger:
    root = repository_root()
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("swing_rsi.dashboard")
    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "dashboard.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def show_expected_error(message: str) -> None:
    st().error(message)


def show_unexpected_error(exc: Exception, *, context: str) -> None:
    _logger().exception("Unexpected dashboard error in %s: %s", context, type(exc).__name__)
    st().error(
        "Unexpected dashboard error. Details were written to logs/dashboard.log without "
        "credentials or request payloads."
    )


def safe_path(path: str | Path) -> str:
    return str(Path(path))
