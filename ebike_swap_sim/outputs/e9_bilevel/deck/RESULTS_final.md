# E9.4 (final) -- the proposal deck's spin-and-adjust planner vs the bi-level layouts

Family `nyc4h_stress2` (6 bikes, 36 orders, H 48 slots of 5 min, `q0 ~ U{3..6}` of 12, `P_j 2.8 kW`, flat 4 kW grid group, `usd_sunk` costs); 3 demand scenarios (seeds 0, 1, 2, `p = 1/3`); 12 Midtown candidates `L01-L12` (`../candidates.csv`); budget unit 52,150 USD (`Fhat 50,000 + 3 bhat 450 + 2 chat 400`); lower-level reposition targets `open_sites` (open facility nodes + depots); Gurobi `Threads 3`, `TimeLimit 300 s`, `Seed 0`; wall budget 3600 s, used 572.6 s (9.5 min). Comparison values are the `layout_chosen` rows of `../sweep/records.jsonl` (greedy + local search and the integrated warm-started incumbent, sweep finished 21:30, after this run). The first attempt on family `nyc4h_stress` (`../_first_attempt/`) is superseded and not used here. The run's own `RESULTS.md` only compares `m = 1` because the sweep had not finished at 20:53; this file replaces it.

Every ILP value is an upper bound on the written E2 optimum (reposition moves only into open sites + depots; the E8 convention), for the deck layouts and for the bi-level layouts alike, so the regret is a difference of two upper bounds whose lower-level solves all ended `OPTIMAL` (gap 0, one row 2.7e-5).

## Summary

The deck heuristic (open the `k` sites with the most swaps under the baseline policy, size by swap demand, 3 iterations, no ILP during the search) spends the entire budget by construction and opens `k = m` co-located sites, whereas the bi-level search stops at one site at every budget because a second site adds nothing the coordinator cannot already do with 6 bikes and 36 orders. At `m = 1` the two planners pick the same size (`SC:B3:C2`) at neighbouring cells (deck `L01`, bi-level `L02`) and the regret is 0.68 USD per 4 h window (0.10 %); at `m = 2, 3, 4` the deck layouts cost 12.56, 25.53 and 38.78 USD more per window (1.92 %, 3.90 %, 5.93 %), almost exactly their extra annualised setup charge (13.0, 26.5, 39.9 USD), while their expected opex is 0.5-1.1 USD lower than the bi-level layout's. Served share (0.852), lateness (1.67 orders) and unserved penalty (160 USD) are identical for every deck and bi-level layout under the ILP, so on this family the budget buys sunk cost, not service. The deck layouts share `L02` with the bi-level layout at `m >= 2` (0 of 1 sites shared at `m = 1`, 1 of 2-4 afterwards); the deck's ranking of sites is driven by a demand proxy of 0-1.67 swaps per scenario with ties broken by candidate order, which is why `L01` (92 restaurants) beats `L02` (72) although the ILP prefers `L02`. Priced by the baseline policy itself the same deck layouts cost 1025-1072 USD per window, 34-39 % more than under the ILP, and the policy ranks `m = 2` best while the ILP ranks `m = 1` best, the asymmetry anticipated in the design note (the ILP absorbs siting, the policy does not).

## Chosen layouts per budget

Deck (D) vs bi-level greedy + local search (C) of the sweep; the integrated model (A) ended `TIME_LIMIT` at every budget with its warm-start incumbent equal to the greedy layout and no usable bound (`-inf` at `m = 1`, `-12,548.6` at `m = 2..4`), so "bi-level V" below is the greedy + LS value, which is also the integrated incumbent.

