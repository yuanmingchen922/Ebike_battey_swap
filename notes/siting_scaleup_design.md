# Siting scale-up design: 40-60 DOT candidates, >= 10 demand scenarios, certified bounds on AWS (2026-10-20)

Audience: implementer (all sections) and author (sections 0, 3, 6). Code paths are relative to `ebike_swap_sim/`;
equation numbers refer to `notes/extracted/E2.txt`. **No equation of E2 (1)-(33) changes.** The lower level stays
the unchanged operations model (aggregated E2 ILP, O1); the LP relaxation is used for bounds only; every incumbent
is priced by the operations ILP. Conventions of `notes/DECISIONS.md` (O2 conventions, O2 second pass) stay in force
unless a section below says otherwise. Everything that solves runs on the EC2 instance (memory
`feedback-run-on-cloud`); this note was written without running any solver.

Sources read for this design: `ebike_swap_sim/bilevel.py`, `benders.py`, `sites_nyc.py`, `data_nyc.py`, `arcs.py`,
`experiments/r6_o2_siting.py`, `notes/o2_siting_bound_design.md`, `notes/o2_manhattan_first_pass.md`,
`notes/bilevel_siting_design.md`, `outputs/r6_o2/RESULTS_final.md`, `outputs/r6_o2/manhattan_pass2/{RESULTS.md,
records.jsonl, cache/index.jsonl}`, `outputs/r5_x6_manhattan/{RESULTS_final.md, cache/index.jsonl}`,
`outputs/e9_bilevel/RESULTS_E9.md`, `outputs/R6_FILL_DIGEST.md` parts 2-3, `deploy/aws/`.

---

## 0. Decisions in one page

| item | decision | why (evidence) |
|---|---|---|
| Candidate set | `manhattan_dot` family: DOT-based sites (40-60, from `data/raw/dot_candidate_sites.csv`) **plus** the 15 lattice candidates of `r5_manhattan`, merged within 80 m; the DOT-only problem is the same master with the lattice sites fixed closed (section 2.6) | one template serves both runs; cuts and cache are shared; the 15-candidate study is reproduced as a special case |
| Reposition convention | moves into a candidate node only from nodes within the eBaaS coverage radius (2 km = 14 blocks); moves into the six depots unrestricted; `reposition='all_candidates'` otherwise unchanged | swap arcs start at the facility node (`arcs._template_specs`), so every candidate must be a move target; one target costs about 0.2 M per-bike arcs (8 bikes), a 60-target template would be 3x today's and every pricing ILP 3x. With the radius the template grows by about 1.45x and pricing ILPs stay at today's size (section 1.4) |
| Role menu | reduced: SC with B in {2, 3, 4} x C in {1, 2}; S with B in {2, 3} (only next to a charge-capable object, as today); charge-only hub with C in {2, 4} at **hub-capable sites only** (DOT types `depot`, `lot`, `citibike_charging`; if fewer than 4 qualify, the 8 largest lattice cells are added; at most 12); transfer services only for pairs within `max_pair_km = 2.0` | B = 1 and hub C options never won at 15 candidates; hubs were never chosen (E9, O2); services scale with the product of charge- and swap-object counts (section 1.3). The hub candidate set is a stated input of the "where do charging stations go" answer (section 7, item 9) |
| Scenarios | 12 in-sample scenarios, 6 strata (3 demand levels x weekday/weekend) x 2 seeds, stratum-weighted `p_s`; 12 held-out scenarios of the same design for out-of-sample evaluation; the subset LPs of the m >= 2 branch-and-bound use `S_LP = 6` (one seed per stratum) with the other six scenarios at their superset values (valid, section 2.7); pricing and the m = 1 enumeration use all 12; cost table also at S = 10 and 15 | the task asks for >= 10 and for an SAA statement; stratification keeps the sample-average approximation meaningful at small S; the 6-of-12 rule halves the dominant LP cost (section 3) |
| Fleet | 8 bikes / 40 orders per base scenario (unchanged); demand levels scale orders (32 / 40 / 48); fleet of 12 bikes only as a sensitivity on 3 layouts | pricing tractability: 10-bike ILPs hit 600 s with 3.7-13 % gaps (`R6_FILL_DIGEST` 4.3); candidate count does not change the demand side |
| Budgets | m = 1-3 headline (unit 52,150 USD); m = 4 optional (greedy + LS, stage F) and only if the budget allows; one extra comparison row at m = 5 for the all-pilot DOT layout | a third rule site never paid at 8 bikes; m = 4 has 400 M layouts at 60 candidates and its bound is the trivial one (section 2.4) |
| Targets | relaxed (headline, certificates); written on 8 layouts as a sensitivity | the regional bounds of section 2.3 need monotonicity in the open set, which holds for relaxed targets only |
| Certificates | m = 1: pruned enumeration (certified expected); m = 2: **regional superset bounds with free sizes in a hierarchical branch-and-bound over candidate subsets** (new, section 2.3), then Benders integer phase with S1 rows; m = 3: the same branch-and-bound stopped at level 2 (bound and incumbent, a certificate only if a third site is provably useless); m = 4: trivial bound only | at 15 candidates single-layout cuts resolved essentially one layout each; the m >= 2 gap stayed at the trivial bound. The m = 2 certificate is expected but not assured (section 7, item 6) |
| Machine | r7i.8xlarge Spot (32 vCPU / 256 GB, about 0.8 USD/h); LP stages 12 workers x 2 threads (all 12 scenario LPs of a layout at once), ILP stages 8 workers x 3 threads on a global (layout, scenario) cell pool; resumable lanes; the on-demand 4xlarge is **stopped** while the Spot instance runs | section 3 (corrected): N = 60, S = 12, core stages about 30 h = 24 USD; with the optional stages about 35 h = 28 USD; 33 USD with the EBS volume and a 20 % contingency |

---

## 1. Instance

### 1.1 Candidate placement from the DOT CSV

Input `data/raw/dot_candidate_sites.csv` (built by the parallel task). Required columns: `id`, `name`, `lat`, `lon`,
`type` (one of `pilot`, `application`, `approved`, `citibike_charging`, `depot`, `lot`, `other`), optional `source`,
`address`, `capacity_hint`. Unknown columns are carried into `Candidate.label`.

Procedure (`sites_nyc.dot_candidates(path, region='manhattan_s110', merge_m=80.0)`, deterministic):

1. Keep rows inside `data_nyc.MANHATTAN_BOX` **and** the region band (`StudyRegion.in_band`); rows outside (for example
   pilot sites in Brooklyn or north of 110th St) are written to `candidates_dropped.csv` with the reason.
2. Snap with `StudyBox.snap(lat, lon)` to the 150 m rotated grid (R2.4 convention). Record `snap_m` = distance between
   the raw point and the node (about one block of uncertainty, as for the depots).
3. Merge: two rows whose raw points are closer than 80 m, or whose snapped nodes coincide, become one candidate; the
   survivor is chosen by type priority `pilot > approved > application > citibike_charging > depot > lot > other`,
   then by the larger `n_restaurants` at the node; merged names go to `merged_labels`. (At 150 m resolution two
   rows 80-150 m apart can still snap to the same node; that is the second merge rule.)
4. Union with `lattice_candidates()` (the 15 cells of `r5_manhattan`, source `lattice`), merged by the same rule
   with priority below every DOT type; `Candidate.source` keeps `dot:<type>` or `lattice`.
5. Ids `D01..Dnn` in the order south -> north, west -> east (like the lattice ids), so that the map labels are
   readable; `rank` keeps the input order; the lattice candidates keep a `lattice_id` field (`M01..M15`) for the
   reproduction test (section 5.1).
6. Attach `n_restaurants` (DOHMH rows at the node) and `hub_capable` (type in `{depot, lot}`, or the 8 largest
   lattice cells when fewer than 4 DOT rows qualify).
7. Cap: if the union exceeds 60, drop `other` rows with the fewest restaurants within 4 blocks, then `lot`; record
   what was dropped. Report N_DOT, N_lattice-only, N_merged, N in `candidates.csv` and the plan record.

Every candidate is a grid node of the instance (`site_latlon` = all candidate coordinates in `make_base_instance`),
so the route library contains every candidate as before.

### 1.2 Roles and size menu

`SIZE_MENUS['manhattan_dot']`:

| role | options | count |
|---|---|---|
| SC | B in {2, 3, 4} x C in {1, 2} | 6 |
| S | B in {2, 3} (admissible only next to an open C or SC object, `layout_admissible(s_needs_charge=True)`) | 2 |
| C (hub) | C in {2, 4}, only at `hub_capable` locations (master fixes the hub binaries of the others to 0) | 2 |

Master binaries: N x (6 + 2) + N_hub x 2 = 480 + 16 at N = 60 (210 today). The full `r5_manhattan` menu (14 options)
stays available by flag (`--menu full`) for the reproduction run and for a sub-result on the DOT instance
("the reduced menu loses at most x USD": the best full-menu one-site layout is priced once).

Why the reduction is safe to report: at 15 candidates no best layout used B = 1 or a hub; sizes above B = 4 are
outside today's menu as well; the certified m = 1 optimum (`M09:SC:B3:C2`) and both m = 2 incumbents
(`M04:SC:B2:C2|M09:SC:B4:C2`, `M04:SC:B4:C2|M09:SC:B4:C2`) are inside the reduced menu.

Admissible layout counts (reduced menu, N = 60; N = 40 in brackets): m = 1: 360 [240]; m = 2: about 106 k [47 k];
m = 3: about 8 M [2.3 M]; m = 4: about 400 M. Only m = 1 is enumerable; m = 2 and 3 need the regional bounds.

### 1.3 Transfer services

