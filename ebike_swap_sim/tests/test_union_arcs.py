"""R8 fifteen-site study, lane L1 (2026-10-28): the union (bike-class) arc library
``arcs.UnionArcLibrary`` (``library_mode = 'union'``) reproduces ``build_arcs`` exactly --
same arcs with the same ids per bike, same lookups, same reachability as the per-bike DFS,
same aggregated network, same baseline schedules and the same ILP models / values -- on the
toy instances, the reduced-6 ``manhattan_dot`` family and the ``r5_manhattan`` family at 8
riders; a 48-rider toy-grid instance builds under the laptop limits with the numbers logged.
The default path (no ``library_mode``) is untouched (``test_core.py`` / ``test_aggregate.py``).
"""
from __future__ import annotations

import json
import os
import resource
import sys
import time
from collections import defaultdict

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import Bike, battery_swap_p7_instance, build_arcs, check, cost, toy_instance  # noqa: E402
from ebike_swap_sim import baseline as bl  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from ebike_swap_sim import costs as cm  # noqa: E402
from ebike_swap_sim.aggregate import AggregatedNetwork  # noqa: E402
from ebike_swap_sim.arcs import (ArcLibrary, UnionArcLibrary, _BitRank, _reachable, _template_specs, arc_key,  # noqa: E402
                                 build_union_arcs, library_mode, reach_sweep)
from ebike_swap_sim.generator import default_pruning, make_synthetic_instance  # noqa: E402
from ebike_swap_sim.or_instance import DEFAULT_OPTIONS, Instance, Order  # noqa: E402

DATA_RAW = os.path.join(ROOT, "..", "data", "raw")
HAS_NYC = os.path.exists(os.path.join(DATA_RAW, "dohmh_restaurants.csv"))
HAS_DOT = HAS_NYC and os.path.exists(S.DOT_CSV_DEFAULT)
LOG_DIR = os.path.join(ROOT, "outputs", "union_library")

FIELDS = ("id", "k", "kind", "src", "dst", "l", "u", "d_km", "g", "order", "fac", "theta")


def _row(a):
    return tuple(getattr(a, f) for f in FIELDS)


def _log(name: str, rec: dict) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, default=str)


def _toy_more_bikes():
    inst = toy_instance()
    inst.bikes = inst.bikes + [Bike(3, "A", 2), Bike(4, "B", 1), Bike(5, "A", 2)]
    inst.reindex()
    return inst


def _toy_zero_duration():
    """Toy with an order whose restaurant is its customer and no handling time: delivery
    arcs of zero duration (same ``t`` at tail and head), the case the time-ordered sweep
    iterates to a fixpoint within a level."""
    inst = toy_instance()
    o = inst.orders[0]
    inst.orders = inst.orders + [Order(id=99, o=o.o, d=o.o, r=0, a=0, b=3, hp=0, hd=0, P=o.P, w=o.w, v=o.v,
                                       platform=o.platform)]
    inst.reindex()
    return inst


OPTION_SETS = [
    {},
    {"reachable_pruning": True},
    {"dominance": False},
    {"energy_rounding": "concat", "reachable_pruning": True},
    {"dummy_terminal_cost": 50.0, "reachable_pruning": True},
    {"swap_q_max": 1, "tau_max": 1, "start_slack": 1, "reposition_targets": {"A", "B"}},
]


