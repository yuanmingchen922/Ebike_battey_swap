"""Shared helpers for the E2 experiments (``experiments/e*.py``).

Everything an experiment script needs that is not model logic lives here:

* **instance families** (:data:`FAMILIES`, :func:`make_instance`) -- the toy
  (E2 pp.10-15), the Battery_Swap p.7 station and the synthetic families of
  ``plan.size_estimates`` (``small`` = 4 bikes / 12 orders, ``medium`` = 8 / 24,
  ``large`` = 10 / 30, all ``H = 24``) and the round-2 USD families of
  ``DECISIONS.md`` R2.1 / R2.2 (``usd4h`` = 6 bikes / 36 orders, 4 h, 1.5 orders per
  bike-hour, ``usd_sunk`` costs -- the R2.2 nominal 10 bikes / 60 orders is
  ``usd4h_large``; ``usd8h`` = 8 h sensitivity, rolling horizon only; ``usd4h_toyunits``
  = the same instance priced in toy units; ``nyc4h`` = the semi-real R2.4 family;
  :data:`R2_FAMILIES`);
* **pruning defaults** (:data:`PRUNING_DEFAULTS`, :func:`pruning_for`) -- the
  arc-builder options recommended by the plan (reposition only to restaurants,
  facilities and depots, ``tau_max = 4``, ``start_slack = 6``);
* **runners** (:func:`run_baseline_case`, :func:`run_ilp_case`, :func:`run_pair`)
  that price and verify every schedule with ``evaluate.cost`` (26)-(32) and
  ``evaluate.check`` (5)-(22) and return flat, CSV-ready records;
* **fair-control helpers** -- :func:`relax_end_targets` (copy with ``rho = 0`` and
  ``R_end_j = 0``, (17)-(18) off, so that a 'same constraints for both' control
  exists; the written ``R_end_j`` is kept in ``meta['written_R_end']`` and
  :func:`run_baseline_case` uses it as the DEMAND_AWARE reserve on the copy so the
  policy is identical under both target settings), :func:`gap_definitions` (both gap
  conventions, named explicitly), :data:`BASELINE_VARIANTS` /
  :func:`baseline_variant_params` (the documented baseline variants, including
  ``baseline_reserve`` which respects (17)), :func:`unservable_orders` (orders no
  method can serve) and :func:`demand_key` / :func:`demand_md5` (hash of the demand
  side, to assert byte-identical demand across layouts / sitings / cost variants);
* **output helpers** -- CSV / Markdown tables (pandas) and matplotlib figures
  rendered with the ``Agg`` backend, Gurobi always with ``OutputFlag = 0``,
  ``Threads = 3`` (round-2 rule; round 1 used 4) and a time limit.

Only :func:`run_ilp_case` / :func:`run_pair` touch gurobipy (through
``ebike_swap_sim.ilp``); the rest of the module works without a licence.

Run scripts from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    PYTHONPATH=. python3 experiments/e1_toy.py
"""
from __future__ import annotations

import copy
import csv
import json
import math
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)
import pandas as pd  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:  # allow ``python3 experiments/e1_toy.py`` without PYTHONPATH
    sys.path.insert(0, _ROOT)

from ebike_swap_sim import (  # noqa: E402
    ArcLibrary,
    Instance,
    Schedule,
    battery_swap_p7_instance,
    build_arcs,
    check,
    cost,
    facility_vars,
    in_transit,
    metrics,
    reconstruct_inventory,
    toy_instance,
)
from ebike_swap_sim import generator as gen  # noqa: E402
from ebike_swap_sim import baseline as bl  # noqa: E402
from ebike_swap_sim import sites_nyc as _sites_nyc  # noqa: E402

OUTPUT_ROOT = os.path.join(_ROOT, "outputs")
#: Gurobi threads (round-2 rule: at most 3; round-1 outputs were produced with 4).
THREADS = 3
DEFAULT_TIME_LIMIT = 300.0

#: Constraint families the baseline may *report* without being wrong
#: (DECISIONS.md: (9), (17), (18) are reported, not enforced by the policy).
BASELINE_REPORT_ONLY = ("(9)", "(17)", "(18)")

#: Synthetic families of ``plan.size_estimates`` (kwargs of
#: :func:`ebike_swap_sim.generator.make_synthetic_instance`) plus the two
#: reference instances.
FAMILIES: Dict[str, Dict[str, Any]] = {
    "toy": {},
    "p7": {},
    "small": {"n_bikes": 4, "n_orders": 12, "H": 24, "L": 8},
    "medium": {"n_bikes": 8, "n_orders": 24, "H": 24, "L": 8},
    "large": {"n_bikes": 10, "n_orders": 30, "H": 24, "L": 12},
    # round 2 (DECISIONS R2.1 / R2.2): USD costs, 4 h dinner window 17:00-21:00, 1.5 orders
    # per bike-hour (10 bikes -> 60 orders), B = 3 / C = 2, Kaggle order attributes, the
    # declared time-of-day profile; sizes may be reduced by the integrate step.
    # sizes fixed by experiments/r2_size_probe.py (outputs/r2_probe/usd4h.jsonl; DECISIONS
    # "R2 implementation notes"): 6 bikes / 36 orders / H 48 solve to optimality in 71-95 s at
    # Threads 3 on seeds 0 and 1 with default and reachable pruning; the R2.2 nominal
    # 10 bikes / 60 orders is kept as ``usd4h_large``.
    "usd4h": {"n_bikes": 6, "window_h": 4.0, "window_start_hour": 17.0,
              "orders_per_bike_hour": 1.5, "L": 12, "n_restaurants": 8,
              "cost_variant": "usd_sunk"},
    "usd4h_large": {"n_bikes": 10, "window_h": 4.0, "window_start_hour": 17.0,
                    "orders_per_bike_hour": 1.5, "L": 12, "n_restaurants": 8,
                    "cost_variant": "usd_sunk"},
    # 8 h sensitivity window 14:00-22:00 (H = 96), same knobs; ROLLING-HORIZON ONLY until a
    # single-ILP probe (python3 experiments/r2_size_probe.py --family usd8h --bikes 6) shows
    # <= 1 % gap within 300 s (not yet verified, see DECISIONS R2 implementation notes)
    "usd8h": {"n_bikes": 6, "window_h": 8.0, "window_start_hour": 14.0,
              "orders_per_bike_hour": 1.5, "L": 12, "n_restaurants": 8,
              "cost_variant": "usd_sunk", "rolling_horizon_only": True},
    # the usd4h instance (same geography, orders, bikes, facilities) priced in toy units
    "usd4h_toyunits": {"n_bikes": 6, "window_h": 4.0, "window_start_hour": 17.0,
                       "orders_per_bike_hour": 1.5, "L": 12, "n_restaurants": 8,
                       "cost_variant": "toy"},
    # semi-real NYC family (DECISIONS R2.4): DOHMH restaurants, ACS zone weights, real
    # candidate-site coordinates on the synthetic grid of the default Midtown study box;
    # built by ``ebike_swap_sim.data_nyc.make_nyc_instance`` (``builder`` key)
    "nyc4h": {"builder": "nyc", "n_bikes": 6, "window_h": 4.0, "orders_per_bike_hour": 1.5,
              "L": 12, "n_sites": 3, "cost_variant": "usd_sunk"},
    # energy-stressed semi-real family for the bi-level siting study
    # (notes/bilevel_siting_design.md section 5; E2_formulation_review proposal SC-1): 8 bikes /
    # 48 orders / H 48, q0 ~ U{2..4} of 12 (100-200 Wh), one spare and one 1.4 kW charger per
    # site (Cbar 4), a flat 4 kW grid group -- the regime in which location, role and size of
    # the facilities matter (on nyc4h the battery side never binds: siting delta <= 0.41 USD).
    # (the keyword arguments are ``ebike_swap_sim.sites_nyc.STRESS_PARAMS``: 8 bikes, 4 h, 1.5
    # orders per bike-hour, L 12, usd_sunk, init_frac (2/12, 4/12), B 1 / C 1 / P 1.4 kW / Cbar 4,
    # flat 4 kW grid group)
    "nyc4h_stress": {"builder": "nyc", **_sites_nyc.STRESS_PARAMS},
    # 'stressed but sane' family of the E9 relaunch (DECISIONS "E9 relaunch decisions"): 6 bikes /
    # 36 orders / H 48, q0 ~ U{3..6} of 12, B 1 / C 1 / P 2.8 kW / Cbar 4, flat 4 kW grid group
    # (``ebike_swap_sim.sites_nyc.STRESS2_PARAMS``)
    "nyc4h_stress2": {"builder": "nyc", **_sites_nyc.STRESS2_PARAMS},
}

