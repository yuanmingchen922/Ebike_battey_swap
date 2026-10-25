# R6 fill stage rl_seeds: the PPO station-layer comparator over three training seeds (final report)

Question. Round 6 retrained the PPO station-layer comparator at the new prices (unserved penalty P = 60 USD,
response price w = 18 USD/h from release, lateness price v = 15 USD/h from the promise) with one PPO seed and drew
three conclusions: PPO is never cheaper than the best rule; on stress4h with M2+M3 riders it collapses to
never-charge; on nyc4h-stress it matches its own rule station layer. This stage adds PPO seeds 1 and 2 for the four
learning cells (family x rider layer). With three PPO seeds per cell: what are the mean and CI over PPO seeds of
the PPO cost, the gap to the relaxed ILP, the paired differences to the best rule and to never-charge, and the
served share? Do the single-seed conclusions hold across seeds, and which manuscript caveats does this replace?

Sources. Seed 0: `outputs/r6_penalty/rl/records.jsonl` (264 lines, 264 unique keys; its ILP, rule and heuristic rows
are the shared references) and `outputs/r6_penalty/rl/models/*/monitor.csv`. Seeds 1 and 2:
`outputs/r6_fill/rl_seeds/records.jsonl` (488 lines, 488 unique keys `(ppo_seed, kind, family, seed, method)`, no
duplicates; the per-seed X7 folders `seed1/`, `seed2/` with `records.jsonl`, `models/*/monitor.csv`,
`run_stdout.log`, `wall_time.json`). Legacy prices (P 30, w 18, v 36; one PPO seed; ILP 120 s):
`outputs/r5_x7_rl/records.jsonl` (284 lines, 284 keys). Every number below is recomputed from these files by
`figs/make_rl_seeds_report.py` (no solves, no simulation), which also writes `figs/rl_seeds_tables.json`,
`figs/tables.md`, `figs/per_test_seed_recomputed.csv` and the three figures. The auto-generated `RESULTS.md` was
checked against these numbers (Section 1, item 9).

Terminology. Families **nyc4h-stress** (code `nyc4h_stress2`: 6 bikes, 36 orders, 3 sites) and **stress4h**
(`r5_stress4h`: 6 bikes, 48 orders, 3 sites, TOU tariff). Rider layers **r2** and **M2+M3** (code `r5`; no transfer
services in these families, so rule M2 equals rule M2+M3). PPO controls only station charging (one binary charge
decision per site and slot). **Own rule station layer** = the rule station layer run inside the RL environment;
it equals rule r2 or rule M2+M3 exactly on every test seed (parity flag true on 120 of 120 rows). **Never charge**
and **charge ASAP** are fixed station heuristics on the same rider layer; on nyc4h-stress charge ASAP equals the
own rule. **Best rule** = per-test-seed minimum of the end-adjusted cost over rules r2, M2 and M2+M3. Cost = E2
total + M1 end-state adjustment (**end-adjusted**), relaxed end targets, USD per 4-h window. **Gap** = 100 (policy
- ILP) / policy per test seed, then averaged. **Test seeds** 0-9 (n = 10 per cell); **PPO seeds** 0, 1, 2 (n = 3 per
cell; training seeds 1000-1019, 200,704 steps, hyper-parameters `a7_rl.PPO_DEFAULTS`, identical for all 12 runs).
Intervals are exact Student-t 95 % CIs, `mean ± half-width`: over the 10 test seeds within a PPO seed
(t_0.975,9 = 2.262), or over the three PPO-seed means (t_0.975,2 = 4.303, "across seeds"). A third view, the
**seed-averaged policy**, averages the three PPO costs per test seed and takes the CI over the 10 test seeds.
Every difference is paired by test seed. p values are two-sided paired t-tests, uncorrected.

---

## 1. Problems and anomalies

1. **The stress4h M2+M3 collapse is reproduced by every seed and is deeper in the new seeds.** PPO seeds 0, 1
   and 2 serve the never-charge number of orders on 8, 9 and 9 of 10 test seeds; their cost is within 0.5 USD of
   never-charge on 8, 9 and 9 test seeds (exactly equal on 5, 8 and 9). Energy bought per window: 0.84, 0.48 and
   0.26 kWh (own rule 2.77 kWh); seed 2 buys nothing on 3 test seeds. All three seeds serve 59.0 % of orders
   (never-charge 58.5 %, best rule 75.8 %, ILP 94.4 %) and are dearer than the best rule by 189.48, 191.83 and
   190.71 USD (dearer on 10 of 10 test seeds each) and than charge ASAP, an action inside their action space, by
   176.50, 178.84 and 177.73 USD (10 of 10 each). The instance-adjusted training cost rose in all three runs
   (+27.0, +37.7, +60.0 USD from the first to the last 100 episodes; block-clustered CIs exclude zero). The
   failure is therefore not a property of PPO seed 0.
2. **The one seed-sensitive cell is stress4h with r2 riders.** Seeds 0 and 2 charge partially (1.46 and 1.74 kWh,
   served 70.6 %, 80.29 ± 72.84 and 78.50 ± 57.77 USD cheaper than never-charge on 8 of 10 test seeds); seed 1
   is a partial collapse (1.07 kWh, served 66.5 %, 14.19 ± 23.63 USD cheaper than never-charge, 3 of 10, with the
   never-charge order count on 7 of 10 test seeds) and is 106.34 ± 59.12 USD dearer than its own rule against
   40.24 ± 27.48 and 42.03 ± 32.46 for seeds 0 and 2. The three seed means of PPO minus best rule are +115.74,
   +181.85 and +117.54 USD, all positive (PPO cheaper on 1, 0 and 1 test seed). The between-seed standard
   deviation of the seed means is 37.7 USD (range 66.1 USD), one sixth of the within-seed SD over test seeds
   (226.9 USD). The n = 3 across-seed CI is correspondingly wide (+138.37 ± 93.55 USD) but excludes zero.
3. **On nyc4h-stress the new seeds sit near the own rule but not as tightly as seed 0.** PPO minus own rule
   (= charge ASAP): r2 riders -1.11 ± 4.09, +17.02 ± 33.66 and +9.22 ± 13.97 USD; M2+M3 riders +4.14 ± 8.76,
   -1.89 ± 18.05 and +10.23 ± 32.36 USD. No seed mean differs from the rule (p >= 0.17). The cost is within
   0.5 USD of the rule on 8, 6 and 8 (r2) and 8, 7 and 4 (M2+M3) test seeds, and the served orders equal the
   rule's on 9, 9 and 8 and on 9, 8 and 5 test seeds. Single-test-seed deviations reach +150.6 USD (r2, seed 1,
   test seed 9) and +107.9 USD (M2+M3, seed 2, test seed 4), and PPO is cheaper than its rule by 63.6 USD on test
   seed 2 for M2+M3 seeds 1 and 2. The manuscript's "reproduces its own rule ... the same served orders on 9 of
   10 seeds" (one seed) should read "ends within about 20 USD of its own rule on average in every seed, with the
   rule's cost on 4-8 of 10 test seeds and deviations of up to 150 USD on single test seeds" (Section 7).
4. **ILP reference unchanged, 5 of 10 stress4h seeds time-limited.** The relaxed ILP rows of the rl stage
   (300 s) were not among the fill-round retries (those covered headline, psweep, vsweep, fleet and levers).
   stress4h: 5 OPTIMAL (seeds 0, 4, 7, 8, 9), 5 TIME_LIMIT (seeds 1, 2, 3, 5, 6; MIP gaps 1.12, 0.32, 0.43, 0.49,
   0.54 %). nyc4h-stress: 10 OPTIMAL (max MIP gap 0.01 %). Gaps use the incumbent; against the MIP bound the
   stress4h means rise by at most 0.16 points (Table 4.2). The paired cost differences to the rules do not
   involve the ILP.
5. **Report-only constraint family (9) flags.** PPO r2 on stress4h has `ok = False` on test seeds 1, 3, 5, 7, 8
   (seed 0), 1, 3 (seed 1) and 1, 3, 9 (seed 2); `ok_modulo_report_only` is true on all 120 PPO rows, as in the
   R6 rl stage. No other row is flagged.
6. **Across-seed CIs with n = 3 need care.** t_0.975,2 = 4.303 makes them wide where the seeds disagree (stress4h
   r2: ± 93.55 USD) and tiny where they agree (stress4h M2+M3: 1804.80 ± 2.91 USD). The tiny intervals measure
   agreement between seeds, not uncertainty over instances: the same quantity has a CI of ± 111.69 USD over the
   10 test seeds (seed-averaged policy). Both views are reported. The pooled 30-row CIs in the auto `RESULTS.md`
   and `summary_pooled.csv` treat PPO seed x test seed rows as independent (three rows share a test instance)
   and should not be quoted.
7. **Cosmetic: `maxrss_gb` 7.5 GB on all four seed-2 training rows, including nyc4h-stress.** Seeds 1 and 2 ran in
   one process (`r6_fill.run_rl_seeds` loops over the seeds), and `maxrss` is the process-level peak carried over
   from seed 1's stress4h training (7.2 GB). The seed-1 nyc4h-stress runs peaked at 2.0-2.1 GB, the true
   requirement. Throughput (nyc4h-stress 429-435 steps/s; stress4h 125-128 for seed 1, 147-152 for seed 2;
   seed 0: 369-411 and 125-142) is not a clean benchmark: the laptop ran other work during all three runs.
