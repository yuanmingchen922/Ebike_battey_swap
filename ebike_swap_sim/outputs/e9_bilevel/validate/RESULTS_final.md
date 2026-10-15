# E9.1 validation (final): exhaustive bi-level enumeration (B) vs integrated stochastic ILP (A)

Family `nyc4h_stress2` (6 bikes, 36 orders, H = 48 slots of 5 min, q0 ~ U{3..6} of 12, P_j = 2.8 kW, `usd_sunk` costs);
candidates L01-L04 (the four busiest restaurant cells, `../candidates.csv`); demand scenarios seeds 0 and 1 (p = 1/2);
budget m = 1 (52,150 USD); option grid per location S:B1, S:B2, SC:B1:C1, SC:B2:C1; rule "swap-only sites only next
to a charge-capable object" on. Reposition targets `all_candidates` (every candidate node + the three depots), so (A)
and (B) price every layout on the same arc library. Gurobi 13, Threads 3, Seed 0, TimeLimit 300 s per lower-level
solve and 600 s for the integrated model. Run of 2026-10-14, 44.7 min wall (`wall_time.json`), records in
`records.jsonl` / `results.csv` / `agreement.json`. The first attempt on the 8-bike `nyc4h_stress` family
(`../_first_attempt/`) is superseded and not used here.

Every ILP value below is an upper bound on the written E2 optimum: the lower level moves bikes only into candidate and
depot nodes (E8 convention), and five of the fourteen lower-level solves stopped at the 300 s limit with a 0.8-1.6 %
MIP gap (their incumbents are reported). The R2.4 geometry caveat applies (real restaurants, zone weights and candidate
coordinates on a synthetic 150 m grid).

## Summary

The exhaustive enumeration and the integrated stochastic ILP choose the same layout, L02:SC:B2:C1 (one co-located
site at busiest cell 2, W 29th-30th / 6th Ave, with 2 spare batteries and 1 charger), at the same expected value
V = 676.22 USD per 4 h window, so E9.1 passes. The agreement is exact to 3e-13 on the value and on the layout, but it
is not a gap-0 certificate: the integrated model stopped at its 600 s limit with bound 668.04 (gap 1.21 %) and three of
the eight layouts carry lower-level solves at the 300 s limit, so the formal test is "V_B within [bound_A, incumbent_A]",
which holds with a 13.19 USD tolerance. Combining the per-layout Gurobi bounds, the optimum over the eight layouts lies
in [671.13, 676.22] (0.75 % wide), tighter than the integrated model's own bound. The enumeration had full coverage: 8
layouts, 6 solved on both scenarios, 2 pruned after scenario 0 by the superset bound, no skipped, infeasible, error or
wall-budget rows. The first lesson about sizes is that the second spare is worth about 50 USD per window (7 %) and
raises the served share from 0.68 to 0.79-0.82 for 450 USD of investment, whereas the choice among the three central
locations is worth at most 4.7 USD and is not even certified.

## Chosen layout (budget m = 1, 52,150 USD)

| item | value |
|---|---|
| layout | L02:SC:B2:C1 (co-located swap + charge site at candidate L02, lat 40.74745, lon -73.98687; B = 2 spares, C = 1 charger) |
| investment | 51,300 USD of 52,150 (Fhat 50,000 + 2 x 450 + 400); 850 USD unspent |
| allocated setup C_setup | 12.776 USD per window (12.03 + 2 x 0.332 + 0.082) |
| V (expected total) | 676.223 USD per window = 12.776 + expected opex 663.447 |
| opex per scenario | seed 0: 692.458 (TIME_LIMIT, gap 1.45 %); seed 1: 634.437 (OPTIMAL) |
| served share | 0.819 expected (seed 0: 28 of 36 orders = 0.778; seed 1: 31 of 36 = 0.861) |
| unserved penalty | 240 USD (8 orders) / 150 USD (5 orders) at P = 30 USD each |
| response + lateness | 423 + 18 USD / 468 + 3 USD; late orders 5 / 1 |
| travel, electricity | C_travel 10.78 / 12.73 USD; C_elec 0.68 / 0.71 USD (2.11 / 2.22 kWh purchased) |
| swaps, stock-outs | 5 / 6 swaps at the site; 42 / 40 of 48 slots with no full battery in stock |
| transfers | 0 (a single site has no shuttle services; C_reb = 0) |
| integrated model on the same layout | obj 676.2233 (= the MIP start), bound 668.036, gap 1.21 %, certified by re-evaluation on the layout instance (`certified_ok` true) |

