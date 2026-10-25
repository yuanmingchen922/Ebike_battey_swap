# X3 / M7 rolling horizon: foresight vs coordination

headline = best_rule - offline = (rolling - offline) [value of information] + (best_rule - rolling) [value of coordination online]; best_rule = per-instance min over r2, r5_range, r5_transfer (with services) and r5. Mean +/- 95 % t-CI half-width over seeds, USD per window (percentages: gap = 100 (baseline - ILP) / baseline). Headline = relaxed targets (rho = 0, R_end = 0) on the end-adjusted basis; written = price of recovery.

Rows: 210 records, 56 keys still SKIPPED_BUDGET, 0 keys with only ERROR rows; rolling/forecast rows failing a hard family or (24): 0; offline rows not OPTIMAL: 5 (their voi is a difference of upper bounds; see offline_gap / offline_bound in per_instance.csv).

## targets = relaxed, basis = total_end_adjusted

| quantity | r5_stress4h | usd4h_ebaas |
|---|---|---|
| best_rule | 1387.36 +/- 213.71 (n=5) | 830.91 +/- 109.17 (n=10) |
| r2 | 1460.64 +/- 255.63 (n=5) | 840.44 +/- 111.00 (n=10) |
| offline | 826.10 +/- 54.50 (n=5) | 582.05 +/- 18.40 (n=10) |
| headline_gap_pct | 39.96 +/- 6.38 (n=5) | 28.28 +/- 7.36 (n=10) |
| headline_gap_r2_pct | 42.78 +/- 7.41 (n=5) | 29.03 +/- 7.49 (n=10) |
| forecast10 | 934.37 +/- 62.58 (n=5) | 641.88 +/- 33.14 (n=10) |
| voi_forecast10 | 108.27 +/- 33.38 (n=5) | 59.83 +/- 23.12 (n=10) |
| voi_pct_forecast10 | 13.14 +/- 4.07 (n=5) | 10.24 +/- 3.94 (n=10) |
| coord_forecast10 | 452.99 +/- 187.59 (n=5) | 189.02 +/- 95.57 (n=10) |
| coord_pct_forecast10 | 32.00 +/- 8.76 (n=5) | 20.91 +/- 8.73 (n=10) |
| foresight_share_forecast10 | 0.21 +/- 0.10 (n=5) | 0.32 +/- 0.21 (n=10) |
| coord_r2_forecast10 | 526.28 +/- 222.23 (n=5) | 198.56 +/- 97.08 (n=10) |
| rolling0 | 1027.95 +/- 69.82 (n=5) | 689.95 +/- 37.09 (n=10) |
| voi_rolling0 | 201.85 +/- 27.90 (n=5) | 107.90 +/- 30.32 (n=10) |
| voi_pct_rolling0 | 24.45 +/- 3.12 (n=5) | 18.53 +/- 5.14 (n=10) |
| coord_rolling0 | 359.41 +/- 160.20 (n=5) | 140.96 +/- 99.76 (n=10) |
| coord_pct_rolling0 | 25.31 +/- 7.86 (n=5) | 14.93 +/- 9.53 (n=10) |
| foresight_share_rolling0 | 0.37 +/- 0.11 (n=5) | 0.57 +/- 0.28 (n=10) |
| coord_r2_rolling0 | 432.70 +/- 197.02 (n=5) | 150.50 +/- 97.61 (n=10) |
| rolling10 | 944.07 +/- 64.12 (n=5) | 648.64 +/- 31.34 (n=10) |
| voi_rolling10 | 117.97 +/- 44.85 (n=5) | 66.59 +/- 23.34 (n=10) |
| voi_pct_rolling10 | 14.35 +/- 5.64 (n=5) | 11.43 +/- 3.94 (n=10) |
| coord_rolling10 | 443.29 +/- 192.76 (n=5) | 182.27 +/- 101.77 (n=10) |
| coord_pct_rolling10 | 31.26 +/- 9.44 (n=5) | 19.94 +/- 9.18 (n=10) |
| foresight_share_rolling10 | 0.23 +/- 0.13 (n=5) | 0.36 +/- 0.20 (n=10) |
| coord_r2_rolling10 | 516.57 +/- 228.52 (n=5) | 191.81 +/- 101.87 (n=10) |
| rolling20 | 948.44 +/- 63.55 (n=5) | 620.10 +/- 26.51 (n=10) |
| voi_rolling20 | 122.34 +/- 84.79 (n=5) | 38.05 +/- 19.74 (n=10) |
| voi_pct_rolling20 | 15.09 +/- 11.32 (n=5) | 6.55 +/- 3.43 (n=10) |
| coord_rolling20 | 438.92 +/- 222.22 (n=5) | 210.81 +/- 92.25 (n=10) |
| coord_pct_rolling20 | 30.73 +/- 12.41 (n=5) | 23.65 +/- 7.80 (n=10) |
| foresight_share_rolling20 | 0.24 +/- 0.24 (n=5) | 0.19 +/- 0.16 (n=10) |
| coord_r2_rolling20 | 512.20 +/- 264.87 (n=5) | 220.34 +/- 94.34 (n=10) |
| battery_plan_value | 9.71 +/- 18.66 (n=5) | 6.75 +/- 15.08 (n=10) |

