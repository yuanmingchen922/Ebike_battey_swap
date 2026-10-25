"""Tests of the round-5 instance options (``notes/reading_to_model.md``): the eBaaS energy
calibration (A1), the data-grounded stressed families ``r5_stress8h`` / ``r5_stress4h`` with
the TOU tariff (M5), the home-charging counterfactual (A5), the fleet x spare x pack sweep
(A6), cyclic transfer routes (M8), battery lock-out (M9) and the data levers (M10).

Invariants: every round-1..4 family regenerates byte-identically (md5 of the JSON computed
before the round-5 edits), every option validates, round-trips through JSON and builds an
arc library, and the counterfactual / lock-out / cyclic variants keep the demand side of the
network instance of the same seed (``experiments.common.demand_md5``)."""
from __future__ import annotations

import hashlib
import math
import os
import sys
import warnings

import pytest

from ebike_swap_sim import Instance, build_arcs, check
from ebike_swap_sim import costs as cm
from ebike_swap_sim import generator as G
from ebike_swap_sim.config import ENERGY_CALIBRATIONS, EBAAS_FACTS, SimConfig, energy_calibration

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from experiments import common as C  # noqa: E402

#: md5 of ``experiments.common.make_instance(family, seed).to_json()`` for every family of
#: rounds 1-4, computed on 2026-10-17 BEFORE the round-5 edits of generator.py / costs.py /
#: config.py.  Old families must regenerate byte-identically.
OLD_FAMILY_MD5 = {
    ("large", 0): "2479a4a323618f7999824a1d2f2ada34",
    ("large", 1): "04cf19097b7ce337e0ee4156275196a9",
    ("medium", 0): "f396c24436a0af27762c6acddb9b12c4",
    ("medium", 1): "56b81aedd20998c9c176ee64d6b39676",
    ("nyc4h", 0): "896714eda092a8323f6da1021fa71428",
    ("nyc4h", 1): "5c90fb1c0a70d0e8ad110ddf61ac4494",
    ("nyc4h_stress", 0): "0f1365225dce4e5c44a49c53a8536649",
    ("nyc4h_stress", 1): "ed27873ca298d004ec488b8b58433f18",
    ("nyc4h_stress2", 0): "0e7a2526b2585241940ed23a29798b0c",
    ("nyc4h_stress2", 1): "db2efb4df57790dbfd13b7f5e9113539",
    ("p7", 0): "e76474cbb587b0cd820a76bcc89272f1",
    ("small", 0): "0bc8e4831dda6f00c0703b8062821974",
    ("small", 1): "8087e4c521005089c892c4af1e550910",
    ("toy", 0): "e1941549ff5b9cb5d3206164cd4530dc",
    ("usd4h", 0): "442e9dc1a391ce225656a5037f47cb87",
    ("usd4h", 1): "b6045644e277e2aac305dc1bae4f0243",
    ("usd4h_large", 0): "5e56fec146e41d1063fdb4ef7444fcda",
    ("usd4h_toyunits", 0): "0d4017fa178f7ac1c080aed157e876af",
    ("usd4h_toyunits", 1): "1fb0446b27a49e11f2c9b13992eaaf38",
    ("usd8h", 0): "cbf8900aaed5b05356b3d2989f2fa318",
    ("usd8h", 1): "62aefb6680ca6234fc356124c3b2fded",
}


def _md5(inst: Instance) -> str:
    return hashlib.md5(inst.to_json().encode()).hexdigest()


def _roundtrip(inst: Instance) -> None:
    assert inst.validate() == []
    back = Instance.from_json(inst.to_json())
    assert back == inst and back.to_json() == inst.to_json()


@pytest.fixture(scope="module")
def net4():
    return G.make_r5_instance("r5_stress4h", seed=0)


# ---------------------------------------------------------------------------
# invariants: old families
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("family,seed", sorted(OLD_FAMILY_MD5))
def test_old_families_byte_identical(family, seed):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        inst = C.make_instance(family, seed=seed)
    assert _md5(inst) == OLD_FAMILY_MD5[(family, seed)]
    for key in ("energy_calibration", "tariff", "home_charging", "lockout", "cyclic_services", "r5"):
        assert key not in inst.meta


