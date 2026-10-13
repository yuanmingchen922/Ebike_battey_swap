"""Tests of the Gurobi model (``ilp.py``) on the E2 toy (pp.10-15, J* = 12.5) and the
Battery_Swap p.7 instance: documented optimum and components, p.15 inventory
table, what-ifs (rho = 0 -> 11.2, no transfers -> 106.0), lexicographic
service-first, co-location, free facilities, dummy terminal arcs (q_res = 1
probe: 206.5), MIP starts (accepted / rejected), infeasible switches and the
stats contract.  All solves take milliseconds; OutputFlag stays 0."""
from __future__ import annotations

import pytest

pytest.importorskip("gurobipy")

from ebike_swap_sim import (
    ArcLibrary,
    Schedule,
    battery_swap_p7_instance,
    build_arcs,
    check,
    cost,
    toy_instance,
)
from ebike_swap_sim import ilp
from ebike_swap_sim.ilp import ILPConsistencyError, ILPModel, build_model, colocated_instance, solve

P15_TABLE = {0: ((0, 0, 0), (0, 0, 1)), 1: ((0, 0, 0), (0, 0, 1)), 2: ((0, 0, 0), (0, 0, 0)),
             3: ((0, 0, 1), (0, 0, 0)), 4: ((1, 0, 0), (0, 0, 0)), 5: ((0, 0, 0), (0, 0, 0)),
             6: ((0, 0, 0), (1, 0, 0)), 7: ((0, 0, 0), (0, 1, 0)), 8: ((0, 0, 0), (0, 0, 1))}


def _ids(*arcs):
    for a in arcs:
        assert a is not None, "arc missing from library"
    return [a.id for a in arcs]


def toy_documented_schedule(lib: ArcLibrary) -> Schedule:
    """E2_Example p.14 optimal schedule (without n: reconstructed by evaluate)."""
    f = lib.find
    bike1 = _ids(
        f(1, "deliver", ("A", 0, 2), order=1), f(1, "move", ("B", 2, 1), dst=("A", 3, 0)),
        f(1, "swap", ("A", 3, 0), fac="A"), f(1, "deliver", ("A", 4, 2), order=3),
        f(1, "wait", ("B", 6, 1)), f(1, "wait", ("B", 7, 1)), f(1, "term", ("B", 8, 1), fac="A"),
    )
    bike2 = _ids(f(2, "deliver", ("A", 0, 2), order=2),
                 *[f(2, "wait", ("B", t, 1)) for t in range(2, 8)],
                 f(2, "term", ("B", 8, 1), fac="A"))
    return Schedule(x={1: bike1, 2: bike2}, u={1: 0, 2: 0, 3: 0},
                    c={("C", 0, 6): 1, ("C", 1, 7): 1}, h={1: 1, 2: 1}, z={(1, 2): 1, (2, 0): 1})


def _components(st):
    c = st["cost"]
    return (c["C_travel"], c["C_elec"], c["C_orders_parts"]["unserved"],
            c["C_orders_parts"]["response"], c["C_reb"])


@pytest.fixture
def toy():
    inst = toy_instance()
    return inst, build_arcs(inst)


# ---------------------------------------------------------------------------
# documented optimum
# ---------------------------------------------------------------------------
def test_toy_optimum_12_5_components_and_p15_table(toy):
    inst, lib = toy
    sched, st = solve(inst, lib)
    assert st["status"] == "OPTIMAL" and st["obj"] == pytest.approx(12.5)
    assert _components(st) == pytest.approx((4.0, 0.1, 0.0, 6.0, 2.4))
    assert st["cost"]["C_orders_parts"]["lateness"] == 0 and st["cost"]["C_setup"] == 0
    # inventory table p.15 (facility stock does not depend on bike/order relabelling)
    for t, (rowA, rowC) in P15_TABLE.items():
        assert tuple(sched.n[("A", q, t)] for q in range(3)) == rowA, t
        assert tuple(sched.n[("C", q, t)] for q in range(3)) == rowC, t
    assert sched.u == {1: 0, 2: 0, 3: 0}
    assert sched.h == {1: 1, 2: 1} and sched.z == {(1, 2): 1, (2, 0): 1}
    assert sched.c == {("C", 0, 6): 1, ("C", 1, 7): 1}
    assert sched.y == {"A": 1, "C": 1} and sched.B == {"A": 0, "C": 1} and sched.C == {"A": 0, "C": 1}
    # one bike makes two deliveries and swaps once, the other delivers once
    kinds = {k: sorted(a.kind for a in sched.path(k, lib)) for k in (1, 2)}
    n_deliv = sorted(kinds[k].count("deliver") for k in (1, 2))
    assert n_deliv == [1, 2]
    assert sum(kinds[k].count("swap") for k in (1, 2)) == 1
    # independent re-check and re-pricing
    rep = check(inst, lib, sched)
    assert rep["ok"] and rep["identity_24_ok"] and rep["n_source"] == "given"
    assert cost(inst, lib, sched)["total"] == pytest.approx(st["obj"])
    assert sched.meta["status"] == "OPTIMAL" and sched.meta["obj"] == pytest.approx(12.5)


