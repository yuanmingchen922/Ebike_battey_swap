# E4 -- station sizing sensitivity (spares B_j, chargers C_j, power P_j)

Family `large` (|K| = 10, |I| = 30, H = 24 slots of 5 min, L = 12, p_ch = 0.667 kW), co-located 3 sites (K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, shared grid group 8 kW / 6 kW from 18:00), seeds [0, 1, 2]; pruning {'tau_max': 4, 'start_slack': 6, 'reachable': False} (reposition targets = restaurants + facilities + depots); Gurobi Threads 4, TimeLimit 150 s, OutputFlag 0; total wall time 48.8 min. Baseline: nearest-feasible dispatch, threshold swap (q_thr = 3), FCFS, HIGH_FIRST charging, no transfers (no services exist on the co-located layout, so C_reb = 0 everywhere). Instances are byte-identical across methods and sizes (only the facility fields B_j, C_j, P_kw and, for the control, rho change).

Costs are in the toy unit system (E2 p.14). `total` is (26) including the setup constant (27) `F_j y_j + bB B_j + bC C_j` (F = 20, bB = 3, bC = 2 per site per horizon); `operational` = total - C_setup. Marginal values are finite differences of the seed-mean cost per *one unit added at one site* (network change / 3 sites / step).

## Which comparison is the headline

**Headline: ILP (written model, rho = 0.5) vs baseline at identical sizes.** The baseline does not enforce the network end target (18) (DECISIONS.md: reported, not enforced), so its schedule is the same under rho = 0 and rho = 0.5, while the ILP with rho = 0.5 carries the extra requirement sum_j n_jLH >= 0.5 sum_j B_j. To show how much of the gap is (18), the `ILP_rho0` rows re-solve the same instances with rho = 0 (same baseline MIP start); `gap_decomposition.csv` reports both `vs = ILP` and `vs = ILP_rho0`. The rho = 0 comparison is the fair *operational* comparison; the rho = 0.5 comparison is the one that matches the written model.

## Sweep B: B_j (seed means; min/max over seeds for total)

