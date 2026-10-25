# R7 siting re-plan after batch 2: m = 1 and batches 4-6 (planner, 2026-10-22, 23:00 UTC)

Inputs:
- the two diagnosis reports: the records analysis of batch 2, and the server diag on D30 s8 / s11;
- `notes/siting_production_plan.md`, including section 8;
- `notes/DECISIONS.md`, "R7 production code (2026-10-21)";
- `outputs/r7_prod_snapshots/b2/r7_siting/{records,cuts,cost}.jsonl`;
- `outputs/r7_prod_snapshots/diag/r7_diag_server_tester_summary.json`;
- the code paths `SitingCertifier.price` / `_price_open` / `restore` / `certify_by_enumeration` (`benders.py`), `LowerLevelEvaluator.layout_pair` / `evaluate_scenario` / `_solve_scenario` (`bilevel.py`), and `r7_search.py` `stage_price_list`.

No code was edited. One scratch script was written:
`/private/tmp/claude-501/-Users-yuanmingchen-Desktop-Research-SUMO/632dd867-1612-4afe-a6b5-a9fc7fe1d1bd/scratchpad/diag_replan/env_all.py`.

## 0. Bottom line

1. **A 1 % certificate at m = 1 is out of reach under the all-candidates follower** (the model of the paper). The reason is the lower bound:
   - The floor is the LP: D29 at 1034.09, with 12 locations within 4 % of it.
   - A 300 s all-candidates ILP raises a cell bound by only +0.43 % (median); the root LP alone takes 150-300 s.
   - The integer optimum sits about 3.5-4.5 % above the LP (D30: s8 open_sites optimum = LP + 4.5 %, s11 = LP + 3.6 %).
   - So the reachable statement is a gap of about **3-4 % (range 2-5 %)**, not 1 %.
2. **The upper bound can be fixed cheaply, and it unlocks everything else.**
   - Pricing on the open_sites tier is a valid upper bound (it is a sub-library). It solves to OPTIMAL in 47-140 s on the worst cells.
   - Expected best V: about 1065-1085, against 1347.61 now.
   - With UB ≤ 1150, all 69 smaller-size layouts are pruned without another LP: recomputed envelopes are ≥ 1176.0 for the 27 without an LP, and LP values are ≥ 1166.6 for the other 42.
   - The m = 1 enumeration therefore reduces to the 23 B3:C2 layouts, whose LPs are all in `cuts.jsonl` (`lp_memo` restores from it).
3. **The same pricing gives an exact m = 1 optimum under the open_sites follower** (repositioning only to open sites and depots), at no extra cost:
   - The all-candidates LP value of a location is a valid lower bound for both followers.
   - So pricing on open_sites, in LP order, every location with v_LP < best V_open certifies the open_sites optimum by pruned enumeration.
   - This is a second, honest headline: "certified under the restricted follower, bounded within about 3-4 % under the all-candidates follower".
4. **Batches 4-6 switch from all-candidates 300 s pricing to open_sites pricing for every value they report** (V, regrets, out-of-sample, radius effect). Lower bounds keep coming only from LPs, `L_s` (batch 3), the cut pool and subset bounds.
   - The all-candidates 300 s rows add almost nothing: +0.4 % cuts, and incumbents up to 99 % too high.
   - With this switch, batches 4-6 fall from 18.8 h to about 11.7 h.
5. **Remaining cost from now** (batch 3 included, 12 h left): **about 25.3 h = 26.8 USD central (22-32 h, 24-34 USD)**, plus 3.4 h / 3.6 USD if the conditional bound pass (Tier 2) runs.
   - Study total: about 60 USD (57-67), or 64 with Tier 2.
   - That is below the plan's 66 USD central, but above the 50 USD/month line, which the author already allowed.

## 1. Fixed facts reused (no re-solve)

| Item | Value | Source |
|---|---|---|
| Terminal-feasible one-site locations (all 12 scenarios) | 23 of 59; 144 of 236 layouts INFEASIBLE_TERMINAL | `feas_one_site_*.json`, `enumerate` record |
| In-budget sizes (b1 = 52,150) | B3:C2, B3:C1, B2:C2, B2:C1 (92 feasible layouts) | menu; B4 is above b1 |
| B3:C2 location LPs (12 scenarios each, cuts in `cuts.jsonl`) | D29 1034.1, D28 1036.0, D34 1037.2, D33 1043.5, D30 1048.1, D37 1048.2, D23 1049.6, D24 1050.4, D38 1051.3, D25 1065.5, D39 1066.3, D22 1073.7, D31 1079.3, D19 1081.0, D18 1082.6, D16 1085.7, D07 1088.3, D26 1090.7, D17 1096.6, D13 1101.3, D14 1106.7, D20 1120.2, D11 1138.1 | `lp_location` records |
| Smaller sizes | 42 with LP: v_LP 1166.6-1382.3. 27 without LP: envelope (all LP cuts) ≥ 1176.0 (lowest D18:B3:C1 1176.0, D07:B3:C1 1183.7) | `env_all.py` |
| Valid enumeration floor | **1034.09** (D29:SC:B3:C2), valid now and unchanged by any UB | `enumerate` / `final_bound` |
| Priced (all-candidates, 300 s) | D30 1347.61 (lower 1055.39), D18 1558.0, D38 1666.5, D07 UNRESOLVED | `price` records |
| Valid UB available today (diag s8/s11 open_sites schedules, which pass `check` on the all-candidates library) | D30 ≤ 1347.61 − (1/21)(780.74 + 1117.71) = **1257.21** | diag summary; not yet in `records.jsonl` |
| Scenario weights | weekday 1/8.4 = 0.119 each (s0-s5), weekend 1/21 = 0.0476 each (s6-s11) | design |

Projection, assuming each location's opex is its LP × (1 + d), as observed (d = 3.6-4.5 % on D30 s8/s11, 5.3 % on s0):

