# Bi-level siting of swapping and charging stations on top of the E2 model (design, 2026-10-14)

Audience: supervisor (sections 1-2, 6-7) and implementer (sections 3-5, appendix). Equation numbers
(1)-(33) refer to `notes/extracted/E2.txt`; code paths are relative to `ebike_swap_sim/`; binding
conventions are `notes/DECISIONS.md`. Nothing in E2 (1)-(33) is changed by this design: the lower
level IS the E2 model with facilities fixed, and the integrated benchmark IS E2 with `y, B, C` free
and scenario-indexed operations, which the implementation already supports (`ilp.py`: `y_j, B_j, C_j`
free when `Facility.y/B/C = None`, budget row (33) via `build_model(budget=...)`).

Evidence that motivates the design (round 3, `notes/E2_formulation_review.md`, `outputs/e8_round3/RESULTS_final.md`):

* On the `usd4h` / `nyc4h` families (6 bikes, 9 spares, 6 chargers, q0 ~ U{4..7} of 12) the battery
  side never binds: moving the three sites from the busiest restaurant cells to the landmark siting
  changes the ILP optimum by <= 0.41 USD (0.063 %) on every seed (E8, n = 10), the free-size ILP buys
  3.5 spares network-wide and saves 1.43 USD (E4u), chargers and grid have zero marginal value.
  Siting cannot be studied on that family: every layout is equally good for the coordinator.
* The same code with tight data shows the knee (round 1: 177 toy units for the first extra spare in the
  stressed state). The review's surviving proposal SC-1 therefore defines an **energy-stressed family**
  (8 bikes, 48 orders, q0 ~ U{2..4}, few spares, 1.4 kW sites, 4 kW grid) on which location, role and
  size can matter. Section 5 adopts it for the siting study.

---

## 1. Problem statement

A planner (the city / NYDOT, or a platform consortium acting as infrastructure owner) chooses, among a
finite set of candidate locations `Lambda` in the study area (Midtown / Chelsea / Flatiron box of
`data_nyc`), which locations to open, with which **role** and **size**:

* role `S` = swap-only site (issues full batteries, cannot charge; must be fed by transfers),
* role `C` = charge-only hub (charges, cannot serve bikes; ships full batteries to swap sites),
* role `SC` = co-located site (both functions, one inventory, site cost counted once, E2 Section 1),
* size = initial spares `B_j` (E2: initial placement, not storage capacity) and chargers `C_j`,

subject to an **investment budget** (33) with the actual investment coefficients `Fhat_j, bhat_j, chat_j`
and, optionally, planner-only requirements (access: every demand zone within distance `D` of an open
swap site; a minimum expected served share `zeta`). Once the facilities are fixed, the daily
**operations** (rider paths, order assignment, swaps, charging, transfers) are run by the E2 model
(5)-(22) with objective (28)-(32) for each demand scenario `s` (a seed of the instance generator).

**Why bi-level.** The two decisions are taken by different actors at different time scales with different
information: infrastructure is chosen once, before demand is known, for a set of scenarios; operations are
re-optimised every day for the realised orders by the coordinator of E2. The planner anticipates the
follower's reaction: the value of a layout is the operating cost the coordinator will achieve on it, not
the cost of some fixed rule. That is a Stackelberg structure: leader = planner (y, roles, B, C), follower =
E2 operations (x, u, n, c, h, z). The follower's problem is the written E2 model with
`fixed_facilities = True` (DECISIONS "Model switches"), exactly as every round-1-3 experiment ran it.

**When it collapses to a single level.** If (i) the leader's objective is the same cost the follower
minimises (allocated setup (27) plus operating cost (28)-(32)), (ii) the scenarios and their probabilities
are known to both, and (iii) the planner-only rows are absent, then the optimistic bi-level problem equals
one integer program: E2 with `y_j, B_j, C_j` free and one copy of the operations variables per scenario,
coupled only through the shared facility variables, i.e. a **two-stage stochastic ILP** (first stage
facilities, second stage operations, sample-average over seeds). This is the exact benchmark of this
design (algorithm A). The bi-level view adds something only when (iii) fails (access / equity /
service-share rows the operator does not price) or when the planner evaluates layouts under an operating
policy that is not the ILP (algorithm E: the baseline policy as the follower). Both cases are kept.

---

## 2. Formulation

### 2.1 Sets and data

* `Lambda` candidate locations `l`, each a distinct grid node `v_l`; roles `R = {S, C, SC}`.
* Facility objects `N = {(l, r) : l in Lambda, r in R}`; `j = (l, r)`; swap-capable set
  `S = {(l, S), (l, SC)}`, charge-capable set `C = {(l, C), (l, SC)}` (E2 notation `S`, `C`, `N = S u C`).
  One facility object per (location, role) is the encoding E2 already supports: facilities are keyed by
  id, several may share a node (CONTRACT section 1), roles are the `swap` / `charge` flags.
* Scenarios `s in Sigma` (generator seeds), probabilities `p_s` (`1/|Sigma|`); scenario data = orders
  `I_s`, bikes' initial levels `q0_ks`; everything else (nodes, routes, candidates, costs) is common.
* Investment coefficients `Fhat_j, bhat_j, chat_j` (USD, undiscounted); allocated costs `F_j, bB_j, bC_j`
  per window (27); budget `Budget`; access radius `D`; service share `zeta`.