| method | B_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | C_orders_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | n_unserved_mean | swap_wait_slots_mean | stockout_slots_mean | stockout_queue_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | n_swaps_mean | end_full_total_mean | marginal_operational_per_unit | marginal_total_per_unit | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 3 | 528.53 | 460.72 | 576.82 | 441.53 | 87 | 341 | 66.67 | 249 | 25.33 | 1.93 | 98.60 | 0.67 | 0.33 | 39 | 0 | 0.08 | 0.03 | 0.43 | 1.33 | 2.33 | 3 | 0.70 | -2.30 | 22.20 | 23.49 | 0.00 |
| ILP | 2 | 3 | 535.44 | 467.05 | 583.27 | 439.44 | 96 | 340.67 | 66.67 | 249.33 | 24.67 | 0.22 | 98.55 | 0.67 | 1.33 | 5.33 | 0 | 0.01 | 0.04 | 0.92 | 0.22 | 2.67 | 3.67 | 0.07 | -2.93 | 28.90 | 34.68 | 0.00 |
| ILP | 3 | 3 | 544.22 | 476.05 | 591.60 | 439.22 | 105 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 2.67 | 6.33 | 0 | -3 | 24.86 | 28.57 | 0.00 |
| ILP | 4 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 9 | 0 | -3 | 26.63 | 32.85 | 0 |
| ILP | 6 | 3 | 571.22 | 503.05 | 618.60 | 439.22 | 132 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 15 | - | - | 27.82 | 28.65 | 0.00 |
| ILP_rho0 | 1 | 3 | 528.53 | 460.72 | 576.82 | 441.53 | 87 | 341 | 66.67 | 249 | 25.33 | 1.93 | 98.60 | 0.67 | 0.33 | 39 | 0 | 0.08 | 0.03 | 0.43 | 1.33 | 2.33 | 3 | 0.70 | -2.30 | 29.28 | 34.93 | 0 |
| ILP_rho0 | 2 | 3 | 535.44 | 467.05 | 583.27 | 439.44 | 96 | 340.67 | 66.67 | 249.33 | 24.67 | 0.22 | 98.55 | 0.67 | 1.33 | 5.33 | 0 | 0.01 | 0.04 | 0.92 | 0.22 | 2.67 | 3.67 | 0.07 | -2.93 | 23.81 | 26.74 | 0.00 |
| ILP_rho0 | 3 | 3 | 544.22 | 476.05 | 591.60 | 439.22 | 105 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 2.67 | 6.33 | 0 | -3 | 22.90 | 30.81 | 0 |
| ILP_rho0 | 4 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 9 | 0 | -3 | 22.04 | 25.73 | 0 |
| ILP_rho0 | 6 | 3 | 571.22 | 503.05 | 618.60 | 439.22 | 132 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 15 | - | - | 23.71 | 31.40 | 0 |
| baseline | 1 | 3 | 923.14 | 780.40 | 1045.48 | 836.14 | 87 | 726.33 | 466.67 | 221 | 38.67 | 1.85 | 107.95 | 4.67 | 0.33 | 16.67 | 0.33 | 0.08 | 0.04 | 0.73 | 1.33 | 2.67 | 1 | 0.39 | -2.61 | 0.00 | 0.00 | - |
| baseline | 2 | 3 | 930.98 | 787.37 | 1055.03 | 834.98 | 96 | 724.33 | 466.67 | 220.33 | 37.33 | 2.59 | 108.05 | 4.67 | 0 | 6.33 | 0 | 0.11 | 0.06 | 0.88 | 2.44 | 4.33 | 2.33 | -0.10 | -3.10 | 0.00 | 0.00 | - |
| baseline | 3 | 3 | 940.27 | 796.48 | 1064.48 | 835.27 | 105 | 724.33 | 466.67 | 220.33 | 37.33 | 2.89 | 108.05 | 4.67 | 0.33 | 2.67 | 0 | 0.12 | 0.07 | 0.95 | 3.11 | 5.33 | 4.33 | 0 | -3 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 949.27 | 805.48 | 1073.48 | 835.27 | 114 | 724.33 | 466.67 | 220.33 | 37.33 | 2.89 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.12 | 0.08 | 0.98 | 3.11 | 5.67 | 7 | 0 | -3 | 0.00 | 0.00 | - |
| baseline | 6 | 3 | 967.27 | 823.48 | 1091.48 | 835.27 | 132 | 724.33 | 466.67 | 220.33 | 37.33 | 2.89 | 108.05 | 4.67 | 1.33 | 0 | 0 | 0.12 | 0.08 | 1 | 3.11 | 6 | 12.67 | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit` at size s = (cost(s) - cost(next s)) per added battery at one site (positive = adding the unit saves cost); `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H) averaged over sites and seeds; `desk_occupancy` = swap-slot occupancy of the single swap position (22); `idle_full_share` = share of slots in which a full battery stays unused; `stockout_queue_slots` = slots with n_jLt = 0 and a bike waiting to swap; `end_full_total` = sum_j n_jLH (the (18) left-hand side).

## Sweep C: C_j (seed means; min/max over seeds for total)

