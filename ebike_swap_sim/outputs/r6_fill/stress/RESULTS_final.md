# R6 fill, stage stress: stress4h-K10, stress8h, written targets and the end-target grid at 6 bikes, LP shadow prices (final report, new prices P 60 / w 18 / v 15)

Written 2026-10-20 from the records; no solve was run for this report and the script-generated `RESULTS.md` was not
trusted (its anomaly section says "none" and it is wrong, see Section 1). Every number below is recomputed by
`figs/make_stress_figs.py` from

- `records.jsonl` of this stage (236 rows: the written-target cell and the end-target grid of stress4h with 6 bikes,
  the relaxed stress4h-K10 and stress8h cells, the LP relaxations of all of them and of stress4h-K8),
- `outputs/r6_penalty/psweep/records.jsonl` (the relaxed stress4h 6-bike ILP at P 60 / v 15, seeds 0-4, last row per
  key after the 600 s server retries of seeds 1, 2 and 3; the rule rows of the same instances),
- `outputs/r6_penalty/levers/records.jsonl` (the stress4h-K8 reference cell: 1800 s laptop retries, last row per key,
  `retry_worse` rows ignored),
- `outputs/r6_penalty/fleet/records.jsonl` (cell K6_B2_pack0.6, rho 0 / R_end 0: the same relaxed 6-bike instances,
  seeds 0-2, last row per key after the 600 s server retries of seeds 1 and 2) and
  `outputs/r6_penalty/network/records.jsonl` (the relaxed 6-bike ILP rows, 300 s, seeds 0-4); both added by the
  verification pass (Section 8) to the pool of relaxed solves,
- `outputs/r5_x5_stress/records_core.jsonl` and `records_boundary.jsonl` (the same instances at the legacy prices).

Conventions. Families stress4h (6 bikes, 48 orders, 4 h), stress4h-K8 (8 bikes, 64 orders), stress4h-K10 (10 bikes,
80 orders), stress8h (6 bikes, 96 orders, 8 h); three swap sites with 2 spares and 1 charger each. Rules r2, M2 (code
`r5_range`) and M2+M3 (code `r5`; identical to M2 here, no transport services exist); best rule = per-instance minimum of
the end-adjusted cost over the three. ILP = aggregated formulation, Gurobi Threads 3, Seed 0, MIP start from the
cheapest clean rule schedule where one exists. Gap = 100 (best rule - ILP) / best rule per instance, then averaged, on
the end-adjusted cost unless stated; "gap against the bounds" uses the solver's proven lower bound instead of the
incumbent (raw totals) and is the upper end of the true gap of a time-limited cell. Intervals are exact Student-t 95 %
CIs over seeds, written `mean [lo, hi]`; paired differences are per seed on identical instances (the demand hashes of
the 23 instance pairs are equal across the two price sets). Price of recovery (PoR) = ILP cost under the given end
targets minus the relaxed ILP cost on the same seed, on objective (26) (raw); its proven bracket is
`[max(0, bound_target - incumbent_relaxed), incumbent_target - bound_relaxed]`. New prices: unserved order P 60 USD,
response w 18 USD/h from release, lateness v 15 USD/h from the promise; legacy prices: P 30, v 36. USD per window.

Files: `figs/stress_final_per_instance.csv` (every ILP/rule pair used, new and legacy), `figs/stress_final_written.csv`,
`figs/stress_final_boundary.csv`, `figs/stress_final_lp.csv`, `figs/stress_final_summary.json`, figures in `figs/`.

## 0. Answer in brief

1. **Gap at 10 bikes: 50.2 % [47.0, 53.4] (n 5), a lower bound; at most 53.8 % [50.7, 56.8] against the proven
   bounds.** All five 600 s solves are time-limited with MIP gaps 3.7-13.3 % (legacy prices: 46.99 %, MIP gaps 0.9-1.9 %).
   The ILP serves 0.907 of the orders against 0.593 for the best rule.
2. **Gap in the 8-hour window: 42.8 % [13.5, 72.0] (n 3), at most 47.0 % [20.4, 73.6] against the bounds**; per seed
   29.2, 48.8, 50.3 % (bounds 34.8, 51.4, 54.8 %); all three solves time-limited at 600 s with MIP gaps 4.9-9.0 %. The
   interval is too wide to separate the window lengths; the value is lower than the legacy 47.9 % on every seed and
   provably lower on seeds 1 and 2.
3. **Fleet axis at the new prices: 40.0 % (6 bikes) -> 47.6 % (8 bikes, 1800 s reference solves of the lever
   experiment, 1 optimal + 4 time-limited at 0.7-2.9 %) -> 50.2 % (10 bikes).** Welch tests on the per-seed gaps:
   6 -> 8 +7.6 points, p 0.026; 6 -> 10 +10.2 points, p 0.003; 8 -> 10 +2.6 points, p 0.29 (bound-based gaps: p 0.024,
   0.0008, 0.061). At the legacy prices the same tests gave p 0.092, 0.038 and 0.54.
4. **Written targets at 6 bikes: gap 38.8 % [32.6, 45.0] (n 4) against 39.7 % relaxed on the same seeds (-0.9
   [-3.0, 1.2] points).** The price of recovery is resolved on two seeds only: 0.77 USD on seed 0 (both solves optimal,
   0.10 % of the relaxed optimum) and in [0, 9.97] USD on seed 4; seeds 1 and 3 are bracketed in [0, 13.9] and
   [1.3, 52.0] USD by time-limited solves, and the written solve of seed 2 found no incumbent in 300 s. The legacy
   value was 3.20 USD [0.18, 6.21] (n 5).
5. **End-target grid (seeds 0-2, 300 s): every cell with rho <= 0.5 costs exactly 0.48-0.77 USD on seed 0 (optimal
   solves) and at most 9.3-18.8 USD on seed 1; full battery return (rho = 1, either R_end, and the periodic bracket) is
   proven to cost at least 9.2 USD on seed 1 and 55.4 USD on seed 2** (raw cost; all six rho = 1 solves of seeds 1-2
   time-limited at 300 s; upper bounds 69.7 USD on seed 0 and 152-175 USD on seed 2; corrected in Section 8). 10 of
   the 27 grid and written solves found no feasible solution within 300 s (legacy prices: 1 of 24).
6. **LP operating value of one more spare per site: 0.70 USD [0.17, 1.24] with 6 bikes (about 2 x its set-up cost of
   0.332 USD), 9.81 [4.64, 14.98] with 8 (30 x) and 77.95 [38.30, 117.60] with 10 (235 x); charger 0.03 [-0.02, 0.08]
   (below its 0.082 USD set-up cost on every seed), 8.78 [2.60, 14.96] and 65.86 [29.70, 102.03].** Legacy: 0.45 / 2.79 /
   21.87 and 0.07 / 1.29 / 16.67. Paired, the spare value rises by +0.25 [-0.36, 0.87], +7.01 [3.04, 10.99] and +56.08
   [24.30, 87.85] USD; the ordering and the break-even point (between 6 and 8 bikes) are unchanged.
7. **Served shares, ILP vs best rule: 0.954 vs 0.754 (6 bikes), 0.925 vs 0.653 (8), 0.907 vs 0.593 (10), 0.910 vs
   0.729 (8 h).** No ILP order is more than 60 min late in any cell.

## 1. Problems and anomalies (read first)

1. **Ten ILP solves ended at the 300 s limit without any incumbent** (status TIME_LIMIT, no `total`): written
   targets seed 2; rho 0 / R_end 1 seed 2; rho 0.25 / R_end 1 seed 2; rho 0.5 / R_end 0 seed 2; rho 1 / R_end 0 seeds
   0, 1, 2; rho 1 / R_end 1 seed 1; periodic bracket seeds 0 and 1. In all ten the MIP start is `default_unclean`
   verified INFEASIBLE (the rule schedules violate the end targets), so Gurobi started without a feasible solution and
   did not find one; a proven lower bound is recorded for each. At the legacy prices the same cells (where run) found
   an incumbent in all but one case (periodic seed 1). Consequences: the written-target cell has n 4, the grid cells
   with R_end 1 and rho <= 0.5 have n 2, rho 1 / R_end 0 has n 0, and the script's `RESULTS.md` averages what is left
   without saying so (its "Anomalies: none" line counts only ERROR / SKIPPED_BUDGET rows). This report gives per-seed
   brackets instead of means where seeds are missing.