Note on the grid: the E9.1 option grid stops at B = 2, so the 850 USD left in the budget could not buy a third spare
here; the sweep / roles sub-experiments use the full menu (B up to 3, C up to 2).

## All eight enumerated layouts (B), sorted by V

V = C_setup + (OPEX_0 + OPEX_1) / 2. "certified lower bound" = mean of the per-scenario Gurobi bounds (the superset
bound 631.76 stands in for the unsolved scenario of a pruned row). Solve times in seconds (seed 0, seed 1).

| rank | layout | investment USD | C_setup | status | V | certified lower bound | OPEX seed 0 / seed 1 | Gurobi status (gap) seed 0 / seed 1 | served share | solve s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | L02:SC:B2:C1 | 51,300 | 12.776 | OK (best) | 676.223 | 671.126 | 692.458 / 634.437 | TIME_LIMIT (1.45 %) / OPTIMAL | 0.819 | 300.1 / 42.2 |
| 2 | L01:SC:B2:C1 | 51,300 | 12.776 | OK | 679.595 | 671.803 | 691.774 / 641.865 | TIME_LIMIT (1.31 %) / TIME_LIMIT (0.97 %) | 0.792 | 300.0 / 300.1 |
| 3 | L03:SC:B2:C1 | 51,300 | 12.776 | OK | 680.915 | 672.747 | 694.899 / 641.379 | TIME_LIMIT (1.59 %) / TIME_LIMIT (0.78 %) | 0.792 | 300.1 / 300.1 |
| 4 | L01:SC:B1:C1 | 50,850 | 12.444 | OK | 728.996 | 728.996 | 733.310 / 699.794 | OPTIMAL / OPTIMAL | 0.681 | 28.9 / 45.8 |
| 5 | L03:SC:B1:C1 | 50,850 | 12.444 | OK | 730.497 | 730.479 | 733.868 / 702.237 | OPTIMAL / OPTIMAL (0.005 %) | 0.681 | 29.3 / 62.1 |
| 6 | L04:SC:B1:C1 | 50,850 | 12.444 | OK | 745.995 | 745.995 | 754.581 / 712.521 | OPTIMAL / OPTIMAL | 0.639 | 29.9 / 27.6 |
| - | L04:SC:B2:C1 | 51,300 | 12.776 | PRUNED after seed 0 | >= 676.563 | 676.563 | 695.817 / not solved | OPTIMAL / - | 0.750 (seed 0) | 98.0 / - |
| - | L02:SC:B1:C1 | 50,850 | 12.444 | PRUNED after seed 0 | >= 694.588 | 694.588 | 732.530 / not solved | OPTIMAL / - | 0.667 (seed 0) | 26.4 / - |

The grid allows 16 single-location layouts (4 locations x 4 options); the 8 swap-only singletons (S:B1, S:B2) are
excluded by the admissibility rule (a swap-only site with no charge-capable object can never be resupplied), which
leaves the 8 SC layouts above. No two-location layout fits the budget (2 x 50,000 > 52,150).

## Enumeration trace (what was tried, in order, and why)

