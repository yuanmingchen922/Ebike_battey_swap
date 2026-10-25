# X6 -- Manhattan-wide siting on `r5_manhattan`: final report

Source: `outputs/r5_x6_manhattan/` (driver `experiments/r5_x6_manhattan.py`, finished 2026-10-18 03:43 after 271.4 min; log `outputs/r5_lanes/r5_x6_manhattan.log`). Every number below is recomputed from `cache/index.jsonl` and the stage `records.jsonl` files (last record per cache key; where several cache keys share one layout key, i.e. the A4 lever variants *position*, *shuttle* and *grid*, the earliest row is the un-modified layout and the lever rows are matched to the logged `V_new`). No ILP was re-solved. Instance: 15 lattice candidates over Manhattan south of 110th St, six bridge/tunnel rider depots, 8 bikes, 40 orders, dinner window 16:00-20:00 (4 h, 48 slots), three demand scenarios (seeds 0-2, p = 1/3 each). `V` = expected total cost per 4-h window (operating cost + allocated set-up cost, USD), i.e. the probability-weighted mean over the three scenarios. Budget unit m = 52,150 USD (one SC station with B = 3 spare batteries and C = 2 chargers). Protocol: aggregated ILP (O1), Gurobi Threads 3, Seed 0, TimeLimit 300 s. Every ILP total is an upper bound on the written optimum (rebalancing moves only into open sites and depots); the R2.4 geometry caveat applies (real restaurants and candidate coordinates on a synthetic 150 m grid). 95 % confidence intervals are exact Student-t intervals over the n = 3 scenarios (t_{0.975,2} = 4.303) unless stated; with n = 3 they are wide and mostly reflect scenario-to-scenario demand variation that is common to all methods, so paired differences are reported alongside.

## Summary

On the Manhattan-wide instance the coordinated ILP lower level again beats the conservative operating baseline (best_rule = per-instance minimum over r2, r5_range, r5_transfer and r5) by a margin that matches the earlier rounds: on the like-for-like relaxed control (rho = 0, R_end = 0) the gap is 31.8 % [23.1, 40.5] at the bi-level layout and 34.3 % [30.7, 37.8] pooled over all 21 layout-scenario cells of the seven compared layouts (34.3 % [20.8, 47.7] when the layouts are first averaged within each scenario, n = 3), against 31.8 % +/- 8.2 for nyc4h in rounds 3-4. The siting side is weaker than intended. The bi-level greedy + local search (k_screen 2, `x6` size menu) exhausted its 125-min wall budget after pricing four layouts: it returned no layout at m = 1 (its only usable singleton, M06:SC:B4:C2, costs 52,600 USD > 52,150 USD) and the same two-site layout M06:SC:B4:C2 + M12:S:B3:C0 (103,950 USD) at m = 2, 3, 4. Under the ILP follower with written targets this layout (V = 703.1 USD) is beaten by the demand-proportional rule layout CSCD at m = 2 (M08 + M09, V = 676.6 USD) in all three scenarios (paired gap -4.0 % [-8.7, 0.8]; still -2.8 % when the two TIME_LIMIT incumbents are replaced by their MIP lower bounds), while on the relaxed control the two layouts tie (675.0 vs 675.0 USD). The bi-level layout wins only when the follower is NOT the ILP with written targets: under rule r2 it is 12-14 % cheaper than every rule-sited layout at m = 2 in every scenario, and under the selfish follower it is cheaper in every scenario but by only 2.6-10.6 % (95 % CI includes zero). The marginal-lever table shows that one extra spare battery or charger (400-450 USD) lowers V by about 20 USD per window under the ILP follower in every scenario, while under the selfish follower the mean effect is positive but not significant and driven by scenario 0 (CIs include zero); the policy-aware (selfish-follower) siting search also ran out of wall time and returned a poor single-site layout (M07) at every budget. Averaged over scenarios, compliance lowers cost at every step and the curve is concave (savings accelerate): V falls from 1165 USD with no compliant rider to 703 USD with full compliance and drops below the selfish-equilibrium cost between alpha_c = 0.25 and 0.5 (about 0.32 by linear interpolation). Scenario 1 is not monotone (it rises from alpha_c = 0 to 0.25).

## Coverage

| item | count | detail |
|---|---|---|
| ILP lower-level solves, written targets (unique cache keys) | 66 | OPTIMAL 47, TIME_LIMIT 18, INFEASIBLE_ILP 1 (M07:SC:B3:C1, scenario 0) |
| ILP lower-level solves, relaxed control | 21 | OPTIMAL 20, TIME_LIMIT 1 |
| TIME_LIMIT MIP gaps | 19 | min 0.39 %, median 1.54 %, max 2.75 % (max: present-day proxy M03+M08, scenario 1, written) |
| rule (r2) evaluations | 1026 | POLICY 972, INFEASIBLE_TERMINAL 54 (sweep screening only) |
| selfish-equilibrium evaluations | 84 | MSA, tol 0.01, cap 10 iterations; 82 converged, 2 stopped at the cap without converging (CSCD m = 2 `M08|M09` scenario 2, V 1212.96; CSAV m = 3 `M02|M08|M14` scenario 1, V 872.23); the headline relaxed-control selfish row of CSCD m = 2 scenario 2 also did not converge (digest correction; the earlier text said all converged) |
| SKIPPED_BUDGET (stage rows) | 14 | sweep greedy moves 3; baselines present-day ILP at m = 2-4 3 (later solved in the headline stage and used here); policy-aware greedy moves 6; levers (shuttle, grid) under ILP 2 |
| solver / script errors | 0 | `n_errors` = 0 in every stage; all six stages status OK |
| headline cells | 21 | 20 OK + 1 NO_ILP_SCHEDULE (M07 scenario 0: written ILP infeasible; its relaxed cell exists and is included below) |
| stages complete | 2 / 6 | sweep, baselines, policy_aware, levers truncated by their wall budgets (`complete = False`); compliance and headline complete |

## Table 1 -- Siting methods per budget under three followers (written targets)

V in USD per 4-h window, mean [95 % CI] over the three scenarios. ILP status per scenario: O = OPTIMAL, T = TIME_LIMIT (incumbent, an upper bound), I = INFEASIBLE_ILP. Served = share of orders served under the ILP follower. Rule layouts: each site SC with B = C = 1 plus extra spares/chargers bought alternately (IJCAI-15 Sec. 5.1); present-day proxy = DOHMH-restaurant-weighted sites, capacity-matched to the bi-level layout (to CSAV at m = 1).

