# X2 (round 5): battery transfers and charging-hub separation, final report

Source: `records.jsonl` in this directory (390 records, last record per key kept; no duplicate keys found). Tables and figures were regenerated from the records by `figs/make_x2_final.py`. No ILP was re-solved. Instance family `usd4h` (6 bikes, 36 orders, H 48 five-minute slots, `usd_sunk` costs) with the eBaaS energy calibration (A1). Three layouts (co-located: 3 swap+charge sites, B 3 and C 2 each; separated, 1 hub: 3 swap-only sites with B 3 and one charge-only hub with 6 chargers; separated, 2 hubs: two hubs with 3 chargers each). Seeds 0-4. Demand md5 is identical across every layout, timetable and target setting of a seed. Timetables: `r3` = round-3 shuttles (hub-site or site-site, every 30 min, fare f = 20 USD per shuttle); `cyclic` = M8 tours (one chained tour per 60 min, f split over the legs: 6.67 / 5.00 / 4.00 USD per leg for 3 / 4 / 5 facilities). ILP: aggregated flow (O1), Gurobi Threads 3, Seed 0, TimeLimit 300 s. ILP `none` (h = z = 0) does not depend on the timetable. It was solved once on the r3 instance (`timetable = any`) and is compared with the r3 rules. Gap = 100 (baseline - ILP) / baseline. `best_rule` = per-instance minimum over r2, r5_range, r5_transfer and r5 (the conservative baseline). Targets: **relaxed** (rho 0, R_end 0; the like-for-like headline) and **written** (rho 0.5; R_end_j 1 at co-located sites and 0 at swap-only sites and hubs, M1; the price of recovery). Each entry is a mean with an exact-t 95 % CI in brackets (n 5 per cell unless stated otherwise). The CI is mean +/- t(0.975, n-1) s / sqrt(n).

## Summary

**Relaxed targets (headline).** Transfers are worthless to the coordinator. In all 45 relaxed solves the ILP uses 0 transfers, buys 0 kWh, and the transfers-free optimum equals the no-transfer optimum. The pooled gap to the best rule is therefore 20.98 % [16.59, 25.36] (n 15) for every timetable and switch. Separating the hubs costs 29.00 USD [28.53, 29.48] (1 hub) and 58.04 USD [57.39, 58.70] (2 hubs) per window. That is the hub fixed charge (29.19 / 58.38 USD) less 0.19 / 0.34 USD of operating cost.

**Written targets (price of recovery).** Transfers have value only in the separated layouts:
- With cyclic tours they save 16.40 USD [8.46, 24.35] (1 hub) and 17.39 USD [10.69, 24.09] (2 hubs). That is 2.6-2.7 % of ILP(none), positive on 5/5 seeds, and each optimum uses one leg that carries two batteries.
- With r3 shuttles the incumbents save only 3.56 / 3.09 USD, and 10 of the 15 runs stopped at TIME_LIMIT. Even so, the cyclic optimum lies below the r3 lower bound on 10/10 separated instances, so cyclic tours are provably cheaper here.
- The cyclic advantage comes mostly from the fare split: one leg costs 5 or 4 USD, against 20 USD for an r3 shuttle.
- Transfers cut the ILP price of recovery in separated layouts from about 24 USD (no transfers) to 7.87 / 6.75 USD.

**Transfer rules in the policies.** No transfer rule helps a policy.
- COST_AWARE (M3) roughly halves the REORDER_POINT loss on r3 shuttles (for example, co-located relaxed: 50.60 vs 122.52 USD above r2).
- On cyclic tours COST_AWARE is worse than REORDER_POINT in the separated layouts (31.88 vs 10.48 and 24.86 vs 10.56 USD).
- COST_AWARE is no more expensive than r2 in only 2 of 60 instance-cells.

## Coverage

All 390 planned rows exist (90 ILP + 300 policy runs). 0 SKIPPED_BUDGET, 0 solver errors, 0 ILP rows failing `check`. Wall time 138.5 min (`wall_time.json`). The demand md5 is unique per seed (1 distinct value for each of seeds 0-4).

| targets | ILP transfers | timetable | n | OPTIMAL | TIME_LIMIT | TIME_LIMIT MIP gaps (%) | runtime mean / max (s) |
|---|---|---|---|---|---|---|---|
| relaxed | free | cyclic | 15 | 15 | 0 | - | 33 / 81 |
| relaxed | free | r3 | 15 | 15 | 0 | - | 34 / 60 |
| relaxed | none | any | 15 | 15 | 0 | - | 34 / 79 |
| written | free | cyclic | 15 | 14 | 1 | 0.47 | 146 / 300 |
| written | free | r3 | 15 | 5 | 10 | 2.28, 2.18, 2.24, 2.16, 1.87, 2.12, 2.10, 2.17, 0.92, 1.02 | 213 / 300 |
| written | none | any | 15 | 15 | 0 | - | 53 / 114 |

