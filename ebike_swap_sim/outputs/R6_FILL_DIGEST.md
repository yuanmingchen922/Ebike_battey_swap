# Round 6 fill digest, part 1: retries, transfers, stress, pack sizes, levers and PPO seeds

**Part 1 of 2: rolling_ext, compliance and the second siting pass follow in part 2.** Nothing in this file reports
on those three stages.

Date: 2026-10-20. The fill round completes the experiments that round 6 (R6, `R6_DIGEST.md`) had not re-run at the
new prices: P 60 USD per unserved order, w 18 USD/h of response from release, v 15 USD/h of lateness from the promise.
The legacy prices are P 30 / v 36. Plan: `notes/DECISIONS.md`, sections "R6 fill-in script and the retry rule",
"Smoke fixes (2026-10-19)" and "Fleet retry reused on the server (2026-10-19)". Code: `experiments/r6_fill.py` and
`experiments/r6_penalty.py`.

**Inputs.** The six corrected stage reports. They include the verification corrections where claims were refuted.
- `outputs/r6_fill/RETRIES_final.md`: the retries of the R6 grid and X5 stages.
- `outputs/r6_fill/transfers/RESULTS_final.md`
- `outputs/r6_fill/stress/RESULTS_final.md`
- `outputs/r6_fill/pack/RESULTS_final.md`
- `outputs/r6_fill/levers_ext/RESULTS_final.md`
- `outputs/r6_fill/rl_seeds/RESULTS_final.md`

They are read together with `R6_DIGEST.md` and `manuscript/PENDING_R6.md`. Every number below is taken from these
reports. The reports in turn recomputed every number from the stage `records.jsonl` files; no solver was run for
them or for this digest. I re-counted two things from the records:
- retry rows: 55 in total (headline 3, psweep 23, vsweep 2, fleet 16, levers 11); 3 are `retry_worse`, all fleet;
  10 are OPTIMAL;
- transfer ILP rows: 74 OPTIMAL and 16 TIME_LIMIT of 90.

**Conventions** (as in R6):
- Families: usd4h, nyc4h, stress4h, stress4h-K8, stress4h-K10, stress8h, nyc4h-stress.
- Rules: r2, M2, M3, M2+M3, M4. The best rule is the per-instance minimum of the end-adjusted cost.
- The headline is relaxed end targets (rho 0, R_end 0) on the end-adjusted cost; written targets measure the price
  of recovery.
- Gap = 100 (best rule - ILP) / best rule, computed per instance and then averaged.
- Intervals are exact Student-t 95 % CIs over seeds, written `[lo, hi]` or `+-` half-width. Differences are paired
  by seed.
- "OPT" means optimal and "TL" means time limit, followed by the Gurobi MIP gap. "Upper limit" is the gap computed
  against the proven bound.
- Costs are in USD per 4-h window unless stated.

---

## 1. Short answers

1. **The retries change no R6 conclusion.** 55 ILP rows were re-solved: 10 are now optimal, 42 remain time-limited
   with smaller MIP gaps (at most 3.38 %), and 3 fleet re-solves were worse and are ignored. The headline moves
   by rounding only: pooled usd4h 25.10 -> 25.11 % [20.15, 30.07], x1.5 38.42 -> 38.44 % [35.37, 41.51]. The three
   sleep-truncated cells are now solved and equal the best-known substitutes the R6 reports had used.
2. **The retries matter at the station levers.** The stress4h-K8 reference gap rises 46.14 -> 47.59 % [42.16, 53.03]
   (upper limit 48.26). No on-site charging costs the ILP +262.96 USD [216.81, 309.11], at least 207.7 USD on every
   seed (was +228.53). The demand-charge break-even rises to at least about 24,900 USD per kW-month (was 20,400). The
   lock-out "paradox" is gone: the lock-out of two spares now costs +9.78 USD [-4.88, 24.43], positive on 5/5 seeds,
   and exactly +2.52 USD on seed 4.
3. **Transfers: worth nothing without end targets, about one order per window under enforced recovery.** In all 45
   relaxed solves no battery was moved. Under written targets in the separated layouts, transfers on cyclic tours
   are worth 63.87 / 64.64 USD per window on incumbents (one hub / two hubs), 9.1 / 8.8 % of the ILP cost; at the
   legacy prices the value was 16.40 / 17.39 USD (2.6-2.7 %). They are provably positive on 5/5 seeds. Separation
   never pays, and no rule-based transfer policy beats r2 in any of 60 cells. Relaxed gap: 24.15 % [13.44, 34.86],
   with the seed means as units.
4. **The gap keeps rising with the fleet at the new prices.** 40.03 % (6 bikes) -> 47.59 % (8) -> 50.21 % [46.99,
   53.43] (10; a lower bound, at most 53.77 %). Welch tests: 6 -> 8 p 0.026, 6 -> 10 p 0.003, 8 -> 10 p 0.29.
   stress8h: 42.77 % [13.51, 72.03] (n 3, a lower bound). The battery side binds from 8 bikes on: the LP value of a
   spare is 0.70 / 9.81 / 77.95 USD per site and window at 6 / 8 / 10 bikes.
5. **End targets at 6 bikes cost little where they are resolved, and full battery return costs clearly more.** The
   price of recovery is 0.77 USD on seed 0 (exact) and at most about 10 USD on seed 4. Full battery return is proven
   to cost at least 9.23 USD (seed 1) and 55.39 USD (seed 2). 10 of 27 written and grid solves found no incumbent in
   300 s.
6. **Pack size changes the rule's best design cost little.** Cost-minimal system cost: 1684.9 / 1619.6 / 1611.8 /
   1606.8 USD at 0.5 / 0.6 / 0.75 / 1.0 kWh. Only the 0.5 kWh penalty is measurable: +50.8 USD [32.1, 69.4] against
   0.6 kWh. At every pack the rule's design stays 150-201 USD (9.4-12.2 %) above the ILP's 0.6 kWh design. The
   legacy "significant negative spare value" (-9.33 USD) does not survive repricing: -1.7 [-16.9, 13.5].
7. **Of the five station levers, only on-site charging matters to the ILP.** The other four stay within proven
   ceilings of 2.5-41 USD per seed. Faster chargers lower the best rule's cost by 309.2 USD [70.4, 548.1], but that
   lever also coarsens the energy rounding to 50 Wh levels.
8. **Three PPO seeds confirm the single-seed R6 conclusions.**
   - PPO is never cheaper than the best rule: all 12 seed x cell means are positive.
   - The stress4h M2+M3 collapse to never-charge appears in every seed.
   - The nyc4h-stress match to the own rule holds on average, but less tightly than for seed 0.
   - stress4h with r2 riders is seed-dependent.
   - ILP-vs-PPO gaps: 28.72 / 31.42 / 44.30 / 46.28 % across seeds; the R6 range of 28-46 % stands.

---

## 2. Coverage

| Stage | Records | ILP status | Time limit, machine | Wall time / budget |
|---|---|---|---|---|
| retries | 55 retry rows appended to `r6_penalty/{headline,psweep,vsweep,fleet,levers}/records.jsonl` (headline 3, psweep 23, vsweep 2, fleet 16, levers 11) | 10 OPT, 42 TL, 3 `retry_worse` (ignored). MIP start accepted, `obj_eq_eval` and `check_ok` true, model dimensions and instance hashes equal on 55/55. No retry row is sleep-truncated | 600 s on an x86-64 Linux server (headline, psweep, vsweep, fleet); 1800 s on the laptop (levers) | wall clocks 2026-10-19 16:31 to 2026-10-20 02:41 (server and laptop clocks mixed) |
| transfers | 390 (90 ILP, 300 rule) | 74 OPT + 16 TL (max 2.89 %). 1 TL row certified by nesting, 15 open. Not retried | 300 s, laptop | 3.46 h (12,467 s); legacy run 2.31 h |
| stress | 236 (37 ILP, 23 LP, 176 rule) | 6-bike written: 1 OPT + 4 TL (1.15-4.90 %), seed 2 without incumbent. Grid: 6 OPT + 20 TL, 9 of them without incumbent. K10: 0 OPT + 5 TL (3.65-13.31 %). stress8h: 0 OPT + 3 TL (4.86-8.98 %). 23 LPs LP_OPTIMAL | 300 s (6 bikes), 600 s (K10, 8 h); joins the 1800 s K8 reference | 16,106 s / 24,000 s |
| pack | 576 (144 rule-only instances x r2, M2, M2+M3, best rule) | no ILP (by plan). The 0.6 kWh ILP reference is the retried fleet grid: 29 OPT + 19 TL of 48 | - | 497.9 s / 2,700 s |
| levers_ext | 75 new (15 keys x 5 methods; `lockout0.1` shares the key of `lockout0.05`) | faster chargers 3 OPT + 2 TL (2.66, 0.41 %); second swap position 0 + 5 TL (0.84-7.52 %); lock-out of 1 spare 0 + 5 TL (0.41-5.65 %). Reused rows: reference 1 OPT + 4 TL (0.75-2.87 %, 1800 s); 2-spare lock-out 1 + 4 TL (1.05-3.26 %, 1800 s); no on-site charging 4 OPT + 1 TL (0.32 %) | 600 s (new cells), laptop | 138.0 min / 270 |
| rl_seeds | 488 (PPO seeds 1-2; 8 trainings TRAINED at 200,704 steps / 4,181 episodes) | no ILP solved. Reference ILP of the rl stage reused: nyc4h-stress 10 OPT; stress4h 5 OPT + 5 TL (0.32-1.12 %) | 300 s (reference) | 72.9 / 135 min (seed 1), 64.4 / 135 min (seed 2) |

Across the five new stages:
- no SKIPPED_BUDGET or ERROR rows;
- every row carries P 60 / w 18 / v 15;
- demand (or order) hashes equal the legacy instances wherever a legacy comparison is made.

The `lockout0.1` reuse that the task flagged for seed 4 is legitimate, and it occurs on all five seeds, not only
seed 4. The 5 % and 10 % shares both round to one locked battery, the slot and site draws are identical, and the
content keys are equal per seed (de20be62, 88dddffb, ad4074d4, 0904d97f, dae2a212). One solve serves both labels,
and the lever is counted once. This is confirmed by the levers_ext and retries reports.

---

## 3. Verification outcome

Two independent refuters checked every stage report. Claims refuted by at least one refuter were recomputed from the
records and corrected in the stage `RESULTS_final.md`, in its "Verification corrections" section. No ILP was
re-solved in any correction.

| Stage | Refuted claims | Verdicts | What was wrong | Numbers changed? |
|---|---|---|---|---|
| retries | none | - | - | - |
| transfers | C1: relaxed transfers-allowed optimum equals the transfer-free optimum on every instance | both refuters | Nesting was applied in the wrong direction. Only 1 of 16 TL rows is certified (relaxed, 1 hub, no transfers, seed 3). Two rows are open: relaxed 2 hubs, shuttles, seed 3, optimum in 667.40-671.46 (value of transfers 0-4.06 USD); written co-located cyclic seed 3, optimum in 610.21-613.33. Equality is proven on 29 of 30 pairs | no table value; wording and certification only |
| transfers | C2: value of cyclic transfers with 1 hub, 63.87 USD | one refuter | Solve status and n missing from the prose. Bracket 61.73-65.83; smallest provable value 26.47 (seed 0) | no |
| transfers | C6: legacy vs new price of recovery (+47.60; cyclic +0.14) | both | Solve status missing. The no-transfer change is bounded in +45.47 to +47.60, the cyclic change in -1.82 to +0.14. "Unchanged within 1 USD" becomes "within 2 USD on incumbents" | bracket columns added; the legacy-vs-new figure redrawn |
| stress | C5: full battery return costs at least 8.49 USD on seed 1 | both | The seed-1 relaxed reference was not the best known (fleet K6_B2_pack0.6 retry: 1028.748). The bound is now 9.23 USD; seed 2 stays at 55.39 | yes: seed-1 PoR +0.74 USD in every cell (written 4.85 -> 5.59 raw, 4.72 end-adjusted); seed-2 upper ends 175.29 / 151.81; 6-bike gap 40.03 [34.62, 45.45]; verdicts unchanged |
| pack | none | - | - | - |
| levers_ext | C2: second swap position "cannot raise the optimum" | both | It adds a +0.119 USD set-up, so the bracket's upper end is +0.12, not 0. +33.48 is end-adjusted (raw +33.51). The 600 s vs 1800 s asymmetry is now stated: -1.37 [-38.04, 35.31] against the 600 s reference | only the upper ends move, by 0.12 USD |
| levers_ext | C3: faster-charger mechanism ("half-range packs") | both | hp = hd = 1 are durations, not energy levels. The real effect is coarser rounding: about 10-12 % more modelled energy per delivery arc, and pack range about 8.2 -> 6.8 loaded legs. The lever now reads "chargers twice as fast, with energy rounded to 50 Wh levels" | no table value or figure |
| rl_seeds | none | - | - | - |

**Cross-stage consistency notes.**
- The retries report predicted that the stress stage's seed-1 price of recovery "would read 4.23 instead of 2.49
  USD". That prediction is superseded by the stress correction, which pooled every relaxed solve of the instance:
  the value is 5.59 USD raw, 4.72 end-adjusted, bracket [0, 13.85].
- For the 2-spare lock-out on seed 3, the retries report gives the bracket [0, 17.1] and levers_ext gives [0, 16.9].
  levers_ext uses the best bound over both runs of a key; the retries analysis uses the last row's bound (retries
  anomaly 5). This digest quotes levers_ext.
- The stage-results anomaly list of the transfers stage still calls the written co-located cyclic seed-3 row
  "certified". The corrected report does not, and this digest follows the corrected report.
- The auto-generated `RESULTS.md` files of fleet, levers, stress, pack and levers_ext print "Anomalies: none". Quote
  only the `RESULTS_final.md` files.

---

## 4. Answers by topic

### 4.1 Retries of the R6 grid and X5 stages (`RETRIES_final.md`)

- **Headline.** usd4h x1.5 gap 38.44 +- 3.07 % [35.37, 41.51]: 8 OPT + 2 TL at 600 s (seeds 0 and 8 at 0.87 / 0.90 %),
  upper limit 38.63 (38.62 with the best bound of each cell). Pooled usd4h: 25.11 % [20.15, 30.07] (n 30, 28 OPT),
  upper limit 25.32. Saving 363.32 USD [235.07, 491.57]. Change against the legacy prices: x1.5 -5.00 +- 3.09 points
  (p 0.005, 9/10 seeds lower); pooled -2.05 +- 2.00 (p 0.044). Saving shares (lateness / response / unserved):
  19.1 / 16.8 / 63.9 %. Service share of the pooled saving: 99.8 % (99.82). Headline ILPs optimal: 48/50.
- **Lateness sweep.** v 36 seeds 5 and 6 are OPTIMAL at 645.02 and 626.90 USD, equal to the v 25 optimum repriced
  at v 36. The v 36 gap 31.65 +- 6.56 % [25.09, 38.22] is a solved value (10/10 OPT). Slope 2.09 +- 0.75 points per
  10 USD/h, monotone on 10/10 seeds. v 36 - v 15: +4.31 +- 1.53 points.
- **Penalty sweep** (n 10 per point):
  - stress4h P 40: 35.21 +- 2.19 % (7 OPT + 3 TL, <= 0.40 %);
  - stress4h P 60: 39.73 +- 2.84 % [36.89, 42.57] (5 OPT + 5 TL, <= 0.87 %; upper limit 39.98);
  - stress4h P 80: recorded 44.50 +- 3.03 % [41.47, 47.53], best-known 44.69 +- 3.15 % [41.53, 47.84], upper limit
    45.43 (2 OPT + 8 TL, largest MIP gap 11.63 -> 3.38 %). Seeds 3, 6, 7 are still beaten by the repriced P 60
    schedule, by 11.2 / 9.2 / 15.9 USD;
  - P 80 - P 60 contrast: +4.77 +- 0.74 points recorded (was +4.01 +- 1.50), 10/10 seeds higher;
  - usd4h P 80 seed 0 is OPTIMAL at 532.60 USD; that point's gap is 30.66 +- 6.73 % (10/10 OPT).
- **Fleet grid** (stress4h, 48 orders, 0.6 kWh, n 3). Status 29 OPT + 19 TL of 48. No design conclusion changes:
  - cost-minimal designs: ILP K 8 / B 3 at 1477.9 USD [1307.6, 1648.1], 99.3 % served (not certified); rule K 8 /
    B 4 at 1619.6;
  - per-seed argmins: K 6 / B 2, K 8 / B 2, K 8 / B 3 (all OPT);
  - certified statement: "6-8 bikes with 2-3 spares per site";
  - design saving: 9.4 % [6.5, 12.2] (150.1 USD [90.0, 210.2]);
  - bike values: 4 -> 6 214.1 [193.7, 234.4], 6 -> 8 89.4 [0.3, 178.5], 8 -> 10 17.1 [-13.2, 47.5] USD;
  - a third spare at 6 bikes is now worth -0.11 [-0.86, 0.64] USD (was 0.62);
  - K 10 / B 1 seed 2 is OPTIMAL (837.06 USD); K 10 / B 2 seed 2 was not re-solved (100.5 %, excluded by nesting).
- **Levers** (stress4h-K8, n 5, 1800 s):
  - reference: ILP 1278.7 USD [1086.9, 1470.5]; 1 OPT + 4 TL (1.50, 0.75, 2.87, 1.00 %); gap 47.59 % [42.16, 53.03];
    upper limit 48.26;
  - no on-site charging: +262.96 USD [216.81, 309.11], at least 207.7 per seed; gap change -5.72 [-8.44, -3.01]
    points;
  - demand-charge break-even: at least 24,900 USD per kW-month;
  - lock-out of 2 spares: +9.78 USD [-4.88, 24.43], 5/5 positive; seed 4 exactly +2.52 USD;
  - no lock-out incumbent lies below its reference any more.

### 4.2 Transfers and hub separation (`transfers/RESULTS_final.md`; usd4h x1, seeds 0-4, n 5)

- **Relaxed targets.**
  - Battery movements: none in any of the 45 solves (43 OPT, 2 TL). The transfers-allowed incumbent equals the
    transfer-free value on all 30 pairs. Equality is proven on 29 of 30; on the open pair the value is at most
    4.06 USD.
  - Energy: 42 of 45 solves buy none; the three co-located seed-1 solves buy 0.139 kWh (0.044 USD).
  - Gap to the best rule (r2 on every instance): 24.15 % [13.44, 34.86] with the seed means as units; 24.15 %
    [19.71, 28.59] over the 15 layout-seed cells; 24.21 % raw. Legacy 20.92 %: paired +3.23 points [0.94, 5.51]
    over the cells, higher on 12 of 15.
  - Separation cost: 29.20 USD [29.15, 29.24] with one hub against a fixed charge of 29.19; 57.76 [56.68, 58.83]
    with two hubs against 58.38. Hub nodes enlarge the road graph, so this means "within about 1 USD" of the fixed
    charge, not "exactly".
- **Written targets, separated layouts.**
  - Value of transfers on cyclic tours: 63.87 USD [20.79, 106.94] with 1 hub (bounds 61.73-65.83) and 64.64 [21.18,
    108.11] with 2 hubs (63.30-65.28). That is 9.08 % and 8.82 % of the ILP cost without transfers.
  - On shuttles: 49.24 / 48.78 USD (bounds 47.11-61.38 / 47.43-60.98). Provably positive on 5/5 seeds in all four
    cells. Co-located: 0.00.
  - The value is unserved orders avoided: 72.00 / 84.00 USD, i.e. 1.2 / 1.4 orders at 60 USD. Each service carries
    2.0-2.2 batteries.
  - Legacy: 16.40 / 17.39 USD (2.6-2.7 %), paired +47.46 [7.39, 87.54] and +47.25 [5.56, 88.95].
- **Price of recovery** (written minus relaxed ILP):
  - co-located: 0.27 USD [0.21, 0.34];
  - without transfers: 71.88 [28.27, 115.49] with 1 hub (bounds 69.75-71.88) and 71.74 [26.78, 116.69] with 2 hubs
    (70.39-71.74); legacy 24.28 / 24.15; change +45.47 to +47.60 by the bounds;
  - cyclic tours: 8.01 [7.02, 9.00] (6.05-8.01) and 7.09 [5.23, 8.95] (6.46-7.09); unchanged against legacy within
    2 USD;
  - shuttles: 22.64 / 22.96.
- **Separation cost, written targets.**
  - Without transfers: 100.80 USD [57.16, 144.44] (1 hub) and 129.22 [84.92, 173.52] (2 hubs).
  - Cyclic tours: 36.93 [35.95, 37.92] and 64.58 [63.39, 65.76].
  - Separation does not pay in any setting.
  - Written-target gap to the best rule: 18.62 % [10.14, 27.09] without transfers and 23.56 % [12.81, 34.32] with
    cyclic transfers (seed means). The rules mostly miss the targets: 148 of 150 rule schedules violate them.
- **Cyclic tours vs shuttles.** The ILP is 14.62 / 15.87 USD cheaper on cyclic tours. This is the fare split: the
  same batteries are moved. Only -2.49 / -3.67 USD is provable.
- **Transfer rules.**
  - Neither transfer rule is strictly cheaper than r2 in any of the 60 cells (0 of 60 each).
  - On shuttles, the reorder-point rule costs 116-124 USD more than r2 and M3 71-89 USD more.
  - M3 reads P and ships more at P 60. Its co-located shuttle loss grew by +38.36 USD [7.62, 69.11].
  - The best rule is r2 in all 60 cells.

### 4.3 Stress, 6 to 10 bikes and the 8-hour window (`stress/RESULTS_final.md`)

- **Gaps.**

  | Cell | n | Gap % | Upper limit | ILP status |
  |---|---|---|---|---|
  | stress4h-K10 | 5 | 50.21 [46.99, 53.43] (lower bound) | 53.77 [50.73, 56.81] | 0 OPT + 5 TL (3.65-13.31 %) at 600 s |
  | stress8h | 3 | 42.77 [13.51, 72.03]; per seed 29.2 / 48.8 / 50.3 | 46.96 | 0 OPT + 3 TL (4.86-8.98 %) |

  Legacy values: K10 46.99 % (stress report: 46.93), stress8h 47.91 %. stress8h is lower than legacy on 3/3 seeds,
  provably on seeds 1-2.
- **Fleet axis.** 40.03 % [34.62, 45.45] (6 bikes; 2 OPT + 3 TL, 0.14-0.80 %) -> 47.59 % (8) -> 50.21 % (10).

  | Step | Welch (new prices) | Bound-based | Legacy |
  |---|---|---|---|
  | 6 -> 8 | +7.56 points, p 0.026 | p 0.024 | p 0.092 |
  | 8 -> 10 | +2.62 points, p 0.29 | p 0.061 | p 0.54 |
  | 6 -> 10 | +10.18 points, p 0.003 | p 0.0008 | p 0.038 |

- **Served shares, ILP vs best rule.** 0.954 vs 0.754 (6 bikes), 0.925 vs 0.653 (8), 0.907 vs 0.593 (10), 0.910 vs
  0.729 (8 h). Paired, the ILP serves more than at the legacy prices: +0.079 / +0.059 / +0.035 / +0.031, all CIs
  above zero. No ILP order is more than 60 min late.
