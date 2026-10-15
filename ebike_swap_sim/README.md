# ebike_swap_sim — E2 battery-swap / delivery-bike optimisation (NYC e-bike delivery)

Python implementation of the time-expanded ILP of `notes/extracted/E2.txt` (bikes on
state networks `(node, slot, battery level)`, swap / charge facilities with inventory
balance, battery transfers between facilities, order service costs) together with an
event-driven baseline policy, a synthetic instance generator, a semi-real NYC instance
builder (round 2) and the experiment scripts.
Equation numbers everywhere refer to E2; **all binding implementation conventions are in
[`../notes/DECISIONS.md`](../notes/DECISIONS.md)** (round 1: timing of the inventory
recursion, arc construction rules, model switches; round 2, sections R2.1-R2.4: USD cost
variants, the `usd4h` / `usd8h` instance families, the revised baseline rules, the real
NYC data pipeline; "R2 implementation notes" at the end records the sizes actually chosen;
round 3, sections R3.1-R3.3: the hard service-share constraint (33) replacing the lexicographic
variant, end targets kept, the solve / reuse protocol and the extended seed sets; round 4, "E9
relaunch decisions" E9R.1-E9R.4: the bi-level siting family, search rules and reposition
conventions). The module API contract is in [`CONTRACT.md`](CONTRACT.md).

The E2 mathematics (`ilp.py`, `arcs.py`, `evaluate.py`) is unchanged since round 1; the
toy reference values 12.5 / 11.2 / 106 are reproduced by `experiments/e1_toy.py`.

## Layout

```
ebike_swap_sim/                 run everything from here with PYTHONPATH=.
├── ebike_swap_sim/             the package
│   ├── config.py               SimConfig: physical parameters of the synthetic simulator
│   ├── network.py              GridNetwork (Manhattan grid, elevation, signals, zones); route(u,v)
│   ├── or_instance.py          data model: Discretisation, Route, Bike, Order, Facility, Service,
│   │                           Instance (validate, JSON round-trip), toy_instance(), battery_swap_p7_instance()
│   ├── arcs.py                 ArcLibrary: time-expanded bike networks, (1)-(4), (9), pruning options
│   ├── evaluate.py             Schedule; cost (26)-(32); check (5)-(22), (24), (33); metrics; inventory recursion
│   ├── ilp.py                  gurobipy model of (5)-(22), (26)-(33) + switches, MIP start, solution extraction
│   ├── baseline.py             event-driven policy (R2.3: stock-aware site choice, DEMAND_AWARE charging,
│   │                           JIT dispatch, FCFS swap service, optional reorder-point transfers; variants)
│   ├── generator.py            synthetic instances: grid, demand OD modules, facilities, services, pruning, sizing;
│   │                           round-2 mode (window_h, Kaggle order attributes, assumed time profile, cost variants)
│   ├── costs.py                R2.1 cost variants from notes/data/cost_calibration_usd.json (toy, usd_A, usd_sunk, ...)
│   ├── data_nyc.py             R2.4 semi-real NYC: StudyBox projection, DOHMH restaurants -> Kaggle cuisines,
│   │                           NTA point-in-polygon, GeoDa fallback zone weights, crash / counter loaders,
│   │                           make_nyc_instance()
│   ├── acs_weights.py          R2.4 literature zone weights from the ACS 2020-24 NTA tables (ACSZoneWeights)
│   ├── sites_nyc.py            E9: the 12 Midtown candidate sites, siting families / size menus, layout -> instance,
│   │                           admissibility rules, siting pruning (all_candidates / open_sites), sub-libraries
│   └── bilevel.py              E9: Layout, LowerLevelEvaluator (cached E2 solves per scenario), exhaustive,
│                               greedy_local_search, deck_heuristic, integrated_stochastic_ilp, cross_evaluate, [U4]
├── experiments/
│   ├── common.py               instance families, pruning defaults, baseline variants, run_pair(), output helpers
│   ├── e1_toy.py               E1: toy reproduction (12.5 / 11.2 / 106 / lexicographic / baselines / p.7 / identities)
│   ├── e2_synthetic_smoke.py   baseline vs ILP on the small / medium / large synthetic families
│   ├── e2_coord*.py, e3_transfers_separation.py, e4_sizing.py   round-1 experiments (see outputs/)
│   ├── e2u_coord_usd.py, e3u_transfers_usd.py, e4u_sizing_usd.py, e8_nyc.py   round-2 USD experiments
│   ├── e2u_coord_usd_fixed.py, e3u_transfers_usd_fixed.py, e8_nyc_fixed.py    review-fixed copies (the originals
│   │                           were running when the review landed; the copies write to outputs/<name>_fixed/)
│   ├── e2u_round3.py, e3u_round3.py, e4u_round3.py, e8_round3.py   round-3 scripts (R3.3: fill every cell, reuse
│   │                           round-2 rows only if OPTIMAL / gap <= 1 %, zeta cells, more seeds; --dry-run /
│   │                           --smoke / --analyse); e3u_round3_report.py builds the E3u report from records.jsonl
│   ├── e9_bilevel_siting.py    round-4 bi-level siting (E9.1-E9.6: --validate / --sweep / --roles / --deck / --cross /
│   │                           --access; --dry-run / --smoke; outputs/e9_bilevel/<sub>/)
│   ├── r2_size_probe.py        round-2 size probe (R2.2): arcs / binaries / solve time per family and size
│   └── r2_cost_variants.py     round-2 cost-variant comparison (R2.1 degenerate-objective check)
├── tests/                      pytest suite, 158 tests (core, ilp, baseline, generator, costs, data_nyc, acs_weights,
│                               experiments, round3, bilevel)
├── outputs/                    experiment outputs; round 1: e1/, e2_smoke/, e2_coord/, e2_coord_v2/, e3/, e4_sizing/;
│                               round 2: r2_probe/, e2u_coord_usd/, e3u/, e4u_sizing_usd/, e8_nyc_fixed/;
│                               round 3 (authoritative): e2u_round3/, e3u_round3/, e4u_round3/, e8_round3/ (each with a
│                               RESULTS_final.md; e8_nyc/ is the superseded pre-fix run, see "Outputs index");
│                               round 4: e9_bilevel/ (RESULTS_E9.md + six sub-folders with RESULTS_final.md;
│                               _first_attempt/ is superseded)
├── CONTRACT.md                 API contract between the modules
└── pytest.ini                  pythonpath = . so tests run without PYTHONPATH
```

