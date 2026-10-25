# X4 -- value of the swap network vs home charging (final report)

Source: `outputs/r5_x4_network/records.jsonl` (180 records, 180 unique keys `(case, seed, infra, method)`; the last
record per key is kept, no duplicates were present). Script: `experiments/r5_x4_network.py`; log:
`outputs/r5_lanes/r5_x4_network.log`; wall time 59.1 min (`wall_time.json`). All tables below were recomputed from the
records by `figs/make_x4_final.py` (no solves) and agree with the script's own `RESULTS.md` to the printed precision.
Intervals are exact Student-t 95 % confidence intervals over seeds, `mean [lo, hi]` (all cells have n >= 5).

## Summary

On byte-identical demand (demand md5 equal for every row of a seed), every instance was solved on the swap network
(3 co-located swap + charge sites) and on the eBaaS-style home-charging counterfactual (one `HOMEn` per depot, a
"swap" is a 25-slot = 125 min recharge of the rider's own 0.5 kWh pack), each by the rule policies and by the
aggregated E2 ILP (Threads 3, Seed 0, 300 s). Under the like-for-like relaxed targets (rho = 0, R_end = 0) and the
conservative per-instance best rule, moving from (home, best rule) to (network, ILP) cuts the window cost by
**474.3 USD [390.3, 558.3] = 44.3 % [39.6, 49.1]** on `usd4h_ebaas` (n = 10) and by **822.2 USD [632.5, 1011.8] =
49.6 % [42.7, 56.6]** on `r5_stress4h` (n = 5). The Shapley split attributes **175.1 USD [104.5, 245.6] (37 %)** to the
network and **299.3 USD [247.0, 351.5] (63 %)** to coordination on `usd4h_ebaas`, and 249.2 USD [93.2, 405.1] (30 %)
vs 573.0 USD [464.3, 681.7] (70 %) on `r5_stress4h`. The value of coordination on the network,
(best rule - ILP) / best rule, is **28.4 % [21.0, 35.7]** (`usd4h_ebaas`) and **40.0 % [33.7, 46.4]** (`r5_stress4h`);
the value of the network under the ILP is **17.7 % [16.2, 19.2]** and **22.5 % [19.4, 25.5]** of the home cost, with
very tight intervals, whereas the value of the network under the best rule is 20.4 % [7.5, 33.3] and 15.3 %
[-1.4, 31.9] (not significant on `r5_stress4h`). In operational terms the network lets the ILP serve 1.43 vs 0.99
orders per rider-hour (`usd4h_ebaas`) and 1.75 vs 1.00 (`r5_stress4h`), at the price of 2.7x more empty
(repositioning) km per rider-hour (0.75 vs 0.28 and 0.80 vs 0.30).

## Coverage

| case | seeds | infra | policies r2 / r5_range / r5 | r5_transfer | ILP relaxed | ILP written |
|---|---|---|---|---|---|---|
| usd4h_ebaas | 0-9 | network | 10 / 10 / 10 POLICY | 10 NOT_APPLICABLE (no services) | 10 OPTIMAL (gap <= 0.0084 %, max 184 s) | 10 OPTIMAL (gap <= 0.0096 %, max 218 s) |
| usd4h_ebaas | 0-9 | home | 10 / 10 / 10 POLICY | 10 NOT_APPLICABLE | 10 OPTIMAL (max 8.6 s) | 10 OPTIMAL, implied by construction (no solve; (17)/(18) verified on the relaxed schedule) |
| r5_stress4h | 0-4 | network | 5 / 5 / 5 POLICY | 5 NOT_APPLICABLE | 5 OPTIMAL (gap <= 0.0017 %, max 294 s) | 2 OPTIMAL + 3 TIME_LIMIT at 300 s (gaps 0.30 %, 0.49 %, 0.79 %; seeds 1, 2, 3) |
| r5_stress4h | 0-4 | home | 5 / 5 / 5 POLICY | 5 NOT_APPLICABLE | 5 OPTIMAL (max 10.1 s) | 5 OPTIMAL, implied by construction |

Totals: 180 records = 120 policy rows (30 NOT_APPLICABLE), 45 solved ILPs (42 OPTIMAL, 3 TIME_LIMIT), 15 implied home
`ilp_written` rows. SKIPPED_BUDGET: 0. Errors: 0. Every evaluated row passes `evaluate.check` except 5 network `r2`
rows that report only the report-only family (9) (`ok_modulo_report_only = True`, accepted by protocol; see
Anomalies). All nine round-5 commands exited 0.

## Table 1 -- 2x2 cell costs (USD per 4 h window, objective (26), relaxed targets, best rule)

| case | n | Home, best rule | Home, ILP | Network, best rule | Network, ILP |
|---|---|---|---|---|---|
| usd4h_ebaas | 10 | 1054.9 [971.4, 1138.4] | 705.7 [683.4, 728.1] | 829.9 [720.8, 939.0] | 580.6 [562.2, 599.0] |
| r5_stress4h | 5 | 1646.4 [1483.5, 1809.3] | 1062.4 [1027.0, 1097.8] | 1386.1 [1172.5, 1599.8] | 824.2 [769.7, 878.8] |

## Table 2 -- 2x2 decomposition in USD (relaxed targets, objective (26))

VoN_P = H_P - N_P, VoN_ILP = H_ILP - N_ILP, VoC_home = H_P - H_ILP, VoC_network = N_P - N_ILP,
interaction = VoC_network - VoC_home = VoN_ILP - VoN_P, Shapley network = (VoN_P + VoN_ILP)/2, Shapley coordination =
(VoC_network + VoC_home)/2; the two Shapley shares add up to the total H_P - N_ILP. best_rule = per-instance minimum
over r2, r5_range, r5 (r5_transfer not applicable). The network cost includes the sunk setup cost C_setup (39.57 USD on
usd4h_ebaas, 38.33 USD on r5_stress4h, identical for every method); home has no setup cost, so all VoN figures are net
of it.

| case | policy P | VoN under P | VoN under ILP | VoC at home | VoC on network | interaction | Shapley network | Shapley coordination | total H_P - N_ILP |
|---|---|---|---|---|---|---|---|---|---|
| usd4h_ebaas | best_rule | 225.0 [83.6, 366.4] | 125.1 [113.3, 137.0] | 349.2 [265.7, 432.7] | 249.3 [156.2, 342.4] | -99.9 [-242.6, 42.8] | 175.1 [104.5, 245.6] | 299.3 [247.0, 351.5] | 474.3 [390.3, 558.3] |
| usd4h_ebaas | r2 | 215.4 [75.1, 355.8] | 125.1 [113.3, 137.0] | 349.2 [265.7, 432.7] | 258.9 [164.1, 353.8] | -90.3 [-231.7, 51.2] | 170.3 [100.2, 240.4] | 304.1 [249.4, 358.7] | 474.3 [390.3, 558.3] |
| usd4h_ebaas | r5 | 338.8 [155.1, 522.5] | 125.1 [113.3, 137.0] | 479.2 [361.8, 596.5] | 265.5 [157.3, 373.7] | -213.6 [-398.8, -28.5] | 232.0 [140.5, 323.5] | 372.4 [307.8, 436.9] | 604.3 [487.0, 721.7] |
| r5_stress4h | best_rule | 260.3 [-34.2, 554.7] | 238.1 [211.7, 264.5] | 584.0 [403.9, 764.2] | 561.9 [388.9, 734.9] | -22.1 [-300.6, 256.3] | 249.2 [93.2, 405.1] | 573.0 [464.3, 681.7] | 822.2 [632.5, 1011.8] |
| r5_stress4h | r2 | 187.2 [-148.1, 522.5] | 238.1 [211.7, 264.5] | 584.0 [403.9, 764.2] | 635.0 [425.9, 844.0] | 50.9 [-267.0, 368.8] | 212.7 [35.8, 389.5] | 609.5 [496.3, 722.7] | 822.2 [632.5, 1011.8] |
| r5_stress4h | r5 | 442.6 [176.2, 709.1] | 238.1 [211.7, 264.5] | 771.7 [641.3, 902.2] | 567.2 [404.4, 730.1] | -204.5 [-451.0, 42.0] | 340.4 [196.6, 484.1] | 669.5 [588.4, 750.6] | 1009.9 [860.7, 1159.1] |

## Table 3 -- the same decomposition in percent (per-seed ratios, then averaged)

| case | policy P | VoN under P (% of H_P) | VoN under ILP (% of H_ILP) | VoC at home (% of H_P) | VoC on network (% of N_P) | total (% of H_P) | seeds with VoN_P > 0 | seeds with interaction > 0 |
|---|---|---|---|---|---|---|---|---|
| usd4h_ebaas | best_rule | 20.4 [7.5, 33.3] | 17.7 [16.2, 19.2] | 32.4 [26.7, 38.1] | 28.4 [21.0, 35.7] | 44.3 [39.6, 49.1] | 9/10 | 4/10 |
| usd4h_ebaas | r2 | 19.5 [6.7, 32.3] | 17.7 [16.2, 19.2] | 32.4 [26.7, 38.1] | 29.1 [21.6, 36.6] | 44.3 [39.6, 49.1] | 9/10 | 4/10 |
| usd4h_ebaas | r5 | 27.1 [13.5, 40.6] | 17.7 [16.2, 19.2] | 39.4 [33.0, 45.8] | 29.3 [21.2, 37.4] | 50.1 [44.8, 55.5] | 9/10 | 4/10 |
| r5_stress4h | best_rule | 15.3 [-1.4, 31.9] | 22.5 [19.4, 25.5] | 35.1 [27.6, 42.6] | 40.0 [33.7, 46.4] | 49.6 [42.7, 56.6] | 5/5 | 3/5 |
| r5_stress4h | r2 | 10.7 [-8.9, 30.3] | 22.5 [19.4, 25.5] | 35.1 [27.6, 42.6] | 42.8 [35.5, 50.2] | 49.6 [42.7, 56.6] | 4/5 | 3/5 |
| r5_stress4h | r5 | 23.9 [10.6, 37.1] | 22.5 [19.4, 25.5] | 41.9 [37.1, 46.8] | 40.3 [34.5, 46.2] | 54.9 [49.8, 60.1] | 5/5 | 0/5 |

## Table 4 -- robustness: written targets (price of recovery) and end-state adjusted cost (best rule)

| case | metric | targets | Network ILP (USD) | VoN under ILP (USD) | VoN under ILP (%) | VoC on network (%) | Shapley coordination (USD) |
|---|---|---|---|---|---|---|---|
| usd4h_ebaas | total | relaxed | 580.6 [562.2, 599.0] | 125.1 [113.3, 137.0] | 17.7 [16.2, 19.2] | 28.4 [21.0, 35.7] | 299.3 [247.0, 351.5] |
| usd4h_ebaas | total | written | 581.0 [562.5, 599.5] | 124.7 [112.9, 136.5] | 17.7 [16.2, 19.1] | 28.3 [21.0, 35.7] | 299.1 [246.9, 351.3] |
| usd4h_ebaas | total_end_adjusted | relaxed | 582.0 [563.6, 600.4] | 124.5 [112.8, 136.3] | 17.6 [16.1, 19.1] | 28.3 [20.9, 35.6] | 299.0 [246.8, 351.3] |
| usd4h_ebaas | total_end_adjusted | written | 582.0 [563.6, 600.4] | 124.5 [112.8, 136.3] | 17.6 [16.1, 19.1] | 28.3 [20.9, 35.6] | 299.1 [246.8, 351.3] |
| r5_stress4h | total | relaxed | 824.2 [769.7, 878.8] | 238.1 [211.7, 264.5] | 22.5 [19.4, 25.5] | 40.0 [33.7, 46.4] | 573.0 [464.3, 681.7] |
| r5_stress4h | total | written | 827.5 [770.9, 884.0] | 234.9 [206.5, 263.3] | 22.2 [18.9, 25.4] | 39.8 [33.6, 46.0] | 571.4 [463.2, 679.5] |
| r5_stress4h | total_end_adjusted | relaxed | 826.1 [771.6, 880.6] | 236.6 [210.4, 262.8] | 22.3 [19.3, 25.3] | 40.0 [33.6, 46.3] | 572.7 [464.0, 681.5] |
| r5_stress4h | total_end_adjusted | written | 828.6 [772.2, 885.0] | 234.1 [205.8, 262.4] | 22.1 [18.8, 25.3] | 39.8 [33.6, 46.0] | 571.4 [463.3, 679.6] |

Price of recovery on the network ILP (written - relaxed): 0.40 USD [0.30, 0.51] = 0.07 % (`usd4h_ebaas`) and 3.22 USD
[0.20, 6.24] = 0.38 % (`r5_stress4h`, 3 of 5 written solves at TIME_LIMIT, so this is an upper bound). On the home
instance the written and relaxed optima coincide by construction. `C_end_adjust` moves no conclusion: every
decomposition quantity changes by less than 2 USD.

## Table 5 -- eBaaS-comparable operating metrics per cell (relaxed rows unless stated)

Empty km = reposition arcs (A3 `empty_km`; the ride to a home recharge is a reposition arc, the approach leg of a
delivery counts as delivery km). At home a "swap" is a 125 min recharge, hence the station time.

| case | infra | method | orders / rider-h | empty km / rider-h | bike km / rider-h | served share | orders given up | swaps (home: recharges) / rider-h | station time per swap (min) | outage rate | C_end_adjust (USD) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h_ebaas | home | best_rule | 0.54 [0.51, 0.58] | 0.25 [0.19, 0.31] | 1.87 [1.69, 2.05] | 0.361 [0.338, 0.384] | 23.0 [22.2, 23.8] | 0.16 [0.12, 0.19] | 135.3 [127.0, 143.6] | 0.37 [0.22, 0.51] | 0.84 [0.75, 0.93] |
| usd4h_ebaas | home | r2 | 0.54 [0.51, 0.58] | 0.25 [0.19, 0.31] | 1.87 [1.69, 2.05] | 0.361 [0.338, 0.384] | 23.0 [22.2, 23.8] | 0.16 [0.12, 0.19] | 135.3 [127.0, 143.6] | 0.37 [0.22, 0.51] | 0.84 [0.75, 0.93] |
| usd4h_ebaas | home | r5 | 0.57 [0.50, 0.65] | 0.24 [0.19, 0.29] | 1.95 [1.68, 2.22] | 0.383 [0.331, 0.435] | 22.2 [20.3, 24.1] | 0.21 [0.18, 0.24] | 133.3 [127.0, 139.7] | 0.15 [0.05, 0.25] | 0.86 [0.82, 0.90] |
| usd4h_ebaas | home | ilp_relaxed | 0.99 [0.93, 1.05] | 0.28 [0.20, 0.36] | 2.70 [2.50, 2.90] | 0.658 [0.617, 0.699] | 12.3 [10.8, 13.8] | 0.16 [0.13, 0.19] | 125.3 [124.8, 125.7] | 0.43 [0.28, 0.58] | 0.81 [0.75, 0.87] |
| usd4h_ebaas | home | ilp_written | 0.99 [0.93, 1.05] | 0.28 [0.20, 0.36] | 2.70 [2.50, 2.90] | 0.658 [0.617, 0.699] | 12.3 [10.8, 13.8] | 0.16 [0.13, 0.19] | 125.3 [124.8, 125.7] | 0.43 [0.28, 0.58] | 0.81 [0.75, 0.87] |
| usd4h_ebaas | network | best_rule | 1.38 [1.32, 1.43] | 0.46 [0.36, 0.56] | 5.12 [4.72, 5.51] | 0.919 [0.883, 0.956] | 2.9 [1.6, 4.2] | 0.38 [0.34, 0.42] | 5.7 [5.1, 6.3] | 0.13 [0.02, 0.24] | 0.99 [0.87, 1.11] |
| usd4h_ebaas | network | r2 | 1.39 [1.34, 1.44] | 0.40 [0.27, 0.53] | 5.07 [4.65, 5.50] | 0.928 [0.896, 0.959] | 2.6 [1.5, 3.7] | 0.35 [0.30, 0.39] | 5.9 [5.0, 6.7] | 0.15 [0.05, 0.25] | 0.94 [0.80, 1.08] |
| usd4h_ebaas | network | r5 | 1.37 [1.31, 1.43] | 0.54 [0.41, 0.67] | 5.15 [4.74, 5.56] | 0.911 [0.870, 0.952] | 3.2 [1.7, 4.7] | 0.42 [0.38, 0.46] | 5.3 [4.8, 5.9] | 0.02 [-0.02, 0.05] | 0.99 [0.88, 1.09] |
| usd4h_ebaas | network | ilp_relaxed | 1.43 [1.39, 1.47] | 0.75 [0.62, 0.87] | 4.71 [4.53, 4.90] | 0.953 [0.926, 0.979] | 1.7 [0.7, 2.7] | 0.35 [0.31, 0.39] | 8.3 [6.6, 9.9] | 0.35 [0.21, 0.49] | 1.46 [1.39, 1.53] |
| usd4h_ebaas | network | ilp_written | 1.43 [1.39, 1.47] | 0.75 [0.63, 0.88] | 4.72 [4.54, 4.91] | 0.953 [0.926, 0.979] | 1.7 [0.7, 2.7] | 0.30 [0.26, 0.35] | 8.8 [6.4, 11.2] | 0.43 [0.27, 0.59] | 1.02 [0.97, 1.07] |
| r5_stress4h | home | best_rule | 0.77 [0.60, 0.94] | 0.24 [0.12, 0.36] | 2.60 [2.23, 2.98] | 0.383 [0.298, 0.468] | 29.6 [25.5, 33.7] | 0.25 [0.25, 0.25] | 125.5 [124.6, 126.4] | 0.00 [0.00, 0.00] | 0.45 [0.43, 0.46] |
| r5_stress4h | home | r2 | 0.77 [0.60, 0.94] | 0.24 [0.12, 0.36] | 2.60 [2.23, 2.98] | 0.383 [0.298, 0.468] | 29.6 [25.5, 33.7] | 0.25 [0.25, 0.25] | 125.5 [124.6, 126.4] | 0.00 [0.00, 0.00] | 0.45 [0.43, 0.46] |
| r5_stress4h | home | r5 | 0.80 [0.68, 0.92] | 0.24 [0.15, 0.34] | 2.78 [2.45, 3.11] | 0.400 [0.338, 0.462] | 28.8 [25.8, 31.8] | 0.25 [0.25, 0.25] | 128.8 [125.9, 131.8] | 0.00 [0.00, 0.00] | 0.41 [0.40, 0.43] |
| r5_stress4h | home | ilp_relaxed | 1.00 [0.90, 1.10] | 0.29 [0.20, 0.39] | 2.63 [2.27, 2.98] | 0.500 [0.452, 0.548] | 24.0 [21.7, 26.3] | 0.18 [0.14, 0.23] | 125.3 [124.4, 126.3] | 0.33 [0.08, 0.59] | 0.34 [0.30, 0.38] |
| r5_stress4h | home | ilp_written | 1.00 [0.90, 1.10] | 0.29 [0.20, 0.39] | 2.63 [2.27, 2.98] | 0.500 [0.452, 0.548] | 24.0 [21.7, 26.3] | 0.18 [0.14, 0.23] | 125.3 [124.4, 126.3] | 0.33 [0.08, 0.59] | 0.34 [0.30, 0.38] |
| r5_stress4h | network | best_rule | 1.51 [1.30, 1.72] | 0.61 [0.44, 0.79] | 5.81 [5.46, 6.17] | 0.754 [0.648, 0.860] | 11.8 [6.7, 16.9] | 0.39 [0.33, 0.45] | 7.5 [4.2, 10.8] | 0.40 [0.29, 0.51] | 1.22 [1.10, 1.33] |
| r5_stress4h | network | r2 | 1.48 [1.22, 1.75] | 0.54 [0.36, 0.71] | 5.61 [5.14, 6.09] | 0.742 [0.608, 0.876] | 12.4 [6.0, 18.8] | 0.36 [0.31, 0.40] | 13.0 [6.1, 19.8] | 0.50 [0.35, 0.65] | 1.43 [1.31, 1.55] |
| r5_stress4h | network | r5 | 1.48 [1.33, 1.63] | 0.64 [0.49, 0.78] | 5.78 [5.39, 6.17] | 0.742 [0.667, 0.816] | 12.4 [8.8, 16.0] | 0.40 [0.35, 0.45] | 6.7 [3.4, 9.9] | 0.40 [0.29, 0.51] | 1.17 [1.02, 1.31] |
| r5_stress4h | network | ilp_relaxed | 1.75 [1.65, 1.85] | 0.79 [0.48, 1.11] | 5.59 [5.28, 5.89] | 0.875 [0.823, 0.927] | 6.0 [3.5, 8.5] | 0.40 [0.28, 0.52] | 8.5 [4.8, 12.2] | 0.77 [0.65, 0.88] | 1.84 [1.67, 2.00] |
| r5_stress4h | network | ilp_written | 1.74 [1.63, 1.85] | 0.71 [0.50, 0.91] | 5.57 [5.34, 5.80] | 0.871 [0.815, 0.927] | 6.2 [3.5, 8.9] | 0.36 [0.28, 0.44] | 5.4 [4.6, 6.2] | 0.70 [0.53, 0.87] | 1.14 [1.02, 1.27] |

Empty km per served order (derived, n = 10 / 5): usd4h_ebaas home best rule 0.46 [0.34, 0.58], home ILP 0.28
[0.20, 0.37], network best rule 0.33 [0.26, 0.41], network ILP 0.53 [0.44, 0.61]; r5_stress4h 0.34 [0.08, 0.61],
0.30 [0.20, 0.39], 0.41 [0.27, 0.56], 0.46 [0.27, 0.65].

## Figures

* `figs/fig_x4_2x2_decomposition.pdf|.png` (7.2 in): (a, b) 2x2 heat maps of the mean window cost with 95 % t-CI for
  each case (rows home / network, columns best rule / ILP); (c) the four effects VoN|best rule, VoN|ILP,
  VoC|home, VoC|network with 95 % t-CI error bars.
* `figs/fig_x4_ebaas_metrics.pdf|.png` (7.2 in): (a) orders served per rider-hour, (b) empty km per rider-hour, for the
  four cells and both cases, 95 % t-CI error bars.
* Data behind the figures: `figs/x4_decomposition_final.csv` (per seed), `figs/x4_summary_final.csv`,
  `figs/x4_ebaas_metrics_final.csv`; regenerate with `python3 figs/make_x4_final.py`.

## Anomalies and caveats

1. **r5 and r5_range are identical on every row** (30/30 instance-infra pairs, same total): no instance has transport
   services, so the r5 transfer layer is inactive; best_rule is effectively min(r2, r5). At home the best rule is r2
   on 15/15 instances; on the network it is r5 on 4/10 (`usd4h_ebaas`) and 4/5 (`r5_stress4h`).
2. **Five network r2 rows violate the report-only family (9)** (no admissible terminal certificate: usd4h_ebaas seed 9,
   r5_stress4h seeds 0, 1, 2, 4). They are kept, as in rounds 3-4, because (9) is in `BASELINE_REPORT_ONLY`. On
   r5_stress4h seeds 1, 2, 4 the best rule is r5 (unflagged), so only two best-rule network cells use a (9)-flagged
   schedule: usd4h_ebaas seed 9 (r2 820.7 vs r5 821.0 USD) and r5_stress4h seed 0 (r2 1134.2 vs r5 1160.9 USD).
3. **The value of the network under the rule is not robust in sign.** On `usd4h_ebaas` seed 8 the rule is cheaper at
   home (935.8 USD) than on the network (1115.7 USD): on the network it serves 34 orders but accrues 312 USD of
   lateness, at home it gives up 24 orders at the flat drop penalty. The objective prices a late order above a dropped
   one in these cases (brief issue 5), so the USD value of the network under the rule is partly a penalty-calibration
   artefact; VoN_best is not significant on `r5_stress4h` (15.3 % [-1.4, 31.9]).
4. **Home electricity is not priced in (26)** (`C_elec = 0` on every home row; 0.5 kWh per recharge, under 1 USD per
   window); `total_end_adjusted` prices the depleted packs left at home and changes nothing material.
5. **The ILP uses more empty km than the rule** on the network (0.75 vs 0.46 km per rider-hour on `usd4h_ebaas`, 16 %
   vs 9 % of bike km): the optimiser repositions riders towards future pick-ups, so "empty km" is not a cost the ILP
   minimises on its own and is not directly comparable with eBaaS's "invalid km" (which counts the ride home to
   charge). Under home charging empty km per rider-hour is low because riders are idle 125 min per recharge.
