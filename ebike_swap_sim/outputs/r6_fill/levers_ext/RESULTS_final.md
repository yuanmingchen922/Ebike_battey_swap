# R6 fill, stage levers_ext: station levers on stress4h-K8 at the new prices (final report)

Family stress4h-K8 (code `r5_stress4h_k8`): 8 bikes, 64 orders, 3 swap sites with 2 spares and one 0.333 kW charger
each, one swap position per site, site power cap 4 kW, 4-h window, seeds 0-4. New prices: unserved penalty
P = 60 USD, response price w = 18 USD/h from release, lateness price v = 15 USD/h from the promise. Legacy prices
(round 5): P = 30, w = 18, v = 36. Everything else follows the round-5 main specification: eBaaS energy calibration,
aggregated ILP, Gurobi Threads 3, Seed 0, relaxed end targets (rho = 0, R_end = 0). Costs are end-adjusted (total +
end-state adjustment), USD per 4-h window. Best rule = per-instance minimum over r2, M2 and M2+M3 of the end-adjusted
cost. Gap = 100 (best rule - ILP) / best rule per instance, then averaged. Intervals are exact Student-t 95 % CIs over
seeds, written `mean [lo, hi]`. Lever effects are paired per seed (lever minus reference).

Five levers against one reference:

| lever | what changes | cell / folder | ILP limit |
|---|---|---|---|
| Reference | - | `reference`, r6_penalty/levers (re-solved at 1800 s by the retry) | 1800 s |
| Faster chargers | level size 50 Wh instead of 25 Wh on the same 0.6 kWh pack: L 12, p_ch 0.667 kW (see anomaly 1) | `eps50`, this stage | 600 s |
| Second swap position | M_j = 2 at every site, set-up +0.119 USD per window | `M2`, this stage | 600 s |
| Lock-out of 1 spare | one of the 6 spares removed at a random slot in the 17-18 h peak (shares 0.05 and 0.10 both round to one battery: one instance) | `lockout0.05` = `lockout0.1`, this stage | 600 s |
| Lock-out of 2 spares | two spares removed in the 17-18 h peak | `lockout0.25`, r6_penalty/levers (re-solved at 1800 s) | 1800 s |
| No on-site charging | site power cap P_j = 0 at all 3 sites | `P0`, r6_penalty/levers (seed 2 re-solved at 1800 s) | 600 / 1800 s |

All numbers below were recomputed from `records.jsonl` + `cases.jsonl` of this stage and of `r6_penalty/levers`
(last row per key, `retry_worse` rows ignored: none exist) and from `r5_x5_stress/records_{levers,core}.jsonl` by
`figs/make_levers_ext_figs.py`. No solve was run for this report. The script-generated `RESULTS.md` is kept unchanged;
its means and CI half-widths match this recomputation to rounding (Section 1, item 7). Two claims were corrected after
verification on 2026-10-20 (second-swap-position bracket and faster-charger mechanism); see the last section,
"Verification corrections".

## Answer in brief

- **Only on-site charging matters to the coordinated schedule.** Against the retried reference, removing it costs
  the ILP **+263.0 USD [216.8, 309.1]** per window (5/5 seeds; proven at least 207.7 USD on every seed, bracketed within 16 USD
  on 4 seeds and 40 USD on seed 2) and the best rule +213.5 [124.0, 303.1] (5/5). The demand-charge break-even for giving
  up on-site charging is at least **24,900 USD per kW-month** (minimum over seeds of the proven lower bound; 29,200
  to 36,200 on the other seeds; legacy prices: 6,200), far above the assumed 10-40 USD per kW-month, at which the
  demand charge of the three 0.333 kW connections is 0.08-0.33 USD per window. Both policies keep on-site charging
  on every seed at every assumed tariff.
- **The other four levers are within solver tolerance for the ILP, and the bounds now say how small they are.**
  Faster chargers: -1.6 [-14.8, 11.6], proven bracket covering zero on 3 seeds and a small cost increase on 2 (+4.7
  to +15.2 and +10.1 USD). Second swap position: it only relaxes the swap-position constraint (22) and adds a
  constant 0.119 USD set-up, so it can raise the ILP optimum (raw total) by at most 0.12 USD; it saves at most
  4.1-35.3 USD per seed (mean of the maxima 16.1 USD, 1.3 % of the reference). The measured +33.5 [2.0, 65.0]
  (end-adjusted; 5/5 seeds) compares 600 s M2 incumbents (5/5 time limit, 0.84-7.52 %) with the 1800 s reference
  and is a time-limit artefact; against the 600 s reference rows it is -1.4 [-38.0, 35.3] (4/5 > 0). Lock-out of
  1 spare: between 0 and 2.5-40.7 USD per seed (mean of the maxima 20.6 USD); lock-out of 2 spares: between 0 and
  16.9-41.3 USD, exactly +2.5 USD on seed 4 (both solves optimal). The measured lock-out changes (+11.8 and +9.8) are
  positive on 5/5 seeds, as a restriction requires, but inside the 15 USD mean MIP gap of the reference.
- **The rule gains a lot from faster chargers, but the lever is confounded.** The best rule costs -309.2 USD
  [-548.1, -70.4] less with the 50 Wh levels (cheaper on 5/5 seeds) and serves 12.8 points more orders. Yet the
  50 Wh instance is not only "the same pack charged twice as fast": route energies are unchanged but rounded up to
  the coarser levels (restaurant-to-customer legs 1-3 levels of 50 Wh instead of 1-5 of 25 Wh; rounding overhead on
  a delivery arc 21-28 % instead of 11-14 % of its route energy, so about 10-12 % more modelled energy per
  delivery arc and 20 % more per loaded leg). Purchased energy rises x1.76 [1.48, 2.05] for the ILP and x2.10
  [1.89, 2.31] for the rule; the records do not split that rise into its causes (item 1). The rule, which runs out
  of charged spares in the reference, benefits from the 1-h instead of 2-h pack turnaround; the ILP does not. The
  manuscript must describe the lever this way (Section 6).
- **The lock-out of one spare moves the rule only when it falls early in the peak.** On seeds 0, 2 and 4 the rule
  is unchanged (-0.3 to -0.4 USD bookkeeping), on seed 3 +17.4 USD, on seed 1 (site S3 at 17:05) +187.5 USD, where r2
  drops 6 more orders; mean +40.8 [-61.5, 143.1].
- **The reused `lockout0.1` rows are legitimate** on all five seeds (not only seed 4): the 5 % and 10 % shares both
  round to one battery, the slot and site drawn for n = 1 are identical, and the content key is the same, so the
  stage solved the instance once under `lockout0.05` and the case note of `lockout0.1` maps to it. It is one lever
  and is counted once here.
- **The retry changed the reference and with it the levers report of 2026-10-18.** The reference ILP is 1278.7
  [1086.9, 1470.6] (was 1313.6), the gap 47.59 % [42.16, 53.03] (was 46.14; at most 48.26 % against the bounds), the
  no-on-site-charging effect +263.0 (was +228.5), the break-even at least 24,900 (was 20,400). The three provably
  sub-optimal reference incumbents are gone: every lock-out incumbent now lies above its reference incumbent.

## 1. Problems and anomalies