8. **Training-instance reconstruction uses the PPO seed as environment seed.** `r5_x7_rl.train_policy` calls
   `venv.seed(PPO_SEED)`, so the block draw of training instances follows gymnasium `np_random(k)` for seed k
   (the R6 report's reconstruction used `np_random(0)` for seed 0). Validation as in the R6 report: for seed 1
   and 2 the predicted cache-miss episodes (cache size 8) are among the largest wall-time increments in 158-160 of
   160-161 cases (seed 0: 145-150 of 151), and the instance fixed effects explain R^2 = 0.71-0.86 (nyc4h-stress)
   and 0.95-0.99 (stress4h) of the episode-cost variance. The number of predicted cache misses differs by seed
   (151, 161, 160) because the LRU pattern depends on the draw sequence; the number of 16-episode blocks is the
   same (4,181 episodes).
9. **The auto-generated `RESULTS.md` reproduces.** Every entry of its "Across PPO seeds" and "Per PPO seed"
   tables matches this recomputation to the printed precision (for example PPO cost 1064.734 ± 22.602 and gap
   28.719 ± 1.648 on nyc4h-stress r2; PPO minus best rule 190.676 ± 2.912 on stress4h M2+M3). It omits the served
   share, the comparisons with never-charge and charge ASAP, the collapse diagnostics, the training trend and the
   legacy comparison, which are added here. Its header is correct (no written ILP by design).
10. **Nothing is missing or skipped.** 12 of 12 trainings TRAINED (200,704 steps, 4,181 episodes each, identical
    hyper-parameters, `ppo_seed` recorded in the train row equals the folder seed); 120 of 120 PPO evaluations;
    no SKIPPED_BUDGET, no error rows. Wall time 72.9 min (seed 1) and 64.4 min (seed 2) of 135 min budgets each.

---

## 2. Coverage

| item | PPO seed 0 (`r6_penalty/rl`) | PPO seed 1 (`rl_seeds/seed1`) | PPO seed 2 (`rl_seeds/seed2`) |
|---|---|---|---|
| records (unique keys) | 264 (264) | 244 (244) | 244 (244) |
| rule rows (r2, M2, M2+M3, M2+M3 selfish; 2 families x 10 test seeds) | 80 POLICY | 80 POLICY | 80 POLICY |
| RL-environment rows (PPO, own rule, never charge, charge ASAP; 2 rider layers) | 160 POLICY | 160 POLICY | 160 POLICY |
| PPO training rows | 4 TRAINED, 200,704 steps | 4 TRAINED, 200,704 steps | 4 TRAINED, 200,704 steps |
| relaxed ILP (300 s), shared reference | nyc4h-stress 10 OPT; stress4h 5 OPT + 5 TL (0.32-1.12 %) | not re-solved (`--no-ilp`) | not re-solved |
| written-target ILP | not run (by design) | not run | not run |
| prices on every non-training row | P 60, w 18, v 15 | P 60, w 18, v 15 | P 60, w 18, v 15 |
| SKIPPED / error / budget-shortened rows | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| wall time | 119.4 min of 270 | 72.9 min of 135 | 64.4 min of 135 |

- **Identity of the non-learned rows across seeds.** The rule, own-rule, never-charge and charge-ASAP rows of
  seeds 1 and 2 equal those of seed 0 exactly (maximum absolute difference of the end-adjusted cost 0.0 USD on all
  120 cell x test-seed pairs for each of the four methods). Own rule = rule r2 / M2+M3 exactly (parity flag true,
  120 of 120). The analysis therefore uses seed 0's ILP, rule and heuristic rows as the common reference.
- **Instances.** The test instances are the repriced copies of the rl stage (`seed<k>/instances/` copied from
  `r6_penalty/rl/instances`, byte-identical); `demand_md5` matches seed 0 on 120 of 120 PPO rows and matches the
  legacy records on all 20 family x test-seed pairs. Training instances: seeds 1000-1019, 16 consecutive episodes
  per draw, cache 8, reward scale 0.1, relaxed targets.
- **Best rule** (identical for every PPO seed): r2 on 7 and M2 on 3 test seeds of nyc4h-stress; M2 on 6 and r2 on 4
  of stress4h.

Training rows:

| family | riders | PPO seed | status | steps | episodes | wall s | steps/s | peak RSS GB | train id |
|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | 0 | TRAINED | 200,704 | 4181 | 544 | 369 | 2.0 | `nyc4h_stress2_r2_20261018T115835` |
| nyc4h-stress | r2 | 1 | TRAINED | 200,704 | 4181 | 465 | 432 | 2.0 | `nyc4h_stress2_r2_20261019T133020` |
| nyc4h-stress | r2 | 2 | TRAINED | 200,704 | 4181 | 461 | 435 | 7.5 (a) | `nyc4h_stress2_r2_20261019T144309` |
| nyc4h-stress | M2+M3 | 0 | TRAINED | 200,704 | 4181 | 489 | 411 | 2.0 | `nyc4h_stress2_r5_20261018T120705` |
| nyc4h-stress | M2+M3 | 1 | TRAINED | 200,704 | 4181 | 468 | 429 | 2.1 | `nyc4h_stress2_r5_20261019T133826` |
| nyc4h-stress | M2+M3 | 2 | TRAINED | 200,704 | 4181 | 462 | 434 | 7.5 (a) | `nyc4h_stress2_r5_20261019T145109` |
| stress4h | r2 | 0 | TRAINED | 200,704 | 4181 | 1603 | 125 | 6.9 | `r5_stress4h_r2_20261018T134814` |
| stress4h | r2 | 1 | TRAINED | 200,704 | 4181 | 1612 | 125 | 6.7 | `r5_stress4h_r2_20261019T140637` |
| stress4h | r2 | 2 | TRAINED | 200,704 | 4181 | 1322 | 152 | 7.5 (a) | `r5_stress4h_r2_20261019T151427` |
| stress4h | M2+M3 | 0 | TRAINED | 200,704 | 4181 | 1413 | 142 | 6.9 | `r5_stress4h_r5_20261018T141308` |
| stress4h | M2+M3 | 1 | TRAINED | 200,704 | 4181 | 1572 | 128 | 7.2 | `r5_stress4h_r5_20261019T143404` |
| stress4h | M2+M3 | 2 | TRAINED | 200,704 | 4181 | 1364 | 147 | 7.5 (a) | `r5_stress4h_r5_20261019T153824` |

(a) process-level peak carried over from seed 1 (anomaly 7).

---

## 3. Answer

- **PPO is never cheaper than the best rule, in every seed and every cell.** All 12 (PPO seed x cell) means of
  PPO minus best rule are positive: +37.57 / +55.71 / +47.91 USD (nyc4h-stress, r2; seeds 0 / 1 / 2),
  +91.79 / +85.75 / +97.87 (nyc4h-stress, M2+M3), +115.74 / +181.85 / +117.54 (stress4h, r2),
  +189.48 / +191.83 / +190.71 (stress4h, M2+M3). Across seeds (n = 3): **+47.06 ± 22.60, +91.80 ± 15.06,
  +138.37 ± 93.55 and +190.68 ± 2.91 USD**. Seed-averaged policy over the 10 test seeds: +47.06 ± 64.37
  (p = 0.13), +91.80 ± 74.87 (p = 0.02), +138.37 ± 68.12 (p = 0.001), +190.68 ± 74.31 (p = 3e-4). Of the 120
  (PPO seed, cell, test seed) evaluations, PPO is cheaper than the best rule on 4, by at most 16.4 USD (seed 0:
  nyc4h-stress test seed 9 with both rider layers, stress4h r2 test seed 0; seed 2: stress4h r2 test seed 0).
  The nyc4h-stress r2 cell stays not significant within each seed (p = 0.10-0.23) because PPO there is the r2
  rule on most test seeds and the best rule beats r2 by picking M2 on 3 test seeds.
- **The collapse to never-charge on stress4h with M2+M3 riders holds on all three seeds** (anomaly 1): served
  share 59.0 % in each seed (across seeds 59.0 ± 0.0 %), PPO minus never-charge -4.43 ± 7.37, -2.09 ± 4.78 and
  -3.21 ± 7.25 USD (none significant; across -3.24 ± 2.91), energy bought 0.84, 0.48 and 0.26 kWh. It costs
  150.49 ± 2.91 USD more than the own rule and 190.68 ± 2.91 USD more than the best rule (across seeds), and the
  constant charge-ASAP action beats it on 30 of 30 seed x test-seed evaluations. Served share is 14.4 points
  below the own rule and 16.9 points below the best rule in each seed. The paired decomposition against the best
  rule is the same in every seed: +486.0 USD of unserved orders (8.1 more dropped orders per window), -71 to -72
  of lateness, -219 to -220 of response.
- **On nyc4h-stress PPO ends near its own rule station layer (= charge ASAP) in every seed, and never improves on
  it on average.** PPO minus own rule, across seeds: **+8.38 ± 22.60 USD (r2) and +4.16 ± 15.06 USD (M2+M3)**;
  served share -0.4 ± 1.4 and -0.2 ± 0.4 points. Within seeds the means are -1.1 to +17.0 (r2) and -1.9 to +10.2
  USD (M2+M3), all p >= 0.17, with the rule's cost on 4-8 of 10 test seeds and deviations of either sign on the
  others (anomaly 3). PPO beats never-charge by 452-471 USD (r2) and 575-588 USD (M2+M3), on 10 of 10 test seeds
  in every seed. Energy bought 3.51-3.60 kWh (r2; rule 3.83) and 3.34-4.03 kWh (M2+M3; rule 4.20).
- **stress4h with r2 riders depends on the seed** (anomaly 2): PPO buys 1.07-1.74 kWh (rule 2.48), serves
  66.5-70.6 % (rule 74.2, never-charge 65.2) and is dearer than its own rule by 40.24, 106.34 and 42.03 USD
  (across seeds 62.87 ± 93.55). Seed 1 sits near never-charge on 7 of 10 test seeds; seeds 0 and 2 on 3 and 2.
- **Gap to the relaxed ILP across seeds: 28.72 ± 1.65 % (nyc4h-stress, r2), 31.42 ± 0.88 % (M2+M3),
  44.30 ± 3.50 % (stress4h, r2), 46.28 ± 0.08 % (M2+M3)**; seed ranges 28.01-29.32, 31.08-31.79, 43.47-45.93,
  46.25-46.31 %. The best rule's gaps are 25.75 ± 3.58 and 39.71 ± 2.84 %; no PPO seed in any cell gets closer
  to the ILP than the best rule. The R6 range "28-46 %" stands (28.0-46.3 over the twelve seed x cell means).
  PPO costs across seeds: 1064.73 ± 22.60, 1109.47 ± 15.06, 1752.50 ± 93.55 and 1804.80 ± 2.91 USD (ILP
  751.81 and 969.52; best rule 1017.67 and 1614.12).
- **Served share across seeds: 83.8 ± 1.4 %, 80.9 ± 0.4 %, 69.2 ± 6.0 %, 59.0 ± 0.0 %** (ILP 93.3 and 94.4 %,
  best rule 85.3 and 75.8 %); PPO minus ILP -9.5, -12.4, -25.1 and -35.4 points.
- **Training.** The instance-adjusted stochastic-policy cost falls on nyc4h-stress in every seed (-189.5, -191.3,
  -153.7 USD with r2 riders; -270.1, -242.8, -190.3 with M2+M3; 12-20 % of the initial cost, all block-clustered
  CIs below zero), is flat on stress4h with r2 riders (-7.9, +14.6, -16.7 USD; all CIs include zero) and rises
  on stress4h with M2+M3 riders in every seed (+27.0, +37.7, +60.0 USD; all CIs above zero).
- **Legacy comparison** (one PPO seed at P 30 / v 36 on the same instances). The sign flip of PPO minus best rule on
  stress4h M2+M3, from -149.69 ± 58.13 USD (cheaper on 10 of 10) at the legacy prices to about +190 USD (dearer
  on 10 of 10), is reproduced by all three new-price seeds (+189.48, +191.83, +190.71). On nyc4h-stress the legacy
  under-charging (2.83 and 2.67 kWh, served 80.6 and 75.6 %) is gone in every new-price seed (3.51-3.60 and
  3.34-4.03 kWh, served 83.3-84.4 and 80.8-81.1 %). On stress4h r2 the legacy PPO was never-charge exactly
  (0.12 kWh, 65.2 % served); every new-price seed charges more (1.07-1.74 kWh, 66.5-70.6 %), seed 1 the least.
  The legacy gaps 33.51 / 31.77 % (nyc4h-stress) and 42.85 / 34.69 % (stress4h) become 28.7 / 31.4 and
  44.3 / 46.3 % across seeds.

**Verdict on the single-seed conclusions.** (i) "PPO never cheaper than the best rule": holds, 12 of 12 seed x cell
means positive. (ii) "Collapse to never-charge on stress4h with M2+M3 riders": holds and is deeper in seeds 1 and 2.
(iii) "Matches its own rule on nyc4h-stress": holds on average in every seed (no significant difference, served
share within 1 point) but the match is exact on fewer test seeds in seeds 1 and 2 (4-8 of 10 instead of 8 of 10);
the wording should be softened. New finding: stress4h with r2 riders is seed-dependent (seed 1 half-collapses), so
the single-seed numbers of that cell (PPO minus own rule +40.2, minus never-charge -80.3 USD) should be reported
as seed ranges.

---

## 4. Tables

### 4.1 Paired differences, PPO minus reference, per PPO seed (n = 10 test seeds) and across seeds (n = 3)

End-adjusted USD per 4-h window; negative = PPO cheaper; "cheaper" = test seeds (of 10) on which PPO is cheaper.
Charge ASAP equals the own rule on nyc4h-stress and is omitted there.

| family | riders | reference | seed 0 | cheaper | seed 1 | cheaper | seed 2 | cheaper | across seeds (n 3) | min / max of seed means |
|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | never charge | -470.55 ± 90.65 | 10 | -452.41 ± 92.43 | 10 | -460.21 ± 88.43 | 10 | **-461.05 ± 22.60** | -470.55 / -452.41 |
| nyc4h-stress | r2 | own rule station layer | -1.11 ± 4.09 | 1 | 17.02 ± 33.66 | 0 | 9.22 ± 13.97 | 0 | **8.38 ± 22.60** | -1.11 / 17.02 |
| nyc4h-stress | r2 | best rule | 37.57 ± 66.30 | 1 | 55.71 ± 68.69 | 0 | 47.91 ± 64.20 | 0 | **47.06 ± 22.60** | 37.57 / 55.71 |
| nyc4h-stress | r2 | ILP, relaxed | 303.43 ± 80.21 | 0 | 321.57 ± 79.06 | 0 | 313.77 ± 75.44 | 0 | **312.92 ± 22.60** | 303.43 / 321.57 |
| nyc4h-stress | M2+M3 | never charge | -581.56 ± 102.08 | 10 | -587.59 ± 97.46 | 10 | -575.47 ± 98.94 | 10 | **-581.54 ± 15.06** | -587.59 / -575.47 |
| nyc4h-stress | M2+M3 | own rule station layer | 4.14 ± 8.76 | 3 | -1.89 ± 18.05 | 3 | 10.23 ± 32.36 | 5 | **4.16 ± 15.06** | -1.89 / 10.23 |
| nyc4h-stress | M2+M3 | best rule | 91.79 ± 78.37 | 1 | 85.75 ± 75.74 | 0 | 97.87 ± 75.00 | 0 | **91.80 ± 15.06** | 85.75 / 97.87 |
| nyc4h-stress | M2+M3 | ILP, relaxed | 357.64 ± 94.75 | 0 | 351.61 ± 91.30 | 0 | 363.73 ± 93.37 | 0 | **357.66 ± 15.06** | 351.61 / 363.73 |
| stress4h | r2 | never charge | -80.29 ± 72.84 | 8 | -14.19 ± 23.63 | 3 | -78.50 ± 57.77 | 8 | **-57.66 ± 93.55** | -80.29 / -14.19 |
| stress4h | r2 | own rule station layer | 40.24 ± 27.48 | 1 | 106.34 ± 59.12 | 0 | 42.03 ± 32.46 | 1 | **62.87 ± 93.55** | 40.24 / 106.34 |
| stress4h | r2 | charge ASAP | 52.26 ± 24.13 | 0 | 118.36 ± 71.63 | 0 | 54.05 ± 27.93 | 0 | **74.89 ± 93.55** | 52.26 / 118.36 |
| stress4h | r2 | best rule | 115.74 ± 76.70 | 1 | 181.85 ± 68.94 | 0 | 117.54 ± 79.86 | 1 | **138.37 ± 93.55** | 115.74 / 181.85 |
| stress4h | r2 | ILP, relaxed | 760.34 ± 123.64 | 0 | 826.45 ± 88.45 | 0 | 762.14 ± 126.24 | 0 | **782.98 ± 93.55** | 760.34 / 826.45 |
| stress4h | M2+M3 | never charge | -4.43 ± 7.37 | 2 | -2.09 ± 4.78 | 1 | -3.21 ± 7.25 | 1 | **-3.24 ± 2.91** | -4.43 / -2.09 |
| stress4h | M2+M3 | own rule station layer | 149.30 ± 43.24 | 0 | 151.64 ± 41.80 | 0 | 150.52 ± 42.44 | 0 | **150.49 ± 2.91** | 149.30 / 151.64 |
| stress4h | M2+M3 | charge ASAP | 176.50 ± 54.53 | 0 | 178.84 ± 53.99 | 0 | 177.73 ± 51.11 | 0 | **177.69 ± 2.91** | 176.50 / 178.84 |
| stress4h | M2+M3 | best rule | 189.48 ± 75.85 | 0 | 191.83 ± 72.58 | 0 | 190.71 ± 75.01 | 0 | **190.68 ± 2.91** | 189.48 / 191.83 |
| stress4h | M2+M3 | ILP, relaxed | 834.09 ± 68.48 | 0 | 836.43 ± 71.24 | 0 | 835.31 ± 69.10 | 0 | **835.28 ± 2.91** | 834.09 / 836.43 |

p values of the per-seed paired tests: PPO minus best rule p = 0.23 / 0.10 / 0.13 (nyc4h-stress r2),
0.027 / 0.031 / 0.016 (nyc4h-stress M2+M3), 0.008 / 2e-4 / 0.009 (stress4h r2), 3e-4 / 2e-4 / 3e-4 (stress4h
M2+M3). PPO minus own rule on nyc4h-stress p = 0.55 / 0.28 / 0.17 and 0.31 / 0.82 / 0.49. PPO minus never-charge on
stress4h M2+M3 p = 0.21 / 0.35 / 0.34.

Seed-averaged policy (mean of the three PPO costs per test seed, CI over n = 10 test seeds), PPO minus best rule:
+47.06 ± 64.37 (p = 0.13, cheaper on 0 of 10), +91.80 ± 74.87 (p = 0.022, 0 of 10), +138.37 ± 68.12 (p = 0.001,
0 of 10), +190.68 ± 74.31 (p = 3e-4, 0 of 10); minus never-charge: -461.05 ± 89.02, -581.54 ± 98.36,
-57.66 ± 45.13 (p = 0.018), -3.24 ± 4.03 (p = 0.10); minus own rule: +8.38 ± 13.40 (p = 0.19), +4.16 ± 15.95
(p = 0.57), +62.87 ± 27.15 (p = 5e-4), +150.49 ± 42.18.

### 4.2 PPO level per seed: cost, served share, gap, energy

Mean ± exact-t 95 % CI. "Mean of seed means" is over the three PPO seeds; "seed-averaged policy" over the 10
test seeds. Gap vs MIP bound replaces the ILP incumbent by the solver bound on (26) plus the ILP's end adjustment
(differs only on the 5 time-limited stress4h seeds). No PPO row has an order more than 60 min late.

| family | riders | PPO seed | cost USD | served % | gap vs ILP % | gap vs MIP bound % | kWh bought |
|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | 0 | 1055.24 ± 106.71 | 84.4 ± 4.9 | 28.01 ± 4.73 | 28.01 ± 4.73 | 3.54 ± 0.18 |
| nyc4h-stress | r2 | 1 | 1073.38 ± 94.94 | 83.3 ± 4.2 | 29.32 ± 5.16 | 29.32 ± 5.15 | 3.60 ± 0.20 |
| nyc4h-stress | r2 | 2 | 1065.58 ± 98.55 | 83.6 ± 4.3 | 28.83 ± 4.56 | 28.83 ± 4.56 | 3.51 ± 0.14 |
| nyc4h-stress | r2 | **mean of seed means (n 3)** | **1064.73 ± 22.60** | **83.8 ± 1.4** | **28.72 ± 1.65** | 28.72 ± 1.65 | 3.55 ± 0.12 |
| nyc4h-stress | r2 | seed-averaged policy (n 10) | 1064.73 ± 98.84 | 83.8 ± 4.4 | 28.72 ± 4.67 | 28.72 ± 4.67 | 3.55 ± 0.15 |
| nyc4h-stress | M2+M3 | 0 | 1109.45 ± 122.78 | 80.8 ± 4.3 | 31.39 ± 4.78 | 31.39 ± 4.78 | 3.96 ± 0.29 |
| nyc4h-stress | M2+M3 | 1 | 1103.42 ± 117.69 | 81.1 ± 4.1 | 31.08 ± 4.78 | 31.08 ± 4.78 | 4.03 ± 0.21 |
| nyc4h-stress | M2+M3 | 2 | 1115.54 ± 121.96 | 80.8 ± 4.3 | 31.79 ± 4.72 | 31.79 ± 4.72 | 3.34 ± 0.23 |
| nyc4h-stress | M2+M3 | **mean of seed means (n 3)** | **1109.47 ± 15.06** | **80.9 ± 0.4** | **31.42 ± 0.88** | 31.42 ± 0.88 | 3.78 ± 0.93 |
| nyc4h-stress | M2+M3 | seed-averaged policy (n 10) | 1109.47 ± 119.88 | 80.9 ± 4.2 | 31.42 ± 4.64 | 31.42 ± 4.64 | 3.78 ± 0.21 |
| stress4h | r2 | 0 | 1729.86 ± 174.69 | 70.6 ± 6.4 | 43.47 ± 3.81 | 43.63 ± 3.89 | 1.46 ± 0.32 |
| stress4h | r2 | 1 | 1795.97 ± 134.00 | 66.5 ± 5.1 | 45.93 ± 2.60 | 46.08 ± 2.65 | 1.07 ± 0.26 |
| stress4h | r2 | 2 | 1731.66 ± 178.31 | 70.6 ± 6.8 | 43.51 ± 3.80 | 43.67 ± 3.88 | 1.74 ± 0.29 |
| stress4h | r2 | **mean of seed means (n 3)** | **1752.50 ± 93.55** | **69.2 ± 6.0** | **44.30 ± 3.50** | 44.46 ± 3.50 | 1.42 ± 0.84 |
| stress4h | r2 | seed-averaged policy (n 10) | 1752.50 ± 160.39 | 69.2 ± 5.9 | 44.30 ± 3.16 | 44.46 ± 3.24 | 1.42 ± 0.18 |
| stress4h | M2+M3 | 0 | 1803.61 ± 111.98 | 59.0 ± 5.2 | 46.25 ± 2.49 | 46.41 ± 2.41 | 0.84 ± 0.13 |
| stress4h | M2+M3 | 1 | 1805.95 ± 112.14 | 59.0 ± 5.2 | 46.31 ± 2.59 | 46.47 ± 2.52 | 0.48 ± 0.28 |
| stress4h | M2+M3 | 2 | 1804.83 ± 111.30 | 59.0 ± 5.0 | 46.28 ± 2.54 | 46.44 ± 2.46 | 0.26 ± 0.22 |
| stress4h | M2+M3 | **mean of seed means (n 3)** | **1804.80 ± 2.91** | **59.0 ± 0.0** | **46.28 ± 0.08** | 46.44 ± 0.07 | 0.53 ± 0.73 |
| stress4h | M2+M3 | seed-averaged policy (n 10) | 1804.80 ± 111.69 | 59.0 ± 5.1 | 46.28 ± 2.54 | 46.44 ± 2.46 | 0.53 ± 0.20 |

### 4.3 Reference levels on the same test seeds (n = 10; identical for every PPO seed)

| family | riders | method | cost USD | served % | gap vs ILP % | kWh bought |
|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | ILP, relaxed targets (10 OPT) | 751.81 ± 38.83 | 93.3 ± 2.3 | - | 2.06 ± 0.42 |
| nyc4h-stress | r2 | best rule | 1017.67 ± 80.65 | 85.3 ± 2.8 | 25.75 ± 3.58 | 4.01 ± 0.26 |
| nyc4h-stress | r2 | own rule station layer = charge ASAP | 1056.36 ± 105.32 | 84.2 ± 4.6 | 28.10 ± 4.72 | 3.83 ± 0.25 |
| nyc4h-stress | r2 | never charge | 1525.79 ± 65.88 | 53.6 ± 2.5 | 50.72 ± 1.56 | 0.00 |
| nyc4h-stress | M2+M3 | own rule station layer = charge ASAP | 1105.32 ± 118.11 | 81.1 ± 4.2 | 31.21 ± 4.60 | 4.20 ± 0.22 |
| nyc4h-stress | M2+M3 | never charge | 1691.01 ± 48.70 | 40.0 ± 2.7 | 55.53 ± 2.12 | 0.00 |
| stress4h | r2 | ILP, relaxed targets (5 OPT + 5 TL) | 969.52 ± 75.57 | 94.4 ± 2.9 | - | 1.91 ± 0.57 |
| stress4h | r2 | best rule | 1614.12 ± 138.86 | 75.8 ± 5.3 | 39.71 ± 2.84 | 2.71 ± 0.15 |
| stress4h | r2 | own rule station layer | 1689.63 ± 174.95 | 74.2 ± 6.1 | 42.16 ± 3.52 | 2.48 ± 0.22 |
| stress4h | r2 | charge ASAP | 1677.60 ± 187.57 | 74.8 ± 6.3 | 41.55 ± 4.21 | - |
| stress4h | r2 | never charge | 1810.15 ± 149.12 | 65.2 ± 6.1 | 46.28 ± 2.87 | 0.00 |
| stress4h | M2+M3 | own rule station layer | 1654.31 ± 124.49 | 73.3 ± 4.4 | 41.31 ± 2.42 | 2.77 ± 0.13 |
| stress4h | M2+M3 | charge ASAP | 1627.11 ± 119.76 | 75.6 ± 3.7 | 40.34 ± 2.39 | - |
| stress4h | M2+M3 | never charge | 1808.04 ± 114.49 | 58.5 ± 5.5 | 46.37 ± 2.54 | 0.00 |

### 4.4 Served share, PPO minus reference (percentage points), per PPO seed

| family | riders | reference | seed 0 | seed 1 | seed 2 | across (n 3) |
|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | never charge | 30.8 ± 5.4 | 29.7 ± 5.4 | 30.0 ± 5.3 | **30.2 ± 1.4** |
| nyc4h-stress | r2 | own rule | 0.3 ± 0.6 | -0.8 ± 1.9 | -0.6 ± 0.8 | **-0.4 ± 1.4** |
| nyc4h-stress | r2 | best rule | -0.8 ± 2.7 | -1.9 ± 2.3 | -1.7 ± 2.1 | **-1.5 ± 1.4** |
| nyc4h-stress | r2 | ILP, relaxed | -8.9 ± 3.5 | -10.0 ± 3.8 | -9.7 ± 3.4 | **-9.5 ± 1.4** |
| nyc4h-stress | M2+M3 | never charge | 40.8 ± 3.6 | 41.1 ± 3.4 | 40.8 ± 3.8 | **40.9 ± 0.4** |
| nyc4h-stress | M2+M3 | own rule | -0.3 ± 0.6 | 0.0 ± 0.9 | -0.3 ± 1.5 | **-0.2 ± 0.4** |
| nyc4h-stress | M2+M3 | best rule | -4.4 ± 3.7 | -4.2 ± 3.4 | -4.4 ± 3.4 | **-4.4 ± 0.4** |
| nyc4h-stress | M2+M3 | ILP, relaxed | -12.5 ± 3.0 | -12.2 ± 3.0 | -12.5 ± 3.1 | **-12.4 ± 0.4** |
| stress4h | r2 | never charge | 5.4 ± 3.7 | 1.3 ± 1.9 | 5.4 ± 2.6 | **4.0 ± 6.0** |
| stress4h | r2 | own rule | -3.5 ± 1.7 | -7.7 ± 2.4 | -3.5 ± 1.7 | **-4.9 ± 6.0** |
| stress4h | r2 | best rule | -5.2 ± 4.1 | -9.4 ± 3.2 | -5.2 ± 3.5 | **-6.6 ± 6.0** |
| stress4h | r2 | ILP, relaxed | -23.8 ± 5.0 | -27.9 ± 3.9 | -23.7 ± 5.2 | **-25.1 ± 6.0** |
| stress4h | M2+M3 | never charge | 0.4 ± 0.6 | 0.4 ± 0.9 | 0.4 ± 0.9 | **0.4 ± 0.0** |
| stress4h | M2+M3 | own rule | -14.4 ± 2.5 | -14.4 ± 2.7 | -14.4 ± 2.5 | **-14.4 ± 0.0** |
| stress4h | M2+M3 | best rule | -16.9 ± 3.8 | -16.9 ± 3.4 | -16.9 ± 3.8 | **-16.9 ± 0.0** |
| stress4h | M2+M3 | ILP, relaxed | -35.4 ± 3.6 | -35.4 ± 3.9 | -35.4 ± 3.5 | **-35.4 ± 0.0** |

### 4.5 Collapse and rule-matching diagnostics per PPO seed (deterministic policy, 10 test seeds each)

| family | riders | PPO seed | kWh PPO mean [min, max] | kWh own rule | served = never charge | cost within 0.5 USD of never charge | served = own rule | cost within 0.5 USD of own rule | test seeds PPO cheaper than best rule | test seeds charge ASAP cheaper than PPO |
|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | 0 | 3.54 [3.22, 3.89] | 3.83 | 0 | 0 | 9 | 8 | 1 | 1 |
| nyc4h-stress | r2 | 1 | 3.60 [3.22, 4.06] | 3.83 | 0 | 0 | 9 | 6 | 0 | 4 |
| nyc4h-stress | r2 | 2 | 3.51 [3.22, 3.83] | 3.83 | 0 | 0 | 8 | 8 | 0 | 3 |
| nyc4h-stress | M2+M3 | 0 | 3.96 [3.44, 4.56] | 4.20 | 0 | 0 | 9 | 8 | 1 | 3 |
| nyc4h-stress | M2+M3 | 1 | 4.03 [3.56, 4.44] | 4.20 | 0 | 0 | 8 | 7 | 0 | 2 |
| nyc4h-stress | M2+M3 | 2 | 3.34 [3.06, 3.94] | 4.20 | 0 | 0 | 5 | 4 | 0 | 5 |
| stress4h | r2 | 0 | 1.46 [0.75, 2.11] | 2.48 | 3 | 3 (1 exactly) | 1 | 0 | 1 | 10 |
| stress4h | r2 | 1 | 1.07 [0.42, 1.81] | 2.48 | 7 | 7 (6 exactly) | 0 | 0 | 0 | 10 |
| stress4h | r2 | 2 | 1.74 [0.78, 2.19] | 2.48 | 2 | 2 (2 exactly) | 1 | 0 | 1 | 10 |
| stress4h | M2+M3 | 0 | 0.84 [0.61, 1.08] | 2.77 | 8 | 8 (5 exactly) | 0 | 0 | 0 | 10 |
| stress4h | M2+M3 | 1 | 0.48 [0.00, 1.17] | 2.77 | 9 | 9 (8 exactly) | 0 | 0 | 0 | 10 |
| stress4h | M2+M3 | 2 | 0.26 [0.00, 0.94] | 2.77 | 9 | 9 (9 exactly) | 0 | 0 | 0 | 10 |

Served orders, PPO minus never-charge, stress4h M2+M3, test seeds 0-9: seed 0: 0, 0, 0, +1, 0, 0, +1, 0, 0, 0;
seed 1: 0, 0, 0, 0, 0, 0, 0, 0, +2, 0; seed 2: 0, 0, 0, 0, 0, 0, +2, 0, 0, 0. On nyc4h-stress charge ASAP = own
rule, so the last column there counts test seeds on which PPO is dearer than its rule.

### 4.6 Variability: between PPO seeds against between test seeds (end-adjusted PPO cost, USD)

| family | riders | SD of the three seed means | mean within-seed SD over test seeds | SD over test seeds of the seed-averaged policy | range of seed means |
|---|---|---|---|---|---|
| nyc4h-stress | r2 | 9.1 | 139.9 | 138.2 | 18.1 |
| nyc4h-stress | M2+M3 | 6.1 | 168.9 | 167.6 | 12.1 |
| stress4h | r2 | 37.7 | 226.9 | 224.2 | 66.1 |
| stress4h | M2+M3 | 1.2 | 156.3 | 156.1 | 2.3 |

The PPO seed moves the mean cost by 2-66 USD; the test instance moves it by 140-230 USD (SD). Only on stress4h
with r2 riders does the seed matter beyond noise.

### 4.7 Legacy prices (P 30 / v 36, one PPO seed, ILP 120 s) against the new prices (three PPO seeds), same instances

Legacy reference levels (end-adjusted USD): ILP 668.54 ± 13.31 (nyc4h-stress; 10 OPT at 120 s) and 841.63 ± 31.16
(stress4h; 3 OPT + 7 TL, MIP gaps 0.13-1.64 %); best rule 964.37 ± 130.65 and 1441.08 ± 100.82; never-charge
1133.81 / 1120.01 (nyc4h-stress, r2 / M2+M3) and 1476.98 / 1291.36 (stress4h). The rule and heuristic schedules
are identical across rounds (pure repricing, see the R6 rl report, Section 4.5); only PPO (retrained) and the ILP
(re-solved) change behaviour.

| family | riders | quantity | legacy, seed 0 | new, seed 0 | new, seed 1 | new, seed 2 | new, across (n 3) |
|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | PPO - best rule, USD | 61.01 ± 65.38 (2/10 cheaper) | 37.57 ± 66.30 (1/10) | 55.71 ± 68.69 (0/10) | 47.91 ± 64.20 (0/10) | **47.06 ± 22.60** |
| nyc4h-stress | r2 | PPO - never charge, USD | -108.44 ± 77.55 (9/10) | -470.55 ± 90.65 (10/10) | -452.41 ± 92.43 (10/10) | -460.21 ± 88.43 (10/10) | **-461.05 ± 22.60** |
| nyc4h-stress | r2 | PPO - own rule, USD | 22.07 ± 25.89 (3/10) | -1.11 ± 4.09 (1/10) | 17.02 ± 33.66 (0/10) | 9.22 ± 13.97 (0/10) | **8.38 ± 22.60** |
| nyc4h-stress | r2 | PPO - ILP, USD | 356.84 ± 110.66 (0/10) | 303.43 ± 80.21 (0/10) | 321.57 ± 79.06 (0/10) | 313.77 ± 75.44 (0/10) | **312.92 ± 22.60** |
| nyc4h-stress | r2 | gap vs relaxed ILP, % | 33.51 ± 6.26 | 28.01 ± 4.73 | 29.32 ± 5.16 | 28.83 ± 4.56 | **28.72 ± 1.65** |
| nyc4h-stress | r2 | PPO served, % | 80.6 ± 7.4 | 84.4 ± 4.9 | 83.3 ± 4.2 | 83.6 ± 4.3 | **83.8 ± 1.4** |
| nyc4h-stress | r2 | kWh bought by PPO | 2.83 ± 0.54 | 3.54 ± 0.18 | 3.60 ± 0.20 | 3.51 ± 0.14 | **3.55 ± 0.12** |
| nyc4h-stress | M2+M3 | PPO - best rule, USD | 46.34 ± 47.92 (3/10) | 91.79 ± 78.37 (1/10) | 85.75 ± 75.74 (0/10) | 97.87 ± 75.00 (0/10) | **91.80 ± 15.06** |
| nyc4h-stress | M2+M3 | PPO - never charge, USD | -109.31 ± 128.82 (7/10) | -581.56 ± 102.08 (10/10) | -587.59 ± 97.46 (10/10) | -575.47 ± 98.94 (10/10) | **-581.54 ± 15.06** |
| nyc4h-stress | M2+M3 | PPO - own rule, USD | -8.38 ± 18.87 (6/10) | 4.14 ± 8.76 (3/10) | -1.89 ± 18.05 (3/10) | 10.23 ± 32.36 (5/10) | **4.16 ± 15.06** |
| nyc4h-stress | M2+M3 | PPO - ILP, USD | 342.17 ± 139.91 (0/10) | 357.64 ± 94.75 (0/10) | 351.61 ± 91.30 (0/10) | 363.73 ± 93.37 (0/10) | **357.66 ± 15.06** |
| nyc4h-stress | M2+M3 | gap vs relaxed ILP, % | 31.77 ± 8.12 | 31.39 ± 4.78 | 31.08 ± 4.78 | 31.79 ± 4.72 | **31.42 ± 0.88** |
| nyc4h-stress | M2+M3 | PPO served, % | 75.6 ± 6.0 | 80.8 ± 4.3 | 81.1 ± 4.1 | 80.8 ± 4.3 | **80.9 ± 0.4** |
| nyc4h-stress | M2+M3 | kWh bought by PPO | 2.67 ± 0.52 | 3.96 ± 0.29 | 4.03 ± 0.21 | 3.34 ± 0.23 | **3.78 ± 0.93** |
| stress4h | r2 | PPO - best rule, USD | 35.90 ± 55.52 (3/10) | 115.74 ± 76.70 (1/10) | 181.85 ± 68.94 (0/10) | 117.54 ± 79.86 (1/10) | **138.37 ± 93.55** |
| stress4h | r2 | PPO - never charge, USD | 0.00 ± 0.00 (identical) | -80.29 ± 72.84 (8/10) | -14.19 ± 23.63 (3/10) | -78.50 ± 57.77 (8/10) | **-57.66 ± 93.55** |
| stress4h | r2 | PPO - own rule, USD | -49.77 ± 61.42 (8/10) | 40.24 ± 27.48 (1/10) | 106.34 ± 59.12 (0/10) | 42.03 ± 32.46 (1/10) | **62.87 ± 93.55** |
| stress4h | r2 | PPO - ILP, USD | 635.35 ± 65.06 (0/10) | 760.34 ± 123.64 (0/10) | 826.45 ± 88.45 (0/10) | 762.14 ± 126.24 (0/10) | **782.98 ± 93.55** |
| stress4h | r2 | gap vs relaxed ILP, % | 42.85 ± 2.15 | 43.47 ± 3.81 | 45.93 ± 2.60 | 43.51 ± 3.80 | **44.30 ± 3.50** |
| stress4h | r2 | PPO served, % | 65.2 ± 6.1 | 70.6 ± 6.4 | 66.5 ± 5.1 | 70.6 ± 6.8 | **69.2 ± 6.0** |
| stress4h | r2 | kWh bought by PPO | 0.12 ± 0.08 | 1.46 ± 0.32 | 1.07 ± 0.26 | 1.74 ± 0.29 | **1.42 ± 0.84** |
| stress4h | M2+M3 | PPO - best rule, USD | -149.69 ± 58.13 (10/10) | 189.48 ± 75.85 (0/10) | 191.83 ± 72.58 (0/10) | 190.71 ± 75.01 (0/10) | **190.68 ± 2.91** |
| stress4h | M2+M3 | PPO - never charge, USD | 0.03 ± 0.07 (0/10) | -4.43 ± 7.37 (2/10) | -2.09 ± 4.78 (1/10) | -3.21 ± 7.25 (1/10) | **-3.24 ± 2.91** |
| stress4h | M2+M3 | PPO - own rule, USD | -155.14 ± 52.90 (10/10) | 149.30 ± 43.24 (0/10) | 151.64 ± 41.80 (0/10) | 150.52 ± 42.44 (0/10) | **150.49 ± 2.91** |
| stress4h | M2+M3 | PPO - ILP, USD | 449.77 ± 48.94 (0/10) | 834.09 ± 68.48 (0/10) | 836.43 ± 71.24 (0/10) | 835.31 ± 69.10 (0/10) | **835.28 ± 2.91** |
| stress4h | M2+M3 | gap vs relaxed ILP, % | 34.69 ± 2.33 | 46.25 ± 2.49 | 46.31 ± 2.59 | 46.28 ± 2.54 | **46.28 ± 0.08** |
| stress4h | M2+M3 | PPO served, % | 58.5 ± 5.5 | 59.0 ± 5.2 | 59.0 ± 5.2 | 59.0 ± 5.0 | **59.0 ± 0.0** |
| stress4h | M2+M3 | kWh bought by PPO | 0.24 ± 0.23 | 0.84 ± 0.13 | 0.48 ± 0.28 | 0.26 ± 0.22 | **0.53 ± 0.73** |

### 4.8 Training trend per PPO seed (stochastic training policy, instance-adjusted, USD)

Method as in the R6 rl report, Section 4.6: episode cost = -10 x episode return; the training instance of each
episode is reconstructed from gymnasium `np_random(k)` for PPO seed k (anomaly 8); OLS of episode cost on
instance fixed effects and period dummies (first 100 / middle / last 100 episodes); the block-clustered interval
(16-episode blocks) still ignores the slow drift of the policy and is indicative.

| family | riders | PPO seed | cache misses among the largest wall-time increments | R^2 instance FE | raw first-100 -> last-100 | instance-mix shift | **instance-adjusted change** | block-clustered 95 % CI | % of first 100 |
|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | 0 | 145 / 151 | 0.80 | 1239.8 -> 1147.1 | +84.9 | **-189.5** | [-257.3, -121.6] | -15.3 % |
| nyc4h-stress | r2 | 1 | 159 / 161 | 0.85 | 1311.0 -> 1008.0 | -125.6 | **-191.3** | [-237.7, -144.8] | -14.6 % |
| nyc4h-stress | r2 | 2 | 159 / 160 | 0.86 | 1285.5 -> 1139.9 | -1.7 | **-153.7** | [-189.4, -118.0] | -12.0 % |
| nyc4h-stress | M2+M3 | 0 | 147 / 151 | 0.69 | 1321.4 -> 999.7 | -67.6 | **-270.1** | [-354.8, -185.4] | -20.4 % |
| nyc4h-stress | M2+M3 | 1 | 160 / 161 | 0.71 | 1268.3 -> 1002.7 | -40.3 | **-242.8** | [-320.6, -165.0] | -19.1 % |
| nyc4h-stress | M2+M3 | 2 | 160 / 160 | 0.77 | 1282.5 -> 1055.9 | -49.0 | **-190.3** | [-232.3, -148.3] | -14.8 % |
| stress4h | r2 | 0 | 150 / 151 | 0.98 | 1803.1 -> 1974.2 | +177.9 | **-7.9** | [-28.9, +13.1] | -0.4 % |
| stress4h | r2 | 1 | 159 / 161 | 0.99 | 1890.8 -> 1882.5 | -21.6 | **+14.6** | [-2.0, +31.2] | +0.8 % |
| stress4h | r2 | 2 | 158 / 160 | 0.98 | 1864.5 -> 1909.8 | +60.9 | **-16.7** | [-42.8, +9.4] | -0.9 % |
| stress4h | M2+M3 | 0 | 150 / 151 | 0.95 | 1832.2 -> 1912.9 | +55.5 | **+27.0** | [+10.9, +43.1] | +1.5 % |
| stress4h | M2+M3 | 1 | 160 / 161 | 0.95 | 1805.3 -> 1881.7 | +41.5 | **+37.7** | [+23.4, +52.0] | +2.1 % |
| stress4h | M2+M3 | 2 | 160 / 160 | 0.97 | 1816.5 -> 1860.8 | -11.6 | **+60.0** | [+43.7, +76.3] | +3.3 % |

Decile profiles (instance-adjusted, relative to the first tenth of training, USD): nyc4h-stress r2 reaches -91 /
-58 / -56 after the second tenth and -179 / -144 / -140 at the end (seeds 0 / 1 / 2); nyc4h-stress M2+M3 -159 /
-144 / -109 then -232 / -202 / -173; stress4h r2 stays within [-29, +21] throughout for every seed; stress4h
M2+M3 rises to +26 / +40 / +41 and stays there from about the fourth tenth on (seed 2 from the second tenth).

---

## 5. Interpretation

**Shown by these records.**
- *The round-6 verdict on the comparator does not depend on the PPO seed.* With three seeds per cell, no seed in
  any cell is cheaper than the best rule on average, and the cross-seed spread of the PPO mean (2-66 USD) is
  small against the spread over test instances (140-230 USD SD). The single-seed R6 conclusions (i)-(iii) stand,
  with the qualifications of anomalies 2 and 3.
- *The stress4h M2+M3 failure is systematic for this comparator at these settings.* Three independent trainings
  end within 2.3 USD of each other at the never-charge cost, buy less energy the later the seed (0.84, 0.48,
  0.26 kWh), and their stochastic training cost drifts upward in every run. A constant action in their action
  space is cheaper on every test seed. Whatever the mechanism, it is not seed luck.
- *Where PPO learns, it learns the rule and no more.* On nyc4h-stress all three seeds beat never-charge by 450-590
  USD and end within 20 USD of the own rule on average, in both directions on single test seeds. None improves on
  the best rule, which is a per-instance choice between rider layers that a single-rider-layer station agent
  cannot make.
- *The gap band 28-46 % to the relaxed ILP holds across seeds*, always above the best rule's 26-40 %, and the
  served-share deficit of PPO against the ILP is 9.5-35 points in every seed.
- *The legacy "advantage" is a pricing artefact in every seed.* The +190 USD at the new prices against -150 USD at
  the legacy prices on stress4h M2+M3 is reproduced by all three retrained seeds with the same decomposition
  (+486 USD unserved, -72 lateness, -220 response).

**Suggested, not shown.**
- *Why stress4h r2 is seed-sensitive and stress4h M2+M3 is not.* The r2 cell has an intermediate optimum (partial
  charging, 1.1-1.7 kWh) that two seeds find and one half-misses; the M2+M3 cell has the agent at the
  never-charge corner in every seed. A plausible reading is that the reward signal for charging under M2+M3
  riders is weaker or later (reservation swaps smooth demand at the station so a charge decision pays off
  further away in time), but these records do not identify the mechanism (credit assignment, reward
  normalisation, entropy, training length, network size). Three seeds with one hyper-parameter set cannot
  separate seed variance from hyper-parameter sensitivity.
- *Whether more seeds, more steps or tuning would reach charge ASAP on stress4h.* Not tested. The upward drift of
  the training cost in all three M2+M3 runs suggests the problem is not training length alone.
- *What the paper should say.* The comparator statements can drop the "one PPO seed" caveat and quote seed ranges
  (Section 7). The statement that an RL station agent could beat the best rule remains unsupported; a
  two-layer agent with tuned hyper-parameters is the fair test, as the discussion already says.

---

## 6. Figures (`figs/`, PDF + 300-dpi PNG; script `figs/make_rl_seeds_report.py`; Okabe-Ito hues, validated
colour-blind-safe: worst adjacent deutan dE 11.0, normal-vision dE 25.8, contrast >= 3:1 on the light surface)

