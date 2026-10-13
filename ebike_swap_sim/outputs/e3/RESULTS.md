# E3 -- value of battery transfers and of separating charging hubs from swap sites

Family `large` ({'n_bikes': 10, 'n_orders': 30, 'H': 24, 'L': 12}), seeds [0, 1, 2]; bike q0 ~ U{ceil(0.3L)..floor(0.6L)}; equal totals sum B = 9, sum C = 9, grid group 8 kW (6 kW in the 18-20 h peak) in every layout; hubs hold 3 of the spares. Shuttles every 6 slots from t = 2, U_e = 6, f_e = 5.0, v_reb = 0.2. Pruning {'tau_max': 4, 'start_slack': 6, 'reachable': False}; Gurobi Threads 4, TimeLimit 300 s, OutputFlag 0. Total wall time 29.3 min (single process).

## Seed means per layout, method and transfer switch

| layout | method | switch | total | C_travel | C_elec | unserved | response | lateness | C_reb | served_share | n_unserved | mean_lateness_h | n_late | n_swaps | transfers_used | batteries_moved | stockout_slots_total | m_t_max | peak_kw_group_max | end_full_total | runtime_s | gap | n_seeds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | ilp | no_transfers | 556.052 | 105.200 | 2.519 | 66.667 | 250.667 | 26 | 0 | 0.978 | 0.667 | 0.037 | 7 | 7 | 0 | 0 | 15.667 | 0 | 1.778 | 5 | 22.082 | 0 | 3 |
| colocated | ilp | transfers free | 556.052 | 105.200 | 2.519 | 66.667 | 250.667 | 26 | 0 | 0.978 | 0.667 | 0.037 | 7.333 | 7 | 0 | 0 | 13.667 | 0 | 1.778 | 5 | 36.142 | 0 | 3 |
| colocated | baseline | transfer_rule=NONE | 1085.789 | 102.900 | 7.889 | 600 | 220 | 50 | 0 | 0.800 | 6 | 0.088 | 10.333 | 8.667 | 0 | 0 | 15.333 | 0 | 4.444 | 5.333 | 0.002 | - | 3 |
| colocated | baseline | transfer_rule=REORDER_POINT | 1091.226 | 102.900 | 7.926 | 600 | 220 | 50 | 5.400 | 0.800 | 6 | 0.088 | 10.333 | 9.667 | 1 | 2 | 12.667 | 2 | 4.444 | 4.333 | 0.002 | - | 3 |
| separated_1hub | ilp | no_transfers | 868.433 | 90.100 | 0 | 366.667 | 231.333 | 35.333 | 0 | 0.878 | 3.667 | 0.055 | 8 | 3 | 0 | 0 | 0 | 0 | 0 | 6 | 33.407 | 0 | 3 |
| separated_1hub | ilp | transfers free | 611.474 | 106.600 | 2.074 | 66.667 | 251.667 | 26.667 | 12.800 | 0.978 | 0.667 | 0.038 | 7 | 6.333 | 2.333 | 5.667 | 8.667 | 3 | 1.556 | 5 | 185.897 | 0.006 | 3 |
| separated_1hub | baseline | transfer_rule=NONE | 1324.450 | 95.450 | 0 | 833.333 | 200 | 50.667 | 0 | 0.722 | 8.333 | 0.097 | 8.667 | 5 | 0 | 0 | 27.333 | 0 | 0 | 4 | 0.002 | - | 3 |
| separated_1hub | baseline | transfer_rule=REORDER_POINT | 1209.781 | 101.900 | 3.815 | 666.667 | 214.333 | 49.333 | 28.733 | 0.778 | 6.667 | 0.087 | 10 | 7.667 | 5.333 | 10.333 | 21 | 5.667 | 3.556 | 2 | 0.002 | - | 3 |
| separated_2hubs | ilp | no_transfers | 908.433 | 90.100 | 0 | 366.667 | 231.333 | 35.333 | 0 | 0.878 | 3.667 | 0.055 | 8.333 | 3 | 0 | 0 | 0 | 0 | 0 | 6 | 34.193 | 0.000 | 3 |
| separated_2hubs | ilp | transfers free | 653.950 | 104.150 | 2 | 66.667 | 251.333 | 28.667 | 16.133 | 0.978 | 0.667 | 0.041 | 7.667 | 6.333 | 3 | 5.667 | 16.333 | 3 | 1.556 | 5 | 200.100 | 0.007 | 3 |
| separated_2hubs | baseline | transfer_rule=NONE | 1364.450 | 95.450 | 0 | 833.333 | 200 | 50.667 | 0 | 0.722 | 8.333 | 0.097 | 8.667 | 5 | 0 | 0 | 27.333 | 0 | 0 | 4 | 0.002 | - | 3 |
| separated_2hubs | baseline | transfer_rule=REORDER_POINT | 1143.913 | 106.750 | 3.630 | 533.333 | 227.667 | 52 | 35.533 | 0.822 | 5.333 | 0.088 | 11.333 | 7.667 | 6.667 | 11 | 23 | 6 | 3.111 | 2 | 0.002 | - | 3 |

