# R6 stage rl: PPO station-layer comparator retrained at the new prices (final report)

Question. The PPO agent was retrained with the new order prices (unserved penalty P = 60 USD, response price
w = 18 USD/h from release, lateness price v = 15 USD/h from the promise). How does it compare with never-charge,
its own rule station layer, the best rule and the relaxed ILP, including served share? Does it still collapse to
never-charge, and does its round-5 advantage over the best rule (artefact a) disappear? What is the training trend,
and how do these results compare with round 5 (old prices P 30, v 36)?

Sources. `outputs/r6_penalty/rl/records.jsonl` (264 lines, 264 unique keys `(kind, family, seed, method)`; the last
record per key is used) and `models/*/monitor.csv`. Round 5: `outputs/r5_x7_rl/records.jsonl` (284 lines, 284 keys)
and its `models/*/monitor.csv`. Every number below is recomputed from these files by `figs/make_rl_report.py` (no
solves and no new simulation), which also writes `figs/rl_tables.json` and the figures. The auto-generated
`RESULTS.md` was checked against these numbers (Appendix B).

Terminology. Families: **nyc4h-stress** (code `nyc4h_stress2`: 6 bikes, 36 orders, 3 sites) and **stress4h** (code
`r5_stress4h`: 6 bikes, 48 orders, 3 sites, TOU tariff). Rider layers: **r2** and **M2+M3** (code `r5`). PPO
controls only station charging: one binary charge decision per site and slot, action space `MultiDiscrete([2 2 2])`.
These families have no transfer services, so M3 never fires and rule M2 equals rule M2+M3 on every seed (max
difference 0.00 USD). **Own rule station layer** = the rule station layer run inside the RL environment
(`replay[r]`). It equals rule r2 or rule M2+M3 exactly on all 40 seed-rider pairs. **Never charge** /
**charge ASAP** = fixed station heuristics on the same rider layer. On these families charge ASAP is the constant
action "charge at every site in every slot". **Best rule** = per-seed minimum of the end-adjusted cost over rules
r2, M2 and M2+M3. Headline cost = E2 total (26) + M1 end-state adjustment (**end-adjusted**), relaxed end targets
(rho = 0, R_end = 0). **Gap** = 100 (policy - ILP) / policy per seed, then averaged. Intervals are exact Student-t
95 % CIs over the n = 10 test seeds (t_0.975,9 = 2.262), written `mean ± half-width`. Every difference is paired by
seed. p values come from two-sided paired t-tests and are not corrected for multiplicity. USD figures are per 4-h
window.

---

## 1. Problems and anomalies

1. **The collapse to never-charge persists for M2+M3 riders on stress4h, and it is no longer explained by the
   prices.** The deterministic PPO policy serves exactly as many orders as never-charge on 8 of 10 seeds (one more
   order on seeds 3 and 6). Its cost is within 0.5 USD of never-charge on 8 seeds and identical on 5. It buys
   0.84 kWh per window (range 0.61-1.08) against 2.77 kWh for its own rule. At the new prices this behaviour costs
   189.48 ± 75.85 USD more than the best rule. The constant charge-ASAP action, which lies inside PPO's action
   space, is cheaper than PPO on 10 of 10 seeds by 176.50 ± 54.53 USD. Under the new prices this is therefore a
   learning failure, not an artefact of the objective.
2. **The training trend on stress4h is flat or adverse.** With instance fixed effects, the stochastic training
   policy's change from the first to the last 100 episodes is -7.9 USD for r2 riders (block-clustered CI
   [-28.9, 13.1]) and **+27.0 USD for M2+M3 riders** ([10.9, 43.1]; it got worse). At the old prices both
   stress4h runs improved by 47-53 USD. On nyc4h-stress training clearly helps: -189.5 and -270.1 USD.
3. **The raw training numbers in the auto `RESULTS.md` mislead.** The "return first 100 / last 100" columns are in
   reward units (-0.1 x USD) and are confounded by which training instances are drawn. On stress4h they suggest a
   worsening (r2: -180.31 to -197.42, i.e. +171 USD), but +177.9 USD of that is a harder instance mix in the last
   block. The instance-adjusted trends in Section 4.6 should be used instead.
4. **Auto `RESULTS.md` header (cosmetic).** The header describes `ilp_written` and a price of recovery, but the
   stage ran with `--no-written` (by design, `r6_penalty.run_rl`). There are no written-target ILP rows, so this
   stage has no price of recovery. All other numbers in `RESULTS.md` reproduce (Appendix B).
5. **ILP time limits on stress4h.** 5 of 10 relaxed ILPs hit the 300 s limit (seeds 1, 2, 3, 5, 6; MIP gaps 0.32,
   0.43, 0.49, 0.54 and 1.12 %). Gaps on stress4h use the incumbent. Measured against the MIP bound on (26), the
   means rise by at most 0.18 points: best rule 39.96 ± 2.85 %, PPO r2 43.69 ± 3.89 %, PPO M2+M3
   46.47 ± 2.41 %. The certified seeds differ from round 5 (old: seeds 0, 1, 4 at 120 s; new: seeds 0, 4, 7, 8, 9
   at 300 s). Seed 1 was optimal at the old prices but is time-limited at the new prices with the largest gap
   (1.12 %). So the new-price ILP is harder, as `DECISIONS.md` anticipated.
6. **Report-only constraint family (9) flags** on stress4h, r2 riders only: rule r2 6, own rule r2 6, charge ASAP
   r2 6, never charge r2 3, PPO r2 5 (round 5: 3), rule M2+M3 selfish 7 of 10 seeds. `ok_modulo_report_only` is true
   on all 260 non-training rows. The same pattern as round 5, apart from PPO r2.
