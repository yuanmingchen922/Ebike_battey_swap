# X2 (round 5) -- transfers and separation (usd4h, ebaas, seeds 0-4)

Gurobi Threads 3, Seed 0, TimeLimit 300 s, aggregated ILP (O1). Gap = 100 (baseline - ILP) / baseline. best_rule = min over r2, r5_range, r5_transfer, r5 per instance. Headline = relaxed control (rho 0, R_end 0); written = rho 0.5, R_end_j 1 at swap+charge sites, 0 at swap-only sites (M1) = price of recovery. ILP 'none' (h = z = 0) is timetable independent (solved on the r3 instance, timetable 'any').

## Solver status

| targets | variant | timetable | status | n |
|---|---|---|---|---|
| relaxed | free | cyclic | OPTIMAL | 15 |
| relaxed | free | r3 | OPTIMAL | 14 |
| relaxed | free | r3 | TIME_LIMIT | 1 |
| relaxed | none | any | OPTIMAL | 14 |
| relaxed | none | any | TIME_LIMIT | 1 |
| written | free | cyclic | OPTIMAL | 11 |
| written | free | cyclic | TIME_LIMIT | 4 |
| written | free | r3 | OPTIMAL | 7 |
| written | free | r3 | TIME_LIMIT | 8 |
| written | none | any | OPTIMAL | 13 |
| written | none | any | TIME_LIMIT | 2 |

ILP runtime: mean 125.4 s, max 300.1 s, 74 OPTIMAL of 90; max gap 0.0289.

Demand md5 per seed (distinct values, must be 1): {0: 1, 1: 1, 2: 1, 3: 1, 4: 1}.

## Headline (relaxed control, rho 0, R_end 0): ILP vs policies (seed means)

| layout | timetable | ILP | n | ILP_total | ILP_C_end_adjust | best_rule_total | gap_best_rule_% | gap_best_rule_adj_% | gap_best_notransfer_% | gap_r2_% | gap_r2_reorder_% | gap_r5_transfer_% | gap_r5_% | served | transfers | moved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | any | none | 5 | 579.60 | 1.39 | 785.08 | 25.08 | 24.98 | 25.08 | 25.08 | 35.72 | 32.83 | 33.94 | 0.99 | 0 | 0 |
| colocated | r3 | free | 5 | 579.60 | 1.38 | 785.08 | 25.08 | 24.98 | 25.08 | 25.08 | 35.72 | 32.83 | 33.94 | 0.99 | 0 | 0 |
| colocated | cyclic | free | 5 | 579.60 | 1.39 | 785.08 | 25.08 | 24.98 | 25.08 | 25.08 | 28.03 | 27.95 | 29.70 | 0.99 | 0 | 0 |
| separated_1hub | any | none | 5 | 608.79 | 1.47 | 813.72 | 24.15 | 24.10 | 24.15 | 24.15 | 33.85 | 30.47 | 32.85 | 0.99 | 0 | 0 |
| separated_1hub | r3 | free | 5 | 608.79 | 1.47 | 813.72 | 24.15 | 24.10 | 24.15 | 24.15 | 33.85 | 30.47 | 32.85 | 0.99 | 0 | 0 |
| separated_1hub | cyclic | free | 5 | 608.79 | 1.47 | 813.72 | 24.15 | 24.10 | 24.15 | 24.15 | 25.23 | 29.41 | 29.99 | 0.99 | 0 | 0 |
| separated_2hubs | any | none | 5 | 637.35 | 1.39 | 842.91 | 23.41 | 23.36 | 23.41 | 23.41 | 32.87 | 29.81 | 31.89 | 0.99 | 0 | 0 |
| separated_2hubs | r3 | free | 5 | 637.35 | 1.39 | 842.91 | 23.41 | 23.36 | 23.41 | 23.41 | 32.87 | 29.81 | 31.89 | 0.99 | 0 | 0 |
| separated_2hubs | cyclic | free | 5 | 637.35 | 1.39 | 842.91 | 23.41 | 23.36 | 23.41 | 23.41 | 24.42 | 27.47 | 26.17 | 0.99 | 0 | 0 |

## Written targets (M1): ILP vs policies (seed means)

