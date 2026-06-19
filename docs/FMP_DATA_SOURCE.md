# FMP Data Source

## Version 1 role

Financial Modeling Prep is the primary initial provider for daily stock and ETF OHLCV. The project uses the stable end-of-day full-history endpoint and sends the API key through the `apikey` request header rather than embedding it in the URL.

## Local configuration

The API key belongs in `.env` as:

```text
FMP_API_KEY=...
FMP_BASE_URL=https://financialmodelingprep.com/stable
```

Use `./scripts/configure_fmp.sh` rather than manually editing source code. `.env` is excluded from Git.

## Endpoint

```text
GET /historical-price-eod/full
```

Parameters currently used:

- `symbol`
- `from`
- `to`

## What the adapter currently guarantees

- Uppercases and validates the ticker
- Validates ISO dates and date ordering
- Uses header authentication
- Handles current list responses and the older `historical` wrapper shape
- Rejects authentication, plan, rate-limit, HTTP, JSON, and schema errors clearly
- Normalizes fields to Date, Open, High, Low, Close, optional Adj Close, and Volume
- Sorts chronologically
- Rejects duplicate dates and invalid OHLCV
- Never logs the key

## What is not yet proven

- Split and dividend adjustment semantics across all instruments and dates
- Completeness of historical sessions
- Delisted-security coverage suitable for unbiased universe research
- Point-in-time universe membership
- Correction and revision behavior
- Consistency against an independent reference provider

FMP is the selected initial source, not an unquestioned source of truth. Milestone M1 audits its suitability before model claims are trusted.