1. **The faster-charger lever also coarsens the energy rounding (design confound, inherited from round 5;
   corrected 2026-10-20, see "Verification corrections", C3).** The instance builder keeps the 0.6 kWh pack and sets
   the level size to 50 Wh (L 12 instead of 24, p_ch 0.667 kW by p_ch = eps / (eta Delta)), so a charger still
   advances one level per slot and a full charge takes 1 h instead of 2 h. Rebuilt instances (seeds 0-4, demand
   hashes equal to the records): the routes and their energies are identical; the pack (600 Wh), the reserve (50 Wh:
   2 levels vs 1) and the bikes' initial energy are the same in Wh (equal on seeds 0-2 and 4; +75 Wh on seed 3 from
   rounding q0). Only the rounding g = ceil(E / eps) is coarser. Restaurant-to-customer legs average 55 Wh (4.5-125
   Wh; 13 % at or below 25 Wh) and take 1-5 levels (mean 2.69) at 25 Wh against 1-3 (mean 1.62) at 50 Wh; the
   concatenated delivery arcs (`energy_rounding = 'concat'`) take 1-11 against 1-6 levels. The rounding overhead over
   all candidate delivery arcs grows from 11-14 % to 21-28 % of the route energy, so the modelled energy per delivery
   arc rises by about 10-12 % (per loaded leg 67 -> 81 Wh, +20 %), and a full pack carries about 6.8 instead of 8.2
   loaded legs (-17 %). (hp = hd = 1 on all 64 orders are the pickup and handoff durations in slots, not energy.)
   The records show: purchased energy rises x1.76 [1.48, 2.05] for the ILP (n 5; eps 50 at 600 s, 3 optimal, seeds
   2-3 time limit at 2.66 and 0.41 %; reference at 1800 s, 1 optimal, seeds 0-3 at 0.75-2.87 %; x1.64 [1.24, 2.03]
   against the 600 s reference rows) and x2.10 [1.89, 2.31] for the best rule (M2 on eps-50 seeds 0, 1, 4, r2
   elsewhere). ILP served orders are unchanged (64/57/60/58/60 vs 63/57/59/57/60), ILP bike-km rises 0-9 %, ILP swaps
   15-17 instead of 11-13, rule swaps 13-18 instead of 9-10. With relaxed targets both ILP schedules end with the
   spares drained (station end deficit 3.45-3.60 kWh of the 3.6 kWh spare stock in both cells), so purchases are what
   the schedule needs beyond its start stock; the bikes' end deficit (positive part) falls from 575-975 to 100-950 Wh.
   The records hold neither the signed bike end state nor the per-arc energy of the schedules, so they do not split
   the purchase rise between the coarser rounding, the extra swaps and kilometres and fuller end states. The lever is
   therefore "chargers twice as fast, with energy rounded to 50 Wh levels", not "half-range packs". The manuscript's
   S8.4 sentence "route energies are rounded to the coarser levels, and the orders are unchanged" is true but should
   say how large the rounding effect is; the replacement wording is in Section 6. A clean charger-speed lever (one
   level per slot x 2 at eps 25 Wh) needs a formulation change (E2 (19)) and was not run.
2. **Time-limit asymmetry.** The reference and the 2-spare lock-out were re-solved at 1800 s (retry of 2026-10-19,
   warm-started from the lock-out incumbent, `mip_start_variant = ilp:lockout0.25|no_transfers` on all five
   reference seeds; improvements 59.0, 0, 102.7, 5.4, 7.2 USD, mean 34.9). The three new lever cells ran at 600 s and
   have not been retried (`--retry-unsolved` covers headline, psweep, vsweep, fleet and levers, not levers_ext).
   Consequences: (a) 12 of the 15 new ILP solves stopped at the limit (second swap position 0.84-7.52 %, mean
   absolute gap 49.6 USD; lock-out of 1 spare 0.41-5.65 %, 26.7 USD; faster chargers seeds 2-3 at 2.66 and 0.41 %);
   (b) the measured ILP deltas of these cells are biased upward. The second swap position only relaxes constraint
   (22) (M_j is its right-hand side) and adds a constant set-up of +0.119 USD per window (C_setup 38.447 against
   38.328, in the raw total), so its optimum can exceed the reference optimum by at most 0.12 USD. Its measured
   change, M2 at 600 s (5/5 time limit, 0.84-7.52 %) minus the reference at 1800 s (4 time limit at 0.75-2.87 %, 1
   optimal), is +33.48 [1.98, 64.97] end-adjusted (+33.51 [1.98, 65.04] raw), positive on 5/5 seeds and far above
   +0.12, so it is incumbent quality of the shorter time limit; against the original 600 s reference rows (5/5 time
   limit, 0.83-10.48 %) it is -1.37 [-38.04, 35.31] end-adjusted (-1.36 [-38.01, 35.30] raw), positive on 4/5. The
   proven bracket (raw totals) is [-16.4, +0.12], [-10.4, +0.12], [-35.3, +0.12], [-14.5, +0.12], [-4.1, +0.12] USD.
   Report the brackets, not the deltas, for the ILP. A 1800 s retry of the 12 time-limited rows (about 6 h at
   Threads 3) would narrow them.
3. **Lock-out effects are bounded, not resolved.** With the retried reference the measured changes (+11.8 and +9.8
   USD) have the right sign on every seed, but the proven brackets still span 17-41 USD on 4 seeds (seed 4 is exact
   for the 2-spare lock-out, +2.52 USD, both solves optimal, and at most 2.52 for the 1-spare lock-out). Nesting
   (1-spare lock-out at (S3, 17:30), (S2, 17:25), (S2, 17:05) is one of the two 2-spare lock-outs on seeds 2, 3, 4;
   not on seeds 0-1, where the single lock-out falls at the later slot of the pair) tightens the seed-2 upper end
   of the 1-spare lock-out from 71.1 to 40.7 USD and gives the seed-4 lower end 2.5 of the 2-spare lock-out.
4. **`reused: true` for `lockout0.1`, all five seeds.** The lane log prints it for seeds 0-4. `n_locked(6, 0.05) =
   max(1, round(0.3)) = 1 = n_locked(6, 0.10)`, `lockout_slots` depends on (n, seed) only, the site draw is the first
   draw of the same generator, and the content keys in `cases.jsonl` are identical per seed (de20be62, 88dddffb,
   ad4074d4, 0904d97f, dae2a212). `records.jsonl` holds 15 keys x 5 methods = 75 rows and no `lockout0.1` row;
   `summary.csv` and the script's `RESULTS.md` list the same rows twice under both cells. Legitimate, as in round 5
   ("5 % and 10 % round to 1 and are counted once"); the lever is counted once here.
5. **Superseded numbers in the R6 levers report, digest and manuscript.** `r6_penalty/levers/RESULTS_final.md`
   (2026-10-18) predates the retry. Its reference block (1313.6 USD; gap 46.14 % lower bound; three provably
   sub-optimal incumbents; +228.5 USD without on-site charging; break-even 20,400) is replaced by the values of
   Section 3 (1278.7; 47.59 %; no sub-optimal incumbent left; +263.0; at least 24,900). The same numbers sit in
   R6_DIGEST rows 10, 31, 73-75 and in the manuscript (6.6, 7.1, S8.4, S12, Table tab:res:levers footnote a).
6. **Rule rows violating a report-only constraint.** 6 of the 45 new rule rows (all r2: faster chargers seeds 0, 2,
   3; second swap position seeds 0, 1; 1-spare lock-out seed 0) violate terminal reachability (`check_ok = False`,
   `ok_modulo_report_only = True`), as in rounds 5-6; 5 of the 15 best-rule rows are affected (faster chargers seeds
   2-3, second swap position seeds 0-1, 1-spare lock-out seed 0). It slightly favours the rule, so gaps are
   conservative.
7. **The auto-generated `RESULTS.md` is correct but incomplete.** Every mean and CI half-width matches this
   recomputation (e.g. reference ILP 1278.720 +- 191.828, faster chargers delta best rule -309.231 +- 238.829,
   second swap position delta ILP 33.478 +- 31.497). But it says "Anomalies: none", lists `lockout0.1` as a second
   lever, gives no proven brackets, and its demand-charge table only evaluates the three assumed tariffs (no
   break-even).
8. **Cross-round comparison limits.** The legacy run has n = 3 (seeds 0-2) at 300 s against n = 5 at 600 / 1800 s;
   the best rule changes identity between price sets (legacy: M2 on 9 of 18 cells; new: r2 on 27 of 30, M2 on
   faster chargers seeds 0, 1, 4); absolute costs are not comparable across price sets, only effects, gaps and
   served shares. Legacy rule costs on seeds 3-4 are repriced new-price rows (exact for r2 and M2, which read no
   order price; M2+M3 reads the mean P_i through its stock-out value but produced identical schedules on every
   shared row). `check_repricing()`: 60 shared rule rows (reference 15, each lever 9), all status OK, max
   |difference| 4.55e-13 USD, 43 exact, schedule statistics and lock-out slots identical.
9. **Shared machine.** The stage ran on the laptop (138.0 min of a 270 min budget, exit 0, caffeinate) while other
   jobs ran; time-limited incumbents may depend on load. No solve was sleep-truncated (runtimes 600.04-600.85 s at
   the 600 s limit).

## 2. Coverage