def assert_same_library(a: ArcLibrary, b: UnionArcLibrary, inst: Instance, full: bool = True) -> None:
    """``b`` (union) reproduces ``a`` (per bike): arcs by id, lookups, reachability."""
    assert isinstance(b, UnionArcLibrary) and not isinstance(a, UnionArcLibrary)
    assert len(a) == len(b) == len(b.arcs)
    assert a.infeasible_bikes == b.infeasible_bikes and a.has_dummy_terminal == b.has_dummy_terminal
    assert a.gbar == b.gbar
    assert {k: v for k, v in a.options.items()} == {k: v for k, v in b.options.items() if k != "library_mode"}
    assert b.options["library_mode"] == "union"
    for x, y in zip(a.arcs, b.arcs):
        assert _row(x) == _row(y)
    assert a.counts() == b.counts()
    assert [_row(x) for x in a.terminal_arcs()] == [_row(x) for x in b.terminal_arcs()]
    for kind in ("wait", "move", "deliver", "swap", "term"):
        assert [_row(x) for x in a.arcs_of_kind(kind)] == [_row(x) for x in b.arcs_of_kind(kind)]
    for o in inst.orders:
        assert [_row(x) for x in a.delivery_arcs(o.id)] == [_row(x) for x in b.delivery_arcs(o.id)]
        assert list(a._deliv.get(o.id, [])) == list(b._deliv[o.id])
    for j in inst.S:
        assert [_row(x) for x in a.swap_arcs(j)] == [_row(x) for x in b.swap_arcs(j)]
        if full:
            for t in range(inst.H):
                for q in range(inst.L):
                    assert [_row(x) for x in a.swap_arcs_at(j, t, q)] == [_row(x) for x in b.swap_arcs_at(j, t, q)]
    specs = _template_specs(inst, a.options, a.gbar)
    by_src = defaultdict(list)
    for i, sp in enumerate(specs):
        by_src[sp[1]].append(i)
    for bk in inst.bikes:
        k = bk.id
        assert a.counts(k) == b.counts(k) and a.ids_of(k) == b.ids_of(k) and a.source(k) == b.source(k)
        assert [_row(x) for x in a.arcs_of(k)] == [_row(x) for x in b.arcs_of(k)]
        assert a.states(k) == b.states(k)
        assert [_row(x) for x in a.terminal_arcs(k)] == [_row(x) for x in b.terminal_arcs(k)]
        for o in inst.orders:
            assert [_row(x) for x in a.delivery_arcs(o.id, k)] == [_row(x) for x in b.delivery_arcs(o.id, k)]
        for j in inst.S:
            assert [_row(x) for x in a.swap_arcs(j, k)] == [_row(x) for x in b.swap_arcs(j, k)]
        if full:
            for st in a.states(k):
                assert [_row(x) for x in a.out_arcs(k, st)] == [_row(x) for x in b.out_arcs(k, st)]
                assert [_row(x) for x in a.in_arcs(k, st)] == [_row(x) for x in b.in_arcs(k, st)]
            for x in a.arcs_of(k):
                for labels in ({"order": x.order, "fac": x.fac, "dst": x.dst}, {"order": x.order, "fac": x.fac}, {}):
                    f = b.find(k, x.kind, x.src, **labels)
                    g = a.find(k, x.kind, x.src, **labels)
                    assert f is not None and _row(f) == _row(g)
                assert _row(b.arc(x.id)) == _row(x)
        # reachability: the per-bike DFS of build_arcs equals the bitmask sweep
        assert _reachable(specs, by_src, (bk.v0, 0, bk.q0)) == b.reachable_states(k)
        assert b.has_real_terminal(k) == (k not in a.infeasible_bikes)
    # absent lookups
    assert b.find(inst.bikes[0].id, "deliver", ("nowhere", 0, 0)) is None
    assert b.find(inst.bikes[0].id, "deliver", b.source(inst.bikes[0].id), order="no-such-order") is None
    with pytest.raises(IndexError):
        b.arc(len(b))


def assert_same_aggregation(a: ArcLibrary, b: UnionArcLibrary, inst: Instance) -> None:
    for mode in ("auto", "single", "groups"):
        na = AggregatedNetwork(inst, a, mode=mode)
        nb = AggregatedNetwork(inst, b, mode=mode)
        assert na.summary() == nb.summary()
        assert len(na) == len(nb) and list(na.ub) == list(nb.ub) and na.term_ub == nb.term_ub
        assert na.classes == nb.classes
        assert [(c.id, c.bikes, c.supply, list(c.arc_ids)) for c in na.commodities] == \
               [(c.id, c.bikes, c.supply, list(c.arc_ids)) for c in nb.commodities]
        for x, y in zip(na.arcs, nb.arcs):
            assert _row(x) == _row(y)
        assert _row(nb.arcs[-1]) == _row(na.arcs[-1]) and [_row(x) for x in nb.arcs[:3]] == [_row(x) for x in na.arcs[:3]]
        for x in a.arcs:
            assert na.agg_id(x.k, x) == nb.agg_id(x.k, b.arc(x.id))
            assert nb.commodity_of(x.k) == na.commodity_of(x.k)
        sched, _ = bl.run_baseline(inst, b)
        fa, ma = na.aggregate_x(sched.x)
        fb, mb = nb.aggregate_x(sched.x)
        assert fa == fb and ma == mb
        if ma:                          # a stranded bike's open path uses arcs that cannot reach the sink
            continue
        back_a = na.decompose(fa)
        back_b = nb.decompose(fb)
        rows = lambda lib, sel: {k: [_row(lib.arc(i)) for i in ids] for k, ids in sel.items()}  # noqa: E731
        assert rows(b, back_b) == rows(a, back_a)
        paths = lambda lib, sel: sorted(sorted(arc_key(lib.arc(i)) for i in ids) for ids in sel.values())  # noqa: E731
        assert paths(b, back_b) == paths(b, sched.x)


