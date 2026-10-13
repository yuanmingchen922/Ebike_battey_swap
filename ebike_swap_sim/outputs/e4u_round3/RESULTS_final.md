# E4u round 3 -- station sizing under USD (spares B_j, chargers C_j, power P_j), usd4h family: final report

## Summary (5 sentences)

1. With the station sizes free (y_j = 1, B_j and C_j chosen by the ILP at usd_sunk prices), all six seeds buy only 3-4 spare batteries and 2-4 chargers for the whole 3-site network (mean 3.5 +/- 0.6 batteries and 2.8 +/- 0.8 chargers against the R2.2 default of 9 and 6), never more than 2 batteries or 2 chargers at any site, with one site left without a charger on 2 of the 6 seeds, and the saving of free sizing over the default size is only 1.43 +/- 0.18 USD per 4 h window (1.18-1.62), because the holding costs bB = 0.332 and bC = 0.082 USD per site per window are tiny next to the order-side costs.
2. The ILP cost is flat in every sizing dimension and this is now shown by solves rather than by bounds: on the fully solved seed-0 B x C grid the ILP operational cost spans 574.9-578.8 USD over all 20 cells (total 614.2-618.0, minimum at B 2 / C 1), the operational cost is identical to 1e-9 USD across C_j = 1-4 and P_j = 1.4-4.2 kW on seeds 0-2 (the single exception, +0.053 USD at B3_C4_P4 seed 0, is inside the 1e-4 MIP tolerance), and on the B sweep with n = 6 the operational marginal value of a battery is +0.35 +/- 0.34 USD per battery per window for 1 -> 2 and <= 0.09 afterwards, so in total cost every extra battery beyond 2 per site costs 0.25-0.31 USD per window (-359 to -453 USD per battery-year), the CI excluding zero.
3. For the R2.3 baseline the first extra spare is worth 44.2 +/- 21.6 USD per battery per window (64,600 USD per battery-year at 1460 windows per year, n = 6, CI excludes 0), the second 6.1 +/- 10.8 (not significant), and chargers and site power are worth nothing to it either (-0.17 to -0.08 USD per charger per window, -0.02 USD per kW), while the service level the baseline reaches by buying spares saturates at B_j = 2: on seeds 1, 2 and 3 it never reaches the ILP's served share at B_j = 3 (0.806 / 0.806-0.833 / 0.778-0.833 vs 0.861 / 0.889 / 0.861) even with 6 batteries per site, and on no seed does it reach the ILP's total cost at any B_j <= 6.
4. At the default size (B 3, C 2, P 4 kW) the headline gap with n = 6 is 24.6 +/- 12.0 % (per seed 16.1 / 32.2 / 19.1 / 29.0 / 10.3 / 41.1 %; ILP 641.4 +/- 23.1 vs baseline 871.8 +/- 172.2 USD per window, difference 230 +/- 152 USD), made of the baseline's lateness (127 USD), response time (67 USD) and unserved orders (35 USD, 1.2 orders) with travel and electricity below 2 USD; the ILP serves 0.898 +/- 0.044 of the orders against 0.866 +/- 0.083 for the baseline.
5. Compared with round 2 (n = 3: 22.5 +/- 21.3 %, ILP P sweep and 12 off-line B x C cells unsolved) the three new seeds confirm every qualitative statement, halve the width of the headline CI, make the baseline marginal value of the first spare significant, and close the two evidence gaps -- the ILP P sweep is solved and exactly flat, the seed-0 B x C grid is solved on all 20 cells for both methods -- with 72 ILP cells (69 OPTIMAL, 3 TIME_LIMIT at MIP gap <= 0.29 %, none skipped) in 96.7 min of wall time.

## Setup and data provenance

Family `usd4h` (DECISIONS R2.2: |K| = 6 bikes, |I| = 36 orders, H = 48 slots of 5 min (17:00-21:00), L = 12, q0 ~ U{4..7} = 30-60 % of L, p_ch = 0.667 kW), 3 co-located sites (K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, grid group 8 kW / 6 kW 18-20 h), cost variant `usd_sunk` (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03 $, bB 0.332 $, bC 0.082 $ per site per 4 h window). Baseline = round-2 rules (R2.3: stock-aware site choice, DEMAND_AWARE charging, JIT dispatch), recomputed in round 3 at every cell (milliseconds, same code path). Instances are byte-identical across methods and sizes (only B_j, C_j, P_kw change). Pruning: plan defaults + reachable (lossless on this family). Gurobi OutputFlag 0, Threads 3, TimeLimit 300 s, Seed 0 (`common.ILP_PARAMS_R3`). Costs are USD per 4 h window; `total` is (26) including the setup constant (27) `F_j + bB B_j + bC C_j`; `operational` = total - C_setup. Headline gap = (baseline - ILP) / baseline. Marginal values = paired per-seed finite differences (cost at size s minus cost at the next size) per unit added at one site (network change / 3 sites / step), per window and per year (x 1460 = 16 h / 4 h x 365); mean +/- 95 % t-CI over seeds (n >= 3).

Records used: `records.jsonl` written by `experiments/e4u_round3.py` (138 records, 138 distinct (seed, tag, method) keys, 0 duplicates; the last record per key is used). ILP rows: 29 reused from round 2 (`source = round2`, `outputs/e4u_sizing_usd/results.csv`, OPTIMAL or MIP gap <= 1 %) and 43 solved in round 3 (`source = round3`: the P sweep at B 3 / C 4 for seeds 0-2 (9), the skipped seed-2 B3_C4_P4 cell (1), the 12 off-line B x C cells on seed 0, the B sweep on seeds 3-5 (15) and the free-size run plus its fixed-size check on seeds 3-5 (6)). Baseline rows: 66, all recomputed in round 3 (`phase = baseline_fill` where no ILP was solved in the same call); there is no baseline row for the 6 `free` ILP rows by design (the baseline runs at the chosen sizes as `free_fixed`). Coverage: seeds 0-5 on the B sweep (which contains the default size) and the free-size run; seeds 0-2 on the C and P sweeps; seed 0 on the 12 off-line B x C cells. No cell was skipped by the 4 h wall budget (`SKIPPED_BUDGET` count 0; wall 96.7 min, finished 2026-10-12 23:36).

## Headline at the R2.2 default sizes (B_j = 3, C_j = 2, P_j = 4 kW): seeds 0-5, mean +/- 95 % t-CI (n = 6)

| quantity | n = 6 (seeds 0-5), mean +/- 95 % t-CI | round 2 (seeds 0-2, n = 3) |
|---|---|---|
| ILP total, USD per 4 h window | 641.36 +/- 23.13 | 637.91 +/- 55.26 |
| baseline total, USD per 4 h window | 871.81 +/- 172.18 | 832.16 +/- 311.68 |
| baseline - ILP, USD per window | 230.46 +/- 152.43 | 194.25 +/- 260.15 |
| headline gap (baseline - ILP) / baseline, % | 24.6 +/- 12.0 | 22.5 +/- 21.3 |
| ILP served share | 0.898 +/- 0.044 | 0.907 +/- 0.144 |
| baseline served share | 0.866 +/- 0.083 | 0.861 +/- 0.239 |
| gap component unserved, USD | 35.00 +/- 54.23 | 50.00 +/- 113.84 |
| gap component response, USD | 66.75 +/- 69.04 | 45.50 +/- 111.43 |
| gap component lateness, USD | 127.00 +/- 102.73 | 97.00 +/- 146.29 |
| gap component C_travel, USD | 1.28 +/- 0.77 | 1.31 +/- 2.76 |
| gap component C_elec, USD | 0.42 +/- 0.16 | 0.43 +/- 0.51 |

Per seed:

| seed | ILP source | ILP status | ILP total USD | baseline total USD | gap % | ILP served | baseline served | gap unserved USD | gap response USD | gap lateness USD | ILP s | MIP gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | round2 | OPTIMAL | 615.15 | 733.10 | 16.1 | 0.972 | 0.972 | 0 | 54.0 | 63.0 | 174 | 1.3e-05 |
| 1 | round2 | OPTIMAL | 659.60 | 973.24 | 32.2 | 0.861 | 0.806 | 60 | 85.5 | 165.0 | 79 | 0.0e+00 |
| 2 | round2 | OPTIMAL | 638.98 | 790.12 | 19.1 | 0.889 | 0.806 | 90 | -3.0 | 63.0 | 77 | 0.0e+00 |
| 3 | round3 | OPTIMAL | 662.63 | 932.91 | 29.0 | 0.861 | 0.778 | 90 | 43.5 | 135.0 | 82 | 0.0e+00 |
| 4 | round3 | OPTIMAL | 614.78 | 685.14 | 10.3 | 0.917 | 0.917 | 0 | 33.0 | 36.0 | 88 | 4.3e-05 |
| 5 | round3 | OPTIMAL | 657.01 | 1116.37 | 41.1 | 0.889 | 0.917 | -30 | 187.5 | 300.0 | 227 | 8.4e-05 |

The baseline is worst on seed 5 (1116 USD, 303 USD of lateness while serving the same 0.917 share as on seed 4) and best on seed 4 (685 USD), so its CI is 7 times wider than the ILP's; every gap is computed within seed.

## What the coordinator buys: ILP with B_j, C_j free (y_j = 1 fixed) at usd_sunk prices, per seed (n = 6)

| seed | source | chosen B (S1/S2/S3) | chosen C (S1/S2/S3) | sum B | sum C | ILP free total | ILP fixed at chosen sizes | ILP at default B3/C2 | saving of free sizing USD | ILP served | baseline at chosen sizes | baseline served there | baseline at default | baseline served at default | gap at chosen sizes % | gap at default % | free-ILP s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | round2 | 2 / 1 / 1 | 1 / 1 / 1 | 4 | 3 | 613.83 | 613.83 | 615.15 | 1.32 | 0.972 | 790.37 | 0.972 | 733.10 | 0.972 | 22.3 | 16.1 | 191 |
| 1 | round2 | 1 / 1 / 1 | 1 / 1 / 0 | 3 | 2 | 657.99 | 657.99 | 659.60 | 1.61 | 0.861 | 1175.98 | 0.722 | 973.24 | 0.806 | 44.0 | 32.2 | 130 |
| 2 | round2 | 1 / 2 / 1 | 1 / 1 / 0 | 4 | 2 | 637.63 | 637.63 | 638.98 | 1.35 | 0.889 | 908.86 | 0.722 | 790.12 | 0.806 | 29.8 | 19.1 | 170 |
| 3 | round3 | 1 / 1 / 1 | 1 / 1 / 1 | 3 | 3 | 661.14 | 661.14 | 662.63 | 1.49 | 0.861 | 1064.05 | 0.639 | 932.91 | 0.778 | 37.9 | 29.0 | 107 |
| 4 | round3 | 1 / 1 / 1 | 1 / 1 / 1 | 3 | 3 | 613.16 | 613.16 | 614.78 | 1.62 | 0.917 | 792.77 | 0.861 | 685.14 | 0.917 | 22.7 | 10.3 | 213 |
| 5 | round3 | 1 / 2 / 1 | 1 / 2 / 1 | 4 | 4 | 655.82 | 655.82 | 657.01 | 1.18 | 0.889 | 1179.08 | 0.861 | 1116.37 | 0.917 | 44.4 | 41.1 | 206 |

Means over the 6 seeds (95 % t-CI): batteries bought 3.5 +/- 0.6 (default 9), chargers 2.8 +/- 0.8 (default 6), saving of free sizing 1.43 +/- 0.18 USD per window, baseline at the chosen sizes 985.2 +/- 188.3 USD (served 0.796 +/- 0.129, against 0.866 +/- 0.083 at the default size), gap at the chosen sizes 33.5 +/- 10.5 %. On every seed the fixed-size re-solve at the chosen sizes reproduces the free-size optimum to 1e-6 USD (`free_fixed` = `free`), which certifies that the free-size model is consistent with the fixed-size model. The ILP never buys a second charger except on seed 5 (site S2) and never a third battery at any site; the per-site pattern is 1 battery / 1 charger with a second battery at one site on seeds 0, 2 and 5.

## Sweep B: spares per site B_j (C_j = 2, P_j = 4 kW); seeds 0-5, mean +/- 95 % t-CI (n = 6)

**ILP**

| B_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | stock-out site-slots | idle-full share | charger util | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 640.61 +/- 22.61 | 603.03 +/- 22.61 | 0.894 +/- 0.034 | 3.83 +/- 1.23 | 472.8 +/- 16.8 | 2.5 +/- 2.4 | 1.06 +/- 0.14 | 105.3 +/- 17.8 | 0.22 +/- 0.13 | 0.21 +/- 0.03 | 0.02 +/- 0.34 | 0.35 +/- 0.34 | 26 +/- 495 | 35.7 +/- 11.4 |
| 2 | 6 | 640.56 +/- 23.11 | 601.98 +/- 23.11 | 0.898 +/- 0.044 | 3.67 +/- 1.58 | 476.8 +/- 25.9 | 3.0 +/- 3.4 | 0.56 +/- 0.20 | 43.0 +/- 19.0 | 0.68 +/- 0.13 | 0.11 +/- 0.04 | -0.27 +/- 0.02 | 0.07 +/- 0.02 | -389 +/- 26 | 26.0 +/- 12.9 |
| 3 | 6 | 641.36 +/- 23.13 | 601.79 +/- 23.13 | 0.898 +/- 0.044 | 3.67 +/- 1.58 | 476.8 +/- 25.9 | 3.0 +/- 3.4 | 0.40 +/- 0.22 | 21.3 +/- 18.9 | 0.84 +/- 0.14 | 0.08 +/- 0.04 | -0.25 +/- 0.01 | 0.09 +/- 0.01 | -359 +/- 17 | 24.6 +/- 12.0 |
| 4 | 6 | 642.10 +/- 23.15 | 601.53 +/- 23.15 | 0.898 +/- 0.044 | 3.67 +/- 1.58 | 476.8 +/- 25.9 | 3.0 +/- 3.4 | 0.14 +/- 0.21 | 3.2 +/- 7.6 | 0.97 +/- 0.06 | 0.03 +/- 0.04 | -0.31 +/- 0.03 | 0.02 +/- 0.03 | -453 +/- 42 | 24.7 +/- 12.1 |
| 6 | 6 | 643.96 +/- 23.19 | 601.40 +/- 23.19 | 0.898 +/- 0.044 | 3.67 +/- 1.58 | 476.8 +/- 25.9 | 3.0 +/- 3.4 | 0.02 +/- 0.05 | 0.0 +/- 0.0 | 1.00 +/- 0.00 | 0.00 +/- 0.01 | - | - | - | 24.0 +/- 11.7 |

**baseline**

| B_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | stock-out site-slots | idle-full share | charger util | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 1022.90 +/- 199.22 | 985.32 +/- 199.22 | 0.787 +/- 0.104 | 7.67 +/- 3.73 | 538.5 +/- 79.3 | 204.0 +/- 117.7 | 1.09 +/- 0.12 | 61.5 +/- 6.9 | 0.52 +/- 0.05 | 0.21 +/- 0.02 | 44.22 +/- 21.61 | 44.55 +/- 21.61 | 64562 +/- 31551 | 35.7 +/- 11.4 |
| 2 | 6 | 890.24 +/- 186.21 | 851.67 +/- 186.21 | 0.875 +/- 0.066 | 4.50 +/- 2.37 | 557.0 +/- 65.9 | 145.5 +/- 107.8 | 1.17 +/- 0.07 | 18.0 +/- 4.8 | 0.86 +/- 0.04 | 0.23 +/- 0.01 | 6.14 +/- 10.77 | 6.47 +/- 10.77 | 8967 +/- 15724 | 26.0 +/- 12.9 |
| 3 | 6 | 871.81 +/- 172.18 | 832.24 +/- 172.18 | 0.866 +/- 0.083 | 4.83 +/- 3.00 | 543.5 +/- 76.3 | 130.0 +/- 102.5 | 0.82 +/- 0.08 | 8.3 +/- 4.3 | 0.93 +/- 0.03 | 0.16 +/- 0.02 | -0.68 +/- 1.07 | -0.35 +/- 1.07 | -994 +/- 1566 | 24.6 +/- 12.0 |
| 4 | 6 | 873.86 +/- 172.87 | 833.29 +/- 172.87 | 0.870 +/- 0.077 | 4.67 +/- 2.79 | 547.2 +/- 74.3 | 132.5 +/- 102.9 | 0.61 +/- 0.11 | 1.0 +/- 2.1 | 0.99 +/- 0.02 | 0.12 +/- 0.02 | 1.09 +/- 3.46 | 1.42 +/- 3.46 | 1591 +/- 5055 | 24.7 +/- 12.1 |
| 6 | 6 | 867.32 +/- 167.82 | 824.76 +/- 167.82 | 0.870 +/- 0.077 | 4.67 +/- 2.79 | 544.2 +/- 75.0 | 127.5 +/- 101.4 | 0.20 +/- 0.15 | 0.0 +/- 0.0 | 1.00 +/- 0.00 | 0.04 +/- 0.03 | - | - | - | 24.0 +/- 11.7 |

