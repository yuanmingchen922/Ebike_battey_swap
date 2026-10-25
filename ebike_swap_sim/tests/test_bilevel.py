"""Bi-level siting (``ebike_swap_sim/sites_nyc.py``, ``ebike_swap_sim/bilevel.py``,
``experiments/e9_bilevel_siting.py``): toy-scale checks of the design's validation E9.1
(integrated stochastic ILP == exhaustive bi-level enumeration), the greedy, the cache, the
budget and demand invariants, the role semantics, the candidate rules and the stressed family."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import Schedule, build_arcs, check  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from experiments import common as C  # noqa: E402

pytest.importorskip("gurobipy")
from ebike_swap_sim import bilevel as BL  # noqa: E402

TOY_MENU = {"S": [(0, 0), (1, 0), (2, 0)], "C": [(0, 1), (1, 1), (2, 1)],
            "SC": [(B, Cc) for B in (0, 1, 2) for Cc in (0, 1)]}
TOY_GRID = BL.option_grid(TOY_MENU)          # every integer size of TOY_SPEC (K 2, Cbar 1): 12 options
BUDGET = 250.0


@pytest.fixture(scope="module")
def toy_scenarios():
    return [S.toy_base_instance(0), S.toy_base_instance(1)]


@pytest.fixture(scope="module")
def evaluator(toy_scenarios):
    return BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, time_limit=30.0, threads=1)


@pytest.fixture(scope="module")
def exhaustive_result(evaluator):
    return BL.exhaustive(evaluator, evaluator.candidates, TOY_GRID, BUDGET, (1, 2), bound=evaluator.superset_bound())


# ---------------------------------------------------------------------------
# layouts, instances, libraries
# ---------------------------------------------------------------------------
def test_layout_dataclass_key_json_and_costs():
    lay = BL.Layout.of([("T2", "S", 1, 0), ("T1", "SC", 2, 1)])
    assert lay.key() == "T1:SC:B2:C1|T2:S:B1:C0" and str(lay) == lay.key()
    assert BL.Layout.from_key(lay.key()) == lay and BL.Layout.from_json(json.dumps(lay.to_json())) == lay
    assert lay.locations() == ("T1", "T2") and lay.has_swap() and lay.has_charge() and lay.n_role("S") == 1
    sp = S.TOY_SPEC
    assert lay.investment(sp) == pytest.approx(2 * sp.Fhat + 3 * sp.bhat + 1 * sp.chat)
    assert lay.allocated_cost(sp) == pytest.approx(2 * sp.F + 3 * sp.bB + 1 * sp.bC)
    assert lay.drop("T2").key() == "T1:SC:B2:C1" and lay.replace("T2", ("T2", "C", 0, 1)).n_role("C") == 1
    with pytest.raises(ValueError):
        BL.Layout.of([("T1", "S", 1, 0), ("T1", "C", 0, 1)])          # one role per location [U1]
    with pytest.raises(ValueError):
        BL.Layout.of([("T1", "S", 1, 2)])                             # C_j = 0 off C (8)
    assert BL.Layout().key() == "empty" and BL.Layout().n_open == 0


def test_layout_instance_roles_demand_and_subset_library(toy_scenarios):
    base = toy_scenarios[0]
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "C", 1, 1)])
    inst = S.layout_instance(base, lay, S.TOY_SPEC)
    assert inst.validate() == [] and inst.meta["layout_key"] == lay.key()
    assert {f.id for f in inst.facilities} == {"T1:SC", "T2:C"}
    hub = inst.facility("T2:C")
    assert not hub.swap and hub.charge and hub.C == 1 and hub.R_end == 0 and hub.F == S.TOY_SPEC.F_hub
    assert inst.services and all({s.o_fac, s.d_fac} == {"T1:SC", "T2:C"} for s in inst.services)
    # demand identical across layouts of a seed (include_bike_nodes: bikes start at the depots)
    other = S.layout_instance(base, [("T2", "S", 2, 0)], S.TOY_SPEC)
    assert C.demand_key(inst) == C.demand_key(other) == C.demand_key(base)
    assert C.demand_md5(inst) == C.demand_md5(base)
    # role semantics in the arc library: the hub has no swap / terminal arcs, the swap site has
    lib = build_arcs(inst, strict=False, **S.siting_pruning(inst))
    assert lib.swap_arcs("T2:C") == [] and lib.swap_arcs("T1:SC")
    assert {a.fac for a in lib.terminal_arcs()} == {"T1:SC"}
    # a swap-only site cannot charge: evaluate.check flags c at an S-role facility under (20)
    inst_s = S.layout_instance(base, [("T2", "S", 1, 0), ("T1", "SC", 1, 1)], S.TOY_SPEC)
    lib_s = build_arcs(inst_s, strict=False)
    from ebike_swap_sim import baseline as bl
    sched, _ = bl.run_baseline(inst_s, lib_s)
    bad = Schedule(x=sched.x, u=sched.u, c={**sched.c, ("T2:S", 0, 0): 1}, h=sched.h, z=sched.z)
    rep = check(inst_s, lib_s, bad)
    assert "(20)" in C.family_counts(rep) or "domain" in C.family_counts(rep)
    # subset_library == build_arcs on the layout instance (arc by arc, same ids)
    t_inst = S.all_candidates_instance(base, S.TOY_SPEC)
    assert len(t_inst.facilities) == 6 and all(f.y is None and f.B is None for f in t_inst.facilities)
    t_lib = build_arcs(t_inst, strict=False, **S.siting_pruning(t_inst))
    sub = S.subset_library(t_lib, inst, strict=False)
    key = lambda a: (a.id, a.k, a.kind, a.src, a.dst, a.l, a.u, a.d_km, a.g, a.order, a.fac, a.theta)  # noqa: E731
    assert [key(a) for a in sub.arcs] == [key(a) for a in lib.arcs]
    assert sub.infeasible_bikes == lib.infeasible_bikes == []
    with pytest.raises(ValueError):
        S.layout_instance(base, [("T9", "S", 1, 0)], S.TOY_SPEC)


def test_portable_schedule_round_trip(toy_scenarios):
    base = toy_scenarios[0]
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "S", 1, 0)])
    inst = S.layout_instance(base, lay, S.TOY_SPEC)
    lib = build_arcs(inst, strict=False)
    from ebike_swap_sim import baseline as bl
    sched, _ = bl.run_baseline(inst, lib)
    port = json.loads(json.dumps(BL.portable_schedule(sched, inst, lib)))
    back = BL.materialise_schedule(port, inst, lib)
    assert back is not None and {k: sorted(v) for k, v in back.x.items()} == {k: sorted(v) for k, v in sched.x.items()}
    assert back.u == sched.u and back.c == sched.c
    # the same schedule does not fit a layout without the swap site it uses
    other = S.layout_instance(base, [("T2", "S", 1, 0)], S.TOY_SPEC)
    other_lib = build_arcs(other, strict=False)
    if any(a.kind == "swap" for a in sched.chosen_arcs(lib)):
        assert BL.materialise_schedule(port, other, other_lib) is None


# ---------------------------------------------------------------------------
# E9.1 at toy scale: integrated == exhaustive; greedy; budget; cache
# ---------------------------------------------------------------------------
def test_integrated_equals_exhaustive_toy(evaluator, exhaustive_result):
    ex = exhaustive_result
    assert ex["coverage"]["full_coverage"] and ex["best_layout"] is not None
    assert all(r["investment"] <= BUDGET + 1e-9 for r in ex["rows"])                 # [U2] respected
    assert ex["coverage"]["n_layouts"] == len(BL.enumerate_layouts(evaluator.candidates, TOY_GRID, BUDGET,
                                                                   S.TOY_SPEC, (1, 2)))
    assert ex["coverage"]["infeasible"] >= 1                                          # C-only / empty swap sites
    ig = BL.integrated_stochastic_ilp(evaluator, evaluator.candidates, BUDGET, time_limit=120.0, threads=1,
                                      mip_start_layout=ex["best_layout"])
    assert ig["status"] == "OPTIMAL" and ig["gap"] == pytest.approx(0.0, abs=1e-9)
    assert ig["layout"].investment(S.TOY_SPEC) <= BUDGET + 1e-9
    # agreement of the optimal values (objectives coincide: no planner-only rows)
    assert abs(ig["obj"] - ex["best_value"]) <= 1e-6 * max(1.0, abs(ig["obj"]))
    assert ig["V_model"] == pytest.approx(ig["obj"], abs=1e-6) and ig["certified_ok"]
    assert ig["V_certified"] == pytest.approx(ig["obj"], abs=1e-6)
    # the integrated layout, priced by the lower-level evaluator, has the same value
    assert evaluator.value(ig["layout"]) == pytest.approx(ig["obj"], abs=1e-6)
    assert ig["mip_start"]["given"] and ig["mip_start"]["accepted"]
    assert ig["mip_start"]["start_obj"] == pytest.approx(ex["best_value"], abs=1e-6)
    assert all(r["check_ok"] and r["check_ok_layout"] for r in ig["per_scenario"])


def test_greedy_finds_toy_optimum(evaluator, exhaustive_result):
    g = BL.greedy_local_search(evaluator, evaluator.candidates, BUDGET, size_menu=TOY_MENU,
                               budget_levels=[130.0, BUDGET], screen=False)
    assert g["per_budget"][BUDGET]["value"] == pytest.approx(exhaustive_result["best_value"], abs=1e-6)
    assert g["per_budget"][BUDGET]["layout"].investment(S.TOY_SPEC) <= BUDGET + 1e-9
    ex130 = BL.exhaustive(evaluator, evaluator.candidates, TOY_GRID, 130.0, (1, 2))
    assert g["per_budget"][130.0]["value"] == pytest.approx(ex130["best_value"], abs=1e-6)
    assert g["per_budget"][130.0]["layout"].investment(S.TOY_SPEC) <= 130.0 + 1e-9
    assert g["frontier"] and g["best_singleton"] is not None


def test_cache_hit_on_repeat(toy_scenarios, tmp_path):
    cache = str(tmp_path / "cache")
    ev = BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, time_limit=30.0, threads=1, cache_dir=cache)
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "S", 1, 0)])
    r1 = ev.evaluate(lay)
    assert r1["complete"] and r1["n_solves"] == 2 and r1["n_cache_hits"] == 0 and ev.n_solves == 2
    r2 = ev.evaluate(lay)
    assert r2["n_cache_hits"] == 2 and r2["n_solves"] == 0 and r2["V"] == pytest.approx(r1["V"])
    rows = C.load_jsonl(os.path.join(cache, "index.jsonl"))
    assert len(rows) == 2 and all(os.path.exists(r["schedule_path"]) for r in rows)
    ev2 = BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, time_limit=30.0, threads=1, cache_dir=cache)
    r3 = ev2.evaluate(lay)
    assert r3["n_cache_hits"] == 2 and ev2.n_solves == 0 and r3["V"] == pytest.approx(r1["V"])
    assert all(r["cache_hit"] for r in r3["rows"])
    # a different policy / layout is a different key
    rb = ev2.evaluate(lay, "baseline")
    assert rb["n_cache_hits"] == 0 and rb["V"] >= r1["V"] - 1e-9
    assert ev2.cache_key(lay, 0, "ilp") != ev2.cache_key(lay.drop("T2"), 0, "ilp")


def test_deck_cross_and_access(evaluator, toy_scenarios):
    d = BL.deck_heuristic(evaluator, evaluator.candidates, BUDGET, iterations=3)
    assert d["layout"] is not None and d["layout"].investment(S.TOY_SPEC) <= BUDGET + 1e-9 and d["k"] == 2
    cr = BL.cross_evaluate(evaluator, d["layout"])
    assert cr["ilp"]["V"] <= cr["baseline"]["V"] + 1e-9 and cr["gap_vs_baseline_pct"] >= 0.0
    # access sets [U4] on the toy (zone codes attached to the orders' customer nodes)
    for inst in toy_scenarios:
        inst.meta["orders"] = [{"id": o.id, "zone_code": "Z1" if o.d <= 2 else "Z2"} for o in inst.orders]
    acc = BL.access_sets(evaluator.candidates, toy_scenarios, 1)
    assert acc["Z2"] == ["T2"] and set(acc["Z1"]) <= {"T1", "T2"}
    assert BL.layout_covers(BL.Layout.of([("T2", "SC", 1, 1)]), acc)
    assert not BL.layout_covers(BL.Layout.of([("T1", "SC", 1, 1), ("T2", "C", 0, 1)]), acc)
    ig = BL.integrated_stochastic_ilp(evaluator, evaluator.candidates, 130.0, time_limit=60.0, threads=1, access=acc)
    assert ig["status"] == "OPTIMAL" and BL.layout_covers(ig["layout"], acc)
    dist = BL.zone_site_distances(ig["layout"], evaluator.candidates, toy_scenarios)
    assert all(z["min"] <= 1 for z in dist["per_zone"].values()) and dist["max_blocks"] <= 3
    for inst in toy_scenarios:
        inst.meta.pop("orders", None)


# ---------------------------------------------------------------------------
# E9 relaunch regressions (DECISIONS "E9 relaunch decisions"): the first-attempt failures
# ---------------------------------------------------------------------------
def _per_budget_values(g):
    return {b: (None if r["layout"] is None else r["value"]) for b, r in g["per_budget"].items()}


def test_role_set_with_S_is_at_least_as_good_as_SC_only(evaluator):
    """(1) of the relaunch: a role set that allows S must find at least the SC_only optimum."""
    levels = [130.0, BUDGET]
    out = {}
    for name, roles in (("SC_only", ("SC",)), ("S_SC", ("S", "SC")), ("S_C_SC", ("S", "C", "SC"))):
        g = BL.greedy_local_search(evaluator, evaluator.candidates, BUDGET, size_menu=TOY_MENU, roles=roles,
                                   budget_levels=levels, screen=False, s_needs_charge=True)
        out[name] = _per_budget_values(g)
        assert all(r["status"] == "OK" and r["layout"] is not None for r in g["per_budget"].values()), out
        assert g["wall_exhausted"] is False and g["class_counts"].get("OK", 0) >= 1
    for b in levels:
        assert out["S_SC"][b] <= out["SC_only"][b] + 1e-6
        assert out["S_C_SC"][b] <= out["SC_only"][b] + 1e-6


def test_greedy_start_is_the_best_singleton_by_V(evaluator):
    """(2) of the relaunch: the start is the best singleton by lower-level V, not by ratio or screen."""
    g = BL.greedy_local_search(evaluator, evaluator.candidates, BUDGET, size_menu=TOY_MENU, budget_levels=[130.0, BUDGET],
                               screen=False, s_needs_charge=True)
    singles = [r for r in g["history"] if r["step"] == "singleton"]
    assert singles and all(r["status"] in ("OK", BL.LOW_SERVICE) or r["V"] is None for r in singles)
    usable = [r for r in singles if r["usable"]]
    best = min(usable, key=lambda r: (r["V"], r["layout_key"]))
    start = next(r for r in g["history"] if r["step"] == "start")
    assert start["layout_key"] == best["layout_key"] and start["V"] == pytest.approx(best["V"])
    assert g["best_singleton"][0] == best["layout_key"] and g["best_singleton"][1] == pytest.approx(best["V"])
    assert all(r["served_share"] >= 0.5 - 1e-9 for r in usable)
    # every priced singleton is admissible (no C-only, no S without a charge-capable object) and the
    # best singleton coincides with the exhaustive enumeration of singletons under the same rule
    for r in singles:
        assert S.layout_admissible(BL.Layout.from_json(r["layout"]), s_needs_charge=True)
    ex1 = BL.exhaustive(evaluator, evaluator.candidates, TOY_GRID, BUDGET, (1,), s_needs_charge=True)
    assert ex1["best_value"] == pytest.approx(best["V"], abs=1e-6)
    # the first budget level is served by the best singleton when nothing cheaper beats it
    assert g["per_budget"][130.0]["value"] <= best["V"] + 1e-6


def test_access_reported_not_enforced(evaluator, toy_scenarios):
    """(1b) of the relaunch: with the access row the greedy still finds a layout; zones no
    affordable layout can cover are reported as ``uncovered_zones``, not turned into 'no
    feasible layout'; ``enforce`` reproduces the first-attempt failure on a one-site budget."""
    acc = {"Z1": ["T1"], "Z2": ["T2"]}          # no single candidate covers both zones
    g = BL.greedy_local_search(evaluator, evaluator.candidates, BUDGET, size_menu=TOY_MENU, budget_levels=[130.0, BUDGET],
                               screen=False, s_needs_charge=True, access=acc, access_mode="repair")
    one = g["per_budget"][130.0]
    assert one["status"] == "OK" and one["layout"] is not None and len(one["uncovered_zones"]) == 1
    assert one["uncovered_zones"] == BL.uncovered_zones(one["layout"], acc)
    two = g["per_budget"][BUDGET]
    assert two["status"] == "OK" and two["layout"] is not None
    assert two["uncovered_zones"] == BL.uncovered_zones(two["layout"], acc)
    if two["uncovered_zones"] == []:
        assert BL.layout_covers(two["layout"], acc)
    g_rep = BL.greedy_local_search(evaluator, evaluator.candidates, 130.0, size_menu=TOY_MENU, screen=False,
                                   s_needs_charge=True, access=acc, access_mode="report")
    assert g_rep["per_budget"][130.0]["status"] == "OK" and len(g_rep["per_budget"][130.0]["uncovered_zones"]) == 1
    g_enf = BL.greedy_local_search(evaluator, evaluator.candidates, 130.0, size_menu=TOY_MENU, screen=False,
                                   s_needs_charge=True, access=acc, access_mode="enforce")
    assert g_enf["per_budget"][130.0]["status"] == BL.NO_FEASIBLE_LAYOUT
    # an uncoverable zone (empty access set) is always reported, never blocks the search
    acc2 = {"Z1": ["T1", "T2"], "Z9": []}
    g2 = BL.greedy_local_search(evaluator, evaluator.candidates, 130.0, size_menu=TOY_MENU, screen=False,
                                s_needs_charge=True, access=acc2)
    assert g2["per_budget"][130.0]["status"] == "OK" and g2["per_budget"][130.0]["uncovered_zones"] == ["Z9"]


