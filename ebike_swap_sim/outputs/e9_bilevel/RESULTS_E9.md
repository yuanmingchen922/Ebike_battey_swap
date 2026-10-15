# E9 -- bi-level siting of swap and charge stations in Midtown: consolidated results (2026-10-14)

Family `nyc4h_stress2` (6 bikes, 36 orders, one 4 h window of 48 slots, initial charge `q0 ~ U{3..6}` of 12
levels, site power `P_j = 2.8 kW`, 4 kW grid group, `usd_sunk` cost convention); 12 Midtown candidate
locations (`candidates.csv`: six busiest restaurant cells L01-L06, three landmarks L07-L09, three zone
centres L10-L12); roles S (swap-only), C (charge-only hub), SC (co-located); budget unit 52,150 USD
(= 50,000 site + 3 x 450 spares + 2 x 400 chargers). Authoritative numbers live in the six sub-reports
`validate/`, `sweep/`, `roles/`, `deck/`, `access/`, `cross/` (`RESULTS_final.md` and the figures in each
folder); this file consolidates them and names the source of every number. The first E9 launch on the
8-bike family `nyc4h_stress` (`_first_attempt/`) is superseded; section 5 item 8 records what went wrong.

Every ILP value in this file is an upper bound on the written E2 optimum (the lower level moves bikes only
into open-site / candidate and depot nodes, the E8 convention) and the R2.4 geometry caveat applies (real
restaurants, zone weights and candidate coordinates placed on a synthetic 150 m grid).

## 1. Summary

On the stressed Midtown family the planner's answer is one well-stocked co-located station, and nothing
else is worth its money. Every search method (exhaustive enumeration, integrated stochastic ILP, greedy +
local search, and all three role sets) opens a single swap-and-charge site at candidate L02 (W 29th-30th /
6th Ave, NoMad) with 3-4 spare batteries and 2 chargers, for an expected total cost of about 654 USD per
4 h window (13.2-13.5 USD of window-allocated setup plus 641 USD of operations) while serving 85 % of the
36 orders. A second site of any role never pays: its allocated setup is 11.9-12.2 USD per window (29.4 USD
for a charge-only hub, which is never used) against an operating saving of at most 1.1 USD, so the greedy
returns the same layout at budgets of 1, 2, 3 and 4 units and leaves up to 156,000 USD unspent. The
proposal's spin-and-adjust planner, which opens one site per budget unit, loses 0.1 / 1.9 / 3.9 / 5.9 %
at the four budgets, almost exactly the setup of the sites it opens for nothing. Forcing every demand zone
within 1.2-1.8 km of a swap site costs +12 USD per window per extra site and buys coverage, not service.
The location is robust to the operating policy (the myopic baseline policy also prefers L02, with L01 a
tie), the size is not (the baseline wants the fourth spare, worth 47 USD per window to it and 0.15 USD to
the coordinator). The structural reason behind all of this is that for the optimising coordinator the fleet
(6 bikes in 4 h), not the batteries, is what limits service: the served share is 0.852 for every layout
with at least three spares, so infrastructure beyond the first site moves only travel and electricity.

## 2. The question and the bi-level setup

The proposal asks where in Midtown swap / charge stations should go, which kind, and how big, for a
delivery fleet whose daily operations are run by the E2 coordinator. We model this as a bi-level problem
(design: `notes/bilevel_siting_design.md`, binding conventions: `notes/DECISIONS.md`, "E9 relaunch
decisions"). The upper level (planner) picks, among 12 candidates, which to open, with which role (S / C /
SC) and size (B spares, C chargers) under an investment budget of m x 52,150 USD; the lower level is the
unchanged E2 operations ILP with facilities fixed, solved once per demand scenario (a seed of the instance
generator), and the planner's value V of a layout is its window-allocated setup cost plus the expected
operating cost over the scenarios. Because planner and coordinator minimise the same cost, the bi-level
problem collapses to one two-stage stochastic ILP (algorithm A, the exact benchmark); it stays genuinely
bi-level when the planner adds rows the operator does not price (the access row [U4]) or evaluates layouts
under a different operating policy. Algorithms: (A) integrated stochastic ILP, (B) exhaustive enumeration
with a superset bound and scenario-by-scenario pruning, (C) greedy + local search with a cheap
baseline-policy screen and ILP pricing of the top-5 moves per role, (D) the proposal deck's spin-and-adjust
heuristic, (E) cross-evaluation under the ILP and the baseline policy. Gurobi 13, Threads 3, Seed 0,
TimeLimit 300 s per lower-level solve (600 s with hubs), 600 s for the integrated model.

