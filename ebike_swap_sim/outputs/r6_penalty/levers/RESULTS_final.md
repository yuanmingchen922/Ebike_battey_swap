# R6 levers: station levers on stress4h-K8 under the new prices (final report)

Family stress4h-K8 (code `r5_stress4h_k8`): 8 bikes, 64 orders, 3 swap sites with 2 spares and 1 charger each, 4-h window,
seeds 0-4. New prices: unserved penalty P = 60 USD, response price w = 18 USD/h from release, lateness price v = 15 USD/h
from the promise. Old prices (round 5): P = 30, w = 18, v = 36. Everything else follows the round-5 main specification:
eBaaS energy calibration, aggregated ILP, Gurobi Threads 3, Seed 0, relaxed end targets (rho = 0, R_end = 0), time limit
600 s (round 5: 300 s). Costs are end-adjusted (total + end-state adjustment), in USD per 4-h window. Best rule =
per-instance minimum over r2, M2 and M2+M3 of the end-adjusted cost. Gap = 100 (best rule - ILP) / best rule per
instance, then averaged. Intervals are exact Student-t 95 % CIs over seeds, written `mean [lo, hi]`. Lever effects
are paired per seed (lever minus reference).

Levers: reference; no on-site charging (site power cap P_j = 0 at all 3 sites); lock-out of 2 spares (2 of the 6 spares
removed at 2 random slots in the 17-18 h dinner peak, seed-specific).

All numbers below were recomputed from `records.jsonl` (round 6) and `r5_x5_stress/records_{levers,core}.jsonl`
(round 5) by `figs/make_levers_figs.py`. No solve was run for this report. The script-generated `RESULTS.md` is kept
unchanged; its numbers match this recomputation (Section 1, item 7).

## Answer in brief

- **Artefact (b) is gone.** Without on-site charging the best rule now costs **+213.5 USD [124.0, 303.1]** more per
  window, and it is dearer on all 5 seeds. On every instance that round 5 also ran (33 rule rows), the rule
  schedules are identical to round 5. Priced at the old prices, the same schedules give **-238.9 [-380.9, -96.9]**,
  cheaper on 5/5 seeds. The paired change between the two price
  sets is +452.4 [325.4, 579.4]. Only the prices changed; r2's schedules, and the orders it leaves unserved, are the
  same in both rounds. Its served share still falls from 65.3 % to 51.6 % (-13.8 points [-16.3, -11.2]).
- **The ILP loses more than in round 5.** Removing on-site charging costs the ILP **+228.5 [184.0, 273.0] USD**
  (17 % of the reference). The proven lower bound is at least 169.6 USD on every seed, and 4 of the 5 solves without
  on-site charging are optimal. On the same seeds 0-2 the effect is 210.4 against 79.4 in round 5 (paired +131.0
  [47.1, 214.9], n = 3).
- **The coordination gap narrows without on-site charging, now by much less.** The gap is 46.1 [42.5, 49.8] % at the
  reference and 41.9 [37.9, 45.9] % without on-site charging. The paired change is -4.3 [-5.8, -2.7] points (5/5
  seeds). Round 5 had -11.0 [-14.5, -7.5] points on seeds 0-2.
- **The ILP effect of the lock-out is not resolved.** The reference and lock-out ILPs all stopped at the 600 s limit,
  with MIP gaps of 0.4-10.5 %. The measured change, -7.8 [-59.9, 44.3], is solver noise. The true change lies between 0
  and 6.6-71.4 USD, depending on the seed. For the rule, the lock-out changes nothing on 3 seeds (|change| <= 0.40 USD).
  It costs +17.4 USD on seed 3 and +284.2 USD on seed 1, where the rule drops 8 more orders.

## 1. Problems and anomalies

1. **The reference ILPs are poorly converged, worse than in round 5.** All 5 reference solves stopped at the 600 s
   limit. Their MIP gaps are 6.87, 0.83, 10.48, 1.36 and 0.85 % (seeds 0-4), or 75.3, 11.6, 138.1, 19.4 and 11.3 USD;
   the mean is 4.08 % (51.2 USD). Round 5 ran 300 s on seeds 0-2: 1 optimal, and 2 time-limited at 1.20 % and 1.37 %.
   The longer time limit did not make up for the harder instances under the new prices.
