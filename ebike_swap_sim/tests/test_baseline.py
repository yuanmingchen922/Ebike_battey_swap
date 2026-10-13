"""Baseline policy tests: zero hard-constraint violations on the E2 toy (both
transfer rules), the Battery_Swap p.7 queue table reproduced by the policy, a
hand-made 1-bike / 2-order instance where the threshold rule is needed, path
contiguity in the arc library, parity under pruning, pruned-arc fallbacks,
zone dispatch and charge-rule ordering; round-2 rules (DECISIONS R2.3):
stock-aware site choice, DEMAND_AWARE charging (forecast / reserve / hub rule)
and the named variants ``default`` / ``round1`` / ``legacy``."""
from __future__ import annotations

import json

import pytest

from ebike_swap_sim import (
    SINK,
    Bike,
    Discretisation,
    Facility,
    Instance,
    Order,
    Route,
    battery_swap_p7_instance,
    build_arcs,
    check,
    cost,
    metrics,
    reconstruct_inventory,
    toy_instance,
)
from ebike_swap_sim.baseline import (
    BASELINE_VARIANTS,
    BaselineParams,
    baseline_variant_params,
    run_baseline,
)

#: families the baseline must satisfy by construction (DECISIONS.md: (9), (17), (18) are reported)
HARD = ["arcs", "(5)", "(6)", "(10)", "(12)", "(13)", "(14)", "(15)", "(16)", "(20)", "(21)", "(22)", "domain"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def assert_hard_ok(rep: dict) -> None:
    bad = {f: rep["families"][f] for f in HARD if f in rep["families"]}
    assert not bad, bad


def assert_contiguous_paths(inst, lib, sched) -> None:
    """Each bike's chosen arcs form one source -> sink path inside its own library A_k."""
    for b in inst.bikes:
        k = b.id
        own = set(lib.ids_of(k))
        path = sched.path(k, lib)
        assert path, f"bike {k}: empty path"
        assert all(a.id in own for a in path)
        assert len({a.id for a in path}) == len(path)
        cur = lib.source(k)
        for a in path:
            assert a.src == cur, (k, a, cur)
            cur = a.dst
        assert cur == SINK
        assert path[-1].kind == "term" and all(a.kind != "term" for a in path[:-1])
        # consecutive non-terminal arcs tile the horizon [0, H)
        assert [a.l for a in path[:-1]] == [0] + [a.u for a in path[:-2]]
        assert path[-2].u == inst.H


def path_sig(sched, lib):
    return {k: [(a.kind, a.src, a.dst, a.order, a.fac) for a in sched.path(k, lib)] for k in sched.x}


# ---------------------------------------------------------------------------
# toy instance
# ---------------------------------------------------------------------------
def test_toy_baseline_no_transfers():
    inst = toy_instance()
    lib = build_arcs(inst)
    sched, flags = run_baseline(inst, lib)                 # defaults: transfer_rule NONE
    rep = check(inst, lib, sched)
    assert_hard_ok(rep)
    assert rep["ok"] and rep["n_violations"] == 0 and rep["n_source"] == "given"
    assert rep["identity_24_ok"]
    assert_contiguous_paths(inst, lib, sched)
    cst = cost(inst, lib, sched)
    # order 3 cannot be served without a transfer (A never holds a full spare);
    # both bikes return to A under the threshold rule: 2 + 2 km travel
    assert sched.u == {1: 0, 2: 0, 3: 1}
    assert cst["C_orders_parts"]["unserved"] == 100.0
    assert cst["C_orders_parts"]["response"] == pytest.approx(4.0)
    assert cst["C_travel"] == pytest.approx(4.0)
    assert cst["C_reb"] == 0 and cst["C_elec"] == 0
    assert cst["total"] == pytest.approx(108.0)
    assert 100 < cst["total"] < 110
    # schedule bookkeeping
    assert sched.h == {1: 0, 2: 0} and sched.z == {} and sched.c == {}
    assert sched.y == {"A": 1, "C": 1} and sched.B == {"A": 0, "C": 1} and sched.C == {"A": 0, "C": 1}
    # online (13) stepping equals the evaluate recursion
    n_rec = reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z)
    assert sched.n == n_rec
    assert flags["inventory_consistent"]
    # flags
    assert flags["q_thr"] == 1
    assert flags["queued_at_H"] == [1, 2]
    assert flags["wait_slots_in_queue"] == {"A": 10}
    assert flags["stranded"] == [] and flags["terminal_violations"] == [] and flags["storage_violations"] == []
    assert flags["end_shortfalls"] == {"local": {}, "global": 0.0}
    assert flags["pruned_arc_fallbacks"]["count"] == {"move": 0, "deliver": 0, "swap": 0}
    assert flags["n_swaps"] == 0 and flags["n_unserved"] == 1
    # round-2 defaults (R2.3) leave the toy at 108: A is the only swap site (the two
    # bikes fall back to it at B and queue at it, 4 fallbacks, no reroute) and the
    # charge site C is a hub, charged by the HIGH_FIRST hub rule
    assert flags["stock_aware_reroutes"] == 0 and flags["stock_aware_fallbacks"] == 4
    assert flags["charge_rule_effective"] == {"C": "HIGH_FIRST"}
    assert sched.meta["params"]["charge_rule"] == "DEMAND_AWARE" and sched.meta["params"]["stock_aware_site"] is True
    # the Schedule is JSON-safe (MIP-start / result files)
    s2 = type(sched).from_dict(json.loads(json.dumps(sched.to_dict())))
    assert cost(inst, lib, s2)["total"] == pytest.approx(108.0)
    m = metrics(inst, lib, sched)
    assert m["served_share"] == pytest.approx(2 / 3) and m["bike_km"] == pytest.approx(4.0)


