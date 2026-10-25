# R6 fleet: fleet size x spares per site under the new prices (final report)

**Question.** On the fleet x spare grid (stress4h family, 48 orders fixed, 0.6 kWh pack; fleet size K in {4, 6, 8, 10} x spares per site B in {1, 2, 3, 4}; seeds 0-2), which design has the lowest system cost for each policy under the new prices (P 60 USD, w 18 USD/h, v 15 USD/h), and what share of orders does it serve? Is the round-5 design that served only about 70 % of orders (artefact c) gone? Is one more bike or one more spare worth more? Are the optima on the edge of the grid? How does this compare with round 5 (old prices P 30, v 36)?

**Sources.** `records.jsonl` (240 rows, last row per (key_md5, method)) and `cases.jsonl` (48 cases) in this folder; round 5: `outputs/r5_x5_stress/records_fleet.jsonl`, `records_core.jsonl` (the K 6 / B 2 cell) and `cases_fleet.jsonl`, 0.6 kWh only. No solve was run for this report. Every number below is recomputed from the records by `figs/fleet_analysis.py` (tables, CSVs) and `figs/make_fleet_figs.py` (figures). The script-generated `RESULTS.md` is kept unchanged and checked in Section 1.

**Protocol (as round 5).** Relaxed end targets (rho 0, R_end 0), aggregated ILP, Gurobi Threads 3, Seed 0, time limit 300 s at K 4 and 6 and 600 s at K 8 and 10. Best rule = per-instance minimum of the end-adjusted total over r2, M2 and M2+M3. System cost = end-adjusted operating total (USD per 4-h window, including the spare set-up of (27), 0.332 USD per spare) + K x 88.94 USD (allocated bike and rider cost per window; a reporting price, not a term of (26)). Gap = 100 (best rule - ILP) / best rule per instance, then averaged. Intervals: exact Student-t 95 % CIs over seeds (t(2) = 4.30 for n = 3); differences are paired per seed first. Served share = served orders / 48.

## Summary

The 70 % design is gone. Under the new prices the lowest seed-mean ILP system cost is at 8 bikes with 3 spares per site: 1477.9 [1307.6, 1648.1] USD per window, served share 99.3 % [96.3, 102.3] (n = 3; its 3 solves are OPTIMAL). This ranking is incumbent-based and not certified. K 8 / B 2 is only 0.25 USD higher, and K 8 / B 2, K 6 / B 2 and K 6 / B 3 have TIME_LIMIT seeds whose bounds allow a lower seed mean (Section 3.1). The certified design statement is 6-8 bikes with 2-3 spares per site, not a unique K 8 / B 3. Seed by seed, the cost-minimal designs are K 6 / B 2, K 8 / B 2 and K 8 / B 3, all OPTIMAL, serving 100 %, 97.9 % and 100 % of orders. On seed 1 the remaining order is unservable for every policy (`n_unservable` = 1), so all servable orders are served. On raw totals, the solver's lower bounds certify each of these designs against every other grid cell. Two qualifications: the neighbouring spare levels are beaten by only 0.2-1.9 USD, and the K 10 / B 2 cell on seed 2 has a useless bound and is excluded only by a nesting argument. Every 4-bike design is now dominated. It costs 252.1 [61.3, 442.8] USD per window more than 8 bikes (paired, best spare level per seed), the proven margin is at least 240.8 USD on every seed, and it serves 25.0 [14.6, 35.4] points fewer orders.

Under the ILP, 6 and 8 bikes tie on cost (difference 1.4 [-176.4, 179.2] USD; per seed -79.7, +28.0, +55.9), so the cheapest fleet size depends on the seed. A sixth bike pays: it saves 214 USD per bike against its 88.94 USD cost. Bikes 7-8 break even (89.4 [0.3, 178.5] USD per bike), and bikes 9-10 do not pay (17.1 [-13.2, 47.5]). The first two values rest partly on TIME_LIMIT solves (4 of 6 solves at 4 -> 6, 2 of 6 at 6 -> 8; time limit 300 s at K 4/6, 600 s at K 8/10). The solver bounds keep their seed means within 210.9-216.9 and 87.3-89.4 USD (Table 4), and the 8 -> 10 value rests on 6 OPTIMAL solves. The second spare per site has a positive value (0.7-22.9 USD net, depending on fleet size). A third spare adds at most 1.5 USD on any seed. A fourth spare adds nothing: its computed net value is -0.12 to -0.35 USD on all 12 fleet size x seed pairs, which is about its 0.33 USD set-up. This is certified on 10 of the 12 pairs: every pair at 6-10 bikes, and K 4 on seed 2. It is not certified at K 4 on seeds 0-1, where both solves are TIME_LIMIT and the bounds allow up to +2.9 and +4.3 USD per spare. The ILP optimum lies inside the grid.

The best rule still needs 8 bikes and 4 spares per site: 1619.6 [1256.2, 1983.0] USD, served 97.9 % [92.7, 103.1]. On seed 2 its cheapest design is 10 bikes and 4 spares. Its optimum sits on the spare edge of the grid on all three seeds, and a fourth spare still pays at 8 bikes, so the rule's true optimum may need more than 4 spares per site. At each policy's own per-seed design, both policies serve the same share on every seed, and the ILP design costs 150.1 [90.0, 210.2] USD per window less (9.4 % [6.5, 12.2]). In round 5 the gap was 17.5 % at 70 % service, and 8.75 % at matched service.

## 1. Problems and anomalies