2. **Three reference incumbents are provably suboptimal.** The lock-out only removes batteries. Any lock-out schedule
   is also feasible in the reference with the same raw cost: the locked spare stays idle at its site, and storage
   capacity (8 per site, against 2 spares) does not bind. So the reference optimum cannot exceed the lock-out optimum.
   Yet the lock-out incumbents are lower than the reference incumbents on seeds 0, 2 and 4, by 15.83, 66.71 and
   4.68 USD (raw totals). The reference incumbents are therefore at least that far above their optima. Two
   consequences follow. The reference ILP cost (1313.6) overstates the optimum by at least 17.4 USD on average. And
   the reference gap of 46.1 % is a lower bound. Using min(reference, lock-out) incumbent as the reference upper bound, it is at least 46.9 [42.5, 51.3] %
   (raw totals). Against the proven bound it is at most 48.3 [42.4, 54.2] %.
3. **The lock-out ILP effect is unresolved** (Table 2). The sign of the measured change is negative on 4/5 seeds. That
   is impossible for a restriction, so the measured change only shows incumbent quality. Round 5 resolved it to within
   [0, 1.4]-[0, 11.1] USD per seed.
4. **The best rule changes identity between price sets.** Under the new prices the best rule is r2 in 15/15 cells. M2
   costs 61-274 USD more in every cell. Under the old prices (round-5 records on seeds 0-2, repriced rows on seeds 3-4)
   the best rule is M2 in 9/15 cells, and in 4/5 cells without on-site charging. M2 leaves 2-10 more orders unserved
   than r2 in every cell, and mostly has less lateness. Part of the round-5 artefact was the old prices choosing this
   order-dropping variant. M2+M3 equals M2 (same total) in all 15 round-6 cells and in all 40 round-5 instances of
   X5 levers and core. The M3 component never changes a schedule on these families.
5. **Rule rows violate a report-only constraint.** 8 of the 45 rule rows (4 of the 15 best-rule rows: reference seeds 0
   and 1, no on-site charging seed 2, lock-out seed 0) violate terminal reachability (9), 1-3 times each
   (`check_ok = False`, `ok_modulo_report_only = True`). This was already the case in round 5. It slightly favours the
   rule, so the gaps are conservative.
6. **The cross-round comparison is limited.**
   - Round 5 solved the levers only on seeds 0-2, at 300 s. The ILP comparison is therefore n = 3, with different time
     limits.
   - Old-price rule costs on seeds 3-4 come from repricing the round-6 rule rows: old = total_end_adjusted -
     unserved - lateness + 30 x n_unserved + lateness x 36/15. This is exact for r2 and M2 because they do not read
     the order prices. The formula reproduces all 33 round-5 rule rows that share an instance with round 6 (all
     status OK) to within 4.6e-13 USD: the reference on seeds 0-4 (from core), and both levers on seeds 0-2, each
     for r2, M2 and M2+M3. The largest difference, 4.55e-13 USD, is on lock-out seed 0, r2 (two floating-point
     rounding steps at about 1815 USD). The other 32 rows are within 2.3e-13 USD, and 24 are exact. On those rows the
     schedule statistics (served, unserved, late, swaps, km, response, kWh, travel, electricity, set-up, end
     adjustment) are identical. `check_repricing()` in the script prints this check.
   - M2+M3 does read the order prices: its M3 stock-out value is the mean P_i (`stockout_value()` in `baseline.py`).
     It was not re-run at the old prices on the lever cells of seeds 3-4, so its repriced cost there assumes an
     unchanged schedule. The data support that assumption: its schedule is identical at both price sets on all 11
     shared M2+M3 rows, and M2+M3 equals M2 in all 15 round-6 cells (item 4). Leaving M2+M3 out of the best rule
     changes no number in this report.
   - Absolute costs are not comparable across price sets. Only lever effects, gaps and served shares are.
7. **The auto-generated `RESULTS.md` is correct but incomplete.**
   - Every mean and CI half-width it shows matches this recomputation to rounding.
   - But it states "Anomalies: none", which misses items 1-5.
   - It lists `ilp_gap` as a fraction (0.041 = 4.1 %) with a t-interval that crosses zero (-1.4 to 9.5 %). The
     min-max range is the honest summary for this skewed, non-negative quantity.
   - Its `delta_ilp_ea` for the lock-out must not be read as an effect (item 3).
8. **The runs shared the machine.** The stage ran concurrently with three other round-6 lanes (4 lanes x 3 threads).
   Time-limited incumbents may depend on machine load.

## 2. Coverage

