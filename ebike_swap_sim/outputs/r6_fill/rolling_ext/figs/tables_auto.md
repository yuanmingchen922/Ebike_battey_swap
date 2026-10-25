### T1 Cost per method (USD per 4 h window, end-adjusted, relaxed targets; mean [exact 95 % t-CI])

| method | usd4h new (n = 10) | usd4h legacy (n = 10) | stress4h new (n = 5) | stress4h legacy (n = 5) |
|---|---|---|---|---|
| best rule | 838.50 [753.33, 923.68] | 830.91 [721.74, 940.07] | 1581.76 [1289.40, 1874.12] | 1387.36 [1173.65, 1601.07] |
| rolling, lookahead 0 min | 871.65 [780.09, 963.21] | 689.95 [652.86, 727.03] | 1484.68 [1290.45, 1678.92] | 1027.95 [958.13, 1097.77] |
| rolling, lookahead 10 min | 738.51 [672.23, 804.78] | 648.64 [617.30, 679.97] | 1242.78 [1015.28, 1470.29] | 944.07 [879.95, 1008.20] |
| rolling, lookahead 20 min | 738.31 [627.12, 849.50] | 620.10 [593.59, 646.61] | 1344.81 [1241.47, 1448.15] | 948.44 [884.89, 1011.99] |
| rolling + forecast battery plan, 10 min | 735.51 [678.71, 792.31] | 641.88 [608.74, 675.02] | 1284.33 [1007.08, 1561.58] | 934.37 [871.79, 996.94] |
| offline ILP (full foresight) | 601.41 [572.70, 630.13] | 582.05 [563.65, 600.45] | 941.46 [820.06, 1062.87] | 826.10 [771.60, 880.60] |

### T2 Decomposition of the offline gap per policy (paired per seed; new prices unless stated)

| quantity | usd4h new (n = 10) | usd4h legacy | stress4h new (n = 5) | stress4h legacy |
|---|---|---|---|---|
| offline gap (best rule - offline), USD | 237.09 [172.78, 301.41] | 248.86 [155.71, 342.01] | 640.30 [454.42, 826.17] | 561.26 [388.10, 734.41] |
| offline gap, % of best rule | 27.34 [21.69, 32.99] | 28.28 [20.91, 35.64] | 40.03 [34.61, 45.45] | 39.96 [33.58, 46.35] |
| **rolling, lookahead 0 min** | | | | |
| foresight (policy - offline), USD | 270.24 [192.04, 348.45] | 107.90 [77.58, 138.21] | 543.22 [440.82, 645.62] | 201.85 [173.94, 229.75] |
| foresight, % of best rule | 32.16 [23.80, 40.51] | 13.34 [9.40, 17.29] | 34.64 [28.84, 40.44] | 14.66 [12.44, 16.87] |
| online coordination (best rule - policy), USD | -33.15 [-116.97, 50.67] | 140.96 [41.20, 240.72] | 97.08 [-43.45, 237.60] | 359.41 [199.21, 519.62] |
| online coordination, % of best rule | -4.81 [-14.85, 5.22] | 14.93 [5.40, 24.47] | 5.39 [-3.97, 14.75] | 25.31 [17.45, 33.17] |
| share of the gap kept online, mean of ratios | -0.326 [-0.863, 0.211] | 0.427 [0.146, 0.708] | 0.121 [-0.123, 0.365] | 0.626 [0.520, 0.732] |
| share kept, ratio of means | -0.140 | 0.566 | 0.152 | 0.640 |
| share kept, median | -0.142 | 0.495 | 0.233 | 0.657 |
| seeds with the policy cheaper than the best rule | 4/10 | 9/10 | 4/5 | 5/5 |
| seeds with foresight > online coordination | 9/10 | 5/10 | 5/5 | 0/5 |
| **rolling, lookahead 10 min** | | | | |
| foresight (policy - offline), USD | 137.09 [81.49, 192.70] | 66.59 [43.25, 89.92] | 301.32 [153.58, 449.06] | 117.97 [73.13, 162.82] |
| foresight, % of best rule | 16.35 [10.00, 22.69] | 8.33 [5.21, 11.46] | 18.92 [11.45, 26.38] | 8.70 [4.72, 12.69] |
| online coordination (best rule - policy), USD | 100.00 [31.13, 168.87] | 182.27 [80.50, 284.04] | 338.98 [178.31, 499.64] | 443.29 [250.53, 636.04] |
| online coordination, % of best rule | 11.00 [2.40, 19.59] | 19.94 [10.76, 29.12] | 21.11 [13.00, 29.23] | 31.26 [21.82, 40.70] |
| share of the gap kept online, mean of ratios | 0.289 [-0.191, 0.770] | 0.636 [0.438, 0.835] | 0.526 [0.344, 0.708] | 0.774 [0.643, 0.904] |
| share kept, ratio of means | 0.422 | 0.732 | 0.529 | 0.790 |
| share kept, median | 0.538 | 0.731 | 0.570 | 0.831 |
| seeds with the policy cheaper than the best rule | 9/10 | 10/10 | 5/5 | 5/5 |
| seeds with foresight > online coordination | 4/10 | 3/10 | 2/5 | 0/5 |
| **rolling, lookahead 20 min** | | | | |
| foresight (policy - offline), USD | 136.90 [37.73, 236.07] | 38.05 [18.31, 57.79] | 403.34 [246.71, 559.97] | 122.34 [37.55, 207.13] |
| foresight, % of best rule | 16.00 [5.02, 26.98] | 4.63 [2.08, 7.17] | 26.98 [10.34, 43.62] | 9.23 [1.60, 16.86] |
| online coordination (best rule - policy), USD | 100.20 [-5.25, 205.65] | 210.81 [118.56, 303.05] | 236.96 [-83.41, 557.32] | 438.92 [216.70, 661.15] |
| online coordination, % of best rule | 11.34 [-0.61, 23.30] | 23.65 [15.85, 31.45] | 13.05 [-8.16, 34.27] | 30.73 [18.32, 43.14] |
| share of the gap kept online, mean of ratios | 0.354 [-0.062, 0.770] | 0.808 [0.648, 0.968] | 0.293 [-0.261, 0.848] | 0.756 [0.520, 0.992] |
| share kept, ratio of means | 0.423 | 0.847 | 0.370 | 0.782 |
| share kept, median | 0.531 | 0.854 | 0.391 | 0.821 |
| seeds with the policy cheaper than the best rule | 7/10 | 10/10 | 4/5 | 5/5 |
| seeds with foresight > online coordination | 5/10 | 1/10 | 3/5 | 1/5 |
| **rolling + forecast battery plan, 10 min** | | | | |
| foresight (policy - offline), USD | 134.10 [76.79, 191.41] | 59.83 [36.71, 82.96] | 342.87 [166.79, 518.94] | 108.27 [74.89, 141.64] |
| foresight, % of best rule | 17.06 [7.58, 26.54] | 7.36 [4.21, 10.52] | 21.06 [13.03, 29.08] | 7.96 [4.98, 10.94] |
| online coordination (best rule - policy), USD | 102.99 [-1.95, 207.94] | 189.02 [93.46, 284.59] | 297.43 [216.51, 378.36] | 452.99 [265.40, 640.59] |
| online coordination, % of best rule | 10.29 [-3.72, 24.29] | 20.91 [12.18, 29.64] | 18.97 [13.86, 24.08] | 32.00 [23.25, 40.76] |
| share of the gap kept online, mean of ratios | 0.109 [-0.824, 1.042] | 0.683 [0.474, 0.891] | 0.480 [0.333, 0.627] | 0.794 [0.693, 0.894] |
| share kept, ratio of means | 0.434 | 0.760 | 0.465 | 0.807 |
| share kept, median | 0.644 | 0.816 | 0.459 | 0.803 |
| seeds with the policy cheaper than the best rule | 8/10 | 10/10 | 5/5 | 5/5 |
| seeds with foresight > online coordination | 4/10 | 3/10 | 3/5 | 0/5 |