1. **`fig_rlseeds_paired`** (7.2 in, double column). Panels: PPO minus (a) never charge, (b) own rule station
   layer, (c) best rule, per family and rider layer. Three PPO seeds at the new prices (blue square, vermilion
   circle, green triangle; mean and exact-t 95 % CI paired over 10 test seeds) and the legacy-price single seed
   (hollow grey diamond). Shows: panel (c) all twelve new-price markers right of zero, the legacy stress4h M2+M3
   marker at -150; panel (a) the stress4h M2+M3 markers at zero for every seed; panel (b) the seed-1 outlier on
   stress4h r2.
2. **`fig_rlseeds_service_energy`** (7.2 in). (a) Orders served (%) and (b) energy bought (kWh) per cell: three PPO
   seeds (coloured, CI over 10 test seeds) and the references ILP, best rule, own rule, never charge (black
   marks, means). Shows: the three stress4h M2+M3 seeds at the never-charge served share with 0.3-0.8 kWh; the
   nyc4h-stress seeds at the own-rule level; the stress4h r2 seeds between never-charge and the rule.
3. **`fig_rlseeds_training`** (7.2 in, appendix). Instance-adjusted 100-episode rolling mean of the training
   episode cost, change from the first 100 episodes, one panel per cell, three seeds. Shows: 150-270 USD falls
   on nyc4h-stress in every seed; flat curves on stress4h r2; rises of 25-60 USD on stress4h M2+M3 in every seed.