def test_old_defaults_untouched():
    """Round-5 keys are opt-in: none of the shared default dicts gained a key."""
    assert set(G.DEFAULT_SERVICES_SPEC) == {"every", "first", "handling_min", "U", "f", "vreb", "site_site",
                                            "site_site_every"}
    assert G.DEFAULT_PHYSICS["wh_per_km"] == 12.0 and SimConfig().wh_per_km == 12.0
    assert "price_peak_hours" not in G.DEFAULT_FACILITIES_SPEC
    leg = ENERGY_CALIBRATIONS["legacy"]
    cfg = SimConfig()
    assert (leg["wh_per_km"], leg["wh_per_m_climb"], leg["wh_per_light"]) == \
        (cfg.wh_per_km, cfg.wh_per_m_climb, cfg.wh_per_light)
    assert leg["eps_wh"] * 12 == cfg.battery_capacity_wh and leg["energy_rounding"] == "per_leg"


# ---------------------------------------------------------------------------
# A1: energy calibration
# ---------------------------------------------------------------------------
def test_energy_calibration_resolution():
    e = energy_calibration("ebaas")
    assert (e["wh_per_km"], e["eps_wh"], e["L"], e["energy_rounding"]) == (25.0, 25.0, 24, "concat")
    assert e["battery_wh"] == 600.0 and e["q_res"] == 2 and e["p_ch_kw"] == pytest.approx(1 / 3)
    assert 1000.0 / e["wh_per_km"] == EBAAS_FACTS["km_per_kwh"]       # 40 km per kWh
    assert energy_calibration("ebaas", pack_kwh=1.0)["L"] == 40
    assert energy_calibration("ebaas", eps_wh=50.0)["p_ch_kw"] == pytest.approx(2 / 3)
    assert energy_calibration("legacy")["L"] == 12
    with pytest.raises(KeyError):
        energy_calibration("nope")
    with pytest.raises(KeyError):
        energy_calibration("ebaas", wh_per_mile=1.0)
    with pytest.raises(ValueError):
        energy_calibration("ebaas", pack_kwh=0.61)                    # not an integer number of levels


def test_ebaas_calibration_on_a_legacy_call():
    old = G.make_synthetic_instance(seed=2, n_bikes=3, n_orders=8, H=24)
    new = G.make_synthetic_instance(seed=2, n_bikes=3, n_orders=8, H=24, energy_calibration="ebaas")
    _roundtrip(new)
    assert (new.L, new.disc.eps_kwh, new.q_res) == (24, pytest.approx(0.025), 2)
    assert new.option("energy_rounding") == "concat" and old.option("energy_rounding") == "per_leg"
    assert new.meta["energy_calibration"]["name"] == "ebaas"
    assert new.meta["params"]["energy_calibration"]["wh_per_km"] == 25.0
    # routes: 25 Wh/km plus the climb term, no signal term; same geometry and orders
    for key, r in new.routes.items():
        assert r.E_kwh >= 0.025 * r.d_km - 1e-12 and r.d_km == old.routes[key].d_km
    assert [(o.o, o.d, o.r, o.a, o.b) for o in new.orders] == [(o.o, o.d, o.r, o.a, o.b) for o in old.orders]
    # explicit keys still win
    alt = G.make_synthetic_instance(seed=2, n_bikes=3, n_orders=8, H=24, energy_calibration="ebaas",
                                    costs={"q_res": 1}, pruning={"energy_rounding": "per_leg"})
    assert alt.q_res == 1 and alt.option("energy_rounding") == "per_leg"


# ---------------------------------------------------------------------------
# M5: stressed families, profile, TOU
# ---------------------------------------------------------------------------
def test_r5_time_profile():
    dens = G.block_profile(G.R5_TIME_PROFILE)
    assert G.profile_integral(dens) == pytest.approx(1.0, abs=1e-6)
    assert dens(7.9) == 0.0 and dens(22.1) == 0.0 and dens(3.0) == 0.0
    for (lo, hi) in EBAAS_FACTS["meal_peaks"]:
        assert dens((lo + hi) / 2) == pytest.approx(2.0 * dens(15.0))   # peak_ratio 2
    assert dens(9.0) == pytest.approx(dens(15.0)) == pytest.approx(dens(20.0)) == pytest.approx(1 / 18)