def test_toy_model_sizes_and_stats_contract(toy):
    inst, lib = toy
    mdl = build_model(inst, lib)
    assert isinstance(mdl, ILPModel)
    assert mdl.model.Params.OutputFlag == 0 and mdl.model.Params.Threads == 4
    assert mdl.model.Params.TimeLimit == 600.0
    sched, st = mdl.solve()
    # x 470 + u 3 + y 2 + B 2 + C 2 + n 54 + c 16 + h 2 + z 6
    assert st["n_vars"] == 557 and st["n_binaries"] == 477 and st["n_arcs"] == 470
    assert st["n_rows"] == 315 and st["n_nonzeros"] > 0
    fam = st["rows_by_family"]
    assert fam["(5)"] == 2 * 82 and fam["(6)"] == 3 and fam["(13)"] == 2 * 3 * 8
    assert fam["(15)"] == 2 * 9 and fam["(16)"] == 6 and fam["(17)"] == 1 and fam["(18)"] == 1
    assert fam["(20)"] == 16 and fam["(21)"] == 8 and fam["(22)"] == 8 and fam["(9)"] == 2
    for key in ("status", "obj", "bound", "gap", "runtime", "build_time", "cost", "components",
                "check", "mip_start", "switches", "sol_count", "node_count"):
        assert key in st
    assert st["gap"] == pytest.approx(0.0, abs=1e-6) and st["bound"] == pytest.approx(12.5)
    assert st["components"]["C_travel"] == pytest.approx(4.0)
    assert st["components"]["C_dummy_terminal"] == 0.0
    assert st["check"]["ok"] and st["mip_start"] == {"given": False}
    assert st["switches"]["fixed_facilities"] is True and st["switches"]["no_transfers"] is False


# ---------------------------------------------------------------------------
# what-ifs (verified in notes/verify/toy_e2_example.py)
# ---------------------------------------------------------------------------
def test_rho_zero_gives_11_2():
    inst = toy_instance()
    inst.rho = 0.0
    sched, st = solve(inst, build_arcs(inst))
    assert st["obj"] == pytest.approx(11.2)
    assert _components(st) == pytest.approx((4.0, 0.0, 0.0, 6.0, 1.2))
    assert sched.h == {1: 1, 2: 0}


def test_no_transfers_gives_106(toy):
    inst, lib = toy
    sched, st = solve(inst, lib, no_transfers=True)
    assert st["obj"] == pytest.approx(106.0)
    assert sum(sched.u.values()) == 1 and not any(sched.h.values()) and sched.z == {}
    assert st["switches"]["no_transfers"] is True
    # the switch may also come from the instance options
    inst2 = toy_instance()
    inst2.options["no_transfers"] = True
    lib2 = build_arcs(inst2)
    _, st2 = solve(inst2, lib2)
    assert st2["obj"] == pytest.approx(106.0) and st2["switches"]["no_transfers"] is True


def test_lexicographic_service_first(toy):
    inst, lib = toy
    sched, st = solve(inst, lib, lexicographic=True)
    assert st["obj"] == pytest.approx(12.5)
    assert st["lex_min_unserved"] == 0 and st["lex_stage1_status"] == "OPTIMAL"
    sched, st = solve(inst, lib, lexicographic=True, no_transfers=True)
    assert st["lex_min_unserved"] == 1 and st["obj"] == pytest.approx(106.0)


def test_zeta_and_budget(toy):
    inst, lib = toy
    _, st = solve(inst, lib, zeta=1.0)
    assert st["obj"] == pytest.approx(12.5) and st["rows_by_family"]["(33)"] == 1
    _, st = solve(inst, lib, budget=0.0)          # all investment coefficients are 0
    assert st["obj"] == pytest.approx(12.5)
    sched, st = solve(inst, lib, zeta=1.0, no_transfers=True)   # all served is impossible
    assert sched is None and st["status"] == "INFEASIBLE" and st["obj"] is None
    assert st["sol_count"] == 0


