"""Round 6 (``notes/penalty_calibration.md`` sections 1, 6, 7): order repricing as data.

``costs.reprice_orders`` / ``check_lib_prices`` / the ``usd_r6`` cost variant and every
consumer of the order prices ``P_i, w_i, v_i`` of E2 (30)-(31): ``evaluate.cost``, the ILP
objective (per-bike and aggregated), the delivery-arc ``theta`` stored on the arc library,
the rolling-horizon shifted penalty, the M3 stock-out value of the rule policy and the
bi-level cache keys.  No E2 equation changes; the toy invariants under the default prices
are re-asserted."""
from __future__ import annotations

import dataclasses
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import Schedule, build_arcs, check, cost, toy_instance  # noqa: E402
from ebike_swap_sim import costs as cm  # noqa: E402
from experiments import common as C  # noqa: E402

gp = pytest.importorskip("gurobipy")
from ebike_swap_sim import ilp  # noqa: E402

KW = {"threads": 3, "time_limit": 60.0}


def _doc_schedule(lib) -> Schedule:
    """E2_Example p.14 optimal schedule of the toy (as tests/test_ilp.py)."""
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


def _toy_late():
    """The toy with every promise at release (b_i = r_i): every delivery is late, so the
    lateness price v enters the cost of the documented schedule."""
    inst = toy_instance()
    inst.orders = [dataclasses.replace(o, b=o.r) for o in inst.orders]
    inst.reindex()
    return inst


def _small_usd(**kw):
    return C.make_instance("usd4h", seed=0, n_bikes=2, window_h=1.0, **kw)


# ---------------------------------------------------------------------------
# the cost variant and the helper
# ---------------------------------------------------------------------------
def test_usd_r6_variant_is_usd_sunk_with_new_order_prices():
    r6 = cm.load_cost_calibration(variant="usd_r6")
    sunk = cm.load_cost_calibration(variant="usd_sunk")
    assert r6["demand_spec"] == {"P": 60.0, "w": 18.0, "v": 15.0}
    assert {k: r6["demand_spec"][k] for k in "Pwv"} == {k: cm.R6_PRICING[k] for k in "Pwv"}
    assert {k: sunk["demand_spec"][k] for k in "Pwv"} == {k: cm.LEGACY_PRICING[k] for k in "Pwv"}
    assert r6["costs"] == sunk["costs"] and r6["services_spec"] == sunk["services_spec"]
    assert "penalty_calibration" in cm.cost_variants()["usd_r6"]


def test_reprice_equals_generating_with_usd_r6_and_updates_meta():
    a = _small_usd()
    b = _small_usd(cost_variant="usd_r6")
    r = cm.reprice_orders(a, P=60.0, v=15.0, source="test")
    da, db = r.to_dict(), b.to_dict()
    da.pop("meta"), db.pop("meta")
    assert da == db                                   # same orders, prices, everything but meta
    assert C.demand_md5(r) == C.demand_md5(a)          # the demand side is untouched
    assert {(o.P, o.w, o.v) for o in a.orders} == {(30.0, 18.0, 36.0)}   # the input is not mutated
    m = r.meta
    assert (m["costs"]["P"], m["costs"]["w"], m["costs"]["v"]) == (60.0, 18.0, 15.0)
    assert (m["params"]["demand_spec"]["P"], m["params"]["demand_spec"]["v"]) == (60.0, 15.0)
    assert m["cost_variant"] == "usd_r6" and m["cost_variant_generated"] == "usd_sunk"
    assert m["pricing"]["label"] == "P60_w18_v15" and m["pricing"]["changed"] == ["P", "v"]
    assert m["pricing"]["previous"] == {"P": 30.0, "w": 18.0, "v": 36.0}
    assert m["pricing"]["library_rebuild_required"] is True
    other = cm.reprice_orders(r, P=40.0)
    assert other.meta["cost_variant"] == "usd_sunk@P40_w18_v15"
    assert other.meta["pricing"]["previous"] == {"P": 30.0, "w": 18.0, "v": 36.0}
    back = cm.reprice_orders(r, P=30.0, v=36.0)
    assert back.meta["cost_variant"] == "usd_sunk"
    with pytest.raises(ValueError):
        cm.reprice_orders(a, P=-1.0)


