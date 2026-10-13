"""Tests of the semi-real NYC data layer (``ebike_swap_sim.data_nyc``, DECISIONS
R2.4 with R2.1 / R2.2 conventions) on the real files under ``data/raw``:
projection, grid, DOHMH restaurants and cuisine mapping, samplers, pure-python
point-in-polygon, loaders, cost variants and the instance builder."""
from __future__ import annotations

import math
import os
import time
from collections import Counter

import numpy as np
import pytest

from ebike_swap_sim import Instance, build_arcs
from ebike_swap_sim import data_nyc as dn
from ebike_swap_sim.generator import default_pruning

pytestmark = pytest.mark.skipif(
    not all(os.path.exists(p) for p in dn.DEFAULT_PATHS.values()),
    reason="real data files under data/raw / notes/data are missing")


@pytest.fixture(scope="module")
def box() -> dn.StudyBox:
    return dn.DEFAULT_BOX


@pytest.fixture(scope="module")
def zw_all() -> dn.GeoDaZoneWeights:
    with pytest.warns(UserWarning, match="FALLBACK"):
        return dn.GeoDaZoneWeights()


@pytest.fixture(scope="module")
def zw_box(box) -> dn.GeoDaZoneWeights:
    return dn.GeoDaZoneWeights(box=box, warn=False)


@pytest.fixture(scope="module")
def restaurants(box):
    return dn.restaurants_in_box(box)


# ---------------------------------------------------------------------------
# 1. geometry
# ---------------------------------------------------------------------------
def test_projection_round_trip_and_rotation(box):
    pts = [(40.7484, -73.9857), (box.lat_min, box.lon_min), (box.lat_max, box.lon_max),
           (40.7359, -73.9911), (40.76, -73.97)]
    for lat, lon in pts:
        x, y = box.project(lat, lon)
        lat2, lon2 = box.inverse(x, y)
        assert abs(lat2 - lat) * dn.M_PER_DEG_LAT < 1.0 and abs(lon2 - lon) * dn.M_PER_DEG_LON < 1.0
    # all four box corners land at x, y >= 0 with min exactly 0
    corners = [box.project(a, b) for a in (box.lat_min, box.lat_max) for b in (box.lon_min, box.lon_max)]
    assert min(c[0] for c in corners) == pytest.approx(0.0, abs=1e-6)
    assert min(c[1] for c in corners) == pytest.approx(0.0, abs=1e-6)
    # a displacement along the avenue azimuth (29 deg E of N) maps onto the grid +y axis
    a = math.radians(dn.GRID_AZIMUTH_DEG)
    lat1, lon1 = 40.75, -73.99
    lat2 = lat1 + 1000 * math.cos(a) / dn.M_PER_DEG_LAT
    lon2 = lon1 + 1000 * math.sin(a) / dn.M_PER_DEG_LON
    (x1, y1), (x2, y2) = box.project(lat1, lon1), box.project(lat2, lon2)
    assert abs(x2 - x1) < 1e-6 and y2 - y1 == pytest.approx(1000.0, abs=1e-6)
    # a point 1 deg north moves 111.0 km, 1 deg east 84.3 km (R2.4 constants)
    e, n = box._east_north(box.lat_min + 1.0, box.lon_min + 1.0)
    assert (e, n) == (84_300.0, 111_000.0)


def test_box_grid_size_sane(box):
    # 3.9 x 3.4 km box -> rotated bounding box ~4.8 x 5.0 km -> 34 x 35 nodes of 150 m
    assert 25 <= box.grid_nx <= 45 and 25 <= box.grid_ny <= 45
    assert box.grid_nx == math.ceil(box.width_m / 150 - 1e-9) + 1
    assert box.grid_ny == math.ceil(box.height_m / 150 - 1e-9) + 1
    assert 4500 < box.width_m < 5200 and 4700 < box.height_m < 5400
    net = box.make_grid(np.random.default_rng(0))
    assert (net.nx_, net.ny_, net.block_m) == (box.grid_nx, box.grid_ny, 150.0)
    assert len(net.nodes) == box.grid_nx * box.grid_ny == len(box.grid_nodes())
    # snapping: every corner and the centre land inside the grid, snapping error <= half a block
    for lat, lon in [(box.lat_min, box.lon_min), (box.lat_max, box.lon_max), (40.7525, -73.985)]:
        v = box.snap(lat, lon)
        assert 0 <= v[0] < box.grid_nx and 0 <= v[1] < box.grid_ny
        x, y = box.project(lat, lon)
        nx_, ny_ = box.node_xy(v)
        assert abs(x - nx_) <= 75.0 + 1e-6 and abs(y - ny_) <= 75.0 + 1e-6
    # a point far outside is clamped to the grid border
    assert box.snap(40.9, -73.8) in box.grid_nodes()
    with pytest.raises(ValueError):
        dn.StudyBox(lat_min=1.0, lat_max=0.0)


