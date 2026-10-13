# E2 -- coordinated ILP vs event-driven baseline on identical demand

Instances: 10 bikes, |I| in {22, 30, 45} (demand x0.75 / x1.0 / x1.5 of 30 orders), H = 24 slots of 5 min, L = 12, 3 co-located fixed sites (B_j = 4, C_j = 3, M_j = 1, sigma_j = 1), hourly site <-> site shuttles (12 services; h, z free in the ILP, h = z = 0 in the baseline), seeds [0, 1, 2, 3, 4]. Pruning: reposition targets = restaurants + facilities + depots, tau_max = 4, start_slack = 6, reachable_pruning = True (lossless). Gurobi 13: OutputFlag 0, Threads 4, TimeLimit 240 s; 4 of 60 ILP solves hit the limit. Total wall time 39.0 min. One instance JSON per (seed, demand) in `instances/`; every method consumes the byte-identical instance and arc library (the rho = 0 pair uses a copy that differs only in `rho`).

## Headline

**The headline comparison is `baseline_rho0` vs `ilp_rho0`** (both with rho = 0, i.e. without the network recovery target (18), the family the baseline violates most often): there the baseline schedule is an accepted MIP start in 13 of 15 runs; the remaining 2 end with a local shortfall of (17) (R_end = 1 full spare per site, violated by the baseline in 2 runs), which the ILP meets at no measurable cost. Mean cost reduction **28.0 % (95 % CI +/- 7.2, n = 15)**; by demand: x0.75: 12.6 +/- 11.0 %, x1: 34.6 +/- 15.6 %, x1.5: 36.8 +/- 5.9 %; excluding the constant setup term (27) the operational cost falls by 31.8 % (+/- 7.5). With the written model (rho = 0.5) the reduction is 28.0 % (+/- 7.2); the baseline violates (18) in 3 of 15 runs, so its MIP start is rejected there (reported, not enforced, per DECISIONS.md).

## Relative improvement over the baseline (mean over seeds, 95 % t-CI)

| comparison | demand_mult | n_seeds | rel_impr_mean_pct | rel_impr_ci95_pct | rel_impr_lo_pct | rel_impr_hi_pct | abs_gain_mean | rel_impr_ex_setup_mean_pct | rel_impr_ex_setup_ci95_pct |
|---|---|---|---|---|---|---|---|---|---|
| ILP (rho=0.5) vs baseline | 0.75 | 5 | 12.59 | 10.99 | 1.60 | 23.59 | 59.46 | 16.65 | 14.04 |
| ILP (rho=0.5) vs baseline | 1 | 5 | 34.61 | 15.59 | 19.02 | 50.21 | 309.29 | 39.91 | 16.55 |
| ILP (rho=0.5) vs baseline | 1.50 | 5 | 36.84 | 5.86 | 30.98 | 42.69 | 810.59 | 38.86 | 6.20 |
| ILP (rho=0.5) vs baseline | all | 15 | 28.01 | 7.19 | 20.82 | 35.21 | 393.12 | 31.80 | 7.47 |
| ILP (rho=0) vs baseline [headline] | 0.75 | 5 | 12.59 | 10.99 | 1.60 | 23.59 | 59.46 | 16.65 | 14.04 |
| ILP (rho=0) vs baseline [headline] | 1 | 5 | 34.61 | 15.59 | 19.02 | 50.21 | 309.29 | 39.91 | 16.55 |
| ILP (rho=0) vs baseline [headline] | 1.50 | 5 | 36.83 | 5.90 | 30.93 | 42.73 | 810.46 | 38.85 | 6.24 |
| ILP (rho=0) vs baseline [headline] | all | 15 | 28.01 | 7.20 | 20.82 | 35.21 | 393.07 | 31.80 | 7.47 |
| ILP fixed arcs vs baseline | 0.75 | 5 | 1.47 | 0.87 | 0.60 | 2.34 | 6.51 | 1.99 | 1.19 |
| ILP fixed arcs vs baseline | 1 | 5 | 0.95 | 0.34 | 0.61 | 1.28 | 7.98 | 1.11 | 0.41 |
| ILP fixed arcs vs baseline | 1.50 | 5 | 0.19 | 0.10 | 0.09 | 0.30 | 4.29 | 0.21 | 0.11 |
| ILP fixed arcs vs baseline | all | 15 | 0.87 | 0.34 | 0.53 | 1.21 | 6.26 | 1.10 | 0.47 |
| ILP fixed assignment vs baseline | 0.75 | 5 | 1.65 | 1.19 | 0.46 | 2.85 | 7.31 | 2.24 | 1.63 |
| ILP fixed assignment vs baseline | 1 | 5 | 2.62 | 1.98 | 0.64 | 4.59 | 20.00 | 3.10 | 2.48 |
| ILP fixed assignment vs baseline | 1.50 | 5 | 1.23 | 0.72 | 0.51 | 1.95 | 27.62 | 1.30 | 0.75 |
| ILP fixed assignment vs baseline | all | 15 | 1.83 | 0.61 | 1.23 | 2.44 | 18.31 | 2.21 | 0.77 |
| baseline+opp. swap vs baseline | 0.75 | 5 | -0.09 | 0.13 | -0.22 | 0.04 | -0.42 | -0.12 | 0.17 |
| baseline+opp. swap vs baseline | 1 | 5 | 3.76 | 10.48 | -6.72 | 14.23 | 36.40 | 4.26 | 11.87 |
| baseline+opp. swap vs baseline | 1.50 | 5 | -0.00 | 0.01 | -0.01 | 0.00 | -0.09 | -0.00 | 0.01 |
| baseline+opp. swap vs baseline | all | 15 | 1.22 | 2.47 | -1.25 | 3.69 | 11.96 | 1.38 | 2.80 |
| baseline zone dispatch vs baseline | 0.75 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline zone dispatch vs baseline | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline zone dispatch vs baseline | 1.50 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline zone dispatch vs baseline | all | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