@pytest.mark.parametrize("family,H,start,n_orders", [("r5_stress4h", 48, 16.0, 48), ("r5_stress8h", 96, 10.5, 96)])
def test_r5_families_build(family, H, start, n_orders):
    inst = G.make_r5_instance(family, seed=0)
    _roundtrip(inst)
    assert inst.to_json() == G.make_r5_instance(family, seed=0).to_json()           # deterministic
    assert inst.H == H and inst.L == 24 and len(inst.orders) == n_orders and len(inst.bikes) == 6
    assert inst.meta["window_h"] == [start, start + H / 12]
    assert inst.meta["family"] == family and inst.option("energy_rounding") == "concat"
    assert all(math.ceil(0.25 * 24) <= b.q0 <= 12 for b in inst.bikes)
    assert [(f.B, f.C) for f in inst.facilities] == [(2, 1)] * 3
    # TOU: price peak 08-22 h covers both windows -> every slot at the peak price
    assert inst.meta["price_peak_hours"] == [8.0, 22.0]
    assert set(inst.pi.values()) == {0.442}
    assert inst.meta["costs"]["pi"] == 0.132 and inst.meta["costs"]["pi_peak"] == 0.442
    assert inst.meta["time_profile"]["name"] == "r5_ebaas_meal_peaks"
    inten = inst.meta["r5"]["intensity"]
    assert 5.0 < inten["est_km_per_bike_hour"] < 12.0 and inten["packs_per_bike"] > 1.0
    assert inst.meta.get("rolling_horizon_only", False) == (family == "r5_stress8h")
    # releases inside the window and only in eBaaS operating hours
    for rec in inst.meta["orders"]:
        hour = start + rec["release_min"] / 60.0
        assert 8.0 <= hour < 22.0
    # F, bB scale with the window (R2.1)
    assert inst.facilities[0].F == pytest.approx(12.03 * H / 48)


def test_r5_family_kwargs_are_generator_kwargs():
    """``experiments.common.FAMILIES`` can register the dicts verbatim (builder pops the flag)."""
    for family, kw in G.R5_FAMILIES.items():
        clean = {k: v for k, v in kw.items() if k != "rolling_horizon_only"}
        inst = G.make_synthetic_instance(seed=1, name="x", **clean)
        assert _md5(inst) != ""
        ref = G.make_r5_instance(family, seed=1)
        assert [(o.o, o.d, o.r) for o in inst.orders] == [(o.o, o.d, o.r) for o in ref.orders]


@pytest.mark.parametrize("family", sorted(G.R5_FAMILIES))
def test_r5_arc_library_builds(family):
    inst = G.make_r5_instance(family, seed=0)
    est = G.estimate_arcs(inst, C.pruning_for(inst, reachable=True), sample_bikes=1)
    assert est["infeasible_bikes"] == [] and est["n_arcs"] > 0
    assert est["options"]["energy_rounding"] == "concat"


# ---------------------------------------------------------------------------
# A5: home charging
# ---------------------------------------------------------------------------
def test_home_charging_counterfactual(net4):
    home = G.make_r5_instance("r5_stress4h", seed=0, home_charging=True)
    _roundtrip(home)
    assert C.demand_md5(home) == C.demand_md5(net4)
    assert C.demand_key(home) == C.demand_key(net4)
    hc = home.meta["home_charging"]
    assert [f.id for f in home.facilities] == ["HOME1", "HOME2", "HOME3"]
    assert [list(f.node) for f in home.facilities] == net4.meta["depots"]
    assert home.services == [] and home.P_grid == {} and home.Cset == []
    # sigma = ceil((L - ceil(0.25 L)) eps / eta / 0.24 kW / Delta) = ceil(0.5 kWh / 0.24 kW * 12) = 25
    assert hc["charger_kw"] == 0.24 and hc["return_level"] == 6 and hc["sigma_slots"] == 25
    for f in home.facilities:
        assert f.swap and not f.charge and f.sigma == 25 and f.M == 6 and f.B == f.K and f.C == 0
        assert (f.F, f.bB, f.bC, f.R_end) == (0.0, 0.0, 0.0, 0)
    # stock never binds and (18) stays slack: (1 - rho) sum B >= max swaps
    assert (1 - home.rho) * sum(f.B for f in home.facilities) >= hc["max_swaps"]
    assert hc["removed_facilities"] == ["S1", "S2", "S3"]
    # arc library: swap arcs last sigma slots
    lib = build_arcs(home, **C.pruning_for(home, reachable=True))
    swaps = [a for a in lib.arcs if a.kind == "swap"]
    assert swaps and all(a.u - a.l == 25 and a.fac.startswith("HOME") for a in swaps)


