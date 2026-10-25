# R6 stress -- stressed family, price of recovery, boundary grid, LP shadow prices (P 60, w 18, v 15)

r5_x5_stress machinery on the repriced instances (aggregated ILP, Threads 3, Seed 0; identical cells solved once by content key).  best rule = per-instance min over the rules (end-adjusted); mean +- exact t 95 % over seeds; deltas paired per seed.

## Core cells (relaxed control) and the K6 written cell

| cell | target | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| r5_stress4h_K6 | written | ilp_ea | 938.817 | 177.554 | 4 |
| r5_stress4h_K6 | written | best_ea | 1581.761 | 292.357 | 5 |
| r5_stress4h_K6 | written | gap_best_ea_pct | 38.781 | 6.200 | 4 |
| r5_stress4h_K6 | written | ilp_gap | 0.018 | 0.034 | 4 |
| r5_stress4h_K6 | written | ilp_served_share | 0.948 | 0.063 | 4 |
| r5_stress4h_k10_K10 | rho0_R0 | ilp_ea | 1612.862 | 226.031 | 5 |
| r5_stress4h_k10_K10 | rho0_R0 | best_ea | 3233.831 | 324.363 | 5 |
| r5_stress4h_k10_K10 | rho0_R0 | gap_best_ea_pct | 50.211 | 3.221 | 5 |
| r5_stress4h_k10_K10 | rho0_R0 | ilp_gap | 0.070 | 0.051 | 5 |
| r5_stress4h_k10_K10 | rho0_R0 | ilp_served_share | 0.907 | 0.049 | 5 |
| r5_stress8h_K6 | rho0_R0 | ilp_ea | 1965.903 | 528.209 | 3 |
| r5_stress8h_K6 | rho0_R0 | best_ea | 3570.438 | 2451.443 | 3 |
| r5_stress8h_K6 | rho0_R0 | gap_best_ea_pct | 42.771 | 29.262 | 3 |
| r5_stress8h_K6 | rho0_R0 | ilp_gap | 0.072 | 0.053 | 3 |
| r5_stress8h_K6 | rho0_R0 | ilp_served_share | 0.910 | 0.105 | 3 |

ILP status: ('r5_stress4h_K6', 'written') {"TIME_LIMIT": 4, "OPTIMAL": 1}; ('r5_stress4h_k10_K10', 'rho0_R0') {"TIME_LIMIT": 5}; ('r5_stress8h_K6', 'rho0_R0') {"TIME_LIMIT": 3}

## Price of recovery on stress4h 6 bikes (ILP written - ILP relaxed, end-adjusted)

| seed | written_ea | relaxed_ea | relaxed_source | written_status | relaxed_status | price_of_recovery_end_adjusted | price_of_recovery | lp_spare_written | lp_charger_written |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 787.74 | 787.83 | stress | OPTIMAL | OPTIMAL | -0.09 | 0.77 | 0.31 | 0 |
| 1 | 1035.54 | 1033.05 | stress | TIME_LIMIT | TIME_LIMIT | 2.49 | 3.26 | 2.28 | 0.46 |
| 2 | - | 1020.59 | stress | TIME_LIMIT | TIME_LIMIT | - | - | 2.02 | 1.50 |
| 3 | 1008.99 | 958.82 | psweep | TIME_LIMIT | TIME_LIMIT | 50.16 | 50.70 | 4.86 | 1.37 |
| 4 | 923.00 | 913.79 | psweep | TIME_LIMIT | OPTIMAL | 9.21 | 9.97 | 1.90 | 0.42 |

mean 15.45 +- 37.35 USD (n 4).

## Boundary grid (rho x R_end + periodic) on stress4h 6 bikes seeds 0-2: price of recovery vs rho0_R0 (paired)