Services exist between every open charge-capable object and every open swap-capable object at a different location
(both directions, 8 departures). With hubs at every one of 60 locations that is about 14,000 ordered pairs and 2.8 M
`z` columns per scenario LP (0.25 M today). Decision: `SitingSpec.max_pair_km = 2.0` (already a field, recorded in the
cache key) and hubs only at hub-capable sites. Expected at N = 60 (density 1.4 sites per km2 in the 12 x 3.5 km band,
about 10-12 neighbours within 2 km per site): 60 SC + <= 12 C charge-capable objects x about 11 neighbouring
locations x 2 swap objects x 2 directions = about 3,000-3,200 ordered pairs, 8 departures each, i.e. about 0.45-0.5 M
`z` columns per scenario LP (**about twice today's**, not "at or below"; the sanity threshold of section 5.2 is
0.6 M). Hubs at every candidate would give about 0.9 M and are not allowed. The all-candidates template keeps the
services of every candidate pair within 2 km (the Benders template must contain every arc and service of every layout);
a hub object exists in the template only at hub-capable locations, so **no hub can be priced or screened elsewhere**
(this fixes the stage J screen, section 2.6).

### 1.4 Template library size, LP size, memory

Measured at 15 candidates (`manhattan_pass2` records): template 5.84-6.13 M per-bike arcs per scenario (8 bikes), built in
10-12 s; aggregated scenario LP 1.09-1.12 M columns, 179 k rows, 3.6 M nonzeros; superset per-bike LP 194-257 s per
scenario; cold barrier + crossover 13-17 s (one open site) / 26 s (2-4 open sites) at 3 threads; pricing ILPs under the
all-candidates convention 3.9-5.2 M arcs, 111-144 k binaries, mean 563 s (one site, with escalations) / 234 s (two) /
145 s (three or four), cap 300 s. From the open-sites cache (`r5_x6_manhattan`): 1.45 / 1.74 / 2.07 / 2.32 M arcs at
1 / 2 / 3 / 4 open sites, i.e. about 0.29 M arcs per extra open site (one target + one swap object).

Fit (per scenario, 8 bikes): arcs ~ 0.205 M per reposition target + 0.03 M per open swap object (terminal arcs (9)
from every node, `gbar`-limited) + a small order-dependent part. The 21 targets (15 candidates + 6 depots) explain
4.3 M of the 5.9 M.

Scaling to N candidates with every candidate a full target: N = 40: 11.7 M; N = 60: 17.8 M per scenario, LP columns
2.2 / 3.3 M, and every pricing ILP 2-3x today's, which already hits 300 s on one- and two-site layouts. **Not
feasible within the budget.**

With the approach radius (moves into a candidate only from nodes within 14 blocks; the band south of 110th St is
about 12 x 3.5 km, so a 2 km disc covers roughly 30 % of the nodes): per-candidate target cost about 0.06 M.

| quantity | 15 cand. (measured) | N = 40, radius | N = 60, radius |
|---|---|---|---|
| template arcs per scenario (8 bikes) | 5.9 M | about 6.1 M | about 8.4 M |
| LP columns per scenario (incl. `z`, section 1.3) | 1.1 M | 1.3-1.5 M | 1.8-2.2 M |
| cold barrier per LP, 3 threads, fixed layout (1 / 2-4 open sites) | 15 / 26 s (laptop) | x1.6 | x2.1 |
| cold barrier per **subset** LP (12-36 open objects, free sizes) | not measured (the all-open aggregated LP was never solved; the all-open per-bike LP took 194-257 s) | table uses 2 x the 2-4-site time | same rule |
| pricing ILP arcs, one open site | 4.35 M | about 4.0 M | about 4.9 M |
| pricing ILP time (per scenario, 3 threads, laptop) | 290 / 244 / 150 s at 1 / 2 / 3-4 sites (cache rows) | same | same to x1.1 |
| memory per persistent scenario LP | 1-2 GB | 1.5-2.5 GB | 2.5-3.5 GB |
| 12 LPs + 2 templates (about 2.5 GB each at 8.4 M `Arc` objects) + 8 pricing workers (library + model, 5-7 GB each) | 5 GB peak measured for 3 templates | about 60 GB | about 90 GB |

Both machines hold it (128 / 256 GB), but on the 4xlarge the 8 pricing workers must be 4 (the thread budget is 12
anyway). S = 15 adds about 10 GB. `keep_libraries = 2` stays; the per-bike template is released after the aggregated
LP is built (the LP keeps the aggregated matrix only). A `size` dry run (section 5.3) measures RSS and, **new**, the
cold-barrier time of (i) a one-site LP, (ii) a two-site LP, (iii) the all-open free-size LP of one lattice cell and
(iv) of the whole candidate set, before the first production lane; the lane plan is regenerated from these four
numbers (section 3.3). Abort threshold 100 GB on the 4xlarge, 200 GB on the 8xlarge.

Laptop-to-server factor: the pass-2 unit times were measured on the laptop (12 cores, `lp_workers 3 x 3 threads +
master 2 = 11 of 12`); no comparable solve exists on the r7i, so the factor is unknown. The cost table uses **x1.3**
(not x1.1): x86 Sapphire Rapids per-thread speed is at best equal to the laptop's, and eight concurrent barrier
solves share the memory bandwidth. The dry run replaces it by the measured ratio.

The radius is a restriction of the follower's move arcs, i.e. a stronger form of the standing PRUNING_NYC caveat
(every ILP value is an upper bound on the unrestricted optimum; the certificate is a statement about V* under the
library convention). Its effect is measured on the 15-candidate family (section 5.1, step 3).

### 1.5 Access radius, coverage rows, depots

* Access row [U4] at `D = 14` blocks (`access_radius_blocks()`): not in the headline (as today); sensitivity at m = 3
  (`--access-D 14`), zones with an empty candidate set reported and skipped (`access_sets`).
* A-priori terminal cover rows (`benders.cover_sets`): unchanged; with 60 candidates the cover sets are large and the
  rows bind rarely, which is fine (they cost nothing).
* Depots: the six bridge / tunnel entry points (`data_nyc.MANHATTAN_ENTRY_POINTS`), unchanged; `include_north` stays
  off (riders from Harlem would enter at 110th St; the region ends there; noted as a limitation).

### 1.6 Fleet

8 bikes, 40 orders at the base demand level, 4-h dinner window, eBaaS energy calibration, unchanged
(`R5_MANHATTAN_PARAMS`). Justification: the candidate count changes the planner's choice set, not the demand; the
instance is one platform's local fleet slice (ex-ante 7.8 km per bike-hour against the eBaaS 8.57), and pricing
tractability is the binding constraint of the certificate (K10 solves: 0 OPTIMAL at 600 s). More bikes would make a
third site pay (the LP value of a spare rises 0.70 -> 9.81 -> 77.95 USD at 6 / 8 / 10 bikes), so the number of sites
that pays is reported as a function of the fleet in a **sensitivity** (12 bikes / 60 orders, three layouts, 600 s
ILPs with gaps reported; stage K of section 3), not inside the certified study.

### 1.7 Demand scenarios

Generator knobs that exist: `orders_per_bike_hour` (n_orders), `demand_spec['profile']` (`R5_TIME_PROFILE`; the
generator also has weekday / weekend profiles and `weekend_factor` 1.15), `init_frac`, the seed. New scenario
generator `sites_nyc.scenario_design(S, held_out=False)`:

| stratum | day type | orders per bike-hour (orders) | weight |
|---|---|---|---|
| 1-3 | weekday profile | 1.00 (32) / 1.25 (40) / 1.50 (48) | 5/7 x 1/3 each |
| 4-6 | weekend profile (x1.15 volume shape) | 1.00 / 1.25 / 1.50 | 2/7 x 1/3 each |

Two seeds per stratum -> S = 12, `p_s` = stratum weight / 2 (sum 1). Seeds 0-11 in-sample; seeds 100-111 held out
(same strata). S = 10 = strata 1-3 and 5 with the remaining weight folded in (table only); S = 15 = three seeds per
stratum for the weekday strata (weights adjusted). `init_frac` stays `(0.25, 0.5)`. The demand hash of every scenario is
asserted layout-independent (`demand_md5`), as today. Orders of the 48-order scenarios enlarge delivery arcs by about
20 %; the cost table uses mean times.

SAA statement (section 2.7): in-sample certificate on the 12 scenarios; the chosen layouts re-priced on the 12 held-out
scenarios (unbiased value estimate with its 95 % CI); the optimality-gap estimate of the multiple-replication procedure
is given in its LP-based form on two extra replications when the budget allows (stage L).

### 1.8 Budgets, targets, prices

Budgets `m x 52,150 USD`, m = 1..4; prices `R6_PRICING` (P 60, w 18, v 15); tolerance `max(0.25 % UB, 1 USD)`;
nested budgets; relaxed targets headline; written targets priced on the best layout per budget, the best rule layout
per budget and the DOT-pilot proxy at m = 1-2 (8 layouts) with escalations.

---

## 2. Algorithm

### 2.1 What scales from the certified scheme and what does not

| component | at 15 candidates | at 40-60 candidates |
|---|---|---|
| scenario LP (`ScenarioLP`, cold barrier, safe Lagrangian cut) | 15-26 s | 30-70 s (fixed layout), 60-140 s (subset LP); S = 12 LPs per layout on 12 workers x 2 threads -> 1-3 min wall per layout (8 workers x 3 threads would leave 4 workers idle in the second wave of every layout) |
| envelope pruning (`Master.envelope`, size transfer at a site) | resolved 97 % of one-site layouts | same mechanism; one LP per location suffices for the sizes |
| exact pricing (`price_layout`, BestBdStop, escalations) | 6 min per layout (3 scenarios, **sequential** over scenarios: `price_layout` loops `for s in range(S)` and the `BestBdStop` of scenario s uses the bounds of the scenarios already solved) | 12 x 150-300 s = 30-60 min of solver time per layout; 4-8 min wall only with the **new** scenario-parallel pricing of section 4 item 2 (static `need_s` from `lb0` in a first parallel pass, sequential refinement of the rows that stopped early); **the number of priced layouts is the cost driver** |
| m = 1 enumeration | 90 layouts, 2-4 LPs + 1-2 pricings per target | 240-360 layouts, N + 10 LP layouts, about 8 pricings |
| single-layout LP / lifted cuts at m >= 2 | resolved one layout per 30 s LP; bound stayed trivial | same; not the tool for m >= 2 (section 2.3 replaces it) |
| LP phase (in-out, fractional points) | 2-4 h per target, bound below the trivial one | run once with S1 rows for the record; not relied on |
| master MIP | 210 binaries, seconds | 496 binaries plus a few thousand cuts, seconds to a minute |
| integrated stochastic ILP (A) | no usable bound at 12 candidates | incumbent checker only; not run |

