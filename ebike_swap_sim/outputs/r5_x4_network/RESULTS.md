# X4 -- value of the swap network (A5, eBaaS home-charging counterfactual)

Network instance vs `generator.home_charging_counterfactual` (one swap-only home per depot, recharge of the rider's own battery at 0.24 kW, stock never binding), identical demand (demand md5 per seed: all identical). Gurobi Threads 3, Seed 0, TimeLimit 300 s, aggregated flow (O1). Headline = relaxed targets (rho 0, R_end 0); written targets = price of recovery. VoN = home - network (value of the network), VoC = policy - ILP (value of coordination); percentages: VoN in % of the home cost, VoC in % of the policy cost ((baseline - ILP) / baseline). best_rule = per instance min over r2, r5_range, r5_transfer (only with services), r5.

## total, relaxed targets (headline)
| case | policy | n | H_policy_mean | H_ilp_mean | N_policy_mean | N_ilp_mean | VoN_policy_mean | VoN_ilp_mean | VoC_network_mean | VoC_home_mean | VoC_network_pct_mean | VoN_ilp_pct_mean | interaction_mean | shapley_network_mean | shapley_coordination_mean | total_effect_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r5_stress4h | r2 | 5 | 1646.40 | 1062.36 | 1459.21 | 824.25 | 187.18 | 238.12 | 634.97 | 584.03 | 42.85 | 22.45 | 50.93 | 212.65 | 609.50 | 822.15 |
| r5_stress4h | best_rule | 5 | 1646.40 | 1062.36 | 1386.14 | 824.25 | 260.25 | 238.12 | 561.90 | 584.03 | 40.05 | 22.45 | -22.13 | 249.19 | 572.96 | 822.15 |
| r5_stress4h | r5 | 5 | 1834.11 | 1062.36 | 1391.48 | 824.25 | 442.63 | 238.12 | 567.24 | 771.74 | 40.35 | 22.45 | -204.51 | 340.37 | 669.49 | 1009.86 |
| usd4h_ebaas | r2 | 10 | 1054.93 | 705.74 | 839.50 | 580.59 | 215.43 | 125.15 | 258.91 | 349.19 | 29.13 | 17.71 | -90.28 | 170.29 | 304.05 | 474.34 |
| usd4h_ebaas | best_rule | 10 | 1054.93 | 705.74 | 829.92 | 580.59 | 225.01 | 125.15 | 249.32 | 349.19 | 28.37 | 17.71 | -99.87 | 175.08 | 299.26 | 474.34 |
| usd4h_ebaas | r5 | 10 | 1184.91 | 705.74 | 846.12 | 580.59 | 338.80 | 125.15 | 265.53 | 479.18 | 29.33 | 17.71 | -213.65 | 231.97 | 372.35 | 604.32 |

## total, written targets
| case | policy | n | H_policy_mean | H_ilp_mean | N_policy_mean | N_ilp_mean | VoN_policy_mean | VoN_ilp_mean | VoC_network_mean | VoC_home_mean | VoC_network_pct_mean | VoN_ilp_pct_mean | interaction_mean | shapley_network_mean | shapley_coordination_mean | total_effect_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r5_stress4h | r2 | 5 | 1646.40 | 1062.36 | 1459.21 | 827.46 | 187.18 | 234.90 | 631.75 | 584.03 | 42.64 | 22.15 | 47.72 | 211.04 | 607.89 | 818.93 |
| r5_stress4h | best_rule | 5 | 1646.40 | 1062.36 | 1386.14 | 827.46 | 260.25 | 234.90 | 558.68 | 584.03 | 39.83 | 22.15 | -25.35 | 247.58 | 571.36 | 818.93 |
| r5_stress4h | r5 | 5 | 1834.11 | 1062.36 | 1391.48 | 827.46 | 442.63 | 234.90 | 564.02 | 771.74 | 40.13 | 22.15 | -207.72 | 338.76 | 667.88 | 1006.65 |
| usd4h_ebaas | r2 | 10 | 1054.93 | 705.74 | 839.50 | 580.99 | 215.43 | 124.75 | 258.51 | 349.19 | 29.08 | 17.65 | -90.68 | 170.09 | 303.85 | 473.94 |
| usd4h_ebaas | best_rule | 10 | 1054.93 | 705.74 | 829.92 | 580.99 | 225.01 | 124.75 | 248.92 | 349.19 | 28.32 | 17.65 | -100.27 | 174.88 | 299.06 | 473.94 |
| usd4h_ebaas | r5 | 10 | 1184.91 | 705.74 | 846.12 | 580.99 | 338.80 | 124.75 | 265.13 | 479.18 | 29.29 | 17.65 | -214.05 | 231.77 | 372.15 | 603.92 |

## total_end_adjusted, relaxed targets
| case | policy | n | H_policy_mean | H_ilp_mean | N_policy_mean | N_ilp_mean | VoN_policy_mean | VoN_ilp_mean | VoC_network_mean | VoC_home_mean | VoC_network_pct_mean | VoN_ilp_pct_mean | interaction_mean | shapley_network_mean | shapley_coordination_mean | total_effect_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r5_stress4h | r2 | 5 | 1646.84 | 1062.70 | 1460.64 | 826.08 | 186.20 | 236.62 | 634.56 | 584.14 | 42.78 | 22.30 | 50.42 | 211.41 | 609.35 | 820.76 |
| r5_stress4h | best_rule | 5 | 1646.84 | 1062.70 | 1387.36 | 826.08 | 259.48 | 236.62 | 561.28 | 584.14 | 39.96 | 22.30 | -22.86 | 248.05 | 572.71 | 820.76 |
| r5_stress4h | r5 | 5 | 1834.52 | 1062.70 | 1392.65 | 826.08 | 441.87 | 236.62 | 566.57 | 771.82 | 40.27 | 22.30 | -205.25 | 339.24 | 669.19 | 1008.44 |
| usd4h_ebaas | r2 | 10 | 1055.77 | 706.55 | 840.44 | 582.05 | 215.33 | 124.50 | 258.39 | 349.22 | 29.03 | 17.60 | -90.82 | 169.91 | 303.81 | 473.72 |
| usd4h_ebaas | best_rule | 10 | 1055.77 | 706.55 | 830.91 | 582.05 | 224.86 | 124.50 | 248.86 | 349.22 | 28.28 | 17.60 | -100.36 | 174.68 | 299.04 | 473.72 |
| usd4h_ebaas | r5 | 10 | 1185.77 | 706.55 | 847.11 | 582.05 | 338.67 | 124.50 | 265.06 | 479.22 | 29.24 | 17.60 | -214.17 | 231.58 | 372.14 | 603.73 |

## total_end_adjusted, written targets
| case | policy | n | H_policy_mean | H_ilp_mean | N_policy_mean | N_ilp_mean | VoN_policy_mean | VoN_ilp_mean | VoC_network_mean | VoC_home_mean | VoC_network_pct_mean | VoN_ilp_pct_mean | interaction_mean | shapley_network_mean | shapley_coordination_mean | total_effect_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r5_stress4h | r2 | 5 | 1646.84 | 1062.70 | 1460.64 | 828.60 | 186.20 | 234.09 | 632.04 | 584.14 | 42.62 | 22.07 | 47.89 | 210.15 | 608.09 | 818.24 |
| r5_stress4h | best_rule | 5 | 1646.84 | 1062.70 | 1387.36 | 828.60 | 259.48 | 234.09 | 558.76 | 584.14 | 39.80 | 22.07 | -25.39 | 246.79 | 571.45 | 818.24 |
| r5_stress4h | r5 | 5 | 1834.52 | 1062.70 | 1392.65 | 828.60 | 441.87 | 234.09 | 564.04 | 771.82 | 40.10 | 22.07 | -207.78 | 337.98 | 667.93 | 1005.91 |
| usd4h_ebaas | r2 | 10 | 1055.77 | 706.55 | 840.44 | 582.01 | 215.33 | 124.54 | 258.43 | 349.22 | 29.04 | 17.60 | -90.79 | 169.93 | 303.82 | 473.76 |
| usd4h_ebaas | best_rule | 10 | 1055.77 | 706.55 | 830.91 | 582.01 | 224.86 | 124.54 | 248.89 | 349.22 | 28.28 | 17.60 | -100.32 | 174.70 | 299.06 | 473.76 |
| usd4h_ebaas | r5 | 10 | 1185.77 | 706.55 | 847.11 | 582.01 | 338.67 | 124.54 | 265.09 | 479.22 | 29.25 | 17.60 | -214.13 | 231.60 | 372.16 | 603.76 |

## 95 % t-CI half-widths (relaxed, total)
| case | policy | n | VoN_policy_ci95 | VoN_ilp_ci95 | VoC_network_ci95 | VoC_home_ci95 | VoC_network_pct_ci95 | interaction_ci95 |
|---|---|---|---|---|---|---|---|---|
| r5_stress4h | r2 | 5 | 335.23 | 26.37 | 209.03 | 180.11 | 7.39 | 317.85 |
| r5_stress4h | best_rule | 5 | 294.42 | 26.37 | 173.01 | 180.11 | 6.37 | 278.39 |
| r5_stress4h | r5 | 5 | 266.43 | 26.37 | 162.81 | 130.45 | 5.84 | 246.49 |
| usd4h_ebaas | r2 | 10 | 140.34 | 11.80 | 94.84 | 83.48 | 7.48 | 141.43 |
| usd4h_ebaas | best_rule | 10 | 141.38 | 11.80 | 93.09 | 83.48 | 7.36 | 142.68 |
| usd4h_ebaas | r5 | 10 | 183.69 | 11.80 | 108.19 | 117.32 | 8.09 | 185.13 |

## eBaaS-comparable metrics (means over seeds)
| case | infra | method | total | total_end_adjusted | C_end_adjust | served_share | orders_given_up | orders_per_rider_hour | empty_km_per_rider_hour | bike_km_per_rider_hour | swaps_per_rider_hour | r5_empty_km_share | r5_outage_rate | r5_n_energy_refused_orders | r5_mean_station_time_min | r5_mean_detour_km_per_swap | mean_response_h | mean_lateness_h | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r5_stress4h | home | ilp_relaxed | 1062.364 | 1062.699 | 0.336 | 0.500 | 24 | 1 | 0.295 | 2.626 | 0.183 | 0.111 | 0.333 | 15.600 | 125.333 | 0.080 | 0.773 | 0.001 | 5 |
| r5_stress4h | home | ilp_written | 1062.364 | 1062.699 | 0.336 | 0.500 | 24 | 1 | 0.295 | 2.626 | 0.183 | 0.111 | 0.333 | 15.600 | 125.333 | 0.080 | 0.773 | 0.001 | 5 |
| r5_stress4h | home | r2 | 1646.395 | 1646.843 | 0.448 | 0.383 | 29.600 | 0.767 | 0.241 | 2.603 | 0.250 | 0.097 | 0 | 0 | 125.500 | 0.935 | 1.321 | 0.458 | 5 |
| r5_stress4h | home | r5 | 1834.106 | 1834.519 | 0.413 | 0.400 | 28.800 | 0.800 | 0.241 | 2.780 | 0.250 | 0.088 | 0 | 0 | 128.833 | 0.765 | 1.520 | 0.629 | 5 |
| r5_stress4h | home | r5_range | 1834.106 | 1834.519 | 0.413 | 0.400 | 28.800 | 0.800 | 0.241 | 2.780 | 0.250 | 0.088 | 0 | 0 | 128.833 | 0.765 | 1.520 | 0.629 | 5 |
| r5_stress4h | network | ilp_relaxed | 824.245 | 826.082 | 1.837 | 0.875 | 6 | 1.750 | 0.795 | 5.586 | 0.400 | 0.142 | 0.767 | 4.400 | 8.457 | 0.836 | 0.778 | 0.001 | 5 |
| r5_stress4h | network | ilp_written | 827.461 | 828.605 | 1.144 | 0.871 | 6.200 | 1.742 | 0.705 | 5.570 | 0.358 | 0.127 | 0.700 | 2.800 | 5.411 | 0.899 | 0.778 | 0.000 | 5 |
| r5_stress4h | network | r2 | 1459.211 | 1460.642 | 1.432 | 0.742 | 12.400 | 1.483 | 0.537 | 5.615 | 0.358 | 0.095 | 0.500 | 10.600 | 12.972 | 1.086 | 1.122 | 0.257 | 5 |
| r5_stress4h | network | r5 | 1391.480 | 1392.649 | 1.169 | 0.742 | 12.400 | 1.483 | 0.636 | 5.780 | 0.400 | 0.110 | 0.400 | 8.400 | 6.655 | 1.375 | 1.083 | 0.214 | 5 |
| r5_stress4h | network | r5_range | 1391.480 | 1392.649 | 1.169 | 0.742 | 12.400 | 1.483 | 0.636 | 5.780 | 0.400 | 0.110 | 0.400 | 8.400 | 6.655 | 1.375 | 1.083 | 0.214 | 5 |
| usd4h_ebaas | home | ilp_relaxed | 705.739 | 706.549 | 0.811 | 0.658 | 12.300 | 0.988 | 0.278 | 2.704 | 0.158 | 0.103 | 0.433 | 7.500 | 125.292 | 0.219 | 0.767 | 0.002 | 10 |
| usd4h_ebaas | home | ilp_written | 705.739 | 706.549 | 0.811 | 0.658 | 12.300 | 0.988 | 0.278 | 2.704 | 0.158 | 0.103 | 0.433 | 7.500 | 125.292 | 0.219 | 0.767 | 0.002 | 10 |
| usd4h_ebaas | home | r2 | 1054.928 | 1055.768 | 0.839 | 0.361 | 23 | 0.542 | 0.247 | 1.868 | 0.158 | 0.135 | 0.367 | 19.300 | 135.308 | 1.027 | 1.051 | 0.232 | 10 |
| usd4h_ebaas | home | r5 | 1184.914 | 1185.774 | 0.860 | 0.383 | 22.200 | 0.575 | 0.241 | 1.949 | 0.208 | 0.130 | 0.150 | 8.500 | 133.325 | 0.948 | 1.220 | 0.376 | 10 |
| usd4h_ebaas | home | r5_range | 1184.914 | 1185.774 | 0.860 | 0.383 | 22.200 | 0.575 | 0.241 | 1.949 | 0.208 | 0.130 | 0.150 | 8.500 | 133.325 | 0.948 | 1.220 | 0.376 | 10 |
| usd4h_ebaas | network | ilp_relaxed | 580.591 | 582.048 | 1.457 | 0.953 | 1.700 | 1.429 | 0.749 | 4.713 | 0.350 | 0.160 | 0.350 | 0.400 | 8.272 | 0.762 | 0.769 | 0.001 | 10 |
| usd4h_ebaas | network | ilp_written | 580.993 | 582.012 | 1.019 | 0.953 | 1.700 | 1.429 | 0.754 | 4.723 | 0.304 | 0.160 | 0.433 | 0.400 | 8.805 | 0.880 | 0.769 | 0.001 | 10 |
| usd4h_ebaas | network | r2 | 839.503 | 840.442 | 0.940 | 0.928 | 2.600 | 1.392 | 0.401 | 5.074 | 0.346 | 0.077 | 0.150 | 0.300 | 5.862 | 1.055 | 0.951 | 0.112 | 10 |
| usd4h_ebaas | network | r5 | 846.119 | 847.107 | 0.988 | 0.911 | 3.200 | 1.367 | 0.542 | 5.151 | 0.421 | 0.104 | 0.017 | 0 | 5.338 | 1.178 | 0.952 | 0.113 | 10 |
| usd4h_ebaas | network | r5_range | 846.119 | 847.107 | 0.988 | 0.911 | 3.200 | 1.367 | 0.542 | 5.151 | 0.421 | 0.104 | 0.017 | 0 | 5.338 | 1.178 | 0.952 | 0.113 | 10 |

Empty km = reposition arcs (A3 `empty_km`); the approach leg of a delivery arc counts as delivery km. At home a 'swap' is a recharge trip (sigma = 25 slots). `total_end_adjusted` adds the M1 end-state adjustment, which also prices the depleted batteries left at the homes.

## Solver statistics
| case | infra | method | n | optimal | time_limit | skipped | implied | gap_max | runtime_mean | runtime_max |
|---|---|---|---|---|---|---|---|---|---|---|
| r5_stress4h | home | ilp_relaxed | 5 | 5 | 0 | 0 | 0 | 0.000 | 7.674 | 10.069 |
| r5_stress4h | home | ilp_written | 5 | 5 | 0 | 0 | 5 | 0.000 | 0 | 0 |
| r5_stress4h | network | ilp_relaxed | 5 | 5 | 0 | 0 | 0 | 0.000 | 131.317 | 294.015 |
| r5_stress4h | network | ilp_written | 5 | 2 | 3 | 0 | 0 | 0.008 | 226.576 | 300.035 |
| usd4h_ebaas | home | ilp_relaxed | 10 | 10 | 0 | 0 | 0 | 0 | 5.669 | 8.572 |
| usd4h_ebaas | home | ilp_written | 10 | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| usd4h_ebaas | network | ilp_relaxed | 10 | 10 | 0 | 0 | 0 | 0.000 | 54.802 | 183.618 |
| usd4h_ebaas | network | ilp_written | 10 | 10 | 0 | 0 | 0 | 0.000 | 71.891 | 217.762 |

Figure: `x4_decomposition.png`
