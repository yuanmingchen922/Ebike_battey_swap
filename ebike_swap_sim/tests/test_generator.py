"""Tests of the synthetic instance generator (``ebike_swap_sim.generator``):
determinism / JSON round-trip, route coverage, OD modules, facility and service
layout, arc-library build with terminal pre-check (9), and the size table for
the (n_bikes, n_orders, H, L) families with the recommended pruning."""
from __future__ import annotations

import math

import numpy as np
import pytest

from ebike_swap_sim import Instance, build_arcs
from ebike_swap_sim.generator import (
    DEFAULT_CUISINES,
    DemographicDestinationSampler,
    RestaurantTypeSampler,
    TimeDependentGenerator,
    anchor_lattice,
    default_pruning,
    estimate_arcs,
    make_synthetic_instance,
    node_zone_map,
    synthetic_zone_demographics,
    zone_centres,
)
from ebike_swap_sim.network import GridNetwork


# ---------------------------------------------------------------------------
# determinism and serialisation
# ---------------------------------------------------------------------------
def test_deterministic_and_json_round_trip():
    a = make_synthetic_instance(seed=3, n_bikes=4, n_orders=12, H=24, L=8)
    b = make_synthetic_instance(seed=3, n_bikes=4, n_orders=12, H=24, L=8)
    assert a.to_json() == b.to_json()                     # byte-identical twice
    assert a == b
    c = make_synthetic_instance(seed=4, n_bikes=4, n_orders=12, H=24, L=8)
    assert c.to_json() != a.to_json()                     # the seed matters
    loaded = Instance.from_json(a.to_json())
    assert loaded == a and loaded.to_json() == a.to_json()
    assert loaded.validate() == []
    assert node_zone_map(loaded) == node_zone_map(a)
    assert set(node_zone_map(a)) == set(a.nodes)


def test_default_medium_family_structure():
    inst = make_synthetic_instance(seed=1)                # defaults: K=10, I=30, H=24, L=12
    assert inst.validate() == []
    assert inst.summary()["bikes"] == 10 and inst.summary()["orders"] == 30
    d = inst.disc
    assert d.H == 24 and d.L == 12 and d.Delta_h == pytest.approx(5 / 60)
    assert d.eps_kwh == pytest.approx(0.05) and d.p_ch_kw == pytest.approx(0.05 / (0.9 / 12))
    assert len(set(inst.nodes)) == len(inst.nodes)
    # all ordered pairs of V are offered (E2 p.10: unique shortest route per pair)
    assert len(inst.routes) == len(inst.nodes) * (len(inst.nodes) - 1)
    for (u, v), r in inst.routes.items():
        assert r.T_h == pytest.approx(r.d_km * 1000 / 250 / 60)   # T_h = length_m / 250 / 60
        assert r.E_kwh >= 0.012 * r.d_km - 1e-12                   # >= 12 Wh/km
    # facilities: co-located at zone centres, fixed sizes, one shared grid group
    meta = inst.meta
    assert [f.node for f in inst.facilities] == [tuple(s) for s in meta["sites"]]
    assert all(tuple(s) in [tuple(z) for z in meta["zone_centres"]] for s in meta["sites"])
    for f in inst.facilities:
        assert f.swap and f.charge and (f.y, f.B, f.C) == (1, 4, 3)
        assert (f.K, f.Cbar, f.M, f.sigma, f.P_kw, f.R_end) == (8, 6, 1, 1, 4.0, 1)
        assert (f.F, f.bB, f.bC) == (20.0, 3.0, 2.0) and f.group == "sites"
    assert set(inst.P_grid) == {"sites"} and len(inst.P_grid["sites"]) == 24
    assert min(inst.P_grid["sites"]) == 6.0 and max(inst.P_grid["sites"]) == 8.0  # peak 18-20 h
    assert inst.services == []                            # no hubs -> no shuttles
    assert (inst.kappa, inst.pi, inst.q_res, inst.rho) == (1.0, 2.0, 1, 0.5)
    # bikes: depots round robin, q0 in ceil(0.4 L)..L
    depots = [tuple(x) for x in meta["depots"]]
    assert len(depots) == 2
    for k, b in enumerate(inst.bikes):
        assert b.v0 == depots[k % 2] and math.ceil(0.4 * 12) <= b.q0 <= 12
    # orders: a = r + ceil(prep / Delta), b = r + 9, hp = hd = 1, anchors / restaurants
    anchors = {tuple(a) for a in meta["anchors"]}
    restaurants = {tuple(n) for n, _ in meta["restaurants"]}
    assert len(anchors) == 16 and len(restaurants) == 6
    om = {o["id"]: o for o in meta["orders"]}
    for o in inst.orders:
        assert o.d in anchors and o.o in restaurants
        assert o.a == o.r + math.ceil(om[o.id]["prep_min"] / 5 - 1e-9) and o.b == o.r + 9
        assert o.hp == 1 and o.hd == 1 and (o.P, o.w, o.v) == (100.0, 12.0, 24.0)
        assert o.platform in ("A", "B", "C") and 0 <= o.r < 24 - 8
        assert 5 <= om[o.id]["prep_min"] <= 30
    assert [o.r for o in inst.orders] == sorted(o.r for o in inst.orders)
    # meta records the generator parameters
    p = meta["params"]
    assert p["seed"] == 1 and p["n_bikes"] == 10 and p["facilities_spec"]["mode"] == "colocated"
    assert meta["p_ch_kw"] == pytest.approx(d.p_ch_kw)


