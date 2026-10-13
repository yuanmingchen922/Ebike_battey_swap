"""Core tests: E2 toy arc counts, JSON round-trip, documented optimal schedule
(J = 12.5, zero violations), identity (24), inventory recursion on the
Battery_Swap p.7 table, and detection of a double-used battery."""
from __future__ import annotations

import json

import pytest

from ebike_swap_sim import (
    ArcLibrary,
    InfeasibleInstanceError,
    Instance,
    Schedule,
    battery_swap_p7_instance,
    build_arcs,
    check,
    compute_gbar,
    cost,
    metrics,
    reconstruct_inventory,
    toy_instance,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _ids(*arcs):
    for a in arcs:
        assert a is not None, "arc missing from library"
    return [a.id for a in arcs]


def toy_documented_schedule(lib: ArcLibrary) -> Schedule:
    """The optimal schedule of E2_Example p.14 (J = 12.5), written by hand."""
    f = lib.find
    bike1 = _ids(
        f(1, "deliver", ("A", 0, 2), order=1),          # (A,0,2) -> (B,2,1)
        f(1, "move", ("B", 2, 1), dst=("A", 3, 0)),     # return to A
        f(1, "swap", ("A", 3, 0), fac="A"),             # (A,3,0) -> (A,4,2)
        f(1, "deliver", ("A", 4, 2), order=3),          # (A,4,2) -> (B,6,1)
        f(1, "wait", ("B", 6, 1)),
        f(1, "wait", ("B", 7, 1)),
        f(1, "term", ("B", 8, 1), fac="A"),
    )
    bike2 = _ids(
        f(2, "deliver", ("A", 0, 2), order=2),          # (A,0,2) -> (B,2,1)
        *[f(2, "wait", ("B", t, 1)) for t in range(2, 8)],
        f(2, "term", ("B", 8, 1), fac="A"),
    )
    n = {}
    table = {0: ((0, 0, 0), (0, 0, 1)), 1: ((0, 0, 0), (0, 0, 1)), 2: ((0, 0, 0), (0, 0, 0)),
             3: ((0, 0, 1), (0, 0, 0)), 4: ((1, 0, 0), (0, 0, 0)), 5: ((0, 0, 0), (0, 0, 0)),
             6: ((0, 0, 0), (1, 0, 0)), 7: ((0, 0, 0), (0, 1, 0)), 8: ((0, 0, 0), (0, 0, 1))}
    for t, (rowA, rowC) in table.items():
        for q in range(3):
            n[("A", q, t)] = rowA[q]
            n[("C", q, t)] = rowC[q]
    return Schedule(
        x={1: bike1, 2: bike2},
        u={1: 0, 2: 0, 3: 0},
        c={("C", 0, 6): 1, ("C", 1, 7): 1},
        h={1: 1, 2: 1},
        z={(1, 2): 1, (2, 0): 1},
        n=n,
    )


# ---------------------------------------------------------------------------
# instance / arcs
# ---------------------------------------------------------------------------
def test_toy_instance_validates_and_discretisation():
    inst = toy_instance()
    assert inst.validate() == []
    assert inst.disc.p_ch_kw == pytest.approx(0.3)
    assert inst.disc.kwh_per_step == pytest.approx(0.025)
    assert inst.tau("B", "C") == 2 and inst.g("B", "C") == 2 and inst.d("B", "C") == 2.0
    assert inst.tau("A", "A") == 0 and inst.route("A", "A").d_km == 0.0
    assert inst.theta(1, 2) == pytest.approx(2.0)          # w Delta (u_a - r_i) = 1 * 2
    assert inst.theta(1, 3) == pytest.approx(3.0 + 2.0)    # one slot late: + v Delta = 2


def test_toy_arc_counts_no_pruning_dominance_off():
    inst = toy_instance()
    lib = build_arcs(inst, dominance=False)
    for k in (1, 2):
        c = lib.counts(k)
        assert c == {"wait": 72, "move": 78, "deliver": 62, "swap": 16, "term": 7, "total": 235}
    assert len(lib) == 470
    assert lib.infeasible_bikes == []


def test_toy_arc_counts_dominance_on_unchanged():
    inst = toy_instance()
    lib = build_arcs(inst)                       # dominance ON by default
    assert lib.options["dominance"] is True
    assert lib.counts(1)["deliver"] == 62        # a_i = r_i: nothing to prune
    assert lib.counts(1)["total"] == 235
    # index consistency
    assert len(lib.delivery_arcs(1)) == 26 * 2 and len(lib.delivery_arcs(3)) == 10 * 2
    assert len(lib.swap_arcs("A")) == 32 and len(lib.swap_arcs_at("A", 3, 0)) == 2
    assert len(lib.terminal_arcs(1)) == 7
    assert sum(len(lib.out_arcs(1, s)) for s in lib.states(1)) == 235
    assert sum(len(lib.in_arcs(1, s)) for s in lib.states(1)) == 235


def test_gbar_and_pruning_options():
    inst = toy_instance()
    gbar = compute_gbar(inst)
    assert gbar == {("A", "A"): 0, ("B", "A"): 1, ("C", "A"): 1}
    lib = build_arcs(inst, reposition_targets={"A"}, tau_max=0, start_slack=0, swap_q_max=0)
    c = lib.counts(1)
    assert c["move"] == 32                 # only B->A and C->A
    assert c["swap"] == 8                  # q = 0 only
    # deliveries only from A (tau_max=0) and t <= b_i: orders 1,2: t 0..2, q 1,2 -> 6 each; order 3: t 4..6 -> 6
    assert c["deliver"] == 18
    # forward reachability pruning: every kept arc leaves a state reachable from s_k,
    # the documented optimal path survives, and the library shrinks
    lib_r = build_arcs(inst, reachable_pruning=True)
    assert len(lib_r) < 470 and lib_r.infeasible_bikes == []
    reach = {lib_r.source(1)}
    for a in sorted(lib_r.arcs_of(1), key=lambda a: a.l):
        assert a.src in reach
        reach.add(a.dst)
    assert lib_r.find(1, "deliver", ("A", 0, 2), order=1) is not None
    assert lib_r.find(1, "swap", ("A", 3, 0), fac="A") is not None
    assert lib_r.find(1, "wait", ("C", 0, 2)) is None       # (C,0,2) is unreachable


def test_infeasible_bike_detected_and_dummy_terminal():
    inst = toy_instance()
    inst.q_res = 3                          # no terminal arc can exist (q <= L = 2)
    with pytest.raises(InfeasibleInstanceError):
        build_arcs(inst)
    lib = build_arcs(inst, strict=False)
    assert lib.infeasible_bikes == [1, 2]
    lib = build_arcs(inst, dummy_terminal_cost=50.0)
    assert lib.infeasible_bikes == [1, 2] and lib.has_dummy_terminal
    assert lib.counts(1)["term"] == 9      # 3 nodes x 3 levels dummy arcs


def test_concat_rounding_toy_identical():
    inst = toy_instance()
    a = build_arcs(inst, energy_rounding="per_leg")
    b = build_arcs(inst, energy_rounding="concat")
    key = lambda lib: sorted((x.kind, x.src, x.dst, x.order, x.fac, x.theta) for x in lib.arcs_of(1))
    assert key(a) == key(b)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------
def test_json_round_trip_toy():
    inst = toy_instance()
    s = inst.to_json()
    inst2 = Instance.from_json(s)
    assert inst2 == inst
    assert inst2.to_json() == s
    assert build_arcs(inst2).counts(1) == build_arcs(inst).counts(1)


def test_json_round_trip_tuple_nodes_and_dict_pi():
    inst = toy_instance()
    # rename nodes to grid tuples, use a (facility, t) price dict and reposition targets
    ren = {"A": (0, 0), "B": (0, 1), "C": (1, 0)}
    inst.nodes = [ren[v] for v in inst.nodes]
    inst.routes = {(ren[u], ren[v]): r for (u, v), r in inst.routes.items()}
    for b in inst.bikes:
        b.v0 = ren[b.v0]
    for o in inst.orders:
        o.o, o.d = ren[o.o], ren[o.d]
    for f in inst.facilities:
        f.node = ren[f.node]
    inst.pi = {("C", t): 2.0 + t for t in range(inst.H)}
    inst.options["reposition_targets"] = {(0, 0)}
    inst.reindex()
    inst.validate()
    inst2 = Instance.from_json(inst.to_json())
    assert inst2 == inst
    assert inst2.price("C", 3) == 5.0 and inst2.routes[((0, 1), (1, 0))].d_km == 2.0
    assert inst2.options["reposition_targets"] == {(0, 0)}


# ---------------------------------------------------------------------------
# documented optimum: cost 12.5, zero violations, identity
# ---------------------------------------------------------------------------
def test_toy_documented_schedule_cost_and_check():
    inst = toy_instance()
    lib = build_arcs(inst)
    sched = toy_documented_schedule(lib)
    cst = cost(inst, lib, sched)
    assert cst["total"] == pytest.approx(12.5)
    assert cst["C_travel"] == pytest.approx(4.0)
    assert cst["C_elec"] == pytest.approx(0.1)
    assert cst["C_orders_parts"]["unserved"] == 0
    assert cst["C_orders_parts"]["response"] == pytest.approx(6.0)
    assert cst["C_orders_parts"]["lateness"] == 0
    assert cst["C_reb"] == pytest.approx(2.4)
    assert cst["C_setup"] == 0
    rep = check(inst, lib, sched)
    assert rep["ok"], rep
    assert rep["n_violations"] == 0 and rep["identity_24_ok"] and rep["n_source"] == "given"
    # the same schedule without n: reconstruction must reproduce the p.15 table
    sched2 = Schedule(x=sched.x, u=sched.u, c=sched.c, h=sched.h, z=sched.z)
    n_rec = reconstruct_inventory(inst, lib, sched2.x, sched2.c, sched2.z)
    assert n_rec == sched.n
    rep2 = check(inst, lib, sched2)
    assert rep2["ok"] and rep2["n_source"] == "reconstructed"
    # Schedule JSON round-trip
    s3 = Schedule.from_dict(json.loads(json.dumps(sched.to_dict())))
    assert cost(inst, lib, s3)["total"] == pytest.approx(12.5)
    assert check(inst, lib, s3)["ok"]


def test_toy_metrics():
    inst = toy_instance()
    lib = build_arcs(inst)
    m = metrics(inst, lib, toy_documented_schedule(lib))
    assert m["served_share"] == 1.0 and m["n_late"] == 0
    assert m["mean_response_h"] == pytest.approx(2 / 12)
    assert m["bike_km"] == pytest.approx(4.0) and m["n_swaps"] == 1
    assert m["kwh_purchased"] == pytest.approx(0.05) and m["kwh_stored"] == pytest.approx(0.04)
    assert m["peak_kw_facility"]["C"] == pytest.approx(0.3) and m["peak_kw_group"]["g1"] == pytest.approx(0.3)
    assert m["transfers_used"] == 2 and m["batteries_moved"] == 2
    assert m["in_transit"] == [0, 0, 1, 0, 0, 1, 0, 0, 0]
    assert m["full_stock"]["C"] == [1, 1, 0, 0, 0, 0, 0, 0, 1]
    assert m["full_stock"]["A"] == [0, 0, 0, 1, 0, 0, 0, 0, 0]
    assert m["end_target_shortfall"] == 0
    assert m["wait_before_swap"] == [0]
    assert m["bike_end_levels"] == {1: 1, 2: 1}


def test_identity_24_random_recursion():
    """(24) holds for any (13) recursion, including one-slot services."""
    import random
    from ebike_swap_sim.or_instance import Service
    from ebike_swap_sim.evaluate import in_transit
    rng = random.Random(3)
    inst = toy_instance()
    inst.rho = 0.0
    inst.facilities[0].B, inst.facilities[0].K = 2, 10
    inst.facilities[1].B, inst.facilities[1].K = 3, 10
    inst.services = [Service(e, *rng.choice([("A", "C"), ("C", "A")]), l := rng.randrange(0, 7), rng.randrange(l + 1, 9), 3)
                     for e in range(1, 7)]
    inst.reindex()
    inst.validate()
    lib = build_arcs(inst)
    z = {(e.id, q): rng.randrange(0, 2) for e in inst.services for q in range(3)}
    c = {("C", q, t): rng.randrange(0, 2) for q in range(2) for t in range(8)}
    x = {1: [lib.find(1, "swap", ("A", 0, 2 - 2), fac="A").id], 2: []}  # one swap (A,0,0)
    n = reconstruct_inventory(inst, lib, x, c, z)
    m = in_transit(inst, z)
    for t in range(9):
        assert sum(n[(j, q, t)] for j in "AC" for q in range(3)) + m[t] == 5


# ---------------------------------------------------------------------------
# Battery_Swap p.7 table
# ---------------------------------------------------------------------------
def test_battery_swap_p7_inventory_table():
    inst = battery_swap_p7_instance()
    inst.validate()
    lib = build_arcs(inst)
    f = lib.find
    sched = Schedule(
        x={1: _ids(f(1, "swap", ("J", 0, 0), fac="J"), *[f(1, "wait", ("J", t, 2)) for t in range(1, 4)],
                   f(1, "term", ("J", 4, 2), fac="J")),
           2: _ids(*[f(2, "wait", ("J", t, 0)) for t in range(0, 3)], f(2, "swap", ("J", 3, 0), fac="J"),
                   f(2, "term", ("J", 4, 2), fac="J"))},
        u={}, c={("J", 0, 1): 1, ("J", 1, 2): 1},
    )
    n = reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z)
    rows = [tuple(n[("J", q, t)] for q in range(3)) for t in range(5)]
    assert rows == [(0, 0, 1), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)]
    rep = check(inst, lib, sched)
    assert rep["ok"], rep
    # the second swap cannot start before t = 3: starting at t = 2 violates (14)
    bad = Schedule(
        x={1: sched.x[1],
           2: _ids(*[f(2, "wait", ("J", t, 0)) for t in range(0, 2)], f(2, "swap", ("J", 2, 0), fac="J"),
                   f(2, "wait", ("J", 3, 2)), f(2, "term", ("J", 4, 2), fac="J"))},
        u={}, c=sched.c,
    )
    rep = check(inst, lib, bad)
    assert not rep["ok"] and "(14)" in rep["families"]