| method | C_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | C_orders_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | n_unserved_mean | swap_wait_slots_mean | stockout_slots_mean | stockout_queue_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | n_swaps_mean | end_full_total_mean | marginal_operational_per_unit | marginal_total_per_unit | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 3 | 541.22 | 473.05 | 588.60 | 439.22 | 102 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.67 | 0 | 0 | 0 | 0.05 | 1 | 0 | 3.33 | 8.67 | 0 | -2 | 24.26 | 25.05 | 0.00 |
| ILP | 2 | 3 | 547.22 | 479.05 | 594.60 | 439.22 | 108 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1.33 | 0 | 0 | 0 | 0.05 | 1 | 0 | 3.33 | 8.67 | 0 | -2 | 22.62 | 28.08 | 0 |
| ILP | 3 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 9 | 0 | -2 | 26.63 | 32.85 | 0 |
| ILP | 4 | 3 | 559.22 | 491.05 | 606.60 | 439.22 | 120 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 3.33 | 0 | 0 | 0 | 0.05 | 1 | 0 | 3.33 | 8.67 | - | - | 21.07 | 28.18 | 0 |
| ILP_rho0 | 1 | 3 | 541.22 | 473.05 | 588.60 | 439.22 | 102 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.67 | 0 | 0 | 0 | 0.05 | 1 | 0 | 3.33 | 8.67 | 0 | -2 | 23.73 | 33.42 | 0 |
| ILP_rho0 | 3 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 9 | - | - | 22.04 | 25.73 | 0 |
| baseline | 1 | 3 | 936.27 | 792.70 | 1060.48 | 834.27 | 102 | 724.33 | 466.67 | 220.33 | 37.33 | 1.89 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.24 | 0.08 | 0.98 | 1.33 | 5.67 | 7 | -0.23 | -2.23 | 0.00 | 0.00 | - |
| baseline | 2 | 3 | 942.98 | 799.37 | 1067.03 | 834.98 | 108 | 724.33 | 466.67 | 220.33 | 37.33 | 2.59 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.16 | 0.08 | 0.98 | 2.44 | 5.67 | 7 | -0.10 | -2.10 | 0.00 | 0.00 | - |
| baseline | 3 | 3 | 949.27 | 805.48 | 1073.48 | 835.27 | 114 | 724.33 | 466.67 | 220.33 | 37.33 | 2.89 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.12 | 0.08 | 0.98 | 3.11 | 5.67 | 7 | -0.04 | -2.04 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 955.38 | 811.48 | 1079.81 | 835.38 | 120 | 724.33 | 466.67 | 220.33 | 37.33 | 3 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.09 | 0.08 | 0.98 | 3.33 | 5.67 | 7 | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit` at size s = (cost(s) - cost(next s)) per added charger at one site (positive = adding the unit saves cost); `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H) averaged over sites and seeds; `desk_occupancy` = swap-slot occupancy of the single swap position (22); `idle_full_share` = share of slots in which a full battery stays unused; `stockout_queue_slots` = slots with n_jLt = 0 and a bike waiting to swap; `end_full_total` = sum_j n_jLH (the (18) left-hand side).

## Sweep P: P_kw (seed means; min/max over seeds for total)

| method | P_kw | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | C_orders_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | n_unserved_mean | swap_wait_slots_mean | stockout_slots_mean | stockout_queue_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | n_swaps_mean | end_full_total_mean | marginal_operational_per_unit | marginal_total_per_unit | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 0.70 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1 | 0 | 0 | 0 | 0.05 | 1 | 0 | 3.67 | 8.33 | 0 | 0 | 22.26 | 31.43 | 0 |
| ILP | 1.40 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1 | 0 | 0 | 0 | 0.05 | 1 | 0 | 3.67 | 8.33 | 0 | 0 | 24.15 | 29.81 | 0 |
| ILP | 2.10 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 9 | 0 | 0 | 21.29 | 29.80 | 0 |
| ILP | 2.80 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 1.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 2.67 | 9.33 | 0 | 0 | 22.04 | 29.04 | 0 |
| ILP | 4 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 9 | - | - | 26.63 | 32.85 | 0 |
| ILP_rho0 | 4 | 3 | 553.22 | 485.05 | 600.60 | 439.22 | 114 | 340.67 | 66.67 | 249.33 | 24.67 | 0 | 98.55 | 0.67 | 2.33 | 0 | 0 | 0 | 0.04 | 1 | 0 | 3 | 9 | - | - | 22.04 | 25.73 | 0 |
| baseline | 0.70 | 3 | 948.27 | 804.70 | 1072.48 | 834.27 | 114 | 724.33 | 466.67 | 220.33 | 37.33 | 1.89 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.08 | 0.08 | 0.98 | 1.33 | 5.67 | 7 | -0.34 | -0.34 | 0.00 | 0.00 | - |
| baseline | 1.40 | 3 | 948.98 | 805.37 | 1073.03 | 834.98 | 114 | 724.33 | 466.67 | 220.33 | 37.33 | 2.59 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.11 | 0.08 | 0.98 | 2.44 | 5.67 | 7 | -0.14 | -0.14 | 0.00 | 0.00 | - |
| baseline | 2.10 | 3 | 949.27 | 805.48 | 1073.48 | 835.27 | 114 | 724.33 | 466.67 | 220.33 | 37.33 | 2.89 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.12 | 0.08 | 0.98 | 3.11 | 5.67 | 7 | 0 | 0 | 0.00 | 0.00 | - |
| baseline | 2.80 | 3 | 949.27 | 805.48 | 1073.48 | 835.27 | 114 | 724.33 | 466.67 | 220.33 | 37.33 | 2.89 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.12 | 0.08 | 0.98 | 3.11 | 5.67 | 7 | 0 | 0 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 949.27 | 805.48 | 1073.48 | 835.27 | 114 | 724.33 | 466.67 | 220.33 | 37.33 | 2.89 | 108.05 | 4.67 | 0.67 | 1 | 0 | 0.12 | 0.08 | 0.98 | 3.11 | 5.67 | 7 | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit` at size s = (cost(s) - cost(next s)) per added kW at one site (positive = adding the unit saves cost); `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H) averaged over sites and seeds; `desk_occupancy` = swap-slot occupancy of the single swap position (22); `idle_full_share` = share of slots in which a full battery stays unused; `stockout_queue_slots` = slots with n_jLt = 0 and a bike waiting to swap; `end_full_total` = sum_j n_jLH (the (18) left-hand side).