def test_every_order_has_routes_from_everywhere():
    inst = make_synthetic_instance(seed=2, n_bikes=4, n_orders=12, H=24, L=8)
    for o in inst.orders:
        assert inst.route(o.o, o.d) is not None
        for v in inst.nodes:
            assert inst.route(v, o.o) is not None
            assert inst.tau(v, o.o) >= (1 if v != o.o else 0)


def test_separated_mode_hubs_services_and_options():
    inst = make_synthetic_instance(seed=5, n_bikes=6, n_orders=15, H=24, L=12,
                                   facilities_spec={"mode": "separated", "n_hubs": 2},
                                   services_spec={"site_site": True},
                                   costs={"pi_peak": 3.0}, pruning={"tau_max": 4})
    assert inst.validate() == []
    sites = [f for f in inst.facilities if f.swap]
    hubs = [f for f in inst.facilities if not f.swap]
    assert len(sites) == 3 and len(hubs) == 2
    for f in sites:
        assert not f.charge and f.C == 0 and f.Cbar == 0 and f.group is None
    for f in hubs:
        assert f.charge and (f.K, f.Cbar, f.P_kw, f.C, f.B) == (30, 20, 12.0, 6, 4)
        assert f.F == 40.0 and inst.P_grid[f.group] == [12.0] * 24
    assert set(inst.P_grid) == {"hub1", "hub2"}
    # shuttles hub <-> site every 6 slots from t = 2, duration ceil((route + 10 min)/Delta)
    ids = {f.id: f for f in inst.facilities}
    hub_svcs = [s for s in inst.services if s.o_fac.startswith("HUB") or s.d_fac.startswith("HUB")]
    assert hub_svcs and all(s.l % 6 == 2 for s in hub_svcs)
    departures = {(s.o_fac, s.d_fac, s.l) for s in hub_svcs}
    for h in hubs:
        for st in sites:
            assert (h.id, st.id, 2) in departures and (st.id, h.id, 2) in departures
    for s in inst.services:
        assert 0 <= s.l < s.u <= 24 and (s.U, s.f, s.vreb) == (6, 5.0, 0.2)
        a, b = ids[s.o_fac].node, ids[s.d_fac].node
        route_min = inst.route(a, b).d_km * 1000 / 250
        assert s.u - s.l == max(1, math.ceil((route_min + 10) / 5 - 1e-9))
    site_svcs = [s for s in inst.services if s.o_fac.startswith("S") and s.d_fac.startswith("S")]
    assert site_svcs and all(s.l % 12 == 2 for s in site_svcs)
    # peak price dict, pruning option travels with the instance, JSON round-trip
    assert isinstance(inst.pi, dict)
    assert inst.price("HUB1", 0) == 2.0 and inst.price("HUB1", 6) == 3.0   # 17:30 off-peak, 18:00 peak
    assert inst.options["tau_max"] == 4
    assert Instance.from_json(inst.to_json()) == inst
    # free facilities variant validates and carries None decisions
    free = make_synthetic_instance(seed=5, n_bikes=2, n_orders=4, facilities_spec={"fixed": False})
    assert all(f.y is None and f.B is None and f.C is None for f in free.facilities)
    assert free.validate() == []