`stockout_slots_total` = slots with `n_jLt = 0` summed over swap sites; `m_t_max` = max in-transit batteries (24); `peak_kw_group_max` = max over grid groups of the peak charging load (21); `end_full_total` = sum_j n_jLH ((18) requires >= rho sum B = 4.5).

## Per-run table (ILP)

| layout | seed | switch | status | total | C_travel | C_elec | unserved | response | lateness | C_reb | served_share | n_late | transfers_used | batteries_moved | stockout_slots | m_t_max | peak_kw_group | end_full_total | n_binaries | n_rows | runtime_s | gap | mip_start_accepted | check_ok | identity_24_ok | baseline_total_same_switch | baseline_gap_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | 0 | transfers free | OPTIMAL | 484.217 | 98.550 | 2.667 | 0 | 254 | 24 | 0 | 1 | 7 | 0 | 0 | {"S1": 9, "S2": 0, "S3": 11} | 0 | {"sites": 2.0} | 5 | 1491087 | 80402 | 16.197 | 0 | True | True | True | 809.300 | 67.136 |
| colocated | 0 | no_transfers | OPTIMAL | 484.217 | 98.550 | 2.667 | 0 | 254 | 24 | 0 | 1 | 6 | 0 | 0 | {"S1": 10, "S2": 0, "S3": 13} | 0 | {"sites": 2.0} | 5 | 1491087 | 80402 | 14.509 | 0 | True | True | True | 803.900 | 66.021 |
| separated_1hub | 0 | transfers free | TIME_LIMIT | 539.439 | 101.550 | 1.889 | 0 | 254 | 26 | 11 | 1 | 6 | 2 | 5 | {"S1": 0, "S2": 0, "S3": 2} | 3 | {"hub1": 1.3333333333333335} | 5 | 1622318 | 83481 | 200.096 | 0.010 | False | True | True | 982.461 | 82.126 |
| separated_1hub | 0 | no_transfers | OPTIMAL | 840.750 | 87.750 | 0 | 300 | 250 | 58 | 0 | 0.900 | 11 | 0 | 0 | {"S1": 0, "S2": 0, "S3": 0} | 0 | {"hub1": 0.0} | 6 | 1622318 | 83481 | 46.606 | 0 | False | True | True | 1115.800 | 32.715 |
| separated_2hubs | 0 | transfers free | TIME_LIMIT | 583.139 | 98.250 | 1.889 | 0 | 256 | 26 | 16 | 1 | 6 | 3 | 5 | {"S1": 2, "S2": 0, "S3": 4} | 2 | {"hubs": 1.3333333333333335} | 5 | 1758813 | 87520 | 200.141 | 0.010 | False | True | True | 942.772 | 61.672 |
| separated_2hubs | 0 | no_transfers | OPTIMAL | 880.750 | 87.750 | 0 | 300 | 250 | 58 | 0 | 0.900 | 11 | 0 | 0 | {"S1": 0, "S2": 0, "S3": 0} | 0 | {"hubs": 0.0} | 6 | 1758813 | 87520 | 43.291 | 0.000 | False | True | True | 1155.800 | 31.229 |
| colocated | 1 | transfers free | OPTIMAL | 575.617 | 103.950 | 1.667 | 100 | 245 | 20 | 0 | 0.967 | 7 | 0 | 0 | {"S1": 0, "S2": 8, "S3": 0} | 0 | {"sites": 0.6666666666666667} | 5 | 1523965 | 80394 | 67.177 | 0 | False | True | True | 1119.339 | 94.459 |
| colocated | 1 | no_transfers | OPTIMAL | 575.617 | 103.950 | 1.667 | 100 | 245 | 20 | 0 | 0.967 | 7 | 0 | 0 | {"S1": 0, "S2": 5, "S3": 0} | 0 | {"sites": 1.3333333333333335} | 5 | 1523965 | 80394 | 24.429 | 0 | False | True | True | 1113.939 | 93.521 |
| separated_1hub | 1 | transfers free | TIME_LIMIT | 627.017 | 103.350 | 1.667 | 100 | 246 | 20 | 11 | 0.967 | 7 | 2 | 5 | {"S1": 0, "S2": 1, "S3": 0} | 3 | {"hub1": 1.3333333333333335} | 5 | 1655878 | 83481 | 200.099 | 0.009 | False | True | True | 1091.367 | 74.057 |
| separated_1hub | 1 | no_transfers | OPTIMAL | 722 | 99 | 0 | 200 | 248 | 30 | 0 | 0.933 | 10 | 0 | 0 | {"S1": 0, "S2": 0, "S3": 0} | 0 | {"hub1": 0.0} | 6 | 1655878 | 83481 | 24.518 | 0 | False | True | True | 1326.500 | 83.726 |
| separated_2hubs | 1 | transfers free | TIME_LIMIT | 668.478 | 101.100 | 0.778 | 100 | 245 | 26 | 10.600 | 0.967 | 9 | 2 | 3 | {"S1": 0, "S2": 8, "S3": 0} | 3 | {"hubs": 0.6666666666666667} | 5 | 1792871 | 87512 | 200.105 | 0.008 | False | True | True | 1043.767 | 56.141 |
| separated_2hubs | 1 | no_transfers | OPTIMAL | 762 | 99 | 0 | 200 | 248 | 30 | 0 | 0.933 | 11 | 0 | 0 | {"S1": 0, "S2": 0, "S3": 0} | 0 | {"hubs": 0.0} | 6 | 1792871 | 87512 | 26.308 | 0 | False | True | True | 1366.500 | 79.331 |
| colocated | 2 | transfers free | OPTIMAL | 608.322 | 113.100 | 3.222 | 100 | 253 | 34 | 0 | 0.967 | 8 | 0 | 0 | {"S1": 13, "S2": 0, "S3": 0} | 0 | {"sites": 2.666666666666667} | 5 | 1434695 | 80394 | 25.053 | 0 | True | True | True | 1345.039 | 121.106 |
| colocated | 2 | no_transfers | OPTIMAL | 608.322 | 113.100 | 3.222 | 100 | 253 | 34 | 0 | 0.967 | 8 | 0 | 0 | {"S1": 19, "S2": 0, "S3": 0} | 0 | {"sites": 2.0} | 5 | 1434695 | 80394 | 27.306 | 0 | True | True | True | 1339.528 | 120.200 |
| separated_1hub | 2 | transfers free | OPTIMAL | 667.967 | 114.900 | 2.667 | 100 | 255 | 34 | 16.400 | 0.967 | 8 | 3 | 7 | {"S1": 3, "S2": 0, "S3": 20} | 3 | {"hub1": 2.0} | 5 | 1563758 | 83481 | 157.495 | 0 | False | True | True | 1555.517 | 132.873 |
| separated_1hub | 2 | no_transfers | OPTIMAL | 1042.550 | 83.550 | 0 | 600 | 196 | 18 | 0 | 0.800 | 3 | 0 | 0 | {"S1": 0, "S2": 0, "S3": 0} | 0 | {"hub1": 0.0} | 6 | 1563758 | 83481 | 29.098 | 0 | False | True | True | 1531.050 | 46.856 |
| separated_2hubs | 2 | transfers free | TIME_LIMIT | 710.233 | 113.100 | 3.333 | 100 | 253 | 34 | 21.800 | 0.967 | 8 | 4 | 9 | {"S1": 18, "S2": 0, "S3": 17} | 4 | {"hubs": 2.666666666666667} | 5 | 1697761 | 87512 | 200.056 | 0.004 | False | True | True | 1445.200 | 103.482 |
| separated_2hubs | 2 | no_transfers | OPTIMAL | 1082.550 | 83.550 | 0 | 600 | 196 | 18 | 0 | 0.800 | 3 | 0 | 0 | {"S1": 0, "S2": 0, "S3": 0} | 0 | {"hubs": 0.0} | 6 | 1697761 | 87512 | 32.981 | 0 | False | True | True | 1571.050 | 45.125 |

