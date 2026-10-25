"""Round-5 evaluation layer (``notes/reading_to_model.md``): the A3 metric pack
(``evaluate.metric_pack``, ``metrics()['r5']``), the M1 end-state adjustment
(``evaluate.end_state_adjustment``, ``cost()['C_end_adjust']``) and the M1 boundary
grid (``experiments.common.boundary_grid`` / ``end_target_copy`` / ``relax_end_targets``).

None of these changes E2 (``notes/extracted/E2.txt``): ``cost()['total']`` is still (26)
and the toy optima 12.5 / 11.2 are re-checked here on the grid cells."""
from __future__ import annotations

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebike_swap_sim import Schedule, build_arcs, check, cost, metrics, toy_instance  # noqa: E402
from ebike_swap_sim.evaluate import (R5_SCALAR_KEYS, end_reference_price,  # noqa: E402
                                     end_state_adjustment, metric_pack)
from experiments import common as C  # noqa: E402


# ---------------------------------------------------------------------------
# helpers: hand-built schedules on an existing library
# ---------------------------------------------------------------------------
def _wait_to_horizon(lib, k, node, arcs):
    """Append wait arcs from ``node`` to ``H`` and a terminal arc; returns the end node."""
    H = lib.inst.H
    v, t, q = node
    while t < H:
        a = lib.find(k, "wait", (v, t, q))
        assert a is not None, f"no wait arc at {(v, t, q)}"
        arcs.append(a.id)
        t += 1
    term = [a for a in lib.out_arcs(k, (v, H, q)) if a.kind == "term"]
    if term:
        arcs.append(term[0].id)
    return (v, H, q)


def _idle_schedule(inst, lib):
    """Every bike waits at its start node for the whole horizon: nothing happens."""
    x = {}
    for b in inst.bikes:
        arcs = []
        _wait_to_horizon(lib, b.id, lib.source(b.id), arcs)
        x[b.id] = arcs
    return Schedule(x=x, u={o.id: 1 for o in inst.orders})


def _one_swap_schedule(inst, lib):
    """Idle schedule except one bike that (moves to a site and) swaps once, then waits.
    Returns ``(schedule, bike id, swap arc)``."""
    sched = _idle_schedule(inst, lib)
    for b in inst.bikes:
        k = b.id
        src = lib.source(k)
        cand = [a for a in lib.out_arcs(k, src) if a.kind == "swap"]
        pre = []
        if not cand:
            for m in lib.out_arcs(k, src):
                if m.kind != "move":
                    continue
                sw = [a for a in lib.out_arcs(k, m.dst) if a.kind == "swap"]
                if sw:
                    pre, cand = [m.id], sw
                    break
        if not cand:
            continue
        sw = cand[0]
        arcs = pre + [sw.id]
        _wait_to_horizon(lib, k, sw.dst, arcs)
        sched.x[k] = arcs
        return sched, k, sw
    pytest.skip("no bike can reach a swap site at t = 0 in this library")


@pytest.fixture(scope="module")
def small():
    inst = C.make_instance("small", seed=0)
    lib = build_arcs(inst, **C.pruning_for(inst))
    return inst, lib


# ---------------------------------------------------------------------------
# M1 end-state adjustment
# ---------------------------------------------------------------------------
def test_end_adjust_zero_when_end_state_equals_start_state(small):
    """C_end_adjust = 0 when every station ends at its initial stock and every bike at q0
    (toy and one synthetic instance), for every bike-term convention; total unchanged."""
    for inst, lib in ((toy_instance(), None), small):
        lib = lib or build_arcs(inst)
        sched = _idle_schedule(inst, lib)
        for term in ("positive", "signed", "none"):
            adj = end_state_adjustment(inst, lib, sched, bike_term=term)
            assert adj["C_end_adjust"] == 0.0 and adj["station_levels"] == 0 and adj["bike_levels"] == 0
        cst = cost(inst, lib, sched)
        assert cst["C_end_adjust"] == 0.0 and cst["total_end_adjusted"] == cst["total"]
        assert metrics(inst, lib, sched)["r5"]["C_end_adjust"] == 0.0
    with pytest.raises(ValueError):
        end_state_adjustment(inst, lib, sched, bike_term="both")