def assert_same_baseline(a: ArcLibrary, b: UnionArcLibrary, inst: Instance, params=None) -> None:
    sa, fa = bl.run_baseline(inst, a, params)
    sb, fb = bl.run_baseline(inst, b, params)
    assert {k: sorted(v) for k, v in sa.x.items()} == {k: sorted(v) for k, v in sb.x.items()}
    assert sa.u == sb.u and sa.c == sb.c and sa.h == sb.h and sa.z == sb.z and sa.n == sb.n
    assert fa["n_swaps"] == fb["n_swaps"] and fa["n_unserved"] == fb["n_unserved"] and fa["terminal_violations"] == fb["terminal_violations"]
    ca, cb = cost(inst, a, sa), cost(inst, b, sb)
    assert ca == cb
    ra, rb = check(inst, a, sa), check(inst, b, sb)
    assert ra["ok"] == rb["ok"] and ra["families"] == rb["families"]
    # metric_pack (per-site statistics) reads the same values; the union library answers the
    # unserved-order index through ``delivery_need`` without materialising arcs
    from ebike_swap_sim.evaluate import metric_pack
    assert json.dumps(metric_pack(inst, b, sb), sort_keys=True, default=str) == \
        json.dumps(metric_pack(inst, a, sa), sort_keys=True, default=str)
    # library-independent form round trip on the union library (bilevel.portable_schedule)
    port = json.loads(json.dumps(BL.portable_schedule(sb, inst, b)))
    back = BL.materialise_schedule(port, inst, b)
    assert back is not None and {k: sorted(v) for k, v in back.x.items()} == {k: sorted(v) for k, v in sb.x.items()}
    # a schedule written against the union library prices and checks on the per-bike one (same ids)
    assert cost(inst, a, sb) == cb and check(inst, a, sb)["families"] == rb["families"]


# ---------------------------------------------------------------------------
# toy instances
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kw", OPTION_SETS, ids=[str(sorted(k)) for k in OPTION_SETS])
@pytest.mark.parametrize("maker", [toy_instance, battery_swap_p7_instance, _toy_more_bikes, _toy_zero_duration],
                         ids=["toy", "p7", "more_bikes", "zero_duration"])
def test_toy_views_reproduce_build_arcs(maker, kw):
    inst = maker()
    a = build_arcs(inst, **kw)
    b = build_arcs(inst, library_mode="union", **kw)
    assert_same_library(a, b, inst)
    assert_same_aggregation(a, b, inst)
    assert_same_baseline(a, b, inst)


def test_zero_duration_arcs_exist_and_sweep_reaches_through_them():
    inst = _toy_zero_duration()
    b = build_union_arcs(inst, reachable_pruning=True)
    zd = [x for x in b.arcs_of_kind("deliver") if x.l == x.u]
    assert zd, "the fixture must produce zero-duration delivery arcs"
    # a zero-duration arc whose tail is reachable makes its head reachable within the same level
    for x in zd[:20]:
        assert x.dst in b.reachable_states(x.k)