## Per-run table (baseline)

| layout | seed | switch | total | C_travel | C_elec | unserved | response | lateness | C_reb | served_share | n_late | transfers_used | batteries_moved | stockout_slots | m_t_max | peak_kw_group | end_full_total | reported_families | check_ok_modulo_report_only | identity_24_ok | runtime_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | 0 | transfer_rule=NONE | 803.900 | 114.900 | 10 | 300 | 238 | 36 | 0 | 0.900 | 10 | 0 | 0 | {"S1": 8, "S2": 7, "S3": 0} | 0 | {"sites": 5.333333333333334} | 6 | {} | True | True | 0.002 |
| colocated | 0 | transfer_rule=REORDER_POINT | 809.300 | 114.900 | 10 | 300 | 238 | 36 | 5.400 | 0.900 | 10 | 1 | 2 | {"S1": 8, "S2": 7, "S3": 0} | 2 | {"sites": 5.333333333333334} | 6 | {} | True | True | 0.002 |
| separated_1hub | 0 | transfer_rule=NONE | 1115.800 | 106.800 | 0 | 600 | 218 | 46 | 0 | 0.800 | 9 | 0 | 0 | {"S1": 14, "S2": 11, "S3": 13} | 0 | {"hub1": 0.0} | 3 | {"(17)": 3, "(18)": 1} | True | True | 0.002 |
| separated_1hub | 0 | transfer_rule=REORDER_POINT | 982.461 | 117.150 | 6.111 | 400 | 236 | 46 | 32.200 | 0.867 | 10 | 6 | 11 | {"S1": 2, "S2": 11, "S3": 13} | 6 | {"hub1": 5.333333333333334} | 3 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| separated_2hubs | 0 | transfer_rule=NONE | 1155.800 | 106.800 | 0 | 600 | 218 | 46 | 0 | 0.800 | 9 | 0 | 0 | {"S1": 14, "S2": 11, "S3": 13} | 0 | {"hubs": 0.0} | 3 | {"(17)": 3, "(18)": 1} | True | True | 0.002 |
| separated_2hubs | 0 | transfer_rule=REORDER_POINT | 942.772 | 121.950 | 5.222 | 300 | 244 | 44 | 42.600 | 0.900 | 11 | 8 | 13 | {"S1": 10, "S2": 10, "S3": 13} | 7 | {"hubs": 3.333333333333334} | 2 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| colocated | 1 | transfer_rule=NONE | 1113.939 | 100.050 | 6.889 | 600 | 232 | 70 | 0 | 0.800 | 13 | 0 | 0 | {"S1": 6, "S2": 9, "S3": 0} | 0 | {"sites": 4.0} | 3 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| colocated | 1 | transfer_rule=REORDER_POINT | 1119.339 | 100.050 | 6.889 | 600 | 232 | 70 | 5.400 | 0.800 | 13 | 1 | 2 | {"S1": 0, "S2": 9, "S3": 0} | 2 | {"sites": 4.0} | 2 | {"(17)": 1, "(18)": 1} | True | True | 0.002 |
| separated_1hub | 1 | transfer_rule=NONE | 1326.500 | 94.500 | 0 | 800 | 215 | 72 | 0 | 0.733 | 11 | 0 | 0 | {"S1": 9, "S2": 14, "S3": 0} | 0 | {"hub1": 0.0} | 4 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| separated_1hub | 1 | transfer_rule=REORDER_POINT | 1091.367 | 103.500 | 2.667 | 500 | 240 | 68 | 32.200 | 0.833 | 14 | 6 | 11 | {"S1": 9, "S2": 10, "S3": 0} | 4 | {"hub1": 2.666666666666667} | 1 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| separated_2hubs | 1 | transfer_rule=NONE | 1366.500 | 94.500 | 0 | 800 | 215 | 72 | 0 | 0.733 | 11 | 0 | 0 | {"S1": 9, "S2": 14, "S3": 0} | 0 | {"hubs": 0.0} | 4 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| separated_2hubs | 1 | transfer_rule=REORDER_POINT | 1043.767 | 107.100 | 2.667 | 400 | 249 | 68 | 32 | 0.867 | 15 | 6 | 10 | {"S1": 9, "S2": 9, "S3": 0} | 4 | {"hubs": 2.666666666666667} | 2 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| colocated | 2 | transfer_rule=NONE | 1339.528 | 93.750 | 6.778 | 900 | 190 | 44 | 0 | 0.700 | 8 | 0 | 0 | {"S1": 9, "S2": 0, "S3": 7} | 0 | {"sites": 4.0} | 7 | {} | True | True | 0.002 |
| colocated | 2 | transfer_rule=REORDER_POINT | 1345.039 | 93.750 | 6.889 | 900 | 190 | 44 | 5.400 | 0.700 | 8 | 1 | 2 | {"S1": 7, "S2": 0, "S3": 7} | 2 | {"sites": 4.0} | 5 | {} | True | True | 0.002 |
| separated_1hub | 2 | transfer_rule=NONE | 1531.050 | 85.050 | 0 | 1100 | 167 | 34 | 0 | 0.633 | 6 | 0 | 0 | {"S1": 11, "S2": 0, "S3": 10} | 0 | {"hub1": 0.0} | 5 | {"(17)": 2} | True | True | 0.002 |
| separated_1hub | 2 | transfer_rule=REORDER_POINT | 1555.517 | 85.050 | 2.667 | 1100 | 167 | 34 | 21.800 | 0.633 | 6 | 4 | 9 | {"S1": 8, "S2": 0, "S3": 10} | 7 | {"hub1": 2.666666666666667} | 2 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |
| separated_2hubs | 2 | transfer_rule=NONE | 1571.050 | 85.050 | 0 | 1100 | 167 | 34 | 0 | 0.633 | 6 | 0 | 0 | {"S1": 11, "S2": 0, "S3": 10} | 0 | {"hubs": 0.0} | 5 | {"(17)": 2} | True | True | 0.002 |
| separated_2hubs | 2 | transfer_rule=REORDER_POINT | 1445.200 | 91.200 | 3 | 900 | 190 | 44 | 32 | 0.700 | 8 | 6 | 10 | {"S1": 9, "S2": 0, "S3": 9} | 7 | {"hubs": 3.333333333333334} | 2 | {"(17)": 2, "(18)": 1} | True | True | 0.002 |

