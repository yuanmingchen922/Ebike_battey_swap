"""R7 siting scale-up (``notes/siting_scaleup_design.md`` section 4 item 7, corrected in section 7):
toy tests at Threads 1.  DOT CSV loader (snapping, 80 m merge, type priority, lattice union,
hub-capable set), the approach radius (signature unchanged when unset, library byte-identical
when the radius does not bind), the stratified scenario design, scenario-parallel pricing against
the sequential one, the regional subset bound (validity against exhaustive toy values, the
free-size point where the max-size point fails, the subset cut at every integer point), the
branch-and-bound at m = 1, 2 against the exhaustive optimum with resume, two-tier pricing, the
CI helpers, the lane writer and the CLI smoke run."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import arcs as AR  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from ebike_swap_sim import data_nyc as dn  # noqa: E402
from ebike_swap_sim import costs as CM  # noqa: E402
from experiments import common as C  # noqa: E402

CANDS4 = (("T1", 1), ("T2", 2), ("T3", 3), ("T4", 4))
MENU = {"S": [(1, 0), (2, 0)], "C": [(0, 1)], "SC": [(1, 1), (2, 1)]}
PARAMS = {"Seed": 0, "MIPGap": 0.0}
UNIT = 130.0
LEVELS4 = [{"R1": ["T1", "T2"], "R2": ["T3", "T4"]}, {"T1": ["T1"], "T2": ["T2"], "T3": ["T3"], "T4": ["T4"]}]


# ---------------------------------------------------------------------------
# DOT loader
# ---------------------------------------------------------------------------
def _fake_restaurants(box, nodes):
    return pd.DataFrame({"node": [tuple(n) for n in nodes], "boro": ["Manhattan"] * len(nodes)})


def _dot_csv(path, rows, cols=("id", "name", "address", "lat", "lon", "site_type", "operator", "status_date",
                                 "source_url", "coord_method", "verdict", "angle")):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cols))
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def test_dot_loader_snapping_merge_priority_and_lattice_union(tmp_path):
    reg = dn.resolve_region("manhattan_s110")
    box = reg.box
    base = box.node_latlon((40, 40))
    # offsets in metres along the rotated frame via inverse()
    def at(dx, dy):
        x, y = box.node_xy((40, 40))
        return box.inverse(x + dx, y + dy)
    near1, near2 = at(10.0, 0.0), at(50.0, 0.0)            # 40 m apart: merge; the pilot wins
    far1, far2 = at(600.0, 0.0), at(600.0, 120.0)           # 120 m apart, distinct nodes (150 m grid): both stay
    north = (40.805, -73.95)                                 # north of 110th St: outside the band
    rows = [
        {"id": "a", "name": "shortlist site", "lat": near1[0], "lon": near1[1], "site_type": "shortlist", "verdict": "keep"},
        {"id": "b", "name": "pilot site", "lat": near2[0], "lon": near2[1], "site_type": "pilot", "verdict": "keep"},
        {"id": "c", "name": "citi dock", "lat": far1[0], "lon": far1[1], "site_type": "citibike_charging"},
        {"id": "d", "name": "weird", "lat": far2[0], "lon": far2[1], "site_type": "something_new"},
        {"id": "e", "name": "uptown", "lat": north[0], "lon": north[1], "site_type": "pilot"},
        {"id": "f", "name": "no coords", "lat": "", "lon": "", "site_type": "pilot"},
        {"id": "g", "name": "rejected", "lat": far1[0], "lon": far1[1], "site_type": "fdny_hub", "verdict": "reject: private"},
    ]
    p = tmp_path / "dot.csv"
    _dot_csv(p, rows)
    lat_same = S.Candidate(id="M01", label="lattice at the pilot node", source="lattice", lat=base[0], lon=base[1],
                           node=box.snap(*near2), n_restaurants=7, rank=1)
    lat_far = S.Candidate(id="M02", label="lattice far", source="lattice", lat=0.0, lon=0.0, node=(60, 60),
                          n_restaurants=3, rank=2)
    rest = _fake_restaurants(box, [box.snap(*near2)] * 5 + [(60, 60)] * 3)
    cands, dropped, info = S.dot_candidates(str(p), region=reg, merge_m=80.0, lattice=[lat_same, lat_far], restaurants=rest,
                                            min_hub=0)
    by_label = {c.label.split(" [")[0]: c for c in cands}
    assert "pilot site" in by_label and "shortlist site" not in by_label           # merged: pilot priority wins
    pilot = by_label["pilot site"]
    assert "shortlist site" in pilot.merged_labels and pilot.dot_type == "pilot" and pilot.cls == "both"
    assert pilot.lattice_id == "M01" and pilot.n_restaurants == 5
    assert "citi dock" in by_label and "weird" in by_label                           # 120 m apart, distinct nodes
    assert by_label["citi dock"].node != by_label["weird"].node
    assert by_label["weird"].dot_type == "other" and by_label["citi dock"].hub_capable and not pilot.hub_capable
    assert by_label["lattice far"].cls == "lattice" and by_label["lattice far"].lattice_id == "M02"
    reasons = {r["id"]: r["reason"] for r in dropped}
    assert "outside" in reasons["e"] and "lat/lon" in reasons["f"] and "verdict" in reasons["g"]
    assert all(c.snap_m < 110.0 for c in cands) and all(c.cell is not None for c in cands)
    ids = [c.id for c in cands]
    assert ids == [f"D{i + 1:02d}" for i in range(len(cands))]
    order = [(c.cell[1], c.cell[0], c.node[1], c.node[0]) for c in cands]
    assert order == sorted(order)                                                   # south -> north, west -> east
    assert info["n_merged"] == 2 and info["n_dropped"] == 3 and info["n_candidates"] == 4   # shortlist -> pilot, M01 -> pilot
    paths = S.write_candidate_tables(cands, dropped, str(tmp_path / "out"))
    assert os.path.exists(paths["candidates"]) and os.path.exists(paths["dropped"])
    back = S.candidates_from_records(S.candidates_to_records(cands))
    assert [c.id for c in back] == ids and back[0].cell == cands[0].cell
    # unknown columns / missing columns are tolerated
    _dot_csv(tmp_path / "dot2.csv", [{"id": "x", "lat": far1[0], "lon": far1[1], "extra": 1}], cols=("id", "lat", "lon", "extra"))
    c2, d2, i2 = S.dot_candidates(str(tmp_path / "dot2.csv"), region=reg, with_lattice=False, restaurants=rest)
    assert len(c2) == 1 and c2[0].dot_type == "other" and i2["n_candidates"] == 1
    c3, d3, i3 = S.dot_candidates(str(tmp_path / "absent.csv"), region=reg, lattice=[lat_far], restaurants=rest)
    assert not i3["file_present"] and len(c3) == 1 and c3[0].cls == "lattice"


def test_dot_loader_duplicate_ids_lattice_id_collision_and_verdict_tokens(tmp_path):
    """Fixer pass: two rows with the same id 3 km apart stay two candidates; a DOT row whose id
    equals a lattice id is not merged with that lattice cell; only whole rejecting tokens drop a
    row ('No objection', 'not sure', 'outstanding candidate' are kept)."""
    reg = dn.resolve_region("manhattan_s110")
    box = reg.box
    a_lat, a_lon = box.node_latlon((40, 40))
    b_lat, b_lon = box.node_latlon((60, 40))                   # 20 blocks = 3 km east
    rows = [{"id": "dup", "name": "first", "lat": a_lat, "lon": a_lon, "site_type": "pilot"},
            {"id": "dup", "name": "second", "lat": b_lat, "lon": b_lon, "site_type": "shortlist"},
            {"id": "M01", "name": "dot spelled like a lattice id", "lat": box.node_latlon((50, 40))[0],
             "lon": box.node_latlon((50, 40))[1], "site_type": "installed"}]
    p = tmp_path / "dot.csv"
    _dot_csv(p, rows)
    lat_far = S.Candidate(id="M01", label="lattice M01", source="lattice", lat=0.0, lon=0.0, node=(60, 60),
                          n_restaurants=3, rank=1)
    rest = _fake_restaurants(box, [(40, 40)] * 2)
    cands, dropped, info = S.dot_candidates(str(p), region=reg, lattice=[lat_far], restaurants=rest, min_hub=0)
    labels = sorted(c.label.split(" [")[0] for c in cands)
    assert labels == ["dot spelled like a lattice id", "first", "lattice M01", "second"]
    assert info["n_merged"] == 0 and not dropped and info["n_candidates"] == 4
    assert all(not c.merged_labels for c in cands)
    assert set(info["renamed_ids"]) == {"dup~2", "M01~dot"} and info["renamed_ids"]["dup~2"] == "dup"
    assert [c.lattice_id for c in cands if c.label.startswith("lattice")] == ["M01"]
    assert all(c.lattice_id is None for c in cands if c.cls == "dot")
    # verdict tokens
    for v in ("No objection", "not sure", "outstanding candidate", "keep", "OK", "Excellent", "", "yes", "Outstanding"):
        assert not S._rejected(v), v
    for v in ("drop", "Drop: private", "reject", "rejected (fence)", "exclude", "Excluded", "out of scope", "out",
              "outside the band", "no-go", "No go: traffic", "remove"):
        assert S._rejected(v), v
    rows2 = [{"id": "k", "name": "kept", "lat": a_lat, "lon": a_lon, "site_type": "pilot", "verdict": "No objection"},
             {"id": "d", "name": "dropped", "lat": b_lat, "lon": b_lon, "site_type": "pilot", "verdict": "no-go: private"}]
    _dot_csv(tmp_path / "dot2.csv", rows2)
    c2, d2, i2 = S.dot_candidates(str(tmp_path / "dot2.csv"), region=reg, with_lattice=False, restaurants=rest, min_hub=0)
    assert [c.label.split(" [")[0] for c in c2] == ["kept"] and [r["id"] for r in d2] == ["d"]
    assert i2["verdict_dropped"] == [{"id": "d", "name": "dropped", "verdict": "no-go: private"}]
    assert i2["verdicts_kept"] == {"No objection": 1}


def test_dot_loader_cap_and_hub_fallback(tmp_path):
    reg = dn.resolve_region("manhattan_s110")
    box = reg.box
    rows = []
    for i in range(8):
        lat, lon = box.node_latlon((20 + 3 * i, 30))
        rows.append({"id": f"o{i}", "name": f"other {i}", "lat": lat, "lon": lon, "site_type": "other"})
    lat, lon = box.node_latlon((20, 60))
    rows.append({"id": "p", "name": "pilot", "lat": lat, "lon": lon, "site_type": "pilot"})
    p = tmp_path / "dot.csv"
    _dot_csv(p, rows)
    lattice = [S.Candidate(id=f"M{k:02d}", label=f"lat {k}", source="lattice", lat=0, lon=0, node=(10 + 2 * k, 80),
                           n_restaurants=10 - k, rank=k) for k in range(1, 5)]
    rest = _fake_restaurants(box, [(20, 30)] * 4 + [(23, 30)] * 2)
    cands, dropped, info = S.dot_candidates(str(p), region=reg, cap=6, lattice=lattice, restaurants=rest, min_hub=4,
                                            lattice_hub_fallback=2)
    assert info["n_candidates"] == 6 and info["n_capped"] + info["n_dropped"] == 7
    assert sum(1 for c in cands if c.dot_type == "other") == 1 and all(r.get("reason") for r in dropped)
    # the 'other' rows with the fewest restaurants within 4 blocks went first; the pilot and the lattice stay
    assert any(c.dot_type == "pilot" for c in cands) and sum(1 for c in cands if c.cls == "lattice") == 4
    hubs = [c for c in cands if c.hub_capable]
    assert len(hubs) == 2 and all(c.lattice_id in ("M01", "M02") for c in hubs)    # two busiest lattice cells
    assert info["hub_fallback_lattice"] == ["M01", "M02"]


@pytest.mark.skipif(not os.path.exists(dn.DEFAULT_PATHS.get("dohmh", "")), reason="DOHMH data not present")
def test_lattice_fixture_reproduces_the_15_candidate_nodes(tmp_path):
    lat = S.lattice_candidates()
    rows = [{"id": c.id, "name": c.label, "lat": c.lat, "lon": c.lon, "site_type": "pilot"} for c in lat]
    p = tmp_path / "lattice_as_dot.csv"
    _dot_csv(p, rows)
    cands, dropped, info = S.dot_candidates(str(p))
    assert info["n_candidates"] == 15 and info["n_merged"] == 15 and not dropped
    assert [c.node for c in cands] == [c.node for c in lat]
    assert [c.lattice_id for c in cands] == [c.id for c in lat] and all(c.cls == "both" for c in cands)
    roles = S.candidate_roles(cands)
    assert all("C" not in roles[c.id] for c in cands) or info["n_hub_capable"] <= 12


# ---------------------------------------------------------------------------
# approach radius and pruning signature
# ---------------------------------------------------------------------------
def _toy_ev(tmp_path=None, relaxed=False, cands=CANDS4, pruning=None, **kw):
    scen = [S.toy_base_instance(0, candidates=cands), S.toy_base_instance(1, candidates=cands)]
    ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                cache_dir=(None if tmp_path is None else str(tmp_path)), pruning=pruning, **kw)
    return ev.derive(relaxed_targets=True) if relaxed else ev


def test_pruning_signature_unchanged_without_radius_and_library_identical_when_it_does_not_bind(tmp_path):
    ev0 = _toy_ev()
    sig0 = ev0.pruning_signature(0)
    assert "reposition_target_radius" not in sig0
    ev_inf = _toy_ev(pruning={"approach_radius_blocks": 99})
    assert "reposition_target_radius" in ev_inf.pruning_signature(0)
    t0, t1 = ev0.template(0)[1], ev_inf.template(0)[1]
    assert len(t0) == len(t1) and all((a.kind, a.src, a.dst, a.k) == (b.kind, b.src, b.dst, b.k) for a, b in zip(t0.arcs, t1.arcs))
    ev_r = _toy_ev(pruning={"approach_radius_blocks": 1})
    tr = ev_r.template(0)[1]
    assert len(tr) < len(t0)
    cand_nodes = set(ev_r.cand_node.values())
    exempt = AR.radius_exempt_states(S.siting_pruning(ev_r.scenarios[0], approach_radius_blocks=1)["reposition_radius_exempt_states"])
    for a in tr.arcs:
        if a.kind == "move" and a.dst[0] in cand_nodes and AR.node_blocks(a.src[0], a.dst[0]) > 1:
            assert a.src[2] in exempt.get(a.src[0], ())          # only from a bike's start state
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    assert ev0.cache_key(lay, 0, "ilp") != ev_r.cache_key(lay, 0, "ilp")
    # every ILP value under the radius is an upper bound on the unrestricted one (sub-library)
    v0, vr = ev0.value(lay), ev_r.value(lay)
    assert vr >= v0 - 1e-6


def test_siting_pruning_radius_key_only_when_set():
    inst = S.toy_base_instance(0, candidates=CANDS4)
    assert S.siting_pruning(inst) == {}
    pr = S.siting_pruning(inst, approach_radius_blocks=2)
    assert set(pr) == {"reposition_target_radius", "reposition_radius_exempt_states"}
    assert pr["reposition_target_radius"] == {1: 2, 2: 2, 3: 2, 4: 2}
    assert set(pr["reposition_radius_exempt_states"]) == {(b.v0, b.q0) for b in inst.bikes}


def test_radius_exempts_start_states_only():
    """2026-10-21 (narrowed after review): a bike's first approach to a far candidate is one move
    arc from its start state ``(v0, q0)`` at any ``t``; every other tail state, including the depot
    at another charge level, still obeys the radius."""
    inst = S.toy_base_instance(0, candidates=CANDS4)
    pr = S.siting_pruning(inst, approach_radius_blocks=0)
    states = set(pr["reposition_radius_exempt_states"])
    assert states == {(0, 3)}
    opts = dict(inst.options); opts.update(pr)
    specs = AR._template_specs(inst, opts, AR.compute_gbar(inst))
    moves = [sp for sp in specs if sp[0] == "move" and sp[2][0] in pr["reposition_target_radius"]]
    far = [sp for sp in moves if AR.node_blocks(sp[1][0], sp[2][0]) > 0]
    assert far and all((sp[1][0], sp[1][2]) in states for sp in far)
    H, L = inst.disc.H, inst.disc.L
    for (v, w), r in inst.routes.items():          # every far move out of a start state, at every t
        if (v, 3) in states and w in pr["reposition_target_radius"] and inst.disc.g(r.E_kwh) <= 3:
            tau = inst.disc.tau(r.T_h, distinct=True)
            got = {sp[1][1] for sp in far if sp[1][0] == v and sp[2][0] == w}
            assert got == set(range(0, H - tau + 1)), (v, w)
    # the old whole-tail exemption kept the depot at every level; the narrowed one does not
    tail = dict(opts, reposition_radius_exempt_states=[(0, q) for q in range(L + 1)])
    far_tail = [sp for sp in AR._template_specs(inst, tail, AR.compute_gbar(inst))
                if sp[0] == "move" and sp[2][0] in pr["reposition_target_radius"] and AR.node_blocks(sp[1][0], sp[2][0]) > 0]
    assert len(far_tail) > len(far)
    # a JSON round-trip of grid (tuple) nodes gives lists: normalised back to tuples
    assert AR.radius_exempt_states(json.loads(json.dumps([((44, 56), 8), ((44, 56), 6), (0, 3)]))) == {(44, 56): (6, 8), 0: (3,)}


def _toy_far_starts(cands=CANDS4, q0=3):
    """Two toy scenarios whose bike 2 starts at a different NON-depot node (4, resp. 3) with ``q0``."""
    import dataclasses
    out = []
    for seed, v0 in ((0, 4), (1, 3)):
        inst = S.toy_base_instance(seed, candidates=cands)
        inst.bikes[1] = dataclasses.replace(inst.bikes[1], v0=v0, q0=int(q0))
        inst.validate()
        out.append(inst)
    return out


def test_radius_exemption_follows_each_scenarios_own_starts():
    """Review 2026-10-21: (i) each scenario's exempt states hold its own non-depot start and the
    pruning signatures differ; (ii) a far, low-charge start (node 4, q0 = 3, one-site layout at
    node 1) is terminal-feasible at radius 0 only through the exemption; (iii) under
    ``reposition='open_sites'`` every move arc of a layout library is in the all-candidates
    template of the same scenario (same exemption in the template and every pricing ILP)."""
    scen = _toy_far_starts()
    ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                pruning={"approach_radius_blocks": 0}, reposition="open_sites")
    st = [set(S.siting_pruning(i, approach_radius_blocks=0)["reposition_radius_exempt_states"]) for i in scen]
    assert st[0] == {(0, 3), (4, 3)} and st[1] == {(0, 3), (3, 3)}
    sig0, sig1 = ev.pruning_signature(0), ev.pruning_signature(1)
    assert sig0["reposition_radius_exempt_states"] == [["0", 3], ["4", 3]] and sig0 != sig1
    # (ii) terminal feasibility of bike 2 (far start) for the one-site layout at T1
    lay = BL.Layout.of([("T1", "SC", 1, 1)])
    li = S.layout_instance(scen[0], lay, S.TOY_SPEC)
    free = AR.build_arcs(li, strict=False, **S.siting_pruning(li))
    pr = S.siting_pruning(li, approach_radius_blocks=0)
    ex = AR.build_arcs(li, strict=False, **pr)
    noex = AR.build_arcs(li, strict=False, **{k: v for k, v in pr.items() if k != "reposition_radius_exempt_states"})
    assert not free.infeasible_bikes and not ex.infeasible_bikes and noex.infeasible_bikes == [2]
    # (iii) open_sites layout libraries against the template, both scenarios, several layouts
    lays = [lay, BL.Layout.of([("T4", "SC", 1, 1)]), BL.Layout.of([("T2", "S", 1, 0), ("T3", "C", 0, 1)])]
    for s in range(2):
        tmpl = {(a.k, a.kind, a.src, a.dst) for a in ev.template(s)[1].arcs if a.kind == "move"}
        for ly in lays:
            _inst, lib = ev.layout_pair(ly, s)
            mv = {(a.k, a.kind, a.src, a.dst) for a in lib.arcs if a.kind == "move"}
            assert mv and mv <= tmpl, (s, ly.key(), len(mv - tmpl))
        assert not ev.template(s)[1].infeasible_bikes


def test_hub_slots_prefer_operator_stores_over_docks(tmp_path):
    """2026-10-21: depots (operator stores) fill the max_hub slots before Citi Bike docks."""
    import csv
    rows = []
    for i in range(6):
        rows.append({"id": f"C{i}", "name": f"dock {i}", "lat": 40.720 + 0.004 * i, "lon": -73.995,
                     "site_type": "citibike_charging", "verdict": "confirmed"})
    for i in range(3):
        rows.append({"id": f"P{i}", "name": f"store {i}", "lat": 40.745 + 0.004 * i, "lon": -73.985,
                     "site_type": "depot", "verdict": "confirmed"})
    p = tmp_path / "dot.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    cands, _dropped, info = S.dot_candidates(str(p), max_hub=4, min_hub=1)
    hubs = [c for c in cands if c.hub_capable]
    assert len(hubs) == 4
    assert sum(1 for c in hubs if c.dot_type == "depot") == 3


def test_hub_slot_follows_the_best_merged_hub_type(tmp_path):
    """Review 2026-10-21: an operator store (depot) merged into a pilot row within 80 m keeps the
    pilot survivor hub-capable AND ranked as a depot, so it fills a hub slot ahead of the docks."""
    reg = dn.resolve_region("manhattan_s110")
    box = reg.box

    def at(node, dx, dy=0.0):
        x, y = box.node_xy(node)
        return box.inverse(x + dx, y + dy)
    p_lat, p_lon = at((40, 40), 10.0)
    d_lat, d_lon = at((40, 40), 50.0)                      # 40 m from the pilot row: merged, the pilot wins
    rows = [{"id": "pil", "name": "pilot row", "lat": p_lat, "lon": p_lon, "site_type": "pilot"},
            {"id": "dep", "name": "operator store", "lat": d_lat, "lon": d_lon, "site_type": "depot"}]
    for i in range(4):                                     # four docks with more restaurants at their nodes
        lat, lon = box.node_latlon((20 + 5 * i, 60))
        rows.append({"id": f"dock{i}", "name": f"dock {i}", "lat": lat, "lon": lon, "site_type": "citibike_charging"})
    p = tmp_path / "dot.csv"
    _dot_csv(p, rows)
    rest = _fake_restaurants(box, [(20 + 5 * i, 60) for i in range(4)] * 9)
    cands, _dropped, info = S.dot_candidates(str(p), region=reg, with_lattice=False, restaurants=rest, min_hub=1, max_hub=2)
    by_label = {c.label.split(" [")[0]: c for c in cands}
    pilot = by_label["pilot row"]
    assert "operator store" not in by_label and "operator store" in pilot.merged_labels and pilot.dot_type == "pilot"
    assert info["n_merged"] == 1 and info["n_hub_capable"] == 2
    assert pilot.hub_capable                                # the depot's hub type ranks first
    assert sum(1 for c in cands if c.dot_type == "citibike_charging" and c.hub_capable) == 1


def test_capped_lot_never_holds_a_hub_slot(tmp_path):
    """Adversarial review 2026-10-21: the size cap runs before the hub cap, so a lot removed by
    the cap does not take a hub slot from a kept dock (max_hub hubs remain)."""
    reg = dn.resolve_region("manhattan_s110")
    box = reg.box
    rows = []
    for i in range(2):
        lat, lon = box.node_latlon((40 + 6 * i, 40))
        rows.append({"id": f"lot{i}", "name": f"lot {i}", "lat": lat, "lon": lon, "site_type": "lot"})
    for i in range(2):
        lat, lon = box.node_latlon((20 + 5 * i, 60))
        rows.append({"id": f"dock{i}", "name": f"dock {i}", "lat": lat, "lon": lon, "site_type": "citibike_charging"})
    p = tmp_path / "dot.csv"
    _dot_csv(p, rows)
    rest = _fake_restaurants(box, [(20, 60), (25, 60)] * 3)
    cands, dropped, info = S.dot_candidates(str(p), region=reg, with_lattice=False, restaurants=rest, cap=3,
                                            min_hub=1, max_hub=2)
    assert info["n_candidates"] == 3 and info["n_capped"] == 1
    assert [r["type"] for r in dropped if str(r.get("reason", "")).startswith("cap")] == ["lot"]
    hubs = [c for c in cands if c.hub_capable]
    assert len(hubs) == 2 and sorted(c.dot_type for c in hubs) == ["citibike_charging", "lot"]


# ---------------------------------------------------------------------------
# scenario design
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("S_n", [6, 10, 12, 15])
def test_scenario_design_weights_and_strata(S_n):
    d = S.scenario_design(S_n)
    assert len(d) == S_n and abs(sum(r["p"] for r in d) - 1.0) < 1e-12
    seeds = [r["seed"] for r in d]
    assert seeds == list(range(S_n))
    wk = sum(r["p"] for r in d if r["day_type"] == "weekday")
    assert abs(wk - 5.0 / 7.0) < 1e-12 or S_n == 10
    for r in d:
        assert r["overrides"]["orders_per_bike_hour"] == r["level"]
        if r["day_type"] == "weekend":
            assert r["overrides"]["demand_spec"] == {"profile": "weekend", "day_type": "weekend"}
        else:
            assert "demand_spec" not in r["overrides"]
    if S_n == 12:
        assert sorted({r["stratum"] for r in d}) == list(range(1, 7))
        assert all(abs(r["p"] - (5 / 7 if r["day_type"] == "weekday" else 2 / 7) / 6) < 1e-12 for r in d)
        assert S.lp_scenario_subset(d) == [0, 2, 4, 6, 8, 10]
    held = S.scenario_design(S_n, held_out=True)
    assert [r["seed"] for r in held] == [100 + i for i in range(S_n)]


def test_ci_helpers_match_hand_computation():
    d = [1.0, 3.0, 2.0, 6.0]
    plain = BL.paired_ci(d)
    assert abs(plain["mean"] - 3.0) < 1e-12 and plain["df"] == 3
    sd = np.std(d, ddof=1)
    assert abs(plain["half"] - BL._t975(3) * sd / 2.0) < 1e-9
    strat = BL.stratified_ci(d, ["a", "a", "b", "b"], [0.25, 0.25, 0.25, 0.25])
    # W_a = W_b = 0.5; means 2 and 4; s2_a = 2, s2_b = 8; v_a = 0.25*2/2 = 0.25, v_b = 0.25*8/2 = 1.0;
    # var = 1.25; df_sum = 2; Welch df = 1.25^2 / (0.25^2/1 + 1.0^2/1) = 1.5625 / 1.0625
    assert abs(strat["mean"] - 3.0) < 1e-12 and strat["df_sum"] == 2
    assert abs(strat["df"] - 1.5625 / 1.0625) < 1e-12
    assert abs(strat["half"] - BL._t975(1.5625 / 1.0625) * np.sqrt(1.25)) < 1e-9
    assert abs(strat["half_df_sum"] - BL._t975(2) * np.sqrt(1.25)) < 1e-9


# ---------------------------------------------------------------------------
# parallel pricing
# ---------------------------------------------------------------------------
pytest.importorskip("gurobipy")
from ebike_swap_sim import benders as BD  # noqa: E402


def _rows_sig(res):
    return [(r["scenario"], r["status"], None if r["total"] is None else round(r["total"], 6),
             None if r["bound"] is None else round(r["bound"], 6)) for r in res.rows]


def test_parallel_pricing_contract_against_sequential(tmp_path):
    """Fixer pass (review item 5): the parallel pricing (waves, largest p_s first) has the same
    status as the sequential loop, scenario bounds at least as strong and, when nothing is
    pruned (``PRICED``), identical rows and value; a ``PRUNED_BY_BOUND`` result may hold more or
    stronger rows (stated contract, not a defect).  Several ub_ref thresholds around the values
    of two layouts, both worker counts, and ``lb0`` either trivial or the exact OPEX."""
    ev0 = _toy_ev(relaxed=True)
    lays = [BL.Layout.from_key("T1:SC:B2:C1|T3:S:B1:C0"), BL.Layout.from_key("T2:SC:B1:C1")]
    n_pruned = n_priced = 0
    for i, lay in enumerate(lays):
        exact = ev0.evaluate(lay, "ilp")
        V, opex = exact["V"], [float(x) for x in exact["opex"]]
        setup = lay.allocated_cost(S.TOY_SPEC)
        thresholds = [float("inf"), 1e9, V + 5.0, V + 0.5, V - 0.5, V - 5.0, setup + 1.0]
        for j, ub_ref in enumerate(thresholds):
            for lb0 in ([0.0, 0.0], [opex[0], 0.0]):
                for workers in (2, 3):
                    ev_a = _toy_ev(tmp_path / f"a{i}{j}{workers}{lb0[0]:.1f}", relaxed=True)
                    ev_b = _toy_ev(tmp_path / f"b{i}{j}{workers}{lb0[0]:.1f}", relaxed=True)
                    seq = BD.price_layout(ev_a, lay, lb0, ub_ref, 1e-6)
                    par = BD.price_layout(ev_b, lay, lb0, ub_ref, 1e-6, workers=workers)
                    assert par.status == seq.status and par.tier == seq.tier == "all_candidates", (lay.key(), ub_ref)
                    assert all(a >= b - 1e-6 for a, b in zip(par.lb, seq.lb)), (lay.key(), ub_ref)
                    assert par.setup + sum(p * x for p, x in zip(ev_b.p, par.lb)) <= V + 1e-6     # valid lower bound
                    if par.V is not None:
                        assert par.V >= V - 1e-6                                              # a feasible value
                    if seq.status == "PRICED":
                        n_priced += 1
                        assert seq.V is not None and par.V is not None and abs(seq.V - par.V) < 1e-6 and abs(par.V - V) < 1e-6
                        assert par.ub == seq.ub and _rows_sig(par) == _rows_sig(seq)
                        for k, row in ev_a.cache.items():
                            assert ev_b.cache[k]["status"] == row["status"] and ev_b.cache[k].get("total") == row.get("total")
                    else:
                        n_pruned += 1
                        assert len(par.rows) <= ev0.n_scenarios
    assert n_priced > 0 and n_pruned > 0
    # full=True never prunes: identical to the sequential function
    for lay in lays:
        ev_a = _toy_ev(tmp_path / f"fa{lay.n_open}", relaxed=True)
        ev_b = _toy_ev(tmp_path / f"fb{lay.n_open}", relaxed=True)
        seq = BD.price_layout(ev_a, lay, [0.0, 0.0], float("inf"), 0.0, full=True)
        par = BD.price_layout(ev_b, lay, [0.0, 0.0], float("inf"), 0.0, full=True, workers=2)
        assert seq.status == par.status == "PRICED" and abs(seq.V - par.V) < 1e-6 and _rows_sig(par) == _rows_sig(seq)


# ---------------------------------------------------------------------------
# regional subset bound
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def toy_rel():
    ev = _toy_ev(relaxed=True, cands=CANDS4)
    lps = [BD.ScenarioLP(ev, s, threads=1, relaxed=True) for s in range(ev.n_scenarios)]
    enc = BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, S.TOY_SPEC)
    lays = BL.enumerate_layouts(ev.candidates, enc.options, 2 * UNIT, S.TOY_SPEC, (1, 2), s_needs_charge=True)
    vals = {}
    for l in lays:
        e = ev.evaluate(l, "ilp")
        vals[l.key()] = (e["V"], [None if x is None else float(x) for x in e["opex"]])
    yield ev, lps, enc, lays, vals
    for lp in lps:
        lp.dispose()


def test_subset_bound_valid_monotone_and_equals_superset_at_all(toy_rel):
    ev, lps, enc, lays, vals = toy_rel
    L = ev.superset_bound(method="lp")
    sets = [["T1"], ["T1", "T2"], ["T1", "T2", "T3"], ["T1", "T2", "T3", "T4"], ["T3"], ["T2", "T4"]]
    lba = {}
    for A in sets:
        lba[tuple(A)] = [lps[s].solve_subset(A).Qs for s in range(ev.n_scenarios)]
        for l in lays:
            if set(l.locations()) <= set(A):
                V, opex = vals[l.key()]
                if V is None or V == BL.INF:
                    continue
                for s in range(ev.n_scenarios):
                    assert lba[tuple(A)][s] <= opex[s] + 1e-6, (A, l.key(), s)
                    r = lps[s].solve(enc.x_of_layout(l))
                    assert lba[tuple(A)][s] <= r.Qt + 1e-6
    for s in range(ev.n_scenarios):
        assert abs(lba[("T1", "T2", "T3", "T4")][s] - L[s]) <= 1e-5 * max(1.0, abs(L[s]))
        assert lba[("T1",)][s] >= lba[("T1", "T2")][s] - 1e-6 >= lba[("T1", "T2", "T3")][s] - 2e-6
    # the subset cut holds at every integer point (inside and outside A)
    master = BD.Master(enc, ev.p, L, s_needs_charge=True, threads=1)
    for A in sets:
        for s in range(ev.n_scenarios):
            cut = BD.Cut(kind="subset", target="relaxed", scenario=s, c0=lba[tuple(A)][s], L=L[s], meta={"atoms": list(A)})
            const, a = cut.linear(enc)
            for l in lays:
                V, opex = vals[l.key()]
                if V is None or V == BL.INF:
                    continue
                w = enc.w_of(l)
                assert const + float(a @ w) <= opex[s] + 1e-6, (A, l.key())
            assert master.add_cut(cut)


def test_free_size_point_is_valid_with_transfers_at_K_equal_Bmax(toy_rel):
    """Design 7.1 item 1: with transfer services and ``K = B_max`` (TOY_SPEC: ``K = 2``, SC ``B in
    {1, 2}``, shuttles between every charge- / swap-capable pair) the bound uses FREE sizes.  The
    free-size point is a lower bound on every layout's LP and ILP value (asserted on every
    cell), it is at most the max-size point (free sizes contain the max sizes) and layouts of
    the toy do use transfers.  Note (recorded in DECISIONS): an exhaustive search over the toy
    seeds found no cell where the max-size point exceeds a layout's LP value -- the model lets a
    site ship empties out before receiving and hubs sit at ``B = 0`` -- so the max-size point's
    invalidity cannot be exhibited on this toy; the free-size point is used because its validity
    follows from monotonicity in ``y`` alone, which the max-size point lacks."""
    ev, lps, enc, lays, vals = toy_rel
    A = ["T1", "T2", "T3", "T4"]
    free = [lps[s].solve_subset(A).Qs for s in range(ev.n_scenarios)]
    x_max = {}
    for l in A:
        for r in enc.roles:
            fid = S.facility_id(l, r)
            x_max[fid] = (1.0, float(S.TOY_SPEC.K), float(S.TOY_SPEC.c_max(r)))
    at_max = [lps[s].solve(x_max).Qt for s in range(ev.n_scenarios)]
    assert S.TOY_SPEC.K == max(B for B, _C in MENU["SC"])
    assert all(free[s] <= at_max[s] + 1e-6 for s in range(ev.n_scenarios))
    n_transfer_layouts = 0
    for l in lays:
        V, opex = vals[l.key()]
        if V is None or V == BL.INF:
            continue
        inst, _lib = ev.layout_pair(l, 0)
        if inst.services:
            n_transfer_layouts += 1
        for s in range(ev.n_scenarios):
            assert free[s] <= opex[s] + 1e-6
            assert free[s] <= lps[s].solve(enc.x_of_layout(l)).Qt + 1e-6
    assert n_transfer_layouts > 0
    e = ev.evaluate(BL.Layout.from_key("T1:SC:B1:C1|T4:SC:B1:C1"), "ilp")
    assert e["rows"][0]["n_services"] > 0


def test_setup_min_hand_values():
    enc = BD.MenuEncoding(["T1", "T2", "T3"], MENU, S.ROLES, S.TOY_SPEC)
    sp = S.TOY_SPEC
    sc11 = sp.F + sp.bB * 1 + sp.bC * 1
    s1 = sp.F + sp.bB * 1
    assert BD.setup_min(enc, 1, ["T1"]) == pytest.approx(sc11)              # S alone needs a charge object
    assert BD.setup_min(enc, 2, ["T1", "T2"]) == pytest.approx(s1 + min(sc11, sp.F_hub + sp.bC))
    assert BD.setup_min(enc, 3, ["T1", "T2"]) == BL.INF
    enc2 = BD.MenuEncoding(["T1", "T2"], MENU, S.ROLES, S.TOY_SPEC, roles_of={"T1": ("S", "SC"), "T2": ("S", "SC")})
    assert BD.setup_min(enc2, 2, ["T1", "T2"]) == pytest.approx(s1 + sc11)   # no hub without a hub-capable site
    assert "T1:C" not in enc2.objects and all(o[0] != "C" for _l, o in enc2.index)


def test_master_restrict_fixes_other_locations():
    ev = _toy_ev(relaxed=True)
    enc = BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, S.TOY_SPEC)
    master = BD.Master(enc, ev.p, [0.0, 0.0], s_needs_charge=True, threads=1)
    master.restrict(["T1", "T2"])
    res = master.solve(2 * UNIT)
    assert res["layout"] is not None and set(res["layout"].locations()) <= {"T1", "T2"}
    assert not master.rows_ok(BL.Layout.from_key("T3:SC:B1:C1"))
    master.restrict(None)
    assert master.rows_ok(BL.Layout.from_key("T3:SC:B1:C1"))
    master.dispose()


# ---------------------------------------------------------------------------
# branch-and-bound on the toy, resume, two-tier pricing
# ---------------------------------------------------------------------------
def _cert(ev, pool, records, budgets, **kw):
    cert = BD.SitingCertifier(ev, budgets, MENU, S.ROLES, s_needs_charge=True, pool=pool, tol_rel=1e-9, tol_abs=1e-6,
                              lp_threads=1, master_threads=1, on_record=records.append, price_workers=2, **kw)
    return cert


def test_bnb_returns_exhaustive_optimum_and_resumes(tmp_path, toy_rel):
    ev0, _lps, enc, lays, vals = toy_rel
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    budgets = [UNIT, 2 * UNIT]
    best = {}
    for b in budgets:
        best[b] = min((v[0], k) for k, v in vals.items() if BL.Layout.from_key(k).investment(S.TOY_SPEC) <= b + 1e-6 and v[0] is not None)
    pool = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
    records = []
    cert = _cert(ev, pool, records, budgets)
    cert.warm_start([BL.Layout.from_key("T2:SC:B1:C1"), BL.Layout.from_key("T2:SC:B1:C1|T4:S:B1:C0")])
    levels1 = [LEVELS4[1]]
    # a single B&B pass (exactly one open location, no window) is a certificate of m = 1 on its own
    bb1 = BD.SubsetBranchAndBound(cert, 1, UNIT, levels1, S_LP=[0], lb_smaller=BL.INF, label="m1")
    r1 = bb1.run()
    assert cert.UB[UNIT] == pytest.approx(best[UNIT][0], abs=1e-6)
    assert r1["LB"] <= best[UNIT][0] + 1e-6 and r1["certified"] and r1["stop_reason"] == "complete"
    # m = 2 through the driver: window (UNIT, 2 UNIT] for k = 1 (enumeration) and k = 2 (B&B pass)
    r2 = BD.certify_bnb(cert, 2, 2 * UNIT, LEVELS4, S_LP=[0], lb_smaller=cert.LB[UNIT], budget_smaller=UNIT, label="m2")
    assert cert.UB[2 * UNIT] == pytest.approx(best[2 * UNIT][0], abs=1e-6)
    assert r2["LB"] <= best[2 * UNIT][0] + 1e-6 and r2["certified"] and r2["stop_reason"] == "complete"
    assert [p["k"] for p in r2["passes"]] == [1, 2] and r2["passes"][0]["method"] == "enumeration"
    assert r2["passes"][0]["n_layouts"] == 0                 # UNIT = 130 >= every one-site investment: empty window
    assert r2["n_nodes"] >= 3 and any(c.kind == "subset" for c in pool.cuts)
    # every m = 2 leaf / node is covered: brute force over the 2-site layouts
    thr = cert.UB[2 * UNIT] - cert.tol(cert.UB[2 * UNIT])
    for l in lays:
        if l.n_open != 2:
            continue
        pr = cert.priced.get(l.key())
        lo = max(cert.master.envelope(l), pr.lower if pr is not None else -BL.INF)
        assert lo >= thr - 1e-6 or (pr is not None and pr.status == "INFEASIBLE") or lo >= vals[l.key()][0] - 1e-6 or \
            vals[l.key()][0] >= thr - 1e-6
    res = cert.finish()
    assert res[2 * UNIT]["certified"] and res[UNIT]["certified"]
    n_lp = cert.counters["subset_lps"]
    # resume: a fresh certifier on the same pool and records solves no subset LP again
    pool2 = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
    records2 = []
    cert2 = _cert(ev, pool2, records2, budgets)
    cert2.restore(records)
    assert cert2.restored["subset_bounds"] > 0 and cert2.restored["priced"] > 0
    r2b = BD.certify_bnb(cert2, 2, 2 * UNIT, LEVELS4, S_LP=[0], lb_smaller=cert2.LB[UNIT] if cert2.LB[UNIT] > -BL.INF else r1["LB"],
                         budget_smaller=UNIT, label="m2r")
    assert cert2.counters["subset_lps"] == 0 and cert2.counters["ilp_solves"] == 0
    assert abs(r2b["LB"] - r2["LB"]) < 1e-6 and r2b["certified"]
    assert n_lp > 0
    cert.close()
    cert2.close()


@pytest.mark.parametrize("F", [2.0, 30.0, 60.0])
def test_bnb_window_covers_layouts_with_fewer_sites_above_the_smaller_budget(tmp_path, F):
    """Review blocker: with UNIT = 125 the one-site layout SC:B2:C1 (investment 130) is admissible
    at budget 2 only; the old m = 2 certificate bounded layouts with exactly two sites and relied
    on LB_1 for the rest, so with a large set-up F (a second site never pays) it reported LB = UB
    above the exhaustive optimum.  The driver's window pass k = 1 covers it: LB <= V* and UB = V*."""
    import dataclasses
    unit = 125.0
    spec = dataclasses.replace(S.TOY_SPEC, F=F)
    scen = [S.toy_base_instance(0, candidates=CANDS4), S.toy_base_instance(1, candidates=CANDS4)]
    ev = BL.LowerLevelEvaluator(scen, spec, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                cache_dir=str(tmp_path / "cache")).derive(relaxed_targets=True)
    enc = BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, spec)
    lays = BL.enumerate_layouts(ev.candidates, enc.options, 2 * unit, spec, (1, 2), s_needs_charge=True)
    vals = {l.key(): ev.evaluate(l, "ilp")["V"] for l in lays}
    best = {}
    for b in (unit, 2 * unit):
        best[b] = min((v, k) for k, v in vals.items() if v is not None and v != BL.INF
                      and BL.Layout.from_key(k).investment(spec) <= b + 1e-6)
    window1 = [k for k in vals if BL.Layout.from_key(k).n_open == 1 and unit < BL.Layout.from_key(k).investment(spec) <= 2 * unit]
    assert len(window1) == 4 and all(k.endswith("SC:B2:C1") for k in window1)
    assert BD.setup_min(enc, 1, ["T1", "T2"], True, unit, 2 * unit) == pytest.approx(spec.setup_cost("SC") + 2 * spec.bB + spec.bC)
    assert BD.setup_min(enc, 1, ["T1", "T2"], True, 2 * unit, 3 * unit) == BL.INF
    pool = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
    records = []
    cert = BD.SitingCertifier(ev, [unit, 2 * unit], MENU, S.ROLES, s_needs_charge=True, pool=pool, tol_rel=1e-9, tol_abs=1e-6,
                              lp_threads=1, master_threads=1, on_record=records.append, price_workers=1)
    cert.warm_start([BL.Layout.from_key("T2:SC:B1:C1"), BL.Layout.from_key("T2:SC:B1:C1|T4:S:B1:C0")])
    r1 = BD.certify_bnb(cert, 1, unit, [LEVELS4[1]], S_LP=[0], label="m1")
    assert r1["certified"] and r1["LB"] <= best[unit][0] + 1e-6 and cert.UB[unit] == pytest.approx(best[unit][0], abs=1e-6)
    r2 = BD.certify_bnb(cert, 2, 2 * unit, LEVELS4, S_LP=[0], lb_smaller=cert.LB[unit], budget_smaller=unit, label="m2")
    assert r2["passes"][0] == {**r2["passes"][0], "k": 1, "method": "enumeration", "n_layouts": 4}
    assert cert.UB[2 * unit] == pytest.approx(best[2 * unit][0], abs=1e-6), (cert.best[2 * unit].key(), best[2 * unit])
    assert r2["LB"] <= best[2 * unit][0] + 1e-6 and r2["certified"]
    res = cert.finish()
    assert res[2 * unit]["certified"] and res[2 * unit]["LB"] <= best[2 * unit][0] + 1e-6
    assert res[2 * unit]["best_layout"] == best[2 * unit][1]
    cert.close()


