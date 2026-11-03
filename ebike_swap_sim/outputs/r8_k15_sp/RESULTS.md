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

Best restart: CSCD_best2; best locations V = 9489.8; after the size polish V = 8851.4 (D05:SC:B4:C2|D07:SC:B3:C2|D09:SC:B3:C2|D12:SC:B4:C2|D18:SC:B3:C2|D23:SC:B3:C2|D28:SC:B2:C2|D34:SC:B2:C2|D35:SC:B4:C2|D38:SC:B4:C2|D41:SC:B3:C2|D48:SC:B3:C2|D49:SC:B2:C2|D50:SC:B3:C2|D55:SC:B2:C2).  '15 units free' (budget reading): D05:SC:B3:C1|D07:SC:B3:C2|D11:SC:B3:C1|D12:SC:B3:C1|D17:SC:B3:C1|D22:SC:B3:C1|D30:SC:B3:C1|D34:SC:B3:C1|D35:SC:B3:C1|D41:SC:B3:C1|D45:SC:B3:C2|D49:SC:B3:C1|D51:SC:B3:C1|D54:SC:B3:C1|D59:SC:B3:C1 with 15 sites, V = 10849.7.  1578 lower-level cells (1578 solved), 9170 proxy evaluations, wall 4549.3 s; cell mean 17.83 s, max 39.52 s, worker RSS max 2.31 GB.

## Final table (in-sample, stratified 95 % CI; held-out; regret against the best, paired stratified CI)

| layout | sites | V in | CI | served | V out | regret in | regret CI | regret out |
|---|---|---|---|---|---|---|---|---|
| best | 15 | 9081.4 | [8111.4, 10051.3] | 0.864 | 9234.6 | 0.0 | +-0.0 | 0.0 |
| best_locations | 15 | 9719.5 | [8619.4, 10819.6] | 0.849 | 10035.8 | 638.1 | +-167.7 | 801.3 |
| restart:m2_incumbent | 15 | 9907.8 | [8841.4, 10974.3] | 0.840 | 10071.7 | 826.5 | +-274.3 | 837.2 |
| restart:CSCD_best2 | 15 | 9719.5 | [8619.4, 10819.6] | 0.849 | 10035.8 | 638.1 | +-167.7 | 801.3 |
| restart:CSAV_best2 | 15 | 9838.0 | [8903.0, 10773.0] | 0.842 | 10178.9 | 756.6 | +-178.7 | 944.3 |
| restart:empty | 15 | 10336.1 | [9410.5, 11261.6] | 0.824 | 10518.0 | 1254.7 | +-398.0 | 1283.5 |
| CSCD15 | 15 | 12337.3 | [11416.5, 13258.1] | 0.712 | 12929.1 | 3255.9 | +-698.6 | 3694.6 |
| CSTC15 | 15 | 12819.6 | [12005.3, 13634.0] | 0.686 | 13205.1 | 3738.3 | +-298.2 | 3970.6 |
| CSAV15 | 15 | 10608.0 | [9364.1, 11851.8] | 0.800 | 11379.8 | 1526.6 | +-315.8 | 2145.2 |
| kmedian15 | 15 | 11188.7 | [10223.9, 12153.5] | 0.781 | 11653.6 | 2107.3 | +-519.4 | 2419.1 |
| dotfirst15 | 15 | 12420.7 | [11627.0, 13214.4] | 0.719 | 13298.7 | 3339.3 | +-1027.8 | 4064.1 |
| free | 15 | 10962.4 | [9924.1, 12000.7] | 0.773 | 11020.4 | 1881.0 | +-546.9 | 1785.9 |
| V(k=1) | 1 | 18280.8 | [18097.6, 18464.1] | 0.103 | 18434.6 | 9199.4 | +-945.0 | 9200.0 |
| V(k=2) | 2 | 17608.2 | [17346.7, 17869.7] | 0.194 | 17597.3 | 8526.8 | +-763.9 | 8362.7 |
| V(k=5) | 5 | 15567.4 | [15159.5, 15975.3] | 0.408 | 15943.7 | 6486.0 | +-570.5 | 6709.2 |
| V(k=10) | 10 | 12447.3 | [11856.4, 13038.2] | 0.678 | 12900.6 | 3365.9 | +-409.0 | 3666.1 |
| V(k=15) | 15 | 9719.5 | [8619.4, 10819.6] | 0.849 | 10035.8 | 638.1 | +-167.7 | 801.3 |
| V(k=20) | 20 | 8761.3 | [7730.2, 9792.3] | 0.899 | 8695.8 | -320.1 | +-195.7 | -538.8 |
| prod_m1 | 1 | 18182.6 | [17878.4, 18486.7] | 0.107 | 18426.7 | 9101.2 | +-808.1 | 9192.2 |
| prod_m2 | 2 | 17608.2 | [17346.7, 17869.7] | 0.194 | 17597.3 | 8526.8 | +-763.9 | 8362.7 |

## V(k) curve (greedy path, re-priced on the in-sample scenarios)