`rel_impr` = (cost_baseline - cost_method) / cost_baseline in % (plan definition); `rel_impr_ex_setup` divides by the baseline cost without the constant setup term (27) (C_setup = 114 for the fixed facilities), i.e. the operational-cost reduction; `abs_gain_mean` in toy units; negative = the method is worse than the baseline.

## Cost (26) and components (27)-(32): mean over seeds per demand level and method

| demand_mult | method | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb |
|---|---|---|---|---|---|---|---|---|---|
| 0.75 | baseline | 452.52 | 114 | 2.31 | 90.81 | 60 | 175 | 10.40 | 0 |
| 0.75 | baseline_opp | 452.94 | 114 | 2.73 | 90.81 | 60 | 175 | 10.40 | 0 |
| 0.75 | baseline_zone | 452.52 | 114 | 2.31 | 90.81 | 60 | 175 | 10.40 | 0 |
| 0.75 | ilp | 393.06 | 114 | 0 | 70.86 | 20 | 177.40 | 10.80 | 0 |
| 0.75 | ilp_fixed_arcs | 446.01 | 114 | 0 | 86.61 | 60 | 175 | 10.40 | 0 |
| 0.75 | ilp_fixed_assign | 445.21 | 114 | 0 | 86.01 | 60 | 174.80 | 10.40 | 0 |
| 0.75 | baseline_rho0 | 452.52 | 114 | 2.31 | 90.81 | 60 | 175 | 10.40 | 0 |
| 0.75 | ilp_rho0 | 393.06 | 114 | 0 | 70.86 | 20 | 177.80 | 10.40 | 0 |
| 1 | baseline | 844.08 | 114 | 3.33 | 113.55 | 320 | 244 | 49.20 | 0 |
| 1 | baseline_opp | 807.69 | 114 | 3.78 | 113.91 | 280 | 247.20 | 48.80 | 0 |
| 1 | baseline_zone | 844.08 | 114 | 3.33 | 113.55 | 320 | 244 | 49.20 | 0 |
| 1 | ilp | 534.79 | 114 | 0 | 99.39 | 40 | 254.20 | 27.20 | 0 |
| 1 | ilp_fixed_arcs | 836.10 | 114 | 0 | 108.90 | 320 | 244 | 49.20 | 0 |
| 1 | ilp_fixed_assign | 824.08 | 114 | 0 | 106.68 | 320 | 239 | 44.40 | 0 |
| 1 | baseline_rho0 | 844.08 | 114 | 3.33 | 113.55 | 320 | 244 | 49.20 | 0 |
| 1 | ilp_rho0 | 534.79 | 114 | 0 | 99.39 | 40 | 254.20 | 27.20 | 0 |
| 1.50 | baseline | 2201.87 | 114 | 3.24 | 118.83 | 1500 | 325 | 140.80 | 0 |
| 1.50 | baseline_opp | 2201.96 | 114 | 3.33 | 118.83 | 1500 | 325 | 140.80 | 0 |
| 1.50 | baseline_zone | 2201.87 | 114 | 3.24 | 118.83 | 1500 | 325 | 140.80 | 0 |
| 1.50 | ilp | 1391.28 | 114 | 0 | 118.68 | 740 | 347.40 | 71.20 | 0 |
| 1.50 | ilp_fixed_arcs | 2197.58 | 114 | 0 | 117.78 | 1500 | 325 | 140.80 | 0 |
| 1.50 | ilp_fixed_assign | 2174.25 | 114 | 0 | 115.65 | 1500 | 317 | 127.60 | 0 |
| 1.50 | baseline_rho0 | 2201.87 | 114 | 3.24 | 118.83 | 1500 | 325 | 140.80 | 0 |
| 1.50 | ilp_rho0 | 1391.41 | 114 | 0 | 119.61 | 740 | 347.40 | 70.40 | 0 |

