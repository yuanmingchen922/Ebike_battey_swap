# E4u round 3 -- provenance

Rows by method and source (round2 = reused ILP rows of outputs/e4u_sizing_usd, OPTIMAL or gap <= 1 %; round3 = solved here, Threads 3, Seed 0, TimeLimit 300 s; every baseline row is recomputed in round 3):

| method | source | n |
|---|---|---|
| ILP | round2 | 29 |
| ILP | round3 | 43 |
| baseline | round3 | 66 |

# E4u -- station sizing under USD (spares B_j, chargers C_j, power P_j), usd4h family

Family `usd4h` (DECISIONS R2.2: |K| = 6, |I| = 36, H = 48 slots of 5 min (17:00-21:00), L = 12, q0 ~ U{4..7} = 30-60 %, p_ch = 0.667 kW), 3 co-located sites (K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, grid group 8 kW / 6 kW 18-20 h), seeds [0, 1, 2, 3, 4, 5] on the sweep lines, seeds [0] on the off-line B x C cells; cost variant `usd_sunk` (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03 $, bB 0.332 $, bC 0.082 $ per site per 4 h). Pruning: plan defaults + reachable (lossless on this family, R2 implementation notes). Gurobi Threads 3, TimeLimit 300 s, OutputFlag 0; wall 96.7 min. Baseline = round-2 rules (R2.3). Instances are byte-identical across methods and sizes (only B_j, C_j, P_kw change).

Costs in USD per 4 h window. `total` is (26) including the setup constant (27) `F_j + bB B_j + bC C_j`; `operational` = total - C_setup. Marginal values = finite differences of the seed-mean cost per *one unit added at one site* (network change / 3 sites / step), per window and per year (x 1460 = 16 h/4 h x 365). Headline gap = (baseline - ILP) / baseline.

## What the coordinator buys: ILP with B_j, C_j free (y_j = 1 fixed) at usd_sunk prices, and the baseline at those sizes