## Figures

- `fig_cost_by_layout.png`
- `fig_cost_components.png`
- `fig_transfer_value.png`
- `fig_in_transit.png`
- `fig_full_stock_seed0.png`
- `fig_grid_load_seed0.png`

## Anomalies / checks

- separated_1hub seed 0 ilp transfers free: status TIME_LIMIT gap 0.0096087498326436
- separated_2hubs seed 0 ilp transfers free: status TIME_LIMIT gap 0.0096508359929495
- separated_1hub seed 1 ilp transfers free: status TIME_LIMIT gap 0.0085590494670522
- separated_2hubs seed 1 ilp transfers free: status TIME_LIMIT gap 0.0084603493841728
- separated_2hubs seed 2 ilp transfers free: status TIME_LIMIT gap 0.0036529466059657

## Headline comparison and interpretation

**Headline = ILP vs ILP** (layout x transfer switch, same instances, same end targets (17)-(18)).
The baseline rows are context only: on every separated run and on co-located seed 1 the baseline
violates (17) (swap sites end without a full spare) and (18), so its point is infeasible for the model,
its MIP start is rejected, and "baseline gap" mixes policy quality with an infeasibility.

| quantity (3-seed mean, toy units) | (a) co-located | (b) 1 hub | (c) 2 hubs |
|---|---|---|---|
| ILP total, transfers free | 556.05 | 611.47 | 653.95 |
| ILP total, h = z = 0 | 556.05 | 868.43 | 908.43 |
| value of transfers = cost(h = z = 0) - cost(free) | **0.0** (seeds 0/0/0) | **257.0** (301.3 / 95.0 / 374.6) | **254.5** (297.6 / 93.5 / 372.3) |
| cost of separation vs (a), transfers free | - | +55.4 (= 40 setup (27) + 15.4 operations) | +97.9 (= 80 setup + 17.9 operations) |
| operational cost (total - C_setup), transfers free | 451.05 | 466.47 (+3.4 %) | 468.95 (+4.0 %) |
| served share, transfers free / h = z = 0 | 0.978 / 0.978 | 0.978 / 0.878 | 0.978 / 0.878 |
| transfers used / batteries moved (free) | 0 / 0 | 2.3 / 5.7 | 3.0 / 5.7 |
| grid-group peak kW (limit 8, 6 in peak) | 1.78 | 1.56 | 1.56 |
| baseline NONE / REORDER_POINT total | 1085.8 / 1091.2 | 1324.5 / 1209.8 | 1364.5 / 1143.9 |

