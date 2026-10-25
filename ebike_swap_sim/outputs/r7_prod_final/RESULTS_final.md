# R7 Manhattan siting, production run: final results

Run finished on AWS on 2026-10-24 at 04:16 UTC. This analysis was done on the laptop on 2026-10-24 from the downloaded
records only; no solver was run. Generated files:

* `r7_siting/RESULTS.md`: `r7_siting.py --stage analyse`. It appended records 1008 (`plan`), 1009 (`m1_dual_statement`)
  and 1010-1011 (`role_table`) to `records.jsonl`, and wrote no `cost.jsonl` row.
* `r7_siting/SEARCH.md`: `r7_search.py --stage report`. It wrote no record and no cost row.
* Maps:
  * `figs/fig_final_map.{png,pdf}`: written by the new script `figs/final_map.py`.
  * `figs/fig_dot_map.{png,pdf}`: written by the standard `outputs/r7_siting/figs/siting_map.py`.
  * `fig_final_map.{png,pdf}` is copied unchanged to `paper_itsc/figs/fig_layouts.{png,pdf}` for the paper.

**Scope of every number.**
* N = 59 candidates in Manhattan south of 110th St: 45 DOT-based and 14 lattice-only cells.
* S = 12 stratified in-sample scenarios, plus 12 held-out scenarios. The strata are 3 weekday demand levels and 3
  weekend demand levels, 2 seeds each, with weights 0.119 (weekday) and 0.048 (weekend).
* 8 bikes, relaxed end targets.
* 14-block approach radius with the start-state exemption.
* tol-rel 0.01. The open-sites gap is reported with tol 0.
* Values are USD per day: allocated set-up plus expected operating cost (`V`).
* Budget unit m = 52,150 USD of investment. One SC:B3:C2 site (swap + charge, 3 spare batteries, 2 chargers) uses
  exactly one unit.

**The two follower conventions are kept apart in every statement.**
* **(i) All-candidates follower** (model of record). Riders may reposition towards any candidate node, also closed
  ones. Every LB in this file (LP, cuts, enumeration floor, master) is a bound for this follower.
* **(ii) Open-sites follower.** Riders reposition only to open sites and depots. Every production pricing was done
  under this follower (`price_open`).
* How the two relate:
  * The open-sites library is a sub-library of the all-candidates library. So an open-sites value V_open is a valid
    UB on the all-candidates value of the same layout. M6 checked this explicitly for D23 (records line 643: 12 of 12
    cells ok, V_checked = V_open = 1085.87).
  * An all-candidates LB is also a valid LB for the open-sites follower.
  * The reverse never holds: open-sites ILP bounds (`lower_open`) are never used as all-candidates bounds.

Record references below are `kind @ line` in `r7_siting/records.jsonl`, or `cache@line` in `r7_siting/cache/index.jsonl`.

---

## 0. Headline

| m | best layout found | UB (USD/day) | all-cand. LB | gap | certified? | served |
|---|---|---|---|---|---|---|
| 1 | D23:SC:B3:C2 | 1,085.87 | 1,036.03 | 4.59 % | all-candidates: no. Open-sites: **yes**, V*_open in [1,084.31, 1,085.87], gap 0.14 % | 0.775 |
| 2 | D07:SC:B3:C2 + D45:SC:B3:C2 | **716.85** (record value 718.91) | 670.23 | 6.50 % (record 6.77 %) | no (heuristic pair search) | 0.983 |
| 3 | D07:SC:B4:C2 + D45:SC:B4:C2 | 709.98 | 670.23 | 5.60 % | no; the third site was "not found to pay", which is not proved | 0.985 |

* A second site cuts the daily cost by 34 % (1,085.87 to 716.85), almost all of it through unserved orders (section 7).
* The third budget unit is not used for a third site. The best layout found keeps the two sites and enlarges them to
  B4. The best three-site layout priced, D07 + D23 + D45, costs 718.80, which is 8.82 +- 2.46 more (stratified 95 %
  CI, 6 df).
* All three rule baselines are 92-141 USD/day worse than the best at m = 2 under the open-sites follower (point
  differences +91.70 CSAV, +134.42 DOT pilot pair, +141.48 CSCD; section 4): CSCD (demand coverage), CSAV (spatial
  spread) and the DOT pilot pair. The lower end of each all-candidates regret interval is
  negative, so under follower (i) that regret is not proven.
* A separate charging hub never pays. The hub was never used: 0 swaps, 0 kWh bought, 0 battery transfers. A
  swap-only site costs about 41 USD/day more than a co-located SC site.

---

## 1. Best layout per budget

Candidate details are from `r7_siting/candidates.csv` and `data/raw/dot_candidate_sites.csv`. Hub-capable means the C
(charge-only hub) role is allowed there. Twelve sites are hub-capable: 4 operator depots (D13 is a JOCO hub, the
others are stores) and 8 Citi Bike docks (D31 and D50 are DOT-announced docks marked UNCERTAIN as charging docks).

