# R7 production search -- manhattan_dot

Records `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r7_prod_final/r7_siting/records.jsonl`.  Generated 2026-10-24 00:39.

## Bounds per budget (last budget_result)

| m | best layout | UB | LB | LB kind | gap % | certified |
|---|---|---|---|---|---|---|
| 1 | D23:SC:B3:C2 | 1,085.87 | 1,036.03 | master | 4.59 | no |
| 2 | D07:SC:B3:C2\|D45:SC:B3:C2 | 718.91 | 670.23 | master | 6.77 | no |
| 3 | D07:SC:B4:C2\|D45:SC:B4:C2 | 709.98 | 670.23 | master | 5.60 | no |

## Pair screens (m = 2; subset LP on S_LP, L_s elsewhere; bound over every size combination)

UB_2 718.9115952380953; 5 of 16 pairs excluded (no layout of the pair below UB_2 - tol).

| pair | source | pair bound | window bound | excluded |
|---|---|---|---|---|
| D24\|D45 | swap:D23->D24 | 675.87 | 663.84 | no |
| D23\|D45 | coverage_complement | 675.92 | 663.89 | no |
| D07\|D45 | swap:D23->D07 | 676.48 | 664.45 | no |
| D23\|D41 | coverage_complement | 676.61 | 664.58 | no |
| D23\|D44 | coverage_complement | 676.62 | 664.59 | no |
| D26\|D45 | swap:D23->D26 | 676.99 | 664.96 | no |
| D09\|D38 | given | 677.97 | 665.94 | no |
| D37\|D45 | swap:D23->D37 | 678.68 | 666.65 | no |
| D28\|D45 | swap:D23->D28 | 679.16 | 667.13 | no |
| D30\|D38 | given | 681.43 | 669.40 | no |
| D23\|D28 | swap:D45->D28 | 688.14 | 676.11 | no |
| D07\|D23 | swap:D45->D07 | 718.42 | 706.39 | yes |
| D12\|D23 | coverage_complement | 718.72 | 706.69 | yes |
| D23\|D24 | m1_top2 | 719.07 | 707.04 | yes |
| D23\|D26 | swap:D45->D26 | 719.76 | 707.73 | yes |
| D01\|D07 | relax_and_round_master | 746.63 | 734.60 | yes |

## M3 bound probe (Tier 2 decision; lift = ILP OPEX bound over the cell LP value)

Verdict: start Tier 2 (lanes_r2_tier2.txt): variant default lifts the cell bounds by 2.28 % >= 1 %.

| variant | cells | mean lift % | cells OPTIMAL | limit >= 1200 s |
|---|---|---|---|---|
| Method=2 | 2 | 1.882 | 0 | yes |
| default | 2 | 2.284 | 1 | yes |

| variant | layout | s | LP Qs | ILP bound | lift % | status | nodes | runtime s | limit s |
|---|---|---|---|---|---|---|---|---|---|
| Method=2 | D29:SC:B3:C2 | 2 | 1,075.120 | 1,093.374 | 1.698 | TIME_LIMIT | 570.000 | 1,200.090 | 1,200.000 |
| Method=2 | D29:SC:B3:C2 | 5 | 1,437.548 | 1,467.242 | 2.066 | TIME_LIMIT | 72.000 | 1,200.109 | 1,200.000 |
| default | D29:SC:B3:C2 | 2 | 1,075.120 | 1,091.843 | 1.555 | TIME_LIMIT | 535.000 | 1,200.080 | 1,200.000 |
| default | D29:SC:B3:C2 | 5 | 1,437.548 | 1,480.847 | 3.012 | OPTIMAL | 123.000 | 1,106.846 | 1,200.000 |

## m = 3 additions

| variant | layout | status | tier | V (UB) | LB all-candidates | LB open_sites |
|---|---|---|---|---|---|---|
| pair_max_sizes | D07:SC:B4:C2\|D45:SC:B4:C2 | PRICED | open_sites | 709.98 | 678.06 | 709.96 |
| pair_plus_D23 | D07:SC:B3:C2\|D23:SC:B3:C2\|D45:SC:B3:C2 | PRICED | open_sites | 718.80 | 684.33 | 718.79 |
| pair_plus_D24 | D07:SC:B3:C2\|D24:SC:B3:C2\|D45:SC:B3:C2 | SKIPPED_BUDGET | open_sites | - | 684.33 | 710.16 |
| summary | D07:SC:B4:C2\|D45:SC:B4:C2 | - | - | 709.98 | - | - |

### Pair pricings on the open_sites tier (V = UB; LB all-candidates = envelope / LP / subset)

| pair | layout | status | V_open (UB) | LB all-candidates | LB open_sites |
|---|---|---|---|---|---|
| D24\|D45 | D24:SC:B3:C2\|D45:SC:B3:C2 | PRICED | 721.78 | 676.78 | 714.27 |
| D23\|D45 | D23:SC:B3:C2\|D45:SC:B3:C2 | PRICED | 719.60 | 676.83 | 713.09 |
| D07\|D45 | D07:SC:B3:C2\|D45:SC:B3:C2 | PRICED | 718.91 | 677.39 | 711.70 |

