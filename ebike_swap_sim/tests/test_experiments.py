"""Tests of the experiments layer (``experiments/common.py``) and of the node-aware
option encoder added to ``or_instance.Instance.to_dict / from_dict``."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebike_swap_sim import Instance, toy_instance  # noqa: E402
from ebike_swap_sim import generator as gen  # noqa: E402
from experiments import common as C  # noqa: E402

pytest.importorskip("gurobipy")


def test_option_encoder_round_trip():
    """Sets and node-keyed dicts in ``Instance.options`` survive JSON (bug reported by
    the generator author); ``reposition_targets`` keeps its plain-list encoding."""
    inst = toy_instance()
    inst.options["reposition_targets"] = {"A", "C"}
    inst.options["node_zone_dict"] = {("x", 1): 0, "B": 2}
    inst.options["some_set"] = {("x", 1), "y"}
    js = inst.to_json()
    back = Instance.from_json(js)
    assert back == inst
    assert back.to_json() == js
    assert back.options["node_zone_dict"] == {("x", 1): 0, "B": 2}
    assert back.options["some_set"] == {("x", 1), "y"}
    # generator instances (node_zone list) still round-trip byte-identically
    g = gen.make_synthetic_instance(seed=3, n_bikes=2, n_orders=4, H=12, L=4)
    assert Instance.from_json(g.to_json()) == g


def test_grid_route_cache_is_per_instance():
    """GridNetwork.route memoises per instance (no process-wide lru_cache)."""
    import numpy as np
    from ebike_swap_sim import GridNetwork
    net = GridNetwork(4, 4, 150.0, 0.5, 2, np.random.default_rng(0))
    r1 = net.route((0, 0), (3, 3))
    assert net.route((0, 0), (3, 3)) is r1
    assert ((0, 0), (3, 3)) in net._route_cache
    assert not hasattr(GridNetwork.route, "cache_info")


def test_run_pair_on_toy_reorder_point():
    """run_pair: baseline REORDER_POINT 14.5, ILP 12.5, start accepted, identities."""
    inst = C.make_instance("toy")
    rec = C.run_pair(inst, pruning={}, baseline_params={"transfer_rule": "REORDER_POINT"},
                     time_limit=60.0, keep_schedules=True)
    C.assert_pair(rec)
    assert rec["baseline_total"] == pytest.approx(14.5)
    assert rec["ilp_total"] == pytest.approx(12.5)
    assert rec["ilp_status"] == "OPTIMAL" and rec["mip_start_accepted"] is True
    assert rec["baseline_identity_24_ok"] and rec["ilp_identity_24_ok"]
    assert rec["n_arcs"] == 470
    df = C.records_to_frame([rec])
    assert "_lib" not in df.columns and df.loc[0, "ilp_total"] == pytest.approx(12.5)


def test_run_pair_small_synthetic(tmp_path):
    """Small synthetic family end to end with the plan's pruning; CSV / table helpers."""
    inst = C.make_instance("small", seed=0)
    pr = C.pruning_for(inst)
    assert pr["tau_max"] == 4 and pr["start_slack"] == 6 and pr["reposition_targets"]
    rec = C.run_pair(inst, pruning=pr, time_limit=120.0)
    C.assert_pair(rec)
    assert rec["ilp_status"] == "OPTIMAL"
    assert rec["ilp_total"] <= rec["baseline_total"]
    df = C.write_csv([rec], str(tmp_path / "r.csv"))
    assert (tmp_path / "r.csv").exists() and len(df) == 1
    md = C.markdown_table(df, ["family", "ilp_total", "baseline_total"])
    assert md.startswith("| family |")


