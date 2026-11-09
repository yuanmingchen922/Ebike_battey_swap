# R8 fifteen-site study -- r8_k15_sp

Family `manhattan15`, k = 15, unit option ('SC', 3, 2), lower level = rule-based rider module (`baseline.run_baseline` variant r2, every schedule certified by `evaluate.check`), open-sites tier, union arc library; search on scenarios [0, 2, 4, 6, 8, 10], final table on 12 in-sample + 12 held-out scenarios.  Values are USD per evening (window-allocated set-up + operating cost).  The best layout is 'best found under the rule follower' (no certificate; design section 5).  Power: shared supply group of all sites capped at 1000 kW, each site at 1.4 kW.

## Dry run (gates)

| gate | value | limit | ok |
|---|---|---|---|
| cell_s | 28.22 | 45.0 | yes |
| rss_gb | 1.90 | 4.0 | yes |
| median_site_swaps | 4.02 | 3.0 | yes |

Layout D07:SC:B3:C2|D13:SC:B3:C2|D14:SC:B3:C2|D18:SC:B3:C2|D19:SC:B3:C2|D22:SC:B3:C2|D23:SC:B3:C2|D24:SC:B3:C2|D28:SC:B3:C2|D29:SC:B3:C2|D30:SC:B3:C2|D33:SC:B3:C2|D34:SC:B3:C2|D38:SC:B3:C2|D45:SC:B3:C2: V = 12337.3, served 0.712; median site swaps 4.02; escalate = False (go: 48 riders / 240 orders).

## Rule follower against the exact aggregated ILP (16 riders, k = 5, 1800.0 s, Threads 3)

Ratio = rule total / ILP incumbent total of the same cell with the cell's MIP gap (critic C6: no rank statistic).

| layout | scenario | rule | ILP incumbent | bound | gap | status | ratio |
|---|---|---|---|---|---|---|---|
| greedy5 | 0 | 2494.5 | 1320.6 | 1320.5 | 0.000 | OPTIMAL | 1.889 |
| greedy5 | 1 | 2127.9 | 1289.8 | 1289.8 | 0.000 | OPTIMAL | 1.650 |
| greedy5 | 2 | 2780.1 | 1258.4 | 1258.4 | 0.000 | OPTIMAL | 2.209 |
| CSCD5 | 0 | 3453.5 | 1349.9 | 1349.9 | 0.000 | OPTIMAL | 2.558 |
| CSCD5 | 1 | 3137.7 | 1363.0 | 1363.0 | 0.000 | OPTIMAL | 2.302 |
| CSCD5 | 2 | 2633.7 | 1291.2 | 1291.2 | 0.000 | OPTIMAL | 2.040 |
| CSAV5 | 0 | 2522.1 | 1328.2 | 1328.2 | 0.000 | OPTIMAL | 1.899 |
| CSAV5 | 1 | 2716.6 | 1294.0 | 1294.0 | 0.000 | OPTIMAL | 2.099 |
| CSAV5 | 2 | 2787.1 | 1269.7 | 1269.6 | 0.000 | OPTIMAL | 2.195 |

Ratio median 2.099 (min 1.650, max 2.558); gap median 0.000, max 0.000; 9 of 9 cells OPTIMAL.

## Search (6-scenario subset)

| restart | start | result | V | status |
|---|---|---|---|---|
| m2_incumbent | D07:SC:B3:C2|D45:SC:B3:C2 | D05:SC:B3:C2|D07:SC:B3:C2|D09:SC:B3:C2|D13:SC:B3:C2|D16:SC:B3:C2|D22:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D41:SC:B3:C2|D45:SC:B3:C2|D49:SC:B3:C2|D51:SC:B3:C2|D54:SC:B3:C2|D55:SC:B3:C2 | 9678.3 | OK |
| CSCD_best2 | D18:SC:B3:C2|D23:SC:B3:C2 | D05:SC:B3:C2|D07:SC:B3:C2|D09:SC:B3:C2|D12:SC:B3:C2|D18:SC:B3:C2|D23:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D41:SC:B3:C2|D48:SC:B3:C2|D49:SC:B3:C2|D50:SC:B3:C2|D55:SC:B3:C2 | 9489.8 | OK |
| CSAV_best2 | D30:SC:B3:C2|D38:SC:B3:C2 | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D14:SC:B3:C2|D16:SC:B3:C2|D23:SC:B3:C2|D30:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D39:SC:B3:C2|D41:SC:B3:C2|D49:SC:B3:C2|D51:SC:B3:C2|D53:SC:B3:C2|D55:SC:B3:C2 | 9635.0 | OK |
| empty | empty | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D14:SC:B3:C2|D23:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D41:SC:B3:C2|D46:SC:B3:C2|D49:SC:B3:C2|D51:SC:B3:C2|D54:SC:B3:C2|D55:SC:B3:C2 | 10295.1 | OK |