6. **The ILP accepts more outages than the rule at home** (outage rate 0.43 vs 0.37 on `usd4h_ebaas`; 0.33 vs 0.00 on
   `r5_stress4h`) and refuses orders for energy (7.5 per window on `usd4h_ebaas`): it deliberately lets a pack run
   down and drops the tail orders instead of a 125 min recharge.
7. **`r5_stress4h` written network solves**: 3/5 TIME_LIMIT (max gap 0.79 %); the relaxed headline cells are all
   OPTIMAL, the slowest at 294 s of 300 s.
8. **Comparison with round 3/4 (corrected)**: `usd4h_ebaas` is the round-3 `usd4h` x1 demand level (36 orders,
   seeds 0-9) with the eBaaS energy calibration (25 Wh/km, L 24). Its network cell is not new evidence: the value of
   coordination on the network (28.37 % [21.01, 35.72], n = 10) equals the X1 usd4h x1 stage S3 on the same instances
   (paired difference < 0.01 point). The like-for-like round-3 reference is therefore the x1 subset, 31.18 % +/- 9.05
   (n = 10), not the pooled 29.55 % over three demand levels. Paired X4 - round 3 = -2.82 +/- 3.20 points (95 % t,
   p = 0.08, lower on 7/10 seeds): not significant, but the point estimate is a 2.8-point reduction, not agreement.