### T3 Paired contrasts between policies (USD per window, end-adjusted; positive = the second policy is cheaper; +a/-b = seeds with positive / negative difference)

| contrast | usd4h new (n = 10) | usd4h legacy (n = 10) | stress4h new (n = 5) | stress4h legacy (n = 5) |
|---|---|---|---|---|
| lookahead 0 -> 10 min (cost at 0 - cost at 10) | 133.15 [71.59, 194.70]; +10/-0; t p = 0.001, W p = 0.002 | 41.31 [22.62, 60.00]; +9/-1; t p = 0.001, W p = 0.004 | 241.90 [187.65, 296.14]; +5/-0; t p < 0.001, W p = 0.062 | 83.87 [48.77, 118.98]; +5/-0; t p = 0.003, W p = 0.062 |
| lookahead 10 -> 20 min (cost at 10 - cost at 20) | 0.20 [-84.43, 84.83]; +6/-4; t p = 0.996, W p = 0.922 | 28.54 [2.17, 54.90]; +7/-3; t p = 0.037, W p = 0.064 | -102.02 [-306.17, 102.13]; +2/-3; t p = 0.238, W p = 0.312 | -4.36 [-59.58, 50.85]; +3/-2; t p = 0.837, W p = 1.000 |
| lookahead 0 -> 20 min | 133.35 [30.22, 236.47]; +9/-1; t p = 0.017, W p = 0.027 | 69.85 [41.89, 97.81]; +10/-0; t p < 0.001, W p = 0.002 | 139.88 [-51.46, 331.21]; +4/-1; t p = 0.112, W p = 0.188 | 79.51 [1.73, 157.29]; +4/-1; t p = 0.047, W p = 0.125 |
| plain rolling -> forecast battery plan, both 10 min (plain - forecast) | 3.00 [-69.30, 75.29]; +5/-5; t p = 0.927, W p = 1.000 | 6.75 [-8.32, 21.83]; +7/-3; t p = 0.337, W p = 0.322 | -41.55 [-182.07, 98.98]; +3/-2; t p = 0.458, W p = 0.812 | 9.71 [-8.95, 28.36]; +4/-1; t p = 0.222, W p = 0.312 |
| seeds with cost(0) >= cost(10) >= cost(20) | 6/10 | 6/10 | 2/5 | 3/5 |
| share kept: 10 min - 0 min | 0.615 [0.331, 0.900]; +10/-0; t p = 0.001, W p = 0.002 | 0.210 [0.101, 0.319]; +9/-1; t p = 0.002, W p = 0.004 | 0.405 [0.208, 0.601]; +5/-0; t p = 0.005, W p = 0.062 | 0.148 [0.113, 0.184]; +5/-0; t p < 0.001, W p = 0.062 |
| share kept: 20 min - 10 min | 0.064 [-0.389, 0.518]; +6/-4; t p = 0.755, W p = 0.770 | 0.172 [0.023, 0.320]; +7/-3; t p = 0.028, W p = 0.037 | -0.233 [-0.734, 0.269]; +2/-3; t p = 0.267, W p = 0.312 | -0.018 [-0.145, 0.109]; +3/-2; t p = 0.716, W p = 1.000 |
| share kept: forecast plan - plain rolling | -0.180 [-0.691, 0.330]; +5/-5; t p = 0.445, W p = 0.770 | 0.046 [-0.015, 0.107]; +7/-3; t p = 0.121, W p = 0.160 | -0.046 [-0.256, 0.164]; +3/-2; t p = 0.577, W p = 0.812 | 0.020 [-0.022, 0.062]; +4/-1; t p = 0.262, W p = 0.312 |

### T4 Service and lateness per method (mean [exact 95 % t-CI] per 4 h window)

