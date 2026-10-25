# O2 -- certified siting bound: L-shaped Benders with exact incumbent pricing (design, 2026-10-18)

Plan item O2 (`notes/reading_to_model.md` sections 4.3 and 6, step 3). Audience: implementer (all sections) and
supervisor (sections 0, 6-8). Equation numbers refer to `notes/extracted/E2.txt`; code paths are relative to
`ebike_swap_sim/`. **No equation of E2 (1)-(33) changes.** The lower level stays the unchanged operations model.
Its LP relaxation is used for bounds only, and every incumbent is priced by the unchanged operations ILP through
`bilevel.LowerLevelEvaluator`.

Goal: for every budget `m = 1..4` and for both the relaxed-target (`rho = R_end = 0`) and the written-target lower
level:

1. a valid lower bound `LB_m <= V*_m` that is tighter than the existing `superset_bound`;
2. a search that covers every candidate, role and menu size (no truncated screen), with incumbents priced exactly;
3. the gap `(UB_m - LB_m) / UB_m`.

Why the current tools are not enough:

* Greedy search (round 5, `outputs/r5_x6_manhattan/RESULTS_final.md`): 4 layouts priced, M08 never screened,
  nothing found at m = 1.
* Integrated model (A): no usable bound at 12 candidates (`outputs/e9_bilevel/RESULTS_E9.md` 3.3, 5.6).
* Superset LP bound: 2.1 % below the Midtown validation optimum, valid for every layout but not tied to any
  layout.

Pre-check already done (2026-10-18, toy instance `sites_nyc.toy_base_instance`, Threads 1, scratch prototype, not
committed):

* the per-scenario subproblem of section 2 was built with `ilp.build_submodel(aggregate=True)` on free copy
  variables with fixing rows;
* on 117 toy layouts x 2 scenarios, every cut satisfied `cut_xhat(x) <= Q_LP(x)` for every pair (27,378 checks,
  0 violations), under written and relaxed targets;
* the elastic slacks of section 2.4 priced the 12 IP-infeasible toy layouts at 5,200-20,400 (versus about 100
  for feasible layouts);
* the LP gap at fixed layouts, `(Q_IP - Q_LP) / Q_IP`, had median 0.38 % and maximum 26 % with written targets
  (41 % of cells exact), and median 0 and maximum 23 % with relaxed targets (84 % exact).

So the LP bound alone cannot certify in the worst case. The integer cuts of section 3.4 are part of the default
design, not an option.

---

## Critique and corrections (mathematical review, 2026-10-18)

Review of every step against `ilp.py` (`ILPModel._build`, `build_submodel`), `aggregate.py`, `bilevel.py`
(`LowerLevelEvaluator`, `superset_bound`, `integrated_stochastic_ilp`), `sites_nyc.py` (`layout_instance`,
`all_candidates_instance`, `subset_library`, `layout_admissible`, `SIZE_MENUS`) and `experiments/common.py`
(`relax_end_targets`, `ILP_PARAMS_R3`, `reusable_ilp_row`). No E2 equation is touched by any correction: the changes
are in the bound LP (relaxation columns), in how cuts are computed from Gurobi output, and in how evaluator rows
are read. The affected sections below have been rewritten; each item names them.

### Confirmed (no change needed)

* **Coupling table (1.2).** Rows, senses, coefficients and dual signs match `ILPModel._build`: (9) aggregated
  `sum X - U_kj y_j <= 0` with `U_kj = agg.term_ub[(c, j)]`; (10) `svc_yo`, `svc_yd`; (15) per `t = 0..H`; (16)
  `n_jL0 - B_j = 0`; (17) only for swap objects (`if f.swap`, also when `R_end = 0`, so the target switch by
  `chgCoeff` works); (18) over all objects including hubs (hub menu has `B = 0`); (20) only for `j in C`; (22) only
  for `j in S` and slots with an occupying swap arc. The explicit `beta` formula of 2.2 has the right signs.
* **No row or bound of the template sub-model depends on the first-stage values.** Rows are created per role
  object (role flags `swap`/`charge`, fixed per object id), per template arc and per template service (all
  charge/swap pairs at different locations); the bounds `K`, `min(Cbar, K)`, `U_e`, `U_a` are constants. The
  sub-model omits (7)-(8) and (33); the menu encoding supplies (7)-(8) at integer points and on the menu hull
  (`B = sum B_o w <= K y`, `c_min y <= C <= c_max y`). Facility data (`K, Cbar, M, P_kw, R_end`, prices, grid
  group, timetable) depend on the role only, not on `B, C`, so they are identical in the template and in every
  layout instance. Hence the template LP is a fixed-recourse LP whose first-stage values enter only right-hand
  sides, and dual cuts are valid for every `x`, not only at `xhat` (subject to item C1 on tolerances).
* **Aggregated duals bound the per-bike integer problem.** At every integer layout, a per-bike schedule on
  `subset_library(template, layout)` maps into the template aggregated LP (its arcs are template arcs, none is
  dropped by the aggregation pruning because it carries flow, and `U_a`, `term_ub` count at least the bikes that
  use the arc), so `Qt_template_agg(x) <= Q^LP_perbike(x) <= Q^IP(x)`. The aggregated LP is weaker than the
  per-bike LP only at fractional `y`, which affects strength, not validity. The pricing ILP's `ObjBound` (aggregated
  or per-bike) bounds the same per-bike optimum (O1 equivalence).
* **Superset bound** (`superset_bound('lp')`): per-bike LP with all objects open, free sizes, relaxed targets, on
  the template; valid for every layout and both targets. Clipping at 0 is valid because every objective
  coefficient is nonnegative (assert this once; see C13).
* **Cover rows (2.4 b), terminal combinatorial cut (2.4 c), relaxed-below-written.** Valid: `subset_library` only
  removes arcs and its reachability shrinks with the open swap-object set; terminal arcs depend only on the node of
  `j` (`gbar(v, j)`), not on sizes, hubs or targets; the written rows (17)-(18) are a restriction of the relaxed
  ones (`R_end y >= 0`, `rho sum B >= 0`).
* **Admissibility.** The master rows reproduce `layout_admissible` (`require_swap`, `s_needs_charge` = any open C
  or SC object anywhere), [U1], [U2] with `Layout.investment` and the family menu (`option_grid`).
* **Pricing convention vs round 5.** With `reposition='all_candidates'` the evaluator prices every layout on
  `subset_library(template_s, layout_s)`, which is exactly the library of the cuts; `template_pair` and
  `layout_pair` coincide in this mode. Round 5 priced on `open_sites` libraries (same pruning, reposition targets
  restricted to open nodes + depots), which are sub-libraries of the all-candidates library of the same layout.
  So an `open_sites` incumbent is feasible under the all-candidates convention and its value is a valid upper
  bound on `V*` (under the prices it was computed with), but an `open_sites` `ObjBound` is NOT a lower bound on the
  all-candidates `OPEX_s` and must never enter `LBIP`. Under the round-6 prices all layouts are re-priced anyway.

### Corrections

**C1 (critical, 2.2) The cut constant is not safe against solver tolerances; compute a safe Lagrangian bound.**
`Qt_s(xhat)` is the primal `ObjVal`, and `(Pi, RC)` is dual feasible only within `OptimalityTol = 1e-7` per column.
With 0.5-0.9 M bounded columns (`U_a` up to the fleet size, `z <= U_e`), the dual objective can be off by about
`sum_v |rc violation_v| (u_v - l_v)`, i.e. up to tenths of a USD, far above `delta_s = 0.007 USD`. With free copy
columns a reduced cost of 1e-7 on a copy makes the formal dual bound `-inf`. Fix (section 2.2 rewritten): take
the row duals `Pi` of the E2 rows only, project them to the correct sign (`<=` rows `min(Pi, 0)`, `>=` rows
`max(Pi, 0)`, equality free), recompute `rc = q - A^T Pi` exactly (sparse `m.getA()`), and use

```
theta_s >= sum_{i not fix} Pi_i h_i + sum_{v not copy} min(rc_v l_v, rc_v u_v) + sum_j beta_j x_j,
beta = -T^T Pi  (the explicit form of 2.2)
```

This is weak duality for any `Pi`, valid at every `x`, and needs every non-copy column to have finite bounds (true
for all E2 columns; the elastic columns get finite upper bounds, C2). The fixing-row `Pi` become an audit only.
`delta_s` is dropped.

**C2 (critical, 2.3-2.4) The elastic LP is not complete recourse as designed; add artificial columns.** Zero
activity does not satisfy (5): every unit of supply must reach the sink. A bike whose template terminal arcs are
reachable only after a swap (low `q0`, `q_res = 2` on Manhattan) has no path when its swap sites are closed or
only fractionally open, because swap flow is capped by (22) `sum X <= M_j y_j` and by stock (14)-(16) with
`n <= K y`, and the slacks on (9), (17), (18) do not relax these rows. The LP is then infeasible and returns no
`Pi`; this is most likely exactly at the fractional in-out separation points of 3.6. The build-time assertion
"every bike has a terminal arc in the template" does not prevent it. Fix (2.1 step 4 and 2.4 (a) rewritten): add,
per commodity and source state, one artificial column `source -> SINK` with cost `M_el` per bike and bounds
`[0, supply]`. Then the point "all supply on artificial columns, `u = 1`, `h = z = c = 0`, `n_jLt = B_j` for all
`t`, `n_jqt = 0` for `q < L`" satisfies (5), (6), (10), (13)-(16), (20)-(22) for every `x` in the menu hull, (17)
when `B_j >= R_end_j y_j` (true on every family menu, but the slack `s17` is kept for safety) and (18) when
`rho <= 1` (slack `s18` kept). So the bound LP is feasible at every master point (complete recourse by
construction). Adding columns only lowers the minimum, so it remains a relaxation of `Q^LP` and every cut stays
valid. `s9` becomes redundant but is harmless. All elastic columns get finite upper bounds (`s9 <= U_kj`,
`s17 <= R_end_j`, `s18 <= rho sum_j K_j`, artificial `<= supply`) so that C1 applies.

