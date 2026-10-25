# O2 certified siting -- midtown_validate

Records `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/midtown_validate/records.jsonl`; cut pool `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/midtown_validate/cuts.jsonl`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/midtown_validate/cache`.  Generated 2026-10-18 15:06.

## Problems (read first)

* written, m = 1: NOT certified (gap 0.75 %, stop: open pricing gaps only (3 priced layouts below UB - tol, escalations used up; every other layout resolved)).
* written, m = 1: 3 layouts still open at stop (brute-force check; 3 of them priced with open ILP gaps).

## Table 1 -- certified bound per target and budget

UB = best feasible V found (exact up to the MIP gaps of its rows; ILP follower, all-candidates library); LB = master bound (valid lower bound on V*_m); gap = (UB - LB) / UB; LB_LP = LP-phase master bound; superset = min setup + superset LP bound.  Counters (priced ... LP solves, wall) are per target run, shared by its budgets.

| target | m | best layout | inv USD | UB | LB | gap % | certified | LB_LP | superset | priced | LP-pruned | bound-stopped | infeasible | ILP solves by status | LP solves | wall min | served share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| written | 1.000 | L02:SC:B2:C1 | 51,300.000 | 676.223 | 671.126 | 0.754 | no | 661.528 | 661.391 | 3 | 1 | 0 | 0 |  | 24 | 1.610 | 0.819 |

## Table 2 -- rule, present-day and round-5 layouts against the certified bound

Regret interval [V_rule - UB, V_rule - LB]: how much worse the rule layout is than the best found (lower end) and than any layout can be at most (upper end).  diff = V_rule - V_best with the exact-t 95 % CI over the scenarios (paired OPEX differences; uniform p).

| target | m | layout rule | layout | V | status | regret lo | regret hi | lo % | hi % | V_rule - V_best | CI lo | CI hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Table 3 -- fixed-layout LP gap (measurement gate) and coverage

(Q_IP - Q_LP) / Q_IP over the scenario cells of every fully priced layout (Q_LP = safe Benders value).

| target | cells | median % | max % | exact cells % | gate |
|---|---|---|---|---|---|
| written | 6 | 1.550 | 1.892 | 0.000 | S1/S2 needed |

| target | m | brute-force checked | layouts | open at stop | of which priced (open gaps) | stuck layouts | exploration proposals | note |
|---|---|---|---|---|---|---|---|---|
| written | 1.00 | yes | 8 | 3 | 3 | 3 | 0 | - |

## Acceptance

* `{"stage": "midtown_validate", "kind": "acceptance", "best_layout": "L02:SC:B2:C1", "UB": 676.2233333333332, "LB": 671.1264898997358, "gap": 0.007537219114391343, "same_layout": true, "tie_within_pricing_gaps": false, "UB_matches": true, "LB_valid": true, "LB_above_superset": true, "integrated_bound_E9": 668.04, "LB_LP": 661.5278285616854, "ok": true, "wall_clock": "2026-10-18 15:06:44"}`

## Caveats

* Every ILP value is an upper bound on the unpruned written optimum (PRUNING_NYC); V* is the optimum under the all-candidates library convention (values are not comparable one to one with round-5 `open_sites` numbers).
* Certificates hold for this scenario set (seeds listed in the plan record) and this library only; CIs over three scenarios are wide by construction.
* LB is valid under solver tolerances: LP cuts are safe Lagrangian bounds (C1), integer cuts use Gurobi ObjBound minus C_setup (C3).
