"""Round-5 integration tests (``notes/reading_to_model.md``): cross-module wiring of the
plan items, with no E2 equation change.

* M9 lock-out end to end: the baseline policy executes the data-forced transfers
  (``options['forced_transfers']``) and never uses them for its own rules, ``ilp.build_model``
  fixes them automatically (E2 (10) variable bounds only), ``evaluate.metrics`` reports the
  stock without the dummy sink, the aggregated ILP (O1) agrees with the per-bike ILP;
* ``experiments.common``: the R5 sizes are registered, ``make_instance`` builds them through
  ``generator.make_r5_instance`` (identical demand), the round-5 baseline variants map onto
  ``baseline.BASELINE_VARIANTS``, the R5 pruning applies to round-5 instances only;
* the round-5 modules are lazy attributes of the package;
* A7 station layer: with the M2 reservation rider variant the agent's loads respect the
  reservations, and random actions stay feasible modulo (9)/(17)/(18).
"""
from __future__ import annotations

import pytest

from ebike_swap_sim import baseline as bl
from ebike_swap_sim import build_arcs, check, metrics, toy_instance
from ebike_swap_sim import generator as G

C = pytest.importorskip("experiments.common")

REPORT_ONLY = {"(9)", "(17)", "(18)"}


@pytest.fixture(scope="module")
def lock_small():
    inst = C.make_instance("small", 0)
    lk = G.add_battery_lockout(inst, share=0.1, seed=1, level="any")
    return inst, lk, build_arcs(lk, **C.pruning_for(lk))


def test_baseline_executes_forced_transfers(lock_small):
    inst, lk, lib = lock_small
    n = lk.meta["lockout"]["n_locked"]
    assert n >= 1
    for name in ("default", "round1", "r5", "r5_transfer"):
        for rule in (None, "REORDER_POINT"):
            p = bl.baseline_variant_params(name)
            if rule is not None and name not in ("r5", "r5_transfer"):
                p["transfer_rule"] = rule
            sched, flags = bl.run_baseline(lk, lib, p)
            ft = flags["forced_transfers"]
            assert ft["executed"] == n and not ft["missed"], (name, rule, ft)
            for rec in lk.options["forced_transfers"]:
                e = rec["service"]
                assert sched.h[e] == 1
                assert sum(v for (ee, _q), v in sched.z.items() if ee == e) == 1
            # the voluntary rules never ship to the sink
            sink = lk.meta["lockout"]["sink"]
            forced = {r["service"] for r in lk.options["forced_transfers"]}
            assert all(s.id in forced for s in lk.services if s.d_fac == sink)
            rep = check(lk, lib, sched)
            assert set(rep["families"]) <= REPORT_ONLY, rep["families"]
            m = metrics(lk, lib, sched)["lockout"]
            assert m["locked_batteries"] == n and m["forced_executed"] == n
            assert m["end_full_total_incl_sink"] == m["end_full_total_excl_sink"] + m["locked_full_at_H"]
    # a lock-out free instance has no 'forced_transfers' flag and no 'lockout' metrics
    lib0 = build_arcs(inst, **C.pruning_for(inst))
    s0, f0 = bl.run_baseline(inst, lib0)
    assert "forced_transfers" not in f0 and "lockout" not in metrics(inst, lib0, s0)


def test_baseline_forced_full_level():
    base = G.make_synthetic_instance(seed=0, n_bikes=2, n_orders=4, H=12, L=6)
    lk = G.add_battery_lockout(base, share=0.25, level="full", slots=[1, 2, 3])
    lib = build_arcs(lk)
    sched, flags = bl.run_baseline(lk, lib)
    for svc, t, q in flags["forced_transfers"]["loads"]:
        assert q == lk.L
    assert flags["forced_transfers"]["executed"] + len(flags["forced_transfers"]["missed"]) == len(
        lk.options["forced_transfers"])


def test_ilp_build_model_applies_forced_transfers(lock_small):
    pytest.importorskip("gurobipy")
    from ebike_swap_sim import ilp
    _inst, lk, lib = lock_small
    sched, st = ilp.solve(lk, lib, threads=3, time_limit=120)
    assert st["status"] == "OPTIMAL"
    assert st["switches"]["forced_transfers"] == lk.meta["lockout"]["n_locked"]
    assert all(sched.h[r["service"]] == 1 for r in lk.options["forced_transfers"])
    sa, sta = ilp.solve(lk, lib, threads=3, time_limit=120, aggregate=True)
    assert sta["status"] == "OPTIMAL" and sta["obj"] == pytest.approx(st["obj"], abs=1e-6)
    assert all(sa.h[r["service"]] == 1 for r in lk.options["forced_transfers"])
    # no_transfers removes the lock-out (documented), recorded in the switches
    mdl = ilp.build_model(lk, lib, threads=3, time_limit=60, no_transfers=True)
    assert mdl.switches["forced_transfers"] == 0
    assert mdl.switches["forced_transfers_skipped"] == lk.meta["lockout"]["n_locked"]
    # instances without forced transfers: switches unchanged
    toy = toy_instance()
    m2 = ilp.build_model(toy, build_arcs(toy), threads=1, time_limit=10)
    assert "forced_transfers" not in m2.switches