1. **K 10 / B 2, seed 2: ILP stopped with a 100.5 % MIP gap.** TIME_LIMIT at 604 s, bound -4.35 USD, incumbent 848.89 USD. The incumbent is the K 10 / B 1 MIP start (847.89) plus the set-up of one more spare per site. The first bikes coincide across fleet sizes (`generator.make_fleet_sweep_instance`), so a K 10 schedule can copy the K 8 one and leave 2 bikes idle. Its optimum should therefore not exceed the K 8 / B 2 value on the same seed, 783.16 (TIME_LIMIT, 0.31 %). The incumbent is at least 65.7 USD too high. This is the only violation of that nesting check among the 48 ILP rows (`fleet_analysis.monotonicity`). Consequences:
   - The K 10 / B 2 grid entries are biased: ILP system cost 1661.9 against 1621.5 at B 3, and gap 26.9 [-14.0, 67.8] %.
   - Two `fleet_frontier.csv` entries are artefacts: the bike value 8 -> 10 at B 2 (-2.96 USD) and the spare value at K 10 B 2 -> 3 (13.49 USD).
   - The cost-minimal design is not affected. On seed 2, K 10 / B 3 is OPTIMAL at 724.11, so by nesting the K 10 / B 2 optimum is at least 723.1 and its system cost at least 1612.5. That is above the seed-2 optimum of 1491.5 (an argument from the model, not a solver certificate). The figures mark the cell with a dagger.
2. **K 10 / B 1, seed 2 ran 991 s against a 600 s limit** (TIME_LIMIT, gap 2.31 %; wall-clock gap 13:12:03 -> 13:28:58). The records do not show why. The incumbent passes `check`, so the result stands, but the runtime figure is unreliable.
3. **The auto-generated `RESULTS.md` says "Anomalies: none".** That is wrong because it misses items 1 and 2: it counts only ERROR and SKIPPED_BUDGET rows. All its numbers reproduce exactly: the cost-minimal table, the 16 x 4 grid means and CIs, and the per-seed argmins. Two smaller issues:
   - Its cost-minimal table gives the per-seed argmins (K6_B2, K8_B2, K8_B3) without saying that the seed-mean argmin (K 8 / B 3) is a near-tie with five other cells.
   - `fleet_frontier.csv`'s `cheaper_lever` column compares net USD per unit (one bike vs one spare), not value per USD. A bike costs 268 spares. Use Table 4 here instead.
4. **The ILP is harder to solve at the new prices.** 20 of 48 ILPs hit the time limit (K 4: 8/12, K 6: 7/12, K 8: 3/12, K 10: 2/12). On the 24 instances shared with round 5, 13 are TIME_LIMIT now against 1 of 24 at the old prices. TIME_LIMIT gaps are 0.31-2.31 %, apart from item 1. For this reason the design conclusions rest on proven lower bounds (Section 3.2), not on incumbents.
5. **Rule schedules that break terminal reachability (9).** r2 violates (9) 1-3 times on 21 of its 48 schedules, and the best rule is such a schedule on 11 of 48 instances. As in round 5, (9), (17) and (18) are report-only for the rules, which favours the rule. Sensitivity check: restricting the best rule to schedules that pass `check` leaves its seed-mean cost-minimal design unchanged (K 8 / B 4, 1619.6). The seed-2 argmin also stays at K 10 / B 4 (1700.1 instead of 1671.8).
6. **The rules do not react to the prices on this grid.** On all 24 shared instances, the r2, M2 and M2+M3 schedules are identical in round 5 and round 6: same served count, response cost and bike-km, with lateness cost x 15/36 and unserved cost x 2. M2+M3 equals M2 on all 48 instances: there are no transport services, so M3 never acts. On the rule side, round 6 only reprices round 5. Which rule is best switches between r2 and M2 on 4 of the 24 shared instances.
7. **Small n and seed-level effects.** n = 3 in round 6 and n = 2 in round 5 (0.6 kWh ILPs only on seeds 0-1, K 4-8). Seed 0 is 90-280 USD cheaper than seeds 1-2 for every policy and design, so unpaired CIs on levels are wide. Use the paired differences. Round-5 CIs (t(1) = 12.7) are listed only for completeness.
8. **What the bound-based certificates do and do not cover.** They use raw totals (Gurobi ObjBound + K x 88.94). The end adjustment (0.93-2.98 USD per ILP schedule) is not part of the ILP objective. It changes no argmin, but where cells differ by less than about 1 USD (the spare level among B 2-4) the order is not certified.

## 2. Coverage

- 48 cases (16 cells x 3 seeds), 48 unique instances, 240 records: r2, M2, M2+M3, the best-rule row and one ILP per instance. All rule rows have status OK. All 48 ILPs returned an incumbent: 28 OPTIMAL, 20 TIME_LIMIT, none without an incumbent.
- All 48 ILP schedules pass `check` (`check_ok`), and objective = evaluation holds for all 48 (`obj_eq_eval`). MIP starts were accepted 48/48, from a rule schedule or from the previous spare level's ILP.
- No SKIPPED_BUDGET rows, no budget-shortened solves, no errors. Wall time 158.0 min against a 380 min budget (expected 250 min; `wall_time.jsonl`). All runs use relaxed targets, so the written targets were not run for this stage.
- The round-5 counterpart has 24 instances (K 4/6/8 x B 1-4 x seeds 0-1, 0.6 kWh): 23 OPTIMAL and 1 TIME_LIMIT (0.33 %). The demand hash matches round 6 on all 24 (`demand_md5`), and only the order prices differ (`orders_md5`).

**Table 1. ILP solve status by fleet size (round 6).**

| K | time limit (s) | ILPs | OPTIMAL | TIME_LIMIT | MIP gap of TIME_LIMIT runs (%) | runtime median (s) |
|---|---|---|---|---|---|---|
| 4 | 300 | 12 | 4 | 8 | 0.72, 0.79, 0.81, 0.88, 0.97, 1.00, 1.21, 1.56 | 300 |
| 6 | 300 | 12 | 5 | 7 | 0.63, 0.64, 0.94, 1.14, 1.21, 1.30, 1.54 | 300 |
| 8 | 600 | 12 | 9 | 3 | 0.31, 0.62, 1.34 | 63 |
| 10 | 600 | 12 | 10 | 2 | 2.31, 100.51 (anomaly 1) | 48 |

