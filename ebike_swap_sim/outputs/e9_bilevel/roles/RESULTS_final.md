# E9.3 -- role separation: co-located only vs no hubs vs hubs allowed (final)

Family `nyc4h_stress2` (6 bikes, 36 orders, H 48, q0 ~ U{3..6} of 12, P_j 2.8 kW, flat 4 kW grid group,
`usd_sunk` costs); 12 Midtown candidates (`../candidates.csv`); demand scenarios seeds 0-2 (p = 1/3);
algorithm (C) greedy + local search with role sets `SC_only` = {SC}, `S_SC` = {S, SC}, `S_C_SC` = {S, C, SC}
at budgets m = 2 (104,300 USD) and m = 3 (156,450 USD); reposition targets `open_sites`; min served share 0.5;
swap-only sites admissible only next to a C / SC object; Gurobi Threads 3, TimeLimit 300 s (600 s for layouts
with a hub), Seed 0; wall budget 7,200 s; cache version `e9-2`. Source files: `records.jsonl`, `results.csv`,
`wall_time.json`, `../logs/roles.log`.

Every ILP total on this family is an upper bound on the written E2 optimum (reposition moves only into the
open sites and the depots; `all_candidates` libraries in `../validate` only), and the R2.4 geometry caveat
applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid). The first E9
launch (family `nyc4h_stress`, archived in `../_first_attempt/`) is superseded by this run and is not used here.

## Summary

All three role sets at both budgets converge to the same single co-located site, L02:SC:B4:C2 (NoMad,
W 29th-30th / 6th Ave, 4 spares, 2 chargers, investment 52,600 USD), with V = 654.53 USD per 4 h window,
expected operating cost 641.00 USD, expected served share 0.852 and zero transfers. Charge-only hubs were priced
five times (C = 2 at L02-L06 next to the start site L01:SC:B3:C2) and every one of them gave exactly the parent's
operating cost plus its allocated setup, V = 684.41 = 655.06 + 29.19 (F_hub) + 2 x 0.082 (bC), i.e. the hub
was never used by any scenario. Swap-only sites were priced seven times (L06, L07, L10, L12 with 1-3 spares)
and saved 0.00-1.02 USD of operations against 12.36-13.03 USD of allocated setup, so none entered either.
Even a second co-located site saves at most 1.09 USD of operations per window against 12.4-13.2 USD of
allocated setup, so the budget beyond one site is left unspent at m = 2 and m = 3 by every role set. Forcing
co-location therefore costs nothing on this family and allowing hubs gains nothing; the E3u finding "hub =
+F_hub, transfers worth 0-9 USD" is reproduced in its extreme form (transfers worth 0 USD).

## Chosen layout per role set and budget

| budget m | budget USD | role set | layout | n_S | n_C | n_SC | investment USD | C_setup (27) | V | opex (expected) | opex per seed 0 / 1 / 2 | served share | transfers | C_reb | status | search complete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 104,300 | SC_only | L02:SC:B4:C2 | 0 | 0 | 1 | 52,600 | 13.522 | 654.525 | 641.003 | 667.823 / 632.507 / 622.679 | 0.852 | 0 | 0 | OK | yes |
| 3 | 156,450 | SC_only | L02:SC:B4:C2 | 0 | 0 | 1 | 52,600 | 13.522 | 654.525 | 641.003 | 667.823 / 632.507 / 622.679 | 0.852 | 0 | 0 | OK | yes |
| 2 | 104,300 | S_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52,600 | 13.522 | 654.525 | 641.003 | 667.823 / 632.507 / 622.679 | 0.852 | 0 | 0 | OK | yes |
| 3 | 156,450 | S_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52,600 | 13.522 | 654.525 | 641.003 | 667.823 / 632.507 / 622.679 | 0.852 | 0 | 0 | OK | yes |
| 2 | 104,300 | S_C_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52,600 | 13.522 | 654.525 | 641.003 | 667.823 / 632.507 / 622.679 | 0.852 | 0 | 0 | OK | yes |
| 3 | 156,450 | S_C_SC | L02:SC:B4:C2 | 0 | 0 | 1 | 52,600 | 13.522 | 654.525 | 641.003 | 667.823 / 632.507 / 622.679 | 0.852 | 0 | 0 | OK | yes |