Per seed the ILP operational cost is non-increasing in B_j on all 6 seeds (no violation of monotonicity; the seed-0 B_j = 1 cell is a TIME_LIMIT row with 0.29 % MIP gap and is still 3.0 USD above its B_j = 2 value). The baseline is non-monotone on seeds 2 and 3 (2 -> 3 spares raises its cost from 765.8 to 790.1 USD on seed 2 and lowers its served share from 0.833 to 0.778 on seed 3), which is why its 2 -> 3 and 3 -> 4 marginal values straddle zero.

## Sweep C: chargers per site C_j (B_j = 3, P_j = 4 kW); seeds 0-2 (common seed set), mean +/- 95 % t-CI (n = 3)

The C_j = 2 cell is the default size and has 6 seeds; the tables below use the 3 seeds that every C_j cell has, so the lines are comparable (with all 6 seeds at C_j = 2 the ILP mean would read 641.36 and the baseline 871.81 -- a seed-set artefact, not a charger effect: seeds 3 and 5 are more expensive instances).

**ILP**

| C_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | stock-out site-slots | idle-full share | charger util | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 637.66 +/- 55.26 | 598.34 +/- 55.26 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.41 +/- 0.75 | 27.3 +/- 42.0 | 0.80 +/- 0.29 | 0.16 +/- 0.29 | -0.08 +/- 0.00 | 0.00 +/- 0.00 | -120 +/- 0 | 22.5 +/- 21.3 |
| 2 | 3 | 637.91 +/- 55.26 | 598.34 +/- 55.26 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.41 +/- 0.75 | 26.7 +/- 43.4 | 0.81 +/- 0.31 | 0.08 +/- 0.15 | -0.08 +/- 0.00 | 0.00 +/- 0.00 | -120 +/- 0 | 22.5 +/- 21.3 |
| 3 | 3 | 638.15 +/- 55.26 | 598.34 +/- 55.26 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.41 +/- 0.75 | 27.0 +/- 32.5 | 0.80 +/- 0.24 | 0.05 +/- 0.10 | -0.09 +/- 0.03 | -0.01 +/- 0.03 | -128 +/- 37 | 22.5 +/- 21.3 |
| 4 | 3 | 638.42 +/- 55.20 | 598.36 +/- 55.20 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.43 +/- 0.83 | 27.0 +/- 25.9 | 0.80 +/- 0.18 | 0.04 +/- 0.08 | - | - | - | 22.5 +/- 21.3 |

**baseline**

| C_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | stock-out site-slots | idle-full share | charger util | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 831.65 +/- 311.67 | 792.33 +/- 311.67 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.59 +/- 0.23 | 10.7 +/- 16.0 | 0.91 +/- 0.12 | 0.23 +/- 0.09 | -0.17 +/- 0.02 | -0.08 +/- 0.02 | -244 +/- 25 | 22.5 +/- 21.3 |
| 2 | 3 | 832.16 +/- 311.68 | 792.59 +/- 311.68 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.85 +/- 0.24 | 7.7 +/- 10.0 | 0.94 +/- 0.08 | 0.17 +/- 0.05 | -0.11 +/- 0.04 | -0.03 +/- 0.04 | -163 +/- 57 | 22.5 +/- 21.3 |
| 3 | 3 | 832.49 +/- 311.74 | 792.67 +/- 311.74 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.94 +/- 0.29 | 7.7 +/- 10.0 | 0.94 +/- 0.08 | 0.12 +/- 0.04 | -0.08 +/- 0.00 | -0.00 +/- 0.00 | -120 +/- 0 | 22.5 +/- 21.3 |
| 4 | 3 | 832.74 +/- 311.74 | 792.67 +/- 311.74 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.94 +/- 0.29 | 7.7 +/- 10.0 | 0.94 +/- 0.08 | 0.09 +/- 0.03 | - | - | - | 22.5 +/- 21.3 |

ILP operational cost per seed across C_j = 1 / 2 / 3 / 4: seed 0 575.576 / 575.576 / 575.576 / 575.630, seed 1 620.031 x 4, seed 2 599.409 x 4 -- identical to the solver tolerance, so the ILP's marginal operational value of a charger is 0.000 and its total marginal value is exactly -bC = -0.082 USD per charger per window (-120 USD per charger-year). For the baseline a charger is also worthless (-0.17 / -0.11 / -0.08 USD per charger per window: more chargers buy slightly more electricity for batteries that are never swapped).

## Sweep P: site power limit P_j (B_j = 3, C_j = 4); seeds 0-2, mean +/- 95 % t-CI (n = 3); the ILP is now solved at every P

(20) allows floor(P_j / 0.667 kW) = 2 / 4 / 6 / 6 simultaneous chargers at 1.4 / 2.8 / 4.0 / 4.2 kW, so with C_j = 4 only P_j = 1.4 kW can bind at the site; the grid group (21) never binds (peak group draw <= 3.33 kW on every schedule against 6-8 kW). Marginal values are per kW added at one site.

**ILP**

| P_kw | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | stock-out site-slots | idle-full share | charger util | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.4 | 3 | 638.40 +/- 55.26 | 598.34 +/- 55.26 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.41 +/- 0.75 | 16.0 +/- 54.1 | 0.88 +/- 0.38 | 0.04 +/- 0.07 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0 +/- 0 | 22.5 +/- 21.3 |
| 2.8 | 3 | 638.40 +/- 55.26 | 598.34 +/- 55.26 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.41 +/- 0.75 | 29.3 +/- 29.4 | 0.78 +/- 0.21 | 0.04 +/- 0.07 | -0.00 +/- 0.02 | -0.00 +/- 0.02 | -7 +/- 31 | 22.5 +/- 21.3 |
| 4 | 3 | 638.42 +/- 55.20 | 598.36 +/- 55.20 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.43 +/- 0.83 | 27.0 +/- 25.9 | 0.80 +/- 0.18 | 0.04 +/- 0.08 | 0.03 +/- 0.13 | 0.03 +/- 0.13 | 43 +/- 186 | 22.5 +/- 21.3 |
| 4.2 | 3 | 638.40 +/- 55.26 | 598.34 +/- 55.26 | 0.907 +/- 0.144 | 3.33 +/- 5.17 | 481.5 +/- 91.0 | 5.0 +/- 8.6 | 0.41 +/- 0.75 | 32.3 +/- 23.1 | 0.76 +/- 0.18 | 0.04 +/- 0.07 | - | - | - | 22.5 +/- 21.3 |

**baseline**

