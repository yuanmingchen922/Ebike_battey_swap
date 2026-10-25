# X1 -- headline re-validation (round 5)

Gap = 100 (baseline - ILP) / baseline per instance, mean with 95 % t-CI. Headline = eBaaS energy, per-instance best rule (min over r2, r5_range, r5_transfer when services exist, r5; either target copy), relaxed targets (rho 0, R_end 0), end-adjusted totals (M1). ILP settings (Threads, TimeLimit s, Seed, aggregated flow O1) used: [[3, 300.0, 0, True]]. nyc4h gaps are lower bounds (PRUNING_NYC restricts only the ILP). Legacy ILP values are the stored round-3 rows (per-bike model, raw totals only).

* **usd4h: 27.2 % +/- 6.0** (n = 30, positive on 30), round 3: 29.6 %. Price of recovery (written - relaxed ILP): 0.38 USD raw, -0.04 USD end-adjusted. C_end_adjust best rule 0.95 / ILP relaxed 1.39 USD. Orders identical to legacy: 30/30.
* **nyc4h: 27.4 % +/- 7.1** (n = 10, positive on 10), round 3: 31.8 %. Price of recovery (written - relaxed ILP): 0.45 USD raw, -0.04 USD end-adjusted. C_end_adjust best rule 0.90 / ILP relaxed 1.41 USD. Orders identical to legacy: 10/10.

## Survival path (cells where all five stages exist)

| group | stage | label | mean_pct_common | ci95_pct_common | n_common | step_pts_common | survival_vs_S0_common | mean_pct | n | n_positive |
|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | S0 | round 3: legacy energy, r2 rule, written targets, raw total | 29.55 | 5.61 | 30 | - | 1 | 29.55 | 30 | 30 |
| usd4h | S1 | (a) eBaaS energy calibration | 28.91 | 5.69 | 30 | -0.64 | 0.98 | 28.91 | 30 | 30 |
| usd4h | S2 | (b) + per-instance best rule | 27.21 | 5.96 | 30 | -1.70 | 0.92 | 27.21 | 30 | 30 |
| usd4h | S3 | (c1) + relaxed targets (rho 0, R_end 0), raw total | 27.25 | 5.95 | 30 | 0.04 | 0.92 | 27.25 | 30 | 30 |
| usd4h | S4 | (c2) + end-state adjustment = X1 headline | 27.17 | 5.96 | 30 | -0.08 | 0.92 | 27.17 | 30 | 30 |
| usd4h x0.75 | S0 | round 3: legacy energy, r2 rule, written targets, raw total | 15.36 | 7.28 | 10 | - | 1 | 15.36 | 10 | 10 |
| usd4h x0.75 | S1 | (a) eBaaS energy calibration | 13.25 | 4.10 | 10 | -2.10 | 0.86 | 13.25 | 10 | 10 |
| usd4h x0.75 | S2 | (b) + per-instance best rule | 9.83 | 2.89 | 10 | -3.42 | 0.64 | 9.83 | 10 | 10 |
| usd4h x0.75 | S3 | (c1) + relaxed targets (rho 0, R_end 0), raw total | 9.87 | 2.88 | 10 | 0.04 | 0.64 | 9.87 | 10 | 10 |
| usd4h x0.75 | S4 | (c2) + end-state adjustment = X1 headline | 9.78 | 2.88 | 10 | -0.09 | 0.64 | 9.78 | 10 | 10 |
| usd4h x1 | S0 | round 3: legacy energy, r2 rule, written targets, raw total | 31.18 | 9.05 | 10 | - | 1 | 31.18 | 10 | 10 |
| usd4h x1 | S1 | (a) eBaaS energy calibration | 29.08 | 7.48 | 10 | -2.10 | 0.93 | 29.08 | 10 | 10 |
| usd4h x1 | S2 | (b) + per-instance best rule | 28.32 | 7.35 | 10 | -0.76 | 0.91 | 28.32 | 10 | 10 |
| usd4h x1 | S3 | (c1) + relaxed targets (rho 0, R_end 0), raw total | 28.37 | 7.35 | 10 | 0.05 | 0.91 | 28.37 | 10 | 10 |
| usd4h x1 | S4 | (c2) + end-state adjustment = X1 headline | 28.28 | 7.36 | 10 | -0.09 | 0.91 | 28.28 | 10 | 10 |
| usd4h x1.5 | S0 | round 3: legacy energy, r2 rule, written targets, raw total | 42.11 | 5.66 | 10 | - | 1 | 42.11 | 10 | 10 |
| usd4h x1.5 | S1 | (a) eBaaS energy calibration | 44.40 | 5.88 | 10 | 2.29 | 1.05 | 44.40 | 10 | 10 |
| usd4h x1.5 | S2 | (b) + per-instance best rule | 43.47 | 5.86 | 10 | -0.93 | 1.03 | 43.47 | 10 | 10 |
| usd4h x1.5 | S3 | (c1) + relaxed targets (rho 0, R_end 0), raw total | 43.50 | 5.86 | 10 | 0.03 | 1.03 | 43.50 | 10 | 10 |
| usd4h x1.5 | S4 | (c2) + end-state adjustment = X1 headline | 43.45 | 5.86 | 10 | -0.05 | 1.03 | 43.45 | 10 | 10 |
| nyc4h | S0 | round 3: legacy energy, r2 rule, written targets, raw total | 31.82 | 8.19 | 10 | - | 1 | 31.82 | 10 | 10 |
| nyc4h | S1 | (a) eBaaS energy calibration | 29.45 | 8.04 | 10 | -2.37 | 0.93 | 29.45 | 10 | 10 |
| nyc4h | S2 | (b) + per-instance best rule | 27.40 | 7.10 | 10 | -2.05 | 0.86 | 27.40 | 10 | 10 |
| nyc4h | S3 | (c1) + relaxed targets (rho 0, R_end 0), raw total | 27.46 | 7.11 | 10 | 0.05 | 0.86 | 27.46 | 10 | 10 |
| nyc4h | S4 | (c2) + end-state adjustment = X1 headline | 27.37 | 7.11 | 10 | -0.09 | 0.86 | 27.37 | 10 | 10 |

