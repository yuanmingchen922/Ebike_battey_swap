# Round 6 digest: the main experiments at the recalibrated order prices

Date: 2026-10-18. Round 6 (R6) re-ran the main experiments of round 5 with new order prices: unserved penalty
P = 60 USD (was 30), response price w = 18 USD/h from release (unchanged) and lateness price v = 15 USD/h from the
promise (was 36). Below, "new prices" means (P 60, v 15) and "old prices" means (P 30, v 36). The prices come from a
verified web study (`notes/penalty_calibration.md`); the implementation is described in `notes/DECISIONS.md`
("R6 implementation notes") and the code is in `experiments/r6_penalty.py`.

**Inputs.** This digest uses the eight corrected stage reports
`outputs/r6_penalty/<stage>/RESULTS_final.md` (stages headline, psweep, vsweep, network, rolling, levers, fleet, rl),
their "Verification corrections (R6)" sections, the round-5 reference reports (`R5_DIGEST.md`,
`r5_x*/RESULTS_final.md`) and the manuscript (`manuscript/main.tex`, `highlights.tex`, `sections/*.tex`). Every number
comes from these reports or was recomputed from the stage `records.jsonl` files without any solve. The numbers
recomputed for this digest are marked **[rec]**. Their check: the same script reproduces the paper's old-price value
exactly (13.3 → 0.4 and 14.7 → 0.8 late orders, 0.39 / 0.42 km of detour, 0.92 → 0.74 and 0.86 → 0.53 no-wait swap
share, and M4 − best rule 45.03 / 42.69 USD).

**Conventions** (as in round 5). Aggregated E2 ILP, Gurobi Threads 3, Seed 0, eBaaS energy calibration. Headline =
relaxed end targets (rho 0, R_end 0) scored on the end-adjusted cost (total + C_end_adjust). Best rule = the
per-instance minimum over r2, M2 (`r5_range`) and M2+M3 (`r5`). Gap = 100 (best rule − ILP) / best rule per instance,
then averaged. Intervals are exact Student-t 95 % CIs over seeds, written `[lo, hi]` or `± half-width`. Differences are
paired by seed. Costs are in USD per 4-h window. Family names: usd4h, nyc4h, stress4h (code `r5_stress4h`),
stress4h-K8 (`r5_stress4h_k8`), nyc4h-stress (`nyc4h_stress2`).

---

## 1. Short answers

1. **The coordination gain survives the new prices.** The gap is positive on 40/40 headline instances: usd4h pooled
   25.10 % [20.15, 30.06] (n = 30), nominal demand 27.34 % [21.69, 32.99] and nyc4h at least 27.88 % [24.15, 31.61]
   (n = 10 each). It is statistically unchanged from round 5 except at usd4h x1.5 (−5.03 ± 3.08 points). That drop is
   a denominator effect: the USD saving is unchanged in every group.
2. **What the saving is made of has flipped.** Unserved orders are now 64.4 % of the pooled usd4h saving (old 22.8 %),
   and lateness is 19.0 % (old 50.5 %). Service terms still make up 99.8 % of the pooled saving **[rec]**.
3. **All five round-5 artefacts (a)-(e) disappear as artefacts.** Two behaviours remain and are now reported as real
   findings: on stress4h with M2+M3 riders PPO still collapses in service (a learning failure), and the rolling
   horizon keeps only about half of the offline gap (rolling item in Section 6).
4. **Several paper statements reverse:**
   - The swap network, not coordination, is now the larger lever on usd4h (Shapley 58.2 % network).
   - Rolling re-planning keeps about half of the gap (ratio of means 0.42 / 0.53), not 64-77 %.
   - Removing on-site charging costs the ILP +228.5 USD instead of +79.2 USD.
   - The cost-minimal ILP fleet serves 99 % instead of 70 % of orders.
   - PPO is never cheaper than the best rule.
5. **Recommendation: switch the main specification to the new prices** (Section 8). This needs a short list of
   re-solves first, and explicit disclosure of the experiments that were not re-run.

---

## 2. Coverage

All four R6 lanes exited 0 (`outputs/r6_lanes/lane_1..4.status`). No stage has SKIPPED_BUDGET or ERROR rows, and no
solve was budget-shortened. In every stage the demand hashes equal round 5, so every comparison below is paired on
identical instances.

| Stage | Families, n | Records | ILP status (relaxed unless stated) | Time limit | Wall time / budget |
|---|---|---|---|---|---|
| headline | usd4h x0.75 / x1 / x1.5, nyc4h; 10 seeds each | 290 (240 rule rows POLICY) | relaxed 37 OPT + 3 TL (usd4h x1.5 seeds 0, 5, 8; MIP gaps 1.07 / 0.33 / 0.91 %); written (usd4h x1 only) 10 OPT | 300 s | 68.1 / 150 min |
| psweep | usd4h x1, stress4h; P in {20, 30, 40, 60, 80} at v 15; 10 seeds | 400 | usd4h 49 OPT + 1 TL (P 80 seed 0, sleep-truncated); stress4h OPT 10 / 7 / 5 / 4 / 2 of 10 at P 20 / 30 / 40 / 60 / 80 (max MIP gap 1.12 % up to P 60, 11.63 % at P 80) | 300 s | 214 / 360 min |
| vsweep | usd4h x1; v in {8, 15, 25, 36} at P 60, plus the bridge (P 30, v 36); 10 seeds | 200 | 48 OPT + 2 TL (P 60 / v 36 seeds 5, 6: sleep-truncated, not real solves) | 300 s | 67.6 min clock (39.4 min process) / 90 min |
| network | usd4h x1 (n = 10), stress4h (n = 5); home vs network × best rule vs ILP | 165 | 27 OPT + 3 TL (stress4h network seeds 1, 2, 3; 1.12 / 0.31 / 0.43 %) | 300 s | 33.4 / 75 min |
| rolling | usd4h x1 (n = 10), stress4h (n = 5); lambda 10, relaxed only | 15 rolling runs, 120 windows | all 120 windows OPT; offline references: usd4h 10 OPT, stress4h 2 OPT + 3 TL (1.12 / 0.54 / 0.46 %); unpriced terminal fallback in 12/15 runs | 60 s per window | 16.2 / 45 min |
| levers | stress4h-K8, seeds 0-4; reference, no on-site charging, lock-out of 2 spares | 75 | reference 0 OPT + 5 TL (0.83-10.48 %); no on-site charging 4 OPT + 1 TL (0.72 %); lock-out 0 OPT + 5 TL (0.39-5.62 %) | 600 s | 129.3 / 270 min |
| fleet | stress4h, K in {4, 6, 8, 10} × B in {1, 2, 3, 4}, seeds 0-2 | 240 (48 cases) | 28 OPT + 20 TL (0.31-2.31 %, plus K 10 / B 2 seed 2 at 100.5 %) | 300 s (K 4, 6), 600 s (K 8, 10) | 158.0 / 380 min |
| rl | nyc4h-stress, stress4h; 10 test seeds; 4 PPO trainings (200,704 steps each) | 264 | nyc4h-stress 10 OPT; stress4h 5 OPT + 5 TL (0.32-1.12 %); no written ILP (by design) | 300 s (round 5: 120 s) | 119.4 / 270 min |

**Not re-run at the new prices.** These experiments still exist only at the old prices:
- the transfer and hub-separation experiment (X2);
- the Manhattan siting and compliance experiment (X6);
- the end-of-window boundary grid, the LP shadow prices of spares and chargers, stress4h-K10 and stress8h (X5 core);
- the pack-size axis of the fleet sweep;
- the rolling-horizon runs at lambda 0 and 20, the forecast battery plan and the written-target online runs;
- the legacy-specification waterfall (preliminary specification);
- the price of recovery outside usd4h x1;
- the levers "faster chargers", "second swap position" and "lock-out of 1 spare".

---

## 3. Verification outcome

Two independent refuters checked the claims of every stage report. Claims refuted by at least one refuter were
recomputed from the records and corrected in the stage `RESULTS_final.md`, in its "Verification corrections (R6)"
section.