| d | Best three V (all D29 / D28 / D34) | Gap to floor 1034.09 | Locations with v_LP < UB (cannot be excluded under all-candidates) |
|---|---|---|---|
| 3 % | 1064.7 / 1066.7 / 1067.9 | 2.9 % | 9 |
| 4 % | 1074.9 / 1076.9 / 1078.1 | 3.8 % | 12 |
| 5 % | 1085.1 / 1087.2 / 1088.4 | 4.7 % | 16 |

## 2. Revised m = 1 procedure

### 2.1 Steps

| Step | What | Tier / limits | Threads | Wall | Valid output |
|---|---|---|---|---|---|
| M0 | Code changes 1, 2, 3 (section 4). Laptop tests. Upload. | | laptop | 2-3 h of agent time, 0 server h | |
| M1 (C0, concurrent with batch 3, recommended) | UB pass: `price-list --tier open_sites` on B3:C2 at the 12 locations with v_LP < 1075, in LP order: D29, D28, D34, D33, D30, D37, D23, D24, D38, D25, D39, D22. Separate `--out-dir outputs/r7_siting_ub`, `R7_USD_PER_H=0` (the instance is already billed to batch 3), `nice -n 19`, `--max-rss-gb 30`. | open_sites, 600 s, rule start, full (no BestBdStop) | 2 workers x 2 = the 4 vCPUs batch 3 leaves free | about 4-6 h (144 cells x 100-250 s / 2); stop at 10:30 UTC whatever is left | V_open per location = valid all-candidates UB; open_sites optimum per cell |
| M1-rest (after batch 3, only if C0 did not finish or best V_open > 1073.7) | Remaining cells. Extend the list in LP order while v_LP(next) < best V_open (D31, D19, D18, D16, ...). | open_sites, 600 s | 4 x 3 | 0-1.5 h (central 0.5) | same |
| M2 | Merge C0 into `outputs/r7_siting` (change 3: `price_open` records + cache rows and schedules, same `instance_md5`). | | 1 | 0.1 h | |
| M3 (bound probe, decides Tier 2) | All-candidates on D29 s5 and D29 s2 (weekday, p = 0.119), warm from the open_sites schedule (change 4). Variants: (a) default params, Threads 6; (b) `Method 2`, Threads 6 (the default concurrent root gives barrier one thread out of 3). 1,200 s each, 2 at a time. Record the root LP time, the bound and the node count. | all_candidates | 2 x 6 | 0.7 h | valid cell bounds (all-candidates ILP best bound) |
| M4 (m1 resume, no pricing) | `r7_siting.py --stage m1` with `--m1-pass2 off` (change 5) and `--max-escalations 0`. The restore puts V_open into UB. Pass 1 prunes all 27 smaller sizes without an LP and re-uses 65 restored LPs. Pass 2 only tests prunes. `finish` writes `budget_result` with LB = floor and UB = best V_open. | none | 2 | 0.3 h | the official m = 1 bound pair |
| M5 (Tier 2, conditional) | **Only if** M3 shows a mean bound lift ≥ 1.0 % over the cell LP at 1,200 s in the better variant. All-candidates bound jobs on the 6 weekday cells of D29, D28, D34 (18 cells, the M3 cells re-used), warm start, best variant, 1,200 s, then M4 again. | all_candidates | 2 x 6 | 3.4 h (2.6-4.5) | floor about 1038-1042 (D29 +0.5-1 % on weekday weight 0.714) |
| M6 (optional check, 0.2 h) | For the headline layout: `check` its 12 open_sites schedules on the all-candidates layout library. Change 4 records this as `ub_check_all_candidates`. | | 3 | 0.2 h | explicit validity record for the paper's UB |

Rules:
- No all-candidates 300 s pricing in m1 any more: M4 skips pass 2 pricing.
- Escalation is replaced by M3 / M5. They target only the cells whose bound can move the floor: the weekday cells of the 3 lowest-LP locations.
- The floor is min over D29, D28, D34 and then D33 (1043.5). Lifting only D29 does not move it past 1036.0, so M5 is all three or nothing.

### 2.2 Expected m = 1 result (all-candidates follower)

| Case | UB (best V_open) | LB (floor) | Gap | Locations not excluded |
|---|---|---|---|---|
| Tier 1 (M1-M4), d = 3 / 4 / 5 % | 1064.7 / 1074.9 / 1085.1 | 1034.09 | 2.9 / 3.8 / 4.7 % | 9 / 12 / 16 of 23 |
| Tier 1 + Tier 2 (lift 0.5 / 1 % on weekday cells) | as above | 1037.8 / 1041.6 | 2.5-4.4 % / 2.2-4.0 % | unchanged: Tier 2 lifts only 3 locations |

Under the **open_sites follower**, the same M1 data certify the optimum:
- A location is either priced on open_sites (all 12 cells OPTIMAL, expected), or pruned because v_LP (all-candidates LP ≤ all-candidates V ≤ open_sites V) ≥ best V_open − tol.
- Smaller sizes are pruned the same way through their envelope or LP.
- The resulting gap is the largest open_sites MIP gap: about 0, at most 0.25 % with `tol-rel 0.0025`.
- It needs every location with v_LP < best V_open (minus tol) priced. That is 9-16 locations, which M1 + M1-rest already does.

## 3. Batches 4-6: changes and walls

Common change: the reported value of every layout is its **open_sites** pricing.
- 600 s; 900 s for layouts with 5 or more open sites (DOT all-pilot), where the open_sites library approaches the all-candidates size.
- 4 workers x 3 threads; no templates needed (`layout_pair` builds open_sites libraries with `build_arcs`).
- `verify_start` is off for check-clean starts (change 6).

