# Daily Cycle

The daily cycle command is:

```bash
python -m swing_rsi.cli daily-cycle --include-challengers
```

The wrapper script is:

```bash
./scripts/run_daily_cycle.sh
```

## Steps

1. Acquire a local lock under `state/daily_cycle.lock`.
2. Optionally update local universe data through the existing provider abstraction.
3. Rebuild autonomous features and labels.
4. Run discovery only if no champion, challenger, or retained candidate exists.
5. Run the live scanner.
6. Append forward-test events from the scanner snapshot.
7. Mark the market date as completed in SQLite.
8. Release the lock.

## Idempotency

The same market-date cycle returns `already_completed` after the first completed run.

Scanner snapshots are keyed by as-of date, model IDs, universe snapshot, and feature snapshot hash.

Forward events use unique event keys and `INSERT OR IGNORE`, so reruns do not duplicate event rows.

## Secrets

The daily cycle uses the configured provider abstraction and never prints `.env`, API keys, authenticated URLs, or request headers.