| Stage | Refuted claims | Refuter verdicts | What was wrong | Numbers changed? |
|---|---|---|---|---|
| headline | C3 (rule schedules are price-independent) | refuter 1 no, refuter 2 yes (scope) | True on this stage only because M3 is inactive (no services); M2+M3 reads mean P_i through `baseline.stockout_value` where services exist | no |
| headline | C5 (lateness tail) | both (wording) | The 45-min ILP maximum is a TIME_LIMIT incumbent (usd4h x1.5 seed 8); the maximum on OPTIMAL rows is 35 min; the rule-row list omitted M2+M3 and the per-seed counts | no |
| network | C6 (gap on the network "does not change" with the prices) | both | Only "no detectable change": paired −0.93 [−5.79, 3.92] (usd4h, n = 10) and +0.03 [−3.65, 3.72] (stress4h, n = 5; 3 TL); CIs allow 4-6 point shifts; the stress4h USD value rose on 5/5 seeds | no |
| rolling | C3 (served-share reversal vs best rule) | both | The old-price deficits were not significant (−6.4 [−13.0, 0.2], −2.5 [−11.2, 6.2] pp). The robust change is rolling's own served share: +7.8 [1.0, 14.6] and +8.8 [4.5, 13.0] pp | no |
| levers | C2 (repricing tolerance and price independence) | both | The tolerance is 4.55e-13, not 2.3e-13; "price-independent" is too strong for M2+M3 (it reads mean P_i). The result −238.93 [−380.94, −96.91] (5/5) stands | no |
| fleet | C1 (cheapest ILP design) | refuter 1 yes, refuter 2 no (caveats) | The seed-mean argmin K 8 / B 3 is the lowest incumbent mean, not certified; the bounds certify only "6-8 bikes, 2-3 spares" | no |
| fleet | C6 (marginal values) | refuter 1 yes, refuter 2 no (numbers) | Solve status not disclosed; the fourth-spare value is certified on 10 of 12 pairs, not on K 4 seeds 0-1 | no |
| psweep, vsweep, rl | none | - | - | - |

All corrections concern wording, scope and disclosure of solve status. No number, table value or conclusion changed.
The fleet figures were regenerated (markers and annotations only), and the levers figure script gained a
`check_repricing()` check.

**Data problems found by the stage authors, independent of the refuters:**
- **Laptop sleep (13:13-13:42 local time).** It cut ILP solves short across lanes, because Gurobi counts wall-clock
  time. Affected rows:
  - psweep usd4h P 80 seed 0: recorded cell gap 0 %; best-known 10.98 %.
  - psweep stress4h P 40 seed 9: 1.51 USD worse than the repriced P 30 schedule.
  - vsweep P 60 / v 36 seeds 5 and 6: the rows hold the rule MIP start; the auto `RESULTS.md` v 36 row is wrong.
  - fleet stress4h seed 2: two `ILP_tl600` rows (K 10 / B 1 ran 991 s against a 600 s limit).

  The resume logic does not flag these rows, because the time limit used equals the one requested. The final reports
  use best-known (repriced) schedules or exclude these cells. Suggested guard: treat `runtime_s > wall_s + 10` as not
  done, and run lanes under `caffeinate -i`.
- **fleet K 10 / B 2, seed 2.** The solve stopped with a 100.5 % MIP gap. Its incumbent is at least 65.7 USD too high
  (nesting argument). It does not change the cost-minimal design.
- **levers reference.** Three reference incumbents are provably suboptimal: the lock-out, a pure restriction, has
  lower incumbents on seeds 0, 2 and 4.
- **Auto-generated `RESULTS.md` files.** They are numerically correct but report "Anomalies: none" (network, rolling,
  levers, fleet). Their `ilp_max_lateness_min` columns are means of per-seed maxima, and some columns are in USD where
  counts are implied. Use `RESULTS_final.md` only.

---

## 4. Question 1: does the coordination gain survive the new prices?

Yes. Headline stage, relaxed targets, end-adjusted:

| Group | n | ILP status | Gap, old prices (%) | Gap, new prices (%) [95 % CI] | Paired new − old (points) | Saving old → new (USD) | Paired saving change (USD) |
|---|---|---|---|---|---|---|---|
| usd4h x0.75 | 10 | 10 OPT | 9.78 ± 2.88 | 9.56 [6.73, 12.38] | −0.23 ± 2.55 (p = 0.85) | 47.74 → 46.66 | −1.07 ± 14.90 |
| usd4h x1 | 10 | 10 OPT | 28.28 ± 7.36 | 27.34 [21.69, 32.99] | −0.93 ± 4.86 (p = 0.67) | 248.87 → 237.09 | −11.78 ± 57.00 |
| usd4h x1.5 | 10 | 7 OPT + 3 TL (≤ 1.07 %) | 43.45 ± 5.86 | 38.42 [35.35, 41.49] | **−5.03 ± 3.08 (p = 0.005, 9/10 lower)** | 796.06 → 805.74 | +9.69 ± 72.84 |
| nyc4h (lower bound) | 10 | 10 OPT | 27.37 ± 7.11 | 27.88 [24.15, 31.61] | +0.51 ± 5.05 (p = 0.82) | 240.98 → 244.44 | +3.46 ± 67.86 |
| usd4h pooled | 30 | 27 OPT + 3 TL | 27.17 ± 5.96 | 25.10 [20.15, 30.06] | −2.06 ± 2.00 (p = 0.044) | 364.22 → 363.17 | −1.05 ± 27.45 |

- **The gap is positive on 40/40 instances.** The minimum is 4.92 % on usd4h and 19.78 % on nyc4h (old prices: 5.3 %
  and 17.9 %).
- **x1.5 drop.** Against the ILP bound the x1.5 gap is at most 38.63 %, a paired change of −4.81 points. The best rule
  costs +294.90 ± 67.22 USD more at x1.5, mainly +507 USD of doubled penalties on the 17.6 orders it drops. The USD
  saving does not move, so the fall is a denominator effect. Report the gap in both % and USD.
- **Demand gradient.** It survives: 9.6 → 27.3 → 38.4 % (47 → 237 → 806 USD).
- **Composition of the saving.** Pooled usd4h, new prices (old prices in brackets):

  | Term | Share of the saving |
  |---|---|
  | Unserved | 64.4 % (22.8 %) |
  | Lateness | 19.0 % (50.5 %) |
  | Response | 16.4 % (26.4 %) |

  On nyc4h the shares are unserved 63.8 %, response 18.4 % and lateness 17.5 %. Service terms make up at least
  91.7 % of the saving on every instance (old: 93 %) and 99.8 % of the pooled usd4h saving **[rec]**.
- **Service.** The ILP serves more orders than under the old prices: 98.9 % vs 95.3 % (x1), 84.3 % vs 78.9 % (x1.5)
  and 98.3 % vs 94.2 % (nyc4h). It is late more often but never badly:
  - late orders per window go 0.6 → 3.1 (x1), 0.3 → 8.4 (x1.5) and 0.8 → 4.4 (nyc4h);
  - no ILP order is more than 60 min late;
  - the maximum is 35 min on OPTIMAL rows and 45 min on one TIME_LIMIT incumbent.

  Pooled usd4h late orders, best rule → ILP: 13.8 → 4.1 per window **[rec]** (old 13.3 → 0.4); nyc4h 14.9 → 4.4
  (old 14.7 → 0.8).
- **Price of recovery.** On usd4h x1 it is 0.41 ± 0.13 USD raw (10/10 written ILPs OPTIMAL), unchanged from round 5
  (paired +0.003 ± 0.109).
- **Best rule.** It is now r2 on 24/40 instances and M2 (= M2+M3) on 16/40 (old 17 / 23). The rule schedules are
  physically identical to round 5 on 240/240 rows. M3 never acts here: no instance has transfer services.
- **ILP adaptation.** If the ILP had kept its old-price plans, the new gap would be lower by 0.6-4.1 points. Its
  adaptation consists mainly of serving more orders.

---

## 5. Question 2: how do the results depend on P and v?

**P (psweep, v 15).** Best-known ILP; n = 10 per cell.

| P | usd4h gap (%) | stress4h gap (%) | stress4h ILP OPT / 10 | ILP served share usd4h / stress4h | Best-rule served share usd4h / stress4h | ILP late orders usd4h / stress4h |
|---|---|---|---|---|---|---|
| 20 | 22.29 ± 6.41 | 33.21 ± 2.48 | 10 | 0.900 / 0.798 | 0.919 / 0.746 | 0 / 0 |
| 30 | 22.48 ± 5.25 | 33.64 ± 2.22 | 7 | 0.958 / 0.875 | 0.919 / 0.746 | 1.1 / 2.2 |
| 40 | 23.79 ± 5.01 | 35.15 ± 2.17 | 5 | 0.978 / 0.894 | 0.925 / 0.758 | 2.2 / 4.0 |
| **60** | **27.34 ± 5.65** | **39.70 ± 2.84** | 4 | 0.989 / 0.944 | 0.925 / 0.758 | 3.1 / 10.9 |
| 80 | 30.66 ± 6.73 | 44.61 ± 3.15 (≤ 45.44 vs the bound) | 2 | 0.992 / 0.958 | 0.928 / 0.762 | 3.8 / 12.8 |

- **Mean gap.** It rises with P. Against P 60:

  | Pricing | usd4h (points) | stress4h (points) |
  |---|---|---|
  | P 20 | −5.05 ± 5.03 | −6.49 ± 3.08 |
  | P 80 | +3.31 ± 1.66 | +4.91 ± 0.71 |

  The 20 → 30 step is flat. Every step from P 40 upwards is significant. Per seed the gap is not monotone: it falls
  at least once on 4/10 usd4h and 2/10 stress4h seeds, all at low P.
