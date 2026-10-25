# X2 (round 5) -- transfers and separation (usd4h, ebaas, seeds 0-4)

Gurobi Threads 3, Seed 0, TimeLimit 300 s, aggregated ILP (O1). Gap = 100 (baseline - ILP) / baseline. best_rule = min over r2, r5_range, r5_transfer, r5 per instance. Headline = relaxed control (rho 0, R_end 0); written = rho 0.5, R_end_j 1 at swap+charge sites, 0 at swap-only sites (M1) = price of recovery. ILP 'none' (h = z = 0) is timetable independent (solved on the r3 instance, timetable 'any').

## Solver status

| targets | variant | timetable | status | n |
|---|---|---|---|---|
| relaxed | free | cyclic | OPTIMAL | 15 |
| relaxed | free | r3 | OPTIMAL | 15 |
| relaxed | none | any | OPTIMAL | 15 |
| written | free | cyclic | OPTIMAL | 14 |
| written | free | cyclic | TIME_LIMIT | 1 |
| written | free | r3 | OPTIMAL | 5 |
| written | free | r3 | TIME_LIMIT | 10 |
| written | none | any | OPTIMAL | 15 |

ILP runtime: mean 85.5 s, max 300.1 s, 79 OPTIMAL of 90; max gap 0.0228.

Demand md5 per seed (distinct values, must be 1): {0: 1, 1: 1, 2: 1, 3: 1, 4: 1}.

## Headline (relaxed control, rho 0, R_end 0): ILP vs policies (seed means)

| layout | timetable | ILP | n | ILP_total | ILP_C_end_adjust | best_rule_total | gap_best_rule_% | gap_best_rule_adj_% | gap_best_notransfer_% | gap_r2_% | gap_r2_reorder_% | gap_r5_transfer_% | gap_r5_% | served | transfers | moved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | any | none | 5 | 565.54 | 1.40 | 732.73 | 21.77 | 21.67 | 21.77 | 22.17 | 33.62 | 27.60 | 26.76 | 0.97 | 0 | 0 |
| colocated | r3 | free | 5 | 565.54 | 1.40 | 732.73 | 21.77 | 21.67 | 21.77 | 22.17 | 33.62 | 27.60 | 26.76 | 0.97 | 0 | 0 |
| colocated | cyclic | free | 5 | 565.54 | 1.40 | 732.73 | 21.77 | 21.67 | 21.77 | 22.17 | 25.14 | 24.39 | 23.86 | 0.97 | 0 | 0 |
| separated_1hub | any | none | 5 | 594.54 | 1.44 | 761.52 | 20.94 | 20.91 | 20.94 | 21.31 | 31.74 | 27.50 | 27.60 | 0.97 | 0 | 0 |
| separated_1hub | r3 | free | 5 | 594.54 | 1.44 | 761.52 | 20.94 | 20.91 | 20.94 | 21.31 | 31.74 | 27.50 | 27.60 | 0.97 | 0 | 0 |
| separated_1hub | cyclic | free | 5 | 594.54 | 1.44 | 761.52 | 20.94 | 20.91 | 20.94 | 21.31 | 22.44 | 24.66 | 24.02 | 0.97 | 0 | 0 |
| separated_2hubs | any | none | 5 | 623.59 | 1.40 | 790.71 | 20.21 | 20.19 | 20.21 | 20.57 | 30.73 | 27.33 | 28.39 | 0.97 | 0 | 0 |
| separated_2hubs | r3 | free | 5 | 623.59 | 1.40 | 790.71 | 20.21 | 20.19 | 20.21 | 20.57 | 30.73 | 27.33 | 28.39 | 0.97 | 0 | 0 |
| separated_2hubs | cyclic | free | 5 | 623.59 | 1.40 | 790.71 | 20.21 | 20.19 | 20.21 | 20.57 | 21.69 | 22.73 | 21.87 | 0.97 | 0 | 0 |

## Written targets (M1): ILP vs policies (seed means)

