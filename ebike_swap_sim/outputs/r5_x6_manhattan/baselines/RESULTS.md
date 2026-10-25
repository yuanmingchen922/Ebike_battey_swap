# E9 A4 -- IJCAI-15 rules and the capacity-matched present-day layout under each follower

Family `r5_manhattan` (8 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 45.1 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Protocol

Rules ['CSCD', 'CSTC', 'CSAV'] (IJCAI-15 Sec. 5.1: CSCD demand-proportional within D = 14 blocks; CSTC mode access; CSAV uniform spread), each site SC with B = C = 1 plus extra spares / chargers bought alternately with the remaining budget (caps (4, 2)); present-day layout: proxy: DOHMH restaurants at the candidate node (no present-day hub list in data/raw), capacity-matched (same number of sites and total B, C) to the reference layout of each budget; followers ['ilp', 'baseline', 'selfish']; seeds [0, 1, 2].

## Layouts and values

| budget_m | rule | policy | layout_key | investment | status | V | served_share | reference | reference_source |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CSCD | ilp | M09:SC:B3:C2 | 52150 | OK | 796.387 | 0.683 | - | - |
| 1 | CSCD | baseline | M09:SC:B3:C2 | 52150 | OK | 1376.432 | 0.483 | - | - |
| 1 | CSCD | selfish | M09:SC:B3:C2 | 52150 | OK | 1376.432 | 0.483 | - | - |
| 1 | CSTC | ilp | M09:SC:B3:C2 | 52150 | OK | 796.387 | 0.683 | - | - |
| 1 | CSTC | baseline | M09:SC:B3:C2 | 52150 | OK | 1376.432 | 0.483 | - | - |
| 1 | CSTC | selfish | M09:SC:B3:C2 | 52150 | OK | 1376.432 | 0.483 | - | - |
| 1 | CSAV | ilp | M08:SC:B3:C2 | 52150 | OK | 795.414 | 0.675 | - | - |
| 1 | CSAV | baseline | M08:SC:B3:C2 | 52150 | OK | 1345.454 | 0.442 | - | - |
| 1 | CSAV | selfish | M08:SC:B3:C2 | 52150 | OK | 1345.454 | 0.442 | - | - |
| 2 | CSCD | ilp | M08:SC:B3:C2|M09:SC:B3:C2 | 104300 | OK | 676.582 | 0.908 | - | - |
| 2 | CSCD | baseline | M08:SC:B3:C2|M09:SC:B3:C2 | 104300 | OK | 1168.729 | 0.800 | - | - |
| 2 | CSCD | selfish | M08:SC:B3:C2|M09:SC:B3:C2 | 104300 | OK | 1123.746 | 0.783 | - | - |
| 2 | CSTC | ilp | M08:SC:B3:C2|M09:SC:B3:C2 | 104300 | OK | 676.582 | 0.908 | - | - |
| 2 | CSTC | baseline | M08:SC:B3:C2|M09:SC:B3:C2 | 104300 | OK | 1168.729 | 0.800 | - | - |
| 2 | CSTC | selfish | M08:SC:B3:C2|M09:SC:B3:C2 | 104300 | OK | 1123.746 | 0.783 | - | - |
| 2 | CSAV | ilp | M08:SC:B3:C2|M14:SC:B3:C2 | 104300 | OK | 699.194 | 0.892 | - | - |
| 2 | CSAV | baseline | M08:SC:B3:C2|M14:SC:B3:C2 | 104300 | OK | 1412.703 | 0.533 | - | - |
| 2 | CSAV | selfish | M08:SC:B3:C2|M14:SC:B3:C2 | 104300 | OK | 1248.557 | 0.700 | - | - |
| 3 | CSCD | ilp | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2 | 156450 | OK | 680.173 | 0.925 | - | - |
| 3 | CSCD | baseline | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2 | 156450 | OK | 1091.804 | 0.867 | - | - |
| 3 | CSCD | selfish | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2 | 156450 | OK | 973.319 | 0.917 | - | - |
| 3 | CSTC | ilp | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 156450 | OK | 679.067 | 0.925 | - | - |
| 3 | CSTC | baseline | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 156450 | OK | 1148.881 | 0.833 | - | - |
| 3 | CSTC | selfish | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 156450 | OK | 1007.119 | 0.883 | - | - |
| 3 | CSAV | ilp | M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2 | 156450 | OK | 686.958 | 0.925 | - | - |
| 3 | CSAV | baseline | M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2 | 156450 | OK | 1217.780 | 0.783 | - | - |
| 3 | CSAV | selfish | M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2 | 156450 | OK | 1067.802 | 0.850 | - | - |
| 4 | CSCD | ilp | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2 | 208600 | OK | 691.971 | 0.925 | - | - |
| 4 | CSCD | baseline | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2 | 208600 | OK | 1091.059 | 0.892 | - | - |
| 4 | CSCD | selfish | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2 | 208600 | OK | 955.542 | 0.925 | - | - |
| 4 | CSTC | ilp | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | 208600 | OK | 690.549 | 0.933 | - | - |
| 4 | CSTC | baseline | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | 208600 | OK | 1162.065 | 0.858 | - | - |
| 4 | CSTC | selfish | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | 208600 | OK | 961.172 | 0.925 | - | - |
| 4 | CSAV | ilp | M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2 | 208600 | OK | 694.278 | 0.933 | - | - |
| 4 | CSAV | baseline | M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2 | 208600 | OK | 1099.545 | 0.858 | - | - |
| 4 | CSAV | selfish | M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2 | 208600 | OK | 968.221 | 0.908 | - | - |
| 1 | present_day | ilp | M08:SC:B3:C2 | 52150 | OK | 795.414 | 0.675 | M08:SC:B3:C2 | best rule CSAV under ilp |
| 1 | present_day | baseline | M08:SC:B3:C2 | 52150 | OK | 1345.454 | 0.442 | M08:SC:B3:C2 | best rule CSAV under ilp |
| 1 | present_day | selfish | M08:SC:B3:C2 | 52150 | OK | 1345.454 | 0.442 | M08:SC:B3:C2 | best rule CSAV under ilp |
| 2 | present_day | ilp | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | SKIPPED_BUDGET | - | - | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 2 | present_day | baseline | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | OK | 1112.306 | 0.792 | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 2 | present_day | selfish | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | OK | 1086.583 | 0.775 | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 3 | present_day | ilp | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | SKIPPED_BUDGET | - | - | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 3 | present_day | baseline | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | OK | 1112.306 | 0.792 | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 3 | present_day | selfish | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | OK | 1086.583 | 0.775 | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 4 | present_day | ilp | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | SKIPPED_BUDGET | - | - | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 4 | present_day | baseline | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | OK | 1112.306 | 0.792 | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |
| 4 | present_day | selfish | M03:SC:B3:C1|M08:SC:B4:C1 | 103950 | OK | 1086.583 | 0.775 | M06:SC:B4:C2|M12:S:B3:C0 | sweep greedy_ls |

## Solver statistics

{"n_solves": 32, "n_cache_hits": 47, "n_baseline_runs": 208, "n_errors": 0, "solver_time_s": 2390.7731626033783, "library_time_s": 186.7618815859314, "n_cached_rows": 706, "reposition": "open_sites", "aggregate": true, "variant": {}}

## Figures

* `V_vs_budget.png`
