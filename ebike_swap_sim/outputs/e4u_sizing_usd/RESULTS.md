# E4u -- station sizing under USD (spares B_j, chargers C_j, power P_j), usd4h family

Family `usd4h` (DECISIONS R2.2: |K| = 6, |I| = 36, H = 48 slots of 5 min (17:00-21:00), L = 12, q0 ~ U{4..7} = 30-60 %, p_ch = 0.667 kW), 3 co-located sites (K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, grid group 8 kW / 6 kW 18-20 h), seeds [0, 1, 2] on the sweep lines, seeds [0] on the off-line B x C cells; cost variant `usd_sunk` (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03 $, bB 0.332 $, bC 0.082 $ per site per 4 h). Pruning: plan defaults + reachable (lossless on this family, R2 implementation notes). Gurobi Threads 3, TimeLimit 300 s, OutputFlag 0; wall 57.6 min. Baseline = round-2 rules (R2.3). Instances are byte-identical across methods and sizes (only B_j, C_j, P_kw change).

Costs in USD per 4 h window. `total` is (26) including the setup constant (27) `F_j + bB B_j + bC C_j`; `operational` = total - C_setup. Marginal values = finite differences of the seed-mean cost per *one unit added at one site* (network change / 3 sites / step), per window and per year (x 1460 = 16 h/4 h x 365). Headline gap = (baseline - ILP) / baseline.

Runs skipped by the wall budget: 20 (seed 2 B3_C4_P4, seed 0 B3_C4_P1.4, seed 0 B3_C4_P2.8, seed 0 B3_C4_P4.2, seed 1 B3_C4_P1.4, seed 1 B3_C4_P2.8, seed 2 B3_C4_P1.4, seed 2 B3_C4_P2.8, seed 0 B1_C1_P4, seed 0 B1_C3_P4, seed 0 B1_C4_P4, seed 0 B2_C1_P4 ...).

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

## Sweep B: B_j (C_j = 2, P_kw = 4; seed means, min/max over seeds for total)

| method | B_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | served_share_mean | mean_response_h_mean | max_lateness_h_mean | n_late_mean | bike_km_mean | n_swaps_mean | kwh_purchased_mean | swap_wait_slots_mean | stockout_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | end_full_total_mean | marginal_operational_per_unit_window | marginal_total_per_unit_window | marginal_total_per_unit_year | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 3 | 637.56 | 616.42 | 658.32 | 599.98 | 37.58 | 110 | 473.50 | 4 | 1.08 | 11.40 | 0.90 | 0.81 | 0.08 | 1.33 | 95 | 7.33 | 3.37 | 5.33 | 103.67 | 0.21 | 0.05 | 0.23 | 1.78 | 3 | 0.47 | 0.14 | 203.32 | 157.87 | 300.11 | 0.00 |
| ILP | 2 | 3 | 637.14 | 614.42 | 658.78 | 598.56 | 38.57 | 100 | 481.50 | 5 | 0.58 | 11.48 | 0.91 | 0.82 | 0.08 | 1.67 | 95.70 | 7 | 1.81 | 2.33 | 40 | 0.11 | 0.05 | 0.70 | 1.56 | 3 | 0.08 | -0.26 | -374.77 | 105.76 | 158.97 | 0 |
| ILP | 3 | 3 | 637.91 | 615.15 | 659.60 | 598.34 | 39.57 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 4.67 | 26.67 | 0.08 | 0.05 | 0.81 | 1.78 | 5 | 0.08 | -0.25 | -363.59 | 110.12 | 173.59 | 0.00 |
| ILP | 4 | 3 | 638.66 | 615.88 | 660.37 | 598.09 | 40.57 | 100 | 481.50 | 5 | 0.17 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 0.52 | 3.33 | 6 | 0.03 | 0.05 | 0.95 | 0.44 | 6 | 0.02 | -0.31 | -453.00 | 102.41 | 146.72 | 0.00 |
| ILP | 6 | 3 | 640.52 | 617.48 | 662.36 | 597.96 | 42.56 | 100 | 481.50 | 5 | 0.04 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.67 | 0.11 | 7.33 | 0 | 0.01 | 0.05 | 1 | 0.22 | 10.67 | - | - | - | 102.77 | 122.88 | 0 |
| baseline | 1 | 3 | 1003.05 | 822.06 | 1176.52 | 965.47 | 37.58 | 200 | 553.50 | 199 | 1.08 | 11.89 | 0.81 | 1.05 | 0.67 | 15 | 99.05 | 7.33 | 3.39 | 24.33 | 61 | 0.21 | 0.05 | 0.53 | 2 | 1.33 | 48.82 | 48.49 | 70791.04 | 0.00 | 0.00 | - |
| baseline | 2 | 3 | 857.59 | 765.75 | 1039.55 | 819.01 | 38.57 | 140 | 543 | 122 | 1.17 | 12.85 | 0.87 | 0.97 | 0.47 | 13.33 | 107.05 | 7 | 3.65 | 4 | 21.67 | 0.23 | 0.05 | 0.83 | 2.67 | 5 | 8.81 | 8.48 | 12376.91 | 0.00 | 0.00 | - |
| baseline | 3 | 3 | 832.16 | 733.10 | 973.24 | 792.59 | 39.57 | 150 | 527 | 102 | 0.85 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.65 | 0.33 | 7.67 | 0.17 | 0.05 | 0.94 | 2.22 | 5.33 | 0.06 | -0.27 | -392.61 | 0.00 | 0.00 | - |
| baseline | 4 | 3 | 832.96 | 733.85 | 974.15 | 792.40 | 40.57 | 150 | 527 | 102 | 0.63 | 12.77 | 0.86 | 0.95 | 0.50 | 11.67 | 106.40 | 7.33 | 1.96 | 0.33 | 1.67 | 0.12 | 0.05 | 0.99 | 1.78 | 7.33 | 2.77 | 2.44 | 3563.64 | 0.00 | 0.00 | - |
| baseline | 6 | 3 | 818.32 | 735.30 | 927.21 | 775.76 | 42.56 | 150 | 521 | 92 | 0.24 | 12.52 | 0.86 | 0.93 | 0.47 | 11.67 | 104.35 | 7 | 0.74 | 0.33 | 0 | 0.05 | 0.05 | 1 | 0.89 | 11.67 | - | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit_window` at size s = (cost(s) - cost(next s)) per added battery at one site per 4 h window (positive = adding the unit saves cost); `*_per_unit_year` = x 1460. `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H); `desk_occupancy` = occupancy of the single swap position (22); `idle_full_share` = share of slots with an unused full battery; `end_full_total` = sum_j n_jLH, the (18) left-hand side.