def test_toy_invariants_unchanged_under_default_prices():
    """Repricing to the prices the toy already has is the identity: 12.5 per-bike and
    aggregated, and the library of the original instance stays valid."""
    inst = toy_instance()
    same = cm.reprice_orders(inst, P=100.0, w=12.0, v=24.0)
    assert same.orders == inst.orders and same.meta["pricing"]["library_rebuild_required"] is False
    lib = build_arcs(inst)
    assert cm.check_lib_prices(same, lib)["ok"]
    lib2 = build_arcs(same)
    for agg in (False, True):
        _s, st = ilp.solve(same, lib2, aggregate=agg, **KW)
        assert st["status"] == "OPTIMAL" and st["obj"] == pytest.approx(12.5, abs=1e-6)
    assert cost(same, lib2, _doc_schedule(lib2))["total"] == pytest.approx(12.5)
    assert cm.pricing_cache_component(inst) is None


def test_reprice_P_only_keeps_theta():
    inst = toy_instance()
    lib = build_arcs(inst)
    rp = cm.reprice_orders(inst, P=60.0)
    assert rp.meta["pricing"]["library_rebuild_required"] is False
    assert cm.check_lib_prices(rp, lib)["ok"]                  # the old library is still priced right
    lib2 = build_arcs(rp)
    assert [(a.id, a.kind, a.src, a.dst, a.theta) for a in lib2.arcs] == \
        [(a.id, a.kind, a.src, a.dst, a.theta) for a in lib.arcs]
    sched = _doc_schedule(lib2)
    sched.u = {1: 0, 2: 1, 3: 0}                               # one order dropped: P enters through u
    c_old, c_new = cost(inst, lib, sched), cost(rp, lib2, sched)
    assert c_new["C_orders_parts"]["unserved"] - c_old["C_orders_parts"]["unserved"] == pytest.approx(60.0 - 100.0)
    for part in ("response", "lateness"):
        assert c_new["C_orders_parts"][part] == pytest.approx(c_old["C_orders_parts"][part])


def test_reprice_v_requires_rebuilt_library_and_shifts_cost_by_formula():
    inst = _toy_late()
    lib = build_arcs(inst)
    sched = _doc_schedule(lib)
    assert check(inst, lib, sched)["ok"]
    rp = cm.reprice_orders(inst, v=15.0, w=18.0)
    assert rp.meta["pricing"]["library_rebuild_required"] is True
    # the old library is stale: the check and the ILP builder refuse it
    with pytest.raises(cm.PricingMismatchError):
        cm.check_lib_prices(rp, lib)
    stale = build_arcs(inst)
    stale.inst = rp                                             # a re-bound (copied) library
    with pytest.raises(cm.PricingMismatchError):
        ilp.build_model(rp, stale)
    # the rebuilt library has the new theta on every delivery arc, the same arcs otherwise
    lib2 = build_arcs(rp)
    assert cm.check_lib_prices(rp, lib2, per_order=10 ** 6)["ok"]
    assert [(a.id, a.kind, a.src, a.dst) for a in lib2.arcs] == [(a.id, a.kind, a.src, a.dst) for a in lib.arcs]
    for a in lib2.arcs_of_kind("deliver"):
        assert a.theta == pytest.approx(rp.theta(a.order, a.u))
    # evaluate.cost of the fixed schedule changes by sum_i [(w'-w) (u-r) + (v'-v) (u-b)^+] Delta
    D = inst.disc.Delta_h
    expect_resp = expect_late = 0.0
    for a in sched.chosen_arcs(lib):
        if a.kind == "deliver":
            o = inst.order(a.order)
            expect_resp += (18.0 - o.w) * D * (a.u - o.r)
            expect_late += (15.0 - o.v) * D * max(a.u - o.b, 0)
    assert expect_late != 0.0
    c_old, c_new = cost(inst, lib, sched), cost(rp, lib2, sched)
    assert c_new["C_orders_parts"]["lateness"] - c_old["C_orders_parts"]["lateness"] == pytest.approx(expect_late)
    assert c_new["C_orders_parts"]["response"] - c_old["C_orders_parts"]["response"] == pytest.approx(expect_resp)
    assert c_new["total"] - c_old["total"] == pytest.approx(expect_late + expect_resp)
    # v only: the lateness part moves, the response part does not
    rv = cm.reprice_orders(inst, v=15.0)
    c_v = cost(rv, build_arcs(rv), sched)
    assert c_v["C_orders_parts"]["response"] == pytest.approx(c_old["C_orders_parts"]["response"])
    assert c_v["total"] - c_old["total"] == pytest.approx(expect_late)


