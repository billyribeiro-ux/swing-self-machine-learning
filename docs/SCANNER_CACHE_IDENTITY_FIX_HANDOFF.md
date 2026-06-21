# Scanner Cache Identity Fix Handoff

## Confirmed P2 Finding

`src/swing_rsi/engine/scanner.py` derived scanner snapshot IDs without including the effective scanner configuration. A snapshot created under looser runtime thresholds could be returned from cache when a later run requested stricter thresholds.

Reproduced behavior before the fix:

- Run 1 with `expected_return_threshold = 0.0` produced `ACTIONABLE_PAPER_CANDIDATE`.
- Run 2 with `expected_return_threshold = 0.03` reused the same scan ID and cached actionable row.

Expected behavior:

- Run 2 gets a different scan identity.
- Run 2 is freshly evaluated.
- The candidate is `REJECTED`.
- The rejection reason is `below_expected_return_threshold`.

## Root Cause

The old scan ID was based on:

- as-of date;
- ordered model IDs;
- model states;
- model eligibility;
- persisted model-policy hashes;
- universe snapshot ID;
- feature snapshot hash.

It omitted behavior-affecting runtime scanner config and per-model effective selection policies. The cache lookup then returned the existing CSV before policy evaluation could run.

## Correction

Created a canonical scan-execution identity in `src/swing_rsi/engine/scanner.py`.

New identity fields include:

- `scanner_identity_schema_version`;
- scanner implementation version;
- market as-of date;
- universe snapshot ID;
- feature-manifest hash;
- feature snapshot hash;
- normalized ordered model IDs;
- model artifact hashes when available;
- model generation IDs when available;
- model states;
- model gate eligibility;
- model state mode;
- include-challengers/include-candidates behavior;
- persisted selection-policy hashes by model;
- per-model effective selection policy after merging persisted policy and runtime `ScannerConfig`;
- normalized behavior-affecting `ScannerConfig`;
- raw scanner config hash;
- effective policy-bundle hash;
- canonical candidate-ordering version and ordering fields.

The scan ID is now derived from that canonical identity using stable sorted JSON. Model input order and feature-row input order are normalized before hashing.

## Cache Reuse Rules

A cached snapshot is reused only if all of these match:

- scan ID;
- identity schema version;
- canonical execution identity;
- scanner-config hash;
- effective policy-bundle hash;
- feature-manifest hash;
- universe snapshot ID;
- model generation IDs;
- model IDs.
- CSV and Parquet snapshot artifacts must both still exist.

If any field is missing or mismatched, the old snapshot remains readable for audit but is not reused. A new immutable snapshot is created with a conflict-derived scan ID rather than overwriting the old row.

## Persisted Metadata

Each new scanner snapshot stores in `scanner_snapshots.metadata_json`:

- raw scanner config JSON;
- raw scanner config hash;
- persisted model-policy hashes;
- effective model-policy JSON;
- effective policy-bundle hash;
- scanner identity schema version;
- scanner implementation version;
- complete canonical scan-execution identity;
- canonical identity JSON;
- final scan ID.

No SQLite schema migration was required.

## Legacy Snapshot Behavior

Legacy snapshots that lack the new identity metadata remain in SQLite and remain readable for audit. They are not eligible for cache reuse by new scanner executions.

Snapshots with mismatched scanner-config hash or effective policy-bundle hash are also not reused.

## Tests Added

Added scanner cache identity regression coverage in `tests/test_autonomous_engine.py` proving:

- loose expected-return threshold followed by stricter threshold produces a different scan ID;
- the stricter run is freshly evaluated;
- the stricter run rejects with `below_expected_return_threshold`;
- target-before-stop, probability, liquidity, global cap, per-date cap, persisted policy hash, generation, feature-manifest, and universe changes affect scan identity;
- exact same identity reuses cache without duplicate snapshot or candidate rows;
- model ordering and input row ordering do not change scan ID or results;
- legacy or mismatched cached metadata is not reused;
- old immutable snapshots remain unchanged;
- new snapshots persist raw config, effective policy, hashes, schema version, canonical identity, and final scan ID;
- scanner actionability still applies the canonical persisted policy evaluator;
- gate-ineligible models still cannot create actionable rows.

All tests use temporary SQLite/output paths and synthetic fixtures. They make no FMP calls.

## Verification Results

- `.venv/bin/pytest tests/test_autonomous_engine.py tests/test_model_evaluation_integrity.py tests/test_dashboard_model_registry.py tests/test_dashboard_interactions.py -q`
  - 57 passed
  - 0 failed
  - 0 skipped
  - 161 warnings

- `.venv/bin/pytest tests/test_autonomous_engine.py -k "scanner or portfolio" -q`
  - 15 passed
  - 13 deselected

- `.venv/bin/pytest tests/test_autonomous_engine.py -k "scanner" -q`
  - 14 passed
  - 14 deselected

- `.venv/bin/pytest tests/test_dashboard_interactions.py tests/test_dashboard_model_registry.py -q`
  - 11 passed

- `.venv/bin/pytest`
  - 115 collected
  - 115 passed
  - 0 failed
  - 0 skipped
  - 161 warnings
  - 56.91s

- `.venv/bin/ruff check .`
  - All checks passed

- `.venv/bin/ruff format --check .`
  - 91 files already formatted

- `.venv/bin/mypy src`
  - Success: no issues found in 53 source files

## Changed Files

- `src/swing_rsi/engine/scanner.py`
- `src/swing_rsi/application/engine_service.py`
- `tests/test_autonomous_engine.py`
- `docs/SCANNER_CACHE_IDENTITY_FIX_HANDOFF.md`

## Commit

Commit message: `fix: include effective scanner config in snapshot identity`

Exact commit hash is reported in the final Codex handoff after the commit is created.

## Remaining Limitations

- Historical scanner snapshots created before schema version 2 remain audit-only for new scanner cache reuse.
- The scanner still reads cached CSV files for exact identity matches, so display-only dtype differences from CSV round-tripping can exist, but candidate status, policy metadata, and cache identity remain deterministic.
- This task did not retrain models, update FMP data, promote models, run forward-update, or run daily-cycle.
