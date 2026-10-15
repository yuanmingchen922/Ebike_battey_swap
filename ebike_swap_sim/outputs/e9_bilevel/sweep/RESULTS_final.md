# E9.2 budget sweep -- greedy + local search per budget with the integrated bound (final report)

Run: `experiments/e9_bilevel_siting.py --sweep --threads 3 --wall-budget 18000`, family `nyc4h_stress2`
(6 bikes, 36 orders, H = 48 slots of 5 min, `q0 ~ U{3..6}` of 12, `P_j = 2.8 kW`, 4 kW grid group, `usd_sunk`
costs), 12 Midtown candidates (`../candidates.csv`), roles S / C / SC, size menu `S: B in {1,2,3}`,
`SC: B in {1,2,3} x C in {1,2}`, hubs `C in {2,4}`, 3 demand scenarios (seeds 0-2, `p = 1/3`), budgets
`m = 1..4` (52,150 / 104,300 / 156,450 / 208,600 USD), `k_screen = 5`, `min_served = 0.5`, swap-only sites only
next to a C / SC object, reposition targets `open_sites`, Gurobi `Threads 3`, `Seed 0`, `TimeLimit 300 s`
(600 s with hubs, 600 s integrated). Finished 2026-10-14 21:30, wall 133.3 min of the 300 min budget.
The first attempt (family `nyc4h_stress`, 8 bikes, degenerate) is superseded and archived under `../_first_attempt/`.