**C3 (critical, 3.4, 4.2) Evaluator `bound` and `total` include `C_setup`; OPTIMAL does not mean `bound = total`.**
The layout ILP minimises the full objective (26) with `y, B, C` fixed as variables, so `row.total` and `row.bound`
(Gurobi `ObjBound`) include `C_setup`, while `theta_s` and `Qt_s` are OPEX only. `LBIP_s = max(Qt_s, row.bound)`
would overstate the scenario OPEX by `C_setup` and produce invalid integer cuts; `V = setup + sum p_s row.total`
would count the setup twice; `BestBdStop = need_s` would stop `C_setup` too early. Also, `ILP_PARAMS_R3 = {Seed:
0}` leaves `MIPGap` at its default 1e-4, so an OPTIMAL row has `bound <= total` with a relative gap up to 1e-4,
not equality, and the cache reuses rows with gaps up to 1 % (`REUSE_GAP_TOL`). Fix (3.4 and 4.2 rewritten):
`bound_s := row.bound - row.C_setup` for every status that carries a bound, `ub_s := row.opex`,
`BestBdStop := need_s + C_setup(xhat)`, and `V = setup + sum_s p_s ub_s`. "Exactly priced" means within the pricing
gaps; the termination argument of 3.4 is restated accordingly.

**C4 (important, 4.2, 9) `ObjBound` is dropped when Gurobi has no incumbent.** `ILPModel.solve` sets `bound = None`
when `SolCount = 0`, and the evaluator turns such solves into `NO_INCUMBENT`. With `BestBdStop` and a rejected MIP
start (the baseline start often violates the written (17)-(18)), a stopped solve can have a strong bound and no
incumbent; the certificate would lose it. Fix: record `ObjBound` whenever Gurobi provides it (stats only, no E2
change, default results unchanged because `bound` is only added where it was `None`); O2 uses such a row as a lower
bound only. Rows with `NO_INCUMBENT`, `ERROR` or `SKIPPED_BUDGET` never produce no-good or combinatorial cuts.

**C5 (important, 3.8) The LP pruning test compares with the wrong budget.** `v_LP >= min_{m: inv <= Budget_m} UB_m
- tol` compares with the largest budget's `UB` (the `UB_m` are nonincreasing in `m`). A layout that is optimal at
`m = 1` but worse than `UB_4` would never be priced, master 1 would keep proposing it, and `LB_1` would stall below
`UB_1`. Not invalid, but the budget can never be certified. Fix: skip pricing only if `v_LP >= UB_m - tol` for every
budget `m` with `inv(xhat) <= Budget_m`, i.e. `v_LP >= max_{m: inv(xhat) <= Budget_m} UB_m - tol`.

**C6 (important, 3.5 S2) The family cut is invalid as written.** `LBF_s = min_{B, C} (size cost + OPEX_s)` includes
`bB B + bC C`, but `theta_s` is OPEX only, so `theta_s >= LBF_s` at `d_role = 0` can cut off the true value of a
family member with large sizes. Correct cut: `theta_s >= LBF_s - sigma_F(x) - (LBF_s - L_s) d_role(y, yF)` with
`sigma_F(x) = sum_{j in F} (bB B_j + bC C_j)` (linear in `w`); at `d_role >= 1` the right-hand side is at most
`L_s`. The family ILP must add (7) `B_j <= K y_j` and the menu range itself (the shared sub-model omits (7)-(8)); a
range wider than the menu (hub `C in {2, 3, 4}`) is a relaxation and stays valid.

**C7 (moderate, 3.5 S3) The Lagrangian statement is wrong.** Relaxing the copy (nonanticipativity) constraints
keeps each scenario's integer operations problem, so the Lagrangian dual is at least the LP-recourse bound and can
close exactly the operations-integrality gap (Caroe and Schultz 1999). It stays "not recommended", but for cost:
each Lagrangian subproblem is a one-scenario integrated siting MIP, which had no usable bound at 12 candidates. If
the LP gap is large, the affordable options are S2 and Benders cuts from integer information (Lagrangian cuts,
Chen and Luedtke 2022) on a few layouts.

**C8 (moderate, 2.3, 2.4 c) Relaxed targets can also be IP-infeasible.** Besides reachability, bikes that must
swap need full batteries ((14), (16)) and swap positions ((22), `M_j = 1` per slot) at open sites; integer
infeasibility from stock or position capacity is possible with `rho = R_end = 0`. The no-good handles it under
both targets, but no-goods must be tagged by target: a relaxed `INFEASIBLE_ILP` no-good is valid for the written
problem, never the reverse. Under relaxed targets infeasibility is down-closed (fewer objects or smaller `B, C`
never restore feasibility, because an extra object can stay idle with `n_jLt = B_j`), so an optional stronger
cut excludes every layout dominated by the infeasible one. Under written targets it is not (a new swap object adds
(17), a larger `B` raises (18)).

**C9 (moderate, 3.5 S1) Most S1 rows are redundant.** `n_jqt <= K_j y_j` is implied by (15) with `n >= 0`;
`c_jqt <= min(Cbar, K) y_j` is implied by (20) `chargers` and the master's `C_j <= c_max y_j`; arc-level swap rows
are implied by (22) when `M_j = 1` (all current families). Only the arc-level terminal rows
`X_a <= U_a Yc_{fac(a)}` (and swap rows if some `M_j > 1`) strengthen the LP. They are valid at every integer `x`
and have `Yc` on the left-hand side, so the cuts stay valid.

**C10 (moderate, 3.6) The in-out core point can violate master rows.** The proposed uniform point gives
`sum_{j in R_k} y_j` well below 1 (about 0.02-0.1 per object on Manhattan), violating the cover rows (and possibly
swap and access rows). Validity is unaffected (cuts are valid everywhere), but in-out convergence needs a core
point in the master LP region. Fix: core point = convex combination of admissible warm-start layouts within
`Budget_m` (feasible for every master row), enlarged by admissible layouts that contain otherwise unused objects.

**C11 (minor, 1.2, 7.1 e) Algorithm (A) equals the extensive form only for box menus.** `integrated_stochastic_ilp`
encodes sizes by `size_bounds` ranges, so the hub menu `C in {2, 4}` becomes `{2, 3, 4}`; (A) is then a relaxation.
Test 7.1 (e) uses a box toy menu, or compares with `exhaustive` only.

**C12 (minor, 1.2, 7.1 c) Why the template LP equals the layout LP at integer `x`.** Not only because of the
reachability pass: the template aggregated network merges more bikes and has larger `U_a`, `term_ub` than the
layout network. Equality holds because closed objects force their swap and terminal flows to 0, and at integer `y`
the aggregated LP equals the per-bike LP (closure: an LP path from `s_c` stays in class `c`'s arc set; class flows
are at most `m_c` per arc and split evenly per bike), so both sides equal the per-bike LP on `subset_library`.
Preconditions to assert once per scenario: no `options['forced_transfers']` (applied by `build_model` but not by
`build_submodel`), no dummy terminal arcs, and `check_lib_prices` passes on the repriced template.

**C13 (minor, 3.4) Classic L-shaped cut needs `LBIP_s >= L_s`.** Otherwise `-(LBIP - L) d` grows with `d`. Use
`LBIP_s := max(LBIP_s, L_s)`. The clipping `b = max(0, b)` in `superset_bound` and `sigma_F >= 0` in C6 need all
objective coefficients nonnegative (order prices `P`, `theta`, travel, transfer, electricity); assert it.

**C14 (minor, 7.2) The Midtown cache cannot be both read only and receive new solves.** The up-to-4 new ILP rows
would be appended to `outputs/e9_bilevel/cache`. Copy its `index.jsonl` and `schedules/` into
`outputs/o2_siting/midtown_cache` and run there (reuse requires `CACHE_VERSION = 'e9-2'` unchanged and old prices).

**C15 (minor, 7.1 f) LP-phase test.** The LP master also carries `theta_s >= LB_s^sup`, which can legitimately lift
it above the extensive LP; and with finite `M_el` the Benders LP is the elastic LP. Compare the LP phase without the
`LB^sup` rows against the extensive LP with the same artificial and slack columns.

**C16 (minor, 2.1, 3.7) Copies and pool scope.** The template always has all three roles (`evaluator.template`
uses `ROLES`) even when the master has fewer (Midtown: `{S, SC}`); copies of objects whose role is not in the
master are fixed to 0. Cut import across targets is one way only: relaxed -> written (LP, integer, terminal cuts and
relaxed no-goods); written no-goods are never used for the relaxed problem.

**Answer to the review questions.** (i) Coupling rows and right-hand sides are correct, including the rows that
multiply bounds by `y` and the rows that exist only per role. (ii) Dual cuts are valid for every first-stage value
because the sub-model is built once on the all-candidates template with first-stage values only in right-hand
sides; with C1 they are also safe against tolerances. (iii) The master value is a valid lower bound on `V*_m` for
both targets once C1, C3, C6 and C13 are applied; the remaining items affect completeness of the search or bound
strength. (iv) Recourse is not complete for E2 (integer infeasibility is real under both targets) nor for the
designed elastic LP; with C2 the bound LP is complete and integer infeasibility is handled by the combinatorial
cuts. (v) Aggregated-model duals give valid bounds for the per-bike integer problem. (vi) Incumbent pricing is
consistent with the cuts (all-candidates sub-library); round-5 `open_sites` values are upper bounds only.

---

## 0. Definitions and conventions

* **Layout** `lambda` = open items `(l, r, B, C)` (`bilevel.Layout`): one role per location, sizes from the
  family size menu `sites_nyc.SIZE_MENUS[family]`.
* **Admissible layout** satisfies all of the following:
  * at least one swap-capable object;
  * swap-only sites only next to an open C or SC object, the E9 relaunch rule `layout_admissible(...,
    s_needs_charge=True)`;
  * investment within the budget, `inv(lambda) = sum (Fhat + bhat B + chat C) <= Budget_m = m x 52,150 USD`;
  * optionally the access row [U4].