def test_bnb_window_m3_covers_two_site_layouts_above_budget_two(tmp_path):
    """The k = 2 window of the m = 3 certificate: with UNIT = 125 the pair SC:B2:C1 | SC:B2:C1
    (investment 260) is admissible at budget 3 only; the m = 3 certificate must bound it (k = 2
    pass with the window (250, 375]) besides the three-site layouts (k = 3) and LB_2."""
    import dataclasses
    unit = 125.0
    spec = dataclasses.replace(S.TOY_SPEC, F=30.0)
    scen = [S.toy_base_instance(0, candidates=CANDS4), S.toy_base_instance(1, candidates=CANDS4)]
    ev = BL.LowerLevelEvaluator(scen, spec, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                cache_dir=str(tmp_path / "cache")).derive(relaxed_targets=True)
    enc = BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, spec)
    budgets = [unit, 2 * unit, 3 * unit]
    lays = BL.enumerate_layouts(ev.candidates, enc.options, 3 * unit, spec, (1, 2, 3), s_needs_charge=True)
    vals = {l.key(): ev.evaluate(l, "ilp")["V"] for l in lays}
    best = {b: min((v, k) for k, v in vals.items() if v is not None and v != BL.INF
                   and BL.Layout.from_key(k).investment(spec) <= b + 1e-6) for b in budgets}
    w2 = [k for k in vals if BL.Layout.from_key(k).n_open == 2 and 2 * unit < BL.Layout.from_key(k).investment(spec) <= 3 * unit]
    assert w2 and all(k.count("SC:B2:C1") == 2 for k in w2)
    pool = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
    records = []
    cert = BD.SitingCertifier(ev, budgets, MENU, S.ROLES, s_needs_charge=True, pool=pool, tol_rel=1e-9, tol_abs=1e-6,
                              lp_threads=1, master_threads=1, on_record=records.append, price_workers=1)
    cert.warm_start([BL.Layout.from_key("T2:SC:B1:C1"), BL.Layout.from_key("T2:SC:B1:C1|T4:S:B1:C0")])
    BD.certify_bnb(cert, 1, unit, [LEVELS4[1]], S_LP=[0], label="m1")
    BD.certify_bnb(cert, 2, 2 * unit, LEVELS4, S_LP=[0], lb_smaller=cert.LB[unit], budget_smaller=unit, label="m2")
    r3 = BD.certify_bnb(cert, 3, 3 * unit, LEVELS4, S_LP=[0], lb_smaller=cert.LB[2 * unit], budget_smaller=2 * unit, label="m3")
    assert [p["k"] for p in r3["passes"]] == [1, 2, 3] and r3["passes"][1]["method"] == "bnb" and r3["passes"][1]["n_nodes"] >= 1
    assert r3["passes"][0]["n_layouts"] == 0                        # no one-site layout above 250
    for b in budgets:
        assert cert.UB[b] == pytest.approx(best[b][0], abs=1e-6), (b, cert.best[b].key(), best[b])
        assert cert.LB[b] <= best[b][0] + 1e-6, (b, cert.LB[b], best[b])
    assert r3["certified"] and r3["LB"] <= best[3 * unit][0] + 1e-6
    res = cert.finish()
    assert all(res[b]["certified"] for b in budgets)
    cert.close()