| item | value |
|---|---|
| new cases | 20 notes = 4 cells x 5 seeds; 15 distinct instances (lockout0.1 = lockout0.05), relaxed targets, all planned cases present, 0 skipped |
| new records | 75 = 15 x (r2, M2, M2+M3, best rule, ILP), one row per (key, method), no duplicates, no ERROR / SKIPPED_BUDGET |
| reused rows | reference, no on-site charging, 2-spare lock-out from `r6_penalty/levers` (86 rows incl. 11 retry rows, 0 `retry_worse`); last row per key |
| rule rows | 45/45 status OK; MIP start accepted 15/15 (rule starts) |
| ILP rows, new | faster chargers 3 OPT (seeds 0, 1, 4; 124-540 s) + 2 TL (2.66, 0.41 %); second swap position 0 OPT + 5 TL (7.52, 0.84, 6.76, 2.72, 2.12 %); lock-out of 1 spare 0 OPT + 5 TL (1.91, 1.38, 5.65, 1.26, 0.41 %) |
| ILP rows, reused | reference 1 OPT + 4 TL (1.50, 0.75, 2.87, 1.00 %) at 1800 s; no on-site charging 4 OPT (600 s) + 1 TL (seed 2, 0.32 % at 1800 s); lock-out of 2 spares 1 OPT + 4 TL (2.20, 2.23, 3.26, 1.05 %) at 1800 s |
| time limits | 600 s requested and used on every new ILP; 1800 s on the retried rows; no budget shortening |
| absolute MIP gaps (incumbent - best bound over runs), mean per cell | reference 15.0 USD (0-34.9); faster chargers 7.7; second swap position 49.6; lock-out of 1 spare 26.7; lock-out of 2 spares 21.9; no on-site charging 1.0 |
| checks | ILP objective = evaluator cost on 15/15 new and 11/11 retried rows; `check_ok` and identity (24) true on all ILP schedules; prices P 60, w 18, v 15 on every row |
| model size, new | faster chargers 146-156 k binaries, 14.7-15.6 k rows (L 12); second swap position 297-316 k, 28.2-29.9 k; lock-out 297-316 k, 30.8-32.5 k |
| wall time | 138.0 min of 270 (`wall_time.jsonl`); lane 1: retry 20:01-01:24, levers_ext 01:24-03:42 UTC, exit 0 |
| legacy counterpart | `r5_x5_stress` levers: all six cells on seeds 0-2, ILP 300 s; reference rule rows from core; same demand hashes and lock-out slots on every shared instance |

## 3. Results at the new prices (n = 5)

### Table 1. Cost, gap and service per lever

| lever | ILP OPT/TL | MIP gap % | ILP end-adj. | best rule end-adj. (rule) | gap vs best rule % | gap vs bound % (upper) | served ILP / rule |
|---|---|---|---|---|---|---|---|
| Reference (1800 s) | 1/4 | 0-2.87 | 1278.7 [1086.9, 1470.6] | 2435.1 [2261.6, 2608.5] (r2 x5) | 47.59 [42.16, 53.03] | 48.26 [42.35, 54.17] | 0.925 / 0.653 |
| Faster chargers | 3/2 | 0-2.66 | 1277.1 [1079.4, 1474.8] | 2125.8 [1777.0, 2474.6] (M2 x3, r2 x2) | 39.84 [38.05, 41.64] | 40.27 [37.93, 42.61] | 0.934 / 0.781 |
| Second swap position | 0/5 | 0.84-7.52 | 1312.2 [1148.2, 1476.2] | 2437.5 [2261.3, 2613.7] (r2 x5) | 46.23 [41.98, 50.48] | 48.36 [42.53, 54.19] | 0.919 / 0.650 |
| Lock-out of 1 spare | 0/5 | 0.41-5.65 | 1290.5 [1100.1, 1480.9] | 2475.8 [2235.6, 2716.1] (r2 x5) | 47.94 [43.06, 52.83] | 49.06 [43.53, 54.59] | 0.922 / 0.631 |
| Lock-out of 2 spares (1800 s) | 1/4 | 0-3.26 | 1288.5 [1093.5, 1483.5] | 2495.2 [2213.3, 2777.0] (r2 x5) | 48.39 [43.34, 53.44] | 49.30 [43.61, 54.99] | 0.925 / 0.625 |
| No on-site charging | 4/1 | 0-0.32 | 1541.7 [1375.7, 1707.7] | 2648.6 [2534.1, 2763.1] (r2 x5) | 41.87 [37.86, 45.88] | 41.95 [37.93, 45.98] | 0.822 / 0.516 |

The gap vs best rule uses incumbents (a lower bound of the true gap where the ILP is time-limited); the gap vs bound
uses the best proven bound and raw totals and bounds the true gap from above. No ILP order is more than 60 min late
in any cell.

### Table 2. Lever effects (lever minus reference, paired per seed)

| lever | ILP change, measured | seeds > 0 | proven bracket of the true ILP change per seed (raw USD) | best-rule change | seeds > 0 | gap change (points) | served-share change ILP / rule (points) |
|---|---|---|---|---|---|---|---|
| Faster chargers | -1.58 [-14.80, 11.63] | 3/5 | [-14.7, 0.9], [4.7, 15.2], [-29.0, 38.3], [-16.6, 3.1], [10.1, 10.1] | **-309.23 [-548.06, -70.40]** (per seed -582.9, -231.8, -404.0, -252.6, -75.0) | 0/5 | -7.75 [-14.04, -1.46] | +0.9 [-0.1, 2.0] / +12.8 [8.6, 17.0] |
| Second swap position | 33.48 [1.98, 64.97] (600 s vs 1800 s reference: time-limit artefact, see item 2; -1.37 [-38.04, 35.31] vs the 600 s reference rows) | 5/5 | [-16.4, 0.12], [-10.4, 0.12], [-35.3, 0.12], [-14.5, 0.12], [-4.1, 0.12] (relaxation plus 0.119 USD set-up) | +2.40 [-3.94, 8.74] (+0.12 set-up on 4 seeds, +11.5 on seed 1) | 5/5 | -1.36 [-2.85, 0.13] | -0.6 [-1.7, 0.4] / -0.3 [-1.2, 0.6] |
| Lock-out of 1 spare | 11.79 [-5.34, 28.92] | 5/5 | [0, 20.6], [0, 22.3], [0, 40.7], [0, 16.9], [0, 2.5] (restriction) | +40.78 [-61.54, 143.09] (per seed -0.40, +187.54, -0.34, +17.42, -0.34) | 2/5 | +0.35 [-1.86, 2.56] | -0.3 [-1.2, 0.6] / -2.2 [-7.2, 2.9] |
| Lock-out of 2 spares | 9.78 [-4.88, 24.43] | 5/5 | [0, 25.3], [0, 41.3], [0, 40.7], [0, 16.9], [2.5, 2.5] (restriction) | +60.11 [-95.75, 215.97] (per seed -0.40, +284.23, -0.34, +17.41, -0.35) | 2/5 | +0.80 [-1.74, 3.34] | 0.0 / -2.8 [-9.6, 4.0] |
| No on-site charging | **+262.96 [216.81, 309.11]** | 5/5 | [301.3, 316.8], [207.7, 218.1], [276.3, 316.1], [280.1, 294.1], [243.2, 243.2]: at least 207.7 on every seed | **+213.51 [123.95, 303.07]** (per seed 289.0, 185.9, 121.9, 185.3, 285.4) | 5/5 | -5.72 [-8.44, -3.01] (5/5 < 0) | -10.3 [-12.5, -8.1] / -13.8 [-16.3, -11.2] |

- **Brackets.** [lever bound - reference incumbent, lever incumbent - reference bound] with raw totals and the best
  bound over both runs of a key; restriction: lower end >= 0; relaxation (second swap position, same orders, same
  batteries, one more position): upper end <= the constant set-up difference, +0.119 USD (raw totals include the
  set-up); nesting of the lock-outs on seeds 2-4 (item 3). The ILP change column is end-adjusted, the brackets are
  raw. Solve status: lever cells at 600 s (faster chargers 3 OPT / 2 TL, second swap position 0 / 5, lock-out of 1
  spare 0 / 5), reference and 2-spare lock-out at 1800 s (1 / 4 each), no on-site charging 4 / 1 (Table 1). The
  reference MIP-gap "noise band" is the mean absolute gap of the reference solves, 15.0 USD (per seed 15.6, 10.4,
  34.9, 14.0, 0). The lock-out and faster-charger deltas lie inside it; the second-swap-position delta exceeds it
  only because of the M 2 solves' own gaps (mean 49.6 USD) at the shorter time limit (600 s against 1800 s).
- **Second swap position.** The ILP uses the second position in the same slot only on seed 3 (2 slots); on the other
  four seeds the peak occupancy of its schedule is 0.5, i.e. it never needs two simultaneous swaps. The coordinated
  schedule spreads swaps so that one position suffices; the proven saving is at most 16.1 USD on average (1.3 % of
  the reference) and at most 4.1 USD on seed 4.
- **ILP vs rule without on-site charging.** The ILP loses 49.4 USD [-48.1, 147.0] more than the rule (not
  distinguishable from zero); round 5 had the ILP losing 288.9 more on seeds 0-2.

### Table 3. Why the rule gains from the faster-charger instance (best rule, mean of seeds 0-4)