| quantity | usd4h new | usd4h legacy | stress4h new | stress4h legacy |
|---|---|---|---|---|
| served share, best rule, % | 92.5 [89.4, 95.6] | 91.9 [88.3, 95.6] | 75.4 [64.8, 86.0] | 75.4 [64.8, 86.0] |
| served share, rolling, lookahead 0 min, % | 86.7 [80.5, 92.9] | 81.4 [74.3, 88.5] | 70.8 [62.7, 79.0] | 63.7 [53.5, 74.0] |
| served share, rolling, lookahead 10 min, % | 93.3 [89.1, 97.5] | 85.6 [80.0, 91.2] | 81.7 [72.8, 90.5] | 72.9 [66.9, 79.0] |
| served share, rolling, lookahead 20 min, % | 93.9 [87.8, 99.9] | 89.2 [84.6, 93.7] | 76.7 [69.7, 83.6] | 70.4 [60.3, 80.5] |
| served share, rolling + forecast battery plan, 10 min, % | 94.2 [89.6, 98.7] | 86.7 [80.7, 92.7] | 80.0 [69.2, 90.8] | 73.8 [68.1, 79.4] |
| served share, offline ILP, % | 98.9 [97.9, 99.9] | 95.3 [92.6, 97.9] | 95.4 [90.8, 100.0] | 87.5 [82.3, 92.7] |
| served share, lookahead 0 - best rule, pp (paired) | -5.8 [-10.8, -0.8]; +2/-7/1 tie; t p = 0.027, W p = 0.038 | -10.6 [-18.2, -2.9]; +2/-8; t p = 0.012, W p = 0.020 | -4.6 [-11.0, 1.9]; +0/-3/2 tie; t p = 0.119, W p = 0.109 | -11.7 [-16.0, -7.3]; +0/-5; t p = 0.002, W p = 0.062 |
| served share, lookahead 10 - best rule, pp (paired) | 0.8 [-3.1, 4.8]; +5/-4/1 tie; t p = 0.647, W p = 0.473 | -6.4 [-13.0, 0.2]; +2/-7/1 tie; t p = 0.057, W p = 0.066 | 6.3 [0.8, 11.7]; +4/-0/1 tie; t p = 0.034, W p = 0.068 | -2.5 [-11.2, 6.2]; +2/-2/1 tie; t p = 0.468, W p = 1.000 |
| served share, lookahead 20 - best rule, pp (paired) | 1.4 [-4.5, 7.3]; +5/-4/1 tie; t p = 0.605, W p = 0.372 | -2.8 [-9.1, 3.5]; +3/-6/1 tie; t p = 0.343, W p = 0.552 | 1.2 [-11.6, 14.1]; +4/-1; t p = 0.801, W p = 0.625 | -5.0 [-20.4, 10.4]; +2/-3; t p = 0.417, W p = 0.625 |
| served share, forecast plan - best rule, pp (paired) | 1.7 [-3.6, 7.0]; +7/-2/1 tie; t p = 0.496, W p = 0.437 | -5.3 [-12.6, 2.0]; +3/-6/1 tie; t p = 0.136, W p = 0.171 | 4.6 [-0.4, 9.6]; +4/-0/1 tie; t p = 0.063, W p = 0.068 | -1.7 [-7.8, 4.5]; +1/-1/3 tie; t p = 0.495, W p = 0.655 |
| lateness, best rule, order-min | 215.0 [107.8, 322.2] | 209.5 [98.9, 320.1] | 456.0 [277.8, 634.2] | 456.0 [277.8, 634.2] |
| lateness, lookahead 0, order-min | 120.0 [63.5, 176.5] | 15.0 [9.2, 20.8] | 158.0 [37.4, 278.6] | 16.0 [4.1, 27.9] |
| lateness, lookahead 10, order-min | 92.5 [39.2, 145.8] | 9.5 [3.8, 15.2] | 146.0 [86.1, 205.9] | 9.0 [0.9, 17.1] |
| lateness, lookahead 20, order-min | 113.0 [49.1, 176.9] | 4.0 [2.5, 5.5] | 124.0 [39.9, 208.1] | 4.0 [-1.2, 9.2] |
| lateness, forecast plan, order-min | 107.5 [50.7, 164.3] | 6.5 [2.4, 10.6] | 160.0 [38.5, 281.5] | 6.0 [-4.2, 16.2] |
| lateness, offline ILP, order-min | 33.0 [6.5, 59.5] | 3.0 [0.5, 5.5] | 149.0 [87.8, 210.2] | 2.0 [-1.4, 5.4] |
| unserved orders: best rule / 0 / 10 / 20 / forecast / offline | 2.7 / 4.8 / 2.4 / 2.2 / 2.1 / 0.4 | 2.9 / 6.7 / 5.2 / 3.9 / 4.8 / 1.7 | 11.8 / 14.0 / 8.8 / 11.2 / 9.6 / 2.2 | 11.8 / 17.4 / 13.0 / 14.2 / 12.6 / 6.0 |
| orders > 60 min late: 0 / 10 / 20 / forecast (new prices only) | 0.0 / 0.0 / 0.0 / 0.0 | n/a | 0.0 / 0.0 / 0.0 / 0.0 | n/a |
| max lateness over seeds, min: 0 / 10 / 20 / forecast (new prices only) | 55 / 50 / 60 / 50 | n/a | 45 / 45 / 30 / 60 | n/a |
| swaps per window: best rule / 0 / 10 / 20 / forecast / offline | 8.8 / 4.8 / 5.4 / 6.9 / 7.0 / 8.3 | 9.2 / 5.0 / 5.7 / 5.8 / 5.6 / 8.3 | 9.4 / 5.4 / 7.0 / 7.4 / 6.8 / 10.0 | 9.4 / 4.2 / 5.6 / 6.0 / 6.0 / 9.6 |
| energy-refused unserved orders (proxy): best rule / 0 / 10 / 20 / forecast / offline | 0.1 / 4.2 / 2.0 / 1.7 / 1.6 / 0.0 | 0.3 / 6.3 / 4.7 / 2.8 / 4.3 / 0.4 | 7.6 / 13.8 / 8.4 / 10.4 / 9.0 / 0.0 | 7.6 / 17.0 / 12.8 / 13.8 / 12.4 / 4.4 |
| electricity, USD: best rule / 0 / 10 / 20 / forecast / offline | 0.68 / 0.03 / 0.01 / 0.03 / 0.09 / 0.08 | 0.71 / 0.01 / 0.02 / 0.01 / 0.03 / 0.05 | 1.18 / 0.06 / 0.24 / 0.22 / 0.15 / 0.76 | 1.18 / 0.01 / 0.01 / 0.09 / 0.11 / 0.63 |