#: Families generated in round-2 mode of :func:`ebike_swap_sim.generator.make_synthetic_instance`
#: (``window_h`` / ``orders_per_bike_hour`` knobs instead of ``n_orders`` / ``H``) or by
#: :func:`ebike_swap_sim.data_nyc.make_nyc_instance`.
R2_FAMILIES = ("usd4h", "usd4h_large", "usd8h", "usd4h_toyunits", "nyc4h", "nyc4h_stress", "nyc4h_stress2")

#: Arc-builder pruning recommended by the plan (``generator.default_pruning``).
PRUNING_DEFAULTS: Dict[str, Any] = {"tau_max": 4, "start_slack": 6, "reachable": False}
#: Pruning of the semi-real NYC family (``meta['semi_real']``): the DOHMH restaurant
#: nodes used by the orders (one per order) would make ``reposition_targets`` ~60 nodes
#: and the library ~36 M arcs at 10 bikes, so moves are allowed only into facility /
#: depot nodes (``targets = 'facilities'``; a bike still reaches any restaurant through
#: the delivery arc itself, which starts from any node within ``tau_max``) and
#: unreachable states are dropped.
#:
#: One-sided effect (fairness review F2): ``targets = 'facilities'`` is a restriction of
#: the written E2 model that binds **only the ILP** -- the policy repositions exclusively
#: to swap sites (``_go_swap``) and starts deliveries from where it stands, so it loses
#: nothing, whereas the ILP loses pre-positioning moves towards restaurants / customers
#: (on nyc4h seed 0 ``tau_max`` never binds: all 1,296 customer -> restaurant pairs are
#: within 4 slots, so the whole 0.75 M vs ~36 M arc reduction comes from the forbidden
#: moves).  The nyc4h ILP optimum under this pruning is therefore an UPPER bound on the
#: written optimum and the reported gap a LOWER bound on the coordination value; no
#: lossless probe exists yet for these targets (the usd4h reachable pruning was shown
#: lossless by ``r2_size_probe``).  Report this wherever nyc4h ILP numbers appear.
PRUNING_NYC: Dict[str, Any] = {"tau_max": 4, "start_slack": 6, "reachable": True, "targets": "facilities"}

#: Documented baseline variants (``BaselineParams`` field overrides; ``W`` denotes
#: the end window ``max_j sigma_j + END_WINDOW_SLACK`` of :func:`end_window`).
#: Since round 2 the ``BaselineParams`` defaults ARE the R2.3 rules (stock-aware site
#: choice, DEMAND_AWARE charging, JIT dispatch, dead-zone rule), so the three policy
#: generations are taken from :data:`ebike_swap_sim.baseline.BASELINE_VARIANTS`:
#:
#: * ``baseline``          -- the round-2 policy (DECISIONS R2.3; ``bl`` variant ``'default'``);
#: * ``baseline_round1``   -- the round-1 policy after the reviewer fixes (nearest site
#:                            regardless of stock, ASAP HIGH_FIRST charging; ``'round1'``);
#: * ``baseline_legacy``   -- pre-review round-1 behaviour (``round1`` + no JIT dispatch,
#:                            no dead-zone rule; ``'legacy'``);
#: * ``baseline_reorder``  -- REORDER_POINT transfer rule;
#: * ``baseline_zone``     -- zone-first dispatch;
#: * ``baseline_reserve``  -- RESERVE variant (reviewer F3): keeps the last ``R_end_j`` full
#:                            spares in the last ``W`` slots and makes no swap trip that
#:                            would end after ``H - W`` -> a feasible start under (17);
#: * ``baseline_informed`` -- reviewer F6 (a)+(b): stock-aware site choice (now the default)
#:                            plus end-of-horizon awareness (no (17) reserve).
BASELINE_VARIANTS: Dict[str, Dict[str, Any]] = {
    "baseline": dict(bl.BASELINE_VARIANTS["default"]),
    "baseline_round1": dict(bl.BASELINE_VARIANTS["round1"]),
    "baseline_legacy": dict(bl.BASELINE_VARIANTS["legacy"]),
    "baseline_reorder": {"transfer_rule": "REORDER_POINT"},
    "baseline_zone": {"dispatch_scope": "zone"},
    "baseline_reserve": {"end_reserve_window": "W", "late_threshold_window": "W"},
    "baseline_informed": {"stock_aware_site": True, "late_threshold_window": "W"},
}
#: Baseline variants tried, in order, by :func:`feasible_mip_start` when the default
#: baseline schedule violates one of the report-only families (9)/(17)/(18) and would
#: therefore be rejected as a Gurobi MIP start.
MIP_START_FALLBACKS = ("baseline_round1", "baseline_reserve")
#: Slots added to ``max_j sigma_j`` for the end window of the RESERVE / informed variants.
END_WINDOW_SLACK = 3


# ---------------------------------------------------------------------------
# instances and libraries
# ---------------------------------------------------------------------------
def make_instance(family: str, seed: int = 0, **overrides: Any) -> Instance:
    """Instance of one :data:`FAMILIES` entry.

    ``'toy'`` -> :func:`ebike_swap_sim.toy_instance` (J* = 12.5), ``'p7'`` ->
    :func:`ebike_swap_sim.battery_swap_p7_instance`; the synthetic families call
    :func:`ebike_swap_sim.generator.make_synthetic_instance` with the family's
    sizes, ``seed`` and any ``overrides`` (e.g. ``facilities_spec={'mode':
    'separated'}``).  ``meta['family']`` records the family name.
    """
    if family not in FAMILIES:
        raise KeyError(f"unknown family {family!r}; known: {sorted(FAMILIES)}")
    if family == "toy":
        inst = toy_instance()
    elif family == "p7":
        inst = battery_swap_p7_instance()
    else:
        kw = {**FAMILIES[family], **overrides}
        builder = kw.pop("builder", "synthetic")
        rolling_only = kw.pop("rolling_horizon_only", False)
        name = kw.pop("name", f"{family}-seed{seed}")
        if builder == "nyc":
            from ebike_swap_sim import data_nyc
            inst = data_nyc.make_nyc_instance(seed=seed, name=name, **kw)
        else:
            inst = gen.make_synthetic_instance(seed=seed, name=name, **kw)
    inst.meta["family"] = family
    inst.meta.setdefault("seed", seed)
    if family not in ("toy", "p7") and rolling_only:
        inst.meta["rolling_horizon_only"] = True
    return inst


