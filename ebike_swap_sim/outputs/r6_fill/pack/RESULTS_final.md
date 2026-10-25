# R6 fill, stage pack: pack-size axis of the fleet sweep at the new prices (final report)

**Question.** On the fleet x spare grid of the stressed four-hour family (stress4h, 48 orders fixed; fleet size K in {4, 6, 8, 10} x spares per site B in {1, 2, 3, 4}; seeds 0-2, n = 3), operated by the best rule at the new prices (P 60 USD per unserved order, w 18 USD/h response from release, v 15 USD/h lateness from the promise): which design has the lowest system cost at pack sizes of 0.5, 0.75 and 1.0 kWh, how does the pack size change the cost and the service, how does this compare with the legacy-price values (P 30, v 36) in the manuscript, and how do the rule's designs at every pack size compare with the ILP's design at 0.6 kWh?

**Sources.** `records.jsonl` (576 rows, 144 cases) and `cases.jsonl` in this folder (rule-only cells at 0.5 / 0.75 / 1.0 kWh); `outputs/r6_penalty/fleet/records.jsonl` (256 rows incl. the 16 retry rows) and `cases.jsonl` (48 cases) for the 0.6 kWh grid with the ILP; round 5 at the legacy prices: `outputs/r5_x5_stress/records_fleet.jsonl` (686 rows) and `records_core.jsonl` (the 0.6 kWh, 6-bike, 2-spare cell on seeds 0-1). No solve was run for this report. Every number below is recomputed from the records by `figs/pack_analysis.py` (tables, CSVs; its printed output is `figs/pack_analysis_output.md`) and `figs/make_pack_figs.py` (figures). The script-generated `RESULTS.md` is kept unchanged and checked in Section 1.

**Protocol (as the fleet stage).** Relaxed end targets (rho 0, R_end 0), 48 orders on 3 sites. Pack size realised with the energy step fixed at 25 Wh (L = 20 / 24 / 30 / 40 levels), the same charger power (0.333 kW), so a larger pack also takes longer to charge; the spare set-up cost scales with the pack (0.277 / 0.332 / 0.415 / 0.553 USD per spare and window). Best rule = per-instance minimum of the end-adjusted total over r2, M2 and M2+M3. System cost = end-adjusted operating total (USD per 4-h window, spare set-up included) + K x 88.94 USD (allocated bike and rider cost per window, identical at every pack size; a reporting price, not a model term). Intervals: exact Student-t 95 % CIs over seeds (t(2) = 4.30 for n = 3); differences are paired per seed first. Served share = served orders / 48. "ILP, 0.6 kWh" uses the fleet records after the round-6 retries (last row per key, rows marked `retry_worse` ignored).

## Summary

At the new prices the best rule's cost-minimal design is 8 bikes and 4 spares per site at 0.6, 0.75 and 1.0 kWh and 10 bikes and 4 spares at 0.5 kWh. Its system cost falls monotonically with the pack, 1,684.9 [1,530.4, 1,839.4] USD per window at 0.5 kWh, 1,619.6 [1,256.2, 1,983.0] at 0.6, 1,611.8 [1,264.7, 1,959.0] at 0.75 and 1,606.8 [1,318.0, 1,895.6] at 1.0 kWh (n = 3 each), a spread of 78 USD, with 97.9-99.3 % of orders served. Paired per seed at each pack's own cost-minimal design, the 0.5 kWh pack costs 50.8 [32.1, 69.4] USD (3.1 %) more than 0.6 kWh on all three seeds, while 0.75 and 1.0 kWh cost no measurable amount less (9.0 [-62.8, 80.7] and 5.3 [-59.6, 70.2] USD more). Away from the optimum a larger pack helps the rule a lot: averaged over the 16 designs the 1.0 kWh pack is 72.4 [-177.9, 33.0] USD cheaper than 0.6 kWh (cheaper on all three seeds and in 30 of 48 design-seed pairs), with the largest savings at one spare per site (136-231 USD). The whole effect is an unserved-order effect: with 8 bikes and 4 spares the 1.0 kWh pack serves 2.0 [-0.5, 4.5] more orders per window than 0.5 kWh with 6.0 [1.7, 10.3] fewer swaps and 3.2 [2.2, 4.2] min less station time per bike, which saves 120 USD of penalty against 3.3 USD more spare set-up and less than 1 USD in electricity, travel and end adjustment. Because the rule schedules are identical at both prices (432 of 432 rule rows reprice exactly), the new prices change only the weights: the same pack step saves 105.7 USD at the new prices and 60.9 at the legacy prices (difference exactly 30 USD per unserved order less 21 USD per lateness hour). The rule's spare edge softens with the pack: a fourth spare per site still pays the rule 20.9-26.4 USD at 0.5-0.75 kWh, but only 2.4 [-9.6, 14.4] USD at 1.0 kWh (and -0.3 at 10 bikes), and the ninth and tenth bike pay the rule only at 0.5 kWh. At every pack size the rule's cost-minimal design stays 150-201 USD (9.4-12.2 %) above the ILP's cost-minimal 0.6 kWh design at the same served share (CIs exclude zero at every pack), so a 67 % larger pack does not buy the rule what coordination buys the ILP at 0.6 kWh. The legacy-price sentence that a further spare at 4 bikes and 2 spares has a significant negative value for the rule (-9.33 USD at 0.5 kWh) does not survive repricing: -1.7 [-16.9, 13.5] USD.

## 1. Problems and anomalies