### 2.2 m = 1: pruned enumeration (certified)

As in the second pass (`certify_by_enumeration`, location-major, envelope-ascending), with two changes:

1. **One LP per location is mandatory** (representative option `SC:B3:C2`) before any envelope prune, so that every
   candidate has an LP value (validation requirement, and the "siting landscape" map of section 4.6). Cost N x S LPs.
2. The open set after pass 2 is priced with the usual BestBdStop and escalated (900 / 1,800 s) until closed; expected
   open set 5-10 layouts (2-4 of 90 at 15 candidates, the tolerance scales with UB).

Written m = 1: the top-3 relaxed layouts plus the rule layouts are priced written; no written enumeration (the
15-candidate written m = 1 took 2.5 h for one open layout and ended uncertified).

### 2.3 m = 2 and 3: regional superset bounds and a hierarchical branch-and-bound over candidate subsets (new)

**Bound.** For a candidate subset A, let `LBA_s` = safe value of the elastic scenario LP with every role object of every
location in A open (`y = 1`) **with free sizes** (`B` free in `[0, K]`, `C` free in `[c_min, Cbar]`, exactly as the
existing superset bound `evaluator.superset_bound` does: "all open with free sizes"), everything outside A closed
(`y = B = C = 0`), relaxed targets, no budget. Under relaxed targets OPEX is non-increasing in the open set: `y`
appears only on the right-hand side of the `<=` rows (9), (15), (22) (and of (17) under written targets, where
`R_end = 0` here), so opening an object enlarges the feasible set (`bilevel_siting_design.md` 2.4; the C8 down-closure
argument). **It is not non-increasing in the sizes**: (16) fixes the initial full stock `n_jL0 = B_j` as an equality
and (15) caps the total stock at `K_j`, so a larger `B_j` leaves less room `K_j - B_j` for batteries arriving by
transfer; the first draft's "largest menu sizes" point is therefore not a relaxation of the smaller sizes when
transfers are used. With free sizes the LP is a relaxation of every layout inside A, so for every admissible layout x
with all open locations in A:

```
LBA_s <= Q^LP_s(x) <= Q^IP_s(x),      hence   V(x) >= min_{x in A, inv(x) <= Budget_m} setup(x) + sum_s p_s LBA_s.
```

Safe value with free sizes: `ScenarioLP.solve_subset(A)` turns the `B` / `C` fixing rows of the objects in A into
bounds, solves, and takes `LBA_s = c0 + sum_{l in A} beta_y,l + sum_{l in A} min(beta_B,l lb_B, beta_B,l ub_B) +
sum_{l in A} min(beta_C,l lb_C, beta_C,l ub_C)` from the C1 Lagrangian cut (`cut_from_pi`), i.e. the box minimum of
the cut over the free copies: valid for any multipliers, the same safety as every other cut. The per-size envelope
(section 2.2, `Master.envelope`) still uses the cut `c0 + beta . x` itself, so sizes inside an open leaf are
separated without extra LPs (the LP value of a spare is 9.81 USD at 8 bikes against 0.33 USD of allocated set-up, so
the cut typically prunes the small-B combinations of a leaf whose large-B combination was priced).

The master gets it as a combinatorial cut, valid at every integer point (if any site outside A is open the right-hand
side is at most `L_s`):

```
theta_s >= LBA_s - (LBA_s - L_s) * sum_{l not in A} sum_o w_{l,o}         (kind 'subset', tagged relaxed)
```

It is the superset bound (`L_s` = all candidates open) restricted to a region, and the enumeration floor of m = 1 is the
case |A| = 1 with the sizes free. It needs no integer information, costs S LPs per subset, and binds for every
layout inside A, which is what single-layout cuts cannot do. Not valid for written targets (R_end rows grow with
open sites); written m >= 2 stays an incumbent-plus-Benders-bound statement, as today.

**Branch-and-bound.** Atoms = the lattice cells (15 cells of 2 km; every DOT candidate lies in one; cells with no
candidate are dropped). Level 1: 5 coarse regions (three adjacent cells each, south -> north). A node is a union of
<= m regions / cells; its bound is `setup_min(k, A, window) + sum_s p_s LBA_s`, where `setup_min(k, A, window)` is the
cheapest admissible layout inside A **with exactly k open locations and investment in the window `(budget_{m-1},
budget_m]`** (the explicit minimum over the option multisets). **Corrected by the fixer pass (2026-10-20):** a
layout with fewer than m open locations is covered by the smaller budget's bound ONLY when its investment is at most
`budget_{m-1}`; the menu has one-site layouts above `budget_1` (`SC:B4:C1` 52,200 and `SC:B4:C2` 52,600 > 52,150) and
two-site layouts above `budget_2` (`B3:C2 + B4:C2` 104,750 > 104,300), so the certificate of budget m bounds the
window `(budget_{m-1}, budget_m]` for EVERY number of open locations `k = 1..m` (`benders.certify_bnb`: k = 1 by a
windowed enumeration -- envelope prune, LP, price; most of it LP-free thanks to the m = 1 LP cuts -- and k >= 2 by
one B&B pass each with the window in `setup_min`; `LB_m = min(LB_{m-1}, min_k floor_k)`). Prune if `>= UB_m - tol`. Refine a surviving node by
splitting its largest region into cells, then cells into single candidates; a node whose atoms are single candidates
and whose size is m is a size-free layout: its subset LP is its bound over all size combinations; if still open, the
size envelope selects the combinations to price (largest B first).

Subset LPs use `S_LP = 6` scenarios (one seed per stratum; the other six enter at their superset value `L_s`,
section 2.7, valid); a leaf that survives at `S_LP = 6` is re-solved on all 12 before pricing.

Node counts (worst case before pruning): m = 2: level 1 `C(5,2) + 5 = 15`, level 2 (cells) `C(15,2) + 15 = 120`,
level 3 only inside surviving cell pairs (with 4 candidates per cell, 16 cross pairs + 6 within-cell pairs per
surviving cell pair). m = 3: level 1 35, level 2 up to 680, which is why level 2 is entered only for region triples
that survive level 1 (expected: the demand core, 2-3 regions). The cost table budgets **200 nodes at m = 2** (15 + 120
+ about 65 leaves) and **100 nodes at m = 3** (35 + the level-2 nodes of the surviving triples), each `S_LP` LPs, 20
leaves at full S, plus 12 (m = 2) and 6 (m = 3) exact pricings; the run stops at the wall and reports the open subsets
(coverage statement), `LB_m` = min over open nodes of their bounds, exactly as the enumeration floor does today.

What to expect, honestly. Inside the demand core the all-open free-size LP of a region will be close to `L_s` (at
15 candidates the superset LP is 650.02 against a two-site incumbent OPEX of about 675.3: 3.6 %), so **the regional
levels prune the periphery, not the core**; the core is closed only at the leaf level, by per-pair LPs. At 15
candidates every one of the 72 two-site master proposals was pruned by its own LP value, which is the evidence that
leaf LPs do prune; the fixed-layout LP gap (median 0.8 %, max 5 %) against a tolerance of 0.25 % says that the pairs
within about 1 % of the incumbent will need pricing or S2. Expected outcome: a certificate at m = 2 if the core holds
at most about 15 candidates (105 pairs) and fewer than 12 pairs end within the tolerance; otherwise m = 2 ends with a
gap of 0.5-2 % and a list of open pairs, which is still a far stronger statement than today's trivial bound
(7,060 open layouts). m = 3 is run to level 2 only and reported as bound + incumbent; it is certified only if every
three-region node is above the two-site incumbent (a third site provably useless), else a gap of 1-3 %.

**Where the stronger cuts of the design note fit.** S1 (disaggregated terminal rows `X_a <= U_a Yc`, cheap) is switched
on in every scenario LP: it tightens the subset LPs (fractional `y` is exactly where aggregated (9) is weak; here the
subset LP is at integer `y`, so S1 changes nothing for it, but it tightens the LP phase and the relax-and-round
screen). S2 family cuts (one ILP per scenario per open-role family, bound over all sizes) are used only on the last
open pairs of the B&B when their LP values sit inside the tolerance (the "family" of a pair = its two locations with
roles fixed, 36 size combinations). Lagrangian / integer L-shaped cuts stay as today (generated at every priced
layout). Cuts generated at master two-site proposals remain the last polish (stage G, fixed 2 h).

### 2.4 m = 4 and the believable answer without a certificate

m = 4 (optional stage F): greedy + local search (`greedy_local_search`, screen `'lp'` = cut envelope then `v_LP`)
seeded with the m = 3 incumbents, `k_screen = 3`, 6 pricings. Bound: the master at budget 4 with every cut in the
pool. Nesting runs the other way (`SitingCertifier._nested_lb`: `V*_m >= V*_{m'}` for `m <= m'`, so a bound proved
at a larger budget is valid at a smaller one, never the reverse); the subset cuts of nodes with <= 3 regions do not
bind for a layout spanning four regions, so `LB_4` is essentially the trivial bound `L + cheapest four-site
set-up`. Reported with the regret interval against the rule layouts and against `LB_4`, never as "optimal"; the
paper states m = 4 as "not certified; the m = 3 bound does not transfer".

For every budget the report gives: the best layout found, `LB_m`, the gap, the regret interval of each comparison
layout `[V_rule - UB_m, V_rule - LB_m]`, the paired difference over scenarios with its 95 % CI, and the out-of-sample
values. That is the same protocol as `outputs/r6_o2/RESULTS_final.md` Tables 1-3.

### 2.5 Two-tier pricing (new switch, cost control)

Incumbent values may be computed with the cheaper `open_sites` library (1.4-2.3 M arcs, medians 28-113 s) because they
are valid upper bounds on the all-candidates value; integer cuts and `LBIP` need the all-candidates bound
(`DECISIONS` O2 conventions). `price_layout(..., tier='open_sites' | 'all_candidates')`: **only the greedy moves of stage F** use `open_sites`
and enter the master only as `UB`; layouts that decide a certificate (m = 1 open set, B&B leaves) and **every layout
that appears in a comparison table** (rule, DOT pilot, transplanted, out-of-sample, hub sensitivity) use
`all_candidates`. Reason: the open-sites value of a layout is an upper bound on its all-candidates value, so pricing
the rule layouts open-sites and the best layouts all-candidates would bias every paired difference and regret
interval against the rules (the first draft had the comparison layouts on the cheap tier). The cost table assumes
all-candidates everywhere except stage F.