def test_toy_baseline_reorder_point_serves_all():
    inst = toy_instance()
    lib = build_arcs(inst)
    params = BaselineParams(transfer_rule="REORDER_POINT", reorder_point=1)
    sched, flags = run_baseline(inst, lib, params)
    rep = check(inst, lib, sched)
    assert_hard_ok(rep)
    assert rep["ok"], rep
    assert_contiguous_paths(inst, lib, sched)
    # the spare ships C -> A at t = 1 (arrives 3), bike 1 swaps at 3 and serves order 3,
    # the returned empty ships A -> C at t = 4 and is charged in slots 6, 7 (p.14-15)
    assert sched.u == {1: 0, 2: 0, 3: 0}
    assert sched.h == {1: 1, 2: 1}
    assert sched.z == {(1, 2): 1, (2, 0): 1}
    assert sched.c == {("C", 0, 6): 1, ("C", 1, 7): 1}
    assert lib.arc(sched.x[1][2]).kind == "swap" and lib.arc(sched.x[1][2]).src == ("A", 3, 0)
    cst = cost(inst, lib, sched)
    assert cst["C_orders_parts"]["response"] == pytest.approx(6.0)
    assert cst["C_elec"] == pytest.approx(0.1) and cst["C_reb"] == pytest.approx(2.4)
    # optimum 12.5 plus the two 1 km returns forced by the threshold rule (bikes at q = 1)
    assert cst["C_travel"] == pytest.approx(6.0)
    assert cst["total"] == pytest.approx(14.5)
    assert flags["end_shortfalls"]["global"] == 0 and flags["n_swaps"] == 1
    assert sched.n[("C", 2, 8)] == 1 and sched.n[("A", 2, 3)] == 1 and sched.n[("A", 0, 4)] == 1
    assert flags["inventory_consistent"]
    assert sched.n == reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z)


def test_toy_parity_with_reachable_pruning_and_option_switches():
    inst = toy_instance()
    lib = build_arcs(inst)
    lib_r = build_arcs(inst, reachable_pruning=True)
    assert len(lib_r) < len(lib)
    for params in (None, BaselineParams(transfer_rule="REORDER_POINT")):
        s1, _ = run_baseline(inst, lib, params)
        s2, f2 = run_baseline(inst, lib_r, params)
        assert path_sig(s1, lib) == path_sig(s2, lib_r)
        assert s1.c == s2.c and s1.z == s2.z and s1.u == s2.u
        assert_contiguous_paths(inst, lib_r, s2)
        assert check(inst, lib_r, s2)["ok"]
        assert f2["pruned_arc_fallbacks"]["count"] == {"move": 0, "deliver": 0, "swap": 0}
    # opportunistic swaps change nothing here (nobody idles at A below full with stock)
    s3, _ = run_baseline(inst, lib, BaselineParams(transfer_rule="REORDER_POINT", opportunistic_swap=True))
    assert cost(inst, lib, s3)["total"] == pytest.approx(14.5)
    # the model switch no_transfers overrides the policy parameter
    inst2 = toy_instance()
    inst2.options["no_transfers"] = True
    lib2 = build_arcs(inst2)
    s4, f4 = run_baseline(inst2, lib2, BaselineParams(transfer_rule="REORDER_POINT"))
    assert f4["transfer_rule_effective"] == "NONE" and s4.h == {1: 0, 2: 0}
    assert check(inst2, lib2, s4)["ok"]
    # dict params and validation
    s5, _ = run_baseline(inst, lib, {"transfer_rule": "REORDER_POINT"})
    assert path_sig(s5, lib) == path_sig(run_baseline(inst, lib, BaselineParams(transfer_rule="REORDER_POINT"))[0], lib)
    with pytest.raises(ValueError):
        run_baseline(inst, lib, {"charge_rule": "RANDOM"})
    with pytest.raises(ValueError):
        BaselineParams(dispatch_scope="galaxy").validate()
    assert BaselineParams().threshold(12) == 3 and BaselineParams(q_thr=5).threshold(12) == 5


def test_toy_pruned_reposition_is_recorded_and_bikes_wait():
    """With move arcs allowed only into C, the bikes at (B, 2, 1) cannot head for A:
    they wait (stranded, reason 'pruned') and the fallback is recorded."""
    inst = toy_instance()
    lib = build_arcs(inst, reposition_targets={"C"})
    sched, flags = run_baseline(inst, lib)
    rep = check(inst, lib, sched)
    assert_hard_ok(rep)
    assert rep["ok"], rep
    assert_contiguous_paths(inst, lib, sched)
    assert flags["pruned_arc_fallbacks"]["count"]["move"] > 0
    assert flags["stranded_bikes"] == [1, 2]
    assert all(reason == "pruned" for (_, _, reason) in flags["stranded"])
    assert sched.u == {1: 0, 2: 0, 3: 1}
    assert cost(inst, lib, sched)["C_travel"] == pytest.approx(2.0)   # no returns
    # bikes end at (B, 8, 1): the certificate (9) still holds (gbar(B, A) = 1)
    assert flags["terminal_violations"] == []


