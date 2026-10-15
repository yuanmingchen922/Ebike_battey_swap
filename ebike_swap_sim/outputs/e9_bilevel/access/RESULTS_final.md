# E9.6 -- the planner-only access row [U4]: what it costs the operator (final)

Family `nyc4h_stress2` (6 bikes, 36 orders, H = 48 slots of 5 min, `q0 ~ U{3..6}` of 12, `P_j = 2.8 kW`, `usd_sunk` costs);
3 demand scenarios (seeds 0-2, `p_s = 1/3`); 12 Midtown candidates (`../candidates.csv`); algorithm (C) greedy + local
search with the access row in `repair` mode; budgets `m = 2, 3` (104,300 / 156,450 USD); variants `no_access`, `D = 8`
blocks (1.2 km), `D = 12` blocks (1.8 km). Run finished 2026-10-14 21:37 after 140.4 min (wall budget 120 min, see
coverage). Records: `records.jsonl` / `results.csv` in this folder; lower-level cache `../cache` (version `e9-2`).

Every ILP value below is an upper bound on the written E2 optimum: the lower-level libraries restrict reposition targets
to the open sites plus the depots (`reposition = open_sites`, E8 convention), and the R2.4 geometry caveat applies
(real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid). The first E9 attempt on
`nyc4h_stress` (8 bikes, archived under `../_first_attempt/`) is superseded by this run and is not used anywhere below.

## Summary

The access row [U4] -- every demand zone within `D` blocks of an open swap-capable site -- never pays for itself for
the operator: without it the greedy opens a single co-located site (`L02:SC:B4:C2`, V 654.5 USD per window, 52,600
USD invested) at both budgets, and with it the planner must open a second site (`L05:SC:B1:C1`, Rockefeller south) at
`D = 8` and `D = 12`, which costs +12.08 USD per window (+1.85 %) and +50,450 USD of investment while leaving the served
share unchanged at 0.852 and lowering the expected opex by only 0.28 USD. At `D = 8` the second site covers 8 of the 11
NTA demand zones (MN0202 needs L08, MN0701 needs L06, MN0801 is beyond 8 blocks of every candidate), and at `D = 12` the
same two-site layout covers all 11 zones, so the planner's requirement is met at 1.8 km but not at 1.2 km with two
sites. At `D = 8, m = 3` the repair added a third site (`L08:S:B1:C0`, Union Square) for MN0202 before the wall budget
cut the search (`search_complete = False`), giving V 678.9 (+24.38, +3.73 %) with MN0701 still uncovered and the
covering local search not run. The whole cost of access is the allocated fixed cost of the extra sites (12.36 USD per
window per site); the customer-to-site distance falls from 11.6 to 8.5 blocks (mean) and from 22 to 15 blocks (max),
which is the benefit the planner buys with it.

## Chosen layouts per budget and variant

| budget m | variant | layout | sites | investment USD | V | C_setup | opex (expected) | served share | transfers | stock-out slots | kWh bought | zones covered D8 / D12 | uncovered zones | mean / max blocks to site | search complete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | no_access | L02:SC:B4:C2 | 1 SC | 52,600 | 654.525 | 13.522 | 641.003 | 0.852 | 0 | 30.3 | 1.74 | 5 / 8 | (not required) | 11.65 / 22 | yes |
| 3 | no_access | L02:SC:B4:C2 | 1 SC | 52,600 | 654.525 | 13.522 | 641.003 | 0.852 | 0 | 30.3 | 1.74 | 5 / 8 | (not required) | 11.65 / 22 | yes |
| 2 | D = 8 | L02:SC:B4:C1 + L05:SC:B1:C1 | 2 SC | 103,050 | 666.605 | 25.884 | 640.721 | 0.852 | 0 | 59.7 | 1.76 | 8 / 11 | MN0202, MN0701, MN0801* | 8.52 / 15 | yes |
| 3 | D = 8 | L02:SC:B4:C2 + L05:SC:B1:C1 + L08:S:B1:C0 | 2 SC + 1 S | 153,900 | 678.906 | 38.328 | 640.578 | 0.852 | 0 | 55.7 | 1.39 | 9 / 11 | MN0701, MN0801* | 7.41 / 15 | **no** (wall budget) |
| 2 | D = 12 | L02:SC:B4:C1 + L05:SC:B1:C1 | 2 SC | 103,050 | 666.605 | 25.884 | 640.721 | 0.852 | 0 | 59.7 | 1.76 | 8 / 11 | none | 8.52 / 15 | yes |
| 3 | D = 12 | L02:SC:B4:C1 + L05:SC:B1:C1 | 2 SC | 103,050 | 666.605 | 25.884 | 640.721 | 0.852 | 0 | 59.7 | 1.76 | 8 / 11 | none | 8.52 / 15 | yes |

