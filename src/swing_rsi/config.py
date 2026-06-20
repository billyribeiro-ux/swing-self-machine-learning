from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def raw_data(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def processed_data(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def feature_data(self) -> Path:
        return self.root / "data" / "features"

    @property
    def universe_data(self) -> Path:
        return self.root / "data" / "universes"

    @property
    def manifests(self) -> Path:
        return self.root / "data" / "manifests"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def forward_tests(self) -> Path:
        return self.root / "data" / "forward_tests"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def model_artifacts(self) -> Path:
        return self.artifacts / "models"

    @property
    def explainability_artifacts(self) -> Path:
        return self.artifacts / "explainability"

    @property
    def registry_artifacts(self) -> Path:
        return self.artifacts / "registry"

    @property
    def scanner_artifacts(self) -> Path:
        return self.artifacts / "scanner"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def engine_db(self) -> Path:
        return self.state / "engine.sqlite3"

    def ensure(self) -> None:
        for path in (
            self.raw_data,
            self.processed_data,
            self.feature_data,
            self.universe_data,
            self.manifests,
            self.reports,
            self.forward_tests,
            self.model_artifacts,
            self.explainability_artifacts,
            self.registry_artifacts,
            self.scanner_artifacts,
            self.state,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected a YAML mapping in {config_path}")
    return loaded