| layout | timetable | ILP | n | ILP_total | ILP_C_end_adjust | best_rule_total | gap_best_rule_% | gap_best_rule_adj_% | gap_best_notransfer_% | gap_r2_% | gap_r2_reorder_% | gap_r5_transfer_% | gap_r5_% | served | transfers | moved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | any | none | 5 | 579.87 | 1.10 | 785.08 | 25.05 | 24.98 | 25.05 | 25.05 | 35.69 | 35.70 | 35.85 | 0.99 | 0 | 0 |
| colocated | r3 | free | 5 | 579.87 | 1.10 | 785.08 | 25.05 | 24.98 | 25.05 | 25.05 | 35.69 | 35.70 | 35.85 | 0.99 | 0 | 0 |
| colocated | cyclic | free | 5 | 579.87 | 1.10 | 785.08 | 25.05 | 24.98 | 25.05 | 25.05 | 27.99 | 28.34 | 30.13 | 0.99 | 0 | 0 |
| separated_1hub | any | none | 5 | 680.67 | 1.22 | 813.72 | 15.65 | 15.65 | 15.65 | 15.65 | 26.37 | 22.62 | 25.32 | 0.96 | 0 | 0 |
| separated_1hub | r3 | free | 5 | 631.43 | 1.11 | 813.72 | 21.31 | 21.31 | 21.31 | 21.31 | 31.38 | 27.87 | 30.33 | 0.99 | 1 | 2.20 |
| separated_1hub | cyclic | free | 5 | 616.81 | 1.06 | 813.72 | 23.15 | 23.15 | 23.15 | 23.15 | 24.24 | 28.48 | 29.06 | 0.99 | 1 | 2.20 |
| separated_2hubs | any | none | 5 | 709.09 | 1.22 | 842.91 | 15.24 | 15.23 | 15.24 | 15.24 | 25.64 | 22.28 | 24.62 | 0.95 | 0 | 0 |
| separated_2hubs | r3 | free | 5 | 660.31 | 1.09 | 842.91 | 20.64 | 20.64 | 20.64 | 20.64 | 30.44 | 27.28 | 29.42 | 0.99 | 1 | 2 |
| separated_2hubs | cyclic | free | 5 | 644.45 | 1.08 | 842.91 | 22.56 | 22.56 | 22.56 | 22.56 | 23.59 | 26.67 | 25.35 | 0.99 | 1 | 2.20 |

## Policy totals (seed means, USD per 4 h window)

| targets | layout | timetable | r2 | r2_reorder | r5_range | r5_transfer | r5 | r2_C_end_adjust |
|---|---|---|---|---|---|---|---|---|
| relaxed | colocated | r3 | 785.08 | 909.05 | 808.48 | 874.05 | 891.10 | 0.80 |
| relaxed | colocated | cyclic | 785.08 | 818.17 | 808.48 | 815.17 | 838.90 | 0.80 |
| relaxed | separated_1hub | r3 | 813.72 | 929.93 | 837.49 | 884.48 | 922.49 | 1.38 |
| relaxed | separated_1hub | cyclic | 813.72 | 824.20 | 837.49 | 872.81 | 888.93 | 1.38 |
| relaxed | separated_2hubs | r3 | 842.91 | 958.87 | 866.68 | 917.54 | 951.23 | 1.38 |
| relaxed | separated_2hubs | cyclic | 842.91 | 853.47 | 866.68 | 894.75 | 877.31 | 1.38 |
| written | colocated | r3 | 785.08 | 909.05 | 808.48 | 908.10 | 916.50 | 0.80 |
| written | colocated | cyclic | 785.08 | 818.17 | 808.48 | 819.79 | 846.00 | 0.80 |
| written | separated_1hub | r3 | 813.72 | 929.93 | 837.49 | 884.48 | 922.49 | 1.38 |
| written | separated_1hub | cyclic | 813.72 | 824.20 | 837.49 | 872.81 | 888.93 | 1.38 |
| written | separated_2hubs | r3 | 842.91 | 958.87 | 866.68 | 917.54 | 951.23 | 1.38 |
| written | separated_2hubs | cyclic | 842.91 | 853.47 | 866.68 | 894.75 | 877.31 | 1.38 |

## Value of transfers (ILP)