class _ExhaustedWall:
    def solve_limit(self, time_limit):
        return None


def test_wall_budget_exhaustion_is_not_infeasibility(toy_scenarios):
    """(1a) of the relaunch: SKIPPED_BUDGET prices must surface as 'wall budget exhausted'."""
    ev = BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, time_limit=30.0, threads=1, wall=_ExhaustedWall())
    out = ev.evaluate(BL.Layout.of([("T1", "SC", 1, 1)]))
    assert out["status"] == BL.SKIPPED_BUDGET and out["V"] is None and out["feasible"] is None
    g = BL.greedy_local_search(ev, ev.candidates, BUDGET, size_menu=TOY_MENU, budget_levels=[130.0, BUDGET], screen=False)
    assert g["wall_exhausted"] is True
    for r in g["per_budget"].values():
        assert r["status"] == BL.WALL_EXHAUSTED and r["layout"] is None
    assert g["class_counts"] == {BL.SKIPPED_BUDGET: 1}          # stopped after the first skipped price


def test_lower_level_exception_is_recorded_as_error(toy_scenarios, monkeypatch):
    """(1) of the relaunch: an exception inside the lower level is an ERROR row with the
    message (recorded, not cached), never a silent 'infeasible'."""
    ev = BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, time_limit=30.0, threads=1)
    lay = BL.Layout.of([("T1", "SC", 1, 1)])

    def boom(*args, **kwargs):
        raise RuntimeError("synthetic lower-level failure")

    monkeypatch.setattr(ev, "_solve_scenario", boom)
    out = ev.evaluate(lay)
    assert out["status"] == BL.ERROR and out["V"] is None and out["feasible"] is None
    assert "synthetic lower-level failure" in out["error"]
    assert ev.n_errors == 1 and ev.stats()["n_errors"] == 1
    assert ev.new_rows and ev.new_rows[-1]["status"] == BL.ERROR and "RuntimeError" in ev.new_rows[-1]["error"]
    assert ev.cache_key(lay, 0, "ilp") not in ev.cache                       # not cached
    g = BL.greedy_local_search(ev, ev.candidates, 130.0, size_menu=TOY_MENU, screen=False, local_search=False)
    assert g["per_budget"][130.0]["status"] == BL.NO_FEASIBLE_LAYOUT
    assert g["per_budget"][130.0]["reasons"] == {BL.ERROR: g["class_counts"][BL.ERROR]}
    assert all(r["status"] == BL.ERROR and "synthetic" in r["error"] for r in g["history"] if r["step"] == "singleton")
    monkeypatch.undo()
    assert ev.evaluate(lay)["status"] == "OK"                                 # recovers after the fault