| item | value |
|---|---|
| cases | 15 = 3 levers x 5 seeds (seeds 0-4), relaxed targets, all planned cases present |
| records | 75 = 15 x (r2, M2, M2+M3, best rule, ILP), one record per (key, method), no duplicates |
| rule rows | 60/60 status OK |
| ILP rows | 15/15 with incumbent: reference 0 OPT / 5 TL; no on-site charging 4 OPT / 1 TL; lock-out 0 OPT / 5 TL |
| time limit | 600 s requested and used on every ILP (no budget shortening); OPT runtimes 165-371 s |
| MIP gaps of time-limited solves | reference 0.83-10.48 % (11.3-138.1 USD); lock-out 0.39-5.62 % (5.2-70.3 USD); no on-site charging seed 2 0.72 % (10.8 USD) |
| checks | MIP start accepted 15/15 (rule starts); ILP objective = evaluator cost (max abs diff 7.0e-5 USD); `check_ok` and identity (24) true on all 15 ILP schedules |
| skipped | 0 (no SKIPPED_BUDGET); wall time 129.3 min of a 270 min budget; command exit 0 (`outputs/r6_lanes/lane_3.status`) |
| prices | P 60, w 18, v 15 on all 75 rows; unserved = 60 x n_unserved and all cost identities hold on all rows |
| model size | 297-316 k binaries, 28-32 k rows per ILP |
| round-5 counterpart | `r5_x5_stress` levers: seeds 0-2, ILP 300 s; reference ILP from the levers rows and reference rule rows from core (same demand hashes as round 6 on all 15 shared instances) |

## 3. Results under the new prices (n = 5)

### Table 1. Cost, gap and service per lever

| lever | ILP OPT/TL | MIP gap % (range) | ILP end-adj. | best rule end-adj. | gap vs best rule % | gap vs bound % (upper) | served ILP | served best rule | unserved ILP / rule (mean) |
|---|---|---|---|---|---|---|---|---|---|
| Reference | 0/5 | 0.83-10.48 | 1313.6 [1155.2, 1471.9] | 2435.1 [2261.6, 2608.5] | 46.14 [42.47, 49.80] | 48.31 [42.45, 54.18] | 0.919 [0.877, 0.961] | 0.653 [0.618, 0.688] | 5.2 / 22.2 |
| No on-site charging | 4/1 | 0-0.72 | 1542.1 [1376.3, 1707.9] | 2648.6 [2534.1, 2763.1] | 41.85 [37.85, 45.86] | 41.98 [37.95, 46.02] | 0.822 [0.773, 0.871] | 0.516 [0.492, 0.539] | 11.4 / 31.0 |
| Lock-out of 2 spares | 0/5 | 0.39-5.62 | 1305.8 [1124.2, 1487.3] | 2495.2 [2213.3, 2777.0] | 47.69 [43.43, 51.94] | 49.35 [43.74, 54.96] | 0.919 [0.872, 0.965] | 0.625 [0.534, 0.716] | 5.2 / 24.0 |

The best rule is r2 on all 15 instances. No ILP order is more than 60 min late. The rule has 2 such orders on seed 1, in
both the reference and the lock-out. The gap vs bound uses raw totals and bounds the true gap from above.

### Table 2. Lever effects (lever minus reference, paired per seed)

| lever | ILP change | ILP true change, proven bracket per seed | ILP seeds > 0 | best-rule change | rule seeds > 0 | gap change (points) | served-share change ILP / rule (points) |
|---|---|---|---|---|---|---|---|
| No on-site charging | **+228.53 [184.05, 273.00]** | [242.3, 317.6], [207.7, 219.3], [169.6, 318.6], [274.7, 294.1], [236.0, 247.3]; lower end >= 169.6 on every seed | 5/5 | **+213.51 [123.95, 303.07]** (per seed 288.96, 185.94, 121.91, 185.31, 285.42) | 5/5 | -4.28 [-5.84, -2.73] (5/5 < 0) | -9.7 [-12.2, -7.2] / -13.8 [-16.3, -11.2] |
| Lock-out of 2 spares | -7.80 [-59.88, 44.28] (solver noise) | [0, 59.5], [0, 62.4], [0, 71.4], [0, 19.6], [0, 6.6] (restriction, so >= 0) | 1/5 | +60.11 [-95.75, 215.97] (per seed -0.40, +284.23, -0.34, +17.41, -0.35) | 2/5 | +1.55 [-0.40, 3.50] (5/5 > 0) | 0.0 [-1.4, 1.4] / -2.8 [-9.6, 4.0] |