2. **One grid incumbent is useless:** rho 0.25 / R_end 0 seed 2 stopped at 1741.8 USD with a 42.1 % MIP gap (the
   rule-free relaxation bound is 1007.9). Its "price of recovery" of 728 USD is solver noise (bracket [0, 731]); the
   script's `summary_boundary.csv` averaged it into 243.9 +- 1030.8 USD. It is excluded from every mean below.
3. **All K10 and stress8h solves are time-limited with large MIP gaps at 600 s** (3.65-13.31 % and 4.86-8.98 %;
   legacy prices at the same limit: 0.87-1.93 % and 0.18-1.49 %). Every K10 / stress8h gap is therefore a lower bound and
   is reported with its bound-based upper end; the K10 bracket is [50.2, 53.8] %, the stress8h bracket [42.8, 47.0] %.
   The new prices make these instances markedly harder (the psweep already noted this for stress4h at P 60-80).
4. **Written-target seed 3 (MIP gap 4.9 %) dominates the mean price of recovery:** its estimate 50.7 USD has the
   proven bracket [1.34, 52.0]; the 4-seed mean 16.8 USD [-19.7, 53.3] is not a usable number. The honest statement is
   per seed (Section 3.3).
5. **Several relaxed solves exist for the 6-bike instances at the new prices** (corrected in Section 8): the psweep
   P 60 cell (retried at 600 s on the server for seeds 1-3), this stage's rho 0 / R_end 0 solve (300 s, seeds 0-2), the
   fleet grid's K6_B2_pack0.6 cell (the same instances; retried at 600 s on the server for seeds 1-2) and the network
   stage's relaxed ILP (300 s, seeds 0-4; the rl stage's 300 s rows repeat the psweep incumbents with no larger bound).
   They agree on seed 0 (optimum 785.620). Best-known incumbents: seed 1 1028.748 (fleet retry; psweep 1029.492, this
   stage 1031.082), seed 2 1013.761 (psweep and network; fleet retry 1013.939, this stage 1018.797); seeds 3-4 psweep.
   Largest bounds: seed 1 1020.491 and seed 2 1010.626 (both network). This report uses the best-known incumbent and the
   largest bound per seed over all of them; the script's `price_of_recovery.csv` used the stage's own rows for seeds
   0-2 (seed 1 PoR 3.26 instead of 5.59 USD).
6. **The 8-bike reference numbers differ from `outputs/r6_penalty/levers/RESULTS_final.md`** (46.14 % there, 47.59 %
   here) because the 1800 s retries of the five reference solves landed after that report (seed 4 is now optimal, the
   other four improved by 0-103 USD). The levers report should be refreshed; the manuscript's 46.14 % and "0 optimal,
   5 time limit (0.83-10.48 %)" are superseded.
7. **End-adjusted price of recovery can be negative** (seed 0: -0.07 USD while the raw price is +0.77), because the
   relaxed optimum minimises the raw objective and the end-state adjustment of the relaxed schedule is larger. Prices of
   recovery are therefore reported on the raw objective, as in the legacy report.
8. **stress8h rests on three seeds and the best rule changes identity** (M2, M2, r2; legacy M2 on all three), so
   the 42.8 % is a mean of 29.2, 48.8 and 50.3 % and its interval spans 13.5-72.0 %.
9. Clean otherwise: no ERROR / SKIPPED_BUDGET rows; the stage ran 16,106 s of a 24,000 s budget (2026-10-19 23:13 to
   2026-10-20 03:41, laptop with caffeinate); the largest run-time overshoot is 4.1 s (no sleep truncation);
   `check_ok` and `obj_eq_eval` are True on all 27 incumbents; identity (24) holds on every evaluated schedule; all 23
   LPs are LP_OPTIMAL (30-119 s each); every row carries P 60 / w 18 / v 15.
10. Not covered by this stage (so still legacy-only in the manuscript): the price of recovery with 8 and 10 bikes
    (11.63 and 29.41 USD on seed 0), the price of recovery on nyc4h and the transfer layouts, and the operating metrics
    other than served share, lateness and stock-outs.

Recommendation: re-solve the ten incumbent-less cells and the four time-limited written / grid cells of seeds 1-3 at
1800 s from a repaired start (the relaxed incumbent plus end-of-window charging, or the written optimum of seed 0's
family of starts), as the R6 retry rule does for the grid stages; without it the calibrated-price boundary table has
holes on seed 2 and the written-target price of recovery is resolved on two seeds.

## 2. Coverage

| item | this stage | joined from |
|---|---|---|
| records | 236: 37 ILP (29 at 300 s: 6 OPTIMAL + 23 TIME_LIMIT, 10 of them without incumbent; 8 at 600 s: all TIME_LIMIT), 23 LP (all LP_OPTIMAL, LP limit 300 s), 176 rule rows (44 instance-targets x r2, M2, M2+M3, best rule) | psweep: 5 relaxed ILP rows (seeds 0 and 4 OPTIMAL at 300 s; 1-3 TIME_LIMIT at 600 s after retry, MIP gaps 0.14-0.87 %) + 15 rule rows; fleet (K6_B2_pack0.6): 3 relaxed ILP rows (seed 0 OPTIMAL at 300 s; seeds 1-2 TIME_LIMIT at 600 s after retry); network: 5 relaxed ILP rows (300 s); levers: 5 reference ILP rows (1800 s retries; seed 4 OPTIMAL, others 0.75-2.87 %) + 15 rule rows |
| cells and seeds | stress4h 6 bikes: written (seeds 0-4, 300 s + LP), grid rho {0, 0.25, 0.5, 1} x R_end {0, 1} + periodic (seeds 0-2, 300 s; the relaxed cell carries the LP), LP-only relaxed seeds 3-4; stress4h-K8 LP-only seeds 0-4; stress4h-K10 relaxed seeds 0-4 (600 s + LP); stress8h relaxed seeds 0-2 (600 s + LP) | legacy: `r5_x5_stress` core and boundary, same seeds |
| model sizes | 0.49-0.51 M variables (6 bikes, 0.22-0.23 M binaries), 0.67-0.75 M (10 bikes), 1.13-1.14 M (8 h, 0.50 M binaries) | - |
| wall time | 16,106 s / 24,000 s budget; 47 cases; none skipped | - |
| solve status by cell | K6 written 1 OPT + 4 TL (1.15-4.90 %; seed 2 no incumbent); grid: see Section 3.4; K10 0 OPT + 5 TL (3.65-13.31 %); stress8h 0 OPT + 3 TL (4.86-8.98 %) | K6 relaxed 2 OPT + 3 TL (0.14-0.80 %, best-known incumbent against the largest bound; psweep rows alone 0.14-0.87 %); K8 1 OPT + 4 TL (0.75-2.87 %) |
| checks | check_ok and obj_eq_eval True on all 27 incumbents; no ERROR / SKIPPED_BUDGET; max runtime - limit 4.1 s; demand_md5 equal to the legacy instances on all 23 pairs | - |

## 3. Results at the new prices

### 3.1 Gap at 10 bikes and in the 8-hour window (relaxed targets)