def test_end_adjust_station_and_bike_terms(small):
    """One swap of an otherwise idle fleet: the station gains a level-q battery (L - q
    levels missing), the bike ends full (no deficit under the plan's positive part); the
    signed balance equals the energy the bike rode before swapping (q0 - q)."""
    inst, lib = small
    sched, k, sw = _one_swap_schedule(inst, lib)
    L, q_ret, q0 = inst.L, sw.src[2], inst.bike(k).q0
    pos = end_state_adjustment(inst, lib, sched)
    sig = end_state_adjustment(inst, lib, sched, bike_term="signed")
    assert pos["station_levels"] == L - q_ret and pos["bike_levels"] == 0
    assert sig["station_levels"] + sig["bike_levels"] == q0 - q_ret
    price = end_reference_price(inst)
    assert price == pytest.approx(float(inst.pi))                      # flat price
    assert pos["C_end_adjust"] == pytest.approx(price * inst.disc.kwh_per_step * (L - q_ret))
    cst = cost(inst, lib, sched)
    assert cst["C_end_adjust"] == pytest.approx(pos["C_end_adjust"])
    assert cst["total_end_adjusted"] == pytest.approx(cst["total"] + pos["C_end_adjust"])
    assert cost(inst, lib, sched, end_price=1.0)["C_end_adjust"] == pytest.approx(
        inst.disc.kwh_per_step * (L - q_ret))


def test_toy_cost_total_unchanged_and_end_adjust_reported():
    """(26) is untouched: the toy optimum still prices at 12.5; the end adjustment is a
    separate line (both bikes end one level below q0 = 2: 2 levels x 0.025 kWh x 2)."""
    from tests.test_core import toy_documented_schedule
    inst = toy_instance()
    lib = build_arcs(inst)
    cst = cost(inst, lib, toy_documented_schedule(lib))
    assert cst["total"] == pytest.approx(12.5)
    assert cst["C_end_adjust"] == pytest.approx(0.1)
    assert cst["C_end_adjust_parts"]["station"] == 0.0 and cst["C_end_adjust_parts"]["bike_levels"] == 2
    assert cst["total_end_adjusted"] == pytest.approx(12.6)
    flat = C.flatten_cost(cst, "x_")
    assert flat["x_total"] == pytest.approx(12.5) and flat["x_C_end_adjust_bikes"] == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# A3 metric pack
# ---------------------------------------------------------------------------
def test_metric_pack_toy_documented_schedule():
    """Hand-checked values on the E2 toy optimum (one swap at A at t = 3 after a 1 km
    reposition; two charge steps at C; 1 km empty of 4 km)."""
    from tests.test_core import toy_documented_schedule
    inst = toy_instance()
    lib = build_arcs(inst)
    r5 = metrics(inst, lib, toy_documented_schedule(lib))["r5"]
    assert r5["n_swaps"] == 1 and r5["swaps_per_slot"] == [0, 0, 0, 1, 0, 0, 0, 0]
    assert r5["bsr"] == 1.0 and r5["bsr_unblocked"] == 1.0
    assert r5["sbur"] == {"A": None} and r5["min_sbur"] is None           # B_A = 0
    assert r5["mean_station_time_min"] == pytest.approx(5.0)              # sigma 1 slot, no wait
    assert r5["mean_detour_km_per_swap"] == pytest.approx(1.0)
    assert r5["empty_km"] == pytest.approx(1.0) and r5["delivery_km"] == pytest.approx(3.0)
    assert r5["empty_km_per_bike_hour"] == pytest.approx(1.0 / (2 * 8 / 12))
    assert r5["peak_kw_network"] == pytest.approx(0.3) and r5["kwh_by_price"] == {"2": pytest.approx(0.05)}
    assert r5["outage_rate"] == 0.0 and r5["n_energy_refused_orders"] == 0
    assert r5["batteries_saved"] == {"C": 0}