Mean cost components of the chosen layout (identical in all six rows, USD per window): C_setup 13.52,
C_elec 0.56 (1.74 kWh purchased), C_travel 11.95, response 462.5, lateness 6.0 (1.67 late orders), unserved
160.0 (5.33 orders x 30 USD), C_reb 0.00. Served per seed 30 / 31 / 31 of 36 orders; 26.7 stock-out slots per
window at the site. The investment of 52,600 USD exceeds the m = 1 budget (52,150) by the fourth spare, so this
layout is affordable only from m = 2 on; 51,700 USD (m = 2) and 103,850 USD (m = 3) of the budget are unspent.

## Priced hub and swap-only moves (why no hub and no swap-only site was ever chosen)

All additions were priced as the second object next to the greedy start L01:SC:B3:C2 (V 655.056, opex 641.866,
C_setup 13.190) in the forward step, except the L06 rows, which are local-search neighbours of the final layout
L02:SC:B4:C2 (V 654.525, opex 641.003, C_setup 13.522). "delta setup" is the allocated setup (27) the object adds,
"delta opex" the change of the expected lower-level operating cost; V = parent V + delta setup + delta opex.

| move | role added | layout | investment USD | V | delta setup | delta opex | transfers used (seeds 0/1/2) | gain per USD | why rejected |
|---|---|---|---|---|---|---|---|---|---|
| hub C=2 at L02 | C | L01:SC:B3:C2 + L02:C:B0:C2 | 102,950 | 684.410 | +29.354 | +0.000 | 0 / 0 / 0 | -5.78e-4 | hub never used: opex identical to the parent on every seed |
| hub C=2 at L03 | C | L01:SC:B3:C2 + L03:C:B0:C2 | 102,950 | 684.410 | +29.354 | +0.000 | 0 / 0 / 0 | -5.78e-4 | same |
| hub C=2 at L04 | C | L01:SC:B3:C2 + L04:C:B0:C2 | 102,950 | 684.410 | +29.354 | +0.000 | 0 / 0 / 0 | -5.78e-4 | same |
| hub C=2 at L05 | C | L01:SC:B3:C2 + L05:C:B0:C2 | 102,950 | 684.410 | +29.354 | +0.000 | 0 / 0 / 0 | -5.78e-4 | same |
| hub C=2 at L06 | C | L01:SC:B3:C2 + L06:C:B0:C2 | 102,950 | 684.410 | +29.354 | +0.000 | 0 / 0 / 0 | -5.78e-4 | same |
| swap-only B=3 at L10 | S | L01:SC:B3:C2 + L10:S:B3:C0 | 103,500 | 667.065 | +13.026 | -1.018 | 0 / 0 / 0 | -2.34e-4 | 3 dead-stock spares save 1.02 USD, cost 13.03 |
| swap-only B=2 at L12 | S | L01:SC:B3:C2 + L12:S:B2:C0 | 103,050 | 667.090 | +12.694 | -0.660 | 0 / 0 / 0 | -2.36e-4 | saves 0.66, costs 12.69 |
| swap-only B=1 at L12 | S | L01:SC:B3:C2 + L12:S:B1:C0 | 102,600 | 667.234 | +12.362 | -0.184 | 0 / 0 / 0 | -2.41e-4 | saves 0.18, costs 12.36 |
| swap-only B=1 at L07 | S | L01:SC:B3:C2 + L07:S:B1:C0 | 102,600 | 667.234 | +12.362 | -0.184 | 0 / 0 / 0 | -2.41e-4 | same value as L12:S:B1 (one spare used the same way) |
| swap-only B=3 at L12 | S | L01:SC:B3:C2 + L12:S:B3:C0 | 103,500 | 667.269 | +13.026 | -0.814 | 0 / 0 / 0 | -2.38e-4 | saves 0.81, costs 13.03 |
| swap-only B=1 at L06 (local search) | S | L02:SC:B4:C2 + L06:S:B1:C0 | 103,050 | 666.887 | +12.362 | +0.000 | 0 / 0 / 0 | - | spare never used next to the 4-spare site |
| co-located B=2 C=1 at L10 (best second site) | SC | L01:SC:B3:C2 + L10:SC:B2:C1 | 103,450 | 666.908 | +12.776 | -0.924 | 0 / 0 / 0 | -2.31e-4 | for comparison: the best SC addition is rejected for the same reason |
| co-located B=3 C=1 at L10 (largest opex saving) | SC | L01:SC:B3:C2 + L10:SC:B3:C1 | 103,900 | 667.075 | +13.108 | -1.090 | 0 / 0 / 0 | -2.32e-4 | largest operating saving of any second site: 1.09 USD |

