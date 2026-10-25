# O2 -- certified Manhattan siting at the new prices: final report

Sources (read only, nothing was re-solved): first pass `outputs/r6_o2/manhattan/` (records.jsonl, 259 records, wall
19.3 h, finished 2026-10-19 11:18) with its post-hoc bound `outputs/r6_o2/manhattan_bound/` (BOUND.md, records.jsonl);
second pass `outputs/r6_o2/manhattan_pass2/` (records.jsonl, 969 records of which the first 259 are the copied first-pass
records, checked identical; cuts.jsonl, 998 cuts; cache/index.jsonl, 149 per-scenario rows; logs
`manhattan_pass2.log`, `manhattan_pass2_step2.log`; finished 2026-10-20 00:15) with its bound
`outputs/r6_o2/manhattan_pass2_bound/BOUND.md`; design and diagnosis `notes/o2_siting_bound_design.md`,
`notes/o2_manhattan_first_pass.md`, `notes/DECISIONS.md` (O2 conventions, O2 second pass); legacy-price study
`outputs/r5_x6_manhattan/RESULTS_final.md`. The cross-check of the round-5 layout under rule r2 and the selfish follower
uses `outputs/r6_fill/compliance/records.jsonl`. Every number below is recomputed by
`outputs/r6_o2/figs/siting_report.py` (tables in `figs/siting_tables.txt`, CSV next to it).

Set-up. Family `manhattan` (15 candidate sites south of 110th St, six rider depots, 8 bikes, 40 orders per scenario,
4-h dinner window), three demand scenarios (seeds 0-2, p = 1/3), new prices P 60 USD, w 18 USD/h, v 15 USD/h. Menu of
14 options per site: swap-only S with 1-4 spares, charge-only hub with 2 or 4 chargers, co-located SC with 1-4 spares
(B) and 1-2 chargers (C); budgets m = 1-4 units of 52,150 USD (one SC site with 3 spares and 2 chargers). V = allocated
set-up + mean scenario operating cost per 4-h window (USD), ILP follower (aggregated E2 ILP, all-candidates
repositioning library, Threads 3, 300 s per scenario, 600 s with a charge-only hub, escalations 900 s and 1,800 s).
LB = valid lower bound on the optimal value V*_m (safe Lagrangian LP cuts, integer L-shaped and lifted cuts, enumeration
floor at m = 1, nested over budgets); UB = V of the best layout found; bound gap = 100 (UB - LB)/UB; certified when the
gap is within max(0.25 % UB, 1 USD). Rule layouts: CSCD, CSTC, CSAV (demand-, trip- and availability-proportional
siting), the present-day proxy (restaurant-weighted, capacity-matched to the best layout) and the round-5 bi-level
layout. Followers: ILP, rule r2 and the selfish follower M4 (MSA equilibrium, cap 10 iterations). Exact Student-t 95 %
CIs over the n = 3 scenarios (t = 4.303); differences between layouts are paired by scenario. Layouts are written as
site numbers with sizes, e.g. "04 SC B2 C2 + 09 SC B4 C2" (record key `M04:SC:B2:C2|M09:SC:B4:C2`).

## 1. Problems and anomalies (read first)

1. **No certificate at two to four budget units.** Bound gaps at m = 2-4: relaxed 3.48 %, written 3.39 % (m = 2) and
   2.53 % (m = 3-4). The lower bound (relaxed 675.740, written 676.240) is only 0.91 and 1.41 USD above the trivial
   two-site bound 674.830 (mean superset LP 650.024 + cheapest two-site set-up 24.806). The cuts say almost nothing
   about two-site layouts: the brute-force check over the 17,340 admissible layouts at m = 2 leaves 7,060 (relaxed,
   40.7 %) and 3,140 (written, 18.1 %) open; m = 3-4 (about 1.27 M and 53.7 M layouts) was not checked.
2. **Written m = 1 is not certified, and the open layout is a rule layout.** Every one-site layout but one is resolved;
   the open one is site 09 (CSCD = CSTC rule layout), priced with MIP gaps 2.86, 2.91 and 1.59 % after six escalation
   calls (900 s and 1,800 s per scenario). Its value lies in [1,115.25, 1,143.03] and straddles the incumbent site 08
   (1,131.80), so the written one-unit optimum is site 08 or site 09; the 1.46 % bound gap is entirely this layout.
3. **The relaxed incumbent at m = 2-4 is stale.** The relaxed run never priced the two layouts at sites 04 + 09 that the
   written screen found later. Written rows restrict the relaxed problem (V_relaxed <= V_written for every layout; true
   for all 14 layouts priced under both targets up to one MIP-gap case, item 7), so their written values are upper
   bounds on relaxed V*: m = 2 <= 699.957 (reported 700.113), m = 3-4 <= 693.807 (reported 700.113). With these the
   relaxed bound gaps are 3.46 % (m = 2) and 2.60 % (m = 3-4), the reported relaxed best layout 08 + 09 is not the best
   known at m = 3-4 (by at least 6.31 USD), and the lower ends of the relaxed regret intervals in
   `manhattan_pass2/RESULTS.md` Table 2 are understated by 0.16 (m = 2) and 6.31 USD (m = 3-4).
4. **The relaxed step 2 never reached the integer phase.** Its LP phase took 29 rounds and 3.7 h (m = 3 alone 15 rounds,
   2.7 h), the screen proposed three far one-spare layouts (LP values 1,192 and 1,334), the three m = 4 rule layouts
   were priced, and the 4-h wall stopped it with no master proposal. The written step 2 spent 2.1 h in the LP phase
   (21 rounds), found the 04 + 09 layouts in its screen, and then proposed 72 two-site layouts in 45 min, all pruned
   by their LP value (none priced); LB rose from 675.908 to 676.240 in 20 rounds and stayed flat for 52. The LP-phase
   bounds (662.39-664.33) are below the trivial two-site bound and added nothing to LB.
5. **The m = 3-4 written best layout does not use the budget**: 04 SC B4 C2 + 09 SC B4 C2 costs 105,200 USD (450 USD
   per extra spare above B3), i.e. two sites at 67 % of the m = 3 budget; the m = 3 and m = 4 results are identical.
