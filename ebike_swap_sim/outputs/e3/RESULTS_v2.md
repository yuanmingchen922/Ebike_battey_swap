# E3 v2 -- value of transfers and of separation, baseline side re-run with the fixed policy

Byte-identical instances `instances/*.json` of the v1 run (family `large`: 10 bikes / 30 orders / H = 24 / L = 12; layouts ['colocated', 'separated_1hub', 'separated_2hubs'], seeds [0, 1, 2]; equal totals sum B = 9, sum C = 9, hubs hold 3 spares; bike q0 ~ U{0.3L..0.6L}; shuttles every 6 slots). Arc libraries rebuilt with the v1 pruning (`pruning_for(inst)`), arc counts reproduced in 18/18 runs. **ILP rows (`no_transfers` and transfers free) are the unchanged v1 rows; the free ILP was not re-solved.** `baseline_legacy` reproduces the v1 baseline cost in 18/18 (layout, seed, rule) runs. Certificates: fix-and-solve (Threads 4, TimeLimit 120 s) of NONE starts in the `no_transfers` model and REORDER_POINT starts in the transfers-free model, under the written model and under `relax_end_targets` (rho = 0, R_end_j = 0). Wall time 12.7 min.

Headline gap definition: `gap_vs_baseline_pct = 100 (baseline - ILP) / baseline` with the ILP of the matching transfer switch (`NONE` <-> `no_transfers`, `REORDER_POINT` <-> transfers free).

## Headline

- (a) co-located 3 sites: NONE: baseline 1085.8 (v1) -> 1092.4 (fixed) vs ILP 556.1, gap 48.0 +/- 18.3 % (v1 gap 47.6 %); REORDER_POINT: baseline 1091.2 (v1) -> 1171.2 (fixed) vs ILP 556.1, gap 52.0 +/- 10.4 % (v1 gap 47.8 %).
- (b) 3 swap sites + 1 hub: NONE: baseline 1324.5 (v1) -> 1395.6 (fixed) vs ILP 868.4, gap 37.2 +/- 21.4 % (v1 gap 34.0 %); REORDER_POINT: baseline 1209.8 (v1) -> 1184.2 (fixed) vs ILP 611.5, gap 47.9 +/- 12.7 % (v1 gap 48.2 %).
- (c) 3 swap sites + 2 hubs: NONE: baseline 1364.5 (v1) -> 1435.6 (fixed) vs ILP 908.4, gap 36.2 +/- 20.9 % (v1 gap 33.0 %); REORDER_POINT: baseline 1143.9 (v1) -> 1175.1 (fixed) vs ILP 654.0, gap 44.0 +/- 9.5 % (v1 gap 41.7 %).
- value of transfers, (a) co-located 3 sites: ILP -0.0 +/- 0.0; fixed baseline (NONE - REORDER_POINT) -78.8 +/- 148.7 (v1 legacy -5.4); per seed [-124.494, -11.022, -100.828].
- value of transfers, (b) 3 swap sites + 1 hub: ILP 257.0 +/- 360.2; fixed baseline (NONE - REORDER_POINT) 211.3 +/- 233.1 (v1 legacy 114.7); per seed [118.472, 209.383, 306.094].
- value of transfers, (c) 3 swap sites + 2 hubs: ILP 254.5 +/- 358.5; fixed baseline (NONE - REORDER_POINT) 260.5 +/- 268.9 (v1 legacy 220.5); per seed [191.783, 204.383, 385.233].
- MIP start of the fixed baseline (NONE) accepted under the written model in 1/9 runs (v1 legacy: 2/9) and under rho = 0, R_end = 0 in 9/9; `baseline_reserve`: 2/9 written.
- MIP start of the fixed baseline (REORDER_POINT) accepted under the written model in 1/9 runs (v1 legacy: 2/9) and under rho = 0, R_end = 0 in 9/9; `baseline_reserve`: 3/9 written.

## Cost by layout x transfer switch (seed means; gap mean and 95 % t-CI over seeds)