Only `ilp.py` imports gurobipy; `ebike_swap_sim.ilp`, `.baseline`, `.generator`, `.costs`,
`.data_nyc` and `.acs_weights` are lazy attributes, so `import ebike_swap_sim` works
without a Gurobi licence or the data files.

## How the model maps to the modules

| E2 object | module / symbol |
|---|---|
| Discretisation (1), `p_ch = eps/(eta Delta)` (19), kWh per charging step (28) | `or_instance.Discretisation` |
| Sets `V, K, I, N, S, C, E`, routes, grid groups, prices, `theta_ia` (31) | `or_instance.Instance` and its dataclasses |
| Bike arcs: wait, reposition, deliver (2)-(4), swap, terminal (9) with `gbar` by Dijkstra | `arcs.build_arcs` -> `arcs.ArcLibrary`; `arcs.compute_gbar` |
| Pruning options (`energy_rounding`, `dominance`, `reposition_targets`, `tau_max`, `start_slack`, `reachable_pruning`, `dummy_terminal_cost`, `swap_q_max`) | `Instance.options` (travel with the instance), `build_arcs(**overrides)` |
| Decision variables `x, u, y, B, C, n, c, h, z` | `evaluate.Schedule` (data) / `ilp.ILPModel` (Gurobi vars) |
| Flow (5), order cover (6), facility bounds (7)-(8), terminal (9), services (10), `D/A` (11), `s/S` (12), balance (13), joint availability (14), storage (15), initial stock (16), end targets (17)-(18), chargers / power (20), grid (21), swap occupancy (22), budget / service share (33) | rows of `ilp.ILPModel._build`; the same families are verified by `evaluate.check` |
| Battery conservation identity (24) | `evaluate.in_transit`, `check()['identity_24_ok']`, `experiments.common.check_identity_24` |
| Objective (26) = setup (27) + electricity (28) + travel (29) + orders (30)-(31) + rebalancing (32) | `evaluate.cost` (used to price every schedule) and `ilp.ILPModel.components` |
| Model switches: `no_transfers`, `colocated` (S = C = N), `fixed_facilities`, `lexicographic`, `battery_swap_v1_bounds`, `budget`, `zeta` (round 3: `zeta` 0.90 / 0.85 is the service-level variant, `experiments.common.run_zeta_case`; `max_service_share` = one `min sum u_i` solve for infeasible cells) | `ilp.build_model(...)` kwargs, defaulting to `Instance.options` / `Instance.budget` / `Instance.zeta` |
| Baseline policy (DECISIONS R2.3 + round-1 spec): nearest-feasible FIFO dispatch with JIT and dead-zone rule, threshold swap, stock-aware site choice, FCFS swap service, DEMAND_AWARE charging (HIGH_FIRST among charged), optional reorder-point transfers; reports (9), (17), (18) | `baseline.run_baseline(inst, lib, BaselineParams)`; arcs taken only via `lib.find`, so ILP and baseline share the same arc library; `baseline.BASELINE_VARIANTS` = `default` / `round1` / `legacy` |
| Cost units (R2.1): `toy`, `usd_A`, `usd_sunk` (default), `usd_B`, `usd_low`, `usd_high`; `F, F_hub, bB, bC` scale with the window length | `costs.load_cost_calibration(variant, window_h)`, `generator.make_synthetic_instance(cost_variant=...)`, `data_nyc.make_nyc_instance(cost_variant=...)` |
| Synthetic NYC-like instances (grid, zones, demographics, time-dependent demand, restaurants, facilities, shuttle services); round-2 mode with Kaggle order attributes and the assumed time profile (R2.2) | `generator.make_synthetic_instance`, `generator.default_pruning`, `generator.estimate_arcs` |
| Semi-real NYC instances (R2.4): DOHMH restaurants mapped to the 14 Kaggle cuisines, Zipf popularity, ACS literature zone weights (GeoDa fallback), real site coordinates projected on the synthetic grid | `data_nyc.make_nyc_instance`, `data_nyc.StudyBox`, `data_nyc.NYCRestaurantSampler`, `data_nyc.NYCDestinationSampler`, `acs_weights.ACSZoneWeights` |

Every schedule — ILP incumbent or baseline — is a `Schedule` priced by `evaluate.cost` and
verified by `evaluate.check`; `ilp.solve` refuses to return a schedule whose checker report is
not clean or whose cost differs from the Gurobi objective. The baseline schedule can be injected
as a MIP start (`ilp.solve(..., mip_start=sched)`), and acceptance is certified by a fix-and-solve.
Because the round-2 baseline only reserves the per-site target (17), its schedule may violate
the network target (18); `experiments.common.feasible_mip_start` then injects the first clean
schedule among the `baseline_round1` / `baseline_reserve` variants and records
`mip_start_variant` (the baseline columns always describe the policy under test).

