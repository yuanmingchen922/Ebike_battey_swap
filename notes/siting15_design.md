# Siting study with about 15 open sites: consolidated plan (2026-10-28)

Supervisor request: a budget of at most three sites is too small; open about 15 sites, show them on the NYC map, and
explain why those sites were chosen. Author constraints: visible Manhattan map with the 15 sites, plain-language
interpretation per site or cluster, paper stays at 10 pages, AWS cost estimated before any run (October already at
about 64 USD against the 50 USD line; exceedable with approval). This note consolidates three angle studies (demand
and solver scale, upper-level search, map and interpretation). All probes were run on the laptop within the toy limits;
no project file and no paper file was changed; the EC2 instance is stopped and only the user starts it.

Sources: `outputs/r7_prod_final/RESULTS_final.md`, `outputs/r7_prod_final/r7_siting/{records.jsonl, cache/index.jsonl}`,
`notes/siting_scaleup_design.md`, `siting_production_plan.md`, `siting_production_replan_m1.md`, `DECISIONS.md`,
`notes/dot_candidate_sites.md`; code `ebike_swap_sim/{arcs,aggregate,ilp,baseline,bilevel,benders,rolling,evaluate,
sites_nyc,generator,data_nyc}.py`, `experiments/r7_search.py`, `paper_itsc/figs/src/make_figs.py`,
`outputs/r7_prod_final/figs/final_map.py`. Probe scripts live in the session scratchpad
(`scale_probe.py`, `search_probe/probe_a_toy.py`, `search_probe/probe_b_reduced.py`, `map15/map15_prototype.py`).

---

## 0. The plan in one page

| item | decision | one-line reason |
|---|---|---|
| Fleet / demand | **48 riders, 240 orders per 16:00-20:00 evening** (6 x the 8/40 case; demand levels 192/240/288; same 6 entry depots, 8 riders each; same restaurant + ACS demand model) | 15 sites are busy only at about 90 swaps per evening; one SC:B3:C2 site does 6-7 swaps per evening at capacity, riders swap about 1.5 times per evening |
| Sites | **exactly 15 open sites**, each one unit SC:B3:C2 (782,250 USD capital), sizes polished at the end from the reduced SC menu | with "at most 15" the planner opens a few sites and buys spares (the production third unit bought batteries); 15 is a policy target and is shown on a V(k) curve |
| Lower level | **rule-based rider module** (`baseline.run_baseline`, variant r2), every schedule certified by `evaluate.check` | the only follower that scales (seconds per evening); the exact ILP has a 94 % gap after 240 s already at 8 riders / 80 orders / 15 sites |
| Prerequisite code | **union (bike-class) arc library** with per-bike views, plus `force_k` search mode, per-policy service gate, library-free proxy screen, per-site metrics | today's per-bike library would be 170 M arcs = 60 GB per evening at 48 riders; the union network is 3.5-4.5 M arcs = 2 GB |
| Upper level | three warm starts (CSCD-15, CSAV-15, greedy from the m=2 incumbent) + k-median-15 and DOT-first as comparison rows; forward selection to 15 with proxy screen, 3 priced per step; swap local search at fixed k; size polish | no certificate possible (4e13 location sets); the V(k) curve and regret against rule layouts are the honest output |
| Scenarios | 6 stratified scenarios during the search, 12 for the final table, 12 held-out | cells are cheap under the rule follower; stratified CIs as in production |
| Map | vector figure built offline on the laptop: NTA land + OSM major streets (cached extract) + restaurant density + 15 numbered sites + entry depots + uncovered land; 15-row companion table | prototype renders in 0.6 s; raster tile servers need API keys; interpretation needs per-site statistics logged by the run |
| Cost | **Plan A about 8 h = 9 USD** on the r7i.4xlarge on-demand (range 6-11 USD), plus 3-4 laptop days of coding; the figure is free | Option B (no union library, 24 riders / 120 orders) about 11 USD on-demand or about 5 USD on a Spot r7i.8xlarge, weaker story |
| Paper | new Fig. 4 (15-site map) + 15-row table + a 15-site subsection; delete Figs. 5 and 6 and fold their content into text | keeps 10 pages |

---

## 1. Fleet and demand: why 15 sites pay only at a larger fleet

Evidence from the production cache (12 scenarios, p-weighted) and the DOT pilot:

| fact | number | source |
|---|---|---|
| swaps per evening at one open SC:B3:C2 site (D23 alone) | 6.83, served 78 % | cache, open-sites tier |
| swaps at the best pair D07 + D45 | 5.69 + 6.36 = 12.05, served 98.5 % | cache |
| physical capacity of a B3:C2 site per 4 h window | about 7 recharged swaps (3 spares + 2 chargers x 4 h / 1.8 h per battery) | cost model |
| swaps per rider per evening | about 1.5 (12.05 / 8) | cache |
| DOT 2024 pilot | 12,100 swaps / 184 days / 5 sites = 13 per site per day, about 4-5 in a dinner window | `notes/dot_candidate_sites.md` |

So the open sites already run near capacity at 8 riders, which is why a third unit bought spares instead of a site.
Fifteen busy sites need about 75-100 swaps per evening, i.e. 50-65 riders and 250-330 orders.

**Chosen: 48 riders / 240 orders** (exactly 6 x 8/40, so every existing number scales by a stated factor). Stratified
demand levels 0.8 / 1.0 / 1.2 give 192 / 240 / 288 orders; weekday/weekend profiles as today; riders start at the same
six bridge/tunnel depots (8 per depot). `n_bikes` and `n_orders` are existing overrides of `make_base_instance`; the
demand model (DOHMH restaurants + ACS profiles over the whole band south of 110th St) does not change. Expected
utilisation at 15 sites: about 70 swaps per evening / 15 sites = 4-5 swaps per site, i.e. 60-70 % of capacity, which
is also the DOT pilot's level. Optional sensitivity 64 riders / 320 orders (only with the union library; may need the
pickup-radius pruning of section 2).

**Site count: exactly 15**, 15 units budget, every site one SC:B3:C2 unit in the search, sizes freed in the final
polish (SC menu B in {2,3,4} x C in {1,2}; S and C roles stay admissible but are expected not to appear, as in
production). The greedy path gives V(k) for k = 1..20 for free, so "15" is placed on a cost curve and the paper can say
what the marginal site costs or saves at this fleet.

## 2. Lower-level solver: what is feasible at 48 riders / 240 orders / 15 sites

Measured scaling (laptop probes, nice -n 15, Threads 1):

| lower level | per-evening cost at 48 / 240 / 15 open sites (server factors 1.9x Python, 2.1x LP, 1.5x ILP applied) | verdict |
|---|---|---|
| exact aggregated ILP | 3-4 M integer columns; already 757 k columns and a 94 % gap after 240 s at 8 riders / 80 orders / 15 sites | not feasible |
| LP relaxation, all 59 candidates open | 10-12 M columns, 10-20 min and 15-25 GB per scenario; bound is for the exact follower, 40-60 % below any rule-follower value | optional context only, not planned |
| rolling horizon (`rolling.py`) | 48 bikes x 130 k arcs = 6 M binaries per window; not wired into the evaluator's policies | not feasible |
| **rule-based module** (`baseline.run_baseline`) | simulation 1-3 s; the per-layout arc library is the cost: 170 M arcs / 60 GB / 10-12 min with today's per-bike library, **3.5-4.5 M arcs / 1.5-2 GB / 20-30 s with a union library** | **chosen**, with the union library |