All-candidates ILP pricing is dropped from these stages. Lower bounds come from:
- subset LPs (pair screens, hub screen);
- the layout envelope (`lp=False`), `L_s` from batch 3, and the master pool.

Two paired-difference results become exact differences between open_sites optima: the radius effect and V_out − V_in.

| Lane | Old pricing (wall) | New | New wall | Hours (central / range) |
|---|---|---|---|---|
| b4_pairs | 16 pair screens (subset LPs on S_LP = 6) + 4 pairs at all-candidates 300 s (5 h) | Screens unchanged (valid pair bounds). The top 4 non-excluded pairs priced open_sites → UB_2. | 4 | 3.4 / 2.9-4.2 |
| b4_m3 | 3-5 triples at all-candidates 300 s (2 h) | open_sites | 1 | 0.6 / 0.4-0.9 |
| b4_roles | hub screen LPs + 2 hub layouts at 600 s all-candidates (3.5 h) | Screen unchanged; the role layouts (SC+SC, SC+S, hub+S) priced open_sites at 600 s (hub limit) | 2.5 | 2.2 / 1.8-2.8 |
| (b4 10 %) | | | | 0.6 |
| b5_comparison | CSCD m = 1-3, CSAV m = 2, DOT all-pilot, DOT pilot proxy m = 2 at all-candidates (m = 2 rows 600 s) (4 h) | open_sites for all rows. Regret interval [LB_rule − UB*_m, UB_rule − LB*_m] with LB_rule = max(envelope, LP). Paired CIs on open_sites values (same follower for both sides). | 2 | 1.3 / 1.0-1.9 |
| b5_restricted | DOT-only restricted master + up to 2 pricings (1 h) | pricings open_sites | 1 | 0.7 / 0.5-1.0 |
| b5_oos | 4 layouts x 12 held-out at all-candidates (2 h) | open_sites on held-out; V_in from the in-sample open_sites values | 1 | 0.9 / 0.7-1.3 |
| (b5 10 %) | | | | 0.3 |
| b6_noradius | about 6 layouts, no radius, all-candidates (5 h; root LP cannot finish at x1.9 arcs) | open_sites without radius against open_sites with radius: the radius effect is measured exactly under one follower. No `--noradius-group` eviction needed. | 2 | 1.5 / 1.2-2.4 |
| (b6 10 %) | | | | 0.2 |
| **Batches 4-6** | 18.8 h | | | **11.7 / 9.3-15.9** |

The pair seeds of b4_pairs (`D30+D38 D09+D38`) were chosen from the N = 40 transplant. Add the two best m = 1 locations by V_open, which the stage already does ("the two best m = 1 locations"), once M1 is merged.

Optional, not in the total: an all-candidates bound pass for the best pair (12 cells, 1,200 s, 2 x 6, warm), about 1.8 h. Run it only if the m = 2 gap is to be quoted below about 8 %.

## 4. Code changes (ordered smallest first; proposals only)

| # | Change | Where | Size | Needed by | Test |
|---|---|---|---|---|---|
| 1 | `restore` reads `price_open` records into `priced_open` and `UB` (in-menu layouts only). Never into `priced`, cuts or the floor. | `benders.py` `SitingCertifier.restore` | about 15 lines | M4, b4-b6 resume | Toy: emit `price_open`, new certifier, UB restored; `priced`, pool size and floor unchanged. |
| 2 | `price-list --tier {all_candidates,open_sites}` (evaluator `in`) calling `cert.price(lay, full=True, tier=...)`. Resume skips layouts with a final `priced_open`. | `r7_search.py` `stage_price_list`, `price` | about 15 lines | M1 | Toy: `price_open` emitted, UB set, no new cut, re-run makes 0 solves. |
| 3 | `--stage import-records --from DIR`: append the `price_open` / `price` records with the same `instance_md5`; copy cache index rows and schedule files whose key is absent. | `r7_search.py` | about 40 lines | M2 | Toy with two out-dirs: same UB and cache hits as a single-dir run. |
| 4 | Warm all-candidates from open_sites. `price_layout(..., warm_tier='open_sites')` passes the open_sites sibling's cached schedule of (layout, s) as `warm` to `evaluate_scenario` (whose `warm_parent` logic already exists). It records `ub_check_all_candidates` (materialise + `check` result and cost). | `benders.py` `price_layout(_parallel)`, `bilevel.py` cache lookup | about 30 lines | M3, M5, M6 | Toy: `mip_start_variant == warm_parent` when better; all-candidates total ≤ open_sites total; check ok; cuts identical to a cold run. |
| 5 | `--m1-pass2 off`: `certify_by_enumeration(price_pass=False)` tests prunes but does not price; the floor is computed as now. Also a `--cells L:s,...` filter and `--ilp-params K=V` for price-list (params enter the cache key → new rows, by design). | `benders.py`, `r7_siting.py`, `r7_search.py` | about 30 lines | M3-M5 | Reduced-6 m1 resume with an injected UB: smaller sizes envelope-pruned, 0 ILP solves, floor equals the pre-resume floor; params change the key. |
| 6 | `verify_start=False` when the MIP start already passed `check` (rule or warm). Not in the cache key. | `bilevel.py` `_solve_scenario` → `run_ilp_case` | about 10 lines | all pricing (saves up to 60 s/cell) | Toy totals identical with and without; `R7_REPRO` keys unchanged. |
| 7 | `--price-tier {all_candidates,open_sites}` for pairs, m3, roles, comparison, restricted, oos, noradius (production lanes pass `open_sites`; default stays `all_candidates` so older families are unchanged). The noradius stage pairs open_sites with and without radius. Tables show UB (open_sites) and LB (envelope / LP / subset) columns; the comparison regret uses LB_rule. | `r7_search.py`, `r7_siting.py` `stage_comparison` / `stage_restricted` | about 120 lines | b4-b6 | Toy: each stage emits `price_open`, pool signature unchanged, regret interval contains the exhaustive toy regret. |
| 8 | Analyse: m = 1 dual statement. All-candidates [floor, UB] plus the list of locations with lower < UB. Open_sites certificate: every location priced OPTIMAL or v_LP ≥ UB_open − tol. | `r7_siting.py --stage analyse` | about 40 lines | paper | Toy: the open_sites certificate equals exhaustive open_sites enumeration at m = 1. |
| 9 | Lane plan (b2b_ub concurrent, b2b_probe, b2b_m1, b2b_tier2, revised b4-b6 flags and walls), `r7_prod_check.sh` markers for 1-8, zip rebuild. | `deploy/aws`, `outputs/cloud_lanes_siting_prod` | | all | Full `pytest -q tests/` green, `R7_REPRO=1 ... -k reproduced` green, the reduced-6 `feas,rootlp,m1` smoke plus an M1 → M4 resume smoke, `--write-lanes` diff reviewed, CJK scan of the zip clean. |