def test_relax_end_targets_and_gap_definitions():
    """relax_end_targets: rho = 0 AND R_end = 0 on a deep copy (reviewer F3); both gap
    conventions named explicitly (reviewer F4)."""
    inst = C.make_instance("toy")
    inst.facilities[0].R_end = 1
    inst.reindex()
    rho0 = inst.rho
    assert rho0 > 0
    relaxed = C.relax_end_targets(inst)
    assert relaxed.rho == 0.0 and all(f.R_end == 0 for f in relaxed.facilities)
    assert inst.rho == rho0 and inst.facilities[0].R_end == 1                # original untouched
    assert relaxed.meta["relax_end_targets"] is True
    assert [o.id for o in relaxed.orders] == [o.id for o in inst.orders]
    from ebike_swap_sim import build_arcs
    rec = C.run_ilp_case(relaxed, build_arcs(relaxed), time_limit=60.0)
    assert rec["obj"] == pytest.approx(11.2)                                 # toy with (18) off
    g = C.gap_definitions(14.5, 12.5)
    assert g["gap_vs_baseline_pct"] == pytest.approx(100 * 2 / 14.5)
    assert g["gap_vs_ilp_pct"] == pytest.approx(16.0)
    assert C.gap_definitions(None, 12.5) == {"gap_vs_baseline_pct": None, "gap_vs_ilp_pct": None}


def test_baseline_variants_run_on_toy():
    """Every documented baseline variant runs on the toy with only report-only families;
    baseline_reserve resolves the symbolic end window W = max sigma + 3."""
    from ebike_swap_sim import build_arcs
    inst = C.make_instance("toy")
    lib = build_arcs(inst)
    assert C.end_window(inst) == 4
    assert C.baseline_variant_params("baseline_reserve", inst) == {"end_reserve_window": 4, "late_threshold_window": 4}
    assert C.baseline_variant_params("baseline_legacy", inst) == {
        "stock_aware_site": False, "charge_rule": "HIGH_FIRST", "jit_dispatch": False, "swap_on_reach_refusal": False}
    assert C.baseline_variant_params("baseline_round1", inst) == {"stock_aware_site": False, "charge_rule": "HIGH_FIRST"}
    assert C.baseline_variant_params("baseline", inst) == {}
    totals = {}
    for name in C.BASELINE_VARIANTS:
        rec = C.run_baseline_case(inst, lib, C.baseline_variant_params(name, inst), label=name)
        assert rec["ok_modulo_report_only"] and rec["identity_24_ok"], (name, rec["families"])
        totals[name] = rec["cost"]["total"]
    assert totals["baseline"] == pytest.approx(108.0) and totals["baseline_reorder"] == pytest.approx(14.5)
    with pytest.raises(KeyError):
        C.baseline_variant_params("nope", inst)


def test_run_pair_emits_both_gap_columns():
    inst = C.make_instance("toy")
    rec = C.run_pair(inst, pruning={}, baseline_params={"transfer_rule": "REORDER_POINT"}, time_limit=60.0)
    assert rec["gap_vs_ilp_pct"] == pytest.approx(rec["baseline_gap_pct"]) == pytest.approx(16.0)
    assert rec["gap_vs_baseline_pct"] == pytest.approx(100 * 2 / 14.5)
    assert rec["baseline_jit_dispatches"] == 0 and rec["baseline_reach_refusals"] == 0


def test_relaxed_copy_keeps_written_reserve_for_the_policy():
    """Fairness review F1: the DEMAND_AWARE reserve is R_end_j y_j (R2.3), so on a
    relax_end_targets copy (R_end 0) run_baseline_case passes the WRITTEN R_end_j as
    charge_reserve -- the policy is the same policy under both target settings and its
    schedule is identical.  An explicit charge_reserve still wins."""
    from ebike_swap_sim import build_arcs
    inst = C.make_instance("toy")
    for f in inst.facilities:
        if f.swap:
            f.R_end = 1
    inst.reindex()
    lib = build_arcs(inst)
    written = C.run_baseline_case(inst, lib, {"transfer_rule": "REORDER_POINT"})
    rel = C.relax_end_targets(inst)
    assert rel.meta["written_R_end"] == {f.id: int(f.R_end) for f in inst.facilities}
    assert rel.meta["written_rho"] == inst.rho and all(f.R_end == 0 for f in rel.facilities)
    rlib = build_arcs(rel)
    relaxed = C.run_baseline_case(rel, rlib, {"transfer_rule": "REORDER_POINT"})
    assert written["policy_reserve_source"] == "R_end" and relaxed["policy_reserve_source"] == "written_R_end"
    assert relaxed["params"]["charge_reserve"] == rel.meta["written_R_end"]
    assert relaxed["cost"]["total"] == pytest.approx(written["cost"]["total"])
    assert relaxed["schedule"].c == written["schedule"].c and relaxed["schedule"].x == written["schedule"].x
    explicit = C.run_baseline_case(rel, rlib, {"transfer_rule": "REORDER_POINT", "charge_reserve": 0})
    assert explicit["policy_reserve_source"] == "params" and explicit["params"]["charge_reserve"] == 0
    # the written instance itself is never touched by the reserve logic
    assert "written_R_end" not in inst.meta and written["params"]["charge_reserve"] is None