def test_toy_siting_layouts_with_pruning_and_radius():
    base = S.toy_base_instance(0, candidates=(("T1", 1), ("T2", 2), ("T3", 3), ("T4", 4)))
    for lay in ([("T1", "SC", 1, 1), ("T2", "S", 1, 0)], [("T3", "SC", 2, 1)], [("T1", "SC", 1, 1), ("T4", "C", 0, 1)]):
        inst = S.layout_instance(base, lay, S.TOY_SPEC)
        for radius in (None, 1, 2):
            pr = S.siting_pruning(inst, targets="open_sites", approach_radius_blocks=radius)
            a = build_arcs(inst, strict=False, **pr)
            b = build_arcs(inst, strict=False, library_mode="union", **pr)
            assert_same_library(a, b, inst, full=radius is None)
            assert_same_aggregation(a, b, inst)
            assert_same_baseline(a, b, inst)
    # the template tier (all candidates) and its sub-library also agree on the union library
    t_inst = S.all_candidates_instance(base, S.TOY_SPEC)
    pr = S.siting_pruning(t_inst)
    ta = build_arcs(t_inst, strict=False, **pr)
    tb = build_arcs(t_inst, strict=False, library_mode="union", **pr)
    assert_same_library(ta, tb, t_inst, full=False)
    inst = S.layout_instance(base, [("T1", "SC", 1, 1), ("T2", "S", 1, 0)], S.TOY_SPEC)
    sub_a = S.subset_library(ta, inst, strict=False)
    sub_b = S.subset_library(tb, inst, strict=False)
    assert [_row(x) for x in sub_a.arcs] == [_row(x) for x in sub_b.arcs]


def test_default_path_and_option_plumbing():
    inst = toy_instance()
    assert "library_mode" not in DEFAULT_OPTIONS and "library_mode" not in inst.options
    lib = build_arcs(inst)
    assert type(lib) is ArcLibrary and "library_mode" not in lib.options and len(lib) == 470
    assert library_mode({}) == "per_bike" and library_mode({"library_mode": None}) == "per_bike"
    with pytest.raises(ValueError):
        library_mode({"library_mode": "bogus"})
    with pytest.raises(ValueError):
        build_arcs(inst, library_mode="bogus")
    # the option on the instance switches every build (and survives the JSON round trip)
    inst.options["library_mode"] = "union"
    u = build_arcs(inst)
    assert isinstance(u, UnionArcLibrary) and u.options["library_mode"] == "union"
    inst2 = Instance.from_json(inst.to_json())
    assert inst2.options["library_mode"] == "union" and isinstance(build_arcs(inst2), UnionArcLibrary)
    # a rebuild from lib.options (ilp's co-located rebuild) stays in union mode
    opts = dict(u.options)
    opts["colocated"] = True
    assert isinstance(build_arcs(inst, **opts), UnionArcLibrary)
    # explicit per-bike override wins over the instance option
    assert type(build_arcs(inst, library_mode="per_bike")) is ArcLibrary
    # strictness as in build_arcs
    bad = toy_instance()
    bad.q_res = 3                           # no terminal arc can exist (q <= L = 2), as in test_core
    from ebike_swap_sim.arcs import InfeasibleInstanceError
    with pytest.raises(InfeasibleInstanceError):
        build_union_arcs(bad)
    assert build_union_arcs(bad, strict=False).infeasible_bikes == [1, 2]
    assert build_union_arcs(bad, dummy_terminal_cost=50.0).infeasible_bikes == [1, 2]


def test_lazy_sequences_and_price_check():
    inst = _toy_more_bikes()
    b = build_union_arcs(inst, reachable_pruning=True)
    arcs = b.arcs
    assert len(arcs) == len(b) and [x.id for x in arcs] == list(range(len(b)))
    assert _row(arcs[-1]) == _row(b.arc(len(b) - 1)) and len(arcs[2:5]) == 3
    with pytest.raises(IndexError):
        arcs[len(b)]
    ids = b._deliv[inst.orders[0].id]
    assert list(ids) == list(ids[:]) and ids[-1] == ids[len(ids) - 1]
    assert cm.check_lib_prices(inst, b)["ok"]
    rep = cm.reprice_orders(inst, w=3.0)
    with pytest.raises(cm.PricingMismatchError):
        cm.check_lib_prices(rep, b)
    s = b.summary()
    assert s["library_mode"] == "union" and s["n_arcs"] == len(b) and s["n_classes"] == 2
    assert s["memory_mb"] >= 0 and {"gbar", "specs", "reach", "total"} <= set(s["timings_s"])
    assert b.memory_bytes() > 0
    assert b.class_of_bike[1] == b.class_of_bike[3] == b.class_of_bike[5] != b.class_of_bike[4]
    assert b.class_bikes[b.class_of_bike[1]] == [1, 2, 3, 5] and b.class_bikes[b.class_of_bike[4]] == [4]
    k, spec = b.spec_of_id(b.ids_of(3)[0])
    assert k == 3 and b.id_of(3, spec) == b.ids_of(3)[0]
    with pytest.raises(KeyError):
        unreachable = int(np.flatnonzero(~b.reachable_mask(4))[0])
        b.id_of(4, unreachable)


