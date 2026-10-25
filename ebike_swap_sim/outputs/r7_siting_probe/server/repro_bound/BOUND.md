# O2 bound from the stored cut pool -- manhattan

Source `/home/ubuntu/battery_swap/ebike_swap_sim/outputs/r6_o2/manhattan_pass2` (read-only); generated 2026-10-21 13:44.  LB = max(master ObjBound over the full pool with cover rows, superset trivial bound, enumeration floor where the enumeration started), nested over budgets; UB = best priced V of a menu layout within the budget (records).  No LP or ILP solved.

| target | m | LB | bound kind | UB | UB layout | gap % | master bound | superset | enumeration floor | cuts | cover rows | master status | stored LB | stored UB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | 1.000 | 1,052.995 | enumeration | 1,052.995 | M09:SC:B3:C2 | 0.000 | 1,052.995 | 662.386 | 1,052.995 | 380 | 0 | OPTIMAL | 1,052.995 | 1,052.995 |
| relaxed | 2.000 | 675.740 | master | 700.113 | M08:SC:B3:C2\|M09:SC:B3:C2 | 3.481 | 675.740 | 662.386 | - | 380 | 0 | OPTIMAL | 675.740 | 700.113 |
| relaxed | 3.000 | 675.740 | master | 700.113 | M08:SC:B3:C2\|M09:SC:B3:C2 | 3.481 | 675.740 | 662.386 | - | 380 | 0 | OPTIMAL | 675.740 | 700.113 |
| relaxed | 4.000 | 675.740 | master | 700.113 | M08:SC:B3:C2\|M09:SC:B3:C2 | 3.481 | 675.740 | 662.386 | - | 380 | 0 | OPTIMAL | 675.740 | 700.113 |
| written | 1.000 | 1,115.251 | enumeration | 1,131.800 | M08:SC:B3:C2 | 1.462 | 1,115.251 | 662.386 | 1,115.251 | 998 | 0 | OPTIMAL | 1,115.251 | 1,131.800 |
| written | 2.000 | 676.240 | master | 699.957 | M04:SC:B2:C2\|M09:SC:B4:C2 | 3.388 | 676.240 | 662.386 | - | 998 | 0 | OPTIMAL | 676.240 | 699.957 |
| written | 3.000 | 676.240 | master | 693.807 | M04:SC:B4:C2\|M09:SC:B4:C2 | 2.532 | 676.240 | 662.386 | - | 998 | 0 | OPTIMAL | 676.240 | 693.807 |
| written | 4.000 | 676.240 | master | 693.807 | M04:SC:B4:C2\|M09:SC:B4:C2 | 2.532 | 676.240 | 662.386 | - | 998 | 0 | OPTIMAL | 676.240 | 693.807 |

## relaxed, m = 1: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M09:SC:B3:C2 | 1,052.995 | 1,019.607 | PRICED | 1,052.995 | yes |
| 2 | M05:SC:B3:C2 | 1,067.821 | - | - | - | yes |
| 3 | M08:SC:B3:C2 | 1,070.071 | 1,034.974 | PRICED | 1,070.071 | yes |
| 4 | M06:SC:B3:C2 | 1,087.377 | 1,087.377 | - | - | yes |
| 5 | M07:SC:B3:C2 | 1,098.564 | - | - | - | yes |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36}`; enumeration: `{"floor": 1052.9949919684395, "argmin": "M09:SC:B3:C2", "n_layouts": 90, "n_infeasible": 0, "n_from_envelope": 90, "n_from_v_lp": 0, "n_from_pricing": 0}`

## relaxed, m = 2: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M06:SC:B2:C2\|M15:SC:B2:C2 | 675.740 | - | - | - | no |
| 2 | M03:SC:B3:C2\|M15:SC:B1:C2 | 675.740 | - | - | - | no |
| 3 | M05:SC:B2:C2\|M06:SC:B2:C2 | 675.740 | - | - | - | no |
| 4 | M03:SC:B2:C2\|M15:SC:B2:C2 | 675.740 | - | - | - | no |
| 5 | M06:SC:B1:C2\|M15:SC:B3:C2 | 675.740 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36}`; enumeration: `null`