| id | site | type | hub-capable | single site feasible |
|---|---|---|---|---|
| D23 | DOT PEC Site 34 (MN03), 2nd Ave at E 13th St, SE corner (DOT reference address 207 2nd Ave), East Village | DOT shortlist (PEC preliminary) | no | yes |
| D07 | Lattice cell M03 (grid cell (2, 1), 624 restaurants; about 40.7301 N, 74.0008 W, Greenwich Village). No DOT site. | lattice-only | no | yes |
| D45 | Citi Bike charging dock 3 Ave & E 62 St (station 6830.04, 51 docks), Upper East Side | citibike_charging | yes | **no** (terminal-infeasible alone in 3 of 4 scenario groups) |
| D24 | Citi Bike charging dock E 14 St & 1 Ave (5779.10, 34 docks) | citibike_charging | yes | yes |

### m = 1 (budget 52,150 USD; investment 52,150)

* **Best: D23:SC:B3:C2. One co-located swap + charge site, 3 spare batteries, 2 chargers.**
* **UB = 1,085.87.** Source: `price_open @496` (open-sites follower; 11 of 12 cells OPTIMAL, s9 TIME_LIMIT at 600 s),
  `budget_result @954`. Under follower (i) this is a UB (M6 `ub_check_summary @643`).
* **All-candidates follower:** V*_1 in **[1,036.03, 1,085.87], gap 4.59 %, not certified** (`m1_dual_statement @1009`).
  * The LB comes from the M3 probe, which lifted D29's bound from its LP 1,034.09 to 1,041.23 (probe a, `@655`) and
    then 1,041.41 (probe b, `@674`). Either way the floor is now D28's LP, 1,036.03 (`lp_layout @367`;
    `budget_result @660`, carried forward to `@954`).
  * The official M4 pair was [1,034.09, 1,085.87], gap 4.77 % (`budget_result @639`).
  * 16 locations are not excluded under (i), because their best all-candidates lower bound is below UB: D28, D34,
    D29, D33, D37, D23, D24, D30, D38, D25, D39, D22, D31, D19, D18, D16.
  * Under this follower D23 is **not** proven best. Any of these 16 could still be optimal.
* **Open-sites follower:** see section 2. **Certified**: D23 is the optimum.
* **Near-ties (open-sites values, all 12 cells priced at 600 s; `price_open @486-516`):**

  | rank | layout | V_open | vs D23 |
  |---|---|---|---|
  | 1 | D23 | 1,085.87 | |
  | 2 | D24 | 1,087.74 | +0.17 % |
  | 3 | D28 | 1,091.06 | |
  | 4 | D37 | 1,092.44 | |
  | 5 | D29 | 1,095.90 | |
  | 6 | D38 | 1,097.95 | |
  | 7 | D34 | 1,099.67 | |
  | 8 | D30 | 1,102.40 | |
  | 9 | D33 | 1,103.92 | |
  | 10 | D25 | 1,105.78 | |
  | 11 | D39 | 1,109.86 | +2.2 % |

  * 11 locations lie within 3 % of D23.
  * Paired difference D24 - D23 = +1.87 (p-weighted), plain CI +- 8.75 (unweighted SD, 11 df), stratified +- 8.86
    (6 df). On these 12 scenarios
    the top two are statistically indistinguishable, even though D24 is excluded under the open-sites certificate.

### m = 2 (budget 104,300 USD; investment 104,300)

* **Best found: D07:SC:B3:C2 + D45:SC:B3:C2.**
  * D07 is a West Village lattice cell.
  * D45 is the Citi Bike charging dock at 3 Ave & E 62 St. It is infeasible as a single site, but works as the
    partner of D07.
* **UB = 716.85** (open-sites follower, 8 of 12 cells OPTIMAL).
  * This is the in-sample re-solve of the oos stage: cells s10 and s11 were re-solved from scratch (default MIP
    start, no warm start) at 600 s and reached OPTIMAL (`cache@409-410`, the same instances as `cache@279-280`; the
    full set is `cache@269-278, 409-410`).
  * The same value appears as `oos_result @986` V_in and `noradius_result @1004` V_radius.
  * The `budget_result` records still carry the pairs-stage value **718.91** (`price_open @813`, `budget_result @955`,
    6 of 12 cells OPTIMAL), because the re-solve wrote no `price_open` record. Both are valid UBs, and 716.85 is the
    better one.
* **LB = 670.23** (all-candidates master bound, `budget_result @955`). **Gap 6.50 %** with UB 716.85, 6.77 % with
  718.91. **Not certified under either follower.**
* **Search effort** (`pair_summary @815`): 16 pairs screened, 5 excluded by their pair bound. 11 pairs are not
  excluded; their bounds are 675.9-688.1, all below UB. Only 3 pairs were priced. Against the record UB 718.91 one of
  the 5 exclusions (D07 + D23, bound 718.42) held only within tol-rel 0.01; against 716.85 all 5 hold strictly.