@pytest.mark.parametrize("make", [toy_instance, _toy_late])
def test_ilp_objective_equals_evaluate_cost_after_repricing(make):
    inst = cm.reprice_orders(make(), P=cm.R6_PRICING["P"], w=cm.R6_PRICING["w"], v=cm.R6_PRICING["v"])
    lib = build_arcs(inst)
    objs = []
    for agg in (False, True):
        sched, st = ilp.solve(inst, lib, aggregate=agg, **KW)
        assert st["status"] == "OPTIMAL"
        assert check(inst, lib, sched)["ok"]
        assert cost(inst, lib, sched)["total"] == pytest.approx(st["obj"], abs=1e-6)
        objs.append(st["obj"])
    assert objs[0] == pytest.approx(objs[1], abs=1e-6)


def test_small_synthetic_ilp_matches_cost_under_r6_prices():
    inst = cm.reprice_orders(_small_usd(), P=60.0, v=15.0)
    lib, _ = C.build_library(inst, C.pruning_for(inst, reachable=True))
    assert cm.check_lib_prices(inst, lib)["ok"]
    rec = C.run_ilp_case(inst, lib, time_limit=60.0, threads=3, aggregate=True, params={"Seed": 0})
    assert rec["schedule"] is not None
    assert rec["cost"]["total"] == pytest.approx(rec["obj"], rel=1e-6)


# ---------------------------------------------------------------------------
# other consumers of the prices
# ---------------------------------------------------------------------------
def test_rolling_shifted_penalty_uses_the_repriced_orders():
    from ebike_swap_sim.rolling import _shift_order
    inst = cm.reprice_orders(_small_usd(), P=60.0, v=15.0)
    D = inst.disc.Delta_h
    o = inst.orders[0]
    t0 = o.r + 6
    so = _shift_order(o, t0, D)
    assert so.P == pytest.approx(60.0 - 18.0 * D * 6) and so.v == 15.0 and so.w == 18.0


def test_rule_stockout_value_reads_the_repriced_P():
    """M3 (COST_AWARE transfers) values an avoided stock-out at mean P_i: it must see the new P."""
    from ebike_swap_sim import baseline as bl
    for P in (30.0, 60.0):
        inst = cm.reprice_orders(_small_usd(), P=P)
        lib, _ = C.build_library(inst, C.pruning_for(inst, reachable=True))
        run = bl._BaselineRun(inst, lib, bl.BaselineParams.coerce(bl.baseline_variant_params("r5_transfer")))
        assert run.stockout_value() == pytest.approx(P)


def test_bilevel_cache_key_differs_across_prices():
    from ebike_swap_sim import bilevel as BL
    from ebike_swap_sim import sites_nyc as S
    base = [S.toy_base_instance(0), S.toy_base_instance(1)]
    lay = BL.Layout.of([("T1", "SC", 1, 1)])
    ev0 = BL.LowerLevelEvaluator(base, S.TOY_SPEC, time_limit=30.0, threads=1)
    same = [cm.reprice_orders(i, P=float(i.orders[0].P), w=float(i.orders[0].w), v=float(i.orders[0].v))
            for i in base]
    r6 = [cm.reprice_orders(i, P=60.0, w=18.0, v=15.0) for i in base]
    r6b = [cm.reprice_orders(i, P=80.0, w=18.0, v=15.0) for i in base]
    keys = {name: BL.LowerLevelEvaluator(sc, S.TOY_SPEC, time_limit=30.0, threads=1).cache_key(lay, 0, pol)
            for name, sc in (("r6", r6), ("r6b", r6b), ("same", same)) for pol in ("ilp",)}
    k0 = ev0.cache_key(lay, 0, "ilp")
    assert keys["r6"] != k0 and keys["r6b"] != k0 and keys["r6"] != keys["r6b"]
    # an instance repriced to its own prices is marked as repriced: a separate key, never a stale hit
    assert cm.pricing_cache_component(same[0]) is not None
    # instances priced as generated keep the round-5 key
    assert BL.LowerLevelEvaluator(base, S.TOY_SPEC, time_limit=30.0, threads=1).cache_key(lay, 0, "ilp") == k0