| seed | K10: ILP end-adj. (status, MIP gap) | K10: best rule (id) | K10 gap % [incumbent, bound] | ILP / rule served | 8 h: ILP end-adj. (status, MIP gap) | 8 h: best rule (id) | 8 h gap % [incumbent, bound] | ILP / rule served |
|---|---|---|---|---|---|---|---|---|
| 0 | 1302.45 (TL, 4.90 %) | 2791.89 (r2) | 53.35 [53.35, 55.68] | 0.975 / 0.675 | 1721.42 (TL, 7.79 %) | 2431.16 (M2) | 29.19 [29.19, 34.75] | 0.958 / 0.865 |
| 1 | 1684.36 (TL, 9.00 %) | 3430.80 (M2) | 50.90 [50.90, 55.37] | 0.888 / 0.575 | 2107.70 (TL, 4.86 %) | 4120.48 (M2) | 48.85 [48.85, 51.37] | 0.885 / 0.635 |
| 2 | 1623.77 (TL, 4.06 %) | 3363.37 (r2) | 51.72 [51.72, 53.72] | 0.900 / 0.562 | 2068.60 (TL, 8.98 %) | 4159.68 (r2) | 50.27 [50.27, 54.77] | 0.885 / 0.688 |
| 3 | 1776.74 (TL, 13.31 %) | 3379.36 (r2) | 47.42 [47.42, 54.46] | 0.875 / 0.575 | | | | |
| 4 | 1676.99 (TL, 3.65 %) | 3203.74 (M2) | 47.66 [47.66, 49.61] | 0.900 / 0.575 | | | | |
| mean | 1612.86 [1386.83, 1838.89] | 3233.83 [2909.47, 3558.19] | **50.21 [46.99, 53.43]**; bound 53.77 [50.73, 56.81] | 0.907 [0.859, 0.956] / 0.593 [0.535, 0.650] | 1965.90 [1437.69, 2494.11] | 3570.44 [1119.00, 6021.88] | **42.77 [13.51, 72.03]**; bound 46.96 [20.36, 73.57] | 0.910 [0.805, 1.014] / 0.729 [0.431, 1.028] |

The raw-objective gaps differ from the end-adjusted ones by less than 0.1 point. The ILP leaves 7.4 [3.5, 11.3] of 80
orders unserved with 10 bikes and 8.7 [-1.4, 18.7] of 96 in the 8-h window, none more than 60 min late (best rule:
0.2 and 1.0 such orders per window); mean ILP lateness of served orders 1.4 and 1.7 min. Stock-out slot-sites (site,
slot pairs without a full battery): ILP 97.6 [87.6, 107.6] vs rule 105.8 [85.0, 126.6] with 10 bikes, 211.3 vs 199.3
in the 8-h window (legacy 95.2 vs 112.2 and 211.3 vs 198.3).

### 3.2 Fleet axis 6 -> 8 -> 10 bikes and the Welch tests

| cell | n | ILP status (limit) | ILP end-adj. | best rule end-adj. | gap % (end-adj.) | gap % against bounds | served ILP / rule | legacy gap % (status) |
|---|---|---|---|---|---|---|---|---|
| stress4h, 6 bikes | 5 | 2 OPT + 3 TL, 0.14-0.80 % (300 / 600 s) | 941.37 [820.10, 1062.63] | 1581.76 [1289.40, 1874.12] | **40.03 [34.62, 45.45]** | 40.26 [34.86, 45.66] | 0.954 [0.908, 1.000] / 0.754 [0.648, 0.860] | 39.96 [33.58, 46.35] (5 OPT) |
| stress4h-K8 | 5 | 1 OPT + 4 TL, 0.75-2.87 % (1800 s) | 1278.72 [1086.89, 1470.55] | 2435.06 [2261.64, 2608.47] | **47.59 [42.16, 53.03]** | 48.26 [42.35, 54.17] | 0.925 [0.877, 0.973] / 0.653 [0.618, 0.688] | 45.51 [40.76, 50.26] (2 OPT + 3 TL, <= 1.25 %) |
| stress4h-K10 | 5 | 0 OPT + 5 TL, 3.65-13.31 % (600 s) | 1612.86 [1386.83, 1838.89] | 3233.83 [2909.47, 3558.19] | **50.21 [46.99, 53.43]** | 53.77 [50.73, 56.81] | 0.907 [0.859, 0.956] / 0.593 [0.535, 0.650] | 46.93 [43.03, 50.82] (5 TL, <= 1.93 %) |
| stress8h, 6 bikes | 3 | 0 OPT + 3 TL, 4.86-8.98 % (600 s) | 1965.90 [1437.69, 2494.11] | 3570.44 [1119.00, 6021.88] | **42.77 [13.51, 72.03]** | 46.96 [20.36, 73.57] | 0.910 [0.805, 1.014] / 0.729 [0.431, 1.028] | 47.91 [13.60, 82.23] (3 TL, <= 1.49 %) |

Per-seed gaps (end-adjusted): 6 bikes 33.5, 38.8, 41.3, 45.4, 41.2; 8 bikes 53.5, 45.3, 51.0, 44.6, 43.6; 10 bikes
53.3, 50.9, 51.7, 47.4, 47.7. The best rule is r2 on 5/5 K8 instances, r2 on 1/5 and M2 on 4/5 at 6 bikes, r2 on 3/5
at 10 bikes (legacy: M2 on 4/5, 2/5 and 4/5).

Welch two-sample tests on the per-seed gaps (unpaired: each fleet size has its own instances; orders scale with the
fleet at 8 per bike, so fleet and demand are confounded):

| step | new prices: difference, t (df), p | new prices, bound-based gaps: p | legacy prices: difference, p |
|---|---|---|---|
| 6 -> 8 bikes | +7.56 points, t 2.73 (8.0), **p 0.026** | 0.024 | +5.55, p 0.092 |
| 8 -> 10 bikes | +2.62 points, t 1.15 (6.5), p 0.29 | 0.061 | +1.42, p 0.54 |
| 6 -> 10 bikes | +10.18 points, t 4.48 (6.5), **p 0.003** | 0.0008 | +6.97, p 0.038 |
| 6 bikes, 4 h -> 8 h | +2.74 points, t 0.39 (2.3), p 0.73 | - | +7.95, p 0.43 |

### 3.3 Written targets at 6 bikes: gap and price of recovery