def test_bnb_max_level_keeps_nodes_open_at_their_bound(tmp_path, toy_rel):
    """``max_level`` (the --bnb-levels-m3 switch) stops the refinement: a complete run with open
    unrefined nodes, a valid (weaker) floor, no leaf pricing below that level."""
    ev0, _lps, enc, lays, vals = toy_rel
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    pool = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
    records = []
    cert = _cert(ev, pool, records, [UNIT, 2 * UNIT])
    cert.warm_start([BL.Layout.from_key("T2:SC:B1:C1|T4:S:B1:C0")])
    bb = BD.SubsetBranchAndBound(cert, 2, 2 * UNIT, LEVELS4, S_LP=[0], lb_smaller=BL.INF, label="m2", max_level=0,
                                 update_lb=False)
    r = bb.run()
    assert r["stop_reason"].startswith("complete") and r["n_leaves"] == 0 and r["n_unrefined"] + r["n_pruned"] + r["n_empty"] == r["n_nodes"]
    assert r["n_unrefined"] >= 1 and all(n["level"] == 0 for n in r["open_nodes"])
    best2 = min(v[0] for k, v in vals.items() if v[0] is not None and BL.Layout.from_key(k).investment(S.TOY_SPEC) <= 2 * UNIT + 1e-6)
    assert r["LB_floor_m"] <= best2 + 1e-6 and r["update_lb"] is False and cert.LB[2 * UNIT] == -BL.INF
    cert.close()