- **Sensitivity around P 60.** About 0.17 (usd4h) and 0.25 (stress4h) gap points per USD of P. A ±20 USD error in P
  moves the stress4h gap by about ±5 points. The headline now rests on the calibrated P.
- **Dropping.** It returns only at P ≤ 20-30. At P 20 the ILP serves fewer orders than the best rule on 4/10 usd4h
  seeds and never delivers late. On usd4h it mostly stops dropping servable orders between P 40 and P 60. On stress4h
  it still drops 1.7-2.4 servable orders per window at P 60-80, mostly in time-limited solves.
- **Solve difficulty.** stress4h gets harder with P: OPTIMAL at 300 s on 10 → 2 of 10 seeds. At P 80 four
  incumbents are beaten by repricing the P 60 schedule.

**v (vsweep, P 60, usd4h x1, n = 10).**

| Pricing | Gap (%) | Seeds |
|---|---|---|
| v 8 | 25.80 ± 5.39 | 10 OPT |
| v 15 | 27.34 ± 5.65 | 10 OPT |
| v 25 | 29.47 ± 6.08 | 10 OPT |
| v 36 | 31.65 ± 6.56 (lower bound) | 8 OPT + 2 best-known |

- **Slope.** 2.09 ± 0.75 points per 10 USD/h, positive on 10/10 seeds. On the 8 seeds solved to optimality at every
  v, v 36 − v 15 = +3.87 ± 1.76 points.
- **ILP lateness barely responds to v.** It has 2.8-4.2 late orders and 0.7-1.1 min of lateness per served order,
  with a served share of 0.986-0.992. None of these changes against v 15 is significant. The rule schedules do not
  change with v: about 13.8 late orders per window and 3.6 late hours. The gap rises because those fixed late hours
  are priced higher.
- **Lateness price removed (v = 0).** The gap is still at least 23.90 ± 5.15 % (raw; minimum seed 9.6 %). At most
  3.54 ± 1.43 of the 27.44 % raw gap needs lateness to be priced at all.
- **Bridge.** (P 30, v 36) reproduces round 5 exactly: 28.28 ± 7.36 % in both rounds, paired −0.0012 ± 0.0025
  points. The R6 pipeline therefore adds no drift.
- **Old → new split** (Shapley, usd4h x1):

  | Effect | Points | Seeds |
  |---|---|---|
  | v 36 → 15 | −5.05 ± 1.86 | 10/10 negative |
  | P 30 → 60 | +4.12 ± 3.51 | 7/10 positive |

  The near-equal headline (−0.93 ± 4.86) is therefore a cancellation, and the sensitivity has moved from v to P. On
  stress4h, v alone (36 → 15 at P 30) costs 7.75 ± 0.58 points, and doubling P gives back 6.06.

---

## 6. Questions 3-4: round-5 artefacts and updated results

### 6.1 Status of the round-5 artefacts

| Artefact | Round 5 (old prices) | Round 6 (new prices) | Status |
|---|---|---|---|
| (a) PPO station agent on stress4h collapses to never-charge and looks cheaper than the best rule | PPO (M2+M3 riders) − best rule = −149.69 ± 58.13 USD, cheaper on 10/10 | +189.48 ± 75.85 USD, dearer on 10/10 (p = 3e-4). No PPO cell is cheaper than the best rule (n = 10 each). Never-charge − best rule: −149.72 → +193.92 ± 73.65 | **Objective artefact gone.** The service collapse persists for M2+M3 riders on stress4h (served share = never-charge on 8/10 seeds; charge-ASAP beats PPO on 10/10 by 176.50 ± 54.53): a learning failure of the comparator (one PPO seed, default hyper-parameters) |
| (b) Removing on-site charging (P_j = 0) lowers the rule's cost while its service falls | Same rule schedules priced at old prices: −238.9 [−380.9, −96.9] USD (0/5 dearer; stress4h-K8, n = 5) | +213.5 [124.0, 303.1] USD, dearer on 5/5; paired change +452.4 [325.4, 579.4] | **Gone.** Pure pricing effect (identical r2 / M2 schedules). The rule's served share still falls 65.3 → 51.6 % (−13.8 [−16.3, −11.2] points) |
| (c) Cost-minimal ILP fleet design serves only about 70 % of orders | K 4 / B 2, 1310.1 USD, 69.8 % served (n = 2) | Cheapest seed-mean incumbent K 8 / B 3, 1477.9 [1307.6, 1648.1], 99.3 % served (n = 3, 3/3 OPT; ranking not certified: certified set is 6-8 bikes, 2-3 spares). Per-seed argmins K 6 / B 2, K 8 / B 2, K 8 / B 3 serve 100 / 97.9 (= all servable) / 100 %. Every 4-bike design is at least 240.8 USD above the optimum on every seed | **Gone** |
| (d) Rule-based value of the swap network negative on one seed | usd4h seed 8: −180.0 USD | Same schedules: +646.2 USD; network value under the best rule positive on 10/10 usd4h and 5/5 stress4h (minimum 300.3 USD over all rules) | **Gone.** Caused by the prices alone |
| (e) Part of the rolling-horizon gain was order admission (dropping late orders) | Rolling − best rule served share −6.4 [−13.0, 0.2] (usd4h) and −2.5 [−11.2, 6.2] pp (stress4h), not significant | +0.8 [−3.1, 4.8] pp (usd4h) and +6.3 [0.8, 11.7] pp (stress4h, 4 up / 0 down / 1 tie). Rolling's own served share rose +7.8 [1.0, 14.6] and +8.8 [4.5, 13.0] pp on the same seeds. The offline ILP's small-scale admission effect (vsweep: −0.036 ± 0.025 served share at old prices) is also removed | **Gone** as an admission effect. The online advantage no longer depends on dropping orders, but it is smaller (Section 6.3) |

### 6.2 Network (home charging vs swap network × best rule vs ILP)

usd4h n = 10 (all ILPs OPTIMAL); stress4h n = 5 (network ILP 2 OPT + 3 TL, ≤ 1.12 %). End-adjusted.

| Quantity | usd4h new [CI] | usd4h old | stress4h new [CI] | stress4h old |
|---|---|---|---|---|
| Total effect, (home, best rule) → (network, ILP), % | 64.1 [62.5, 65.6] (1072.9 USD) | 44.3 | 60.0 [54.5, 65.4] (1412.2 USD) | 49.5 |
| Shapley share of the network, % (per-seed mean) | 58.2 [55.1, 61.3] | 35.0 | 53.8 [46.4, 61.1] | 29.2 |
| Shapley coordination − network, USD | −176.8 [−247.0, −106.5] (0/10) | +124.4 [32.9, 215.8] | −111.3 [−337.4, 114.7] (n.s.) | +324.7 [134.1, 515.2] |
| Network value under the ILP, % of home ILP | 40.6 [37.7, 43.4] (10/10) | 17.6 | 44.5 [39.5, 49.4] (5/5) | 22.3 |
| Network value under the best rule, % | 49.9 [45.0, 54.9] (10/10) | 20.3 | 32.8 [20.4, 45.2] (5/5) | 15.2 |
| Coordination at home, % | 39.4 [36.0, 42.7] | 32.3 | 28.0 [22.2, 33.8] | 35.1 |
| Coordination on the network (gap), % | 27.3 [21.7, 33.0] | 28.3 | 40.0 [34.6, 45.4] | 40.0 |
| Interaction, USD | −422.0 [−524.1, −319.8] (0/10 > 0) | −100.4 (n.s.) | −21.4 [−293.1, 250.3] | −22.9 |
| Orders per rider-hour, ILP home / network | 1.11 / 1.48 | 0.99 / 1.43 | 1.18 / 1.91 | 1.00 / 1.75 |
| Served share, ILP home / network | 0.742 / 0.989 | 0.658 / 0.953 | 0.592 / 0.954 | 0.500 / 0.875 |
| Empty km per rider-hour, ILP home / network | 0.23 / 0.76 | 0.28 / 0.75 | 0.18 / 0.82 | 0.29 / 0.79 |

- **Lever ranking.** The network is now the larger lever on usd4h. On stress4h the point estimates point the same way,
  but the difference is not significant. The round-5 statement that coordination accounts for 63-70 % of the joint
  effect was conditional on P 30.
- **Source of the network's value.** It is avoided penalties on unserved orders. On usd4h the ILP gains 534 USD of
  unserved penalty and pays 89 USD more response and 40 USD of set-up.
- **What did not move.** Only the coordination gap on the network shows no detectable change (verification C6).
- **Caveats.** Home electricity is unpriced. The network ILP with written targets was not run. The instances are
  shared with the headline (usd4h) and psweep (stress4h).

### 6.3 Rolling horizon (lambda 10, relaxed targets)