6. **Duplicate and stale rows in `manhattan_pass2/RESULTS.md` Table 4** (cross-follower): the copied first-pass rows
   appear next to the new ones, and site 08 written shows two ILP values (1,132.394 from the first pass, 1,131.800 after
   the second-pass escalation of scenario 0). This report uses the last, best incumbent per scenario (1,131.800).
7. One relaxed incumbent is above the written optimum of the same layout: 08 + 09 + 12 + 13 (CSTC m = 4) scenario 2,
   relaxed TIME_LIMIT 793.91 (MIP gap 0.56 %) against written OPTIMAL 791.40, so its price of recovery is -0.26 USD;
   a MIP-gap effect without influence on any bound.
8. One selfish equilibrium did not converge: 08 + 09 (CSCD m = 2) scenario 2 stopped at the 10-iteration cap (max share
   change 0.062); the same cell failed to converge at the legacy prices. 17 of the 18 distinct selfish equilibria
   converged.
9. Several rule-layout values are time-limited incumbents (status per scenario in Table 2). The round-5 layout under
   written targets has MIP gaps 6.44, 8.49 and 2.88 % (V 802.43, lower 755.79); CSAV m = 2 written and the present-day
   proxy m = 2 written are TTT. The regret lower ends are therefore also given against the layouts' own MIP bounds.
10. First pass: LB None at every budget (no master solve before the wall), five rule-layout cells SKIPPED_BUDGET
    (relaxed m = 4 CSCD, CSTC, CSAV; written m = 4 CSTC, CSAV) and one written ILP cut to 49.6 s by the wall
    (08 + 09 + 12 + 13 scenario 0, TIME_LIMIT, MIP gap 45.35 %). All were re-run in the second pass (all PRICED; the
    shortened cell OPTIMAL at 693.04). The diagnosis note says the first-pass enumeration stopped "at layout 47-52 of
    90"; the records give 50 (relaxed) and 45 (written).
11. Bound-LP elasticity: artificial columns active in some LPs (max 2.0 bikes in the second pass, 5.0 / 5.5 in the first);
    validity unaffected (safe cuts; audits Qt - Qs <= 6.1e-8). Fixed-layout LP gap (Q_IP - Q_LP)/Q_IP over the priced
    cells: median 0.84 % (relaxed, 33 cells) and 0.69 % (written, 39 cells), max 5.33 and 14.39 %, so single-layout LP
    cuts are weak; the strengthening (S1/S2) recommended by the gate is not implemented.
12. Scope. Certificates hold for these three scenarios and the all-candidates library only; values are not comparable
    one to one with the legacy X6 values (open-sites library, legacy prices). Only rule r2 and the selfish follower were
    evaluated on the layouts here: the Manhattan ILP-vs-best-rule gap (best of r2, M2, M3, M2+M3) cannot be computed.

## 2. Coverage

| item | first pass | second pass (new rows only) |
|---|---|---|
| wall time | relaxed 538.9 min, written 599.3 min (19.3 h) | step 1 (m = 1): relaxed 13.0 min, written 153.1 min; step 2 (m = 2-4): relaxed 238.5 min, written 236.9 min (10.7 h) |
| LP-solved layouts (unique) | relaxed 61, written 56 | relaxed 4, written 85 (cumulative unique: 65, 141) |
| LP-pruned before any LP (envelope) / by LP value | 0 / 0 | relaxed 88 / 0, written 87 / 72 |
| layouts priced by the ILP (cumulative unique, final status) | relaxed 11 PRICED + 3 SKIPPED_BUDGET; written 12 PRICED + 2 SKIPPED_BUDGET | relaxed 14 PRICED; written 17 PRICED + 2 bound-stopped (06 SC B3 C2 at m = 1; 04 SC B4 C2 + 09 SC B2 C2) |
| ILP solves, relaxed | 37: OPTIMAL 28, TIME_LIMIT 7 (MIP gaps 0.91-4.08 %, median 1.13), USER_OBJ_LIMIT 2 (bound-stopped); 300 s (one cut to 158.9 s, OPTIMAL) | 8: OPTIMAL 6, TIME_LIMIT 2 (0.47, 0.56 %); one escalation at 900 s (site 09 scenario 0, OPTIMAL in 730 s); one limit cut to 187.4 s (OPTIMAL) |
| ILP solves, written | 38: OPTIMAL 21, TIME_LIMIT 16 (0.72-45.35 %, median 3.09), NO_INCUMBENT 1 (bound-stopped); 300 s, two cut by the wall (158.6 s OPTIMAL; 49.6 s TIME_LIMIT at 45.35 %) | 24: OPTIMAL 15, TIME_LIMIT 7 (0.09-3.91 %, median 2.86), NO_INCUMBENT 2 (bound-stopped); 7 escalations (900 s x 4, 1,800 s x 3); one limit cut to 266.4 s (OPTIMAL) |
| ILP rows passing the independent check (`check_ok`) | 74 of 75 (the NO_INCUMBENT row has no schedule) | 30 of 32 (2 NO_INCUMBENT rows) |
| master solves | 0 | 216 (written integer phase, 72 rounds x 3 budgets) + 8 final bound solves (all OPTIMAL) |
| rule r2 / selfish evaluations | 15 / 15 per-scenario rows | 6 / 6; 18 distinct selfish equilibria in total, 17 converged |
| cut pool | 507 cuts | 998 cuts (lp 780, L-shaped 132, lifted 86) |

Both passes have every `budget_result` row (8 per pass). The second-pass bound recomputed from the stored pool without
any solve (`manhattan_pass2_bound`) equals the certifier's LB in all 8 rows. The V of every priced layout equals the
mean of its cached per-scenario totals (0 mismatches). Validation run (2026-10-18, `outputs/r6_o2/midtown_validate`):
on an 8-layout Midtown instance the certifier returned the exhaustive-search layout with a valid LB (acceptance ok).

## 3. Results

### 3.1 What is certified, per target and budget

Table 1. Best layout found (UB) and certified lower bound (LB). ILP status per scenario: O OPTIMAL, T TIME_LIMIT.