# ---------------------------------------------------------------------------
# 2. restaurants
# ---------------------------------------------------------------------------
def test_dohmh_loader_filters_and_box_count(restaurants):
    df = dn.load_dohmh()
    lat_min, lat_max, lon_min, lon_max = dn.DOHMH_BBOX
    assert df["lat"].between(lat_min, lat_max).all() and df["lon"].between(lon_min, lon_max).all()
    assert (df["cuisine"].str.len() > 0).all() and df["r_last_insp"].notna().all()
    assert df["camis"].is_unique and 25_000 <= len(df) <= 30_000     # MANIFEST: 27,030 usable
    assert len(restaurants) >= 500
    assert set(restaurants["node"].map(len)) == {2}
    assert restaurants["lat"].between(dn.DEFAULT_BOX.lat_min, dn.DEFAULT_BOX.lat_max).all()


def test_cuisine_map_covers_dohmh_values(restaurants):
    assert len(dn.CUISINE_MAP) == 90
    assert set(dn.CUISINE_MAP.values()) <= set(dn.KAGGLE_CLASSES) | {"other"}
    assert len(dn.KAGGLE_CLASSES) == 14
    present_in_box = set(restaurants["cuisine"])
    assert present_in_box <= set(dn.CUISINE_MAP), present_in_box - set(dn.CUISINE_MAP)
    assert set(dn.load_dohmh()["cuisine"]) <= set(dn.CUISINE_MAP)
    # explicit anchors of the declared mapping
    assert dn.CUISINE_MAP["Pizza"] == "Italian" and dn.CUISINE_MAP["Tex-Mex"] == "Mexican"
    assert dn.CUISINE_MAP["Coffee/Tea"] == "other" and dn.CUISINE_MAP["Southeast Asian"] == "Vietnamese"
    # every Kaggle class has at least one restaurant in the default box
    assert set(dn.KAGGLE_CLASSES) <= set(restaurants["kaggle_class"])


def test_restaurant_sampler_shares_radius_and_ranks(box, zw_box):
    rng = np.random.default_rng(7)
    dest = dn.NYCDestinationSampler(box, zw_box, rng)
    rs = dn.NYCRestaurantSampler(box, rng)
    shares = rs.cuisine_shares()
    kaggle = dn.load_kaggle_calibration()["cuisine_shares"]
    assert sum(shares.values()) == pytest.approx(1.0) and rs.dropped_classes == []
    assert shares["American"] == pytest.approx(kaggle["American"])
    # Zipf ranks: a permutation 1..n inside every class, fixed per seed
    for c in rs.cuisines:
        ranks = sorted(rs.df.loc[rs.df["kaggle_class"] == c, "rank"])
        assert ranks == list(range(1, len(ranks) + 1))
    rs_same = dn.NYCRestaurantSampler(box, np.random.default_rng(7))
    assert (rs_same.df["rank"].to_numpy() == rs.df["rank"].to_numpy()).all()
    counts = Counter()
    for _ in range(2000):
        d = dest.sample(rng)
        rec = rs.sample_record(rng, d)
        counts[rec["cuisine"]] += 1
        assert rec["dist_m"] <= rec["radius_m"] + 1e-6              # within the radius used
        assert rec["radius_m"] >= 2500.0 and rec["n_candidates"] >= 1
        assert 20.0 <= rec["prep_min"] <= 35.0 and float(rec["prep_min"]).is_integer()
        assert rec["node"] in set(rs.df["node"])
    for c, p in shares.items():
        assert abs(counts[c] / 2000 - p) <= 0.05, (c, counts[c] / 2000, p)
    # generator interface
    node, prep = rs.sample(rng, dest.sample(rng), 0)
    assert isinstance(node, tuple) and 20 <= prep <= 35
    # candidate expansion: the radius grows x1.5 until >= 3 candidates (rare classes far away)
    far = (0, 0)
    local, radius = rs.candidates("Vietnamese", far)
    assert len(local) >= min(3, 9) and radius / 2500.0 == pytest.approx(1.5 ** round(math.log(radius / 2500.0, 1.5)))


