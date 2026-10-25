# E9 A4 -- marginal-lever table under each follower

Family `r5_manhattan` (8 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 38.9 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Reference

Layout M06:SC:B4:C2|M12:S:B3:C0 (cli); V per follower {"ilp": 703.114537037037, "selfish": 1057.451111111111}

## Best site per lever and follower

| lever | policy | site | d_V | d_investment | served_new |
|---|---|---|---|---|---|
| spare | ilp | M06 | -19.724 | 450 | 0.900 |
| spare | selfish | M12 | 7.304 | 450 | 0.808 |
| charger | ilp | M06 | -21.054 | 400 | 0.908 |
| charger | selfish | M06 | 47.691 | 400 | 0.792 |
| position | ilp | M06 | -7.024 | 400 | 0.883 |
| position | selfish | M12 | 0.040 | 400 | 0.758 |
| shuttle | ilp | - | - | - | - |
| shuttle | selfish | all pairs | 0 | 0 | 0.758 |
| grid | ilp | - | - | - | - |
| grid | selfish | group | 0 | 0 | 0.758 |

## All lever evaluations

| lever | site | policy | status | V_ref | V_new | d_V | d_opex | d_investment | d_allocated | d_V_per_kusd | served_ref | served_new | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spare | M06 | ilp | OK | 703.115 | 683.391 | -19.724 | -20.056 | 450 | 0.332 | -43.831 | 0.858 | 0.900 |  |
| spare | M06 | selfish | OK | 1057.451 | 1160.883 | 103.432 | 103.100 | 450 | 0.332 | 229.848 | 0.758 | 0.833 |  |
| spare | M12 | ilp | OK | 703.115 | 683.433 | -19.682 | -20.014 | 450 | 0.332 | -43.737 | 0.858 | 0.892 |  |
| spare | M12 | selfish | OK | 1057.451 | 1064.755 | 7.304 | 6.972 | 450 | 0.332 | 16.231 | 0.758 | 0.808 |  |
| charger | M06 | ilp | OK | 703.115 | 682.061 | -21.054 | -21.136 | 400 | 0.082 | -52.635 | 0.858 | 0.908 |  |
| charger | M06 | selfish | OK | 1057.451 | 1105.142 | 47.691 | 47.609 | 400 | 0.082 | 119.227 | 0.758 | 0.792 |  |
| position | M06 | ilp | OK | 703.115 | 696.051 | -7.024 | -7.064 | 400 | 0.040 | -17.560 | 0.858 | 0.883 | M_j 1 -> 2; capex 400 USD |
| position | M06 | selfish | OK | 1057.451 | 1115.218 | 57.807 | 57.767 | 400 | 0.040 | 144.517 | 0.758 | 0.783 | M_j 1 -> 2; capex 400 USD |
| position | M12 | ilp | OK | 703.115 | 703.649 | 0.574 | 0.535 | 400 | 0.040 | 1.436 | 0.858 | 0.858 | M_j 1 -> 2; capex 400 USD |
| position | M12 | selfish | OK | 1057.451 | 1057.451 | 0.040 | 0 | 400 | 0.040 | 0.099 | 0.758 | 0.758 | M_j 1 -> 2; capex 400 USD |
| shuttle | all pairs | ilp | SKIPPED_BUDGET | 703.115 | - | - | - | 0 | 0 | - | 0.858 | - | one more vehicle (twin departures every/2 later); trips priced by f_e (32) |
| shuttle | all pairs | selfish | OK | 1057.451 | 1057.451 | 0 | 0 | 0 | 0 | - | 0.758 | 0.758 | one more vehicle (twin departures every/2 later); trips priced by f_e (32) |
| grid | group | ilp | SKIPPED_BUDGET | 703.115 | - | - | - | 0 | 0 | - | 0.858 | - | P_grid x 1.1; demand charge not priced (M10(b)) |
| grid | group | selfish | OK | 1057.451 | 1057.451 | 0 | 0 | 0 | 0 | - | 0.758 | 0.758 | P_grid x 1.1; demand charge not priced (M10(b)) |

## Solver statistics

{"n_solves": 9, "n_cache_hits": 3, "n_baseline_runs": 68, "n_errors": 0, "solver_time_s": 484.8783555030823, "library_time_s": 56.119376375572756, "n_cached_rows": 1152, "reposition": "open_sites", "aggregate": true, "variant": {}}

## Figures

* `levers.png`