# ---------------------------------------------------------------------------
# broken schedules
# ---------------------------------------------------------------------------
def test_double_used_battery_detected():
    """Both bikes swap at A at t = 3 although only one full spare arrives: (14) and (22)."""
    inst = toy_instance()
    lib = build_arcs(inst)
    good = toy_documented_schedule(lib)
    f = lib.find
    bike2 = _ids(
        f(2, "deliver", ("A", 0, 2), order=2),
        f(2, "move", ("B", 2, 1), dst=("A", 3, 0)),
        f(2, "swap", ("A", 3, 0), fac="A"),
        *[f(2, "wait", ("A", t, 2)) for t in range(4, 8)],
        f(2, "term", ("A", 8, 2), fac="A"),
    )
    bad = Schedule(x={1: good.x[1], 2: bike2}, u=good.u, c=good.c, h=good.h, z=good.z)
    rep = check(inst, lib, bad)
    assert not rep["ok"]
    fams = rep["families"]
    assert "(14)" in fams and "(22)" in fams
    assert any("S + D = 2 > n_L = 1" in ex for ex in fams["(14)"]["examples"])
    # cost still prices the schedule (travel 5 km now)
    assert cost(inst, lib, bad)["C_travel"] == pytest.approx(5.0)


def test_broken_flow_and_order_constraints_detected():
    inst = toy_instance()
    lib = build_arcs(inst)
    good = toy_documented_schedule(lib)
    # drop a wait arc -> (5) broken; claim order 3 unserved although delivered -> (6)
    x1 = [a for a in good.x[1] if lib.arc(a).kind != "wait"]
    bad = Schedule(x={1: x1, 2: good.x[2]}, u={1: 0, 2: 0, 3: 1}, c=good.c, h=good.h, z=good.z)
    rep = check(inst, lib, bad)
    assert "(5)" in rep["families"] and "(6)" in rep["families"]
    # inconsistent given inventory -> (13)
    n_bad = dict(good.n)
    n_bad[("A", 2, 5)] = 1
    rep = check(inst, lib, Schedule(x=good.x, u=good.u, c=good.c, h=good.h, z=good.z, n=n_bad))
    assert "(13)" in rep["families"]
    # charging where no stock -> (14); service used with no load -> (10)
    rep = check(inst, lib, Schedule(x=good.x, u=good.u, c={("C", 0, 0): 1}, h={1: 1}, z={}))
    assert "(14)" in rep["families"] and "(10)" in rep["families"]
    # closed site with stock -> (7)-(8) / (15); terminal at closed site -> (9)
    rep = check(inst, lib, Schedule(x=good.x, u=good.u, c=good.c, h=good.h, z=good.z,
                                    y={"A": 0, "C": 1}, B={"A": 0, "C": 1}, C={"A": 0, "C": 1}))
    assert "(9)" in rep["families"] and "(15)" in rep["families"] and "(10)" in rep["families"]