Why the library dominates: today `ArcLibrary` stores one `Arc` per bike, so memory = riders x union network; per-bike
arcs grow about linearly in riders and as orders^1.9 (82 k / 296 k / 697 k delivery arcs per bike at 40 / 80 / 120
orders; 1.86 M -> 8.32 M total arcs for 2x bikes and 2x orders at 6 candidates). The union network is fleet-independent
and 6-10x smaller (184 k vs 1.86 M at N=6/40; 1.55 M vs 3.66 M at N=20/120 with 2 bikes), and every probe had a single
closed commodity (`agg_mode = single`), as in production.

**Prerequisite code change (laptop, no AWS cost, 2-3 days):** `UnionArcLibrary` stores the bike-independent arcs once
(the `_template_specs` already exist in `arcs.py`), keeps one reachable-state set per bike class (source state (depot,
q0): at most 6 x 7 = 42 classes), and materialises per-bike `Arc` views on demand with virtual ids. The baseline uses
only `find`, `out_arcs`, `source`, `gbar`, `options`, `has_dummy_terminal`; `evaluate` uses `arc`, `source`,
`delivery_arcs`, `arcs`; `aggregate` uses `arcs_of`, `out_arcs`, `source`, `arc`. Toy tests must reproduce
`build_arcs` arc sets and values exactly, so `evaluate.cost` / `check` certify every rule schedule as today and the
aggregated ILP/LP still build on it. Cache keys and all 8-rider results are untouched (new family name `manhattan15`).

Optional pruning: delivery arcs only from nodes within a pickup radius (about 20 blocks = 3 km) cuts the quadratic term
about 3x. It restricts the follower's arc set (allowed by the E8 convention), so it would apply to the whole 15-site
family and never be mixed with 8-rider numbers. Default: off at 48/240, on only if 64/320 is run.

**Rule variant:** r2 (the evaluator's default `BaselineParams()`: stock-aware site choice, demand-aware charging,
threshold swaps, no transfers), because the cache's `baseline_total` rows used it and the validation below is on r2.
One variant for every number in the study.

**Validation of the rule follower (what the paper can say):** from the existing cache (590 cells with both values),
rule / ILP cost ratio median 1.68 (p25 1.57, p75 1.81); layout ranking agrees with the ILP across the 11 priced pairs
(Spearman 0.92) but not across the 16 near-tied single sites (-0.38; all within 3 % under the ILP). Planned extra
check on the server (about 1.6 USD): 16 riders / 80 orders, 3 five-site layouts (greedy best, CSCD, CSAV) x 3
scenarios, exact aggregated ILP with 1,800 s cells; report ratio and rank agreement at that scale. The 15-site layout is
therefore a "best found under the rule-based follower" result and is labelled so.

## 3. Upper-level search and the number of evaluations

Existing `greedy_local_search` stops at "no improving addition" (toy probe: 2 sites with budget for 8) and its local
search drops sites (CSCD-6 warm start shrank to 3), and the `min_served_share = 0.5` gate discards every single-site
layout under the simulator (served 0.29-0.33). Three small changes in `bilevel.py` (about 150 lines) plus a `k15`
stage in `experiments/r7_search.py` (about 300 lines, records / cost rows / resume) and tests: `force_k` cardinality
mode (add/drop disabled at fixed k), per-policy service gate (0 for the simulator; served share reported instead),
library-free proxy score for ranking neighbours (p-weighted sum over orders of the grid distance from the restaurant
to the nearest open site, times the order penalty, plus set-up; milliseconds), restricted swap neighbourhood, and a
k-median-15 warm start (about 30 lines, one small MIP).

| step | what | pricings (layouts) | scenarios |
|---|---|---|---|
| 0 warm starts | CSCD-15, CSAV-15, k-median-15, DOT-first-15 (in-region pilot/PEC sites filled by CSCD), all SC:B3:C2 | 4 | 6 |
| 1 forward selection | from the m=2 incumbent D07 + D45 to 15 (13 steps), proxy ranks up to 57 additions, top 3 priced, best accepted even if V rises; records V(k) | 39 | 6 |
| 1' forward selection from the two rule warm starts' best 2 and from empty | same procedure, gives independent local optima (3 restarts in all) | 78 | 6 |
| 2 swap local search at k = 15 | neighbourhood: 3 nearest closed candidates of each open site + 5 best closed by proxy; about 120 swaps + 60 size moves per pass, proxy-ranked, 3 priced, first improvement, up to 5 passes, per restart | 45 | 6 |
| 3 size polish | D'Hondt sizes and +-1 size moves at the best layout, 3 priced | 3 | 6 |
| 4 final table | best of each restart, each rule layout, polished incumbent (about 8 layouts) | 8 | 12 + 12 held-out |
| 5 V(k) curve beyond 15 | continue forward selection to k = 20 | 15 | 6 |
| 6 remove-one pass | 15 layouts with one site removed (marginal value per site for the interpretation) | 15 | 12 |

About 200 priced layouts at 6 scenarios (1,200 cells) + 8 x 24 + 15 x 12 = 372 cells: **about 1,600 lower-level cells**,
plus about 8,000 proxy evaluations (seconds). At 25-30 s per cell with the union library and 8 one-thread workers
(utilisation 0.9), the search is about 1.5-2 h of wall time. If the proxy mis-ranks and the simulator must screen a
restricted neighbourhood instead (S_screen = 2), add about 2 h.

Comparison rows in the paper: CSCD-15, CSTC-15, CSAV-15, k-median-15, DOT-first-15, and "15 units free" (greedy
without `force_k`, which shows what the budget reading would do), each with the paired stratified 95 % CI against the
best found.

## 4. Scenarios

12 stratified in-sample scenarios (6 strata = 3 demand levels x weekday/weekend, 2 seeds, p_s as today) and 12
held-out scenarios of the same design. The search uses the 6-scenario subset (one seed per stratum,
`lp_scenario_subset`); every candidate layout that enters the final table is re-priced on all 12 and on the 12
held-out. Cells are cheap under the rule follower, so S = 12 for the final table costs nothing noticeable; raising S to
15 would only change the final-table cost (+25 %) and is not needed.

## 5. What is reported honestly instead of a bound

* No certificate: C(59,15) = 4.0e13 location sets (1.9e25 with sizes); the only LP bound valid for every layout is the
  all-candidates root LP, which took 2.6 h and 14 GB per scenario at 8 riders and collapses to "L + cheapest set-up" at
  m = 15; at a larger fleet it does not solve in budget. The paper says so in one sentence.
* Reported: best-found layout at k = 15 (map + table); V(k) for k = 1..20 (k = 1, 2 from the certified / incumbent
  production values, scaled fleet noted); regret of each rule layout against the best found with paired stratified
  CIs; in-sample vs held-out values; served share and cost components per layout; the rule / ILP ratio and rank
  agreement from section 2 as the statement of what the follower is worth.
