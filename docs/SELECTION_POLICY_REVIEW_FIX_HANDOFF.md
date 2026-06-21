# Selection Policy Review Fix Handoff

Date: 2026-06-20

Branch: `feat/autonomous-swing-scanner-v1`

Commit message: `fix: align scanner selection and portfolio ordering`

Commit hash: recorded in the final Codex response after commit creation. A Git commit cannot contain its own final object hash in tracked content.

## Scope

This pass fixes only the three confirmed `/review` findings:

1. Scanner actionability did not apply persisted expected-return and target-before-stop thresholds.
2. Holdout candidate-cap ranking did not match the persisted tie-breaking rule.
3. Same-date portfolio replay was input-order dependent when equal-utility rows met binding constraints.

No models were retrained. No FMP data was updated. The scanner, forward updater, daily cycle, and model promotion paths were not run against persistent state. `.env` was not opened or printed.

## Finding 1: Scanner Persisted Policy Gates

Root cause: `src/swing_rsi/engine/scanner.py` used `ScannerConfig.probability_threshold`, `ScannerConfig.minimum_dollar_volume`, and `expected_return > 0`, but it did not load or apply the model artifact's persisted `SelectionPolicy`.

Correction:

- Added canonical `evaluate_candidate_policy()` in `src/swing_rsi/engine/selection.py`.
- Scanner now loads `selection_policy_json` and `selection_policy_configuration_hash` from each `ModelBundle.metrics`.
- Scanner rejects missing or unreadable persisted policy with `persisted_selection_policy_missing`.
- Scanner applies expected-return threshold `0.001` and target-before-stop threshold `0.50` from the persisted policy.
- ScannerConfig may make thresholds stricter, never looser:
  - minimum thresholds use `max(persisted_threshold, runtime_threshold)`;
  - caps use `min(persisted_cap, runtime_cap)` when both are configured.
- Snapshot identity now includes model policy hashes so a policy change cannot reuse an older scanner snapshot with stale actionability.

## Finding 2: Holdout Cap Tie-Breaking

Root cause: holdout selection ranked cap-bound candidates by `composite_utility_score`, then probability and expected return, before symbol. That disagreed with the persisted `tie_breaking_rule`.

Correction:

- Added one canonical deterministic ordering helper, `order_candidates()`, in `src/swing_rsi/engine/selection.py`.
- The declared and implemented order is:
  1. `composite_utility_score` descending;
  2. symbol ascending;
  3. direction ascending;
  4. model ID ascending;
  5. stable candidate identity hash ascending.
- Holdout per-date and global caps use `select_policy_cap_indexes()`, which uses the canonical order.
- Probability and expected return are not tie-breakers unless the persisted policy is explicitly changed.

## Finding 3: Portfolio Same-Date Determinism

Root cause: portfolio replay sorted same-date candidates only by `composite_utility_score`, so equal-score rows retained input order. With binding constraints, shuffling input rows could change entered trades and rejection reasons.

Correction:

- `backtest_scanner_candidates()` now calls the same `order_candidates(..., date_column="as_of_date")` helper.
- Portfolio replay processes dates chronologically and candidates within each date by the canonical deterministic order.
- Equal-utility same-date candidates now produce identical entered symbols, rejected symbols, rejection reasons, trade ledgers, daily equity, and metrics across shuffled inputs.

## Canonical Policy Evaluation

Function: `src/swing_rsi/engine/selection.py::evaluate_candidate_policy`

It evaluates:

- `probability_threshold`;
- `expected_return_threshold`;
- `target_before_stop_threshold`;
- `liquidity_threshold`.

Semantics:

- configured minimum thresholds pass only when value is `>= threshold`;
- missing required metrics fail with `required_policy_metric_missing`;
- non-finite required metrics fail with `required_policy_metric_nonfinite`;
- below-threshold values fail with one of:
  - `below_probability_threshold`;
  - `below_expected_return_threshold`;
  - `below_target_before_stop_threshold`;
  - `below_liquidity_threshold`.

The result is structured and includes:

- `passed`;
- individual check results;
- rejection reasons;
- policy hash when supplied.

Both holdout model selection and live scanner actionability import and call this same function.

## Scanner Actionability Rules

A scanner row may become `ACTIONABLE_PAPER_CANDIDATE` only when:

1. model state is `CHAMPION` or `CHALLENGER`;
2. persisted canonical quality gates mark the model eligible;
3. the model has a persisted `SelectionPolicy`;
4. the row passes the effective persisted-plus-runtime policy;
5. the row survives deterministic per-date and global caps.

Runtime configuration may tighten thresholds and caps. It cannot relax persisted model policy.

## Tests Added

Added or extended tests covering:

- expected return `0.0005` rejected against persisted `0.001`;
- target-before-stop probability `0.49` rejected against persisted `0.50`;
- equality at minimum thresholds passes;
- missing required selection metrics fail;
- non-finite required selection metrics fail;
- scanner config cannot loosen persisted thresholds;
- scanner config can tighten thresholds;
- scanner and holdout selection use the same canonical evaluator;
- equal-utility cap selection uses symbol before probability or expected return;
- shuffled holdout rows select the same candidate set;
- shuffled scanner rows produce the same candidate statuses under caps;
- promoted but gate-ineligible models cannot produce actionable rows;
- missing persisted policy cannot produce actionable rows;
- shuffled same-date portfolio candidates produce identical trades, rejections, equity, and metrics.

## Verification Results

Full suite:

- Command: `.venv/bin/pytest`
- Collected: 108
- Passed: 108
- Failed: 0
- Skipped: 0
- Warnings: 161
- Time: 99.09s

Focused review suite:

- Command: `.venv/bin/pytest tests/test_model_evaluation_integrity.py tests/test_autonomous_engine.py tests/test_dashboard_model_registry.py tests/test_dashboard_interactions.py -q`
- Passed: 50
- Failed: 0
- Skipped: 0
- Warnings: 161
- Time: 81.81s

Static checks:

- Command: `.venv/bin/ruff check .`
- Result: passed
- Command: `.venv/bin/ruff format --check .`
- Result: passed, 91 files already formatted
- Command: `.venv/bin/mypy src`
- Result: passed, no issues in 53 source files

## Changed Files

- `src/swing_rsi/engine/selection.py`
- `src/swing_rsi/engine/models.py`
- `src/swing_rsi/engine/scanner.py`
- `src/swing_rsi/engine/portfolio.py`
- `src/swing_rsi/application/engine_service.py`
- `dashboard/sections/model_registry.py`
- `tests/test_autonomous_engine.py`
- `tests/test_model_evaluation_integrity.py`
- `docs/SCANNER_SPEC.md`
- `docs/MODEL_VALIDATION_STANDARD.md`
- `docs/MODEL_GOVERNANCE.md`
- `docs/DECISIONS.md`
- `docs/CHANGELOG.md`
- `docs/SELECTION_POLICY_REVIEW_FIX_HANDOFF.md`

## Remaining Limitations

- Existing model artifacts were not retrained, so older registered models may still show their old persisted policy metadata until a future discovery run creates new artifacts.
- The current-state audit report remains untracked and was intentionally not committed.
- External `/review` is not a shell command available inside this environment; final Codex response reports the local post-commit review status.
