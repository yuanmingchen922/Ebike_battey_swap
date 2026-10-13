# E4 -- station sizing sensitivity (spares B_j, chargers C_j, power P_j)

Family `large` (|K| = 10, |I| = 30, H = 24 slots of 5 min, L = 12, p_ch = 0.667 kW), co-located 3 sites (K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, shared grid group 8 kW / 6 kW from 18:00), seeds [0, 1, 2]; pruning {'tau_max': 4, 'start_slack': 6, 'reachable': False} (reposition targets = restaurants + facilities + depots); Gurobi Threads 4, TimeLimit 150 s, OutputFlag 0; total wall time 41.0 min. Baseline: nearest-feasible dispatch, threshold swap (q_thr = 3), FCFS, HIGH_FIRST charging, no transfers (no services exist on the co-located layout, so C_reb = 0 everywhere). Instances are byte-identical across methods and sizes (only the facility fields B_j, C_j, P_kw and, for the control, rho change).

Costs are in the toy unit system (E2 p.14). `total` is (26) including the setup constant (27) `F_j y_j + bB B_j + bC C_j` (F = 20, bB = 3, bC = 2 per site per horizon); `operational` = total - C_setup. Marginal values are finite differences of the seed-mean cost per *one unit added at one site* (network change / 3 sites / step).

## Which comparison is the headline

**Headline: ILP (written model, rho = 0.5) vs baseline at identical sizes.** The baseline does not enforce the network end target (18) (DECISIONS.md: reported, not enforced), so its schedule is the same under rho = 0 and rho = 0.5, while the ILP with rho = 0.5 carries the extra requirement sum_j n_jLH >= 0.5 sum_j B_j. To show how much of the gap is (18), the `ILP_rho0` rows re-solve the same instances with rho = 0 (same baseline MIP start); `gap_decomposition.csv` reports both `vs = ILP` and `vs = ILP_rho0`. The rho = 0 comparison is the fair *operational* comparison; the rho = 0.5 comparison is the one that matches the written model.

## Sweep B: B_j (seed means; min/max over seeds for total)