7. **MIP start.** The ILP starts from the cheapest rule, which on nyc4h-stress seeds 7 and 9 was the informational
   rule M2+M3 selfish (not a best-rule member). The start was accepted on all 20 solves, and both seeds solved to
   optimality, so this is harmless.
8. **The PPO results rest on one seed and default hyper-parameters.** One PPO seed (0), default hyper-parameters,
   200,704 steps per run. Training ran in lane 4 concurrently with lanes 1-3. Throughput (125-411 steps/s) is
   therefore not a clean benchmark (nyc4h-stress r2: 369 steps/s against 410 in round 5).
9. **The round-5 training figure is not repeated.** It drew test-seed reference lines over training-seed curves,
   which are different instances. At the new prices the stochastic training cost on stress4h (about 1850 USD)
   sits above the test-seed never-charge mean (about 1750 USD) for that reason alone. The training figure here
   therefore shows only changes within a run (Fig. 3).

---

## 2. Coverage

| item | nyc4h-stress | stress4h |
|---|---|---|
| rule rows (r2, M2, M2+M3, M2+M3 selfish) | 40 / 40 POLICY | 40 / 40 POLICY |
| RL-environment rows (PPO, own rule, never charge, charge ASAP; x 2 rider layers) | 80 / 80 POLICY | 80 / 80 POLICY |
| PPO training | 2 / 2 TRAINED (200,704 steps, 4,181 episodes each) | 2 / 2 TRAINED (200,704 steps, 4,181 episodes each) |
| relaxed ILP (TimeLimit 300 s; round 5: 120 s) | 10 OPTIMAL (max MIP gap 0.0099 %, 5-28 s) | 5 OPTIMAL (121-297 s), 5 TIME_LIMIT (MIP gap 0.32-1.12 %) |
| written-target ILP | not run (`--no-written`) | not run |
| SKIPPED_BUDGET / errors / budget-shortened ILP | 0 / 0 / 0 | 0 / 0 / 0 |

- **Run.** Wall time 119.4 min of a 270 min budget (plan: 82 min expected, 224 min worst). Lane 4 exited 0
  (`outputs/r6_lanes/lane_4.status`).
- **Instances.** The test instances are byte-identical in demand to round 5: the `demand_md5` matches on 20 of 20
  family-seed pairs, and only the prices differ (all rows carry P 60, w 18, v 15). Training used the same seeds
  1000-1019, the same seeded instance draw and the same PPO seed as round 5.
- **Best rule.** It picks r2 on 7 seeds and M2 on 3 (nyc4h-stress), and M2 on 6 and r2 on 4 (stress4h). In round 5
  the stress4h split was M2 8, r2 2.

---

## 3. Answer

- **The apparent advantage of PPO over the best rule disappears.**
  - At the new prices PPO is not cheaper than the best rule in any of the four family x rider cells.
  - On stress4h with M2+M3 riders, PPO minus best rule moves from **-149.69 ± 58.13 USD** (old prices, PPO cheaper
    on 10/10 seeds) to **+189.48 ± 75.85 USD** (new prices, PPO dearer on 10/10, p = 3e-4).
  - The other cells at the new prices: stress4h r2 +115.74 ± 76.70 (9/10 dearer, p = 0.008); nyc4h-stress M2+M3
    +91.79 ± 78.37 (9/10, p = 0.03); nyc4h-stress r2 +37.57 ± 66.30 (not significant, p = 0.23).
- **The collapse to never-charge is gone in three cells but persists in one.**
  - *nyc4h-stress:* PPO now reproduces its own rule station layer, which equals charge ASAP here. Cost difference:
    -1.11 ± 4.09 (r2) and +4.14 ± 8.76 USD (M2+M3). Served orders are identical on 9/10 seeds in each layer. At the
    old prices PPO served 3.6-5.6 points fewer orders than its rule.
  - *stress4h, r2 riders:* PPO charges partially (1.46 kWh against 2.48 for its rule). It serves 70.6 % of orders,
    against 74.2 % for its rule and 65.2 % for never-charge. It is 40.24 ± 27.48 USD dearer than its rule and
    80.29 ± 72.84 USD cheaper than never-charge.
  - *stress4h, M2+M3 riders:* the collapse persists in service. PPO serves 59.0 % (never-charge 58.5 %, best rule
    75.8 %, ILP 94.4 %). Its cost is -4.43 ± 7.37 USD relative to never-charge (not significant). The collapse is
    now costly, so it is a learning failure rather than a pricing artefact (anomaly 1).
- **PPO stays far from the relaxed ILP.**
  - Gaps: 28.01 ± 4.73 % and 31.39 ± 4.78 % on nyc4h-stress (r2, M2+M3); 43.47 ± 3.81 % and 46.25 ± 2.49 % on
    stress4h.
  - For comparison, the best rule's gaps are 25.75 ± 3.58 % and 39.71 ± 2.84 %.
  - The ILP serves 93.3 % and 94.4 % of orders; PPO serves 80.8-84.4 % on nyc4h-stress and 59.0-70.6 % on
    stress4h.
- **Training.** Once the instance mix is controlled for, the stochastic policy improves on nyc4h-stress (-15 % and
  -20 % of the initial cost) but not on stress4h (-0.4 % and +1.5 %). At the old prices it improved on all four
  runs, by 3-4 % on stress4h.

---

## 4. Tables

### 4.1 Cost and service per method, new prices (relaxed control headline)

Mean ± exact-t 95 % CI, n = 10 seeds per cell. USD per 4-h window. "Unserved" = P x unserved orders.

**nyc4h-stress** (ILP 10/10 OPTIMAL)

