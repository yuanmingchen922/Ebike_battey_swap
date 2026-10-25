# X5 -- stressed family, boundary grid, fleet x spare x pack, levers (round 5, final report)

Source: `outputs/r5_x5_stress/` records (`records_{core,boundary,fleet,levers}.jsonl`, last record per (key_md5, method) kept; `cases_*.jsonl` map cases to instance keys), logs `outputs/r5_lanes/r5_x5_*.log` (all three commands exit 0). Protocol: aggregated ILP (O1), Gurobi Threads 3, Seed 0; headline = relaxed control (rho = 0, R_end = 0); gap = 100 (baseline - ILP) / baseline with baseline = best_rule (per-instance min over r2, r5_range, r5 by total (26); no transport services exist, so r5_transfer is not applicable). Totals in USD per window. Intervals are exact-t 95 % CIs over seeds (shown only for n >= 3; otherwise the mean and n). No solve was run for this report; tables and figures are recomputed from the records by a reader script, and the script-generated `RESULTS.md` is kept unchanged.

## Summary

On the stressed family (M5, eBaaS peaks, 25 Wh/km) the coordinated ILP beats the best rule by 40.05 [33.68, 46.41] % at 6 bikes (all 5 seeds OPTIMAL), 45.58 [40.83, 50.32] % at 8 bikes and 46.99 [43.09, 50.88] % at 10 bikes (orders scale with the fleet, 8 per bike), and by 47.96 [13.66, 82.26] % on the 8 h window at 6 bikes; this is about 10 points above the round-3 usd4h reference (29.55 %, SD 5.61, n = 30). The end-state adjustment changes no per-instance gap by more than 0.10 points. The battery side now binds: the LP value of one more spare rises from 0.45 USD per site and window at 6 bikes (about the 0.33 USD spare cost) to 2.79 at 8 and 21.87 at 10 bikes, and the charger value from 0.07 to 1.29 and 16.67. Recovering the written end targets costs the ILP 3.20 [0.18, 6.21] USD per window at 6 bikes (0.38 [0.02, 0.74] % of the relaxed optimum), and at most 4.38 USD on average for any rho x R_end cell of the M1 grid solved on all three seeds, so at 6 bikes the headline does not depend on the boundary choice within the solved part of the grid (rho1_R1 unsolved, rho1_R0 seed 0 only, periodic seeds 0 and 2 only). The price grows with the fleet: on seed 0 it is 11.63 USD (1.17 %) at 8 bikes and 29.41 USD at 10 bikes (true value in [0, 50.96], both runs TIME_LIMIT). In the fleet x spare x pack sweep (48 orders fixed) spares are cheap (0.28-0.55 USD per window against 88.94 USD for a bike and rider), the rule needs 8-10 bikes and 4 spares per site for its lowest system cost (1587.7-1688.3 USD), whereas under the ILP, within the tested grid (K in {4, 6, 8}, B <= 4, 0.6 kWh, seeds 0-1, n = 2), neither an extra bike nor an extra spare pays beyond 4 bikes and 2 spares per site (1310.1 USD, 17.5 % below the rule's best design at the same pack and seeds, per seed 13.0 % and 21.3 %, but with served share 0.70 against 0.99). At matched service (ILP K 8 / B 2, served 0.969) the ILP design costs 1448.8 USD, 8.75 % below the rule's best design. Both cost-minimal designs lie on the edge of the tested grid (ILP at the smallest K, rule at the largest K and B for 0.6 kWh), so the true optima may lie outside it. Of the M9/M10 levers only removing on-site charging (P = 0) moves the ILP cost (+79.2 USD; all P = 0 solves OPTIMAL); faster chargers, a second swap position and locking out one or two spares change it by less than the MIP gap, and a demand charge would need to exceed about 6,200 USD per kW-month before a zero site cap became optimal.

## Coverage

| sub | cases | unique instances | baseline rows OK | ILP requested | OPTIMAL | TIME_LIMIT (incumbent) | TIME_LIMIT (no incumbent) | SKIPPED_BUDGET | errors/missing | TL MIP gap % (min-max) | LP rows |
|---|---|---|---|---|---|---|---|---|---|---|---|
| core | 25 | 25 | 25 | 25 | 9 | 16 | 0 | 0 | 0 | 0.17-3.23 | 25 |
| boundary | 27 | 27 | 27 | 27 | 11 | 10 | 1 | 5 | 0 | 0.24-2.87 | 6 |
| fleet | 168 | 168 | 168 | 24 | 23 | 1 | 0 | 0 | 0 | 0.33-0.33 | 2 |
| levers | 21 | 18 | 21 | 21 | 8 | 13 | 0 | 0 | 0 | 0.14-1.37 | 3 |

- Wall time per sub-command: core 191.5 min (budget 240), boundary 58.2 min (budget 60), fleet 51.6 min (budget 180), levers 69.5 min (budget 120) (`wall_time.jsonl`). The four lanes ran concurrently (4 jobs x 3 threads).
- Instances shared between sub-commands are solved once (same key_md5): the boundary cells rho0_R0 and rho0.5_R1 (= written) on seeds 0-2 reuse the core 6-bike rows; the fleet cell K 6, B 2, pack 0.6 kWh on seeds 0-1 reuses the core relaxed rows; the lever reference reuses the core 8-bike instance, with its own 300 s ILP row.
- SKIPPED_BUDGET (boundary, 60 min budget): rho1_R0 seeds 1-2 and rho1_R1 seeds 0-2. TIME_LIMIT with no incumbent: periodic seed 1 (MIP start rejected, 300 s). One run was budget-shortened (rho1_R0 seed 0, limit 167 s) but finished OPTIMAL in 137 s, so it stands. No errors; every incumbent passed `check` (check_ok = True for all 80 ILP schedules).
- Written-target ILPs at 8 and 10 bikes were run on seed 0 only (by design, `CORE_WRITTEN_TAIL`). The 8 h family has no written-target run (rolling-horizon family). Fleet ILPs: pack 0.6 kWh only, K in {4, 6, 8}, seeds 0-1 (n = 2).

## 1. Stressed family (M5): gap, end adjustment

| cell | targets | n | ILP OPT/TL | max MIP gap % | best rule (USD) | ILP (USD) | gap vs best rule % | gap end-adj % | gap vs bound % | gap vs r2 % | C_end_adjust rule / ILP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 h, 6 bikes, 48 orders | relaxed | 5 | 5/0 | 0.00 | 1386.1 [1172.5, 1599.8] | 824.2 [769.7, 878.8] | 40.05 [33.68, 46.41] | 39.96 [33.58, 46.35] | 40.05 [33.68, 46.41] | 42.85 [35.46, 50.24] | 1.22 / 1.84 |
| 4 h, 6 bikes, 48 orders | written | 5 | 2/3 | 0.79 | 1386.1 [1172.5, 1599.8] | 827.4 [770.9, 883.9] | 39.83 [33.63, 46.03] | 39.80 [33.59, 46.01] | 40.01 [33.62, 46.39] | 42.64 [35.40, 49.88] | 1.22 / 1.10 |
| 4 h, 8 bikes, 64 orders | relaxed | 5 | 2/3 | 1.25 | 2009.5 [1777.3, 2241.7] | 1089.3 [1010.6, 1168.0] | 45.58 [40.83, 50.32] | 45.51 [40.76, 50.26] | 45.85 [40.98, 50.72] | 45.69 [40.98, 50.41] | 1.43 / 2.10 |
| 4 h, 8 bikes, 64 orders | written | 1 | 0/1 | 0.91 | 1813.4 (n=1) | 1002.9 (n=1) | 44.69 (n=1) | 44.66 (n=1) | 45.20 (n=1) | 44.69 (n=1) | 1.57 / 1.41 |
| 4 h, 10 bikes, 80 orders | relaxed | 5 | 0/5 | 1.93 | 2520.8 [2250.8, 2790.7] | 1331.6 [1255.8, 1407.4] | 46.99 [43.09, 50.88] | 46.93 [43.03, 50.82] | 47.76 [43.72, 51.80] | 48.70 [45.17, 52.22] | 1.44 / 2.17 |
| 4 h, 10 bikes, 80 orders | written | 1 | 0/1 | 3.23 | 2215.1 (n=1) | 1254.0 (n=1) | 43.39 (n=1) | 43.36 (n=1) | 45.22 (n=1) | 43.39 (n=1) | 1.58 / 1.58 |
| 8 h, 6 bikes, 96 orders | relaxed | 3 | 0/3 | 1.49 | 3282.0 [948.8, 5615.1] | 1621.5 [1358.1, 1884.8] | 47.96 [13.66, 82.26] | 47.91 [13.60, 82.23] | 48.25 [13.49, 83.00] | 51.85 [24.78, 78.93] | 1.25 / 2.10 |

`gap vs bound` uses the proven lower bound instead of the incumbent (upper end of the true gap); `gap end-adj` uses total + C_end_adjust for both sides (rule side = min over the rules of its end-adjusted total). OPT/TL = OPTIMAL / TIME_LIMIT ILP runs; time limits 300 s at 6 bikes (4 h), 600 s otherwise.

### LP shadow prices and stock-outs

| cell | targets | n | LP spare value (USD/site/window) | LP charger value (USD/site/window) | stock-out slot-sites rule | stock-out slot-sites ILP | served share rule | served share ILP |
|---|---|---|---|---|---|---|---|---|
| 4 h, 6 bikes, 48 orders | relaxed | 5 | 0.45 [-0.00, 0.90] | 0.07 [-0.08, 0.21] | 70.8 [58.0, 83.6] | 84.4 [56.7, 112.1] | 0.754 [0.648, 0.860] | 0.875 [0.823, 0.927] |
| 4 h, 6 bikes, 48 orders | written | 5 | 1.04 [0.08, 2.00] | 0.46 [-0.26, 1.19] | 70.8 [58.0, 83.6] | 69.6 [40.8, 98.4] | 0.754 [0.648, 0.860] | 0.871 [0.815, 0.927] |
| 4 h, 8 bikes, 64 orders | relaxed | 5 | 2.79 [0.61, 4.98] | 1.29 [0.20, 2.38] | 97.8 [81.8, 113.8] | 109.4 [92.3, 126.5] | 0.631 [0.572, 0.690] | 0.866 [0.784, 0.947] |
| 4 h, 8 bikes, 64 orders | written | 1 | 7.93 (n=1) | 9.68 (n=1) | 87.0 (n=1) | 93.0 (n=1) | 0.688 (n=1) | 0.953 (n=1) |
| 4 h, 10 bikes, 80 orders | relaxed | 5 | 21.87 [12.12, 31.62] | 16.67 [7.20, 26.15] | 112.2 [94.8, 129.6] | 95.2 [85.3, 105.1] | 0.573 [0.493, 0.652] | 0.872 [0.818, 0.927] |
| 4 h, 10 bikes, 80 orders | written | 1 | 36.58 (n=1) | 35.13 (n=1) | 92.0 (n=1) | 89.0 (n=1) | 0.675 (n=1) | 0.925 (n=1) |
| 8 h, 6 bikes, 96 orders | relaxed | 3 | 0.39 [0.19, 0.58] | 0.03 [-0.09, 0.14] | 198.3 [175.8, 220.9] | 211.3 [170.9, 251.7] | 0.726 [0.422, 1.029] | 0.878 [0.751, 1.006] |

LP value = operating value of one more spare / charger at a site from the LP relaxation of the aggregated model (-RC + set-up coefficient; spare cost bB = 0.332, charger cost bC = 0.082 USD per site and window). Stock-out slot-sites = (site, slot) pairs with no full battery in stock.

### Price of recovery, core (written - relaxed ILP)

| cell | seed | relaxed status | written status | PoR raw | PoR end-adj | PoR raw lower (bound) | PoR % of relaxed ILP |
|---|---|---|---|---|---|---|---|
| 4 h, 6 bikes, 48 orders | 0 | OPTIMAL | OPTIMAL | 0.65 | -0.02 | 0.65 | 0.09 |
| 4 h, 6 bikes, 48 orders | 1 | OPTIMAL | TIME_LIMIT | 3.87 | 2.85 | 1.41 | 0.45 |
| 4 h, 6 bikes, 48 orders | 2 | OPTIMAL | TIME_LIMIT | 3.60 | 2.94 | 0.00 | 0.42 |
| 4 h, 6 bikes, 48 orders | 3 | OPTIMAL | TIME_LIMIT | 6.70 | 6.11 | 0.07 | 0.80 |
| 4 h, 6 bikes, 48 orders | 4 | OPTIMAL | OPTIMAL | 1.16 | 0.40 | 1.11 | 0.14 |
| 4 h, 8 bikes, 64 orders | 0 | OPTIMAL | TIME_LIMIT | 11.63 | 10.85 | 2.48 | 1.17 |
| 4 h, 10 bikes, 80 orders | 0 | TIME_LIMIT | TIME_LIMIT | 29.41 | 28.75 | 0.00 | 2.40 |

6 bikes, n = 5: raw 3.20 [0.18, 6.21] USD, end-adjusted 2.45 [-0.60, 5.50] USD, 0.38 [0.02, 0.74] % of the relaxed optimum. The lower bound uses the written run's proven bound (the relaxed problem is a relaxation of the written one, so the true price is non-negative). At 10 bikes both runs are TIME_LIMIT, so the true price lies in [0, 50.96] USD (written incumbent minus relaxed bound).

## 2. Boundary grid (M1, r5_stress4h, 6 bikes, seeds 0-2, ILP 300 s)

| variant | seeds with ILP | ILP OPT/TL | ILP total (USD) | price of recovery raw (USD) | PoR raw per seed | PoR lower bound per seed | PoR end-adj (USD) | gap vs best rule % | ILP C_end_adjust | rule violates under these targets (seeds 0/1/2) |
|---|---|---|---|---|---|---|---|---|---|---|
| rho0_R0 (headline) | 3/3 (0,1,2) | 3/0 | 820.6 [667.8, 973.3] | 0.00 [0.00, 0.00] | 0.00, 0.00, 0.00 | 0.00, 0.00, 0.00 | 0.00 [0.00, 0.00] | 38.12 [27.91, 48.32] | 1.90 [1.61, 2.19] | {"(9)": 1} / {} / {} |
| rho0.25_R0 | 3/3 (0,1,2) | 2/1 | 821.6 [667.4, 975.7] | 1.02 [-1.10, 3.14] | 0.37, 0.71, 1.99 | 0.37, 0.64, 0.00 | 0.56 [-1.56, 2.69] | 38.04 [27.86, 48.22] | 1.44 [1.07, 1.81] | {"(9)": 1} / {"(18)": 1} / {"(18)": 1} |
| rho0.5_R0 | 3/3 (0,1,2) | 1/2 | 823.5 [665.8, 981.3] | 3.00 [-2.45, 8.44] | 0.65, 3.35, 4.99 | 0.65, 1.25, 0.00 | 2.28 [-3.02, 7.57] | 37.90 [27.91, 47.89] | 1.18 [0.74, 1.62] | {"(9)": 1, "(18)": 1} / {"(18)": 1} / {"(18)": 1} |
| rho1_R0 | 1/3 (0) | 1/0 | 751.2 (n=1) | 1.62 (n=1) | 1.62 | 1.55 | 0.04 (n=1) | 33.77 (n=1) | 0.41 (n=1) | {"(9)": 1, "(18)": 1} / {"(18)": 1} / {"(18)": 1} |
| rho0_R1 | 3/3 (0,1,2) | 1/2 | 824.9 [664.1, 985.7] | 4.38 [-5.42, 14.17] | 0.65, 3.97, 8.51 | 0.65, 1.41, 0.00 | 3.69 [-6.19, 13.57] | 37.80 [27.87, 47.74] | 1.22 [0.98, 1.45] | {"(9)": 1, "(17)": 1} / {"(17)": 3} / {"(17)": 3} |
| rho0.25_R1 | 3/3 (0,1,2) | 1/2 | 823.7 [665.6, 981.8] | 3.15 [-2.56, 8.86] | 0.65, 3.62, 5.17 | 0.65, 1.41, 0.00 | 2.42 [-3.17, 8.01] | 37.89 [27.93, 47.86] | 1.17 [0.79, 1.55] | {"(9)": 1, "(17)": 1} / {"(17)": 3, "(18)": 1} / {"(17)": 3, "(18)": 1} |
| rho0.5_R1 (written) | 3/3 (0,1,2) | 1/2 | 823.3 [666.1, 980.4] | 2.71 [-1.73, 7.14] | 0.65, 3.87, 3.60 | 0.65, 1.41, 0.00 | 1.92 [-2.27, 6.11] | 37.92 [27.98, 47.87] | 1.11 [0.62, 1.60] | {"(9)": 1, "(17)": 1, "(18)": 1} / {"(17)": 3, "(18)": 1} / {"(17)": 3, "(18)": 1} |
| rho1_R1 | 0/3 | 0/0 | - | - |  |  | - | - | - | {"(9)": 1, "(17)": 1, "(18)": 1} / {"(17)": 3, "(18)": 1} / {"(17)": 3, "(18)": 1} |
| periodic | 2/3 (0,2) | 1/1 | 821.8 (n=2) | 19.46 (n=2) | 1.62, 37.30 | 1.55, 11.73 | 17.99 (n=2) | 34.70 (n=2) | 0.41 (n=2) | {"(9)": 1, "(17)": 3, "(18)": 1} / {"(17)": 3, "(18)": 1} / {"(17)": 3, "(18)": 1} |

Price of recovery (PoR) = ILP(variant) - ILP(rho0_R0) on the same seed (all three rho0_R0 runs OPTIMAL). The lower-bound column uses the variant's proven bound. The rule's schedule is target-agnostic (best rule 1333.72 USD mean on every row); the last column lists, per seed, the report-only constraint families the rule's schedule violates under that row's targets ((9) terminal reachability, (17)/(18) end targets; numbers = violated rows). Under the written targets the rule violates (17) and (18) on every seed, which is why the relaxed control is the like-for-like headline; under the relaxed targets it is clean except one (9) violation on seed 0. rho1_R0 has seed 0 only and periodic seeds 0 and 2 only, so their ILP-total means are not comparable with the 3-seed rows (seed 0 is the cheapest seed).

## 3. Fleet x spare x pack (A6, r5_stress4h, 48 orders fixed)

### ILP gap at fixed demand (pack 0.6 kWh, seeds 0-1)

| K | B/site | n | gap mean % | gap min % | gap max % | ILP total | rule total | ILP served | rule served |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 1 | 2 | 43.14 | 38.41 | 47.88 | 954.84 | 1684.30 | 0.69 | 0.48 |
| 4 | 2 | 2 | 42.14 | 40.56 | 43.71 | 952.79 | 1645.74 | 0.70 | 0.61 |
| 4 | 3 | 2 | 42.62 | 41.66 | 43.58 | 953.59 | 1661.03 | 0.70 | 0.62 |
| 4 | 4 | 2 | 41.97 | 40.39 | 43.55 | 954.51 | 1643.89 | 0.70 | 0.62 |
| 6 | 1 | 2 | 45.93 | 43.04 | 48.81 | 808.60 | 1493.88 | 0.88 | 0.49 |
| 6 | 2 | 2 | 38.02 | 33.91 | 42.12 | 803.29 | 1307.48 | 0.90 | 0.81 |
| 6 | 3 | 2 | 36.70 | 29.01 | 44.40 | 803.98 | 1299.65 | 0.90 | 0.82 |
| 6 | 4 | 2 | 35.98 | 28.96 | 42.99 | 804.80 | 1281.54 | 0.90 | 0.84 |
| 8 | 1 | 2 | 46.08 | 45.53 | 46.63 | 743.28 | 1377.57 | 0.97 | 0.74 |
| 8 | 2 | 2 | 24.02 | 12.36 | 35.68 | 735.29 | 1000.90 | 0.97 | 0.94 |
| 8 | 3 | 2 | 18.65 | 7.63 | 29.67 | 735.87 | 929.48 | 0.97 | 0.98 |
| 8 | 4 | 2 | 14.50 | 6.76 | 22.24 | 736.80 | 873.92 | 0.97 | 0.99 |

### Cost-minimal design per policy and pack (system cost = operating total incl. end adjustment and spare set-up + 88.94 USD per bike and window)

| policy | pack kWh | argmin K | argmin B/site | min system cost | served | n seeds |
|---|---|---|---|---|---|---|
| best_rule | 0.50 | 10 | 4 | 1688.3 | 0.993 | 3 |
| best_rule | 0.60 | 8 | 4 | 1587.7 | 0.990 | 2 |
| best_rule | 0.75 | 8 | 4 | 1647.8 | 0.986 | 3 |
| best_rule | 1.00 | 8 | 4 | 1637.5 | 0.986 | 3 |
| ilp | 0.60 | 4 | 2 | 1310.1 | 0.698 | 2 |

### Iso-cost frontier: one more bike vs one more spare (pack 0.6 kWh, rule and ILP on the same seeds 0-1)

| policy | pack kWh | K | B/site | n | system cost (USD/window) | served | saving per extra bike | saving per extra spare (net) | spare cost | lever that pays |
|---|---|---|---|---|---|---|---|---|---|---|
| best_rule | 0.60 | 4 | 1 | 2 | 2040.4 (n=2) | 0.479 | 94.95 (n=2) | 12.61 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 4 | 2 | 2 | 2002.6 (n=2) | 0.615 | 169.03 (n=2) | -5.19 (n=2) | 0.332 | bike |
| best_rule | 0.60 | 4 | 3 | 2 | 2018.1 (n=2) | 0.625 | 180.39 (n=2) | 5.64 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 4 | 4 | 2 | 2001.2 (n=2) | 0.625 | 180.71 (n=2) | - | 0.332 | bike |
| best_rule | 0.60 | 6 | 1 | 2 | 2028.4 (n=2) | 0.490 | 58.19 (n=2) | 61.99 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 6 | 2 | 2 | 1842.4 (n=2) | 0.812 | 153.11 (n=2) | 2.39 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 6 | 3 | 2 | 1835.3 (n=2) | 0.823 | 184.99 (n=2) | 5.85 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 6 | 4 | 2 | 1817.7 (n=2) | 0.844 | 203.95 (n=2) | - | 0.332 | bike |
| best_rule | 0.60 | 8 | 1 | 2 | 2089.9 (n=2) | 0.740 | - | 125.27 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 8 | 2 | 2 | 1714.1 (n=2) | 0.938 | - | 23.64 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 8 | 3 | 2 | 1643.2 (n=2) | 0.979 | - | 18.49 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 8 | 4 | 2 | 1587.7 (n=2) | 0.990 | - | - | 0.332 | - |
| ilp | 0.60 | 4 | 1 | 2 | 1311.6 (n=2) | 0.688 | 73.06 (n=2) | 0.50 (n=2) | 0.332 | spare |
| ilp | 0.60 | 4 | 2 | 2 | 1310.1 (n=2) | 0.698 | 74.56 (n=2) | -0.29 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 4 | 3 | 2 | 1311.0 (n=2) | 0.698 | 74.47 (n=2) | -0.33 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 4 | 4 | 2 | 1312.0 (n=2) | 0.698 | 74.52 (n=2) | - | 0.332 | neither pays |
| ilp | 0.60 | 6 | 1 | 2 | 1343.4 (n=2) | 0.875 | 32.59 (n=2) | 1.50 (n=2) | 0.332 | spare |
| ilp | 0.60 | 6 | 2 | 2 | 1338.9 (n=2) | 0.896 | 33.99 (n=2) | -0.35 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 6 | 3 | 2 | 1340.0 (n=2) | 0.896 | 34.04 (n=2) | -0.30 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 6 | 4 | 2 | 1340.9 (n=2) | 0.896 | 33.98 (n=2) | - | 0.332 | neither pays |
| ilp | 0.60 | 8 | 1 | 2 | 1456.1 (n=2) | 0.969 | - | 2.43 (n=2) | 0.332 | spare |
| ilp | 0.60 | 8 | 2 | 2 | 1448.8 (n=2) | 0.969 | - | -0.32 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 8 | 3 | 2 | 1449.8 (n=2) | 0.969 | - | -0.34 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 8 | 4 | 2 | 1450.8 (n=2) | 0.969 | - | - | 0.332 | - |

`saving per extra bike` = (V(K) - V(K+2)) / 2 per seed (a bike pays if it exceeds 88.94 USD); `saving per extra spare (net)` = (V(B) - V(B+1)) / 3 sites per seed, already net of the spare's set-up cost because V includes (27). One bike's allocated cost equals 321 / 268 / 214 / 161 spares at 0.5 / 0.6 / 0.75 / 1.0 kWh, so whenever a spare has any positive net value it is the cheaper lever per USD. The full table for all packs (with CIs, n = 3) is in Appendix B and `figs/x5_frontier.csv`.

## 4. Levers (M9, M10; r5_stress4h, 8 bikes / 64 orders, relaxed control, seeds 0-2, ILP 300 s)

| lever | n | ILP OPT/TL | ILP total | dILP vs ref | dILP interval (bounds), seed range | best rule total | d best rule vs ref | gap vs best rule % | served ILP / rule | peak swap occupancy (ILP) |
|---|---|---|---|---|---|---|---|---|---|---|
| Reference (8 bikes, M = 1, eps 25 Wh, P = 4 kW) | 3 | 1/2 | 1058.6 [892.3, 1224.8] | 0 | - | 1959.4 [1623.6, 2295.2] | 0 | 45.96 [44.34, 47.57] | 0.891 / 0.635 | 1.00 |
| Charger speed x2 (eps 50 Wh, p_ch 0.667 kW) | 3 | 3/0 | 1053.6 [893.9, 1213.3] | -5.00 [-14.57, 4.57] | [-8.2, 7.4] | 1818.4 [1113.7, 2523.0] | -141.04 [-510.16, 228.08] | 41.44 [26.46, 56.43] | 0.896 / 0.781 | 1.00 |
| Two swap positions (M = 2) | 3 | 1/2 | 1056.4 [890.4, 1222.4] | -2.16 [-11.30, 6.99] | [-14.4, 13.3] | 1939.5 [1616.7, 2262.4] | -19.90 [-69.02, 29.21] | 45.51 [42.40, 48.63] | 0.891 / 0.615 | 0.50 |
| Lock-out 1 spare (5 % and 10 % round to 1) | 3 | 0/3 | 1057.0 [898.0, 1216.1] | -1.55 [-12.22, 9.12] | [-14.1, 10.8] | 1933.9 [1651.2, 2216.5] | -25.55 [-80.81, 29.71] | 45.34 [44.10, 46.59] | 0.885 / 0.599 | 1.00 |
| Lock-out 2 spares (25 %) | 3 | 0/3 | 1056.6 [894.8, 1218.3] | -2.01 [-10.03, 6.01] | [-12.1, 11.1] | 1927.8 [1665.7, 2189.8] | -31.66 [-105.46, 42.14] | 45.20 [43.39, 47.02] | 0.891 / 0.568 | 1.00 |
| Site power cap P = 0 (no on-site charging) | 3 | 3/0 | 1137.8 [1027.0, 1248.6] | 79.23 [18.95, 139.50] | [51.8, 102.5] | 1749.6 [1609.3, 1889.9] | -209.82 [-448.22, 28.59] | 34.97 [31.34, 38.60] | 0.807 / 0.448 | 1.00 |

dILP = lever minus reference on the same seed. The interval column bounds the true change by [lever bound - reference incumbent, lever incumbent - reference bound] (min / max over seeds). LaTeX version: `figs/tab_x5_levers.tex`.

### Demand-charge proxy (M10(b))

| seed | P0 ILP status | ref ILP status | V(P0) - V(p_ch) (USD, >=) | break-even tariff (USD/kW-month, >=) | rule V(P0) - V(p_ch) |
|---|---|---|---|---|---|
| 0 | OPTIMAL | OPTIMAL | 97.94 | 11752.61 | -126.46 |
| 1 | OPTIMAL | TIME_LIMIT | 51.81 | 6217.45 | -314.73 |
| 2 | OPTIMAL | TIME_LIMIT | 87.93 | 10551.93 | -188.26 |

V(p_ch) is the reference (with one charger per site the cap p_ch = 0.333 kW is not binding). The true difference V(P0) - V(p_ch) is at least P0 optimum minus reference incumbent (all P0 runs OPTIMAL). The break-even monthly tariff is that difference / (3 sites x p_ch) x 120 windows per month; at the assumed 10-40 USD/kW-month the ILP keeps p_ch on every seed (demand charge 0.08-0.33 USD per window). The rule prefers P = 0 for the reason given under Anomalies.

## Figures (`figs/`, PDF vector + PNG 300 dpi)

- `fig_x5_gap_vs_fleet` (7.2 in): (a) gap vs best rule against fleet size on the stressed family (orders = 8 per bike), relaxed targets, mean with 95 % CI and seeds; 8 h window at 6 bikes (mean of 3 seeds; CI in Table 1 too wide to draw); written-target seeds as open circles; grey band = round-3 usd4h mean +/- SD. (b) gap at fixed demand (48 orders, 0.6 kWh) by spares per site (n = 2, seeds shown).
- `fig_x5_shadow_prices` (7.2 in): (a) LP value of one more spare / charger per site (symlog axis; dotted lines = their set-up costs); (b) stock-out slot-sites per window, best rule vs ILP.
- `fig_x5_isocost_heatmap` (7.2 in): system cost (operating + 88.94 USD per bike) over fleet size x spares per site, best rule at 0.5 / 0.75 / 1.0 kWh (n = 3) and 0.6 kWh (n = 2), ILP at 0.6 kWh (n = 2); common colour scale; outlined cell = cost-minimal design.
- `fig_x5_levers` (7.2 in): change in cost vs the 8-bike reference per lever, ILP (a, grey band = mean MIP gap of the reference, 9.3 USD) and best rule (b); mean with 95 % CI, seeds as dots.
- `tab_x5_levers.tex` (booktabs lever table); `x5_per_instance.csv` (all 241 cases); `x5_frontier.csv`.

## Anomalies and caveats

- The script's `RESULTS.md` boundary table reports n_seeds = 3 for rho1_R0, rho1_R1 and periodic, but it counts cases: rho1_R0 has an ILP on seed 0 only, rho1_R1 on none (SKIPPED_BUDGET), periodic on seeds 0 and 2 (seed 1: TIME_LIMIT without incumbent). Its rho1_R0 total 751.18 and periodic total 821.78 are therefore not 3-seed means. Corrected above.
- Periodic seed 2 shows a price of recovery of 37.30 USD, but the run is TIME_LIMIT with a 2.87 % gap; the proven lower bound is 11.73 USD. The periodic bracket is the only M1 cell whose price is clearly above solver noise.
- Fleet cell K 6 / B 2 / 0.6 kWh is the core instance (same key); its records carry no allocated bike cost, so `RESULTS.md` shows no system cost for it and lists its frontier row out of order. Recomputed here with the constant 88.94 USD per bike and window (identical for every fleet cell).
- Lock-out (a restriction) and the two relaxing levers give ILP changes of -1.6 to -5.0 USD, inside the reference MIP gap (1.2-1.4 % on seeds 1-2, i.e. 13.4-14.6 USD; mean over seeds 9.3 USD); the lock-out runs are all TIME_LIMIT. These deltas are solver noise, not effects. Lock-out 5 % and 10 % are one instance (1 of 6 spares) and are counted once.
- The rule is not monotone in resources, but at n = 3 none of the lever responses is significant: removing on-site charging lowers the best-rule cost on all three seeds (-126.5 / -314.7 / -188.3 USD; mean -209.8 [-448.2, 28.6]; served share 0.635 -> 0.448), locking out spares lowers it on 2 of 3 seeds only (1 spare: -0.02 / -40.68 / -35.97, mean -25.6 [-80.8, 29.7]; 2 spares: -0.03 / -58.96 / -35.99, mean -31.7 [-105.5, 42.1]), and several fleet cells show negative spare marginals (e.g. K 4 / B 2 / 0.5 kWh: -9.33 [-12.79, -5.88] USD per spare, the one significant case). Cause: in the 8-bike reference a served order costs about 29.6 USD in response + lateness while an unserved one costs about 29.9 USD, so the rule's late service is worth almost nothing; fewer swaps cut travel and lateness. The rule's demand-charge choice (P = 0) is an artefact of this.
- ILP stock-out slot-sites exceed the rule's at 6 and 8 bikes (84.4 vs 70.8; 109.4 vs 97.8) although the ILP serves more orders: the optimiser runs stock to zero on purpose, so stock-out counts do not show service quality.
- At 10 bikes all 5 relaxed ILPs stop at the 600 s limit (MIP gaps 0.87-1.93 %); the 10-bike written run has a 3.23 % gap. Gaps vs the proven bound are reported next to incumbent gaps; they differ by at most 0.77 points on average.
- The 8 h family CI is wide (n = 3; per-seed gaps 32.2, 53.6, 58.0 %); the rule's cost varies from 2213 to 3976 USD.
- Fleet ILPs exist only at 0.6 kWh with n = 2, so the ILP frontier has no CIs and no pack variation; the rule grid at 0.6 kWh also has only seeds 0-1, while the 0.5 / 0.75 / 1.0 kWh grids have seeds 0-2. K 10 has no ILP.
- The core fleet axis scales demand with the fleet (8 orders per bike), so gap vs fleet size there mixes fleet and demand effects; the fleet sweep keeps 48 orders. LP charger values at 6 bikes are numerically zero on 3 of 5 seeds (|value| < 1e-13).
- The rule's schedules are scored without enforcing the report-only families (9), (17), (18); under the relaxed targets the r2 schedule on seed 0 of the 6-bike cell still violates terminal reachability (9) once, which slightly favours the rule (conservative for the gap).
- All four sub-commands ran concurrently with other round-5 lanes; TIME_LIMIT incumbents may depend on machine load.

## Interpretation

The stressed family does what M5 was meant to do: the battery side binds, and it binds more as the fleet and demand grow, with the LP value of a spare rising about fifty-fold from 6 to 10 bikes and that of a charger from near zero to 16.7 USD per site and window. The coordination gap grows with it, from 40 % to 47 %, about 10 points above the round-3 reference (6 vs 10 bikes Welch p = 0.04; the 8 -> 10 step, +1.4 points, is within seed noise, p = 0.54). Because orders scale with the fleet, this design does not separate battery stress from demand scale, so the statement is that the advantage is largest where fleet, demand and battery scarcity are all highest. At 6 bikes the headline is robust to the boundary handling within the solved part of the M1 grid: recovering the written end targets costs the ILP 0.1-0.8 % of its relaxed optimum (3.20 [0.18, 6.21] USD; mean proven lower bound 0.65 USD) and lowers the gap by 0.22 [0.03, 0.40] points on average (at most 0.42 on a seed), and only the strict periodic bracket has a price clearly above solver noise (at least 11.7 USD on one seed). rho1_R1 was not solved and rho1_R0 and periodic have one and two seeds. The price grows with the fleet (seed 0: 11.63 USD, 1.17 %, at 8 bikes; 29.41 USD, true value in [0, 50.96], at 10 bikes), so boundary robustness is shown only for the 6-bike cell. The end-state adjustment is about 1-2 USD on both sides and never changes a conclusion. Stock-out counts are a poor indicator here, because the optimiser runs stock to zero on purpose and still serves 12-30 points more orders than the rule. The fleet sweep makes the main sizing point: coordination substitutes for hardware. Operated by the best rule, the system needs 8-10 bikes and 4 spares per site to reach its lowest cost, while under the ILP (tested grid K 4-8, B 1-4, n = 2) extra spares have negative net value beyond 2 per site and an extra bike saves only 33-75 USD against its 88.94 USD allocated cost. At matched service (ILP K 8 / B 2, served 0.969 vs the rule's 0.990) the ILP design is 8.75 % cheaper than the rule's best design, against 17.5 % at the cost-minimal ILP design. This sizing result depends on the unserved-order price: the cost-minimal ILP design serves only 70 % of the orders, so a service-level constraint or a higher penalty would move it to 6-8 bikes. Because a bike with its rider costs as much as 161-321 spares, a spare is the cheaper lever per USD wherever it has positive net value. That is not everywhere: under the rule the spare's net value is negative in several cells (e.g. K 4 / B 2 at 0.5 and 0.6 kWh, -9.33 and -5.19 USD) while an extra bike there saves 169-175 USD, so the iso-cost rule is to add spares while their net marginal value is positive and to add bikes only where the saving exceeds the allocated cost, which happens for the rule mainly at 4-6 bikes but never for the ILP within the tested grid. Pack size matters much less than fleet and spares (the rule's best system cost differs by about 100 USD across 0.5-1.0 kWh). Among the operating levers only on-site charging is material (+79 USD per window without it), so the demand-charge proxy is immaterial at realistic tariffs; faster chargers, a second swap position and a one- or two-battery lock-out are within solver tolerance for the ILP, which means the coordinated schedule absorbs them. The rule's larger and sometimes negative lever responses come from its non-monotone cost, not from real gains, and should be reported as a weakness of the rule baseline rather than as lever effects.

## Appendix A. Per-instance results (core, boundary, levers, fleet ILP cells)

| sub | cell | seed | target | best rule | rule total | ILP status | ILP total | ILP bound | MIP gap % | gap % | gap end-adj % | served rule | served ILP | LP spare | LP charger |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| boundary | r5_stress4h_K6 | 0 | periodic | r2 | 1134.20 | OPTIMAL | 751.18 | 751.11 | 0.01 | 33.77 | 33.81 | 0.90 | 0.94 | - | - |
| boundary | r5_stress4h_K6 | 1 | periodic | r5_range | 1480.76 | TIME_LIMIT | - | - | - | - | - | 0.73 | - | - | - |
| boundary | r5_stress4h_K6 | 2 | periodic | r5_range | 1386.19 | TIME_LIMIT | 892.38 | 866.81 | 2.87 | 35.62 | 35.65 | 0.67 | 0.79 | - | - |
| boundary | r5_stress4h_K6 | 0 | rho0.25_R0 | r2 | 1134.20 | OPTIMAL | 749.93 | 749.93 | 0.00 | 33.88 | 33.81 | 0.90 | 0.94 | - | - |
| boundary | r5_stress4h_K6 | 1 | rho0.25_R0 | r5_range | 1480.76 | OPTIMAL | 857.73 | 857.66 | 0.01 | 42.08 | 42.03 | 0.73 | 0.85 | - | - |
| boundary | r5_stress4h_K6 | 2 | rho0.25_R0 | r5_range | 1386.19 | TIME_LIMIT | 857.07 | 853.08 | 0.47 | 38.17 | 38.12 | 0.67 | 0.83 | - | - |
| boundary | r5_stress4h_K6 | 0 | rho0.25_R1 | r2 | 1134.20 | OPTIMAL | 750.21 | 750.21 | 0.00 | 33.86 | 33.81 | 0.90 | 0.94 | - | - |
| boundary | r5_stress4h_K6 | 1 | rho0.25_R1 | r5_range | 1480.76 | TIME_LIMIT | 860.64 | 858.43 | 0.26 | 41.88 | 41.85 | 0.73 | 0.83 | - | - |
| boundary | r5_stress4h_K6 | 2 | rho0.25_R1 | r5_range | 1386.19 | TIME_LIMIT | 860.25 | 854.48 | 0.67 | 37.94 | 37.92 | 0.67 | 0.83 | - | - |
| boundary | r5_stress4h_K6 | 0 | rho0.5_R0 | r2 | 1134.20 | OPTIMAL | 750.21 | 750.21 | 0.00 | 33.86 | 33.81 | 0.90 | 0.94 | - | - |
| boundary | r5_stress4h_K6 | 1 | rho0.5_R0 | r5_range | 1480.76 | TIME_LIMIT | 860.37 | 858.27 | 0.24 | 41.90 | 41.86 | 0.73 | 0.83 | - | - |
| boundary | r5_stress4h_K6 | 2 | rho0.5_R0 | r5_range | 1386.19 | TIME_LIMIT | 860.07 | 854.38 | 0.66 | 37.95 | 37.93 | 0.67 | 0.83 | - | - |
| boundary | r5_stress4h_K6 | 0 | rho0.5_R1 | r2 | 1134.20 | OPTIMAL | 750.21 | 750.21 | 0.00 | 33.86 | 33.81 | 0.90 | 0.94 | 0.28 | 0.00 |
| boundary | r5_stress4h_K6 | 1 | rho0.5_R1 | r5_range | 1480.76 | TIME_LIMIT | 860.89 | 858.43 | 0.29 | 41.86 | 41.85 | 0.73 | 0.83 | 0.70 | 0.74 |
| boundary | r5_stress4h_K6 | 2 | rho0.5_R1 | r5_range | 1386.19 | TIME_LIMIT | 858.68 | 854.48 | 0.49 | 38.05 | 38.02 | 0.67 | 0.83 | 2.12 | 1.35 |
| boundary | r5_stress4h_K6 | 0 | rho0_R0 | r2 | 1134.20 | OPTIMAL | 749.56 | 749.56 | 0.00 | 33.91 | 33.81 | 0.90 | 0.94 | 0.15 | 0.00 |
| boundary | r5_stress4h_K6 | 1 | rho0_R0 | r5_range | 1480.76 | OPTIMAL | 857.02 | 857.01 | 0.00 | 42.12 | 42.04 | 0.73 | 0.85 | 0.32 | 0.06 |
| boundary | r5_stress4h_K6 | 2 | rho0_R0 | r5_range | 1386.19 | OPTIMAL | 855.08 | 855.08 | 0.00 | 38.31 | 38.24 | 0.67 | 0.83 | 1.08 | 0.27 |
| boundary | r5_stress4h_K6 | 0 | rho0_R1 | r2 | 1134.20 | OPTIMAL | 750.21 | 750.21 | 0.00 | 33.86 | 33.81 | 0.90 | 0.94 | - | - |
| boundary | r5_stress4h_K6 | 1 | rho0_R1 | r5_range | 1480.76 | TIME_LIMIT | 860.99 | 858.43 | 0.30 | 41.86 | 41.83 | 0.73 | 0.83 | - | - |
| boundary | r5_stress4h_K6 | 2 | rho0_R1 | r5_range | 1386.19 | TIME_LIMIT | 863.59 | 854.57 | 1.04 | 37.70 | 37.67 | 0.67 | 0.83 | - | - |
| boundary | r5_stress4h_K6 | 0 | rho1_R0 | r2 | 1134.20 | OPTIMAL | 751.18 | 751.11 | 0.01 | 33.77 | 33.81 | 0.90 | 0.94 | - | - |
| boundary | r5_stress4h_K6 | 1 | rho1_R0 | r5_range | 1480.76 | SKIPPED_BUDGET | - | - | - | - | - | 0.73 | - | - | - |
| boundary | r5_stress4h_K6 | 2 | rho1_R0 | r5_range | 1386.19 | SKIPPED_BUDGET | - | - | - | - | - | 0.67 | - | - | - |
| boundary | r5_stress4h_K6 | 0 | rho1_R1 | r2 | 1134.20 | SKIPPED_BUDGET | - | - | - | - | - | 0.90 | - | - | - |
| boundary | r5_stress4h_K6 | 1 | rho1_R1 | r5_range | 1480.76 | SKIPPED_BUDGET | - | - | - | - | - | 0.73 | - | - | - |
| boundary | r5_stress4h_K6 | 2 | rho1_R1 | r5_range | 1386.19 | SKIPPED_BUDGET | - | - | - | - | - | 0.67 | - | - | - |
| core | r5_stress4h_K6 | 0 | rho0_R0 | r2 | 1134.20 | OPTIMAL | 749.56 | 749.56 | 0.00 | 33.91 | 33.81 | 0.90 | 0.94 | 0.15 | 0.00 |
| core | r5_stress4h_K6 | 1 | rho0_R0 | r5_range | 1480.76 | OPTIMAL | 857.02 | 857.01 | 0.00 | 42.12 | 42.04 | 0.73 | 0.85 | 0.32 | 0.06 |
| core | r5_stress4h_K6 | 2 | rho0_R0 | r5_range | 1386.19 | OPTIMAL | 855.08 | 855.08 | 0.00 | 38.31 | 38.24 | 0.67 | 0.83 | 1.08 | 0.27 |
| core | r5_stress4h_K6 | 3 | rho0_R0 | r5_range | 1594.53 | OPTIMAL | 835.43 | 835.43 | 0.00 | 47.61 | 47.55 | 0.73 | 0.85 | 0.40 | 0.00 |
| core | r5_stress4h_K6 | 4 | rho0_R0 | r5_range | 1335.03 | OPTIMAL | 824.14 | 824.14 | 0.00 | 38.27 | 38.18 | 0.75 | 0.90 | 0.30 | -0.00 |
| core | r5_stress4h_K6 | 0 | written | r2 | 1134.20 | OPTIMAL | 750.21 | 750.21 | 0.00 | 33.86 | 33.81 | 0.90 | 0.94 | 0.28 | 0.00 |
| core | r5_stress4h_K6 | 1 | written | r5_range | 1480.76 | TIME_LIMIT | 860.89 | 858.43 | 0.29 | 41.86 | 41.85 | 0.73 | 0.83 | 0.70 | 0.74 |
| core | r5_stress4h_K6 | 2 | written | r5_range | 1386.19 | TIME_LIMIT | 858.68 | 854.48 | 0.49 | 38.05 | 38.02 | 0.67 | 0.83 | 2.12 | 1.35 |
| core | r5_stress4h_K6 | 3 | written | r5_range | 1594.53 | TIME_LIMIT | 842.13 | 835.50 | 0.79 | 47.19 | 47.16 | 0.73 | 0.85 | 1.56 | 0.00 |
| core | r5_stress4h_K6 | 4 | written | r5_range | 1335.03 | OPTIMAL | 825.30 | 825.25 | 0.01 | 38.18 | 38.15 | 0.75 | 0.90 | 0.54 | 0.21 |
| core | r5_stress4h_k10_K10 | 0 | rho0_R0 | r2 | 2215.06 | TIME_LIMIT | 1224.55 | 1202.99 | 1.76 | 44.72 | 44.66 | 0.68 | 0.95 | 31.19 | 25.99 |
| core | r5_stress4h_k10_K10 | 1 | rho0_R0 | r5_range | 2789.22 | TIME_LIMIT | 1361.67 | 1335.38 | 1.93 | 51.18 | 51.12 | 0.57 | 0.86 | 18.82 | 13.58 |
| core | r5_stress4h_k10_K10 | 2 | rho0_R0 | r5_range | 2559.55 | TIME_LIMIT | 1339.68 | 1326.90 | 0.95 | 47.66 | 47.61 | 0.51 | 0.85 | 29.25 | 23.54 |
| core | r5_stress4h_k10_K10 | 3 | rho0_R0 | r5_range | 2624.92 | TIME_LIMIT | 1359.39 | 1333.98 | 1.87 | 48.21 | 48.16 | 0.53 | 0.85 | 13.84 | 8.79 |
| core | r5_stress4h_k10_K10 | 4 | rho0_R0 | r5_range | 2415.02 | TIME_LIMIT | 1372.82 | 1360.87 | 0.87 | 43.15 | 43.10 | 0.57 | 0.85 | 16.26 | 11.45 |
| core | r5_stress4h_k10_K10 | 0 | written | r2 | 2215.06 | TIME_LIMIT | 1253.95 | 1213.46 | 3.23 | 43.39 | 43.36 | 0.68 | 0.93 | 36.58 | 35.13 |
| core | r5_stress4h_k8_K8 | 0 | rho0_R0 | r2 | 1813.36 | OPTIMAL | 991.31 | 991.31 | 0.00 | 45.33 | 45.26 | 0.69 | 0.97 | 2.75 | 1.84 |
| core | r5_stress4h_k8_K8 | 1 | rho0_R0 | r2 | 2080.13 | TIME_LIMIT | 1125.14 | 1112.08 | 1.16 | 45.91 | 45.85 | 0.62 | 0.81 | 1.40 | 0.82 |
| core | r5_stress4h_k8_K8 | 2 | rho0_R0 | r5_range | 1984.75 | TIME_LIMIT | 1059.26 | 1046.02 | 1.25 | 46.63 | 46.56 | 0.59 | 0.89 | 4.95 | 2.46 |
| core | r5_stress4h_k8_K8 | 3 | rho0_R0 | r2 | 2290.18 | TIME_LIMIT | 1137.78 | 1135.89 | 0.17 | 50.32 | 50.26 | 0.67 | 0.81 | 4.10 | 1.14 |
| core | r5_stress4h_k8_K8 | 4 | rho0_R0 | r5_range | 1878.95 | OPTIMAL | 1133.15 | 1133.15 | 0.00 | 39.69 | 39.62 | 0.58 | 0.84 | 0.77 | 0.21 |
| core | r5_stress4h_k8_K8 | 0 | written | r2 | 1813.36 | TIME_LIMIT | 1002.93 | 993.79 | 0.91 | 44.69 | 44.66 | 0.69 | 0.95 | 7.93 | 9.68 |
| core | r5_stress8h_K6 | 0 | rho0_R0 | r5_range | 2213.11 | TIME_LIMIT | 1500.05 | 1497.37 | 0.18 | 32.22 | 32.16 | 0.86 | 0.94 | 0.31 | -0.00 |
| core | r5_stress8h_K6 | 1 | rho0_R0 | r5_range | 3657.23 | TIME_LIMIT | 1695.64 | 1691.70 | 0.23 | 53.64 | 53.60 | 0.64 | 0.84 | 0.46 | 0.08 |
| core | r5_stress8h_K6 | 2 | rho0_R0 | r5_range | 3975.52 | TIME_LIMIT | 1668.70 | 1643.83 | 1.49 | 58.03 | 57.98 | 0.68 | 0.85 | 0.39 | 0.00 |
| fleet | K4_B1_pack0.6 | 0 | rho0_R0 | r5_range | 1743.32 | OPTIMAL | 908.59 | 908.59 | 0.00 | 47.88 | 47.83 | 0.52 | 0.75 | - | - |
| fleet | K4_B1_pack0.6 | 1 | rho0_R0 | r5_range | 1625.28 | OPTIMAL | 1001.08 | 1001.08 | 0.00 | 38.41 | 38.35 | 0.44 | 0.62 | - | - |
| fleet | K4_B2_pack0.6 | 0 | rho0_R0 | r2 | 1612.02 | OPTIMAL | 907.33 | 907.33 | 0.00 | 43.71 | 43.65 | 0.65 | 0.75 | - | - |
| fleet | K4_B2_pack0.6 | 1 | rho0_R0 | r2 | 1679.46 | OPTIMAL | 998.25 | 998.25 | 0.00 | 40.56 | 40.51 | 0.58 | 0.65 | - | - |
| fleet | K4_B3_pack0.6 | 0 | rho0_R0 | r2 | 1609.74 | OPTIMAL | 908.18 | 908.18 | 0.00 | 43.58 | 43.53 | 0.67 | 0.75 | - | - |
| fleet | K4_B3_pack0.6 | 1 | rho0_R0 | r5_range | 1712.33 | OPTIMAL | 999.00 | 998.97 | 0.00 | 41.66 | 41.60 | 0.58 | 0.65 | - | - |
| fleet | K4_B4_pack0.6 | 0 | rho0_R0 | r2 | 1610.50 | OPTIMAL | 909.17 | 909.17 | 0.00 | 43.55 | 43.51 | 0.67 | 0.75 | - | - |
| fleet | K4_B4_pack0.6 | 1 | rho0_R0 | r5_range | 1677.29 | OPTIMAL | 999.84 | 999.84 | 0.00 | 40.39 | 40.33 | 0.58 | 0.65 | - | - |
| fleet | K6_B1_pack0.6 | 0 | rho0_R0 | r2 | 1465.30 | OPTIMAL | 750.02 | 750.02 | 0.00 | 48.81 | 48.77 | 0.56 | 0.94 | - | - |
| fleet | K6_B1_pack0.6 | 1 | rho0_R0 | r2 | 1522.46 | TIME_LIMIT | 867.19 | 864.30 | 0.33 | 43.04 | 43.00 | 0.42 | 0.81 | - | - |
| fleet | K6_B2_pack0.6 | 0 | rho0_R0 | r2 | 1134.20 | OPTIMAL | 749.56 | 749.56 | 0.00 | 33.91 | 33.81 | 0.90 | 0.94 | 0.15 | 0.00 |
| fleet | K6_B2_pack0.6 | 1 | rho0_R0 | r5_range | 1480.76 | OPTIMAL | 857.02 | 857.01 | 0.00 | 42.12 | 42.04 | 0.73 | 0.85 | 0.32 | 0.06 |
| fleet | K6_B3_pack0.6 | 0 | rho0_R0 | r2 | 1057.09 | OPTIMAL | 750.48 | 750.43 | 0.01 | 29.01 | 28.94 | 0.90 | 0.94 | - | - |
| fleet | K6_B3_pack0.6 | 1 | rho0_R0 | r5_range | 1542.20 | OPTIMAL | 857.48 | 857.48 | 0.00 | 44.40 | 44.30 | 0.75 | 0.85 | - | - |
| fleet | K6_B4_pack0.6 | 0 | rho0_R0 | r2 | 1057.78 | OPTIMAL | 751.40 | 751.40 | 0.00 | 28.96 | 28.92 | 0.90 | 0.94 | - | - |
| fleet | K6_B4_pack0.6 | 1 | rho0_R0 | r2 | 1505.30 | OPTIMAL | 858.20 | 858.20 | 0.00 | 42.99 | 42.91 | 0.79 | 0.85 | - | - |
| fleet | K8_B1_pack0.6 | 0 | rho0_R0 | r5_range | 1289.69 | OPTIMAL | 688.36 | 688.36 | 0.00 | 46.63 | 46.55 | 0.79 | 1.00 | - | - |
| fleet | K8_B1_pack0.6 | 1 | rho0_R0 | r2 | 1465.44 | OPTIMAL | 798.19 | 798.19 | 0.00 | 45.53 | 45.48 | 0.69 | 0.94 | - | - |
| fleet | K8_B2_pack0.6 | 0 | rho0_R0 | r5_range | 785.12 | OPTIMAL | 688.06 | 688.06 | 0.00 | 12.36 | 12.27 | 0.98 | 1.00 | - | - |
| fleet | K8_B2_pack0.6 | 1 | rho0_R0 | r2 | 1216.68 | OPTIMAL | 782.53 | 782.46 | 0.01 | 35.68 | 35.62 | 0.90 | 0.94 | - | - |
| fleet | K8_B3_pack0.6 | 0 | rho0_R0 | r5_range | 745.69 | OPTIMAL | 688.78 | 688.78 | 0.00 | 7.63 | 7.55 | 1.00 | 1.00 | - | - |
| fleet | K8_B3_pack0.6 | 1 | rho0_R0 | r2 | 1113.27 | OPTIMAL | 782.96 | 782.93 | 0.00 | 29.67 | 29.61 | 0.96 | 0.94 | - | - |
| fleet | K8_B4_pack0.6 | 0 | rho0_R0 | r5_range | 739.76 | OPTIMAL | 689.77 | 689.77 | 0.00 | 6.76 | 6.70 | 1.00 | 1.00 | - | - |
| fleet | K8_B4_pack0.6 | 1 | rho0_R0 | r5_range | 1008.07 | OPTIMAL | 783.83 | 783.83 | 0.00 | 22.24 | 22.18 | 0.98 | 0.94 | - | - |
| levers | M2 | 0 | rho0_R0 | r5_range | 1792.94 | OPTIMAL | 991.43 | 991.33 | 0.01 | 44.70 | 44.62 | 0.64 | 0.97 | - | - |
| levers | M2 | 1 | rho0_R0 | r2 | 2040.72 | TIME_LIMIT | 1124.95 | 1112.29 | 1.13 | 44.87 | 44.81 | 0.61 | 0.81 | - | - |
| levers | M2 | 2 | rho0_R0 | r5_range | 1984.87 | TIME_LIMIT | 1052.86 | 1044.86 | 0.76 | 46.96 | 46.89 | 0.59 | 0.89 | - | - |
| levers | P0 | 0 | rho0_R0 | r5_range | 1686.90 | OPTIMAL | 1089.25 | 1089.25 | 0.00 | 35.43 | 35.35 | 0.45 | 0.86 | - | - |
| levers | P0 | 1 | rho0_R0 | r5_range | 1765.40 | OPTIMAL | 1176.95 | 1176.95 | 0.00 | 33.33 | 33.26 | 0.38 | 0.77 | - | - |
| levers | P0 | 2 | rho0_R0 | r2 | 1796.48 | OPTIMAL | 1147.19 | 1147.19 | 0.00 | 36.14 | 36.09 | 0.52 | 0.80 | - | - |
| levers | eps50 | 0 | rho0_R0 | r5_range | 1515.57 | OPTIMAL | 990.58 | 990.53 | 0.01 | 34.64 | 34.54 | 0.86 | 0.97 | - | - |
| levers | eps50 | 1 | rho0_R0 | r2 | 2077.90 | OPTIMAL | 1119.09 | 1119.07 | 0.00 | 46.14 | 46.09 | 0.72 | 0.83 | - | - |
| levers | eps50 | 2 | rho0_R0 | r2 | 1861.66 | OPTIMAL | 1051.04 | 1051.03 | 0.00 | 43.54 | 43.48 | 0.77 | 0.89 | - | - |
| levers | lockout0.05 | 0 | rho0_R0 | r2 | 1813.34 | TIME_LIMIT | 994.50 | 990.59 | 0.39 | 45.16 | 45.11 | 0.69 | 0.95 | - | - |
| levers | lockout0.05 | 1 | rho0_R0 | r2 | 2039.45 | TIME_LIMIT | 1122.46 | 1112.48 | 0.89 | 44.96 | 44.91 | 0.53 | 0.81 | - | - |
| levers | lockout0.05 | 2 | rho0_R0 | r5_range | 1948.78 | TIME_LIMIT | 1054.10 | 1045.12 | 0.85 | 45.91 | 45.86 | 0.58 | 0.89 | - | - |
| levers | lockout0.1 | 0 | rho0_R0 | r2 | 1813.34 | TIME_LIMIT | 994.50 | 990.59 | 0.39 | 45.16 | 45.11 | 0.69 | 0.95 | - | - |
| levers | lockout0.1 | 1 | rho0_R0 | r2 | 2039.45 | TIME_LIMIT | 1122.46 | 1112.48 | 0.89 | 44.96 | 44.91 | 0.53 | 0.81 | - | - |
| levers | lockout0.1 | 2 | rho0_R0 | r5_range | 1948.78 | TIME_LIMIT | 1054.10 | 1045.12 | 0.85 | 45.91 | 45.86 | 0.58 | 0.89 | - | - |
| levers | lockout0.25 | 0 | rho0_R0 | r2 | 1813.33 | TIME_LIMIT | 992.66 | 991.23 | 0.14 | 45.26 | 45.20 | 0.69 | 0.97 | - | - |
| levers | lockout0.25 | 1 | rho0_R0 | r5_range | 2021.17 | TIME_LIMIT | 1122.83 | 1113.60 | 0.82 | 44.45 | 44.39 | 0.44 | 0.81 | - | - |
| levers | lockout0.25 | 2 | rho0_R0 | r5_range | 1948.76 | TIME_LIMIT | 1054.19 | 1047.12 | 0.67 | 45.90 | 45.86 | 0.58 | 0.89 | - | - |
| levers | reference | 0 | rho0_R0 | r2 | 1813.36 | OPTIMAL | 991.31 | 991.31 | 0.00 | 45.33 | 45.26 | 0.69 | 0.97 | 2.75 | 1.84 |
| levers | reference | 1 | rho0_R0 | r2 | 2080.13 | TIME_LIMIT | 1125.14 | 1111.69 | 1.20 | 45.91 | 45.85 | 0.62 | 0.81 | 1.40 | 0.82 |
| levers | reference | 2 | rho0_R0 | r5_range | 1984.75 | TIME_LIMIT | 1059.26 | 1044.71 | 1.37 | 46.63 | 46.56 | 0.59 | 0.89 | 4.95 | 2.46 |

The 144 baseline-only fleet grid cells (packs 0.5 / 0.75 / 1.0 kWh, seeds 0-2) are listed in `figs/x5_per_instance.csv`.

## Appendix B. Iso-cost frontier, all packs

| policy | pack kWh | K | B/site | n | system cost (USD/window) | served | saving per extra bike | saving per extra spare (net) | spare cost | lever that pays |
|---|---|---|---|---|---|---|---|---|---|---|
| best_rule | 0.50 | 4 | 1 | 3 | 2052.3 [1857.7, 2246.9] | 0.444 | 65.78 [-114.47, 246.03] | 5.10 [-83.24, 93.45] | 0.277 | spare |
| best_rule | 0.50 | 4 | 2 | 3 | 2037.0 [1852.5, 2221.5] | 0.569 | 174.71 [19.64, 329.77] | -9.33 [-12.79, -5.88] | 0.277 | bike |
| best_rule | 0.50 | 4 | 3 | 3 | 2065.0 [1887.3, 2242.7] | 0.583 | 172.64 [-64.94, 410.21] | 5.60 [-9.97, 21.18] | 0.277 | both pay; spare cheaper per USD |
| best_rule | 0.50 | 4 | 4 | 3 | 2048.2 [1914.8, 2181.6] | 0.583 | 169.36 [-67.91, 406.63] | - | 0.277 | bike |
| best_rule | 0.50 | 6 | 1 | 3 | 2098.6 [1749.3, 2448.0] | 0.576 | 47.53 [-15.65, 110.72] | 77.72 [-34.64, 190.08] | 0.277 | spare |
| best_rule | 0.50 | 6 | 2 | 3 | 1865.5 [1432.1, 2298.8] | 0.750 | 82.59 [-12.04, 177.22] | -10.71 [-76.80, 55.37] | 0.277 | neither pays |
| best_rule | 0.50 | 6 | 3 | 3 | 1897.6 [1275.2, 2520.0] | 0.826 | 176.63 [94.22, 259.05] | 3.42 [-7.08, 13.91] | 0.277 | both pay; spare cheaper per USD |
| best_rule | 0.50 | 6 | 4 | 3 | 1887.3 [1291.8, 2482.9] | 0.806 | 183.42 [96.90, 269.93] | - | 0.277 | bike |
| best_rule | 0.50 | 8 | 1 | 3 | 2181.4 [1829.6, 2533.3] | 0.618 | 68.21 [35.14, 101.28] | 101.09 [1.35, 200.83] | 0.277 | spare |
| best_rule | 0.50 | 8 | 2 | 3 | 1878.2 [1273.2, 2483.2] | 0.819 | 90.05 [-136.39, 316.49] | 51.98 [3.74, 100.22] | 0.277 | both pay; spare cheaper per USD |
| best_rule | 0.50 | 8 | 3 | 3 | 1722.2 [1261.7, 2182.8] | 0.917 | 73.27 [-65.25, 211.80] | 7.94 [-16.35, 32.23] | 0.277 | spare |
| best_rule | 0.50 | 8 | 4 | 3 | 1698.4 [1245.0, 2151.8] | 0.944 | 93.99 [-52.11, 240.08] | - | 0.277 | bike |
| best_rule | 0.50 | 10 | 1 | 3 | 2222.9 [1805.4, 2640.4] | 0.694 | - | 115.65 [7.61, 223.70] | 0.277 | spare |
| best_rule | 0.50 | 10 | 2 | 3 | 1875.9 [1208.9, 2543.0] | 0.889 | - | 40.79 [-65.24, 146.83] | 0.277 | spare |
| best_rule | 0.50 | 10 | 3 | 3 | 1753.6 [1403.3, 2103.8] | 0.965 | - | 21.75 [-42.06, 85.56] | 0.277 | spare |
| best_rule | 0.50 | 10 | 4 | 3 | 1688.3 [1519.8, 1856.9] | 0.993 | - | - | 0.277 | - |
| best_rule | 0.60 | 4 | 1 | 2 | 2040.4 (n=2) | 0.479 | 94.95 (n=2) | 12.61 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 4 | 2 | 2 | 2002.6 (n=2) | 0.615 | 169.03 (n=2) | -5.19 (n=2) | 0.332 | bike |
| best_rule | 0.60 | 4 | 3 | 2 | 2018.1 (n=2) | 0.625 | 180.39 (n=2) | 5.64 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 4 | 4 | 2 | 2001.2 (n=2) | 0.625 | 180.71 (n=2) | - | 0.332 | bike |
| best_rule | 0.60 | 6 | 1 | 2 | 2028.4 (n=2) | 0.490 | 58.19 (n=2) | 61.99 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 6 | 2 | 2 | 1842.4 (n=2) | 0.812 | 153.11 (n=2) | 2.39 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 6 | 3 | 2 | 1835.3 (n=2) | 0.823 | 184.99 (n=2) | 5.85 (n=2) | 0.332 | both pay; spare cheaper per USD |
| best_rule | 0.60 | 6 | 4 | 2 | 1817.7 (n=2) | 0.844 | 203.95 (n=2) | - | 0.332 | bike |
| best_rule | 0.60 | 8 | 1 | 2 | 2089.9 (n=2) | 0.740 | - | 125.27 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 8 | 2 | 2 | 1714.1 (n=2) | 0.938 | - | 23.64 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 8 | 3 | 2 | 1643.2 (n=2) | 0.979 | - | 18.49 (n=2) | 0.332 | spare |
| best_rule | 0.60 | 8 | 4 | 2 | 1587.7 (n=2) | 0.990 | - | - | 0.332 | - |
| best_rule | 0.75 | 4 | 1 | 3 | 2083.5 [1903.5, 2263.4] | 0.479 | 66.87 [-40.43, 174.17] | -3.15 [-38.86, 32.57] | 0.415 | neither pays |
| best_rule | 0.75 | 4 | 2 | 3 | 2092.9 [1987.7, 2198.1] | 0.569 | 187.81 [-106.24, 481.86] | -6.83 [-41.17, 27.50] | 0.415 | bike |
| best_rule | 0.75 | 4 | 3 | 3 | 2113.4 [1927.6, 2299.3] | 0.583 | 209.16 [13.93, 404.39] | -1.82 [-7.85, 4.22] | 0.415 | bike |
| best_rule | 0.75 | 4 | 4 | 3 | 2118.9 [1930.2, 2307.5] | 0.583 | 207.95 [6.65, 409.26] | - | 0.415 | bike |
| best_rule | 0.75 | 6 | 1 | 3 | 2127.6 [1924.2, 2331.0] | 0.562 | 78.36 [36.37, 120.36] | 77.48 [-75.94, 230.90] | 0.415 | spare |
| best_rule | 0.75 | 6 | 2 | 3 | 1895.2 [1273.4, 2517.0] | 0.840 | 91.39 [39.00, 143.78] | 7.40 [-36.08, 50.89] | 0.415 | both pay; spare cheaper per USD |
| best_rule | 0.75 | 6 | 3 | 3 | 1873.0 [1333.1, 2412.9] | 0.833 | 167.01 [53.62, 280.41] | -2.62 [-15.46, 10.22] | 0.415 | bike |
| best_rule | 0.75 | 6 | 4 | 3 | 1880.8 [1321.8, 2439.9] | 0.826 | 205.45 [137.02, 273.88] | - | 0.415 | bike |
| best_rule | 0.75 | 8 | 1 | 3 | 2148.8 [2016.5, 2281.1] | 0.632 | 13.86 [-71.77, 99.50] | 86.16 [-114.86, 287.18] | 0.415 | spare |
| best_rule | 0.75 | 8 | 2 | 3 | 1890.3 [1193.0, 2587.6] | 0.889 | 69.71 [3.79, 135.63] | 57.82 [-15.87, 131.51] | 0.415 | spare |
| best_rule | 0.75 | 8 | 3 | 3 | 1716.8 [1106.6, 2327.1] | 0.972 | 102.63 [-108.48, 313.75] | 23.00 [-50.61, 96.62] | 0.415 | both pay; spare cheaper per USD |
| best_rule | 0.75 | 8 | 4 | 3 | 1647.8 [1220.7, 2075.0] | 0.986 | 74.93 [-65.40, 215.26] | - | 0.415 | neither pays |
| best_rule | 0.75 | 10 | 1 | 3 | 2298.9 [2258.9, 2339.0] | 0.701 | - | 123.39 [-73.91, 320.69] | 0.415 | spare |
| best_rule | 0.75 | 10 | 2 | 3 | 1928.8 [1361.4, 2496.1] | 0.965 | - | 79.77 [-53.25, 212.78] | 0.415 | spare |
| best_rule | 0.75 | 10 | 3 | 3 | 1689.5 [1501.3, 1877.6] | 0.993 | - | 4.54 [-6.63, 15.70] | 0.415 | spare |
| best_rule | 0.75 | 10 | 4 | 3 | 1675.8 [1502.6, 1849.1] | 0.993 | - | - | 0.415 | - |
| best_rule | 1.00 | 4 | 1 | 3 | 2054.3 [1918.3, 2190.4] | 0.514 | 120.94 [55.07, 186.81] | -12.73 [-28.49, 3.04] | 0.553 | bike |
| best_rule | 1.00 | 4 | 2 | 3 | 2092.5 [1918.4, 2266.6] | 0.562 | 170.03 [-119.06, 459.12] | -1.78 [-7.08, 3.51] | 0.553 | bike |
| best_rule | 1.00 | 4 | 3 | 3 | 2097.9 [1928.4, 2267.4] | 0.604 | 191.72 [-124.35, 507.79] | -0.55 [-0.55, -0.55] | 0.553 | bike |
| best_rule | 1.00 | 4 | 4 | 3 | 2099.5 [1930.0, 2269.0] | 0.604 | 188.74 [-116.41, 493.89] | - | 0.553 | bike |
| best_rule | 1.00 | 6 | 1 | 3 | 1990.3 [1863.1, 2117.6] | 0.618 | 93.33 [-32.90, 219.57] | 20.00 [-150.26, 190.25] | 0.553 | both pay; spare cheaper per USD |
| best_rule | 1.00 | 6 | 2 | 3 | 1930.3 [1297.4, 2563.3] | 0.847 | 174.19 [120.76, 227.62] | 12.68 [-11.67, 37.03] | 0.553 | both pay; spare cheaper per USD |
| best_rule | 1.00 | 6 | 3 | 3 | 1892.3 [1200.5, 2584.1] | 0.847 | 210.71 [62.87, 358.55] | -2.54 [-11.17, 6.09] | 0.553 | bike |
| best_rule | 1.00 | 6 | 4 | 3 | 1899.9 [1232.7, 2567.2] | 0.847 | 220.15 [61.40, 378.89] | - | 0.553 | bike |
| best_rule | 1.00 | 8 | 1 | 3 | 1981.6 [1604.2, 2358.9] | 0.694 | 59.52 [-31.05, 150.10] | 73.90 [22.81, 125.00] | 0.553 | spare |
| best_rule | 1.00 | 8 | 2 | 3 | 1759.9 [1233.3, 2286.4] | 0.931 | 48.69 [-3.64, 101.03] | 37.02 [-10.66, 84.70] | 0.553 | spare |
| best_rule | 1.00 | 8 | 3 | 3 | 1648.8 [1251.4, 2046.2] | 0.986 | 62.02 [-29.74, 153.77] | 3.75 [-15.40, 22.91] | 0.553 | spare |
| best_rule | 1.00 | 8 | 4 | 3 | 1637.5 [1286.9, 1988.2] | 0.986 | 55.91 [-18.84, 130.66] | - | 0.553 | neither pays |
| best_rule | 1.00 | 10 | 1 | 3 | 2040.4 [1494.6, 2586.2] | 0.771 | - | 66.68 [17.49, 115.87] | 0.553 | spare |
| best_rule | 1.00 | 10 | 2 | 3 | 1840.4 [1415.7, 2265.0] | 0.944 | - | 45.90 [-33.46, 125.27] | 0.553 | spare |
| best_rule | 1.00 | 10 | 3 | 3 | 1702.6 [1470.1, 1935.2] | 0.993 | - | -0.32 [-2.64, 1.99] | 0.553 | neither pays |
| best_rule | 1.00 | 10 | 4 | 3 | 1703.6 [1470.1, 1937.1] | 0.993 | - | - | 0.553 | - |
| ilp | 0.60 | 4 | 1 | 2 | 1311.6 (n=2) | 0.688 | 73.06 (n=2) | 0.50 (n=2) | 0.332 | spare |
| ilp | 0.60 | 4 | 2 | 2 | 1310.1 (n=2) | 0.698 | 74.56 (n=2) | -0.29 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 4 | 3 | 2 | 1311.0 (n=2) | 0.698 | 74.47 (n=2) | -0.33 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 4 | 4 | 2 | 1312.0 (n=2) | 0.698 | 74.52 (n=2) | - | 0.332 | neither pays |
| ilp | 0.60 | 6 | 1 | 2 | 1343.4 (n=2) | 0.875 | 32.59 (n=2) | 1.50 (n=2) | 0.332 | spare |
| ilp | 0.60 | 6 | 2 | 2 | 1338.9 (n=2) | 0.896 | 33.99 (n=2) | -0.35 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 6 | 3 | 2 | 1340.0 (n=2) | 0.896 | 34.04 (n=2) | -0.30 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 6 | 4 | 2 | 1340.9 (n=2) | 0.896 | 33.98 (n=2) | - | 0.332 | neither pays |
| ilp | 0.60 | 8 | 1 | 2 | 1456.1 (n=2) | 0.969 | - | 2.43 (n=2) | 0.332 | spare |
| ilp | 0.60 | 8 | 2 | 2 | 1448.8 (n=2) | 0.969 | - | -0.32 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 8 | 3 | 2 | 1449.8 (n=2) | 0.969 | - | -0.34 (n=2) | 0.332 | neither pays |
| ilp | 0.60 | 8 | 4 | 2 | 1450.8 (n=2) | 0.969 | - | - | 0.332 | - |

## Digest corrections (2026-10-18)

Applied after the two-refuter verification pass; numbers recomputed from the records (no solves). Items marked "one verifier" are qualifiers added where only one verifier objected.

- C3 (boundary robustness): both verifiers refuted the unqualified 'headline does not depend on the boundary'. Now restricted to 6 bikes and the solved part of the M1 grid; added the gap move 0.22 [0.03, 0.40] points, the mean proven lower bound 0.65 USD and the growth of the price with fleet size (8 bikes 11.63 USD = 1.17 %; 10 bikes 29.41 USD, true value in [0, 50.96]).
- C4 (fleet sizing): both verifiers refuted parts of the sizing claim. Restricted to the tested grid; added per-seed gaps (13.0 / 21.3 %), the matched-service comparison (ILP K8 B2 1448.8 USD, served 0.969, 8.75 % below the rule's best design), the grid-edge caveat, and replaced 'always add spares first' (false for the rule at K4 B2: spare -9.33 / -5.19 USD net, bike +169-175 USD).
- C6 (rule non-monotonicity): both verifiers refuted the unqualified statement. Lock-out lowers the rule cost on 2 of 3 seeds only; no rule lever response is significant at n = 3 (P = 0: -209.8 [-448.2, 28.6]; lock-out -25.6 [-80.8, 29.7] and -31.7 [-105.5, 42.1]). Anomaly rewritten.
- C1 (one verifier): added that the 6 -> 10-bike rise is significant (Welch p = 0.04) but 8 -> 10 is not (p = 0.54) and that fleet and demand are confounded.