## Interpretation

Replacing home charging by a swap network and replacing rule-based dispatch by the coordinating ILP together cut the
window cost by 44-50 %, and both Shapley shares are significantly positive on both families. Coordination is the larger
lever: its Shapley share is 299 USD (63 %) on `usd4h_ebaas` and 573 USD (70 %) on `r5_stress4h`, against 175 USD and
249 USD for the network. The two levers are substitutes rather than complements: the ILP already recovers much of
what the network offers (VoN under the ILP 125 USD vs 225 USD under the best rule on `usd4h_ebaas`), so the
interaction is negative on average (-100 USD on `usd4h_ebaas`, -22 USD on `r5_stress4h`), although its interval
includes zero for the best rule and it is significant only against the weaker r5 rule on `usd4h_ebaas` (-214 USD
[-399, -29]). The value of the network is most precisely
measured under the ILP (17.7 % [16.2, 19.2] and 22.5 % [19.4, 25.5] of the home cost), because the optimiser removes
the rule's erratic dispatch, which makes this the recommended headline for "value of the network". Under the rule
the network's value is noisy and can even be negative (seed 8), mainly because a rule that serves more orders late
can cost more than one that drops them. Operationally the network turns roughly one served order per rider-hour into
1.43-1.75, raising the served share from 0.66 to 0.95 (`usd4h_ebaas`) and from 0.50 to 0.88 (`r5_stress4h`) under the
ILP, because riders no longer lose 125 min per recharge. This gain comes with more, not fewer, empty km per
rider-hour (0.75 vs 0.28), so an eBaaS-style "less unproductive riding" claim is not supported by this model; the
gain is in time, not distance. The value of coordination on the network (28.4 % and 40.0 %) reproduces the X1 headline cell
for usd4h x1; against the matched round-3 x1 instances (31.2 %) it is 2.8 +/- 3.2 points lower, a reduction that is
not significant at n = 10, so the eBaaS calibration does not change the sign or rough size of the coordination
value but should not be described as leaving it unchanged. The written end targets
cost at most 0.4 % on top of the relaxed optimum, so the price of recovery is negligible here. Both families have
only 6 bikes and no transport services, so the result says nothing yet about larger fleets or the shuttle layer.