| Quantity | usd4h new [CI] (n = 10) | usd4h old | stress4h new [CI] (n = 5) | stress4h old |
|---|---|---|---|---|
| Offline gap, % of best rule | 27.34 [21.69, 32.99] | 28.28 | 40.00 [34.56, 45.43] | 39.96 |
| Foresight (rolling − offline), % | 16.35 [10.00, 22.69] | 8.33 | 18.88 [11.36, 26.41] | 8.70 |
| Online coordination (best rule − rolling), % | 11.00 [2.40, 19.59] | 19.94 | 21.11 [13.00, 29.23] | 31.26 |
| Share kept online, mean of ratios | 0.29 [−0.19, 0.77] | 0.64 | 0.53 [0.34, 0.71] | 0.77 |
| Share kept online, ratio of means | 0.42 | 0.73 | 0.53 | 0.79 |
| Share kept, paired change | −0.35 [−0.71, 0.02] (t p = 0.058, Wilcoxon p = 0.037) | | −0.25 [−0.35, −0.15] (5/5, p = 0.002) | |
| Seeds with rolling cheaper than the best rule | 9/10 | 10/10 | 5/5 | 5/5 |
| Served share, best rule / rolling / offline, % | 92.5 / 93.3 / 98.9 | 91.9 / 85.6 / 95.3 | 75.4 / 81.7 / 95.4 | 75.4 / 72.9 / 87.5 |

- **Seed 0.** On usd4h seed 0 rolling loses to r2 by 99.19 USD. This seed drives the mean of ratios; without it the
  mean of ratios is 0.49 [0.30, 0.68] (post hoc).
- **Foresight.** Foresight is now mostly orders that rolling drops and the offline ILP serves (usd4h: 120.0 of the
  137.1 USD of foresight). Most of these drops are flagged energy-refused.
- **Upper bounds.** In 12/15 runs the unpriced terminal fallback leaves (9) violated for 1.2 / 1.0 bikes per run, so
  the shares kept are upper bounds.
- **Adaptation.** The rolling policy does not reliably adapt: on 4 usd4h seeds the round-5 online schedule would be
  cheaper at the new prices.
- **Scope.** Lambda 0 / 20 and the forecast plan were not re-run.

### 6.4 Station levers (stress4h-K8, n = 5, 600 s)

- **No on-site charging, ILP.** +228.53 [184.05, 273.00] USD (about 17 % of the reference). It is proven to cost at
  least 169.6 USD on every seed: 4/5 of these solves are OPTIMAL, 1 is TL at 0.72 %. On seeds 0-2 it is 210.42 against
  79.45 USD in round 5 (paired +130.98 [47.07, 214.89], n = 3). The demand-charge break-even rises from 6,217 to about
  20,400 USD per kW-month (minimum over seeds).
- **No on-site charging, rule.** +213.51 [123.95, 303.07], dearer on 5/5 seeds (artefact (b) gone).
- **Gap.** 46.14 [42.47, 49.80] % at the reference. It is 41.85 [37.85, 45.86] % without on-site charging (paired
  −4.28 [−5.84, −2.73], 5/5) and 47.69 [43.43, 51.94] % with the lock-out. The reference gap is a lower bound (at most
  48.31 % against the proven bounds). In round 5, removing on-site charging cut the gap by 10.99 points.
- **Lock-out of 2 spares, ILP.** Unresolved. All reference and lock-out solves are TL. The measured −7.80
  [−59.88, 44.28] is solver noise; the true change lies in [0, 6.6]-[0, 71.4] USD per seed. For the rule it changes
  nothing on 3 seeds, costs +17.4 USD on seed 3 and +284.2 USD on seed 1.
- **Best rule.** It is r2 on 15/15 cells (old prices: M2 on 9/15).

### 6.5 Fleet and spares (stress4h, 48 orders, 0.6 kWh, n = 3)

- **ILP.** The cost-minimal design is interior to the grid: 6-8 bikes with 2-3 spares per site (certified set). The
  lowest seed-mean incumbent is K 8 / B 3, 1477.9 [1307.6, 1648.1] USD, serving 99.3 %.
  - 6 vs 8 bikes tie: 1.4 [−176.4, 179.2] USD.
  - 4 bikes cost +252.1 [61.3, 442.8] USD more and serve 25.0 [14.6, 35.4] points fewer orders than 8 bikes.
  - Bike values: 4 → 6 saves 214.4 [195.3, 233.5] USD per bike (old 74.5), 6 → 8 saves 89.4 [0.3, 178.5] (old 34.0;
    break-even with the 88.94 USD bike cost), 8 → 10 saves 17.1 [−13.2, 47.5].
  - Spares: only the second spare per site has value (0.7-22.9 USD net). The fourth spare is worth −0.12 to −0.35 USD,
    certified on 10/12 pairs.
- **Best rule.** Still K 8 / B 4, 1619.6 [1256.2, 1983.0] USD, 97.9 % served. It sits on the spare edge of the grid,
  and the fourth spare still pays (26.4 USD per spare at 8 bikes).
- **Policies at their own per-seed designs.** Service is equal on every seed, and the ILP design costs 150.1
  [90.0, 210.2] USD less (9.4 % [6.5, 12.2]). Round 5 gave 17.5 % at 70 % vs 99 % service, and 8.75 % at matched
  service.
- **Gap at fixed demand.** The gap falls with spares: K 8 goes from 51.6 [47.8, 55.4] % at B 1 to 14.7 [−5.6, 35.0] %
  at B 4. K 4 gives 37.9 % at B 1 and 32.3-32.5 % at B 2-4.
- **Solve status.** 20/48 solves are TL (round 5: 1/24). The design conclusions rest on proven bounds.

### 6.6 Learning comparator (PPO station layer, n = 10 test seeds per cell)

| Quantity | Old prices | New prices |
|---|---|---|
| ILP status | nyc4h-stress 10 OPT; stress4h 3 OPT + 7 TL (0.13-1.64 %) at 120 s | nyc4h-stress 10 OPT; stress4h 5 OPT + 5 TL (0.32-1.12 %) at 300 s |
| Best-rule gap, nyc4h-stress / stress4h, % | 28.97 ± 7.27 / 41.30 ± 2.61 | 25.75 ± 3.58 / 39.71 ± 2.84 |
| PPO gap to the ILP, nyc4h-stress r2 / M2+M3, % | 31.77-33.51 (paper) | 28.01 ± 4.73 / 31.39 ± 4.78 |
| PPO gap to the ILP, stress4h r2 / M2+M3, % | 34.69-42.85 (paper) | 43.47 ± 3.81 / 46.25 ± 2.49 |
| PPO − own rule, nyc4h-stress r2 / M2+M3, USD | +22.07 ± 25.89 / −8.38 ± 18.87; served −3.6 / −5.6 pp | −1.11 ± 4.09 / +4.14 ± 8.76; served +0.3 / −0.3 pp |
| PPO − best rule, stress4h M2+M3, USD | −149.69 ± 58.13 | +189.48 ± 75.85 |
| PPO − never-charge, stress4h M2+M3, USD | +0.03 ± 0.07 | −4.43 ± 7.37 |
| Served share, PPO M2+M3 / best rule / ILP, stress4h, % | 58.5 / 74.6 / 85.4 | 59.0 / 75.8 / 94.4 |
| Instance-adjusted training trend, nyc4h-stress r2 / M2+M3, USD | −82.8 / −175.0 | −189.5 / −270.1 |
| Instance-adjusted training trend, stress4h r2 / M2+M3, USD | −46.6 / −53.1 | −7.9 [−28.9, 13.1] / +27.0 [10.9, 43.1] (worse) |
| M4 (selfish) − best rule, nyc4h-stress / stress4h, USD **[rec]** | 45.03 ± 62.65 / 42.69 ± 71.70 | 45.68 ± 61.61 / 21.13 ± 62.76 (neither significant) |

- **nyc4h-stress.** Where PPO learns, it reproduces its own rule station layer (= charge ASAP).
- **stress4h.** PPO does not learn the rule: it is dearer than its own rule by 40.24 ± 27.48 USD (r2) and
  149.30 ± 43.24 USD (M2+M3).
- **Rule schedules.** The rule and heuristic schedules are identical across rounds (repricing error ≤ 5e-13 USD over
  160 rows).

---

## 7. Old prices vs new prices for every headline number in the paper

"Where" lists every place the number appears: Abs = abstract, HL = highlights, Intro = Section 1 findings paragraph,
6.x = subsection or Table 1 / Table 2 of Section 6, Concl = Section 8. "Old" is the paper's value. Bases follow the
paper: the stressed rows of Table 1, the 6.4 network rows and Table 2(b) are on objective (26) (raw); everything else
is end-adjusted. Where the new raw value is not reported, the end-adjusted value is given and marked "ea"; the round-5
reports show that the two bases differ by at most 0.1 point and 1.5 USD. "Rerun needed" marks numbers for which R6
has no new-price value.

### 7.1 Coordination gap and its composition