| seed | sweep | method | status | total | operational | C_setup | C_orders | unserved | response | lateness | C_elec | served_share | n_swaps | chosen_B | chosen_C | sum_B | sum_C | charger_util_mean | idle_full_share_mean | end_full_total | gap | runtime_s | mip_start_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | free | ILP | OPTIMAL | 613.83 | 576.17 | 37.66 | 562.50 | 30 | 523.50 | 9 | 1.17 | 0.97 | 9 | {"S1": 2, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 4 | 3 | 0.46 | 0.47 | 3 | 0.00 | 190.92 | - |
| 0 | free_fixed | ILP | OPTIMAL | 613.83 | 576.17 | 37.66 | 562.50 | 30 | 523.50 | 9 | 1.17 | 0.97 | 9 | {"S1": 2, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 4 | 3 | 0.46 | 0.47 | 3 | 0.00 | 65.30 | True |
| 0 | free_fixed | baseline | - | 790.37 | 752.71 | 37.66 | 738 | 30 | 600 | 108 | 1.08 | 0.97 | 8 | {"S1": 2, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 4 | 3 | 0.42 | 0.58 | 1 | - | 0.00 | - |
| 1 | free | ILP | OPTIMAL | 657.99 | 620.74 | 37.25 | 609 | 150 | 456 | 3 | 0.94 | 0.86 | 6 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.55 | 0.41 | 3 | 0.00 | 129.77 | - |
| 1 | free_fixed | ILP | OPTIMAL | 657.99 | 620.74 | 37.25 | 609 | 150 | 456 | 3 | 0.94 | 0.86 | 6 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.55 | 0.41 | 3 | 0.00 | 69.93 | True |
| 1 | free_fixed | baseline | - | 1175.98 | 1138.73 | 37.25 | 1126.50 | 300 | 547.50 | 279 | 0.75 | 0.72 | 7 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.44 | 0.48 | 0 | - | 0.00 | - |
| 2 | free | ILP | OPTIMAL | 637.63 | 600.05 | 37.58 | 588 | 120 | 465 | 3 | 0.85 | 0.89 | 6 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 4 | 2 | 0.50 | 0.53 | 3 | 0.00 | 169.61 | - |
| 2 | free_fixed | ILP | OPTIMAL | 637.63 | 600.05 | 37.58 | 588 | 120 | 465 | 3 | 0.85 | 0.89 | 6 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 4 | 2 | 0.50 | 0.53 | 3 | 0.00 | 50.19 | True |
| 2 | free_fixed | baseline | - | 908.86 | 871.28 | 37.58 | 859.50 | 300 | 448.50 | 111 | 0.78 | 0.72 | 7 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 4 | 2 | 0.46 | 0.48 | 1 | - | 0.00 | - |
| 3 | free | ILP | OPTIMAL | 661.14 | 623.81 | 37.33 | 610.50 | 150 | 460.50 | 0 | 1.07 | 0.86 | 7 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 3 | 3 | 0.42 | 0.28 | 3 | 0.00 | 106.59 | - |
| 3 | free_fixed | ILP | OPTIMAL | 661.14 | 623.81 | 37.33 | 610.50 | 150 | 460.50 | 0 | 1.07 | 0.86 | 7 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 3 | 3 | 0.42 | 0.28 | 3 | 0.00 | 85.89 | True |
| 3 | free_fixed | baseline | - | 1064.05 | 1026.71 | 37.33 | 1014 | 390 | 444 | 180 | 0.98 | 0.64 | 7 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 3 | 3 | 0.38 | 0.57 | 0 | - | 0.00 | - |
| 4 | free | ILP | OPTIMAL | 613.16 | 575.83 | 37.33 | 564 | 90 | 474 | 0 | 0.89 | 0.92 | 6 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 3 | 3 | 0.35 | 0.40 | 3 | 0.00 | 212.87 | - |
| 4 | free_fixed | ILP | OPTIMAL | 613.16 | 575.83 | 37.33 | 564 | 90 | 474 | 0 | 0.89 | 0.92 | 6 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 3 | 3 | 0.35 | 0.40 | 3 | 0.00 | 85.82 | True |
| 4 | free_fixed | baseline | - | 792.77 | 755.43 | 37.33 | 744 | 150 | 513 | 81 | 1.08 | 0.86 | 7 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 3 | 3 | 0.42 | 0.53 | 1 | - | 0.00 | - |
| 5 | free | ILP | OPTIMAL | 655.82 | 618.08 | 37.75 | 604.50 | 120 | 481.50 | 3 | 1.10 | 0.89 | 8 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 2, "S3": 1} | 4 | 4 | 0.33 | 0.46 | 3 | 0.00 | 205.78 | - |
| 5 | free_fixed | ILP | OPTIMAL | 655.82 | 618.08 | 37.75 | 604.50 | 120 | 481.50 | 3 | 1.10 | 0.89 | 8 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 2, "S3": 1} | 4 | 4 | 0.33 | 0.46 | 3 | 0.00 | 106.94 | True |
| 5 | free_fixed | baseline | - | 1179.08 | 1141.33 | 37.75 | 1126.50 | 150 | 646.50 | 330 | 1.26 | 0.86 | 7 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 2, "S3": 1} | 4 | 4 | 0.42 | 0.55 | 3 | - | 0.00 | - |

## Sweep B: B_j (C_j = 2, P_kw = 4; seed means, min/max over seeds for total)