## Appendix -- per-instance table (objective (26), USD; relaxed unless stated)

| case | seed | H r2 | H r5 | H ILP | N r2 | N r5 | N ILP relaxed | N ILP written | N written status (gap) | best rule H / N | VoN_ILP | VoC_N % (best) | interaction (best) | served share H ILP / N ILP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h_ebaas | 0 | 1093.8 | 1320.5 | 673.8 | 613.1 | 612.3 | 532.6 | 532.8 | OPTIMAL (0.00 %) | r2 / r5 | 141.2 | 13.0 | -340.3 | 0.722 / 1.000 |
| usd4h_ebaas | 1 | 944.5 | 944.5 | 715.2 | 830.0 | 843.8 | 582.7 | 582.9 | OPTIMAL (0.00 %) | r2 / r2 | 132.6 | 29.8 | 18.0 | 0.639 / 0.944 |
| usd4h_ebaas | 2 | 1167.0 | 1364.7 | 674.8 | 745.5 | 729.2 | 582.9 | 583.2 | OPTIMAL (0.00 %) | r2 / r5 | 91.9 | 20.1 | -345.9 | 0.722 / 0.944 |
| usd4h_ebaas | 3 | 967.0 | 985.4 | 694.4 | 856.5 | 879.2 | 583.3 | 583.7 | OPTIMAL (0.00 %) | r2 / r2 | 111.1 | 31.9 | 0.6 | 0.667 / 0.944 |
| usd4h_ebaas | 4 | 865.4 | 1001.8 | 661.8 | 636.8 | 635.7 | 546.2 | 546.5 | OPTIMAL (0.00 %) | r2 / r5 | 115.6 | 14.1 | -114.0 | 0.722 / 1.000 |
| usd4h_ebaas | 5 | 1112.0 | 1265.9 | 713.9 | 944.2 | 866.6 | 588.8 | 589.2 | OPTIMAL (0.01 %) | r2 / r5 | 125.1 | 32.1 | -120.3 | 0.639 / 0.917 |
| usd4h_ebaas | 6 | 1103.5 | 1172.7 | 719.8 | 1003.9 | 1059.4 | 587.6 | 588.1 | OPTIMAL (0.00 %) | r2 / r2 | 132.2 | 41.5 | 32.6 | 0.611 / 0.944 |
| usd4h_ebaas | 7 | 1207.3 | 1328.9 | 747.8 | 828.7 | 837.5 | 597.4 | 597.8 | OPTIMAL (0.00 %) | r2 / r2 | 150.4 | 27.9 | -228.2 | 0.611 / 0.944 |
| usd4h_ebaas | 8 | 935.8 | 1129.4 | 756.7 | 1115.7 | 1176.5 | 625.9 | 626.4 | OPTIMAL (0.00 %) | r2 / r2 | 130.8 | 43.9 | 310.8 | 0.556 / 0.889 |
| usd4h_ebaas | 9 | 1153.0 | 1335.2 | 699.1 | 820.7 | 821.0 | 578.5 | 579.2 | OPTIMAL (0.00 %) | r2 / r2 | 120.5 | 29.5 | -211.8 | 0.694 / 1.000 |
| r5_stress4h | 0 | 1660.2 | 1907.8 | 1020.1 | 1134.2 | 1160.9 | 749.6 | 750.2 | OPTIMAL (0.00 %) | r2 / r2 | 270.5 | 33.9 | -255.4 | 0.542 / 0.938 |
| r5_stress4h | 1 | 1528.8 | 1775.0 | 1099.9 | 1594.0 | 1480.8 | 857.0 | 861.0 | TIME_LIMIT (0.30 %) | r2 / r5 | 242.9 | 42.1 | 194.8 | 0.438 / 0.854 |
| r5_stress4h | 2 | 1524.1 | 1724.7 | 1069.7 | 1487.0 | 1386.2 | 855.1 | 858.7 | TIME_LIMIT (0.49 %) | r2 / r5 | 214.6 | 38.3 | 76.7 | 0.500 / 0.833 |
| r5_stress4h | 3 | 1674.7 | 1841.8 | 1060.2 | 1666.2 | 1594.5 | 835.4 | 842.1 | TIME_LIMIT (0.79 %) | r2 / r5 | 224.8 | 47.6 | 144.6 | 0.500 / 0.854 |
| r5_stress4h | 4 | 1844.2 | 1921.3 | 1062.0 | 1414.6 | 1335.0 | 824.1 | 825.3 | OPTIMAL (0.01 %) | r2 / r5 | 237.8 | 38.3 | -271.3 | 0.521 / 0.896 |

## Digest corrections (2026-10-18)

Applied after the two-refuter verification pass; numbers recomputed from the records (no solves). Items marked "one verifier" are qualifiers added where only one verifier objected.

- C4 (comparison with round 3/4): both verifiers refuted 'consistent with the round-3/4 headline'. The X4 network cell equals X1 usd4h x1 stage S3 on the same 10 instances; the matched round-3 x1 reference is 31.18 +/- 9.05 % and the paired difference is -2.82 +/- 3.20 points (p = 0.08, 7/10 lower). Anomaly 8 and the Interpretation rewritten.