| budget m (USD) | planner | layout (location:role:B spares:C chargers) | sites | investment USD | C_setup / window | expected opex | V = opex + setup | served share | n_late | transfers | ILP statuses (gaps) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 (52,150) | deck | `L01:SC:B3:C2` | 1 | 52,150 | 13.19 | 641.87 | **655.06** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 0) |
| 1 (52,150) | bi-level (C = A incumbent) | `L02:SC:B3:C2` | 1 | 52,150 | 13.19 | 641.19 | **654.38** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 0) |
| 2 (104,300) | deck | `L01:SC:B3:C1 \| L02:SC:B4:C1` | 2 | 103,950 | 26.55 | 640.54 | **667.08** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 0) |
| 2 (104,300) | bi-level | `L02:SC:B4:C2` | 1 | 52,600 | 13.52 | 641.00 | **654.53** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 0) |
| 3 (156,450) | deck | `L01:SC:B4:C1 \| L02:SC:B4:C1 \| L04:SC:B3:C1` | 3 | 156,150 | 39.99 | 640.07 | **680.06** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 2.7e-5) |
| 3 (156,450) | bi-level | `L02:SC:B4:C2` | 1 | 52,600 | 13.52 | 641.00 | **654.53** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 0) |
| 4 (208,600) | deck | `L01:SC:B4:C1 \| L02:SC:B5:C1 \| L04:SC:B3:C1 \| L06:SC:B3:C1` | 4 | 208,350 | 53.43 | 639.88 | **693.31** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 0) |
| 4 (208,600) | bi-level | `L02:SC:B4:C2` | 1 | 52,600 | 13.52 | 641.00 | **654.53** | 0.852 | 1.67 | 0 | OPTIMAL x3 (0, 0, 0) |

Per-scenario opex (seeds 0 / 1 / 2): deck `m = 1` 669.48 / 633.26 / 622.86; bi-level `m = 1` 668.00 / 632.69 / 622.87; deck `m = 4` 666.37 / 631.76 / 621.52; bi-level `m >= 2` 667.82 / 632.51 / 622.68. kWh purchased falls with the deck's site count (2.46, 1.33, 0.52, 0.00 kWh at `m = 1..4`) and stock-out slots from 30 to 0, i.e. the extra spares do replace charging, but charging costs only 0.79 USD per window at `m = 1`, so there is nothing to save.

## Regret, overlap and iterations per budget

| budget m | deck layout | deck V (ILP) | bi-level V (ILP) | regret USD / window | regret % | extra setup of deck (USD / window) | shared locations | deck sites / bi-level sites | deck iterations (converged?) | deck V under baseline policy | ILP-vs-policy gap % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `L01:SC:B3:C2` | 655.06 | 654.38 (`L02:SC:B3:C2`) | 0.68 | 0.10 | 0.00 | 0 (`L01` vs `L02`) | 1 / 1 | 2 (yes, fixed point at iteration 2) | 1072.25 | 38.9 |
| 2 | `L01:SC:B3:C1 \| L02:SC:B4:C1` | 667.08 | 654.53 (`L02:SC:B4:C2`) | 12.56 | 1.92 | 13.03 | 1 (`L02`) | 2 / 1 | 3 (yes, fixed point at iteration 3) | 1025.28 | 34.9 |
| 3 | `L01:SC:B4:C1 \| L02:SC:B4:C1 \| L04:SC:B3:C1` | 680.06 | 654.53 | 25.53 | 3.90 | 26.47 | 1 (`L02`) | 3 / 1 | 2 (yes, fixed point at iteration 2) | 1031.66 | 34.1 |
| 4 | `L01:SC:B4:C1 \| L02:SC:B5:C1 \| L04:SC:B3:C1 \| L06:SC:B3:C1` | 693.31 | 654.53 | 38.78 | 5.93 | 39.91 | 1 (`L02`) | 4 / 1 | 3 (yes, fixed point at iteration 3) | 1055.87 | 34.3 |

Regret = `V_deck - V_bilevel` on the same three scenarios; both values are `open_sites` upper bounds with all lower-level solves OPTIMAL, so the regret is exact up to the two gaps (at most 2.7e-5 relative on one scenario of `m = 3`). "Extra setup" is `C_setup(deck) - C_setup(bi-level)`; the regret minus the extra setup (-1.13 to +0.68 USD) is the opex difference. The percentage gap in the last column is `(V_policy - V_ILP) / V_policy` of the deck layout (the `gap_vs_baseline_pct` column of `results.csv`).

## Per-step table of the deck search (3 iterations max, baseline policy only)

