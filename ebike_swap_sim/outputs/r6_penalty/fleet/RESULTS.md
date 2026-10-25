# R6 fleet -- under P 60, w 18, v 15

r5_x5_stress machinery (relaxed control rho 0 / R_end 0, aggregated ILP, Threads 3, Seed 0); best rule = per-instance min over the rules (end-adjusted); mean +- exact t 95 % over seeds; deltas paired per seed.

## Cost-minimal design within the grid (system cost = end-adjusted total incl. spare set-up (27) + K x allocated bike + rider cost per window)

| policy | K | B_per_site | system_cost_mean | system_cost_ci95 | served_share_mean | n_seeds | per_seed_argmin |
|---|---|---|---|---|---|---|---|
| best_rule | 8 | 4 | 1619.60 | 363.43 | 0.98 | 3 | {"0": "K8_B4", "1": "K8_B4", "2": "K10_B4"} |
| ilp | 8 | 3 | 1477.89 | 170.24 | 0.99 | 3 | {"0": "K6_B2", "1": "K8_B2", "2": "K8_B3"} |

## Grid means

| K | B_per_site | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| 4 | 1 | best_system_cost | 2582.73 | 79.35 | 3 |
| 4 | 1 | ilp_system_cost | 1740.01 | 359.61 | 3 |
| 4 | 1 | ilp_served_share | 0.74 | 0.13 | 3 |
| 4 | 1 | gap_best_ea_pct | 37.89 | 14.38 | 3 |
| 4 | 2 | best_system_cost | 2387.26 | 288.48 | 3 |
| 4 | 2 | ilp_system_cost | 1729.04 | 339.91 | 3 |
| 4 | 2 | ilp_served_share | 0.74 | 0.11 | 3 |
| 4 | 2 | gap_best_ea_pct | 32.50 | 8.25 | 3 |
| 4 | 3 | best_system_cost | 2385.16 | 400.06 | 3 |
| 4 | 3 | ilp_system_cost | 1729.01 | 337.94 | 3 |
| 4 | 3 | ilp_served_share | 0.74 | 0.11 | 3 |
| 4 | 3 | gap_best_ea_pct | 32.37 | 7.97 | 3 |
| 4 | 4 | best_system_cost | 2386.14 | 400.12 | 3 |
| 4 | 4 | ilp_system_cost | 1730.01 | 337.92 | 3 |
| 4 | 4 | ilp_served_share | 0.74 | 0.11 | 3 |
| 4 | 4 | gap_best_ea_pct | 32.35 | 7.96 | 3 |
| 6 | 1 | best_system_cost | 2616.70 | 300.02 | 3 |
| 6 | 1 | ilp_system_cost | 1514.20 | 396.14 | 3 |
| 6 | 1 | ilp_served_share | 0.92 | 0.12 | 3 |
| 6 | 1 | gap_best_ea_pct | 53.09 | 13.84 | 3 |
| 6 | 2 | best_system_cost | 2066.84 | 753.42 | 3 |
| 6 | 2 | ilp_system_cost | 1478.45 | 338.14 | 3 |
| 6 | 2 | ilp_served_share | 0.94 | 0.12 | 3 |
| 6 | 2 | gap_best_ea_pct | 37.86 | 9.97 | 3 |
| 6 | 3 | best_system_cost | 2012.82 | 741.39 | 3 |
| 6 | 3 | ilp_system_cost | 1478.79 | 336.76 | 3 |
| 6 | 3 | ilp_served_share | 0.94 | 0.12 | 3 |
| 6 | 3 | gap_best_ea_pct | 35.52 | 10.79 | 3 |
| 6 | 4 | best_system_cost | 1977.66 | 657.36 | 3 |
| 6 | 4 | ilp_system_cost | 1479.70 | 336.58 | 3 |
| 6 | 4 | ilp_served_share | 0.94 | 0.12 | 3 |
| 6 | 4 | gap_best_ea_pct | 34.11 | 7.61 | 3 |
| 8 | 1 | best_system_cost | 2438.71 | 679.18 | 3 |
| 8 | 1 | ilp_system_cost | 1546.90 | 326.58 | 3 |
| 8 | 1 | ilp_served_share | 0.97 | 0.08 | 3 |
| 8 | 1 | gap_best_ea_pct | 51.63 | 3.80 | 3 |
| 8 | 2 | best_system_cost | 1912.75 | 931.26 | 3 |
| 8 | 2 | ilp_system_cost | 1478.14 | 171.42 | 3 |
| 8 | 2 | ilp_served_share | 0.99 | 0.03 | 3 |
| 8 | 2 | gap_best_ea_pct | 32.56 | 43.25 | 3 |
| 8 | 3 | best_system_cost | 1698.88 | 529.53 | 3 |
| 8 | 3 | ilp_system_cost | 1477.89 | 170.24 | 3 |
| 8 | 3 | ilp_served_share | 0.99 | 0.03 | 3 |
| 8 | 3 | gap_best_ea_pct | 20.63 | 30.82 | 3 |
| 8 | 4 | best_system_cost | 1619.60 | 363.43 | 3 |
| 8 | 4 | ilp_system_cost | 1478.63 | 169.92 | 3 |
| 8 | 4 | ilp_served_share | 0.99 | 0.03 | 3 |
| 8 | 4 | gap_best_ea_pct | 14.71 | 20.28 | 3 |
| 10 | 1 | best_system_cost | 2496.36 | 624.25 | 3 |
| 10 | 1 | ilp_system_cost | 1660.53 | 200.29 | 3 |
| 10 | 1 | ilp_served_share | 0.99 | 0.03 | 3 |
| 10 | 1 | gap_best_ea_pct | 51.74 | 6.59 | 3 |
| 10 | 2 | best_system_cost | 1992.81 | 776.86 | 3 |
| 10 | 2 | ilp_system_cost | 1661.95 | 210.32 | 3 |
| 10 | 2 | ilp_served_share | 0.99 | 0.03 | 3 |
| 10 | 2 | gap_best_ea_pct | 26.91 | 40.94 | 3 |
| 10 | 3 | best_system_cost | 1717.37 | 231.54 | 3 |
| 10 | 3 | ilp_system_cost | 1621.49 | 127.54 | 3 |
| 10 | 3 | ilp_served_share | 0.99 | 0.03 | 3 |
| 10 | 3 | gap_best_ea_pct | 11.12 | 18.62 | 3 |
| 10 | 4 | best_system_cost | 1677.02 | 167.71 | 3 |
| 10 | 4 | ilp_system_cost | 1622.42 | 127.62 | 3 |
| 10 | 4 | ilp_served_share | 0.99 | 0.03 | 3 |
| 10 | 4 | gap_best_ea_pct | 6.85 | 3.67 | 3 |

