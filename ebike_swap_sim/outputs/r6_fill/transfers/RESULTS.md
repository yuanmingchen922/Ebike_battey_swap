# R6 transfers -- value of transfers and hub separation under P 60, w 18, v 15

r5_x2_transfers design on the repriced usd4h (eBaaS) instances, seeds 0-4; aggregated ILP, Threads 3, Seed 0, TimeLimit 300 s; libraries price-checked.  Means with exact Student-t 95 % half-widths over seeds; every difference paired per seed.  `RESULTS_x2.md` holds the round-5 report layout on these records.

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

## ILP per cell (seed means +- t 95 %)

| targets | layout | timetable | variant | metric | mean | ci95 | n |
|---|---|---|---|---|---|---|---|
| relaxed | colocated | any | none | total_end_adjusted | 580.984 | 48.440 | 5 |
| relaxed | colocated | any | none | gap_vs_best_rule_pct_end_adjusted | 24.979 | 10.943 | 5 |
| relaxed | colocated | any | none | served_share | 0.989 | 0.019 | 5 |
| relaxed | colocated | any | none | n_late_over_60min | 0 | 0 | 5 |
| relaxed | colocated | any | none | transfers_used | 0 | 0 | 5 |
| relaxed | colocated | any | none | gap | 0 | 0 | 5 |
| relaxed | colocated | cyclic | free | total_end_adjusted | 580.984 | 48.440 | 5 |
| relaxed | colocated | cyclic | free | gap_vs_best_rule_pct_end_adjusted | 24.979 | 10.943 | 5 |
| relaxed | colocated | cyclic | free | served_share | 0.989 | 0.019 | 5 |
| relaxed | colocated | cyclic | free | n_late_over_60min | 0 | 0 | 5 |
| relaxed | colocated | cyclic | free | transfers_used | 0 | 0 | 5 |
| relaxed | colocated | cyclic | free | gap | 0.000 | 0.000 | 5 |
| relaxed | colocated | r3 | free | total_end_adjusted | 580.983 | 48.440 | 5 |
| relaxed | colocated | r3 | free | gap_vs_best_rule_pct_end_adjusted | 24.979 | 10.944 | 5 |
| relaxed | colocated | r3 | free | served_share | 0.989 | 0.019 | 5 |
| relaxed | colocated | r3 | free | n_late_over_60min | 0 | 0 | 5 |
| relaxed | colocated | r3 | free | transfers_used | 0 | 0 | 5 |
| relaxed | colocated | r3 | free | gap | 0.000 | 0.000 | 5 |
| relaxed | separated_1hub | any | none | total_end_adjusted | 610.262 | 48.360 | 5 |
| relaxed | separated_1hub | any | none | gap_vs_best_rule_pct_end_adjusted | 24.098 | 10.695 | 5 |
| relaxed | separated_1hub | any | none | served_share | 0.989 | 0.019 | 5 |
| relaxed | separated_1hub | any | none | n_late_over_60min | 0 | 0 | 5 |
| relaxed | separated_1hub | any | none | transfers_used | 0 | 0 | 5 |
| relaxed | separated_1hub | any | none | gap | 0.001 | 0.002 | 5 |
| relaxed | separated_1hub | cyclic | free | total_end_adjusted | 610.262 | 48.360 | 5 |
| relaxed | separated_1hub | cyclic | free | gap_vs_best_rule_pct_end_adjusted | 24.098 | 10.695 | 5 |
| relaxed | separated_1hub | cyclic | free | served_share | 0.989 | 0.019 | 5 |
| relaxed | separated_1hub | cyclic | free | n_late_over_60min | 0 | 0 | 5 |
| relaxed | separated_1hub | cyclic | free | transfers_used | 0 | 0 | 5 |
| relaxed | separated_1hub | cyclic | free | gap | 0.000 | 0.000 | 5 |
| relaxed | separated_1hub | r3 | free | total_end_adjusted | 610.262 | 48.360 | 5 |
| relaxed | separated_1hub | r3 | free | gap_vs_best_rule_pct_end_adjusted | 24.098 | 10.695 | 5 |
| relaxed | separated_1hub | r3 | free | served_share | 0.989 | 0.019 | 5 |
| relaxed | separated_1hub | r3 | free | n_late_over_60min | 0 | 0 | 5 |
| relaxed | separated_1hub | r3 | free | transfers_used | 0 | 0 | 5 |
| relaxed | separated_1hub | r3 | free | gap | 0.000 | 0.000 | 5 |
| relaxed | separated_2hubs | any | none | total_end_adjusted | 638.748 | 47.952 | 5 |
| relaxed | separated_2hubs | any | none | gap_vs_best_rule_pct_end_adjusted | 23.365 | 10.496 | 5 |
| relaxed | separated_2hubs | any | none | served_share | 0.989 | 0.019 | 5 |
| relaxed | separated_2hubs | any | none | n_late_over_60min | 0 | 0 | 5 |
| relaxed | separated_2hubs | any | none | transfers_used | 0 | 0 | 5 |
| relaxed | separated_2hubs | any | none | gap | 0.000 | 0.000 | 5 |
| relaxed | separated_2hubs | cyclic | free | total_end_adjusted | 638.748 | 47.952 | 5 |
| relaxed | separated_2hubs | cyclic | free | gap_vs_best_rule_pct_end_adjusted | 23.365 | 10.496 | 5 |
| relaxed | separated_2hubs | cyclic | free | served_share | 0.989 | 0.019 | 5 |
| relaxed | separated_2hubs | cyclic | free | n_late_over_60min | 0 | 0 | 5 |
| relaxed | separated_2hubs | cyclic | free | transfers_used | 0 | 0 | 5 |
| relaxed | separated_2hubs | cyclic | free | gap | 0.000 | 0.000 | 5 |
| relaxed | separated_2hubs | r3 | free | total_end_adjusted | 638.748 | 47.952 | 5 |
| relaxed | separated_2hubs | r3 | free | gap_vs_best_rule_pct_end_adjusted | 23.365 | 10.496 | 5 |
| relaxed | separated_2hubs | r3 | free | served_share | 0.989 | 0.019 | 5 |
| relaxed | separated_2hubs | r3 | free | n_late_over_60min | 0 | 0 | 5 |
| relaxed | separated_2hubs | r3 | free | transfers_used | 0 | 0 | 5 |
| relaxed | separated_2hubs | r3 | free | gap | 0.001 | 0.003 | 5 |
| written | colocated | any | none | total_end_adjusted | 580.970 | 48.423 | 5 |
| written | colocated | any | none | gap_vs_best_rule_pct_end_adjusted | 24.981 | 10.941 | 5 |
| written | colocated | any | none | served_share | 0.989 | 0.019 | 5 |
| written | colocated | any | none | n_late_over_60min | 0 | 0 | 5 |
| written | colocated | any | none | transfers_used | 0 | 0 | 5 |
| written | colocated | any | none | gap | 0 | 0 | 5 |
| written | colocated | cyclic | free | total_end_adjusted | 580.970 | 48.423 | 5 |
| written | colocated | cyclic | free | gap_vs_best_rule_pct_end_adjusted | 24.981 | 10.941 | 5 |
| written | colocated | cyclic | free | served_share | 0.989 | 0.019 | 5 |
| written | colocated | cyclic | free | n_late_over_60min | 0 | 0 | 5 |
| written | colocated | cyclic | free | transfers_used | 0 | 0 | 5 |
| written | colocated | cyclic | free | gap | 0.001 | 0.003 | 5 |
| written | colocated | r3 | free | total_end_adjusted | 580.970 | 48.423 | 5 |
| written | colocated | r3 | free | gap_vs_best_rule_pct_end_adjusted | 24.981 | 10.941 | 5 |
| written | colocated | r3 | free | served_share | 0.989 | 0.019 | 5 |
| written | colocated | r3 | free | n_late_over_60min | 0 | 0 | 5 |
| written | colocated | r3 | free | transfers_used | 0 | 0 | 5 |
| written | colocated | r3 | free | gap | 0.000 | 0.000 | 5 |
| written | separated_1hub | any | none | total_end_adjusted | 681.893 | 84.451 | 5 |
| written | separated_1hub | any | none | gap_vs_best_rule_pct_end_adjusted | 15.646 | 7.545 | 5 |
| written | separated_1hub | any | none | served_share | 0.956 | 0.039 | 5 |
| written | separated_1hub | any | none | n_late_over_60min | 0 | 0 | 5 |
| written | separated_1hub | any | none | transfers_used | 0 | 0 | 5 |
| written | separated_1hub | any | none | gap | 0.003 | 0.008 | 5 |
| written | separated_1hub | cyclic | free | total_end_adjusted | 617.871 | 48.402 | 5 |
| written | separated_1hub | cyclic | free | gap_vs_best_rule_pct_end_adjusted | 23.150 | 10.807 | 5 |
| written | separated_1hub | cyclic | free | served_share | 0.989 | 0.019 | 5 |
| written | separated_1hub | cyclic | free | n_late_over_60min | 0 | 0 | 5 |
| written | separated_1hub | cyclic | free | transfers_used | 1 | 0 | 5 |
| written | separated_1hub | cyclic | free | gap | 0.003 | 0.006 | 5 |
| written | separated_1hub | r3 | free | total_end_adjusted | 632.535 | 48.607 | 5 |
| written | separated_1hub | r3 | free | gap_vs_best_rule_pct_end_adjusted | 21.312 | 11.202 | 5 |
| written | separated_1hub | r3 | free | served_share | 0.989 | 0.019 | 5 |
| written | separated_1hub | r3 | free | n_late_over_60min | 0 | 0 | 5 |
| written | separated_1hub | r3 | free | transfers_used | 1 | 0 | 5 |
| written | separated_1hub | r3 | free | gap | 0.019 | 0.014 | 5 |
| written | separated_2hubs | any | none | total_end_adjusted | 710.311 | 85.381 | 5 |
| written | separated_2hubs | any | none | gap_vs_best_rule_pct_end_adjusted | 15.230 | 7.123 | 5 |
| written | separated_2hubs | any | none | served_share | 0.950 | 0.045 | 5 |
| written | separated_2hubs | any | none | n_late_over_60min | 0 | 0 | 5 |
| written | separated_2hubs | any | none | transfers_used | 0 | 0 | 5 |
| written | separated_2hubs | any | none | gap | 0.002 | 0.005 | 5 |
| written | separated_2hubs | cyclic | free | total_end_adjusted | 645.527 | 48.442 | 5 |
| written | separated_2hubs | cyclic | free | gap_vs_best_rule_pct_end_adjusted | 22.558 | 10.513 | 5 |
| written | separated_2hubs | cyclic | free | served_share | 0.989 | 0.019 | 5 |
| written | separated_2hubs | cyclic | free | n_late_over_60min | 0 | 0 | 5 |
| written | separated_2hubs | cyclic | free | transfers_used | 1 | 0 | 5 |
| written | separated_2hubs | cyclic | free | gap | 0.001 | 0.003 | 5 |
| written | separated_2hubs | r3 | free | total_end_adjusted | 661.401 | 48.289 | 5 |
| written | separated_2hubs | r3 | free | gap_vs_best_rule_pct_end_adjusted | 20.638 | 10.917 | 5 |
| written | separated_2hubs | r3 | free | served_share | 0.989 | 0.019 | 5 |
| written | separated_2hubs | r3 | free | n_late_over_60min | 0 | 0 | 5 |
| written | separated_2hubs | r3 | free | transfers_used | 1 | 0 | 5 |
| written | separated_2hubs | r3 | free | gap | 0.019 | 0.013 | 5 |