* **Value** `V(lambda) = C_setup(lambda) + sum_s p_s OPEX_s(lambda)`, design section 3.
  * `OPEX_s` is the optimal value of the E2 operations ILP with facilities fixed, on the layout instance
    `sites_nyc.layout_instance`.
  * The arc library is the sub-library of the scenario's all-candidates template (`reposition =
    'all_candidates'`, `sites_nyc.subset_library`). This is the convention of (A), (B) and `superset_bound`.
* **Target** `V*_m = min { V(lambda) : lambda admissible at budget m }`, separately for written and relaxed
  targets.
* Every ILP total is, as always, an upper bound on the unpruned written optimum (PRUNING_NYC); `V*` is the optimum
  *under this library convention*.
* **Library convention.** The round-5 search used `open_sites` libraries. Those values are upper bounds on the
  all-candidates values of the same layout, so the round-5 numbers are not comparable one to one. Under the new
  prices every layout is re-priced anyway.
* **Integer cuts need all-candidates pricing.** An `open_sites` ILP bound is NOT a lower bound on the
  all-candidates `OPEX_s`, so the integer cuts of section 3.4 require `all_candidates` pricing. The O2 evaluator
  is `LowerLevelEvaluator(..., reposition='all_candidates', aggregate=True)`.
* **Evaluator row fields (C3).** `row.total` and `row.bound` are on the full objective (26) and include
  `C_setup`; `row.opex = total - C_setup`. The OPEX bound of a row is `row.bound - row.C_setup`. `ILP_PARAMS_R3`
  only sets `Seed 0`, so `MIPGap` is the default 1e-4 and an OPTIMAL row has `bound <= total` with relative gap up
  to 1e-4. Every certificate uses `bound`, never `total`.
* **Prices.**
  * Midtown validation: the old `usd_sunk` prices (P 30, w 18, v 36).
  * Manhattan runs: the round-6 base (`costs.reprice_orders(inst, P=60, w=18, v=15, source=...)` exactly as in
    `experiments/r6_penalty.py`), applied to the base scenarios before any library is built. `theta` (31) is
    stored on the arcs, and `ilp.ILPModel` calls `costs.check_lib_prices`.
* **Cache keys.**
  * `LowerLevelEvaluator.cache_key` contains `costs.pricing_cache_component(scenario)`: `None` for an instance
    priced as generated, so the Midtown E9.1 rows remain reusable, and an order-price MD5 for repriced
    scenarios. It also contains the spec, the reposition mode, the pruning signature, the switches including
    `relaxed_targets` and `rho`, the params and the formulation flag.
  * `superset_bound` keys on the order prices as well.
  * The O2 cut pool (section 3.7) carries the same components.
* **Threads.** While the round-6 lanes run, only toy or tiny solves with `Threads 1` are allowed (the unit tests
  of section 7). Every Midtown and Manhattan step of sections 7-8 starts after the lanes have finished.

---

## 1. The two-stage model in the notation of the code

### 1.1 First stage

Role objects `j = (l, r)` (`facility_id(l, r) = 'M08:SC'`) for `l in Lambda`, `r in roles`. The first-stage
vector is `x = (y_j, B_j, C_j)_j`. In the master it is generated by menu binaries (section 3.1); in the
subproblem it enters only as right-hand sides.

* Rows on `x` only: (7)-(8), [U1], [U2] = (33a), [U4] and the structural rules (`s_needs_charge`, at least one
  swap object) are master rows, exactly as `bilevel.integrated_stochastic_ilp` adds them.
* `C_setup` (27) = `sum_j (F_j y_j + bB B_j + bC C_j)` is a first-stage cost (master objective).

### 1.2 Second stage (scenario s)

The operations model is the one `ilp.build_submodel(inst_s, lib_s, model, facility_vars=(y, B, C),
aggregate=True)` builds, where:

* `inst_s = all_candidates_instance(base_s, spec, roles)`, passed through `evaluator._maybe_relax`;
* `lib_s = subset_library(template_s, inst_s)`, i.e. the integrated-model (A) sub-model.

Variables:

| variable | type in ILP | bounds |
|---|---|---|
| aggregated arc flows `X_a` | integer | `[0, U_a]`; deliver arcs `U_a = 1` |
| `u_i` | binary | |
| `n_jqt` | integer | `0 <= n_jqt <= K_j` |
| `c_jqt` | integer | `0 <= c <= min(Cbar_j, K_j)`, `j in C` |
| `h_e` | binary | |
| `z_eq` | integer | `0 <= z <= U_e` |

The cost is `C_elec + C_travel + C_orders + C_reb` = (28)-(32) = `sub.objective - sub.components['C_setup']`.
Every variable bound is a constant: no bound depends on `x`.

Rows that do NOT involve `x` (constant right-hand side):

* (5) aggregated flow conservation (`out - in = supply m_c` at sources, `-sum m_c` at the sink, 0 elsewhere);
* (6) `sum_{a in deliver(i)} X_a + u_i = 1`;
* (10) `svc_lo` / `svc_hi` (`load >= h_e`, `load <= U_e h_e`);
* (13) balance, using `s_jqt`, `S_jt` of (12) and `D_jqt`, `A_jqt` of (11), all linear expressions;
* (14) joint availability;
* (16) `init_zero`: `n_jq0 = 0` for `q < L`;
* (21) grid group `p_ch sum c <= P_grid_gt`, a constant cap (the group exists in the all-candidates instance; at
  a closed charge object `c = 0` through (20), so it is identical to the layout instance).

**Coupling rows.** Each row is written as in `ilp.py` (left side = operations expression), with its right-hand
side as a function of the first stage. Row names are those of `ILPModel._build`, with prefix `s{s}_`.

| E2 | row name (code) | row | right-hand side `b_i(x)` | sign of `Pi_i` (min) |
|---|---|---|---|---|
| (9) aggregated terminal | `term[c{k},{j}]` | `sum_{a in term(k,j)} X_a <= .` | `U_kj y_j`, `U_kj = agg.term_ub[(k, j)]` | `<= 0` |
| (10) service at open origin | `svc_yo[e]` | `h_e <= .` | `y_{o(e)}` | `<= 0` |
| (10) service at open destination | `svc_yd[e]` | `h_e <= .` | `y_{d(e)}` | `<= 0` |
| (15) storage, `t = 0..H` | `store[j,t]` | `sum_q n_jqt <= .` | `K_j y_j` | `<= 0` |
| (16) initial full stock | `init_full[j]` | `n_jL0 = .` | `B_j` | free |
| (17) local end target, `j in S` | `end_local[j]` | `n_jLH >= .` | `R_end_j y_j` (0 when relaxed) | `>= 0` |
| (18) network end share | `end_share` | `sum_{j in N} n_jLH >= .` | `rho sum_j B_j` (0 when relaxed) | `>= 0` |
| (20) chargers, `j in C`, `t < H` | `chargers[j,t]` | `sum_{q<L} c_jqt <= .` | `C_j` | `<= 0` |
| (20) site power, `j in C`, `t < H` | `site_power[j,t]` | `p_ch sum_{q<L} c_jqt <= .` | `P_j y_j` | `<= 0` |
| (22) swap positions, `j in S`, `tau < H` | `swap_pos[j,tau]` | `sum_{a in occ(j,tau)} X_a <= .` | `M_j y_j` | `<= 0` |

Notes on the table:

* (16) `n_jq0 = B_j` for `q = L` and `= 0` otherwise.
* (12) and (19) are definitions (`S_jt`, `p_ch = eps / (eta Delta)`). They add no row.
* (33b) `zeta` and the lexicographic switch are not used (section 3.3 on [U5]).

**Monotonicity facts used below.**

* At a closed object (`y_j = 0`), rows (9) and (22) force its terminal and swap arcs to zero, (15)/(16) force its
  stock to zero, (20) forces `c = 0`, and (10) forces its services to zero.
* Hence at integer `x` the template LP equals the LP of the layout instance on `subset_library`: the reachability
  pass of `subset_library` only drops arcs that cannot carry flow, and at integer `y` the aggregated LP equals the
  per-bike LP on either library (closure argument, C12), although the template network has larger `U_a`,
  `term_ub` and possibly fewer commodities. Cut validity needs only `<=`, which holds at every integer `x`. The
  equality is a unit test, section 7.1 (c).
* Preconditions asserted at build time (C12): no `options['forced_transfers']` (applied by `build_model`, not by
  `build_submodel`), no dummy terminal arcs (`C_dummy_terminal` empty), `check_lib_prices` on the repriced
  template, and all objective coefficients nonnegative (C13).

Written compactly, per scenario: `Q_s(x) = min { q_s^T w : W_s w (sense) h_s - T_s x, w in bounds }`, with fixed
recourse matrix `W_s` (fixed because all candidate arcs exist in the template) and technology matrix `T_s` =
the coefficients in the table. `Q_s^IP` takes `w` integer, `Q_s^LP` continuous. `Q_s^LP <= Q_s^IP` at every `x`,
and `Q_s^LP` is convex and piecewise linear in `x` over the continuous hull. This is what makes L-shaped
optimality cuts valid globally, including cuts generated at fractional `x`.

The extensive form `min C_setup(x) + sum_s p_s Q_s^IP(x)` over admissible `x` is algorithm (A) when every role menu
is a box of sizes. `integrated_stochastic_ilp` encodes sizes by ranges (`size_bounds`), so the non-contiguous hub
menu `C in {2, 4}` of `r5_manhattan` becomes `{2, 3, 4}` there and (A) is a relaxation (C11).

---

## 2. Benders subproblem (one persistent LP per scenario)

### 2.1 Construction (new class `benders.ScenarioLP`)

1. Load the template: `inst_s`, `lib_s` as in 1.2. The template and library are taken from the evaluator
   (`evaluator.template(s)`), so incumbents and cuts share the arcs.
2. Create **free copy variables** for every facility id of the template: `Yc_j`, `Bc_j`, `Cc_j` with
   `lb = -inf`, `ub = +inf`, continuous, zero cost. The template always has all three roles (`evaluator.template`
   uses `ROLES`); copies of objects whose role is not in the master's role set are fixed to 0 (C16).
3. Build the sub-model with `ilp.build_submodel(inst_s, lib_s, m, facility_vars=(Yc, Bc, Cc), prefix=f's{s}_',
   aggregate=True, keep_rows=True)`.
   * `keep_rows` is a new keyword of `ILPModel`, default `False`, so the default path is byte-identical. With it,
     `ILPModel.add()` appends the returned `Constr` to `self.rows[family]` so that rows can be addressed without
     names.
   * Names are switched off above 300 k model arcs. Fallback: `names=True`.
   * The sub-model adds (5)-(6), (9)-(22). (7)-(8) and (33) stay in the master, which is the existing
     shared-model contract.
4. Add the relaxation columns of section 2.4 (a) (C2): one artificial column `source -> SINK` per commodity and
   source state (bounds `[0, supply]`), and the slacks `s9`, `s17`, `s18` with finite upper bounds. Objective:
   `sub.objective - sub.components['C_setup'] + M_el * (sum artificial + sum slacks)`.
5. Add the fixing rows `fix_y[j]: Yc_j = yhat_j`, `fix_B[j]: Bc_j = Bhat_j`, `fix_C[j]: Cc_j = Chat_j`.
6. Set every variable to `GRB.CONTINUOUS` (`m.setAttr('VType', m.getVars(), 'C')`), which gives the LP of the
   E2 rows.

**Re-solve for a new first-stage point** `xhat`: set `constr.RHS` of the fixing rows (3 x |objects| values,
`m.setAttr('RHS', fix_rows, values)`), then `m.optimize()`. Nothing else changes, so the previous optimal basis
stays dual feasible and the dual simplex warm start is the natural method.

**Gurobi protocol:**

* `OutputFlag 0`, `Seed 0`, `Threads 3` in production (`1` in tests).
* First solve: `Method 2` (barrier) with crossover on (a basis is needed for warm starts and exact `Pi`).
* Re-solves: `Method 1` (dual simplex), `LPWarmStart 2`.
* `FeasibilityTol = OptimalityTol = 1e-7`.
* If re-solves do not reuse the basis (check `IterCount` against the first solve), use `Presolve 0` for
  re-solves.

**Target switch without rebuilding.** The relaxed copy (`common.relax_end_targets`) differs from the written
instance only in `rho` and `R_end_j`. These appear only as coefficients of `Yc_j` in `end_local[j]` and of `Bc_j`
in `end_share`. So one LP per scenario serves both targets: `m.chgCoeff(end_local[j], Yc_j, -R_end_j or 0)` and
`m.chgCoeff(end_share, Bc_j, -rho or 0)`, about 50 coefficient changes. This halves memory on Manhattan.

### 2.2 Duals and the optimality cut

After an optimal solve at `xhat` (corrected by C1: the cut is computed from the E2 row duals by a safe
Lagrangian bound, not from `ObjVal` plus a shift):

* read `Pi` of every E2 row and of the elastic rows (`m.getAttr('Pi', rows)`), excluding the fixing rows;
* project to the dual sign of a minimisation: `Pi_i <- min(Pi_i, 0)` on `<=` rows, `max(Pi_i, 0)` on `>=` rows,
  unchanged on equality rows;
* recompute the reduced costs exactly, `rc = q - A^T Pi` (sparse `m.getA()` restricted to the non-copy columns,
  numpy), where `q` is the elastic objective;
* `beta = -T^T Pi`, the explicit form below (`T` = the copy-column coefficients of the coupling rows);
* `Qs_s(xhat) = sum_i Pi_i h_i + sum_{v not copy} min(rc_v l_v, rc_v u_v) + beta^T xhat` (the safe value; `h_i` is
  the constant part of the right-hand side).

**Optimality cut (multi-cut, one per scenario):**

```
theta_s  >=  l_s(x) := sum_i Pi_i h_i + sum_{v not copy} min(rc_v l_v, rc_v u_v)
                       + sum_j [ beta^y_j y_j + beta^B_j B_j + beta^C_j C_j ]
