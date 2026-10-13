# E2u round 3 -- coordination value with the service-share constraint (33), seeds 0-9

Family `usd4h` (usd_sunk), demand x0.75 / x1 / x1.5, seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]; methods ['baseline', 'ilp', 'ilp_zeta90', 'ilp_zeta85', 'ilp_relaxed']; zeta 0.90 (main) / 0.85 (sensitivity); Gurobi Threads 3, TimeLimit 300 s, Seed 0; rows with `source = round2` are reused round-2 records (OPTIMAL or gap <= 1 %), `solve_mode = implied_by_written` cells are certified written optima that already serve >= zeta |I| orders (no solve needed), `implied_by_max_service` cells are infeasible by the certified maximum share of the zeta-0.90 run. Gap = 100 (baseline - ILP) / baseline, mean over seeds, 95 % t-CI.

## Gap per method and demand level
| comparison | demand_mult | n | gap_mean_pct | gap_ci95_pct | gap_lo_pct | gap_hi_pct | abs_gain_mean | policy_total_mean | ilp_total_mean |
|---|---|---|---|---|---|---|---|---|---|
| ILP (written, rho 0.5, R_end 1) vs baseline R2.3 | 0.75 | 10 | 15.36 | 7.28 | 8.08 | 22.63 | 97.31 | 577.41 | 480.10 |
| ILP (written, rho 0.5, R_end 1) vs baseline R2.3 | 1 | 10 | 31.18 | 9.05 | 22.14 | 40.23 | 333.95 | 992.54 | 658.59 |
| ILP (written, rho 0.5, R_end 1) vs baseline R2.3 | 1.50 | 10 | 42.11 | 5.66 | 36.45 | 47.77 | 831.85 | 1930.28 | 1098.43 |
| ILP (written, rho 0.5, R_end 1) vs baseline R2.3 | all | 30 | 29.55 | 5.38 | 24.17 | 34.93 | 421.04 | 1166.74 | 745.71 |
| ILP + (33) zeta 0.90 vs baseline R2.3 | 0.75 | 10 | 15.20 | 7.26 | 7.94 | 22.46 | 96.38 | 577.41 | 481.03 |
| ILP + (33) zeta 0.90 vs baseline R2.3 | 1 | 10 | 27.76 | 8.66 | 19.10 | 36.42 | 296.56 | 992.54 | 695.98 |
| ILP + (33) zeta 0.90 vs baseline R2.3 | 1.50 | 0 | - | - | - | - | - | - | - |
| ILP + (33) zeta 0.90 vs baseline R2.3 | all | 20 | 21.48 | 5.54 | 15.94 | 27.02 | 196.47 | 784.97 | 588.50 |
| ILP + (33) zeta 0.85 vs baseline R2.3 | 0.75 | 10 | 15.36 | 7.28 | 8.08 | 22.63 | 97.31 | 577.41 | 480.10 |
| ILP + (33) zeta 0.85 vs baseline R2.3 | 1 | 10 | 30.58 | 8.59 | 21.99 | 39.16 | 325.95 | 992.54 | 666.58 |
| ILP + (33) zeta 0.85 vs baseline R2.3 | 1.50 | 0 | - | - | - | - | - | - | - |
| ILP + (33) zeta 0.85 vs baseline R2.3 | all | 20 | 22.97 | 5.85 | 17.12 | 28.82 | 211.63 | 784.97 | 573.34 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | 0.75 | 10 | 15.39 | 7.28 | 8.11 | 22.66 | 97.49 | 577.41 | 479.92 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | 1 | 10 | 31.22 | 9.03 | 22.19 | 40.26 | 334.31 | 992.54 | 658.23 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | 1.50 | 10 | 42.14 | 5.66 | 36.48 | 47.79 | 832.33 | 1930.28 | 1097.95 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | all | 30 | 29.58 | 5.38 | 24.21 | 34.96 | 421.37 | 1166.74 | 745.37 |

Zeta rows enter the gap only when they have a total (feasible); INFEASIBLE cells are listed below.