| target | metric | mean | ci95 | n |
|---|---|---|---|---|
| periodic | price_of_recovery | 143.640 | - | 1 |
| periodic | price_of_recovery_end_adjusted | 142.302 | - | 1 |
| periodic | ilp_gap | 0.080 | - | 1 |
| rho0.25_R0 | price_of_recovery | 243.917 | 1030.789 | 3 |
| rho0.25_R0 | price_of_recovery_end_adjusted | 243.274 | 1030.639 | 3 |
| rho0.25_R0 | ilp_gap | 0.146 | 0.592 | 3 |
| rho0.25_R1 | price_of_recovery | 2.015 | 15.771 | 2 |
| rho0.25_R1 | price_of_recovery_end_adjusted | 1.204 | 16.395 | 2 |
| rho0.25_R1 | ilp_gap | 0.006 | 0.073 | 2 |
| rho0.5_R0 | price_of_recovery | -0.282 | 13.413 | 2 |
| rho0.5_R0 | price_of_recovery_end_adjusted | -1.092 | 12.789 | 2 |
| rho0.5_R0 | ilp_gap | 0.004 | 0.046 | 2 |
| rho0.5_R1 | price_of_recovery | 2.015 | 15.771 | 2 |
| rho0.5_R1 | price_of_recovery_end_adjusted | 1.204 | 16.395 | 2 |
| rho0.5_R1 | ilp_gap | 0.006 | 0.073 | 2 |
| rho0_R0 | price_of_recovery | 0 | 0 | 3 |
| rho0_R0 | price_of_recovery_end_adjusted | 0 | 0 | 3 |
| rho0_R0 | ilp_gap | 0.007 | 0.015 | 3 |
| rho0_R1 | price_of_recovery | 2.015 | 15.771 | 2 |
| rho0_R1 | price_of_recovery_end_adjusted | 1.204 | 16.395 | 2 |
| rho0_R1 | ilp_gap | 0.006 | 0.073 | 2 |
| rho1_R1 | price_of_recovery | 118.401 | 619.069 | 2 |
| rho1_R1 | price_of_recovery_end_adjusted | 116.872 | 621.643 | 2 |
| rho1_R1 | ilp_gap | 0.090 | 0.107 | 2 |

## LP shadow prices: operating value of one more spare / charger per site (USD per window)

| cell | target | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| r5_stress4h_K6 | rho0.5_R1 | LP_lp_spare_value_mean | 1.538 | 2.651 | 3 |
| r5_stress4h_K6 | rho0.5_R1 | LP_lp_charger_value_mean | 0.653 | 1.911 | 3 |
| r5_stress4h_K6 | rho0_R0 | LP_lp_spare_value_mean | 0.703 | 0.533 | 5 |
| r5_stress4h_K6 | rho0_R0 | LP_lp_charger_value_mean | 0.029 | 0.052 | 5 |
| r5_stress4h_K6 | written | LP_lp_spare_value_mean | 2.276 | 2.035 | 5 |
| r5_stress4h_K6 | written | LP_lp_charger_value_mean | 0.750 | 0.812 | 5 |
| r5_stress4h_k10_K10 | rho0_R0 | LP_lp_spare_value_mean | 77.952 | 39.651 | 5 |
| r5_stress4h_k10_K10 | rho0_R0 | LP_lp_charger_value_mean | 65.864 | 36.163 | 5 |
| r5_stress4h_k8_K8 | rho0_R0 | LP_lp_spare_value_mean | 9.808 | 5.171 | 5 |
| r5_stress4h_k8_K8 | rho0_R0 | LP_lp_charger_value_mean | 8.780 | 6.184 | 5 |
| r5_stress8h_K6 | rho0_R0 | LP_lp_spare_value_mean | 1.248 | 1.512 | 3 |
| r5_stress8h_K6 | rho0_R0 | LP_lp_charger_value_mean | 0.408 | 1.010 | 3 |

## Anomalies

* none

Files: records.jsonl, cases.jsonl, results.csv, cases_wide.csv, summary_core.csv, price_of_recovery.csv, summary_boundary.csv, summary_lp.csv.