| target | m | best layout found | invest. USD | UB | LB | LB from | bound gap % | certified | ILP st. (MIP gaps %) | served share |
|---|---|---|---|---|---|---|---|---|---|---|
| relaxed | 1 | 09 SC B3 C2 | 52,150 | 1,052.995 | 1,052.995 | enumeration | 0.00 | **yes** | OOO | 0.783 |
| relaxed | 2 | 08 SC B3 C2 + 09 SC B3 C2 | 104,300 | 700.113 (<= 699.957, item 3) | 675.740 | master | 3.48 (3.46) | no | OOT (0.91) | 0.983 |
| relaxed | 3-4 | 08 SC B3 C2 + 09 SC B3 C2 | 104,300 | 700.113 (<= 693.807, item 3) | 675.740 | master | 3.48 (2.60) | no | OOT (0.91) | 0.983 |
| written | 1 | 08 SC B3 C2 | 52,150 | 1,131.800 | 1,115.251 | enumeration | 1.46 | no (site 09 open) | OOO | 0.742 |
| written | 2 | 04 SC B2 C2 + 09 SC B4 C2 | 104,300 | 699.957 | 676.240 | master | 3.39 | no | OOO | 0.983 |
| written | 3-4 | 04 SC B4 C2 + 09 SC B4 C2 | 105,200 | 693.807 | 676.240 | master | 2.53 | no | OOO | 0.983 |

V of the best layouts with exact-t 95 % CIs over the scenarios (demand variation shared by all layouts): relaxed m = 1
1,052.99 [920.86, 1,185.13]; written m = 1 1,131.80 [1,065.24, 1,198.36]; written m = 2 699.96 [509.64, 890.28];
written m = 3-4 693.81 [517.25, 870.37]. End-adjusted values are 0.5-1.8 USD higher (1,054.07; 1,132.34; 701.01;
695.01). At the two-site layouts the ILP serves 98.3 % of the orders (0.67 unserved per window), with 5.0-5.7 late
orders per window under written targets (6.0 at the relaxed 08 + 09 layout) and a mean lateness of 1.8-2.0 min per
served order; at one site it serves 74-78 %.

First pass vs second pass (bound from the first-pass cut pool, computed post hoc): relaxed m = 1 LB 1,037.83 -> 1,052.995
(gap 1.44 -> 0 %); written m = 1 1,037.83 -> 1,115.25 (8.35 -> 1.46 %); m = 2-4 674.83 (the trivial bound) -> 675.74
relaxed / 676.24 written (relaxed 3.61 -> 3.48 %; written m = 2 4.45 -> 3.39 %, m = 3-4 4.09 -> 2.53 %; the written gain
comes mostly from the lower UB of the 04 + 09 layouts).

### 3.2 Rule, present-day and round-5 layouts against the bound

Table 2. Regret interval [V_rule - UB, V_rule - LB] in USD per window and in % of V_rule (gap definition
100 (V_rule - V)/V_rule); "lo, own bounds" uses the rule layout's MIP lower bound instead of its incumbent; paired
difference V_rule - V_best over the scenarios (n = 3) with exact-t 95 % CI. CSCD and CSTC choose the same layout at
m = 1-2; the round-5 and present-day rows are identical at m = 3 and 4.

| target | m | layout (rule) | V | ILP st. | regret USD [lo, hi] | regret % [lo, hi] | lo, own bounds | V_rule - V_best [95 % CI] |
|---|---|---|---|---|---|---|---|---|
| relaxed | 1 | 09 SC B3 C2 (CSCD = CSTC) | 1,052.99 | OOO | [0, 0] | [0, 0] | 0 | 0 (is the optimum) |
| relaxed | 1 | 08 SC B3 C2 (CSAV = present-day) | 1,070.07 | OOO | [17.08, 17.08] | [1.60, 1.60] | 17.08 | 17.08 [-19.08, 53.23] |
| relaxed | 2 | 08 + 09, SC B3 C2 (CSCD = CSTC) | 700.11 | OOT | [0 (0.16), 24.37] | [0, 3.48] | 0 | 0 (is the incumbent) |
| relaxed | 2 | 08 + 14, SC B3 C2 (CSAV) | 740.04 | OTT | [39.92, 64.30] | [5.39, 8.69] | 20.84 | 39.92 [-22.20, 102.05] |
| relaxed | 2-4 | 03 SC B2 C1 + 08 SC B4 C3 (present-day) | 714.37 | TOO | [14.26, 38.63] | [2.00, 5.41] | 11.65 | 14.26 [-20.90, 49.41] |
| relaxed | 2-4 | 06 SC B4 C2 + 12 S B3 (round-5) | 706.82 | TOT | [6.71, 31.08] | [0.95, 4.40] | 1.51 | 6.71 [-11.92, 25.33] |
| relaxed | 3 | 08 + 09 + 10 (CSCD) | 702.88 | OOO | [2.76, 27.14] | [0.39, 3.86] | 2.76 | 2.76 [-15.74, 21.26] |
| relaxed | 3 | 08 + 09 + 12 (CSTC) | 701.66 | OOO | [1.55 (7.86), 25.92] | [0.22, 3.69] | 1.55 | 1.55 [-14.67, 17.77] |
| relaxed | 3 | 02 + 08 + 14 (CSAV) | 706.72 | OOO | [6.60, 30.98] | [0.93, 4.38] | 6.60 | 6.60 [-19.73, 32.94] |
| relaxed | 4 | 08 + 09 + 10 + 11 (CSCD) | 713.28 | OOO | [13.17, 37.54] | [1.85, 5.26] | 13.17 | 13.17 [-8.36, 34.70] |
| relaxed | 4 | 08 + 09 + 12 + 13 (CSTC) | 713.42 | OOT | [13.31, 37.68] | [1.87, 5.28] | 11.82 | 13.31 [-1.36, 27.97] |
| relaxed | 4 | 02 + 08 + 11 + 14 (CSAV) | 712.10 | OTO | [11.99, 36.36] | [1.68, 5.11] | 10.94 | 11.99 [-26.71, 50.69] |
| written | 1 | 09 SC B3 C2 (CSCD = CSTC) | 1,143.03 | TTT | [11.23, 27.78] | [0.98, 2.43] | **0** (may be optimal) | 11.23 [-93.02, 115.47] |
| written | 1 | 08 SC B3 C2 (CSAV = present-day) | 1,131.80 | OOO | [0, 16.55] | [0, 1.46] | 0 | 0 (is the incumbent) |
| written | 2 | 08 + 09 (CSCD = CSTC) | 706.26 | OOT | [6.30, 30.02] | [0.89, 4.25] | 3.04 | 6.30 [-9.94, 22.55] |
| written | 2 | 08 + 14 (CSAV) | 752.74 | TTT | [52.78, 76.50] | [7.01, 10.16] | 32.92 | 52.78 [-16.57, 122.13] |
| written | 2 | 03 SC B2 C1 + 08 SC B4 C3 (present-day) | 732.84 | TTT | [32.88, 56.60] | [4.49, 7.72] | 15.47 | 32.88 [-9.00, 74.76] |
| written | 2 | 06 SC B4 C2 + 12 S B3 (round-5) | 802.43 | TTT | [102.47, 126.19] | [12.77, 15.73] | 55.83 | **102.47 [37.22, 167.72]** |
| written | 3-4 | 06 SC B4 C2 + 12 S B3 (round-5) | 802.43 | TTT | [108.62, 126.19] | [13.54, 15.73] | 61.98 | **108.62 [53.72, 163.52]** |
| written | 3-4 | 08 + 09 (CSCD m = 2 layout) | 706.26 | OOT | [12.46, 30.02] | [1.76, 4.25] | 9.19 | 12.46 [-16.09, 41.00] |
| written | 3 | 08 + 09 + 10 (CSCD) | 705.74 | OOO | [11.93, 29.50] | [1.69, 4.18] | 11.91 | 11.93 [-1.68, 25.55] |
| written | 3 | 08 + 09 + 12 (CSTC) | 703.61 | OOO | [9.80, 27.37] | [1.39, 3.89] | 9.78 | 9.80 [-5.06, 24.65] |
| written | 3 | 02 + 08 + 14 (CSAV) | 711.28 | OTO | [17.48, 35.04] | [2.46, 4.93] | 15.87 | 17.48 [-5.94, 40.89] |
| written | 3-4 | 03 SC B3 C1 + 08 SC B5 C3 (present-day) | 707.16 | OOO | [13.35, 30.92] | [1.89, 4.37] | 13.34 | 13.35 [-4.39, 31.09] |
| written | 4 | 08 + 09 + 10 + 11 (CSCD) | 714.50 | OOO | [20.69, 38.26] | [2.90, 5.35] | 20.67 | **20.69 [10.97, 30.41]** |
| written | 4 | 08 + 09 + 12 + 13 (CSTC) | 713.17 | OOO | [19.36, 36.93] | [2.71, 5.18] | 19.36 | **19.36 [7.01, 31.71]** |
| written | 4 | 02 + 08 + 11 + 14 (CSAV) | 712.60 | OTO | [18.79, 36.36] | [2.64, 5.10] | 18.59 | 18.79 [-6.41, 43.99] |

