"""Rolling-horizon wrapper around the unchanged E2 ILP (plan item M7 of
``notes/reading_to_model.md``; SC-2 of ``notes/E2_formulation_review.md``; planned
experiment E7).

Purpose
-------
The E2u / E8 headline compares a full-information offline optimum (every order known
at ``t = 0``) with an online rule.  This module re-solves E2 on a moving window with
only the orders released so far (plus a look-ahead ``lambda``), commits the first
``k`` slots, carries the physical state forward and prices the stitched day with the
same ``evaluate.cost`` / ``evaluate.check`` as every other schedule.  The difference
offline vs rolling is the value of (perfect) information; with the optional forecast
mode the battery side (charging, transfers) is planned on sampled future orders while
riders are dispatched to known orders only, which splits that value into a
battery-side and a rider-side part (M7).

Wrapper (E2 (1)-(33) unchanged inside every window)
---------------------------------------------------
Epochs ``t0 = 0, k, 2k, ...`` while ``t0 < H``; the window is ``[t0, t0 + W']``
with ``W' = min(W, H - t0)``; a window *reaches the end* when ``t0 + W >= H`` and the
*final* epoch is the first with ``t0 + k >= H``.  At every epoch the window instance (:func:`window_instance`) is the base instance with

* time shifted by ``-t0`` (``H' = W'``, grid limits ``P^grid_gt`` (21) and prices
  ``pi_jt`` (28) sliced);
* orders ``I(t0) = {i : r_i <= t0 + lambda, not served by a committed arc}``; release
  and ready times are clamped at the window start, ``b_i`` is shifted, and the
  unserved penalty becomes ``P_i - w_i Delta (t0 - r_i)^+`` so that, by (6), the
  window objective equals the day objective (26) minus a constant (the SC-3 identity
  applied to the window start; (31) unchanged);
* bike sources ``s_k = (v_k, 0, q_k)`` = the end node of the last committed arc; a bike
  whose committed arc is still in progress at ``t0`` (it ends at ``u > t0``) starts at
  that arc's end node and is held there by its wait arcs until ``u - t0``
  (non-anticipativity: committed ``x_ka`` fixed; (5) unchanged);
* station stock: the initial-stock row (16) takes ``N^0_jq`` = the simulated stock
  ``n_{j q t0}`` of the (13) recursion over the committed decisions (``N^0`` given as
  data, formulation review section 8);
* committed transfers in transit (``l_e < t0 < u_e``) enter (13) as constant arrivals
  ``A_jqt``; committed swaps still occupying a position enter (22) as constants;
* targets (9), (17), (18) only in windows that reach the end ``H`` (earlier windows:
  ``R_end_j = 0``, ``rho = 0`` and a zero-cost dummy terminal arc, i.e. a free end
  state); those windows use the written targets, the M1 parameter variant (``R_end_j = 0`` at
  swap-only sites) or the relaxed control (``rho = R_end_j = 0``);
* facilities ``y, B, C`` fixed to the data, to ``facility_values`` or to the first
  window's decision (they cannot change within a day);
* the arcs (and charging / transfer decisions) that start before ``t0 + k`` are
  committed (all of them at the final epoch).

The stitched schedule is priced ex post over the whole day with ``evaluate.cost``
(26)-(32) and verified with ``evaluate.check`` (5)-(22), (24).  Sequential window
solves are a feasible policy, so the rolling total is an upper bound on the offline
optimum; with ``lambda = infinity`` and ``W = H`` the single window is the offline
model and reproduces its optimum.

Forecast mode (M7 battery plan)
-------------------------------
With ``forecast=`` (e.g. :class:`BootstrapForecast`) every epoch first solves the
window ``n_scenarios`` times with the known orders plus sampled future orders
(released in ``(t0 + lambda, t0 + W')``); the charging ``c`` and transfer ``h, z``
decisions of the commit period are aggregated (lower median per entry) into a
battery plan.  The dispatch window is then solved with known orders only and the
plan fixed in the commit period (fallbacks: transfers only, then nothing, recorded
per window).  Bike arcs are always taken from the dispatch solve.

Gurobi lives in ``ilp.py``; it is imported lazily here so that the module imports
without gurobipy.  The aggregated model (O1, ``build_model(..., aggregate=True)``) is
used when requested, supported by the installed ``ilp.build_model`` and no bike is
held by an in-progress arc (the hold is a per-bike restriction); otherwise the window
is solved with the per-bike model (recorded per window).
"""
from __future__ import annotations

import inspect
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .arcs import SINK, Arc, ArcLibrary, build_arcs
from .evaluate import Schedule, check, cost, reconstruct_inventory
from .or_instance import Bike, Instance, Order

__all__ = [
    "RollingHorizonError", "RollingResult", "BootstrapForecast", "HARD_EXEMPT_FAMILIES",
    "FINAL_TARGETS", "WINDOW_TARGETS", "lookahead_slots", "window_instance",
    "rolling_horizon", "hard_families_ok", "forecast_facility_plan", "offline_vs_online",
]

#: Families of ``evaluate.check`` that are targets / reporting rows rather than
#: physical feasibility: (9) terminal certificate, (17)-(18) end targets, (33) budget /
#: service share.  Every other family plus identity (24) is "hard" for a stitched
#: rolling schedule.
HARD_EXEMPT_FAMILIES = ("(9)", "(17)", "(18)", "(33)")
#: ``final_targets`` values: written (9), (17), (18); M1 variant (``R_end_j = 0`` at
#: swap-only sites, ``rho`` as written); relaxed control (``rho = R_end_j = 0``).
FINAL_TARGETS = ("written", "m1", "relaxed")
#: ``window_targets`` values: targets only in windows reaching ``H``, or in every window.
WINDOW_TARGETS = ("last", "every")