## Sweep C: C_j (B_j = 3, P_kw = 4; seed means, min/max over seeds for total)

| method | C_j | n_seeds | total_mean | total_min | total_max | operational_mean | C_setup_mean | unserved_mean | response_mean | lateness_mean | C_elec_mean | C_travel_mean | served_share_mean | mean_response_h_mean | max_lateness_h_mean | n_late_mean | bike_km_mean | n_swaps_mean | kwh_purchased_mean | swap_wait_slots_mean | stockout_slots_mean | charger_util_mean_mean | desk_occupancy_mean_mean | idle_full_share_mean_mean | peak_kw_group_mean | end_full_total_mean | marginal_operational_per_unit_window | marginal_total_per_unit_window | marginal_total_per_unit_year | runtime_s_mean | runtime_s_max | gap_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP | 1 | 3 | 637.66 | 614.90 | 659.36 | 598.34 | 39.32 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 5.67 | 27.33 | 0.16 | 0.05 | 0.80 | 1.56 | 5 | 0 | -0.08 | -119.72 | 95.64 | 112.23 | 0 |
| ILP | 2 | 3 | 637.91 | 615.15 | 659.60 | 598.34 | 39.57 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 4.67 | 26.67 | 0.08 | 0.05 | 0.81 | 1.78 | 5 | 0 | -0.08 | -119.72 | 110.12 | 173.59 | 0.00 |
| ILP | 3 | 3 | 638.15 | 615.39 | 659.85 | 598.34 | 39.82 | 100 | 481.50 | 5 | 0.41 | 11.42 | 0.91 | 0.82 | 0.08 | 1.67 | 95.20 | 7.33 | 1.30 | 4.67 | 27 | 0.05 | 0.05 | 0.80 | 2 | 5 | 0.17 | 0.09 | 127.69 | 90.92 | 119.18 | 0 |
| ILP | 4 | 2 | 637.89 | 615.69 | 660.09 | 597.83 | 40.06 | 90 | 489.75 | 6 | 0.52 | 11.56 | 0.92 | 0.82 | 0.08 | 2 | 96.30 | 8 | 1.64 | 5 | 29.50 | 0.05 | 0.06 | 0.78 | 1.67 | 5 | - | - | - | 102.19 | 117.85 | 0.00 |
| baseline | 1 | 3 | 831.65 | 732.59 | 972.73 | 792.33 | 39.32 | 150 | 527 | 102 | 0.59 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 1.85 | 0.33 | 10.67 | 0.23 | 0.05 | 0.91 | 1.11 | 4.33 | -0.08 | -0.17 | -243.73 | 0.00 | 0.00 | - |
| baseline | 2 | 3 | 832.16 | 733.10 | 973.24 | 792.59 | 39.57 | 150 | 527 | 102 | 0.85 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.65 | 0.33 | 7.67 | 0.17 | 0.05 | 0.94 | 2.22 | 5.33 | -0.03 | -0.11 | -162.98 | 0.00 | 0.00 | - |
| baseline | 3 | 3 | 832.49 | 733.45 | 973.61 | 792.67 | 39.82 | 150 | 527 | 102 | 0.94 | 12.74 | 0.86 | 0.95 | 0.50 | 11.67 | 106.15 | 7.33 | 2.93 | 0.33 | 7.67 | 0.12 | 0.05 | 0.94 | 2.67 | 6.33 | -7.01 | -7.10 | -10360.34 | 0.00 | 0.00 | - |
| baseline | 4 | 2 | 853.78 | 733.70 | 973.86 | 813.72 | 40.06 | 120 | 559.50 | 120 | 0.99 | 13.23 | 0.89 | 0.98 | 0.46 | 14.50 | 110.25 | 7.50 | 3.08 | 0 | 9.50 | 0.10 | 0.05 | 0.92 | 3 | 6 | - | - | - | 0.00 | 0.00 | - |