def test_toy_metrics_for_both_policies_via_run_pair():
    """run_pair on the toy: ILP 12.5 and REORDER_POINT 14.5 unchanged; A3 columns and the
    end-adjusted totals / gaps exist for both policies."""
    pytest.importorskip("gurobipy")
    rec = C.run_pair(C.make_instance("toy"), pruning={},
                     baseline_params={"transfer_rule": "REORDER_POINT"}, time_limit=60.0)
    C.assert_pair(rec)
    assert rec["ilp_total"] == pytest.approx(12.5) and rec["baseline_total"] == pytest.approx(14.5)
    for pref in ("ilp_", "baseline_"):
        for key in R5_SCALAR_KEYS:
            assert f"{pref}r5_{key}" in rec
        assert rec[f"{pref}total_end_adjusted"] == pytest.approx(rec[f"{pref}total"] + rec[f"{pref}C_end_adjust"])
        assert rec[f"{pref}r5_C_end_adjust"] == pytest.approx(rec[f"{pref}C_end_adjust"])
    assert rec["gap_vs_baseline_pct_end_adjusted"] is not None
    assert rec["boundary_variant"] == "written"
    df = C.records_to_frame([rec])
    assert "ilp_r5_bsr" in df.columns and "baseline_r5_outage_rate" in df.columns


def test_synthetic_metrics_for_both_policies(small):
    """Small synthetic instance (co-located sites): the pack is computed for the ILP and
    the baseline from their schedules alone and is internally consistent."""
    pytest.importorskip("gurobipy")
    inst, lib = small
    rec = C.run_pair(inst, lib=lib, time_limit=120.0, keep_schedules=True)
    C.assert_pair(rec)
    for tag in ("_ilp", "_baseline"):
        r = rec[tag]
        sched, met = r["schedule"], r["metrics"]
        r5 = met["r5"]
        assert r5 == metric_pack(inst, lib, sched)                        # no hidden state
        assert r5["n_swaps"] == met["n_swaps"] == sum(r5["swaps_per_slot"])
        assert r5["kwh_purchased"] == pytest.approx(met["kwh_purchased"])
        assert sum(r5["kwh_by_price"].values()) == pytest.approx(met["kwh_purchased"])
        assert r5["peak_kw_network"] >= max(met["peak_kw_facility"].values() or [0.0]) - 1e-9
        assert 0.0 <= r5["outage_rate"] <= 1.0
        for v in (r5["bsr"], r5["bsr_unblocked"]):
            assert v is None or 0.0 <= v <= 1.0
        if r5["bsr"] is not None:
            assert r5["bsr_unblocked"] >= r5["bsr"]
        assert r5["empty_km"] + r5["delivery_km"] == pytest.approx(met["bike_km"])
        B = met["facility_vars"]["B"]
        assert all(0 <= v <= B[j] for j, v in r5["batteries_saved"].items())
        for j, v in r5["sbur"].items():
            assert v == pytest.approx(met["swaps_per_facility"].get(j, 0) / B[j])
        assert r5["C_end_adjust"] == pytest.approx(r["cost"]["C_end_adjust"])


def test_batteries_saved_is_an_exact_certificate(small):
    """Removing ``batteries_saved_j`` initial spares at each site keeps the baseline
    schedule feasible for (13)-(16) (only the report-only end targets may move)."""
    inst, lib = small
    base = C.run_baseline_case(inst, lib)
    saved = base["metrics"]["r5"]["batteries_saved"]
    assert sum(saved.values()) > 0
    B = dict(base["metrics"]["facility_vars"]["B"])
    s2 = copy.deepcopy(base["schedule"])
    s2.n = None
    s2.B = {j: B[j] - saved.get(j, 0) for j in B}
    rep = check(inst, lib, s2)
    bad = {f for f, r in rep["families"].items() if r["count"] and f not in C.BASELINE_REPORT_ONLY}
    assert not bad, rep["families"]
    # one more spare removed at a site with stock breaks (14) or the sign of n
    j = next(j for j in B if s2.B[j] > 0)
    s2.B[j] -= 1
    rep2 = check(inst, lib, s2)
    assert any(f in rep2["families"] for f in ("(14)", "domain"))