| P_kw | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | stock-out site-slots | idle-full share | charger util | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.4 | 3 | 832.65 +/- 311.68 | 792.59 +/- 311.68 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.85 +/- 0.24 | 7.7 +/- 10.0 | 0.94 +/- 0.08 | 0.08 +/- 0.02 | -0.02 +/- 0.03 | -0.02 +/- 0.03 | -31 +/- 41 | 22.5 +/- 21.3 |
| 2.8 | 3 | 832.74 +/- 311.74 | 792.67 +/- 311.74 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.94 +/- 0.29 | 7.7 +/- 10.0 | 0.94 +/- 0.08 | 0.09 +/- 0.03 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0 +/- 0 | 22.5 +/- 21.3 |
| 4 | 3 | 832.74 +/- 311.74 | 792.67 +/- 311.74 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.94 +/- 0.29 | 7.7 +/- 10.0 | 0.94 +/- 0.08 | 0.09 +/- 0.03 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0 +/- 0 | 22.5 +/- 21.3 |
| 4.2 | 3 | 832.74 +/- 311.74 | 792.67 +/- 311.74 | 0.861 +/- 0.239 | 5.00 +/- 8.61 | 527.0 +/- 146.8 | 102.0 +/- 142.2 | 0.94 +/- 0.29 | 7.7 +/- 10.0 | 0.94 +/- 0.08 | 0.09 +/- 0.03 | - | - | - | 22.5 +/- 21.3 |

ILP operational cost per seed across P_j = 1.4 / 2.8 / 4.0 / 4.2 kW: seed 0 575.576 / 575.576 / 575.630 / 575.576, seed 1 620.031 x 4, seed 2 599.409 x 4. The round-2 sandwich bound (opt at 1.4 kW between oper(B3_C4_P4) and oper(B3_C1_P4)) is confirmed with equality: the ILP curve is exactly flat and the marginal value of a kW is 0 for the ILP; the baseline gains 0.02 USD per kW per window from a tighter cap (less electricity bought, same service).

## B x C grid at P_j = 4 kW, seed 0: all 20 cells solved for the ILP and the baseline

| B_j | C_j | ILP status | ILP source | ILP total | ILP operational | ILP served | ILP stock-out slots | baseline total | baseline operational | baseline served | baseline stock-out slots | gap % | ILP s | MIP gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | TIME_LIMIT | round3 | 615.62 | 578.28 | 0.944 | 81 | 1010.31 | 972.98 | 0.917 | 61 | 39.1 | 300 | 2.0e-03 |
| 1 | 2 | TIME_LIMIT | round2 | 616.42 | 578.84 | 0.944 | 128 | 1010.56 | 972.98 | 0.917 | 61 | 39.0 | 300 | 2.9e-03 |
| 1 | 3 | OPTIMAL | round3 | 616.11 | 578.28 | 0.944 | 85 | 1010.81 | 972.98 | 0.917 | 61 | 39.0 | 234 | 3.0e-05 |
| 1 | 4 | TIME_LIMIT | round3 | 616.42 | 578.35 | 0.944 | 93 | 1011.05 | 972.98 | 0.917 | 61 | 39.0 | 300 | 2.1e-03 |
| 2 | 1 | OPTIMAL | round3 | 614.21 | 575.88 | 0.972 | 85 | 766.84 | 728.52 | 0.972 | 29 | 19.9 | 178 | 8.9e-05 |
| 2 | 2 | OPTIMAL | round2 | 614.42 | 575.85 | 0.972 | 21 | 767.46 | 728.89 | 0.972 | 23 | 19.9 | 159 | 0.0e+00 |
| 2 | 3 | OPTIMAL | round3 | 614.67 | 575.85 | 0.972 | 33 | 767.71 | 728.89 | 0.972 | 23 | 19.9 | 95 | 0.0e+00 |
| 2 | 4 | OPTIMAL | round3 | 614.91 | 575.85 | 0.972 | 38 | 767.95 | 728.89 | 0.972 | 23 | 19.9 | 113 | 0.0e+00 |
| 3 | 1 | OPTIMAL | round2 | 614.90 | 575.58 | 0.972 | 13 | 732.59 | 693.26 | 0.972 | 18 | 16.1 | 112 | 0.0e+00 |
| 3 | 2 | OPTIMAL | round2 | 615.15 | 575.58 | 0.972 | 12 | 733.10 | 693.53 | 0.972 | 12 | 16.1 | 174 | 1.3e-05 |
| 3 | 3 | OPTIMAL | round2 | 615.39 | 575.58 | 0.972 | 18 | 733.45 | 693.63 | 0.972 | 12 | 16.1 | 119 | 0.0e+00 |
| 3 | 4 | OPTIMAL | round2 | 615.69 | 575.63 | 0.972 | 20 | 733.70 | 693.63 | 0.972 | 12 | 16.1 | 118 | 1.0e-04 |
| 4 | 1 | OPTIMAL | round3 | 615.59 | 575.27 | 0.972 | 8 | 733.47 | 693.15 | 0.972 | 0 | 16.1 | 83 | 0.0e+00 |
| 4 | 2 | OPTIMAL | round2 | 615.88 | 575.31 | 0.972 | 18 | 733.85 | 693.28 | 0.972 | 0 | 16.1 | 147 | 5.8e-05 |
| 4 | 3 | OPTIMAL | round3 | 616.09 | 575.27 | 0.972 | 8 | 734.22 | 693.40 | 0.972 | 0 | 16.1 | 85 | 0.0e+00 |
| 4 | 4 | OPTIMAL | round3 | 616.33 | 575.27 | 0.972 | 3 | 734.46 | 693.40 | 0.972 | 0 | 16.1 | 79 | 0.0e+00 |
| 6 | 1 | OPTIMAL | round3 | 617.23 | 574.92 | 0.972 | 0 | 735.06 | 692.75 | 0.972 | 0 | 16.0 | 101 | 0.0e+00 |
| 6 | 2 | OPTIMAL | round2 | 617.48 | 574.92 | 0.972 | 0 | 735.30 | 692.75 | 0.972 | 0 | 16.0 | 123 | 0.0e+00 |
| 6 | 3 | OPTIMAL | round3 | 617.72 | 574.92 | 0.972 | 0 | 735.55 | 692.75 | 0.972 | 0 | 16.0 | 93 | 0.0e+00 |
| 6 | 4 | OPTIMAL | round3 | 617.97 | 574.92 | 0.972 | 0 | 735.80 | 692.75 | 0.972 | 0 | 16.0 | 86 | 0.0e+00 |

Seed-0 reading: the ILP total ranges over 614.2-618.0 USD (minimum at B 2 / C 1; operational 574.9-578.8, decreasing in B_j by 0.3-0.6 USD per step and flat in C_j to within 0.06 USD on every row except B_j = 1, where the three TIME_LIMIT / rejected-start cells scatter by 0.6 USD, see anomaly 2); the baseline ranges over 732.6-1011.1 USD (minimum at B 3 / C 1), with a 243 USD drop from 1 to 2 spares, 34 USD from 2 to 3, and nothing afterwards, and a 0.25 USD rise per charger (bC plus electricity); the gap is 39.0-39.1 % at B_j = 1, 19.9 % at B_j = 2 and 16.0-16.1 % for B_j >= 3, independent of C_j. The seed-mean grid of the sweep lines (summary_heat_*.csv) mixes n = 6, 3 and 1 cells and must not be read as a surface; the figure uses seed 0 only.

## Spares the baseline needs to match the ILP service level (B sweep, C_j = 2, P_j = 4 kW; n = 6)

| seed | ILP served at B3 | ILP total at B3 | baseline served at B3 | baseline B_j to match ILP served | B_j to match served and mean response | B_j to match ILP total | ILP served at B1 | baseline B_j to match ILP-at-B1 served | best baseline served (B 1-6) | best baseline total (B 1-6) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.972 | 615.15 | 0.972 | 2 | > 6 | > 6 | 0.944 | 2 | 0.972 | 733.10 |
| 1 | 0.861 | 659.60 | 0.806 | > 6 | > 6 | > 6 | 0.861 | > 6 | 0.806 | 927.21 |
| 2 | 0.889 | 638.98 | 0.806 | > 6 | > 6 | > 6 | 0.889 | > 6 | 0.833 | 765.75 |
| 3 | 0.861 | 662.63 | 0.778 | > 6 | > 6 | > 6 | 0.861 | > 6 | 0.833 | 932.91 |
| 4 | 0.917 | 614.78 | 0.917 | 2 | > 6 | > 6 | 0.917 | 2 | 0.917 | 684.74 |
| 5 | 0.889 | 657.01 | 0.917 | 2 | > 6 | > 6 | 0.889 | 2 | 0.917 | 1116.37 |