def test_reposition_modes_and_admissibility(toy_scenarios, evaluator):
    """(4) of the relaunch: the per-layout 'open_sites' library prices the toy identically
    (no pruning there), is a different cache key, and the integrated model honours the rule
    'swap-only sites only next to a charge-capable object'."""
    ev_open = BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, time_limit=30.0, threads=1, reposition="open_sites")
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "S", 1, 0)])
    assert ev_open.value(lay) == pytest.approx(evaluator.value(lay), abs=1e-6)
    assert ev_open.cache_key(lay, 0, "ilp") != evaluator.cache_key(lay, 0, "ilp")
    assert ev_open.stats()["reposition"] == "open_sites"
    with pytest.raises(ValueError):
        BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, reposition="everywhere")
    # structural rule
    assert S.layout_admissible([("T1", "SC", 1, 1), ("T2", "S", 1, 0)], s_needs_charge=True)
    assert not S.layout_admissible([("T2", "S", 1, 0)], s_needs_charge=True)
    assert S.layout_admissible([("T2", "S", 1, 0)], s_needs_charge=False)
    assert not S.layout_admissible([("T1", "C", 0, 1)])
    lays = BL.enumerate_layouts(evaluator.candidates, TOY_GRID, BUDGET, S.TOY_SPEC, (1, 2), s_needs_charge=True)
    assert lays and all(S.layout_admissible(l, s_needs_charge=True) for l in lays)
    assert len(lays) < len(BL.enumerate_layouts(evaluator.candidates, TOY_GRID, BUDGET, S.TOY_SPEC, (1, 2)))
    ex = BL.exhaustive(evaluator, evaluator.candidates, TOY_GRID, BUDGET, (1, 2), s_needs_charge=True)
    ig = BL.integrated_stochastic_ilp(evaluator, evaluator.candidates, BUDGET, time_limit=120.0, threads=1,
                                      s_needs_charge=True, mip_start_layout=ex["best_layout"])
    assert ig["status"] == "OPTIMAL" and ig["s_needs_charge"] and S.layout_admissible(ig["layout"], s_needs_charge=True)
    assert abs(ig["obj"] - ex["best_value"]) <= 1e-6 * max(1.0, abs(ig["obj"]))
    # certification of the integrated schedules uses the template convention under open_sites too
    ig2 = BL.integrated_stochastic_ilp(ev_open, ev_open.candidates, BUDGET, time_limit=120.0, threads=1, s_needs_charge=True)
    assert ig2["status"] == "OPTIMAL" and ig2["certified_ok"] and ig2["obj"] == pytest.approx(ig["obj"], abs=1e-6)