| targets | layout | timetable | ILP value of transfers none - free (USD) | share of ILP(none) % |
|---|---|---|---|---|
| relaxed | colocated | r3 | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| relaxed | colocated | cyclic | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| relaxed | separated_1hub | r3 | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| relaxed | separated_1hub | cyclic | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| relaxed | separated_2hubs | r3 | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| relaxed | separated_2hubs | cyclic | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| written | colocated | r3 | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| written | colocated | cyclic | 0.00 +- 0.00 (n 5) | 0.00 +- 0.00 (n 5) |
| written | separated_1hub | r3 | 49.24 +- 34.55 (n 5) | 6.91 +- 4.45 (n 5) |
| written | separated_1hub | cyclic | 63.87 +- 34.69 (n 5) | 9.08 +- 4.27 (n 5) |
| written | separated_2hubs | r3 | 48.78 +- 35.14 (n 5) | 6.57 +- 4.40 (n 5) |
| written | separated_2hubs | cyclic | 64.64 +- 35.00 (n 5) | 8.82 +- 4.17 (n 5) |

## Separation cost (separated - colocated, USD)

| targets | timetable | ILP | layout | ILP sep - colocated | best_rule sep - colocated |
|---|---|---|---|---|---|
| relaxed | any | none | separated_1hub | 29.20 +- 0.04 (n 5) | 28.63 +- 0.05 (n 5) |
| relaxed | any | none | separated_2hubs | 57.76 +- 0.86 (n 5) | 57.82 +- 0.05 (n 5) |
| relaxed | r3 | free | separated_1hub | 29.20 +- 0.04 (n 5) | 28.63 +- 0.05 (n 5) |
| relaxed | r3 | free | separated_2hubs | 57.76 +- 0.86 (n 5) | 57.82 +- 0.05 (n 5) |
| relaxed | cyclic | free | separated_1hub | 29.20 +- 0.04 (n 5) | 28.63 +- 0.05 (n 5) |
| relaxed | cyclic | free | separated_2hubs | 57.76 +- 0.86 (n 5) | 57.82 +- 0.05 (n 5) |
| written | any | none | separated_1hub | 100.80 +- 35.14 (n 5) | 28.63 +- 0.05 (n 5) |
| written | any | none | separated_2hubs | 129.22 +- 35.68 (n 5) | 57.82 +- 0.05 (n 5) |
| written | r3 | free | separated_1hub | 51.56 +- 0.82 (n 5) | 28.63 +- 0.05 (n 5) |
| written | r3 | free | separated_2hubs | 80.44 +- 0.88 (n 5) | 57.82 +- 0.05 (n 5) |
| written | cyclic | free | separated_1hub | 36.93 +- 0.79 (n 5) | 28.63 +- 0.05 (n 5) |
| written | cyclic | free | separated_2hubs | 64.58 +- 0.95 (n 5) | 57.82 +- 0.05 (n 5) |

## Does COST_AWARE (M3) remove the REORDER_POINT loss? (USD; positive = worse than r2)