| layout | transfer_rule | ilp_switch | variant | n | v1_baseline_total_mean | baseline_total_mean | ilp_total_mean | gap_vs_baseline_mean_pct | gap_vs_baseline_ci95_pct | unserved_mean | ilp_unserved_mean | swaps_mean | transfers_used_mean | batteries_moved_mean | jit_mean | reach_refusals_mean | late_suppressed_mean | viol_17_runs | viol_18_runs | start_written_accepted | start_relaxed_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | NONE | no_transfers | baseline | 3 | 1085.79 | 1092.38 | 556.05 | 47.95 | 18.26 | 6 | 0.67 | 9.33 | 0 | 0 | 10.33 | 1.67 | 0 | 2 | 1 | 1 | 3 |
| colocated | NONE | no_transfers | baseline_legacy | 3 | 1085.79 | 1085.79 | 556.05 | 47.56 | 18.48 | 6 | 0.67 | 8.67 | 0 | 0 | 0 | 2.67 | 0 | 1 | 1 | 2 | 3 |
| colocated | NONE | no_transfers | baseline_reserve | 3 | 1085.79 | 1091.16 | 556.05 | 47.90 | 18.28 | 6 | 0.67 | 8.33 | 0 | 0 | 10.33 | 2 | 3.33 | 1 | 1 | 2 | 3 |
| colocated | NONE | no_transfers | baseline_informed | 3 | 1085.79 | 1068.93 | 556.05 | 46.96 | 16.56 | 5.67 | 0.67 | 8.67 | 0 | 0 | 10.33 | 2 | 3.33 | 1 | 1 | 2 | 3 |
| colocated | REORDER_POINT | transfers free | baseline | 3 | 1091.23 | 1171.16 | 556.05 | 51.97 | 10.43 | 6.67 | 0.67 | 10 | 3.67 | 6.33 | 10 | 1.67 | 0 | 2 | 2 | 0 | 3 |
| colocated | REORDER_POINT | transfers free | baseline_legacy | 3 | 1091.23 | 1091.23 | 556.05 | 47.84 | 18.21 | 6 | 0.67 | 9.67 | 1 | 2 | 0 | 2.67 | 0 | 1 | 1 | 2 | 3 |
| colocated | REORDER_POINT | transfers free | baseline_reserve | 3 | 1091.23 | 1169.84 | 556.05 | 51.91 | 10.47 | 6.67 | 0.67 | 9.33 | 3.67 | 6.33 | 10 | 2.33 | 4 | 1 | 1 | 2 | 3 |
| colocated | REORDER_POINT | transfers free | baseline_informed | 3 | 1091.23 | 1124.32 | 556.05 | 50.11 | 8.96 | 6 | 0.67 | 8.33 | 4.67 | 7.33 | 10 | 2.33 | 4 | 1 | 1 | 1 | 2 |
| separated_1hub | NONE | no_transfers | baseline | 3 | 1324.45 | 1395.57 | 868.43 | 37.24 | 21.36 | 9.33 | 3.67 | 4.67 | 0 | 0 | 10 | 1.67 | 0 | 3 | 2 | 0 | 3 |
| separated_1hub | NONE | no_transfers | baseline_legacy | 3 | 1324.45 | 1324.45 | 868.43 | 34.04 | 26.39 | 8.33 | 3.67 | 5 | 0 | 0 | 0 | 2.67 | 0 | 3 | 2 | 0 | 3 |
| separated_1hub | NONE | no_transfers | baseline_reserve | 3 | 1324.45 | 1394.57 | 868.43 | 37.19 | 21.47 | 9.33 | 3.67 | 4.67 | 0 | 0 | 10 | 2 | 3.33 | 3 | 2 | 0 | 3 |
| separated_1hub | NONE | no_transfers | baseline_informed | 3 | 1324.45 | 1345.55 | 868.43 | 35.26 | 16.65 | 8.67 | 3.67 | 6 | 0 | 0 | 10 | 2 | 3.33 | 3 | 3 | 0 | 2 |
| separated_1hub | REORDER_POINT | transfers free | baseline | 3 | 1209.78 | 1184.25 | 611.47 | 47.93 | 12.66 | 6.33 | 0.67 | 7.33 | 5.67 | 10.67 | 10 | 1.67 | 0 | 2 | 2 | 1 | 3 |
| separated_1hub | REORDER_POINT | transfers free | baseline_legacy | 3 | 1209.78 | 1209.78 | 611.47 | 48.23 | 19.25 | 6.67 | 0.67 | 7.67 | 5.33 | 10.33 | 0 | 2.67 | 0 | 3 | 3 | 0 | 3 |
| separated_1hub | REORDER_POINT | transfers free | baseline_reserve | 3 | 1209.78 | 1183 | 611.47 | 47.88 | 12.56 | 6.33 | 0.67 | 7.33 | 5.67 | 10.67 | 10 | 2.33 | 4 | 2 | 2 | 1 | 3 |
| separated_1hub | REORDER_POINT | transfers free | baseline_informed | 3 | 1209.78 | 1161.36 | 611.47 | 47.06 | 6.89 | 6 | 0.67 | 8.33 | 6 | 11.67 | 10 | 2.33 | 4 | 3 | 2 | 0 | 3 |
| separated_2hubs | NONE | no_transfers | baseline | 3 | 1364.45 | 1435.57 | 908.43 | 36.19 | 20.94 | 9.33 | 3.67 | 4.67 | 0 | 0 | 10 | 1.67 | 0 | 3 | 2 | 0 | 3 |
| separated_2hubs | NONE | no_transfers | baseline_legacy | 3 | 1364.45 | 1364.45 | 908.43 | 33.04 | 25.73 | 8.33 | 3.67 | 5 | 0 | 0 | 0 | 2.67 | 0 | 3 | 2 | 0 | 3 |
| separated_2hubs | NONE | no_transfers | baseline_reserve | 3 | 1364.45 | 1434.57 | 908.43 | 36.15 | 21.05 | 9.33 | 3.67 | 4.67 | 0 | 0 | 10 | 2 | 3.33 | 3 | 2 | 0 | 3 |
| separated_2hubs | NONE | no_transfers | baseline_informed | 3 | 1364.45 | 1385.55 | 908.43 | 34.23 | 16.24 | 8.67 | 3.67 | 6 | 0 | 0 | 10 | 2 | 3.33 | 3 | 3 | 0 | 2 |
| separated_2hubs | REORDER_POINT | transfers free | baseline | 3 | 1143.91 | 1175.10 | 653.95 | 44.00 | 9.49 | 5.67 | 0.67 | 8.33 | 7.67 | 13 | 10.33 | 1.67 | 0 | 3 | 2 | 0 | 3 |
| separated_2hubs | REORDER_POINT | transfers free | baseline_legacy | 3 | 1143.91 | 1143.91 | 653.95 | 41.65 | 19.99 | 5.33 | 0.67 | 7.67 | 6.67 | 11 | 0 | 2.67 | 0 | 3 | 3 | 0 | 3 |
| separated_2hubs | REORDER_POINT | transfers free | baseline_reserve | 3 | 1143.91 | 1174.60 | 653.95 | 43.97 | 9.54 | 5.67 | 0.67 | 8.33 | 7.67 | 13 | 10.33 | 2 | 3.33 | 3 | 2 | 0 | 3 |
| separated_2hubs | REORDER_POINT | transfers free | baseline_informed | 3 | 1143.91 | 1147.63 | 653.95 | 42.89 | 5.13 | 5.33 | 0.67 | 8.67 | 7.33 | 13.33 | 10.33 | 2 | 3.33 | 3 | 3 | 0 | 3 |