* Demand zones `Z` (the NTA codes used by the instance, `meta['zones_used']`) with the candidate set
  within reach `Lambda(z) = {l : dist(v_l, z) <= D}` (Manhattan grid distance from the zone's centre cell,
  or min over the zone's customer nodes).

### 2.2 Upper level (planner)

Variables: `y_j in {0,1}` for `j = (l, r)`, `B_j, C_j in Z_{>=0}`.

```
min_{y,B,C}  Phi(y,B,C) = sum_{j in N} (F_j y_j + bB_j B_j + bC_j C_j)                 (27, allocated)
                        + sum_{s in Sigma} p_s  OPEX_s(y,B,C)                           (expected operations)
s.t.   sum_{r in R} y_{(l,r)} <= 1                                   for all l in Lambda   (one role per location)   [U1]
       sum_{j in N} (Fhat_j y_j + bhat_j B_j + chat_j C_j) <= Budget                                                    [U2] = (33a)
       0 <= B_j <= K_j y_j,  0 <= C_j <= min(Cbar_j, K_j) y_j,  C_j = 0 (j not in C),  C_j >= y_j (j in C \ S)       [U3] = (7)-(8)
       sum_{l in Lambda(z)} (y_{(l,S)} + y_{(l,SC)}) >= 1          for all z in Z        (optional access row)        [U4]
       sum_{s} p_s (1/|I_s|) sum_{i in I_s} (1 - u_is) >= zeta                           (optional expected service share) [U5]
       y binary, B, C integer.
```

`OPEX_s(y,B,C)` is the optimal value of the lower level for scenario `s`. [U5] is the planner's version of
(33b); the per-scenario hard version `sum_i (1 - u_is) >= zeta |I_s|` can instead be imposed inside the
lower level (`build_model(zeta=...)`, round-3 `ilp_zeta90`); both are named explicitly in the outputs.

### 2.3 Lower level (E2 operations, facilities fixed), one per scenario

```
OPEX_s(y,B,C) = min_{x,u,n,c,h,z}  C_elec + C_travel + C_orders + C_reb                 (28)-(32)
                s.t.  (5)-(6)   bike paths and order cover         (9)  terminal certificate  x_ka <= y_j
                      (10)-(11) transfers and departure/arrival    (12)-(14) swaps, balance, joint availability
                      (15)-(18) storage, initial stock n_jL0 = B_j, end targets (rho, R_end_j)
                      (20)-(22) chargers / site power, grid groups, swap positions
                      y, B, C fixed at the leader's values; x, u, h binary; n, c, z integer.
```

`C_setup` (27) is a constant of the lower level and is reported, not optimised, there (DECISIONS
"Objective"). The lower level is exactly `ilp.build_model(inst_layout, lib_layout, fixed_facilities=True)`
on the layout instance of section 4.5.

### 2.4 Assumptions and consequences

* **Optimistic (cooperative) bi-level.** When the lower level has several optimal schedules the one most
  favourable to the leader is assumed. With the shared objective of 2.2 this is harmless: `Phi` depends on
  the follower only through the optimal value `OPEX_s`, which is unique. With planner-only rows ([U4] is on
  `y` only, so still harmless; [U5] depends on `u_is`) the optimistic choice matters and is what the
  integrated model computes; the pessimistic variant would need the worst `u` among alternative optima
  and is out of scope (documented, not implemented).
* **The follower is an ILP**, so the usual single-level reformulations (KKT conditions, strong duality of the
  follower, the LP value-function) do not apply: there is no duality gap-free certificate for an integer
  follower. Consequently every solution method is **enumerative, decomposition-based or heuristic** on the
  leader's variables, with the lower level solved as a black box (Gurobi), and the **integrated single-level
  stochastic ILP (algorithm A)** is the exact reference wherever it solves to a small MIP gap. Integer
  L-shaped / no-good cuts on `y` are a possible later decomposition; they are not required for the
  experiment plan.
* **Infeasible layouts.** A layout is infeasible when some bike has no reachable terminal arc (9) with the
  open swap sites (`arcs.InfeasibleInstanceError`, `strict=True`), or the hard end targets (17)-(18) cannot
  be met. The energy-stressed `q0 ~ U{2..4}` makes the first case real (a bike with `q0 = 2` and
  `q_res = 1` must reach an open swap site within one level, about 2.5-4 km). Enumerative methods assign
  `Phi = +inf` and record `INFEASIBLE_TERMINAL` / `INFEASIBLE_ILP`; the integrated model encodes the
  requirement automatically through `x_ka <= y_j` on the terminal arcs of every candidate swap object.
* **Monotonicity used by the heuristics (stated, not assumed exact).** Opening an additional facility object
  with `B = 0` (or raising `C_j`) enlarges the follower's feasible set (superset of arcs and of the inventory
  rows), so `OPEX_s` cannot increase; raising `B_j` also raises the right-hand side of (18) (`rho sum_j B_j`)
  and the storage use, so under the written targets it is not exactly monotone. The greedy of algorithm C
  uses the monotone direction as a search heuristic and the relaxed-target control (`rho = R_end = 0`,
  `common.relax_end_targets`) as the setting in which the monotone bound is exact.
* **Demand is layout-independent.** Orders, bikes' initial levels and the restaurant ranks of a seed are
  drawn before the facilities (E8 convention, `demand_md5` asserted equal across layouts); bikes start at
  three fixed depot nodes (the three busiest cells of `nyc4h`), not at the open sites, so changing the
  layout never changes the demand side (new builder argument `depots`, section 4.5).

---

## 3. Algorithms to implement

All lower-level solves use `experiments.common.run_ilp_case` conventions: Gurobi 13, `OutputFlag 0`,
`Threads <= 3`, `Seed 0` (`ILP_PARAMS_R3`), `TimeLimit` per solve, `evaluate.check` clean and
`evaluate.cost == objective` (the `ilp.solve` certificate). Every evaluation is cached (3.6) and appended to
`outputs/e9_siting/records.jsonl` (append-only, `results.csv` refreshed per run, `--dry-run / --smoke /
--analyse` modes, `WallBudget` with `SKIPPED_BUDGET`, as in the round-3 scripts).

Notation: a **layout** is `lambda = {(l, r, B, C)}` over open locations; `V(lambda)` is its value
`C_setup(lambda) + sum_s p_s OPEX_s(lambda)` with `OPEX_s = +inf` when infeasible; `inv(lambda)` its
investment `sum (Fhat + bhat B + chat C)`.

### (A) INTEGRATED exact benchmark: one Gurobi model, shared `y, B, C`, scenario copies of operations