### 2.6 Comparison protocol

| comparison | definition | cost |
|---|---|---|
| rule layouts CSCD / CSTC / CSAV | `rule_layout` at m = 1-4 on the N candidates (demand weights with radius D = 14, access weights, max-min spread); role SC, menu caps of the reduced menu | 12 layouts |
| present-day proxy = DOT pilot | `present_day_sites` reads `PRESENT_DAY_FILES`; add `dot_candidate_sites.csv` rows of type `pilot` as a third source (weight 1 per pilot site); `capacity_matched_layout` at m = 1-4 to the best layout found; plus the all-pilot layout (every in-region pilot site open as SC:B3:C2, its own budget row, m = 5 if 5 sites remain in the region) | 5 layouts |
| transplanted 15-candidate optima | `M09:SC:B3:C2`, `M04+M09` moved to the merged candidates (same nodes, since the lattice candidates are in the set) | re-priced (2-3 layouts): the `manhattan_dot` keys differ by family and `max_pair_km`, so never cache hits (fixer pass, 5.1 step 2) |
| DOT-only vs full | master with the lattice-only candidates fixed closed (`--restrict dot`): same template, cuts and cache; `V*_DOT >= V*_full`; reported per budget with both bounds | one more master per budget (seconds) + pricing of the DOT-only incumbent if it differs (<= 4 layouts) |
| followers | ILP (headline), rule r2, selfish M4 on the best layout per budget and the best rule layout (`cross_evaluate`, minutes) | minutes |
| compliance | psi in {0, .25, .5, .75, 1} x 3 draws x S on the chosen m = 2 layout (`r6_fill.py --stage compliance`, pointed at the new records) | 0.3 h |
| out-of-sample | 12 held-out scenarios: templates built once (section 1.7), the best layout per budget (m = 1-3), the best rule layout per budget, the DOT all-pilot layout and the capacity-matched DOT proxy at m = 2 priced (8 layouts x 12 ILPs, all-candidates); in- vs out-of-sample difference reported | stage I |
| charging-station question | (a) a **role table** per budget: the best layout, the best S-containing layout and the best hub-containing layout found (from the enumeration / B&B records and the LP screen), with their values and bounds, so that "all co-located" is a reported finding with the price of the alternatives; (b) sensitivity on the hub economics: (i) site power cap `P_kw` 1.4 -> 0.7 kW at SC sites (sidewalk cabinet cannot carry chargers) with hubs at 2.8 kW, (ii) `F_hub` 29.19 -> 12.03 (hub priced like a site); a grid-connection surcharge is dropped (it only moves hubs further away); for each setting the best m = 2 layout, CSCD m = 2 and the best hub-containing layout from an LP screen of the **hub-capable sites only** (<= 12 locations x 2 sizes added to the m = 2 incumbent; hubs elsewhere are not in the template, section 1.3) are priced | stage J |
| written targets | 8 layouts (section 1.8) | stage H |

### 2.7 SAA and statistics

* In-sample: certificate and regret intervals on the S = 12 stratified scenarios (p_s as in 1.7). CIs over scenarios
  use the stratified estimator (within-stratum variance, weights p_s), paired by scenario for differences. With two
  seeds per stratum the within-stratum variance has 6 degrees of freedom (t = 2.447), so the report also gives the
  plain paired t over the 12 scenarios (11 df) and states which is used; neither is narrow, and the paper must say so
  (the 3-scenario CIs of the 15-candidate study were +/- 100 USD on 700).
* Out-of-sample: the chosen layouts on the 12 held-out scenarios; report `V_out - V_in` with its CI (over-fitting check,
  the E9.5 protocol).
* MRP (optional stage L, **m = 1 only**): two extra replications of the in-sample design at `S_rep = 6` (one seed per
  stratum, seeds 200-205 and 300-305; `S_rep = 5` cannot be stratified over 6 strata), LP-only enumeration floor at
  m = 1 (`N + 10` LP layouts each). Since `E[v*_N] <= v*` for every N and `LB^(k) <= v*_{S_rep}^(k)`, the mean of the
  three lower bounds is a conservative lower-bound estimator; the upper estimator is the held-out value of the
  in-sample best layout. The gap estimate is labelled "LP-based, conservative". At m = 2 the MRP is not run: its
  per-replication bound would be the level-2 B&B bound, which is near the trivial bound, so the "gap" would measure
  the bound's weakness, not the sampling error; the m = 2 statement is the in-sample bound gap plus the out-of-sample
  difference.
* With fewer LP scenarios than pricing scenarios (the `S_LP = 6` rule of section 2.3 and the cut-first list, section
  3.3): a bound that uses the LP of a scenario subset is `sum_{s in LP} p_s LBA_s + sum_{s not in LP} p_s L_s` (the
  others at their superset value): valid, weaker.

---

## 3. Cost model

### 3.1 Unit costs (from the records, 3-thread Gurobi, laptop; x1.3 for the r7i until the dry run measures it)

**2026-10-21: not yet replaced by server measurements (instance unreachable); see section 8 for the probe that
measures these unit times and for a laptop smoke that puts the subset-LP factor at 1.6-3.3 x.**


* scenario LP cold barrier, fixed layout: 15 s (one open site) / 26 s (2-4 sites) at 1.1 M columns
  (`o2_manhattan_first_pass.md`); scaled x1.6 (N = 40) and x2.1 (N = 60) for the larger templates (section 1.4);
* subset LP (a region open with free sizes): **2 x the 2-4-site time** (never measured; presolve removes fewer columns
  when more objects are open; the all-open per-bike LP took 194-257 s, the aggregated one was never solved);
* pricing ILP, mean per scenario (`manhattan_pass2/cache/index.jsonl`, 149 rows): 290 s (one site, with escalations;
  OPTIMAL median 172 s) / 244 s (two: 17 OPTIMAL at 191 s, 16 TIME_LIMIT at 300 s) / 150 s (three-four); x1.07 for
  the 32 / 40 / 48-order mix (48-order ILPs about +20 %); unchanged size with the radius convention;
* escalation of one scenario: 900 + 1,800 s;
* workers: r7i.8xlarge, 24 threads (1.5 per physical core, the `run_lanes.sh` rule): LP stages 12 workers x 2 threads
  (a 2-thread barrier solve taken as 1.3 x the 3-thread time; all 12 LPs of a layout run at once), ILP stages 8
  workers x 3 threads on a global (layout, scenario) cell pool (utilisation 0.9); r7i.4xlarge: 6 x 2 and 4 x 3;
  15 % overhead for scheduling, I/O and the master; fixed hours for setup, polish and analysis;
* Spot prices (us-east-2, October 2026): r7i.8xlarge about 0.80 USD/h (on-demand about 2.12, so 0.80 is a 62 % discount;
  check the current price before launching), r7i.4xlarge 0.35-0.45 (0.42 used); on-demand 4xlarge 1.06. EBS: shrink
  the root volume to 60 GB (about 5 USD/month; the O2 caches are 3-25 MB, the templates are not persisted). The
  on-demand 4xlarge **must be stopped** for the duration of the Spot run (1.06 USD/h would add 30-35 USD).

Stage counts per configuration (LP layouts x LPs; ILP layouts x S ILPs; escalations): A 18 ILPs (radius validation);
B 19 / 19 / 0; C (N + 10) x S / 8 / 4; D 200 x `S_LP` + 20 x S / 12 / 4; E 100 x `S_LP` / 6 / 2; G fixed 1.5 h;
H 0 / 8 / 6; I 96 ILPs; J 8 x S / 6 / 0; M fixed; optional F 40 x S / 6 / 0, K 3 x S ILPs at 600 s, L 2 x (N + 10)
x 6 LPs.

### 3.2 Table (wall hours and USD; "core" = without the optional stages F, K and L; calculator
`cost_calc2.py` in the critic's scratchpad, reproduced from the unit costs above)

| configuration | r7i.8xlarge Spot, 0.80 USD/h | r7i.4xlarge Spot, 0.42 USD/h | r7i.4xlarge on-demand, 1.06 USD/h |
|---|---|---|---|
| N = 40, S = 10 | 28.0 h, 22.4 USD (core 25.0 h, 20.0 USD) | 52.5 h, 22.0 USD (core 46.5 h, 19.5 USD) | 52.5 h, 55.6 USD (core 49.3 USD) |
| N = 60, S = 10 | 31.7 h, 25.4 USD (core 28.0 h, 22.4 USD) | 59.9 h, 25.2 USD (core 52.4 h, 22.0 USD) | 59.9 h, 63.5 USD (core 55.5 USD) |
| N = 40, S = 12 | 30.6 h, 24.5 USD (core 27.1 h, 21.7 USD) | 57.6 h, 24.2 USD (core 50.7 h, 21.3 USD) | 57.6 h, 61.1 USD (core 53.8 USD) |
| **N = 60, S = 12 (recommended)** | **34.5 h, 27.6 USD (core 30.2 h, 24.2 USD)** | 65.5 h, 27.5 USD (core 57.0 h, 23.9 USD) | 65.5 h, 69.5 USD (not within budget) |
| N = 40, S = 15 | 34.4 h, 27.6 USD (core 30.3 h, 24.2 USD) | 65.4 h, 27.5 USD (core 57.1 h, 24.0 USD) | 65.4 h, 69.3 USD (core 60.5 USD) |
| N = 60, S = 15 | 38.7 h, 31.0 USD (core 33.7 h, 26.9 USD) | 73.9 h, 31.0 USD (core 63.8 h, 26.8 USD) | 73.9 h, 78.4 USD (core 67.6 USD) |

With the first draft's stage counts (300 + 150 subset nodes at full S, m = 4 in the core, 3 hub settings) and the
corrected unit costs the N = 60, S = 12 run would be 58 h = 47 USD (core 50 h = 40 USD): over budget. The first
draft's "about 32 h, 26 USD" for S = 12 was also inconsistent with its own S = 10 row (34.8 h).

Per stage, **N = 60, S = 12, r7i.8xlarge** (solver hours are 3-thread solve time before parallelism):

