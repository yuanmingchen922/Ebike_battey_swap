# E9.5 -- cross-evaluation of the chosen layouts under the ILP and the baseline policy

Family `nyc4h_stress2` (6 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 55.8 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Layout x policy

| layout_key | sources | investment | ilp_V | baseline_V | ilp_relaxed_V | gap_vs_baseline_pct | regret_ilp | regret_baseline | ilp_served_share | baseline_served_share | ilp_opex_in_sample | ilp_opex_out_of_sample | in_out_gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L02:SC:B3:C2 | ["greedy_ls@m1.0"] | 52150 | 654.488 | 1026.244 | 654.140 | 36.225 | 0 | 47.374 | 0.856 | 0.811 | 641.187 | 641.465 | 0.278 |
| L01:SC:B3:C2 | ["deck@m1.0"] | 52150 | 654.649 | 1022.259 | 654.294 | 35.961 | 0.161 | 43.390 | 0.856 | 0.822 | 641.866 | 640.849 | -1.017 |
| L01:SC:B3:C1|L02:SC:B4:C1 | ["deck@m2.0"] | 103950 | 666.912 | 991.355 | 666.490 | 32.727 | 12.424 | 12.486 | 0.856 | 0.833 | 640.537 | 640.106 | -0.431 |
| L01:SC:B4:C1|L02:SC:B4:C1|L04:SC:B3:C1 | ["deck@m3.0"] | 156150 | 679.852 | 986.307 | 679.667 | 31.071 | 25.364 | 7.438 | 0.856 | 0.844 | 640.072 | 639.553 | -0.519 |
| L01:SC:B4:C1|L02:SC:B5:C1|L04:SC:B3:C1|L06:SC:B3:C1 | ["deck@m4.0"] | 208350 | 693.100 | 1006.162 | 693.078 | 31.114 | 38.612 | 27.292 | 0.856 | 0.844 | 639.882 | 639.357 | -0.525 |
| L02:SC:B4:C2 | ["greedy_ls[SC_only]@m2.0", "greedy_ls[SC_only]@m3.0", "greedy_ls[S_SC]@m2.0", "greedy_ls[S_SC]@m3.0", "greedy_ls[S_C_SC]@m2.0", "greedy_ls[S_C_SC]@m3.0"] | 52600 | 654.639 | 978.869 | 654.322 | 33.123 | 0.151 | 0 | 0.856 | 0.850 | 641.003 | 641.287 | 0.284 |
| L02:SC:B2:C1 | ["exhaustive@m1.0", "integrated@m1.0"] | 51300 | 662.788 | 1129.475 | 661.404 | 41.319 | 8.300 | 150.605 | 0.828 | 0.706 | 651.695 | 647.487 | -4.208 |

## Solver statistics

{"written": {"n_solves": 17, "n_cache_hits": 39, "n_baseline_runs": 31, "n_errors": 0, "solver_time_s": 1144.5386641025543, "library_time_s": 27.832533623557538, "n_cached_rows": 1615, "reposition": "open_sites"}, "relaxed": {"n_solves": 35, "n_cache_hits": 0, "n_baseline_runs": 35, "n_errors": 0, "solver_time_s": 1901.4990892410278, "library_time_s": 50.27993174968287, "n_cached_rows": 1619, "reposition": "open_sites"}}

## Figures

* `cross_eval.png`