| layout | timetable | ILP | n | ILP_total | ILP_C_end_adjust | best_rule_total | gap_best_rule_% | gap_best_rule_adj_% | gap_best_notransfer_% | gap_r2_% | gap_r2_reorder_% | gap_r5_transfer_% | gap_r5_% | served | transfers | moved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| colocated | any | none | 5 | 565.84 | 1.07 | 732.73 | 21.73 | 21.67 | 21.73 | 22.13 | 33.58 | 29.83 | 28.85 | 0.97 | 0 | 0 |
| colocated | r3 | free | 5 | 565.84 | 1.07 | 732.73 | 21.73 | 21.67 | 21.73 | 22.13 | 33.58 | 29.83 | 28.85 | 0.97 | 0 | 0 |
| colocated | cyclic | free | 5 | 565.84 | 1.07 | 732.73 | 21.73 | 21.67 | 21.73 | 22.13 | 25.10 | 25.77 | 24.70 | 0.97 | 0 | 0 |
| separated_1hub | any | none | 5 | 618.82 | 1.18 | 761.52 | 17.75 | 17.76 | 17.75 | 18.13 | 28.99 | 24.56 | 24.67 | 0.93 | 0 | 0 |
| separated_1hub | r3 | free | 5 | 615.26 | 1.13 | 761.52 | 18.20 | 18.22 | 18.20 | 18.59 | 29.38 | 24.98 | 25.09 | 0.96 | 0.60 | 1.20 |
| separated_1hub | cyclic | free | 5 | 602.42 | 1.07 | 761.52 | 19.89 | 19.91 | 19.89 | 20.27 | 21.41 | 23.66 | 23.01 | 0.97 | 1 | 2 |
| separated_2hubs | any | none | 5 | 647.73 | 1.19 | 790.71 | 17.15 | 17.16 | 17.15 | 17.52 | 28.08 | 24.52 | 25.64 | 0.93 | 0 | 0 |
| separated_2hubs | r3 | free | 5 | 644.64 | 1.13 | 790.71 | 17.54 | 17.55 | 17.54 | 17.91 | 28.41 | 24.88 | 25.99 | 0.96 | 0.60 | 1.20 |
| separated_2hubs | cyclic | free | 5 | 630.34 | 1.08 | 790.71 | 19.35 | 19.37 | 19.35 | 19.72 | 20.84 | 21.90 | 21.03 | 0.97 | 1 | 2 |

## Policy totals (seed means, USD per 4 h window)

| targets | layout | timetable | r2 | r2_reorder | r5_range | r5_transfer | r5 | r2_C_end_adjust |
|---|---|---|---|---|---|---|---|---|
| relaxed | colocated | r3 | 736.38 | 858.90 | 740.03 | 786.98 | 781.76 | 0.80 |
| relaxed | colocated | cyclic | 736.38 | 763.47 | 740.03 | 756.32 | 751.67 | 0.80 |
| relaxed | separated_1hub | r3 | 765.02 | 881.23 | 769.04 | 827.54 | 832.64 | 1.38 |
| relaxed | separated_1hub | cyclic | 765.02 | 775.50 | 769.04 | 796.90 | 792.36 | 1.38 |
| relaxed | separated_2hubs | r3 | 794.21 | 910.17 | 798.23 | 864.70 | 882.78 | 1.38 |
| relaxed | separated_2hubs | cyclic | 794.21 | 804.77 | 798.23 | 819.06 | 808.58 | 1.38 |
| written | colocated | r3 | 736.38 | 858.90 | 740.03 | 812.73 | 804.83 | 0.80 |
| written | colocated | cyclic | 736.38 | 763.47 | 740.03 | 768.82 | 760.21 | 0.80 |
| written | separated_1hub | r3 | 765.02 | 881.23 | 769.04 | 827.54 | 832.64 | 1.38 |
| written | separated_1hub | cyclic | 765.02 | 775.50 | 769.04 | 796.90 | 792.36 | 1.38 |
| written | separated_2hubs | r3 | 794.21 | 910.17 | 798.23 | 864.70 | 882.78 | 1.38 |
| written | separated_2hubs | cyclic | 794.21 | 804.77 | 798.23 | 819.06 | 808.58 | 1.38 |

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
| written | separated_1hub | r3 | 3.56 +- 3.43 (n 5) | 0.57 +- 0.55 (n 5) |
| written | separated_1hub | cyclic | 16.40 +- 6.40 (n 5) | 2.64 +- 1.01 (n 5) |
| written | separated_2hubs | r3 | 3.09 +- 2.97 (n 5) | 0.48 +- 0.46 (n 5) |
| written | separated_2hubs | cyclic | 17.39 +- 5.40 (n 5) | 2.68 +- 0.82 (n 5) |

