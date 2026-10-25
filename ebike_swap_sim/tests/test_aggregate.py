"""Tests of the aggregated integer-flow form of E2 (plan item O1, ``aggregate.py`` and
``ilp.build_model(..., aggregate=True)``): the toy optima 12.5 / 11.2 / 106 and every
other documented toy what-if are reproduced, the decomposed per-bike schedules pass
``evaluate.check`` and are priced to the Gurobi objective, MIP starts are mapped,
multi-bike supplies, multi-source and non-closed (``groups``) libraries agree with the
per-bike model, and the shared-model entry point ``ilp.build_submodel`` works."""
from __future__ import annotations

import pytest

from ebike_swap_sim import Bike, Schedule, battery_swap_p7_instance, build_arcs, check, cost, toy_instance
from ebike_swap_sim.aggregate import AggregatedNetwork, AggregationError, aggregate_network, decompose_flow
from ebike_swap_sim.arcs import ArcLibrary, Arc, arc_key

gp = pytest.importorskip("gurobipy")

from ebike_swap_sim import ilp  # noqa: E402
from ebike_swap_sim.ilp import build_model, build_submodel, solve  # noqa: E402

KW = {"threads": 3, "time_limit": 60.0}


def _doc_schedule(lib: ArcLibrary) -> Schedule:
    """E2_Example p.14 optimal schedule (same as tests/test_ilp.py)."""
    f = lib.find
    bike1 = [a.id for a in (
        f(1, "deliver", ("A", 0, 2), order=1), f(1, "move", ("B", 2, 1), dst=("A", 3, 0)),
        f(1, "swap", ("A", 3, 0), fac="A"), f(1, "deliver", ("A", 4, 2), order=3),
        f(1, "wait", ("B", 6, 1)), f(1, "wait", ("B", 7, 1)), f(1, "term", ("B", 8, 1), fac="A"))]
    bike2 = [a.id for a in (f(2, "deliver", ("A", 0, 2), order=2),
                            *[f(2, "wait", ("B", t, 1)) for t in range(2, 8)],
                            f(2, "term", ("B", 8, 1), fac="A"))]
    return Schedule(x={1: bike1, 2: bike2}, u={1: 0, 2: 0, 3: 0},
                    c={("C", 0, 6): 1, ("C", 1, 7): 1}, h={1: 1, 2: 1}, z={(1, 2): 1, (2, 0): 1})


def _pair(inst, lib, **kw):
    """Solve the per-bike and the aggregated model; both must be certified."""
    s0, st0 = solve(inst, lib, **KW, **kw)
    s1, st1 = solve(inst, lib, aggregate=True, **KW, **kw)
    return (s0, st0), (s1, st1)


def _assert_same(inst, lib, r0, r1):
    (s0, st0), (s1, st1) = r0, r1
    assert st0["status"] == st1["status"]
    if st0["obj"] is None:
        assert st1["obj"] is None and s1 is None
        return
    assert st1["obj"] == pytest.approx(st0["obj"], abs=1e-6)
    assert check(inst, lib, s1)["ok"]
    assert cost(inst, lib, s1)["total"] == pytest.approx(st1["obj"])
    assert set(s1.x) == {b.id for b in inst.bikes}
    for k in s1.x:                                   # one source-to-sink path per bike
        path = s1.path(k, lib)
        assert path[0].src == lib.source(k) and path[-1].kind == "term"
        assert all(a.k == k for a in path)


# ---------------------------------------------------------------------------
# documented toy optima (E2 pp.10-15)
# ---------------------------------------------------------------------------
def test_toy_12_5_11_2_106_aggregated():
    inst = toy_instance()
    lib = build_arcs(inst)
    sched, st = solve(inst, lib, aggregate=True, **KW)
    assert st["status"] == "OPTIMAL" and st["obj"] == pytest.approx(12.5)
    c = st["cost"]
    assert (c["C_travel"], c["C_elec"], c["C_orders_parts"]["response"], c["C_reb"]) == \
        pytest.approx((4.0, 0.1, 6.0, 2.4))
    assert check(inst, lib, sched)["ok"] and sched.meta["aggregate"] == "single"
    assert st["switches"]["aggregate"] is True
    assert st["n_agg_arcs"] < st["n_arcs"] == 470
    assert st["n_vars"] < 557 and st["rows_by_family"]["(5)"] < 2 * 82

    inst0 = toy_instance()
    inst0.rho = 0.0
    _, st0 = solve(inst0, build_arcs(inst0), aggregate=True, **KW)
    assert st0["obj"] == pytest.approx(11.2)

    sched_n, st_n = solve(inst, lib, aggregate=True, no_transfers=True, **KW)
    assert st_n["obj"] == pytest.approx(106.0) and sum(sched_n.u.values()) == 1