# ---------------------------------------------------------------------------
# 3. zones: point in polygon, GeoDa fallback, destination sampler
# ---------------------------------------------------------------------------
def test_point_in_polygon_known_points(zw_all):
    assert zw_all.zone_at(40.7484, -73.9857) == "MN17"              # Empire State Building
    assert zw_all.zone_at(40.7359, -73.9911) in ("MN13", "MN23")    # Union Square
    park = zw_all.zone_at(40.7812, -73.9665)                        # Central Park
    assert park == "MN99" and "park" in zw_all.info(park)["name"].lower()
    assert zw_all.zone_at(40.0, -73.0) is None and zw_all.weight_at(40.0, -73.0) == 0.0
    assert len(zw_all.zones()) == 195
    # simple ring / hole arithmetic
    square = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    hole = [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6], [0.4, 0.4]]
    assert dn.point_in_ring(0.5, 0.5, square) and not dn.point_in_ring(1.5, 0.5, square)
    assert not dn.point_in_polygon(0.5, 0.5, [square, hole]) and dn.point_in_polygon(0.2, 0.2, [square, hole])
    assert dn.point_in_geometry(0.5, 0.5, {"type": "MultiPolygon", "coordinates": [[square]]})


def test_geoda_fallback_weights(zw_all, zw_box):
    info = zw_all.info("MN17")
    assert info["poptot"] == 28228 and info["youth16_19"] == 129 + 1166
    share = (129 + 1166) / 28228
    # R2.4 fallback N_z = popover18 (adults), share relative to poptot (units review F6)
    assert info["popover18"] > 0 and info["N_z"] == info["popover18"]
    assert zw_all.zone_total("MN17") == pytest.approx(info["popover18"] * (1 + 2.4 * share))
    assert "popover18" in dn.GEODA_FALLBACK_WARNING and "N_z" in dn.GEODA_FALLBACK_WARNING
    assert zw_all.weight_at(40.7484, -73.9857) == pytest.approx(zw_all.zone_total("MN17") / info["area_km2"])
    assert 0.5 < info["area_km2"] < 5.0
    # park NTA is naturally low, corrupt fields are never read
    assert zw_all.weight_at(40.7812, -73.9665) < 0.05 * zw_all.weight_at(40.7484, -73.9857)
    assert not ({"medianinco", "medianage", "popdty"} & set(info))
    assert isinstance(zw_all, dn.ZoneWeights) and dn.as_zone_weight_fn(zw_all) == zw_all.weight_at
    # box-restricted object knows only the Manhattan NTAs intersecting the box
    assert set(zw_box.zones()) <= set(zw_all.zones()) and {"MN13", "MN17", "MN20"} <= set(zw_box.zones())
    assert all(z.startswith("MN") for z in zw_box.zones())
    assert "GeoDa" in zw_box.warning and "medianinco" in zw_box.warning


