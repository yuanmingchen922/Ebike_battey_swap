"""Tests of the rolling-horizon wrapper (``ebike_swap_sim.rolling``; plan item M7,
SC-2 of ``notes/E2_formulation_review.md``).

* With every order known (``lambda = inf``) and ``W = H`` the wrapper reproduces the
  offline E2 optimum on the toy (J* = 12.5) and on a small synthetic instance, for a
  single epoch and for commit steps ``k < H`` (principle of optimality on the exact
  carried state: (16) with ``N^0``, constant arrivals in (13), held bikes, (22)).
* Stitched online schedules pass every hard family of ``evaluate.check`` ((5)-(8),
  (10)-(16), (20)-(22), domains) and the conservation identity (24), also when bikes
  are held by in-progress arcs and transfers are in transit at an epoch.
* Window orders keep the day objective up to a constant ((31) and the SC-3 identity).
"""
from __future__ import annotations

import math

import pytest

pytest.importorskip("gurobipy")

from ebike_swap_sim import build_arcs, ilp, toy_instance
from ebike_swap_sim.rolling import (
    BootstrapForecast,
    hard_families_ok,
    lookahead_slots,
    offline_vs_online,
    rolling_horizon,
    window_instance,
)
from experiments.common import make_instance, pruning_for

EXACT = {"MIPGap": 0.0}
TOL = 1e-6


@pytest.fixture(scope="module")
def small():
    """Small synthetic instance (3 bikes, 8 orders, H = 16, co-located sites, written
    targets rho = 0.5, R_end = 1), its pruned library and the offline optimum."""
    inst = make_instance("small", seed=0, n_bikes=3, n_orders=8, H=16)
    pr = pruning_for(inst)
    lib = build_arcs(inst, **pr)
    sched, st = ilp.solve(inst, lib, threads=3, time_limit=120, params=EXACT)
    assert st["status"] == "OPTIMAL"
    return inst, pr, lib, st["obj"]


@pytest.fixture(scope="module")
def separated():
    """Separated layout (swap-only sites + charge hub, 12 transfer services)."""
    inst = make_instance("small", seed=1, n_bikes=3, n_orders=8, H=16,
                         facilities_spec={"mode": "separated"})
    pr = pruning_for(inst)
    lib = build_arcs(inst, **pr)
    sched, st = ilp.solve(inst, lib, threads=3, time_limit=120, params=EXACT)
    assert st["status"] == "OPTIMAL"
    return inst, pr, lib, st["obj"]


def _families(res):
    return {f: v["count"] for f, v in res.check["families"].items() if v["count"]}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def test_lookahead_slots():
    inst = toy_instance()                      # Delta = 5 min
    assert lookahead_slots(inst, 0) == 0
    assert lookahead_slots(inst, 10) == 2
    assert lookahead_slots(inst, 12) == 2
    assert math.isinf(lookahead_slots(inst, None))
    assert math.isinf(lookahead_slots(inst, math.inf))
    with pytest.raises(ValueError):
        lookahead_slots(inst, -1)


def test_window_orders_keep_day_objective_up_to_a_constant():
    """theta'(u') + w Delta (t0 - r)^+ = theta(u' + t0) on every window delivery arc and
    P' + w Delta (t0 - r)^+ = P ((31), (6); SC-3 identity at the window start)."""
    inst = toy_instance()
    t0 = 3
    states = {b.id: ("A", t0, 2) for b in inst.bikes}
    wi = window_instance(inst, t0, 5, states, inst.orders, last=True, targets=True)
    wlib = build_arcs(wi, strict=False)
    D = inst.disc.Delta_h
    n_checked = 0
    for o in inst.orders:
        s = max(0, t0 - o.r)
        wo = wi.order(o.id)
        assert wo.P + o.w * D * s == pytest.approx(o.P)
        for a in wlib.delivery_arcs(o.id):
            assert a.theta + o.w * D * s == pytest.approx(inst.theta(o.id, a.u + t0))
            n_checked += 1
    assert n_checked > 0


