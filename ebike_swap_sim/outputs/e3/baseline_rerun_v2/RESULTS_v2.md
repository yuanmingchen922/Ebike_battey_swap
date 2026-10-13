# E3 v2 -- fixed baseline re-run (ILP rows unchanged)

Same 9 saved layout instances (`instances/*.json`: family large, sum B = 9, sum C = 9, q0 ~ U{0.3L..0.6L}, seeds 0-2) and the two relaxed-end-target instances of `relaxed_end_targets/` (seed 0, rho = 0, R_end = 0); same arc library (n_arcs equal to the old results on every instance: True). ILP rows (transfers free / `no_transfers`) from the old `results.csv`. Baseline families: NONE (`baseline`, `baseline_legacy`, `baseline_reserve`, `baseline_informed`) and REORDER_POINT (`baseline_reorder`, `baseline_reorder_legacy`); the legacy variants reproduce the old rows exactly: True. `ilp_total` = the ILP of the same transfer switch (free for REORDER_POINT, `no_transfers` for NONE); `gap_vs_ilp_free_pct` compares every variant with the transfers-free ILP. `gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline, plan definition); `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP (baseline excess over the optimum).

## Headline

Seed-and-layout means: baseline NONE 1258.2 -> 1307.8 (unserved 7.56 -> 8.22) against the no-transfer ILP 777.6: headline gap 38.2 % -> 40.5 %; baseline REORDER_POINT 1148.3 -> 1176.8 (unserved 6.00 -> 6.22) against the transfers-free ILP 607.2: gap 45.9 % -> 48.0 %. New NONE start accepted by the written model on 1 / 9 runs and under the fully relaxed end targets on 9 / 9; REORDER_POINT start 1 / 9 and 9 / 9. The E3 headline (ILP vs ILP: value of transfers, cost of separation) is unaffected.

`baseline` MIP start accepted (Gurobi fix-and-solve, all variables fixed, Threads 4, TimeLimit 120 s): written model 1/9, rho = 0 only 1/9, fully relaxed end targets (rho = 0, R_end = 0) 9/9; certificate agrees with `evaluate.check` on every run: True.

`baseline_reorder` MIP start accepted (Gurobi fix-and-solve, all variables fixed, Threads 4, TimeLimit 120 s): written model 1/9, rho = 0 only 2/9, fully relaxed end targets (rho = 0, R_end = 0) 9/9; certificate agrees with `evaluate.check` on every run: True.

## Seed means per layout and variant (group main)