## Separation cost (separated - colocated, USD)

| targets | timetable | ILP | layout | ILP sep - colocated | best_rule sep - colocated |
|---|---|---|---|---|---|
| relaxed | any | none | separated_1hub | 29.00 +- 0.38 (n 5) | 28.79 +- 0.38 (n 5) |
| relaxed | any | none | separated_2hubs | 58.04 +- 0.53 (n 5) | 57.98 +- 0.38 (n 5) |
| relaxed | r3 | free | separated_1hub | 29.00 +- 0.38 (n 5) | 28.79 +- 0.38 (n 5) |
| relaxed | r3 | free | separated_2hubs | 58.04 +- 0.53 (n 5) | 57.98 +- 0.38 (n 5) |
| relaxed | cyclic | free | separated_1hub | 29.00 +- 0.38 (n 5) | 28.79 +- 0.38 (n 5) |
| relaxed | cyclic | free | separated_2hubs | 58.04 +- 0.53 (n 5) | 57.98 +- 0.38 (n 5) |
| written | any | none | separated_1hub | 52.98 +- 6.00 (n 5) | 28.79 +- 0.38 (n 5) |
| written | any | none | separated_2hubs | 81.89 +- 5.88 (n 5) | 57.98 +- 0.38 (n 5) |
| written | r3 | free | separated_1hub | 49.41 +- 3.00 (n 5) | 28.79 +- 0.38 (n 5) |
| written | r3 | free | separated_2hubs | 78.80 +- 3.22 (n 5) | 57.98 +- 0.38 (n 5) |
| written | cyclic | free | separated_1hub | 36.57 +- 0.56 (n 5) | 28.79 +- 0.38 (n 5) |
| written | cyclic | free | separated_2hubs | 64.50 +- 0.90 (n 5) | 57.98 +- 0.38 (n 5) |

## Does COST_AWARE (M3) remove the REORDER_POINT loss? (USD; positive = worse than r2)

| targets | layout | timetable | REORDER loss r2_reorder - r2 | COST_AWARE loss r5_transfer - r2 | r5 - r5_range | COST_AWARE <= r2 (seeds) | COST_AWARE < REORDER (seeds) |
|---|---|---|---|---|---|---|---|
| relaxed | colocated | r3 | 122.52 +- 18.05 (n 5) | 50.60 +- 31.11 (n 5) | 41.73 +- 8.02 (n 5) | 0/5 | 5/5 |
| relaxed | colocated | cyclic | 27.09 +- 20.34 (n 5) | 19.94 +- 20.42 (n 5) | 11.63 +- 16.92 (n 5) | 0/5 | 3/5 |
| relaxed | separated_1hub | r3 | 116.21 +- 40.51 (n 5) | 62.52 +- 8.88 (n 5) | 63.60 +- 9.42 (n 5) | 0/5 | 4/5 |
| relaxed | separated_1hub | cyclic | 10.48 +- 8.68 (n 5) | 31.88 +- 31.83 (n 5) | 23.32 +- 26.09 (n 5) | 0/5 | 2/5 |
| relaxed | separated_2hubs | r3 | 115.96 +- 40.59 (n 5) | 70.50 +- 16.83 (n 5) | 84.55 +- 23.78 (n 5) | 0/5 | 3/5 |
| relaxed | separated_2hubs | cyclic | 10.56 +- 6.41 (n 5) | 24.86 +- 30.66 (n 5) | 10.35 +- 7.14 (n 5) | 1/5 | 0/5 |
| written | colocated | r3 | 122.52 +- 18.05 (n 5) | 76.35 +- 31.99 (n 5) | 64.80 +- 6.05 (n 5) | 0/5 | 4/5 |
| written | colocated | cyclic | 27.09 +- 20.34 (n 5) | 32.44 +- 18.09 (n 5) | 20.18 +- 22.84 (n 5) | 0/5 | 2/5 |
| written | separated_1hub | r3 | 116.21 +- 40.51 (n 5) | 62.52 +- 8.88 (n 5) | 63.60 +- 9.42 (n 5) | 0/5 | 4/5 |
| written | separated_1hub | cyclic | 10.48 +- 8.68 (n 5) | 31.88 +- 31.83 (n 5) | 23.32 +- 26.09 (n 5) | 0/5 | 2/5 |
| written | separated_2hubs | r3 | 115.96 +- 40.59 (n 5) | 70.50 +- 16.83 (n 5) | 84.55 +- 23.78 (n 5) | 0/5 | 3/5 |
| written | separated_2hubs | cyclic | 10.56 +- 6.41 (n 5) | 24.86 +- 30.66 (n 5) | 10.35 +- 7.14 (n 5) | 1/5 | 0/5 |

