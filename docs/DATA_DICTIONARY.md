# Data Dictionary

## Required raw daily OHLCV

| Field | Type | Meaning |
|---|---|---|
| Date | date | Trading session date |
| Open | float | Session open |
| High | float | Session high |
| Low | float | Session low |
| Close | float | Session close |
| Volume | float | Session volume |
| Adj Close | float, optional | Provider-adjusted close; cannot be mixed casually with raw OHLC |

## Starter trailing features

| Prefix/field | Meaning |
|---|---|
| `sma_*` | Simple moving averages and trailing slopes |
| `atr_*` | Wilder ATR and ATR as percentage of close |
| `atr_percentile_252` | Trailing percentile of ATR percentage |
| `relative_volume_20` | Current volume divided by prior 20-session mean volume |
| `close_position` | Close location within current session range |
| `gap_pct` | Open relative to prior close |
| `drawdown_from_high_*` | Close relative to a trailing prior high |
| `bounce_from_low_*` | Close relative to a trailing prior low |
| `failed_breakdown_20` | Low pierced prior 20-session low but close reclaimed it |

## RSI fields

| Field | Meaning |
|---|---|
| `rsi_<length>` | Wilder RSI for the specified length |
| Rule slope | Current RSI minus RSI from the configured prior bar |
| Lower reclaim | RSI crosses from at/below a lower region to above it |

## Future labels

All future-looking fields begin with `label_`. Examples:

- `label_return_10d`
- `label_mfe_10d`
- `label_mae_10d`
- `label_positive_10d`
- `label_hit_3pct_within_10d`

No `label_` column may be used by the scanner or model feature matrix.
