# R6 pack -- pack-size axis of the fleet sweep (rules), joined to the 0.6 kWh grid (P 60, w 18, v 15)

Rule-only cells K {4, 6, 8, 10} x B {1..4} x pack {0.5, 0.75, 1.0} kWh, seeds 0-2, relaxed control, repriced; the 0.6 kWh grid (rules + ILP) from r6_penalty/fleet.  System cost = end-adjusted best-rule total (spare set-up (27) included) + K x allocated bike (+ rider) cost per window.  Means +- exact t 95 % over seeds.

## Cost-minimal design per pack (best rule, seed-mean system cost)

| pack_kwh | K | B_per_site | system_cost_mean | system_cost_ci95 | served_share_mean | n_seeds |
|---|---|---|---|---|---|---|
| 0.50 | 10 | 4 | 1684.89 | 154.49 | 0.99 | 3 |
| 0.60 | 8 | 4 | 1619.60 | 363.43 | 0.98 | 3 |
| 0.75 | 8 | 4 | 1611.83 | 347.13 | 0.99 | 3 |
| 1 | 8 | 4 | 1606.78 | 288.82 | 0.99 | 3 |

## Iso-cost frontier (best rule): marginal value of a bike vs a spare per (pack, K, B)

| pack_kwh | K | B_per_site | V | dV_bike | dV_spare | alloc_per_bike | bike_net | cheaper_lever |
|---|---|---|---|---|---|---|---|---|
| 0.50 | 4 | 1 | 2288.52 | 148.66 | 73.53 | 88.94 | 59.71 | spare |
| 0.50 | 4 | 2 | 2067.92 | 258.06 | -1.68 | 88.94 | 169.12 | bike |
| 0.50 | 4 | 3 | 2072.96 | 314.97 | 4.24 | 88.94 | 226.03 | bike |
| 0.50 | 4 | 4 | 2060.25 | 308.76 | - | 88.94 | 219.82 | - |
| 0.50 | 6 | 1 | 1991.21 | 66.16 | 146.47 | 88.94 | -22.78 | spare |
| 0.50 | 6 | 2 | 1551.79 | 114.54 | 36.26 | 88.94 | 25.59 | spare |
| 0.50 | 6 | 3 | 1443.02 | 189.72 | 0.10 | 88.94 | 100.77 | bike |
| 0.50 | 6 | 4 | 1442.72 | 220.89 | - | 88.94 | 131.95 | - |
| 0.50 | 8 | 1 | 1858.89 | 122.25 | 178.72 | 88.94 | 33.30 | spare |
| 0.50 | 8 | 2 | 1322.72 | 114.65 | 86.38 | 88.94 | 25.71 | spare |
| 0.50 | 8 | 3 | 1063.59 | 90.19 | 20.88 | 88.94 | 1.25 | spare |
| 0.50 | 8 | 4 | 1000.93 | 102.74 | - | 88.94 | 13.79 | - |
| 0.50 | 10 | 1 | 1614.40 | - | 173.66 | 88.94 | - | - |
| 0.50 | 10 | 2 | 1093.42 | - | 70.07 | 88.94 | - | - |
| 0.50 | 10 | 3 | 883.21 | - | 29.25 | 88.94 | - | - |
| 0.50 | 10 | 4 | 795.46 | - | - | 88.94 | - | - |
| 0.60 | 4 | 1 | 2226.96 | 71.96 | 65.16 | 88.94 | -16.98 | spare |
| 0.60 | 4 | 2 | 2031.48 | 249.15 | 0.70 | 88.94 | 160.21 | bike |
| 0.60 | 4 | 3 | 2029.39 | 275.11 | -0.33 | 88.94 | 186.17 | bike |
| 0.60 | 4 | 4 | 2030.37 | 293.18 | - | 88.94 | 204.24 | - |
| 0.60 | 6 | 1 | 2083.04 | 177.94 | 183.29 | 88.94 | 89.00 | spare |
| 0.60 | 6 | 2 | 1533.18 | 165.99 | 18.01 | 88.94 | 77.05 | bike |
| 0.60 | 6 | 3 | 1479.16 | 245.91 | 11.72 | 88.94 | 156.97 | bike |
| 0.60 | 6 | 4 | 1444.00 | 267.98 | - | 88.94 | 179.03 | - |
| 0.60 | 8 | 1 | 1727.16 | 60.12 | 175.32 | 88.94 | -28.83 | spare |
| 0.60 | 8 | 2 | 1201.20 | 48.91 | 71.29 | 88.94 | -40.03 | spare |
| 0.60 | 8 | 3 | 987.34 | 79.70 | 26.43 | 88.94 | -9.24 | spare |
| 0.60 | 8 | 4 | 908.05 | 60.23 | - | 88.94 | -28.71 | - |
| 0.60 | 10 | 1 | 1606.92 | - | 167.85 | 88.94 | - | - |
| 0.60 | 10 | 2 | 1103.38 | - | 91.81 | 88.94 | - | - |
| 0.60 | 10 | 3 | 827.94 | - | 13.45 | 88.94 | - | - |
| 0.60 | 10 | 4 | 787.59 | - | - | 88.94 | - | - |
| 0.75 | 4 | 1 | 2253.50 | 122.54 | 53.12 | 88.94 | 33.60 | spare |
| 0.75 | 4 | 2 | 2094.15 | 336.77 | -2.36 | 88.94 | 247.82 | bike |
| 0.75 | 4 | 3 | 2101.22 | 341.16 | 1.97 | 88.94 | 252.22 | bike |
| 0.75 | 4 | 4 | 2095.32 | 335.06 | - | 88.94 | 246.12 | - |
| 0.75 | 6 | 1 | 2008.41 | 103.24 | 195.93 | 88.94 | 14.30 | spare |
| 0.75 | 6 | 2 | 1420.61 | 109.08 | 0.57 | 88.94 | 20.14 | bike |
| 0.75 | 6 | 3 | 1418.91 | 225.89 | -2.10 | 88.94 | 136.95 | bike |
| 0.75 | 6 | 4 | 1425.20 | 262.46 | - | 88.94 | 173.51 | - |
| 0.75 | 8 | 1 | 1801.92 | 62.29 | 199.83 | 88.94 | -26.65 | spare |
| 0.75 | 8 | 2 | 1202.45 | 101.76 | 78.44 | 88.94 | 12.82 | spare |
| 0.75 | 8 | 3 | 967.13 | 85.55 | 22.28 | 88.94 | -3.39 | spare |
| 0.75 | 8 | 4 | 900.28 | 57.18 | - | 88.94 | -31.76 | - |
| 0.75 | 10 | 1 | 1677.34 | - | 226.14 | 88.94 | - | - |
| 0.75 | 10 | 2 | 998.92 | - | 67.63 | 88.94 | - | - |
| 0.75 | 10 | 3 | 796.03 | - | 3.37 | 88.94 | - | - |
| 0.75 | 10 | 4 | 785.92 | - | - | 88.94 | - | - |
| 1 | 4 | 1 | 2182.14 | 165.31 | 46.47 | 88.94 | 76.37 | bike |
| 1 | 4 | 2 | 2042.74 | 306.36 | -1.84 | 88.94 | 217.42 | bike |
| 1 | 4 | 3 | 2048.27 | 323.81 | -0.55 | 88.94 | 234.86 | bike |
| 1 | 4 | 4 | 2049.93 | 321.98 | - | 88.94 | 233.03 | - |
| 1 | 6 | 1 | 1851.52 | 130.34 | 140.50 | 88.94 | 41.39 | spare |
| 1 | 6 | 2 | 1430.02 | 182.27 | 9.79 | 88.94 | 93.33 | bike |
| 1 | 6 | 3 | 1400.65 | 249.12 | -1.77 | 88.94 | 160.18 | bike |
| 1 | 6 | 4 | 1405.98 | 255.37 | - | 88.94 | 166.43 | - |
| 1 | 8 | 1 | 1590.84 | 98.27 | 175.12 | 88.94 | 9.33 | spare |
| 1 | 8 | 2 | 1065.47 | 44.11 | 54.35 | 88.94 | -44.84 | spare |
| 1 | 8 | 3 | 902.41 | 48.64 | 2.39 | 88.94 | -40.30 | spare |
| 1 | 8 | 4 | 895.23 | 44.57 | - | 88.94 | -44.37 | - |
| 1 | 10 | 1 | 1394.30 | - | 139.01 | 88.94 | - | - |
| 1 | 10 | 2 | 977.26 | - | 57.38 | 88.94 | - | - |
| 1 | 10 | 3 | 805.13 | - | -0.32 | 88.94 | - | - |
| 1 | 10 | 4 | 806.09 | - | - | 88.94 | - | - |

