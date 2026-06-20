from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from swing_rsi import __version__
from swing_rsi.application.datasets import DatasetSummary, discover_raw_datasets
from swing_rsi.config import ProjectPaths
from swing_rsi.settings import get_fmp_api_key, get_fmp_base_url, load_project_environment


@dataclass(frozen=True)
class ProjectStatus:
    project_name: str
    package_version: str
    python_version: str
    project_root: Path
    local_env_found: bool
    fmp_configured: bool
    fmp_base_url: str
    raw_ticker_csv_count: int
    saved_report_count: int
    datasets: tuple[DatasetSummary, ...]


def resolve_project_root(start: str | Path | None = None) -> Path:
    current = Path(start).resolve() if start is not None else Path.cwd().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "swing_rsi").exists():
            return candidate
    return current


def sanitize_url(value: str) -> str:
    parsed = urlsplit(value)
    hostname = parsed.hostname or ""
    if parsed.port is not None:
        hostname = f"{hostname}:{parsed.port}"
    return urlunsplit((parsed.scheme, hostname, parsed.path.rstrip("/"), "", ""))


def collect_project_status(root: str | Path | None = None) -> ProjectStatus:
    project_root = resolve_project_root(root)
    env_path = load_project_environment(project_root)
    try:
        get_fmp_api_key(project_root)
    except RuntimeError:
        configured = False
    else:
        configured = True

    paths = ProjectPaths(project_root)
    datasets = discover_raw_datasets(project_root)
    reports = tuple(paths.reports.glob("*.csv")) if paths.reports.exists() else ()
    return ProjectStatus(
        project_name="Self-Learning Swing Trading Engine",
        package_version=__version__,
        python_version=sys.version.split()[0],
        project_root=project_root,
        local_env_found=env_path is not None,
        fmp_configured=configured,
        fmp_base_url=sanitize_url(get_fmp_base_url(project_root)),
        raw_ticker_csv_count=len(datasets),
        saved_report_count=len(reports),
        datasets=datasets,
    )