```
build_integrated(cands, scenarios, budget, access=None, zeta_exp=None, time_limit, threads):
    m <- gp.Model("E2-siting")
    y, B, C <- facility variables for every object j = (l, r) in N, free (bounds (7)-(8), C_j >= y_j on C\S)
    for l in Lambda: add  sum_r y[(l,r)] <= 1                                    [U1]
    add  sum_j (Fhat_j y_j + bhat_j B_j + chat_j C_j) <= budget                  [U2]
    if access: for z in Z: add sum_{l in Lambda(z)} (y[(l,S)] + y[(l,SC)]) >= 1  [U4]
    for s in scenarios:
        inst_s <- all-candidates instance of scenario s (36 facility objects, services for all C x S pairs)
        lib_s  <- build_arcs(inst_s, **pruning_for(inst_s))          # targets = candidate nodes + depots
        sub_s  <- ILPModel._build(model=m, prefix=f"s{s}", facility_vars=(y, B, C))   # (5)-(22), (28)-(32)
        comps_s <- sub_s.components                                   # LinExpr per cost term
    if zeta_exp: add sum_s p_s (1/|I_s|) sum_i (1 - u_is) >= zeta_exp              [U5]
    m.setObjective( sum_j (F_j y_j + bB_j B_j + bC_j C_j) + sum_s p_s (C_elec+C_travel+C_orders+C_reb)_s )
    m.Params: OutputFlag 0, Threads, TimeLimit, Seed 0
    optional MIP start: the best layout of (C) or (D) with its per-scenario schedules (section 3.6, warm starts)
    optimise; extract (y, B, C) -> layout; per scenario extract_schedule(sub_s), then
    evaluate.check / evaluate.cost on the LAYOUT instance (facilities fixed) -> certified OPEX_s; assert
    sum of certified components == m.ObjVal within 1e-6 (the ilp.solve consistency rule, extended)
    return layout, {obj, bound, gap, status, runtime, per-scenario certified costs}
```

Implementation route: refactor `ilp.ILPModel.__init__` to accept optional `model: gp.Model`,
`prefix: str` and `facility_vars: (y, B, C)`; when given, `_build` adds its variables and rows to the supplied
model under the prefix, uses the shared facility variables instead of creating its own, and leaves the
objective unset (the caller sets it). With the arguments omitted the behaviour is byte-identical to today
(all 136 tests must still pass; `e1_toy.py` must still give 12.5 / 11.2 / 106). Alternative with no
refactor: build each scenario with `build_model` and merge by variable copying -- slower and error-prone;
not recommended.

Size (section 7): per scenario about 1.5-2.5 M arcs at 8 bikes with 12 candidate targets, 36 facility
objects, up to ~8 k services (restricted to pairs within 2 km, otherwise ~8.4 k); 3 scenarios = 5-8 M
binaries. Feasible to build (a few GB) and to run to a bound, not necessarily to optimality within 1 h.
Protocol: `TimeLimit` 1800 s (E9.1, 6 candidates, 2-3 scenarios) and 3600 s (one run per budget on 12
candidates, E9.2 reference), report incumbent, bound and gap; the value of the best heuristic layout is
also a valid upper bound and is injected as MIP start, so the integrated run always returns at least that.

Complexity: one MIP of size `|Sigma| x` (one E2 instance); exponential in the worst case; in practice the
LP bound is tight on the operations part (root-node optimal in 26/30 E2u, 37/40 E8 solves) and the
difficulty is the facility part (DECISIONS plan risk: weak LP relaxation of (7)-(9) with `y` free).

### (B) EXHAUSTIVE upper level for small candidate sets

```
exhaustive(cands, option_grid, budget, scenarios):
    layouts <- [lambda : lambda = one option per location from option_grid, inv(lambda) <= budget,
                at least one swap-capable object open]            # C-only layouts are infeasible by (9)
    sort layouts by inv (cheapest first) or by baseline-policy value (cheap screening, ms each)
    best <- +inf
    for lambda in layouts (parallel workers, Threads 2-3 each, <= 9 threads in total):
        lb <- C_setup(lambda) + sum_s p_s LB_s        # LB_s = OPEX_s(all candidates open, max sizes) (superset relaxation, solved once)
        if lb >= best: record SKIPPED_BOUND; continue
        acc <- C_setup(lambda)
        for s in scenarios (in order):               # scenario-by-scenario pruning
            v_s <- evaluate(lambda, s)               # cached lower-level solve, section 3.6
            acc <- acc + p_s v_s
            if acc + sum_{s' > s} p_s' LB_s' >= best: break (partial, recorded as PRUNED)
        if all scenarios solved: best <- min(best, acc)
    return argmin, table of all evaluated layouts
```

Option grid for E9.1 (validation against (A), where the objective coincides): 6 candidate locations
(the six busiest cells), roles `{closed, S, SC}` with `B in {1, 2}`, `C = 1` for `SC` (and the role `C` with
`C = 1` at most at one location, added as a separate sub-run) -- 4 open options per location (5 with
'closed'); budgets `m = 1` (6 x 4 = 24 layouts) and `m = 2` (`C(6,2) x 4^2 = 240`, plus 120 with one hub),
minus budget-infeasible ones (Appendix B). Count formula:
`|layouts| = sum over subsets of locations of prod_l |options_l|`; with 2 scenarios and ~100 s per solve the
`m = 2` sweep is ~20 h of solver time without pruning and 4-8 h with the bound and the screening, so E9.1
runs `m = 1` fully and `m = 2` with the pruning, and reports coverage (layouts solved / pruned / skipped).
Complexity: `O(prod_l |options_l| x |Sigma|)` lower-level solves worst case.

Agreement test: on every budget where (A) reaches gap 0 and (B) has full coverage, the two optimal values
must coincide to 1e-6 and the layouts must be equivalent (same value; ties are possible). A unit test
(`tests/test_siting.py`) does the same on a toy-sized instance (2 candidates, 2 bikes, 1 scenario) in
seconds.

### (C) GREEDY forward selection + LOCAL SEARCH (default for 10-12 candidates)

