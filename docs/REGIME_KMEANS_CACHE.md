# Regime KMeans Cache

## Purpose

`expanding_kmeans_regime_cache_v1` accelerates `build-features` by caching the
exact historical output of `_expanding_kmeans_regime(...)`.

This is not a new regime model. It preserves the current one-fit-per-eligible-date
expanding KMeans behavior.

## Cached Feature

The cache stores only:

- `Date`
- `market_regime_cluster_expanding`

It does not cache labels, model predictions, scanner rows, forward events,
final-holdout events, raw data, secrets, `.env`, or authenticated URLs.

## Location

Cache artifacts live under:

```text
data/cache/regime/
```

The path is Git-ignored.

The exact-label cache artifact uses schema:

```text
expanding_kmeans_regime_cache_v1
```

`build-features` also writes a latest-run status sidecar with schema:

```text
expanding_kmeans_regime_cache_status_v1
```

The sidecar records dashboard telemetry such as latest cache status, validity
reason, cached dates reused, new dates computed, KMeans fits avoided/performed,
runtime, and feature manifest hash. It is display metadata only; feature output
does not depend on it.

## Validity Contract

The cache is reused only when all frozen inputs match:

- cache schema version;
- universe snapshot ID;
- covered symbol set;
- date ordering;
- regime input columns;
- KMeans parameters;
- random seed;
- preprocessing policy;
- minimum sample requirement;
- feature-builder version identifier;
- historical input-prefix hash;
- cached output dataframe hash.

If any check fails, the feature builder ignores the cache, recomputes the full
expanding KMeans sequence, and writes a new cache atomically.

## Append Behavior

When the cached historical prefix is valid and the current input has later dates:

1. Cached historical labels are reused.
2. New dates are computed with the same expanding KMeans refit semantics.
3. The cache is rewritten atomically with the appended exact labels.

The new-date fit for date `t` still fits KMeans on all rows available through
`t`, then takes the current-date label. It does not use a stale model and it does
not use future rows.

## Force Rebuild

Use either control to ignore the cache and rewrite it:

```bash
.venv/bin/python -m swing_rsi.cli build-features --rebuild-regime-cache
```

or:

```bash
SWING_RSI_REBUILD_REGIME_CACHE=1 .venv/bin/python -m swing_rsi.cli build-features
```

Forced rebuild is not the default.

## CLI Telemetry

`build-features` prints:

- regime cache status: `HIT`, `MISS`, `PARTIAL_APPEND`, or `INVALIDATED`;
- cached dates reused;
- new dates computed;
- KMeans fits avoided;
- KMeans fits performed;
- regime runtime;
- estimated speedup.

The same latest-run cache telemetry is displayed in the Streamlit dashboard:

- Signal Board shows compact status cards.
- Developer Diagnostics shows detailed metadata, input columns, KMeans config,
  and CSV/XLSX exports.

The dashboard reads local cache metadata only. It does not run `build-features`
or recompute regime features on page load.

## Atomic Writes

Cache writes use a temporary file in the target cache directory and `os.replace`.
If the write fails, the previous valid cache remains in place and the current
feature output still comes from the recomputed or appended exact labels.

## Scope Guardrails

The cache does not change:

- regime input columns;
- KMeans refit cadence;
- KMeans cluster count;
- random seed;
- preprocessing;
- feature definitions;
- labels;
- thresholds;
- model artifacts;
- scanner state;
- forward state;
- final-holdout state.