```

where `y_j, B_j, C_j` are the master's linear expressions in the menu binaries (section 3.1). No `delta_s` is
needed.

Validity (weak duality, for any `Pi` after the sign projection and any `x`): for every `w` within its bounds that
satisfies the rows at `x`, `q^T w = rc^T w + Pi^T A w >= sum_v min(rc_v l_v, rc_v u_v) + Pi^T (h - T x)` (rows written `A w + T x (sense) h`), hence
`l_s(x) <= Qt_s(x) <= Q_s^LP(x) <= Q_s^IP(x)`. This needs every non-copy column to have finite bounds: true for
all E2 columns and, after C2, for the elastic columns. It does not depend on the LP being solved to any accuracy;
accuracy affects only tightness (`Qt_s(xhat) - Qs_s(xhat)` is logged and should be below 1e-3 USD). Wherever a
lower bound is taken from the LP below (the lifted cut of 3.4, `lb_s` and `v_LP` in 3.8 and 4.2), it is the safe
value `Qs_s(xhat) = l_s(xhat)`, never `ObjVal`.

The fixing-row duals `fix_y[j].Pi` etc. are used only in the audit: with free copies they equal `beta` up to the
solver tolerances.

**Explicit form, used for the cut coefficients (and in the audit).** Stationarity of the free copy `Yc_j` (zero
cost, reduced cost 0) gives `fix_y[j].Pi = - sum_i a_ij Pi_i`. With the table of 1.2:

```
beta^y_j = sum_k U_kj Pi(term[k,j]) + sum_{e: o(e)=j} Pi(svc_yo[e]) + sum_{e: d(e)=j} Pi(svc_yd[e])
         + K_j sum_t Pi(store[j,t]) + R_end_j Pi(end_local[j]) + P_j sum_t Pi(site_power[j,t])
         + M_j sum_tau Pi(swap_pos[j,tau])
beta^B_j = Pi(init_full[j]) + rho Pi(end_share)
beta^C_j = sum_t Pi(chargers[j,t])
```

which is the textbook `theta_s >= Q(xhat) + sum_i Pi_i (b_i(x) - b_i(xhat))`. The elastic columns of 2.4 (a) do
not touch the copies, so they do not change these formulas. Audit, run in the unit tests and on every 50th
production solve:

* `|Yc_j.RC|, |Bc_j.RC|, |Cc_j.RC| <= 1e-6`;
* the explicit sums from `keep_rows` equal the fixing-row duals within `1e-6 (1 + |beta|)`;
* `0 <= Qt_s(xhat) - Qs_s(xhat) <= 1e-3` USD (safe value against `ObjVal`).

**LP solution kept for section 5.** Per role object: swap volume `sum_t S_jt`, terminal flow, charging
`sum_{q,t} c_jqt`, shipped and received loads `sum z`, and the elastic slack total.

### 2.3 Is the recourse complete?

Without help it is not. Three mechanisms can make a scenario infeasible for some first-stage values:

1. **Terminal (9).** Every unit of flow must leave through a terminal arc of an open swap object. A bike whose
   reachable terminals are all at closed objects makes the scenario infeasible (`INFEASIBLE_TERMINAL` in the
   evaluator; real on Manhattan with `q_res = 2` levels and depots at the bridges). At fractional `y`, the
   aggregated row `X <= U_kj y_j` can make the LP infeasible even when every bike has a reachable open terminal
   in the integer sense. The siting libraries have no dummy terminal arcs (`dummy_terminal_cost = None`, see
   `or_instance.DEFAULT_OPTIONS`).
2. **Written end targets (17)-(18).** `n_jLH >= R_end_j y_j` and `sum_j n_jLH >= rho sum_j B_j` require full
   stock at `H`. A layout whose bikes must swap to reach a terminal, while its sites cannot recharge in time
   (swap-only sites, one charger), can be infeasible.
   * Round 5 shows it is real: `M07:SC:B3:C1` is `INFEASIBLE_ILP` in scenario 0 with written targets and feasible
     when relaxed.
   * It can also be IP-infeasible but LP-feasible: integrality of stock and charging steps.
3. **Stock and swap positions (14), (16), (22)** (added by C8). Bikes that must swap need a full battery in
   stock and a free swap position (`M_j = 1` per slot) at an open site. With small `B_j`, slow charging and several
   low bikes this can make the ILP infeasible even with `rho = R_end = 0`. At fractional `y` the caps `M_j y_j`
   and `K_j y_j` make it worse in the LP.
4. **Unserved orders (6)** never cause infeasibility (`u_i = 1`). (10), (14), (15), (20)-(22) are feasible at
   zero activity of the bikes' operations, but zero activity is NOT feasible for (5): the supply must reach the
   sink. (16) and (15) are compatible because the master enforces `B_j <= K_j y_j` (7).

Relaxed targets: mechanisms 1 and 3. Written targets: mechanisms 1, 2 and 3. Mechanism 1 is monotone in the open
swap-object set; mechanism 3 under relaxed targets is down-closed in the layout (C8); mechanism 2 is not monotone.

### 2.4 Feasibility handling (chosen design: elastic LP + combinatorial cuts)

**(a) Elastic columns in the bound LP only (corrected by C2).** Cost `M_el = 1e4` USD per unit, all with finite
upper bounds (needed by the safe cut of 2.2):

* **artificial columns** (the essential part): for every commodity `c` and source state `w` with supply
  `m_cw > 0`, one column `a_cw` from `w` to `SINK`, bounds `[0, m_cw]`, entering (5) with `+1` at `w` and `-1` at
  the sink;
* `X_term(c,j) - U_cj Yc_j - s9_cj <= 0`, `0 <= s9_cj <= U_cj` (redundant once the artificial columns exist, kept
  because it is harmless);
* `n_jLH - R_end_j Yc_j + s17_j >= 0`, `0 <= s17_j <= R_end_j`;
* `sum n_LH - rho sum Bc + s18 >= 0`, `0 <= s18 <= rho sum_j K_j`.

Consequences:

* The LP is then feasible for every `x` in the menu hull: complete recourse by construction. The point "all supply
  on the artificial columns, `u = 1`, `h = z = c = 0`, `n_jLt = B_j` for all `t`, `n_jqt = 0` for `q < L`, slacks
  as needed" satisfies (5), (6), (10), (13)-(16), (20)-(22) because `B_j <= K_j y_j` holds on the hull, and (17)-(18)
  with the slacks. Without the artificial columns this fails (C2): a bike that can reach a terminal only after a
  swap has no path when its swap sites are closed or fractionally open, because (22) and (14)-(16) cap the swap
  flow and carry no slack. A template assertion "every bike has a terminal arc" does not prevent this.
* Its value `Qt_s(x) <= Q_s^LP(x)` for any `M_el >= 0` (adding columns only lowers the minimum), so every cut stays
  valid.
* An infeasible layout gets a large `Qt_s` (the toy: 5,200-20,400 against about 100), and the cut's slope points
  to the facilities that remove the violation. Feasibility cuts are therefore subsumed by optimality cuts, and no
  Farkas sign conventions are needed.
* The artificial and slack totals are recorded per solve.
* `M_el` must be finite and large: by exact-penalty theory `Qt = Q^LP` once `M_el` exceeds the relevant duals. A
  bike diverted to its artificial column loses at most its orders (order price times the orders one bike can
  serve in the window, a few hundred USD), so 1e4 per bike and per battery is above it.
* The elastic columns are NOT part of the pricing ILP, which stays the unchanged E2 model.

The Farkas alternative (`InfUnbdInfo 1`, `FarkasDual` of the fixing rows, cut `FarkasDual^T r(x) + const`
oriented so that `xhat` violates it) stays documented as a fallback. It is not implemented unless `M_el` causes
numerical trouble, which the 1e-7 tolerances and coefficient range 1e-1..1e5 make unlikely.

**(b) A-priori terminal cover rows (master).** From the template library of each scenario, let
`R_k^s = { j in S : bike k has a terminal arc labelled j in template_s whose tail is reachable from s_k }`. The
Manhattan and Midtown templates are built with reachable pruning, so every terminal arc present is reachable with
all candidates open; the toy templates are not pruned, so the reachability test is done explicitly (with it the
row is tighter; without it the row is weaker but still valid). The master gets:

```
sum_{j in R_k^s} y_j >= 1      for every bike k and scenario s   (duplicates removed)
```

These rows are valid (necessary): `subset_library` only removes arcs, so a bike with no open `j` in `R_k^s` has no
path. They cut most terminal-infeasible layouts before any LP is solved. They are not sufficient, because a
terminal at `j` may be reachable only after a swap at a closed `j'`. The elastic LP and (c) handle the rest.