| method | B_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | C_orders_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | n_unserved_mean | swap_wait_slots_mean | stockout_slots_mean | stockout_queue_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | n_swaps_mean | end_full_total_mean | marginal_operational_per_unit | marginal_total_per_unit | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 3 | 731.05 | 610.91 | 889.98 | 644.05 | 87 | 537 | 233.33 | 253 | 50.67 | 6.70 | 100.35 | 2.33 | 2 | 61 | 2 | 0.28 | 0.08 | 0.07 | 2 | 6 | 3 | 61.88 | 58.88 | 31.39 | 38.80 | 0 |
| ILP | 2 | 3 | 554.40 | 480.19 | 610.54 | 458.40 | 96 | 348 | 66.67 | 251.33 | 30 | 5 | 105.40 | 0.67 | 3.33 | 46.67 | 1.33 | 0.21 | 0.11 | 0.28 | 2.44 | 8 | 3 | 0.96 | -2.04 | 23.58 | 29.25 | 0 |
| ILP | 3 | 3 | 560.53 | 487.77 | 613.66 | 455.53 | 105 | 345.33 | 66.67 | 250 | 28.67 | 4.15 | 106.05 | 0.67 | 1.33 | 25.67 | 0.33 | 0.17 | 0.12 | 0.61 | 2.89 | 8.33 | 5 | 0.72 | -2.28 | 32.02 | 40.83 | 0.00 |
| ILP | 4 | 3 | 567.36 | 494.55 | 620.54 | 453.36 | 114 | 345.33 | 66.67 | 250 | 28.67 | 2.07 | 105.95 | 0.67 | 2.33 | 10 | 0 | 0.09 | 0.12 | 0.84 | 1.56 | 8.33 | 6 | 0.34 | -2.66 | 23.82 | 27.55 | 0 |
| ILP | 6 | 3 | 583.29 | 510.80 | 635.88 | 451.29 | 132 | 344.33 | 66.67 | 249.67 | 28 | 0.26 | 106.70 | 0.67 | 2 | 0 | 0 | 0.01 | 0.12 | 1 | 0.22 | 9 | 9.33 | - | - | 32.26 | 38.75 | 0.00 |
| ILP_rho0 | 1 | 3 | 731.05 | 610.91 | 889.98 | 644.05 | 87 | 537 | 233.33 | 253 | 50.67 | 6.70 | 100.35 | 2.33 | 2 | 61 | 2 | 0.28 | 0.08 | 0.07 | 2 | 6 | 3 | 61.88 | 58.88 | 45.77 | 53.80 | 0 |
| ILP_rho0 | 2 | 3 | 554.40 | 480.19 | 610.54 | 458.40 | 96 | 348 | 66.67 | 251.33 | 30 | 5 | 105.40 | 0.67 | 3.33 | 46.67 | 1.33 | 0.21 | 0.11 | 0.28 | 2.44 | 8 | 3 | 1.63 | -1.37 | 33.77 | 42.89 | 0 |
| ILP_rho0 | 3 | 3 | 558.52 | 485.75 | 611.54 | 453.52 | 105 | 345 | 66.67 | 249.67 | 28.67 | 2.07 | 106.45 | 0.67 | 2.67 | 20.67 | 0 | 0.09 | 0.12 | 0.68 | 1.33 | 8.33 | 3 | 0.59 | -2.41 | 25.95 | 34.41 | 0 |
| ILP_rho0 | 4 | 3 | 565.76 | 493 | 618.77 | 451.76 | 114 | 344 | 66.67 | 249.33 | 28 | 0.56 | 107.20 | 0.67 | 1.67 | 5.67 | 0 | 0.02 | 0.12 | 0.92 | 0.44 | 9 | 3.67 | 0.12 | -2.88 | 35.12 | 40.45 | 0 |
| ILP_rho0 | 6 | 3 | 583.03 | 510.80 | 635.10 | 451.03 | 132 | 344.33 | 66.67 | 249.67 | 28 | 0 | 106.70 | 0.67 | 4.33 | 0 | 0 | 0 | 0.13 | 1 | 0 | 9.33 | 8.67 | - | - | 29.26 | 32.17 | 0.00 |
| baseline | 1 | 3 | 1725.12 | 1619.39 | 1835.96 | 1638.12 | 87 | 1559.33 | 1333.33 | 164.67 | 61.33 | 4.74 | 74.05 | 13.33 | 42 | 42.67 | 32.67 | 0.20 | 0.09 | 0.32 | 1.78 | 6.33 | 0.33 | 130.18 | 127.18 | 0.00 | 0.00 | - |
| baseline | 2 | 3 | 1343.59 | 1110.61 | 1587.85 | 1247.59 | 96 | 1142 | 866.67 | 208 | 67.33 | 8.19 | 97.40 | 8.67 | 31.33 | 29.33 | 21 | 0.34 | 0.12 | 0.51 | 3.56 | 9 | 3.67 | 95.88 | 92.88 | 0.00 | 0.00 | - |
| baseline | 3 | 3 | 1064.95 | 826.26 | 1283.61 | 959.95 | 105 | 837.33 | 533.33 | 236.67 | 67.33 | 10.37 | 112.25 | 5.33 | 13 | 17.67 | 6.67 | 0.43 | 0.14 | 0.70 | 4.67 | 10 | 6.67 | 31.73 | 28.73 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 978.76 | 730.42 | 1206.52 | 864.76 | 114 | 739.33 | 433.33 | 242.67 | 63.33 | 10.48 | 114.95 | 4.33 | 5.67 | 5.67 | 1.67 | 0.44 | 0.14 | 0.90 | 4.67 | 10 | 10 | 1.14 | -1.86 | 0.00 | 0.00 | - |
| baseline | 6 | 3 | 989.90 | 727.82 | 1224.52 | 857.90 | 132 | 732.67 | 433.33 | 240 | 59.33 | 10.48 | 114.75 | 4.33 | 2.67 | 0.67 | 0 | 0.44 | 0.14 | 0.99 | 4.67 | 10 | 16 | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit` at size s = (cost(s) - cost(next s)) per added battery at one site (positive = adding the unit saves cost); `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H) averaged over sites and seeds; `desk_occupancy` = swap-slot occupancy of the single swap position (22); `idle_full_share` = share of slots in which a full battery stays unused; `stockout_queue_slots` = slots with n_jLt = 0 and a bike waiting to swap; `end_full_total` = sum_j n_jLH (the (18) left-hand side).