| component | best rule, new prices | ILP, new prices |
|---|---|---|
| unserved orders | -492.0 [-653.5, -330.5] (8.2 fewer unserved: 22.2 -> 14.0) | -36.0 [-76.8, 4.8] (0.6 fewer) |
| response | +152.7 [111.1, 194.3] | +22.5 [-1.5, 46.5] |
| lateness | +25.5 [-26.3, 77.3] | +10.3 [0.0, 20.5] |
| travel, electricity, set-up, end adjustment | +4.6 | +1.7 |
| **net** | **-309.2 [-548.1, -70.4]** | **-1.6 [-14.8, 11.6]** |

The rule swaps 13-18 times (reference 9-10), leaves 0-3 bikes stranded by an empty battery (reference 5-7) and sees
63-86 stock-out slot-sites (reference 83-103): the 1-h pack turnaround repairs the rule's stock-outs. The best rule
switches to M2 on seeds 0, 1, 4 (M2 beats r2 by 118.6, 12.3 and 29.0 USD there). Per extra served order the rule
pays 6.6-44.2 USD of response and lateness against the 60 USD penalty saved. The ILP, which already serves 92.5 %,
has nothing to repair; it swaps more (15-17 vs 11-13) under the coarser rounding (about 10-12 % more modelled
energy per delivery arc, item 1), at a cost within its MIP gaps.

### Table 4. Site power cap and the demand-charge proxy (P_j in {0, p_ch}; with one charger per site the cap p_ch = 0.333 kW is not binding, so the reference is the p_ch point)

| seed | P0 / reference status | V(P0) - V(p_ch), ILP (raw USD) | proven lower bound | break-even tariff, ILP (USD per kW-month, >=) | V(P0) - V(p_ch), best rule | break-even, rule |
|---|---|---|---|---|---|---|
| 0 | OPT / TL | 301.3 | 301.3 | 36,151 | 288.5 | 34,619 |
| 1 | OPT / TL | 207.7 | 207.7 | 24,926 | 185.6 | 22,267 |
| 2 | TL / TL | 281.1 | 276.3 | 33,161 | 121.3 | 14,553 |
| 3 | OPT / TL | 280.1 | 280.1 | 33,618 | 184.7 | 22,167 |
| 4 | OPT / OPT | 243.2 | 243.2 | 29,184 | 284.8 | 34,182 |

Break-even = (V(P0) - V(p_ch)) / (3 sites x 0.333 kW) x 120 windows per month, using the P0 bound and the reference
incumbent (a lower bound of the true difference). At the assumed 10, 25 and 40 USD per kW-month the demand charge
at cap p_ch is 0.083, 0.208 and 0.333 USD per window; the ILP and the rule keep on-site charging on every seed at
every tariff. Legacy prices (seeds 0-2): ILP 11,753, 6,217, 10,552; the rule then preferred P0 at any tariff
(artefact of the cheap drop, Section 4).

## 4. Comparison with the legacy prices (round 5, seeds 0-2, ILP 300 s)

Same demand hashes and lock-out slots. The legacy ILP is the round-5 300 s row; the legacy rule rows on seeds 3-4
reprice the new-price rows (item 8). "s012" = seeds 0-2 paired on the records; "s01234" = seeds 0-4 with repriced
rule rows.

| lever | quantity | legacy prices (P 30, v 36) | new prices (P 60, v 15) | new - legacy (paired) |
|---|---|---|---|---|
| Faster chargers | ILP change, s012 | -5.22 [-14.95, 4.52] (3 OPT; brackets [-0.8, -0.7], [-6.1, 7.4], [-8.2, 6.3]) | -2.26 [-29.19, 24.66] | +2.95 [-33.34, 39.24] |
| | best-rule change, s012 | -141.38 [-510.85, 228.09] | -406.21 [-842.43, 30.00] | -264.83 [-341.88, -187.79] |
| | best-rule change, s01234 | -41.26 [-262.22, 179.70] (repriced; 2/5 > 0) | -309.23 [-548.06, -70.40] (0/5 > 0) | -267.97 [-305.38, -230.56] |
| | rule served-share change, s012 | +14.6 [3.4, 25.8] points | +14.6 [8.7, 20.5] points | 0 (identical schedules) |
| | gap, s012 | 41.37 [26.33, 56.41] | 39.65 [35.51, 43.79] | -1.72 [-14.03, 10.59] |
| Second swap position | ILP change, s012 | -2.19 [-11.40, 7.02] (brackets [0.03, 0.12], [-12.8, 0.12], [-14.4, 0.12]) | +39.37 [-45.11, 123.86] (time-limit artefact) | not interpretable |
| | best-rule change, s01234 | -11.95 [-34.08, 10.17] (repriced) | +2.40 [-3.94, 8.74] | +14.36 [-13.42, 42.14] |
| | gap, s012 | 45.44 [42.32, 48.56] | 48.34 [42.01, 54.66] | +2.90 [-3.75, 9.55] |
| Lock-out of 1 spare | ILP change, s012 | -2.17 [-12.79, 8.45] (brackets [0, 3.2], [0, 10.8], [0, 9.4]) | +17.16 [-23.61, 57.93] (brackets [0, 20.6], [0, 22.3], [0, 40.7]) | not interpretable |
| | best-rule change, s01234 | -27.40 [-47.32, -7.48] (repriced; 0/5 > 0) | +40.78 [-61.54, 143.09] (2/5 > 0) | +68.18 [-45.37, 181.72] |
| | gap, s012 | 45.29 [44.05, 46.54] | 50.50 [44.42, 56.58] | +5.21 [-1.18, 11.60] |
| Lock-out of 2 spares | ILP change, s012 | -2.60 [-10.62, 5.42] (brackets [0, 1.4], [0, 11.1], [0, 9.5]) | +14.83 [-18.77, 48.43] (brackets [0, 25.3], [0, 41.3], [0, 40.7]) | not interpretable |
| | best-rule change, s01234 | -31.10 [-57.59, -4.60] (repriced; 0/5 > 0) | +60.11 [-95.75, 215.97] (2/5 > 0) | +91.21 [-85.60, 268.01] |
| | gap, s012 | 45.15 [43.32, 46.98] | 51.21 [46.98, 55.43] | +6.06 [2.09, 10.02] |
| No on-site charging | ILP change, s012 | +79.45 [19.20, 139.70] | +263.62 [141.48, 385.77] | +184.18 [122.28, 246.07] |
| | best-rule change, s01234 | -238.93 [-380.94, -96.91] (repriced; 0/5 > 0) | +213.51 [123.95, 303.07] (5/5 > 0) | +452.44 [325.43, 579.44] |
| | gap, s012 | 34.90 [31.26, 38.54] | 43.60 [36.43, 50.77] | +8.70 [2.23, 15.17] |
| | gap change, s012 / s01234 | -10.99 [-14.50, -7.48] | -6.34 [-12.09, -0.59] / -5.72 [-8.44, -3.01] | +4.65 (s012) |
| Reference | gap, s012 | 45.89 [44.28, 47.50] (1 OPT, 2 TL at 1.20-1.37 %) | 49.94 [39.57, 60.31] (3 TL at 0.75-2.87 %, 1800 s) | +4.05 [-6.83, 14.93] |
| | best rule | r2, r2, M2 | r2 x3 | - |

- The legacy lever table (round 5, `r5_x5_stress/RESULTS_final.md` Section 4) reads, for the ILP, -5.0, -2.2, -1.5,
  -2.0 and +79.2 USD "within the 9.3 USD MIP gap"; for the rule -141.0, -19.9, -25.6, -31.7 and -209.8 USD, none
  significant at n = 3. The new-price table keeps the ILP ordering (only on-site charging matters; the other four
  within tolerance, now with proven ceilings of 2.5-41 USD per seed) and reverses the rule's sign on the lock-outs
  and on on-site charging: at the legacy prices dropping an order saved the rule about 47 USD of response and
  lateness against a 30 USD penalty, so losing batteries or charging "paid"; at the new prices it saves 35 USD
  against 60 and every restriction costs. The faster-charger gain of the rule survives both price sets, with
  identical schedules (+14.6 served points on seeds 0-2 under both), and is 265 USD larger at the new prices because
  the extra served orders are worth 60 instead of 30 USD each.
- The legacy ILP deltas for the second swap position and the lock-outs were already "solver noise" in round 5; the
  new brackets are wider (600 s against the 1800 s reference) but say the same thing with a ceiling.

## 5. Interpretation

**Shown by the records**