Values in parentheses for relaxed m = 2 and CSTC m = 3: lower regret ends against the written-implied relaxed UB
(item 3); against the written values of the 04 + 09 layouts, which bound their relaxed values from above, the paired
differences are 0.16 [-11.26, 11.58] (CSCD m = 2) and 7.86 [-5.88, 21.59] (CSTC m = 3).

### 3.3 Does siting beat rule siting?

Table 3. Best rule layout (minimum over CSCD, CSTC, CSAV at that budget) against the best layout found; gap =
100 (V_best rule - V)/V_best rule, lower end against UB, upper end against LB (no layout can be cheaper than LB).

| target | m | best rule layout | V best rule | gap % [vs UB, vs LB] | paired V_rule - V_best [95 % CI], n = 3 |
|---|---|---|---|---|---|
| relaxed | 1 | CSCD = CSTC (09) | 1,052.99 | [0, 0] (the rule layout is the certified optimum) | 0 |
| relaxed | 2 | CSCD = CSTC (08 + 09) | 700.11 | [0.02, 3.48] | 0.16 [-11.26, 11.58] vs the written value of 04 + 09 |
| relaxed | 3 | CSTC (08 + 09 + 12) | 701.66 | [1.12, 3.69] | 7.86 [-5.88, 21.59] vs the written value of 04 + 09 (B4) |
| relaxed | 4 | CSAV (02 + 08 + 11 + 14) | 712.10 | [2.57, 5.11] | 18.29 [-8.87, 45.46] vs the written value of 04 + 09 (B4) |
| written | 1 | CSAV = present-day (08) | 1,131.80 | [0, 1.46] | 0 (the rule layout is the incumbent; CSCD 09 may be the optimum) |
| written | 2 | CSCD = CSTC (08 + 09) | 706.26 | [0.89, 4.25] | 6.30 [-9.94, 22.55]; per-scenario gap 0.85 % [-1.19, 2.90] |
| written | 3 | CSTC (08 + 09 + 12) | 703.61 | [1.39, 3.89] | 9.80 [-5.06, 24.65] |
| written | 4 | CSAV (02 + 08 + 11 + 14) | 712.60 | [2.64, 5.10] | 18.79 [-6.41, 43.99]; the best rule layout of any budget <= 4 (CSTC m = 3) is 9.80 [-5.06, 24.65] dearer |

Shown: at one unit the demand-proportional rule picks the certified relaxed optimum, and with written targets the
rule layouts are the only two candidates left (08, 09). At two to four units no rule layout is significantly worse than
the best layout found except the four-site CSCD and CSTC layouts (2.90 and 2.71 %, CIs 10.97-30.41 and 7.01-31.71 USD)
and the round-5 layout (written, 12.8-13.5 %). The best possible advantage of optimised siting over the best rule
layout is bounded by the regret upper ends: 0 (relaxed m = 1), at most 1.46 % (written m = 1), 3.5 % (relaxed m = 2),
4.25 % (written m = 2), 3.7-3.9 % (m = 3) and 5.1 % (m = 4). Not shown: that optimised siting beats rule siting by a significant margin at any budget.

### 3.4 Follower dependence