**(c) Combinatorial cuts after pricing.**

* `INFEASIBLE_TERMINAL` at layout `lambda`, with open swap-object set `O`, is monotone: every layout whose open
  swap set is a subset of `O` is also terminal-infeasible, because `subset_library` reachability shrinks. Cut:
  `sum_{j in S \ O} y_j >= 1`.
* `INFEASIBLE_ILP` (Gurobi INFEASIBLE or INF_OR_UNBD; possible under both targets, C8): a plain no-good on the
  menu binaries, `d(w, what) >= 1` (section 3.4). This excludes exactly that layout, which has `V = +inf`. The cut
  is tagged with its target: a relaxed no-good is valid for the written problem, a written no-good never for the
  relaxed one. Optional under relaxed targets only: infeasibility is down-closed (an extra object can stay idle
  with `n_jLt = B_j`; larger `B, C` only loosen rows), so the cut may exclude every layout whose objects are a
  subset of `what`'s with sizes no larger.
* `NO_INCUMBENT`, `ERROR`, `SKIPPED_BUDGET` rows never produce a combinatorial cut (C4).

---

## 3. Master MIP (new class `benders.Master`)

### 3.1 Menu encoding

* Options `o = (r, B, C)` from `bilevel.option_grid(size_menu, roles)`.
* Binaries `w_{l,o}` for `l in Lambda`, `o in options`, plus `theta_s >= 0` for each `s`.
* Derived expressions:

```
y_(l,r)  = sum_{o: role(o)=r} w_{l,o}
B_(l,r)  = sum_{o: role(o)=r} B_o w_{l,o}
C_(l,r)  = sum_{o: role(o)=r} C_o w_{l,o}
```

This reproduces every menu exactly, including the non-contiguous hub menu `C in {2, 4}` and the round-5 issue 2
(no size escape outside the menu). (7)-(8) hold by construction of the menu (`valid_sizes`). Manhattan:
15 x 14 = 210 binaries. Midtown validation: 4 x 4 = 16.

### 3.2 Rows

| row | formula | note |
|---|---|---|
| [U1] | `sum_o w_{l,o} <= 1` for every `l` | one role per location |
| [U2] | `sum_{l,o} inv_o w_{l,o} <= Budget_m`, `inv_o = Fhat + bhat B_o + chat C_o` | one master per budget: the RHS is changed |
| swap | `sum_{l, o swap-capable} w_{l,o} >= 1` | implied by the cover rows; kept for clarity |
| `s_needs_charge` | `y_(l,S) <= sum_{l', r in {C,SC}} y_(l',r)` for every `l` | as in `integrated_stochastic_ilp` |
| [U4] (optional) | `sum_{l in Lambda(z)} sum_{o swap-capable} w_{l,o} >= 1` per zone | `bilevel.access_sets(cands, scen, D)`; zones with an empty set are reported and skipped |
| cover | section 2.4 (b) | |
| initial bound | `theta_s >= LB_s^sup` | `evaluator.superset_bound(method='lp')`: valid for every layout under both targets (relaxed, all open, free sizes) |
| cuts | 2.2 optimality, 3.4 integer, 2.4 (c) combinatorial | shared by all budgets (none depends on `Budget_m`) |

* Objective: `min sum_{l,o} setup_o w_{l,o} + sum_s p_s theta_s` with `setup_o = F_r + bB B_o + bC C_o`
  (`spec.setup_cost(r)`).
* By the `theta_s >= LB_s^sup` rows, the master value is never below `min setup + sum_s p_s LB_s^sup`. The O2
  bound therefore dominates the superset bound by construction.
* **[U5] expected served share** couples second-stage `u_is` across scenarios. It is not separable and is not in
  O2. The greedy's 50 % served-share guard is a heuristic filter, not part of `V*`. The served share of every
  certified layout is reported.
* **Symmetry.** None needs breaking: candidates are distinct nodes, the SC menu has `C >= 1` so `S:B1` and
  `SC:B1:C0` cannot both exist (the old duplicate of E9 issue 9 is gone), and scenarios are distinct.

### 3.3 Master solving

* Gurobi, `Threads 2`, `MIPGap 0`, `MIPGapAbs 1e-4`, `Seed 0`; seconds per solve (210 binaries, at most a few
  thousand cuts).
* The reported bound is `ObjBound` (equal to `ObjVal` when optimal).
* Multi-tree loop: re-solve after each round of cuts. This is simple to checkpoint and resume, and the master cost
  is negligible against the LPs.
* A single-tree lazy-constraint callback is a later optimisation and is not needed.

### 3.4 Integer cuts from exact pricing (default, not optional)

Let `what` be the menu binaries of a priced layout `xhat` and
`d(w, what) = sum_{what=1} (1 - w) + sum_{what=0} w` (the Hamming distance; 0 only at `xhat`; 2 for a size or
location change).

* `L_s = LB_s^sup`.
* `LBIP_s(xhat) = max(Qs_s(xhat), bound_s, L_s)` (corrected by C1, C3, C13), where
  `bound_s = row.bound - row.C_setup` is the evaluator row's Gurobi `ObjBound` minus the setup cost. `row.bound`
  is on the full objective (26), which includes `C_setup`; it is `<= total` even when OPTIMAL (`MIPGap` 1e-4), and
  it is also available at TIME_LIMIT, at BestBdStop (`USER_OBJ_LIMIT`) and, after C4, without an incumbent. It is a
  valid lower bound on `Q_s^IP(xhat)`. Never use `total` or `opex` here, and never a row priced on an `open_sites`
  library. Taking `L_s` into the max keeps `LBIP_s - L_s >= 0`, which the classic cut needs.

Add, per scenario:

```
(classic L-shaped, Laporte-Louveaux)  theta_s >= LBIP_s - (LBIP_s - L_s) d(w, what)
(lifted, uses the LP cut l_s at xhat) theta_s >= l_s(x) + Delta_s (1 - d(w, what)),   Delta_s = max(0, LBIP_s - l_s(xhat))
```

Validity of the lifted cut:

* at `d = 0` it gives `LBIP_s`;
* at `d >= 1` its right-hand side is `<= l_s(x) <= Q_s^IP(x)` (with `l_s` the safe cut of 2.2).

The classic cut gives `L_s` at `d = 1`. Both are kept. Both are valid only for the target under which `LBIP_s`
was computed and for the written target if that was the relaxed one (3.7).

Termination: after pricing, the master values `xhat` at `setup(xhat) + sum_s p_s LBIP_s >= V(xhat) - sum_s p_s
(ub_s - lb_s)`, where `ub_s - lb_s` is the pricing gap of scenario `s` (at most 1e-4 relative when OPTIMAL). If the
master returns `xhat` again, `LB_m` is at least that value and `UB_m <= V(xhat)`, so the budget's gap is at most the
pricing gaps of `xhat`; when they exceed `tol`, escalation (4.3) re-prices `xhat`. The loop terminates after
finitely many layouts, because the layout set is finite.

### 3.5 Optional strengthening (switched on by the measurement gate of section 8, step 3)

**(S1) Bound-only valid inequalities at fractional `y`, in the subproblem LP.**

* Arc-level `X_a <= U_a Yc_{fac(a)}` for terminal arcs (disaggregated (9)), and for swap arcs only if some
  `M_j > 1` (with `M_j = 1`, the value of every current family, (22) already gives `X_a <= Yc_j`).
* Dropped after review (C9): `n_jqt <= K_j Yc_j` is implied by (15) with `n >= 0`; `c_jqt <= min(Cbar_j, K_j)
  Yc_j` is implied by (20) `chargers` together with the master's `C_j <= c_max y_j`.

At integer `y` the terminal rows are implied by the E2 rows (`y = 1`: the constant bounds; `y = 0`: (9) already
forces zero), so `Q^LP` at integer `x` is unchanged; `Yc` appears in them as a coefficient of a row with constant
right-hand side, so the cuts of 2.2 stay valid (their `beta` gains the term `sum_a U_a Pi(arc row)`). They only
tighten the LP phase (aggregated (9) is weak with free `y`, `aggregate.py` docstring) and the relax-and-round
input. Cost: about one row per terminal arc.

**(S2) Size-family bounds (cut corrected by C6).** A family `F = (open (l, r) set)` covers all sizes in the menu.
Per scenario, solve the operations ILP with `y` fixed to the family and `B_j, C_j` free integers over the menu
range, minimising `sigma_F + OPEX_s` with `sigma_F = sum_{j in F} (bB B_j + bC C_j)`. It is the integrated
sub-model with fixed `y`, plus the rows (7) `B_j <= K_j y_j` and the menu range that the shared sub-model omits,
with Gurobi `ObjBound` as `LBF_s`. A range wider than the menu (hub `C in {2, 3, 4}`) is a relaxation and stays
valid. Then `OPEX_s(x) >= LBF_s - sigma_F(x)` for every `x in F`, and `sum_s p_s LBF_s + F_r terms <= V(lambda)`
for every `lambda in F` (the scenario-wise minimum underestimates the joint one). Family cut, with the size cost
moved to the right-hand side because `theta_s` is OPEX only:

```
theta_s >= LBF_s - sigma_F(x) - (LBF_s - L_s) d_role(y, yF),   d_role = Hamming distance on y_(l,r)
```

At `d_role >= 1` the right-hand side is at most `L_s - sigma_F(x) <= L_s`. The uncorrected form
`theta_s >= LBF_s - ...` is invalid: it can exceed `OPEX_s` of a family member with large sizes.

One ILP per scenario bounds up to 8^k layouts (8 SC sizes per site). Use it when many layouts of one family sit
within the LP gap of `UB`.

**(S3) Not recommended.**