| method | B_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | served_share_mean | mean_response_h_mean | max_lateness_h_mean | n_late_mean | bike_km_mean | n_swaps_mean | kwh_purchased_mean | swap_wait_slots_mean | stockout_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | end_full_total_mean | marginal_operational_per_unit_window | marginal_total_per_unit_window | marginal_total_per_unit_year | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 6 | 640.61 | 613.41 | 661.38 | 603.03 | 37.58 | 115 | 472.75 | 2.50 | 1.06 | 11.72 | 0.89 | 0.82 | 0.06 | 0.83 | 97.67 | 7.33 | 3.31 | 5 | 105.33 | 0.21 | 0.05 | 0.22 | 1.89 | 3 | 0.35 | 0.02 | 25.67 | 132.23 | 300.11 | 0.00 |
| ILP | 2 | 6 | 640.56 | 613.93 | 661.78 | 601.98 | 38.57 | 110 | 476.75 | 3 | 0.56 | 11.67 | 0.90 | 0.82 | 0.06 | 1 | 97.28 | 7 | 1.75 | 4.17 | 43 | 0.11 | 0.05 | 0.68 | 1.67 | 3 | 0.07 | -0.27 | -389.33 | 119.63 | 219.57 | 0.00 |
| ILP | 3 | 6 | 641.36 | 614.78 | 662.63 | 601.79 | 39.57 | 110 | 476.75 | 3 | 0.40 | 11.64 | 0.90 | 0.82 | 0.06 | 1 | 96.98 | 7.17 | 1.25 | 3.33 | 21.33 | 0.08 | 0.05 | 0.84 | 1.78 | 5 | 0.09 | -0.25 | -359.27 | 121.22 | 227.26 | 0.00 |
| ILP | 4 | 6 | 642.10 | 615.47 | 663.41 | 601.53 | 40.57 | 110 | 476.75 | 3 | 0.14 | 11.64 | 0.90 | 0.82 | 0.06 | 1 | 96.98 | 7.17 | 0.44 | 3.67 | 3.17 | 0.03 | 0.05 | 0.97 | 0.44 | 6 | 0.02 | -0.31 | -452.98 | 104.47 | 150.26 | 0.00 |
| ILP | 6 | 6 | 643.96 | 617.47 | 665.26 | 601.40 | 42.56 | 110 | 476.75 | 3 | 0.02 | 11.63 | 0.90 | 0.82 | 0.06 | 1 | 96.93 | 7.67 | 0.06 | 6.33 | 0 | 0.00 | 0.05 | 1 | 0.11 | 10.50 | - | - | - | 111.22 | 187.75 | 0 |
| baseline | 1 | 6 | 1022.90 | 793.01 | 1270.96 | 985.32 | 37.58 | 230 | 538.50 | 204 | 1.09 | 11.73 | 0.79 | 1.06 | 0.69 | 14.17 | 97.75 | 7.17 | 3.42 | 20 | 61.50 | 0.21 | 0.05 | 0.52 | 2 | 1.17 | 44.55 | 44.22 | 64561.65 | 0.00 | 0.00 | - |
| baseline | 2 | 6 | 890.24 | 684.74 | 1132.18 | 851.67 | 38.57 | 135 | 557 | 145.50 | 1.17 | 13.00 | 0.88 | 0.98 | 0.51 | 13.83 | 108.32 | 6.83 | 3.65 | 2 | 18 | 0.23 | 0.05 | 0.86 | 2.78 | 5 | 6.47 | 6.14 | 8967.18 | 0.00 | 0.00 | - |
| baseline | 3 | 6 | 871.81 | 685.14 | 1116.37 | 832.24 | 39.57 | 145 | 543.50 | 130 | 0.82 | 12.92 | 0.87 | 0.97 | 0.54 | 12.67 | 107.67 | 7.17 | 2.57 | 0.17 | 8.33 | 0.16 | 0.05 | 0.93 | 2.22 | 5.50 | -0.35 | -0.68 | -993.63 | 0.00 | 0.00 | - |
| baseline | 4 | 6 | 873.86 | 685.82 | 1117.23 | 833.29 | 40.57 | 140 | 547.25 | 132.50 | 0.61 | 12.93 | 0.87 | 0.97 | 0.53 | 12.83 | 107.77 | 7.17 | 1.90 | 0.17 | 1 | 0.12 | 0.05 | 0.99 | 1.78 | 7.33 | 1.42 | 1.09 | 1590.65 | 0.00 | 0.00 | - |
| baseline | 6 | 6 | 867.32 | 687.44 | 1118.67 | 824.76 | 42.56 | 140 | 544.25 | 127.50 | 0.20 | 12.81 | 0.87 | 0.97 | 0.51 | 12.83 | 106.75 | 7 | 0.63 | 0.17 | 0 | 0.04 | 0.05 | 1 | 0.89 | 11.67 | - | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit_window` at size s = (cost(s) - cost(next s)) per added battery at one site per 4 h window (positive = adding the unit saves cost); `*_per_unit_year` = x 1460. `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H); `desk_occupancy` = occupancy of the single swap position (22); `idle_full_share` = share of slots with an unused full battery; `end_full_total` = sum_j n_jLH, the (18) left-hand side.

