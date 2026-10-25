# ebike_swap_sim — API contract for `ilp.py`, `baseline.py`, `generator.py` (+ round-2 and round-5 modules)

Package root: `ebike_swap_sim/ebike_swap_sim/`. Run from `ebike_swap_sim/` with
`PYTHONPATH=.` (`pytest.ini` sets `pythonpath = .`, so `python3 -m pytest tests/ -x -q`
works as is). Equation numbers refer to `notes/extracted/E2.txt`; binding conventions
are in `notes/DECISIONS.md`. Only `ilp.py` may import gurobipy; it is reached through
the lazy attribute `ebike_swap_sim.ilp` so the package imports without Gurobi.

```python
from ebike_swap_sim import (Instance, Discretisation, Route, Bike, Order, Facility, Service,
                            toy_instance, battery_swap_p7_instance, build_arcs, ArcLibrary, Arc,
                            SINK, compute_gbar, Schedule, cost, check, metrics,
                            reconstruct_inventory, swap_counts, transfer_counts, in_transit,
                            facility_vars)
```

## 1. `or_instance.py` — data (no solver imports)

| class | fields (defaults) | notes |
|---|---|---|
| `Discretisation` | `Delta_h, H, L, eps_kwh, eta` | `p_ch_kw = eps/(eta Delta)` (19); `kwh_per_step = eps/eta` (28); `tau(T_h, distinct=True)`, `g(E_kwh)` = ceil of (1) with 1e-9 tolerance, `tau >= 1` for distinct nodes |
| `Route` | `T_h, E_kwh, d_km` | raw physical values; `Instance.routes: dict[(u,v)] -> Route`, `u != v`, missing key = no route; `(v,v)` is the implicit empty route |
| `Bike` | `id, v0, q0` | source `s_k = (v0, 0, q0)` |
| `Order` | `id, o, d, r, a, b, hp=1, hd=1, P=100, w=12, v=24, platform='default'` | `a >= r`, `b >= r`, `hp + hd >= 1`; `w`, `v` per hour (31) |
| `Facility` | `id, node, swap, charge, y=None, B=None, C=None, K=1, Cbar=0, M=1, sigma=1, P_kw=0, group=None, F=0, bB=0, bC=0, R_end=0, Fhat=0, bhat=0, chat=0` | keyed by **facility id**, several facilities may share a node. `y/B/C = None` means *free* (ILP decides); an int means fixed data. `M`, `sigma` only matter for swap sites |
| `Service` | `id, o_fac, d_fac, l, u, U, f=0, vreb=0` | endpoints are facility ids; `0 <= l < u <= H`; `vreb` scalar or list of length `L+1`; `vreb_q(q)` |
| `Instance` | `disc, nodes, routes, bikes, orders, facilities, services, P_grid={}, kappa=1, pi=2, q_res=0, rho=0, budget=None, zeta=None, options={}, meta={}` | `pi` float or `{(fac_id, t): price}`; `P_grid: {group: [kW]*H}` (missing group = unlimited) |

`Instance` helpers: `bike(k)`, `order(i)`, `facility(j)`, `service(e)`; `H`, `L`, `S`
(swap ids), `Cset` (charge ids), `N`, `groups`; `route(u,v)`, `tau(u,v)`, `g(u,v)`,
`d(u,v)` (0 for `u == v`, `None` if no route); `price(j,t)`; `theta(i, u_a)` (31);
`grid_limit(g,t)`; `option(name)`; `validate(raise_on_error=True) -> list[str]`;
`to_dict/from_dict`, `to_json/from_json`, `save/load`; `summary()`; `reindex()` after
mutating the lists. Node ids may be str/int/tuple (tuples survive JSON). Equality
(`==`) is by value, so `Instance.from_json(inst.to_json()) == inst`.

`Instance.options` is `DEFAULT_OPTIONS` updated by the data. Keys:

* arc builder (`arcs.py`): `energy_rounding` (`'per_leg'` default | `'concat'`),
  `dominance` (True), `swap_q_max` (None), `dummy_terminal_cost` (None),
  `reposition_targets` (None | set of nodes), `tau_max` (None), `start_slack` (None),
  `reachable_pruning` (False).
* model switches to be honoured by `ilp.py`: `no_transfers` (h = z = 0), `colocated`
  (treat every facility as swap+charge), `fixed_facilities` (None = fixed iff `y/B/C`
  given), `lexicographic` (min Σu first), `battery_swap_v1_bounds` (add `y <= B`,
  `C <= B`). `budget`/`zeta` (33) live on the instance itself.