Relaxed reference per seed = best-known incumbent over all R6 relaxed solves of the same instance at the new prices
(psweep with its 600 s retries on seeds 1-3, this stage's 300 s solve, the fleet grid's K6_B2_pack0.6 cell with its
600 s retries on seeds 1-2, the network stage's 300 s solve) with the largest proven bound among them: seed 1 takes its
incumbent from the fleet retry, the other seeds from psweep; the bounds of seeds 1 and 2 come from the network solve.
The relaxed MIP gap shown is that incumbent against that bound.

| seed | written ILP raw (status, MIP gap) | written bound | relaxed ILP raw (status) | relaxed bound | PoR raw (USD) | proven bracket | PoR end-adj. | gap written / relaxed % | legacy PoR raw (status) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 786.39 (OPTIMAL) | 786.39 | 785.62 (OPTIMAL) | 785.62 | **0.77** (0.10 % of the relaxed optimum) | [0.77, 0.77] | -0.07 | 33.47 / 33.46 | 0.65 (OPT) |
| 1 | 1034.34 (TL, 1.15 %) | 1022.48 | 1028.75 (TL, 0.80 %) | 1020.49 | 5.59 | [0, 13.85] | 4.72 | 38.54 / 38.82 | 3.87 (TL) |
| 2 | no incumbent (TL) | 1008.74 | 1013.76 (TL, 0.31 %) | 1010.63 | - | [0, ?] | - | - / 41.32 | 3.60 (TL) |
| 3 | 1007.82 (TL, 4.90 %) | 958.45 | 957.11 (TL, 0.14 %) | 955.81 | 50.70 | [1.34, 52.01] | 50.16 | 42.50 / 45.36 | 6.70 (TL) |
| 4 | 921.93 (TL, 1.20 %) | 910.88 | 911.96 (OPTIMAL) | 911.92 | 9.97 | [0, 9.97] | 9.21 | 40.62 / 41.21 | 1.16 (OPT) |

Gap under the written targets 38.78 % [32.58, 44.98] (n 4; served share 0.948 [0.884, 1.011]) against 39.71 %
[31.81, 47.62] under the relaxed targets on the same four seeds: -0.93 [-3.01, 1.15] points, of which seed 3 alone
contributes -2.86 (its written solve has a 4.9 % MIP gap). Legacy: 39.80 % [33.59, 46.01] (n 5), -0.22 points. The price
of recovery is established only where a solve is optimal: 0.77 USD on seed 0 and at most 9.97 USD on seed 4; on seeds
1 and 3 it lies in [0, 13.85] and [1.34, 52.01] USD and on seed 2 it is unknown (>= 0). The 4-seed mean of the
estimates, 16.76 USD [-19.74, 53.26], is dominated by the MIP gap of seed 3 and should not be quoted; without seed 3 the
three resolved or near-resolved seeds average 5.4 USD (legacy on the same three seeds 1.89 USD). With the written
targets the LP value of a spare rises to 2.28 USD [0.24, 4.31] (relaxed 0.70) and that of a charger to 0.75 [-0.06, 1.56]
(relaxed 0.03).

### 3.4 End-target grid (rho x R_end + periodic bracket, seeds 0-2, 300 s)

Price of recovery per seed against the best-known relaxed solve of the seed (Section 3.3: seed 0 optimal 785.620;
seeds 1 and 2 time-limited, incumbents 1028.748 and 1013.761 against the largest bounds 1020.491 and 1010.626, i.e.
0.80 and 0.31 %). "none" = time-limited without incumbent; the lower bound then comes from the variant's solver bound.

| targets | seeds with incumbent (OPT / TL) | PoR raw, seed 0 | seed 1 | seed 2 | proven bracket per seed (USD) | MIP gap per seed | gap to best rule % (seeds with incumbent) | legacy PoR raw per seed (status) |
|---|---|---|---|---|---|---|---|---|
| rho 0, R_end 0 (relaxed, reference) | 0, 1, 2 (1 / 2) | 0 | 0 | 0 | - | 0.00, 0.80, 0.31 | 37.9 (n 3) | 0, 0, 0 (3 OPT) |
| rho 0.25, R_end 0 | 0, 1, 2 (1 / 2) | **0.48** | 10.57 | (728.1, unusable) | [0.48, 0.48]; [0, 18.83]; [0, 731.2] | 0.00, 1.78, 42.13 | 36.6 (seeds 0-1) | 0.37, 0.71, 1.99 (2 OPT + 1 TL) |
| rho 0.5, R_end 0 | 0, 1 (1 / 2) | **0.77** | 1.00 | none | [0.77, 0.77]; [0, 9.25]; [0, ?] | 0.00, 0.72, - | 36.1 (n 2) | 0.65, 3.35, 4.99 (1 OPT + 2 TL) |
| rho 1, R_end 0 | none (0 / 3) | none | none | none | [0, ?]; [9.23, ?]; [55.39, ?] | - | - | 1.62 (seed 0 OPT; seeds 1-2 not run) |
| rho 0, R_end 1 | 0, 1 (1 / 2) | **0.77** | 5.59 | none | [0.77, 0.77]; [0, 13.85]; [0, ?] | 0.00, 1.15, - | 36.0 (n 2) | 0.65, 3.97, 8.51 (1 OPT + 2 TL) |
| rho 0.25, R_end 1 | 0, 1 (1 / 2) | **0.77** | 5.59 | none | [0.77, 0.77]; [0, 13.85]; [0, ?] | 0.00, 1.15, - | 36.0 (n 2) | 0.65, 3.62, 5.17 (1 OPT + 2 TL) |
| rho 0.5, R_end 1 (written) | 0, 1 (1 / 2) | **0.77** | 5.59 | none | [0.77, 0.77]; [0, 13.85]; [0, ?] | 0.00, 1.15, - | 36.0 (n 2) | 0.65, 3.87, 3.60 (1 OPT + 2 TL) |
| rho 1, R_end 1 | 0, 2 (0 / 3) | 69.68 | none | 172.16 | [0, 69.68]; [9.23, ?]; [55.39, 175.29] | 8.16, -, 9.85 | 29.6 (n 2) | not run |
| periodic bracket | 2 (0 / 3) | none | none | 148.68 | [0, ?]; [9.23, ?]; [55.39, 151.81] | -, -, 8.03 | 32.8 (n 1) | 1.62 (OPT), none, 37.30 (TL) |

Reading: on seed 0 the solver proves that every cell with rho <= 0.5 costs 0.48-0.77 USD (the written optimum
786.39 is also optimal for rho 0 / R_end 1 and rho 0.25 / R_end 1, and rho 0.5 / R_end 0 reaches the same value). On
seed 1 the same cells are bracketed within 9-19 USD (0.9-1.8 % of the relaxed cost). Requiring full battery return
(rho 1, both R_end values, and the periodic bracket) has a 300 s solver bound (1037.98 on seed 1 in all three cells,
none of which found an incumbent; 1069.15 on seed 2) above the best-known relaxed incumbent (1028.748 and 1013.761, both
time-limited), so its raw price is at least 9.23 and 55.39 USD there; on seed 0 the rho = 1 bounds (785.52-785.57) lie
below the relaxed optimum 785.620 and prove nothing. Where an incumbent exists (rho 1 / R_end 1 on seeds 0 and 2,
periodic on seed 2) the upper ends are 69.7, 175.3 and 151.8 USD, with MIP gaps of 8-10 %. The ILP's served share is 0.96 in the
rho <= 0.5 cells on seeds 0-1 and 0.81-0.96 under full battery return.

### 3.5 LP operating values of one more spare and one more charger per site

LP relaxation of the aggregated model with the fixed site sizes free; value = reduced cost plus the set-up coefficient
(27), USD per site and window, mean over the three sites and then over seeds. Set-up costs 0.332 USD per spare and
0.082 USD per charger per 4-h window (0.664 / 0.164 per 8-h window).

| cell (targets) | n | spare: new prices | spare: legacy | paired new - legacy | spare / set-up (new) | charger: new prices | charger: legacy | paired new - legacy | charger / set-up (new) |
|---|---|---|---|---|---|---|---|---|---|
| 6 bikes (relaxed) | 5 | **0.70 [0.17, 1.24]** (median 0.73; > set-up on 4/5 seeds) | 0.45 [-0.00, 0.90] | +0.25 [-0.36, 0.87] | 2.1 | **0.03 [-0.02, 0.08]** (> set-up on 1/5) | 0.07 [-0.08, 0.21] | -0.04 [-0.21, 0.14] | 0.4 |
| 6 bikes (written) | 5 | 2.28 [0.24, 4.31] | 1.04 [0.08, 2.00] | +1.24 [-0.48, 2.95] | 6.9 | 0.75 [-0.06, 1.56] | 0.46 [-0.26, 1.19] | +0.29 [-0.50, 1.08] | 9.1 |
| 8 bikes (relaxed) | 5 | **9.81 [4.64, 14.98]** | 2.79 [0.61, 4.98] | +7.01 [3.04, 10.99] | 29.5 | **8.78 [2.60, 14.96]** | 1.29 [0.20, 2.38] | +7.49 [1.56, 13.42] | 107 |
| 10 bikes (relaxed) | 5 | **77.95 [38.30, 117.60]** | 21.87 [12.12, 31.62] | +56.08 [24.30, 87.85] | 235 | **65.86 [29.70, 102.03]** | 16.67 [7.20, 26.15] | +49.19 [20.57, 77.82] | 803 |
| 6 bikes, 8 h (relaxed; per 8-h window) | 3 | 1.25 [-0.26, 2.76] | 0.39 [0.19, 0.58] | +0.86 [-0.52, 2.25] | 1.9 | 0.41 [-0.60, 1.42] | 0.03 [-0.09, 0.14] | +0.38 [-0.65, 1.41] | 2.5 |

Per seed the new-price spare value is 0.7-4.5 times the legacy one at 6 bikes (1.62, 1.20, 0.74, 1.84, 4.52), 2.0-7.6
times at 8 bikes and 2.8-4.3 times at 10 bikes. The spread across the three sites of an instance is 0.68 USD at 6
bikes, 1.19 at 8 and 2.41 at 10 (small against the levels). Stock-out slot-sites at 6 bikes: ILP 91.0 (seeds 0-2 of
this stage; legacy 84.4) vs rule 70.8.

### 3.6 Served shares and lateness

| cell | ILP served, new | best rule served, new | ILP - rule | ILP served, legacy | rule served, legacy | paired ILP served, new - legacy | ILP late > 60 min, new | rule late > 60 min, new |
|---|---|---|---|---|---|---|---|---|
| 6 bikes (relaxed) | 0.954 [0.908, 1.000] | 0.754 [0.648, 0.860] | +0.200 | 0.875 | 0.754 | +0.079 [0.058, 0.101] | 0.0 | 0.2 |
| 6 bikes (written) | 0.948 [0.884, 1.011] (n 4) | 0.754 | +0.19 | 0.871 | 0.754 | - | 0.0 | 0.2 |
| 8 bikes | 0.925 [0.877, 0.973] | 0.653 [0.618, 0.688] | +0.272 | 0.866 | 0.631 | +0.059 [0.017, 0.101] | 0.0 | 0.4 |
| 10 bikes | 0.907 [0.859, 0.956] | 0.593 [0.535, 0.650] | +0.315 | 0.872 | 0.573 | +0.035 [0.018, 0.052] | 0.0 | 0.2 |
| 6 bikes, 8 h | 0.910 [0.805, 1.014] | 0.729 [0.431, 1.028] | +0.181 | 0.878 | 0.726 | +0.031 [0.005, 0.057] | 0.0 | 1.0 |

The rules do not read the prices (M2+M3 reads P only through the stock-out value, and it never wins here), so the
rule's served share changes only where the identity of the best rule changes (8 and 10 bikes: +0.022 and +0.020 from
r2 replacing M2 on two seeds each).

