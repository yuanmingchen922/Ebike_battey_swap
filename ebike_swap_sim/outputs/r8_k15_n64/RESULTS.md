# R8 fifteen-site study -- r8_k15_n64

Family `manhattan15`, k = 15, unit option ('SC', 3, 2), lower level = rule-based rider module (`baseline.run_baseline` variant r2, every schedule certified by `evaluate.check`), open-sites tier, union arc library; search on scenarios [0, 2, 4, 6, 8, 10], final table on 12 in-sample + 12 held-out scenarios.  Values are USD per evening (window-allocated set-up + operating cost).  The best layout is 'best found under the rule follower' (no certificate; design section 5).

## Dry run (gates)

| gate | value | limit | ok |
|---|---|---|---|
| cell_s | 32.93 | 45.0 | yes |
| rss_gb | 1.95 | 4.0 | yes |
| median_site_swaps | 3.00 | 3.0 | yes |

Layout D07:SC:B3:C2|D13:SC:B3:C2|D14:SC:B3:C2|D18:SC:B3:C2|D19:SC:B3:C2|D22:SC:B3:C2|D23:SC:B3:C2|D24:SC:B3:C2|D28:SC:B3:C2|D29:SC:B3:C2|D30:SC:B3:C2|D33:SC:B3:C2|D34:SC:B3:C2|D38:SC:B3:C2|D45:SC:B3:C2: V = 13223.8, served 0.626; median site swaps 3.00; escalate = False (go: 48 riders / 240 orders).

## Rule follower against the exact aggregated ILP (16 riders, k = 5, 1800.0 s, Threads 3)

Ratio = rule total / ILP incumbent total of the same cell with the cell's MIP gap (critic C6: no rank statistic).

| layout | scenario | rule | ILP incumbent | bound | gap | status | ratio |
|---|---|---|---|---|---|---|---|
| greedy5 | 0 | 2494.3 | 1320.5 | 1320.5 | 0.000 | OPTIMAL | 1.889 |
| greedy5 | 1 | 2127.7 | 1289.8 | 1289.8 | 0.000 | OPTIMAL | 1.650 |
| greedy5 | 2 | 2780.1 | 1258.4 | 1258.4 | 0.000 | OPTIMAL | 2.209 |
| CSCD5 | 0 | 2989.1 | 1448.7 | 1429.8 | 0.013 | TIME_LIMIT | 2.063 |
| CSCD5 | 1 | 2408.5 | 1472.0 | 1467.3 | 0.003 | TIME_LIMIT | 1.636 |
| CSCD5 | 2 | 2438.8 | 1460.0 | 1452.0 | 0.005 | TIME_LIMIT | 1.670 |
| CSAV5 | 0 | 2522.1 | 1328.2 | 1328.2 | 0.000 | OPTIMAL | 1.899 |
| CSAV5 | 1 | 2716.6 | 1294.0 | 1294.0 | 0.000 | OPTIMAL | 2.099 |
| CSAV5 | 2 | 2787.0 | 1269.6 | 1269.6 | 0.000 | OPTIMAL | 2.195 |

Ratio median 1.899 (min 1.636, max 2.209); gap median 0.000, max 0.013; 6 of 9 cells OPTIMAL.

## Search (6-scenario subset)

| restart | start | result | V | status |
|---|---|---|---|---|
| m2_incumbent | D07:SC:B3:C2|D45:SC:B3:C2 | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D13:SC:B3:C2|D22:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D40:SC:B3:C2|D45:SC:B3:C2|D48:SC:B3:C2|D49:SC:B3:C2|D51:SC:B3:C2|D55:SC:B3:C2 | 12117.7 | OK |
| CSCD_best2 | D18:SC:B3:C2|D23:SC:B3:C2 | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D12:SC:B3:C2|D16:SC:B3:C2|D23:SC:B3:C2|D29:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D41:SC:B3:C2|D48:SC:B3:C2|D49:SC:B3:C2|D51:SC:B3:C2|D54:SC:B3:C2|D55:SC:B3:C2 | 11508.1 | OK |
| CSAV_best2 | D30:SC:B3:C2|D38:SC:B3:C2 | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D14:SC:B3:C2|D23:SC:B3:C2|D30:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D39:SC:B3:C2|D41:SC:B3:C2|D46:SC:B3:C2|D49:SC:B3:C2|D51:SC:B3:C2|D54:SC:B3:C2|D59:SC:B3:C2 | 11969.5 | OK |
| empty | empty | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D12:SC:B3:C2|D16:SC:B3:C2|D19:SC:B3:C2|D30:SC:B3:C2|D33:SC:B3:C2|D38:SC:B3:C2|D40:SC:B3:C2|D46:SC:B3:C2|D49:SC:B3:C2|D54:SC:B3:C2|D55:SC:B3:C2|D58:SC:B3:C2 | 11456.0 | OK |

