# E9.1 -- integrated stochastic ILP (A) vs exhaustive bi-level enumeration (B)

Family `nyc4h_stress2` (6 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel/cache`; reposition targets `all_candidates`; min served share 0.5; swap-only sites need a C / SC object: True; wall 44.7 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Protocol

Candidates ['L01', 'L02', 'L03', 'L04']; scenarios seeds [0, 1] (p = 1/2); 6 bikes; option grid [('S', 1, 0), ('S', 2, 0), ('SC', 1, 1), ('SC', 2, 1)]; roles ['S', 'SC']; swap-only sites need a C / SC object: True; superset bound per scenario [666.3, 631.758] (ObjBound of the all-open relaxed-target model); (B) with scenario-by-scenario pruning and baseline-value ordering, (A) warm-started from (B)'s optimum. Agreement rule: |V_A - V_B| <= 1e-6 + gap_A |V_A| + sum_s p_s gap_s |OPEX_s| (exact when all gaps are 0 and (B) has full coverage), otherwise V_B within [bound_A, incumbent_A].

## Budget m = 1 (52,150 USD): all enumerated layouts (B)

| layout_key | investment | C_setup | status | V | lower_bound | statuses | gaps | served_share | solve_s | error |
|---|---|---|---|---|---|---|---|---|---|---|
| L02:SC:B2:C1 | 51300 | 12.776 | OK | 676.223 | 676.223 | ["TIME_LIMIT", "OPTIMAL"] | [0.014454186217251655, 0.0] | 0.819 | [300.1, 42.2] | - |
| L01:SC:B2:C1 | 51300 | 12.776 | OK | 679.595 | 679.595 | ["TIME_LIMIT", "TIME_LIMIT"] | [0.013065939779174139, 0.009743416360502027] | 0.792 | [300.0, 300.1] | - |
| L03:SC:B2:C1 | 51300 | 12.776 | OK | 680.915 | 680.915 | ["TIME_LIMIT", "TIME_LIMIT"] | [0.015852209758559617, 0.007824280218677898] | 0.792 | [300.1, 300.1] | - |
| L01:SC:B1:C1 | 50850 | 12.444 | OK | 728.996 | 728.996 | ["OPTIMAL", "OPTIMAL"] | [0.0, 0.0] | 0.681 | [28.9, 45.8] | - |
| L03:SC:B1:C1 | 50850 | 12.444 | OK | 730.497 | 730.497 | ["OPTIMAL", "OPTIMAL"] | [0.0, 5.037210056962207e-05] | 0.681 | [29.3, 62.1] | - |
| L04:SC:B1:C1 | 50850 | 12.444 | OK | 745.995 | 745.995 | ["OPTIMAL", "OPTIMAL"] | [0.0, 0.0] | 0.639 | [29.9, 27.6] | - |
| L04:SC:B2:C1 | 51300 | 12.776 | PRUNED | - | 676.563 | ["OPTIMAL"] | [0.0] | 0.750 | [98.0] | - |
| L02:SC:B1:C1 | 50850 | 12.444 | PRUNED | - | 694.588 | ["OPTIMAL"] | [0.0] | 0.667 | [26.4] | - |

## Budget m = 1: agreement (A) vs (B)

| exhaustive_V | exhaustive_layout | integrated_obj | integrated_bound | integrated_gap | integrated_layout | integrated_V_certified | diff | tolerance | exact | agree | same_layout |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 676.223333 | L02:SC:B2:C1 | 676.223333 | 668.036333 | 0.012107 | L02:SC:B2:C1 | 676.223333 | 0 | 13.192132 | False | True | True |

Coverage: {"n_layouts": 8, "solved": 6, "pruned": 2, "skipped_bound": 0, "infeasible": 0, "skipped_budget": 0, "no_incumbent": 0, "error": 0, "full_coverage": true}

## Lower-level solve times (cached ILP rows of this family / candidate set)

{"n": 14, "mean_s": 135.0375634431839, "max_s": 300.0904848575592, "median_s": 62.058449029922485, "n_time_limit": 5}

## Solver statistics

{"n_solves": 16, "n_cache_hits": 4, "n_baseline_runs": 30, "n_errors": 0, "solver_time_s": 1943.5376651287079, "library_time_s": 34.250727373640984, "n_cached_rows": 30, "reposition": "all_candidates"}

## Figures

* `map_budget_1.png`