# ---------------------------------------------------------------------------
# M1 boundary grid
# ---------------------------------------------------------------------------
def test_boundary_grid_sizes_labels_and_rules():
    """8 cells rho {0, .25, .5, 1} x R_end {0, 1} + periodic; R_end = 0 at swap-only sites
    in every variant; periodic R_end_j = B_j at S cap C; only parameters change."""
    for overrides, colocated in (({}, True), ({"facilities_spec": {"mode": "separated"}}, False)):
        inst = C.make_instance("small", seed=0, **overrides)
        before = inst.to_json()
        grid = C.boundary_grid(inst)
        assert len(grid) == 9 and len(C.boundary_grid(inst, periodic=False)) == 8
        labels = [lab for lab, _ in grid]
        assert labels[0] == "rho0_R0" and labels[-1] == "periodic" and len(set(labels)) == 9
        assert inst.to_json() == before                                  # original untouched
        md5 = C.demand_md5(inst, include_facilities=False)
        for lab, g in grid:
            assert g.meta["boundary_variant"] == lab and g.meta["compare_with_end_adjust"] is True
            assert C.demand_md5(g) == md5
            assert g.meta["written_R_end"] == {f.id: f.R_end for f in inst.facilities}
            b = g.meta["boundary"]
            assert g.rho == b["rho"]
            for f in g.facilities:
                if f.swap and not f.charge:
                    assert f.R_end == 0                                  # swap-only: always 0
                elif not f.swap:
                    assert f.R_end == 0
                elif lab == "periodic":
                    assert f.R_end == f.B
                else:
                    assert f.R_end == b["R_end"]
            assert [(f.id, f.node, f.B, f.C, f.K) for f in g.facilities] == \
                   [(f.id, f.node, f.B, f.C, f.K) for f in inst.facilities]
        rhos = sorted({g.rho for _, g in grid})
        assert rhos == [0.0, 0.25, 0.5, 1.0]
        if not colocated:
            assert all(f.R_end == 0 for _, g in grid for f in g.facilities)
    # free B: the periodic bracket cannot set R_end = B_j as data
    inst = C.make_instance("small", seed=0)
    inst.facilities[0].B = None
    inst.reindex()
    per = C.end_target_copy(inst, 1.0, "B")
    assert per.meta["boundary_variant"] == "periodic" and per.meta["boundary_free_B"] == [inst.facilities[0].id]
    assert per.facilities[0].R_end == 0


def test_relax_end_targets_is_the_rho0_R0_cell():
    inst = C.make_instance("small", seed=0)
    rel = C.relax_end_targets(inst)
    cell = dict(C.boundary_grid(inst))["rho0_R0"]
    assert rel.rho == cell.rho == 0.0
    assert [f.R_end for f in rel.facilities] == [f.R_end for f in cell.facilities] == [0] * len(inst.facilities)
    assert rel.meta["relax_end_targets"] is True and rel.meta["boundary_variant"] == "rho0_R0"
    assert rel.meta["written_R_end"] == {f.id: f.R_end for f in inst.facilities}
    assert rel.meta["written_rho"] == inst.rho
    # a copy of a copy keeps the WRITTEN targets
    assert C.relax_end_targets(cell).meta["written_R_end"] == rel.meta["written_R_end"]


def test_toy_grid_cells_reproduce_invariants():
    """Toy (swap-only A, hub C, written rho = 1): rho1_R0 is the written model (12.5),
    rho0_R0 the relaxed control (11.2); the policy keeps its written reserve on a cell."""
    pytest.importorskip("gurobipy")
    from ebike_swap_sim import build_arcs as ba
    grid = dict(C.boundary_grid(toy_instance()))
    assert len(grid) == 9
    for lab, want in (("rho1_R0", 12.5), ("rho0_R0", 11.2), ("periodic", 12.5)):
        g = grid[lab]
        rec = C.run_ilp_case(g, ba(g), time_limit=60.0)
        assert rec["status"] == "OPTIMAL" and rec["obj"] == pytest.approx(want), lab
        assert rec["cost"]["total"] == pytest.approx(want)
    g = grid["rho0.5_R1"]
    base = C.run_baseline_case(g, ba(g))
    assert base["policy_reserve_source"] == "written_R_end"