| sub-experiment | what | size | coverage | headline |
|---|---|---|---|---|
| E9.1 `validate/` | exhaustive enumeration (B) vs integrated stochastic ILP (A) | 4 candidates (L01-L04), 2 seeds, m = 1, menu B <= 2, all-candidates reposition | 8 layouts, 6 solved on both seeds, 2 pruned; 14 lower-level solves (9 OPTIMAL, 5 TIME_LIMIT at 0.8-1.6 % gap); 44.7 min | both pick L02:SC:B2:C1 at V 676.22; integrated bound 668.04 (gap 1.21 %) |
| E9.2 `sweep/` | greedy + local search per budget, Pareto curve, integrated bound | 12 candidates, 3 seeds, m = 1..4, full menu | 29 layouts priced, 87 solves all OPTIMAL; 4 integrated runs at TIME_LIMIT; 133 min | one site at every budget: L02:SC:B3:C2 (654.38) / L02:SC:B4:C2 (654.53); budget beyond one unit unspent |
| E9.3 `roles/` | role sets {SC}, {S, SC}, {S, C, SC} | 12 candidates, 3 seeds, m = 2, 3 | 28 layouts, 84 solves all OPTIMAL; 87 min | identical optimum L02:SC:B4:C2 for all role sets; hubs +29.4 USD and unused, swap-only sites +12.4-13.0 USD |
| E9.4 `deck/` | proposal deck heuristic (D) vs bi-level (C) | 12 candidates, 3 seeds, m = 1..4 | 10 baseline iterations, 12 ILP solves all OPTIMAL; 9.5 min | regret 0.68 / 12.56 / 25.53 / 38.78 USD (0.10 / 1.92 / 3.90 / 5.93 %) |
| E9.5 `cross/` | 7 chosen layouts under ILP, baseline policy, relaxed-target ILP | 5 seeds (0-2 in-sample, 3-4 out-of-sample) | 105 evaluations; 66 of 70 ILP evaluations OPTIMAL, 4 TIME_LIMIT on L02:SC:B2:C1; 56 min | location robust to policy, size not; cross-regret 0.15 vs 47.4 USD; ILP beats policy by 31-41 % |
| E9.6 `access/` | planner-only access row [U4], D = 8 / 12 blocks | 12 candidates, 3 seeds, m = 2, 3, repair mode | 112 new solves (111 OPTIMAL); D = 8, m = 3 truncated by the wall budget; 140 min | access costs +12.08 USD per window (+1.85 %) per extra site; served share unchanged; 11 / 11 zones covered at D = 12 |

## 3. Consolidated findings

### 3.1 The chosen layout (`sweep/RESULTS_final.md`, `roles/RESULTS_final.md`)

One co-located site at L02 (busiest restaurant cell 2, 72 restaurants, lat 40.74745 / lon -73.98687), role
SC, 2 chargers, 3 spares at m = 1 (investment 52,150 USD, the whole budget unit) or 4 spares at m = 2..4
(52,600 USD). Expected total V = 654.38 (B = 3) / 654.53 (B = 4) USD per 4 h window = 13.19 / 13.52 USD of
allocated setup + 641.19 / 641.00 USD of operations. Served share 0.852 (30.67 of 36 orders), 1.67 late
orders (6 USD lateness), unserved penalty 160 USD (5.33 orders x 30 USD), response cost 462.5 USD, travel
11.9 USD, electricity 0.56-0.75 USD (1.7-2.4 kWh bought), no transfers. The site is out of full batteries
for 12-41 of 48 slots per scenario, yet the coordinator times its six swaps (one per bike) around the
charging cycle. The cross-evaluation on five seeds (`cross/RESULTS_final.md`) gives V 654.49 (B3) / 654.64
(B4) and confirms that `L01:SC:B3:C2` (654.65) is a statistical tie; among the eight single sites priced as
SC:B3:C2 the spread is 4.2 USD (0.6 %): L02 654.4, L01 655.1, L05 655.2, L07 655.7, L08 657.0, L11 658.5.
Location matters at the 0.6 % level; central restaurant cells near the depots beat zone centres and the
southern landmark.

