# R6 levers -- under P 60, w 18, v 15

r5_x5_stress machinery (relaxed control rho 0 / R_end 0, aggregated ILP, Threads 3, Seed 0); best rule = per-instance min over the rules (end-adjusted); mean +- exact t 95 % over seeds; deltas paired per seed.

| lever | cell | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| lockout | lockout0.25 | ilp_ea | 1288.498 | 195.044 | 5 |
| lockout | lockout0.25 | best_ea | 2495.167 | 281.845 | 5 |
| lockout | lockout0.25 | gap_best_ea_pct | 48.390 | 5.053 | 5 |
| lockout | lockout0.25 | delta_ilp_ea | 9.779 | 14.656 | 5 |
| lockout | lockout0.25 | delta_best_ea | 60.112 | 155.859 | 5 |
| lockout | lockout0.25 | ilp_gap | 0.017 | 0.016 | 5 |
| lockout | lockout0.25 | ilp_served_share | 0.925 | 0.048 | 5 |
| reference | reference | ilp_ea | 1278.720 | 191.828 | 5 |
| reference | reference | best_ea | 2435.056 | 173.416 | 5 |
| reference | reference | gap_best_ea_pct | 47.593 | 5.436 | 5 |
| reference | reference | delta_ilp_ea | 0 | 0 | 5 |
| reference | reference | delta_best_ea | 0 | 0 | 5 |
| reference | reference | ilp_gap | 0.012 | 0.013 | 5 |
| reference | reference | ilp_served_share | 0.925 | 0.048 | 5 |
| site_power | P0 | ilp_ea | 1541.676 | 165.999 | 5 |
| site_power | P0 | best_ea | 2648.565 | 114.512 | 5 |
| site_power | P0 | gap_best_ea_pct | 41.871 | 4.009 | 5 |
| site_power | P0 | delta_ilp_ea | 262.957 | 46.151 | 5 |
| site_power | P0 | delta_best_ea | 213.510 | 89.558 | 5 |
| site_power | P0 | ilp_gap | 0.001 | 0.002 | 5 |
| site_power | P0 | ilp_served_share | 0.822 | 0.049 | 5 |

ILP status per lever: P0 {"OPTIMAL": 4, "TIME_LIMIT": 1}; lockout0.25 {"TIME_LIMIT": 4, "OPTIMAL": 1}; reference {"TIME_LIMIT": 4, "OPTIMAL": 1}

## Anomalies

* none

Files: records.jsonl, cases.jsonl, results.csv, cases_wide.csv, summary.csv.

## Retries (r6_fill --retry-unsolved; last row per key wins above, except retry_worse rows, which are ignored and leave the previous row in place)

11 re-solved ILP row(s), 2 now OPTIMAL, 0 worse than the replaced row (kept); improvement = previous total - new total (USD).

| key | retry_reason | prev_status | prev_mip_gap | new_status | new_mip_gap | improved_usd | retry_worse | new_runtime_s | new_time_limit_s | mip_start_variant |
|---|---|---|---|---|---|---|---|---|---|---|
| lockout0.25|s0|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0524 | TIME_LIMIT | 0.0220 | 33.3937 | False | 1800.0763 | 1800 | rule:r5_range@lockout0.25:rho0_R0 |
| reference|s0|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0687 | TIME_LIMIT | 0.0150 | 58.9584 | False | 1800.1096 | 1800 | ilp:lockout0.25:rho0_R0|no_transfers |
| lockout0.25|s1|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0364 | TIME_LIMIT | 0.0223 | 19.9329 | False | 1800.1129 | 1800 | rule:r2@lockout0.25:rho0_R0 |
| reference|s1|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0083 | TIME_LIMIT | 0.0075 | 0 | False | 1800.0643 | 1800 | ilp:lockout0.25:rho0_R0|no_transfers |
| lockout0.25|s2|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0562 | TIME_LIMIT | 0.0326 | 30.2397 | False | 1800.0774 | 1800 | rule:r2@lockout0.25:rho0_R0 |
| P0|s2|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0072 | TIME_LIMIT | 0.0032 | 2.0720 | False | 1810.6109 | 1800 | rule:r5_range@P0:rho0_R0 |
| reference|s2|ILP_tl600 | not_optimal | TIME_LIMIT | 0.1048 | TIME_LIMIT | 0.0287 | 102.7385 | False | 1800.0639 | 1800 | ilp:lockout0.25:rho0_R0|no_transfers |
| lockout0.25|s3|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0123 | TIME_LIMIT | 0.0105 | 2.6760 | False | 1800.0744 | 1800 | rule:r2@lockout0.25:rho0_R0 |
| reference|s3|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0136 | TIME_LIMIT | 0.0100 | 5.4480 | False | 1800.1962 | 1800 | ilp:lockout0.25:rho0_R0|no_transfers |
| lockout0.25|s4|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0039 | OPTIMAL | 0 | 0 | False | 1659.1756 | 1800 | rule:r2@lockout0.25:rho0_R0 |
| reference|s4|ILP_tl600 | not_optimal | TIME_LIMIT | 0.0085 | OPTIMAL | 0 | 7.2053 | False | 1287.6236 | 1800 | ilp:lockout0.25:rho0_R0|no_transfers |