## Value of transfers (per layout; ILP: no_transfers - free; baseline: NONE - REORDER_POINT)

| layout | quantity | n | mean | ci95 | min | max | per_seed |
|---|---|---|---|---|---|---|---|
| colocated | ILP: cost(no_transfers) - cost(transfers free) | 3 | 0 | 0 | 0 | 0 | [-0.0, 0.0, 0.0] |
| colocated | baseline: cost(NONE) - cost(REORDER_POINT) | 3 | -78.78 | 148.72 | -124.49 | -11.02 | [-124.494, -11.022, -100.828] |
| colocated | baseline_legacy: cost(NONE) - cost(REORDER_POINT) | 3 | -5.44 | 0.16 | -5.51 | -5.40 | [-5.4, -5.4, -5.511] |
| colocated | baseline_reserve: cost(NONE) - cost(REORDER_POINT) | 3 | -78.68 | 147.59 | -123.74 | -11.36 | [-123.744, -11.356, -100.939] |
| colocated | baseline_informed: cost(NONE) - cost(REORDER_POINT) | 3 | -55.39 | 120.28 | -109.51 | -16.20 | [-109.511, -16.2, -40.444] |
| separated_1hub | ILP: cost(no_transfers) - cost(transfers free) | 3 | 256.96 | 360.18 | 94.98 | 374.58 | [301.311, 94.983, 374.583] |
| separated_1hub | baseline: cost(NONE) - cost(REORDER_POINT) | 3 | 211.32 | 233.10 | 118.47 | 306.09 | [118.472, 209.383, 306.094] |
| separated_1hub | baseline_legacy: cost(NONE) - cost(REORDER_POINT) | 3 | 114.67 | 324.96 | -24.47 | 235.13 | [133.339, 235.133, -24.467] |
| separated_1hub | baseline_reserve: cost(NONE) - cost(REORDER_POINT) | 3 | 211.57 | 234.04 | 118.47 | 306.84 | [118.472, 209.383, 306.844] |
| separated_1hub | baseline_informed: cost(NONE) - cost(REORDER_POINT) | 3 | 184.19 | 304.32 | 54.75 | 298.29 | [199.522, 54.75, 298.294] |
| separated_2hubs | ILP: cost(no_transfers) - cost(transfers free) | 3 | 254.48 | 358.53 | 93.52 | 372.32 | [297.611, 93.522, 372.317] |
| separated_2hubs | baseline: cost(NONE) - cost(REORDER_POINT) | 3 | 260.47 | 268.89 | 191.78 | 385.23 | [191.783, 204.383, 385.233] |
| separated_2hubs | baseline_legacy: cost(NONE) - cost(REORDER_POINT) | 3 | 220.54 | 245.10 | 125.85 | 322.73 | [213.028, 322.733, 125.85] |
| separated_2hubs | baseline_reserve: cost(NONE) - cost(REORDER_POINT) | 3 | 259.97 | 266.74 | 191.78 | 383.73 | [191.783, 204.383, 383.733] |
| separated_2hubs | baseline_informed: cost(NONE) - cost(REORDER_POINT) | 3 | 237.92 | 309.83 | 135.73 | 376.88 | [201.133, 135.733, 376.883] |