`marginal_*_per_unit_window` at size s = (cost(s) - cost(next s)) per added charger at one site per 4 h window (positive = adding the unit saves cost); `*_per_unit_year` = x 1460. `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H); `desk_occupancy` = occupancy of the single swap position (22); `idle_full_share` = share of slots with an unused full battery; `end_full_total` = sum_j n_jLH, the (18) left-hand side.

## Spares the baseline needs to match the ILP service level (B sweep, C_j = 2, P_j = 4 kW)

| seed | ilp_B | ilp_served_share | ilp_total | ilp_mean_response_h | baseline_served_share_at_B3 | baseline_B_to_match_served_share | baseline_B_to_match_served_and_response | baseline_B_to_match_total_cost | baseline_served_share_at_max_B | baseline_total_at_max_B | max_B_swept |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 3 | 0.972 | 615.146 | 0.831 | 0.972 | 2 | - | - | 0.972 | 735.304 | 6 |
| 1 | 3 | 0.861 | 659.601 | 0.817 | 0.806 | - | - | - | 0.806 | 927.211 | 6 |
| 2 | 3 | 0.889 | 638.979 | 0.807 | 0.806 | - | - | - | 0.806 | 792.436 | 6 |

Reference = the ILP at the R2.2 default B_j = 3; `baseline_B_to_match_*` = smallest B_j in the sweep at which the baseline reaches the ILP's served share / served share and mean response / total cost (`-` = not reached up to B_j = 6).

## Gap decomposition: baseline - ILP by cost component (seed means; gap % of baseline)

| sweep | size | n_seeds | baseline_total | ilp_total | gap_total | gap_pct_of_baseline | gap_unserved | gap_response | gap_lateness | gap_C_travel | gap_C_elec | baseline_served_share | ilp_served_share | baseline_n_unserved | ilp_n_unserved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 1 | 3 | 1003.05 | 637.56 | 365.49 | 36.44 | 90 | 80 | 195 | 0.49 | 0.01 | 0.81 | 0.90 | 6.67 | 3.67 |
| B | 2 | 3 | 857.59 | 637.14 | 220.45 | 25.71 | 40 | 61.50 | 117 | 1.36 | 0.59 | 0.87 | 0.91 | 4.67 | 3.33 |
| B | 3 | 3 | 832.16 | 637.91 | 194.25 | 23.34 | 50 | 45.50 | 97 | 1.31 | 0.43 | 0.86 | 0.91 | 5 | 3.33 |
| B | 4 | 3 | 832.96 | 638.66 | 194.31 | 23.33 | 50 | 45.50 | 97 | 1.34 | 0.46 | 0.86 | 0.91 | 5 | 3.33 |
| B | 6 | 3 | 818.32 | 640.52 | 177.80 | 21.73 | 50 | 39.50 | 87 | 1.10 | 0.20 | 0.86 | 0.91 | 5 | 3.33 |
| C | 1 | 3 | 831.65 | 637.66 | 193.99 | 23.33 | 50 | 45.50 | 97 | 1.31 | 0.18 | 0.86 | 0.91 | 5 | 3.33 |
| C | 2 | 3 | 832.16 | 637.91 | 194.25 | 23.34 | 50 | 45.50 | 97 | 1.31 | 0.43 | 0.86 | 0.91 | 5 | 3.33 |
| C | 3 | 3 | 832.49 | 638.15 | 194.34 | 23.34 | 50 | 45.50 | 97 | 1.31 | 0.52 | 0.86 | 0.91 | 5 | 3.33 |
| C | 4 | 2 | 853.78 | 637.89 | 215.89 | 25.29 | 30 | 69.75 | 114 | 1.67 | 0.46 | 0.89 | 0.92 | 4 | 3 |

## B x C grid (P_j = 4 kW; seed means, `n_seeds` per cell)

ILP:

| B_j | C_j | total | operational | C_orders | n_unserved | served_share | swap_wait_slots | stockout_slots | charger_util_mean | n_seeds |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 637.56 | 599.98 | 587.50 | 3.67 | 0.90 | 5.33 | 103.67 | 0.21 | 3 |
| 2 | 2 | 637.14 | 598.56 | 586.50 | 3.33 | 0.91 | 2.33 | 40 | 0.11 | 3 |
| 3 | 1 | 637.66 | 598.34 | 586.50 | 3.33 | 0.91 | 5.67 | 27.33 | 0.16 | 3 |
| 3 | 2 | 637.91 | 598.34 | 586.50 | 3.33 | 0.91 | 4.67 | 26.67 | 0.08 | 3 |
| 3 | 3 | 638.15 | 598.34 | 586.50 | 3.33 | 0.91 | 4.67 | 27 | 0.05 | 3 |
| 3 | 4 | 637.89 | 597.83 | 585.75 | 3 | 0.92 | 5 | 29.50 | 0.05 | 2 |
| 4 | 2 | 638.66 | 598.09 | 586.50 | 3.33 | 0.91 | 3.33 | 6 | 0.03 | 3 |
| 6 | 2 | 640.52 | 597.96 | 586.50 | 3.33 | 0.91 | 7.33 | 0 | 0.01 | 3 |

Baseline on the same grid:

| B_j | C_j | total | operational | C_orders | n_unserved | served_share | swap_wait_slots | stockout_slots | charger_util_mean | n_seeds |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 1003.05 | 965.47 | 952.50 | 6.67 | 0.81 | 24.33 | 61 | 0.21 | 3 |
| 2 | 2 | 857.59 | 819.01 | 805 | 4.67 | 0.87 | 4 | 21.67 | 0.23 | 3 |
| 3 | 1 | 831.65 | 792.33 | 779 | 5 | 0.86 | 0.33 | 10.67 | 0.23 | 3 |
| 3 | 2 | 832.16 | 792.59 | 779 | 5 | 0.86 | 0.33 | 7.67 | 0.17 | 3 |
| 3 | 3 | 832.49 | 792.67 | 779 | 5 | 0.86 | 0.33 | 7.67 | 0.12 | 3 |
| 3 | 4 | 853.78 | 813.72 | 799.50 | 4 | 0.89 | 0 | 9.50 | 0.10 | 2 |
| 4 | 2 | 832.96 | 792.40 | 779 | 5 | 0.86 | 0.33 | 1.67 | 0.12 | 3 |
| 6 | 2 | 818.32 | 775.76 | 763 | 5 | 0.86 | 0.33 | 0 | 0.05 | 3 |

## Solver statistics

- ILP runs: 29; statuses {'OPTIMAL': 28, 'TIME_LIMIT': 1}; arcs 1,044,906-1,154,942; binaries 1,044,945-1,154,981; rows 60,032-63,124; solve time mean 109.5 s, max 300.1 s; MIP gap max 0.0029; arc build mean 2.24 s; model build mean 4.33 s; every ILP schedule passes `evaluate.check`: True; MIP start accepted in 25 of 26 runs with a start; start variants {'default': 19, None: 3, 'chain:free': 3, 'baseline_reserve': 3, 'baseline_round1': 1}.
- baseline: 26 runs, reported families ['{"(17)": 1, "(18)": 1}', '{"(17)": 1}', '{"(17)": 2, "(18)": 1}', '{"(17)": 3, "(18)": 1}', '{"(18)": 1}', '{}'] (only the report-only families (9), (17), (18) may appear); identity (24) holds on all schedules: True; ILP <= baseline on every variant: True.

## Figures

- `cost_vs_B.png`
- `cost_vs_C.png`
- `heatmap_BxC.png`

## Interpretation and anomalies

(not written yet: put the text in INTERPRETATION.md next to this file and re-run with --report-only)
