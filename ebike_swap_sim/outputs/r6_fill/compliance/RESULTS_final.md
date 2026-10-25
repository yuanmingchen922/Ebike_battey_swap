# R6 compliance -- final report: compliance sweep, selfish equilibrium and rule r2 on Manhattan at the calibrated prices (P 60 USD, w 18 USD/h, v 15 USD/h)

Source: `outputs/r6_fill/compliance/` (driver `experiments/r6_fill.py --stage compliance`, run on the AWS server, finished 2026-10-20 14:52:40 server clock after 255.3 s). Every number below is recomputed from `records.jsonl` (113 rows) and `cache/index.jsonl` (21 rows) by `figs/compliance_final.py` (no solver call; output `figs/compliance_numbers.json`, per-run table `figs/compliance_cells.csv`). The legacy-price counterpart is recomputed by the same script from `outputs/r5_x6_manhattan/compliance/records.jsonl` (45 runs) and the reference rows of `outputs/r5_x6_manhattan/cache/index.jsonl`; it reproduces the legacy report exactly (V 1165.0 / 1081.1 / 998.6 / 849.1 / 703.1, gap closed 18.2 / 36.0 / 68.4 %, crossings 0.32 / 0.43, price of decentralisation 354.3 [276.7, 432.0]).

Instance: family `r5_manhattan` (15 candidates south of 110th St, 8 bikes, 40 orders, 16:00-20:00, 48 slots), three demand scenarios (seeds 0-2, p = 1/3), written end-of-window targets, aggregated ILP (Gurobi Threads 3, Seed 0, TimeLimit 300 s). V = allocated set-up cost + mean scenario operating cost, USD per 4-h window. Two layouts:

* **Sites 04 + 09** (`M04:SC:B2:C2|M09:SC:B4:C2`, 104,300 USD): best written-target two-site layout of the certified siting pass `outputs/r6_o2/manhattan_pass2` (UB 699.96 = this run's ILP value, all three scenarios OPTIMAL; certified lower bound 676.24; gap 3.39 %).
* **Sites 06 + 12** (`M06:SC:B4:C2|M12:S:B3:C0`, 103,950 USD): the round-5 bi-level layout (the "bi-level layout" of the current manuscript), which is also the layout of the legacy-price compliance sweep.

Compliance: a share psi of the 8 riders follows the cached ILP plan of its scenario, the station layer replays the plan (`station_plan = plan`), the other riders follow the M4 logit rule. Draw d selects `random.Random(d).sample(range(8), round(8 psi))`, so for a given draw the compliant sets are nested in psi (2, 4, 6 riders) and identical across scenarios and layouts; layout comparisons are therefore paired run by run.

**Confidence intervals.** Exact Student-t 95 %, t_{0.975,2} = 4.303, in two versions: **over scenarios** (n = 3; each scenario's value is the mean of its three draws; same convention as the manuscript and the legacy report, used in the figures and the headline) and **over draws** (n = 3; each draw's value is the mean over the three scenarios of the same compliant set; the convention of the server's `RESULTS.md`). The over-draws interval conditions on the three demand scenarios and measures only which riders comply; it is zero at psi = 0 and psi = 1, where all draws coincide. Differences against the followers and between layouts are paired per scenario.

## Problems (read first)

1. **The 04 + 09 layout is the best layout found, not a certified optimum.** The siting pass stopped on its wall budget with gap 3.39 % (3,140 two-site layouts still open), so `o2_certified = False` in every row. PENDING_R6 item 4 asked for "the certified Manhattan layout"; what can be said is "the best written-target two-site layout found, within 3.39 % of a certified lower bound (676.24 USD)".
2. **The 06 + 12 ILP values are time-limited incumbents** (MIP gaps 6.44, 8.49 and 2.88 %; lower bounds 726.02, 700.36, 840.99, mean 755.79). Its psi = 1 point (802.4) is an upper bound on its coordinated cost, its price of decentralisation (446.4) a lower bound (up to 493.1 [202.3, 783.9] against the MIP bounds), and its mixed runs follow these incumbent plans. The layout ranking under the ILP survives the bounds (row 2 of Table 6).
3. **psi = 0 is not the selfish equilibrium.** At psi = 0 the stations still replay the ILP plan's charging and loads, and the riders run the M4 logit rule once with myopic wait estimates (`bilevel.compliance_sweep` -> `baseline.simulate_compliance`; no successive-averages iteration). It costs more than the selfish equilibrium on free stations in every scenario (04 + 09: +170.5, +448.9, +348.2 USD; 06 + 12: +144.8, +88.8, +444.6 USD; means +322.6 [-27.6, 672.7] and +226.1 [-249.2, 701.3]). The crossing with the selfish equilibrium therefore compares mixed systems on a planned station layer with fully decentralised operation on free stations. The legacy sweep had the same design (+107.6 USD).
4. **Mixed runs do not honour the written end-of-window targets, and at 04 + 09 often lack a terminal certificate.** Report-only check families: (17) R_end and (18) rho in most mixed runs of both layouts, and (9) (rider path ends without a terminal certificate at an open swap site) in 14 of the 27 mixed runs at 04 + 09 (5, 6, 3 at psi 0.25, 0.5, 0.75) and 1 of 27 at 06 + 12. Runs passing all checks: 04 + 09 6/9, 2/9, 2/9, 3/9, 9/9 at psi = 0 ... 1; 06 + 12 0/9 at every psi < 1, 9/9 at psi = 1. The rule r2 and selfish reference runs also violate (17)/(18) (and (9) in 2 of the 6 runs at 04 + 09, 1 of 6 at 06 + 12). The ILP pays for the targets and the other runs do not, which favours partial compliance and the decentralised followers, as already stated in the manuscript for the legacy sweep. No hard family is violated in any run.
5. **Small samples.** n = 3 scenarios and n = 3 draws; the over-scenario intervals of V are 300-850 USD wide and mostly reflect demand variation common to all followers. Paired differences are the meaningful comparisons; even these include zero for every layout comparison except under the ILP.
6. **Selfish equilibrium = rule r2 on 06 + 12 in scenarios 0 and 2.** The cached schedules are identical (all of x, u, c, h, z), as they were at the legacy prices (1088.40 and 1084.90 USD there). The two references therefore almost coincide on this layout (selfish minus r2 = 10.3 [-34.1, 54.7]; 20.1 [-35.2, 75.4] on 04 + 09).
7. **One equilibrium reached the iteration cap.** 06 + 12 scenario 0 stopped at iteration 10 = cap, but with `converged = True` and zero share change; the other five converged in 2-6 iterations.
8. **Not every path is monotone.** On 04 + 09 scenario 0 the draw-mean V rises from psi = 0 to 0.25 (1311.5 -> 1357.4); 3 of the 36 draw-by-scenario steps rise on each layout (largest +121 USD, 06 + 12 scenario 1 draw 1 from 0 to 0.25). The per-draw mean curves are monotone on both layouts.
9. **Cache reuse.** No ILP was solved in this run (`n_solves = 0` for every ILP row; 15 cache rows seeded from the siting-pass cache, hence 255 s instead of the expected 75 min). The 04 + 09 rule r2 and selfish values are also siting-pass cache rows; the six 06 + 12 policy runs were computed here. Values agree with the siting pass (UB 699.957; 06 + 12 written value 802.43 in its Table 2), demand md5s agree with the plan row, all rows carry P 60 / w 18 / v 15. The earlier NO_PLAN attempt is not in this folder; all 90 compliance runs are `OK`.
10. **The server `RESULTS.md` says "Anomalies: none"** and its "share_of_selfish_gap_recovered" is (V_selfish - V) / (V_selfish - V_ILP), not the no-to-full share asked for; both are reported below.

## Coverage

| item | value |
|---|---|
| records | 113: 1 plan, 6 layout prices (2 layouts x ILP / rule r2 / selfish), 6 policy solves (06 + 12), 90 compliance runs, 10 compliance summaries |
| compliance runs | 2 layouts x 5 psi x 3 scenarios x 3 draws = 90, all `OK`, `station_plan = plan`, all summaries `complete` |
| psi = 1 | reproduces the ILP total in all 18 runs (difference < 1e-6 USD) |
| psi = 0 | identical across the three draws (no randomness), as designed |
| ILP status | 04 + 09: OPTIMAL x 3 (gap 0); 06 + 12: TIME_LIMIT x 3 (6.44 / 8.49 / 2.88 %) |
| selfish equilibria | 6, all converged (MSA, tol 0.01, cap 10): 2, 5, 4 iterations (04 + 09), 10, 6, 3 (06 + 12) |
| defections (compliant rider turned policy rider because a planned swap could not be honoured) | 04 + 09: 0.56 / 1.00 / 0.56 per run at psi 0.25 / 0.5 / 0.75 (in 5, 6, 5 of 9 runs); 06 + 12: 0 / 0.11 / 0.11 (0, 1, 1 of 9) |
| planned swaps executed | 04 + 09: 2.3 / 5.0 / 8.0 of 11; 06 + 12: 1.9 / 3.7 / 5.8 of 8 |
| legacy counterpart | 45 runs (06 + 12, P 30 / v 36), recomputed with the same code |

## Answer

### Summary

* **Curve.** At the calibrated prices compliance lowers V at every step on average on both layouts. On 04 + 09 V falls from 1491.1 USD (psi = 0) to 1307.2, 1100.1, 902.2 and 700.0 USD; on 06 + 12 from 1474.9 to 1251.3, 1050.4, 937.1 and 802.4 USD. Served share rises from 0.667 to 0.983 (04 + 09) and 0.650 to 0.958 (06 + 12).
* **Shape.** On 04 + 09 the curve is linear: psi = 0.25, 0.5 and 0.75 close 23.2, 49.4 and 74.4 % of the 791.2-USD difference between no and full compliance; the deviation from the chord at psi = 0.5 is +4.6 USD [-359.6, 368.8]. On 06 + 12 it is convex (benefit front-loaded): 33.3, 63.1 and 80.0 % of 672.5 USD, with chord deviations -55.5 [-102.5, -8.5] at psi = 0.25 and -88.3 [-155.5, -21.1] at psi = 0.5. The legacy shape (concave, "savings accelerate", 18.2 / 36.0 / 68.4 %) does not carry over; it was not significant at the legacy prices either (chord deviation +64.6 [-117.0, 246.1]).
* **Crossings.** The mean curve drops below the selfish equilibrium at psi = 0.42 and below rule r2 at 0.44 on 04 + 09 (per scenario 0.30-0.53 and 0.35-0.53), and at 0.25 and 0.27 on 06 + 12 (per scenario 0.12-0.45 and 0.14-0.45); legacy 0.32 and 0.43. The mixed system is significantly cheaper than the selfish equilibrium (paired CI over scenarios) from psi = 0.75 on 04 + 09 (-266.4 [-335.0, -197.8]) and only at psi = 1 on 06 + 12.
* **Price of decentralisation** (selfish minus ILP): 468.6 USD [380.0, 557.3] on 04 + 09 (40.1 % of the selfish cost) and 446.4 [191.9, 701.0] on 06 + 12 (35.7 %; up to 493.1 against the MIP bounds), against 354.3 [276.7, 432.0] (33.5 %) at the legacy prices.
* **Layout ranking.** 04 + 09 is cheaper under the ILP by 102.5 USD [37.2, 167.7] in all three scenarios, and still by 55.8 [25.6, 86.1] against the MIP lower bounds of 06 + 12. The mean order is the same under rule r2 (-90.1 [-381.7, 201.5]) and the selfish equilibrium (-80.3 [-440.5, 279.9]), but both intervals include zero and scenario 2 reverses it. Under partial compliance at psi <= 0.5 the mean order reverses (06 + 12 cheaper by 16.2, 55.9 and 49.8 USD; not significant) and returns at psi = 0.75 (-34.9 [-162.0, 92.2]). Only the ranking under the coordinated follower is established.
* **What drives the curve.** Within a scenario, every extra served order lowers the run cost by 61.0 USD (04 + 09; R^2 0.97 over 45 runs) and 53.5 USD (06 + 12; R^2 0.96), close to the 60-USD unserved-order price; at the legacy prices the same fit gives 41.1 USD (R^2 0.66). The extra served orders per psi step are flat on 04 + 09 (3.4, 2.8, 3.0, 3.4) and front-loaded on 06 + 12 (4.3, 3.1, 2.7, 2.2), matching the two shapes.

### Table 1 -- Layout values under the three followers (written targets)

| layout | follower | V mean [95 % CI over scenarios] | per scenario | served share [95 % CI] | solve status |
|---|---|---|---|---|---|
| 04 + 09 | Coordinated ILP | 699.96 [509.64, 890.28] | 683.06, 633.20, 783.61 | 0.983 [0.947, 1.019] | OPTIMAL x 3 |
| 04 + 09 | Rule r2 | 1148.45 [905.21, 1391.69] | 1142.59, 1053.59, 1249.17 | 0.825 [0.763, 0.887] | policy |
| 04 + 09 | Selfish equilibrium M4 | 1168.58 [889.76, 1447.41] | 1140.98, 1072.72, 1292.05 | 0.808 [0.737, 0.880] | MSA 2, 5, 4 iterations, converged |
| 06 + 12 | Coordinated ILP | 802.43 [665.24, 939.61] | 776.01, 765.37, 865.90 | 0.958 [0.922, 0.994] | TIME_LIMIT x 3 (6.44, 8.49, 2.88 %) |
| 06 + 12 | ILP MIP lower bound | 755.79 [569.74, 941.84] | 726.02, 700.36, 840.99 | - | bound |
| 06 + 12 | Rule r2 | 1238.55 [1061.26, 1415.84] | 1320.40, 1189.34, 1205.90 | 0.750 [0.642, 0.858] | policy |
| 06 + 12 | Selfish equilibrium M4 | 1248.87 [1093.95, 1403.79] | 1320.40, 1220.30, 1205.90 | 0.758 [0.663, 0.853] | MSA 10, 6, 3 iterations, converged |

Relative to the ILP, rule r2 and the selfish equilibrium cost 64.1 % and 67.0 % more on 04 + 09 and 54.4 % and 55.6 % more on 06 + 12 (legacy, 06 + 12: 45.2 % and 50.4 %).

### Table 2 -- Compliance curve, sites 04 + 09

| psi | riders following the plan | V mean | 95 % CI over scenarios | 95 % CI over draws | per scenario (mean of 3 draws) | served share | 95 % CI over scenarios | 95 % CI over draws | defections per run | runs passing all checks |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 | 0 of 8 | 1491.1 | [1077.6, 1904.7] | 0 (identical draws) | 1311.5, 1521.6, 1640.3 | 0.667 | [0.432, 0.902] | 0 | 0.00 | 6/9 |
| 0.25 | 2 of 8 | 1307.2 | [1148.9, 1465.5] | [1155.4, 1459.0] | 1357.4, 1235.5, 1328.7 | 0.753 | [0.690, 0.816] | [0.686, 0.819] | 0.56 | 2/9 |
| 0.50 | 4 of 8 | 1100.1 | [877.4, 1322.9] | [969.4, 1230.9] | 1171.1, 999.4, 1129.9 | 0.822 | [0.756, 0.889] | [0.779, 0.865] | 1.00 | 2/9 |
| 0.75 | 6 of 8 | 902.2 | [671.6, 1132.8] | [779.6, 1024.8] | 899.8, 810.6, 996.2 | 0.897 | [0.834, 0.960] | [0.831, 0.964] | 0.56 | 3/9 |
| 1.00 | 8 of 8 | 700.0 | [509.6, 890.3] | 0 (identical draws) | 683.1, 633.2, 783.6 | 0.983 | [0.947, 1.019] | 0 | 0.00 | 9/9 |

### Table 3 -- Shape and position against the followers, sites 04 + 09

Gap closed = (V(0) - V(psi)) / (V(0) - V(1)); "mean curve" uses the scenario-mean V (ratio of means; equals the mean over draws because the endpoints do not vary over draws); the per-scenario column is the mean of the three per-scenario ratios with its CI. Chord deviation = V(psi) - [(1 - psi) V(0) + psi V(1)] per scenario (> 0 concave, savings accelerate; < 0 convex, savings front-loaded). Selfish-gap recovered = (V_selfish - V) / (V_selfish - V_ILP) (the server metric).

| psi | gap closed (mean curve) | per scenario [CI over scenarios] | CI over draws | chord deviation USD [CI over scenarios] | V minus selfish eq. USD [CI] | V minus rule r2 USD [CI] | selfish gap recovered |
|---|---|---|---|---|---|---|---|
| 0.00 | 0.0 % | 0.0 | - | 0 (endpoint) | +322.6 [-27.6, 672.7] | +342.7 [-43.1, 728.5] | -68.8 % |
| 0.25 | 23.2 % | 20.4 [-39.4, 80.3] | [4.1, 42.4] | +13.8 [-395.1, 422.8] | +138.6 [-90.6, 367.8] | +158.7 [-16.4, 333.9] | -29.6 % |
| 0.50 | 49.4 % | 46.9 [-6.0, 99.8] | [32.9, 66.0] | +4.6 [-359.6, 368.8] | -68.5 [-307.6, 170.7] | -48.3 [-232.4, 135.7] | 14.6 % |
| 0.75 | 74.4 % | 73.6 [55.2, 92.0] | [58.9, 89.9] | +4.4 [-125.9, 134.8] | -266.4 [-335.0, -197.8] | -246.3 [-260.8, -231.7] | 56.8 % |
| 1.00 | 100.0 % | 100.0 | - | 0 (endpoint) | -468.6 [-557.3, -380.0] | -448.5 [-509.4, -387.6] | 100.0 % |

Drop of the mean curve per step of 0.25: 184.0, 207.1, 197.9, 202.2 USD (constant within 12 %).

### Table 4 -- Compliance curve, sites 06 + 12

| psi | riders following the plan | V mean | 95 % CI over scenarios | 95 % CI over draws | per scenario (mean of 3 draws) | served share | 95 % CI over scenarios | 95 % CI over draws | defections per run | runs passing all checks |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 | 0 of 8 | 1474.9 | [1050.3, 1899.5] | 0 (identical draws) | 1465.2, 1309.1, 1650.5 | 0.650 | [0.542, 0.758] | 0 | 0.00 | 0/9 |
| 0.25 | 2 of 8 | 1251.3 | [895.2, 1607.4] | [946.9, 1555.6] | 1215.5, 1129.2, 1409.1 | 0.758 | [0.609, 0.908] | [0.643, 0.874] | 0.00 | 0/9 |
| 0.50 | 4 of 8 | 1050.4 | [775.2, 1325.5] | [965.5, 1135.2] | 1063.5, 933.6, 1154.0 | 0.836 | [0.734, 0.938] | [0.763, 0.909] | 0.11 | 0/9 |
| 0.75 | 6 of 8 | 937.1 | [715.2, 1159.0] | [823.6, 1050.6] | 879.7, 891.5, 1040.0 | 0.903 | [0.824, 0.981] | [0.819, 0.986] | 0.11 | 0/9 |
| 1.00 | 8 of 8 | 802.4 | [665.2, 939.6] | 0 (identical draws) | 776.0, 765.4, 865.9 | 0.958 | [0.922, 0.994] | 0 | 0.00 | 9/9 |

### Table 5 -- Shape and position against the followers, sites 06 + 12

| psi | gap closed (mean curve) | per scenario [CI over scenarios] | CI over draws | chord deviation USD [CI over scenarios] | V minus selfish eq. USD [CI] | V minus rule r2 USD [CI] | selfish gap recovered |
|---|---|---|---|---|---|---|---|
| 0.00 | 0.0 % | 0.0 | - | 0 (endpoint) | +226.1 [-249.2, 701.3] | +236.4 [-212.6, 685.4] | -50.6 % |
| 0.25 | 33.3 % | 33.4 [26.6, 40.2] | [-12.0, 78.5] | -55.5 [-102.5, -8.5] | +2.4 [-429.9, 434.7] | +12.7 [-400.8, 426.2] | -0.5 % |
| 0.50 | 63.1 % | 63.5 [50.1, 76.9] | [50.5, 75.7] | -88.3 [-155.5, -21.1] | -198.5 [-516.0, 119.0] | -188.2 [-481.3, 104.9] | 44.5 % |
| 0.75 | 80.0 % | 79.9 [68.8, 90.9] | [63.1, 96.9] | -33.5 [-110.6, 43.7] | -311.8 [-655.1, 31.5] | -301.5 [-642.9, 40.0] | 69.8 % |
| 1.00 | 100.0 % | 100.0 | - | 0 (endpoint) | -446.4 [-701.0, -191.9] | -436.1 [-691.3, -180.9] | 100.0 % |

Drop per step: 223.7, 200.9, 113.3, 134.7 USD. Chord deviation at psi = 0.5 over draws: -88.3 [-173.1, -3.5]. Per-scenario chord deviations at psi = 0.5: -57.1, -103.6, -104.2 (all three below the chord).

### Crossing points (linear interpolation, first crossing from above; every curve crosses each reference once)

| layout | reference | mean curve | per scenario (own reference) | per draw (nested compliant sets) | served share reaches the reference at |
|---|---|---|---|---|---|
| 04 + 09 | selfish equilibrium (1168.6) | 0.42 | 0.53, 0.42, 0.30 | 0.42, 0.47, 0.40 | 0.45 |
| 04 + 09 | rule r2 (1148.5) | 0.44 | 0.53, 0.44, 0.35 | 0.43, 0.51, 0.42 | 0.51 |
| 06 + 12 | selfish equilibrium (1248.9) | 0.25 | 0.14, 0.12, 0.45 | 0.27, 0.33, 0.16 | 0.25 |
| 06 + 12 | rule r2 (1238.5) | 0.27 | 0.14, 0.17, 0.45 | 0.28, 0.34, 0.17 | 0.23 |
| legacy 06 + 12 | selfish equilibrium (1057.5) | 0.32 | 0.02, 0.51, 0.43 | - | - |
| legacy 06 + 12 | rule r2 (1020.8) | 0.43 | 0.02, 0.65, 0.43 | - | - |

Significance of the position against the selfish equilibrium: over scenarios (paired), 04 + 09 is significantly below from psi = 0.75 and 06 + 12 only at psi = 1; over draws (conditioning on the three scenarios), 04 + 09 is below from psi = 0.75 ([779.6, 1024.8] < 1168.6) and 06 + 12 from psi = 0.5 ([965.5, 1135.2] < 1248.9). At psi = 0 both layouts are above the selfish equilibrium in every scenario.

### Price of decentralisation (selfish equilibrium minus coordinated ILP, paired over scenarios)

| layout | mean [95 % CI] | per scenario | % of the selfish V | rule r2 minus ILP |
|---|---|---|---|---|
| 04 + 09 | 468.6 [380.0, 557.3] | 457.9, 439.5, 508.4 | 40.1 % | 448.5 [387.6, 509.4] |
| 06 + 12 (incumbents) | 446.4 [191.9, 701.0] | 544.4, 454.9, 340.0 | 35.7 % | 436.1 [180.9, 691.3] |
| 06 + 12 against the MIP lower bounds | 493.1 [202.3, 783.9] | - | - | - |
| legacy 06 + 12 (P 30 / v 36) | 354.3 [276.7, 432.0] | 386.8, 324.5, 351.7 | 33.5 % | 317.7 |

### Table 6 -- Does the layout ranking depend on the follower? V(04 + 09) - V(06 + 12)

Negative = 04 + 09 cheaper. Mixed rows are paired run by run (same compliant riders, same scenario).

| follower | V(04 + 09) | V(06 + 12) | difference [95 % CI over scenarios] | per scenario | 95 % CI over draws | 04 + 09 cheaper in |
|---|---|---|---|---|---|---|
| Coordinated ILP | 700.0 | 802.4 | -102.5 [-167.7, -37.2] | -92.9, -132.2, -82.3 | - | 3/3 scenarios |
| ILP, 04 + 09 optimum vs. MIP lower bound of 06 + 12 | 700.0 | 755.8 | -55.8 [-86.1, -25.6] | -43.0, -67.2, -57.4 | - | 3/3 scenarios |
| Rule r2 | 1148.5 | 1238.5 | -90.1 [-381.7, 201.5] | -177.8, -135.7, +43.3 | - | 2/3 scenarios |
| Selfish equilibrium M4 | 1168.6 | 1248.9 | -80.3 [-440.5, 279.9] | -179.4, -147.6, +86.1 | - | 2/3 scenarios |
| Mixed, psi = 0 | 1491.1 | 1474.9 | +16.2 [-442.2, 474.7] | -153.7, +212.6, -10.2 | 0 (identical draws) | 6/9 runs |
| Mixed, psi = 0.25 | 1307.2 | 1251.3 | +55.9 [-240.6, 352.5] | +141.8, +106.3, -80.4 | [-372.1, 484.0] | 3/9 runs |
| Mixed, psi = 0.5 | 1100.1 | 1050.4 | +49.8 [-117.4, 216.9] | +107.6, +65.8, -24.1 | [-153.3, 252.8] | 5/9 runs |
| Mixed, psi = 0.75 | 902.2 | 937.1 | -34.9 [-162.0, 92.2] | +20.1, -81.0, -43.8 | [-145.3, 75.5] | 7/9 runs |

Answer: the ranking is established only under the coordinated follower (12.8 % cheaper; 7.4 % against the bounds). Under the three uncoordinated or partly coordinated followers the sign of the mean difference depends on the follower (04 + 09 cheaper under r2, the selfish equilibrium and psi = 0.75; 06 + 12 cheaper at psi = 0-0.5), but no such difference is distinguishable from zero, and the per-scenario order is mixed in every one of these rows.

## Comparison with the legacy prices (same layout 06 + 12, plus the new layout)

| quantity | 06 + 12, legacy (P 30 / v 36) | 06 + 12, calibrated | 04 + 09, calibrated |
|---|---|---|---|
| V at psi = 0 / 0.25 / 0.5 / 0.75 / 1 | 1165.0 / 1081.1 / 998.6 / 849.1 / 703.1 | 1474.9 / 1251.3 / 1050.4 / 937.1 / 802.4 | 1491.1 / 1307.2 / 1100.1 / 902.2 / 700.0 |
| no-to-full difference V(0) - V(1) | 461.9 | 672.5 | 791.2 |
| gap closed at psi = 0.25 / 0.5 / 0.75 (mean curve) | 18.2 / 36.0 / 68.4 % | 33.3 / 63.1 / 80.0 % | 23.2 / 49.4 / 74.4 % |
| chord deviation at psi = 0.25 / 0.5 / 0.75 (USD, CI over scenarios) | +31.5 [-126.6, 189.6] / +64.6 [-117.0, 246.1] / +30.5 [-57.3, 118.3] | -55.5 [-102.5, -8.5] / -88.3 [-155.5, -21.1] / -33.5 [-110.6, 43.7] | +13.8 / +4.6 / +4.4 (all CIs include 0) |
| shape | concave on the mean curve, not significant | convex, significant at 0.25 and 0.5 | linear |
| drop per 0.25 step (USD) | 84.0, 82.4, 149.5, 146.0 | 223.7, 200.9, 113.3, 134.7 | 184.0, 207.1, 197.9, 202.2 |
| extra served orders per 0.25 step | 3.9, 1.8, 2.0, 1.7 | 4.3, 3.1, 2.7, 2.2 | 3.4, 2.8, 3.0, 3.4 |
| cost change per extra served order, within scenario (R^2) | -41.1 USD (0.66) | -53.5 USD (0.96) | -61.0 USD (0.97) |
| selfish equilibrium / rule r2 V | 1057.5 / 1020.8 | 1248.9 / 1238.5 | 1168.6 / 1148.5 |
| crossing with selfish equilibrium / rule r2 (mean curve) | 0.32 / 0.43 | 0.25 / 0.27 | 0.42 / 0.44 |
| price of decentralisation | 354.3 [276.7, 432.0] (33.5 %) | 446.4 [191.9, 701.0] (35.7 %) | 468.6 [380.0, 557.3] (40.1 %) |
| psi = 0 minus selfish equilibrium | +107.6 [-236.7, 451.8] | +226.1 [-249.2, 701.3] | +322.6 [-27.6, 672.7] |
| served share psi = 0 / psi = 1 | 0.625 / 0.858 | 0.650 / 0.958 | 0.667 / 0.983 |
| served share selfish / r2 | 0.758 / 0.750 | 0.758 / 0.750 | 0.808 / 0.825 |

USD amounts are not comparable across the two price regimes (the unserved-order price doubled and the lateness price fell from 36 to 15 USD/h); shares, crossing points and percentages are.

## Interpretation

**Shown by these records.**
* At the calibrated prices partial compliance lowers the expected cost on average at every step on both layouts, and full compliance reproduces the ILP value exactly.
* The benefit of compliance is not back-loaded. On the best two-site layout found it is proportional to the share of compliant riders (half compliance closes 49.4 % of the gap, 95 % CI over draws 32.9-66.0 %); on the earlier bi-level layout it is front-loaded (63.1 % at half compliance; all three scenarios lie below the chord at psi = 0.5, CI of the deviation -155.5 to -21.1 USD). The manuscript's legacy statement that savings accelerate with compliance, and that half compliance closes about a third of the gain, does not hold at the calibrated prices; at the legacy prices that statement rested on the mean curve only (its chord deviations all include zero).
* The coordinated plan with stations run to plan is worse than free station choice when nobody complies, in every scenario on both layouts, and becomes cheaper than the selfish equilibrium on the mean curve at psi of about 0.42 (04 + 09) or 0.25 (06 + 12). With n = 3 the crossing is only located to the interval 0.12-0.53 across scenarios; statistically clear savings against the selfish equilibrium appear from psi = 0.75 (04 + 09) over scenarios.
* The price of decentralisation is 468.6 USD per window on the best layout found (40.1 % of the selfish cost) and at least 446.4 USD on the earlier layout, larger in relative terms than at the legacy prices (33.5 %).
* Under the coordinated follower the new layout is cheaper than the earlier bi-level layout in every scenario, even against the earlier layout's MIP lower bounds. Under rule r2, the selfish equilibrium and partial compliance, the two layouts cannot be told apart.
* At the calibrated prices the cost differences along the compliance curve are almost entirely served orders: within a scenario, V falls by 53-61 USD per additional served order (R^2 0.96-0.97), close to the 60-USD unserved-order price.

**Suggested, not shown.**
* The change of shape is plausibly a price effect: with the unserved-order price doubled and lateness cheaper, V tracks the served-order count, whose gains per compliant rider are flat (04 + 09) or front-loaded (06 + 12); at the legacy prices other cost components (lateness at 36 USD/h) decoupled V from served orders (R^2 0.66) and the cost gains arrived late. The records hold only run totals and served shares, so the component decomposition of the mixed runs is not available.
* The earlier crossing on 06 + 12 may reflect its swap-only site 12 (no charger), where the first riders who follow the plan prevent the stock-outs that free choice causes; the more frequent defections on 04 + 09 (planned swaps that the live stock cannot honour; 0.56-1.00 per run, against 0-0.11 on 06 + 12), where site 04 holds only two spares, may be why its first compliant riders gain less. Neither mechanism was tested.
* The reversal of the mean layout order at psi <= 0.5 hints that a layout chosen for a coordinated follower loses its advantage when compliance is low, which would support siting under a behavioural follower; with n = 3 and every interval including zero this remains a hypothesis.
* Because the mixed and policy runs ignore the written end-of-window targets (problem 4), the true mixed costs are somewhat higher than reported, which would move the crossings to the right; the size of this bias is not measured here.

## Figures (`figs/`, vector PDF + 300-dpi PNG; script `figs/compliance_final.py`)

* `figs/fig_r6_compliance_curve.pdf` / `.png` -- Compliance sweep at the calibrated prices on the two Manhattan layouts, written targets: expected cost V per 4-h window (top) and served share (bottom) against the share psi of riders who follow the coordinated plan; (a) sites 04 + 09, the best two-site layout found by the siting pass; (b) sites 06 + 12, the earlier bi-level layout. Line: mean over the three demand scenarios; band: exact-t 95 % interval over scenarios (n = 3); grey dots: scenario means over three draws of the compliant riders. Dashed: selfish equilibrium on free stations; dotted: reference rule r2 on the same layout; open circle: crossing of the mean curve with the selfish equilibrium. At psi = 1 the value equals the ILP plan (time-limited incumbents on 06 + 12). Double column. Replaces fig:res:compliance.
* `figs/fig_r6_compliance_shape_ranking.pdf` / `.png` -- (a) Share of the cost difference between no and full compliance closed at each psi, for 06 + 12 at the legacy prices (open triangles, dashed), 06 + 12 at the calibrated prices (squares) and 04 + 09 at the calibrated prices (circles); bars: exact-t 95 % intervals over scenarios; grey line: proportional benefit. (b) Paired difference V(04 + 09) - V(06 + 12) per window under the coordinated ILP (also against the MIP lower bound of 06 + 12), rule r2, the selfish equilibrium and partial compliance; dot and bar: mean and 95 % interval over the three scenarios; grey dots: scenarios; negative values favour 04 + 09. Double column; suggested for Section S10.5.

## Manuscript items replaced (manuscript/PENDING_R6.md)

**Item 4 (selfish equilibrium, price of decentralisation 354.3 USD, compliance sweep): replaceable**, with two conditions: the layout is "the best written-target two-site layout found (within 3.39 % of a certified lower bound)", not a certified optimum, and several statements must change direction, not only their numbers.

| location | legacy content | calibrated replacement |
|---|---|---|
| 6.9, first paragraph | 703.1 / 1,020.8 / 1,057.5 USD, "45-50 % more", served 0.858 -> 0.750 / 0.758, PoD 354.3 (276.7-432.0) | 04 + 09: 700.0 / 1,148.5 / 1,168.6 USD, 64-67 % more, served 0.983 -> 0.825 / 0.808, PoD 468.6 (380.0-557.3); 06 + 12: 802.4 / 1,238.5 / 1,248.9, PoD 446.4 (191.9-701.0), at least, ILP time-limited. The range "263.6 ... 550.0 USD on the other layouts" is a siting-study result (item 2) and stays legacy. |
| 6.9, "Partial compliance" paragraph | 1,165.0 -> 703.1 USD; 18.2 / 36.0 / 68.4 %; served 0.625 -> 0.858; "savings accelerate"; crossings 0.32 / 0.43, per scenario below 0.25 to 0.75 | 04 + 09: 1,491.1 -> 700.0 USD; 23.2 / 49.4 / 74.4 %; served 0.667 -> 0.983; linear; crossings 0.42 / 0.44, per scenario 0.30-0.53; 06 + 12: 33.3 / 63.1 / 80.0 %, convex, crossings 0.25 / 0.27. Keep: zero compliance costs more than free station choice (every scenario); mixed runs ignore written end targets. Drop "savings accelerate". |
| Figure fig:res:compliance (`figs/x6_compliance.pdf`) | legacy curve, one layout | `figs/fig_r6_compliance_curve.pdf` |
| S10.5 compliance paragraph | legacy values with CIs over scenarios; scenario 1 non-monotone (1,050.8 -> 1,059.9) | Tables 2-5 above (CIs over scenarios); non-monotone case now 04 + 09 scenario 0 (1,311.5 -> 1,357.4); optionally `figs/fig_r6_compliance_shape_ranking.pdf` |
| S10.5 / 6.9 "84 selfish equilibria, 82 converged" | siting-study count | for this experiment: 6 equilibria, all converged (one at the 10-iteration cap with zero share change); the 84 count of the siting study stays with item 2 |
| 7.2 compliance paragraph | "reduces the benefit more than proportionally ... half compliance closed only about a third"; "354.3 USD ... bounds what incentives could recover" | "the benefit is proportional to compliance on the best layout found (half compliance closes about half, 49 %) and front-loaded on the earlier layout (63 %)"; keep "a plan that assumes compliance can be worse than none"; 468.6 USD (40 % of the selfish cost) |
| 7.3 (selfish equilibria) | 84 equilibria | see row above |
| 8, RQ5 sentence | "36.0 %" | "49.4 % (95 % CI over draws 32.9-66.0 %) on the best two-site layout found; 63.1 % on the earlier bi-level layout" |
| abstract, last clause; introduction findings paragraph | "half compliance with the plan closes about a third of the gain"; "siting and compliance results are reported at the legacy prices" | "half compliance closes about half of the gain"; compliance no longer legacy (siting remains legacy until item 2 is replaced) |

**Item 15 (settings and coverage tables): partly.** The compliance part of the Manhattan row of Table S4 (`supplement/s04_costs_parameters.tex`, "selfish equilibrium and compliance sweep ... legacy") can switch to the calibrated prices (scenarios 0-2, ILP plans from the cache, 300 s limit); the siting part of that row stays legacy.

**Item 2 (Manhattan siting): not replaced**, but this run gives the calibrated-price evidence for the 7.2 sentence on follower-dependent rankings for these two layouts: the ranking is significant only under the coordinated follower (Table 6).

**Not affected:** the M4-versus-best-rule values on the learning families (45.7 / 21.1 USD, already calibrated; item 20 "verify").

## Files

* `RESULTS_final.md` -- this report.
* `figs/compliance_final.py` -- analysis and figures (`python3 -I figs/compliance_final.py`; reads the records only).
* `figs/compliance_numbers.json` -- every number above; `figs/compliance_cells.csv` -- one row per run (calibrated and legacy).
* `figs/fig_r6_compliance_curve.{pdf,png}`, `figs/fig_r6_compliance_shape_ranking.{pdf,png}`.
* Server outputs left unchanged: `records.jsonl`, `results.csv`, `per_draw.csv`, `summary.csv`, `layout_values.csv`, `RESULTS.md`, `cache/`, `wall_time.json`.