## Sweep C: C_j (seed means; min/max over seeds for total)

| method | C_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | C_orders_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | n_unserved_mean | swap_wait_slots_mean | stockout_slots_mean | stockout_queue_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | n_swaps_mean | end_full_total_mean | marginal_operational_per_unit | marginal_total_per_unit | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 3 | 555.36 | 482.55 | 608.54 | 453.36 | 102 | 345.33 | 66.67 | 250 | 28.67 | 2.07 | 105.95 | 0.67 | 1 | 6.67 | 0 | 0.26 | 0.12 | 0.89 | 1.11 | 8.33 | 6 | 0 | -2 | 25.68 | 29.97 | 0 |
| ILP | 2 | 3 | 561.36 | 488.55 | 614.54 | 453.36 | 108 | 345.33 | 66.67 | 250 | 28.67 | 2.07 | 105.95 | 0.67 | 2 | 10 | 0.33 | 0.13 | 0.12 | 0.84 | 1.33 | 8.33 | 6 | 0 | -2 | 25.33 | 32.12 | 0 |
| ILP | 3 | 3 | 567.36 | 494.55 | 620.54 | 453.36 | 114 | 345.33 | 66.67 | 250 | 28.67 | 2.07 | 105.95 | 0.67 | 2.33 | 10 | 0 | 0.09 | 0.12 | 0.84 | 1.56 | 8.33 | 6 | 0 | -2 | 23.82 | 27.55 | 0 |
| ILP | 4 | 3 | 573.36 | 500.55 | 626.54 | 453.36 | 120 | 345.33 | 66.67 | 250 | 28.67 | 2.07 | 105.95 | 0.67 | 2.67 | 7.33 | 0.33 | 0.06 | 0.12 | 0.88 | 1.33 | 8.33 | 6 | - | - | 23.82 | 31.52 | 0 |
| ILP_rho0 | 1 | 3 | 553.76 | 481 | 606.77 | 451.76 | 102 | 344 | 66.67 | 249.33 | 28 | 0.56 | 107.20 | 0.67 | 3.33 | 5 | 0 | 0.07 | 0.12 | 0.92 | 0.22 | 9 | 3.67 | 0 | -2 | 34.38 | 44.85 | 0.00 |
| ILP_rho0 | 3 | 3 | 565.76 | 493 | 618.77 | 451.76 | 114 | 344 | 66.67 | 249.33 | 28 | 0.56 | 107.20 | 0.67 | 1.67 | 5.67 | 0 | 0.02 | 0.12 | 0.92 | 0.44 | 9 | 3.67 | - | - | 35.12 | 40.45 | 0 |
| baseline | 1 | 3 | 987.51 | 791.34 | 1188.74 | 885.51 | 102 | 767.67 | 466.67 | 239 | 62 | 5.15 | 112.70 | 4.67 | 10 | 12 | 6 | 0.64 | 0.14 | 0.80 | 1.78 | 10 | 5.67 | 7.56 | 5.56 | 0.00 | 0.00 | - |
| baseline | 2 | 3 | 970.84 | 722.64 | 1198.18 | 862.84 | 108 | 739.33 | 433.33 | 242.67 | 63.33 | 8.56 | 114.95 | 4.33 | 5.67 | 9.33 | 1.67 | 0.53 | 0.14 | 0.84 | 3.56 | 10 | 8.67 | -0.64 | -2.64 | 0.00 | 0.00 | - |
| baseline | 3 | 3 | 978.76 | 730.42 | 1206.52 | 864.76 | 114 | 739.33 | 433.33 | 242.67 | 63.33 | 10.48 | 114.95 | 4.33 | 5.67 | 5.67 | 1.67 | 0.44 | 0.14 | 0.90 | 4.67 | 10 | 10 | -0.12 | -2.12 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 985.14 | 736.42 | 1213.07 | 865.14 | 120 | 739.33 | 433.33 | 242.67 | 63.33 | 10.85 | 114.95 | 4.33 | 5.67 | 5.67 | 1.67 | 0.34 | 0.14 | 0.90 | 5.11 | 10 | 10 | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit` at size s = (cost(s) - cost(next s)) per added charger at one site (positive = adding the unit saves cost); `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H) averaged over sites and seeds; `desk_occupancy` = swap-slot occupancy of the single swap position (22); `idle_full_share` = share of slots in which a full battery stays unused; `stockout_queue_slots` = slots with n_jLt = 0 and a bike waiting to swap; `end_full_total` = sum_j n_jLH (the (18) left-hand side).