def test_window_instance_targets_and_slicing():
    inst = make_instance("small", seed=0, n_bikes=3, n_orders=8, H=16,
                         facilities_spec={"mode": "separated"})
    states = {b.id: (b.v0, 4, b.q0) for b in inst.bikes}
    mid = window_instance(inst, 4, 6, states, inst.orders, last=False, targets=False)
    assert mid.H == 6 and mid.rho == 0.0
    assert all(f.R_end == 0 for f in mid.facilities)
    assert mid.options["dummy_terminal_cost"] == 0.0
    assert all(0 <= s.l < s.u <= 6 for s in mid.services)
    assert {s.id for s in mid.services} == {s.id for s in inst.services if s.l >= 4 and s.u <= 10}
    for g, lim in mid.P_grid.items():
        assert lim == inst.P_grid[g][4:10]
    end = window_instance(inst, 10, 6, states, inst.orders, last=True, targets=True,
                          final_targets="written")
    assert end.rho == inst.rho
    assert [f.R_end for f in end.facilities] == [f.R_end for f in inst.facilities]
    assert end.options["dummy_terminal_cost"] == inst.options.get("dummy_terminal_cost")
    m1 = window_instance(inst, 10, 6, states, inst.orders, last=True, targets=True,
                         final_targets="m1")
    for f, f0 in zip(m1.facilities, inst.facilities):
        assert f.R_end == (0 if (f0.swap and not f0.charge) else f0.R_end)
    rel = window_instance(inst, 10, 6, states, inst.orders, last=True, targets=True,
                          final_targets="relaxed")
    assert rel.rho == 0.0 and all(f.R_end == 0 for f in rel.facilities)


# ---------------------------------------------------------------------------
# lambda = inf, W = H reproduces the offline optimum
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("k", [8, 2, 1])
def test_toy_full_information_reproduces_offline(k):
    res = rolling_horizon(toy_instance(), W=8, k=k, lookahead_min=math.inf, params=EXACT)
    assert res.total == pytest.approx(12.5, abs=TOL)
    assert res.check["ok"], _families(res)
    assert res.check["identity_24_ok"]


def test_toy_epochs_carry_held_bikes_and_transfers_in_transit():
    """k = 1: at t0 = 1 both bikes are inside their first delivery (held), at t0 = 2 the
    C -> A battery of service 1 is in transit ((13) constant arrival, (24))."""
    res = rolling_horizon(toy_instance(), W=8, k=1, lookahead_min=math.inf, params=EXACT)
    assert any(w["n_busy"] > 0 for w in res.windows)
    assert any(w["n_in_transit"] > 0 for w in res.windows)
    assert res.total == pytest.approx(12.5, abs=TOL)


@pytest.mark.parametrize("k", [16, 4])
def test_small_full_information_reproduces_offline(small, k):
    inst, pr, lib, opt = small
    res = rolling_horizon(inst, W=inst.H, k=k, lookahead_min=None, lib=lib, arc_options=pr,
                          params=EXACT)
    assert res.total == pytest.approx(opt, abs=1e-5)
    assert res.check["ok"], _families(res)


def test_separated_full_information_reproduces_offline_with_aggregate(separated):
    inst, pr, lib, opt = separated
    res = rolling_horizon(inst, W=inst.H, k=inst.H, lookahead_min=math.inf, lib=lib,
                          arc_options=pr, params=EXACT, aggregate=True)
    assert res.total == pytest.approx(opt, abs=1e-5)
    assert res.check["ok"], _families(res)


# ---------------------------------------------------------------------------
# online: hard families and (24) on stitched schedules
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("W,k,lam", [(4, 2, 0), (4, 1, 0), (3, 1, 10), (8, 2, 0), (6, 2, math.inf)])
def test_toy_online_stitched_schedule_is_feasible(W, k, lam):
    res = rolling_horizon(toy_instance(), W=W, k=k, lookahead_min=lam, params=EXACT)
    assert res.hard_ok, _families(res)
    assert res.check["identity_24_ok"]
    assert hard_families_ok(res.check)
    assert res.total >= 12.5 - TOL               # a policy: upper bound on the optimum
    assert all(w["status"] == "OPTIMAL" for w in res.windows)