- **Proven bracket.** The bracket bounds the true change in the optimum by [lever bound - reference upper bound, lever
  incumbent - reference bound], with raw totals. For no on-site charging, the upper bound used for the reference is its
  incumbent. Using the lower lock-out incumbent where it is lower raises the lower ends to 258.1 / 207.7 / 236.4 /
  274.7 / 240.7. For the lock-out, the lower end is 0 by the restriction argument (Section 1, item 2).
- **Demand-charge proxy.** As in round 5, the break-even tariff = (V(P_j = 0) - V(reference)) / (3 sites x 0.333 kW)
  x 120 windows per month. On every seed the ILP keeps on-site charging unless the demand charge exceeds about **20,400
  USD per kW-month** (min over seeds; round 5: 6,200). That is far above any realistic tariff.
- **Rule under the lock-out.** On 3 seeds the change is -0.34 to -0.40 USD. That is bookkeeping: the locked batteries
  are left out of the end-state adjustment, and the raw-total change is -0.025 USD. On seed 1 the two lock-outs fall
  at slots 12 and 13 (17:00 and 17:05, the start of the dinner peak). They push r2 from 24 to 32 unserved orders
  (served 62.5 % to 50.0 %).

### Table 3. Where the no-on-site-charging change comes from (mean of seeds 0-4, USD per window)

| component | ILP, new prices | best rule, new prices | best rule, old prices (rule schedules repriced) |
|---|---|---|---|
| unserved orders | +372.0 [274.9, 469.1] (+6.2 orders) | +528.0 [430.9, 625.1] (+8.8 orders) | +402.0 [190.3, 613.7] (+13.4 orders) |
| response | -120.6 [-168.5, -72.7] | -234.3 [-282.0, -186.6] | -356.7 [-536.5, -177.0] |
| lateness | -17.5 [-30.1, -4.9] | -75.3 [-106.6, -43.9] | -277.2 [-422.4, -132.0] |
| travel, electricity, set-up, end adjustment | -5.4 | -4.9 [-5.6, -4.3] | -7.0 [-10.0, -4.1] |
| **net** | **+228.5 [184.0, 273.0]** | **+213.5 [124.0, 303.1]** | **-238.9 [-380.9, -96.9]** |

The best rule is chosen per price set: r2 on 5/5 seeds at the new prices, M2 on 4/5 at the old prices. That is why
the old-price column drops more orders. Per extra dropped order, the rule avoids 35.2 USD of response and lateness at
the new prices, against a 60 USD penalty. At the old prices it avoided 47.3 USD, against a 30 USD penalty. This
reversal explains the artefact.

**Answer to the question.** No: under the new prices the rule no longer gets cheaper without on-site charging. It gets
dearer by +213.5 USD [124.0, 303.1] per window, on all 5 seeds. This is a pure pricing effect. r2 and M2 do not
read the order prices, and M2+M3 (which reads the mean P_i) produced the same schedules at both price sets on every
instance where both were run. So the schedules, and the orders each rule leaves unserved, are unchanged. What changed is the price of those orders, and
with it which rule is best (r2 instead of mostly M2). Without on-site charging the ILP and the rule now lose about the same
amount (ILP minus rule: +15.0 [-62.1, 92.2]). In round 5 the ILP lost 288.9 [110.0, 467.9] more than the rule, on
seeds 0-2.

## 4. Comparison with round 5 (old prices) on the same instances

Same demand hashes. The old-price ILP is from the round-5 levers rows (300 s), so n = 3, seeds 0-2. The rule's n = 5
rows reprice the round-6 rule rows on all five seeds (Section 1, item 6). On seeds 0-2 the repriced per-seed changes
equal those from the round-5 records to within 2.3e-13 USD.