| targets | layout | timetable | REORDER loss r2_reorder - r2 | COST_AWARE loss r5_transfer - r2 | r5 - r5_range | COST_AWARE <= r2 (seeds) | COST_AWARE < REORDER (seeds) |
|---|---|---|---|---|---|---|---|
| relaxed | colocated | r3 | 123.97 +- 27.93 (n 5) | 88.96 +- 25.73 (n 5) | 82.62 +- 27.71 (n 5) | 0/5 | 4/5 |
| relaxed | colocated | cyclic | 33.09 +- 26.53 (n 5) | 30.09 +- 13.02 (n 5) | 30.42 +- 27.21 (n 5) | 0/5 | 2/5 |
| relaxed | separated_1hub | r3 | 116.21 +- 40.51 (n 5) | 70.76 +- 16.73 (n 5) | 85.00 +- 23.98 (n 5) | 0/5 | 3/5 |
| relaxed | separated_1hub | cyclic | 10.48 +- 8.68 (n 5) | 59.09 +- 29.85 (n 5) | 51.44 +- 28.01 (n 5) | 0/5 | 0/5 |
| relaxed | separated_2hubs | r3 | 115.96 +- 40.59 (n 5) | 74.63 +- 10.76 (n 5) | 84.55 +- 23.78 (n 5) | 0/5 | 3/5 |
| relaxed | separated_2hubs | cyclic | 10.56 +- 6.41 (n 5) | 51.85 +- 43.22 (n 5) | 10.63 +- 7.71 (n 5) | 0/5 | 0/5 |
| written | colocated | r3 | 123.97 +- 27.93 (n 5) | 123.02 +- 18.56 (n 5) | 108.01 +- 5.42 (n 5) | 0/5 | 2/5 |
| written | colocated | cyclic | 33.09 +- 26.53 (n 5) | 34.71 +- 13.42 (n 5) | 37.51 +- 33.17 (n 5) | 0/5 | 2/5 |
| written | separated_1hub | r3 | 116.21 +- 40.51 (n 5) | 70.76 +- 16.73 (n 5) | 85.00 +- 23.98 (n 5) | 0/5 | 3/5 |
| written | separated_1hub | cyclic | 10.48 +- 8.68 (n 5) | 59.09 +- 29.85 (n 5) | 51.44 +- 28.01 (n 5) | 0/5 | 0/5 |
| written | separated_2hubs | r3 | 115.96 +- 40.59 (n 5) | 74.63 +- 10.76 (n 5) | 84.55 +- 23.78 (n 5) | 0/5 | 3/5 |
| written | separated_2hubs | cyclic | 10.56 +- 6.41 (n 5) | 51.85 +- 43.22 (n 5) | 10.63 +- 7.71 (n 5) | 0/5 | 0/5 |

## Cyclic (M8) vs hub-spoke / site-site (round-3) timetable (USD)

| targets | layout | ILP free cyclic - r3 | ILP transfers used r3 / cyclic | ILP moved r3 / cyclic | r2_reorder cyclic - r3 | r5_transfer cyclic - r3 | r5 cyclic - r3 |
|---|---|---|---|---|---|---|---|
| relaxed | colocated | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -90.88 +- 44.03 (n 5) | -58.87 +- 33.09 (n 5) | -52.20 +- 48.26 (n 5) |
| relaxed | separated_1hub | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -105.73 +- 33.65 (n 5) | -11.68 +- 23.69 (n 5) | -33.56 +- 25.26 (n 5) |
| relaxed | separated_2hubs | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -105.40 +- 37.17 (n 5) | -22.78 +- 51.43 (n 5) | -73.92 +- 21.94 (n 5) |
| written | colocated | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -90.88 +- 44.03 (n 5) | -88.31 +- 24.65 (n 5) | -70.50 +- 35.91 (n 5) |
| written | separated_1hub | -14.62 +- 0.57 (n 5) | 1 / 1 | 2.2 / 2.2 | -105.73 +- 33.65 (n 5) | -11.68 +- 23.69 (n 5) | -33.56 +- 25.26 (n 5) |
| written | separated_2hubs | -15.87 +- 0.21 (n 5) | 1 / 1 | 2 / 2.2 | -105.40 +- 37.17 (n 5) | -22.78 +- 51.43 (n 5) | -73.92 +- 21.94 (n 5) |

## Price of recovery (written - relaxed, USD)

| layout | timetable | ILP | ILP written - relaxed (total) | ILP written - relaxed (end-adjusted) | C_end_adjust written / relaxed | best_rule written - relaxed |
|---|---|---|---|---|---|---|
| colocated | any | none | 0.27 +- 0.05 (n 5) | -0.01 +- 0.05 (n 5) | 1.10 / 1.39 | 0.00 +- 0.00 (n 5) |
| colocated | r3 | free | 0.27 +- 0.05 (n 5) | -0.01 +- 0.05 (n 5) | 1.10 / 1.38 | 0.00 +- 0.00 (n 5) |
| colocated | cyclic | free | 0.27 +- 0.05 (n 5) | -0.01 +- 0.05 (n 5) | 1.10 / 1.39 | 0.00 +- 0.00 (n 5) |
| separated_1hub | any | none | 71.88 +- 35.12 (n 5) | 71.63 +- 35.10 (n 5) | 1.22 / 1.47 | 0.00 +- 0.00 (n 5) |
| separated_1hub | r3 | free | 22.64 +- 0.79 (n 5) | 22.27 +- 0.72 (n 5) | 1.11 / 1.47 | 0.00 +- 0.00 (n 5) |
| separated_1hub | cyclic | free | 8.01 +- 0.80 (n 5) | 7.61 +- 0.73 (n 5) | 1.06 / 1.47 | 0.00 +- 0.00 (n 5) |
| separated_2hubs | any | none | 71.74 +- 36.21 (n 5) | 71.56 +- 36.19 (n 5) | 1.22 / 1.39 | 0.00 +- 0.00 (n 5) |
| separated_2hubs | r3 | free | 22.96 +- 1.48 (n 5) | 22.65 +- 1.49 (n 5) | 1.09 / 1.39 | 0.00 +- 0.00 (n 5) |
| separated_2hubs | cyclic | free | 7.09 +- 1.50 (n 5) | 6.78 +- 1.51 (n 5) | 1.08 / 1.39 | 0.00 +- 0.00 (n 5) |

