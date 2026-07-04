# Development Final-Holdout Status

Repository:
`/Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev`

## Run Identity

- run ID: `d25d6fa11a2e50daa430c15e`
- original enrolled model: `5b3f37a96a7968bca8d2f398`
- model state at enrollment: `CANDIDATE`
- original enrolled code commit: `8e2b40effab1332f474ca47d720fcb8c21ca4912`
- current development code commit: `2423023d781d945680ceece25fc58317f45de217`
- status: `INVALIDATED`
- invalidation reason: `code commit hash changed since enrollment`
- baseline market date: `2026-06-25`
- first eligible future signal date: `2026-06-26`
- latest processed market date: `2026-06-26`

## Invalidation Events

| Market date | Event ID | Timestamp UTC | Reason |
| --- | --- | --- | --- |
| 2026-06-29 | `bc77733b0893a7208617358c` | `2026-07-04T18:13:49.162277+00:00` | code commit hash changed since enrollment |
| 2026-06-30 | `4cf384958eaf8174240ac3a3` | `2026-07-04T18:13:50.582104+00:00` | code commit hash changed since enrollment |
| 2026-07-01 | `9bb40623c0fc620c4a595bd7` | `2026-07-04T18:13:51.999438+00:00` | code commit hash changed since enrollment |
| 2026-07-02 | `101184c317f351f803e595de` | `2026-07-04T18:13:53.444537+00:00` | code commit hash changed since enrollment |

## Event State

- event count: 30
- event count by type:
  - `FINAL_HOLDOUT_SIGNAL_REJECTED`: 24
  - `FINAL_HOLDOUT_SIGNAL_CREATED`: 1
  - `FINAL_HOLDOUT_ENTRY_PENDING`: 1
  - `FINAL_HOLDOUT_DATA_INVALIDATED`: 4
- previous events rewritten: no evidence of rewrite; invalidation was appended.

## Historical TZA Row

The pending TZA row remains visible as historical evidence:

| Event type | Event ID | Market date | Ticker | Probability | Expected return | Entry rule |
| --- | --- | --- | --- | ---: | ---: | --- |
| `FINAL_HOLDOUT_SIGNAL_CREATED` | `2acdbdee5fb355bc94566f9a` | 2026-06-26 | TZA | 0.576112 | 0.022294 | `next_completed_session_open` |
| `FINAL_HOLDOUT_ENTRY_PENDING` | `b75bad88ada4dd671a60e514` | 2026-06-26 | TZA | 0.576112 | 0.022294 | `next_completed_session_open` |

## Plain-English Explanation

This development final-holdout run was enrolled under commit `8e2b40effab1332f474ca47d720fcb8c21ca4912`. The development branch has since moved to `2423023d781d945680ceece25fc58317f45de217`. Because final-holdout evidence must be tied to the exact enrolled code state, the run was invalidated when the code commit changed.

That is expected after development code changes. The run should not be reactivated or repaired. It should be treated as invalidated historical evidence only. A separate explicit task would be required to initialize a new development final-holdout run under the current code commit.

