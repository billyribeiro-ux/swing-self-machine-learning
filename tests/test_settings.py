from __future__ import annotations

from pathlib import Path

import pytest

from swing_rsi.settings import get_fmp_api_key, load_project_environment


def test_load_project_environment_reads_local_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    (tmp_path / ".env").write_text("FMP_API_KEY=local-test-key\n", encoding="utf-8")

    loaded = load_project_environment(tmp_path)

    assert loaded == tmp_path / ".env"
    assert get_fmp_api_key(tmp_path) == "local-test-key"


def test_get_fmp_api_key_requires_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="configure_fmp"):
        get_fmp_api_key(tmp_path)