## targets = written, basis = total_end_adjusted

| quantity | r5_stress4h | usd4h_ebaas |
|---|---|---|
| best_rule | 1387.36 +/- 213.71 (n=5) | 733.60 +/- 137.06 (n=5) |
| r2 | 1460.64 +/- 255.63 (n=5) | 737.18 +/- 136.63 (n=5) |
| offline | 832.83 +/- 57.30 (n=5) | 566.92 +/- 30.25 (n=5) |
| headline_gap_pct | 39.48 +/- 6.43 (n=5) | 21.67 +/- 10.86 (n=5) |
| headline_gap_r2_pct | 42.32 +/- 7.37 (n=5) | 22.07 +/- 10.72 (n=5) |
| rolling10 | 952.07 +/- 89.02 (n=4) | 633.47 +/- 44.15 (n=5) |
| voi_rolling10 | 122.91 +/- 59.13 (n=4) | 66.55 +/- 25.11 (n=5) |
| voi_pct_rolling10 | 14.93 +/- 7.55 (n=4) | 11.73 +/- 4.33 (n=5) |
| coord_rolling10 | 448.09 +/- 284.56 (n=4) | 100.13 +/- 114.34 (n=5) |
| coord_pct_rolling10 | 31.14 +/- 13.96 (n=4) | 12.46 +/- 13.00 (n=5) |
| foresight_share_rolling10 | 0.24 +/- 0.19 (n=4) | 0.51 +/- 0.38 (n=5) |
| coord_r2_rolling10 | 519.70 +/- 337.92 (n=4) | 103.71 +/- 111.54 (n=5) |

## targets = relaxed, basis = total