| layout | variant | total | C_travel | C_elec | unserved | response | lateness | C_reb | n_unserved | n_swaps | transfers_used | batteries_moved | end_full_total | viol_17_local_sum | viol_18_global | gap_vs_baseline_pct | gap_vs_ilp_free_pct | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | baseline | 1092.38 | 101.75 | 7.96 | 600 | 224.33 | 53.33 | 0 | 6 | 9.33 | 0 | 0 | 4.67 | 0.67 | 0.50 | 47.95 | 47.95 | 3 |
| colocated | baseline_informed | 1068.93 | 103.60 | 8 | 566.67 | 229 | 56.67 | 0 | 5.67 | 8.67 | 0 | 0 | 5.33 | 0.33 | 0.17 | 46.96 | 46.96 | 3 |
| colocated | baseline_legacy | 1085.79 | 102.90 | 7.89 | 600 | 220 | 50 | 0 | 6 | 8.67 | 0 | 0 | 5.33 | 0.67 | 0.50 | 47.56 | 47.56 | 3 |
| colocated | baseline_reorder | 1171.16 | 100.45 | 7.78 | 666.67 | 218.33 | 53.33 | 19.60 | 6.67 | 10 | 3.67 | 6.33 | 3.67 | 1 | 1 | 51.97 | 51.97 | 3 |
| colocated | baseline_reorder_legacy | 1091.23 | 102.90 | 7.93 | 600 | 220 | 50 | 5.40 | 6 | 9.67 | 1 | 2 | 4.33 | 0.33 | 0.83 | 47.84 | 47.84 | 3 |
| colocated | baseline_reserve | 1091.16 | 100.75 | 7.74 | 600 | 224.33 | 53.33 | 0 | 6 | 8.33 | 0 | 0 | 5.67 | 0.33 | 0.17 | 47.90 | 47.90 | 3 |
| separated_1hub | baseline | 1395.57 | 86.90 | 0 | 933.33 | 189 | 41.33 | 0 | 9.33 | 4.67 | 0 | 0 | 4.33 | 2 | 0.67 | 37.24 | 55.56 | 3 |
| separated_1hub | baseline_informed | 1345.55 | 94.55 | 0 | 866.67 | 196 | 43.33 | 0 | 8.67 | 6 | 0 | 0 | 3 | 3 | 1.50 | 35.26 | 54.05 | 3 |
| separated_1hub | baseline_legacy | 1324.45 | 95.45 | 0 | 833.33 | 200 | 50.67 | 0 | 8.33 | 5 | 0 | 0 | 4 | 2.33 | 0.67 | 34.04 | 53.59 | 3 |
| separated_1hub | baseline_reorder | 1184.25 | 102.45 | 4.33 | 633.33 | 219.33 | 49.33 | 30.47 | 6.33 | 7.33 | 5.67 | 10.67 | 4 | 1.33 | 1.33 | 47.93 | 47.93 | 3 |
| separated_1hub | baseline_reorder_legacy | 1209.78 | 101.90 | 3.81 | 666.67 | 214.33 | 49.33 | 28.73 | 6.67 | 7.67 | 5.33 | 10.33 | 2 | 2 | 2.50 | 48.23 | 48.23 | 3 |
| separated_1hub | baseline_reserve | 1394.57 | 85.90 | 0 | 933.33 | 189 | 41.33 | 0 | 9.33 | 4.67 | 0 | 0 | 4.33 | 2 | 0.67 | 37.19 | 55.53 | 3 |
| separated_2hubs | baseline | 1435.57 | 86.90 | 0 | 933.33 | 189 | 41.33 | 0 | 9.33 | 4.67 | 0 | 0 | 4.33 | 2 | 0.67 | 36.19 | 53.81 | 3 |
| separated_2hubs | baseline_informed | 1385.55 | 94.55 | 0 | 866.67 | 196 | 43.33 | 0 | 8.67 | 6 | 0 | 0 | 3 | 3 | 1.50 | 34.23 | 52.29 | 3 |
| separated_2hubs | baseline_legacy | 1364.45 | 95.45 | 0 | 833.33 | 200 | 50.67 | 0 | 8.33 | 5 | 0 | 0 | 4 | 2.33 | 0.67 | 33.04 | 51.81 | 3 |
| separated_2hubs | baseline_reorder | 1175.10 | 103.50 | 4.33 | 566.67 | 225.33 | 49.33 | 40.93 | 5.67 | 8.33 | 7.67 | 13 | 3 | 1.67 | 1.67 | 44.00 | 44.00 | 3 |
| separated_2hubs | baseline_reorder_legacy | 1143.91 | 106.75 | 3.63 | 533.33 | 227.67 | 52 | 35.53 | 5.33 | 7.67 | 6.67 | 11 | 2 | 2 | 2.50 | 41.65 | 41.65 | 3 |
| separated_2hubs | baseline_reserve | 1434.57 | 85.90 | 0 | 933.33 | 189 | 41.33 | 0 | 9.33 | 4.67 | 0 | 0 | 4.33 | 2 | 0.67 | 36.15 | 53.77 | 3 |

ILP references (old rows) and old baseline NONE per layout:

| layout | ilp_free_total | ilp_none_total | ilp_free_n_unserved | ilp_none_n_unserved | old_baseline_total | n |
|---|---|---|---|---|---|---|
| colocated | 556.05 | 556.05 | 0.67 | 0.67 | 1085.79 | 3 |
| separated_1hub | 611.47 | 868.43 | 0.67 | 3.67 | 1324.45 | 3 |
| separated_2hubs | 653.95 | 908.43 | 0.67 | 3.67 | 1364.45 | 3 |

## Per run (both groups)

