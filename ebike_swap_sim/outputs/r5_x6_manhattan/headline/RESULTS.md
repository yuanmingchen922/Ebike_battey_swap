# X6 headline -- ILP vs rule variants (best_rule), relaxed control and written targets

Family `r5_manhattan` (8 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 32.2 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Protocol

Seeds [0, 1, 2]; ILP = aggregated E2 ILP (O1), Threads 3, Seed 0, TimeLimit 300 s (hubs 600 s); rules {'r2': 'baseline', 'r5_range': 'baseline_r5_range', 'r5_transfer': 'baseline_r5_transfer', 'r5': 'baseline_r5', 'r5_selfish': 'baseline_r5_selfish'} (r5_transfer only when the layout has shuttle services); best_rule = per-instance min over ['r2', 'r5_range', 'r5_transfer', 'r5'] by (26) total (end-adjusted columns re-pick the best rule by total_end_adjusted); selfish_eq = follower E (r5_selfish equilibrium). Headline = relaxed control (rho = 0, R_end = 0, common.relax_end_targets); written targets = price of recovery. Gap = 100 (rule - ILP) / rule. Demand md5 asserted per cell.

## Headline (relaxed control, mean over seeds)

| layout_key | labels | n_seeds_ok | relaxed_ilp_total | relaxed_best_rule_total | relaxed_gap_vs_best_rule_pct | relaxed_gap_vs_r2_pct | relaxed_gap_vs_r5_pct | relaxed_gap_vs_best_rule_pct_end_adjusted | relaxed_ilp_C_end_adjust | relaxed_gap_vs_selfish_eq_pct | best_rule_relaxed | ilp_status_relaxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M06:SC:B4:C2|M12:S:B3:C0 | bilevel_chosen, bilevel_m2, bilevel_m3, bilevel_m4 | 3 | 675.011 | 992.812 | 31.807 | 33.502 | 38.921 | 31.725 | 2.050 | 36.151 | r5_range,r2,r2 | OPTIMAL,OPTIMAL,OPTIMAL |
| M07:SC:B3:C1 | policy_aware_m1, policy_aware_m2, policy_aware_m3, policy_aware_m4 | 2 | 867.589 | 1216.175 | 28.652 | 28.652 | 32.314 | 28.641 | 1.019 | 28.652 | r2,r2 | OPTIMAL,OPTIMAL |
| M08:SC:B3:C2 | best_siting_rule_m1(CSAV), present_day_m1 | 3 | 778.081 | 1331.624 | 41.557 | 42.168 | 43.128 | 41.513 | 1.040 | 42.168 | r2,r2,r5_range | OPTIMAL,OPTIMAL,OPTIMAL |
| M08:SC:B3:C2|M09:SC:B3:C2 | best_siting_rule_m2(CSCD) | 3 | 674.963 | 1149.164 | 41.115 | 42.011 | 44.297 | 41.031 | 1.752 | 39.838 | r5_range,r5_transfer,r2 | OPTIMAL,OPTIMAL,OPTIMAL |
| M03:SC:B3:C1|M08:SC:B4:C1 | present_day_m2, present_day_m3, present_day_m4 | 3 | 684.573 | 1027.371 | 32.706 | 36.999 | 37.810 | 32.642 | 1.989 | 36.777 | r5_range,r2,r5_transfer | TIME_LIMIT,OPTIMAL,OPTIMAL |
| M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | best_siting_rule_m3(CSTC) | 3 | 677.907 | 1048.645 | 33.464 | 40.365 | 38.520 | 33.365 | 2.353 | 31.514 | r5,r5_transfer,r2 | OPTIMAL,OPTIMAL,OPTIMAL |
| M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | best_siting_rule_m4(CSTC) | 3 | 689.835 | 994.662 | 29.416 | 39.671 | 35.417 | 29.315 | 2.574 | 27.116 | r5_range,r5_transfer,r5_range | OPTIMAL,OPTIMAL,OPTIMAL |

## Written targets and price of recovery

| layout_key | written_ilp_total | written_best_rule_total | written_gap_vs_best_rule_pct | written_gap_vs_r2_pct | written_ilp_C_end_adjust | written_gap_vs_best_rule_pct_end_adjusted | price_of_recovery_ilp | price_of_recovery_ilp_end_adjusted | price_of_recovery_best_rule |
|---|---|---|---|---|---|---|---|---|---|
| M06:SC:B4:C2|M12:S:B3:C0 | 703.115 | 992.812 | 28.900 | 30.695 | 1.068 | 28.923 | 28.103 | 27.121 | 0 |
| M07:SC:B3:C1 | 928.708 | 1216.175 | 23.629 | 23.629 | 0.448 | 23.670 | 61.120 | 60.549 | 0 |
| M08:SC:B3:C2 | 795.414 | 1331.624 | 40.258 | 40.883 | 0.499 | 40.255 | 17.333 | 16.793 | 0 |
| M08:SC:B3:C2|M09:SC:B3:C2 | 676.582 | 1149.164 | 40.969 | 41.867 | 0.966 | 40.953 | 1.619 | 0.833 | 0 |
| M03:SC:B3:C1|M08:SC:B4:C1 | 723.124 | 1027.371 | 28.734 | 33.204 | 1.068 | 28.769 | 38.551 | 37.630 | 0 |
| M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 679.067 | 1056.661 | 33.874 | 40.261 | 1.146 | 33.880 | 1.159 | -0.048 | 8.016 |
| M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | 690.549 | 1003.838 | 30.265 | 39.607 | 1.752 | 30.246 | 0.714 | -0.109 | 9.176 |

## A3 metric pack (relaxed control; full pack per policy in results.csv)

| layout_key | relaxed_ilp_r5_min_sbur | relaxed_ilp_r5_bsr | relaxed_ilp_r5_outage_rate | relaxed_ilp_r5_empty_km | relaxed_r2_r5_min_sbur | relaxed_r2_r5_bsr | relaxed_r2_r5_outage_rate | relaxed_r2_r5_empty_km |
|---|---|---|---|---|---|---|---|---|
| M06:SC:B4:C2|M12:S:B3:C0 | 1 | 0.697 | 0.417 | 38.800 | 1 | 0.467 | 0.708 | 39.950 |
| M07:SC:B3:C1 | 1.667 | 0.700 | 0.875 | 21.075 | 1.667 | 0.500 | 1 | 54.525 |
| M08:SC:B3:C2 | 2 | 0.778 | 0.625 | 17 | 2 | 0.278 | 1 | 39 |
| M08:SC:B3:C2|M09:SC:B3:C2 | 1.778 | 0.767 | 0.500 | 43.400 | 1.667 | 0.739 | 0.583 | 34.050 |
| M03:SC:B3:C1|M08:SC:B4:C1 | 1.444 | 0.688 | 0.458 | 36 | 1.361 | 0.645 | 0.625 | 43.800 |
| M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 0.889 | 0.710 | 0.375 | 43 | 0.444 | 0.751 | 0.458 | 34.750 |
| M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | 0.444 | 0.697 | 0.458 | 41.250 | 0.111 | 0.739 | 0.458 | 34.450 |

## Solver statistics

{"written": {"n_solves": 4, "n_cache_hits": 38, "n_baseline_runs": 4, "n_errors": 0, "solver_time_s": 632.7898211479187, "library_time_s": 109.04006674955599, "n_cached_rows": 1197, "reposition": "open_sites", "aggregate": true, "variant": {}}, "relaxed": {"n_solves": 21, "n_cache_hits": 0, "n_baseline_runs": 115, "n_errors": 0, "solver_time_s": 992.711576461792, "library_time_s": 99.95123566919938, "n_cached_rows": 1197, "reposition": "open_sites", "aggregate": true, "variant": {}}}