## Instance families (`experiments/common.py`)

| family | builder | sizes / knobs | costs |
|---|---|---|---|
| `toy`, `p7` | `toy_instance`, `battery_swap_p7_instance` | E2 pp.10-15 (J* = 12.5), Battery_Swap p.7 | toy |
| `small`, `medium`, `large` | `generator.make_synthetic_instance` (legacy mode) | 4/12/24/L8, 8/24/24/L8, 10/30/24/L12 (bikes/orders/H/L) | toy |
| `usd4h` (round-2 main) | generator, round-2 mode | 6 bikes, 4 h window 17:00-21:00 (H 48), 1.5 orders per bike-hour -> 36 orders, B 3 / C 2 at 3 co-located sites, q0 ~ U{4..7}, Kaggle prep 20-35 min, promise +25 min, assumed time profile | `usd_sunk` |
| `usd4h_large` | generator, round-2 mode | the R2.2 nominal 10 bikes / 60 orders / H 48 (3.9 M arcs; solvability within 5 min at Threads 3 not yet verified, see probe) | `usd_sunk` |
| `usd4h_toyunits` | generator, round-2 mode | the `usd4h` instance priced in toy units | `toy` |
| `usd8h` | generator, round-2 mode | 6 bikes, 8 h window 14:00-22:00 (H 96), 72 orders — registered **rolling-horizon only** (`meta['rolling_horizon_only']`) until a single-ILP probe passes | `usd_sunk` |
| `nyc4h` | `data_nyc.make_nyc_instance` | 6 bikes, 4 h, 36 orders (0.75 M arcs under `PRUNING_NYC`); DOHMH restaurants + ACS zone weights in the Midtown study box; sites = busiest restaurant cells; releases from the R2.2 block profile as a step function (same object as `usd4h`, `meta['hourly_profile_used']`) | `usd_sunk` |

Sizes of the round-2 families were fixed by `experiments/r2_size_probe.py`
(`outputs/r2_probe/`, summarised in `../notes/DECISIONS.md`, "R2 implementation notes").
`pruning_for(inst)` applies the plan's pruning (`reposition_targets` = restaurants + facilities +
depots, `tau_max 4`, `start_slack 6`) to synthetic instances and the harder `PRUNING_NYC`
(moves only into facility / depot nodes, `reachable_pruning`) to semi-real ones. **`PRUNING_NYC`
restricts the ILP but not the policy** (the baseline repositions only to swap sites anyway, the
ILP loses pre-positioning moves; on nyc4h `tau_max` never binds), so nyc4h ILP totals are upper
bounds on the written optimum and the reported gaps lower bounds on the coordination value; no
lossless probe exists for these targets yet (`e8_nyc_fixed.py --targets default` runs it).

## Running

Requirements: Python 3.12, numpy, pandas, networkx, matplotlib, pytest, openpyxl (ACS
workbooks), gurobipy 13 (academic licence) for `ilp.py` and the experiments. Gurobi is always
run with `OutputFlag=0`, `Threads=3` (round-2 rule; round-1 outputs used 4) and a time limit.

```bash
cd ebike_swap_sim
export PYTHONPATH=$PWD

# tests (about 2 min with the data-driven tests; 158 tests)
python3 -m pytest tests -x -q

# E1: toy reproduction -> outputs/e1/results.csv, RESULTS.md, figures
python3 experiments/e1_toy.py

# baseline vs ILP on the synthetic families -> outputs/e2_smoke/
python3 experiments/e2_synthetic_smoke.py --families small medium large --time-limit 300

# round-2 size probe (arcs / binaries / solve time) and cost-variant comparison
python3 experiments/r2_size_probe.py --family usd4h --bikes 6 8 10 --seeds 0 1 --pruning default reachable
python3 experiments/r2_cost_variants.py --family usd4h --seed 0 --variants usd_sunk usd_A toy

# round-3 experiments (hours of Gurobi time each; --dry-run lists the cells, --smoke runs a tiny subset,
# --analyse rebuilds results.csv / RESULTS.md / figures from records.jsonl without solving)
python3 experiments/e2u_round3.py --dry-run
python3 experiments/e8_round3.py --analyse

# round-4 bi-level siting (E9); --smoke runs the toy siting instances in seconds, --dry-run lists the plan
python3 experiments/e9_bilevel_siting.py --sweep --smoke
python3 experiments/e9_bilevel_siting.py --validate --dry-run
python3 experiments/e9_bilevel_siting.py --sweep --budgets 1 --seeds 0 1 2 --wall-budget 3600

# zone-weight table from the ACS files -> notes/data/zone_weights_manhattan.csv
python3 -m ebike_swap_sim.acs_weights
```

Minimal programmatic use:

```python
from ebike_swap_sim import toy_instance, build_arcs, cost, check
from ebike_swap_sim import ilp, baseline, generator, costs, data_nyc, acs_weights

inst = toy_instance()                      # E2 pp.10-15, J* = 12.5
lib = build_arcs(inst)                     # 235 arcs per bike
sched_bl, flags = baseline.run_baseline(inst, lib, {"transfer_rule": "REORDER_POINT"})
sched, stats = ilp.solve(inst, lib, mip_start=sched_bl, time_limit=60, threads=3)
print(stats["obj"], cost(inst, lib, sched)["total"], check(inst, lib, sched)["ok"])

# round-2 synthetic family: 4 h window, usd_sunk costs, Kaggle order attributes (R2.1 / R2.2)
inst = generator.make_synthetic_instance(seed=0, n_bikes=8, window_h=4.0, window_start_hour=17.0,
                                         orders_per_bike_hour=1.5, L=12, n_restaurants=8,
                                         cost_variant="usd_sunk")
print(inst.meta["costs"], inst.meta["kaggle_calibration"]["promise_after_ready_min"])
lib = build_arcs(inst, **generator.default_pruning(inst, tau_max=4, start_slack=6))

# semi-real NYC instance (R2.4): real restaurants / zone weights / site coordinates on the grid
cal = costs.load_cost_calibration(variant="usd_A", window_h=8.0)        # F, bB, bC x2
nyc = data_nyc.make_nyc_instance(seed=0, n_bikes=8, window_h=4.0)       # ACS weights by default
print(nyc.meta["geometry_caveat"], nyc.meta["zone_weights_source"])
sched_bl, flags = baseline.run_baseline(nyc, build_arcs(nyc, **generator.default_pruning(nyc)))
```

`experiments/common.py` wraps this into `run_pair(inst)` (baseline + ILP with a feasible baseline
schedule as MIP start, flat record with costs, runtimes, gap, binaries, checker families,
identity (24), the policy's pruned-arc fallbacks / stranded bikes / suppressed late trips,
`n_unservable` orders and `*_served_share_servable`, `mip_start_fallback_errors`, `demand_md5`)
and provides `make_instance(family)`, `pruning_for(inst)`, the documented baseline variants
(`baseline`, `baseline_round1`, `baseline_legacy`, `baseline_reorder`, `baseline_zone`,
`baseline_reserve`, `baseline_informed`), `relax_end_targets` (the fair control; on the copy
`run_baseline_case` keeps the written `R_end_j` as the DEMAND_AWARE reserve so the policy is the
same policy under both target settings), `unservable_orders`, `demand_key` / `demand_md5`,
`pair_anomalies`, CSV / Markdown / figure helpers.

## Data pipeline (round 2)

* `notes/data/cost_calibration_usd.json` -> `costs.load_cost_calibration(variant, window_h)`:
  `toy` (E2 p.14, not window-scaled), `usd_A` (calibration base: kappa 0.50 $/km, w 40, v 80,
  P 30, pi 0.32, F 12.03 / F_hub 29.19, bB 0.332, bC 0.082 per 4 h), `usd_sunk` (**default**:
  rider labour sunk, kappa 0.12, w 18, v 36), `usd_B` (kappa 1.60), `usd_low` / `usd_high`.
  Every instance built with a variant (synthetic or NYC) records the coefficients used in the
  flat `meta['costs']`. Known spec caveat (kept as written): `bB` contains a one-off initial
  charge (0.213 $ per spare) that R2.1 scales with the window like the holding part, so the
  8 h variant overstates it by 0.213 $ per spare (`costs.BB_INITIAL_CHARGE_USD`, `cal['notes']`);
  the 4 h families are exact. The electricity price peak of a TOU variant uses
  `facilities_spec['price_peak_hours']` (default = the grid-limit `peak_hours`; Con Edison TOU
  08-22 h must be passed explicitly), `pi_peak` is `None` in all six R2.1 variants.
* `notes/data/kaggle_calibration.json` -> `generator.load_kaggle_calibration`: prep time
  DiscreteUniform{20..35} min, promise 25 min after ready, 14 cuisine shares, Zipf s = 1.0.
* Time-of-day profile (R2.2, assumption): `generator.TIME_PROFILE_R2` / `data_nyc.ASSUMED_TIME_PROFILE`
  are block profiles evaluated as **step functions** (`generator.block_profile`,
  `data_nyc.assumed_block_config`) by `TimeDependentGenerator` in both builders.
  `data_nyc.assumed_hourly_profile` (24 integrated hourly shares) is for period aggregation
  only: handed to `TimeDependentGenerator` as a 24-list it would be interpolated between hour
  tops and smear the 17:30 step over 17:00-18:00 (the nyc4h instances in `outputs/e8_nyc/` were
  built that way; `e8_nyc_fixed.py` rebuilds them).
* `data/raw/` (see `../data/MANIFEST.md`): DOHMH restaurants (`data_nyc.load_dohmh`, 27k usable
  rows, 90 cuisine descriptions -> 14 Kaggle classes + `other` via `data_nyc.CUISINE_MAP`; the
  `other` class -- cafes, bakeries, desserts, juice, 26 % of the default box, 32.5 % citywide -- is
  unreachable by construction and recorded in `meta['unmapped_share_in_box']`;
  `make_nyc_instance(cuisine_map_overrides=...)` with `CUISINE_MAP_CAFES_AS_AMERICAN` /
  `CUISINE_MAP_REGIONAL_TO_KAGGLE` is the sensitivity hook),
  NTA polygons (`nycnhood_acs.geojson` for the GeoDa fallback, `acs/nta2020.geojson` for the ACS
  path), ACS 2020-24 NTA profiles (`acs_weights.load_acs_tables`, 262 NTAs), crash grid and
  bike-counter profile (`data_nyc.load_crash_grid`, `data_nyc.counter_hourly_profile`; loaders
  only, not in the objective).