| stage | 3-thread LP h | 3-thread ILP h | escalation h | wall h |
|---|---|---|---|---|
| A setup: templates, DOT snap, sanity, `size` dry run (4 LP timings), radius validation (18 ILPs) | 0.0 | 1.7 | 0.0 | 1.3 |
| B comparison layouts, relaxed, all-candidates (rules m 1-4, DOT pilot m 1-5, transplanted 2) = 19 layouts | 4.5 | 21.5 | 0.0 | 4.0 |
| C m = 1 enumeration: one LP per location (full S) + envelope, 8 pricings, 4 escalations | 9.6 | 10.8 | 3.9 | 3.5 |
| D m = 2 subset B&B: 200 nodes at S_LP = 6, 20 leaves at full S, 12 pricings, 4 escalations | 56.8 | 13.6 | 3.9 | 9.9 |
| E m = 3 subset B&B levels 1-2: 100 nodes at S_LP = 6, 6 pricings, 2 escalations | 23.7 | 4.2 | 1.9 | 3.9 |
| G Benders integer phase polish m = 2-3 (S1 rows, master proposals), fixed wall | 0.0 | 0.0 | 0.0 | 1.5 |
| H written-target sensitivity on 8 layouts, 6 escalations | 0.0 | 9.1 | 5.8 | 2.4 |
| I out-of-sample 12 held-out scenarios x 8 layouts; r2 / selfish; compliance sweep | 0.0 | 9.1 | 0.0 | 1.9 |
| J charging-hub sensitivity (2 settings x 3 layouts + LP hub screen of 8 additions) | 1.9 | 6.8 | 0.0 | 1.3 |
| M analysis, tables, map figure, report (no solver) | 0.0 | 0.0 | 0.0 | 0.5 |
| **core total** | | | | **30.2 h = 24.2 USD** |
| F m = 4 greedy + LS from m = 3 (LP screen 40, 6 pricings) [optional] | 9.5 | 4.2 | 0.0 | 1.8 |
| K fleet sensitivity 12 bikes (3 layouts, 600 s ILPs) [optional] | 0.0 | 7.8 | 0.0 | 1.2 |
| L SAA MRP at m = 1: 2 LP-only replications at S_rep = 6 [optional] | 9.6 | 0.0 | 0.0 | 1.2 |
| **total with the optional stages** | | | | **34.5 h = 27.6 USD** |

Stage D is the cost driver (a third of the core wall time) and its node count is the least certain number in the
table. Everything is an estimate from recorded unit times; the `size` dry run (four LP timings and one pricing ILP)
and stage C recalibrate the unit times, and the lane plan is regenerated from the measured ones before stage D starts.

### 3.3 Budget rule and what to cut first

Remaining budget about 40 USD of 50 (10 spent); target for this study <= 35 USD including EBS (5 USD) and a 20 %
contingency for Spot price changes and one repeated stage: core 24 + 5 + 5 = **34 USD**. Recommended: N = 60 (or
whatever the merged DOT set gives, 40-60), S = 12, r7i.8xlarge Spot, core stages first; the optional stages F, K, L
(3.4 USD together) only if the core finishes under 22 USD. If the measured unit times exceed the table by more than
30 % after stage C, cut in this order:

1. stage J down to one setting (site power cap) and 2 layouts (saves about 0.7 h);
2. stage D node budget 200 -> 120 (levels 1-2 only; leaves only inside the two best cell pairs): m = 2 reported as
   bound + open pairs (saves about 4 h);
3. stage E entirely: m = 3 reported as incumbent + the master bound with the m = 2 subset cuts (saves about 4 h);
4. shorter ILP limits: 200 s with the MIP gap reported, escalations 600 / 1,200 s (saves about 3 h over B, C, H);
5. stage H down to 4 layouts (saves about 1.2 h);
6. N = 40 (drop `other` / `lot` DOT types first; saves about 3 h over C-E);
7. S = 10 for pricing (fold the weekend strata as in section 1.7; saves about 3 h) -- last, because it weakens the
   statistics.

Spot interruption: every stage is resumable (records, cut pool, cache, and the new `subset_bound` records); the
dispatcher restarts the lane after `run_lanes.sh start` is run again; the Spot request is made with the **stop**
interruption behaviour on a persistent request, so the EBS volume and the records survive, and a boot-time unit
re-runs `run_lanes.sh start` (section 4 item 5); the idle watchdog stops the instance 20 min after the last lane.

---

## 4. Implementation list (follow-up coding task)

All in `ebike_swap_sim/`; English only; defaults unchanged so that the existing tests and the 15-candidate run are
byte-identical when the new flags are off.

1. **`sites_nyc.py`**
   * `dot_candidates(path, region, merge_m=80.0, cap=60, hub_types=('depot', 'lot'))` (section 1.1), writing
     `candidates.csv` and `candidates_dropped.csv`; `Candidate` gains `hub_capable: bool`, `lattice_id: Optional[str]`,
     `snap_m: float`, `dot_type: Optional[str]`.
   * family `MANHATTAN_DOT_FAMILY = 'manhattan_dot'` in `SITING_FAMILIES` (parameters = `R5_MANHATTAN_PARAMS`),
     `SITING_POST` entry (same energy calibration and tariff), `SIZE_MENUS['manhattan_dot']` (section 1.2),
     `family_candidates` / `family_depots` / `family_access_D` cases.
   * `siting_pruning(..., approach_radius_blocks=None)`: when set, move arcs into candidate nodes only from nodes
     within the radius; depots unrestricted. Implemented as a new arc-builder option `reposition_target_radius:
     {node: blocks}` in `arcs._template_specs` (skip `(v, w)` routes with `w` a candidate and
     `manhattan_blocks(v, w) > radius`); `None` = today's behaviour; part of the pruning signature and the cache key.
   * `scenario_design(S, held_out=False)` (section 1.7) returning `[(seed, overrides, p_s)]`;
     `make_base_instance` accepts `orders_per_bike_hour` and `profile` overrides (it already forwards `**overrides`;
     the generator's `block_profile(day_type='weekend')` and `weekend_factor` exist, `data_nyc.make_nyc_instance`
     must expose `day_type`).
   * `SitingSpec.max_pair_km = 2.0` for the new family (`spec_from_instance` override), hub-capable filter in
     `all_candidates_instance` / `layout_instance` (C objects only at hub-capable locations; `roles` becomes
     per-candidate).
   * `siting_pruning` / `pruning_signature`: the radius enters the signature **only when set** (`None` adds no key),
     otherwise every existing cache key and `config_md5` changes and the reproduction test of section 5.1 fails.
2. **`benders.py`**
   * `MenuEncoding`: per-location option lists (hub options only at hub-capable locations); `Master`: `restrict(ids)`
     (fix every binary of other locations to 0, for the DOT-only run) and the `subset` cut kind
     (`Cut.kind = 'subset'`, `meta.atoms`, `linear()` = section 2.3 form; `applies_to` relaxed only).
   * `ScenarioLP.solve_subset(A, scenarios)`: `y` fixing rows set to 1 on the objects of A and 0 elsewhere, the `B` / `C`
     fixing rows of A **turned into bounds** (free sizes, section 2.3), solve, safe value = box minimum of the C1 cut
     over the free copies, fixing rows restored; S1 rows behind `ScenarioLP(s1=True)`.
   * **Scenario-parallel pricing** (new; today `price_layout` is sequential over scenarios and the certifier prices
     one layout at a time): a `PricingPool(n_workers)` of threads (Gurobi releases the GIL in `optimize`; model build is
     4-5 s per cell, so threads suffice) over (layout, scenario) cells; a first pass with the static
     `need_s = (target - setup - sum_{t != s} p_t lb0_t) / p_s`, then the sequential refinement of the rows that
     stopped on `BestBdStop`; `LowerLevelEvaluator._store` / `append_jsonl` and the `keep_libraries` LRU behind a lock;
     one Gurobi `Env` per worker. Without it the ILP stages take 8 x longer (section 2.1).
   * `SubsetBranchAndBound(certifier, atoms, levels, m, wall, S_LP)`: node list, bounds, pruning, refinement, leaf LP
     (S_LP then full S) and pricing through the existing `lp_at` / `price`; records `subset_bound` (atoms, level, bound
     per scenario, scenarios used, pruned) and `bnb_done` (open nodes, `LB_floor`); resume from the records;
     `pool_bound` reads subset cuts.
   * `price_layout(..., tier=...)` two-tier pricing (section 2.5): `open_sites` rows never feed `LBIP`, never a
     comparison table.
   * `certify_by_enumeration`: `force_lp_per_location=True` (one LP per location before pruning).
   * stratified `p_s` already supported (`probabilities`); CI helpers in the analysis use them (stratified and plain
     paired t, section 2.7).
3. **`bilevel.py`**: `present_day_sites` reads `dot_candidate_sites.csv` rows of type `pilot` as a source;
   `rule_layout` unchanged (menu caps from the reduced menu); `greedy_local_search(screen='lp')` seeded with layouts;
   a second `LowerLevelEvaluator` on the held-out scenarios shares the cache directory (keys carry `demand_md5`).
4. **`experiments/r6_o2_siting.py`** (or a new `experiments/r7_dot_siting.py` that imports it): flags
   `--family manhattan_dot|r5_manhattan`, `--dot-csv`, `--menu reduced|full`, `--scenarios 12 --held-out`,
   `--approach-radius 14`, `--restrict dot|full`, `--bnb-budgets 2 3 --bnb-nodes 200 100 --bnb-levels 3 2
   --bnb-lp-scenarios 6`, `--pricing-tier`, `--pricing-workers 8`,
   `--stage {size,setup,warm,m1,bnb2,bnb3,m4,polish,written,oos,hubs,fleet,mrp,analyse}`,
   `--lp-workers 12 --lp-threads 2 --threads 3 --master-threads 2`, memory guard `--max-rss-gb` (abort a stage
   before it starts a solve when RSS exceeds it), `--wall-<stage>` hours. **Remove the hard-coded laptop cap**
   `lp_workers x lp_threads + master_threads <= 12` (`r6_o2_siting.py` line 1059) in favour of `--max-threads`
   (default: `run_lanes.sh` rule). Every stage appends to `records.jsonl`, `cuts.jsonl`, `cache/`; resume as today
   (`--resume-open`).