ILP totals: 79 OPTIMAL and 11 TIME_LIMIT. All TIME_LIMIT runs are written-target, transfers-free cells in separated layouts (10 on r3, 1 on cyclic: separated, 2 hubs, seed 1). Their largest MIP gap is 2.28 %. Twelve MIP starts were rejected (all `none` written cells with an unverified r2 or r5_range start), and all twelve of those solves still reached OPTIMAL. Policy schedules: all 150 relaxed rows pass `check`. Under written targets, 147 of 150 rows fail `check` only on the reported (not enforced) end-state constraints: (18) in 147 rows and (17) in 33 of them. All 147 have `check_ok_modulo_report_only = True`.

## Table 1. Headline (relaxed targets): ILP vs best rule

| layout | ILP transfers, timetable | ILP total (USD) | best_rule total (USD) | gap vs best_rule (%) | gap end-adjusted (%) | ILP C_end_adjust (USD) |
|---|---|---|---|---|---|---|
| Co-located | none (any) | 565.54 [535.31, 595.78] | 732.73 [595.72, 869.74] | 21.77 [10.92, 32.62] | 21.67 [10.80, 32.54] | 1.40 |
| Co-located | free, r3 | 565.54 [535.31, 595.78] | 732.73 [595.72, 869.74] | 21.77 [10.92, 32.62] | 21.67 [10.80, 32.54] | 1.40 |
| Co-located | free, cyclic | 565.54 [535.31, 595.78] | 732.73 [595.72, 869.74] | 21.77 [10.92, 32.62] | 21.67 [10.80, 32.54] | 1.40 |
| Separated, 1 hub | none (any) | 594.54 [564.52, 624.57] | 761.52 [624.77, 898.28] | 20.94 [10.34, 31.55] | 20.91 [10.31, 31.51] | 1.44 |
| Separated, 1 hub | free, r3 | 594.54 [564.52, 624.57] | 761.52 [624.77, 898.28] | 20.94 [10.34, 31.55] | 20.91 [10.31, 31.51] | 1.44 |
| Separated, 1 hub | free, cyclic | 594.54 [564.52, 624.57] | 761.52 [624.77, 898.28] | 20.94 [10.34, 31.55] | 20.91 [10.31, 31.51] | 1.44 |
| Separated, 2 hubs | none (any) | 623.59 [593.65, 653.52] | 790.71 [653.96, 927.47] | 20.21 [9.90, 30.53] | 20.19 [9.88, 30.50] | 1.40 |
| Separated, 2 hubs | free, r3 | 623.59 [593.65, 653.52] | 790.71 [653.96, 927.47] | 20.21 [9.90, 30.53] | 20.19 [9.88, 30.50] | 1.40 |
| Separated, 2 hubs | free, cyclic | 623.59 [593.65, 653.52] | 790.71 [653.96, 927.47] | 20.21 [9.90, 30.53] | 20.19 [9.88, 30.50] | 1.40 |

## Table 2. Written targets (price of recovery setting): ILP vs best rule

| layout | ILP transfers, timetable | ILP total (USD) | best_rule total (USD) | gap vs best_rule (%) | gap end-adjusted (%) | ILP C_end_adjust (USD) |
|---|---|---|---|---|---|---|
| Co-located | none (any) | 565.84 [535.57, 596.11] | 732.73 [595.72, 869.74] | 21.73 [10.87, 32.58] | 21.67 [10.82, 32.53] | 1.07 |
| Co-located | free, r3 | 565.84 [535.57, 596.11] | 732.73 [595.72, 869.74] | 21.73 [10.87, 32.58] | 21.67 [10.82, 32.53] | 1.07 |
| Co-located | free, cyclic | 565.84 [535.57, 596.11] | 732.73 [595.72, 869.74] | 21.73 [10.87, 32.58] | 21.67 [10.82, 32.53] | 1.07 |
| Separated, 1 hub | none (any) | 618.82 [586.01, 651.63] | 761.52 [624.77, 898.28] | 17.75 [7.11, 28.39] | 17.76 [7.13, 28.38] | 1.18 |
| Separated, 1 hub | free, r3 | 615.26 [583.51, 647.01] | 761.52 [624.77, 898.28] | 18.20 [7.39, 29.01] | 18.22 [7.42, 29.01] | 1.13 |
| Separated, 1 hub | free, cyclic | 602.42 [572.35, 632.49] | 761.52 [624.77, 898.28] | 19.89 [9.12, 30.67] | 19.91 [9.16, 30.67] | 1.07 |
| Separated, 2 hubs | none (any) | 647.73 [615.20, 680.27] | 790.71 [653.96, 927.47] | 17.15 [6.76, 27.55] | 17.16 [6.78, 27.54] | 1.19 |
| Separated, 2 hubs | free, r3 | 644.64 [612.57, 676.71] | 790.71 [653.96, 927.47] | 17.54 [7.06, 28.01] | 17.55 [7.09, 28.01] | 1.13 |
| Separated, 2 hubs | free, cyclic | 630.34 [599.87, 660.81] | 790.71 [653.96, 927.47] | 19.35 [8.98, 29.73] | 19.37 [9.01, 29.73] | 1.08 |

## Table 3. Pooled gaps over layouts (n 15)