```
greedy(cands, budget_levels, scenarios):
    lambda <- {}                                           # nothing open
    frontier <- []                                         # layout after each accepted step
    moves(lambda) = { add (l, r, B, C) for closed l, r in R, (B, C) in size_menu(r) }   # size_menu: S: B in {1,2,3}; C: C in {1,2}; SC: B in {1,2,3} x C in {1,2}
    while True:
        cand_moves <- [mu in moves(lambda) : inv(lambda + mu) <= max(budget_levels)]
        # two-stage screening: price every move with the baseline policy (milliseconds) on all scenarios,
        # keep the top-k_screen (k_screen = 5) by baseline value, evaluate those with the lower-level ILP
        top <- k_screen best of cand_moves by  sum_s p_s BASE_s(lambda + mu)
        gains <- { mu : (V(lambda) - V(lambda + mu)) / inv(mu)  for mu in top }          # per investment dollar
        mu* <- argmax gains;  if V(lambda + mu*) >= V(lambda): break
        lambda <- lambda + mu*;  frontier.append(lambda)
    greedy_layout[m] <- the last frontier element with inv <= budget_m, for every budget level m
    # best-singleton safeguard (standard for budgeted greedy): compare with the best single-location layout
    return { m : local_search(greedy_layout[m], budget_m) }

local_search(lambda, budget):
    improved <- True; passes <- 0
    while improved and passes < 3:
        improved <- False; passes += 1
        for mu in neighbourhood(lambda):                       # 1-swap (close one open l, open one closed l', same role and size),
                                                               # role flip (S <-> SC, C <-> SC, S -> C only if another S stays),
                                                               # size +-1 (B_j or C_j), budget kept
            if inv(lambda ^ mu) > budget: continue
            screen with the baseline policy; evaluate the top-k_screen with the ILP (cached)
            if V(lambda ^ mu) < V(lambda) - 1e-6: lambda <- lambda ^ mu; improved <- True; break   # first improvement
    return lambda
```

Complexity: forward selection `O(m_max x k_screen x |Sigma|)` ILP solves after `O(m_max x |moves|
x |Sigma|)` baseline runs (ms); local search `O(passes x k_screen x |Sigma|)` ILP solves per budget.
With `m_max = 4`, `k_screen = 5`, `|Sigma| = 3`, ~100 s per solve: forward selection <= 4 x 5 x 3 x 100 s
= 1.7 h, local search <= 3 passes x 5 x 3 x 100 s = 1.25 h per budget level, so E9.2 fits in ~8 h with
caching (the frontier is shared across budgets; a move evaluated for one budget is reused by the others).
The value `V` of the greedy's accepted layouts uses the ILP on all `|Sigma|` scenarios; the screening never
decides acceptance, only which moves are priced exactly.

### (D) DECK heuristic (the naive planner of the proposal deck, p.9: "given a station distribution, spin
the simulation, see where stations queue or sit unused, then iterate")

```
deck(cands, budget, scenarios, iters = 3):
    k <- number of sites affordable: max k with k x (Fhat + bhat + chat) <= budget   # one spare + one charger per site minimum
    open <- all candidates as SC with B = 1, C = 1                                     # iteration 0: everything open
    for it in 1..iters:
        for s in scenarios: run the baseline policy (R2.3 rules, ms) on the layout instance of `open`,
            collect swaps_per_facility, wait_before_swap (queue proxy), stockout_slots per site
        demand_l <- sum_s p_s swaps at l (+ queued arrivals at l)
        keep <- the k locations with the largest demand_l (ties by candidate order)
        if it > 1 and some kept site had 0 swaps: replace it by the closed candidate with the most orders
            released within 1 km (demand proxy) -- the deck's 'unused station' rule
        sizes: distribute the remaining budget as spares in proportion to demand_l (bhat 450 each), then
            chargers (chat 400) one per site, within K_j and Cbar_j
        open <- keep with these sizes
    return open   # evaluated afterwards with BOTH the lower-level ILP and the baseline policy (algorithm E)
```

Cost: `iters x |Sigma|` baseline runs (milliseconds) plus the final evaluations; it never calls the ILP
during the search, which is the point of the comparison (E9.4).

### (E) CROSS-EVALUATION of every chosen layout under both operating policies

For each layout chosen by (A)-(D) at each budget and each evaluation seed (5 seeds, section 5): price it
with the lower-level ILP (`OPEX^ILP_s`) and with the baseline policy (`OPEX^BASE_s`, `baseline.run_baseline`
on the same instance and arc library, (9)/(17)/(18) reported not enforced), and tabulate
`V^ILP(lambda)`, `V^BASE(lambda)`, the regret `V^ILP(lambda) - min_lambda' V^ILP(lambda')` and
`V^BASE(lambda) - min_lambda' V^BASE(lambda')` over the chosen layouts. The question answered: does the
layout optimised for the coordinator remain good when the operations are run by the myopic policy, and
vice versa (the deck heuristic optimises for the policy by construction). E8 suggests the answer is
asymmetric (the ILP absorbs siting, the policy does not); the stressed family tests whether that survives
when spares are scarce.

### 3.6 Caching, warm starts, parallelism

Cache key of one lower-level evaluation (md5 of the canonical JSON):

```
key = (family, scenario_seed, demand_md5(inst, include_bike_nodes=True, include_facilities=False),
       sorted tuple of (location_id, role, B, C) over open objects,
       transfer timetable spec (every, first, U, f, vreb, max_pair_km) or 'none',
       pruning signature (lib.options after pruning_for), model switches (rho, R_end per role, q_res,
       zeta, no_transfers, fixed_facilities = True), cost variant, Gurobi protocol (TimeLimit, Threads,
       Seed, params), package version (git commit of ebike_swap_sim))
value = {status, obj, bound, gap, runtime_s, n_arcs, n_binaries, metrics (served_share, n_late,
         swaps_per_facility, stockout_slots, kwh_purchased, transfers_used), schedule path (JSON),
         mip_start_variant, families}
```

A cached row is reused when `common.reusable_ilp_row(status, gap)` holds (OPTIMAL or gap <= 1 %);
otherwise the solve is repeated with the remaining wall budget. Baseline evaluations use the same key with
`policy = baseline` (no Gurobi fields). The cache is `outputs/e9_siting/cache/<md5>.json` plus the
append-only `records.jsonl`.

Warm starts: (i) when a move only adds a facility object or raises `C_j`, the previous layout's ILP
schedule is feasible on the new layout (superset of arcs under `PRUNING_NYC` targets = open facilities +
depots) -- re-identify its arcs through `lib.find(k, kind, src, order=, fac=, dst=)` (the mechanism of
`experiments.e4u_sizing_usd.chain_start`) and inject it as MIP start; (ii) otherwise inject the baseline
policy schedule through `common.feasible_mip_start` (falls back over `baseline_round1` / `baseline_reserve`
when the default violates (18)); (iii) the integrated model receives the best heuristic layout and its
per-scenario schedules. Gurobi certifies every start by a fixed solve (`verify_start=True`).