## 3. Answer

### 3.1 Cost-minimal design within the grid

**Table 2. Cost-minimal design per policy, new prices (system cost in USD per 4-h window; n = 3).**

| policy | design (seed-mean argmin) | system cost | served share | per-seed argmin (system cost, served, status) | on grid edge? |
|---|---|---|---|---|---|
| ILP | K 8 / B 3 (lowest incumbent mean, 3/3 OPTIMAL; ranking not certified, see below) | 1477.9 [1307.6, 1648.1] | 99.3 % [96.3, 102.3] | s0 K 6 / B 2 (1321.5, 100 %, OPTIMAL); s1 K 8 / B 2 (1535.8, 97.9 % = 47/48, the 48th unservable, OPTIMAL); s2 K 8 / B 3 (1494.2, 100 %, OPTIMAL) | no (K and B interior on every seed) |
| best rule | K 8 / B 4 | 1619.6 [1256.2, 1983.0] | 97.9 % [92.7, 103.1] | s0 K 8 / B 4 (1453.3, 100 %); s1 K 8 / B 4 (1676.8, 97.9 %); s2 K 10 / B 4 (1671.8, 100 %) | yes: B = 4 on all seeds; K = 10 on seed 2 |

The ILP surface is flat near its minimum. Six cells lie within 2.8 USD of the minimum in seed means: K 8 / B 2-4 at 1477.9-1478.6 and K 6 / B 2-4 at 1478.8-1480.6 (Figure 1b). K 8 / B 2 against K 8 / B 3 differs by 0.2 [-5.1, 5.6] USD. Within a fleet size, the spare level beyond 2 changes the cost only by the 0.996 USD set-up of three more spares. The fleet size matters more (Section 3.2).

**The seed-mean ranking is not certified** (R6 verification, C1). K 8 / B 3 has the lowest computed seed mean, and its three solves are OPTIMAL, but three competitors rest on TIME_LIMIT incumbents:
- K 8 / B 2 (1478.1, +0.25 USD): its seed-2 solve stopped at 600 s with a 0.31 % gap (system cost 1496.9 incumbent, 1494.5 bound; bounds in this bullet list add the incumbent's end adjustment to Gurobi's bound). Any seed-2 optimum below 1496.2 would make K 8 / B 2 the seed-mean minimum, and its mean can be as low as about 1477.3.
- K 6 / B 3 (1478.8) and K 6 / B 2 (1480.6) are TIME_LIMIT on seeds 1-2. Their mean bounds are 1474.5 and 1473.5.

On the raw-total basis of the certificates, the K 8 / B 3 mean is 1475.4, and the mean bounds of K 8 / B 2, K 6 / B 3 and K 6 / B 2 are 1475.2, 1472.0 and 1471.5. Every other cell has a mean bound above 1475.4, except K 10 / B 2, which nesting excludes (anomaly 1). The certified statement is therefore: the seed-mean cost-minimal design is one of K 6-8 with 2-3 spares per site. These four cells lie within 2.8 USD of each other, far inside the ±170 USD interval (n = 3).

### 3.2 Certificates: what the bounds prove

Per seed, the lower bound of every other cell (ObjBound + K x 88.94) is above the incumbent of the cost-minimal cell (`fleet_analysis.certify_argmin`):

| seed | ILP argmin | its system cost (raw total basis) | min. bound margin of K 4 cells | of K 6 cells | of K 8 cells | of K 10 cells (excl. anomaly 1) |
|---|---|---|---|---|---|---|
| 0 | K 6 / B 2 (OPTIMAL) | 1319.3 | +240.8 | argmin | +80.3 | +250.2 |
| 1 | K 8 / B 2 (OPTIMAL) | 1533.9 | +246.1 | +20.3 | argmin | +138.4 |
| 2 | K 8 / B 3 (OPTIMAL) | 1491.5 | +323.8 | +49.5 | argmin | +122.0 |

Shown: the cost-minimal fleet size is 6 on seed 0 and 8 on seeds 1-2. Every 4-bike design is at least 240.8 USD per window above it, on every seed. Within the argmin's fleet size, the other spare levels B ≥ 2 are also above it on raw totals, but only by 0.19-1.94 USD (seed 0: B 3 +0.94, B 4 +1.94; seed 1: B 3 +0.38, B 4 +1.07; seed 2: B 2 +0.77, B 4 +0.19). That is less than the end adjustment, so the exact spare level among 2-4 is not a robust finding, although the end-adjusted argmin is the same cell on every seed (anomaly 8).

### 3.3 Is the round-5 70 % design (artefact c) gone?

Yes. Paired over seeds 0-2, with the best spare level per seed and fleet size (Figure 2):

| comparison (ILP, new prices) | system cost difference (USD/window) | served share difference (points) |
|---|---|---|
| K 4 - K 8 | +252.1 [61.3, 442.8] (per seed +170.4, +263.1, +322.7) | -25.0 [-35.4, -14.6] |
| K 6 - K 8 | +1.4 [-176.4, 179.2] (per seed -79.7, +28.0, +55.9) | -4.9 [-15.6, 5.9] |
| K 10 - K 8 | +143.6 [83.2, 204.0] (per seed +170.0, +138.6, +122.2) | 0.0 |