# ---------------------------------------------------------------------------
# reviewer findings: arc-library superset property, (9) open paths, checker switches,
# P_kw = 0 warning
# ---------------------------------------------------------------------------
def _arc_keys(lib: ArcLibrary, k) -> set:
    return {(a.kind, a.src, a.dst, a.order, a.fac, a.g, round(a.theta, 9)) for a in lib.arcs_of(k)}


def concat_break_instance() -> Instance:
    """Reviewer (ilp) F1 instance: Delta = 1 h, H = 4, L = 4; V -> O and O -> D each
    0.5 h (tau 1 each, tau_cat 1); order r = 0, a = 3, b = 3, hp = 1, hd = 0; bike at
    (V, 0, 4).  With 'concat' rounding u_a is not monotone in t for t + tau_r < a_i."""
    from ebike_swap_sim import Bike, Discretisation, Facility, Instance, Order, Route
    disc = Discretisation(Delta_h=1.0, H=4, L=4, eps_kwh=0.1, eta=1.0)
    routes = {("V", "O"): Route(0.5, 0.1, 1.0), ("O", "D"): Route(0.5, 0.1, 1.0), ("D", "O"): Route(0.5, 0.1, 1.0)}
    return Instance(
        disc=disc, nodes=["V", "O", "D"], routes=routes, bikes=[Bike(1, "V", 4)],
        orders=[Order(1, "O", "D", r=0, a=3, b=3, hp=1, hd=0)],
        facilities=[Facility("O", "O", swap=True, charge=False, y=1, B=0, C=0, K=1, M=1, sigma=1)],
        services=[], q_res=0, rho=0.0,
    )