Every ILP value on this family is an upper bound on the written E2 optimum: the lower-level libraries allow
reposition moves only into open-site and depot nodes (E8 convention; `open_sites` is itself an upper bound on
the `all_candidates` value of the same layout), and the R2.4 geometry caveat applies (real restaurants, zone
weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Summary

One co-located site is the answer at every budget: the greedy + local search opens only L02 (W 29th-30th / 6th
Ave, NoMad, the second-busiest restaurant cell and a depot) as an SC site with 2 chargers and 3 spares at
m = 1 (investment 52,150 USD, the whole budget) or 4 spares at m = 2..4 (52,600 USD, leaving 51,700 to
156,000 USD of the budget unused), with expected total cost V = 654.38 / 654.53 USD per 4 h window
(13.19 / 13.52 allocated setup + 641.19 / 641.00 operating), 85.2 % of the orders served, 1.67 late orders,
no transfers. A second site never pays because every priced addition raises V by 11.9-12.2 USD (swap-only or
co-located) or 29.4 USD (charge-only hub) against an operating saving of at most 1.09 USD per window (0.17 %):
the 5-6 orders dropped per scenario are dropped for fleet-time reasons (6 bikes, 36 orders, 4 h), not for lack
of batteries, so extra sites only shorten swap detours and electricity. The integrated stochastic ILP
(5.35 M variables) returned the greedy's layout as its incumbent at all four budgets but produced no usable
bound in 600 s (`-inf` at m = 1, -12,549 at m = 2..4), so the sweep's optimality rests on the lower-level
solves (87 solves, all OPTIMAL, max 75 s) and on the E9.1 validation, where exhaustive enumeration and the
integrated model agreed on L02:SC at m = 1. Two artefacts of the search are flagged below: the m >= 2 layout
(B = 4, V 654.53) is 0.15 USD worse than the m = 1 layout, which stays feasible at every budget (the local
search restarts from the greedy frontier, not from the lower budget's result), and B = 4 lies outside the
size menu (the size +-1 move is bounded only by K_j = 8 / Cbar_j = 4).

## Chosen layout per budget (greedy + local search; the integrated incumbent is the same layout at every budget)

| m | budget USD | layout | sites / roles | B | C | investment USD (share of budget) | C_setup | V | opex (expected) | served share | n_late (lateness USD) | swaps per site (s0/s1/s2) | stock-out slots of 48 (s0/s1/s2) | kWh bought | transfers | C_elec | C_travel | unserved USD | response USD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 52,150 | L02:SC:B3:C2 | L02 co-located | 3 | 2 | 52,150 (100 %) | 13.190 | **654.377** | 641.187 | 0.852 (30.67 / 36) | 1.67 (6.0) | 6 / 6 / 7 | 41 / 38 / 27 | 2.35 | 0 | 0.753 | 11.934 | 160.0 | 462.5 |
| 2 | 104,300 | L02:SC:B4:C2 | L02 co-located | 4 | 2 | 52,600 (50 %) | 13.522 | 654.525 | 641.003 | 0.852 | 1.67 (6.0) | 6 / 6 / 6 | 29 / 23 / 12 | 1.74 | 0 | 0.557 | 11.946 | 160.0 | 462.5 |
| 3 | 156,450 | L02:SC:B4:C2 | L02 co-located | 4 | 2 | 52,600 (34 %) | 13.522 | 654.525 | 641.003 | 0.852 | 1.67 (6.0) | 6 / 6 / 6 | 29 / 23 / 12 | 1.74 | 0 | 0.557 | 11.946 | 160.0 | 462.5 |
| 4 | 208,600 | L02:SC:B4:C2 | L02 co-located | 4 | 2 | 52,600 (25 %) | 13.522 | 654.525 | 641.003 | 0.852 | 1.67 (6.0) | 6 / 6 / 6 | 29 / 23 / 12 | 1.74 | 0 | 0.557 | 11.946 | 160.0 | 462.5 |

Per-scenario totals (USD, allocated setup included): L02:SC:B3:C2 681.19 / 645.88 / 636.06; L02:SC:B4:C2
681.35 / 646.03 / 636.20. Orders served 30 / 31 / 31 of 36 in both. Unserved cost 160 = 5.33 orders x 30 USD
and response cost 462.5 are identical for every one- and two-site layout with B >= 3 (170 / 455 with B = 2 or at
L11), so these components do not depend on the layout. Zone-to-site distance of the chosen site: mean 11.6
blocks (1.75 km), max 22 blocks (MN0402 Hell's Kitchen); no access row in this sub-experiment. The m = 1
layout L02:SC:B3:C2 is feasible at every budget and has the lowest V of all 29 priced layouts, so the
reader should take it as the greedy + LS Pareto point for m = 2..4 as well (anomaly 1).

Cost identities (per window, `usd_sunk`): `C_setup = 12.03 + 0.332 B + 0.082 C` for S / SC,
`29.19 + 0.082 C` for a hub; investment `= 50,000 + 450 B + 400 C` per open site.

## Pareto table: investment vs expected operating cost (all 29 ILP-priced layouts; figure `pareto_final.png`)

| investment USD | layout | C_setup | expected opex | V | note |
|---|---|---|---|---|---|
| 51,700 | L05:SC:B2:C2 | 12.858 | 643.776 | 656.634 | one spare fewer: one more order dropped (served 0.843) |
| 52,150 | **L02:SC:B3:C2** | 13.190 | 641.187 | **654.377** | chosen m = 1; lowest V overall |
| 52,150 | L01:SC:B3:C2 | 13.190 | 641.866 | 655.056 | best singleton of the forward greedy (start) |
| 52,150 | L05:SC:B3:C2 | 13.190 | 641.981 | 655.171 | |
| 52,150 | L07:SC:B3:C2 | 13.190 | 642.486 | 655.676 | |
| 52,150 | L08:SC:B3:C2 | 13.190 | 643.808 | 656.998 | Union Square, southern edge |
| 52,150 | L11:SC:B3:C2 | 13.190 | 645.350 | 658.540 | Hell's Kitchen zone centre; served 0.843 |
| 52,600 | **L02:SC:B4:C2** | 13.522 | 641.003 | 654.525 | chosen m = 2..4 |
| 52,600 | L01:SC:B4:C2 | 13.522 | 641.182 | 654.704 | |
| 52,600 | L05:SC:B4:C2 | 13.522 | 641.303 | 654.825 | |
| 53,000 | L02:SC:B4:C3 | 13.604 | 641.003 | 654.607 | third charger idle: opex unchanged |
| 53,050 | L02:SC:B5:C2 | 13.854 | 641.003 | 654.857 | fifth spare idle: opex unchanged |
| 102,600 | L01:SC:B3:C2 + L07:S:B1:C0 / + L12:S:B1:C0 | 25.552 | 641.682 | 667.234 | one-spare S sites: 0 swaps there |
| 102,950 | L01:SC:B3:C2 + L02 / L03 / L04 / L06 :C:B0:C2 | 42.544 | 641.866 | 684.410 | hub: opex identical to L01 alone, transfers unused |
| 102,950 | L01:SC:B3:C2 + L05:C:B0:C2 | 42.544 | 641.878 | 684.422 | |
| 103,050 | L01:SC:B3:C2 + L12:S:B2:C0 | 25.884 | 641.206 | 667.090 | |
| 103,050 | L02:SC:B4:C2 + L06:S:B1:C0 | 25.884 | 641.003 | 666.887 | local-search add at m = 2..4 |
| 103,450 | L01:SC:B3:C2 + L10:SC:B2:C1 | 25.966 | 640.942 | 666.908 | |
| 103,450 | L01:SC:B3:C2 + L12:SC:B2:C1 | 25.966 | 641.206 | 667.172 | |
| 103,450 | L02:SC:B4:C2 + L06:SC:B1:C1 | 25.966 | 640.961 | 666.927 | local-search add at m = 2..4 |
| 103,500 | L01:SC:B3:C2 + L10:S:B3:C0 | 26.216 | 640.849 | 667.065 | 1-2 swaps at L10 per scenario |
| 103,500 | L01:SC:B3:C2 + L12:S:B3:C0 | 26.216 | 641.053 | 667.269 | |
| 103,850 | L01:SC:B3:C2 + L10:SC:B2:C2 | 26.048 | 640.942 | 666.990 | best gain per USD among additions (still negative) |
| 103,900 | L01:SC:B3:C2 + L10:SC:B3:C1 | 26.298 | 640.789 | 667.087 | |
| 104,300 | L01:SC:B3:C2 + L10:SC:B3:C2 | 26.380 | **640.777** | 667.157 | lowest operating cost found: -1.09 USD vs L01 alone, +13.19 setup |

Reading: the operating-cost frontier is flat. Doubling the investment from 52 k to 104 k USD buys at most
1.09 USD per window of operating cost (0.17 %), while the allocated setup of the second site costs 12.0-13.2
USD (S / SC) or 29.4 USD (hub). The investment actually used by the planner is 52,150-52,600 USD at every
budget; the Pareto "curve" is a single point plus the 450 USD fourth spare.

## Integrated stochastic ILP (A) per budget: incumbent, bound, agreement with the greedy

| m | status | runtime s | build s | variables (binaries) / rows | MIP start (greedy layout) | incumbent layout | obj | bound | gap | V certified on the lower level | greedy V | greedy = incumbent |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | TIME_LIMIT (600 s) | 600.4 | 43.2 | 5,346,292 (4,955,308) / 465,149 | accepted, 654.377 | L02:SC:B3:C2 | 654.377 | -inf (root relaxation unfinished) | inf | 654.377 (ok) | 654.377 | yes |
| 2 | TIME_LIMIT | 602.7 | 28.6 | same | accepted, 654.525 | L02:SC:B4:C2 | 654.525 | -12,548.6 | 20.17 | 654.525 (ok) | 654.525 | yes |
| 3 | TIME_LIMIT | 610.1 | 29.9 | same | accepted, 654.525 | L02:SC:B4:C2 | 654.525 | -12,548.6 | 20.17 | 654.525 (ok) | 654.525 | yes |
| 4 | TIME_LIMIT | 600.9 | 33.7 | same | accepted, 654.525 | L02:SC:B4:C2 | 654.525 | -12,548.6 | 20.17 | 654.525 (ok) | 654.525 | yes |

The integrated model (12 candidates x 3 roles, 3 scenario copies, all-candidates reposition template) never
improved on its warm start and its root bound is useless at this size, so it confirms the greedy's incumbent
but certifies nothing; the only exact check of this design remains E9.1 (4 candidates, 2 scenarios, m = 1:
exhaustive = integrated at L02:SC:B2:C1, V 676.2, bound 668.0, `../validate/RESULTS.md`), which also points
to L02:SC. The greedy's own values are exact lower-level optima (87 solves, max gap 9.5e-5).

## Greedy search, step by step (figure `greedy_trajectory_final.png`)

Rules (DECISIONS "E9 relaunch decisions", E9R.3): every move is first priced on all 3 scenarios by the R2.3
baseline policy (milliseconds), the `k_screen = 5` best by baseline value per role (singletons and forward
additions) or overall (local search) are priced by the lower-level ILP; the search starts from the usable
singleton with the lowest ILP V; an addition is accepted only if V falls (ranked by gain per investment
dollar); the local search per budget is first-improvement over add / drop / swap / role / size +-1 /
exchange, at most 3 passes, restarting from the best frontier layout affordable at that budget.

### Step 0: singletons (72 admissible SC singletons screened; S alone inadmissible without a charger, C alone has no swap)

| order | layout | investment | baseline screen V | ILP V | served | decision |
|---|---|---|---|---|---|---|
| 1 | L05:SC:B3:C2 | 52,150 | 1016.9 (screen rank 1) | 655.171 | 0.852 | usable |
| 2 | L11:SC:B3:C2 | 52,150 | 1068.7 | 658.540 | 0.843 | usable |
| 3 | L08:SC:B3:C2 | 52,150 | 1068.9 | 656.998 | 0.852 | usable |
| 4 | L01:SC:B3:C2 | 52,150 | 1072.3 | **655.056** | 0.852 | **start** (lowest ILP V of the five) |
| 5 | L05:SC:B2:C2 | 51,700 | 1072.3 | 656.634 | 0.843 | usable |

L02:SC:B3:C2, the eventual best layout, ranked 6th in the baseline screen (1077.5) and was not priced here;
it entered only through the local search (step 2). The screen's favourite L05 is 4th by the ILP.

### Step 1: forward addition to L01:SC:B3:C2 (121 admissible additions within 208,600 USD screened; 5 per added role priced)

| added item | role | investment of pair | baseline screen V | ILP V | delta V vs 655.056 | gain per USD | why rejected |
|---|---|---|---|---|---|---|---|
| L02:C:B0:C2 | C | 102,950 | 1101.6 | 684.410 | +29.354 | -5.78e-4 | hub adds F_hub 29.19 + 0.16; opex unchanged (641.866), transfers unused |
| L03:C:B0:C2 | C | 102,950 | 1101.6 | 684.410 | +29.354 | -5.78e-4 | same |
| L04:C:B0:C2 | C | 102,950 | 1101.6 | 684.410 | +29.354 | -5.78e-4 | same |
| L05:C:B0:C2 | C | 102,950 | 1101.6 | 684.422 | +29.366 | -5.78e-4 | same |
| L06:C:B0:C2 | C | 102,950 | 1101.6 | 684.410 | +29.354 | -5.78e-4 | same |
| L10:S:B3:C0 | S | 103,500 | 1019.0 | 667.065 | +12.009 | -2.34e-4 | 1-2 swaps at L10; opex -1.02 vs setup +13.03 |
| L12:S:B2:C0 | S | 103,050 | 1023.2 | 667.090 | +12.034 | -2.36e-4 | opex -0.66 vs setup +12.69 |
| L12:S:B3:C0 | S | 103,500 | 1023.5 | 667.269 | +12.213 | -2.38e-4 | |
| L12:S:B1:C0 | S | 102,600 | 1028.4 | 667.234 | +12.178 | -2.41e-4 | 0 swaps at L12 |
| L07:S:B1:C0 | S | 102,600 | 1029.3 | 667.234 | +12.178 | -2.41e-4 | 0 swaps at L07 |
| L10:SC:B2:C1 | SC | 103,450 | 1019.0 | 666.908 | +11.852 | -2.31e-4 | opex -0.92 vs setup +12.78 |
| L10:SC:B2:C2 | SC | 103,850 | 1019.2 | 666.990 | +11.934 | -2.31e-4 | best gain per USD of the step ("best rejected") |
| L10:SC:B3:C1 | SC | 103,900 | 1019.2 | 667.087 | +12.031 | -2.32e-4 | |
| L10:SC:B3:C2 | SC | 104,300 | 1019.3 | 667.157 | +12.101 | -2.32e-4 | lowest opex of all (640.777) but setup +13.19 |
| L12:SC:B2:C1 | SC | 103,450 | 1023.4 | 667.172 | +12.116 | -2.36e-4 | |

`forward_stop`: "no improving addition". Frontier = [L01:SC:B3:C2]; no three-site layout was ever priced,
because no two-site layout beat the singleton.

### Step 2: local search per budget

| budget | pass | start | move priced (screen order) | baseline V | ILP V | decision |
|---|---|---|---|---|---|---|
| m = 1 | 1 | L01:SC:B3:C2 (655.056) | swap -> L05:SC:B3:C2 | 1016.9 | 655.171 (cached) | no |
| | | | swap -> L11:SC:B3:C2 | 1068.7 | 658.540 (cached) | no |
| | | | swap -> L08:SC:B3:C2 | 1068.9 | 656.998 (cached) | no |
| | | | swap -> L02:SC:B3:C2 | 1077.5 | **654.377** | **accepted** (-0.679) |
| m = 1 | 2 | L02:SC:B3:C2 (654.377) | swaps -> L05 / L11 / L08 / L01 :SC:B3:C2 | 1016.9-1072.3 | cached | no |
| | | | swap -> L07:SC:B3:C2 | 1081.1 | 655.676 | no; pass without improvement -> stop |
| m = 2 | 1 | L01:SC:B3:C2 (655.056), restart from the frontier | swap -> L05:SC:B3:C2 | 1016.9 | 655.171 (cached) | no |
| | | | size B+1 -> L01:SC:B4:C2 | 1017.3 | 654.704 | **accepted** (-0.352) |
| m = 2 | 2 | L01:SC:B4:C2 (654.704) | swap -> L02:SC:B4:C2 | 1008.6 | 654.525 | **accepted** (-0.179) |
| m = 2 | 3 | L02:SC:B4:C2 (654.525) | size C+1 -> L02:SC:B4:C3 | 1008.8 | 654.607 | no |
| | | | size B+1 -> L02:SC:B5:C2 | 1008.8 | 654.857 | no |
| | | | swap -> L05:SC:B4:C2 | 1012.6 | 654.825 | no |
| | | | add L06:S:B1:C0 | 1014.2 | 666.887 | no |
| | | | add L06:SC:B1:C1 | 1014.5 | 666.927 | no; max_passes = 3 reached -> result L02:SC:B4:C2 |
| m = 3, 4 | 1-3 | L01:SC:B3:C2 | identical path (all layouts cached, 0 new solves); the 11 extra two-site additions affordable at m >= 3 (second SC:B3:C2, 104,750 USD) rank below the top 5 of the screen | | | result L02:SC:B4:C2 |

The order within a pass is reconstructed from the first-improvement rule and the recorded baseline ranking
(`records.jsonl` stores every priced layout and its baseline value, not the pass index). Moves never tried:
drop / exchange (one open site), role flips of L02 to S (inadmissible without a charger) or to C (no swap).

## Coverage and wall budget

* Layouts priced by the ILP: 29 (5 singletons, 15 forward additions, 9 local-search moves), 87 lower-level
  solves, status OPTIMAL 87 / 87 (max MIP gap 9.5e-5), 0 TIME_LIMIT, 0 ERROR, 0 LOW_SERVICE, 0 infeasible,
  0 SKIPPED_BUDGET; `search_complete = True` at every budget; `class_counts = {OK: 29}`.
* Solve times: mean 29.3 s, median 25.3 s, max 75.3 s (L07:SC:B3:C2, seed 0); solver time 2,548 s;
  library builds 2,279 s (0.49-0.81 M arcs per layout-scenario, `open_sites` targets); MIP start accepted in 54 / 87.
* Baseline screen: 1,449 policy runs on 454 distinct layouts (91 one-site, 363 two-site); cache hits 2,871
  (re-evaluations of chosen layouts and the screens of m = 3, 4); 1,469 rows in the shared cache (`e9-2`).
* Integrated runs: 4 x 600 s, all TIME_LIMIT, 43 / 29 / 30 / 34 s build; certification of the incumbent on
  the lower-level sub-libraries OK in all four.
* Timeline (wall clock): launch 19:17; scenario and template libraries (1.90 / 1.54 / 1.50 M arcs) to 19:24;
  singletons 19:24-19:31; forward step 19:31-20:11 (40 min, 15 layouts); local search m = 1 3 min, m = 2 28 min,
  m = 3 4 min (screens only), m = 4 < 1 s; integrated 4 x ~11 min, 20:46-21:30. Total 7,998 s of 18,000 s.
* Reproducibility: `records.jsonl` (1,484 rows), `results.csv`, `pareto.csv`, `wall_time.json`; schedules of
  every ILP solve in `../cache/schedules/`.

## Anomalies

1. **Non-monotone result across budgets.** The m = 2..4 layout L02:SC:B4:C2 (V 654.525) is 0.148 USD worse
   than the m = 1 layout L02:SC:B3:C2 (654.377), which is affordable at every budget. Cause: the local search
   of each budget restarts from the frontier layout L01:SC:B3:C2 (`greedy_local_search`, step 3) instead of
   from the lower budget's result; from L01:SC:B4:C2 / L02:SC:B4:C2 the baseline screen (which values extra
   spares: B4 / B5 variants at 1008-1017 vs B3 at 1072-1078) never put L02:SC:B3:C2 in its top 5, and the pass
   limit of 3 was hit. Recommended fix for the next run: seed the candidate set of budget m with the results of
   all lower budgets (nested budgets make them feasible) and let the local search exhaust its passes.
2. **B = 4 is outside the size menu.** The LS `size +-1` move is bounded by `spec.valid_sizes` (K_j = 8,
   Cbar_j = 4), not by the menu `SC: B <= 3`; the chosen m >= 2 layout is therefore not in the grid used by
   the forward step or by E9.1. The integrated model admits it (bounds (7)-(8)), so the comparison stands.
3. **Integrated bound useless.** `-inf` at m = 1 (root LP not finished in 600 s) and -12,548.6 at m = 2..4
   (gap 20.2): 40 min of the wall budget bought no certification. The bound line of the auto-generated
   `pareto.png` (-12,549) is therefore meaningless; `pareto_final.png` omits it.
4. **Screen and ILP disagree on ranking.** The baseline screen's best singleton (L05) is 4th by the ILP and the
   ILP-best singleton (L02) is 6th in the screen; the screen also prefers more spares than the ILP. With
   `k_screen = 5` the search still found L02, but only via the swap move.
5. **Hubs and transfers dominated.** All 5 hub additions cost exactly F_hub + bC C (opex to 3 decimals
   unchanged), `transfers_used = 0` on all 17 priced two-site layouts although 14-16 transfer services existed:
   consistent with E3u (hub = +F_hub, transfers worth ~0 USD).
6. **Flat family.** Across the 8 one-site locations priced as SC:B3:C2 the V spread is 4.2 USD (0.6 %);
   unserved and response costs are layout-independent. The family is energy-stressed on the station side
   (the single site is out of full batteries 12-41 of 48 slots) but not on the fleet side.
7. E9.1 and E9.2 are not value-comparable (2 vs 3 seeds, `all_candidates` vs `open_sites` targets, menu B <= 2
   vs B <= 3), only layout-comparable (both choose L02:SC).

## Interpretation

The budget sweep gives the planner a clear and somewhat deflating answer: on the relaunch family one
co-located swap-and-charge site at L02 (NoMad) with two chargers and three or four spares is the best layout
the search can find at 52,150, 104,300, 156,450 and 208,600 USD alike, and the extra budget beyond the first
unit buys nothing. The reason is visible in the priced moves: every second site raises the allocated setup by
12-13 USD per window (29 USD for a charge-only hub) while the best operating saving any second site produces is
1.09 USD per window, because the orders that go unserved (5-6 of 36 per scenario, 160 USD) and the response
cost (462.5 USD) are the same whatever the layout; they are lost to fleet time, not to empty batteries. The
"stress" of the family shows up as the single site being out of full batteries for most of the window, yet
the coordinator copes by timing the six swaps (one per bike) around the charging cycle, so a second site only
shortens detours (C_travel -0.1 to -0.3) and purchased electricity (C_elec -0.2 to -0.4). Among single sites
the location matters at the 0.6 % level (L02 654.4, L01 655.1, L05 655.2, L07 655.7, L08 657.0, L11 658.5):
central restaurant cells near the depots beat the zone centres and the southern landmark, and a fourth spare
or third charger at L02 is idle (opex unchanged, setup up). Charge-only hubs are priced exactly at their setup
cost with unused transfer services, confirming the E3u finding under stress. The integrated model matched the
greedy's incumbent at every budget but could not bound it, so the claim "greedy = optimum" rests on the
exhaustive E9.1 check at small scale and on the exhaustive pricing of all single-location moves here, not on a
certified gap. Two search artefacts (the 0.15 USD non-monotonicity and the off-menu B = 4) do not change the
conclusion but should be fixed before the roles, deck and cross sub-experiments are read, since they inherit
the same local search. For the model itself, the result argues that siting on this family should be studied
with a tighter fleet-energy coupling (lower q0 or longer windows) if the second site is ever to be worth its
50,000 USD, or with the access row [U4] of E9.6, where the planner's objective and the operator's diverge.

## Figures (regenerated from `records.jsonl` and `../candidates.csv`, matplotlib Agg)

* `map_sites_final.png` -- the 12 candidates on a lat / lon km frame, depots, the chosen SC site at L02, the
  greedy's best singleton L01, with the ILP value of each priced single-site option and the V increase of each
  priced second-site option.
* `pareto_final.png` -- investment vs expected operating cost (left) and vs V (right) for all 29 priced
  layouts, chosen layouts per budget and the integrated incumbents, budget lines m = 1..4.
* `greedy_trajectory_final.png` -- V of every priced move by phase (singletons, forward additions by role,
  local search at m = 1 and m = 2..4), with the start and best-found lines.
* Auto-generated by the run and superseded for reading: `pareto.png` (includes the meaningless bound),
  `map_budget_{1..4}.png` (rotated grid frame).