Each PNG was inspected after rendering (axis labels, legend placement, no clipping).

---

## 7. Manuscript items replaced

`manuscript/PENDING_R6.md` has no numbered item whose re-run is the learning comparator: the calibrated-price PPO
run was already the main result when the list was made. The items that touch this stage, and what changes:

- **Item 17** (learning comparator at the legacy prices, "labelled, no re-run needed"). Unchanged in status. This
  stage adds nothing at the legacy prices; the legacy single-seed values stay as the sensitivity comparison, now
  set against three calibrated-price seeds (Table 4.7). Replacement wording for the S11 sensitivity paragraph and
  the open markers of fig:app:rl-tradeoff / fig:res:rl: "legacy prices, one PPO seed; calibrated prices, three
  PPO seeds (the figure shows seed 0; seed ranges in the text)".
- **Item 20** (values recomputed for the digest, source list includes `outputs/r6_penalty/rl/records.jsonl` for the
  M4 minus best rule contrasts 45.7 / 21.1 USD). Not altered by this stage: those are rule rows, and this stage
  confirms that the rule rows of three independent runs are bit-identical (max difference 0.0 USD), so the rl
  records remain a valid source for them. Status stays "verify" for the digest re-derivation.
- **Item 15** (coverage tables tab:data:seeds, tab:app:coverage-legacy, online rows). Add the rl_seeds rows: "PPO
  seeds 1 and 2, calibrated prices, 488 records (`outputs/r6_fill/rl_seeds`), 8 trainings complete (200,704 steps),
  no ILP solves (reference ILP of the rl stage reused: nyc4h-stress 10 of 10 optimal at 300 s, stress4h 5 optimal
  and 5 time-limited, 0.32-1.12 %)".

