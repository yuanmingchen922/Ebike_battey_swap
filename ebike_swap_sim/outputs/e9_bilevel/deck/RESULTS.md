# E9.4 -- the proposal deck's spin-and-adjust planner vs the bi-level optimum

Family `nyc4h_stress2` (6 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 9.5 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Deck heuristic per budget

| budget_m | k | layout_key | investment | V | baseline_V | gap_vs_baseline_pct | served_share | status |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | L01:SC:B3:C2 | 52150 | 655.056 | 1072.254 | 38.909 | 0.852 | OK |
| 2 | 2 | L01:SC:B3:C1|L02:SC:B4:C1 | 103950 | 667.085 | 1025.277 | 34.936 | 0.852 | OK |
| 3 | 3 | L01:SC:B4:C1|L02:SC:B4:C1|L04:SC:B3:C1 | 156150 | 680.060 | 1031.660 | 34.081 | 0.852 | OK |
| 4 | 4 | L01:SC:B4:C1|L02:SC:B5:C1|L04:SC:B3:C1|L06:SC:B3:C1 | 208350 | 693.310 | 1055.868 | 34.337 | 0.852 | OK |

## Overlap and regret vs the bi-level layouts (from --sweep records, if present)

| budget_m | other | deck | other_layout | shared_locations | regret_usd | regret_pct |
|---|---|---|---|---|---|---|
| 1 | greedy_ls | L01:SC:B3:C2 | L02:SC:B3:C2 | 0 | 0.680 | 0.104 |

## Solver statistics

{"n_solves": 9, "n_cache_hits": 27, "n_baseline_runs": 27, "n_errors": 0, "solver_time_s": 487.9887788295746, "library_time_s": 31.234449541196227, "n_cached_rows": 1509, "reposition": "open_sites"}

## Figures

* `deck_vs_bilevel.png`