## Service / operations metrics: mean over seeds

| demand_mult | method | served_share | mean_response_h | mean_lateness_h | max_lateness_h | n_late | bike_km | n_swaps | queue_wait_slots | mean_wait_before_swap | kwh_purchased | transfers_used | batteries_moved | end_full_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.750 | baseline | 0.973 | 0.681 | 0.020 | 0.150 | 3.600 | 90.810 | 4.400 | 0 | 0 | 1.156 | 0 | 0 | 8.400 |
| 0.750 | baseline_opp | 0.973 | 0.681 | 0.020 | 0.150 | 3.600 | 90.810 | 5.400 | 0 | 0 | 1.367 | 0 | 0 | 8 |
| 0.750 | baseline_zone | 0.973 | 0.681 | 0.020 | 0.150 | 3.600 | 90.810 | 4.400 | 0 | 0 | 1.156 | 0 | 0 | 8.400 |
| 0.750 | ilp | 0.991 | 0.678 | 0.021 | 0.150 | 3.800 | 70.860 | 2.200 | 1.600 | 0.800 | 0 | 0 | 0 | 9.800 |
| 0.750 | ilp_fixed_arcs | 0.973 | 0.681 | 0.020 | 0.150 | 3.600 | 86.610 | 0.800 | 0 | 0 | 0 | 0 | 0 | 11.200 |
| 0.750 | ilp_fixed_assign | 0.973 | 0.681 | 0.020 | 0.150 | 3.600 | 86.010 | 1.200 | 0.200 | 0.200 | 0 | 0 | 0 | 10.800 |
| 0.750 | baseline_rho0 | 0.973 | 0.681 | 0.020 | 0.150 | 3.600 | 90.810 | 4.400 | 0 | 0 | 1.156 | 0 | 0 | 8.400 |
| 0.750 | ilp_rho0 | 0.991 | 0.679 | 0.020 | 0.150 | 3.600 | 70.860 | 2 | 0.200 | 0.100 | 0 | 0 | 0 | 10 |
| 1 | baseline | 0.893 | 0.756 | 0.076 | 0.367 | 10.600 | 113.550 | 5.800 | 0.600 | 0.140 | 1.667 | 0 | 0 | 7.200 |
| 1 | baseline_opp | 0.907 | 0.756 | 0.074 | 0.367 | 10.800 | 113.910 | 6.800 | 0.600 | 0.109 | 1.889 | 0 | 0 | 6.800 |
| 1 | baseline_zone | 0.893 | 0.756 | 0.076 | 0.367 | 10.600 | 113.550 | 5.800 | 0.600 | 0.140 | 1.667 | 0 | 0 | 7.200 |
| 1 | ilp | 0.987 | 0.716 | 0.038 | 0.300 | 7.200 | 99.390 | 3.800 | 2.600 | 1.370 | 0 | 0 | 0 | 8.200 |
| 1 | ilp_fixed_arcs | 0.893 | 0.756 | 0.076 | 0.367 | 10.600 | 108.900 | 3 | 0.800 | 0.267 | 0 | 0 | 0 | 9 |
| 1 | ilp_fixed_assign | 0.893 | 0.741 | 0.068 | 0.383 | 9.400 | 106.680 | 3.400 | 2.200 | 0.603 | 0 | 0 | 0 | 8.600 |
| 1 | baseline_rho0 | 0.893 | 0.756 | 0.076 | 0.367 | 10.600 | 113.550 | 5.800 | 0.600 | 0.140 | 1.667 | 0 | 0 | 7.200 |
| 1 | ilp_rho0 | 0.987 | 0.716 | 0.038 | 0.317 | 7.200 | 99.390 | 3.600 | 2.200 | 0.510 | 0 | 0 | 0 | 8.400 |
| 1.500 | baseline | 0.667 | 0.902 | 0.195 | 0.533 | 20.200 | 118.830 | 5.400 | 0.200 | 0.033 | 1.622 | 0 | 0 | 7 |
| 1.500 | baseline_opp | 0.667 | 0.902 | 0.195 | 0.533 | 20.200 | 118.830 | 6.600 | 0.400 | 0.054 | 1.667 | 0 | 0 | 5.800 |
| 1.500 | baseline_zone | 0.667 | 0.902 | 0.195 | 0.533 | 20.200 | 118.830 | 5.400 | 0.200 | 0.033 | 1.622 | 0 | 0 | 7 |
| 1.500 | ilp | 0.836 | 0.769 | 0.078 | 0.500 | 15.200 | 118.680 | 3.400 | 1 | 0.400 | 0 | 0 | 0 | 8.600 |
| 1.500 | ilp_fixed_arcs | 0.667 | 0.902 | 0.195 | 0.533 | 20.200 | 117.780 | 3.400 | 0.200 | 0.067 | 0 | 0 | 0 | 8.600 |
| 1.500 | ilp_fixed_assign | 0.667 | 0.880 | 0.177 | 0.650 | 18.800 | 115.650 | 4 | 1.600 | 0.420 | 0 | 0 | 0 | 8 |
| 1.500 | baseline_rho0 | 0.667 | 0.902 | 0.195 | 0.533 | 20.200 | 118.830 | 5.400 | 0.200 | 0.033 | 1.622 | 0 | 0 | 7 |
| 1.500 | ilp_rho0 | 0.836 | 0.769 | 0.077 | 0.483 | 16 | 119.610 | 3.800 | 0.600 | 0.123 | 0 | 0 | 0 | 8.200 |