### 3.2 Why a second site never pays (`sweep/RESULTS_final.md`, `roles/RESULTS_final.md`)

The forward step priced 15-16 second-site additions to the best singleton L01:SC:B3:C2 (V 655.06), and the
local search five more next to L02:SC:B4:C2. Every one raised V: swap-only and co-located additions by
+11.85 to +12.21 USD per window, charge-only hubs (C = 2 at L02-L06) by +29.35 USD. The allocated setup of a
second site is 12.0-13.2 USD (S / SC) or 29.19 + 0.16 USD (hub), and the best operating saving any second
site produced was 1.09 USD per window (0.17 %, `L01:SC:B3:C2 + L10:SC:B3:C2`, opex 640.78). Hubs were
priced five times and gave byte-identical operating cost to the parent: `transfers_used = 0` in all 84
lower-level solves of the roles run although 14-16 shuttle services existed, so a hub costs exactly its
setup. Swap-only sites are dead stock: with no transfers they contribute only their 1-3 initial spares,
worth 0.18-1.02 USD. The 5-6 orders dropped per scenario are lost to fleet time and initial charge, not to
missing batteries: unserved (160 USD) and response (462.5 USD) are identical for every layout with B >= 3.

### 3.3 Budget sweep (`sweep/RESULTS_final.md`, figures `pareto_final.png`, `map_sites_final.png`, `greedy_trajectory_final.png`)

| m | budget USD | layout | investment used | unspent | V | served share |
|---|---|---|---|---|---|---|
| 1 | 52,150 | L02:SC:B3:C2 | 52,150 (100 %) | 0 | 654.377 | 0.852 |
| 2 | 104,300 | L02:SC:B4:C2 | 52,600 (50 %) | 51,700 | 654.525 | 0.852 |
| 3 | 156,450 | L02:SC:B4:C2 | 52,600 (34 %) | 103,850 | 654.525 | 0.852 |
| 4 | 208,600 | L02:SC:B4:C2 | 52,600 (25 %) | 156,000 | 654.525 | 0.852 |

The Pareto "curve" of investment vs expected operating cost is a single point plus the 450 USD fourth
spare: doubling the investment from 52 k to 104 k USD buys at most 1.09 USD per window of operating cost. A
third charger or fifth spare at L02 is idle (opex unchanged, setup +0.08 / +0.33 USD). The integrated
stochastic ILP (5.35 M variables) accepted the greedy's layout as its incumbent at all four budgets but
produced no usable bound in 600 s.

### 3.4 Role separation (`roles/RESULTS_final.md`, figures `roles_priced_moves.png`, `roles_components.png`)

All three role sets ({SC}, {S, SC}, {S, C, SC}) at both budgets (m = 2, 3) converge to the identical
layout L02:SC:B4:C2, V 654.525, served 0.852, zero transfers. Forcing co-location costs 0.00 USD and
allowing hubs gains 0.00 USD. The E3u finding "hub = +F_hub, transfers worth 0-9 USD" is reproduced in its
extreme form (transfers worth exactly 0). The hub cost sensitivity (F_hub = 12.03 instead of 29.19) was not
run but is not needed: a hub with unchanged operating cost enters only at negative setup.

### 3.5 Deck heuristic regret (`deck/RESULTS_final.md`, figures `deck_vs_bilevel_final.png`, `map_deck_vs_bilevel.png`)

The proposal deck's planner (open the k = m sites with the most swaps under the baseline policy, size by
swap demand, 3 iterations, no ILP during the search) spends the whole budget by construction.