## Shapley decomposition of S0 -> S3 (raw totals) plus the end-state step

| group | n | S0_round3_pct | a_calibration_pts | b_best_rule_pts | c1_relaxed_targets_pts | c2_end_adjust_pts | S4_headline_pct | survival_share |
|---|---|---|---|---|---|---|---|---|
| usd4h | 30 | 29.55 | -0.41 | -1.93 | 0.04 | -0.08 | 27.17 | 0.92 |
| usd4h x0.75 | 10 | 15.36 | -2.22 | -3.31 | 0.04 | -0.09 | 9.78 | 0.64 |
| usd4h x1 | 10 | 31.18 | -1.35 | -1.51 | 0.04 | -0.09 | 28.28 | 0.91 |
| usd4h x1.5 | 10 | 42.11 | 2.34 | -0.98 | 0.03 | -0.05 | 43.45 | 1.03 |
| nyc4h | 10 | 31.82 | -2.20 | -2.20 | 0.04 | -0.09 | 27.37 | 0.86 |

## Headline difference by cost component (eBaaS, USD per instance)

| group | n | diff_total_end_adjusted | diff_C_setup | diff_C_elec | diff_C_travel | diff_unserved | diff_response | diff_lateness | diff_C_reb | diff_C_end_adjust |
|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 30 | 364.22 | 0 | 0.66 | 1.05 | 83 | 96.15 | 183.80 | 0 | -0.44 |
| nyc4h | 10 | 240.98 | 0 | 0.65 | 0.98 | 39 | 82.65 | 118.20 | 0 | -0.50 |

## A3 metric pack (means)