* Lagrangian relaxation of the copy (nonanticipativity) constraints (statement corrected by C7). Its dual keeps
  each scenario's integer operations problem, so it is at least the LP-recourse bound and can close the
  operations-integrality gap (Caroe and Schultz 1999). It is not recommended because of cost: every Lagrangian
  subproblem is a one-scenario integrated siting MIP, the model (A) had no usable bound at 12 candidates. If the
  LP gap is large, use S2 first, then Benders cuts from integer information on a few layouts (Lagrangian cuts,
  Chen and Luedtke 2022).
* Magnanti-Wong Pareto cuts (the network LP is highly degenerate): worth trying only if the LP phase stalls,
  using the in-out core point as the MW core.

### 3.6 Warm start and stabilisation

**Warm-start layouts,** each priced exactly and turned into LP plus integer cuts before the first master solve:

* `rule_layout` CSCD / CSTC (`cstc_mode='access'`, no singleton ILPs) / CSAV at every budget, `role='SC'`, with
  the family menu caps;
* the round-5 chosen layout `M06:SC:B4:C2|M12:S:B3:C0` (inv 103,950: feasible for `m >= 2`);
* the round-5 best known `M08:SC:B3:C2|M09:SC:B3:C2` (= CSCD `m = 2`);
* the best singleton by Q^LP;
* the present-day proxy (`capacity_matched_layout` to the current best layout).

The best priced layout per budget sets `UB_m`. It is the master `Start` (`w.Start`), and its schedules are kept in
the cache as MIP starts for neighbouring pricings (evaluator `warm`).

**Stabilisation (LP phase only, section 3.8).** In-out separation (Ben-Ameur and Neto):

* separate at `x_sep = alpha xcore + (1 - alpha) xmaster` with `alpha = 0.5`;
* core point (corrected by C10) initialised as a convex combination of admissible integer layouts within
  `Budget_m`: the warm-start layouts plus, for every object not in any of them, one admissible layout that
  contains it (for example that object plus the cheapest SC option at a location that completes the cover rows,
  within the budget). It satisfies
  every master row (cover, swap, `s_needs_charge`, [U4], budget) and opens every object fractionally
  (informative duals for objects that are otherwise closed and get arbitrary degenerate `Pi`). The uniform point
  `w_{l,o} = min(1/|options|, Budget_m / (|Lambda| sum_o inv_o))` of the first draft violates the cover rows
  (about 0.02-0.1 per object on Manhattan). Then `xcore <- (xcore + xmaster)/2`. Validity never depends on the
  core point; convergence of in-out does;
* if the cut at `x_sep` does not cut off `xmaster`, separate at `xmaster` too (Fischetti-Salvagnin-Zanette);
* if the bound improves by less than 0.01 % over 5 iterations, set `alpha = 0` (Kelley) to converge.

The integer phase needs no stabilisation: its points are integer layouts that are priced anyway.

### 3.7 Cut pool and resume

`cuts.jsonl` (append-only), one record per cut: `kind` (lp / lshaped / lifted / terminal / nogood / family),
scenario, target, layout key or the fractional `r` (sparse), the safe constant `c0 = sum Pi h + sum min(rc l,
rc u)` (2.2), `Qt` (ObjVal, for the log only), `beta` (sparse dict over `('y'|'B'|'C', j)`), `Delta`, `LBIP`,
`bound_s`, `C_setup` and the evaluator row keys it used.

Header signature: `CACHE_VERSION`, family, seeds, `demand_md5`, order-price signatures, `spec.to_dict()`, roles,
menu, pruning signature (`all_candidates`), aggregate mode, `M_el`, target.

* Cuts are reloaded only when the signature matches, except for the one-way target import below.
* Relaxed-target cuts are also valid for the written problem (`Q^relaxed <= Q^written`: the written rows are a
  restriction, for the LP with its elastic columns and for the ILP). The written run is seeded with the relaxed LP
  cuts, integer cuts, terminal cuts and relaxed no-goods. The reverse import is invalid: written cuts and written
  no-goods are never used for the relaxed problem (C16).

### 3.8 Algorithm (one target; all budgets in one loop)

```
setup: scenarios (repriced), evaluator E (all_candidates, aggregated, cache dir outputs/o2_siting/cache),
       LB_s^sup = E.superset_bound('lp'); ScenarioLP_s for every s (target switch 2.1); master with rows 3.2
warm:  price the warm-start layouts (section 4), add their cuts; UB_m, best_m per budget
LP phase (per budget m, cuts shared): relax w; loop { solve LP master; x_sep (3.6); solve the 3 LPs at x_sep
       (in parallel threads); add cuts } until stall (< 0.05 % in 5 iterations) or 80 iterations;
       record LB_LP_m (= LP bound of the two-stage model with the menu hull) and x*_m for section 5
screen: relax-and-round shortlist per budget (section 5): cut envelope -> LP -> price the top 3
integer phase: repeat
    for every open budget m (gap_m > tol): solve master_m -> xhat_m, LB_m = ObjBound
    stop if every budget is closed, the wall is exhausted, or no new proposal appears in 3 rounds
    for every distinct proposal xhat:
        LP: if xhat is not in the LP memo, solve ScenarioLP_s(xhat) for all s; add LP cuts
        v_LP = setup(xhat) + sum_s p_s Qs_s(xhat)                               # safe LP values (2.2)
        if v_LP >= max_{m: inv(xhat) <= Budget_m} (UB_m - tol): continue       # pruned by the LP for EVERY budget (C5)
        price(xhat) (section 4); add the 3.4 integer cuts or the 2.4 (c) combinatorial cut;
        update UB_m for every m with inv(xhat) <= Budget_m (nested budgets: a priced layout serves every larger budget)
    if a proposal was already priced and its bounds are the binding ones: escalate its pricing (section 4.3)
output per budget: best layout, UB_m, LB_m, gap_m, LB_LP_m, LB^sup_m, coverage counters
```

`tol = max(0.25 % UB_m, 1 USD)`.

The pruning test uses the maximum (C5): the `UB_m` are nonincreasing in `m`, and a layout is useless only if it
cannot beat the incumbent of any budget it fits. With the first draft's minimum, a layout optimal at `m = 1` but
worse than `UB_4` would never be priced, master 1 would keep proposing it, and `LB_1` would stall below `UB_1`.

---

## 4. Incumbent pricing and the stopping rule

### 4.1 Evaluator configuration

`LowerLevelEvaluator(scenarios, spec, reposition='all_candidates', aggregate=True, time_limit=300,
time_limit_hub=600, threads=3, params=common.ILP_PARAMS_R3, cache_dir=outputs/o2_siting/cache,
relaxed_targets=...)`. Relaxed and written use `derive(relaxed_targets=True)`, which shares templates.

* The O2 cache is its own directory, because of the bound-stop rows of 4.2, which the greedy's reuse rule
  (`_reusable`) must never see as completed solves.
* The Midtown validation runs on a copy of the existing `outputs/e9_bilevel/cache` (`index.jsonl` and
  `schedules/` copied to `outputs/o2_siting/midtown_cache`, C14), so that new solves and bound-stop rows never
  enter the E9 cache.

### 4.2 `price(xhat, UB)`: per scenario, with a bound-driven stop

Corrected by C3 and C4: `row.bound` and `row.total` are on the full objective (26) and include
`setup(xhat) = row.C_setup`; the scenario's OPEX bound is `row.bound - row.C_setup`, its OPEX value `row.opex`.
`UB` is the incumbent of the largest relevant budget test, i.e. `max_{m: inv(xhat) <= Budget_m} UB_m` (as in C5).

```
lb_s <- max(Qs_s(xhat), L_s) for all s; ub_s <- None
for s in scenarios (order: largest p_s (Q_LP spread), default index order):
    need_s = (UB - tol - setup(xhat) - sum_{t != s} p_t lb_t) / p_s       # OPEX bound at which xhat is proven >= UB - tol
    row = E.evaluate_scenario(xhat, s, 'ilp', best_bd_stop=need_s + setup(xhat))   # Gurobi objective includes C_setup
    if row.bound is not None: lb_s <- max(lb_s, row.bound - row.C_setup)
    ub_s <- row.opex (None if infeasible / no incumbent)
    if row.status == INFEASIBLE_TERMINAL or INFEASIBLE_ILP: add the 2.4 (c) cut (target-tagged); return INFEASIBLE
    if row.status in (NO_INCUMBENT, ERROR, SKIPPED_BUDGET): keep lb_s, no cut from the status; mark xhat UNRESOLVED_s
    if setup + sum_t p_t lb_t >= UB - tol: add integer cuts with LBIP = lb; return PRUNED_BY_BOUND
add integer cuts (3.4) with LBIP_s = lb_s
V = setup + sum p_s ub_s if every ub_s exists (an upper bound on V(xhat), within the MIP gaps of the rows); UB_m updated with it
```

Required evaluator extension (no change to existing behaviour):

* `evaluate_scenario(..., best_bd_stop=None)` passes Gurobi `BestBdStop` through `run_ilp_case` (status
  `USER_OBJ_LIMIT`) and stores `best_bd_stop` and `bound` on the row.
* `ILPModel.solve` records `ObjBound` in `stats['bound']` also when `SolCount = 0` (today it is set to `None`), so
  that a stopped or timed-out solve without incumbent keeps its lower bound (C4). Statistics only; no E2 row
  changes and existing results are unchanged.
* An O2-side reuse rule takes a cached row when it is OPTIMAL, or when `row.bound - row.C_setup >= need_s`.
  Otherwise it re-solves with the cached schedule as `warm` MIP start.
* This deliberately does NOT use `evaluate(..., bound, best)` pruning, which accumulates incumbent `opex` (upper
  values). The certificate needs lower values.

### 4.3 Escalation and stopping

**Escalation.** If the master proposes a layout that is already priced, the binding bounds are its TIME_LIMIT or
stopped scenario bounds. Re-price the scenario with the weakest `lb_s` with `TimeLimit x 3` (cap 1800 s,
`Threads 6`, MIP start from the cache). At the cap the layout is marked `UNRESOLVED`; it stays in the master with
its bounds, and the remaining gap is reported. It is never cut off.

**Stopping rule per budget `m`.** `gap_m = (UB_m - LB_m) / UB_m <= 0.25 %`, or the wall budget of the run is
exhausted, or 3 consecutive rounds bring no new proposal for `m`.