| m | deck layout | deck V | bi-level V | regret USD | regret % | extra setup of the deck |
|---|---|---|---|---|---|---|
| 1 | L01:SC:B3:C2 | 655.06 | 654.38 | 0.68 | 0.10 | 0.00 |
| 2 | L01:SC:B3:C1 + L02:SC:B4:C1 | 667.08 | 654.53 | 12.56 | 1.92 | 13.03 |
| 3 | L01:SC:B4:C1 + L02:SC:B4:C1 + L04:SC:B3:C1 | 680.06 | 654.53 | 25.53 | 3.90 | 26.47 |
| 4 | L01:SC:B4:C1 + L02:SC:B5:C1 + L04:SC:B3:C1 + L06:SC:B3:C1 | 693.31 | 654.53 | 38.78 | 5.93 | 39.91 |

At m = 1 the two planners agree on role and size and differ only between two adjacent cells (L01 vs L02,
a tie on a demand proxy of 1.67 swaps each). From m = 2 the regret is the setup of the extra sites minus
0.5-1.1 USD of operating saving; served share, lateness and unserved penalty are identical. Priced by the
baseline policy, the same deck layouts cost 1025-1072 USD (34-39 % more than under the ILP) and the policy
ranks the two-site layout best, so a planner evaluating designs with the myopic policy over-builds.

### 3.6 Access constraint (`access/RESULTS_final.md`, figures `access_map.png`, `access_coverage.png`, `access.png`)

With the access row [U4] (every NTA demand zone within D blocks of an open swap-capable site, repair mode)
the planner must open a second site, L05:SC:B1:C1 (Rockefeller south), at both radii.

| m | variant | layout | investment | V | delta V vs no access | served share | zones covered of 11 | mean / max blocks to site |
|---|---|---|---|---|---|---|---|---|
| 2, 3 | no access | L02:SC:B4:C2 | 52,600 | 654.525 | - | 0.852 | 5 (D 8) / 8 (D 12) | 11.65 / 22 |
| 2 | D = 8 | L02:SC:B4:C1 + L05:SC:B1:C1 | 103,050 | 666.605 | +12.08 (+1.85 %) | 0.852 | 8 | 8.52 / 15 |
| 3 | D = 8 | L02:SC:B4:C2 + L05:SC:B1:C1 + L08:S:B1:C0 | 153,900 | 678.906 | +24.38 (+3.73 %) | 0.852 | 9 | 7.41 / 15 |
| 2, 3 | D = 12 | L02:SC:B4:C1 + L05:SC:B1:C1 | 103,050 | 666.605 | +12.08 (+1.85 %) | 0.852 | 11 | 8.52 / 15 |

The cost of access is the allocated fixed cost of each extra site (12.36-12.44 USD per window), of which
0.28-0.43 USD comes back as shorter rider detours; the served share does not move. At D = 12 (1.8 km) two
sites cover all 11 zones and the third budget unit stays unspent. At D = 8 (1.2 km) zone MN0801 is beyond
8 blocks of every candidate, MN0202 and MN0701 each have a single candidate in reach (L08, L06), and the
three-site search at m = 3 was cut by the wall budget with MN0701 still uncovered. The candidates that
enter only because of the access row are L05 (always) and L08 (D = 8, m = 3); no zone-centre candidate
(L10-L12) is ever chosen.

### 3.7 Cross-evaluation (`cross/RESULTS_final.md`, figure `cross_eval_final.png`)

Seven chosen layouts re-priced on five seeds under the ILP, the baseline policy and the relaxed-target ILP.

| layout | chosen by | V ILP | V baseline | regret ILP | regret baseline | ILP-vs-policy gap |
|---|---|---|---|---|---|---|
| L02:SC:B3:C2 | greedy + LS m = 1 | 654.49 | 1026.24 | 0.00 | 47.37 | 36.2 % |
| L01:SC:B3:C2 | deck m = 1 | 654.65 | 1022.26 | 0.16 | 43.39 | 36.0 % |
| L02:SC:B4:C2 | greedy + LS m = 2, 3; all role sets | 654.64 | 978.87 | 0.15 | 0.00 | 33.1 % |
| L01 + L02 (deck m = 2) | deck | 666.91 | 991.36 | 12.42 | 12.49 | 32.7 % |
| L01 + L02 + L04 (deck m = 3) | deck | 679.85 | 986.31 | 25.36 | 7.44 | 31.1 % |
| L01 + L02 + L04 + L06 (deck m = 4) | deck | 693.10 | 1006.16 | 38.61 | 27.29 | 31.1 % |
| L02:SC:B2:C1 | validate (restricted menu) | 662.79 | 1129.47 | 8.30 | 150.61 | 41.3 % |