Best restart: CSCD_best2; best locations V = 9489.8; after the size polish V = 8408.6 (D05:SC:B4:C2|D07:SC:B4:C2|D09:SC:B4:C2|D12:SC:B4:C2|D18:SC:B4:C2|D23:SC:B2:C2|D28:SC:B2:C2|D34:SC:B2:C2|D35:SC:B4:C2|D38:SC:B4:C2|D41:SC:B2:C2|D48:SC:B2:C2|D49:SC:B2:C2|D50:SC:B3:C2|D55:SC:B2:C2).  '15 units free' (budget reading): D05:SC:B3:C1|D07:SC:B3:C2|D11:SC:B3:C1|D12:SC:B3:C1|D17:SC:B3:C1|D22:SC:B3:C1|D30:SC:B3:C1|D34:SC:B3:C1|D35:SC:B3:C1|D41:SC:B3:C1|D45:SC:B3:C2|D49:SC:B3:C1|D51:SC:B3:C1|D54:SC:B3:C1|D59:SC:B3:C1 with 15 sites, V = 10849.7.  72 lower-level cells (72 solved), 9170 proxy evaluations, wall 162.3 s; cell mean 13.71 s, max 20.89 s, worker RSS max 2.25 GB.

## Final table (in-sample, stratified 95 % CI; held-out; regret against the best, paired stratified CI)

| layout | sites | V in | CI | served | V out | regret in | regret CI | regret out |
|---|---|---|---|---|---|---|---|---|
| best | 15 | 8642.1 | [7027.3, 10256.8] | 0.882 | 8977.9 | 0.0 | +-0.0 | 0.0 |
| best_locations | 15 | 9719.5 | [7310.0, 12129.1] | 0.849 | 10035.8 | 1077.5 | +-421.0 | 1057.9 |
| restart:m2_incumbent | 15 | 9907.8 | [7015.0, 12800.7] | 0.840 | 10071.7 | 1265.8 | +-554.1 | 1093.8 |
| restart:CSCD_best2 | 15 | 9719.5 | [7310.0, 12129.1] | 0.849 | 10035.8 | 1077.5 | +-421.0 | 1057.9 |
| restart:CSAV_best2 | 15 | 9838.0 | [7551.6, 12124.4] | 0.842 | 10178.9 | 1195.9 | +-460.6 | 1201.0 |
| restart:empty | 15 | 10336.1 | [8303.8, 12368.4] | 0.824 | 10518.0 | 1694.0 | +-1943.7 | 1540.1 |
| CSCD15 | 15 | 12337.3 | [11186.4, 13488.3] | 0.712 | 12929.1 | 3695.3 | +-1571.5 | 3951.2 |
| CSTC15 | 15 | 12819.6 | [11488.5, 14150.8] | 0.686 | 13205.1 | 4177.6 | +-385.5 | 4227.2 |
| CSAV15 | 15 | 10608.0 | [6894.1, 14321.8] | 0.800 | 11379.8 | 1965.9 | +-1561.6 | 2401.9 |
| kmedian15 | 15 | 11188.7 | [9588.4, 12789.0] | 0.781 | 11653.6 | 2546.6 | +-895.2 | 2675.7 |
| dotfirst15 | 15 | 12420.7 | [11505.9, 13335.5] | 0.719 | 13298.7 | 3778.6 | +-1530.6 | 4320.8 |
| free | 15 | 10962.4 | [9261.0, 12663.9] | 0.773 | 11020.4 | 2320.4 | +-906.2 | 2042.5 |
| V(k=1) | 1 | 18280.8 | [17966.7, 18594.9] | 0.103 | 18434.6 | 9638.8 | +-1364.9 | 9456.7 |
| V(k=2) | 2 | 17608.2 | [17143.1, 18073.4] | 0.194 | 17597.3 | 8966.2 | +-989.2 | 8619.3 |
| V(k=5) | 5 | 15567.4 | [14674.6, 16460.2] | 0.408 | 15943.7 | 6925.3 | +-781.6 | 6965.8 |
| V(k=10) | 10 | 12447.3 | [11425.9, 13468.7] | 0.678 | 12900.6 | 3805.3 | +-539.1 | 3922.7 |
| V(k=15) | 15 | 9719.5 | [7310.0, 12129.1] | 0.849 | 10035.8 | 1077.5 | +-421.0 | 1057.9 |
| V(k=20) | 20 | 8761.3 | [6798.7, 10723.9] | 0.899 | 8695.8 | 119.2 | +-323.9 | -282.1 |
| prod_m1 | 1 | 18182.6 | [17747.4, 18617.7] | 0.107 | 18426.7 | 9540.5 | +-1009.7 | 9448.8 |
| prod_m2 | 2 | 17608.2 | [17143.1, 18073.4] | 0.194 | 17597.3 | 8966.2 | +-989.2 | 8619.3 |

