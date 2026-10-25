# X6 -- Manhattan-wide siting (M6, A4, M4) on `r5_manhattan`

Driver `experiments/r5_x6_manhattan.py`; seeds [0, 1, 2]; budgets m = [1.0, 2.0, 3.0, 4.0] (x 52,150 USD); Threads 3, Seed 0, TimeLimit 300 s (hubs 600 s), aggregated ILP (O1); k_screen 2; size menu `x6`; total wall budget 300 min. Every ILP total is an upper bound on the written optimum (moves only into open sites / depots); the R2.4 geometry caveat applies.

## Stages

| stage | status | complete | wall budget (min) | wall used (min) | folder |
|---|---|---|---|---|---|
| sweep | OK | False | 125.0 | 124.2 | `sweep/` |
| baselines | OK | False | 45.8 | 45.1 | `baselines/` |
| policy_aware | OK | False | 30.7 | 30.8 | `policy_aware/` |
| levers | OK | False | 40.0 | 38.9 | `levers/` |
| compliance | OK | True | 6.1 | 0.2 | `compliance/` |
| headline | OK | True | 60.9 | 32.2 | `headline/` |

## Chosen bi-level layout

`M06:SC:B4:C2|M12:S:B3:C0` -- {"source": "sweep greedy_ls@m2.0", "V": 703.114537037037, "budget_m": 2.0, "search_complete": false, "served_share": 0.8583333333333333}

## Demand md5 per base scenario (asserted across stages and runs)

```
{
 "seed0_bikes8_cands15": "46752a7261550259245286d760dd69c3",
 "seed1_bikes8_cands15": "df09c499257691cd6e76a7737c5192cc",
 "seed2_bikes8_cands15": "d960ba3b25aa2f5367a8431541eb3a32"
}
```

Per-stage reports: `sweep/RESULTS.md` (b), `baselines/RESULTS.md` (a), `policy_aware/RESULTS.md` (d), `levers/RESULTS.md` (c), `compliance/RESULTS.md` (e), `headline/RESULTS.md` (fairness + targets: relaxed-control headline gap vs best_rule, written targets = price of recovery, C_end_adjust and the A3 metric pack for both policies). Truncated stages (complete = False) resume by re-running the same command.