* **Near-ties.** Every priced pair is within 0.7 % of the best:

  | layout | V_open | record | difference to best | stratified CI |
  |---|---|---|---|---|
  | D07 + D45 | 716.85 | | | |
  | D23 + D45 (all-DOT) | 719.60 | `price_open @811` | +2.75 | +- 10.58 |
  | D24 + D45 | 721.78 | `@809` | +4.93 | +- 11.29 |

  * Under the open-sites follower the three cannot be ranked. Their `lower_open` values (712.40 for the 716.85 version
    of D07 + D45, recomputed from the cache cells; 711.70 in `@813` for the 718.91 version / 713.09 / 714.27) are each
    below the others' UBs.
  * D45 is in every pair priced by the pair search. (The rule, role and restricted pairs do not all contain D45.) The
    western partner (D07, D23 or D24) is interchangeable within noise.

### m = 3 (budget 156,450 USD; investment 105,200, so about 51,250 is unused)

* **Best found: D07:SC:B4:C2 + D45:SC:B4:C2.** These are the m = 2 sites with 4 spare batteries each.
* **UB = 709.98** (`price_open @831`, 12 of 12 cells OPTIMAL, `lower_open` 709.96, `m3_summary @837`).
* **LB = 670.23** (`budget_result @956`). **Gap 5.60 %, not certified.**
* **Third site.**
  * D07 + D23 + D45 (all B3:C2) = 718.80 (`m3_price @834`): worse by 8.82 +- 2.46.
  * D07 + D24 + D45 ran out of wall time (`m3_price @836`: SKIPPED_BUDGET; the cache holds 8 of 12 cells, s0-s7 at
    `cache@305-312`, s5 at TIME_LIMIT).
  * The record's claim is "no layout found" with `third_site_pays = false`. This is not a proof.
* Going from B3 to B4 at the same two sites is worth 6.87 USD/day (stratified CI +- 3.15).

---

## 2. Open-sites certificate (m = 1 only)

From `m1_dual_statement @1009`, with tol 0:

* **V*_open in [1,084.31, 1,085.87], gap 0.14 %. The certificate is COMPLETE.**
  * Every one of the 236 m = 1 layouts with an open-sites lower bound below UB_open was priced. 16 B3:C2 layouts were
    priced; the other 220 are infeasible alone or envelope / LP pruned.
  * The LB argmin is D23 itself. Its `lower_open` is 1,084.31, below its value only because scenario 9 stopped at
    TIME_LIMIT with a 3.42 % cell gap on the total incl. set-up (3.46 % on the opex basis; `epsilon_1` = 0.143 %).
  * Every other layout has an open-sites lower bound at or above 1,085.87. The closest is D24, at 1,087.74.
* So **D23:SC:B3:C2 is the certified optimal single site under the open-sites follower**, within 0.14 % on its own
  value.
* This certificate does **not** carry over to the all-candidates follower (section 1). The 16 open-sites ILPs would
  need all-candidates ILPs proved to within about 1 % at 9-16 locations, and the probe shows a lift of only 1.6-3.0 %
  per cell after 1,200 s (`probe_summary @656 / @675`).
* m = 2 and m = 3 have **no open-sites certificate**. Only 3 pairs and 2 triples were priced, and the pair bounds
  are all-candidates bounds.

---

## 3. Role table: best, best S-containing, best hub-containing

Rows are open-sites values: one follower on both sides of every difference (`role_row @906`; the hub screen
`@861-901` covered 11 of the 12 hub-capable sites, D11, D13, D16, D20, D24, D31, D33, D34, D42, D47 and D50, on
scenarios 4, 10 and 2; D45 was not screened as a hub). The differences in the table are against 716.85; `role_row
@906` reports +39.43 / +726.86 against 718.91.

| m | best | V_open | best with an S (swap-only) site | V_open | +S | best with a C hub | V_open | +hub |
|---|---|---|---|---|---|---|---|---|
| 1 | D23:SC:B3:C2 | 1,085.87 | not admissible | - | - | not admissible | - | - |
| 2 | D07:SC:B3:C2 + D45:SC:B3:C2 | 716.85 | D24:S:B3:C0 + D45:SC:B3:C2 | 758.34 | **+41.49** (CI +- 7.66 strat.) | D07:S:B3:C0 + D50:C:B0:C4 | 1,445.77 | **+728.92** (CI +- 65.93 strat.) |
| 3 | D07:SC:B4:C2 + D45:SC:B4:C2 | 709.98 | not searched at m = 3 (m = 2 row is feasible: 758.34) | - | - | not searched at m = 3 (m = 2 row: 1,445.77) | - | - |

Notes on the table:

* **m = 1.** S needs a charge-capable partner, and S + C does not fit in one unit (51,350 + 51,600 USD). So the role
  question is only meaningful from m = 2.