def pruning_for(inst: Instance, **overrides: Any) -> Dict[str, Any]:
    """Arc-builder options for ``inst``: :data:`PRUNING_DEFAULTS` (or :data:`PRUNING_NYC`
    for semi-real instances, ``meta['semi_real']``) updated by ``overrides``
    (``tau_max``, ``start_slack``, ``reachable``, ``targets`` in ``{'default',
    'facilities'}``) passed to :func:`ebike_swap_sim.generator.default_pruning`;
    ``targets='facilities'`` restricts ``reposition_targets`` to facility and depot
    nodes.  The toy and p.7 instances are built unpruned (``{}``) so that the
    documented arc counts are reproduced."""
    if inst.meta.get("family") in ("toy", "p7") or not inst.meta.get("restaurants"):
        return {}
    base = PRUNING_NYC if inst.meta.get("semi_real") else PRUNING_DEFAULTS
    kw = {**base, **overrides}
    pr = gen.default_pruning(inst, tau_max=kw["tau_max"], start_slack=kw["start_slack"],
                             reachable=kw["reachable"])
    if kw.get("targets", "default") == "facilities":
        targets = {f.node for f in inst.facilities}
        targets.update(gen._node(d) for d in inst.meta.get("depots", []))
        pr["reposition_targets"] = targets
    return pr


def end_window(inst: Instance, slack: int = END_WINDOW_SLACK) -> int:
    """End window ``W = max_{j in S} sigma_j + slack`` (slots) of the RESERVE /
    informed baseline variants (reviewer F3: ``sigma_j + 2..4``)."""
    sigmas = [inst.facility(j).sigma for j in inst.S] or [1]
    return int(max(sigmas) + slack)


def baseline_variant_params(name: str, inst: Instance, **overrides: Any) -> Dict[str, Any]:
    """``BaselineParams`` field dict of the variant ``name`` of :data:`BASELINE_VARIANTS`
    for ``inst`` (the symbolic window ``'W'`` is resolved with :func:`end_window`),
    updated by ``overrides``."""
    if name not in BASELINE_VARIANTS:
        raise KeyError(f"unknown baseline variant {name!r}; known: {sorted(BASELINE_VARIANTS)}")
    W = end_window(inst)
    params = {k: (W if v == "W" else v) for k, v in BASELINE_VARIANTS[name].items()}
    params.update(overrides)
    return params


def relax_end_targets(inst: Instance) -> Instance:
    """Deep copy of ``inst`` with ``rho = 0`` **and** ``R_end_j = 0`` for every facility,
    i.e. both end-of-horizon targets (17) and (18) switched off (E2 p.6: 'either
    target can be disabled by setting it to zero').

    This is the fair 'same constraints for both' control of reviewer F3: the
    baseline policy *enforces* neither target (it reports (17)/(18)), so an ILP
    compared with it should drop both, not only (18).  Everything else (bikes,
    orders, routes, services, options, meta) is byte-identical;
    ``meta['relax_end_targets'] = True`` marks the copy and
    ``meta['written_R_end'] = {j: R_end_j}`` / ``meta['written_rho']`` keep the
    written targets.  The arc library does not depend on ``rho`` / ``R_end`` but
    ``run_baseline`` insists on ``lib.inst == inst``, so rebuild it for the copy
    (``build_arcs(copy, **lib.options)``).

    Since R2.3 the policy is **not** target-agnostic: the DEMAND_AWARE charging
    rule uses ``reserve_j = R_end_j y_j`` (fairness review F1), so running the
    policy on the relaxed copy with the default parameters would change its
    charging schedule (usd4h seed 0: 732.849 vs 733.098 USD).  :func:`run_baseline_case`
    therefore passes ``charge_reserve = meta['written_R_end']`` when it runs on a
    relaxed copy and no explicit reserve was given, which reproduces the written
    schedule exactly; the row records ``policy_reserve_source = 'written_R_end'``.
    (The ``baseline_reserve`` variant's end-window rule reads ``f.R_end`` directly and
    is a no-op on the copy; it is only a MIP-start fallback there.)"""
    out = copy.deepcopy(inst)
    out.meta["written_R_end"] = {f.id: int(f.R_end) for f in out.facilities}
    out.meta["written_rho"] = float(out.rho)
    out.rho = 0.0
    for f in out.facilities:
        f.R_end = 0
    out.reindex()
    out.meta["relax_end_targets"] = True
    return out


def unservable_orders(inst: Instance, lib: ArcLibrary) -> List[Any]:
    """Orders that **no** method can serve on this library (fairness review F5): no
    delivery arc exists, typically because ``r_i + prep + handling + ride > H`` for
    an order released near ``H - tail`` with a long prep time (usd4h seed 0: order 35,
    ``r 37, a 44``).  Both the ILP and the policy pay ``P_i`` for them, so they
    inflate the raw drop rate of both identically and dilute the relative gap;
    report ``served_share_servable = n_served / (|I| - n_unservable)`` next to the
    raw share."""
    return [o.id for o in inst.orders if not lib.delivery_arcs(o.id)]


def demand_key(inst: Instance, include_bike_nodes: bool = True, include_facilities: bool = False) -> Any:
    """Hashable description of the demand side that layouts / sitings / cost variants
    must NOT change (units review F7): orders with times and nodes, bikes (``q0``, and
    ``v0`` unless ``include_bike_nodes=False`` -- the e8 sitings move the bikes' start
    nodes with the sites), ``H``, ``L``; facilities only on request (``e2u`` adds them
    for the cost-variant check).  Compare with ``==`` or hash it with :func:`demand_md5`."""
    key: List[Any] = [
        [(o.id, o.o, o.d, o.r, o.a, o.b, o.hp, o.hd) for o in inst.orders],
        [(k.id, k.v0 if include_bike_nodes else None, k.q0) for k in inst.bikes],
        inst.H, inst.L,
    ]
    if include_facilities:
        key.append([(f.id, f.node, f.swap, f.charge, f.B, f.C, f.K, f.M, f.sigma, f.R_end) for f in inst.facilities])
    return key


def demand_md5(inst: Instance, include_bike_nodes: bool = True, include_facilities: bool = False) -> str:
    """MD5 of :func:`demand_key` (JSON with ``default=str``), for ``results.csv`` /
    ``RESULTS.md`` so that 'byte-identical demand per seed' is checkable after the fact."""
    import hashlib
    txt = json.dumps(demand_key(inst, include_bike_nodes, include_facilities), default=str, sort_keys=False)
    return hashlib.md5(txt.encode("utf-8")).hexdigest()