## relaxed, m = 3: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M06:SC:B2:C2\|M15:SC:B2:C2 | 675.740 | - | - | - | no |
| 2 | M04:SC:B1:C2\|M15:SC:B3:C2 | 675.740 | - | - | - | no |
| 3 | M05:SC:B2:C2\|M06:SC:B2:C2 | 675.740 | - | - | - | no |
| 4 | M03:SC:B2:C2\|M15:SC:B2:C2 | 675.740 | - | - | - | no |
| 5 | M04:SC:B2:C2\|M15:SC:B2:C2 | 675.740 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36}`; enumeration: `null`

## relaxed, m = 4: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M06:SC:B2:C2\|M15:SC:B2:C2 | 675.740 | - | - | - | no |
| 2 | M05:SC:B2:C2\|M09:SC:B2:C2 | 675.740 | - | - | - | no |
| 3 | M05:SC:B2:C2\|M06:SC:B2:C2 | 675.740 | - | - | - | no |
| 4 | M06:SC:B1:C2\|M15:SC:B3:C2 | 675.740 | - | - | - | no |
| 5 | M04:SC:B2:C2\|M15:SC:B2:C2 | 675.740 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36}`; enumeration: `null`

## written, m = 1: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M09:SC:B3:C2 | 1,115.251 | 1,063.909 | PRICED | 1,115.251 | no |
| 2 | M06:SC:B3:C2 | 1,130.764 | 1,120.445 | PRUNED_BY_BOUND | 1,130.764 | yes |
| 3 | M08:SC:B3:C2 | 1,131.800 | 1,067.898 | PRICED | 1,131.800 | yes |
| 4 | M05:SC:B3:C2 | 1,133.737 | 1,133.737 | - | - | yes |
| 5 | M03:SC:B3:C2 | 1,139.872 | 1,139.872 | - | - | yes |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36, "lp:written": 495, "lshaped:written": 73, "lifted:written": 50}`; enumeration: `{"floor": 1115.2509647205302, "argmin": "M09:SC:B3:C2", "n_layouts": 90, "n_infeasible": 0, "n_from_envelope": 88, "n_from_v_lp": 2, "n_from_pricing": 0}`

## written, m = 2: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M04:SC:B2:C2\|M15:S:B4:C0 | 676.240 | - | - | - | no |
| 2 | M01:S:B4:C0\|M10:SC:B2:C2 | 676.240 | - | - | - | no |
| 3 | M04:SC:B3:C2\|M15:S:B3:C0 | 676.240 | - | - | - | no |
| 4 | M07:SC:B4:C2\|M14:S:B2:C0 | 676.240 | - | - | - | no |
| 5 | M02:SC:B2:C2\|M10:S:B4:C0 | 676.240 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36, "lp:written": 495, "lshaped:written": 73, "lifted:written": 50}`; enumeration: `null`

## written, m = 3: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M08:S:B2:C0\|M09:SC:B4:C2 | 676.240 | - | - | - | no |
| 2 | M02:SC:B2:C2\|M10:S:B4:C0 | 676.240 | - | - | - | no |
| 3 | M04:SC:B2:C2\|M15:S:B4:C0 | 676.240 | - | - | - | no |
| 4 | M08:S:B4:C0\|M09:SC:B2:C2 | 676.240 | - | - | - | no |
| 5 | M10:SC:B2:C2\|M15:S:B4:C0 | 676.240 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36, "lp:written": 495, "lshaped:written": 73, "lifted:written": 50}`; enumeration: `null`

## written, m = 4: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M08:S:B4:C0\|M10:SC:B2:C2 | 676.240 | - | - | - | no |
| 2 | M07:SC:B2:C2\|M08:S:B4:C0 | 676.240 | - | - | - | no |
| 3 | M08:S:B2:C0\|M09:SC:B4:C2 | 676.240 | - | - | - | no |
| 4 | M01:S:B4:C0\|M10:SC:B2:C2 | 676.240 | - | - | - | no |
| 5 | M07:S:B4:C0\|M10:SC:B2:C2 | 676.240 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 285, "lshaped:relaxed": 59, "lifted:relaxed": 36, "lp:written": 495, "lshaped:written": 73, "lifted:written": 50}`; enumeration: `null`