| quantity | old prices (P 30, v 36) | new prices (P 60, v 15) | new - old (paired) |
|---|---|---|---|
| ILP change, no on-site charging (seeds 0-2) | +79.45 [19.20, 139.70] | +210.42 [133.41, 287.44] | +130.98 [47.07, 214.89] |
| best-rule change, no on-site charging (seeds 0-2, records) | -209.48 [-448.17, 29.21] | +198.94 [-10.42, 408.30] | +408.42 [170.36, 646.48] |
| best-rule change, no on-site charging (seeds 0-4) | -238.93 [-380.94, -96.91] (repriced) | +213.51 [123.95, 303.07] | +452.44 [325.43, 579.44] |
| best-rule served-share change, no on-site charging (seeds 0-4, points) | -20.9 [-32.0, -9.9] (repriced) | -13.8 [-16.3, -11.2] | +7.2 [-2.5, 16.8] |
| ILP served-share change, no on-site charging (seeds 0-2, points) | -8.3 [-16.4, -0.3] | -8.3 [-10.6, -6.1] | 0.0 [-6.7, 6.7] |
| gap change, no on-site charging (seeds 0-2, points) | -10.99 [-14.50, -7.48] | -4.11 [-4.84, -3.38] | +6.88 [2.99, 10.77] |
| gap at reference (seeds 0-2) | 45.89 [44.28, 47.50] | 47.68 [40.60, 54.76] | +1.79 [-6.45, 10.04] |
| gap at reference (seeds 0-4; old ILP = round-5 core, 600 s) | 45.51 [40.76, 50.26] | 46.14 [42.47, 49.80] | +0.62 [-4.84, 6.09] |
| gap without on-site charging (seeds 0-2) | 34.90 [31.26, 38.54] | 43.57 [36.37, 50.78] | +8.67 [2.12, 15.23] |
| gap with lock-out (seeds 0-2) | 45.15 [43.32, 46.98] | 50.07 [46.74, 53.39] | +4.92 [1.54, 8.29] |
| ILP change, lock-out (seeds 0-2) | -2.60 [-10.62, 5.42] | -11.17 [-157.50, 135.17] | not interpretable (MIP gaps) |
| best-rule change, lock-out (seeds 0-4) | -31.10 [-57.59, -4.60] (repriced; 0/5 > 0) | +60.11 [-95.75, 215.97] (2/5 > 0) | +91.21 [-85.60, 268.01] |
| ILP status, reference / no on-site charging / lock-out (seeds 0-2) | 1 OPT + 2 TL (1.20, 1.37 %) / 3 OPT / 3 TL (0.14-0.82 %) | 3 TL (6.87, 0.83, 10.48 %) / 2 OPT + 1 TL (0.72 %) / 3 TL (5.24, 3.64, 5.62 %) | - |

- The old-price best-rule change on seeds 0-2 (-126.35, -314.68, -187.42) differs slightly from the round-5 report
  (-126.46, -314.73, -188.26). The round-5 report picked the best rule on raw totals; here the pick is on end-adjusted
  totals.
- The gap with the lock-out is 4.9 points higher at the new prices on seeds 0-2 (3/3 seeds). This is not a clean
  price effect. Per seed it mixes three things:
  - seed 0: the reference gap is also higher at the new prices (50.9 against 45.3 %);
  - seed 1: the rule's +284 USD lock-out response;
  - seed 2: incumbent quality (the new-price lock-out incumbent is 66.7 USD below the reference incumbent).
  The new-price lock-out ILPs carry MIP gaps of 3.6-5.6 % on these seeds.

## 5. Interpretation

**Shown by the records**

- The round-5 finding that the rule gets cheaper without on-site charging was an artefact of cheap unserved orders.
  The evidence: r2 and M2 do not read the order prices, and on all 33 rule rows shared with round 5 the schedules
  are identical (M2+M3 included). Priced at the old prices they give -238.9 USD (5/5 seeds);
  at the new prices +213.5 USD (5/5 seeds). Nothing but the prices differs; the best rule is picked per price set.
- Per dropped order, the rule saves 35 USD of response and lateness. Dropping now costs 60 USD, so it no longer pays.
- At the old prices the rule family also switched to the more order-refusing M2 in 4/5 cells without on-site
  charging. Under the new prices r2 wins everywhere.
- The behavioural weakness remains. Without on-site charging the rule still serves only 51.6 % of the orders, against
  82.2 % for the ILP. The new prices only make that weakness visible in cost.
- On-site charging is the one material station lever for the ILP. Removing it costs at least 169.6 USD on every seed
  (proven), about 17 % of the reference cost, and about 2.6 times the round-5 effect on the same seeds. Most of it
  is 6.2 more unserved orders (+372 USD) partly offset by lower response and lateness costs.
- The coordination gap stays large in every lever cell (41.9-47.7 %). Without on-site charging it falls by 4.3
  points, against 11.0 points in round 5. In round 5 the rule's apparent gain had shrunk the gap; that no longer
  happens.