def test_home_charging_parameters_and_rho_one():
    base = G.make_synthetic_instance(seed=0, n_bikes=2, n_orders=4, H=24)
    fast = G.home_charging_counterfactual(base, charger_kw=1.0, return_frac=0.5)
    assert fast.facilities[0].sigma == math.ceil((12 - 6) * 0.05 / 0.9 / 1.0 * 12 - 1e-9)
    assert C.demand_md5(fast) == C.demand_md5(base)
    from ebike_swap_sim import toy_instance
    toy = G.home_charging_counterfactual(toy_instance())          # rho = 1 in the toy
    assert toy.rho == 0.0 and toy.meta["home_charging"]["rho_written"] == 1.0
    assert [f.node for f in toy.facilities] == ["A"]
    with pytest.raises(ValueError):
        G.home_charging_counterfactual(base, charger_kw=0.0)
    with pytest.raises(ValueError):
        G.home_charging_counterfactual(base, homes=[(99, 99)])


def test_home_charging_runs_with_the_baseline():
    from ebike_swap_sim.baseline import run_baseline
    home = G.make_synthetic_instance(seed=1, n_bikes=3, n_orders=8, window_h=2.0, energy_calibration="ebaas",
                                     home_charging={"charger_kw": 0.24})
    lib = build_arcs(home, **C.pruning_for(home))
    sched, _ = run_baseline(home, lib)
    rep = check(home, lib, sched)
    assert not [f for f in rep["families"] if f not in C.BASELINE_REPORT_ONLY]


# ---------------------------------------------------------------------------
# M9: battery lock-out
# ---------------------------------------------------------------------------
def test_lockout_data(net4):
    lock = G.make_r5_instance("r5_stress4h", seed=0, lockout={"share": 0.5, "seed": 3})
    _roundtrip(lock)
    assert C.demand_md5(lock) == C.demand_md5(net4)
    lo = lock.meta["lockout"]
    assert lo["n_locked"] == 3 and lo["total_spares"] == 6 and lo["sink"] == "LOCK"
    sink = lock.facility("LOCK")
    assert sink.charge and not sink.swap and sink.B == 0 and sink.K == 3 and sink.P_kw < lock.disc.p_ch_kw
    assert (sink.F, sink.bB, sink.bC, sink.Fhat) == (0.0, 0.0, 0.0, 0.0)
    forced = lock.options["forced_transfers"]
    assert [r["service"] for r in forced] == lo["services"] and all(r["level"] is None for r in forced)
    for r in forced:
        s = lock.service(r["service"])
        assert s.d_fac == "LOCK" and s.u == s.l + 1 and s.U == 1 and s.f == 0.0 and s.vreb == 0.0
        assert 1 <= s.l < lock.H
    from collections import Counter
    per_site = Counter(lo["sites"])
    assert all(per_site[j] <= net4.facility(j).B for j in per_site)
    assert not [s for s in lock.services if s.o_fac == "LOCK"]          # nothing ever leaves the sink
    # same seed -> same draw; given slots respected; level 'full'
    again = G.add_battery_lockout(net4, share=0.5, seed=3)
    assert again.meta["lockout"]["slots"] == lo["slots"]
    given = G.add_battery_lockout(net4, share=0.2, slots=[10], level="full")
    assert given.meta["lockout"]["slots"] == [10] and given.options["forced_transfers"][0]["level"] == 24
    assert G.add_battery_lockout(net4, share=0.0).services == net4.services
    with pytest.raises(ValueError):
        G.add_battery_lockout(net4, share=0.5, slots=[3])               # too few slots
    with pytest.raises(ValueError):
        G.add_battery_lockout(net4, level="half")
    est = G.estimate_arcs(lock, C.pruning_for(lock, reachable=True), sample_bikes=1)
    assert est["infeasible_bikes"] == []