- **Written targets, 6 bikes.**
  - Gap: 38.78 % [32.58, 44.98] (n 4) against 39.71 % relaxed on the same seeds, a difference of -0.93 [-3.01,
    1.15] points.
  - Price of recovery, raw, per seed: 0.77 USD (seed 0, exact, 0.10 % of the relaxed optimum); 5.59 in [0, 13.85]
    (seed 1); unknown (seed 2, no incumbent); 50.70 in [1.34, 52.01] (seed 3, 4.90 % MIP gap); 9.97 in [0, 9.97]
    (seed 4; strictly [0, 10.00]).
  - Do not quote the 4-seed mean (16.76 [-19.74, 53.26]). Legacy: 3.20 [0.18, 6.21] (n 5).
- **End-target grid** (seeds 0-2, 300 s).
  - Every rho <= 0.5 cell costs 0.48-0.77 USD on seed 0 (OPT) and at most 9.25-18.83 USD on seed 1. Seed 2 is
    unresolved for rho <= 0.5.
  - Full battery return (rho 1, either R_end, and the periodic bracket) is proven to cost at least 9.23 USD on
    seed 1 and 55.39 USD on seed 2. Upper ends: 69.68 USD (seed 0, rho 1 / R_end 1); 175.29 and 151.81 USD on
    seed 2.
  - Seed 0 is not resolved for full return.
  - 10 of 27 solves found no incumbent (legacy: 1 of 24).
- **LP operating values per site and window** (n 5; per 8-h window for stress8h, n 3).

  | Cell | Spare (new prices) | Spare / set-up 0.332 USD | Spare (legacy) | Charger (new prices) | Charger (legacy) |
  |---|---|---|---|---|---|
  | 6 bikes | 0.70 [0.17, 1.24] | 2.1 x | 0.45 | 0.03 [-0.02, 0.08] (below its 0.082 USD set-up) | 0.07 |
  | 8 bikes | 9.81 [4.64, 14.98] | 30 x | 2.79 | 8.78 [2.60, 14.96] | 1.29 |
  | 10 bikes | 77.95 [38.30, 117.60] | 235 x | 21.87 | 65.86 [29.70, 102.03] | 16.67 |
  | 6 bikes, written targets | 2.28 [0.24, 4.31] | - | - | 0.75 [-0.06, 1.56] | - |
  | stress8h | 1.25 [-0.26, 2.76] | - | - | 0.41 [-0.60, 1.42] | - |

  Paired rise of the spare value: +0.25 [-0.36, 0.87], +7.01 [3.04, 10.99], +56.08 [24.30, 87.85]. The ordering
  and the break-even between 6 and 8 bikes are unchanged.
- **Stock-out slot-sites.** ILP 91.0 vs rule 70.8 (6 bikes, seeds 0-2); 97.6 vs 105.8 (10 bikes).

### 4.4 Pack size (`pack/RESULTS_final.md`; rule only, stress4h fleet grid, n 3)

- **Cost-minimal best-rule design.** K 10 / B 4 at 0.5 kWh and K 8 / B 4 at 0.6, 0.75 and 1.0 kWh, serving
  97.9-99.3 % of orders. Legacy: 1688.3 / 1587.7 (n 2) / 1647.8 / 1637.5. The legacy 0.6 kWh advantage was partly
  seed composition.

  | Pack (kWh) | System cost (USD) |
  |---|---|
  | 0.5 | 1684.9 [1530.4, 1839.4] |
  | 0.6 | 1619.6 [1256.2, 1983.0] |
  | 0.75 | 1611.8 [1264.7, 1959.0] |
  | 1.0 | 1606.8 [1318.0, 1895.6] |

- **Pack effect at each pack's per-seed cost-minimal design, against 0.6 kWh.** 0.5 kWh: +50.8 USD [32.1, 69.4]
  (3.1 %, all 3 seeds). 0.75 kWh: +9.0 [-62.8, 80.7]. 1.0 kWh: +5.3 [-59.6, 70.2]. Averaged over the 16 designs,
  1.0 kWh is 72.4 USD cheaper than 0.6 kWh [-177.9, 33.0], and 136-231 USD cheaper at one spare per site.
- **Mechanism: unserved orders.** At K 8 / B 4, 1.0 vs 0.5 kWh serves 2.0 [-0.5, 4.5] more orders with 6.0 fewer
  swaps. The step saves 105.7 USD at the new prices against 60.9 at the legacy prices. The identity "new minus
  legacy = 30 USD per unserved order - 21 USD per lateness hour" holds on 432/432 rule rows.
- **Rule vs ILP.** At every pack the rule's design costs 150-201 USD more than the ILP's 0.6 kWh design at the same
  served share; the CIs exclude zero.

  | Rule pack (kWh) | Rule design minus ILP 0.6 kWh design (USD) | Relative |
  |---|---|---|
  | 0.5 | 200.9 [153.2, 248.5] | 12.2 % |
  | 0.6 | 150.1 [90.0, 210.2] | 9.4 % |
  | 0.75 | 159.1 [96.2, 222.0] | 9.8 % |
  | 1.0 | 155.4 [141.5, 169.3] | 9.7 % |

- **Spares and bikes.**
  - A fourth spare per site pays the rule 20.9-26.4 USD at 0.5-0.75 kWh but only 2.4 [-9.6, 14.4] USD at 1.0 kWh.
  - Bikes 9-10 pay the rule only at 0.5 kWh.
  - At 4 bikes / 2 spares a further spare is worth -1.7 [-16.9, 13.5] USD at 0.5 kWh (legacy -9.33 [-12.79,
    -5.88]), +0.7 [-42.0, 43.4] at 0.6, -2.4 [-16.5, 11.7] at 0.75 and -1.8 [-7.2, 3.5] at 1.0.

### 4.5 Station levers (`levers_ext/RESULTS_final.md`; stress4h-K8, seeds 0-4)

ILP brackets are on raw totals: [lever bound - reference incumbent, lever incumbent - reference bound].

| Lever | ILP status | ILP change, measured (USD) | Proven bracket per seed (USD) | Best-rule change (USD) | Gap % |
|---|---|---|---|---|---|
| Reference | 1 OPT + 4 TL, 1800 s | - | - | - | 47.59 [42.16, 53.03] (<= 48.26) |
| Faster chargers (50 Wh levels) | 3 OPT + 2 TL, 600 s | -1.58 [-14.80, 11.63] | [-14.7, 0.9], [4.7, 15.2], [-29.0, 38.3], [-16.6, 3.1], [10.1, 10.1] | -309.23 [-548.06, -70.40], 0/5 > 0; served +12.8 points | 39.84 [38.05, 41.64] |
| Second swap position | 0 OPT + 5 TL, 600 s | +33.48 [1.98, 64.97] (time-limit artefact; -1.37 [-38.04, 35.31] against the 600 s reference rows) | saving at most 16.4 / 10.4 / 35.3 / 14.5 / 4.1; increase at most +0.12 | +2.40 [-3.94, 8.74] | 46.23 [41.98, 50.48] |
| Lock-out of 1 spare | 0 OPT + 5 TL, 600 s | +11.79 [-5.34, 28.92], 5/5 > 0 | [0, 20.6], [0, 22.3], [0, 40.7], [0, 16.9], [0, 2.5] | +40.78 [-61.54, 143.09] | 47.94 [43.06, 52.83] |
| Lock-out of 2 spares | 1 OPT + 4 TL, 1800 s | +9.78 [-4.88, 24.43], 5/5 > 0 | [0, 25.3], [0, 41.3], [0, 40.7], [0, 16.9], [2.5, 2.5] | +60.11 [-95.75, 215.97] | 48.39 [43.34, 53.44] |
| No on-site charging | 4 OPT + 1 TL | +262.96 [216.81, 309.11], 5/5 | at least 207.7 on every seed | +213.51 [123.95, 303.07], 5/5 | 41.87 [37.86, 45.88]; change -5.72 [-8.44, -3.01] |

- **Demand-charge break-even** (minimum over seeds of the proven lower bound): at least 24,900 USD per kW-month;
  29,200-36,200 on the other seeds; legacy 6,200. Both policies keep on-site charging at the assumed 10-40 USD per
  kW-month.
- **Faster-charger confound.** Energy is rounded to 50 Wh levels, which adds about 10-12 % modelled energy per
  delivery arc. Purchased energy rises x1.76 [1.48, 2.05] for the ILP and x2.10 [1.89, 2.31] for the rule. The
  rule's gain comes from repaired stock-outs. A clean charger-speed lever needs a formulation change (E2 (19)).
- **Legacy comparison** (seeds 0-2). The rule's sign reverses on the lock-outs and on on-site charging purely by
  repricing identical schedules (60 shared rows, 4.55e-13 USD). Its faster-charger gain survives both price sets
  (+14.6 served points under both) and is 264.83 USD larger at the new prices [187.79, 341.88].

### 4.6 PPO over three training seeds (`rl_seeds/RESULTS_final.md`; n 3 PPO seeds x 10 test seeds)

- **PPO minus best rule** (across seeds, n 3):

  | Cell | PPO minus best rule (USD) | Seed means (USD) |
  |---|---|---|
  | nyc4h-stress, r2 | +47.06 +- 22.60 | 37.57 / 55.71 / 47.91 |
  | nyc4h-stress, M2+M3 | +91.80 +- 15.06 | 91.79 / 85.75 / 97.87 |
  | stress4h, r2 | +138.37 +- 93.55 | 115.74 / 181.85 / 117.54 |
  | stress4h, M2+M3 | +190.68 +- 2.91 | 189.48 / 191.83 / 190.71 |

  PPO beats the best rule on 4 of 120 evaluations, by at most 16.4 USD.
- **stress4h, M2+M3 collapse.**
  - Served share 59.0 % in all three seeds (never-charge 58.5, best rule 75.8, ILP 94.4 %).
  - PPO minus never-charge: -4.43 +- 7.37, -2.09 +- 4.78 and -3.21 +- 7.25 USD (not significant).
  - Energy bought: 0.84 / 0.48 / 0.26 kWh (own rule 2.77).
  - Charge ASAP is cheaper on 30/30 evaluations, by 176.5-178.8 USD.
  - Training cost rises in all three runs: +27.0 / +37.7 / +60.0 USD.
- **nyc4h-stress.** PPO minus own rule: +8.38 +- 22.60 USD (r2) and +4.16 +- 15.06 USD (M2+M3). Seed means are -1.1
  to +17.0 and -1.9 to +10.2 USD (p >= 0.17). The cost is within 0.5 USD of the rule on 8/6/8 (r2) and 8/7/4 (M2+M3)
  of 10 test seeds. Single-test-seed deviations reach +150.6 USD.
- **stress4h, r2.** Seed 1 half-collapses: 1.07 kWh bought, 66.5 % served, near never-charge on 7 of 10 test
  seeds. Seeds 0 and 2 charge partially (1.46 / 1.74 kWh, 70.6 % served). PPO minus own rule: 40.24 / 106.34 /
  42.03 USD.
- **Gap of the ILP below PPO.** 28.72 +- 1.65 %, 31.42 +- 0.88 %, 44.30 +- 3.50 %, 46.28 +- 0.08 % (seed ranges
  28.01-29.32, 31.08-31.79, 43.47-45.93, 46.25-46.31). PPO served share: 83.8 / 80.9 / 69.2 / 59.0 %.
- **Legacy comparison.** On stress4h M2+M3 the sign flip from -149.69 +- 58.13 USD (legacy, one seed) to about +190
  is reproduced by all three seeds. The legacy under-charging on nyc4h-stress is gone in every seed.
- **Reproducibility.** The non-learned rows are bit-identical across the three runs (maximum difference 0.0 USD).

---

## 5. Updated rows of R6_DIGEST.md Section 7

### 5.1 Rows that change because of the retries

Rows are numbered as in `R6_DIGEST.md` Section 7. "Old" is the R6 digest value; "new" is the post-retry value (last
row per key, `retry_worse` rows ignored).

| # | Quantity | Old (R6) | New | 95 % CI | n | ILP status (new) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Gap, usd4h pooled | 25.10 % | **25.11 %** (upper limit 25.32) | [20.15, 30.07] | 30 | 28 OPT + 2 TL (x1.5 seeds 0, 8: 0.87 / 0.90 % at 600 s) | retries 3.1 |
| 4 | Gap, usd4h x1.5 | 38.42 % (<= 38.63) | **38.44 %** (<= 38.63; 38.62 with the best bound) | [35.37, 41.51] | 10 | 8 OPT + 2 TL (0.87, 0.90 %) | retries 3.1 |
| 8 | Gap, stress4h 6 bikes (n 5) | 40.1 % raw (40.00 ea), network | **40.03 %** ea, all R6 relaxed solves pooled (upper limit 40.26) | [34.62, 45.45] | 5 | 2 OPT + 3 TL (0.14-0.80 %, best-known incumbent against the largest bound) | stress 3.2, 8 |
| 9 | Gap, stress4h 6 bikes, seeds 0-9 | 39.70 % ea | **39.73 %** (upper limit 39.98) | [36.89, 42.57] (+- 2.84) | 10 | 5 OPT + 5 TL (<= 0.87 %) | retries 3.2 |
| 10 | Gap, stress4h-K8 | 46.14 % ea, lower bound (<= 48.31) | **47.59 %**, lower bound (<= 48.26) | [42.16, 53.03] | 5 | 1 OPT + 4 TL (0.75-2.87 %) at 1800 s | retries 3.5, levers_ext |
| 19 | Saving, usd4h pooled | 363.17 USD | **363.32 USD** | [235.07, 491.57] | 30 | as row 1 | retries 3.1 |
| 20 | Saving shares usd4h: lateness / response / unserved | 19.0 / 16.4 / 64.4 % | **19.1 / 16.8 / 63.9 %** (travel 0.14, electricity 0.17, end adjustment -0.13) | - | 30 | as row 1 | retries 3.1 |
| 24 | Service share of the pooled saving | 99.8 % [rec] | 99.8 % (99.82), re-derived | - | 30 | as row 1 | retries 3.1 |
| 25 | Late orders per window, best rule -> ILP | usd4h 13.8 -> 4.1; nyc4h 14.9 -> 4.4 | usd4h **13.8 -> 3.9**; nyc4h 14.9 -> 4.4 (unchanged) | usd4h ILP +- 1.36 | 30 / 10 | as rows 1, 5 | retries 3.1 |
| 26 | Served-share rise, ILP - best rule | +0.081 +- 0.027 / +0.072 | +0.081 +- 0.026 / +0.072 (unchanged) | - | 30 / 10 | as rows 1, 5 | retries 3.1 |
| 27 | Detour per swap saved, km | 0.36 / 0.40 | **0.38** (0.379 +- 0.125) / 0.40 | - | 30 / 10 | as rows 1, 5 | retries 3.1 |
| 29 | ILP end adjustment larger by, USD | 0.46 / 0.58 | 0.46 (0.464 +- 0.070) / 0.58 (unchanged) | - | 30 / 10 | - | retries 3.1 |
| 30 | Headline ILPs solved to optimality | 47/50 | **48/50** (2 TL at x1.5, <= 0.90 %) | - | 50 | - | retries 3.1 |
| 31 | Gap against the proven bound, largest excess | headline <= 0.21; psweep P 60 +0.33; levers +2.17 | headline **0.19**; psweep stress4h P 60 **0.25**, P 80 **0.93**; levers **0.67** (48.26 vs 47.59) | - | - | - | retries 7 |
| 60 | Gap rise with fleet, 6 -> 8 -> 10 bikes | 40.1 -> 46.14 -> rerun needed | **40.03 -> 47.59 -> 50.21 %** (8 and 10 bikes lower bounds; upper limits 48.26, 53.77); Welch 6 -> 8 p 0.026, 6 -> 10 p 0.003, 8 -> 10 p 0.29 | [34.62, 45.45] / [42.16, 53.03] / [46.99, 53.43] | 5 each | rows 8, 10, 11 | stress 3.2 |
| 62 | Fixed demand, gap at 4 bikes | 37.9 % (B 1), 32.3-32.5 % (B 2-4) | 37.9 % (B 1), 32.4-32.5 % (B 2-4); the retries report lists this row as unchanged | B 1 [23.5, 52.3] | 3 | K 4: 4 OPT + 8 TL (0.33-1.56 %) | retries 3.4 |
| 65 | Served share ILP vs best rule, 6 / 8 bikes | 0.954 vs 0.754; 0.919 vs 0.653 | 0.954 vs 0.754; **0.925** vs 0.653 | K 8 ILP [0.877, 0.973] | 5 / 5 | rows 8, 10 | retries 3.5 |
| 70 | Saving per extra bike, 4 -> 6 / 6 -> 8 / 8 -> 10 (USD) | 214.4 / 89.4 / 17.1 | **214.1** / 89.4 / 17.1 | [193.7, 234.4] / [0.3, 178.5] / [-13.2, 47.5] | 3 | 4 -> 6: 4/6 TL (0.33-1.04 %); 6 -> 8: 2/6 TL (0.35, 0.63 %); 8 -> 10: 6/6 OPT | retries 3.4 |
| 73 | No on-site charging, ILP change | +228.53 USD, >= 169.6 per seed | **+262.96 USD**, >= 207.7 on every seed | [216.81, 309.11] | 5 | 4 OPT + 1 TL (0.32 %); reference 1 OPT + 4 TL at 1800 s | retries 3.5, levers_ext |
| 74 | Demand-charge break-even | >= about 20,400 USD per kW-month | **>= about 24,900** (per seed 36,200 / 24,900 / 33,700 / 33,600 / 29,200) | - | 5 (minimum over seeds) | as row 73 | retries 3.5 |
| 75 | Other levers, ILP | lock-out of 2 spares -7.80 [-59.88, 44.28], true value in [0, 6.6]-[0, 71.4]; others rerun needed | lock-out of 2 spares **+9.78**, 5/5 > 0, brackets [0, 25.3], [0, 41.3], [0, 40.7], [0, 16.9], exactly +2.52 on seed 4. Faster chargers -1.58 [-14.80, 11.63]. Second swap position: saving at most 4.1-35.3 per seed, increase at most 0.12. Lock-out of 1 spare: +11.79 [-5.34, 28.92], in [0, 2.5]-[0, 40.7] per seed | 2 spares [-4.88, 24.43] | 5 | 2 spares 1 OPT + 4 TL (1800 s); faster chargers 3 + 2; second position 0 + 5; 1 spare 0 + 5 (600 s) | retries 3.5, levers_ext |

Rows 2, 3, 5-7, 18, 21-23 and 32-59 are unchanged by the retries (all-optimal or untouched stages). So are rows 63,
67-69, 71 and 72 (the 0.6 kWh part) and rows 76-87; for rows 76-87, Section 5.2 adds the rl_seeds view. For rows
32-44 (rolling), the retries report finds the effect of the resynced psweep row below 0.001 of the share kept
(stress4h 0.526 +- 0.183 -> 0.526 +- 0.182); `--analyse` should be re-run before part 2 is written.

### 5.2 Rows filled or changed by the fill stages

| # | Quantity | Old (R6) | New | 95 % CI | n | ILP status | Source |
|---|---|---|---|---|---|---|---|
| 11 | Gap, stress4h-K10 | rerun needed (legacy 46.99 %) | **50.21 %**, lower bound; <= 53.77 against the bounds | [46.99, 53.43] (bound [50.73, 56.81]) | 5 | 0 OPT + 5 TL (3.65-13.31 %) at 600 s | stress 3.1 |
| 12 | Gap, stress8h | rerun needed (legacy 47.96 %; stress report 47.91) | **42.77 %**, lower bound; <= 46.96; per seed 29.2 / 48.8 / 50.3 | [13.51, 72.03] | 3 | 0 OPT + 3 TL (4.86-8.98 %) at 600 s | stress 3.1 |
| 13 | Gap, transfer experiment | rerun needed (legacy 20.98 %) | **24.15 %** ea (raw 24.21) | seed means [13.44, 34.86]; 15 cells [19.71, 28.59] | 5 (15 cells) | relaxed no-transfer solves 14 OPT + 1 TL (0.29 %, certified by nesting) | transfers 3.1 |
| 61 | Written-target 6-bike gap; stress8h gap | rerun needed (legacy 39.83 %; 47.96 %) | written **38.78 %** (relaxed on the same seeds 39.71; -0.93 [-3.01, 1.15] points); stress8h as row 12 | written [32.58, 44.98] | 4; 3 | written 1 OPT + 3 TL with incumbent (1.15-4.90 %), seed 2 without incumbent | stress 3.3 |
| 64 | LP value of a spare / charger, 6 / 8 / 10 bikes | rerun needed (legacy 0.45 / 2.79 / 21.87; 0.07 / 1.29 / 16.67) | spare **0.70 / 9.81 / 77.95**; charger **0.03 / 8.78 / 65.86** USD per site and window | spare [0.17, 1.24] / [4.64, 14.98] / [38.30, 117.60]; charger [-0.02, 0.08] / [2.60, 14.96] / [29.70, 102.03] | 5 | 23 LPs LP_OPTIMAL | stress 3.5 |
| 66 | Price of recovery, 6 bikes; boundary grid | rerun needed (legacy 3.20 USD; <= 4.38) | per seed: **0.77** exact (seed 0); 5.59 in [0, 13.85]; unknown (seed 2); 50.70 in [1.34, 52.01]; <= 9.97 (strictly 10.00, seed 4). Grid: rho <= 0.5 0.48-0.77 (seed 0, exact), <= 9.25-18.83 (seed 1); full return >= 9.23 (seed 1), >= 55.39 (seed 2) | not meaningful (do not quote the mean) | 5 (seeds 0-2 for the grid) | written 1 OPT + 4 TL (one without incumbent); grid 6 OPT + 20 TL (9 without incumbent) | stress 3.3-3.4, 8 |
| 69 | ILP design vs rule design | 9.4 % at equal service (150.1 USD) | unchanged at 0.6 kWh; against the rule at the other packs 12.2 / 9.8 / 9.7 % (200.9 / 159.1 / 155.4 USD) at 0.5 / 0.75 / 1.0 kWh | 0.5 [153.2, 248.5]; 0.75 [96.2, 222.0]; 1.0 [141.5, 169.3] USD | 3 | ILP at 0.6 kWh only | pack 3.5 |
| 72 | Negative net value of a rule spare | 0.6 kWh single seeds; pack sizes: rerun needed (legacy -9.33 at 0.5 kWh) | at 4 bikes / 2 spares: **-1.7** (0.5 kWh; per seed +5.4, -5.6, -4.8), +0.7 (0.6), -2.4 (0.75), -1.8 (1.0); no significant negative value; single-seed non-monotonicity remains (K 10, 0.6 kWh, seed 1 -0.95 per spare; 1.0 kWh seed 2 -1.37; K 4 third spare seed 2 19.1 USD) | 0.5 [-16.9, 13.5]; 0.6 [-42.0, 43.4]; 0.75 [-16.5, 11.7]; 1.0 [-7.2, 3.5] | 3 | POLICY | pack 3.4 |
| 77 | Compliance, decentralisation, Manhattan siting and transfers | rerun needed (transfers 2.6-2.7 %) | transfer part: **63.87 / 64.64 USD**, **9.08 / 8.82 %** of the ILP cost on cyclic tours under enforced recovery (bounds 61.73-65.83 / 63.30-65.28); compliance, decentralisation and siting: part 2 | 1 hub [20.79, 106.94]; 2 hubs [21.18, 108.11] | 5 | see transfers Table 3.2 | transfers 3.2 |
| 78 | ILP cheaper than PPO, range of gaps | 28.01-31.39 / 43.47-46.25 % (one seed) | across three seeds 28.72 +- 1.65 / 31.42 +- 0.88 (nyc4h-stress r2 / M2+M3), 44.30 +- 3.50 / 46.28 +- 0.08 % (stress4h); twelve seed means 28.0-46.3 %, so the range of 28-46 % stands | as given (n 3, t 4.303) | 3 x 10 | reference ILP: nyc 10 OPT; stress 5 OPT + 5 TL | rl_seeds 3 |
| 79 | PPO - own rule, nyc4h-stress (cost) | -1.11 / +4.14 USD | across seeds **+8.38 +- 22.60** (r2) / **+4.16 +- 15.06** (M2+M3); seed means -1.1 to +17.0 / -1.9 to +10.2 | as given | 3 x 10 | 10 OPT | rl_seeds 3 |
| 82 | PPO M2+M3 - best rule, stress4h | +189.48 [113.63, 265.33] | across seeds **+190.68 +- 2.91** (189.48 / 191.83 / 190.71); seed-averaged policy +190.68 +- 74.31 | as given | 3 x 10 | 5 OPT + 5 TL | rl_seeds 3 |
| 83 | PPO M2+M3 - never-charge, stress4h | -4.43 USD | -4.43 +- 7.37 / -2.09 +- 4.78 / -3.21 +- 7.25 (across -3.24 +- 2.91), none significant | as given | 3 x 10 | - | rl_seeds 3 |
| 84 | Served share PPO M2+M3 / best rule / ILP, stress4h | 59.0 / 75.8 / 94.4 % | 59.0 % in every seed / 75.8 / 94.4 % | - | 3 x 10 | as row 78 | rl_seeds 3 |
| 86 | Training improved the stochastic policy | 2 of 4 runs | nyc4h-stress improves in every seed (r2 -189.5 / -191.3 / -153.7; M2+M3 -270.1 / -242.8 / -190.3 USD); stress4h r2 flat (-7.9, +14.6, -16.7); stress4h M2+M3 worse in every seed (+27.0, +37.7, +60.0) | block-clustered | 12 runs | - | rl_seeds 3 |