| # | Quantity | Where | Old (paper) | New | 95 % CI | n | ILP status (new) | Source |
|---|---|---|---|---|---|---|---|---|
| 1 | Gap, usd4h pooled (x0.75, x1, x1.5) | Abs, HL ("27 %"), Intro, 6.2, Table 1, Concl | 27.2 % (21.2-33.1) | **25.10 %** | [20.15, 30.06] | 30 | 27 OPT + 3 TL (≤ 1.07 %) | headline |
| 2 | Gap, usd4h x1 | Abs, 6.2, Table 1, Table 2(a) | 28.3 % (20.9-35.6) | **27.34 %** | [21.69, 32.99] | 10 | 10 OPT | headline |
| 3 | Gap, usd4h x0.75 | Abs ("from 9.8 %"), 6.2, Table 1 | 9.78 % (6.90-12.66) | **9.56 %** | [6.73, 12.38] | 10 | 10 OPT | headline |
| 4 | Gap, usd4h x1.5 | Abs ("to 43.5 %"), 6.2, Table 1 | 43.45 % (37.59-49.31) | **38.42 %** (≤ 38.63 against the bound) | [35.35, 41.49] | 10 | 7 OPT + 3 TL (≤ 1.07 %) | headline |
| 5 | Gap, nyc4h (lower bound) | Abs, Intro, 6.2, Table 1, Concl | ≥ 27.37 % (20.26-34.48) | **≥ 27.88 %** | [24.15, 31.61] | 10 | 10 OPT | headline |
| 6 | Minimum instance gap, usd4h / nyc4h | 6.2 | 5.3 / 17.9 % | 4.92 / 19.78 % | - | 30 / 10 | as rows 1, 5 | headline |
| 7 | Best rule = M2 / r2 (cells of 40) | 6.2 | 23 / 17 | 16 / 24 | - | 40 | - | headline |
| 8 | Gap, stress4h 6 bikes | Abs, HL ("40-47 %"), Intro, 6.2, Table 1, 6.5, Concl | 40.05 % (33.68-46.41), raw | **40.1 %** raw (40.00 ea) | [34.7, 45.5] (ea [34.56, 45.43]) | 5 | 2 OPT + 3 TL (≤ 1.12 %) | network |
| 9 | Gap, stress4h 6 bikes, seeds 0-9 | 6.9 | - | 39.70 % ea | ± 2.84 | 10 | 4 OPT + 6 TL (≤ 1.12 %) | psweep P 60 |
| 10 | Gap, stress4h-K8 | Abs, HL, Intro (range), 6.2, Table 1, 6.5 | 45.58 % (40.83-50.32), raw | **46.14 %** ea (lower bound; ≤ 48.31 against the bound) | [42.47, 49.80] | 5 | 0 OPT + 5 TL (0.83-10.48 %) at 600 s | levers |
| 11 | Gap, stress4h-K10 | Abs, HL ("47 %"), Intro, 6.2, Table 1, 6.5, Concl (47.0 %) | 46.99 % (43.09-50.88) | rerun needed | - | - | - | - |
| 12 | Gap, stress8h | 6.2 Table 1, 6.5 | 47.96 % | rerun needed | - | - | - | - |
| 13 | Gap, transfer experiment | 6.2, Table 1, 6.6 | 20.98 % | rerun needed | - | - | - | - |
| 14 | Gap, Manhattan bi-level / seven layouts | Abs (31.8-34.3), 6.2, Table 1, 6.7 | 31.8 / 34.3 % | rerun needed | - | - | - | - |
| 15 | Gap, learning comparison stress4h (seeds 0-9) | 6.2 Table 1, 6.9 | 41.30 % (38.69-43.91), 120 s | **39.71 %** | [36.87, 42.55] | 10 | 5 OPT + 5 TL (0.32-1.12 %) at 300 s | rl |
| 16 | Gap, nyc4h-stress (lower bound) | 6.2 Table 1, 6.9 | ≥ 28.97 % (21.70-36.24) | **≥ 25.75 %** | [22.17, 29.33] | 10 | 10 OPT | rl |
| 17 | Ratio to the preliminary specification (0.92 / 0.86) | 6.2 | 29.6 → 27.2 %; 31.8 → 27.4 % | rerun needed (the legacy rows are old-price) | - | - | - | - |
| 18 | Price of recovery, base families | 6.2 | < 0.5 USD (n = 30, 10) | 0.41 ± 0.13 USD raw (usd4h x1 only) | [0.28, 0.54] | 10 | 10 written OPT | headline |
| 19 | Saving, usd4h pooled (USD) | 6.2 | 364.2 (230.2-498.2) | **363.17** | [234.99, 491.35] | 30 | as row 1 | headline |
| 20 | Saving shares usd4h: lateness / response / unserved | 6.2, Intro ("mainly through lateness, response time and unserved orders") | 50.5 / 26.4 / 22.8 % | **19.0 / 16.4 / 64.4 %** | - | 30 | as row 1 | headline |
| 21 | Travel / electricity share, usd4h | 6.2 | 0.3 / 0.2 % | 0.15 / 0.17 % (0.53 / 0.62 of 363.17 USD) | - | 30 | as row 1 | headline |
| 22 | Saving, nyc4h (USD) | 6.2 | 241.0 (145.6-336.4) | **244.44** | [196.98, 291.90] | 10 | 10 OPT | headline |
| 23 | Saving shares nyc4h: lateness / response / unserved | 6.2 | 49.1 / 34.3 / 16.2 % | **17.5 / 18.4 / 63.8 %** | - | 10 | 10 OPT | headline |
| 24 | Service share of the saving | Abs ("almost entirely"), 6.2 (≥ 93 % per instance), Concl (> 99 %) | ≥ 93 % per instance; > 99 % pooled | ≥ 91.7 % per instance; 99.8 % pooled usd4h **[rec]** | - | 30 / 40 | as row 1 | headline |
| 25 | Late orders per window, best rule → ILP | 6.2 | usd4h 13.3 → 0.4; nyc4h 14.7 → 0.8 | usd4h 13.8 → 4.1 **[rec]**; nyc4h 14.9 → 4.4 | usd4h ILP ± 1.5; nyc4h ILP ± 1.4 | 30 / 10 | as rows 1, 5 | headline |
| 26 | Served-share rise, ILP − best rule | 6.2 | +0.06 / +0.04 | **+0.081 / +0.072** **[rec]** | ± 0.027 / ± 0.030 | 30 / 10 | as rows 1, 5 | headline |
| 27 | Detour per swap saved by the ILP, km | 6.2 | 0.39 / 0.42 | 0.36 / 0.40 **[rec]** | ± 0.13 / ± 0.18 | 30 / 10 | as rows 1, 5 | headline records |
| 28 | Share of swaps without a wait, best rule → ILP | 6.2 | 0.92 → 0.74; 0.86 → 0.53 | 0.91 → 0.73; 0.86 → 0.48 **[rec]** | - | 30 / 10 | as rows 1, 5 | headline records |
| 29 | ILP end adjustment larger by / electricity saving, USD | 6.2 | 0.44, 0.50 / 0.66, 0.65 | 0.46, 0.58 / 0.62, 0.60 | ± 0.07, ± 0.06 / ± 0.05, ± 0.07 | 30 / 10 | as rows 1, 5 | headline |
| 30 | ILPs of the headline solved to optimality | 6.1 | 80/80 (max gap 9.6e-5) | 47/50 (3 TL at x1.5, ≤ 1.07 %) | - | 50 | - | headline |
| 31 | Gap against the proven bound, largest excess | 6.1 | ≤ 0.77 points on average | headline ≤ 0.21; psweep stress4h P 60 +0.33; levers +2.17 (48.31 vs 46.14) | - | - | - | headline, psweep, levers |

### 7.2 Rolling horizon (Section 6.3, Table 2(a))