def test_battery_swap_v1_bounds_make_toy_infeasible(toy):
    inst, lib = toy
    sched, st = solve(inst, lib, battery_swap_v1_bounds=True)   # y_A = 1 > B_A = 0
    assert sched is None and st["status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# facilities free / co-located
# ---------------------------------------------------------------------------
def test_free_facilities_relaxation(toy):
    inst, lib = toy
    sched, st = solve(inst, lib, fixed_facilities=False)
    assert st["status"] == "OPTIMAL" and st["obj"] <= 12.5 + 1e-9
    assert st["obj"] == pytest.approx(11.3)      # spare placed at A: swap without transport 1
    assert sched.B == {"A": 1, "C": 0} and sched.y == {"A": 1, "C": 1}
    assert all(isinstance(v, int) for d in (sched.y, sched.B, sched.C) for v in d.values())
    assert check(inst, lib, sched)["ok"]


def test_colocated_variant_runs(toy):
    inst, lib = toy
    mdl = build_model(inst, lib, colocated=True)
    assert mdl.inst is not inst and mdl.lib is not lib
    assert set(mdl.inst.S) == {"A", "C"} and set(mdl.inst.Cset) == {"A", "C"}
    assert mdl.inst.facility("C").M == 1 and mdl.inst.options["colocated"] is True
    assert len(mdl.lib) > len(lib)                      # swap arcs at C, more terminal arcs
    sched, st = mdl.solve()
    assert st["status"] == "OPTIMAL" and st["obj"] <= 12.5 + 1e-9
    assert st["obj"] == pytest.approx(12.5)             # the extra swap site at C does not help
    assert sched.meta["colocated"] is True
    assert check(mdl.inst, mdl.lib, sched)["ok"]
    assert cost(mdl.inst, mdl.lib, sched)["total"] == pytest.approx(st["obj"])
    # the helper is a pure function of the instance
    inst_c = colocated_instance(inst)
    assert inst_c.validate() == [] and inst_c != inst and toy_instance() == inst


# ---------------------------------------------------------------------------
# dummy terminal arcs (q_res = 1 probe, workflow1_result.json: J = 206.5)
# ---------------------------------------------------------------------------
def test_q_res_one_probe_and_dummy_terminal():
    inst = toy_instance()
    inst.q_res = 1
    sched, st = solve(inst, build_arcs(inst))
    assert st["obj"] == pytest.approx(206.5)
    assert sum(sched.u.values()) == 2 and st["cost"]["C_dummy_terminal"] == 0
    # dummy arcs with a cheap penalty: serve everything, strand both bikes (2 x 50)
    lib_d = build_arcs(inst, dummy_terminal_cost=50.0)
    sched_d, st_d = solve(inst, lib_d)
    assert st_d["obj"] == pytest.approx(112.5)
    assert st_d["cost"]["C_dummy_terminal"] == pytest.approx(100.0)
    assert st_d["components"]["C_dummy_terminal"] == pytest.approx(100.0)
    assert sum(sched_d.u.values()) == 0
    assert any("dummy" in note for note in st_d["check"]["notes"])
    assert all(a.fac is None for a in sched_d.chosen_arcs(lib_d) if a.kind == "term")
    # an expensive penalty reproduces the written model
    sched_e, st_e = solve(inst, build_arcs(inst, dummy_terminal_cost=1000.0))
    assert st_e["obj"] == pytest.approx(206.5) and st_e["cost"]["C_dummy_terminal"] == 0


# ---------------------------------------------------------------------------
# MIP starts
# ---------------------------------------------------------------------------
def test_mip_start_documented_schedule_accepted(toy):
    inst, lib = toy
    doc = toy_documented_schedule(lib)
    sched, st = solve(inst, lib, mip_start=doc)
    ms = st["mip_start"]
    assert ms["given"] and ms["start_obj"] == pytest.approx(12.5) and ms["start_check_ok"]
    assert ms["verified"] is True and ms["verified_obj"] == pytest.approx(12.5)
    assert ms["verified_status"] == "OPTIMAL" and ms["accepted"] is True
    assert ms["first_incumbent_obj"] == pytest.approx(12.5)
    assert st["obj"] == pytest.approx(12.5)
    # the loader fills Start on every variable
    mdl = build_model(inst, lib, mip_start=doc, verify_start=False)
    assert mdl.mip_start_info["verified"] is None
    mdl.model.update()
    starts = mdl.model.getAttr("Start", mdl.model.getVars())
    assert all(s != ilp.GRB.UNDEFINED for s in starts)
    assert sum(starts[:len(lib)]) == len(doc.x[1]) + len(doc.x[2])


def test_mip_start_infeasible_schedule_rejected(toy):
    inst, lib = toy
    doc = toy_documented_schedule(lib)
    bad = Schedule(x=doc.x, u=doc.u, c={}, h=doc.h, z=doc.z)     # no charging: (18) fails
    sched, st = solve(inst, lib, mip_start=bad)
    ms = st["mip_start"]
    assert ms["start_check_ok"] is False and ms["start_violations"] >= 1
    assert ms["verified"] is False and ms["verified_status"] == "INFEASIBLE"
    assert ms["accepted"] is False
    assert st["obj"] == pytest.approx(12.5)                       # solve still succeeds


def test_mip_start_translated_to_colocated_library(toy):
    inst, lib = toy
    mdl = build_model(inst, lib, colocated=True, mip_start=toy_documented_schedule(lib))
    assert mdl.mip_start_info["verified"] is True
    sched, st = mdl.solve()
    assert st["obj"] == pytest.approx(12.5) and st["mip_start"]["accepted"]


# ---------------------------------------------------------------------------
# Battery_Swap p.7 instance (no orders): trivial optimum, documented start accepted
# ---------------------------------------------------------------------------
def test_battery_swap_p7_instance():
    inst = battery_swap_p7_instance()
    lib = build_arcs(inst)
    f = lib.find
    start = Schedule(
        x={1: _ids(f(1, "swap", ("J", 0, 0), fac="J"), *[f(1, "wait", ("J", t, 2)) for t in range(1, 4)],
                   f(1, "term", ("J", 4, 2), fac="J")),
           2: _ids(*[f(2, "wait", ("J", t, 0)) for t in range(0, 3)], f(2, "swap", ("J", 3, 0), fac="J"),
                   f(2, "term", ("J", 4, 2), fac="J"))},
        c={("J", 0, 1): 1, ("J", 1, 2): 1},
    )
    sched, st = solve(inst, lib, mip_start=start)
    assert st["status"] == "OPTIMAL" and st["obj"] == pytest.approx(0.0)
    assert st["mip_start"]["verified"] is True
    assert st["mip_start"]["verified_obj"] == pytest.approx(0.1)   # two charging steps
    assert sched.n[("J", 2, 0)] == 1 and check(inst, lib, sched)["ok"]
    assert sched.y == {"J": 1} and sched.B == {"J": 1} and sched.C == {"J": 1}
    # with rho = 1 the two swaps + two charges of the p.7 table are forced if both bikes
    # must leave with full batteries: force it through q_res = 2 (terminal needs q >= 2)
    inst2 = battery_swap_p7_instance()
    inst2.q_res = 2
    inst2.rho = 1.0
    sched2, st2 = solve(inst2, build_arcs(inst2))
    assert st2["status"] == "INFEASIBLE" and sched2 is None   # only one spare for two bikes
    inst3 = battery_swap_p7_instance()
    inst3.q_res = 2
    inst3.bikes = inst3.bikes[:1]
    inst3.reindex()
    sched3, st3 = solve(inst3, build_arcs(inst3))
    assert st3["obj"] == pytest.approx(0.0)                      # one swap, no charging needed
    assert [a.kind for a in sched3.path(1, build_arcs(inst3))].count("swap") == 1


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------
def test_library_instance_mismatch_rejected(toy):
    inst, lib = toy
    other = toy_instance()
    other.rho = 0.0
    with pytest.raises(ValueError):
        build_model(other, lib)


def test_consistency_error_is_raised_on_tampered_objective(toy):
    """If the Gurobi objective and evaluate.cost disagree, solve() must raise."""
    inst, lib = toy
    mdl = build_model(inst, lib)
    mdl.model.setObjective(mdl.objective + 1.0, ilp.GRB.MINIMIZE)    # constant shift
    with pytest.raises(ILPConsistencyError):
        mdl.solve()


def test_lexicographic_stage1_certification_flag(toy):
    """Reviewer (ilp) F7: a certified stage 1 sets lex_certified=True and no bound key."""
    inst, lib = toy
    _, st = solve(inst, lib, lexicographic=True)
    assert st["lex_certified"] is True and "lex_min_unserved_bound" not in st
    assert st["lex_stage1_status"] == "OPTIMAL"


def test_solve_check_uses_effective_switches(toy):
    """Reviewer (ilp) F5: the checker run inside solve sees the keyword switches."""
    inst, lib = toy
    sched, st = solve(inst, lib, no_transfers=True, zeta=2 / 3)
    assert st["obj"] == pytest.approx(106.0) and st["check"]["ok"]
    assert st["switches"]["no_transfers"] is True and st["switches"]["zeta"] == pytest.approx(2 / 3)
    from ebike_swap_sim import check as _check
    assert _check(inst, lib, sched, switches=st["switches"])["ok"]
    assert "(33)" in _check(inst, lib, sched, switches={"zeta": 1.0})["families"]