# ---------------------------------------------------------------------------
# Battery_Swap p.7 queue table produced by the policy itself
# ---------------------------------------------------------------------------
def test_battery_swap_p7_table_from_policy():
    inst = battery_swap_p7_instance()
    lib = build_arcs(inst)
    sched, flags = run_baseline(inst, lib)
    rep = check(inst, lib, sched)
    assert rep["ok"], rep
    rows = [tuple(sched.n[("J", q, t)] for q in range(3)) for t in range(5)]
    assert rows == [(0, 0, 1), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)]
    assert sched.c == {("J", 0, 1): 1, ("J", 1, 2): 1}
    kinds = {k: [a.kind for a in sched.path(k, lib)] for k in (1, 2)}
    assert kinds[1] == ["swap", "wait", "wait", "wait", "term"]
    assert kinds[2] == ["wait", "wait", "wait", "swap", "term"]      # FCFS: bike 2 queues 3 slots
    assert flags["wait_slots_in_queue"] == {"J": 3} and flags["queued_at_H"] == []
    assert metrics(inst, lib, sched)["wait_before_swap"] == [0, 3]


# ---------------------------------------------------------------------------
# hand-made 1-bike / 2-order instance: the threshold rule triggers a swap
# ---------------------------------------------------------------------------
def one_bike_two_orders(L: int = 4) -> Instance:
    """Chain A - B, A = restaurant + swap site (B_A = 1), B = customer; one bike at
    (A, 0, 2); orders A -> B at r = 0 and r = 4; H = 8; each edge 1 slot / 1 level / 1 km."""
    disc = Discretisation(Delta_h=1 / 12, H=8, L=L, eps_kwh=0.02, eta=0.8)
    routes = {("A", "B"): Route(disc.Delta_h, disc.eps_kwh, 1.0),
              ("B", "A"): Route(disc.Delta_h, disc.eps_kwh, 1.0)}
    return Instance(
        disc=disc, nodes=["A", "B"], routes=routes,
        bikes=[Bike(1, "A", 2)],
        orders=[Order(1, "A", "B", r=0, a=0, b=2, hp=1, hd=0),
                Order(2, "A", "B", r=4, a=4, b=6, hp=1, hd=0)],
        facilities=[Facility("A", "A", swap=True, charge=False, y=1, B=1, C=0, K=1, M=1, sigma=1)],
        services=[], kappa=1.0, pi=2.0, q_res=0, rho=0.0,
    )


def test_threshold_rule_triggers_swap_and_is_needed():
    inst = one_bike_two_orders()
    assert inst.validate() == []
    lib = build_arcs(inst)
    sched, flags = run_baseline(inst, lib)                # q_thr = ceil(0.25 * 4) = 1
    rep = check(inst, lib, sched)
    assert rep["ok"], rep
    assert_contiguous_paths(inst, lib, sched)
    kinds = [(a.kind, a.src) for a in sched.path(1, lib)]
    # deliver 1 -> (B,2,1) is at threshold -> back to A -> swap at 3 -> deliver 2 at 4
    assert kinds[:4] == [("deliver", ("A", 0, 2)), ("move", ("B", 2, 1)), ("swap", ("A", 3, 0)),
                         ("deliver", ("A", 4, 4))]
    assert sched.u == {1: 0, 2: 0} and flags["n_swaps"] == 1
    assert sched.n[("A", 4, 0)] == 1 and sched.n[("A", 0, 4)] == 1 and sched.n[("A", 4, 4)] == 0
    assert cost(inst, lib, sched)["total"] == pytest.approx(3.0 + 2.0 + 2.0)   # 3 km, two 2-slot responses
    assert sched.n == reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z)
    # without the rule (q_thr = 0) the bike idles at (B, 2, 1) and cannot serve order 2
    sched0, flags0 = run_baseline(inst, lib, BaselineParams(q_thr=0))
    assert check(inst, lib, sched0)["ok"]
    assert sched0.u == {1: 0, 2: 1} and flags0["n_swaps"] == 0
    assert cost(inst, lib, sched0)["C_orders_parts"]["unserved"] == 100.0
    # end-reserve variant: keeping R_end = 1 full battery in the last 6 slots blocks the swap at t = 3
    inst_r = one_bike_two_orders()
    inst_r.facilities[0].R_end = 1
    inst_r.reindex()
    lib_r = build_arcs(inst_r)
    sched_r, flags_r = run_baseline(inst_r, lib_r, BaselineParams(end_reserve_window=6))
    assert check(inst_r, lib_r, sched_r)["ok"]
    assert flags_r["n_swaps"] == 0 and sched_r.u[2] == 1 and flags_r["end_shortfalls"] == {"local": {}, "global": 0.0}
    # ... and without the reserve the (17) shortfall is reported, not enforced
    sched_n, flags_n = run_baseline(inst_r, lib_r)
    rep_n = check(inst_r, lib_r, sched_n)
    assert_hard_ok(rep_n)
    assert "(17)" in rep_n["families"] and flags_n["end_shortfalls"]["local"] == {"A": 1}


