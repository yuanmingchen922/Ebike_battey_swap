# O2 bound from the stored cut pool -- manhattan

Source `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r6_o2/manhattan` (read-only); generated 2026-10-19 13:11.  LB = max(master ObjBound over the full pool with cover rows, superset trivial bound, enumeration floor where the enumeration started), nested over budgets; UB = best priced V of a menu layout within the budget (records).  No LP or ILP solved.

| target | m | LB | bound kind | UB | UB layout | gap % | master bound | superset | enumeration floor | cuts | cover rows | master status | stored LB | stored UB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | 1.000 | 1,037.834 | enumeration | 1,052.995 | M09:SC:B3:C2 | 1.440 | 1,037.834 | 662.386 | 1,037.834 | 262 | 0 | OPTIMAL | - | 1,052.995 |
| relaxed | 2.000 | 674.830 | master | 700.113 | M08:SC:B3:C2\|M09:SC:B3:C2 | 3.611 | 674.830 | 662.386 | - | 262 | 0 | OPTIMAL | - | 700.113 |
| relaxed | 3.000 | 674.830 | master | 700.113 | M08:SC:B3:C2\|M09:SC:B3:C2 | 3.611 | 674.830 | 662.386 | - | 262 | 0 | OPTIMAL | - | 700.113 |
| relaxed | 4.000 | 674.830 | master | 700.113 | M08:SC:B3:C2\|M09:SC:B3:C2 | 3.611 | 674.830 | 662.386 | - | 262 | 0 | OPTIMAL | - | 700.113 |
| written | 1.000 | 1,037.834 | enumeration | 1,132.394 | M08:SC:B3:C2 | 8.350 | 1,037.834 | 662.386 | 1,037.834 | 507 | 0 | OPTIMAL | - | 1,132.394 |
| written | 2.000 | 674.830 | master | 706.262 | M08:SC:B3:C2\|M09:SC:B3:C2 | 4.450 | 674.830 | 662.386 | - | 507 | 0 | OPTIMAL | - | 706.262 |
| written | 3.000 | 674.830 | master | 703.606 | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2 | 4.090 | 674.830 | 662.386 | - | 507 | 0 | OPTIMAL | - | 703.606 |
| written | 4.000 | 674.830 | master | 703.606 | M08:SC:B3:C2\|M09:SC:B3:C2\|M12:SC:B3:C2 | 4.090 | 674.830 | 662.386 | - | 507 | 0 | OPTIMAL | - | 703.606 |

## relaxed, m = 1: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M06:SC:B3:C2 | 1,037.834 | - | - | - | no |
| 2 | M09:SC:B3:C2 | 1,046.214 | 1,019.607 | PRICED | 1,046.214 | no |
| 3 | M03:SC:B3:C2 | 1,049.517 | - | - | - | no |
| 4 | M05:SC:B3:C2 | 1,067.821 | - | - | - | yes |
| 5 | M08:SC:B3:C2 | 1,070.071 | 1,034.974 | PRICED | 1,070.071 | yes |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28}`; enumeration: `{"floor": 1037.8339295242681, "argmin": "M06:SC:B3:C2", "n_layouts": 90, "n_infeasible": 0, "n_from_envelope": 90, "n_from_v_lp": 0, "n_from_pricing": 0}`

## relaxed, m = 2: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M01:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |
| 2 | M04:S:B1:C0\|M05:SC:B1:C1 | 674.830 | - | - | - | no |
| 3 | M01:S:B1:C0\|M12:SC:B1:C1 | 674.830 | - | - | - | no |
| 4 | M05:SC:B1:C1\|M09:S:B1:C0 | 674.830 | - | - | - | no |
| 5 | M07:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28}`; enumeration: `null`

## relaxed, m = 3: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M01:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |
| 2 | M03:SC:B1:C1\|M13:S:B1:C0 | 674.830 | - | - | - | no |
| 3 | M04:S:B1:C0\|M07:SC:B1:C1 | 674.830 | - | - | - | no |
| 4 | M02:S:B1:C0\|M07:SC:B1:C1 | 674.830 | - | - | - | no |
| 5 | M02:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28}`; enumeration: `null`

## relaxed, m = 4: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M01:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |
| 2 | M03:SC:B1:C1\|M08:S:B1:C0 | 674.830 | - | - | - | no |
| 3 | M04:S:B1:C0\|M07:SC:B1:C1 | 674.830 | - | - | - | no |
| 4 | M11:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |
| 5 | M08:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28}`; enumeration: `null`

## written, m = 1: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M06:SC:B3:C2 | 1,037.834 | - | - | - | no |
| 2 | M03:SC:B3:C2 | 1,050.148 | - | - | - | no |
| 3 | M05:SC:B3:C2 | 1,067.821 | - | - | - | no |
| 4 | M07:SC:B3:C2 | 1,098.564 | - | - | - | no |
| 5 | M09:SC:B3:C2 | 1,100.586 | 1,063.909 | PRICED | 1,100.586 | no |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28, "lp:written": 168, "lshaped:written": 48, "lifted:written": 29}`; enumeration: `{"floor": 1037.8339295242681, "argmin": "M06:SC:B3:C2", "n_layouts": 90, "n_infeasible": 0, "n_from_envelope": 88, "n_from_v_lp": 2, "n_from_pricing": 0}`

## written, m = 2: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M09:S:B1:C0\|M14:SC:B1:C1 | 674.830 | - | - | - | no |
| 2 | M09:S:B1:C0\|M15:SC:B1:C1 | 674.830 | - | - | - | no |
| 3 | M01:S:B1:C0\|M03:SC:B1:C1 | 674.830 | - | - | - | no |
| 4 | M03:S:B1:C0\|M12:SC:B1:C1 | 674.830 | - | - | - | no |
| 5 | M09:S:B1:C0\|M12:SC:B1:C1 | 674.830 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28, "lp:written": 168, "lshaped:written": 48, "lifted:written": 29}`; enumeration: `null`

## written, m = 3: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M09:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |
| 2 | M12:SC:B1:C1\|M15:S:B1:C0 | 674.830 | - | - | - | no |
| 3 | M09:S:B1:C0\|M14:SC:B1:C1 | 674.830 | - | - | - | no |
| 4 | M06:SC:B1:C1\|M09:S:B1:C0 | 674.830 | - | - | - | no |
| 5 | M09:SC:B1:C1\|M11:S:B1:C0 | 674.830 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28, "lp:written": 168, "lshaped:written": 48, "lifted:written": 29}`; enumeration: `null`

## written, m = 4: ranked master proposals

| rank | layout | envelope | v_LP | priced | priced lower | resolved (>= UB - tol) |
|---|---|---|---|---|---|---|
| 1 | M09:S:B1:C0\|M13:SC:B1:C1 | 674.830 | - | - | - | no |
| 2 | M13:S:B1:C0\|M15:SC:B1:C1 | 674.830 | - | - | - | no |
| 3 | M02:S:B1:C0\|M07:SC:B1:C1 | 674.830 | - | - | - | no |
| 4 | M06:S:B1:C0\|M07:SC:B1:C1 | 674.830 | - | - | - | no |
| 5 | M05:SC:B1:C1\|M11:S:B1:C0 | 674.830 | - | - | - | no |

Cuts by kind:target in this master: `{"lp:relaxed": 183, "lshaped:relaxed": 51, "lifted:relaxed": 28, "lp:written": 168, "lshaped:written": 48, "lifted:written": 29}`; enumeration: `null`