def test_lockout_fixed_in_the_ilp():
    pytest.importorskip("gurobipy")
    from ebike_swap_sim import ilp
    inst = G.make_synthetic_instance(seed=0, n_bikes=2, n_orders=4, H=12, L=6,
                                     lockout={"share": 0.25, "seed": 0, "level": "any"})
    lib = build_arcs(inst)
    mdl = ilp.build_model(inst, lib, threads=1, time_limit=60)
    assert G.apply_forced_transfers(mdl) == inst.meta["lockout"]["n_locked"] == 3
    sched, st = mdl.solve()
    assert st["status"] == "OPTIMAL"
    assert all(sched.h[r["service"]] == 1 for r in inst.options["forced_transfers"])
    assert check(inst, lib, sched)["ok"]
    full = G.add_battery_lockout(G.make_synthetic_instance(seed=0, n_bikes=2, n_orders=4, H=12, L=6),
                                 share=0.25, level="full")
    lib2 = build_arcs(full)
    m2 = ilp.build_model(full, lib2, threads=1, time_limit=60)
    G.apply_forced_transfers(m2)
    s2, st2 = m2.solve()
    assert st2["status"] == "OPTIMAL"
    assert all(s2.z.get((r["service"], full.L), 0) == 1 for r in full.options["forced_transfers"])
    m3 = ilp.build_model(inst, lib, threads=1, time_limit=60, no_transfers=True)
    with pytest.raises(ValueError):
        G.apply_forced_transfers(m3)


# ---------------------------------------------------------------------------
# M8: cyclic routes
# ---------------------------------------------------------------------------
def _check_tours(inst):
    cyc = inst.meta["cyclic_services"]
    cycle, n_legs = cyc["cycle"], cyc["legs_per_tour"]
    assert n_legs == len(cycle)
    legs = list(zip(cycle, cycle[1:] + cycle[:1]))
    svcs = list(inst.services)
    i = 0
    while i < len(svcs):
        tour = [svcs[i]]
        while i + len(tour) < len(svcs) and svcs[i + len(tour)].l == tour[-1].u \
                and (svcs[i + len(tour)].o_fac == tour[-1].d_fac) and len(tour) < n_legs:
            tour.append(svcs[i + len(tour)])
        assert tour[0].l in cyc["tour_starts"]
        for k, s in enumerate(tour):
            assert (s.o_fac, s.d_fac) == legs[k] and s.u <= inst.H and s.U == cyc["cap"]
        i += len(tour)
    return cyc


def test_cyclic_services(net4):
    cyc_inst = G.make_r5_instance("r5_stress4h", seed=0, services_spec={"mode": "cyclic", "U": 4})
    _roundtrip(cyc_inst)
    assert C.demand_md5(cyc_inst) == C.demand_md5(net4) and net4.services == []
    cyc = _check_tours(cyc_inst)
    assert cyc["complete_tours"] >= 3 and cyc["tour_starts"] == [2, 14, 26, 38]
    assert sum(s.f for s in cyc_inst.services[:3]) == pytest.approx(cyc_inst.meta["costs"]["f"])
    sep = G.make_synthetic_instance(seed=0, n_bikes=3, n_orders=8, H=48,
                                    facilities_spec={"mode": "separated", "n_hubs": 1},
                                    services_spec={"mode": "cyclic", "tour_every": 24, "cap": 5,
                                                   "split_f": False, "night_tour_start_h": 18.0})
    _roundtrip(sep)
    cyc2 = _check_tours(sep)
    assert "HUB1" in cyc2["cycle"] and cyc2["cap"] == 5 and cyc2["night_tour_slot"] == 6
    assert 6 in cyc2["tour_starts"] and all(s.f == 5.0 for s in sep.services)
    lib = build_arcs(sep, **G.default_pruning(sep))
    assert len(lib) > 0
    with pytest.raises(ValueError):
        G.make_synthetic_instance(seed=0, n_bikes=2, n_orders=4, services_spec={"mode": "ring"})
    with pytest.raises(ValueError):
        G.make_synthetic_instance(seed=0, n_bikes=2, n_orders=4,
                                  services_spec={"mode": "cyclic", "tour_order": ["S1", "S2"]})
    assert G.cyclic_tour_order(["a", "b", "c"], lambda x, y: abs(ord(x) - ord(y))) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# A6: fleet x spare x pack sweep
