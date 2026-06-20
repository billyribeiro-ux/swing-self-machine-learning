from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class DataManifest:
    provider: str
    symbol: str
    retrieval_timestamp_utc: str
    requested_start: str | None
    requested_end: str | None
    actual_first_date: str | None
    actual_last_date: str | None
    row_count: int
    raw_file_hash: str
    corporate_action_semantics_status: str
    missing_data_status: str
    stale_data_status: str
    code_commit_hash: str | None


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_commit_hash(root: str | Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def stale_status(last_date: str | None, *, today: date | None = None) -> str:
    if last_date is None:
        return "unknown_no_rows"
    current = today or datetime.now(UTC).date()
    age = (current - pd.Timestamp(last_date).date()).days
    if age <= 3:
        return "fresh_within_3_calendar_days"
    if age <= 10:
        return f"stale_{age}_calendar_days"
    return f"stale_gt_10_calendar_days_{age}"


def missing_data_status(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "empty"
    if frame.index.has_duplicates:
        return "duplicate_dates_detected"
    required = ["Open", "High", "Low", "Close", "Volume"]
    if frame[required].isna().any().any():
        return "missing_required_values"
    return "structural_ohlcv_checks_passed_calendar_completeness_not_audited"


def create_manifest(
    *,
    provider: str,
    symbol: str,
    requested_start: str | None,
    requested_end: str | None,
    raw_path: Path,
    frame: pd.DataFrame,
    root: str | Path,
) -> DataManifest:
    first = frame.index.min().date().isoformat() if not frame.empty else None
    last = frame.index.max().date().isoformat() if not frame.empty else None
    return DataManifest(
        provider=provider,
        symbol=symbol,
        retrieval_timestamp_utc=datetime.now(UTC).isoformat(),
        requested_start=requested_start,
        requested_end=requested_end,
        actual_first_date=first,
        actual_last_date=last,
        row_count=len(frame),
        raw_file_hash=hash_file(raw_path),
        corporate_action_semantics_status="unaudited_fmp_semantics",
        missing_data_status=missing_data_status(frame),
        stale_data_status=stale_status(last),
        code_commit_hash=current_commit_hash(root),
    )


def write_manifest(manifest: DataManifest, directory: str | Path) -> Path:
    output = Path(directory) / f"{manifest.symbol}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True), encoding="utf-8")
    return output