## V(k) curve (greedy path, re-priced on the in-sample scenarios)

| k | layout | V in | CI | V out | served |
|---|---|---|---|---|---|
| 1 | D30:SC:B3:C2 | 18280.8 | [17966.7, 18594.9] | 18434.6 | 0.103 |
| 2 | D07:SC:B3:C2|D45:SC:B3:C2 | 17608.2 | [17143.1, 18073.4] | 17597.3 | 0.194 |
| 5 | D07:SC:B3:C2|D13:SC:B3:C2|D34:SC:B3:C2|D45:SC:B3:C2|D51:SC:B3:C2 | 15567.4 | [14674.6, 16460.2] | 15943.7 | 0.408 |
| 10 | D07:SC:B3:C2|D09:SC:B3:C2|D13:SC:B3:C2|D22:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D41:SC:B3:C2|D45:SC:B3:C2|D51:SC:B3:C2|D54:SC:B3:C2 | 12447.3 | [11425.9, 13468.7] | 12900.6 | 0.678 |
| 15 | D05:SC:B3:C2|D07:SC:B3:C2|D09:SC:B3:C2|D12:SC:B3:C2|D18:SC:B3:C2|D23:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D41:SC:B3:C2|D48:SC:B3:C2|D49:SC:B3:C2|D50:SC:B3:C2|D55:SC:B3:C2 | 9719.5 | [7310.0, 12129.1] | 10035.8 | 0.849 |
| 20 | D05:SC:B3:C2|D07:SC:B3:C2|D09:SC:B3:C2|D11:SC:B3:C2|D12:SC:B3:C2|D17:SC:B3:C2|D18:SC:B3:C2|D23:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D41:SC:B3:C2|D44:SC:B3:C2|D48:SC:B3:C2|D49:SC:B3:C2|D50:SC:B3:C2|D53:SC:B3:C2|D55:SC:B3:C2|D58:SC:B3:C2 | 8761.3 | [6798.7, 10723.9] | 8695.8 | 0.899 |

## Per-site statistics of the best layout (p-weighted over the in-sample scenarios; removal = V without the site - V with it)