(B) orders the layouts by their baseline-policy value (cheap screen, run on both seeds), solves scenario 0 then
scenario 1, and prunes as soon as C_setup + p_0 OPEX_0 + p_1 LB_1 reaches the incumbent, where LB_1 = 631.758 is the
superset lower bound of scenario 1 (LP relaxation of the all-open, relaxed-target model: 847,907 arcs on seed 0, bound
666.300 in 29 s; 630,184 arcs on seed 1, bound 631.758 in 24 s). The a-priori skip test C_setup + p_0 LB_0 + p_1 LB_1
(661.5-661.8 USD) never reached the incumbent, so no layout was skipped outright.

| step | layout | baseline screen value | action | outcome | incumbent after step | wall clock |
|---|---|---|---|---|---|---|
| 1 | L03:SC:B1:C1 | 1243.7 | solve seeds 0, 1 (29 s, 62 s; both OPTIMAL) | V 730.50 | 730.50 | 19:15:31 |
| 2 | L01:SC:B1:C1 | 1252.0 | solve seeds 0, 1 (29 s, 46 s; both OPTIMAL) | V 729.00, better by 1.5 | 729.00 | 19:16:57 |
| 3 | L04:SC:B1:C1 | 1271.8 | solve seeds 0, 1 (30 s, 28 s; both OPTIMAL) | V 746.00, worse | 729.00 | 19:18:05 |
| 4 | L03:SC:B2:C1 | 1274.2 | solve seeds 0, 1 (300 s, 300 s; both TIME_LIMIT, gaps 1.59 % / 0.78 %) | V 680.92, better by 48.1 | 680.92 | 19:28:18 |
| 5 | L02:SC:B2:C1 | 1276.8 | solve seeds 0, 1 (300 s TIME_LIMIT gap 1.45 %, 42 s OPTIMAL) | V 676.22, better by 4.7 | 676.22 | 19:34:14 |
| 6 | L04:SC:B2:C1 | 1279.6 | solve seed 0 (98 s, OPTIMAL, OPEX 695.82) | partial bound 12.776 + 347.91 + 315.88 = 676.56 >= 676.22: PRUNED (margin 0.34 USD) | 676.22 | 19:35:59 |
| 7 | L02:SC:B1:C1 | 1295.0 | solve seed 0 (26 s, OPTIMAL, OPEX 732.53) | partial bound 694.59 >= 676.22: PRUNED (margin 18.4 USD) | 676.22 | 19:36:32 |
| 8 | L01:SC:B2:C1 | 1306.3 | solve seeds 0, 1 (300 s, 300 s; both TIME_LIMIT, gaps 1.31 % / 0.97 %) | V 679.60, worse by 3.4 | 676.22 | 19:46:44 |
| A | integrated ILP, MIP start = L02:SC:B2:C1 with its two schedules | - | build 10.5 s (1,501,051 variables, 1,478,747 binaries, 134,439 rows); solve 600 s | start accepted at 676.2233; no better incumbent; 1 node explored; bound 668.04, gap 1.21 % | 676.22 | 19:57:00 |

The baseline screen ranked the one-spare layouts first (baseline values 1244-1272 vs 1274-1306 for two spares), the
opposite of the ILP ranking, so the first three solves produced a weak incumbent (729) and the strong one only
appeared at step 4; the ordering did not change the result, only the pruning power (steps 6-7 would have been pruned
either way once 676.2 was known).

## Agreement (A) vs (B)

| exhaustive V | exhaustive layout | integrated obj | integrated bound | integrated gap | integrated layout | integrated V certified | diff | tolerance | exact | agree | same layout |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 676.223333 | L02:SC:B2:C1 | 676.223333 | 668.036333 | 0.012107 | L02:SC:B2:C1 | 676.223333 | 3.4e-13 | 13.192132 | False | True | True |