## Cyclic (M8) vs hub-spoke / site-site (round-3) timetable (USD)

| targets | layout | ILP free cyclic - r3 | ILP transfers used r3 / cyclic | ILP moved r3 / cyclic | r2_reorder cyclic - r3 | r5_transfer cyclic - r3 | r5 cyclic - r3 |
|---|---|---|---|---|---|---|---|
| relaxed | colocated | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -95.43 +- 31.05 (n 5) | -30.66 +- 15.16 (n 5) | -30.09 +- 14.45 (n 5) |
| relaxed | separated_1hub | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -105.73 +- 33.65 (n 5) | -30.64 +- 31.54 (n 5) | -40.28 +- 26.07 (n 5) |
| relaxed | separated_2hubs | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -105.40 +- 37.17 (n 5) | -45.64 +- 44.06 (n 5) | -74.20 +- 21.99 (n 5) |
| written | colocated | 0.00 +- 0.00 (n 5) | 0 / 0 | 0 / 0 | -95.43 +- 31.05 (n 5) | -43.91 +- 21.31 (n 5) | -44.63 +- 19.97 (n 5) |
| written | separated_1hub | -12.84 +- 3.47 (n 5) | 0.6 / 1 | 1.2 / 2 | -105.73 +- 33.65 (n 5) | -30.64 +- 31.54 (n 5) | -40.28 +- 26.07 (n 5) |
| written | separated_2hubs | -14.30 +- 2.98 (n 5) | 0.6 / 1 | 1.2 / 2 | -105.40 +- 37.17 (n 5) | -45.64 +- 44.06 (n 5) | -74.20 +- 21.99 (n 5) |

## Price of recovery (written - relaxed, USD)

| layout | timetable | ILP | ILP written - relaxed (total) | ILP written - relaxed (end-adjusted) | C_end_adjust written / relaxed | best_rule written - relaxed |
|---|---|---|---|---|---|---|
| colocated | any | none | 0.30 +- 0.09 (n 5) | -0.03 +- 0.12 (n 5) | 1.07 / 1.40 | 0.00 +- 0.00 (n 5) |
| colocated | r3 | free | 0.30 +- 0.09 (n 5) | -0.03 +- 0.12 (n 5) | 1.07 / 1.40 | 0.00 +- 0.00 (n 5) |
| colocated | cyclic | free | 0.30 +- 0.09 (n 5) | -0.03 +- 0.12 (n 5) | 1.07 / 1.40 | 0.00 +- 0.00 (n 5) |
| separated_1hub | any | none | 24.28 +- 6.11 (n 5) | 24.02 +- 6.06 (n 5) | 1.18 / 1.44 | 0.00 +- 0.00 (n 5) |
| separated_1hub | r3 | free | 20.71 +- 3.12 (n 5) | 20.40 +- 3.05 (n 5) | 1.13 / 1.44 | 0.00 +- 0.00 (n 5) |
| separated_1hub | cyclic | free | 7.87 +- 0.72 (n 5) | 7.51 +- 0.72 (n 5) | 1.07 / 1.44 | 0.00 +- 0.00 (n 5) |
| separated_2hubs | any | none | 24.15 +- 5.76 (n 5) | 23.94 +- 5.76 (n 5) | 1.19 / 1.40 | 0.00 +- 0.00 (n 5) |
| separated_2hubs | r3 | free | 21.06 +- 3.27 (n 5) | 20.78 +- 3.25 (n 5) | 1.13 / 1.40 | 0.00 +- 0.00 (n 5) |
| separated_2hubs | cyclic | free | 6.75 +- 0.67 (n 5) | 6.43 +- 0.67 (n 5) | 1.08 / 1.40 | 0.00 +- 0.00 (n 5) |