# ---------------------------------------------------------------------------
# NYC candidates and the stressed family
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "..", "data", "raw", "dohmh_restaurants.csv")),
                    reason="DOHMH data not present")
def test_candidate_sites_dedup_and_stressed_base():
    from ebike_swap_sim import data_nyc as dn
    cands = S.candidate_sites()
    assert len(cands) == 12 and len({c.node for c in cands}) == 12
    assert [c.id for c in cands] == [f"L{i:02d}" for i in range(1, 13)]
    assert cands[0].node == (13, 14) and "Penn Station (7th Ave / W 32nd)" in cands[0].merged_labels
    assert cands[0].grid_connected and cands[1].source == "busiest" and not cands[1].grid_connected
    assert sum(c.source == "landmark" for c in cands) == 3 and sum(c.source == "zone" for c in cands) == 3
    assert all(S.manhattan_blocks(a.node, b.node) >= 2 for i, a in enumerate(cands) for b in cands[i + 1:])
    back = S.candidates_from_records(json.loads(json.dumps(S.candidates_to_records(cands))))
    assert [(c.id, c.node) for c in back] == [(c.id, c.node) for c in cands]
    # merge rule on a custom landmark one block from busiest cell 1 (more restaurants wins, label kept)
    lat, lon = dn.DEFAULT_BOX.node_latlon((13, 15))
    few = S.candidate_sites(n_busiest=2, landmarks={"near L01": (lat, lon)}, n_zones=0)
    assert len(few) == 2 and few[0].merged_labels == ["near L01"]
    # stressed base: q0 in {2, 3, 4}, 8 bikes / 48 orders, depots = three busiest cells, no facilities
    base = S.make_base_instance(0, cands)
    assert base.meta["family"] == "nyc4h_stress" and base.facilities == [] and base.services == []
    assert len(base.bikes) == 8 and len(base.orders) == 48 and base.H == 48
    assert all(b.q0 in (2, 3, 4) for b in base.bikes)
    assert [b.v0 for b in base.bikes[:3]] == [cands[0].node, cands[1].node, cands[2].node]
    assert all(c.node in base.nodes for c in cands)
    # byte-identical demand across candidate subsets (sites never touch the random stream)
    base3 = S.make_base_instance(0, cands[:3])
    assert C.demand_key(base3) == C.demand_key(base)
    fam = C.make_instance("nyc4h_stress", seed=0)
    assert [b.q0 for b in fam.bikes] == [b.q0 for b in base.bikes] and len(fam.facilities) == 3
    assert fam.facilities[0].B == 1 and fam.facilities[0].C == 1 and fam.facilities[0].P_kw == 1.4
    assert fam.P_grid["sites"] == [4.0] * 48
    # a layout instance of the stressed base validates, keeps the demand and prunes to candidates + depots
    lay = S.layout_instance(base, [("L01", "SC", 1, 1), ("L04", "C", 0, 1)], S.spec_from_instance(base))
    assert lay.validate() == [] and C.demand_md5(lay) == C.demand_md5(base) and len(lay.services) > 0
    pr = S.siting_pruning(lay)
    assert pr["reposition_targets"] == {c.node for c in cands} and pr["tau_max"] == 4
    # the per-layout convention: open sites + depots only (E8 convention), a subset of the above
    pr_open = S.siting_pruning(lay, targets="open_sites")
    assert pr_open["reposition_targets"] == {cands[0].node, cands[3].node, cands[1].node, cands[2].node}
    assert pr_open["reposition_targets"] < pr["reposition_targets"]
    with pytest.raises(ValueError):
        S.siting_pruning(lay, targets="everywhere")


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "..", "data", "raw", "dohmh_restaurants.csv")),
                    reason="DOHMH data not present")