def test_peak_price_hours():
    inst = make_synthetic_instance(seed=5, n_bikes=2, n_orders=4, H=36, costs={"pi_peak": 3.0})
    # window starts 17:30; peak 18:00-20:00 = slots 6..29
    assert inst.price("S1", 5) == 2.0 and inst.price("S1", 6) == 3.0
    assert inst.price("S1", 29) == 3.0 and inst.price("S1", 30) == 2.0


# ---------------------------------------------------------------------------
# OD modules
# ---------------------------------------------------------------------------
def test_time_dependent_generator():
    gen = TimeDependentGenerator("weekday", (17.5, 19.5), target=40)
    rng = np.random.default_rng(0)
    exact = gen.sample(rng, 40)
    assert len(exact) == 40 and exact == sorted(exact) and 0 <= min(exact) and max(exact) < 120
    # expected count equals the target: average of Poisson samples
    counts = [len(gen.sample(rng)) for _ in range(300)]
    assert abs(np.mean(counts) - 40) < 2.0
    # dinner peak is busier than the night and the profile is periodic
    assert gen.rate(19.0) > gen.rate(16.0) > gen.rate(3.0) and gen.rate(27.0) == gen.rate(3.0)
    wk = TimeDependentGenerator("weekend", (18.0, 20.0), 10)
    assert wk.rate(19.0) / wk.rate(12.5) == pytest.approx(1.4)
    with pytest.raises(ValueError):
        TimeDependentGenerator([1.0] * 23, (17.5, 19.5), 10)


def test_destination_and_restaurant_samplers():
    rng = np.random.default_rng(1)
    net = GridNetwork(20, 20, 150.0, 0.5, 4, rng)
    demo = synthetic_zone_demographics(net.n_zones, rng)
    anchors = anchor_lattice(net, 5)
    assert len(anchors) == 16 and anchors == zone_centres(net)
    dest = DemographicDestinationSampler(net, demo, anchors)
    assert demo.weight.sum() == pytest.approx(1.0)
    draws = [dest.sample(rng) for _ in range(200)]
    assert all(d in anchors for d in draws) and len(set(draws)) > 4
    restaurants = [((3, 3), "pizza"), ((16, 3), "chinese"), ((10, 16), "fine_dining"), ((4, 15), "pizza")]
    pref = np.full((net.n_zones, 3), 1 / 3)
    rs = RestaurantTypeSampler(restaurants, list(DEFAULT_CUISINES), pref, DEFAULT_CUISINES, 5.0, 3)
    for _ in range(50):
        node, prep = rs.sample(rng, (7, 7), dest.zone_of((7, 7)))
        assert node in {n for n, _ in restaurants} and 5.0 <= prep <= 30.0
    # cuisine with a single restaurant: pizza preference forces the nearest pizza place
    only_pizza = np.zeros((net.n_zones, 3)); only_pizza[:, 0] = 1.0
    rs2 = RestaurantTypeSampler(restaurants, list(DEFAULT_CUISINES), only_pizza, DEFAULT_CUISINES, 5.0, 1)
    assert rs2.sample(rng, (2, 2), 0)[0] == (3, 3)


# ---------------------------------------------------------------------------
# arc library: terminal pre-check and size table
# ---------------------------------------------------------------------------
def test_arc_library_builds_for_default_medium_family():
    inst = make_synthetic_instance(seed=1)
    pr = default_pruning(inst)
    targets = pr["reposition_targets"]
    assert {tuple(n) for n, _ in inst.meta["restaurants"]} <= targets
    assert {f.node for f in inst.facilities} <= targets and {b.v0 for b in inst.bikes} <= targets
    assert pr["tau_max"] == 4 and pr["start_slack"] == 6
    lib = build_arcs(inst, strict=True, **pr)          # raises if a bike cannot reach a terminal arc
    assert lib.infeasible_bikes == [] and len(lib) > 0
    assert all(a.dst[0] in targets for a in lib.arcs_of_kind("move", k=1))
    # sampled estimate agrees with the full build (per-bike specs are bike-independent)
    est = estimate_arcs(inst, pr, sample_bikes=2)
    assert est["extrapolated"] and est["n_arcs"] == len(lib)
    assert est["binaries"] == len(lib) + len(inst.orders) + len(inst.services)


SIZE_FAMILIES = [(4, 12, 24, 8), (8, 24, 24, 8), (10, 30, 24, 12)]