Location is robust: every method and both policies put the single site at L02, with L01 a tie (+0.16 USD
for the ILP, 4 USD better for the policy). Size is not: the coordinator is indifferent between 3 and 4
spares (0.15 USD) while the myopic policy values the fourth spare at 47.4 USD per window (4.8 %) because it
runs the site dry; both agree two spares are too few (+8.3 / +150.6 USD). The cross-regret is asymmetric:
taking the policy's best layout costs the coordinator 0.15 USD, taking the coordinator's best costs the
policy 47.4 USD. The ILP beats the baseline policy by 31.1-41.3 % of the policy's cost on every layout
(306-467 USD per shift), 53-60 % of it lateness (15-18 late orders vs 1.4-1.8). In-sample (seeds 0-2) vs
out-of-sample (seeds 3-4) ILP operating cost differs by -0.3 to +4.2 USD, so the three-seed search did not
over-fit; the baseline policy swings by 74-128 USD between the subsets (seed heterogeneity). The relaxed
end-of-horizon targets are worth 0.02-0.42 USD per window on layouts with B >= 3 and 1.38 USD at B = 2.

### 3.8 Validation (`validate/RESULTS_final.md`, figures `layouts_m1.png`, `map_validate_m1.png`, `solve_times_m1.png`)

On the restricted protocol (4 candidates, 2 seeds, m = 1, menu B in {1, 2}, all-candidates reposition) the
exhaustive enumeration of the 8 admissible single-site layouts and the integrated stochastic ILP (1.50 M
variables) choose the same layout, L02:SC:B2:C1, at the same value V = 676.223 USD (agreement to 3e-13).
The integrated model stopped at 600 s with bound 668.04 (gap 1.21 %, one node explored, no improvement on
its MIP start); the per-layout Gurobi bounds place the optimum over the eight layouts in [671.13, 676.22].
The one-spare vs two-spare separation (>= 48 USD, served 0.68 vs 0.79-0.82) is certified; the ranking among
L01 / L02 / L03 with two spares (676.2 / 679.6 / 680.9) lies inside the solver gaps and is not.

## 4. Solver facts

* Lower-level E2 ILP (6 bikes, 0.5-0.8 M arcs with `open_sites` targets): OPTIMAL in 11-150 s on the
  search sub-experiments (sweep mean 29 s, max 75 s; roles mean 28 s, max 66 s; cross 11-148 s, growing
  with the number of open sites; access mean 35 s, max 185 s). Two-spare layouts are the slow ones: in the
  validation (all-candidates libraries, 0.6-0.8 M arcs) 5 of 14 solves hit the 300 s limit at 0.8-1.6 %
  gap, all on B = 2 layouts; in the cross run the 4 TIME_LIMIT solves are all on L02:SC:B2:C1. The 8-bike
  first-attempt family needed 2.2-2.4 M arcs and routinely hit 300 s.
* Integrated stochastic ILP: 1.50 M variables on the validation protocol (bound 668.04, gap 1.21 % in
  600 s); 5.35 M variables (4.96 M binaries, 465 k rows) on 12 candidates x 3 scenarios, where it returned
  only its warm start and no usable bound in 600 s (`-inf` at m = 1 because the root LP did not finish,
  -12,549 at m = 2..4). At this size it is an incumbent checker, not a certifier; the enumeration or the
  heuristic is the actual optimiser.
