# E9 sweep -- greedy + local search per budget with the integrated bound

Family `nyc4h_stress2` (6 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 133.2 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Chosen layouts per budget

| budget_m | method | layout_key | investment | C_setup | status | V | opex_mean | served_share | n_late | kwh_purchased | transfers_used | gap | bound | search_complete | reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | greedy_ls | L02:SC:B3:C2 | 52150 | 13.190 | OK | 654.377 | 641.187 | 0.852 | 1.667 | 2.352 | 0 | - | - | True | - |
| 1 | integrated | L02:SC:B3:C2 | 52150 | 13.190 | TIME_LIMIT | 654.377 | - | - | - | - | - | inf | inf | - | - |
| 2 | greedy_ls | L02:SC:B4:C2 | 52600 | 13.522 | OK | 654.525 | 641.003 | 0.852 | 1.667 | 1.741 | 0 | - | - | True | - |
| 2 | integrated | L02:SC:B4:C2 | 52600 | 13.522 | TIME_LIMIT | 654.525 | - | - | - | - | - | 20.172 | -12548.628 | - | - |
| 3 | greedy_ls | L02:SC:B4:C2 | 52600 | 13.522 | OK | 654.525 | 641.003 | 0.852 | 1.667 | 1.741 | 0 | - | - | True | - |
| 3 | integrated | L02:SC:B4:C2 | 52600 | 13.522 | TIME_LIMIT | 654.525 | - | - | - | - | - | 20.172 | -12548.628 | - | - |
| 4 | greedy_ls | L02:SC:B4:C2 | 52600 | 13.522 | OK | 654.525 | 641.003 | 0.852 | 1.667 | 1.741 | 0 | - | - | True | - |
| 4 | integrated | L02:SC:B4:C2 | 52600 | 13.522 | TIME_LIMIT | 654.525 | - | - | - | - | - | 20.172 | -12548.628 | - | - |

## Greedy frontier

[["L01:SC:B3:C2", 655.056148148148]]

best singleton: ('L01:SC:B3:C2', 655.056148148148)

priced layouts by status: {"OK": 29}; wall exhausted: False

## Solver statistics

{"n_solves": 87, "n_cache_hits": 2871, "n_baseline_runs": 1449, "n_errors": 0, "solver_time_s": 2547.523640394211, "library_time_s": 2278.891684182454, "n_cached_rows": 1469, "reposition": "open_sites"}

## Figures

* `pareto.png`
* `map_budget_1.png`
* `map_budget_2.png`
* `map_budget_3.png`
* `map_budget_4.png`