## Gap decomposition: baseline - ILP by cost component (seed means)

| sweep | size | vs | baseline_total | ilp_total | gap_total | gap_pct | gap_unserved | gap_response | gap_lateness | gap_C_travel | gap_C_elec | unserved_share_of_gap | baseline_n_unserved | ilp_n_unserved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 1 | ILP | 923.14 | 528.53 | 394.61 | 74.66 | 400 | -28 | 13.33 | 9.35 | -0.07 | 1.01 | 4.67 | 0.67 |
| B | 1 | ILP_rho0 | 923.14 | 528.53 | 394.61 | 74.66 | 400 | -28 | 13.33 | 9.35 | -0.07 | 1.01 | 4.67 | 0.67 |
| B | 2 | ILP | 930.98 | 535.44 | 395.54 | 73.87 | 400 | -29 | 12.67 | 9.50 | 2.37 | 1.01 | 4.67 | 0.67 |
| B | 2 | ILP_rho0 | 930.98 | 535.44 | 395.54 | 73.87 | 400 | -29 | 12.67 | 9.50 | 2.37 | 1.01 | 4.67 | 0.67 |
| B | 3 | ILP | 940.27 | 544.22 | 396.06 | 72.78 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| B | 3 | ILP_rho0 | 940.27 | 544.22 | 396.06 | 72.78 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| B | 4 | ILP | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| B | 4 | ILP_rho0 | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| B | 6 | ILP | 967.27 | 571.22 | 396.06 | 69.34 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| B | 6 | ILP_rho0 | 967.27 | 571.22 | 396.06 | 69.34 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| C | 1 | ILP | 936.27 | 541.22 | 395.06 | 72.99 | 400 | -29 | 12.67 | 9.50 | 1.89 | 1.01 | 4.67 | 0.67 |
| C | 1 | ILP_rho0 | 936.27 | 541.22 | 395.06 | 72.99 | 400 | -29 | 12.67 | 9.50 | 1.89 | 1.01 | 4.67 | 0.67 |
| C | 2 | ILP | 942.98 | 547.22 | 395.76 | 72.32 | 400 | -29 | 12.67 | 9.50 | 2.59 | 1.01 | 4.67 | 0.67 |
| C | 3 | ILP | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| C | 3 | ILP_rho0 | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| C | 4 | ILP | 955.38 | 559.22 | 396.17 | 70.84 | 400 | -29 | 12.67 | 9.50 | 3 | 1.01 | 4.67 | 0.67 |
| P | 0.70 | ILP | 948.27 | 553.22 | 395.06 | 71.41 | 400 | -29 | 12.67 | 9.50 | 1.89 | 1.01 | 4.67 | 0.67 |
| P | 1.40 | ILP | 948.98 | 553.22 | 395.76 | 71.54 | 400 | -29 | 12.67 | 9.50 | 2.59 | 1.01 | 4.67 | 0.67 |
| P | 2.10 | ILP | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| P | 2.80 | ILP | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| P | 4 | ILP | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |
| P | 4 | ILP_rho0 | 949.27 | 553.22 | 396.06 | 71.59 | 400 | -29 | 12.67 | 9.50 | 2.89 | 1.01 | 4.67 | 0.67 |

`gap_<component>` = baseline component - ILP component (positive = baseline pays more); `unserved_share_of_gap` = gap_unserved / gap_total (P_i = 100 per unserved order).

## B x C grid (seed means, P_j = 4 kW)

ILP:

| B_j | C_j | total | operational | C_orders | n_unserved | swap_wait_slots | stockout_slots | charger_util_mean |
|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 523.44 | 439.44 | 340.67 | 0.67 | 2.33 | 0 | 0.03 |
| 2 | 2 | 529.44 | 439.44 | 340.67 | 0.67 | 1 | 6.33 | 0.01 |
| 2 | 3 | 535.44 | 439.44 | 340.67 | 0.67 | 1.33 | 5.33 | 0.01 |
| 4 | 1 | 541.22 | 439.22 | 340.67 | 0.67 | 2.67 | 0 | 0 |
| 4 | 2 | 547.22 | 439.22 | 340.67 | 0.67 | 1.33 | 0 | 0 |
| 4 | 3 | 553.22 | 439.22 | 340.67 | 0.67 | 2.33 | 0 | 0 |
| 6 | 1 | 559.22 | 439.22 | 340.67 | 0.67 | 1 | 0 | 0 |
| 6 | 2 | 565.22 | 439.22 | 340.67 | 0.67 | 1.33 | 0 | 0 |
| 6 | 3 | 571.22 | 439.22 | 340.67 | 0.67 | 1 | 0 | 0 |

Baseline on the same grid:

| B_j | C_j | total | operational | C_orders | n_unserved | swap_wait_slots | stockout_slots | charger_util_mean |
|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 918.27 | 834.27 | 724.33 | 4.67 | 0 | 6.33 | 0.24 |
| 2 | 2 | 924.98 | 834.98 | 724.33 | 4.67 | 0 | 6.33 | 0.16 |
| 2 | 3 | 930.98 | 834.98 | 724.33 | 4.67 | 0 | 6.33 | 0.11 |
| 4 | 1 | 936.27 | 834.27 | 724.33 | 4.67 | 0.67 | 1 | 0.24 |
| 4 | 2 | 942.98 | 834.98 | 724.33 | 4.67 | 0.67 | 1 | 0.16 |
| 4 | 3 | 949.27 | 835.27 | 724.33 | 4.67 | 0.67 | 1 | 0.12 |
| 6 | 1 | 954.27 | 834.27 | 724.33 | 4.67 | 1.33 | 0 | 0.24 |
| 6 | 2 | 960.98 | 834.98 | 724.33 | 4.67 | 1.33 | 0 | 0.16 |
| 6 | 3 | 967.27 | 835.27 | 724.33 | 4.67 | 1.33 | 0 | 0.12 |

## ILP with B_j, C_j free (y fixed, bB = 3, bC = 2) and the fixed re-run at the chosen sizes

| seed | sweep | method | status | total | operational | C_setup | C_orders | C_elec | n_unserved | swap_wait_slots | stockout_slots | chosen_B | chosen_C | sum_B | sum_C | charger_util_mean | idle_full_share_mean | end_full_total | gap | runtime_s | mip_start_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | free | ILP | OPTIMAL | 446.52 | 375.52 | 71 | 278 | 1.67 | 0 | 4 | 20 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 0, "S2": 1, "S3": 0} | 3 | 1 | 0.62 | 0.69 | 3 | 0 | 74.17 | - |
| 0 | free_fixed | ILP | OPTIMAL | 446.52 | 375.52 | 71 | 278 | 1.67 | 0 | 4 | 16 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 0, "S2": 1, "S3": 0} | 3 | 1 | 0.62 | 0.75 | 3 | 0.00 | 17.30 | True |
| 0 | free_fixed | ILP_rho0 | OPTIMAL | 446.52 | 375.52 | 71 | 278 | 1.67 | 0 | 4 | 16 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 0, "S2": 1, "S3": 0} | 3 | 1 | 0.62 | 0.75 | 3 | 0 | 15.98 | False |
| 0 | free_fixed | baseline | - | 926.53 | 855.53 | 71 | 736 | 1.78 | 5 | 1 | 25 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 0, "S2": 1, "S3": 0} | 3 | 1 | 0.67 | 0.60 | 0 | - | 0.00 | - |
| 1 | free | ILP | OPTIMAL | 532 | 460 | 72 | 361 | 0 | 1 | 0 | 0 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 0, "S2": 0, "S3": 0} | 4 | 0 | - | 1 | 3 | 0 | 30.64 | - |
| 1 | free_fixed | ILP | OPTIMAL | 532 | 460 | 72 | 361 | 0 | 1 | 0 | 0 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 0, "S2": 0, "S3": 0} | 4 | 0 | - | 1 | 3 | 0 | 17.86 | True |
| 1 | free_fixed | ILP_rho0 | OPTIMAL | 532 | 460 | 72 | 361 | 0 | 1 | 0 | 0 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 0, "S2": 0, "S3": 0} | 4 | 0 | - | 1 | 3 | 0 | 19.15 | False |
| 1 | free_fixed | baseline | - | 763.40 | 691.40 | 72 | 584 | 0 | 3 | 0 | 18 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 0, "S2": 0, "S3": 0} | 4 | 0 | - | 0.72 | 1 | - | 0.00 | - |
| 2 | free | ILP | OPTIMAL | 562.94 | 489.94 | 73 | 385 | 1.44 | 1 | 1 | 25 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.27 | 0.62 | 3 | 0 | 65.33 | - |
| 2 | free_fixed | ILP | OPTIMAL | 562.94 | 489.94 | 73 | 385 | 1.44 | 1 | 2 | 39 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.27 | 0.43 | 3 | 0.00 | 17.14 | True |
| 2 | free_fixed | ILP_rho0 | OPTIMAL | 562.94 | 489.94 | 73 | 385 | 1.44 | 1 | 2 | 39 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.27 | 0.43 | 3 | 0 | 13.49 | False |
| 2 | free_fixed | baseline | - | 1031.48 | 958.48 | 73 | 859 | 0.78 | 6 | 0 | 7 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.15 | 0.89 | 2 | - | 0.00 | - |