@pytest.mark.parametrize("n_bikes,n_orders,H,L", SIZE_FAMILIES)
def test_size_table(n_bikes, n_orders, H, L):
    inst = make_synthetic_instance(seed=1, n_bikes=n_bikes, n_orders=n_orders, H=H, L=L)
    est = estimate_arcs(inst, default_pruning(inst), strict=True)
    kinds = {k: int(round(v)) for k, v in est["per_kind_per_bike"].items()}
    print(f"\n(n_bikes, n_orders, H, L) = {(n_bikes, n_orders, H, L)}: |V| = {len(inst.nodes)}, "
          f"arcs/bike = {est['arcs_per_bike']:.0f} {kinds}, x binaries = {est['n_arcs']}, "
          f"total binaries = {est['binaries']}, integers = {est['integers']}, "
          f"flow rows = {est['flow_rows']}")
    assert est["infeasible_bikes"] == [] and not est["extrapolated"]
    assert est["n_arcs"] == round(est["arcs_per_bike"] * n_bikes)
    assert est["binaries"] == est["n_arcs"] + n_orders + len(inst.services)
    assert est["integers"] == len(inst.facilities) * (L + 1) * (H + 1) + len(inst.Cset) * L * H


# ---------------------------------------------------------------------------
# round 2 (DECISIONS.md R2.1 / R2.2): byte-identical round-1 families, USD
# families, Kaggle-calibrated order attributes, time-of-day profile, meta
# ---------------------------------------------------------------------------
import hashlib  # noqa: E402
import sys  # noqa: E402
from collections import Counter  # noqa: E402

from ebike_swap_sim.generator import (  # noqa: E402
    DEFAULT_FACILITIES_SPEC,
    DEFAULT_FACILITIES_SPEC_R2,
    KaggleRestaurantSampler,
    R2_DEFAULTS,
    TIME_PROFILE_R2,
    apportion_counts,
    block_profile,
    load_kaggle_calibration,
    profile_integral,
)

_HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
_ROOT = __import__("os").path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from experiments import common as C  # noqa: E402

#: md5 of ``make_instance(family, seed).to_json()`` computed BEFORE the round-2 edits
#: of generator.py (2026-10-12); the round-1 families must regenerate byte-identically.
ROUND1_MD5 = {
    ("small", 0): "0bc8e4831dda6f00c0703b8062821974",
    ("medium", 0): "f396c24436a0af27762c6acddb9b12c4",
    ("large", 0): "2479a4a323618f7999824a1d2f2ada34",
    ("large", 1): "04cf19097b7ce337e0ee4156275196a9",
}
#: md5 of ``make_synthetic_instance(seed=1).to_json()`` (generator defaults, legacy call).
ROUND1_DEFAULT_SEED1_MD5 = "b9b3e03d1d4eeb13072276ef3aa0f14b"


@pytest.mark.parametrize("family,seed", sorted(ROUND1_MD5))
def test_round1_family_json_unchanged(family, seed):
    inst = C.make_instance(family, seed=seed)
    assert hashlib.md5(inst.to_json().encode()).hexdigest() == ROUND1_MD5[(family, seed)]
    # legacy meta has no round-2 keys
    assert "round2" not in inst.meta and "cost_variant" not in inst.meta
    assert "window_h" not in inst.meta["params"]


def test_round1_generator_default_call_unchanged():
    inst = make_synthetic_instance(seed=1)
    assert hashlib.md5(inst.to_json().encode()).hexdigest() == ROUND1_DEFAULT_SEED1_MD5
    assert (inst.H, len(inst.orders)) == (24, 30)
    assert DEFAULT_FACILITIES_SPEC["B"] == 4 and DEFAULT_FACILITIES_SPEC["C"] == 3
    assert DEFAULT_FACILITIES_SPEC_R2["B"] == 3 and DEFAULT_FACILITIES_SPEC_R2["C"] == 2
    # explicit legacy sizes in round-2 mode reproduce the old facility / battery defaults
    old = make_synthetic_instance(seed=1, n_bikes=4, window_h=2.0, facilities_spec={"B": 4, "C": 3},
                                  init_frac=(0.4, 1.0), cost_variant="toy", kaggle_calibrated=False,
                                  time_profile="weekday", window_start_hour=17.5)
    assert all((f.B, f.C) == (4, 3) for f in old.facilities)
    assert all(math.ceil(0.4 * 12) <= b.q0 <= 12 for b in old.bikes)
    assert old.kappa == 1.0 and old.orders[0].P == 100.0 and old.meta["cost_variant"] == "toy"