Transfers: `transfers_used = 0` and `C_reb = 0` in all 84 lower-level solves. Every two-site layout carries the
shuttle timetable between its charge-capable and swap-capable objects (`n_services` 14-16 per scenario on the
hub, swap-only and two-SC layouts; 0 on single sites), and the ILP never used one: the hub never shipped a
battery to the swap site, and a swap-only site lived on its initial spares only. The hub rows are identical for L02-L06 because the hub does nothing; the ILP solved them
in 12-46 s under the 600 s hub time limit.

F_hub sensitivity (design section 7, "if hubs are never chosen"): not run in this batch (no `F_hub` variant in
`records.jsonl`). It is not needed for the conclusion: since the lower level treats C_setup as a constant and the
hub layouts have exactly the parent's operating cost on every seed, V(parent + hub) = V(parent) + F_hub + C bC for
any F_hub, so a hub would enter only at F_hub + 2 bC < 0; at the alternative value F_hub = 12.03 the hub move would
still cost +12.19 USD per window for zero operating benefit. Hubs with C = 4 and hubs at L07-L12 were not priced
(see coverage); the argument applies to them only if they are equally unused, which the zero transfer usage of
every priced hub makes very likely but does not prove.

## Greedy search, step by step

The singleton start and the SC forward candidates are shared by the three role sets (cache hits); S_SC adds the
five swap-only candidates, S_C_SC adds the five hub candidates. Baseline V is the screening value (baseline
policy, milliseconds); V is the lower-level ILP value on seeds 0-2. k_screen = 5 per added role.

| role set | step | layout tried | investment USD | baseline V (screen) | V (ILP) | served | decision / reason |
|---|---|---|---|---|---|---|---|
| all | singleton 1 | L05:SC:B3:C2 | 52,150 | 1016.9 | 655.171 | 0.852 | usable |
| all | singleton 2 | L11:SC:B3:C2 | 52,150 | 1068.7 | 658.540 | 0.843 | usable |
| all | singleton 3 | L08:SC:B3:C2 | 52,150 | 1068.9 | 656.998 | 0.852 | usable |
| all | singleton 4 | L01:SC:B3:C2 | 52,150 | 1072.3 | 655.056 | 0.852 | usable, lowest V |
| all | singleton 5 | L05:SC:B2:C2 | 51,700 | 1072.3 | 656.634 | 0.843 | usable |
| all | start | L01:SC:B3:C2 | 52,150 | - | 655.056 | 0.852 | best singleton by V (5 priced; only SC singletons are admissible: S needs a charger, C cannot serve) |
| all | forward SC 1 | + L10:SC:B2:C1 | 103,450 | 1019.0 | 666.908 | 0.852 | V rises by 11.85: rejected |
| all | forward SC 2 | + L10:SC:B2:C2 | 103,850 | 1019.2 | 666.990 | 0.852 | rejected (least negative gain per USD, -2.308e-4) |
| all | forward SC 3 | + L10:SC:B3:C1 | 103,900 | 1019.2 | 667.075 | 0.852 | rejected |
| all | forward SC 4 | + L10:SC:B3:C2 | 104,300 | 1019.3 | 667.157 | 0.852 | rejected |
| all | forward SC 5 | + L12:SC:B2:C1 | 103,450 | 1023.4 | 667.172 | 0.852 | rejected |
| S_SC, S_C_SC | forward S 1 | + L10:S:B3:C0 | 103,500 | 1019.0 | 667.065 | 0.852 | rejected |
| S_SC, S_C_SC | forward S 2 | + L12:S:B2:C0 | 103,050 | 1023.2 | 667.090 | 0.852 | rejected |
| S_SC, S_C_SC | forward S 3 | + L12:S:B3:C0 | 103,500 | 1023.5 | 667.269 | 0.852 | rejected |
| S_SC, S_C_SC | forward S 4 | + L12:S:B1:C0 | 102,600 | 1028.4 | 667.234 | 0.852 | rejected |
| S_SC, S_C_SC | forward S 5 | + L07:S:B1:C0 | 102,600 | 1029.3 | 667.234 | 0.852 | rejected |
| S_C_SC | forward C 1-5 | + L02 / L03 / L04 / L05 / L06 :C:B0:C2 | 102,950 | 1101.6 | 684.410 | 0.852 | rejected, hub unused (gain per USD -5.78e-4) |
| all | forward stop | L01:SC:B3:C2 | 52,150 | - | 655.056 | - | no improving addition; frontier = {L01:SC:B3:C2} |
| all, m = 2 and 3 | local search pass 1 | L01:SC:B4:C2 (size B+1) | 52,600 | - | 654.704 | 0.852 | accepted (-0.352): the 4th spare saves 0.68 of opex for 0.33 of setup |
| all, m = 2 and 3 | local search pass 2 | L02:SC:B4:C2 (move to L02) | 52,600 | - | 654.525 | 0.852 | accepted (-0.179), driven by seed 1 (632.51 vs 633.08) |
| all, m = 2 and 3 | local search pass 3 | L02:SC:B4:C3 (C+1) | 53,000 | - | 654.607 | 0.852 | rejected: opex identical, +0.082 setup (3rd charger worthless) |
| all, m = 2 and 3 | local search pass 3 | L02:SC:B5:C2 (B+1) | 53,050 | - | 654.857 | 0.852 | rejected: opex identical, +0.332 setup (5th spare worthless) |
| all, m = 2 and 3 | local search pass 3 | L05:SC:B4:C2 (move to L05) | 52,600 | - | 654.825 | 0.852 | rejected (+0.30) |
| SC_only, S_C_SC | local search pass 3 | + L06:SC:B1:C1 / + L06:SC:B1:C2 | 103,450 / 103,850 | - | 666.927 / 667.009 | 0.852 | rejected: opex -0.04, setup +12.4 / +12.5 |
| S_SC | local search pass 3 | + L06:S:B1:C0 | 103,050 | - | 666.887 | 0.852 | rejected: opex unchanged, setup +12.36 |
| all | result m = 2, m = 3 | L02:SC:B4:C2 | 52,600 | - | 654.525 | 0.852 | search complete; same at both budgets because no second site improves V |