* data fixings (round 5, M9): `forced_transfers` (list of `{'service', 'level'}`, written by
  `generator.add_battery_lockout`): `ilp.build_model` sets `h_e >= 1` (and `z_eq >= 1` for a
  given level) on these services (variable bounds of (10), no row changes;
  `switches['forced_transfers']` = number fixed; under `no_transfers` they are skipped and
  counted in `switches['forced_transfers_skipped']`); the baseline executes them
  (`flags['forced_transfers']`) and never uses them for its own transfer rules.

Reference instances: `toy_instance()` (E2 pp.10-15, J* = 12.5) and
`battery_swap_p7_instance()` (one co-located station, `L=2, B=C=M=1, H=4`, no orders).

## 2. `arcs.py` — time-expanded bike networks

```python
lib = build_arcs(inst, strict=True, **option_overrides)   # == ArcLibrary.build(...)
```

`Arc` (slots dataclass): `id, k, kind, src, dst, l, u, d_km, g, order=None, fac=None, theta=0.0`.

* `kind in {'wait','move','deliver','swap','term'}`; `src`/`dst` are states `(v, t, q)`;
  `dst == SINK == ('sink',)` for `term`; `l`/`u` start/end boundaries (`l = u = H` for `term`).
* `g` = energy consumed (`src_q - dst_q`) for wait/move/deliver; 0 for swap (`dst_q = L`) and term.
* `order` set on deliver arcs; `fac` set on swap arcs (facility id) and real terminal arcs;
  a dummy terminal arc has `fac=None` and `theta = dummy_terminal_cost`.
* `theta` = (31) on deliver arcs, else 0 (dummy terminal: the penalty).
* **Arc ids are global integers `0..len(lib)-1`**, bike after bike in `inst.bikes` order;
  `lib.arc(id)` returns the object; `x_ka` in the ILP should be indexed by `arc.id`.
* Every non-terminal arc strictly increases `t`, so each bike graph is acyclic and a
  unit flow satisfying (5) is one path.

Build rules (exactly `DECISIONS.md`): wait `(v,t,q)->(v,t+1,q)`, `t<H`; move per offered
route if `q >= g_r`, `t+tau_r <= H`; deliver per order from **any** start node with a route
to `o_i`: `u_a = max(t+tau_r, a_i) + hp + tau_r' + hd`, `g_a = g_r + g_r'` (`per_leg`) or
`ceil((E_r+E_r')/eps)` (`concat`), created iff `t >= r_i`, `q >= g_a`, `u_a <= H`;
swap `(v_j,t,q)->(v_j,t+sigma_j,L)` for `q < L`, `t+sigma_j <= H`, one arc per swap
*facility*; terminal `(v,H,q)->SINK` labelled `j in S` iff `q >= gbar(v,j) + q_res`
(`gbar` by Dijkstra on route energies, `lib.gbar[(v,j)]`). Facilities with fixed `y == 0`
get no swap/terminal arcs. Toy with no pruning: 72 wait, 78 move, 62 deliver, 16 swap,
7 term = 235 arcs per bike (470 total).

Lookups (all return `list[Arc]` unless noted):

| call | meaning |
|---|---|
| `lib.bikes()`, `lib.source(k)`, `lib.sink` / `SINK` | bike ids, `s_k`, sink node |
| `lib.states(k) -> set` | all nodes of bike k's network incl. `s_k` and `SINK` (one flow row (5) each) |
| `lib.arcs_of(k)`, `lib.ids_of(k)` | `A_k` |
| `lib.out_arcs(k, node)`, `lib.in_arcs(k, node)` | `delta^+_k`, `delta^-_k` for (5) |
| `lib.delivery_arcs(i, k=None)` | `A^ord_ki` (6), (30) |
| `lib.swap_arcs(j, k=None)`, `lib.swap_arcs_at(j, t, q, k=None)` | `A^sw_k(j)` (22), `A^sw_k(j,t,q)` (12) |
| `lib.terminal_arcs(k=None)` | (9); check `a.fac is None` for dummy arcs |
| `lib.arcs_of_kind(kind, k=None)` | by kind |
| `lib.find(k, kind, src, order=None, fac=None, dst=None) -> Arc | None` | exact arc lookup for the baseline (returns `None` if pruned → the baseline must not take it) |
| `lib.counts(k=None)`, `lib.summary()` | sizes |
| `lib.infeasible_bikes`, `lib.has_dummy_terminal`, `lib.options`, `lib.gbar` | diagnostics |

