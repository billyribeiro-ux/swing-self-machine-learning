# First Codex Prompt

Paste the following into Codex after opening the repository folder:

```text
Read AGENTS.md and every document it requires, in the stated order.

This repository is the canonical Version 1 project for a daily swing-trading RSI self-learning engine. Do not expand scope.

First, inspect the repository and run all existing tests and quality checks. Do not edit anything until you have summarized:
1. the current architecture,
2. the Version 1 boundaries,
3. the exact signal and entry timing,
4. the current anti-leakage protections,
5. the FMP authentication and normalization path,
6. any failing tests or design conflicts.

Then implement only Milestone M1 from docs/MILESTONES.md: the FMP real-data ingestion audit.

Preserve CSV loading and the existing FMP adapter. Add provider-neutral raw/processed caching and a reproducible per-symbol data-quality report. Do not hardcode or print the API key. Keep yfinance isolated as an optional fallback/comparison adapter, not a trusted production source.

Acceptance criteria:
- no options or intraday functionality,
- no same-close fills,
- no label columns in features,
- FMP raw-response provenance is reproducible without committing licensed data,
- split/dividend consistency checks are implemented and documented,
- missing sessions, duplicates, stale rows, invalid OHLC, date semantics, and provider errors are tested,
- SPY, QQQ, AAPL, MSFT, NVDA, TSLA, AMD, META, AMZN, and GOOGL can be audited through one command,
- no research optimization begins during M1,
- all tests, Ruff, formatting, and mypy pass,
- docs/CHANGELOG.md and docs/DECISIONS.md are updated,
- the final report lists changed files, assumptions, limitations, leakage review, and the next smallest milestone.
```