* Near-ties: 11 single sites were within 3 % at m = 1 and pair CIs were +-10 USD, so many 15-site swaps will fall
  inside the CI. The interpretation is by cluster/zone, not by exact corner, and the text says so.
* Optional (0.8 USD, context only): root LP at 48 riders on the union library, reported as "exact-follower lower
  bound" with the caveat that the rule follower sits 1.5-1.8x above it.

## 6. Map and interpretation

**Figure** (figure*, full text width 7.16 x about 2.55 in, replaces the current Fig. 4; same rotated frame as
`make_figs.fig_map`, north to the right). Layers bottom to top: (1) Manhattan NTA land (`data/raw/nycnhood_acs.geojson`,
existing filters); (2) restaurant density of the 11,377 DOHMH restaurants in the band, 75 m bins, Gaussian smoothing,
single-hue warm ramp #f4f3f0 -> #a85c14, clipped to land; (3) OSM major streets (motorway/trunk/primary/secondary/
tertiary, 6,230 ways, cached extract `data/raw/osm_major_roads_manhattan.json`, 5.3 MB or thinned to 2 MB) as two
LineCollections, plus the existing dashed 14th/34th/59th/96th St guides; (4) hatched land beyond 14 blocks of every
open site (with 15 sites the access diamonds cover about 86 % of the land, so the uncovered remainder is the
informative layer; Roosevelt Island masked); (5) 44 unchosen candidates as light-grey dots, six entry depots as
dark-grey stars; (6) the 15 sites: marker shape = candidate class (square PEC, circle pilot, pentagon cabinet,
triangle Citi Bike dock, hexagon depot, X other, diamond grid cell), blue #2a78d6, marker size = swaps per evening
from the run, red #d03b3b ring on DOT programme sites, numbers 1-15 with white halo and leader lines for the close
pairs (D23/D24/D25 within 300 m, D28/D29 within 200 m); (7) scale bar, north arrow, legend with the layout's cost.
Caption credits "streets: OpenStreetMap contributors, ODbL" and names the lower level. Raster tiles are off the table
(Carto returns an API-key watermark, Stadia 401, tile.openstreetmap.org is policy-limited and busy); contextily /
geopandas are not installed and not needed. Prototype: `scratchpad/map15/map15_prototype.py`, 0.6 s per map, PDF
650 kB; it moves to `paper_itsc/figs/src/make_figs.py` as `fig_map15` and also emits `figs/site_table.tex`.

**Companion table** (15 rows, scriptsize, ordered south -> north as on the map): No. | site (short name, class, DOT
yes/no) | NTA | size B:C | restaurants within 1 km (and % of the band) | km to nearest entry depot | swaps per evening
(mean, 95 % CI) | orders served with pick-up within 1 km | charger busy share | kWh bought | marginal value (cost
change if the site is removed, from the remove-one pass). Columns 1-6 are computable now from `candidates.csv` and
`dohmh_restaurants.csv`; the rest come from the run.

**Per-site statistics the run must log** (small addition to `evaluate.metric_pack` / the analyse stage before launch;
output `outputs/<run>/site_stats.csv` and `layout.json`): swaps per site (exists), served orders whose restaurant is
within 1 km of the site (new join), distinct riders and their entry depot per site (from swap arcs), idle share of
15-min slots (from `sbur` / `swaps_per_slot`, exist), kWh per site (one dict addition), mean wait before swap
(exists), stock-outs (exists). Schedules are kept, so a metrics re-pass is possible afterwards (about 1 server hour).

**Interpretation template**, one sentence per site or cluster: "Site k (<name>, <class>, DOT: yes/no) in <NTA>: <n>
restaurants within 1 km (<p> % of the band), <d> km from the <entry> approach; makes <S> swaps per evening [CI] and
serves <o> orders nearby; chargers busy <u> % of the evening; removing it costs <delta> USD/day." Clusters expected
from the density layer: Chinatown / Lower Manhattan near the Brooklyn, Manhattan and Williamsburg Bridge approaches;
East/West Village to Union Square; the Midtown core 34th-59th (MN17 alone holds 2,308 restaurants); northern coverage
sites on the Upper East / Upper West Side (few restaurants, chosen for reach). Each cluster is explained by demand
share, rider entry points, DOT programme overlap (how many of the 15 are pilot/PEC sites), grid power (docks and
depots are hub-capable), and the land left beyond reach. Low-swap sites under the myopic rule follower are called
coverage sites, not errors.

### 6.1 Input contract of `fig_map15` (L3, 2026-10-28; the driver lane logs exactly these fields)

Implemented in `paper_itsc/figs/src/make_figs.py`: `fig_map15(layout_json, site_stats_csv)` draws
`figs/fig_map15.{pdf,png}` (7.16 x 2.7 in, figure*) and writes `figs/site_table.tex` (table*, 15 rows south -> north);
`make_figs.py map15` reads `figs/map15/layout.json` + `figs/map15/site_stats.csv`, `make_figs.py map15_demo` renders the
DEMO (CSCD-15 from `bilevel.rule_layout`, synthetic statistics, inputs in `figs/map15_demo/`, stamped DEMO on the map,
in the legend title and in the table caption). The streets come from the cached extract
`data/raw/osm_major_roads_manhattan.json` (6,230 ways, 1.1 MB; (c) OpenStreetMap contributors, ODbL; the caption and the
map carry the credit; `osm_fetch_streets()` rebuilds it from Overpass only when the file is missing). The site numbers are
not an input: both the map and the table number the sites 1-15 by the along-avenue coordinate (south -> north), so the
driver writes the sites in any order. Columns 1-6 of the table (name, class, DOT, NTA, restaurants within 1 km, km to
the nearest entry depot) are computed by the emitter from `candidates.csv`, `dohmh_restaurants.csv` and the NTA
polygons; the run supplies only `site_stats.csv`.

**`layout.json`** (one object, written by the R8 driver next to its records):

| key | type | meaning |
|---|---|---|
| `schema` | str | must be `"map15.layout/1"` |
| `label` | str | legend title, e.g. `"Best found, 15 sites"` |
| `demo` | bool | `false` for a run result; `true` stamps DEMO everywhere |
| `run`, `family`, `policy`, `variant`, `n_bikes`, `n_orders`, `n_scenarios` | str / int | provenance, printed as a comment in the table (`manhattan15`, `baseline`, `r2`, 48, 240, 12) |
| `V`, `V_ci95` | float, [lo, hi] | expected cost per day (USD) of the layout, stratified 95 % CI (legend title) |
| `served_share` | float | p-weighted share of orders served (legend title) |
| `investment_usd` | float | capital of the layout (15 x 52,150 at one SC:B3:C2 unit per site) |
| `candidates_csv` | str, optional | the run's `candidates.csv` (default: the r7 production file, ids D01-D59) |
| `depots` | list, optional | `[{"name", "lat", "lon"}]`; default `data_nyc.MANHATTAN_ENTRY_POINTS` (six bridges / tunnels) |
| `sites` | list of 15 | `{"id": "D23", "role": "SC", "B": 3, "C": 2, "name": optional short name}` |