## A3 metric pack (seed means)

| targets | layout | timetable | method | min_sbur | bsr | outage_rate | empty_km_share | mean_station_time_min | peak_kw_network | kwh_purchased | batteries_saved_total | C_end_adjust |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | colocated | r3 | ilp:free | 0.467 | 0.620 | 0.333 | 0.159 | 9.970 | 0 | 0 | 1.800 | 1.404 |
| relaxed | colocated | r3 | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| relaxed | colocated | r3 | baseline:r5 | 0 | 0.958 | 0 | 0.094 | 5.211 | 1.333 | 1.633 | 0 | 1.072 |
| relaxed | colocated | cyclic | ilp:free | 0.467 | 0.587 | 0.300 | 0.160 | 10.470 | 0 | 0 | 1.800 | 1.404 |
| relaxed | colocated | cyclic | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| relaxed | colocated | cyclic | baseline:r5 | 0 | 0.936 | 0 | 0.094 | 5.322 | 1.267 | 1.711 | 0 | 1.070 |
| relaxed | separated_1hub | r3 | ilp:free | 0.667 | 0.699 | 0.133 | 0.188 | 9.226 | 0 | 0 | 1 | 1.436 |
| relaxed | separated_1hub | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_1hub | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1.800 | 2.494 | 0.400 | 0.775 |
| relaxed | separated_1hub | cyclic | ilp:free | 0.667 | 0.699 | 0.133 | 0.188 | 9.115 | 0 | 0 | 1 | 1.436 |
| relaxed | separated_1hub | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_1hub | cyclic | baseline:r5 | 0.067 | 0.933 | 0 | 0.111 | 5.333 | 0.933 | 1.267 | 0 | 1.180 |
| relaxed | separated_2hubs | r3 | ilp:free | 0.467 | 0.640 | 0.167 | 0.176 | 8.583 | 0 | 0 | 1.600 | 1.404 |
| relaxed | separated_2hubs | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_2hubs | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1 | 1.706 | 0.400 | 1.028 |
| relaxed | separated_2hubs | cyclic | ilp:free | 0.467 | 0.640 | 0.167 | 0.176 | 8.583 | 0 | 0 | 1.600 | 1.404 |
| relaxed | separated_2hubs | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| relaxed | separated_2hubs | cyclic | baseline:r5 | 0.533 | 0.933 | 0 | 0.089 | 5.333 | 0.800 | 1.100 | 0.200 | 1.205 |
| written | colocated | r3 | ilp:free | 0.400 | 0.817 | 0.233 | 0.154 | 6.875 | 0.600 | 0.822 | 3.200 | 1.074 |
| written | colocated | r3 | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| written | colocated | r3 | baseline:r5 | 0.133 | 0.958 | 0 | 0.105 | 5.211 | 1.400 | 1.739 | 0 | 1.045 |
| written | colocated | cyclic | ilp:free | 0.400 | 0.817 | 0.233 | 0.157 | 6.875 | 0.600 | 0.822 | 3.200 | 1.074 |
| written | colocated | cyclic | baseline:r2 | 0.333 | 0.975 | 0.067 | 0.072 | 5.125 | 1.467 | 1.872 | 2.600 | 0.796 |
| written | colocated | cyclic | baseline:r5 | 0.133 | 0.933 | 0 | 0.097 | 5.333 | 1.267 | 1.761 | 0 | 1.029 |
| written | separated_1hub | r3 | ilp:free | 0.333 | 0.850 | 0.400 | 0.158 | 6.250 | 0.400 | 0.439 | 3.800 | 1.129 |
| written | separated_1hub | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_1hub | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1.800 | 2.494 | 0.400 | 0.775 |
| written | separated_1hub | cyclic | ilp:free | 0.333 | 0.800 | 0.200 | 0.162 | 7.500 | 0.667 | 0.817 | 3 | 1.072 |
| written | separated_1hub | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_1hub | cyclic | baseline:r5 | 0.067 | 0.933 | 0 | 0.111 | 5.333 | 0.933 | 1.267 | 0 | 1.180 |
| written | separated_2hubs | r3 | ilp:free | 0.200 | 0.800 | 0.367 | 0.178 | 6.500 | 0.400 | 0.450 | 3.800 | 1.125 |
| written | separated_2hubs | r3 | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_2hubs | r3 | baseline:r5 | 0.867 | 0.956 | 0 | 0.110 | 5.222 | 1 | 1.706 | 0.400 | 1.028 |
| written | separated_2hubs | cyclic | ilp:free | 0.333 | 0.767 | 0.333 | 0.174 | 7.500 | 0.667 | 0.833 | 3 | 1.083 |
| written | separated_2hubs | cyclic | baseline:r2 | 0.467 | 0.975 | 0.100 | 0.074 | 5.125 | 0 | 0 | 2.200 | 1.376 |
| written | separated_2hubs | cyclic | baseline:r5 | 0.533 | 0.933 | 0 | 0.089 | 5.333 | 0.800 | 1.100 | 0.200 | 1.205 |