- At 4 bikes the ILP schedules serve 33-38 of 48 orders (69-79 %; 74.3 % [63.5, 85.1] at any B ≥ 2; 8 of the 12 K 4 solves are TIME_LIMIT). The higher penalty raises this only slightly: on seeds 0-1, 75.0 % and 64.6 % at the old prices against 79.2 % and 72.9 % now. That suggests a capacity limit of 4 bikes. What changed is the price of the orders left unserved: at P 60 they cost more than the two extra bikes (2 x 88.94 USD) needed to serve them.
- Every design that is cost-minimal or nearly so (K 6-8, B ≥ 2) serves 91.7-100 % of orders on every seed: 94.4 % mean at K 6 and 99.3 % at K 8. None of the ILP schedules is more than 60 min late on any order (`n_late_over_60min` = 0 on all 48), and the longest lateness is 45 min.

### 3.4 One more bike or one more spare?

**Table 4. Marginal values, new prices (USD per window; mean [95 % CI], n = 3).** Bike = (V(K) - V(K+2)) / 2: the gross saving per added bike, which pays if it exceeds 88.94. Spare = (V(B) - V(B+1)) / 3 sites: the value per added spare, already net of its 0.332 USD set-up. V = end-adjusted operating total. Full tables, including all K and B and round 5, are in `figs/fleet_marginal_values_r6.csv` and `_r5.csv`. Solve-status column (added in the R6 verification, C6): the ILP solves behind each new-price value. The range is the seed mean that the solver bounds allow, on the raw-total basis of the certificates. For spares it uses nesting: a spare can be left idle, so the value is at least -0.332. The time limit is 300 s at K 4 and 6 and 600 s at K 8 and 10, so the 6 -> 8 step compares solves made under different limits. The bound range covers this.

| step | ILP, new prices | ILP solve status (new prices); bound-certified range of the mean | ILP, old prices (n = 2, per seed) | best rule, new prices |
|---|---|---|---|---|
| bike 4 -> 6 (B 3) | 214.4 [195.3, 233.5]; pays on 3/3 seeds | 4/6 TIME_LIMIT (K 4 s0-1, K 6 s1-2; gaps 0.63-1.00 %); [210.9, 216.9], every seed > 88.94 | 74.5 (78.6, 70.4); does not pay | 275.1 [26.3, 524.0]; pays on 3/3 seeds |
| bike 6 -> 8 (B 3) | 89.4 [0.3, 178.5] (48.8, 102.4, 116.9); break-even | 2/6 TIME_LIMIT (K 6 s1-2; gaps 0.63, 0.64 %); [87.3, 89.4]; per seed s0 < 88.94 < s1, s2 | 34.0 (30.8, 37.3); does not pay | 245.9 [99.7, 392.2]; pays on 3/3 seeds |
| bike 8 -> 10 (B 3) | 17.1 [-13.2, 47.5]; does not pay on any seed | 6/6 OPTIMAL | not run | 79.7 [-69.9, 229.3] (10.8, 106.2, 122.1); pays on 2/3 seeds |
| spare 1 -> 2 (K 8) | 22.9 [-45.2, 91.0] (-0.2, 15.7, 53.2) | 3/6 TIME_LIMIT (B 1 s1-2, B 2 s2); [21.2, 23.5] | 2.4 (-0.1, 5.0) | 175.3 [90.3, 260.4] |
| spare 2 -> 3 (K 8) | 0.08 [-1.69, 1.85] | 1/6 TIME_LIMIT (B 2 s2, 0.31 %); [-0.05, 0.23] | -0.32 | 71.3 [-74.5, 217.1] |
| spare 3 -> 4 (K 8) | -0.25 [-0.52, 0.03] | 6/6 OPTIMAL | -0.34 | 26.4 [-29.0, 81.8] (1.3, 34.0, 44.0) |
| spare 1 -> 2 (K 6) | 11.8 [-14.0, 37.6] | 5/6 TIME_LIMIT; [7.6, 14.4] | 1.5 | 183.3 [17.1, 349.4] |
| spare 3 -> 4 (K 6) | -0.31 [-0.40, -0.22] | B 3 TIME_LIMIT s1-2, B 4 OPTIMAL; [-0.33, -0.27] (nesting) | -0.30 | 11.7 [-31.1, 54.5] |
| spare 3 -> 4 (K 4) | -0.33 [-0.38, -0.29] (-0.35, -0.31, -0.33) | 4/6 TIME_LIMIT; both levels TIME_LIMIT on s0-1, where the B 4 incumbent is the B 3 MIP start plus set-up; per seed [-0.33, +2.86], [-0.33, +4.34], -0.26 (s2 OPTIMAL); not certified | -0.33 | -0.33 [-0.35, -0.30] |

Interpretation of Table 4 (Figure 3):

- **ILP.** A spare is the cheaper lever per USD wherever it has value, because one bike costs as much as 268 spares. But only the second spare per site has value: 3.4 USD net at 4 bikes, 11.8 at 6, 22.9 at 8 and 0.7 at 10. The third spare adds -0.33 to +1.47 USD per seed. The positive values are 0.6-1.5 USD: mostly within the MIP gaps of TIME_LIMIT solves (K 6 seeds 1-2, K 8 seed 2), and real but small at K 4 on seed 2, where both solves are OPTIMAL. The fourth spare is not used: its computed net value is -0.12 to -0.35 USD on every seed and fleet size, which is its set-up cost. This is certified (both solves OPTIMAL, or B 4 OPTIMAL plus nesting) on 10 of 12 pairs. At K 4, seeds 0-1, both solves are TIME_LIMIT and the B 4 incumbent is only the B 3 MIP start plus set-up, so there the bounds allow +2.86 and +4.34 USD per spare (Table 4). The binding lever is therefore the bike. At the new prices a bike pays up to 6, breaks even from 6 to 8 (pays on seeds 1-2, not on seed 0) and does not pay from 8 to 10. At the old prices no bike beyond 4 paid (74.5 and 34.0 USD). The new prices raise the value of a bike about 2.6-2.9-fold at this size.
- **Best rule.** Spares keep paying up to the edge of the grid: 26.4 USD per spare from 3 to 4 at 8 bikes, positive on all three seeds, and 13.4 at 10 bikes. Bikes pay up to 8 and, on seeds 1-2, up to 10. The rule's cost is not monotone in resources. On three seed x cell combinations an extra spare makes the rule's operation worse (net value below minus its set-up): K 4 / B 2 -> 3 on seed 2 (-19.1), K 6 / B 2 -> 3 on seed 1 (-1.3) and K 10 / B 3 -> 4 on seed 1 (-1.0). An extra bike loses money at K 8 -> 10, B 2, on seed 1 (-21.7).