def test_bitrank_and_sweep_primitives():
    rng = np.random.default_rng(0)
    for n in (0, 1, 63, 64, 65, 1000, 4097):
        mask = rng.random(n) < 0.4
        rs = _BitRank(mask, n)
        idx = np.flatnonzero(mask)
        assert rs.count == len(idx) and list(rs.indices()) == list(idx)
        assert all(rs.test(i) == bool(mask[i]) for i in range(n))
        assert [rs.rank(i) for i in range(n)] == list(np.cumsum(mask) - mask) if n else True
        assert [rs.select(r) for r in range(rs.count)] == list(idx)
        lo, hi = n // 3, 2 * n // 3
        assert list(rs.indices(lo, hi)) == [i for i in idx if lo <= i < hi]
        assert list(rs.mask(lo, hi)) == list(mask[lo:hi])
        ident = _BitRank(None, n)
        assert ident.count == n and ident.rank(n - 1 if n else 0) == (n - 1 if n else 0)
        # rank(n) is the total and test(n) is False, also when n is a multiple of 64 (R8 fix: IndexError before)
        assert rs.rank(n) == rs.count and not rs.test(n)
    for n in (64, 128):
        full = _BitRank(np.ones(n, dtype=bool), n)
        assert full.rank(n) == n and full.rank(n - 1) == n - 1 and not full.test(n)
    # the sweep on a small DAG with a zero-duration arc, more than 64 classes (two words)
    state_t = np.array([0, 0, 1, 1, 2], dtype=np.int32)      # states 0,1 at level 0; 2,3 at 1; 4 at 2
    src = np.array([0, 1, 2, 3, 0], dtype=np.int32)
    dst = np.array([1, 2, 3, 4, 2], dtype=np.int32)          # 0->1 is zero-duration
    sources = [0] * 70 + [1, 3]
    R = reach_sweep(src, dst, state_t, sources, 3)
    assert R.shape == (5, 2)
    reach = lambda c: {s for s in range(5) if (int(R[s, c >> 6]) >> (c & 63)) & 1}  # noqa: E731
    assert reach(0) == reach(69) == {0, 1, 2, 3, 4} and reach(70) == {1, 2, 3, 4} and reach(71) == {3, 4}


# ---------------------------------------------------------------------------
# ILP values (Gurobi)
# ---------------------------------------------------------------------------
gp = pytest.importorskip("gurobipy")
from ebike_swap_sim.ilp import build_model, solve  # noqa: E402

KW = dict(threads=1, time_limit=60.0, params={"Seed": 0, "MIPGap": 0.0})


@pytest.mark.parametrize("kw", [{}, {"reachable_pruning": True}, {"dummy_terminal_cost": 50.0}])
@pytest.mark.parametrize("maker", [toy_instance, _toy_more_bikes], ids=["toy", "more_bikes"])
def test_ilp_values_identical_on_toy(maker, kw):
    inst = maker()
    a = build_arcs(inst, **kw)
    b = build_arcs(inst, library_mode="union", **kw)
    for agg in (True, False):
        (s0, st0) = solve(inst, a, aggregate=agg, **KW)
        (s1, st1) = solve(inst, b, aggregate=agg, **KW)
        assert st0["status"] == st1["status"] == "OPTIMAL"
        assert st1["obj"] == pytest.approx(st0["obj"], abs=1e-6)
        assert check(inst, b, s1)["ok"] and cost(inst, b, s1)["total"] == pytest.approx(st1["obj"], abs=1e-6)
        assert check(inst, a, s1)["ok"]                       # same ids: certifies on the per-bike library too
        assert {k: sorted(v) for k, v in s0.x.items()} == {k: sorted(v) for k, v in s1.x.items()}
        if maker is toy_instance and not kw:
            assert st1["obj"] == pytest.approx(12.5)
    # identical models: Gurobi's fingerprint of the aggregated model is the same
    fa = int(build_model(inst, a, aggregate=True, **KW).model.Fingerprint)
    fb = int(build_model(inst, b, aggregate=True, **KW).model.Fingerprint)
    assert fa == fb
    # MIP start from a baseline schedule on the union library (aggregate_x path)
    sched, _ = bl.run_baseline(inst, b)
    s2, st2 = solve(inst, b, aggregate=True, mip_start=sched, **KW)
    assert st2["status"] == "OPTIMAL" and st2["obj"] == pytest.approx(st1["obj"], abs=1e-6)