# ---------------------------------------------------------------------------
def test_fleet_spare_pack_sweep(net4):
    grid = G.fleet_spare_pack_grid()
    assert len(grid) == 4 * 4 * 3 and grid[0] == {"n_bikes": 4, "B": 1, "pack_kwh": 0.5}
    small = G.make_fleet_sweep_instance("r5_stress4h", 0, n_bikes=4, B=1, pack_kwh=0.6)
    big = G.make_fleet_sweep_instance("r5_stress4h", 0, n_bikes=10, B=4, pack_kwh=0.6)
    for inst in (small, big):
        _roundtrip(inst)
        assert inst.orders == net4.orders                       # demand fixed at the nominal 6 bikes
    assert [b.q0 for b in small.bikes] == [b.q0 for b in net4.bikes][:4]
    assert [b.q0 for b in big.bikes][:6] == [b.q0 for b in net4.bikes]
    assert [f.B for f in big.facilities] == [4, 4, 4]
    one = G.make_fleet_sweep_instance("r5_stress4h", 0, n_bikes=6, B=2, pack_kwh=1.0)
    _roundtrip(one)
    fs = one.meta["fleet_sweep"]
    assert one.L == 40 and one.disc.eps_kwh == pytest.approx(0.025) and one.disc.p_ch_kw == pytest.approx(1 / 3)
    assert one.facilities[0].bB == pytest.approx(net4.facilities[0].bB / 0.6)
    assert one.facilities[0].bhat == pytest.approx(450.0 / 0.6)
    assert fs["allocated_bike_cost"]["rider_wage_per_window"] == pytest.approx(22.13 * 4)
    assert fs["allocated_bike_cost"]["allocated_per_bike_window"] > fs["allocated_bike_cost"]["bike_capex_per_window"]
    assert fs["n_orders_fixed"] == 48 and fs["total_spares"] == 6
    est = G.estimate_arcs(one, C.pruning_for(one, reachable=True), sample_bikes=1)
    assert est["infeasible_bikes"] == []


# ---------------------------------------------------------------------------
# M10: data levers
# ---------------------------------------------------------------------------
def test_swap_position_variants(net4):
    var = G.swap_position_variants(net4, M_values=(1, 2, 3))
    per = cm.position_cost_per_window(400.0, 10.0, 0.07, 4.0)
    for M, inst in var.items():
        _roundtrip(inst)
        assert all(f.M == M for f in inst.facilities if f.swap)
        assert inst.facilities[0].F == pytest.approx(net4.facilities[0].F + (M - 1) * per)
        assert inst.facilities[0].Fhat == pytest.approx(net4.facilities[0].Fhat + (M - 1) * 400.0)
        assert C.demand_md5(inst) == C.demand_md5(net4)
    assert net4.facilities[0].M == 1                       # the input is not mutated
    with pytest.raises(ValueError):
        G.swap_position_variants(net4, M_values=(0,))


def test_charger_speed_variants(net4):
    var = G.charger_speed_variants("r5_stress4h", seed=0)
    assert sorted(var) == [25.0, 50.0]
    assert (var[25.0].L, var[50.0].L) == (24, 12)
    assert var[25.0].disc.p_ch_kw == pytest.approx(1 / 3) and var[50.0].disc.p_ch_kw == pytest.approx(2 / 3)
    assert var[25.0].q_res == 2 and var[50.0].q_res == 1                  # 50 Wh reserve either way
    for inst in var.values():
        _roundtrip(inst)
        assert inst.orders == net4.orders and inst.option("energy_rounding") == "concat"


def test_site_power_cap_sweep_and_demand_charge(net4):
    sweep = G.site_power_cap_sweep(net4)
    p_ch = net4.disc.p_ch_kw
    assert [round(P / p_ch) for P, _ in sweep] == [0, 1]                  # C_j = 1 per site
    for P, inst in sweep:
        assert all(f.P_kw == pytest.approx(P) for f in inst.facilities if f.charge)
        assert C.demand_md5(inst) == C.demand_md5(net4)
    lock = G.add_battery_lockout(net4, share=0.2)
    sw2 = G.site_power_cap_sweep(lock, multiples=[0, 2])
    assert sw2[1][1].facility("LOCK").P_kw < p_ch and sw2[1][1].facility("S1").P_kw == pytest.approx(2 * p_ch)
    prox = cm.demand_charge_proxy({P: v for (P, _), v in zip(sweep, [None, 600.0])}, 15.0, 4.0, n_sites=3)
    assert prox["best"]["P_kw"] == pytest.approx(p_ch)
    assert prox["best"]["total"] == pytest.approx(600.0 + 3 * p_ch * 15.0 / 30 * 4 / 16)