`queue_wait_slots` = wait slots at a swap node immediately before a swap (summed over swaps); `end_full_total` = full spares at H summed over sites ((18) requires >= rho * 12 = 6 at rho = 0.5).

## Gap decomposition (baseline - ILP) by component, rho = 0 headline pair

| demand_mult | total_gap | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 59.5 | 2.3 | 19.9 | 40 | -2.8 | 0 | 0 | 67.3 | -4.7 | 0 | 33.6 |
| x1 | 309.3 | 3.3 | 14.2 | 280 | -10.2 | 22 | 0 | 90.5 | -3.3 | 7.1 | 4.6 |
| x1.5 | 810.5 | 3.2 | -0.8 | 760 | -22.4 | 70.4 | 0 | 93.8 | -2.8 | 8.7 | -0.1 |
| all | 393.1 | 3.0 | 11.1 | 360 | -11.8 | 30.8 | 0 | 91.6 | -3.0 | 7.8 | 2.8 |

Same decomposition for the written model (rho = 0.5):

| demand_mult | total_gap | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 59.5 | 2.3 | 19.9 | 40 | -2.4 | -0.4 | 0 | 67.3 | -4.0 | -0.7 | 33.6 |
| x1 | 309.3 | 3.3 | 14.2 | 280 | -10.2 | 22 | 0 | 90.5 | -3.3 | 7.1 | 4.6 |
| x1.5 | 810.6 | 3.2 | 0.1 | 760 | -22.4 | 69.6 | 0 | 93.8 | -2.8 | 8.6 | 0.0 |
| all | 393.1 | 3.0 | 11.4 | 360 | -11.7 | 30.4 | 0 | 91.6 | -3.0 | 7.7 | 2.9 |

## Dispatch vs swap/charge decomposition (rho = 0.5, same instance, three ILPs)