### T5 Components of online coordination (best rule - policy) and foresight (policy - offline), new prices, USD per window (paired)

| component | usd4h: 0 | 10 | 20 | forecast | stress4h: 0 | 10 | 20 | forecast |
|---|---|---|---|---|---|---|---|---|
| coordination: unserved | -126.0 [-233.9, -18.1] | 18.0 [-68.0, 104.0] | 30.0 [-96.8, 156.8] | 36.0 [-78.8, 150.8] | -132.0 [-317.5, 53.5] | 180.0 [22.0, 338.0] | 36.0 [-335.0, 407.0] | 132.0 [-11.3, 275.3] |
| coordination: response | 65.4 [25.9, 104.9] | 49.4 [15.0, 83.7] | 42.9 [4.6, 81.2] | 38.7 [7.5, 69.9] | 149.1 [81.5, 216.7] | 78.6 [17.7, 139.5] | 114.6 [30.6, 198.6] | 88.8 [26.8, 150.8] |
| coordination: lateness | 23.8 [7.1, 40.4] | 30.6 [13.2, 48.0] | 25.5 [6.0, 45.0] | 26.9 [9.3, 44.5] | 74.5 [44.6, 104.4] | 77.5 [36.0, 119.0] | 83.0 [51.2, 114.8] | 74.0 [46.9, 101.1] |
| coordination: other | 3.7 [2.1, 5.3] | 2.0 [0.5, 3.6] | 1.8 [0.2, 3.4] | 1.4 [0.3, 2.5] | 5.5 [4.3, 6.7] | 2.9 [1.8, 4.0] | 3.4 [2.1, 4.6] | 2.6 [1.1, 4.1] |
| foresight: unserved | 264.0 [149.2, 378.8] | 120.0 [44.3, 195.7] | 108.0 [-7.9, 223.9] | 102.0 [7.0, 197.0] | 708.0 [538.1, 877.9] | 396.0 [216.6, 575.4] | 540.0 [304.4, 775.6] | 444.0 [223.0, 665.0] |
| foresight: response | -12.6 [-51.6, 26.4] | 3.5 [-25.0, 31.9] | 9.9 [-20.9, 40.7] | 14.1 [-25.7, 53.9] | -160.5 [-225.0, -96.0] | -90.0 [-127.0, -53.0] | -126.0 [-198.2, -53.8] | -100.2 [-160.8, -39.6] |
| foresight: lateness | 21.8 [12.2, 31.3] | 14.9 [6.5, 23.2] | 20.0 [8.1, 31.9] | 18.6 [8.3, 29.0] | 2.2 [-20.0, 24.5] | -0.8 [-13.8, 12.3] | -6.2 [-19.6, 7.1] | 2.8 [-22.2, 27.7] |
| foresight: other | -2.9 [-3.9, -1.9] | -1.2 [-1.9, -0.5] | -1.0 [-1.8, -0.2] | -0.6 [-1.3, 0.1] | -6.5 [-9.1, -4.0] | -3.9 [-6.3, -1.5] | -4.4 [-6.6, -2.2] | -3.7 [-6.0, -1.4] |

### T6 Change from legacy to new prices on the same instances (new - legacy, paired by seed)