On seeds 0, 4 and 5 the baseline reaches the ILP's served share with 2 spares per site (it already does so at B_j = 3), but its total cost never reaches the ILP's on any seed at any B_j <= 6 (best 733 / 927 / 766 / 933 / 685 / 1116 vs ILP 615 / 660 / 639 / 663 / 615 / 657 USD), and no seed reaches the ILP's served share together with its mean response time. On seeds 1, 2 and 3 the baseline's service level saturates at 0.806 / 0.833 / 0.833 below the ILP's 0.861 / 0.889 / 0.861, and it does not even reach the ILP's B_j = 1 service level with 6 batteries per site.

## Gap decomposition: baseline - ILP by cost component on the B sweep (n = 6, mean +/- 95 % t-CI, USD per window)

| B_j | n | gap total USD | gap unserved | gap response | gap lateness | gap C_travel | gap C_elec | gap % |
|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 382.3 +/- 183.8 | 115.0 +/- 78.2 | 65.8 +/- 67.1 | 201.5 +/- 116.7 | 0.0 +/- 0.7 | 0.0 +/- 0.1 | 35.7 +/- 11.4 |
| 2 | 6 | 249.7 +/- 166.8 | 25.0 +/- 31.0 | 80.2 +/- 60.5 | 142.5 +/- 107.9 | 1.3 +/- 0.4 | 0.6 +/- 0.1 | 26.0 +/- 12.9 |
| 3 | 6 | 230.5 +/- 152.4 | 35.0 +/- 54.2 | 66.8 +/- 69.0 | 127.0 +/- 102.7 | 1.3 +/- 0.8 | 0.4 +/- 0.2 | 24.6 +/- 12.0 |
| 4 | 6 | 231.8 +/- 153.0 | 30.0 +/- 48.8 | 70.5 +/- 68.0 | 129.5 +/- 103.2 | 1.3 +/- 0.8 | 0.5 +/- 0.2 | 24.7 +/- 12.1 |
| 6 | 6 | 223.4 +/- 148.6 | 30.0 +/- 48.8 | 67.5 +/- 67.6 | 124.5 +/- 101.7 | 1.2 +/- 0.5 | 0.2 +/- 0.2 | 24.0 +/- 11.7 |

Lateness is the largest component at every size (124-202 USD), then response (66-80 USD) and unserved orders (25-115 USD); travel and electricity are below 1.5 USD. The gap shrinks from 35.7 % at B_j = 1 to 24.0 % at B_j = 6 only because the baseline improves; the ILP's cost is the same to within 3.4 USD.

## Per-cell table (one row per ILP cell; the last record per (seed, tag, method); baseline at the same sizes)