Parallelism: a process pool of 2-3 workers with `Threads = 3 / 2` each (<= 9 threads on the 12-core
machine, leaving room for the concurrent paper workflow); the pool evaluates (layout, scenario) pairs;
one Gurobi environment per worker; ~1.5-2.5 GB RAM per 8-bike model.

---

## 4. Candidate sites (Midtown / Chelsea / Flatiron box of `data_nyc.DEFAULT_BOX`)

Grid: 34 x 35 blocks of 150 m, Manhattan azimuth 29 deg, `StudyBox.snap(lat, lon)` -> grid node `(i, j)`;
the geometry caveat of R2.4 (synthetic road network, elevation and signals) applies to every output.
Values below were computed with the package on 2026-10-14 (`restaurants_in_box`: 4,607 DOHMH rows;
`busiest_restaurant_cells(df, 6, min_sep_blocks=4)`; ACS 2020-24 literature zone weights,
`NYCDestinationSampler.zone_totals()`), and are to be recomputed by the candidate builder, not hard-coded.

| id | source | label | lat, lon (WGS84) | grid node | note |
|---|---|---|---|---|---|
| L01 | (i) busiest cell 1 | W 34th / 7th-8th Ave (Penn Station area) | 40.75126, -73.99223 | (13, 14) | 92 restaurants; `nyc4h` site S1; depot 1 |
| L02 | (i) busiest cell 2 | W 29th-30th / 6th Ave (NoMad) | 40.74745, -73.98687 | (17, 13) | 72; `nyc4h` S2; depot 2 |
| L03 | (i) busiest cell 3 | W 40th / 6th Ave (Bryant Park south) | 40.75455, -73.98169 | (17, 19) | 55; `nyc4h` S3; depot 3 |
| L04 | (i) busiest cell 4 | E 42nd-43rd / Lexington (Grand Central east) | 40.75494, -73.97530 | (20, 21) | 45 |
| L05 | (i) busiest cell 5 | W 46th-47th / 6th Ave (Rockefeller south) | 40.75927, -73.97824 | (17, 23) | 42 |
| L06 | (i) busiest cell 6 | W 55th-56th / 8th-9th Ave | 40.76728, -73.98257 | (12, 27) | 41 |
| L07 | (ii) landmark | 8th Ave / W 34th St | 40.75270, -73.99370 | (12, 15) | E8 `grid` site; 1 block from L01, distinct node |
| L08 | (ii) landmark | Union Square | 40.73590, -73.99110 | (19, 4) | E8 `grid` site; southern edge of the box |
| L09 | (ii) landmark | Grand Central Terminal | 40.75270, -73.97720 | (20, 19) | E8 `grid` site; 2 blocks from L04 |
| -- | (ii) landmark | Penn Station (7th Ave / W 32nd) | 40.75050, -73.99340 | (13, 13) | 1 block from L01: merged into L01 (label kept) |
| L10 | (iii) zone centre | Murray Hill-Kips Bay (MN0603, 20.3 % of demand mass) | 40.74470, -73.97667 | (23, 14) | east of all restaurant hubs |
| L11 | (iii) zone centre | Hell's Kitchen (MN0402, 20.0 %) | 40.76333, -73.99156 | (9, 22) | west |
| L12 | (iii) zone centre | Chelsea-Hudson Yards (MN0401, 17.8 %) | 40.74968, -73.99949 | (10, 11) | south-west |

Rules: (a) candidates are deduplicated to **distinct grid nodes**; (b) in addition, two candidates closer
than 2 blocks (300 m) are merged into the one with more restaurants (Penn Station -> L01), the merged label
is kept in `meta['candidate_labels']`; L07 and L01 are 1 block apart on different axes (Manhattan distance
2) and are both kept so that the 'landmark vs busiest cell' question of E8 remains answerable; (c) zone
centre = the sampler-support node of the zone nearest to the mean of the zone's in-box nodes (zone weights
are per-zone densities, so every node of a zone has the same weight; the centre is the geometric one);
(d) every candidate can take role `S`, `C` or `SC` (three facility objects per location, exclusivity [U1]);
(e) `C`-role objects at a location need transfer services: shuttles between every open charge-capable
object and every open swap-capable object at a different location, departures every 6 slots from boundary
2 (`l = 2, 8, ..., 44`), duration `ceil((route minutes + 10 min handling) / 5 min)`, `U_e = 6`,
`f_e = 20 USD`, `v_reb = 1 USD` (the E3u / `generator.DEFAULT_SERVICES_SPEC` timetable with the `usd_sunk`
service prices), both directions; optional `max_pair_km = 2.0` to limit the service count in the
integrated model (recorded in the cache key).

Role parameters (per facility object; `usd_sunk`, 4 h window):

| role | swap | charge | K_j | Cbar_j | M_j | sigma_j | P_j kW | R_end_j | F_j USD | Fhat_j USD |
|---|---|---|---|---|---|---|---|---|---|---|
| S | yes | no | 8 | 0 | 1 | 1 | 0 | 1 (written) / 0 (control, SC-4) | 12.03 | 50,000 |
| C | no | yes | 8 | 4 | - | - | 1.4 | 0 | 29.19 (F_hub) | 50,000 |
| SC | yes | yes | 8 | 4 | 1 | 1 | 1.4 | 1 | 12.03 | 50,000 |

`bB = 0.332`, `bC = 0.082` USD per window; `bhat = 450` per spare, `chat = 400` per charger (R2.1,
`notes/data/cost_calibration_usd.json`). All open charge-capable objects share one grid group
`sites` with `P_grid = 4 kW` flat (section 5); `p_ch = 0.667 kW`, so a site charges at most 2 batteries
at a time (`P_j = 1.4`) and the group at most 6.

### 4.5 Builders (new module `ebike_swap_sim/siting.py`, no change to `arcs.py` / `ilp.py` semantics)

* `candidate_set(box, n_busiest=6, landmarks=LANDMARKS, n_zones=3, min_sep_blocks=2) -> list[Candidate]`
  (`id, label, source, lat, lon, node`), deterministic, written to `outputs/e9_siting/candidates.json`
  and drawn on the map.