| # | Quantity | Where | Old (paper) | New | 95 % CI | n | ILP status (new) | Source |
|---|---|---|---|---|---|---|---|---|
| 32 | Share kept online, lambda 10, usd4h / stress4h (mean of ratios) | Abs, HL, Intro ("64-77 %"), 6.3, Table 2(a), Concl | 0.64 (0.44-0.83) / 0.77 (0.64-0.90) | **0.29 / 0.53** | [−0.19, 0.77] / [0.34, 0.71] | 10 / 5 | windows 120/120 OPT; offline usd4h 10 OPT, stress4h 2 OPT + 3 TL | rolling |
| 33 | Share kept, ratio of means | Table 2(a) | 0.73 / 0.79 | **0.42 / 0.53** | - | 10 / 5 | as row 32 | rolling |
| 34 | Online coordination, % of best rule | Table 2(a) | 19.9 / 31.3 | 11.00 / 21.11 | [2.40, 19.59] / [13.00, 29.23] | 10 / 5 | as row 32 | rolling |
| 35 | Foresight, % of best rule | Table 2(a) | 8.3 / 8.7 | 16.35 / 18.88 | [10.00, 22.69] / [11.36, 26.41] | 10 / 5 | as row 32 | rolling |
| 36 | Foresight share, mean of ratios (= 1 − share kept per seed) | Intro, 6.3, Table 2(a), Concl ("minor part on stressed") | 0.36 (0.17-0.56) / 0.23 (0.10-0.36) | 0.71 / 0.47 (derived) | [0.23, 1.19] / [0.29, 0.66] | 10 / 5 | as row 32 | rolling |
| 37 | Foresight share, ratio of means | Table 2(a) | 0.27 / 0.21 | 0.578 / 0.470 | - | 10 / 5 | as row 32 | rolling |
| 38 | Costs: best rule / rolling lambda 10 / offline, usd4h (USD) | Table 2(a) | 830.9 / 648.6 / 582.1 | 838.50 / 738.51 / 601.41 | [753.33, 923.68] / [672.23, 804.78] / [572.70, 630.13] | 10 | as row 32 | rolling |
| 39 | Costs: best rule / rolling lambda 10 / offline, stress4h (USD) | Table 2(a) | 1387.4 / 944.1 / 826.1 | 1581.76 / 1242.78 / 942.01 | [1289.40, 1874.12] / [1015.28, 1470.29] / [819.82, 1064.19] | 5 | as row 32 | rolling |
| 40 | Seeds with rolling cheaper than the best rule | Abs (R5 digest), 6.3, Table 2(a), Concl | 15/15 | **14/15** (usd4h seed 0 loses by 99.19 USD) | - | 15 | as row 32 | rolling |
| 41 | Served share, rolling vs best rule | 6.3 | 0.856 vs 0.919; 0.729 vs 0.754 | 0.933 vs 0.925; 0.817 vs 0.754 | paired +0.8 [−3.1, 4.8] / +6.3 [0.8, 11.7] pp | 10 / 5 | as row 32 | rolling |
| 42 | Lateness, rolling vs best rule (USD per window) | 6.3 | 5.7 vs 125.7; 5.4 vs 273.6 | 23.1 vs 53.8; 36.5 vs 114.0 (= order-minutes 92.5 / 215.0 and 146.0 / 456.0 × v / 60) | rolling order-min [39.2, 145.8] / [86.1, 205.9] | 10 / 5 | as row 32 | rolling |
| 43 | Online runs with the terminal fallback; bikes breaking (9) | 6.3 | 47/60 (all lambda); 0.8-2.6 bikes | 12/15 (lambda 10 only); 1.20 / 1.00 bikes | [0.54, 1.86] / [0.12, 1.88] | 15 | - | rolling |
| 44 | Lambda 0 / 20, forecast plan, lookahead p-values | 6.3, Table 2(a) | 0.43 / 0.81 / 0.68 etc. | rerun needed | - | - | - | - |

### 7.3 Value of the swap network (Section 6.4, Table 2(b))

| # | Quantity | Where | Old (paper) | New | 95 % CI | n | ILP status (new) | Source |
|---|---|---|---|---|---|---|---|---|
| 45 | Total effect, % of (home, best rule) | Abs ("44-50 %"), 6.4, Table 2(b), Concl | 44.3 (39.6-49.1) / 49.6 (42.7-56.6) | **64.1 / 60.0** (raw 64.1 / 60.0) | [62.5, 65.6] / [54.5, 65.4] | 10 / 5 | usd4h all OPT; stress4h network 2 OPT + 3 TL | network |
| 46 | Total effect, USD | 6.4, Table 2(b) | 474.3 / 822.2 | 1072.9 / 1412.2 (ea) | [1033.3, 1112.6] / [1263.8, 1560.7] | 10 / 5 | as row 45 | network |
| 47 | Coordination's Shapley share of the total effect | Abs, Concl ("63-70 %"), 6.4, 7.4 | 63 / 70 % | **41.8 / 46.2 %** (100 − network share 58.2 / 53.8) | network share [55.1, 61.3] / [46.4, 61.1] | 10 / 5 | as row 45 | network |
| 48 | Shapley network / coordination, USD | Table 2(b) | 175.1 / 299.3; 249.2 / 573.0 | 625.2 / 448.3; 762.9 / 650.8 (raw) | ea: [579.6, 670.1] / [413.4, 482.7]; [601.2, 922.3] / [546.6, 754.3] | 10 / 5 | as row 45 | network |
| 49 | Coordination − network, USD | 6.4 | +124 (33-216) / +324 (133-514) | **−176.8 / −111.3** | [−247.0, −106.5] / [−337.4, 114.7] | 10 / 5 | as row 45 | network |
| 50 | Network value under the ILP, % | 6.4, Table 2(b), 7.2 | 17.7 (16.2-19.2) / 22.5 (19.4-25.5) | **40.7 / 44.6** (raw) | [37.8, 43.5] / [39.6, 49.5] | 10 / 5 | as row 45 | network |
| 51 | Network value under the ILP, USD | 6.4 | 125.1 / 238.1 | 414.4 / 752.6 (raw) | [367.8, 461.1] / [692.7, 812.5] | 10 / 5 | as row 45 | network |
| 52 | Network value under the best rule, % | 6.4, Table 2(b) | 20.4 (7.5-33.3) / 15.3 (−1.4-31.9); negative on 1 seed | 49.9 / 32.8 (ea); positive on 15/15 | [45.0, 54.9] / [20.4, 45.2] | 10 / 5 | - | network |
| 53 | Coordination at home / on the network, % | Table 2(b) | 32.4 / 28.4; 35.1 / 40.0 | 39.4 / 27.3; 28.0 / 40.0 (ea) | [36.0, 42.7] / [21.7, 33.0]; [22.2, 33.8] / [34.6, 45.4] | 10 / 5 | as row 45 | network |
| 54 | Interaction, USD | 6.4, Table 2(b) | −99.9 (n.s.) / −22.1 (n.s.) | **−422.0** (0/10 > 0) / −21.4 (n.s.) | [−524.1, −319.8] / [−293.1, 250.3] | 10 / 5 | as row 45 | network |
| 55 | Cell costs: home rule / home ILP / network rule / network ILP, usd4h | Table 2(b) | 1054.9 / 705.7 / 829.9 / 580.6 (raw) | 1674.3 / 1015.3 / 838.5 / 601.4 (ea) | Table 1 of the network report | 10 | as row 45 | network |
| 56 | Cell costs, stress4h | Table 2(b) | 1646.4 / 1062.4 / 1386.1 / 824.2 (raw) | 2354.2 / 1693.1 / 1581.8 / 942.0 (ea) | Table 1 of the network report | 5 | as row 45 | network |
| 57 | Orders per rider-hour, ILP home / network | 6.4, Table 2(b), 7.2 | 0.99 / 1.43; 1.00 / 1.75 | 1.11 / 1.48; 1.18 / 1.91 | paired +0.37 [0.33, 0.42] / +0.73 [0.65, 0.80] | 10 / 5 | as row 45 | network |
| 58 | Served share, ILP home / network | Table 2(b) | 0.658 / 0.953; 0.500 / 0.875 | 0.742 / 0.989; 0.592 / 0.954 | - | 10 / 5 | as row 45 | network |
| 59 | Empty km per rider-hour, ILP home / network | Table 2(b) | 0.28 / 0.75; 0.30 / 0.80 | 0.23 / 0.76; 0.18 / 0.82 | paired +0.53 [0.35, 0.71] / +0.64 [0.44, 0.85] | 10 / 5 | as row 45 | network |

### 7.4 When batteries and stations bind (Section 6.5)