| m | method | layout | invest. (kUSD) | V ILP | ILP st. | served ILP | V rule r2 | V selfish |
|---|---|---|---|---|---|---|---|---|
| 1 | CSCD | `M09:SC:B3:C2` | 52.15 | 796.4 [724.2, 868.6] | OTO | 0.683 | 1376.4 [1083.5, 1669.4] | 1376.4 [1083.5, 1669.4] |
| 1 | CSTC | `M09:SC:B3:C2` | 52.15 | 796.4 [724.2, 868.6] | OTO | 0.683 | 1376.4 [1083.5, 1669.4] | 1376.4 [1083.5, 1669.4] |
| 1 | CSAV | `M08:SC:B3:C2` | 52.15 | 795.4 [752.1, 838.8] | OOO | 0.675 | 1345.5 [1302.3, 1388.6] | 1345.5 [1302.3, 1388.6] |
| 1 | Present-day proxy | `M08:SC:B3:C2` | 52.15 | 795.4 [752.1, 838.8] | OOO | 0.675 | 1345.5 [1302.3, 1388.6] | 1345.5 [1302.3, 1388.6] |
| 1 | Bi-level greedy+LS | none (wall budget spent; only singleton over budget) | - | - | - | - | - | - |
| 1 | Policy-aware [selfish] | `M07:SC:B3:C1` | 51.75 | 928.7 (n=2) | IOO | 0.463 | 1224.4 [1184.4, 1264.5] | 1224.4 [1184.4, 1264.5] |
| 2 | CSCD | `M08:SC:B3:C2|M09:SC:B3:C2` | 104.30 | 676.6 [580.0, 773.1] | OOO | 0.908 | 1168.7 [880.3, 1457.2] | 1123.7 [890.9, 1356.6] |
| 2 | CSTC | `M08:SC:B3:C2|M09:SC:B3:C2` | 104.30 | 676.6 [580.0, 773.1] | OOO | 0.908 | 1168.7 [880.3, 1457.2] | 1123.7 [890.9, 1356.6] |
| 2 | CSAV | `M08:SC:B3:C2|M14:SC:B3:C2` | 104.30 | 699.2 [597.6, 800.8] | OOO | 0.892 | 1412.7 [1335.4, 1490.0] | 1248.6 [1009.7, 1487.4] |
| 2 | Present-day proxy | `M03:SC:B3:C1|M08:SC:B4:C1` | 103.95 | 723.1 [678.7, 767.6] | TTT | 0.825 | 1112.3 [571.6, 1653.0] | 1086.6 [819.1, 1354.1] |
| 2 | Bi-level greedy+LS | `M06:SC:B4:C2|M12:S:B3:C0` | 103.95 | 703.1 [630.2, 776.0] | TTO | 0.858 | 1020.8 [737.4, 1304.2] | 1057.5 [931.7, 1183.2] |
| 2 | Policy-aware [selfish] | `M07:SC:B3:C1` | 51.75 | 928.7 (n=2) | IOO | 0.463 | 1224.4 [1184.4, 1264.5] | 1224.4 [1184.4, 1264.5] |
| 3 | CSCD | `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2` | 156.45 | 680.2 [575.7, 784.6] | OOO | 0.925 | 1091.8 [457.5, 1726.1] | 973.3 [527.0, 1419.7] |
| 3 | CSTC | `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2` | 156.45 | 679.1 [571.7, 786.5] | OOO | 0.925 | 1148.9 [746.2, 1551.5] | 1007.1 [556.1, 1458.2] |
| 3 | CSAV | `M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2` | 156.45 | 687.0 [594.7, 779.2] | OOO | 0.925 | 1217.8 [810.0, 1625.5] | 1067.8 [647.0, 1488.6] |
| 3 | Present-day proxy | `M03:SC:B3:C1|M08:SC:B4:C1` | 103.95 | 723.1 [678.7, 767.6] | TTT | 0.825 | 1112.3 [571.6, 1653.0] | 1086.6 [819.1, 1354.1] |
| 3 | Bi-level greedy+LS | `M06:SC:B4:C2|M12:S:B3:C0` | 103.95 | 703.1 [630.2, 776.0] | TTO | 0.858 | 1020.8 [737.4, 1304.2] | 1057.5 [931.7, 1183.2] |
| 3 | Policy-aware [selfish] | `M07:SC:B3:C1` | 51.75 | 928.7 (n=2) | IOO | 0.463 | 1224.4 [1184.4, 1264.5] | 1224.4 [1184.4, 1264.5] |
| 4 | CSCD | `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2` | 208.60 | 692.0 [586.3, 797.6] | OOO | 0.925 | 1091.1 [396.6, 1785.5] | 955.5 [554.2, 1356.9] |
| 4 | CSTC | `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2` | 208.60 | 690.5 [582.5, 798.6] | OOO | 0.933 | 1162.1 [681.3, 1642.8] | 961.2 [504.0, 1418.4] |
| 4 | CSAV | `M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2` | 208.60 | 694.3 [595.3, 793.3] | OOO | 0.933 | 1099.5 [344.9, 1854.2] | 968.2 [643.7, 1292.7] |
| 4 | Present-day proxy | `M03:SC:B3:C1|M08:SC:B4:C1` | 103.95 | 723.1 [678.7, 767.6] | TTT | 0.825 | 1112.3 [571.6, 1653.0] | 1086.6 [819.1, 1354.1] |
| 4 | Bi-level greedy+LS | `M06:SC:B4:C2|M12:S:B3:C0` | 103.95 | 703.1 [630.2, 776.0] | TTO | 0.858 | 1020.8 [737.4, 1304.2] | 1057.5 [931.7, 1183.2] |
| 4 | Policy-aware [selfish] | `M07:SC:B3:C1` | 51.75 | 928.7 (n=2) | IOO | 0.463 | 1224.4 [1184.4, 1264.5] | 1224.4 [1184.4, 1264.5] |

Notes. CSCD and CSTC choose the same layout at m = 1 and m = 2. The present-day proxy at m = 1 coincides with CSAV (M08). The present-day ILP values at m = 2-4 are three TIME_LIMIT incumbents (gaps 1.41 %, 2.75 %, 1.72 %) produced in the headline stage. The policy-aware ILP value has n = 2 because the written-target ILP is infeasible for M07 in scenario 0.

## Table 2 -- Paired comparison of the bi-level layout with rule siting

Gap = 100 (comparator - bi-level) / comparator per scenario; positive = bi-level layout cheaper. 'Best rule site' = per-scenario minimum over the CSCD, CSTC and CSAV layouts of that budget evaluated under the same follower. The 'LB' column replaces the bi-level TIME_LIMIT incumbents (scenarios 0, 1) by their MIP lower bounds (688.22, 665.05 USD), i.e. the most favourable value the bi-level layout could attain.