`*` MN0801 has an empty access set at `D = 8` (no candidate within 8 blocks of any of its customer nodes): it can never be
covered at that radius and is always listed. V = C_setup (window-allocated setup, E2 (27)) + expected OPEX over seeds
0-2; all three scenarios solved to OPTIMAL (gaps <= 8e-5) for every chosen layout; distances are grid (Manhattan) blocks
of 150 m from each of the 108 customer nodes (36 orders x 3 seeds) to the nearest open swap-capable site; "zones
covered" counts the 11 NTA zones with an open swap-capable site inside their `D`-block access set.

### The cost of access (V difference vs `no_access`, same budget)

| budget m | variant | delta V (USD / window) | delta V % | delta investment (USD) | delta C_setup | delta opex | delta served share | delta mean distance (blocks) |
|---|---|---|---|---|---|---|---|---|
| 2 | D = 8 | +12.080 | +1.85 % | +50,450 | +12.362 | -0.282 | 0 | -3.13 (11.65 -> 8.52) |
| 3 | D = 8 | +24.381 | +3.73 % | +101,300 | +24.806 | -0.425 | 0 | -4.24 (11.65 -> 7.41) |
| 2 | D = 12 | +12.080 | +1.85 % | +50,450 | +12.362 | -0.282 | 0 | -3.13 |
| 3 | D = 12 | +12.080 | +1.85 % | +50,450 | +12.362 | -0.282 | 0 | -3.13 |

The price of a covering site is its window-allocated fixed cost (`F_j` 12.03 + `bB` x B + `bC` x C: 12.44 USD for
`SC:B1:C1`, 12.36 for `S:B1:C0`; the 12.36 delta at m = 2 is 12.44 for L05 minus 0.08 for the charger removed at L02),
of which the operator recovers 0.28-0.43 USD through shorter rider detours; the extra spares are mostly idle (stock-out slots at the small site: 59.7 - 30.3 = 29 slots per window
on average), and the served share does not move because the 5-6 unserved orders per scenario are unserved for
energy / timing reasons that a second site 7-9 blocks away does not change.

### Candidates that enter only because of the access row

| candidate | label | role / size | enters in | zones it covers that the no_access layout does not | note |
|---|---|---|---|---|---|
| L05 | busiest cell 5 (W 46th-47th / 6th Ave, Rockefeller south) | SC, B1, C1 | every access variant (D 8 and D 12, m 2 and 3) | D 8: MN0402, MN0604, MN0802; D 12: MN0701, MN0801, MN0802 | best V among the covering adds (666.687 before re-sizing); the covering local search then trims L02 from C2 to C1 (-0.08 USD) |
| L08 | Union Square (landmark) | S, B1, C0 | D 8, m 3 only | MN0202 | accepted by the second repair round (678.906 vs 678.940 for `L08:SC:B1:C1`); L06 (the only candidate covering MN0701) was never priced because the wall budget expired |

L06 (W 55th-56th / 8th-9th Ave) is the only candidate inside MN0701's `D = 8` set. A fourth site is unaffordable at
m = 3 (153,900 + 50,450 > 156,450), so with L08 already open MN0701 could only be covered by replacing L08 or L05 with
L06, a move the repair's add / role-flip neighbourhood does not contain; and before L08 was accepted the wall budget
expired before any L06 option was priced. Hence at `D = 8` the search found no three-site layout covering all 10
coverable zones; the 11-zone requirement is infeasible at `D = 8` for every layout (MN0801), and the 10-zone question
would need the integrated model with hard [U4] rows.

### Zone coverage per variant (access sets from the plan; a zone is covered when one of its listed candidates is open as S / SC)