| method | n | cost, end-adj. | served % | lateness | unserved | response | kWh bought | late orders | gap vs ILP % |
|---|---|---|---|---|---|---|---|---|---|
| ILP, relaxed targets | 10 | 751.81 ± 38.83 | 93.3 ± 2.3 | 20.6 ± 7.3 | 144.0 ± 50.4 | 536.0 ± 18.4 | 2.06 ± 0.42 | 7.9 ± 2.2 | - |
| Best rule | 10 | 1017.67 ± 80.65 | 85.3 ± 2.8 | 75.5 ± 37.0 | 318.0 ± 60.9 | 571.6 ± 53.0 | 4.01 ± 0.26 | 16.6 ± 3.6 | 25.75 ± 3.58 |
| Rule r2 (= charge ASAP, r2) | 10 | 1056.36 ± 105.32 | 84.2 ± 4.6 | 84.2 ± 36.8 | 342.0 ± 99.2 | 577.8 ± 54.8 | 3.83 ± 0.25 | 17.4 ± 3.2 | 28.10 ± 4.72 |
| Rule M2 = M2+M3 (= charge ASAP, M2+M3) | 10 | 1105.32 ± 118.11 | 81.1 ± 4.2 | 84.1 ± 40.6 | 408.0 ± 90.0 | 560.9 ± 53.2 | 4.20 ± 0.22 | 16.9 ± 3.8 | 31.21 ± 4.60 |
| Never charge, r2 | 10 | 1525.79 ± 65.88 | 53.6 ± 2.5 | 77.9 ± 18.5 | 1002.0 ± 53.7 | 398.7 ± 25.4 | 0 | 10.1 ± 1.6 | 50.72 ± 1.56 |
| Never charge, M2+M3 | 10 | 1691.01 ± 48.70 | 40.0 ± 2.7 | 55.0 ± 13.5 | 1296.0 ± 57.9 | 295.1 ± 24.6 | 0 | 7.9 ± 0.8 | 55.53 ± 2.12 |
| **PPO, r2 riders** | 10 | 1055.24 ± 106.71 | 84.4 ± 4.9 | 85.8 ± 36.1 | 336.0 ± 105.5 | 581.1 ± 55.4 | 3.54 ± 0.18 | 17.6 ± 3.1 | 28.01 ± 4.73 |
| **PPO, M2+M3 riders** | 10 | 1109.45 ± 122.78 | 80.8 ± 4.3 | 84.1 ± 40.4 | 414.0 ± 93.7 | 559.0 ± 51.6 | 3.96 ± 0.29 | 16.8 ± 3.7 | 31.39 ± 4.78 |

**stress4h** (ILP 5 OPTIMAL + 5 TIME_LIMIT, MIP gap <= 1.12 %; gaps vs incumbent)

| method | n | cost, end-adj. | served % | lateness | unserved | response | kWh bought | late orders | gap vs ILP % |
|---|---|---|---|---|---|---|---|---|---|
| ILP, relaxed targets | 10 | 969.52 ± 75.57 | 94.4 ± 2.9 | 39.0 ± 9.5 | 162.0 ± 83.5 | 710.0 ± 19.1 | 1.91 ± 0.57 | 10.9 ± 1.9 | - |
| Best rule | 10 | 1614.12 ± 138.86 | 75.8 ± 5.3 | 131.4 ± 24.4 | 696.0 ± 151.7 | 728.9 ± 44.6 | 2.71 ± 0.15 | 21.8 ± 2.0 | 39.71 ± 2.84 |
| Rule r2 | 10 | 1689.63 ± 174.95 | 74.2 ± 6.1 | 149.4 ± 30.0 | 744.0 ± 174.3 | 738.8 ± 42.9 | 2.48 ± 0.22 | 23.0 ± 2.3 | 42.16 ± 3.52 |
| Rule M2 = M2+M3 | 10 | 1654.31 ± 124.49 | 73.3 ± 4.4 | 125.9 ± 21.3 | 768.0 ± 127.6 | 702.9 ± 32.1 | 2.77 ± 0.13 | 20.6 ± 0.9 | 41.31 ± 2.42 |
| Charge ASAP, r2 | 10 | 1677.60 ± 187.57 | 74.8 ± 6.3 | 150.1 ± 32.8 | 726.0 ± 182.6 | 743.9 ± 43.5 | 2.93 ± 0.25 | 22.9 ± 2.3 | 41.55 ± 4.21 |
| Charge ASAP, M2+M3 | 10 | 1627.11 ± 119.76 | 75.6 ± 3.7 | 135.1 ± 24.7 | 702.0 ± 107.2 | 731.9 ± 29.2 | 3.26 ± 0.18 | 21.6 ± 1.1 | 40.34 ± 2.39 |
| Never charge, r2 | 10 | 1810.15 ± 149.12 | 65.2 ± 6.1 | 119.9 ± 15.5 | 1002.0 ± 176.4 | 633.5 ± 41.4 | 0 | 19.3 ± 1.6 | 46.28 ± 2.87 |
| Never charge, M2+M3 | 10 | 1808.04 ± 114.49 | 58.5 ± 5.5 | 57.4 ± 16.1 | 1194.0 ± 157.3 | 503.2 ± 50.9 | 0 | 13.6 ± 1.6 | 46.37 ± 2.54 |
| **PPO, r2 riders** | 10 | 1729.86 ± 174.69 | 70.6 ± 6.4 | 134.2 ± 29.5 | 846.0 ± 183.7 | 693.5 ± 47.7 | 1.46 ± 0.32 | 21.3 ± 2.3 | 43.47 ± 3.81 |
| **PPO, M2+M3 riders** | 10 | 1803.61 ± 111.98 | 59.0 ± 5.2 | 59.2 ± 15.6 | 1182.0 ± 148.8 | 508.8 ± 46.7 | 0.84 ± 0.13 | 13.8 ± 1.5 | 46.25 ± 2.49 |

Notes on Table 4.1:
- At the new prices, never-charge is the most expensive policy in both families. At the old prices, never-charge
  with M2+M3 riders was the cheapest non-ILP policy on stress4h (Section 4.5).