| m | follower | V bi-level | V best rule site | gap % mean [95 % CI] | per-scenario gaps % | gap % with bi-level LB (ILP only) |
|---|---|---|---|---|---|---|
| 2 | ilp | 703.1 | 676.6 | -3.99 [-8.74, 0.77] | -5.52, -4.60, -1.84 | -2.82 [-5.00, -0.65] |
| 2 | selfish | 1057.5 | 1123.7 | 5.69 [-4.90, 16.28] | 3.87, 2.63, 10.56 | - |
| 2 | rule r2 | 1020.8 | 1168.7 | 12.73 [9.86, 15.61] | 12.03, 14.07, 12.10 | - |
| 3 | ilp | 703.1 | 679.0 | -3.66 [-11.03, 3.70] | -6.58, -3.75, -0.65 | -2.50 [-7.36, 2.37] |
| 3 | selfish | 1057.5 | 973.3 | -10.59 [-49.93, 28.75] | -12.75, -25.23, 6.22 | - |
| 3 | rule r2 | 1020.8 | 1066.0 | 2.42 [-28.32, 33.17] | 12.01, -11.55, 6.80 | - |
| 4 | ilp | 703.1 | 690.4 | -1.94 [-9.17, 5.29] | -4.87, -1.89, 0.94 | -0.80 [-5.60, 4.01] |
| 4 | selfish | 1057.5 | 941.9 | -13.72 [-48.43, 20.99] | -21.80, -21.77, 2.42 | - |
| 4 | rule r2 | 1020.8 | 1046.8 | 0.57 [-31.57, 32.71] | 14.28, -11.42, -1.14 | - |

Capacity-matched comparison at equal investment (103,950 USD, two sites, B = 7, C = 2): bi-level M06:SC:B4:C2 + M12:S:B3:C0 vs present-day proxy M03:SC:B3:C1 + M08:SC:B4:C1.

| follower | V bi-level | V present-day | gap % mean [95 % CI] | per-scenario gaps % |
|---|---|---|---|---|
| ILP (written) | 703.1 | 723.1 | 2.79 [-2.36, 7.94] | 1.78, 5.17, 1.41 |
| rule r2 | 1020.8 | 1112.3 | 7.07 [-15.11, 29.26] | 14.81, -2.70, 9.10 |
| selfish | 1057.5 | 1086.6 | 2.31 [-12.28, 16.91] | 0.40, -2.37, 8.91 |
| ILP (relaxed control) | 675.0 | 684.6 | 1.43 [-3.10, 5.96] | 3.15, 1.61, -0.48 |
| ILP (relaxed control), vs CSCD m = 2 | 675.0 | 675.0 (CSCD) | -0.00 [-0.51, 0.51] | 0.18, 0.04, -0.22 |

## Table 3 -- Headline: ILP vs best_rule on the relaxed control (rho = 0, R_end = 0)

best_rule = per-instance minimum over r2, r5_range, r5_transfer (layouts with shuttle services only) and r5 by total cost (26). Gap = 100 (rule - ILP) / rule. selfish_eq = follower E (r5_selfish equilibrium). C_end_adjust = end-of-window inventory adjustment of the ILP schedule (USD). All relaxed ILP solves are OPTIMAL except present-day scenario 0 (TIME_LIMIT, gap 0.39 %).

| layout (role) | n | ILP total | best_rule total | gap vs best_rule % | gap vs r2 % | gap vs r5 % | gap vs selfish_eq % | gap end-adj. % | ILP C_end_adjust | best rule per scenario |
|---|---|---|---|---|---|---|---|---|---|---|
| `M06:SC:B4:C2|M12:S:B3:C0` (Bi-level greedy+LS (m=2-4)) | 3 | 675.0 [573.5, 776.5] | 992.8 [748.3, 1237.3] | 31.8 [23.1, 40.5] | 33.5 [19.4, 47.6] | 38.9 [26.2, 51.7] | 36.2 [29.1, 43.2] | 31.7 [23.1, 40.4] | 2.05 [1.83, 2.27] | r5_range, r2, r2 |
| `M07:SC:B3:C1` (Policy-aware [selfish] (m=1-4)) | 3 | 859.6 [807.2, 912.1] | 1224.4 [1184.4, 1264.5] | 29.8 [23.3, 36.3] | 29.8 [23.3, 36.3] | 33.1 [23.5, 42.8] | 29.8 [23.3, 36.3] | 29.8 [23.3, 36.2] | 1.06 [0.88, 1.24] | r2, r2, r2 |
| `M08:SC:B3:C2` (CSAV m=1 / present-day m=1) | 3 | 778.1 [727.7, 828.5] | 1331.6 [1302.2, 1361.1] | 41.6 [36.5, 46.6] | 42.2 [38.7, 45.7] | 43.1 [35.0, 51.3] | 42.2 [38.7, 45.7] | 41.5 [36.5, 46.6] | 1.04 [0.87, 1.21] | r2, r2, r5_range |
| `M08:SC:B3:C2|M09:SC:B3:C2` (CSCD m=2) | 3 | 675.0 [576.4, 773.5] | 1149.2 [890.8, 1407.5] | 41.1 [33.6, 48.6] | 42.0 [31.5, 52.6] | 44.3 [43.0, 45.6] | 39.8 [34.5, 45.2] | 41.0 [33.5, 48.6] | 1.75 [1.63, 1.87] | r5_range, r5_transfer, r2 |
| `M03:SC:B3:C1|M08:SC:B4:C1` (Present-day proxy m=2-4) | 3 | 684.6 [604.2, 764.9] | 1027.4 [677.6, 1377.2] | 32.7 [14.3, 51.1] | 37.0 [9.1, 64.9] | 37.8 [33.2, 42.4] | 36.8 [28.4, 45.2] | 32.6 [14.3, 51.0] | 1.99 [1.96, 2.02] | r5_range, r2, r5_transfer |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2` (CSTC m=3) | 3 | 677.9 [570.0, 785.8] | 1048.6 [470.7, 1626.5] | 33.5 [0.5, 66.4] | 40.4 [22.3, 58.4] | 38.5 [24.4, 52.7] | 31.5 [6.0, 57.0] | 33.4 [0.4, 66.3] | 2.35 [1.74, 2.96] | r5, r5_transfer, r2 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2` (CSTC m=4) | 3 | 689.8 [581.4, 798.3] | 994.7 [546.3, 1443.0] | 29.4 [2.9, 56.0] | 39.7 [16.9, 62.4] | 35.4 [16.5, 54.4] | 27.1 [5.2, 49.0] | 29.3 [2.8, 55.8] | 2.57 [2.08, 3.07] | r5_range, r5_transfer, r5_range |
| pooled, all cells | 21 | - | - | 34.3 [30.7, 37.8] | - | - | - | - | - | cells share scenarios; CI treats them as independent |
| pooled, scenario-clustered (mean over 7 layouts per scenario) | 3 | - | - | 34.3 [20.8, 47.7] | - | - | - | - | - | per-scenario means 38.4, 28.1, 36.2 |