`ilp_fixed_arcs` keeps the baseline's delivery arcs (who, when, from where) and frees only swaps, charging, transfers and repositioning; `ilp_fixed_assign` keeps the order-to-bike assignment and the unserved set but frees delivery timing; `ilp` frees everything. Gains are chained: baseline -> fixed arcs (swap/charge/transfer only) -> fixed assignment (re-timing) -> ILP (re-assignment incl. serving more orders).

| demand_mult | n | total_gain | swap_charge_transfer_only | swap_charge_transfer_share_pct | delivery_timing_resequencing | timing_share_pct | order_reassignment | reassignment_share_pct |
|---|---|---|---|---|---|---|---|---|
| x0.75 | 5 | 59.5 | 6.5 | 11.0 | 0.8 | 1.3 | 52.1 | 87.7 |
| x1 | 5 | 309.3 | 8.0 | 2.6 | 12.0 | 3.9 | 289.3 | 93.5 |
| x1.5 | 5 | 810.6 | 4.3 | 0.5 | 23.3 | 2.9 | 783.0 | 96.6 |
| all | 15 | 393.1 | 6.3 | 1.6 | 12.0 | 3.1 | 374.8 | 95.3 |

## Solver statistics (ILP runs)

| demand_mult | method | n_binaries | n_rows | runtime_mean_s | runtime_max_s | gap_max | n_optimal | n_runs | start_accepted |
|---|---|---|---|---|---|---|---|---|---|
| 0.75 | ilp | 662499 | 40651.20 | 15.71 | 20.09 | 0 | 5 | 5 | 5 |
| 0.75 | ilp_fixed_arcs | 662499 | 40651.20 | 1.26 | 2.60 | 0 | 5 | 5 | 5 |
| 0.75 | ilp_fixed_assign | 662499 | 40651.20 | 3.84 | 5.95 | 0 | 5 | 5 | 5 |
| 0.75 | ilp_rho0 | 662499 | 40651.20 | 15.15 | 17.00 | 0 | 5 | 5 | 5 |
| 1 | ilp | 795926.80 | 42360.60 | 20.31 | 28.86 | 0 | 5 | 5 | 2 |
| 1 | ilp_fixed_arcs | 795926.80 | 42360.60 | 0.68 | 1.29 | 0 | 5 | 5 | 2 |
| 1 | ilp_fixed_assign | 795926.80 | 42360.60 | 5.96 | 8.08 | 0 | 5 | 5 | 2 |
| 1 | ilp_rho0 | 795926.80 | 42360.60 | 21.63 | 33.34 | 0 | 5 | 5 | 3 |
| 1.50 | ilp | 1042309 | 43768 | 143.43 | 240.08 | 0.02 | 3 | 5 | 4 |
| 1.50 | ilp_fixed_arcs | 1042309 | 43768 | 0.74 | 1.16 | 0 | 5 | 5 | 4 |
| 1.50 | ilp_fixed_assign | 1042309 | 43768 | 9.04 | 10.73 | 0 | 5 | 5 | 4 |
| 1.50 | ilp_rho0 | 1042309 | 43768 | 150.72 | 242.38 | 0.02 | 3 | 5 | 5 |

## Baseline violations of the report-only families (default baseline, per demand level)

| demand_mult | viol_9_bikes | viol_17_shortfall | viol_18_runs | viol_18_mean_shortfall | stranded | queued_at_H | seeds |
|---|---|---|---|---|---|---|---|
| 0.75 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| 1 | 0 | 2 | 2 | 0.40 | 1 | 1 | 5 |
| 1.50 | 0 | 0 | 1 | 0.20 | 1 | 0 | 5 |

`viol_9_bikes` = bikes without a terminal certificate (9); `viol_17_shortfall` = summed local end-stock shortfall (17); `viol_18_runs` = runs ending below rho * sum B (18).

## Interpretation