@pytest.mark.parametrize("rounding", ["per_leg", "concat"])
def test_dominance_off_library_is_superset_of_dominance_on(rounding):
    """build_arcs(dominance=False) contains every arc of build_arcs(dominance=True) for
    both energy-rounding modes (reviewer ilp F1: the early 'break' in _delivery_specs
    must only fire once arrive >= a_i)."""
    from ebike_swap_sim import toy_instance as _toy
    cases = []
    t3 = _toy()
    t3.orders[2].r, t3.orders[2].a = 2, 4                    # a_i > r_i: dominance prunes something
    t3.reindex()
    cases.append(("toy a>r", t3))
    cases.append(("concat-break", concat_break_instance()))
    for name, inst in cases:
        assert inst.validate() == []
        on = build_arcs(inst, dominance=True, energy_rounding=rounding)
        off = build_arcs(inst, dominance=False, energy_rounding=rounding)
        for b in inst.bikes:
            k_on, k_off = _arc_keys(on, b.id), _arc_keys(off, b.id)
            assert k_on <= k_off, (name, rounding, k_on - k_off)
            # only delivery arcs with t + tau_r < a_i may be missing from the pruned library
            for kind, src, dst, order, *_ in k_off - k_on:
                assert kind == "deliver"
                o = inst.order(order)
                assert src[1] + inst.tau(src[0], o.o) < o.a, (name, src, order)
    # the reviewer's instance: 'concat' keeps the valid later starts under both settings
    inst = concat_break_instance()
    on = build_arcs(inst, dominance=True, energy_rounding="concat")
    off = build_arcs(inst, dominance=False, energy_rounding="concat")
    assert on.counts(1)["deliver"] == off.counts(1)["deliver"] > 0
    assert all(a.l == 2 and a.u == 4 for a in off.delivery_arcs(1))
    assert build_arcs(inst, dominance=False, energy_rounding="per_leg").counts(1)["deliver"] == 0  # u_a = 5 > H