# ---------------------------------------------------------------------------
# dispatch scope and charge rule
# ---------------------------------------------------------------------------
def test_zone_dispatch_prefers_same_zone_bike():
    """Restaurant R (zone z1); bike 1 at P (z1, 2 slots away), bike 2 at Qn (z2, 1 slot away)."""
    disc = Discretisation(Delta_h=1 / 12, H=8, L=6, eps_kwh=0.02, eta=0.8)
    edges = {("P", "R"): 2, ("R", "P"): 2, ("Qn", "R"): 1, ("R", "Qn"): 1, ("R", "D"): 1, ("D", "R"): 1}
    routes = {uv: Route(n * disc.Delta_h, n * disc.eps_kwh, float(n)) for uv, n in edges.items()}
    inst = Instance(
        disc=disc, nodes=["R", "D", "P", "Qn"], routes=routes,
        bikes=[Bike(1, "P", 6), Bike(2, "Qn", 6)],
        orders=[Order(1, "R", "D", r=0, a=0, b=4, hp=1, hd=0)],
        facilities=[Facility("R", "R", swap=True, charge=False, y=1, B=0, C=0, K=1, M=1, sigma=1)],
        services=[], options={"node_zone": {"R": "z1", "D": "z1", "P": "z1", "Qn": "z2"}},
    )
    assert inst.validate() == []
    lib = build_arcs(inst)
    s_glob, _ = run_baseline(inst, lib, BaselineParams(dispatch_scope="global"))
    s_zone, _ = run_baseline(inst, lib, BaselineParams(dispatch_scope="zone"))
    deliverer = lambda s: [k for k in s.x if any(lib.arc(a).kind == "deliver" for a in s.x[k])]
    assert deliverer(s_glob) == [2]          # nearest: tau 1
    assert deliverer(s_zone) == [1]          # same zone first: tau 2
    for s in (s_glob, s_zone):
        assert check(inst, lib, s)["ok"]
        assert_contiguous_paths(inst, lib, s)
    # 'zone' without the option behaves like 'global'
    inst.options.pop("node_zone")
    lib2 = build_arcs(inst)
    s_fallback, _ = run_baseline(inst, lib2, BaselineParams(dispatch_scope="zone"))
    assert deliverer(s_fallback) == [2]


def test_charge_rule_order_and_capacities():
    """One co-located station, two bikes swap at t = 0 returning levels 0 and 1; one
    charger: HIGH_FIRST charges the level-1 battery first, LOW_FIRST the empty one."""
    disc = Discretisation(Delta_h=1 / 12, H=4, L=3, eps_kwh=0.02, eta=0.8)
    fac = Facility("J", "J", swap=True, charge=True, y=1, B=2, C=1, K=2, Cbar=2, M=2, sigma=1,
                   P_kw=10.0, group="g1")
    inst = Instance(disc=disc, nodes=["J"], routes={}, bikes=[Bike(1, "J", 0), Bike(2, "J", 1)],
                    orders=[], facilities=[fac], services=[], P_grid={"g1": [10.0] * 4})
    assert inst.validate() == []
    lib = build_arcs(inst)
    s_hi, _ = run_baseline(inst, lib, BaselineParams(charge_rule="HIGH_FIRST"))
    s_lo, _ = run_baseline(inst, lib, BaselineParams(charge_rule="LOW_FIRST"))
    for s in (s_hi, s_lo):
        assert check(inst, lib, s)["ok"]
        assert tuple(s.n[("J", q, 1)] for q in range(4)) == (1, 1, 0, 0)
    assert s_hi.c[("J", 1, 1)] == 1 and ("J", 0, 1) not in s_hi.c
    assert s_lo.c[("J", 0, 1)] == 1 and ("J", 1, 1) not in s_lo.c
    # grid group limit binds below the charger count: 2 chargers but power for one battery
    fac.C, fac.P_kw = 2, 10.0
    inst.P_grid = {"g1": [disc.p_ch_kw] * 4}
    inst.reindex()
    lib = build_arcs(inst)
    s_g, _ = run_baseline(inst, lib)
    rep = check(inst, lib, s_g)
    assert rep["ok"], rep
    assert all(sum(s_g.c.get(("J", q, t), 0) for q in range(3)) <= 1 for t in range(4))


# ---------------------------------------------------------------------------
# reviewer findings F1 (just-in-time dispatch), F2 (dead zone), F6 (informed variants)
# ---------------------------------------------------------------------------
def jit_instance() -> Instance:
    """Restaurant R, customer D; bike 1 at P (1 slot from R), bike 2 at Qn (3 slots from
    R); the order is released at 0 but the food is ready at a = 3, so at t = 0 the
    library (dominance ON) holds a delivery arc for bike 2 (arrive 3 >= a) but none
    for the nearer bike 1 (arrive 1 < a; its dominating start is t = 2)."""
    disc = Discretisation(Delta_h=1 / 12, H=8, L=6, eps_kwh=0.02, eta=0.8)
    edges = {("P", "R"): 1, ("R", "P"): 1, ("Qn", "R"): 3, ("R", "Qn"): 3, ("R", "D"): 1, ("D", "R"): 1}
    routes = {uv: Route(n * disc.Delta_h, n * disc.eps_kwh, float(n)) for uv, n in edges.items()}
    return Instance(
        disc=disc, nodes=["R", "D", "P", "Qn"], routes=routes,
        bikes=[Bike(1, "P", 6), Bike(2, "Qn", 6)],
        orders=[Order(1, "R", "D", r=0, a=3, b=5, hp=1, hd=0)],
        facilities=[Facility("R", "R", swap=True, charge=False, y=1, B=0, C=0, K=1, M=1, sigma=1)],
        services=[], rho=0.0,
    )