def baseline_pruning_flags(flags: Dict[str, Any]) -> Dict[str, int]:
    """Counts of the policy events where the shared pruning / the arc rules bound the
    *baseline* (fairness review F4; round-1 parity rule 'report pruned fallbacks'):
    ``pruned_fallbacks`` = sum of ``flags['pruned_arc_fallbacks']['count']`` over
    move / deliver / swap, ``stranded`` = ``len(flags['stranded_bikes'])``,
    ``late_suppressed`` = ``flags['late_trips_suppressed']``."""
    pf = (flags.get("pruned_arc_fallbacks") or {}).get("count") or {}
    return {
        "pruned_fallbacks": int(sum(int(v) for v in pf.values())),
        "stranded": int(len(flags.get("stranded_bikes") or [])),
        "late_suppressed": int(flags.get("late_trips_suppressed", 0) or 0),
    }


def gap_definitions(baseline_total: Optional[float], ilp_total: Optional[float]
                    ) -> Dict[str, Optional[float]]:
    """Both gap conventions, named explicitly (reviewer F4):

    * ``gap_vs_baseline_pct = 100 (baseline - ILP) / baseline`` -- the plan's
      definition (relative improvement of the coordinator over the policy; used
      by ``e2_coord``);
    * ``gap_vs_ilp_pct = 100 (baseline - ILP) / ILP`` -- the baseline's excess over
      the optimum (the historical ``baseline_gap_pct`` of :func:`run_pair`).

    Either is ``None`` when a total is missing or its denominator is zero."""
    if baseline_total is None or ilp_total is None:
        return {"gap_vs_baseline_pct": None, "gap_vs_ilp_pct": None}
    diff = float(baseline_total) - float(ilp_total)
    return {
        "gap_vs_baseline_pct": (None if abs(baseline_total) < 1e-12 else 100.0 * diff / abs(baseline_total)),
        "gap_vs_ilp_pct": (None if abs(ilp_total) < 1e-12 else 100.0 * diff / abs(ilp_total)),
    }


def build_library(inst: Instance, pruning: Optional[Dict[str, Any]] = None,
                  strict: bool = True) -> Tuple[ArcLibrary, float]:
    """``build_arcs(inst, **pruning)`` (E2 (1)-(4), (9)) timed with
    ``time.perf_counter``; returns ``(library, seconds)``."""
    t0 = time.perf_counter()
    lib = build_arcs(inst, strict=strict, **(pruning or {}))
    return lib, time.perf_counter() - t0


# ---------------------------------------------------------------------------
# evaluation helpers
# ---------------------------------------------------------------------------
def family_counts(report: Dict[str, Any]) -> Dict[str, int]:
    """``{family: count}`` of the violations in an ``evaluate.check`` report."""
    return {fam: rec["count"] for fam, rec in report["families"].items() if rec["count"]}


def check_identity_24(inst: Instance, lib: ArcLibrary, sched: Schedule) -> bool:
    """Battery conservation (24): ``sum_j N_jt + m_t = sum_j B_j`` for ``t = 0..H``
    on the (13) recursion of the schedule (``m_t`` strict ``l_e < t < u_e``)."""
    _, B, _ = _facility_vars(inst, sched)
    n = sched.n if sched.n is not None else reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z, B)
    m = in_transit(inst, sched.z)
    total_B = sum(B.values())
    for t in range(inst.H + 1):
        stock = sum(n.get((j, q, t), 0) for j in inst.N for q in range(inst.L + 1))
        if stock + m[t] != total_B:
            return False
    return True


def _facility_vars(inst: Instance, sched: Schedule):
    """Effective ``(y, B, C)`` of a schedule (``evaluate.facility_vars``)."""
    return facility_vars(inst, sched)


def flatten_cost(c: Dict[str, Any], prefix: str = "") -> Dict[str, float]:
    """Flatten an ``evaluate.cost`` dict ((26)-(32)) into scalar columns
    ``<prefix>total, <prefix>C_travel, ..., <prefix>unserved/response/lateness``."""
    out: Dict[str, float] = {}
    for key, val in c.items():
        if key == "C_orders_parts":
            for part, pv in val.items():
                out[f"{prefix}{part}"] = pv
        elif isinstance(val, (int, float)):
            out[f"{prefix}{key}"] = val
    return out


def inventory_table(inst: Instance, lib: ArcLibrary, sched: Schedule) -> pd.DataFrame:
    """Stock table ``n_jqt`` (13)/(16) of a schedule, one row per boundary ``t``
    and one column ``n[j][q]`` per facility and level, plus ``m_t`` (24).  Uses
    ``sched.n`` when given, else the recursion."""
    _, B, _ = _facility_vars(inst, sched)
    n = sched.n if sched.n is not None else reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z, B)
    m = in_transit(inst, sched.z)
    rows = []
    for t in range(inst.H + 1):
        row: Dict[str, Any] = {"t": t}
        for j in inst.N:
            for q in range(inst.L + 1):
                row[f"n[{j}][{q}]"] = int(n.get((j, q, t), 0))
        row["m_t"] = m[t]
        rows.append(row)
    return pd.DataFrame(rows)


def path_description(inst: Instance, lib: ArcLibrary, sched: Schedule, k: Any) -> List[str]:
    """Human-readable arc sequence of bike ``k`` (kind, state transitions, order /
    facility labels) for result reports."""
    out = []
    for a in sched.path(k, lib):
        label = ""
        if a.order is not None:
            label = f" order {a.order}"
        if a.fac is not None:
            label = f" fac {a.fac}"
        dst = "sink" if a.kind == "term" else f"{a.dst}"
        out.append(f"{a.kind}{label}: {a.src} -> {dst}")
    return out


# ---------------------------------------------------------------------------
# runners
# ---------------------------------------------------------------------------
def run_baseline_case(inst: Instance, lib: ArcLibrary, params: Any = None,
                      label: str = "baseline") -> Dict[str, Any]:
    """Run :func:`ebike_swap_sim.baseline.run_baseline` and price / verify the
    schedule with the shared evaluator.

    Returns ``{'label', 'schedule', 'flags', 'runtime', 'cost', 'check', 'families',
    'ok', 'ok_modulo_report_only', 'identity_24_ok', 'metrics'}``.  ``ok_modulo_
    report_only`` is True when the only reported families are
    :data:`BASELINE_REPORT_ONLY` ((9), (17), (18)), which the policy reports but
    does not enforce (DECISIONS.md).
    """
    p = bl.BaselineParams.coerce(params)
    reserve_source = "params" if p.charge_reserve is not None else "R_end"
    written = inst.meta.get("written_R_end") if inst.meta.get("relax_end_targets") else None
    if written and p.charge_reserve is None:
        # fairness review F1: DEMAND_AWARE reserves R_end_j y_j (R2.3).  On a relax_end_targets
        # copy (R_end 0) keep the WRITTEN reserve so the policy under test is the same policy
        # under both end-target settings (its schedule is then identical to the written run).
        import dataclasses
        p = dataclasses.replace(p, charge_reserve={j: int(v) for j, v in written.items()})
        reserve_source = "written_R_end"
    t0 = time.perf_counter()
    sched, flags = bl.run_baseline(inst, lib, p)
    rt = time.perf_counter() - t0
    rep = check(inst, lib, sched)
    fams = family_counts(rep)
    return {
        "label": label,
        "schedule": sched,
        "flags": flags,
        "params": p.__dict__,
        "policy_reserve_source": reserve_source,
        "pruning_flags": baseline_pruning_flags(flags),
        "runtime": rt,
        "cost": cost(inst, lib, sched),
        "check": rep,
        "families": fams,
        "ok": rep["ok"],
        "ok_modulo_report_only": all(f in BASELINE_REPORT_ONLY for f in fams),
        "identity_24_ok": rep["identity_24_ok"] and check_identity_24(inst, lib, sched),
        "metrics": metrics(inst, lib, sched),
    }