## A3 metric pack (seed means)

| targets | layout | timetable | method | min_sbur | bsr | outage_rate | empty_km_share | mean_station_time_min | peak_kw_network | kwh_purchased | batteries_saved_total | C_end_adjust |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | colocated | r3 | ilp:free | 0.533 | 0.783 | 0.267 | 0.173 | 7.708 | 0.067 | 0.028 | 1.800 | 1.385 |
| relaxed | colocated | r3 | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| relaxed | colocated | r3 | baseline:r5 | 0 | 0.936 | 0.033 | 0.114 | 5.322 | 1.333 | 1.561 | 0.200 | 1.134 |
| relaxed | colocated | cyclic | ilp:free | 0.533 | 0.758 | 0.267 | 0.179 | 7.833 | 0.067 | 0.028 | 1.800 | 1.387 |
| relaxed | colocated | cyclic | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| relaxed | colocated | cyclic | baseline:r5 | 0 | 0.933 | 0 | 0.094 | 5.333 | 1.267 | 1.717 | 0 | 1.040 |
| relaxed | separated_1hub | r3 | ilp:free | 0.733 | 0.515 | 0.267 | 0.167 | 9.609 | 0 | 0 | 1 | 1.468 |
| relaxed | separated_1hub | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_1hub | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1.800 | 2.506 | 0.400 | 0.772 |
| relaxed | separated_1hub | cyclic | ilp:free | 0.733 | 0.544 | 0.267 | 0.167 | 9.355 | 0 | 0 | 1 | 1.468 |
| relaxed | separated_1hub | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_1hub | cyclic | baseline:r5 | 0.067 | 0.978 | 0 | 0.112 | 5.111 | 1.200 | 1.367 | 0.200 | 1.129 |
| relaxed | separated_2hubs | r3 | ilp:free | 0.600 | 0.832 | 0.267 | 0.167 | 7.946 | 0 | 0 | 1.800 | 1.394 |
| relaxed | separated_2hubs | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_2hubs | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1 | 1.706 | 0.400 | 1.028 |
| relaxed | separated_2hubs | cyclic | ilp:free | 0.600 | 0.832 | 0.267 | 0.168 | 7.946 | 0 | 0 | 1.800 | 1.394 |
| relaxed | separated_2hubs | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_2hubs | cyclic | baseline:r5 | 0.333 | 0.978 | 0.033 | 0.090 | 5.111 | 0.933 | 1.194 | 0.400 | 1.172 |
| written | colocated | r3 | ilp:free | 0.400 | 0.771 | 0.400 | 0.169 | 8.071 | 0.667 | 0.817 | 3 | 1.099 |
| written | colocated | r3 | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| written | colocated | r3 | baseline:r5 | 0.267 | 0.913 | 0.033 | 0.106 | 5.433 | 1.467 | 1.800 | 0 | 1.029 |
| written | colocated | cyclic | ilp:free | 0.400 | 0.805 | 0.400 | 0.169 | 7.905 | 0.667 | 0.817 | 3 | 1.099 |
| written | colocated | cyclic | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| written | colocated | cyclic | baseline:r5 | 0.200 | 0.933 | 0 | 0.094 | 5.333 | 1.267 | 1.828 | 0 | 1.004 |
| written | separated_1hub | r3 | ilp:free | 0.267 | 0.771 | 0.400 | 0.173 | 6.786 | 0.733 | 0.889 | 2.800 | 1.106 |
| written | separated_1hub | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_1hub | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1.800 | 2.506 | 0.400 | 0.772 |
| written | separated_1hub | cyclic | ilp:free | 0.267 | 0.733 | 0.300 | 0.171 | 8.833 | 0.733 | 0.972 | 2.800 | 1.065 |
| written | separated_1hub | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_1hub | cyclic | baseline:r5 | 0.067 | 0.978 | 0 | 0.112 | 5.111 | 1.200 | 1.367 | 0.200 | 1.129 |
| written | separated_2hubs | r3 | ilp:free | 0.200 | 0.700 | 0.333 | 0.162 | 10.333 | 0.667 | 0.878 | 3 | 1.086 |
| written | separated_2hubs | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_2hubs | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1 | 1.706 | 0.400 | 1.028 |
| written | separated_2hubs | cyclic | ilp:free | 0.133 | 0.600 | 0.367 | 0.167 | 10.833 | 0.733 | 0.978 | 2.800 | 1.079 |
| written | separated_2hubs | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_2hubs | cyclic | baseline:r5 | 0.333 | 0.978 | 0.033 | 0.090 | 5.111 | 0.933 | 1.194 | 0.400 | 1.172 |