Agreement rule: |V_A - V_B| <= 1e-6 + gap_A |V_A| + sum_s p_s gap_s |OPEX_s|, exact only when every gap is 0 and (B)
has full coverage; otherwise V_B must lie within [bound_A, incumbent_A]. Here diff = 3.4e-13 and V_B = 676.22 lies in
[668.04, 676.22], so `agree` = True; `exact` = False because gap_A = 1.21 % and the seed-0 solve of the chosen layout has
gap 1.45 % (tolerance = 0.0007 + 8.19 + 5.00 = 13.19 USD). The integrated model never improved on the MIP start:
`sol_count` 1, `node_count` 1, i.e. it spent the 600 s at the root (LP relaxation plus cuts) and its bound 668.04 is a
root bound of a 1.5 M-variable model. The per-layout bounds give a tighter statement: min over layouts of the certified
lower bound is 671.13 (L02:SC:B2:C1 itself; the others are 671.80, 672.75, 676.56, ...), so the optimum over the eight
layouts is in [671.13, 676.22].

## What the TIME_LIMIT rows mean

* Five of the fourteen lower-level solves (all five on two-spare layouts: L01:B2 both seeds, L03:B2 both seeds,
  L02:B2 seed 0) hit the 300 s limit; Gurobi returned its best incumbent with a 0.78-1.59 % MIP gap after 64-1077
  branch-and-bound nodes. The nine others solved to optimality in 26-98 s, mostly at the root node. Two spares let the
  ILP choose which bikes swap when, so the two-spare models have many more near-equivalent schedules than the one-spare
  models, where the single full battery pins the schedule down.
* The V of such a layout is its incumbent, an upper bound on the layout's true V; the certified interval of the
  layout is [mean of Gurobi bounds, incumbent]: L02 [671.13, 676.22], L01 [671.80, 679.60], L03 [672.75, 680.92].
  These intervals overlap, so the ranking L02 < L01 < L03 among the three central two-spare sites (spread 4.7 USD,
  0.7 %) is NOT certified; what is certified is that any two-spare site at L01-L03 beats every one-spare layout by at
  least 48 USD and that the optimum lies in [671.13, 676.22].
* The two pruned rows are valid regardless of the time limits: pruning compares a lower bound of the pruned layout
  (exact scenario-0 value plus the superset LP bound of scenario 1) with the incumbent, which is itself an upper
  bound of a feasible layout; L04:SC:B2:C1 was pruned by only 0.34 USD, so it is probably within a few USD of the
  best, but its full V is unknown.
* Cache reuse: rows with gap <= 1 % are reusable (`common.reusable_ilp_row`); the three rows with gaps 1.31, 1.45 and
  1.59 % (L01:B2 seed 0, L02:B2 seed 0, L03:B2 seed 0) will be re-solved with the remaining wall budget if any later
  sub-experiment (e.g. the cross-evaluation) needs them under the same key.

## Coverage and solver statistics

* Layouts: 8 enumerated, 6 solved on both scenarios, 2 pruned after scenario 0, 0 skipped by the a-priori bound,
  0 infeasible, 0 SKIPPED_BUDGET, 0 NO_INCUMBENT, 0 ERROR; `full_coverage` = true.
* Solver calls: 14 lower-level ILP solves (9 OPTIMAL, 5 TIME_LIMIT; mean 135 s, median 62 s, max 300.1 s) + 2 LP solves
  for the superset bound = 16 solves, 1943.5 s of solver time (32.4 min of the 44.7 min wall); 34.3 s of library
  building (0.58-0.79 M arcs per layout and scenario); 30 baseline-policy runs (16 for the ordering screen, the rest for
  MIP starts: one solve, L04:SC:B1:C1 seed 0, used the `baseline_reserve` start, all others the default start);
  4 cache hits (the re-pricing of the integrated layout and its MIP-start schedules); 30 cached rows written.
* Integrated model: 600 s TimeLimit reached (runtime 600.2 s), status TIME_LIMIT, 1 incumbent (the MIP start),
  1 node, bound 668.04, gap 1.21 %.
* Wall budget: 7200 s allowed, 2685 s used (superset bound 19:13, exhaustive finished at 34.4 min, integrated at
  44.7 min); nothing was skipped for wall time.

## Anomalies and caveats