def test_demand_key_unservable_and_anomaly_helpers():
    """Units review F7 / fairness review F4, F5: demand hash, unservable orders, pruning
    flag summary and the anomaly lines of a run_pair record."""
    import copy
    from ebike_swap_sim import build_arcs
    inst = C.make_instance("toy")
    lib = build_arcs(inst)
    assert C.unservable_orders(inst, lib) == []
    twin = C.make_instance("toy")
    assert C.demand_key(inst) == C.demand_key(twin) and C.demand_md5(inst) == C.demand_md5(twin)
    assert len(C.demand_md5(inst)) == 32
    moved = copy.deepcopy(inst)
    moved.orders[0].r += 1
    assert C.demand_md5(moved) != C.demand_md5(inst)
    # bike start nodes may be excluded (e8 sitings move them with the sites); facilities on request
    assert C.demand_key(inst, include_bike_nodes=False) != C.demand_key(inst)
    assert len(C.demand_key(inst, include_facilities=True)) == len(C.demand_key(inst)) + 1
    flags = {"pruned_arc_fallbacks": {"count": {"move": 1, "deliver": 0, "swap": 2}},
             "stranded_bikes": [1], "late_trips_suppressed": 3}
    assert C.baseline_pruning_flags(flags) == {"pruned_fallbacks": 3, "stranded": 1, "late_suppressed": 3}
    assert C.baseline_pruning_flags({}) == {"pruned_fallbacks": 0, "stranded": 0, "late_suppressed": 0}
    rec = {"name": "x", "baseline_pruned_fallbacks": 3, "baseline_stranded": 0, "baseline_late_suppressed": 0,
           "n_unservable": 1, "mip_start_fallback_errors": '{"baseline_reserve": "ValueError: w"}'}
    lines = C.pair_anomalies(rec)
    assert len(lines) == 3 and all(line.startswith("x:") for line in lines)
    assert C.pair_anomalies({"name": "y", "mip_start_fallback_errors": "{}"}) == []


def test_feasible_mip_start_records_fallback_errors(monkeypatch):
    """Fairness review F7: a fallback variant that raises a parameter error is recorded on
    the base record instead of being swallowed; genuine policy bugs propagate."""
    from ebike_swap_sim import build_arcs
    inst = C.make_instance("toy")
    lib = build_arcs(inst)
    base = {"families": {"(18)": 1}, "schedule": None}

    def bad_params(name, inst, **overrides):
        raise ValueError(f"no swap site for W ({name})")

    monkeypatch.setattr(C, "baseline_variant_params", bad_params)
    sched, label = C.feasible_mip_start(inst, lib, base)
    assert (sched, label) == (None, "default")
    assert set(base["mip_start_fallback_errors"]) == set(C.MIP_START_FALLBACKS)
    assert all(v.startswith("ValueError") for v in base["mip_start_fallback_errors"].values())

    def bug(name, inst, **overrides):
        raise RuntimeError("policy bug")

    monkeypatch.setattr(C, "baseline_variant_params", bug)
    with pytest.raises(RuntimeError):
        C.feasible_mip_start(inst, lib, {"families": {"(18)": 1}, "schedule": None})
    clean = {"families": {}, "schedule": "S"}
    assert C.feasible_mip_start(inst, lib, clean) == ("S", "default") and clean["mip_start_fallback_errors"] == {}