Pre-check: a forward reachability pass from `s_k` is always run; a bike with no reachable
real terminal arc raises `InfeasibleInstanceError` (`strict=True`, no dummy arc) or is
listed in `lib.infeasible_bikes`.

`arc_key(a) -> (kind, src, dst, order, fac)` (round 5, O1) is the identity of an arc
independent of the bike (unique within one bike network); the aggregated flow
(`aggregate.AggregatedNetwork`) merges the copies of one key across bikes of a class.

Suggested ILP mapping: `x[a.id]` binary for `a in lib.arcs`; (5) for each `k`, each
`w in lib.states(k)`; (6) over `lib.delivery_arcs(i)`; (9) `x[a.id] <= y[a.fac]` for
real terminal arcs; (12) `s_jqt = sum x over lib.swap_arcs_at(j,t,q)`; (22) `sum x over
{a in lib.swap_arcs(j): a.l <= tau < a.u} <= M_j y_j`; (29) `kappa * a.d_km`; (30)
`a.theta`. Always `OutputFlag=0`, `Threads<=3` (round-2 rule; round 1 used 4), a `TimeLimit`.

## 3. `evaluate.py` — Schedule, cost, check, metrics

```python
@dataclass
class Schedule:
    x: dict[bike_id, Iterable[int]]          # chosen arc ids per bike (any order)
    u: dict[order_id, 0|1] = {}               # unserved (6); missing = 0
    c: dict[(fac_id, q, t), int] = {}         # charged q->q+1 in slot t, q<L, t<H; missing = 0
    h: dict[svc_id, 0|1] = {}                 # service used (10)
    z: dict[(svc_id, q), int] = {}            # load at level q (10), q = 0..L
    y: dict[fac_id, 0|1] | None = None        # None -> Facility.y (None in data => 1, noted)
    B: dict[fac_id, int] | None = None        # None -> Facility.B (None => 0)
    C: dict[fac_id, int] | None = None        # None -> Facility.C (None => 0)
    n: dict[(fac_id, q, t), int] | None = None  # stock (13) t=0..H; None -> reconstructed
    meta: dict = {}
```
Helpers: `sched.path(k, lib)` (arcs sorted by `(l,u)`), `sched.chosen_arcs(lib)`,
`sched.to_dict()/from_dict()` (JSON-safe). Derived quantities (module functions):
`facility_vars(inst, sched) -> (y, B, C)`, `swap_counts(inst, lib, x) -> (s[(j,q,t)], S[(j,t)])`
(12), `transfer_counts(inst, z) -> (D[(j,q,t)], A[(j,q,t)])` (11), `in_transit(inst, z) -> [m_t]`
(24, strict `l_e < t < u_e`), `reconstruct_inventory(inst, lib, x, c, z, B=None) -> n` (13)+(16).

`cost(inst, lib, sched, end_price=None, bike_term='positive') -> dict`: `C_setup` (27),
`C_elec` (28), `C_travel` (29), `C_orders` (30) with `C_orders_parts = {unserved, response,
lateness}` (31), `C_reb` (32), `C_dummy_terminal` (0 in the written model), `total` (26). Toy
optimum: `total = 12.5 = 4 (travel) + 0.1 (elec) + 0 (unserved) + 6 (response) + 2.4 (reb)`.
Round 5 (M1) adds three reporting keys that are NOT part of (26): `C_end_adjust`,
`C_end_adjust_parts` and `total_end_adjusted = total + C_end_adjust`, where
`C_end_adjust = pi_ref (eps/eta) [sum_j sum_q (L - q)(n_jqH - n_jq0) + sum_k (q0_k - q_k(H))^+]`
(`end_state_adjustment(inst, lib, sched, end_price=None, bike_term='positive'|'signed'|'none')`;
`end_reference_price(inst, end_price=None)` = argument, `meta['end_price']`, else the mean of
`pi_jt` over `C x T`; `bike_end_levels(inst, lib, sched)`). `total` is unchanged, so the ILP
self-certification `cost == objective` still holds.