The local search is identical at m = 2 and m = 3 (the frontier holds only the singleton, so the one-add
neighbourhood is the same) and identical across role sets except for the fifth screened neighbour of pass 3;
the per-budget history has 11 entries (start, one re-read cached neighbour and the accepted move in pass 1,
one candidate and the accepted move in pass 2, five candidates in pass 3). In the local search the screen keeps
the five best neighbours overall (not per role), and hub neighbours of L02:SC:B4:C2 (baseline value about 1100
vs about 1019 for SC additions) never made that top five, so no hub was priced next to the final layout.

## Coverage

* Lower-level ILP: 84 solves = 28 distinct layouts x 3 scenarios (SC_only 17 layouts, S_SC +6, S_C_SC +5),
  all `OPTIMAL`, max MIP gap 9.2e-5, 0 `TIME_LIMIT`, 0 `ERROR`, 0 infeasible, 0 `LOW_SERVICE`, 0
  `SKIPPED_BUDGET`; runtime mean 28.4 s, median 25.5 s, min 11.9 s, max 66.0 s (sum 2,382.5 s); 0.49-0.81 M
  arcs per solve. Priced layouts per role set (`class_counts`): SC_only 17 OK, S_SC 22 OK, S_C_SC 27 OK (the
  later sets re-priced the shared layouts from the cache: `n_cache_hits` 5,838 in total, almost all baseline
  screen hits; `n_baseline_runs` 1,446).
* Wall budget: 5,227.7 s used of 7,200 s (87.1 min; SC_only done at 53.9 min, S_SC at 73.9 min, S_C_SC at
  87.1 min); `search_complete = True` for every row; `wall_exhausted = False`; solver time 2,382.5 s, arc-library
  build time 2,305.3 s.
* Not priced by the ILP (screened out or outside the neighbourhood): hubs with C = 4, hubs at L07-L12, hubs as
  neighbours of the final layout, S or SC singletons other than the five screened per role, and any layout with
  three open locations (the forward step stopped at one site, so no m = 3 layout with three sites was ever
  priced). The final layouts are therefore greedy + local-search values, not certified optima; the integrated
  bound for this budget is produced by `../sweep`, not here.

## Anomalies

1. Degenerate answer to the E9.3 question: the three role sets return the identical layout and value, so the
   role comparison is a statement about the priced moves (table above) rather than about different optima.