## 4. Comparison with the legacy prices on the same instances

| quantity | legacy (P 30 / v 36) | new (P 60 / v 15) | paired new - legacy | verdict |
|---|---|---|---|---|
| gap, 6 bikes | 39.96 % (5 OPT) | 40.03 % (2 OPT + 3 TL <= 0.80 %) | +0.07 [-3.55, 3.69], up on 2/5 | unchanged |
| gap, 8 bikes | 45.51 % (<= 1.25 %) | 47.59 % (1 OPT + 4 TL <= 2.87 %, 1800 s) | +2.08 [-4.54, 8.70], up on 3/5 | not distinguishable |
| gap, 10 bikes | 46.93 % (<= 1.93 %) | 50.21 % (5 TL, 3.65-13.31 %; <= 53.77 against bounds) | +3.28 [-1.53, 8.09], up on 3/5 | not distinguishable; new value a lower bound |
| gap, 8 h | 47.91 % (<= 1.49 %) | 42.77 % (3 TL, 4.86-8.98 %; <= 46.96) | -5.14 [-11.10, 0.81], down on 3/3 | lower on seeds 1-2 even against the new bounds (legacy 53.6 / 58.0 vs brackets [48.8, 51.4] / [50.3, 54.8]); seed 0 undecided |
| Welch 6 -> 10 / 8 -> 10 | p 0.038 / 0.54 | p 0.003 / 0.29 | - | same pattern, sharper |
| written gap, 6 bikes | 39.80 % (n 5) | 38.78 % (n 4) | -0.9 points vs relaxed on the same seeds (legacy -0.22) | same sign; new value within solver noise |
| PoR, 6 bikes | 3.20 [0.18, 6.21] USD (n 5; proven lower bounds 0.65, 1.41, 0, 0.07, 1.11) | exact 0.77 (seed 0); <= 9.97 (seed 4); [0, 13.85], [1.34, 52.01] (seeds 1, 3); unknown (seed 2) | - | small where resolved; unresolved on 3/5 seeds |
| grid, rho <= 0.5 cells | <= 4.38 USD mean per cell (all 3 seeds) | 0.48-0.77 USD exact on seed 0; <= 9.3-18.8 USD on seed 1; seed 2 unresolved | - | consistent; seed 2 missing |
| grid, full battery return | periodic >= 11.73 USD on seed 2 (TL); rho 1 / R_end 0 1.62 USD on seed 0 (OPT); rho 1 / R_end 1 not run | >= 9.23 (seed 1) and >= 55.39 USD (seed 2) for rho 1 / R_end 0, rho 1 / R_end 1 and periodic (raw; 300 s bounds against the best-known relaxed incumbents); seed 0 bracket [0, 69.68] for rho 1 / R_end 1 | - | the only grid region with a price clearly above solver noise at both price sets; larger at the new prices |
| LP spare value 6 / 8 / 10 bikes | 0.45 / 2.79 / 21.87 USD | 0.70 / 9.81 / 77.95 USD | +0.25 [-0.36, 0.87] / +7.01 [3.04, 10.99] / +56.08 [24.30, 87.85] | 1.6-3.6 x higher; ordering and break-even (between 6 and 8 bikes) unchanged |
| LP charger value 6 / 8 / 10 bikes | 0.07 / 1.29 / 16.67 USD | 0.03 / 8.78 / 65.86 USD | -0.04 / +7.49 [1.56, 13.42] / +49.19 [20.57, 77.82] | below set-up at 6 bikes under both price sets |
| ILP served share 6 / 8 / 10 / 8 h | 0.875 / 0.866 / 0.872 / 0.878 | 0.954 / 0.925 / 0.907 / 0.910 | +0.079 / +0.059 / +0.035 / +0.031, all intervals above zero | the ILP serves more at the new prices, most at 6 bikes |
| incumbent-less grid / written solves at 300 s | 1 of 24 run | 10 of 27 | - | the new prices make the end-target variants much harder |

Absolute USD costs are not comparable across price sets (the same schedule is priced differently); only gaps, served
shares, Welch statistics and LP values relative to their set-up costs are.

## 5. Interpretation

Shown by the records:

- At the new prices the coordination gap on the stressed family rises along the fleet axis: 40.0 % with 6 bikes,
  47.6 % with 8 and 50.2 % with 10 (the last two are lower bounds; the bound-based upper ends are 48.3 and 53.8 %).
  The steps 6 -> 8 and 6 -> 10 are significant under Welch tests on five seeds each (p 0.026 and 0.003; the
  bound-based gaps give the same verdicts), the step 8 -> 10 is not (p 0.29; bound-based p 0.061). The mechanism is
  service: the ILP keeps its served share at 0.91-0.95 while the best rule falls from 0.75 to 0.59, so the ILP's
  advantage in served orders grows from +0.20 to +0.32 with the fleet.
- The battery side binds from 8 bikes on, as at the legacy prices: the LP value of one more spare is about twice its
  set-up cost at 6 bikes (above it on 4 of 5 seeds), 30 times at 8 bikes and 235 times at 10, and the charger value is
  below its set-up cost at 6 bikes (0.03 vs 0.082 USD) and 100-800 times above it at 8-10 bikes. The ordering is the
  same under both price sets; the levels are 1.6-3.6 times higher because unserved orders are priced at 60 USD.
- Written targets at 6 bikes cost the ILP 0.77 USD on seed 0 (exact) and at most 9.97 USD on seed 4; the gap under the
  written targets is within 1 point of the relaxed gap on the resolved seeds. The rho <= 0.5 cells of the grid cost
  0.48-0.77 USD on seed 0 and at most 9-19 USD on seed 1. Full battery return is proven to cost at least 9.2 USD (seed
  1) and 55.4 USD (seed 2) in raw cost, with upper ends up to 175 USD; seed 0 is not resolved.