def feasible_mip_start(inst: Instance, lib: ArcLibrary, base: Dict[str, Any],
                       fallbacks: Sequence[str] = MIP_START_FALLBACKS
                       ) -> Tuple[Optional[Schedule], str]:
    """Pick the baseline schedule to inject as the Gurobi MIP start.

    The round-2 default baseline (DECISIONS R2.3, DEMAND_AWARE charging) covers only the
    per-site reserve (17) and may end with ``sum_j n_jLH < rho sum_j B_j`` (18), which
    the policy *reports* but the ILP enforces -- such a start is rejected by the
    fix-and-solve certificate of ``ilp.set_mip_start``.  If ``base`` (a
    :func:`run_baseline_case` record) reports any violated family, the variants in
    ``fallbacks`` are run in order and the first one whose schedule passes ``check``
    cleanly is returned as ``(schedule, variant_name)``; otherwise the default
    schedule is returned with ``'default'`` (still a valid heuristic start: Gurobi
    simply ignores an infeasible one).  E2 semantics are untouched -- this only
    chooses *which* policy schedule is offered as a start."""
    errors: Dict[str, str] = base.setdefault("mip_start_fallback_errors", {})
    if not base["families"]:
        return base["schedule"], "default"
    for name in fallbacks:
        try:
            rec = run_baseline_case(inst, lib, baseline_variant_params(name, inst), label=name)
        except (ValueError, KeyError, TypeError) as exc:
            # a variant may be inapplicable (e.g. no swap site for the end window W); the
            # error is recorded on the base record (fairness review F7) instead of being
            # swallowed; genuine policy bugs (RuntimeError etc.) propagate.
            errors[name] = f"{type(exc).__name__}: {exc}"
            continue
        if not rec["families"]:
            return rec["schedule"], name
    return base["schedule"], "default"


def run_ilp_case(inst: Instance, lib: ArcLibrary, mip_start: Optional[Schedule] = None,
                 time_limit: float = DEFAULT_TIME_LIMIT, threads: int = THREADS,
                 label: str = "ilp", verify_start: bool = True,
                 **build_kwargs: Any) -> Dict[str, Any]:
    """Build and solve the E2 ILP ((5)-(22), (26)-(33)) with
    :func:`ebike_swap_sim.ilp.solve` (``OutputFlag = 0``, ``Threads``,
    ``TimeLimit``) and return ``{'label', 'schedule', 'stats', 'runtime',
    'build_time', 'cost', 'check', 'families', 'ok', 'identity_24_ok', 'metrics',
    'mip_start_accepted', ...}``.  ``build_kwargs`` are the model switches
    (``no_transfers``, ``colocated``, ``lexicographic``, ``fixed_facilities``,
    ``budget``, ``zeta``, ``params``).  ``schedule`` is ``None`` without an
    incumbent (the record then carries ``stats`` only)."""
    from ebike_swap_sim import ilp

    sched, st = ilp.solve(inst, lib, mip_start=mip_start, verify_start=verify_start,
                          threads=threads, time_limit=time_limit, **build_kwargs)
    rec: Dict[str, Any] = {
        "label": label, "schedule": sched, "stats": st,
        "status": st["status"], "obj": st.get("obj"), "bound": st.get("bound"),
        "gap": st.get("gap"), "runtime": st["runtime"], "build_time": st["build_time"],
        "n_binaries": st.get("n_binaries"), "n_vars": st.get("n_vars"), "n_rows": st.get("n_rows"),
        "mip_start_accepted": (st.get("mip_start") or {}).get("accepted"),
        "mip_start_info": st.get("mip_start"),
        "lex_min_unserved": st.get("lex_min_unserved"),
    }
    if sched is None:
        rec.update(cost=None, check=None, families={}, ok=False, identity_24_ok=None, metrics=None)
        return rec
    # the ILP solve already asserts check-ok and cost == objective; evaluate again
    # with the model's effective instance/library (colocated rebuilds the library)
    eff_inst, eff_lib = inst, lib
    if st["switches"].get("colocated"):
        eff_inst = ilp.colocated_instance(inst)
        eff_lib = build_arcs(eff_inst, **lib.options)
    rep = check(eff_inst, eff_lib, sched)
    rec.update(cost=cost(eff_inst, eff_lib, sched), check=rep, families=family_counts(rep),
               ok=rep["ok"], identity_24_ok=rep["identity_24_ok"] and check_identity_24(eff_inst, eff_lib, sched),
               metrics=metrics(eff_inst, eff_lib, sched))
    return rec