**`site_stats.csv`** (one row per open site, header exactly these columns, blank = not measured -> `--` in the table;
`make_figs.SITE_STATS15_COLUMNS` is the authoritative list and unknown columns are rejected):

| column | meaning (p-weighted mean over the final 12 scenarios unless stated) |
|---|---|
| `id` | candidate id, must match `layout.sites` |
| `swaps_mean`, `swaps_lo`, `swaps_hi` | swaps per evening at the site and its stratified 95 % CI (marker size = `swaps_mean`; hollow marker when blank) |
| `orders_1km_served` | served orders whose restaurant lies within 1 km (grid distance) of the site |
| `orders_1km_total` | all orders with the restaurant within 1 km, served or not |
| `riders_distinct` | distinct riders that swapped at the site per evening |
| `charger_busy_share` | share of 15-min slots with a charger in use (0..1); table column "Busy %" |
| `idle_share` | share of 15-min slots with no swap and no charging (0..1) |
| `kwh_bought` | kWh purchased at the site per evening (`charge_steps_facility` x step energy) |
| `wait_min_mean` | mean wait before a swap, minutes |
| `stockout_slots` | slots per evening with no full battery on the shelf |
| `marginal_usd`, `marginal_lo`, `marginal_hi` | cost change per day when the site is removed (remove-one pass; positive = the site saves money) and its 95 % CI; table column "Removal USD/d" |
| `n_scenarios` | scenarios behind the row |

Table columns (13, scriptsize, fits the IEEEtran text width; checked by a test compile): No. | Site (id) | Class |
DOT | NTA | Size B:C | Rest. (% of band) | Entry km | Swaps +- CI | Orders <= 1 km | Busy % | kWh | Removal USD/d +- CI.
Map legibility rules applied: fonts >= 7 pt; every label placed by a collision-aware placer (numbers first, depot names
second; a site with a neighbour within 300 m always gets a leader line, leaders never cross another marker); markers
carry a white 2-pt ring and the DOT ring sits on a white under-ring, so the figure reads in greyscale (the density ramp's
dark end is lighter than the marker blue); the blue/red pair passes the dataviz validator all-pairs (CVD dE 23.8).

## 7. Stage table: hours and USD on the r7i.4xlarge (on-demand 1.0584 USD/h)

| stage | where | wall h | USD | notes |
|---|---|---|---|---|
| L1 union arc library + tests | laptop | 2-3 days | 0 | toy reproduction of `build_arcs` sets and values |
| L2 `force_k`, per-policy gate, proxy screen, k-median, `k15` stage, per-site metrics, tests | laptop | 1-1.5 days | 0 | no solves |
| L3 map script `fig_map15` + cached OSM extract + table emitter | laptop | 0.5 day | 0 | prototype exists |
| S1 start instance, pull code, size dry run (one layout, 12 scenarios at 48/240) | server | 0.5 | 0.5 | confirms 20-30 s per cell and about 2 GB per worker |
| S2 rule-follower validation (16 riders / 80 orders / 5 sites, 3 layouts x 3 scenarios, exact ILP 1,800 s cells) | server | 1.5 | 1.6 | 4 workers x 3 threads |
| S3 15-site search (about 1,600 cells, 8 workers) | server | 2-4 | 2-4 | +2 h if the simulator screen is needed |
| S4 final table, held-out, V(k) to 20, remove-one pass, metrics | server | 1 | 1 | |
| S5 optional root LP bound at 48/240 (12 LPs, 3 threads each) | server | 0.8 | 0.8 | context only; skip by default |
| contingency 25 % | | 1.5 | 1.5 | |
| **Plan A total** | | **about 8 h** | **about 9 USD** (6-11) | memory peak about 25 GB |

Spot: with the union library the job is small and CPU-light, so a larger instance buys nothing; a Spot r7i.4xlarge
(about 0.45 USD/h) would save 4-5 USD but needs the lane scripts re-tuned and risks interruption of a run that is
only 8 h long. Recommendation: on-demand 4xlarge for Plan A, watchdog stops it after the lanes. For Option B (section
10), which is memory-bound, a Spot r7i.8xlarge (256 GB, about 0.8 USD/h) is the cheaper machine.

The spend falls in November unless the author wants it in October on top of the 64 USD already spent.

## 8. What changes in the paper (10 pages kept)

| place | change |
|---|---|
| Sec. II framework table | state that the modular lower level is instantiated with the rule-based rider module for the 15-site study (follower r2), the exact ILP for the 1-3 site study |
| Sec. VI results, new subsection "Fifteen sites at a city-scale fleet" (about 0.6 column) | fleet scaling argument (5 lines), best-found layout, V(k) curve as a short table or one sentence, regret rows, rule-follower validation sentence, the no-certificate sentence |
| Fig. 4 (map) | replaced by the 15-site map (figure*, 7.16 x 2.7 in nominal, 7.2 x 2.74 in as built); the current pair D07 + D45 is kept as two marked markers or mentioned in the caption |
| new Table (15 rows, scriptsize, about a third of a column) | companion table of section 6 |
| Fig. 5 one-site corridor dot plot and Fig. 6 budget bars | deleted; their content becomes one short paragraph each ("11 sites within 3 %" and "a third unit buys batteries"); Table tab:bounds gains a 15-site row marked "best found, no bound (rule follower)": the root LP (S5) is off by default and the lane chain has no LP stage, so the row carries the best-found value only (fixer, 2026-10-28; the optional LP lane, 0.8 USD, would add a valid but loose bound, section 12.3) |
| Fig. 7 cost bars | gains a 15-site bar |
| Sec. VI-C hubs | shortened to one paragraph if still over; regret column of tab:regret dropped as the last resort |
| Sec. VII limitations | one sentence: 15-site result is best-found under a heuristic follower, 1.5-1.8x above the exact follower, ranking validated on pairs only |

Net page budget: +0.7 in for the wider map (the built `fig_map15.pdf` measures 7.2 x 2.74 in after the tight
bounding box of the 7.16 x 2.7 in figure of section 6.1; `\figfile` scales it to the text width, so the height is what
counts, 0.2 in more than the 2.55 in first assumed), +3.2 in for the table, +0.6 column of text; -4.5 in and two
captions from the deleted figures. No paper edit is made now.

## 9. Decisions for the author (recommended default first)