Caveats and single-seed statements replaced (these are the "one PPO seed" clauses that R6 left in the text; the
new statement follows each):

- **6.10, `sections/06b_results.tex`, first paragraph** ("PPO is not cheaper than the best rule in any cell: +37.6
  USD ... +189.5 (113.6-265.3, dearer on 10 of 10 seeds)"). New: "PPO is not cheaper than the best rule in any
  cell or for any of three training seeds: across seeds +47.1 ± 22.6 and +91.8 ± 15.1 USD on nyc4h-stress (r2,
  M2+M3) and +138.4 ± 93.5 and +190.7 ± 2.9 USD on stress4h (mean ± exact-t 95 % CI over the three seed means,
  n = 3; seed-averaged policy over the ten test seeds: +47.1 ± 64.4, not significant; +91.8 ± 74.9; +138.4 ± 68.1;
  +190.7 ± 74.3). PPO is cheaper than the best rule on 4 of 120 seed x instance evaluations, by at most 16.4 USD."
  Gaps: "The ILP is 28.7 ± 1.7 % and 31.4 ± 0.9 % cheaper than PPO on nyc4h-stress and 44.3 ± 3.5 % and
  46.3 ± 0.1 % on stress4h (across three PPO seeds; seed ranges 28.0-29.3, 31.1-31.8, 43.5-45.9, 46.25-46.31 %)".
- **6.10, third paragraph** ("the agent reproduces its own rule station layer ... cost difference -1.1 USD ...
  the same served orders on 9 of 10 seeds"). New: "the agent ends near its own rule station layer, which there
  charges whenever a charger is free: across three seeds the cost difference is +8.4 ± 22.6 USD with r2 riders
  and +4.2 ± 15.1 with M2+M3 riders (seed means -1.1 to +17.0 and -1.9 to +10.2, none significant), the served
  share is within one point of the rule's, and it beats never charging by 452-471 and 575-588 USD on every test
  seed in every seed; on single test seeds it deviates from the rule by up to 150 USD in either direction".
- **6.10, third paragraph, stress4h** ("with r2 riders it charges about 60 % of what the rule charges and is 40.2
  USD dearer than its rule; with M2+M3 riders it stays at the service level of never charging (59.0 against 58.5
  %) ... 189.5 USD more than the best rule ... charge-at-every-site action ... cheaper on every seed (by 176.5
  USD)"). New: "with r2 riders it charges 43-70 % of what the rule charges (1.07-1.74 kWh against 2.48) and is
  40-106 USD dearer than its rule depending on the seed (one of three seeds half-collapses to never charging);
  with M2+M3 riders all three seeds stay at the service level of never charging (59.0 against 58.5 %; served
  share identical to never charging on 8-9 of 10 test seeds), which costs 190.7 ± 2.9 USD more than the best rule
  across seeds (189.5-191.8), although the constant charge-at-every-site action inside the action space is
  cheaper on every test seed for every seed (by 176.5-178.8 USD)".
- **6.10, "a learning failure of the comparator (one PPO seed, default hyperparameters, 200,704 steps)"**. New:
  "a learning failure of the comparator that three training seeds reproduce (default hyperparameters, 200,704
  steps each)". Training sentence: "its instance-adjusted training cost did not improve on this family in any
  seed (-7.9, +14.6 and -16.7 USD with r2 riders; +27.0, +37.7 and +60.0 USD, all worse, with M2+M3 riders, from
  the first to the last 100 episodes) whereas it fell by 154-191 and 190-270 USD on nyc4h-stress".
- **S11, `supplement/s11_learning.tex`, Table tab:res:rl and text**: give the PPO rows as the across-seed mean with
  the seed range, or add seed-1 and seed-2 rows (Table 4.2 of this report); replace "one PPO seed with default
  hyperparameters did not find the constant charge action" by "three PPO seeds with default hyperparameters did
  not find the constant charge action (energy bought 0.84, 0.48 and 0.26 kWh per window; never-charge cost on 8,
  9 and 9 of 10 test seeds)"; S11 training paragraph: add the seed-1 and seed-2 changes (Table 4.8) and the
  reconstruction note that the environment seed equals the PPO seed.
- **S2, `supplement/s02_methods_details.tex` line 150** ("with one PPO seed and no hyperparameter tuning") and
  **4.7, `sections/04_methods.tex` line 104** ("(one PPO seed, no hyperparameter tuning)"), **S4 Table of
  parameters, `supplement/s04_costs_parameters.tex` line 241** ("one PPO seed"). New: "three PPO seeds (0, 1, 2;
  the environment is seeded with the PPO seed) and no hyperparameter tuning".
- **7.4 / discussion, `sections/07_discussion.tex` line 38** ("a learned controller of both layers, trained over
  several seeds with tuned hyperparameters, would test learning more fairly"). New: "a learned controller of both
  layers with tuned hyperparameters would test learning more fairly; three seeds of the station-only agent agree
  on its ranking, so seed variance is not what limits the present comparator".
- **`outputs/R6_DIGEST.md`, caveat 10** ("One PPO seed, default hyper-parameters and 200,704 steps. The stress4h
  failure may be fixable by ..."). New: "Three PPO seeds, default hyper-parameters, 200,704 steps each; the
  stress4h M2+M3 failure is reproduced by every seed and the stress4h r2 cell is seed-dependent (one of three
  seeds half-collapses); hyper-parameter tuning and longer training remain untested".

---

## Appendix A. PPO end-adjusted cost per test seed and PPO seed (USD), with the references

| family | riders | test seed | PPO seed 0 | PPO seed 1 | PPO seed 2 | own rule | best rule (rule) | never charge | charge ASAP | ILP relaxed (status) |
|---|---|---|---|---|---|---|---|---|---|---|
| nyc4h-stress | r2 | 0 | 1201.77 | 1201.77 | 1201.77 | 1201.77 | 1201.77 (r2) | 1589.01 | 1201.77 | 783.16 (OPT) |
| nyc4h-stress | r2 | 1 | 1039.70 | 1039.70 | 1039.79 | 1039.70 | 1039.70 (r2) | 1473.55 | 1039.70 | 752.75 (OPT) |
| nyc4h-stress | r2 | 2 | 942.02 | 942.02 | 986.96 | 936.52 | 936.52 (r2) | 1468.95 | 936.52 | 721.17 (OPT) |
| nyc4h-stress | r2 | 3 | 1134.18 | 1134.18 | 1134.18 | 1134.18 | 1031.40 (M2) | 1467.26 | 1134.18 | 790.38 (OPT) |
| nyc4h-stress | r2 | 4 | 1304.64 | 1304.64 | 1304.64 | 1304.64 | 1020.79 (M2) | 1533.25 | 1304.64 | 778.83 (OPT) |
| nyc4h-stress | r2 | 5 | 866.84 | 866.84 | 866.84 | 866.84 | 866.84 (r2) | 1517.91 | 866.84 | 722.87 (OPT) |
| nyc4h-stress | r2 | 6 | 979.19 | 984.71 | 979.19 | 979.19 | 979.19 (r2) | 1498.08 | 979.19 | 716.10 (OPT) |
| nyc4h-stress | r2 | 7 | 1054.13 | 1054.13 | 1054.13 | 1054.13 | 1054.13 (r2) | 1654.58 | 1054.13 | 807.81 (OPT) |
| nyc4h-stress | r2 | 8 | 1177.45 | 1186.05 | 1177.45 | 1177.45 | 1177.45 (r2) | 1678.43 | 1177.45 | 810.30 (OPT) |
| nyc4h-stress | r2 | 9 | 852.50 | 1019.77 | 910.85 | 869.14 | 868.90 (M2) | 1376.85 | 869.14 | 634.71 (OPT) |
| nyc4h-stress | M2+M3 | 0 | 1207.03 | 1206.99 | 1206.80 | 1207.03 | 1201.77 (r2) | 1705.72 | 1207.03 | 783.16 (OPT) |
| nyc4h-stress | M2+M3 | 1 | 1168.39 | 1168.52 | 1168.39 | 1168.52 | 1039.70 (r2) | 1586.39 | 1168.52 | 752.75 (OPT) |
| nyc4h-stress | M2+M3 | 2 | 1006.27 | 942.68 | 942.68 | 1006.27 | 936.52 (r2) | 1661.80 | 1006.27 | 721.17 (OPT) |
| nyc4h-stress | M2+M3 | 3 | 1031.40 | 1034.76 | 1031.43 | 1031.40 | 1031.40 (M2) | 1625.07 | 1031.40 | 790.38 (OPT) |
| nyc4h-stress | M2+M3 | 4 | 1023.54 | 1020.79 | 1128.66 | 1020.79 | 1020.79 (M2) | 1727.60 | 1020.79 | 778.83 (OPT) |
| nyc4h-stress | M2+M3 | 5 | 1004.29 | 1004.29 | 980.19 | 1004.29 | 866.84 (r2) | 1719.68 | 1004.29 | 722.87 (OPT) |
| nyc4h-stress | M2+M3 | 6 | 1017.24 | 1017.22 | 1019.99 | 1017.22 | 979.19 (r2) | 1639.22 | 1017.22 | 716.10 (OPT) |
| nyc4h-stress | M2+M3 | 7 | 1380.54 | 1380.59 | 1380.38 | 1380.59 | 1054.13 (r2) | 1806.56 | 1380.59 | 807.81 (OPT) |
| nyc4h-stress | M2+M3 | 8 | 1387.02 | 1348.08 | 1386.77 | 1348.13 | 1177.45 (r2) | 1771.84 | 1348.13 | 810.30 (OPT) |
| nyc4h-stress | M2+M3 | 9 | 868.81 | 910.27 | 910.13 | 868.90 | 868.90 (M2) | 1666.24 | 868.90 | 634.71 (OPT) |
| stress4h | r2 | 0 | 1170.02 | 1444.38 | 1170.12 | 1183.98 | 1183.98 (r2) | 1444.38 | 1265.73 | 787.82 (OPT) |
| stress4h | r2 | 1 | 1968.94 | 1968.99 | 1968.99 | 1960.66 | 1684.78 (M2) | 1968.99 | 1676.50 | 1034.02 (TL 1.12 %) |
| stress4h | r2 | 2 | 1791.46 | 1791.28 | 1791.28 | 1758.22 | 1730.79 (M2) | 1791.28 | 1719.76 | 1015.58 (TL 0.32 %) |
| stress4h | r2 | 3 | 1797.49 | 1851.49 | 1770.45 | 1761.74 | 1754.85 (M2) | 1851.31 | 1755.07 | 958.82 (TL 0.43 %) |
| stress4h | r2 | 4 | 1605.19 | 1809.17 | 1721.60 | 1571.11 | 1554.41 (M2) | 1830.00 | 1554.41 | 913.79 (OPT) |
| stress4h | r2 | 5 | 1782.94 | 1793.30 | 1762.73 | 1738.18 | 1499.05 (M2) | 1793.30 | 1499.05 | 960.84 (TL 0.49 %) |
| stress4h | r2 | 6 | 2078.92 | 2129.83 | 2111.48 | 2056.62 | 1867.60 (M2) | 2235.39 | 1745.62 | 1066.47 (TL 0.54 %) |
| stress4h | r2 | 7 | 1671.98 | 1690.98 | 1610.70 | 1559.67 | 1559.67 (r2) | 1690.98 | 1647.67 | 893.29 (OPT) |
| stress4h | r2 | 8 | 1798.98 | 1863.19 | 1807.14 | 1772.65 | 1772.65 (r2) | 1863.19 | 1855.93 | 1164.12 (OPT) |
| stress4h | r2 | 9 | 1632.72 | 1617.09 | 1602.12 | 1533.43 | 1533.43 (r2) | 1632.72 | 1533.53 | 900.45 (OPT) |
| stress4h | M2+M3 | 0 | 1571.27 | 1571.10 | 1571.10 | 1307.42 | 1183.98 (r2) | 1571.10 | 1265.73 | 787.82 (OPT) |
| stress4h | M2+M3 | 1 | 1756.35 | 1756.20 | 1756.20 | 1684.78 | 1684.78 (M2) | 1756.20 | 1676.50 | 1034.02 (TL 1.12 %) |
| stress4h | M2+M3 | 2 | 1884.64 | 1884.64 | 1884.46 | 1730.79 | 1730.79 (M2) | 1884.46 | 1719.76 | 1015.58 (TL 0.32 %) |
| stress4h | M2+M3 | 3 | 1858.18 | 1889.14 | 1889.14 | 1754.85 | 1754.85 (M2) | 1889.14 | 1755.07 | 958.82 (TL 0.43 %) |
| stress4h | M2+M3 | 4 | 1646.25 | 1646.25 | 1646.25 | 1554.41 | 1554.41 (M2) | 1646.25 | 1554.41 | 913.79 (OPT) |
| stress4h | M2+M3 | 5 | 1695.64 | 1695.64 | 1695.64 | 1499.05 | 1499.05 (M2) | 1695.64 | 1499.05 | 960.84 (TL 0.49 %) |
| stress4h | M2+M3 | 6 | 2006.37 | 2020.25 | 1988.19 | 1867.60 | 1867.60 (M2) | 2020.25 | 1745.62 | 1066.47 (TL 0.54 %) |
| stress4h | M2+M3 | 7 | 1890.14 | 1890.14 | 1890.14 | 1681.25 | 1559.67 (r2) | 1890.14 | 1647.67 | 893.29 (OPT) |
| stress4h | M2+M3 | 8 | 2040.44 | 2019.35 | 2040.44 | 1878.32 | 1772.65 (r2) | 2040.44 | 1855.93 | 1164.12 (OPT) |
| stress4h | M2+M3 | 9 | 1686.76 | 1686.76 | 1686.76 | 1584.64 | 1533.43 (r2) | 1686.76 | 1551.34 | 900.45 (OPT) |

Rule M2 equals rule M2+M3 on every test seed (no transfer services). Costs printed to 0.01 USD; differences below
that (for example 1968.94 against 1968.99 on stress4h r2 test seed 1) are the end-state adjustment of a schedule
that serves the same orders.

## Appendix B. Files

`records.jsonl` (seeds 1-2, 488 rows), `seed1/`, `seed2/` (X7 run folders with `records.jsonl`, `instances/`,
`models/<family>_<rider>/{ppo_station.zip, vecnormalize.pkl, monitor.csv}`, `run_stdout.log`, `wall_time.json`,
auto `RESULTS.md`), auto `RESULTS.md`, `per_test_seed.csv`, `training.csv`, `summary_by_ppo_seed.csv`,
`summary_across_ppo_seeds.csv`, `summary_pooled.csv` (do not quote, anomaly 6); this report's
`figs/make_rl_seeds_report.py`, `figs/rl_seeds_tables.json`, `figs/tables.md`, `figs/per_test_seed_recomputed.csv`,
`figs/fig_rlseeds_{paired,service_energy,training}.{pdf,png}`.