Rows still "rerun needed" after part 1:
- 14 (Manhattan, part 2);
- 17 (ratio to the preliminary specification);
- 44 (lambda 0 / 20 and the forecast plan, part 2, rolling_ext);
- the compliance, decentralisation and siting parts of 77 (part 2).

**Highlights and abstract wording (derived from the rows above).** Bullet 4 ("40-47 %") can read "40-50 % with 6 to
10 bikes, the 8- and 10-bike values lower bounds". The R6 digest had proposed "40-46 % on 6 and 8 bikes; K 10 not
re-run". The abstract's "40-47" and the conclusion's "47.0 %" (K10) become 40-50 % and 50.2 % (at most 53.8 %).

---

## 6. PENDING_R6.md items

### 6.1 Resolved by part 1

**Item 1, the transfer and hub-separation experiment.** Resolved in full; status `labelled` -> replaced. The
replacement statements are in transfers `RESULTS_final.md` Section 7, which includes the full Section 6.7 text and
the cell values of Table tab:res:transfers (a)-(c). The key statements:
- Table tab:res:headline, transfer row: "usd4h x1, seeds 0-4, three layouts, seed means | 5 | 24.15 (13.44-34.86) |
  14 optimal, 1 time limit (0.29 %, certified optimal by nesting)" (end-adjusted; raw 24.21). Footnote a no longer
  applies.
- Section 6.2, the 21.0 % sentence: "the transfer experiment (three layouts, seeds 0-4) gives 24.2 % (13.4-34.9 with
  the five seed means as units)".
- Section 6.6, first sentence: "in all 45 relaxed-target ILP solves of the transfer experiment (43 optimal, 2 at the
  time limit) the ILP moved no battery, and it bought energy on one instance only (0.14 kWh, 0.04 USD), as the initial
  stock of three spares per swap site covered every swap of the window".
- Section 7.1: "Hubs and transfers are a fallback (Table tab:res:transfers): under relaxed targets transfers had no
  value, and under enforced end-of-window recovery they saved about 64 USD per window, 9 % of cost, between swap sites
  and separate charging hubs, almost entirely as unserved orders avoided; yet separation still did not pay and no
  rule-based transfer policy was strictly cheaper than r2 in any of 60 cells. Transfers were not tested where
  batteries bind."
- Section 8, first clause: "none of the 45 relaxed ILP solves of the transfer experiment moved a battery (the three
  solves of one instance bought 0.14 kWh)". Second clause: "transfers saved about 9 % of cost (64 USD per window)
  only between swap sites and separate charging hubs and only under enforced recovery (n 5)".
- Section 1 findings paragraph: "battery transfers pay only between swap sites and separate charging hubs and only
  under enforced end-of-window recovery, where they recover one to two orders per window (RQ3)".
- Abstract: drop the legacy-price qualifier. If a number is quoted, use "about 9 % of cost under enforced recovery".
- Section S9: the same values. The timetable sentence becomes "14.62 USD (13.92-15.33) with one hub and 15.87 USD
  (15.60-16.13) with two, of which 2.49 and 3.67 USD are provable; the transfer charges differ by 15.0 and 15.8 USD
  for the same batteries moved".
- Figures: `fig_r6_transfers_cost_by_layout` replaces fig:res:transfers and `fig_r6_transfer_rule_loss` replaces
  fig:app:transfer-rules. `fig_r6_transfers_legacy_vs_new` is available for the sensitivity paragraph.

**Item 9, the station levers.** Resolved in full by levers_ext and the levers retry. This includes the clause "the
unresolved lock-out of two spares also needs a warm-started reference solve": the reference was warm-started from the
lock-out incumbent with transfers stripped and solved at 1800 s.
- Table tab:res:levers, calibrated block (n 5):
  - Reference: gap 47.6 (42.2-53.0)^a, served 0.92 / 0.65, 1/4 (1800 s).
  - Faster chargers (50 Wh levels): ILP -1.6 (-14.8 to 11.6)^b, rule -309.2 (-548.1 to -70.4), gap 39.8
    (38.1-41.6), served 0.93 / 0.78, 3/2.
  - Second swap position: ILP saving at most 4.1 to 35.3 per seed and increase at most 0.12^b, rule +2.4 (-3.9 to
    8.7), gap 46.2 (42.0-50.5), served 0.92 / 0.65, 0/5.
  - Lock-out of 1 spare: ILP 0 to 2.5-40.7 per seed (measured +11.8)^b, rule +40.8 (-61.5 to 143.1), gap 47.9
    (43.1-52.8), served 0.92 / 0.63, 0/5.
  - Lock-out of 2 spares: ILP 0 to 16.9-41.3 per seed, exactly +2.5 on seed 4 (measured +9.8)^b, rule +60.1 (-95.8
    to 216.0), gap 48.4 (43.3-53.4), served 0.92 / 0.63, 1/4 (1800 s).
  - No on-site charging: ILP +263.0 (216.8-309.1; at least 207.7 on every seed), rule +213.5 (124.0-303.1), gap
    41.9 (37.9-45.9), served 0.82 / 0.52, 4/1.
  - Footnote a: lower bound; at most 48.3 % against the proven bounds; mean MIP gap of the reference solves 15 USD.
  - Footnote b: proven bracket on raw totals.
- Section 6.6, the levers paragraph: the full text is in levers_ext Section 6. It opens: "On stress4h-K8 (seeds 0-4,
  relaxed targets; reference and 2-spare lock-out solved 1800 s, the other levers 600 s), removing on-site charging
  costs the ILP 263.0 USD per window (216.8-309.1; at least 207.7 USD on every seed by the proven bounds; four of
  five solves optimal), about 21 % of its cost, and the best rule 213.5 USD (124.0-303.1, dearer on 5 of 5 seeds);
  giving up on-site charging would pay only at a demand charge of at least about 24,900 USD per kW-month."
- Section S8.4, lever definition: "Faster charging was represented by a level size of eps = 50 Wh (L = 12) on the
  same 0.6 kWh pack, so that a charger still advances one level per slot but draws 0.667 kW and a full charge takes
  one hour instead of two. ... The lever therefore combines faster charging with a coarser, conservative energy
  rounding." This is the post-correction wording (C3); "half-range packs" must not be used.
- Section 7.1: "Among the station levers, on-site charging is the one the coordinator needs: removing it cost the ILP
  263.0 USD per window (216.8-309.1, n = 5; at least 207.7 USD on every seed) and the best rule 213.5 USD; a second
  swap position and the lock-out of one or two spares are worth at most 4-41 USD per window to the coordinated
  schedule (proven bounds; a second position can raise its cost by at most its 0.12 USD set-up), and chargers twice
  as fast (with energy rounded to 50 Wh levels) change its cost by less than 40 USD while they lower the rule's by
  309 USD."
- Figures: `fig_r6_levers_ext_effects` replaces fig:app:levers, and `fig_r6_levers_ext_service_demand` (a) replaces
  panel (a) of fig:app:levers-mechanism. The legacy block and the legacy statement (rule 238.9 USD cheaper without
  on-site charging; repriced -238.93 [-380.94, -96.91]) remain as the sensitivity case.

**Item 6, LP operating values and stock-out counts.** Resolved for the text. Panel (b) of fig:res:shadow still has
to be redrawn from the records.
- Section 6.6, "Battery-side scarcity", and Section S8.1: "At the calibrated prices one more spare at a site is worth
  0.70 USD per site and window with 6 bikes (0.17-1.24; n = 5; median 0.73; above its set-up cost of 0.332 USD on
  four of five seeds), 9.81 USD with 8 bikes (4.64-14.98) and 77.95 USD with 10 (38.30-117.60), about 2, 30 and 235
  times its set-up cost; one more charger is worth 0.03 USD (-0.02 to 0.08; below its set-up cost of 0.082 USD),
  8.78 USD (2.60-14.96) and 65.86 USD (29.70-102.03)." The rest of the paragraph is in stress Section 6: written
  targets 2.28 / 0.75 USD; 8 h 1.25 / 0.41 USD; paired rises; stock-outs 91.0 vs 70.8 and 97.6 vs 105.8.
- Section 7.1: "LP value of one more spare per site 0.70 to 77.95 USD per window from 6 to 10 bikes against an
  allocated cost of 0.33 USD (calibrated prices)". The hedge "measured only at the legacy prices" is removed.
- Figure: `fig_r6_stress_lp_values` replaces panel (a) of fig:res:shadow.

**Item 16, cells cut short by sleep or the time limit.** Resolved except one cell. Replacement statements, per cell
(retries Section 7):
- usd4h x1.5 seeds 0, 5, 8: re-solved at 600 s; seed 5 optimal, seeds 0 and 8 at 0.87 / 0.90 %. Gap 38.44 +- 3.07 %
  (upper limit 38.63). Pooled 25.11 % [20.15, 30.07], 28 of 30 optimal. "MIP gaps at most 1.07 %" becomes "at most
  0.90 % at 600 s".
- Levers reference: "re-solved at 1800 s from the lock-out incumbent: 1 of 5 optimal, MIP gaps 0.75-2.87 %, no
  incumbent provably sub-optimal; 2-spare lock-out 1 of 5 optimal, 1.05-3.26 %; no on-site charging seed 2 at
  0.32 %". The dependent values are 1278.7 USD, gap 47.6 % (48.3 % upper), +263.0 USD and >= 24,900 USD per
  kW-month.
- Fleet 10 bikes / 1 spare seed 2: optimal (837.06 USD); the "991 s run used" note is void.
- Lateness sweep v 36 seeds 5 and 6: solved to optimality and equal to the best-known schedules. 31.65 +- 6.56 % is a
  solved value; drop "two seeds use the best known schedule".
- Penalty sweep:
  - usd4h P 80 seed 0: optimal (532.60 USD); gap 30.66 +- 6.73 % recorded;
  - stress4h P 40 seed 9: optimal;
  - stress4h P 30 seed 5: 0.12 USD above a repriced schedule (immaterial);
  - stress4h P 80 seeds 2, 3, 6, 7: 1.66 / 2.33 / 3.38 / 3.22 %. Seeds 3, 6, 7 are still best reported via the
    repriced P 60 schedule: recorded 44.50 +- 3.03 %, best-known 44.69 +- 3.15 %, upper limit 45.43.
- stress4h six-bike psweep cells: 5 of 10 optimal (<= 0.87 %), gap 39.73 +- 2.84 %. Over the five 6-bike seeds
  (pooled): 2 OPT + 3 TL (<= 0.80 %), gap 40.03 %.
- **Still open:** fleet 10 bikes / 2 spares seed 2 was not re-solved. Its 100.5 % gap stands, and so does the
  nesting exclusion.

### 6.2 Partly resolved by part 1

- **Item 5, K10 and stress8h.** Replaced:
  - Table tab:res:headline rows: "stress4h-K10, 10 bikes, 80 orders & 5 & 50.21 (46.99-53.43) & 0 optimal, 5 time
    limit (3.65-13.31 %, 600 s)" and "stress8h, 6 bikes, 96 orders & 3 & 42.77 (13.51-72.03) & 3 time limit
    (4.86-8.98 %, 600 s)". The bound list gains 53.77 (stress4h-K10) and 46.96 (stress8h).
  - The 6.6 / S8.1 fleet-axis paragraph (full text in stress Section 6): "At the calibrated prices the gap is 50.2 %
    (47.0-53.4; n = 5) with ten bikes, a lower bound because all five 600 s solves are time-limited with MIP gaps of
    3.7-13.3 % (at most 53.8 %, 50.7-56.8, against the proven bounds), and 42.8 % (13.5-72.0; n = 3; ...) in the
    eight-hour window, too wide to separate the window lengths. The gap rises from 40.0 % with 6 bikes to 47.6 %
    with 8 ... and 50.2 % with 10; the rises from 6 to 8 bikes (+7.6 points, Welch p = 0.026) and from 6 to 10
    (+10.2 points, p = 0.003) are significant, the step from 8 to 10 (+2.6 points, p = 0.29) is not ..."
  - Figure fig:app:gap-vs-fleet panel (a) is replaced by `fig_r6_stress_gap_vs_fleet`.
  - Section 7.3: "the largest ILPs, 10 bikes and 80 orders or 6 bikes and 96 orders, stop at 600 s with MIP gaps of
    4-13 % at the calibrated prices, so their gaps are lower bounds with bound-based upper ends 3.6 and 4.2 points
    higher".
  - **Open:** the tab:app:recovery rows for 8 and 10 bikes (legacy 11.63 / 29.41 USD on seed 0). No written solves
    were run at 8 or 10 bikes.
- **Item 7, boundary grid and price of recovery.** Replaced:
  - the transfer rows of tab:app:recovery: co-located 0.27; one hub 71.88 / 8.01; two hubs 71.74 / 7.09 USD, with
    the statuses and bounds of transfers Section 7;
  - the stress4h six-bike content: "At the calibrated prices the price of recovering the written targets on stress4h
    with 6 bikes is 0.77 USD per window on seed 0 (both solves optimal; 0.10 % of the relaxed optimum) and at most
    9.97 USD on seed 4 (...); on seeds 1 and 3 both solves are time-limited and the price lies in [0, 13.9] and
    [1.3, 52.0] USD, and on seed 2 the written solve found no incumbent within 300 s." The strict upper end on seed
    4 is 10.00 USD (stress Section 8); "at most 10.0 USD" is the strict form.
  - Table tab:app:boundary takes the rows of stress Section 3.4.
  - The 6.6 boundary sentence ends "robust to the end-of-window boundary for partial recovery (rho <= 0.5) and not
    for full battery return, at 6 bikes and within the solved part of the grid", with full return at least 9.2 /
    55.4 USD on seeds 1 / 2.
  - In 7.2 / 7.3, the 3.20 USD becomes "below 1 USD on the seed solved to optimality and at most 10 USD on a second
    seed; unresolved on three seeds at 300 s".
  - **Open:** nyc4h, usd4h x0.75 and x1.5, the 8- and 10-bike rows (11.63 / 29.41 USD) and the Manhattan row
    (part 2).
- **Item 8, the pack-size axis.** Replaced on the rule side:
  - the last sentence of the 6.6 fleet paragraph;
  - the four tab:res:sizing rule rows: n 3; 0.50 | 10, 4 | 1684.9 (1530.4-1839.4) | 0.993; 0.60 | 8, 4 | 1619.6
    (1256.2-1983.0) | 0.979; 0.75 | 8, 4 | 1611.8 (1264.7-1959.0) | 0.986; 1.00 | 8, 4 | 1606.8 (1318.0-1895.6) |
    0.986;
  - the S8.3 paragraph "Pack size", including -1.7 [-16.9, 13.5] in place of -9.33 USD;
  - "pack sizes" is removed from the Section 7 list of legacy-only experiments.

  Full texts are in pack Section 7. **Open:** panels (a) and (c) of fig:res:isocost and the hatched ILP bars of
  fig:app:fleet-marginal stay as a labelled legacy comparison; no ILP was run at the other packs.
- **Item 15, coverage and seed tables.** Rows updated:
  - transfers: 390 records; 74 OPT + 16 TL with the breakdown; Prices "calibrated";
  - stress: "calibrated; 300 s (6 bikes), 600 s (10 bikes, 8 h), 1800 s (8-bike reference)", with the status
    counts of Section 2;
  - pack: "rules 0-2 (3), no solve, calibrated";
  - levers: the three levers at the calibrated prices (75 records, 3 OPT + 12 TL); the legacy K8 rows remain as the
    sensitivity run;
  - rl_seeds: 488 records, 8 trainings, reference ILP reused.

  **Open:** the rows of items 2-4, 10 and 11.
- **Item 20, values re-derived for the digest.** Done for the headline-dependent entries: 99.8 % (99.82); late
  orders 13.8 -> 3.9 (usd4h, was 4.1) and 14.9 -> 4.4 (nyc4h); served-share advantage +0.081 / +0.072; detours 0.38
  (was 0.36) / 0.40 km; end-adjustment differences 0.46 / 0.58 USD; saving shares 19.1 / 16.8 / 63.9 %. The values
  that changed must be corrected in 6.2, 7.1, S6.1 and S6.2. **Still "verify":** the no-wait shares 0.91 -> 0.73 and
  0.86 -> 0.48, and M4 minus best rule 45.7 / 21.1 USD. The rl rule rows are bit-identical across the three PPO
  runs, so the source stays valid.
- **Item 17, legacy learning comparator.** Status unchanged ("labelled, no re-run needed"). The calibrated-price
  single-seed statements are replaced (rl_seeds Section 7):
  - 6.10: "PPO is not cheaper than the best rule in any cell or for any of three training seeds: across seeds
    +47.1 +- 22.6 and +91.8 +- 15.1 USD on nyc4h-stress (r2, M2+M3) and +138.4 +- 93.5 and +190.7 +- 2.9 USD on
    stress4h ...";
  - "a learning failure of the comparator that three training seeds reproduce (default hyperparameters, 200,704
    steps each)";
  - S2 line 150, 4.7 line 104 and S4 line 241: "three PPO seeds (0, 1, 2; the environment is seeded with the PPO
    seed) and no hyperparameter tuning";
  - captions: "legacy prices, one PPO seed; calibrated prices, three PPO seeds (the figure shows seed 0; seed ranges
    in the text)";
  - R6_DIGEST caveat 10: "Three PPO seeds, default hyper-parameters, 200,704 steps each; the stress4h M2+M3 failure
    is reproduced by every seed and the stress4h r2 cell is seed-dependent (one of three seeds half-collapses);
    hyper-parameter tuning and longer training remain untested".

### 6.3 Still open after part 1

| Item | Status | Waiting for |
|---|---|---|
| 2 Manhattan siting | labelled | the second siting pass (part 2) |
| 3 Earlier Midtown study | labelled | optional re-run; none planned in the fill round |
| 4 Selfish equilibrium and compliance | labelled | the compliance stage (part 2) |
| 5 (rest) | labelled | written-target solves at 8 and 10 bikes (not planned) |
| 7 (rest) | labelled | price of recovery on nyc4h, usd4h x0.75 / x1.5, 8 / 10 bikes, Manhattan |
| 8 (rest) | labelled | isocost panels (a), (c) and the hatched ILP bars: keep as legacy or drop (author decision) |
| 10 Rolling lambda 0 / 20, forecast plan, written-target online runs | labelled | rolling_ext (part 2) |
| 11 Robustness decomposition (preliminary specification) | labelled | no fill stage; re-run or drop |
| 12 Operating-metric figure fig:app:metrics | labelled | regeneration from the calibrated headline records (no solve; not done) |
| 13, 14, 19 | labelled, no re-run needed | - |
| 15 (rest) | labelled | items 2-4, 10, 11 |
| 16 (rest) | labelled | fleet K 10 / B 2 seed 2 (100.5 %): warm start from the K 8 / B 2 schedule or `--time-limit 1800` |
| 18 Wage-per-order variant | labelled | optional re-run |
| 20 (rest) | verify | no-wait shares and M4 minus best rule |

---

## 7. Caveats

1. **Many cells remain time-limited.** The stated values are incumbents with bounds, not optima:
   - 42 of the 55 retried rows: headline 2 at <= 0.90 %, psweep 19 at <= 3.38 %, fleet 12 at <= 1.04 % (the kept
     300 s rows up to 1.56 %), levers 9 at <= 3.26 %;
   - four fleet rows were never retried: K 8 / B 1 seeds 1-2, K 8 / B 2 seed 2 (0.31-1.34 %) and K 10 / B 2 seed 2
     (100.5 %);
   - 16 transfer rows (15 open);
   - all eight K10 and stress8h solves (up to 13.31 %);
   - 12 of 15 new levers_ext ILPs;
   - 5 of 10 stress4h rl references.

   Quote the bound-based limits next to the gaps.
2. **The 8- and 10-bike gaps are lower bounds.** The K8 value is better converged (1800 s) than the K10 value
   (600 s, MIP gaps 3.65-13.31 %), so part of the 8 -> 10 step is solver gap. The 8 -> 10 test is not significant.
   Fleet and demand are confounded (8 orders per bike).
3. **The stress end-target results have holes.** 10 of 27 written and grid solves have no incumbent. The written
   price of recovery is resolved on two seeds only, and seed 3's 50.7 USD is 97 % solver gap. The stress report
   recommends re-solving these cells at 1800 s from a repaired start.
4. **Unequal time limits in levers_ext.** The new lever cells ran at 600 s against the 1800 s reference. Report the
   brackets, not the measured deltas, for the ILP; the +33.5 USD for the second swap position is an artefact. A 1800
   s retry of the 12 rows (about 6 h at Threads 3) would narrow the brackets.
5. **The faster-charger lever is confounded with the energy rounding.** It is "chargers twice as fast, with energy
   rounded to 50 Wh levels". The rule's 309 USD gain is real for the instance as built but is not a clean
   charger-speed effect.
6. **The transfer findings are limited in scope.**
   - The value of transfers counts whole 60-USD orders: 26-108 USD across seeds, CI half-width 43 USD. "About one
     order per window" is safer than a USD figure.
   - The written-target gaps compare an ILP that meets the targets with rules that mostly do not (148 of 150).
   - The cyclic-tour advantage of the ILP is a fare convention.
   - Transfers were not tested on a stressed family.
7. **The pack-size results come from the rule only.** No ILP was solved at 0.5 / 0.75 / 1.0 kWh, so the comparison
   is rule-at-pack-p against ILP-at-0.6-kWh. The sign of the 0.75 / 1.0 kWh effect at the optimum is not
   established at n 3. Rule schedules violate the report-only constraint (9) on 25 of 192 best-rule instances, which
   favours the rule.