def test_jit_dispatch_picks_nearest_idle_bike_when_food_is_not_ready():
    """Reviewer F1: with a_i > r_i the nearest idle bike must win (just-in-time start),
    not the farther one whose arc happens to survive the dominance rule."""
    inst = jit_instance()
    assert inst.validate() == []
    lib = build_arcs(inst)                                   # dominance ON (default)
    assert lib.find(1, "deliver", ("P", 0, 6), order=1) is None
    assert lib.find(1, "deliver", ("P", 2, 6), order=1) is not None
    assert lib.find(2, "deliver", ("Qn", 0, 6), order=1) is not None
    deliverer = lambda s, l: [k for k in s.x if any(l.arc(a).kind == "deliver" for a in s.x[k])]

    s_jit, f_jit = run_baseline(inst, lib)                   # jit_dispatch=True by default
    s_old, f_old = run_baseline(inst, lib, BaselineParams(jit_dispatch=False))
    for s in (s_jit, s_old):
        assert check(inst, lib, s)["ok"]
        assert_contiguous_paths(inst, lib, s)
    assert deliverer(s_old, lib) == [2] and f_old["jit_dispatches"] == 0       # pre-fix: farther bike
    assert deliverer(s_jit, lib) == [1] and f_jit["jit_dispatches"] == 1       # fixed: nearest bike
    path1 = [(a.kind, a.l) for a in s_jit.path(1, lib)]
    assert path1[:3] == [("wait", 0), ("wait", 1), ("deliver", 2)]            # waits until a_i - tau_r
    c_jit, c_old = cost(inst, lib, s_jit), cost(inst, lib, s_old)
    # fixed: 1 + 1 km; pre-fix: 3 + 1 km delivery plus a 1 km threshold trip (q = 2 = q_thr afterwards)
    assert c_jit["C_travel"] == pytest.approx(2.0) and c_old["C_travel"] == pytest.approx(5.0)
    assert c_jit["C_orders_parts"]["response"] == pytest.approx(c_old["C_orders_parts"]["response"])
    assert c_jit["total"] < c_old["total"]
    # parity: on the unpruned (dominance OFF) library the same dispatch happens without JIT
    lib_off = build_arcs(inst, dominance=False)
    s_off, f_off = run_baseline(inst, lib_off)
    assert deliverer(s_off, lib_off) == [1] and f_off["jit_dispatches"] == 0
    assert cost(inst, lib_off, s_off)["total"] == pytest.approx(c_jit["total"])
    # (the unpruned library holds the early-start arc from (P, 0, 6) itself, so the path
    # shape differs -- same completion u_a = 5, same energy, same cost)
    deliv = lambda s, l: [a for a in s.path(1, l) if a.kind == "deliver"][0]
    assert (deliv(s_off, lib_off).u, deliv(s_off, lib_off).dst) == (deliv(s_jit, lib).u, deliv(s_jit, lib).dst) == (5, ("D", 5, 4))


def dead_zone_instance() -> Instance:
    """Swap site A (one full spare), restaurant R, customer D.  The bike at R has q = 4
    (above q_thr = 2) but q - g_a = 2 < gbar(D, A) + q_res = 3: the reach guard refuses
    the only order, and without the dead-zone rule the bike idles to H."""
    disc = Discretisation(Delta_h=1 / 12, H=8, L=6, eps_kwh=0.02, eta=0.8)
    edges = {("A", "R"): 1, ("R", "A"): 1, ("R", "D"): 2, ("D", "A"): 2, ("D", "R"): 2}
    routes = {uv: Route(n * disc.Delta_h, n * disc.eps_kwh, float(n)) for uv, n in edges.items()}
    return Instance(
        disc=disc, nodes=["A", "R", "D"], routes=routes,
        bikes=[Bike(1, "R", 4)],
        orders=[Order(1, "R", "D", r=0, a=0, b=4, hp=1, hd=0)],
        facilities=[Facility("A", "A", swap=True, charge=False, y=1, B=1, C=0, K=1, M=1, sigma=1)],
        services=[], q_res=1, rho=0.0,
    )


def test_reach_refusal_sends_bike_to_swap_instead_of_idling():
    """Reviewer F2: a reach-only refusal with q <= max_need triggers a swap trip."""
    inst = dead_zone_instance()
    assert inst.validate() == []
    lib = build_arcs(inst)
    assert lib.find(1, "deliver", ("R", 0, 4), order=1) is not None       # the arc exists ...
    s_old, f_old = run_baseline(inst, lib, BaselineParams(swap_on_reach_refusal=False))
    assert check(inst, lib, s_old)["ok"]
    assert s_old.u == {1: 1} and f_old["n_swaps"] == 0                     # ... but the bike idles to H
    assert f_old["reach_refusals"]["count"] >= 1 and f_old["reach_refusals"]["bikes_sent_to_swap"] == 0
    assert f_old["q_thr"] == 2 and f_old["max_need"] == 7
    s_new, f_new = run_baseline(inst, lib)                                 # default: dead-zone rule on
    assert check(inst, lib, s_new)["ok"]
    assert_contiguous_paths(inst, lib, s_new)
    kinds = [(a.kind, a.src) for a in s_new.path(1, lib)]
    assert kinds[:3] == [("move", ("R", 0, 4)), ("swap", ("A", 1, 3)), ("deliver", ("A", 2, 6))]
    assert s_new.u == {1: 0} and f_new["n_swaps"] == 1
    assert f_new["reach_refusals"]["count"] == 1 and f_new["reach_refusals"]["bikes_sent_to_swap"] == 1
    assert cost(inst, lib, s_new)["total"] == pytest.approx(4.0 + 6.0 + 4.0)   # 4 km, response 6, lateness 4
    assert cost(inst, lib, s_old)["total"] == pytest.approx(100.0)