| seed | tag | sweep | ILP source | ILP status | ILP total | ILP oper. | ILP served | ILP stock-out slots | ILP s | MIP gap | MIP start | baseline total | baseline served | gap % | baseline report-only |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | B1_C1_P4 | heat | round3 | TIME_LIMIT | 615.62 | 578.28 | 0.944 | 81 | 300 | 2.0e-03 | default | 1010.31 | 0.917 | 39.1 | {"(17)": 2, "(18)": 1} |
| 0 | B1_C2_P4 | B | round2 | TIME_LIMIT | 616.42 | 578.84 | 0.944 | 128 | 300 | 2.9e-03 | default | 1010.56 | 0.917 | 39.0 | {"(17)": 2, "(18)": 1} |
| 0 | B1_C3_P4 | heat | round3 | OPTIMAL | 616.11 | 578.28 | 0.944 | 85 | 234 | 3.0e-05 | default | 1010.81 | 0.917 | 39.0 | {"(17)": 2, "(18)": 1} |
| 0 | B1_C4_P4 | heat | round3 | TIME_LIMIT | 616.42 | 578.35 | 0.944 | 93 | 300 | 2.1e-03 | default | 1011.05 | 0.917 | 39.0 | {"(17)": 2, "(18)": 1} |
| 0 | B2_C1_P4 | heat | round3 | OPTIMAL | 614.21 | 575.88 | 0.972 | 85 | 178 | 8.9e-05 | default | 766.84 | 0.972 | 19.9 | {} |
| 0 | B2_C2_P4 | B | round2 | OPTIMAL | 614.42 | 575.85 | 0.972 | 21 | 159 | 0.0e+00 | default | 767.46 | 0.972 | 19.9 | {} |
| 0 | B2_C3_P4 | heat | round3 | OPTIMAL | 614.67 | 575.85 | 0.972 | 33 | 95 | 0.0e+00 | default | 767.71 | 0.972 | 19.9 | {} |
| 0 | B2_C4_P4 | heat | round3 | OPTIMAL | 614.91 | 575.85 | 0.972 | 38 | 113 | 0.0e+00 | default | 767.95 | 0.972 | 19.9 | {} |
| 0 | B3_C1_P4 | C | round2 | OPTIMAL | 614.90 | 575.58 | 0.972 | 13 | 112 | 0.0e+00 | default | 732.59 | 0.972 | 16.1 | {} |
| 0 | B3_C2_P4 | B | round2 | OPTIMAL | 615.15 | 575.58 | 0.972 | 12 | 174 | 1.3e-05 | default | 733.10 | 0.972 | 16.1 | {} |
| 0 | B3_C3_P4 | C | round2 | OPTIMAL | 615.39 | 575.58 | 0.972 | 18 | 119 | 0.0e+00 | default | 733.45 | 0.972 | 16.1 | {} |
| 0 | B3_C4_P1.4 | P | round3 | OPTIMAL | 615.64 | 575.58 | 0.972 | 6 | 130 | 1.3e-05 | default | 733.59 | 0.972 | 16.1 | {} |
| 0 | B3_C4_P2.8 | P | round3 | OPTIMAL | 615.64 | 575.58 | 0.972 | 22 | 141 | 0.0e+00 | default | 733.70 | 0.972 | 16.1 | {} |
| 0 | B3_C4_P4 | C | round2 | OPTIMAL | 615.69 | 575.63 | 0.972 | 20 | 118 | 1.0e-04 | default | 733.70 | 0.972 | 16.1 | {} |
| 0 | B3_C4_P4.2 | P | round3 | OPTIMAL | 615.64 | 575.58 | 0.972 | 40 | 141 | 1.3e-05 | default | 733.70 | 0.972 | 16.1 | {} |
| 0 | B4_C1_P4 | heat | round3 | OPTIMAL | 615.59 | 575.27 | 0.972 | 8 | 83 | 0.0e+00 | default | 733.47 | 0.972 | 16.1 | {} |
| 0 | B4_C2_P4 | B | round2 | OPTIMAL | 615.88 | 575.31 | 0.972 | 18 | 147 | 5.8e-05 | default | 733.85 | 0.972 | 16.1 | {} |
| 0 | B4_C3_P4 | heat | round3 | OPTIMAL | 616.09 | 575.27 | 0.972 | 8 | 85 | 0.0e+00 | default | 734.22 | 0.972 | 16.1 | {} |
| 0 | B4_C4_P4 | heat | round3 | OPTIMAL | 616.33 | 575.27 | 0.972 | 3 | 79 | 0.0e+00 | default | 734.46 | 0.972 | 16.1 | {} |
| 0 | B6_C1_P4 | heat | round3 | OPTIMAL | 617.23 | 574.92 | 0.972 | 0 | 101 | 0.0e+00 | default | 735.06 | 0.972 | 16.0 | {} |
| 0 | B6_C2_P4 | B | round2 | OPTIMAL | 617.48 | 574.92 | 0.972 | 0 | 123 | 0.0e+00 | default | 735.30 | 0.972 | 16.0 | {} |
| 0 | B6_C3_P4 | heat | round3 | OPTIMAL | 617.72 | 574.92 | 0.972 | 0 | 93 | 0.0e+00 | default | 735.55 | 0.972 | 16.0 | {} |
| 0 | B6_C4_P4 | heat | round3 | OPTIMAL | 617.97 | 574.92 | 0.972 | 0 | 86 | 0.0e+00 | default | 735.80 | 0.972 | 16.0 | {} |
| 0 | free | free | round2 | OPTIMAL | 613.83 | 576.17 | 0.972 | 68 | 191 | 7.9e-05 | - | - | - | - | - |
| 0 | free_fixed | free_fixed | round2 | OPTIMAL | 613.83 | 576.17 | 0.972 | 68 | 65 | 3.0e-05 | chain:free | 790.37 | 0.972 | 22.3 | {"(17)": 2, "(18)": 1} |
| 1 | B1_C2_P4 | B | round2 | OPTIMAL | 658.32 | 620.74 | 0.861 | 79 | 93 | 0.0e+00 | baseline_reserve | 1176.52 | 0.722 | 44.0 | {"(17)": 2, "(18)": 1} |
| 1 | B2_C2_P4 | B | round2 | OPTIMAL | 658.78 | 620.21 | 0.861 | 52 | 87 | 0.0e+00 | default | 1039.55 | 0.806 | 36.6 | {} |
| 1 | B3_C1_P4 | C | round2 | OPTIMAL | 659.36 | 620.03 | 0.861 | 46 | 99 | 0.0e+00 | baseline_reserve | 972.73 | 0.806 | 32.2 | {"(17)": 1, "(18)": 1} |
| 1 | B3_C2_P4 | B | round2 | OPTIMAL | 659.60 | 620.03 | 0.861 | 46 | 79 | 0.0e+00 | baseline_round1 | 973.24 | 0.806 | 32.2 | {"(18)": 1} |
| 1 | B3_C3_P4 | C | round2 | OPTIMAL | 659.85 | 620.03 | 0.861 | 42 | 80 | 0.0e+00 | default | 973.61 | 0.806 | 32.2 | {} |
| 1 | B3_C4_P1.4 | P | round3 | OPTIMAL | 660.09 | 620.03 | 0.861 | 41 | 95 | 0.0e+00 | baseline_round1 | 973.74 | 0.806 | 32.2 | {"(18)": 1} |
| 1 | B3_C4_P2.8 | P | round3 | OPTIMAL | 660.09 | 620.03 | 0.861 | 43 | 92 | 0.0e+00 | default | 973.86 | 0.806 | 32.2 | {} |
| 1 | B3_C4_P4 | C | round2 | OPTIMAL | 660.09 | 620.03 | 0.861 | 39 | 87 | 0.0e+00 | default | 973.86 | 0.806 | 32.2 | {} |
| 1 | B3_C4_P4.2 | P | round3 | OPTIMAL | 660.09 | 620.03 | 0.861 | 35 | 95 | 0.0e+00 | default | 973.86 | 0.806 | 32.2 | {} |
| 1 | B4_C2_P4 | B | round2 | OPTIMAL | 660.37 | 619.80 | 0.861 | 0 | 81 | 0.0e+00 | default | 974.15 | 0.806 | 32.2 | {} |
| 1 | B6_C2_P4 | B | round2 | OPTIMAL | 662.36 | 619.80 | 0.861 | 0 | 96 | 0.0e+00 | default | 927.21 | 0.806 | 28.6 | {} |
| 1 | free | free | round2 | OPTIMAL | 657.99 | 620.74 | 0.861 | 79 | 130 | 6.7e-05 | - | - | - | - | - |
| 1 | free_fixed | free_fixed | round2 | OPTIMAL | 657.99 | 620.74 | 0.861 | 79 | 70 | 1.9e-06 | chain:free | 1175.98 | 0.722 | 44.0 | {"(17)": 3, "(18)": 1} |
| 2 | B1_C2_P4 | B | round2 | OPTIMAL | 637.93 | 600.35 | 0.889 | 104 | 80 | 4.6e-05 | baseline_reserve | 822.06 | 0.806 | 22.4 | {"(17)": 1} |
| 2 | B2_C2_P4 | B | round2 | OPTIMAL | 638.21 | 599.64 | 0.889 | 47 | 72 | 0.0e+00 | default | 765.75 | 0.833 | 16.7 | {} |
| 2 | B3_C1_P4 | C | round2 | OPTIMAL | 638.73 | 599.41 | 0.889 | 23 | 75 | 0.0e+00 | default | 789.65 | 0.806 | 19.1 | {} |
| 2 | B3_C2_P4 | B | round2 | OPTIMAL | 638.98 | 599.41 | 0.889 | 22 | 77 | 0.0e+00 | default | 790.12 | 0.806 | 19.1 | {} |
| 2 | B3_C3_P4 | C | round2 | OPTIMAL | 639.22 | 599.41 | 0.889 | 21 | 74 | 0.0e+00 | default | 790.41 | 0.806 | 19.1 | {} |
| 2 | B3_C4_P1.4 | P | round3 | OPTIMAL | 639.47 | 599.41 | 0.889 | 1 | 67 | 0.0e+00 | default | 790.62 | 0.806 | 19.1 | {} |
| 2 | B3_C4_P2.8 | P | round3 | OPTIMAL | 639.47 | 599.41 | 0.889 | 23 | 80 | 0.0e+00 | default | 790.65 | 0.806 | 19.1 | {} |
| 2 | B3_C4_P4 | C | round3 | OPTIMAL | 639.47 | 599.41 | 0.889 | 22 | 78 | 0.0e+00 | default | 790.65 | 0.806 | 19.1 | {} |
| 2 | B3_C4_P4.2 | P | round3 | OPTIMAL | 639.47 | 599.41 | 0.889 | 22 | 84 | 0.0e+00 | default | 790.65 | 0.806 | 19.1 | {} |
| 2 | B4_C2_P4 | B | round2 | OPTIMAL | 639.73 | 599.16 | 0.889 | 0 | 80 | 0.0e+00 | default | 790.89 | 0.806 | 19.1 | {} |
| 2 | B6_C2_P4 | B | round2 | OPTIMAL | 641.72 | 599.16 | 0.889 | 0 | 90 | 0.0e+00 | default | 792.44 | 0.806 | 19.0 | {} |
| 2 | free | free | round2 | OPTIMAL | 637.63 | 600.05 | 0.889 | 62 | 170 | 2.4e-05 | - | - | - | - | - |
| 2 | free_fixed | free_fixed | round2 | OPTIMAL | 637.63 | 600.05 | 0.889 | 62 | 50 | 3.7e-05 | chain:free | 908.86 | 0.722 | 29.8 | {"(17)": 2, "(18)": 1} |
| 3 | B1_C2_P4 | B | round3 | OPTIMAL | 661.38 | 623.81 | 0.861 | 113 | 78 | 0.0e+00 | default | 1064.29 | 0.639 | 37.9 | {"(17)": 3, "(18)": 1} |
| 3 | B2_C2_P4 | B | round3 | OPTIMAL | 661.78 | 623.20 | 0.861 | 72 | 92 | 0.0e+00 | default | 951.77 | 0.833 | 30.5 | {} |
| 3 | B3_C2_P4 | B | round3 | OPTIMAL | 662.63 | 623.06 | 0.861 | 0 | 82 | 0.0e+00 | default | 932.91 | 0.778 | 29.0 | {} |
| 3 | B4_C2_P4 | B | round3 | OPTIMAL | 663.41 | 622.85 | 0.861 | 0 | 86 | 0.0e+00 | default | 941.21 | 0.806 | 29.5 | {} |
| 3 | B6_C2_P4 | B | round3 | OPTIMAL | 665.26 | 622.70 | 0.861 | 0 | 79 | 0.0e+00 | default | 942.86 | 0.806 | 29.4 | {} |
| 3 | free | free | round3 | OPTIMAL | 661.14 | 623.81 | 0.861 | 97 | 107 | 5.6e-05 | - | - | - | - | - |
| 3 | free_fixed | free_fixed | round3 | OPTIMAL | 661.14 | 623.81 | 0.861 | 97 | 86 | 2.9e-06 | chain:free | 1064.05 | 0.639 | 37.9 | {"(17)": 3, "(18)": 1} |
| 4 | B1_C2_P4 | B | round3 | OPTIMAL | 613.41 | 575.83 | 0.917 | 95 | 87 | 0.0e+00 | default | 793.01 | 0.861 | 22.6 | {"(17)": 2, "(18)": 1} |
| 4 | B2_C2_P4 | B | round3 | OPTIMAL | 613.93 | 575.35 | 0.917 | 30 | 89 | 4.4e-05 | default | 684.74 | 0.917 | 10.3 | {} |
| 4 | B3_C2_P4 | B | round3 | OPTIMAL | 614.78 | 575.21 | 0.917 | 9 | 88 | 4.3e-05 | default | 685.14 | 0.917 | 10.3 | {} |
| 4 | B4_C2_P4 | B | round3 | OPTIMAL | 615.47 | 574.91 | 0.917 | 0 | 84 | 0.0e+00 | default | 685.82 | 0.917 | 10.3 | {} |
| 4 | B6_C2_P4 | B | round3 | OPTIMAL | 617.47 | 574.91 | 0.917 | 0 | 92 | 0.0e+00 | default | 687.44 | 0.917 | 10.2 | {} |
| 4 | free | free | round3 | OPTIMAL | 613.16 | 575.83 | 0.917 | 80 | 213 | 2.0e-05 | - | - | - | - | - |
| 4 | free_fixed | free_fixed | round3 | OPTIMAL | 613.16 | 575.83 | 0.917 | 80 | 86 | 8.3e-06 | chain:free | 792.77 | 0.861 | 22.7 | {"(17)": 2, "(18)": 1} |
| 5 | B1_C2_P4 | B | round3 | OPTIMAL | 656.19 | 618.62 | 0.889 | 113 | 155 | 0.0e+00 | default | 1270.96 | 0.778 | 48.4 | {"(17)": 1} |
| 5 | B2_C2_P4 | B | round3 | OPTIMAL | 656.22 | 617.65 | 0.889 | 36 | 220 | 4.8e-05 | default | 1132.18 | 0.889 | 42.0 | {} |
| 5 | B3_C2_P4 | B | round3 | OPTIMAL | 657.01 | 617.44 | 0.889 | 39 | 227 | 8.4e-05 | default | 1116.37 | 0.917 | 41.1 | {} |
| 5 | B4_C2_P4 | B | round3 | OPTIMAL | 657.72 | 617.15 | 0.889 | 1 | 150 | 0.0e+00 | default | 1117.23 | 0.917 | 41.1 | {} |
| 5 | B6_C2_P4 | B | round3 | OPTIMAL | 659.46 | 616.90 | 0.889 | 0 | 188 | 0.0e+00 | default | 1118.67 | 0.917 | 41.0 | {} |
| 5 | free | free | round3 | OPTIMAL | 655.82 | 618.08 | 0.889 | 72 | 206 | 7.9e-05 | - | - | - | - | - |
| 5 | free_fixed | free_fixed | round3 | OPTIMAL | 655.82 | 618.08 | 0.889 | 72 | 107 | 8.0e-05 | chain:free | 1179.08 | 0.861 | 44.4 | {"(17)": 1} |