8. **Across-seed CIs with n 3 measure seed agreement.** For example, stress4h M2+M3 has +- 2.91 across seeds but
   +- 74.31 over test seeds. Do not quote the pooled 30-row CIs of the auto `RESULTS.md`. The stress4h r2 cell
   should be reported as seed ranges.
9. **Weaker retry bounds.** In 15 retried rows the retry's bound is weaker than the first solve's. Stage analyses
   that read the last row's bound give slightly conservative upper limits and MIP gaps (for example, fleet K 4 / B 1
   seed 0: 1.04 % shown, 0.88 % proven).
10. **Downstream products need refreshing.** The rolling-horizon analysis was produced before the retried server
    rows were synced; re-run `--analyse` before part 2. Its effect on the share kept is below 0.001. The R6 levers
    report (2026-10-18), R6_DIGEST rows 10, 31 and 73-75 and the manuscript's K8 statements (6.6, 7.1, S8.4, S12,
    the footnote of tab:res:levers) still carry the pre-retry values.
11. **Shared instances.** The usd4h x1 seeds 0-4 of the transfer experiment are the headline instances, and the
    stress4h 6-bike seeds recur across psweep, network, fleet, rl and the stress stage. These are not independent
    replications.
12. **Mixed clocks; this digest is not refuter-checked.** Server and laptop rows mix two clocks (records about 4 h
    ahead of local EDT). This digest's own derived wordings (the highlights sentence, the row-60 assembly from three
    sources) have not been through a refuter pass; every number in them comes from the reports.

---

## 8. Sources

- `outputs/r6_fill/RETRIES_final.md` (script `figs_retries/retries_analysis.py`)
- `outputs/r6_fill/transfers/RESULTS_final.md` (`figs/make_r6_transfers_final.py`, `figs/write_results_final.py`)
- `outputs/r6_fill/stress/RESULTS_final.md` (`figs/make_stress_figs.py`)
- `outputs/r6_fill/pack/RESULTS_final.md` (`figs/pack_analysis.py`, `figs/make_pack_figs.py`)
- `outputs/r6_fill/levers_ext/RESULTS_final.md` (`figs/make_levers_ext_figs.py`, `figs/check_eps50_energy.py`)
- `outputs/r6_fill/rl_seeds/RESULTS_final.md` (`figs/make_rl_seeds_report.py`)
- `outputs/R6_DIGEST.md` (Section 7 row numbers), `manuscript/PENDING_R6.md` (item numbers)


---
---

# Part 3: compliance at the new prices

**Scope.** This part covers only the compliance stage of the fill round: the selfish equilibrium, rule r2 and the
compliance sweep on Manhattan at the calibrated prices (P 60 USD, w 18 USD/h, v 15 USD/h). The part-1 header says that
compliance "follows in part 2"; for this stage, this part takes that place. Nothing in parts 1 or 2 is changed.

Date: 2026-10-20. **Input:** `outputs/r6_fill/compliance/RESULTS_final.md`. That report recomputes every number from
`records.jsonl` (113 rows) and `cache/index.jsonl` (21 rows) with `figs/compliance_final.py`; no solver was called.
The run itself was on the AWS server (255.3 s wall time, finished 14:52:40 server clock). For this digest I re-derived
the following from `records.jsonl` and they agree with the report to the printed digit: V and served share at every
psi with both CIs, gap closed, the chord deviation at psi 0.5, both crossings and the price of decentralisation, on
both layouts. **Legacy counterpart:** `outputs/r5_x6_manhattan/RESULTS_final.md` (sites 06 + 12, P 30 / v 36),
recomputed by the same script; it reproduces the legacy report exactly.

**Design.**
- Instance: family `manhattan`, 8 bikes, 40 orders, 16:00-20:00, three demand scenarios (seeds 0-2, p 1/3), written
  end-of-window targets, ILP plans with a 300 s limit.
- A share psi in {0, 0.25, 0.5, 0.75, 1} of the 8 riders (0, 2, 4, 6, 8 riders) follows the ILP plan of its scenario.
  The stations replay the plan's charging and loads. The other riders run the logit rule M4 once, with myopic waits
  and no equilibrium iteration.
- Three draws of the compliant set per psi. A draw picks the same riders in every scenario and on both layouts, and
  its sets are nested in psi, so layout differences are paired run by run.
- **Sites 04 + 09** (`M04:SC:B2:C2|M09:SC:B4:C2`, set-up 104,300 USD): the best written-target two-site layout of
  the siting pass `outputs/r6_o2/manhattan_pass2`. ILP V 699.96, optimal in all three scenarios. Its certified lower
  bound is 676.24 (gap 3.39 %), so the layout is **not** a certified optimum.
- **Sites 06 + 12** (`M06:SC:B4:C2|M12:S:B3:C0`, 103,950 USD): the round-5 bi-level layout. It is the layout of the
  current manuscript and of the legacy sweep. ILP V 802.43, time-limited in all three scenarios.

**Confidence intervals.** Exact Student-t 95 %, t_{0.975,2} = 4.303, in two versions:
- **over scenarios** (n 3; each scenario value is the mean of its 3 draws). This is the manuscript convention and is
  used for the headline numbers and the figures.
- **over draws** (n 3; each draw value is the mean over the 3 scenarios of the same compliant set). It conditions on
  the three demand scenarios and measures only which riders comply. It is zero at psi 0 and 1.

Differences against the followers and between layouts are paired per scenario.

## P3.1 Short answers

1. **V falls at every step of psi on both layouts, and the served share rises.**
   - Sites 04 + 09: 1491.1 -> 1307.2 -> 1100.1 -> 902.2 -> 700.0 USD; served share 0.667 -> 0.983. At psi 0.5 the
     95 % CI is [877.4, 1322.9] over scenarios and [969.4, 1230.9] over draws.
   - Sites 06 + 12: 1474.9 -> 1251.3 -> 1050.4 -> 937.1 -> 802.4 USD; served share 0.650 -> 0.958.
   - psi 1 reproduces the ILP value in all 18 runs (difference below 1e-6 USD).
2. **The shape changed with the prices.** The benefit is no longer back-loaded.
   - 04 + 09: **linear**. psi 0.25 / 0.5 / 0.75 close 23.2 / 49.4 / 74.4 % of the 791.2 USD gap between no and full
     compliance. The chord deviation at psi 0.5 is +4.6 USD [-359.6, 368.8].
   - 06 + 12: **convex, front-loaded**. 33.3 / 63.1 / 80.0 % of 672.5 USD. Chord deviations are -55.5 [-102.5, -8.5]
     at psi 0.25 and -88.3 [-155.5, -21.1] at psi 0.5, and all three scenarios lie below the chord at psi 0.5.
   - Legacy (06 + 12): concave, 18.2 / 36.0 / 68.4 %, "savings accelerate". It was **not significant** even then:
     the chord deviation at psi 0.5 was +64.6 [-117.0, 246.1].
3. **Crossings (mean curve, linear interpolation).**
   - 04 + 09: below the selfish equilibrium (1168.6) at psi 0.42 and below rule r2 (1148.5) at 0.44. Per scenario
     0.30-0.53 and 0.35-0.53.
   - 06 + 12: 0.25 (selfish, 1248.9) and 0.27 (r2, 1238.5). Per scenario 0.12-0.45 and 0.14-0.45.
   - Legacy: 0.32 and 0.43.
   - Significantly below the selfish equilibrium (paired over scenarios): 04 + 09 from psi 0.75 on (-266.4
     [-335.0, -197.8]); 06 + 12 only at psi 1.
4. **Price of decentralisation (selfish minus ILP).**
   - 04 + 09: 468.6 USD [380.0, 557.3], 40.1 % of the selfish cost.
   - 06 + 12: 446.4 [191.9, 701.0], 35.7 %. This is a lower bound, because the ILP is time-limited; against the MIP
     bounds it is up to 493.1 [202.3, 783.9].
   - Legacy: 354.3 [276.7, 432.0], 33.5 %.
   - Rule r2 minus ILP: 448.5 [387.6, 509.4] and 436.1 [180.9, 691.3].
5. **The layout ranking depends on the follower and is established only under the coordinated ILP.** Under the ILP,
   04 + 09 is cheaper by 102.5 USD [37.2, 167.7], in 3/3 scenarios. Against the MIP lower bounds of 06 + 12 it is
   still cheaper by 55.8 [25.6, 86.1].
   - Under r2 (-90.1 [-381.7, 201.5]) and the selfish equilibrium (-80.3 [-440.5, 279.9]) the mean order is the same,
     but both CIs include zero and scenario 2 reverses it.
   - At psi 0 / 0.25 / 0.5 the mean order reverses: 06 + 12 is cheaper by 16.2 / 55.9 / 49.8 USD, none significant.
     At psi 0.75 it returns (-34.9 [-162.0, 92.2]).
6. **Zero compliance on the planned station layer is worse than free station choice in every scenario on both
   layouts.** psi 0 minus selfish: +322.6 [-27.6, 672.7] (04 + 09) and +226.1 [-249.2, 701.3] (06 + 12); legacy
   +107.6.
7. **At the calibrated prices the compliance curve is essentially a served-order curve.** Within a scenario, each
   additional served order lowers the run cost by 61.0 USD (04 + 09, R^2 0.97, 45 runs) and by 53.5 USD (06 + 12,
   R^2 0.96), close to the 60 USD unserved-order price. The legacy fit gives 41.1 USD with R^2 0.66. Extra served
   orders per 0.25 step are flat on 04 + 09 (3.4, 2.8, 3.0, 3.4) and front-loaded on 06 + 12 (4.3, 3.1, 2.7, 2.2),
   which matches the two shapes.
8. **The selfish equilibrium is no better than rule r2 on Manhattan either.** Selfish minus r2 is +20.1
   [-35.2, 75.4] on 04 + 09 and +10.3 [-34.1, 54.7] on 06 + 12. On 06 + 12 the two schedules are identical in
   scenarios 0 and 2.

## P3.2 Numbers

**Table P3-A. Layout values under the three followers (written targets; V in USD per 4-h window; 95 % CI over
scenarios).**

| layout | follower | V [95 % CI] | per scenario | served share [CI] | status |
|---|---|---|---|---|---|
| 04 + 09 | Coordinated ILP | 699.96 [509.64, 890.28] | 683.06, 633.20, 783.61 | 0.983 [0.947, 1.019] | OPT x 3 |
| 04 + 09 | Rule r2 | 1148.45 [905.21, 1391.69] | 1142.59, 1053.59, 1249.17 | 0.825 [0.763, 0.887] | policy |
| 04 + 09 | Selfish equilibrium | 1168.58 [889.76, 1447.41] | 1140.98, 1072.72, 1292.05 | 0.808 [0.737, 0.880] | MSA 2, 5, 4 it., converged |
| 06 + 12 | Coordinated ILP | 802.43 [665.24, 939.61] | 776.01, 765.37, 865.90 | 0.958 [0.922, 0.994] | TL x 3 (6.44, 8.49, 2.88 %) |
| 06 + 12 | ILP MIP lower bound | 755.79 [569.74, 941.84] | 726.02, 700.36, 840.99 | - | bound |
| 06 + 12 | Rule r2 | 1238.55 [1061.26, 1415.84] | 1320.40, 1189.34, 1205.90 | 0.750 [0.642, 0.858] | policy |
| 06 + 12 | Selfish equilibrium | 1248.87 [1093.95, 1403.79] | 1320.40, 1220.30, 1205.90 | 0.758 [0.663, 0.853] | MSA 10, 6, 3 it., converged |

Relative to the ILP, r2 and the selfish equilibrium cost 64.1 / 67.0 % more on 04 + 09 and 54.4 / 55.6 % more on
06 + 12. Legacy, 06 + 12: 45.2 / 50.4 %.

**Table P3-B. Compliance curve (V in USD; served share).**

| layout | psi | V | CI over scenarios | CI over draws | served share | CI over scenarios | CI over draws |
|---|---|---|---|---|---|---|---|
| 04 + 09 | 0 | 1491.1 | [1077.6, 1904.7] | 0 (identical draws) | 0.667 | [0.432, 0.902] | 0 |
| 04 + 09 | 0.25 | 1307.2 | [1148.9, 1465.5] | [1155.4, 1459.0] | 0.753 | [0.690, 0.816] | [0.686, 0.819] |
| 04 + 09 | 0.5 | 1100.1 | [877.4, 1322.9] | [969.4, 1230.9] | 0.822 | [0.756, 0.889] | [0.779, 0.865] |
| 04 + 09 | 0.75 | 902.2 | [671.6, 1132.8] | [779.6, 1024.8] | 0.897 | [0.834, 0.960] | [0.831, 0.964] |
| 04 + 09 | 1 | 700.0 | [509.6, 890.3] | 0 | 0.983 | [0.947, 1.019] | 0 |
| 06 + 12 | 0 | 1474.9 | [1050.3, 1899.5] | 0 (identical draws) | 0.650 | [0.542, 0.758] | 0 |
| 06 + 12 | 0.25 | 1251.3 | [895.2, 1607.4] | [946.9, 1555.6] | 0.758 | [0.609, 0.908] | [0.643, 0.874] |
| 06 + 12 | 0.5 | 1050.4 | [775.2, 1325.5] | [965.5, 1135.2] | 0.836 | [0.734, 0.938] | [0.763, 0.909] |
| 06 + 12 | 0.75 | 937.1 | [715.2, 1159.0] | [823.6, 1050.6] | 0.903 | [0.824, 0.981] | [0.819, 0.986] |
| 06 + 12 | 1 | 802.4 | [665.2, 939.6] | 0 | 0.958 | [0.922, 0.994] | 0 |

**Table P3-C. Share of the no-to-full gap closed, and chord deviation.** Gap closed = (V(0) - V(psi)) / (V(0) - V(1)).
"Mean curve" is the ratio of scenario means. The CI columns give the mean of the per-scenario ratios over scenarios,
and the over-draw interval. Chord deviation = V(psi) - [(1 - psi) V(0) + psi V(1)] per scenario: > 0 means concave
(savings accelerate), < 0 means convex (front-loaded).

| layout | psi | gap closed, mean curve | per-scenario mean [CI over scenarios] | CI over draws | chord deviation USD [CI over scenarios] |
|---|---|---|---|---|---|
| 04 + 09 | 0.25 | 23.2 % | 20.4 [-39.4, 80.3] | [4.1, 42.4] | +13.8 [-395.1, 422.8] |
| 04 + 09 | 0.5 | 49.4 % | 46.9 [-6.0, 99.8] | [32.9, 66.0] | +4.6 [-359.6, 368.8] |
| 04 + 09 | 0.75 | 74.4 % | 73.6 [55.2, 92.0] | [58.9, 89.9] | +4.4 [-125.9, 134.8] |
| 06 + 12 | 0.25 | 33.3 % | 33.4 [26.6, 40.2] | [-12.0, 78.5] | -55.5 [-102.5, -8.5] |
| 06 + 12 | 0.5 | 63.1 % | 63.5 [50.1, 76.9] | [50.5, 75.7] | -88.3 [-155.5, -21.1] |
| 06 + 12 | 0.75 | 80.0 % | 79.9 [68.8, 90.9] | [63.1, 96.9] | -33.5 [-110.6, 43.7] |
| legacy 06 + 12 | 0.25 | 18.2 % | 16.0 [-24.2, 56.3] | - | +31.5 [-126.6, 189.6] |
| legacy 06 + 12 | 0.5 | 36.0 % | 33.2 [-15.8, 82.1] | - | +64.6 [-117.0, 246.1] |
| legacy 06 + 12 | 0.75 | 68.4 % | - | - | +30.5 [-57.3, 118.3] |

The drop of the mean curve per 0.25 step is 184.0, 207.1, 197.9 and 202.2 USD on 04 + 09 (constant within 12 %), and
223.7, 200.9, 113.3 and 134.7 USD on 06 + 12.

**Table P3-D. Position against the decentralised followers (paired over scenarios, USD).**

| layout | psi | V minus selfish eq. | V minus rule r2 | share of selfish gap recovered (server metric) |
|---|---|---|---|---|
| 04 + 09 | 0 | +322.6 [-27.6, 672.7] | +342.7 [-43.1, 728.5] | -68.8 % |
| 04 + 09 | 0.25 | +138.6 [-90.6, 367.8] | +158.7 [-16.4, 333.9] | -29.6 % |
| 04 + 09 | 0.5 | -68.5 [-307.6, 170.7] | -48.3 [-232.4, 135.7] | 14.6 % |
| 04 + 09 | 0.75 | **-266.4 [-335.0, -197.8]** | **-246.3 [-260.8, -231.7]** | 56.8 % |
| 04 + 09 | 1 | **-468.6 [-557.3, -380.0]** | **-448.5 [-509.4, -387.6]** | 100 % |
| 06 + 12 | 0 | +226.1 [-249.2, 701.3] | +236.4 [-212.6, 685.4] | -50.6 % |
| 06 + 12 | 0.25 | +2.4 [-429.9, 434.7] | +12.7 [-400.8, 426.2] | -0.5 % |
| 06 + 12 | 0.5 | -198.5 [-516.0, 119.0] | -188.2 [-481.3, 104.9] | 44.5 % |
| 06 + 12 | 0.75 | -311.8 [-655.1, 31.5] | -301.5 [-642.9, 40.0] | 69.8 % |
| 06 + 12 | 1 | **-446.4 [-701.0, -191.9]** | **-436.1 [-691.3, -180.9]** | 100 % |

Bold: the CI excludes zero. Over draws (which conditions on the three scenarios), 04 + 09 lies below the selfish
equilibrium from psi 0.75 on and 06 + 12 from psi 0.5 on. Crossing points per draw: 0.42, 0.47 and 0.40 (04 + 09,
selfish) and 0.27, 0.33 and 0.16 (06 + 12, selfish). The server's "share of selfish gap recovered" is
(V_selfish - V) / (V_selfish - V_ILP), which is not the no-to-full share of Table P3-C.

**Table P3-E. Layout difference V(04 + 09) - V(06 + 12) by follower (negative = 04 + 09 cheaper; paired over
scenarios).**

| follower | difference [CI over scenarios] | per scenario | 04 + 09 cheaper in |
|---|---|---|---|
| Coordinated ILP | **-102.5 [-167.7, -37.2]** | -92.9, -132.2, -82.3 | 3/3 scenarios |
| ILP, against the MIP lower bound of 06 + 12 | **-55.8 [-86.1, -25.6]** | -43.0, -67.2, -57.4 | 3/3 |
| Rule r2 | -90.1 [-381.7, 201.5] | -177.8, -135.7, +43.3 | 2/3 |
| Selfish equilibrium | -80.3 [-440.5, 279.9] | -179.4, -147.6, +86.1 | 2/3 |
| Mixed, psi 0 | +16.2 [-442.2, 474.7] | -153.7, +212.6, -10.2 | 6/9 runs |
| Mixed, psi 0.25 | +55.9 [-240.6, 352.5] | +141.8, +106.3, -80.4 | 3/9 runs |
| Mixed, psi 0.5 | +49.8 [-117.4, 216.9] | +107.6, +65.8, -24.1 | 5/9 runs |
| Mixed, psi 0.75 | -34.9 [-162.0, 92.2] | +20.1, -81.0, -43.8 | 7/9 runs |

**Table P3-F. Calibrated against legacy prices.** USD amounts are not comparable across price regimes. Shares,
crossing points and percentages are.

| quantity | 06 + 12, legacy (P 30 / v 36) | 06 + 12, calibrated | 04 + 09, calibrated |
|---|---|---|---|
| V at psi 0 / 0.25 / 0.5 / 0.75 / 1 | 1165.0 / 1081.1 / 998.6 / 849.1 / 703.1 | 1474.9 / 1251.3 / 1050.4 / 937.1 / 802.4 | 1491.1 / 1307.2 / 1100.1 / 902.2 / 700.0 |
| gap closed at 0.25 / 0.5 / 0.75 | 18.2 / 36.0 / 68.4 % | 33.3 / 63.1 / 80.0 % | 23.2 / 49.4 / 74.4 % |
| shape | concave on the mean, not significant | convex, significant at 0.25 and 0.5 | linear |
| crossing selfish / r2 | 0.32 / 0.43 | 0.25 / 0.27 | 0.42 / 0.44 |
| price of decentralisation | 354.3 [276.7, 432.0] (33.5 %) | 446.4 [191.9, 701.0] (35.7 %), at least | 468.6 [380.0, 557.3] (40.1 %) |
| psi 0 minus selfish | +107.6 [-236.7, 451.8] | +226.1 | +322.6 |
| served share psi 0 / psi 1 | 0.625 / 0.858 | 0.650 / 0.958 | 0.667 / 0.983 |
| cost per extra served order (R^2) | -41.1 USD (0.66) | -53.5 USD (0.96) | -61.0 USD (0.97) |

## P3.3 Coverage and checks

- **Records:** 113 rows.
  - 1 plan row.
  - 6 layout prices: 2 layouts x ILP / r2 / selfish.
  - 6 policy solves on 06 + 12.
  - 90 compliance runs: 2 layouts x 5 psi x 3 scenarios x 3 draws. All are `OK` with `station_plan = plan`.
  - 10 compliance summaries, all `complete`.
- **No ILP was solved in this run.**
  - 15 cache rows were seeded from the siting-pass cache, which is why the run took 255 s instead of the expected
    75 min. The 04 + 09 r2 and selfish values are also siting-pass cache rows.
  - The six 06 + 12 policy runs were computed in this run.
  - The values agree with the siting pass (UB 699.957; 06 + 12 at 802.43), the demand md5 values agree with the plan
    row, and every row carries P 60 / w 18 / v 15.
- **Earlier attempt.** The NO_PLAN attempt (laptop paths in the cache) is not in this folder.
- **Selfish equilibria:** 6, all converged (MSA, tol 0.01, cap 10). 06 + 12 scenario 0 stopped at iteration 10 (the
  cap) with `converged = True` and zero share change.
- **Defections** (a compliant rider becomes a policy rider when a planned swap cannot be honoured): 0.56 / 1.00 / 0.56
  per run on 04 + 09 at psi 0.25 / 0.5 / 0.75, and 0 / 0.11 / 0.11 on 06 + 12. Planned swaps executed: 2.3 / 5.0 / 8.0
  of 11, and 1.9 / 3.7 / 5.8 of 8.
- **Runs passing all checks** at psi 0 ... 1:
  - 04 + 09: 6, 2, 2, 3 and 9 of 9.
  - 06 + 12: 0 of 9 at every psi below 1, and 9 of 9 at psi 1.
  - No hard family is violated in any run (details in P3.5, item 4).
- **Figures** (vector PDF + 300-dpi PNG, `outputs/r6_fill/compliance/figs/`). Checked: English labels, no internal
  codes; layouts are named "Sites 04 + 09 (best two-site layout found)" and "Sites 06 + 12 (earlier bi-level layout)".
  - `fig_r6_compliance_curve.pdf`: V and served share against psi on both layouts, with the selfish and r2
    references and the crossing marked. Replaces fig:res:compliance.
  - `fig_r6_compliance_shape_ranking.pdf`: (a) gap closed against psi for legacy 06 + 12, calibrated 06 + 12 and
    calibrated 04 + 09, with the proportional line; (b) the layout difference by follower. Suggested for S10.5.

## P3.4 PENDING_R6.md items

### Item 4 (selfish equilibrium, price of decentralisation 354.3 USD, compliance sweep): resolved, can be replaced in full

**Conditions.**
- (a) Call the layout "the best two-site layout found by the siting search (within 3.39 % of a certified lower
  bound)", never "certified".