* `make_base_instance(seed, family='nyc4h_stress', candidates)`: `data_nyc.make_nyc_instance(...)` with
  `site_latlon = [all candidate coordinates]` (so the node set and the route library contain every
  candidate) and the new argument `depots = [L01, L02, L03 nodes]` (bikes start round-robin at the three
  `nyc4h` busiest cells; default `None` = today's behaviour `depots = site_nodes`, so `nyc4h` is unchanged).
  The returned instance has NO facilities and NO services yet (`facilities_spec['none'] = True` or a
  post-processing step that strips them) and carries `meta['candidates']`.
* `layout_instance(base, layout, roles_spec, services_spec) -> Instance`: adds one `Facility` per open
  `(l, r, B, C)` with `y = 1, B, C` fixed (`fixed_facilities = True`), the services of rule (e), `P_grid`,
  `inst.reindex()`, `validate()`; `meta['layout']`, `meta['layout_key']`. `common.pruning_for` then yields
  `PRUNING_NYC` with the layout's facility nodes + depots as move targets.
* `all_candidates_instance(base, roles_spec, services_spec) -> Instance`: the 36 role objects with
  `y = B = C = None` (free) for the integrated model (A) and for the superset lower bound of (B).
* `Layout` dataclass: `open: tuple[(l, r, B, C)]`, `inv()`, `setup_cost()`, `key()`, `to_json()`;
  `LayoutSpace(cands, roles, size_menu, budget)` with `enumerate()`, `moves(layout)`, `neighbourhood(layout)`.
* `evaluate_layout(base_s, layout, policy='ilp'|'baseline', cache, budget_guard) -> record`.
* `experiments/e9_siting.py` with sub-commands `validate` (E9.1), `pareto` (E9.2), `roles` (E9.3), `deck`
  (E9.4), `cross` (E9.5), `access` (E9.6), `--analyse`; outputs under `outputs/e9_siting/<sub>/`.
* Tests (`tests/test_siting.py`): candidate dedup rule; layout key canonical and JSON round trip;
  `layout_instance` validates and its `demand_md5(include_facilities=False)` equals the base's; exclusivity
  and budget rows of the integrated model on a 2-candidate toy; integrated == exhaustive on that toy;
  superset monotonicity of `OPEX` under relaxed targets on the toy; `nyc4h` byte-identical with
  `depots=None`.

---

## 5. Instance family for siting: `nyc4h_stress` (energy-stressed `nyc4h`)

Registered in `experiments/common.FAMILIES` as `builder: 'nyc'`, `n_bikes 8`, `window_h 4.0`
(17:00-21:00, `H = 48`, `Delta = 5 min`), `orders_per_bike_hour 1.5` -> 48 orders, `L = 12`
(`eps = 50 Wh`, 600 Wh pack), `demand_spec = {'init_frac': (2/12, 4/12)}` -> `q0 ~ U{2..4}` (assert in a
test that `q0 in {2, 3, 4}` on 20 seeds), `facilities_spec = {'B': 1, 'C': 1, 'P_kw': 1.4, 'Cbar': 4,
'grid_sites_kw': 4.0, 'grid_sites_peak_kw': 4.0}` (so the default sized layout has `sum_j B_j = 3 < |K| =
8`), `cost_variant 'usd_sunk'`, `q_res = 1`, `rho = 0.5`, `R_end_j = 1` at swap-capable objects (written)
with the relaxed control `rho = R_end = 0` as in every round (`common.relax_end_targets`), and the SC-4
sensitivity `R_end_j = 0` at `S`-role objects.

Justification (E2_formulation_review SC-1 / L4-P6, the only proposal kept by both verdicts): with
`q0 ~ U{4..7}`, 9 spares and 6 chargers for 6 bikes the battery subsystem is slack -- E4u marginal value
of a spare +0.35 USD, of a charger 0.000, relaxed ILP buys 0 kWh in 20/20 E8 runs, and the E8 siting
delta is 0.41 USD -- so any siting result on `nyc4h` would be a statement about ties. With 8 bikes
starting at 2-4 levels (100-200 Wh, 1-2 deliveries), 1-3 spares network-wide in the budget-1 layouts, a
0.667 kW charge rate capped at 2 per site and 6 per group, swaps must be rationed and timed, and the
location of the stock relative to the restaurant hubs and the depots decides which orders can be served:
this is the regime in which round 1 showed a cost knee (177 toy units for the first extra spare). The
review's success criteria carry over: at least one of (14), (20), (21) binds, the marginal value of a spare
exceeds `bB = 0.332 USD`, the relaxed ILP purchases kWh, and the siting delta exceeds 0.41 USD.

Scenarios: seeds `0, 1, 2` with `p_s = 1/3` for every search (A-D); seeds `0-4` with `p_s = 1/5` for the
final evaluation of the chosen layouts (E9.5), so that seeds 3-4 are out-of-sample for the search and the
in-sample / out-of-sample difference is reported. `demand_md5(inst, include_bike_nodes=True,
include_facilities=False)` is asserted identical across layouts of a seed.

Costs: `usd_sunk` (kappa 0.12, w 18, v 36, P 30, pi 0.32, f 20, v_reb 1); window-allocated `F_j 12.03`
(site), `F_hub 29.19`, `bB 0.332`, `bC 0.082`; investment `Fhat 50,000`, `bhat 450`, `chat 400`; budgets
`Budget_m = m x (Fhat + 3 bhat + 2 chat) = m x 52,150 USD`, `m in {1, 2, 3, 4}` = 52,150 / 104,300 /
156,450 / 208,600 USD. Reading: `Fhat` dominates, so budget `m` buys at most `m` locations and leaves
`2,150 m` USD for spares and chargers beyond the first location's `3 bhat + 2 chat`; at `m = 3` and `4` the
planner can instead open fewer locations and stock them (up to `K_j = 8` spares), which is exactly the
sites-versus-spares trade-off the Pareto curve of E9.2 displays.

Size and timing expectations (section 7): `nyc4h` 8 bikes = 1.55 M arcs under `PRUNING_NYC` with 3
targets (`outputs/r2_probe/nyc4h_arcs.jsonl`); a layout with 1-4 open locations has 1-4 targets, so
1.3-1.7 M arcs; E8 6-bike solves took 46 s mean / 64 s max at 0.55 M binaries, the `usd4h` 8-bike probes
137-171 s at 1.7-1.8 M, hence the 40-150 s per lower-level solve assumed throughout.

---

## 6. Experiment plan (E9.x), `outputs/e9_siting/`

Common protocol: Gurobi `OutputFlag 0`, `Threads 3` (2 when two workers run), `Seed 0`, `TimeLimit 300 s`
per lower-level solve (600 s for layouts with charge-only hubs, the E3u rule), integrated model 1800 /
3600 s; wall budgets per sub-command; `SKIPPED_BUDGET` / `SKIPPED_BOUND` / `PRUNED` recorded; every row
carries the cache key, `demand_md5`, the geometry caveat and `source`.

| id | question | design | metrics / deliverable |
|---|---|---|---|
| **E9.1 validation** | Do the integrated stochastic ILP (A) and the exhaustive bi-level (B) agree when the objectives coincide? | 6 candidates (L01-L06), roles `{S, SC}` + one optional `C`, `B in {1,2}`, `C = 1`, budgets `m = 1, 2`, scenarios seeds 0-1 (`p = 1/2`), written targets; (A) at 1800 s with the (B) optimum as MIP start; (B) with superset bound and scenario pruning; wall 8 h | equality of optimal values to 1e-6 where (A) has gap 0 and (B) full coverage; otherwise (B) value within (A)'s [bound, incumbent]; table of all layouts; lower-level solve counts / time; coverage |
| **E9.2 budget sweep (Pareto)** | Where, which role, which size per budget; investment vs expected operating cost | 12 candidates, greedy + local search (C) at `m = 1..4` on seeds 0-2; one integrated run (A) per budget at 3600 s warm-started from (C) for the bound; wall 10 h | Pareto curve `inv(lambda)` vs `sum_s p_s OPEX_s` (and vs `V`); chosen sites / roles / sizes per budget (table + map); served share, lateness, swaps per site, stock-out slots, kWh, transfers; distance from each demand zone / customer node to the nearest open swap site; MIP gap of (A) per budget |
| **E9.3 role separation** | Is a charge-only hub ever chosen; what does forcing co-location cost? | rerun (C) at `m = 2, 3` with roles restricted to `{SC}` (all co-located) vs the full set `{S, C, SC}` (hubs allowed, transfers on) vs `{S, SC}` (no hubs); seeds 0-2; wall 6 h | `V` per role set; number of hubs / swap-only sites chosen; transfers used and `C_reb`; difference decomposed by cost component; the E3u finding (hub = +F_hub, transfers worth 0-9 USD) re-tested under stress |
| **E9.4 deck heuristic vs bi-level** | How far is the proposal's spin-and-adjust planner from the bi-level optimum? | (D) with 3 iterations at `m = 1..4`, seeds 0-2; compared with (C) and the (A) bound | bar chart `V` deck vs greedy+LS vs integrated incumbent / bound per budget; overlap of chosen sites; regret in USD and % |
| **E9.5 cross-evaluation** | Is the siting robust to the operating policy? | layouts of (A)/(C)/(D) per budget evaluated under the ILP and under the baseline policy on seeds 0-4 (3 in-sample + 2 out-of-sample) | `V^ILP`, `V^BASE`, regret matrices (layout x policy), in- vs out-of-sample gap, served share and lateness under each policy; the gap (baseline - ILP)/baseline per layout as in E8 |
| **E9.6 access constraint** | What does the planner-only access row cost the operator? | (C) at `m = 2, 3` with [U4] for `D in {8, 12}` blocks (1.2 / 1.8 km) over the NTA zones used; optional expected-share row [U5] `zeta = 0.85`; seeds 0-2 | `V` with / without [U4]; zones covered; max and mean zone-to-site distance; service share; which locations enter only because of the access row |

Figures (matplotlib Agg, the E8 map code reused): `map_candidates.png` (box, zone-weight heat, DOHMH
restaurants, 12 candidates with ids, depots) and `map_budget_m.png` per budget (chosen sites coloured by
role, sized by `B_j`, with the seed-0 ILP bike paths); `pareto.png` (investment vs expected operating cost,
one marker per budget and method, integrated bound as a dashed line); `deck_vs_bilevel.png` (grouped bars
per budget: deck / greedy+LS / integrated incumbent / integrated bound); `cross_eval.png` (heat map layout
x policy); `roles.png` (E9.3 stacked cost components). Tables: `candidates.csv`, `layouts_<sub>.csv`,
`pareto.csv`, `cross_eval.csv`, `solve_stats.csv` (counts, mean / max runtime, cache hits), and one
`RESULTS.md` per sub-command plus `RESULTS_final.md` with the coverage statement.

Reporting conventions: gap = (baseline - ILP)/baseline as in rounds 1-3; 95 % t-intervals over seeds
when n >= 3; every ILP total on the semi-real family is an upper bound on the written optimum because
`PRUNING_NYC` restricts the ILP only (state it under every table, as E8 does); the relaxed-target control
is run for the final layouts (E9.5) so that the recovery targets' price is reported separately.

---

## 7. Risks and compute budget

| risk | effect | mitigation / honest reporting |
|---|---|---|
| Lower-level solve time 40-150 s at 8 bikes (1.3-1.8 M arcs), occasionally 300 s TIME_LIMIT with 1-2 % gap (E3u pattern with hubs) | the search is solve-bound: ~30-60 ILP solves per hour per worker | caching with the 1 % reuse rule; baseline screening before ILP pricing; scenario-by-scenario pruning with the superset bound; 2-3 workers x Threads 2-3; wall budget per sub-command with `SKIPPED_BUDGET`; **coverage reported in every RESULTS.md** (layouts solved / pruned / skipped, cells at TIME_LIMIT with their gaps) |
| Integrated model (A) at 12 candidates x 3 scenarios = 5-8 M binaries | may not close the gap within 1 h; memory 4-8 GB | run (A) at 6 candidates for validation (E9.1); at 12 candidates use it only for the bound, warm-started with the best heuristic layout (so the incumbent is never worse than (C)); restrict services to pairs within 2 km; report bound and gap, never 'optimal' without gap 0 |
| Infeasible layouts (terminal certificate (9) with `q0 = 2`, `q_res = 1`; written end targets at spare-starved sites) | holes in the enumeration; greedy may start from an infeasible empty layout | `V = +inf` with the reason recorded; the greedy's first step is the best feasible singleton; SC-4 sensitivity (`R_end = 0` at S-role sites) and the relaxed control reported; count of infeasible layouts per budget in the tables |
| Few scenarios (3) for the search: layout over-fitted to the seeds | optimistic in-sample `V` | 5-seed out-of-sample evaluation in E9.5, in-/out-of-sample difference reported; if it exceeds the between-method differences, increase to 5 search seeds for E9.2 only (doubles its wall time) |
| Multiple lower-level optima (optimistic assumption) | matters only with [U5] | `V` depends on the optimal value only; [U5] runs are labelled 'optimistic'; no pessimistic claim |
| Stress regime dominated by unserved-order penalties (`P = 30` per order) | the Pareto curve may be a service-share curve in disguise | report served share, lateness and the cost decomposition next to `V`; add the `zeta = 0.85` hard row as a sensitivity (round-3 machinery) |
| `PRUNING_NYC` restricts repositioning for the ILP only; arc library differs per layout (targets = open facilities) | ILP totals are upper bounds; layouts with more open sites get more move arcs | stated under every table (E8 convention); the lossless `targets = default` probe on one budget-2 layout as a check if time allows |
| Hub cost convention (`F_hub` 29.19 for a K 8 / Cbar 4 hub vs the E3u hub of K 30 / Cbar 20) | hub role priced generously or not | documented as data; sensitivity `F_hub in {12.03, 29.19}` on E9.3 if hubs are never chosen |
| Candidate coordinates and zone centres depend on the data files present (ACS vs GeoDa fallback) | different candidate set on another machine | the builder recomputes and writes `candidates.json`; `meta['zone_weights_source']` recorded; the table of section 4 is the 2026-10-14 ACS result |
| Concurrent paper workflow (light CPU) and the 12-core machine | contention | <= 9 solver threads in total, one `gp.Env` per worker, `nice` the pool; memory check before starting a third worker |

Compute budget (solver wall time, sequential-equivalent at ~100 s per solve, before parallelism):
E9.1 ~ 6-8 h (m = 1 full, m = 2 with pruning, + (A) 2 x 0.5 h); E9.2 ~ 8-10 h ((C) 4 budgets with cache
sharing + (A) 4 x 1 h); E9.3 ~ 4-6 h; E9.4 ~ 0.5 h (ILP only for the final evaluation of 4 layouts x 3
seeds); E9.5 ~ 3 h (<= 12 layouts x 5 seeds x ILP, baseline in ms); E9.6 ~ 4 h. Total ~ 30 h sequential,
~ 12-15 h with 2-3 workers, spread over 3-4 nights with the round-3 append / resume protocol. Order of
execution: E9.1 (validation first; if (A) and (B) disagree, stop and debug), then E9.2 and E9.4, then
E9.5, E9.3, E9.6.

---

## Appendix A. Implementation checklist

1. `data_nyc.make_nyc_instance(..., depots=None)` (additive; `nyc4h` byte-identical, test).
2. `common.FAMILIES['nyc4h_stress']` as in section 5; `tests/test_experiments.py` q0 range test.
3. `siting.py`: `Candidate`, `candidate_set`, `Layout`, `LayoutSpace`, `make_base_instance`,
   `layout_instance`, `all_candidates_instance`, `services_for`, `evaluate_layout` + cache, `deck_heuristic`,
   `greedy_local_search`, `exhaustive`.
4. `ilp.ILPModel` refactor for `model / prefix / facility_vars` (default path unchanged; 136 tests green,
   E1 12.5 / 11.2 / 106); `siting.IntegratedModel` with [U1], [U2], [U4], [U5], expected objective,
   per-scenario certification by `evaluate.check` / `evaluate.cost`.
5. `experiments/e9_siting.py` sub-commands, `--dry-run / --smoke / --analyse`, `WallBudget`, figures,
   `RESULTS.md` writers; `tests/test_siting.py` (toy agreement of (A) and (B); layout round trips; dedup).
6. English only in every file (code, outputs, reports); plain-language wrap-up for the user in chat after
   each run.

## Appendix B. Enumeration counts for the option grids used

Per-location options `O = 1 + |S sizes| + |C sizes| + |SC sizes|`. E9.1 grid: `S: B in {1,2}`, `SC: B in
{1,2}, C = 1`, `C`-role separately: `O = 1 + 2 + 2 = 5` (+1 with `C`); 6 locations: `m = 1`: 6 x 4 = 24
layouts (+6 with a hub, all infeasible alone); `m = 2`: 15 x 4^2 = 240 (+ 6 x 5 x 4 = 120 with one hub)
minus budget-infeasible. Full menu of (C) (`S: B in {1,2,3}`, `C: C in {1,2}`, `SC: 3 x 2`): `O = 12`, 12
locations, `m = 4`: `sum_{k<=4} C(12,k) 11^k` ~ 7.6 M layouts -- the reason (B) is for small sets only and
(C) is the default.


---

## Addendum (2026-10-14, after the first launch): relaunch conventions

The first launch on `nyc4h_stress` (8 bikes) produced degenerate results (`outputs/e9_bilevel/_first_attempt/README.md`;
`notes/DECISIONS.md` "E9 relaunch decisions"). Binding changes for the relaunch, all in `sites_nyc.py` /
`bilevel.py` / `experiments/e9_bilevel_siting.py`:

* **Family `nyc4h_stress2`** (section 5 replaced for the runs): 6 bikes / 36 orders / `q0 ~ U{3..6}`, `P_j = 2.8 kW`,
  4 kW group, menu `S: B in {1,2,3}`, `SC: B in {1,2,3} x C in {1,2}`, hubs `C in {2,4}`; swap-only sites only next
  to a C / SC object (`layout_admissible`, also rows of the integrated model). A single SC site serves >= 70 %.
* **Algorithm (C)**: start = best singleton by V (per-role baseline screen, exhaustive singletons as fallback);
  moves infeasible or serving < 50 % are discarded (`LOW_SERVICE`); `SKIPPED_BUDGET` stops the search and is
  reported as `wall budget exhausted`; exceptions are `ERROR` rows with the message; the access row [U4] is a
  repair-and-report rule in the greedy (uncovered zones listed, never enforced on intermediate layouts).
* **Libraries**: `siting_pruning(targets='open_sites')` (open facility nodes + depots, E8 convention) for the
  search algorithms (C)-(E); `--validate` keeps `all_candidates` so that (A) and (B) share the same per-layout
  libraries (section 3, algorithm (B) statement unchanged there). Cache version `e9-2`.