## Service-share feasibility (zeta runs)
| name | seed | demand_mult | n_orders | method | zeta | zeta_min_served | status | solve_mode | zeta_feasible | total | n_unserved | served_share | mip_gap | runtime_s | ms_status | ms_min_unserved | ms_min_unserved_bound | ms_share_achievable | ms_share_upper_bound | ms_certified | ms_n_unservable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h-K6-I27-seed0-x0.75 | 0 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 443.904 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed0-x0.75 | 0 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | implied_by_written | True | 443.904 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed1-x0.75 | 1 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 471.022 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed1-x0.75 | 1 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | implied_by_written | True | 471.022 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed2-x0.75 | 2 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 462.867 | 0 | 1 | 0.000 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed2-x0.75 | 2 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | implied_by_written | True | 462.867 | 0 | 1 | 0.000 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed3-x0.75 | 3 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 497.321 | 3 | 0.889 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed3-x0.75 | 3 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | solved | True | 502.667 | 2 | 0.926 | 0.000 | 70.148 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed4-x0.75 | 4 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 459.185 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed4-x0.75 | 4 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | implied_by_written | True | 459.185 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed5-x0.75 | 5 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 510.695 | 2 | 0.926 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed5-x0.75 | 5 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | implied_by_written | True | 510.695 | 2 | 0.926 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed6-x0.75 | 6 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 501.226 | 3 | 0.889 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed6-x0.75 | 6 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | solved | True | 501.730 | 2 | 0.926 | 0 | 69.035 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed7-x0.75 | 7 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 488.438 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed7-x0.75 | 7 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | implied_by_written | True | 488.438 | 1 | 0.963 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed8-x0.75 | 8 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 499.215 | 3 | 0.889 | 0.000 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed8-x0.75 | 8 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | solved | True | 502.719 | 2 | 0.926 | 0 | 94.729 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed9-x0.75 | 9 | 0.750 | 27 | ilp_zeta85 | 0.850 | 23 | OPTIMAL | implied_by_written | True | 467.114 | 0 | 1 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I27-seed9-x0.75 | 9 | 0.750 | 27 | ilp_zeta90 | 0.900 | 25 | OPTIMAL | implied_by_written | True | 467.114 | 0 | 1 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed0-x1 | 0 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | solved | True | 615.146 | 1 | 0.972 | 0 | 137.862 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed0-x1 | 0 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 615.146 | 1 | 0.972 | 0 | 127.275 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed1-x1 | 1 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | implied_by_written | True | 659.601 | 5 | 0.861 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed1-x1 | 1 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 688.257 | 3 | 0.917 | 0 | 130.328 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed2-x1 | 2 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | implied_by_written | True | 638.979 | 4 | 0.889 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed2-x1 | 2 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 703.713 | 3 | 0.917 | 0.000 | 144.019 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed3-x1 | 3 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | implied_by_written | True | 662.630 | 5 | 0.861 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed3-x1 | 3 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 708.673 | 3 | 0.917 | 0 | 129.021 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed4-x1 | 4 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | implied_by_written | True | 614.781 | 3 | 0.917 | 0.000 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed4-x1 | 4 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | implied_by_written | True | 614.781 | 3 | 0.917 | 0.000 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed5-x1 | 5 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | implied_by_written | True | 657.005 | 4 | 0.889 | 0 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed5-x1 | 5 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 673.154 | 3 | 0.917 | 0 | 79.744 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed6-x1 | 6 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | solved | True | 680.959 | 5 | 0.861 | 0 | 89.410 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed6-x1 | 6 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | TIME_LIMIT | solved | True | 714.291 | 3 | 0.917 | 0.000 | 300.071 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed7-x1 | 7 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | implied_by_written | True | 684.553 | 5 | 0.861 | 0.000 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed7-x1 | 7 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 689.241 | 3 | 0.917 | 0.000 | 81.594 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed8-x1 | 8 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | solved | True | 795.642 | 5 | 0.861 | 0 | 142.895 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed8-x1 | 8 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 894.581 | 3 | 0.917 | 0 | 56.436 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed9-x1 | 9 | 1 | 36 | ilp_zeta85 | 0.850 | 31 | OPTIMAL | implied_by_written | True | 656.545 | 4 | 0.889 | 0.000 | 0 | - | - | - | - | - | - | - |
| usd4h-K6-I36-seed9-x1 | 9 | 1 | 36 | ilp_zeta90 | 0.900 | 33 | OPTIMAL | solved | True | 657.913 | 3 | 0.917 | 0.000 | 107.399 | - | - | - | - | - | - | - |
| usd4h-K6-I54-seed0-x1.5 | 0 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | TIME_LIMIT | solved | - | - | - | - | - | 300.053 | TIME_LIMIT | 17 | 9 | 0.685 | 0.833 | False | 1 |
| usd4h-K6-I54-seed0-x1.5 | 0 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | - | - | - | - | - | 300.056 | TIME_LIMIT | 17 | 9 | 0.685 | 0.833 | False | 1 |
| usd4h-K6-I54-seed1-x1.5 | 1 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | TIME_LIMIT | solved | - | - | - | - | - | 300.051 | TIME_LIMIT | 14 | 13 | 0.741 | 0.759 | False | 1 |
| usd4h-K6-I54-seed1-x1.5 | 1 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | - | - | - | - | - | 300.074 | TIME_LIMIT | 14 | 13 | 0.741 | 0.759 | False | 1 |
| usd4h-K6-I54-seed2-x1.5 | 2 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | INFEASIBLE | solved | False | - | - | - | - | 247.711 | TIME_LIMIT | 20 | 13 | 0.630 | 0.759 | False | 2 |
| usd4h-K6-I54-seed2-x1.5 | 2 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | INFEASIBLE | solved | False | - | - | - | - | 213.734 | TIME_LIMIT | 20 | 13 | 0.630 | 0.759 | False | 2 |
| usd4h-K6-I54-seed3-x1.5 | 3 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | INFEASIBLE | implied_by_max_service | False | - | - | - | - | 0 | OPTIMAL | 14 | 14 | 0.741 | 0.741 | True | 1 |
| usd4h-K6-I54-seed3-x1.5 | 3 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | False | - | - | - | - | 300.051 | OPTIMAL | 14 | 14 | 0.741 | 0.741 | True | 1 |
| usd4h-K6-I54-seed4-x1.5 | 4 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | INFEASIBLE | implied_by_max_service | False | - | - | - | - | 0 | OPTIMAL | 12 | 12 | 0.778 | 0.778 | True | 2 |
| usd4h-K6-I54-seed4-x1.5 | 4 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | False | - | - | - | - | 300.044 | OPTIMAL | 12 | 12 | 0.778 | 0.778 | True | 2 |
| usd4h-K6-I54-seed5-x1.5 | 5 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | TIME_LIMIT | solved | - | - | - | - | - | 300.039 | TIME_LIMIT | - | 11 | - | 0.796 | False | 1 |
| usd4h-K6-I54-seed5-x1.5 | 5 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | - | - | - | - | - | 300.048 | TIME_LIMIT | 16 | 11 | 0.704 | 0.796 | False | 1 |
| usd4h-K6-I54-seed6-x1.5 | 6 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | TIME_LIMIT | solved | - | - | - | - | - | 300.044 | TIME_LIMIT | 21 | 12 | 0.611 | 0.778 | False | 1 |
| usd4h-K6-I54-seed6-x1.5 | 6 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | - | - | - | - | - | 300.053 | TIME_LIMIT | 17 | 12 | 0.685 | 0.778 | False | 1 |
| usd4h-K6-I54-seed7-x1.5 | 7 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | TIME_LIMIT | solved | False | - | - | - | - | 300.032 | OPTIMAL | 14 | 14 | 0.741 | 0.741 | True | 3 |
| usd4h-K6-I54-seed7-x1.5 | 7 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | False | - | - | - | - | 300.042 | OPTIMAL | 14 | 14 | 0.741 | 0.741 | True | 3 |
| usd4h-K6-I54-seed8-x1.5 | 8 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | INFEASIBLE | solved | False | - | - | - | - | 209.116 | OPTIMAL | 11 | 11 | 0.796 | 0.796 | True | 3 |
| usd4h-K6-I54-seed8-x1.5 | 8 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | INFEASIBLE | solved | False | - | - | - | - | 174.935 | OPTIMAL | 11 | 11 | 0.796 | 0.796 | True | 3 |
| usd4h-K6-I54-seed9-x1.5 | 9 | 1.500 | 54 | ilp_zeta85 | 0.850 | 46 | TIME_LIMIT | solved | False | - | - | - | - | 300.039 | OPTIMAL | 13 | 13 | 0.759 | 0.759 | True | 0 |
| usd4h-K6-I54-seed9-x1.5 | 9 | 1.500 | 54 | ilp_zeta90 | 0.900 | 49 | TIME_LIMIT | solved | False | - | - | - | - | 300.037 | OPTIMAL | 13 | 13 | 0.759 | 0.759 | True | 0 |

