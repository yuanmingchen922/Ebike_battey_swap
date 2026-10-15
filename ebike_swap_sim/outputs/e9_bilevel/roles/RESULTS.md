# E9.3 -- role separation: co-located only vs hubs allowed vs no hubs

Family `nyc4h_stress2` (6 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 87.1 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Role sets per budget

| budget_m | role_set | layout_key | n_S | n_C | n_SC | investment | V | opex_mean | transfers_used | C_reb | served_share | status | search_complete | reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | SC_only | L02:SC:B4:C2 | 0 | 0 | 1 | 52600 | 654.525 | 641.003 | 0 | 0 | 0.852 | OK | True | - |
| 3 | SC_only | L02:SC:B4:C2 | 0 | 0 | 1 | 52600 | 654.525 | 641.003 | 0 | 0 | 0.852 | OK | True | - |
| 2 | S_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52600 | 654.525 | 641.003 | 0 | 0 | 0.852 | OK | True | - |
| 3 | S_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52600 | 654.525 | 641.003 | 0 | 0 | 0.852 | OK | True | - |
| 2 | S_C_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52600 | 654.525 | 641.003 | 0 | 0 | 0.852 | OK | True | - |
| 3 | S_C_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52600 | 654.525 | 641.003 | 0 | 0 | 0.852 | OK | True | - |

## Solver statistics

{"n_solves": 84, "n_cache_hits": 5838, "n_baseline_runs": 1446, "n_errors": 0, "solver_time_s": 2382.504446744919, "library_time_s": 2305.2926905259956, "n_cached_rows": 1466, "reposition": "open_sites"}

## Figures

* `roles.png`
* `roles_components.png`