* **Role stage budgets.** It ran with `--role-budgets 2` only. In `RESULTS.md` the T4b rows for m = 3 repeat the m = 2
  role layouts.
* **T4 display issue.** `RESULTS.md` T4 (all-candidates tier) shows D30 at 1,347.61 as "best" for every m. Only three
  single-site layouts were priced on that tier (`price @312 / @314 / @315`, all from 300 s TIME_LIMIT cells): D18
  1,558.01, D30 1,347.61 and D38 1,666.51, and D30 is the cheapest of them. These are not the role layouts, so ignore
  T4 and use T4b or this table.

**What it says about separate charging stations.**

* The best hub layouts (D50 = W 92 St & Broadway, and D34 = W 42 St & 6 Ave, `role_price @903 / @905`) cost the same,
  1,445.77.
* The hub is simply idle: 0 swaps at the hub, 0 kWh bought, 0 battery transfers (`cache@325, @330`).
* The S site serves only its 3 initial batteries. The served share drops to 0.580, against 0.983 for the best layout.
* Within a 4-hour horizon at 8 bikes, a charge-only hub cannot return charged batteries to riders. Separating
  charging from swapping is therefore never worth it here: co-located SC sites dominate.
* A swap-only site next to an SC site is a much smaller loss (+41 USD/day, served 0.969). It still loses to a second
  SC site.

---

## 4. Comparisons: rules, DOT pilot, DOT-only

Records: `baseline @922-931`, `price_open @923-929`; regret intervals from `RESULTS.md` T2, recomputed against UB*_2 =
716.85.

**Regret intervals.**
* All-candidates follower (i): [LB_rule - UB*_m, UB_rule - LB*_m]. The lower end uses lower bounds only.
* Open-sites follower (ii): the lower end is `lower_open`(rule) - UB*_open,m. That end is valid because V*_open <= the
  best UB found. The upper end is V_open(rule) - LB*_m.

| m | rule | layout | V_open | LB_rule (i) | lower_open | regret (i) | regret (ii) | V - V_best, strat. 95 % CI | served |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CSCD | D18 (Cooper Sq pilot) | 1,118.68 | 1,085.33 | 1,118.68 | [-0.54, 82.65] | **[32.81, 34.37]** (certified m = 1 open-sites optimum) | +32.81 +- 29.64 | 0.753 |
| 2 | CSAV | D30 (lattice M08) + D58 (PEC Site 16, W 106 St) | 808.56 | 671.14 | 805.94 | [-45.71, 138.33] | [89.09, 138.33] | +91.70 +- 37.08 | 0.946 |
| 2 | CSCD | D18 + D19 (PEC Site 38, 1st Ave & E 5th St) | 858.33 | 671.14 | 853.04 | [-45.71, 188.10] | [136.19, 188.10] | +141.48 +- 38.12 | 0.914 |
| 2 | DOT pilot proxy = all-pilot | D12 (Essex Market) + D18 (Cooper Sq) | 851.27 | 671.14 | 847.71 | [-45.71, 181.04] | [130.86, 181.04] | +134.42 +- 37.70 | 0.916 |
| 3 | CSCD | D18 + D19 + D23 | 830.96 | 684.33 | 830.96 | [-25.65, 160.73] | [120.98, 160.73] | +120.98 +- 31.65 | 0.936 |

* **Pilot rows.** Only two DOT 2024 pilot hubs lie in the study region; Plaza de las Americas is north of 110th St.
  So the pilot proxy (`@928`) and the all-pilot layout (`@931`) are the same layout. D12 is infeasible alone.
* **Under the open-sites follower** every rule is worse than the best layout found, with a regret lower bound of 33 to
  136 USD/day. The paired CIs exclude 0 at m = 2 and 3.
* **Under the all-candidates follower** no positive regret is proven. LB_2 = 670.23 is too weak: the rule's own
  all-candidates value could, in principle, be as low as its LP bound.

**DOT-only vs full** (`restricted_result @947 / @949 / @950`; lattice-only candidates fixed closed; 45 DOT
locations):

| m | best DOT-only found | V_open | best full | V_open | best-found difference | certified price of restriction [LB_dot - UB_full, UB_dot - LB_full] |
|---|---|---|---|---|---|---|
| 1 | D23:SC:B3:C2 | 1,085.87 | the same | 1,085.87 | 0 | [-49.84, 49.84] |
| 2 | D23 + D45 | 719.60 | D07 + D45 | 716.85 | +2.75 (CI +- 10.58) | [-46.62, 49.37] |
| 3 | D23 + D45 (B3) | 719.60 | D07 + D45 (B4) | 709.98 | +9.62 | [-39.75, 49.37] |

* At m = 1, under the open-sites follower, the certified optimum is a DOT site (D23), so restricting to DOT sites
  costs nothing. Under the all-candidates follower this holds only for the best found: the 16 unexcluded locations
  include the lattice cells D30, D38 and D22, so it is not proved that the m = 1 optimum is a DOT site.