| # | decision | default | alternative |
|---|---|---|---|
| 1 | fleet / demand | 48 riders / 240 orders (levels 192/240/288) | 60/300 (DOT anchor) or 64/320 as a sensitivity only |
| 2 | approve the union arc library (2-3 laptop days, no AWS cost) | yes, prerequisite for Plan A | Option B with today's code (section 10) |
| 3 | lower level and variant | rule-based module, r2, one variant for every number | r5 (range-aware swaps, reservations, cost-aware transfers): changes how batteries move between the 15 sites |
| 4 | site count | exactly 15, one unit each, V(k) curve shown, "15 units free" as one comparison row | at most 15 (planner opens fewer and buys spares) |
| 5 | pickup radius pruning (20 blocks) | off at 48/240 | on if 64/320 is run; then for the whole family |
| 6 | rule-follower validation (1.6 USD) and root LP bound (0.8 USD) | validation yes, LP no | both, or neither |
| 7 | scenarios | 6 search / 12 final / 12 held-out | 12 throughout, or 15 |
| 8 | map frame | rotated paper frame (north right, matches Fig. 4) | north-up, tall two-column layout with the table beside it |
| 9 | basemap | OSM major streets as vector lines, cached, ODbL credit in caption | NTA outline only |
| 10 | density layer | DOHMH restaurant density | generated order-origin density of the 12 scenarios |
| 11 | marker size | swaps per evening from the run | design size (spares B) |
| 12 | table | all 15 rows in the paper | 5-6 cluster rows, full table in the repository |
| 13 | page cuts | delete Figs. 5 and 6 | trim the toy example (Sec. V) or Sec. VI-C |
| 14 | DOT highlight | red ring on the marker | mark DOT sites in the table only |
| 15 | per-site metrics and remove-one pass | log them in the run; remove-one pass included (cheap under the rule follower) | metrics re-pass afterwards (about 1 server hour) |
| 16 | AWS spend | approve about 9 USD (6-11) on-demand in November, user starts the instance | Option B |

## 10. Option B if the full plan is too expensive (in money or in coding days)

Skip the union library; keep today's per-bike library and shrink the fleet to what fits in memory.

| item | Option B |
|---|---|
| fleet / demand | 24 riders / 120 orders (levels 96/120/144); 15 sites about 40 % utilised, 16/80 fits more easily but leaves them at about 25 % |
| library per cell | about 34 M arcs, 12-18 GB, about 140 s on the server; 5 workers under `--max-rss-gb 110` on the 4xlarge |
| search | same `force_k` + proxy-screen procedure but one restart (greedy from the m=2 incumbent) and k_screen = 2: about 600 search cells + 370 final/remove-one cells = about 1,000 cells |
| server hours | 1,000 x 140 s / (5 x 0.9) = 8.6 h + dry run + metrics = about 10 h = 11 USD on-demand; on a Spot r7i.8xlarge (10 workers, 0.8 USD/h) about 5 h = 4-5 USD plus retuning of the lane scripts |
| coding | L2 and L3 of section 7 (1.5-2 laptop days); no L1 |
| what is lost | the "city-scale fleet" story (sites half idle), the 64/320 sensitivity, and the exact ILP validation stays at 8-16 riders; the map and the interpretation are unchanged |
| what is kept | exactly-15 layout, V(k) curve, regret rows, per-site table, same figure |

A still cheaper Option C (not recommended): 16 riders / 80 orders, 8 workers, about 4 h = 4.5 USD, but most of the
15 sites would do 1-2 swaps per evening and the supervisor's "why these 15" would be answered by coverage alone.

## 11. Risks, briefly

* The rule follower is 1.5-1.8x above the exact follower and does not rank near-tied layouts; the 15 sites are
  "best found under the rule follower" and the paper must say so.
* The study depends on the union library; without it 48 riders are impossible (60 GB per evening). Toy reproduction
  tests gate any server run.
* Extrapolated cell times (20-30 s) rest on laptop measurements x server factors; the dry run (S1) checks them before
  the search starts, and the 25 % contingency covers a 2x slip in the search stage only.
* Label collisions on the map for neighbouring candidates; leader lines or an offset table handle them.
* Page limit: the new figure* and table cost about 0.4 page; it balances only if Figs. 5 and 6 are folded into text.
* AWS: October is at about 64 USD; the spend above is additional and needs the user's go-ahead; the watchdog must stop
  the instance after the lanes.

---

## 12. Critic corrections (2026-10-28, checked against the code and the probe records)

Checked: `ebike_swap_sim/{arcs,baseline,bilevel,aggregate,evaluate,sites_nyc,data_nyc,generator,config}.py`,
`experiments/r7_search.py`, `outputs/r7_prod_final/r7_siting/{cache/index.jsonl, records.jsonl, cost.jsonl,
wall_time.json}`, `RESULTS_final.md`, and the probe outputs in the session scratchpad (`search_probe/probe_b_N6_b8.json`,
`probe_b_N6_b16.json`, `map15/`). The probe numbers quoted in sections 1-3 reproduce (instance 16 / 50 s, template
1.86 M / 8.32 M arcs, rule evaluation 2.2-3.4 s / 12.0-20.4 s, served 0.29-0.68, RSS 2.5 / 6.1 GB; rule/ILP cell
ratio median 1.68; Spearman 0.92 over the 11 complete pairs and -0.39 over the 19 complete single-site layouts, not
16). The corrections below change the hours, one bound statement, and the "15 sites are busy" claim.

### 12.1 Infeasible or understated steps