- (b) The manuscript must say where that layout comes from. While item 2 (siting) is still legacy, this needs one
  sentence or footnote: found by a calibrated-price two-site search with written targets, which stopped at its wall
  budget 3.39 % above a certified lower bound of 676.24 USD.
- (c) Directions change, not only numbers. "Savings accelerate", "more than proportionally" and "about a third" become
  "proportional (about half)" on the best layout and "front-loaded" on the earlier layout.
- (d) The 6.9 first paragraph cites Table tab:res:siting, which stays legacy (item 2). Cite Section S10.5 instead, or
  add Table P3-A as a supplement table.

The siting-study pieces inside the item-4 locations stay with item 2, labelled legacy:
- the price-of-decentralisation range 263.6-550.0 USD on the other layouts;
- the count "84 selfish equilibria, 82 converged".

Exact replacement statements (LaTeX, in the manuscript's style). File and line refer to the current sources in
`manuscript/`.

**R1. Section 6.9, first paragraph, sentences 1-2** (`sections/06b_results.tex` l. 143). Replace the text from "On the
bi-level layout, the same infrastructure costs 703.1~USD" to "to 550.0~USD at a single site at 08." with:

```latex
At the calibrated prices, on the best two-site layout found by the siting search with written targets (sites 04 and 09, within 3.39\,\% of a certified lower bound), the same infrastructure costs 700.0~USD per window when riders follow the ILP plan with written targets (optimal in all three scenarios), 1,148.5~USD under rule r2 and 1,168.6~USD in the selfish equilibrium M4 ($n=3$ scenarios; Section~\sref{sec:supp:siting}), 64--67\,\% more, while the served share falls from 0.983 to 0.825 and 0.808. The price of decentralisation, the selfish-equilibrium cost minus the ILP cost, is 468.6~USD per window (95\,\% CI 380.0--557.3), 40.1\,\% of the selfish cost. On the earlier bi-level layout (sites 06 and 12) the three costs are 802.4, 1,238.5 and 1,248.9~USD, and the price of decentralisation is at least 446.4~USD (191.9--701.0), because the ILP values are time-limited incumbents (MIP gaps 2.88--8.49\,\%; up to 493.1~USD against the MIP bounds). At the legacy prices it was 354.3~USD (276.7--432.0) on that layout, and on the other layouts of the siting study it ranged from 263.6~USD at the four-site CSCD layout, whose interval includes zero, to 550.0~USD at a single site at 08.
```

**R2. Section 6.9, last sentence of the first paragraph.** Replace "Of the 84 selfish equilibria of the Manhattan
study, 82 converged; the other two stopped at the cap of ten iterations and are approximate." with:

```latex
The six selfish equilibria of this comparison all converged (one at the cap of ten iterations, with no share change); of the 84 equilibria of the siting study (legacy prices), 82 converged and the other two stopped at the cap and are approximate.
```

**R3. Section 6.9, paragraph "Partial compliance"** (l. 146). Replace the whole paragraph with:

```latex
In the compliance sweep (Figure~\ref{fig:res:compliance}), a share $\psi$ of the eight riders follows the ILP's written-target plan, the stations keep the planned inventory and charging, and the other riders choose stations by M4 (three draws of the compliant set per scenario; $n=3$ scenarios). On the best layout found, $V$ falls from 1,491.1~USD at $\psi=0$ to 700.0~USD at $\psi=1$, and $\psi=0.25$, 0.5 and 0.75 close 23.2, 49.4 and 74.4\,\% of this difference (intervals in Section~\sref{sec:supp:siting}), while the served share rises from 0.667 to 0.983. The benefit is proportional to compliance: at $\psi=0.5$ the curve lies 4.6~USD above the straight line between its end points (95\,\% CI $-359.6$ to 368.8). On the earlier bi-level layout it is front-loaded: $\psi=0.25$, 0.5 and 0.75 close 33.3, 63.1 and 80.0\,\% of a 672.5~USD difference, and at $\psi=0.5$ all three scenarios lie below the straight line ($-88.3$~USD, $-155.5$ to $-21.1$). By linear interpolation the mean curve crosses the selfish equilibrium on free stations (1,168.6~USD) at about $\psi=0.42$ and rule r2 (1,148.5~USD) at about $\psi=0.44$ on the best layout found (per scenario 0.30--0.53), and at about 0.25 and 0.27 on the earlier layout (per scenario 0.12--0.45). The mixed system is significantly cheaper than the selfish equilibrium from $\psi=0.75$ on the best layout found ($-266.4$~USD, $-335.0$ to $-197.8$), but on the earlier layout only at $\psi=1$. Zero compliance costs more than free station choice in every scenario on both layouts (by 322.6 and 226.1~USD on average), because the stations hold inventory planned for coordinated riders. The mixed runs ignore the written end targets, which favours partial compliance. Within a scenario, each additional served order lowers the cost by 61.0 and 53.5~USD ($R^2$ 0.97 and 0.96), so at the calibrated prices the compliance curve follows the number of orders served. The coordination gain therefore depends on riders following the plan, and it accrues in proportion to compliance or faster. At the legacy prices the mean curve was concave (18.2, 36.0 and 68.4\,\%), but no deviation from the straight line was significant. Whether a layout chosen for self-interested riders would lower the price of decentralisation remains open.
```

**R4. Figure fig:res:compliance** (l. 150-151). Copy `outputs/r6_fill/compliance/figs/fig_r6_compliance_curve.pdf`
to `manuscript/figs/`. Then replace the `\includegraphics` line and the caption with the following (the label stays):

```latex
\includegraphics[width=\linewidth]{figs/fig_r6_compliance_curve.pdf}
\caption{Compliance sweep at the calibrated prices on two Manhattan layouts, written targets: $V$ per four-hour window (top) and served share (bottom) against the share $\psi$ of riders who follow the coordinated plan; (a) sites 04 and 09, the best two-site layout found by the siting search; (b) sites 06 and 12, the earlier bi-level layout. Line: mean over the three demand scenarios; band: exact-$t$ 95\,\% interval over scenarios ($n=3$); grey dots: scenario means over three draws of the compliant riders. Dashed: selfish equilibrium M4 on free stations; dotted: rule r2 on the same layout; open circle: crossing of the mean curve with the selfish equilibrium. At $\psi=1$ the value equals the ILP plan (time-limited incumbents in (b)).}\label{fig:res:compliance}
```

The figure is double-column (two panels). The main-text figure count is unchanged (10 of 12).

**R5. Section S10.5, first paragraph** (`supplement/s10_siting_behaviour.tex` l. 50).

Replace the first sentence ("On the bi-level layout, the same infrastructure costs 703.1~USD ... ($n=3$ scenarios).")
with:

```latex
At the calibrated prices, on the best two-site layout found (sites 04 and 09), the same infrastructure costs 700.0~USD per window (95\,\% CI 509.6--890.3) when riders follow the ILP plan with written targets, 1,148.5~USD (905.2--1,391.7) under rule r2 and 1,168.6~USD (889.8--1,447.4) in the selfish equilibrium M4 ($n=3$ scenarios); on the earlier bi-level layout (sites 06 and 12) the three costs are 802.4~USD (665.2--939.6; time-limited incumbents with mean MIP lower bound 755.8~USD), 1,238.5~USD (1,061.3--1,415.8) and 1,248.9~USD (1,094.0--1,403.8). The selfish equilibrium costs 20.1~USD ($-35.2$ to 75.4) and 10.3~USD ($-34.1$ to 54.7) more than rule r2 on the two layouts; on the earlier layout the two schedules coincide in scenarios 0 and 2, as they did at the legacy prices.
```

Replace the last sentence ("Of the 84 selfish equilibria computed in the Manhattan study, ... approximate equilibria.")
with:

```latex
The six selfish equilibria of this comparison all converged, in 2, 5 and 4 iterations on the best layout found and in 10, 6 and 3 on the earlier layout (the tenth, at the cap, moved no share). Of the 84 selfish equilibria computed in the siting study (legacy prices), 82 converged and 2 stopped at the cap of ten iterations, one of them the CSCD comparator in scenario 2 (also in its relaxed-target copy); these two values are approximate equilibria.
```

**R6. Section S10.5, compliance paragraph** (l. 52). Replace the whole paragraph with:

```latex
In the compliance sweep (calibrated prices), three random draws of the compliant set were run per scenario ($n=3$ scenarios, nine runs per value of $\psi$ and layout); a draw selects the same riders in every scenario and on both layouts, and its compliant sets are nested in $\psi$. On the best two-site layout found, $V$ falls from 1,491.1~USD (95\,\% CI 1,077.6--1,904.7) at $\psi=0$ to 1,307.2~USD (1,148.9--1,465.5), 1,100.1~USD (877.4--1,322.9), 902.2~USD (671.6--1,132.8) and 700.0~USD (509.6--890.3) at $\psi=0.25$, 0.5, 0.75 and 1, while the served share rises from 0.667 to 0.983. These values close 23.2, 49.4, 74.4 and 100\,\% of the gap between no and full compliance (over the three draws of the compliant riders, half compliance closes 32.9--66.0\,\%), and the curve stays within 14~USD of the straight line between its end points, so the benefit is proportional to compliance. On the earlier bi-level layout, $V$ is 1,474.9~USD (1,050.3--1,899.5), 1,251.3~USD (895.2--1,607.4), 1,050.4~USD (775.2--1,325.5), 937.1~USD (715.2--1,159.0) and 802.4~USD (665.2--939.6), closing 33.3, 63.1 and 80.0\,\% of the gap, with the served share rising from 0.650 to 0.958; the curve lies below the straight line at $\psi=0.25$ ($-55.5$~USD, $-102.5$ to $-8.5$) and $\psi=0.5$ ($-88.3$~USD, $-155.5$ to $-21.1$), so the benefit is front-loaded. At the legacy prices on the earlier layout the mean curve was concave (18.2, 36.0 and 68.4\,\%), but its deviations from the straight line all included zero ($+64.6$~USD at $\psi=0.5$, $-117.0$ to 246.1). Not every scenario is monotone; on the best layout found, in scenario 0, $V$ rises from 1,311.5 to 1,357.4~USD between $\psi=0$ and $\psi=0.25$. Zero compliance costs more than the selfish equilibrium on free stations in every scenario (by 322.6 and 226.1~USD on average on the two layouts), because the stations hold the inventory planned for coordinated riders, which is wrong for riders who choose stations themselves. In the mean over the three scenarios the coordinated station plan cost more than free station choice below $\psi\approx0.42$ on the best layout found and below $\psi\approx0.25$ on the earlier one; per scenario the crossing lay between 0.30 and 0.53 and between 0.12 and 0.45. Within a scenario, each additional served order lowers the run cost by 61.0~USD ($R^2$ 0.97) and 53.5~USD ($R^2$ 0.96) on the two layouts, against 41.1~USD ($R^2$ 0.66) at the legacy prices. Under the coordinated follower the best layout found is 102.5~USD per window cheaper than the earlier layout (37.2--167.7; in all three scenarios, and by 55.8~USD, 25.6--86.1, against the earlier layout's MIP lower bounds); under rule r2 ($-90.1$~USD, $-381.7$ to 201.5), the selfish equilibrium ($-80.3$~USD, $-440.5$ to 279.9) and partial compliance the two layouts cannot be told apart, and at $\psi\le0.5$ the mean order reverses (not significant).
```

Optional: add `figs/fig_r6_compliance_shape_ranking.pdf` to S10.5 (supplement figures 24 -> 25), with this caption:

```latex
\caption{Calibrated prices unless marked. (a) Share of the cost difference between no and full compliance closed at each $\psi$: earlier bi-level layout at the legacy prices (open triangles, dashed) and at the calibrated prices (squares), best two-site layout found at the calibrated prices (circles); bars: exact-$t$ 95\,\% intervals over scenarios ($n=3$); grey line: proportional benefit. (b) Paired difference $V$(sites 04 and 09) $-$ $V$(sites 06 and 12) per window under the coordinated ILP (also against the MIP lower bound of the earlier layout), rule r2, the selfish equilibrium and partial compliance; dot and bar: mean and 95\,\% interval over the three scenarios; grey dots: scenarios; negative values favour sites 04 and 09.}
```

**R7. Section 7.2, compliance paragraph** (`sections/07_discussion.tex` l. 22). Replace the whole paragraph with:

```latex
Partial compliance lowers the cost in proportion to the share of riders who comply on the best two-site layout found, and faster than that on the earlier bi-level layout (Figure~\ref{fig:res:compliance}): half compliance closed 49.4 and 63.1\,\% of the cost difference. With no compliance the planned inventory cost more than free station choice in every scenario, so a plan that assumes compliance can be worse than none. The 468.6~USD per window between selfish and coordinated operation (40\,\% of the selfish cost) bounds what untested incentives, such as reserved batteries, could recover.
```

**R8. Section 7.3** (l. 34). Replace "and two of 84 selfish equilibria stopped at the iteration cap (legacy prices)"
with "and two of the 84 selfish equilibria of the siting study stopped at the iteration cap (legacy prices)".

**R9. Section 8, RQ4/RQ5 sentence** (`sections/08_conclusion.tex` l. 10).
- Replace "On siting (RQ4) and rider behaviour (RQ5), both studied at the legacy prices, layout rankings" with "On
  siting (RQ4), studied at the legacy prices, layout rankings".
- Replace "; half of the riders complying closed 36.0\,\% of the cost difference between no and full compliance
  ($n=3$ scenarios)." with:

```latex
. On rider behaviour (RQ5), at the calibrated prices, half of the riders complying closed 49.4\,\% of the cost difference between no and full compliance on the best two-site layout found (95\,\% CI over draws of the compliant riders 32.9--66.0\,\%; $n=3$ scenarios) and 63.1\,\% on the earlier bi-level layout, and selfish station choice cost 468.6~USD per window (380.0--557.3) more than the coordinated plan.
```

**R10. Abstract** (`main.tex` l. 70). Two edits; together they cut the abstract from 249 to 246 words.
- Replace "used for the siting and compliance experiments" with "used for the siting experiments".
- Replace "and half compliance with the plan closes about a third of the gain." with "and half compliance with the
  plan closes about half of the gain."

**R11. Introduction, findings paragraph** (`sections/01_introduction.tex` l. 31). Replace "and half compliance with the
coordinated plan closes about a third of the gain (RQ5); the siting and compliance results are reported at the legacy
prices." with "and half compliance with the coordinated plan closes about half of the gain (RQ5); the siting results
are reported at the legacy prices."

**Also affected, though not listed under item 4.** These are compliance statements made for the same reason, and
they should change with item 4.

- **R12. Section 6.3** (`sections/06_results.tex` l. 95). After the list of "Five legacy-price findings ... do not
  survive", add:

  ```latex
  The accelerating compliance curve of the legacy prices is proportional or front-loaded at the calibrated prices (Section~\ref{sec:results:behaviour}); it was not significant at the legacy prices either.
  ```

  Do not file it under "depended on cheap dropping". The served-order mechanism is suggested by the records, not
  shown.
- **R13. Section 7.3** (`sections/07_discussion.tex` l. 30), three edits:
  - "(transfers, Manhattan siting and compliance, the ten-bike ...)" becomes "(transfers, Manhattan siting, the
    ten-bike ...)".
  - "in the siting and compliance experiments the rules read the prices only through M3's stock-out value, so a
    change of prices could alter the rule layouts but not the mechanism by which the ILP ranks layouts" becomes "in
    the siting experiments the rules read the prices only through M3's stock-out value, so a change of prices could
    alter the rule layouts but not the mechanism by which the ILP ranks layouts; the compliance curve, re-run at the
    calibrated prices, changed shape (Section~\ref{sec:results:behaviour})".
  - "Five legacy-price findings listed in Section~\ref{sec:results:prices} do not survive the calibration." becomes
    "Five legacy-price findings listed in Section~\ref{sec:results:prices}, and the accelerating compliance curve, do
    not survive the calibration."
- **R14. Section 7.4** (l. 38). "and the accelerating compliance curve calls for incentive design" becomes "and the
  dependence of the gain on compliance, with a plan that is worse than free station choice when nobody complies,
  calls for incentive design".
- **R15. Section S10, introduction** (`supplement/s10_siting_behaviour.tex` l. 12). Replace "All siting, equilibrium
  and compliance results of this section were obtained at the legacy prices (P 30 / v 36) and have not been repeated
  at the calibrated prices; on layouts with shuttle services the cost-aware transfer rule M3 reads the mean penalty, so
  rule-sited layouts and selfish equilibria may change with the prices." with:

  ```latex
  The siting results of this section were obtained at the legacy prices (P 30 / v 36); on layouts with shuttle services the cost-aware transfer rule M3 reads the mean penalty, so rule-sited layouts may change with the prices. The equilibrium and compliance comparison of the last subsection is at the calibrated prices, on the best two-site layout found and on the earlier bi-level layout, with the legacy-price values given for comparison.
  ```

  This also removes a "have not been repeated" phrase that the fixer-pass wording rule bans. Update the header
  comment of the file (l. 4-5) to match.
- **R16 (optional, price-independent clarification). Section 4.3** (`sections/04_methods.tex` l. 66). Replace "and
  the other bikes follow the logit rule." with "and the other bikes follow the logit rule once, with the waits of the
  day itself rather than in equilibrium, so that $\psi=0$ is not the selfish equilibrium."

### Item 15 (settings and coverage tables): partly resolved

- **Table S4, settings** (`supplement/s04_costs_parameters.tex` l. 133). Replace the row "Manhattan siting
  (\mref{sec:results:siting}, \mref{sec:results:behaviour}) & ... selfish equilibrium and compliance sweep & ... &
  legacy \\" with two rows. The siting row stays legacy.

  ```latex
  Manhattan siting (\mref{sec:results:siting}) & \texttt{manhattan}, budgets $m=1,\dots,4$ & scenarios 0--2 (3) & 300~s (600~s with a hub) & legacy \\
  Selfish equilibrium and compliance (\mref{sec:results:behaviour}) & \texttt{manhattan}, sites 04 and 09 and sites 06 and 12, written targets; $\psi\in\{0,0.25,0.5,0.75,1\}$, 3 draws & scenarios 0--2 (3) & 300~s (ILP plans of the siting search) & calibrated \\
  ```

- **Table tab:app:coverage, calibrated** (`supplement/s12_status_recovery.tex`). Add this row:

  ```latex
  Manhattan equilibrium and compliance & calibrated & 113 & Coordinated ILP plans reused from the siting search (300~s, no new solve): sites 04 and 09, 3 of 3 optimal; sites 06 and 12, 3 TL (2.88--8.49\,\%). Six selfish equilibria, all converged (one at the 10-iteration cap with no share change); 90 compliance runs complete & 0; 0 \\
  ```

  The "Manhattan siting" row of tab:app:coverage-legacy stays (it carries the siting stages and the 84 equilibria).
- The rest of item 15 (other experiments) is unaffected.

### Item 2 (Manhattan siting): not replaced

This run gives calibrated-price evidence for two layouts only, as input to the 7.2 layout-ranking sentence. The
ranking is significant only under the coordinated follower (Table P3-E). If an interim sentence is wanted in 7.2
(l. 20) before item 2 is replaced:

```latex
At the calibrated prices, the best two-site layout found was 102.5~USD per window cheaper than the earlier bi-level layout under the coordinated follower (37.2--167.7; $n=3$ scenarios; also against its MIP lower bounds), but the two could not be told apart under rule r2, selfish choice or partial compliance (Section~\sref{sec:supp:siting}).
```

**Not affected:** item 20, the M4-versus-best-rule values on the learning families (45.7 / 21.1 USD; already
calibrated; still "verify").

**Status update for PENDING_R6.md** once R1-R15 are applied: item 4 becomes "replaced (calibrated prices,
`outputs/r6_fill/compliance`)", and item 15 becomes "partly replaced (compliance rows)".

## P3.5 Caveats

1. **The layout is not certified.** 04 + 09 is the best written-target two-site layout found. In every row
   `o2_certified` is False, the gap to the lower bound 676.24 is 3.39 %, and the siting pass stopped on its wall
   budget with 3,140 layouts still open. PENDING item 4 asked for "the certified layout".
2. **The 06 + 12 ILP endpoints are time-limited incumbents** (MIP gaps 6.44 / 8.49 / 2.88 %; mean bound 755.79). So
   its psi 1 value is an upper bound and its price of decentralisation a lower bound (up to 493.1), and its mixed runs
   follow these incumbent plans. The ILP layout ranking survives the bounds.
3. **psi 0 is not the selfish equilibrium.** The stations replay the ILP plan, and the riders run the logit rule once
   without equilibrium iteration. psi 0 costs more than the selfish equilibrium in every scenario, so the crossing
   compares a planned station layer with free stations. The legacy sweep had the same design.
4. **The mixed and policy runs ignore the written end-of-window targets.**
   - The report-only families (17) R_end and (18) rho are violated in most mixed runs on both layouts, and in the r2
     and selfish reference runs.
   - Family (9), no terminal certificate, appears in 14 of the 27 mixed runs on 04 + 09 (5, 6 and 3 at psi 0.25, 0.5
     and 0.75) and in 1 of 27 on 06 + 12.
   - The ILP pays for the targets and the other runs do not, which favours partial compliance and decentralised
     operation; true mixed costs are somewhat higher than reported, which would move the crossings right. The size of
     this bias is not measured.
5. **Small samples.** With n 3 and t 4.303, the over-scenario CIs of V are 300-850 USD wide and mostly reflect demand
   variation common to all followers. Paired differences are the meaningful comparisons, and even those include zero
   for every layout difference except the one under the ILP. The over-draw CIs are zero by construction at psi 0
   and 1.
6. **The shape statements rest on few points.**
   - The 04 + 09 "linear" claim is a failure to reject: its chord-deviation CI at psi 0.5 is 728 USD wide.
   - The 06 + 12 "convex" claim is significant at psi 0.25 and 0.5 over scenarios, and at psi 0.5 over draws
     (-88.3 [-173.1, -3.5]).
   - The legacy "concave, savings accelerate" claim in the manuscript rested on the mean curve only: all three legacy
     chord deviations include zero.
7. **Some paths are not monotone.** On 04 + 09 scenario 0 the draw-mean V rises from psi 0 to 0.25 (1311.5 ->
   1357.4). In 3 of 36 draw-by-scenario steps per layout V rises, the largest by +121.3 USD (06 + 12, scenario 1,
   draw 1). The per-draw mean curves are monotone.
8. **Selfish equals r2 on 06 + 12 in scenarios 0 and 2.** The schedules are identical in all of x, u, c, h and z, as
   they were at the legacy prices, so the two references nearly coincide there.
9. **Defections differ by layout.** Compliant riders defected more often on 04 + 09 (0.56-1.00 per run, in 5-6 of 9
   runs) than on 06 + 12 (0-0.11). Site 04 holds only two spares. It is plausible, but not tested, that this is why
   the first compliant riders gain less on 04 + 09.
10. **The mechanism is suggested, not shown.** The reading of the shape change as a price effect is inferred from
    run totals and served shares: V tracks served orders at P 60, while lateness at 36 USD/h decoupled them at the
    legacy prices. The records hold no component decomposition of the mixed runs.
11. **Cache reuse.** No ILP was solved in this run, and all ILP plans and the 04 + 09 reference values come from the
    siting-pass cache. They agree with the siting pass, but they inherit its status: 06 + 12 is time-limited.
12. **Do not quote the server's `RESULTS.md`.** It prints "Anomalies: none", and its
    "share_of_selfish_gap_recovered" is a different metric from the no-to-full share. Quote only `RESULTS_final.md`.