def test_toy_value_of_information():
    out = offline_vs_online(toy_instance(), lookaheads_min=(0.0, None), params=EXACT,
                            W=8, k=2)
    assert out["offline"]["total"] == pytest.approx(12.5)
    by_lam = {row["lookahead_min"]: row for row in out["rolling"]}
    # order 3 (r = 4) is unknown when the C -> A shuttle (l = 1) must leave
    assert by_lam[0.0]["voi"] == pytest.approx(106.0 - 12.5)
    assert by_lam[math.inf]["voi"] == pytest.approx(0.0, abs=TOL)


@pytest.mark.parametrize("W,k,lam,targets", [(8, 4, 0, "written"), (8, 2, 10, "m1"),
                                             (6, 3, 20, "relaxed")])
def test_small_online_stitched_schedule_is_feasible(small, W, k, lam, targets):
    inst, pr, lib, opt = small
    res = rolling_horizon(inst, W=W, k=k, lookahead_min=lam, lib=lib, arc_options=pr,
                          final_targets=targets, params=EXACT)
    assert res.hard_ok, _families(res)
    assert res.check["identity_24_ok"]
    assert res.total >= opt - 1e-5
    if targets == "written" and not any(w["fallback"] for w in res.windows):
        assert res.check["ok"], _families(res)


def test_separated_online_with_held_bikes(separated):
    inst, pr, lib, opt = separated
    res = rolling_horizon(inst, W=6, k=1, lookahead_min=0, lib=lib, arc_options=pr, params=EXACT)
    assert any(w["n_busy"] > 0 for w in res.windows)
    assert res.hard_ok, _families(res)
    assert res.check["identity_24_ok"]
    assert res.total >= opt - 1e-5


# ---------------------------------------------------------------------------
# forecast mode (M7 battery plan)
# ---------------------------------------------------------------------------
def test_bootstrap_forecast_uses_generator_law(small):
    inst, *_ = small
    fc = BootstrapForecast(inst)
    assert fc.source == "generator_profile" and fc.exact
    import numpy as np
    rng = np.random.default_rng(0)
    t_info = 3
    known = [o for o in inst.orders if o.r <= t_info]
    out = fc.sample(t_info, 0, inst.H, rng, known=known)
    assert len(out) == len(inst.orders) - len(known)       # exact count, whole horizon
    assert all(o.r > t_info and o.a >= o.r and o.b >= o.r for o in out)
    assert len({o.id for o in out}) == len(out)
    released = BootstrapForecast(inst, pool="released")
    assert released.sample(-1, 0, inst.H, rng, known=[]) == []


def test_forecast_mode_dispatches_known_orders_only(small):
    inst, pr, lib, opt = small
    res = rolling_horizon(inst, W=8, k=4, lookahead_min=0, lib=lib, arc_options=pr,
                          forecast=BootstrapForecast(inst), n_scenarios=2, params=EXACT)
    assert res.hard_ok, _families(res)
    assert res.check["identity_24_ok"]
    assert any(w["n_forecast"] > 0 for w in res.windows)
    assert all(w["plan_fix"] in ("all", "transfers", "none") for w in res.windows)
    day_ids = {o.id for o in inst.orders}
    assert set(res.schedule.u) == day_ids
    assert res.total >= opt - 1e-5


def test_forecast_mode_on_toy_with_transfers():
    res = rolling_horizon(toy_instance(), W=8, k=2, lookahead_min=0,
                          forecast=BootstrapForecast(toy_instance()), n_scenarios=3,
                          forecast_seed=1, params=EXACT)
    assert res.hard_ok, _families(res)
    assert res.check["identity_24_ok"]
    assert res.total >= 12.5 - TOL


def test_invalid_arguments():
    inst = toy_instance()
    with pytest.raises(ValueError):
        rolling_horizon(inst, W=2, k=3)
    with pytest.raises(ValueError):
        rolling_horizon(inst, final_targets="bogus")
    with pytest.raises(ValueError):
        rolling_horizon(inst, window_targets="bogus")