2. The chosen size B = 4 lies outside the forward-selection menu (SC: B in {1, 2, 3}); it was reached by the
   local search's size +1 move (allowed up to K = 8). An enumeration or integrated model restricted to the menu
   cannot return this layout, and a single site at B = 4 costs 52,600 USD, 450 USD above the m = 1 budget.
3. The five hub rows have byte-identical V (684.410) and opex because the hub is unused; ties were broken by
   layout key. Likewise L07:S:B1:C0 and L12:S:B1:C0 coincide (667.234): the one spare is used the same way.
4. `best_rejected` in the `forward_stop` record is L10:SC:B2:C2 (V 666.990), ranked by gain per investment
   dollar, while the lowest-V rejected addition is L10:SC:B2:C1 (V 666.908); cosmetic, the decision is unaffected.
5. Chargers and grid are nearly slack at the chosen site: 1.74 kWh purchased per window (C_elec 0.56 USD), a
   third charger has zero value, so the 4 kW group cap never binds; the family stresses initial stock, not
   charging, which is also why a charge-only hub cannot help within a 4 h window.
6. Local-search history (`ls_pass*` rows) is kept only in memory (`history_len` 11 per budget); the step table
   above was reconstructed from `../logs/roles.log` and the `lower_level` rows of `records.jsonl`.
7. L02 beats L01 by 0.18 USD per window (0.03 %) and L05 by 0.30 USD; the location choice among the three
   depots / busiest cells is at the level of the E8 "siting delta" (0.41 USD), i.e. essentially a tie.

## Interpretation

On `nyc4h_stress2` the planner's problem collapses to sizing one co-located site: one SC site at a busy cell
with 4 spares and 2 chargers serves 85 % of the 36 orders, and no second facility of any role recovers more than
1.1 USD per window of the remaining 160 USD of unserved-order penalty, because the unserved orders are lost to
bike time and energy (6 bikes, 4 h, q0 3-6 levels), not to the distance between the stock and the riders.
Charge-only hubs are worthless here for a structural reason: within a 4 h window the chosen site buys only
1.74 kWh, its third charger has zero marginal value, so there is no charging capacity to relocate, and the
transfer shuttles (20 USD fixed + 1 USD per battery) are never worth a single battery; the hub costs its allocated
F_hub = 29.19 USD plus 0.16 USD of chargers and nothing else, exactly as E3u found on the unstressed family.
Swap-only sites are dead stock on this family: with no transfers ever used, a swap-only site contributes only
its 1-3 initial spares, worth 0.18-1.02 USD per window, against 12.4-13.0 USD of allocated setup, so the
"S next to a charger" rule of the relaunch is necessary but not sufficient to make swap-only sites attractive.
Forcing co-location costs 0.00 USD and allowing hubs gains 0.00 USD, so for this family the role decision can be
removed from the upper level without loss, and the siting question reduces to the spare count (the 4th spare is
worth 0.68 USD of opex against 0.33 USD of allocated cost, the 5th 0.00 USD) and, at a 0.2-0.3 USD level, to the
cell. The budget is slack: 51,700 USD at m = 2 and 103,850 USD at m = 3 remain unspent, so the E9.2 Pareto curve
of this family is flat beyond one site, which is informative but means role separation must be studied on a
family where a second site is worth more than its allocated 12.8 USD (more bikes per site, longer windows, or
higher site productivity). The result is in-sample on three scenarios, every ILP value is an upper bound on the
written optimum, and layouts with three sites, C = 4 hubs and hubs next to the final layout were never priced;
within those limits the search is complete (no wall-budget skip, every solve optimal), and the sign of the
conclusion is robust because the gap between the best second site (-1.09 USD) and its setup (+12.4 USD) is an
order of magnitude.

## Figures

* `roles_map.png` -- the 12 candidates (lat/lon from `../candidates.csv`), the depots L01-L03, the greedy start
  L01 and the chosen site L02:SC:B4:C2.
* `roles_priced_moves.png` -- V of every layout priced by the ILP (28), grouped as singletons, local-search size
  and location moves, SC additions, swap-only additions and hub additions, with the setup / opex decomposition
  of each addition against its parent.
* `roles.png` -- V of the chosen layout per role set and budget (regenerated from `records.jsonl`).
* `roles_components.png` -- mean cost components (27)-(32) of the chosen layout per role set and budget.