- Orders more than 30 min late (stress4h): best rule 6.7, PPO M2+M3 1.7, ILP 1.1 per window.

### 4.2 Paired comparisons: PPO minus reference, old vs new prices

Cost = end-adjusted USD (negative = PPO cheaper). "cheaper" = seeds on which PPO is cheaper, out of 10. Served =
percentage points.

| family | riders | reference | old prices: cost diff | cheaper | p | **new prices: cost diff** | cheaper | p | served diff old | **served diff new** |
|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | never charge | -108.44 ± 77.55 | 9 | 0.012 | **-470.55 ± 90.65** | 10 | 9e-7 | +26.9 ± 8.3 | **+30.8 ± 5.4** |
| nyc4h-stress | r2 | own rule (= charge ASAP) | +22.07 ± 25.89 | 3 | 0.086 | **-1.11 ± 4.09** | 1 | 0.55 | -3.6 ± 3.1 | **+0.3 ± 0.6** |
| nyc4h-stress | r2 | best rule | +61.01 ± 65.38 | 2 | 0.064 | **+37.57 ± 66.30** | 1 | 0.23 | -4.7 ± 5.2 | **-0.8 ± 2.7** |
| nyc4h-stress | r2 | ILP, relaxed | +356.84 ± 110.66 | 0 | 5e-5 | **+303.43 ± 80.21** | 0 | 1e-5 | -5.3 ± 7.6 | **-8.9 ± 3.5** |
| nyc4h-stress | M2+M3 | never charge | -109.31 ± 128.82 | 7 | 0.087 | **-581.56 ± 102.08** | 10 | 4e-7 | +35.6 ± 5.4 | **+40.8 ± 3.6** |
| nyc4h-stress | M2+M3 | own rule (= charge ASAP) | -8.38 ± 18.87 | 6 | 0.34 | **+4.14 ± 8.76** | 3 | 0.31 | -5.6 ± 3.6 | **-0.3 ± 0.6** |
| nyc4h-stress | M2+M3 | best rule | +46.34 ± 47.92 | 3 | 0.057 | **+91.79 ± 78.37** | 1 | 0.027 | -9.7 ± 5.8 | **-4.4 ± 3.7** |
| nyc4h-stress | M2+M3 | ILP, relaxed | +342.17 ± 139.91 | 0 | 4e-4 | **+357.64 ± 94.75** | 0 | 1e-5 | -10.3 ± 4.5 | **-12.5 ± 3.0** |
| stress4h | r2 | never charge | 0.00 ± 0.00 (identical) | 0 | - | **-80.29 ± 72.84** | 8 | 0.034 | 0.0 | **+5.4 ± 3.7** |
| stress4h | r2 | own rule | -49.77 ± 61.42 | 8 | 0.10 | **+40.24 ± 27.48** | 1 | 0.009 | -9.0 ± 3.2 | **-3.5 ± 1.7** |
| stress4h | r2 | charge ASAP | -47.80 ± 76.37 | 8 | 0.19 | **+52.26 ± 24.13** | 0 | 8e-4 | -9.6 ± 3.2 | **-4.2 ± 1.6** |
| stress4h | r2 | best rule | +35.90 ± 55.52 | 3 | 0.18 | **+115.74 ± 76.70** | 1 | 0.008 | -9.4 ± 4.2 | **-5.2 ± 4.1** |
| stress4h | r2 | ILP, relaxed | +635.35 ± 65.06 | 0 | 4e-9 | **+760.34 ± 123.64** | 0 | 2e-7 | -20.2 ± 4.7 | **-23.8 ± 5.0** |
| stress4h | M2+M3 | never charge | +0.03 ± 0.07 | 0 | 0.34 | **-4.43 ± 7.37** | 2 | 0.21 | 0.0 | **+0.4 ± 0.6** |
| stress4h | M2+M3 | own rule | -155.14 ± 52.90 | 10 | 1e-4 | **+149.30 ± 43.24** | 0 | 3e-5 | -14.8 ± 2.7 | **-14.4 ± 2.5** |
| stress4h | M2+M3 | charge ASAP | -173.88 ± 68.02 | 10 | 3e-4 | **+176.50 ± 54.53** | 0 | 4e-5 | -17.1 ± 3.9 | **-16.7 ± 3.6** |
| stress4h | M2+M3 | best rule | -149.69 ± 58.13 | 10 | 3e-4 | **+189.48 ± 75.85** | 0 | 3e-4 | -16.0 ± 3.7 | **-16.9 ± 3.8** |
| stress4h | M2+M3 | ILP, relaxed | +449.77 ± 48.94 | 0 | 6e-9 | **+834.09 ± 68.48** | 0 | 5e-10 | -26.9 ± 3.0 | **-35.4 ± 3.6** |

### 4.3 Collapse diagnostics (deterministic PPO policy on test seeds 0-9)

| family | riders | prices | kWh bought by PPO, mean [min, max] | kWh, own rule | seeds served = never charge | seeds cost within 0.5 USD of never charge | seeds served = own rule | seeds cost within 0.5 USD of own rule |
|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | old | 2.83 [1.39, 3.67] | 3.83 | 0 | 0 | 4 | 3 |
| nyc4h-stress | r2 | **new** | 3.54 [3.22, 3.89] | 3.83 | 0 | 0 | **9** | **8** |
| nyc4h-stress | M2+M3 | old | 2.67 [1.78, 3.83] | 4.20 | 0 | 0 | 2 | 2 |
| nyc4h-stress | M2+M3 | **new** | 3.96 [3.44, 4.56] | 4.20 | 0 | 0 | **9** | **8** |
| stress4h | r2 | old | 0.12 [0.00, 0.28] | 2.48 | 10 | 10 | 0 | 0 |
| stress4h | r2 | **new** | 1.46 [0.75, 2.11] | 2.48 | **3** | **3** | 1 | 0 |
| stress4h | M2+M3 | old | 0.24 [0.03, 1.11] | 2.77 | 10 | 10 | 0 | 0 |
| stress4h | M2+M3 | **new** | 0.84 [0.61, 1.08] | 2.77 | **8** | **8** (5 exactly equal) | 0 | 0 |

