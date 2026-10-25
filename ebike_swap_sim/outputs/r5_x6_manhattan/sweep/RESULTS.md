# E9 sweep -- greedy + local search per budget

Family `r5_manhattan` (8 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 124.2 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Chosen layouts per budget

| budget_m | method | layout_key | investment | C_setup | status | V | opex_mean | served_share | n_late | kwh_purchased | transfers_used | gap | bound | search_complete | reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | greedy_ls | - | - | - | wall budget exhausted | - | - | - | - | - | - | - | - | False | {"INFEASIBLE_ILP": 1, "OK": 4, "SKIPPED_BUDGET": 3} |
| 2 | greedy_ls | M06:SC:B4:C2|M12:S:B3:C0 | 103950 | 26.548 | OK | 703.115 | 676.567 | 0.858 | 1 | 2.454 | 0 | - | - | False | - |
| 3 | greedy_ls | M06:SC:B4:C2|M12:S:B3:C0 | 103950 | 26.548 | OK | 703.115 | 676.567 | 0.858 | 1 | 2.454 | 0 | - | - | False | - |
| 4 | greedy_ls | M06:SC:B4:C2|M12:S:B3:C0 | 103950 | 26.548 | OK | 703.115 | 676.567 | 0.858 | 1 | 2.454 | 0 | - | - | False | - |

## Greedy frontier

[["M06:SC:B4:C2", 783.7825925925924], ["M06:SC:B4:C2|M12:S:B3:C0", 703.114537037037]]

best singleton: ('M06:SC:B4:C2', 783.7825925925924)

priced layouts by status: {"INFEASIBLE_ILP": 1, "OK": 4, "SKIPPED_BUDGET": 3}; wall exhausted: True

## Solver statistics

{"n_solves": 14, "n_cache_hits": 9, "n_baseline_runs": 560, "n_errors": 0, "solver_time_s": 4601.57439494133, "library_time_s": 2593.063142286148, "n_cached_rows": 614, "reposition": "open_sites", "aggregate": true, "variant": {}}

## Figures

* `pareto.png`
* `map_budget_1.png`
* `map_budget_2.png`
* `map_budget_3.png`
* `map_budget_4.png`