`ms_*` = maximum feasible served share (min sum u solve) recorded for INFEASIBLE / undecided cells: `ms_share_achievable` is reached by the incumbent, `ms_share_upper_bound` from Gurobi's bound; `ms_n_unservable` orders have no delivery arc at all.

## Means per method and demand level
| demand_mult | method | total | served_share | n_unserved | mean_response_h | mean_lateness_h | n_late | bike_km | n_swaps | kwh_purchased | end_full_total | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.750 | baseline | 577.411 | 0.967 | 0.900 | 0.920 | 0.070 | 7.700 | 96.825 | 6.600 | 2.411 | 5.900 | 10 |
| 0.750 | ilp | 480.099 | 0.944 | 1.500 | 0.830 | 0.005 | 1.400 | 79.665 | 5.300 | 0.528 | 5 | 10 |
| 0.750 | ilp_relaxed | 479.924 | 0.944 | 1.500 | 0.830 | 0.005 | 1.400 | 79.605 | 6.600 | 0.006 | 2.400 | 10 |
| 0.750 | ilp_zeta85 | 480.099 | 0.944 | 1.500 | 0.830 | 0.005 | 1.400 | 79.665 | 5.300 | 0.528 | 5 | 10 |
| 0.750 | ilp_zeta90 | 481.034 | 0.956 | 1.200 | 0.836 | 0.008 | 2.200 | 81.225 | 5.300 | 0.522 | 5 | 10 |
| 1 | baseline | 992.536 | 0.872 | 4.600 | 1.050 | 0.183 | 16.500 | 114.225 | 7.600 | 2.683 | 5.200 | 10 |
| 1 | ilp | 658.590 | 0.875 | 4.500 | 0.826 | 0.003 | 1.200 | 94.140 | 7 | 1.167 | 5 | 10 |
| 1 | ilp_relaxed | 658.229 | 0.875 | 4.500 | 0.826 | 0.003 | 1.200 | 93.915 | 7.400 | 0.122 | 1.900 | 10 |
| 1 | ilp_zeta85 | 666.584 | 0.886 | 4.100 | 0.837 | 0.011 | 2.100 | 95.550 | 7.200 | 1.244 | 5 | 10 |
| 1 | ilp_zeta90 | 695.975 | 0.922 | 2.800 | 0.873 | 0.032 | 5.700 | 103.320 | 7.900 | 1.583 | 5 | 10 |
| 1.500 | baseline | 1930.282 | 0.626 | 20.200 | 1.295 | 0.404 | 24.400 | 125.670 | 8.400 | 2.911 | 4.600 | 10 |
| 1.500 | ilp | 1098.433 | 0.698 | 16.300 | 0.817 | 0.002 | 0.700 | 107.040 | 8.400 | 2.089 | 5 | 10 |
| 1.500 | ilp_relaxed | 1097.950 | 0.698 | 16.300 | 0.817 | 0.002 | 0.700 | 107.535 | 8.800 | 0.394 | 1.300 | 10 |
| 1.500 | ilp_zeta85 | - | - | - | - | - | - | - | - | - | - | 10 |
| 1.500 | ilp_zeta90 | - | - | - | - | - | - | - | - | - | - | 10 |

