# O2 certified siting -- manhattan

Records `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/manhattan_pass2/records.jsonl`; cut pool `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/manhattan_pass2/cuts.jsonl`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/manhattan_pass2/cache`.  Generated 2026-10-20 00:17.

## Problems (read first)

* relaxed, m = 2: NOT certified (gap 3.48 %, stop: wall).
* relaxed, m = 2: 7060 layouts still open at stop (brute-force check; 1 of them priced with open ILP gaps).
* relaxed, m = 3: NOT certified (gap 3.48 %, stop: wall).
* relaxed, m = 4: NOT certified (gap 3.48 %, stop: wall).
* written, m = 1: NOT certified (gap 1.46 %, stop: enumerated (open pricing gaps: 1 priced layouts below UB - tol, escalations used up after 7 calls)).
* written, m = 1: 1 layouts still open at stop (brute-force check; 1 of them priced with open ILP gaps).
* written, m = 2: NOT certified (gap 3.39 %, stop: wall).
* written, m = 2: 3140 layouts still open at stop (brute-force check; 0 of them priced with open ILP gaps).
* written: artificial columns active in some LP (max 2.0000 bikes): the bound LP is elastic at some (fractional or infeasible) points; validity unaffected.
* written, m = 3: NOT certified (gap 2.53 %, stop: wall).
* written, m = 4: NOT certified (gap 2.53 %, stop: wall).

## Table 1 -- certified bound per target and budget

UB = best feasible V found (exact up to the MIP gaps of its rows; ILP follower, all-candidates library); LB = master bound (valid lower bound on V*_m); gap = (UB - LB) / UB; LB_LP = LP-phase master bound; superset = min setup + superset LP bound.  Counters (priced ... LP solves, wall) are per target run, shared by its budgets.

| target | m | best layout | inv USD | UB | LB | bound kind | gap % | certified | LB_LP | superset | priced | LP-pruned | bound-stopped | infeasible | ILP solves by status | LP solves | wall min | served share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | 1.000 | M09:SC:B3:C2 | 52,150.000 | 1,052.995 | 1,052.995 | enumeration | 0.000 | yes | - | 662.386 | 11 | 88 | 3 | 0 | OPTIMAL 1 | 6 | 13.024 | 0.783 |
| relaxed | 2.000 | M08:SC:B3:C2\|M09:SC:B3:C2 | 104,300.000 | 700.113 | 675.740 | master | 3.481 | no | 662.391 | 662.386 | 11 | 0 | 3 | 0 | OPTIMAL 5, TIME_LIMIT 2 | 96 | 238.502 | 0.983 |
| relaxed | 3.000 | M08:SC:B3:C2\|M09:SC:B3:C2 | 104,300.000 | 700.113 | 675.740 | master | 3.481 | no | 664.290 | 662.386 | 11 | 0 | 3 | 0 | OPTIMAL 5, TIME_LIMIT 2 | 96 | 238.514 | 0.983 |
| relaxed | 4.000 | M08:SC:B3:C2\|M09:SC:B3:C2 | 104,300.000 | 700.113 | 675.740 | master | 3.481 | no | 664.301 | 662.386 | 11 | 0 | 3 | 0 | OPTIMAL 5, TIME_LIMIT 2 | 96 | 238.514 | 0.983 |
| written | 1.000 | M08:SC:B3:C2 | 52,150.000 | 1,131.800 | 1,115.251 | enumeration | 1.462 | no | - | 662.386 | 12 | 87 | 3 | 0 | OPTIMAL 1, TIME_LIMIT 6, USER_OBJ_LIMIT 1 | 12 | 153.103 | 0.742 |
| written | 2.000 | M04:SC:B2:C2\|M09:SC:B4:C2 | 104,300.000 | 699.957 | 676.240 | master | 3.388 | no | 664.312 | 662.386 | 15 | 72 | 4 | 0 | OPTIMAL 14, TIME_LIMIT 1, USER_OBJ_LIMIT 1 | 315 | 236.927 | 0.983 |
| written | 3.000 | M04:SC:B4:C2\|M09:SC:B4:C2 | 105,200.000 | 693.807 | 676.240 | master | 2.532 | no | 664.319 | 662.386 | 15 | 72 | 4 | 0 | OPTIMAL 14, TIME_LIMIT 1, USER_OBJ_LIMIT 1 | 315 | 236.943 | 0.983 |
| written | 4.000 | M04:SC:B4:C2\|M09:SC:B4:C2 | 105,200.000 | 693.807 | 676.240 | master | 2.532 | no | 664.326 | 662.386 | 15 | 72 | 4 | 0 | OPTIMAL 14, TIME_LIMIT 1, USER_OBJ_LIMIT 1 | 315 | 236.943 | 0.983 |

## Table 2 -- rule, present-day and round-5 layouts against the certified bound

Regret interval [V_rule - UB, V_rule - LB]: how much worse the rule layout is than the best found (lower end) and than any layout can be at most (upper end).  diff = V_rule - V_best with the exact-t 95 % CI over the scenarios (paired OPEX differences; uniform p).

| target | m | layout rule | layout | V | status | regret lo | regret hi | lo % | hi % | V_rule - V_best | CI lo | CI hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | 1.00 | CSAV | M08:SC:B3:C2 | 1,070.07 | PRICED | 17.08 | 17.08 | 1.60 | 1.60 | 17.08 | -19.08 | 53.23 |
| relaxed | 1.00 | CSCD | M09:SC:B3:C2 | 1,052.99 | PRICED | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| relaxed | 1.00 | CSTC | M09:SC:B3:C2 | 1,052.99 | PRICED | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| relaxed | 1.00 | present_day | M08:SC:B3:C2 | 1,070.07 | PRICED | 17.08 | 17.08 | 1.60 | 1.60 | 17.08 | -19.08 | 53.23 |
| relaxed | 2.00 | CSAV | M08:SC:B3:C2\|M14:SC:B3:C2 | 740.04 | PRICED | 39.92 | 64.30 | 5.39 | 8.69 | 39.92 | -22.20 | 102.05 |
| relaxed | 2.00 | CSCD | M08:SC:B3:C2\|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | 24.37 | 0.00 | 3.48 | 0.00 | 0.00 | 0.00 |
| relaxed | 2.00 | CSTC | M08:SC:B3:C2\|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | 24.37 | 0.00 | 3.48 | 0.00 | 0.00 | 0.00 |
| relaxed | 2.00 | present_day | M03:SC:B2:C1\|M08:SC:B4:C3 | 714.37 | PRICED | 14.26 | 38.63 | 2.00 | 5.41 | 14.26 | -20.90 | 49.41 |
| relaxed | 2.00 | round5:M06:SC:B4:C2\|M12:S:B3:C0 | M06:SC:B4:C2\|M12:S:B3:C0 | 706.82 | PRICED | 6.71 | 31.08 | 0.95 | 4.40 | 6.71 | -11.92 | 25.33 |
| relaxed | 2.00 | round5:M08:SC:B3:C2\|M09:SC:B3:C2 | M08:SC:B3:C2\|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | 24.37 | 0.00 | 3.48 | 0.00 | 0.00 | 0.00 |
| relaxed | 3.00 | CSAV | M02:SC:B3:C2\|M08:SC:B3:C2\|M14:SC:B3:C2 | 706.72 | PRICED | 6.60 | 30.98 | 0.93 | 4.38 | 6.60 | -19.73 | 32.94 |
| relaxed | 3.00 | CSCD | M08:SC:B3:C2\|M09:SC:B3:C2\|M10:SC:B3:C2 | 702.88 | PRICED | 2.76 | 27.14 | 0.39 | 3.86 | 2.76 | -15.74 | 21.26 |
| relaxed | 3.00 | CSTC | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2 | 701.66 | PRICED | 1.55 | 25.92 | 0.22 | 3.69 | 1.55 | -14.67 | 17.77 |
| relaxed | 3.00 | present_day | M03:SC:B2:C1\|M08:SC:B4:C3 | 714.37 | PRICED | 14.26 | 38.63 | 2.00 | 5.41 | 14.26 | -20.90 | 49.41 |
| relaxed | 3.00 | round5:M06:SC:B4:C2\|M12:S:B3:C0 | M06:SC:B4:C2\|M12:S:B3:C0 | 706.82 | PRICED | 6.71 | 31.08 | 0.95 | 4.40 | 6.71 | -11.92 | 25.33 |
| relaxed | 3.00 | round5:M08:SC:B3:C2\|M09:SC:B3:C2 | M08:SC:B3:C2\|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | 24.37 | 0.00 | 3.48 | 0.00 | 0.00 | 0.00 |
| relaxed | 4.00 | CSAV | M02:SC:B3:C2\|M08:SC:B3:C2\|M11:SC:B3:C2\|M14:SC:B3:C2 | 712.10 | PRICED | 11.99 | 36.36 | 1.68 | 5.11 | 11.99 | -26.71 | 50.69 |
| relaxed | 4.00 | CSCD | M08:SC:B3:C2\|M09:SC:B3:C2\|M10:SC:B3:C2\|M11:SC:B3:C2 | 713.28 | PRICED | 13.17 | 37.54 | 1.85 | 5.26 | 13.17 | -8.36 | 34.70 |
| relaxed | 4.00 | CSTC | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2\|M13:SC:B3:C2 | 713.42 | PRICED | 13.31 | 37.68 | 1.87 | 5.28 | 13.31 | -1.36 | 27.97 |
| relaxed | 4.00 | present_day | M03:SC:B2:C1\|M08:SC:B4:C3 | 714.37 | PRICED | 14.26 | 38.63 | 2.00 | 5.41 | 14.26 | -20.90 | 49.41 |
| relaxed | 4.00 | round5:M06:SC:B4:C2\|M12:S:B3:C0 | M06:SC:B4:C2\|M12:S:B3:C0 | 706.82 | PRICED | 6.71 | 31.08 | 0.95 | 4.40 | 6.71 | -11.92 | 25.33 |
| relaxed | 4.00 | round5:M08:SC:B3:C2\|M09:SC:B3:C2 | M08:SC:B3:C2\|M09:SC:B3:C2 | 700.11 | PRICED | 0.00 | 24.37 | 0.00 | 3.48 | 0.00 | 0.00 | 0.00 |
| written | 1.00 | CSAV | M08:SC:B3:C2 | 1,131.80 | PRICED | 0.00 | 16.55 | 0.00 | 1.46 | 0.00 | 0.00 | 0.00 |
| written | 1.00 | CSCD | M09:SC:B3:C2 | 1,143.03 | PRICED | 11.23 | 27.78 | 0.98 | 2.43 | 11.23 | -93.02 | 115.47 |
| written | 1.00 | CSTC | M09:SC:B3:C2 | 1,143.03 | PRICED | 11.23 | 27.78 | 0.98 | 2.43 | 11.23 | -93.02 | 115.47 |
| written | 1.00 | present_day | M08:SC:B3:C2 | 1,131.80 | PRICED | 0.00 | 16.55 | 0.00 | 1.46 | 0.00 | 0.00 | 0.00 |
| written | 2.00 | CSAV | M08:SC:B3:C2\|M14:SC:B3:C2 | 752.74 | PRICED | 52.78 | 76.50 | 7.01 | 10.16 | 52.78 | -16.57 | 122.13 |
| written | 2.00 | CSCD | M08:SC:B3:C2\|M09:SC:B3:C2 | 706.26 | PRICED | 6.30 | 30.02 | 0.89 | 4.25 | 6.30 | -9.94 | 22.55 |
| written | 2.00 | CSTC | M08:SC:B3:C2\|M09:SC:B3:C2 | 706.26 | PRICED | 6.30 | 30.02 | 0.89 | 4.25 | 6.30 | -9.94 | 22.55 |
| written | 2.00 | present_day | M03:SC:B2:C1\|M08:SC:B4:C3 | 732.84 | PRICED | 32.88 | 56.60 | 4.49 | 7.72 | 32.88 | -9.00 | 74.76 |
| written | 2.00 | round5:M06:SC:B4:C2\|M12:S:B3:C0 | M06:SC:B4:C2\|M12:S:B3:C0 | 802.43 | PRICED | 102.47 | 126.19 | 12.77 | 15.73 | 102.47 | 37.22 | 167.72 |
| written | 2.00 | round5:M08:SC:B3:C2\|M09:SC:B3:C2 | M08:SC:B3:C2\|M09:SC:B3:C2 | 706.26 | PRICED | 6.30 | 30.02 | 0.89 | 4.25 | 6.30 | -9.94 | 22.55 |
| written | 3.00 | CSAV | M02:SC:B3:C2\|M08:SC:B3:C2\|M14:SC:B3:C2 | 711.28 | PRICED | 17.48 | 35.04 | 2.46 | 4.93 | 17.48 | -5.94 | 40.89 |
| written | 3.00 | CSCD | M08:SC:B3:C2\|M09:SC:B3:C2\|M10:SC:B3:C2 | 705.74 | PRICED | 11.93 | 29.50 | 1.69 | 4.18 | 11.93 | -1.68 | 25.55 |
| written | 3.00 | CSTC | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2 | 703.61 | PRICED | 9.80 | 27.37 | 1.39 | 3.89 | 9.80 | -5.06 | 24.65 |
| written | 3.00 | present_day | M03:SC:B3:C1\|M08:SC:B5:C3 | 707.16 | PRICED | 13.35 | 30.92 | 1.89 | 4.37 | 13.35 | -4.39 | 31.09 |
| written | 3.00 | round5:M06:SC:B4:C2\|M12:S:B3:C0 | M06:SC:B4:C2\|M12:S:B3:C0 | 802.43 | PRICED | 108.62 | 126.19 | 13.54 | 15.73 | 108.62 | 53.72 | 163.52 |
| written | 3.00 | round5:M08:SC:B3:C2\|M09:SC:B3:C2 | M08:SC:B3:C2\|M09:SC:B3:C2 | 706.26 | PRICED | 12.46 | 30.02 | 1.76 | 4.25 | 12.46 | -16.09 | 41.00 |
| written | 4.00 | CSAV | M02:SC:B3:C2\|M08:SC:B3:C2\|M11:SC:B3:C2\|M14:SC:B3:C2 | 712.60 | PRICED | 18.79 | 36.36 | 2.64 | 5.10 | 18.79 | -6.41 | 43.99 |
| written | 4.00 | CSCD | M08:SC:B3:C2\|M09:SC:B3:C2\|M10:SC:B3:C2\|M11:SC:B3:C2 | 714.50 | PRICED | 20.69 | 38.26 | 2.90 | 5.35 | 20.69 | 10.97 | 30.41 |
| written | 4.00 | CSTC | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2\|M13:SC:B3:C2 | 713.17 | PRICED | 19.36 | 36.93 | 2.71 | 5.18 | 19.36 | 7.01 | 31.71 |
| written | 4.00 | present_day | M03:SC:B3:C1\|M08:SC:B5:C3 | 707.16 | PRICED | 13.35 | 30.92 | 1.89 | 4.37 | 13.35 | -4.39 | 31.09 |
| written | 4.00 | round5:M06:SC:B4:C2\|M12:S:B3:C0 | M06:SC:B4:C2\|M12:S:B3:C0 | 802.43 | PRICED | 108.62 | 126.19 | 13.54 | 15.73 | 108.62 | 53.72 | 163.52 |
| written | 4.00 | round5:M08:SC:B3:C2\|M09:SC:B3:C2 | M08:SC:B3:C2\|M09:SC:B3:C2 | 706.26 | PRICED | 12.46 | 30.02 | 1.76 | 4.25 | 12.46 | -16.09 | 41.00 |

## Table 3 -- fixed-layout LP gap (measurement gate) and coverage

(Q_IP - Q_LP) / Q_IP over the scenario cells of every fully priced layout (Q_LP = safe Benders value).

| target | cells | median % | max % | exact cells % | gate |
|---|---|---|---|---|---|
| relaxed | 33 | 0.835 | 5.331 | 0.000 | S1/S2 needed |
| written | 39 | 0.693 | 14.388 | 0.000 | S1/S2 needed |

| target | m | brute-force checked | layouts | open at stop | of which priced (open gaps) | stuck layouts | exploration proposals | note |
|---|---|---|---|---|---|---|---|---|
| relaxed | 1.00 | yes | 90 | 0 | 0 | 0 | 0 | - |
| relaxed | 2.00 | yes | 17,340 | 7,060 | 1 | 0 | 0 | - |
| relaxed | 3.00 | no | - | - | - | 0 | 0 | about 1269310 layouts |
| relaxed | 4.00 | no | - | - | - | 0 | 0 | about 53707150 layouts |
| written | 1.00 | yes | 90 | 1 | 1 | 0 | 0 | - |
| written | 2.00 | yes | 17,340 | 3,140 | 0 | 0 | 0 | - |
| written | 3.00 | no | - | - | - | 0 | 0 | about 1269310 layouts |
| written | 4.00 | no | - | - | - | 0 | 0 | about 53707150 layouts |

Gate records (measured after the warm start, acted on during the run):

* `{"kind": "gate", "target": "relaxed", "n_cells": 6, "median": 0.027024132804360827, "max": 0.04040990188537762, "action": "certify smallest budget by enumeration", "mode": "auto", "wall_clock": "2026-10-18 17:39:40"}`
* `{"kind": "gate_enumeration", "target": "relaxed", "m": 1.0, "done": false, "reason": "wall", "n_layouts": 90, "LB_enum": null, "UB": null, "gap": null, "close_reason": null, "wall_clock": "2026-10-19 00:05:50"}`
* `{"kind": "gate", "target": "written", "n_cells": 12, "median": 0.0453435945576768, "max": 0.08914722949509986, "action": "certify smallest budget by enumeration", "mode": "auto", "wall_clock": "2026-10-19 05:35:54"}`
* `{"kind": "gate_enumeration", "target": "written", "m": 1.0, "done": false, "reason": "wall", "n_layouts": 90, "LB_enum": null, "UB": null, "gap": null, "close_reason": null, "wall_clock": "2026-10-19 10:19:20"}`
* `{"kind": "gate", "target": "relaxed", "n_cells": 24, "median": 0.010589715509423576, "max": 0.05331368005497689, "action": "S1/S2 recommended (not implemented; Benders continues)", "mode": "report", "certify_budgets": [1.0], "skip_enumeration": false, "wall_clock": "2026-10-19 13:13:22"}`
* `{"kind": "gate_enumeration", "target": "relaxed", "m": 1.0, "done": true, "reason": null, "n_layouts": 90, "LB_enum": 1052.9949919684395, "LB_floor": null, "UB": 1052.995, "gap": 7.627348995435083e-09, "close_reason": "gap", "n_lp": 2, "n_envelope_pruned": 88, "n_priced": 0, "n_lp_pruned": 0, "wall_clock": "2026-10-19 13:26:17"}`
* `{"kind": "gate", "target": "written", "n_cells": 27, "median": 0.013372936511542973, "max": 0.14387749729719207, "action": "S1/S2 recommended (not implemented; Benders continues)", "mode": "report", "certify_budgets": [1.0], "skip_enumeration": false, "wall_clock": "2026-10-19 13:26:24"}`
* `{"kind": "gate_enumeration", "target": "written", "m": 1.0, "done": true, "reason": null, "n_layouts": 90, "LB_enum": 1115.2509647205302, "LB_floor": null, "UB": 1131.7997962962963, "gap": 0.01462169513541226, "close_reason": "enumerated (open pricing gaps: 1 priced layouts below UB - tol, escalations used up after 7 calls)", "n_lp": 4, "n_envelope_pruned": 87, "n_priced": 1, "n_lp_pruned": 0, "wall_clock": "2026-10-19 15:59:23"}`
* `{"kind": "gate", "target": "relaxed", "n_cells": 24, "median": 0.010589715509423576, "max": 0.05331368005497689, "action": "S1/S2 recommended (not implemented; Benders continues)", "mode": "report", "certify_budgets": null, "skip_enumeration": true, "wall_clock": "2026-10-19 16:03:39"}`
* `{"kind": "gate", "target": "written", "n_cells": 27, "median": 0.013372936511542973, "max": 0.14387749729719207, "action": "S1/S2 recommended (not implemented; Benders continues)", "mode": "report", "certify_budgets": null, "skip_enumeration": true, "wall_clock": "2026-10-19 20:16:48"}`

## Table 4 -- best layouts under other followers

Same layout, same target; V under the R2.3 policy (`baseline`) and the selfish follower against its ILP value.

| target | layout | follower | V | V (ILP) | status | served share |
|---|---|---|---|---|---|---|
| relaxed | M09:SC:B3:C2 | baseline | 1,834.848 | 1,052.995 | OK | 0.483 |
| relaxed | M09:SC:B3:C2 | selfish | 1,834.848 | 1,052.995 | OK | 0.483 |
| relaxed | M08:SC:B3:C2\|M09:SC:B3:C2 | baseline | 1,260.562 | 700.113 | OK | 0.800 |
| relaxed | M08:SC:B3:C2\|M09:SC:B3:C2 | selfish | 1,257.163 | 700.113 | OK | 0.783 |
| written | M08:SC:B3:C2 | baseline | 1,873.121 | 1,132.394 | OK | 0.442 |
| written | M08:SC:B3:C2 | selfish | 1,873.121 | 1,132.394 | OK | 0.442 |
| written | M08:SC:B3:C2\|M09:SC:B3:C2 | baseline | 1,260.562 | 706.262 | OK | 0.800 |
| written | M08:SC:B3:C2\|M09:SC:B3:C2 | selfish | 1,257.163 | 706.262 | OK | 0.783 |
| written | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2 | baseline | 1,207.131 | 703.606 | OK | 0.833 |
| written | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2 | selfish | 1,046.786 | 703.606 | OK | 0.883 |
| relaxed | M09:SC:B3:C2 | baseline | 1,834.848 | 1,052.995 | OK | 0.483 |
| relaxed | M09:SC:B3:C2 | selfish | 1,834.848 | 1,052.995 | OK | 0.483 |
| written | M08:SC:B3:C2 | baseline | 1,873.121 | 1,131.800 | OK | 0.442 |
| written | M08:SC:B3:C2 | selfish | 1,873.121 | 1,131.800 | OK | 0.442 |
| relaxed | M08:SC:B3:C2\|M09:SC:B3:C2 | baseline | 1,260.562 | 700.113 | OK | 0.800 |
| relaxed | M08:SC:B3:C2\|M09:SC:B3:C2 | selfish | 1,257.163 | 700.113 | OK | 0.783 |
| written | M04:SC:B2:C2\|M09:SC:B4:C2 | baseline | 1,148.450 | 699.957 | OK | 0.825 |
| written | M04:SC:B2:C2\|M09:SC:B4:C2 | selfish | 1,168.582 | 699.957 | OK | 0.808 |
| written | M04:SC:B4:C2\|M09:SC:B4:C2 | baseline | 1,111.775 | 693.807 | OK | 0.850 |
| written | M04:SC:B4:C2\|M09:SC:B4:C2 | selfish | 1,040.534 | 693.807 | OK | 0.867 |

## Caveats

* Every ILP value is an upper bound on the unpruned written optimum (PRUNING_NYC); V* is the optimum under the all-candidates library convention (values are not comparable one to one with round-5 `open_sites` numbers).
* Certificates hold for this scenario set (seeds listed in the plan record) and this library only; CIs over three scenarios are wide by construction.
* LB is valid under solver tolerances: LP cuts are safe Lagrangian bounds (C1), integer cuts use Gurobi ObjBound minus C_setup (C3).