- On-site charging is the only station lever with a material effect on the coordinated schedule: removing it
  costs at least 207.7 USD on every seed (proven), +263.0 [216.8, 309.1] measured, about 21 % of the reference,
  and 10.3 served points; the rule loses 213.5 and 13.8 points. A demand charge would have to exceed 24,900 USD per
  kW-month before giving up on-site charging paid.
- A second swap position is worth at most 4-35 USD per window to the coordinated schedule (proven; 16 USD on
  average, 1.3 %), and can cost it at most its 0.12 USD set-up, because the ILP spreads swaps so that two never
  coincide on 4 of 5 seeds. For the rule it is worth nothing (+0.12 USD set-up).
- Losing one or two of the six spares in the dinner peak costs the coordinated schedule at most 2.5-41 USD per seed
  (proven), exactly 2.5 USD on seed 4; the rule is unaffected unless the lock-out falls at 17:05 (seed 1: +187.5 /
  +284.2 USD, 6-8 more dropped orders).
- The faster-charger instance (50 Wh levels) leaves the ILP cost within -14.7 to +38.3 USD of the reference (3 seeds
  undetermined, 2 seeds slightly dearer, +4.7-15.2 and +10.1) and lowers the rule's cost by 309 USD [70, 548]
  (5/5), with 12.8 more served points. With it the gap falls from 47.6 to 39.8 % (-7.8 points [-14.0, -1.5]).
- The sign reversal of the rule's lever responses against round 5 is a pricing effect on identical schedules
  (60 shared rule rows repriced to 4.6e-13 USD), not a behavioural one.

**Not shown (solver or design limits)**

- The exact ILP cost of the lock-outs and of the second swap position (brackets of 17-41 USD on 4 seeds; a 1800 s
  retry of the 12 time-limited levers_ext rows would narrow them).
- The effect of faster chargers at an unchanged energy rounding: the current lever confounds charger power with the
  energy discretisation (item 1; about 10-12 % more modelled energy per delivery arc). The rule's gain is real for
  the instance as built; whether it survives at the 25 Wh rounding is not tested, and the records do not say how much
  of the x1.8-2.1 rise in purchased energy the rounding causes.
- Whether the levers interact (each was varied alone).

**Suggested, not tested**

- The rule's faster-charger gain comes from stock-out repair (stranded bikes 5-7 -> 0-3), so a charger upgrade is a
  station lever that helps uncoordinated fleets and not coordinated ones; the coordination gap would shrink by about
  8 points if operators bought it. The ILP's indifference suggests that its reference schedules are not
  charger-limited at 8 bikes and 2 spares per site, consistent with the small second-spare values of the fleet grid.
- The second-swap-position result suggests that queueing at the swap position is a rule problem, not a system one.

## 6. Manuscript items replaced (`manuscript/PENDING_R6.md`)

- **Item 9** (station levers "chargers twice as fast", "second swap position", "lock-out of one spare" at the legacy
  prices, n 3, 300 s; the legacy rule schedules without on-site charging; the unresolved 2-spare lock-out needing a
  warm-started reference). Replaced by this stage and the levers retry:
  - Table tab:res:levers, calibrated block (seeds 0-4, n 5): Reference, gap 47.6 (42.2-53.0)^a, 0.92 / 0.65, 1/4
    (1800 s). Faster chargers (50 Wh levels), ILP -1.6 (-14.8 to 11.6)^b, rule -309.2 (-548.1 to -70.4), gap 39.8
    (38.1-41.6), 0.93 / 0.78, 3/2. Second swap position, ILP saving at most 4.1 to 35.3 per seed, increase at most
    0.12 (measured +33.5 at 600 s against the 1800 s reference, a time-limit artefact)^b, rule +2.4 (-3.9 to 8.7),
    gap 46.2 (42.0-50.5), 0.92 / 0.65, 0/5. Lock-out of 1 spare, ILP 0 to 2.5-40.7
    per seed (measured +11.8)^b, rule +40.8 (-61.5 to 143.1), gap 47.9 (43.1-52.8), 0.92 / 0.63, 0/5. Lock-out of 2
    spares, ILP 0 to 16.9-41.3 per seed, exactly +2.5 on seed 4 (measured +9.8)^b, rule +60.1 (-95.8 to 216.0), gap
    48.4 (43.3-53.4), 0.92 / 0.63, 1/4 (1800 s). No on-site charging, ILP +263.0 (216.8-309.1; at least 207.7 on
    every seed), rule +213.5 (124.0-303.1), gap 41.9 (37.9-45.9), 0.82 / 0.52, 4/1. Footnote a: lower bound; at
    most 48.3 % against the proven bounds; mean MIP gap of the reference solves 15 USD (was 51). Footnote b: proven
    bracket [lever bound - reference incumbent, lever incumbent - reference bound] on raw totals; a restriction cannot
    lower the optimum, and the second swap position, a relaxation with a constant set-up of +0.119 USD, cannot raise
    it by more than 0.12 USD. The legacy block (seeds 0-2) stays as the sensitivity case.
  - 6.6 levers paragraph: "On stress4h-K8 (seeds 0-4, relaxed targets; reference and 2-spare lock-out solved 1800 s,
    the other levers 600 s), removing on-site charging costs the ILP 263.0 USD per window (216.8-309.1; at least
    207.7 USD on every seed by the proven bounds; four of five solves optimal), about 21 % of its cost, and the best
    rule 213.5 USD (124.0-303.1, dearer on 5 of 5 seeds); giving up on-site charging would pay only at a demand charge
    of at least about 24,900 USD per kW-month. The other levers stay within the solver gaps for the ILP, and the
    bounds give their ceilings: a second swap position saves at most 4-35 USD per seed (16 USD on average), and
    locking out one or two of the six spares in the dinner peak costs at most 2.5-41 USD (exactly 2.5 USD on one
    seed). Chargers twice as fast, represented by 50 Wh levels on the same pack (a charger advances one 50 Wh level
    per slot; route energies are rounded up to the coarser levels, about 10-12 % more modelled energy per delivery),
    leave the ILP cost within -15 to +38 USD of the reference
    but lower the best rule's cost by 309 USD (70-548; cheaper on 5 of 5 seeds) and raise its served share by 12.8
    points, because the one-hour pack turnaround repairs the rule's stock-outs; the gap falls to 39.8 %."
  - S8.4: the lever definition sentence becomes "Faster charging was represented by a level size of eps = 50 Wh
    (L = 12) on the same 0.6 kWh pack, so that a charger still advances one level per slot but draws 0.667 kW and
    a full charge takes one hour instead of two. Routes, route energies, the pack, the 50 Wh reserve and the orders
    are unchanged; only the energies are rounded up to the coarser levels (restaurant-to-customer legs take 1-3
    levels of 50 Wh instead of 1-5 of 25 Wh), which raises the modelled energy of a delivery by about 10-12 %. The
    lever therefore combines faster charging with a coarser, conservative energy rounding. Purchased energy rises
    by a factor 1.76 (1.48-2.05) for the ILP and 2.10 (1.89-2.31) for the best rule, together with more swaps (ILP
    15-17 instead of 11-13); the runs do not separate the contributions." The
    "Reference and solve status" paragraph: "one of five reference solves optimal within 1800 s (MIP gaps 0.75-2.87 %,
    0-34.9 USD, mean 15 USD), warm-started from the 2-spare lock-out incumbent; every lock-out incumbent lies above
    its reference incumbent, so no reference incumbent is provably sub-optimal". The "Lock-out of two spares"
    paragraph: "the measured change of +9.8 USD (-4.9 to 24.4) is positive on 5 of 5 seeds, as a restriction
    requires; the proven brackets are [0, 25.3], [0, 41.3], [0, 40.7], [0, 16.9] and [2.5, 2.5] USD; the lock-out of
    one spare gives +11.8 USD (-5.3 to 28.9) with brackets [0, 20.6], [0, 22.3], [0, 40.7], [0, 16.9] and [0, 2.5]".
    The "Other levers (legacy prices)" paragraph is replaced by the calibrated results above and the legacy values
    (-5.0, -2.2, -1.5, -2.0 USD; rule -141.0, -19.9, -25.6, -31.7) move to the sensitivity sentence.
  - 7.1: "Among the station levers, on-site charging is the one the coordinator needs: removing it cost the ILP 263.0
    USD per window (216.8-309.1, n = 5; at least 207.7 USD on every seed) and the best rule 213.5 USD; a second swap
    position and the lock-out of one or two spares are worth at most 4-41 USD per window to the coordinated schedule
    (proven bounds; a second position can raise its cost by at most its 0.12 USD set-up), and chargers twice as fast
    (with energy rounded to 50 Wh levels) change its cost by less than 40 USD while they lower the rule's by 309
    USD."
  - Figures: `fig_r6_levers_ext_effects` replaces fig:app:levers (caption: grey band 15 USD, bracket bars; new prices
    n 5, legacy n 3); `fig_r6_levers_ext_service_demand` (a) replaces panel (a) of fig:app:levers-mechanism with six
    cells; `fig_r6_levers_ext_brackets` is a new supplement figure if wanted. Panel (b) of fig:app:levers-mechanism
    (rule decomposition without on-site charging at both price sets) is unchanged.
  - The legacy statement "at the legacy prices the same rule schedules were 238.9 USD cheaper without on-site
    charging" stands (repriced value -238.93 [-380.94, -96.91], 5/5, re-verified on 60 rows).