def test_two_tier_pricing_never_feeds_cuts_or_priced(tmp_path):
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    pool = BD.CutPool(None, BD.pool_signature(ev))
    records = []
    cert = _cert(ev, pool, records, [UNIT])
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    n_cuts = len(pool.cuts)
    r = cert.price(lay, tier="open_sites", tag="t")
    assert r.tier == "open_sites" and r.V is not None
    assert lay.key() not in cert.priced and lay.key() in cert.priced_open and len(pool.cuts) == n_cuts
    assert cert.UB[UNIT] == pytest.approx(r.V) and records[-1]["kind"] == "price_open"
    r2 = cert.price(lay, tag="t", full=True)
    assert r2.tier == "all_candidates" and r2.V <= r.V + 1e-6 and lay.key() in cert.priced
    assert set(ev.cache) and all(row["reposition"] in ("all_candidates", "open_sites") for row in ev.cache.values())
    assert any(row["reposition"] == "open_sites" for row in ev.cache.values())
    cert.close()


def test_lp_per_location_runs_once_per_location(tmp_path):
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    pool = BD.CutPool(None, BD.pool_signature(ev))
    records = []
    cert = _cert(ev, pool, records, [UNIT])
    vals = cert.lp_per_location()
    assert set(vals) == {"T1", "T2", "T3", "T4"} and cert.counters["lp_locations"] == 4
    vals2 = cert.lp_per_location()
    assert vals2 == vals and cert.counters["lp_locations"] == 4
    e = cert.certify_by_enumeration(UNIT, force_lp_per_location=True)
    assert e["done"] and e.get("lp_per_location") == 4
    cert.close()