## Anomalies

* none

Files: records.jsonl, cases.jsonl, results.csv, cases_wide.csv, summary.csv, cost_minimal_design.csv, fleet_frontier.csv.

## Retries (r6_fill --retry-unsolved; last row per key wins above, except retry_worse rows, which are ignored and leave the previous row in place)

16 re-solved ILP row(s), 1 now OPTIMAL, 3 worse than the replaced row (kept); improvement = previous total - new total (USD).

| key | retry_reason | prev_status | prev_mip_gap | new_status | new_mip_gap | improved_usd | retry_worse | new_runtime_s | new_time_limit_s | mip_start_variant |
|---|---|---|---|---|---|---|---|---|---|---|
| K4_B1_pack0.6|s0|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0088 | TIME_LIMIT | 0.0104 | 0 | False | 600.0506 | 600 | rule:r5_range@K4_B1_pack0.6:rho0_R0 |
| K4_B2_pack0.6|s0|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0081 | TIME_LIMIT | 0.0086 | 0 | False | 600.0741 | 600 | ilp:K4_B1_pack0.6:rho0_R0 |
| K4_B3_pack0.6|s0|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0072 | TIME_LIMIT | 0.0076 | 0 | False | 600.0695 | 600 | ilp:K4_B2_pack0.6:rho0_R0 |
| K4_B4_pack0.6|s0|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0079 | TIME_LIMIT | 0.0062 | 0 | False | 600.1949 | 600 | ilp:K4_B3_pack0.6:rho0_R0 |
| K6_B1_pack0.6|s0|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0130 | TIME_LIMIT | 0.0087 | 4.2537 | False | 600.0385 | 600 | rule:r5_range@K6_B1_pack0.6:rho0_R0 |
| K4_B1_pack0.6|s1|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0156 | TIME_LIMIT | 0.0153 | -3.2651 | True | 600.0354 | 600 | rule:r2@K4_B1_pack0.6:rho0_R0 |
| K4_B2_pack0.6|s1|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0121 | TIME_LIMIT | 0.0090 | 2.2336 | False | 600.0403 | 600 | ilp:K4_B1_pack0.6:rho0_R0 |
| K4_B3_pack0.6|s1|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0100 | TIME_LIMIT | 0.0050 | 2.0740 | False | 600.0430 | 600 | ilp:K4_B2_pack0.6:rho0_R0 |
| K4_B4_pack0.6|s1|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0097 | TIME_LIMIT | 0.0033 | 2.0380 | False | 600.0741 | 600 | ilp:K4_B3_pack0.6:rho0_R0 |
| K6_B1_pack0.6|s1|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0154 | TIME_LIMIT | 0.0240 | -9.2722 | True | 600.0618 | 600 | rule:r5_range@K6_B1_pack0.6:rho0_R0 |
| K6_B2_pack0.6|s1|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0094 | TIME_LIMIT | 0.0081 | 1.5167 | False | 600.0675 | 600 | ilp:K6_B1_pack0.6:rho0_R0 |
| K6_B3_pack0.6|s1|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0063 | TIME_LIMIT | 0.0074 | -1.1060 | True | 600.0909 | 600 | ilp:K6_B2_pack0.6:rho0_R0 |
| K10_B1_pack0.6|s2|ILP_tl600 | sleep_truncated | TIME_LIMIT | 0.0231 | OPTIMAL | 0 | 10.8352 | False | 565.2196 | 600 | rule:r5_range@K10_B1_pack0.6:rho0_R0 |
| K6_B1_pack0.6|s2|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0121 | TIME_LIMIT | 0.0076 | 1.0340 | False | 600.0380 | 600 | rule:r5_range@K6_B1_pack0.6:rho0_R0 |
| K6_B2_pack0.6|s2|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0114 | TIME_LIMIT | 0.0054 | 5.0700 | False | 600.0398 | 600 | ilp:K6_B1_pack0.6:rho0_R0 |
| K6_B3_pack0.6|s2|ILP_tl300 | not_optimal | TIME_LIMIT | 0.0064 | TIME_LIMIT | 0.0035 | 0 | False | 600.0444 | 600 | ilp:K6_B2_pack0.6:rho0_R0 |