1. **Co-location dominates at equal totals.** With 9 spares, 9 chargers and the same 8/6 kW grid
   group in every layout, the co-located layout is cheapest on every seed; one hub costs +55 (+10 %
   of total, +3.4 % of operational cost) and two hubs +98. Net of the horizon-allocated hub cost
   (27) the separation penalty is only 11-22 units per seed, which is essentially the shuttle fixed
   charges f_e = 5 per used service plus v_reb (C_reb = 11.0-21.8); travel, response and lateness
   are within a few units of (a). The separation penalty is certified: the 1-hub bounds
   (obj * (1 - gap) = 534.3 / 621.6 / 668.0) exceed the co-located optimum on every seed.
2. **Transfers are worth nothing when sites can charge, and everything when they cannot.** In (a)
   the site <-> site shuttles are offered on every seed and never used (identical objectives, 0
   transfers). In (b)/(c) the switch h = z = 0 loses 3-6 orders per seed (unserved 300-600 at
   P_i = 100): with no chargers at the swap sites the six site spares (2 + 2 + 2) are the only
   swap supply, and (17) R_end_j = 1 freezes one of them per site, so at most 3 swaps are possible
   (n_swaps = 3 on every h = z = 0 run). Transfers restore service to exactly the co-located served
   share on every seed (0.978 both) with 2-4 services and 3-9 batteries moved.