* The negative lower ends of the certified ranges are formula artefacts: the DOT set is a subset of the candidates, so
  the price of restriction is >= 0.
* At m = 2 the all-DOT pair D23 + D45 is a statistical tie with the best pair.
* At m = 3 the gap is mostly a size effect: the restricted stage did not price D23 + D45 at B4:C2.
* The proposal the restricted master priced, D14:S:B2:C0 + D29:SC:B2:C1, scored 1,029.67 (`@948`), so it was not
  competitive.
* **Bottom line:** a planner limited to DOT-listed sites loses essentially nothing at these budgets. The certified
  range is wide only because the LBs are weak.

---

## 5. Held-out (out-of-sample) values

**The oos stage did not finish.**
* All four `oos_result` records (`@985-988`) are SKIPPED_BUDGET with `V_out = null`. The 1 h wall ran out after 25 of
  48 held-out cells.
* Every held-out cell present is in the **weekday strata 1-3** (scenarios 0-5). D23 also has s6, at TIME_LIMIT.
* Weekend behaviour out of sample is **not measured**.

The table compares weekday-conditional means, Σ_h W_h mean_h / Σ_h W_h over strata 1-3:
* For each layout, the same in-sample scenarios (0-5) are compared with held-out seeds 100-105.
* The difference is a two-sample stratified estimate with a 95 % t interval, df 6. In and out use different demand
  draws, so the difference is not paired.
* Values include set-up. The cells are in `cache@411-435`.

| layout | V_in (weekday) | V_out (weekday) | V_out - V_in | 95 % CI | held-out cell status | served in / out |
|---|---|---|---|---|---|---|
| best@m1 D23 | 1,112.51 | 1,073.51 | -39.01 (-3.5 %) | +- 95.43 | 6 of 6 OPTIMAL | 0.762 / 0.778 |
| best@m2 D07 + D45 | 730.14 | 683.10 | -47.05 (-6.4 %) | +- 51.38 | 5 OPTIMAL, s5 TIME_LIMIT | 0.980 / 0.981 |
| CSCD@m2 D18 + D19 | 888.32 | 813.47 | -74.86 (-8.4 %) | +- 77.94 | 3 OPTIMAL, 3 TIME_LIMIT | 0.903 / 0.931 |
| DOT all-pilot D12 + D18 | 879.58 | 826.22 | -53.36 (-6.1 %) | +- 81.36 | 3 OPTIMAL, 3 TIME_LIMIT | 0.903 / 0.926 |

Paired differences on the same scenarios, weekday strata 1-3 (stratified CI, df 3):

| difference | in sample | held out |
|---|---|---|
| CSCD@m2 - best@m2 | +158.18 +- 69.26 | +130.37 +- 84.01 |
| DOT all-pilot - best@m2 | +149.44 +- 66.91 | +143.12 +- 84.05 |
| best@m1 - best@m2 | +382.37 +- 109.95 | +390.41 +- 97.72 |

* There is no evidence of in-sample optimism: every V_out - V_in CI contains 0, and the point estimates are negative.
  This is a weak test, not evidence that there is none.
  * All four layouts, the rules included, move by -39 to -75. This looks like a common demand-draw difference between
    seeds 100-105 and 0-5, not something specific to the selected layouts.
  * df 6 follows the code's cells-minus-groups convention. Welch-Satterthwaite df are only 1.9-4.7, which widens the
    half-widths to about +- 55 to +- 145; every CI still contains 0.
* The advantage of the best m = 2 pair over the rule and pilot layouts persists out of sample on weekdays.
* All held-out pricings were done under the open-sites follower. TIME_LIMIT cells are incumbent values, i.e. upper
  bounds.
* `RESULTS.md` T6 and `SEARCH.md` show "-" for V_out. The numbers above are recomputed from the cache rows by the
  laptop script described in section 9.

---

## 6. No-radius re-pricing

Open-sites follower with the radius unset, warm-started from the radius schedules (`noradius_result @993-1005`,
`noradius_summary @1006`). Effect = (V_radius - V_noradius) / V_noradius.

| layout | V radius 14 | V no radius | effect | both sides 12 OPTIMAL |
|---|---|---|---|---|
| D23 | 1,085.87 | 1,078.16 | 0.71 % | no |
| D24 | 1,087.74 | 1,078.32 | 0.87 % | no |
| D28 | 1,091.06 | 1,062.49 | 2.69 % | yes |
| D37 | 1,092.44 | 1,078.07 | 1.33 % | yes |
| D29 | 1,095.90 | 1,062.87 | 3.11 % | yes |
| D38 | 1,097.95 | 1,071.30 | 2.49 % | yes |
| D34 | 1,099.67 | 1,062.47 | 3.50 % | no |
| D30 | 1,102.40 | 1,069.16 | 3.11 % | no |
| D33 | 1,103.92 | 1,069.30 | 3.24 % | no |
| D25 | 1,105.78 | 1,092.78 | 1.19 % | no |
| D39 | 1,109.86 | 1,086.43 * | 2.16 % * | no |
| best@m2 D07 + D45 B3 | 716.85 | 710.56 * | 0.89 % * | no (8 / 8 OPTIMAL) |
| best@m3 D07 + D45 B4 | 709.98 | 705.19 * | 0.68 % * | no (12 / 10 OPTIMAL) |