| # | Quantity | Where | Old (paper) | New | 95 % CI | n | ILP status (new) | Source |
|---|---|---|---|---|---|---|---|---|
| 60 | Gap rise with fleet, 6 → 8 → 10 bikes | Abs, HL, Intro, 6.5 | 40.05 → 45.58 → 46.99 % | 40.1 (raw) → 46.14 (ea, lower bound) → rerun needed | rows 8, 10 | 5 | rows 8, 10 | network, levers |
| 61 | Written-target 6-bike gap; stress8h gap | 6.5 | 39.83 %; 47.96 % | rerun needed | - | - | - | - |
| 62 | Fixed demand 48 orders: gap at 4 bikes | 6.5 | 42-43 % (n = 2) | 37.9 % (B 1), 32.3-32.5 % (B 2-4) | B 2: [24.1, 40.8] | 3 | K 4: 4 OPT + 8 TL | fleet |
| 63 | Fixed demand: gap at 8 bikes, 1 → 4 spares | 6.5 | 46.1 → 14.5 % (n = 2) | 51.6 → 14.7 % | [47.8, 55.4] → [−5.6, 35.0] | 3 | K 8: 9 OPT + 3 TL | fleet |
| 64 | LP value of a spare / charger, 6 / 8 / 10 bikes | 6.5, Concl | 0.45 / 2.79 / 21.87; 0.07 / 1.29 / 16.67 USD | rerun needed | - | - | - | - |
| 65 | Served share ILP vs best rule, 6 / 8 bikes | 6.5 | 0.875 vs 0.754; 0.866 vs 0.631 | 0.954 vs 0.754; 0.919 vs 0.653 | K 8 ILP [0.877, 0.961], rule [0.618, 0.688] | 5 / 5 | rows 8, 10 | network, levers |
| 66 | Price of recovery, 6 bikes; boundary grid | 6.5 | 3.20 USD; ≤ 4.38 | rerun needed | - | - | - | - |
| 67 | Cost-minimal ILP design | 6.5, 7.1 | K 4 / B 2, 1310.1 USD, 0.698 served | **6-8 bikes, 2-3 spares** (lowest incumbent K 8 / B 3, 1477.9 USD, 0.993 served; not certified) | [1307.6, 1648.1] | 3 | K 8 / B 3: 3/3 OPT | fleet |
| 68 | Cost-minimal rule design | 6.5 | K 8 / B 4, 1587.7, 0.990 | K 8 / B 4, 1619.6, 0.979 | [1256.2, 1983.0] | 3 | POLICY | fleet |
| 69 | ILP design vs rule design | 6.5, 7.1 | 17.5 % cheaper at 0.698 vs 0.990; 8.75 % at matched service (K 8 / B 2, 0.969) | **9.4 % cheaper at equal service on every seed** (150.1 USD) | [6.5, 12.2] % ([90.0, 210.2] USD) | 3 | argmin cells OPT | fleet |
| 70 | Saving per extra bike, from 4 / 6 bikes (USD) | 6.5 | 73-75 / 33-34 (n = 2) | **214.4 / 89.4**; 8 → 10: 17.1 | [195.3, 233.5] / [0.3, 178.5] / [−13.2, 47.5] | 3 | 4 → 6: 4/6 TL; 6 → 8: 2/6 TL; 8 → 10: 6/6 OPT | fleet |
| 71 | Optima on the grid edge | 6.5 | both | rule only (B = 4); ILP interior | - | 3 | - | fleet |
| 72 | Negative net value of a rule spare | 6.5 | −9.33 (0.5 kWh), −5.19 (0.6 kWh) USD | 0.6 kWh: K 4 / B 2 → 3 seed 2 −19.1; K 6 seed 1 −1.3; K 10 seed 1 −1.0 USD (single seeds); pack sizes: rerun needed | - | 1 seed each | POLICY | fleet |
| 73 | No on-site charging, ILP change | 6.5, 7.1, Concl | 79.23 (18.95-139.50), n = 3, ≥ 51.8 per seed | **+228.53** USD, ≥ 169.6 per seed | [184.05, 273.00] | 5 | 4 OPT + 1 TL (0.72 %); reference 0/5 OPT | levers |
| 74 | Demand-charge break-even for on-site charging | 6.5, 7.2 | ≥ 6,217 USD per kW-month | ≥ about 20,400 | - | 5 (minimum over seeds) | as row 73 | levers |
| 75 | Other levers (faster chargers, second swap position, lock-out of 1 / 2 spares), ILP | 6.5 | −5.00, −2.16, −1.55, −2.01 USD (within 9.3 USD MIP gap) | lock-out of 2 spares: −7.80 [−59.88, 44.28], unresolved (true value in [0, 6.6]-[0, 71.4] per seed); others: rerun needed | - | 5 | 0/5 OPT | levers |

### 7.5 Behaviour, learning, abstract and conclusion ranges

| # | Quantity | Where | Old (paper) | New | 95 % CI | n | ILP status (new) | Source |
|---|---|---|---|---|---|---|---|---|
| 76 | M4 (selfish) − best rule, nyc4h-stress / stress4h | 6.8 | 45.03 / 42.69 USD (n.s.) | 45.68 / 21.13 USD (n.s.) **[rec]** | [−15.93, 107.30] / [−41.63, 83.89] | 10 / 10 | POLICY | rl records |
| 77 | Compliance (half compliance closes about a third), price of decentralisation, Manhattan siting and transfers | Abs, HL, Intro, 6.6-6.8, Concl | 36.0 %, 354.3 USD, 12.73 %, 3.99 %, 2.6-2.7 % | rerun needed | - | - | - | - |
| 78 | ILP cheaper than PPO (range of gaps) | Abs ("32-43 %"), Intro, 6.9, Concl ("31.8-42.9 %") | 31.77-33.51 (nyc4h-stress), 34.69-42.85 % (stress4h) | **28.01-31.39 / 43.47-46.25 %** (overall 28-46 %) | nyc r2 [23.28, 32.74], M2+M3 [26.61, 36.17]; stress r2 [39.66, 47.28], M2+M3 [43.76, 48.74] | 10 each | nyc 10 OPT; stress 5 OPT + 5 TL | rl |
| 79 | PPO − own rule, nyc4h-stress (cost; served) | 6.9 | +22.07 / −8.38 USD; served −3.61 / −5.56 pp | −1.11 / +4.14 USD; served +0.3 / −0.3 pp | [−5.20, 2.98] / [−4.62, 12.90] | 10 | 10 OPT | rl |
| 80 | PPO vs never-charge, nyc4h-stress r2 / M2+M3 | 6.9 | p = 0.01 / p = 0.09 | −470.55 ± 90.65 (p = 9e-7) / −581.56 ± 102.08 (p = 4e-7) USD | - | 10 | - | rl |
| 81 | ILP vs best-rule lateness, nyc4h-stress / stress4h (USD) | 6.9 | 6.0 / 2.1 vs 181.2 / 303.9 | ILP 20.6 / 39.0 vs best rule 75.5 / 131.4 | ILP ± 7.3 / ± 9.5 | 10 | as row 78 | rl |
| 82 | PPO M2+M3 − best rule, stress4h | 6.9, Concl ("beat the rules only where it had stopped charging") | −149.69 (91.56-207.82 cheaper) | **+189.48** (dearer on 10/10) | [113.63, 265.33] | 10 | 5 OPT + 5 TL | rl |
| 83 | PPO M2+M3 − never-charge, stress4h | 6.9 | +0.03 USD | −4.43 USD | [−11.80, 2.94] | 10 | - | rl |
| 84 | Served share PPO M2+M3 / best rule / ILP, stress4h | 6.9 | 58.5 / 74.6 / 85.4 % | 59.0 / 75.8 / 94.4 % | ± 5.2 / ± 5.3 / ± 2.9 | 10 | as row 78 | rl |
| 85 | PPO lateness / unserved vs best rule, stress4h M2+M3 (USD) | 6.9 | 137.7 / 597.0 vs 303.9 / 366.0 | 59.2 / 1182.0 vs 131.4 / 696.0 | ± 15.6 / ± 148.8 vs ± 24.4 / ± 151.7 | 10 | - | rl |
| 86 | Training improved the stochastic policy | 6.9 | in all four runs | in 2 of 4 (nyc4h-stress: −189.5, −270.1 USD); stress4h −7.9 [−28.9, 13.1] and +27.0 [10.9, 43.1] (worse) | block-clustered | 4 runs | - | rl |
| 87 | Reference ILP status, learning comparison | 6.9 | nyc 10 OPT; stress4h 3 OPT + 7 TL (0.13-1.64 %) | nyc 10 OPT; stress4h 5 OPT + 5 TL (0.32-1.12 %) | - | 10 / 10 | - | rl |

**Highlights, new wording (numbers only):**
- Bullet 2, "27 %": 25 % pooled (25.10 [20.15, 30.06], n = 30), or 27 % at nominal demand (27.34, n = 10).
- Bullet 3, "64-77 %": about half (ratio of means 0.42 / 0.53; mean of ratios 0.29 / 0.53, upper bounds).
- Bullet 4, "40-47 %": 40-46 % on 6 and 8 bikes; K 10 not re-run.
- Bullet 5: not re-run (Manhattan).

---

## 8. Recommendation

**Switch the paper's main specification to the new prices (P 60, v 15), and report the old prices as a sensitivity
case.** Reasons:
1. **The calibration is better grounded.** At the old prices the model drops an order once it is about 13-18 min late,
   which no real platform does. The new prices put the serve/drop break-even at about 76-85 min late, close to real
   cancellation practice (`penalty_calibration.md`).
2. **The headline survives.** It is statistically unchanged at usd4h x0.75 and x1 and on nyc4h, positive on 40/40
   instances, and identical in USD at x1.5. The demand gradient survives.
3. **The paper's "most consequential limitation" disappears.** All five artefacts (a)-(e) that the paper now hedges in
   Sections 3, 6.3, 6.5, 6.9 and 7.3 are gone. The remaining phenomena (the PPO learning failure on stress4h, rolling
   keeping about half) are genuine results, not properties of the calibration.