Iteration 1 is identical for every budget: all 12 candidates open as `SC:B1:C1` (investment 610,200 USD), baseline policy V 1106.45; the demand proxy (expected swaps served at the site) is `L01 1.67, L02 1.67, L04 1.00, L06 1.00, L08 1.00, L11 1.00, L03 0.33, L05 0.33, L10 0.33, L12 0.33, L07 0.00, L09 0.00`. The 'unused station' replacement rule never fired (no kept site had zero swaps after iteration 1). Sizes: the leftover budget after `k` units goes to spares first (in proportion to demand, cap `K = 8`), then chargers one per site; with `k = m` the leftover is 1,300 USD at `m = 1` (2 spares + 1 charger) and 2,600 / 3,900 / 5,200 USD at `m = 2 / 3 / 4` (5 / 8 / 11 spares, 350 USD left, below one charger), which is why every multi-site deck layout keeps `C = 1` per site.

| budget m | iteration | layout evaluated (baseline policy) | policy V | demand proxy at the open sites (expected swaps) | kept (top-k by demand, ties by candidate order) | next layout (sizes) | investment | result |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | all 12 `SC:B1:C1` | 1106.45 | see above; `L01` = `L02` = 1.67, tie -> `L01` | `L01` | `L01:SC:B3:C2` | 52,150 | changed |
| 1 | 2 | `L01:SC:B3:C2` | 1072.25 | `L01 8.00` | `L01` | `L01:SC:B3:C2` | 52,150 | fixed point, stop (2 iterations) |
| 2 | 1 | all 12 `SC:B1:C1` | 1106.45 | see above | `L01, L02` | `L01:SC:B4:C1 \| L02:SC:B3:C1` | 103,950 | changed |
| 2 | 2 | `L01:SC:B4:C1 \| L02:SC:B3:C1` | 1025.28 | `L01 3.67, L02 5.00` | `L02, L01` | `L01:SC:B3:C1 \| L02:SC:B4:C1` | 103,950 | spares re-allocated to `L02` |
| 2 | 3 | `L01:SC:B3:C1 \| L02:SC:B4:C1` | 1025.28 | `L01 3.67, L02 5.00` | `L02, L01` | `L01:SC:B3:C1 \| L02:SC:B4:C1` | 103,950 | fixed point, stop (3 iterations) |
| 3 | 1 | all 12 `SC:B1:C1` | 1106.45 | see above | `L01, L02, L04` | `L01:SC:B4:C1 \| L02:SC:B4:C1 \| L04:SC:B3:C1` | 156,150 | changed |
| 3 | 2 | `L01:SC:B4:C1 \| L02:SC:B4:C1 \| L04:SC:B3:C1` | 1031.66 | `L01 3.00, L02 3.67, L04 1.67` | `L02, L01, L04` | same | 156,150 | fixed point, stop (2 iterations) |
| 4 | 1 | all 12 `SC:B1:C1` | 1106.45 | see above | `L01, L02, L04, L06` | `L01:SC:B5:C1 \| L02:SC:B4:C1 \| L04:SC:B3:C1 \| L06:SC:B3:C1` | 208,350 | changed |
| 4 | 2 | `L01:SC:B5:C1 \| L02:SC:B4:C1 \| L04:SC:B3:C1 \| L06:SC:B3:C1` | 1055.94 | `L01 2.00, L02 3.33, L04 1.67, L06 1.67` | `L02, L01, L04, L06` | `L01:SC:B4:C1 \| L02:SC:B5:C1 \| L04:SC:B3:C1 \| L06:SC:B3:C1` | 208,350 | one spare moved `L01 -> L02` |
| 4 | 3 | `L01:SC:B4:C1 \| L02:SC:B5:C1 \| L04:SC:B3:C1 \| L06:SC:B3:C1` | 1055.87 | `L01 2.00, L02 3.33, L04 1.67, L06 1.67` | `L02, L01, L04, L06` | same | 208,350 | fixed point, stop (3 iterations) |

## The bi-level search that produced the comparison values (from `../sweep/records.jsonl`)