## Anomalies

- separated_1hub/any/relaxed/seed3/none: status TIME_LIMIT, gap 0.0028835314852991103
- separated_2hubs/r3/relaxed/seed3/free: status TIME_LIMIT, gap 0.00604356489907037
- colocated/any/written/seed0/none: MIP start r2(unverified) not accepted
- separated_1hub/any/written/seed0/none: MIP start r2(unverified) not accepted
- separated_1hub/r3/written/seed0/free: status TIME_LIMIT, gap 0.022831189230984532
- separated_2hubs/any/written/seed0/none: MIP start r2(unverified) not accepted
- separated_2hubs/r3/written/seed0/free: status TIME_LIMIT, gap 0.02175733418889921
- separated_1hub/any/written/seed1/none: MIP start r2(unverified) not accepted
- separated_1hub/any/written/seed1/none: status TIME_LIMIT, gap 0.01443479699223647
- separated_1hub/r3/written/seed1/free: status TIME_LIMIT, gap 0.023233085403399342
- separated_2hubs/any/written/seed1/none: MIP start r2(unverified) not accepted
- separated_2hubs/any/written/seed1/none: status TIME_LIMIT, gap 0.008775226998433985
- separated_2hubs/r3/written/seed1/free: status TIME_LIMIT, gap 0.022115595697304223
- separated_1hub/any/written/seed2/none: MIP start r2(unverified) not accepted
- separated_2hubs/any/written/seed2/none: MIP start r2(unverified) not accepted
- colocated/any/written/seed3/none: MIP start r2(unverified) not accepted
- colocated/cyclic/written/seed3/free: status TIME_LIMIT, gap 0.005082374976828811
- separated_1hub/any/written/seed3/none: MIP start r2(unverified) not accepted
- separated_1hub/r3/written/seed3/free: status TIME_LIMIT, gap 0.028874250623978
- separated_1hub/cyclic/written/seed3/free: status TIME_LIMIT, gap 0.009769544217192205
- separated_2hubs/any/written/seed3/none: MIP start r2(unverified) not accepted
- separated_2hubs/r3/written/seed3/free: status TIME_LIMIT, gap 0.02802911034082637
- separated_2hubs/cyclic/written/seed3/free: status TIME_LIMIT, gap 0.004700793582923619
- separated_1hub/any/written/seed4/none: MIP start r2(unverified) not accepted
- separated_1hub/r3/written/seed4/free: status TIME_LIMIT, gap 0.022101412799088022
- separated_1hub/cyclic/written/seed4/free: status TIME_LIMIT, gap 0.005918696133822622
- separated_2hubs/any/written/seed4/none: MIP start r2(unverified) not accepted
- separated_2hubs/r3/written/seed4/free: status TIME_LIMIT, gap 0.021327532244561596

## Figures

- `fig_cost_by_layout.png`