## Paired differences (USD per window; per seed, then mean +- t 95 %)

| targets | layout | timetable | metric | mean_diff | ci95 | n_pairs |
|---|---|---|---|---|---|---|
| relaxed | colocated | r3 | value_of_transfers | 0 | 0 | 5 |
| relaxed | colocated | cyclic | value_of_transfers | 0 | 0 | 5 |
| relaxed | colocated | cyclic-r3 | cyclic_minus_r3 | 0 | 0 | 5 |
| relaxed | colocated | r3 | value_of_transfers_end_adjusted | 0.002 | 0.005 | 5 |
| relaxed | colocated | cyclic | value_of_transfers_end_adjusted | 0 | 0 | 5 |
| relaxed | colocated | cyclic-r3 | cyclic_minus_r3_end_adjusted | 0.002 | 0.005 | 5 |
| relaxed | separated_1hub | r3 | value_of_transfers | 0 | 0 | 5 |
| relaxed | separated_1hub | cyclic | value_of_transfers | 0 | 0 | 5 |
| relaxed | separated_1hub | cyclic-r3 | cyclic_minus_r3 | 0 | 0 | 5 |
| relaxed | separated_1hub | any/none | separation_cost | 29.196 | 0.045 | 5 |
| relaxed | separated_1hub | r3/free | separation_cost | 29.196 | 0.045 | 5 |
| relaxed | separated_1hub | cyclic/free | separation_cost | 29.196 | 0.045 | 5 |
| relaxed | separated_1hub | r3 | value_of_transfers_end_adjusted | 0 | 0 | 5 |
| relaxed | separated_1hub | cyclic | value_of_transfers_end_adjusted | 0 | 0 | 5 |
| relaxed | separated_1hub | cyclic-r3 | cyclic_minus_r3_end_adjusted | 0 | 0 | 5 |
| relaxed | separated_1hub | any/none | separation_cost_end_adjusted | 29.277 | 0.154 | 5 |
| relaxed | separated_1hub | r3/free | separation_cost_end_adjusted | 29.279 | 0.158 | 5 |
| relaxed | separated_1hub | cyclic/free | separation_cost_end_adjusted | 29.277 | 0.154 | 5 |
| relaxed | separated_2hubs | r3 | value_of_transfers | 0 | 0 | 5 |
| relaxed | separated_2hubs | cyclic | value_of_transfers | 0 | 0 | 5 |
| relaxed | separated_2hubs | cyclic-r3 | cyclic_minus_r3 | 0 | 0 | 5 |
| relaxed | separated_2hubs | any/none | separation_cost | 57.757 | 1.073 | 5 |
| relaxed | separated_2hubs | r3/free | separation_cost | 57.757 | 1.073 | 5 |
| relaxed | separated_2hubs | cyclic/free | separation_cost | 57.757 | 1.073 | 5 |
| relaxed | separated_2hubs | r3 | value_of_transfers_end_adjusted | 0 | 0 | 5 |
| relaxed | separated_2hubs | cyclic | value_of_transfers_end_adjusted | 0 | 0 | 5 |
| relaxed | separated_2hubs | cyclic-r3 | cyclic_minus_r3_end_adjusted | 0 | 0 | 5 |
| relaxed | separated_2hubs | any/none | separation_cost_end_adjusted | 57.764 | 1.075 | 5 |
| relaxed | separated_2hubs | r3/free | separation_cost_end_adjusted | 57.766 | 1.071 | 5 |
| relaxed | separated_2hubs | cyclic/free | separation_cost_end_adjusted | 57.764 | 1.075 | 5 |
| written | colocated | r3 | value_of_transfers | 0 | 0 | 5 |
| written | colocated | cyclic | value_of_transfers | 0 | 0 | 5 |
| written | colocated | cyclic-r3 | cyclic_minus_r3 | 0 | 0 | 5 |
| written | colocated | r3 | value_of_transfers_end_adjusted | 0 | 0 | 5 |
| written | colocated | cyclic | value_of_transfers_end_adjusted | 0 | 0 | 5 |
| written | colocated | cyclic-r3 | cyclic_minus_r3_end_adjusted | 0 | 0 | 5 |
| written-relaxed | colocated | any/none | price_of_recovery | 0.274 | 0.066 | 5 |
| written-relaxed | colocated | any/none | price_of_recovery_end_adjusted | -0.014 | 0.062 | 5 |
| written-relaxed | colocated | r3/free | price_of_recovery | 0.274 | 0.066 | 5 |
| written-relaxed | colocated | r3/free | price_of_recovery_end_adjusted | -0.012 | 0.062 | 5 |
| written-relaxed | colocated | cyclic/free | price_of_recovery | 0.274 | 0.066 | 5 |
| written-relaxed | colocated | cyclic/free | price_of_recovery_end_adjusted | -0.014 | 0.062 | 5 |
| written | separated_1hub | r3 | value_of_transfers | 49.243 | 42.899 | 5 |
| written | separated_1hub | cyclic | value_of_transfers | 63.866 | 43.074 | 5 |
| written | separated_1hub | cyclic-r3 | cyclic_minus_r3 | -14.623 | 0.706 | 5 |
| written | separated_1hub | any/none | separation_cost | 100.800 | 43.637 | 5 |
| written | separated_1hub | r3/free | separation_cost | 51.557 | 1.013 | 5 |
| written | separated_1hub | cyclic/free | separation_cost | 36.934 | 0.985 | 5 |
| written | separated_1hub | r3 | value_of_transfers_end_adjusted | 49.358 | 42.885 | 5 |
| written | separated_1hub | cyclic | value_of_transfers_end_adjusted | 64.022 | 43.061 | 5 |
| written | separated_1hub | cyclic-r3 | cyclic_minus_r3_end_adjusted | -14.664 | 0.691 | 5 |
| written | separated_1hub | any/none | separation_cost_end_adjusted | 100.923 | 43.617 | 5 |
| written | separated_1hub | r3/free | separation_cost_end_adjusted | 51.564 | 1.003 | 5 |
| written | separated_1hub | cyclic/free | separation_cost_end_adjusted | 36.900 | 0.947 | 5 |
| written-relaxed | separated_1hub | any/none | price_of_recovery | 71.878 | 43.613 | 5 |
| written-relaxed | separated_1hub | any/none | price_of_recovery_end_adjusted | 71.631 | 43.579 | 5 |
| written-relaxed | separated_1hub | r3/free | price_of_recovery | 22.636 | 0.982 | 5 |
| written-relaxed | separated_1hub | r3/free | price_of_recovery_end_adjusted | 22.273 | 0.900 | 5 |
| written-relaxed | separated_1hub | cyclic/free | price_of_recovery | 8.013 | 0.988 | 5 |
| written-relaxed | separated_1hub | cyclic/free | price_of_recovery_end_adjusted | 7.609 | 0.904 | 5 |
| written | separated_2hubs | r3 | value_of_transfers | 48.778 | 43.631 | 5 |
| written | separated_2hubs | cyclic | value_of_transfers | 64.645 | 43.464 | 5 |
| written | separated_2hubs | cyclic-r3 | cyclic_minus_r3 | -15.866 | 0.266 | 5 |
| written | separated_2hubs | any/none | separation_cost | 129.221 | 44.301 | 5 |
| written | separated_2hubs | r3/free | separation_cost | 80.443 | 1.094 | 5 |
| written | separated_2hubs | cyclic/free | separation_cost | 64.576 | 1.183 | 5 |
| written | separated_2hubs | r3 | value_of_transfers_end_adjusted | 48.910 | 43.611 | 5 |
| written | separated_2hubs | cyclic | value_of_transfers_end_adjusted | 64.783 | 43.428 | 5 |
| written | separated_2hubs | cyclic-r3 | cyclic_minus_r3_end_adjusted | -15.874 | 0.279 | 5 |
| written | separated_2hubs | any/none | separation_cost_end_adjusted | 129.340 | 44.272 | 5 |
| written | separated_2hubs | r3/free | separation_cost_end_adjusted | 80.430 | 1.094 | 5 |
| written | separated_2hubs | cyclic/free | separation_cost_end_adjusted | 64.557 | 1.189 | 5 |
| written-relaxed | separated_2hubs | any/none | price_of_recovery | 71.738 | 44.955 | 5 |
| written-relaxed | separated_2hubs | any/none | price_of_recovery_end_adjusted | 71.562 | 44.940 | 5 |
| written-relaxed | separated_2hubs | r3/free | price_of_recovery | 22.960 | 1.840 | 5 |
| written-relaxed | separated_2hubs | r3/free | price_of_recovery_end_adjusted | 22.653 | 1.850 | 5 |
| written-relaxed | separated_2hubs | cyclic/free | price_of_recovery | 7.094 | 1.860 | 5 |
| written-relaxed | separated_2hubs | cyclic/free | price_of_recovery_end_adjusted | 6.779 | 1.879 | 5 |
| relaxed | colocated | r3 | r5_transfer_minus_r2 | 88.963 | 31.942 | 5 |
| relaxed | colocated | r3 | r2_reorder_minus_r2 | 123.971 | 34.684 | 5 |
| relaxed | colocated | r3 | r5_minus_r2 | 106.020 | 47.375 | 5 |
| relaxed | colocated | r3 | r5_range_minus_r2 | 23.400 | 34.511 | 5 |
| relaxed | colocated | cyclic | r5_transfer_minus_r2 | 30.091 | 16.168 | 5 |
| relaxed | colocated | cyclic | r2_reorder_minus_r2 | 33.089 | 32.936 | 5 |
| relaxed | colocated | cyclic | r5_minus_r2 | 53.818 | 30.012 | 5 |
| relaxed | colocated | cyclic | r5_range_minus_r2 | 23.400 | 34.511 | 5 |
| relaxed | separated_1hub | r3 | r5_transfer_minus_r2 | 70.764 | 20.768 | 5 |
| relaxed | separated_1hub | r3 | r2_reorder_minus_r2 | 116.209 | 50.296 | 5 |
| relaxed | separated_1hub | r3 | r5_minus_r2 | 108.777 | 63.477 | 5 |
| relaxed | separated_1hub | r3 | r5_range_minus_r2 | 23.775 | 33.897 | 5 |
| relaxed | separated_1hub | cyclic | r5_transfer_minus_r2 | 59.088 | 37.065 | 5 |
| relaxed | separated_1hub | cyclic | r2_reorder_minus_r2 | 10.483 | 10.776 | 5 |
| relaxed | separated_1hub | cyclic | r5_minus_r2 | 75.216 | 62.069 | 5 |
| relaxed | separated_1hub | cyclic | r5_range_minus_r2 | 23.775 | 33.897 | 5 |
| relaxed | separated_2hubs | r3 | r5_transfer_minus_r2 | 74.632 | 13.361 | 5 |
| relaxed | separated_2hubs | r3 | r2_reorder_minus_r2 | 115.963 | 50.401 | 5 |
| relaxed | separated_2hubs | r3 | r5_minus_r2 | 108.321 | 63.203 | 5 |
| relaxed | separated_2hubs | r3 | r5_range_minus_r2 | 23.775 | 33.897 | 5 |
| relaxed | separated_2hubs | cyclic | r5_transfer_minus_r2 | 51.848 | 53.664 | 5 |
| relaxed | separated_2hubs | cyclic | r2_reorder_minus_r2 | 10.564 | 7.964 | 5 |
| relaxed | separated_2hubs | cyclic | r5_minus_r2 | 34.404 | 37.979 | 5 |
| relaxed | separated_2hubs | cyclic | r5_range_minus_r2 | 23.775 | 33.897 | 5 |
| written | colocated | r3 | r5_transfer_minus_r2 | 123.015 | 23.045 | 5 |
| written | colocated | r3 | r2_reorder_minus_r2 | 123.971 | 34.684 | 5 |
| written | colocated | r3 | r5_minus_r2 | 131.413 | 34.745 | 5 |
| written | colocated | r3 | r5_range_minus_r2 | 23.400 | 34.511 | 5 |
| written | colocated | cyclic | r5_transfer_minus_r2 | 34.707 | 16.669 | 5 |
| written | colocated | cyclic | r2_reorder_minus_r2 | 33.089 | 32.936 | 5 |
| written | colocated | cyclic | r5_minus_r2 | 60.914 | 55.342 | 5 |
| written | colocated | cyclic | r5_range_minus_r2 | 23.400 | 34.511 | 5 |
| written | separated_1hub | r3 | r5_transfer_minus_r2 | 70.764 | 20.768 | 5 |
| written | separated_1hub | r3 | r2_reorder_minus_r2 | 116.209 | 50.296 | 5 |
| written | separated_1hub | r3 | r5_minus_r2 | 108.777 | 63.477 | 5 |
| written | separated_1hub | r3 | r5_range_minus_r2 | 23.775 | 33.897 | 5 |
| written | separated_1hub | cyclic | r5_transfer_minus_r2 | 59.088 | 37.065 | 5 |
| written | separated_1hub | cyclic | r2_reorder_minus_r2 | 10.483 | 10.776 | 5 |
| written | separated_1hub | cyclic | r5_minus_r2 | 75.216 | 62.069 | 5 |
| written | separated_1hub | cyclic | r5_range_minus_r2 | 23.775 | 33.897 | 5 |
| written | separated_2hubs | r3 | r5_transfer_minus_r2 | 74.632 | 13.361 | 5 |
| written | separated_2hubs | r3 | r2_reorder_minus_r2 | 115.963 | 50.401 | 5 |
| written | separated_2hubs | r3 | r5_minus_r2 | 108.321 | 63.203 | 5 |
| written | separated_2hubs | r3 | r5_range_minus_r2 | 23.775 | 33.897 | 5 |
| written | separated_2hubs | cyclic | r5_transfer_minus_r2 | 51.848 | 53.664 | 5 |
| written | separated_2hubs | cyclic | r2_reorder_minus_r2 | 10.564 | 7.964 | 5 |
| written | separated_2hubs | cyclic | r5_minus_r2 | 34.404 | 37.979 | 5 |
| written | separated_2hubs | cyclic | r5_range_minus_r2 | 23.775 | 33.897 | 5 |

## Anomalies

* 16 ILP row(s) not OPTIMAL (max gap 0.0289)

Files: records.jsonl, results.csv, summary.csv (long), paired.csv, RESULTS_x2.md, figs/, instances/, schedules/.