3. **Caveat: in this 2 h window the value of transfers is a recovery-target effect, not a
   replenishment effect.** The side run `relaxed_end_targets/` (seed 0, R_end = 0, rho = 0) gives
   co-located 481.50 and separated-1-hub 525.25 with zero transfers, zero charging and all 30
   orders served; 525.25 - 481.50 = 43.75 = 40 hub setup + 3.75 extra travel. With the end targets
   on, (b) needs transfers (539.44, 2 services, 5 batteries) purely to end with one full spare at
   each swap-only site and >= rho * 9 = 5 full batteries in the network. The plan's expectation that
   "the ILP times shipments right before predicted stock-outs" holds in the trajectories
   (seed 0, (b): S3 hits n_jLt = 0 at t = 4 and the 3-battery shipment lands at t = 6; see
   `fig_full_stock_seed0.png`), but the within-horizon stock-out itself is avoidable without
   transfers once the end targets are dropped. A 4 h horizon (plan: H = 48, |I| = 40) is needed to
   see replenishment value; at H = 36 / 45 orders the probe solved co-located in 160-195 s per run
   and the separated layouts did not finish in 300 s, outside the 45 min budget.
4. **The grid-group limit never binds.** Peak charging load is 0.67-2.67 kW against 6-8 kW. With
   p_ch = eps / (eta Delta) = 0.667 kW per charger (L = 12) a battery needs up to 12 slots = 60 min
   to refill, few batteries return within 2 h, and the 9 hub chargers never have more than 4
   batteries to charge, so the plan's expected "limit binds at the hub during the peak, shifting
   charging earlier" does not occur at this size (the hub charges only after t = 13).