## Gap decomposition: baseline - ILP by cost component (seed means)

| sweep | size | vs | baseline_total | ilp_total | gap_total | gap_pct | gap_unserved | gap_response | gap_lateness | gap_C_travel | gap_C_elec | unserved_share_of_gap | baseline_n_unserved | ilp_n_unserved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 1 | ILP | 1725.12 | 731.05 | 994.07 | 135.98 | 1100 | -88.33 | 10.67 | -26.30 | -1.96 | 1.11 | 13.33 | 2.33 |
| B | 1 | ILP_rho0 | 1725.12 | 731.05 | 994.07 | 135.98 | 1100 | -88.33 | 10.67 | -26.30 | -1.96 | 1.11 | 13.33 | 2.33 |
| B | 2 | ILP | 1343.59 | 554.40 | 789.19 | 142.35 | 800 | -43.33 | 37.33 | -8 | 3.19 | 1.01 | 8.67 | 0.67 |
| B | 2 | ILP_rho0 | 1343.59 | 554.40 | 789.19 | 142.35 | 800 | -43.33 | 37.33 | -8 | 3.19 | 1.01 | 8.67 | 0.67 |
| B | 3 | ILP | 1064.95 | 560.53 | 504.42 | 89.99 | 466.67 | -13.33 | 38.67 | 6.20 | 6.22 | 0.93 | 5.33 | 0.67 |
| B | 3 | ILP_rho0 | 1064.95 | 558.52 | 506.43 | 90.67 | 466.67 | -13 | 38.67 | 5.80 | 8.30 | 0.92 | 5.33 | 0.67 |
| B | 4 | ILP | 978.76 | 567.36 | 411.41 | 72.51 | 366.67 | -7.33 | 34.67 | 9 | 8.41 | 0.89 | 4.33 | 0.67 |
| B | 4 | ILP_rho0 | 978.76 | 565.76 | 413.01 | 73.00 | 366.67 | -6.67 | 35.33 | 7.75 | 9.93 | 0.89 | 4.33 | 0.67 |
| B | 6 | ILP | 989.90 | 583.29 | 406.61 | 69.71 | 366.67 | -9.67 | 31.33 | 8.05 | 10.22 | 0.90 | 4.33 | 0.67 |
| B | 6 | ILP_rho0 | 989.90 | 583.03 | 406.86 | 69.78 | 366.67 | -9.67 | 31.33 | 8.05 | 10.48 | 0.90 | 4.33 | 0.67 |
| C | 1 | ILP | 987.51 | 555.36 | 432.16 | 77.82 | 400 | -11 | 33.33 | 6.75 | 3.07 | 0.93 | 4.67 | 0.67 |
| C | 1 | ILP_rho0 | 987.51 | 553.76 | 433.76 | 78.33 | 400 | -10.33 | 34 | 5.50 | 4.59 | 0.92 | 4.67 | 0.67 |
| C | 2 | ILP | 970.84 | 561.36 | 409.48 | 72.94 | 366.67 | -7.33 | 34.67 | 9 | 6.48 | 0.90 | 4.33 | 0.67 |
| C | 3 | ILP | 978.76 | 567.36 | 411.41 | 72.51 | 366.67 | -7.33 | 34.67 | 9 | 8.41 | 0.89 | 4.33 | 0.67 |
| C | 3 | ILP_rho0 | 978.76 | 565.76 | 413.01 | 73.00 | 366.67 | -6.67 | 35.33 | 7.75 | 9.93 | 0.89 | 4.33 | 0.67 |
| C | 4 | ILP | 985.14 | 573.36 | 411.78 | 71.82 | 366.67 | -7.33 | 34.67 | 9 | 8.78 | 0.89 | 4.33 | 0.67 |