4. **The sensitivity is now measured.** psweep and vsweep give the gap along both price axes (22-31 % on usd4h and
   33-45 % on stress4h for P 20-80; 26-32 % for v 8-36), so the dependence on P can be stated rather than hidden.

**Conditions before the switch:**
- **Re-solve these cells** with sleep disabled and a `runtime_s > wall_s + 10` guard:
  - usd4h x1.5 seeds 0, 5, 8 at 600 s;
  - psweep usd4h P 80 seed 0 and stress4h P 40 seed 9;
  - vsweep P 60 / v 36 seeds 5, 6;
  - fleet K 10 / B 1 and K 10 / B 2 on seed 2;
  - the levers reference, warm-started from the lock-out incumbent or with a longer limit, so that the K8 gap and the
    lock-out effect are resolved.
- **Re-run or flag the experiments not re-run.** Either re-run them at the new prices or mark them clearly as
  old-price results:
  - stress4h-K10 and stress8h;
  - the LP shadow prices and the boundary grid;
  - the pack-size axis;
  - rolling lambda 0 / 20 and the forecast plan;
  - transfers (X2);
  - Manhattan siting and compliance (X6; there M2+M3 reads P through M3, so the rules may change);
  - the legacy waterfall;
  - the price of recovery on x0.75, x1.5 and nyc4h.

  Re-running X2 and X6 is preferable, because the abstract and conclusion quote them.
- **Report the gap in both % and USD.** The x1.5 percentage moves through the denominator while the USD saving does
  not.

**What would change in the manuscript:**

| Location | Change |
|---|---|
| Abstract | Every quantitative sentence: 27.2 → 25.1 % (28.3 → 27.3 % nominal); Midtown ≥ 27.9 %; 9.8-43.5 → 9.6-38.4 %; 40-47 → 40-46 % (K10 pending); 64-77 % → about one half; 44-50 % → 60-64 %, with the network (not coordination) the larger Shapley share; 32-43 → 28-46 %; compliance sentence pending X6 |
| Highlights | Bullets 2, 3, 4 (bullet 5 pending X6) |
| Section 1 | Findings paragraph: composition ("mainly through unserved orders, then lateness and response"); RQ2 sentence (foresight about half, no longer minor on stress4h); RQ1 learning range |
| Section 3 (special cases, response reference) | The "29.6 vs 29.9 USD" near-indifference paragraph is replaced: at the new prices the rule avoids 35.2 USD of response and lateness per dropped order against a 60 USD penalty (levers) |
| Section 5 (cost calibration) and Table S data costs | ν 36 → 15 USD/h from the promise, P 30 → 60 USD, new sources (penalty_calibration.md); the serve/drop break-even |
| Section 6.1 | Solve-status statements (47/50 headline ILPs OPTIMAL; more TL cells on stressed families; bound excess up to 2.17 points on K8) |
| Section 6.2, Table 1 | All rows except transfer, K10, stress8h and Manhattan (pending); text on composition, late orders, served share, detours and waits; Figure `x1_gap_by_demand` (replace with or adapt `r6_penalty/headline/figs/r6_gap_old_vs_new`); Figure `x1_component_decomposition` (replace with `r6_saving_components`) |
| Section 6.3, Table 2(a), Figure `x3_decomposition` | Lambda 10 rows and the decomposition (shares kept 0.29 / 0.53; ratio of means 0.42 / 0.53); "14 of 15"; the admission qualification is replaced by "no longer depends on dropping orders; foresight is mostly energy-refused drops"; lambda 0 / 20 and the forecast plan are pending (use `rolling/figs/fig_rolling_decomposition`) |
| Section 6.4, Table 2(b) | All numbers; the Shapley conclusion reverses on usd4h; the network value is positive on every seed; the interaction is significant on usd4h (`network/figs/fig_network_2x2_effects`, `fig_network_von_per_seed`, `fig_network_productivity`) |
| Section 6.5 | Fleet-axis paragraph and Figure `x5_gap_vs_fleet` (panel a K10 pending; panel b from the fleet grid); served shares; fleet sizing paragraph (artefact (c) resolved), Table S sizing, Figure S isocost (`fleet/figs/*`); station-levers paragraph and Table S levers (`levers/figs/*`); shadow prices and boundary unchanged (old prices, flagged) |
| Section 6.6, 6.7 | Unchanged numbers but they must be labelled old prices, or re-run |
| Section 6.8 | M4 − best rule: 45.68 / 21.13 USD; compliance pending |
| Section 6.9, Figure `x7_cost_by_method`, Table S rl, Figure S rl-tradeoff, training appendix | Rewrite: PPO is never cheaper than the best rule, learns the rule on nyc4h-stress and fails to learn it on stress4h (`rl/figs/*`) |
| New subsection or supplement section | Price sensitivity: psweep and vsweep tables and figures (`psweep/figs/fig1_gap_vs_P`, `fig2_service_vs_P`, `fig3_saving_components`; `vsweep/figs/fig1_gap_vs_v`, `fig2_lateness_vs_v`, `fig3_saving_components`); the old-price bridge |
| Section 7 | Managerial (rolling share, fleet design, on-site charging 228.5 USD), policy (break-even about 20,400 USD/kW-month; network 40.7 / 44.6 %; Shapley), limitations (the calibration paragraph becomes a P-sensitivity paragraph), future research ("recalibrated drop penalty" is done) |
| Section 8 | RQ1 (25.1 %, ≥ 27.9 %, 99.8 %, PPO 28-46 % and never cheaper), RQ2 (about half; 14/15; network and coordination 64 / 60 %, network larger on usd4h), RQ3 (on-site charging 228.5 USD), last paragraph (the main limitation is no longer the near-indifference; it is the dependence on P) |
| Supplement | coverage table, levers, sizing, rl, recovery, metrics figures, Shapley / waterfall (legacy, pending) |

---

## 9. Caveats

1. **The headline now rests on P.** Unserved orders are 58-83 % of the saving at P 60. The gap moves about 0.17-0.25
   points per USD of P, and the calibration's churn evidence is weak (`penalty_calibration.md`, item 7). State the
   P range (40-80) and show psweep.
2. **More lateness.** The ILP accepts more late deliveries (3.1 per window at usd4h x1, 8.4 at x1.5, 10.9 on
   stress4h). None is over 60 min; the maximum is 35 min on OPTIMAL headline rows and exactly 60 min on stress4h.
   "Service quality" now includes late service; report served share and lateness side by side.
3. **Harder solves at the new prices.** TIME_LIMIT is more frequent:
   - headline x1.5: 3/10;
   - psweep stress4h: 6/10 at P 60 and 8/10 at P 80 (up to 11.63 %);
   - network stress4h: 3/5;
   - levers: 0/5 reference solves OPTIMAL at 600 s (up to 10.48 %);
   - fleet: 20/48;
   - rl stress4h: 5/10.

   Gaps on these cells are incumbent-based, and the stated bound limits must accompany them.
4. **Sleep-truncated rows** in psweep, vsweep and fleet (Section 3). The final reports correct for them; the raw
   `records.jsonl` and the auto `RESULTS.md` still contain them.
5. **Shared instances.** usd4h x1 seeds 0-9 are the same instances in headline, vsweep (v 15), psweep (P 60), network
   and rolling. stress4h seeds 0-4 recur in psweep, network, rolling and rl. These are not independent replications.
6. **M3 is inactive in every R6 family** (no transfer services), so the rules are price-invariant here by
   construction. On layouts with services (X2, Manhattan) M2+M3 reads P, and its schedules may change.
7. **Missing old-price detail.** Round-5 records lack per-order lateness, so old-price counts of orders more than 30
   or 60 min late and the old ILP maximum lateness (≤ 15 min) are reconstructed or bounded. The round-5 stress4h
   reference in psweep mixes 300 s (seeds 0-4) and 120 s (seeds 5-9) solves.
8. **Rolling.** The terminal fallback is unpriced in 12/15 runs, so the shares kept are upper bounds. usd4h seed 0
   dominates the mean of ratios. The rolling heuristic does not always adapt to the prices.
9. **Small n.** levers n = 5 (n = 3 against round 5), fleet n = 3 (round 5 n = 2), network and rolling stress4h n = 5.
   The fleet seed-mean ranking is not certified, and 6 vs 8 bikes is a tie.
10. **Learning.** One PPO seed, default hyper-parameters and 200,704 steps. The stress4h failure may be fixable by
    tuning, which was not tested.
11. **Percentage gaps depend on the price level.** Where neither method can serve some orders (x1.5), the percentage
    falls through its denominator although the USD saving is unchanged.
12. **Recomputed numbers.** Values marked **[rec]** were computed for this digest from `r6_penalty/headline/records.jsonl`,
    `per_instance_final.csv` and `r6_penalty/rl/records.jsonl`. The same code reproduces the paper's old-price values
    exactly, but these numbers have not been through a refuter pass.