# ---------------------------------------------------------------------------
# CLI: smoke run, lanes
# ---------------------------------------------------------------------------
def _run(args, cwd=ROOT, timeout=900):
    return subprocess.run([sys.executable, "experiments/r7_siting.py"] + args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)


def test_cli_smoke_all_stages_and_lane_writer(tmp_path):
    out = tmp_path / "smoke"
    r = _run(["--smoke", "--stage", "all", "--out-dir", str(out)])
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    recs = C.load_jsonl(str(out / "records.jsonl"))
    kinds = {x.get("kind") for x in recs}
    for k in ("plan", "budget_result", "bnb_done", "bnb_certificate", "restricted_result", "baseline", "role_table",
              "oos_result", "acceptance", "sizes"):
        assert k in kinds, k
    rr = [x for x in recs if x.get("kind") == "restricted_result"]
    for x in rr:                                   # DOT-only bounds sit above the full bounds and never cross
        assert x["LB"] is not None and x["UB"] is not None and x["LB"] <= x["UB"] + 1e-6
        assert x["UB"] >= x["UB_full"] - 1e-6 and x["LB"] >= x["LB_full"] - 1e-6
    txt_res = (out / "RESULTS.md").read_text()
    assert "## T3 -- DOT-only vs full" in txt_res and "## T4 -- role table" in txt_res
    acc = [x for x in recs if x.get("kind") == "acceptance"]
    assert acc and all(a.get("ok") for a in acc), acc
    assert os.path.exists(out / "RESULTS.md") and os.path.exists(out / "candidates.csv")
    r2 = _run(["--smoke", "--stage", "all", "--out-dir", str(out), "--dry-run"])
    assert r2.returncode == 0
    lanes = tmp_path / "lanes"
    r3 = _run(["--smoke", "--write-lanes", "--out-dir", str(out), "--lanes-dir", str(lanes), "--vcpu", "16"])
    assert r3.returncode == 0, r3.stderr[-2000:]
    txt = (lanes / "lanes.txt").read_text().splitlines()
    rows = [ln.split("\t") for ln in txt if ln and not ln.startswith("#")]
    assert rows and all(len(r) == 4 for r in rows)
    names = [r[0] for r in rows]
    meta = json.loads((lanes / "lanes.json").read_text())
    for name, thr, after, cmd in rows:
        assert thr.isdigit() and int(thr) <= meta["usable_threads"]
        assert after == "-" or all(a in names for a in after.split(","))
        assert "r7_siting.py" in cmd
        toks = cmd.split()
        lp_w, lp_t, pr_w, thr_ilp, mst, mx = (int(toks[toks.index(f) + 1]) for f in
                                             ("--lp-workers", "--lp-threads", "--price-workers", "--threads", "--master-threads",
                                              "--max-threads"))
        # review item 2: every lane declares the threads its own pools open
        assert lp_w * lp_t + mst <= int(thr) and pr_w * thr_ilp <= int(thr) and mx == int(thr), (name, cmd)
        assert "--restrict dot" in cmd or name.endswith("analyse") or name.endswith("setup")
    assert names[0].endswith("setup") and "r7_restricted" in names
    r4 = _run(["--write-lanes", "--vcpu", "16", "--lanes-dir", str(tmp_path / "lanes16"), "--out-dir", str(out)])
    assert r4.returncode == 0, r4.stderr[-2000:]
    rows16 = [ln.split("\t") for ln in (tmp_path / "lanes16" / "lanes.txt").read_text().splitlines() if ln and not ln.startswith("#")]
    par = [r for r in rows16 if r[2] == "r7_polish"]
    assert len(par) == 5 and sum(int(r[1]) for r in par) <= 2 * 12            # 4 + 4 + 4 + 4 + 4 at 16 vCPU: never 36 threads
    for name, thr, after, cmd in rows16:
        toks = cmd.split()
        lp_w, lp_t, pr_w, thr_ilp, mst, mx = (int(toks[toks.index(f) + 1]) for f in
                                             ("--lp-workers", "--lp-threads", "--price-workers", "--threads", "--master-threads",
                                              "--max-threads"))
        assert lp_w * lp_t + mst <= int(thr) and pr_w * thr_ilp <= int(thr) and mx == int(thr), (name, cmd)
    # any three of the parallel lanes together stay within the 12-thread budget of the dispatcher
    assert max(int(r[1]) for r in par) * 3 <= 12


def test_bb3_plan_reports_the_levels_visited(tmp_path):
    """Review item 6: --bnb-levels-m3 now truncates the refinement (plan record 'levels' and 'max_level')."""
    from experiments import r7_siting as R
    recs = []
    for lv, exp_levels, exp_max in ((1, [2], 0), (2, [2, 4], None), (5, [2, 4], None)):
        args = R.parse_args(["--smoke", "--dry-run", "--stage", "bb3", "--budgets", "1", "2", "3", "--bnb-levels-m3", str(lv),
                             "--out-dir", str(tmp_path / f"d{lv}")])
        run = R.Run(args)
        ctx = R.Ctx(run)
        plan = R.stage_bnb(run, ctx, 3)
        ctx.close()
        assert plan["kind"] == "bb3_plan" and plan["levels"] == exp_levels and plan["max_level"] == exp_max, (lv, plan)
        assert plan["levels_all"] == [2, 4] and plan["passes"] == [1, 2, 3] and plan["window"][0] == pytest.approx(2 * R.TOY_UNIT)
        recs.append(plan)


def test_lane_writer_fits_workers_to_16_and_32_vcpu():
    from experiments import r7_siting as R
    a16 = R.parse_args(["--write-lanes", "--vcpu", "16"])
    assert a16.max_threads is not None
    assert R.fit_workers(a16, 12) == (5, 4)          # 5 x 2 + 2 = 12; 4 x 3 = 12
    a32 = R.parse_args(["--write-lanes", "--vcpu", "32"])
    assert R.fit_workers(a32, 24) == (11, 8)         # 11 x 2 + 2 = 24; 8 x 3 = 24


def test_r6_o2_thread_cap_is_the_max_threads_budget():
    """The hard-coded laptop cap (12) of r6_o2_siting is gone: the budget is --max-threads."""
    import argparse
    from experiments import r6_o2_siting as O2
    assert O2.default_max_threads() >= 1
    ns = argparse.Namespace(lp_workers=7, lp_threads=2, master_threads=2, max_threads=20)
    assert O2.check_thread_budget(ns) == 20                      # 16 > 12 would have failed before
    with pytest.raises(SystemExit):
        O2.check_thread_budget(argparse.Namespace(lp_workers=7, lp_threads=2, master_threads=2, max_threads=8))
    ns = argparse.Namespace(lp_workers=1, lp_threads=1, master_threads=1, max_threads=None)
    assert O2.check_thread_budget(ns) == O2.default_max_threads()


def test_hub_capable_set_enters_pool_bound_and_config_keys_only_when_restricted(tmp_path):
    """Review 2026-10-21 (major): the hub-capable set (``roles_of``) is a component of the cut-pool
    signature, the superset-bound key and ``config_md5`` when some location lacks the hub role,
    and absent otherwise (older families byte-identical)."""
    from experiments import r7_siting as R
    ev = _toy_ev()
    assert ev.roles_signature() is None and "roles_of" not in ev.superset_bound_key_parts()
    old_pool = BL._md5({"o2": BD.O2_VERSION, "cache": BL.CACHE_VERSION, "family": ev.family, "seeds": ev.seeds,
                        "demand": ev.demand_md5, "prices": [CM.pricing_cache_component(i) for i in ev.scenarios],
                        "spec": ev.spec.to_dict(), "pruning": [ev.pruning_signature(s) for s in range(ev.n_scenarios)],
                        "reposition": ev.reposition, "lp": "aggregated", "M_el": float(BD.M_EL)})
    assert BD.pool_signature(ev) == old_pool
    # T3 not hub-capable
    scen = [S.toy_base_instance(0, candidates=CANDS4), S.toy_base_instance(1, candidates=CANDS4)]
    for inst in scen:
        for rec in inst.meta["candidates"]:
            if rec["id"] == "T3":
                rec["hub_capable"] = False
    ev_h = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True)
    assert ev_h.roles_of["T3"] == ("S", "SC")
    sig = ev_h.roles_signature()
    assert sig == [["T1", ["S", "C", "SC"]], ["T2", ["S", "C", "SC"]], ["T3", ["S", "SC"]], ["T4", ["S", "C", "SC"]]]
    parts_h, parts = ev_h.superset_bound_key_parts(), ev.superset_bound_key_parts()
    assert parts_h.pop("roles_of") == sig and parts_h == parts      # the only difference
    assert BD.pool_signature(ev_h) != BD.pool_signature(ev)
    ev_h.roles_signature = lambda: None                              # without the component: same signature
    assert BD.pool_signature(ev_h) == BD.pool_signature(ev)
    # config_md5 of the r7 driver (toy smoke context)
    args = R.parse_args(["--smoke", "--dry-run", "--stage", "setup", "--out-dir", str(tmp_path / "cfg")])
    ctx = R.Ctx(R.Run(args))
    try:
        assert ctx.ev.roles_signature() is None
        old_cfg = BL._md5({"family": ctx.family, "seeds": ctx.ev.seeds, "demand": ctx.ev.demand_md5, "p": ctx.p,
                           "spec": ctx.spec.to_dict(), "menu": {k: [list(x) for x in v] for k, v in ctx.menu.items()},
                           "budgets": ctx.budgets, "candidates": ctx.ids, "pruning": ctx.ev.pruning_signature(0),
                           "prices": [CM.pricing_cache_component(i) for i in ctx.scen]})
        assert ctx.config_md5() == old_cfg
        ctx.ev.roles_of = {**ctx.ev.roles_of, ctx.ids[0]: ("S", "SC")}
        assert ctx.ev.roles_signature() is not None and ctx.config_md5() != old_cfg
    finally:
        ctx.close()