5. **Cloud lanes** (`deploy/aws/make_cloud_lanes.py`): a `--dot` plan writing lanes `A -> B -> C -> D -> E -> G
   -> H, I, J (parallel after G) -> M` (F, K, L appended when enabled) with thread accounting for 24 threads, the
   measured-minutes recalibration after stage C, and the Spot-restart rule; `run_lanes.sh` unchanged; `sync_down.sh`
   includes `outputs/r7_dot/`. **New operational items**: (a) the Spot request (persistent, interruption behaviour
   `stop`) and a systemd unit or `@reboot` cron that runs `run_lanes.sh start` after a restart; (b) stop the on-demand
   4xlarge before the Spot run starts and keep it stopped; (c) the Gurobi licence on the instance is a WLS file
   (`bootstrap.sh` step 4: it needs outbound HTTPS), which is portable to the new instance, so `upload_licence.sh`
   runs once on the 8xlarge; (d) the security group allow-list must be updated when the user's public IPv4 changes
   (the user said they may change networks); (e) `--max-rss-gb 200` on the 8xlarge, 100 on the 4xlarge.
6. **Outputs**: `outputs/r7_dot/<stage>/` records; `RESULTS.md` tables: (T1) per budget and target: best layout, inv,
   UB, LB, LB kind (enumeration / subset B&B level / master), gap, certified, open nodes, ILP statuses, served share;
   (T2) comparison layouts with regret intervals and paired CIs; (T3) DOT-only vs full; (T4) followers and compliance;
   (T5) out-of-sample; (T6) hub sensitivity; (T7) coverage and timings (LP count, ILP count, escalations, wall per
   stage, unit times measured vs table). **Map figure** `fig_dot_map.pdf/.png` (double column): Manhattan south of
   110th St with NTA polygons, all candidates (DOT types by marker, lattice cells hollow), the six depots, the one-site
   LP value of every candidate as a colour scale (the siting landscape), the best layouts at m = 1-3 (filled, sized by
   B, labelled), the CSCD layout at m = 2 and the DOT pilot sites; a second panel with the B&B pruning map (cells
   pruned at level 1 / 2 / open). Script `outputs/r7_dot/figs/siting_report.py` extending `outputs/r6_o2/figs/
   siting_report.py`; every number recomputed from the records.
7. **Tests** (`tests/test_dot_siting.py`, toy, Threads 1): DOT CSV parsing, snapping and the 80 m merge (two rows at
   50 m merge, two at 120 m with distinct nodes stay); hub-capable filter; subset bound validity on the toy (every
   layout inside A has `V >= setup + sum p_s LBA_s`, and the subset cut holds at every integer point) **including a
   toy with transfer services and `K` close to `B_max`, where the max-size point is NOT a valid bound and the
   free-size point is** (the case of section 2.3); B&B returns the exhaustive optimum on the toy at m = 1, 2;
   approach radius = infinity reproduces the default library byte for byte and leaves the pruning signature
   unchanged; two-tier pricing never uses an open-sites row in an integer cut or a comparison row; the parallel
   pricing pool gives the same `PriceResult` as the sequential `price_layout` on the toy (values, statuses, cache
   rows); stratified `p_s` sum to 1 and the CI helpers match a hand computation.

---

## 5. Validation plan

### 5.1 The 15-candidate results as a special case (no production time; cache hits)

1. `--family r5_manhattan --menu full --seeds 0 1 2 --approach-radius none` through the new code path must produce
   the same template arc counts (5,835,874 / 5,923,013 / 6,133,784), the same `demand_md5`, the same cache keys
   (`outputs/r6_o2/manhattan_pass2/cache/index.jsonl` rows are hits) and, with `--bound-from-cuts` on the copied
   pool, the same bounds (relaxed m = 1 1,052.995; m = 2-4 675.740; written 1,115.251 / 676.240).
2. `--family manhattan_dot` with a CSV containing only the 15 lattice points (a fixture) must give the same candidate
   nodes (`test_lattice_fixture_reproduces_the_15_candidate_nodes`). **Corrected by the fixer pass (2026-10-21):**
   "identical keys again" cannot hold: the family name and `max_pair_km = 2.0` (`FAMILY_SPEC_OVERRIDES`, hence the
   transfer pairs) enter every cache key and the pool signature of `manhattan_dot`, so this step checks the candidate
   nodes only, and the transplanted 15-candidate optima of stage B are re-priced on the new family (budgeted there).
3. **Approach-radius effect** (the only new convention that changes values): re-price `M09:SC:B3:C2`, `M04+M09 (B2/B4)`
   and `M08+M09` under `--approach-radius 14` on seeds 0-2 (3 layouts x 3 scenarios x 2 conventions, about 1 h on the
   instance); report the difference (expected below 1 USD; if above 1 % the radius is raised to 20 blocks and the
   size table of section 1.4 is redone).
4. Subset bound sanity on the 15-candidate pool: `LB_{A = all} = L_s` within 1e-6 (the free-size all-open point is
   exactly the superset bound); `LB_{A = {M09}}` is at most the one-site LP value of every `M09` size option in the
   cache (free sizes relax every fixed size); `LB_A` non-increasing when A grows (10 random nested pairs); the
   certified relaxed m = 1 value 1,052.995 is reproduced by the B&B at m = 1 (leaves = single candidates).
5. **Subset-LP timing** on the 15-candidate family (part of the `size` dry run, 2 x 3 LPs): the all-open free-size LP
   of one cell pair and of all 15 candidates against the 26 s two-site LP; this is the x2 assumption of section 3.1.

### 5.2 Sanity checks on the new instance (stage A, written to the plan record and RESULTS T7)

* candidate table: N, dropped rows and reasons, merges, `snap_m` distribution (max below 110 m), hub-capable count;
* coverage: `uncoverable_bikes` empty in every scenario (every bike has a terminal arc with all candidates open);
  `access_sets(D = 14)` has no empty zone, or the empty zones are listed;
* reachability per candidate: every candidate's SC object has at least one terminal arc from a reachable state in
  every scenario and at least one swap arc with incoming move flow possible (reported as a count of scenarios);
* every candidate priced at least in the LP: the per-location LP of stage C (N x S values) is complete; the map shows
  the value of every candidate;
* services: number of ordered pairs within 2 km and `z` columns per scenario (must stay below 0.6 M; expected 0.45-0.5 M);
* LP sizes, RSS and the four LP timings from the `size` dry run against sections 1.4 and 3.1 (abort thresholds: 2.5 M
  columns per LP, 100 GB RSS on the 4xlarge, 200 GB on the 8xlarge; a subset LP above 3 x the two-site LP triggers
  the cut list of section 3.3 before stage D);
* demand: `demand_md5` layout-independent per scenario, stratum weights sum to 1, order counts 32 / 40 / 48;
* the warm-start layouts are admissible and inside the menu (`in_menu` true in the plan record), the DOT pilot proxy
  uses only in-region pilot sites (count reported; fallback flagged when fewer than 2 remain).

### 5.3 Run-time checks

* After stage C: measured LP and ILP unit times against section 3.1; the lane plan is regenerated when they exceed
  the table by 30 % (cut list 3.3).
* Every certificate row: `LB <= UB`, `LB_kind` named, `bound_from_cuts` equals the certifier's LB (the toy test and
  the post-hoc run), ILP rows pass `check_ok`, no `ERROR` / `SKIPPED_BUDGET` rows, every `TIME_LIMIT` row's gap listed.
* B&B: the open-node list at the wall is reported; a layout outside every open node and every priced layout has a
  bound `>= UB - tol` (brute-force check of the envelope over all m = 1 layouts and over the 120 cell pairs at m = 2).

---

## 6. Risks (to be reported, not hidden)

1. **The DOT candidate set may not exist in the assumed form** (the parallel task). The builder tolerates missing
   columns (type defaults to `other`) and a small set (N < 40 is run as is; the lattice union adds 15).
2. **Pricing time on 48-order scenarios** (about 20 % more delivery arcs) and on written targets: more `TIME_LIMIT`
   rows; mitigated by BestBdStop, escalations only where they decide a certificate, and the gap reporting (the
   two-tier pricing helps only the greedy moves of stage F).
3. **The subset bound may be weak inside the demand core** (an all-open region LP close to `L_s`): then m = 2 ends with
   a few open cell pairs and a 1-2 % gap; S2 family cuts and the Benders polish are the next tools; the honest
   statement is the regret interval.
4. **Spot interruptions** on the 8xlarge: every stage resumes from records; a lane restarted loses at most the
   running solves (<= 30 min).
5. **Memory** with S = 15 and 8 pricing workers on the 4xlarge: the `--max-rss-gb` guard and `keep_libraries = 2`;
   fall back to 6 workers.
6. **Approach radius** changes values by more than expected: measured in 5.1 step 3 before any production stage; the
   radius is raised if needed and the cost table recomputed.
7. **Few bikes for a city-wide candidate set**: with 8 bikes and 40 orders a third site may again never pay; the fleet
   sensitivity (stage K) shows how the number of sites that pays grows with the fleet, and the paper states the fleet
   slice explicitly.
8. **Budget**: the recommended configuration is about 24 USD (core) at Spot prices plus 5 USD EBS; a price spike or a
   repeated stage can reach 34 USD; the cut list of 3.3 is applied before, not after, the overrun. The on-demand
   4xlarge left running in parallel would add 1.06 USD/h and break the budget within a day.
9. **Unit times are laptop times**: the laptop-to-r7i factor (1.3 assumed) and the subset-LP factor (2 assumed) have
   never been measured; both are measured in the `size` dry run before any production stage, and the lane plan is
   regenerated. If the subset LP is 4 x the two-site LP, stage D alone is 20 h and the cut list applies.
10. **No m = 2 certificate** is the realistic downside (section 2.3): the paper then reports the gap and the open pairs,
    which is still a quantified statement; the regret intervals against the rule and DOT layouts do not depend on it.
11. **The DOT candidate file may carry few hub-capable rows** (the pilot sites are sidewalk cabinets): the hub question
    is then answered only at the lattice fallback locations, and the paper must say that charging hubs were allowed at
    these locations only.