`gap_<component>` = baseline component - ILP component (positive = baseline pays more); `unserved_share_of_gap` = gap_unserved / gap_total (P_i = 100 per unserved order).

## B x C grid (seed means, P_j = 4 kW)

ILP:

| B_j | C_j | total | operational | C_orders | n_unserved | swap_wait_slots | stockout_slots | charger_util_mean |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 554.40 | 458.40 | 348 | 0.67 | 3.33 | 46.67 | 0.21 |
| 4 | 1 | 555.36 | 453.36 | 345.33 | 0.67 | 1 | 6.67 | 0.26 |
| 4 | 2 | 561.36 | 453.36 | 345.33 | 0.67 | 2 | 10 | 0.13 |
| 4 | 3 | 567.36 | 453.36 | 345.33 | 0.67 | 2.33 | 10 | 0.09 |
| 6 | 3 | 583.29 | 451.29 | 344.33 | 0.67 | 2 | 0 | 0.01 |

Baseline on the same grid:

| B_j | C_j | total | operational | C_orders | n_unserved | swap_wait_slots | stockout_slots | charger_util_mean |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 1343.59 | 1247.59 | 1142 | 8.67 | 31.33 | 29.33 | 0.34 |
| 4 | 1 | 987.51 | 885.51 | 767.67 | 4.67 | 10 | 12 | 0.64 |
| 4 | 2 | 970.84 | 862.84 | 739.33 | 4.33 | 5.67 | 9.33 | 0.53 |
| 4 | 3 | 978.76 | 864.76 | 739.33 | 4.33 | 5.67 | 5.67 | 0.44 |
| 6 | 3 | 989.90 | 857.90 | 732.67 | 4.33 | 2.67 | 0.67 | 0.44 |

## ILP with B_j, C_j free (y fixed, bB = 3, bC = 2) and the fixed re-run at the chosen sizes