R6_O2_INDEX = os.path.join(ROOT, "outputs", "r6_o2", "manhattan_pass2", "cache", "index.jsonl")


@pytest.mark.skipif(not (os.environ.get("R7_REPRO") and os.path.exists(R6_O2_INDEX)),
                    reason="set R7_REPRO=1 with outputs/r6_o2/manhattan_pass2 present (about 1 min, NYC data)")
def test_r5_manhattan_cache_keys_reproduced_through_the_r7_path(tmp_path):
    """Design 5.1 step 1: --family r5_manhattan --menu full --scenarios 0 --seeds 0 1 2 reproduces every
    cache key of the second-pass Manhattan run (ILP, baseline and selfish rows, both targets)."""
    from experiments import r7_siting as R
    args = R.parse_args(["--family", "r5_manhattan", "--menu", "full", "--scenarios", "0", "--seeds", "0", "1", "2",
                         "--stage", "setup", "--dry-run", "--out-dir", str(tmp_path), "--max-threads", "4",
                         "--lp-workers", "1", "--price-workers", "1"])
    ctx = R.Ctx(R.Run(args))
    rows = C.load_jsonl(R6_O2_INDEX)
    miss = []
    for r in rows:
        ev = ctx.ev if r.get("relaxed_targets", True) else ctx.ev_written
        if ev.cache_key(BL.Layout.from_key(r["layout_key"]), int(r["scenario"]), r["policy"]) != r["key"]:
            miss.append((r["layout_key"], r["scenario"], r["policy"]))
    assert rows and not miss, miss[:5]
    assert ctx.ev.demand_md5 == [md5 for _s, md5 in sorted({(int(x["scenario"]), x["demand_md5"]) for x in rows})]


def test_p_kw_variant_changes_site_power_and_cache_key(tmp_path):
    """Hub-economics setting (i): the P_kw variant caps the site power of (20) per role object
    (data only) and enters the cache key; unknown keys are still rejected."""
    ev = BL.LowerLevelEvaluator([S.toy_base_instance(0, candidates=CANDS4)], S.TOY_SPEC, cache_dir=str(tmp_path),
                                relaxed_targets=True, threads=1, params=PARAMS, aggregate=True)
    lay = BL.Layout.of([("T1", "SC", 1, 1), ("T3", "C", 0, 1)])
    ev2 = ev.derive(variant={"P_kw": {"SC": 0.7, "C": 2.8}})
    inst = ev2._layout_instance(lay, 0)
    pk = {S.split_facility_id(f.id)[1]: f.P_kw for f in inst.facilities}
    assert pk == {"SC": 0.7, "C": 2.8}
    base = {S.split_facility_id(f.id)[1]: f.P_kw for f in ev._layout_instance(lay, 0).facilities}
    assert base == {"SC": S.TOY_SPEC.P_kw, "C": S.TOY_SPEC.P_kw}
    assert ev2.cache_key(lay, 0, "ilp") != ev.cache_key(lay, 0, "ilp")
    with pytest.raises(ValueError):
        ev.derive(variant={"bogus": 1})


def test_probe_summary_only_driver_setup_dirs_and_flags_stale(tmp_path):
    """Adversarial review 2026-10-21: summary reads only dot_N<N>_S<SCEN> dirs, tags their radius
    convention, and drops per-scenario fixed-layout times whose LP has artificial > 0."""
    from experiments import r7_probe as RP

    def setup_dir(name, pruning, artificial=(0.0, 0.0)):
        d = tmp_path / name
        d.mkdir()
        plan = {"kind": "plan", "n_candidates": 6, "pruning": pruning, "config_md5": "x", "approach_radius": 14}
        sizes = {"kind": "sizes", "templates": [], "timings": {
            "one_site": {"layout": "a", "runtime_s": [1.0, 2.0], "artificial": list(artificial)},
            "two_site": {"layout": "a|b", "runtime_s": [2.0, 4.0], "artificial": list(artificial)},
            "one_cell_free": {"n_locations": 2}, "all_open_free": {"n_locations": 6}}}
        subs = [{"kind": "subset_lp", "tag": "size", "scenario": s, "atoms": list(range(6)), "runtime_s": 8.0}
                for s in (0, 1)]
        with open(d / "records.jsonl", "w", encoding="utf-8") as fh:
            for r in [plan, sizes] + subs:
                fh.write(json.dumps(r) + "\n")
    rad = {"reposition_target_radius": [["(1, 1)", 14]]}
    setup_dir("dot_N6_S6", {**rad, "reposition_radius_exempt_states": [["(0, 0)", 3]]}, artificial=(0.0, 5.0))
    setup_dir("dot_N40_S6", {**rad, "reposition_radius_exempt_tails": ["(0, 0)"]})
    setup_dir("dot_N40", {**rad})                       # old naming: ignored
    setup_dir("laptop_smoke_N6", {**rad})               # laptop smoke: ignored
    res = RP.main(["summary", "--out", str(tmp_path)])
    assert sorted(res["setup"]) == ["dot_N40_S6", "dot_N6_S6"]
    assert res["setup"]["dot_N6_S6"]["radius_convention"] == "exempt_states" and not res["setup"]["dot_N6_S6"]["stale"]
    assert res["setup"]["dot_N40_S6"]["stale"] and res["setup_stale"] == ["dot_N40_S6"]
    sub = res["setup"]["dot_N6_S6"]["subset_lp_size"]
    assert [x["ratio_subset_to_two_site"] for x in sub] == [4.0, None]     # scenario 1: artificial > 0
    assert res["setup"]["dot_N6_S6"]["fixed_layout_artificial_scenarios"] == {"one_site": [1], "two_site": [1]}


# ---------------------------------------------------------------------------
# R7 production code (notes/siting_production_plan.md section 5 items 1-4, 2026-10-21)
# ---------------------------------------------------------------------------
def _row_cmp(row):
    """Solver-independent identity of a cache row (no run times, no paths)."""
    def r9(x):
        return None if x is None else round(float(x), 9)
    return (row.get("key"), row.get("status"), r9(row.get("total")), r9(row.get("opex")), r9(row.get("bound")),
            row.get("feasible"), row.get("n_arcs"))


def test_one_site_terminal_feasibility_does_not_depend_on_sizes():
    """Item 4: terminal feasibility of a one-site layout depends on the open swap object only,
    never on (B, C): every SC size of a wider menu (K = 4, Cbar = 2), both targets, both
    scenarios, the default toy (T4 infeasible) and the far-start toy under radius 0 (other
    locations infeasible in one scenario only); the evaluator returns INFEASIBLE_TERMINAL for
    exactly those layouts."""
    import dataclasses
    spec = dataclasses.replace(S.TOY_SPEC, K=4, Cbar=2)
    sizes = [(B, C) for B in range(1, 5) for C in (1, 2)]
    worlds = [([S.toy_base_instance(0, candidates=CANDS4), S.toy_base_instance(1, candidates=CANDS4)], None),
              (_toy_far_starts(q0=1), {"approach_radius_blocks": 0})]
    n_inf = n_feas = 0
    patterns = set()
    for scen, pruning in worlds:
        ev = BL.LowerLevelEvaluator(scen, spec, time_limit=30.0, threads=1, params=PARAMS, aggregate=True, pruning=pruning)
        for ev_t in (ev.derive(relaxed_targets=True), ev):
            for l, _n in CANDS4:
                for s in range(2):
                    got = {(B, C): tuple(BD.verify_terminal_infeasible(ev_t, BL.Layout.of([(l, "SC", B, C)]), s))
                           for B, C in sizes}
                    assert len(set(got.values())) == 1, (l, s, got)
                    inf = next(iter(got.values()))
                    patterns.add((l, s, bool(inf)))
                    n_inf += int(bool(inf))
                    n_feas += int(not inf)
                    row = ev_t.evaluate_scenario(BL.Layout.of([(l, "SC", 4, 2)]), s, "ilp")
                    assert (row["status"] == BL.INFEASIBLE_TERMINAL) == bool(inf), (l, s, row["status"])
    assert n_inf > 0 and n_feas > 0
    # some location is infeasible in one scenario and feasible in the other (a per-scenario proof)
    assert any((l, 0, True) in patterns and (l, 1, False) in patterns or (l, 1, True) in patterns and (l, 0, False) in patterns
               for l, _n in CANDS4)


def test_terminal_marks_skip_lp_and_ilp_and_never_cut_a_feasible_layout(tmp_path):
    """Item 4: a location proven terminal-infeasible gets every one-site size option marked
    INFEASIBLE_TERMINAL with no LP and no ILP, and the master row it adds (the terminal row,
    which implies the window row y_l <= sum_{l' != l} y_l') excludes only layouts with V = inf:
    checked against the exhaustive values of every layout within 3 budget units."""
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    enc = BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, S.TOY_SPEC)
    lays = BL.enumerate_layouts(ev.candidates, enc.options, 3 * UNIT, S.TOY_SPEC, (1, 2, 3), s_needs_charge=True)
    vals = {l.key(): ev.evaluate(l, "ilp")["V"] for l in lays}
    pool = BD.CutPool(None, BD.pool_signature(ev))
    records = []
    cert = _cert(ev, pool, records, [UNIT, 2 * UNIT, 3 * UNIT], lazy_lps=True)
    ok_before = {l.key(): cert.master.rows_ok(l) for l in lays}
    proofs = {}
    for l, _n in CANDS4:
        for s in range(ev.n_scenarios):
            inf = BD.verify_terminal_infeasible(ev, BL.Layout.of([(l, "SC", 1, 1)]), s)
            if inf:
                proofs[l] = (s, inf)
                break
    assert set(proofs) == {"T4"}
    n = sum(cert.mark_terminal_infeasible(l, s, bikes=b, source="test") for l, (s, b) in proofs.items())
    assert n == len(MENU["SC"])
    assert cert.counters["lp_solves"] == 0 and cert.counters["ilp_solves"] == 0 and not cert.lps.built()
    for o in MENU["SC"]:
        pr = cert.priced[BL.Layout.of([("T4", "SC") + tuple(o)]).key()]
        assert pr.status == "INFEASIBLE" and pr.infeasible == BL.INFEASIBLE_TERMINAL and pr.n_solves == 0
    assert any(c.kind == "terminal" for c in pool.cuts)
    assert sum(1 for r in records if r.get("kind") == "price" and r.get("tag") == "feas_skip") == n
    assert cert.mark_terminal_infeasible("T4", proofs["T4"][0]) == 0          # idempotent
    n_cut = 0
    for l in lays:
        ok = cert.master.rows_ok(l)
        if ok_before[l.key()] and not ok:
            n_cut += 1
            assert vals[l.key()] in (None, BL.INF), (l.key(), vals[l.key()])
        if ok:                                   # the plan's window row holds at every admissible layout
            w = enc.w_of(l)
            for loc in proofs:
                y_l = sum(w[i] for i in range(enc.n) if enc.loc[i] == loc)
                assert y_l <= sum(w[i] for i in range(enc.n) if enc.loc[i] != loc) + 1e-9
    assert n_cut >= len(MENU["SC"])
    assert any(l.n_open == 2 and not cert.master.rows_ok(l) for l in lays)    # l:SC with a hub only: infeasible too
    # restore keeps the marks (price records with n_solves 0)
    cert2 = _cert(ev, pool, [], [UNIT], lazy_lps=True)
    cert2.restore(records)
    assert all(cert2.priced[BL.Layout.of([("T4", "SC") + tuple(o)]).key()].status == "INFEASIBLE" for o in MENU["SC"])
    # enumeration with the skip list: no LP at T4, certificate equals the exhaustive optimum
    e = cert.certify_by_enumeration(UNIT, force_lp_per_location=True, skip_locations=sorted(proofs), release_lps=True)
    best1 = min(v for k, v in vals.items() if v not in (None, BL.INF) and BL.Layout.from_key(k).investment(S.TOY_SPEC) <= UNIT + 1e-6)
    assert e["done"] and e["lp_per_location_skipped"] == ["T4"] and e["lp_per_location"] == 3 and e["lp_released"] == 2
    assert cert.UB[UNIT] == pytest.approx(best1, abs=1e-6) and cert.LB[UNIT] <= best1 + 1e-6 and e["n_infeasible"] >= 2
    assert not any(k.startswith("T4:") for k in cert.lp_memo) and not cert.lps.built()
    cert.close()
    cert2.close()