| step | layout tried | ILP V | investment | outcome |
|---|---|---|---|---|
| singletons (k_screen 5 per role; the baseline screen kept only SC singletons as usable) | `L01:SC:B3:C2` 655.06, `L05:SC:B3:C2` 655.17, `L05:SC:B2:C2` 656.63, `L08:SC:B3:C2` 657.00, `L11:SC:B3:C2` 658.54 | - | 52,150 / 51,700 | 5 singletons priced, all OK (served 0.84-0.85) |
| start | `L01:SC:B3:C2` | 655.06 | 52,150 | best singleton by V |
| forward additions (16 priced) | `+ L02/L03/L04/L05/L06:C:B0:C2` 684.41-684.42; `+ L10:S:B3:C0` 667.06; `+ L12:S:B1/B2/B3:C0` 667.09-667.27; `+ L07:S:B1:C0` 667.23; `+ L10:SC:B2:C1` 666.91; `+ L10:SC:B2:C2` 666.99; `+ L10:SC:B3:C1/C2` 667.09 / 667.16; `+ L12:SC:B2:C1` 667.17 | all > 655.06 | 102,600-104,300 | forward_stop "no improving addition" (best rejected `+ L10:SC:B2:C2`, V 666.99); every second site raises V by 12-29 USD, its setup charge |
| local search, m = 1 | `L02:SC:B3:C2` (swap move `L01 -> L02`) | 654.38 | 52,150 | accepted, search complete |
| local search, m = 2, 3, 4 | `L02:SC:B4:C2` (size move `B 3 -> 4`, +450 USD) | 654.53 | 52,600 | accepted, search complete; note 654.53 > 654.38, the budget-2 local search started from the forward frontier, not from the budget-1 result, and did not revisit `B3` |

## Coverage

* Deck run: 4 budgets x (2-3 baseline iterations) = 10 baseline evaluations (27 policy runs, milliseconds each; 9 of them from the sweep cache), then one ILP and one baseline cross-evaluation of each final layout: 12 ILP scenario solves, 9 fresh (`n_solves 9`, 34.7 / 22.6 / 22.2 s at `m = 2`, 60.5 / 41.7 / 41.5 s at `m = 3`, 116.4 / 74.5 / 73.8 s at `m = 4`) and 3 cache hits (`m = 1`, `L01:SC:B3:C2` was priced by the sweep); `n_cache_hits 27` in total; `n_errors 0`.
* ILP statuses: 12 x OPTIMAL, 0 x TIME_LIMIT, 0 x SKIPPED_BUDGET, 0 x LOW_SERVICE, 0 x ERROR; gaps 0 except one 2.7e-5.
* Wall: 572.6 s of the 3600 s budget, `wall exhausted False`; the run finished at 20:53:35 and resumed nothing.
* Sweep side (comparison values): 87 ILP solves, 2871 cache hits, 1449 baseline runs, 29 priced layouts all OK, `wall_exhausted False`, `search_complete True` at every budget; integrated model `TIME_LIMIT` (600 s) at every budget with no usable bound.
* The cross run (`../cross/`) was still executing when this report was written and is not used.

## Anomalies and caveats

1. The deck planner's spare cap is the model bound `K = 8`, not the sweep's forward size menu (`SC: B <= 3`), so it reaches `B4` and `B5`; the bi-level local search also leaves the menu through unit size moves (`spec.valid_sizes`, hence `L02:SC:B4:C2`). The option sets therefore differ slightly, in the deck's favour; the regret is not inflated by this.
2. At `m = 2..4` the bi-level value (654.53, `B4`) is 0.15 USD above the `m = 1` value (654.38, `B3`): the greedy's local search at the larger budgets accepted the `B 3 -> 4` size move from the forward frontier (its starting point differs from the budget-1 local optimum), so the sweep's per-budget values are not monotone. The regret at `m >= 2` would be 0.15 USD larger against the `m = 1` layout; immaterial at the 12-39 USD scale.
3. The integrated model (A) gives no certificate: `TIME_LIMIT` with bound `-inf` (`m = 1`) and `-12,548.6` (`m = 2..4`); "integrated" in the figures and tables is its warm-start incumbent, identical to the greedy layout. The deck's regret is therefore measured against a heuristic value, not a proven optimum; E9.1 (4 candidates, 2 seeds) is the only exact check of the greedy's class of layouts (exhaustive = integrated at `L02:SC:B2:C1`, V 676.2).
4. The deck's demand proxy is tiny (0-1.67 expected swaps per site with 12 sites open; 36 orders and 6 bikes make about 8 swaps per scenario in total) and ties are broken by candidate order; the `L01` vs `L02` choice at `m = 1` is such a tie. With more scenarios the ranking would likely change; the 0.68 USD regret at `m = 1` is within the between-layout noise of the family (the five SC singletons priced by the sweep span 655.06-658.54).
5. The run's own `RESULTS.md` (20:53) lists overlap / regret only for `m = 1` (the sweep had finished `m = 1` only); it also labels the figure's `integrated` group with the greedy value. This file and the `_final` figures supersede it.
6. Both planners price with `open_sites` reposition targets; the E9.1 validation used `all_candidates`. The E9.1 value of `L02:SC:B2:C1` on seeds 0-1 (676.2) is not comparable with the three-seed values here.
7. Served share is 0.852 for every ILP-priced layout (deck or bi-level, 1-4 sites), i.e. 16 of 108 scenario-orders are never served (unserved penalty 160 USD per window in every row): with 6 bikes and `q0 ~ U{3..6}` of 12 the lost orders are a fleet / initial-charge limit, not a siting limit, which is why the budget cannot buy service on this family.