| family | calib | method | n | total | total_end_adjusted | C_end_adjust | served_share | n_unserved | n_late | bike_km | r5_n_swaps | r5_bsr | r5_min_sbur | r5_mean_sbur | r5_outage_rate | r5_n_energy_refused_orders | r5_mean_station_time_min | r5_mean_detour_km_per_swap | r5_empty_km_share | r5_empty_km_per_bike_hour | r5_peak_kw_network | r5_kwh_purchased | r5_batteries_saved_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h | ebaas | r2 | 10 | 864.682 | 865.578 | 0.895 | 0.903 | 3.500 | 15.200 | 120.900 | 7.700 | 0.832 | 0.500 | 0.856 | 0.017 | 0 | 11.555 | 1.047 | 0.074 | 0.374 | 1.400 | 1.889 | 1.800 |
| nyc4h | ebaas | r5_range | 10 | 845.753 | 846.691 | 0.938 | 0.894 | 3.800 | 15.500 | 120.735 | 9.700 | 0.830 | 0.800 | 1.078 | 0 | 0 | 9.984 | 1.176 | 0.106 | 0.534 | 1.633 | 2.328 | 0.700 |
| nyc4h | ebaas | r5 | 10 | 845.753 | 846.691 | 0.938 | 0.894 | 3.800 | 15.500 | 120.735 | 9.700 | 0.830 | 0.800 | 1.078 | 0 | 0 | 9.984 | 1.176 | 0.106 | 0.534 | 1.633 | 2.328 | 0.700 |
| nyc4h | ebaas | best_rule | 10 | 833.840 | 834.743 | 0.903 | 0.906 | 3.400 | 14.700 | 119.565 | 8.800 | 0.857 | 0.733 | 0.978 | 0.017 | 0 | 10.372 | 1.102 | 0.091 | 0.459 | 1.500 | 2.100 | 1.100 |
| nyc4h | ebaas | ilp_written | 10 | 592.813 | 593.728 | 0.915 | 0.939 | 2.200 | 0.700 | 111.345 | 8.200 | 0.529 | 0.500 | 0.911 | 0.317 | 0.300 | 17.566 | 0.640 | 0.078 | 0.364 | 1.067 | 1.506 | 3.100 |
| nyc4h | ebaas | ilp_relaxed | 10 | 592.361 | 593.767 | 1.406 | 0.942 | 2.100 | 0.800 | 111.420 | 8.300 | 0.534 | 0.767 | 0.922 | 0.317 | 0.100 | 23.193 | 0.685 | 0.078 | 0.362 | 0.067 | 0.064 | 0.900 |
| nyc4h | legacy | r2 | 10 | 1013.696 | 1014.317 | 0.620 | 0.839 | 5.800 | 17.800 | 109.920 | 7.100 | 0.954 | 0.367 | 0.789 | 0.033 | 0.100 | 5.792 | 1.219 | 0.081 | 0.369 | 2.533 | 2.456 | 2.900 |
| nyc4h | legacy | r5_range | 10 | 990.108 | 990.750 | 0.642 | 0.850 | 5.400 | 17 | 111.930 | 9.500 | 0.766 | 0.667 | 1.056 | 0 | 0 | 11.629 | 1.007 | 0.087 | 0.404 | 2.267 | 2.989 | 2.400 |
| nyc4h | legacy | r5 | 10 | 990.108 | 990.750 | 0.642 | 0.850 | 5.400 | 17 | 111.930 | 9.500 | 0.766 | 0.667 | 1.056 | 0 | 0 | 11.629 | 1.007 | 0.087 | 0.404 | 2.267 | 2.989 | 2.400 |
| nyc4h | legacy | best_rule | 10 | 982.516 | 983.133 | 0.617 | 0.850 | 5.400 | 16.600 | 110.550 | 8.400 | 0.818 | 0.567 | 0.933 | 0.017 | 0 | 9.961 | 1.098 | 0.083 | 0.383 | 2.400 | 2.750 | 2.500 |
| usd4h | ebaas | r2 | 30 | 1050.175 | 1051.114 | 0.939 | 0.862 | 6.867 | 14.400 | 117.990 | 8.200 | 0.897 | 0.444 | 0.911 | 0.117 | 0.933 | 7.206 | 1.024 | 0.079 | 0.391 | 1.389 | 2.019 | 2 |
| usd4h | ebaas | r5_range | 30 | 1043.683 | 1044.608 | 0.924 | 0.849 | 7.467 | 13.567 | 121.340 | 10.267 | 0.915 | 0.778 | 1.141 | 0.039 | 0.200 | 5.567 | 1.161 | 0.104 | 0.533 | 1.711 | 2.508 | 0.700 |
| usd4h | ebaas | r5 | 30 | 1043.683 | 1044.608 | 0.924 | 0.849 | 7.467 | 13.567 | 121.340 | 10.267 | 0.915 | 0.778 | 1.141 | 0.039 | 0.200 | 5.567 | 1.161 | 0.104 | 0.533 | 1.711 | 2.508 | 0.700 |
| usd4h | ebaas | best_rule | 30 | 1030.437 | 1031.391 | 0.954 | 0.854 | 7.233 | 13.300 | 119.445 | 9.467 | 0.920 | 0.622 | 1.052 | 0.089 | 0.767 | 6.048 | 1.079 | 0.093 | 0.466 | 1.578 | 2.293 | 1.200 |
| usd4h | ebaas | ilp_written | 30 | 666.156 | 667.130 | 0.975 | 0.910 | 4.500 | 0.400 | 110.500 | 7.333 | 0.731 | 0.378 | 0.815 | 0.367 | 0.600 | 7.813 | 0.753 | 0.154 | 0.703 | 0.833 | 1.331 | 2.967 |
| usd4h | ebaas | ilp_relaxed | 30 | 665.778 | 667.171 | 1.393 | 0.910 | 4.467 | 0.400 | 110.685 | 8.100 | 0.744 | 0.600 | 0.900 | 0.350 | 0.333 | 7.719 | 0.688 | 0.159 | 0.721 | 0.200 | 0.238 | 1.600 |
| usd4h | legacy | r2 | 30 | 1166.743 | 1167.366 | 0.623 | 0.822 | 8.567 | 16.200 | 112.240 | 7.533 | 0.928 | 0.289 | 0.837 | 0.028 | 0.033 | 5.362 | 0.989 | 0.072 | 0.336 | 2.511 | 2.669 | 3.033 |
| usd4h | legacy | r5_range | 30 | 1142.846 | 1143.471 | 0.625 | 0.817 | 8.800 | 15.567 | 113.905 | 9.800 | 0.935 | 0.433 | 1.089 | 0 | 0 | 5.339 | 0.974 | 0.088 | 0.421 | 2.489 | 3.304 | 2.267 |
| usd4h | legacy | r5 | 30 | 1142.846 | 1143.471 | 0.625 | 0.817 | 8.800 | 15.567 | 113.905 | 9.800 | 0.935 | 0.433 | 1.089 | 0 | 0 | 5.339 | 0.974 | 0.088 | 0.421 | 2.489 | 3.304 | 2.267 |
| usd4h | legacy | best_rule | 30 | 1135.124 | 1135.733 | 0.609 | 0.822 | 8.633 | 15.400 | 113.615 | 9.233 | 0.929 | 0.400 | 1.026 | 0.006 | 0.033 | 5.370 | 0.976 | 0.085 | 0.403 | 2.511 | 3.189 | 2.400 |

## Solver (eBaaS ILP rows)

| family | targets | n | statuses | mean_runtime_s | max_runtime_s | max_mip_gap | mip_start_accepted_share | check_ok_all | mean_n_vars | mean_n_arcs |
|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h | relaxed | 10 | {"OPTIMAL": 10} | 13.60 | 19.49 | 0.00 | 1 | True | 179325.40 | 1131439.30 |
| nyc4h | written | 10 | {"OPTIMAL": 10} | 19.69 | 36.25 | 0.00 | 0.60 | True | 179325.40 | 1131439.30 |
| usd4h | relaxed | 30 | {"OPTIMAL": 30} | 37.47 | 111.92 | 0.00 | 1 | True | 374213.90 | 2332523.63 |
| usd4h | written | 30 | {"OPTIMAL": 30} | 71.21 | 211.82 | 0.00 | 0.57 | True | 374213.90 | 2332523.63 |

## Anomalies

* none

![stages](stages.png)

Files: records.jsonl, results.csv, per_instance.csv, stages.csv, shapley.csv, components.csv, metric_pack.csv, solver.csv, summary.json, instances/.
