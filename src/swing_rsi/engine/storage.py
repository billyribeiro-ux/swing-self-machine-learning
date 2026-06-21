from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    horizon INTEGER NOT NULL,
    direction TEXT NOT NULL,
    family TEXT NOT NULL,
    state TEXT NOT NULL,
    training_start TEXT,
    training_end TEXT,
    validation_start TEXT,
    validation_end TEXT,
    holdout_start TEXT,
    holdout_end TEXT,
    universe_snapshot_id TEXT NOT NULL,
    feature_manifest_hash TEXT NOT NULL,
    raw_manifest_hashes_json TEXT NOT NULL,
    hyperparameters_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    calibration_metrics_json TEXT NOT NULL,
    quality_gates_json TEXT NOT NULL,
    gate_results_json TEXT NOT NULL DEFAULT '[]',
    artifact_path TEXT NOT NULL,
    code_commit_hash TEXT,
    created_at_utc TEXT NOT NULL,
    promoted_at_utc TEXT,
    retirement_reason TEXT
);

CREATE TABLE IF NOT EXISTS scanner_snapshots (
    scan_id TEXT PRIMARY KEY,
    as_of_date TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    model_ids_json TEXT NOT NULL,
    universe_snapshot_id TEXT NOT NULL,
    feature_snapshot_hash TEXT NOT NULL,
    csv_path TEXT NOT NULL,
    parquet_path TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scanner_candidates (
    scan_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL,
    horizon INTEGER NOT NULL,
    model_id TEXT NOT NULL,
    candidate_status TEXT NOT NULL,
    exclusion_reason TEXT,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (scan_id, ticker, direction, horizon, model_id)
);

CREATE TABLE IF NOT EXISTS forward_events (
    event_id TEXT PRIMARY KEY,
    unique_key TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    market_as_of_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL,
    model_id TEXT NOT NULL,
    scanner_snapshot_id TEXT,
    feature_snapshot_hash TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS final_holdout_runs (
    run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    creation_git_commit TEXT,
    baseline_market_date TEXT NOT NULL,
    first_eligible_future_signal_date TEXT,
    universe_snapshot_id TEXT NOT NULL,
    feature_manifest_hash TEXT NOT NULL,
    generation_id TEXT NOT NULL,
    model_ids_json TEXT NOT NULL,
    scanner_identity_version INTEGER NOT NULL,
    execution_policy_hash TEXT NOT NULL,
    horizon INTEGER NOT NULL,
    direction TEXT NOT NULL,
    status TEXT NOT NULL,
    invalidation_reason TEXT,
    latest_processed_market_date TEXT,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS final_holdout_models (
    run_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    generation_id TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    model_state_at_enrollment TEXT NOT NULL,
    development_gate_eligible INTEGER NOT NULL,
    research_only INTEGER NOT NULL DEFAULT 0,
    selection_policy_hash TEXT NOT NULL,
    calibration_governance_hash TEXT NOT NULL,
    ood_governance_hash TEXT NOT NULL,
    enrollment_blockers_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    PRIMARY KEY (run_id, model_id)
);

CREATE TABLE IF NOT EXISTS daily_cycles (
    market_date TEXT PRIMARY KEY,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    status TEXT NOT NULL,
    summary_json TEXT NOT NULL
);
"""


def _migrate_scanner_candidates_primary_key(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(scanner_candidates)").fetchall()
    primary_key_columns = tuple(
        row["name"] for row in sorted(rows, key=lambda row: row["pk"]) if row["pk"]
    )
    expected = ("scan_id", "ticker", "direction", "horizon", "model_id")
    if primary_key_columns == expected:
        return
    connection.execute("ALTER TABLE scanner_candidates RENAME TO scanner_candidates_old")
    connection.execute(
        """
        CREATE TABLE scanner_candidates (
            scan_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,
            horizon INTEGER NOT NULL,
            model_id TEXT NOT NULL,
            candidate_status TEXT NOT NULL,
            exclusion_reason TEXT,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (scan_id, ticker, direction, horizon, model_id)
        )
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO scanner_candidates (
            scan_id, ticker, direction, horizon, model_id, candidate_status, exclusion_reason, payload_json
        )
        SELECT scan_id, ticker, direction, horizon, model_id, candidate_status, exclusion_reason, payload_json
        FROM scanner_candidates_old
        """
    )
    connection.execute("DROP TABLE scanner_candidates_old")


def _add_missing_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row["name"] for row in rows}
    if column not in existing:
        try:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise


def initialize_engine_db(path: str | Path) -> Path:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        _add_missing_column(
            connection,
            "models",
            "gate_results_json",
            "TEXT NOT NULL DEFAULT '[]'",
        )
        _migrate_scanner_candidates_primary_key(connection)
    return db_path


@contextmanager
def engine_connection(path: str | Path) -> Iterator[sqlite3.Connection]:
    db_path = initialize_engine_db(path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def loads(value: str) -> Any:
    return json.loads(value)