- The new prices make the end-target variants of the stressed instance substantially harder: 10 of 27 written / grid
  solves found no feasible solution in 300 s, and all eight 600 s solves of the K10 and 8-h cells stopped with MIP gaps
  of 3.7-13.3 % (legacy prices: <= 1.9 %).

Suggested, not shown:

- A lower gap in the 8-hour window at the new prices (42.8 vs 47.9 %): the direction holds on all three seeds and is
  proven on seeds 1 and 2 against the new bounds, but n is 3 and the interval spans 13.5-72.0 %; nothing can be said
  about day length.
- A continued rise from 8 to 10 bikes: the point estimates (+2.6 points, +5.5 with bounds) point up, the test does
  not resolve it, and fleet and demand are confounded on this axis.
- That the price of recovery at 6 bikes is "a few USD" as at the legacy prices: true where solved (0.77 and <= 9.97),
  unresolved on three seeds; the seed-3 estimate of 50.7 USD is 97 % solver gap.
- The LP values are marginal values of a continuous relaxation; they say where the battery side binds, not what an
  integer spare or charger would return (the fleet x spare grid, where the second spare per site is the last one with
  value under the ILP, is the integer evidence).

## 6. Manuscript items replaced (`manuscript/PENDING_R6.md`)

**Item 5** (rows of Table tab:res:headline with footnote a and the bound list; Section 6.6 fleet-axis paragraph
(47.0 %, 48.0 %, Welch tests); Figure fig:app:gap-vs-fleet; Section S8.1; 7.3 eight-hour window; the recovery rows for 8
and 10 bikes in Table tab:app:recovery are NOT replaced, see below). New statements:

- Table rows: "stress4h-K10, 10 bikes, 80 orders & 5 & 50.21 (46.99-53.43) & 0 optimal, 5 time limit (3.65-13.31 %,
  600 s)"; "stress8h, 6 bikes, 96 orders & 3 & 42.77 (13.51-72.03) & 3 time limit (4.86-8.98 %, 600 s)"; both
  end-adjusted and at the calibrated prices, footnote a no longer needed for them; the bound list reads "... 53.77
  (stress4h-K10), 46.96 (stress8h)".
- 6.6 / S8.1: "At the calibrated prices the gap is 50.2 % (47.0-53.4; n = 5) with ten bikes, a lower bound because all
  five 600 s solves are time-limited with MIP gaps of 3.7-13.3 % (at most 53.8 %, 50.7-56.8, against the proven
  bounds), and 42.8 % (13.5-72.0; n = 3; per seed 29.2, 48.8 and 50.3 %; three time-limited solves with MIP gaps
  4.9-9.0 %, at most 47.0 % against the bounds) in the eight-hour window, too wide to separate the window lengths. The
  gap rises from 40.0 % with 6 bikes to 47.6 % with 8 (42.2-53.0; 1800 s reference solves of the lever experiment, one
  optimal, MIP gaps 0.7-2.9 %) and 50.2 % with 10; the rises from 6 to 8 bikes (+7.6 points, Welch p = 0.026) and from
  6 to 10 (+10.2 points, p = 0.003) are significant, the step from 8 to 10 (+2.6 points, p = 0.29) is not; the
  bound-based gaps give p = 0.024, 0.0008 and 0.061. The ILP's served share is 0.954, 0.925, 0.907 and 0.910 with 6, 8,
  10 bikes and in the eight-hour window against 0.754, 0.653, 0.593 and 0.729 for the best rule."
- Figure fig:app:gap-vs-fleet panel (a) is replaced by `figs/fig_r6_stress_gap_vs_fleet.pdf` (calibrated prices with
  the legacy means as hollow markers).
- 7.3: "the largest ILPs, 10 bikes and 80 orders or 6 bikes and 96 orders, stop at 600 s with MIP gaps of 4-13 % at
  the calibrated prices, so their gaps are lower bounds with bound-based upper ends 3.6 and 4.2 points higher".
- Remaining legacy: the written-target solves with 8 and 10 bikes (11.63 and 29.41 USD on seed 0) were not re-run;
  their rows in Table tab:app:recovery stay labelled legacy or are dropped.

**Item 6** (Figure fig:res:shadow; 6.6 "Battery-side scarcity"; S8.1; 7.1 LP-value sentence; stock-out counts). New
statements:

- "At the calibrated prices one more spare at a site is worth 0.70 USD per site and window with 6 bikes (0.17-1.24;
  n = 5; median 0.73; above its set-up cost of 0.332 USD on four of five seeds), 9.81 USD with 8 bikes (4.64-14.98) and
  77.95 USD with 10 (38.30-117.60), about 2, 30 and 235 times its set-up cost; one more charger is worth 0.03 USD
  (-0.02 to 0.08; below its set-up cost of 0.082 USD), 8.78 USD (2.60-14.96) and 65.86 USD (29.70-102.03). With the
  written targets and 6 bikes a spare is worth 2.28 USD (0.24-4.31) and a charger 0.75 USD (-0.06 to 1.56); in the
  eight-hour window with 6 bikes the values are 1.25 USD (-0.26 to 2.76) and 0.41 USD (-0.60 to 1.42) per eight-hour
  window (n = 3; set-up 0.664 and 0.164 USD). On the same instances the values are 1.6-3.6 times the legacy-price values
  (paired +0.25, -0.36 to 0.87; +7.01, 3.04-10.99; +56.08, 24.30-87.85 USD for a spare with 6, 8 and 10 bikes); the
  ordering and the break-even between 6 and 8 bikes are unchanged. The ILP, which runs stock down on purpose, has 91.0
  site-slot pairs without a full battery per window against 70.8 for the rule with 6 bikes (seeds 0-2) and 97.6 against
  105.8 with 10 bikes."
- 7.1: "LP value of one more spare per site 0.70 to 77.95 USD per window from 6 to 10 bikes against an allocated cost
  of 0.33 USD (calibrated prices)"; the hedge "measured only at the legacy prices" is removed.
- Figure fig:res:shadow panel (a) is replaced by `figs/fig_r6_stress_lp_values.pdf`; panel (b) (stock-out counts) can
  be redrawn from `figs/stress_final_per_instance.csv` and the records.

**Item 7** (6.6 "End-of-window boundary"; Table tab:app:boundary; the stress4h six-bike row of Table tab:app:recovery;
S12.2 sentence; 7.2 recovery sentence; 7.3 price-of-recovery paragraph). Replaced for stress4h with 6 bikes only; the
other families named in the item (nyc4h, the transfer layouts, 8 and 10 bikes) are not covered by this stage. New
statements:

- "At the calibrated prices the price of recovering the written targets on stress4h with 6 bikes is 0.77 USD per window
  on seed 0 (both solves optimal; 0.10 % of the relaxed optimum) and at most 9.97 USD on seed 4 (relaxed solve
  optimal, written solve time-limited at 1.2 %); on seeds 1 and 3 both solves are time-limited and the price lies in
  [0, 13.9] and [1.3, 52.0] USD, and on seed 2 the written solve found no incumbent within 300 s. The gap under the
  written targets is 38.8 % (32.6-45.0; n = 4) against 39.7 % under the relaxed targets on the same seeds (-0.9 points,
  -3.0 to 1.2)."
- Table tab:app:boundary (calibrated prices): the rows of Section 3.4 above; caption: "Calibrated prices (P 60 /
  v 15). ... price of recovery per seed against the best-known relaxed solve of the seed (seed 0 optimal, seeds 1 and 2
  time-limited at 0.80 and 0.31 %); proven bracket from the solver bounds; 'none': time-limited without incumbent."