def run_pair(inst: Instance, pruning: Optional[Dict[str, Any]] = None,
             baseline_params: Any = None, time_limit: float = DEFAULT_TIME_LIMIT,
             threads: int = THREADS, lib: Optional[ArcLibrary] = None,
             ilp_kwargs: Optional[Dict[str, Any]] = None,
             keep_schedules: bool = False, start_fallback: bool = True) -> Dict[str, Any]:
    """Baseline + ILP (baseline injected as MIP start) on one instance.

    Steps: build the arc library with ``pruning`` (default :func:`pruning_for`),
    run the baseline policy, solve the ILP with the baseline as MIP start, and
    return one flat record with instance sizes, ``build_time``, ``n_arcs``,
    ``baseline_*`` (cost components, runtime, reported families, unserved,
    identity), ``ilp_*`` (status, obj, bound, gap, runtime, build time, binaries,
    rows, components, identity), ``mip_start_accepted``, ``ilp_le_baseline``,
    ``baseline_gap_pct`` = 100 (baseline - ILP) / ILP (historical name) and both
    explicit conventions of :func:`gap_definitions` (``gap_vs_baseline_pct``,
    ``gap_vs_ilp_pct``), plus the baseline flags ``baseline_jit_dispatches``,
    ``baseline_reach_refusals``, ``baseline_pruned_fallbacks`` / ``baseline_stranded`` /
    ``baseline_late_suppressed`` (where the shared pruning bound the policy, fairness
    review F4), ``baseline_policy_reserve_source``, ``n_unservable`` and
    ``*_served_share_servable`` (orders no method can serve, fairness review F5),
    ``mip_start_fallback_errors`` and ``demand_md5``.  With ``start_fallback`` (default) the MIP start is
    chosen by :func:`feasible_mip_start` (``mip_start_variant`` records which policy
    schedule was injected: ``'default'`` or one of :data:`MIP_START_FALLBACKS`); the
    baseline columns always describe the ``baseline_params`` policy.  With ``keep_schedules`` the
    record also carries the two :class:`Schedule` objects and the library under
    ``'_baseline'``, ``'_ilp'``, ``'_lib'`` (dropped by :func:`records_to_frame`).
    """
    if pruning is None:
        pruning = pruning_for(inst)
    if lib is None:
        lib, build_time = build_library(inst, pruning)
    else:
        build_time = float("nan")
    base = run_baseline_case(inst, lib, baseline_params)
    if start_fallback:
        start_sched, start_label = feasible_mip_start(inst, lib, base)
    else:
        start_sched, start_label = base["schedule"], "default"
    ilp_rec = run_ilp_case(inst, lib, mip_start=start_sched, time_limit=time_limit,
                           threads=threads, **(ilp_kwargs or {}))
    unserv = unservable_orders(inst, lib)
    n_servable = max(0, len(inst.orders) - len(unserv))
    pf = base.get("pruning_flags") or baseline_pruning_flags(base["flags"])
    rec: Dict[str, Any] = {
        "name": inst.meta.get("name", ""), "family": inst.meta.get("family", ""),
        "seed": inst.meta.get("seed", ""),
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
        "n_facilities": len(inst.facilities), "n_services": len(inst.services),
        "n_arcs": len(lib), "build_time_s": build_time,
        "baseline_runtime_s": base["runtime"],
        "baseline_ok": base["ok"],
        "baseline_ok_modulo_report_only": base["ok_modulo_report_only"],
        "baseline_families": json.dumps(base["families"]),
        "baseline_unserved": base["flags"]["n_unserved"],
        "baseline_swaps": base["flags"]["n_swaps"],
        "baseline_identity_24_ok": base["identity_24_ok"],
        "baseline_inventory_consistent": base["flags"]["inventory_consistent"],
        "baseline_jit_dispatches": base["flags"].get("jit_dispatches", 0),
        "baseline_reach_refusals": (base["flags"].get("reach_refusals") or {}).get("count", 0),
        "baseline_pruned_fallbacks": pf["pruned_fallbacks"],
        "baseline_stranded": pf["stranded"],
        "baseline_late_suppressed": pf["late_suppressed"],
        "baseline_policy_reserve_source": base.get("policy_reserve_source", "R_end"),
        "n_unservable": len(unserv),
        "unservable_orders": json.dumps(unserv, default=str),
        "baseline_served_share_servable": (None if n_servable == 0 else
                                           base["metrics"]["n_served"] / n_servable),
        "mip_start_fallback_errors": json.dumps(base.get("mip_start_fallback_errors") or {}),
        "demand_md5": demand_md5(inst),
        **flatten_cost(base["cost"], "baseline_"),
        "ilp_status": ilp_rec["status"], "ilp_obj": ilp_rec["obj"], "ilp_bound": ilp_rec["bound"],
        "ilp_gap": ilp_rec["gap"], "ilp_runtime_s": ilp_rec["runtime"],
        "ilp_build_time_s": ilp_rec["build_time"], "ilp_binaries": ilp_rec["n_binaries"],
        "ilp_vars": ilp_rec["n_vars"], "ilp_rows": ilp_rec["n_rows"],
        "ilp_ok": ilp_rec["ok"], "ilp_identity_24_ok": ilp_rec["identity_24_ok"],
        "mip_start_accepted": ilp_rec["mip_start_accepted"],
        "mip_start_variant": start_label,
        "mip_start_verified_status": (ilp_rec["mip_start_info"] or {}).get("verified_status"),
    }
    if ilp_rec["cost"] is not None:
        rec.update(flatten_cost(ilp_rec["cost"], "ilp_"))
        rec["ilp_unserved_n"] = ilp_rec["metrics"]["n_unserved"]
        rec["ilp_served_share_servable"] = (None if n_servable == 0 else
                                            ilp_rec["metrics"]["n_served"] / n_servable)
        rec["ilp_le_baseline"] = ilp_rec["cost"]["total"] <= base["cost"]["total"] + 1e-6
        rec["baseline_gap_pct"] = 100.0 * (base["cost"]["total"] - ilp_rec["cost"]["total"]) / max(1e-9, abs(ilp_rec["cost"]["total"]))
        rec.update(gap_definitions(base["cost"]["total"], ilp_rec["cost"]["total"]))
    else:
        rec["ilp_le_baseline"] = None
        rec["baseline_gap_pct"] = None
        rec.update(gap_definitions(None, None))
    if keep_schedules:
        rec["_baseline"] = base
        rec["_ilp"] = ilp_rec
        rec["_lib"] = lib
    return rec


def assert_pair(rec: Dict[str, Any]) -> None:
    """Sanity assertions of the plan on a :func:`run_pair` record: the baseline
    passes ``check`` except for the report-only families (9), (17), (18); the ILP
    schedule passes ``check`` with zero violations; ILP cost <= baseline cost;
    identity (24) holds for both."""
    assert rec["baseline_ok_modulo_report_only"], f"baseline violations {rec['baseline_families']}"
    assert rec["baseline_identity_24_ok"], "baseline breaks identity (24)"
    assert rec["ilp_status"] not in ("INFEASIBLE", "INF_OR_UNBD", "UNBOUNDED"), rec["ilp_status"]
    if rec["ilp_obj"] is not None:
        assert rec["ilp_ok"], "ILP schedule violates constraints"
        assert rec["ilp_identity_24_ok"], "ILP breaks identity (24)"
        assert rec["ilp_le_baseline"], f"ILP {rec['ilp_total']} > baseline {rec['baseline_total']}"


def pair_anomalies(rec: Dict[str, Any]) -> List[str]:
    """Human-readable flags of a :func:`run_pair` record that the round-2 tables should
    print (fairness review F4 / F5 / F7): pruning that bound the policy
    (``baseline_pruned_fallbacks > 0``), stranded bikes, suppressed late trips,
    structurally unservable orders and MIP-start fallback variants that raised."""
    out: List[str] = []
    tag = f"{rec.get('name', '')}"
    if rec.get("baseline_pruned_fallbacks"):
        out.append(f"{tag}: the shared pruning bound the baseline {rec['baseline_pruned_fallbacks']} time(s) "
                   f"(pruned_arc_fallbacks; round-1 parity rule)")
    if rec.get("baseline_stranded"):
        out.append(f"{tag}: {rec['baseline_stranded']} baseline bike(s) stranded (no feasible reposition / terminal)")
    if rec.get("baseline_late_suppressed"):
        out.append(f"{tag}: {rec['baseline_late_suppressed']} late swap trip(s) suppressed by the end window")
    if rec.get("n_unservable"):
        out.append(f"{tag}: {rec['n_unservable']} order(s) structurally unservable (no delivery arc; both methods pay P)")
    errs = rec.get("mip_start_fallback_errors")
    if errs and errs not in ("{}", ""):
        out.append(f"{tag}: MIP-start fallback variants raised {errs}")
    return out


# ---------------------------------------------------------------------------
# output helpers
# ---------------------------------------------------------------------------
def ensure_dir(path: str) -> str:
    """``os.makedirs(path, exist_ok=True)``; returns ``path``."""
    os.makedirs(path, exist_ok=True)
    return path


def records_to_frame(records: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """DataFrame of flat records; keys starting with ``_`` (schedules, libraries)
    and non-scalar values are dropped or JSON-encoded."""
    rows = []
    for rec in records:
        row = {}
        for k, v in rec.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (dict, list, tuple, set)):
                row[k] = json.dumps(v, default=str, sort_keys=True)
            else:
                row[k] = v
        rows.append(row)
    return pd.DataFrame(rows)