def test_usd4h_family_builds_and_records_everything():
    inst = C.make_instance("usd4h", seed=0)
    assert inst.validate() == []
    assert Instance.from_json(inst.to_json()) == inst
    assert inst.to_json() == C.make_instance("usd4h", seed=0).to_json()   # deterministic
    d = inst.disc
    assert d.H == 48 and d.L == 12 and d.Delta_h == pytest.approx(5 / 60)
    # sizes fixed by the R2.2 probe (DECISIONS "R2 implementation notes"): 1.5 orders/bike-h x 6 x 4 h
    nb = C.FAMILIES["usd4h"]["n_bikes"]
    assert len(inst.bikes) == nb and len(inst.orders) == round(1.5 * nb * 4)
    large = C.make_instance("usd4h_large", seed=0)
    assert len(large.bikes) == 10 and len(large.orders) == 60          # R2.2 nominal size kept as usd4h_large
    meta = inst.meta
    assert meta["family"] == "usd4h" and meta["round2"] is True
    assert meta["window_h"] == [17.0, 21.0] and meta["window_length_h"] == 4.0
    assert meta["day_type"] == "weekday"
    p = meta["params"]
    assert p["round2"] and p["window_h"] == 4.0 and p["window_start_hour"] == 17.0
    assert p["orders_per_bike_hour"] == 1.5 and p["init_frac"] == [0.3, 0.6]
    assert p["cost_variant"] == "usd_sunk" and p["kaggle_calibrated"] is True
    assert p["n_orders"] == len(inst.orders) and p["H"] == 48
    # R2.2 facilities: B 3, C 2, K 8, M 1, sigma 1, 4 kW; grid 8 kW, 6 kW during 18-20 h
    for f in inst.facilities:
        assert f.swap and f.charge and (f.y, f.B, f.C) == (1, 3, 2)
        assert (f.K, f.M, f.sigma, f.P_kw, f.R_end) == (8, 1, 1, 4.0, 1)
        assert (f.F, f.bB, f.bC) == pytest.approx((12.03, 0.332, 0.082))
        assert (f.Fhat, f.bhat, f.chat) == (50000.0, 450.0, 400.0)
    grid = inst.P_grid["sites"]
    assert len(grid) == 48 and grid[:12] == [8.0] * 12 and grid[12:36] == [6.0] * 24 and grid[36:] == [8.0] * 12
    # R2.1 usd_sunk prices
    assert inst.kappa == 0.12 and inst.pi == pytest.approx(0.32) and (inst.q_res, inst.rho) == (1, 0.5)
    for o in inst.orders:
        assert (o.P, o.w, o.v) == (30.0, 18.0, 36.0)
    # R2.2 bikes: q0 in 4..7
    assert all(4 <= b.q0 <= 7 for b in inst.bikes)
    assert len({b.q0 for b in inst.bikes}) > 1
    # R2.2 Kaggle order attributes: prep 20..35 min -> a - r in 4..7 slots, b = a + 5
    om = {o["id"]: o for o in meta["orders"]}
    for o in inst.orders:
        prep = om[o.id]["prep_min"]
        assert 20 <= prep <= 35 and prep == int(prep)
        assert o.a == o.r + math.ceil(prep / 5 - 1e-9) and 4 <= o.a - o.r <= 7
        assert o.b == o.a + 5 and o.hp == 1 and o.hd == 1
        assert om[o.id]["cuisine"] in meta["kaggle_calibration"]["cuisines_present"]
        assert om[o.id]["rank"] >= 1
        assert 0 <= o.r < 48 - 8
    assert [o.r for o in inst.orders] == sorted(o.r for o in inst.orders)
    # meta['cost_variant'] / meta['costs'] record variant, window and every coefficient
    assert meta["cost_variant"] == "usd_sunk"
    mc = meta["costs"]
    assert mc["variant"] == "usd_sunk" and mc["window_h"] == 4.0 and mc["window_scale"] == 1.0
    for key, val in {"kappa": 0.12, "pi": 0.32, "pi_peak": None, "F": 12.03, "F_hub": 29.19,
                     "bB": 0.332, "bC": 0.082, "Fhat": 50000.0, "bhat": 450.0, "chat": 400.0,
                     "P": 30.0, "w": 18.0, "v": 36.0, "f": 20.0, "vreb": 1.0,
                     "q_res": 1, "rho": 0.5}.items():
        assert mc[key] == val, key
    assert mc["source"].endswith("cost_calibration_usd.json")
    # time profile block recorded with its 'assumption' flag; Kaggle calibration recorded
    tp = meta["time_profile"]
    assert tp["status"] == "assumption" and tp["name"] == TIME_PROFILE_R2["name"]
    assert tp["weekday_integral"] == pytest.approx(1.0, abs=1e-6) and tp["weekend_factor"] == 1.15
    kc = meta["kaggle_calibration"]
    assert kc["prep_min_range"] == [20, 35] and kc["promise_after_ready_min"] == 25.0
    assert kc["promise_after_ready_slots"] == 5 and kc["zipf_s"] == 1.0
    assert kc["cuisine_shares"]["American"] == pytest.approx(0.3077, abs=1e-3)
    assert sum(kc["cuisine_shares_effective"].values()) == pytest.approx(1.0)
    assert meta["cuisine_pref"] is None
    # restaurants carry Kaggle cuisines apportioned by share (American first)
    cuisines = [c for _, c in meta["restaurants"]]
    assert len(cuisines) == 8 and Counter(cuisines)["American"] >= 2 and "Japanese" in cuisines