Minimum for C0 to start during batch 3: changes 1, 2 and 3, about 70 lines plus tests.

## 5. Hours and USD (r7i.4xlarge on-demand, 1.0584 USD/h)

| Item | Hours central (range) | USD central (range) |
|---|---|---|
| Spent: probes before production (plan 2.2) | about 12 | about 13 |
| Spent: batch 1 (03:55-08:40 UTC) | 4.74 | 5.02 |
| Spent: batch 2 (m1) | 13.23 | 14.00 |
| Batch 3 (running, until about 11:00 UTC 2026-10-23; 1 h done) | 13 (+0-1.5 if C0 slows it) | 13.8 (+0-1.6) |
| m1 Tier 1 after batch 3 (M1-rest, M2, M3, M4; C0 itself billed in batch 3) | 1.6 (1.1-3.0; without C0: 2.9, 2.0-4.5) | 1.7 (1.2-3.2) |
| m1 Tier 2 (conditional) | 3.4 (2.6-4.5) | 3.6 (2.8-4.8) |
| Batches 4-6 revised | 11.7 (9.3-15.9) | 12.4 (9.8-16.8) |
| **Remaining from now (batch 3 rest 12 h + Tier 1 + b4-b6)** | **25.3 (22.4-32.4)** | **26.8 (23.7-34.3)** |
| Remaining with Tier 2 | 28.7 (25.0-36.9) | 30.4 (26.5-39.1) |
| **Study total** | | **about 60 (57-67); 64 with Tier 2 (60-72)** + EBS |

Notes:
- C0 risk: on 8 physical cores, 4 more threads on the free vCPUs share cores with the batch-3 barrier solves.
- Stop C0 if the summed RSS goes above 100 GB, and stop it at 10:30 UTC.
- If the author prefers no risk to batch 3, skip C0. Running everything after batch 3 costs 1.3 h (1.4 USD) more.
- The instance stops between batches (watchdog); the start-ups are included above.

## 6. What the paper can claim per budget

Scope throughout: N = 59, S = 12 in-sample, relaxed targets, 8 bikes, radius 14 with start-state exemption.