13. **Dependence on item 2.** Replacement R1 needs one sentence in the manuscript on the calibrated-price siting
    search that produced 04 + 09 (condition (b) above). Without it, the main text would cite a layout that it does not
    introduce.
14. **Mixed clocks; not refuter-checked.** Server rows are about 4 h ahead of local EDT. This part has not been
    through a refuter pass. Its numbers come from `RESULTS_final.md`, and the key values were re-derived from
    `records.jsonl` for this digest. The replacement wordings R1-R16 are this digest's own.

## P3.6 Sources

- `outputs/r6_fill/compliance/RESULTS_final.md` (script `figs/compliance_final.py`; numbers
  `figs/compliance_numbers.json`; per-run table `figs/compliance_cells.csv`)
- `outputs/r6_fill/compliance/{records.jsonl, layout_values.csv, per_draw.csv, summary.csv, wall_time.json}` (server
  outputs, unchanged)
- `outputs/r6_fill/compliance/figs/fig_r6_compliance_curve.{pdf,png}`,
  `figs/fig_r6_compliance_shape_ranking.{pdf,png}`
- `outputs/r6_o2/manhattan_pass2/RESULTS.md` (layout 04 + 09, UB 699.96, LB 676.24, gap 3.39 %)
- `outputs/r5_x6_manhattan/RESULTS_final.md` (legacy compliance on 06 + 12)
- `manuscript/PENDING_R6.md` (items 2, 4, 15, 20); manuscript sources `main.tex`, `sections/01, 04, 06, 06b, 07,
  08`, `supplement/s04, s10, s12` (line numbers as of 2026-10-20)

---

# Part 2: rolling-horizon extension and certified siting

**Scope.** This part covers two stages of the fill round: the rolling-horizon extension (`rolling_ext`) and the
certified Manhattan siting (`r6_o2`, first and second pass). The part-1 header lists compliance under part 2. Compliance
is covered instead by Part 3 above, which a parallel workflow appended at 11:21 from
`outputs/r6_fill/compliance/RESULTS_final.md`. This part does not change Part 3 or re-check it. It only notes the places
where the siting results here update Part 3 (P2.6, item 4). Parts 1 and 3 are not edited.

Date: 2026-10-20. Prices as in part 1: new prices P 60 USD, w 18 USD/h, v 15 USD/h; legacy prices P 30 / v 36.

**Inputs.**
- `outputs/r6_fill/rolling_ext/RESULTS_final.md`. Script `figs/make_rolling_ext_final.py`, plus an independent
  second script for costs, shares and contrasts. It reads `rolling_ext/records.jsonl` (51 rows), the lookahead-10 rows
  of `r6_penalty/rolling`, the offline references and rules of `r6_penalty/headline` (usd4h x1) and `r6_penalty/psweep`
  (stress4h P 60, with the 600 s re-solves of seeds 1-3), and the legacy counterpart `r5_x3_rolling`.
- `outputs/r6_o2/RESULTS_final.md`. Script `outputs/r6_o2/figs/siting_report.py`. It reads the first pass
  (`manhattan/`, 259 records, 19.3 h), its post-hoc bound (`manhattan_bound/BOUND.md`), the second pass
  (`manhattan_pass2/`, 969 records of which the first 259 are the copied first-pass rows; 998 cuts), its bound
  (`manhattan_pass2_bound/BOUND.md`), both logs, the notes `o2_siting_bound_design.md`, `o2_manhattan_first_pass.md`
  and `DECISIONS.md` (O2), and the legacy study `r5_x6_manhattan/RESULTS_final.md`.

No solver was run for the reports or for this digest. Last row per key everywhere: (case, seed, policy, lookahead)
for the online runs. This picks up the six cells that were first recorded `SKIPPED_BUDGET` and re-run.

**Conventions.** Same as part 1. In addition:
- Rolling: share of the offline gap kept online = (best rule - rolling) / (best rule - offline). It is given as mean
  of ratios [CI] and as ratio of means. Foresight = rolling - offline; online coordination = best rule - rolling. Both
  are also given in % of the best rule.
- "Poor window": a window that stopped at the 60 s limit with a MIP gap above 1 %.
- Siting: V = allocated set-up + mean scenario operating cost per 4-h window. UB = V of the best layout found;
  LB = valid lower bound on V*_m. Bound gap = 100 (UB - LB) / UB. A budget is certified when the gap is at most
  max(0.25 % UB, 1 USD).
- Siting CIs: n = 3 demand scenarios (t 4.303), paired by scenario. ILP status per scenario: O OPTIMAL, T TIME_LIMIT.

## P2.1 Short answers

1. **Lookahead 0 -> 10 min is the one robust online effect at the new prices.** It lowers the cost on every seed:
   - usd4h: 133.15 USD [71.59, 194.70] per window (n 10, +10/-0, t p 0.001, all 160 windows OPT);
   - stress4h: 241.90 [187.65, 296.14] (n 5, +5/-0, t p < 0.001);
   - legacy: 41.31 and 83.87 USD. The share-kept step also triples (0.21 -> 0.62 and 0.15 -> 0.41).
2. **Without lookahead the rolling coordinator keeps none of the offline gap on usd4h.**
   - usd4h: share kept -0.33 [-0.86, 0.21] (ratio of means -0.14), online coordination -4.81 % [-14.85, 5.22] of the
     best rule, cheaper than the best rule on 4/10 seeds.
   - stress4h: 0.12 [-0.12, 0.37] (ratio of means 0.15), cheaper on 4/5 seeds.
   - Legacy: 0.43 / 0.63, cheaper on 14/15 instances.
3. **Neither 20 min nor the forecast battery plan has a detectable value over 10 min.**
   - 10 -> 20 min: +0.20 USD [-84.43, 84.83] (usd4h, 6/10) and -102.02 [-306.17, 102.13] (stress4h, 2/5).
   - Plain rolling -> forecast plan: +3.00 [-69.30, 75.29] (usd4h, +5/-5, every window OPT) and -41.55
     [-182.07, 98.98] (stress4h).
   - Shares kept (ratio of means) at 10 / 20 / forecast: 0.42 / 0.42 / 0.43 on usd4h and 0.53 / 0.37 / 0.47 on
     stress4h.
   - The all-seed 10 -> 20 contrast and the stress4h forecast-plan contrast are confounded. 14 of the 360 server window
     solves stopped at 60 s, 11 of them with MIP gaps of 27-102 %. These windows sit on every seed where 20 min lost
     more than 20 USD and on both stress4h seeds where the forecast plan lost. On the 7 usd4h seeds without a poor
     window, 10 -> 20 saves 66.30 USD [22.62, 109.98] (post hoc).
4. **The prices do not move the offline gap, but they lower what survives online.** The offline gap is 27.34 % against
   28.28 % (usd4h) and 40.03 % against 39.96 % (stress4h). Paired new - legacy changes in the share kept range from
   -0.25 to -0.75, and no stress4h seed rises at any lookahead. The unpriced terminal fallback is used in 41/60
   new-price runs (legacy 47/60), so shares kept and online coordination are upper bounds.
5. **Siting: only the relaxed one-unit budget is certified.**
   - Relaxed m 1: site 09 (SC B3 C2), UB = LB = 1,052.995 USD per window, OOO. This is also the CSCD / CSTC rule
     layout.
   - Written m 1: site 08 (1,131.80) or site 09, whose value lies in [1,115.25, 1,143.03]. Bound gap 1.46 %.
   - m 2-4: not certified. Bound gaps are relaxed 3.48 %, written 3.39 % (m 2) and 2.53 % (m 3-4). The LB (675.74 /
     676.24) is only 0.9-1.4 USD above the trivial two-site bound 674.83.
6. **Rule siting is not significantly worse than the best layouts found.**
   - Written m 2: CSCD (08 + 09) costs +6.30 USD [-9.94, 22.55] (0.89 %), and by the bound at most 4.25 % more than
     the optimum.
   - Significant regrets: four-site CSCD +20.69 [10.97, 30.41] and CSTC +19.36 [7.01, 31.71] at m 4; the round-5
     layout +102.47 [37.22, 167.72] (12.8 %) under written targets.
   - The round-5 layout ties under relaxed targets (+6.71 [-11.92, 25.33]).
7. **Coordinating riders matters an order of magnitude more than siting.** On every evaluated layout the ILP is
   35-44 % cheaper than rule r2 and 32-44 % cheaper than the selfish follower. At the best two-unit layout:
   - r2 gap 39.1 % [35.1, 43.1];
   - price of decentralisation 468.6 USD [380.0, 557.3].
   Layout rankings under r2 and the selfish follower are not significantly different from the ILP's. The round-5
   layout's legacy r2 advantage (12.73 %) shrinks to 1.65 % [-10.80, 14.10].
8. **The computational fix worked at one unit and not at two to four units.**
   - The second pass ran 18-24 times faster per one-site LP (median 16 s vs 388 / 282 s) and about 14 times faster for
     two to four sites (28 s vs 388 s).
   - Envelope pruning resolved 88 / 87 of the 90 one-site layouts before any LP.
   - The pass gave finite bounds at every budget in 10.7 h; the first pass, after 19.3 h, had LB None everywhere.
   - At m >= 2 the single-layout LP cuts close essentially only the layout they are built on.

## P2.2 Coverage

| Stage | Records | Solve status | Limits, machine | Wall time |
|---|---|---|---|---|
| rolling_ext | 51 rows, 45 keys (usd4h seeds 0-9, stress4h seeds 0-4 x lookahead 0, lookahead 20, forecast plan). First status 45 ROLLING + 6 SKIPPED_BUDGET (usd4h seeds 8-9, all three policies); last 45/45 ROLLING, 0 ERROR | 360 windows: 346 OPT, 14 TL at 60 s (11 poor, gaps 27.3-101.6 %). 12 of 45 runs contain a TL window. Joined lookahead-10 rows: 15 runs, 120 windows, all OPT (max 42.9 s) | W 24 slots, commit 6, 60 s per window, Threads 3; AWS r7i.4xlarge with 5 concurrent 3-thread lanes (15 threads on 8 physical cores); lookahead 10 on the laptop (2026-10-18) | 8,870.6 s + 1,275.5 s (re-run of the 6 skipped cells, 03:51-04:12 UTC, after the other lanes ended) |
| rolling references | usd4h x1 headline offline 10/10 OPT (300 s); stress4h psweep P 60: seeds 0, 4 OPT, seeds 1-3 TL after the 600 s re-solve (0.87 / 0.40 / 0.14 %); rules r2, M2, M2+M3 all POLICY | best rule r2 on 8/10 and M2 on 2/10 usd4h seeds; r2 1/5, M2 4/5 on stress4h | - | - |
| rolling legacy | `r5_x3_rolling`: 60 relaxed runs, 480 windows all OPT; offline 14 OPT + 1 TL (0.09 %) | - | laptop (round 5) | - |
| siting, first pass | 259 records; 75 ILP solves (relaxed 37: 28 OPT, 7 TL 0.91-4.08 %, 2 bound-stopped; written 38: 21 OPT, 16 TL 0.72-45.35 %, 1 bound-stopped); 0 master solves; LB None at every budget; 5 rule cells SKIPPED_BUDGET | 74 of 75 ILP rows `check_ok` (the bound-stopped row has no schedule) | 300 s per scenario (600 s with a hub); warm-started dual simplex LPs; machine paging | 19.3 h (relaxed 538.9 + written 599.3 min) |
| siting, second pass | 710 new records; 32 ILP solves (relaxed 8: 6 OPT, 2 TL 0.47 / 0.56 %; written 24: 15 OPT, 7 TL 0.09-3.91 %, 2 bound-stopped); 8 escalations (900 s and 1,800 s); 216 master solves + 8 final bound solves, all OPT | 30 of 32 `check_ok` (2 NO_INCUMBENT); unique LP-solved layouts 65 relaxed / 141 written cumulative; 247 LP-pruned (envelope 88 / 87; by LP value 0 / 72) | cold barrier + crossover LPs; guaranteed final master bound | 10.7 h (step 1: 13.0 / 153.1 min; step 2: 238.5 / 236.9 min) |
| siting followers | r2 and selfish M4 on 6 new layout x scenario rows in pass 2 (15 in pass 1); 18 distinct selfish equilibria, 17 converged | - | MSA, cap 10 iterations | - |
| siting validation | `outputs/r6_o2/midtown_validate` (2026-10-18): the certifier returned the exhaustive-search layout with a valid LB on an 8-layout Midtown instance | - | - | - |

Both siting passes have every `budget_result` row (8 per pass). The second-pass bound recomputed from the stored cut
pool without any solve (`manhattan_pass2_bound`) equals the certifier's LB in all 8 rows. Every priced V equals the
mean of its cached per-scenario totals.

## P2.3 Verification outcome

**Stage verification.** Both stage reports went through the refuter step. No claim was refuted in either stage, and no
correction was needed. Every number of both reports was recomputed from the records by the stage scripts. The rolling
report's costs, shares and contrasts were also re-derived by a second script that shares no code with the first, with
identical results.

**My own re-derivations from the records for this digest.** All of them agree with the reports to the printed digit.
- From `rolling_ext/per_instance.csv`, the following, with exact t CIs:
  - the paired contrasts 0 -> 10, 10 -> 20 and plain -> forecast on both families;
  - the share kept, mean of ratios and ratio of means, at all four policies;
  - the seeds where rolling beats the best rule (4/9/7/8 of 10 usd4h; 4/5/4/5 of 5 stress4h).
- From `rolling_ext/records.jsonl` (last row per key):
  - 45 keys, 15 per policy;
  - 29 of 45 runs with the dummy-terminal fallback, plus 12 of 15 at lookahead 10 (`r6_penalty/rolling`), giving
    41/60;
  - 11 runs with a window gap above 0.1 %. Of these, 10 runs (11 windows) have a poor window and one run has only a
    0.40 % window. This matches T8 and T10 of the report.
- From `manhattan_pass2/records.jsonl`, the 8 `budget_result` rows: UB, LB, the certified flag and the gap for every
  target and budget, as in Table 1 of the report:
  - relaxed m 1: 1,052.995 / 1,052.995 / certified;
  - written m 1: 1,131.800 / 1,115.251 / 1.46 %;
  - relaxed m 2-4: 700.113 / 675.740 / 3.48 %;
  - written m 2: 699.957 / 676.240 / 3.39 %;
  - written m 3-4: 693.807 / 676.240 / 2.53 %.

**Points the reports correct in their own auto-generated files (do not quote those files).**
- `rolling_ext/RESULTS.md` is numerically correct. However, its `ci95` column is a half-width, it has no paired
  lookahead tests, and it prints "Anomalies: none".
- `manhattan_pass2/RESULTS.md` reports a stale relaxed UB at m 2-4 (700.113). The written values of the 04 + 09
  layouts bound relaxed V* by 699.957 (m 2) and 693.807 (m 3-4). As a result, its relaxed regret lower ends (Table 2)
  are understated by 0.16 and 6.31 USD.
- Its Table 4 also repeats the copied first-pass cross-follower rows, so site 08 written shows 1,132.394 next to the
  escalated 1,131.800.
- The first-pass diagnosis note says the enumeration stopped "at layout 47-52 of 90". The records show 50 (relaxed)
  and 45 (written).

**Inconsistencies and wording problems found while assembling this part.**
1. The siting report's "number of cabinets" statement reads "-38 %; 25-51 %". The 25-51 % interval is not in any of
   its tables. The table value is -431.8 USD [306.3, 557.4], and 306.3 / 1,131.8 and 557.4 / 1,131.8 give 27-49 %.
   The replacement in P2.6 therefore quotes the USD interval.
2. Part 3 (compliance) treats item 2 as still legacy. It therefore adds a condition (b), an interim 7.2 sentence, a
   legacy settings row in Table S4, and legacy siting-study values in its R1 / R2 texts (263.6-550.0 USD; 82 of 84
   equilibria). Once item 2 is replaced as below, these four pieces are superseded (P2.6, item 4).
3. Siting Table 3 gives relaxed m 3-4 contrasts against the *written* value of 04 + 09 (B4). This is valid as an upper
   bound on the relaxed V of that layout, but the relaxed run never priced it. These contrasts are not relaxed-vs-relaxed
   comparisons.

## P2.4 Answers by topic

### P2.4.1 Rolling horizon at lookahead 0 / 10 / 20 min and the forecast plan (`rolling_ext/RESULTS_final.md`)

**Cost per method** (USD per 4-h window, end-adjusted, relaxed targets; mean [CI]):

| method | usd4h new (n 10) | usd4h legacy | stress4h new (n 5) | stress4h legacy |
|---|---|---|---|---|
| best rule | 838.50 [753.33, 923.68] | 830.91 | 1581.76 [1289.40, 1874.12] | 1387.36 |
| rolling, lookahead 0 | 871.65 [780.09, 963.21] | 689.95 | 1484.68 [1290.45, 1678.92] | 1027.95 |
| rolling, lookahead 10 | 738.51 [672.23, 804.78] | 648.64 | 1242.78 [1015.28, 1470.29] | 944.07 |
| rolling, lookahead 20 | 738.31 [627.12, 849.50] | 620.10 | 1344.81 [1241.47, 1448.15] | 948.44 |
| forecast battery plan, 10 min | 735.51 [678.71, 792.31] | 641.88 | 1284.33 [1007.08, 1561.58] | 934.37 |
| offline ILP | 601.41 [572.70, 630.13] | 582.05 | 941.46 [820.06, 1062.87] | 826.10 |

**Share kept, online coordination and foresight** (new prices; legacy in parentheses):

| policy | share kept, mean of ratios | ratio of means | online coordination, % best rule | foresight, % best rule | cheaper than best rule |
|---|---|---|---|---|---|
| usd4h, lookahead 0 | -0.33 [-0.86, 0.21] (0.43) | -0.14 (0.57) | -4.81 [-14.85, 5.22] (14.93) | 32.16 [23.80, 40.51] (13.34) | 4/10 (9/10) |
| usd4h, lookahead 10 | 0.29 [-0.19, 0.77] (0.64) | 0.42 (0.73) | 11.00 [2.40, 19.59] (19.94) | 16.35 [10.00, 22.69] (8.33) | 9/10 (10/10) |
| usd4h, lookahead 20 | 0.35 [-0.06, 0.77] (0.81) | 0.42 (0.85) | 11.34 [-0.61, 23.30] (23.65) | 16.00 [5.02, 26.98] (4.63) | 7/10 (10/10) |
| usd4h, forecast plan | 0.11 [-0.82, 1.04] (0.68) | 0.43 (0.76) | 10.29 [-3.72, 24.29] (20.91) | 17.06 [7.58, 26.54] (7.36) | 8/10 (10/10) |
| stress4h, lookahead 0 | 0.12 [-0.12, 0.37] (0.63) | 0.15 (0.64) | 5.39 [-3.97, 14.75] (25.31) | 34.64 [28.84, 40.44] (14.66) | 4/5 (5/5) |
| stress4h, lookahead 10 | 0.53 [0.34, 0.71] (0.77) | 0.53 (0.79) | 21.11 [13.00, 29.23] (31.26) | 18.92 [11.45, 26.38] (8.70) | 5/5 (5/5) |
| stress4h, lookahead 20 | 0.29 [-0.26, 0.85] (0.76) | 0.37 (0.78) | 13.05 [-8.16, 34.27] (30.73) | 26.98 [10.34, 43.62] (9.23) | 4/5 (5/5) |
| stress4h, forecast plan | 0.48 [0.33, 0.63] (0.79) | 0.47 (0.81) | 18.97 [13.86, 24.08] (32.00) | 21.06 [13.03, 29.08] (7.96) | 5/5 (5/5) |

Foresight exceeds online coordination on 9/10 and 5/5 seeds at lookahead 0 (legacy 5/10 and 0/5). At lookahead 0 the
foresight is almost entirely orders that rolling drops and the offline ILP serves: the unserved component is 264.0 of
270.2 USD on usd4h.

**Paired contrasts** (USD per window; positive = the second policy is cheaper):

| contrast | usd4h new (n 10) | usd4h legacy | stress4h new (n 5) | stress4h legacy |
|---|---|---|---|---|
| 0 -> 10 min | 133.15 [71.59, 194.70]; +10/-0; t p 0.001 | 41.31 [22.62, 60.00]; +9/-1 | 241.90 [187.65, 296.14]; +5/-0; t p < 0.001 | 83.87 [48.77, 118.98]; +5/-0 |
| 10 -> 20 min | 0.20 [-84.43, 84.83]; +6/-4; t p 0.996 | 28.54 [2.17, 54.90]; +7/-3 | -102.02 [-306.17, 102.13]; +2/-3; t p 0.24 | -4.36 [-59.58, 50.85] |
| 10 -> 20 min, seeds without a poor window (post hoc) | 66.30 [22.62, 109.98]; +6/-1; n 7; t p 0.010 | - | 30.23 [11.22, 49.24]; n 2 | - |
| plain rolling -> forecast plan (both 10 min) | 3.00 [-69.30, 75.29]; +5/-5; t p 0.93 | 6.75 [-8.32, 21.83] | -41.55 [-182.07, 98.98]; +3/-2; t p 0.46 | 9.71 [-8.95, 28.36] |
| plain -> forecast, seeds without a poor window (post hoc) | as above (no poor window) | - | 40.37 [-4.81, 85.55]; n 3 | - |
| share kept: 10 min - 0 min | 0.615 [0.331, 0.900]; +10/-0 | 0.210 [0.101, 0.319] | 0.405 [0.208, 0.601]; +5/-0 | 0.148 [0.113, 0.184] |
| cost monotone in the lookahead | 6/10 | 6/10 | 2/5 | 3/5 |

On the three clean stress4h seeds the 0 -> 10 step keeps its sign: 221.94 [108.45, 335.42].

**Service and lateness.**
- Served share:
  - usd4h: best rule 92.5 %; lookahead 0 / 10 / 20 / forecast 86.7 / 93.3 / 93.9 / 94.2 %; offline 98.9 %.
  - stress4h: 75.4 %; 70.8 / 81.7 / 76.7 / 80.0 %; offline 95.4 %.
  - Lookahead 0 serves fewer orders than the best rule on usd4h: -5.8 pp [-10.8, -0.8], t p 0.027.
- Lateness (order-minutes per window):
  - usd4h: best rule 215.0; online 120.0 / 92.5 / 113.0 / 107.5; offline 33.0.
  - stress4h: 456.0; 158.0 / 146.0 / 124.0 / 160.0; offline 149.0.
- No online order is more than 60 min late.
- At the new prices the online policies accept 83-154 more order-minutes of lateness than at the legacy prices and
  serve 4.7-8.8 pp more orders.

**Terminal-fallback caveat.**
- 41 of 60 new-price runs use the unpriced dummy-terminal fallback: lookahead 0 / 10 / 20 / forecast 8, 8, 4, 7 of 10
  on usd4h and 4, 4, 3, 3 of 5 on stress4h. The legacy count is 47/60.
- A run breaks the terminal certificate (9) exactly when it uses the fallback, and `C_dummy_terminal` = 0 in every
  row.
- The certificate is broken for 1.5 / 1.2 / 0.6 / 0.9 bikes per run on usd4h and 1.8 / 1.0 / 1.0 / 0.8 on stress4h.
- Shares kept and online coordination are therefore upper bounds, and foresight is a lower bound.
- Lookahead 20 uses the fallback least (7/15 against 12/15 at 10 min). This biases the 10 -> 20 contrast against
  20 min.