def test_destination_sampler_zone_weights(box, zw_box):
    rng = np.random.default_rng(3)
    dest = dn.NYCDestinationSampler(box, zw_box, rng)
    assert set(dest.support) <= set(box.grid_nodes())
    for v in dest.support:
        lat, lon = box.node_latlon(v)
        assert box.contains(lat, lon) and dest.node_weight[v] > 0
    outside = [v for v in box.grid_nodes() if not box.contains(*box.node_latlon(v))]
    assert outside and all(dest.node_weight[v] == 0.0 for v in outside)
    mass = dest.zone_totals()
    assert sum(mass.values()) == pytest.approx(1.0) and mass.get("MN99", 0.0) < 0.01
    draws = [dest.sample(rng) for _ in range(500)]
    assert all(d in set(dest.support) for d in draws) and len(set(draws)) > 50
    assert all(0 <= dest.zone_of(d) < len(dest.zone_ids()) for d in draws)
    assert dest.zone_of((0, 0)) == -1 or dest.node_zone_code[(0, 0)] is not None
    # a bare callable is accepted through the same interface (uniform weight -> uniform nodes)
    uni = dn.NYCDestinationSampler(box, lambda lat, lon: 1.0, rng)
    assert len(uni.support) == sum(1 for v in box.grid_nodes() if box.contains(*box.node_latlon(v)))
    assert all(uni.zone_of(v) == -1 for v in uni.support)


# ---------------------------------------------------------------------------
# 4. loaders
# ---------------------------------------------------------------------------
def test_crash_grid_and_counter_profile(box):
    grid = dn.load_crash_grid()
    assert len(grid) == 2251 and grid[(40.72, -73.995)]["cyc_crashes"] == 87     # MANIFEST top cell
    risk = dn.crash_risk_by_node(box, grid)
    assert set(risk) == set(box.grid_nodes()) and min(risk.values()) >= 0 and max(risk.values()) >= 50
    prof = dn.counter_hourly_profile()
    assert set(prof) == {"weekday", "weekend"}
    for day, vals in prof.items():
        assert len(vals) == 24 and sum(vals) == pytest.approx(1.0) and min(vals) >= 0
        assert max(range(24), key=lambda h: vals[h]) in range(12, 20)   # afternoon / evening peak
    assert prof["weekday"][18] > prof["weekday"][3]
    df = dn.load_counter_profile()
    assert "Staten Island Ferry" in set(df["name"])
    assert dn.counter_hourly_profile(exclude=()) != prof            # the exclusion matters
    table = dn.compare_counter_profile(prof)
    assert list(table["period"]) == ["lunch", "dinner", "late", "rest"]
    assert table["assumed"].sum() == pytest.approx(1.0)
    assert table["counter_weekday"].sum() == pytest.approx(1.0)
    assert table["counter_weekend"].sum() == pytest.approx(1.0)
    hourly = dn.assumed_hourly_profile()
    assert len(hourly) == 24 and sum(hourly) == pytest.approx(1.0)
    shares = dn.period_shares(hourly)
    assert shares["dinner"] > shares["lunch"] > shares["late"] and dn.ASSUMED_TIME_PROFILE["flag"] == "assumption"
    assert hourly[19] == pytest.approx(0.45 / 4.0) and hourly[12] == pytest.approx(0.28 / 2.5)


# ---------------------------------------------------------------------------
# 5. cost variants (R2.1) and the instance builder
# ---------------------------------------------------------------------------
def test_cost_variants():
    sunk = dn.cost_variant_params("usd_sunk", 4.0)
    assert sunk["costs"]["kappa"] == 0.12 and sunk["demand_spec"] == {"P": 30.0, "w": 18.0, "v": 36.0}
    assert (sunk["costs"]["pi"], sunk["costs"]["F"], sunk["costs"]["bB"], sunk["costs"]["bC"]) == (0.32, 12.03, 0.332, 0.082)
    assert (sunk["costs"]["Fhat"], sunk["costs"]["bhat"], sunk["costs"]["chat"]) == (50000.0, 450.0, 400.0)
    assert sunk["services_spec"] == {"f": 20.0, "vreb": 1.0}
    a = dn.cost_variant_params("usd_A", 4.0)
    assert a["costs"]["kappa"] == 0.5 and a["demand_spec"]["w"] == 40.0 and a["demand_spec"]["v"] == 80.0
    b = dn.cost_variant_params("usd_B", 8.0)
    assert b["costs"]["kappa"] == 1.6 and b["demand_spec"]["w"] == 18.0
    assert b["costs"]["F"] == pytest.approx(24.06) and b["costs"]["bB"] == pytest.approx(0.664)   # x2 for 8 h
    two = dn.cost_variant_params("usd_sunk", 2.0)
    assert two["costs"]["F"] == pytest.approx(6.015) and two["costs"]["kappa"] == 0.12         # kappa not scaled
    toy = dn.cost_variant_params("toy", 8.0)
    assert (toy["costs"]["kappa"], toy["costs"]["pi"], toy["costs"]["F"], toy["costs"]["bB"]) == (1.0, 2.0, 20.0, 3.0)
    assert toy["demand_spec"] == {"P": 100.0, "w": 12.0, "v": 24.0}
    assert dn.cost_variant_params("usd_low", 4.0)["costs"]["kappa"] == 0.12
    assert dn.cost_variant_params("usd_high", 4.0)["demand_spec"]["P"] == 60.0
    with pytest.raises(ValueError):
        dn.cost_variant_params("eur", 4.0)