## Solver statistics
| method | demand_mult | n | optimal | time_limit | infeasible | skipped | implied | gap_max | runtime_mean | runtime_max |
|---|---|---|---|---|---|---|---|---|---|---|
| ilp | 0.750 | 10 | 10 | 0 | 0 | 0 | 0 | 0.000 | 94.291 | 199.344 |
| ilp | 1 | 10 | 9 | 1 | 0 | 0 | 0 | 0.000 | 98.888 | 183.089 |
| ilp | 1.500 | 10 | 9 | 1 | 0 | 0 | 0 | 0.001 | 161.389 | 300.061 |
| ilp_relaxed | 0.750 | 10 | 10 | 0 | 0 | 0 | 0 | 0.000 | 97.149 | 218.633 |
| ilp_relaxed | 1 | 10 | 10 | 0 | 0 | 0 | 0 | 0.000 | 90.515 | 125.535 |
| ilp_relaxed | 1.500 | 10 | 10 | 0 | 0 | 0 | 0 | 0.000 | 132.547 | 211.664 |
| ilp_zeta85 | 0.750 | 10 | 10 | 0 | 0 | 0 | 10 | 0.000 | 0 | 0 |
| ilp_zeta85 | 1 | 10 | 10 | 0 | 0 | 0 | 7 | 0.000 | 37.017 | 142.895 |
| ilp_zeta85 | 1.500 | 10 | 0 | 6 | 4 | 0 | 2 | - | 225.708 | 300.053 |
| ilp_zeta90 | 0.750 | 10 | 10 | 0 | 0 | 0 | 7 | 0.000 | 23.391 | 94.729 |
| ilp_zeta90 | 1 | 10 | 9 | 1 | 0 | 0 | 1 | 0.000 | 115.589 | 300.071 |
| ilp_zeta90 | 1.500 | 10 | 0 | 8 | 2 | 0 | 0 | - | 278.907 | 300.074 |

Figure: `gap_by_demand.png`