def test_late_threshold_window_suppresses_end_of_horizon_trips():
    """Reviewer F6 (b): no threshold trip whose swap would end after H - W."""
    inst = one_bike_two_orders()
    lib = build_arcs(inst)
    # the threshold trip at t = 2 (tau 1, sigma 1) ends at 4: allowed for W = 4, suppressed for W = 5
    s_ok, f_ok = run_baseline(inst, lib, BaselineParams(late_threshold_window=4))
    assert f_ok["n_swaps"] == 1 and f_ok["late_trips_suppressed"] == 0 and s_ok.u == {1: 0, 2: 0}
    s_sup, f_sup = run_baseline(inst, lib, BaselineParams(late_threshold_window=5))
    assert check(inst, lib, s_sup)["ok"]
    assert_contiguous_paths(inst, lib, s_sup)
    assert f_sup["n_swaps"] == 0 and f_sup["late_trips_suppressed"] >= 1 and s_sup.u == {1: 0, 2: 1}
    assert f_sup["stranded"] == []                       # suppressed trips are not 'stranded'


def two_site_instance(B_S2: int = 2) -> Instance:
    """Node X, swap sites S1 (empty, 1 slot from X) and S2 (``B_S2`` spares, 2 slots
    from X, 1 slot from S1); bikes at X and at S1 with ``q = 1 = q_thr`` both need a
    swap; each edge costs one level."""
    disc = Discretisation(Delta_h=1 / 12, H=8, L=4, eps_kwh=0.02, eta=0.8)
    edges = {("X", "S1"): 1, ("X", "S2"): 2, ("S1", "S2"): 1, ("S2", "S1"): 1}
    routes = {uv: Route(n * disc.Delta_h, disc.eps_kwh, float(n)) for uv, n in edges.items()}   # g = 1 each
    return Instance(
        disc=disc, nodes=["X", "S1", "S2"], routes=routes,
        bikes=[Bike(1, "X", 1), Bike(2, "S1", 1)],
        orders=[],
        facilities=[Facility("S1", "S1", swap=True, charge=False, y=1, B=0, C=0, K=1, M=1, sigma=1),
                    Facility("S2", "S2", swap=True, charge=False, y=1, B=B_S2, C=0, K=2, M=1, sigma=1)],
        services=[], q_res=0, rho=0.0,
    )


def test_stock_aware_site_choice_avoids_empty_site():
    """DECISIONS R2.3 (default ``stock_aware_site=True``): the swap trip goes to the
    nearest open site with ``n_jLt >= 1``; the round-1 naive rule heads for the
    nearest site regardless of stock and both bikes queue at empty S1 until H."""
    inst = two_site_instance()
    assert inst.validate() == []
    lib = build_arcs(inst)
    s_naive, f_naive = run_baseline(inst, lib, BaselineParams(stock_aware_site=False))
    assert f_naive["n_swaps"] == 0 and sorted(f_naive["queued_at_H"]) == [1, 2]   # both queue at empty S1
    assert f_naive["stock_aware_reroutes"] == 0 and f_naive["stock_aware_fallbacks"] == 0
    s_aware, f_aware = run_baseline(inst, lib)                                    # R2.3 default
    for s in (s_naive, s_aware):
        assert check(inst, lib, s)["ok"]
        assert_contiguous_paths(inst, lib, s)
        assert s.n == reconstruct_inventory(inst, lib, s.x, s.c, s.z)
    assert f_aware["n_swaps"] == 2 and f_aware["queued_at_H"] == []
    # bike 1 (X): naive nearest is S1, stocked nearest is S2 -> reroute; bike 2 leaves empty S1 -> reroute
    assert f_aware["stock_aware_reroutes"] == 2 and f_aware["stock_aware_fallbacks"] == 0
    assert [a.dst[0] for a in s_aware.path(1, lib) if a.kind == "move"] == ["S2"]
    assert [a.dst[0] for a in s_aware.path(2, lib) if a.kind == "move"] == ["S2"]
    assert cost(inst, lib, s_aware)["C_travel"] == pytest.approx(3.0)             # 2 km + 1 km
    # round-1 variant reproduces the naive run
    s_r1, _ = run_baseline(inst, lib, baseline_variant_params("round1"))
    assert path_sig(s_r1, lib) == path_sig(s_naive, lib)


def test_stock_aware_fallback_to_nearest_when_no_site_has_stock():
    """R2.3 fallback: with no stocked site anywhere the nearest site is used (and the
    bike standing at an empty site queues there); every such decision is counted."""
    inst = two_site_instance(B_S2=0)
    lib = build_arcs(inst)
    s, f = run_baseline(inst, lib)
    assert check(inst, lib, s)["ok"]
    assert_contiguous_paths(inst, lib, s)
    assert f["n_swaps"] == 0 and sorted(f["queued_at_H"]) == [1, 2]
    assert [a.dst[0] for a in s.path(1, lib) if a.kind == "move"] == ["S1"]          # nearest, as round 1
    assert f["stock_aware_reroutes"] == 0
    # bike 1 at X (t=0), bike 2 at S1 (t=0), bike 1 arriving at S1 (t=1): three fallbacks
    assert f["stock_aware_fallbacks"] == 3
    s_r1, _ = run_baseline(inst, lib, baseline_variant_params("round1"))
    assert path_sig(s_r1, lib) == path_sig(s, lib)