| targets | ILP | gap vs best_rule (%), n 15 | end-adjusted (%) | gap vs r2 (%) |
|---|---|---|---|---|
| relaxed | none (any) | 20.98 [16.59, 25.36] | 20.92 [16.53, 25.31] | 21.35 [17.01, 25.69] |
| relaxed | free, r3 | 20.98 [16.59, 25.36] | 20.92 [16.53, 25.31] | 21.35 [17.01, 25.69] |
| relaxed | free, cyclic | 20.98 [16.59, 25.36] | 20.92 [16.53, 25.31] | 21.35 [17.01, 25.69] |
| written | none (any) | 18.88 [14.34, 23.42] | 18.86 [14.33, 23.40] | 19.54 [15.04, 24.05] |
| written | free, r3 | 19.16 [14.61, 23.70] | 19.15 [14.61, 23.69] | 19.54 [15.04, 24.05] |
| written | free, cyclic | 20.33 [15.88, 24.77] | 20.32 [15.88, 24.76] | 20.71 [16.31, 25.10] |

Round-3/4 reference: usd4h 29.55 % +/- 5.61 (n 30). The X2 headline of 20.98 % [16.59, 25.36] is lower. The comparison is not like-for-like: X2 uses the eBaaS energy calibration, the E3u layouts and a stricter best_rule that includes r5_range.

## Table 4. Value of transfers to the ILP: ILP(none) - ILP(free), paired by seed (USD)

The 'provable upper limit' uses the Gurobi bound of the transfers-free run, so for TIME_LIMIT runs the true value lies between the two columns.

| targets | layout | timetable | ILP(none) - ILP(free) (USD) | provable upper limit none - bound(free) (USD) | services / batteries moved | seeds with value > 0 | share of ILP(none) (%) |
|---|---|---|---|---|---|---|---|
| relaxed | Co-located | r3 | 0.00 [0.00, 0.00] | 0.01 [-0.01, 0.03] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| relaxed | Co-located | cyclic | 0.00 [0.00, 0.00] | 0.01 [-0.02, 0.04] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| relaxed | Separated, 1 hub | r3 | 0.00 [0.00, 0.00] | 0.02 [-0.01, 0.05] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| relaxed | Separated, 1 hub | cyclic | 0.00 [0.00, 0.00] | 0.02 [-0.01, 0.05] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| relaxed | Separated, 2 hubs | r3 | 0.00 [0.00, 0.00] | 0.01 [-0.01, 0.04] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| relaxed | Separated, 2 hubs | cyclic | 0.00 [0.00, 0.00] | 0.02 [-0.01, 0.05] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| written | Co-located | r3 | 0.00 [0.00, 0.00] | 0.03 [-0.00, 0.05] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| written | Co-located | cyclic | 0.00 [0.00, 0.00] | 0.02 [-0.00, 0.04] | 0.0 / 0.0 | 0/5 | 0.00 [0.00, 0.00] |
| written | Separated, 1 hub | r3 | 3.56 [-0.70, 7.82] | 15.18 [7.15, 23.21] | 0.6 / 1.2 | 3/5 | 0.57 [-0.11, 1.25] |
| written | Separated, 1 hub | cyclic | 16.40 [8.46, 24.35] | 16.40 [8.46, 24.35] | 1.0 / 2.0 | 5/5 | 2.64 [1.38, 3.89] |
| written | Separated, 2 hubs | r3 | 3.09 [-0.60, 6.78] | 15.58 [8.48, 22.67] | 0.6 / 1.2 | 3/5 | 0.48 [-0.09, 1.04] |
| written | Separated, 2 hubs | cyclic | 17.39 [10.69, 24.09] | 18.01 [10.80, 25.21] | 1.0 / 2.0 | 5/5 | 2.68 [1.66, 3.69] |

## Table 5. Cyclic (M8) vs round-3 timetable (USD, paired by seed)

| targets | layout | ILP free: cyclic - r3 (USD) | seeds with cyclic optimum < r3 bound | ILP C_reb r3 / cyclic (USD) | r2_reorder: cyclic - r3 | r5_transfer: cyclic - r3 | best_rule: cyclic - r3 |
|---|---|---|---|---|---|---|---|
| relaxed | Co-located | 0.00 [0.00, 0.00] | 0/5 | 0.0 / 0.0 | -95.43 [-133.98, -56.88] | -30.66 [-49.49, -11.84] | 0.00 [0.00, 0.00] |
| relaxed | Separated, 1 hub | 0.00 [0.00, 0.00] | 0/5 | 0.0 / 0.0 | -105.73 [-147.51, -63.94] | -30.64 [-69.80, 8.52] | 0.00 [0.00, 0.00] |
| relaxed | Separated, 2 hubs | 0.00 [0.00, 0.00] | 0/5 | 0.0 / 0.0 | -105.40 [-151.56, -59.24] | -45.64 [-100.35, 9.07] | 0.00 [0.00, 0.00] |
| written | Co-located | 0.00 [0.00, 0.00] | 0/5 | 0.0 / 0.0 | -95.43 [-133.98, -56.88] | -43.91 [-70.37, -17.46] | 0.00 [0.00, 0.00] |
| written | Separated, 1 hub | -12.84 [-17.15, -8.53] | 5/5 | 13.2 / 7.0 | -105.73 [-147.51, -63.94] | -30.64 [-69.80, 8.52] | 0.00 [0.00, 0.00] |
| written | Separated, 2 hubs | -14.30 [-18.00, -10.61] | 5/5 | 13.2 / 6.0 | -105.40 [-151.56, -59.24] | -45.64 [-100.35, 9.07] | 0.00 [0.00, 0.00] |