---

## 7. Critique and corrections (critic pass, 2026-10-20)

Scope of the check: sections 0-6 above against `benders.py` (`ScenarioLP`, `price_layout`, `Master.envelope`,
`SitingCertifier._nested_lb`), `bilevel.py` (`LowerLevelEvaluator.evaluate`, `superset_bound`), `sites_nyc.py`
(`_services`, `SitingSpec`, `all_candidates_instance`, `siting_pruning`), `arcs.py` (`_template_specs`, `Arc`),
`experiments/r6_o2_siting.py` (thread caps), `deploy/aws/*`, E2 (13)-(18) in `notes/extracted/E2.txt`, and the
records `outputs/r6_o2/manhattan_pass2/{records.jsonl, cache/index.jsonl, wall_time.json}`,
`outputs/r5_x6_manhattan/cache/index.jsonl`, `o2_manhattan_first_pass.md`. No solver was run. Every correction
below has already been written into the section it names; this section lists what was wrong and why.

### 7.1 Bound validity

1. **The subset bound at "largest menu sizes" was not valid (section 2.3, fixed).** The draft took `LBA_s` as the LP
   with every object of A open at `B = 4, C = 2` and claimed OPEX is non-increasing in the sizes. E2 (16) fixes
   `n_jL0 = B_j` as an equality and (15) caps `sum_q n_jqt <= K_j y_j` (`K = 8`), so a larger `B_j` leaves less room
   for batteries arriving by transfer (`A_jqt`); a layout with `B = 2` can receive 6 batteries where `B = 4` can
   receive 4. The LP at `B = 4` is therefore not a relaxation of the LP at `B = 2` when transfers are used, and the
   "bound" could exceed the value of a layout inside A. `bilevel_siting_design.md` 2.4 only claims monotonicity in
   the open set and in `C`, plus the direction `B = 0 -> B > 0` of opening; C8 is about infeasibility, not value.
   Correction: free sizes (`B` in `[0, K]`, `C` in `[c_min, Cbar]`) in the subset LP, exactly as
   `LowerLevelEvaluator.superset_bound` already does for the all-open point; the safe value is the box minimum of the
   C1 cut over the free copies. Monotonicity in `y` alone is what the bound needs, and that holds under relaxed
   targets (`y` only on the right-hand side of `<=` rows). A toy test with transfers and `K` close to `B_max` is added
   (section 4 item 7).
2. **The subset cut** `theta_s >= LBA_s - (LBA_s - L_s) sum_{l not in A} sum_o w_{l,o}` is valid at every integer point
   (if any site outside A is open the right-hand side is at most `L_s`, the superset floor already in the master);
   it is a linear inequality valid at all integer points, so the LP-relaxed master in the in-out phase keeps a valid
   bound too. No change.
3. **`setup_min(m, A)` was ambiguous (fixed), and the first fix had a hole (fixed again by the fixer pass).**
   "Cheapest admissible layout inside A at budget m" would be the single cheapest site at every m, which makes every
   node bound trivial. The node bound of a B&B pass uses layouts with exactly k open locations. The earlier claim
   "layouts with fewer open locations are covered by the smaller budgets" is FALSE when a size option exceeds the
   budget unit: `LB_{m-1}` covers only layouts with investment `<= budget_{m-1}`, and one-site layouts at 52,200 /
   52,600 (`SC:B4:C1`, `SC:B4:C2`) or two-site layouts at 104,350-105,200 lie in `(budget_{m-1}, budget_m]` (toy: UNIT
   = 125, F = 30, the optimum at budget 250 is `T2:SC:B2:C1` at investment 130 while the old B&B certified 129.0 > 126.0).
   The certificate of budget m therefore bounds the window `(budget_{m-1}, budget_m]` for every `k = 1..m` (k = 1 by
   windowed enumeration, k >= 2 by one pass each with the window inside `setup_min`, which also tightens the k = m
   pass) and takes `LB_m = min(LB_{m-1}, min_k floor_k)`; test
   `test_bnb_window_covers_layouts_with_fewer_sites_above_the_smaller_budget`.
4. **The m = 4 bound was wrong (section 2.4, fixed).** The draft wrote `LB_4 = LB_3` "nested". `_nested_lb` runs the
   other way: `V*_m >= V*_{m'}` for `m <= m'`, so a bound at a larger budget transfers to a smaller one, never the
   reverse. Subset cuts of nodes with at most three regions do not bind for four-region layouts, so `LB_4` is the
   trivial bound. m = 4 is now an optional stage and the paper states it as uncertified.
5. **S1 at the subset LP**: the claim "S1 changes nothing at integer y" is correct (with `Yc = 1` the disaggregated rows
   `X_a <= U_a Yc` are the arc capacities); S1 helps the fractional master proposals of the polish stage only. S2
   family cuts (an ILP at the free-size point bounding every size combination) are valid for the same reason as item
   1 only if the ILP also leaves the sizes free; stated in section 2.3.
6. **Cuts generated at two-site master proposals** (stage G) are ordinary safe Lagrangian / integer L-shaped cuts at
   integer points: valid, but weak elsewhere (at 15 candidates 72 such proposals left 7,060 of 17,340 layouts open),
   which is why they are the polish and not the certificate. No change, but the expectation for the m = 2 certificate
   is now stated honestly in section 2.3: the regional levels prune the periphery, the core is closed only by
   per-pair leaf LPs, and the fixed-layout LP gap (median 0.8 %, max 5 %) against a 0.25 % tolerance means the pairs
   within about 1 % of the incumbent need pricing. A certificate is plausible if the core holds at most about 15
   candidates; otherwise the result is a 0.5-2 % gap with a list of open pairs.

### 7.2 Feasibility: memory, wall time, cost

7. **Pricing is sequential over scenarios today.** `price_layout` loops `for s in range(S)` and its `BestBdStop`
   uses the bounds of the scenarios already solved; `LowerLevelEvaluator.evaluate` is sequential too. The draft's
   "4-8 min wall per layout with 8 workers" presupposed scenario-parallel pricing, which does not exist. Added as a
   first-class implementation item (section 4 item 2, `PricingPool`): threads are enough (Gurobi releases the GIL;
   model build is 4-5 s per cell from the cache rows), with a static `need_s` first pass and a sequential refinement.
   Without it every ILP stage is about 8 x longer and the study does not fit the budget.
8. **LP worker layout.** 12 LPs per layout on 8 workers leave 4 workers idle in the second wave (75 % utilisation);
   the LP stages use 12 workers x 2 threads instead (a 2-thread barrier solve counted as 1.3 x the 3-thread time).
   `r6_o2_siting.py` line 1059 hard-codes `lp_workers x lp_threads + master_threads <= 12` (the laptop); it must be
   replaced by the `run_lanes.sh` thread budget (section 4 item 4).
9. **Unit times are laptop times.** `wall_time.json` of pass 2 shows `lp_workers 3 x 3 + master 2 = 11 of 12` cores:
   the laptop, not the r7i. No comparable solve exists on the server; the draft's x1.1 was a guess. The table now uses
   x1.3 and the `size` dry run measures the ratio (four LP timings and one pricing ILP) before stage D.
10. **Subset LPs were costed like fixed-layout LPs.** With 12-36 open objects and free sizes presolve removes far fewer
    columns than at one or two open sites; the aggregated all-open LP was never solved (the per-bike all-open LP took
    194-257 s against 15-26 s for fixed layouts). The table uses 2 x the two-site time for subset LPs and the dry run
    measures it; a factor above 3 triggers the cut list before stage D.
11. **Transfer columns.** "z columns at or below today's" was wrong: with 60 SC objects, up to 12 hubs and about 11
    neighbours within 2 km per site the count is about 0.45-0.5 M, twice today's 0.25 M (section 1.3). Still fine for
    the LP (threshold raised to 0.6 M); hubs at every site (0.9 M) stay excluded.
12. **The cost table was internally inconsistent and too optimistic.** The draft's "recommended N <= 60, S = 12: about
    32 h, 26 USD" sat below its own N = 60, S = 10 row (34.8 h). With the corrected unit costs (items 9-10) and the
    draft's stage counts (300 + 150 subset nodes at full S, m = 4 in the core, 3 hub settings, 40-addition hub
    screen) the run is 58 h = 47 USD, core 50 h = 40 USD: over the budget. Section 3 is rewritten with the reduced
    plan (200 + 100 subset nodes at `S_LP = 6`, 20 leaves at full S, m = 4 / fleet / MRP optional, hub screen on the
    hub-capable sites, radius validation and the dry run inside stage A, DOT layouts in the out-of-sample set).
13. **Operational costs the draft left out**: the on-demand 4xlarge must be stopped during the Spot run (1.06 USD/h,
    30-35 USD over the run); EBS 5 USD; a 20 % contingency. The Gurobi licence is a WLS file (`bootstrap.sh` step 4),
    portable, needs outbound HTTPS; the Spot request needs the `stop` interruption behaviour and a boot-time
    `run_lanes.sh start`; the security-group allow-list changes with the user's public IPv4.
14. **Memory** (section 1.4): 8 pricing workers each hold a derived library (1.5-5 M `Arc` slotted objects) and a
    Gurobi model, 5-7 GB each; with 12 persistent LPs (2.5-3.5 GB) and two templates the 8xlarge sits at about 90 GB
    of 256 GB and the 4xlarge at about 60 GB with 4 workers of 128 GB. Feasible on both; the 4xlarge is 1.9 x slower
    at the same price per run, so the 8xlarge Spot is right if its price holds at about 0.80 USD/h.

### 7.3 Statistics

15. **CIs with 6 strata x 2 seeds** have 6 df for the stratified variance; the report now gives both the stratified
    and the plain paired t (11 df) and the paper states that neither is narrow (section 2.7).
16. **MRP at `S_rep = 5` cannot be stratified over 6 strata**; `S_rep = 6` (one seed per stratum). The MRP is run at
    m = 1 only: at m = 2 its per-replication bound is the near-trivial level-2 bound, so the "gap" would measure the
    bound's weakness, not the sampling error. The m = 2 statement is the in-sample bound gap plus the out-of-sample
    difference.