**Not shown (solver limits)**

- Whether a 2-spare lock-out costs the coordinated schedule anything. The true ILP change lies in [0, 6.6] to
  [0, 71.4] USD per seed. In round 5 it was at most 11 USD. A longer or warm-started reference solve is needed. For
  example: start the reference from the lock-out incumbent, which is feasible for it, or re-solve seeds 0 and 2 with
  a longer limit.

**Suggested, not tested**

- The new prices make the stress4h-K8 ILP harder: 0/5 reference solves optimal at 600 s, against 2/5 at 600 s in
  round 5 (core) and 1/3 at 300 s (levers). A plausible cause is that more orders are worth serving at P = 60, which
  widens the effective search space. That was not measured.
- The rule's lock-out response on seed 1 (+284 USD) suggests that r2 is fragile to losing spares early in the peak.
  With one seed this is an observation, not a result.

## Figures (`figs/`, PDF vector + PNG 300 dpi, Okabe-Ito colours)

- `fig_r6_levers_effects`: change in end-adjusted cost against the reference, for the ILP (a) and the best rule (b).
  New prices (n = 5) and old prices (round 5, seeds 0-2). Mean with exact-t 95 % CI, seeds as dots. The grey band in
  (a) is the mean absolute MIP gap of the new-price reference (51 USD).
- `fig_r6_levers_mechanism`: (a) served share per lever, ILP vs best rule, new prices (n = 5). (b) The best rule's cost
  change without on-site charging, split into unserved, response, lateness and other components, at the old prices
  (repriced schedules) and the new prices, with the net change and its 95 % CI (seeds 0-4).
- `fig_r6_levers_ilp_bounds`: ILP incumbent and proven lower bound per instance (new prices, 600 s). Open markers are
  time-limited solves, labelled with their MIP gap. It shows the lock-out incumbent below the reference incumbent on
  seeds 0, 2 and 4.
- Data next to the figures: `levers_per_instance_final.csv` (round 6 and round 5 rows),
  `levers_summary_final.csv`, `levers_cross_round_final.csv`, `levers_rule_decomposition_final.csv`.
  Script: `make_levers_figs.py` (prints every table above).

## Appendix. Per-instance results

Round 6, new prices, ILP 600 s. The ILP and rule change columns are lever minus reference (end-adjusted). The bracket
is the proven range of the true ILP change (raw totals, own incumbents).

| lever | seed | ILP status | MIP gap % | ILP end-adj. | ILP bound | best rule | best rule end-adj. | gap % | gap vs bound % | served ILP / rule | unserved ILP / rule | ILP change | ILP bracket | rule change |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reference | 0 | TL | 6.87 | 1099.06 | 1021.57 | r2 | 2236.43 | 50.86 | 54.29 | 0.969 / 0.688 | 2 / 20 | - | - | - |
| Reference | 1 | TL | 0.83 | 1388.98 | 1375.30 | r2 | 2541.11 | 45.34 | 45.84 | 0.891 / 0.625 | 7 / 24 | - | - | - |
| Reference | 2 | TL | 10.48 | 1320.27 | 1180.09 | r2 | 2484.05 | 46.85 | 52.47 | 0.906 / 0.625 | 6 / 24 | - | - | - |
| Reference | 3 | TL | 1.36 | 1427.43 | 1406.01 | r2 | 2566.33 | 44.38 | 45.18 | 0.891 / 0.672 | 7 / 21 | - | - | - |
| Reference | 4 | TL | 0.85 | 1332.07 | 1318.68 | r2 | 2347.36 | 43.25 | 43.79 | 0.938 / 0.656 | 4 / 22 | - | - | - |
| No on-site charging | 0 | OPT | 0.00 | 1341.61 | 1339.20 | r2 | 2525.39 | 46.87 | 46.93 | 0.875 / 0.547 | 8 / 29 | +242.56 | [242.3, 317.6] | +288.96 |
| No on-site charging | 1 | OPT | 0.00 | 1597.01 | 1594.59 | r2 | 2727.06 | 41.44 | 41.48 | 0.812 / 0.500 | 12 / 32 | +208.03 | [207.7, 219.3] | +185.94 |
| No on-site charging | 2 | TL | 0.72 | 1500.96 | 1487.83 | r2 | 2605.96 | 42.40 | 42.86 | 0.828 / 0.516 | 11 / 31 | +180.69 | [169.6, 318.6] | +121.91 |
| No on-site charging | 3 | OPT | 0.00 | 1702.51 | 1700.14 | r2 | 2751.64 | 38.13 | 38.17 | 0.766 / 0.516 | 15 / 31 | +275.08 | [274.7, 294.1] | +185.31 |
| No on-site charging | 4 | OPT | 0.00 | 1568.35 | 1565.99 | r2 | 2632.79 | 40.43 | 40.48 | 0.828 / 0.500 | 11 / 32 | +236.27 | [236.0, 247.3] | +285.42 |
| Lock-out of 2 spares | 0 | TL | 5.24 | 1082.62 | 1024.38 | r2 | 2236.03 | 51.58 | 54.16 | 0.969 / 0.688 | 2 / 20 | -16.44 | [-72.5, 59.5] | -0.40 |
| Lock-out of 2 spares | 1 | TL | 3.64 | 1439.18 | 1385.34 | r2 | 2825.35 | 49.06 | 50.95 | 0.875 / 0.500 | 8 / 32 | +50.20 | [-1.5, 62.4] | +284.23 |
| Lock-out of 2 spares | 2 | TL | 5.62 | 1253.01 | 1181.17 | r2 | 2483.71 | 49.55 | 52.42 | 0.922 / 0.625 | 5 / 24 | -67.26 | [-137.0, 71.4] | -0.34 |
| Lock-out of 2 spares | 3 | TL | 1.23 | 1427.09 | 1407.99 | r2 | 2583.74 | 44.77 | 45.48 | 0.891 / 0.656 | 7 / 22 | -0.33 | [-17.4, 19.6] | +17.41 |
| Lock-out of 2 spares | 4 | TL | 0.39 | 1326.92 | 1320.13 | r2 | 2347.02 | 43.46 | 43.73 | 0.938 / 0.656 | 4 / 22 | -5.16 | [-9.9, 6.6] | -0.35 |