| quantity | r5_stress4h | usd4h_ebaas |
|---|---|---|
| best_rule | 1386.14 +/- 213.68 (n=5) | 829.92 +/- 109.09 (n=10) |
| r2 | 1459.21 +/- 255.53 (n=5) | 839.50 +/- 110.89 (n=10) |
| offline | 824.25 +/- 54.58 (n=5) | 580.59 +/- 18.39 (n=10) |
| headline_gap_pct | 40.04 +/- 6.37 (n=5) | 28.37 +/- 7.36 (n=10) |
| headline_gap_r2_pct | 42.85 +/- 7.39 (n=5) | 29.13 +/- 7.48 (n=10) |
| forecast10 | 932.47 +/- 62.46 (n=5) | 640.64 +/- 33.22 (n=10) |
| voi_forecast10 | 108.21 +/- 33.38 (n=5) | 60.05 +/- 23.19 (n=10) |
| voi_pct_forecast10 | 13.17 +/- 4.08 (n=5) | 10.30 +/- 3.96 (n=10) |
| coord_forecast10 | 453.68 +/- 187.70 (n=5) | 189.27 +/- 95.52 (n=10) |
| coord_pct_forecast10 | 32.08 +/- 8.76 (n=5) | 20.97 +/- 8.73 (n=10) |
| foresight_share_forecast10 | 0.21 +/- 0.10 (n=5) | 0.32 +/- 0.21 (n=10) |
| coord_r2_forecast10 | 526.74 +/- 222.31 (n=5) | 198.86 +/- 97.00 (n=10) |
| rolling0 | 1026.33 +/- 69.87 (n=5) | 688.78 +/- 37.18 (n=10) |
| voi_rolling0 | 202.08 +/- 27.83 (n=5) | 108.19 +/- 30.45 (n=10) |
| voi_pct_rolling0 | 24.53 +/- 3.12 (n=5) | 18.63 +/- 5.18 (n=10) |
| coord_rolling0 | 359.81 +/- 160.11 (n=5) | 141.13 +/- 99.75 (n=10) |
| coord_pct_rolling0 | 25.36 +/- 7.85 (n=5) | 14.97 +/- 9.54 (n=10) |
| foresight_share_rolling0 | 0.37 +/- 0.11 (n=5) | 0.57 +/- 0.28 (n=10) |
| coord_r2_rolling0 | 432.88 +/- 196.87 (n=5) | 150.72 +/- 97.55 (n=10) |
| rolling10 | 942.18 +/- 63.99 (n=5) | 647.38 +/- 31.40 (n=10) |
| voi_rolling10 | 117.93 +/- 44.89 (n=5) | 66.79 +/- 23.41 (n=10) |
| voi_pct_rolling10 | 14.38 +/- 5.67 (n=5) | 11.50 +/- 3.96 (n=10) |
| coord_rolling10 | 443.96 +/- 192.88 (n=5) | 182.53 +/- 101.74 (n=10) |
| coord_pct_rolling10 | 31.33 +/- 9.45 (n=5) | 20.00 +/- 9.18 (n=10) |
| foresight_share_rolling10 | 0.23 +/- 0.13 (n=5) | 0.36 +/- 0.20 (n=10) |
| coord_r2_rolling10 | 517.03 +/- 228.62 (n=5) | 192.12 +/- 101.81 (n=10) |
| rolling20 | 946.59 +/- 63.71 (n=5) | 618.82 +/- 26.57 (n=10) |
| voi_rolling20 | 122.34 +/- 84.97 (n=5) | 38.23 +/- 19.86 (n=10) |
| voi_pct_rolling20 | 15.13 +/- 11.37 (n=5) | 6.60 +/- 3.46 (n=10) |
| coord_rolling20 | 439.55 +/- 222.34 (n=5) | 211.10 +/- 92.17 (n=10) |
| coord_pct_rolling20 | 30.80 +/- 12.42 (n=5) | 23.72 +/- 7.79 (n=10) |
| foresight_share_rolling20 | 0.24 +/- 0.24 (n=5) | 0.19 +/- 0.16 (n=10) |
| coord_r2_rolling20 | 512.62 +/- 264.91 (n=5) | 220.68 +/- 94.25 (n=10) |
| battery_plan_value | 9.71 +/- 18.71 (n=5) | 6.74 +/- 15.09 (n=10) |

## targets = written, basis = total

| quantity | r5_stress4h | usd4h_ebaas |
|---|---|---|
| best_rule | 1386.14 +/- 213.68 (n=5) | 732.73 +/- 137.01 (n=5) |
| r2 | 1459.21 +/- 255.53 (n=5) | 736.38 +/- 136.54 (n=5) |
| offline | 831.67 +/- 57.41 (n=5) | 565.84 +/- 30.26 (n=5) |
| headline_gap_pct | 39.51 +/- 6.42 (n=5) | 21.73 +/- 10.86 (n=5) |
| headline_gap_r2_pct | 42.35 +/- 7.36 (n=5) | 22.13 +/- 10.71 (n=5) |
| rolling10 | 950.19 +/- 88.79 (n=4) | 632.32 +/- 44.15 (n=5) |
| voi_rolling10 | 122.19 +/- 59.26 (n=4) | 66.49 +/- 25.10 (n=5) |
| voi_pct_rolling10 | 14.87 +/- 7.59 (n=4) | 11.74 +/- 4.33 (n=5) |
| coord_rolling10 | 448.73 +/- 284.75 (n=4) | 100.41 +/- 114.36 (n=5) |
| coord_pct_rolling10 | 31.21 +/- 13.97 (n=4) | 12.51 +/- 13.01 (n=5) |
| foresight_share_rolling10 | 0.24 +/- 0.19 (n=4) | 0.50 +/- 0.37 (n=5) |
| coord_r2_rolling10 | 520.16 +/- 338.06 (n=4) | 104.06 +/- 111.49 (n=5) |

## price of recovery (written - relaxed, same policy and seed)

basis = total_end_adjusted

| quantity | r5_stress4h | usd4h_ebaas |
|---|---|---|
| recovery_offline | 6.73 +/- 10.60 (n=5) | -0.03 +/- 0.15 (n=5) |
| recovery_rolling10 | 0.00 +/- 0.00 (n=4) | 2.74 +/- 7.62 (n=5) |

basis = total

| quantity | r5_stress4h | usd4h_ebaas |
|---|---|---|
| recovery_offline | 7.42 +/- 10.60 (n=5) | 0.29 +/- 0.11 (n=5) |
| recovery_rolling10 | 0.00 +/- 0.00 (n=4) | 2.81 +/- 7.81 (n=5) |