def test_common_registers_r5_sizes():
    for name in C.R5_SIZES:
        assert name in C.FAMILIES and name in C.R2_FAMILIES
    inst = C.make_instance("r5_stress4h", 0)
    ref = G.make_r5_instance("r5_stress4h", 0)
    assert C.demand_md5(inst) == C.demand_md5(ref)
    assert inst.meta["family"] == "r5_stress4h" and inst.meta["r5_family"] == "r5_stress4h"
    k8 = C.make_instance("r5_stress4h_k8", 1)
    assert len(k8.bikes) == 8 and len(k8.orders) == round(2.0 * 8 * 4)
    assert C.make_instance("r5_stress8h", 0).meta.get("rolling_horizon_only") is True
    pr = C.pruning_for(inst)
    assert pr.get("reachable_pruning") is True
    # old families keep their pruning (no reachable pruning for usd4h)
    assert not C.pruning_for(C.make_instance("usd4h", 0)).get("reachable_pruning")
    for v in ("baseline_r5", "baseline_r5_range", "baseline_r5_transfer", "baseline_r5_selfish"):
        assert C.baseline_variant_params(v, inst) == bl.BASELINE_VARIANTS[v[len("baseline_"):]]


def test_round5_modules_are_lazy_attributes():
    import ebike_swap_sim as pkg
    assert pkg.aggregate.__name__ == "ebike_swap_sim.aggregate"
    assert pkg.rolling.__name__ == "ebike_swap_sim.rolling"


def test_rl_station_layer_respects_reservations():
    """A7 + M2: a full battery reserved by a bike at a swap site is never loaded by the agent
    (``rl_env._StationRun.station_external`` draws full batteries through ``_avail_full``)."""
    pytest.importorskip("gymnasium")
    import numpy as np
    from ebike_swap_sim.rl_env import EnvConfig, StationEnv
    inst = toy_instance()
    lib = build_arcs(inst)
    env = StationEnv(instances=[(inst, lib)], config=EnvConfig(rider_variant="r5"))
    env.reset(options={"seed": 0})
    run = env.run
    L = inst.L
    svc = inst.service(2)                       # A -> C departing at l = 4, U = 1
    run.n["A"] = [0] * (L + 1)
    run.n["A"][L] = 1
    run.n["C"] = [0] * (L + 1)                  # free storage at the hub (15)
    run.resv["A"] = {1: inst.H}                 # bike 1 holds the only full battery
    applied = run.station_external(svc.l, {}, {svc.id: 1})
    assert applied["loads"].get(svc.id, 0) == 0
    assert run.n["A"][L] == 1 and run.h[svc.id] == 0
    run.resv["A"] = {}                          # without the hold the battery may leave
    applied = run.station_external(svc.l, {}, {svc.id: 1})
    assert run.n["A"][L] == 0 and run.h[svc.id] == 1
    # random actions with the r5 rider rules stay feasible modulo (9)/(17)/(18)
    rng = np.random.default_rng(1)
    for _ in range(5):
        env.reset(options={"seed": 0})
        done = False
        while not done:
            _obs, _r, done, _trunc, info = env.step(rng.integers(0, env.action_space.nvec))
        rep = check(inst, lib, info["schedule"])
        assert set(rep["families"]) <= REPORT_ONLY, rep["families"]
        assert rep["identity_24_ok"]


def test_aggregated_extraction_tolerates_intfeastol():
    """O1: Gurobi accepts integer flows within IntFeasTol (1e-5); the decomposition must round
    a flow such as 1.999998 (seen on r5_stress8h at 6 bikes) instead of raising."""
    pytest.importorskip("gurobipy")
    from ebike_swap_sim import ilp
    inst = toy_instance()
    lib = build_arcs(inst)
    mdl = ilp.build_model(inst, lib, threads=1, time_limit=30, aggregate=True)
    sched, st = mdl.solve()
    assert st["obj"] == pytest.approx(12.5)
    flows = mdl.agg.aggregate_x({k: sched.arc_ids(k) for k in sched.x})[0]
    noisy = {a: (v - 1.5e-6 if v > 0 else v) for a, v in flows.items()}
    from ebike_swap_sim.aggregate import AggregationError
    with pytest.raises(AggregationError):
        mdl.agg.decompose(noisy)                     # strict default tolerance 1e-6
    seen = {}
    orig = mdl.agg.decompose

    def spy(values, tol=1e-6):
        seen["tol"] = tol
        return orig(values, tol=tol)
    mdl.agg.decompose = spy
    again = mdl.extract_schedule()
    assert seen["tol"] >= 1e-5 and again.x.keys() == sched.x.keys()
    assert set(mdl.agg.decompose(noisy, tol=seen["tol"])) == set(sched.x)