| site | swaps | CI | orders <= 1 km served / total | riders | busy | idle | kWh | wait min | stock-out slots | removal USD | CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D05 | 7.81 | [6.55, 9.07] | 13.0 / 14.4 | 7.8 | 0.98 | 0.02 | 2.33 | 60.2 | 36.9 | 1238.3 | [879.0, 1597.5] |
| D07 | 7.90 | [6.69, 9.11] | 25.3 / 29.6 | 7.9 | 0.99 | 0.01 | 2.41 | 63.7 | 38.5 | 1514.7 | [311.4, 2717.9] |
| D09 | 7.64 | [6.13, 9.16] | 20.8 / 23.2 | 7.6 | 0.99 | 0.01 | 2.24 | 35.0 | 34.4 | 1240.8 | [1110.0, 1371.6] |
| D12 | 8.02 | [7.41, 8.64] | 23.5 / 26.6 | 7.9 | 0.97 | 0.01 | 2.37 | 55.9 | 36.6 | 1313.9 | [1068.1, 1559.8] |
| D18 | 6.64 | [5.41, 7.87] | 37.5 / 42.4 | 6.5 | 0.78 | 0.18 | 1.82 | 21.2 | 27.0 | 919.3 | [657.8, 1180.7] |
| D23 | 3.45 | [2.82, 4.08] | 22.9 / 26.6 | 3.3 | 0.67 | 0.28 | 1.44 | 13.2 | 25.0 | 512.8 | [50.1, 975.5] |
| D28 | 3.17 | [1.80, 4.54] | 27.8 / 32.3 | 3.2 | 0.63 | 0.35 | 1.25 | 7.1 | 20.9 | 311.8 | [-183.6, 807.3] |
| D34 | 3.07 | [1.53, 4.61] | 40.2 / 45.3 | 3.1 | 0.66 | 0.32 | 1.27 | 9.4 | 22.1 | 309.9 | [-54.8, 674.7] |
| D35 | 7.62 | [6.95, 8.28] | 28.1 / 31.5 | 7.5 | 0.98 | 0.02 | 2.27 | 32.2 | 35.6 | 1019.0 | [270.9, 1767.1] |
| D38 | 7.71 | [5.12, 10.31] | 24.0 / 28.6 | 7.7 | 0.96 | 0.04 | 2.31 | 31.7 | 35.0 | 1088.2 | [788.0, 1388.4] |
| D41 | 3.31 | [2.67, 3.95] | 25.9 / 31.8 | 3.3 | 0.66 | 0.33 | 1.29 | 5.3 | 21.3 | 399.3 | [-645.7, 1444.2] |
| D48 | 3.79 | [3.06, 4.51] | 30.9 / 33.6 | 3.7 | 0.73 | 0.23 | 1.49 | 9.0 | 25.4 | 269.4 | [-16.1, 554.9] |
| D49 | 2.83 | [1.56, 4.11] | 22.8 / 26.5 | 2.8 | 0.57 | 0.42 | 1.13 | 3.2 | 18.6 | 278.1 | [-44.3, 600.6] |
| D50 | 4.33 | [3.72, 4.94] | 15.6 / 18.5 | 4.3 | 0.63 | 0.32 | 1.38 | 5.1 | 21.1 | 618.6 | [-73.4, 1310.6] |
| D55 | 2.93 | [1.56, 4.30] | 17.6 / 19.7 | 2.9 | 0.56 | 0.41 | 1.13 | 10.6 | 19.6 | 359.3 | [118.3, 600.4] |

Map inputs: `layout.json` (schema map15.layout/1, V = 8642.1, served 0.882, investment 782250 USD) and `site_stats.csv` in `/home/ubuntu/battery_swap/ebike_swap_sim/outputs/r8_k15_sp` -> copy to `paper_itsc/figs/map15/` and run `make_figs.py map15`.

## Cost per batch (`cost.jsonl`; instance hours = union of the lane intervals)

| batch | invocations | stages | instance | wall h (sum) | USD (sum) | instance h | USD (instance h) | failed | unfinished |
|---|---|---|---|---|---|---|---|---|---|
| k15sp | 5 | dryrun, final, instances, search, validate | r7i.4xlarge | 2.01 | 2.13 | 2.01 | 2.13 | 0 | 0 |
| k15sp2 | 4 | final, search | r7i.4xlarge | 0.17 | 0.17 | 0.17 | 0.17 | 0 | 0 |
| total | 9 | | | 2.18 | 2.31 | 2.18 | 2.31 | | 0 |