## Interpretation

The experiment asks how far the proposal deck's planner, which never consults the coordinator's optimisation, lands from the bi-level layout, and the answer on `nyc4h_stress2` is: as far as the money it spends. At one unit of budget the two planners agree on the role and size (`SC`, three spares, two chargers) and disagree only on which of two adjacent Midtown cells to use, which costs 0.68 USD per window, 0.1 %. From two units upwards the deck opens a site per unit because "number of affordable sites" is its first decision, and every additional site is a sunk charge of about 13 USD per window for which the ILP finds no operational use: expected opex falls by at most 1.1 USD (electricity and travel) while served share, lateness and the unserved penalty do not move at all. The bi-level search sees this directly, prices sixteen second-site additions in the forward pass, rejects every one of them by 12-29 USD, and returns a single site at every budget; its regret curve for the deck therefore grows linearly with the budget, 1.9 %, 3.9 %, 5.9 %. The deck's site choices are not unreasonable in themselves: `L01`, `L02`, `L04`, `L06` are the restaurant-dense cells and `L02` is exactly the bi-level site, but the ranking rests on a proxy of one or two swaps per site per scenario with order-of-candidates tie-breaking, and its sizing rule spends the leftover on spares before chargers, leaving one charger per site where the bi-level prefers two. The same layouts priced by the baseline policy tell the opposite story: the policy pays 34-39 % more than the ILP on every layout and prefers the two-site layout over the single site, so a planner that evaluates designs with the myopic policy will systematically over-build relative to what an optimising coordinator needs, which is the asymmetry the design note predicted. Two caveats bound the claim: the bi-level values are heuristic incumbents without an integrated certificate (the stochastic ILP hit its time limit with a useless bound), and all values are upper bounds under the `open_sites` reposition convention, though every lower-level solve was optimal so the regrets themselves are exact differences. The practical reading for the supervisor is that on a 6-bike, 36-order window one well-placed co-located station is the whole answer, the siting question only becomes interesting when the fleet or the demand is large enough that a second station changes who gets served, and the E9.6 access variants (coverage of all 12 zones) are where multi-site layouts are forced rather than chosen.

## Figures

* `deck_vs_bilevel_final.png` -- (a) V split into expected opex and setup charge for deck vs bi-level per budget, (b) regret in USD and %, (c) the deck layout priced by the ILP vs by the baseline policy.
* `map_deck_vs_bilevel.png` -- candidate map (WGS84 from `../candidates.csv`) with the deck sites (orange), the bi-level site (blue) and the shared site (ringed) per budget, with sizes.
* `deck_demand_proxy.png` -- the deck's iteration-1 demand proxy (expected swaps per candidate with all 12 open) that decides the site ranking, with restaurant counts.
* `deck_vs_bilevel.png` -- the run's original bar chart (20:53, `m = 1` comparison only), kept for provenance.

Data: `records.jsonl` (4 `layout_chosen` rows with the per-iteration `log`, 27 `lower_level` rows), `results.csv` (same, flattened), `wall_time.json`; comparison rows in `../sweep/records.jsonl` (`layout_chosen`, methods `greedy_ls` and `integrated`, `greedy_step` rows for the search table).