5. **Baseline.** The baseline-vs-ILP gap (66-133 % of the ILP cost) is almost entirely P_i: on (a)
   the mean difference 529.7 decomposes into unserved +533.3, response -30.7, lateness +24.0,
   electricity +5.4, travel -2.3; on (b) with REORDER_POINT the difference 598.3 is unserved +600,
   C_reb +15.9, response -37.3, lateness +22.7. REORDER_POINT helps the separated layouts on seeds
   0-1 (1-2 fewer unserved, -115 to -220) but uses 4-8 services and 9-13 batteries where the ILP
   uses 2-4 and 3-9, and on seed 2 it is worse than NONE on (b) (+24.5: same unserved count, extra
   C_reb). The baseline MIP start is accepted only on co-located seeds 0 and 2 (reported families
   {}); elsewhere it reports (17)/(18) and is rejected, as expected. A rho = 0 / R_end = 0
   comparison on seed 0 (`relaxed_end_targets/`) accepts the start on both layouts and leaves the
   gap at 67 % (a) and 87 % (b, REORDER_POINT), so the inflation by (17)/(18) is small: the
   baseline's loss is dispatch/threshold quality, i.e. unserved orders.
6. **Solver.** 1.43-1.79 M binaries, 80-88 k rows. Co-located and all h = z = 0 runs solve to
   optimality in 14-67 s; the separated runs with transfers are the hard ones: 5 of 6 hit the 200 s
   limit at gaps 0.37-0.97 % (the sixth, (b) seed 2, is optimal in 157 s). Those gaps (<= 6 units)
   are below every reported difference except the per-seed operational separation penalty on
   seed 1 (11 units, still above the 5.4-unit gap). Wall time 29.3 min for the 36 runs plus ~4 min
   for the side check, single process, Threads = 4, while two other experiments shared the machine.

**Instance choice.** The generator defaults (12 spares, q0 ~ U{0.4L..L}) were probed first and are
degenerate for this question: 12 initially full spares cover every swap of a 2 h window, the ILP
never charges or transfers, and the layouts differ only by (27) (+40 per hub). The family used is
`large` (10 bikes, 30 orders, H = 24, L = 12, Delta = 5 min) with 9 spares (3+3+3 / 2+2+2 + hub 3 /
2+2+2 + hubs 2+1), 9 chargers (3+3+3 / hub 9 / hubs 5+4), q0 ~ U{4..7}, seeds 0-2; the H = 36 /
45-order variant was too slow (above). All 36 schedules pass `evaluate.check` with zero violations
(ILP) or only the report-only families (baseline), identity (24) holds everywhere, and
`obj == cost` for every ILP run.