| # | item in sections 2-3, 7, 10 | what the code says | correction |
|---|---|---|---|
| C1 | "8 one-thread workers, utilisation 0.9" (S3, Option B) | every pricing pool is `concurrent.futures.ThreadPoolExecutor` (`r7_search.price_cells` line 584, `benders.py` 1732/2342/2550); no `multiprocessing` anywhere in the package or the experiments. With the ILP the Gurobi solve releases the GIL (measured utilisation 0.53 at 4 x 3 threads). The rule follower is pure Python (library build, `run_baseline`, `evaluate.check`) and holds the GIL: 8 thread workers = about 1 core. `price_cells` also hard-codes `policy="ilp"` | the `k15` stage needs a **process pool** (fork after the scenario instances are built, return small dicts, never pickle a library) and its own baseline cell runner: add 0.5-1 laptop day to L2. Without it the search wall time is x7 (section 12.4) |
| C2 | union library at "20-30 s per cell" | `build_arcs` runs `_reachable` (pure-Python DFS over all template specs) once **per bike**; the note's per-class variant still runs it once per (depot, q0) class present: about 30 of the 42 classes at 48 riders (8 riders per depot over 7 levels). One DFS over a 4 M-spec union network is 4-8 laptop s, so 30 passes = 2-4 min laptop, 5-10 min server per cell | the 20-30 s holds only if L1 computes reachability in **one time-ordered sweep with a per-state class bitmask** (the network is a DAG in t; one O(arcs) numpy pass for all classes), or skips per-class reachability for the rule follower (the simulation only walks forward from each bike's own source, so every visited state is reachable by construction; the terminal pre-check is a gbar lookup). Put this in L1's scope and in the S1 gate (cell <= 45 s) |
| C3 | instance build not in the stage table | `generator.build_route_library` calls `net.route(u, v)` for every ordered node pair; measured 16 s at 81 nodes and 50 s at 150 nodes (about 2.3 ms per pair). At 240 orders the node set is about 59 candidates + 6 depots + ~380 order nodes = ~440 nodes = 190 k pairs: **7-8 min per scenario on the laptop, 12-15 min on the server**; 24 scenarios = 3 h laptop or 5-6 serial server hours. `inst.routes` then holds 190 k `Route` objects (0.3-0.5 GB) per scenario | build the 24 instances once (laptop, each under the 10-min limit, or 0.7 server-h in 8 processes), `Instance.save` them, load in the workers. At 64/320: ~560 nodes, 310 k pairs, 12-13 min per scenario, over the laptop limit: server only (about 1 h in parallel) |
| C4 | `n_orders` "existing override" | `data_nyc.make_nyc_instance` line 1122: `n_orders = round(n_bikes x window_h x orders_per_bike_hour)`; there is no independent order count | `n_bikes=48` alone gives 240 orders and the stratified levels 1.0/1.25/1.5 orders per bike-hour give 192/240/288; nothing else to pass. Correct as a mechanism, wrong as a description |
| C5 | memory on the 123 GB machine | Plan A: 8 processes x (instance 0.5 GB + union 1.5-2 GB + transient views) = 20-30 GB, fine. Plan B: per-bike library at 24 riders / 120 orders / 15 open sites = 30-40 M arcs = 11-14 GB per cell, 5 processes = 55-70 GB, fits under `--max-rss-gb 110`. **Not feasible at any larger fleet:** the all-candidates template tier (`evaluator.template(s)`, used by `_screen`, `superset_bound`, `template_pair`) keeps one template per scenario resident; production already peaked at 104 GB RSS in the m1 stage with 12 resident 8.5 M-arc templates | the k15 stage must run on the open-sites tier only and never call `template(s)`; the optional root LP (S5) at 48/240 needs the union template (10-12 M columns, 15-25 GB per LP): at most 3-4 LPs at a time, 12 LPs in 40-80 min, keep it off by default |
| C6 | S2 validation "exact aggregated ILP, 1,800 s cells, 16 riders / 80 orders / 5 sites; report ratio and rank agreement" | R6 stress runs at >= 10 bikes: 0 OPTIMAL at 600 s, gaps 3.7-13.3 %; the laptop probe at 8 riders / 80 orders / 15 sites had a 94 % gap at 240 s. The 9 cells will end at TIME_LIMIT with gaps; "rank agreement" over 3 layouts is 3 points | keep it only as a **ratio against an ILP incumbent with its gap stated** (rule / incumbent, gap g), 9 cells x 1,800 s / 4 workers = about 1.2 h + templates = 1.5 h, 1.6 USD; drop the rank-agreement claim at that scale |
| C7 | laptop-to-server factor "1.9x Python, 2.1x LP from the October probe" | `siting_scaleup_design.md` records the factor as unknown (1.3 assumed); the only server measurement is the production template build: 28-77 s for 8.5 M arcs = 3.3-9 s per M arcs against 1.8-2.1 laptop s per M, i.e. 1.6-4x under 4-thread contention | use **2.5x** for pure-Python work: union cell 25-35 s server; let the S1 dry run measure it |

### 12.2 Would 15 sites still be idle?

* Production cache, exact follower, 8 riders: mean 8.0 swaps per evening over all 591 cells (1.0 per rider; single-site
  layouts dominate), 12.05-13.9 at the best pairs (1.5-1.7 per rider). At 48 riders that is **48-77 swaps per evening =
  3.2-5.1 per site at 15 sites = 45-70 % of the window capacity** (about 7.4 swaps: 3 spares + 2 chargers x 48 slots /
  18-24 levels x 5 min at p_ch = 0.33 kW). Section 1's "4-5 swaps per site, 60-70 %" is the upper end.
* Under the rule follower the swap count at scale is unmeasured. The probe's rule follower served 0.29-0.53 of the
  orders where the ILP served 0.78 at the same single site, so fewer km and fewer swaps; the r2 rider heads for the
  nearest stocked site, so the sites nearest the six entry depots take most swaps and the northern "coverage" sites may
  see fewer than one swap per evening. At 48/240 the 15-site layout can therefore still be a 2-cluster layout with
  coverage sites that the follower never uses.
* Correction: make the fleet decision at the S1 dry run (CSCD-15 at 48/240, 12 scenarios, r2): **if the median site
  makes fewer than 3 swaps per evening, go to 64 riders / 320 orders** (pickup-radius pruning on for the whole family;
  union network 7-9 M arcs, 2.5-3 GB per process, 40-60 s per cell; instances built on the server). Budget both
  (section 12.4). Either way the per-site table reports swaps, and sites below one swap per evening are called coverage
  sites in the text.
* V(k) curve: **k = 1 and k = 2 cannot come from the production values** (8 riders, exact follower, 1,085.87 and
  716.85). Every point of the curve must be priced at the same fleet with the same follower (2 extra layouts x 12
  scenarios, cheap). Section 5 bullet 2 is withdrawn.

### 12.3 Bound and validation statements

* The all-candidates root LP (free sizes) is a valid lower bound for the **rule follower's** values too, not only for
  the exact follower: every certified rule schedule is feasible for the ILP, so V_rule >= V_ILP >= LP. It is weak (the
  rule follower sits 1.5-1.8x above the ILP at 8 riders), not invalid; the paper may call it a valid but loose bound.
  At m = 15 with 15 units the fixed part is 15 x 13.19 = 197.85 USD/day of allocated set-up on top of the LP opex.
* The production root LPs took 4,555-9,627 s (mean about 7,100 s = 2.0 h, not 2.6 h; 9,243 s was one of twelve) at
  2.4-2.8 M columns and 12-15 GB each.
* The rule/ILP ratio and the rank agreement in section 2 come from `baseline_total` rows that are the MIP start of
  each ILP cell (same library, same `evaluate.cost`), so they are comparable; the single-site figure is -0.39 over 19
  complete layouts.
* The DOT anchor (12,100 swaps / 184 days / 5 sites) overstates: the swap count runs past the 184-day pilot (swapping
  extended to Feb 2025) and the City Hall hub charged rather than swapped; "about 13 per site per day" is an upper
  anchor, "about 10" is safer. It does not change the fleet decision.
* No optimality statement at 15 sites stands (section 5); correct.

### 12.4 Recomputed hours and USD (r7i.4xlarge on-demand, 1.0584 USD/h; instance stopped, user starts it)

Plan A, 48 riders / 240 orders, union library with bitmask reachability (C2), process pool (C1):

| stage | wall h | USD | basis |
|---|---|---|---|
| S0 build and save the 24 scenario instances | 0.7 (or 3 h laptop, free) | 0.7 | C3: 24 x 13 min / 8 processes |
| S1 dry run + gates (cell <= 45 s, RSS <= 4 GB per process, median site >= 3 swaps) | 0.5 | 0.5 | |
| S2 rule-follower ratio check (ratio only, gaps stated) | 1.5 | 1.6 | optional |
| S3 search, about 1,600 cells | 1.7-2.2 | 2 | 1,600 x 30 s / (8 x 0.85) |
| S4 final table, held-out, V(k) incl. k = 1, 2 re-priced, remove-one, metrics | 1.0 | 1 | about 400 cells |
| contingency 30 % | 1.6 | 1.7 | |
| **Plan A total** | **about 7 h** | **about 7.5 USD** (6-9) | the note's 8 h / 9 USD stands within the range |
| escalation to 64 / 320 (C12.2 gate) | +3-4 h | +3.5-4.5 USD | cells 40-60 s, instances on the server (1 h) |
| **Plan A with escalation** | **10-11 h** | **11-12 USD** | |