Served-order differences, PPO minus never-charge, on stress4h with M2+M3 riders (new prices), by seed 0-9:
0, 0, 0, +1, 0, 0, +1, 0, 0, 0.

### 4.4 Where the cost difference comes from (paired, USD, mean ± 95 % CI)

| family | comparison | prices | response | lateness | unserved | electricity | travel | end adj. | **total, end-adj.** |
|---|---|---|---|---|---|---|---|---|---|
| stress4h | PPO M2+M3 - best rule | old | -210.3 ± 40.2 | -166.2 ± 40.3 | +231.0 ± 52.6 | -1.1 ± 0.1 | -3.5 ± 0.6 | +0.4 ± 0.1 | **-149.7 ± 58.1** |
| stress4h | PPO M2+M3 - best rule | new | -220.1 ± 41.2 | -72.1 ± 16.1 | +486.0 ± 109.8 | -0.8 ± 0.1 | -3.7 ± 0.5 | +0.2 ± 0.2 | **+189.5 ± 75.9** |
| stress4h | never charge M2+M3 - best rule | new | -225.6 ± 43.3 | -74.0 ± 17.5 | +498.0 ± 109.1 | -1.2 ± 0.1 | -3.7 ± 0.5 | +0.4 ± 0.1 | **+193.9 ± 73.6** |
| stress4h | best rule - ILP | old | +140.7 ± 36.5 | +301.8 ± 48.3 | +156.0 ± 45.0 | +0.6 ± 0.2 | +1.0 ± 0.9 | -0.6 ± 0.1 | **+599.5 ± 75.0** |
| stress4h | best rule - ILP | new | +18.9 ± 43.2 | +92.4 ± 20.3 | +534.0 ± 109.8 | +0.4 ± 0.2 | -0.4 ± 0.8 | -0.6 ± 0.2 | **+644.6 ± 85.1** |
| nyc4h-stress | best rule - ILP | old | +112.0 ± 60.2 | +175.2 ± 88.1 | +6.0 ± 33.2 | +0.8 ± 0.1 | +2.2 ± 0.8 | -0.4 ± 0.1 | **+295.8 ± 121.3** |
| nyc4h-stress | best rule - ILP | new | +35.7 ± 44.1 | +54.9 ± 30.3 | +174.0 ± 47.2 | +0.6 ± 0.1 | +1.1 ± 0.7 | -0.5 ± 0.1 | **+265.9 ± 55.4** |

- **Why the sign flips.** PPO with M2+M3 riders on stress4h drops about 8 more orders than the best rule at both
  price levels (231/30 and 486/60). At the old prices this was more than paid for by avoided response and lateness
  cost. At P 60 / v 15 the doubled unserved price and the lower lateness price reverse the balance.
- **Where the ILP's advantage comes from.** The ILP's advantage is almost entirely service: response, lateness and
  unserved orders. Energy terms are below 1 USD.

### 4.5 Comparison with round 5 (old prices) on the same 20 test instances

The rule, never-charge, charge-ASAP and own-rule schedules do not depend on order prices in these families. Their
schedules are identical across rounds: served orders are equal on 10/10 seeds for every one of these methods.
Their cost changes are pure repricing: new = old + unserved_old x (60/30 - 1) + lateness_old x (15/36 - 1), with a
maximum error of 5e-13 USD over 160 rows. Only PPO (retrained) and the ILP (re-solved) change behaviour.

| family | method | cost old | **cost new** | served % old | **served % new** |
|---|---|---|---|---|---|
| nyc4h-stress | ILP, relaxed targets | 668.54 ± 13.31 | **751.81 ± 38.83** | 85.8 ± 2.2 | **93.3 ± 2.3** |
| nyc4h-stress | Best rule | 964.37 ± 130.65 | **1017.67 ± 80.65** | 85.3 ± 2.8 | **85.3 ± 2.8** |
| nyc4h-stress | Never charge, r2 / M2+M3 | 1133.81 / 1120.01 | **1525.79 / 1691.01** | 53.6 / 40.0 | **53.6 / 40.0** |
| nyc4h-stress | PPO, r2 riders | 1025.38 ± 121.30 | **1055.24 ± 106.71** | 80.6 ± 7.4 | **84.4 ± 4.9** |
| nyc4h-stress | PPO, M2+M3 riders | 1010.71 ± 149.28 | **1109.45 ± 122.78** | 75.6 ± 6.0 | **80.8 ± 4.3** |
| stress4h | ILP, relaxed targets | 841.63 ± 31.16 | **969.52 ± 75.57** | 85.4 ± 3.8 | **94.4 ± 2.9** |
| stress4h | Best rule | 1441.08 ± 100.82 | **1614.12 ± 138.86** | 74.6 ± 5.5 | **75.8 ± 5.3** |
| stress4h | Never charge, r2 / M2+M3 | 1476.98 / 1291.36 | **1810.15 / 1808.04** | 65.2 / 58.5 | **65.2 / 58.5** |
| stress4h | PPO, r2 riders | 1476.98 ± 84.30 | **1729.86 ± 174.69** | 65.2 ± 6.1 | **70.6 ± 6.4** |
| stress4h | PPO, M2+M3 riders | 1291.40 ± 65.33 | **1803.61 ± 111.98** | 58.5 ± 5.5 | **59.0 ± 5.2** |