* Zone weights (R2.4): `acs_weights.ACSZoneWeights` implements the literature formula
  `w_z = N_z M_age M_eth M_sex M_inc M_kid M_alone M_stu` (M_FI off by default; `N_z = pop18`
  including group-quarters residents -- the note's group-quarters correction is the option
  `gq_correction=True`, `N_z = pop18 (1 - gq_share)`, OFF by default and recorded in
  `meta['zone_weights_gq_correction']`; the cap alternative is moot, max `M_stu` 1.08) and exposes a
  density per km^2 through the `data_nyc.ZoneWeights` protocol; `data_nyc.GeoDaZoneWeights` is the
  loud-warning fallback (`N_z (1 + 2.4 youth16_19_share)` with `N_z = popover18`). `make_nyc_instance` uses the ACS
  weights when the tables are present (`meta['zone_weights_source'] = 'acs_2020_24_literature'`,
  NTA-2020 codes such as `MN0501`), else the fallback (`'geoda_fallback'`, NTA-2010 codes such as
  `MN17`, `meta['zone_weights_warning']`). The table is written to
  `notes/data/zone_weights_manhattan.csv` by `python3 -m ebike_swap_sim.acs_weights`.
* Geometry: no real road network. `data_nyc.StudyBox` projects lat/lon to local metres
  (111.0 km/deg lat, 84.3 km/deg lon), rotates by the Manhattan grid azimuth (29 deg) and snaps
  to 150 m blocks of a synthetic `GridNetwork` (elevation / signals synthetic). Every NYC instance
  carries `meta['semi_real'] = True` and `meta['geometry_caveat']`.

## Reference numbers

* Toy (E2 pp.10-15): ILP 12.5 = 4 travel + 0.1 electricity + 0 unserved + 6 response + 2.4
  rebalancing; `rho = 0` -> 11.2; `no_transfers` -> 106; lexicographic U* = 0; baseline NONE 108,
  baseline REORDER_POINT 14.5 (p.15 inventory table reproduced) under the round-2 rules as well
  as under the `round1` / `legacy` variants; Battery_Swap p.7 table reproduced by the baseline.
  See `outputs/e1/RESULTS.md`.
* Synthetic round 1 (toy units, 10 bikes / 2 h, Threads 4): coordination gap
  (baseline - ILP)/baseline 24.0 % +/- 8.7 (x0.75 / x1 / x1.5: 4.3 / 29.6 / 38.2 %), 90 % of it
  unserved-order penalty; see `outputs/e2_coord_v2/RESULTS_v2.md`, `outputs/e3/`, `outputs/e4_sizing/`.
* Round 2 (`usd4h`: 6 bikes / 36 orders / H 48, `usd_sunk`, R2.3 baseline, Threads 3), gap =
  (baseline - ILP)/baseline, 95 % t-CI:
  * E2u coordination: **21.9 % +/- 8.1** (n = 15; x0.75 / x1 / x1.5: 6.9 / 21.3 / 37.3 %), mean totals
    1022 vs 727 USD per 4 h; composition lateness 54 %, response 25 %, unserved 20 %, travel + electricity
    < 1 %. Relaxed-target control 21.9 % best known. Drop rate by cost variant (seeds 0-1): ILP drops
    4-26 % of orders under `usd_sunk`, 83-86 % under `usd_A` (degenerate, R2.1), 2-35 % under `toy`
    (toy x1 / x1.5 at TIME_LIMIT). 0.9-1.5 M binaries, written model 23/27 OPTIMAL in ~90 s.
  * E3u transfers / separation: co-located 637 USD, +52 / +82 USD for 1 / 2 hubs (29 / 58 of it F_hub);
    value of transfers 0 (a), 6.6 / 12.6 USD lower bounds (b) / (c) under written targets, 0 under relaxed
    targets; REORDER_POINT baseline +143 to +302 USD worse than NONE everywhere. ILP n = 1-2 seeds only.
  * E4u sizing: ILP cost flat in B_j, C_j, P_j (marginal battery +0.14 +/- 1.14 USD/window for 1 -> 2, then
    negative; charger 0.000; power 0); baseline gains 48.5 USD/window per battery for 1 -> 2, 8.5 for
    2 -> 3; free-size ILP buys 3-4 batteries / 2-3 chargers network-wide. Headline gap at default sizes
    22.5 % +/- 21.3 (n = 3).
  * E8 semi-real `nyc4h` (`outputs/e8_nyc_fixed/`): 36.5 % +/- 29.3 (busiest siting), 34.3 % +/- 37.6
    (grid siting), n = 3; relaxed control identical within 0.04 points; siting moves the ILP optimum by
    <= 0.04 % and the baseline by -9 to +4 %; 0.58 M binaries, 12/12 OPTIMAL in 28-60 s. Gaps are lower
    bounds (PRUNING_NYC restricts only the ILP).
  * Sizes / solve-time probe: `outputs/r2_probe/*.jsonl` and "R2 implementation notes" in `../notes/DECISIONS.md`.