def test_make_nyc_instance_builds_validates_and_arcs(box):
    t0 = time.time()
    inst = dn.make_nyc_instance(seed=0, n_bikes=6, window_h=2.0)    # default: ACS weights, no warning
    assert inst.validate() == []
    s = inst.summary()
    assert s["bikes"] == 6 and s["orders"] == 18 and s["H"] == 24 and s["L"] == 12   # 6 x 2 h x 1.5
    assert inst.disc.p_ch_kw == pytest.approx(0.05 / (0.9 / 12))
    # R2.1 usd_sunk prices
    assert inst.kappa == 0.12 and inst.pi == 0.32 and (inst.q_res, inst.rho) == (1, 0.5)
    for o in inst.orders:
        assert (o.P, o.w, o.v) == (30.0, 18.0, 36.0) and o.hp == 1 and o.hd == 1
        assert o.a - o.r in range(4, 8) and o.b == o.a + 5               # prep 20..35 min, promise 25 min
        assert 0 <= o.r < 24 - 8 and o.o in inst.nodes and o.d in inst.nodes
    assert [o.r for o in inst.orders] == sorted(o.r for o in inst.orders)
    # R2.2 facilities, co-located, fixed; window scaling of F / bB / bC (2 h = x0.5)
    assert len(inst.facilities) == 3 and inst.services == []
    for f in inst.facilities:
        assert f.swap and f.charge and (f.y, f.B, f.C, f.K, f.M, f.sigma, f.P_kw, f.R_end) == (1, 3, 2, 8, 1, 1, 4.0, 1)
        assert (f.F, f.bB, f.bC) == pytest.approx((6.015, 0.166, 0.041)) and f.group == "sites"
    assert inst.P_grid["sites"][0] == 8.0 and 6.0 in inst.P_grid["sites"]      # 18-20 h peak inside 17-19 h
    assert inst.P_grid["sites"][12] == 6.0                                       # 18:00
    # bikes start at the sites with q0 in 4..7
    sites = {f.node for f in inst.facilities}
    assert all(b.v0 in sites and 4 <= b.q0 <= 7 for b in inst.bikes)
    # all ordered pairs of V have a route; node set = restaurants + sites + customers
    assert len(inst.routes) == len(inst.nodes) * (len(inst.nodes) - 1)
    for (u, v), r in inst.routes.items():
        assert r.T_h == pytest.approx(r.d_km * 1000 / 250 / 60)
    # meta: semi-real flag, box, counts, caveat, fallback warning, assumption-flagged profile
    m = inst.meta
    assert m["semi_real"] is True and m["geometry_caveat"] == dn.GEOMETRY_CAVEAT
    assert "no real road network" in m["geometry_caveat"]
    assert m["box"]["lat_min"] == box.lat_min and m["box"]["grid_nx"] == box.grid_nx
    assert m["n_restaurants_in_box"] >= 500 and 1 <= m["n_restaurants_used"] <= 18
    # default zone weights = ACS literature formula on NTA-2020 polygons (MN0501 = Midtown South-Flatiron)
    assert m["n_zones_used"] == len(m["zones_used"]) >= 5 and "MN0501" in m["zones_used"]
    assert m["zone_weights_source"] == "acs_2020_24_literature" and m["zone_weights_warning"] is None
    assert m["zone_weights_vintage"] == "NTA2020" and m["zone_weights_food_insecurity"] is False
    assert m["cost_variant"] == "usd_sunk" and m["time_profile"]["flag"] == "assumption"
    assert len(m["restaurants"]) == m["n_restaurants_used"] and len(m["orders"]) == 18
    assert all(box.contains(*r["customer_latlon"]) for r in m["orders"])
    assert [tuple(x) for x in m["sites"]] == [f.node for f in inst.facilities]
    assert all(box.contains(a, b) for a, b in m["sites_latlon"])
    # node_zone option covers every node; default_pruning reads the meta
    assert {tuple(n) for n, _ in inst.options["node_zone"]} == set(inst.nodes)
    pr = default_pruning(inst)
    assert sites <= pr["reposition_targets"]
    # JSON round trip and determinism
    txt = inst.to_json()
    again = Instance.from_json(txt)
    assert again == inst and again.to_json() == txt and again.validate() == []
    twin = dn.make_nyc_instance(seed=0, n_bikes=6, window_h=2.0)
    assert twin.to_json() == txt
    # arcs + terminal pre-check (9) with the recommended pruning
    lib = build_arcs(inst, **pr)
    assert lib.infeasible_bikes == [] and len(lib) > 0
    assert all(lib.terminal_arcs(k) for k in lib.bikes())
    assert time.time() - t0 < 60.0