## Solver statistics

- ILP runs: 72 (29 `round2` reused: 28 OPTIMAL + 1 TIME_LIMIT at MIP gap 0.29 %; 43 `round3` solved: 41 OPTIMAL + 2 TIME_LIMIT); statuses {OPTIMAL: 69, TIME_LIMIT: 3, SKIPPED_BUDGET: 0, INFEASIBLE: 0}; TIME_LIMIT cells: seed 0 B1_C2_P4 (round 2, gap 0.29 %), seed 0 B1_C1_P4 (round 3, 0.20 %), seed 0 B1_C4_P4 (round 3, 0.21 %), i.e. at most 1.8 USD of slack each; binaries 1,032,998-1,207,111 (arcs 1,032,959-1,207,072; rows 58,961-65,034); solve time mean 118.4 s (round-3 cells 124.4 s), median 92.6 s, max 300.1 s; MIP gap max 0.0029, mean 0.00011; arc build mean 2.28 s; model build mean 4.10 s; `evaluate.check` passes on all 72 schedules: True; identity (24): True; MIP start accepted 59 of 66 runs with a start (rejected 7: the four seed-0 B_j = 1 cells and seed 3 / 4 / 5 B1_C2_P4, all with the `default` R2.3 schedule, which at B_j = 1 violates (17)/(18) and had no clean fallback); start variants {default: 55, none (free runs): 6, chain:free: 6, baseline_reserve: 3, baseline_round1: 2}; Threads 3 on every round-3 cell; Seed 0.
- Baseline runs: 66, runtime < 10 ms each; identity (24) holds on all: True; report-only families observed: 48 clean, 9 with (17) x 2 + (18), 3 with (17) x 3 + (18), 3 with (17), 2 with (18), 1 with (17) + (18) (only the report-only families (9), (17), (18) appear; (17)/(18) violations occur at B_j = 1 and at the ILP-chosen lean sizes); stock-aware fallbacks (no site with stock) are non-zero only at B_j = 1 and at the lean `free_fixed` sizes (1-6 per run); ILP <= baseline on every cell with both rows: True.
- Wall time 96.7 min for the 43 round-3 ILP solves and 66 baseline runs (budget 4 h); the E2u round-3 run was executing concurrently on the same machine, so solve times are indicative only.

## Figures (regenerated 2026-10-13 from records.jsonl with matplotlib Agg; blue = ILP, orange = baseline)

- `cost_vs_B.png` -- B sweep, seeds 0-5: (a) total cost (USD per 4 h window) with the 95 % t-CI band, (b) served share (%) with CIs, (c) paired marginal value of one more battery at one site (USD per unit per window) with CIs.
- `cost_vs_C.png` -- C sweep, seeds 0-2 (common seed set), same panels; marginal value per charger.
- `cost_vs_P.png` -- P sweep, seeds 0-2, same panels; marginal value per kW; the ILP is now solved at every P (round 2 had a bound only).
- `heatmap_BxC.png` -- seed 0, all 20 B x C cells: ILP total cost, baseline total cost and the gap in % of the baseline (cell text: cost and served share); sequential single-hue scale per panel.
- `free_sizing.png` -- per seed: free-size ILP vs ILP at the default size, baseline at the ILP-chosen sizes vs at the default size (USD per window), and the number of batteries / chargers bought against the defaults 9 / 6.

The script's own `summary_*.csv`, `spares_to_match.csv` and `gap_decomposition.csv` (written by `--analyse`) are kept; the C-sweep lines there mix n = 6 at C_j = 2 with n = 3 elsewhere, and this file (common seed set) is authoritative where they disagree. `_analysis_final.json` holds every number quoted here.

## Anomalies