# ---------------------------------------------------------------------------
# DECISIONS R2.3: DEMAND_AWARE charging
# ---------------------------------------------------------------------------
def colocated_station(R_end: int = 0, H: int = 10) -> Instance:
    """One co-located station J (``L = 4``, 3 full spares, 2 chargers, 2 positions,
    ample power, ``K = 6``); two bikes at J with ``q = 0`` and ``q = 1`` (both at or
    below ``q_thr = 1``) swap at ``t = 0`` and return batteries at levels 0 and 1;
    no orders, so no further swap is ever observed."""
    disc = Discretisation(Delta_h=1 / 12, H=H, L=4, eps_kwh=0.02, eta=0.8)
    fac = Facility("J", "J", swap=True, charge=True, y=1, B=3, C=2, K=6, Cbar=2, M=2, sigma=1,
                   P_kw=10.0, group="g1", R_end=R_end)
    return Instance(disc=disc, nodes=["J"], routes={}, bikes=[Bike(1, "J", 0), Bike(2, "J", 1)],
                    orders=[], facilities=[fac], services=[], P_grid={"g1": [10.0] * H},
                    kappa=1.0, pi=2.0, q_res=0, rho=0.0)


def charged_per_slot(sched, H: int, L: int, j="J"):
    return [sum(sched.c.get((j, q, t), 0) for q in range(L)) for t in range(H)]


def test_demand_aware_charges_less_than_asap_without_forecast_and_as_much_with():
    """R2.3: ``need = forecast + reserve - n_jL``.  With ``lookback = 2``, ``lead = 4``
    the two swaps at t = 0 give forecast 8 (t = 0, one observed slot scaled) and 4
    (t = 1): the site charges as many batteries as ASAP (2, HIGH_FIRST: levels 1
    then 0).  From t = 2 on no swap lies in the window, forecast = 0, the reserve is
    0 and one full battery is in stock -> nothing is charged, whereas ASAP keeps
    charging until all batteries are full."""
    inst = colocated_station()
    assert inst.validate() == []
    lib = build_arcs(inst)
    H, L = inst.H, inst.L
    s_da, f_da = run_baseline(inst, lib, BaselineParams(charge_lookback=2, charge_lead=4))
    s_asap, f_asap = run_baseline(inst, lib, BaselineParams(charge_rule="ASAP"))      # alias of HIGH_FIRST
    for s in (s_da, s_asap):
        rep = check(inst, lib, s)
        assert rep["ok"], rep
        assert_contiguous_paths(inst, lib, s)
        assert s.n == reconstruct_inventory(inst, lib, s.x, s.c, s.z)
    assert f_da["n_swaps"] == f_asap["n_swaps"] == 2
    assert s_asap.meta["params"]["charge_rule"] == "HIGH_FIRST"
    assert f_da["charge_rule_effective"] == {"J": "DEMAND_AWARE"} and f_asap["charge_rule_effective"] == {"J": "HIGH_FIRST"}
    da = f_da["demand_aware"]
    assert da["forecast"]["J"][:3] == [8, 4, 0] and da["need"]["J"][:3] == [7, 3, 0]
    assert all(v == 0 for v in da["forecast"]["J"][2:])
    # t = 0: returned batteries enter stock at t = 1, nothing to charge yet; t = 1: both rules charge 2
    assert charged_per_slot(s_da, H, L) == [0, 2] + [0] * (H - 2)
    assert s_da.c == {("J", 1, 1): 1, ("J", 0, 1): 1}
    assert charged_per_slot(s_asap, H, L)[:2] == [0, 2] and sum(charged_per_slot(s_asap, H, L)) == 7   # 3 + 4 steps
    assert da["charge_steps"] == 2 < da["asap_cap_steps"]
    assert cost(inst, lib, s_da)["C_elec"] < cost(inst, lib, s_asap)["C_elec"]
    # end stock: DEMAND_AWARE keeps the one full battery, ASAP has all three full
    assert s_da.n[("J", L, H)] == 1 and s_asap.n[("J", L, H)] == 3
    # with the default lead = lookback = 12 > H every boundary still sees the two swaps
    # (forecast ceil(24 / (t+1)) >= 3 > full stock), so DEMAND_AWARE charges like ASAP here
    s_def, f_def = run_baseline(inst, lib)
    assert check(inst, lib, s_def)["ok"] and s_def.c == s_asap.c
    assert f_def["demand_aware"]["forecast"]["J"][0] == 24


