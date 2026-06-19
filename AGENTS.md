# AGENTS.md

These instructions apply to Codex and every coding agent working in this repository.

## Read before editing

Read, in order:

1. `docs/VISION.md`
2. `docs/V1_SCOPE.md`
3. `docs/ARCHITECTURE.md`
4. `docs/FMP_SETUP.md`
5. `docs/FMP_DATA_SOURCE.md`
6. `docs/RSI_RESEARCH_SPEC.md`
7. `docs/BACKTESTING_STANDARD.md`
8. `docs/MODEL_VALIDATION_STANDARD.md`
9. `docs/FORWARD_TESTING_STANDARD.md`
10. `docs/DECISIONS.md`
11. `docs/ASSUMPTIONS.md`
12. `docs/OPEN_QUESTIONS.md`

## Non-negotiable Version 1 boundaries

Do not add options, Greeks, implied volatility, gamma, dealer positioning, intraday bars, market internals, news/NLP, brokerage execution, reinforcement learning, or deep learning unless the scope documents are explicitly revised first.

## Research integrity

- A signal observed at the daily close cannot be filled at that same close.
- The earliest default entry is the next trading session's open.
- Never train on future observations or compute trailing features with future bars.
- Keep label columns prefixed with `label_` and prevent them from entering feature matrices.
- Never optimize or rank candidates using win rate alone.
- Report trade count, expectancy, median return, profit factor, max drawdown, MFE, MAE, temporal stability, and out-of-sample results.
- Preserve `RSI(14)` and `70/30` as a baseline/control, not as a privileged rule.
- Treat claims about institutional use of retail defaults as hypotheses to test, not established causal facts.
- Never silently alter signal timestamps, entries, exits, costs, or failed trades.
- Forward signals and outcomes are append-only records.
- Synthetic demo data validates software plumbing only, never strategy performance.

## Engineering rules

- Python 3.12+.
- Use the `src/` package layout.
- Keep modules small, typed, and testable.
- Prefer transparent implementations over opaque abstractions.
- FMP is the primary Version 1 daily-data provider; keep provider logic isolated.
- Treat provider quality as testable, not assumed.
- Validate all OHLCV data at ingestion.
- Use UTC or explicit `America/New_York` semantics when timestamps are introduced.
- Do not commit secrets, API keys, virtual environments, raw licensed data, or generated caches.
- Add or update tests for every behavior change.
- Run `pytest`, `ruff check .`, `ruff format --check .`, and `mypy src` before declaring completion.
- Update `docs/CHANGELOG.md` after meaningful work.
- Add a dated entry to `docs/DECISIONS.md` for architectural or methodological changes.
- Add unresolved methodological questions to `docs/OPEN_QUESTIONS.md`; do not guess.

## Completion report

After each milestone, report:

- Files changed
- Tests and checks run
- Exact assumptions introduced
- Known limitations
- Data leakage review
- Scope changes, if any
- Next smallest milestone