## Role table

| m | follower | UB | LB | best | V | LB | best with S | V | LB | + S | best with hub | V | LB | + hub |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | open_sites | 718.91 | 670.23 | D07:SC:B3:C2\|D45:SC:B3:C2 | 718.91 | 677.39 | D24:S:B3:C0\|D45:SC:B3:C2 | 758.34 | 676.62 | 39.43 | D07:S:B3:C0\|D50:C:B0:C4 | 1,445.77 | 690.45 | 726.86 |

## Out of sample (held-out scenarios; feasibility checked first)

| layout | key | tier | status | V in | V out | out - in |
|---|---|---|---|---|---|---|
| best@m1 | D23:SC:B3:C2 | open_sites | SKIPPED_BUDGET | 1,085.87 | - | - |
| best@m2 | D07:SC:B3:C2\|D45:SC:B3:C2 | open_sites | SKIPPED_BUDGET | 716.85 | - | - |
| CSCD@m2 | D18:SC:B3:C2\|D19:SC:B3:C2 | open_sites | SKIPPED_BUDGET | 858.33 | - | - |
| dot_all_pilot | D12:SC:B3:C2\|D18:SC:B3:C2 | open_sites | SKIPPED_BUDGET | 851.27 | - | - |

## Radius effect (stage R: approach radius unset)

| group | layout | tier | V radius 14 | V no radius | effect % | both sides OPTIMAL |
|---|---|---|---|---|---|---|
| m1_tie | D23:SC:B3:C2 | open_sites | 1,085.87 | 1,078.16 | 0.71 | no |
| m1_tie | D24:SC:B3:C2 | open_sites | 1,087.74 | 1,078.32 | 0.87 | no |
| m1_tie | D28:SC:B3:C2 | open_sites | 1,091.06 | 1,062.49 | 2.69 | yes |
| m1_tie | D37:SC:B3:C2 | open_sites | 1,092.44 | 1,078.07 | 1.33 | yes |
| m1_tie | D29:SC:B3:C2 | open_sites | 1,095.90 | 1,062.87 | 3.11 | yes |
| m1_tie | D38:SC:B3:C2 | open_sites | 1,097.95 | 1,071.30 | 2.49 | yes |
| m1_tie | D34:SC:B3:C2 | open_sites | 1,099.67 | 1,062.47 | 3.50 | no |
| m1_tie | D30:SC:B3:C2 | open_sites | 1,102.40 | 1,069.16 | 3.11 | no |
| m1_tie | D33:SC:B3:C2 | open_sites | 1,103.92 | 1,069.30 | 3.24 | no |
| m1_tie | D25:SC:B3:C2 | open_sites | 1,105.78 | 1,092.78 | 1.19 | no |
| m1_tie | D39:SC:B3:C2 | open_sites | 1,109.86 | - | - | no |
| best@m2 | D07:SC:B3:C2\|D45:SC:B3:C2 | open_sites | 716.85 | - | - | no |
| best@m3 | D07:SC:B4:C2\|D45:SC:B4:C2 | open_sites | 709.98 | - | - | no |

* m = 1 ranking library-conditional; m = 1 effect [0.007146057259888499, 0.035012596222729814], m = 2/3 effect None

## List pricing (price-list; open_sites V = UB only, LB all-candidates = envelope / LP / pricing)

| name | layout | tier | status | V | LB all-candidates | LB open_sites |
|---|---|---|---|---|---|---|
| m1-lp-order:1034.09 | D29:SC:B3:C2 | open_sites | PRICED | 1,095.90 | 1,034.09 | 1,095.90 |
| m1-lp-order:1036.03 | D28:SC:B3:C2 | open_sites | PRICED | 1,091.06 | 1,036.03 | 1,091.06 |
| m1-lp-order:1037.18 | D34:SC:B3:C2 | open_sites | PRICED | 1,099.67 | 1,037.18 | 1,099.67 |
| m1-lp-order:1043.54 | D33:SC:B3:C2 | open_sites | PRICED | 1,103.92 | 1,043.54 | 1,103.92 |
| m1-lp-order:1048.20 | D37:SC:B3:C2 | open_sites | PRICED | 1,092.44 | 1,048.20 | 1,092.44 |
| m1-lp-order:1049.63 | D23:SC:B3:C2 | open_sites | PRICED | 1,085.87 | 1,049.63 | 1,084.31 |
| m1-lp-order:1050.42 | D24:SC:B3:C2 | open_sites | PRICED | 1,087.74 | 1,050.42 | 1,087.74 |
| m1-lp-order:1055.39 | D30:SC:B3:C2 | open_sites | PRICED | 1,102.40 | 1,055.39 | 1,102.40 |
| m1-lp-order:1059.87 | D38:SC:B3:C2 | open_sites | PRICED | 1,097.95 | 1,059.87 | 1,097.95 |
| m1-lp-order:1065.50 | D25:SC:B3:C2 | open_sites | PRICED | 1,105.78 | 1,065.50 | 1,103.61 |
| m1-lp-order:1066.28 | D39:SC:B3:C2 | open_sites | PRICED | 1,109.86 | 1,066.28 | 1,109.86 |
| m1-lp-order:1073.66 | D22:SC:B3:C2 | open_sites | PRICED | 1,122.71 | 1,073.66 | 1,122.33 |
| extend:1079.32 | D31:SC:B3:C2 | open_sites | PRICED | 1,139.15 | 1,079.32 | 1,139.15 |
| extend:1081.02 | D19:SC:B3:C2 | open_sites | PRICED | 1,125.28 | 1,081.02 | 1,124.55 |
| extend:1085.33 | D18:SC:B3:C2 | open_sites | PRICED | 1,118.68 | 1,085.33 | 1,118.68 |
| extend:1085.74 | D16:SC:B3:C2 | open_sites | PRICED | 1,131.04 | 1,085.74 | 1,130.56 |
| D29:SC:B3:C2 | D29:SC:B3:C2 | all_candidates | UNRESOLVED | - | 1,041.41 | - |