def test_open_path_at_horizon_is_reported_under_9_not_5():
    """Reviewer (baseline) F5: a path that tiles [0, H] but has no terminal arc has no
    certificate (9); the checker must not call it a broken flow (5)."""
    inst = toy_instance()
    lib = build_arcs(inst)
    good = toy_documented_schedule(lib)
    x2 = [a for a in good.x[2] if lib.arc(a).kind != "term"]
    rep = check(inst, lib, Schedule(x={1: good.x[1], 2: x2}, u=good.u, c=good.c, h=good.h, z=good.z))
    assert "(9)" in rep["families"] and rep["families"]["(9)"]["count"] == 1
    assert "(5)" not in rep["families"]
    assert "without a terminal certificate" in rep["families"]["(9)"]["examples"][0]
    # a genuinely broken flow (missing interior arc) is still (5)
    x1 = [a for a in good.x[1] if lib.arc(a).kind != "wait"]
    rep = check(inst, lib, Schedule(x={1: x1, 2: good.x[2]}, u=good.u, c=good.c, h=good.h, z=good.z))
    assert "(5)" in rep["families"]


def test_check_reads_effective_switches():
    """Reviewer (ilp) F5: no_transfers / zeta / budget passed as model switches are
    verified by the checker even when the instance does not carry them."""
    inst = toy_instance()
    lib = build_arcs(inst)
    good = toy_documented_schedule(lib)                     # uses both transfers, serves all orders
    assert check(inst, lib, good)["ok"]
    rep = check(inst, lib, good, switches={"no_transfers": True})
    assert "(10)" in rep["families"]
    assert check(inst, lib, good, switches={"zeta": 1.0})["ok"]
    bad_u = Schedule(x=good.x, u={1: 0, 2: 0, 3: 1}, c=good.c, h=good.h, z=good.z)   # (6) broken on purpose
    fams = check(inst, lib, bad_u, switches={"zeta": 1.0})["families"]
    assert "(33)" in fams and "(33)" not in check(inst, lib, bad_u)["families"]
    inst.facilities[0].Fhat = 10.0
    inst.reindex()
    assert "(33)" in check(inst, lib, good, switches={"budget": 5.0})["families"]
    assert "(33)" not in check(inst, lib, good, switches={"budget": None})["families"]


def test_validate_warns_on_charge_site_without_power():
    """Reviewer (ilp) F6: Cbar_j > 0 with P_j = 0 kW silently forbids charging by (20)."""
    from ebike_swap_sim import Bike, Discretisation, Facility, Instance
    disc = Discretisation(Delta_h=1 / 12, H=4, L=2, eps_kwh=0.02, eta=0.8)
    mk = lambda P: Instance(disc=disc, nodes=["J"], routes={}, bikes=[Bike(1, "J", 2)], orders=[],
                            facilities=[Facility("J", "J", swap=True, charge=True, y=1, B=1, C=1, K=2,
                                                 Cbar=1, M=1, sigma=1, P_kw=P)], services=[], rho=0.0)
    with pytest.warns(UserWarning, match="P_j = 0 kW"):
        assert mk(0.0).validate() == []                       # a warning, not an error
    import warnings as _w
    with _w.catch_warnings():
        _w.simplefilter("error")
        assert mk(1.0).validate() == []