- **Item 16**, levers part ("levers reference (0 of 5 optimal at 600 s, up to 10.48 %; three incumbents provably
  sub-optimal)"): replaced by "levers reference re-solved at 1800 s from the lock-out incumbent: 1 of 5 optimal,
  MIP gaps 0.75-2.87 %, no incumbent provably sub-optimal; 2-spare lock-out 1 of 5 optimal, 1.05-3.26 %; no on-site
  charging seed 2 at 0.32 %". The S12 coverage row and S13.5 sentence for the levers change accordingly; the
  dependent values (reference 1278.7 USD, gap 47.6 % lower bound / 48.3 % upper, +263.0 USD, 24,900 USD per
  kW-month) replace 1313.6, 46.1 / 48.3, +228.5 and 20,400 in 6.6, 7.1, S8.4, S12 and Table tab:res:levers; the
  digest rows 10, 31, 73, 74, 75 of R6_DIGEST.md need the same update.
- **Item 15**, levers rows: Table tab:app:coverage gains the three levers at the calibrated prices (stress4h-K8,
  seeds 0-4, 600 s; 75 records, 3 OPT + 12 TL as in Section 2); the stress4h-K8 row of Table tab:app:coverage-legacy
  and the S4 row "chargers twice as fast, second swap position, lock-out of 1 and 2 spares, no on-site charging,
  seeds 0-2, 300 s, legacy" remain as the sensitivity run.
- No other PENDING_R6 item is affected. Item 7's recovery rows and item 5's K10 cells are not touched by this stage.

## Figures (`figs/`, PDF vector + PNG 300 dpi, Okabe-Ito colours, no internal codes)

- `fig_r6_levers_ext_effects`: change in end-adjusted cost against the reference for (a) the ILP and (b) the best
  rule, five levers; new prices (n 5, filled) and legacy prices (n 3, open), mean with exact-t 95 % CI, seeds as
  dots; in (a) the light-blue bar is the pooled proven range of the true ILP change over the seeds and the grey band
  the mean MIP gap of the new-price reference (15 USD).
- `fig_r6_levers_ext_brackets`: per lever and seed, the proven bracket of the true ILP change and the measured
  change (filled = lever solve optimal, open = time-limited), new prices.
- `fig_r6_levers_ext_service_demand`: (a) served share per lever, ILP vs best rule, new prices (n 5); (b) break-even
  demand charge per seed (proven lower bound) at both price sets against the assumed 10-40 USD per kW-month band.
- Data next to the figures: `levers_ext_per_instance_final.csv` (new prices, 30 rows), `levers_ext_per_instance_legacy_final.csv`
  (18 rows), `levers_ext_summary_final.csv`, `levers_ext_cross_round_final.csv`, `levers_ext_demand_charge_final.csv`.
  Script: `make_levers_ext_figs.py` (prints every table above, including the repricing check);
  `check_eps50_energy.py` (rebuilds the 25 / 50 Wh instances and prints the leg and arc energy levels of item 1).

## Appendix. Per-instance results

New prices. ILP columns are the row used (retried where it exists); the bracket is the proven range of the true ILP
change (raw totals). Changes are lever minus reference (end-adjusted).

| lever | seed | ILP status | MIP gap % | abs gap USD | limit s | ILP raw | ILP bound | ILP end-adj. | best rule | best rule end-adj. | gap % | gap vs bound % | served ILP / rule | unserved ILP / rule | ILP change | bracket | rule change |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reference | 0 | TL | 1.50 | 15.55 | 1800 | 1037.94 | 1022.39 | 1040.18 | r2 | 2236.43 | 53.49 | 54.25 | 0.984 / 0.688 | 1 / 20 | - | - | - |
| Reference | 1 | TL | 0.75 | 10.39 | 1800 | 1386.87 | 1376.49 | 1388.97 | r2 | 2541.11 | 45.34 | 45.79 | 0.891 / 0.625 | 7 / 24 | - | - | - |
| Reference | 2 | TL | 2.87 | 34.91 | 1800 | 1215.46 | 1180.55 | 1217.50 | r2 | 2484.05 | 50.99 | 52.45 | 0.922 / 0.625 | 5 / 24 | - | - | - |
| Reference | 3 | TL | 1.00 | 13.98 | 1800 | 1419.99 | 1406.01 | 1422.01 | r2 | 2566.33 | 44.59 | 45.18 | 0.891 / 0.672 | 7 / 21 | - | - | - |
| Reference | 4 | OPT | 0 | 0 | 1800 | 1322.79 | 1322.79 | 1324.93 | r2 | 2347.36 | 43.56 | 43.61 | 0.938 / 0.656 | 4 / 22 | - | - | - |
| Faster chargers | 0 | OPT | 0 | 0 | 600 | 1023.28 | 1023.28 | 1025.44 | M2 | 1653.50 | 37.98 | 38.08 | 1.000 / 0.859 | 0 / 9 | -14.74 | [-14.7, 0.9] | -582.93 |
| Faster chargers | 1 | OPT | 0.01 | 0.14 | 600 | 1391.73 | 1391.59 | 1393.77 | M2 | 2309.37 | 39.65 | 39.71 | 0.891 / 0.750 | 7 / 16 | +4.80 | [4.7, 15.2] | -231.75 |
| Faster chargers | 2 | TL | 2.66 | 32.40 | 600 | 1218.84 | 1186.44 | 1220.66 | r2 | 2080.09 | 41.32 | 42.93 | 0.938 / 0.766 | 4 / 15 | +3.16 | [-29.0, 38.3] | -403.96 |
| Faster chargers | 3 | TL | 0.41 | 5.71 | 600 | 1409.15 | 1403.44 | 1411.09 | r2 | 2313.75 | 39.01 | 39.31 | 0.906 / 0.797 | 6 / 13 | -10.93 | [-16.6, 3.1] | -252.57 |
| Faster chargers | 4 | OPT | 0 | 0 | 600 | 1332.85 | 1332.85 | 1334.72 | M2 | 2272.42 | 41.26 | 41.33 | 0.938 / 0.734 | 4 / 17 | +9.79 | [10.1, 10.1] | -74.95 |
| Second swap position | 0 | TL | 7.52 | 83.12 | 600 | 1104.67 | 1021.55 | 1106.81 | r2 | 2236.55 | 50.51 | 54.29 | 0.969 / 0.688 | 2 / 20 | +66.62 | [-16.4, 0.12] | +0.12 |
| Second swap position | 1 | TL | 0.84 | 11.66 | 600 | 1388.14 | 1376.48 | 1390.23 | r2 | 2552.65 | 45.54 | 46.04 | 0.891 / 0.609 | 7 / 25 | +1.26 | [-10.4, 0.12] | +11.54 |
| Second swap position | 2 | TL | 6.76 | 85.51 | 600 | 1265.68 | 1180.16 | 1267.73 | r2 | 2484.17 | 48.97 | 52.47 | 0.922 / 0.625 | 5 / 24 | +50.23 | [-35.3, 0.12] | +0.12 |
| Second swap position | 3 | TL | 2.72 | 39.29 | 600 | 1444.80 | 1405.51 | 1446.78 | r2 | 2566.44 | 43.63 | 45.21 | 0.891 / 0.672 | 7 / 21 | +24.76 | [-14.5, 0.12] | +0.12 |
| Second swap position | 4 | TL | 2.12 | 28.61 | 600 | 1347.32 | 1318.71 | 1349.44 | r2 | 2347.48 | 42.52 | 43.79 | 0.922 / 0.656 | 5 / 22 | +24.51 | [-4.1, 0.12] | +0.12 |
| Lock-out of 1 spare | 0 | TL | 1.91 | 19.87 | 600 | 1042.96 | 1023.08 | 1044.59 | r2 | 2236.03 | 53.28 | 54.22 | 0.984 / 0.688 | 1 / 20 | +4.40 | [0, 20.6] | -0.40 |
| Lock-out of 1 spare | 1 | TL | 1.38 | 19.36 | 600 | 1398.80 | 1379.44 | 1400.38 | r2 | 2728.65 | 48.68 | 49.43 | 0.875 / 0.531 | 8 / 30 | +11.41 | [0, 22.3] | +187.54 |
| Lock-out of 1 spare | 2 | TL | 5.65 | 70.72 | 600 | 1251.61 | 1180.89 | 1253.17 | r2 | 2483.71 | 49.54 | 52.44 | 0.922 / 0.625 | 5 / 24 | +35.68 | [0, 40.7] | -0.34 |
| Lock-out of 1 spare | 3 | TL | 1.26 | 17.96 | 600 | 1425.99 | 1408.04 | 1427.52 | r2 | 2583.74 | 44.75 | 45.48 | 0.891 / 0.656 | 7 / 22 | +5.51 | [0, 16.9] | +17.42 |
| Lock-out of 1 spare | 4 | TL | 0.41 | 5.38 | 600 | 1325.32 | 1319.94 | 1326.89 | r2 | 2347.02 | 43.46 | 43.74 | 0.938 / 0.656 | 4 / 22 | +1.96 | [0, 2.5] | -0.34 |
| Lock-out of 2 spares | 0 | TL | 2.20 | 23.04 | 1800 | 1047.68 | 1024.63 | 1049.08 | r2 | 2236.03 | 53.08 | 54.15 | 0.984 / 0.688 | 1 / 20 | +8.89 | [0, 25.3] | -0.40 |
| Lock-out of 2 spares | 1 | TL | 2.23 | 31.65 | 1800 | 1417.75 | 1386.10 | 1419.28 | r2 | 2825.35 | 49.77 | 50.93 | 0.891 / 0.500 | 7 / 32 | +30.31 | [0, 41.3] | +284.23 |
| Lock-out of 2 spares | 2 | TL | 3.26 | 39.77 | 1800 | 1221.24 | 1181.47 | 1222.78 | r2 | 2483.71 | 50.77 | 52.41 | 0.922 / 0.625 | 5 / 24 | +5.29 | [0, 40.7] | -0.34 |
| Lock-out of 2 spares | 3 | TL | 1.05 | 14.91 | 1800 | 1422.91 | 1407.99 | 1424.44 | r2 | 2583.74 | 44.87 | 45.48 | 0.891 / 0.656 | 7 / 22 | +2.42 | [0, 16.9] | +17.41 |
| Lock-out of 2 spares | 4 | OPT | 0 | 0 | 1800 | 1325.32 | 1325.32 | 1326.92 | r2 | 2347.02 | 43.46 | 43.51 | 0.938 / 0.656 | 4 / 22 | +1.99 | [2.5, 2.5] | -0.35 |
| No on-site charging | 0 | OPT | 0 | 0 | 600 | 1339.20 | 1339.20 | 1341.61 | r2 | 2525.39 | 46.87 | 46.93 | 0.875 / 0.547 | 8 / 29 | +301.43 | [301.3, 316.8] | +288.96 |
| No on-site charging | 1 | OPT | 0 | 0 | 600 | 1594.59 | 1594.59 | 1597.01 | r2 | 2727.06 | 41.44 | 41.48 | 0.812 / 0.500 | 12 / 32 | +208.04 | [207.7, 218.1] | +185.94 |
| No on-site charging | 2 | TL | 0.32 | 4.81 | 1800 | 1496.61 | 1491.80 | 1498.90 | r2 | 2605.96 | 42.48 | 42.71 | 0.828 / 0.516 | 11 / 31 | +281.41 | [276.3, 316.1] | +121.91 |
| No on-site charging | 3 | OPT | 0 | 0 | 600 | 1700.14 | 1700.14 | 1702.51 | r2 | 2751.64 | 38.13 | 38.17 | 0.766 / 0.516 | 15 / 31 | +280.49 | [280.1, 294.1] | +185.31 |
| No on-site charging | 4 | OPT | 0 | 0 | 600 | 1565.99 | 1565.99 | 1568.35 | r2 | 2632.79 | 40.43 | 40.48 | 0.828 / 0.500 | 11 / 32 | +243.42 | [243.2, 243.2] | +285.42 |