The script's own `headline/RESULTS.md` lists M07 with n = 2 (28.65 %) because it drops the scenario whose written-target ILP is infeasible; the relaxed cell of that scenario is valid (OPTIMAL, gap 32.01 %), so n = 3 is used here. Reference: round 3/4 usd4h 29.55 % +/- 5.61 (n = 30), nyc4h 31.8 % +/- 8.2 (n = 10).

## Table 4 -- Written targets and the price of recovery

Price of recovery = written-target total minus relaxed-control total (USD per window) for the same policy and scenario. Rules do not act on the end-of-window targets, so their price of recovery is zero except where best_rule switches variant.

| layout | n | written ILP total | ILP st. | written gap vs best_rule % | written gap vs r2 % | written ILP C_end_adjust | price of recovery ILP (USD) | PoR ILP end-adj. (USD) | PoR best_rule (USD) |
|---|---|---|---|---|---|---|---|---|---|
| `M06:SC:B4:C2|M12:S:B3:C0` | 3 | 703.1 [630.2, 776.0] | TTO | 28.9 [18.3, 39.5] | 30.7 [16.0, 45.3] | 1.07 [0.78, 1.36] | 28.10 [-6.68, 62.88] | 27.12 [-7.72, 61.96] | 0.00 [0.00, 0.00] |
| `M07:SC:B3:C1` | 2 | 928.7 (n=2) | IOO | 23.6 (n=2) | 23.6 (n=2) | 0.45 (n=2) | 61.12 (n=2) | 60.55 (n=2) | 0.00 [0.00, 0.00] |
| `M08:SC:B3:C2` | 3 | 795.4 [752.1, 838.8] | OOO | 40.3 [35.8, 44.7] | 40.9 [38.8, 43.0] | 0.50 [0.48, 0.52] | 17.33 [-6.09, 40.76] | 16.79 [-6.53, 40.12] | 0.00 [0.00, 0.00] |
| `M08:SC:B3:C2|M09:SC:B3:C2` | 3 | 676.6 [580.0, 773.1] | OOO | 41.0 [33.3, 48.7] | 41.9 [31.2, 52.6] | 0.97 [0.81, 1.12] | 1.62 [-0.53, 3.77] | 0.83 [-1.20, 2.87] | 0.00 [0.00, 0.00] |
| `M03:SC:B3:C1|M08:SC:B4:C1` | 3 | 723.1 [678.7, 767.6] | TTT | 28.7 [4.6, 52.8] | 33.2 [-0.8, 67.2] | 1.07 [0.80, 1.33] | 38.55 [-5.16, 82.26] | 37.63 [-6.00, 81.26] | 0.00 [0.00, 0.00] |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2` | 3 | 679.1 [571.7, 786.5] | OOO | 33.9 [1.1, 66.7] | 40.3 [22.2, 58.4] | 1.15 [0.91, 1.38] | 1.16 [0.65, 1.66] | -0.05 [-0.18, 0.09] | 8.02 [-14.53, 30.56] |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2` | 3 | 690.5 [582.5, 798.6] | OOO | 30.3 [7.6, 52.9] | 39.6 [16.8, 62.4] | 1.75 [1.43, 2.08] | 0.71 [0.36, 1.07] | -0.11 [-0.35, 0.13] | 9.18 [-30.30, 48.66] |
| pooled, all cells | 20 | - | - | 32.8 [28.8, 36.9] | - | - | 19.23 [9.01, 29.45] | - | - |

The written ILP totals of the bi-level layout (scenarios 0, 1) and of the present-day proxy (all three) are TIME_LIMIT incumbents, so their price of recovery is an upper bound (MIP gaps 1.4-2.7 % of a ~700 USD total are 10-19 USD).

## Table 5 -- Marginal levers at the bi-level layout (M06:SC:B4:C2 + M12:S:B3:C0)

d_V = V(layout with lever) - V(reference), USD per window, mean [95 % CI] over the paired scenarios (negative = cheaper). Reference V: ILP 703.1 (scenarios 0, 1 TIME_LIMIT with gaps 1.90 % and 1.41 %), selfish 1057.5. 'd_V vs LB' compares the lever layout with the reference MIP lower bounds (688.22, 665.05, 733.20), i.e. the smallest possible ILP improvement.

| lever | site | follower | status | d_invest. (USD) | d_V mean [95 % CI] | per-scenario d_V | lever ILP st. | d_V vs ref LB | served ref -> new |
|---|---|---|---|---|---|---|---|---|---|
| spare | M06 | ilp | OK | 450 | -19.7 [-34.8, -4.6] | -23.7, -22.7, -12.7 | OOO | -12.1 [-15.8, -8.4] | 0.858 -> 0.900 |
| spare | M06 | selfish | OK | 450 | 103.4 [-270.8, 477.6] | 264.6, -33.8, 79.6 | - | - | 0.758 -> 0.833 |
| spare | M12 | ilp | OK | 450 | -19.7 [-44.1, 4.8] | -26.5, -24.1, -8.4 | OOO | -12.1 [-20.1, -4.0] | 0.858 -> 0.892 |
| spare | M12 | selfish | OK | 450 | 7.3 [-150.4, 165.0] | -39.2, -18.5, 79.6 | - | - | 0.758 -> 0.808 |
| charger | M06 | ilp | OK | 400 | -21.1 [-42.1, -0.0] | -27.8, -23.8, -11.6 | OOO | -13.4 [-17.5, -9.4] | 0.858 -> 0.908 |
| charger | M06 | selfish | OK | 400 | 47.7 [-204.1, 299.4] | 164.7, -8.8, -12.8 | - | - | 0.758 -> 0.792 |
| position | M06 | ilp | OK | 400 | -7.1 [-23.9, 9.7] | 0.3, -13.0, -8.5 | TOO | 0.6 [-28.3, 29.4] | 0.858 -> 0.883 |
| position | M06 | selfish | OK | 400 | 57.8 [-190.8, 306.3] | 173.3, 0.0, 0.0 | - | - | 0.758 -> 0.783 |
| position | M12 | ilp | OK | 400 | 0.5 [-1.5, 2.5] | 1.5, 0.1, 0.0 | TTO | 8.2 [-10.5, 26.8] | 0.858 -> 0.858 |
| position | M12 | selfish | OK | 400 | 0.0 [0.0, 0.0] | 0.0, 0.0, 0.0 | - | - | 0.758 -> 0.758 |
| shuttle | all pairs | ilp | SKIPPED_BUDGET | 0 | - | - | - | - | - |
| shuttle | all pairs | selfish | OK | 0 | 0.0 [0.0, 0.0] | 0.0, 0.0, 0.0 | - | - | 0.758 -> 0.758 |
| grid | group | ilp | SKIPPED_BUDGET | 0 | - | - | - | - | - |
| grid | group | selfish | OK | 0 | 0.0 [0.0, 0.0] | 0.0, 0.0, 0.0 | - | - | 0.758 -> 0.758 |