def test_make_nyc_instance_options(box, zw_box):
    other = dn.make_nyc_instance(seed=1, n_bikes=6, window_h=2.0)
    base = dn.make_nyc_instance(seed=0, n_bikes=6, window_h=2.0)
    assert other.to_json() != base.to_json()
    # the GeoDa fallback stays selectable and keeps its warning + NTA-2010 codes
    geo = dn.make_nyc_instance(seed=0, n_bikes=6, window_h=2.0,
                               zone_weights=dn.GeoDaZoneWeights(box=box, warn=False))
    assert geo.meta["zone_weights_source"] == "geoda_fallback" and "MN17" in geo.meta["zones_used"]
    assert "FALLBACK" in geo.meta["zone_weights_warning"]
    # explicit site coordinates, toy costs, injected zone weights (no fallback warning), 4 h window
    sites = [(40.7484, -73.9857), (40.7420, -73.9897)]
    inst = dn.make_nyc_instance(seed=2, n_bikes=4, window_h=4.0, orders_per_bike_hour=1.0,
                                cost_variant="toy", site_latlon=sites, zone_weights=zw_box,
                                pruning={"tau_max": 4})
    assert inst.validate() == [] and inst.H == 48 and len(inst.orders) == 16
    assert [f.node for f in inst.facilities] == [box.snap(*s) for s in sites]
    assert inst.kappa == 1.0 and inst.pi == 2.0 and inst.facilities[0].F == 20.0
    assert all((o.P, o.w, o.v) == (100.0, 12.0, 24.0) for o in inst.orders)
    assert inst.options["tau_max"] == 4 and inst.meta["zone_weights_warning"] is not None
    assert inst.meta["params"]["n_orders"] == 16 and inst.meta["window_h"] == [17.0, 21.0]
    assert Instance.from_json(inst.to_json()) == inst
    with pytest.raises(ValueError):
        dn.make_nyc_instance(seed=0, n_bikes=2, window_h=2.0, facilities_spec={"mode": "separated"},
                             zone_weights=zw_box)


def test_cost_variants_agree_with_costs_module():
    """Cross-check with ``ebike_swap_sim.costs`` (written by another task) when present."""
    costs_mod = pytest.importorskip("ebike_swap_sim.costs")
    for variant in dn.COST_VARIANTS:
        for window_h in (2.0, 4.0, 8.0):
            mine = dn.cost_variant_params(variant, window_h)
            theirs = costs_mod.load_cost_calibration(variant=variant, window_h=window_h)
            for key in ("kappa", "pi", "F", "F_hub", "bB", "bC", "Fhat", "bhat", "chat"):
                assert mine["costs"][key] == pytest.approx(theirs["costs"][key]), (variant, window_h, key)
            assert mine["demand_spec"] == pytest.approx(theirs["demand_spec"]), (variant, window_h)
            assert mine["services_spec"] == pytest.approx(theirs["services_spec"]), (variant, window_h)