17. **The `S_LP = 6` rule** (subset LPs on one seed per stratum, the other six at `L_s`) is valid and is now the
    default of the B&B rather than a cut-list item; the m = 1 enumeration, pricing and every reported value use all
    12 scenarios.

### 7.4 Does the comparison answer the supervisor's question?

18. **Mixed pricing tiers would have biased the comparison (section 2.5, fixed).** The draft priced the rule and DOT
    layouts with the cheaper `open_sites` library (an upper bound on the all-candidates value) and the best layouts
    with `all_candidates`; every paired difference and regret interval would then be tilted against the rules. All
    comparison layouts are priced all-candidates; `open_sites` is for the greedy moves of stage F only.
19. **The hub screen was impossible as written.** Stage J proposed an LP screen of "40 hub additions" while the
    template holds hub objects at hub-capable sites only (the Benders template must contain every object that is ever
    priced). The screen is restricted to the hub-capable sites (<= 12 locations x 2 sizes), and the hub-capable set is
    widened to `depot`, `lot`, `citibike_charging` plus the lattice fallback; the paper states that charging hubs were
    allowed at these locations only (risk 11).
20. **The role question needs a table, not only a sensitivity.** The supervisor asks where swapping and charging
    stations go and whether their roles differ. Section 2.6 now requires a role table per budget (best layout, best
    S-containing layout, best hub-containing layout, with values and bounds), so "all co-located" is reported with the
    price of the alternatives; the hub sensitivity is reduced to the two settings that can change the answer (site
    power cap, hub priced like a site); the grid-connection surcharge is dropped (it only pushes hubs further out).
21. **Out-of-sample set** now includes the DOT all-pilot layout and the capacity-matched DOT proxy (8 layouts), since
    the comparison with the DOT 2024 pilot is the policy-relevant one.
22. **Fleet.** 8 bikes / 40 orders for 60 city-wide candidates will again make at most two sites pay, so the headline
    answers "the best one and two sites in Manhattan". That is acceptable if the paper says so and the fleet
    sensitivity (optional stage K) is run when the budget allows; the number of sites that pays is a function of the
    fleet, not of the candidate count.

### 7.5 Implementation list completeness (section 4, added)

Scenario-parallel pricing (item 7 above); `solve_subset` with free sizes and the box-minimum safe value; the radius
entering `pruning_signature` only when set (else every cache key and `config_md5` changes and the reproduction test
fails); removal of the 12-thread cap; `day_type` plumbing to the generator's weekend profile; per-candidate roles in
`all_candidates_instance`; a held-out evaluator sharing the cache; the Spot / licence / security-group / on-demand-stop
items; the dry-run timings and the toy test for the invalid max-size point.

### 7.6 Final cost estimate

N = 60 (or the merged DOT count, 40-60), S = 12, r7i.8xlarge Spot at about 0.80 USD/h, 24 threads:
**core stages 30 h = 24 USD**; with the optional m = 4, fleet and MRP stages 35 h = 28 USD; plus EBS 5 USD and a 20 %
contingency: **about 34 USD** of the remaining 40. On the current 4xlarge as Spot the same core run is 57 h = 24 USD
(same money, twice the calendar time); on the 4xlarge on-demand 60 USD, not within budget. The two numbers that decide
whether this holds are the subset-LP time and the laptop-to-server factor, both measured in the `size` dry run before
stage D; if they are worse than assumed, the cut list of section 3.3 applies in order (hub settings, m = 2 node
budget, m = 3, ILP limits, written layouts, N = 40, S = 10).


---

## 8. Measured on the server

**Status (2026-10-21, prober): nothing measured on the server yet.** The instance at `AWS_HOST` (the public IP
value in `deploy/aws/aws_env.sh`) did not answer on port 22 (ssh `ConnectTimeout 10` timed out twice, ping lost all
packets), so it is stopped (the idle watchdog) or it came back with another public IP. The cost table of section 3
therefore still uses the laptop unit times with the assumed x1.3 server factor and x2 subset-LP factor; **no row of
section 3.2 is replaced by a measurement yet.**

What is ready to run (one unattended command, about 4-5 h on the r7i.4xlarge, at most 12 solver threads, every step
killed above 58 GB):

* `deploy/aws/r7_probe.sh` (driver) and `ebike_swap_sim/experiments/r7_probe.py` (subcommands `repro`, `radius`,
  `price`, `feas`, `synth`, `summary`). Steps: (1) 15-candidate reproduction: `--bound-from-cuts --no-cover` on a copy
  of `manhattan_pass2` (expected 1,052.995 / 675.740 / 1,115.251 / 676.240, UB 1,052.995 / 700.113 / 1,131.800 /
  699.957), every cache key of `manhattan_pass2/cache/index.jsonl` through the r7 path, the demand hashes, the
  template arc counts 5,835,874 / 5,923,013 / 6,133,784, the three validation layouts as cache hits, and the
  `R7_REPRO` test; (3) approach radius: reachability of the 15 one-site layouts with and without the radius (library
  builds only), then `M09:SC:B3:C2`, `M04:SC:B2:C2|M09:SC:B4:C2` (written; it was only priced written in pass 2) and
  `M08:SC:B3:C2|M09:SC:B3:C2` on seeds 0-2 at radius 14 (9 ILPs, 300 s, 4 x 3 threads) against the cached values;
  (2a / 2b) `r7_siting.py --stage setup` on `manhattan_dot` with the real DOT CSV, radius 14, `--scenarios 6` (one seed
  per stratum; S = 12 does not fit 60 GB at N = 59 with every template kept), N = 40 (`--reduced 40`: the 40
  southernmost ids) and N = 59 (all): template arcs, services, LP columns / rows / nonzeros, z columns, RSS, superset
  LP time per scenario, the four cold-barrier LP timings per scenario at 3 threads, one exact pricing ILP at 300 s
  (the M09 lattice location, `SC:B3:C2`, weekday 40-order scenario), and the reachability of every one-site layout;
  `probe_summary.json` collects everything.
* Upload zips: `ebike_swap_sim/outputs/r7_siting_probe/upload/r7_code.zip` (code, tests, `deploy/aws`, the DOT CSV;
  no `aws_env.sh`, no licence, no key) and `r7_pass2.zip` (`outputs/r6_o2/manhattan_pass2`, 6 MB unpacked).
  `r7_code.zip` was rebuilt from the current tree after the adversarial review of 2026-10-21 (the 09:40 build
  predated the start-state exemption, the hub-capable key component, the factor steps and the representative
  layouts). The driver now refuses to start (exit 2, `STALE CODE` in `probe.log`) when the server copy lacks any of
  these markers; never overwrite `r7_probe.sh` while a driver is executing it (bash reads the script lazily).

The DOT candidate set as the loader reads it today (`data/raw/dot_candidate_sites.csv`, 61 rows): 45 rows in the
band south of 110th St (16 dropped as outside the band), 1 merged with a lattice cell, 14 lattice-only cells, **N = 59**
(shortlist 25, citibike_charging 17, installed 8, depot 5, pilot 3, other 3 in the file); 12 hub-capable (cap 12,
filled in `DOT_HUB_PRIORITY` order since 2026-10-21): the 4 in-band depots D13, D16, D20, D33 and 8 Citi Bike docks;
the docks D10, D21, D26, D37, D43, D55 lost hub capability to the cap. `snap_m` max 97.8 m.

### 8.1 Laptop smoke (not a server measurement; Threads 1, niced, N = 6, one scenario)

`r7_siting.py --stage setup --family manhattan_dot --reduced 6 --scenarios 0 --seeds 0 --approach-radius 14`, 6 DOT /
lattice candidates in the far south (D01-D06), seed 0, 40 orders: template 1,845,391 arcs (3.1 s; 2,063,565 without
the radius, -11 %), 576 services, aggregated scenario LP 219,629 columns / 44,650 rows / 639,690 nonzeros, 14,400 z
columns, superset LP 23.4 s, LP timings at 1 thread: one-site 5.3 s, two-site 10.4 s, one-cell free size (4
locations) 16.7 s, all-open free size (6 locations) 34.2 s, i.e. **subset LP = 1.6 x / 3.3 x the two-site LP**
(the section 3.1 assumption is 2 x; at N = 6 and one thread this is only indicative, but it is above the 3 x trigger
of section 5.2 for the all-open point). The all-open free-size bound equals the superset bound exactly (difference
0.0), as validation 5.1 step 4 requires. Peak RSS 2.1 GB, stage wall 101 s.

### 8.2 Finding that can block production: the approach radius removes feasibility, not only arcs

In the same smoke, **two of the six one-site layouts (`D01:SC:B3:C2`, `D02:SC:B3:C2`) become INFEASIBLE_TERMINAL
under radius 14 and are feasible without it** (`D02` priced 1,452.92 without the radius, 60 s, gap 1.0 %). Cause: bike
1 starts at the northern entry point (44, 56) with q0 = 8 of 24, 51 blocks from the site. Without the radius it rides
straight to the site; with the radius the only way in is a hop through a depot inside the disc ((42, 14), 7 blocks
from `D02`), and the two-hop energy rounding (`energy_rounding = concat`, each hop rounded up) leaves no reachable
real terminal arc. So the radius is not "a restriction of the follower's move arcs with a small value effect": for
one-site layouts far from an entry point it changes V from finite to infinite. Consequences: the m = 1 enumeration
would silently drop such layouts, the comparison layouts (rules, DOT pilot proxy) could become infeasible, and
validation 5.1 step 3 can fail by more than 1 % for a reason a larger radius (20 blocks) does not fix in general.
Candidate fix for the author (one line in `arcs._template_specs`, keeps every equation): exempt the tails that are
bike start nodes or depots from the radius (moves INTO a candidate from a depot / start node always allowed); cost
about 6-8 tails x N targets x H x L arcs per bike, small against the 0.2 M per unrestricted target. The probe's `feas`
steps measure how often this happens on the 15-candidate family and on N = 59 before any decision.
*Adopted 2026-10-21, narrowed the same day* (DECISIONS "R7 decisions of 2026-10-21"): only the start states
`(v0, q0)` of the scenario's bikes are exempt (option `reposition_radius_exempt_states`); on N = 6, seeds 0-7, it
restores every one-site layout's terminal feasibility at 1,860,100 template arcs at seed 0 (tail exemption
1,930,091).