Lever definitions (from the stage log): spare / charger = +1 B or +1 C at the site (450 / 400 USD); position = M_j 1 -> 2 swap positions (400 USD); shuttle = one more shuttle vehicle; grid = P_grid x 1.1. Shuttle and grid were not priced under the ILP (SKIPPED_BUDGET); under the selfish follower they change nothing (d_V = 0 in every scenario).

## Table 6 -- Policy-aware siting and cross-evaluation

The policy-aware search (follower = selfish equilibrium, minimum served share 0) priced only two singletons (M07:SC:B3:C1, M06:SC:B4:C2) before its 30.7-min wall budget was spent on 399 rule-follower screening evaluations; all six forward moves were SKIPPED_BUDGET, so it returned M07:SC:B3:C1 at every budget. Each layout is evaluated under every follower (V, USD per window, mean [95 % CI]; n < 3 shown as n).

| layout | chosen by | invest. (kUSD) | ILP written | ILP relaxed | rule r2 | selfish | selfish - ILP written (price of decentralisation) |
|---|---|---|---|---|---|---|---|
| `M06:SC:B4:C2|M12:S:B3:C0` | bi-level (ILP follower), m = 2-4 | 103.95 | 703.1 [630.2, 776.0] | 675.0 [573.5, 776.5] | 1020.8 [737.4, 1304.2] | 1057.5 [931.7, 1183.2] | 354.3 [276.7, 432.0] |
| `M07:SC:B3:C1` | policy-aware (selfish), m = 1-4 | 51.75 | 928.7 (n=2) | 859.6 [807.2, 912.1] | 1224.4 [1184.4, 1264.5] | 1224.4 [1184.4, 1264.5] | 287.5 (n=2) |
| `M08:SC:B3:C2` | CSAV / present-day, m = 1 | 52.15 | 795.4 [752.1, 838.8] | 778.1 [727.7, 828.5] | 1345.5 [1302.3, 1388.6] | 1345.5 [1302.3, 1388.6] | 550.0 [520.8, 579.3] |
| `M08:SC:B3:C2|M09:SC:B3:C2` | CSCD = CSTC, m = 2 | 104.30 | 676.6 [580.0, 773.1] | 675.0 [576.4, 773.5] | 1168.7 [880.3, 1457.2] | 1123.7 [890.9, 1356.6] | 447.2 [301.6, 592.8] |
| `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2` | CSCD, m = 4 | 208.60 | 692.0 [586.3, 797.6] | - | 1091.1 [396.6, 1785.5] | 955.5 [554.2, 1356.9] | 263.6 [-33.0, 560.2] |
| `M03:SC:B3:C1|M08:SC:B4:C1` | present-day proxy, m = 2-4 | 103.95 | 723.1 [678.7, 767.6] | 684.6 [604.2, 764.9] | 1112.3 [571.6, 1653.0] | 1086.6 [819.1, 1354.1] | 363.5 [134.2, 592.7] |

Under the selfish follower the policy-aware choice M07 (V = 1224.4) is worse than every evaluated multi-site layout (e.g. the ILP-chosen bi-level layout, 1057.5, and CSCD m = 4, 955.5), i.e. the policy-aware search did not reach its own objective's better layouts within the wall budget. M07 is a low-demand cell (13 DOHMH restaurants; 9 at the node) that the rule-follower screen ranked first among all priced singletons (rule V 1224.4, ahead of M06:SC:B4:C2 1261.2 and M08:SC:B4:C2 1272.1).

## Table 7 -- Compliance sweep at the bi-level layout

A share alpha_c of the 8 riders follows the ILP plan (cached written-target schedule of each scenario; stations keep the planned inventory), the rest follow the r5_selfish rule; 3 random draws of the compliant set per scenario. V and served share: mean over draws within a scenario, then mean [95 % CI] over the 3 scenarios (n = 3; 9 runs per alpha_c). Gap closed = (V(0) - V(alpha_c)) / (V(0) - V(1)).

| alpha_c | V mean [95 % CI] | per-scenario V | served share | mean defected riders | gap closed % | check_ok runs |
|---|---|---|---|---|---|---|
| 0.00 | 1165.0 [762.9, 1567.1] | 1094.0, 1050.8, 1350.3 | 0.625 [0.625, 0.625] | 0.00 | 0.0 | 0/9 |
| 0.25 | 1081.1 [862.9, 1299.3] | 1005.7, 1059.9, 1177.5 | 0.722 [0.710, 0.734] | 0.56 | 18.2 | 0/9 |
| 0.50 | 998.6 [865.7, 1131.6] | 940.8, 1008.7, 1046.4 | 0.767 [0.725, 0.808] | 0.44 | 36.0 | 0/9 |
| 0.75 | 849.1 [640.8, 1057.4] | 790.2, 812.0, 945.1 | 0.817 [0.796, 0.837] | 0.00 | 68.4 | 0/9 |
| 1.00 | 703.1 [630.2, 776.0] | 701.6, 674.6, 733.2 | 0.858 [0.729, 0.988] | 0.00 | 100.0 | 9/9 |

Reference at the same layout: selfish equilibrium V = 1057.5 (served 0.758); rule r2 V = 1020.8 (served 0.750). check_ok is False for every mixed run only because of the report-only end-of-window recovery families (17) R_end and (18) rho, which the non-compliant riders do not honour.

## Appendix A -- Per-instance headline cells (layout x scenario)