`check(inst, lib, sched) -> dict`:
`{'ok', 'n_violations', 'families': {name: {'count', 'examples': [str]}}, 'identity_24_ok',
'notes', 'n_source': 'given'|'reconstructed'}`. Family names: `'arcs'`, `'(5)'`, `'(6)'`,
`'(7)-(8)'`, `'(9)'`, `'(10)'`, `'(12)'`, `'(13)'`, `'(14)'`, `'(15)'`, `'(16)'`, `'(17)'`,
`'(18)'`, `'(20)'`, `'(21)'`, `'(22)'`, `'(24)'`, `'(33)'`, `'domain'`. When `sched.n` is given
it is compared entry-by-entry with the (13) recursion; otherwise the recursion is used for
(14), (15), (17), (18), (24). The baseline should report (9), (17), (18) violations rather
than enforce them; this checker lists them like every other family.

`metrics(inst, lib, sched) -> dict`: `served_share`, `n_served/unserved`, `mean/max_response_h`,
`mean/max_lateness_h`, `n_late`, `bike_km`, `n_swaps/moves/waits`, `swaps_per_facility`,
`wait_before_swap` (queue proxy), `kwh_purchased`, `kwh_stored`, `charge_steps_facility`,
`peak_kw_facility`, `peak_kw_group`, `transfers_used`, `batteries_moved(_by_level)`,
`in_transit`, `full_stock[j]` (`n_jLt`, t = 0..H), `stock[j]` (`N_jt`), `stockout_slots`,
`end_full_total`, `end_target_shortfall`, `per_platform`, `bike_end_levels`, `facility_vars`;
round 5: `r5` = `metric_pack(inst, lib, sched)` (A3: `sbur`, `min_sbur`, `mean_sbur`,
`swaps_per_storage_slot`, `bsr`, `bsr_unblocked`, `batteries_saved` / `batteries_saved_total`,
station time per swap, detour km / min, `reserve_breach_bikes`, `stranded_bikes`,
`energy_refused_orders`, `outage_rate`, `empty_km` / `empty_km_per_bike_hour` / `empty_km_share`,
`peak_kw_network`, `peak_kw_facility`, `kwh_by_price`, `peak_kw_by_price`; scalar keys listed in
`R5_SCALAR_KEYS`), and, only on a lock-out instance (M9, `meta['lockout']['sink']`), `lockout`
(`locked_batteries`, `forced_executed`, `end_full_total_excl_sink`, `end_share_excl_sink`,
`transfers_used_excl_forced`, ...: the stock metrics without the dummy sink, since (18) as
written counts it).

## 4. Conventions every module must respect

* Timing (Section 5 / DECISIONS): `n_jqt` is stock after arrivals at `t`, before new actions;
  bike returns enter stock at `t+1`; a transported battery arriving at `t` is usable at `t`;
  charging in slot `t` finishes at `t+1`; `A_jq0 = D_jqH = 0`; (22) counts `[l_a, u_a)`.
* Fixed zeros: no `c` outside `j in C`, `q < L`, `t < H`; no `s/S` outside `S`. Do not create
  variables for them; `evaluate` treats missing keys as 0 and flags nonzero entries.
* The baseline must take arcs only through `lib.find(...)` so that it is never allowed an
  action the ILP cannot take; the resulting `Schedule` is priced and checked with the same
  functions and can be injected as a MIP start (`x`, `u`, `c`, `h`, `z`).
* Generators must produce an `Instance` that passes `validate()` and round-trips through JSON
  (`Instance.load(path)` must yield the byte-identical instance for ILP and baseline).
* Cost units are selected per instance by the R2.1 `cost_variant` switch
  (`costs.load_cost_calibration`): `toy` = E2 p.14 units (round-1 instances, not window-scaled),
  `usd_A` / `usd_sunk` (default of the round-2 families) / `usd_B` / `usd_low` / `usd_high` in USD
  with `F, F_hub, bB, bC` scaled by `window_h / 4`. The coefficients actually used are recorded
  in the flat `Instance.meta['costs']` by **both** builders (`generator.make_synthetic_instance`
  and `data_nyc.make_nyc_instance`: `variant, window_h, window_scale, source, kappa, pi, pi_peak,
  F, F_hub, bB, bC, Fhat, bhat, chat, P, w, v, f, vreb, q_res, rho`); `Delta_h` and `eps_kwh`
  carry the physics. The model itself is unit-agnostic. `bB` carries a one-off initial charge
  (0.213 $, `costs.BB_INITIAL_CHARGE_USD`) that is window-scaled with the rest per R2.1
  (documented in `cal['notes']`, not corrected).