| quantity | usd4h (n = 10) | stress4h (n = 5) |
|---|---|---|
| offline gap, pp of best rule | -0.93 [-5.79, 3.92]; +5/-5; t p = 0.674, W p = 0.770 | 0.07 [-3.56, 3.69]; +2/-3; t p = 0.962, W p = 1.000 |
| share kept, lookahead 0 (mean of ratios) | -0.753 [-1.052, -0.453]; +0/-10; t p < 0.001, W p = 0.002 | -0.505 [-0.649, -0.360]; +0/-5; t p = 0.001, W p = 0.062 |
| share kept, lookahead 10 (mean of ratios) | -0.347 [-0.709, 0.015]; +2/-8; t p = 0.058, W p = 0.037 | -0.248 [-0.346, -0.150]; +0/-5; t p = 0.002, W p = 0.062 |
| share kept, lookahead 20 (mean of ratios) | -0.454 [-0.783, -0.126]; +1/-9; t p = 0.012, W p = 0.006 | -0.463 [-0.808, -0.118]; +0/-5; t p = 0.020, W p = 0.062 |
| share kept, forecast plan (mean of ratios) | -0.574 [-1.328, 0.180]; +0/-10; t p = 0.119, W p = 0.002 | -0.314 [-0.515, -0.113]; +0/-5; t p = 0.012, W p = 0.062 |
| foresight, lookahead 0, pp of best rule | 18.81 [12.23, 25.39]; +10/-0; t p < 0.001, W p = 0.002 | 19.98 [16.31, 23.65]; +5/-0; t p < 0.001, W p = 0.062 |
| foresight, lookahead 10, pp of best rule | 8.02 [0.90, 15.13]; +8/-2; t p = 0.031, W p = 0.027 | 10.21 [4.93, 15.50]; +5/-0; t p = 0.006, W p = 0.062 |
| foresight, lookahead 20, pp of best rule | 11.37 [1.84, 20.91]; +9/-1; t p = 0.024, W p = 0.006 | 17.75 [7.31, 28.18]; +5/-0; t p = 0.009, W p = 0.062 |
| foresight, forecast plan, pp of best rule | 9.69 [1.97, 17.41]; +9/-1; t p = 0.019, W p = 0.004 | 13.09 [3.97, 22.22]; +5/-0; t p = 0.016, W p = 0.062 |
| online coordination, lookahead 0, pp of best rule | -19.75 [-27.29, -12.21]; +1/-9; t p < 0.001, W p = 0.004 | -19.91 [-23.91, -15.92]; +0/-5; t p < 0.001, W p = 0.062 |
| online coordination, lookahead 10, pp of best rule | -8.95 [-17.72, -0.18]; +2/-8; t p = 0.046, W p = 0.049 | -10.15 [-14.60, -5.69]; +0/-5; t p = 0.003, W p = 0.062 |
| online coordination, lookahead 20, pp of best rule | -12.31 [-24.15, -0.47]; +3/-7; t p = 0.043, W p = 0.084 | -17.68 [-27.59, -7.78]; +0/-5; t p = 0.008, W p = 0.062 |
| online coordination, forecast plan, pp of best rule | -10.63 [-18.92, -2.33]; +1/-9; t p = 0.018, W p = 0.006 | -13.03 [-24.31, -1.75]; +0/-5; t p = 0.033, W p = 0.062 |
| served share, lookahead 0, pp | 5.3 [-1.1, 11.7]; +5/-2/3 tie; t p = 0.094, W p = 0.121 | 7.1 [2.8, 11.4]; +5/-0; t p = 0.010, W p = 0.062 |
| served share, lookahead 10, pp | 7.8 [1.0, 14.6]; +7/-1/2 tie; t p = 0.029, W p = 0.035 | 8.8 [4.5, 13.0]; +5/-0; t p = 0.005, W p = 0.062 |
| served share, lookahead 20, pp | 4.7 [-0.2, 9.7]; +7/-1/2 tie; t p = 0.060, W p = 0.068 | 6.2 [-0.8, 13.3]; +4/-0/1 tie; t p = 0.070, W p = 0.068 |
| served share, forecast plan, pp | 7.5 [0.9, 14.1]; +8/-1/1 tie; t p = 0.031, W p = 0.028 | 6.2 [-0.1, 12.6]; +4/-0/1 tie; t p = 0.052, W p = 0.068 |
| lateness, lookahead 0, order-min | 105.0 [49.4, 160.6]; +10/-0; t p = 0.002, W p = 0.002 | 142.0 [28.7, 255.3]; +5/-0; t p = 0.025, W p = 0.062 |
| lateness, lookahead 10, order-min | 83.0 [29.3, 136.7]; +9/-1; t p = 0.007, W p = 0.006 | 137.0 [82.4, 191.6]; +5/-0; t p = 0.002, W p = 0.062 |
| lateness, lookahead 20, order-min | 109.0 [45.4, 172.6]; +10/-0; t p = 0.004, W p = 0.002 | 120.0 [38.1, 201.9]; +5/-0; t p = 0.015, W p = 0.062 |
| lateness, forecast plan, order-min | 101.0 [45.0, 157.0]; +9/-0/1 tie; t p = 0.003, W p = 0.008 | 154.0 [28.6, 279.4]; +5/-0; t p = 0.027, W p = 0.062 |
| contrast 0 -> 10, USD (new - legacy; not comparable in USD across prices, sign only) | 91.84 [34.49, 149.18]; +8/-2; t p = 0.006, W p = 0.010 | 158.03 [114.13, 201.92]; +5/-0; t p = 0.001, W p = 0.062 |
| contrast 10 -> 20, USD (new - legacy; not comparable in USD across prices, sign only) | -28.34 [-116.38, 59.70]; +6/-4; t p = 0.485, W p = 0.770 | -97.66 [-271.93, 76.61]; +2/-3; t p = 0.195, W p = 0.312 |
| contrast plain -> forecast, USD (new - legacy; not comparable in USD across prices, sign only) | -3.76 [-78.02, 70.50]; +4/-6; t p = 0.911, W p = 0.695 | -51.25 [-191.11, 88.60]; +3/-2; t p = 0.366, W p = 0.812 |

### T7 Legacy online schedules repriced at the new prices (legacy schedule repriced - new-price run, USD; positive = the new-price run is cheaper)

| policy | usd4h (n = 10) | seeds where the legacy schedule would be cheaper | stress4h (n = 5) | seeds where the legacy schedule would be cheaper |
|---|---|---|---|---|
| rolling, lookahead 0 min | 14.04 [-65.54, 93.63]; +3/-7; t p = 0.699, W p = 0.922 | [0, 1, 2, 3, 4, 6, 9] | 59.66 [25.81, 93.52]; +5/-0; t p = 0.008, W p = 0.062 | [] |
| rolling, lookahead 10 min | 62.80 [-33.19, 158.80]; +6/-4; t p = 0.173, W p = 0.275 | [0, 3, 6, 9] | 88.14 [-23.11, 199.39]; +5/-0; t p = 0.093, W p = 0.062 | [] |
| rolling, lookahead 20 min | -2.61 [-69.91, 64.70]; +4/-6; t p = 0.932, W p = 1.000 | [1, 2, 3, 4, 5, 6] | 28.23 [-134.17, 190.63]; +3/-2; t p = 0.655, W p = 0.812 | [1, 4] |
| rolling + forecast battery plan, 10 min | 48.10 [-30.43, 126.63]; +6/-4; t p = 0.199, W p = 0.275 | [0, 1, 4, 9] | 25.94 [-158.86, 210.73]; +3/-2; t p = 0.717, W p = 0.812 | [1, 3] |

### A1 Per instance, new prices (end-adjusted USD; kept = share of the offline gap kept online; TL = windows at the 60 s limit of 8; fb = fallback windows of 8)