* A budget is **certified** when it stops on the gap.
* Final polish for every budget: re-price the best layout and every layout whose `LBIP`-based value is within the
  gap with `TimeLimit 1800 s`. In round 5 the TIME_LIMIT gaps were 0.4-2.75 % at 300 s, and those gaps floor the
  certificate.

**Coverage statement** (replaces "search_complete"): at termination every admissible layout `lambda` is either
priced, or has master value `>= UB_m - tol` under valid cuts. For `m <= 2` (90 and 17,340 Manhattan layouts) this
is also verified by brute force: the cut envelope of every enumerated layout is evaluated with numpy (17,340
layouts x a few thousand cuts take seconds). This lists the layouts that are still open when the wall budget stops
a run. For `m = 3, 4` (1.2 M and 52.7 M layouts) only `LB_m` and `gap_m` are reported.

---

## 5. LP-based relax-and-round screen

**Input.** Per budget, the LP-phase point `x*_m` (`w*`, hence `y*`, `B*`, `C*`) and the subproblem solutions at
`x*_m` (2.2): swap volume `S_j*`, terminal flow, charging `c_j*`, loads shipped and received per object, averaged
over scenarios with `p_s`.

**Rounding on usage, not on `y`** (reading_to_model O2):

1. Location score `sigma_l = sum_r (S*_(l,r) + term*_(l,r))`, ties broken by `sum_r y*_(l,r)`.
2. Number of sites `k in {k* - 1, k*, k* + 1}`, `k* = round(sum_l sum_r y*_(l,r))`, clipped to `[1, m]`. Take the
   top-`k` locations by `sigma_l`.
3. Role per chosen location:
   * `SC` if the charging use `c*_l >= 0.5` battery-steps per window and swaps `> 0`;
   * `S` if swaps `> 0` and no charging, admissible only with another charge-capable site;
   * `C` if no swaps but `z` shipped `> 0`;
   * otherwise `argmax_r y*_(l,r)`.
4. Sizes, conditional on open:
   * `B in {floor(B*_l / y*_l), ceil(B*_l / y*_l)}` and also `ceil(peak net full-battery draw at l)` from the LP
     stock path `n_{lL t}`;
   * `C = ceil(C*_l / y*_l)`, raised to `ceil(max_t sum_q c*_{l q t})`;
   * all snapped to the nearest menu option.
5. Keep admissible combinations within `Budget_m`. If over budget, reduce the size with the smallest cut-slope
   value per USD (`beta^B`, `beta^C`) until it fits.

**Ranking:**

1. cut envelope `max_cuts` (instant);
2. Q^LP of the top 10 through the persistent LPs (seconds to a minute each);
3. exact pricing of the top 3 (4.2).

The results become incumbents and cuts. This replaces the warm-start role the baseline-policy screen played
badly: the screen mis-ranked roles and sizes, and M08 was never screened.

**As the screen of the greedy** (`greedy_local_search`): add `screen='baseline'|'lp'|callable` (default
`'baseline'`, unchanged). The `'lp'` screen ranks moves by cut envelope, then Q^LP, keeping `k_screen` per added
role as before. The greedy stays a heuristic; certification comes only from section 3. With the O2 loop available
the greedy is optional; it is kept for comparison with round 5.

---

## 6. Expected sizes, run times and memory

These are estimates from the cached runs. Step 0 of section 8 measures them without solving.

Sources:

* O1 aggregation ratio 6.3 on nyc4h / usd4h (`outputs/r5_o1_validation/summary.csv`);
* round-5 aggregated rows: 44-109 k binaries and 18-33 k rows at 1-4 open sites on 1.3-2.5 M per-bike
  `open_sites` arcs, solve medians 27-113 s (`r5_x6_manhattan/cache/index.jsonl`);
* E9.1 all-candidates libraries 0.63-0.85 M per-bike arcs, superset LP 24-29 s per scenario;
* the E9 integrated model 5.35 M per-bike variables for 12 candidates x 3 scenarios.

| quantity | Midtown validation (E9.1) | Midtown full (`nyc4h_stress2`, 12 cand.) | Manhattan `r5_manhattan` |
|---|---|---|---|
| candidates x roles = objects | 4 x {S, SC} = 8 | 12 x 3 = 36 | 15 x 3 = 45 |
| scenarios, bikes, H, L | 2, 6, 48, 12 | 3, 6, 48, 12 | 3, 8, 48, 24 |
| menu options per location / master binaries | 4 / 16 | 11 / 132 | 14 / 210 |
| admissible layouts | 8 (m = 1) | (not needed) | 90 / 17,340 / 1.20 M / 52.7 M (m = 1..4) |
| per-bike template arcs per scenario | 0.63-0.85 M | ~1.8 M | 2-3 M |
| services (all charge-swap object pairs, <= 8 departures) | ~250 | ~5-6 k | ~7-11 k (1,470 ordered object pairs) |
| LP columns per scenario (aggregated `X` + `n, c` + `h, z`) | 0.12-0.18 M | 0.35-0.5 M | 0.5-0.9 M (`z` alone ~0.25 M: 25 levels per service) |
| LP rows per scenario | 25-40 k | 100-150 k | 0.2-0.3 M |
| first LP (barrier + crossover, 3 threads) | 2-10 s | 20-90 s | 60-300 s |
| warm dual-simplex re-solve | < 2 s | 5-30 s | 10-120 s |
| ILP pricing per scenario (all_candidates sub-library) | cached (E9.1) / 25-300 s | 11-150 s | 30-300 s, TIME_LIMIT at 300 s in about 20 % (round 5: 19 of 87) |
| memory | ~2 GB | ~6-8 GB | 9-14 GB peak (below) |

Memory, Manhattan: per scenario the per-bike template library (2-3 M `Arc` objects plus indexes, about 1-1.5 GB
in Python), the `AggregatedNetwork`, and the persistent LP (gurobipy model plus Python `Var` maps, about 1-2 GB).
Three scenarios come to 6-10 GB, plus one pricing ILP (2-3 GB), for 9-14 GB of the machine's 24 GB. Hence:

* one target LP set at a time (the target switch of 2.1 avoids a second set);
* `keep_libraries = 2` in the evaluator;
* the run starts only after the round-6 lanes have exited.

Per-iteration cost, Manhattan:

* LP phase: one round = 3 re-solves in parallel, 0.5-2 min. 40-80 rounds per budget make 1-3 h for four budgets
  with shared cuts. Later budgets start from earlier cuts and need fewer rounds.
* Integer phase: master solves take seconds. A proposal costs 3 LP re-solves (1-2 min) plus, if it survives the LP
  test, 3 pricings (2-15 min, shortened by `BestBdStop`).
* The run time is driven by the number of priced layouts `N_p`: about `N_p x 6` min.

Expected `N_p`:

* `m = 1`: at most 90 (exhaustive worst case, about 9 h). With LP pruning, 10-40 expected.
* `m = 2`: 30-150 if the fixed-layout LP gap is at most 0.5 %. Several hundred if it is 1-2 %, then S2 is needed
  and certification within one night is unlikely.
* `m = 3, 4`: the gap is reported; certification only if the LP gap is small and the optimum is a 1-2-site layout
  (the Midtown pattern).

Thread plan, after the lanes:

* 3 LP worker threads (`ThreadPoolExecutor`; gurobipy releases the GIL in `optimize`), `Threads 3` each;
* pricing `Threads 3` in the same process;
* total at most 12.

---

## 7. Validation plan

### 7.1 Unit tests (`tests/test_o2_benders.py`, toy, `Threads 1`, seconds; allowed now)