* **Round 3 (authoritative; same `usd4h` / `nyc4h` families, R2.3 baseline, Threads 3, Seed 0, TimeLimit 300 s,
  every cell solved, round-2 rows reused only if OPTIMAL or gap <= 1 %), gap = (baseline - ILP)/baseline, 95 % t-CI
  with exact t quantiles:**
  * E2u coordination (`outputs/e2u_round3/`, seeds 0-9): **29.6 % +/- 5.6** (n = 30; x0.75 / x1 / x1.5:
    15.4 +/- 7.3 / 31.2 +/- 9.1 / 42.1 +/- 5.7 %), ILP cheaper on 30/30 instances, mean totals 1167 vs 746 USD per
    4 h; seeds 0-4 reproduce round 2 exactly (21.9 %), seeds 5-9 give 37.2 % +/- 6.2 (harder baseline draws);
    composition lateness 59 %, response 32 %, unserved 8 %, travel + electricity < 1 %. Relaxed control 29.6 %,
    30/30 OPTIMAL, end targets worth 0.34 USD per instance. Service-share constraint (33), R3.1: zeta 0.90
    feasible on 20/30 (all x0.75 and x1), premium over the written optimum 0.9 USD (0.2 %) at x0.75 and 37.4 USD
    (5.5 %) at x1, gap vs baseline 15.2 / 27.8 % (21.5 % +/- 5.9 pooled, n = 20); zeta 0.85 premium 0 / 8.0 USD,
    23.0 % +/- 6.3; both levels INFEASIBLE on 10/10 x1.5 instances (maximum feasible served share 0.74-0.80
    certified, <= 0.83 by bound, vs 0.85 required). 0.89-1.58 M binaries; written ILP 28/30 OPTIMAL, 143 s mean.
  * E3u transfers / separation (`outputs/e3u_round3/`, seeds 0-4, 60/60 cells): co-located 638.2 +/- 28.7 USD;
    separation +52.2 +/- 1.6 (1 hub) / +81.4 +/- 1.6 USD (2 hubs) written, of which F_hub 29.19 / 58.38; relaxed
    +29.3 / +58.5 (= F_hub). Value of transfers 0.01 (a), 8.6 +/- 10.1 (b), 8.6 +/- 10.1 USD (c) written (lower
    bounds, upper 22.2; the separated / written / transfers-free cells stay at a 1.8-2.0 % MIP gap after 600 s),
    0.00 on all 15 relaxed pairs. Gap vs policy NONE 21.3 / 18.4 / 17.8 % written; REORDER_POINT +165 to +207 USD
    worse than NONE on every layout and seed.
  * E4u sizing (`outputs/e4u_round3/`, seeds 0-5 on the B sweep, P sweep and 20-cell B x C grid solved): headline
    gap at default sizes 24.6 % +/- 12.0 (n = 6); ILP flat in B_j, C_j, P_j (operational +0.35 +/- 0.34 USD for
    1 -> 2 spares, then <= 0.09; chargers and power 0.000); baseline +44.2 +/- 21.6 USD per window for the first
    extra spare per site, +6.1 for the second; free-size ILP buys 3.5 batteries / 2.8 chargers network-wide
    (default 9 / 6) saving 1.43 +/- 0.18 USD.
  * E8 semi-real `nyc4h` (`outputs/e8_round3/`, seeds 0-9): **31.8 % +/- 8.2** (busiest siting) / 30.5 % +/- 8.6
    (grid siting), gap positive on 20/20 instances, relaxed control within 0.1 points (end targets 0.27-0.28 USD);
    ILP moves by <= 0.41 USD (0.063 %) between sitings, baseline by -9 to +6 %; 553 k binaries, 40/40 OPTIMAL in
    46 s mean. Gaps remain lower bounds (PRUNING_NYC restricts only the ILP).

## Outputs index

| directory | experiment | authoritative report |
|---|---|---|
| `outputs/e1/` | E1 toy reproduction | `RESULTS.md` |
| `outputs/e2_smoke/` | round-1 synthetic smoke | `RESULTS.md` |
| `outputs/e2_coord/`, `outputs/e2_coord_v2/` | round-1 E2 coordination (`_v2` = after the baseline fairness fixes) | `RESULTS_v2.md` |
| `outputs/e3/`, `outputs/e4_sizing/` | round-1 E3 transfers / E4 sizing (toy units) | `RESULTS*.md` |
| `outputs/r2_probe/` | round-2 size probe (R2.2) | `usd4h.jsonl`, `*_arcs.jsonl` |
| `outputs/e2u_coord_usd/` | round-2 E2u coordination under USD (+ cost-variant drop rates, `variants.csv`) | **`RESULTS_final.md`** |
| `outputs/e3u/` | round-2 E3u transfers / separation under USD (relaxed baseline rows recomputed after fairness fix F1) | **`RESULTS_final.md`** |
| `outputs/e4u_sizing_usd/` | round-2 E4u station sizing under USD (baseline fill of skipped cells) | **`RESULTS_final.md`** |
| `outputs/e8_nyc_fixed/` | round-2 E8 semi-real NYC (review-fixed block profile) | **`RESULTS_final.md`** |
| `outputs/e8_nyc/` | superseded E8 run (interpolated ramp profile, units fix F1); do not quote | - |
| `outputs/e2u_round3/` | **round-3 E2u** coordination value, 10 seeds, service-share constraint (33) at zeta 0.90 / 0.85, relaxed control (`zeta_feasibility.csv`, `improvement.csv`, `instances/`) | **`RESULTS_final.md`** |
| `outputs/e3u_round3/` | **round-3 E3u** transfers / separation, 5 seeds, all 60 ILP cells (600 s re-solves of the separated / written / transfers-free cells) | **`RESULTS_final.md`** |
| `outputs/e4u_round3/` | **round-3 E4u** station sizing, 6 seeds on the B sweep / default / free size, P sweep and seed-0 B x C grid complete (`summary_*.csv`, `_analysis_final.json`) | **`RESULTS_final.md`** |
| `outputs/e8_round3/` | **round-3 E8** semi-real NYC, 10 seeds x 2 sitings (`per_instance.csv`, `siting.csv`, `demand_comparison.json`, `map_seed0.png`) | **`RESULTS_final.md`** |
| `outputs/e9_bilevel/` | **round-4 E9** bi-level siting on `nyc4h_stress2`: consolidated report, `candidates.csv` / `.json`, `launch2.json`, `logs/`, shared lower-level `cache/` | **`RESULTS_E9.md`** |
| `outputs/e9_bilevel/validate/` | E9.1 exhaustive enumeration vs integrated stochastic ILP (4 candidates, 2 seeds, m = 1) | **`RESULTS_final.md`** (`agreement.json`, `layouts_m1.png`, `map_validate_m1.png`, `solve_times_m1.png`) |
| `outputs/e9_bilevel/sweep/` | E9.2 greedy + local search per budget m = 1..4, Pareto curve, integrated bound | **`RESULTS_final.md`** (`pareto.csv`, `map_sites_final.png`, `pareto_final.png`, `greedy_trajectory_final.png`; `pareto.png` draws a meaningless bound) |
| `outputs/e9_bilevel/roles/` | E9.3 role sets {SC}, {S, SC}, {S, C, SC} at m = 2, 3 | **`RESULTS_final.md`** (`roles_priced_moves.png`, `roles_components.png`, `roles_map.png`) |
| `outputs/e9_bilevel/deck/` | E9.4 proposal deck heuristic vs bi-level, m = 1..4 | **`RESULTS_final.md`** (`deck_vs_bilevel_final.png`, `map_deck_vs_bilevel.png`, `deck_demand_proxy.png`) |
| `outputs/e9_bilevel/cross/` | E9.5 cross-evaluation of 7 chosen layouts under ILP / baseline / relaxed ILP, 5 seeds | **`RESULTS_final.md`** (`cross_eval.csv`, `cross_eval_final.png`) |
| `outputs/e9_bilevel/access/` | E9.6 access row [U4] at D = 8 / 12 blocks, m = 2, 3 (D = 8, m = 3 truncated) | **`RESULTS_final.md`** (`access_map.png`, `access_coverage.png`, `access.png`, `access_search.png`) |
| `outputs/e9_bilevel/_first_attempt/` | superseded first E9 launch on `nyc4h_stress` (8 bikes); degenerate, do not quote | `README.md` (the four failures) |