def test_stress2_family_is_stressed_but_sane():
    """(3) of the relaunch: ``nyc4h_stress2`` = 6 bikes / 36 orders, ``q0 ~ U{3..6}``, 2.8 kW
    sites, 4 kW grid; the size menu of the relaunch; a sensible single SC site serves >= 70 %
    of the orders under the baseline policy on seed 0."""
    cands = S.candidate_sites()
    base = S.make_base_instance(0, cands, family="nyc4h_stress2")
    assert base.meta["family"] == "nyc4h_stress2" and len(base.bikes) == 6 and len(base.orders) == 36 and base.H == 48
    assert all(3 <= b.q0 <= 6 for b in base.bikes) and base.facilities == []
    for seed in range(1, 6):
        assert all(3 <= b.q0 <= 6 for b in S.make_base_instance(seed, cands, family="nyc4h_stress2").bikes)
    spec = S.spec_from_instance(base)
    assert spec.P_kw == pytest.approx(2.8) and spec.grid_kw == pytest.approx(4.0) and spec.Cbar == 4
    assert S.SIZE_MENUS["nyc4h_stress2"]["C"] == [(0, 2), (0, 4)] and S.SIZE_MENUS["nyc4h_stress2"]["S"] == [(1, 0), (2, 0), (3, 0)]
    assert S.SIZE_MENUS["nyc4h_stress2"]["SC"] == [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)]
    assert C.make_instance("nyc4h_stress2", seed=0).meta["family"] == "nyc4h_stress2"
    with pytest.raises(ValueError):
        S.make_base_instance(0, cands, family="nyc4h")
    inst = S.layout_instance(base, [("L03", "SC", 3, 2)], spec)
    lib = build_arcs(inst, strict=False, **S.siting_pruning(inst, targets="open_sites"))
    assert lib.infeasible_bikes == [] and len(lib) < 1_000_000
    rec = C.run_baseline_case(inst, lib)
    assert rec["metrics"]["served_share"] >= 0.70


# ---------------------------------------------------------------------------
# experiment script modes
# ---------------------------------------------------------------------------
def _run(*args: str, timeout: float = 900.0) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=ROOT, MPLBACKEND="Agg")
    return subprocess.run([sys.executable, os.path.join(ROOT, "experiments", "e9_bilevel_siting.py"), *args],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)