The ILP lowers the cost by 28 % on average (rho = 0 headline; 28 % with rho = 0.5), within the 10-40 % band the plan expected at base demand, and the effect is stable across seeds (CI half-width 7.2 points). The gap is dominated by the P_i = 100 penalty: 92 % of the baseline-minus-ILP difference is unserved orders (shares by demand: x0.75 67 %, x1 91 %, x1.5 94 %); the baseline serves 89 % of the orders at base demand versus 99 % for the ILP, and 67 % vs 84 % at x1.5. Response is the next component (mean response per served order 0.76 h baseline vs 0.72 h ILP at base demand); its summed cost rises by 12 units on average because the ILP serves more orders, so the per-order response and the summed response cost move in opposite directions; travel (114 vs 99 km) and electricity (1.7 vs 0.0 kWh) change little, as the plan predicted. The chained decomposition attributes 2 % of the gain to swap/charge/transfer decisions alone (baseline deliveries kept), 3 % to re-timing the same assignment and 95 % to re-assigning orders (including serving the orders the baseline dropped): the gain sits in dispatch, which matches the plan's expectation. The baseline swaps 5.2 times per run (ILP 3.1) and accumulates 0.2 queue-wait slots per run at x1.5 (ILP 0.6); the ILP uses 0.0 transfer services per run at base demand and 0.0 at x1.5 (f_e = 5 per service), so site <-> site transfers are rarely worth their fee when every site charges. Battery logistics is barely exercised by this 2-hour family: the ILP purchases 0.0 kWh in total over all 15 runs and uses 0 transfer services, because 12 full spares for 10 bikes (q0 >= 0.4 L) cover every swap it needs within H = 24 and (18) costs it on average -0.0 units (ILP cost at rho = 0.5 minus rho = 0); the swap-queue congestion the plan expected at x1.5 does not appear either (M_j = 1, sigma_j = 1 and only 5 swaps per run), so charging, transfers and (18) only become decision-relevant with a longer horizon or fewer spares (E3/E4). Zone dispatch is byte-identical to global dispatch in every run: with 5 x 5-block zones a same-zone idle bike, when it exists, is also the nearest-by-tau candidate, so the zone preference never changes the choice. The opportunistic-swap variant changes the baseline cost by -1.2 % and zone dispatch by -0.0 % (positive = worse): both are second-order next to the coordination gap, and the fixed-dispatch ILPs (0.9 % with fixed arcs, 1.8 % with fixed assignment) show that re-optimising only the battery side of the baseline's plan recovers little of the gap. Caveat: the gap is measured in the toy unit system of E2 p.14 (P_i = 100, w_i = 12/h, v_i = 24/h, kappa = 1/km, pi = 2/kWh). With P_i this large relative to the operational terms, the comparison is essentially a comparison of service levels; a USD-calibrated P_i or the service-share form (33) would rebalance the picture, and the lexicographic switch would separate service level from cost explicitly.

## Anomalies

- The default baseline ends below rho * sum B in 3 of 15 runs (18) and below R_end_j = 1 at some site in 2 runs (17), so its MIP start is rejected by the fix-and-solve verification in 4 runs at rho = 0.5 and still in 2 runs at rho = 0 (the (17)-only cases); both families are reported, not enforced, by the policy (DECISIONS.md). The rho = 0 re-run is the headline because (18) is the network-wide target the deck's policy does not know about; (17) could be removed the same way (R_end = 0) if a fully feasible start is wanted.
- ILP runs not proven optimal: e2-K10-I45-seed2/ilp (TIME_LIMIT, gap 0.0198255608123331), e2-K10-I45-seed2-rho0/ilp_rho0 (TIME_LIMIT, gap 0.0212129977822775), e2-K10-I45-seed4/ilp (TIME_LIMIT, gap 0.0150838465850661), e2-K10-I45-seed4-rho0/ilp_rho0 (TIME_LIMIT, gap 0.0137531024162717)
- The ILP never charges (C_elec = 0, kWh = 0) and never uses a transfer in any run: the charging / transfer part of the model is feasible but non-binding on this family (12 spares, H = 24); the baseline's small C_elec comes from its ASAP charging rule, not from need.
- `baseline_zone` reproduces `baseline` exactly in every run (counter-intuitive but explained: the nearest-by-tau rule already prefers the same-zone bike); the zone map itself decodes correctly.

## Figures

- `cost_components.png`: stacked cost components per method, one panel per demand level (means over seeds).
- `improvement_vs_demand.png`: relative improvement vs demand multiplier with 95 % CI, one line per comparison.
- `gap_decomposition_rho0.png`: baseline-minus-ILP gap by component (rho = 0 headline pair).

Files: `results.csv` (one row per run), `improvement.csv`, `gap_decomposition_rho0.csv`, `gap_decomposition_rho05.csv`, `dispatch_decomposition.csv`, `instances/*.json`.