## Cost of separation (cost(layout) - cost(co-located), same method and switch)

| layout | method | transfer_rule | n | mean | ci95 | per_seed |
|---|---|---|---|---|---|---|
| colocated | ilp | REORDER_POINT | 3 | 0 | 0 | [0.0, 0.0, 0.0] |
| colocated | baseline | REORDER_POINT | 3 | 0 | 0 | [0.0, 0.0, 0.0] |
| colocated | baseline | NONE | 3 | 0 | 0 | [0.0, 0.0, 0.0] |
| colocated | baseline_legacy | REORDER_POINT | 3 | 0 | 0 | [0.0, 0.0, 0.0] |
| separated_1hub | ilp | REORDER_POINT | 3 | 55.42 | 10.25 | [55.222, 51.4, 59.644] |
| separated_1hub | baseline | REORDER_POINT | 3 | 13.09 | 293.91 | [120.956, -113.439, 31.75] |
| separated_1hub | baseline | NONE | 3 | 303.19 | 432.26 | [363.922, 106.967, 438.672] |
| separated_1hub | baseline_legacy | REORDER_POINT | 3 | 118.56 | 318.64 | [173.161, -27.972, 210.478] |
| separated_2hubs | ilp | REORDER_POINT | 3 | 97.90 | 11.46 | [98.922, 92.861, 101.911] |
| separated_2hubs | baseline | REORDER_POINT | 3 | 3.94 | 195.41 | [87.644, -68.439, -7.389] |
| separated_2hubs | baseline | NONE | 3 | 343.19 | 432.26 | [403.922, 146.967, 478.672] |
| separated_2hubs | baseline_legacy | REORDER_POINT | 3 | 52.69 | 279.03 | [133.472, -75.572, 100.161] |

## Per-run table (baseline variants)