## Grid means

| pack_kwh | K | B_per_site | metric | mean | ci95 | n |
|---|---|---|---|---|---|---|
| 0.50 | 4 | 1 | best_system_cost | 2644.30 | 204.67 | 3 |
| 0.50 | 4 | 1 | best_rule_served_share | 0.47 | 0.12 | 3 |
| 0.50 | 4 | 2 | best_system_cost | 2423.70 | 301.22 | 3 |
| 0.50 | 4 | 2 | best_rule_served_share | 0.58 | 0.11 | 3 |
| 0.50 | 4 | 3 | best_system_cost | 2428.73 | 344.47 | 3 |
| 0.50 | 4 | 3 | best_rule_served_share | 0.58 | 0.14 | 3 |
| 0.50 | 4 | 4 | best_system_cost | 2416.02 | 339.76 | 3 |
| 0.50 | 4 | 4 | best_rule_served_share | 0.59 | 0.13 | 3 |
| 0.50 | 6 | 1 | best_system_cost | 2524.87 | 530.57 | 3 |
| 0.50 | 6 | 1 | best_rule_served_share | 0.58 | 0.18 | 3 |
| 0.50 | 6 | 2 | best_system_cost | 2085.45 | 569.37 | 3 |
| 0.50 | 6 | 2 | best_rule_served_share | 0.75 | 0.19 | 3 |
| 0.50 | 6 | 3 | best_system_cost | 1976.68 | 714.60 | 3 |
| 0.50 | 6 | 3 | best_rule_served_share | 0.83 | 0.20 | 3 |
| 0.50 | 6 | 4 | best_system_cost | 1976.38 | 711.89 | 3 |
| 0.50 | 6 | 4 | best_rule_served_share | 0.83 | 0.20 | 3 |
| 0.50 | 8 | 1 | best_system_cost | 2570.44 | 730.60 | 3 |
| 0.50 | 8 | 1 | best_rule_served_share | 0.62 | 0.29 | 3 |
| 0.50 | 8 | 2 | best_system_cost | 2034.27 | 882.69 | 3 |
| 0.50 | 8 | 2 | best_rule_served_share | 0.83 | 0.29 | 3 |
| 0.50 | 8 | 3 | best_system_cost | 1775.13 | 462.93 | 3 |
| 0.50 | 8 | 3 | best_rule_served_share | 0.92 | 0.09 | 3 |
| 0.50 | 8 | 4 | best_system_cost | 1712.48 | 433.50 | 3 |
| 0.50 | 8 | 4 | best_rule_served_share | 0.94 | 0.08 | 3 |
| 0.50 | 10 | 1 | best_system_cost | 2503.83 | 641.76 | 3 |
| 0.50 | 10 | 1 | best_rule_served_share | 0.72 | 0.21 | 3 |
| 0.50 | 10 | 2 | best_system_cost | 1982.86 | 980.05 | 3 |
| 0.50 | 10 | 2 | best_rule_served_share | 0.89 | 0.32 | 3 |
| 0.50 | 10 | 3 | best_system_cost | 1772.64 | 420.93 | 3 |
| 0.50 | 10 | 3 | best_rule_served_share | 0.97 | 0.11 | 3 |
| 0.50 | 10 | 4 | best_system_cost | 1684.89 | 154.49 | 3 |
| 0.50 | 10 | 4 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 0.60 | 4 | 1 | best_system_cost | 2582.73 | 79.35 | 3 |
| 0.60 | 4 | 1 | best_rule_served_share | 0.50 | 0.05 | 3 |
| 0.60 | 4 | 2 | best_system_cost | 2387.26 | 288.48 | 3 |
| 0.60 | 4 | 2 | best_rule_served_share | 0.60 | 0.11 | 3 |
| 0.60 | 4 | 3 | best_system_cost | 2385.16 | 400.06 | 3 |
| 0.60 | 4 | 3 | best_rule_served_share | 0.61 | 0.16 | 3 |
| 0.60 | 4 | 4 | best_system_cost | 2386.14 | 400.12 | 3 |
| 0.60 | 4 | 4 | best_rule_served_share | 0.61 | 0.16 | 3 |
| 0.60 | 6 | 1 | best_system_cost | 2616.70 | 300.02 | 3 |
| 0.60 | 6 | 1 | best_rule_served_share | 0.55 | 0.06 | 3 |
| 0.60 | 6 | 2 | best_system_cost | 2066.84 | 753.42 | 3 |
| 0.60 | 6 | 2 | best_rule_served_share | 0.76 | 0.29 | 3 |
| 0.60 | 6 | 3 | best_system_cost | 2012.82 | 741.39 | 3 |
| 0.60 | 6 | 3 | best_rule_served_share | 0.81 | 0.20 | 3 |
| 0.60 | 6 | 4 | best_system_cost | 1977.66 | 657.36 | 3 |
| 0.60 | 6 | 4 | best_rule_served_share | 0.82 | 0.17 | 3 |
| 0.60 | 8 | 1 | best_system_cost | 2438.71 | 679.18 | 3 |
| 0.60 | 8 | 1 | best_rule_served_share | 0.68 | 0.29 | 3 |
| 0.60 | 8 | 2 | best_system_cost | 1912.75 | 931.26 | 3 |
| 0.60 | 8 | 2 | best_rule_served_share | 0.88 | 0.29 | 3 |
| 0.60 | 8 | 3 | best_system_cost | 1698.88 | 529.53 | 3 |
| 0.60 | 8 | 3 | best_rule_served_share | 0.95 | 0.13 | 3 |
| 0.60 | 8 | 4 | best_system_cost | 1619.60 | 363.43 | 3 |
| 0.60 | 8 | 4 | best_rule_served_share | 0.98 | 0.05 | 3 |
| 0.60 | 10 | 1 | best_system_cost | 2496.36 | 624.25 | 3 |
| 0.60 | 10 | 1 | best_rule_served_share | 0.72 | 0.24 | 3 |
| 0.60 | 10 | 2 | best_system_cost | 1992.81 | 776.86 | 3 |
| 0.60 | 10 | 2 | best_rule_served_share | 0.90 | 0.21 | 3 |
| 0.60 | 10 | 3 | best_system_cost | 1717.37 | 231.54 | 3 |
| 0.60 | 10 | 3 | best_rule_served_share | 0.98 | 0.05 | 3 |
| 0.60 | 10 | 4 | best_system_cost | 1677.02 | 167.71 | 3 |
| 0.60 | 10 | 4 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 0.75 | 4 | 1 | best_system_cost | 2609.27 | 288.80 | 3 |
| 0.75 | 4 | 1 | best_rule_served_share | 0.49 | 0.13 | 3 |
| 0.75 | 4 | 2 | best_system_cost | 2449.92 | 331.01 | 3 |
| 0.75 | 4 | 2 | best_rule_served_share | 0.59 | 0.17 | 3 |
| 0.75 | 4 | 3 | best_system_cost | 2457.00 | 341.28 | 3 |
| 0.75 | 4 | 3 | best_rule_served_share | 0.59 | 0.17 | 3 |
| 0.75 | 4 | 4 | best_system_cost | 2451.10 | 327.05 | 3 |
| 0.75 | 4 | 4 | best_rule_served_share | 0.60 | 0.15 | 3 |
| 0.75 | 6 | 1 | best_system_cost | 2542.07 | 352.56 | 3 |
| 0.75 | 6 | 1 | best_rule_served_share | 0.61 | 0.12 | 3 |
| 0.75 | 6 | 2 | best_system_cost | 1954.27 | 578.16 | 3 |
| 0.75 | 6 | 2 | best_rule_served_share | 0.84 | 0.13 | 3 |
| 0.75 | 6 | 3 | best_system_cost | 1952.57 | 565.93 | 3 |
| 0.75 | 6 | 3 | best_rule_served_share | 0.83 | 0.14 | 3 |
| 0.75 | 6 | 4 | best_system_cost | 1958.86 | 581.94 | 3 |
| 0.75 | 6 | 4 | best_rule_served_share | 0.84 | 0.13 | 3 |
| 0.75 | 8 | 1 | best_system_cost | 2513.47 | 341.45 | 3 |
| 0.75 | 8 | 1 | best_rule_served_share | 0.64 | 0.15 | 3 |
| 0.75 | 8 | 2 | best_system_cost | 1913.99 | 751.78 | 3 |
| 0.75 | 8 | 2 | best_rule_served_share | 0.90 | 0.21 | 3 |
| 0.75 | 8 | 3 | best_system_cost | 1678.68 | 536.88 | 3 |
| 0.75 | 8 | 3 | best_rule_served_share | 0.97 | 0.08 | 3 |
| 0.75 | 8 | 4 | best_system_cost | 1611.83 | 347.13 | 3 |
| 0.75 | 8 | 4 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 0.75 | 10 | 1 | best_system_cost | 2566.78 | 170.73 | 3 |
| 0.75 | 10 | 1 | best_rule_served_share | 0.70 | 0.11 | 3 |
| 0.75 | 10 | 2 | best_system_cost | 1888.35 | 497.43 | 3 |
| 0.75 | 10 | 2 | best_rule_served_share | 0.97 | 0.08 | 3 |
| 0.75 | 10 | 3 | best_system_cost | 1685.46 | 189.29 | 3 |
| 0.75 | 10 | 3 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 0.75 | 10 | 4 | best_system_cost | 1675.35 | 179.78 | 3 |
| 0.75 | 10 | 4 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 1 | 4 | 1 | best_system_cost | 2537.92 | 216.77 | 3 |
| 1 | 4 | 1 | best_rule_served_share | 0.51 | 0.08 | 3 |
| 1 | 4 | 2 | best_system_cost | 2398.52 | 335.64 | 3 |
| 1 | 4 | 2 | best_rule_served_share | 0.62 | 0.13 | 3 |
| 1 | 4 | 3 | best_system_cost | 2404.04 | 335.14 | 3 |
| 1 | 4 | 3 | best_rule_served_share | 0.61 | 0.13 | 3 |
| 1 | 4 | 4 | best_system_cost | 2405.70 | 335.14 | 3 |
| 1 | 4 | 4 | best_rule_served_share | 0.61 | 0.13 | 3 |
| 1 | 6 | 1 | best_system_cost | 2385.18 | 271.70 | 3 |
| 1 | 6 | 1 | best_rule_served_share | 0.62 | 0.11 | 3 |
| 1 | 6 | 2 | best_system_cost | 1963.68 | 569.67 | 3 |
| 1 | 6 | 2 | best_rule_served_share | 0.85 | 0.13 | 3 |
| 1 | 6 | 3 | best_system_cost | 1934.31 | 667.93 | 3 |
| 1 | 6 | 3 | best_rule_served_share | 0.85 | 0.14 | 3 |
| 1 | 6 | 4 | best_system_cost | 1939.64 | 652.40 | 3 |
| 1 | 6 | 4 | best_rule_served_share | 0.85 | 0.14 | 3 |
| 1 | 8 | 1 | best_system_cost | 2302.39 | 582.46 | 3 |
| 1 | 8 | 1 | best_rule_served_share | 0.70 | 0.21 | 3 |
| 1 | 8 | 2 | best_system_cost | 1777.02 | 515.74 | 3 |
| 1 | 8 | 2 | best_rule_served_share | 0.93 | 0.11 | 3 |
| 1 | 8 | 3 | best_system_cost | 1613.96 | 316.56 | 3 |
| 1 | 8 | 3 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 1 | 8 | 4 | best_system_cost | 1606.78 | 288.82 | 3 |
| 1 | 8 | 4 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 1 | 10 | 1 | best_system_cost | 2283.73 | 749.19 | 3 |
| 1 | 10 | 1 | best_rule_served_share | 0.77 | 0.24 | 3 |
| 1 | 10 | 2 | best_system_cost | 1866.69 | 416.97 | 3 |
| 1 | 10 | 2 | best_rule_served_share | 0.94 | 0.08 | 3 |
| 1 | 10 | 3 | best_system_cost | 1694.56 | 219.06 | 3 |
| 1 | 10 | 3 | best_rule_served_share | 0.99 | 0.03 | 3 |
| 1 | 10 | 4 | best_system_cost | 1695.52 | 219.66 | 3 |
| 1 | 10 | 4 | best_rule_served_share | 0.99 | 0.03 | 3 |

## Anomalies

* none

Files: records.jsonl, cases.jsonl, results.csv, cases_wide.csv, cases_wide_joined.csv, summary.csv, fleet_frontier.csv, cost_minimal_design_by_pack.csv.