| group | layout | seed | variant | total | old_baseline_total | legacy_matches_old | n_unserved | transfers_used | batteries_moved | C_reb | families | ilp_total | ilp_free_total | ilp_none_total | gap_vs_baseline_pct | gap_vs_ilp_free_pct | cert_written | cert_rho0 | cert_relaxed | ilp_free_mip_start_accepted_old | ilp_none_mip_start_accepted_old | jit_dispatches | reach_refusals |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| main | colocated | 0 | baseline | 800.08 | 803.90 | - | 3 | 0 | 0 | 0 | {} | 484.22 | 484.22 | 484.22 | 39.48 | 39.48 | True | True | True | True | True | 13 | 1 |
| main | colocated | 0 | baseline_informed | 801.39 | 803.90 | - | 3 | 0 | 0 | 0 | {} | 484.22 | 484.22 | 484.22 | 39.58 | 39.58 | - | - | - | True | True | 13 | 1 |
| main | colocated | 0 | baseline_legacy | 803.90 | 803.90 | True | 3 | 0 | 0 | 0 | {} | 484.22 | 484.22 | 484.22 | 39.77 | 39.77 | - | - | - | True | True | 0 | 2 |
| main | colocated | 0 | baseline_reorder | 924.57 | 809.30 | - | 4 | 5 | 7 | 26.40 | {"(17)": 1} | 484.22 | 484.22 | 484.22 | 47.63 | 47.63 | False | False | True | True | True | 12 | 1 |
| main | colocated | 0 | baseline_reorder_legacy | 809.30 | 809.30 | True | 3 | 1 | 2 | 5.40 | {} | 484.22 | 484.22 | 484.22 | 40.17 | 40.17 | - | - | - | True | True | 0 | 2 |
| main | colocated | 0 | baseline_reserve | 799.11 | 803.90 | - | 3 | 0 | 0 | 0 | {} | 484.22 | 484.22 | 484.22 | 39.41 | 39.41 | True | True | True | True | True | 13 | 1 |
| main | colocated | 1 | baseline | 1195.13 | 1113.94 | - | 7 | 0 | 0 | 0 | {"(17)": 1, "(18)": 1} | 575.62 | 575.62 | 575.62 | 51.84 | 51.84 | False | False | True | False | False | 9 | 0 |
| main | colocated | 1 | baseline_informed | 1123.89 | 1113.94 | - | 6 | 0 | 0 | 0 | {"(17)": 1, "(18)": 1} | 575.62 | 575.62 | 575.62 | 48.78 | 48.78 | - | - | - | False | False | 9 | 0 |
| main | colocated | 1 | baseline_legacy | 1113.94 | 1113.94 | True | 6 | 0 | 0 | 0 | {"(17)": 2, "(18)": 1} | 575.62 | 575.62 | 575.62 | 48.33 | 48.33 | - | - | - | False | False | 0 | 1 |
| main | colocated | 1 | baseline_reorder | 1206.16 | 1119.34 | - | 7 | 2 | 4 | 10.80 | {"(17)": 2, "(18)": 1} | 575.62 | 575.62 | 575.62 | 52.28 | 52.28 | False | False | True | False | False | 9 | 0 |
| main | colocated | 1 | baseline_reorder_legacy | 1119.34 | 1119.34 | True | 6 | 1 | 2 | 5.40 | {"(17)": 1, "(18)": 1} | 575.62 | 575.62 | 575.62 | 48.58 | 48.58 | - | - | - | False | False | 0 | 1 |
| main | colocated | 1 | baseline_reserve | 1194.80 | 1113.94 | - | 7 | 0 | 0 | 0 | {"(17)": 1, "(18)": 1} | 575.62 | 575.62 | 575.62 | 51.82 | 51.82 | False | False | True | False | False | 9 | 0 |
| main | colocated | 2 | baseline | 1281.93 | 1339.53 | - | 8 | 0 | 0 | 0 | {"(17)": 1} | 608.32 | 608.32 | 608.32 | 52.55 | 52.55 | False | False | True | True | True | 9 | 4 |
| main | colocated | 2 | baseline_informed | 1281.51 | 1339.53 | - | 8 | 0 | 0 | 0 | {} | 608.32 | 608.32 | 608.32 | 52.53 | 52.53 | - | - | - | True | True | 9 | 5 |
| main | colocated | 2 | baseline_legacy | 1339.53 | 1339.53 | True | 9 | 0 | 0 | 0 | {} | 608.32 | 608.32 | 608.32 | 54.59 | 54.59 | - | - | - | True | True | 0 | 5 |
| main | colocated | 2 | baseline_reorder | 1382.76 | 1345.04 | - | 9 | 4 | 8 | 21.60 | {"(18)": 1} | 608.32 | 608.32 | 608.32 | 56.01 | 56.01 | False | True | True | True | True | 9 | 4 |
| main | colocated | 2 | baseline_reorder_legacy | 1345.04 | 1345.04 | True | 9 | 1 | 2 | 5.40 | {} | 608.32 | 608.32 | 608.32 | 54.77 | 54.77 | - | - | - | True | True | 0 | 5 |
| main | colocated | 2 | baseline_reserve | 1279.57 | 1339.53 | - | 8 | 0 | 0 | 0 | {} | 608.32 | 608.32 | 608.32 | 52.46 | 52.46 | True | True | True | True | True | 9 | 5 |
| main | separated_1hub | 0 | baseline | 1164 | 1115.80 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 840.75 | 539.44 | 840.75 | 27.77 | 53.66 | False | False | True | False | False | 12 | 1 |
| main | separated_1hub | 0 | baseline_informed | 1170.15 | 1115.80 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 840.75 | 539.44 | 840.75 | 28.15 | 53.90 | - | - | - | False | False | 12 | 2 |
| main | separated_1hub | 0 | baseline_legacy | 1115.80 | 1115.80 | True | 6 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 840.75 | 539.44 | 840.75 | 24.65 | 51.65 | - | - | - | False | False | 0 | 2 |
| main | separated_1hub | 0 | baseline_reorder | 1045.53 | 982.46 | - | 5 | 7 | 11 | 37.20 | {"(17)": 2, "(18)": 1} | 539.44 | 539.44 | 840.75 | 48.41 | 48.41 | False | False | True | False | False | 12 | 1 |
| main | separated_1hub | 0 | baseline_reorder_legacy | 982.46 | 982.46 | True | 4 | 6 | 11 | 32.20 | {"(17)": 2, "(18)": 1} | 539.44 | 539.44 | 840.75 | 45.09 | 45.09 | - | - | - | False | False | 0 | 2 |
| main | separated_1hub | 0 | baseline_reserve | 1162.50 | 1115.80 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 840.75 | 539.44 | 840.75 | 27.68 | 53.60 | False | False | True | False | False | 12 | 2 |
| main | separated_1hub | 1 | baseline | 1302.10 | 1326.50 | - | 8 | 0 | 0 | 0 | {"(17)": 2, "(18)": 1} | 722 | 627.02 | 722 | 44.55 | 51.85 | False | False | True | False | False | 9 | 0 |
| main | separated_1hub | 1 | baseline_informed | 1233.45 | 1326.50 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1, "(9)": 1} | 722 | 627.02 | 722 | 41.46 | 49.17 | - | - | - | False | False | 9 | 0 |
| main | separated_1hub | 1 | baseline_legacy | 1326.50 | 1326.50 | True | 8 | 0 | 0 | 0 | {"(17)": 2, "(18)": 1} | 722 | 627.02 | 722 | 45.57 | 52.73 | - | - | - | False | False | 0 | 1 |
| main | separated_1hub | 1 | baseline_reorder | 1092.72 | 1091.37 | - | 5 | 5 | 11 | 27.20 | {"(17)": 2, "(18)": 1} | 627.02 | 627.02 | 722 | 42.62 | 42.62 | False | False | True | False | False | 9 | 0 |
| main | separated_1hub | 1 | baseline_reorder_legacy | 1091.37 | 1091.37 | True | 5 | 6 | 11 | 32.20 | {"(17)": 2, "(18)": 1} | 627.02 | 627.02 | 722 | 42.55 | 42.55 | - | - | - | False | False | 0 | 1 |
| main | separated_1hub | 1 | baseline_reserve | 1302.10 | 1326.50 | - | 8 | 0 | 0 | 0 | {"(17)": 2, "(18)": 1} | 722 | 627.02 | 722 | 44.55 | 51.85 | False | False | True | False | False | 9 | 0 |
| main | separated_1hub | 2 | baseline | 1720.60 | 1531.05 | - | 13 | 0 | 0 | 0 | {"(17)": 1} | 1042.55 | 667.97 | 1042.55 | 39.41 | 61.18 | False | False | True | False | False | 9 | 4 |
| main | separated_1hub | 2 | baseline_informed | 1633.05 | 1531.05 | - | 12 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 1042.55 | 667.97 | 1042.55 | 36.16 | 59.10 | - | - | - | False | False | 9 | 4 |
| main | separated_1hub | 2 | baseline_legacy | 1531.05 | 1531.05 | True | 11 | 0 | 0 | 0 | {"(17)": 2} | 1042.55 | 667.97 | 1042.55 | 31.91 | 56.37 | - | - | - | False | False | 0 | 5 |
| main | separated_1hub | 2 | baseline_reorder | 1414.51 | 1555.52 | - | 9 | 5 | 10 | 27 | {} | 667.97 | 667.97 | 1042.55 | 52.78 | 52.78 | True | True | True | False | False | 9 | 4 |
| main | separated_1hub | 2 | baseline_reorder_legacy | 1555.52 | 1555.52 | True | 11 | 4 | 9 | 21.80 | {"(17)": 2, "(18)": 1} | 667.97 | 667.97 | 1042.55 | 57.06 | 57.06 | - | - | - | False | False | 0 | 5 |
| main | separated_1hub | 2 | baseline_reserve | 1719.10 | 1531.05 | - | 13 | 0 | 0 | 0 | {"(17)": 1} | 1042.55 | 667.97 | 1042.55 | 39.35 | 61.14 | False | False | True | False | False | 9 | 4 |
| main | separated_2hubs | 0 | baseline | 1204 | 1155.80 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 880.75 | 583.14 | 880.75 | 26.85 | 51.57 | False | False | True | False | False | 12 | 1 |
| main | separated_2hubs | 0 | baseline_informed | 1210.15 | 1155.80 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 880.75 | 583.14 | 880.75 | 27.22 | 51.81 | - | - | - | False | False | 12 | 2 |
| main | separated_2hubs | 0 | baseline_legacy | 1155.80 | 1155.80 | True | 6 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 880.75 | 583.14 | 880.75 | 23.80 | 49.55 | - | - | - | False | False | 0 | 2 |
| main | separated_2hubs | 0 | baseline_reorder | 1012.22 | 942.77 | - | 4 | 10 | 14 | 52.80 | {"(17)": 2, "(18)": 1} | 583.14 | 583.14 | 880.75 | 42.39 | 42.39 | False | False | True | False | False | 12 | 1 |
| main | separated_2hubs | 0 | baseline_reorder_legacy | 942.77 | 942.77 | True | 3 | 8 | 13 | 42.60 | {"(17)": 2, "(18)": 1} | 583.14 | 583.14 | 880.75 | 38.15 | 38.15 | - | - | - | False | False | 0 | 2 |
| main | separated_2hubs | 0 | baseline_reserve | 1202.50 | 1155.80 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 880.75 | 583.14 | 880.75 | 26.76 | 51.51 | False | False | True | False | False | 12 | 2 |
| main | separated_2hubs | 1 | baseline | 1342.10 | 1366.50 | - | 8 | 0 | 0 | 0 | {"(17)": 2, "(18)": 1} | 762 | 668.48 | 762 | 43.22 | 50.19 | False | False | True | False | False | 9 | 0 |
| main | separated_2hubs | 1 | baseline_informed | 1273.45 | 1366.50 | - | 7 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1, "(9)": 1} | 762 | 668.48 | 762 | 40.16 | 47.51 | - | - | - | False | False | 9 | 0 |
| main | separated_2hubs | 1 | baseline_legacy | 1366.50 | 1366.50 | True | 8 | 0 | 0 | 0 | {"(17)": 2, "(18)": 1} | 762 | 668.48 | 762 | 44.24 | 51.08 | - | - | - | False | False | 0 | 1 |
| main | separated_2hubs | 1 | baseline_reorder | 1137.72 | 1043.77 | - | 5 | 6 | 11 | 32.20 | {"(17)": 2, "(18)": 1} | 668.48 | 668.48 | 762 | 41.24 | 41.24 | False | False | True | False | False | 9 | 0 |
| main | separated_2hubs | 1 | baseline_reorder_legacy | 1043.77 | 1043.77 | True | 4 | 6 | 10 | 32 | {"(17)": 2, "(18)": 1} | 668.48 | 668.48 | 762 | 35.96 | 35.96 | - | - | - | False | False | 0 | 1 |
| main | separated_2hubs | 1 | baseline_reserve | 1342.10 | 1366.50 | - | 8 | 0 | 0 | 0 | {"(17)": 2, "(18)": 1} | 762 | 668.48 | 762 | 43.22 | 50.19 | False | False | True | False | False | 9 | 0 |
| main | separated_2hubs | 2 | baseline | 1760.60 | 1571.05 | - | 13 | 0 | 0 | 0 | {"(17)": 1} | 1082.55 | 710.23 | 1082.55 | 38.51 | 59.66 | False | False | True | False | False | 9 | 4 |
| main | separated_2hubs | 2 | baseline_informed | 1673.05 | 1571.05 | - | 12 | 0 | 0 | 0 | {"(17)": 3, "(18)": 1} | 1082.55 | 710.23 | 1082.55 | 35.29 | 57.55 | - | - | - | False | False | 9 | 4 |
| main | separated_2hubs | 2 | baseline_legacy | 1571.05 | 1571.05 | True | 11 | 0 | 0 | 0 | {"(17)": 2} | 1082.55 | 710.23 | 1082.55 | 31.09 | 54.79 | - | - | - | False | False | 0 | 5 |
| main | separated_2hubs | 2 | baseline_reorder | 1375.37 | 1445.20 | - | 8 | 7 | 14 | 37.80 | {"(17)": 1} | 710.23 | 710.23 | 1082.55 | 48.36 | 48.36 | False | False | True | False | False | 10 | 4 |
| main | separated_2hubs | 2 | baseline_reorder_legacy | 1445.20 | 1445.20 | True | 9 | 6 | 10 | 32 | {"(17)": 2, "(18)": 1} | 710.23 | 710.23 | 1082.55 | 50.86 | 50.86 | - | - | - | False | False | 0 | 5 |
| main | separated_2hubs | 2 | baseline_reserve | 1759.10 | 1571.05 | - | 13 | 0 | 0 | 0 | {"(17)": 1} | 1082.55 | 710.23 | 1082.55 | 38.46 | 59.63 | False | False | True | False | False | 9 | 4 |
| relaxed_end_targets | colocated | 0 | baseline | 800.08 | 803.90 | - | 3 | 0 | 0 | 0 | {} | 481.50 | 481.50 | 481.50 | 39.82 | 39.82 | True | True | True | True | True | 13 | 1 |
| relaxed_end_targets | colocated | 0 | baseline_informed | 801.39 | 803.90 | - | 3 | 0 | 0 | 0 | {} | 481.50 | 481.50 | 481.50 | 39.92 | 39.92 | - | - | - | True | True | 13 | 1 |
| relaxed_end_targets | colocated | 0 | baseline_legacy | 803.90 | 803.90 | True | 3 | 0 | 0 | 0 | {} | 481.50 | 481.50 | 481.50 | 40.10 | 40.10 | - | - | - | True | True | 0 | 2 |
| relaxed_end_targets | colocated | 0 | baseline_reorder | 924.57 | 809.30 | - | 4 | 5 | 7 | 26.40 | {} | 481.50 | 481.50 | 481.50 | 47.92 | 47.92 | True | True | True | True | True | 12 | 1 |
| relaxed_end_targets | colocated | 0 | baseline_reorder_legacy | 809.30 | 809.30 | True | 3 | 1 | 2 | 5.40 | {} | 481.50 | 481.50 | 481.50 | 40.50 | 40.50 | - | - | - | True | True | 0 | 2 |
| relaxed_end_targets | colocated | 0 | baseline_reserve | 799.11 | 803.90 | - | 3 | 0 | 0 | 0 | {} | 481.50 | 481.50 | 481.50 | 39.75 | 39.75 | True | True | True | True | True | 13 | 1 |
| relaxed_end_targets | separated_1hub | 0 | baseline | 1164 | 1115.80 | - | 7 | 0 | 0 | 0 | {} | 525.25 | 525.25 | 525.25 | 54.88 | 54.88 | True | True | True | True | True | 12 | 1 |
| relaxed_end_targets | separated_1hub | 0 | baseline_informed | 1170.15 | 1115.80 | - | 7 | 0 | 0 | 0 | {} | 525.25 | 525.25 | 525.25 | 55.11 | 55.11 | - | - | - | True | True | 12 | 2 |
| relaxed_end_targets | separated_1hub | 0 | baseline_legacy | 1115.80 | 1115.80 | True | 6 | 0 | 0 | 0 | {} | 525.25 | 525.25 | 525.25 | 52.93 | 52.93 | - | - | - | True | True | 0 | 2 |
| relaxed_end_targets | separated_1hub | 0 | baseline_reorder | 1045.53 | 982.46 | - | 5 | 7 | 11 | 37.20 | {} | 525.25 | 525.25 | 525.25 | 49.76 | 49.76 | True | True | True | True | True | 12 | 1 |
| relaxed_end_targets | separated_1hub | 0 | baseline_reorder_legacy | 982.46 | 982.46 | True | 4 | 6 | 11 | 32.20 | {} | 525.25 | 525.25 | 525.25 | 46.54 | 46.54 | - | - | - | True | True | 0 | 2 |
| relaxed_end_targets | separated_1hub | 0 | baseline_reserve | 1162.50 | 1115.80 | - | 7 | 0 | 0 | 0 | {} | 525.25 | 525.25 | 525.25 | 54.82 | 54.82 | True | True | True | True | True | 12 | 2 |