| layout | seed | transfer_rule | method | v1_baseline_total | total | delta_vs_v1_baseline | ilp_total | ilp_status | gap_vs_baseline_pct | n_unserved | ilp_unserved_n | n_swaps | transfers_used | batteries_moved | jit_dispatches | reach_refusals | reach_bikes_sent_to_swap | late_trips_suppressed | viol_17 | viol_18 | check_families | start_written_accepted | start_written_status | start_relaxed_accepted | check_families_relaxed | v1_mip_start_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | 0 | NONE | baseline | 803.90 | 800.08 | -3.82 | 484.22 | OPTIMAL | 39.48 | 3 | 0 | 10 | 0 | 0 | 13 | 1 | 1 | 0 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 0 | NONE | baseline_informed | 803.90 | 801.39 | -2.51 | 484.22 | OPTIMAL | 39.58 | 3 | 0 | 9 | 0 | 0 | 13 | 1 | 1 | 4 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 0 | NONE | baseline_legacy | 803.90 | 803.90 | 0 | 484.22 | OPTIMAL | 39.77 | 3 | 0 | 10 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 0 | NONE | baseline_reserve | 803.90 | 799.11 | -4.79 | 484.22 | OPTIMAL | 39.41 | 3 | 0 | 9 | 0 | 0 | 13 | 1 | 1 | 4 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 0 | REORDER_POINT | baseline | 809.30 | 924.57 | 115.27 | 484.22 | OPTIMAL | 47.63 | 4 | 0 | 10 | 5 | 7 | 12 | 1 | 1 | 0 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | True |
| colocated | 0 | REORDER_POINT | baseline_informed | 809.30 | 910.91 | 101.61 | 484.22 | OPTIMAL | 46.84 | 4 | 0 | 9 | 5 | 6 | 12 | 2 | 1 | 6 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 0 | REORDER_POINT | baseline_legacy | 809.30 | 809.30 | 0 | 484.22 | OPTIMAL | 40.17 | 3 | 0 | 10 | 1 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 0 | REORDER_POINT | baseline_reserve | 809.30 | 922.85 | 113.55 | 484.22 | OPTIMAL | 47.53 | 4 | 0 | 9 | 5 | 7 | 12 | 2 | 1 | 6 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 1 | NONE | baseline | 1113.94 | 1195.13 | 81.19 | 575.62 | OPTIMAL | 51.84 | 7 | 1 | 9 | 0 | 0 | 9 | 0 | 0 | 0 | 1 | 1.50 | {"(17)": 1, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 1 | NONE | baseline_informed | 1113.94 | 1123.89 | 9.96 | 575.62 | OPTIMAL | 48.78 | 6 | 1 | 8 | 0 | 0 | 9 | 0 | 0 | 0 | 1 | 0.50 | {"(17)": 1, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 1 | NONE | baseline_legacy | 1113.94 | 1113.94 | 0 | 575.62 | OPTIMAL | 48.33 | 6 | 1 | 9 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 1.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 1 | NONE | baseline_reserve | 1113.94 | 1194.80 | 80.86 | 575.62 | OPTIMAL | 51.82 | 7 | 1 | 8 | 0 | 0 | 9 | 0 | 0 | 0 | 1 | 0.50 | {"(17)": 1, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 1 | REORDER_POINT | baseline | 1119.34 | 1206.16 | 86.82 | 575.62 | OPTIMAL | 52.28 | 7 | 1 | 10 | 2 | 4 | 9 | 0 | 0 | 0 | 2 | 2.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 1 | REORDER_POINT | baseline_informed | 1119.34 | 1140.09 | 20.76 | 575.62 | OPTIMAL | 49.51 | 6 | 1 | 8 | 3 | 6 | 9 | 0 | 0 | 0 | 1 | 0.50 | {"(17)": 1, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 1 | REORDER_POINT | baseline_legacy | 1119.34 | 1119.34 | 0 | 575.62 | OPTIMAL | 48.58 | 6 | 1 | 10 | 1 | 2 | 0 | 1 | 0 | 0 | 1 | 2.50 | {"(17)": 1, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 1 | REORDER_POINT | baseline_reserve | 1119.34 | 1206.16 | 86.82 | 575.62 | OPTIMAL | 52.28 | 7 | 1 | 10 | 2 | 4 | 9 | 0 | 0 | 0 | 2 | 2.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| colocated | 2 | NONE | baseline | 1339.53 | 1281.93 | -57.60 | 608.32 | OPTIMAL | 52.55 | 8 | 1 | 9 | 0 | 0 | 9 | 4 | 4 | 0 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | True |
| colocated | 2 | NONE | baseline_informed | 1339.53 | 1281.51 | -58.02 | 608.32 | OPTIMAL | 52.53 | 8 | 1 | 9 | 0 | 0 | 9 | 5 | 4 | 6 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 2 | NONE | baseline_legacy | 1339.53 | 1339.53 | 0 | 608.32 | OPTIMAL | 54.59 | 9 | 1 | 7 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 2 | NONE | baseline_reserve | 1339.53 | 1279.57 | -59.96 | 608.32 | OPTIMAL | 52.46 | 8 | 1 | 8 | 0 | 0 | 9 | 5 | 4 | 6 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 2 | REORDER_POINT | baseline | 1345.04 | 1382.76 | 37.72 | 608.32 | OPTIMAL | 56.01 | 9 | 1 | 10 | 4 | 8 | 9 | 4 | 4 | 0 | 0 | 0.50 | {"(18)": 1} | False | INFEASIBLE | True | {} | True |
| colocated | 2 | REORDER_POINT | baseline_informed | 1345.04 | 1321.96 | -23.08 | 608.32 | OPTIMAL | 53.98 | 8 | 1 | 8 | 6 | 10 | 9 | 5 | 4 | 6 | 0 | 0 | {"(9)": 1} | False | INFEASIBLE | False | {"(9)": 1} | True |
| colocated | 2 | REORDER_POINT | baseline_legacy | 1345.04 | 1345.04 | 0 | 608.32 | OPTIMAL | 54.77 | 9 | 1 | 9 | 1 | 2 | 0 | 5 | 0 | 0 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| colocated | 2 | REORDER_POINT | baseline_reserve | 1345.04 | 1380.51 | 35.47 | 608.32 | OPTIMAL | 55.93 | 9 | 1 | 9 | 4 | 8 | 9 | 5 | 4 | 6 | 0 | 0 | {} | True | OPTIMAL | True | {} | True |
| separated_1hub | 0 | NONE | baseline | 1115.80 | 1164 | 48.20 | 840.75 | OPTIMAL | 27.77 | 7 | 3 | 6 | 0 | 0 | 12 | 1 | 1 | 0 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 0 | NONE | baseline_informed | 1115.80 | 1170.15 | 54.35 | 840.75 | OPTIMAL | 28.15 | 7 | 3 | 6 | 0 | 0 | 12 | 2 | 1 | 6 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 0 | NONE | baseline_legacy | 1115.80 | 1115.80 | 0 | 840.75 | OPTIMAL | 24.65 | 6 | 3 | 6 | 0 | 0 | 0 | 2 | 0 | 0 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 0 | NONE | baseline_reserve | 1115.80 | 1162.50 | 46.70 | 840.75 | OPTIMAL | 27.68 | 7 | 3 | 6 | 0 | 0 | 12 | 2 | 1 | 6 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 0 | REORDER_POINT | baseline | 982.46 | 1045.53 | 63.07 | 539.44 | TIME_LIMIT | 48.41 | 5 | 0 | 8 | 7 | 11 | 12 | 1 | 1 | 0 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 0 | REORDER_POINT | baseline_informed | 982.46 | 970.63 | -11.83 | 539.44 | TIME_LIMIT | 44.42 | 4 | 0 | 9 | 7 | 12 | 12 | 2 | 1 | 6 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 0 | REORDER_POINT | baseline_legacy | 982.46 | 982.46 | 0 | 539.44 | TIME_LIMIT | 45.09 | 4 | 0 | 8 | 6 | 11 | 0 | 2 | 0 | 0 | 2 | 1.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 0 | REORDER_POINT | baseline_reserve | 982.46 | 1044.03 | 61.57 | 539.44 | TIME_LIMIT | 48.33 | 5 | 0 | 8 | 7 | 11 | 12 | 2 | 1 | 6 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 1 | NONE | baseline | 1326.50 | 1302.10 | -24.40 | 722 | OPTIMAL | 44.55 | 8 | 2 | 5 | 0 | 0 | 9 | 0 | 0 | 0 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 1 | NONE | baseline_informed | 1326.50 | 1233.45 | -93.05 | 722 | OPTIMAL | 41.46 | 7 | 2 | 6 | 0 | 0 | 9 | 0 | 0 | 0 | 3 | 1.50 | {"(17)": 3, "(18)": 1, "(9)": 1} | False | INFEASIBLE | False | {"(9)": 1} | False |
| separated_1hub | 1 | NONE | baseline_legacy | 1326.50 | 1326.50 | 0 | 722 | OPTIMAL | 45.57 | 8 | 2 | 5 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 1 | NONE | baseline_reserve | 1326.50 | 1302.10 | -24.40 | 722 | OPTIMAL | 44.55 | 8 | 2 | 5 | 0 | 0 | 9 | 0 | 0 | 0 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 1 | REORDER_POINT | baseline | 1091.37 | 1092.72 | 1.35 | 627.02 | TIME_LIMIT | 42.62 | 5 | 1 | 8 | 5 | 11 | 9 | 0 | 0 | 0 | 2 | 3.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 1 | REORDER_POINT | baseline_informed | 1091.37 | 1178.70 | 87.33 | 627.02 | TIME_LIMIT | 46.80 | 6 | 1 | 8 | 5 | 11 | 9 | 0 | 0 | 0 | 2 | 3.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 1 | REORDER_POINT | baseline_legacy | 1091.37 | 1091.37 | 0 | 627.02 | TIME_LIMIT | 42.55 | 5 | 1 | 8 | 6 | 11 | 0 | 1 | 0 | 0 | 2 | 3.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 1 | REORDER_POINT | baseline_reserve | 1091.37 | 1092.72 | 1.35 | 627.02 | TIME_LIMIT | 42.62 | 5 | 1 | 8 | 5 | 11 | 9 | 0 | 0 | 0 | 2 | 3.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 2 | NONE | baseline | 1531.05 | 1720.60 | 189.55 | 1042.55 | OPTIMAL | 39.41 | 13 | 6 | 3 | 0 | 0 | 9 | 4 | 4 | 0 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 2 | NONE | baseline_informed | 1531.05 | 1633.05 | 102 | 1042.55 | OPTIMAL | 36.16 | 12 | 6 | 6 | 0 | 0 | 9 | 4 | 4 | 4 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 2 | NONE | baseline_legacy | 1531.05 | 1531.05 | 0 | 1042.55 | OPTIMAL | 31.91 | 11 | 6 | 4 | 0 | 0 | 0 | 5 | 0 | 0 | 2 | 0 | {"(17)": 2} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 2 | NONE | baseline_reserve | 1531.05 | 1719.10 | 188.05 | 1042.55 | OPTIMAL | 39.35 | 13 | 6 | 3 | 0 | 0 | 9 | 4 | 4 | 4 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 2 | REORDER_POINT | baseline | 1555.52 | 1414.51 | -141.01 | 667.97 | OPTIMAL | 52.78 | 9 | 1 | 6 | 5 | 10 | 9 | 4 | 4 | 0 | 0 | 0 | {} | True | OPTIMAL | True | {} | False |
| separated_1hub | 2 | REORDER_POINT | baseline_informed | 1555.52 | 1334.76 | -220.76 | 667.97 | OPTIMAL | 49.96 | 8 | 1 | 8 | 6 | 12 | 9 | 5 | 4 | 6 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 2 | REORDER_POINT | baseline_legacy | 1555.52 | 1555.52 | 0 | 667.97 | OPTIMAL | 57.06 | 11 | 1 | 7 | 4 | 9 | 0 | 5 | 0 | 0 | 2 | 2.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_1hub | 2 | REORDER_POINT | baseline_reserve | 1555.52 | 1412.26 | -143.26 | 667.97 | OPTIMAL | 52.70 | 9 | 1 | 6 | 5 | 10 | 9 | 5 | 4 | 6 | 0 | 0 | {} | True | OPTIMAL | True | {} | False |
| separated_2hubs | 0 | NONE | baseline | 1155.80 | 1204 | 48.20 | 880.75 | OPTIMAL | 26.85 | 7 | 3 | 6 | 0 | 0 | 12 | 1 | 1 | 0 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 0 | NONE | baseline_informed | 1155.80 | 1210.15 | 54.35 | 880.75 | OPTIMAL | 27.22 | 7 | 3 | 6 | 0 | 0 | 12 | 2 | 1 | 6 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 0 | NONE | baseline_legacy | 1155.80 | 1155.80 | 0 | 880.75 | OPTIMAL | 23.80 | 6 | 3 | 6 | 0 | 0 | 0 | 2 | 0 | 0 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 0 | NONE | baseline_reserve | 1155.80 | 1202.50 | 46.70 | 880.75 | OPTIMAL | 26.76 | 7 | 3 | 6 | 0 | 0 | 12 | 2 | 1 | 6 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 0 | REORDER_POINT | baseline | 942.77 | 1012.22 | 69.44 | 583.14 | TIME_LIMIT | 42.39 | 4 | 0 | 9 | 10 | 14 | 12 | 1 | 1 | 0 | 2 | 1.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 0 | REORDER_POINT | baseline_informed | 942.77 | 1009.02 | 66.24 | 583.14 | TIME_LIMIT | 42.21 | 4 | 0 | 9 | 8 | 14 | 12 | 2 | 1 | 6 | 2 | 1.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 0 | REORDER_POINT | baseline_legacy | 942.77 | 942.77 | 0 | 583.14 | TIME_LIMIT | 38.15 | 3 | 0 | 9 | 8 | 13 | 0 | 2 | 0 | 0 | 2 | 2.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 0 | REORDER_POINT | baseline_reserve | 942.77 | 1010.72 | 67.94 | 583.14 | TIME_LIMIT | 42.30 | 4 | 0 | 9 | 10 | 14 | 12 | 2 | 1 | 6 | 2 | 1.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 1 | NONE | baseline | 1366.50 | 1342.10 | -24.40 | 762 | OPTIMAL | 43.22 | 8 | 2 | 5 | 0 | 0 | 9 | 0 | 0 | 0 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 1 | NONE | baseline_informed | 1366.50 | 1273.45 | -93.05 | 762 | OPTIMAL | 40.16 | 7 | 2 | 6 | 0 | 0 | 9 | 0 | 0 | 0 | 3 | 1.50 | {"(17)": 3, "(18)": 1, "(9)": 1} | False | INFEASIBLE | False | {"(9)": 1} | False |
| separated_2hubs | 1 | NONE | baseline_legacy | 1366.50 | 1366.50 | 0 | 762 | OPTIMAL | 44.24 | 8 | 2 | 5 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 1 | NONE | baseline_reserve | 1366.50 | 1342.10 | -24.40 | 762 | OPTIMAL | 43.22 | 8 | 2 | 5 | 0 | 0 | 9 | 0 | 0 | 0 | 2 | 0.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 1 | REORDER_POINT | baseline | 1043.77 | 1137.72 | 93.95 | 668.48 | TIME_LIMIT | 41.24 | 5 | 1 | 8 | 6 | 11 | 9 | 0 | 0 | 0 | 2 | 3.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 1 | REORDER_POINT | baseline_informed | 1043.77 | 1137.72 | 93.95 | 668.48 | TIME_LIMIT | 41.24 | 5 | 1 | 8 | 6 | 11 | 9 | 0 | 0 | 0 | 2 | 3.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 1 | REORDER_POINT | baseline_legacy | 1043.77 | 1043.77 | 0 | 668.48 | TIME_LIMIT | 35.96 | 4 | 1 | 7 | 6 | 10 | 0 | 1 | 0 | 0 | 2 | 2.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 1 | REORDER_POINT | baseline_reserve | 1043.77 | 1137.72 | 93.95 | 668.48 | TIME_LIMIT | 41.24 | 5 | 1 | 8 | 6 | 11 | 9 | 0 | 0 | 0 | 2 | 3.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | NONE | baseline | 1571.05 | 1760.60 | 189.55 | 1082.55 | OPTIMAL | 38.51 | 13 | 6 | 3 | 0 | 0 | 9 | 4 | 4 | 0 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | NONE | baseline_informed | 1571.05 | 1673.05 | 102 | 1082.55 | OPTIMAL | 35.29 | 12 | 6 | 6 | 0 | 0 | 9 | 4 | 4 | 4 | 3 | 1.50 | {"(17)": 3, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | NONE | baseline_legacy | 1571.05 | 1571.05 | 0 | 1082.55 | OPTIMAL | 31.09 | 11 | 6 | 4 | 0 | 0 | 0 | 5 | 0 | 0 | 2 | 0 | {"(17)": 2} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | NONE | baseline_reserve | 1571.05 | 1759.10 | 188.05 | 1082.55 | OPTIMAL | 38.46 | 13 | 6 | 3 | 0 | 0 | 9 | 4 | 4 | 4 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | REORDER_POINT | baseline | 1445.20 | 1375.37 | -69.83 | 710.23 | TIME_LIMIT | 48.36 | 8 | 1 | 8 | 7 | 14 | 10 | 4 | 4 | 0 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | REORDER_POINT | baseline_informed | 1445.20 | 1296.17 | -149.03 | 710.23 | TIME_LIMIT | 45.21 | 7 | 1 | 9 | 8 | 15 | 10 | 4 | 4 | 4 | 1 | 0.50 | {"(17)": 1, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | REORDER_POINT | baseline_legacy | 1445.20 | 1445.20 | 0 | 710.23 | TIME_LIMIT | 50.86 | 9 | 1 | 7 | 6 | 10 | 0 | 5 | 0 | 0 | 2 | 2.50 | {"(17)": 2, "(18)": 1} | False | INFEASIBLE | True | {} | False |
| separated_2hubs | 2 | REORDER_POINT | baseline_reserve | 1445.20 | 1375.37 | -69.83 | 710.23 | TIME_LIMIT | 48.36 | 8 | 1 | 8 | 7 | 14 | 10 | 4 | 4 | 4 | 1 | 0 | {"(17)": 1} | False | INFEASIBLE | True | {} | False |

## Interpretation

With the fixed policy the coordination gap is 40 % (NONE vs no_transfers ILP) and 48 % (REORDER_POINT vs transfers-free ILP) on average over layouts and seeds, against 38 % / 46 % for the v1 policy: the E3 conclusions (transfers are worth nothing when every site charges and 250-260 units when it does not; separation costs the coordinator 55-100 units) do not involve the baseline and are unchanged; the baseline moves by +39.1 units on average (6 runs cheaper, 12 dearer of 18). Value of transfers for the baseline (NONE - REORDER_POINT, seed means): (a) co-located 3 sites -79 (v1 -5; ILP -0); (b) 3 swap sites + 1 hub 211 (v1 115; ILP 257); (c) 3 swap sites + 2 hubs 260 (v1 221; ILP 254). Where charging is separated from swapping the reorder-point rule recovers 83-101 % of the value the coordinator extracts from the shuttles; in the co-located layout the fixed policy's extra swaps trigger shipments between sites that charge themselves ([-124.494, -11.022, -100.828] per seed, 3.7 services and C_reb 19.6 per run), so the rule costs 79 units there, whereas the ILP never ships between co-located sites (value 0). Cost of separation (layout minus co-located): (b) 3 swap sites + 1 hub ILP 55 / fixed baseline REORDER_POINT 13 / NONE 303; (c) 3 swap sites + 2 hubs ILP 98 / fixed baseline REORDER_POINT 4 / NONE 343. Without transfers the baseline pays several times more for separation than the coordinator (swap-only sites with two spares each and no charger run dry); with the reorder-point rule its separation penalty is smaller than the ILP's, because its co-located REORDER_POINT run is itself inflated by the pointless shipments above. Variants (mean over layouts, rules and seeds): legacy 1203.3, fixed 1242.3, reserve 1241.3, informed 1205.6. On this swap-scarce family (9 spares for 10 bikes starting at 0.3-0.6 L) the fixed policy is dearer than the v1 policy on average; the likely mechanism (not isolated here) is that the just-in-time rule (10.1 JIT dispatches per run) keeps bikes idle-but-committed instead of sending them to swap early, and one more order per run is left unserved (6.78 -> 7.22); the stock-aware site choice of `baseline_informed` is the one variant that helps here, 37 units below the fixed default. MIP starts: 2/18 fixed-baseline starts are feasible points of the written model; the rejected ones all carry (17)/(18) shortfalls (report-only families), and 18/18 are accepted once rho = 0 and R_end = 0. Note that the ILP rows at the written targets therefore compare a constrained optimum with an unconstrained policy; the partial v1 side run `relaxed_end_targets/` (seed 0, two layouts) showed the ILP cost moving by only a few units when (17)-(18) are dropped.

## Anomalies / checks

- starts rejected even under rho = 0, R_end = 0: colocated/seed2/baseline_informed/REORDER_POINT ({"(9)": 1}), separated_1hub/seed1/baseline_informed/NONE ({"(9)": 1}), separated_2hubs/seed1/baseline_informed/NONE ({"(9)": 1})
- v1 ILP rows not proven optimal (inherited): separated_1hub/seed0/transfers free (TIME_LIMIT, gap 0.0096), separated_1hub/seed1/transfers free (TIME_LIMIT, gap 0.0086), separated_2hubs/seed0/transfers free (TIME_LIMIT, gap 0.0097), separated_2hubs/seed1/transfers free (TIME_LIMIT, gap 0.0085), separated_2hubs/seed2/transfers free (TIME_LIMIT, gap 0.0037)

## Figures

- `fig_cost_by_layout_v2.png`
- `fig_transfer_value_v2.png`

Files: `results_v2.csv` (baseline variant rows + the unchanged v1 ILP rows, column `source`), `wall_time_v2.json`. v1 files (`RESULTS.md`, `results.csv`, figures without suffix) are untouched.