| layout | scen. | relaxed ILP | st. | best rule | best_rule total | relaxed gap % | written ILP | st. (MIP gap %) | written best_rule | written gap % | PoR ILP (USD) | C_end_adj. relaxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bi-level | 0 | 662.15 | O | r5_range | 1004.44 | 34.08 | 701.56 | T (1.90) | 1004.44 | 30.15 | 39.41 | 2.12 |
| Bi-level | 1 | 642.12 | O | r2 | 889.09 | 27.78 | 674.58 | T (1.41) | 889.09 | 24.13 | 32.46 | 2.07 |
| Bi-level | 2 | 720.76 | O | r2 | 1084.90 | 33.56 | 733.20 | O (0.00) | 1084.90 | 32.42 | 12.44 | 1.95 |
| Policy-aware | 0 | 843.76 | O | r2 | 1240.96 | 32.01 | - | I | 1240.96 | - | - | 1.14 |
| Policy-aware | 1 | 851.56 | O | r2 | 1223.63 | 30.41 | 917.82 | O (0.00) | 1223.63 | 24.99 | 66.26 | 1.03 |
| Policy-aware | 2 | 883.62 | O | r2 | 1208.72 | 26.90 | 939.59 | O (0.00) | 1208.72 | 22.27 | 55.98 | 1.01 |
| CSAV m1 | 0 | 756.16 | O | r2 | 1344.74 | 43.77 | 782.03 | O (0.00) | 1344.74 | 41.85 | 25.87 | 1.12 |
| CSAV m1 | 1 | 781.85 | O | r2 | 1328.47 | 41.15 | 789.06 | O (0.00) | 1328.47 | 40.60 | 7.21 | 1.02 |
| CSAV m1 | 2 | 796.22 | O | r5_range | 1321.67 | 39.76 | 815.15 | O (0.00) | 1321.67 | 38.32 | 18.92 | 0.98 |
| CSCD m2 | 0 | 663.33 | O | r5_range | 1179.96 | 43.78 | 664.86 | O (0.00) | 1179.96 | 43.65 | 1.54 | 1.69 |
| CSCD m2 | 1 | 642.40 | O | r5_transfer | 1033.26 | 37.83 | 644.92 | O (0.00) | 1033.26 | 37.58 | 2.52 | 1.78 |
| CSCD m2 | 2 | 719.16 | O | r2 | 1234.28 | 41.73 | 719.96 | O (0.00) | 1234.28 | 41.67 | 0.80 | 1.78 |
| Present-day | 0 | 683.72 | T | r5_range | 1123.39 | 39.14 | 714.28 | T (1.41) | 1123.39 | 36.42 | 30.56 | 2.00 |
| Present-day | 1 | 652.66 | O | r2 | 865.72 | 24.61 | 711.38 | T (2.75) | 865.72 | 17.83 | 58.72 | 1.98 |
| Present-day | 2 | 717.34 | O | r5_transfer | 1093.01 | 34.37 | 743.71 | T (1.72) | 1093.01 | 31.96 | 26.37 | 1.99 |
| CSTC m3 | 0 | 657.02 | O | r5 | 1105.15 | 40.55 | 658.24 | O (0.00) | 1123.02 | 41.39 | 1.22 | 2.37 |
| CSTC m3 | 1 | 648.86 | O | r5_transfer | 792.96 | 18.17 | 650.19 | O (0.00) | 799.14 | 18.64 | 1.33 | 2.59 |
| CSTC m3 | 2 | 727.83 | O | r2 | 1247.82 | 41.67 | 728.77 | O (0.01) | 1247.82 | 41.60 | 0.93 | 2.10 |
| CSTC m4 | 0 | 668.20 | O | r5_range | 1035.25 | 35.45 | 668.96 | O (0.00) | 1035.25 | 35.38 | 0.75 | 2.68 |
| CSTC m4 | 1 | 661.22 | O | r5_transfer | 797.33 | 17.07 | 662.05 | O (0.00) | 824.86 | 19.74 | 0.83 | 2.70 |
| CSTC m4 | 2 | 740.08 | O | r5_range | 1151.40 | 35.72 | 740.64 | O (0.00) | 1151.40 | 35.68 | 0.56 | 2.35 |

## Appendix B -- Per-scenario V of every siting layout (written targets)