* Time profiles are block profiles evaluated as step functions (`generator.block_profile`);
  a 24-list passed to `TimeDependentGenerator` is interpolated between hour tops and must not
  be used for the R2.2 profile (`data_nyc.assumed_block_config` is the sampling object,
  `meta['hourly_profile_used'] = {'kind': 'block_step', 'config', 'hourly_density'}`).

## 5. Round-2 modules (DECISIONS R2.1-R2.4)

* `costs.py` — `load_cost_calibration(path=None, variant='usd_sunk', window_h=4.0)` ->
  `{'variant', 'window_h', 'window_scale', 'source', 'costs' (keys of
  `generator.DEFAULT_COSTS` minus `q_res`/`rho`), 'demand_spec' {P, w, v}, 'services_spec'
  {f, vreb}, 'notes' (list; the bB initial-charge scaling caveat when `window_scale != 1`)}`; `cost_variants()`, `flat_coefficients(cal)`, `apply_cost_calibration(cal, costs,
  demand_spec, services_spec)` (explicit keys win), `variant_table()`. `KeyError` for unknown
  variants. `data_nyc.cost_variant_params` is a thin wrapper that adds `q_res` / `rho` and raises
  `ValueError`.
* `generator.make_synthetic_instance(..., window_h=, window_start_hour=, orders_per_bike_hour=,
  init_frac=, cost_variant=, kaggle_calibrated=, time_profile=, day_type=, round2=)` — round-2
  mode is entered by `window_h` (or `round2=True`): `H = window_h * 60 / Delta_min`, `n_orders =
  round(orders_per_bike_hour * n_bikes * window_h)`, facilities `DEFAULT_FACILITIES_SPEC_R2`
  (B 3 / C 2), `q0 ~ U{4..7}`, Kaggle order attributes (`a_i = r_i + ceil(prep/Delta)`, `b_i =
  a_i + 5`), the assumed time profile `TIME_PROFILE_R2` (status `assumption`). Legacy calls
  (`H` given, no `window_h`) are byte-identical to round 1. Meta gains `round2`, `cost_variant`,
  `costs`, `time_profile`, `kaggle_calibration`, per-order `cuisine` / `rank`. With `pi_peak`
  set, the price peak window is `facilities_spec['price_peak_hours']` (default = the grid-limit
  `peak_hours` (18, 20); Con Edison TOU = (8, 22)), recorded in `meta['price_peak_hours']`.
* `baseline.py` — `BaselineParams` defaults are the R2.3 rules: `stock_aware_site=True`,
  `charge_rule='DEMAND_AWARE'` (`charge_lead=12`, `charge_lookback=12`, `charge_reserve=None` ->
  `R_end_j y_j`, `hub_charge_rule='HIGH_FIRST'` at charge-only hubs because their literal
  forecast is 0), `jit_dispatch=True`, `swap_on_reach_refusal=True`; `'ASAP'` is an alias of
  `HIGH_FIRST`. `BASELINE_VARIANTS` / `baseline_variant_params(name, **overrides)` give
  `default` / `round1` / `legacy`. New flags: `stock_aware_reroutes`, `stock_aware_fallbacks`,
  `charge_rule_effective`, `demand_aware` (per-site forecast / need / charged / ASAP cap).
  The DEMAND_AWARE reserve covers (17) only, so the default schedule may report (18);
  `experiments.common.feasible_mip_start` picks a clean variant schedule as the Gurobi start.