## UB validity check (M6: open_sites schedules on the all-candidates library)

| layout | ok | cells ok | V_checked | V_open |
|---|---|---|---|---|
| D23:SC:B3:C2 | yes | 12 | 1,085.87 | 1,085.87 |

## Calibration (stage P)

* pricing: `{"part": "pricing", "layout": "D38:SC:B3:C2", "status": "PRICED", "V": 1666.5090542328044, "template_s": [30.500221523000164, 42.122874642999705, 48.3841060120003, 57.47276961699981, 51.06181892099994, 56.429674906999935, 27.762337333999767, 54.30634653700008, 63.9323919200001, 29.704934125000364, 77.40321431200027, 35.22084030099995], "template_s_sum": 574.3015301520004, "wall_s": 1693.4984670149997, "n_cells": 12, "n_solved": 12, "n_cache_hits": 0, "solver_s_sum": 3602.4002068042755, "workers": 4, "threads": 3, "utilisation": 0.5317985632951223, "overhead_per_cell_s": 264.29947177131027, "no`
* crossover: `{"part": "crossover", "layout": "D38:SC:B3:C2", "scenario": 4, "cell": "cell_3_2", "n_locations": 9, "rows": [{"variant": "crossover", "status": "OPTIMAL", "Qs": 1021.2742083319282, "Qt": 1021.2742083333335, "runtime_s": 511.0705526219999, "iterations": 62539.0}, {"variant": "no_crossover", "status": "OPTIMAL", "Qs": 1021.2742018232674, "Qt": 1021.2742086016722, "runtime_s": 465.35220616100014, "iterations": 0.0}], "saving": 0.08945603738357855, "keep_nox": false, "wall_clock": "2026-10-22 05:21:11"}`
* lp_workers: `{"part": "lp_workers", "layout": "D38:SC:B3:C2", "scenarios": [4, 5, 10, 11, 2, 3, 8, 9], "configs": [{"workers": 3, "threads": 3, "wall_s": 434.4298300320006, "runtime_s": [147.50767484600055, 163.9748804840001, 167.7472586189997, 160.92214863299978, 157.42972907500007, 157.19098016099997, 118.03235917500024, 109.52458022999963], "Qs": [1385.209620470024, 1507.4259444430004, 1329.234155068266, 1266.3454260618912, 1074.525666665164, 1090.6406852915143, 818.6511989520806, 891.509141023768]}, {"workers": 4, "threads": 2, "wall_s": 364.5930034820003, "runtime_s": [194.54937788799998, 209.06667392`

## Cost per batch (`cost.jsonl`; instance hours = union of the lane intervals)

| batch | invocations | stages | instance | wall h (sum) | USD (sum) | instance h | USD (instance h) | failed | unfinished |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 | calib, feas, oos-feas | r7i.4xlarge | 10.74 | 11.37 | 4.73 | 5.00 | 0 | 0 |
| 2 | 1 | m1 | r7i.4xlarge | 13.23 | 14.00 | 13.23 | 14.00 | 0 | 0 |
| 2b | 6 | gate, m1, price-list, ub-check | r7i.4xlarge | 6.69 | 7.08 | 6.69 | 7.08 | 0 | 0 |
| 3 | 12 | rootlp | r7i.4xlarge | 26.82 | 28.38 | 9.18 | 9.72 | 0 | 0 |
| 4 | 3 | m3, pairs, roles | r7i.4xlarge | 7.73 | 8.19 | 7.73 | 8.19 | 0 | 0 |
| 5 | 3 | comparison, oos, restricted | r7i.4xlarge | 4.29 | 4.54 | 4.29 | 4.54 | 0 | 0 |
| 6 | 1 | noradius | r7i.4xlarge | 2.21 | 2.34 | 2.21 | 2.34 | 0 | 0 |
| total | 32 | | | 71.71 | 75.89 | 48.06 | 50.87 | | 0 |