| family | seed | best rule (name) | offline (status, MIP gap) | cost 0 / 10 / 20 / forecast | kept 0 / 10 / 20 / forecast | served % 0 / 10 / 20 / fc / best / offline | TL 0 / 10 / 20 / fc | fb 0 / 10 / 20 / fc | (9) bikes 0 / 10 / 20 / fc |
|---|---|---|---|---|---|---|---|---|---|
| usd4h | 0 | 599.96 (r2) | 534.18 (OPTIMAL, 0.00 %) | 730.79 / 699.14 / 618.73 / 830.43 | -1.989 / -1.508 / -0.285 / -3.504 | 94.4 / 94.4 / 97.2 / 86.1 / 100.0 / 100.0 | 0 / 0 / 0 / 0 | 4 / 4 / 4 / 4 | 2 / 2 / 2 / 3 |
| usd4h | 1 | 886.04 (r2) | 592.47 (OPTIMAL, 0.01 %) | 823.53 / 667.49 / 683.55 / 759.16 | 0.213 / 0.744 / 0.690 / 0.432 | 88.9 / 97.2 / 97.2 / 91.7 / 88.9 / 100.0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 4 | 0 / 0 / 0 / 1 |
| usd4h | 2 | 824.24 (r2) | 618.13 (OPTIMAL, 0.00 %) | 1030.47 / 781.29 / 654.24 / 869.42 | -1.001 / 0.208 / 0.825 / -0.219 | 72.2 / 86.1 / 94.4 / 80.6 / 88.9 / 97.2 | 0 / 0 / 0 / 0 | 4 / 4 / 0 / 4 | 2 / 1 / 0 / 1 |
| usd4h | 3 | 902.18 (r2) | 614.48 (OPTIMAL, 0.00 %) | 915.60 / 845.57 / 1083.74 / 700.43 | -0.047 / 0.197 / -0.631 / 0.701 | 83.3 / 86.1 / 72.2 / 94.4 / 88.9 / 97.2 | 0 / 0 / 2 / 0 | 4 / 4 / 4 / 0 | 1 / 1 / 1 / 0 |
| usd4h | 4 | 716.97 (r2) | 545.80 (OPTIMAL, 0.00 %) | 661.94 / 587.71 / 551.14 / 590.72 | 0.322 / 0.755 / 0.969 / 0.738 | 94.4 / 97.2 / 100.0 / 97.2 / 91.7 / 100.0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| usd4h | 5 | 875.41 (M2) | 634.99 (OPTIMAL, 0.00 %) | 1012.67 / 729.31 / 843.46 / 728.24 | -0.571 / 0.608 / 0.133 / 0.612 | 77.8 / 97.2 / 91.7 / 97.2 / 91.7 / 97.2 | 0 / 0 / 1 / 0 | 4 / 4 / 0 / 4 | 3 / 1 / 0 / 1 |
| usd4h | 6 | 956.87 (r2) | 617.76 (OPTIMAL, 0.01 %) | 1037.15 / 907.80 / 830.40 / 724.42 | -0.237 / 0.145 / 0.373 / 0.685 | 77.8 / 83.3 / 88.9 / 97.2 / 91.7 / 97.2 | 0 / 0 / 0 / 0 | 4 / 4 / 4 / 4 | 3 / 3 / 2 / 1 |
| usd4h | 7 | 749.38 (r2) | 610.67 (OPTIMAL, 0.00 %) | 825.20 / 676.03 / 785.86 / 713.93 | -0.547 / 0.529 / -0.263 / 0.256 | 94.4 / 100.0 / 97.2 / 100.0 / 100.0 / 100.0 | 0 / 0 / 1 / 0 | 4 / 4 / 0 / 4 | 2 / 1 / 0 / 1 |
| usd4h | 8 | 994.81 (r2) | 667.31 (OPTIMAL, 0.00 %) | 803.14 / 776.07 / 722.79 / 773.31 | 0.585 / 0.668 / 0.831 / 0.676 | 97.2 / 97.2 / 100.0 / 97.2 / 94.4 / 100.0 | 0 / 0 / 0 / 0 | 4 / 4 / 4 / 4 | 1 / 2 / 1 / 1 |
| usd4h | 9 | 879.18 (M2) | 578.31 (OPTIMAL, 0.00 %) | 876.05 / 714.64 / 609.18 / 665.03 | 0.010 / 0.547 / 0.897 / 0.712 | 86.1 / 94.4 / 100.0 / 100.0 / 88.9 / 100.0 | 0 / 0 / 0 / 0 | 4 / 4 / 0 / 0 | 1 / 1 / 0 / 0 |
| stress4h | 0 | 1183.98 (r2) | 787.82 (OPTIMAL, 0.00 %) | 1265.21 / 1005.22 / 1373.90 / 957.73 | -0.205 / 0.451 / -0.479 / 0.571 | 77.1 / 89.6 / 72.9 / 91.7 / 89.6 / 100.0 | 0 / 0 / 1 / 0 | 4 / 4 / 4 / 4 | 2 / 1 / 2 / 1 |
| stress4h | 1 | 1684.78 (M2) | 1031.31 (TIME_LIMIT, 0.87 %) | 1518.36 / 1231.16 / 1300.21 / 1384.54 | 0.255 / 0.694 / 0.588 / 0.459 | 72.9 / 83.3 / 81.2 / 79.2 / 72.9 / 91.7 | 1 / 0 / 2 / 1 | 0 / 4 / 0 / 0 | 0 / 1 / 0 / 0 |
| stress4h | 2 | 1730.79 (M2) | 1015.58 (TIME_LIMIT, 0.40 %) | 1677.00 / 1505.73 / 1476.99 / 1451.81 | 0.075 / 0.315 / 0.355 / 0.390 | 60.4 / 70.8 / 68.8 / 70.8 / 66.7 / 91.7 | 0 / 0 / 0 / 1 | 4 / 4 / 4 / 4 | 3 / 2 / 2 / 2 |
| stress4h | 3 | 1754.85 (M2) | 958.82 (TIME_LIMIT, 0.14 %) | 1557.49 / 1301.02 / 1269.29 / 1476.48 | 0.248 / 0.570 / 0.610 / 0.350 | 68.8 / 79.2 / 81.2 / 72.9 / 72.9 / 95.8 | 1 / 0 / 1 / 1 | 4 / 4 / 4 / 4 | 2 / 1 / 1 / 1 |
| stress4h | 4 | 1554.41 (M2) | 913.79 (OPTIMAL, 0.00 %) | 1405.34 / 1170.79 / 1303.63 / 1151.09 | 0.233 / 0.599 / 0.391 / 0.630 | 75.0 / 85.4 / 79.2 / 85.4 / 75.0 / 97.9 | 0 / 0 / 1 / 0 | 4 / 0 / 0 / 0 | 2 / 0 / 0 / 0 |

### A2 Per instance, legacy prices (end-adjusted USD)

