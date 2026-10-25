# O2 certified siting -- manhattan

Records `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/manhattan/records.jsonl`; cut pool `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/manhattan/cuts.jsonl`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/manhattan/cache`.  Generated 2026-10-19 11:18.

## Problems (read first)

* relaxed, m = 1: NOT certified (gap inf %, stop: wall).
* relaxed, m = 1: 3 layouts still open at stop (brute-force check; 1 of them priced with open ILP gaps).
* relaxed: artificial columns active in some LP (max 5.0000 bikes): the bound LP is elastic at some (fractional or infeasible) points; validity unaffected.
* relaxed, m = 2: NOT certified (gap inf %, stop: wall).
* relaxed, m = 2: 16806 layouts still open at stop (brute-force check; 1 of them priced with open ILP gaps).
* relaxed, m = 3: NOT certified (gap inf %, stop: wall).
* relaxed, m = 4: NOT certified (gap inf %, stop: wall).
* written, m = 1: NOT certified (gap inf %, stop: wall).
* written, m = 1: 6 layouts still open at stop (brute-force check; 2 of them priced with open ILP gaps).
* written: artificial columns active in some LP (max 5.5000 bikes): the bound LP is elastic at some (fractional or infeasible) points; validity unaffected.
* written, m = 2: NOT certified (gap inf %, stop: wall).
* written, m = 2: 16794 layouts still open at stop (brute-force check; 1 of them priced with open ILP gaps).
* written, m = 3: NOT certified (gap inf %, stop: wall).
* written, m = 4: NOT certified (gap inf %, stop: wall).

## Table 1 -- certified bound per target and budget

UB = best feasible V found (exact up to the MIP gaps of its rows; ILP follower, all-candidates library); LB = master bound (valid lower bound on V*_m); gap = (UB - LB) / UB; LB_LP = LP-phase master bound; superset = min setup + superset LP bound.  Counters (priced ... LP solves, wall) are per target run, shared by its budgets.

| target | m | best layout | inv USD | UB | LB | gap % | certified | LB_LP | superset | priced | LP-pruned | bound-stopped | infeasible | ILP solves by status | LP solves | wall min | served share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | 1.000 | M09:SC:B3:C2 | 52,150.000 | 1,052.995 | - | inf | no | - | 662.386 | 5 | 0 | 9 | 0 | OPTIMAL 28, SKIPPED_BUDGET 3, TIME_LIMIT 7, USER_OBJ_LIMIT 2 | 183 | 538.858 | 0.783 |
| relaxed | 2.000 | M08:SC:B3:C2|M09:SC:B3:C2 | 104,300.000 | 700.113 | - | inf | no | - | 662.386 | 5 | 0 | 9 | 0 | OPTIMAL 28, SKIPPED_BUDGET 3, TIME_LIMIT 7, USER_OBJ_LIMIT 2 | 183 | 538.858 | 0.983 |
| relaxed | 3.000 | M08:SC:B3:C2|M09:SC:B3:C2 | 104,300.000 | 700.113 | - | inf | no | - | 662.386 | 5 | 0 | 9 | 0 | OPTIMAL 28, SKIPPED_BUDGET 3, TIME_LIMIT 7, USER_OBJ_LIMIT 2 | 183 | 538.869 | 0.983 |
| relaxed | 4.000 | M08:SC:B3:C2|M09:SC:B3:C2 | 104,300.000 | 700.113 | - | inf | no | - | 662.386 | 5 | 0 | 9 | 0 | OPTIMAL 28, SKIPPED_BUDGET 3, TIME_LIMIT 7, USER_OBJ_LIMIT 2 | 183 | 538.869 | 0.983 |
| written | 1.000 | M08:SC:B3:C2 | 52,150.000 | 1,132.394 | - | inf | no | - | 662.386 | 7 | 0 | 7 | 0 | OPTIMAL 21, SKIPPED_BUDGET 2, TIME_LIMIT 16, USER_OBJ_LIMIT 1 | 168 | 599.317 | 0.733 |
| written | 2.000 | M08:SC:B3:C2|M09:SC:B3:C2 | 104,300.000 | 706.262 | - | inf | no | - | 662.386 | 7 | 0 | 7 | 0 | OPTIMAL 21, SKIPPED_BUDGET 2, TIME_LIMIT 16, USER_OBJ_LIMIT 1 | 168 | 599.317 | 0.983 |
| written | 3.000 | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 156,450.000 | 703.606 | - | inf | no | - | 662.386 | 7 | 0 | 7 | 0 | OPTIMAL 21, SKIPPED_BUDGET 2, TIME_LIMIT 16, USER_OBJ_LIMIT 1 | 168 | 599.330 | 0.983 |
| written | 4.000 | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 156,450.000 | 703.606 | - | inf | no | - | 662.386 | 7 | 0 | 7 | 0 | OPTIMAL 21, SKIPPED_BUDGET 2, TIME_LIMIT 16, USER_OBJ_LIMIT 1 | 168 | 599.330 | 0.983 |

## Table 2 -- rule, present-day and round-5 layouts against the certified bound

Regret interval [V_rule - UB, V_rule - LB]: how much worse the rule layout is than the best found (lower end) and than any layout can be at most (upper end).  diff = V_rule - V_best with the exact-t 95 % CI over the scenarios (paired OPEX differences; uniform p).

| target | m | layout rule | layout | V | status | regret lo | regret hi | lo % | hi % | V_rule - V_best | CI lo | CI hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | 1.00 | CSAV | M08:SC:B3:C2 | 1,070.07 | PRICED | 17.08 | - | 1.60 | - | 17.08 | -19.08 | 53.23 |
| relaxed | 1.00 | CSCD | M09:SC:B3:C2 | 1,052.99 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| relaxed | 1.00 | CSTC | M09:SC:B3:C2 | 1,052.99 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| relaxed | 1.00 | present_day | M08:SC:B3:C2 | 1,070.07 | PRICED | 17.08 | - | 1.60 | - | 17.08 | -19.08 | 53.23 |
| relaxed | 2.00 | CSAV | M08:SC:B3:C2|M14:SC:B3:C2 | 740.04 | PRICED | 39.92 | - | 5.39 | - | 39.92 | -22.20 | 102.05 |
| relaxed | 2.00 | CSCD | M08:SC:B3:C2|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| relaxed | 2.00 | CSTC | M08:SC:B3:C2|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| relaxed | 2.00 | present_day | M03:SC:B2:C1|M08:SC:B4:C3 | 714.37 | PRICED | 14.26 | - | 2.00 | - | 14.26 | -20.90 | 49.41 |
| relaxed | 2.00 | round5:M06:SC:B4:C2|M12:S:B3:C0 | M06:SC:B4:C2|M12:S:B3:C0 | 706.82 | PRICED | 6.71 | - | 0.95 | - | 6.71 | -11.92 | 25.33 |
| relaxed | 2.00 | round5:M08:SC:B3:C2|M09:SC:B3:C2 | M08:SC:B3:C2|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| relaxed | 3.00 | CSAV | M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2 | 706.72 | PRICED | 6.60 | - | 0.93 | - | 6.60 | -19.73 | 32.94 |
| relaxed | 3.00 | CSCD | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2 | 702.88 | PRICED | 2.76 | - | 0.39 | - | 2.76 | -15.74 | 21.26 |
| relaxed | 3.00 | CSTC | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 701.66 | PRICED | 1.55 | - | 0.22 | - | 1.55 | -14.67 | 17.77 |
| relaxed | 3.00 | present_day | M03:SC:B2:C1|M08:SC:B4:C3 | 714.37 | PRICED | 14.26 | - | 2.00 | - | 14.26 | -20.90 | 49.41 |
| relaxed | 3.00 | round5:M06:SC:B4:C2|M12:S:B3:C0 | M06:SC:B4:C2|M12:S:B3:C0 | 706.82 | PRICED | 6.71 | - | 0.95 | - | 6.71 | -11.92 | 25.33 |
| relaxed | 3.00 | round5:M08:SC:B3:C2|M09:SC:B3:C2 | M08:SC:B3:C2|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| relaxed | 4.00 | CSAV | M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2 | - | SKIPPED_BUDGET | - | - | - | - | - | - | - |
| relaxed | 4.00 | CSCD | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2 | - | SKIPPED_BUDGET | - | - | - | - | - | - | - |
| relaxed | 4.00 | CSTC | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | - | SKIPPED_BUDGET | - | - | - | - | - | - | - |
| relaxed | 4.00 | present_day | M03:SC:B2:C1|M08:SC:B4:C3 | 714.37 | PRICED | 14.26 | - | 2.00 | - | 14.26 | -20.90 | 49.41 |
| relaxed | 4.00 | round5:M06:SC:B4:C2|M12:S:B3:C0 | M06:SC:B4:C2|M12:S:B3:C0 | 706.82 | PRICED | 6.71 | - | 0.95 | - | 6.71 | -11.92 | 25.33 |
| relaxed | 4.00 | round5:M08:SC:B3:C2|M09:SC:B3:C2 | M08:SC:B3:C2|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| written | 1.00 | CSAV | M08:SC:B3:C2 | 1,132.39 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| written | 1.00 | CSCD | M09:SC:B3:C2 | 1,151.96 | PRICED | 19.56 | - | 1.70 | - | 19.56 | -104.76 | 143.89 |
| written | 1.00 | CSTC | M09:SC:B3:C2 | 1,151.96 | PRICED | 19.56 | - | 1.70 | - | 19.56 | -104.76 | 143.89 |
| written | 1.00 | present_day | M08:SC:B3:C2 | 1,132.39 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| written | 2.00 | CSAV | M08:SC:B3:C2|M14:SC:B3:C2 | 752.74 | PRICED | 46.48 | - | 6.17 | - | 46.48 | -11.68 | 104.63 |
| written | 2.00 | CSCD | M08:SC:B3:C2|M09:SC:B3:C2 | 706.26 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| written | 2.00 | CSTC | M08:SC:B3:C2|M09:SC:B3:C2 | 706.26 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| written | 2.00 | present_day | M03:SC:B2:C1|M08:SC:B4:C3 | 732.84 | PRICED | 26.58 | - | 3.63 | - | 26.58 | -26.91 | 80.07 |
| written | 2.00 | round5:M06:SC:B4:C2|M12:S:B3:C0 | M06:SC:B4:C2|M12:S:B3:C0 | 802.43 | PRICED | 96.16 | - | 11.98 | - | 96.16 | 25.10 | 167.23 |
| written | 2.00 | round5:M08:SC:B3:C2|M09:SC:B3:C2 | M08:SC:B3:C2|M09:SC:B3:C2 | 706.26 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| written | 3.00 | CSAV | M02:SC:B3:C2|M08:SC:B3:C2|M14:SC:B3:C2 | 711.28 | PRICED | 7.68 | - | 1.08 | - | 7.68 | -3.93 | 19.28 |
| written | 3.00 | CSCD | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2 | 705.74 | PRICED | 2.14 | - | 0.30 | - | 2.14 | -0.38 | 4.65 |
| written | 3.00 | CSTC | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | 703.61 | PRICED | 0.00 | - | 0.00 | - | 0.00 | 0.00 | 0.00 |
| written | 3.00 | present_day | M03:SC:B3:C2|M04:SC:B2:C1|M08:SC:B4:C3 | 716.75 | PRICED | 13.14 | - | 1.83 | - | 13.14 | -11.77 | 38.06 |
| written | 3.00 | round5:M06:SC:B4:C2|M12:S:B3:C0 | M06:SC:B4:C2|M12:S:B3:C0 | 802.43 | PRICED | 98.82 | - | 12.32 | - | 98.82 | 48.49 | 149.15 |
| written | 3.00 | round5:M08:SC:B3:C2|M09:SC:B3:C2 | M08:SC:B3:C2|M09:SC:B3:C2 | 706.26 | PRICED | 2.66 | - | 0.38 | - | 2.66 | -19.08 | 24.39 |
| written | 4.00 | CSAV | M02:SC:B3:C2|M08:SC:B3:C2|M11:SC:B3:C2|M14:SC:B3:C2 | - | SKIPPED_BUDGET | - | - | - | - | - | - | - |
| written | 4.00 | CSCD | M08:SC:B3:C2|M09:SC:B3:C2|M10:SC:B3:C2|M11:SC:B3:C2 | 714.50 | PRICED | 10.89 | - | 1.52 | - | 10.89 | 2.07 | 19.72 |
| written | 4.00 | CSTC | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2|M13:SC:B3:C2 | - | SKIPPED_BUDGET | - | - | - | - | - | - | - |
| written | 4.00 | present_day | M03:SC:B3:C2|M04:SC:B2:C1|M08:SC:B4:C3 | 716.75 | PRICED | 13.14 | - | 1.83 | - | 13.14 | -11.77 | 38.06 |
| written | 4.00 | round5:M06:SC:B4:C2|M12:S:B3:C0 | M06:SC:B4:C2|M12:S:B3:C0 | 802.43 | PRICED | 98.82 | - | 12.32 | - | 98.82 | 48.49 | 149.15 |
| written | 4.00 | round5:M08:SC:B3:C2|M09:SC:B3:C2 | M08:SC:B3:C2|M09:SC:B3:C2 | 706.26 | PRICED | 2.66 | - | 0.38 | - | 2.66 | -19.08 | 24.39 |

## Table 3 -- fixed-layout LP gap (measurement gate) and coverage

(Q_IP - Q_LP) / Q_IP over the scenario cells of every fully priced layout (Q_LP = safe Benders value).

| target | cells | median % | max % | exact cells % | gate |
|---|---|---|---|---|---|
| relaxed | 24 | 1.059 | 5.331 | 0.000 | S1/S2 needed |
| written | 27 | 1.337 | 14.388 | 0.000 | S1/S2 needed |

| target | m | brute-force checked | layouts | open at stop | of which priced (open gaps) | stuck layouts | exploration proposals | note |
|---|---|---|---|---|---|---|---|---|
| relaxed | 1.00 | yes | 90 | 3 | 1 | 0 | 0 | - |
| relaxed | 2.00 | yes | 17,340 | 16,806 | 1 | 0 | 0 | - |
| relaxed | 3.00 | no | - | - | - | 0 | 0 | about 1269310 layouts |
| relaxed | 4.00 | no | - | - | - | 0 | 0 | about 53707150 layouts |
| written | 1.00 | yes | 90 | 6 | 2 | 0 | 0 | - |
| written | 2.00 | yes | 17,340 | 16,794 | 1 | 0 | 0 | - |
| written | 3.00 | no | - | - | - | 0 | 0 | about 1269310 layouts |
| written | 4.00 | no | - | - | - | 0 | 0 | about 53707150 layouts |

Gate records (measured after the warm start, acted on during the run):

* `{"kind": "gate", "target": "relaxed", "n_cells": 6, "median": 0.027024132804360827, "max": 0.04040990188537762, "action": "certify smallest budget by enumeration", "mode": "auto", "wall_clock": "2026-10-18 17:39:40"}`
* `{"kind": "gate_enumeration", "target": "relaxed", "m": 1.0, "done": false, "reason": "wall", "n_layouts": 90, "LB_enum": null, "UB": null, "gap": null, "close_reason": null, "wall_clock": "2026-10-19 00:05:50"}`
* `{"kind": "gate", "target": "written", "n_cells": 12, "median": 0.0453435945576768, "max": 0.08914722949509986, "action": "certify smallest budget by enumeration", "mode": "auto", "wall_clock": "2026-10-19 05:35:54"}`
* `{"kind": "gate_enumeration", "target": "written", "m": 1.0, "done": false, "reason": "wall", "n_layouts": 90, "LB_enum": null, "UB": null, "gap": null, "close_reason": null, "wall_clock": "2026-10-19 10:19:20"}`

## Table 4 -- best layouts under other followers

Same layout, same target; V under the R2.3 policy (`baseline`) and the selfish follower against its ILP value.

| target | layout | follower | V | V (ILP) | status | served share |
|---|---|---|---|---|---|---|
| relaxed | M09:SC:B3:C2 | baseline | 1,834.848 | 1,052.995 | OK | 0.483 |
| relaxed | M09:SC:B3:C2 | selfish | 1,834.848 | 1,052.995 | OK | 0.483 |
| relaxed | M08:SC:B3:C2|M09:SC:B3:C2 | baseline | 1,260.562 | 700.113 | OK | 0.800 |
| relaxed | M08:SC:B3:C2|M09:SC:B3:C2 | selfish | 1,257.163 | 700.113 | OK | 0.783 |
| written | M08:SC:B3:C2 | baseline | 1,873.121 | 1,132.394 | OK | 0.442 |
| written | M08:SC:B3:C2 | selfish | 1,873.121 | 1,132.394 | OK | 0.442 |
| written | M08:SC:B3:C2|M09:SC:B3:C2 | baseline | 1,260.562 | 706.262 | OK | 0.800 |
| written | M08:SC:B3:C2|M09:SC:B3:C2 | selfish | 1,257.163 | 706.262 | OK | 0.783 |
| written | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | baseline | 1,207.131 | 703.606 | OK | 0.833 |
| written | M08:SC:B3:C2|M09:SC:B3:C2|M12:SC:B3:C2 | selfish | 1,046.786 | 703.606 | OK | 0.883 |

## Caveats

* Every ILP value is an upper bound on the unpruned written optimum (PRUNING_NYC); V* is the optimum under the all-candidates library convention (values are not comparable one to one with round-5 `open_sites` numbers).
* Certificates hold for this scenario set (seeds listed in the plan record) and this library only; CIs over three scenarios are wide by construction.
* LB is valid under solver tolerances: LP cuts are safe Lagrangian bounds (C1), integer cuts use Gurobi ObjBound minus C_setup (C3).