def test_demand_aware_keeps_the_reserve_without_any_forecast():
    """R2.3: ``reserve_j = R_end_j``; with forecast 0 the site charges only up to the
    reserve, HIGH_FIRST (level 1 first, then the empty battery stays untouched)."""
    inst = colocated_station(R_end=2)
    lib = build_arcs(inst)
    H, L = inst.H, inst.L
    s, f = run_baseline(inst, lib, BaselineParams(charge_lookback=2, charge_lead=4))
    rep = check(inst, lib, s)
    assert rep["ok"], rep                                   # (17) met: 2 full at H
    assert s.n == reconstruct_inventory(inst, lib, s.x, s.c, s.z) and f["inventory_consistent"]
    # t = 1: need 3 -> 2 charged; t = 2: need = 0 + 2 - 1 = 1 -> level 2; t = 3: level 3 -> full at 4; then 0
    assert charged_per_slot(s, H, L) == [0, 2, 1, 1] + [0] * (H - 4)
    assert s.c[("J", 2, 2)] == 1 and s.c[("J", 3, 3)] == 1
    assert s.n[("J", L, H)] == 2 and s.n[("J", 1, H)] == 1
    assert f["demand_aware"]["need"]["J"][2:5] == [1, 1, 0]
    # charge_reserve overrides R_end (scalar or per site); 0 -> nothing after t = 1
    s0, _ = run_baseline(inst, lib, BaselineParams(charge_lookback=2, charge_lead=4, charge_reserve=0))
    assert charged_per_slot(s0, H, L) == [0, 2] + [0] * (H - 2)
    s3, f3 = run_baseline(inst, lib, BaselineParams(charge_lookback=2, charge_lead=4, charge_reserve={"J": 3}))
    assert s3.n[("J", L, H)] == 3 and f3["end_shortfalls"] == {"local": {}, "global": 0.0}
    # the reserve shortfall (17) is reported, not enforced, when R_end exceeds what can be charged
    inst5 = colocated_station(R_end=5)
    lib5 = build_arcs(inst5)
    s5, f5 = run_baseline(inst5, lib5)
    rep5 = check(inst5, lib5, s5)
    assert_hard_ok(rep5)
    assert set(rep5["families"]) <= {"(9)", "(17)", "(18)"} and f5["end_shortfalls"]["local"] == {"J": 2}


def test_demand_aware_hub_rule_on_toy_literal_vs_default():
    """The toy's charge site C is a hub (``j in C \\ S``): it never observes a swap, so
    the literal R2.3 forecast is 0 and C would never recharge the empty battery that
    arrives at t = 6 (electricity 0.1 saved, (18) violated: 14.4 instead of 14.5).
    The default ``hub_charge_rule='HIGH_FIRST'`` keeps the round-1 behaviour there."""
    inst = toy_instance()
    lib = build_arcs(inst)
    s_def, f_def = run_baseline(inst, lib, {"transfer_rule": "REORDER_POINT"})
    assert f_def["charge_rule_effective"] == {"C": "HIGH_FIRST"}
    assert cost(inst, lib, s_def)["total"] == pytest.approx(14.5) and check(inst, lib, s_def)["ok"]
    s_lit, f_lit = run_baseline(inst, lib, {"transfer_rule": "REORDER_POINT", "hub_charge_rule": "DEMAND_AWARE"})
    rep = check(inst, lib, s_lit)
    assert_hard_ok(rep)
    assert list(rep["families"]) == ["(18)"]                 # reported, not enforced
    assert f_lit["charge_rule_effective"] == {"C": "DEMAND_AWARE"} and s_lit.c == {}
    assert f_lit["demand_aware"]["asap_cap"]["C"] == [0] * 6 + [1, 1] and f_lit["demand_aware"]["charge_steps"] == 0
    assert cost(inst, lib, s_lit)["total"] == pytest.approx(14.4)
    assert f_lit["end_shortfalls"]["global"] == pytest.approx(1.0)
    assert s_lit.n == reconstruct_inventory(inst, lib, s_lit.x, s_lit.c, s_lit.z) and f_lit["inventory_consistent"]


def test_baseline_variants_and_param_validation():
    """``baseline_variant_params``: 'default' (R2.3), 'round1' (stock_aware False,
    HIGH_FIRST), 'legacy' (round-1 legacy flags); overrides merge; unknown names and
    invalid parameters raise."""
    assert BaselineParams().stock_aware_site is True and BaselineParams().charge_rule == "DEMAND_AWARE"
    assert (BaselineParams().charge_lead, BaselineParams().charge_lookback, BaselineParams().charge_reserve) == (12, 12, None)
    assert baseline_variant_params("default") == {}
    assert baseline_variant_params("round1") == {"stock_aware_site": False, "charge_rule": "HIGH_FIRST"}
    assert baseline_variant_params("legacy") == {"stock_aware_site": False, "charge_rule": "HIGH_FIRST",
                                                 "jit_dispatch": False, "swap_on_reach_refusal": False}
    assert set(BASELINE_VARIANTS) == {"default", "round1", "legacy"}
    p = baseline_variant_params("round1", transfer_rule="REORDER_POINT")
    assert p["transfer_rule"] == "REORDER_POINT" and p["charge_rule"] == "HIGH_FIRST"
    assert BaselineParams.coerce(baseline_variant_params("legacy")).jit_dispatch is False
    with pytest.raises(KeyError):
        baseline_variant_params("round2")
    with pytest.raises(ValueError):
        baseline_variant_params("default", charge_rule="RANDOM")
    with pytest.raises(ValueError):
        BaselineParams(charge_lookback=0).validate()
    with pytest.raises(ValueError):
        BaselineParams(charge_lead=-1).validate()
    with pytest.raises(ValueError):
        BaselineParams(hub_charge_rule="NONE").validate()
    assert BaselineParams.coerce({"charge_rule": "ASAP", "hub_charge_rule": "ASAP"}).charge_rule == "HIGH_FIRST"
    # all three variants run on the toy; the toy's only charge site is a hub, so the
    # round-2 defaults reproduce the round-1 numbers there (108 / 14.5)
    inst = toy_instance()
    lib = build_arcs(inst)
    for name in ("default", "round1", "legacy"):
        for rule, total in (("NONE", 108.0), ("REORDER_POINT", 14.5)):
            s, f = run_baseline(inst, lib, baseline_variant_params(name, transfer_rule=rule))
            assert cost(inst, lib, s)["total"] == pytest.approx(total), (name, rule)
            assert check(inst, lib, s)["ok"] and f["inventory_consistent"]