def write_csv(records: Iterable[Dict[str, Any]], path: str) -> pd.DataFrame:
    """Write flat records to ``path`` (CSV, ``csv.QUOTE_MINIMAL``) and return the frame."""
    df = records_to_frame(records)
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    return df


def fmt(v: Any, digits: int = 3) -> str:
    """Compact cell formatting for Markdown tables (floats rounded, None -> '-')."""
    if v is None:
        return "-"
    if isinstance(v, float):
        if math.isnan(v):
            return "-"
        if abs(v - round(v)) < 1e-9 and abs(v) < 1e12:
            return str(int(round(v)))
        return f"{v:.{digits}f}"
    return str(v)


def markdown_table(df: pd.DataFrame, columns: Optional[Sequence[str]] = None,
                   digits: int = 3) -> str:
    """GitHub-flavoured Markdown table of ``df`` (optionally a column subset)."""
    cols = list(columns) if columns is not None else list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row[c], digits) for c in cols) + " |")
    return "\n".join(lines)


def plot_cost_components(records: Sequence[Dict[str, Any]], path: str,
                         prefixes: Sequence[str] = ("baseline_", "ilp_"),
                         title: str = "Cost components (26)") -> str:
    """Stacked bars of the (27)-(32) components per record and method; saved to ``path``."""
    comps = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"]
    labels = [str(r.get("label") or r.get("name") or i) for i, r in enumerate(records)]
    fig, ax = plt.subplots(figsize=(max(6, 1.6 * len(records) * len(prefixes)), 4))
    width = 0.8 / len(prefixes)
    for pi, prefix in enumerate(prefixes):
        bottoms = [0.0] * len(records)
        xs = [i + pi * width for i in range(len(records))]
        for comp in comps:
            vals = [float(r.get(f"{prefix}{comp}") or 0.0) for r in records]
            ax.bar(xs, vals, width, bottom=bottoms, label=f"{prefix}{comp}" if pi == 0 else None)
            bottoms = [b + v for b, v in zip(bottoms, vals)]
        for x, b in zip(xs, bottoms):
            ax.text(x, b, prefix.rstrip("_"), ha="center", va="bottom", fontsize=7)
    ax.set_xticks([i + 0.4 - width / 2 for i in range(len(records))])
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("cost (toy units)")
    ax.set_title(title)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_inventory(inst: Instance, lib: ArcLibrary, sched: Schedule, path: str,
                   title: str = "Stock n_jqt (13)") -> str:
    """Step plot of ``n_jqt`` per facility and level over ``t = 0..H`` (plus
    ``m_t``); saved to ``path``."""
    df = inventory_table(inst, lib, sched)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    for col in df.columns:
        if col == "t":
            continue
        ax.step(df["t"], df[col], where="post", label=col)
    ax.set_xlabel("boundary t")
    ax.set_ylabel("batteries")
    ax.set_title(title)
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# round 3 helpers (DECISIONS round-3 user decisions; experiments/e*_round3.py)
# ---------------------------------------------------------------------------
#: Gurobi parameters of every round-3 solve (``ilp.build_model(params=...)``): a fixed
#: random seed so that re-runs are reproducible.  Threads / TimeLimit are passed
#: separately (``THREADS``, 300 s; 600 s for the E3u separated transfers-free cells).
ILP_PARAMS_R3: Dict[str, Any] = {"Seed": 0}
#: Service-share levels of (33) ``sum_i (1 - u_i) >= zeta |I|``: main setting and sensitivity.
ZETA_MAIN = 0.90
ZETA_SENS = 0.85
#: A stored ILP row is reused (not re-solved) when its status is OPTIMAL or its MIP gap
#: is at most this value (round-3 rule "already solved to OPTIMAL or within 1 % gap").
REUSE_GAP_TOL = 0.01
#: Row status of a solve the wall budget did not allow (never exceed the budget).
SKIPPED_BUDGET = "SKIPPED_BUDGET"


class WallBudget:
    """Wall-clock guard shared by the round-3 scripts: ``remaining()`` seconds left,
    ``solve_limit(tl)`` = the TimeLimit to give the next solve (``min(tl, remaining -
    margin)``) or ``None`` when fewer than ``min_solve_s`` seconds remain, in which case
    the run is recorded as :data:`SKIPPED_BUDGET` instead of being started.  The
    ``margin`` covers library / model build and the fixed-solve start verification."""

    def __init__(self, budget_s: float, margin_s: float = 90.0, min_solve_s: float = 30.0) -> None:
        self.t0 = time.perf_counter()
        self.budget = float(budget_s)
        self.margin = float(margin_s)
        self.min_solve_s = float(min_solve_s)

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0

    def remaining(self) -> float:
        return self.budget - self.elapsed()

    def solve_limit(self, time_limit: float) -> Optional[float]:
        avail = self.remaining() - self.margin
        if avail < self.min_solve_s:
            return None
        return float(min(time_limit, avail))