* Coverage: validate 8 layouts (6 solved, 2 pruned by the superset bound, none skipped); sweep 29 layouts /
  87 solves, roles 28 / 84, deck 12 solves, cross 105 evaluations (52 fresh ILP solves), access 112 new
  solves: all OPTIMAL except the TIME_LIMIT rows listed above and one partial solve in the truncated access
  row; no ERROR, no infeasible layout, no LOW_SERVICE row. Wall time: validate 44.7 min, sweep 133.3 min,
  roles 87.1 min, deck 9.5 min, cross 55.8 min, access 140.4 min (about 7.9 h in total, three processes in
  parallel); shared lower-level cache `cache/` (version `e9-2`, 2,329 schedule files). Baseline-policy
  screening runs take milliseconds; 1,449 (sweep), 1,446 (roles) and 2,088 (access) of them were used.
* Search coverage limits: no three-site layout was ever priced by the greedy (no two-site layout beat the
  singleton), hubs with C = 4 and hubs at L07-L12 were never priced, and only the top-5 moves per role by
  the baseline screen reach the ILP (the screen ranks sizes the wrong way round: it prefers more spares and
  put the eventual best singleton L02 6th).

## 5. Issues and limitations

1. **The coordinator's service does not depend on the layout.** Under the ILP the served share is 0.852
   (0.856 on five seeds), lateness 1.7-1.8 orders and the unserved penalty 160 USD for every layout with at
   least three spares, from one site to four. For the coordinator the fleet (6 bikes, 4 h, q0 3-6 levels)
   binds, not the batteries, so siting and sizing move only travel (11.8-12.4 USD) and electricity (0-0.8
   USD). The family makes station siting bind for the myopic policy but still not for the coordinator; the
   upper level therefore carries little information beyond "one site, B >= 3". (`cross`, `sweep`)
2. **Size-menu escape (B = 4).** The forward step and E9.1 use the menu SC: B <= 3, but the local search's
   size +-1 move is bounded only by K_j = 8 / Cbar_j = 4, so the m >= 2 answer L02:SC:B4:C2 lies outside
   the menu and costs 450 USD more than the m = 1 budget. The integrated model admits it, so the comparison
   stands, but an enumeration restricted to the menu cannot return it. (`sweep`, `roles`)
3. **Non-monotone values across budgets (0.15 USD).** The m = 2..4 layout (654.525) is 0.148 USD worse than
   the m = 1 layout (654.377), which is feasible at every budget; the local search of each budget restarts
   from the forward frontier, not from the lower budget's result, and the 3-pass limit was hit. Immaterial
   at the 12-39 USD scale of the conclusions; fix by seeding budget m with the results of all lower budgets.
   (`sweep`)
4. **Access run truncated at D = 8, m = 3.** The wall budget (120 min) expired inside the second repair
   round; the reported three-site layout (L02 + L05 + L08, +24.4 USD) is the first usable covering layout,
   the L06 option for zone MN0701 and the covering polish were never priced. Also, the 11-zone requirement
   is infeasible at D = 8 for every layout (MN0801 has no candidate within 8 blocks), and the integrated
   model with hard [U4] rows was not run, so there is no exact benchmark of the access cost. (`access`)
5. **The validation layout is not the full-problem optimum.** L02:SC:B2:C1 is the certified answer of the
   restricted protocol (4 candidates, 2 seeds, B <= 2, all-candidates libraries); on the full menu and five
   seeds it is the worst of the seven chosen layouts (+8.3 USD under the ILP, +150.6 USD under the policy)
   because one more order per shift goes unserved. E9.1 validates the machinery, not the number. (`cross`,
   `validate`)
6. **The integrated bound is useless at full size.** 5.35 M variables, root LP unfinished in 600 s; the
   search results are heuristic incumbents without a certified gap, and the optimality claim rests on the
   small-scale E9.1 agreement and on the exhaustive pricing of every single-site move. The auto-generated
   `sweep/pareto.png` draws the meaningless -12,549 bound; `pareto_final.png` omits it. (`sweep`)
7. **Synthetic grid and few scenarios.** Real restaurants, zone weights and candidate coordinates sit on a
   synthetic rotated 150 m grid (R2.4 caveat); the search uses 3 demand scenarios and the hold-out check 2
   more. The ILP side passes the in/out-of-sample check (<= 4.2 USD), but policy-side rankings closer than
   about 30 USD are not resolved with five seeds. Every ILP value is an upper bound on the written E2
   optimum (reposition targets restricted to open sites and depots).