def test_usd4h_arc_library_and_terminal_precheck():
    inst = C.make_instance("usd4h", seed=0)
    pr = C.pruning_for(inst)
    assert pr["tau_max"] == 4 and pr["start_slack"] == 6
    lib = build_arcs(inst, strict=True, **pr)         # raises on a bike without a terminal arc (9)
    assert lib.infeasible_bikes == [] and len(lib) > 0
    assert len(lib.delivery_arcs(inst.orders[0].id)) > 0
    est = estimate_arcs(inst, pr, sample_bikes=1)
    assert est["infeasible_bikes"] == [] and est["extrapolated"]


def test_usd8h_and_toyunits_families():
    eight = C.make_instance("usd8h", seed=0)
    assert eight.validate() == [] and eight.H == 96
    assert len(eight.orders) == round(1.5 * C.FAMILIES["usd8h"]["n_bikes"] * 8)
    assert eight.meta["rolling_horizon_only"] is True                    # registered rolling-horizon-only
    assert eight.meta["window_h"] == [14.0, 22.0]
    # window scaling of F, F_hub, bB, bC (8 h -> x2); kappa / P / w / v unchanged
    for f in eight.facilities:
        assert (f.F, f.bB, f.bC) == pytest.approx((24.06, 0.664, 0.164))
    assert eight.kappa == 0.12 and eight.orders[0].P == 30.0
    assert eight.meta["costs"]["window_h"] == 8.0 and eight.meta["costs"]["window_scale"] == 2.0
    # peak 18-20 h = slots 48..71 at a 14:00 start
    grid = eight.P_grid["sites"]
    assert grid[47] == 8.0 and grid[48] == 6.0 and grid[71] == 6.0 and grid[72] == 8.0
    # usd4h_toyunits: identical instance except for the prices
    usd = C.make_instance("usd4h", seed=0)
    toy = C.make_instance("usd4h_toyunits", seed=0)
    assert toy.meta["cost_variant"] == "toy" and toy.kappa == 1.0 and toy.pi == 2.0
    assert toy.nodes == usd.nodes and toy.routes == usd.routes and toy.bikes == usd.bikes
    assert [(o.o, o.d, o.r, o.a, o.b) for o in toy.orders] == [(o.o, o.d, o.r, o.a, o.b) for o in usd.orders]
    assert all((o.P, o.w, o.v) == (100.0, 12.0, 24.0) for o in toy.orders)
    assert [(f.node, f.B, f.C) for f in toy.facilities] == [(f.node, f.B, f.C) for f in usd.facilities]
    assert all((f.F, f.bB, f.bC) == (20.0, 3.0, 2.0) for f in toy.facilities)
    assert toy.P_grid == usd.P_grid and toy.options == usd.options
    assert toy.meta["orders"] == usd.meta["orders"]
    # explicit costs win over the variant (R2.1)
    over = make_synthetic_instance(seed=0, n_bikes=2, window_h=4.0, costs={"kappa": 0.7},
                                   demand_spec={"P": 45.0})
    assert over.kappa == 0.7 and over.orders[0].P == 45.0 and over.orders[0].w == 18.0
    assert over.meta["costs"]["kappa"] == 0.7 and over.meta["costs"]["P"] == 45.0
    with pytest.raises(ValueError):
        make_synthetic_instance(seed=0, n_bikes=2, window_h=4.0, H=24)