* `data_nyc.py` (no gurobipy) — `StudyBox` (projection, snapping, `make_grid`), pure-python
  point-in-polygon, `ZoneWeights` protocol (`weight_at(lat, lon)` = density per km^2,
  `zones()`, optional `zone_at`, optional `meta()`), `GeoDaZoneWeights` (fallback, NTA-2010
  codes, warning), `load_dohmh` / `restaurants_in_box` / `CUISINE_MAP` / `NYCRestaurantSampler`
  (implements `generator.RestaurantSampler`), `NYCDestinationSampler` (implements
  `generator.DestinationSampler`), crash / counter loaders, `default_zone_weights(box)` (ACS
  when available, else GeoDa; the GeoDa fallback uses `N_z = popover18`) and
  `make_nyc_instance(seed, n_bikes, window_h, orders_per_bike_hour, cost_variant, box, n_sites,
  site_latlon, ..., zone_weights, restaurant_sampler, cuisine_map_overrides, pruning)` ->
  validated, JSON-round-tripping `Instance` with `meta['semi_real'] = True`,
  `meta['geometry_caveat']`, `meta['zone_weights_source'/'zone_weights_warning'/'zone_weights_vintage']`,
  the flat `meta['costs']`, `meta['hourly_profile_used']` (`kind = 'block_step'`: releases are
  sampled from `assumed_block_config()`, the R2.2 step profile), `meta['n_restaurants_unmapped_in_box'
  / 'unmapped_share_in_box' / 'unmapped_cuisines_in_box' / 'cuisine_map_overrides']` (the DOHMH
  rows in the unreachable `other` class; `CUISINE_MAP_CAFES_AS_AMERICAN` / `CUISINE_MAP_REGIONAL_TO_KAGGLE`
  are the sensitivity maps), generator-compatible `meta['restaurants'] / ['depots']` (so
  `generator.default_pruning` works) and `options['node_zone']`.
* `acs_weights.py` (no gurobipy) — `ACSZoneWeights(paths, box, food_insecurity=False,
  student_cap=None, gq_correction=False, fallback='auto'|'never'|'force')` (`gq_correction`:
  `N_z = pop18 (1 - gq_share)`, the note's group-quarters correction, OFF by default, recorded
  as `meta['zone_weights_gq_correction']`; the table column `N_z` is the base used) implementing `ZoneWeights` on the NTA-2020
  polygons (`source='acs_2020_24_literature'`, codes like `MN0501`; wraps `GeoDaZoneWeights` in
  fallback mode), `compute_zone_weights(raw)`, `weights_table()`, `write_zone_weights()`
  (-> `notes/data/zone_weights_manhattan.csv`, README); CLI `python -m ebike_swap_sim.acs_weights`.
* `experiments/common.py` — `FAMILIES` adds `usd4h`, `usd4h_large`, `usd4h_toyunits`, `usd8h`
  (generator round-2 mode) and `nyc4h` (`builder: 'nyc'` -> `data_nyc.make_nyc_instance`);
  `R2_FAMILIES`; `PRUNING_NYC` (facility / depot targets only + `reachable_pruning`) used by
  `pruning_for` for semi-real instances (it restricts the ILP only: upper bound on the written
  optimum, see the `PRUNING_NYC` comment); `THREADS = 3`; `BASELINE_VARIANTS` maps `baseline` /
  `baseline_round1` / `baseline_legacy` onto `baseline.BASELINE_VARIANTS`; `feasible_mip_start`
  (parameter errors of a fallback variant are recorded in `base['mip_start_fallback_errors']`,
  other exceptions propagate), `MIP_START_FALLBACKS`; `run_pair(..., start_fallback=True)`
  records `mip_start_variant`, `baseline_pruned_fallbacks` / `baseline_stranded` /
  `baseline_late_suppressed`, `baseline_policy_reserve_source`, `n_unservable`,
  `baseline_` / `ilp_served_share_servable`, `mip_start_fallback_errors`, `demand_md5`.
  `relax_end_targets` keeps `meta['written_R_end']` / `meta['written_rho']`, and
  `run_baseline_case` on such a copy passes the written `R_end_j` as `charge_reserve` unless
  one is given (`rec['policy_reserve_source']` in `{'R_end', 'written_R_end', 'params'}`), so the
  R2.3 policy is identical under both target settings. Helpers: `unservable_orders(inst, lib)`,
  `demand_key(inst, include_bike_nodes=True, include_facilities=False)`, `demand_md5`,
  `baseline_pruning_flags(flags)`, `pair_anomalies(rec)`.

## 6. Round-5 modules and options (`notes/reading_to_model.md`; DECISIONS "R5 implementation notes")

No E2 equation changes: every item below is a parameter, data, policy, wrapper or solver
option. Plan item ids (A1-A7, M1-M10, O1) are cited in the docstrings.

* `config.py` (A1) -- `ENERGY_CALIBRATIONS` (`'legacy'`, `'ebaas'`: 25 Wh/km = eBaaS 40 km/kWh,
  0 Wh per signal, 0.6 Wh per metre of climb, `eps` 25 Wh, `L` 24, `energy_rounding='concat'`,
  `q_res` 50 Wh = 2 levels, `sigma` 1 slot), `EBAAS_FACTS`, `HOME_CHARGING_DEFAULTS`,
  `energy_calibration(name='ebaas', Delta_h=5/60, eta=0.9, **overrides)` (adds `L`, `battery_wh`,
  `eps_kwh`, `q_res`, `p_ch_kw`).