Best restart: empty; best locations V = 11456.0; after the size polish V = 11156.0 (D05:SC:B4:C2|D07:SC:B4:C2|D11:SC:B4:C2|D12:SC:B3:C2|D16:SC:B3:C2|D19:SC:B3:C2|D30:SC:B3:C2|D33:SC:B3:C2|D38:SC:B3:C2|D40:SC:B2:C2|D46:SC:B3:C2|D49:SC:B3:C2|D54:SC:B2:C2|D55:SC:B3:C2|D58:SC:B2:C2).  '15 units free' (budget reading): D05:SC:B3:C1|D07:SC:B3:C2|D11:SC:B3:C1|D13:SC:B3:C1|D17:SC:B3:C1|D22:SC:B3:C1|D30:SC:B3:C1|D34:SC:B3:C1|D35:SC:B3:C1|D40:SC:B3:C1|D45:SC:B3:C2|D49:SC:B3:C1|D51:SC:B3:C1|D54:SC:B3:C1|D59:SC:B3:C1 with 15 sites, V = 12058.5.  1512 lower-level cells (1512 solved), 8793 proxy evaluations, wall 5245.9 s; cell mean 21.37 s, max 42.52 s, worker RSS max 2.45 GB.

## Final table (in-sample, stratified 95 % CI; held-out; regret against the best, paired stratified CI)

| layout | sites | V in | CI | served | V out | regret in | regret CI | regret out |
|---|---|---|---|---|---|---|---|---|
| best | 15 | 11210.5 | [10338.1, 12082.9] | 0.729 | 11464.7 | 0.0 | +-0.0 | 0.0 |
| best_locations | 15 | 11599.6 | [10582.9, 12616.3] | 0.714 | 11881.3 | 389.1 | +-271.8 | 416.6 |
| restart:m2_incumbent | 15 | 11895.3 | [10965.2, 12825.3] | 0.708 | 12380.5 | 684.8 | +-453.7 | 915.8 |
| restart:CSCD_best2 | 15 | 11559.5 | [10862.8, 12256.1] | 0.713 | 11689.2 | 349.0 | +-241.6 | 224.5 |
| restart:CSAV_best2 | 15 | 11941.7 | [11087.7, 12795.7] | 0.699 | 12195.7 | 731.2 | +-482.5 | 731.0 |
| restart:empty | 15 | 11599.6 | [10582.9, 12616.3] | 0.714 | 11881.3 | 389.1 | +-271.8 | 416.6 |
| CSCD15 | 15 | 13223.8 | [12415.0, 14032.7] | 0.626 | 13670.6 | 2013.3 | +-710.2 | 2205.9 |
| CSTC15 | 15 | 13750.6 | [12987.2, 14514.0] | 0.595 | 13961.8 | 2540.1 | +-266.2 | 2497.1 |
| CSAV15 | 15 | 11878.2 | [10825.9, 12930.5] | 0.704 | 12475.8 | 667.7 | +-308.9 | 1011.1 |
| kmedian15 | 15 | 12239.1 | [11271.3, 13206.9] | 0.689 | 12608.6 | 1028.6 | +-344.0 | 1143.9 |
| dotfirst15 | 15 | 13208.6 | [12449.6, 13967.6] | 0.643 | 13962.5 | 1998.1 | +-961.0 | 2497.8 |
| free | 15 | 11907.9 | [10912.4, 12903.4] | 0.703 | 12278.8 | 697.4 | +-329.8 | 814.1 |
| V(k=1) | 1 | 18280.8 | [18097.6, 18464.1] | 0.103 | 18434.6 | 7070.3 | +-848.0 | 6969.9 |
| V(k=2) | 2 | 17608.2 | [17346.7, 17869.7] | 0.194 | 17597.3 | 6397.7 | +-629.6 | 6132.6 |
| V(k=5) | 5 | 15824.5 | [15450.1, 16199.0] | 0.362 | 16120.9 | 4614.0 | +-590.1 | 4656.2 |
| V(k=10) | 10 | 13760.4 | [13185.5, 14335.3] | 0.548 | 14116.1 | 2549.9 | +-340.5 | 2651.4 |
| V(k=15) | 15 | 11599.6 | [10582.9, 12616.3] | 0.714 | 11881.3 | 389.1 | +-271.8 | 416.6 |
| V(k=20) | 20 | 10486.3 | [9210.8, 11761.7] | 0.800 | 10682.1 | -724.2 | +-435.9 | -782.6 |
| prod_m1 | 1 | 18182.6 | [17878.4, 18486.7] | 0.107 | 18426.7 | 6972.1 | +-696.3 | 6962.1 |
| prod_m2 | 2 | 17608.2 | [17346.7, 17869.7] | 0.194 | 17597.3 | 6397.7 | +-629.6 | 6132.6 |