| zone | D 8 access set | D 12 access set | no_access layout (L02) at D 8 / D 12 | D 8 m 2 (L02, L05) | D 8 m 3 (L02, L05, L08) | D 12 m 2, 3 (L02, L05) |
|---|---|---|---|---|---|---|
| MN0202 | L08 | L02, L08 | no / yes | no | yes | yes |
| MN0401 | L01 L02 L07 L08 L11 L12 | + L03 L10 | yes / yes | yes | yes | yes |
| MN0402 | L01 L03 L05 L06 L07 L11 L12 | + L02 L04 L09 | no / yes | yes | yes | yes |
| MN0501 | L01 L02 L03 L07 L08 L09 L10 L12 | + L04 L05 | yes / yes | yes | yes | yes |
| MN0502 | L01-L07 L09 L10 L11 | + L12 | yes / yes | yes | yes | yes |
| MN0602 | L02 L08 L09 L10 | + L01 L03 L04 L07 L12 | yes / yes | yes | yes | yes |
| MN0603 | L01-L05 L09 L10 | + L07 L08 L12 | yes / yes | yes | yes | yes |
| MN0604 | L03 L04 L05 L09 L10 | + L02 L06 | no / yes | yes | yes | yes |
| MN0701 | L06 | L05 L06 L11 | no / no | no | no | yes |
| MN0801 | (none) | L04 L05 L06 L09 | no / no | no | no | yes |
| MN0802 | L04 L05 L06 | + L03 L09 | no / no | yes | yes | yes |
| covered | | | 5 / 8 | 8 | 9 | 11 |

## Greedy + local search, step by step

The three variants share the start stage and the forward stage exactly (the access row never restricts the search in
`repair` mode, so the priced layouts and the decisions are identical); they differ only after the local search of each
budget level, where the repair adds covering sites. The per-pass local-search history is not written to
`records.jsonl` (only `history_len` is), so the local-search and repair rows below are reconstructed from the
lower-level ILP rows of each variant block in solve order and from the `layout_chosen` rows; cache hits from the
concurrent `sweep` / `roles` runs (shared cache) are marked.

### Stage 1 -- start: best singleton by lower-level V (baseline screen keeps the 5 best singletons per role; only SC singletons survive the `s_needs_charge` rule and the 50 % served-share guard)