* `costs.py` (M5, A6, M10) -- `TARIFFS` / `load_tariff('tou'|'tou_summer'|'flat')` (pi 0.132,
  pi_peak 0.442 / 0.74 summer, `price_peak_hours (8, 22)`), `crf`, `allocate_per_window`,
  `FLEET_COST_DEFAULTS`, `allocated_bike_cost`, `pack_cost_scaling`, `position_cost_per_window`,
  `demand_charge_per_window`, `demand_charge_proxy`.
* `generator.py` -- `make_synthetic_instance(..., energy_calibration=, tariff=, home_charging=,
  lockout=)` (all `None` by default: round-1..4 families regenerate byte-identically,
  `tests/test_r5_instances.py` asserts the md5s); `services_spec={'mode': 'cyclic', ...}` (M8);
  `R5_TIME_PROFILE` and `R5_FAMILIES` (`r5_stress4h`, `r5_stress8h`, M5), `make_r5_instance(family,
  seed, **overrides)` (`meta['r5']` with `riding_intensity`); `home_charging_counterfactual` (A5);
  `add_battery_lockout` / `apply_forced_transfers` (M9; `ilp.build_model` now applies the fixings
  itself, `apply_forced_transfers` stays as an idempotent helper); `fleet_spare_pack_grid`,
  `make_fleet_sweep_instance` (A6); `swap_position_variants`, `site_power_cap_sweep`,
  `charger_speed_variants` (M10).
* `evaluate.py` (A3, M1, M9) -- see section 3 (`metric_pack`, `end_state_adjustment`,
  `cost(...)['C_end_adjust' / 'total_end_adjusted']`, `metrics(...)['r5' / 'lockout']`).
* `baseline.py` (M2-M4) -- `BaselineParams` gains `swap_rule ('THRESHOLD'|'RANGE')`,
  `range_margin`, `range_cap_frac`, `range_typical`, `reservation`, `reservation_timeout`,
  `transfer_lookback`, `transfer_lead`, `transfer_prior_rate`, `stockout_cost_mode`,
  `orders_per_stockout`, `stockout_wait_slots`, `transfer_load_cap`, `transfer_reserve`,
  `site_choice ('NEAREST'|'LOGIT')`, `logit_alpha/beta/gamma/scale`, `choice_seed`,
  `expected_wait`; `TRANSFER_RULES` adds `'COST_AWARE'`. Defaults reproduce round 2 bit for bit.
  `BASELINE_VARIANTS`: `default` (= `r2`), `round1`, `legacy`, `r5_range`, `r5_transfer`,
  `r5_selfish`, `r5` (RANGE + reservation + COST_AWARE + stock-aware + DEMAND_AWARE);
  `DEFAULT_VARIANT_NEW = 'r5'`. New functions `poisson_sf`, `logit_probabilities`,
  `run_selfish_equilibrium(inst, arcs, params=None, max_iter=10, tol=0.01, averaging='msa')`,
  `select_compliant_bikes`, `simulate_compliance(inst, arcs, plan, alpha_c, ..., station_plan=
  'plan'|'policy')`. Flags (all variants): `swap_rule_effective`, `site_choice_effective`,
  `outages`, `range_rule`, `site_choice`, `cost_aware`; `forced_transfers` on lock-out instances.
  Information sets are non-anticipative (documented per rule, tested).
* `aggregate.py` (O1, no gurobipy) -- `AggregatedNetwork(inst, lib, mode='auto'|'single'|'groups',
  prune=True)` (`arcs`, `commodities`, `ub`, `term_ub`, `aggregate_x`, `decompose`, `summary`),
  `aggregate_network`, `decompose_flow`, `AggregationError` (raised if two bikes' copies of one
  arc key differ). `ilp.build_model(..., aggregate=False, aggregate_mode='auto')` and
  `ilp.solve(..., aggregate=...)`: with `aggregate=True`, `x` is keyed by aggregated arc id and
  holds integer flows, the returned `Schedule` is per bike (path decomposition) and is certified
  by `evaluate.check` / `cost` exactly as before; `stats` gains `aggregate` and `n_agg_arcs`.
  `ilp.build_submodel(inst, lib, model, *, facility_vars, prefix, aggregate=True, ...)` is the
  shared-model scenario copy used by `bilevel.integrated_stochastic_ilp`. Exactness requires that
  no E2 parameter depends on the bike beyond `A_k` and `s_k` (true today).