## Solver statistics

- `ILP` runs: 54; statuses {'OPTIMAL': 54}; binaries 1,434,673-1,523,943; rows 80,306-80,306; solve time mean 25.1 s, max 74.2 s; gap max 0.0000; arc build mean 2.46 s; model build mean 5.37 s; every schedule passes `evaluate.check`: True; MIP start accepted in 37 of 51 runs with a start.
- `ILP_rho0` runs: 27; statuses {'OPTIMAL': 27}; binaries 1,434,673-1,523,943; rows 80,306-80,306; solve time mean 22.7 s, max 34.9 s; gap max 0.0001; arc build mean 2.49 s; model build mean 5.45 s; every schedule passes `evaluate.check`: True; MIP start accepted in 13 of 27 runs with a start.
- baseline: 51 runs, reported families ['{"(17)": 1, "(18)": 1}', '{"(17)": 1}', '{"(17)": 2, "(18)": 1}', '{"(17)": 3, "(18)": 1}', '{"(18)": 1}', '{}'] (only the report-only families (9), (17), (18) may appear); identity (24) holds on all schedules: True; ILP <= baseline on every variant: True.

## Figures

- `cost_vs_B.png`
- `cost_vs_C.png`
- `cost_vs_P.png`
- `heatmap_BxC.png`

## Interpretation and anomalies

### Headline comparison and what the sweeps show

