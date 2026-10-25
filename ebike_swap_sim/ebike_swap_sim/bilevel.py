"""Bi-level siting of swapping and charging stations on top of the E2 model
(``notes/bilevel_siting_design.md``; equation numbers refer to ``notes/extracted/E2.txt``).

Leader (planner): which candidate locations to open, with which role (``S`` swap-only,
``C`` charge-only hub, ``SC`` co-located) and size (``B_j`` spares, ``C_j`` chargers),
subject to one role per location [U1], the investment budget [U2] = (33a), the bounds
[U3] = (7)-(8) and, optionally, the planner-only access row [U4] and the expected
service-share row [U5].  Follower (per demand scenario ``s``): the E2 operations ILP
(5)-(22), (28)-(32) with the facilities fixed, exactly ``ilp.build_model(fixed_facilities
=True)`` on the layout instance of :mod:`ebike_swap_sim.sites_nyc`.  Upper objective::

    Phi(y, B, C) = sum_j (F_j y_j + bB_j B_j + bC_j C_j)  +  sum_s p_s OPEX_s(y, B, C)

The optimistic (cooperative) bi-level problem is assumed; with the shared objective the
follower enters only through its optimal value ``OPEX_s`` (unique), so without [U4] /
[U5] the problem collapses to one two-stage stochastic ILP (algorithm A, the exact
benchmark).  Because the follower is an ILP, KKT / duality reformulations do not apply;
the upper-level methods are enumerative, decomposition-based or heuristic with the lower
level solved as a black box (Gurobi), and (A) is the reference wherever it closes its gap.

Contents
--------
:class:`Layout` -- open ``(l, r, B, C)`` items with ``investment()`` / ``allocated_cost()``;
:class:`LowerLevelEvaluator` -- certified lower-level values per scenario with a persistent
JSONL cache (keyed by layout, scenario, policy and the model protocol), baseline warm
starts, the superset lower bound and scenario-by-scenario pruning;
:func:`exhaustive` (B), :func:`greedy_local_search` (C), :func:`deck_heuristic` (D),
:func:`integrated_stochastic_ilp` (A) and :func:`cross_evaluate` (E); the access helpers
:func:`access_sets` / :func:`layout_covers` / :func:`uncovered_zones`.  Relaunch conventions
(``notes/DECISIONS.md``, "E9 relaunch decisions"): the evaluator's ``reposition`` mode
(``all_candidates`` template sub-libraries for (A) / (B), per-layout ``open_sites`` libraries for
the search), ``ERROR`` rows for exceptions, and the greedy's best-singleton start, served-share
guard, wall-budget reporting and access repair.  All lower-level solves follow the round-3
protocol (``experiments.common.run_ilp_case``: ``OutputFlag 0``, ``Threads <= 3``,
``Seed 0``, a ``TimeLimit``; ``evaluate.check`` clean and ``evaluate.cost == objective``).

Integrated model route (design section 3, algorithm A): ONE ``gurobipy`` model with the
facility variables ``y_j, B_j, C_j`` created here and shared by one
:class:`~ebike_swap_sim.ilp.ILPModel` **sub-model per scenario** (``ILPModel(model=m,
prefix=..., facility_vars=(y, B, C), set_objective=False)``: the sub-model adds its
operations variables and rows (5)-(6), (9)-(22) to the shared model and leaves (7)-(8),
(33) and the objective to the caller).  This keeps ``ilp.py`` byte-for-byte on its default
path and reuses its builder, extraction and MIP-start code without copying variables.
Only this module and ``ilp.py`` touch gurobipy (lazily here).

Round 5 (``notes/reading_to_model.md``; no E2 equation changes, every item is a policy, data,
wrapper or solver change):

* **M4** -- follower ``E``: the evaluator's third policy ``'selfish'`` = the ``r5_selfish``
  equilibrium of ``baseline.run_selfish_equilibrium`` (self-interested station choice, iterated
  best response); :func:`cross_evaluate` prices every layout under ``ilp``, ``baseline`` and
  ``selfish`` (price of decentralisation); :func:`greedy_local_search` ``(policy=...)`` searches
  with a policy as the lower level (policy-aware siting); :func:`compliance_sweep` lets a share
  ``alpha_c`` of the riders follow the ILP plan.
* **A4** -- siting baselines: the IJCAI-15 rules :func:`rule_layout` / :func:`rule_baselines`
  (``CSCD`` demand-proportional, ``CSTC`` cost in isolation or inverse-distance access, ``CSAV``
  uniform) at equal budget, the capacity-matched present-day layout
  (:func:`present_day_sites`, :func:`capacity_matched_layout`) and the marginal-lever table
  :func:`lever_table` (+1 spare, +1 charger, +1 swap position, one shuttle, +10 % grid) under
  each follower; lever variants are evaluator ``variant`` data (``M_j``, extra services,
  ``P_grid``) applied to the layout instances.
* **O1** -- :func:`integrated_stochastic_ilp` uses the aggregated integer flow
  (``ilp.build_submodel``, ``aggregate.py``) when available (feature-detected), and the
  evaluator can price lower levels with it (``aggregate=True``; equivalent formulation).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import threading
import time
import traceback
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .arcs import ArcLibrary, build_arcs, radius_exempt_states
from .costs import pricing_cache_component
from .evaluate import Schedule, check, cost, metrics
from .or_instance import Instance, Node
from . import sites_nyc as SN
from .sites_nyc import (REPOSITION_MODES, ROLE_CHARGE, ROLE_SWAP, ROLES, Candidate, SitingSpec, all_candidates_instance,
                        facility_id, layout_admissible, layout_instance, manhattan_blocks, siting_pruning,
                        split_facility_id, subset_library)

__all__ = [
    "CACHE_VERSION", "INF", "INFEASIBLE_TERMINAL", "INFEASIBLE_ILP", "NO_INCUMBENT", "SKIPPED_BOUND",
    "PRUNED", "SKIPPED_BUDGET", "ERROR", "LOW_SERVICE", "NO_FEASIBLE_LAYOUT", "WALL_EXHAUSTED", "Layout", "DEFAULT_SIZE_MENU", "VALIDATION_GRID", "option_grid",
    "portable_schedule", "materialise_schedule", "LowerLevelEvaluator", "enumerate_layouts", "exhaustive",
    "greedy_local_search", "deck_heuristic", "integrated_stochastic_ilp", "cross_evaluate", "access_sets",
    "layout_covers", "uncovered_zones", "zone_site_distances",
    "POLICIES", "LEVERS", "RULES", "aggregate_available", "apply_variant", "lever_table", "compliance_sweep",
    "demand_weights", "access_weights", "isolation_values", "rule_layout", "rule_baselines", "present_day_sites",
    "capacity_matched_layout", "PRESENT_DAY_FILES", "bd_stopped", "dot_pilot_layout", "stratified_ci", "paired_ci",
]

#: Bump when the semantics of a cached lower-level row change (invalidates the cache).
CACHE_VERSION = "e9-2"
INF = float("inf")
INFEASIBLE_TERMINAL = "INFEASIBLE_TERMINAL"   # some bike has no reachable terminal arc (9)
INFEASIBLE_ILP = "INFEASIBLE_ILP"             # Gurobi proved the lower level infeasible (end targets)
NO_INCUMBENT = "NO_INCUMBENT"                 # time limit without any feasible schedule
SKIPPED_BOUND = "SKIPPED_BOUND"               # exhaustive: lower bound >= incumbent, not solved
PRUNED = "PRUNED"                             # exhaustive: stopped after some scenarios
SKIPPED_BUDGET = "SKIPPED_BUDGET"             # wall budget exhausted before the solve
ERROR = "ERROR"                               # an exception in the lower-level evaluation (recorded, never cached)
LOW_SERVICE = "LOW_SERVICE"                   # greedy: feasible but serves < min_served_share (discarded)
NO_FEASIBLE_LAYOUT = "no feasible layout"     # greedy: no admissible layout priced feasible with enough service
WALL_EXHAUSTED = "wall budget exhausted"      # greedy: the search stopped because the wall budget ran out
_TOL = 1e-6


def bd_stopped(row: Dict[str, Any]) -> bool:
    """Plan item O2: ``True`` when the solve of a cached row was actually stopped by Gurobi
    ``BestBdStop`` (status or Gurobi status ``USER_OBJ_LIMIT``; with or without an incumbent).
    A row solved with a ``best_bd_stop`` that never fired is an ordinary solve."""
    return row.get("status") == "USER_OBJ_LIMIT" or row.get("gurobi_status") == "USER_OBJ_LIMIT"


#: Lower-level policies of the evaluator: the E2 ILP (system optimum), the R2.3 baseline policy and
#: follower ``E`` = the ``r5_selfish`` equilibrium (plan item M4).
POLICIES: Tuple[str, ...] = ("ilp", "baseline", "selfish")


def aggregate_available() -> bool:
    """Plan item O1 feature detection: ``True`` when ``aggregate.py`` and ``ilp.build_submodel``
    (the aggregated integer flow of E2 (5), (9)) can be imported (gurobipy present)."""
    try:
        from . import aggregate as _agg  # noqa: F401
        from . import ilp as _ilp
    except Exception:  # noqa: BLE001 -- missing module or gurobipy
        return False
    return hasattr(_ilp, "build_submodel")


def _norm_variant(variant: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not variant:
        return {}
    out: Dict[str, Any] = {}
    for k, v in variant.items():
        if k == "M":
            out["M"] = {str(l): int(m) for l, m in sorted(v.items())}
        elif k == "grid_factor":
            out["grid_factor"] = float(v)
        elif k == "extra_shuttle":
            out["extra_shuttle"] = bool(v)
        elif k == "name":
            out["name"] = str(v)
        elif k == "P_kw":                       # R7 hub economics: site power cap per role, {role: kW}
            out["P_kw"] = {str(r): float(x) for r, x in sorted(dict(v).items())}
        else:
            raise ValueError(f"unknown variant key {k!r} (M, grid_factor, extra_shuttle, P_kw, name)")
    return out


def apply_variant(inst: Instance, variant: Optional[Dict[str, Any]], spec: Optional[SitingSpec] = None) -> Instance:
    """Lever data of plan item A4 (iii) applied to a layout instance in place (no E2 equation
    changes): ``M`` = ``{location: M_j}`` swap positions of (22) at those locations;
    ``grid_factor`` scales every grid-group cap ``P_grid`` of (21) (``1.1`` = +10 % grid);
    ``extra_shuttle`` = one more shuttle vehicle on the timetable: every service ``(o, d, l, u)``
    of (10)-(11) gets a twin departing ``max(1, every // 2)`` slots later (when it ends by ``H``
    and is not already offered), same ``U, f, vreb``; ``P_kw`` = ``{role: kW}`` site power cap
    of (20) per role object (R7 hub-economics sensitivity: sidewalk SC cabinets at 0.7 kW, hubs
    at 2.8 kW).  Returns ``inst`` (re-indexed, validated)."""
    var = _norm_variant(variant)
    if not var:
        return inst
    if var.get("M"):
        for f in inst.facilities:
            loc = split_facility_id(f.id)[0]
            if f.swap and loc in var["M"]:
                f.M = int(var["M"][loc])
    if var.get("P_kw"):                         # site power cap of (20) per role object (data only)
        for f in inst.facilities:
            role = split_facility_id(f.id)[1]
            if f.charge and role in var["P_kw"]:
                f.P_kw = float(var["P_kw"][role])
    if var.get("grid_factor") is not None and inst.P_grid:
        inst.P_grid = {g: [float(x) * var["grid_factor"] for x in caps] for g, caps in inst.P_grid.items()}
    if var.get("extra_shuttle") and inst.services:
        every = int(spec.every) if spec is not None else 6
        shift = max(1, every // 2)
        have = {(e.o_fac, e.d_fac, e.l, e.u) for e in inst.services}
        nxt = max(e.id for e in inst.services) + 1
        extra = []
        for e in list(inst.services):
            l2, u2 = e.l + shift, e.u + shift
            if u2 <= inst.H and (e.o_fac, e.d_fac, l2, u2) not in have:
                have.add((e.o_fac, e.d_fac, l2, u2))
                extra.append(type(e)(id=nxt, o_fac=e.o_fac, d_fac=e.d_fac, l=l2, u=u2, U=e.U, f=e.f, vreb=e.vreb))
                nxt += 1
        inst.services = list(inst.services) + extra
    inst.meta["variant"] = dict(var)
    inst.reindex()
    inst.validate()
    return inst

#: Size menu of the greedy / local search (design algorithm C): ``role -> [(B, C), ...]``.
DEFAULT_SIZE_MENU: Dict[str, List[Tuple[int, int]]] = {
    "S": [(1, 0), (2, 0), (3, 0)],
    "C": [(0, 1), (0, 2)],
    "SC": [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)],
}
#: Option grid of the E9.1 validation (design Appendix B): ``S: B in {1,2}``, ``SC: B in {1,2}, C = 1``.
VALIDATION_GRID: List[Tuple[str, int, int]] = [("S", 1, 0), ("S", 2, 0), ("SC", 1, 1), ("SC", 2, 1)]


def option_grid(size_menu: Dict[str, Sequence[Tuple[int, int]]] = DEFAULT_SIZE_MENU,
                roles: Sequence[str] = ROLES) -> List[Tuple[str, int, int]]:
    """``[(role, B, C), ...]`` of a size menu restricted to ``roles``."""
    return [(r, int(B), int(C)) for r in roles for (B, C) in size_menu.get(r, [])]


# ---------------------------------------------------------------------------
# layouts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Layout:
    """Open facility objects ``{(l, r, B, C)}`` of the planner, sorted by location; at most
    one role per location [U1].  Hashable, JSON round-trip (``to_json`` / ``from_json``),
    canonical ``key()`` (``'L01:SC:B2:C1|L03:S:B1:C0'``, ``'empty'``)."""
    open: Tuple[Tuple[str, str, int, int], ...] = ()

    @staticmethod
    def of(items: Iterable[Any]) -> "Layout":
        norm = tuple(SN.layout_items(items))
        locs = [it[0] for it in norm]
        if len(set(locs)) != len(locs):
            raise ValueError(f"a location is opened twice: {locs}")
        for _l, r, B, C in norm:
            if r not in ROLES:
                raise ValueError(f"unknown role {r!r}")
            if B < 0 or C < 0 or (not ROLE_CHARGE[r] and C != 0):
                raise ValueError(f"invalid sizes B={B}, C={C} for role {r}")
        return Layout(norm)

    def __post_init__(self) -> None:
        object.__setattr__(self, "open", tuple(SN.layout_items(self.open)))

    def key(self) -> str:
        return "|".join(f"{l}:{r}:B{B}:C{C}" for l, r, B, C in self.open) or "empty"

    def __str__(self) -> str:
        return self.key()

    @property
    def n_open(self) -> int:
        return len(self.open)

    def locations(self) -> Tuple[str, ...]:
        return tuple(it[0] for it in self.open)

    def item(self, loc: str) -> Optional[Tuple[str, str, int, int]]:
        for it in self.open:
            if it[0] == loc:
                return it
        return None

    def role(self, loc: str) -> Optional[str]:
        it = self.item(loc)
        return None if it is None else it[1]

    def has_swap(self) -> bool:
        return any(ROLE_SWAP[r] for _l, r, _B, _C in self.open)

    def has_charge(self) -> bool:
        return any(ROLE_CHARGE[r] for _l, r, _B, _C in self.open)

    def n_role(self, role: str) -> int:
        return sum(1 for it in self.open if it[1] == role)

    def total_B(self) -> int:
        return sum(it[2] for it in self.open)

    def total_C(self) -> int:
        return sum(it[3] for it in self.open)

    def investment(self, spec: SitingSpec = SN.DEFAULT_SPEC) -> float:
        """``inv(lambda) = sum_j (Fhat_j + bhat_j B_j + chat_j C_j)`` (33a), USD undiscounted."""
        return float(sum(spec.Fhat + spec.bhat * B + spec.chat * C for _l, _r, B, C in self.open))

    def allocated_cost(self, spec: SitingSpec = SN.DEFAULT_SPEC) -> float:
        """``C_setup = sum_j (F_j + bB_j B_j + bC_j C_j)`` (27), window-allocated."""
        return float(sum(spec.setup_cost(r) + spec.bB * B + spec.bC * C for _l, r, B, C in self.open))

    def valid(self, spec: SitingSpec) -> bool:
        return all(spec.valid_sizes(r, B, C) for _l, r, B, C in self.open)

    # -- edits ------------------------------------------------------------
    def add(self, item: Tuple[str, str, int, int]) -> "Layout":
        if self.item(item[0]) is not None:
            raise ValueError(f"{item[0]} already open")
        return Layout.of(self.open + (tuple(item),))

    def drop(self, loc: str) -> "Layout":
        return Layout.of(tuple(it for it in self.open if it[0] != loc))

    def replace(self, loc: str, item: Tuple[str, str, int, int]) -> "Layout":
        return self.drop(loc).add(item)

    # -- JSON -----------------------------------------------------------------
    def to_json(self) -> List[List[Any]]:
        return [list(it) for it in self.open]

    @classmethod
    def from_json(cls, data: Any) -> "Layout":
        if isinstance(data, str):
            data = json.loads(data)
        return cls.of([tuple(it) for it in data])

    @classmethod
    def from_key(cls, key: str) -> "Layout":
        if key == "empty":
            return cls()
        items = []
        for part in key.split("|"):
            l, r, b, c = part.split(":")
            items.append((l, r, int(b[1:]), int(c[1:])))
        return cls.of(items)


# ---------------------------------------------------------------------------
# portable schedules (library-independent, used for cache files and warm starts)
# ---------------------------------------------------------------------------
def _enc(v: Any) -> Any:
    return [_enc(w) for w in v] if isinstance(v, tuple) else v


def _dec(v: Any) -> Any:
    return tuple(_dec(w) for w in v) if isinstance(v, list) else v


def portable_schedule(sched: Schedule, inst: Instance, lib: ArcLibrary) -> Dict[str, Any]:
    """Library-independent form of a schedule: chosen arcs as ``(kind, src, dst, order, fac)``
    descriptors per bike, services as ``(o_fac, d_fac, l, u)`` keys (ids differ between layout
    instances), ``u`` / ``c`` as they are.  Re-attached with :func:`materialise_schedule`."""
    x = {}
    for k, ids in sched.x.items():
        x[str(_enc(k))] = [[a.kind, _enc(a.src), _enc(a.dst), _enc(a.order), _enc(a.fac)]
                          for a in (lib.arc(int(i)) for i in ids)]
    svc = {s.id: (s.o_fac, s.d_fac, s.l, s.u) for s in inst.services}
    return {
        "x": x,
        "u": [[_enc(i), int(v)] for i, v in sched.u.items()],
        "c": [[_enc(j), q, t, int(v)] for (j, q, t), v in sched.c.items() if v],
        "h": [[list(svc[e]), int(v)] for e, v in sched.h.items() if v and e in svc],
        "z": [[list(svc[e]), q, int(v)] for (e, q), v in sched.z.items() if v and e in svc],
        "bike_ids": [_enc(b.id) for b in inst.bikes],
    }


def materialise_schedule(port: Dict[str, Any], inst: Instance, lib: ArcLibrary,
                         facilities: Optional[Tuple[Dict[Any, int], Dict[Any, int], Dict[Any, int]]] = None
                         ) -> Optional[Schedule]:
    """Schedule of a portable form on ``inst`` / ``lib``; ``None`` when an arc or a service
    does not exist there (e.g. a swap at a closed facility).  ``facilities`` = ``(y, B, C)``
    dicts to store on the schedule (all facilities of ``inst``; default: the instance data)."""
    bike_ids = {str(b): _dec(b) for b in port["bike_ids"]}
    x: Dict[Any, List[int]] = {}
    for k_str, descs in port["x"].items():
        k = bike_ids.get(k_str, _dec(json.loads(k_str)) if k_str.startswith("[") else k_str)
        ids = []
        for kind, src, dst, order, fac in descs:
            a = lib.find(k, kind, _dec(src), order=_dec(order), fac=_dec(fac), dst=_dec(dst))
            if a is None:
                return None
            ids.append(a.id)
        x[k] = ids
    svc = {(s.o_fac, s.d_fac, s.l, s.u): s.id for s in inst.services}
    h: Dict[Any, int] = {}
    z: Dict[Tuple[Any, int], int] = {}
    for key, v in port.get("h", []):
        e = svc.get(tuple(key))
        if e is None:
            return None
        h[e] = int(v)
    for key, q, v in port.get("z", []):
        e = svc.get(tuple(key))
        if e is None:
            return None
        z[(e, int(q))] = int(v)
    u = {_dec(i): int(v) for i, v in port.get("u", [])}
    c = {(_dec(j), int(q), int(t)): int(v) for j, q, t, v in port.get("c", [])}
    for (j, _q, _t) in c:
        if j not in inst.N:
            return None
    if facilities is None:
        y = {f.id: (1 if f.y is None else int(f.y)) for f in inst.facilities}
        B = {f.id: (0 if f.B is None else int(f.B)) for f in inst.facilities}
        C = {f.id: (0 if f.C is None else int(f.C)) for f in inst.facilities}
    else:
        y, B, C = (dict(d) for d in facilities)
    return Schedule(x=x, u=u, c=c, h=h, z=z, y=y, B=B, C=C)


# ---------------------------------------------------------------------------
# lower-level evaluator
# ---------------------------------------------------------------------------
def _flat_metrics(met: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "served_share": met["served_share"], "n_served": met["n_served"], "n_unserved": met["n_unserved"],
        "n_late": met["n_late"], "mean_response_h": met["mean_response_h"],
        "mean_lateness_h": met["mean_lateness_h"], "bike_km": met["bike_km"], "n_swaps": met["n_swaps"],
        "swaps_per_facility": {str(k): int(v) for k, v in met["swaps_per_facility"].items()},
        "queue_wait_slots": int(sum(met["wait_before_swap"])),
        "stockout_slots": {str(k): int(v) for k, v in met["stockout_slots"].items()},
        "kwh_purchased": met["kwh_purchased"], "transfers_used": met["transfers_used"],
        "batteries_moved": met["batteries_moved"], "end_full_total": met["end_full_total"],
        "end_target_shortfall": met["end_target_shortfall"],
    }


def _md5(obj: Any) -> str:
    return hashlib.md5(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _pruning_signature(pr: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (sorted(map(str, v)) if isinstance(v, (set, frozenset)) else v) for k, v in sorted(pr.items())}


class LowerLevelEvaluator:
    """Certified lower-level values ``OPEX_s(lambda)`` of layouts on a fixed scenario set.

    Parameters
    ----------
    scenarios : base instances (``sites_nyc.make_base_instance`` or a toy equivalent carrying
        ``meta['candidates']``, ``meta['depots']``, ``meta['seed']``), one per scenario ``s``.
    spec : :class:`~ebike_swap_sim.sites_nyc.SitingSpec` (roles, costs, timetable).
    probabilities : ``p_s`` (default uniform).
    time_limit, threads, params : Gurobi protocol of every lower-level solve (``Seed 0``
        by default); ``time_limit_hub`` applies to layouts with a charge-only hub (the E3u
        600 s rule), default = ``time_limit``.
    cache_dir : directory of the persistent cache (``index.jsonl`` + ``schedules/``); ``None``
        = in-memory only.  A cached ILP row is reused when it is OPTIMAL, within 1 % gap
        (``common.reusable_ilp_row``) or a proven infeasibility, else re-solved.
    relaxed_targets : evaluate on the ``common.relax_end_targets`` copy (``rho = R_end = 0``).
    pruning : overrides of :func:`sites_nyc.siting_pruning` (``tau_max``, ...).
    wall : an object with ``solve_limit(time_limit) -> Optional[float]``
        (``experiments.common.WallBudget``); ``None`` = no wall budget.
    reposition : :data:`sites_nyc.REPOSITION_MODES`.  ``'all_candidates'`` (default): every
        scenario keeps ONE template library (all role objects of all candidates,
        :func:`sites_nyc.all_candidates_instance`) and layout libraries are derived from it with
        :func:`sites_nyc.subset_library` (identical to ``build_arcs`` on the layout instance) --
        the convention under which the integrated model (A) and the enumeration (B) price the
        same arcs.  ``'open_sites'``: the library of a layout is built directly with reposition
        targets = its open facility nodes + depots (E8 convention; smaller, faster; an upper
        bound on the all-candidates value), used by the search algorithms (C)-(E).  The mode is
        part of the cache key; the superset bound and the integrated model always use the
        all-candidates template.

    Exceptions raised inside a lower-level evaluation are caught and returned as rows with
    ``status = ERROR`` and the message (``error``, ``traceback``); they are appended to
    ``new_rows`` (so that the experiment records them) but never cached and never treated as
    an infeasible layout.

    Round 5: ``policy='selfish'`` (follower E, plan item M4) runs
    ``baseline.run_selfish_equilibrium`` with ``selfish`` = ``{'params': overrides of the
    r5_selfish variant, 'max_iter': 10, 'tol': 0.01, 'averaging': 'msa'}``; ``aggregate`` (O1)
    solves the lower-level ILP with the aggregated integer flow (``None`` = when
    :func:`aggregate_available`; an equivalent formulation, recorded in the cache key only when
    on); ``variant`` (A4 levers, :func:`apply_variant`) changes the layout instances' data and
    is part of the cache key.  :meth:`derive` builds an evaluator with another spec / variant
    sharing scenarios, templates and the in-memory cache.
    """

    def __init__(self, scenarios: Sequence[Instance], spec: SitingSpec, *, probabilities: Optional[Sequence[float]] = None,
                 time_limit: float = 300.0, time_limit_hub: Optional[float] = None, threads: int = 3,
                 params: Optional[Dict[str, Any]] = None, cache_dir: Optional[str] = None,
                 relaxed_targets: bool = False, pruning: Optional[Dict[str, Any]] = None,
                 wall: Any = None, verbose: bool = False, keep_libraries: int = 4,
                 reposition: str = "all_candidates", aggregate: Optional[bool] = False,
                 selfish: Optional[Dict[str, Any]] = None, variant: Optional[Dict[str, Any]] = None) -> None:
        if not scenarios:
            raise ValueError("at least one scenario is needed")
        if reposition not in REPOSITION_MODES:
            raise ValueError(f"reposition must be one of {REPOSITION_MODES} (got {reposition!r})")
        self.reposition = str(reposition)
        self.scenarios: List[Instance] = list(scenarios)
        self.spec = spec
        n = len(self.scenarios)
        self.p: List[float] = [1.0 / n] * n if probabilities is None else [float(x) for x in probabilities]
        if len(self.p) != n or abs(sum(self.p) - 1.0) > 1e-9:
            raise ValueError("probabilities must have one entry per scenario and sum to 1")
        self.seeds: List[int] = [int(inst.meta.get("seed", i)) for i, inst in enumerate(self.scenarios)]
        self.family: str = str(self.scenarios[0].meta.get("family", "custom"))
        self.time_limit = float(time_limit)
        self.time_limit_hub = float(time_limit if time_limit_hub is None else time_limit_hub)
        self.threads = int(threads)
        self.params: Dict[str, Any] = {"Seed": 0, **(params or {})}
        self.cache_dir = cache_dir
        self.relaxed_targets = bool(relaxed_targets)
        self.pruning_overrides = dict(pruning or {})
        self.wall = wall
        self.verbose = bool(verbose)
        self.keep_libraries = int(keep_libraries)
        self.candidates: List[Candidate] = SN.candidates_from_records(self.scenarios[0].meta["candidates"])
        self.cand_node: Dict[str, Node] = {c.id: c.node for c in self.candidates}
        #: R7: roles allowed per location (hubs only at hub-capable candidates; every role elsewhere)
        self.roles_of: Dict[str, Tuple[str, ...]] = SN.candidate_roles(self.candidates, ROLES)
        #: R7: one re-entrant lock guards the caches, the library LRUs and the counters so that
        #: several threads (``benders.PricingPool``) may price scenarios of one evaluator at once
        self._lock = threading.RLock()
        from experiments import common as C   # lazy: the runners / hashing conventions of the experiments layer
        self._C = C
        self.demand_md5: List[str] = [C.demand_md5(inst, include_bike_nodes=True, include_facilities=False)
                                      for inst in self.scenarios]
        #: all-candidates templates by scenario (an OrderedDict: least recently used first, for
        #: the optional ``max_templates`` cap; shared with :meth:`derive` siblings)
        self._templates: Dict[int, Tuple[Instance, ArcLibrary]] = OrderedDict()
        #: R7 memory lifecycle: at most this many templates resident (``None`` = no cap, the
        #: default); the least recently used one is evicted, :meth:`template` rebuilds it
        self.max_templates: Optional[int] = None
        self.n_template_builds = 0
        self.n_template_evictions = 0
        self._pairs: Dict[Tuple[str, int], Tuple[Instance, ArcLibrary]] = {}
        self._pair_order: List[Tuple[str, int]] = []
        self._tpairs: Dict[Tuple[str, int], Tuple[Instance, ArcLibrary]] = {}
        self._tpair_order: List[Tuple[str, int]] = []
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.index_path: Optional[str] = None
        self.sched_dir: Optional[str] = None
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            self.sched_dir = os.path.join(cache_dir, "schedules")
            os.makedirs(self.sched_dir, exist_ok=True)
            self.index_path = os.path.join(cache_dir, "index.jsonl")
            for row in C.load_jsonl(self.index_path):
                self.cache[row["key"]] = row
        self.aggregate = aggregate_available() if aggregate is None else bool(aggregate)
        self.selfish: Dict[str, Any] = {"params": {}, "max_iter": 10, "tol": 0.01, "averaging": "msa", **(selfish or {})}
        self.variant: Dict[str, Any] = _norm_variant(variant)
        self.n_solves = 0
        self.n_cache_hits = 0
        self.n_baseline_runs = 0
        self.n_errors = 0
        self.solver_time = 0.0
        self.library_time = 0.0
        self._bound: Optional[List[float]] = None
        self.bound_rows: List[Dict[str, Any]] = []
        self.new_rows: List[Dict[str, Any]] = []   # rows produced in this process (for experiment records)
        #: R7 re-plan change 6: ``False`` skips Gurobi's fix-and-solve verification of a MIP start
        #: that already passed ``evaluate.check`` on the layout instance (a clean rule start or a
        #: checked warm schedule).  Not part of the cache key (it changes no value, only the time
        #: of the verification solve, at most 60 s per cell); ``True`` = the old behaviour.
        self.verify_checked_starts: bool = True

    # ---------------------------------------------------------------- data
    @property
    def n_scenarios(self) -> int:
        return len(self.scenarios)

    def template(self, s: int) -> Tuple[Instance, ArcLibrary]:
        """All-candidates instance (every role object, free) and its library of scenario ``s``."""
        with self._lock:
            if s not in self._templates:
                inst = all_candidates_instance(self.scenarios[s], self.spec, self.roles_of)
                t0 = time.perf_counter()
                lib = build_arcs(inst, strict=False, **siting_pruning(inst, **self.pruning_overrides))
                self._log(f"template library of scenario {s} (seed {self.seeds[s]}): {len(lib)} arcs in "
                          f"{time.perf_counter() - t0:.1f} s")
                self._templates[s] = (inst, lib)
                self.n_template_builds = getattr(self, "n_template_builds", 0) + 1
                cap = getattr(self, "max_templates", None)
                if cap is not None and int(cap) >= 1:
                    for old in [k for k in list(self._templates) if k != s][: max(0, len(self._templates) - int(cap))]:
                        self.evict_template(old)
            elif hasattr(self._templates, "move_to_end"):
                self._templates.move_to_end(s)
            return self._templates[s]

    def evict_template(self, s: Optional[int] = None) -> int:
        """R7 memory lifecycle (production plan 5 item 2): drop the all-candidates template of
        scenario ``s`` (every scenario when ``None``) and the layout libraries derived from it.
        :meth:`template` rebuilds it on the next use; ``build_arcs`` is deterministic, so the
        library, the layout libraries, the cache keys and every value are identical (test
        ``test_template_eviction_gives_identical_values_and_cache_rows``).  The template dict is
        shared with the :meth:`derive` siblings (evicted for them too); objects that still hold
        a reference (a running derivation, a :class:`benders.ScenarioLP` that did not release
        it) keep it alive until they drop it.  Returns the number of templates dropped."""
        with self._lock:
            keys = list(self._templates) if s is None else ([int(s)] if int(s) in self._templates else [])
            for k in keys:
                self._templates.pop(k, None)
            for store, order in ((self._pairs, self._pair_order), (self._tpairs, self._tpair_order)):
                for key in [k for k in store if (s is None or k[1] == int(s))]:
                    store.pop(key, None)
                order[:] = [k for k in order if k in store]
            self.n_template_evictions = getattr(self, "n_template_evictions", 0) + len(keys)
            return len(keys)

    def resident_templates(self) -> List[int]:
        """Scenarios whose template is built now (least recently used first)."""
        with self._lock:
            return list(self._templates)

    def pruning_signature(self, s: int = 0, layout: Optional[Layout] = None) -> Dict[str, Any]:
        """Arc-builder options of the scenario's libraries (cache key component); computed
        from :func:`sites_nyc.siting_pruning` without building a library.  In the
        ``'open_sites'`` mode the reposition targets of ``layout`` (its open nodes + depots)
        replace the all-candidates set."""
        base = self.scenarios[s]
        opts = dict(base.options)
        opts.update(siting_pruning(base, **self.pruning_overrides))
        if layout is not None and self.reposition == "open_sites" and opts.get("reposition_targets") is not None:
            nodes = {self.cand_node[l] for l in layout.locations()}
            nodes.update(SN._grid_node(d) for d in base.meta.get("depots", []))
            opts["reposition_targets"] = nodes
        sig = _pruning_signature({k: v for k, v in opts.items()
                                  if k in ("energy_rounding", "dominance", "swap_q_max", "dummy_terminal_cost",
                                           "reposition_targets", "tau_max", "start_slack", "reachable_pruning")})
        rad = opts.get("reposition_target_radius")
        if rad is not None:                     # R7: present ONLY when the approach radius is set
            sig["reposition_target_radius"] = sorted([str(v), int(r)] for v, r in rad.items())
            ex = opts.get("reposition_radius_exempt_states")
            if ex:
                sig["reposition_radius_exempt_states"] = sorted([str(v), q] for v, qs in radius_exempt_states(ex).items()
                                                                for q in qs)
        return sig

    def roles_signature(self) -> Optional[List[List[Any]]]:
        """R7 (review 2026-10-21): the hub-capable set as a key component, ``[[loc, [roles]], ...]``
        sorted by location, when some location lacks the hub role ``C`` (``manhattan_dot``);
        ``None`` when every location allows every role (the older families), so their cut-pool
        signatures, superset-bound keys and ``config_md5`` stay byte-identical.  The template's
        role objects (and so the LP cuts and the superset bound) depend on this set."""
        if all("C" in r for r in self.roles_of.values()):
            return None
        return sorted([str(l), list(r)] for l, r in self.roles_of.items())

    def _maybe_relax(self, inst: Instance) -> Instance:
        return self._C.relax_end_targets(inst) if self.relaxed_targets else inst

    def derive(self, *, spec: Optional[SitingSpec] = None, variant: Optional[Dict[str, Any]] = None,
               relaxed_targets: Optional[bool] = None, selfish: Optional[Dict[str, Any]] = None,
               reposition: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> "LowerLevelEvaluator":
        """A sibling evaluator on the same scenarios with another ``spec`` / ``variant`` /
        target setting / follower-E settings (plan item A4 levers): same protocol, cache
        directory, wall budget and reposition mode; the in-memory cache dict is shared (keys
        differ by construction) and so are the all-candidates templates when the spec is
        unchanged.  R7 fixer (review of 2026-10-21): the template instance is built from the
        WHOLE spec (``spec.facility``: K, Cbar, M, sigma, P_kw, F, F_hub, R_end; ``_finish``:
        services, grid), so a sibling with another spec gets its own template dict; before,
        the dict was shared whenever ``sigma`` and ``max_pair_km`` were equal, and with eviction
        the spec that rebuilt a shared template depended on the order of eviction and rebuild.

        R7 re-plan change 5: ``params`` (extra Gurobi parameters, e.g. ``{'Method': 2}``) are
        merged into the sibling's ``params``, which enter every cache key: its rows are new rows
        by design (the model is the same, so every bound and incumbent stays valid for it).  The
        tier / params siblings cached on ``self`` are not inherited (they belong to ``self``)."""
        sp = self.spec if spec is None else spec
        ev = LowerLevelEvaluator.__new__(LowerLevelEvaluator)
        ev.__dict__.update(self.__dict__)
        for attr in ("_open_sites_sibling", "_params_siblings"):
            ev.__dict__.pop(attr, None)
        if params:
            ev.params = {**self.params, **dict(params)}
        ev.spec = sp
        ev.variant = _norm_variant(self.variant if variant is None else variant)
        ev.relaxed_targets = self.relaxed_targets if relaxed_targets is None else bool(relaxed_targets)
        ev.selfish = dict(self.selfish) if selfish is None else {**self.selfish, **selfish}
        if reposition is not None:              # R7 two-tier pricing: an 'open_sites' sibling
            if reposition not in REPOSITION_MODES:
                raise ValueError(f"reposition must be one of {REPOSITION_MODES}")
            ev.reposition = str(reposition)
        ev._templates = self._templates if sp.to_dict() == self.spec.to_dict() else OrderedDict()
        ev._pairs, ev._pair_order, ev._tpairs, ev._tpair_order = {}, [], {}, []
        ev._bound = None
        ev.bound_rows = []
        ev.new_rows = self.new_rows
        ev.n_solves = ev.n_cache_hits = ev.n_baseline_runs = ev.n_errors = 0
        ev.solver_time = ev.library_time = 0.0
        return ev

    def _layout_instance(self, layout: Layout, s: int) -> Instance:
        inst = layout_instance(self.scenarios[s], layout, self.spec)
        inst = self._maybe_relax(inst)
        if self.variant:
            inst = apply_variant(inst, self.variant, self.spec)
        return inst

    def layout_pair(self, layout: Layout, s: int) -> Tuple[Instance, ArcLibrary]:
        """Layout instance and its library of scenario ``s`` under the evaluator's
        ``reposition`` mode (sub-library of the template, or built per layout); the
        evaluator's ``variant`` (A4 levers) is applied to the instance."""
        key = (layout.key(), s)
        with self._lock:
            if key in self._pairs:
                return self._pairs[key]
        for l, r, _B, _C in layout.open:
            if r not in self.roles_of.get(l, ()):
                raise ValueError(f"role {r} is not allowed at {l} (hub-capable: {l in self.roles_of and 'C' in self.roles_of[l]})")
        inst = self._layout_instance(layout, s)
        t0 = time.perf_counter()
        if self.reposition == "open_sites":
            lib = build_arcs(inst, strict=False, **siting_pruning(inst, targets="open_sites", **self.pruning_overrides))
        else:
            _t_inst, t_lib = self.template(s)
            lib = subset_library(t_lib, inst, strict=False)
        with self._lock:
            self.library_time += time.perf_counter() - t0
            self._pairs[key] = (inst, lib)
            self._pair_order.append(key)
            while len(self._pair_order) > max(1, self.keep_libraries):
                old = self._pair_order.pop(0)
                self._pairs.pop(old, None)
        return inst, lib

    def template_pair(self, layout: Layout, s: int) -> Tuple[Instance, ArcLibrary]:
        """Layout instance and its library as a sub-library of the all-candidates template
        (the (A) / (B) convention), whatever the evaluator's ``reposition`` mode; used to
        certify the schedules of the integrated model on the layout instance."""
        if self.reposition != "open_sites":
            return self.layout_pair(layout, s)
        key = (layout.key(), s)
        with self._lock:
            if key in self._tpairs:
                return self._tpairs[key]
        _t_inst, t_lib = self.template(s)
        inst = self._layout_instance(layout, s)
        lib = subset_library(t_lib, inst, strict=False)
        with self._lock:
            self._tpairs[key] = (inst, lib)
            self._tpair_order.append(key)
            while len(self._tpair_order) > max(1, self.keep_libraries):
                self._tpairs.pop(self._tpair_order.pop(0), None)
        return inst, lib

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"# {msg}", flush=True)

    # --------------------------------------------------------------- cache
    def switches(self) -> Dict[str, Any]:
        return {"fixed_facilities": True, "no_transfers": False, "relaxed_targets": self.relaxed_targets,
                "q_res": int(self.scenarios[0].q_res),
                "rho": 0.0 if self.relaxed_targets else float(self.scenarios[0].meta.get("costs", {}).get("rho", self.scenarios[0].rho))}

    def cache_key(self, layout: Layout, s: int, policy: str) -> str:
        """MD5 of the canonical description of one lower-level evaluation (design 3.6):
        cache version, family, seed, demand hash, layout key, spec (roles, costs, timetable),
        reposition mode and pruning signature (per-layout targets in the ``open_sites`` mode),
        model switches, policy and Gurobi params (not the time limit, which is checked against
        the reuse rule instead)."""
        parts = {
            "version": CACHE_VERSION, "family": self.family, "seed": self.seeds[s], "demand_md5": self.demand_md5[s],
            "layout": layout.key(), "spec": self.spec.to_dict(), "reposition": self.reposition,
            "pruning": self.pruning_signature(s, layout),
            "switches": self.switches(), "policy": policy, "params": self.params,
            "cost_variant": self.scenarios[s].meta.get("cost_variant"),
        }
        # round-5 components, present only when used (keys of earlier rows are unchanged)
        # round 6: order prices (costs.pricing_cache_component: None for instances priced as
        # generated, so earlier keys are unchanged; the order-price MD5 for repriced scenarios)
        price_sig = pricing_cache_component(self.scenarios[s])
        if price_sig is not None:
            parts["order_prices"] = price_sig
        if self.aggregate and policy == "ilp":
            parts["formulation"] = "aggregated"
        if self.variant:
            parts["variant"] = self.variant
        if policy == "selfish":
            parts["selfish"] = self.selfish
        return _md5(parts)

    def _reusable(self, row: Dict[str, Any], time_limit: float) -> bool:
        st = row.get("status")
        if row.get("policy") == "baseline":
            return True
        if st in (INFEASIBLE_TERMINAL, INFEASIBLE_ILP, "INFEASIBLE", "INF_OR_UNBD"):
            return True
        if bd_stopped(row):
            # O2: a solve stopped by BestBdStop is a bound certificate, never a completed solve
            # (tested BEFORE the gap rule: a stopped row can have a MIP gap <= REUSE_GAP_TOL).  A
            # row solved with a BestBdStop that never fired follows the ordinary rules below.
            return False
        if self._C.reusable_ilp_row(st, row.get("gap")):
            return True
        # not solved: reuse only when the stored solve had at least the time now offered
        return float(row.get("time_limit") or 0.0) >= time_limit - 1e-9 and row.get("total") is not None

    def _store(self, row: Dict[str, Any], sched: Optional[Schedule], inst: Optional[Instance],
               lib: Optional[ArcLibrary]) -> Dict[str, Any]:
        row = dict(row)
        if sched is not None and inst is not None and lib is not None and self.sched_dir:
            path = os.path.join(self.sched_dir, row["key"] + ".json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(portable_schedule(sched, inst, lib), fh)
            row["schedule_path"] = path
        elif sched is not None and inst is not None and lib is not None:
            row["_portable"] = portable_schedule(sched, inst, lib)
        with self._lock:
            self.cache[row["key"]] = row
            self.new_rows.append(row)
            if self.index_path:
                self._C.append_jsonl(self.index_path, {k: v for k, v in row.items() if not k.startswith("_")})
        return row

    def load_portable(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Portable schedule of a cached row (``None`` when not stored)."""
        if row.get("_portable") is not None:
            return row["_portable"]
        path = row.get("schedule_path")
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return None

    def cached_schedule(self, layout: Layout, s: int, policy: str = "ilp"
                        ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """R7 re-plan change 4: ``(row, portable schedule)`` of this evaluator's cached cell
        ``(layout, s, policy)`` (its own cache key: reposition mode, params, ... included);
        ``(None, None)`` when the cell is not cached, ``(row, None)`` when the row has no stored
        schedule (no incumbent, infeasible, or a cache without a schedule directory)."""
        key = self.cache_key(layout, s, policy)
        with self._lock:
            row = self.cache.get(key)
        if row is None:
            return None, None
        return row, (self.load_portable(row) if row.get("feasible") else None)

    # ---------------------------------------------------------- evaluation
    def _base_row(self, layout: Layout, s: int, policy: str, key: str) -> Dict[str, Any]:
        return {
            "key": key, "layout_key": layout.key(), "layout": layout.to_json(), "n_open": layout.n_open,
            "investment": layout.investment(self.spec), "C_setup_allocated": layout.allocated_cost(self.spec),
            "family": self.family, "seed": self.seeds[s], "scenario": s, "p": self.p[s],
            "demand_md5": self.demand_md5[s], "policy": policy, "relaxed_targets": self.relaxed_targets,
            "cache_version": CACHE_VERSION, "threads": self.threads, "params": dict(self.params),
            "reposition": self.reposition, "cache_hit": False,
        }

    def _time_limit_for(self, layout: Layout) -> float:
        return self.time_limit_hub if layout.n_role("C") > 0 else self.time_limit

    def evaluate_scenario(self, layout: Layout, s: int, policy: str = "ilp",
                          warm: Optional[Dict[str, Any]] = None, force: bool = False,
                          best_bd_stop: Optional[float] = None,
                          time_limit: Optional[float] = None,
                          warm_source: Optional[str] = None) -> Dict[str, Any]:
        """One lower-level evaluation (cached): the ILP (``policy='ilp'``, facilities fixed,
        baseline / ``warm`` portable schedule as MIP start) or the baseline policy
        (``policy='baseline'``, R2.3 rules, (9)/(17)/(18) reported not enforced).  Returns the
        row (``status``, ``feasible``, ``total``, ``C_setup``, ``opex``, components, metrics,
        ``gap``, ``runtime_s``, ...).  Layouts on which a bike has no reachable terminal arc
        are :data:`INFEASIBLE_TERMINAL` (``opex = inf``) for both policies.  An exception in
        the evaluation gives a (recorded, uncached) :data:`ERROR` row with the message.

        Plan item O2 (``notes/o2_siting_bound_design.md`` 4.2): ``best_bd_stop`` passes Gurobi
        ``BestBdStop`` to the ILP (on the full objective (26), i.e. including ``C_setup``; status
        ``USER_OBJ_LIMIT`` when it fires; not part of the cache key; stored on the row);
        ``time_limit`` overrides the evaluator's time limit for this solve (escalation).  Rows
        keep Gurobi's ``bound`` also without an incumbent.  Both default to ``None`` (unchanged).

        R7 re-plan change 4: ``warm_source`` names where ``warm`` comes from (e.g.
        ``'open_sites'``: the cached schedule of the open-sites sibling of the same cell).  When
        set, the row records ``warm_source``, ``warm_materialised``, ``warm_check_ok`` and
        ``warm_obj`` (the materialise + ``check`` + ``cost`` result of that schedule on this
        evaluator's library); ``None`` keeps the rows as before."""
        if policy not in POLICIES:
            raise ValueError(f"policy must be one of {POLICIES} (got {policy!r})")
        key = self.cache_key(layout, s, policy)
        tl = self._time_limit_for(layout) if time_limit is None else float(time_limit)
        with self._lock:
            row = self.cache.get(key)
        if row is not None and not force and self._reusable(row, tl):
            with self._lock:
                self.n_cache_hits += 1
            out = dict(row)
            out["cache_hit"] = True
            return out
        if self.wall is not None and policy == "ilp":
            lim = self.wall.solve_limit(tl)
            if lim is None:
                row = self._base_row(layout, s, policy, key)
                row.update(status=SKIPPED_BUDGET, feasible=None, total=None, opex=None, C_setup=None,
                           skip_reason=WALL_EXHAUSTED)
                return row   # not cached
            tl = float(lim)
        try:
            return self._solve_scenario(layout, s, policy, key, tl, warm, best_bd_stop=best_bd_stop,
                                        warm_source=warm_source)
        except Exception as exc:  # noqa: BLE001 -- visible in the records (status ERROR), never a silent 'infeasible'
            row = self._base_row(layout, s, policy, key)
            row.update(status=ERROR, feasible=None, total=None, opex=None, C_setup=layout.allocated_cost(self.spec),
                       time_limit=tl, error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc()[-3000:])
            with self._lock:
                self.n_errors += 1
                self.new_rows.append(row)   # recorded by the experiment, not cached
            self._log(f"{layout.key()} s{s} {policy} ERROR {row['error']}")
            return row

    def _solve_scenario(self, layout: Layout, s: int, policy: str, key: str, tl: float,
                        warm: Optional[Dict[str, Any]], best_bd_stop: Optional[float] = None,
                        warm_source: Optional[str] = None) -> Dict[str, Any]:
        inst, lib = self.layout_pair(layout, s)
        row = self._base_row(layout, s, policy, key)
        row.update(n_arcs=len(lib), n_services=len(inst.services), n_facilities=len(inst.facilities),
                   time_limit=tl, infeasible_bikes=[str(b) for b in lib.infeasible_bikes])
        if lib.infeasible_bikes:
            row.update(status=INFEASIBLE_TERMINAL, feasible=False, total=None, C_setup=layout.allocated_cost(self.spec),
                       opex=None, runtime_s=0.0)
            return self._store(row, None, None, None)
        C = self._C
        t0 = time.perf_counter()
        if policy == "selfish":
            return self._solve_selfish(row, inst, lib, layout, t0)
        base = C.run_baseline_case(inst, lib)
        with self._lock:
            self.n_baseline_runs += 1
        if policy == "baseline":
            cst = base["cost"]
            row.update(status="POLICY", feasible=True, total=cst["total"], C_setup=cst["C_setup"],
                       opex=cst["total"] - cst["C_setup"], components=C.flatten_cost(cst),
                       check_families=base["families"], ok_modulo_report_only=base["ok_modulo_report_only"],
                       metrics=_flat_metrics(base["metrics"]), runtime_s=time.perf_counter() - t0,
                       pruning_flags=base["pruning_flags"], n_unservable=len(C.unservable_orders(inst, lib)))
            return self._store(row, base["schedule"], inst, lib)
        start, start_label = C.feasible_mip_start(inst, lib, base)
        start_obj = cost(inst, lib, start)["total"] if start is not None else None
        # R7 re-plan change 6: the rule start passed ``check`` when the default policy schedule
        # reported no family or a fallback variant was returned (only clean ones are)
        start_clean = start is not None and (start_label != "default" or not base.get("families"))
        if warm_source is not None:
            row.update(warm_source=str(warm_source), warm_available=warm is not None)
        if warm is not None:
            ws = materialise_schedule(warm, inst, lib)
            if warm_source is not None:
                row["warm_materialised"] = ws is not None
            if ws is not None:
                rep = check(inst, lib, ws)
                if warm_source is not None:
                    row.update(warm_check_ok=bool(rep["ok"]), warm_violations=int(rep.get("n_violations") or 0))
                if rep["ok"]:
                    wobj = cost(inst, lib, ws)["total"]
                    if warm_source is not None:
                        row["warm_obj"] = float(wobj)
                    if start_obj is None or wobj < start_obj - _TOL:
                        start, start_label, start_obj = ws, "warm_parent", wobj
                        start_clean = True
        extra_kw: Dict[str, Any] = {"aggregate": True} if self.aggregate else {}
        if not self.verify_checked_starts and start is not None and start_clean:
            extra_kw["verify_start"] = False                   # change 6: not part of the cache key
            row["verify_start"] = False
        run_params = dict(self.params)
        if best_bd_stop is not None and math.isfinite(float(best_bd_stop)):
            run_params["BestBdStop"] = float(best_bd_stop)       # O2: not part of the cache key
            row["best_bd_stop"] = float(best_bd_stop)
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads, label="ilp",
                             params=run_params, fixed_facilities=True, **extra_kw)
        if self.aggregate:
            row["formulation"] = "aggregated"
        with self._lock:
            self.n_solves += 1
            self.solver_time += float(rec["runtime"])
        row.update(runtime_s=rec["runtime"], build_time_s=rec["build_time"], n_binaries=rec["n_binaries"],
                   n_rows=rec["n_rows"], mip_start_variant=start_label, mip_start_obj=start_obj,
                   mip_start_accepted=rec["mip_start_accepted"], gurobi_status=rec["status"],
                   bound=rec["bound"], gap=rec["gap"], node_count=(rec["stats"] or {}).get("node_count"))
        if rec["schedule"] is None:
            st = INFEASIBLE_ILP if rec["status"] in ("INFEASIBLE", "INF_OR_UNBD") else NO_INCUMBENT
            row.update(status=st, feasible=False if st == INFEASIBLE_ILP else None, total=None,
                       C_setup=layout.allocated_cost(self.spec), opex=None)
            return self._store(row, None, None, None)
        cst = rec["cost"]
        row.update(status=rec["status"], feasible=True, total=cst["total"], C_setup=cst["C_setup"],
                   opex=cst["total"] - cst["C_setup"], components=C.flatten_cost(cst), check_ok=rec["ok"],
                   metrics=_flat_metrics(rec["metrics"]), baseline_total=base["cost"]["total"],
                   n_unservable=len(C.unservable_orders(inst, lib)))
        self._log(f"{layout.key()} s{s} {rec['status']} total {cst['total']:.3f} gap {rec['gap']} "
                  f"in {rec['runtime']:.0f} s (start {start_label})")
        return self._store(row, rec["schedule"], inst, lib)

    def _solve_selfish(self, row: Dict[str, Any], inst: Instance, lib: ArcLibrary, layout: Layout,
                       t0: float) -> Dict[str, Any]:
        """Follower E (plan item M4): the ``r5_selfish`` equilibrium (``baseline.
        run_selfish_equilibrium``) on the layout instance; the schedule is priced with
        ``evaluate.cost`` (26)-(32) and checked like every policy ((9), (17), (18) reported).
        On a relaxed-target copy the written DEMAND_AWARE reserve is kept (as for the baseline)."""
        from . import baseline as bl
        C = self._C
        over = dict(self.selfish.get("params") or {})
        written = (inst.meta.get("written_R_end")
                   if (inst.meta.get("relax_end_targets") or inst.meta.get("boundary_variant")) else None)
        if written and over.get("charge_reserve") is None:
            over["charge_reserve"] = {j: int(v) for j, v in written.items()}
        sched, flags, info = bl.run_selfish_equilibrium(inst, lib, over, max_iter=int(self.selfish["max_iter"]),
                                                        tol=float(self.selfish["tol"]),
                                                        averaging=str(self.selfish["averaging"]))
        self.n_baseline_runs += int(info["iterations"])
        cst = cost(inst, lib, sched)
        rep = check(inst, lib, sched)
        fams = C.family_counts(rep)
        row.update(status="POLICY", feasible=True, total=cst["total"], C_setup=cst["C_setup"],
                   opex=cst["total"] - cst["C_setup"], components=C.flatten_cost(cst), check_families=fams,
                   ok_modulo_report_only=all(f in C.BASELINE_REPORT_ONLY for f in fams),
                   metrics=_flat_metrics(metrics(inst, lib, sched)), runtime_s=time.perf_counter() - t0,
                   equilibrium={"iterations": info["iterations"], "converged": info["converged"],
                                "max_share_change": (info["max_share_change"][-1] if info["max_share_change"] else None),
                                "shares": {str(k): v for k, v in (info["shares"][-1] if info["shares"] else {}).items()},
                                "tol": info["tol"], "averaging": info["averaging"]},
                   n_unservable=len(C.unservable_orders(inst, lib)))
        return self._store(row, sched, inst, lib)

    def evaluate(self, layout: Layout, policy: str = "ilp", bound: Optional[Sequence[float]] = None,
                 best: Optional[float] = None, scenarios: Optional[Sequence[int]] = None,
                 warm: Optional[Dict[int, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """``V(lambda) = C_setup(lambda) + sum_s p_s OPEX_s(lambda)`` under ``policy``.

        With ``bound`` (per-scenario lower bounds on ``OPEX_s``, :meth:`superset_bound`) and an
        incumbent ``best`` the scenarios are solved in order and the evaluation stops as soon as
        the partial sum plus the remaining bounds reaches ``best`` (``status = PRUNED``,
        ``V = None``, ``lower_bound`` set).  An infeasible scenario gives ``V = inf``.  A
        :data:`SKIPPED_BUDGET` or :data:`ERROR` scenario gives ``V = None`` and that status
        (``error`` carries the message).
        """
        idx = list(range(self.n_scenarios)) if scenarios is None else list(scenarios)
        setup = layout.allocated_cost(self.spec)
        acc = setup
        rows: List[Dict[str, Any]] = []
        status = "OK"
        value: Optional[float] = None
        hits = solves = 0
        for pos, s in enumerate(idx):
            if bound is not None and best is not None and best < INF:
                rest = sum(self.p[t] * float(bound[t]) for t in idx[pos:])
                if acc + rest >= best - _TOL:
                    status = PRUNED
                    break
            row = self.evaluate_scenario(layout, s, policy, warm=(warm or {}).get(s))
            rows.append(row)
            hits += int(bool(row.get("cache_hit")))
            solves += int(not row.get("cache_hit"))
            if row["status"] == SKIPPED_BUDGET:
                status = SKIPPED_BUDGET
                break
            if row["status"] == ERROR:
                status = ERROR
                break
            if row["feasible"] is False:
                acc = INF
                status = row["status"]
                break
            if row["feasible"] is None:
                status = NO_INCUMBENT
                acc = INF
                break
            acc += self.p[s] * float(row["opex"])
        if status in ("OK",) or acc == INF:
            value = acc
        out = {
            "layout": layout, "layout_key": layout.key(), "policy": policy, "status": status,
            "feasible": (None if status in (PRUNED, SKIPPED_BUDGET, ERROR) else bool(value is not None and value < INF)),
            "error": next((r.get("error") for r in rows if r.get("status") == ERROR), None),
            "V": value, "C_setup": setup, "investment": layout.investment(self.spec),
            "opex_mean": (None if value is None or value == INF else value - setup),
            "opex": [r.get("opex") for r in rows], "statuses": [r["status"] for r in rows],
            "gaps": [r.get("gap") for r in rows], "rows": rows, "n_cache_hits": hits, "n_solves": solves,
            "lower_bound": (None if bound is None else acc + sum(self.p[t] * float(bound[t]) for t in idx[len(rows):])),
            "complete": status == "OK",
        }
        if rows and all(r.get("metrics") for r in rows):
            ms = [r["metrics"] for r in rows]
            out["served_share"] = sum(self.p[s] * m["served_share"] for s, m in zip(idx, ms)) / sum(self.p[s] for s in idx[:len(ms)])
            out["n_late"] = sum(m["n_late"] for m in ms) / len(ms)
            out["kwh_purchased"] = sum(m["kwh_purchased"] for m in ms) / len(ms)
            out["transfers_used"] = sum(m["transfers_used"] for m in ms) / len(ms)
            out["stockout_slots"] = sum(sum(m["stockout_slots"].values()) for m in ms) / len(ms)
        return out

    def value(self, layout: Layout, policy: str = "ilp") -> float:
        """``V(lambda)`` (``inf`` when infeasible) without pruning."""
        v = self.evaluate(layout, policy)["V"]
        return INF if v is None else v

    # ------------------------------------------------------------ bound
    def superset_bound_key_parts(self, method: str = "lp") -> Dict[str, Any]:
        """Components of the ``bound.json`` key of :meth:`superset_bound` (its MD5 is the key)."""
        key_parts = {"version": CACHE_VERSION, "family": self.family, "seeds": self.seeds, "demand": self.demand_md5,
                     "spec": self.spec.to_dict(), "pruning": self.pruning_signature(0), "params": self.params,
                     "method": method}
        if self.aggregate:                                      # O2: same LP value, smaller model
            key_parts["aggregate"] = True
        roles_sig = self.roles_signature()
        if roles_sig is not None:                               # R7: hub-capable set (absent when all are)
            key_parts["roles_of"] = roles_sig
        price_sigs = [pricing_cache_component(inst) for inst in self.scenarios]
        if any(p is not None for p in price_sigs):             # round 6: repriced scenarios
            key_parts["order_prices"] = price_sigs
        return key_parts

    def superset_bound(self, time_limit: Optional[float] = None, force: bool = False, method: str = "lp") -> List[float]:
        """Per-scenario lower bound ``LB_s <= OPEX_s(lambda)`` for EVERY layout, from the superset
        relaxation ``min C_elec + C_travel + C_orders + C_reb`` with all role objects of all
        candidates open, ``B_j, C_j`` free within (7)-(8), end targets relaxed ``rho = R_end = 0``
        and no budget: any schedule feasible for a layout is feasible there (superset of arcs,
        same sizes available, weaker targets), so the bound is valid under the written targets
        too.  ``method='lp'`` (default) takes the optimal value of the LP relaxation (valid, and
        the LP solves within the time limit where the MIP root of the all-open model does not);
        ``method='mip'`` takes Gurobi's ``ObjBound`` after a time-limited MIP solve (stronger
        when the root finishes).  A bound that could not be computed is 0.  Cached in
        ``cache_dir/bound.json``."""
        if self._bound is not None and not force:
            return self._bound
        tl = float(self.time_limit if time_limit is None else time_limit)
        path = os.path.join(self.cache_dir, "bound.json") if self.cache_dir else None
        key = _md5(self.superset_bound_key_parts(method))
        if path and os.path.exists(path) and not force:
            with open(path, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
            if saved.get("key") == key:
                self._bound = [float(b) for b in saved["bound"]]
                self.bound_rows = saved.get("rows", [])
                return self._bound
        from ebike_swap_sim import ilp
        import gurobipy as gp
        bounds: List[float] = []
        rows: List[Dict[str, Any]] = []
        for s in range(self.n_scenarios):
            _t_inst, t_lib = self.template(s)
            inst = all_candidates_instance(self.scenarios[s], self.spec, self.roles_of, open_all=True)
            inst = self._C.relax_end_targets(inst)
            lib = subset_library(t_lib, inst, strict=False)
            t0 = time.perf_counter()
            if lib.infeasible_bikes:
                bounds.append(0.0)
                rows.append({"scenario": s, "status": INFEASIBLE_TERMINAL, "bound": 0.0})
                continue
            agg_kw: Dict[str, Any] = {"aggregate": True} if self.aggregate else {}
            mdl = ilp.build_model(inst, lib, fixed_facilities=True, threads=self.threads, time_limit=tl,
                                  params=dict(self.params), **agg_kw)
            mdl.model.setObjective(mdl.objective - mdl.components["C_setup"], gp.GRB.MINIMIZE)
            m = mdl.model
            m.update()
            obj = None
            if method == "lp":
                lp = m.relax()
                lp.Params.OutputFlag = 0
                lp.Params.Threads = self.threads
                lp.Params.TimeLimit = tl
                lp.optimize()
                status = "LP_" + ilp.status_name(lp.Status)
                b = float(lp.ObjVal) if lp.Status == gp.GRB.OPTIMAL else 0.0
                runtime = float(lp.Runtime)
                n_bin = m.NumBinVars
                try:
                    lp.dispose()
                except Exception:  # noqa: BLE001
                    pass
            else:
                m.optimize()
                status = ilp.status_name(m.Status)
                try:
                    b = float(m.ObjBound)
                except gp.GurobiError:
                    b = 0.0
                obj = float(m.ObjVal) if m.SolCount > 0 else None
                runtime = float(m.Runtime)
                n_bin = m.NumBinVars
            if math.isinf(b) or math.isnan(b):
                b = 0.0
            b = max(0.0, b)
            rows.append({"scenario": s, "seed": self.seeds[s], "status": status, "method": method, "bound": b,
                         "obj": obj, "runtime_s": runtime, "n_arcs": len(lib), "n_binaries": n_bin,
                         "time_limit": tl, "wall_s": time.perf_counter() - t0})
            bounds.append(b)
            self.n_solves += 1
            self.solver_time += runtime
            try:
                m.dispose()
                mdl.env.dispose()
            except Exception:  # noqa: BLE001
                pass
            self._log(f"superset bound scenario {s}: {b:.3f} ({rows[-1]['status']}, {rows[-1]['runtime_s']:.0f} s)")
        self._bound = bounds
        self.bound_rows = rows
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"key": key, "bound": bounds, "rows": rows}, fh, indent=1)
        return bounds

    def stats(self) -> Dict[str, Any]:
        return {"n_solves": self.n_solves, "n_cache_hits": self.n_cache_hits, "n_baseline_runs": self.n_baseline_runs,
                "n_errors": self.n_errors, "solver_time_s": self.solver_time, "library_time_s": self.library_time,
                "n_cached_rows": len(self.cache), "reposition": self.reposition, "aggregate": self.aggregate,
                "variant": dict(self.variant)}


# ---------------------------------------------------------------------------
# access helpers ([U4])
# ---------------------------------------------------------------------------
def access_sets(candidates: Sequence[Candidate], scenarios: Sequence[Instance], D_blocks: int,
                zones: Optional[Sequence[str]] = None) -> Dict[str, List[str]]:
    """``Lambda(z) = {l : min over the zone's customer nodes of the grid distance to v_l <= D}``
    per demand zone ``z`` (NTA codes of the orders, ``meta['orders'][i]['zone_code']``), over
    the union of the scenarios (layout-independent).  Zones with no customer node are skipped;
    ``zones`` restricts the set."""
    cust: Dict[str, set] = {}
    for inst in scenarios:
        recs = inst.meta.get("orders") or []
        by_id = {o.id: o for o in inst.orders}
        for r in recs:
            code = r.get("zone_code")
            o = by_id.get(r.get("id"))
            if code is None or o is None:
                continue
            cust.setdefault(str(code), set()).add(o.d)
    out: Dict[str, List[str]] = {}
    for code in sorted(cust):
        if zones is not None and code not in zones:
            continue
        out[code] = [c.id for c in candidates if min(manhattan_blocks(c.node, v) for v in cust[code]) <= int(D_blocks)]
    return out


def layout_covers(layout: Layout, access: Dict[str, Sequence[str]]) -> bool:
    """[U4]: every zone has an open swap-capable object within reach."""
    return not uncovered_zones(layout, access)


def uncovered_zones(layout: Layout, access: Dict[str, Sequence[str]]) -> List[str]:
    """Zones of ``access`` without an open swap-capable object within reach (sorted); a zone
    whose access set is empty can never be covered and is always listed."""
    swap_locs = {l for l, r, _B, _C in layout.open if ROLE_SWAP[r]}
    return sorted(str(z) for z, locs in access.items() if not any(l in swap_locs for l in locs))


def zone_site_distances(layout: Layout, candidates: Sequence[Candidate], scenarios: Sequence[Instance]
                        ) -> Dict[str, Any]:
    """Grid distance (blocks) from every customer node to the nearest open swap-capable site:
    ``per_zone`` (mean / max per NTA), ``mean_blocks``, ``max_blocks``; ``inf`` without swap site."""
    node_of = {c.id: c.node for c in candidates}
    sites = [node_of[l] for l, r, _B, _C in layout.open if ROLE_SWAP[r]]
    per: Dict[str, List[int]] = {}
    allv: List[float] = []
    for inst in scenarios:
        by_id = {o.id: o for o in inst.orders}
        for r in inst.meta.get("orders") or []:
            o = by_id.get(r.get("id"))
            if o is None:
                continue
            d = min((manhattan_blocks(v, o.d) for v in sites), default=INF)
            per.setdefault(str(r.get("zone_code")), []).append(d)
            allv.append(d)
    return {"per_zone": {z: {"mean": sum(v) / len(v), "max": max(v), "min": min(v), "n": len(v)} for z, v in per.items()},
            "mean_blocks": (sum(allv) / len(allv)) if allv else None, "max_blocks": max(allv) if allv else None}


# ---------------------------------------------------------------------------
# (B) exhaustive
# ---------------------------------------------------------------------------
def enumerate_layouts(candidates: Sequence[Candidate], grid: Any, budget: float, spec: SitingSpec,
                      k_range: Sequence[int] = (1, 2), require_swap: bool = True,
                      access: Optional[Dict[str, Sequence[str]]] = None,
                      max_role_count: Optional[Dict[str, int]] = None, s_needs_charge: bool = False) -> List[Layout]:
    """All layouts with ``k in k_range`` open locations, one option ``(role, B, C)`` per open
    location from ``grid`` (a list shared by all locations, or ``{loc: list}``), investment
    within ``budget``, at least one swap-capable object (C-only layouts violate (9)), with
    ``access`` [U4], with ``max_role_count`` (``{role: n}``, e.g. at most one hub) that cap and,
    with ``s_needs_charge``, swap-only sites only next to a charge-capable object
    (:func:`sites_nyc.layout_admissible`); sorted by investment then key (deterministic)."""
    ids = [c.id for c in candidates]
    out: List[Layout] = []
    for k in k_range:
        for subset in itertools.combinations(ids, int(k)):
            menus = [list(grid[l] if isinstance(grid, dict) else grid) for l in subset]
            for choice in itertools.product(*menus):
                lay = Layout.of([(l, r, B, C) for l, (r, B, C) in zip(subset, choice)])
                if not lay.valid(spec) or lay.investment(spec) > budget + 1e-9:
                    continue
                if not layout_admissible(lay, s_needs_charge=s_needs_charge, require_swap=require_swap):
                    continue
                if access is not None and not layout_covers(lay, access):
                    continue
                if max_role_count and any(lay.n_role(r) > n for r, n in max_role_count.items()):
                    continue
                out.append(lay)
    out.sort(key=lambda l: (l.investment(spec), l.key()))
    return out


def exhaustive(evaluator: LowerLevelEvaluator, candidates: Sequence[Candidate], grid: Any, budget: float,
               k_range: Sequence[int] = (1, 2), bound: Optional[Sequence[float]] = None, require_swap: bool = True,
               access: Optional[Dict[str, Sequence[str]]] = None, max_layouts: Optional[int] = None,
               on_row: Optional[Callable[[Dict[str, Any]], None]] = None, policy: str = "ilp",
               best: Optional[float] = None, screen: bool = False,
               max_role_count: Optional[Dict[str, int]] = None, s_needs_charge: bool = False) -> Dict[str, Any]:
    """Algorithm (B): evaluate every layout of :func:`enumerate_layouts` with the lower-level
    ``policy``, skipping layouts whose bound ``C_setup + sum_s p_s LB_s`` reaches the incumbent
    (``SKIPPED_BOUND``) and pruning scenario by scenario (``PRUNED``).  With ``screen`` the
    layouts are ordered by their baseline value first (cheap, better incumbents early).
    Returns ``best_layout``, ``best_value``, ``rows`` (one per layout: ``status``, ``V``,
    ``investment``, ``lower_bound``, ...), ``coverage`` and the evaluator stats."""
    layouts = enumerate_layouts(candidates, grid, budget, evaluator.spec, k_range, require_swap, access, max_role_count,
                                s_needs_charge=s_needs_charge)
    if max_layouts is not None:
        layouts = layouts[:int(max_layouts)]
    if screen and policy == "ilp":
        layouts.sort(key=lambda l: (evaluator.value(l, "baseline"), l.investment(evaluator.spec), l.key()))
    best_v = INF if best is None else float(best)
    best_lay: Optional[Layout] = None
    rows: List[Dict[str, Any]] = []
    cov = {"n_layouts": len(layouts), "solved": 0, "pruned": 0, "skipped_bound": 0, "infeasible": 0,
           "skipped_budget": 0, "no_incumbent": 0, "error": 0}
    for lay in layouts:
        setup = lay.allocated_cost(evaluator.spec)
        lb = setup + (sum(p * float(b) for p, b in zip(evaluator.p, bound)) if bound is not None else 0.0)
        row: Dict[str, Any] = {"layout_key": lay.key(), "layout": lay.to_json(), "n_open": lay.n_open,
                               "investment": lay.investment(evaluator.spec), "C_setup": setup, "policy": policy,
                               "lower_bound": lb}
        if bound is not None and lb >= best_v - _TOL:
            row.update(status=SKIPPED_BOUND, V=None, feasible=None)
            cov["skipped_bound"] += 1
        else:
            ev = evaluator.evaluate(lay, policy, bound=bound, best=best_v)
            row.update(status=ev["status"], V=ev["V"], feasible=ev["feasible"], opex=ev["opex"],
                       statuses=ev["statuses"], gaps=ev["gaps"], lower_bound=ev["lower_bound"],
                       n_cache_hits=ev["n_cache_hits"], n_solves=ev["n_solves"], served_share=ev.get("served_share"),
                       error=ev.get("error"))
            if ev["status"] == PRUNED:
                cov["pruned"] += 1
            elif ev["status"] == SKIPPED_BUDGET:
                cov["skipped_budget"] += 1
            elif ev["status"] == ERROR:
                cov["error"] += 1
            elif ev["status"] == NO_INCUMBENT:
                cov["no_incumbent"] += 1
            elif ev["V"] == INF:
                cov["infeasible"] += 1
            else:
                cov["solved"] += 1
                if ev["V"] < best_v - _TOL:
                    best_v, best_lay = ev["V"], lay
        row["is_best"] = False
        rows.append(row)
        if on_row is not None:
            on_row(row)
    for r in rows:
        r["is_best"] = best_lay is not None and r["layout_key"] == best_lay.key()
    cov["full_coverage"] = cov["skipped_budget"] == 0 and cov["no_incumbent"] == 0 and cov["error"] == 0
    return {"best_layout": best_lay, "best_value": (None if best_lay is None else best_v), "rows": rows,
            "coverage": cov, "evaluator": evaluator.stats()}


# ---------------------------------------------------------------------------
# (C) greedy forward selection + local search
# ---------------------------------------------------------------------------
def _screen(evaluator: LowerLevelEvaluator, layouts: Sequence[Layout], k: int,
            by_group: Optional[Callable[[Layout], Any]] = None,
            score: Optional[Callable[[Layout], float]] = None) -> List[Tuple[float, Layout]]:
    """Baseline values of ``layouts`` (cheap), the best ``k`` first (infeasible ones last).
    With ``by_group`` (layout -> key, e.g. the role of the item a move adds) the best ``k`` of
    EVERY group are kept: the baseline policy ranks roles against each other poorly (it serves
    orders at a loss where the ILP drops them, so on the first E9 attempt the five best
    baseline values were all one-spare swap-only sites although the ILP valued them at
    1398 vs 867 for a co-located site), hence the screen must never decide between roles.
    ``score`` (plan item O2: the LP screen of ``benders.LPScreen``) replaces the baseline value."""
    scored = [((score(l) if score is not None else evaluator.value(l, "baseline")), l) for l in layouts]
    scored.sort(key=lambda t: (t[0], t[1].key()))
    if by_group is None:
        return scored[:max(1, int(k))]
    groups: Dict[Any, List[Tuple[float, Layout]]] = {}
    for bv, l in scored:
        groups.setdefault(by_group(l), []).append((bv, l))
    out: List[Tuple[float, Layout]] = []
    for g in sorted(groups, key=str):
        out.extend(groups[g][:max(1, int(k))])
    return out


def _added_role(parent: Layout, child: Layout) -> str:
    """Role of the item ``child`` has and ``parent`` has not (an 'add' move); ``'?'`` otherwise."""
    for l, r, _B, _C in child.open:
        if parent.item(l) is None:
            return r
    return "?"


def greedy_local_search(evaluator: LowerLevelEvaluator, candidates: Sequence[Candidate], budget: float,
                        size_menu: Dict[str, Sequence[Tuple[int, int]]] = DEFAULT_SIZE_MENU,
                        roles: Sequence[str] = ROLES, k_screen: int = 5, max_passes: int = 3,
                        moves: Sequence[str] = ("add", "drop", "swap", "role", "size", "exchange"),
                        start: Optional[Layout] = None,
                        access: Optional[Dict[str, Sequence[str]]] = None, budget_levels: Optional[Sequence[float]] = None,
                        on_step: Optional[Callable[[Dict[str, Any]], None]] = None, screen: Any = True,
                        local_search: bool = True, min_served_share: float = 0.5, s_needs_charge: bool = False,
                        access_mode: str = "repair", policy: str = "ilp") -> Dict[str, Any]:
    """Algorithm (C): best-singleton start, forward selection, local search per budget level.

    ``policy`` is the lower level that prices every move (default ``'ilp'``, the written
    operations ILP).  ``'selfish'`` (plan item M4, follower E: the ``r5_selfish`` equilibrium)
    or ``'baseline'`` give *policy-aware siting*: the layout that is best when the riders choose
    stations self-interestedly (or follow the R2.3 rule) instead of being dispatched by the
    system optimum; the search rules below are unchanged.

    1. **Start = the best singleton by V.**  Every admissible singleton ``(l, r, B, C)`` of the
       size menu (:func:`sites_nyc.layout_admissible` with ``s_needs_charge``; C-only never) is
       priced by the lower-level ILP on all scenarios -- with ``screen`` only the ``k_screen``
       best by baseline value PER ROLE (the screen never decides between roles) -- and the
       feasible singleton with the lowest ``V`` that serves at least ``min_served_share`` of the
       orders starts the search.  If no screened singleton is usable, every remaining admissible
       singleton is priced (exhaustive singletons), so that "no feasible layout" is reported only
       when no singleton is feasible with enough service.
    2. **Forward selection** up to ``max(budget_levels)``: add one item from the menu per step,
       the ``k_screen`` best baseline moves per added role priced by the ILP, the usable move with
       the largest gain per investment dollar accepted while ``V`` decreases.
    3. **Per budget level**: the best layout of the frontier (plus the best singleton) within the
       level, then a first-improvement local search over ``moves`` (``add`` / ``drop`` / ``swap``
       location / ``role`` flip / ``size`` +-1 / ``exchange`` the role and size of two open
       locations), at most ``max_passes`` passes.

    A priced move is **usable** only when its lower level is feasible on every scenario and its
    expected served share is at least ``min_served_share``; infeasible, :data:`LOW_SERVICE`,
    :data:`NO_INCUMBENT`, :data:`ERROR` and :data:`SKIPPED_BUDGET` moves are recorded with that
    status (``history``) and discarded, and ``SKIPPED_BUDGET`` (wall budget exhausted) stops the
    search instead of being mistaken for infeasibility (the first E9 attempt).  Values are
    lower-level ILP values on all scenarios (the baseline screening never decides acceptance).

    ``access`` [U4] with ``access_mode='repair'`` (default) never restricts the search: after the
    local search of a budget level, if zones stay uncovered, swap-capable items that cover the
    most uncovered zones are added / flipped within the budget (usable moves only) and the local
    search is repeated without losing coverage; the zones still uncovered are *reported*
    (``uncovered_zones``), never enforced.  ``'report'`` only reports, ``'enforce'`` restricts
    every admissible layout to covering ones (the first-attempt behaviour, which has no
    admissible singleton on 12 zones).

    Returns ``{'per_budget': {budget: {'layout', 'value', 'status', 'history', 'uncovered_zones',
    'search_complete', ...}}, 'frontier', 'best_singleton', 'history', 'class_counts',
    'wall_exhausted', 'evaluator'}``; ``status`` is ``'OK'``, :data:`WALL_EXHAUSTED` or
    :data:`NO_FEASIBLE_LAYOUT` (with ``reasons`` = the status counts of the priced layouts).

    ``screen``: ``True`` / ``'baseline'`` (default, unchanged) ranks moves by the baseline
    policy value, ``False`` prices every move, and a callable ``layout -> score`` (plan item O2:
    ``benders.LPScreen``, cut envelope then LP recourse value) replaces the baseline value; the
    ``k_screen`` best per added role are kept as before."""
    if access_mode not in ("repair", "report", "enforce"):
        raise ValueError(f"access_mode must be repair, report or enforce (got {access_mode!r})")
    score_fn: Optional[Callable[[Layout], float]] = screen if callable(screen) else None
    if isinstance(screen, str):
        if screen != "baseline":
            raise ValueError("screen must be True / False / 'baseline' or a callable (e.g. benders.LPScreen)")
        screen = True
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES} (got {policy!r})")
    spec = evaluator.spec
    levels = sorted(float(b) for b in (budget_levels or [budget]))
    bmax = max(levels)
    grid = option_grid(size_menu, roles)
    ids = [c.id for c in candidates]
    history: List[Dict[str, Any]] = []
    priced: Dict[str, Tuple[str, float, Dict[str, Any]]] = {}
    class_counts: Dict[str, int] = {}
    exhausted = [False]
    min_share = float(min_served_share)

    def uncovered(l: Layout) -> List[str]:
        return [] if access is None else uncovered_zones(l, access)

    def n_coverable_uncovered(l: Layout) -> int:
        return 0 if access is None else sum(1 for z in uncovered(l) if access.get(z))

    def admissible(l: Layout, b: float) -> bool:
        if not (l.valid(spec) and l.investment(spec) <= b + 1e-9):
            return False
        if not layout_admissible(l, s_needs_charge=s_needs_charge, require_swap=True):
            return False
        if access is not None and access_mode == "enforce" and not layout_covers(l, access):
            return False
        return True

    def price(l: Layout) -> Tuple[str, float, Dict[str, Any]]:
        """``(class, V, evaluation)``: class ``'OK'`` (usable), :data:`LOW_SERVICE` (feasible,
        discarded), :data:`SKIPPED_BUDGET`, :data:`ERROR` or the infeasibility status."""
        if l.key() in priced:
            return priced[l.key()]
        ev = evaluator.evaluate(l, policy)
        st, v = ev["status"], ev["V"]
        if st == SKIPPED_BUDGET:
            cls, val = SKIPPED_BUDGET, INF
            exhausted[0] = True
        elif st == ERROR:
            cls, val = ERROR, INF
        elif v is None or v == INF:
            cls, val = (st if st not in ("OK",) else INFEASIBLE_ILP), INF
        elif ev.get("served_share") is not None and ev["served_share"] < min_share - 1e-9:
            cls, val = LOW_SERVICE, float(v)
        else:
            cls, val = "OK", float(v)
        if cls != SKIPPED_BUDGET:
            priced[l.key()] = (cls, val, ev)
        class_counts[cls] = class_counts.get(cls, 0) + 1
        return cls, val, ev

    def record(step: str, l: Layout, cls: str, v: float, ev: Optional[Dict[str, Any]] = None,
               extra: Optional[Dict[str, Any]] = None) -> None:
        rec: Dict[str, Any] = {"step": step, "layout_key": l.key(), "layout": l.to_json(), "status": cls,
                               "usable": cls == "OK", "V": (None if v == INF else v), "investment": l.investment(spec)}
        if ev is not None:
            rec["served_share"] = ev.get("served_share")
            rec["statuses"] = ev.get("statuses")
            if ev.get("error"):
                rec["error"] = ev["error"]
        if access is not None:
            rec["uncovered_zones"] = uncovered(l)
        rec.update(extra or {})
        history.append(rec)
        if on_step is not None:
            on_step(rec)

    # 1. start: the best singleton by V --------------------------------------------------------
    frontier: List[Tuple[Layout, float]] = []
    best_single: Optional[Tuple[Layout, float]] = None
    lam: Optional[Layout] = None
    v_lam = INF
    if start is not None and start.n_open:
        cls, v, ev = price(start)
        record("start", start, cls, v, ev)
        if cls == "OK":
            lam, v_lam = start, v
            frontier.append((lam, v_lam))
    if lam is None:
        singles = [Layout.of([(l, r, B, C)]) for l in ids for (r, B, C) in grid]
        singles = [x for x in singles if admissible(x, bmax)]
        pool = (_screen(evaluator, singles, k_screen, by_group=lambda l: l.open[0][1], score=score_fn) if screen
                else [(INF, x) for x in singles])
        usable: List[Tuple[Layout, float]] = []
        seen_keys = set()
        for bv, x in pool:
            if exhausted[0]:
                break
            cls, v, ev = price(x)
            seen_keys.add(x.key())
            record("singleton", x, cls, v, ev, {"baseline_V": (None if bv == INF else bv), "screened": bool(screen)})
            if cls == "OK":
                usable.append((x, v))
        if not usable and not exhausted[0]:
            # fallback: price every remaining admissible singleton (exhaustive singletons)
            for x in singles:
                if x.key() in seen_keys or exhausted[0]:
                    continue
                cls, v, ev = price(x)
                record("singleton_fallback", x, cls, v, ev)
                if cls == "OK":
                    usable.append((x, v))
        if usable:
            best_single = min(usable, key=lambda t: (t[1], t[0].key()))
            lam, v_lam = best_single
            frontier.append(best_single)
            record("start", lam, "OK", v_lam, None, {"n_singletons_priced": len(seen_keys) if screen else len(singles)})
    elif lam.n_open == 1:
        best_single = (lam, v_lam)

    # 2. forward selection -------------------------------------------------------------------------
    while lam is not None and not exhausted[0]:
        adds = [lam.add((l, r, B, C)) for l in ids if lam.item(l) is None for (r, B, C) in grid]
        adds = [a for a in adds if admissible(a, bmax)]
        if not adds:
            record("forward_stop", lam, "OK", v_lam, None, {"reason": "no admissible addition within the budget"})
            break
        top = (_screen(evaluator, adds, k_screen, by_group=lambda a, p=lam: _added_role(p, a), score=score_fn) if screen
               else [(INF, a) for a in adds])
        scored: List[Tuple[float, float, Layout]] = []
        for bv, a in top:
            cls, va, ev = price(a)
            inv_a = a.investment(spec) - lam.investment(spec)
            gain = (v_lam - va) / max(inv_a, 1.0) if cls == "OK" else None
            record("forward_candidate", a, cls, va, ev, {"parent": lam.key(), "baseline_V": (None if bv == INF else bv),
                                                         "gain_per_usd": gain})
            if cls == "OK":
                scored.append((gain, va, a))
        if not scored:
            record("forward_stop", lam, "OK", v_lam, None,
                   {"reason": WALL_EXHAUSTED if exhausted[0] else "no usable addition (all infeasible / low service)"})
            break
        scored.sort(key=lambda t: (-t[0], t[2].key()))
        gain, va, a = scored[0]
        if va >= v_lam - _TOL:
            record("forward_stop", lam, "OK", v_lam, None, {"reason": "no improving addition", "best_rejected": a.key(),
                                                            "rejected_V": va})
            break
        lam, v_lam = a, va
        frontier.append((lam, v_lam))
        record("forward_accept", lam, "OK", v_lam, None, {"gain_per_usd": gain})

    # 3. per budget level: local search (+ access repair) ------------------------------------------
    def neighbours(lam_b: Layout, b: float, allowed: Sequence[str], cover_floor: Optional[int]) -> List[Layout]:
        neigh: List[Layout] = []
        for it in lam_b.open:
            l, r, B, C = it
            if "drop" in allowed and lam_b.n_open > 1:
                neigh.append(lam_b.drop(l))
            if "swap" in allowed:
                for l2 in ids:
                    if lam_b.item(l2) is None:
                        neigh.append(lam_b.replace(l, (l2, r, B, C)))
            if "role" in allowed:
                for r2 in roles:
                    if r2 == r:
                        continue
                    for (B2, C2) in size_menu.get(r2, []):
                        neigh.append(lam_b.replace(l, (l, r2, B2, C2)))
            if "size" in allowed:
                for dB, dC in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    B2, C2 = B + dB, C + dC
                    if spec.valid_sizes(r, B2, C2) and (B2 >= 1 or not ROLE_SWAP[r]):
                        neigh.append(lam_b.replace(l, (l, r, B2, C2)))
        if "exchange" in allowed and lam_b.n_open > 1:
            for it1, it2 in itertools.combinations(lam_b.open, 2):
                l1, l2 = it1[0], it2[0]
                neigh.append(Layout.of([it for it in lam_b.open if it[0] not in (l1, l2)]
                                       + [(l1,) + it2[1:], (l2,) + it1[1:]]))
        if "add" in allowed:
            for l2 in ids:
                if lam_b.item(l2) is None:
                    for (r2, B2, C2) in grid:
                        neigh.append(lam_b.add((l2, r2, B2, C2)))
        seen = set()
        uniq: List[Layout] = []
        for n in neigh:
            if n.key() in seen or n.key() == lam_b.key() or not admissible(n, b):
                continue
            if cover_floor is not None and n_coverable_uncovered(n) > cover_floor:
                continue
            seen.add(n.key())
            uniq.append(n)
        return uniq

    def local(lam_b: Layout, v_b: float, b: float, hist: List[Dict[str, Any]], cover_floor: Optional[int],
              tag: str) -> Tuple[Layout, float]:
        passes = 0
        improved = True
        while improved and passes < max_passes and not exhausted[0]:
            improved = False
            passes += 1
            uniq = neighbours(lam_b, b, moves, cover_floor)
            if not uniq:
                break
            top = _screen(evaluator, uniq, k_screen, score=score_fn) if screen else [(INF, n) for n in uniq]
            for _bv, n in top:
                cls, vn, ev = price(n)
                hist.append({"step": f"{tag}_pass{passes}", "layout_key": n.key(), "status": cls, "V": (None if vn == INF else vn),
                             "served_share": (ev or {}).get("served_share"), "baseline_V": (None if _bv == INF else _bv)})
                if cls == "OK" and vn < v_b - _TOL:
                    lam_b, v_b = n, vn
                    hist.append({"step": f"{tag}_accept{passes}", "layout_key": n.key(), "V": vn})
                    improved = True
                    break
        return lam_b, v_b

    def repair(lam_b: Layout, v_b: float, b: float, hist: List[Dict[str, Any]]) -> Tuple[Layout, float, bool]:
        """Add / flip swap-capable items that cover the most still-coverable uncovered zones."""
        changed = False
        while not exhausted[0]:
            n_unc = n_coverable_uncovered(lam_b)
            if n_unc == 0:
                break
            cands = [n for n in neighbours(lam_b, b, ("add", "role"), None) if n_coverable_uncovered(n) < n_unc]
            if not cands:
                hist.append({"step": "repair_stop", "layout_key": lam_b.key(), "reason": "no affordable covering move",
                             "uncovered_zones": uncovered(lam_b)})
                break
            ranked = _screen(evaluator, cands, len(cands), score=score_fn) if screen else [(INF, n) for n in cands]
            ranked.sort(key=lambda t: (n_coverable_uncovered(t[1]), t[0], t[1].investment(spec), t[1].key()))
            accepted = None
            for _bv, n in ranked[:max(1, int(k_screen))]:
                cls, vn, ev = price(n)
                hist.append({"step": "repair_candidate", "layout_key": n.key(), "status": cls, "V": (None if vn == INF else vn),
                             "served_share": (ev or {}).get("served_share"), "uncovered_zones": uncovered(n)})
                if cls == "OK" and (accepted is None or (n_coverable_uncovered(n), vn) < (n_coverable_uncovered(accepted[0]), accepted[1])):
                    accepted = (n, vn)
            if accepted is None:
                hist.append({"step": "repair_stop", "layout_key": lam_b.key(), "reason": "no usable covering move",
                             "uncovered_zones": uncovered(lam_b)})
                break
            lam_b, v_b = accepted
            changed = True
            hist.append({"step": "repair_accept", "layout_key": lam_b.key(), "V": v_b, "uncovered_zones": uncovered(lam_b)})
        return lam_b, v_b, changed

    per_budget: Dict[float, Dict[str, Any]] = {}
    for b in levels:
        cand = [(l, v) for l, v in frontier if l.investment(spec) <= b + 1e-9]
        if best_single is not None and best_single[0].investment(spec) <= b + 1e-9:
            cand.append(best_single)
        if not cand:
            status = WALL_EXHAUSTED if exhausted[0] else NO_FEASIBLE_LAYOUT
            per_budget[b] = {"layout": None, "value": None, "history": [], "status": status,
                             "reasons": dict(class_counts), "search_complete": not exhausted[0]}
            record("budget_result", Layout(), status, INF, None, {"budget": b, "reasons": dict(class_counts)})
            continue
        lam_b, v_b = min(cand, key=lambda t: (t[1], t[0].key()))
        hist_b: List[Dict[str, Any]] = [{"step": "start", "layout_key": lam_b.key(), "V": v_b}]
        if local_search:
            lam_b, v_b = local(lam_b, v_b, b, hist_b, None, "ls")
        repaired = False
        if access is not None and access_mode == "repair" and n_coverable_uncovered(lam_b) > 0:
            lam_b, v_b, repaired = repair(lam_b, v_b, b, hist_b)
            if repaired and local_search:
                lam_b, v_b = local(lam_b, v_b, b, hist_b, n_coverable_uncovered(lam_b), "ls_covering")
        per_budget[b] = {"layout": lam_b, "value": v_b, "history": hist_b, "status": "OK",
                         "investment": lam_b.investment(spec), "uncovered_zones": uncovered(lam_b),
                         "access_repaired": repaired, "search_complete": not exhausted[0],
                         "served_share": (priced.get(lam_b.key(), (None, None, {}))[2] or {}).get("served_share")}
        record("local_search_result", lam_b, "OK", v_b, None, {"budget": b, "search_complete": not exhausted[0]})
    return {"per_budget": per_budget, "frontier": [(l.key(), v) for l, v in frontier],
            "best_singleton": (None if best_single is None else (best_single[0].key(), best_single[1])),
            "history": history, "class_counts": dict(class_counts), "wall_exhausted": exhausted[0],
            "evaluator": evaluator.stats(), "policy": policy}


# ---------------------------------------------------------------------------
# (D) deck heuristic
# ---------------------------------------------------------------------------
def deck_heuristic(evaluator: LowerLevelEvaluator, candidates: Sequence[Candidate], budget: float,
                   iterations: int = 3, policy: str = "baseline", radius_blocks: int = 7) -> Dict[str, Any]:
    """Algorithm (D), the proposal deck's planner: open every candidate as ``SC`` (``B 1, C 1``),
    run the operating ``policy`` (the baseline, milliseconds) on every scenario, rank locations
    by the expected number of swaps served there, keep the ``k`` affordable ones (``k`` = max
    sites with ``k (Fhat + bhat + chat) <= budget``), replace a kept site that served no swap
    by the closed candidate with most orders released within ``radius_blocks`` (~1 km), size
    the kept sites (extra spares in proportion to demand, then one extra charger per site)
    within the budget, and iterate.  Never calls the lower-level ILP during the search; the
    result is priced afterwards by the caller (E9.4 / E9.5).  Returns the final layout, the
    per-iteration log and the demand proxies."""
    spec = evaluator.spec
    ids = [c.id for c in candidates]
    unit = spec.Fhat + spec.bhat + spec.chat
    k = int(math.floor((budget + 1e-9) / unit))
    if k < 1:
        return {"layout": None, "k": 0, "log": [], "status": "budget below one site"}
    # order counts within the radius (demand proxy for the 'unused station' rule)
    nearby: Dict[str, float] = {}
    node_of = {c.id: c.node for c in candidates}
    for cid in ids:
        cnt = 0.0
        for s, inst in enumerate(evaluator.scenarios):
            cnt += evaluator.p[s] * sum(1 for o in inst.orders if manhattan_blocks(node_of[cid], o.o) <= radius_blocks)
        nearby[cid] = cnt
    lay = Layout.of([(l, "SC", 1, 1) for l in ids])
    log: List[Dict[str, Any]] = []
    keep = list(ids)
    for it in range(1, int(iterations) + 1):
        ev = evaluator.evaluate(lay, policy)
        demand: Dict[str, float] = {l: 0.0 for l in ids}
        if ev["rows"] and all(r.get("metrics") for r in ev["rows"]):
            for s, row in zip(range(evaluator.n_scenarios), ev["rows"]):
                for fid, n in row["metrics"]["swaps_per_facility"].items():
                    loc = split_facility_id(fid)[0]
                    demand[loc] = demand.get(loc, 0.0) + evaluator.p[s] * float(n)
        open_locs = list(lay.locations())
        ranked = sorted(open_locs, key=lambda l: (-demand.get(l, 0.0), ids.index(l)))
        keep = ranked[:k]
        replaced: List[Tuple[str, str]] = []
        if it > 1:
            closed = [l for l in ids if l not in keep]
            for i, l in enumerate(list(keep)):
                if demand.get(l, 0.0) <= 0.0 and closed:
                    best = max(closed, key=lambda c: (nearby[c], -ids.index(c)))
                    closed.remove(best)
                    keep[i] = best
                    replaced.append((l, best))
        # sizes: spares in proportion to demand, then chargers one per site
        rem = budget - k * unit
        extra_B = {l: 0 for l in keep}
        n_sp = int(math.floor(rem / spec.bhat + 1e-9)) if spec.bhat > 0 else 0
        tot = sum(max(demand.get(l, 0.0), 0.0) for l in keep)
        if n_sp > 0 and tot > 0:
            shares = {l: n_sp * max(demand.get(l, 0.0), 0.0) / tot for l in keep}
            for l in keep:
                extra_B[l] = min(int(math.floor(shares[l])), spec.K - 1)
            left = n_sp - sum(extra_B.values())
            for l in sorted(keep, key=lambda l: -(shares[l] - math.floor(shares[l]))):
                if left <= 0:
                    break
                if extra_B[l] < spec.K - 1:
                    extra_B[l] += 1
                    left -= 1
        rem -= spec.bhat * sum(extra_B.values())
        extra_C = {l: 0 for l in keep}
        for l in sorted(keep, key=lambda l: (-demand.get(l, 0.0), ids.index(l))):
            if rem >= spec.chat - 1e-9 and 1 + extra_C[l] < spec.c_max("SC"):
                extra_C[l] += 1
                rem -= spec.chat
        new = Layout.of([(l, "SC", 1 + extra_B[l], 1 + extra_C[l]) for l in keep])
        log.append({"iteration": it, "evaluated": lay.key(), "policy_V": (None if ev["V"] in (None, INF) else ev["V"]),
                    "demand": {l: demand.get(l, 0.0) for l in open_locs}, "kept": list(keep), "replaced": replaced,
                    "next": new.key(), "investment": new.investment(spec)})
        if new.key() == lay.key():
            break
        lay = new
    return {"layout": lay, "k": k, "log": log, "nearby_orders": nearby, "status": "OK"}


# ---------------------------------------------------------------------------
# (A) integrated two-stage stochastic ILP
# ---------------------------------------------------------------------------
def integrated_stochastic_ilp(evaluator: LowerLevelEvaluator, candidates: Sequence[Candidate], budget: float, *,
                              roles: Sequence[str] = ROLES,
                              size_bounds: Optional[Dict[str, Tuple[int, int, int, int]]] = None,
                              time_limit: float = 600.0, threads: int = 3, params: Optional[Dict[str, Any]] = None,
                              access: Optional[Dict[str, Sequence[str]]] = None, zeta_exp: Optional[float] = None,
                              mip_start_layout: Optional[Layout] = None, certify: bool = True, output: bool = False,
                              label: str = "integrated", max_role_count: Optional[Dict[str, int]] = None,
                              s_needs_charge: bool = False, aggregate: Optional[bool] = None) -> Dict[str, Any]:
    """Algorithm (A): ONE Gurobi model with shared facility variables ``y_j, B_j, C_j`` for
    every role object ``j = (l, r)``, ``r in roles``, rows (7)-(8), [U1] one role per location,
    [U2] budget, optional ``size_bounds`` ``{role: (B_min, B_max, C_min, C_max)}`` (as ``B_min y_j
    <= B_j <= B_max y_j``, so that an option grid of contiguous ranges is reproduced exactly),
    optional [U4] ``access`` rows, [U5] expected service share ``zeta_exp``, ``max_role_count``
    (``{role: n}``: ``sum_l y_(l,r) <= n``, e.g. at most one hub) and, with ``s_needs_charge``,
    the rows ``y_(l,S) <= sum_l' (y_(l',C) + y_(l',SC))`` (a swap-only site only next to a
    charge-capable object, :func:`sites_nyc.layout_admissible`); one E2 operations
    sub-model per scenario (``ilp.ILPModel`` on the shared model, see the module docstring);
    objective ``sum_j (F_j y_j + bB_j B_j + bC_j C_j) + sum_s p_s (C_elec + C_travel + C_orders +
    C_reb)_s``.  ``mip_start_layout`` injects that layout's cached lower-level schedules (and
    its facility values) as MIP start.  After the solve the per-scenario schedules are checked
    with ``evaluate.check`` / priced with ``evaluate.cost`` on the all-candidates instances
    (sum == objective within 1e-6) and, with ``certify``, re-priced on the LAYOUT instances
    (facilities fixed) through :func:`materialise_schedule` -- the certified ``OPEX_s``.

    ``aggregate`` (plan item O1): ``None`` (default) builds every scenario sub-model with the
    aggregated integer flow (``ilp.build_submodel``, ``aggregate.py``) when
    :func:`aggregate_available`, else with the per-bike copies; ``True`` / ``False`` force it.
    The aggregated form is an equivalent implementation of E2 (5), (6), (9), (12), (22),
    (29)-(30); schedules are recovered per bike by path decomposition and certified exactly as
    before.  ``out['aggregate']`` records the choice.

    Returns ``status, obj, bound, gap, runtime_s, layout, V_certified, per_scenario, sizes,
    expected_served_share, mip_start, ...``; ``layout = None`` without an incumbent."""
    from ebike_swap_sim import ilp
    import gurobipy as gp
    from gurobipy import GRB

    spec = evaluator.spec
    cands = list(candidates)
    ids = [c.id for c in cands]
    node_of = {c.id: c.node for c in cands}
    t_all = time.perf_counter()
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 1 if output else 0)
    env.start()
    m = gp.Model("E2-siting", env=env)
    m.Params.OutputFlag = 1 if output else 0
    m.Params.Threads = int(threads)
    m.Params.TimeLimit = float(time_limit)
    for k_, v_ in {"Seed": 0, **(params or {})}.items():
        m.setParam(k_, v_)
    objects = [(l, r) for l in ids for r in roles]
    y: Dict[str, gp.Var] = {}
    B: Dict[str, gp.Var] = {}
    C: Dict[str, gp.Var] = {}
    for l, r in objects:
        fid = facility_id(l, r)
        y[fid] = m.addVar(vtype=GRB.BINARY, name=f"y[{fid}]")
        B[fid] = m.addVar(lb=0, ub=spec.K, vtype=GRB.INTEGER, name=f"B[{fid}]")
        C[fid] = m.addVar(lb=0, ub=spec.c_max(r), vtype=GRB.INTEGER, name=f"C[{fid}]")
    n_rows = 0
    for l, r in objects:                                               # [U3] = (7)-(8)
        fid = facility_id(l, r)
        m.addLConstr(B[fid] - spec.K * y[fid], GRB.LESS_EQUAL, 0, name=f"B_le_Ky[{fid}]")
        m.addLConstr(C[fid] - spec.c_max(r) * y[fid], GRB.LESS_EQUAL, 0, name=f"C_le_Cbary[{fid}]")
        n_rows += 2
        if r == "C":
            m.addLConstr(C[fid] - y[fid], GRB.GREATER_EQUAL, 0, name=f"C_ge_y[{fid}]")
            n_rows += 1
        if size_bounds and r in size_bounds:
            bmin, bmax, cmin, cmax = size_bounds[r]
            m.addLConstr(B[fid] - bmin * y[fid], GRB.GREATER_EQUAL, 0, name=f"B_ge_min[{fid}]")
            m.addLConstr(B[fid] - bmax * y[fid], GRB.LESS_EQUAL, 0, name=f"B_le_max[{fid}]")
            m.addLConstr(C[fid] - cmin * y[fid], GRB.GREATER_EQUAL, 0, name=f"C_ge_min[{fid}]")
            m.addLConstr(C[fid] - cmax * y[fid], GRB.LESS_EQUAL, 0, name=f"C_le_max[{fid}]")
            n_rows += 4
    for l in ids:                                                       # [U1]
        m.addLConstr(gp.quicksum(y[facility_id(l, r)] for r in roles), GRB.LESS_EQUAL, 1, name=f"one_role[{l}]")
        n_rows += 1
    inv = gp.quicksum(spec.Fhat * y[f] + spec.bhat * B[f] + spec.chat * C[f] for f in y)
    m.addLConstr(inv, GRB.LESS_EQUAL, float(budget), name="budget")   # [U2] = (33a)
    n_rows += 1
    for r, cap in (max_role_count or {}).items():
        if r in roles:
            m.addLConstr(gp.quicksum(y[facility_id(l, r)] for l in ids), GRB.LESS_EQUAL, int(cap), name=f"max_role[{r}]")
            n_rows += 1
    if s_needs_charge and "S" in roles:                                 # swap-only sites need a C / SC object
        charge_roles = [r for r in roles if ROLE_CHARGE[r]]
        charge_sum = gp.quicksum(y[facility_id(l, r)] for l in ids for r in charge_roles)
        for l in ids:
            m.addLConstr(y[facility_id(l, "S")] - charge_sum, GRB.LESS_EQUAL, 0, name=f"S_needs_charge[{l}]")
            n_rows += 1
    access_infeasible: List[str] = []
    if access:                                                          # [U4]
        swap_roles = [r for r in roles if ROLE_SWAP[r]]
        for z, locs in access.items():
            terms = [y[facility_id(l, r)] for l in locs if l in node_of for r in swap_roles]
            if not terms:
                access_infeasible.append(str(z))
                continue
            m.addLConstr(gp.quicksum(terms), GRB.GREATER_EQUAL, 1, name=f"access[{z}]")
            n_rows += 1
    setup = gp.quicksum(spec.setup_cost(r) * y[facility_id(l, r)] + spec.bB * B[facility_id(l, r)]
                        + spec.bC * C[facility_id(l, r)] for l, r in objects)
    subs: List[Any] = []
    insts: List[Instance] = []
    libs: List[ArcLibrary] = []
    opex = gp.LinExpr()
    share = gp.LinExpr()
    use_agg = aggregate_available() if aggregate is None else bool(aggregate)
    if use_agg and not hasattr(ilp, "build_submodel"):
        raise RuntimeError("aggregate=True but ilp.build_submodel is not available")
    agg_stats: List[Any] = []
    t0 = time.perf_counter()
    for s in range(evaluator.n_scenarios):
        _t_inst, t_lib = evaluator.template(s)
        inst_s = all_candidates_instance(evaluator.scenarios[s], spec, roles)
        inst_s = evaluator._maybe_relax(inst_s)
        lib_s = subset_library(t_lib, inst_s, strict=False)
        if use_agg:
            sub = ilp.build_submodel(inst_s, lib_s, m, facility_vars=(y, B, C), prefix=f"s{s}_", aggregate=True)
            agg = getattr(sub, "agg", None)
            agg_stats.append(agg.summary() if agg is not None and hasattr(agg, "summary") else None)
        else:
            sub = ilp.ILPModel(inst_s, lib_s, no_transfers=False, colocated=False, fixed_facilities=False, budget=None,
                               zeta=None, lexicographic=False, battery_swap_v1_bounds=False, threads=threads,
                               time_limit=time_limit, output=False, params=None, model=m, prefix=f"s{s}_",
                               facility_vars=(y, B, C), set_objective=False)
        subs.append(sub)
        insts.append(inst_s)
        libs.append(lib_s)
        opex += evaluator.p[s] * (sub.objective - sub.components["C_setup"])
        if inst_s.orders:
            share += evaluator.p[s] * (len(inst_s.orders) - sub.sum_u) / len(inst_s.orders)
    if zeta_exp is not None:                                             # [U5]
        m.addLConstr(share, GRB.GREATER_EQUAL, float(zeta_exp), name="expected_share")
        n_rows += 1
    m.setObjective(setup + opex, GRB.MINIMIZE)
    m.update()
    build_s = time.perf_counter() - t0
    # MIP start --------------------------------------------------------------
    start_info: Dict[str, Any] = {"given": False}
    if mip_start_layout is not None and mip_start_layout.n_open:
        start_info = {"given": True, "layout_key": mip_start_layout.key(), "scenarios_loaded": 0, "start_obj": None}
        yv = {f: 0 for f in y}
        Bv = {f: 0 for f in B}
        Cv = {f: 0 for f in C}
        for l, r, b_, c_ in mip_start_layout.open:
            fid = facility_id(l, r)
            if fid in yv:
                yv[fid], Bv[fid], Cv[fid] = 1, int(b_), int(c_)
        total = mip_start_layout.allocated_cost(spec)
        okay = all(facility_id(l, r) in yv for l, r, _b, _c in mip_start_layout.open)
        for s in range(evaluator.n_scenarios):
            if not okay:
                break
            row = evaluator.evaluate_scenario(mip_start_layout, s, "ilp")
            port = evaluator.load_portable(row) if row.get("feasible") else None
            sched = materialise_schedule(port, insts[s], libs[s], (yv, Bv, Cv)) if port else None
            if sched is None:
                okay = False
                break
            info = subs[s].set_mip_start(sched, verify=False)
            if not info["start_check_ok"]:
                okay = False
                break
            total += evaluator.p[s] * (info["start_obj"] - cost(insts[s], libs[s], sched)["C_setup"])
            start_info["scenarios_loaded"] += 1
        if okay:
            for f in y:
                y[f].Start, B[f].Start, C[f].Start = float(yv[f]), float(Bv[f]), float(Cv[f])
            start_info["start_obj"] = total
        else:
            start_info["error"] = "start could not be materialised on every scenario; ignored"
    first: List[Tuple[float, float]] = []

    def cb(model: gp.Model, where: int) -> None:
        if where == GRB.Callback.MIPSOL and not first:
            first.append((model.cbGet(GRB.Callback.MIPSOL_OBJ), model.cbGet(GRB.Callback.MIPSOL_NODCNT)))

    m.optimize(cb)
    out: Dict[str, Any] = {
        "label": label, "status": ilp.status_name(m.Status), "status_code": int(m.Status), "runtime_s": float(m.Runtime),
        "build_s": build_s, "wall_s": time.perf_counter() - t_all, "n_vars": m.NumVars, "n_binaries": m.NumBinVars,
        "n_rows": m.NumConstrs, "n_upper_rows": n_rows, "n_objects": len(objects), "roles": list(roles),
        "budget": float(budget), "size_bounds": size_bounds, "access_zones_infeasible": access_infeasible,
        "s_needs_charge": bool(s_needs_charge), "aggregate": bool(use_agg), "aggregate_stats": agg_stats,
        "zeta_exp": zeta_exp, "time_limit": float(time_limit), "threads": int(threads),
        "n_scenarios": evaluator.n_scenarios, "p": list(evaluator.p), "sol_count": int(m.SolCount),
        "node_count": float(m.NodeCount), "mip_start": start_info, "obj": None, "bound": None, "gap": None,
        "layout": None, "layout_key": None, "V_model": None, "V_certified": None, "per_scenario": [],
    }
    if start_info.get("given") and first:
        start_info["first_incumbent_obj"] = first[0][0]
        start_info["accepted"] = (start_info.get("start_obj") is not None
                                  and first[0][0] <= start_info["start_obj"] + _TOL * max(1.0, abs(start_info["start_obj"])))
    try:
        out["bound"] = float(m.ObjBound)
    except gp.GurobiError:
        pass
    if m.SolCount == 0:
        _dispose(m, env)
        return out
    out["obj"] = float(m.ObjVal)
    try:
        out["gap"] = float(m.MIPGap)
    except gp.GurobiError:
        pass
    items = []
    for l, r in objects:
        fid = facility_id(l, r)
        if y[fid].X > 0.5:
            items.append((l, r, int(round(B[fid].X)), int(round(C[fid].X))))
    layout = Layout.of(items)
    out["layout"], out["layout_key"] = layout, layout.key()
    out["investment"] = layout.investment(spec)
    out["C_setup"] = layout.allocated_cost(spec)
    out["sizes"] = {facility_id(l, r): {"y": int(round(y[facility_id(l, r)].X)), "B": int(round(B[facility_id(l, r)].X)),
                                        "C": int(round(C[facility_id(l, r)].X))} for l, r in objects}
    total_model = layout.allocated_cost(spec)
    total_cert = layout.allocated_cost(spec)
    exp_share = 0.0
    per: List[Dict[str, Any]] = []
    cert_ok = True
    for s, sub in enumerate(subs):
        sched = sub.extract_schedule()
        cst = cost(insts[s], libs[s], sched)
        rep = check(insts[s], libs[s], sched, switches={"budget": float(budget), "no_transfers": False})
        met = metrics(insts[s], libs[s], sched)
        opex_s = cst["total"] - cst["C_setup"]
        total_model += evaluator.p[s] * opex_s
        exp_share += evaluator.p[s] * met["served_share"]
        row = {"scenario": s, "seed": evaluator.seeds[s], "opex_model": opex_s, "C_setup_model": cst["C_setup"],
               "check_ok": rep["ok"], "n_violations": rep["n_violations"],
               "components": evaluator._C.flatten_cost(cst), "metrics": _flat_metrics(met), "opex_certified": None}
        if not rep["ok"]:
            raise ilp.ILPConsistencyError(f"integrated scenario {s} schedule violates {rep['n_violations']} rows: "
                                          + "; ".join(f"{fam}: {rec['examples'][:2]}" for fam, rec in rep["families"].items()))
        if certify:
            inst_l, lib_l = evaluator.template_pair(layout, s)   # the (A) / (B) library convention
            port = portable_schedule(sched, insts[s], libs[s])
            sched_l = materialise_schedule(port, inst_l, lib_l)
            if sched_l is None:
                raise ilp.ILPConsistencyError(f"integrated scenario {s}: schedule does not fit the layout instance")
            cst_l = cost(inst_l, lib_l, sched_l)
            rep_l = check(inst_l, lib_l, sched_l)
            row["opex_certified"] = cst_l["total"] - cst_l["C_setup"]
            row["check_ok_layout"] = rep_l["ok"]
            if not rep_l["ok"] or abs(row["opex_certified"] - opex_s) > _TOL * max(1.0, abs(opex_s)):
                cert_ok = False
            total_cert += evaluator.p[s] * row["opex_certified"]
        per.append(row)
    if abs(total_model - out["obj"]) > _TOL * max(1.0, abs(out["obj"])):
        raise ilp.ILPConsistencyError(f"priced total {total_model!r} differs from the integrated objective {out['obj']!r}")
    out.update(per_scenario=per, V_model=total_model, V_certified=(total_cert if certify else None),
               certified_ok=(cert_ok if certify else None), expected_served_share=exp_share)
    _dispose(m, env)
    return out


def _dispose(m: Any, env: Any) -> None:
    try:
        m.dispose()
        env.dispose()
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# (E) cross-evaluation
# ---------------------------------------------------------------------------
def cross_evaluate(evaluator: LowerLevelEvaluator, layout: Layout, policies: Sequence[str] = POLICIES,
                   scenarios: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    """``V^policy(lambda)`` for every policy on the evaluator's scenarios (or a subset): the
    lower-level ILP, the R2.3 baseline policy and follower E (``'selfish'``, the ``r5_selfish``
    equilibrium, plan item M4) on the same layout instances and libraries.  Returns
    ``{policy: evaluation dict}`` plus ``gap_vs_baseline_pct`` = 100 (base - ILP) / base,
    ``gap_vs_selfish_pct`` = 100 (selfish - ILP) / selfish and ``price_of_decentralisation`` =
    V_selfish / V_ILP (IJCAI-15 framing, plan item A2)."""
    out: Dict[str, Any] = {}
    for pol in policies:
        out[pol] = evaluator.evaluate(layout, pol, scenarios=scenarios)

    def _gap(other: str) -> Optional[float]:
        vi, vo = out["ilp"].get("V"), out[other].get("V")
        return None if vi is None or vo in (None, 0, INF) or vi == INF else 100.0 * (vo - vi) / vo

    if "ilp" in out and "baseline" in out:
        out["gap_vs_baseline_pct"] = _gap("baseline")
    if "ilp" in out and "selfish" in out:
        out["gap_vs_selfish_pct"] = _gap("selfish")
        vi, vs = out["ilp"].get("V"), out["selfish"].get("V")
        out["price_of_decentralisation"] = (None if vi in (None, 0, INF) or vs in (None, INF) else vs / vi)
    return out


# ---------------------------------------------------------------------------
# Round 5, plan item M4: compliance sweep (a share of riders follows the ILP plan)
# ---------------------------------------------------------------------------
def compliance_sweep(evaluator: LowerLevelEvaluator, layout: Layout,
                     alphas: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0), scenarios: Optional[Sequence[int]] = None,
                     seeds: Sequence[int] = (0,), station_plan: str = "plan") -> Dict[str, Any]:
    """Compliance sweep of plan item M4 at one layout: on every scenario the lower-level ILP
    schedule (cached, :meth:`LowerLevelEvaluator.evaluate_scenario`) is the coordinator's plan;
    for each compliance share ``alpha_c`` and draw ``seed`` (which riders comply,
    ``baseline.select_compliant_bikes``) ``baseline.simulate_compliance`` lets the compliant
    riders follow the plan and the others behave as follower E (``r5_selfish`` rule with the
    evaluator's ``selfish['params']``); ``station_plan`` = ``'plan'`` replays the plan's charging
    and shuttles, ``'policy'`` runs the policy's own station rules.  Every result is an ordinary
    Schedule priced by ``evaluate.cost`` (E2 (26)-(32)) and checked by ``evaluate.check``; no E2
    equation is involved.  ``alpha_c = 1`` with ``station_plan='plan'`` reproduces the ILP value.

    Returns ``{'rows': [per scenario x alpha x seed], 'summary': [per alpha: V = C_setup +
    sum_s p_s mean_seed OPEX_s, served share, defections], 'layout_key', 'station_plan'}``."""
    from . import baseline as bl

    idx = list(range(evaluator.n_scenarios)) if scenarios is None else list(scenarios)
    rows: List[Dict[str, Any]] = []
    setup = layout.allocated_cost(evaluator.spec)
    params = dict(evaluator.selfish.get("params") or {})
    for s in idx:
        ilp_row = evaluator.evaluate_scenario(layout, s, "ilp")
        port = evaluator.load_portable(ilp_row) if ilp_row.get("feasible") else None
        inst, lib = evaluator.layout_pair(layout, s)
        plan = materialise_schedule(port, inst, lib) if port else None
        if plan is None:
            for a in alphas:
                rows.append({"scenario": s, "seed_scenario": evaluator.seeds[s], "alpha_c": float(a), "status": "NO_PLAN",
                             "ilp_status": ilp_row.get("status"), "opex": None})
            continue
        for a in alphas:
            for sd in seeds:
                sched, flags = bl.simulate_compliance(inst, lib, plan, float(a), params=params, seed=int(sd),
                                                      station_plan=station_plan)
                cst = cost(inst, lib, sched)
                rep = check(inst, lib, sched)
                met = metrics(inst, lib, sched)
                comp = flags.get("compliance", {})
                rows.append({"scenario": s, "seed_scenario": evaluator.seeds[s], "alpha_c": float(a), "draw": int(sd),
                             "status": "OK", "total": cst["total"], "opex": cst["total"] - cst["C_setup"],
                             "ilp_opex": ilp_row.get("opex"), "served_share": met["served_share"],
                             "n_compliant": len(comp.get("compliant", [])), "n_defected": len(comp.get("defected", [])),
                             "planned_swaps_done": comp.get("planned_swaps_done"),
                             "families": evaluator._C.family_counts(rep), "check_ok": rep["ok"]})
    summary: List[Dict[str, Any]] = []
    for a in alphas:
        ok = [r for r in rows if r["alpha_c"] == float(a) and r["status"] == "OK"]
        complete = all(any(r["scenario"] == s for r in ok) for s in idx)
        if not ok or not complete:
            summary.append({"alpha_c": float(a), "V": None, "complete": False})
            continue
        V = setup
        share = 0.0
        ptot = sum(evaluator.p[s] for s in idx)
        for s in idx:
            rs = [r for r in ok if r["scenario"] == s]
            V += evaluator.p[s] / ptot * sum(r["opex"] for r in rs) / len(rs)
            share += evaluator.p[s] / ptot * sum(r["served_share"] for r in rs) / len(rs)
        summary.append({"alpha_c": float(a), "V": V, "served_share": share, "complete": True,
                        "mean_defected": sum(r["n_defected"] for r in ok) / len(ok)})
    return {"layout_key": layout.key(), "station_plan": station_plan, "rows": rows, "summary": summary,
            "C_setup": setup}


# ---------------------------------------------------------------------------
# Round 5, plan item A4: siting baselines (IJCAI-15 rules, present-day) and the lever table
# ---------------------------------------------------------------------------
#: IJCAI-15 (Xiong et al., Sec. 5.1) planner baselines, adapted to swap sites (plan item A4 (ii)).
RULES: Tuple[str, ...] = ("CSCD", "CSTC", "CSAV")
#: Marginal levers of plan item A4 (iii).
LEVERS: Tuple[str, ...] = ("spare", "charger", "position", "shuttle", "grid")
#: Files under ``data/raw`` that :func:`present_day_sites` reads when present: a GBFS
#: ``station_information`` feed (stations with ``is_charging_station: true``) or a CSV of e-bike
#: charging / swap hubs with ``lat``, ``lon`` columns.
PRESENT_DAY_FILES: Tuple[str, ...] = ("citibike_station_information.json", "ebike_charging_hubs.csv")


def _order_nodes(inst: Instance) -> List[Tuple[Node, Node]]:
    return [(o.o, o.d) for o in inst.orders]


def demand_weights(candidates: Sequence[Candidate], scenarios: Sequence[Instance], D_blocks: int,
                   probabilities: Optional[Sequence[float]] = None) -> Dict[str, float]:
    """CSCD demand of every candidate (plan item A4; IJCAI-15 ``x_i ~ gamma_i``): the expected
    number of orders whose restaurant or customer node lies within ``D_blocks`` (grid distance)
    of the candidate, over the scenarios with probabilities ``p_s`` (uniform by default)."""
    n = len(scenarios)
    p = [1.0 / n] * n if probabilities is None else list(probabilities)
    out = {c.id: 0.0 for c in candidates}
    for ps, inst in zip(p, scenarios):
        for o, d in _order_nodes(inst):
            for c in candidates:
                if manhattan_blocks(c.node, o) <= D_blocks or manhattan_blocks(c.node, d) <= D_blocks:
                    out[c.id] += ps
    return out


def access_weights(candidates: Sequence[Candidate], scenarios: Sequence[Instance],
                   probabilities: Optional[Sequence[float]] = None) -> Dict[str, float]:
    """IJCAI-15 CSTC weights (``x_i ~ sum_j 1 / (alpha_ji d_ji)`` with uniform congestion
    ``alpha``): ``sum over orders of 1 / (1 + d)`` with ``d`` the grid distance in blocks from
    the candidate to the order's restaurant, expected over the scenarios (plan item A4)."""
    n = len(scenarios)
    p = [1.0 / n] * n if probabilities is None else list(probabilities)
    out = {c.id: 0.0 for c in candidates}
    for ps, inst in zip(p, scenarios):
        for o, _d in _order_nodes(inst):
            for c in candidates:
                out[c.id] += ps / (1.0 + manhattan_blocks(c.node, o))
    return out


def isolation_values(evaluator: LowerLevelEvaluator, candidates: Sequence[Candidate], role: str = "SC",
                     B: int = 1, C: int = 1, policy: str = "ilp") -> Dict[str, Optional[float]]:
    """Total cost ``V`` of every candidate opened ALONE as ``(role, B, C)`` under ``policy``
    (the task's CSTC: "lowest total cost per site in isolation", plan item A4); ``None`` when
    the singleton is infeasible or not priced (wall budget)."""
    out: Dict[str, Optional[float]] = {}
    for c in candidates:
        ev = evaluator.evaluate(Layout.of([(c.id, role, int(B), int(C))]), policy)
        v = ev["V"]
        out[c.id] = None if v is None or v == INF else float(v)
    return out


def _spread_order(candidates: Sequence[Candidate], k: int) -> List[str]:
    """CSAV site choice: ``k`` candidates spread evenly over the region by greedy max-min
    dispersion (grid distance), starting from the candidate nearest to the candidates' mean
    node (ties by id).  Deterministic."""
    cands = list(candidates)
    if not cands or k <= 0:
        return []
    if isinstance(cands[0].node, (list, tuple)):
        mx = sum(c.node[0] for c in cands) / len(cands)
        my = sum(c.node[1] for c in cands) / len(cands)
        first = min(cands, key=lambda c: (abs(c.node[0] - mx) + abs(c.node[1] - my), c.id))
    else:
        m = sum(float(c.node) for c in cands) / len(cands)
        first = min(cands, key=lambda c: (abs(float(c.node) - m), c.id))
    chosen = [first]
    while len(chosen) < min(k, len(cands)):
        rest = [c for c in cands if c not in chosen]
        nxt = max(rest, key=lambda c: (min(manhattan_blocks(c.node, h.node) for h in chosen), -cands.index(c)))
        chosen.append(nxt)
    return [c.id for c in chosen]


def rule_layout(rule: str, candidates: Sequence[Candidate], budget: float, spec: SitingSpec,
                weights: Optional[Dict[str, Optional[float]]] = None, role: str = "SC", base_size: Tuple[int, int] = (1, 1),
                max_B: Optional[int] = None, max_C: Optional[int] = None, k: Optional[int] = None,
                lower_is_better: bool = False) -> Optional[Layout]:
    """Layout of an IJCAI-15 planner rule at a budget (plan item A4 (ii); upper-level data only).

    ``k`` = the largest number of ``role`` sites of size ``base_size`` within ``budget`` (33a)
    (capped by the number of candidates; given ``k`` is used when affordable).  Sites:

    * ``CSCD`` -- the ``k`` candidates with the largest ``weights`` (demand, :func:`demand_weights`);
    * ``CSTC`` -- the ``k`` best by ``weights`` (``lower_is_better=True`` for costs, e.g.
      :func:`isolation_values`; or the inverse-distance access of :func:`access_weights`);
      candidates with ``None`` weight (infeasible alone) are skipped;
    * ``CSAV`` -- ``k`` candidates spread evenly (:func:`_spread_order`), equal weights.

    The remaining budget buys extra spares and chargers alternately (spare, charger, spare, ...),
    each to the open site with the largest ``weight / (extra + 1)`` (D'Hondt; CSAV: equal), up to
    ``max_B`` (default ``K``) / ``max_C`` (default ``c_max``) per site, until neither fits.
    Returns ``None`` when not even one site is affordable."""
    if rule not in RULES:
        raise ValueError(f"rule must be one of {RULES} (got {rule!r})")
    B0, C0 = int(base_size[0]), int(base_size[1])
    if not spec.valid_sizes(role, B0, C0):
        raise ValueError(f"base size {base_size} invalid for role {role}")
    unit = spec.Fhat + spec.bhat * B0 + spec.chat * C0
    k_max = int(math.floor((float(budget) + 1e-9) / unit))
    kk = min(len(candidates), k_max if k is None else min(int(k), k_max))
    if kk < 1:
        return None
    ids = [c.id for c in candidates]
    if rule == "CSAV":
        sites = _spread_order(candidates, kk)
        w = {l: 1.0 for l in sites}
    else:
        if weights is None:
            raise ValueError(f"{rule} needs weights")
        pool = [l for l in ids if weights.get(l) is not None]
        sign = 1.0 if lower_is_better else -1.0
        pool.sort(key=lambda l: (sign * float(weights[l]), ids.index(l)))
        sites = pool[:kk]
        if not sites:
            return None
        vals = [float(weights[l]) for l in sites]
        if lower_is_better:   # turn costs into positive "attractiveness" for the size split
            hi = max(vals)
            w = {l: (hi - float(weights[l])) + 1.0 for l in sites}
        else:
            w = {l: max(float(weights[l]), 0.0) + 1e-9 for l in sites}
    capB = int(spec.K if max_B is None else max_B)
    capC = int(spec.c_max(role) if max_C is None else max_C)
    size = {l: [B0, C0] for l in sites}
    rem = float(budget) - len(sites) * unit
    kinds = [("B", spec.bhat, capB, 0), ("C", spec.chat, capC, 1)]
    if not ROLE_CHARGE[role]:
        kinds = kinds[:1]
    turn = 0
    stalled = 0
    while stalled < len(kinds):
        name, price, cap, pos = kinds[turn % len(kinds)]
        turn += 1
        if rem + 1e-9 < price:
            stalled += 1
            continue
        open_ = [l for l in sites if size[l][pos] < cap]
        if not open_:
            stalled += 1
            continue
        best = max(open_, key=lambda l: (w[l] / (size[l][pos] - (B0, C0)[pos] + 1), -sites.index(l)))
        size[best][pos] += 1
        rem -= price
        stalled = 0
    lay = Layout.of([(l, role, size[l][0], size[l][1]) for l in sites])
    return lay if lay.investment(spec) <= float(budget) + 1e-6 else None


def rule_baselines(evaluator: LowerLevelEvaluator, candidates: Sequence[Candidate], budgets: Sequence[float],
                   rules: Sequence[str] = RULES, policies: Sequence[str] = ("ilp",), D_blocks: Optional[int] = None,
                   cstc_mode: str = "isolation", role: str = "SC", size_caps: Optional[Tuple[int, int]] = None,
                   on_row: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """Plan item A4 (ii): the IJCAI-15 planner rules at equal budget, each layout priced by every
    lower-level ``policy`` (``V`` vs budget).  ``D_blocks`` = CSCD demand radius (default the
    eBaaS-anchored ``sites_nyc.access_radius_blocks()``); ``cstc_mode`` = ``'isolation'`` (the
    singleton total cost of every candidate as ``(role, 1, 1)`` under the ILP,
    :func:`isolation_values`) or ``'access'`` (IJCAI-15's inverse-distance access,
    :func:`access_weights`); ``size_caps = (max_B, max_C)`` per site (e.g. the size menu).
    Returns ``{'rows': [{rule, budget, layout_key, investment, policy, V, served_share, status,
    ...}], 'weights': {rule: {loc: w}}, 'cstc_mode', 'D_blocks'}``."""
    if cstc_mode not in ("isolation", "access"):
        raise ValueError("cstc_mode must be 'isolation' or 'access'")
    D = SN.access_radius_blocks() if D_blocks is None else int(D_blocks)
    weights: Dict[str, Dict[str, Optional[float]]] = {}
    if "CSCD" in rules:
        weights["CSCD"] = dict(demand_weights(candidates, evaluator.scenarios, D, evaluator.p))
    if "CSTC" in rules:
        weights["CSTC"] = (isolation_values(evaluator, candidates, role=role) if cstc_mode == "isolation"
                           else dict(access_weights(candidates, evaluator.scenarios, evaluator.p)))
    rows: List[Dict[str, Any]] = []
    mB, mC = (None, None) if size_caps is None else (int(size_caps[0]), int(size_caps[1]))
    for b in budgets:
        for rule in rules:
            lay = rule_layout(rule, candidates, float(b), evaluator.spec, weights.get(rule), role=role, max_B=mB, max_C=mC,
                              lower_is_better=(rule == "CSTC" and cstc_mode == "isolation"))
            for pol in policies:
                row: Dict[str, Any] = {"rule": rule, "budget": float(b), "policy": pol,
                                       "cstc_mode": cstc_mode if rule == "CSTC" else None,
                                       "layout_key": None if lay is None else lay.key(),
                                       "layout": None if lay is None else lay.to_json()}
                if lay is None:
                    row.update(status="NONE", V=None)
                else:
                    ev = evaluator.evaluate(lay, pol)
                    row.update(status=ev["status"], V=(None if ev["V"] in (None, INF) else ev["V"]),
                               feasible=ev["feasible"], investment=lay.investment(evaluator.spec),
                               C_setup=lay.allocated_cost(evaluator.spec), opex_mean=ev["opex_mean"],
                               served_share=ev.get("served_share"), n_open=lay.n_open, total_B=lay.total_B(),
                               total_C=lay.total_C(), gaps=ev["gaps"])
                rows.append(row)
                if on_row is not None:
                    on_row(row)
    return {"rows": rows, "weights": weights, "cstc_mode": cstc_mode, "D_blocks": D}


def present_day_sites(candidates: Sequence[Candidate], data_dir: Optional[str] = None,
                      dot_csv: Optional[str] = None, pilot_types: Sequence[str] = ("pilot",)) -> Dict[str, Any]:
    """Weights of the capacity-matched "present-day" layout (plan item A4 (i); ITSC-21 Sec. III-B).

    If ``data_dir`` (default ``data/raw``) holds one of :data:`PRESENT_DAY_FILES` -- a GBFS
    ``station_information`` feed (stations with ``is_charging_station: true``, i.e. Citi Bike
    e-bike charging docks) or a CSV of e-bike charging / swap hubs with ``lat`` and ``lon`` --
    every point is assigned to its nearest candidate (equirectangular metres) and the weight of
    a candidate is its number of points.  R7 (design 2.6): the DOT candidate file (``dot_csv``,
    default ``data/raw/dot_candidate_sites.csv``) is a third source: its rows of ``site_type``
    in ``pilot_types`` (the 2024 DOT pilot cabinets), weight 1 per site, used when neither of
    the first two files exists.  Otherwise the DOCUMENTED PROXY is used: today's
    cabinets cluster where restaurants cluster (the proposal deck's demand-proportional
    layout), so the weight is the number of DOHMH rows snapped to the candidate node
    (``Candidate.n_restaurants``).  Returns ``{'weights', 'source', 'n_points', 'proxy'}``."""
    from . import data_nyc as dn

    root = data_dir or dn.DATA_RAW
    pts: List[Tuple[float, float]] = []
    source = None
    gbfs = os.path.join(root, PRESENT_DAY_FILES[0])
    hubs = os.path.join(root, PRESENT_DAY_FILES[1])
    dot = dot_csv or os.path.join(root, os.path.basename(SN.DOT_CSV_DEFAULT))
    if os.path.exists(gbfs):
        with open(gbfs, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        stations = (data.get("data") or {}).get("stations") or data.get("stations") or []
        pts = [(float(st["lat"]), float(st["lon"])) for st in stations if st.get("is_charging_station")]
        source = f"{gbfs} (is_charging_station = true)"
    elif os.path.exists(hubs):
        import pandas as pd
        df = pd.read_csv(hubs)
        pts = [(float(a), float(b)) for a, b in zip(df["lat"], df["lon"])]
        source = hubs
    elif os.path.exists(dot):
        for r in SN.read_dot_rows(dot):
            if SN._dot_type(r.get("site_type", r.get("type"))) in set(pilot_types):
                try:
                    pts.append((float(r.get("lat")), float(r.get("lon"))))
                except (TypeError, ValueError):
                    continue
        source = f"{dot} (site_type in {list(pilot_types)})"
    if pts:
        w = {c.id: 0.0 for c in candidates}
        for lat, lon in pts:
            near = min(candidates, key=lambda c: (((c.lat - lat) * dn.M_PER_DEG_LAT) ** 2
                                                  + ((c.lon - lon) * dn.M_PER_DEG_LON) ** 2, c.id))
            w[near.id] += 1.0
        return {"weights": w, "source": source, "n_points": len(pts), "proxy": False}
    return {"weights": {c.id: float(c.n_restaurants) for c in candidates},
            "source": "proxy: DOHMH restaurants at the candidate node (no present-day hub list in data/raw)",
            "n_points": 0, "proxy": True}


def capacity_matched_layout(candidates: Sequence[Candidate], reference: Layout, weights: Dict[str, float],
                            spec: SitingSpec, n_sites: Optional[int] = None, role: str = "SC") -> Layout:
    """Capacity-matched "present-day" layout (plan item A4 (i)): the ``n_sites`` (default the
    reference's number of open locations) candidates with the largest ``weights``
    (:func:`present_day_sites`), all as ``role``, with the reference's total spares and
    chargers split proportionally to the weights (largest remainder; a swap-capable site gets
    at least one spare when the total allows; caps ``K`` / ``c_max`` respected, overflow to the
    next site).  Same number of sites and the same totals give the same investment (33a) as
    the reference when ``role`` matches its roles."""
    ids = [c.id for c in candidates]
    n = int(reference.n_open if n_sites is None else n_sites)
    sites = sorted(ids, key=lambda l: (-float(weights.get(l, 0.0)), ids.index(l)))[:max(1, n)]
    w = [max(float(weights.get(l, 0.0)), 0.0) + 1e-9 for l in sites]

    def split(total: int, cap: int, floor_one: bool) -> List[int]:
        out = [0] * len(sites)
        if floor_one and total >= len(sites):
            out = [1] * len(sites)
        rest = total - sum(out)
        tw = sum(w)
        raw = [rest * x / tw for x in w]
        add = [int(math.floor(r)) for r in raw]
        out = [min(cap, a + b) for a, b in zip(out, add)]
        order = sorted(range(len(sites)), key=lambda i: (-(raw[i] - math.floor(raw[i])), i))
        left = total - sum(out)
        while left > 0 and any(o < cap for o in out):
            for i in order:
                if left <= 0:
                    break
                if out[i] < cap:
                    out[i] += 1
                    left -= 1
        return out

    Bs = split(int(reference.total_B()), int(spec.K), ROLE_SWAP[role])
    Cs = split(int(reference.total_C()), int(spec.c_max(role)), False) if ROLE_CHARGE[role] else [0] * len(sites)
    if role == "C":
        Cs = [max(c, 1) for c in Cs]
    return Layout.of([(l, role, b, c) for l, b, c in zip(sites, Bs, Cs)])


def lever_table(evaluator: LowerLevelEvaluator, layout: Layout, policies: Sequence[str] = POLICIES,
                levers: Sequence[str] = LEVERS, position_capex: float = 400.0, grid_factor: float = 1.1,
                scenarios: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    """Marginal-lever table of plan item A4 (iii) at ``layout`` under each follower (``ilp``,
    ``baseline``, ``selfish``); levers are data changes only (no E2 equation changes):

    * ``spare`` -- ``B_j + 1`` at each open site (``+bhat`` investment (33a), ``+bB`` allocated (27));
    * ``charger`` -- ``C_j + 1`` at each open charge-capable site below ``c_max`` (``+chat``, ``+bC``);
    * ``position`` -- ``M_j + 1`` swap positions of (22) at each open swap-capable site (variant
      ``M``); capex ``position_capex`` (400 USD, ``costs.position_cost_per_window`` per window);
    * ``shuttle`` -- one more shuttle vehicle on the timetable (variant ``extra_shuttle``,
      services (10)-(11)); no investment in (33a), every trip priced by ``f_e`` (32); not
      applicable without services (fewer than two locations);
    * ``grid`` -- every grid-group cap of (21) times ``grid_factor`` (+10 %); a demand charge
      is not priced here (M10(b), ``costs.demand_charge_proxy``).

    ``d_V = V_new + extra allocated cost not in V (position) - V_ref`` per (lever, site, policy);
    ``best`` lists the lowest ``d_V`` per (lever, policy).  Returns ``{'reference': {policy:
    V}, 'rows', 'best', 'layout_key'}``."""
    from .costs import position_cost_per_window

    spec = evaluator.spec
    window_h = evaluator.scenarios[0].H * evaluator.scenarios[0].disc.Delta_h
    ref = {pol: evaluator.evaluate(layout, pol, scenarios=scenarios) for pol in policies}
    probe_inst = evaluator.layout_pair(layout, 0)[0]
    rows: List[Dict[str, Any]] = []
    for lever in levers:
        cases: List[Tuple[str, LowerLevelEvaluator, Optional[Layout], float, float, float, str]] = []
        if lever == "spare":
            for l, r, B, C in layout.open:
                if spec.valid_sizes(r, B + 1, C):
                    cases.append((l, evaluator, layout.replace(l, (l, r, B + 1, C)), spec.bhat, spec.bB, 0.0, ""))
        elif lever == "charger":
            for l, r, B, C in layout.open:
                if ROLE_CHARGE[r] and spec.valid_sizes(r, B, C + 1):
                    cases.append((l, evaluator, layout.replace(l, (l, r, B, C + 1)), spec.chat, spec.bC, 0.0, ""))
        elif lever == "position":
            alloc = position_cost_per_window(position_capex, window_h=window_h)
            for l, r, B, C in layout.open:
                if ROLE_SWAP[r]:
                    M = {**evaluator.variant.get("M", {}), l: int(spec.M) + 1}
                    ev2 = evaluator.derive(variant={**evaluator.variant, "M": M})
                    cases.append((l, ev2, layout, float(position_capex), alloc, alloc,
                                  f"M_j {spec.M} -> {spec.M + 1}; capex {position_capex:g} USD"))
        elif lever == "shuttle":
            if probe_inst.services:
                ev2 = evaluator.derive(variant={**evaluator.variant, "extra_shuttle": True})
                cases.append(("all pairs", ev2, layout, 0.0, 0.0, 0.0,
                              "one more vehicle (twin departures every/2 later); trips priced by f_e (32)"))
            else:
                cases.append(("-", evaluator, None, 0.0, 0.0, 0.0, "not applicable: no shuttle services in this layout"))
        elif lever == "grid":
            if probe_inst.P_grid:
                ev2 = evaluator.derive(variant={**evaluator.variant,
                                                "grid_factor": float(evaluator.variant.get("grid_factor", 1.0)) * grid_factor})
                cases.append(("group", ev2, layout, 0.0, 0.0, 0.0,
                              f"P_grid x {grid_factor:g}; demand charge not priced (M10(b))"))
            else:
                cases.append(("-", evaluator, None, 0.0, 0.0, 0.0, "not applicable: no grid group"))
        else:
            raise ValueError(f"unknown lever {lever!r}; known {LEVERS}")
        if not cases:
            cases.append(("-", evaluator, None, 0.0, 0.0, 0.0, "not applicable: every open site is at its size cap"))
        for site, ev2, lay2, d_inv, d_alloc, extra_alloc, note in cases:
            for pol in policies:
                v_ref = ref[pol]["V"]
                row: Dict[str, Any] = {"lever": lever, "site": site, "policy": pol, "note": note,
                                       "V_ref": (None if v_ref in (None, INF) else v_ref),
                                       "served_ref": ref[pol].get("served_share"), "d_investment": d_inv,
                                       "d_allocated": d_alloc}
                if lay2 is None:
                    row.update(status="NA", V_new=None, d_V=None)
                    rows.append(row)
                    continue
                ev = ev2.evaluate(lay2, pol, scenarios=scenarios)
                v_new = ev["V"]
                row.update(status=ev["status"], layout_key=lay2.key(), V_new=(None if v_new in (None, INF) else v_new),
                           served_new=ev.get("served_share"))
                if v_new in (None, INF) or v_ref in (None, INF):
                    row["d_V"] = None
                else:
                    row["d_V"] = float(v_new) + extra_alloc - float(v_ref)
                    row["d_opex"] = (float(v_new) - lay2.allocated_cost(spec)) - (float(v_ref) - layout.allocated_cost(spec))
                    row["d_V_per_kusd"] = (row["d_V"] / (d_inv / 1000.0)) if d_inv > 0 else None
                rows.append(row)
    best: List[Dict[str, Any]] = []
    for lever in levers:
        for pol in policies:
            rs = [r for r in rows if r["lever"] == lever and r["policy"] == pol and r.get("d_V") is not None]
            if rs:
                b = min(rs, key=lambda r: (r["d_V"], str(r["site"])))
                best.append({"lever": lever, "policy": pol, "site": b["site"], "d_V": b["d_V"],
                             "d_investment": b["d_investment"], "served_new": b.get("served_new")})
            else:
                best.append({"lever": lever, "policy": pol, "site": None, "d_V": None})
    return {"layout_key": layout.key(), "reference": {p: (None if ref[p]["V"] in (None, INF) else ref[p]["V"]) for p in policies},
            "rows": rows, "best": best}


def dot_pilot_layout(candidates: Sequence[Candidate], option: Tuple[str, int, int] = ("SC", 3, 2),
                     pilot_types: Sequence[str] = ("pilot",)) -> Optional[Layout]:
    """R7 (design 2.6): the all-pilot DOT layout -- every in-region candidate whose surviving DOT
    row is a pilot site (``Candidate.dot_type``), open as ``option``; ``None`` without any."""
    locs = [c.id for c in candidates if c.dot_type in set(pilot_types)]
    if not locs:
        return None
    r, B, C = option
    return Layout.of([(l, r, int(B), int(C)) for l in locs])


def _t975(df: int) -> float:
    try:
        from scipy import stats
        return float(stats.t.ppf(0.975, int(df)))
    except Exception:  # noqa: BLE001
        return {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
                10: 2.228, 11: 2.201}.get(int(df), 1.96)


def paired_ci(diffs: Sequence[float], p: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    """Plain paired t over the scenarios (``n - 1`` df): ``mean`` (``p``-weighted when given,
    else uniform), ``half`` = t_{0.975} x sd / sqrt(n) with the unweighted sample sd."""
    d = [float(x) for x in diffs]
    n = len(d)
    if n == 0:
        return {"mean": None, "half": None, "df": 0, "n": 0}
    w = [1.0 / n] * n if p is None else [float(x) for x in p]
    mean = sum(wi * x for wi, x in zip(w, d)) / sum(w)
    if n < 2:
        return {"mean": mean, "half": None, "df": 0, "n": n}
    m0 = sum(d) / n
    sd = math.sqrt(sum((x - m0) ** 2 for x in d) / (n - 1))
    return {"mean": mean, "half": _t975(n - 1) * sd / math.sqrt(n), "df": n - 1, "n": n, "sd": sd}


def stratified_ci(diffs: Sequence[float], strata: Sequence[Any], p: Sequence[float]) -> Dict[str, Any]:
    """Stratified paired estimator (design 2.7): per stratum ``h`` the mean difference over its
    scenarios and the within-stratum variance (``n_h - 1`` df); the estimate is
    ``sum_h W_h mean_h`` with ``W_h = sum of p_s in h``, its variance ``sum_h W_h^2 s_h^2 / n_h``
    and the df ``sum_h (n_h - 1)``.  Strata with one scenario contribute no variance (noted)."""
    groups: Dict[Any, List[Tuple[float, float]]] = {}
    for d, h, ps in zip(diffs, strata, p):
        groups.setdefault(h, []).append((float(d), float(ps)))
    est = 0.0
    var = 0.0
    df = 0
    single = []
    for h, rows in groups.items():
        W = sum(ps for _d, ps in rows)
        n_h = len(rows)
        m_h = sum(d for d, _ps in rows) / n_h
        est += W * m_h
        if n_h >= 2:
            s2 = sum((d - m_h) ** 2 for d, _ps in rows) / (n_h - 1)
            var += W * W * s2 / n_h
            df += n_h - 1
        else:
            single.append(h)
    half = (_t975(df) * math.sqrt(var)) if df >= 1 else None
    return {"mean": est, "half": half, "df": df, "n": len(diffs), "n_strata": len(groups), "single_strata": single}