| order | layout | investment | V | served share | decision |
|---|---|---|---|---|---|
| 1 | L05:SC:B3:C2 | 52,150 | 655.171 | 0.852 | usable |
| 2 | L11:SC:B3:C2 | 52,150 | 658.540 | 0.843 | usable, worst singleton (Hell's Kitchen zone centre) |
| 3 | L08:SC:B3:C2 | 52,150 | 656.998 | 0.852 | usable |
| 4 | L01:SC:B3:C2 | 52,150 | **655.056** | 0.852 | **start** (best V; the baseline screen had ranked it 4th) |
| 5 | L05:SC:B2:C2 | 51,700 | 656.634 | 0.843 | usable |

### Stage 2 -- forward selection from L01:SC:B3:C2 (top-5 baseline-screened additions per added role, priced by the ILP; gain per USD = (V(parent) - V(child)) / added investment)

| order | addition | investment | V | gain per USD | why rejected |
|---|---|---|---|---|---|
| 6-10 | + L02 / L03 / L04 / L05 / L06 as charge-only hub C:C2 | 102,950 | 684.410 (all five identical) | -5.8e-4 | a hub adds `F_hub` 29.19 USD of allocated cost and no benefit: transfers are never used (0 in every scenario) |
| 11 | + L10:S:B3:C0 | 103,500 | 667.065 | -2.3e-4 | V rises by 12.0 |
| 12 | + L12:S:B2:C0 | 103,050 | 667.090 | -2.4e-4 | V rises |
| 13 | + L12:S:B3:C0 | 103,500 | 667.269 | -2.4e-4 | V rises |
| 14 | + L12:S:B1:C0 | 102,600 | 667.234 | -2.4e-4 | V rises |
| 15 | + L07:S:B1:C0 | 102,600 | 667.234 | -2.4e-4 | V rises (L07 is one block from L01) |
| 16 | + L10:SC:B2:C1 | 103,450 | 666.908 | -2.3e-4 | V rises (best SC addition) |
| 17 | + L10:SC:B2:C2 | 103,850 | 666.990 | -2.3e-4 | V rises; recorded as `best_rejected` (highest gain per USD, still negative) |
| 18 | + L10:SC:B3:C1 | 103,900 | 667.075 | -2.3e-4 | V rises |
| 19 | + L10:SC:B3:C2 | 104,300 | 667.169 | -2.3e-4 | V rises |
| 20 | + L12:SC:B2:C1 | 103,450 | 667.172 | -2.4e-4 | V rises |
| -- | forward_stop | | | | "no improving addition": every second site is worse by 11.9-29.4 USD; frontier = {L01:SC:B3:C2}; greedy layout for both budgets = L01:SC:B3:C2 |

### Stage 3 -- local search per budget (first improvement, moves add / drop / swap / role / size / exchange, top-5 by baseline screen per pass, at most 3 passes)

`no_access`, m = 2 (identical outcome at m = 3, all cache hits):

| pass | layout tried | V | decision |
|---|---|---|---|
| 1 | L01:SC:B4:C2 (size B +1) | 654.704 | accepted (-0.35) |
| 2 | L02:SC:B4:C2 (swap L01 -> L02, NoMad) | **654.525** | accepted (-0.18) |
| 3 | L02:SC:B4:C3 | 654.607 | rejected (+0.08: the third charger costs more than it saves) |
| 3 | L02:SC:B5:C2 | 654.857 | rejected (+0.33: fifth spare idle) |
| 3 | L05:SC:B4:C2 | 654.825 | rejected (+0.30) |
| 3 | L02:SC:B4:C2 + L06:S:B1:C0 | 666.887 | rejected (+12.4) |
| 3 | L02:SC:B4:C2 + L06:SC:B1:C1 | 666.927 | rejected (+12.4) |
| -- | result m = 2 and m = 3 | 654.525 | `L02:SC:B4:C2`, investment 52,600 (only 50 % of the m = 2 budget, 34 % of m = 3); `history_len` 11 per budget |

`D = 8`, m = 2: local search as above (cache hits) -> L02:SC:B4:C2, uncovered {MN0202, MN0402, MN0604, MN0701, MN0801,
MN0802}, 5 of them coverable; then repair:

| step | layout tried | coverable zones left | V | decision |
|---|---|---|---|---|
| repair 1 | L02:SC:B4:C2 + L06:S:B1:C0 (cache) | 2 (MN0202, MN0604) | 666.887 | usable |
| repair 1 | L02:SC:B4:C2 + L06:SC:B1:C1 (cache) | 2 | 666.927 | usable |
| repair 1 | L02:SC:B4:C2 + L06:SC:B1:C2 | 2 | 667.009 | usable |
| repair 1 | L02:SC:B4:C2 + L05:SC:B1:C1 | 2 (MN0202, MN0701) | **666.687** | **accepted** (fewest zones left tied at 2, then lowest V) |
| repair 1 | L02:SC:B4:C2 + L05:SC:B1:C2 | 2 | 666.763 | usable |
| repair 2 | -- | 2 | | `repair_stop`: no affordable covering move (850 USD left of the m = 2 budget; L08 / L06 need >= 50,450) |
| covering LS 1 | L02:SC:B4:C1 + L05:SC:B1:C1 (C -1 at L02) | 2 | **666.605** | accepted (-0.08), coverage floor kept |
| covering LS 2 | L02:SC:B4:C1 + L05:S:B1:C0 | 2 | 668.155 | rejected (+1.55; served share 0.843: the uncharged S site runs dry) |
| covering LS 2 | L02:SC:B4:C1 + L05:SC:B1:C0 | 2 | 668.155 | rejected (identical to the S variant: an SC object with C = 0 is an S object, 2 x 3 solves wasted) |
| covering LS 2 | L02:SC:B4:C1 + L05:SC:B1:C2 | 2 | 666.681 | rejected (+0.08) |
| covering LS 2 | L02:SC:B5:C1 + L05:SC:B1:C1 | 2 | 666.789 | rejected (+0.18) |
| -- | result m = 2 | | 666.605 | `L02:SC:B4:C1|L05:SC:B1:C1`, investment 103,050; uncovered MN0202, MN0701, MN0801; `history_len` 26 |

`D = 8`, m = 3: local search (cache) -> L02:SC:B4:C2; repair 1 as above (cache) -> L02:SC:B4:C2 + L05:SC:B1:C1; repair 2
with 53,400 USD left:

| step | layout tried | coverable zones left | V | decision |
|---|---|---|---|---|
| repair 2 | L02:SC:B4:C2 + L05:SC:B1:C1 + L08:S:B1:C0 | 1 (MN0701) | **678.906** | usable (best) |
| repair 2 | L02:SC:B4:C2 + L05:SC:B1:C1 + L08:SC:B1:C1 | 1 | 678.940 | usable |
| repair 2 | L02:SC:B4:C2 + L05:SC:B1:C1 + L08:SC:B1:C2 | 1 | -- | seed 0 hit the remaining wall time (TIME_LIMIT after 86 s, incumbent 1119.7 with served share 0, bound 705.7); seeds 1-2 `SKIPPED_BUDGET` |
| repair 2 | two further candidates (L06 / L08 options) | | -- | `SKIPPED_BUDGET` (wall budget exhausted at 119.2 min of 120) |
| -- | result m = 3 | | 678.906 | `L02:SC:B4:C2|L05:SC:B1:C1|L08:S:B1:C0` accepted as the best usable covering move; the repair loop, the covering local search (which at m = 2 trimmed L02 to C1) and the L06 option were not run; `search_complete = False`, `history_len` 23 |

`D = 12`, m = 2 and 3: every layout needed was already in the cache (0 new ILP solves in this block, 35 usable
cache-hit pricings): local search -> L02:SC:B4:C2 (uncovered MN0701, MN0801, MN0802, all three covered by L05 or L06);
repair 1 accepted L02:SC:B4:C2 + L05:SC:B1:C1 (0 zones left); covering local search -> L02:SC:B4:C1 + L05:SC:B1:C1
(666.605), passes 2-3 rejected the same size moves as at D = 8; at m = 3 the screened neighbours of the covering
layout were all cached 2-site size moves, so no third site was priced; `history_len` 25 per budget.

## Coverage

* Lower-level ILP: 112 new solves (111 OPTIMAL, 1 TIME_LIMIT = the partial seed-0 solve above), 0 errors, solver time
  3,900 s (65.0 min, mean 34.8 s per solve, max 185.2 s for `L02:SC:B4:C1|L05:SC:B1:C0` seed 0), library build time
  3,744 s; 2,088 baseline-policy screening runs (milliseconds each); 8,619 cache hits (both policies; the sweep and roles
  runs shared `../cache`). Per variant: `no_access` 27 layouts priced (81 solves, all OK); `D = 8` 37 OK + 3
  `SKIPPED_BUDGET` (31 new solves); `D = 12` 35 OK (0 new solves).
* Wall budget 7,200 s: exhausted at 119.2 min during the `D = 8, m = 3` repair; the run then continued on cache hits
  only and finished at 140.4 min. Status per row: `no_access` m 2 / 3 complete; `D = 8` m 2 complete, m 3
  **wall budget exhausted** (reported, not treated as infeasible); `D = 12` m 2 / 3 complete but conditional on the cache
  (any uncached neighbour would have been skipped).
* Gurobi: Threads 3, Seed 0, TimeLimit 300 s per lower-level solve (600 s with hubs), `OutputFlag 0`; every solve of a
  chosen layout reached OPTIMAL with gap <= 8.0e-5.
* Not run: the optional expected-share row [U5] (`--zeta` not set) and the integrated model with hard [U4] rows (only
  built when `--zeta` is given), so there is no exact benchmark of the access requirement in this folder; the exact
  E9.1 check (exhaustive = integrated at `L02:SC:B2:C1`, V 676.2, bound 668.0 on the validation sub-family) is the
  only certification of the search machinery.

## Anomalies

1. `D = 8, m = 3` is incomplete: the wall budget expired inside the second repair round; the accepted third site (L08)
   covers MN0202 but the L06 options for MN0701 were never priced, and the covering local search that at m = 2 removed
   one charger at L02 did not run, so the reported 678.906 is the first usable covering layout found, not the end of
   the repair-and-polish procedure. The 1 TIME_LIMIT row (`L02:SC:B4:C2|L05:SC:B1:C1|L08:SC:B1:C2`, seed 0, 86 s,
   incumbent 1119.7 = all orders dropped) is an artefact of the shrinking per-solve limit near the wall budget, not of
   the instance.
2. The chosen two-site layout (`L02:SC:B4:C1|L05:SC:B1:C1`, 666.605) is better than every two-site layout the forward
   stage priced (best 666.908, `L01:SC:B3:C2|L10:SC:B2:C1`): the baseline-policy screen never put an L05 addition in its
   top 5 (the baseline values L10 / L12 / hub additions higher), and the access repair found it only because coverage,
   not value, ranked the candidates. The forward stage's conclusion (no second site pays) is unaffected.
3. `SC:B1:C0` is admitted by the size menu as a role / size neighbour and is priced separately from the identical
   `S:B1:C0` (same investment, same V 668.155): 6 solves (4.5 min) were spent twice on the same facility; a canonical
   form (`SC` with `C = 0` -> `S`) in `Layout.key()` would remove this.
4. The access row is infeasible at `D = 8` for every layout: MN0801's access set is empty (`uncoverable_zones`), so the
   `D = 8` variants can at best cover 10 of 11 zones; the requirement as stated is satisfiable only at `D = 12`.
5. The `zones_covered` / distance columns are computed on the search seeds 0-2 (in-sample); seeds 3-4 are evaluated only
   by the cross sub-experiment, which was still running when this report was written and is not used here.
6. `D = 8` and `D = 12` return the same layout at m = 2 with different coverage (8 vs 11 zones): the first repair move is
   the same because L05 is the best-V covering candidate under both radii; the difference is only in what remains
   uncovered.

## Interpretation

On this family the operator's optimum is a single well-stocked co-located site in NoMad (L02, 4 spares, 2 chargers),
and the greedy's forward stage shows why: every second site, whatever its role or location, raises V by 12-30 USD per
window because its allocated fixed cost (12.4 USD for a small SC or S site, 29.2 USD for a hub) dwarfs the 0.1-0.4 USD
of rider detour it saves, and transfers are never used. The planner-only access row therefore buys coverage, not
operating efficiency: at both radii it forces the second site L05 (Rockefeller south), which cuts the mean
customer-to-site distance from 11.6 to 8.5 blocks (1.75 km to 1.28 km) and the maximum from 22 to 15 blocks, at a price of
+12.08 USD per window (+1.85 %) and +50,450 USD of investment, with the served share unchanged at 0.852. The row is not
a service-level lever here: the six unserved orders per scenario stay unserved with two or three sites, so a planner
who imposes [U4] to improve service would be disappointed, while one who imposes it for spatial equity (no zone farther
than 1.2-1.8 km from a swap point) gets exactly that for about 2 % of the operator's window cost per site. The radius
matters more than the budget: at `D = 12` two sites cover all 11 NTA zones and the third budget unit is left unspent,
whereas at `D = 8` MN0801 is unreachable from any candidate, MN0202 and MN0701 each have a single candidate (L08, L06)
in reach, and even the three-site layout the search accepted before the wall budget expired (L02 + L05 + L08, +24.4 USD,
+101,300 USD) still leaves MN0701 uncovered. The candidates that enter only because of the access row are L05 (always)
and L08 (Union Square, `D = 8, m = 3`); none of the zone-centre candidates (L10-L12) is ever chosen, because the
restaurant-cell sites already sit inside the busiest zones' access sets. Two caveats limit the strength of these
numbers: the `D = 8, m = 3` row is a truncated search (the L06 option and the covering polish were never priced), and
the integrated model with hard [U4] rows was not run, so the +12.1 / +24.4 USD are upper bounds on the true cost of
access for the search's layouts (every lower-level value is itself an upper bound on the written E2 optimum). A
follow-up that settles the `D = 8` question cheaply is to price the two layouts `L02 + L05 + L06` and `L02 + L06 + L08`
directly (6 solves) and, if the exact benchmark is wanted, to run the integrated model with [U4] at `D = 12, m = 2`
warm-started from `L02:SC:B4:C1|L05:SC:B1:C1`.

## Figures (regenerated from `records.jsonl`, `../candidates.csv` and the plan header of `../logs/access.log`; matplotlib Agg)

* `access.png` -- V per budget and variant, split into allocated setup and expected opex, with the investment of each chosen layout.
* `access_map.png` -- the 12 candidates (lat / lon of `candidates.csv` projected to metres) with the chosen sites per
  variant, coloured by role and sized by B, and the `D`-block Manhattan reach of each swap site in the 29-degree grid.
* `access_coverage.png` -- zones covered (of 11) at D 8 and D 12, and the mean / max customer-to-site distance.
* `access_search.png` -- the pricing trace of every newly solved layout per variant (singletons, forward additions,
  local search, repair, covering local search) against the chosen values.