\* The record status is SKIPPED_BUDGET because of the wall. All 12 no-radius cells are in the cache (the no-radius
cells of all 13 layouts are `cache@436-591`),
some of them stopped at a cut time limit. These values are feasible no-radius values, so the effects are indicative.

* **Measured m = 1 effect: 0.7-3.5 %.** The 15-candidate probe had measured +2.4-2.9 % at one site.
* **The m = 1 ranking depends on the radius** (`consequence: "m = 1 ranking library-conditional"`).
  * Without the radius, D34 (1,062.47), D28 (1,062.49, exact) and D29 (1,062.87, exact) tie for best, within 0.04 %.
  * D23 falls to 8th.
  * The radius penalises the Midtown sites (D28, D29, D34, D30, D33: about 3 %) more than the East Village and
    Gramercy sites (D23, D24, D37: 0.7-1.3 %).
* At m = 2 and 3 the radius effect is under 1 %. The two-site recommendation does not depend on the radius in any
  material way.

---

## 7. Served shares and cost drivers

Weighted over the 12 in-sample scenarios, open-sites values. Expected 40 orders per day. Cells are from
`cache/index.jsonl`.

* **Unserved penalty** is 60 USD per unserved order.
* **Response** and **late** are the order-level response-time and lateness costs of the served orders.
* **Travel** is rider repositioning distance.
* **Electricity** is energy bought.

| layout | V | set-up | unserved penalty | response | late | travel | elec. | unserved orders | served | swaps |
|---|---|---|---|---|---|---|---|---|---|---|
| m1 D23 | 1,085.87 | 13.19 | **568.57 (52 %)** | 471.61 | 17.08 | 14.54 | 0.87 | 9.48 | 0.775 | 6.6 |
| m2 D07 + D45 | 716.85 | 26.38 | 44.29 (6 %) | **602.32 (84 %)** | 20.62 | 22.01 | 1.23 | 0.74 | 0.983 | 11.8 |
| m3 D07 + D45 (B4) | 709.98 | 27.04 | 37.14 | 601.11 | 20.74 | 22.92 | 1.03 | 0.62 | 0.985 | 13.0 |
| CSCD m2 D18 + D19 | 858.33 | 26.38 | 221.43 | 560.96 | 23.84 | 24.19 | 1.53 | 3.69 | 0.914 | 12.7 |
| CSAV m2 D30 + D58 | 808.56 | 26.38 | 144.29 | 587.86 | 26.67 | 22.23 | 1.13 | 2.40 | 0.946 | 10.6 |
| pilot D12 + D18 | 851.27 | 26.38 | 218.57 | 559.86 | 19.91 | 24.95 | 1.61 | 3.64 | 0.916 | 14.0 |
| role S: D24:S + D45:SC | 758.34 | 26.22 | 81.43 | 601.86 | 27.38 | 20.76 | 0.70 | 1.36 | 0.969 | 9.1 |
| role hub: D07:S + D50:C | 1,445.77 | 42.54 | 1,031.43 | 347.11 | 14.64 | 10.05 | 0.00 | 17.19 | 0.580 | 3.0 |

**Unserved orders drive the cost.**
* With one site, 9.5 of 40 daily orders go unserved, and the penalty is half of V.
* The second site recovers about 8.7 orders: -524 USD of penalty, partly offset by +131 USD of response cost on the
  extra served orders.
* The rule and pilot layouts lose to the best pair almost entirely through 2.4-3.7 unserved orders per day.
  * The CSCD and pilot pairs put both sites in the East Village / Lower East Side.
  * CSAV puts one site far north, at D58 (W 106th St).
  * The best pair puts one site on each side of the island, with D45 on the Upper East Side.
  * This is an observation; no regional demand split was computed.
* Set-up is small: 13.19 USD/day per SC:B3:C2 site.
* Travel and electricity are under 4 % of V.
* The served-share column in `RESULTS.md` T1 (0.981 at m = 2) belongs to the 718.91 version of the same layout.

---

## 8. Compute cost

Source: `r7_siting/cost.jsonl`, 64 lines = 32 finished invocations plus their 32 start rows; 0 failed, 0 unfinished.
Summarised by `experiments/r7_cost.py`. Instance-hours are the union of lane intervals on the one r7i.4xlarge, at
1.0584 USD/h.