# ---------------------------------------------------------------------------
# reduced siting families at 8 riders (NYC data) and the 48-rider toy grid
# ---------------------------------------------------------------------------
def _peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20


def _family_check(name: str, inst: Instance, pruning: dict, ilp_seconds: float = 0.0) -> dict:
    rec = {"family": name, "instance": inst.summary(), "pruning_keys": sorted(pruning)}
    t0 = time.perf_counter()
    b = build_arcs(inst, strict=False, library_mode="union", **pruning)
    rec["union_build_s"] = round(time.perf_counter() - t0, 3)
    t0 = time.perf_counter()
    a = build_arcs(inst, strict=False, **pruning)
    rec["perbike_build_s"] = round(time.perf_counter() - t0, 3)
    rec["n_arcs"] = len(b)
    rec["n_specs"] = b.n_specs
    rec["n_classes"] = b.n_classes
    rec["union_memory_mb"] = round(b.memory_bytes() / 2 ** 20, 1)
    rec["union_timings_s"] = b.summary()["timings_s"]
    assert_same_library(a, b, inst, full=False)
    # spot checks of find / out_arcs on every state of the first bike's baseline path
    assert_same_baseline(a, b, inst)
    t0 = time.perf_counter()
    sched, _ = bl.run_baseline(inst, b)
    rec["union_baseline_s"] = round(time.perf_counter() - t0, 3)
    t0 = time.perf_counter()
    check(inst, b, sched)
    rec["union_check_s"] = round(time.perf_counter() - t0, 3)
    t0 = time.perf_counter()
    nb = AggregatedNetwork(inst, b)
    rec["agg_union_s"] = round(time.perf_counter() - t0, 3)
    na = AggregatedNetwork(inst, a)
    assert na.summary() == nb.summary() and list(na.ub) == list(nb.ub) and na.term_ub == nb.term_ub
    for x, y in zip(na.arcs, nb.arcs):
        assert _row(x) == _row(y)
    rec["agg_summary"] = nb.summary()
    ma = build_model(inst, a, aggregate=True, threads=1, time_limit=max(1.0, ilp_seconds), params={"Seed": 0})
    mb = build_model(inst, b, aggregate=True, threads=1, time_limit=max(1.0, ilp_seconds), params={"Seed": 0})
    rec["ilp_fingerprint"] = [int(ma.model.Fingerprint), int(mb.model.Fingerprint)]
    assert rec["ilp_fingerprint"][0] == rec["ilp_fingerprint"][1]
    if ilp_seconds > 0:
        (_sa, sta) = ma.solve(mip_start=sched, verify_start=False)
        (_sb, stb) = mb.solve(mip_start=sched, verify_start=False)
        rec["ilp"] = {"perbike": [sta["status"], sta["obj"], sta.get("bound")], "union": [stb["status"], stb["obj"], stb.get("bound")]}
        assert sta["status"] == stb["status"] and sta["obj"] == pytest.approx(stb["obj"], rel=1e-9)
    rec["peak_rss_mb"] = round(_peak_mb(), 1)
    _log(name, rec)
    return rec


@pytest.mark.skipif(not HAS_DOT, reason="DOT candidate CSV / DOHMH data not present")
def test_reduced6_manhattan_dot_8_riders_identical():
    """Reduced-6 ``manhattan_dot`` scenario (seed 0, 8 riders / 40 orders, R6 prices), two
    SC:B3:C2 sites, open-sites tier with the 14-block approach radius: arcs, baseline,
    aggregation and the aggregated ILP model are identical (about 1 min)."""
    cands = S.dot_candidates(S.DOT_CSV_DEFAULT)[0][:6]
    depots = S.family_depots(S.MANHATTAN_DOT_FAMILY, cands)
    base = S.make_base_instance(0, cands, family=S.MANHATTAN_DOT_FAMILY, depots=depots, n_bikes=8)
    pr = cm.R6_PRICING
    base = cm.reprice_orders(base, P=pr["P"], w=pr["w"], v=pr["v"], source="tests/test_union_arcs.py")
    spec = S.spec_from_instance(base, **S.family_spec_overrides(S.MANHATTAN_DOT_FAMILY))
    inst = S.layout_instance(base, [(cands[0].id, "SC", 3, 2), (cands[3].id, "SC", 3, 2)], spec)
    pruning = S.siting_pruning(inst, targets="open_sites", approach_radius_blocks=14)
    rec = _family_check("manhattan_dot_N6_b8", inst, pruning)
    assert rec["n_classes"] <= 8 and rec["n_arcs"] > 0