## Sweep C: C_j (B_j = 3, P_kw = 4; seed means, min/max over seeds for total)

| method | C_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | served_share_mean | mean_response_h_mean | max_lateness_h_mean | n_late_mean | bike_km_mean | n_swaps_mean | kwh_purchased_mean | swap_wait_slots_mean | stockout_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | end_full_total_mean | marginal_operational_per_unit_window | marginal_total_per_unit_window | marginal_total_per_unit_year | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 3 | 637.66 | 614.90 | 659.36 | 598.34 | 39.32 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 5.67 | 27.33 | 0.16 | 0.05 | 0.80 | 1.56 | 5 | -1.15 | -1.23 | -1797.84 | 95.64 | 112.23 | 0 |
| ILP | 2 | 6 | 641.36 | 614.78 | 662.63 | 601.79 | 39.57 | 110 | 476.75 | 3 | 0.40 | 11.64 | 0.90 | 0.82 | 0.06 | 1 | 96.98 | 7.17 | 1.25 | 3.33 | 21.33 | 0.08 | 0.05 | 0.84 | 1.78 | 5 | 1.15 | 1.07 | 1558.40 | 121.22 | 227.26 | 0.00 |
| ILP | 3 | 3 | 638.15 | 615.39 | 659.85 | 598.34 | 39.82 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 4.67 | 27 | 0.05 | 0.05 | 0.80 | 2 | 5 | -0.01 | -0.09 | -128.37 | 90.92 | 119.18 | 0 |
| ILP | 4 | 3 | 638.42 | 615.69 | 660.09 | 598.36 | 40.06 | 100 | 481.50 | 5 | 0.43 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.35 | 4.33 | 27 | 0.04 | 0.05 | 0.80 | 1.56 | 5 | - | - | - | 94.13 | 117.85 | 0.00 |
| baseline | 1 | 3 | 831.65 | 732.59 | 972.73 | 792.33 | 39.32 | 150 | 527 | 102 | 0.59 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 1.85 | 0.33 | 10.67 | 0.23 | 0.05 | 0.91 | 1.11 | 4.33 | -13.30 | -13.39 | -19544.59 | 0.00 | 0.00 | - |
| baseline | 2 | 6 | 871.81 | 685.14 | 1116.37 | 832.24 | 39.57 | 145 | 543.50 | 130 | 0.82 | 12.92 | 0.87 | 0.97 | 0.54 | 12.67 | 107.67 | 7.17 | 2.57 | 0.17 | 8.33 | 0.16 | 0.05 | 0.93 | 2.22 | 5.50 | 13.19 | 13.11 | 19137.88 | 0.00 | 0.00 | - |
| baseline | 3 | 3 | 832.49 | 733.45 | 973.61 | 792.67 | 39.82 | 150 | 527 | 102 | 0.94 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.93 | 0.33 | 7.67 | 0.12 | 0.05 | 0.94 | 2.67 | 6.33 | 0 | -0.08 | -119.72 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 832.74 | 733.70 | 973.86 | 792.67 | 40.06 | 150 | 527 | 102 | 0.94 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.93 | 0.33 | 7.67 | 0.09 | 0.05 | 0.94 | 2.67 | 6.33 | - | - | - | 0.00 | 0.01 | - |