## V(k) curve (greedy path, re-priced on the in-sample scenarios)

| k | layout | V in | CI | V out | served |
|---|---|---|---|---|---|
| 1 | D30:SC:B3:C2 | 18280.8 | [18097.6, 18464.1] | 18434.6 | 0.103 |
| 2 | D07:SC:B3:C2|D45:SC:B3:C2 | 17608.2 | [17346.7, 17869.7] | 17597.3 | 0.194 |
| 5 | D07:SC:B3:C2|D13:SC:B3:C2|D34:SC:B3:C2|D45:SC:B3:C2|D51:SC:B3:C2 | 15824.5 | [15450.1, 16199.0] | 16120.9 | 0.362 |
| 10 | D05:SC:B3:C2|D07:SC:B3:C2|D13:SC:B3:C2|D28:SC:B3:C2|D34:SC:B3:C2|D40:SC:B3:C2|D45:SC:B3:C2|D48:SC:B3:C2|D51:SC:B3:C2|D55:SC:B3:C2 | 13760.4 | [13185.5, 14335.3] | 14116.1 | 0.548 |
| 15 | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D12:SC:B3:C2|D16:SC:B3:C2|D19:SC:B3:C2|D30:SC:B3:C2|D33:SC:B3:C2|D38:SC:B3:C2|D40:SC:B3:C2|D46:SC:B3:C2|D49:SC:B3:C2|D54:SC:B3:C2|D55:SC:B3:C2|D58:SC:B3:C2 | 11599.6 | [10582.9, 12616.3] | 11881.3 | 0.714 |
| 20 | D05:SC:B3:C2|D07:SC:B3:C2|D11:SC:B3:C2|D12:SC:B3:C2|D16:SC:B3:C2|D19:SC:B3:C2|D23:SC:B3:C2|D30:SC:B3:C2|D33:SC:B3:C2|D34:SC:B3:C2|D35:SC:B3:C2|D38:SC:B3:C2|D40:SC:B3:C2|D44:SC:B3:C2|D46:SC:B3:C2|D49:SC:B3:C2|D51:SC:B3:C2|D54:SC:B3:C2|D55:SC:B3:C2|D58:SC:B3:C2 | 10486.3 | [9210.8, 11761.7] | 10682.1 | 0.800 |

## Per-site statistics of the best layout (p-weighted over the in-sample scenarios; removal = V without the site - V with it)