def reusable_ilp_row(status: Any, gap: Any, tol: float = REUSE_GAP_TOL) -> bool:
    """True when a stored ILP row counts as solved: ``status == 'OPTIMAL'`` or a finite
    MIP gap ``<= tol`` (any status with an incumbent, e.g. TIME_LIMIT at 0.04 %)."""
    if status == "OPTIMAL":
        return True
    try:
        g = float(gap)
    except (TypeError, ValueError):
        return False
    return (not math.isnan(g)) and g <= tol


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Records of a JSON-lines file (``[]`` when absent); blank lines are skipped."""
    if not os.path.exists(path):
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def jsonable(v: Any) -> Any:
    """JSON-safe copy of a record (numpy scalars -> Python, other objects -> ``str``)."""
    if isinstance(v, (bool, int, float, str)) or v is None:
        return v
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [jsonable(x) for x in v]
    if hasattr(v, "item") and callable(v.item):  # numpy scalar
        try:
            return v.item()
        except Exception:  # noqa: BLE001
            return str(v)
    return str(v)


def append_jsonl(path: str, row: Dict[str, Any]) -> None:
    """Append one record (with ``wall_clock``) to a JSON-lines file, creating it."""
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    rec = dict(row)
    rec.setdefault("wall_clock", time.strftime("%Y-%m-%d %H:%M:%S"))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(jsonable(rec)) + "\n")


def max_service_share(inst: Instance, lib: ArcLibrary, mip_start: Optional[Schedule] = None,
                      time_limit: float = DEFAULT_TIME_LIMIT, threads: int = THREADS,
                      params: Optional[Dict[str, Any]] = None,
                      **build_kwargs: Any) -> Dict[str, Any]:
    """Maximum feasible served share of ``inst`` under the E2 constraints: one Gurobi solve
    of ``min sum_i u_i`` (the lexicographic stage 1 alone, E2 p.9) on the model of
    :func:`ebike_swap_sim.ilp.build_model` with the given switches (``no_transfers`` etc.;
    ``zeta`` is never imposed here).  Used when a service-share run (33) is INFEASIBLE so
    the reader sees *why*: the share that no schedule can exceed.

    Returns ``{'status', 'runtime', 'n_orders', 'n_unservable', 'min_unserved'
    (incumbent, None without one), 'min_unserved_bound' (Gurobi ObjBound), 'share_achievable'
    (= 1 - min_unserved / |I|, a lower bound on the maximum share), 'share_upper_bound'
    (= 1 - ceil(bound) / |I|), 'certified' (status OPTIMAL: both coincide), 'mip_start_accepted'}``.
    The optional ``mip_start`` (e.g. the written-model schedule) only seeds the incumbent."""
    from ebike_swap_sim import ilp
    import gurobipy as gp
    from gurobipy import GRB

    mdl = ilp.build_model(inst, lib, threads=threads, time_limit=time_limit,
                          params={**ILP_PARAMS_R3, **(params or {})}, **build_kwargs)
    start_info: Dict[str, Any] = {}
    if mip_start is not None:
        try:
            start_info = mdl.set_mip_start(mip_start, verify=False)
        except Exception as exc:  # noqa: BLE001 - a start that does not fit is simply not used
            start_info = {"error": f"{type(exc).__name__}: {exc}"}
    m = mdl.model
    m.setObjective(mdl.sum_u, GRB.MINIMIZE)
    m.optimize()
    n = len(inst.orders)
    out: Dict[str, Any] = {
        "status": ilp.status_name(m.Status), "runtime": float(m.Runtime), "n_orders": n,
        "n_unservable": len(unservable_orders(inst, lib)),
        "min_unserved": None, "min_unserved_bound": None,
        "share_achievable": None, "share_upper_bound": None,
        "certified": bool(m.Status == GRB.OPTIMAL),
        "mip_start_given": bool(start_info.get("given")), "mip_start_info": start_info,
        "threads": threads, "time_limit": time_limit,
    }
    if m.SolCount > 0:
        u_star = int(round(m.ObjVal))
        out["min_unserved"] = u_star
        out["share_achievable"] = (1.0 - u_star / n) if n else None
    try:
        b = float(m.ObjBound)
        if not math.isinf(b):
            out["min_unserved_bound"] = b
            out["share_upper_bound"] = (1.0 - math.ceil(b - 1e-6) / n) if n else None
    except gp.GurobiError:
        pass
    if out["certified"] and out["share_achievable"] is not None:
        out["share_upper_bound"] = out["share_achievable"]
    try:
        m.dispose()
        mdl.env.dispose()
    except Exception:  # noqa: BLE001
        pass
    return out


def run_zeta_case(inst: Instance, lib: ArcLibrary, zeta: float, mip_start: Optional[Schedule] = None,
                  time_limit: float = DEFAULT_TIME_LIMIT, threads: int = THREADS,
                  label: Optional[str] = None, max_service_start: Optional[Schedule] = None,
                  max_service_time_limit: Optional[float] = None,
                  params: Optional[Dict[str, Any]] = None, **build_kwargs: Any) -> Dict[str, Any]:
    """:func:`run_ilp_case` with the service-share constraint (33) at ``zeta`` (round-3
    decision (1)); Gurobi ``Seed = 0`` (:data:`ILP_PARAMS_R3`).  When the run ends
    INFEASIBLE / INF_OR_UNBD, or stops without any incumbent, the record additionally
    carries ``max_service`` = :func:`max_service_share` (the largest share any schedule
    can reach, so an infeasible zeta is explained) and ``zeta_feasible`` is ``False`` for a
    proven infeasibility, ``None`` when feasibility is undecided (no incumbent, no proof).
    ``mip_start`` is used only when it serves at least ``zeta |I|`` orders (a start that
    violates (33) would be rejected by the fixed-solve certificate anyway)."""
    label = label or f"ilp_zeta{int(round(100 * zeta))}"
    n = len(inst.orders)
    start = mip_start
    start_ok = None
    if start is not None:
        unserved = sum(int(v) for v in (start.u or {}).values())
        start_ok = (n - unserved) >= zeta * n - 1e-9
        if not start_ok:
            start = None
    rec = run_ilp_case(inst, lib, mip_start=start, time_limit=time_limit, threads=threads, label=label,
                       zeta=float(zeta), params={**ILP_PARAMS_R3, **(params or {})}, **build_kwargs)
    rec["zeta"] = float(zeta)
    rec["zeta_min_served"] = math.ceil(zeta * n - 1e-9)
    rec["start_satisfies_zeta"] = start_ok
    infeasible = rec["status"] in ("INFEASIBLE", "INF_OR_UNBD")
    undecided = (not infeasible) and rec["schedule"] is None
    rec["zeta_feasible"] = False if infeasible else (None if undecided else True)
    rec["max_service"] = None
    if infeasible or undecided:
        rec["max_service"] = max_service_share(
            inst, lib, mip_start=max_service_start if max_service_start is not None else mip_start,
            time_limit=max_service_time_limit if max_service_time_limit is not None else time_limit,
            threads=threads, params=params, **build_kwargs)
        ms = rec["max_service"]
        if ms.get("certified") and ms.get("share_achievable") is not None:
            # a certified maximum below zeta proves infeasibility even when Gurobi only timed out
            if ms["share_achievable"] < zeta - 1e-9:
                rec["zeta_feasible"] = False
            elif undecided:
                rec["zeta_feasible"] = True   # a feasible point exists, the cost solve just ran out of time
    return rec


def zeta_implied_by_written(written_status: Any, written_served_share: Any, zeta: float,
                            written_gap: Any = None) -> bool:
    """True when a written-model optimum already serves at least ``zeta |I|`` orders, so the
    optimum of the zeta-constrained model (a restriction) equals the written one and no
    solve is needed (the cell is recorded with ``solve_mode = 'implied_by_written'``).
    Requires a certified written optimum (status OPTIMAL, or gap <= 1e-4)."""
    if written_served_share is None:
        return False
    try:
        share = float(written_served_share)
    except (TypeError, ValueError):
        return False
    certified = written_status == "OPTIMAL"
    if not certified:
        try:
            certified = float(written_gap) <= 1e-4
        except (TypeError, ValueError):
            certified = False
    return certified and share >= zeta - 1e-9


__all__ = [
    "FAMILIES", "R2_FAMILIES", "PRUNING_DEFAULTS", "PRUNING_NYC", "OUTPUT_ROOT", "THREADS", "DEFAULT_TIME_LIMIT",
    "BASELINE_REPORT_ONLY", "BASELINE_VARIANTS", "MIP_START_FALLBACKS", "END_WINDOW_SLACK", "end_window",
    "baseline_variant_params", "feasible_mip_start", "relax_end_targets", "gap_definitions",
    "unservable_orders", "demand_key", "demand_md5", "baseline_pruning_flags", "pair_anomalies",
    "make_instance", "pruning_for", "build_library",
    "family_counts", "check_identity_24", "flatten_cost", "inventory_table",
    "path_description", "run_baseline_case", "run_ilp_case", "run_pair", "assert_pair",
    "ensure_dir", "records_to_frame", "write_csv", "fmt", "markdown_table",
    "plot_cost_components", "plot_inventory",
    "ILP_PARAMS_R3", "ZETA_MAIN", "ZETA_SENS", "REUSE_GAP_TOL", "SKIPPED_BUDGET", "WallBudget",
    "reusable_ilp_row", "load_jsonl", "jsonable", "append_jsonl", "max_service_share",
    "run_zeta_case", "zeta_implied_by_written",
]