`marginal_*_per_unit_window` at size s = (cost(s) - cost(next s)) per added charger at one site per 4 h window (positive = adding the unit saves cost); `*_per_unit_year` = x 1460. `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H); `desk_occupancy` = occupancy of the single swap position (22); `idle_full_share` = share of slots with an unused full battery; `end_full_total` = sum_j n_jLH, the (18) left-hand side.

## Sweep P: P_kw (B_j = 3, C_j = 4; seed means, min/max over seeds for total)

| method | P_kw | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | served_share_mean | mean_response_h_mean | max_lateness_h_mean | n_late_mean | bike_km_mean | n_swaps_mean | kwh_purchased_mean | swap_wait_slots_mean | stockout_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | end_full_total_mean | marginal_operational_per_unit_window | marginal_total_per_unit_window | marginal_total_per_unit_year | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1.40 | 3 | 638.40 | 615.64 | 660.09 | 598.34 | 40.06 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 4 | 16 | 0.04 | 0.05 | 0.88 | 1.56 | 5 | 0 | 0 | 0 | 97.50 | 130.07 | 0.00 |
| ILP | 2.80 | 3 | 638.40 | 615.64 | 660.09 | 598.34 | 40.06 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 5.33 | 29.33 | 0.04 | 0.05 | 0.78 | 1.56 | 5 | -0.00 | -0.00 | -7.21 | 104.35 | 141.40 | 0 |
| ILP | 4 | 3 | 638.42 | 615.69 | 660.09 | 598.36 | 40.06 | 100 | 481.50 | 5 | 0.43 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.35 | 4.33 | 27 | 0.04 | 0.05 | 0.80 | 1.56 | 5 | 0.03 | 0.03 | 43.26 | 94.13 | 117.85 | 0.00 |
| ILP | 4.20 | 3 | 638.40 | 615.64 | 660.09 | 598.34 | 40.06 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 2.67 | 32.33 | 0.04 | 0.05 | 0.76 | 2 | 5 | - | - | - | 106.49 | 140.78 | 0.00 |
| baseline | 1.40 | 3 | 832.65 | 733.59 | 973.74 | 792.59 | 40.06 | 150 | 527 | 102 | 0.85 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.65 | 0.33 | 7.67 | 0.08 | 0.05 | 0.94 | 2.22 | 5.33 | -0.02 | -0.02 | -30.90 | 0.00 | 0.00 | - |
| baseline | 2.80 | 3 | 832.74 | 733.70 | 973.86 | 792.67 | 40.06 | 150 | 527 | 102 | 0.94 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.93 | 0.33 | 7.67 | 0.09 | 0.05 | 0.94 | 2.67 | 6.33 | 0 | 0 | 0 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 832.74 | 733.70 | 973.86 | 792.67 | 40.06 | 150 | 527 | 102 | 0.94 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.93 | 0.33 | 7.67 | 0.09 | 0.05 | 0.94 | 2.67 | 6.33 | 0 | 0 | 0 | 0.00 | 0.01 | - |
| baseline | 4.20 | 3 | 832.74 | 733.70 | 973.86 | 792.67 | 40.06 | 150 | 527 | 102 | 0.94 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.93 | 0.33 | 7.67 | 0.09 | 0.05 | 0.94 | 2.67 | 6.33 | - | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit_window` at size s = (cost(s) - cost(next s)) per added kW at one site per 4 h window (positive = adding the unit saves cost); `*_per_unit_year` = x 1460. `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H); `desk_occupancy` = occupancy of the single swap position (22); `idle_full_share` = share of slots with an unused full battery; `end_full_total` = sum_j n_jLH, the (18) left-hand side.

## Spares the baseline needs to match the ILP service level (B sweep, C_j = 2, P_j = 4 kW)

| seed | ilp_B | ilp_served_share | ilp_total | ilp_mean_response_h | baseline_served_share_at_B3 | baseline_B_to_match_served_share | baseline_B_to_match_served_and_response | baseline_B_to_match_total_cost | baseline_served_share_at_max_B | baseline_total_at_max_B | max_B_swept |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 3 | 0.972 | 615.146 | 0.831 | 0.972 | 2 | - | - | 0.972 | 735.304 | 6 |
| 1 | 3 | 0.861 | 659.601 | 0.817 | 0.806 | - | - | - | 0.806 | 927.211 | 6 |
| 2 | 3 | 0.889 | 638.979 | 0.807 | 0.806 | - | - | - | 0.806 | 792.436 | 6 |
| 3 | 3 | 0.861 | 662.630 | 0.825 | 0.778 | - | - | - | 0.806 | 942.860 | 6 |
| 4 | 3 | 0.917 | 614.780 | 0.798 | 0.917 | 2 | - | - | 0.917 | 687.437 | 6 |
| 5 | 3 | 0.889 | 657.005 | 0.836 | 0.917 | 2 | - | - | 0.917 | 1118.669 | 6 |

Reference = the ILP at the R2.2 default B_j = 3; `baseline_B_to_match_*` = smallest B_j in the sweep at which the baseline reaches the ILP's served share / served share and mean response / total cost (`-` = not reached up to B_j = 6).

## Gap decomposition: baseline - ILP by cost component (seed means; gap % of baseline)

| sweep | size | n_seeds | baseline_total | ilp_total | gap_total | gap_pct_of_baseline | gap_unserved | gap_response | gap_lateness | gap_C_travel | gap_C_elec | baseline_served_share | ilp_served_share | baseline_n_unserved | ilp_n_unserved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 1 | 6 | 1022.90 | 640.61 | 382.29 | 37.37 | 115 | 65.75 | 201.50 | 0.01 | 0.03 | 0.79 | 0.89 | 7.67 | 3.83 |
| B | 2 | 6 | 890.24 | 640.56 | 249.68 | 28.05 | 25 | 80.25 | 142.50 | 1.33 | 0.61 | 0.88 | 0.90 | 4.50 | 3.67 |
| B | 3 | 6 | 871.81 | 641.36 | 230.46 | 26.43 | 35 | 66.75 | 127 | 1.28 | 0.42 | 0.87 | 0.90 | 4.83 | 3.67 |
| B | 4 | 6 | 873.86 | 642.10 | 231.76 | 26.52 | 30 | 70.50 | 129.50 | 1.30 | 0.47 | 0.87 | 0.90 | 4.67 | 3.67 |
| B | 6 | 6 | 867.32 | 643.96 | 223.36 | 25.75 | 30 | 67.50 | 124.50 | 1.18 | 0.18 | 0.87 | 0.90 | 4.67 | 3.67 |
| C | 1 | 3 | 831.65 | 637.66 | 193.99 | 23.33 | 50 | 45.50 | 97 | 1.31 | 0.18 | 0.86 | 0.91 | 5 | 3.33 |
| C | 2 | 6 | 871.81 | 641.36 | 230.46 | 26.43 | 35 | 66.75 | 127 | 1.28 | 0.42 | 0.87 | 0.90 | 4.83 | 3.67 |
| C | 3 | 3 | 832.49 | 638.15 | 194.34 | 23.34 | 50 | 45.50 | 97 | 1.31 | 0.52 | 0.86 | 0.91 | 5 | 3.33 |
| C | 4 | 3 | 832.74 | 638.42 | 194.32 | 23.33 | 50 | 45.50 | 97 | 1.31 | 0.50 | 0.86 | 0.91 | 5 | 3.33 |
| P | 1.40 | 3 | 832.65 | 638.40 | 194.25 | 23.33 | 50 | 45.50 | 97 | 1.31 | 0.43 | 0.86 | 0.91 | 5 | 3.33 |
| P | 2.80 | 3 | 832.74 | 638.40 | 194.34 | 23.34 | 50 | 45.50 | 97 | 1.31 | 0.52 | 0.86 | 0.91 | 5 | 3.33 |
| P | 4 | 3 | 832.74 | 638.42 | 194.32 | 23.33 | 50 | 45.50 | 97 | 1.31 | 0.50 | 0.86 | 0.91 | 5 | 3.33 |
| P | 4.20 | 3 | 832.74 | 638.40 | 194.34 | 23.34 | 50 | 45.50 | 97 | 1.31 | 0.52 | 0.86 | 0.91 | 5 | 3.33 |

## B x C grid (P_j = 4 kW; seed means, `n_seeds` per cell)

ILP:

| B_j | C_j | total | operational | C_orders | n_unserved | served_share | swap_wait_slots | stockout_slots | charger_util_mean | n_seeds |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 615.62 | 578.28 | 565.50 | 2 | 0.94 | 5 | 81 | 0.42 | 1 |
| 1 | 2 | 640.61 | 603.03 | 590.25 | 3.83 | 0.89 | 5 | 105.33 | 0.21 | 6 |
| 1 | 3 | 616.11 | 578.28 | 565.50 | 2 | 0.94 | 0 | 85 | 0.14 | 1 |
| 1 | 4 | 616.42 | 578.35 | 565.50 | 2 | 0.94 | 6 | 93 | 0.12 | 1 |
| 2 | 1 | 614.21 | 575.88 | 562.50 | 1 | 0.97 | 12 | 85 | 0.36 | 1 |
| 2 | 2 | 640.56 | 601.98 | 589.75 | 3.67 | 0.90 | 4.17 | 43 | 0.11 | 6 |
| 2 | 3 | 614.67 | 575.85 | 562.50 | 1 | 0.97 | 7 | 33 | 0.11 | 1 |
| 2 | 4 | 614.91 | 575.85 | 562.50 | 1 | 0.97 | 6 | 38 | 0.08 | 1 |
| 3 | 1 | 637.66 | 598.34 | 586.50 | 3.33 | 0.91 | 5.67 | 27.33 | 0.16 | 3 |
| 3 | 2 | 641.36 | 601.79 | 589.75 | 3.67 | 0.90 | 3.33 | 21.33 | 0.08 | 6 |
| 3 | 3 | 638.15 | 598.34 | 586.50 | 3.33 | 0.91 | 4.67 | 27 | 0.05 | 3 |
| 3 | 4 | 638.42 | 598.36 | 586.50 | 3.33 | 0.91 | 4.33 | 27 | 0.04 | 3 |
| 4 | 1 | 615.59 | 575.27 | 562.50 | 1 | 0.97 | 5 | 8 | 0.18 | 1 |
| 4 | 2 | 642.10 | 601.53 | 589.75 | 3.67 | 0.90 | 3.67 | 3.17 | 0.03 | 6 |
| 4 | 3 | 616.09 | 575.27 | 562.50 | 1 | 0.97 | 2 | 8 | 0.06 | 1 |
| 4 | 4 | 616.33 | 575.27 | 562.50 | 1 | 0.97 | 4 | 3 | 0.05 | 1 |
| 6 | 1 | 617.23 | 574.92 | 562.50 | 1 | 0.97 | 3 | 0 | 0.04 | 1 |
| 6 | 2 | 643.96 | 601.40 | 589.75 | 3.67 | 0.90 | 6.33 | 0 | 0.00 | 6 |
| 6 | 3 | 617.72 | 574.92 | 562.50 | 1 | 0.97 | 3 | 0 | 0.01 | 1 |
| 6 | 4 | 617.97 | 574.92 | 562.50 | 1 | 0.97 | 3 | 0 | 0.01 | 1 |

Baseline on the same grid:

| B_j | C_j | total | operational | C_orders | n_unserved | served_share | swap_wait_slots | stockout_slots | charger_util_mean | n_seeds |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1010.31 | 972.98 | 960 | 3 | 0.92 | 25 | 61 | 0.42 | 1 |
| 1 | 2 | 1022.90 | 985.32 | 972.50 | 7.67 | 0.79 | 20 | 61.50 | 0.21 | 6 |
| 1 | 3 | 1010.81 | 972.98 | 960 | 3 | 0.92 | 25 | 61 | 0.14 | 1 |
| 1 | 4 | 1011.05 | 972.98 | 960 | 3 | 0.92 | 25 | 61 | 0.11 | 1 |
| 2 | 1 | 766.84 | 728.52 | 714 | 1 | 0.97 | 0 | 29 | 0.34 | 1 |
| 2 | 2 | 890.24 | 851.67 | 837.50 | 4.50 | 0.88 | 2 | 18 | 0.23 | 6 |
| 2 | 3 | 767.71 | 728.89 | 714 | 1 | 0.97 | 0 | 23 | 0.16 | 1 |
| 2 | 4 | 767.95 | 728.89 | 714 | 1 | 0.97 | 0 | 23 | 0.12 | 1 |
| 3 | 1 | 831.65 | 792.33 | 779 | 5 | 0.86 | 0.33 | 10.67 | 0.23 | 3 |
| 3 | 2 | 871.81 | 832.24 | 818.50 | 4.83 | 0.87 | 0.17 | 8.33 | 0.16 | 6 |
| 3 | 3 | 832.49 | 792.67 | 779 | 5 | 0.86 | 0.33 | 7.67 | 0.12 | 3 |
| 3 | 4 | 832.74 | 792.67 | 779 | 5 | 0.86 | 0.33 | 7.67 | 0.09 | 3 |
| 4 | 1 | 733.47 | 693.15 | 679.50 | 1 | 0.97 | 0 | 0 | 0.23 | 1 |
| 4 | 2 | 873.86 | 833.29 | 819.75 | 4.67 | 0.87 | 0.17 | 1 | 0.12 | 6 |
| 4 | 3 | 734.22 | 693.40 | 679.50 | 1 | 0.97 | 0 | 0 | 0.11 | 1 |
| 4 | 4 | 734.46 | 693.40 | 679.50 | 1 | 0.97 | 0 | 0 | 0.08 | 1 |
| 6 | 1 | 735.06 | 692.75 | 679.50 | 1 | 0.97 | 0 | 0 | 0.07 | 1 |
| 6 | 2 | 867.32 | 824.76 | 811.75 | 4.67 | 0.87 | 0.17 | 0 | 0.04 | 6 |
| 6 | 3 | 735.55 | 692.75 | 679.50 | 1 | 0.97 | 0 | 0 | 0.02 | 1 |
| 6 | 4 | 735.80 | 692.75 | 679.50 | 1 | 0.97 | 0 | 0 | 0.02 | 1 |

## Solver statistics

- ILP runs: 72; statuses {'OPTIMAL': 69, 'TIME_LIMIT': 3}; arcs 1,032,959-1,207,072; binaries 1,032,998-1,207,111; rows 58,961-65,034; solve time mean 118.4 s, max 300.1 s; MIP gap max 0.0029; arc build mean 2.28 s; model build mean 4.10 s; every ILP schedule passes `evaluate.check`: True; MIP start accepted in 59 of 66 runs with a start; start variants {'default': 55, None: 6, 'chain:free': 6, 'baseline_reserve': 3, 'baseline_round1': 2}.
- baseline: 66 runs, reported families ['{"(17)": 1, "(18)": 1}', '{"(17)": 1}', '{"(17)": 2, "(18)": 1}', '{"(17)": 3, "(18)": 1}', '{"(18)": 1}', '{}'] (only the report-only families (9), (17), (18) may appear); identity (24) holds on all schedules: True; ILP <= baseline on every variant: True.

## Figures

- `cost_vs_B.png`
- `cost_vs_C.png`
- `cost_vs_P.png`
- `heatmap_BxC.png`

## Interpretation and anomalies

(not written yet: put the text in INTERPRETATION.md next to this file and re-run with --report-only)