The script-written `RESULTS.md` files in the round-2, round-3 and E9 directories are intermediate (some were
written from partial records; the E3u round-3 one is a stub after the script's `--analyse` step failed);
`RESULTS_final.md` is the deliverable in each. The round-3 directories supersede the round-2 ones for every
quoted number (the round-2 rows they reuse are byte-identical). The project synthesis across rounds is
`../notes/SUMMARY.md` (round 1 in sections 1-6, then "Round 2 (2026-10-12)", "Round 3 (2026-10-12/13)" and
"Round 4 (2026-10-14): bi-level station siting (E9)"); the round-3 headline numbers are also collected in
`../notes/workflow8_round3_reports_a.json`.

## Bi-level siting (E9, `ebike_swap_sim/sites_nyc.py`, `ebike_swap_sim/bilevel.py`, `experiments/e9_bilevel_siting.py`)

Design: `../notes/bilevel_siting_design.md`. Leader = planner (which candidate locations to open, role
`S` swap-only / `C` charge-only hub / `SC` co-located, spares `B_j`, chargers `C_j`, under the investment
budget (33a)); follower = the written E2 operations ILP with the facilities fixed, one solve per demand
scenario (seed). Objective `Phi = sum_j (F_j y_j + bB_j B_j + bC_j C_j) + sum_s p_s OPEX_s`; optimistic
bi-level, which collapses to one two-stage stochastic ILP when no planner-only row is present (the exact
benchmark). Family `nyc4h_stress2` (6 bikes / 36 orders, `q0 ~ U{3..6}`, B 1 / C 1 / 2.8 kW sites / 4 kW
grid; the relaunch family of `../notes/DECISIONS.md` "E9 relaunch decisions", a single SC site serves >= 70 %)
is the default; the first attempt's `nyc4h_stress` (8 bikes / 48 orders, `q0 ~ U{2..4}`, too stressed:
one-site layouts served 7 %) stays selectable with `--family nyc4h_stress`. Rules of the relaunch: swap-only
sites only next to a C / SC object (`sites_nyc.layout_admissible`, also rows of the integrated model); the
greedy starts from the best singleton by lower-level V (per-role baseline screen, exhaustive singletons as
fallback), discards moves that are infeasible or serve < `--min-served` (0.5), reports `wall budget
exhausted` / `no feasible layout` with the status counts of the priced layouts, records lower-level
exceptions as `ERROR` rows, and treats the access row [U4] as repair + report (uncovered zones are listed,
never enforced on the search). Reposition targets: `--validate` keeps the all-candidates template so that
(A) and (B) price the same arcs; the search sub-commands price per-layout libraries (open sites + depots,
E8 convention, `--reposition open_sites`).

* `sites_nyc.candidate_sites()` -- 12 candidates of the Midtown box (6 busiest restaurant cells, 3
  landmarks, 3 zone centres; Penn Station merged into L01), `make_base_instance` (every candidate in V,
  bikes at the three busiest cells, no facilities; demand byte-identical across layouts),
  `layout_instance` / `all_candidates_instance` (one E2 facility object per `(location, role)`, shuttle
  services between charge-capable and swap-capable objects), `siting_pruning(targets='all_candidates' |
  'open_sites')` (reposition targets = all candidates + depots, shared by every layout of a scenario, or the
  open sites + depots of one layout), `subset_library` (layout library derived from the all-candidates
  template, identical to `build_arcs`), `SITING_FAMILIES` / `SIZE_MENUS` / `layout_admissible`.