1. **The headline comparison (written model, rho = 0.5) and the rho = 0 control coincide in this family.** In every one of the 27 B-sweep / C = 1 variants the `ILP_rho0` optimum satisfies (18) anyway (the optimum leaves 3-15 full spares at t = H because it swaps only 2.3-3.7 times in total), so the ILP totals are identical to the cent and the baseline gap is *not* inflated by (18). The baseline start is rejected by the written model in 14 of 24 cases and by the rho = 0 model in 14 of 27 cases: the rejections come from the report-only families (17) (R_end = 1 at a site that the baseline empties, 22 runs) and (18) (16 runs). The chain `baseline -> ILP_rho0 -> ILP` was accepted 27 / 27 times and keeps every C = 1 variant solvable in about 25 s (the probe without it ran 162 s to the time limit without an incumbent on the same instance).
2. **Spares B_j: operational cost is flat beyond two spares per site.** The ILP's operational cost (total - setup) is 441.5 / 439.4 / 439.2 / 439.2 / 439.2 at B_j = 1 / 2 / 3 / 4 / 6 (seed means; seed 0: 373.7 -> 371.05, seed 1: 461.0 -> 460.0, seed 2: 489.8 -> 486.6). The finite-difference value of one more battery at one site is 0.70 (1 -> 2), 0.07 (2 -> 3) and exactly 0 afterwards, all below the setup price bB = 3, so the *total* cost rises monotonically with B_j (528.5 -> 571.2) and the free-size ILP buys one spare per site (sum B = 3, 4, 3 for seeds 0, 1, 2) and zero to two chargers in total. With 10 bikes that start at q0 = 7.5-8.7 of 12 levels and 30 orders in 2 h, the fleet needs only about 3 swaps; the stations are not a bottleneck.
3. **Chargers C_j and power P_j: zero marginal value for the ILP, slightly negative for the baseline.** The ILP never charges in any variant (C_elec = 0 for every seed, C_j and P_j; charger utilisation 0; operational cost 439.2 for C_j = 1..4 and P_j = 0.7..4 kW), because the initial full spares cover the few swaps and (18) is slack. The baseline's ASAP HIGH_FIRST rule does charge (C_elec 1.9-3.0) but gains nothing from it, so its operational cost *increases* with P_j (853.6 -> 854.9 for seed 0) and with C_j: the marginal value per charger is -0.24 and per kW -0.34 for the baseline. The grid-group limit (21) never binds (peak 0-3.3 kW against 6-8 kW).
4. **Baseline-vs-ILP gap: P_i dominates completely.** At the default sizes the gap is 396 (71.6 % of the ILP total); the unserved component alone is 400 (4.67 vs 0.67 unserved orders, P_i = 100), i.e. `unserved_share_of_gap` = 1.01, with lateness +12.7 and travel +9.5 for the baseline offset by a *lower* response term (-29, it serves fewer orders). The baseline's 5 / 3 / 6 unserved orders are identical at every B_j, C_j, P_j, so they are a dispatch effect (nearest-feasible FIFO assignment with the threshold swap rule), not a station-sizing effect. The ILP's 0.67 mean unserved is one order in each of seeds 1 and 2 that no size can serve (same at B_j = 6, C_j = 4): it is time-window / energy infeasible for every bike, not a stock-out.
5. **Service metrics.** The ILP's swap-wait slots are 0.3-3.3 in total (never a stock-out with a queued bike); at B_j = 1 the ILP tolerates 39 site-slots with empty full stock because no bike needs one. Desk occupancy is at most 5 % of the single swap position, idle-full-stock share is 1.0 for B_j >= 3 (a full battery sits unused in every slot at every site). The B x C grid is a pure setup-cost plane for both methods (ILP operational 439.2-439.4, baseline 834.3-835.3 on all nine cells); the cheapest cell is (B_j, C_j) = (2, 1) for both (523.4 and 918.3).
6. **Value of coordination in this regime** is therefore almost entirely in dispatching (serving 4-5 more orders at 100 each); the sizing lever is inactive. The swap-stressed supplement `stressed_lowq0/` (same instances, bikes start at q0 ~ U{3..6} of 12) is where the sizing question has content: there the ILP's marginal battery value is 61.9 (1 -> 2 spares per site) and 0.3-1.0 afterwards, the baseline needs ~4 spares per site to reach the service level the ILP reaches with 2, and one charger per site suffices for the ILP while the baseline gains from a second one. See `stressed_lowq0/RESULTS.md`.

### Anomalies and caveats

- Probe run (seed 0, `B4_C1_P4`, Threads 4, time limit 120 s): Gurobi ended at the time limit with **no incumbent** (the baseline start was rejected by (18)), yet the same instance solved to optimality in 21-25 s in two later runs; this is run-to-run heuristic variability under a shared CPU (load 10-15 on 12 cores while E2/E3 ran concurrently), and it is why the warm-start chain was added for the one-charger variants.
- The baseline is *not* feasible for the written model at small B_j: it violates (17) (R_end = 1) at 1-3 sites in 22 of its 51 runs and (18) in 16; these families are report-only by design, so the baseline totals include no penalty for ending with an empty site.
- Wall time: 48.8 min for 132 rows (81 ILP solves, 1.43-1.52 M binaries, 80,306 rows, mean 24 s, max 74 s for the free-size run) with the stressed supplement (41 min) and two other experiments running on the same 12-core machine; the Threads 4 / 150 s settings were respected and every solve finished OPTIMAL (max MIPGap 1e-4).
- `tests/test_experiments.py::test_option_encoder_round_trip` fails in the full suite order but passes in isolation (order-dependent state; not in a file owned by this experiment).