Lock-out positions (site, slot, clock): 1 spare: (S2, 19, 17:35), (S3, 13, 17:05), (S3, 18, 17:30), (S2, 17, 17:25),
(S2, 13, 17:05); 2 spares: (S2, 16, 17:20) + (S3, 19, 17:35); (S3, 12, 17:00) + (S1, 13, 17:05); (S3, 18, 17:30) +
(S1, 21, 17:45); (S2, 17, 17:25) + (S3, 22, 17:50); (S2, 13, 17:05) + (S1, 22, 17:50).

Legacy prices (round 5, seeds 0-2, ILP 300 s; best rule recomputed on end-adjusted totals).

| lever | seed | ILP status | MIP gap % | ILP raw | ILP bound | ILP end-adj. | best rule | best rule end-adj. | gap % | served ILP / rule | ILP change | bracket | rule change |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reference | 0 | OPT | 0 | 991.31 | 991.31 | 993.49 | r2 | 1814.93 | 45.26 | 0.969 / 0.688 | - | - | - |
| Reference | 1 | TL | 1.20 | 1125.14 | 1111.69 | 1127.35 | r2 | 2081.86 | 45.85 | 0.812 / 0.625 | - | - | - |
| Reference | 2 | TL | 1.37 | 1059.26 | 1044.71 | 1061.31 | M2 | 1985.88 | 46.56 | 0.891 / 0.594 | - | - | - |
| Faster chargers | 0 | OPT | 0.01 | 990.58 | 990.53 | 992.66 | M2 | 1516.50 | 34.54 | 0.969 / 0.859 | -0.83 | [-0.8, -0.7] | -298.43 |
| Faster chargers | 1 | OPT | 0.00 | 1119.09 | 1119.07 | 1120.91 | r2 | 2079.20 | 46.09 | 0.828 / 0.719 | -6.44 | [-6.1, 7.4] | -2.67 |
| Faster chargers | 2 | OPT | 0.00 | 1051.04 | 1051.03 | 1052.93 | r2 | 1862.84 | 43.48 | 0.891 / 0.766 | -8.38 | [-8.2, 6.3] | -123.04 |
| Second swap position | 0 | OPT | 0.01 | 991.43 | 991.33 | 993.61 | M2 | 1794.27 | 44.62 | 0.969 / 0.641 | +0.12 | [0.03, 0.12] | -20.66 |
| Second swap position | 1 | TL | 1.13 | 1124.95 | 1112.29 | 1127.12 | r2 | 2042.40 | 44.81 | 0.812 / 0.609 | -0.22 | [-12.8, 0.12] | -39.46 |
| Second swap position | 2 | TL | 0.76 | 1052.86 | 1044.86 | 1054.85 | M2 | 1985.99 | 46.89 | 0.891 / 0.594 | -6.46 | [-14.4, 0.12] | +0.12 |
| Lock-out of 1 spare | 0 | TL | 0.39 | 994.50 | 990.59 | 996.06 | r2 | 1814.53 | 45.11 | 0.953 / 0.688 | +2.57 | [0, 3.2] | -0.40 |
| Lock-out of 1 spare | 1 | TL | 0.89 | 1122.46 | 1112.48 | 1123.99 | r2 | 2040.40 | 44.91 | 0.812 / 0.531 | -3.35 | [0, 10.8] | -41.46 |
| Lock-out of 1 spare | 2 | TL | 0.85 | 1054.10 | 1045.12 | 1055.58 | M2 | 1949.71 | 45.86 | 0.891 / 0.578 | -5.73 | [0, 9.4] | -36.16 |
| Lock-out of 2 spares | 0 | TL | 0.14 | 992.66 | 991.23 | 994.28 | r2 | 1814.53 | 45.20 | 0.969 / 0.688 | +0.78 | [0, 1.4] | -0.40 |
| Lock-out of 2 spares | 1 | TL | 0.82 | 1122.83 | 1113.60 | 1124.42 | M2 | 2021.93 | 44.39 | 0.812 / 0.438 | -2.93 | [0, 11.1] | -59.93 |
| Lock-out of 2 spares | 2 | TL | 0.67 | 1054.19 | 1047.12 | 1055.66 | M2 | 1949.71 | 45.86 | 0.891 / 0.578 | -5.65 | [0, 9.5] | -36.16 |
| No on-site charging | 0 | OPT | 0 | 1089.25 | 1089.25 | 1091.65 | M2 | 1688.58 | 35.35 | 0.859 / 0.453 | +98.16 | [97.9, 97.9] | -126.35 |
| No on-site charging | 1 | OPT | 0 | 1176.95 | 1176.95 | 1179.39 | M2 | 1767.18 | 33.26 | 0.766 / 0.375 | +52.05 | [51.8, 65.3] | -314.68 |
| No on-site charging | 2 | OPT | 0 | 1147.19 | 1147.19 | 1149.45 | r2 | 1798.46 | 36.09 | 0.797 / 0.516 | +88.14 | [87.9, 102.5] | -187.42 |