## Table 6. Separation cost: separated - co-located, paired by seed (USD)

| targets | layout | fixed-cost difference (USD) | ILP none: sep - coloc | ILP free r3: sep - coloc | ILP free cyclic: sep - coloc | ILP free cyclic, operating part (excl. fixed) | best_rule (r3): sep - coloc |
|---|---|---|---|---|---|---|---|
| relaxed | Separated, 1 hub | 29.19 | 29.00 [28.53, 29.48] | 29.00 [28.53, 29.48] | 29.00 [28.53, 29.48] | -0.19 [-0.66, 0.29] | 28.79 [28.32, 29.26] |
| relaxed | Separated, 2 hubs | 58.38 | 58.04 [57.39, 58.70] | 58.04 [57.39, 58.70] | 58.04 [57.39, 58.70] | -0.34 [-0.99, 0.32] | 57.98 [57.51, 58.45] |
| written | Separated, 1 hub | 29.19 | 52.98 [45.53, 60.43] | 49.41 [45.69, 53.14] | 36.57 [35.88, 37.27] | 7.38 [6.69, 8.08] | 28.79 [28.32, 29.26] |
| written | Separated, 2 hubs | 58.38 | 81.89 [74.59, 89.19] | 78.80 [74.81, 82.79] | 64.50 [63.38, 65.62] | 6.12 [5.00, 7.24] | 57.98 [57.51, 58.45] |

## Table 7. Transfer rules in the policy: REORDER_POINT vs COST_AWARE (M3), loss relative to r2 (no transfers), USD

| targets | layout | timetable | REORDER_POINT loss: r2_reorder - r2 (USD) | COST_AWARE loss: r5_transfer - r2 (USD) | COST_AWARE - REORDER (USD) | COST_AWARE < REORDER (seeds) | COST_AWARE <= r2 (seeds) | services used REORDER / COST_AWARE |
|---|---|---|---|---|---|---|---|---|
| relaxed | Co-located | r3 | 122.52 [100.11, 144.93] | 50.60 [11.97, 89.23] | -71.92 [-122.81, -21.03] | 5/5 | 0/5 | 5.0 / 1.8 |
| relaxed | Co-located | cyclic | 27.09 [1.83, 52.35] | 19.94 [-5.42, 45.30] | -7.15 [-27.95, 13.64] | 3/5 | 0/5 | 2.8 / 1.4 |
| relaxed | Separated, 1 hub | r3 | 116.21 [65.91, 166.50] | 62.52 [51.49, 73.55] | -53.69 [-112.90, 5.52] | 4/5 | 0/5 | 5.4 / 2.8 |
| relaxed | Separated, 1 hub | cyclic | 10.48 [-0.29, 21.26] | 31.88 [-7.63, 71.40] | 21.40 [-21.63, 64.44] | 2/5 | 0/5 | 1.6 / 2.0 |
| relaxed | Separated, 2 hubs | r3 | 115.96 [65.56, 166.36] | 70.50 [49.60, 91.39] | -45.47 [-109.55, 18.62] | 3/5 | 0/5 | 5.4 / 3.2 |
| relaxed | Separated, 2 hubs | cyclic | 10.56 [2.60, 18.53] | 24.86 [-13.21, 62.92] | 14.29 [-22.12, 50.70] | 0/5 | 1/5 | 1.8 / 2.0 |
| written | Co-located | r3 | 122.52 [100.11, 144.93] | 76.35 [36.63, 116.07] | -46.17 [-100.93, 8.59] | 4/5 | 0/5 | 5.0 / 3.0 |
| written | Co-located | cyclic | 27.09 [1.83, 52.35] | 32.44 [9.98, 54.90] | 5.35 [-17.31, 28.02] | 2/5 | 0/5 | 2.8 / 2.4 |
| written | Separated, 1 hub | r3 | 116.21 [65.91, 166.50] | 62.52 [51.49, 73.55] | -53.69 [-112.90, 5.52] | 4/5 | 0/5 | 5.4 / 2.8 |
| written | Separated, 1 hub | cyclic | 10.48 [-0.29, 21.26] | 31.88 [-7.63, 71.40] | 21.40 [-21.63, 64.44] | 2/5 | 0/5 | 1.6 / 2.0 |
| written | Separated, 2 hubs | r3 | 115.96 [65.56, 166.36] | 70.50 [49.60, 91.39] | -45.47 [-109.55, 18.62] | 3/5 | 0/5 | 5.4 / 3.2 |
| written | Separated, 2 hubs | cyclic | 10.56 [2.60, 18.53] | 24.86 [-13.21, 62.92] | 14.29 [-22.12, 50.70] | 0/5 | 1/5 | 1.8 / 2.0 |

## Table 8. Policy totals (USD per 4-h window)