Notes on Table 4.5:
- The best rule's served share changes only because the per-seed argmin changes (stress4h: M2 8/10 to 6/10).
- Best-rule gap vs the relaxed ILP: 28.97 ± 7.27 % to **25.75 ± 3.58 %** (nyc4h-stress) and 41.30 ± 2.61 % to
  **39.71 ± 2.84 %** (stress4h).
- Never-charge minus best rule on stress4h with M2+M3 riders: **-149.72 ± 58.14 USD (old) to +193.92 ± 73.65 USD
  (new)**. This is the objective artefact behind round-5 anomaly (a), and the recalibration removes it.

### 4.6 Training trend (stochastic training policy, training seeds 1000-1019)

**Method.**
- Episode cost = Phi_H - Phi_0 = -10 x episode return (reward scale 0.1).
- The training instance of each episode is reconstructed as in the round-5 digest correction: gymnasium
  `np_random(0)`, 16 consecutive episodes per draw from seeds 1000-1019. The reconstruction is validated two ways:
  - The predicted cache-miss episodes (cache size 8) are among the 151 largest wall-time increments in 145, 147,
    150 and 150 of 151 cases.
  - The instance fixed effects explain R^2 = 0.80 / 0.69 / 0.98 / 0.96 of the episode-cost variance.
- The same procedure reproduces the round-5 corrected numbers exactly (-82.8 / -175.0 / -46.6 / -53.1 USD; mix
  shifts +20.0 / -110.7 / +200.5 / +53.6).
- Model: OLS of episode cost on instance fixed effects + period dummies (first 100 / middle / last 100 episodes),
  over all 4,181 episodes. The reported estimate is last minus first.
- Two intervals are given. OLS assumes independent episodes and is too narrow. The other is clustered by
  16-episode block, which still ignores the slow drift of the policy, so treat it as indicative.

| family | riders | prices | wall s | steps/s | peak RSS GB | raw first-100 -> last-100 (USD) | instance-mix shift | **instance-adjusted change** | OLS 95 % CI | block-clustered 95 % CI | % of first-100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | old | 489 | 410 | 2.1 | 1123.7 -> 1065.7 | +20.0 | -82.8 | [-99.1, -66.5] | [-139.0, -26.6] | -7.4 % |
| nyc4h-stress | r2 | **new** | 544 | 369 | 2.0 | 1239.8 -> 1147.1 | +84.9 | **-189.5** | [-209.4, -169.5] | [-257.3, -121.6] | -15.3 % |
| nyc4h-stress | M2+M3 | old | 465 | 432 | 2.1 | 1170.0 -> 894.8 | -110.7 | -175.0 | [-198.9, -151.0] | [-258.0, -91.9] | -15.0 % |
| nyc4h-stress | M2+M3 | **new** | 489 | 411 | 2.0 | 1321.4 -> 999.7 | -67.6 | **-270.1** | [-296.7, -243.5] | [-354.8, -185.4] | -20.4 % |
| stress4h | r2 | old | 1625 | 124 | 6.7 | 1428.0 -> 1584.7 | +200.5 | -46.6 | [-50.7, -42.4] | [-69.3, -23.8] | -3.3 % |
| stress4h | r2 | **new** | 1603 | 125 | 6.9 | 1803.1 -> 1974.2 | +177.9 | **-7.9** | [-15.4, -0.4] | [-28.9, +13.1] | -0.4 % |
| stress4h | M2+M3 | old | 1562 | 129 | 6.9 | 1277.0 -> 1280.5 | +53.6 | -53.1 | [-57.8, -48.4] | [-74.2, -32.0] | -4.2 % |
| stress4h | M2+M3 | **new** | 1413 | 142 | 6.9 | 1832.2 -> 1912.9 | +55.5 | **+27.0** | [+20.3, +33.7] | [+10.9, +43.1] | +1.5 % |

Decile profile (new prices, instance-adjusted, relative to the first tenth of training, USD):
- nyc4h-stress r2: 0, -91, -128, -154, -155, -166, -168, -178, -178, -180.
- nyc4h-stress M2+M3: 0, -159, -200, -215, -225, -211, -230, -231, -216, -232.
- stress4h r2: 0, +7, +13, +21, +19, +13, +8, -4, -3, -17.
- stress4h M2+M3: 0, +1, -8, +18, +18, +24, +33, +27, +25, +26.

On nyc4h-stress most of the gain comes in the first 30-40 % of training. On stress4h with M2+M3 riders the
stochastic policy drifts upward after about 30 % of training.

The deterministic test-seed episode cost matches the outcome tables: on stress4h M2+M3, PPO 1746.0 ± 112.2 USD
against never-charge 1750.4 ± 114.5 and own rule 1596.7 ± 126.0.

---

## 5. Interpretation

**Shown by these records:**
- **The apparent advantage disappears with the recalibration.** The round-5 result "PPO beats the best rule by
  about 150 USD on stress4h" was an artefact of pricing unserved orders below late ones.
  - At P 60 / v 15 the same service level (about 58.5-59 % of orders) costs about 190 USD more than the best rule.
  - No PPO cell is cheaper than the best rule; three of four are significantly dearer.
- **Where PPO learns, it learns the rule.** On nyc4h-stress the agent converges to (almost exactly) its own rule
  station layer, which here equals charge ASAP: same served orders on 9/10 seeds, cost within 0.5 USD on 8/10
  seeds, mean difference -1.11 ± 4.09 (r2) and +4.14 ± 8.76 USD (M2+M3). The largest single-seed deviation is
  16.6 USD (r2) and 38.9 USD (M2+M3).
  - At the old prices it under-charged and dropped 3.6-5.6 points of service.
  - The higher P made charging valuable enough that PPO now finds the rule. It does not improve on it.