1. Not a gap-0 certificate: the integrated model's gap (1.21 %) and the five 300 s lower-level solves mean the
   agreement is "same layout, same value, value inside the bounds", not "both proven optimal". A 1800 s integrated run
   and 600-900 s lower-level limits on the two-spare layouts would be needed to close it.
2. The ranking among L01, L02, L03 with two spares (676.2 / 679.6 / 680.9) is within the solver gaps; L04:SC:B2:C1
   (pruned by 0.34 USD) may also be close. Only the one-spare vs two-spare separation (>= 48 USD) is robust.
3. The integrated model explored a single node in 600 s; on 12 candidates and 3 scenarios it will serve only as a
   bound, as planned (its incumbent is always at least the heuristic's layout because of the MIP start).
4. The baseline screen orders layouts the wrong way round for sizes (it prefers one spare), which cost pruning power
   here and is the same bias that broke the first attempt's greedy; the relaunch's per-role screen and best-singleton
   start address it in the search sub-experiments.
5. 850 USD of the budget stays unspent because the validation grid stops at B = 2; the served share of the chosen
   layout is 0.82, i.e. 5-8 of 36 orders are dropped per window even at the best single site, and the unserved
   penalty (150-240 USD) is the largest cost component after the response cost.
6. The map uses the WGS84 coordinates of `candidates.csv`; distances inside the model are on the synthetic rotated grid.

## Interpretation

On this small instance the two ways of solving the planner's problem agree: enumerating the eight admissible single-site
layouts and pricing each with the operations ILP gives the same answer as one integrated program that chooses the site,
its role and its sizes together with the two scenario schedules, L02 co-located with 2 spares and 1 charger at 676.2 USD
per 4 h window. The integrated program did not find that answer by itself within 600 s: it accepted the enumeration's
layout as a start, never left the root node, and only contributed a lower bound (668.0), so on larger candidate sets the
integrated model is a bound generator and the enumerative or heuristic search is the actual optimiser, exactly the role
split the design assigns. The size lesson is clear and large: at every location the second spare lowers V by 48-52 USD
(7 %) and lifts the served share from 68 % to 79-82 % for 450 USD of investment, whereas the location choice among the
three central cells (L01, L02, L03) is worth at most 4.7 USD and is inside the solver gaps; L04 (Grand Central east) is
clearly worse with one spare (+17 USD) and was pruned with two. This repeats the E8 pattern (the coordinator absorbs
siting differences among central locations) in the stressed regime, but with a twist: stock, not location, is what the
budget should buy first, which is the question the budget sweep and the Pareto curve answer with the full menu. Reading
the cost decomposition, the chosen layout still drops 5-8 of 36 orders per window (150-240 USD of penalty) and its one
charger turns over the two spares only 5-6 times in four hours while the shelf is empty for 40-42 of 48 slots, so the
stressed family does what it was built for: the battery side binds and the facility decision has a price. The
TIME_LIMIT rows show where the computational cost sits, in the two-spare models whose swap timing has many
near-equivalent optima; one-spare models solve at the root in under a minute. Methodologically the validation
establishes that the lower-level evaluator, the layout instances, the superset bound and the integrated model are
mutually consistent (certified re-evaluation matches the integrated objective to 1e-13), so the search sub-experiments
can rely on the same evaluator; it does not establish gap-0 optimality, and every V in this report remains an upper
bound on the written E2 optimum.

## Figures (regenerated from `records.jsonl` and `../candidates.csv`)

* `map_validate_m1.png`: the 12 candidates in WGS84 coordinates, the four validation candidates with the best option
  and V at each, the depots and the chosen site.
* `layouts_m1.png`: V of the eight layouts with the certified intervals, the pruned rows as bounds, and the integrated
  bound.
* `solve_times_m1.png`: lower-level solve time per layout and scenario with the TIME_LIMIT rows and their gaps.
* `map_budget_1.png`: the run's own map on the rotated grid (restaurants, customers of seed 0, depots, chosen site).