Round 5, old prices, ILP 300 s. The best rule is recomputed on end-adjusted totals.

| lever | seed | ILP status | MIP gap % | ILP end-adj. | ILP bound | best rule | best rule end-adj. | gap % | gap vs bound % | served ILP / rule | unserved ILP / rule | ILP change | ILP bracket | rule change |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reference | 0 | OPT | 0.00 | 993.49 | 991.31 | r2 | 1814.93 | 45.26 | 45.33 | 0.969 / 0.688 | 2 / 20 | - | - | - |
| Reference | 1 | TL | 1.20 | 1127.35 | 1111.69 | r2 | 2081.86 | 45.85 | 46.56 | 0.812 / 0.625 | 12 / 24 | - | - | - |
| Reference | 2 | TL | 1.37 | 1061.31 | 1044.71 | M2 | 1985.88 | 46.56 | 47.36 | 0.891 / 0.594 | 7 / 26 | - | - | - |
| No on-site charging | 0 | OPT | 0.00 | 1091.65 | 1089.25 | M2 | 1688.58 | 35.35 | 35.43 | 0.859 / 0.453 | 9 / 35 | +98.16 | [97.9, 97.9] | -126.35 |
| No on-site charging | 1 | OPT | 0.00 | 1179.39 | 1176.95 | M2 | 1767.18 | 33.26 | 33.33 | 0.766 / 0.375 | 15 / 40 | +52.05 | [51.8, 65.3] | -314.68 |
| No on-site charging | 2 | OPT | 0.00 | 1149.45 | 1147.19 | r2 | 1798.46 | 36.09 | 36.14 | 0.797 / 0.516 | 13 / 31 | +88.14 | [87.9, 102.5] | -187.42 |
| Lock-out of 2 spares | 0 | TL | 0.14 | 994.28 | 991.23 | r2 | 1814.53 | 45.20 | 45.34 | 0.969 / 0.688 | 2 / 20 | +0.78 | [-0.1, 1.4] | -0.40 |
| Lock-out of 2 spares | 1 | TL | 0.82 | 1124.42 | 1113.60 | M2 | 2021.93 | 44.39 | 44.90 | 0.812 / 0.438 | 12 / 36 | -2.93 | [-11.5, 11.1] | -59.93 |
| Lock-out of 2 spares | 2 | TL | 0.67 | 1055.66 | 1047.12 | M2 | 1949.71 | 45.86 | 46.27 | 0.891 / 0.578 | 7 / 27 | -5.65 | [-12.1, 9.5] | -36.16 |