Repriced legacy rule costs on seeds 3-4 (end-adjusted USD, r2 / M2; M2+M3 = M2 everywhere; the lower one is the
legacy best rule, column `best_ea_old_repriced` of `levers_ext_per_instance_final.csv`): reference 2291.58 / 2325.41
(seed 3), 1885.11 / 1880.27 (seed 4); faster chargers 2340.25 / 2385.98, 2092.36 / 2049.42; second swap position
2291.69 / 2342.88, 1885.23 / 1880.39; lock-out of 1 spare 2264.99 / 2325.12, 1884.77 / 1847.88; lock-out of 2 spares
2264.99 / 2284.37, 1884.77 / 1847.87; no on-site charging 2019.39 / 1891.52, 1779.54 / 1714.14. At the legacy prices
the faster-charger instance is dearer for the rule on seeds 3-4 (+48.7 and +169.2 USD), which is why the repriced
five-seed effect (-41.3) is so much smaller than the new-price one (-309.2): the extra served orders are worth 30 USD
there and 60 USD here, while the extra response and lateness cost the same.

## Verification corrections (2026-10-20)

Two claims were refuted by both refuters. Each was recomputed from `records.jsonl` / `cases.jsonl` of this stage and
of `r6_penalty/levers` (last row per key; no `retry_worse` rows exist) and, for C3, from instances rebuilt with
`generator.charger_speed_variants('r5_stress4h', n_bikes=8)` (demand hashes equal to the records on all 5 seeds at
both level sizes; no solve). Stress4h-K8, relaxed targets, new prices, n = 5 (seeds 0-4), exact Student-t 95 % CIs.

**C2. "The second swap position cannot raise the ILP optimum; its proven saving is at most 16.4, 10.4, 35.3, 14.5
and 4.1 USD on seeds 0-4 (raw totals), although the measured change is +33.48 [1.98, 64.97] and positive on 5/5."**

- Verdicts: refuter 1 refuted, refuter 2 refuted. Corrector: both are right; the claim is partly wrong.
- Reproduced: the saving ceilings (reference 1800 s incumbent minus M2 bound: 16.390, 10.395, 35.295, 14.476,
  4.087; mean 16.13), 5/5 positive, +33.48 [1.98, 64.97].
- Wrong: (a) "cannot raise the optimum". M_j enters the ILP only as the right-hand side of (22) (`ilp.py` line 544),
  but every M2 row carries C_setup 38.4466 against 38.328 for the reference (+0.1186 USD, a constant with fixed
  facilities), and the raw total includes C_setup. So the M2 optimum can be up to 0.12 USD above the reference
  optimum, and the upper end of each bracket is +0.12, not 0. (b) +33.48 [1.98, 64.97] is the end-adjusted change;
  the raw change is +33.51 [1.98, 65.04] (per seed 66.74, 1.27, 50.22, 24.81, 24.52). (c) The comparison has unequal
  time limits: M2 at 600 s (0 OPT, 5 TL at 7.52, 0.84, 6.76, 2.72, 2.12 %) against the 1800 s reference retry (1 OPT,
  4 TL at 1.50, 0.75, 2.87, 1.00 %). Against the original 600 s reference rows (5 TL, 0.83-10.48 %) the change is
  -1.37 [-38.04, 35.31] end-adjusted (-1.36 [-38.01, 35.30] raw), positive on 4/5.
- Changed: the bracket cap in `figs/make_levers_ext_figs.py` (`add_deltas`) is now the lever-minus-reference
  set-up difference instead of 0, for both price sets. New-price brackets [-16.4, 0.12], [-10.4, 0.12], [-35.3,
  0.12], [-14.5, 0.12], [-4.1, 0.12]. Legacy brackets [0.03, 0.12], [-12.8, 0.12], [-14.4, 0.12]; the old legacy
  seed-0 bracket "[0, 0]" was in fact empty (lower end 0.026 above the cap 0). Text corrected in Answer in brief,
  item 2, Table 2 and its notes, Section 4, Section 5, Section 6 (table footnote b, 7.1) and the appendix. CSVs
  (`d_ilp_hi`, `d_ilp_resolved`, `brackets`, `bracket_hi_max`, `brackets_legacy_s012`) and the figures
  `fig_r6_levers_ext_effects` and `fig_r6_levers_ext_brackets` were regenerated; only the second-swap-position
  upper ends moved (by 0.12 USD, not visible at figure scale). The script now prints the M2 change against both
  reference runs. No other number changed (diff of all five CSVs against the pre-correction copies).

**C3. "Under eps 50 Wh every order leg still costs exactly one energy level (hd = hp = 1 on all 64 orders, seeds
0-4), so the pack range halves in legs and the physical energy per leg doubles; purchased energy rises x1.76 [1.48,
2.05] for the ILP and x2.10 [1.89, 2.31] for the best rule."**

- Verdicts: refuter 1 refuted, refuter 2 refuted. Corrector: both are right; the mechanism is false, the ratios
  stand.
- Reproduced: ILP kWh 3.333, 4.278, 5.500, 4.944, 5.222 against 2.361, 2.389, 2.694, 2.667, 3.028 (per-seed ratios
  1.41, 1.79, 2.04, 1.85, 1.73; x1.76 [1.48, 2.05]); best rule 6.778, 6.778, 5.556, 5.889, 6.278 against 2.972,
  2.972, 2.750, 3.056, 3.139 (x2.10 [1.89, 2.31]). L 24 vs 12 and hp = hd = 1 on 64/64 orders also reproduce.
- Wrong: hp and hd are the pickup and handoff durations in slots (`or_instance.py`, Order), not energy levels.
  Energy is g = ceil(E / eps) on the routes, with concatenated rounding on delivery arcs (`arcs.py`). Rebuilt
  instances: restaurant-to-customer legs average 54.9 Wh (4.5-124.5 Wh; 12.8 % at or below 25 Wh), 1-5 levels (mean
  2.69; one level on 41 of 320 order-seeds) at 25 Wh and 1-3 (mean 1.62; one level on 135/320) at 50 Wh; delivery
  arcs 1-11 vs 1-6 levels; rounding overhead 10.8-13.8 % vs 21.2-27.6 % of route energy; modelled energy per
  delivery arc +9.4 to +12.2 % by seed, per loaded leg 67.3 -> 80.8 Wh (+20 %); pack range about 8.2 -> 6.8 loaded
  legs (-17 %). Neither does the energy per leg double nor the range halve; the earlier premise "route energies of
  the stress4h legs are below 25 Wh" is false. Bikes' initial energy is equal in Wh on seeds 0-2 and 4 and +75 Wh
  at 50 Wh on seed 3 (rounding of q0).
- Context added (records): ILP served orders 64/57/60/58/60 vs 63/57/59/57/60, ILP bike-km +0-9 %, ILP swaps 15-17 vs
  11-13, best-rule swaps 13-18 vs 9-10 and served 47-55 vs 40-44; station end deficit of the ILP 3.45-3.60 vs
  3.40-3.60 kWh (spares drained in both cells); bike end deficit (positive part) 100-950 vs 575-975 Wh. Solve
  status of the ratio: eps 50 at 600 s (3 OPT, seeds 2-3 TL at 2.66 and 0.41 %), reference at 1800 s (1 OPT, seeds
  0-3 TL at 0.75-2.87 %); against the 600 s reference rows the ILP ratio is x1.64 [1.24, 2.03]. The records do not
  split the purchase rise into rounding, extra swaps and kilometres, and end state.
- Changed: item 1 rewritten; Answer in brief (faster-charger bullet), Table 3 note, Section 5 ("Not shown"), and
  the Section 6 wording for 6.6, S8.4 and 7.1 now describe the lever as "chargers twice as fast, with energy
  rounded to 50 Wh levels" instead of "half-range packs". The script prints the energy context above (new CSV
  columns `ilp_/best_station_end_deficit_wh`, `ilp_/best_bike_end_deficit_wh`, `ilp_/best_bike_km`, `ilp_first_*`).
  No table value or figure changed for C3. The instance rebuild is `figs/check_eps50_energy.py` (run from
  `ebike_swap_sim/` with `PYTHONPATH=.`; builds instances only, no solve).