**Shown / suggested / not shown.**
- Shown:
  - the 0 -> 10 step;
  - the near-zero online value without lookahead;
  - the null of the forecast plan on usd4h, where every window is OPT (the interval is about +-10 % of the rolling
    cost);
  - the fall in the share kept from the legacy to the new prices at every lookahead.
- Suggested only:
  - that 20 min helps when the windows are solved well (post-hoc subsets, possibly biased);
  - that the server load caused the stopped windows. Window run times were 1.8-2.7 times those expected from the laptop
    runs, and no stopped window occurred in the six re-run cells. Larger windows at 20 min and with the forecast plan
    are a second, non-separable cause.
- Not shown:
  - that 20 min is worse than 10 min;
  - that the forecast plan hurts on stress4h;
  - any ranking of 10 min, 20 min and the forecast plan;
  - any online price of recovery at the new prices.
- **Before the paper states a lookahead-20 or forecast-plan result**, re-run lookahead 10, lookahead 20 and the
  forecast plan, plus lookahead 0 on stress4h seeds 1 and 3. Use one machine with at most 4 Gurobi lanes on the 8
  physical cores, or a 120-180 s window limit. The estimate is about 2-3 h on the r7i.4xlarge: about 2-3 USD on demand,
  or under 1.5 USD on Spot.

### P2.4.2 Certified Manhattan siting (`r6_o2/RESULTS_final.md`)

**What is certified, per target and budget** (UB = best layout found):

| target | m | best layout found | UB | LB | bound gap % | certified | ILP st. |
|---|---|---|---|---|---|---|---|
| relaxed | 1 | 09 SC B3 C2 | 1,052.995 | 1,052.995 (enumeration) | 0.00 | **yes** | OOO |
| relaxed | 2 | 08 SC B3 C2 + 09 SC B3 C2 | 700.113 (<= 699.957 via the written 04 + 09 value) | 675.740 | 3.48 (3.46) | no | OOT (0.91 %) |
| relaxed | 3-4 | as m 2 | 700.113 (<= 693.807) | 675.740 | 3.48 (2.60) | no | OOT |
| written | 1 | 08 SC B3 C2 | 1,131.800 | 1,115.251 (enumeration) | 1.46 | no: site 09 open, in [1,115.25, 1,143.03] | OOO |
| written | 2 | 04 SC B2 C2 + 09 SC B4 C2 | 699.957 | 676.240 | 3.39 | no | OOO |
| written | 3-4 | 04 SC B4 C2 + 09 SC B4 C2 (105,200 USD; the m 3-4 budgets do not bind) | 693.807 | 676.240 | 2.53 | no | OOO |

More detail:
- At m 2-4 the lower bound sits only 0.91 (relaxed) and 1.41 USD (written) above the trivial two-site bound 674.83
  (mean superset LP 650.02 + cheapest two-site set-up 24.81).
- The brute-force check over the 17,340 two-site layouts at m 2 leaves 7,060 (relaxed) and 3,140 (written) open.
  m 3-4 was not checked (about 1.27 M and 53.7 M layouts).
- The relaxed step 2 never reached its integer phase: its LP phase took 3.7 h.
- Two-site layouts serve 98.3 % of the orders and single sites 74-78 %.
- Scenario CIs of V are wide, because demand variation is shared by all layouts; for example, written m 2 is 699.96
  [509.64, 890.28]. Only paired differences are informative.

**Rule layouts against the bound** (regret = V_rule - UB to V_rule - LB; paired difference against the best layout
found, n 3; selected rows):

| target | m | layout | V | st. | regret USD [lo, hi] | regret % | paired V_rule - V_best [CI] |
|---|---|---|---|---|---|---|---|
| relaxed | 1 | 09 (CSCD = CSTC) | 1,052.99 | OOO | [0, 0] | 0 | 0 (certified optimum) |
| relaxed | 1 | 08 (CSAV = present-day) | 1,070.07 | OOO | [17.08, 17.08] | 1.60 | 17.08 [-19.08, 53.23] |
| written | 1 | 09 (CSCD = CSTC) | 1,143.03 | TTT | [11.23, 27.78]; 0 against own bounds | 0.98-2.43 | 11.23 [-93.02, 115.47] (may be optimal) |
| written | 2 | 08 + 09 (CSCD = CSTC) | 706.26 | OOT | [6.30, 30.02] | 0.89-4.25 | 6.30 [-9.94, 22.55] |
| written | 2 | 08 + 14 (CSAV) | 752.74 | TTT | [52.78, 76.50] | 7.01-10.16 | 52.78 [-16.57, 122.13] |
| written | 2 | 03 B2 C1 + 08 B4 C3 (present-day) | 732.84 | TTT | [32.88, 56.60] | 4.49-7.72 | 32.88 [-9.00, 74.76] |
| written | 2 | 06 SC B4 C2 + 12 S B3 (round-5) | 802.43 | TTT | [102.47, 126.19]; 55.83 against own bounds | 12.77-15.73 | **102.47 [37.22, 167.72]** |
| relaxed | 2-4 | round-5 | 706.82 | TOT | [6.71, 31.08] | 0.95-4.40 | 6.71 [-11.92, 25.33] |
| written | 3 | 08 + 09 + 12 (CSTC) | 703.61 | OOO | [9.80, 27.37] | 1.39-3.89 | 9.80 [-5.06, 24.65] |
| written | 4 | 08 + 09 + 10 + 11 (CSCD) | 714.50 | OOO | [20.69, 38.26] | 2.90-5.35 | **20.69 [10.97, 30.41]** |
| written | 4 | 08 + 09 + 12 + 13 (CSTC) | 713.17 | OOO | [19.36, 36.93] | 2.71-5.18 | **19.36 [7.01, 31.71]** |
| written | 4 | 02 + 08 + 11 + 14 (CSAV) | 712.60 | OTO | [18.79, 36.36] | 2.64-5.10 | 18.79 [-6.41, 43.99] |

**Does siting beat rule siting at the new prices?** No significant advantage is shown at any budget.
- The best rule layout is within 0-2.6 % of the best layout found at every budget and target.
- By the bound, optimised siting can be at most the following better than the best rule layout:
  - 0 at relaxed m 1 and 1.46 % at written m 1;
  - 3.48 % (relaxed) and 4.25 % (written) at m 2;
  - 3.7-3.9 % at m 3;
  - 5.1 % at m 4.
- The paired advantage at written m 2 is 6.30 USD [-9.94, 22.55]; per scenario the gap is 0.85 % [-1.19, 2.90].
- The significant regrets come from over-building with four rule sites (19-21 USD, 2.7-2.9 %) and from the round-5
  layout's swap-only site under written targets.

**Follower dependence** (end-adjusted; gap relative to the follower's cost):
- On every evaluated layout the ILP is 35-44 % cheaper than r2 and 32-44 % cheaper than the selfish follower. Every CI
  is above zero.
- At the written best m 2 layout: r2 1,148.45 (gap 39.1 % [35.1, 43.1]); selfish 1,168.58 (selfish - ILP 468.63
  [379.97, 557.28]); served share 0.983 / 0.825 / 0.808.
- At CSCD m 2 (relaxed): r2 gap 44.4 % [33.6, 55.3]; legacy 42.0 % [31.5, 52.6].
- Rankings agree among the four cross-evaluated multi-site layouts. No ranking difference is significant at n 3.
- At one unit the written ILP prefers 08, while the relaxed ILP, r2 and the selfish follower prefer 09. None of these
  preferences is significant.
- Round-5 layout vs CSCD m 2:
  - under r2: round-5 cheaper by 1.65 % [-10.80, 14.10] (legacy 12.73 % [9.86, 15.61]);
  - under the selfish follower: 0.61 % [-12.20, 13.42] (legacy 5.69 %);
  - under the written ILP: round-5 dearer by 14.02 % [-27.78, -0.26] (legacy -3.99 % [-8.74, 0.77]).
- One selfish equilibrium did not converge: 08 + 09, scenario 2, the same cell as at the legacy prices. 17 of 18
  equilibria converged.
- Not shown: that the optimal layout depends on the follower.

**Price of recovery** (written minus relaxed ILP, n 3):
- Round-5 layout with a swap-only site: 95.61 USD [13.75, 177.47] (legacy 28.1).
- Single sites: 61.73 [-15.78, 139.24] (site 08; legacy 17.3) and 90.03 [56.37, 123.70] (site 09; an upper bound,
  written TTT).
- Multi-site layouts whose sites all have two chargers: -0.26 to 12.70 USD. CSCD m 2 costs 6.15 [-1.75, 14.05]
  (legacy 1.6), and only CSCD m 4 has a CI above zero (1.22 [0.81, 1.63]).
- The -0.26 at CSTC m 4 is a MIP-gap effect.
- The written best layouts (04 + 09) were priced under written targets only, so their price of recovery is unknown.

**Number of sites that pays** (written ILP):
- A second site lowers V from 1,131.80 to 699.96, by -431.8 USD [306.3, 557.4] (-38 %).
- A third or fourth rule site does not lower V (703.6-714.5).
- The best m 3-4 layout keeps two sites and adds spares. That this beats a third site (9.80 [-5.06, 24.65]) is
  suggested only.

**Computational story.**

| pass | LP method | one-site LP, median s (n timed) | two to four sites, median s (n) | ILP time | bounds |
|---|---|---|---|---|---|
| first | warm-started dual simplex; machine paging | 369: relaxed 388, written 282 (97) | 388 (18) | 3.9 h, 75 solves | LB None everywhere; post hoc from its pool: relaxed m 1 1,037.83 (1.44 %), written m 1 1,037.83 (8.35 %), m 2-4 674.83 (trivial) |
| second | cold barrier + crossover; envelope pruning; guaranteed master bound | 16 (10) | 28 (76) | 3.8 h, 32 solves (2.7 h in 8 escalations of sites 09 and 08) | finite at every budget; relaxed m 1 certified |

More detail:
- The first pass spent about 11 of its 19.3 h on one-site LPs and stopped at 50 (relaxed) and 45 (written) of the 90
  one-site layouts.
- Envelope pruning resolved 97 % of the one-site layouts without an LP.
- At m >= 2 there were 72 written integer-phase proposals. Each was LP-pruned after about 30 s, and each pruning
  closed essentially only that layout.
- The fixed-layout LP gap (Q_IP - Q_LP) / Q_IP is median 0.84 / 0.69 % and up to 14.39 %. Artificial columns are active
  in some bound LPs (up to 2.0 bikes). Bound validity is unaffected, but single-layout cuts are weak.
- The recommended strengthening (S1 / S2) is not implemented.
- The pass-to-pass bound-gap changes: relaxed m 2-4 3.61 -> 3.48 %; written m 2 4.45 -> 3.39 %; written m 3-4 4.09 ->
  2.53 %. The written gain comes mostly from the lower UB of the 04 + 09 layouts.

**Comparison with the legacy study (X6).**
- X6 used a truncated greedy search: four layouts priced, no layout at m 1, the open-sites library and the legacy
  prices. Its levels are not comparable one to one with the values here.
- What survives:
  - CSCD 08 + 09 stays within about 1 % of the best two-site layout;
  - a second site pays and further rule sites do not;
  - the ILP is 35-44 % cheaper than r2 on every layout;
  - rankings under r2 and the selfish follower cannot be told apart at n 3.
- What changes:
  - the round-5 layout is now the worst compared layout under written targets, because its swap-only site's recovery
    cost more than tripled;
  - its legacy r2 advantage of 12.7 % does not reproduce.

**What the paper may claim.**
1. A certified optimum for the one-unit relaxed problem, and certified bounds elsewhere (gaps 1.5-3.5 %).
2. Demand-proportional rule siting lies within the certified regret intervals and is not significantly worse than the
   best layouts found, so optimised siting adds at most a few percent.
3. The coordination gap on a given layout is an order of magnitude larger than the siting gap.
4. Swap-only sites carry a large recovery cost under written targets, and this decides the rank of the round-5 layout.

It may **not** claim any of the following:
- a certified optimal layout for m >= 2 (04 + 09 is "the best layout found, within 3.39 % of a certified lower bound");
- a significant siting advantage;
- follower-dependent optimal layouts;
- a Manhattan ILP-vs-best-rule gap. Only r2 and M4 were evaluated, not M2, M3 or M2+M3.

## P2.5 Rows of R6_DIGEST.md Section 7 that change

Rows are numbered as in `R6_DIGEST.md` Section 7. "Old (R6)" is the R6 digest value, or the paper's legacy value
where R6 had "rerun needed". Where part 1 already changed a row (for example row 8, stress4h gap 40.03 %), part 1's
value stands; the rows here do not overlap with part 1's.

### P2.5.1 Section 7.2, rolling horizon

| # | Quantity | Old (R6) | New | 95 % CI | n | Status (new) | Source |
|---|---|---|---|---|---|---|---|
| 32-42 | ILP status column, stress4h offline reference | 2 OPT + 3 TL (1.12 / 0.54 / 0.46 %) | 2 OPT + 3 TL (0.87 / 0.40 / 0.14 % after the 600 s re-solve; seed 1 incumbent 2.71 USD lower) | - | 5 | psweep P 60, last row | rolling_ext anomaly 6 |
| 33 | Share kept, ratio of means, stress4h | 0.53 (0.530) | 0.53 (0.529) | - | 5 | windows 120/120 OPT | rolling_ext T2 |
| 35 | Foresight, % of best rule, stress4h | 18.88 | **18.92** | [11.45, 26.38] | 5 | as row 33 | rolling_ext T2 |
| 37 | Foresight share, ratio of means, stress4h | 0.470 | 0.471 (= 1 - 0.529, derived) | - | 5 | as row 33 | rolling_ext T2 |
| 39 | Offline cost, stress4h (USD) | 942.01 [819.82, 1064.19] | **941.46** | [820.06, 1062.87] | 5 | 2 OPT + 3 TL (<= 0.87 %) | rolling_ext T1 |
| 40 | Seeds with rolling cheaper than the best rule | 14/15 (lambda 10) | lambda 10 14/15 (unchanged); lambda 0 **8/15**; lambda 20 11/15; forecast plan 13/15 (legacy 14, 15, 15) | - | 15 each | 12 of the 45 new runs (lambda 0, 20, forecast) contain a window stopped at 60 s | rolling_ext 3.1 |
| 43 | Online runs with the terminal fallback; bikes breaking (9) | 12/15 (lambda 10 only); 1.20 / 1.00 bikes | **41/60** over all lookaheads (lambda 0 12/15, 10 12/15, 20 7/15, forecast 10/15; legacy 47/60); bikes per run 1.5 / 1.2 / 0.6 / 0.9 (usd4h), 1.8 / 1.0 / 1.0 / 0.8 (stress4h); `C_dummy_terminal` 0 in every row | - | 60 | - | rolling_ext T11 |
| 44a | Share kept, mean of ratios, lambda 0 / 20 / forecast, usd4h | 0.43 / 0.81 / 0.68 (legacy); rerun needed | **-0.33 / 0.35 / 0.11** | [-0.86, 0.21] / [-0.06, 0.77] / [-0.82, 1.04] | 10 | windows: lambda 0 80/80 OPT; lambda 20 76/80 (4 TL, seeds 3, 5, 7); forecast 80/80 OPT | rolling_ext T2 |
| 44b | Same, stress4h | 0.63 / 0.76 / 0.79 (legacy) | **0.12 / 0.29 / 0.48** | [-0.12, 0.37] / [-0.26, 0.85] / [0.33, 0.63] | 5 | windows: lambda 0 38/40 OPT; lambda 20 35/40; forecast 37/40 | rolling_ext T2 |
| 44c | Share kept, ratio of means, lambda 0 / 20 / forecast | usd4h 0.57 / 0.85 / 0.76; stress4h 0.64 / 0.78 / 0.81 (legacy) | usd4h **-0.14 / 0.42 / 0.43**; stress4h **0.15 / 0.37 / 0.47** | - | 10 / 5 | as rows 44a-b | rolling_ext T2 |
| 44d | Online coordination, % of best rule, lambda 0 / 20 / forecast | usd4h 14.93 / 23.65 / 20.91; stress4h 25.31 / 30.73 / 32.00 (legacy) | usd4h -4.81 / 11.34 / 10.29; stress4h 5.39 / 13.05 / 18.97 | usd4h [-14.85, 5.22] / [-0.61, 23.30] / [-3.72, 24.29]; stress4h [-3.97, 14.75] / [-8.16, 34.27] / [13.86, 24.08] | 10 / 5 | as rows 44a-b | rolling_ext T2 |
| 44e | Foresight, % of best rule, lambda 0 / 20 / forecast | usd4h 13.34 / 4.63 / 7.36; stress4h 14.66 / 9.23 / 7.96 (legacy) | usd4h 32.16 / 16.00 / 17.06; stress4h 34.64 / 26.98 / 21.06 | usd4h [23.80, 40.51] / [5.02, 26.98] / [7.58, 26.54]; stress4h [28.84, 40.44] / [10.34, 43.62] / [13.03, 29.08] | 10 / 5 | as rows 44a-b | rolling_ext T2 |
| 44f | Contrast lambda 0 -> 10 (USD) | 41.31 [22.62, 60.00], p 0.0007 / 83.87 [48.77, 118.98], p 0.003 (legacy) | **133.15** (+10/-0, t p 0.001) / **241.90** (+5/-0, t p < 0.001) | [71.59, 194.70] / [187.65, 296.14] | 10 / 5 | usd4h all 160 windows OPT; stress4h 2 poor lambda 0 windows (clean seeds 221.94 [108.45, 335.42]) | rolling_ext T3, T10 |
| 44g | Contrast lambda 10 -> 20 (USD) | 28.54 [2.17, 54.90], 7/10 / -4.36 [-59.58, 50.85] (legacy) | **0.20** (+6/-4, t p 0.996) / **-102.02** (+2/-3, t p 0.24); not detectable, confounded | [-84.43, 84.83] / [-306.17, 102.13] | 10 / 5 | 7 of 15 lambda 20 runs have a TL window; clean seeds +66.30 [22.62, 109.98] (n 7) and +30.23 [11.22, 49.24] (n 2), post hoc | rolling_ext T3, T10 |
| 44h | Contrast plain rolling -> forecast plan (USD) | 6.75 [-8.32, 21.83] / 9.71 [-8.95, 28.36] (legacy) | **3.00** (+5/-5, t p 0.93) / **-41.55** (+3/-2, t p 0.46) | [-69.30, 75.29] / [-182.07, 98.98] | 10 / 5 | usd4h all windows OPT; stress4h 3 of 5 runs with a TL window; clean seeds +40.37 [-4.81, 85.55] (n 3) | rolling_ext T3, T10 |
| 44i | Cost monotone in the lookahead (seeds) | 6/10 and 3/5 (legacy) | 6/10 and 2/5 | - | 10 / 5 | - | rolling_ext T3 |
| 44j | Served share, lambda 0 / 20 / forecast vs best rule | legacy 81.4 / 89.2 / 86.7 vs 91.9; 63.7 / 70.4 / 73.8 vs 75.4 | usd4h 86.7 / 93.9 / 94.2 vs 92.5 %; stress4h 70.8 / 76.7 / 80.0 vs 75.4 %; lambda 0 - best rule usd4h -5.8 pp (t p 0.027) | lambda 0 - best rule [-10.8, -0.8] | 10 / 5 | as rows 44a-b | rolling_ext T4 |
| 44k | Lateness, lambda 0 / 20 / forecast (order-min per window) | legacy 15.0 / 4.0 / 6.5; 16.0 / 4.0 / 6.0 | usd4h 120.0 / 113.0 / 107.5 (best rule 215.0); stress4h 158.0 / 124.0 / 160.0 (456.0) | usd4h [63.5, 176.5] / [49.1, 176.9] / [50.7, 164.3] | 10 / 5 | as rows 44a-b | rolling_ext T4 |

**R6_DIGEST Section 2, "not re-run" bullet** ("the rolling-horizon runs at lambda 0 and 20, the forecast battery plan
and the written-target online runs"). Only the written-target online runs remain.

### P2.5.2 Sections 7.1 and 7.5, Manhattan rows

| # | Quantity | Old (R6) | New | 95 % CI | n | Status (new) | Source |
|---|---|---|---|---|---|---|---|
| 14 | Gap, Manhattan bi-level / seven layouts | 31.8 / 34.3 % (legacy); rerun needed | **best-rule gap not computable** (M2, M3, M2+M3 not evaluated). ILP vs r2 only: 39.1 % at the best two-unit layout (written), 44.4 % at CSCD 08 + 09 (relaxed); 35-44 % over the evaluated layouts | [35.1, 43.1] / [33.6, 55.3] | 3 scenarios | best m 2 written OOO; CSCD m 2 relaxed OOT (0.91 %) | siting 3.4 |
| 77a | Price of decentralisation (selfish - ILP, written) | 354.3 [276.7, 432.0] at the round-5 layout (legacy) | **468.6** at the best two-unit layout (04 + 09); 446.4 at the round-5 layout (lower bound; the ILP is TTT) | [380.0, 557.3]; [191.9, 701.0] | 3 | 04 + 09 OOO; round-5 TTT (2.88-8.49 %) | siting 3.4; agrees with Part 3 |
| 77b | Round-5 layout cheaper than the rule-sited layout under r2 | 12.73 % [9.86, 15.61] (legacy) | **1.65 %** (vs CSCD 08 + 09; CSAV not evaluated under r2) | [-10.80, 14.10] | 3 | POLICY | siting 4 |
| 77c | Same, selfish follower | 5.69 % [-4.90, 16.28] (legacy) | 0.61 % | [-12.20, 13.42] | 3 | 17 of 18 equilibria converged | siting 4 |
| 77d | Round-5 layout vs CSCD m 2, written ILP, paired gap | -3.99 % [-8.74, 0.77] (legacy) | **-14.02 %** (round-5 dearer in 3/3 scenarios); +102.47 USD against the best layout found | [-27.78, -0.26]; [37.22, 167.72] | 3 | TTT vs OOT | siting 4, Table 2 |
| 77e | Selfish equilibria converged | 82 of 84 (legacy) | 17 of 18 (unconverged: 08 + 09 scenario 2, as at the legacy prices) | - | 18 | - | siting 2 |
| 77f | Compliance (36.0 %) | rerun needed | see Part 3 (49.4 % at psi 0.5 on 04 + 09) | - | - | - | Part 3 |

New Manhattan quantities with no R6 row (append them to Section 7.5 as rows 88-92):

| # | Quantity | Old (legacy, X6) | New | 95 % CI | n | Status | Source |
|---|---|---|---|---|---|---|---|
| 88 | Certified value V*_m (USD per window) | no bound | relaxed m 1 **= 1,052.995** (certified); written m 1 in [1,115.25, 1,131.80]; m 2 in [676.24, 699.96] (relaxed [675.74, 699.96]); m 3-4 in [676.24, 693.81] (relaxed [675.74, 693.81]) | - | 3 | m 1 relaxed OOO; m >= 2 not certified | siting 3.1, 5 |
| 89 | Best two-unit layout found | CSCD 08 + 09, 676.6 (best of four priced) | 04 SC B2 C2 + 09 SC B4 C2, 699.96 (written) | [509.64, 890.28] | 3 | OOO | siting 3.1 |
| 90 | Rule-siting regret at m 2 (written, CSCD) | - | +6.30 USD (0.89 %); at most 30.02 USD (4.25 %) by the bound | [-9.94, 22.55] | 3 | OOT | siting 3.2 |
| 91 | Price of recovery, Manhattan: round-5 / CSCD m 2 / site 08 / present-day | 28.1 / 1.6 / 17.3 / 38.6 | 95.61 / 6.15 / 61.73 / 18.47 (m 2, capacity-matched anew) | [13.75, 177.47] / [-1.75, 14.05] / [-15.78, 139.24] / [-2.70, 39.64] | 3 | written TTT / OOT / OOO / TTT | siting 3.5 |
| 92 | Second site, written ILP | 795.4 -> 676.6 | 1,131.80 -> 699.96, -431.8 USD (-38 %) | [306.3, 557.4] USD | 3 | OOO / OOO | siting 4 |

**Highlights bullet 5** (R6: "not re-run (Manhattan)"). Suggested wording, this digest's own (81 characters): "Rule
siting is within 5 % of a certified bound; coordinating riders saves 32-44 %".

## P2.6 PENDING_R6.md items

### P2.6.1 Resolved or replaced by part 2

**Item 10, rolling horizon (lookahead 0 and 20 min, forecast plan, written-target online runs): replaced in part.**
Lookahead 0 and 20 min and the forecast plan now exist at the calibrated prices, with relaxed targets. The
written-target online runs stay legacy. The lookahead-20 and forecast-plan statements must carry the time-limit caveat
until the clean re-run (P2.4.1) exists. Replacement statements (rolling_ext Section 8):
1. **Section 6.4, paragraph 1** (`sections/06_results.tex` l. 106). This replaces the legacy lookahead sentence and
   the 28.5 USD (2.2-54.9, 7 of 10 seeds) contrast. "At the calibrated prices, moving the lookahead from 0 to 10 min
   lowered the cost on every seed, by 133.2 USD per window (71.6-194.7) on usd4h ($n=10$, paired $t$-test $p=0.001$)
   and by 241.9 USD (187.7-296.1) on stress4h ($n=5$, $p<0.001$). Without lookahead the rolling coordinator was not
   cheaper than the best rule on average (online coordination $-4.8$ % of the best-rule cost, $-14.9$ to 5.2, cheaper
   on 4 of 10 usd4h seeds; 5.4 %, $-4.0$ to 14.8, on 4 of 5 stress4h seeds), and foresight exceeded online coordination
   on 14 of 15 instances. Neither a 20-min lookahead nor the forecast battery plan had a detectable value against
   10 min (20 min: 0.2 USD, $-84.4$ to 84.8, and $-102.0$, $-306.2$ to 102.1; forecast plan: 3.0, $-69.3$ to 75.3, and
   $-41.6$, $-182.1$ to 99.0); 14 of the 360 window solves of these runs stopped at the 60 s limit, 11 with MIP gaps of
   27-102 %, and every seed on which 20 min was more than 20 USD costlier than 10 min, and every stress4h seed on which
   the forecast plan was costlier, contains such a window (Section S7.1)."
2. **Table tab:res:rolling(a).** Replace the legacy share-kept block with calibrated-price rows. Each cell is the
   mean of ratios [CI]; ratio of means, given for usd4h | stress4h:
   - lookahead 0: $-0.33$ [$-0.86$, 0.21]; $-0.14$ | 0.12 [$-0.12$, 0.37]; 0.15;
   - lookahead 10: 0.29 [$-0.19$, 0.77]; 0.42 | 0.53 [0.34, 0.71]; 0.53;
   - lookahead 20: 0.35 [$-0.06$, 0.77]; 0.42 | 0.29 [$-0.26$, 0.85]; 0.37;
   - forecast plan: 0.11 [$-0.82$, 1.04]; 0.43 | 0.48 [0.33, 0.63]; 0.47.

   Footnote: "12 of the 45 runs at lookahead 0 and 20 and with the forecast plan contain a window stopped at the 60 s
   limit". The legacy rows (0.43 / 0.64 / 0.81 / 0.68 and 0.63 / 0.77 / 0.76 / 0.79) move to S7 as the sensitivity
   case.
3. **Section S7.1, paragraph "Lookahead and forecast plan"** (`supplement/s07_rolling_network.tex` l. 34-35): "At the
   calibrated prices the paired contrasts (USD per window, positive when the second policy is cheaper; usd4h and
   stress4h) are 133.2 (71.6-194.7) and 241.9 (187.7-296.1) for 0 against 10 min, 0.2 ($-84.4$ to 84.8) and $-102.0$
   ($-306.2$ to 102.1) for 10 against 20 min, and 3.0 ($-69.3$ to 75.3) and $-41.6$ ($-182.1$ to 99.0) for plain
   rolling against the forecast battery plan at 10 min. Without lookahead the coordinator is cheaper than the best rule
   on 8 of 15 instances, at 10 min on 14, at 20 min on 11 and with the forecast plan on 13. The cost decreases
   monotonically in the lookahead on 6 of 10 and 2 of 5 seeds. The runs at 0 and 20 min and with the forecast plan were
   solved on a shared server; 14 of their 360 window solves stopped at the 60 s limit (11 with MIP gaps of 27-102 %),
   all at 20 min, with the forecast plan or at 0 min on stress4h, against none of the 120 windows at 10 min and none of
   the 480 legacy windows. On the seeds without such a window the step from 10 to 20 min saves 66.3 USD (22.6-110.0;
   6 of 7 usd4h seeds; post hoc) and the forecast plan saves 40.4 USD ($-4.8$ to 85.6; 3 stress4h seeds); a clean re-run
   is needed before these steps can be ranked. In 41 of the 60 calibrated-price online runs the terminal fallback was
   needed, with 0.6-1.8 bikes per run (means by policy) without the certificate (9). At the legacy prices the contrasts
   were 41.3 (22.6-60.0) and 83.9 (48.8-119.0), 28.5 (2.2-54.9) and $-4.4$ ($-59.6$ to 50.9), and 6.8 ($-8.3$ to 21.8)
   and 9.7 ($-9.0$ to 28.4)."
4. **Figure fig:res:rolling-cost (S7).** Replace it with
   `outputs/r6_fill/rolling_ext/figs/fig_rolling_ext_cost_by_method.pdf`, with the caption in rolling_ext Section 6.
   `fig_rolling_ext_share_kept.pdf` can replace the legacy block of Table 2(a), and `fig_rolling_ext_contrasts.pdf`
   belongs in S7.1.
5. **Section 4.4, last paragraph** (`sections/04_methods.tex` l. 78). Replace "lookaheads of 0 and 20 min, a forecast
   battery plan with one sampled scenario per epoch and partial written-target runs were run at the legacy prices
   only" with "lookaheads of 0 and 20 min and a forecast battery plan with one sampled scenario per epoch were run at
   both price sets; partial written-target runs exist at the legacy prices only".
6. **S2 "Settings and coverage"; S7 l. 12.** Replace "Lookahead $\lambda$: 10 min (0 and 20 min at the legacy prices
   only)" with "0, 10 and 20 min". In S7 l. 12, delete "the lookahead-0 and -20 runs and the forecast battery plan
   exist at the legacy prices only".
7. **Table S12 status rows** (`supplement/s12_status_recovery.tex` l. 28). Add: "Rolling horizon, lookahead 0 and
   20 min and forecast plan, calibrated: 45 runs, 360 windows: 346 optimal, 14 at the 60 s limit (11 with MIP gaps of
   27-102 %); unpriced terminal fallback in 29 of 45 runs; 6 runs first skipped by the wall budget and re-run".
8. **Section 7 (discussion, l. 30).** Remove "the lookahead curve" from the list of legacy-only experiments.
9. **Optional, Sections 1 and 8 (RQ2).** After "kept at most about half of the offline gap", add "and without
   lookahead it was not cheaper than the best rule on average".

**Item 2, Manhattan siting: replaced, except the pieces listed under P2.6.3.** Replacement statements (siting
Section 7; one correction marked):
1. **Settings paragraph (4.5; S2 "Settings of the siting experiments").** "The Manhattan study uses the family
   manhattan at the calibrated prices: 15 candidate sites with 14 size options each (swap-only with 1-4 spares,
   charge-only hub with 2 or 4 chargers, co-located with 1-4 spares and 1-2 chargers), budgets of m = 1-4 units of
   52,150 USD, three demand scenarios and the ILP follower with an all-candidates repositioning library. A Benders
   scheme bounds the optimal value V*_m from below (safe Lagrangian cuts of the LP relaxation, integer L-shaped and
   lifted cuts, and a pruned enumeration of the 90 one-unit layouts) against the best layout found; a budget is
   certified when the gap is at most max(0.25 %, 1 USD)."
2. **Section 6.8, Table tab:res:siting, Figure fig:res:siting.** Replace these with siting Tables 1-3 and
   `outputs/r6_o2/figs/fig_siting_bounds.pdf`. Text: "With relaxed targets one co-located site at 09 (three spares,
   two chargers) is the certified one-unit optimum (1,053.0 USD per window), and it is also the CSCD and CSTC rule
   layout. With the written targets the one-unit optimum is site 08 (1,131.8 USD) or site 09, whose value lies between
   1,115.3 and 1,143.0 USD (bound gap 1.46 %). At two to four units no budget is certified: the best layouts found,
   two co-located sites at 04 and 09 (699.96 USD at two units; 693.81 USD with four spares at each site at three and
   four units), lie within 2.5-3.5 % of the lower bound."