@pytest.mark.parametrize("sub", ["--validate", "--sweep", "--roles", "--deck", "--cross", "--access"])
def test_e9_smoke_modes(sub, tmp_path):
    out = str(tmp_path / "e9")
    r = _run(sub, "--smoke", "--out-root", out)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    sub_dir = os.path.join(out, sub.lstrip("-"))
    assert os.path.exists(os.path.join(sub_dir, "records.jsonl"))
    assert os.path.exists(os.path.join(sub_dir, "results.csv"))
    assert os.path.exists(os.path.join(sub_dir, "RESULTS.md"))
    if sub == "--validate":
        agree = json.load(open(os.path.join(sub_dir, "agreement.json"), encoding="utf-8"))
        assert all(a["agree"] for a in agree["budgets"])


def test_e9_dry_run(tmp_path):
    r = _run("--validate", "--dry-run", "--out-root", str(tmp_path / "e9"), timeout=300.0)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    assert "layouts" in r.stdout


# ---------------------------------------------------------------------------
# Round 5 (notes/reading_to_model.md): O1 aggregated integrated model, M4 follower E,
# A4 baselines / levers, M6 Manhattan region (toy scale unless noted)
# ---------------------------------------------------------------------------
def test_integrated_aggregated_equals_per_bike(evaluator, exhaustive_result):
    """O1: the integrated model with the aggregated flow (feature-detected default) has the same
    optimum as the per-bike sub-models and as the exhaustive enumeration."""
    if not BL.aggregate_available():
        pytest.skip("aggregate.py / ilp.build_submodel not available")
    ig_p = BL.integrated_stochastic_ilp(evaluator, evaluator.candidates, BUDGET, time_limit=120.0, threads=1, aggregate=False)
    ig_a = BL.integrated_stochastic_ilp(evaluator, evaluator.candidates, BUDGET, time_limit=120.0, threads=1)
    assert ig_a["aggregate"] is True and ig_p["aggregate"] is False
    assert ig_a["status"] == ig_p["status"] == "OPTIMAL"
    assert ig_a["obj"] == pytest.approx(ig_p["obj"], abs=1e-6) == pytest.approx(exhaustive_result["best_value"], abs=1e-6)
    assert ig_a["n_vars"] < ig_p["n_vars"] and ig_a["certified_ok"] and ig_a["V_certified"] == pytest.approx(ig_a["obj"], abs=1e-6)
    ig_s = BL.integrated_stochastic_ilp(evaluator, evaluator.candidates, BUDGET, time_limit=120.0, threads=1,
                                        mip_start_layout=exhaustive_result["best_layout"])
    assert ig_s["mip_start"]["accepted"] and ig_s["obj"] == pytest.approx(ig_a["obj"], abs=1e-6)


def test_evaluator_aggregated_lower_level_matches(toy_scenarios, evaluator):
    """O1 in the evaluator: the aggregated lower-level ILP prices a layout like the per-bike one
    (equivalent formulation) and is a different cache key."""
    if not BL.aggregate_available():
        pytest.skip("aggregate.py / ilp.build_submodel not available")
    ev_a = BL.LowerLevelEvaluator(toy_scenarios, S.TOY_SPEC, time_limit=30.0, threads=1, aggregate=True)
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "S", 1, 0)])
    out = ev_a.evaluate(lay)
    assert out["V"] == pytest.approx(evaluator.value(lay), abs=1e-6)
    assert all(r.get("formulation") == "aggregated" for r in out["rows"])
    assert ev_a.cache_key(lay, 0, "ilp") != evaluator.cache_key(lay, 0, "ilp")
    assert ev_a.cache_key(lay, 0, "baseline") == evaluator.cache_key(lay, 0, "baseline")


def test_selfish_follower_cross_evaluate(evaluator):
    """M4: follower E (r5_selfish equilibrium) is a lower-level policy; cross_evaluate prices
    every follower and reports the price of decentralisation."""
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "S", 1, 0)])
    cr = BL.cross_evaluate(evaluator, lay)
    assert set(BL.POLICIES) <= set(cr)
    vi, vs = cr["ilp"]["V"], cr["selfish"]["V"]
    assert vs >= vi - 1e-9 and cr["price_of_decentralisation"] == pytest.approx(vs / vi)
    row = cr["selfish"]["rows"][0]
    assert row["status"] == "POLICY" and row["policy"] == "selfish" and row["equilibrium"]["iterations"] >= 1
    assert row["ok_modulo_report_only"]
    assert evaluator.cache_key(lay, 0, "selfish") != evaluator.cache_key(lay, 0, "baseline")
    # the equilibrium schedule equals a direct run of baseline.run_selfish_equilibrium
    from ebike_swap_sim import baseline as bl
    from ebike_swap_sim.evaluate import cost
    inst, lib = evaluator.layout_pair(lay, 0)
    sched, _flags, _info = bl.run_selfish_equilibrium(inst, lib, {})
    assert cost(inst, lib, sched)["total"] == pytest.approx(row["total"], abs=1e-9)
    with pytest.raises(ValueError):
        evaluator.evaluate(lay, "nobody")


def test_policy_aware_greedy(evaluator):
    """M4: the greedy with a policy as the lower level returns layouts priced by that policy."""
    for pol in ("selfish", "baseline"):
        g = BL.greedy_local_search(evaluator, evaluator.candidates, BUDGET, size_menu=TOY_MENU,
                                   budget_levels=[130.0, BUDGET], screen=False, min_served_share=0.0, policy=pol)
        assert g["policy"] == pol
        for b, r in g["per_budget"].items():
            assert r["status"] == "OK" and r["layout"] is not None and r["layout"].investment(S.TOY_SPEC) <= b + 1e-9
            assert r["value"] == pytest.approx(evaluator.value(r["layout"], pol), abs=1e-9)
    with pytest.raises(ValueError):
        BL.greedy_local_search(evaluator, evaluator.candidates, BUDGET, size_menu=TOY_MENU, policy="nobody")