Scenarios: `toy_base_instance(0)`, `toy_base_instance(1)`, `TOY_SPEC`, two candidates, a box toy menu (every
role's sizes a product of ranges, so that `integrated_stochastic_ilp` with `size_bounds` is the extensive form, C11).

* (a) **Dual identities.** Copies have `|RC| <= 1e-6`, and the explicit `beta` of 2.2 (from `keep_rows`) equals
  the fixing-row `Pi`. The safe value satisfies `0 <= Qt(xhat) - Qs(xhat) <= 1e-6`.
* (b) **Cut validity on every pair.** For all toy layouts `xhat`, `x` and both targets, with the safe cuts of 2.2,
  `l_xhat(x) <= Qt(x)` with no tolerance (the prototype, with `ObjVal`-based cuts: 27,378 pairs, 0 violations at
  1e-6). Also at 20 random fractional points of the menu hull, which must all be LP-feasible (C2).
* (b2) **Safe cut under perturbed duals.** Perturb `Pi` by random noise of 1e-3 and check that the safe cut is still
  `<= Qt(x)` at every toy layout (weak duality does not need optimal duals).
* (c) **Template equals layout instance.** At every integer layout, the template LP with fixed `y` (elastic columns
  at zero) equals the LP of `layout_instance` on `subset_library` (aggregated and per-bike,
  `build_model(...).model.relax()`, OPEX objective), within 1e-7 (argument: C12).
* (d) **`Q^LP <= Q^IP`** at every layout. Also `Qt(relaxed) <= Qt(written)`.
* (d2) **Row semantics (C3).** For every priced toy row, `row.bound - row.C_setup <= row.opex` and
  `row.C_setup = Layout.allocated_cost(spec)`; the integer cuts use `bound - C_setup`.
* (e) **Exactness.** The Benders loop at budgets 130 and 260 (toy) returns the exhaustive optimum
  (`bilevel.exhaustive`) and the `integrated_stochastic_ilp` optimum to 1e-6, with `LB <= optimum`, final
  `gap = 0` and every layout covered (4.3 brute-force check). A second run with an artificially large `UB_4` checks
  that the pruning test of 3.8 never skips a layout that is optimal at a smaller budget (C5).
* (f) **LP phase equals the extensive LP.** At convergence on the toy, the LP-phase bound WITHOUT the
  `theta_s >= LB^sup` rows equals the LP relaxation of the extensive form with menu-hull rows and the same
  artificial and slack columns, within 1e-5 (C15).
* (g) **Infeasibility handling.** Terminal-infeasible and IP-infeasible toy layouts get the 2.4 (c) cuts and are
  never returned as incumbents; relaxed no-goods appear in the written pool, written no-goods never in the relaxed
  pool. The artificial and slack totals are 0 at every LP-feasible layout (toy `M_el` above every dual).
* (g2) **S2 family cut (if implemented).** For every toy family and every member `x`,
  `LBF_s - sigma_F(x) <= Q_s^IP(x)` (C6).
* (h) **Cache keys.** The keys and the cut-pool signature change when the toy is repriced
  (`costs.reprice_orders(P=...)`) and when the target changes. Existing evaluator keys are unchanged.
* (i) **Default paths unchanged.** `ilp.build_model` is byte-identical (`keep_rows=False`). The full suite (332
  tests) stays green, and `e1_toy.py` still gives 12.5 / 11.2 / 106.

### 7.2 Midtown E9.1 reproduction (old prices; after the lanes)

**Configuration identical to `e9_bilevel_siting.py --validate`:**

* family `nyc4h_stress2`, candidates L01-L04, seeds 0 and 1, `p = 1/2`, 6 bikes, budget `m = 1`;
* `VALIDATION_GRID` (S: B 1 or 2; SC: B 1 or 2, C 1), roles {S, SC}, `s_needs_charge=True`;
* `reposition='all_candidates'`, written targets, `usd_sunk`;
* evaluator `aggregate=False` and `cache_dir=outputs/o2_siting/midtown_cache`, a copy of
  `outputs/e9_bilevel/cache` (C14), so the 14 E9.1 pricings are reused (keys unchanged while `CACHE_VERSION =
  'e9-2'` and the prices are the generated ones) and the E9 cache is never written. At most 4 new ILP solves are
  needed (the 2 layouts that E9.1 pruned).
* the integer cuts read `bound - C_setup` from the cached rows (C3); the E9.1 rows are per-bike, which bounds the
  same optimum as the aggregated LP cuts.

**Expected:**

* the 8 admissible layouts;
* `UB = 676.223` at `L02:SC:B2:C1`;
* the LP-phase bound between the superset value (minimum setup `SC:B1:C1` 12.44 + `(666.30 + 631.76)/2` = 661.5)
  and 676.2, compared with the integrated-model bound 668.04;
* final `LB` limited by the TIME_LIMIT pricing bounds of E9.1 (about 671.1 at 300 s, `RESULTS_E9.md` 3.8).

**Acceptance:**

* same layout (or a layout tied within its pricing gaps, reported) and `UB = 676.223` within 1e-6;
* `LB <= 676.223 + 1e-6` and `LB >= 661.5`.

**Optional:** with the polish step of 4.3 (TimeLimit 1800 s on the 5 TIME_LIMIT rows) the gap should close below
0.25 %, which certifies the E9.1 optimum. That was not possible in round 4.

**Random-layout checks (pure LP, cheap).**

* Draw 30 random admissible layouts of the full Midtown menu (12 candidates, 3 roles, `m <= 2`, seeds 0-2).
* For each, solve the LP of the layout instance directly (`build_model(layout_inst, subset_lib,
  fixed_facilities=True).model.relax()` with the objective `objective - components['C_setup']`, as in
  `superset_bound`, independent of the Benders code).
* Check that every cut in the pool satisfies `cut(x) <= Q^LP(x) + 1e-6 max(1, |Q|)`.
* For layouts with a cached E9 ILP row (same pricing convention, `reposition = all_candidates`), also check
  `Q^LP <= row.bound - row.C_setup` (both OPEX only).
* Report the maximum violation (must be at most 0) and the distribution of the fixed-layout LP gap.

### 7.3 Size check

`o2 size` builds templates, the aggregated networks and the LP models, prints the column, row and nonzero counts
and the RSS, and solves nothing. It runs on Midtown and Manhattan before any production run.

---

## 8. Manhattan run plan (new prices; after the round-6 lanes finish)

**Instance.**

* Family `r5_manhattan`, 15 lattice candidates, 6 entry-point depots, 8 bikes, 40 orders, `H = 48`, `L = 24`.
* Scenarios = seeds 0-2, `p = 1/3`, repriced with `R6_PRICING` (P 60, w 18, v 15).
* Family menu `SIZE_MENUS['r5_manhattan']` (S: B 1-4; C: C 2 or 4; SC: B 1-4 x C 1-2). Not the reduced X6 menu;
  the X6-menu optimum is reported as a sub-result by restricting the master.
* Budgets `m = 1..4` x 52,150 USD. `s_needs_charge = True`. No access row; [U4] at `D = 14` blocks is a
  sensitivity if time remains.

**Steps** (`experiments/o2_siting_bound.py`, sub-commands `size`, `validate`, `run`, `--analyse`; append-only
`records.jsonl`, `cuts.jsonl`, `WallBudget`, resume from the pool and the cache):

0. `size`: the 7.3 check on Manhattan; abort if peak RSS > 16 GB (then fall back to two scenarios in memory at a
   time with rebuilds).
1. Superset bound under the new prices (`superset_bound('lp')`, 3 LPs).
2. Warm start, relaxed targets: price the CSCD / CSTC / CSAV layouts of all budgets, the round-5 layout and the
   present-day proxy. That is about 9-11 distinct layouts x 3 scenarios, roughly 1-1.5 h.
3. **Measurement gate.** For the warm-start layouts compare `Q^LP` with the exact ILP values. Fixed-layout LP gap
   `g = median (Q_IP - Q_LP)/Q_IP`:
   * `g <= 0.5 %`: default design;
   * `0.5 % < g <= 2 %`: switch on S1 and S2 and expect certification at `m = 1, 2` only;
   * `g > 2 %`: certify `m = 1` (90 layouts, exhaustive pricing with LP ordering) and report bounds for
     `m >= 2`.
   The gate result is written to `RESULTS.md`.
4. Relaxed targets: LP phase (all budgets), relax-and-round, integer phase. Wall budget 9 h.
5. Written targets: switch the LPs (2.1), seed the pool with the relaxed cuts (valid lower bounds), re-price the
   incumbents and warm-start layouts with written targets (relaxed schedules as MIP starts, as X6 did in reverse).
   LP phase, integer phase. Wall budget 10 h.
6. Polish (4.3) for the best layout per budget and target; brute-force coverage check for `m <= 2`; final
   tables.

**Reporting** (`outputs/o2_siting/RESULTS.md`, brief and skimmable, problems flagged first):

* **Table 1, per target and budget:** best layout, inv, UB, LB, gap %, certified yes or no, `LB_LP` (two-stage LP
  bound), superset bound, layouts priced, LP-pruned, bound-stopped, ILP solves (OPTIMAL / TIME_LIMIT /
  USER_OBJ_LIMIT), LP solves, wall time, and the served share of the best layout (flagged if below 0.5, the old
  guard).
* **Table 2, comparison per budget and target:**
  * CSCD / CSTC / CSAV and the present-day proxy (capacity-matched to the O2 best layout; to CSAV at `m = 1`) with
    their exact V under the same convention and prices;
  * the regret interval `[V_rule - UB, V_rule - LB]` in USD and %, i.e. how much better any layout can be;
  * the round-5 layout `M06:SC:B4:C2|M12:S:B3:C0` and the round-5 claim "bi-level beats rules": now decided by
    the interval, not by a truncated search.
* **Table 3, coverage:** the cut-envelope brute force for `m <= 2` (layouts open at stop, if any), the LP-gap gate
  value, escalations, `UNRESOLVED` layouts.
* **Caveats** under every table:
  * PRUNING_NYC upper-bound statement;
  * the all-candidates convention (values not comparable one to one with round-5 `open_sites` numbers);
  * three scenarios;
  * certificates hold for this scenario set and library only.

Under the ILP follower the O2 best layout is also cross-evaluated with rule r2 and the selfish follower
(`cross_evaluate`, cheap). Non-ILP followers have no LP and are outside the certificate.

---

## 9. Implementation checklist

1. `ilp.py`: `ILPModel(..., keep_rows=False)`, and `build_submodel(keep_rows=...)`. With the flag on, `add()`
   stores `(family, label, Constr)`. Default path byte-identical (test 7.1 (i)). `ILPModel.solve` also records
   `ObjBound` when `SolCount = 0` (C4; statistics only).
2. `bilevel.py`:
   * `LowerLevelEvaluator.evaluate_scenario(..., best_bd_stop=None)` (BestBdStop outside the cache key; row
     fields `best_bd_stop`, `bound`; the caller passes `need_s + C_setup`, C3);
   * `greedy_local_search(screen='baseline'|'lp'|callable)`, default unchanged.
3. New `benders.py` (gurobipy imported lazily, like `bilevel.py`):
   * `MenuEncoding`;
   * `ScenarioLP` (construction 2.1 with the artificial columns and bounded slacks of 2.4 (a), `solve(r) ->
     (Qt, Qs, c0, beta, slack, usage)` with the safe Lagrangian cut of 2.2, `set_target`, `audit()`, build-time
     assertions of 1.2);
   * `Cut`, `CutPool` (2.2, 3.4, 2.4 (c), 3.7);
   * `Master` (3.1-3.3, `solve(budget, relax=False)`, `envelope(layouts)`);
   * `price_layout` (4.2);
   * `relax_and_round` (5);
   * `benders_siting(evaluator, candidates, budgets, size_menu, roles, warm_layouts, access=None,
     s_needs_charge=True, wall=None, tol=...)` (3.8), returning per-budget records.
4. `experiments/o2_siting_bound.py` (sub-commands of section 8, `--smoke` on the toy, `--dry-run`).
5. `tests/test_o2_benders.py` (7.1).
6. Documentation:
   * `notes/DECISIONS.md` entry "O2 conventions": all-candidates pricing for certificates, elastic (artificial
     and slack) columns in the bound LP only, safe Lagrangian cuts, `bound - C_setup` as the scenario lower bound,
     `M_el = 1e4`, tol 0.25 %, nested budgets, one-way relaxed -> written cut import;
   * `reading_to_model.md` O2 status line.
   English only in every file.

**Risks** (to be reported, not hidden):

1. Fixed-layout LP gap larger than the spread between layouts. Then many pricings and an uncertified gap at
   `m >= 2`. The gate in step 3 detects it early, and S1/S2 are the mitigation.
2. TIME_LIMIT pricing bounds floor the certificate (round 5: 0.4-2.75 %). Mitigated by the polish step.
3. Memory on Manhattan (9-14 GB). Mitigated by the size check and running alone.
4. Degenerate duals giving flat cuts at closed objects. Mitigated by in-out stabilisation, and by the integer cuts,
   which do not depend on dual quality.
5. The elastic constant `M_el` too small for an exact penalty. That does not affect validity (only bound
   strength), and the slack is monitored.
6. Pricing rows without incumbent (`NO_INCUMBENT`, e.g. a rejected written-target MIP start and an early
   BestBdStop). They keep their `ObjBound` after C4 but give no `UB`; they are escalated like TIME_LIMIT rows.