## Figures

- `fig_cost_by_layout_v2.png`

## Anomalies

- none

## Interpretation

1. **Byte-identity holds** (old `n_arcs` on all 11 instances; `baseline_legacy` and `baseline_reorder_legacy` reproduce the old NONE / REORDER_POINT rows to 1e-6).
2. **The fixed baseline is worse on E3's swap-scarce instances.** With `sum B = 9`, `sum C = 9` and q0 ~ U{0.3L..0.6L} these are the E4 stressed regime's conditions: NONE 1258.2 -> 1307.8 (+3.9 %; unserved 7.56 -> 8.22), REORDER_POINT 1148.3 -> 1176.8 (+2.5 %; 6.00 -> 6.22). Per layout, NONE is unchanged in the mean on the co-located layout (1085.8 -> 1092.4; seed 1 worse, seed 2 better) and +71 on both separated layouts (1324.5 -> 1395.6, 1364.5 -> 1435.6; one more unserved order per seed on average): with swap-only sites holding 2 spares each and no charging on site, the dead-zone rule sends low-charge bikes to sites that are already empty. REORDER_POINT v2 is better than its legacy counterpart on the 1-hub layout (1209.8 -> 1184.3) and worse on the 2-hub layout (1143.9 -> 1175.1) and on the co-located layout (1091.2 -> 1171.2, where the new policy's extra swaps trigger 3.7 shuttle shipments per run instead of 1.0, C_reb 5.4 -> 19.6). `baseline_reserve` is within 1 unit of NONE (the late-threshold window suppresses 0-1 trips) and `baseline_informed` is 20-50 units better than NONE on every layout (the stock-aware site choice is the one variant that helps here: 1092 -> 1069, 1396 -> 1346, 1436 -> 1386).
3. **Headline gaps (ILP of the same transfer switch).** `no_transfers` ILP vs NONE: 38.2 % -> 40.5 % of the baseline cost; transfers-free ILP vs REORDER_POINT: 45.9 % -> 48.0 %. The E3 headline itself (ILP vs ILP: transfers worth 0 when sites can charge and 255-257 when they cannot; separation costs +55 / +98) does not involve the baseline and is unchanged.
4. **MIP start.** Under the written model only co-located seed 0 accepts the new NONE start (1 / 9; the old baseline was accepted on co-located seeds 0 and 2) and only separated-1hub seed 2 accepts the new REORDER_POINT start (1 / 9); every other run reports (17) (a swap site ending without its R_end = 1 full spare) and usually (18). Removing (18) alone adds one REORDER_POINT acceptance (co-located seed 2); under the fully relaxed end targets (rho = 0, R_end = 0) all 18 starts are accepted (Gurobi fix-and-solve: 6.5 s build, 10 s of fixed solves per instance for the three certified variants). On the two saved relaxed-end-target instances (seed 0) the NONE start is accepted directly: co-located 800.1 (old 803.9) vs ILP 481.5, separated-1hub 1164.0 (old 1115.8) vs 525.25.
5. The baseline rows remain context only, as in the original E3 report: on the separated layouts the policy's point is infeasible for the written model because of (17)/(18), and its gap mixes policy quality with the end-target infeasibility; the fully relaxed certificate shows that the schedules are otherwise feasible ((5)-(16), (20)-(22) hold by construction).