Repriced old-price best rule on round-6 seeds 3-4 (end-adjusted, USD): reference 2291.58 (r2) / 1880.27 (M2); no
on-site charging 1891.52 (M2) / 1714.14 (M2); lock-out 2264.99 (r2) / 1847.87 (M2).

## Verification corrections (R6)

Two independent refuters checked the report's claims against the records. One claim was refuted by at least one of
them. The corrector recomputed it from `records.jsonl` (round 6) and `r5_x5_stress/records_{levers,core}.jsonl`
(round 5). The check is now in the script (`check_repricing()`, called from `main()`).

**C2. "The rule schedules are price-independent. Repricing a round-6 rule row ... reproduces all 33 round-5 rule
rows that share an instance to within 2.3e-13 USD. On seeds 0-4 this gives an old-price best-rule change without
on-site charging of -238.93 [-380.94, -96.91], negative on 5/5 seeds."** (Section 1, item 6; Answer in brief;
Section 3, Answer to the question; Section 5.)

- Refuter 1: refuted (the tolerance). Refuter 2: refuted (the tolerance, and "price-independent" is too strong for
  M2+M3).
- Recomputed. Matching on (cell, seed, method) gives 33 shared rule rows: the reference on seeds 0-4 (core, family
  `r5_stress4h_k8`, target `rho0_R0`), plus P0 and lockout0.25 on seeds 0-2 (levers), each for r2, M2 and M2+M3. All
  are status OK in both rounds, and demand hashes match. With old = total_end_adjusted - unserved - lateness + 30 x
  n_unserved + lateness x 36/15, the largest absolute difference from the round-5 total_end_adjusted is **4.55e-13
  USD**, on lockout0.25 seed 0, r2 (1814.5282500000003 against 1814.5282499999998). The same value comes out with
  the 36/15 ratio evaluated first and with total + C_end_adjust in place of total_end_adjusted. The other 32 rows
  are within 2.27e-13 USD and 24 rows are exact. The maximum is 2.27e-13 per cell for the reference and P0, and over
  all rows when the raw `total` is compared. That is the likely source of the stated 2.3e-13. The schedule
  statistics are identical on all 33 rows. Old-price best-rule change without on-site charging, seeds 0-4: per seed
  -126.35, -314.68, -187.42, -400.06, -166.13; **-238.93 [-380.94, -96.91] USD** (n = 5, exact t, paired), negative
  on 5/5 seeds. This is the same with round-5 records used directly on seeds 0-2, and the same with M2+M3 left out
  of the minimum.
- Code check. r2 and M2 read no order price. M2+M3 does: in the default mode `stockout_cost_mode = "P"`,
  `stockout_value()` in `ebike_swap_sim/baseline.py` sets the M3 stock-out value from the mean P_i. Its schedules
  are still identical on all 11 shared M2+M3 rows, and M2+M3 equals M2 in all 15 round-6 cells.
- Verdict. Both refuters are right on the tolerance: 4.6e-13 USD, not 2.3e-13. The difference is floating-point
  rounding only. Refuter 2 is also right that the unqualified "price-independent" overstates the case for M2+M3.
  The substantive result stands: n = 33, identical schedules, and -238.93 [-380.94, -96.91] on 5/5 seeds.
- What changed.
  - Section 1, item 6: the tolerance now reads 4.6e-13 USD, naming the largest row, the 32 other rows within 2.3e-13
    and the 24 exact rows. The status of all rows (OK) is now stated. The M2+M3 caveat now says that it reads the mean
    P_i, that its seeds 3-4 lever repricing assumes an unchanged schedule, and that leaving it out changes nothing.
  - Answer in brief, Section 3 (Answer to the question) and Section 5: "the rule schedules are price-independent" /
    "the same as in round 5" / "every rule's schedules are unchanged" now say what was shown. r2 and M2 do not read
    prices, and all three rules have identical schedules on the 33 shared rows.
  - Section 4 intro: the n = 5 rule rows reprice all five seeds and agree with the round-5 records on seeds 0-2.
  - `figs/make_levers_figs.py`: the docstring said "checked to 1e-12 against every round-5 rule row on seeds 0-2"
    with no computed value. It now states the 33-row check and its maximum. A new `check_repricing()` prints the
    check.
  - No table value, figure or CSV changes. The figures and data files were not regenerated; their inputs are
    unchanged.