| seed | sweep | method | status | total | operational | C_setup | C_orders | C_elec | n_unserved | swap_wait_slots | stockout_slots | chosen_B | chosen_C | sum_B | sum_C | charger_util_mean | idle_full_share_mean | end_full_total | gap | runtime_s | mip_start_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | free | ILP | OPTIMAL | 467.42 | 386.42 | 81 | 280 | 6.67 | 0 | 9 | 44 | {"S1": 1, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 5 | 3 | 0.83 | 0.31 | 3 | 0.00 | 29.22 | - |
| 0 | free_fixed | ILP | OPTIMAL | 467.42 | 386.42 | 81 | 280 | 6.67 | 0 | 11 | 50 | {"S1": 1, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 5 | 3 | 0.83 | 0.22 | 3 | 0.00 | 27.55 | True |
| 0 | free_fixed | ILP_rho0 | OPTIMAL | 467.42 | 386.42 | 81 | 280 | 6.67 | 0 | 11 | 50 | {"S1": 1, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 5 | 3 | 0.83 | 0.22 | 3 | 0 | 25.60 | False |
| 0 | free_fixed | baseline | - | 1378.12 | 1297.12 | 81 | 1201 | 5.67 | 9 | 33 | 34 | {"S1": 1, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 5 | 3 | 0.71 | 0.46 | 2 | - | 0.00 | - |
| 1 | free | ILP | TIME_LIMIT | 560.47 | 476.47 | 84 | 368 | 4.67 | 1 | 2 | 55 | {"S1": 2, "S2": 3, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 6 | 3 | 0.58 | 0.17 | 3 | 0.00 | 150.08 | - |
| 1 | free_fixed | ILP | OPTIMAL | 560.47 | 476.47 | 84 | 368 | 4.67 | 1 | 3 | 55 | {"S1": 2, "S2": 3, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 6 | 3 | 0.58 | 0.17 | 3 | 0 | 20.68 | True |
| 1 | free_fixed | ILP_rho0 | OPTIMAL | 560.47 | 476.47 | 84 | 368 | 4.67 | 1 | 3 | 55 | {"S1": 2, "S2": 3, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 6 | 3 | 0.58 | 0.17 | 3 | 0 | 24.53 | False |
| 1 | free_fixed | baseline | - | 1314.11 | 1230.11 | 84 | 1129 | 5.56 | 8 | 19 | 33 | {"S1": 2, "S2": 3, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 6 | 3 | 0.69 | 0.46 | 1 | - | 0.00 | - |
| 2 | free | ILP | OPTIMAL | 598.19 | 511.19 | 87 | 391 | 5.89 | 1 | 0 | 40 | {"S1": 3, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 7 | 3 | 0.74 | 0.38 | 4 | 0 | 135.19 | - |
| 2 | free_fixed | ILP | OPTIMAL | 598.19 | 511.19 | 87 | 391 | 5.89 | 1 | 5 | 51 | {"S1": 3, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 7 | 3 | 0.74 | 0.22 | 4 | 0 | 40.52 | False |
| 2 | free_fixed | ILP_rho0 | OPTIMAL | 597.08 | 510.08 | 87 | 391 | 4.78 | 1 | 4 | 47 | {"S1": 3, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 7 | 3 | 0.60 | 0.28 | 3 | 0 | 114.04 | False |
| 2 | free_fixed | baseline | - | 1408.64 | 1321.64 | 87 | 1221 | 3.89 | 10 | 18 | 27 | {"S1": 3, "S2": 2, "S3": 2} | {"S1": 1, "S2": 1, "S3": 1} | 7 | 3 | 0.49 | 0.56 | 2 | - | 0.00 | - |

## Solver statistics

- `ILP` runs: 30; statuses {'OPTIMAL': 29, 'TIME_LIMIT': 1}; binaries 1,434,673-1,523,943; rows 80,306-80,306; solve time mean 35.2 s, max 150.1 s; gap max 0.0048; arc build mean 2.45 s; model build mean 5.94 s; every schedule passes `evaluate.check`: True; MIP start accepted in 15 of 27 runs with a start.
- `ILP_rho0` runs: 21; statuses {'OPTIMAL': 21}; binaries 1,434,673-1,523,943; rows 80,306-80,306; solve time mean 37.0 s, max 114.0 s; gap max 0.0001; arc build mean 2.41 s; model build mean 5.65 s; every schedule passes `evaluate.check`: True; MIP start accepted in 10 of 21 runs with a start.
- baseline: 27 runs, reported families ['{"(17)": 1, "(18)": 1}', '{"(17)": 1}', '{"(17)": 2, "(18)": 1}', '{"(17)": 3, "(18)": 1}', '{}'] (only the report-only families (9), (17), (18) may appear); identity (24) holds on all schedules: True; ILP <= baseline on every variant: True.

## Figures

- `cost_vs_B.png`
- `cost_vs_C.png`

## Interpretation and anomalies

### Swap-stressed supplement: same family, bikes start at q0 ~ U{3, ..., 6} of 12 (`--init-frac 0.25 0.5`)

Byte-identical orders, routes and facilities to the main run (the generator draws the bikes last); only the initial battery levels change (mean q0 = 4.0 / 4.7 / 4.3 instead of 7.5 / 8.7 / 8.4). Sweeps B and C with the rho = 0 control on the B sweep and the C = 1 variant, plus the free-size ILP; 3 seeds; Threads 4, 150 s.

1. **Spares now matter, with a knee at two per site.** ILP operational cost 644.1 / 458.4 / 455.5 / 453.4 / 451.3 at B_j = 1 / 2 / 3 / 4 / 6; the marginal value of one more battery at one site is 61.9 (1 -> 2), 0.96 (2 -> 3), 0.72 (3 -> 4), 0.34 (4 -> 6) against bB = 3, so the total cost is minimised at B_j = 2 (554.4) and the free-size ILP buys sum B = 5 / 6 / 7 batteries (B_j in {1, 2, 3} per site) with exactly one charger per site (utilisation 0.58-0.83). At B_j = 1 the ILP leaves 2.33 orders unserved (61 empty-stock site-slots, 2 of them with a queued bike); from B_j = 2 on the only unserved orders are the same two infeasible orders as in the main run (0.67 mean).
2. **The end target (18) binds mildly.** ILP vs ILP_rho0: +2.0 at B_j = 3, +1.6 at B_j = 4, +0.3 at B_j = 6 and 0 at B_j = 1, 2 (where 0.5 sum B <= 3 is implied by (17)); the rho = 0 comparison lowers the baseline gap by at most 0.5 points, so the headline (rho = 0.5) comparison is not materially inflated here either.
3. **One charger per site is enough for the ILP; the baseline wants two.** ILP operational cost is 453.36 for C_j = 1, 2, 3, 4 (identical schedules up to tie-breaks: C_elec 2.07, i.e. about 1 kWh, 8.3 swaps); the marginal value of a charger is 0 and the total rises by bC = 2 per charger. The baseline improves from C_j = 1 to 2 (987.5 -> 970.8, 4.67 -> 4.33 unserved, marginal value 7.6 per charger) and is flat afterwards; its charger utilisation is 0.64 / 0.53 / 0.44 / 0.34.
4. **Value of coordination ~ 2 spares per site.** The baseline needs B_j = 4 (979, 4.33 unserved) to get where the ILP already is at B_j = 2 (554, 0.67 unserved), and its marginal battery values are 130 / 96 / 32 / 1.1; the plan expected "about one more battery per site", the measured figure is two.
5. **Gap decomposition.** At the default B_j = 4 the gap is 411 (72.5 %): unserved 367 (share 0.89), lateness +35, travel +9, electricity +8 (ASAP charging), response -7. Unserved orders still dominate, but lateness and charging are now visible components, and at B_j = 1 the gap is 994 (136 %) with the unserved share 1.11.
6. **Solver.** 51 ILP solves: 50 OPTIMAL, 1 TIME_LIMIT (free-size run of seed 1 at 150 s with MIPGap 0.48 %, incumbent used; its fixed re-run is OPTIMAL at the same value); mean 30 s; 41 min wall concurrently with the main run; every schedule passes `evaluate.check`, identity (24) holds everywhere. The baseline start is accepted by the rho = 0 model when (18) is its only violation (seed 0 B >= 2); the chain `ILP_rho0 -> ILP` is accepted whenever the rho = 0 optimum happens to meet (18).

Caveat: the baseline violates (17) and/or (18) in most stressed variants (report-only), and its ASAP charging buys 5-10 units of electricity that the ILP avoids; the comparison is therefore favourable to the baseline on the end-of-horizon stock.