| family | seed | best rule (name) | offline (status, MIP gap) | cost 0 / 10 / 20 / forecast | kept 0 / 10 / 20 / forecast | fb 0 / 10 / 20 / fc |
|---|---|---|---|---|---|---|
| usd4h | 0 | 613.10 (M2) | 534.17 (OPTIMAL, 0.01 %) | 650.51 / 609.26 / 594.41 / 609.29 | -0.474 / 0.049 / 0.237 / 0.048 | 4 / 4 / 4 / 4 |
| usd4h | 1 | 830.79 (r2) | 583.98 (OPTIMAL, 0.01 %) | 642.57 / 643.40 / 598.03 / 643.38 | 0.763 / 0.759 / 0.943 / 0.759 | 0 / 4 / 0 / 4 |
| usd4h | 2 | 730.17 (M2) | 584.22 (OPTIMAL, 0.00 %) | 713.09 / 679.08 / 586.06 / 678.83 | 0.117 / 0.350 / 0.987 / 0.352 | 4 / 4 / 0 / 4 |
| usd4h | 3 | 857.43 (r2) | 584.80 (OPTIMAL, 0.00 %) | 695.52 / 647.83 / 658.10 / 614.91 | 0.594 / 0.769 / 0.731 / 0.890 | 4 / 4 / 4 / 0 |
| usd4h | 4 | 636.52 (M2) | 547.56 (OPTIMAL, 0.00 %) | 601.34 / 574.07 / 549.07 / 556.19 | 0.395 / 0.702 / 0.983 / 0.903 | 0 / 0 / 0 / 0 |
| usd4h | 5 | 867.66 (M2) | 590.33 (OPTIMAL, 0.01 %) | 780.40 / 686.92 / 629.60 / 648.27 | 0.315 / 0.652 / 0.858 / 0.791 | 4 / 4 / 0 / 4 |
| usd4h | 6 | 1005.12 (r2) | 589.16 (OPTIMAL, 0.00 %) | 693.89 / 625.53 / 651.67 / 654.94 | 0.748 / 0.913 / 0.850 / 0.842 | 4 / 4 / 4 / 4 |
| usd4h | 7 | 829.88 (r2) | 598.86 (OPTIMAL, 0.00 %) | 749.65 / 728.65 / 663.63 / 718.23 | 0.347 / 0.438 / 0.720 / 0.483 | 4 / 4 / 4 / 4 |
| usd4h | 8 | 1116.81 (r2) | 627.33 (OPTIMAL, 0.00 %) | 695.81 / 665.65 / 643.08 / 684.24 | 0.860 / 0.922 / 0.968 / 0.884 | 4 / 4 / 0 / 4 |
| usd4h | 9 | 821.58 (r2) | 580.07 (OPTIMAL, 0.00 %) | 676.68 / 625.96 / 627.33 / 610.53 | 0.600 / 0.810 / 0.804 / 0.874 | 4 / 0 / 4 / 0 |
| stress4h | 0 | 1135.48 (r2) | 751.55 (OPTIMAL, 0.00 %) | 942.88 / 889.87 / 963.09 / 865.03 | 0.502 / 0.640 / 0.449 / 0.704 | 4 / 4 / 4 / 4 |
| stress4h | 1 | 1482.03 (M2) | 858.96 (OPTIMAL, 0.00 %) | 1051.64 / 942.77 / 905.74 / 935.84 | 0.691 / 0.865 / 0.925 / 0.877 | 4 / 4 / 0 / 4 |
| stress4h | 2 | 1387.29 (M2) | 856.85 (TIME_LIMIT, 0.09 %) | 1081.90 / 1025.74 / 1012.98 / 1007.00 | 0.576 / 0.682 / 0.706 / 0.717 | 4 / 4 / 4 / 4 |
| stress4h | 3 | 1595.85 (M2) | 837.18 (OPTIMAL, 0.00 %) | 1062.57 / 949.92 / 972.66 / 937.56 | 0.703 / 0.851 / 0.821 / 0.868 | 4 / 4 / 4 / 4 |
| stress4h | 4 | 1336.16 (M2) | 825.97 (OPTIMAL, 0.00 %) | 1000.75 / 912.07 / 887.71 / 926.40 | 0.657 / 0.831 / 0.879 / 0.803 | 4 / 4 / 4 / 4 |

### T8 Windows stopped at the 60 s limit (new prices; every non-OPTIMAL window of the 60 runs)

| family | seed | policy | window start (slot) | MIP gap at 60 s, % | fallback window | run wall clock (server, UTC) |
|---|---|---|---|---|---|---|
| usd4h | 3 | lookahead 20 | 18 | 43.69 | no | 2026-10-20 00:30:29 |
| usd4h | 3 | lookahead 20 | 24 | 38.24 | yes | 2026-10-20 00:30:29 |
| usd4h | 5 | lookahead 20 | 18 | 70.04 | no | 2026-10-20 01:20:18 |
| usd4h | 7 | lookahead 20 | 12 | 69.29 | no | 2026-10-20 01:41:17 |
| stress4h | 0 | lookahead 20 | 18 | 101.47 | no | 2026-10-19 23:34:19 |
| stress4h | 1 | lookahead 0 | 18 | 65.25 | no | 2026-10-19 23:52:43 |
| stress4h | 1 | lookahead 20 | 12 | 71.49 | no | 2026-10-19 23:56:09 |
| stress4h | 1 | lookahead 20 | 24 | 0.43 | no | 2026-10-19 23:56:09 |
| stress4h | 1 | forecast plan | 18 | 101.62 | no | 2026-10-20 00:04:48 |
| stress4h | 2 | forecast plan | 24 | 0.05 | yes | 2026-10-20 00:25:53 |
| stress4h | 3 | lookahead 0 | 18 | 27.27 | no | 2026-10-20 00:39:52 |
| stress4h | 3 | lookahead 20 | 12 | 0.40 | no | 2026-10-20 00:44:35 |
| stress4h | 3 | forecast plan | 24 | 42.54 | yes | 2026-10-20 00:52:51 |
| stress4h | 4 | lookahead 20 | 24 | 97.72 | no | 2026-10-20 01:08:27 |