@pytest.mark.parametrize("F", [2.0, 30.0])
def test_terminal_marks_in_the_bnb_budget_window(tmp_path, F):
    """Item 4 against the budget-window passes of certify_bnb: with UNIT = 125 the k = 1 window of
    m = 2 holds the one-site SC:B2:C1 layouts; the marked T4 one is resolved as infeasible
    without an LP or a pricing, the k = 2 pass keeps its valid node bounds (setup_min ignores
    the rows: weaker, never invalid) and LB_m <= V*_m = UB_m at m = 1, 2, 3."""
    import dataclasses
    unit = 125.0
    spec = dataclasses.replace(S.TOY_SPEC, F=F)
    scen = [S.toy_base_instance(0, candidates=CANDS4), S.toy_base_instance(1, candidates=CANDS4)]
    ev = BL.LowerLevelEvaluator(scen, spec, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                cache_dir=str(tmp_path / "cache")).derive(relaxed_targets=True)
    enc = BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, spec)
    budgets = [unit, 2 * unit, 3 * unit]
    lays = BL.enumerate_layouts(ev.candidates, enc.options, 3 * unit, spec, (1, 2, 3), s_needs_charge=True)
    vals = {l.key(): ev.evaluate(l, "ilp")["V"] for l in lays}
    best = {b: min((v, k) for k, v in vals.items() if v not in (None, BL.INF)
                   and BL.Layout.from_key(k).investment(spec) <= b + 1e-6) for b in budgets}
    pool = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
    records = []
    cert = BD.SitingCertifier(ev, budgets, MENU, S.ROLES, s_needs_charge=True, pool=pool, tol_rel=1e-9, tol_abs=1e-6,
                              lp_threads=1, master_threads=1, on_record=records.append, price_workers=1, lazy_lps=True)
    s_proof = next(s for s in range(2) if BD.verify_terminal_infeasible(ev, BL.Layout.of([("T4", "SC", 1, 1)]), s))
    assert cert.mark_terminal_infeasible("T4", s_proof, source="test") == 2
    cert.warm_start([BL.Layout.from_key("T2:SC:B1:C1"), BL.Layout.from_key("T2:SC:B1:C1|T4:S:B1:C0")])
    BD.certify_bnb(cert, 1, unit, [LEVELS4[1]], S_LP=[0], label="m1")
    n_ilp = cert.counters["ilp_solves"]
    r2 = BD.certify_bnb(cert, 2, 2 * unit, LEVELS4, S_LP=[0], lb_smaller=cert.LB[unit], budget_smaller=unit, label="m2")
    win = r2["passes"][0]
    assert win["method"] == "enumeration" and win["n_layouts"] == 4
    t4 = BL.Layout.of([("T4", "SC", 2, 1)]).key()
    assert t4 not in cert.lp_memo and not any(r.get("kind") == "price" and r.get("layout_key") == t4 and r.get("tag") != "feas_skip"
                                              for r in records)
    enum_rec = [r for r in records if r.get("kind") == "enumerate" and r.get("tag") == "bnb2_k1_window"][-1]
    assert enum_rec["n_infeasible"] >= 1
    r3 = BD.certify_bnb(cert, 3, 3 * unit, LEVELS4, S_LP=[0], lb_smaller=cert.LB[2 * unit], budget_smaller=2 * unit, label="m3")
    for b in budgets:
        assert cert.UB[b] == pytest.approx(best[b][0], abs=1e-6), (b, best[b])
        assert cert.LB[b] <= best[b][0] + 1e-6, (b, cert.LB[b], best[b])
    assert r2["certified"] and r3["certified"] and cert.counters["ilp_solves"] >= n_ilp
    res = cert.finish()
    assert all(res[b]["LB"] <= best[b][0] + 1e-6 for b in budgets)
    cert.close()


def test_template_eviction_gives_identical_values_and_cache_rows(tmp_path):
    """Item 2: evicting the templates (explicitly between pricings, and the LRU cap of one
    resident template) rebuilds identical libraries: the same pricing statuses, values, rows
    and cache rows as without eviction; a lazy ScenarioLPSet that evicts its template after each
    build, is disposed and rebuilt, gives the same LP values and cuts as eager LPs."""
    ev_a = _toy_ev(tmp_path / "a", relaxed=True)
    ev_b = _toy_ev(tmp_path / "b", relaxed=True)
    ev_b.max_templates = 1
    lays = [BL.Layout.from_key(k) for k in ("T2:SC:B1:C1", "T1:SC:B2:C1|T3:S:B1:C0", "T4:SC:B1:C1",
                                            "T2:SC:B1:C1|T4:C:B0:C1", "T1:S:B2:C0|T3:SC:B1:C1")]
    for lay in lays:
        ra = BD.price_layout(ev_a, lay, [0.0, 0.0], BL.INF, 0.0, full=True, workers=2)
        ev_b.evict_template()
        rb = BD.price_layout(ev_b, lay, [0.0, 0.0], BL.INF, 0.0, full=True, workers=2)
        assert ra.status == rb.status and _rows_sig(ra) == _rows_sig(rb) and ra.V == rb.V, lay.key()
        assert len(ev_b.resident_templates()) <= 1
    assert ev_b.n_template_builds > ev_a.n_template_builds and ev_b.n_template_evictions > 0
    assert sorted(_row_cmp(r) for r in ev_a.cache.values()) == sorted(_row_cmp(r) for r in ev_b.cache.values())
    # LPs: eager against lazy + evict + dispose + rebuild
    enc = BD.MenuEncoding([c.id for c in ev_a.candidates], MENU, S.ROLES, S.TOY_SPEC)
    xs = [enc.x_of_layout(l) for l in lays if enc.contains(l)]
    eager = [BD.ScenarioLP(ev_a, s, threads=1, relaxed=True) for s in range(2)]
    lazy = BD.ScenarioLPSet(ev_b, threads=1, relaxed=True, evict_templates=True)
    assert len(lazy) == 2 and not lazy.built()
    _ = lazy[1]
    assert [lp.s for lp in lazy.built()] == [1] and 1 not in ev_b.resident_templates()
    for rnd in range(2):
        for x in xs:
            for s in range(2):
                r1, r2 = eager[s].solve(x), lazy[s].solve(x)
                assert r1.status == r2.status and abs(r1.Qs - r2.Qs) <= 1e-7 * max(1.0, abs(r1.Qs)) and abs(r1.Qt - r2.Qt) <= 1e-7 * max(1.0, abs(r1.Qt))
                assert abs(r1.c0 - r2.c0) <= 1e-6 * max(1.0, abs(r1.c0))
        sub1 = [eager[s].solve_subset(["T1", "T2"]).Qs for s in range(2)]
        sub2 = [lazy[s].solve_subset(["T1", "T2"]).Qs for s in range(2)]
        assert np.allclose(sub1, sub2, rtol=1e-7, atol=1e-7)
        assert lazy.dispose() == 2 and not lazy.built()
    assert lazy.n_built == 4 and lazy.n_disposed == 4
    for lp in eager:
        lp.dispose()


def test_lazy_lps_build_only_what_a_bound_needs_and_match_eager_certifier(tmp_path):
    """Item 2: a certifier on a lazy ScenarioLPSet builds an LP only when a solve needs it
    (subset bound on S_LP = [0] builds scenario 0 only), and its LP cuts and values equal those
    of the eager certifier; release_lps disposes them and a later LP rebuilds."""
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    rec_a, rec_b = [], []
    ca = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), rec_a, [UNIT])
    cb = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), rec_b, [UNIT], lazy_lps=True)
    assert isinstance(cb.lps, BD.ScenarioLPSet) and not cb.lps.built()
    va = ca.subset_bound(["T1", "T2"], [0])
    vb = cb.subset_bound(["T1", "T2"], [0])
    assert [lp.s for lp in cb.lps.built()] == [0] and np.allclose(va, vb)
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    qa = [r.Qs for r in ca.lp_at(lay)]
    qb = [r.Qs for r in cb.lp_at(lay)]
    assert np.allclose(qa, qb, rtol=1e-7) and len(cb.lps.built()) == 2
    assert cb.release_lps() == 2 and not cb.lps.built() and ca.release_lps() == 0
    lay2 = BL.Layout.from_key("T3:SC:B2:C1")
    assert np.allclose([r.Qs for r in ca.lp_at(lay2)], [r.Qs for r in cb.lp_at(lay2)], rtol=1e-7)
    assert any(r.get("kind") == "lp_release" for r in rec_b)
    ca.close()
    cb.close()


def test_batched_escalation_reprices_all_open_scenarios_in_one_call(tmp_path, monkeypatch):
    """Item 3: with escalate_batch every open scenario of the layout is re-priced in ONE call
    (``scenarios`` = all open ones, the next level's limit; levels counted per (layout,
    scenario)); the serial mode re-prices one scenario per call.  Pricing is replaced by a
    recorder on a fabricated open gap (the toy ILPs close at once)."""
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    for batch in (False, True):
        cert = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), [], [UNIT], lazy_lps=True, escalate_batch=batch,
                     max_escalations=2, escalate_factor=3.0, escalate_cap_s=1e9)
        res = BD.PriceResult(layout=lay, status="PRICED", setup=lay.allocated_cost(S.TOY_SPEC), lb=[10.0, 20.0],
                             ub=[12.0, 25.0], V=50.0, rows=[{"scenario": 0, "time_limit": 30.0}, {"scenario": 1, "time_limit": 30.0}])
        cert.priced[lay.key()] = res
        calls = []
        monkeypatch.setattr(cert, "price", lambda layout, **kw: calls.append(kw) or res)
        while cert.escalate(lay):
            pass
        if batch:
            assert [c["scenarios"] for c in calls] == [[1, 0], [1, 0]]          # largest p_s * gap first
            assert [c["time_limit"] for c in calls] == [90.0, 270.0] and all(c["full"] for c in calls)
            assert all(c["lp"] is False for c in calls)                         # no per-layout LP rebuilt
            assert cert.counters["escalations"] == 4 and cert.counters["escalation_waves"] == 2
        else:
            assert [c["scenarios"] for c in calls] == [[1], [1], [0], [0]]
            assert "escalation_waves" not in cert.counters and cert.counters["escalations"] == 4
        assert cert.esc_level == {(lay.key(), 0): 2, (lay.key(), 1): 2}
        monkeypatch.undo()
        cert.close()