| layout | invest. (kUSD) | scen. | ILP total | ILP st. (MIP gap %) | ILP lower bound | rule r2 total | selfish total | served ILP / r2 / selfish |
|---|---|---|---|---|---|---|---|---|
| `M09:SC:B3:C2` | 52.15 | 0 | 765.21 | O | 765.21 | 1312.56 | 1312.56 | 0.725 / 0.575 / 0.575 |
| `M09:SC:B3:C2` | 52.15 | 1 | 801.23 | T (0.85) | 794.45 | 1304.22 | 1304.22 | 0.700 / 0.450 / 0.450 |
| `M09:SC:B3:C2` | 52.15 | 2 | 822.73 | O | 822.73 | 1512.52 | 1512.52 | 0.625 / 0.425 / 0.425 |
| `M08:SC:B3:C2` | 52.15 | 0 | 782.03 | O | 782.03 | 1344.74 | 1344.74 | 0.700 / 0.475 / 0.475 |
| `M08:SC:B3:C2` | 52.15 | 1 | 789.06 | O | 789.06 | 1328.47 | 1328.47 | 0.700 / 0.425 / 0.425 |
| `M08:SC:B3:C2` | 52.15 | 2 | 815.15 | O | 815.15 | 1363.16 | 1363.16 | 0.625 / 0.425 / 0.425 |
| `M07:SC:B3:C1` | 51.75 | 0 | - | I | - | 1240.96 | 1240.96 | - / 0.400 / 0.400 |
| `M07:SC:B3:C1` | 51.75 | 1 | 917.82 | O | 917.82 | 1223.63 | 1223.63 | 0.500 / 0.325 / 0.325 |
| `M07:SC:B3:C1` | 51.75 | 2 | 939.59 | O | 939.59 | 1208.72 | 1208.72 | 0.425 / 0.350 / 0.350 |
| `M08:SC:B3:C2|M09:SC:B3:C2` | 104.30 | 0 | 664.86 | O | 664.86 | 1237.24 | 1132.24 | 0.925 / 0.800 / 0.775 |
| `M08:SC:B3:C2|M09:SC:B3:C2` | 104.30 | 1 | 644.92 | O | 644.92 | 1034.66 | 1026.04 | 0.975 / 0.800 / 0.775 |
| `M08:SC:B3:C2|M09:SC:B3:C2` | 104.30 | 2 | 719.96 | O | 719.96 | 1234.28 | 1212.96 | 0.825 / 0.800 / 0.800 |
| `M08:SC:B3:C2|M14:SC:B3:C2` | 104.30 | 0 | 674.45 | O | 674.45 | 1398.79 | 1143.28 | 0.925 / 0.675 / 0.750 |
| `M08:SC:B3:C2|M14:SC:B3:C2` | 104.30 | 1 | 676.71 | O | 676.71 | 1390.95 | 1270.66 | 0.925 / 0.450 / 0.700 |
| `M08:SC:B3:C2|M14:SC:B3:C2` | 104.30 | 2 | 746.42 | O | 746.42 | 1448.37 | 1331.74 | 0.825 / 0.475 / 0.650 |
| `M03:SC:B3:C1|M08:SC:B4:C1` | 103.95 | 0 | 714.28 | T (1.41) | 704.18 | 1277.65 | 1092.82 | 0.850 / 0.800 / 0.800 |
| `M03:SC:B3:C1|M08:SC:B4:C1` | 103.95 | 1 | 711.38 | T (2.75) | 691.84 | 865.72 | 975.93 | 0.850 / 0.800 / 0.750 |
| `M03:SC:B3:C1|M08:SC:B4:C1` | 103.95 | 2 | 743.71 | T (1.72) | 730.93 | 1193.55 | 1191.00 | 0.775 / 0.775 / 0.775 |
| `M06:SC:B4:C2|M12:S:B3:C0` | 103.95 | 0 | 701.56 | T (1.90) | 688.22 | 1088.40 | 1088.40 | 0.875 / 0.725 / 0.725 |
| `M06:SC:B4:C2|M12:S:B3:C0` | 103.95 | 1 | 674.58 | T (1.41) | 665.05 | 889.09 | 999.05 | 0.900 / 0.725 / 0.750 |
| `M06:SC:B4:C2|M12:S:B3:C0` | 103.95 | 2 | 733.20 | O | 733.20 | 1084.90 | 1084.90 | 0.800 / 0.800 / 0.800 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2` | 156.45 | 0 | 660.46 | O | 660.46 | 1244.83 | 965.29 | 0.950 / 0.800 / 0.925 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2` | 156.45 | 1 | 651.61 | O | 651.61 | 797.04 | 797.79 | 0.975 / 0.925 / 0.925 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2` | 156.45 | 2 | 728.44 | O | 728.44 | 1233.54 | 1156.88 | 0.850 / 0.875 / 0.900 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2` | 156.45 | 0 | 658.24 | O | 658.24 | 1236.99 | 1051.41 | 0.950 / 0.825 / 0.850 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2` | 156.45 | 1 | 650.19 | O | 650.19 | 961.83 | 807.50 | 0.975 / 0.875 / 0.925 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2` | 156.45 | 2 | 728.77 | O | 728.77 | 1247.82 | 1162.44 | 0.850 / 0.800 / 0.875 |
| `M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2` | 156.45 | 0 | 668.91 | O | 668.91 | 1402.04 | 1162.59 | 0.950 / 0.725 / 0.825 |
| `M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2` | 156.45 | 1 | 662.29 | O | 662.29 | 1087.22 | 872.23 | 0.975 / 0.800 / 0.900 |
| `M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2` | 156.45 | 2 | 729.68 | O | 729.68 | 1164.08 | 1168.58 | 0.850 / 0.825 / 0.825 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2` | 208.60 | 0 | 671.49 | O | 671.49 | 1354.71 | 897.72 | 0.950 / 0.825 / 0.950 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2` | 208.60 | 1 | 663.55 | O | 663.55 | 797.95 | 830.85 | 0.975 / 0.950 / 0.900 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2` | 208.60 | 2 | 740.88 | O | 740.88 | 1120.52 | 1138.06 | 0.850 / 0.900 / 0.925 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2` | 208.60 | 0 | 668.96 | O | 668.96 | 1269.75 | 893.62 | 0.950 / 0.850 / 0.925 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2` | 208.60 | 1 | 662.05 | O | 662.05 | 938.66 | 820.44 | 1.000 / 0.900 / 0.925 |
| `M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2` | 208.60 | 2 | 740.64 | O | 740.64 | 1277.79 | 1169.45 | 0.850 / 0.825 / 0.925 |
| `M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2` | 208.60 | 0 | 673.93 | O | 673.93 | 1415.89 | 936.51 | 0.975 / 0.775 / 0.925 |
| `M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2` | 208.60 | 1 | 668.70 | O | 668.70 | 810.09 | 856.37 | 0.975 / 0.925 / 0.925 |
| `M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2` | 208.60 | 2 | 740.20 | O | 740.20 | 1072.65 | 1111.79 | 0.850 / 0.875 / 0.875 |

## Anomalies and caveats

* Bi-level search truncated: the sweep spent its 124.2-min budget on 4 priced layouts (+1 INFEASIBLE_ILP, 3 SKIPPED_BUDGET); `search_complete = False` at every budget. The result at m = 3 and m = 4 is just the m = 2 layout (103,950 USD of a 156,450 / 208,600 USD budget left unspent).
* No bi-level layout at m = 1: of the two screened singletons, M07:SC:B3:C1 (51,750 USD) is ILP-infeasible in scenario 0 and M06:SC:B4:C2 costs 52,600 USD, 450 USD over the m = 1 budget; the top-demand cell M08 was never screened (k_screen = 2 with the rule-follower screen).
* The bi-level layout is dominated under its own (ILP) follower: CSCD at m = 2 is cheaper in all three scenarios (paired gap -3.99 %), and CSCD / CSTC / CSAV are cheaper at m = 3 and m = 4 on average. On the relaxed control the bi-level and CSCD m = 2 layouts tie (675.01 vs 674.96). The written-target disadvantage comes from the swap-only site M12:S (no charger): its price of recovery is 28.1 USD vs 1.6 USD for CSCD m = 2.
* Policy-aware siting failed to search: 399 rule-follower screening evaluations consumed the 30.7-min budget (library build time 1,745 s); the returned layout M07 is worse under its own selfish follower (1224.4) than the ILP-chosen layout (1057.5).
* Selfish follower may be non-monotone in capacity, but this is not established: adding a spare at M06 raises the selfish-equilibrium V by +103.4 USD on average [-270.8, 477.6] (+264.6, -33.8, +79.6 by scenario), a charger at M06 by +47.7 [-204.1, 299.4] (+164.7, -8.8, -12.8), a second swap position at M06 by +57.8 (scenario 0 only: +173.3); a spare at M12 gives +7.3 [-150.4, 165.0] (2 of 3 scenarios negative). Every interval includes zero and the mean is driven by scenario 0, so a Braess-type effect (riders crowd the enlarged station) is a hypothesis, not a finding. Under the ILP follower an extra spare (M06 or M12) or charger (M06) lowers V in all three scenarios, also against the reference MIP lower bounds; a second swap position gives no gain distinguishable from the MIP gap (M06 -7.1 [-23.9, 9.7], +0.6 against the lower bounds; M12 +0.5).
* Lever ILP improvements are partly MIP-gap artefacts: the reference has two TIME_LIMIT incumbents, the spare / charger variants were solved to optimality. Against the reference lower bounds the improvements shrink from about -20 to about -10 to -13 USD but stay negative in every scenario; 'position @ M06' (-7.0 USD) is not distinguishable from the gap (+0.3 USD in scenario 0).
* M07 headline row: the script's summary uses n = 2 (written ILP infeasible in scenario 0); this report uses all three valid relaxed cells (n = 3).
* Compliance alpha_c = 0 (all riders selfish against the ILP station plan) costs 1165.0, more than the selfish equilibrium on free stations (1057.5): the planned inventory is wrong for non-compliant riders. Mean defected riders is non-monotone (0.56 at 0.25, 0.44 at 0.5, 0 at 0.75).
* Present-day layout is a proxy (DOHMH restaurant weights at candidate nodes; no present-day hub list in data/raw) capacity-matched to the bi-level layout; its ILP values are three TIME_LIMIT incumbents from the headline stage (baselines stage: SKIPPED_BUDGET).
* CSCD and CSTC give identical layouts at m = 1, 2; CSAV equals the present-day proxy at m = 1, so the per-budget comparison has fewer distinct layouts than methods.
* Very wide 95 % CIs: n = 3 scenarios with t = 4.303; the between-scenario spread of V (about 60-80 USD under the ILP, up to 550 USD under rule r2) is shared by all methods. Paired gaps (Tables 2, 5) are the meaningful comparisons.
* A coincidence checked and dismissed: the spare @ M12 lever total in scenario 0 (675.0124) equals the reference operating cost of that scenario; the two rows are distinct solves (different keys, totals with set-up 26.88 vs 26.548 USD).

## Interpretation

The coordination result carries over to the Manhattan-wide network: on the like-for-like relaxed control the ILP is 34.3 % cheaper than the best operating rule pooled over seven layouts, inside the round-3/4 range (29.6 % usd4h, 31.8 % nyc4h), and 31.8 % at the bi-level layout itself. The gap is largest (about 41 %) on the one- and two-hub layouts around the densest cell M08, where uncoordinated riders queue at one station, and smallest (29.4 %) on the four-site CSTC layout, where a rule rider already finds a nearby free station, and at the under-chargered single site M07 (29.8 %). Writing the recovery targets back in costs the ILP between 0.7 and 61 USD per window: about 1-2 USD on the multi-site layouts whose sites all have two chargers (CSCD m = 2, CSTC m = 3, 4), 17 USD at the single hub M08, and 28-61 USD where a site is swap-only (M12:S, bi-level) or has one charger (present-day proxy 38.6, M07 61.1), which is why the bi-level layout's written-target value (703.1) trails CSCD m = 2 (676.6) even though the two tie on the relaxed control. The siting stage therefore does not yet support a claim that bi-level optimisation beats rule siting: with k_screen = 2 and a 125-min wall budget the greedy priced four layouts, never screened the densest cell M08, found nothing at m = 1 and stopped at a two-site layout for m = 2-4. What the run does show is that the value of a layout depends on the follower: at m = 2 the bi-level layout is 12-14 % cheaper than any rule-sited layout under the rule r2 follower (significant), 2.6-10.6 % cheaper under the selfish follower (every scenario, but 5.69 % [-4.90, 16.28]; one comparator equilibrium did not converge), but 1.8-5.5 % dearer under the ILP with written targets; with relaxed targets it ties with CSCD m = 2 under the ILP. The marginal-lever table points the same way at the margin: a 450-USD spare or 400-USD charger saves 8-28 USD per window under the ILP in every scenario (still 8-15 USD against the reference MIP lower bounds), whereas under the selfish equilibrium the mean change is positive but not significant (CIs include zero, driven by scenario 0), so a capacity paradox under selfish riders is suggested but not shown. Shuttle and grid levers are inert under the selfish follower, and their ILP values were not obtained. Compliance pays off more than proportionally at high compliance (a concave curve): half of the riders following the plan removes 36 % of the 462-USD gap between no and full compliance, three quarters remove 68 %. On the scenario mean the mixed system drops below the selfish equilibrium on free stations (1057.5 USD) between alpha_c = 0.25 (1081.1) and 0.5 (998.6), at about 0.32 by linear interpolation, and below rule r2 (1020.8) at about 0.43; per scenario the crossing with the selfish equilibrium lies below 0.25 (scenario 0), between 0.25 and 0.5 (scenario 2) and between 0.5 and 0.75 (scenario 1), and scenario 1 is not monotone (1050.8 -> 1059.9 from alpha_c = 0 to 0.25). For the manuscript, the defensible X6 claims are the headline gap, the follower-dependence of layout rankings (under rule r2; directional under the selfish follower) and the compliance curve; the capacity paradox under selfish riders is only suggestive at n = 3; the 'bi-level beats rules' claim needs a complete search (larger k_screen and wall budget, M08 in the screen) before it can be made.

## Figures (`figs/`, vector PDF + 300-dpi PNG)

* `figs/fig_x6_map.pdf` / `.png` -- Manhattan south of 110th St (neighbourhood polygons, local km frame centred at 40.75 N, 74.00 W): the 15 lattice candidates (circle area proportional to DOHMH restaurants at the node, labels = candidate number), the six bridge/tunnel rider depots, and the sites chosen by each method at budgets m = 1-4 (markers offset from their site along a method-specific direction). Double column.
* `figs/fig_x6_V_vs_budget.pdf` / `.png` -- Expected cost V per 4-h window against budget for each siting method under (a) the ILP follower, (b) the rule r2 follower and (c) the selfish-equilibrium follower (written targets; mean over three demand scenarios, error bars 95 % t-intervals that mostly reflect demand variation common to all methods). The bi-level layout is the same at m = 2-4; no bi-level layout was found at m = 1; the policy-aware layout is omitted from (a) because its ILP is infeasible in one scenario. Double column.
* `figs/fig_x6_compliance.pdf` / `.png` -- Compliance sweep at the bi-level layout: (a) V and (b) served share against the share alpha_c of riders following the ILP plan (mean over three scenarios with 95 % t-band; grey dots = scenario means over three draws). Dashed: selfish equilibrium; dotted: rule r2 on the same layout. Single column.
* `figs/fig_x6_headline_gaps.pdf` / `.png` -- Cost gap of the ILP against the best operating rule per compared layout, on the relaxed control (filled) and with the written recovery targets (open); mean and 95 % t-interval over three scenarios, grey dots = scenarios; dashed line: round-3/4 nyc4h mean 31.8 %. Single column.
* `figs/fig_x6_levers.pdf` / `.png` -- Marginal levers at the bi-level layout: change in V from one extra spare battery, charger or swap position (or one more shuttle / 10 % more grid power) under the ILP follower (blue) and the selfish follower (vermillion); bars = mean, dots = scenarios. Shuttle and grid were not priced under the ILP. Single column.

## Digest corrections (2026-10-18)

Applied after the two-refuter verification pass; numbers recomputed from the records (no solves). Items marked "one verifier" are qualifiers added where only one verifier objected.

- C3 (follower-dependent ranking): both verifiers refuted the unqualified version. The ILP ranking holds only with written targets (relaxed: tie with CSCD m = 2); the selfish-follower advantage is 5.69 [-4.90, 16.28] % and one comparator equilibrium (CSCD m = 2, scenario 2) did not converge.
- C4 (capacity paradox): both verifiers refuted 'extra capacity always helps the ILP but hurts the selfish equilibrium'. All selfish lever CIs include zero (spare M06 +103.4 [-270.8, 477.6], driven by scenario 0); a second swap position gives no ILP gain beyond the MIP gap. Summary, anomaly and Interpretation rewritten.
- C5 (compliance): both verifiers refuted 'slightly convex' and 'at least half must comply'. The mean curve is concave; it crosses the selfish equilibrium between alpha_c = 0.25 and 0.5 (about 0.32) and rule r2 at about 0.43; scenario 1 is not monotone. Summary and Interpretation rewritten.
- Coverage: the earlier text said all 84 selfish equilibria converged; 2 unique evaluations (CSCD m = 2 scenario 2; CSAV m = 3 scenario 1) stopped at the 10-iteration cap with `converged = False`.