| k | layout | V in | CI | V out | served |
|---|---|---|---|---|---|
| 1 | D30:SC:B3:C2 | 18280.8 | [18097.6, 18464.1] | 18434.6 | 0.103 |
| 2 | D07:SC:B3:C2|D45:SC:B3:C2 | 17608.2 | [17346.7, 17869.7] | 17597.3 | 0.194 |
| 5 | D07:SC:B3:C2|D13:SC:B3:C2|D34:SC:B3:C2|D45:SC:B3:C2|D51:SC:B3:C2 | 15567.4 | [15159.5, 15975.3] | 15943.7 | 0.408 |
| 10 | D07:SC:B3:C2|D09:SC:B3:C2|D13:SC:B3:C2|D22:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D41:SC:B3:C2|D45:SC:B3:C2|D51:SC:B3:C2|D54:SC:B3:C2 | 12447.3 | [11856.4, 13038.2] | 12900.6 | 0.678 |
| 15 | D05:SC:B3:C2|D07:SC:B3:C2|D09:SC:B3:C2|D12:SC:B3:C2|D18:SC:B3:C2|D23:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D41:SC:B3:C2|D48:SC:B3:C2|D49:SC:B3:C2|D50:SC:B3:C2|D55:SC:B3:C2 | 9719.5 | [8619.4, 10819.6] | 10035.8 | 0.849 |
| 20 | D05:SC:B3:C2|D07:SC:B3:C2|D09:SC:B3:C2|D11:SC:B3:C2|D12:SC:B3:C2|D17:SC:B3:C2|D18:SC:B3:C2|D23:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D41:SC:B3:C2|D44:SC:B3:C2|D48:SC:B3:C2|D49:SC:B3:C2|D50:SC:B3:C2|D53:SC:B3:C2|D55:SC:B3:C2|D58:SC:B3:C2 | 8761.3 | [7730.2, 9792.3] | 8695.8 | 0.899 |

## Per-site statistics of the best layout (p-weighted over the in-sample scenarios; removal = V without the site - V with it)

| site | swaps | CI | orders <= 1 km served / total | riders | busy | idle | kWh | wait min | stock-out slots | removal USD | CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D05 | 7.90 | [7.67, 8.14] | 12.6 / 14.4 | 7.8 | 0.99 | 0.01 | 2.35 | 60.0 | 37.2 | 1236.2 | [993.4, 1479.0] |
| D07 | 6.95 | [6.84, 7.07] | 24.5 / 29.6 | 6.9 | 1.00 | 0.00 | 2.40 | 78.8 | 39.8 | 1184.8 | [762.3, 1607.4] |
| D09 | 6.52 | [6.11, 6.94] | 20.2 / 23.2 | 6.5 | 0.99 | 0.01 | 2.21 | 41.6 | 35.1 | 966.1 | [702.8, 1229.4] |
| D12 | 8.14 | [7.88, 8.40] | 23.1 / 26.6 | 8.1 | 0.98 | 0.01 | 2.40 | 55.6 | 37.5 | 1272.5 | [1040.0, 1504.9] |
| D18 | 5.76 | [5.11, 6.41] | 36.6 / 42.4 | 5.8 | 0.82 | 0.17 | 1.88 | 32.3 | 28.8 | 617.2 | [505.7, 728.7] |
| D23 | 4.57 | [4.07, 5.07] | 22.5 / 26.6 | 4.5 | 0.67 | 0.27 | 1.52 | 16.7 | 24.8 | 497.3 | [323.3, 671.3] |
| D28 | 2.88 | [2.35, 3.41] | 26.9 / 32.3 | 2.8 | 0.56 | 0.42 | 1.12 | 8.9 | 19.6 | 260.4 | [33.7, 487.0] |
| D34 | 2.69 | [2.40, 2.98] | 38.7 / 45.3 | 2.7 | 0.62 | 0.36 | 1.18 | 9.4 | 19.5 | 169.3 | [9.6, 328.9] |
| D35 | 7.57 | [7.13, 8.02] | 27.2 / 31.5 | 7.4 | 0.99 | 0.01 | 2.24 | 31.1 | 34.5 | 753.2 | [457.9, 1048.6] |
| D38 | 7.95 | [7.84, 8.07] | 23.0 / 28.6 | 8.0 | 1.00 | 0.00 | 2.33 | 32.5 | 33.9 | 628.4 | [185.9, 1071.0] |
| D41 | 3.93 | [3.24, 4.62] | 25.6 / 31.8 | 3.9 | 0.52 | 0.44 | 1.14 | 2.5 | 13.0 | 280.8 | [-173.4, 734.9] |
| D48 | 4.29 | [3.45, 5.12] | 30.6 / 33.6 | 4.2 | 0.62 | 0.33 | 1.37 | 4.5 | 19.4 | 255.7 | [-38.6, 550.0] |
| D49 | 2.83 | [1.95, 3.71] | 22.5 / 26.5 | 2.8 | 0.53 | 0.45 | 1.08 | 4.9 | 18.1 | 230.3 | [-50.9, 511.5] |
| D50 | 4.38 | [3.94, 4.82] | 15.6 / 18.5 | 4.4 | 0.64 | 0.32 | 1.34 | 4.8 | 19.7 | 379.0 | [170.5, 587.4] |
| D55 | 2.81 | [2.19, 3.43] | 17.7 / 19.7 | 2.8 | 0.54 | 0.42 | 1.06 | 8.6 | 17.1 | 126.3 | [-15.7, 268.2] |

Map inputs: `layout.json` (schema map15.layout/1, V = 9081.4, served 0.864, investment 782250 USD) and `site_stats.csv` in `/home/ubuntu/battery_swap/ebike_swap_sim/outputs/r8_k15_sp` -> copy to `paper_itsc/figs/map15/` and run `make_figs.py map15`.

## Cost per batch (`cost.jsonl`; instance hours = union of the lane intervals)

| batch | invocations | stages | instance | wall h (sum) | USD (sum) | instance h | USD (instance h) | failed | unfinished |
|---|---|---|---|---|---|---|---|---|---|
| k15sp | 5 | dryrun, final, instances, search, validate | r7i.4xlarge | 2.01 | 2.13 | 2.01 | 2.13 | 0 | 0 |
| total | 5 | | | 2.01 | 2.13 | 2.01 | 2.13 | | 0 |