## Anomalies

- colocated/any/written/seed0/none: MIP start r5_range(unverified) not accepted
- separated_1hub/any/written/seed0/none: MIP start r2(unverified) not accepted
- separated_1hub/r3/written/seed0/free: status TIME_LIMIT, gap 0.02275503495201406
- separated_2hubs/any/written/seed0/none: MIP start r2(unverified) not accepted
- separated_2hubs/r3/written/seed0/free: status TIME_LIMIT, gap 0.021754945741605827
- separated_1hub/any/written/seed1/none: MIP start r2(unverified) not accepted
- separated_1hub/r3/written/seed1/free: status TIME_LIMIT, gap 0.022426361593017873
- separated_2hubs/any/written/seed1/none: MIP start r2(unverified) not accepted
- separated_2hubs/r3/written/seed1/free: status TIME_LIMIT, gap 0.021575052981050186
- separated_2hubs/cyclic/written/seed1/free: status TIME_LIMIT, gap 0.00474760380535843
- separated_1hub/any/written/seed2/none: MIP start r5_range(unverified) not accepted
- separated_1hub/r3/written/seed2/free: status TIME_LIMIT, gap 0.018669686752720765
- separated_2hubs/any/written/seed2/none: MIP start r5_range(unverified) not accepted
- separated_2hubs/r3/written/seed2/free: status TIME_LIMIT, gap 0.021165432764953654
- colocated/any/written/seed3/none: MIP start r2(unverified) not accepted
- separated_1hub/any/written/seed3/none: MIP start r2(unverified) not accepted
- separated_1hub/r3/written/seed3/free: status TIME_LIMIT, gap 0.021004549585439746
- separated_2hubs/any/written/seed3/none: MIP start r2(unverified) not accepted
- separated_2hubs/r3/written/seed3/free: status TIME_LIMIT, gap 0.021724241351499418
- separated_1hub/any/written/seed4/none: MIP start r5_range(unverified) not accepted
- separated_1hub/r3/written/seed4/free: status TIME_LIMIT, gap 0.009160987599150416
- separated_2hubs/any/written/seed4/none: MIP start r5_range(unverified) not accepted
- separated_2hubs/r3/written/seed4/free: status TIME_LIMIT, gap 0.010216372004989586

## Figures

- `fig_cost_by_layout.png`