| site | swaps | CI | orders <= 1 km served / total | riders | busy | idle | kWh | wait min | stock-out slots | removal USD | CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D05 | 7.90 | [7.74, 8.07] | 10.4 / 14.4 | 7.8 | 0.99 | 0.01 | 2.37 | 58.7 | 37.9 | 837.9 | [646.0, 1029.7] |
| D07 | 8.00 | [8.00, 8.00] | 20.4 / 29.6 | 8.0 | 1.00 | 0.00 | 2.45 | 62.3 | 38.9 | 791.2 | [551.8, 1030.6] |
| D11 | 7.76 | [7.35, 8.17] | 28.0 / 38.9 | 7.8 | 0.99 | 0.01 | 2.34 | 47.9 | 36.7 | 728.4 | [357.2, 1099.6] |
| D12 | 3.05 | [2.93, 3.16] | 19.2 / 26.6 | 3.0 | 0.34 | 0.63 | 0.30 | 10.2 | 44.2 | 512.6 | [136.0, 889.2] |
| D16 | 3.00 | [3.00, 3.00] | 16.0 / 22.5 | 3.0 | 0.03 | 0.82 | 0.02 | 0.4 | 17.4 | 472.9 | [150.3, 795.6] |
| D19 | 3.00 | [3.00, 3.00] | 25.2 / 36.2 | 3.0 | 0.11 | 0.77 | 0.14 | 1.8 | 33.4 | 476.5 | [214.9, 738.0] |
| D30 | 3.00 | [3.00, 3.00] | 24.4 / 34.5 | 3.0 | 0.01 | 0.83 | 0.01 | 0.4 | 19.7 | 292.0 | [112.4, 471.7] |
| D33 | 3.00 | [3.00, 3.00] | 22.5 / 31.5 | 3.0 | 0.07 | 0.88 | 0.03 | 5.0 | 44.0 | 480.0 | [222.1, 737.8] |
| D38 | 3.00 | [3.00, 3.00] | 19.3 / 28.6 | 3.0 | 0.03 | 0.88 | 0.02 | 4.5 | 42.7 | 264.9 | [105.9, 424.0] |
| D40 | 2.00 | [2.00, 2.00] | 22.0 / 32.4 | 2.0 | 0.00 | 0.88 | 0.00 | 0.4 | 29.0 | 238.4 | [-54.9, 531.6] |
| D46 | 3.00 | [3.00, 3.00] | 22.5 / 30.5 | 3.0 | 0.00 | 0.83 | 0.00 | 0.0 | 17.1 | 285.3 | [143.0, 427.5] |
| D49 | 3.00 | [3.00, 3.00] | 20.0 / 26.5 | 3.0 | 0.00 | 0.82 | 0.00 | 0.4 | 18.0 | 424.4 | [149.9, 698.9] |
| D54 | 2.00 | [2.00, 2.00] | 25.0 / 33.7 | 2.0 | 0.00 | 0.88 | 0.00 | 0.3 | 18.1 | 191.2 | [102.9, 279.4] |
| D55 | 2.95 | [2.84, 3.07] | 14.8 / 19.7 | 3.0 | 0.00 | 0.84 | 0.00 | 0.4 | 14.0 | 283.0 | [139.8, 426.2] |
| D58 | 2.00 | [2.00, 2.00] | 7.6 / 11.7 | 2.0 | 0.00 | 0.90 | 0.00 | 0.6 | 24.6 | 314.5 | [31.6, 597.5] |

Map inputs: `layout.json` (schema map15.layout/1, V = 11210.5, served 0.729, investment 782250 USD) and `site_stats.csv` in `/home/ubuntu/battery_swap/ebike_swap_sim/outputs/r8_k15_n64` -> copy to `paper_itsc/figs/map15/` and run `make_figs.py map15`.

## Cost per batch (`cost.jsonl`; instance hours = union of the lane intervals)

| batch | invocations | stages | instance | wall h (sum) | USD (sum) | instance h | USD (instance h) | failed | unfinished |
|---|---|---|---|---|---|---|---|---|---|
| k15n64 | 4 | dryrun, final, instances, search | r7i.4xlarge | 2.73 | 2.89 | 2.73 | 2.89 | 0 | 0 |
| total | 4 | | | 2.73 | 2.89 | 2.73 | 2.89 | | 0 |