def test_compliance_sweep_extremes(evaluator):
    """M4 compliance sweep: alpha_c = 1 with the plan's station layer reproduces the ILP value;
    alpha_c = 0 with the policy station layer equals the r5_selfish rule run directly."""
    from ebike_swap_sim import baseline as bl
    from ebike_swap_sim.evaluate import cost
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "S", 1, 0)])
    cs = BL.compliance_sweep(evaluator, lay, alphas=(0.0, 0.5, 1.0), seeds=(0, 1))
    summ = {r["alpha_c"]: r for r in cs["summary"]}
    assert summ[1.0]["complete"] and summ[1.0]["V"] == pytest.approx(evaluator.value(lay), abs=1e-6)
    assert all(r["check_ok"] or set(r["families"]) <= {"(9)", "(17)", "(18)"} for r in cs["rows"])
    cs0 = BL.compliance_sweep(evaluator, lay, alphas=(0.0,), seeds=(0,), station_plan="policy")
    direct = 0.0
    for s in range(evaluator.n_scenarios):
        inst, lib = evaluator.layout_pair(lay, s)
        sched, _ = bl.run_baseline(inst, lib, bl.baseline_variant_params("r5_selfish"))
        c = cost(inst, lib, sched)
        direct += evaluator.p[s] * (c["total"] - c["C_setup"])
    assert cs0["summary"][0]["V"] == pytest.approx(lay.allocated_cost(S.TOY_SPEC) + direct, abs=1e-6)


def test_variants_and_lever_table(evaluator, toy_scenarios):
    """A4 (iii): lever data (M_j, extra shuttle, grid factor) and the lever table."""
    from ebike_swap_sim.costs import position_cost_per_window
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T2", "S", 1, 0)])
    inst = S.layout_instance(toy_scenarios[0], lay, S.TOY_SPEC)
    n_svc, grid = len(inst.services), dict(inst.P_grid)
    BL.apply_variant(inst, {"M": {"T2": 3}, "grid_factor": 1.1, "extra_shuttle": True}, S.TOY_SPEC)
    assert inst.facility("T2:S").M == 3 and inst.facility("T1:SC").M == S.TOY_SPEC.M
    assert all(a == pytest.approx(1.1 * b) for g in grid for a, b in zip(inst.P_grid[g], grid[g]))
    assert len(inst.services) > n_svc and inst.validate() == [] and inst.meta["variant"]["grid_factor"] == 1.1
    with pytest.raises(ValueError):
        BL.apply_variant(inst, {"bogus": 1})
    ev_v = evaluator.derive(variant={"grid_factor": 1.1})
    assert ev_v.cache_key(lay, 0, "ilp") != evaluator.cache_key(lay, 0, "ilp") and ev_v.cache is evaluator.cache
    lt = BL.lever_table(evaluator, lay)
    assert {r["lever"] for r in lt["rows"]} == set(BL.LEVERS)
    assert {(r["lever"], r["policy"]) for r in lt["best"]} == {(l, p) for l in BL.LEVERS for p in BL.POLICIES}
    spare = next(r for r in lt["rows"] if r["lever"] == "spare" and r["site"] == "T2" and r["policy"] == "ilp")
    assert spare["d_V"] == pytest.approx(evaluator.value(lay.replace("T2", ("T2", "S", 2, 0))) - evaluator.value(lay), abs=1e-6)
    assert spare["d_investment"] == S.TOY_SPEC.bhat
    pos = next(r for r in lt["rows"] if r["lever"] == "position" and r["policy"] == "ilp")
    assert pos["d_allocated"] == pytest.approx(position_cost_per_window(400.0, window_h=1.0))
    single = BL.lever_table(evaluator, BL.Layout.of([("T1", "SC", 1, 1)]), policies=("ilp",), levers=("shuttle",))
    assert single["rows"][0]["status"] == "NA"


def test_rule_baselines_and_capacity_matching(evaluator, tmp_path):
    """A4 (i)-(ii): IJCAI-15 rule layouts within the budget, the rule table, the capacity-matched
    present-day layout (same totals and investment) and the hub-list reader."""
    cands = evaluator.candidates
    dw = BL.demand_weights(cands, evaluator.scenarios, 1, evaluator.p)
    assert set(dw) == {"T1", "T2"} and all(v >= 0 for v in dw.values())
    sp = S.TOY_SPEC
    assert BL.rule_layout("CSAV", cands, 50.0, sp) is None                       # below one site
    for rule, w in (("CSCD", dw), ("CSTC", BL.access_weights(cands, evaluator.scenarios)), ("CSAV", None)):
        for b in (130.0, BUDGET):
            lay = BL.rule_layout(rule, cands, b, sp, w)
            assert lay is not None and lay.investment(sp) <= b + 1e-9 and lay.valid(sp)
            assert lay.n_open == min(2, int(b // (sp.Fhat + sp.bhat + sp.chat)))
    top = max(dw, key=lambda l: (dw[l], -["T1", "T2"].index(l)))
    assert BL.rule_layout("CSCD", cands, 130.0, sp, dw).locations() == (top,)
    iso = BL.isolation_values(evaluator, cands)
    lay_iso = BL.rule_layout("CSTC", cands, 130.0, sp, iso, lower_is_better=True)
    feas = {l: v for l, v in iso.items() if v is not None}
    assert lay_iso.locations() == (min(feas, key=feas.get),)
    rb = BL.rule_baselines(evaluator, cands, [130.0, BUDGET], policies=("ilp", "baseline"), D_blocks=1)
    assert len(rb["rows"]) == 2 * 3 * 2 and all(r["V"] is not None for r in rb["rows"] if r["status"] == "OK")
    ref = BL.Layout.of([("T1", "SC", 2, 1), ("T2", "SC", 1, 0)])
    pres = BL.present_day_sites(cands, data_dir=str(tmp_path))
    assert pres["proxy"] and pres["n_points"] == 0
    cm = BL.capacity_matched_layout(cands, ref, {"T1": 1.0, "T2": 3.0}, sp)
    assert cm.n_open == ref.n_open and cm.total_B() == ref.total_B() and cm.total_C() == ref.total_C()
    assert cm.investment(sp) == pytest.approx(ref.investment(sp)) and cm.valid(sp)
    gbfs = {"data": {"stations": [{"lat": 0.0, "lon": 1.0, "is_charging_station": True},
                                  {"lat": 0.0, "lon": 3.1, "is_charging_station": True},
                                  {"lat": 0.0, "lon": 2.9, "is_charging_station": True},
                                  {"lat": 0.0, "lon": 1.0, "is_charging_station": False}]}}
    with open(tmp_path / BL.PRESENT_DAY_FILES[0], "w", encoding="utf-8") as fh:
        json.dump(gbfs, fh)
    pres2 = BL.present_day_sites(cands, data_dir=str(tmp_path))
    assert not pres2["proxy"] and pres2["n_points"] == 3 and pres2["weights"] == {"T1": 1.0, "T2": 2.0}


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "..", "data", "raw", "dohmh_restaurants.csv")),
                    reason="DOHMH data not present")
