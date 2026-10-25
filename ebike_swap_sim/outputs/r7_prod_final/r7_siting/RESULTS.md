# R7 siting scale-up -- manhattan_dot

Records `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r7_prod_final/r7_siting/records.jsonl`; cut pool `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r7_prod_final/r7_siting/cuts.jsonl`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r7_prod_final/r7_siting/cache`.  Generated 2026-10-24 00:33.

## Problems (read first)

* m = 1: NOT certified (gap 4.59 % if known; stop: not searched)
* m = 2: NOT certified (gap 6.77 % if known; stop: not searched)
* m = 3: NOT certified (gap 5.60 % if known; stop: not searched)
* --root-import refused: FileNotFoundError: outputs/r7_siting_probe/dot_Nall_S12/cuts.jsonl

## Certificate details (plan section 3)

* terminal-infeasible one-site locations (skip list): 36 ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D08', 'D09', 'D10', 'D12', 'D15', 'D21', 'D27', 'D32', 'D35', 'D36', 'D40', 'D41', 'D42', 'D43', 'D44', 'D45', 'D46', 'D47', 'D48', 'D49', 'D50', 'D51', 'D52', 'D53', 'D54', 'D55', 'D56', 'D57', 'D58', 'D59']
* root LP values (L_s): 12 scenarios, missing []; L = [516.66, 450.37, 720.77, 645.47, 779.1, 809.56, 464.98, 476.72, 586.91, 576.24, 862.41, 767.83]
* epsilon_1 (achieved incumbent MIP gap at m = 1): 0.143 % of V = 1085.87 (D23:SC:B3:C2; worst scenario 9 at 3.463 %) [open_sites follower]
* near-tie set at m = 1 (priced one-site layouts within 3.0 % of UB_1 = 1085.8669457671958): D23:SC:B3:C2 (1085.87 open_sites), D24:SC:B3:C2 (1087.74 open_sites), D28:SC:B3:C2 (1091.06 open_sites), D37:SC:B3:C2 (1092.44 open_sites), D29:SC:B3:C2 (1095.90 open_sites), D38:SC:B3:C2 (1097.95 open_sites), D34:SC:B3:C2 (1099.67 open_sites), D30:SC:B3:C2 (1102.40 open_sites), D33:SC:B3:C2 (1103.92 open_sites), D25:SC:B3:C2 (1105.78 open_sites), D39:SC:B3:C2 (1109.86 open_sites)

## m = 1 under both followers (re-plan change 8)

* **All-candidates follower (model of record):** V*_1 in [1036.03, 1085.87] (gap 4.59 %; LB = master, UB = D23:SC:B3:C2 priced on the open_sites tier, a feasible schedule of the all-candidates follower).
* locations not excluded (best known all-candidates lower bound < UB, tol 0): 16: D28 (1036.03), D34 (1037.18), D29 (1041.41), D33 (1043.54), D37 (1048.20), D23 (1049.63), D24 (1050.42), D30 (1055.39), D38 (1059.87), D25 (1065.50), D39 (1066.28), D22 (1073.66), D31 (1079.32), D19 (1081.02), D18 (1085.33), D16 (1085.74)
* UB validity check (M6, open_sites schedules on the all-candidates library): ok = True, 12 cells ok, V_checked = 1085.87 against V_open = 1085.87
* **Open-sites follower (tol 0):** V*_open in [1084.31, 1085.87] (gap 0.14 %; best D23:SC:B3:C2; LB from D23:SC:B3:C2); certificate COMPLETE: every layout with an open-sites lower bound below UB_open is priced

Open-sites ranking at m = 1 (V_open = UB for both followers; lower_open holds for the open-sites follower only; lower_all = LP / envelope / all-candidates pricing):

| layout | status | V_open | lower_open | lower_all | cells OPTIMAL | cells |
|---|---|---|---|---|---|---|
| D23:SC:B3:C2 | PRICED | 1,085.87 | 1,084.31 | 1,049.63 | 11 | 12 |
| D24:SC:B3:C2 | PRICED | 1,087.74 | 1,087.74 | 1,050.42 | 12 | 12 |
| D28:SC:B3:C2 | PRICED | 1,091.06 | 1,091.06 | 1,036.03 | 12 | 12 |
| D37:SC:B3:C2 | PRICED | 1,092.44 | 1,092.44 | 1,048.20 | 12 | 12 |
| D29:SC:B3:C2 | PRICED | 1,095.90 | 1,095.90 | 1,041.41 | 12 | 12 |
| D38:SC:B3:C2 | PRICED | 1,097.95 | 1,097.95 | 1,059.87 | 12 | 12 |
| D34:SC:B3:C2 | PRICED | 1,099.67 | 1,099.67 | 1,037.18 | 12 | 12 |
| D30:SC:B3:C2 | PRICED | 1,102.40 | 1,102.40 | 1,055.39 | 12 | 12 |
| D33:SC:B3:C2 | PRICED | 1,103.92 | 1,103.92 | 1,043.54 | 12 | 12 |
| D25:SC:B3:C2 | PRICED | 1,105.78 | 1,103.61 | 1,065.50 | 11 | 12 |
| D39:SC:B3:C2 | PRICED | 1,109.86 | 1,109.86 | 1,066.28 | 12 | 12 |
| D18:SC:B3:C2 | PRICED | 1,118.68 | 1,118.68 | 1,085.33 | 12 | 12 |
| D22:SC:B3:C2 | PRICED | 1,122.71 | 1,122.33 | 1,073.66 | 11 | 12 |
| D19:SC:B3:C2 | PRICED | 1,125.28 | 1,124.55 | 1,081.02 | 11 | 12 |
| D16:SC:B3:C2 | PRICED | 1,131.04 | 1,130.56 | 1,085.74 | 11 | 12 |
| D31:SC:B3:C2 | PRICED | 1,139.15 | 1,139.15 | 1,079.32 | 12 | 12 |

## Instance

* candidates: 59 (classes {'dot': 44, 'lattice': 14, 'both': 1}); hub-capable 12; snap max 97.78145187296604; DOT info `{"n_rows": 61, "n_dot_in_region": 45, "n_dropped": 16, "n_capped": 0, "n_lattice": 15, "n_merged": 1, "n_candidates": 59, "n_dot": 45, "n_lattice_only": 14, "n_both": 1, "n_hub_capable": 12, "hub_fallback_lattice": [], "snap_m_max": 97.78145187296604, "merge_m": 80.0, "cap": 60, "hub_types": ["depot", "lot", "citibike_charging", "fdny_hub"], "types": ["citibike_charging", "depot", "installed", "other", "pilot", "shortlist"], "path": "/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/data/raw/dot_candidate_sites.csv", "file_present": true, "renamed_ids": {}, "verdict_dropped": [], "verdicts_kept": {"corrected": 18, "confirmed": 43}, "reject_tokens": ["drop", "dropped", "reject", "rejected", "exclude", "excluded", "nogo", "out", "outside", "remove", "removed"]}`
* scenarios: 12 in-sample (weights sum 1.0), 12 held out; orders [32, 32, 40, 40, 48, 48, 32, 32, 40, 40, 48, 48]; S_LP [0, 2, 4, 6, 8, 10]
* menu options 10, master binaries 496; budgets m = [1, 2, 3]

## T1 -- bound per budget (relaxed targets, all-candidates library)

UB tier: the library of the pricing that gave the incumbent; an open_sites value is a feasible value of the all-candidates follower (sub-library), so UB is valid for the model of record either way; LB is always all-candidates (LP / cuts / enumeration floor).

| m | best layout | inv USD | UB | UB tier | LB | LB kind | gap % | certified | stop | priced | subset LPs | ILP solves | served |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | D23:SC:B3:C2 | 52,150.000 | 1,085.867 | open_sites | 1,036.029 | master | 4.590 | no | not searched | 3 | 0 | 12 | 0.775 |
| 2 | D07:SC:B3:C2\|D45:SC:B3:C2 | 104,300.000 | 718.912 | open_sites | 670.230 | master | 6.772 | no | not searched | 3 | 0 | 12 | 0.981 |
| 3 | D07:SC:B4:C2\|D45:SC:B4:C2 | 105,200.000 | 709.983 | open_sites | 670.230 | master | 5.599 | no | not searched | 3 | 0 | 12 | 0.985 |

## T2 -- comparison layouts (all priced on the all-candidates tier): regret intervals and paired CIs

regret lo = V - UB (vs the best found), regret hi = V - LB (vs any layout); diff = V - V_best with the plain paired t (11 df at S = 12) and the stratified half-width (6 df); neither is narrow.

Rows of tier open_sites (re-plan change 7): V = V_open is an upper bound on the rule's all-candidates value (UB_rule) and LB rule its all-candidates lower bound (envelope / LP), so the regret interval under the all-candidates follower is [LB_rule - UB*_m, UB_rule - LB*_m]; diff and its CIs compare open_sites values on both sides (V_open - V_open(best); none when the best layout has no open_sites pricing).

| m | layout | key | V | status | tier | LB rule | UB | regret lo | regret hi | V - V_best | CI plain | CI strat | df |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.00 | CSCD | D18:SC:B3:C2 | 1,118.68 | PRICED | open_sites | 1,085.33 | 1,085.87 | -0.54 | 82.65 | 32.81 | 18.37 | 29.64 | 6 |
| 2.00 | CSAV | D30:SC:B3:C2\|D58:SC:B3:C2 | 808.56 | PRICED | open_sites | 671.14 | 718.91 | -47.77 | 138.33 | 89.64 | 40.96 | 37.19 | 6 |
| 2.00 | CSCD | D18:SC:B3:C2\|D19:SC:B3:C2 | 858.33 | PRICED | open_sites | 671.14 | 718.91 | -47.77 | 188.10 | 139.42 | 53.88 | 38.14 | 6 |
| 2.00 | dot_all_pilot | D12:SC:B3:C2\|D18:SC:B3:C2 | 851.27 | PRICED | open_sites | 671.14 | 718.91 | -47.77 | 181.04 | 132.36 | 52.77 | 38.08 | 6 |
| 2.00 | dot_pilot_proxy | D12:SC:B3:C2\|D18:SC:B3:C2 | 851.27 | PRICED | open_sites | 671.14 | 718.91 | -47.77 | 181.04 | 132.36 | 52.77 | 38.08 | 6 |
| 3.00 | CSCD | D18:SC:B3:C2\|D19:SC:B3:C2\|D23:SC:B3:C2 | 830.96 | PRICED | open_sites | 684.33 | 709.98 | -25.65 | 160.73 | 120.98 | 43.52 | 31.65 | 6 |

## T3 -- DOT-only vs full (lattice-only candidates fixed closed; same template, cuts and cache)

price of the restriction: certified range [LB_dot - UB_full, UB_dot - LB_full] (>= 0 when both bounds hold).

| m | DOT sites | UB full | LB full | UB DOT-only | UB DOT tier | LB DOT-only | best DOT-only | certified | price lo | price hi |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 45 | 1,085.87 | 1,036.03 | 1,085.87 | open_sites | 1,036.03 | D23:SC:B3:C2 | no | -49.84 | 49.84 |
| 2 | 45 | 718.91 | 670.23 | 719.60 | open_sites | 670.23 | D23:SC:B3:C2\|D45:SC:B3:C2 | no | -48.68 | 49.37 |
| 3 | 45 | 709.98 | 670.23 | 719.60 | open_sites | 670.23 | D23:SC:B3:C2\|D45:SC:B3:C2 | no | -39.75 | 49.37 |

## T4 -- role table per budget (best / best S-containing / best hub-containing found)

| m | UB | LB | best | V | best with S | V | LP only | best with hub | V | LP only |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1,085.87 | 1,036.03 | D30:SC:B3:C2 | 1,347.61 | - | - | - | - | - | - |
| 2 | 718.91 | 670.23 | D30:SC:B3:C2 | 1,347.61 | - | - | - | - | - | - |
| 3 | 709.98 | 670.23 | D30:SC:B3:C2 | 1,347.61 | - | - | - | - | - | - |

T4b -- the same rows from the open_sites values only (one follower on every side of a difference; V = UB of the all-candidates value; UB / LB are the budget's all-candidates bounds):

| m | UB | LB | best | V_open | best with S | V_open | best with hub | V_open |
|---|---|---|---|---|---|---|---|---|
| 1 | 1,085.87 | 1,036.03 | D23:SC:B3:C2 | 1,085.87 | - | - | - | - |
| 2 | 718.91 | 670.23 | D07:SC:B3:C2\|D45:SC:B3:C2 | 718.91 | D24:S:B3:C0\|D45:SC:B3:C2 | 758.34 | D07:S:B3:C0\|D50:C:B0:C4 | 1,445.77 |
| 3 | 709.98 | 670.23 | D07:SC:B4:C2\|D45:SC:B4:C2 | 709.98 | D24:S:B3:C0\|D45:SC:B3:C2 | 758.34 | D07:S:B3:C0\|D50:C:B0:C4 | 1,445.77 |

## T6 -- out-of-sample (held-out scenarios, shared cache)

| layout | key | tier | V in | V out | out - in | CI out (strat) | status |
|---|---|---|---|---|---|---|---|
| best@m1 | D23:SC:B3:C2 | open_sites | 1,085.87 | - | - | - | SKIPPED_BUDGET |
| best@m2 | D07:SC:B3:C2\|D45:SC:B3:C2 | open_sites | 716.85 | - | - | - | SKIPPED_BUDGET |
| CSCD@m2 | D18:SC:B3:C2\|D19:SC:B3:C2 | open_sites | 858.33 | - | - | - | SKIPPED_BUDGET |
| dot_all_pilot | D12:SC:B3:C2\|D18:SC:B3:C2 | open_sites | 851.27 | - | - | - | SKIPPED_BUDGET |

## T8 -- sizes, timings, coverage

* stages done: search_calib, feas, feas, feas, feas, search_oos_feas, m1, rootlp, rootlp, rootlp, rootlp, rootlp, rootlp, rootlp, rootlp, rootlp, rootlp, rootlp, rootlp, search_price_list, m1, search_ub_check, search_price_list, search_price_list, search_pairs, search_m3, search_roles, comparison, restricted, search_oos, search_noradius

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

## Caveats

* Every ILP value is an upper bound on the unpruned optimum (PRUNING_NYC; approach radius when set); V* is the optimum under the all-candidates library convention.
* Regional bounds use free sizes (design 7.1 item 1) on the S_LP scenarios and the superset value elsewhere.
* Hubs are allowed at the hub-capable candidates only; the role table says what the alternatives cost.
* open_sites values (re-plan): the follower repositions only to open sites and depots; such a value is a feasible value, hence an upper bound, of the all-candidates follower; its ILP bounds hold for the open-sites follower only and are never used as all-candidates lower bounds.
