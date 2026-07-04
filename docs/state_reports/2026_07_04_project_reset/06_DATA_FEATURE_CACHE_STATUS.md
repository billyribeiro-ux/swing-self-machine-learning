# Data Feature Cache Status

## Development Repo

Path:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

- enabled core symbol count: 35
- latest common completed local session: `2026-07-02`
- latest raw date by symbol: all enabled symbols are `2026-07-02`
- stale symbols: none
- feature rows: 90,288
- label rows: 90,288
- modeling rows: 90,288
- feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- feature parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet`
- labels parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_labels.parquet`
- modeling parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`
- positive infinity count in features: 35
- negative infinity count in features: 0

Development raw dates:

```text
AAPL, AMD, AMZN, DIA, GOOGL, IWM, META, MSFT, NVDA, QID, QQQ, RWM, SDS, SH,
SOXL, SOXS, SPXU, SPY, SQQQ, TNA, TQQQ, TSLA, TZA, UPRO, XLB, XLC, XLE,
XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY: 2026-07-02
```

Development regime cache:

- status: `HIT`
- validity: `VALID`
- reason: `cache_valid`
- last cached date: `2026-07-02`
- row count / dates covered: 5,009
- cached dates reused: 5,009
- new dates computed: 0
- KMeans fits avoided: 2,522
- KMeans fits performed: 0
- regime runtime: about 2.60 seconds
- cache status path: `data/cache/regime/6b1a74750684506e1a5b_expanding_kmeans_regime_cache_status_v1.json`

Development data is current through `2026-07-02`.

## Operational Repo

Path:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner`

- enabled core symbol count: 35
- latest common completed local session: `2026-07-02`
- latest raw date by symbol: all enabled symbols are `2026-07-02`
- stale symbols: none
- feature rows: 90,288
- label rows: 90,288
- modeling rows: 90,288
- feature manifest hash: `3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5`
- feature parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_features.parquet`
- labels parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_labels.parquet`
- modeling parquet path: `data/features/6b1a74750684506e1a5b_3007abe80b54d40c87566bc9185a3086098c91b95d156c664ced290242090ae5_modeling.parquet`
- positive infinity count in features: 70
- negative infinity count in features: 29

Operational raw dates:

```text
AAPL, AMD, AMZN, DIA, GOOGL, IWM, META, MSFT, NVDA, QID, QQQ, RWM, SDS, SH,
SOXL, SOXS, SPXU, SPY, SQQQ, TNA, TQQQ, TSLA, TZA, UPRO, XLB, XLC, XLE,
XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY: 2026-07-02
```

Operational regime cache:

- status artifact: not present in `data/cache` in the operational repo
- regime cache reason: not available from an on-disk cache-status artifact
- last cached date: not available from an on-disk cache-status artifact
- KMeans fits avoided: not available from an on-disk cache-status artifact
- KMeans fits performed: not available from an on-disk cache-status artifact
- regime runtime: not available from an on-disk cache-status artifact

Operational data is current through `2026-07-02`.

## Overall Data Conclusion

Both repositories have local market data and the active feature/label/modeling parquet set through `2026-07-02`. Development has a valid regime cache HIT artifact. Operational does not retain the same cache status artifact, so cache health cannot be independently read from `data/cache`, but the operational feature set is current and matches the active feature manifest.

