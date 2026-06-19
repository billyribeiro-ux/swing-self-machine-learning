# Secure FMP Setup

FMP is the primary real-data provider for Version 1.

## Local configuration

From the project root:

```bash
chmod +x scripts/configure_fmp.sh
./scripts/configure_fmp.sh
```

The script uses hidden Terminal input and writes:

```text
.env
```

The `.env` file is ignored by Git and excluded from the downloadable ZIP. Its permissions are restricted to the Mac owner.

## Authentication design

The adapter sends the credential in the `apikey` HTTP request header, not in the URL query string. Tests verify that the key is absent from request parameters and error messages.

## Verification commands

```bash
python -m swing_rsi.cli doctor
python -m swing_rsi.cli fmp-check --ticker AAPL
```

`doctor` confirms whether a key is configured without printing it. `fmp-check` requests a small daily-data window and validates the returned OHLCV.

## First full download

```bash
python -m swing_rsi.cli download --provider fmp --ticker AAPL --start 2010-01-01
```

## Data-integrity rule

FMP data is not trusted blindly. Milestone M1 still must audit:

- split and dividend semantics,
- adjusted versus unadjusted fields,
- missing sessions,
- duplicates,
- historical corrections,
- delisted-symbol availability,
- exchange calendars,
- point-in-time universe construction,
- and agreement with an independent sample source.