Table 4. The same layout under the ILP follower, rule r2 and the selfish follower M4 (r2 and M4 do not act on the end
targets; one set of values per layout). Gap = 100 (V_follower - V_ILP)/V_follower, end-adjusted; mean [95 % CI], n = 3.

| layout | V ILP (target, st.) | V r2 | r2 - ILP [CI] | gap vs r2 % [CI] | V selfish | selfish - ILP [CI] | served ILP / r2 / selfish |
|---|---|---|---|---|---|---|---|
| 04 SC B2 C2 + 09 SC B4 C2 (written best m = 2) | 699.96 (written, OOO) | 1,148.45 | 448.49 [387.58, 509.41] | 39.1 [35.1, 43.1] | 1,168.58 | 468.63 [379.97, 557.28] | 0.983 / 0.825 / 0.808 |
| 04 SC B4 C2 + 09 SC B4 C2 (written best m = 3-4) | 693.81 (written, OOO) | 1,111.78 | 417.97 [-46.88, 882.82] | 36.2 [10.0, 62.3] | 1,040.53 | 346.73 [-15.78, 709.23] | 0.983 / 0.850 / 0.867 |
| 08 + 09 (CSCD m = 2) | 706.26 (written, OOT) | 1,260.56 | 554.30 [406.20, 702.40] | 44.0 [32.6, 55.4] | 1,257.16 (one equilibrium unconverged) | 550.90 [419.91, 681.89] | 0.983 / 0.800 / 0.783 |
| 08 + 09 (CSCD m = 2) | 700.11 (relaxed, OOT) | 1,260.56 | 560.45 [416.31, 704.59] | 44.4 [33.6, 55.3] | 1,257.16 | 557.05 [433.05, 681.05] | 0.983 / 0.800 / 0.783 |
| 08 + 09 + 12 (CSTC m = 3) | 703.61 (written, OOO) | 1,207.13 | 503.53 [242.00, 765.05] | 41.4 [30.1, 52.8] | 1,046.79 | 343.18 [56.08, 630.28] | 0.983 / 0.833 / 0.883 |
| 08 SC B3 C2 (written best m = 1) | 1,131.80 (written, OOO) | 1,873.12 | 741.32 [655.69, 826.96] | 39.6 [36.4, 42.8] | 1,873.12 | 741.32 [655.69, 826.96] | 0.742 / 0.442 / 0.442 |
| 09 SC B3 C2 (relaxed optimum m = 1) | 1,052.99 (relaxed, OOO) | 1,834.85 | 781.85 [494.19, 1,069.52] | 42.4 [36.0, 48.8] | 1,834.85 | 781.85 [494.19, 1,069.52] | 0.783 / 0.483 / 0.483 |
| 06 SC B4 C2 + 12 S B3 (round-5; compliance stage) | 802.43 (written, TTT) | 1,238.55 | 436.12 [180.92, 691.32] | 35.0 [18.8, 51.3] (not end-adj.) | 1,248.87 | 446.44 [191.93, 700.96] | 0.958 / 0.750 / 0.758 |

Paired layout differences under each follower (V_a - V_b, n = 3): 04 + 09 (B4) minus 08 + 09: ILP written -12.46
[-41.00, 16.09], r2 -148.79 [-556.59, 259.02], selfish -216.63 [-660.69, 227.43]; 04 + 09 (B2/B4) minus 08 + 09:
-6.30 [-22.55, 9.94], -112.11 [-247.46, 23.23], -88.58 [-286.88, 109.72]; site 08 minus site 09: ILP written -11.23
[-115.47, 93.02], ILP relaxed +17.08 [-19.08, 53.23], r2 and selfish +38.27 [-278.17, 354.71]; round-5 minus CSCD
m = 2 under r2 -22.02 (gap 1.65 % [-10.80, 14.10]), under the selfish follower gap 0.61 % [-12.20, 13.42].