1. **Seed-set artefact on the C sweep and the heat-map seed means**: with all cells pooled, the ILP and baseline read 3.7 / 39.7 USD higher at C_j = 2 than at C_j = 1 and 3 (641.36 vs 637.66 / 638.15; 871.81 vs 831.65 / 832.49) because only the C_j = 2 cell has seeds 3-5; on the common seeds 0-2 all four C_j lines are flat (ILP 637.66 / 637.91 / 638.15 / 638.42 = exactly +bC per step). The script's `summary_C.csv`, `summary_heat_*.csv` and `cost_vs_C.png` of the `--analyse` run show the pooled values and should not be quoted; the figure was regenerated on seeds 0-2.
2. **Three TIME_LIMIT cells, all seed 0 at B_j = 1** (B1_C2_P4 0.29 %, B1_C1_P4 0.20 %, B1_C4_P4 0.21 %; B1_C3_P4 reached OPTIMAL in 234 s): the R2.3 default MIP start is rejected on every B_j = 1 cell (it violates (17)/(18) at one spare per site and no clean fallback exists), so the solver starts cold; the three incumbents are within 1.2-1.8 USD of their bounds, which is why the seed-0 B_j = 1 row of the heat map scatters by 0.8 USD in C_j (615.6 / 616.4 / 616.1 / 616.4) while every other row is flat to 0.06 USD. The qualitative reading (flat in C) is unaffected; the exact B_j = 1 operational cost on seed 0 is known only to +/- 1.8 USD.
3. **ILP marginal value of a battery is negative in total cost beyond 2 spares per site** (-0.27 +/- 0.02, -0.25 +/- 0.01, -0.31 +/- 0.03 USD per battery per window at 2 -> 3, 3 -> 4, 4 -> 6; CIs exclude 0) because bB = 0.332 is paid for batteries that are idle (idle-full share 0.68 -> 1.00); only 1 -> 2 has a positive operational value (+0.35 +/- 0.34). The ILP's cost-minimising size on the sweep is B_j = 2 (640.56) within 0.05 USD of B_j = 1 (640.61).
4. **Baseline non-monotone in B_j**: 2 -> 3 spares worsens seed 2 (765.8 -> 790.1 USD, served 0.833 -> 0.806) and seed 3 (served 0.833 -> 0.778), 3 -> 4 worsens seed 3 (932.9 -> 941.2) while 4 -> 6 improves seed 1 by 47 USD; the DEMAND_AWARE / stock-aware rules react discontinuously to stock levels, so the baseline marginal values at 2 -> 3 and 3 -> 4 are -0.68 +/- 1.07 and +1.09 +/- 3.46 USD (not significant).
5. **Baseline at the ILP-chosen lean sizes collapses**: with 3-4 batteries and 2-4 chargers in the network the baseline serves 0.639-0.972 (mean 0.796) and costs 985 +/- 188 USD, 113 USD more than at the default sizes, with the report-only targets (17)/(18) violated on all 6 seeds ((17) only on seed 5); the gap there is 33.5 +/- 10.5 % (22.3-44.4 %). The ILP's sizing is only cheap under coordinated operation.
6. **Chargers and power are worthless for both methods**: ILP operational cost identical across C_j and P_j on seeds 0-2 (one +0.053 USD outlier inside the MIP tolerance), total rises by exactly bC per charger; baseline -0.08 to -0.17 USD per charger and -0.02 USD per kW. The group power limit (21) never binds (peak 3.33 kW); the site limit (20) binds only at 1.4 kW with C_j = 4 and costs nothing.
7. **Unserved orders are cost-optimal drops, not failures**: the ILP itself drops 1-5 orders per seed (served 0.861-0.972) because P = 30 USD is below the waiting cost of late orders under usd_sunk, and usd4h seed 0 order 35 is structurally unservable (no delivery arc); the service-level comparison is between two drop policies.
8. **Seed heterogeneity remains the main statistical caveat**: with n = 6 the baseline's CI at the default size is still +/- 172 USD (seed 5 carries 303 USD of lateness, seed 4 only 36) against +/- 23 USD for the ILP; all marginal values and gaps are paired within seed, and the C / P sweeps still have n = 3.
9. **Annualised figures** (x 1460) assume every 4 h window of a 16 h day all year looks like the dinner peak; they are the task's upper-bound convention, not a forecast.
10. **Concurrent load**: the E2u round-3 script was running on the same machine during this run, so the solve times (mean 124 s on round-3 cells vs 110 s in round 2) are not a clean benchmark.

## Interpretation (with round-2 comparison)

1. Under USD prices and a 4 h evening window, the coordinator buys very little station: on all six seeds the free-size ILP keeps 3-4 spare batteries and 2-4 chargers in the whole 3-site network (one battery and one charger per site, plus a second battery at one site on half of the seeds), against 9 and 6 at the R2.2 default, and gains only 1.43 +/- 0.18 USD per window by doing so -- the round-2 statement (3-4 batteries, 2-3 chargers, 1.3-1.6 USD) holds on the three new seeds without change.
2. The ILP's cost is flat in every sizing dimension, and round 3 replaces the round-2 bounds by solves: the seed-0 B x C grid is solved on all 20 cells (operational 574.9-578.8 USD, total minimum 614.2 at B 2 / C 1), the P sweep is solved on seeds 0-2 and is exactly flat (the ILP operational cost is the same number at 1.4, 2.8, 4.0 and 4.2 kW on every seed), and the B sweep with n = 6 gives a marginal operational value of +0.35 +/- 0.34 USD per battery per window for the first extra spare and <= 0.09 afterwards.
3. Stock-outs are real for the ILP at lean sizes (105 empty site-slots per window at B_j = 1, 43 at B_j = 2, 0 at B_j = 6) but cost nothing in service: the served share is 0.894 at B_j = 1 and 0.898 from B_j = 2 on, because the coordinated schedule routes each bike to a site that has a full battery when it needs one.
4. The knee is on the baseline side, and with n = 6 it is now statistically clear: the first extra spare per site is worth 44.2 +/- 21.6 USD per window to the R2.3 baseline (64,600 USD per battery-year; round 2 had 48.5 +/- 77.6, not significant), the second 6.1 +/- 10.8, and the third and beyond nothing, while chargers (-0.08 to -0.17 USD) and site power (-0.02 USD per kW) are worth nothing to either method, exactly as in round 2.
5. The headline gap at the default size is 24.6 +/- 12.0 % with n = 6 (round 2: 22.5 +/- 21.3 % with n = 3); the three new seeds (29.0 / 10.3 / 41.1 %) bracket the old ones (16.1 / 32.2 / 19.1 %), the CI half-width halves, and the decomposition is unchanged in kind -- lateness 127 USD, response 67 USD, unserved orders 35 USD (1.2 orders), travel and electricity under 2 USD.
6. The gap falls from 35.7 % at B_j = 1 to 24.0 % at B_j = 6 only because the baseline improves (1023 -> 867 USD) while the ILP moves by 3 USD; the value of coordination is therefore largest exactly where stations are lean, which is where the ILP would size them, and at the ILP-chosen sizes the gap is 33.5 +/- 10.5 %.
7. The baseline cannot buy its way to the ILP's service level or cost: on seeds 1-3 it saturates at 0.806-0.833 served against 0.861-0.889 for the ILP at every B_j <= 6 (it does not even reach the ILP's one-spare service level), on seeds 0, 4 and 5 it matches the served share from 2 spares on but never the response time, and on no seed does its total cost at any B_j <= 6 come within 70 USD of the ILP's (round 2 found the same on its 3 seeds).
8. Seed heterogeneity is still the main statistical caveat: the baseline's cost CI at the default size is +/- 172 USD (seed 4 at 685 USD, seed 5 at 1116 USD with 303 USD of lateness) against +/- 23 USD for the ILP, which is why every marginal value and gap is computed as a paired within-seed difference, and why the C and P sweeps, still at n = 3, carry CIs of +/- 55 USD (ILP) and +/- 312 USD (baseline) although their point values are flat to 0.1 USD.
9. The three TIME_LIMIT cells are all seed-0 B_j = 1 cells whose R2.3 MIP start is rejected (one spare per site violates the report-only end targets), and they are within 1.8 USD of their bounds; they do not affect any conclusion but they are the only cells where the seed-0 heat-map row is not flat in C_j.
10. For the paper the sizing message is unchanged and now rests on complete evidence: under realistic USD coefficients station capital is not the lever, coordination is -- one spare and one charger per site suffice for a coordinated fleet, an uncoordinated fleet needs two spares per site to be stable and still serves 3-8 percentage points fewer orders at 24.6 % higher cost; what remains open is the C and P sweeps on seeds 3-5 (cheap, since both are flat) and larger instances (8-10 bikes) where the station may start to bind.

## Files

- `RESULTS_final.md` (this file), `records.jsonl` (138 records, append-only), `results.csv` (refreshed per run by the script), `run_stdout.log`, `wall_time.json`, `RESULTS.md` (script's `--analyse` report, English, with the pooled-seed caveat above), `summary_B.csv` / `summary_C.csv` / `summary_P.csv` / `summary_heat_ILP.csv` / `summary_heat_baseline.csv` / `spares_to_match.csv` / `gap_decomposition.csv` (script outputs), `_analysis_final.json` (every number in this file), `cost_vs_B.png`, `cost_vs_C.png`, `cost_vs_P.png`, `heatmap_BxC.png`, `free_sizing.png` (regenerated from the records).