def test_kaggle_sampler_distributions_over_2000_orders():
    kag = load_kaggle_calibration()
    shares = kag["cuisine_shares"]
    assert len(shares) == 14 and sum(shares.values()) == pytest.approx(1.0)
    # three restaurants per cuisine, all within 2.5 km of the customer
    restaurants = []
    for ci, c in enumerate(shares):
        for k in range(3):
            restaurants.append((((ci % 5) * 2 + k, ci // 5 * 3 + k), c))
    rng = np.random.default_rng(11)
    rs = KaggleRestaurantSampler(restaurants, shares, rng, kag["prep_min_range"], 1.0, 2.5, 3, 150.0)
    assert rs.effective_shares == pytest.approx(shares)
    customer = (5, 5)
    n = 2000
    details = [rs.sample_detail(rng, customer, 0) for _ in range(n)]
    # cuisine shares within tolerance (4 sd, at least 2 points)
    emp = Counter(d["cuisine"] for d in details)
    for c, p in shares.items():
        tol = max(0.02, 4 * math.sqrt(p * (1 - p) / n))
        assert abs(emp[c] / n - p) <= tol, (c, emp[c] / n, p)
    # prep ~ DiscreteUniform{20..35}: integer minutes, every value within 4 sd of 1/16, mean ~ 27.5
    preps = [d["prep_min"] for d in details]
    assert all(p == int(p) and 20 <= p <= 35 for p in preps)
    pc = Counter(int(p) for p in preps)
    for v in range(20, 36):
        assert abs(pc[v] / n - 1 / 16) <= 4 * math.sqrt((1 / 16) * (15 / 16) / n) + 1e-9
    assert abs(float(np.mean(preps)) - 27.5) < 0.5
    # promise (R2.2): b = a + ceil(25 / 5) = a + 5 slots on an instance
    inst = make_synthetic_instance(seed=2, n_bikes=4, window_h=4.0, n_restaurants=8)
    assert all(o.b - o.a == 5 for o in inst.orders)


def test_zipf_popularity_within_cuisine():
    # one cuisine, 4 restaurants within radius: pick shares proportional to 1 / rank (s = 1)
    restaurants = [((2, 2), "American"), ((3, 2), "American"), ((2, 3), "American"), ((3, 3), "American")]
    rng = np.random.default_rng(5)
    rs = KaggleRestaurantSampler(restaurants, {"American": 1.0}, rng, (20, 35), 1.0, 2.5, 3, 150.0)
    assert sorted(rs.rank.values()) == [1, 2, 3, 4]
    n = 4000
    picks = Counter(rs.sample_detail(rng, (2, 2), 0)["rank"] for _ in range(n))
    hs = sum(1 / r for r in range(1, 5))
    for r in range(1, 5):
        p = (1 / r) / hs
        assert abs(picks[r] / n - p) <= 4 * math.sqrt(p * (1 - p) / n) + 1e-9
    # ranks are fixed per seed: a second sampler from the same seed gives the same ranks
    rs2 = KaggleRestaurantSampler(restaurants, {"American": 1.0}, np.random.default_rng(5), (20, 35))
    assert rs2.rank == KaggleRestaurantSampler(restaurants, {"American": 1.0},
                                               np.random.default_rng(5), (20, 35)).rank
    # radius expansion: far restaurants are still candidates when fewer than 3 are inside
    far = [((0, 0), "Thai"), ((19, 19), "Thai")]
    rs3 = KaggleRestaurantSampler(far, {"Thai": 1.0}, np.random.default_rng(0), (20, 35), 1.0, 0.3, 3, 150.0)
    assert len(rs3.candidates("Thai", (0, 0))) == 2
    # cuisines without a restaurant are dropped and the rest renormalised
    rs4 = KaggleRestaurantSampler(far, {"Thai": 0.25, "French": 0.75}, np.random.default_rng(0), (20, 35))
    assert rs4.effective_shares == {"Thai": 1.0} and rs4._dropped_share == pytest.approx(0.75)
    assert apportion_counts({"a": 0.6, "b": 0.3, "c": 0.1}, 6) == {"a": 4, "b": 2, "c": 0}
    assert sum(apportion_counts({"a": 0.5, "b": 0.5}, 3).values()) == 3


def test_block_profile_integrates_to_one_and_drives_generator():
    weekday = block_profile(TIME_PROFILE_R2, "weekday")
    weekend = block_profile(TIME_PROFILE_R2, "weekend")
    assert profile_integral(weekday) == pytest.approx(1.0, abs=1e-6)
    assert profile_integral(weekend) == pytest.approx(1.15, abs=1e-6)
    # block shares: lunch 28 %, dinner 45 %, late 12 %, rest 15 %
    assert profile_integral(weekday, 11.5, 14.0) == pytest.approx(0.28, abs=1e-6)
    assert profile_integral(weekday, 17.5, 21.5) == pytest.approx(0.45, abs=1e-6)
    assert profile_integral(weekday, 21.5, 25.0) == pytest.approx(0.12, abs=1e-6)
    assert profile_integral(weekday, 1.0, 11.5) + profile_integral(weekday, 14.0, 17.5) == pytest.approx(0.15, abs=1e-6)
    assert weekday(0.5) == weekday(24.5) == weekday(21.6)                  # late block wraps midnight
    assert weekday(18.0) > weekday(17.0) and weekday(12.0) > weekday(15.0)
    assert weekend(18.0) == pytest.approx(1.15 * weekday(18.0))
    with pytest.raises(ValueError):
        block_profile(TIME_PROFILE_R2, "holiday")
    # the generator accepts the block (dict or 'r2'), exact count, and the dinner block is busier
    gen = TimeDependentGenerator("r2", (17.0, 20.333), target=60)
    assert gen.profile_name.startswith("r2_lunch_dinner_late") and gen.profile is None
    rng = np.random.default_rng(0)
    mins = gen.sample(rng, 60)
    assert len(mins) == 60 and mins == sorted(mins) and max(mins) < 200
    assert gen.rate(18.0) / gen.rate(17.0) == pytest.approx((0.45 / 4.0) / (0.15 / 14.0))
    counts = [len(gen.sample(rng)) for _ in range(200)]
    assert abs(np.mean(counts) - 60) < 3.0
    # weekend day type: volume x1.15 when n_orders is derived
    wk = make_synthetic_instance(seed=0, n_bikes=10, window_h=4.0, day_type="weekend")
    assert len(wk.orders) == round(1.5 * 10 * 4 * 1.15) == 69
    assert wk.meta["day_type"] == "weekend" and wk.meta["params"]["weekend_factor"] == 1.15
    # the old synthetic hourly profile stays selectable in round-2 mode
    old = make_synthetic_instance(seed=0, n_bikes=4, window_h=4.0, time_profile="weekday")
    assert old.meta["params"]["demand_spec"]["profile"] == "weekday" and "time_profile" not in old.meta
    assert R2_DEFAULTS["time_profile"] == "r2"


def test_price_peak_hours_separate_from_grid_peak():
    """Units review F8: the TOU price window (facilities_spec['price_peak_hours']) is
    independent of the grid-limit peak (peak_hours); default = peak_hours (unchanged)."""
    grid_peak = make_synthetic_instance(seed=5, n_bikes=2, n_orders=4, H=36, costs={"pi_peak": 3.0})
    tou = make_synthetic_instance(seed=5, n_bikes=2, n_orders=4, H=36, costs={"pi_peak": 3.0},
                                  facilities_spec={"price_peak_hours": (8.0, 22.0)})
    assert isinstance(grid_peak.pi, dict) and isinstance(tou.pi, dict)
    assert set(grid_peak.pi.values()) == {2.0, 3.0}                 # 18-20 h peak inside the window
    assert set(tou.pi.values()) == {3.0}                            # 08-22 h covers the whole window
    assert grid_peak.P_grid == tou.P_grid                           # the grid limit still uses peak_hours
    assert grid_peak.meta["price_peak_hours"] == [18.0, 20.0] and tou.meta["price_peak_hours"] == [8.0, 22.0]
    flat = make_synthetic_instance(seed=5, n_bikes=2, n_orders=4, H=36)
    assert not isinstance(flat.pi, dict) and "price_peak_hours" not in flat.meta
    # legacy instances without pi_peak are byte-identical to before (no new meta key)
    assert flat.to_json() == make_synthetic_instance(seed=5, n_bikes=2, n_orders=4, H=36).to_json()