Shown: on every layout the ILP is 35-44 % cheaper than r2 and 32-44 % cheaper than the selfish follower (gap relative
to the follower's cost; all CIs above zero), and the served share falls from 0.98 to 0.78-0.88 at two or three sites. Among the four
cross-evaluated multi-site layouts the best layout found under the ILP is also the cheapest under r2 and the selfish follower, but none
of these rankings is significant; at one unit the written ILP prefers site 08 while the relaxed ILP, r2 and the
selfish follower prefer site 09 (none significant). Under the selfish follower a third site helps (CSTC m = 3,
1,046.79 vs 1,257.16 at CSCD m = 2), as at the legacy prices, again without significance. Not shown: that the optimal
layout depends on the follower.

### 3.5 Price of recovery per layout

Table 5. Written minus relaxed ILP total (USD per window), paired over scenarios, n = 3; status relaxed / written.

| layout | V relaxed | V written | st. | price of recovery [95 % CI] | end-adjusted [CI] |
|---|---|---|---|---|---|
| 06 SC B4 C2 + 12 S B3 (round-5, swap-only site) | 706.82 | 802.43 | TOT / TTT | **95.61 [13.75, 177.47]** | 94.65 [12.95, 176.35] |
| 09 SC B3 C2 (one site) | 1,052.99 | 1,143.03 | OOO / TTT | 90.03 [56.37, 123.70] (upper bound) | 89.54 [55.83, 123.24] |
| 08 SC B3 C2 (one site) | 1,070.07 | 1,131.80 | OOO / OOO | 61.73 [-15.78, 139.24] | 61.20 [-16.19, 138.60] |
| 03 SC B2 C1 + 08 SC B4 C3 (one-charger site) | 714.37 | 732.84 | TOO / TTT | 18.47 [-2.70, 39.64] | 17.69 [-3.32, 38.70] |
| 08 + 14 (CSAV m = 2) | 740.04 | 752.74 | OTT / TTT | 12.70 [-16.96, 42.36] | 11.94 [-17.87, 41.74] |
| 08 + 09 (CSCD m = 2) | 700.11 | 706.26 | OOT / OOT | 6.15 [-1.75, 14.05] | 5.35 [-2.41, 13.12] |
| 03 + 04 B2C1 + 08 B4C3 (one-charger site) | 712.12 | 716.75 | OOO / OOO | 4.62 [-9.65, 18.90] | 3.47 [-10.85, 17.80] |
| 02 + 08 + 14 (CSAV m = 3) | 706.72 | 711.28 | OOO / OTO | 4.56 [-1.93, 11.05] | 3.26 [-3.07, 9.59] |
| 08 + 09 + 10 (CSCD m = 3) | 702.88 | 705.74 | OOO / OOO | 2.86 [-3.67, 9.40] | 1.58 [-5.03, 8.20] |
| 03 + 04 + 06 B2C1 + 08 B4C3 (one-charger site) | 723.06 | 725.50 | OOO / OOO | 2.44 [-4.01, 8.89] | 1.26 [-4.96, 7.48] |
| 08 + 09 + 12 (CSTC m = 3) | 701.66 | 703.61 | OOO / OOO | 1.94 [-0.52, 4.40] | 0.58 [-2.04, 3.20] |
| 08 + 09 + 10 + 11 (CSCD m = 4) | 713.28 | 714.50 | OOO / OOO | 1.22 [0.81, 1.63] | -0.04 [-0.62, 0.54] |
| 02 + 08 + 11 + 14 (CSAV m = 4) | 712.10 | 712.60 | OTO / OTO | 0.49 [-1.57, 2.56] | -0.56 [-2.87, 1.75] |
| 08 + 09 + 12 + 13 (CSTC m = 4) | 713.42 | 713.17 | OOT / OOO | -0.26 [-5.11, 4.60] (item 7) | -1.17 [-5.61, 3.27] |

The written best layouts (04 + 09) were priced under written targets only, so their price of recovery is not known.
Shown: the swap-only site costs about 96 USD per window of recovery (CI above zero, TIME_LIMIT incumbents with large
MIP gaps), the single sites 62-90 USD, the multi-site layouts whose sites all have two chargers -0.3 to 12.7 USD
(6.2 or less except CSAV m = 2 with time-limited written incumbents; CIs include zero except CSCD m = 4, 1.22
[0.81, 1.63]). This is what places the round-5 layout last under written targets while it is within
1 % of the best under relaxed targets.

### 3.6 Computational story: first vs second pass

Table 6. Wall time per LP-solved layout (three scenario LPs in parallel, three workers x three threads), timed from
consecutive records; second-pass Gurobi time per scenario LP from the records.

| pass | layout size | layouts timed | median s | IQR s | range s | Gurobi s per scenario LP |
|---|---|---|---|---|---|---|
| first (warm-started dual simplex) | one site | 97 (relaxed 51, written 46) | 369 (relaxed 388, written 282) | 323-474 / 231-443 | 158-1,575 | not recorded |
| first | two to four sites | 18 | 388 (relaxed 255, written 482) | 129-444 / 299-1,116 | 59-3,157 | not recorded |
| second (cold barrier + crossover) | one site | 10 | 16 | 14-16 | 13-18 | 13.4-13.6 median (10.5-17.1) |
| second | two to four sites | 76 | 28 | 25-32 | 17-42 | 26.2 median (13.7-42.2) |

* LP re-solves are 18-24 times faster for one-site layouts and about 14 times faster for multi-site layouts (ratio of
  medians); the first pass spent about 11 h of its 19.3 h on one-site LPs (50 of 90 one-site layouts relaxed, 45 of 90
  written, both stopped by the wall) and the machine was paging (diagnosis note).
* Envelope pruning before any LP resolved 88 (relaxed) and 87 (written) of the 90 one-site layouts in seconds; relaxed
  m = 1 then needed 2 LPs and one 900-s escalation (13.0 min) to certify, written m = 1 4 LPs, one bound-stopped
  pricing and 7 escalations (153 min) to leave one layout open.
* The guaranteed final master bound turned "LB None" into a finite LB at every budget; at m >= 2 it is only 0.9-1.4 USD
  above the trivial two-site bound, and 72 written integer-phase proposals were all LP-pruned (each costs about 30 s of
  LP and closes essentially that layout only), so a certificate at m >= 2 is out of reach with single-layout LP cuts.
* ILP time: 3.9 h in the first pass (75 solves) and 3.8 h in the second (32 solves, of which 2.7 h in the eight
  escalations of sites 09 and 08).

## 4. Comparison with the legacy-price study (X6, P 30 / v 36)

The legacy study used a truncated bi-level greedy search (four layouts priced, no layout at m = 1), the open-sites
repositioning library and the legacy prices; levels are not comparable, rankings and mechanisms are.

| item | legacy prices (X6) | new prices (this report) |
|---|---|---|
| search | greedy + local search, 4 layouts priced, no bound | Benders certificate: 14 (relaxed) and 19 (written) layouts priced, 206 LP-solved, 247 pruned; m = 1 relaxed certified |
| m = 1 | CSAV 08 795.4 vs CSCD 09 796.4 (tie, written) | relaxed: 09 certified optimal (1,052.99), 08 +17.1 [-19.1, 53.2]; written: 08 1,131.80 or 09 (in [1,115.25, 1,143.03]) |
| m = 2 best | CSCD 08 + 09 676.6 (best of four priced) | 04 SC B2 C2 + 09 SC B4 C2 699.96; CSCD 08 + 09 +6.30 [-9.94, 22.55] (0.89 %) |
| round-5 (bi-level) layout vs CSCD m = 2, written ILP, paired gap | -3.99 % [-8.74, 0.77] | -14.02 % [-27.78, -0.26] (round-5 dearer in all three scenarios) |
| same, relaxed targets | -0.00 % [-0.51, 0.51] (tie) | -0.90 % [-3.50, 1.69] (tie) |
| same, rule r2 | round-5 12.73 % [9.86, 15.61] cheaper than the best rule-sited layout | round-5 1.65 % [-10.80, 14.10] cheaper than CSCD (CSAV not evaluated under r2) |
| same, selfish follower | 5.69 % [-4.90, 16.28] cheaper | 0.61 % [-12.20, 13.42] cheaper |
| price of decentralisation (selfish - ILP written) | 354.3 [276.7, 432.0] at the round-5 layout | 446.4 [191.9, 701.0] at the round-5 layout; 468.6 [380.0, 557.3] at the written best m = 2 layout |
| price of recovery | 28.1 (round-5), 1.6 (CSCD m = 2), 17.3 (08), 38.6 (present-day) | 95.6 (round-5), 6.2 (CSCD m = 2), 61.7 (08), 18.5 (present-day m = 2, capacity-matched anew) |
| number of sites that pays (ILP, written) | second CSCD site 795.4 -> 676.6; third and fourth do not lower V | second site 1,131.80 -> 699.96 (-431.8 [306.3, 557.4] USD, -38 %); third and fourth rule sites do not (703.6-714.5); the best m = 3-4 layout keeps two sites and adds spares |
| ILP vs r2 gap at CSCD m = 2 (relaxed) | 42.0 % [31.5, 52.6] (vs r2) | 44.4 % [33.6, 55.3] (end-adjusted) |
| selfish equilibria converged | 82 of 84 | 17 of 18 (same unconverged cell: CSCD m = 2, scenario 2) |

What changed: the bi-level layout of round 5 is now clearly the worst compared layout under written targets, because
the recovery cost of its swap-only site more than tripled (28 -> 96 USD per window; an unserved order now costs 60 instead of
30 USD); its legacy advantage under rule r2 (12.7 %) does not reproduce. What did not change: the demand-proportional
rule layout 08 + 09 stays within about 1 % of the best two-site layout, a second site pays and further rule sites do
not, the ILP is 35-44 % cheaper than r2 on every layout, and layout rankings under r2 and the selfish follower are not
distinguishable at n = 3.

## 5. Interpretation: shown vs suggested

Shown (records, n = 3 scenarios, this library):
* The relaxed one-unit siting problem is solved to certified optimality: site 09 (SC, 3 spares, 2 chargers) at
  1,052.995 USD per window, which is also the CSCD and CSTC rule layout.
* Every bound is valid and finite: V*_1 in [1,115.25, 1,131.80] (written); V*_2 in [676.24, 699.96] (written) and
  [675.74, 699.96] (relaxed, using the written incumbent); V*_3 and V*_4 in [676.24, 693.81] (written) and [675.74,
  693.81] (relaxed).
* Rule siting is close to the best layouts found: the best rule layout is within 0-2.6 % of the best layout found at
  every budget and target (no paired difference significant), and no layout can beat it by more than 1.5 % at one
  unit and 3.5-5.1 % at two to four units.
* Over-building with four rule sites costs 19-21 USD per window (2.7-2.9 %, significant) against two well-stocked
  sites; the round-5 layout costs 102-109 USD more under written targets (significant), almost all of it recovery at
  its swap-only site (price of recovery 95.6 USD; the relaxed difference, 6.7 USD, is not significant).
* Optimisation of station operations matters far more than siting: the ILP is 32-44 % cheaper than r2 or the selfish
  follower on the same layout, against at most about 1-3 % between the best and the rule layouts.
* The computational fix worked for one-site layouts (LP re-solves 18-24 times faster; envelope pruning resolved 97 %
  of the one-site layouts without an LP) and failed to close m >= 2.

Suggested, not shown:
* That 04 + 09 (two SC sites, spares shifted to 09) is the optimal two-unit layout: 18-41 % of the two-site layouts
  remain open and nothing was checked at m = 3-4.
* That optimised siting beats rule siting at the new prices: the measured advantages (0.9-2.6 %) are below the
  scenario noise and within the regret intervals.
* That buying spares at two sites is better than a third site (693.81 vs 703.61, 9.80 [-5.06, 24.65]).
* That layout rankings depend on the follower: the rankings differ only at one unit and never significantly.

What the paper may claim: (i) a certified optimum for the one-unit relaxed problem and certified bounds (gap 1.5-3.5 %)
elsewhere; (ii) demand-proportional rule siting is within the certified regret intervals and not significantly worse
than the best layouts found, so optimised siting adds at most a few percent; (iii) the coordination gap on a given
layout is an order of magnitude larger than the siting gap; (iv) swap-only sites carry a large recovery cost under
written targets, which decides the rank of the round-5 layout. It may not claim a certified optimal layout for
m >= 2, a significant siting advantage, or follower-dependent optimal layouts.

## 6. Figures (`outputs/r6_o2/figs/`, vector PDF + 300-dpi PNG; script `figs/siting_report.py`)

* `fig_siting_bounds.pdf/.png` (double column): expected cost V per 4-h window of the best layout found and of the
  CSCD, CSTC, CSAV, present-day and round-5 layouts at each budget, relaxed (a, b) and written (c, d) targets, new
  prices, ILP follower, mean over three demand scenarios. Grey box: certified range [LB, UB] of the optimal value V*;
  a vertical line runs from a layout's V down to its MIP lower bound where its ILPs are time-limited; open diamonds:
  written value of the two-site layouts at 04 and 09, an upper bound on their relaxed value; dashed: trivial two-site
  bound (674.83).
* `fig_siting_passes.pdf/.png` (double column): (a) wall time per LP-solved layout (three scenario LPs) in the first pass
  (warm-started dual simplex) and the second pass (cold barrier), by layout size, log scale, label = median and n;
  (b) bound gap 100 (UB - LB)/UB per target and budget, first pass (bound from its cut pool, computed afterwards) vs
  second pass (guaranteed master bound), with the 0.25 % certification tolerance.
* `fig_siting_followers.pdf/.png` (double column): (a) V of six layouts under the ILP follower (written targets), rule
  r2 and the selfish follower M4, mean with exact-t 95 % CI and the three scenarios as dots; (b) price of recovery
  (written minus relaxed V, ILP follower) per layout with 95 % CI, coloured by whether every site has two or more
  chargers, a site has one charger, or a site is swap-only.

## 7. Manuscript items replaced (`manuscript/PENDING_R6.md`)

**Item 2 (Manhattan siting) -- replaced, except the parts listed as still pending.** New statements:
* Settings paragraph (4.5, S2 "Settings of the siting experiments"): "The Manhattan study uses the family manhattan at
  the calibrated prices: 15 candidate sites with 14 size options each (swap-only with 1-4 spares, charge-only hub with
  2 or 4 chargers, co-located with 1-4 spares and 1-2 chargers), budgets of m = 1-4 units of 52,150 USD, three demand
  scenarios and the ILP follower with an all-candidates repositioning library. A Benders scheme bounds the optimal
  value V*_m from below (safe Lagrangian cuts of the LP relaxation, integer L-shaped and lifted cuts, and a pruned
  enumeration of the 90 one-unit layouts) against the best layout found; a budget is certified when the gap is at
  most max(0.25 %, 1 USD)."
* Section 6.8 / Table tab:res:siting / Figure fig:res:siting (replace with Table 1-3 above and `fig_siting_bounds`):
  "With relaxed targets one co-located site at 09 (three spares, two chargers) is the certified one-unit optimum
  (1,053.0 USD per window), and it is also the CSCD and CSTC rule layout. With the written targets the one-unit optimum
  is site 08 (1,131.8 USD) or site 09, whose value lies between 1,115.3 and 1,143.0 USD (bound gap 1.46 %). At two to
  four units no budget is certified: the best layouts found, two co-located sites at 04 and 09 (699.96 USD at two
  units; 693.81 USD with four spares at each site at three and four units), lie within 2.5-3.5 % of the lower bound."
* Rule comparison (6.8, 7.2): "Demand-proportional rule siting is not significantly worse than the best layouts found:
  at two units the CSCD layout (08 and 09) costs 6.3 USD per window more (0.89 %; 95 % CI -9.9 to 22.6 USD; n = 3) and
  at most 30.0 USD (4.25 %) more than any layout can cost; the four-site CSCD and CSTC layouts cost 20.7 and 19.4 USD
  more (2.90 and 2.71 %, CIs 11.0-30.4 and 7.0-31.7 USD) because the budget buys sites instead of spares. The round-5
  bi-level layout (06 and a swap-only site at 12) costs 102.5 USD more (12.8 %; 37.2-167.7 USD) under written targets
  and ties on relaxed targets (+6.7 USD, -11.9 to 25.3)."
* Followers (6.8 paragraph on r2 and the selfish follower; 7.2 "layout rankings ... depend on how riders are operated"):
  "On every evaluated layout the ILP is 35-44 % cheaper than rule r2 and 32-44 % cheaper than the selfish follower
  (at the best two-unit layout 39.1 %, 35.1-43.1, against r2), and there the served share falls from 0.98 to 0.83
  under r2 and 0.81 under the selfish follower. The layout ranking under r2 and the selfish follower agrees with the
  ILP's among the multi-site layouts, and no ranking difference is significant at n = 3; the round-5 layout is no longer cheaper than the rule layout under r2 (1.65 %, -10.8 to 14.1)." This
  replaces the 12.73 % and 5.69 % sentences.
* Price of recovery (6.8 sentence, Manhattan row of Table tab:app:recovery): "Recovery costs 95.6 USD per window
  (13.8-177.5) at the round-5 layout with its swap-only site, 62-90 USD at single sites and -0.3 to 12.7 USD (6.2 USD
  at the CSCD two-site layout) on multi-site layouts whose sites all have two chargers" (replaces 28.1 / 1.6 /
  0.7-1.6 / 28.1-61.1 USD).