| targets | layout | timetable | r2 | r2_reorder | r5_range | r5_transfer | r5 | best_rule label (seeds) |
|---|---|---|---|---|---|---|---|---|
| relaxed | Co-located | r3 | 736.4 [599.8, 872.9] | 858.9 [729.3, 988.5] | 740.0 [591.2, 888.8] | 787.0 [673.1, 900.9] | 781.8 [640.9, 922.6] | r2 2, r5_range 3 |
| relaxed | Co-located | cyclic | 736.4 [599.8, 872.9] | 763.5 [634.8, 892.2] | 740.0 [591.2, 888.8] | 756.3 [627.3, 885.4] | 751.7 [618.5, 884.9] | r2 2, r5_range 3 |
| relaxed | Separated, 1 hub | r3 | 765.0 [628.5, 901.6] | 881.2 [727.0, 1035.5] | 769.0 [621.1, 917.0] | 827.5 [697.5, 957.5] | 832.6 [676.6, 988.7] | r2 3, r5_range 2 |
| relaxed | Separated, 1 hub | cyclic | 765.0 [628.5, 901.6] | 775.5 [640.6, 910.4] | 769.0 [621.1, 917.0] | 796.9 [670.0, 923.8] | 792.4 [651.1, 933.6] | r2 3, r5_range 2 |
| relaxed | Separated, 2 hubs | r3 | 794.2 [657.7, 930.8] | 910.2 [755.9, 1064.5] | 798.2 [650.2, 946.2] | 864.7 [739.0, 990.4] | 882.8 [718.9, 1046.7] | r2 3, r5_range 2 |
| relaxed | Separated, 2 hubs | cyclic | 794.2 [657.7, 930.8] | 804.8 [671.1, 938.4] | 798.2 [650.2, 946.2] | 819.1 [660.4, 977.7] | 808.6 [661.1, 956.0] | r2 3, r5_range 2 |
| written | Co-located | r3 | 736.4 [599.8, 872.9] | 858.9 [729.3, 988.5] | 740.0 [591.2, 888.8] | 812.7 [692.7, 932.8] | 804.8 [661.8, 947.8] | r2 2, r5_range 3 |
| written | Co-located | cyclic | 736.4 [599.8, 872.9] | 763.5 [634.8, 892.2] | 740.0 [591.2, 888.8] | 768.8 [650.1, 887.5] | 760.2 [627.0, 893.4] | r2 2, r5_range 3 |
| written | Separated, 1 hub | r3 | 765.0 [628.5, 901.6] | 881.2 [727.0, 1035.5] | 769.0 [621.1, 917.0] | 827.5 [697.5, 957.5] | 832.6 [676.6, 988.7] | r2 3, r5_range 2 |
| written | Separated, 1 hub | cyclic | 765.0 [628.5, 901.6] | 775.5 [640.6, 910.4] | 769.0 [621.1, 917.0] | 796.9 [670.0, 923.8] | 792.4 [651.1, 933.6] | r2 3, r5_range 2 |
| written | Separated, 2 hubs | r3 | 794.2 [657.7, 930.8] | 910.2 [755.9, 1064.5] | 798.2 [650.2, 946.2] | 864.7 [739.0, 990.4] | 882.8 [718.9, 1046.7] | r2 3, r5_range 2 |
| written | Separated, 2 hubs | cyclic | 794.2 [657.7, 930.8] | 804.8 [671.1, 938.4] | 798.2 [650.2, 946.2] | 819.1 [660.4, 977.7] | 808.6 [661.1, 956.0] | r2 3, r5_range 2 |

## Table 9. Price of recovery for the ILP: written - relaxed, paired by seed (USD)

| layout | ILP | written - relaxed, total (USD) | written - relaxed, end-adjusted (USD) | C_end_adjust relaxed / written (USD) | served share relaxed / written |
|---|---|---|---|---|---|
| Co-located | none (any) | 0.30 [0.19, 0.41] | -0.03 [-0.19, 0.12] | 1.40 / 1.07 | 0.967 / 0.967 |
| Co-located | free, r3 | 0.30 [0.19, 0.41] | -0.03 [-0.19, 0.12] | 1.40 / 1.07 | 0.967 / 0.967 |
| Co-located | free, cyclic | 0.30 [0.19, 0.41] | -0.03 [-0.19, 0.12] | 1.40 / 1.07 | 0.967 / 0.967 |
| Separated, 1 hub | none (any) | 24.28 [16.68, 31.87] | 24.02 [16.49, 31.55] | 1.44 / 1.18 | 0.967 / 0.928 |
| Separated, 1 hub | free, r3 | 20.71 [16.83, 24.59] | 20.40 [16.62, 24.19] | 1.44 / 1.13 | 0.967 / 0.956 |
| Separated, 1 hub | free, cyclic | 7.87 [6.98, 8.77] | 7.51 [6.61, 8.41] | 1.44 / 1.07 | 0.967 / 0.967 |
| Separated, 2 hubs | none (any) | 24.15 [16.99, 31.30] | 23.94 [16.79, 31.08] | 1.40 / 1.19 | 0.967 / 0.928 |
| Separated, 2 hubs | free, r3 | 21.06 [16.99, 25.12] | 20.78 [16.74, 24.81] | 1.40 / 1.13 | 0.967 / 0.956 |
| Separated, 2 hubs | free, cyclic | 6.75 [5.92, 7.59] | 6.43 [5.60, 7.26] | 1.40 / 1.08 | 0.967 / 0.967 |

## Figures