| Budget | Claim (valid) | Expected numbers | Cannot claim |
|---|---|---|---|
| m = 1, all-candidates follower (model of record) | Best site D* with V ≤ UB (feasible schedules). The optimum is ≥ floor (pruned enumeration over all 236 layouts: 144 infeasible alone, 69 smaller sizes dominated by envelope / LP, 23 B3:C2 by LP or ILP bound). Near-tie list of the locations with lower < UB. | Gap 2.9-4.7 % (Tier 1), 2.2-4.4 % (Tier 2); 9-16 locations not excluded | ε ≤ 1 % (the plan's section 3 expectation of 1-1.5 % is withdrawn) |
| m = 1, open_sites follower | Certified optimum (pruned enumeration, open_sites cells OPTIMAL), and the full ranking of the 9-16 priced locations | gap ≈ 0 (≤ 0.25 %) | that it equals the all-candidates optimum |
| m = 2 | Incumbent UB_2 (open_sites); LB_2 = min(LB_1, setup + Σ p_s L_s + pool) with window rows; valid pair bounds for the 16 screened pairs; pairs excluded only when bound_exact ≥ UB_2 − tol | Gap about 6-10 %. The plan's 5-8.5 % assumed ILP ≈ LP + 1 %; the measured ILP/LP is 1.03-1.05. | a certified pair optimum |
| m = 3 | Incumbent + the same kind of bound; "no improving third site found" | gap ≥ m = 2 gap | that a third site does not pay |
| Comparisons | Paired differences between open_sites values (exact under that follower, stratified and plain CIs); regret intervals under the all-candidates follower [LB_rule − UB*, UB_rule − LB*] | | point regrets under the all-candidates follower |
| Role table, out-of-sample, radius effect | Measured on open_sites optima; the radius effect is exact under the open_sites follower | | the radius effect under the all-candidates follower |

What would be needed for ≤ 1 % at m = 1 under the all-candidates follower:
- Either a stronger template LP (valid inequalities that close the 3.5-4.5 % integrality gap), or all-candidates ILPs proved to near-optimality at 9-12 locations x 12 scenarios.
- The second route is extrapolated at 12-24 h or more, with no evidence it closes: N = 40 was still at the root after 300 s.
- Neither is in this plan.

## 7. Commands (after changes 1-3, 5 and 9 are uploaded and gated)

```bash
cd ~/battery_swap/ebike_swap_sim
COMMON="--family manhattan_dot --scenarios 12 --approach-radius 14 --tol-rel 0.01 --tol-abs 1 --restrict dot"
TOP12="D29:SC:B3:C2 D28:SC:B3:C2 D34:SC:B3:C2 D33:SC:B3:C2 D30:SC:B3:C2 D37:SC:B3:C2 D23:SC:B3:C2 D24:SC:B3:C2 D38:SC:B3:C2 D25:SC:B3:C2 D39:SC:B3:C2 D22:SC:B3:C2"
# M1 (C0), concurrent with batch 3; billed to batch 3
R7_BATCH=2b R7_INSTANCE=r7i.4xlarge R7_USD_PER_H=0 nice -n 19 python3 experiments/r7_search.py --stage price-list \
  --evaluator in --tier open_sites --layouts $TOP12 --time-limit 600 --price-workers 2 --threads 2 --max-threads 4 \
  --lp-workers 1 --lp-threads 1 --master-threads 1 --wall 11 --max-rss-gb 30 --out-dir outputs/r7_siting_ub $COMMON
# after batch 3: M2 merge, M1-rest (same command, 4 x 3, R7_USD_PER_H=1.0584, out-dir outputs/r7_siting), M3 probe, M4
python3 experiments/r7_search.py --stage import-records --from outputs/r7_siting_ub --out-dir outputs/r7_siting $COMMON
R7_BATCH=2b R7_INSTANCE=r7i.4xlarge R7_USD_PER_H=1.0584 python3 experiments/r7_search.py --stage price-list --evaluator in \
  --tier all_candidates --layouts D29:SC:B3:C2 --cells D29:5 D29:2 --warm-tier open_sites --ilp-params Method=2 \
  --time-limit 1200 --price-workers 2 --threads 6 --max-threads 12 --wall 1 --max-rss-gb 110 --out-dir outputs/r7_siting $COMMON
R7_BATCH=2b R7_INSTANCE=r7i.4xlarge R7_USD_PER_H=1.0584 python3 experiments/r7_siting.py --stage m1 --m1-pass2 off \
  --max-escalations 0 --wall-m1 1 --lp-workers 1 --lp-threads 2 --master-threads 2 --price-workers 1 --threads 1 \
  --max-threads 4 --max-rss-gb 110 --out-dir outputs/r7_siting $COMMON
```

The default-params probe variant is the same command without `--ilp-params`. Tier 2 (M5) is the probe command with `--layouts D29:SC:B3:C2 D28:SC:B3:C2 D34:SC:B3:C2 --cells` over the weekday scenarios 0-5 of each, followed by M4 again.

## Critic corrections (critic, 2026-10-22, after 23:00 UTC)

Checked against the batch 2 snapshot (`outputs/r7_prod_snapshots/b2/r7_siting/records.jsonl`, `cuts.jsonl`, `cost.jsonl`, lane statuses, `lanes.txt`), the diag summary (`outputs/r7_prod_snapshots/diag/r7_diag_server_tester_summary.json`) and the code (`benders.py` `price_layout`, `price_layout_parallel` / `_price_plan`, `SitingCertifier.price` / `_price_open` / `restore` / `warm_start` / `enumeration_floor`; `bilevel.py` `layout_pair`, `cache_key`; `sites_nyc.py` `siting_pruning`, `reposition_targets`; `r7_siting.py` `Ctx.certifier`, `rss_gb`, `stage_m1`; `r7_search.py` `stage_price_list`, `price`, `finish`). No code was edited. Scratch check: `/private/tmp/claude-501/-Users-yuanmingchen-Desktop-Research-SUMO/632dd867-1612-4afe-a6b5-a9fc7fe1d1bd/scratchpad/diag_critic/check1.py`.

### K1. Verified as stated (no change)

- V(D30) = 13.19 + sum_s p_s opex_s = 1347.61; replacing s8 / s11 by the diag open_sites schedules gives **1257.21**. The cache `total` includes the setup (1699.33 = 1686.14 + 13.19), and so do the diag values; the setup cancels in the differences, so the number is right.
- The open_sites library is a sub-library of the all-candidates library by construction, not only empirically. Both are `build_arcs` with the same `default_pruning` options and the same radius dict. Only `reposition_targets` differs (the open nodes plus depots, a subset of all candidates plus depots). Dominance is target-independent, and reachability pruning is monotone in the arc set. So every open_sites schedule is feasible on the all-candidates library at the same cost, and V_open is a valid UB for the model of record.
- `_price_open` adds no cut, never enters `priced` and does not emit `lb`/`lower`. `restore` ignores `price_open` today, so change 1 is needed.
- The 23 B3:C2 LPs and the 42 smaller-size LPs are restorable: 780 `lp` cuts tagged `layout` = 65 layouts x 12 scenarios.
- The LP ranking, the d = 3 / 4 / 5 % projections of V (1064.7 / 1074.9 / 1085.1) and gaps (2.9 / 3.8 / 4.7 %), and the Tier 2 floors (1037.8 at a 0.5 % lift, 1041.6 at 1 %) all reproduce.
- The regret interval [LB_rule - UB*, UB_rule - LB*] is valid. So are LB_2 = min(LB_1, ...) and the m = 1 floor (min over all 236 layouts).
- Arithmetic of sections 3 and 5 is internally consistent: 11.7 h, 25.3 h = 26.8 USD, and 28.7 h = 30.4 USD.

### K2. Bound and certificate claims that need correcting

1. **"The integer optimum sits about 3.5-4.5 % above the LP" is an open_sites number, not the all-candidates optimum.**
   - On D30 s8 the all-candidates optimum lies in [LP + 0.8 %, LP + 4.5 %]: opex 873.3 (ILP bound, run a) to 905.4 (open_sites optimum), against Qs = 866.2.
   - So "1 % at m = 1 is out of reach" is a projection, not a measurement. The defensible wording is: "not reachable in this plan, because the floor is set by LPs at 9-15 locations and 300-1,200 s ILPs lift a cell bound by about 0.4-0.8 %."
2. **The open_sites certificate tolerance is inconsistent.**
   - Section 2.2 says "at most 0.25 % with `tol-rel 0.0025`". Section 7 and every production lane use `--tol-rel 0.01`.
   - Batch 2 also ran at 1 %, so the m1 prune line was UB - 13.48 = 1334.13, not 1344.24 as the batch-2 records analysis assumed. 33 of the 42 smaller-size LPs were below it, not 39.
   - Under 1 %, pruning at UB_open - tol gives a 1 % open_sites certificate, not about 0.
   - To claim about 0, change 8 must use tol = 0 for the open_sites statement: price every location with v_LP < UB_open, and report gap = (UB_open - min over locations of [open_sites lower if priced, else v_LP]) / UB_open.
3. **Location counts.**
   - With v_LP < UB, d = 5 % leaves **15** locations, not 16 (D16 1085.7 > 1085.1).
   - With the 1 % tolerance actually applied, the counts are 9 / 9 / 12 at d = 3 / 4 / 5 %.
4. **The UB projection is optimistic.** It rests on three cells of one layout (D30 s0 / s8 / s11).
   - The level-1.0 all-candidates cells had median incumbent/LP - 1 of 5.2 % (weekday) and 6.5 % (weekend).
   - Add a d = 7 % row: UB about 1105.5 (D29), gap 6.5 %, and 20 locations with v_LP < UB. The open_sites certificate would then need 8 more locations priced in M1-rest (about 1.7 h at 4 x 3).
   - The pruning of all 69 smaller sizes is robust. With tol 1 % it holds for any UB up to 1178.4 (smallest smaller-size LP 1166.6 / 0.99), and for the 27 without an LP up to 1187.9. That is d up to about 14 %, not just UB <= 1150.
5. **A new open_sites risk: infeasible or very high values at some locations.**
   - Under open_sites, the only reposition targets are the open site and the depots. With the approach radius, a bike more than 14 blocks from the site can reach it only through a depot within 14 blocks, or through a delivery ending nearby. Under all-candidates it can relay through closed candidates.
   - So some LP-best locations may give V_open far above LP + 5 %, or INFEASIBLE_TERMINAL / no start. This is measured only at D30.
   - Validity is unaffected: such a location simply gives no UB, and under the open_sites follower it is correctly excluded. But the expected UB may then come from a location further down the LP list.
6. **Tier 2 has a hard cap.**
   - D33's LP (1043.54) bounds the floor unless D33 is lifted too. Tier 2 can therefore improve the gap by at most (1043.54 - 1034.09) / UB, about 0.9 points; 0.35-0.7 points is expected.
   - M3 alone moves the floor by 0, because D28 (1036.0) caps it after D29.
   - So M3 + M5 cost about 4.5 h / 4.8 USD for at most 0.9 gap points. Recommendation: run M3 only if the author needs the m = 1 gap below a threshold that 0.9 points can cross. Otherwise skip both and save 0.85 h.
7. **Open_sites row bounds must never be labelled as an all-candidates LB.**
   - `price_layout(tier='open_sites')` folds open_sites ILP bounds into `res.lb`.
   - `_price_open` drops them. But `price_cells` / `assemble` (used by `--evaluator out` and noradius) return `res.lb`, and change 7 routes more stages through open_sites.
   - Every table built by change 7 must label these as "open_sites LB" (valid only for that follower) and take the all-candidates LB only from envelope, LP, `L_s`, subset cuts or all-candidates ILP bounds.
   - Also, `PRUNED_BY_BOUND` on an open_sites evaluator with `full=False` proves nothing about the all-candidates value. Change 7 must call open_sites pricing with `full=True` only, as `_price_open` does.

### K3. Code-path corrections (proposals only)

1. **The `--cells` filter in change 5 does not work as the re-plan assumes.** In `price_layout` and `_price_plan`, `scenarios=` only stops re-solving of *cached* cells outside the filter; an uncached cell is solved anyway.
   - D29 has no all-candidates rows. So M3 as written would solve all 12 cells: about 2 h plus overhead per variant, not 20 min. M5 would solve all 36 cells: about 6 h plus overhead.
   - Change 5 must skip uncached cells outside the filter and keep lb_s = LP Qs_s there; the result is UNRESOLVED, and `lower` still enters the floor through `enumeration_floor`, which is correct.
   - Test: on a toy, `n_solves == len(cells)`.
2. **`--max-rss-gb` is not a running cap.** `rss_gb()` is this process's peak RSS (`ru_maxrss`), and `rss_guard` is checked only at stage entry (and before m1 warm pricing). So `--max-rss-gb 30` neither caps C0 during its run nor sees batch 3.
   - "Stop C0 above 100 GB summed" needs an external watcher, which is not in the plan.
   - If memory runs out, the kernel OOM killer picks the largest process, which is a batch-3 root-LP lane, not C0.
   - Launch C0 under `choom -n 1000 --` (or write 1000 to `/proc/self/oom_score_adj` in the wrapper; no root needed to raise it). Add a 60 s loop that kills C0 when `MemAvailable` drops below 12 GB.
   - Expected C0 footprint: 3-8 GB. The diag peak was 6.3 GB in a process that also held an 11.3 M-arc all-candidates library; open_sites libraries have 1.3-2.0 M arcs.
3. **`--wall 11` does not match "stop at 10:30".** Pass `--wall` equal to the hours left to 10:30 at launch (about 8 if C0 starts at 02:30), so the wall budget stops C0 cleanly instead of a kill mid-wave.
4. **M2 import (change 3) must exclude C0's `budget_result` / `final_bound` / `stage_done` records.** `finish()` in price-list writes a `budget_result` with a near-trivial LB: L_s = 0, empty pool. `restore_prior_lb` takes the max, so bounds stay valid. But `last_results` (report, analyse) would show that weak pair as the latest m = 1 result.
5. **M6 should be mandatory for the layout that sets UB_1** (0.2 h). K1 shows the subset relation holds by construction. Still, the paper's headline UB should carry an explicit `check` record, and the cost is negligible.
6. **M3 / M5 thread layout.** 2 x 6 = 12 threads on 8 physical cores oversubscribes them for barrier, which is bandwidth-bound. Use 2 x 4 (or 1 x 8) at the same wall.
   - The claim that the default MIP root gives barrier one thread out of 3 is not verified locally. Read it from the diag Gurobi logs in `~/battery_swap/ebike_swap_sim/outputs/r7_diag` before choosing `Method 2`.

### K4. Thread and memory budget beside batch 3

- Batch 3 runs 3 chains x 4 threads = 12 solver threads. That already equals the project's own `--max-threads` rule (1.5 per physical core, `default_max_threads`). The chains are s04 -> s11 -> s08 -> s01, s05 -> s02 -> s09 -> s06 and s10 -> s03 -> s00 -> s07, about 2.98 h per root LP, started 21:56:37; the end is about 10:00-11:00 UTC.
- C0 adds 4 threads, giving 16 on 8 physical cores. `nice -n 19` protects CPU time slices but not hyperthread-sibling or memory-bandwidth contention, and the barrier root LPs are sensitive to both.
- A batch-3 slowdown of 0-12 % (0-1.5 h) is plausible. That is the same size as C0's saving (1.3 h).
  - **C0's expected net cost saving is therefore about 0.** Its real value is earlier information: UB_1, the M3 / Tier 2 decision and the batch 4 seeds are ready when batch 3 ends.
  - Keep C0, but count +0.5 h for contention in the central case.
  - Stop C0 if the first second-round root LP (s11 / s02 / s03, which start around 01:00 UTC) runs more than 10 % above its plan time.
- Memory: batch 2's m1 peaked at 103.8 GB and calibration at 65.2 GB, but batch 3's per-lane RSS is not in the local snapshot.
  - Check `free -g` before launch, and only start C0 if at least 25 GB is available.
  - C0's own 3-8 GB is then low risk, provided the OOM ordering in K3.2 is set.

### K5. Hours corrections

| Item | Re-plan | Corrected | Reason |
|---|---|---|---|
| C0 wall | 4-6 h | 4.5-8 h | 144 cells x (solve 47-600 s + open_sites overhead about 60-120 s), in waves of 2 that wait for the slower cell (about 1.3x the mean). Starts about 02:30 after M0 and gates; the window to 10:30 is about 8 h, so 9-12 locations are expected. |
| Batch 3 rest | 12 h (+0-1.5) | 12.5 h (12.0-13.5) | K4 contention, central +0.5 h |
| M1-rest | 0.5 (0-1.5) | 0.5 (0-1.7) | the d = 7 % case needs 8 more locations |
| M3 | 0.7 | 0.85 (0.7-1.1) | 4 solves x 1,200 s, 2 at a time, plus about 200 s per cell of library / build / verify overhead and 2 templates |
| M4 | 0.3 | 0.5 (0.4-0.6) | the batch-2 m1 setup alone (certifier, 12 templates) took 0.42 h, 08:40:47-09:05:41 |
| M6 | optional | 0.2, mandatory | K3.5 |
| **Tier 1 after batch 3** | 1.6 (1.1-3.0) | **2.2 (1.4-3.7)** | 0.5 + 0.1 + 0.85 + 0.5 + 0.2 |
| **Tier 2** | 3.4 (2.6-4.5) | **3.7 (3.0-4.8)** | 16 new cells x 1,200 s / 2 = 2.67 h, plus overhead 0.45 h, plus M4 again 0.5 h; capped benefit (K2.6) |
| Batches 4-6 | 11.7 (9.3-15.9) | 11.7 (9.3-15.9), unchanged | Unmeasured for open_sites at m >= 2 and at 5+ sites, where the open_sites library approaches all-candidates size and the root-LP problem returns. Report those cells' status; "exact" differences only where both sides are OPTIMAL. |

### K6. Corrected totals (r7i.4xlarge on-demand, 1.0584 USD/h)

Spent so far:
- Probes: about 13 USD.
- Batch 1: 03:55:09-08:40:32 = 4.76 h, 5.03 USD.
- Batch 2: 08:40:47-21:56:22 = 13.26 h, 14.03 USD.
- Batch 3 to 23:00: 1.06 h, 1.12 USD.
- **Total: about 33.2 USD.**

| | Hours central (range) | USD central (range) |
|---|---|---|
| Batch 3 rest | 12.5 (12.0-13.5) | 13.2 (12.7-14.3) |
| m1 Tier 1 after batch 3 | 2.2 (1.4-3.7) | 2.3 (1.5-3.9) |
| Batches 4-6 | 11.7 (9.3-15.9) | 12.4 (9.8-16.8) |
| **Remaining from now, Tier 1** | **26.4 (22.7-33.1)** | **27.9 (24.0-35.0)** |
| m1 Tier 2 (conditional, at most 0.9 gap points) | 3.7 (3.0-4.8) | 3.9 (3.2-5.1) |
| **Remaining with Tier 2** | **30.1 (25.7-37.9)** | **31.9 (27.2-40.1)** |
| **Study total** | | **about 61 USD (57-68); 65 with Tier 2 (60-73), + EBS** |

- If M3 is skipped (K2.6), subtract 0.85 h / 0.9 USD.
- All of this lands in October 2026. That is about 11 USD over the 50 USD/month line (15 with Tier 2), which the author allowed under plan section 8. It must be reported as such.

### K7. Corrected expected m = 1 result (all-candidates follower)

| d (open_sites opex / LP - 1) | UB (D29) | LB | Gap | Locations with v_LP < UB | Open_sites certificate needs priced |
|---|---|---|---|---|---|
| 3 % | 1064.7 | 1034.09 | 2.9 % | 9 | 9 (M1 covers) |
| 4 % | 1074.9 | 1034.09 | 3.8 % | 12 | 12 (M1 covers) |
| 5 % | 1085.1 | 1034.09 | 4.7 % | 15 | 15 (+3 in M1-rest) |
| 7 % | 1105.5 | 1034.09 | 6.5 % | 20 | 20 (+8 in M1-rest) |
| Tier 2 lift 0.5 / 1 % | as above | 1037.8 / 1041.6 (cap 1043.5) | 2.5-6.1 % / 2.2-5.8 % | unchanged | unchanged |

Tier 1's gap is therefore 2.9-6.5 % (central 3.8-4.7 %), not 2.9-4.7 %.

## Re-plan code status (2026-10-23)

Gate run on the laptop at about 05:35 UTC (nice -n 15, Gurobi Threads 1; toy, reduced-6 and dry runs only; no ssh, nothing uploaded). Settings: `--tol-rel 0.01` in every production lane; the analyse stage reports the open-sites gap with tol = 0 (K2.2). Main-loop decision: no concurrent C0 lane; everything below starts only after batch 3 (about 11:00 UTC) at the full 12-thread budget (4 x 3 pricing).

| Check | Result |
|---|---|
| Full suite `pytest -q tests/` | **482 passed, 1 skipped, 0 failed** (15.6 min). The skip is the opt-in reproduction, run separately below. The six r6_fill solver smokes ran this time (enough free swap). |
| `R7_REPRO=1 pytest tests/test_r7_siting.py -k reproduced` | **1 passed** (149 cache keys of `r6_o2/manhattan_pass2`, 55 s) |
| r5_manhattan pool signature through the r7 path | `ed744dafc64e8f7e7384606bc0fd5c42` for both targets (relaxed and written) |
| Production `instance_md5` / `config_md5` (manhattan_dot, S = 12, radius 14, tol-rel 0.01, restrict dot) | `815886906f1a6cc2e6437e6de890f891` / `8c9cfcddf7846e6b36ee0d2a72027769`, equal to the batch-2 records: `outputs/r7_siting` resumes, the records of batches 1-3 stay valid |
| `outputs/r7_siting_probe/upload/r7_code.zip` | rebuilt from the current tree: 109 files, 1,241,817 bytes, md5 `9ced13a0b5e3e7d60d04b7612e402307`. Contents: `data/raw/dot_candidate_sites.csv`; `deploy/aws/*` without `aws_env*.sh`, `README_AWS.md` and `__pycache__`; `ebike_swap_sim/{CONTRACT.md,README.md,pytest.ini}`; the `*.py` of the package, `experiments` and `tests`; `outputs/cloud_lanes_siting_prod/lanes.txt`, `lanes.json`, `lanes_r2.txt/.json`, `lanes_r2_tier2.txt/.json`. All 109 files md5-identical to the tree (checked again after the suite), 0 CJK, no secrets, unix modes kept (the `.sh` files stay executable). Its file contents equal `r7_code_r2.zip` (01:18 build) file by file, so either zip installs the same tree. The batch 1-3 zip (md5 `908abb1b...`) is kept in the session scratchpad only. |
| Unzipped copy | `r7_prod_check.sh --root <copy> --no-probe`: exit 0, 69 markers, lanes.txt 27 lanes (`b0_gate` first), lanes_r2.txt 13 (`r2_gate` first), lanes_r2_tier2.txt 3 (`r2t2_gate` first). `r7_gate.py`: 35 markers ok. `run_lanes.sh start lanes_r2.txt --max-threads 12 --dry-run`: 13 lanes, only `r2_gate` would start, the rest queue in the chain gate -> M1 -> M4 -> M6 -> batches 4-6 (M3 probes off M6). `r7_cost.py` on the batch-2 snapshot runs. |

**Server commands** (project root `~/battery_swap`, `r7_code.zip` copied there by the author; run in this order):

```bash
cd ~/battery_swap
export LANES_DIR=$PWD/ebike_swap_sim/outputs/cloud_lanes_siting_prod
LF1=ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt
LF=ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes_r2.txt

# 1. wait for batch 3: all 12 b3_rootlp lanes must show 'done' and none 'running'
bash deploy/aws/run_lanes.sh status $LF1
tmux ls 2>/dev/null                     # no lane_b3_* session left

# 2. stop the old dispatcher ONLY once every b3 lane is done ('stop all' also kills running lanes;
#    the dispatcher normally exits by itself, then this is a no-op). Do it before the unzip:
#    the dispatcher's bash reads run_lanes.sh lazily and the zip replaces that file.
bash deploy/aws/run_lanes.sh stop all
tmux has-session -t lanes_dispatch 2>/dev/null && echo "dispatcher still running: do not continue"

# 3. unpack the re-plan code and run the pre-flight check (exit 0 required; 2 = stale code / lane plan)
unzip -o r7_code.zip
bash deploy/aws/r7_prod_check.sh --no-probe

# 4. start the r2 lanes (dry run first; r2_gate runs experiments/r7_gate.py, then the chain follows)
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --dry-run
bash deploy/aws/run_lanes.sh start $LF --max-threads 12

# 5. watch, and cost per batch (R7_BATCH=2b, 4, 5, 6 rows in outputs/r7_siting/cost.jsonl)
bash deploy/aws/run_lanes.sh status $LF
bash deploy/aws/run_lanes.sh logs r2_m1_ub 40
cd ebike_swap_sim && python3 experiments/r7_cost.py outputs/r7_siting
```

Tier 2 (`lanes_r2_tier2.txt`) is started by hand only if the `probe_summary` record of `r2_m3probe_b` (or `r7_search.py --stage report`) gives the verdict to run it. Expected cost of lanes_r2.txt: about 17.5 h = 18.5 USD (range 13.4-25.3 h); Tier 2 adds 3.7 h = 3.9 USD.