def test_default_per_bike_model_is_unchanged():
    inst = toy_instance()
    lib = build_arcs(inst)
    mdl = build_model(inst, lib)
    assert mdl.agg is None and "aggregate" not in mdl.switches
    sched, st = mdl.solve()
    assert st["n_vars"] == 557 and st["n_rows"] == 315 and "n_agg_arcs" not in st
    assert "aggregate" not in sched.meta


@pytest.mark.parametrize("kw", [
    {"lexicographic": True}, {"lexicographic": True, "no_transfers": True},
    {"zeta": 1.0}, {"budget": 0.0}, {"fixed_facilities": False}, {"colocated": True},
    {"battery_swap_v1_bounds": True}, {"zeta": 1.0, "no_transfers": True},
])
def test_toy_switches_agree(kw):
    inst = toy_instance()
    lib = build_arcs(inst)
    r0, r1 = _pair(inst, lib, **kw)
    if kw.get("colocated"):
        mdl = build_model(inst, lib, colocated=True)
        inst, lib = mdl.inst, mdl.lib
    _assert_same(inst, lib, r0, r1)


def test_dummy_terminal_and_q_res():
    inst = toy_instance()
    inst.q_res = 1
    lib = build_arcs(inst)
    _assert_same(inst, lib, *_pair(inst, lib))                       # 206.5
    lib_d = build_arcs(inst, dummy_terminal_cost=50.0)
    r0, r1 = _pair(inst, lib_d)
    _assert_same(inst, lib_d, r0, r1)
    assert r1[1]["obj"] == pytest.approx(112.5)
    assert r1[1]["cost"]["C_dummy_terminal"] == pytest.approx(100.0)


def test_battery_swap_p7_agrees():
    inst = battery_swap_p7_instance()
    lib = build_arcs(inst)
    _assert_same(inst, lib, *_pair(inst, lib))


# ---------------------------------------------------------------------------
# supplies > 1, several sources, reachable pruning, non-closed classes
# ---------------------------------------------------------------------------
def _toy_more_bikes():
    inst = toy_instance()
    inst.bikes = inst.bikes + [Bike(3, "A", 2), Bike(4, "B", 1)]
    inst.reindex()
    return inst


@pytest.mark.parametrize("pruning", [{}, {"reachable_pruning": True}])
def test_multi_bike_supplies_and_sources(pruning):
    inst = _toy_more_bikes()
    lib = build_arcs(inst, **pruning)
    net = aggregate_network(inst, lib)
    assert net.mode == "single" and net.closed
    assert net.commodities[0].supply == {("A", 0, 2): 3, ("B", 0, 1): 1}
    assert max(net.ub) == 4 and all(u == 1 for a, u in zip(net.arcs, net.ub) if a.kind == "deliver")
    r0, r1 = _pair(inst, lib)
    _assert_same(inst, lib, r0, r1)
    assert r1[1]["n_vars"] < r0[1]["n_vars"]
    rg = solve(inst, lib, aggregate=True, aggregate_mode="groups", **KW)
    _assert_same(inst, lib, r0, rg)


def _filtered_library(lib: ArcLibrary, drop) -> ArcLibrary:
    """Copy of ``lib`` without the arcs for which ``drop(arc)`` is true (renumbered)."""
    new = ArcLibrary(lib.inst, dict(lib.options), lib.gbar)
    for a in lib.arcs:
        if drop(a):
            continue
        new._add(Arc(len(new.arcs), a.k, a.kind, a.src, a.dst, a.l, a.u, a.d_km, a.g,
                     a.order, a.fac, a.theta))
    return new