class RollingHorizonError(RuntimeError):
    """A window could not be solved (no incumbent) or a committed arc has no
    counterpart in the full-day arc library."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def lookahead_slots(inst: Instance, lookahead_min: Optional[float]) -> float:
    """Look-ahead ``lambda`` of M7 / SC-2 in slots: ``floor(lambda_min / Delta_min)``;
    ``None`` or ``inf`` give ``inf`` (every order known from ``t = 0``).  An order ``i``
    is known at epoch ``t0`` iff ``r_i <= t0 + lambda``."""
    if lookahead_min is None or math.isinf(float(lookahead_min)):
        return math.inf
    if lookahead_min < 0:
        raise ValueError("lookahead_min must be >= 0")
    delta_min = inst.disc.Delta_h * 60.0
    return float(math.floor(float(lookahead_min) / delta_min + 1e-9))


def hard_families_ok(report: Dict[str, Any],
                     exempt: Sequence[str] = HARD_EXEMPT_FAMILIES) -> bool:
    """True iff an ``evaluate.check`` report has no violation outside ``exempt``
    ((9), (17), (18), (33) by default) and identity (24) holds (plan item M7)."""
    for fam, rec in report["families"].items():
        if rec.get("count") and fam not in exempt:
            return False
    return bool(report.get("identity_24_ok", True))


def _shift_order(o: Order, t0: int, delta_h: float, new_id: Any = None) -> Order:
    """Order ``o`` seen from a window starting at ``t0`` (M7; (31) with the SC-3 identity):
    ``r' = (r - t0)^+``, ``a' = (a - t0)^+``, ``b' = b - t0`` and
    ``P' = P - w Delta (t0 - r)^+``, so that ``theta'(u') + w Delta (t0 - r)^+ =
    theta(u' + t0)`` and ``P' + w Delta (t0 - r)^+ = P``."""
    s = max(0, t0 - o.r)
    return Order(id=o.id if new_id is None else new_id, o=o.o, d=o.d, r=max(o.r - t0, 0),
                 a=max(o.a - t0, 0), b=o.b - t0, hp=o.hp, hd=o.hd,
                 P=o.P - o.w * delta_h * s, w=o.w, v=o.v, platform=o.platform)


def _window_targets(inst: Instance, final_targets: str, final_rho: Optional[float]
                    ) -> Tuple[Dict[Any, int], float]:
    """``({facility: R_end_j}, rho)`` of a window reaching ``H`` (M1 parameter variants; E2
    (17)-(18) unchanged)."""
    if final_targets not in FINAL_TARGETS:
        raise ValueError(f"final_targets must be one of {FINAL_TARGETS}")
    if final_targets == "relaxed":
        r_end = {f.id: 0 for f in inst.facilities}
        rho = 0.0
    elif final_targets == "m1":
        r_end = {f.id: (0 if (f.swap and not f.charge) else int(f.R_end)) for f in inst.facilities}
        rho = float(inst.rho)
    else:
        r_end = {f.id: int(f.R_end) for f in inst.facilities}
        rho = float(inst.rho)
    if final_rho is not None:
        rho = float(final_rho)
    return r_end, rho


def window_instance(inst: Instance, t0: int, W: int, bike_states: Dict[Any, Tuple[Any, int, int]],
                    orders: Iterable[Order], *, last: bool, targets: bool,
                    final_targets: str = "written", final_rho: Optional[float] = None,
                    facility_values: Optional[Dict[Any, Tuple[int, int, int]]] = None,
                    extra_orders: Iterable[Order] = ()) -> Instance:
    """Window instance of the rolling horizon at epoch ``t0`` (plan item M7, SC-2).

    ``bike_states[k] = (v, t_free, q)`` in day time (``t_free >= t0``: the bike's source
    in the window is ``(v, 0, q)``; the hold until ``t_free - t0`` is imposed on the
    model, not here).  ``orders`` are day orders, shifted by :func:`_shift_order` (E2
    (31) via the SC-3 identity); ``extra_orders`` (forecast scenarios) likewise.
    Services with ``t0 <= l_e`` and ``u_e <= t0 + W'`` are kept with shifted times
    (11); grid limits (21) and prices (28) are sliced.  With ``targets`` the window
    keeps (9) and uses the end targets (17)-(18) of ``final_targets``; without,
    ``R_end_j = 0``, ``rho = 0`` and a zero-cost dummy terminal arc leaves every
    ``(v, H', q)`` (free end state of an intermediate window).  Facilities are fixed
    to ``facility_values[j] = (y, B, C)`` when given.  The shifted instance is not
    passed through ``Instance.validate`` (``b'`` may be negative)."""
    H = inst.H
    Wp = min(int(W), H - int(t0))
    if Wp < 1:
        raise ValueError("empty window")
    disc = replace(inst.disc, H=Wp)
    bikes = [Bike(b.id, bike_states[b.id][0], int(bike_states[b.id][2])) for b in inst.bikes]
    wo = [_shift_order(o, t0, inst.disc.Delta_h) for o in orders]
    wo += [_shift_order(o, t0, inst.disc.Delta_h) for o in extra_orders]
    r_end, rho = _window_targets(inst, final_targets, final_rho)
    facs = []
    for f in inst.facilities:
        kw: Dict[str, Any] = {}
        if facility_values is not None and f.id in facility_values:
            yv, Bv, Cv = facility_values[f.id]
            kw.update(y=int(yv), B=int(Bv), C=int(Cv))
        kw["R_end"] = int(r_end[f.id]) if targets else 0
        facs.append(replace(f, **kw))
    services = [replace(s, l=s.l - t0, u=s.u - t0) for s in inst.services
                if s.l >= t0 and s.u <= t0 + Wp]
    P_grid = {g: [float(v) for v in lim[t0:t0 + Wp]] for g, lim in inst.P_grid.items()}
    if isinstance(inst.pi, dict):
        pi: Any = {(j, t - t0): p for (j, t), p in inst.pi.items() if t0 <= t < t0 + Wp}
    else:
        pi = inst.pi
    options = dict(inst.options)
    options["lexicographic"] = False
    if not targets:
        options["dummy_terminal_cost"] = 0.0
    free_fac = any(f.y is None or f.B is None or f.C is None for f in facs)
    meta = {"name": f"{inst.meta.get('name', 'instance')}@rolling[t0={t0},W={Wp}]",
            "rolling_window": {"t0": int(t0), "W": int(Wp), "last": bool(last),
                               "targets": bool(targets), "final_targets": final_targets}}
    return Instance(disc=disc, nodes=list(inst.nodes), routes=inst.routes, bikes=bikes,
                    orders=wo, facilities=facs, services=services, P_grid=P_grid,
                    kappa=inst.kappa, pi=pi, q_res=inst.q_res, rho=rho if targets else 0.0,
                    budget=inst.budget if free_fac else None, zeta=None,
                    options=options, meta=meta)


# ---------------------------------------------------------------------------
# forecast demand model (M7 battery plan)
# ---------------------------------------------------------------------------
class BootstrapForecast:
    """Forecast of future orders for the M7 battery plan, built from the generator's
    demand model where the instance records it.

    Release times: when ``inst.meta['params']`` holds the generator's demand spec
    (``profile``, ``window_start_h``, ``tail_slots``, ``n_orders``, ``exact_count``),
    the slot weights are the generator's intensity ``lambda(hour)``
    (``generator.TimeDependentGenerator``) on the release slots ``0 .. H - tail - 1``;
    with ``exact_count`` the remaining count ``N - #released`` is known and the future
    releases are i.i.d. with density proportional to ``lambda`` after the information
    time -- exactly the generator's conditional law.  Otherwise (toy, NYC builder) the
    weights are uniform on ``0 .. H - 1`` and the count is Poisson with mean ``|I| / H``
    per slot.

    Attributes (restaurant, customer, prep ``a - r``, promise ``b - r``, ``hp, hd, P, w,
    v``, platform) are bootstrapped from a pool: ``pool='all'`` (default) uses every
    order of the instance as a proxy of the generator's i.i.d. OD / prep samplers (the
    attributes, not their release times, of the realised orders); ``pool='released'``
    uses only the orders already known at the information time (no realised future
    attributes at all; no forecast while nothing is known)."""

    def __init__(self, inst: Instance, pool: str = "all") -> None:
        if pool not in ("all", "released"):
            raise ValueError("pool must be 'all' or 'released'")
        self.inst = inst
        self.pool = pool
        self.H = inst.H
        self.weights, self.n_total, self.exact, self.source = self._release_model(inst)
        self.attrs = [self._attr(o) for o in inst.orders]

    @staticmethod
    def _attr(o: Order) -> Tuple:
        return (o.o, o.d, o.a - o.r, o.b - o.r, o.hp, o.hd, o.P, o.w, o.v, o.platform)

    @staticmethod
    def _release_model(inst: Instance) -> Tuple[np.ndarray, float, bool, str]:
        H = inst.H
        params = (inst.meta or {}).get("params") or {}
        dem = params.get("demand_spec") or {}
        try:
            from .generator import TimeDependentGenerator
            profile = dem["profile"]
            start = float(dem["window_start_h"])
            tail = int(dem.get("tail_slots", 0))
            n_orders = float(params.get("n_orders") or len(inst.orders))
            day_type = str(params.get("day_type") or "weekday")
            rel_slots = max(1, H - tail)
            dh = inst.disc.Delta_h
            gen = TimeDependentGenerator(profile, (start, start + rel_slots * dh), n_orders,
                                         day_type=day_type)
            w = np.zeros(H)
            for t in range(min(rel_slots, H)):
                w[t] = np.mean([gen.rate(start + (t + f) * dh) for f in (0.125, 0.375, 0.625, 0.875)])
            if w.sum() <= 0:
                raise ValueError("zero intensity")
            return w / w.sum(), n_orders, bool(dem.get("exact_count", True)), "generator_profile"
        except Exception:   # noqa: BLE001 -- any missing field: documented uniform fallback
            w = np.full(H, 1.0 / H)
            return w, float(len(inst.orders)), False, "uniform"

    def sample(self, t_info: float, t_from: int, t_to: int, rng: np.random.Generator,
               known: Sequence[Order] = (), prefix: str = "fc") -> List[Order]:
        """Sample future orders with release ``r`` in ``[t_from, t_to)`` (day slots) given
        the information time ``t_info`` (orders with ``r <= t_info`` are known and passed
        as ``known``).  Returns new :class:`Order` objects with ids ``f"{prefix}_{n}"``."""
        H = self.H
        t_from = max(int(t_from), 0)
        t_to = min(int(t_to), H)
        if t_to <= t_from:
            return []
        if self.pool == "released":
            pool = [self._attr(o) for o in known]
        else:
            pool = self.attrs
        if not pool:
            return []
        first_unknown = int(math.floor(t_info)) + 1 if not math.isinf(t_info) else H
        first_unknown = max(first_unknown, 0)
        if first_unknown >= H:
            return []
        w_future = self.weights.copy()
        w_future[:first_unknown] = 0.0
        mass_future = float(w_future.sum())
        if mass_future <= 0:
            return []
        if self.exact:
            n_known = sum(1 for o in self.inst.orders if o.r <= t_info) if not known else len(known)
            m = max(0, int(round(self.n_total)) - n_known)
            slots = rng.choice(H, size=m, p=w_future / mass_future) if m else np.array([], int)
        else:
            lam = self.n_total * w_future
            counts = rng.poisson(lam)
            slots = np.repeat(np.arange(H), counts)
        out: List[Order] = []
        n = 0
        for r in sorted(int(s) for s in slots):
            if not (t_from <= r < t_to) or r < first_unknown:
                continue
            o_node, d_node, prep, prom, hp, hd, P, w, v, plat = pool[int(rng.integers(len(pool)))]
            out.append(Order(id=f"{prefix}_{n}", o=o_node, d=d_node, r=r, a=r + int(prep),
                             b=r + int(prom), hp=hp, hd=hd, P=P, w=w, v=v, platform=plat))
            n += 1
        return out


# ---------------------------------------------------------------------------
# result container
# ---------------------------------------------------------------------------
@dataclass
class RollingResult:
    """Outcome of :func:`rolling_horizon` (plan item M7).

    ``schedule`` is the stitched day :class:`Schedule` on ``lib`` (the full-day arc
    library of ``inst``); ``cost`` = ``evaluate.cost`` (26)-(32) and ``check`` =
    ``evaluate.check`` (5)-(22), (24) of it; ``hard_ok`` = :func:`hard_families_ok`;
    ``windows`` one dict per epoch (``t0, W, reaches_end, final, n_known, n_forecast, n_arcs, status,
    obj, gap, runtime, aggregate, n_busy, n_in_transit, plan_fix, fallback``);
    ``params`` the call parameters; ``runtime`` wall time in seconds."""
    inst: Instance
    lib: ArcLibrary
    schedule: Schedule
    cost: Dict[str, Any]
    check: Dict[str, Any]
    hard_ok: bool
    windows: List[Dict[str, Any]]
    params: Dict[str, Any]
    runtime: float
    notes: List[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        """Ex-post day cost (26) of the stitched schedule."""
        return float(self.cost["total"])

    def summary(self) -> Dict[str, Any]:
        """Flat JSON-safe record: totals, components, check outcome, window stats."""
        c = self.cost
        fam = {k: v["count"] for k, v in self.check["families"].items() if v.get("count")}
        return {
            "total": c["total"], "C_setup": c["C_setup"], "C_elec": c["C_elec"],
            "C_travel": c["C_travel"], "C_orders": c["C_orders"], "C_reb": c["C_reb"],
            "unserved": c["C_orders_parts"]["unserved"], "response": c["C_orders_parts"]["response"],
            "lateness": c["C_orders_parts"]["lateness"],
            "C_end_adjust": c.get("C_end_adjust"), "total_end_adjusted": c.get("total_end_adjusted"),
            "n_unserved": int(sum(1 for v in self.schedule.u.values() if v)),
            "check_ok": bool(self.check["ok"]), "hard_ok": bool(self.hard_ok),
            "identity_24_ok": bool(self.check.get("identity_24_ok", True)),
            "violations": fam, "n_windows": len(self.windows),
            "window_runtime": float(sum(w.get("runtime") or 0.0 for w in self.windows)),
            "max_window_gap": max([w.get("gap") or 0.0 for w in self.windows] or [0.0]),
            "statuses": sorted({str(w.get("status")) for w in self.windows}),
            "fallbacks": [w["fallback"] for w in self.windows if w.get("fallback")],
            "plan_fix": [w.get("plan_fix") for w in self.windows if w.get("plan_fix")],
            "runtime": self.runtime, **{f"param_{k}": v for k, v in self.params.items()
                                        if isinstance(v, (int, float, str, bool, type(None)))},
        }


# ---------------------------------------------------------------------------
# model surgery on a built window model (carried state; no E2 row is changed)
# ---------------------------------------------------------------------------
def _ilp():
    from . import ilp   # lazy: gurobipy
    return ilp


def _row_vars(model: Any, con: Any) -> Dict[int, float]:
    row = model.getRow(con)
    return {row.getVar(p).index: row.getCoeff(p) for p in range(row.size())}


def _set_initial_stock(mdl: Any, N0: Dict[Tuple[Any, int], int], Bval: Dict[Any, int]) -> int:
    """Give (16) the carried stock ``N^0_jq`` (data, M7/SC-2): the row ``n_jL0 - B_j = 0``
    gets right-hand side ``N^0_jL - B_j`` (``B_j`` fixed) and ``n_jq0 = 0`` gets
    ``N^0_jq``.  Rows are found through the columns of ``n_jq0``; returns the number
    of rows changed."""
    m = mdl.model
    L = mdl.inst.L
    changed = 0
    for f in mdl.inst.facilities:
        j = f.id
        b_idx = mdl.B[j].index
        for q in range(L + 1):
            var = mdl.n[j, q, 0]
            col = m.getCol(var)
            found = False
            for p in range(col.size()):
                con = col.getConstr(p)
                if con.Sense != "=":
                    continue
                rv = _row_vars(m, con)
                if not set(rv) <= {var.index, b_idx}:
                    continue
                target = int(N0.get((j, q), 0))
                con.RHS = float(target - int(Bval[j])) if q == L else float(target)
                found = True
                changed += 1
                break
            if not found:
                raise RollingHorizonError(f"row (16) of n[{j},{q},0] not found")
    return changed


def _add_arrival(mdl: Any, j: Any, q: int, t: int, amount: int) -> None:
    """Add a constant arrival ``A_jqt = amount`` (committed transfer in transit) to the
    (13) row ``n_{jq,t} - n_{jq,t-1} + ... = 0`` (window time ``t >= 1``)."""
    m = mdl.model
    nxt, prev = mdl.n[j, q, t], mdl.n[j, q, t - 1]
    col = m.getCol(nxt)
    for p in range(col.size()):
        con = col.getConstr(p)
        if con.Sense != "=":
            continue
        rv = _row_vars(m, con)
        if rv.get(nxt.index) == 1.0 and rv.get(prev.index) == -1.0:
            con.RHS = con.RHS + float(amount)
            return
    raise RollingHorizonError(f"row (13) of n[{j},{q},{t}] not found")


def _model_arcs(mdl: Any) -> List[Arc]:
    agg = getattr(mdl, "agg", None)
    return list(agg.arcs) if agg is not None else list(mdl.lib.arcs)


def _supports_aggregate() -> bool:
    try:
        return "aggregate" in inspect.signature(_ilp().build_model).parameters
    except Exception:   # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# one window
# ---------------------------------------------------------------------------
def _solve_window(winst: Instance, *, t0: int, holds: Dict[Any, int],
                  N0: Optional[Dict[Tuple[Any, int], int]], Bval: Dict[Any, int],
                  arrivals: Dict[Tuple[Any, int, int], int], occupancy: Dict[Tuple[Any, int], int],
                  plan: Optional[Dict[str, Any]], plan_mode: str, commit_until: int,
                  arc_options: Dict[str, Any], fixed_facilities: Optional[bool], aggregate: bool,
                  threads: int, time_limit: float, params: Optional[Dict[str, Any]]
                  ) -> Tuple[Optional[Schedule], ArcLibrary, Dict[str, Any]]:
    """Build the window ILP (E2 via ``ilp.build_model``), apply the carried state
    (M7/SC-2: (16) with ``N^0``, constant arrivals in (13), constant occupancy in
    (22), held bikes, fixed battery plan) and optimise.  Returns ``(schedule or
    None, window library, stats)``."""
    import gurobipy as gp
    from gurobipy import GRB
    ilp = _ilp()
    t_start = time.perf_counter()
    wlib = build_arcs(winst, strict=False, **arc_options)
    use_agg = bool(aggregate and _supports_aggregate() and not any(holds.values()))
    kw: Dict[str, Any] = {}
    if use_agg:
        kw["aggregate"] = True
    mdl = ilp.build_model(winst, wlib, threads=int(threads), time_limit=float(time_limit),
                          params=params, fixed_facilities=fixed_facilities, **kw)
    m = mdl.model
    stats: Dict[str, Any] = {"n_arcs": len(wlib), "aggregate": use_agg,
                             "infeasible_bikes": list(wlib.infeasible_bikes)}
    if N0 is not None:
        _set_initial_stock(mdl, N0, Bval)
    for (j, q, t), amount in arrivals.items():
        if amount:
            _add_arrival(mdl, j, q, t, amount)
    # held bikes: wait at the end node of the in-progress arc until it ends
    for k, hold in holds.items():
        if hold <= 0:
            continue
        src = wlib.source(k)
        for t in range(min(hold, winst.H)):
            a = wlib.find(k, "wait", (src[0], t, src[2]))
            if a is None:
                raise RollingHorizonError(f"wait arc of held bike {k} at t={t} missing")
            mdl.x[a.id].LB = 1.0
    # committed swaps still occupying a position: constants in (22)
    if occupancy:
        occ_ids: Dict[Tuple[Any, int], List[int]] = defaultdict(list)
        for a in _model_arcs(mdl):
            if a.kind == "swap":
                for tau in range(a.l, min(a.u, winst.H)):
                    if (a.fac, tau) in occupancy:
                        occ_ids[(a.fac, tau)].append(a.id)
        for (j, tau), const in occupancy.items():
            f = winst.facility(j)
            m.addLConstr(gp.quicksum(mdl.x[i] for i in occ_ids.get((j, tau), ())) + float(const),
                         GRB.LESS_EQUAL, f.M * mdl.y[j])
    # battery plan of the forecast scenarios (commit period only)
    if plan is not None and plan_mode in ("all", "transfers"):
        if plan_mode == "all":
            for (j, q, t), var in mdl.c.items():
                if t < commit_until:
                    val = float(plan["c"].get((j, q, t), 0))
                    var.LB = val
                    var.UB = val
        for e, var in mdl.h.items():
            if winst.service(e).l < commit_until:
                val = float(plan["h"].get(e, 0))
                var.LB = val
                var.UB = val
        for (e, q), var in mdl.z.items():
            if winst.service(e).l < commit_until:
                val = float(plan["z"].get((e, q), 0))
                var.LB = val
                var.UB = val
    m.update()
    m.optimize()
    stats["status"] = ilp.status_name(m.Status)
    stats["runtime"] = float(m.Runtime)
    sched: Optional[Schedule] = None
    if m.SolCount > 0:
        stats["obj"] = float(m.ObjVal)
        try:
            stats["gap"] = float(m.MIPGap)
            stats["bound"] = float(m.ObjBound)
        except gp.GurobiError:
            stats["gap"] = stats["bound"] = None
        sched = mdl.extract_schedule()
    else:
        stats["obj"] = stats["gap"] = stats["bound"] = None
    lib_used = mdl.lib
    stats["wall"] = time.perf_counter() - t_start
    try:
        m.dispose()
        if getattr(mdl, "env", None) is not None:
            mdl.env.dispose()
    except Exception:   # noqa: BLE001
        pass
    return sched, lib_used, stats


def _battery_plan(scheds: List[Tuple[Schedule, Instance]], commit_until: int) -> Dict[str, Any]:
    """Lower-median battery plan over forecast scenarios (M7): charging ``c`` with
    ``t < commit_until`` and transfers ``h, z`` departing before ``commit_until``."""
    n = len(scheds)
    c_vals: Dict[Tuple, List[int]] = defaultdict(lambda: [0] * n)
    z_vals: Dict[Tuple, List[int]] = defaultdict(lambda: [0] * n)
    for s, (sc, wi) in enumerate(scheds):
        for key, val in sc.c.items():
            if key[2] < commit_until and val:
                c_vals[key][s] = int(val)
        for (e, q), val in sc.z.items():
            if wi.service(e).l < commit_until and val:
                z_vals[(e, q)][s] = int(val)
    med = (n - 1) // 2
    c = {k: sorted(v)[med] for k, v in c_vals.items() if sorted(v)[med]}
    z = {k: sorted(v)[med] for k, v in z_vals.items() if sorted(v)[med]}
    h: Dict[Any, int] = defaultdict(int)
    for (e, q), val in z.items():
        if val:
            h[e] = 1
    return {"c": c, "z": z, "h": dict(h), "n_scenarios": n}


# ---------------------------------------------------------------------------
# main loop
# ---------------------------------------------------------------------------
def rolling_horizon(inst: Instance, W: Optional[int] = None, k: Optional[int] = None,
                    lookahead_min: Optional[float] = 0.0, *, lib: Optional[ArcLibrary] = None,
                    arc_options: Optional[Dict[str, Any]] = None,
                    final_targets: str = "written", final_rho: Optional[float] = None,
                    window_targets: str = "last",
                    facility_values: Optional[Dict[Any, Tuple[int, int, int]]] = None,
                    forecast: Optional[BootstrapForecast] = None, n_scenarios: int = 1,
                    forecast_seed: int = 0, aggregate: bool = False, threads: int = 3,
                    time_limit: float = 60.0, params: Optional[Dict[str, Any]] = None,
                    final_fallback_cost: Optional[float] = None,
                    verbose: bool = False) -> RollingResult:
    """Rolling-horizon solution of E2 (plan item M7; SC-2 of the formulation review;
    E2 (1)-(33) unchanged inside each window, see the module docstring).

    Parameters
    ----------
    inst
        Day instance (E2 data).  With ``options['colocated']`` the co-located copy
        (``ilp.colocated_instance``) is used throughout.
    W, k
        Window length and commit step in slots (``W >= k >= 1``; defaults ``W = H``,
        ``k = W``).  Epochs ``t0 = 0, k, 2k, ...`` until ``t0 + k >= H`` (final epoch,
        everything committed).
    lookahead_min
        Look-ahead ``lambda`` in minutes (0 = strict online; ``None`` / ``inf`` = all
        orders known at ``t = 0``).  Order ``i`` enters at the first epoch with
        ``r_i <= t0 + lambda``.
    lib
        Full-day arc library of ``inst`` for the stitched schedule (built with
        ``arc_options`` when omitted).
    arc_options
        Arc-builder overrides (e.g. ``experiments.common.pruning_for``) used for the
        full-day and every window library.
    final_targets, final_rho, window_targets
        Targets (9), (17), (18): ``'written'`` / ``'m1'`` / ``'relaxed'`` (M1), optional
        ``rho`` override, in the windows reaching ``H`` (``'last'``) or in every window
        (``'every'``).
    facility_values
        ``{j: (y, B, C)}`` fixing the facilities for the whole day (e.g. the offline
        or :func:`forecast_facility_plan` decision); default: the data, and facilities
        left free by the data are decided by the first window.
    forecast, n_scenarios, forecast_seed
        M7 battery plan on sampled future orders (see the module docstring).
    aggregate
        Use the O1 aggregated model in windows without held bikes (feature-detected).
    threads, time_limit, params
        Gurobi per window (``Threads <= 3`` by the project rule; ``TimeLimit`` per
        window; extra parameters such as ``{'MIPGap': 1e-4}``).
    final_fallback_cost
        If a window reaching ``H`` is infeasible with its targets, it is re-solved with the
        relaxed targets and a dummy terminal arc of this cost (default
        ``10 * max_i P_i + 1000``); the fallback is recorded and the stitched schedule
        then reports (9) / (17) / (18) in ``evaluate.check``.

    Returns a :class:`RollingResult` whose schedule is priced with ``evaluate.cost``
    (26)-(32) and verified with ``evaluate.check`` (5)-(22), (24) on ``inst``.
    """
    t_wall = time.perf_counter()
    if final_targets not in FINAL_TARGETS:
        raise ValueError(f"final_targets must be one of {FINAL_TARGETS}")
    if window_targets not in WINDOW_TARGETS:
        raise ValueError(f"window_targets must be one of {WINDOW_TARGETS}")
    if inst.option("lexicographic"):
        raise ValueError("lexicographic objective is not supported by the rolling wrapper")
    arc_options = dict(arc_options or {})
    notes: List[str] = []
    if inst.option("colocated") and not all(f.swap and f.charge for f in inst.facilities):
        inst = _ilp().colocated_instance(inst)
        notes.append("colocated: the co-located copy of the instance is used throughout")
        lib = None
    H = inst.H
    W = H if W is None else int(W)
    k = W if k is None else int(k)
    if not (1 <= k <= W):
        raise ValueError("need 1 <= k <= W")
    lam = lookahead_slots(inst, lookahead_min)
    if lib is None:
        lib = build_arcs(inst, strict=False, **arc_options)
    elif lib.inst is not inst and lib.inst != inst:
        raise ValueError("lib was built on a different instance")
    rng = np.random.default_rng(int(forecast_seed))

    # ----------------------------------------------------------- state
    states: Dict[Any, Tuple[Any, int, int]] = {b.id: (b.v0, 0, int(b.q0)) for b in inst.bikes}
    x_c: Dict[Any, List[int]] = {b.id: [] for b in inst.bikes}
    c_c: Dict[Tuple[Any, int, int], int] = {}
    h_c: Dict[Any, int] = {}
    z_c: Dict[Tuple[Any, int], int] = {}
    served: set = set()
    occ_c: Dict[Tuple[Any, int], int] = defaultdict(int)       # committed swap occupancy (22)
    fac_vals: Optional[Dict[Any, Tuple[int, int, int]]] = (
        dict(facility_values) if facility_values is not None else None)
    if fac_vals is None and all(f.y is not None and f.B is not None and f.C is not None
                                for f in inst.facilities):
        fac_vals = {f.id: (int(f.y), int(f.B), int(f.C)) for f in inst.facilities}
    windows: List[Dict[str, Any]] = []
    default_fallback = (10.0 * max([o.P for o in inst.orders] or [100.0]) + 1000.0
                        if final_fallback_cost is None else float(final_fallback_cost))

    t0 = 0
    while True:
        last = t0 + W >= H                 # window reaches the end H: targets apply
        final = t0 + k >= H                # final epoch: commit everything
        Wp = min(W, H - t0)
        commit_until = Wp if final else k
        targets = last or window_targets == "every"
        known = [o for o in inst.orders if o.id not in served and o.r <= t0 + lam]
        holds = {kb: max(0, states[kb][1] - t0) for kb in states}
        # carried stock, in-transit arrivals, committed occupancy
        Bval = {j: v[1] for j, v in fac_vals.items()} if fac_vals is not None else {}
        N0 = None
        arrivals: Dict[Tuple[Any, int, int], int] = {}
        occupancy: Dict[Tuple[Any, int], int] = {}
        if t0 > 0:
            n_rec = reconstruct_inventory(inst, lib, x_c, c_c, z_c, Bval)
            N0 = {(f.id, q): int(n_rec[(f.id, q, t0)]) for f in inst.facilities
                  for q in range(inst.L + 1)}
            for (e, q), val in z_c.items():
                svc = inst.service(e)
                if val and svc.l < t0 < svc.u and svc.u <= t0 + Wp:
                    key = (svc.d_fac, q, svc.u - t0)
                    arrivals[key] = arrivals.get(key, 0) + int(val)
            for (j, tau), val in occ_c.items():
                if val and t0 <= tau < t0 + Wp:
                    occupancy[(j, tau - t0)] = int(val)
        n_in_transit = sum(int(v) for (e, q), v in z_c.items()
                           if v and inst.service(e).l < t0 < inst.service(e).u)
        rec: Dict[str, Any] = {"t0": t0, "W": Wp, "reaches_end": last, "final": final,
                               "n_known": len(known),
                               "n_busy": sum(1 for v in holds.values() if v > 0),
                               "n_in_transit": n_in_transit, "n_forecast": 0,
                               "plan_fix": None, "fallback": None}
        fixed_fac = True if fac_vals is not None else None

        def build(extra: Sequence[Order] = (), tgt: bool = targets, ft: str = final_targets,
                  fr: Optional[float] = final_rho, dummy: Optional[float] = None) -> Instance:
            wi = window_instance(inst, t0, W, states, known, last=last, targets=tgt,
                                 final_targets=ft, final_rho=fr, facility_values=fac_vals,
                                 extra_orders=extra)
            if dummy is not None:
                wi.options["dummy_terminal_cost"] = float(dummy)
            return wi

        common_kw = dict(t0=t0, holds=holds, N0=N0, Bval=Bval, arrivals=arrivals,
                         occupancy=occupancy, commit_until=commit_until, arc_options=arc_options,
                         fixed_facilities=fixed_fac, aggregate=aggregate, threads=threads,
                         time_limit=time_limit, params=params)

        # ------------------------------------------- forecast battery plan (M7)
        plan = None
        if forecast is not None and n_scenarios > 0 and not math.isinf(lam):
            scen: List[Tuple[Schedule, Instance]] = []
            n_fc = []
            for s in range(int(n_scenarios)):
                extra = forecast.sample(t0 + lam, t0, t0 + Wp, rng, known=[
                    o for o in inst.orders if o.r <= t0 + lam], prefix=f"fc{t0}_{s}")
                n_fc.append(len(extra))
                wi = build(extra)
                sc, _, st = _solve_window(wi, plan=None, plan_mode="none", **common_kw)
                if sc is not None:
                    scen.append((sc, wi))
            rec["n_forecast"] = float(np.mean(n_fc)) if n_fc else 0
            if scen:
                plan = _battery_plan(scen, commit_until)

        # ------------------------------------------------- dispatch solve
        sched = None
        attempts: List[Tuple[str, Dict[str, Any]]] = []
        modes = ["all", "transfers", "none"] if plan is not None else ["none"]
        for mode in modes:
            wi = build()
            sched, wlib, st = _solve_window(wi, plan=plan, plan_mode=mode, **common_kw)
            attempts.append((mode, st))
            if sched is not None:
                rec["plan_fix"] = mode if plan is not None else None
                break
        if sched is None and last:
            wi = build(tgt=True, ft="relaxed", fr=0.0, dummy=default_fallback)
            sched, wlib, st = _solve_window(wi, plan=None, plan_mode="none", **common_kw)
            rec["fallback"] = "relaxed_targets_dummy_terminal"
            notes.append(f"t0={t0}: window reaching H infeasible with targets '{final_targets}'; "
                         "re-solved with relaxed targets and a penalised dummy terminal arc")
        if sched is None:
            raise RollingHorizonError(
                f"window t0={t0} W={Wp} has no incumbent: "
                + "; ".join(f"{md}: {s.get('status')}" for md, s in attempts))
        rec.update({key: st.get(key) for key in ("status", "obj", "gap", "bound", "runtime",
                                                  "wall", "n_arcs", "aggregate")})
        if verbose:
            print(f"[rolling] t0={t0} W={Wp} end={last} final={final} known={len(known)} "
                  f"status={rec['status']} obj={rec['obj']}")

        # --------------------------------------------- facilities (first decision)
        if fac_vals is None:
            fac_vals = {f.id: (int(sched.y[f.id]), int(sched.B[f.id]), int(sched.C[f.id]))
                        for f in inst.facilities}

        # --------------------------------------------------------- commit
        for kb in [b.id for b in inst.bikes]:
            hold = holds[kb]
            path = sorted((wlib.arc(a) for a in sched.x.get(kb, [])), key=lambda a: (a.l, a.u))
            for a in path:
                if a.l < hold and a.kind == "wait":
                    continue                        # held at the in-progress arc's end node
                if not final and a.l >= commit_until:
                    break
                if a.kind == "term":
                    if a.fac is None:
                        if final:
                            notes.append(f"bike {kb}: dummy terminal arc at the final epoch "
                                         "(no terminal certificate (9))")
                        continue
                    full = lib.find(kb, "term", (a.src[0], a.src[1] + t0, a.src[2]), fac=a.fac,
                                    dst=SINK)
                else:
                    full = lib.find(kb, a.kind, (a.src[0], a.src[1] + t0, a.src[2]),
                                    order=a.order, fac=a.fac,
                                    dst=(a.dst[0], a.dst[1] + t0, a.dst[2]))
                if full is None:
                    raise RollingHorizonError(
                        f"bike {kb}: window arc {a.kind} {a.src}->{a.dst} (t0={t0}) has no "
                        "counterpart in the full-day library (check arc_options)")
                x_c[kb].append(full.id)
                if full.kind == "deliver":
                    served.add(full.order)
                if full.kind == "swap":
                    for tau in range(full.l, full.u):
                        occ_c[(full.fac, tau)] += 1
                if full.kind != "term":
                    states[kb] = (full.dst[0], full.dst[1], full.dst[2])
        for (j, q, t), val in sched.c.items():
            if val and t < commit_until:
                c_c[(j, q, t + t0)] = int(val)
        for (e, q), val in sched.z.items():
            if val and wi.service(e).l < commit_until:
                z_c[(e, q)] = int(val)
        for e, val in sched.h.items():
            if val and wi.service(e).l < commit_until:
                h_c[e] = 1
        windows.append(rec)
        if final:
            break
        t0 += k

    y = {j: v[0] for j, v in fac_vals.items()}
    B = {j: v[1] for j, v in fac_vals.items()}
    C = {j: v[2] for j, v in fac_vals.items()}
    u = {o.id: (0 if o.id in served else 1) for o in inst.orders}
    h = {s.id: int(h_c.get(s.id, 0)) for s in inst.services}
    stitched = Schedule(x=x_c, u=u, c=c_c, h=h, z=z_c, y=y, B=B, C=C, n=None,
                        meta={"solver": "rolling_horizon", "W": W, "k": k,
                              "lookahead_min": (None if math.isinf(lam) else lookahead_min),
                              "final_targets": final_targets, "window_targets": window_targets,
                              "forecast": forecast is not None})
    cst = cost(inst, lib, stitched)
    rep = check(inst, lib, stitched)
    params_rec = {"W": W, "k": k, "lookahead_min": (math.inf if math.isinf(lam) else lookahead_min),
                  "lookahead_slots": lam, "final_targets": final_targets,
                  "final_rho": final_rho, "window_targets": window_targets,
                  "forecast": (None if forecast is None else f"{type(forecast).__name__}:"
                               f"{getattr(forecast, 'pool', '')}:{getattr(forecast, 'source', '')}"),
                  "n_scenarios": int(n_scenarios) if forecast is not None else 0,
                  "forecast_seed": int(forecast_seed), "aggregate": bool(aggregate),
                  "threads": int(threads), "time_limit": float(time_limit)}
    return RollingResult(inst=inst, lib=lib, schedule=stitched, cost=cst, check=rep,
                         hard_ok=hard_families_ok(rep), windows=windows, params=params_rec,
                         runtime=time.perf_counter() - t_wall, notes=notes)


# ---------------------------------------------------------------------------
# facility plan on forecast scenarios and offline vs online comparison
# ---------------------------------------------------------------------------
def forecast_facility_plan(inst: Instance, forecast: BootstrapForecast, *, n_scenarios: int = 3,
                           lookahead_min: Optional[float] = 0.0, seed: int = 0,
                           arc_options: Optional[Dict[str, Any]] = None, threads: int = 3,
                           time_limit: float = 120.0, params: Optional[Dict[str, Any]] = None
                           ) -> Dict[str, Any]:
    """Battery-side first-stage plan ``(y_j, B_j, C_j)`` on forecast scenarios (plan item
    M7; E2 (7)-(8), (16), (27), (33)): each scenario is the day instance with the orders
    known at ``t = 0`` (``r_i <= lambda``) plus sampled future orders, solved offline
    with the facilities left as in the data; the plan is the lower median per facility.
    Returns ``{'facility_values': {j: (y, B, C)}, 'scenarios': [stats]}``; pass
    ``facility_values`` to :func:`rolling_horizon`."""
    ilp = _ilp()
    lam = lookahead_slots(inst, lookahead_min)
    rng = np.random.default_rng(int(seed))
    known = [o for o in inst.orders if o.r <= lam]
    vals: Dict[Any, List[Tuple[int, int, int]]] = defaultdict(list)
    scen: List[Dict[str, Any]] = []
    for s in range(int(n_scenarios)):
        extra = forecast.sample(lam, 0, inst.H, rng, known=known, prefix=f"fp{s}")
        si = replace(inst, orders=list(known) + list(extra), meta=dict(inst.meta))
        si.reindex()
        slib = build_arcs(si, strict=False, **(arc_options or {}))
        sc, st = ilp.solve(si, slib, threads=int(threads), time_limit=float(time_limit),
                           params=params)
        scen.append({"status": st.get("status"), "obj": st.get("obj"), "n_orders": len(si.orders)})
        if sc is None:
            continue
        for f in inst.facilities:
            vals[f.id].append((int(sc.y[f.id]), int(sc.B[f.id]), int(sc.C[f.id])))
    if not vals:
        raise RollingHorizonError("no forecast scenario produced a facility plan")
    plan = {}
    for j, lst in vals.items():
        med = (len(lst) - 1) // 2
        plan[j] = tuple(sorted(v[i] for v in lst)[med] for i in range(3))
    return {"facility_values": plan, "scenarios": scen}


def offline_vs_online(inst: Instance, lookaheads_min: Sequence[Optional[float]] = (0.0, 10.0, 20.0),
                      W: Optional[int] = None, k: Optional[int] = None, *,
                      lib: Optional[ArcLibrary] = None, arc_options: Optional[Dict[str, Any]] = None,
                      forecast: Optional[BootstrapForecast] = None, n_scenarios: int = 1,
                      threads: int = 3, time_limit_offline: float = 600.0,
                      time_limit_window: float = 60.0, params: Optional[Dict[str, Any]] = None,
                      **rolling_kw: Any) -> Dict[str, Any]:
    """Offline E2 optimum vs rolling horizon at several look-aheads (plan item M7, SC-2 /
    E7): ``{'offline': {...}, 'rolling': [{lambda, total, voi, voi_pct, hard_ok, ...}]}``
    with ``voi = rolling - offline`` (value of information, an upper-bound difference
    when the offline solve stops at its time limit: its gap is reported).  With
    ``forecast`` each look-ahead is also run in forecast mode (``'forecast': True``)."""
    ilp = _ilp()
    arc_options = dict(arc_options or {})
    if lib is None:
        lib = build_arcs(inst, strict=False, **arc_options)
    t = time.perf_counter()
    # O1: the offline reference uses the aggregated flow when the windows do (equivalent model)
    off_kw = {"aggregate": True} if (rolling_kw.get("aggregate") and _supports_aggregate()) else {}
    off_sched, off_st = ilp.solve(inst, lib, threads=int(threads),
                                  time_limit=float(time_limit_offline), params=params, **off_kw)
    off = {"status": off_st.get("status"), "total": (off_st.get("cost") or {}).get("total"),
           "gap": off_st.get("gap"), "bound": off_st.get("bound"), "runtime": time.perf_counter() - t,
           "aggregate": bool(off_kw)}
    rows: List[Dict[str, Any]] = []
    variants: List[Tuple[Optional[float], bool]] = [(lm, False) for lm in lookaheads_min]
    if forecast is not None:
        variants += [(lm, True) for lm in lookaheads_min
                     if lm is not None and not math.isinf(float(lm))]
    for lm, use_fc in variants:
        res = rolling_horizon(inst, W, k, lm, lib=lib, arc_options=arc_options,
                              forecast=forecast if use_fc else None, n_scenarios=n_scenarios,
                              threads=threads, time_limit=time_limit_window, params=params,
                              **rolling_kw)
        row = res.summary()
        row.update(lookahead_min=(math.inf if lm is None else float(lm)), forecast=use_fc)
        if off["total"] is not None:
            row["voi"] = res.total - off["total"]
            row["voi_pct"] = (100.0 * row["voi"] / abs(off["total"])
                              if abs(off["total"]) > 1e-12 else None)
        rows.append(row)
    return {"offline": off, "rolling": rows, "offline_schedule": off_sched}