- 6.6: "On the end-target grid every cell with rho <= 0.5 costs 0.48-0.77 USD on seed 0 (optimal solves) and at most
  9-19 USD on seed 1 by the proven brackets, whereas full battery return (rho = 1, with either R_end, and the periodic
  bracket) is proven to cost at least 9.2 USD on seed 1 and 55.4 USD on seed 2 (300 s solver bounds against the
  best-known relaxed solutions, both time-limited; upper bounds 69.7 USD on seed 0 and 152-175 USD on seed 2; no
  proof on seed 0); ten of the 27 grid and written-target solves found no feasible solution within 300 s, so
  seed 2 is unresolved for rho <= 0.5. The headline is therefore robust to the end-of-window boundary for partial
  recovery (rho <= 0.5) and not for full battery return, at 6 bikes and within the solved part of the grid."
- Table tab:app:recovery row: "Stress, stress4h, calibrated prices & 5 & 1 optimal, 3 TL (1.15-4.90 %), 1 TL without
  incumbent & 0.77 (seed 0, exact), <= 9.97 (seed 4), [0, 13.85] and [1.34, 52.01] (seeds 1, 3), seed 2 unresolved & --".
- 7.2 / 7.3: the 3.20 USD figure is replaced by "below 1 USD on the seed solved to optimality and at most 10 USD on a
  second seed; unresolved on three seeds at 300 s"; the 11.63 / 29.41 USD values (8 and 10 bikes) remain legacy-price
  results.

**Item 15** (Table tab:data:seeds prices column; Table tab:app:coverage-legacy; legacy rows of tab:app:recovery): the
"Stress and sizing" row becomes "calibrated; 300 s (6 bikes), 600 s (10 bikes, 8 h), 1800 s (8-bike reference)"; the
coverage rows read "K10 0 optimal + 5 time limit (3.65-13.31 %); stress8h 0 + 3 (4.86-8.98 %); 6-bike written 1 + 4
(1.15-4.90 %, one without incumbent); grid 6 optimal + 20 time-limited of which 9 without incumbent".

