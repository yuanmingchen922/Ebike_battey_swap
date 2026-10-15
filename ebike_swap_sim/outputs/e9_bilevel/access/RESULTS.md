# E9.6 -- the planner-only access row [U4]: what it costs the operator

Family `nyc4h_stress2` (6 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 140.4 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Access row per budget

| budget_m | method | layout_key | investment | V | opex_mean | served_share | zone_mean_blocks | zone_max_blocks | zones_covered | uncovered_zones | access_repaired | uncoverable_zones | status | search_complete | reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | greedy_ls[no_access] | L02:SC:B4:C2 | 52600 | 654.525 | 641.003 | 0.852 | 11.648 | 22 | {"8": 5, "12": 8} | [] | False | [] | OK | True | - |
| 3 | greedy_ls[no_access] | L02:SC:B4:C2 | 52600 | 654.525 | 641.003 | 0.852 | 11.648 | 22 | {"8": 5, "12": 8} | [] | False | [] | OK | True | - |
| 2 | greedy_ls[D8] | L02:SC:B4:C1|L05:SC:B1:C1 | 103050 | 666.605 | 640.721 | 0.852 | 8.519 | 15 | {"8": 8, "12": 11} | ["MN0202", "MN0701", "MN0801"] | True | ["MN0801"] | OK | True | - |
| 3 | greedy_ls[D8] | L02:SC:B4:C2|L05:SC:B1:C1|L08:S:B1:C0 | 153900 | 678.906 | 640.578 | 0.852 | 7.407 | 15 | {"8": 9, "12": 11} | ["MN0701", "MN0801"] | True | ["MN0801"] | OK | False | - |
| 2 | greedy_ls[D12] | L02:SC:B4:C1|L05:SC:B1:C1 | 103050 | 666.605 | 640.721 | 0.852 | 8.519 | 15 | {"8": 8, "12": 11} | [] | True | [] | OK | True | - |
| 3 | greedy_ls[D12] | L02:SC:B4:C1|L05:SC:B1:C1 | 103050 | 666.605 | 640.721 | 0.852 | 8.519 | 15 | {"8": 8, "12": 11} | [] | True | [] | OK | True | - |

## Access sets

* D = 8: {"MN0202": ["L08"], "MN0401": ["L01", "L02", "L07", "L08", "L11", "L12"], "MN0402": ["L01", "L03", "L05", "L06", "L07", "L11", "L12"], "MN0501": ["L01", "L02", "L03", "L07", "L08", "L09", "L10", "L12"], "MN0502": ["L01", "L02", "L03", "L04", "L05", "L06", "L07", "L09", "L10", "L11"], "MN0602": ["L02", "L08", "L09", "L10"], "MN0603": ["L01", "L02", "L03", "L04", "L05", "L09", "L10"], "MN0604": ["L03", "L04", "L05", "L09", "L10"], "MN0701": ["L06"], "MN0801": [], "MN0802": ["L04", "L05", "L06"]}
* D = 12: {"MN0202": ["L02", "L08"], "MN0401": ["L01", "L02", "L03", "L07", "L08", "L10", "L11", "L12"], "MN0402": ["L01", "L02", "L03", "L04", "L05", "L06", "L07", "L09", "L11", "L12"], "MN0501": ["L01", "L02", "L03", "L04", "L05", "L07", "L08", "L09", "L10", "L12"], "MN0502": ["L01", "L02", "L03", "L04", "L05", "L06", "L07", "L09", "L10", "L11", "L12"], "MN0602": ["L01", "L02", "L03", "L04", "L07", "L08", "L09", "L10", "L12"], "MN0603": ["L01", "L02", "L03", "L04", "L05", "L07", "L08", "L09", "L10", "L12"], "MN0604": ["L02", "L03", "L04", "L05", "L06", "L09", "L10"], "MN0701": ["L05", "L06", "L11"], "MN0801": ["L04", "L05", "L06", "L09"], "MN0802": ["L03", "L04", "L05", "L06", "L09"]}

## Solver statistics

{"n_solves": 112, "n_cache_hits": 8619, "n_baseline_runs": 2200, "n_errors": 0, "solver_time_s": 3900.3829641342163, "library_time_s": 3743.8167460397817, "n_cached_rows": 2220, "reposition": "open_sites"}

## Figures

* `access.png`