def test_non_closed_library_uses_groups():
    inst = toy_instance()
    lib = _filtered_library(build_arcs(inst), lambda a: a.k == 2 and a.kind == "swap")
    net = aggregate_network(inst, lib)
    assert not net.closed and net.mode == "groups" and len(net.commodities) == 2
    with pytest.raises(AggregationError):
        AggregatedNetwork(inst, lib, mode="single")
    r0, r1 = _pair(inst, lib)
    _assert_same(inst, lib, r0, r1)
    assert r1[1]["aggregate"]["mode"] == "groups"


def test_bike_specific_arc_attributes_rejected():
    inst = toy_instance()
    lib0 = build_arcs(inst)
    lib = ArcLibrary(inst, dict(lib0.options), lib0.gbar)
    for a in lib0.arcs:
        d = a.d_km + (1.0 if (a.k == 2 and a.kind == "move") else 0.0)
        lib._add(Arc(len(lib.arcs), a.k, a.kind, a.src, a.dst, a.l, a.u, d, a.g, a.order, a.fac, a.theta))
    with pytest.raises(AggregationError):
        aggregate_network(inst, lib)


# ---------------------------------------------------------------------------
# mapping: aggregate_x / decompose, MIP start
# ---------------------------------------------------------------------------
def test_aggregate_and_decompose_round_trip():
    inst = toy_instance()
    lib = build_arcs(inst)
    doc = _doc_schedule(lib)
    net = aggregate_network(inst, lib)
    flows, missing = net.aggregate_x(doc.x)
    assert missing == [] and sum(flows.values()) == len(doc.x[1]) + len(doc.x[2])
    x = decompose_flow(net, flows)
    back = Schedule(x=x, u=doc.u, c=doc.c, h=doc.h, z=doc.z)
    assert check(inst, lib, back)["ok"]
    assert cost(inst, lib, back)["total"] == pytest.approx(12.5)
    assert sorted(arc_key(lib.arc(i)) for ids in x.values() for i in ids) == \
        sorted(arc_key(lib.arc(i)) for ids in doc.x.values() for i in ids)
    bad = dict(flows)
    bad[next(iter(bad))] += 1                       # break (5)
    with pytest.raises(AggregationError):
        net.decompose(bad)


def test_mip_start_in_aggregated_model():
    inst = toy_instance()
    lib = build_arcs(inst)
    sched, st = solve(inst, lib, aggregate=True, mip_start=_doc_schedule(lib), **KW)
    ms = st["mip_start"]
    assert ms["verified"] is True and ms["verified_obj"] == pytest.approx(12.5)
    assert ms["accepted"] is True and ms["agg_missing_arcs"] == 0
    assert st["obj"] == pytest.approx(12.5)
    mdl = build_model(inst, lib, colocated=True, aggregate=True, mip_start=_doc_schedule(lib), **KW)
    assert mdl.mip_start_info["verified"] is True


# ---------------------------------------------------------------------------
# shared-model entry point for bilevel.integrated_stochastic_ilp
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("aggregate", [False, True])
def test_build_submodel_on_shared_model(aggregate):
    inst = toy_instance()
    lib = build_arcs(inst)
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    m = gp.Model("shared", env=env)
    m.Params.Threads = 3
    m.Params.TimeLimit = 60
    y = {f.id: m.addVar(lb=f.y, ub=f.y, vtype=gp.GRB.BINARY) for f in inst.facilities}
    B = {f.id: m.addVar(lb=f.B, ub=f.B, vtype=gp.GRB.INTEGER) for f in inst.facilities}
    C = {f.id: m.addVar(lb=f.C, ub=f.C, vtype=gp.GRB.INTEGER) for f in inst.facilities}
    subs = [build_submodel(inst, lib, m, facility_vars=(y, B, C), prefix=f"s{s}_", aggregate=aggregate)
            for s in range(2)]
    m.setObjective(0.5 * subs[0].objective + 0.5 * subs[1].objective, gp.GRB.MINIMIZE)
    m.optimize()
    assert m.Status == gp.GRB.OPTIMAL and m.ObjVal == pytest.approx(12.5)
    for sub in subs:
        assert (sub.agg is not None) == aggregate
        sched = sub.extract_schedule()
        assert check(inst, lib, sched)["ok"] and cost(inst, lib, sched)["total"] == pytest.approx(12.5)
        assert sub.set_mip_start(sched, verify=False)["start_check_ok"]
    m.dispose()
    env.dispose()