Related but owned by other reports: the eight-bike reference values quoted in the manuscript (46.14 %, "0 optimal,
5 time limit (0.83-10.48 %)", footnote f, item 16's "levers reference") are superseded by the 1800 s retries used here
(47.59 % [42.16, 53.03], 1 optimal + 4 time-limited at 0.75-2.87 %, at most 48.26 % against the bounds); the six-bike
relaxed status after the psweep retries is 2 optimal + 3 time-limited (<= 0.87 % on the psweep rows alone; <= 0.80 %
for the best-known incumbent against the largest bound over all R6 relaxed solves, Section 8) at 300 / 600 s.

## 7. Figures (`figs/`, PDF vector + PNG 300 dpi, Okabe-Ito colours, filled = new prices, hollow = legacy)

- `fig_r6_stress_gap_vs_fleet.pdf/.png`: gap against fleet size (6, 8, 10 bikes, 8-h window) at the new prices with
  per-seed points, exact-t CIs, the bound-based upper ends and the Welch brackets; legacy means alongside; solve status
  under each category.
- `fig_r6_stress_lp_values.pdf/.png`: LP operating value of one more spare (a) and charger (b) per site against fleet
  size, symmetric-log axis, set-up costs as dotted lines, written-target 6-bike value as a diamond, legacy values hollow.
- `fig_r6_stress_boundary.pdf/.png`: end-target grid, price of recovery per seed with proven brackets, open-ended arrows
  for solves without incumbent, legacy per-seed values as grey crosses (redrawn by the verification pass against the
  corrected relaxed references; the gap figure was redrawn too, with no visible change).
- `make_stress_figs.py`: the reader script (recomputes every number of this report and writes the CSV / JSON files).

## 8. Verification corrections (2026-10-20)

Two refuters checked the claims of this report against the records; one claim was refuted by both. This section
records the claim, the verdicts, the recomputation and every number that changed. No solve was run: the reader script
`figs/make_stress_figs.py` was extended to pool more relaxed solves and re-run. All CSV / JSON files and the three
figures were regenerated, and the changes below come from diffing the old and new outputs.

### C5: lower bound of the price of full battery return (refuted by both refuters; corrector agrees)

**Claim as written.** On the end-target grid, the solver bound of the rho = 1 cells (rho1_R0, rho1_R1, periodic) is
1037.98 on seed 1 and 1069.15 on seed 2. That is 8.49 and 55.39 USD above the best-known relaxed incumbents 1029.492
and 1013.761, so full battery return is proven to cost at least that much on those seeds.

**Verdicts.** Both refuters: refuted. Each found the bounds and the seed-2 margin correct, but the seed-1 reference
was not the best-known relaxed incumbent.

**Recomputation (corrector).**

- **Bounds reproduce.** All six seed 1-2 solves stopped at TIME_LIMIT after 300 s. These are the ILP_tl300 rows of
  cell `r5_stress4h_K6`; line numbers below count file lines from 1.
  - Seed 1: rho1_R0 1037.9805 (line 168), rho1_R1 1037.9802 (line 183) and periodic 1037.9802 (line 93). None of the
    three has an incumbent.
  - Seed 2: rho1_R0 1069.1501 (line 173) has no incumbent. rho1_R1 1069.1514 (line 188) has incumbent 1185.920 at a
    MIP gap of 9.85 %. Periodic 1069.1501 (line 98) has incumbent 1162.437 at 8.03 %.
- **The psweep margins reproduce, but seed 1 has a better incumbent.** Against the psweep 600 s retries (psweep lines
  409 and 410; the task text calls them rows 408 and 409, counting from 0), the margins are 8.4886-8.4889 and
  55.3887-55.3900 USD. For seed 1, `outputs/r6_penalty/fleet/records.jsonl` line 251 holds a better solve of the same
  instance:
  - cell K6_B2_pack0.6, seed 1, rho0_R0, P60_w18_v15;
  - the 600 s server retry of line 110 (`retry_of` 109, `retry_worse` False), so it supersedes that line under
    last-row-per-key;
  - total 1028.7477, end-adjusted 1030.8227, TIME_LIMIT, own bound 1020.4028 (MIP gap 0.81 %);
  - `check_ok`, `obj_eq_eval` and `identity_24_ok` all True.
- **It is the same instance.** Its `key_md5_rebuilt` (473827b8…) equals this stage's seed-1 rho0_R0 `key_md5`. Its
  `demand_md5` and `orders_md5` are identical, and so are the following:
  - sites (B 2 / C 1 / M 1 / 4 kW), 6 bikes, 48 orders and `p_ch_kw`;
  - n_vars 491851, n_rows 29212, n_binaries 224334 and n_arcs 3081416;
  - C_setup 38.328 and the rule totals (r2 1959.240, M2 1683.510).

  `pack_kwh` differs only in float representation (0.6 against 0.6000000000000001).
- **The row was on disk before this report.** Its `wall_clock` is 2026-10-20 01:32:30. The records' clock runs
  4 h ahead of the laptop's EDT, so that is 21:32 EDT on 10-19. The fleet `records.jsonl` was last modified at
  23:52 EDT, before this report was written at 00:14 EDT.
- **Why the original reference missed it.** `make_stress_figs.py` took the relaxed reference only from psweep and this
  stage's rho0_R0 rows.
- **Corrected lower bound, seed 1.** 1037.9802 - 1028.7477 = **9.23 USD** (9.2325-9.2328 over the three cells). The
  8.49 USD figure is a valid but weaker bound.
- **Seed 2 is unchanged.** The fleet retry (line 255, 1013.939) is above the psweep / network incumbent 1013.761, so
  55.39 USD stands.
- **Seed 0 proves nothing.** Its rho = 1 bounds (785.52-785.57) lie below the relaxed optimum 785.620.
- **End-adjusted figures not adopted.** The refuters' end-adjusted figures (about 7.16 and 53.57 USD) assume that the
  end adjustment of a rho = 1 schedule is non-negative. Recorded rho = 1 incumbents show +0.45 to +0.48, but no proof
  exists, so the report keeps the raw objective, as it does everywhere.

**Corrected statement.** On the end-target grid (stress4h, 6 bikes, new prices, raw objective, 300 s per solve),
every rho = 1 cell of seeds 1 and 2 (rho1_R0, rho1_R1, periodic) stopped at the time limit.
- The solver bounds are 1037.98 on seed 1, where none of the three cells has an incumbent, and 1069.15 on seed 2.
- The best-known relaxed incumbents of the same instances are 1028.748 on seed 1 (fleet-grid 600 s retry) and
  1013.761 on seed 2 (psweep 600 s retry). Both are time-limited.
- Full battery return is therefore proven to raise the raw cost by at least 9.23 USD on seed 1 and 55.39 USD on
  seed 2. Seed 0 is not resolved.

### Consequential change: the relaxed reference pools every R6 relaxed solve of the instance

The report states that it uses "the best-known incumbent and the largest bound per seed". The corrector applied that
rule to all R6 relaxed solves of the same 6-bike instances at the new prices:
- psweep, with its retries;
- this stage's rho0_R0 solves;
- the fleet grid's K6_B2_pack0.6 cell, last row per key, `retry_worse` ignored;
- the network stage's relaxed ILP rows. These were checked to be the same instance on demand_md5, n_vars,
  n_binaries, C_setup and prices, and to have `check_ok` True. The script now asserts these checks.

The rl stage's 300 s rows repeat the psweep 300 s incumbents and have no larger bound, so they change nothing. The
pooled references are:

| seed | incumbent (source) | largest bound (source) | MIP gap of the pair | before the correction |
|---|---|---|---|---|
| 0 | 785.620, optimal (all sources agree) | 785.620 | 0 | unchanged |
| 1 | **1028.748** (fleet K6_B2_pack0.6 retry, 600 s) | **1020.491** (network, 300 s) | **0.80 %** | 1029.492 (psweep) / 1020.490 / 0.87 % |
| 2 | 1013.761 (psweep 600 s; network identical) | **1010.626** (network, 300 s) | **0.31 %** | 1013.761 / 1009.700 / 0.40 % |
| 3, 4 | unchanged (psweep; network identical incumbents, smaller bounds) | unchanged | 0.14 %, optimal | unchanged |

### What changed in the report

**Brief (Section 0)**
- Item 5: "at least 8.5 USD on seed 1" became 9.2 USD. The seed-2 upper bounds went from 153-176 to 152-175 USD. Solve
  status and the raw objective are now stated.

**Problems (Section 1)**
- Item 2: the bracket of rho 0.25 / R_end 0 on seed 2 went from [0, 734] to [0, 731]. The old text value 733.9 also
  disagreed with the old CSV value of 732.13. The new value is 731.21, after the larger seed-2 bound.
- Item 4: the 4-seed mean price of recovery went from 16.6 [-20.1, 53.3] to 16.8 [-19.7, 53.3] USD.
- Item 5: rewritten to list all relaxed sources and the pooled references. The script's own seed-1 PoR now reads
  3.26 against 5.59 USD, previously 4.85.

**Coverage (Section 2)**
- The fleet and network sources were added.
- The K6 relaxed MIP gaps went from 0.14-0.87 % to 0.14-0.80 %; the psweep-only range is kept alongside.

**Fleet axis (Section 3.2)**
- 6-bike row: ILP end-adjusted 941.46 [820.06, 1062.87] became 941.37 [820.10, 1062.63], and the gap
  40.03 [34.61, 45.45] became 40.03 [34.62, 45.45].
- 6-bike row, against the bounds: 40.27 [34.87, 45.68] became 40.26 [34.86, 45.66], and the MIP gaps 0.14-0.87 %
  became 0.14-0.80 %.
- The Welch t for 6 -> 8 went from 2.74 to 2.73. Every p value, verdict and per-seed gap at one decimal is unchanged.

**Written targets (Section 3.3)**
- The reference definition was rewritten.
- Seed 1: relaxed 1029.49 (0.87 %) became 1028.75 (0.80 %), the PoR 4.85 became 5.59 USD, the end-adjusted PoR 4.23
  became 4.72 USD, and the relaxed gap 38.79 % became 38.82 %. The proven bracket [0, 13.85] is unchanged.
- Seed 2: the relaxed bound 1009.70 (0.40 %) became 1010.63 (0.31 %).
- Same-seed relaxed gap: 39.71 [31.80, 47.61] became 39.71 [31.81, 47.62], and the difference -0.92 [-3.01, 1.17]
  became -0.93 [-3.01, 1.15] points.
- The 4-seed PoR mean went from 16.57 [-20.13, 53.27] to 16.76 [-19.74, 53.26] USD, and the 3-seed mean from 5.2 to
  5.4 USD.

**End-target grid (Section 3.4)**
- Reference MIP gaps: 0.87 / 0.40 % became 0.80 / 0.31 %.
- Seed 1 price-of-recovery estimates went up by 0.74 USD in every cell:
  - rho 0.25 / R_end 0: 9.83 became 10.57;
  - rho 0.5 / R_end 0: 0.25 became 1.00, with its upper end 9.26 becoming 9.25;
  - the three R_end 1 cells with rho <= 0.5: 4.85 became 5.59.
- Seed 1 lower ends of rho1_R0, rho1_R1 and periodic: 8.49 became 9.23.
- Seed 2 upper ends: rho1_R1 176.22 became 175.29, periodic 152.74 became 151.81, and rho 0.25 / R_end 0 733.9 became
  731.2.
- The reading paragraph was rewritten with the corrected C5 statement.

**Comparison, interpretation and manuscript statements (Sections 4-6)**
- Section 4, 6-bike gap row: "<= 0.87 %" became "<= 0.80 %", and the paired interval [-3.56, 3.69] became
  [-3.55, 3.69].
- Section 4, full-return row: 8.49 became 9.23.
- Section 5: 8.5 became 9.2 USD and "up to 176" became "up to 175".
- Section 6, item 7 text for 6.6: 8.5 became 9.2 USD and 153-176 became 152-175 USD.
- Section 6, caption of tab:app:boundary: 0.87 / 0.40 % became 0.80 / 0.31 %.
- Section 6, six-bike status note: qualified.
- Section 6, item 5 statements: no change, because the rounded values (40.0 %, p 0.026 / 0.003 / 0.29, bound-based
  0.024 / 0.0008 / 0.061) are unchanged.

**Figures and files (Section 7)**
- `fig_r6_stress_boundary` was redrawn. The seed-1 square markers move right by 0.74 USD, the seed-1 rho = 1 arrows
  start at 9.23, and the seed-2 brackets end 0.93 USD lower.
- `fig_r6_stress_gap_vs_fleet` was redrawn; the 6-bike bound marker moved by 0.01 point, which is not visible.
- `fig_r6_stress_lp_values` and every LP number are unaffected.
- The per-instance, written and boundary CSVs and `stress_final_summary.json` were regenerated.

**Unchanged.** The K8, K10 and stress8h cells, the LP values, served shares and lateness, and every legacy-price
number. No R6 source holds a better solve of the K8 reference, K10 or stress8h instances. The levers_ext rows on the
K8 instances are different models: lever variants with another n_vars or set-up cost.

### Noticed but not changed (outside the refuted claim)

- **Seed 4 upper end, written targets.** The report gives the upper end of the written-target PoR on seed 4 as
  9.97 USD, in Sections 0, 3.3 and 6 and in the manuscript statements. That figure treats the OPTIMAL relaxed solve
  as exact. The strictly proven upper end, written incumbent minus relaxed bound, is 921.928 - 911.923 = 10.00 USD,
  as `figs/stress_final_written.csv` (`por_upper`) shows. The 0.03 USD difference is the 0.004 % residual gap that
  Gurobi accepts as optimal. Writing "at most 10.0 USD" would be the strict form.
