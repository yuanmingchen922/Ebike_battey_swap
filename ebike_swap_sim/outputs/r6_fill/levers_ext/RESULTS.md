# R6 levers_ext -- station levers on stress4h-K8 under P 60, w 18, v 15

Relaxed control, aggregated ILP, Threads 3, Seed 0, TimeLimit 600 s (reference rows re-solved by --retry-unsolved at 1800 s where present).  Reference, P0 (no on-site charging) and the 2-spare lock-out from r6_penalty/levers; charger speed x2 (eps 50 Wh), second swap position (M 2) and the 1-spare lock-out (shares 0.05 / 0.10 = one battery) from this stage.  Deltas vs the reference paired per seed; mean +- exact t 95 %.

| lever | cell | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| charger_speed | eps50 | ilp_ea | 1277.135 | 197.696 | 5 |
| charger_speed | eps50 | best_ea | 2125.824 | 348.816 | 5 |
| charger_speed | eps50 | gap_best_ea_pct | 39.845 | 1.797 | 5 |
| charger_speed | eps50 | delta_ilp_ea | -1.584 | 13.213 | 5 |
| charger_speed | eps50 | delta_best_ea | -309.231 | 238.829 | 5 |
| charger_speed | eps50 | ilp_gap | 0.006 | 0.014 | 5 |
| lockout | lockout0.05 | ilp_ea | 1290.510 | 190.384 | 5 |
| lockout | lockout0.05 | best_ea | 2475.831 | 240.224 | 5 |
| lockout | lockout0.05 | gap_best_ea_pct | 47.944 | 4.884 | 5 |
| lockout | lockout0.05 | delta_ilp_ea | 11.791 | 17.131 | 5 |
| lockout | lockout0.05 | delta_best_ea | 40.775 | 102.317 | 5 |
| lockout | lockout0.05 | ilp_gap | 0.021 | 0.025 | 5 |
| lockout | lockout0.1 | ilp_ea | 1290.510 | 190.384 | 5 |
| lockout | lockout0.1 | best_ea | 2475.831 | 240.224 | 5 |
| lockout | lockout0.1 | gap_best_ea_pct | 47.944 | 4.884 | 5 |
| lockout | lockout0.1 | delta_ilp_ea | 11.791 | 17.131 | 5 |
| lockout | lockout0.1 | delta_best_ea | 40.775 | 102.317 | 5 |
| lockout | lockout0.1 | ilp_gap | 0.021 | 0.025 | 5 |
| lockout | lockout0.25 | ilp_ea | 1288.498 | 195.044 | 5 |
| lockout | lockout0.25 | best_ea | 2495.167 | 281.845 | 5 |
| lockout | lockout0.25 | gap_best_ea_pct | 48.390 | 5.053 | 5 |
| lockout | lockout0.25 | delta_ilp_ea | 9.779 | 14.656 | 5 |
| lockout | lockout0.25 | delta_best_ea | 60.112 | 155.859 | 5 |
| lockout | lockout0.25 | ilp_gap | 0.017 | 0.016 | 5 |
| reference | reference | ilp_ea | 1278.720 | 191.828 | 5 |
| reference | reference | best_ea | 2435.056 | 173.416 | 5 |
| reference | reference | gap_best_ea_pct | 47.593 | 5.436 | 5 |
| reference | reference | delta_ilp_ea | 0 | 0 | 5 |
| reference | reference | delta_best_ea | 0 | 0 | 5 |
| reference | reference | ilp_gap | 0.012 | 0.013 | 5 |
| site_power | P0 | ilp_ea | 1541.676 | 165.999 | 5 |
| site_power | P0 | best_ea | 2648.565 | 114.512 | 5 |
| site_power | P0 | gap_best_ea_pct | 41.871 | 4.009 | 5 |
| site_power | P0 | delta_ilp_ea | 262.957 | 46.151 | 5 |
| site_power | P0 | delta_best_ea | 213.510 | 89.558 | 5 |
| site_power | P0 | ilp_gap | 0.001 | 0.002 | 5 |
| swap_positions | M2 | ilp_ea | 1312.197 | 163.962 | 5 |
| swap_positions | M2 | best_ea | 2437.458 | 176.200 | 5 |
| swap_positions | M2 | gap_best_ea_pct | 46.232 | 4.251 | 5 |
| swap_positions | M2 | delta_ilp_ea | 33.478 | 31.497 | 5 |
| swap_positions | M2 | delta_best_ea | 2.402 | 6.340 | 5 |
| swap_positions | M2 | ilp_gap | 0.040 | 0.037 | 5 |

ILP status per cell: M2 {"TIME_LIMIT": 5}; P0 {"OPTIMAL": 4, "TIME_LIMIT": 1}; eps50 {"OPTIMAL": 3, "TIME_LIMIT": 2}; lockout0.05 {"TIME_LIMIT": 5}; lockout0.1 {"TIME_LIMIT": 5}; lockout0.25 {"TIME_LIMIT": 4, "OPTIMAL": 1}; reference {"TIME_LIMIT": 4, "OPTIMAL": 1}

## Site power cap with the demand-charge proxy (P_j in {0, p_ch}; tariffs are assumptions)

| policy | usd_per_kw_month | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| best_rule | 10 | V_P0 | 2646.55 | 114.50 | 5 |
| best_rule | 10 | V_Pch | 2433.57 | 173.41 | 5 |
| best_rule | 10 | best_P_kw | 0.33 | 0 | 5 |
| best_rule | 10 | best_total | 2433.66 | 173.41 | 5 |
| best_rule | 25 | V_P0 | 2646.55 | 114.50 | 5 |
| best_rule | 25 | V_Pch | 2433.57 | 173.41 | 5 |
| best_rule | 25 | best_P_kw | 0.33 | 0 | 5 |
| best_rule | 25 | best_total | 2433.78 | 173.41 | 5 |
| best_rule | 40 | V_P0 | 2646.55 | 114.50 | 5 |
| best_rule | 40 | V_Pch | 2433.57 | 173.41 | 5 |
| best_rule | 40 | best_P_kw | 0.33 | 0 | 5 |
| best_rule | 40 | best_total | 2433.91 | 173.41 | 5 |
| ilp | 10 | V_P0 | 1539.30 | 166.01 | 5 |
| ilp | 10 | V_Pch | 1276.61 | 191.91 | 5 |
| ilp | 10 | best_P_kw | 0.33 | 0 | 5 |
| ilp | 10 | best_total | 1276.69 | 191.91 | 5 |
| ilp | 25 | V_P0 | 1539.30 | 166.01 | 5 |
| ilp | 25 | V_Pch | 1276.61 | 191.91 | 5 |
| ilp | 25 | best_P_kw | 0.33 | 0 | 5 |
| ilp | 25 | best_total | 1276.82 | 191.91 | 5 |
| ilp | 40 | V_P0 | 1539.30 | 166.01 | 5 |
| ilp | 40 | V_Pch | 1276.61 | 191.91 | 5 |
| ilp | 40 | best_P_kw | 0.33 | 0 | 5 |
| ilp | 40 | best_total | 1276.94 | 191.91 | 5 |

## Anomalies

* none

Files: records.jsonl, cases.jsonl, results.csv, cases_wide_joined.csv, summary.csv, demand_charge_proxy.csv.
