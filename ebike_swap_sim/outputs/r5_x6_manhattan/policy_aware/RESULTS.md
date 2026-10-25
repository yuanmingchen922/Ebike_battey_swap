# E9 M4 -- policy-aware siting with follower selfish

Family `r5_manhattan` (8 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/cache`; reposition targets `open_sites`; min served share 0; swap-only sites need a C / SC object: True; wall 30.8 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Chosen layouts

| budget_m | layout_key | investment | status | ilp_V | baseline_V | selfish_V | ilp_served_share | baseline_served_share | selfish_served_share | price_of_decentralisation | ilp_chosen_layout | ilp_chosen_ilp_V | ilp_chosen_baseline_V | ilp_chosen_selfish_V |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | M07:SC:B3:C1 | 51750 | OK | - | 1224.436 | 1224.436 | - | 0.358 | 0.358 | - | - | - | - | - |
| 2 | M07:SC:B3:C1 | 51750 | OK | - | 1224.436 | 1224.436 | - | 0.358 | 0.358 | - | M06:SC:B4:C2|M12:S:B3:C0 | 703.115 | 1020.797 | - |
| 3 | M07:SC:B3:C1 | 51750 | OK | - | 1224.436 | 1224.436 | - | 0.358 | 0.358 | - | M06:SC:B4:C2|M12:S:B3:C0 | 703.115 | 1020.797 | - |
| 4 | M07:SC:B3:C1 | 51750 | OK | - | 1224.436 | 1224.436 | - | 0.358 | 0.358 | - | M06:SC:B4:C2|M12:S:B3:C0 | 703.115 | 1020.797 | - |

## Greedy frontier

[["M07:SC:B3:C1", 1224.4364074074074]]

priced layouts by status: {"OK": 2, "SKIPPED_BUDGET": 6}

## Solver statistics

{"n_solves": 0, "n_cache_hits": 229, "n_baseline_runs": 411, "n_errors": 0, "solver_time_s": 0.0, "library_time_s": 1744.918613332091, "n_cached_rows": 1111, "reposition": "open_sites", "aggregate": true, "variant": {}}

## Figures

* `policy_aware.png`