1. **The auto-generated `RESULTS.md` says "Anomalies: none".** It counts only ERROR and SKIPPED_BUDGET rows. All of its numbers reproduce exactly (cost-minimal designs per pack with half-widths 154.49 / 363.43 / 347.13 / 288.82 USD; the 64 x 2 grid means). Two of its columns should not be quoted: `cheaper_lever` in `fleet_frontier.csv` compares the net value of one bike with that of one spare (a bike costs as much as 161-321 spares), and `V` in that file is the operating total, not the system cost.
2. **Rule schedules that break terminal reachability (9).** r2 violates (9) on 50 of its 192 new-price schedules (29 of the 144 pack-stage cells), M2 on 1, and the best rule is such a schedule on 25 of 192 instances (11 at 0.5 kWh, 11 at 0.6, 2 at 0.75, 1 at 1.0). As in rounds 5-6, (9), (17) and (18) are report-only for the rules, which favours the rule. Sensitivity check: restricting the best rule to schedules that pass `check` leaves every cost-minimal design unchanged and moves only the 0.5 kWh cost, 1,684.9 to 1,694.3 USD.
3. **The 0.6 kWh ILP reference is the retried fleet grid, not the one in the fleet final report.** 13 retry rows are in force (12 re-solved as `not_optimal`, 1 `sleep_truncated`; all at 600 s but still labelled `ILP_tl300` in `method`), 3 retries ended worse and are ignored (`retry_worse`: K 4 / B 1 seed 1, K 6 / B 1 seed 1, K 6 / B 3 seed 1). Effects: the K 10 / B 1 seed-2 row that had run 991 s is replaced by an OPTIMAL 565 s solve (837.1 against 847.9 USD); the seed-mean ILP system cost of K 6 / B 2 moves from 1,480.6 to 1,478.5 USD; every other cell moves by less than 0.1 USD, the per-seed argmins (K 6 / B 2, K 8 / B 2, K 8 / B 3, all OPTIMAL) and the lowest incumbent mean (K 8 / B 3, 1,477.9) are unchanged. The K 10 / B 2 seed-2 solve with the 100.5 % MIP gap is still the row of record (a plain 600 s TIME_LIMIT row, skipped at the default retry limit); it enters no comparison in this report (Section 3.5 uses the ILP's per-seed and seed-mean minima). Solve status after the retries: 29 OPTIMAL and 19 TIME_LIMIT of 48 (Table 1).
4. **`demand_md5` differs between pack sizes of the same seed** because the hash includes the bikes' initial charge levels in energy steps and L, both of which change with the pack. The orders are identical: `orders_md5` is the same across the four pack sizes and the four fleet sizes of a seed (one hash per seed). Pairing across packs is therefore by seed on identical orders and bike start nodes. The pack-stage instances equal the legacy ones byte for byte (`demand_md5` identical on all 168 instances shared with round 5).
5. **The legacy rows of the manuscript's sizing table mix n = 2 and n = 3.** The legacy 0.6 kWh row (1,587.7 USD, 8 bikes / 4 spares) rests on seeds 0-1, the other pack sizes on seeds 0-2. Seed 2 is 100-250 USD more expensive than seed 0 on every design, so the legacy 0.6 kWh "advantage" of 50-100 USD over the other packs is partly seed composition: on seeds 0-1 the legacy pack ranking is 0.6 < 1.0 < 0.75 < 0.5 (1,587.7 / 1,618.1 / 1,620.6 / 1,641.0), on seeds 0-2 at the new prices it is 1.0 < 0.75 < 0.6 < 0.5 with the three larger packs within 13 USD of each other. Only paired differences on equal seeds are informative (Section 3.2).
6. **Seed effects dominate levels.** Unpaired CIs on system-cost levels are +-150 to +-360 USD (n = 3) while the paired pack differences at the optimum are 5-51 USD. All statements below use paired differences.
7. **The rule's cost is not monotone in resources.** A fourth spare per site makes the rule's operation worse on single seeds (10 bikes, 0.6 kWh, seed 1: -0.95 USD per spare; 1.0 kWh, seed 2: -1.37), and at 4 bikes a third spare costs the rule 19.1 USD per spare on seed 2 at 0.6 kWh. These are weaknesses of the rule baseline, not lever effects.
8. **M2+M3 equals M2 on all 192 instances** (no transport services exist on this grid), so the best rule is min(r2, M2). Which of the two is best changes with the prices on 27 of the 144 pack-stage instances (15 from r2 to M2, 12 from M2 to r2), by repricing alone.
9. **Stage run.** 144 cases in 497.9 s against a 2,700 s budget (estimate 15 min), no skipped, no error, every rule row OK; all 144 case keys have their 4 rows. The fleet folder still carries 16 orphan case notes from the failed server retry in `cases_orphans.jsonl`; `cases.jsonl` (48 notes) is clean and is what the join reads.

## 2. Coverage

- **Pack stage (new prices):** 3 packs x 16 designs x 3 seeds = 144 instances; 576 records = r2, M2, M2+M3 and the best-rule row per instance, all status OK; no ILP (by plan: the rules do not read the prices, so the stage reprices identical schedules); no SKIPPED_BUDGET, no ERROR; wall 497.9 s. The recorded `best_rule_total_end_adjusted_min` equals the recomputed end-adjusted minimum on 144 of 144 instances (192 of 192 with the fleet grid).
- **0.6 kWh grid (new prices, `r6_penalty/fleet`):** 48 instances, rules + one ILP each; time limit 300 s at 4 and 6 bikes, 600 s at 8 and 10 bikes, 600 s for the 13 retried rows. The ILP end-adjusted totals and best-rule minima recomputed here agree with the pipeline's `fleet/cases_wide.csv` to 1e-12.
- **Legacy prices (round 5):** 0.5 / 0.75 / 1.0 kWh: 48 instances each (16 designs x seeds 0-2), rules only; 0.6 kWh: 24 instances (4-8 bikes x 1-4 spares, seeds 0-1; the 6-bike / 2-spare cell comes from the core records, which carry no allocated cost, so the constant 88.94 USD is used), rules + ILP (23 OPTIMAL, 1 TIME_LIMIT at 0.33 %). Implied prices from the rows: P 30, w 18, v 36 (legacy) and P 60, w 18, v 15 (new).
- **Repricing identity:** for every (design, seed, rule) the pack-stage row and the legacy row have the same served count, swaps, bike-km, kWh, response cost, travel, electricity, set-up and end adjustment; the lateness cost is x 15/36 and the unserved cost x 2 (432 of 432 rows; worst residual of `new - legacy = 30 x unserved orders - 21 x lateness hours` is 5e-13 USD).

**Table 1. ILP solve status at 0.6 kWh after the retries (reference grid).**

| K | time limit (s) | ILPs | OPTIMAL | TIME_LIMIT | retried rows in force | MIP gaps of TIME_LIMIT rows (%) |
|---|---|---|---|---|---|---|
| 4 | 300 (600 retried) | 12 | 4 | 8 | 7 | 0.33, 0.50, 0.62, 0.76, 0.86, 0.90, 1.04, 1.56 |
| 6 | 300 (600 retried) | 12 | 5 | 7 | 5 | 0.35, 0.54, 0.63, 0.76, 0.81, 0.87, 1.54 |
| 8 | 600 | 12 | 9 | 3 | 0 | 0.31, 0.62, 1.34 |
| 10 | 600 | 12 | 11 | 1 | 1 | 100.51 (anomaly 3) |

## 3. Answer

### 3.1 Cost-minimal best-rule design per pack size

**Table 2. Best rule, cost-minimal design per pack (system cost in USD per 4-h window, seed mean and exact-t 95 % CI; per-seed argmins in brackets).**

| prices | pack (kWh) | n | design (seed-mean argmin) | system cost | served share | runner-up | per-seed argmin (system cost, served) |
|---|---|---|---|---|---|---|---|
| new (P 60, v 15) | 0.50 | 3 | K 10 / B 4 | 1,684.9 [1,530.4, 1,839.4] | 0.993 | K 8 / B 4 (+27.6) | s0 K 8 / B 4 (1,512.7, 97.9 %); s1 K 10 / B 4 (1,724.3, 97.9 %); s2 K 10 / B 4 (1,717.2, 100 %) |
| new | 0.60 | 3 | K 8 / B 4 | 1,619.6 [1,256.2, 1,983.0] | 0.979 | K 10 / B 4 (+57.4) | s0 K 8 / B 4 (1,453.3, 100 %); s1 K 8 / B 4 (1,676.8, 97.9 %); s2 K 10 / B 4 (1,671.8, 100 %) |
| new | 0.75 | 3 | K 8 / B 4 | 1,611.8 [1,264.7, 1,959.0] | 0.986 | K 10 / B 4 (+63.5) | s0 K 8 / B 4 (1,453.5, 100 %); s1 K 8 / B 4 (1,718.0, 97.9 %); s2 K 10 / B 4 (1,657.3, 100 %) |
| new | 1.00 | 3 | K 8 / B 4 | 1,606.8 [1,318.0, 1,895.6] | 0.986 | K 8 / B 3 (+7.2) | s0 K 8 / B 3 (1,473.2, 100 %); s1 K 8 / B 4 (1,697.7, 97.9 %); s2 K 8 / B 4 (1,646.9, 97.9 %) |
| legacy (P 30, v 36) | 0.50 | 3 | K 10 / B 4 | 1,688.3 [1,519.8, 1,856.9] | 0.993 | K 8 / B 4 (+10.1) | s0 K 8 / B 4; s1 K 10 / B 4; s2 K 10 / B 4 |
| legacy | 0.60 | 2 | K 8 / B 4 | 1,587.7 (n = 2) | 0.990 | K 8 / B 3 (+55.5) | s0 K 8 / B 4; s1 K 8 / B 4 |
| legacy | 0.75 | 3 | K 8 / B 4 | 1,647.8 [1,220.7, 2,075.0] | 0.986 | K 10 / B 4 (+28.0) | s0 K 8 / B 4; s1 K 10 / B 4; s2 K 10 / B 4 |
| legacy | 1.00 | 3 | K 8 / B 4 | 1,637.5 [1,286.9, 1,988.2] | 0.986 | K 8 / B 3 (+11.3) | s0 K 8 / B 3; s1 K 8 / B 4; s2 K 8 / B 4 |

On seed 1 one order is unservable for every policy, so 97.9 % = 47 of 47 servable orders. The rule's optimum lies on the spare edge of the grid (B = 4) at 0.5-0.75 kWh on every seed and at 1.0 kWh on seeds 1-2; at 1.0 kWh seed 0 prefers 3 spares, and the two spare levels differ by 7.2 USD in seed means. At 0.5 kWh the optimum is also on the fleet edge (K = 10) on seeds 1-2. The full grids (means, CIs, served shares) are in the appendix and in Figure 3.

### 3.2 Effect of the pack size (paired per seed, new prices)

**Table 3. Best-rule system cost of a pack minus the 0.6 kWh pack (USD per window; mean [95 % CI], n = 3; per seed).**

| comparison level | 0.5 kWh | 0.75 kWh | 1.0 kWh |
|---|---|---|---|
| each pack at its own per-seed cost-minimal design | +50.8 [32.1, 69.4] (+59.4, +47.5, +45.4); dearer on 3/3 seeds | +9.0 [-62.8, 80.7] (+0.2, +41.2, -14.5) | +5.3 [-59.6, 70.2] (+19.9, +20.9, -24.9) |
| at 8 bikes, 4 spares per site (the rule's seed-mean design) | +92.9 [20.3, 165.5] (+59.4, +112.9, +106.4); 3/3 | -7.8 [-140.4, 124.9] (+0.2, +41.2, -64.7) | -12.8 [-161.2, 135.6] (+22.4, +20.9, -81.8) |
| at 10 bikes, 4 spares | +7.9 [-78.1, 93.8] | -1.7 [-30.4, 27.1] | +18.5 [-34.9, 71.9] |
| at 6 bikes, 2 spares | +18.6 [-169.0, 206.3] | -112.6 [-301.7, 76.6]; cheaper on 3/3 | -103.2 [-287.3, 81.0]; cheaper on 3/3 |
| at 4 bikes, 2 spares | +36.4 [10.3, 62.6]; 3/3 | +62.7 [-90.9, 216.2] | +11.3 [-75.9, 98.4] |
| mean over the 16 designs | +34.0 [-1.8, 69.8] (+23.2, +28.4, +50.4); dearer on 3/3 | -3.7 [-135.1, 127.6] (+35.4, +17.2, -63.9) | -72.4 [-177.9, 33.0] (-38.1, -59.3, -119.9); cheaper on 3/3 |
| design-seed pairs where the pack is cheaper than 0.6 kWh | 18 of 48 | 22 of 48 | 30 of 48 |

Shown: a 0.5 kWh pack costs the rule more than 0.6 kWh at its best design on every seed (3.1 %), and the two larger packs change the rule's best system cost by less than the seed noise (the CIs span -60 to +80 USD). The larger packs matter where the system is short of resources: the five largest seed-mean savings of 1.0 kWh over 0.6 kWh are 231.5 USD at 6 bikes / 1 spare, 212.6 at 10 / 1, 136.3 at 8 / 1, 135.7 at 8 / 2 and 126.1 at 10 / 2, while the five largest losses of 0.5 kWh are all at 8 bikes (131.7 at 8 / 1, 121.5 at 8 / 2, 92.9 at 8 / 4, 76.3 at 8 / 3) and 74.8 at 8 / 1 for 0.75 kWh. With 4 bikes the pack size hardly matters (every pack serves 47-62 % and costs 2,380-2,650 USD): the fleet, not the battery, binds there.

**Table 4. Where the pack effect comes from: 1.0 kWh minus 0.5 kWh at 8 bikes and 4 spares per site (best-rule schedules, paired per seed, n = 3).**

| quantity | new prices (P 60, v 15) | legacy prices (P 30, v 36) |
|---|---|---|
| unserved orders per window | -2.00 [-4.48, 0.48] (-1, -2, -3) | same schedules |
| swaps per window | -6.0 [-10.3, -1.7] (-4, -7, -7) | same |
| mean station time per bike (min) | -3.19 [-4.21, -2.17] | same |
| stock-out slot-sites | -11.3 [-35.2, 12.5] | same |
| response hours (served orders) | +1.22 [0.24, 2.20] | same |
| lateness hours | -0.72 [-3.15, 1.71] | same |
| unserved-order penalty (USD) | -120.0 [-269.1, 29.1] | -60.0 [-134.5, 14.5] |
| response cost (USD) | +22.0 [4.4, 39.6] | +22.0 [4.4, 39.6] |
| lateness cost (USD) | -10.8 [-47.2, 25.6] | -26.0 [-113.3, 61.3] |
| spare and site set-up (USD) | +3.32 (12 spares x 0.277 USD) | +3.32 |
| electricity + travel + end adjustment (USD) | -0.19 | -0.19 |
| system cost (USD) | **-105.7 [-295.9, 84.5]** (-36.9, -92.0, -188.2) | **-60.9 [-228.8, 107.1]** (-6.9, -39.0, -136.7) |

The larger pack lets the rule serve one to three more of the 48 orders with four to seven fewer swaps; the extra served orders are the hard ones, so response hours rise. Everything that is not an order price is below 4 USD. The price difference is exact on every seed: (-36.9) - (-6.9) = -30 = 30 x (-1) - 21 x 0; (-92.0) - (-39.0) = -53.0 = 30 x (-2) - 21 x (-0.33); (-188.2) - (-136.7) = -51.5 = 30 x (-3) - 21 x (-1.83). Averaged over the 16 designs the picture is the same: 1.0 minus 0.5 kWh saves 106.4 [-247.6, 34.7] USD at the new prices against 37.5 [-150.1, 75.0] at the legacy prices, from -2.3 unserved orders, -5.3 swaps and -9.0 min station time per bike (new-price best-rule schedules; the legacy best rule differs on a few cells, so the legacy operating differences differ in the second decimal). The 0.5 minus 0.6 kWh step at 8 bikes / 4 spares is +1.67 unserved orders (+100 USD), -15 USD response, +8.8 USD lateness, -0.66 USD set-up.

### 3.3 Marginal values of the best rule by pack size

**Table 5. Saving per extra bike (V(K) - V(K+2)) / 2 against 88.94 USD, and net value of one more spare per site (V(B) - V(B+1)) / 3, V = end-adjusted operating total; mean [95 % CI], n = 3; new prices.**

| step | 0.5 kWh | 0.6 kWh | 0.75 kWh | 1.0 kWh |
|---|---|---|---|---|
| bike 4 -> 6 (4 spares) | 308.8 [88.3, 529.3]; pays 3/3 | 293.2 [105.7, 480.7]; 3/3 | 335.1 [207.2, 463.0]; 3/3 | 322.0 [92.7, 551.3]; 3/3 |
| bike 6 -> 8 (4 spares) | 220.9 [74.5, 367.3]; 3/3 | 268.0 [115.3, 420.7]; 3/3 | 262.5 [124.0, 401.0]; 3/3 | 255.4 [73.3, 437.5]; 3/3 |
| bike 8 -> 10 (4 spares) | 102.7 [-38.9, 244.3] (38.7, 121.6, 147.9); pays 2/3 | 60.2 [-74.6, 195.0]; 1/3 | 57.2 [-50.3, 164.7]; 1/3 | 44.6 [-19.8, 109.0]; 0/3 |
| spare 1 -> 2 (8 bikes) | 178.7 [98.5, 258.9] | 175.3 [90.3, 260.3] | 199.8 [63.0, 336.6] | 175.1 [127.7, 222.5] |
| spare 2 -> 3 (8 bikes) | 86.4 [-55.2, 228.0] | 71.3 [-74.5, 217.1] | 78.4 [-77.4, 234.2] | 54.4 [-18.3, 127.1] |
| spare 3 -> 4 (8 bikes) | 20.9 [-11.7, 53.5] (16.0, 35.8, 10.9); positive 3/3 | 26.4 [-29.0, 81.8] (1.3, 34.0, 44.0); 3/3 | 22.3 [-56.8, 101.4] (3.1, 59.0, 4.7); 3/3 | 2.4 [-9.6, 14.4] (-0.85, 7.95, 0.08); 2/3 |
| spare 3 -> 4 (10 bikes) | 29.2 [-76.1, 134.5] | 13.4 [-45.5, 72.3] | 3.4 [-4.9, 11.7] | -0.3 [-2.6, 2.0] (0.42, -0.01, -1.37) |
| spare 2 -> 3 (4 bikes) (the legacy -9.33 sentence) | -1.7 [-16.9, 13.5] (5.4, -5.6, -4.8) | +0.7 [-42.0, 43.4] (11.8, 9.4, -19.1) | -2.4 [-16.5, 11.7] | -1.8 [-7.2, 3.5] |

Shown: bikes 5-8 pay the rule at every pack size on every seed (221-335 USD per bike against 88.94). The ninth and tenth bike pay the rule only at 0.5 kWh (on 2 of 3 seeds), which is why its optimum moves to 10 bikes there. Spares are the cheaper lever per dollar wherever they have value (a bike costs as much as 321 / 268 / 214 / 161 spares); the fourth spare per site pays the rule at 0.5-0.75 kWh (positive on 3 of 3 seeds, 21-26 USD) but is worth about nothing at 1.0 kWh (2.4 USD at 8 bikes, -0.3 at 10). The spare-edge caveat of the fleet report (the rule's true optimum may need more than 4 spares per site) therefore applies at 0.5-0.75 kWh and not at 1.0 kWh. Legacy comparison (recomputed from the round-5 records, `figs/pack_marginal_values.csv`): at the legacy prices the same steps gave the rule 73-94 USD per bike for 8 -> 10 at 0.5 kWh (3-4 spares) and 7.9 / 18.5 (n = 2) / 23.0 / 3.8 USD for the fourth spare at 8 bikes at 0.5 / 0.6 / 0.75 / 1.0 kWh; the schedules are the same, the values are repriced, and the 1.0 kWh fourth spare was already worth about nothing.

### 3.4 Legacy sentence on the negative value of a spare

The manuscript's pack-size paragraph (legacy prices) states that at 4 bikes and 2 spares per site a further spare has a negative net value of -9.33 USD per spare at 0.5 kWh (-12.79 to -5.88) and -5.19 USD at 0.6 kWh (n = 2). Repriced, the 0.5 kWh value is -1.7 [-16.9, 13.5] USD (per seed +5.4, -5.6, -4.8), the 0.6 kWh value +0.7 [-42.0, 43.4] (n = 3), 0.75 kWh -2.4 [-16.5, 11.7], 1.0 kWh -1.8 [-7.2, 3.5]. The schedules are the same; at the legacy prices the third spare's extra lateness (v 36) outweighed the orders it served (P 30), at the new prices it does not. No design-seed cell at 4 bikes shows a significant negative spare value any more; the rule's non-monotonicity survives only on single seeds (anomaly 7).

### 3.5 Rule designs at every pack size against the ILP at 0.6 kWh

The ILP was run at 0.6 kWh only. After the retries its per-seed cost-minimal designs are K 6 / B 2 (1,321.5 USD, seed 0), K 8 / B 2 (1,535.8, seed 1) and K 8 / B 3 (1,494.2, seed 2), all OPTIMAL and certified against every other cell by the solver bounds (fleet final report, Section 3.2); the lowest incumbent mean is K 8 / B 3, 1,477.9 [1,307.6, 1,648.1] (not certified against K 8 / B 2 at 1,478.1 and K 6 / B 2 at 1,478.5).

**Table 6. Best rule at its own per-seed cost-minimal design of each pack minus the ILP at its per-seed cost-minimal 0.6 kWh design (paired, n = 3).**

| rule pack (kWh) | difference (USD per window) | per seed | relative to the rule's cost | served-share difference (points) | rule at K 8 / B 4 minus ILP at K 8 / B 3 |
|---|---|---|---|---|---|
| 0.5 | 200.9 [153.2, 248.5] | +191.2, +188.5, +223.0 | 12.2 % [9.5, 14.9] | -0.7 [-3.7, 2.3] | 234.6 [-54.8, 524.0] |
| 0.6 | 150.1 [90.0, 210.2] | +131.8, +141.0, +177.6 | 9.4 % [6.5, 12.2] | 0.0 | 141.7 [-86.6, 370.0] |
| 0.75 | 159.1 [96.2, 222.0] | +132.0, +182.2, +163.1 | 9.8 % [8.0, 11.7] | 0.0 | 133.9 [-45.4, 313.3] |
| 1.0 | 155.4 [141.5, 169.3] | +151.7, +161.9, +152.7 | 9.7 % [8.4, 11.0] | -0.7 [-3.7, 2.3] | 128.9 [8.4, 249.4] |

Shown: whatever pack the rule gets, its cost-minimal design costs 150-201 USD per window (9.4-12.2 %) more than the coordinated 0.6 kWh design at the same served share, on every seed (the smallest per-seed margin is 131.8 USD). The 0.6 kWh row is the fleet report's 9.4 % design gap. Not shown: how much the ILP itself would gain from a larger pack; it already serves 98-100 % at its design, so its gain can only come from fewer swaps and shorter station time, which are worth a few USD per window under the ILP (fleet report, levers), whereas the rule's gain is unserved orders.

## 4. Comparison with the legacy-price results on the same instances

Same 144 instances at 0.5 / 0.75 / 1.0 kWh (seeds 0-2) and 24 at 0.6 kWh (seeds 0-1); identical demand hashes; identical rule schedules (Section 2). Levels are not comparable across price regimes; designs, served shares and paired differences are.

| | legacy prices (round 5) | new prices (this stage) |
|---|---|---|
| best-rule cost-minimal designs | 0.5: K 10 / B 4; 0.6: K 8 / B 4 (n = 2); 0.75, 1.0: K 8 / B 4 | unchanged (the rules do not read the prices) |
| best-rule system cost at the design | 1,688.3 / 1,587.7 (n = 2) / 1,647.8 / 1,637.5 | 1,684.9 / 1,619.6 / 1,611.8 / 1,606.8 (n = 3 each) |
| spread over the four packs | 100.6 USD, with the 0.6 kWh n = 2 row lowest | 78.1 USD, monotone in the pack: 1.0 < 0.75 < 0.6 < 0.5 |
| 1.0 minus 0.5 kWh at the per-seed best design | -10.5 [-156.3, 135.4] (-11.2, +48.6, -68.8) | -45.5 [-101.2, 10.3] (-39.5, -26.6, -70.3) |
| 0.75 minus 0.5 kWh at the per-seed best design | -23.5 [-183.0, 135.9] | -41.8 [-118.1, 34.6] |
| 1.0 minus 0.5 kWh at 8 bikes / 4 spares | -60.9 [-228.8, 107.1] | -105.7 [-295.9, 84.5] |
| 1.0 minus 0.5 kWh, mean over 16 designs | -37.5 [-150.1, 75.0]; cheaper in 28 of 48 pairs | -106.4 [-247.6, 34.7]; cheaper in 40 of 48 pairs |
| 0.75 minus 0.5 kWh, mean over 16 designs | +13.1 [-92.2, 118.4]; 19 of 48 | -37.7 [-204.9, 129.4]; 30 of 48 |
| spare 2 -> 3 at 4 bikes, 0.5 kWh | -9.33 [-12.79, -5.88] | -1.7 [-16.9, 13.5] |
| served share at the designs | 0.986-0.993 | identical |

- The sign of every pack effect is the same at both prices where it is measurable; the new prices roughly double its size because the effect is unserved orders (P 30 -> 60) and the lateness component, which worked against the larger pack at v 36, is now smaller (v 15).
- The legacy table's impression that 0.6 kWh is the cheapest pack (by 50-100 USD) came from comparing an n = 2 row with n = 3 rows (anomaly 5). With three seeds at every pack the 0.6 kWh design is 5-13 USD dearer than the larger packs and 51 USD cheaper than 0.5 kWh.
- Legacy statements that change: "pack size matters less than fleet and spares (the rule's best system cost differs by about 100 USD across 0.5-1.0 kWh)" stays true in spirit with 78 USD, but the shape is now monotone and the 0.5 kWh penalty is the only measurable part; the significant negative spare value at 4 bikes and 2 spares is gone.

## 5. Interpretation

**Shown by the records (n = 3, paired per seed):**

- At the new prices the best rule's cost-minimal design is 8 bikes and 4 spares per site for 0.6-1.0 kWh and 10 bikes and 4 spares for 0.5 kWh; its system cost is 1,606.8-1,684.9 USD per window, monotone in the pack, with 97.9-99.3 % of orders served.
- A 0.5 kWh pack costs the rule 50.8 [32.1, 69.4] USD more than 0.6 kWh at the best design (3.1 %, all three seeds); 0.75 and 1.0 kWh do not lower the rule's best system cost measurably (5-9 USD, CIs +-70 USD).
- Off the optimum the larger pack is worth a lot to the rule (72 USD per window averaged over the grid for 1.0 vs 0.6 kWh; 136-231 USD at one spare per site), through fewer swaps, less station time and fewer unserved orders; every non-order cost component moves by less than 4 USD.
- The rule-side pack results are price-independent in their schedules and change only by repricing: the exact identity new minus legacy = 30 USD per unserved order minus 21 USD per lateness hour holds on all 432 rule rows, and doubles the 1.0 vs 0.5 kWh saving at the rule's design from 60.9 to 105.7 USD.
- At every pack size the rule's cost-minimal design remains 150-201 USD (9.4-12.2 %) above the ILP's 0.6 kWh design at the same service.
- The fourth spare per site pays the rule 21-26 USD at 0.5-0.75 kWh and 2.4 [-9.6, 14.4] USD at 1.0 kWh; the significant negative spare value of the legacy pack paragraph (-9.33 USD) does not survive the prices (-1.7 [-16.9, 13.5]).

**Suggested, not shown:**

- *Pack size substitutes for spares and for coordination only partly.* At 1.0 kWh the rule's spare demand saturates (the fourth spare and the ninth bike no longer pay, the optimum is interior in spares on one seed), so the spare-edge caveat of the fleet report weakens with the pack. Whether the rule would still gain from a fifth spare at 0.5-0.75 kWh was not tested.
- *The ILP's pack effect is unknown.* No ILP was solved at 0.5, 0.75 or 1.0 kWh. Because the ILP already serves 98-100 % at its 0.6 kWh design, its gain from a larger pack is probably small (station time and swaps), so the rule-vs-ILP design gap at a common larger pack is probably not far from the 9.4 % measured at 0.6 kWh; this is an inference, not a measurement. The comparison in Table 6 is rule-at-pack-p against ILP-at-0.6-kWh.
- *Charger power.* The pack was varied at fixed charger power, so a larger pack charges longer and its 48-order window ends with more energy in the system; part of the swap reduction is a longer effective range, part is that fewer full charges complete inside the window. The written-target runs of the stress stage, not this one, would show whether the larger pack's advantage survives an end-of-window energy target.
- *n = 3 and seed 2.* Seed 2 drives the larger-pack savings at 8 bikes / 4 spares (-65 to -82 USD against +0 to +41 on seeds 0-1). With three seeds the sign of the 0.75 / 1.0 kWh effect at the optimum is not established; the 0.5 kWh penalty is.

## 6. Figures (`figs/`, PDF vector and PNG 300 dpi; script `figs/make_pack_figs.py`, reader `figs/pack_analysis.py`)

1. `fig_pack_size_curve` (7.2 x 3.0 in). *(a) Best-rule system cost (end-adjusted operating cost plus 88.94 USD per bike and window) against fleet size at the best spare level per seed, one curve per pack size (0.5, 0.6, 0.75, 1.0 kWh), and the ILP at 0.6 kWh (dashed); means with exact-t 95 % CIs (n = 3) and seeds as small dots; rings mark each curve's lowest mean (the ILP's 6 and 8 bikes tie and the ring is not certified). (b) Served share at the same designs.* The four rule curves lie on top of each other from 4 to 8 bikes and separate only at 10 bikes (0.5 kWh keeps falling); the ILP curve is 150-200 USD lower at 6-8 bikes.
2. `fig_pack_effect` (7.2 x 3.2 in). *(a) Paired difference in best-rule system cost between a pack and the 0.6 kWh pack at the new prices, at each pack's per-seed cost-minimal design, at 8 bikes and 4 spares per site, and averaged over the 16 designs; bars are means, error bars exact-t 95 % CIs (n = 3), dots seeds. (b) The 1.0 minus 0.5 kWh difference at 8 bikes and 4 spares by cost component at the new prices (filled) and the legacy prices (hatched).* Panel (b) shows the pack effect to be the unserved-order penalty, doubled by the price change, with every other component within +-25 USD.
3. `fig_pack_design_map` (7.2 x 6.2 in). *Best-rule system cost above the pack's cost-minimal design over fleet size x spares per site at the new prices, seed means (n = 3), one panel per pack size; each cell gives the excess in USD per window and the served share; the box marks the lowest seed mean, triangles the seeds whose own cost-minimal design is that cell.* The minimum sits on the 4-spare edge at 0.5-0.75 kWh and on the 3-4 spare plateau at 1.0 kWh; the one-spare column is where the pack size matters most.

Colours: the four pack sizes on a single-hue orange ordinal ramp (light = 0.5 kWh, dark = 1.0 kWh; validated with the dataviz palette script in ordinal mode: monotone lightness, step gaps >= 0.06, light end 2.2:1 on white), the ILP in the Okabe-Ito blue of the fleet figures, legacy prices hatched; identity is also carried by marker shape and the legend.

Data files written by the reader (in `figs/`): `pack_per_instance_new.csv` (192 rows: 144 pack-stage + 48 fleet instances, rule costs, best rule, components, ILP columns at 0.6 kWh), `pack_per_instance_legacy.csv` (168 rows), `pack_design_by_pack.csv`, `pack_effect.csv`, `pack_decomposition.csv`, `pack_marginal_values.csv`, `pack_rule_vs_ilp.csv`, `pack_grid_means.csv`, `pack_grid_means_legacy.csv`, `pack_analysis_output.md`.

## 7. Manuscript items replaced (`manuscript/PENDING_R6.md`)

**Item 8** ("Pack-size axis of the fleet sweep (0.5, 0.75, 1.0 kWh, best rule, n 3): last sentence of the fleet paragraph in 6.6, legacy rows of Table tab:res:sizing, Section S8.3 pack-size paragraph, panels (a) and (c) of fig:res:isocost and the hatched bars of fig:app:fleet-marginal (legacy n 2 grid)") is replaced on the rule side in full; the status changes from `labelled` to done for the text and table items. New statements:

- *Section 6.6, last sentence of the fleet paragraph* (replaces "Pack sizes of 0.5-1.0 kWh were swept for the rule at the legacy prices only (best system cost 1,587.7-1,688.3 USD; Section S8.3)"): "Pack sizes of 0.5-1.0 kWh were swept for the best rule at the calibrated prices (seeds 0-2, n = 3; Section S8.3): its cost-minimal system cost falls from 1,684.9 USD at 0.5 kWh (10 bikes, 4 spares per site) to 1,619.6 at 0.6, 1,611.8 at 0.75 and 1,606.8 USD at 1.0 kWh (8 bikes, 4 spares), a 0.5 kWh pack costs 50.8 USD (32.1-69.4) more than 0.6 kWh at the per-seed cost-minimal design and the larger packs no measurable amount less (9.0 and 5.3 USD, CIs about +-70 USD), and at every pack size the rule's cost-minimal design remains 150-201 USD (9.4-12.2 %) above the ILP's 0.6 kWh design at the same served share."
- *Table tab:res:sizing*: replace the four rows "Best rule, legacy prices" by calibrated-price rows, n = 3 each: 0.50 | 10, 4 | 1684.9 (1530.4-1839.4) | 0.993; 0.60 | 8, 4 | 1619.6 (1256.2-1983.0) | 0.979 (already present); 0.75 | 8, 4 | 1611.8 (1264.7-1959.0) | 0.986; 1.00 | 8, 4 | 1606.8 (1318.0-1895.6) | 0.986. Caption: "Grid: 4-10 bikes and 1-4 spares per site at every pack size" (drop "4-8 bikes at 0.6 kWh and 4-10 at the other pack sizes at the legacy prices"); the sentence "at the legacy prices every cost-minimal design lay on the edge of the tested grid" can stay for the two remaining legacy ILP rows (1,310.1 and 1,448.8 USD), which are not part of item 8 and keep their label.
- *Section S8.3, paragraph "Pack size (legacy prices, P 30 / v 36)"* becomes "Pack size": "The best rule was also evaluated for 4-10 bikes, 1-4 spares per site and packs of 0.5, 0.75 and 1.0 kWh at the calibrated prices (seeds 0-2, n = 3; the pack is varied at a fixed 25 Wh energy step and fixed charger power, and the spare set-up scales with the pack). Its cost-minimal design is 8 bikes and 4 spares per site at 0.6-1.0 kWh and 10 bikes and 4 spares at 0.5 kWh (Table tab:res:sizing); the system cost is monotone in the pack, 1,684.9, 1,619.6, 1,611.8 and 1,606.8 USD per window, serving 97.9-99.3 % of orders. Paired per seed at each pack's cost-minimal design, 0.5 kWh costs 50.8 USD (32.1-69.4) more than 0.6 kWh on every seed, 0.75 and 1.0 kWh 9.0 (-62.8 to 80.7) and 5.3 USD (-59.6 to 70.2) more, so pack size above 0.6 kWh does not change the rule's best system cost measurably; away from the optimum a 1.0 kWh pack saves the rule 72.4 USD per window on average over the 16 designs (-177.9 to 33.0; cheaper on all three seeds), up to 136-231 USD with one spare per site. The effect is an unserved-order effect: at 8 bikes and 4 spares the 1.0 kWh pack serves 2.0 more orders than 0.5 kWh (-0.5 to 4.5) with 6.0 fewer swaps and 3.2 min less station time per bike, saving 120 USD of penalty against 3.3 USD more spare set-up and under 1 USD in electricity, travel and end adjustment; since the rules' schedules are identical at both prices, the same step saved 60.9 USD at the legacy prices and saves 105.7 USD now (the difference is exactly 30 USD per unserved order less 21 USD per lateness hour). The fourth spare per site pays the rule 21-26 USD at 0.5-0.75 kWh but only 2.4 USD (-9.6 to 14.4) at 1.0 kWh, where the ninth and tenth bike no longer pay either, so the spare-edge caveat applies to the smaller packs only. At 4 bikes and 2 spares per site a further spare is worth -1.7 USD (-16.9 to 13.5) at 0.5 kWh and -1.8 USD (-7.2 to 3.5) at 1.0 kWh; the significant negative value found at the legacy prices (-9.33 USD) was a property of the lateness price. At every pack size the rule's cost-minimal design costs 150-201 USD (9.4-12.2 %) more than the ILP's cost-minimal 0.6 kWh design at the same served share (0.5 kWh: 200.9, 153.2-248.5; 0.75: 159.1, 96.2-222.0; 1.0: 155.4, 141.5-169.3); the ILP was not solved at the other pack sizes."
- *fig:res:isocost panels (a) and (c), fig:app:fleet-marginal hatched bars*: these are the legacy-price 0.6 kWh ILP and rule panels (n = 2), not pack-size results; this stage adds no ILP at other packs and cannot replace panel (a) or the hatched ILP bars, which remain a labelled legacy comparison unless the author drops them. The new `fig_pack_design_map` (rule at four pack sizes, calibrated prices, n = 3) can be added to S8.3 as the pack-size counterpart of panel (d); `fig_pack_size_curve` and `fig_pack_effect` are the candidates for the S8.3 text.
- *Section 7 (07_discussion.tex, paragraph on the calibration choice)*: remove "pack sizes" from the list of experiments "reported only at the legacy prices".
- *Item 15 / Table tab:app:coverage-legacy and the S4 coverage row* "Fleet x spare x pack sweep, 48 orders (0.5, 0.75 and 1.0 kWh; 0.6 kWh at the legacy prices) | ILP 0-1 (2); rules 0-2 (3) | 300 s (4-6 bikes); 600 s (8 bikes) | legacy": move to the calibrated block as "Fleet x spare x pack sweep, 48 orders, 0.5, 0.75 and 1.0 kWh (best rule only; 0.6 kWh with the ILP in the fleet grid) | rules 0-2 (3) | no solve | calibrated".
- *R6 digest row 72* ("Negative net value of a rule spare ... pack sizes: rerun needed"): answered as above (no significant negative value at the calibrated prices; single-seed non-monotonicity remains).

Items not touched by this stage: 5-7 (stress), 9 (levers), 16 (the fleet retries are used here as the reference grid but reported by the fleet stage), 20.