* `bilevel.Layout`, `LowerLevelEvaluator` (certified lower-level values, persistent JSONL cache under
  `outputs/e9_bilevel/cache/`, baseline warm starts, superset lower bound, scenario-by-scenario pruning,
  `reposition` mode, `ERROR` rows for exceptions),
  `exhaustive` (B), `greedy_local_search` (C), `deck_heuristic` (D), `integrated_stochastic_ilp` (A: one
  Gurobi model with shared `y, B, C` and one `ilp.ILPModel` sub-model per scenario through the new
  `model / prefix / facility_vars / set_objective` arguments of `ILPModel`), `cross_evaluate` (E),
  `access_sets` / `layout_covers` ([U4]).
* `experiments/e9_bilevel_siting.py --validate | --sweep | --roles | --deck | --cross | --access`
  (E9.1-E9.6), each with `--dry-run` / `--smoke` (toy siting instances, seconds) and a `--wall-budget`;
  outputs under `outputs/e9_bilevel/<sub>/` (`records.jsonl`, `results.csv`, figures, `RESULTS.md`).
  `tests/test_bilevel.py` checks, at toy scale, that the integrated ILP equals the exhaustive
  enumeration, that the greedy recovers the toy optimum, the cache, the budget, the demand invariance,
  the role semantics and the candidate rules, plus the relaunch regressions (a role set with S finds at
  least the SC_only optimum, the start is the best singleton by V, the access row reports instead of
  enforcing, wall exhaustion and exceptions are reported, not mistaken for infeasibility, and the
  `nyc4h_stress2` sanity bar). First-attempt outputs: `outputs/e9_bilevel/_first_attempt/`.

**Results (2026-10-14).** The consolidated report is `outputs/e9_bilevel/RESULTS_E9.md`; it names the source of
every number, and the authoritative numbers live in the six sub-reports
`outputs/e9_bilevel/{validate,sweep,roles,deck,access,cross}/RESULTS_final.md` with the figures in those folders
(see the Outputs index). Headline on `nyc4h_stress2` (3 seeds in the search, 5 in the cross-evaluation):

* Chosen layout at every budget m = 1..4: one co-located site `L02:SC:B3:C2` (m = 1, 52,150 USD invested) or
  `L02:SC:B4:C2` (m >= 2, 52,600 USD), V = 654.38 / 654.53 USD per 4 h window (13.2-13.5 setup + 641 opex),
  served share 0.852; budget beyond one unit unspent (51,700 / 103,850 / 156,000 USD at m = 2 / 3 / 4), the
  Pareto frontier is one point plus the 450 USD fourth spare (`sweep/`).
* A second site never pays: +11.9 to +12.2 USD per window for an S / SC site, +29.4 USD for a hub, against an
  operating saving of at most 1.09 USD; `transfers_used = 0` in all 84 solves of the roles run; role sets {SC},
  {S, SC}, {S, C, SC} give the identical optimum at m = 2 and 3 (`sweep/`, `roles/`).
* E9.1: exhaustive enumeration = integrated stochastic ILP at `L02:SC:B2:C1`, V 676.22 (4 candidates, 2 seeds,
  m = 1, menu B <= 2); integrated bound 668.04 (gap 1.21 %); at full size (5.35 M variables) the integrated
  model gives no usable bound in 600 s, so the m = 2..4 answers are heuristic incumbents (`validate/`, `sweep/`).
* Deck heuristic regret 0.68 / 12.56 / 25.53 / 38.78 USD = 0.10 / 1.92 / 3.90 / 5.93 % at m = 1..4, almost
  exactly the setup of the extra sites it opens (`deck/`).
* Access row [U4]: +12.08 USD per window (+1.85 %) and +50,450 USD for the second site L05 at D = 8 and D = 12;
  served share unchanged; 11 / 11 zones covered at D = 12, 8 / 11 at D = 8 (MN0801 is beyond 8 blocks of every
  candidate); the D = 8, m = 3 search was truncated by the wall budget (`access/`).
* Cross-evaluation on 5 seeds: location robust to the operating policy (L02 under both, L01 a tie), size not
  (the policy values the fourth spare at 47.4 USD, the coordinator at 0.15 USD); ILP beats the baseline policy by
  31.1-41.3 % on every layout; in-sample vs out-of-sample ILP opex within 4.2 USD (`cross/`).
* Structural reading: for the coordinator the fleet (6 bikes, 4 h, q0 3-6) binds, not the batteries (served
  0.852 for every layout with B >= 3), so siting moves only travel and electricity. Known artefacts: the B = 4
  answer lies outside the enumeration menu, the m >= 2 value is 0.15 USD above the m = 1 layout (local search
  restarts per budget), and the first launch (`_first_attempt/`) is degenerate and superseded.

## Pointers

* Binding decisions: `../notes/DECISIONS.md` (read first when changing semantics).
* Model text: `../notes/extracted/E2.txt`; toy: `../notes/extracted/E2_Example.txt` pp.10-15.
* Round-2 background: `../notes/cost_calibration.md`, `../notes/literature_demand_model.md`,
  `../data/MANIFEST.md`, `../notes/data/zone_weights_README.md`.
* Plan (entity mapping, baseline spec, generator spec, size estimates): `../notes/workflow1_result.json`.
* Standalone verifications: `../notes/verify/toy_e2_example.py`, `../notes/verify/identity_checks.py`.