3. **Rule comparison (6.8, 7.2).** "Demand-proportional rule siting is not significantly worse than the best layouts
   found: at two units the CSCD layout (08 and 09) costs 6.3 USD per window more (0.89 %; 95 % CI -9.9 to 22.6 USD;
   n = 3) and at most 30.0 USD (4.25 %) more than any layout can cost; the four-site CSCD and CSTC layouts cost 20.7
   and 19.4 USD more (2.90 and 2.71 %, CIs 11.0-30.4 and 7.0-31.7 USD) because the budget buys sites instead of spares.
   The round-5 bi-level layout (06 and a swap-only site at 12) costs 102.5 USD more (12.8 %; 37.2-167.7 USD) under
   written targets and ties on relaxed targets (+6.7 USD, -11.9 to 25.3)."
4. **Followers (6.8 paragraph on r2 and the selfish follower; 7.2 "layout rankings ... depend on how riders are
   operated").** "On every evaluated layout the ILP is 35-44 % cheaper than rule r2 and 32-44 % cheaper than the
   selfish follower (at the best two-unit layout 39.1 %, 35.1-43.1, against r2), and there the served share falls from
   0.98 to 0.83 under r2 and 0.81 under the selfish follower. The layout ranking under r2 and the selfish follower
   agrees with the ILP's among the multi-site layouts, and no ranking difference is significant at n = 3; the round-5
   layout is no longer cheaper than the rule layout under r2 (1.65 %, -10.8 to 14.1)." This replaces the 12.73 % and
   5.69 % sentences.
5. **Price of recovery (6.8 sentence; Manhattan row of Table tab:app:recovery).** "Recovery costs 95.6 USD per window
   (13.8-177.5) at the round-5 layout with its swap-only site, 62-90 USD at single sites and -0.3 to 12.7 USD (6.2 USD
   at the CSCD two-site layout) on multi-site layouts whose sites all have two chargers". This replaces 28.1 / 1.6 /
   0.7-1.6 / 28.1-61.1 USD.
6. **"Number of cabinets that pays" (7.2).** Corrected from the report's "(-38 %; 25-51 %)", whose percentage
   interval is not in its tables: "Under the ILP with written targets a second site lowers V from 1,131.8 to 700.0 USD
   per window (by 431.8 USD, 306.3-557.4, or 38 %), a third or fourth rule site does not, and the best three-unit
   layout keeps two sites and adds spares."
7. **7.3 and future work** (siting searches incomplete; "Ranking optimised against rule siting requires a complete
   bi-level search"). "The siting bound is certified for one unit with relaxed targets only; at two to four units the
   bound rests on single-layout LP cuts and is barely above the trivial bound, so a certificate needs stronger cuts or
   a decomposition over sites."
8. **Abstract last sentence, highlights bullet 5, introduction findings paragraph, Section 8 RQ4.** "Optimised siting,
   bounded by a certificate, improves on demand-proportional rule siting by at most a few percent (0-2.6 % at the
   layouts found; by the bound at most 1.5 % at one unit and 3.5-5.1 % at two to four units), whereas coordinating the
   riders on a given layout is 32-44 % cheaper than rule r2 or selfish station choice." For the highlights bullet see
   P2.5.2 (84-character limit).
9. **Table S4 settings row** (`supplement/s04_costs_parameters.tex` l. 133). Part 3 splits this row and leaves the
   siting row "legacy". With item 2 replaced, set the siting row to: "Manhattan siting (\mref{sec:results:siting}) &
   \texttt{manhattan}, budgets $m=1,\dots,4$; certified bound & scenarios 0--2 (3) & 300~s (600~s with a hub;
   escalations 900 and 1,800~s) & calibrated \\".
10. **Figure captions.** `fig_siting_passes.pdf` (first vs second pass) and `fig_siting_followers.pdf` (followers and
    price of recovery) are suggested for S10, with the captions of siting Section 6.

**Item 15, coverage and recovery tables: Manhattan and rolling rows replaced.**
- Manhattan (tab:app:coverage-legacy -> calibrated coverage): "ILP solves 75 + 32 (first and second pass): OPTIMAL 70,
  TIME_LIMIT 32 (MIP gaps 0.09-45.35 %, the 45.35 % row re-solved to optimality), bound-stopped 5; 18 distinct selfish
  equilibria, 17 converged; wall 19.3 + 10.7 h". Also the Manhattan price-of-recovery row (item 2, statement 5).
- Rolling (Table tab:app:online, `supplement/s04_costs_parameters.tex` l. 123-124, 228): the row "lookahead 0 and
  20 min; forecast battery plan" becomes calibrated (seeds 0-9 and 0-4, 60 s per window). The written-target row stays
  legacy.
- Still open under item 15: the rows of items 3 and 11, and the written-target online row.

**Item 16 (related), cells reported with best-known or bound-based statements.** Part 1 resolved item 16 except the
fleet K 10 / B 2 seed-2 cell. Part 2 adds one replacement. The stress4h offline-reference gap list quoted in 6.4 / S7
changes from "1.12 / 0.54 / 0.46 %" to "0.87 / 0.40 / 0.14 % (600 s; seed 1 incumbent 2.71 USD lower)". The
lookahead-10 stress4h values then read: offline gap 40.03 %, foresight 18.92 %, ratio of means 0.529; the share kept
stays 0.53.

**Item 4 (selfish equilibrium, price of decentralisation, compliance).** Part 3 resolves this item. Part 2 agrees with
its values: 468.6 [380.0, 557.3] at 04 + 09; 446.4 [191.9, 701.0] at 06 + 12; r2 - ILP 448.5 / 436.1. Once item 2 is
replaced as above, four pieces of Part 3 change. The wording below is this digest's own.
- **Condition (b) and the interim 7.2 sentence of Part 3** ("Item 2 (Manhattan siting): not replaced") are superseded.
  The siting search is introduced by item-2 statements 1-2, and the layout ranking by statement 3.
- **Part 3, R1, last sentence.** Replace "and on the other layouts of the siting study it ranged from 263.6~USD at the
  four-site CSCD layout, whose interval includes zero, to 550.0~USD at a single site at 08" with "and on the other
  layouts evaluated at the calibrated prices it ranges from 343.2~USD (sites 08, 09 and 12; 56.1--630.3) to
  741.3~USD at a single site at 08 (655.7--827.0)". The source is siting Table 4, selfish minus the written-target
  ILP. The four-spare 04 + 09 layout, 346.7 (-15.8 to 709.2), is the only one whose interval includes zero. Do not
  use the site-09 value 781.9: it is measured against the relaxed ILP.
- **Part 3, R2.** Replace "of the 84 equilibria of the siting study (legacy prices), 82 converged and the other two
  stopped at the cap and are approximate" with "of the 18 distinct selfish equilibria of the calibrated-price siting
  study, 17 converged; the other (sites 08 and 09, scenario 2) stopped at the cap of ten iterations, as at the legacy
  prices, and is approximate".
- **Part 3, Table S4 row split.** The siting row becomes calibrated (item 2, statement 9).

**Item 7 (price of recovery outside usd4h nominal): Manhattan part replaced.** The Manhattan row of Table
tab:app:recovery now has calibrated values (item 2, statement 5). The 7.2 swap-only sentence (0.30 to 24.28 USD) is the
usd4h transfer experiment, which part 1 covered. The Manhattan swap-only value (95.6 USD) is supporting evidence only.
The rest of item 7 is still open (part 1, 6.3).

### P2.6.2 R6_DIGEST changes

Apply the rows of P2.5 and the Section 2 bullet change. R6 Section 7.5 row 77 is then fully replaced, with transfers
from part 1, compliance from Part 3, and decentralisation and siting from here.

### P2.6.3 Still open after part 2

| Item | Status | Waiting for |
|---|---|---|
| 2, map | labelled | redraw fig:res:map with the new sites: 09 (relaxed) and 08 (written) at one unit; 04 + 09 at two to four units |
| 2, siting levers | labelled | the marginal levers at the chosen layout (fig:app:siting-levers), not re-run |
| 2, policy-aware siting (F) | labelled | not re-run at the new prices |
| 2, Manhattan block of tab:res:headline and the 31.8 / 34.3 % sentence in 6.2 | labelled | M2, M3 and M2+M3 on the Manhattan layouts (only r2 is available: 36-44 %) |
| 2, certificate at m >= 2 | open (method) | stronger cuts (S1 / S2) or a decomposition over sites; until then "best layout found, within 2.5-3.5 % of a certified bound" |
| 3, earlier Midtown study | labelled | optional re-run. The `midtown_validate` run is a certifier test, not a re-run |
| 10, written-target online runs and online price of recovery | labelled | not part of rolling_ext |
| 10, lookahead 20 and forecast plan, clean values | caveated | re-run on one machine with at most 4 lanes, or with a 120-180 s window limit (about 2-3 h, at most about 3 USD) |
| 15 (rest) | labelled | items 3, 11; the written-target online row |
| 5, 7 (rest), 8 (rest), 11, 12, 16 (fleet K 10 / B 2), 18, 20 (rest) | as in part 1, 6.3 | unchanged by part 2 |
| 4 | resolved by Part 3 | the four Part 3 updates above |

## P2.7 Caveats

1. **Poor windows confound two of the three rolling contrasts.** 14 of 360 window solves stopped at 60 s, 11 with
   MIP gaps of 27-102 %. They explain every 10 -> 20 loss above 20 USD and both stress4h forecast-plan losses. Do not
   report a 10 vs 20 ranking or a stress4h forecast-plan effect. The post-hoc clean-seed subsets are chosen after the
   fact and may be biased, because harder instances both stop at 60 s and gain less from lookahead.
2. **Machine and load differ between lookahead 10 and the other policies.** Lookahead 10 ran on the laptop; the
   others ran on a shared server with 15 threads on 8 physical cores. The window limit is wall-clock time. Every
   contrast against 10 min compares a laptop run with a server run. Where all windows are OPT, this affects only the
   choice among tied optima.
3. **The online values are upper bounds.** The unpriced terminal fallback is used in 41/60 runs and is uneven across
   policies (7/15 at 20 min against 12/15 at 10 min).
4. **usd4h seed 0 dominates the usd4h means of ratios** (per-seed shares -1.99 / -1.51 / -0.29 / -3.50). Prefer the
   ratios of means and medians. Without seed 0 the forecast-plan share is 0.51 [0.27, 0.75] instead of 0.11.
5. **The rolling policy does not adapt reliably to the prices.** Repriced legacy online schedules would be cheaper
   than the new-price runs on 7/10 usd4h seeds at lookahead 0 and 6/10 at 20 min. Part of the measured foresight is
   therefore a property of the myopic policy, not only of missing information.
6. **`check_ok` is False on all 45 rolling rows by design.** The relaxed runs are also checked against (9), (17) and
   (18). `hard_ok` and identity (24) pass on every row.
7. **No siting certificate at two to four units.** 18-41 % of the two-site layouts remain open, and m 3-4 was not
   checked. "Best layout found" is the only valid wording. The relaxed UB at m 2-4 in `manhattan_pass2/RESULTS.md` is
   stale (use 699.957 / 693.807).
8. **The written m 1 optimum is undecided between 08 and 09.** The open layout is a rule layout, so the rule regret at
   written m 1 may be zero.
9. **Small n and wide CIs on Manhattan.** There are three scenarios (t 4.303), and V CIs span 350-380 USD at two
   sites. Only paired differences are informative. Several rule-layout values are time-limited incumbents: the
   round-5 written MIP gaps are 2.88-8.49 %, and CSAV / present-day m 2 written are TTT. The report gives lower regret
   ends against their own MIP bounds as well.
10. **Library and price dependence.** Values use the all-candidates library and the new prices. They are not
    comparable one to one with the legacy X6 values. Certificates hold for these three scenarios only.
11. **Follower evaluation is incomplete.** Only r2 and the selfish follower ran on the Manhattan layouts. The
    Manhattan best-rule gap and the Table 1 Manhattan block cannot be filled. One selfish equilibrium (CSCD m 2,
    scenario 2) is unconverged.
12. **Weak bound LPs.** The fixed-layout LP gap is up to 14.39 %, and artificial columns (up to 2.0 bikes) are active
    in some LPs. Validity is unaffected, but the cuts are weak.
13. **Ordering and scope of this file.** Part 3 (compliance) precedes this part in the file because it was appended
    first. The part-1 header's "follow in part 2" refers to rolling_ext and siting here, and to compliance in Part 3.
    The task brief describes compliance as still running. Its server run had in fact finished (Part 3: 14:52:40
    server clock), and its report is covered by Part 3, not by this part.
14. **Mixed clocks; this part is not refuter-checked.** Server and laptop clocks are mixed (server records are about
    4 h ahead of local EDT). The stage reports passed their refuter step with no refutation. This part's own wordings
    have not been through a refuter pass: the highlights sentence, the corrected cabinets sentence, and the Part 3
    updates (R1 range 343.2-741.3 USD, R2 count 17 of 18, the Table S4 row). Every number in them comes from the two
    reports.

## P2.8 Sources

- `outputs/r6_fill/rolling_ext/RESULTS_final.md` (script `figs/make_rolling_ext_final.py`; tables
  `figs/tables_auto.md`, `figs/rolling_ext_final_tables.json`, `figs/rolling_ext_final_per_instance.csv`; figures
  `figs/fig_rolling_ext_{cost_by_method,share_kept,contrasts}.{pdf,png}`)
- `outputs/r6_fill/rolling_ext/{records.jsonl, per_instance.csv, summary.csv, RESULTS.md}`;
  `outputs/r6_penalty/rolling/records.jsonl`; `outputs/r6_penalty/headline/`, `outputs/r6_penalty/psweep/`;
  `outputs/r5_x3_rolling/RESULTS_final.md`
- `outputs/r6_o2/RESULTS_final.md` (script `outputs/r6_o2/figs/siting_report.py`; tables `figs/siting_tables.txt`;
  figures `figs/fig_siting_{bounds,passes,followers}.{pdf,png}`)
- `outputs/r6_o2/{manhattan, manhattan_bound, manhattan_pass2, manhattan_pass2_bound}/`, `outputs/r6_o2/manhattan_pass2.log`,
  `manhattan_pass2_step2.log`; `notes/o2_siting_bound_design.md`, `notes/o2_manhattan_first_pass.md`,
  `notes/DECISIONS.md` (O2); `outputs/r5_x6_manhattan/RESULTS_final.md`
- `outputs/R6_DIGEST.md` (Section 7 row numbers, Section 2), `manuscript/PENDING_R6.md` (item numbers), Part 3 of this
  file (compliance)