- **On stress4h PPO does not learn the rule.**
  - With r2 riders it charges about 60 % of what the rule charges and is 40 USD dearer than the rule.
  - With M2+M3 riders it stays at the never-charge service level although that is now 194 USD dearer than the
    best rule. The constant all-sites charge action, which is in its action space, beats it on every seed.
  - The instance-adjusted training curve shows no improvement (r2) or a deterioration (M2+M3) of the stochastic
    policy on this family.
- **A learned station layer on rule riders stays far from coordination.** PPO's gap to the relaxed ILP is 28-46 %,
  never below the best rule's 26-40 %.
  - The ILP now serves 93-94 % of orders (old prices: 85-86 %).
  - At the new prices the ILP's advantage over the best rule on stress4h is mostly unserved orders (534 of 645 USD).
- **The rule baselines are unchanged.** The rule and heuristic schedules are identical across rounds. Every
  rule-side change between rounds is repricing of the same schedule; only PPO and the ILP re-optimise.

**Suggested, not shown:**
- *Why PPO fails on stress4h.* The failure is probably an optimisation (credit-assignment and exploration) problem
  rather than a limit of the station layer: the benefit of a charge decision arrives many slots later through swaps
  and served orders, on a family with 3.1 M arcs and 125-142 steps/s. These records do not show which mechanism it
  is (reward normalisation, entropy, horizon, or training length). They also do not show whether another PPO seed,
  tuning or more steps would reach the charge-ASAP level. There is one seed, default hyper-parameters and
  200 k steps.
- *Whether a better agent could beat the best rule.* That an RL station agent could beat the best rule at all is
  not supported. Where PPO works (nyc4h-stress) it matches its own rule (mean difference within ±5 USD), and the best rule is a
  per-seed oracle choice between two rider layers, which a single-rider-layer agent cannot exploit. The bound on
  what station-only learning could gain is not measured here.
- *What the paper should say.* The RL comparator, with the recalibrated prices, gives no evidence that learned
  station control approaches the coordinated ILP. Its round-5 "win" should be dropped from the manuscript or
  reported as an objective-calibration effect. A service-level constraint is no longer needed to make the
  comparison meaningful, because the new P penalises dropped orders enough. The stress4h M2+M3 collapse should be
  reported as a training failure of the comparator.

---

## 6. Figures (`figs/`, PDF + 300-dpi PNG; script `figs/make_rl_report.py`)

1. **`fig_rl_paired_differences`** (7.2 in, double column).
   - Panels: PPO minus (a) never charge, (b) own rule station layer, (c) best rule, per family and rider layer.
   - Encoding: old prices (hollow vermilion circles) vs new prices (filled blue squares). Paired over test seeds
     0-9, mean with exact-t 95 % CI, end-adjusted USD per 4-h window.
   - What it shows: panel (c) for stress4h M2+M3 riders flips from about -150 to about +190 USD, while panel (a)
     stays at about 0 for that cell.
2. **`fig_rl_service_energy`** (7.2 in).
   - Panels: (a) orders served (%) and (b) energy bought in the window (kWh) for the ILP, best rule, own rule
     station layer, PPO and never charge, per family and rider layer. Same old/new price encoding; mean with
     exact-t 95 % CI (n = 10). PPO rows are shaded.
   - The rule and never-charge rows coincide across prices by construction (identical schedules).
   - What it shows: PPO with M2+M3 riders on stress4h stays at the never-charge service level while buying
     0.84 kWh.
3. **`fig_rl_training`** (7.2 in, appendix).
   - Content: change of the 100-episode mean episode cost relative to the first 100 episodes. Instance-adjusted
     (fixed effects from the reconstructed training-instance sequence) at old prices (vermilion) and new prices
     (blue), plus the unadjusted new-price curve (grey) to show the instance-mix confounding. Changes are in each
     round's own prices.
   - What it shows: training lowers cost on nyc4h-stress at both price levels but not on stress4h at the new
     prices.

---

## Appendix A. Per-seed end-adjusted cost, new prices (USD)

The ILP column gives status, MIP gap and runtime. "R5 ILP" is the round-5 (old prices, 120 s) status of the same
instance. The last column gives served %: best rule / PPO r2 / PPO M2+M3 / ILP.