* `rolling.py` (M7) -- `rolling_horizon(inst, W=None, k=None, lookahead_min=0.0, *, lib=None,
  final_targets='written'|'m1'|'relaxed', window_targets='last'|'every', forecast=None,
  n_scenarios=1, aggregate=False, threads=3, time_limit=60.0, ...) -> RollingResult` (windows
  solve the unchanged E2 ILP; the carried state enters as RHS / bounds of (13), (16), (22) and
  wait-arc bounds; the stitched day schedule is priced and checked by `evaluate`),
  `window_instance`, `BootstrapForecast(inst, pool='all'|'released')`, `forecast_facility_plan`,
  `offline_vs_online`, `lookahead_slots`, `hard_families_ok`, `HARD_EXEMPT_FAMILIES`.
* `rl_env.py` (A7, needs gymnasium) -- `StationEnv(factory=None, instances=None, config=EnvConfig)`:
  rider steps 1-7 from the baseline (`rider_variant`, default `'r2'`), the agent sets charging per
  charge site (bounded by (20)) and loads per service (bounded by `U_e`, (10)); clipped by (14),
  (15), (21), reserved full batteries (M2) never leave, forced M9 transfers are executed as data;
  reward = `-(Phi_{t+1} - Phi_t) * reward_scale` with `Phi` = `evaluate.cost` of the partial
  schedule (+ the M1 adjustment at `H`, same reference price as `evaluate.end_reference_price`).
  `make_family_factory`, `rider_params`, `charge_cap`, `adjusted_cost`, `end_state_adjustment`.
* `sites_nyc.py` / `data_nyc.py` (M6) -- `data_nyc.MANHATTAN_BOX`, `MANHATTAN_ENTRY_POINTS`,
  `StudyRegion`, `REGIONS` (`'manhattan_s110'`), `resolve_region`, `RegionZoneWeights`,
  `region_restaurants`, `entry_point_depots`; `sites_nyc.R5_MANHATTAN_FAMILY` (`'r5_manhattan'`),
  `R5_MANHATTAN_PARAMS`, `SITING_POST`, `lattice_candidates` (2 km cells), `family_candidates`,
  `family_depots`, `family_access_D`, `access_radius_blocks` (eBaaS 2 km coverage).
* `bilevel.py` (M4, A4, O1) -- `POLICIES = ('ilp', 'baseline', 'selfish')`, `cross_evaluate`
  under all three followers, `compliance_sweep`, `RULES` / `rule_layout` / `rule_baselines`
  (CSCD / CSTC / CSAV), `present_day_sites`, `capacity_matched_layout`, `LEVERS` / `lever_table`,
  `apply_variant`, `aggregate_available`; `LowerLevelEvaluator(aggregate=...)`.
* `experiments/common.py` -- "R5 sizes": `R5_SIZES` registered in `FAMILIES` with
  `builder: 'r5'` (`make_instance` calls `generator.make_r5_instance`; `meta['r5_family']`),
  `R5_FAMILY_NAMES`, `R5_PRUNING` (reachable pruning, applied by `pruning_for` to round-5
  synthetic instances only), `R5_ILP_KWARGS = {'aggregate': True}`; baseline variants
  `baseline_r5`, `baseline_r5_range`, `baseline_r5_transfer`, `baseline_r5_selfish`; M1 helpers
  `end_target_copy`, `boundary_grid`, `boundary_label`, `BOUNDARY_RHOS`, `BOUNDARY_R_ENDS`,
  `PERIODIC_LABEL` (`relax_end_targets` = the `rho0_R0` cell); `flatten_r5`; `run_pair` records
  gain `*_C_end_adjust*`, `*_total_end_adjusted`, `gap_vs_*_pct_end_adjusted`, `baseline_r5_*`,
  `ilp_r5_*`, `boundary_variant`.
* Scripts: `experiments/rolling_horizon.py` (E7: offline / rolling / forecast / baseline,
  `--dry-run`, `--analyse`), `experiments/a7_rl.py` (`train | evaluate | all`),
  `experiments/e9_bilevel_siting.py --manhattan | --baselines | --levers | --policy-aware |
  --compliance` (default family `r5_manhattan`).