### T9 Window solve times by machine (OPTIMAL windows only; mean / max s; orders per window incl. forecast orders)

| round | family | policy | machine | windows | stopped at 60 s (gap > 1 %) | mean / max run time, s | orders per window |
|---|---|---|---|---|---|---|---|
| legacy | usd4h | lookahead 0 | laptop (round 5) | 80 | 0 (0) | 2.55 / 11.3 | 6.7 |
| legacy | usd4h | lookahead 10 | laptop (round 5) | 80 | 0 (0) | 3.86 / 17.5 | 7.6 |
| legacy | usd4h | lookahead 20 | laptop (round 5) | 80 | 0 (0) | 5.78 / 29.2 | 8.9 |
| legacy | usd4h | forecast plan | laptop (round 5) | 80 | 0 (0) | 3.82 / 19.6 | 20.1 |
| legacy | stress4h | lookahead 0 | laptop (round 5) | 40 | 0 (0) | 3.62 / 9.9 | 12.1 |
| legacy | stress4h | lookahead 10 | laptop (round 5) | 40 | 0 (0) | 5.18 / 13.7 | 12.6 |
| legacy | stress4h | lookahead 20 | laptop (round 5) | 40 | 0 (0) | 8.30 / 26.2 | 15.1 |
| legacy | stress4h | forecast plan | laptop (round 5) | 40 | 0 (0) | 5.86 / 26.0 | 28.4 |
| new | usd4h | lookahead 0 | server (r7i.4xlarge, 5 lanes x 3 threads on 8 cores) | 80 | 0 (0) | 6.55 / 36.0 | 6.2 |
| new | usd4h | lookahead 10 | laptop (arm64 macOS, 2026-10-18, r6_penalty lanes) | 80 | 0 (0) | 3.64 / 21.9 | 7.1 |
| new | usd4h | lookahead 20 | server (r7i.4xlarge, 5 lanes x 3 threads on 8 cores) | 80 | 4 (4) | 12.82 / 56.7 | 8.9 |
| new | usd4h | forecast plan | server (r7i.4xlarge, 5 lanes x 3 threads on 8 cores) | 80 | 0 (0) | 10.05 / 58.4 | 19.5 |
| new | stress4h | lookahead 0 | server (r7i.4xlarge, 5 lanes x 3 threads on 8 cores) | 40 | 2 (2) | 11.00 / 55.7 | 11.8 |
| new | stress4h | lookahead 10 | laptop (arm64 macOS, 2026-10-18, r6_penalty lanes) | 40 | 0 (0) | 8.67 / 42.9 | 11.8 |
| new | stress4h | lookahead 20 | server (r7i.4xlarge, 5 lanes x 3 threads on 8 cores) | 40 | 5 (3) | 17.12 / 56.4 | 15.0 |
| new | stress4h | forecast plan | server (r7i.4xlarge, 5 lanes x 3 threads on 8 cores) | 40 | 3 (2) | 14.75 / 59.9 | 28.6 |

Ratio of mean window run time, lookahead 0 / lookahead 10, legacy prices: usd4h 0.66, stress4h 0.70.

Ratio of mean window run time, lookahead 0 / lookahead 10, new prices: usd4h 1.80, stress4h 1.27.

### T10 Post hoc sensitivity: seeds whose runs have no window stopped at 60 s with a MIP gap above 1 % (new prices)

| quantity | usd4h | stress4h |
|---|---|---|
| lookahead 0 -> 10 min, USD | 133.15 [71.59, 194.70]; +10/-0; t p = 0.001, W p = 0.002 (seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]); excluded seeds []: [] | 221.94 [108.45, 335.42]; +3/-0; t p = 0.014, W p = 0.250 (seeds [0, 2, 4]); excluded seeds [1, 3]: [287.21, 256.47] |
| lookahead 10 -> 20 min, USD | 66.30 [22.62, 109.98]; +6/-1; t p = 0.010, W p = 0.031 (seeds [0, 1, 2, 4, 6, 8, 9]); excluded seeds [3, 5, 7]: [-238.16, -114.15, -109.83] | 30.23 [11.22, 49.24]; +2/-0; t p = 0.031, W p = 0.500 (seeds [2, 3]); excluded seeds [0, 1, 4]: [-368.68, -69.05, -132.84] |
| plain rolling -> forecast battery plan, USD | 3.00 [-69.30, 75.29]; +5/-5; t p = 0.927, W p = 1.000 (seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]); excluded seeds []: [] | 40.37 [-4.81, 85.55]; +3/-0; t p = 0.061, W p = 0.250 (seeds [0, 2, 4]); excluded seeds [1, 3]: [-153.38, -175.46] |
| share kept, lookahead 0, mean of ratios | -0.326 [-0.863, 0.211] (n = 10) | 0.034 [-0.517, 0.585] (n = 3) |
| share kept, lookahead 10, mean of ratios | 0.289 [-0.191, 0.770] (n = 10) | 0.526 [0.344, 0.708] (n = 5) |
| share kept, lookahead 20, mean of ratios | 0.614 [0.206, 1.023] (n = 7) | 0.482 [-1.138, 2.103] (n = 2) |
| share kept, forecast plan, mean of ratios | 0.109 [-0.824, 1.042] (n = 10) | 0.530 [0.220, 0.840] (n = 3) |

### T11 Runs with the unpriced terminal fallback (at least one window re-solved with the dummy terminal arc; C_dummy_terminal = 0 in every row)

| family | prices | lookahead 0 | lookahead 10 | lookahead 20 | forecast plan |
|---|---|---|---|---|---|
| usd4h | new | 8/10 | 8/10 | 4/10 | 7/10 |
| usd4h | legacy | 8/10 | 8/10 | 5/10 | 7/10 |
| stress4h | new | 4/5 | 4/5 | 3/5 | 3/5 |
| stress4h | legacy | 5/5 | 5/5 | 4/5 | 5/5 |

Total: new prices 41/60 runs (29/45 in rolling_ext), legacy prices 47/60; fallback run <=> terminal certificate (9) broken: True.