@pytest.mark.skipif(not HAS_NYC, reason="DOHMH data not present")
def test_r5_manhattan_8_riders_identical():
    """``r5_manhattan`` scenario (seed 0, 8 riders / 40 orders, R6 prices), one-site layout
    M08:SC:2:1 on the open-sites tier (no radius, as the family is run): identical (about 1 min)."""
    cands = S.lattice_candidates()
    base = S.make_base_instance(0, cands, family=S.R5_MANHATTAN_FAMILY, n_bikes=8)
    pr = cm.R6_PRICING
    base = cm.reprice_orders(base, P=pr["P"], w=pr["w"], v=pr["v"], source="tests/test_union_arcs.py")
    spec = S.spec_from_instance(base)
    inst = S.layout_instance(base, [("M08", "SC", 2, 1)], spec)
    pruning = S.siting_pruning(inst, targets="open_sites")
    rec = _family_check("r5_manhattan_b8", inst, pruning)
    assert rec["n_arcs"] > 0


def test_48_rider_toy_grid_builds_under_laptop_limits():
    """48 riders / 240 orders on the synthetic 4 h grid family (``usd4h`` knobs): the union
    library builds in seconds, its memory does not depend on the fleet (same specs at 8 and
    48 riders), the per-bike views are exact on an 8-rider slice, and the r2 baseline cell
    (build + simulate + check) stays far below the 45 s / 4 GB gates.  Numbers are logged to
    ``outputs/union_library/toy_grid_b48.json``."""
    inst = make_synthetic_instance(seed=0, n_bikes=48, window_h=4.0, window_start_hour=17.0,
                                   orders_per_bike_hour=1.25, L=12, n_restaurants=8, cost_variant="usd_sunk")
    assert len(inst.bikes) == 48 and len(inst.orders) == 240
    pruning = default_pruning(inst, reachable=True)
    rss0 = _peak_mb()
    t0 = time.perf_counter()
    lib = build_arcs(inst, strict=False, library_mode="union", **pruning)
    build_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    sched, flags = bl.run_baseline(inst, lib)
    base_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    rep = check(inst, lib, sched)
    check_s = time.perf_counter() - t0
    peak = _peak_mb()
    rec = {"instance": inst.summary(), "n_specs": lib.n_specs, "n_arcs": len(lib), "n_classes": lib.n_classes,
           "union_memory_mb": round(lib.memory_bytes() / 2 ** 20, 1), "build_s": round(build_s, 3),
           "timings_s": lib.summary()["timings_s"], "baseline_s": round(base_s, 3), "check_s": round(check_s, 3),
           "cell_s": round(build_s + base_s + check_s, 3), "peak_rss_mb": round(peak, 1), "rss_before_mb": round(rss0, 1),
           "check_ok": rep["ok"], "check_families": rep["families"], "n_swaps": flags["n_swaps"],
           "n_unserved": flags["n_unserved"], "cost": cost(inst, lib, sched)["total"]}
    # fleet independence: the 8-rider slice has the same specs and the same union memory up to the class vectors
    inst8 = Instance.from_dict(inst.to_dict())
    inst8.bikes = inst8.bikes[:8]
    inst8.reindex()
    lib8 = build_arcs(inst8, strict=False, library_mode="union", **pruning)
    assert lib8.n_template_specs == lib.n_template_specs          # the template does not depend on the fleet
    assert lib8.n_specs <= lib.n_specs <= lib.n_template_specs     # stored = reachable by some class
    assert lib8.n_classes <= lib.n_classes and lib.memory_bytes() < 64 * 2 ** 20
    per8 = build_arcs(inst8, strict=False, **pruning)
    assert_same_library(per8, lib8, inst8, full=False)
    assert_same_baseline(per8, lib8, inst8)
    rec["n_arcs_8"] = len(lib8)
    rec["perbike_arcs_8"] = len(per8)
    _log("toy_grid_b48", rec)
    assert rec["cell_s"] < 45.0 and (peak - rss0) < 4096.0
    assert rep["ok"] or rep["families"]      # the report is well formed