| batch | stages | process hours (sum) | instance hours | USD | re-plan estimate |
|---|---|---|---|---|---|
| 1 | calib, 4 x feas, oos-feas | 10.74 | 4.73 | 5.00 | 3.8 h |
| 2 | m1 (first pass) | 13.23 | 13.23 | 14.00 | 13.9 h |
| 3 | 12 x rootlp (3 chains) | 26.82 | 9.18 | 9.72 | 13.5 h |
| 2b | gate, M1 open-sites list, M4, M6, M3 probes a / b | 6.69 | 6.69 | 7.08 | 4.86 h (3.25-8.5) |
| 4 | pairs, m3, roles | 7.73 | 7.73 | 8.19 | 7.4 h |
| 5 | comparison, restricted, oos | 4.29 | 4.29 | 4.54 | 3.5 h |
| 6 | noradius | 2.21 | 2.21 | 2.34 | 1.7 h |
| **production total** | | 71.71 | **48.06** | **50.87** | |

* **Lane span.** The lanes ran from the first gate at 2026-10-22 03:55:09 to the last lane exit at 2026-10-24
  04:16:38: 48.36 h = 51.18 USD. Idle gaps between lanes add 0.30 h.
* **Not in `cost.jsonl`:**
  * instance time before the first lane and after the last one (upload, download, shut-down);
  * EBS storage.
* **The re-plan batches 2b, 4, 5 and 6 took 20.92 h = 22.14 USD**, against the plan's 17.5 h = 18.5 USD. Batch 2b
  took 6.69 h against 4.86 h, because M1 priced 16 locations.
* **Study total:** about 13 USD of probes before production (figure from the run plan, not in `cost.jsonl`), plus
  50.87 = **about 64 USD**, all in October 2026. That
  is about 14 USD over the 50 USD/month line, plus EBS and the pre/post-lane instance time. The author allowed the
  overrun in plan section 8.
* Tier 2 (`lanes_r2_tier2.txt`, about 3.9 USD) was **not run**, although the M3 probe verdict said "start Tier 2"
  (`probe_summary @675`: mean lift 2.28 % >= 1 %).

---

## 9. Caveats

1. **The all-candidates follower is the model of record, and it is not certified at any budget.**
   * The m = 1 gap is 4.59 %, with 16 locations not excluded.
   * Tier 2 could have raised the floor by at most about 0.7 points: D33's LP of 1,043.54 caps it.
2. **The m = 2 and m = 3 incumbents come from a heuristic search.**
   * 16 pairs were screened and only 3 priced.
   * 11 screened pairs remain unexcluded, with pair bounds of 675.9-688.1, below UB.
   * Unscreened pairs are covered only by the weak master LB of 670.23.
   * "A third site does not pay" is not proved.
3. **The m = 2 UB of 716.85 is better than the value in the `budget_result` records (718.91).**
   * It comes from the oos stage's in-sample re-solve of two TIME_LIMIT cells, which was cached but wrote no
     `price_open` record.
   * `RESULTS.md` and `SEARCH.md` use 718.91 in T1, T2, T4b and the bound tables, and 716.85 in T6 and the radius
     table.
4. **Held-out results are partial and weekday-only** (section 5). The official `oos_result` records have no V_out.
5. **Open-sites cells with TIME_LIMIT give incumbent values.** Counts of these cells:
   * the m = 2 incumbent: 4 of 12;
   * CSCD m = 2: 5 of 12;
   * the pilot pair: 2 of 12;
   * CSAV m = 2: 2 of 12;
   * D23: 1 of 12 (s9, cell gap 3.42 % on the total, 3.46 % on opex).

   These are valid UBs. The rule-vs-best paired differences can therefore be off by a few USD per cell in either
   direction.
6. **The m = 1 ranking depends on the library.** Without the 14-block radius, D23 drops from 1st to 8th, and the top
   three without the radius are Midtown sites within 0.04 %. The m = 1 near-tie set (11 sites within 3 %) is the
   robust statement, not the single winner.
7. **Some site attributes are not checked.**
   * D07, in the m = 2 / m = 3 best layouts, is a lattice cell (restaurant-density centroid), not a real site. The
     all-DOT pair D23 + D45 is within 2.75 USD/day (CI +- 10.58) and is the implementable alternative.
   * D45 and the other Citi Bike charging docks are only proxies for a grid connection. Their actual cabinet space and
     consent status are not verified.
8. **Separate hubs were tested only at m = 2.** The screen covered 11 of the 12 hub-capable sites (not D45), priced 2
   of them (D50, D34), and used
   4-hour horizons. The "hub never pays" result is horizon-dependent: no battery transfers happen within 4 hours.
9. **Batch 3 root import.** `RESULTS.md` lists "`--root-import` refused: FileNotFoundError" because the step-2b pool
   file was not on the server. Batch 3 recomputed all 12 root LPs itself, so no bound depends on the import.
10. **Partial no-radius values.** The no-radius values for D39 and the m = 2 / m = 3 layouts are SKIPPED_BUDGET in
    the records (section 6). Their effects are indicative only.
