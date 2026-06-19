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
5. any failing tests or design conflicts.

Then implement only Milestone M1 from docs/MILESTONES.md: the real-data ingestion audit. Preserve CSV loading, add a provider-neutral cache and data-quality report, and keep yfinance isolated as a bootstrap adapter rather than a trusted production source.

Acceptance criteria:
- no options or intraday functionality,
- no same-close fills,
- no label columns in features,
- split/dividend consistency checks documented,
- missing sessions, duplicates, invalid OHLC, and timezone handling tested,
- all tests, ruff, formatting, and mypy pass,
- docs/CHANGELOG.md and docs/DECISIONS.md updated,
- final report lists changed files, assumptions, limitations, and next smallest milestone.
```