def test_cli_feas_rootlp_stages_merge_and_stage_lanes(tmp_path):
    """Items 1 and 4 through the driver: stage feas writes the screen with the configuration's
    signature (T4 infeasible), stage rootlp writes bound.json-form root files (one scenario per
    process), the merge raises L_s to the all-open values (equal to the superset bound on the
    toy), m1 skips the LP at T4 and certifies the exhaustive optimum; a probe-format screen
    without signature is re-proved (true claim kept, false claim dropped); --root-import takes
    the all-open subset cuts of a pool with the same signature; the stage lanes are well formed."""
    from experiments import r7_siting as R
    out = tmp_path / "run"
    base = ["--smoke", "--out-dir", str(out)]
    r = _run(base + ["--stage", "setup,feas"])
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    feas = json.loads((out / "feas_one_site_all.json").read_text())
    assert feas["infeasible_locations"] == ["T4"] and feas["signature"] and feas["scenarios"] == [0, 1]
    for s in (1, 0):                                     # two "processes", one scenario each
        r = _run(base + ["--stage", "rootlp", "--root-scenarios", str(s), "--max-threads", "1"])
        assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    roots = [json.loads((out / "root_lp" / f"root_s0{s}.json").read_text()) for s in (0, 1)]
    assert all(set(d) >= {"key", "bound", "rows"} and d["bound"][d["scenario"]] is not None for d in roots)
    assert roots[0]["key"] == roots[1]["key"]
    r = _run(base + ["--stage", "rootlp", "--max-threads", "1"])        # both present: skipped
    assert r.returncode == 0 and r.stdout.count('"stage_skipped"') >= 2, r.stdout[-2000:]
    r = _run(base + ["--stage", "m1", "--superset", "off", "--root-merge", "on", "--lp-lifecycle", "on", "--escalate-batch", "on"])
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    recs = C.load_jsonl(str(out / "records.jsonl"))
    sup = [x for x in recs if x.get("kind") == "superset_bound" and not x.get("skipped")][0]["bound"]
    merged = [x for x in recs if x.get("kind") == "root_bound_merged"][-1]
    assert merged["L_before"] == [0.0, 0.0] and not merged["missing"]
    assert np.allclose(merged["L"], sup, rtol=1e-6, atol=1e-6)
    m1 = [x for x in recs if x.get("kind") == "enumerate" and x.get("stage") == "m1"][-1]
    assert m1["lp_per_location_skipped"] == ["T4"] and m1["lp_released"] >= 1
    acc = [x for x in recs if x.get("kind") == "acceptance" and x.get("stage") == "m1"]
    assert acc and acc[-1]["ok"], acc
    fsl = [x for x in recs if x.get("kind") == "feas_skip_list"][-1]
    assert fsl["locations"] == ["T4"] and fsl["proofs"]["T4"]["trusted"] and fsl["n_verification_builds"] == 0
    # a probe-format screen (no signature): claims are re-proved by a library build
    probe = {"r7_args": "--smoke", "scenarios": [0, 1], "rows": [
        {"layout_key": "T4:SC:B2:C1", "scenario": 0, "n_infeasible_bikes": 2, "infeasible": [["1", "0", 3], ["2", "0", 3]]},
        {"layout_key": "T1:SC:B2:C1", "scenario": 1, "n_infeasible_bikes": 1, "infeasible": [["1", "0", 3]]}]}
    out2 = tmp_path / "run2"
    out2.mkdir()
    (out2 / "feas_one_site_probe.json").write_text(json.dumps(probe))
    args = R.parse_args(["--smoke", "--stage", "m1", "--out-dir", str(out2)])
    ctx = R.Ctx(R.Run(args))
    try:
        fe = ctx.feasibility()
        assert set(fe) == {"T4"} and fe["T4"]["verified"] and not fe["T4"]["trusted"]
        rec = [x for x in C.load_jsonl(str(out2 / "records.jsonl")) if x.get("kind") == "feas_skip_list"][-1]
        assert rec["n_verification_builds"] == 2 and any(d.get("location") == "T1" for d in rec["dropped"])
    finally:
        ctx.close()
    # --root-import from the first run's pool (the setup stage's all-open subset cut of S_LP = [0])
    out3 = tmp_path / "run3"
    r = _run(["--smoke", "--out-dir", str(out3), "--stage", "rootlp", "--root-scenarios", "--root-import",
              str(out / "cuts.jsonl"), "--max-threads", "1"])
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    imp = json.loads((out3 / "root_lp" / "root_s00.json").read_text())
    assert imp["method"] == "imported" and imp["key"] == roots[0]["key"]
    assert imp["bound"][0] == pytest.approx(roots[0]["bound"][0], rel=1e-6, abs=1e-6)
    # stage lanes: rootlp in 3 chains, longest stratum first; feas in 4 disjoint groups
    lanes = tmp_path / "lanes"
    r = _run(["--write-lanes", "--lanes", "rootlp", "--scenarios", "12", "--lanes-dir", str(lanes), "--lp-threads", "3",
              "--out-dir", str(out)])
    assert r.returncode == 0, r.stderr[-2000:]
    rows = [ln.split("\t") for ln in (lanes / "lanes_rootlp.txt").read_text().splitlines() if ln and not ln.startswith("#")]
    assert len(rows) == 12 and [x[2] for x in rows[:3]] == ["-", "-", "-"]
    assert [x[2] for x in rows[3:]] == [x[0] for x in rows[:9]]                 # at most 3 at once
    design = S.scenario_design(12)
    first = [int(x[0][-2:]) for x in rows[:2]]
    assert all(design[s]["level"] == 1.5 and design[s]["day_type"] == "weekday" for s in first)
    assert all("--stage rootlp --root-scenarios" in x[3] and "--max-threads 3" in x[3] for x in rows)
    r = _run(["--write-lanes", "--lanes", "feas", "--scenarios", "12", "--lanes-dir", str(lanes), "--out-dir", str(out)])
    assert r.returncode == 0, r.stderr[-2000:]
    rows = [ln.split("\t") for ln in (lanes / "lanes_feas.txt").read_text().splitlines() if ln and not ln.startswith("#")]
    groups = [x[3].split("--feas-scenarios ")[1].split(" --")[0].split() for x in rows]
    assert len(rows) == 4 and sorted(int(s) for g in groups for s in g) == list(range(12))


# ---------------------------------------------------------------------------
# R7 fixer pass (reviews of 2026-10-21): escalation waves and cap, warm start memory, derive
# ---------------------------------------------------------------------------
class _WaveEv:
    """Minimal evaluator for :func:`benders.price_layout_parallel`: cached TIME_LIMIT rows, solves
    that sleep ``delay`` seconds and record their start time."""

    def __init__(self, n, delay):
        import threading
        self.p = [1.0 / n] * n
        self.n_scenarios = n
        self.spec = S.TOY_SPEC
        self.reposition = "all_candidates"
        self._lock = threading.Lock()
        self.cache = {}
        self.delay = delay
        self.starts = {}

    def cache_key(self, lay, s, policy):
        return f"{lay.key()}|{s}|{policy}"

    def load_portable(self, row):
        return None

    def evaluate_scenario(self, lay, s, policy, **kw):
        import time as _t
        self.starts[s] = _t.perf_counter()
        _t.sleep(self.delay)
        c = lay.allocated_cost(self.spec)
        return {"scenario": s, "status": "OPTIMAL", "gurobi_status": "OPTIMAL", "opex": 10.0, "total": 10.0 + c,
                "bound": 10.0 + c, "C_setup": c, "feasible": True, "time_limit": kw.get("time_limit"), "key": None}


def test_batched_escalation_waves_are_cut_from_the_open_scenarios():
    """Fixer pass: with ``scenarios`` given, the cached rows of the other scenarios are taken first
    and the waves are cut from the open ones, so two open scenarios with workers = 2 start
    together (before: waves of the full p_s order, s0 and s2 in different waves, serial)."""
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    ev = _WaveEv(4, 0.6)
    c = lay.allocated_cost(S.TOY_SPEC)
    for s in range(4):
        ev.cache[ev.cache_key(lay, s, "ilp")] = {"scenario": s, "status": "TIME_LIMIT", "gurobi_status": "TIME_LIMIT",
                                                 "opex": 12.0, "total": 12.0 + c, "bound": 9.0 + c, "C_setup": c,
                                                 "feasible": True, "time_limit": 30.0}
    res = BD.price_layout(ev, lay, [0.0] * 4, BL.INF, 0.0, full=True, time_limit=60.0, scenarios=[0, 2], workers=2)
    assert sorted(ev.starts) == [0, 2]
    assert abs(ev.starts[0] - ev.starts[2]) < 0.3                       # one wave
    assert res.status == "PRICED" and res.ub == [10.0, 12.0, 10.0, 12.0]
    assert [r["cache_hit"] for r in res.rows] == [None, True, None, True]
    # without scenarios: the full p_s order in waves of 2, every TIME_LIMIT row re-solved
    ev2 = _WaveEv(4, 0.0)
    ev2.cache = dict(ev.cache)
    ev2.cache.update({ev2.cache_key(lay, s, "ilp"): dict(ev.cache[ev2.cache_key(lay, s, "ilp")], time_limit=30.0)
                      for s in range(4)})
    res2 = BD.price_layout(ev2, lay, [0.0] * 4, BL.INF, 0.0, full=True, time_limit=60.0, workers=2)
    assert sorted(ev2.starts) == [0, 1, 2, 3] and res2.status == "PRICED"


def test_batched_escalation_cap_at_level_two(tmp_path, monkeypatch):
    """Fixer pass: with ``escalate_batch_max`` a batch at level >= 2 takes at most that many open
    scenarios (largest p_s * gap first); level 1 keeps the full batch; the deferred scenario is
    taken by the next call.  Pricing is replaced by a recorder (as in the batched test)."""
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    cert = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), [], [UNIT], lazy_lps=True, escalate_batch=True,
                 max_escalations=2, escalate_factor=3.0, escalate_cap_s=1e9, escalate_batch_max=1)
    res = BD.PriceResult(layout=lay, status="PRICED", setup=lay.allocated_cost(S.TOY_SPEC), lb=[10.0, 20.0],
                         ub=[12.0, 25.0], V=50.0, rows=[{"scenario": 0, "time_limit": 30.0}, {"scenario": 1, "time_limit": 30.0}])
    cert.priced[lay.key()] = res
    calls = []
    monkeypatch.setattr(cert, "price", lambda layout, **kw: calls.append(kw) or res)
    while cert.escalate(lay):
        pass
    assert [c["scenarios"] for c in calls] == [[1, 0], [1], [0]]
    assert [c["time_limit"] for c in calls] == [90.0, 270.0, 270.0]
    assert cert.esc_level == {(lay.key(), 0): 2, (lay.key(), 1): 2}
    assert cert.counters["escalation_cells_deferred"] == 1
    monkeypatch.undo()
    cert.close()


def test_warm_start_releases_lps_before_pricing(tmp_path):
    """Fixer pass (memory): with ``release_lps`` every warm layout's LPs are solved first, the lazy
    LPs disposed, then the layouts priced from ``lp_memo`` (no LP rebuilt); the values equal the
    interleaved warm start."""
    ev = _toy_ev(tmp_path / "cache", relaxed=True)
    warm = [BL.Layout.from_key(k) for k in ("T2:SC:B1:C1", "T3:SC:B2:C1")]
    rec_a, rec_b = [], []
    ca = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), rec_a, [UNIT], lazy_lps=True)
    cb = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), rec_b, [UNIT], lazy_lps=True)
    ca.warm_start(warm)
    seen = []
    cb.warm_start(warm, release_lps=True, before_pricing=lambda: seen.append(len(cb.lps.built())) or True)
    kinds = [r.get("kind") for r in rec_b if r.get("kind") in ("lp_layout", "lp_release", "price")]
    assert kinds == ["lp_layout", "lp_layout", "lp_release", "price", "price"], kinds
    assert seen == [0] and not cb.lps.built()                             # nothing rebuilt by the pricings
    for l in warm:
        assert ca.priced[l.key()].V == pytest.approx(cb.priced[l.key()].V)
    cc = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), [], [UNIT], lazy_lps=True)
    cc.warm_start(warm, release_lps=True, before_pricing=lambda: False)  # guard tripped: LPs only
    assert not cc.priced and all(l.key() in cc.lp_memo for l in warm)
    for c in (ca, cb, cc):
        c.close()


def test_derive_shares_templates_only_with_an_equal_spec(tmp_path):
    """Fixer pass: a sibling with another spec (e.g. F_hub) gets its own template dict; target or
    variant siblings with the same spec share it."""
    ev = _toy_ev(tmp_path / "cache")
    import dataclasses
    other = ev.derive(spec=dataclasses.replace(S.TOY_SPEC, F_hub=S.TOY_SPEC.F_hub + 1.0))
    same = ev.derive(relaxed_targets=True)
    assert other._templates is not ev._templates and same._templates is ev._templates
    ev.template(0)
    assert 0 in same.resident_templates() and 0 not in other.resident_templates()