11. **Scope.** The results hold for 8 bikes, relaxed targets, S = 12 stratified scenarios and 40 expected orders per
    day. Written-target, compliance and fleet-size variants were not run.

---

## 10. Verification

Three independent laptop checks (2026-10-24) recomputed the claims of this file from the raw files: `records.jsonl`,
`cache/index.jsonl`, `cuts.jsonl`, `cost.jsonl`, `root_lp/*.json`, the `feas_*` records, `candidates.csv`, the raw DOT
CSV and the lane logs. No solver was run. The weights were p_s (5/42 weekday, 2/42 weekend), and the CIs used the
`bilevel.stratified_ci` logic with scenario pairs as strata.

**Checked and confirmed (to 2 decimals unless noted):**
* **m = 1 bounds.**
  * UB 1,085.87 (`@496`; M6 `@643` 12 of 12 ok).
  * Rebuilt 236-layout menu: 144 infeasible and 92 feasible, each feasible one with an all-candidates bound.
  * All-candidates LB 1,036.03 (D28 LP `@367`), gap 4.59 %, and the same 16 unexcluded locations.
  * Open-sites certificate: 1,084.31, gap 0.143 %. D24 at 1,087.74 is next. The 76 unpriced feasible layouts are all
    >= 1,090.74.
  * The 11 near-ties and the D24 - D23 CIs.
* **m = 2 and m = 3.**
  * UB 716.85 and 718.91; LB 670.23 = root LP 644.76 + set-up 25.47.
  * Pair screen 16 / 5 / 11 / 3.
  * Near-tie values and CIs; m = 3 UB 709.98, triple +8.82, B3 -> B4 6.87; investment 105,200.
* **Lower-bound validity.**
  * No open-sites value is used as an all-candidates LB. None of the 1,065 cuts comes from an open-sites solve. The 61
    integer cuts match all-candidates cache bounds (48) or LP bounds (13).
  * The feasibility screen used the all-candidates evaluator.
* **Comparisons.** All rule layouts, V_open, LB_rule, lower_open, served shares, the 5 regret intervals under both
  followers, the paired CIs, the DOT-only best layouts and the certified ranges. Also the role table values and CIs,
  and hub idleness (0 kWh, 0 transfers, swaps only at D07:S).
* **Sites.** Candidate counts (45 DOT-based + 14 lattice-only), the 12 hub-capable sites, the site names and types,
  and 23 single-site-feasible locations (36 infeasible).
* **Held out, no radius, cost drivers and cost.**
  * Held-out V_in / V_out / CIs and paired differences (half-widths within 0.02, from t-quantile rounding).
  * All no-radius values, effects and ranking.
  * All cost-driver rows.
  * Per-batch instance hours and USD, total 48.06 h = 50.87 USD, lane span 48.36 h, re-plan 20.92 h.

**Corrected after verification:**
* Hub screen: 11, not 12, hub-capable sites were screened. D45 was not screened as a hub.
* T4: three layouts were priced on the all-candidates tier, not only D30. D30 is the cheapest of the three.
* D07 + D24 + D45: 8 cached cells, not 9.
* Pilot swaps: 14.05, not 14.1.
* `lower_open` of the 716.85 version of D07 + D45 is 712.40; 711.70 belongs to the 718.91 version.
* Cells s10 / s11 of the m = 2 re-solve were fresh solves, not warm-started.
* D23 s9 cell gap: 3.42 % on the total (3.46 % on opex).
* Clarifications:
  * "D45 in every priced pair" now refers to the pair search only.
  * The D07 + D23 exclusion holds only within tol against 718.91.
  * The rule regret range now reads 92-141.
  * The m = 1 "DOT optimum" statement now names its follower.
  * The held-out wording now reads "no evidence of optimism", with the Welch df caveat.
  * CSAV's 2 TIME_LIMIT cells are added to the caveats.
  * The unchecked West Village landmark for D07 was removed.
  * The probe cost (about 13 USD) is marked as not in `cost.jsonl`.

**Not checked:** the 13 USD probe cost and EBS cost (not in the records), and weekend held-out behaviour (not
measured).

**Reproduce:**
* Analyse and report: run from `ebike_swap_sim` with `--out-dir outputs/r7_prod_final/r7_siting --family
  manhattan_dot --scenarios 12 --approach-radius 14 --max-rss-gb 110 --tol-rel 0.01 --tol-abs 1 --restrict dot
  --held-out` plus 1-thread worker flags. Analyse: `python3 experiments/r7_siting.py --stage analyse`. Report:
  `python3 experiments/r7_search.py --stage report`.
* Map: `python3 outputs/r7_prod_final/figs/final_map.py`.
* The cell-level recomputations in sections 1, 4, 5, 6 and 7 (latest cache row per layout, scenario and convention;
  weights p_s) were done with throw-away laptop scripts. Each number cites its cache lines, so it can be checked by
  hand.