8. **The first attempt was degenerate (superseded, `_first_attempt/README.md`, DECISIONS "E9 relaunch
   decisions").** On the 8-bike family `nyc4h_stress`: (i) the roles run reported "no feasible layout"
   because wall-budget exhaustion (`SKIPPED_BUDGET`) was mapped to an infinite value; (ii) the access run
   reported "no feasible layout" because [U4] was enforced on every intermediate layout, including the
   singletons that can never cover all zones; (iii) the sweep chose a swap-only site with one spare that
   served 7 % of the orders, because the baseline-policy screen (which serves orders at a loss where the
   ILP drops them) let only S:B1 singletons through and no served-share guard existed; (iv) lower-level
   solves of 2.2-2.4 M arcs hit 300 s. Fixes: the lighter family `nyc4h_stress2` (6 bikes, q0 3-6, 2.8 kW
   sites), swap-only sites admissible only next to a charge-capable object, the start = best singleton by
   lower-level V with a per-role screen and a 50 % served-share guard, wall exhaustion reported as
   `wall budget exhausted` and never as infeasibility, the access row as repair-and-report, and per-layout
   `open_sites` libraries for the search. Lesson: a cheap screening policy that values facilities
   differently from the ILP can silently steer the search, and every failure mode of the evaluator must
   be surfaced as a status, never folded into the objective.
9. Minor: the baseline screen and the ILP disagree on ranking (the screen's best singleton L05 is 4th by
   the ILP); `SC:B1:C0` is priced separately from the identical `S:B1:C0` (6 wasted solves); local-search
   histories are kept only in memory and were reconstructed from the logs; E9.1 and E9.2 values are not
   comparable (2 vs 3 seeds, different libraries and menus), only their layouts are.

## 6. What this answers, and what next

For the proposal's "station location" question the answer on this family is unambiguous and smaller than
the question: with six riders and 36 orders in a 4 h window, one co-located swap-and-charge station at a
busy central restaurant cell (L02, or equivalently L01 one cell away), stocked with three spares and two
chargers, is the whole infrastructure; charge-only hubs, swap-only satellites and second sites of any kind
are never worth their fixed cost, and the deck's rule of one station per budget unit over-builds by its
sunk cost. The location is insensitive to who runs the fleet; the size should be chosen for the operator
that actually will (one more spare, 450 USD, if it is the myopic policy). Spatial-equity requirements
(every zone within 1.2-1.8 km of a swap point) are a planner's purchase at about 12 USD per window per
extra site and do not change service. What the study does not yet answer is where stations should go when
the station side binds for the coordinator, because on this family it does not.

Next steps, in order of value: (1) a deeper energy-stressed family in which the second site changes who
gets served (more bikes per site, lower q0, a longer window, or fewer spares per site, since B = 2 is the
only size at which the ILP reacts); (2) more candidates across Manhattan (the Midtown box is 2 x 3.5 km, so
every candidate is within one detour of every order); (3) a rolling-horizon or multi-day lower level, where
charging turnover and end-of-day stock give chargers and hubs a role; (4) policy-aware siting, i.e. the
upper level evaluated under the policy that will run the fleet (algorithm E as the follower) and the
integrated model with hard [U4] rows at D = 12, m = 2 warm-started from L02 + L05 as the exact access
benchmark; (5) the cheap fixes of section 5 (nested budgets in the local search, canonical S / SC keys,
pricing L02 + L05 + L06 and L02 + L06 + L08 directly to settle the D = 8 question in six solves).

## Figures best suited for the brief

* `sweep/map_sites_final.png` -- the 12 candidates, the chosen site L02 and the V of every priced single site and second-site addition.
* `sweep/pareto_final.png` -- investment vs expected operating cost and vs V for all 29 priced layouts: a flat frontier, the second site's setup never repaid.
* `cross/cross_eval_final.png` -- heat maps of V, regret, served share and lateness for the seven chosen layouts under the ILP and the baseline policy.
* Also useful: `deck/deck_vs_bilevel_final.png` (deck regret per budget), `access/access_map.png` (access layouts and reach).