def test_nyc_release_profile_is_the_r2_block_step(box):
    """Units review F1 / F2 / F3: make_nyc_instance samples releases from the R2.2 block
    profile as a step function (the synthetic family's object), records the flat
    meta['costs'] and the unreachable DOHMH share, and accepts cuisine_map_overrides."""
    from ebike_swap_sim.generator import TIME_PROFILE_R2, TimeDependentGenerator, block_profile
    cfg = dn.assumed_block_config()
    assert [b["name"] for b in cfg["blocks"]] == ["lunch", "dinner", "late"]
    assert cfg["rest_share"] == 0.15 and cfg["weekend_factor"] == 1.15 and cfg["status"] == "assumption"
    dens, ref = block_profile(cfg), block_profile(TIME_PROFILE_R2)
    assert all(dens(h / 4.0) == pytest.approx(ref(h / 4.0)) for h in range(96))
    # a step at 17:30, not a ramp from 17:00: flat before, flat after, ratio = block / rest density
    tg = TimeDependentGenerator(cfg, (17.0, 20.0), 36.0)
    assert tg.rate(17.25) == pytest.approx(tg.rate(17.0)) and tg.rate(17.75) == pytest.approx(tg.rate(18.5))
    assert tg.rate(17.75) / tg.rate(17.25) == pytest.approx((0.45 / 4.0) / (0.15 / 14.0))
    ramp = TimeDependentGenerator(dn.assumed_hourly_profile(), (17.0, 20.0), 36.0)   # the old (wrong) object
    assert ramp.rate(17.0) < ramp.rate(17.25) < ramp.rate(17.5) < ramp.rate(18.0)      # interpolated ramp, no step
    inst = dn.make_nyc_instance(seed=0, n_bikes=6, window_h=2.0)
    hp = inst.meta["hourly_profile_used"]
    assert hp["kind"] == "block_step" and hp["config"]["blocks"][1]["start_h"] == 17.5
    assert hp["hourly_density"][17] == pytest.approx(0.45 / 4.0) and hp["hourly_density"][16] == pytest.approx(0.15 / 14.0)
    # F2: flat meta['costs'] as generator.make_synthetic_instance writes it (2 h -> window scale 0.5)
    co = inst.meta["costs"]
    assert co["variant"] == "usd_sunk" and co["window_h"] == 2.0 and co["window_scale"] == 0.5
    assert (co["kappa"], co["pi"], co["P"], co["w"], co["v"], co["q_res"], co["rho"]) == (0.12, 0.32, 30.0, 18.0, 36.0, 1, 0.5)
    assert (co["F"], co["bB"], co["bC"]) == pytest.approx((6.015, 0.166, 0.041)) and co["f"] == 20.0 and co["vreb"] == 1.0
    assert set(co) >= {"kappa", "pi", "pi_peak", "F", "F_hub", "bB", "bC", "Fhat", "bhat", "chat", "P", "w", "v", "f", "vreb"}
    # F3: unreachable 'other' share recorded; sensitivity remapping lowers it and is recorded
    assert 0.2 < inst.meta["unmapped_share_in_box"] < 0.35 and inst.meta["cuisine_map_overrides"] is None
    assert inst.meta["n_restaurants_unmapped_in_box"] == sum(inst.meta["unmapped_cuisines_in_box"].values())
    assert inst.meta["unmapped_cuisines_in_box"].get("Coffee/Tea", 0) > 100
    sens = dn.make_nyc_instance(seed=0, n_bikes=6, window_h=2.0, cuisine_map_overrides=dn.CUISINE_MAP_CAFES_AS_AMERICAN)
    assert sens.meta["unmapped_share_in_box"] < 0.5 * inst.meta["unmapped_share_in_box"]
    assert sens.meta["cuisine_map_overrides"]["Coffee/Tea"] == "American" and sens.validate() == []
    assert "Coffee/Tea" not in sens.meta["unmapped_cuisines_in_box"]
    with pytest.raises(ValueError):
        dn.make_nyc_instance(seed=0, n_bikes=2, window_h=2.0, cuisine_map_overrides={"Coffee/Tea": "Cafe"})