### 3.5 Grid edge

- **ILP, shown:** the optimum is interior on every seed. The value of the extra bike is above its cost on every seed for 4 -> 6 and below it on every seed for 8 -> 10. The computed net value of the extra spare from 3 -> 4 is -0.12 to -0.35 USD on every seed and fleet size, which is its set-up cost. It is certified at the argmin fleet sizes (K 6 on seed 0, K 8 on seeds 1-2: all OPTIMAL) and at every K 6-10 pair, but not at K 4 on seeds 0-1. That gap does not matter here, because K 4 is at least 240.8 USD above the optimum on every seed (Section 3.2). A grid of K 4-10 and B 1-4 therefore brackets the ILP optimum. In round 5 the ILP optimum sat on the smallest fleet size.
- **Best rule, suggested:** the optimum is on the spare edge (B = 4) on all seeds and at the K = 10 corner on seed 2. The spare's marginal value is still positive at B 3 -> 4, so more than 4 spares per site would probably lower the rule's cost further. That was not tested. The rule-vs-ILP comparison in 3.6 is therefore an upper bound on the true design gap.

### 3.6 ILP against best rule at the designs

| comparison | difference (USD/window) | relative | served share |
|---|---|---|---|
| each policy at its own per-seed cost-minimal design (rule - ILP) | 150.1 [90.0, 210.2] (131.8, 141.0, 177.6) | 9.4 % [6.5, 12.2] | identical on all 3 seeds (100 / 97.9 / 100 %) |
| rule at K 8 / B 4 - ILP at K 8 / B 3 (seed-mean designs; the ILP's is the lowest incumbent mean, not certified, Section 3.1) | 141.7 [-86.6, 370.0] (50.7, 140.0, 234.5) | 8.5 % [-4.1, 21.0] (3.5, 8.4, 13.6 %) | 97.9 % vs 99.3 % |

Where the saving comes from, per seed:
- Seed 0: the ILP uses 2 fewer bikes (-177.9 USD) and pays 46.1 USD more in operations.
- Seed 1: the same fleet size and 2 fewer spares per site, with 141.0 USD lower operating cost.
- Seed 2: 2 fewer bikes and one fewer spare per site, at the same operating cost (782.7 vs 782.3).

The ILP reaches the rule's service with less hardware.

Gap by cell (per-instance gap, mean [CI], n = 3 per cell): it falls with spares, from 48.5 [43.8, 53.2] % at B 1 to 22.0 [13.9, 30.1] % at B 4 (pooled over the four fleet sizes, n = 12 instances each). At the largest design (K 10 / B 4) it is smallest at 6.8 [3.2, 10.5] %. At the ILP's design K 8 / B 3 it is 20.6 [-10.2, 51.4] % (7.3, 22.7, 31.9 per seed). Full grid in the appendix.

## 4. Comparison with round 5 (old prices) on the same instances

Same 24 instances (seeds 0-1, K 4/6/8, B 1-4; the demand hash matches). System-cost levels are not comparable across price regimes. Designs, served shares and cross-priced schedules are.

| | old prices (round 5) | new prices (round 6), same seeds and K ≤ 8 | new prices, full grid (n = 3) |
|---|---|---|---|
| ILP seed-mean argmin (lowest incumbent mean) | K 4 / B 2, 1310.1, served 69.8 % | K 6 / B 3, 1443.1, served 95.8 % (not certified: K 6 / B 3 and K 6 / B 2 are TIME_LIMIT on seed 1 and K 6 / B 2's mean bound is below) | K 8 / B 3, 1477.9, served 99.3 % (not certified, Section 3.1) |
| ILP per-seed argmin | s0 K 4 / B 2 (75.0 %), s1 K 4 / B 2 (64.6 %) | s0 K 6 / B 2 (100 %), s1 K 8 / B 2 (97.9 %) | + s2 K 8 / B 3 (100 %) |
| best-rule seed-mean argmin | K 8 / B 4, 1587.7, served 99.0 % | K 8 / B 4, 1565.1, served 99.0 % | K 8 / B 4, 1619.6, served 97.9 % |
| ILP design below the rule's design (per seed) | 17.5 % (13.0, 21.3) at 70 % vs 99 % service | 8.7 % (9.1, 8.4) at equal service | 9.4 % [6.5, 12.2] at equal service |

- **Served share.** On all 24 shared instances the ILP serves at least as many orders at the new prices as at the old ones: +4.9 [3.7, 6.2] points on average (CI over the 24 instances), up to +10.4. By fleet size: +6.5 points at K 4, +6.2 at K 6, +2.1 at K 8.
- **Cost of keeping the round-5 design.** Keeping K 4 / B 2 under the new prices, even with re-optimised schedules, costs 250.0 USD (18.9 %) more than the new optimum on seed 0 and 263.1 USD (17.1 %) more on seed 1. Conversely, the new per-seed designs would have cost 20.5 USD (1.6 %, seed 0) and 140.4 USD (10.4 %, seed 1) more under the old prices. The design shift is caused by the prices.
- **Cross-pricing consistency check.** A round-5 ILP schedule repriced to the new prices (unserved cost x 2, lateness cost x 15/36) is never cheaper than the round-6 ILP schedule. Conversely, a round-6 schedule repriced to the old prices is never cheaper than the round-5 optimum (24/24 both ways). The mean advantage of the own-price schedule (over the 24 instances) is 44.2 [33.5, 54.8] USD at the new prices and 55.1 [37.6, 72.5] at the old prices. It is 0 on the four K 8 cells of seed 0, where both rounds serve all orders on time. The round-6 incumbents, including the 13 TIME_LIMIT ones, are therefore at least as good as the best schedule known from round 5.
- **Best rule.** Its schedules are identical in both rounds (anomaly 6), so its design does not move (K 8 / B 4 in both). Its cost at that design changes only by repricing: equal on seed 0 (no lateness, all orders served) and -45.2 USD on seed 1.
- **Round-5 statements that change.**
  - "Under the ILP neither an extra bike nor an extra spare pays beyond 4 bikes and 2 spares": now a bike pays up to 6 and breaks even up to 8.
  - "The cost-minimal ILP design serves only 70 % of orders": now 92-100 %.
  - "Both cost-minimal designs lie on the grid edge": now only the rule's does.
  - The round-5 finding that only the second spare matters to the ILP is unchanged.

## 5. Interpretation

**Shown by the records (n = 3, certified where stated):**

- The recalibrated order prices remove artefact (c). The ILP's cost-minimal fleet moves from 4 bikes (old prices) to 6-8 bikes. Its served share moves from 65-75 % to 98-100 % per seed (92-100 % across the K 6-8 near-optimal plateau). 4-bike designs are excluded by proven lower bounds on every seed, by at least 240.8 USD per window.
- Under the ILP, spares saturate at 2 per site (3 at most, within MIP gaps). The fourth spare is not used: its computed net value is minus its set-up cost on every seed, certified on all pairs at 6-10 bikes (10 of 12 pairs; at K 4 seeds 0-1 only incumbent-based). Bikes are the binding lever: at the new prices bikes 5-6 save 2.4 times their allocated cost.
- At the cost-minimal designs the coordinated design is 9.4 % [6.5, 12.2] cheaper than the rule's at identical service on every seed. The saving comes mainly from two fewer bikes on two of the three seeds.
- The rules' schedules are price-independent on this grid, so all of the change on the rule side is repricing.

**Suggested, not shown:**

- *Fleet size under the ILP.* Whether 6 or 8 bikes is cheaper on average cannot be decided with 3 seeds. The paired difference is 1.4 [-176.4, 179.2] USD, and the per-seed argmin differs. On average, each extra bike from 6 to 8 is worth about its allocated cost (89.4 vs 88.94 USD). The average choice is therefore a knife-edge that depends on the bike and rider cost assumption. Per seed the choice is clear (48.8 on seed 0 against 102.4 and 116.9 on seeds 1-2). In practice it also depends on the service level wanted: 94.4 % at 6 bikes against 99.3 % at 8.
- *The rule's optimum.* It probably needs more than 4 spares per site, since spares still pay at B 3 -> 4. The grid stops there, so the 9.4 % design gap is an upper bound with respect to the spare level.
- *Is P 60 high enough?* That the remaining unserved orders at the ILP design (0-1 per seed) are an economic choice and not a modelling artefact is plausible, but it is only checked for 3 seeds of one family and one pack size. The round-5 pack variation (0.5-1.0 kWh) was not re-run.
- *Scope of the "2 spares per site" result.* It holds for 48 orders on 3 sites in a 4-h window. The round-5 LP shadow prices show spare values rising steeply with demand (core axis, 8 orders per bike), so it should not be extrapolated to larger demand.

## Figures (`figs/`, PDF vector and PNG 300 dpi; script `figs/make_fleet_figs.py`, reader `figs/fleet_analysis.py`)

1. `fig_fleet_design_map` (7.2 in). *System cost above the cost-minimal design over fleet size x spares per site, seed means. (a) ILP, old prices (round 5, seeds 0-1, n = 2). (b) ILP, new prices (n = 3). (c) Best rule, old prices (n = 2). (d) Best rule, new prices (n = 3). Each cell gives the excess in USD per 4-h window and the served share. The box marks the lowest seed-mean cost. Triangles mark the seeds whose own cost-minimal design is that cell. The dagger marks the cell containing the 100 % MIP-gap solve (anomaly 1). An asterisk marks ILP cells whose mean includes a TIME_LIMIT solve. In (b) the box is not certified: the bounds of K 8 / B 2 and K 6 / B 2-3 allow a lower mean. K 10 was not run in round 5.* It shows the ILP optimum moving from the 4-bike corner at 70 % service to the 6-8 bike plateau at 94-99 %, while the rule stays at K 8 / B 4.
2. `fig_fleet_size_curve` (7.2 in). *(a) System cost against fleet size at the best spare level per seed and (b) served share at the same designs. ILP and best rule; new prices solid with filled markers, old prices dashed with open markers. Means, with exact-t 95 % CIs for n = 3 and individual seeds as small dots. Rings mark each curve's lowest mean; for the ILP at new prices, 6 and 8 bikes tie (+1.4 USD) and the ring is not certified.* The CIs are wide because seed levels differ; the paired differences are in Section 3.3.
3. `fig_fleet_marginal_values` (7.2 in). *(a) Saving per extra bike (USD per window per bike) at 3 spares per site, against the allocated bike and rider cost of 88.94 USD (dashed). (b) Net value of one more spare per site at 8 bikes. Bars are means, error bars are exact-t 95 % CIs (n = 3 only), and dots are seeds. An open dot is an ILP seed value that rests on a TIME_LIMIT solve at either end of the step. Hatched bars are old prices (n = 2).*

Colours are Okabe-Ito blue for the ILP and vermillion for the best rule; the colour-vision-deficiency check passed. The price regime is shown by fill and line style.

Data files written by the reader: `figs/fleet_per_instance_r6.csv` (48 rows), `figs/fleet_per_instance_r5_shared.csv` (24 rows), `figs/fleet_marginal_values_r6.csv`, `figs/fleet_marginal_values_r5.csv`, `figs/fleet_cross_pricing.csv`.

## Appendix A. Grid tables, new prices (mean [exact-t 95 % CI], n = 3 per cell)

ILP system cost (USD per window; K 10 / B 2 includes anomaly 1):

| K \ B | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 4 | 1740.0 [1380.4, 2099.6] | 1729.7 [1388.6, 2070.9] | 1729.7 [1390.4, 2069.0] | 1730.7 [1391.5, 2069.8] |
| 6 | 1516.0 [1124.9, 1907.0] | 1480.6 [1138.0, 1823.2] | 1478.8 [1142.0, 1815.5] | 1479.7 [1143.1, 1816.3] |
| 8 | 1546.9 [1220.3, 1873.5] | 1478.1 [1306.7, 1649.6] | **1477.9 [1307.6, 1648.1]** | 1478.6 [1308.7, 1648.5] |
| 10 | 1664.1 [1452.4, 1875.9] | 1661.9 [1451.6, 1872.3] | 1621.5 [1494.0, 1749.0] | 1622.4 [1494.8, 1750.0] |

Best-rule system cost:

| K \ B | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 4 | 2582.7 [2503.4, 2662.1] | 2387.3 [2098.8, 2675.7] | 2385.2 [1985.1, 2785.2] | 2386.1 [1986.0, 2786.3] |
| 6 | 2616.7 [2316.7, 2916.7] | 2066.8 [1313.4, 2820.3] | 2012.8 [1271.4, 2754.2] | 1977.7 [1320.3, 2635.0] |
| 8 | 2438.7 [1759.5, 3117.9] | 1912.7 [981.5, 2844.0] | 1698.9 [1169.4, 2228.4] | **1619.6 [1256.2, 1983.0]** |
| 10 | 2496.4 [1872.1, 3120.6] | 1992.8 [1216.0, 2769.7] | 1717.4 [1485.8, 1948.9] | 1677.0 [1509.3, 1844.7] |

ILP served share (%):

| K \ B | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 4 | 73.6 [60.6, 86.6] | 74.3 [63.5, 85.1] | 74.3 [63.5, 85.1] | 74.3 [63.5, 85.1] |
| 6 | 91.7 [78.0, 105.4] | 94.4 [82.5, 106.4] | 94.4 [82.5, 106.4] | 94.4 [82.5, 106.4] |
| 8 | 97.2 [89.3, 105.1] | 99.3 [96.3, 102.3] | 99.3 [96.3, 102.3] | 99.3 [96.3, 102.3] |
| 10 | 98.6 [95.6, 101.6] | 98.6 [95.6, 101.6] | 99.3 [96.3, 102.3] | 99.3 [96.3, 102.3] |

Best-rule served share (%):

| K \ B | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 4 | 50.0 [44.8, 55.2] | 59.7 [48.9, 70.5] | 61.1 [45.3, 76.9] | 61.1 [45.3, 76.9] |
| 6 | 54.9 [48.9, 60.8] | 76.4 [47.0, 105.8] | 80.6 [61.0, 100.1] | 81.9 [65.3, 98.6] |
| 8 | 68.1 [39.6, 96.6] | 87.5 [58.7, 116.3] | 95.1 [82.1, 108.2] | 97.9 [92.7, 103.1] |
| 10 | 72.2 [47.8, 96.7] | 90.3 [69.4, 111.2] | 97.9 [92.7, 103.1] | 99.3 [96.3, 102.3] |

Gap ILP vs best rule (%, per instance, end-adjusted):

| K \ B | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 4 | 37.9 [23.5, 52.3] | 32.5 [24.1, 40.8] | 32.3 [24.2, 40.5] | 32.3 [24.2, 40.4] |
| 6 | 53.0 [39.4, 66.6] | 37.7 [28.1, 47.4] | 35.5 [24.7, 46.3] | 34.1 [26.5, 41.7] |
| 8 | 51.6 [47.8, 55.4] | 32.6 [-10.7, 75.8] | 20.6 [-10.2, 51.4] | 14.7 [-5.6, 35.0] |
| 10 | 51.5 [45.6, 57.5] | 26.9 [-14.0, 67.8] | 11.1 [-7.5, 29.7] | 6.8 [3.2, 10.5] |

Round-5 counterparts (old prices, seeds 0-1, n = 2; seed-mean values): ILP system cost 1310.1-1312.0 at K 4, 1338.9-1343.4 at K 6, 1448.8-1456.1 at K 8. ILP served share 68.8-69.8 % at K 4, 87.5-89.6 % at K 6, 96.9 % at K 8. Best-rule system cost minimum 1587.7 at K 8 / B 4. Full tables are printed by `python3 -c "import fleet_analysis as F; F.appendix()"` in `figs/`.

## Verification corrections (R6)

Two claims were refuted by at least one of two independent refuters. I recomputed both from `records.jsonl`: 48 ILP rows, one per cell and seed (ILP_tl300 at K 4/6, ILP_tl600 at K 8/10), all stress4h (`r5_stress4h`), relaxed targets (`rho0_R0`), new prices (`P60_w18_v15`), allocated cost 88.94339 per bike on every row. The fields used were `total_end_adjusted`, `obj`, `bound`, `gap`, `status`, `n_served`, `n_unservable` and `mip_start_variant`. Bound arguments use the raw-total basis (`obj` = `total`), where Gurobi's bound is valid. Every number in both claims reproduces exactly. That includes `cost_minimal_design.csv` and `figs/fleet_marginal_values_r6.csv`. The corrections concern certification and disclosure, not values.

**C1.** Claim: per-seed cheapest ILP designs are K 6 / B 2 (1321.5, 48/48, OPTIMAL), K 8 / B 2 (1535.8, 47/48, OPTIMAL) and K 8 / B 3 (1494.2, 48/48, OPTIMAL); the seed-mean cheapest is K 8 / B 3 at 1477.9 USD.
- Refuter 1: refuted (narrowly). The numbers are right, but the seed-mean sentence presents an unresolved near-tie as settled.
- Refuter 2: not refuted, with the same caveats.
- Recomputed:
  - Per seed, the claim is exact. Seed 1's 47/48 is 47 of 47 servable orders (`n_unservable` = 1 for every policy).
  - Each per-seed argmin is certified by the bounds against every other cell. The exception is K 10 / B 2 on seed 2 (gap 100.5 %), which nesting excludes.
  - Seed mean: K 8 / B 3 1477.9 [1307.6, 1648.1] (n = 3, 3/3 OPTIMAL), then K 8 / B 2 1478.1 (seed 2 TIME_LIMIT, 0.31 %), K 8 / B 4 1478.6, K 6 / B 3 1478.8 (seeds 1-2 TIME_LIMIT), K 6 / B 4 1479.7 and K 6 / B 2 1480.6 (seeds 1-2 TIME_LIMIT).
  - Apart from K 10 / B 2, which nesting excludes, the mean lower bounds of three cells fall below the K 8 / B 3 mean. On the raw basis, K 8 / B 2 1475.2, K 6 / B 3 1472.0 and K 6 / B 2 1471.5, against 1475.4. On the end-adjusted basis, about 1477.3, 1474.5 and 1473.5, against 1477.9.
- Verdict: refuter 1 is right on the seed-mean sentence, and refuter 2's caveats agree with it. The per-seed sentence stands. The seed-mean argmin K 8 / B 3 is the lowest incumbent mean, not a certified optimum. What is certified is that the seed-mean optimum is one of K 6-8 with 2-3 spares per site.
- Changed:
  - Summary paragraph 1: certification caveat, the 6-8 bikes / 2-3 spares statement, and the unservable note.
  - Table 2, ILP row: label and seed-1 served note.
  - Section 3.1: new paragraph "The seed-mean ranking is not certified", with the bounds.
  - Section 3.6 and Section 4 tables: "not certified" notes. The Section 4 seeds 0-1 column (K 6 / B 3) has the same issue.
  - Figure 1 (`fig_fleet_design_map`): asterisks on ILP cells whose mean includes a TIME_LIMIT solve, and a footer note that the box in (b) is not certified.
  - Figure 2 (`fig_fleet_size_curve`): annotation that the ILP ring at 8 bikes is a tie with 6 and not certified.
  - Captions updated.

**C6.** Claim: ILP marginal values at B 3 are 214.4 [195.3, 233.5] (4 -> 6), 89.4 [0.3, 178.5] (6 -> 8) and 17.1 [-13.2, 47.5] (8 -> 10) USD per bike, and the net value of a fourth spare is -0.12 to -0.35 USD for every K and seed.
- Refuter 1: refuted. The numbers are right, but the spare statement is presented as an ILP fact where neither solve is optimal, and n, solve status and the mixed time limits are missing.
- Refuter 2: not refuted on the numbers. It agrees the values are incumbent-based and not certified at K 4, seeds 0-1.
- Recomputed:
  - All values reproduce (n = 3, exact t(2)).
  - 4 -> 6: 4 of 6 solves are TIME_LIMIT (gaps 0.63-1.00 %). The bound-certified mean is 210.9-216.9, and every seed is above 88.94.
  - 6 -> 8: K 6 is TIME_LIMIT on seeds 1-2 (300 s, while K 8 had 600 s). The bound range is 87.3-89.4, and per seed s0 is below 88.94 and s1-s2 are above.
  - 8 -> 10: 6/6 OPTIMAL.
  - Fourth spare: the incumbent range is -0.348 to -0.123 over the 12 pairs (raw basis -0.332 to -0.062, so the spread is end-adjustment noise). It is certified on 10 pairs: 8 with both solves OPTIMAL, and K 6 seeds 1-2 with B 4 OPTIMAL plus nesting, which gives [-0.33, -0.27] and [-0.33, -0.20].
  - At K 4, seeds 0-1, both B 3 and B 4 are TIME_LIMIT. The B 4 incumbent was MIP-started from the B 3 ILP and equals its operating cost plus the 0.996 USD set-up. The bounds allow [-0.33, +2.86] and [-0.33, +4.34] USD per spare.
- Verdict: refuter 1 is right that "for every K and seed" overstates certainty, and refuter 2's numbers agree. The bike values stand, now with solve status disclosed. The fourth-spare statement is corrected to "computed on all 12 pairs, certified on 10, incumbent-only at K 4 seeds 0-1". No design conclusion changes, because K 4 is at least 240.8 USD above the optimum on every seed and the argmin fleet sizes (K 6 on seed 0, K 8 on seeds 1-2) are all OPTIMAL.
- Changed:
  - Summary paragraph 2: status disclosure for the bike values and the fourth-spare qualification.
  - Table 4: new column with the ILP solve status and bound-certified range per row, a note on the 300 s and 600 s limits, and a new row for spare 3 -> 4 at K 4.
  - Section 3.4 ILP bullet, Section 3.5 ILP bullet and Section 5 second bullet: fourth-spare wording qualified.
  - Figure 3 (`fig_fleet_marginal_values`): seed dots that rest on a TIME_LIMIT solve are now drawn open, with a legend entry, and the caption is updated.

All figures were regenerated by `figs/make_fleet_figs.py`, whose only changes are the markers and annotations. No numbers were changed, and no solve was run.