- `figs/fig_x2_cost_layout_timetable_switch.pdf` / `.png` (7.2 in, double column). Panels (a, b): total cost by layout x timetable x transfer switch for the ILP (filled markers) and the best rule (open markers), relaxed and written targets, means with exact-t 95 % CI over seeds 0-4. Panels (c, d): paired change ILP(free) - ILP(none). Open triangles mark the bound-based limit where the transfers-free run stopped at TIME_LIMIT.
- `figs/fig_x2_transfer_rule_loss.pdf` / `.png` (7.2 in). Policy cost above r2 without transfers for REORDER_POINT and COST_AWARE (M3) under each timetable, relaxed and written targets.
- Supporting data: `figs/x2_per_instance_wide.csv` (one row per targets x layout x seed), `figs/tables.json`.

## Anomalies and caveats

1. **The relaxed headline does not exercise charging or transfers.** All 45 relaxed ILP optima buy 0 kWh and move 0 batteries: with B 3 spares per swap site and no end target, the 4-h window is covered by the initial stock. The X2 transfer question is therefore answered only under the written targets, and the relaxed separation cost is pure fixed cost.
2. **TIME_LIMIT on written r3 cells.** 10/15 written r3 transfers-free solves stopped at 300 s with MIP gaps 0.92-2.28 %, and the written cyclic cell of separated, 2 hubs, seed 1 stopped with a 0.47 % gap. On seeds 2 and 4 of both separated layouts the r3 incumbent is the MIP start (the ILP-none schedule, 0 transfers). The r3 value of transfers is therefore only bracketed: 3.56 to 15.18 USD for 1 hub and 3.09 to 15.58 USD for 2 hubs. The cyclic optimum still lies below the r3 bound on 10/10 instances.
3. **The cyclic-vs-r3 contrast is mostly a pricing convention.** The M8 cyclic spec splits the 20 USD tour fare over the legs (`split_f`), so one leg costs 5 USD (1 hub) or 4 USD (2 hubs) against 20 USD per r3 shuttle (ILP C_reb 7 / 6 vs 22 USD for one leg with 2 batteries). The 12.84 / 14.30 USD cyclic advantage should not be read as a routing benefit.
4. **Written-target policy rows violate the end-state constraints.** 147/150 written policy schedules violate the reported-only (18) (33 of them also (17)), and policy totals are identical across target settings except co-located r5_transfer and r5. This is by design: the policy reserve is read from `meta['written_R_end']`. The written-target gaps (18.88-20.33 % pooled) therefore compare an ILP that meets the targets with policies that mostly do not, and they understate the ILP advantage.
5. **Twelve MIP starts were rejected** (written `none` cells, unverified r2 / r5_range starts). All twelve solves still reached OPTIMAL, so the results are unaffected.
6. **Wide absolute CIs, tight paired CIs.** Seed-to-seed variation in policy cost is large (best_rule CI half-width about 137 USD at n 5), so per-layout gap CIs span roughly 10-32 %. The paired differences in Tables 4-7 and 9 carry the inferential weight.
7. **COST_AWARE (M3) is not cost-safe.** COST_AWARE is designed to transfer only when this pays, yet it is never cheaper than r2 except in 2/60 instance-cells. Its cost-awareness check does not prevent losses of 20-76 USD per window on average.
8. **A3 metric pack (from the script's RESULTS.md).** The ILP shows higher outage rates and lower BSR than r2 (for example, relaxed co-located: outage 0.333 vs 0.067, BSR 0.620 vs 0.975), because ending bikes low is free under the cost model. Keep this in mind if the paper reports service-quality metrics.
9. **Lower headline gap than round 3/4.** The X2 headline gap (20.98 %) is below the round-3/4 usd4h reference (29.55 % +/- 5.61, n 30). The setups differ in energy calibration (eBaaS), layouts and baseline set (best_rule includes r5_range, which is the per-instance minimiser on 7 of 15 instances per timetable). This should not be read as a regression.

## Interpretation

At the usd4h scale with the eBaaS calibration, the coordination gap (about 21 % against the best rule) comes from dispatch and swap timing, not from moving batteries. Without end targets the optimal schedule neither charges nor transfers, so separating chargers from swap sites is a pure fixed-cost decision: one hub adds 29.00 USD per window and two hubs add 58.04 USD, almost exactly the hub fixed charge, and transfers cannot recover any of it. Once the written end targets (rho 0.5) require recovery, swap-only sites need batteries charged at a hub, and transfers start to matter. The value is modest, however: about 16-17 USD per window (2.6-2.7 % of cost) with cyclic tours, achieved with a single leg carrying two batteries. Transfers mainly reduce the price of recovery in separated layouts, from about 24 USD to 7-8 USD, which shrinks the operating part of the separation penalty under written targets from about 23.5 USD to 6-7 USD, but do not remove it. The cyclic timetable dominates the r3 shuttles for the ILP on every separated instance (the cyclic optimum is below the r3 bound on 10/10), but because each cyclic leg is priced at a fraction of a shuttle fare, this is a statement about service pricing rather than about tour structure. For the policies, both transfer rules are net losses against the no-transfer rule r2. COST_AWARE (M3) roughly halves the REORDER_POINT loss on 30-min shuttles but not on 60-min tours, where REORDER_POINT fires less often. The manuscript can therefore claim that the coordinator extracts value from transfers that rules cannot (ILP saves 16-17 USD while the transfer rules lose 10-123 USD on average against r2), while stating clearly that transfers are a second-order lever at this scale and are only active when end-of-window recovery is enforced. A battery-binding instance, such as `r5_stress4h_k8` with positive spare shadow prices, would be needed to test whether transfers become first-order.

## Appendix A. Per-instance results (USD per 4-h window; TL = TIME_LIMIT with MIP gap)

| targets | layout | seed | ILP none | ILP free r3 | ILP free cyclic | ILP services r3/cyc | best_rule r3 | best_rule cyclic | r2 | r2_reorder r3/cyc | r5_transfer r3/cyc | gap % r3/cyc | ILP C_end_adjust none/r3/cyc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | Co-located | 0 | 532.60 | 532.60 | 532.60 | 0/0 | 612.30 (r5_range) | 612.30 (r5_range) | 613.14 | 757.94 / 638.50 | 658.97 / 620.81 | 13.02 / 13.02 | 1.55 / 1.55 / 1.55 |
| relaxed | Co-located | 1 | 582.68 | 582.68 | 582.68 | 0/0 | 830.01 (r2) | 830.01 (r2) | 830.01 | 933.24 / 839.73 | 874.80 / 852.89 | 29.80 / 29.80 | 1.31 / 1.31 / 1.31 |
| relaxed | Co-located | 2 | 582.92 | 582.92 | 582.92 | 0/0 | 729.21 (r5_range) | 729.21 (r5_range) | 745.50 | 881.92 / 753.07 | 792.34 / 754.11 | 20.06 / 20.06 | 1.31 / 1.31 / 1.31 |
| relaxed | Co-located | 3 | 583.33 | 583.33 | 583.33 | 0/0 | 856.46 (r2) | 856.46 (r2) | 856.46 | 977.56 / 892.27 | 871.22 / 862.54 | 31.89 / 31.89 | 1.50 / 1.50 / 1.50 |
| relaxed | Co-located | 4 | 546.19 | 546.19 | 546.19 | 0/0 | 635.69 (r5_range) | 635.69 (r5_range) | 636.81 | 743.87 / 693.79 | 737.59 / 691.24 | 14.08 / 14.08 | 1.36 / 1.36 / 1.36 |
| relaxed | Separated, 1 hub | 0 | 561.79 | 561.79 | 561.79 | 0/0 | 641.76 (r2) | 641.76 (r2) | 641.76 | 770.66 / 661.26 | 708.66 / 658.11 | 12.46 / 12.46 | 1.57 / 1.57 / 1.57 |
| relaxed | Separated, 1 hub | 1 | 611.00 | 611.00 | 611.00 | 0/0 | 858.62 (r2) | 858.62 (r2) | 858.62 | 925.48 / 858.62 | 925.48 / 885.12 | 28.84 / 28.84 | 1.49 / 1.49 / 1.49 |
| relaxed | Separated, 1 hub | 2 | 612.07 | 612.07 | 612.07 | 0/0 | 757.77 (r5_range) | 757.77 (r5_range) | 774.07 | 901.85 / 780.23 | 839.61 / 780.20 | 19.23 / 19.23 | 1.31 / 1.31 / 1.31 |
| relaxed | Separated, 1 hub | 3 | 612.48 | 612.48 | 612.48 | 0/0 | 885.15 (r2) | 885.15 (r2) | 885.15 | 1055.84 / 904.64 | 931.82 / 908.53 | 30.80 / 30.80 | 1.44 / 1.44 / 1.44 |
| relaxed | Separated, 1 hub | 4 | 575.38 | 575.38 | 575.38 | 0/0 | 664.30 (r5_range) | 664.30 (r5_range) | 665.48 | 752.30 / 672.74 | 732.14 / 752.55 | 13.39 / 13.39 | 1.37 / 1.37 / 1.37 |
| relaxed | Separated, 2 hubs | 0 | 590.87 | 590.87 | 590.87 | 0/0 | 670.95 (r2) | 670.95 (r2) | 670.95 | 799.62 / 682.45 | 737.46 / 685.30 | 11.93 / 11.93 | 1.47 / 1.47 / 1.47 |
| relaxed | Separated, 2 hubs | 1 | 640.73 | 640.73 | 640.73 | 0/0 | 887.81 (r2) | 887.81 (r2) | 887.81 | 954.29 / 887.81 | 954.29 / 887.81 | 27.83 / 27.83 | 1.28 / 1.28 / 1.28 |
| relaxed | Separated, 2 hubs | 2 | 640.05 | 640.05 | 640.05 | 0/0 | 786.96 (r5_range) | 786.96 (r5_range) | 803.26 | 930.90 / 820.76 | 889.58 / 822.66 | 18.67 / 18.67 | 1.33 / 1.33 / 1.33 |
| relaxed | Separated, 2 hubs | 3 | 641.71 | 641.71 | 641.71 | 0/0 | 914.34 (r2) | 914.34 (r2) | 914.34 | 1084.86 / 925.83 | 960.69 / 992.53 | 29.82 / 29.82 | 1.52 / 1.52 / 1.52 |
| relaxed | Separated, 2 hubs | 4 | 604.57 | 604.57 | 604.57 | 0/0 | 693.49 (r5_range) | 693.49 (r5_range) | 694.67 | 781.17 / 707.01 | 781.49 / 707.01 | 12.82 / 12.82 | 1.42 / 1.42 / 1.42 |
| written | Co-located | 0 | 532.81 | 532.81 | 532.81 | 0/0 | 612.30 (r5_range) | 612.30 (r5_range) | 613.14 | 757.94 / 638.50 | 681.55 / 660.24 | 12.98 / 12.98 | 1.09 / 1.09 / 1.09 |
| written | Co-located | 1 | 582.92 | 582.92 | 582.92 | 0/0 | 830.01 (r2) | 830.01 (r2) | 830.01 | 933.24 / 839.73 | 917.88 / 860.56 | 29.77 / 29.77 | 1.07 / 1.07 / 1.07 |
| written | Co-located | 2 | 583.19 | 583.19 | 583.19 | 0/0 | 729.21 (r5_range) | 729.21 (r5_range) | 745.50 | 881.92 / 753.07 | 812.40 / 761.86 | 20.02 / 20.02 | 1.04 / 1.04 / 1.04 |
| written | Co-located | 3 | 583.75 | 583.75 | 583.75 | 0/0 | 856.46 (r2) | 856.46 (r2) | 856.46 | 977.56 / 892.27 | 892.20 / 870.23 | 31.84 / 31.84 | 1.09 / 1.09 / 1.09 |
| written | Co-located | 4 | 546.54 | 546.54 | 546.54 | 0/0 | 635.69 (r5_range) | 635.69 (r5_range) | 636.81 | 743.87 / 693.79 | 759.64 / 691.24 | 14.02 / 14.02 | 1.08 / 1.08 / 1.08 |
| written | Separated, 1 hub | 0 | 589.50 | 584.00 (TL, 2.28 %) | 569.04 | 1/1 | 641.76 (r2) | 641.76 (r2) | 641.76 | 770.66 / 661.26 | 708.66 / 658.11 | 9.00 / 11.33 | 1.20 / 1.10 / 1.05 |
| written | Separated, 1 hub | 1 | 638.80 | 634.13 (TL, 2.24 %) | 619.67 | 1/1 | 858.62 (r2) | 858.62 (r2) | 858.62 | 925.48 / 858.62 | 925.48 / 885.12 | 26.15 / 27.83 | 1.17 / 1.06 / 1.08 |
| written | Separated, 1 hub | 2 | 632.60 | 632.60 (TL, 1.87 %) | 619.37 | 0/1 | 757.77 (r5_range) | 757.77 (r5_range) | 774.07 | 901.85 / 780.23 | 839.61 / 780.20 | 16.52 / 18.26 | 1.18 / 1.18 / 1.05 |
| written | Separated, 1 hub | 3 | 642.43 | 634.78 (TL, 2.10 %) | 619.99 | 1/1 | 885.15 (r2) | 885.15 (r2) | 885.15 | 1055.84 / 904.64 | 931.82 / 908.53 | 28.29 / 29.96 | 1.21 / 1.16 / 1.16 |
| written | Separated, 1 hub | 4 | 590.77 | 590.77 (TL, 0.92 %) | 584.02 | 0/1 | 664.30 (r5_range) | 664.30 (r5_range) | 665.48 | 752.30 / 672.74 | 732.14 / 752.55 | 11.07 / 12.08 | 1.15 / 1.15 / 1.03 |
| written | Separated, 2 hubs | 0 | 618.65 | 613.10 (TL, 2.18 %) | 597.12 | 1/1 | 670.95 (r2) | 670.95 (r2) | 670.95 | 799.62 / 682.45 | 737.46 / 685.30 | 8.62 / 11.00 | 1.21 / 1.08 / 1.09 |
| written | Separated, 2 hubs | 1 | 666.67 | 663.00 (TL, 2.16 %) | 647.53 (TL, 0.47 %) | 1/1 | 887.81 (r2) | 887.81 (r2) | 887.81 | 954.29 / 887.81 | 954.29 / 887.81 | 25.32 / 27.06 | 1.19 / 1.02 / 1.07 |
| written | Separated, 2 hubs | 2 | 661.79 | 661.79 (TL, 2.12 %) | 646.52 | 0/1 | 786.96 (r5_range) | 786.96 (r5_range) | 803.26 | 930.90 / 820.76 | 889.58 / 822.66 | 15.91 / 17.85 | 1.20 / 1.21 / 1.03 |
| written | Separated, 2 hubs | 3 | 671.62 | 665.40 (TL, 2.17 %) | 649.61 | 1/1 | 914.34 (r2) | 914.34 (r2) | 914.34 | 1084.86 / 925.83 | 960.69 / 992.53 | 27.23 / 28.95 | 1.22 / 1.16 / 1.15 |
| written | Separated, 2 hubs | 4 | 619.92 | 619.92 (TL, 1.02 %) | 610.92 | 0/1 | 693.49 (r5_range) | 693.49 (r5_range) | 694.67 | 781.17 / 707.01 | 781.49 / 707.01 | 10.61 / 11.91 | 1.16 / 1.16 / 1.08 |