| family | seed | rule r2 | rule M2+M3 | best rule (rule) | never r2 | never M2+M3 | PPO r2 | PPO M2+M3 | ILP relaxed | R5 ILP | served % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | 0 | 1201.77 | 1207.03 | 1201.77 (r2) | 1589.01 | 1705.72 | 1201.77 | 1207.03 | 783.16 (OPT, 0.01 %, 17 s) | OPT, 0.00 % | 88.9 / 88.9 / 88.9 / 94.4 |
| nyc4h-stress | 1 | 1039.70 | 1168.52 | 1039.70 (r2) | 1473.55 | 1586.39 | 1039.70 | 1168.39 | 752.75 (OPT, 0.00 %, 11 s) | OPT, 0.00 % | 83.3 / 83.3 / 77.8 / 94.4 |
| nyc4h-stress | 2 | 936.52 | 1006.27 | 936.52 (r2) | 1468.95 | 1661.80 | 942.02 | 1006.27 | 721.17 (OPT, 0.00 %, 11 s) | OPT, 0.00 % | 86.1 / 86.1 / 83.3 / 94.4 |
| nyc4h-stress | 3 | 1134.18 | 1031.40 | 1031.40 (M2) | 1467.26 | 1625.07 | 1134.18 | 1031.40 | 790.38 (OPT, 0.00 %, 6 s) | OPT, 0.00 % | 77.8 / 72.2 / 77.8 / 88.9 |
| nyc4h-stress | 4 | 1304.64 | 1020.79 | 1020.79 (M2) | 1533.25 | 1727.60 | 1304.64 | 1023.54 | 778.83 (OPT, 0.00 %, 6 s) | OPT, 0.00 % | 83.3 / 75.0 / 83.3 / 91.7 |
| nyc4h-stress | 5 | 866.84 | 1004.29 | 866.84 (r2) | 1517.91 | 1719.68 | 866.84 | 1004.29 | 722.87 (OPT, 0.01 %, 7 s) | OPT, 0.00 % | 91.7 / 91.7 / 83.3 / 94.4 |
| nyc4h-stress | 6 | 979.19 | 1017.22 | 979.19 (r2) | 1498.08 | 1639.22 | 979.19 | 1017.24 | 716.10 (OPT, 0.00 %, 8 s) | OPT, 0.00 % | 83.3 / 83.3 / 80.6 / 94.4 |
| nyc4h-stress | 7 | 1054.13 | 1380.59 | 1054.13 (r2) | 1654.58 | 1806.56 | 1054.13 | 1380.54 | 807.81 (OPT, 0.00 %, 28 s) | OPT, 0.00 % | 83.3 / 83.3 / 69.4 / 88.9 |
| nyc4h-stress | 8 | 1177.45 | 1348.13 | 1177.45 (r2) | 1678.43 | 1771.84 | 1177.45 | 1387.02 | 810.30 (OPT, 0.00 %, 19 s) | OPT, 0.00 % | 86.1 / 86.1 / 75.0 / 91.7 |
| nyc4h-stress | 9 | 869.14 | 868.90 | 868.90 (M2) | 1376.85 | 1666.24 | 852.50 | 868.81 | 634.71 (OPT, 0.00 %, 5 s) | OPT, 0.00 % | 88.9 / 94.4 / 88.9 / 100.0 |
| stress4h | 0 | 1183.98 | 1307.42 | 1183.98 (r2) | 1444.38 | 1571.10 | 1170.02 | 1571.27 | 787.82 (OPT, 0.00 %, 121 s) | OPT, 0.00 % | 89.6 / 89.6 / 66.7 / 100.0 |
| stress4h | 1 | 1960.66 | 1684.78 | 1684.78 (M2) | 1968.99 | 1756.20 | 1968.94 | 1756.35 | 1034.02 (TL, 1.12 %, 300 s) | OPT, 0.00 % | 72.9 / 58.3 / 62.5 / 91.7 |
| stress4h | 2 | 1758.22 | 1730.79 | 1730.79 (M2) | 1791.28 | 1884.46 | 1791.46 | 1884.64 | 1015.58 (TL, 0.32 %, 300 s) | TL, 0.41 % | 66.7 / 64.6 / 52.1 / 91.7 |
| stress4h | 3 | 1761.74 | 1754.85 | 1754.85 (M2) | 1851.31 | 1889.14 | 1797.49 | 1858.18 | 958.82 (TL, 0.43 %, 300 s) | TL, 1.64 % | 72.9 / 72.9 / 58.3 / 95.8 |
| stress4h | 4 | 1571.11 | 1554.41 | 1554.41 (M2) | 1830.00 | 1646.25 | 1605.19 | 1646.25 | 913.79 (OPT, 0.00 %, 216 s) | OPT, 0.00 % | 75.0 / 75.0 / 64.6 / 97.9 |
| stress4h | 5 | 1738.18 | 1499.05 | 1499.05 (M2) | 1793.30 | 1695.64 | 1782.94 | 1695.64 | 960.84 (TL, 0.49 %, 300 s) | TL, 1.10 % | 81.2 / 66.7 / 62.5 / 95.8 |
| stress4h | 6 | 2056.62 | 1867.60 | 1867.60 (M2) | 2235.39 | 2020.25 | 2078.92 | 2006.37 | 1066.47 (TL, 0.54 %, 300 s) | TL, 0.80 % | 64.6 / 60.4 / 47.9 / 89.6 |
| stress4h | 7 | 1559.67 | 1681.25 | 1559.67 (r2) | 1690.98 | 1890.14 | 1671.98 | 1890.14 | 893.29 (OPT, 0.00 %, 253 s) | TL, 0.75 % | 79.2 / 70.8 / 56.2 / 97.9 |
| stress4h | 8 | 1772.65 | 1878.32 | 1772.65 (r2) | 1863.19 | 2040.44 | 1798.98 | 2040.44 | 1164.12 (OPT, 0.00 %, 236 s) | TL, 0.13 % | 75.0 / 72.9 / 50.0 / 87.5 |
| stress4h | 9 | 1533.43 | 1584.64 | 1533.43 (r2) | 1632.72 | 1686.76 | 1632.72 | 1686.76 | 900.45 (OPT, 0.01 %, 297 s) | TL, 0.69 % | 81.2 / 75.0 / 68.8 / 95.8 |

The only seed on which PPO beats the best rule is stress4h seed 0 with r2 riders (1170.02 vs 1183.98 USD). Rule M2
equals rule M2+M3 on every seed.

## Appendix B. Check of the auto-generated `RESULTS.md`

Reproduced exactly from the records (mean ± t half-width):
- every cost, end-adjusted cost, C_end_adjust, served share and gap column for all 14 methods in both families
  (programmatic comparison with `summary.csv`: 220 values, max absolute difference 2e-13; spot values: best rule 1017.67 ± 80.65 and 1614.12 ± 138.86; gap 25.75 ± 3.58 and 39.71 ± 2.84);
- all "diff vs own rule" and "diff vs best_rule" entries (for example PPO M2+M3 on stress4h +149.30 ± 43.24 and
  +189.48 ± 75.85);
- the ILP status lines (10/10 OPTIMAL; 5/10 OPTIMAL, max MIP gap 0.0112), the best-rule picks and replay parity;
- the lateness table means (for example best rule 16.60 and 21.80 late orders per window).

Problems:
- the training table (raw, reward units, confounded by instance mix; anomaly 3);
- the stale header reference to `ilp_written` and the price of recovery (anomaly 4).