def test_manhattan_region_lattice_and_depots():
    """M6: Manhattan south of 110th St, 2 km lattice candidates, entry-point depots, D anchored
    to the eBaaS 2 km coverage."""
    from ebike_swap_sim import data_nyc as dn
    reg = dn.MANHATTAN_S110
    assert S.access_radius_blocks() == 14 and S.access_radius_blocks(2000.0, 250.0) == 8
    cands = S.lattice_candidates()
    assert 10 <= len(cands) <= 20 and [c.id for c in cands] == [f"M{i:02d}" for i in range(1, len(cands) + 1)]
    assert len({c.node for c in cands}) == len(cands) and all(c.source == "lattice" for c in cands)
    assert all(reg.node_in_band(c.node) for c in cands)
    assert all(S.manhattan_blocks(a.node, b.node) >= 2 for i, a in enumerate(cands) for b in cands[i + 1:])
    cells = {tuple(int(x) for x in c.label.split("(")[1].split(")")[0].split(", ")) for c in cands}
    assert len(cells) == len(cands)                                     # one candidate per 2 km cell
    rest = dn.region_restaurants(reg)
    assert set(rest["boro"]) == {"Manhattan"} and (rest["y"] <= reg.y_max + 1e-9).all()
    dep = S.family_depots("r5_manhattan", cands)
    assert len(dep) == 6 and dep == dn.entry_point_depots() and all(reg.node_in_band(d) for d in dep)
    assert S.family_depots("nyc4h_stress2", cands) == [c.node for c in cands[:3]]
    assert S.family_access_D("r5_manhattan") == 14 and S.family_access_D("nyc4h_stress2") is None
    with pytest.raises(KeyError):
        dn.resolve_region("brooklyn")


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "..", "data", "raw", "dohmh_restaurants.csv")),
                    reason="DOHMH data not present")
def test_r5_manhattan_base_instance():
    """M6 family ``r5_manhattan`` at reduced size (2 bikes): demand inside the region, eBaaS
    calibration (L 24, q_res 2, concat), TOU price, riders at the entry points, layouts validate
    and keep the demand."""
    from ebike_swap_sim import data_nyc as dn
    reg = dn.MANHATTAN_S110
    cands = S.lattice_candidates()
    base = S.make_base_instance(0, cands, family="r5_manhattan", n_bikes=2)
    assert base.meta["family"] == "r5_manhattan" and base.meta["region"]["name"] == "manhattan_s110"
    assert len(base.orders) == 10 and base.H == 48 and base.L == 24 and base.q_res == 2
    assert base.options["energy_rounding"] == "concat" and base.pi == pytest.approx(0.442)
    assert base.meta["tariff"]["name"] == "tou" and base.meta["energy_calibration"]["name"] == "ebaas"
    assert all(6 <= b.q0 <= 12 for b in base.bikes)
    assert [b.v0 for b in base.bikes] == dn.entry_point_depots()[:2]
    assert all(str(r["zone_code"]).startswith("MN") for r in base.meta["orders"])
    assert all(reg.node_in_band(o.o) and reg.node_in_band(o.d) for o in base.orders)
    assert all(rec["lat"] > 0 and reg.in_band(rec["lat"], rec["lon"]) for rec in base.meta["restaurant_records"])
    spec = S.spec_from_instance(base)
    assert spec.P_kw == pytest.approx(1.4) and spec.grid_kw == pytest.approx(2.0)
    lay = S.layout_instance(base, [("M08", "SC", 2, 1), ("M04", "SC", 1, 1)], spec)
    assert lay.validate() == [] and C.demand_md5(lay) == C.demand_md5(base) and lay.services
    assert lay.pi == pytest.approx(0.442)
    # the region switch is opt-in: without it the builder records no region (old families unchanged)
    assert "region" not in dn.make_nyc_instance(seed=0, n_bikes=1, n_orders=2).meta


@pytest.mark.parametrize("sub", ["--manhattan", "--baselines", "--levers", "--policy-aware", "--compliance"])
def test_e9_round5_smoke_modes(sub, tmp_path):
    out = str(tmp_path / "e9")
    r = _run(sub, "--smoke", "--out-root", out)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    sub_dir = os.path.join(out, sub.lstrip("-").replace("-", "_"))
    for f in ("records.jsonl", "results.csv", "RESULTS.md"):
        assert os.path.exists(os.path.join(sub_dir, f)), f
    rows = C.load_jsonl(os.path.join(sub_dir, "records.jsonl"))
    assert rows
    if sub == "--compliance":
        summ = {r["alpha_c"]: r for r in rows if r.get("kind") == "compliance_summary"}
        assert summ and summ[1.0]["complete"]


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "..", "data", "raw", "dohmh_restaurants.csv")),
                    reason="DOHMH data not present")
def test_e9_round5_dry_runs(tmp_path):
    for sub in ("--manhattan", "--baselines", "--levers", "--policy-aware", "--compliance"):
        r = _run(sub, "--dry-run", "--out-root", str(tmp_path / "e9"), timeout=300.0)
        assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
        assert "r5_manhattan" in r.stdout