* "Number of cabinets that pays" (7.2): "Under the ILP with written targets a second site lowers V from 1,131.8 to
  700.0 USD per window (-38 %; 25-51 %), a third or fourth rule site does not, and the best three-unit layout keeps two
  sites and adds spares."
* 7.3 and future work (siting searches incomplete; "Ranking optimised against rule siting requires a complete bi-level
  search"): "The siting bound is certified for one unit with relaxed targets only; at two to four units the bound
  rests on single-layout LP cuts and is barely above the trivial bound, so a certificate needs stronger cuts or a
  decomposition over sites."
* Abstract last sentence, highlights bullet 5, introduction findings paragraph, Section 8 RQ4: "Optimised siting,
  bounded by a certificate, improves on demand-proportional rule siting by at most a few percent (0-2.6 % at the
  layouts found; by the bound at most 1.5 % at one unit and 3.5-5.1 % at two to four units), whereas coordinating the
  riders on a given layout is 32-44 % cheaper than rule r2 or selfish station choice."
* Coverage rows (Table tab:app:coverage-legacy, Manhattan; item 15): ILP solves 75 + 32 (first and second pass):
  OPTIMAL 70, TIME_LIMIT 32 (MIP gaps 0.09-45.35 %, the 45.35 % row re-solved to optimality), bound-stopped 5;
  18 distinct selfish equilibria, 17 converged; wall 19.3 + 10.7 h.

Still pending under item 2 (not produced by this stage): the map (fig:res:map) must be redrawn with the new chosen
sites (09 relaxed and 08 written at one unit; 04 + 09 at two to four units); the marginal levers at the chosen layout
(fig:app:siting-levers) and the policy-aware siting search (F) were not re-run at the new prices; the Manhattan block of
Table tab:res:headline and the "31.8 / 34.3 %" sentence in 6.2 need the gap against the best rule (best of r2, M2, M3,
M2+M3), of which only r2 was evaluated here (36-44 % on the best and rule layouts, end-adjusted).

**Item 4 (selfish equilibrium, price of decentralisation, compliance) -- partly replaced.** "The price of
decentralisation, the selfish-equilibrium cost minus the ILP cost, is 468.6 USD per window (380.0-557.3) at the best
two-unit layout and 446.4 USD (191.9-701.0) at the round-5 layout (replaces 354.3, 276.7-432.0); 17 of the 18 selfish
equilibria of the Manhattan study converged (replaces 82 of 84)." The compliance sweep (6.9, fig:res:compliance, 36.0 %)
is produced by `outputs/r6_fill/compliance` (which reads the written m = 2 layout 04 + 09 from these records) and is not
covered by this report.

**Item 15 (legacy rows of the coverage and recovery tables) -- Manhattan rows replaced** as stated under item 2.

Not replaced: item 3 (earlier Midtown siting study; the Midtown validation run here is a certifier test, not a re-run
of that study) and item 7 (the 0.30 -> 24.28 USD swap-only sentence in 7.2 is the usd4h transfer experiment; the
Manhattan swap-only price of recovery above is new supporting evidence at the calibrated prices).