Failure modes that the gates must catch before the search starts: thread pool instead of a process pool = search x7
(about 20 h, 21 USD in all); per-class DFS reachability = 5-10 min per cell (search 15-35 h; do not run).

Plan B (today's per-bike library, 24 riders / 120 orders, process pool with 5 workers): 1,000 cells x 140 s /
(5 x 0.85) = 9.1 h + S0 0.5 + S1 0.5 + S4 1 + 25 % = **about 14 h = 15 USD** (the note's 10 h / 11 USD assumed the
thread pool gives 5 cores; it does not). Without a process pool about 40 h = 42 USD. Spot prices quoted in section 7
(0.45 and 0.8 USD/h) are not verifiable offline and are not relied on.

Laptop coding: L1 3-4 days (union library + bitmask reachability + reproduction tests), L2 2 days (process pool and
baseline cell runner, `force_k`, per-policy gate, proxy screen, k-median, per-site metrics; note `charge_steps_facility`
already exists in `metric_pack`, so kWh per site is a multiplication, not a new metric), L3 0.5 day: **about 6 laptop
days**, not 3-4.

### 12.5 Top risks after the corrections (ordered)

1. GIL: the whole timing of Plan A and Plan B assumes a process pool that does not exist in the code; with the
   current thread pool the rule-follower search is single-core (x7 wall).
2. Reachability cost in the union library: per-class DFS makes the cell 5-10 min; the bitmask sweep is a design
   requirement, not an optimisation, and must be in the L1 tests.
3. Idle sites under the rule follower at 48/240: 3-5 swaps per site is the ILP's rate; r2's rate is unmeasured and
   lower, and the nearest-stocked-site rule concentrates swaps near the depots. The S1 gate decides 48/240 vs 64/320.
4. Instance build at 240-320 orders (7-13 min per scenario, quadratic in nodes) is a missing line; it is cheap only if
   built once and saved.
5. All-candidates templates do not fit at any larger fleet (104 GB RSS at 8 riders in production); every k15 call must
   stay on the open-sites tier.
6. The rule follower ranks only materially different layouts like the ILP (pairs 0.92, singles -0.39); the 15-site
   result is heuristic-versus-heuristic and the paper must say so; the S2 check gives a ratio with a gap, not a ranking.
7. AWS: October is at 75.9 USD for the production run alone (`cost.jsonl`, 71.7 h), i.e. above the "about 64" in the
   note; Plan A adds 7.5-12 USD, Plan B 15 USD, both in November unless the author decides otherwise.

---

## 13. Implementation status (2026-10-28)

Gate of the R8 lanes before any server run. Laptop only (nice -n 15, Gurobi Threads 1, every run under 10 min, RSS
under 8 GB); nothing was uploaded and the instance was not touched. Details and the decision trail: `DECISIONS.md`,
"R8 fifteen-site study (2026-10-28)".

### 13.1 What exists

| item | where | state |
|---|---|---|
| L1 union (bike-class) arc library, one time-ordered bitmask reachability sweep (C2), aggregation fast path | `ebike_swap_sim/arcs.py` (`UnionArcLibrary`, `build_union_arcs`, `reach_sweep`, `coreach_sweep`, `library_mode`), `aggregate.py` (`_init_union`), `tests/test_union_arcs.py` (38 tests) | done; reproduces `build_arcs` arc ids, schedules, costs, `check` reports and the aggregated ILP model fingerprint on the toy, reduced-6 `manhattan_dot` and `r5_manhattan` families; off by default (no key in `DEFAULT_OPTIONS`, no cache-key or signature change) |
| L2 family `manhattan15` (48 riders, orders from `n_bikes`, C4), per-site metrics, `force_k` search, per-policy service gate, proxy screen, k-median / DOT-first / CSCD / CSAV / CSTC warm starts | `sites_nyc.py`, `evaluate.py` (`site_metrics`), `bilevel.py`, `experiments/common.py` | done |
| L2 driver: process pool (C1), instances built once and saved with a pickle twin (C3), open-sites tier only (C5), dry-run gates, ratio-with-gaps ILP check (C6), search, final, remove-one, `layout.json` + `site_stats.csv`, `RESULTS.md` | `experiments/r8_k15.py`, `tests/test_r8_k15.py` (13 tests + 1 opt-in `R8_HEAVY`) | done, fixer pass after two reviews applied |
| L3 map and 15-row table | `paper_itsc/figs/src/make_figs.py` (`fig_map15`, `site_table15`), `data/raw/osm_major_roads_manhattan.json` | done; renders the DEMO until the run writes `figs/map15/` |
| lane plan | `ebike_swap_sim/outputs/cloud_lanes_k15/lanes.txt` + `lanes.json` (6 lanes: instances -> dryrun -> {validate, search} -> final -> report) | current: regenerated with `--write-lanes` and diffed, only the path line of a scratch `--lanes-dir` differs; `run_lanes.sh start ... --max-threads 12 --dry-run` accepts it |
| server pre-flight | `deploy/aws/r8_prod_check.sh` | new: 47 code markers (L1, L2, fixer), 4 negative markers (no `ThreadPoolExecutor`, no `.template(` / `superset_bound` / `subset_library` in the driver), lane-plan checks (six lanes in order, `k15_search` after `k15_dryrun`, every command on `manhattan15`, `R7_BATCH=k15`, `--workers 8`, `--out-dir outputs/r8_k15`, no `--n-bikes` / `--n-orders` / `--ignore-gates`), no running `lanes_dispatch`, optional `--smoke` (toy run of every stage, 3 s). Exit 0 ok, 2 stale code / bad plan, 3 dispatcher running, 4 smoke failed; each exit path was exercised on an unzipped copy |
| upload zip | `ebike_swap_sim/outputs/r8_upload/r8_code.zip` | 109 files, 1,303,490 bytes, md5 `ab8cca8a5f45166112877cd0897ba188`; see 13.3 |

### 13.2 Tests (laptop, 2026-10-28, one pytest process per file)

* Full suite: 27 files, **535 collected = 527 passed, 8 skipped, 0 failed, 0 errors**. The skips are the opt-in ones:
  six r6_fill solver smokes, the `R8_HEAVY` cell, the `R7_REPRO` reproduction (run separately). Longest files:
  `test_r7_siting` 232 s, `test_union_arcs` 171 s, `test_round3` 160 s, `test_o2_benders` 110 s.
* `R7_REPRO=1 pytest tests/test_r7_siting.py -k reproduced`: **1 passed** (56 s; the 149 cache keys of
  `r6_o2/manhattan_pass2`), so the older families' keys, pruning and pool signatures are unchanged.
* Pre-flight on the tree and on the unzipped copy: exit 0, smoke ok in 3 s.

### 13.3 Contents of `r8_code.zip`

Paths are relative to the project root, as in `r7_code.zip`: `data/raw/dot_candidate_sites.csv`; `deploy/aws/*` without
`aws_env*.sh`, `README_AWS.md` and `__pycache__` (13 files, `r8_prod_check.sh` new); `ebike_swap_sim/{CONTRACT.md,
README.md,pytest.ini}`; the `*.py` of the package, `experiments` and `tests`; `ebike_swap_sim/outputs/cloud_lanes_k15/
{lanes.txt,lanes.json}`. All 109 files are md5-identical to the tree, 0 CJK, no secret pattern, unix modes kept. New
against `r7_code.zip`: `r8_prod_check.sh`, `r8_k15.py`, `test_r8_k15.py`, `test_union_arcs.py`, the two k15 lane files;
the R7 lane plans are left out (they stay on the server, `unzip -o` does not delete them). No new data file is needed:
the server builds the instances from the DOHMH / NTA / ACS / counter files that the R7 production already used (on the
server since the R7 sync, unchanged since 2026-10-12, DOT CSV since 2026-10-21); the OSM street extract is read only by
`make_figs.py` on the laptop.

### 13.4 Measured laptop timings

| what | scenario | measured | with the 2.5x server factor (C7) |
|---|---|---|---|
| instance build (route library, `Instance.save` + pickle) | level 1.0 (192 orders): 343 nodes, 117 k routes, 15.5 MB JSON | 217-240 s | 9-10 min |
| instance build | **level 1.5 (288 orders), weekend: 450 nodes, 202 k routes, 26.8 MB JSON, 12.4 MB pickle, 0.7 GB RSS** | **414 s** | **17 min** |
| worker instance load (pickle twin) | level 1.5 | 0.08 s | 0.2 s |
| cell CSCD-15 (union library, r2 follower, `check`, cost, per-site metrics) | level 1.0 | 3.1 s, 1.2 GB worker RSS | 8 s |
| cell CSCD-15 / CSAV-15 / CSCD-20 | level 1.5 | 7.9 / 6.7 / 7.0 s; 241-286 M virtual arcs; worker RSS 1.7 / 1.9 / 2.1 GB | 17-20 s |
| gates (cell <= 45 s, RSS <= 4 GB) | every probed cell | pass | pass with a 2x margin |
| median open-site swaps (gate >= 3) | level 1.0 CSCD-15 / level 1.5 CSCD-15, CSAV-15, CSCD-20 | 3 / 3, 3, 3 | the gate sits exactly at its threshold: the server dry run decides 48/240 vs 64/320 |

Side observations from the level-1.5 cells (not a result, one scenario): served share 0.53 (CSCD-15), 0.70 (CSAV-15),
0.65 (CSCD-20); two CSCD-15 sites and six CSCD-20 sites made no swap. The CSCD-15 swaps per site range 0-7, so the
"coverage site" wording of section 12.2 is likely needed.

### 13.5 Corrected server hours and USD (r7i.4xlarge on-demand, 1.0584 USD/h; 8 physical cores, dispatcher budget 12)

The lane plan's own figures (`LANE_HOURS`: 0.7 + 0.5 + 1.5 + 2.2 + 1.0 + 0.1 = 6.0 h = 6.4 USD before contingency) were
set before the cell was measured. The dispatcher runs the lanes one after the other (validate takes all 12 threads,
every rule-follower lane 8), so the wall time is the sum of the stages.

| stage | basis | wall h |
|---|---|---|
| boot, unzip, pre-flight, sync | | 0.2 |
| `k15_instances` | 24 builds (8 per level) at 9 / 13 / 17 min server in 8 processes: 18.9 k s of work / 8 + the last wave | 0.8-0.9 |
| `k15_dryrun` | CSCD-15 + the reference layouts D23, D07 + D45, D07, D45 (the start layout is D07 + D45) x 12 scenarios = at most 72 cells at 12.5 s mean, 8 workers | 0.1-0.2 |
| `k15_validate` (optional) | 9 ILP cells x 1,800 s in 4 x 3 threads = 3 waves, + 16-rider instances and templates | 1.6 |
| `k15_search` | about 1,600 cells in batches of 18 (3 layouts x 6 scenarios) = 3 waves of the slowest cell (about 17 s) per step: about 90 steps x 50 s + parent overhead | 1.2-1.6 |
| `k15_final` | about 450 cells (8 layouts x 24, V(k) 6 x 12, remove-one 15 x 12) at 12.5 s, 8 workers, utilisation 0.85 | 0.3-0.5 |
| `k15_report` | | < 0.1 |
| **sum** | | **4.3-5.0 h** |
| contingency 30 % (the 2.5x factor is still a laptop extrapolation) | | 1.3-1.5 |
| **Plan A total** | | **about 5.5-6.5 h = 6-7 USD** |
| without the optional ILP check (`--only` without `k15_validate`) | | about 3.6-4.4 h = 4-4.5 USD |
| escalation to 64 / 320 (if the dry-run swap gate fails; author's decision) | builds about 2x (about 560 nodes), cells about 2x | +3-4 h = +3-4.5 USD |

This replaces the 7 h / 7.5 USD of 12.4 (lower: cells measured at 3-8 s laptop instead of the assumed 12 s; higher
only in the instance stage, which the level-1.5 build makes 0.8-0.9 h). October already holds 75.9 USD for the R7
production; this spend goes to November unless the author decides otherwise. The watchdog (`~/idle_shutdown.state`)
stops the idle instance after the lanes; check it with `bash deploy/aws/watch.sh once` or stop the instance by hand.

### 13.6 Server commands (project root `~/battery_swap`; the author copies `r8_code.zip` there and starts the instance)

```bash
cd ~/battery_swap
# 0. nothing else may run: no lane dispatcher, no experiment process
tmux ls 2>/dev/null                      # no lanes_dispatch, no lane_* session

# 1. unpack the R8 code (adds the k15 lane plan; the R7 files on the server stay)
unzip -o r8_code.zip

# 2. pre-flight: exit 0 required (2 = stale code or bad lane plan, 3 = a dispatcher runs, 4 = smoke failed)
bash deploy/aws/r8_prod_check.sh --smoke

# 3. start the k15 lanes (dry run first)
export LANES_DIR=$PWD/ebike_swap_sim/outputs/cloud_lanes_k15
LF=ebike_swap_sim/outputs/cloud_lanes_k15/lanes.txt
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --dry-run
bash deploy/aws/run_lanes.sh start $LF --max-threads 12
#    without the optional exact-ILP ratio check (saves about 1.6 h = 1.7 USD):
# bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --only k15_instances,k15_dryrun,k15_search,k15_final,k15_report

# 4. status, logs and the dry-run gate (k15_search refuses to start when dryrun.json says escalate)
bash deploy/aws/run_lanes.sh status $LF
bash deploy/aws/run_lanes.sh logs k15_search 40
python3 -m json.tool ebike_swap_sim/outputs/r8_k15/dryrun.json | head -40

# 5. cost (R7_BATCH=k15 rows of every lane)
cd ebike_swap_sim && python3 experiments/r7_cost.py outputs/r8_k15; cd ..
```

Laptop afterwards: `deploy/aws/sync_down.sh --path ebike_swap_sim/outputs/r8_k15 --path
ebike_swap_sim/outputs/cloud_lanes_k15` (instances stay on the server unless `--with-instances`), then copy
`layout.json` + `site_stats.csv` to `paper_itsc/figs/map15/` and run `make_figs.py map15`. A failed dry-run gate
(`escalate: true`) stops the chain at `k15_search`; the 64 / 320 escalation is the author's decision (design 12.2).
