"""Plan item O2: certified siting bound by L-shaped Benders decomposition with exact incumbent
pricing (``notes/o2_siting_bound_design.md``, corrections C1-C16 applied; equation numbers refer
to ``notes/extracted/E2.txt``).

No equation of E2 (1)-(33) changes.  The lower level of every incumbent is the unchanged
operations ILP, priced through :class:`~ebike_swap_sim.bilevel.LowerLevelEvaluator`
(``reposition='all_candidates'``).  The LP relaxation of the operations model is used for
bounds only.

Pieces
------
:class:`MenuEncoding`
    menu binaries ``w_{l,o}`` of the master (one option ``o = (r, B, C)`` of the family size
    menu per location) and the linear maps ``y_(l,r) = sum w``, ``B = sum B_o w``,
    ``C = sum C_o w`` (design 3.1).
:class:`ScenarioLP`
    one persistent LP per scenario (design 2.1): the aggregated E2 sub-model
    (``ilp.build_submodel(..., keep_rows=True)``) on the all-candidates template of the scenario,
    free copy columns ``Yc, Bc, Cc`` pinned by fixing rows, artificial ``source -> SINK`` columns
    and bounded slacks on (17)-(18) at cost ``M_el`` (C2, complete recourse), all columns
    continuous.  :meth:`ScenarioLP.solve` returns the SAFE Lagrangian cut of C1:
    ``theta_s >= c0 + beta . x`` with ``c0 = sum_i Pi_i h_i + sum_v min(rc_v l_v, rc_v u_v)``
    (sign-projected row duals, exact reduced costs), valid for every first-stage value whatever
    the solver accuracy.  :meth:`ScenarioLP.set_target` switches written <-> relaxed end
    targets by coefficient changes.
:class:`Cut`, :class:`CutPool`
    optimality cuts (``lp``), integer cuts (classic L-shaped ``lshaped`` and ``lifted``, 3.4),
    combinatorial cuts (``terminal``, ``nogood``, 2.4 c); append-only ``cuts.jsonl`` with a
    signature header; one-way target import relaxed -> written (C16).
:class:`Master`
    master MIP over the menu binaries (3.2): one role per location [U1], budget [U2], at least
    one swap object, swap-only sites next to a charge-capable object, optional access rows [U4],
    a-priori terminal cover rows (2.4 b), ``theta_s >= LB_s^sup`` and the cuts.
:func:`price_layout`
    exact pricing with a bound-driven stop (4.2, corrected by C3 / C4): scenario lower bounds
    are ``row.bound - row.C_setup``, values ``row.opex``.
:func:`relax_and_round`, :class:`LPScreen`
    the LP-based screen of section 5 (warm start of the master and screen of the greedy).
:class:`SitingCertifier`
    the algorithm of 3.8 for one target and all budgets: warm start, LP phase (Kelley with
    in-out stabilisation), relax-and-round screen, integer phase with LP pruning (C5),
    escalation (one scenario per call, the largest ``p_s`` x gap) and the per-budget gap report
    (:meth:`SitingCertifier.finish`).  Search completeness: when the master keeps proposing a
    layout whose pricing gap can no longer be closed, an exploration copy of the master with
    no-goods on such ``stuck`` layouts proposes the next candidate (``LB`` is taken only from
    the unmodified master).  :meth:`SitingCertifier.certify_by_enumeration` certifies one
    budget by LP-ordered enumeration (measurement gate, design section 8 step 3).  Shared
    :class:`ScenarioLP` objects are switched to the certifier's target before every solve and
    each cut is tagged with the target the LP actually had.

gurobipy is imported lazily (like ``bilevel.py``).  English only.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

from .arcs import SINK
from .bilevel import (CACHE_VERSION, ERROR, INF, INFEASIBLE_ILP, INFEASIBLE_TERMINAL, NO_INCUMBENT,
                      SKIPPED_BUDGET, Layout, LowerLevelEvaluator, _md5, bd_stopped, materialise_schedule, option_grid)
from .costs import pricing_cache_component
from .evaluate import check as _check_schedule, cost as _cost_schedule
from .sites_nyc import ROLE_CHARGE, ROLE_SWAP, ROLES, SitingSpec, facility_id, layout_admissible, split_facility_id

__all__ = [
    "O2_VERSION", "M_EL", "LP_METHODS", "NO_ADMISSIBLE", "MenuEncoding", "LPResult", "ScenarioLP", "Cut", "CutPool", "Master",
    "PriceResult", "price_layout", "relax_and_round", "LPScreen", "SitingCertifier", "pool_signature",
    "cover_sets", "tolerance", "menu_layouts", "superset_trivial_bound", "enumeration_floor", "pool_bound",
    "PRICING_TIERS", "price_layout_parallel", "setup_min", "SubsetBranchAndBound", "subset_bound_value",
    "parse_ilp_params", "parse_cells", "cells_for_layout", "ub_check_all_candidates",
]

#: Version of the O2 cut-pool semantics (part of the pool signature).
O2_VERSION = "o2-1"
#: Re-solve algorithms of :class:`ScenarioLP` (``--lp-method`` of the CLI).
LP_METHODS = ("barrier", "dual", "concurrent")
#: Cost of the artificial / slack columns of the bound LP (design 2.4 a), USD per unit.
M_EL = 1e4
_EPS = 1e-9
#: Statuses of a lower-level row whose bound is final (no further solve can improve it).
_FINAL = ("OPTIMAL", INFEASIBLE_TERMINAL, INFEASIBLE_ILP, "INFEASIBLE", "INF_OR_UNBD")
#: Close reason of a budget whose master is infeasible (``LB = inf``: no admissible layout).
NO_ADMISSIBLE = "master infeasible (no admissible layout)"
#: R7 two-tier pricing (design 2.5): ``all_candidates`` rows feed cuts, ``LBIP`` and every
#: comparison table; ``open_sites`` rows (an upper bound on the all-candidates value) only ``UB``.
PRICING_TIERS = ("all_candidates", "open_sites")


def tolerance(ub: float, rel: float, abs_: float) -> float:
    """Gap tolerance ``max(rel UB, abs)`` (design 3.8: ``rel = 0.25 %``, ``abs = 1 USD``)."""
    if ub is None or not math.isfinite(ub):
        return float(abs_)
    return max(float(rel) * abs(float(ub)), float(abs_))


# ---------------------------------------------------------------------------
# menu encoding (design 3.1)
# ---------------------------------------------------------------------------
class MenuEncoding:
    """Menu binaries ``w_i``, ``i = (location, option)``, of the master.

    ``options`` = ``bilevel.option_grid(size_menu, roles)`` restricted to sizes valid under
    ``spec`` (7)-(8); ``objects`` = the role objects ``facility_id(l, r)`` of the master
    (``r in roles``).  ``y_(l,r) = sum_{o: r(o) = r} w_{l,o}``, ``B_(l,r) = sum B_o w_{l,o}``,
    ``C_(l,r) = sum C_o w_{l,o}``; ``inv_i`` = (33a) investment, ``setup_i`` = (27) setup cost."""

    def __init__(self, locations: Sequence[str], size_menu: Dict[str, Sequence[Tuple[int, int]]],
                 roles: Sequence[str], spec: SitingSpec, roles_of: Optional[Dict[str, Sequence[str]]] = None) -> None:
        self.locations: List[str] = [str(l) for l in locations]
        self.roles: Tuple[str, ...] = tuple(r for r in ROLES if r in roles)
        self.spec = spec
        self.options: List[Tuple[str, int, int]] = [o for o in option_grid(size_menu, self.roles)
                                                    if spec.valid_sizes(o[0], o[1], o[2])]
        if not self.options:
            raise ValueError("empty size menu")
        #: R7: roles allowed per location (``bilevel.LowerLevelEvaluator.roles_of``; hubs only at
        #: hub-capable sites); ``None`` = every role everywhere (unchanged encoding).
        self.roles_of: Dict[str, Tuple[str, ...]] = {l: (tuple(roles_of[l]) if roles_of and l in roles_of else self.roles)
                                                     for l in self.locations}
        self.index: List[Tuple[str, Tuple[str, int, int]]] = [(l, o) for l in self.locations for o in self.options
                                                              if o[0] in self.roles_of[l]]
        self.pos: Dict[Tuple[str, str, int, int], int] = {(l, o[0], o[1], o[2]): i for i, (l, o) in enumerate(self.index)}
        self.n = len(self.index)
        self.fid = [facility_id(l, o[0]) for l, o in self.index]
        self.loc = [l for l, _o in self.index]
        self.role = [o[0] for _l, o in self.index]
        self.Bo = np.array([float(o[1]) for _l, o in self.index])
        self.Co = np.array([float(o[2]) for _l, o in self.index])
        self.inv = np.array([spec.Fhat + spec.bhat * o[1] + spec.chat * o[2] for _l, o in self.index])
        self.setup = np.array([spec.setup_cost(o[0]) + spec.bB * o[1] + spec.bC * o[2] for _l, o in self.index])
        self.objects: List[str] = [facility_id(l, r) for l in self.locations for r in self.roles if r in self.roles_of[l]]
        self.by_fid: Dict[str, List[int]] = {}
        for i, f in enumerate(self.fid):
            self.by_fid.setdefault(f, []).append(i)
        self.swap_idx = [i for i in range(self.n) if ROLE_SWAP[self.role[i]]]
        self.charge_idx = [i for i in range(self.n) if ROLE_CHARGE[self.role[i]]]

    # -- layouts <-> w ------------------------------------------------------------------
    def contains(self, layout: Layout) -> bool:
        return all(it in self.pos for it in layout.open)

    def layout_w(self, layout: Layout) -> List[int]:
        """Indices ``i`` with ``w_i = 1`` (``KeyError`` when an item is not in the menu)."""
        return [self.pos[it] for it in layout.open]

    def w_of(self, layout: Layout) -> np.ndarray:
        w = np.zeros(self.n)
        w[self.layout_w(layout)] = 1.0
        return w

    def layout_of(self, w: Sequence[float]) -> Layout:
        return Layout.of([(self.loc[i],) + tuple(self.index[i][1]) for i in range(self.n) if w[i] > 0.5])

    def x_of(self, w: Sequence[float]) -> Dict[str, Tuple[float, float, float]]:
        """First-stage value ``{fid: (y, B, C)}`` of a (possibly fractional) ``w``."""
        out: Dict[str, List[float]] = {}
        for i in range(self.n):
            v = float(w[i])
            if abs(v) <= 1e-12:
                continue
            rec = out.setdefault(self.fid[i], [0.0, 0.0, 0.0])
            rec[0] += v
            rec[1] += self.Bo[i] * v
            rec[2] += self.Co[i] * v
        return {f: (r[0], r[1], r[2]) for f, r in out.items()}

    def x_of_layout(self, layout: Layout) -> Dict[str, Tuple[float, float, float]]:
        return {facility_id(l, r): (1.0, float(B), float(C)) for l, r, B, C in layout.open}

    def investment(self, layout: Layout) -> float:
        return layout.investment(self.spec)

    def setup_cost(self, layout: Layout) -> float:
        return layout.allocated_cost(self.spec)

    def lp_coeffs(self, beta: Dict[str, float]) -> np.ndarray:
        """Coefficients on ``w`` of ``beta^y y + beta^B B + beta^C C`` (``beta`` keyed ``'y|fid'``)."""
        a = np.zeros(self.n)
        for i in range(self.n):
            f = self.fid[i]
            a[i] = beta.get("y|" + f, 0.0) + self.Bo[i] * beta.get("B|" + f, 0.0) + self.Co[i] * beta.get("C|" + f, 0.0)
        return a

    def hamming(self, layout_key: str) -> Optional[Tuple[float, np.ndarray]]:
        """``d(w, what) = const + a . w`` of the Hamming distance to a menu layout; ``None`` when
        the layout is not representable in this menu."""
        try:
            lay = Layout.from_key(layout_key)
            ones = self.layout_w(lay)
        except (KeyError, ValueError):
            return None
        a = np.ones(self.n)
        a[ones] = -1.0
        return float(len(ones)), a


# ---------------------------------------------------------------------------
# scenario LP (design 2.1, 2.2, 2.4 a; C1, C2, C12, C13, C16)
# ---------------------------------------------------------------------------
@dataclass
class LPResult:
    """One solve of :class:`ScenarioLP` at a first-stage value ``x``."""
    scenario: int
    status: str
    Qt: Optional[float]                     # ObjVal of the elastic LP (log only)
    Qs: Optional[float]                     # safe value c0 + beta . x (a valid lower bound)
    c0: Optional[float]
    beta: Dict[str, float]
    artificial: float = 0.0
    slack: float = 0.0
    usage: Dict[str, Dict[str, float]] = field(default_factory=dict)
    runtime_s: float = 0.0
    iterations: float = 0.0
    audit: Dict[str, Any] = field(default_factory=dict)
    relaxed: Optional[bool] = None          # end-target state of the LP at this solve (cut tag)
    method: str = ""                        # LP algorithm actually used for this solve

    def value_at(self, x: Dict[str, Tuple[float, float, float]]) -> Optional[float]:
        if self.c0 is None:
            return None
        return self.c0 + sum(b * _x_component(x, k) for k, b in self.beta.items())


def _x_component(x: Dict[str, Tuple[float, float, float]], key: str) -> float:
    kind, fid = key.split("|", 1)
    v = x.get(fid)
    if v is None:
        return 0.0
    return float(v[{"y": 0, "B": 1, "C": 2}[kind]])


class ScenarioLP:
    """Persistent bound LP of scenario ``s`` on the evaluator's all-candidates template.

    Parameters: ``evaluator`` (its ``template(s)``; no ``variant``), ``s``, ``M_el`` (artificial
    and slack cost), ``threads``, ``relaxed`` (initial target), ``first_method`` (Gurobi
    ``Method`` of the first solve under ``method='dual'``), ``method`` (re-solve algorithm, see
    :data:`LP_METHODS`), ``names`` (row names; default as ``ILPModel``).

    ``method``: ``'barrier'`` (default) solves EVERY point from scratch with presolve, barrier and
    crossover (``LPWarmStart 0``: the basis of the previous point is ignored; on the Manhattan
    LPs a cold barrier solve took about 16 s where the warm dual simplex needed 160-1,360 s,
    see ``notes/o2_manhattan_first_pass.md``); ``'dual'`` is the original protocol (first solve
    barrier + crossover, re-solves dual simplex warm-started from the retained basis, now with
    ``LPWarmStart 2`` so that presolve runs); ``'concurrent'`` is Gurobi ``Method 3``.  The cut
    is the safe Lagrangian cut of C1 whatever the method (valid for any optimal duals)."""

    def __init__(self, evaluator: LowerLevelEvaluator, s: int, *, M_el: float = M_EL, threads: int = 1,
                 relaxed: bool = False, first_method: int = 2, names: Optional[bool] = None,
                 method: str = "barrier") -> None:
        import gurobipy as gp
        from gurobipy import GRB

        from . import ilp

        if evaluator.variant:
            raise ValueError("ScenarioLP: evaluator variants (A4 levers) are not supported by the O2 bound")
        t0 = time.perf_counter()
        inst, lib = evaluator.template(s)
        if inst.options.get("forced_transfers"):
            raise ValueError("ScenarioLP: forced transfers are applied by build_model only (C12)")
        if lib.has_dummy_terminal:
            raise ValueError("ScenarioLP: dummy terminal arcs are not allowed in a siting template (C12)")
        self.s = int(s)
        self.inst = inst
        self.M_el = float(M_el)
        self.first_method = int(first_method)
        self.set_method(method)
        self.n_solves = 0
        self.env = gp.Env(empty=True)
        self.env.setParam("OutputFlag", 0)
        self.env.start()
        m = gp.Model(f"o2_lp_s{s}", env=self.env)
        m.Params.OutputFlag = 0
        m.Params.Threads = int(threads)
        m.Params.Seed = 0
        m.Params.FeasibilityTol = 1e-7
        m.Params.OptimalityTol = 1e-7
        self.model = m
        self.fids = [f.id for f in inst.facilities]
        Yc = {j: m.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"Yc[{j}]") for j in self.fids}
        Bc = {j: m.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"Bc[{j}]") for j in self.fids}
        Cc = {j: m.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"Cc[{j}]") for j in self.fids}
        self.Yc, self.Bc, self.Cc = Yc, Bc, Cc
        sub = ilp.build_submodel(inst, lib, m, facility_vars=(Yc, Bc, Cc), prefix=f"s{s}_", aggregate=True,
                                 keep_rows=True, names=names)
        self.sub = sub
        m.update()
        # ---- (C2) artificial source -> SINK columns and bounded slacks on (17), (18)
        flow = sub.rows.get("(5)", {})
        art: List[Any] = []
        for com in sub.agg.commodities:
            sink_row = flow[f"flow[c{com.id},{SINK}]"]
            for w, mcw in com.supply.items():
                if mcw <= 0:
                    continue
                src_row = flow[f"flow[c{com.id},{w}]"]
                art.append(m.addVar(lb=0.0, ub=float(mcw), name="",
                                    column=gp.Column([1.0, -1.0], [src_row, sink_row])))
        slacks: List[Any] = []
        self.end_local: Dict[str, Any] = {}
        for label, row in sub.rows.get("(17)", {}).items():
            j = label[len("end_local["):-1]
            self.end_local[j] = row
            R = float(inst.facility(j).R_end)
            if R > 0:
                slacks.append(m.addVar(lb=0.0, ub=R, column=gp.Column([1.0], [row])))
        self.end_share = sub.rows.get("(18)", {}).get("end_share")
        if self.end_share is not None and inst.rho > 0:
            ub = float(inst.rho) * sum(float(inst.facility(j).K) for j in inst.N)
            slacks.append(m.addVar(lb=0.0, ub=ub, column=gp.Column([1.0], [self.end_share])))
        self.art, self.slacks = art, slacks
        comp = sub.components
        opex = gp.quicksum(expr for name, expr in comp.items() if name != "C_setup")
        m.setObjective(opex + self.M_el * (gp.quicksum(art) + gp.quicksum(slacks)), GRB.MINIMIZE)
        # ---- fixing rows
        self.fix: Dict[str, Any] = {}
        for j in self.fids:
            self.fix["y|" + j] = m.addLConstr(Yc[j], GRB.EQUAL, 0.0)
            self.fix["B|" + j] = m.addLConstr(Bc[j], GRB.EQUAL, 0.0)
            self.fix["C|" + j] = m.addLConstr(Cc[j], GRB.EQUAL, 0.0)
        m.update()
        vars_ = m.getVars()
        m.setAttr("VType", vars_, [GRB.CONTINUOUS] * len(vars_))
        m.update()
        self.vars = vars_
        self.constrs = m.getConstrs()
        self.copy_keys = list(self.fix.keys())
        copy_var = {**{"y|" + j: Yc[j] for j in self.fids}, **{"B|" + j: Bc[j] for j in self.fids},
                    **{"C|" + j: Cc[j] for j in self.fids}}
        self.copy_idx = np.array([copy_var[k].index for k in self.copy_keys], dtype=int)
        self.fix_rows = np.array([self.fix[k].index for k in self.copy_keys], dtype=int)
        ncols = len(vars_)
        mask = np.ones(ncols, dtype=bool)
        mask[self.copy_idx] = False
        self.noncopy = mask
        self.q = np.asarray(m.getAttr("Obj", vars_), dtype=float)
        self.lb = np.asarray(m.getAttr("LB", vars_), dtype=float)
        self.ub = np.asarray(m.getAttr("UB", vars_), dtype=float)
        if not (np.all(np.isfinite(self.lb[mask])) and np.all(np.isfinite(self.ub[mask]))
                and np.all(np.abs(self.ub[mask]) < 1e20) and np.all(np.abs(self.lb[mask]) < 1e20)):
            raise AssertionError("ScenarioLP: every non-copy column needs finite bounds (C1)")
        if np.any(self.q[mask] < -1e-12):
            raise AssertionError("ScenarioLP: negative objective coefficient (C13)")
        sense = m.getAttr("Sense", self.constrs)
        self.le = np.array([c == "<" for c in sense])
        self.ge = np.array([c == ">" for c in sense])
        self.b = np.asarray(m.getAttr("RHS", self.constrs), dtype=float)
        self._A = None
        self.relaxed = False
        if relaxed:
            self.set_target(True)
        self._usage_index()
        self.build_s = time.perf_counter() - t0
        self.size = {"n_cols": ncols, "n_rows": len(self.constrs), "n_nonzeros": int(m.NumNZs),
                     "n_artificial": len(art), "n_slack": len(slacks), "n_agg_arcs": len(sub.agg),
                     "build_s": self.build_s}

    # -- structure ---------------------------------------------------------------
    def _usage_index(self) -> None:
        sub, inst = self.sub, self.inst
        L, H = inst.L, inst.H
        swap: Dict[str, List[int]] = {}
        term: Dict[str, List[int]] = {}
        for a in sub.agg.arcs:
            if a.kind == "swap" and a.fac is not None:
                swap.setdefault(a.fac, []).append(sub.x[a.id].index)
            elif a.kind == "term" and a.fac is not None:
                term.setdefault(a.fac, []).append(sub.x[a.id].index)
        charge: Dict[str, Dict[int, List[int]]] = {}
        for (j, _q, t), v in sub.c.items():
            charge.setdefault(j, {}).setdefault(t, []).append(v.index)
        nL: Dict[str, List[int]] = {j: [sub.n[j, L, t].index for t in range(H + 1)] for j in self.fids}
        ship: Dict[str, List[int]] = {}
        recv: Dict[str, List[int]] = {}
        for (e, _q), v in sub.z.items():
            svc = inst.service(e)
            ship.setdefault(svc.o_fac, []).append(v.index)
            recv.setdefault(svc.d_fac, []).append(v.index)
        self._idx = {"swap": swap, "term": term, "charge": charge, "nL": nL, "ship": ship, "recv": recv}
        self._art_idx = np.array([v.index for v in self.art], dtype=int)
        self._slack_idx = np.array([v.index for v in self.slacks], dtype=int)

    def _matrix(self) -> Any:
        if self._A is None:
            self.model.update()
            self._A = self.model.getA().tocsr()
        return self._A

    def set_target(self, relaxed: bool) -> None:
        """Written (``relaxed=False``) or relaxed (``rho = R_end = 0``) end targets (17)-(18) by
        coefficient changes of the copies (design 2.1); the slacks keep their bounds."""
        relaxed = bool(relaxed)
        if relaxed == self.relaxed:
            return
        m = self.model
        for j, row in self.end_local.items():
            m.chgCoeff(row, self.Yc[j], 0.0 if relaxed else -float(self.inst.facility(j).R_end))
        if self.end_share is not None:
            for j in self.fids:
                m.chgCoeff(self.end_share, self.Bc[j], 0.0 if relaxed else -float(self.inst.rho))
        m.update()
        self._A = None
        self.relaxed = relaxed

    # -- solve ------------------------------------------------------------------
    def set_method(self, method: str) -> None:
        """Choose the re-solve algorithm (``'barrier'``, ``'dual'`` or ``'concurrent'``)."""
        method = str(method).lower()
        if method not in LP_METHODS:
            raise ValueError(f"ScenarioLP method {method!r}; choose one of {sorted(LP_METHODS)}")
        self.method = method

    def _apply_method(self) -> str:
        """Set the Gurobi parameters of the next solve; returns the label recorded in the result."""
        m = self.model
        if self.method == "dual":
            if self.n_solves == 0:
                m.Params.Method = self.first_method
                m.Params.LPWarmStart = 1
                return f"method{self.first_method}-cold"
            m.Params.Method = 1
            m.Params.LPWarmStart = 2            # crush the retained basis into the presolved model
            return "dual-warm"
        if self.method == "concurrent":
            m.Params.Method = 3
            m.Params.LPWarmStart = 0            # from scratch: presolve, barrier / simplex race
            return "concurrent-cold"
        m.Params.Method = 2                     # barrier + crossover (exact Pi and a basis)
        m.Params.LPWarmStart = 0                # ignore the previous basis: presolve + barrier run
        return "barrier-cold"

    def solve(self, x: Dict[str, Tuple[float, float, float]], audit: bool = False) -> LPResult:
        """Solve at ``x = {fid: (y, B, C)}`` (objects absent from ``x`` are closed) and return the
        safe cut of C1 (``c0``, ``beta``) and its value ``Qs`` at ``x``."""
        from gurobipy import GRB

        m = self.model
        vals = [_x_component(x, k) for k in self.copy_keys]
        m.setAttr("RHS", [self.fix[k] for k in self.copy_keys], vals)
        label = self._apply_method()
        t0 = time.perf_counter()
        m.optimize()
        if m.Status != GRB.OPTIMAL:
            # retry once without presolve and with numeric care
            m.Params.Presolve = 0
            m.Params.NumericFocus = 2
            m.reset()
            m.optimize()
            m.Params.Presolve = -1
            m.Params.NumericFocus = 0
            label += "+retry"
        self.n_solves += 1
        rt = time.perf_counter() - t0
        from .ilp import status_name
        st = status_name(m.Status)
        if m.Status != GRB.OPTIMAL:
            return LPResult(self.s, st, None, None, None, {}, runtime_s=rt, relaxed=self.relaxed, method=label)
        pi_raw = np.asarray(m.getAttr("Pi", self.constrs), dtype=float)
        pi_fix = pi_raw[self.fix_rows].copy()
        c0, beta_vec = self.cut_from_pi(pi_raw)
        xv = np.asarray(vals, dtype=float)
        Qs = c0 + float(beta_vec @ xv)
        Qt = float(m.ObjVal)
        beta = self.beta_dict(beta_vec)
        X = np.asarray(m.getAttr("X", self.vars), dtype=float)
        res = LPResult(self.s, st, Qt, Qs, c0, beta, runtime_s=rt, iterations=float(m.IterCount), relaxed=self.relaxed,
                       method=label)
        res.artificial = float(X[self._art_idx].sum()) if len(self._art_idx) else 0.0
        res.slack = float(X[self._slack_idx].sum()) if len(self._slack_idx) else 0.0
        res.usage = self._usage(X, x)
        res.audit = {"Qt_minus_Qs": Qt - Qs}
        if audit:
            rcv = np.asarray(m.getAttr("RC", [self.vars[i] for i in self.copy_idx]), dtype=float)
            res.audit.update(max_copy_rc=float(np.max(np.abs(rcv))) if len(rcv) else 0.0,
                             max_beta_vs_fix_pi=float(np.max(np.abs(beta_vec - pi_fix) / (1.0 + np.abs(beta_vec))))
                             if len(beta_vec) else 0.0)
        return res

    def solve_subset(self, atoms: Iterable[str], audit: bool = False) -> LPResult:
        """R7 regional bound (design 2.3 as corrected in 7.1): every role object of every location
        in ``atoms`` open (``y = 1``) with FREE sizes (``B`` in ``[0, K]``, ``C`` in ``[c_min,
        c_max]``, the box of :meth:`bilevel.LowerLevelEvaluator.superset_bound`), everything else
        closed, relaxed targets (asserted).  The ``B`` / ``C`` fixing rows of the open objects are
        made vacuous (coefficient 0) and the copies bounded instead; after the solve the rows and
        the infinite bounds are restored.  The safe value is the box minimum of the C1 cut over the
        free copies: ``Qs = c0 + sum_A beta_y + sum_A min(beta_B lb, beta_B ub) + sum_A min(beta_C
        lb, beta_C ub)``: by weak duality a lower bound on the LP with those boxes, hence on the LP
        and ILP value of every layout whose open locations lie in ``atoms`` (free sizes relax every
        fixed size; closed objects coincide; relaxed OPEX is non-increasing in the open set).  The
        cut returned (``c0``, ``beta``) is the ordinary C1 cut (valid at every ``x``); ``Qs`` is the
        regional bound and ``audit['boxes']`` the boxes used."""
        from gurobipy import GRB

        if not self.relaxed:
            raise AssertionError("solve_subset needs relaxed end targets (the regional bound is not valid for written targets)")
        A = {str(a) for a in atoms}
        m = self.model
        boxes: Dict[str, Tuple[float, float]] = {}
        rhs_keys, rhs_vals = [], []
        touched: List[Tuple[str, Any, Any]] = []
        for j in self.fids:
            loc, role = split_facility_id(j)
            inside = loc in A
            rhs_keys.append(self.fix["y|" + j]); rhs_vals.append(1.0 if inside else 0.0)
            if inside:
                f = self.inst.facility(j)
                bB = (0.0, float(f.K))
                cmin = 1.0 if (role == "C") else 0.0
                bC = (cmin, float(min(f.Cbar, f.K))) if f.charge else (0.0, 0.0)
                for kind, var, box in (("B", self.Bc[j], bB), ("C", self.Cc[j], bC)):
                    row = self.fix[kind + "|" + j]
                    m.chgCoeff(row, var, 0.0)            # the row becomes 0 = 0 (RHS reset below)
                    rhs_keys.append(row); rhs_vals.append(0.0)
                    var.LB, var.UB = box
                    boxes[kind + "|" + j] = box
                    touched.append((kind + "|" + j, row, var))
            else:
                rhs_keys.append(self.fix["B|" + j]); rhs_vals.append(0.0)
                rhs_keys.append(self.fix["C|" + j]); rhs_vals.append(0.0)
        m.setAttr("RHS", rhs_keys, rhs_vals)
        label = self._apply_method() + "-subset"
        t0 = time.perf_counter()
        try:
            m.optimize()
            if m.Status != GRB.OPTIMAL:
                m.Params.Presolve = 0
                m.Params.NumericFocus = 2
                m.reset()
                m.optimize()
                m.Params.Presolve = -1
                m.Params.NumericFocus = 0
                label += "+retry"
            self.n_solves += 1
            rt = time.perf_counter() - t0
            from .ilp import status_name
            st = status_name(m.Status)
            if m.Status != GRB.OPTIMAL:
                return LPResult(self.s, st, None, None, None, {}, runtime_s=rt, relaxed=self.relaxed, method=label)
            pi_raw = np.asarray(m.getAttr("Pi", self.constrs), dtype=float)
            c0, beta_vec = self.cut_from_pi(pi_raw)
            Qt = float(m.ObjVal)
            iters = float(m.IterCount)
            X = np.asarray(m.getAttr("X", self.vars), dtype=float)
        finally:
            for _k, row, var in touched:
                m.chgCoeff(row, var, 1.0)
                var.LB, var.UB = -GRB.INFINITY, GRB.INFINITY
            m.update()
        # box minimum of the cut over the free copies
        Qs = c0
        for k, b in zip(self.copy_keys, beta_vec):
            kind, j = k.split("|", 1)
            if split_facility_id(j)[0] not in A:
                continue
            if kind == "y":
                Qs += float(b)
            else:
                lo, hi = boxes[k]
                Qs += min(float(b) * lo, float(b) * hi)
        beta = self.beta_dict(beta_vec)
        res = LPResult(self.s, st, Qt, float(Qs), c0, beta, runtime_s=rt, iterations=iters,
                       relaxed=self.relaxed, method=label)
        res.artificial = float(X[self._art_idx].sum()) if len(self._art_idx) else 0.0
        res.slack = float(X[self._slack_idx].sum()) if len(self._slack_idx) else 0.0
        res.audit = {"Qt_minus_Qs": Qt - Qs, "atoms": sorted(A), "boxes": {k: list(v) for k, v in boxes.items()}}
        return res

    def cut_from_pi(self, pi_raw: np.ndarray) -> Tuple[float, np.ndarray]:
        """Safe Lagrangian cut (C1) from ANY row multipliers: the fixing rows are dropped, the
        others projected to the dual sign of a minimisation (``<=``: ``min(Pi, 0)``, ``>=``:
        ``max(Pi, 0)``), the reduced costs recomputed exactly, and
        ``theta_s >= c0 + beta . x`` with ``c0 = Pi . h + sum_v min(rc_v l_v, rc_v u_v)`` over the
        non-copy columns and ``beta = -T^T Pi`` on the copies.  Weak duality makes it valid for
        every ``x``, whatever the accuracy of ``Pi``.  Returns ``(c0, beta in copy_keys order)``."""
        A = self._matrix()
        pi = np.array(pi_raw, dtype=float, copy=True)
        pi[self.fix_rows] = 0.0
        pi = np.where(self.le, np.minimum(pi, 0.0), pi)
        pi = np.where(self.ge, np.maximum(pi, 0.0), pi)
        At_pi = A.T @ pi
        rc = self.q - At_pi
        nc = self.noncopy
        term = np.minimum(rc[nc] * self.lb[nc], rc[nc] * self.ub[nc])
        c0 = float(pi @ self.b + term.sum())
        return c0, -At_pi[self.copy_idx]

    def beta_dict(self, beta_vec: np.ndarray) -> Dict[str, float]:
        return {k: float(b) for k, b in zip(self.copy_keys, beta_vec) if abs(b) > 1e-12}

    def x_vector(self, x: Dict[str, Tuple[float, float, float]]) -> np.ndarray:
        return np.asarray([_x_component(x, k) for k in self.copy_keys], dtype=float)

    def _usage(self, X: np.ndarray, x: Dict[str, Tuple[float, float, float]]) -> Dict[str, Dict[str, float]]:
        idx = self._idx
        out: Dict[str, Dict[str, float]] = {}
        for j in self.fids:
            y, B, C = x.get(j, (0.0, 0.0, 0.0))
            ch = idx["charge"].get(j, {})
            nl = X[idx["nL"][j]]
            rec = {
                "y": float(y), "B": float(B), "C": float(C),
                "swap": float(X[idx["swap"].get(j, [])].sum()) if idx["swap"].get(j) else 0.0,
                "term": float(X[idx["term"].get(j, [])].sum()) if idx["term"].get(j) else 0.0,
                "charge": float(sum(X[ids].sum() for ids in ch.values())),
                "charge_peak": float(max((X[ids].sum() for ids in ch.values()), default=0.0)),
                "ship": float(X[idx["ship"].get(j, [])].sum()) if idx["ship"].get(j) else 0.0,
                "recv": float(X[idx["recv"].get(j, [])].sum()) if idx["recv"].get(j) else 0.0,
                "draw": float(nl[0] - nl.min()) if len(nl) else 0.0,
            }
            if any(abs(v) > 1e-9 for v in rec.values()):
                out[j] = rec
        return out

    def release_library(self) -> None:
        """R7 memory lifecycle (production plan 5 item 2): drop the references to the per-bike
        template library that the model build keeps (``sub.lib``, ``sub.lib_original``,
        ``sub.agg.lib``).  Every solve, cut and usage record uses the model, its row objects
        and the index built in ``__init__`` only, so the results are unchanged; an evicted
        template (:meth:`bilevel.LowerLevelEvaluator.evict_template`) can then be freed while
        the LP lives."""
        sub = getattr(self, "sub", None)
        for obj, attr in ((sub, "lib"), (sub, "lib_original"), (getattr(sub, "agg", None), "lib")):
            if obj is not None and hasattr(obj, attr):
                setattr(obj, attr, None)

    def dispose(self) -> None:
        try:
            self.model.dispose()
            self.env.dispose()
        except Exception:  # noqa: BLE001
            pass


class ScenarioLPSet:
    """R7 memory lifecycle (production plan 5 item 2): the scenario LPs of a certifier, built
    LAZILY on first use and disposable between phases.

    ``get(s)`` (also ``lps[s]``) builds the :class:`ScenarioLP` of scenario ``s`` when it is
    missing (``threads``, ``method``, ``M_el``, initial target ``relaxed``); :meth:`dispose`
    frees the built ones (model, environment), and a later ``get`` rebuilds the LP from the
    same template with the same model, so every solve, cut and bound is identical (nothing of
    an LP survives a solve except its result).  With ``evict_templates=True`` the evaluator's
    template of scenario ``s`` is evicted right after its LP is built
    (:meth:`ScenarioLP.release_library` drops the LP's references to it), so an LP pass holds
    one template at a time; pricing rebuilds a template when it needs one (identical library).
    ``len`` is the number of scenarios; iterating builds EVERY LP (:meth:`built` lists the
    built ones only).  ``on_build(s, lp)`` is called after each build."""

    def __init__(self, evaluator: LowerLevelEvaluator, *, M_el: float = M_EL, threads: int = 1,
                 method: str = "barrier", relaxed: bool = False, evict_templates: bool = False,
                 on_build: Optional[Callable[[int, "ScenarioLP"], None]] = None) -> None:
        self.ev = evaluator
        self.S = int(evaluator.n_scenarios)
        self.M_el = float(M_el)
        self.threads = int(threads)
        self.method = str(method)
        self.relaxed = bool(relaxed)
        self.evict_templates = bool(evict_templates)
        self.on_build = on_build
        self._lps: Dict[int, ScenarioLP] = {}
        self._lock = threading.RLock()
        self.n_built = 0
        self.n_disposed = 0
        self.build_s = 0.0

    def __len__(self) -> int:
        return self.S

    def get(self, s: int) -> "ScenarioLP":
        s = int(s)
        if not 0 <= s < self.S:
            raise IndexError(f"scenario {s} out of range 0..{self.S - 1}")
        with self._lock:
            lp = self._lps.get(s)
            if lp is None:
                lp = ScenarioLP(self.ev, s, M_el=self.M_el, threads=self.threads, method=self.method,
                                relaxed=self.relaxed)
                if self.evict_templates:
                    lp.release_library()
                    self.ev.evict_template(s)
                self._lps[s] = lp
                self.n_built += 1
                self.build_s += float(lp.build_s)
                if self.on_build is not None:
                    self.on_build(s, lp)
            return lp

    def __getitem__(self, s: int) -> "ScenarioLP":
        return self.get(s)

    def __iter__(self):
        return (self.get(s) for s in range(self.S))

    def is_built(self, s: int) -> bool:
        return int(s) in self._lps

    def built(self) -> List["ScenarioLP"]:
        with self._lock:
            return [self._lps[s] for s in sorted(self._lps)]

    def dispose(self, scenarios: Optional[Iterable[int]] = None) -> int:
        """Dispose the built LPs of ``scenarios`` (default all); returns the number disposed."""
        with self._lock:
            keys = sorted(self._lps) if scenarios is None else sorted({int(s) for s in scenarios} & set(self._lps))
            for s in keys:
                self._lps.pop(s).dispose()
            self.n_disposed += len(keys)
            return len(keys)


# ---------------------------------------------------------------------------
# cuts and the pool (design 2.2, 2.4 c, 3.4, 3.7)
# ---------------------------------------------------------------------------
@dataclass
class Cut:
    """One master cut.  ``kind``: ``'lp'`` (``theta_s >= c0 + beta . x``), ``'lshaped'``
    (``theta_s >= LBIP - (LBIP - L) d(w, what)``), ``'lifted'`` (``theta_s >= c0 + beta . x +
    Delta (1 - d(w, what))``), ``'nogood'`` (``d(w, what) >= 1``), ``'terminal'``
    (``sum_{j in objects} y_j >= 1``).  ``target``: ``'relaxed'``, ``'written'`` or ``'both'``."""
    kind: str
    target: str
    scenario: Optional[int] = None
    c0: float = 0.0
    beta: Dict[str, float] = field(default_factory=dict)
    what: Optional[str] = None
    LBIP: float = 0.0
    L: float = 0.0
    Delta: float = 0.0
    objects: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {"kind": self.kind, "target": self.target, "scenario": self.scenario, "c0": self.c0,
                "beta": self.beta, "what": self.what, "LBIP": self.LBIP, "L": self.L, "Delta": self.Delta,
                "objects": self.objects, "meta": self.meta}

    @classmethod
    def from_json(cls, d: Dict[str, Any]) -> "Cut":
        return cls(kind=d["kind"], target=d["target"], scenario=d.get("scenario"), c0=float(d.get("c0", 0.0)),
                   beta={k: float(v) for k, v in (d.get("beta") or {}).items()}, what=d.get("what"),
                   LBIP=float(d.get("LBIP", 0.0)), L=float(d.get("L", 0.0)), Delta=float(d.get("Delta", 0.0)),
                   objects=list(d.get("objects") or []), meta=dict(d.get("meta") or {}))

    @property
    def is_theta(self) -> bool:
        return self.kind in ("lp", "lshaped", "lifted", "subset")

    def applies_to(self, target: str) -> bool:
        """One-way import (C16): relaxed cuts serve the written problem, never the reverse."""
        return self.target in ("both", target) or (target == "written" and self.target == "relaxed")

    def linear(self, enc: MenuEncoding) -> Optional[Tuple[float, np.ndarray]]:
        """``(const, a)``: for theta cuts ``theta_s >= const + a . w``; for row cuts
        ``a . w >= const``.  ``None`` when not representable in ``enc`` (then it is skipped)."""
        if self.kind == "lp":
            return float(self.c0), enc.lp_coeffs(self.beta)
        if self.kind == "subset":
            # R7 regional bound (design 2.3): theta_s >= LBA - (LBA - L) sum_{l not in A} sum_o w_{l,o}
            atoms = set(self.meta.get("atoms") or [])
            lba = max(float(self.c0), float(self.L))
            a = np.zeros(enc.n)
            for i in range(enc.n):
                if enc.loc[i] not in atoms:
                    a[i] = -(lba - float(self.L))
            return lba, a
        if self.kind == "terminal":
            a = np.zeros(enc.n)
            objs = set(self.objects)
            for i in range(enc.n):
                if enc.fid[i] in objs:
                    a[i] = 1.0
            return 1.0, a
        ham = enc.hamming(self.what) if self.what else None
        if ham is None:
            return None
        hc, ha = ham
        if self.kind == "nogood":
            return 1.0 - hc, ha
        if self.kind == "lshaped":
            k = self.LBIP - self.L
            return self.LBIP - k * hc, -k * ha
        if self.kind == "lifted":
            return float(self.c0) + self.Delta * (1.0 - hc), enc.lp_coeffs(self.beta) - self.Delta * ha
        raise ValueError(f"unknown cut kind {self.kind!r}")


def pool_signature(evaluator: LowerLevelEvaluator, M_el: float = M_EL) -> str:
    """Signature of a cut pool (design 3.7): the cuts are valid for these scenarios, prices,
    spec, library convention and bound LP; the target is stored per cut."""
    parts = {"o2": O2_VERSION, "cache": CACHE_VERSION, "family": evaluator.family, "seeds": evaluator.seeds,
             "demand": evaluator.demand_md5, "prices": [pricing_cache_component(i) for i in evaluator.scenarios],
             "spec": evaluator.spec.to_dict(), "pruning": [evaluator.pruning_signature(s) for s in range(evaluator.n_scenarios)],
             "reposition": evaluator.reposition, "lp": "aggregated", "M_el": float(M_el)}
    roles_sig = evaluator.roles_signature() if hasattr(evaluator, "roles_signature") else None
    if roles_sig is not None:                    # R7: hub-capable set, only when some location lacks C
        parts["roles_of"] = roles_sig
    return _md5(parts)


def feasibility_signature(evaluator: LowerLevelEvaluator) -> str:
    """R7 (production plan 5 item 4): key of a one-site terminal-feasibility screen.  The cut-pool
    signature (scenarios, demand hashes, prices, spec, arc-builder options including the
    approach radius and its start-state exemption, library convention, hub-capable set) plus
    the candidate nodes: a screen written under the same key is a proof for this configuration
    (terminal reachability depends on the template library and the bikes only)."""
    return _md5({"kind": "one_site_terminal", "pool": pool_signature(evaluator),
                 "nodes": sorted([str(k), str(v)] for k, v in evaluator.cand_node.items())})


def verify_terminal_infeasible(evaluator: LowerLevelEvaluator, layout: Layout, s: int) -> List[str]:
    """Bikes of scenario ``s`` without a reachable terminal arc (9) in the library of ``layout``
    under the evaluator's convention (a library build, no solve; the check behind
    ``INFEASIBLE_TERMINAL`` in :meth:`bilevel.LowerLevelEvaluator.evaluate_scenario`).  Empty
    when every bike can end its shift."""
    if evaluator.reposition != "all_candidates":
        raise ValueError("terminal feasibility screens use the all-candidates convention")
    _inst, lib = evaluator.layout_pair(layout, int(s))
    return [str(b) for b in lib.infeasible_bikes]


def _cut_hash(cut: Cut) -> str:
    d = cut.to_json()
    meta = d.pop("meta", None) or {}
    if cut.kind == "subset":                     # R7: the atom set is part of the cut's identity
        d["atoms"] = sorted(str(a) for a in meta.get("atoms") or [])
    d["beta"] = {k: round(v, 9) for k, v in sorted(d["beta"].items())}
    for k in ("c0", "LBIP", "L", "Delta"):
        d[k] = round(float(d[k]), 9)
    return _md5(d)


class CutPool:
    """Append-only cut store (``cuts.jsonl``; first line = header with the signature).  A pool
    whose signature differs is moved aside (``.stale``) and a new one is started.  Lines that do
    not parse (a half-written last line while another process appends) are skipped and counted
    in ``n_skipped``.  ``read_only=True`` never writes (no header, no ``.stale`` move, ``add``
    keeps the cut in memory only); a signature mismatch then raises."""

    def __init__(self, path: Optional[str], signature: str, read_only: bool = False) -> None:
        self.path = path
        self.signature = signature
        self.read_only = bool(read_only)
        self.cuts: List[Cut] = []
        self._seen: Set[str] = set()
        self.n_skipped = 0
        if path:
            if not self.read_only:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    lines = [ln for ln in fh.read().splitlines() if ln.strip()]
                head: Dict[str, Any] = {}
                if lines:
                    try:
                        head = json.loads(lines[0])
                    except ValueError:
                        head = {}
                if head.get("signature") == signature:
                    self.load_lines(lines[1:])
                elif self.read_only:
                    raise ValueError(f"cut pool {path}: signature {head.get('signature')!r} differs from {signature!r}")
                else:
                    os.replace(path, path + f".stale{int(time.time())}")
            elif self.read_only:
                raise FileNotFoundError(path)
            if not self.read_only and not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(json.dumps({"header": True, "signature": signature, "o2": O2_VERSION}) + "\n")

    def load_lines(self, lines: Iterable[str]) -> int:
        """Parse cut lines into the pool (in memory; duplicates and malformed lines skipped).
        Returns the number of cuts added."""
        n = 0
        for ln in lines:
            try:
                c = Cut.from_json(json.loads(ln))
            except (ValueError, KeyError, TypeError):
                self.n_skipped += 1
                continue
            h = _cut_hash(c)
            if h not in self._seen:
                self._seen.add(h)
                self.cuts.append(c)
                n += 1
        return n

    def add(self, cut: Cut) -> bool:
        """Store a cut; ``False`` when an identical cut is already in the pool (not stored)."""
        h = _cut_hash(cut)
        if h in self._seen:
            return False
        self._seen.add(h)
        self.cuts.append(cut)
        if self.path and not self.read_only:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(cut.to_json()) + "\n")
        return True

    def counts(self, target: Optional[str] = None) -> Dict[str, int]:
        """Number of cuts by ``kind:target`` (those applying to ``target`` when given)."""
        out: Dict[str, int] = {}
        for c in self.cuts:
            if target is not None and not c.applies_to(target):
                continue
            k = f"{c.kind}:{c.target}"
            out[k] = out.get(k, 0) + 1
        return out

    def for_target(self, target: str) -> List[Cut]:
        return [c for c in self.cuts if c.applies_to(target)]


# ---------------------------------------------------------------------------
# a-priori terminal cover rows (design 2.4 b)
# ---------------------------------------------------------------------------
def cover_sets(evaluator: LowerLevelEvaluator, objects: Iterable[str]) -> List[Tuple[int, Any, Tuple[str, ...]]]:
    """Per scenario and bike: the swap objects whose terminal arc (9) is reachable from the bike's
    source in the all-candidates template (explicit forward pass), restricted to ``objects``.
    ``sum_{j in R_k^s} y_j >= 1`` is a valid master row (``subset_library`` only removes arcs)."""
    objs = set(objects)
    out: List[Tuple[int, Any, Tuple[str, ...]]] = []
    for s in range(evaluator.n_scenarios):
        inst, lib = evaluator.template(s)
        for b in inst.bikes:
            arcs = lib.arcs_of(b.id)
            by_src: Dict[Any, List[Any]] = {}
            for a in arcs:
                by_src.setdefault(a.src, []).append(a)
            src = lib.source(b.id)
            seen = {src}
            stack = [src]
            while stack:
                st = stack.pop()
                for a in by_src.get(st, ()):
                    if a.dst not in seen:
                        seen.add(a.dst)
                        stack.append(a.dst)
            facs = sorted({a.fac for a in arcs if a.kind == "term" and a.fac is not None and a.src in seen} & objs)
            out.append((s, b.id, tuple(facs)))
    return out


# ---------------------------------------------------------------------------
# master (design 3.1-3.3)
# ---------------------------------------------------------------------------
class Master:
    """Master MIP over the menu binaries with ``theta_s >= L_s`` and the cuts of the pool."""

    def __init__(self, enc: MenuEncoding, p: Sequence[float], L: Sequence[float], *, s_needs_charge: bool = True,
                 access: Optional[Dict[str, Sequence[str]]] = None,
                 covers: Optional[Sequence[Tuple[int, Any, Tuple[str, ...]]]] = None, threads: int = 1) -> None:
        import gurobipy as gp
        from gurobipy import GRB

        self.enc = enc
        self.p = [float(x) for x in p]
        self.L = [float(x) for x in L]
        self.S = len(self.p)
        self.env = gp.Env(empty=True)
        self.env.setParam("OutputFlag", 0)
        self.env.start()
        m = gp.Model("o2_master", env=self.env)
        m.Params.OutputFlag = 0
        m.Params.Threads = int(threads)
        m.Params.Seed = 0
        m.Params.MIPGap = 0.0
        m.Params.MIPGapAbs = 1e-6
        self.model = m
        self.w = [m.addVar(vtype=GRB.BINARY, obj=float(enc.setup[i]), name=f"w[{i}]") for i in range(enc.n)]
        self.theta = [m.addVar(lb=self.L[s], obj=self.p[s], name=f"theta[{s}]") for s in range(self.S)]
        w = self.w
        self.rows_info: Dict[str, int] = {}
        for l in enc.locations:                                                        # [U1]
            m.addLConstr(gp.quicksum(w[i] for i in range(enc.n) if enc.loc[i] == l), GRB.LESS_EQUAL, 1.0)
        self.budget_row = m.addLConstr(gp.LinExpr(list(enc.inv), w), GRB.LESS_EQUAL, 1e18)    # [U2]
        m.addLConstr(gp.quicksum(w[i] for i in enc.swap_idx), GRB.GREATER_EQUAL, 1.0)         # a swap object
        self.s_needs_charge = bool(s_needs_charge)
        if s_needs_charge and "S" in enc.roles:
            charge = gp.quicksum(w[i] for i in enc.charge_idx)
            for l in enc.locations:
                ys = gp.quicksum(w[i] for i in range(enc.n) if enc.loc[i] == l and enc.role[i] == "S")
                m.addLConstr(ys - charge, GRB.LESS_EQUAL, 0.0)
        self.access = {str(z): list(ls) for z, ls in (access or {}).items()}
        self.access_empty: List[str] = []
        for z, ls in self.access.items():                                            # [U4]
            idx = [i for i in enc.swap_idx if enc.loc[i] in set(ls)]
            if not idx:
                self.access_empty.append(z)
                continue
            m.addLConstr(gp.quicksum(w[i] for i in idx), GRB.GREATER_EQUAL, 1.0)
        self.cover_rows: List[Tuple[str, ...]] = []
        for _s, _k, objs in (covers or []):                                           # 2.4 (b)
            objs = tuple(objs)
            if objs in self.cover_rows:
                continue
            self.cover_rows.append(objs)
            idx = [i for i in range(enc.n) if enc.fid[i] in set(objs)]
            m.addLConstr(gp.quicksum(w[i] for i in idx), GRB.GREATER_EQUAL, 1.0)
        self.rows_info.update(cover=len(self.cover_rows), access=len(self.access) - len(self.access_empty))
        self.theta_cuts: List[List[Tuple[float, np.ndarray]]] = [[] for _ in range(self.S)]
        self.row_cuts: List[Tuple[float, np.ndarray]] = []
        self.n_cuts = 0
        self._stack = None
        self.restricted: Optional[Set[str]] = None
        m.update()

    def restrict(self, locations: Optional[Iterable[str]]) -> None:
        """R7 (design 2.6, DOT-only run): fix every binary of the locations NOT in ``locations``
        to 0 (``None`` lifts the restriction).  The same template, cuts and cache serve both runs;
        ``V*_restricted >= V*_full``."""
        keep = None if locations is None else {str(l) for l in locations}
        for i, v in enumerate(self.w):
            v.UB = 1.0 if (keep is None or self.enc.loc[i] in keep) else 0.0
        self.restricted = keep
        self.model.update()

    # -- cuts -------------------------------------------------------------------
    def add_cut(self, cut: Cut) -> bool:
        import gurobipy as gp
        from gurobipy import GRB

        lin = cut.linear(self.enc)
        if lin is None:
            return False
        const, a = lin
        nz = [i for i in range(self.enc.n) if abs(a[i]) > 1e-12]
        expr = gp.LinExpr([float(a[i]) for i in nz], [self.w[i] for i in nz])
        if cut.is_theta:
            s = int(cut.scenario)
            self.model.addLConstr(self.theta[s] - expr, GRB.GREATER_EQUAL, float(const))
            self.theta_cuts[s].append((float(const), a))
        else:
            self.model.addLConstr(expr, GRB.GREATER_EQUAL, float(const))
            self.row_cuts.append((float(const), a))
        self.n_cuts += 1
        self._stack = None
        return True

    def _stacked(self) -> Tuple[List[Tuple[np.ndarray, np.ndarray]], Tuple[np.ndarray, np.ndarray]]:
        """Cut matrices for vectorised evaluation (rebuilt after new cuts)."""
        if getattr(self, "_stack", None) is None:
            th = []
            for s in range(self.S):
                cs = self.theta_cuts[s]
                th.append((np.array([c for c, _a in cs]), np.array([a for _c, a in cs]).reshape(len(cs), self.enc.n)))
            rc = (np.array([c for c, _a in self.row_cuts]),
                  np.array([a for _c, a in self.row_cuts]).reshape(len(self.row_cuts), self.enc.n))
            self._stack = (th, rc)
        return self._stack

    # -- evaluation without solving -----------------------------------------------------
    def theta_floor(self, w: np.ndarray) -> List[float]:
        """``max(L_s, max cuts of s at w)`` per scenario."""
        th, _rc = self._stacked()
        out = []
        for s in range(self.S):
            c, A = th[s]
            out.append(max(self.L[s], float(np.max(c + A @ w))) if len(c) else self.L[s])
        return out

    def envelope(self, layout: Layout) -> float:
        """Master objective at a menu layout: ``setup + sum_s p_s max(L_s, cuts)``; ``inf`` when a
        row cut (no-good, terminal) or a structural row excludes it."""
        if not self.enc.contains(layout):
            return INF
        w = self.enc.w_of(layout)
        if not self.rows_ok(layout, w):
            return INF
        th = self.theta_floor(w)
        return float(self.enc.setup @ w) + sum(p * t for p, t in zip(self.p, th))

    def rows_ok(self, layout: Layout, w: Optional[np.ndarray] = None) -> bool:
        enc = self.enc
        if w is None:
            if not enc.contains(layout):
                return False
            w = enc.w_of(layout)
        if not layout_admissible(layout, s_needs_charge=self.s_needs_charge, require_swap=True):
            return False
        if self.restricted is not None and any(l not in self.restricted for l in layout.locations()):
            return False
        swap_fids = {enc.fid[i] for i in enc.swap_idx if w[i] > 0.5}
        swap_locs = {enc.loc[i] for i in enc.swap_idx if w[i] > 0.5}
        for z, ls in self.access.items():
            if z in self.access_empty:
                continue
            if not swap_locs & set(ls):
                return False
        for objs in self.cover_rows:
            if not swap_fids & set(objs):
                return False
        _th, (c, A) = self._stacked()
        if len(c) and np.any(A @ w < c - 1e-9):
            return False
        return True

    # -- solve ------------------------------------------------------------------------
    def solve(self, budget: float, relax: bool = False, start: Optional[Layout] = None,
              time_limit: Optional[float] = None, pool_solutions: Optional[int] = None) -> Dict[str, Any]:
        """Solve the master at ``budget``.  ``relax``: its LP relaxation.  ``time_limit``: seconds
        (``ObjBound`` stays a valid lower bound at ``TIME_LIMIT``); ``None`` = no limit (a limit of
        an earlier call is cleared).  ``pool_solutions = k``: also return the ``k`` best integer
        solutions found (``ranked``: list of ``(obj, layout)``; Gurobi ``PoolSearchMode 2``)."""
        from gurobipy import GRB

        from .ilp import status_name

        m = self.model
        self.budget_row.RHS = float(budget)
        m.update()
        t0 = time.perf_counter()
        if relax:
            lp = m.relax()
            lp.Params.OutputFlag = 0
            lp.optimize()
            st = status_name(lp.Status)
            out: Dict[str, Any] = {"status": st, "relax": True, "runtime_s": time.perf_counter() - t0}
            if lp.Status == GRB.OPTIMAL:
                vals = lp.getAttr("X", lp.getVars())
                out.update(obj=float(lp.ObjVal), bound=float(lp.ObjVal), w=np.array(vals[:self.enc.n]),
                           theta=list(vals[self.enc.n:self.enc.n + self.S]))
            lp.dispose()
            return out
        if start is not None and self.enc.contains(start):
            ws = self.enc.w_of(start)
            for i, v in enumerate(self.w):
                v.Start = float(ws[i])
        else:
            for v in self.w:
                v.Start = GRB.UNDEFINED
        m.Params.TimeLimit = float(time_limit) if time_limit is not None else GRB.INFINITY
        if pool_solutions:
            m.Params.PoolSearchMode = 2
            m.Params.PoolSolutions = int(pool_solutions)
        try:
            m.optimize()
        finally:
            if pool_solutions:
                m.Params.PoolSearchMode = 0
                m.Params.PoolSolutions = 10
            m.Params.TimeLimit = GRB.INFINITY
        st = status_name(m.Status)
        out = {"status": st, "relax": False, "runtime_s": time.perf_counter() - t0, "n_cuts": self.n_cuts}
        try:
            out["bound"] = float(m.ObjBound)
        except Exception:  # noqa: BLE001
            out["bound"] = None
        if m.Status == GRB.INFEASIBLE:
            out["bound"] = INF
        if m.SolCount > 0:
            wv = np.array(m.getAttr("X", self.w))
            out.update(obj=float(m.ObjVal), w=wv, layout=self.enc.layout_of(wv),
                       theta=[float(t.X) for t in self.theta])
            if pool_solutions:
                ranked: List[Tuple[float, Layout]] = []
                for k in range(int(m.SolCount)):
                    m.Params.SolutionNumber = k
                    wk = np.array(m.getAttr("Xn", self.w))
                    ranked.append((float(m.PoolObjVal), self.enc.layout_of(wk)))
                m.Params.SolutionNumber = 0
                out["ranked"] = ranked
        return out

    def solve_excluding(self, budget: float, exclude: Sequence[Layout],
                        time_limit: Optional[float] = None) -> Dict[str, Any]:
        """Exploration solve (search completeness): a COPY of the master with a no-good row
        ``d(w, what) >= 1`` on every layout of ``exclude`` (priced layouts whose open pricing
        gaps cannot be closed any more).  Its value is NOT a lower bound on ``V*`` (the
        excluded layouts are not resolved); the certifier takes ``LB`` only from :meth:`solve`
        of the unmodified master.  Returns ``status``, ``obj``, ``bound`` (of the copy),
        ``layout``, ``w``."""
        import gurobipy as gp
        from gurobipy import GRB

        from .ilp import status_name

        m = self.model
        self.budget_row.RHS = float(budget)
        m.update()
        t0 = time.perf_counter()
        cp = m.copy()
        try:
            cp.Params.OutputFlag = 0
            if time_limit is not None:
                cp.Params.TimeLimit = float(time_limit)
            wv = cp.getVars()[:self.enc.n]
            n_ex = 0
            for lay in exclude:
                ham = self.enc.hamming(lay.key())
                if ham is None:
                    continue
                hc, ha = ham
                cp.addLConstr(gp.LinExpr([float(a) for a in ha], wv), GRB.GREATER_EQUAL, 1.0 - hc)
                n_ex += 1
            cp.optimize()
            out: Dict[str, Any] = {"status": status_name(cp.Status), "explore": True, "n_excluded": n_ex,
                                   "runtime_s": time.perf_counter() - t0}
            try:
                out["bound"] = float(cp.ObjBound)
            except Exception:  # noqa: BLE001
                out["bound"] = None
            if cp.Status == GRB.INFEASIBLE:
                out["bound"] = INF
            if cp.SolCount > 0:
                w = np.array(cp.getAttr("X", wv))
                out.update(obj=float(cp.ObjVal), w=w, layout=self.enc.layout_of(w))
            return out
        finally:
            cp.dispose()

    def dispose(self) -> None:
        try:
            self.model.dispose()
            self.env.dispose()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# exact pricing (design 4.2; C3, C4)
# ---------------------------------------------------------------------------
@dataclass
class PriceResult:
    """Result of :func:`price_layout`.  ``status``: ``PRICED`` (every scenario has an incumbent;
    ``V`` set), ``PRUNED_BY_BOUND`` (proven ``>= UB - tol``; ``V`` may still be set from the
    incumbents of bound-stopped solves, a feasible upper value), ``INFEASIBLE`` (``infeasible`` =
    the row status), ``UNRESOLVED`` (a scenario without incumbent / error), ``SKIPPED_BUDGET``."""
    layout: Layout
    status: str
    setup: float
    lb: List[float]
    ub: List[Optional[float]]
    V: Optional[float] = None
    infeasible: Optional[str] = None
    rows: List[Dict[str, Any]] = field(default_factory=list)
    n_solves: int = 0
    served_share: Optional[float] = None

    lb_p: List[float] = field(default_factory=list)
    #: R7: pricing tier of the rows (:data:`PRICING_TIERS`)
    tier: str = "all_candidates"
    #: R7 re-plan (K3.1): scenarios skipped by a strict ``scenarios`` filter (uncached, not solved)
    skipped: List[int] = field(default_factory=list)

    @property
    def lower(self) -> float:
        return self.setup + sum(self.lb_p)


def _row_lb(row: Dict[str, Any]) -> Optional[float]:
    """OPEX lower bound of an evaluator row (C3): ``bound - C_setup``."""
    b, c = row.get("bound"), row.get("C_setup")
    if b is None or c is None:
        return None
    try:
        b = float(b)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(b) or abs(b) >= 1e99:
        return None
    return b - float(c)


def _tier_evaluator(evaluator: LowerLevelEvaluator, tier: str) -> LowerLevelEvaluator:
    if tier not in PRICING_TIERS:
        raise ValueError(f"tier must be one of {PRICING_TIERS} (got {tier!r})")
    if tier == "all_candidates" or evaluator.reposition == "open_sites":
        return evaluator
    sib = getattr(evaluator, "_open_sites_sibling", None)
    if sib is None:
        sib = evaluator.derive(reposition="open_sites")
        evaluator._open_sites_sibling = sib            # cache keys differ by reposition
    _sync_sibling(evaluator, sib)
    return sib


def _sync_sibling(evaluator: LowerLevelEvaluator, sib: LowerLevelEvaluator) -> None:
    """R7 re-plan: a cached sibling follows the run-time settings of its evaluator that may be
    replaced after the sibling was derived (the wall budget of a new certifier, change 6)."""
    sib.wall = evaluator.wall
    sib.verify_checked_starts = getattr(evaluator, "verify_checked_starts", True)


# ---------------------------------------------------------------------------
# R7 re-plan after batch 2 (notes/siting_production_replan_m1.md, changes 4-5 with K3)
# ---------------------------------------------------------------------------
def _param_value(v: str) -> Any:
    for typ in (int, float):
        try:
            return typ(v)
        except ValueError:
            continue
    return v


def parse_ilp_params(tokens: Optional[Iterable[str]]) -> Dict[str, Any]:
    """``['Method=2', 'MIPFocus=3']`` -> ``{'Method': 2, 'MIPFocus': 3}`` (ints, floats, else
    strings; tokens may also be comma-separated).  The parameters enter the cache key of the
    rows they produce (change 5: new rows by design).  ``Threads`` / ``TimeLimit`` /
    ``BestBdStop`` are refused: they are set by ``--threads``, the time limits and the pricing."""
    out: Dict[str, Any] = {}
    for tok in tokens or ():
        for part in str(tok).split(","):
            part = part.strip()
            if not part:
                continue
            if "=" not in part:
                raise ValueError(f"--ilp-params: expected K=V, got {part!r}")
            k, v = part.split("=", 1)
            k = k.strip()
            if k in ("Threads", "TimeLimit", "BestBdStop"):
                raise ValueError(f"--ilp-params: {k} is set by the runner, not by --ilp-params")
            out[k] = _param_value(v.strip())
    return out


def parse_cells(tokens: Optional[Iterable[str]]) -> Dict[str, Set[int]]:
    """``--cells`` tokens -> ``{name: {scenarios}}``.  A token is ``LOC:SPEC`` (a location id,
    e.g. ``D29:5``) or ``LAYOUT_KEY@SPEC`` (e.g. ``D29:SC:B3:C2@5``); ``SPEC`` is a scenario,
    a range ``0-5`` or a ``+``-list ``2+5``.  Tokens may be comma- or blank-separated."""
    out: Dict[str, Set[int]] = {}
    for tok in tokens or ():
        for part in str(tok).replace(",", " ").split():
            if "@" in part:
                name, spec = part.rsplit("@", 1)
            elif ":" in part:
                name, spec = part.rsplit(":", 1)
            else:
                raise ValueError(f"--cells: expected LOC:s or LAYOUT@s, got {part!r}")
            got: Set[int] = set()
            for piece in spec.split("+"):
                if "-" in piece:
                    lo, hi = piece.split("-", 1)
                    got.update(range(int(lo), int(hi) + 1))
                else:
                    got.add(int(piece))
            out.setdefault(name.strip(), set()).update(got)
    return out


def cells_for_layout(cells: Optional[Dict[str, Set[int]]], layout: Layout) -> Optional[List[int]]:
    """Scenarios of ``layout`` selected by :func:`parse_cells` (its own key, plus every location
    it opens); ``None`` when ``cells`` is ``None`` (no filter); ``[]`` when nothing matches."""
    if cells is None:
        return None
    got: Set[int] = set(cells.get(layout.key(), set()))
    for l in layout.locations():
        got |= cells.get(l, set())
    return sorted(got)


def _params_evaluator(evaluator: LowerLevelEvaluator, ilp_params: Optional[Dict[str, Any]]) -> LowerLevelEvaluator:
    """The sibling of ``evaluator`` with ``ilp_params`` merged into its Gurobi params (cached
    per parameter set; the in-memory cache dict, templates and wall are shared)."""
    if not ilp_params:
        return evaluator
    sig = json.dumps(sorted((str(k), ilp_params[k]) for k in ilp_params), default=str)
    sibs = evaluator.__dict__.setdefault("_params_siblings", {})
    sib = sibs.get(sig)
    if sib is None:
        sib = evaluator.derive(params=dict(ilp_params))
        sibs[sig] = sib
    _sync_sibling(evaluator, sib)
    return sib


def _warm_pick(warm_ev: Optional[LowerLevelEvaluator], layout: Layout, s: int,
               own_row: Optional[Dict[str, Any]], own_port: Optional[Dict[str, Any]]
               ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Change 4: the MIP start offered to a solve of cell ``(layout, s)``: without ``warm_ev``
    the cached row's own schedule (unchanged behaviour, source ``None``); with ``warm_ev`` (the
    open-sites sibling) the schedule of lower total among the cached row's own one
    (``'cached_row'``) and the sibling's cached schedule of the same cell (``'open_sites'``).
    The evaluator still checks the materialised schedule and keeps the rule start when it is
    cheaper, so the choice affects the start only, never a value."""
    if warm_ev is None:
        return own_port, None
    wrow, wport = warm_ev.cached_schedule(layout, s)
    cands: List[Tuple[float, int, Dict[str, Any], str]] = []
    if own_port is not None and own_row is not None and own_row.get("total") is not None:
        cands.append((float(own_row["total"]), 1, own_port, "cached_row"))
    if wport is not None and wrow is not None and wrow.get("total") is not None:
        cands.append((float(wrow["total"]), 0, wport, warm_ev.reposition))
    if not cands:
        return own_port, warm_ev.reposition
    _t, _o, port, src = min(cands, key=lambda c: (c[0], c[1]))
    return port, src


#: R7 re-plan: extra row fields copied into ``PriceResult.rows`` when a warm tier is used
_WARM_ROW_KEYS = ("warm_source", "warm_available", "warm_materialised", "warm_check_ok", "warm_obj",
                  "mip_start_variant", "mip_start_obj", "verify_start", "params", "node_count", "build_time_s")
_ROW_KEYS = ("scenario", "status", "gurobi_status", "total", "opex", "bound", "C_setup", "gap", "runtime_s", "cache_hit",
             "best_bd_stop", "time_limit", "key", "error")


def _row_view(row: Dict[str, Any], extra: bool) -> Dict[str, Any]:
    out = {k: row.get(k) for k in _ROW_KEYS}
    if extra:
        out.update({k: row[k] for k in _WARM_ROW_KEYS if k in row})
    return out


def ub_check_all_candidates(evaluator: LowerLevelEvaluator, layout: Layout,
                            scenarios: Optional[Iterable[int]] = None) -> Dict[str, Any]:
    """Change 4 / M6: materialise the cached ``open_sites`` schedule of every cell
    ``(layout, s)`` on the ALL-CANDIDATES layout library of ``evaluator`` and run
    ``evaluate.check`` and ``evaluate.cost`` on it.  A cell is ``ok`` when the schedule exists
    there (every arc and service), passes ``check`` with zero violations and costs the same as
    on the open-sites library.  ``V_checked`` (set when every cell is ok) is then a feasible
    value of the all-candidates follower: an explicit validity record for an upper bound taken
    from open-sites pricing (the sub-library relation holds by construction; this checks it).
    Builds the all-candidates libraries (the scenario templates) of the cells checked."""
    t0 = time.perf_counter()
    if evaluator.reposition != "all_candidates":
        raise ValueError("ub_check_all_candidates needs the all-candidates evaluator")
    sib = _tier_evaluator(evaluator, "open_sites")
    S = evaluator.n_scenarios
    want = list(range(S)) if scenarios is None else sorted({int(x) for x in scenarios})
    setup = layout.allocated_cost(evaluator.spec)
    cells: List[Dict[str, Any]] = []
    for s in want:
        row, port = sib.cached_schedule(layout, s)
        cell: Dict[str, Any] = {"scenario": s, "open_status": None if row is None else row.get("status"),
                                "open_total": None if row is None else row.get("total"), "ok": False}
        if port is None:
            cell["reason"] = "no open_sites schedule cached"
            cells.append(cell)
            continue
        inst, lib = evaluator.layout_pair(layout, s)
        sched = materialise_schedule(port, inst, lib)
        cell["materialised"] = sched is not None
        if sched is None:
            cell["reason"] = "an arc or a service of the schedule is absent from the all-candidates library"
            cells.append(cell)
            continue
        rep = _check_schedule(inst, lib, sched)
        cst = _cost_schedule(inst, lib, sched)
        tot = float(cst["total"])
        same = row.get("total") is not None and abs(tot - float(row["total"])) <= 1e-6 * max(1.0, abs(tot))
        cell.update(check_ok=bool(rep["ok"]), n_violations=int(rep.get("n_violations") or 0), total=tot,
                    opex=tot - float(cst["C_setup"]), same_cost=bool(same), ok=bool(rep["ok"] and same))
        if not rep["ok"]:
            cell["families"] = sorted((rep.get("families") or {}).keys())
        cells.append(cell)
    ok = bool(cells) and all(c["ok"] for c in cells) and len(want) == S
    V = setup + sum(evaluator.p[c["scenario"]] * c["opex"] for c in cells) if ok else None
    return {"layout_key": layout.key(), "scenarios": want, "cells": cells, "ok": ok,
            "n_ok": sum(1 for c in cells if c["ok"]), "V_checked": V, "setup": setup,
            "wall_s": time.perf_counter() - t0}


def _resolve_pricing_evaluators(evaluator: LowerLevelEvaluator, tier: str, warm_tier: Optional[str],
                                ilp_params: Optional[Dict[str, Any]]
                                ) -> Tuple[LowerLevelEvaluator, Optional[LowerLevelEvaluator]]:
    """``(evaluator of the solves, evaluator whose cached schedules are the warm tier)``.  The
    warm tier is looked up on the BASE parameters (its rows were solved with them)."""
    ev = _tier_evaluator(evaluator, tier)
    warm_ev = None
    if warm_tier is not None:
        if warm_tier not in PRICING_TIERS:
            raise ValueError(f"warm_tier must be one of {PRICING_TIERS} (got {warm_tier!r})")
        if warm_tier == "open_sites" and tier == "all_candidates" and evaluator.reposition == "all_candidates":
            warm_ev = _tier_evaluator(evaluator, "open_sites")
    return _params_evaluator(ev, ilp_params), warm_ev


def price_layout(evaluator: LowerLevelEvaluator, layout: Layout, lb0: Sequence[float], ub_ref: float, tol: float,
                 *, full: bool = False, time_limit: Optional[float] = None,
                 scenarios: Optional[Iterable[int]] = None, workers: int = 1,
                 tier: str = "all_candidates", strict_scenarios: bool = False,
                 warm_tier: Optional[str] = None, ilp_params: Optional[Dict[str, Any]] = None) -> PriceResult:
    """Exact pricing of ``layout`` (design 4.2).  ``lb0`` = per-scenario OPEX lower bounds known
    beforehand (``max(Qs_s, L_s)``), ``ub_ref`` = the incumbent of the largest relevant budget
    (``inf`` = none), ``tol`` its tolerance.  Each scenario ILP gets ``BestBdStop = need_s +
    C_setup`` (unless ``full``), where ``need_s`` is the OPEX bound at which the layout is proven
    ``>= ub_ref - tol``.  Cached rows are reused when final, or when their bound already reaches
    ``need_s``; rows actually stopped by an earlier BestBdStop (``USER_OBJ_LIMIT``) are
    re-solved (warm-started).  A row solved under a BestBdStop that never fired follows the
    ordinary TIME_LIMIT rule.  ``scenarios`` (escalation): only these scenarios may be solved;
    the others reuse their cached rows as they are (a cached row's bound and incumbent stay
    valid).

    R7: ``tier='open_sites'`` prices on the evaluator's ``open_sites`` sibling (design 2.5: a
    valid upper bound, never a cut); ``workers > 1`` prices the scenarios in parallel
    (:func:`price_layout_parallel`); with the defaults this function is unchanged.

    R7 re-plan (changes 4, 5; K3.1), all off by default:
    ``strict_scenarios`` -- with ``scenarios``, a scenario outside the filter WITHOUT a cached
    row is skipped (no solve; its bound stays ``lb0``, e.g. the LP value ``Qs_s``; the result is
    then ``UNRESOLVED`` unless a bound prunes it).  Without it such a cell is solved as before.
    ``warm_tier='open_sites'`` -- (all-candidates tier) every solve is offered, as MIP start,
    the lower-total of the cached row's own schedule and the open-sites sibling's cached
    schedule of the same cell (:func:`_warm_pick`; the rows record the materialise / check /
    cost result of the open-sites schedule).  ``ilp_params`` -- extra Gurobi parameters; the
    solves run on a sibling whose ``params`` (hence cache keys) include them."""
    ev, warm_ev = _resolve_pricing_evaluators(evaluator, tier, warm_tier, ilp_params)
    evaluator = ev
    if int(workers) > 1 and evaluator.n_scenarios > 1:
        return price_layout_parallel(evaluator, layout, lb0, ub_ref, tol, full=full, time_limit=time_limit,
                                     scenarios=scenarios, workers=int(workers), tier=tier,
                                     strict_scenarios=strict_scenarios, _warm_ev=warm_ev)
    only = None if scenarios is None else {int(x) for x in scenarios}
    strict = bool(strict_scenarios) and only is not None
    p = evaluator.p
    S = evaluator.n_scenarios
    setup = layout.allocated_cost(evaluator.spec)
    lb = [float(x) for x in lb0]
    ub: List[Optional[float]] = [None] * S
    res = PriceResult(layout=layout, status="PRICED", setup=setup, lb=lb, ub=ub, tier=tier)
    target = (ub_ref - tol) if (ub_ref is not None and math.isfinite(ub_ref)) else INF
    shares: List[Optional[float]] = [None] * S
    for s in range(S):
        if not full and setup + sum(p[t] * lb[t] for t in range(S)) >= target - _EPS:
            res.status = "PRUNED_BY_BOUND"
            break
        need = (target - setup - sum(p[t] * lb[t] for t in range(S) if t != s)) / p[s] if math.isfinite(target) else INF
        bbs = None if (full or not math.isfinite(need)) else need + setup
        key = evaluator.cache_key(layout, s, "ilp")
        cached = evaluator.cache.get(key)
        row = None
        if cached is None and strict and s not in only:
            res.skipped.append(s)                       # K3.1: an uncached cell outside the filter
            continue
        if cached is not None and only is not None and s not in only:
            row = dict(cached, cache_hit=True)
        elif cached is not None:
            clb = _row_lb(cached)
            if cached.get("status") in _FINAL or cached.get("gurobi_status") in ("INFEASIBLE", "INF_OR_UNBD"):
                row = dict(cached, cache_hit=True)
            elif bbs is not None and clb is not None and clb >= need - _EPS:
                row = dict(cached, cache_hit=True)
            elif time_limit is not None and cached.get("status") == "TIME_LIMIT" \
                    and float(cached.get("time_limit") or 0.0) >= float(time_limit) - 1e-9:
                row = dict(cached, cache_hit=True)      # already solved with at least this time limit
            elif bd_stopped(cached) or cached.get("status") == NO_INCUMBENT:
                wport, wsrc = _warm_pick(warm_ev, layout, s, cached, evaluator.load_portable(cached))
                row = evaluator.evaluate_scenario(layout, s, "ilp", force=True, best_bd_stop=bbs, time_limit=time_limit,
                                                  warm=wport, **({"warm_source": wsrc} if wsrc else {}))
                res.n_solves += int(not row.get("cache_hit"))
        if row is None:
            own = evaluator.load_portable(cached) if cached is not None else None
            wport, wsrc = _warm_pick(warm_ev, layout, s, cached, own)
            row = evaluator.evaluate_scenario(layout, s, "ilp", best_bd_stop=bbs, time_limit=time_limit,
                                              force=time_limit is not None and cached is not None,
                                              warm=wport, **({"warm_source": wsrc} if wsrc else {}))
            res.n_solves += int(not row.get("cache_hit"))
        res.rows.append(_row_view(row, warm_ev is not None))
        st = row.get("status")
        if st == SKIPPED_BUDGET:
            res.status = SKIPPED_BUDGET
            break
        rlb = _row_lb(row)
        if rlb is not None:
            lb[s] = max(lb[s], rlb)
        if st in (INFEASIBLE_TERMINAL, INFEASIBLE_ILP):
            res.status, res.infeasible = "INFEASIBLE", st
            break
        if row.get("feasible") and row.get("opex") is not None:
            ub[s] = float(row["opex"])
            if lb[s] > ub[s]:
                # a bound above a feasible value can only come from tolerances; never overstate
                lb[s] = ub[s]
            shares[s] = (row.get("metrics") or {}).get("served_share")
        elif st in (NO_INCUMBENT, ERROR):
            res.status = "UNRESOLVED"
    if res.status == "PRICED" and all(u is not None for u in ub):
        res.V = setup + sum(p[s] * float(ub[s]) for s in range(S))
        if all(x is not None for x in shares):
            res.served_share = sum(p[s] * float(shares[s]) for s in range(S))
    elif res.status == "PRICED":
        res.status = "UNRESOLVED"
    if res.status in ("PRICED", "UNRESOLVED") and not full \
            and setup + sum(p[t] * lb[t] for t in range(S)) >= target - _EPS:
        # proven >= ub_ref - tol; a V from BestBdStop incumbents is kept (a feasible, upper value)
        res.status = "PRUNED_BY_BOUND"
    res.lb_p = [p[s] * lb[s] for s in range(S)]
    return res


def _price_plan(evaluator: LowerLevelEvaluator, layout: Layout, s: int, need: float, bbs: Optional[float],
                time_limit: Optional[float], only: Optional[Set[int]], strict: bool = False,
                warm_ev: Optional[LowerLevelEvaluator] = None) -> Tuple[str, Any]:
    """The decision :func:`price_layout` takes for scenario ``s`` at bound-stop ``bbs``:
    ``('row', cached row)``, ``('solve', keyword arguments of evaluate_scenario)`` or (R7
    re-plan K3.1, ``strict``) ``('skip', None)`` for an uncached scenario outside ``only``."""
    key = evaluator.cache_key(layout, s, "ilp")
    with evaluator._lock:
        cached = evaluator.cache.get(key)
    if cached is None and strict and only is not None and s not in only:
        return "skip", None
    if cached is not None and only is not None and s not in only:
        return "row", dict(cached, cache_hit=True)
    if cached is not None:
        clb = _row_lb(cached)
        if cached.get("status") in _FINAL or cached.get("gurobi_status") in ("INFEASIBLE", "INF_OR_UNBD"):
            return "row", dict(cached, cache_hit=True)
        if bbs is not None and clb is not None and clb >= need - _EPS:
            return "row", dict(cached, cache_hit=True)
        if time_limit is not None and cached.get("status") == "TIME_LIMIT" \
                and float(cached.get("time_limit") or 0.0) >= float(time_limit) - 1e-9:
            return "row", dict(cached, cache_hit=True)
        if bd_stopped(cached) or cached.get("status") == NO_INCUMBENT:
            wport, wsrc = _warm_pick(warm_ev, layout, s, cached, evaluator.load_portable(cached))
            kw = {"force": True, "best_bd_stop": bbs, "time_limit": time_limit, "warm": wport}
            if wsrc:
                kw["warm_source"] = wsrc
            return "solve", kw
    own = evaluator.load_portable(cached) if cached is not None else None
    wport, wsrc = _warm_pick(warm_ev, layout, s, cached, own)
    kw = {"best_bd_stop": bbs, "time_limit": time_limit, "force": time_limit is not None and cached is not None,
          "warm": wport}
    if wsrc:
        kw["warm_source"] = wsrc
    return "solve", kw


def price_layout_parallel(evaluator: LowerLevelEvaluator, layout: Layout, lb0: Sequence[float], ub_ref: float,
                          tol: float, *, full: bool = False, time_limit: Optional[float] = None,
                          scenarios: Optional[Iterable[int]] = None, workers: int = 4,
                          tier: str = "all_candidates", strict_scenarios: bool = False,
                          warm_tier: Optional[str] = None, ilp_params: Optional[Dict[str, Any]] = None,
                          _warm_ev: Optional[LowerLevelEvaluator] = None) -> PriceResult:
    """R7 scenario-parallel exact pricing (design 4 item 2 / 7.2 item 7; waves added by the
    fixer pass).  Pass 1 runs in WAVES of ``workers`` scenarios, the largest ``p_s`` first:
    every scenario of a wave gets the ``BestBdStop`` of its need computed from the bounds known
    when the wave starts (``lb0`` plus the rows of the earlier waves), the cached-row decisions
    are the ones of :func:`price_layout`, and the solves of a wave run on ``workers`` threads
    (gurobipy releases the GIL; one model and environment per solve; the evaluator's caches are
    locked).  Before each wave the prune test ``setup + sum_s p_s lb_s >= target`` is applied:
    once it holds the remaining scenarios are not started (``PRUNED_BY_BOUND``, as the sequential
    loop).  Pass 2 (sequential refinement): a row stopped by ``BestBdStop`` whose bound falls
    short of its current need is re-solved (warm) in scenario order, until nothing changes.
    The rows are then folded in scenario order.

    Contract against :func:`price_layout` (stated honestly): the status is the same (``PRICED``
    results are identical, rows included, because no stop fired in either), every scenario
    bound is at least the sequential one, and the ``PRUNED_BY_BOUND`` / ``UNRESOLVED`` results
    may hold MORE and STRONGER rows (scenarios of a wave that the sequential loop would have
    skipped after an earlier stop, rows solved to ``OPTIMAL`` where the sequential stop fired
    first), hence possibly a different feasible ``V`` and different cache rows.  With ``workers
    = 1`` the waves are single scenarios in ``p_s`` order.

    R7 re-plan: ``strict_scenarios``, ``warm_tier`` and ``ilp_params`` as in
    :func:`price_layout` (``_warm_ev``: the warm evaluator already resolved by it)."""
    from concurrent.futures import ThreadPoolExecutor

    if _warm_ev is None and (warm_tier is not None or ilp_params):
        evaluator, _warm_ev = _resolve_pricing_evaluators(evaluator, tier, warm_tier, ilp_params)
    warm_ev = _warm_ev
    only = None if scenarios is None else {int(x) for x in scenarios}
    strict = bool(strict_scenarios) and only is not None
    p = evaluator.p
    S = evaluator.n_scenarios
    setup = layout.allocated_cost(evaluator.spec)
    lb = [float(x) for x in lb0]
    ub: List[Optional[float]] = [None] * S
    res = PriceResult(layout=layout, status="PRICED", setup=setup, lb=lb, ub=ub, tier=tier)
    target = (ub_ref - tol) if (ub_ref is not None and math.isfinite(ub_ref)) else INF
    shares: List[Optional[float]] = [None] * S
    if not full and setup + sum(p[t] * lb[t] for t in range(S)) >= target - _EPS:
        res.status = "PRUNED_BY_BOUND"
        res.lb_p = [p[s] * lb[s] for s in range(S)]
        return res

    def need_of(s: int, lb_cur: Sequence[float]) -> Tuple[float, Optional[float]]:
        need = (target - setup - sum(p[t] * lb_cur[t] for t in range(S) if t != s)) / p[s] if math.isfinite(target) else INF
        bbs = None if (full or not math.isfinite(need)) else need + setup
        return need, bbs

    rows_by_s: Dict[int, Dict[str, Any]] = {}
    skipped: Set[int] = set()

    def solve(s: int, kw: Dict[str, Any]) -> Dict[str, Any]:
        return evaluator.evaluate_scenario(layout, s, "ilp", **kw)

    def fold_lb(cur: List[float]) -> List[float]:
        out = list(cur)
        for s, row in rows_by_s.items():
            rlb = _row_lb(row)
            if rlb is not None:
                out[s] = max(out[s], rlb)
        return out

    order = sorted(range(S), key=lambda s: (-float(p[s]), s))
    width = max(1, int(workers))
    pruned_early = False
    if only is not None:
        # R7 fixer (batched escalation): the cached rows of the scenarios outside ``only`` are taken
        # first, so that the waves are cut from the scenarios that may need a solve (two open
        # scenarios with workers = 2 run in ONE wave, not in the waves of the full p_s order)
        for s in order:
            if s in only:
                continue
            need, bbs = need_of(s, lb)
            what, payload = _price_plan(evaluator, layout, s, need, bbs, time_limit, only, strict, warm_ev)
            if what == "row":
                rows_by_s[s] = payload
            elif what == "skip":
                skipped.add(s)
        order = [s for s in order if s not in rows_by_s and s not in skipped]
    pos = 0
    if any(r.get("status") == SKIPPED_BUDGET for r in rows_by_s.values()):
        pos = len(order)
    while pos < len(order):
        lb_now = fold_lb(lb)
        if not full and setup + sum(p[t] * lb_now[t] for t in range(S)) >= target - _EPS:
            pruned_early = True
            break
        wave = order[pos: pos + width]
        pos += width
        todo: List[Tuple[int, Dict[str, Any]]] = []
        for s in wave:
            need, bbs = need_of(s, lb_now)
            what, payload = _price_plan(evaluator, layout, s, need, bbs, time_limit, only, strict, warm_ev)
            if what == "row":
                rows_by_s[s] = payload
            elif what == "skip":
                skipped.add(s)
            else:
                todo.append((s, payload))
        if todo:
            with ThreadPoolExecutor(max_workers=max(1, min(width, len(todo)))) as pool:
                futs = {s: pool.submit(solve, s, kw) for s, kw in todo}
                for s, f in futs.items():
                    rows_by_s[s] = f.result()
                    res.n_solves += int(not rows_by_s[s].get("cache_hit"))
        if any(rows_by_s[s].get("status") == SKIPPED_BUDGET for s in wave if s in rows_by_s):
            break
    # pass 2: sequential refinement of early stops against the improved bounds
    if not full:
        for _ in range(S):
            changed = False
            lb_now = fold_lb(lb)
            for s in range(S):
                row = rows_by_s.get(s)
                if row is None or (only is not None and s not in only):
                    continue
                need, bbs = need_of(s, lb_now)
                rlb = _row_lb(row)
                if bd_stopped(row) and bbs is not None and rlb is not None and rlb < need - _EPS \
                        and row.get("status") not in (SKIPPED_BUDGET, ERROR):
                    wport, wsrc = _warm_pick(warm_ev, layout, s, row, evaluator.load_portable(row))
                    row = evaluator.evaluate_scenario(layout, s, "ilp", force=True, best_bd_stop=bbs, time_limit=time_limit,
                                                      warm=wport, **({"warm_source": wsrc} if wsrc else {}))
                    res.n_solves += int(not row.get("cache_hit"))
                    rows_by_s[s] = row
                    changed = True
                    rlb2 = _row_lb(row)
                    if rlb2 is not None:
                        lb_now[s] = max(lb_now[s], rlb2)
            if not changed:
                break
    res.skipped = sorted(skipped)
    # fold in scenario order (scenarios never started are absent: pruned before their wave)
    for s in range(S):
        row = rows_by_s.get(s)
        if row is None:
            continue
        res.rows.append(_row_view(row, warm_ev is not None))
        st = row.get("status")
        if st == SKIPPED_BUDGET:
            res.status = SKIPPED_BUDGET
            break
        rlb = _row_lb(row)
        if rlb is not None:
            lb[s] = max(lb[s], rlb)
        if st in (INFEASIBLE_TERMINAL, INFEASIBLE_ILP):
            res.status, res.infeasible = "INFEASIBLE", st
            break
        if row.get("feasible") and row.get("opex") is not None:
            ub[s] = float(row["opex"])
            if lb[s] > ub[s]:
                lb[s] = ub[s]
            shares[s] = (row.get("metrics") or {}).get("served_share")
        elif st in (NO_INCUMBENT, ERROR):
            res.status = "UNRESOLVED"
    if res.status == "PRICED" and pruned_early and len(rows_by_s) < S:
        res.status = "PRUNED_BY_BOUND"
    if res.status == "PRICED" and all(u is not None for u in ub):
        res.V = setup + sum(p[s] * float(ub[s]) for s in range(S))
        if all(x is not None for x in shares):
            res.served_share = sum(p[s] * float(shares[s]) for s in range(S))
    elif res.status == "PRICED":
        res.status = "UNRESOLVED"
    if res.status in ("PRICED", "UNRESOLVED") and not full \
            and setup + sum(p[t] * lb[t] for t in range(S)) >= target - _EPS:
        res.status = "PRUNED_BY_BOUND"
    res.lb_p = [p[s] * lb[s] for s in range(S)]
    return res


# ---------------------------------------------------------------------------
# relax-and-round screen (design 5)
# ---------------------------------------------------------------------------
def _snap(enc: MenuEncoding, role: str, B: float, C: float) -> Optional[Tuple[str, int, int]]:
    opts = [o for o in enc.options if o[0] == role]
    if not opts:
        return None
    return min(opts, key=lambda o: (abs(o[1] - B) + abs(o[2] - C), o[1] + o[2], o))


def relax_and_round(enc: MenuEncoding, w_star: np.ndarray, usage: Dict[str, Dict[str, float]], budget: float,
                    admissible: Callable[[Layout], bool], max_layouts: int = 60) -> List[Layout]:
    """Candidate layouts rounded from the LP point ``w_star`` and the LP usage (averaged over the
    scenarios with ``p_s``) at that point (design 5): locations ranked by swap + terminal use,
    ``k* +- 1`` sites, roles from use (SC / S / C), sizes from the fractional sizes and the LP
    stock and charging paths, snapped to the menu; over-budget layouts are shrunk.  Returns the
    admissible layouts within ``budget`` (deduplicated, at most ``max_layouts``)."""
    x = enc.x_of(w_star)
    score: Dict[str, float] = {}
    ysum: Dict[str, float] = {}
    for l in enc.locations:
        sc = 0.0
        yy = 0.0
        for r in enc.roles:
            f = facility_id(l, r)
            u = usage.get(f, {})
            sc += u.get("swap", 0.0) + u.get("term", 0.0)
            yy += x.get(f, (0.0, 0.0, 0.0))[0]
        score[l], ysum[l] = sc, yy
    order = sorted(enc.locations, key=lambda l: (-score[l], -ysum[l], l))
    k_star = int(round(sum(ysum.values())))
    max_sites = max(1, int(math.floor((budget + 1e-9) / max(1.0, float(enc.inv.min())))))
    ks = sorted({min(max(k, 1), max_sites) for k in (k_star - 1, k_star, k_star + 1)})

    def item_choices(l: str) -> List[Tuple[str, str, int, int]]:
        u = {r: usage.get(facility_id(l, r), {}) for r in enc.roles}
        sw = sum(u[r].get("swap", 0.0) + u[r].get("term", 0.0) for r in enc.roles)
        ch = sum(u[r].get("charge", 0.0) for r in enc.roles)
        ship = sum(u[r].get("ship", 0.0) for r in enc.roles)
        if sw > 1e-6 and ch >= 0.5 and "SC" in enc.roles:
            roles = ["SC"]
        elif sw > 1e-6 and "S" in enc.roles:
            roles = ["S", "SC"] if "SC" in enc.roles else ["S"]
        elif ship > 1e-6 and "C" in enc.roles:
            roles = ["C"]
        else:
            roles = sorted(enc.roles, key=lambda r: -x.get(facility_id(l, r), (0.0, 0.0, 0.0))[0])
        out: List[Tuple[str, str, int, int]] = []
        for r in roles[:2]:
            f = facility_id(l, r)
            y, B, C = x.get(f, (0.0, 0.0, 0.0))
            uu = usage.get(f, {})
            Bf = B / y if y > 1e-6 else 1.0
            Cf = C / y if y > 1e-6 else 1.0
            Bs = {math.floor(Bf), math.ceil(Bf), math.ceil(uu.get("draw", 0.0) - 1e-6)}
            Cv = max(math.ceil(Cf - 1e-6), math.ceil(uu.get("charge_peak", 0.0) - 1e-6))
            for Bv in Bs:
                o = _snap(enc, r, Bv, Cv if ROLE_CHARGE[r] else 0)
                if o is not None:
                    out.append((l,) + o)
        return list(dict.fromkeys(out))

    seen: Dict[str, Layout] = {}
    for k in ks:
        locs = order[:k]
        choices = [item_choices(l) for l in locs]
        if any(not c for c in choices):
            continue
        for combo in itertools.islice(itertools.product(*choices), 64):
            lay = Layout.of(list(combo))
            # shrink while over budget: drop one menu step of the cheapest reduction, else the weakest site
            guard = 0
            while lay.investment(enc.spec) > budget + 1e-9 and guard < 50:
                guard += 1
                smaller: List[Layout] = []
                for it in lay.open:
                    l, r, B, C = it
                    for o in enc.options:
                        if o[0] == r and (o[1], o[2]) != (B, C) and o[1] <= B and o[2] <= C:
                            smaller.append(lay.replace(l, (l,) + o))
                if smaller:
                    lay = max(smaller, key=lambda c: (c.investment(enc.spec), c.key()))
                elif lay.n_open > 1:
                    weakest = min(lay.locations(), key=lambda l: (score.get(l, 0.0), l))
                    lay = lay.drop(weakest)
                else:
                    break
            if lay.n_open and lay.investment(enc.spec) <= budget + 1e-9 and enc.contains(lay) and admissible(lay):
                seen.setdefault(lay.key(), lay)
            if len(seen) >= max_layouts:
                break
    return list(seen.values())


# ---------------------------------------------------------------------------
# bounds from a stored pool (shared by the certifier's ``finish`` and the CLI ``--bound-from-cuts``)
# ---------------------------------------------------------------------------
def menu_layouts(evaluator: LowerLevelEvaluator, enc: MenuEncoding, b: float, *,
                 access: Optional[Dict[str, Sequence[str]]] = None, s_needs_charge: bool = True,
                 k_range: Optional[Sequence[int]] = None, inv_lo: float = -INF) -> List[Layout]:
    """All admissible menu layouts within budget ``b`` (one option per location, a swap object,
    swap-only next to charge, non-empty access zones; ``k`` up to ``floor(b / min inv)``).
    ``k_range`` restricts the number of open locations and ``inv_lo`` keeps only the layouts
    with investment ``> inv_lo`` (the budget window of :func:`certify_bnb`)."""
    from .bilevel import enumerate_layouts

    unit = float(enc.inv.min())
    kmax = max(1, min(int(math.floor((b + 1e-9) / unit)), len(enc.locations)))
    cands = [c for c in evaluator.candidates if c.id in set(enc.locations)]
    ks = list(range(1, kmax + 1)) if k_range is None else [int(k) for k in k_range if 1 <= int(k) <= len(enc.locations)]
    lays = enumerate_layouts(cands, enc.options, b, evaluator.spec, ks, access=access, s_needs_charge=s_needs_charge)
    if math.isfinite(inv_lo):
        lays = [l for l in lays if l.investment(evaluator.spec) > inv_lo + 1e-9]
    return lays


def superset_trivial_bound(enc: MenuEncoding, p: Sequence[float], L: Sequence[float]) -> float:
    """``min_i setup_i + sum_s p_s L_s``: valid for every admissible layout (at least one object
    is open; every OPEX is at least the superset bound)."""
    return float(enc.setup.min()) + sum(float(a) * float(x) for a, x in zip(p, L))


def enumeration_floor(master: Master, layouts: Sequence[Layout], v_lp: Dict[str, float],
                      priced: Dict[str, Tuple[str, float]]) -> Tuple[float, Optional[str], Dict[str, int]]:
    """``min_l max(envelope(l), v_LP(l), lower(l))`` over the COMPLETE list ``layouts`` of the
    admissible layouts of a budget: a valid lower bound on ``V*_b`` at any time (every layout's
    value is at least each of its own lower bounds; layouts proven infeasible -- priced
    ``INFEASIBLE`` or excluded by a row cut -- have ``V = inf``).  ``v_lp``: known safe LP
    values by layout key; ``priced``: ``(status, lower)`` by key.  Returns ``(floor, argmin,
    counts)``."""
    lowest, arg = INF, None
    n_inf = n_env = n_lp = n_pr = 0
    for l in layouts:
        key = l.key()
        pr = priced.get(key)
        if pr is not None and pr[0] == "INFEASIBLE":
            n_inf += 1
            continue
        lo = master.envelope(l)
        if lo == INF:
            n_inf += 1
            continue
        src = 0
        if key in v_lp and v_lp[key] > lo:
            lo, src = v_lp[key], 1
        if pr is not None and pr[1] > lo:
            lo, src = pr[1], 2
        if src == 0:
            n_env += 1
        elif src == 1:
            n_lp += 1
        else:
            n_pr += 1
        if lo < lowest:
            lowest, arg = lo, key
    return lowest, arg, {"n_layouts": len(layouts), "n_infeasible": n_inf, "n_from_envelope": n_env,
                         "n_from_v_lp": n_lp, "n_from_pricing": n_pr}


def pool_bound(master: Master, enc: MenuEncoding, p: Sequence[float], L: Sequence[float], budgets: Sequence[float], *,
               ub: Optional[Dict[float, float]] = None, enum_layouts: Optional[Dict[float, Sequence[Layout]]] = None,
               v_lp: Optional[Dict[str, float]] = None, priced: Optional[Dict[str, Tuple[str, float]]] = None,
               prior: Optional[Dict[float, float]] = None, time_limit: Optional[float] = 120.0,
               pool_solutions: Optional[int] = None, start: Optional[Dict[float, Optional[Layout]]] = None
               ) -> Dict[float, Dict[str, Any]]:
    """Lower bound per budget from a master that holds the full cut pool: ``LB_b = max(master
    ObjBound, superset trivial bound, enumeration floor where the admissible layouts of ``b``
    are listed in ``enum_layouts``, ``prior[b]``)``, then nested-budget propagation (``LB_m >=
    LB_m'`` for ``m <= m'``).  Every component is a valid lower bound on ``V*_b``; ``kind``
    names the one that attains the maximum.  Returns per budget: ``LB``, ``kind``,
    ``components``, the master solve (``status``, ``bound``, ``obj``, ``proposal``, ``ranked``
    when ``pool_solutions``), ``UB`` / ``gap`` when ``ub`` is given."""
    sup = superset_trivial_bound(enc, p, L)
    out: Dict[float, Dict[str, Any]] = {}
    for b in sorted(float(x) for x in budgets):
        st = (start or {}).get(b)
        res = master.solve(b, start=st, time_limit=time_limit)
        if pool_solutions:                      # ranking in a second solve: the bound comes from the plain solve
            res2 = master.solve(b, start=st, time_limit=time_limit, pool_solutions=pool_solutions)
            if "ranked" in res2:
                res["ranked"] = res2["ranked"]
        comp: Dict[str, Optional[float]] = {"superset": sup, "master": res.get("bound")}
        if prior is not None and prior.get(b) is not None and math.isfinite(float(prior[b])):
            comp["prior"] = float(prior[b])
        enum_rec: Optional[Dict[str, Any]] = None
        if enum_layouts and b in enum_layouts:
            fl, arg, cnt = enumeration_floor(master, enum_layouts[b], v_lp or {}, priced or {})
            comp["enumeration"] = fl
            enum_rec = {"floor": fl, "argmin": arg, **cnt}
        kind, val = "superset", sup
        for k in ("prior", "master", "enumeration"):
            v = comp.get(k)
            if v is not None and v > val:
                kind, val = k, float(v)
        rec: Dict[str, Any] = {"budget": b, "LB": val, "kind": kind, "components": comp, "master_status": res["status"],
                               "master_bound": res.get("bound"), "master_obj": res.get("obj"),
                               "master_runtime_s": res.get("runtime_s"), "n_cuts": master.n_cuts,
                               "proposal": None if res.get("layout") is None else res["layout"].key(),
                               "enumeration": enum_rec}
        if "ranked" in res:
            rec["ranked"] = [(v, lay.key()) for v, lay in res["ranked"]]
        out[b] = rec
    run_val, run_kind = -INF, ""
    for b in sorted(out, reverse=True):
        if run_val > out[b]["LB"] + 1e-12:
            out[b]["LB"], out[b]["kind"] = run_val, f"nested:{run_kind}"
        else:
            run_val, run_kind = out[b]["LB"], out[b]["kind"]
    if ub is not None:
        for b, rec in out.items():
            u = ub.get(b)
            rec["UB"] = None if (u is None or not math.isfinite(u)) else float(u)
            rec["gap"] = None if rec["UB"] is None else (rec["UB"] - rec["LB"]) / abs(rec["UB"]) if abs(rec["UB"]) > 0 else 0.0
    return out


# ---------------------------------------------------------------------------
# the certifier (design 3.8, 4.3)
# ---------------------------------------------------------------------------
class SitingCertifier:
    """L-shaped Benders with exact incumbent pricing for ONE target and all budgets.

    ``evaluator`` -- all-candidates pricing (``reposition='all_candidates'``); its
    ``relaxed_targets`` defines the target.  ``budgets`` -- USD, nested.  ``size_menu`` /
    ``roles`` -- the master menu.  ``lps`` -- prebuilt :class:`ScenarioLP` objects (shared
    between the two targets; their target is switched here), else they are built.  ``pool`` --
    a :class:`CutPool` (shared file; only cuts that apply to the target are loaded).
    ``L`` -- per-scenario lower bounds valid for every layout (default the evaluator's superset
    LP bound; ``0`` is valid too because every cost coefficient is nonnegative).  Tolerances:
    ``tol_rel``, ``tol_abs``.  ``on_record`` receives every record (dict).

    R7 production switches (``notes/siting_production_plan.md`` section 5; all off by default,
    so older runs are unchanged): ``lps`` may be a lazy :class:`ScenarioLPSet` (or
    ``lazy_lps=True`` builds one): an LP is built on first use and :meth:`release_lps` disposes
    them between phases; ``escalate_batch`` re-prices every open scenario of a layout in one
    pricing call (:meth:`_escalate_batch`); :meth:`mark_terminal_infeasible` applies the
    one-site feasibility skip list (no LP, no ILP; a terminal row in the master)."""

    def __init__(self, evaluator: LowerLevelEvaluator, budgets: Sequence[float],
                 size_menu: Dict[str, Sequence[Tuple[int, int]]], roles: Sequence[str], *,
                 locations: Optional[Sequence[str]] = None, s_needs_charge: bool = True,
                 access: Optional[Dict[str, Sequence[str]]] = None, lps: Optional[List[ScenarioLP]] = None,
                 pool: Optional[CutPool] = None, L: Optional[Sequence[float]] = None, M_el: float = M_EL,
                 tol_rel: float = 0.0025, tol_abs: float = 1.0, lp_threads: int = 1, master_threads: int = 1,
                 wall: Any = None, wall_margin_s: float = 120.0, on_record: Optional[Callable[[Dict[str, Any]], None]] = None,
                 use_cover: bool = True, escalate_factor: float = 3.0, escalate_cap_s: float = 1800.0,
                 max_escalations: int = 2, lp_phase_iters: int = 80, lp_stall_iters: int = 5, lp_stall_rel: float = 5e-4,
                 inout_alpha: float = 0.5, max_rounds: int = 10_000, stall_rounds: int = 3, n_screen_lp: int = 10,
                 n_screen_price: int = 3, audit_every: int = 50, label: str = "", lp_workers: int = 1,
                 max_explore_tries: int = 50, lp_method: str = "barrier", price_workers: int = 1,
                 roles_of: Optional[Dict[str, Sequence[str]]] = None, escalate_batch: bool = False,
                 lazy_lps: bool = False, escalate_batch_max: Optional[int] = None) -> None:
        if evaluator.reposition != "all_candidates":
            raise ValueError("O2 certificates need all_candidates pricing (design section 0)")
        self.ev = evaluator
        self.target = "relaxed" if evaluator.relaxed_targets else "written"
        self.budgets = sorted(float(b) for b in budgets)
        #: R7: scenario-parallel pricing threads (``price_layout(workers=...)``); 1 = sequential
        self.price_workers = max(1, int(price_workers))
        #: R7 (production plan 5 item 3): one pricing call re-prices every open scenario of a layout
        self.escalate_batch = bool(escalate_batch)
        #: R7 fixer: at escalation levels >= 2 a batch re-prices at most this many open scenarios
        #: (largest ``p_s * gap`` first, stopping once their gaps cover the layout's deficit);
        #: ``None`` = every open scenario (the first implementation)
        self.escalate_batch_max = None if escalate_batch_max is None else max(1, int(escalate_batch_max))
        self.enc = MenuEncoding(locations or [c.id for c in evaluator.candidates], size_menu, roles, evaluator.spec,
                                roles_of=(evaluator.roles_of if roles_of is None else roles_of))
        self.s_needs_charge = bool(s_needs_charge)
        self.access = access
        self.M_el = float(M_el)
        self.tol_rel, self.tol_abs = float(tol_rel), float(tol_abs)
        self.wall = wall
        self.wall_margin_s = float(wall_margin_s)
        self.on_record = on_record
        self.escalate_factor, self.escalate_cap_s = float(escalate_factor), float(escalate_cap_s)
        self.max_escalations = int(max_escalations)
        self.lp_phase_iters, self.lp_stall_iters, self.lp_stall_rel = int(lp_phase_iters), int(lp_stall_iters), float(lp_stall_rel)
        self.inout_alpha = float(inout_alpha)
        self.max_rounds, self.stall_rounds = int(max_rounds), int(stall_rounds)
        self.n_screen_lp, self.n_screen_price = int(n_screen_lp), int(n_screen_price)
        self.audit_every = int(audit_every)
        self.label = label
        self.lp_workers = max(1, int(lp_workers))
        self.max_explore_tries = int(max_explore_tries)
        self.t0 = time.perf_counter()
        self.p = list(evaluator.p)
        self.S = evaluator.n_scenarios
        self.L = [max(0.0, float(x)) for x in (L if L is not None else evaluator.superset_bound(method="lp"))]
        self._own_lps = lps is None
        if lps is not None:
            self.lps = lps                      # a prebuilt list or a lazy ScenarioLPSet (R7)
        elif lazy_lps:
            self.lps = ScenarioLPSet(evaluator, M_el=M_el, threads=lp_threads, method=lp_method,
                                     relaxed=self.target == "relaxed")
        else:
            self.lps = [ScenarioLP(evaluator, s, M_el=M_el, threads=lp_threads, method=lp_method)
                        for s in range(self.S)]
        if isinstance(self.lps, ScenarioLPSet) and abs(self.lps.M_el - self.M_el) > 0:
            raise ValueError("ScenarioLPSet M_el differs from the certifier's")
        for lp in self._built_lps():
            lp.set_target(self.target == "relaxed")
            if abs(lp.M_el - self.M_el) > 0:
                raise ValueError("ScenarioLP M_el differs from the certifier's")
        self.covers = cover_sets(evaluator, self.enc.objects) if use_cover else []
        self.uncoverable = [(s, str(k)) for s, k, objs in self.covers if not objs]
        self.master = Master(self.enc, self.p, self.L, s_needs_charge=s_needs_charge, access=access,
                             covers=self.covers, threads=master_threads)
        self.pool = pool if pool is not None else CutPool(None, pool_signature(evaluator, M_el))
        self.n_pool_loaded = 0
        for c in self.pool.for_target(self.target):
            self.n_pool_loaded += int(self.master.add_cut(c))
        # state
        self.UB = {b: INF for b in self.budgets}
        self.best: Dict[float, Optional[Layout]] = {b: None for b in self.budgets}
        self.best_price: Dict[float, Optional[PriceResult]] = {b: None for b in self.budgets}
        self.LB = {b: -INF for b in self.budgets}
        self.LB_LP: Dict[float, Optional[float]] = {b: None for b in self.budgets}
        self.closed: Dict[float, Optional[str]] = {b: None for b in self.budgets}
        self.x_star: Dict[float, Optional[np.ndarray]] = {b: None for b in self.budgets}
        self.priced: Dict[str, PriceResult] = {}
        #: R7 two-tier pricing: ``open_sites`` results (upper bounds only; never a cut, never LB)
        self.priced_open: Dict[str, PriceResult] = {}
        self.lp_memo: Dict[str, List[LPResult]] = {}
        #: R7 regional bounds: ``(frozenset(atoms), scenario) -> LBA_s`` (solved or restored from the pool)
        self.subset_memo: Dict[Tuple[frozenset, int], float] = {}
        self.lp_pruned: Set[str] = set()
        self.esc_level: Dict[Tuple[str, int], int] = {}
        #: priced (or LP-pruned) layouts the master keeps proposing although no escalation can
        #: close their pricing gap; excluded from the exploration master only (never from LB)
        self.stuck: Set[str] = set()
        self.explore_done: Dict[float, bool] = {b: False for b in self.budgets}
        #: complete admissible layout lists of the budgets whose enumeration started (the
        #: enumeration floor over such a list is a valid bound at any time)
        self.enum_lays: Dict[float, List[Layout]] = {}
        self.LB_kind: Dict[float, Optional[str]] = {b: None for b in self.budgets}
        self.LB_parts: Dict[float, Dict[str, Any]] = {b: {} for b in self.budgets}
        self.restored: Dict[str, int] = {}
        self.counters = {"lp_solves": 0, "lp_cuts": 0, "int_cuts": 0, "comb_cuts": 0, "priced": 0, "pruned_by_bound": 0,
                         "infeasible": 0, "unresolved": 0, "lp_pruned": 0, "ilp_solves": 0, "escalations": 0,
                         "master_solves": 0, "screen_layouts": 0, "explore_solves": 0, "explore_proposals": 0,
                         "enumerated": 0, "envelope_pruned": 0, "subset_lps": 0, "subset_cuts": 0, "priced_open": 0,
                         "lp_locations": 0}
        self.ilp_status: Dict[str, int] = {}
        self.max_Qt_minus_Qs = 0.0
        self.max_artificial = 0.0
        self._emit({"kind": "setup", "L": self.L, "n_options": len(self.enc.options), "n_w": self.enc.n,
                    "n_cover_rows": len(self.master.cover_rows), "uncoverable_bikes": self.uncoverable,
                    "access_empty": self.master.access_empty, "n_pool_loaded": self.n_pool_loaded,
                    "lp_sizes": [lp.size for lp in self._built_lps()], "budgets": self.budgets})

    # -- helpers ---------------------------------------------------------------------
    def _emit(self, rec: Dict[str, Any]) -> None:
        rec = {"target": self.target, "label": self.label, "elapsed_s": round(time.perf_counter() - self.t0, 2), **rec}
        if self.on_record is not None:
            self.on_record(rec)

    def _built_lps(self) -> List[ScenarioLP]:
        """The scenario LPs that exist now (all of a prebuilt list; the built ones of a lazy set)."""
        return self.lps.built() if isinstance(self.lps, ScenarioLPSet) else list(self.lps)

    def release_lps(self) -> int:
        """R7 memory lifecycle (production plan 5 item 2): dispose the built scenario LPs of a lazy
        :class:`ScenarioLPSet` (rebuilt on the next use, identical solves); ``lp_memo``, the cut
        pool and every bound are kept.  A prebuilt list cannot be rebuilt and is left alone
        (returns 0).  Returns the number of LPs disposed."""
        if not isinstance(self.lps, ScenarioLPSet):
            return 0
        n = self.lps.dispose()
        self._emit({"kind": "lp_release", "n_disposed": n, "n_built_total": self.lps.n_built,
                    "n_disposed_total": self.lps.n_disposed})
        return n

    def tol(self, ub: float) -> float:
        return tolerance(ub, self.tol_rel, self.tol_abs)

    def wall_out(self) -> bool:
        return self.wall is not None and self.wall.remaining() < self.wall_margin_s

    def fits(self, layout: Layout) -> List[float]:
        inv = layout.investment(self.ev.spec)
        return [b for b in self.budgets if inv <= b + 1e-6]

    def in_master(self, layout: Layout) -> bool:
        return self.enc.contains(layout) and self.master.rows_ok(layout)

    def ub_ref(self, layout: Layout) -> float:
        bs = self.fits(layout)
        if not bs:
            return -INF
        return max(self.UB[b] for b in bs)

    def _add_cut(self, cut: Cut) -> None:
        if self.pool.add(cut):
            self.master.add_cut(cut)

    # -- resume ------------------------------------------------------------------------
    def restore(self, records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        """Resume state from an earlier run of the SAME target: ``lp_memo`` from the pool's
        ``lp`` cuts with ``meta.tag == 'layout'`` (``Qs = c0 + beta . x`` is stored; the LP is
        not solved again), ``priced`` from the ``price`` records (last per layout: statuses,
        scenario bounds, incumbents, rows), ``lp_pruned`` from the ``lp_pruned`` records, and
        ``UB`` / ``best`` from the restored incumbents in the menu.  Records of other targets
        are ignored.  Valid because every restored quantity is a lower bound or a feasible value
        of the same problem (an LP-pruned layout stays pruned: ``UB`` only decreases).

        R7 re-plan change 1: ``price_open`` records (open-sites pricing, an upper bound only)
        are restored into ``priced_open`` (per layout the record with the lowest ``V``, else the
        last one) and their ``V`` into ``UB`` / ``best`` for in-menu layouts.  They never enter
        ``priced``, the cut pool, ``LBIP`` or the enumeration floor; the restored result keeps
        no all-candidates bound (``lb`` = the open-sites bounds of the record when present, used
        for open-sites statements only, else ``L``)."""
        by_key: Dict[str, Dict[int, LPResult]] = {}
        for c in self.pool.cuts:
            if c.kind != "lp" or c.target != self.target or c.scenario is None:
                continue
            meta = c.meta or {}
            key = meta.get("layout_key")
            if meta.get("tag") != "layout" or not key:
                continue
            try:
                lay = Layout.from_key(key)
            except (ValueError, KeyError):
                continue
            if not self.enc.contains(lay):
                continue
            x = self.enc.x_of_layout(lay)
            qs = c.c0 + sum(bv * _x_component(x, k) for k, bv in c.beta.items())
            by_key.setdefault(key, {})[int(c.scenario)] = LPResult(int(c.scenario), "OPTIMAL", meta.get("Qt"), qs, c.c0,
                                                                   dict(c.beta), relaxed=(self.target == "relaxed"),
                                                                   method="restored")
        n_lp = 0
        for key, rs in by_key.items():
            if key in self.lp_memo or set(rs) != set(range(self.S)):
                continue
            self.lp_memo[key] = [rs[s] for s in range(self.S)]
            n_lp += 1
        n_sub = 0
        for c in self.pool.cuts:                 # R7: regional bounds are valid for both targets (one-way import)
            if c.kind != "subset" or c.scenario is None or not c.applies_to(self.target):
                continue
            k = (frozenset(str(a) for a in (c.meta or {}).get("atoms") or []), int(c.scenario))
            if k[0] and k not in self.subset_memo:
                self.subset_memo[k] = max(float(c.c0), float(c.L))
                n_sub += 1
        last_price: Dict[str, Dict[str, Any]] = {}
        open_price: Dict[str, Dict[str, Any]] = {}
        pruned: Set[str] = set()
        for r in records:
            if r.get("target") != self.target:
                continue
            k = r.get("kind")
            if k == "price" and r.get("layout_key") and r.get("status") != SKIPPED_BUDGET:
                last_price[r["layout_key"]] = r
            elif k == "price_open" and r.get("layout_key") and r.get("status") != SKIPPED_BUDGET:
                prev_o = open_price.get(r["layout_key"])
                if prev_o is None or prev_o.get("V") is None or (r.get("V") is not None and float(r["V"]) <= float(prev_o["V"])):
                    open_price[r["layout_key"]] = r
            elif k == "lp_pruned" and r.get("layout_key"):
                pruned.add(r["layout_key"])
        n_pr = 0
        for key, r in last_price.items():
            if key in self.priced:
                continue
            try:
                lay = Layout.from_key(key)
            except (ValueError, KeyError):
                continue
            lb = [float(x) for x in (r.get("lb") or [])]
            ub = [None if x is None else float(x) for x in (r.get("ub") or [None] * self.S)]
            if len(lb) != self.S or len(ub) != self.S:
                continue
            pr = PriceResult(layout=lay, status=str(r.get("status")), setup=float(r.get("setup") or lay.allocated_cost(self.ev.spec)),
                             lb=lb, ub=ub, V=None if r.get("V") is None else float(r["V"]), infeasible=r.get("infeasible"),
                             rows=list(r.get("rows") or []), n_solves=0, served_share=r.get("served_share"))
            pr.lb_p = [self.p[s] * lb[s] for s in range(self.S)]
            self.priced[key] = pr
            n_pr += 1
            cnt = {"PRICED": "priced", "PRUNED_BY_BOUND": "pruned_by_bound", "INFEASIBLE": "infeasible",
                   "UNRESOLVED": "unresolved"}.get(pr.status)
            if cnt:
                self.counters[cnt] += 1
            if pr.V is not None and self.in_master(lay):
                for b in self.fits(lay):
                    if pr.V < self.UB[b] - 1e-9:
                        self.UB[b], self.best[b], self.best_price[b] = pr.V, lay, pr
        n_pruned = 0
        for key in pruned:
            if key not in self.lp_pruned and key not in self.priced:
                self.lp_pruned.add(key)
                n_pruned += 1
        n_open = self._restore_open(open_price)
        self.restored = {"lp_layouts": n_lp, "priced": n_pr, "lp_pruned": n_pruned, "subset_bounds": n_sub}
        if open_price:
            self.restored["priced_open"] = n_open
        self._emit({"kind": "restore", **self.restored, "UB": {str(b): (u if math.isfinite(u) else None) for b, u in self.UB.items()},
                    "best": {str(b): (None if l is None else l.key()) for b, l in self.best.items()}})
        return self.restored

    def _restore_open(self, open_price: Dict[str, Dict[str, Any]]) -> int:
        """Change 1 (see :meth:`restore`): ``priced_open`` and ``UB`` from ``price_open`` records."""
        n = 0
        for key, r in open_price.items():
            if key in self.priced_open:
                continue
            try:
                lay = Layout.from_key(key)
            except (ValueError, KeyError):
                continue
            ub = [None if x is None else float(x) for x in (r.get("ub") or [None] * self.S)]
            if len(ub) != self.S:
                continue
            lbo = r.get("lb_open")
            lb = [float(x) for x in lbo] if isinstance(lbo, list) and len(lbo) == self.S else list(self.L)
            pr = PriceResult(layout=lay, status=str(r.get("status")),
                             setup=float(r.get("setup") or lay.allocated_cost(self.ev.spec)), lb=lb, ub=ub,
                             V=None if r.get("V") is None else float(r["V"]), rows=list(r.get("rows") or []), n_solves=0,
                             served_share=r.get("served_share"), tier="open_sites")
            pr.lb_p = [self.p[s] * lb[s] for s in range(self.S)]
            self.priced_open[key] = pr
            n += 1
            if pr.V is not None and self.in_master(lay):      # a feasible value: an upper bound on V*_b
                for b in self.fits(lay):
                    if pr.V < self.UB[b] - 1e-9:
                        self.UB[b], self.best[b], self.best_price[b] = pr.V, lay, pr
        return n

    # -- LP ------------------------------------------------------------------------------
    def lp_at_x(self, x: Dict[str, Tuple[float, float, float]], tag: str, key: Optional[str] = None) -> List[LPResult]:
        """Solve the scenario LPs at ``x`` and add their safe optimality cuts.  The LPs may be
        shared with another certifier (other target): their end targets are set to this
        certifier's target before every solve, and every cut is tagged with the target the LP
        actually had (an inconsistency raises instead of writing a mislabelled cut)."""
        want = self.target == "relaxed"
        lps = [self.lps[s] for s in range(self.S)]      # R7: a lazy set builds the missing LPs here (main thread)
        for lp in lps:
            lp.set_target(want)
        audits = [self.audit_every > 0 and (lp.n_solves % self.audit_every == 0) for lp in lps]
        if self.lp_workers > 1 and len(lps) > 1:
            # one model and environment per scenario; gurobipy releases the GIL in optimize()
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(self.lp_workers, len(lps))) as pool:
                futs = [pool.submit(lp.solve, x, a) for lp, a in zip(lps, audits)]
                results = [f.result() for f in futs]
        else:
            results = [lp.solve(x, audit=a) for lp, a in zip(lps, audits)]
        out: List[LPResult] = []
        for s, r in enumerate(results):
            out.append(r)
            self.counters["lp_solves"] += 1
            if r.c0 is None:
                self._emit({"kind": "lp_fail", "scenario": s, "status": r.status, "tag": tag, "layout_key": key})
                continue
            self.max_Qt_minus_Qs = max(self.max_Qt_minus_Qs, (r.Qt or 0.0) - (r.Qs or 0.0))
            self.max_artificial = max(self.max_artificial, r.artificial)
            if r.relaxed is None or bool(r.relaxed) != want:
                raise AssertionError(f"ScenarioLP {s} solved with relaxed={r.relaxed}, certifier target {self.target}")
            self._add_cut(Cut(kind="lp", target="relaxed" if r.relaxed else "written", scenario=s, c0=r.c0, beta=r.beta,
                              meta={"tag": tag, "layout_key": key, "Qt": r.Qt, "Qs": r.Qs}))
            self.counters["lp_cuts"] += 1
            if r.audit and len(r.audit) > 1:
                self._emit({"kind": "lp_audit", "scenario": s, **r.audit})
        return out

    def lp_at(self, layout: Layout) -> List[LPResult]:
        key = layout.key()
        if key not in self.lp_memo:
            self.lp_memo[key] = self.lp_at_x(self.enc.x_of_layout(layout), "layout", key)
            r = self.lp_memo[key]
            self._emit({"kind": "lp_layout", "layout_key": key, "Qs": [x.Qs for x in r], "Qt": [x.Qt for x in r],
                        "artificial": [x.artificial for x in r], "v_LP": self.v_lp(layout),
                        "runtime_s": [x.runtime_s for x in r], "iterations": [x.iterations for x in r],
                        "method": [x.method for x in r]})
        return self.lp_memo[key]

    def lp_lb(self, layout: Layout) -> List[float]:
        res = self.lp_at(layout)
        return [max(self.L[s], res[s].Qs if res[s].Qs is not None else -INF) for s in range(self.S)]

    def v_lp(self, layout: Layout) -> float:
        lbs = [max(self.L[s], r.Qs if r.Qs is not None else -INF) for s, r in enumerate(self.lp_memo[layout.key()])]
        return layout.allocated_cost(self.ev.spec) + sum(p * x for p, x in zip(self.p, lbs))

    # -- pricing -------------------------------------------------------------------------
    def price(self, layout: Layout, full: bool = False, time_limit: Optional[float] = None, tag: str = "",
              scenarios: Optional[Iterable[int]] = None, tier: str = "all_candidates", lp: bool = True,
              strict_scenarios: bool = False, warm_tier: Optional[str] = None,
              ilp_params: Optional[Dict[str, Any]] = None) -> PriceResult:
        """Price ``layout`` exactly (4.2), add its integer / combinatorial cuts and update ``UB``
        (``scenarios``: solve only these scenarios, see :func:`price_layout`).

        R7: ``tier='open_sites'`` (design 2.5) prices on the cheaper open-sites library; the
        result is an upper bound only: it updates ``UB`` / ``best`` but adds NO cut, never enters
        ``priced`` (so never ``LBIP``, the enumeration floor or a comparison row) and is kept in
        ``priced_open``.  ``lp=False`` skips the per-layout scenario LPs and takes the master's
        cut envelope (``theta_floor``) as the prior bounds (B&B leaves, whose subset cut is
        already in the master).

        R7 re-plan (changes 4, 5; K3.1; all off by default): ``strict_scenarios`` (with
        ``scenarios``: uncached cells outside the filter are not solved, their bound stays the
        prior, e.g. the LP value; the result is ``UNRESOLVED`` and its ``lower`` still enters the
        enumeration floor, which is valid), ``warm_tier='open_sites'`` (all-candidates solves
        warm-started from the open-sites schedules of the same cells; a
        ``ub_check_all_candidates`` record lists the materialise / check / cost result of every
        open-sites schedule offered) and ``ilp_params`` (extra Gurobi parameters; new cache rows
        by design).  The bounds of such a pricing are all-candidates ILP bounds as before."""
        key = layout.key()
        in_menu = self.in_master(layout)
        if tier not in PRICING_TIERS:
            raise ValueError(f"tier must be one of {PRICING_TIERS}")
        if tier == "open_sites":
            return self._price_open(layout, full, time_limit, tag, scenarios, strict_scenarios=strict_scenarios,
                                    ilp_params=ilp_params)
        if self.enc.contains(layout):
            lb0 = self.lp_lb(layout) if (lp or key in self.lp_memo) else self.master.theta_floor(self.enc.w_of(layout))
        else:
            lb0 = list(self.L)
        prev = self.priced.get(key)
        if prev is not None:
            lb0 = [max(a, b) for a, b in zip(lb0, prev.lb)]
        ubr = self.ub_ref(layout) if in_menu else INF
        extra_kw: Dict[str, Any] = {}
        if strict_scenarios:
            extra_kw["strict_scenarios"] = True
        if warm_tier is not None:
            extra_kw["warm_tier"] = warm_tier
        if ilp_params:
            extra_kw["ilp_params"] = dict(ilp_params)
        res = price_layout(self.ev, layout, lb0, ubr, self.tol(ubr), full=full or not in_menu, time_limit=time_limit,
                           scenarios=scenarios, workers=self.price_workers, **extra_kw)
        self.counters["ilp_solves"] += res.n_solves
        for r in res.rows:
            if not r.get("cache_hit"):
                st = str(r.get("gurobi_status") or r.get("status"))
                self.ilp_status[st] = self.ilp_status.get(st, 0) + 1
        if prev is not None and prev.V is not None and res.V is None:
            res.V = prev.V
        if res.status != SKIPPED_BUDGET:          # a wall-skipped pricing is not a result
            self.priced[key] = res
        cnt = {"PRICED": "priced", "PRUNED_BY_BOUND": "pruned_by_bound", "INFEASIBLE": "infeasible",
               "UNRESOLVED": "unresolved"}.get(res.status)
        if cnt and prev is None:
            self.counters[cnt] += 1
        if self.enc.contains(layout):
            self._integer_cuts(layout, res)
        if res.V is not None and in_menu:
            for b in self.fits(layout):
                if res.V < self.UB[b] - 1e-9:
                    self.UB[b], self.best[b], self.best_price[b] = res.V, layout, res
        rec = {"kind": "price", "tag": tag, "layout_key": key, "status": res.status, "V": res.V,
               "lower": res.setup + sum(p * x for p, x in zip(self.p, res.lb)), "lb": res.lb, "ub": res.ub,
               "setup": res.setup, "investment": layout.investment(self.ev.spec), "in_master": in_menu,
               "ub_ref": ubr, "infeasible": res.infeasible, "rows": res.rows, "served_share": res.served_share,
               "n_solves": res.n_solves, "tier": "all_candidates", "lp": bool(lp or key in self.lp_memo)}
        if extra_kw:                              # R7 re-plan: only when a new switch is used
            rec.update(scenarios=None if scenarios is None else sorted({int(x) for x in scenarios}),
                       strict_scenarios=bool(strict_scenarios), skipped_scenarios=list(res.skipped),
                       warm_tier=warm_tier, ilp_params=dict(ilp_params or {}))
        self._emit(rec)
        if warm_tier is not None:
            self._emit_warm_check(layout, res, tag)
        return res

    def _emit_warm_check(self, layout: Layout, res: PriceResult, tag: str) -> None:
        """Change 4: the ``ub_check_all_candidates`` record of a warm-tier pricing: for every cell
        solved with an open-sites schedule offered, whether it was materialised on the
        all-candidates library, passed ``check`` and what it costs there (``warm_obj``, total
        incl. set-up), against the open-sites row total."""
        sib = _tier_evaluator(self.ev, "open_sites")
        cells = []
        for r in res.rows:
            if r.get("warm_source") != "open_sites":
                continue
            s = int(r["scenario"])
            orow, _port = sib.cached_schedule(layout, s)
            ot = None if orow is None else orow.get("total")
            wo = r.get("warm_obj")
            cells.append({"scenario": s, "materialised": r.get("warm_materialised"), "check_ok": r.get("warm_check_ok"),
                          "total": wo, "open_total": ot,
                          "same_cost": (wo is not None and ot is not None and abs(float(wo) - float(ot)) <= 1e-6 * max(1.0, abs(float(ot)))),
                          "mip_start_variant": r.get("mip_start_variant"), "status": r.get("status")})
        self._emit({"kind": "ub_check_all_candidates", "tag": tag, "source": "pricing_warm_start", "layout_key": layout.key(),
                    "cells": cells, "n_cells": len(cells),
                    "ok": bool(cells) and all(c["check_ok"] and c["same_cost"] for c in cells),
                    "note": "open_sites schedules materialised and checked on the all-candidates library"})

    def ub_check_all_candidates(self, layout: Layout, scenarios: Optional[Iterable[int]] = None,
                                tag: str = "ub_check") -> Dict[str, Any]:
        """Change 4 / M6: :func:`ub_check_all_candidates` on this certifier's (all-candidates)
        evaluator; emits the ``ub_check_all_candidates`` record (``source = 'check'``).  The UB is
        not changed (the open-sites ``V`` is already one); the record is its validity proof."""
        out = ub_check_all_candidates(self.ev, layout, scenarios)
        po = self.priced_open.get(layout.key())
        rec = {"kind": "ub_check_all_candidates", "tag": tag, "source": "check", **out,
               "V_open": None if po is None else po.V}
        self._emit(rec)
        return rec

    def _price_open(self, layout: Layout, full: bool, time_limit: Optional[float], tag: str,
                    scenarios: Optional[Iterable[int]], strict_scenarios: bool = False,
                    ilp_params: Optional[Dict[str, Any]] = None) -> PriceResult:
        key = layout.key()
        in_menu = self.in_master(layout)
        ubr = self.ub_ref(layout) if in_menu else INF
        extra_kw: Dict[str, Any] = {}
        if strict_scenarios:
            extra_kw["strict_scenarios"] = True
        if ilp_params:
            extra_kw["ilp_params"] = dict(ilp_params)
        res = price_layout(self.ev, layout, list(self.L), ubr, self.tol(ubr), full=True, time_limit=time_limit,
                           scenarios=scenarios, workers=self.price_workers, tier="open_sites", **extra_kw)
        self.counters["ilp_solves"] += res.n_solves
        self.counters["priced_open"] += 1
        if res.status != SKIPPED_BUDGET:
            self.priced_open[key] = res
        if res.V is not None and in_menu:         # a feasible value of the layout: an upper bound on V*
            for b in self.fits(layout):
                if res.V < self.UB[b] - 1e-9:
                    self.UB[b], self.best[b], self.best_price[b] = res.V, layout, res
        self._emit({"kind": "price_open", "tag": tag, "layout_key": key, "status": res.status, "V": res.V,
                    "ub": res.ub, "setup": res.setup, "investment": layout.investment(self.ev.spec), "in_master": in_menu,
                    "ub_ref": ubr, "rows": res.rows, "served_share": res.served_share, "n_solves": res.n_solves,
                    "tier": "open_sites", "note": "upper bound only: no cut, not in priced",
                    # R7 re-plan: the open-sites ILP bounds, valid for the open-sites follower ONLY
                    # (never an all-candidates bound; K2.7); used by the open-sites certificate
                    "lb_open": list(res.lb), "lower_open": res.setup + sum(p * x for p, x in zip(self.p, res.lb)),
                    **({"skipped_scenarios": list(res.skipped)} if extra_kw else {})})
        return res

    # -- R7 regional bounds (design 2.3) -----------------------------------------------
    def subset_bound(self, atoms: Iterable[str], scenarios: Optional[Sequence[int]] = None,
                     tag: str = "bnb") -> List[float]:
        """``LBA_s`` for every scenario: the free-size subset LP of :meth:`ScenarioLP.solve_subset`
        on ``scenarios`` (default all; the ``S_LP`` rule of design 2.3 passes one seed per
        stratum), ``L_s`` for the others (valid, weaker).  Every solved value is memoised and
        added to the pool / master as a ``subset`` cut (tagged relaxed; one-way import serves the
        written master too).  Needs the relaxed target."""
        A = frozenset(str(a) for a in atoms)
        want = list(range(self.S)) if scenarios is None else [int(s) for s in scenarios]
        for lp in self._built_lps():
            lp.set_target(True)
        todo = [s for s in want if (A, s) not in self.subset_memo]
        results: Dict[int, LPResult] = {}
        if todo:
            lps = {s: self.lps[s] for s in todo}    # R7: a lazy set builds only the LPs this bound needs
            for lp in lps.values():
                lp.set_target(True)
            if self.lp_workers > 1 and len(todo) > 1:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(self.lp_workers, len(todo))) as pool:
                    futs = {s: pool.submit(lps[s].solve_subset, sorted(A)) for s in todo}
                    results = {s: f.result() for s, f in futs.items()}
            else:
                results = {s: lps[s].solve_subset(sorted(A)) for s in todo}
        for s, r in results.items():
            self.counters["subset_lps"] += 1
            self.counters["lp_solves"] += 1
            if r.c0 is None or r.Qs is None:
                self._emit({"kind": "lp_fail", "scenario": s, "status": r.status, "tag": tag, "atoms": sorted(A)})
                self.subset_memo[(A, s)] = self.L[s]
                continue
            val = max(self.L[s], float(r.Qs))
            self.subset_memo[(A, s)] = val
            self.max_artificial = max(self.max_artificial, r.artificial)
            self._add_cut(Cut(kind="subset", target="relaxed", scenario=s, c0=val, L=self.L[s],
                              meta={"tag": tag, "atoms": sorted(A), "Qt": r.Qt, "Qs": r.Qs, "n_atoms": len(A)}))
            self.counters["subset_cuts"] += 1
            self._emit({"kind": "subset_lp", "scenario": s, "atoms": sorted(A), "Qs": r.Qs, "Qt": r.Qt, "L": self.L[s],
                        "runtime_s": r.runtime_s, "method": r.method, "artificial": r.artificial, "tag": tag})
        return [self.subset_memo.get((A, s), self.L[s]) if s in want else self.L[s] for s in range(self.S)]

    def _integer_cuts(self, layout: Layout, res: PriceResult) -> None:
        key = layout.key()
        if res.status == "INFEASIBLE":
            if res.infeasible == INFEASIBLE_TERMINAL:
                open_swap = {facility_id(l, r) for l, r, _B, _C in layout.open if ROLE_SWAP[r]}
                objs = [f for f in self.enc.objects if f.split(":")[-1] in ("S", "SC") and f not in open_swap]
                self._add_cut(Cut(kind="terminal", target="both", objects=objs, meta={"layout_key": key}))
            else:
                self._add_cut(Cut(kind="nogood", target=self.target, what=key, meta={"status": res.infeasible}))
            self.counters["comb_cuts"] += 1
            return
        lps = self.lp_memo.get(key)
        for s in range(self.S):
            lbip = max(res.lb[s], self.L[s])
            if lbip - self.L[s] > 1e-9:
                self._add_cut(Cut(kind="lshaped", target=self.target, scenario=s, what=key, LBIP=lbip, L=self.L[s]))
                self.counters["int_cuts"] += 1
            if lps is not None and lps[s].c0 is not None:
                l_hat = lps[s].Qs
                delta = max(0.0, lbip - l_hat)
                if delta > 1e-9:
                    self._add_cut(Cut(kind="lifted", target=self.target, scenario=s, what=key, c0=lps[s].c0,
                                      beta=lps[s].beta, Delta=delta, LBIP=lbip))
                    self.counters["int_cuts"] += 1

    def escalation_time_limit(self, layout: Layout, level: int) -> float:
        """Time limit of escalation ``level`` (0 = the evaluator's base limit of the layout)."""
        base = float(self.ev._time_limit_for(layout))
        if level <= 0:
            return base
        return min(self.escalate_cap_s, base * self.escalate_factor ** level)

    def escalate(self, layout: Layout) -> bool:
        """Re-price ONE open scenario of an already priced layout with a longer time limit (4.3):
        the scenario with the largest ``p_s (ub_s - lb_s)`` (``inf`` without incumbent) whose next
        level still raises its time limit (a level whose limit equals the previous level's, e.g.
        hub layouts at the cap, is skipped).  Levels are counted per (layout, scenario), at most
        ``max_escalations``.  ``False`` when nothing can be improved (levels used up, cap reached,
        exact, or wall)."""
        key = layout.key()
        res = self.priced.get(key)
        if res is None or res.status in ("INFEASIBLE", "PRUNED_BY_BOUND") or self.wall_out():
            return False
        rows = {}
        for r in res.rows:
            if r.get("scenario") is not None:
                rows[int(r["scenario"])] = r
        cands = []
        for s in range(self.S):
            u = res.ub[s]
            g = INF if u is None else u - res.lb[s]
            if g <= 1e-6 * max(1.0, abs(u or 0.0)):
                continue
            lvl = self.esc_level.get((key, s), 0)
            row_tl = float((rows.get(s) or {}).get("time_limit") or 0.0)
            nxt, tl = lvl + 1, None
            while nxt <= self.max_escalations:
                t = self.escalation_time_limit(layout, nxt)
                if t > max(row_tl, self.escalation_time_limit(layout, nxt - 1)) + 1e-9:
                    tl = t
                    break
                nxt += 1                        # same limit as before: a wasted level, skipped
            if tl is not None:
                cands.append((self.p[s] * g, s, nxt, tl, g))
        if not cands:
            return False
        if self.escalate_batch:
            return self._escalate_batch(layout, cands)
        _wg, s, lvl, tl, g = max(cands, key=lambda c: (c[0], -c[1]))
        self.esc_level[(key, s)] = lvl
        self.counters["escalations"] += 1
        self._emit({"kind": "escalate", "layout_key": key, "scenario": int(s), "level": lvl, "time_limit": tl,
                    "scenario_gap": g, "open_scenarios": [int(c[1]) for c in cands]})
        self.price(layout, full=True, time_limit=tl, tag="escalate", scenarios=[s])
        return True

    def _escalate_batch(self, layout: Layout, cands: Sequence[Tuple[float, int, int, float, float]]) -> bool:
        """R7 batched escalation (production plan 5 item 3): every open scenario of ``layout``
        whose next level raises its time limit (``cands`` of :meth:`escalate`) is re-priced in
        ONE pricing call (:func:`price_layout_parallel`, waves of ``price_workers``), grouped by
        time limit (normally one group: the open scenarios sit at the same level).  Levels are
        counted per (layout, scenario) exactly as in the serial escalation, the pricing is the
        same (``full``, the longer limit, warm start from the cached row), so every bound and
        incumbent is of the same kind; only the number of calls (and the wall time) changes.
        The per-layout scenario LPs are not rebuilt (``lp`` only when already in ``lp_memo``).

        R7 fixer (review of 2026-10-21): with ``escalate_batch_max`` set, a batch at level >= 2
        (the long limits) takes only the open scenarios with the largest ``p_s * gap_s`` until
        their weighted gaps cover the layout's deficit ``lower - (UB_ref - tol)`` (all of it when
        unknown), at most ``escalate_batch_max`` of them (one wave of ``price_workers``).  The
        others keep their level and are taken by a later call (the callers re-test the gap after
        every call), so a batch never pays for cells it does not need.  Level 1 keeps the full
        batch.  A choice of WHICH cells to re-price only: no bound changes."""
        key = layout.key()
        cap = self.escalate_batch_max
        if cap is not None and max(int(c[2]) for c in cands) >= 2:
            res = self.priced.get(key)
            deficit = INF
            if res is not None:
                ubr = self.ub_ref(layout)
                if math.isfinite(ubr):
                    deficit = res.lower - (ubr - self.tol(ubr))
                    deficit = -deficit if deficit < 0 else INF   # > 0: the bound must still rise by this much
            take, cover = [], 0.0
            for c in sorted(cands, key=lambda c: (-c[0], c[1])):
                if len(take) >= cap:
                    break
                take.append(c)
                cover += c[0]
                if math.isfinite(deficit) and cover >= deficit - 1e-9:
                    break
            if len(take) < len(cands):
                self.counters["escalation_cells_deferred"] = self.counters.get("escalation_cells_deferred", 0) + \
                    len(cands) - len(take)
            cands = take
        groups: Dict[float, List[Tuple[float, int, int, float, float]]] = {}
        for c in cands:
            groups.setdefault(float(c[3]), []).append(c)
        self.counters.setdefault("escalation_waves", 0)
        ran = False
        for tl in sorted(groups):
            if ran and self.wall_out():
                break
            grp = sorted(groups[tl], key=lambda c: (-c[0], c[1]))
            scen = [int(c[1]) for c in grp]
            for _wg, s, lvl, _tl, _g in grp:
                self.esc_level[(key, s)] = lvl
            self.counters["escalations"] += len(scen)
            self.counters["escalation_waves"] += 1
            self._emit({"kind": "escalate", "layout_key": key, "scenario": scen[0], "scenarios": scen,
                        "level": max(int(c[2]) for c in grp), "levels": [int(c[2]) for c in grp], "time_limit": tl,
                        "scenario_gap": [c[4] for c in grp], "open_scenarios": [int(c[1]) for c in cands], "batched": True})
            self.price(layout, full=True, time_limit=tl, tag="escalate", scenarios=scen, lp=key in self.lp_memo)
            ran = True
        return ran

    # -- R7 feasibility skip list (production plan 5 item 4) ------------------------------
    def mark_terminal_infeasible(self, location: str, scenario: int, *, role: str = "SC",
                                 bikes: Optional[Sequence[Any]] = None, source: str = "") -> int:
        """Mark every one-site layout ``location:role:B:C`` of the menu INFEASIBLE_TERMINAL
        (``V = inf``) without an LP or an ILP, given a proof that the one-site layout at
        ``location`` has a bike without a reachable terminal arc in scenario ``scenario`` under
        THIS evaluator's configuration (:func:`verify_terminal_infeasible`, or a screen with the
        same :func:`feasibility_signature`).  Valid for every size option: under the
        all-candidates convention the layout library keeps the swap / terminal arcs of the open
        swap objects only (``sites_nyc.subset_library``); ``B`` and ``C`` enter neither the arcs
        nor the reachability pass (test ``test_one_site_terminal_feasibility_does_not_depend_on_sizes``).

        The master gets the terminal row of :meth:`_integer_cuts`: the other swap objects sum to
        at least 1.  Under the master's structural rows (a swap object; swap-only next to a
        charge object) it implies the window row ``y_l <= sum_{l' != l} y_l'`` of the plan, and
        it also excludes ``location:role`` together with charge-only hubs elsewhere, infeasible by
        the same argument (a hub adds no swap or terminal arc); it never excludes a layout with
        another swap object.  One ``price`` record per layout (tag ``feas_skip``, ``n_solves 0``)
        so that :meth:`restore` keeps the marks.  Returns the number of layouts newly marked."""
        if self.ev.reposition != "all_candidates":
            raise ValueError("terminal-infeasibility marks need all_candidates pricing")
        if not ROLE_SWAP[role]:
            raise ValueError(f"role {role} has no terminal arc")
        loc = str(location)
        if loc not in set(self.enc.locations) or role not in self.enc.roles_of.get(loc, ()):
            return 0
        n = 0
        for o in [o for o in self.enc.options if o[0] == role]:
            lay = Layout.of([(loc,) + tuple(o)])
            key = lay.key()
            prev = self.priced.get(key)
            if prev is not None and prev.status == "INFEASIBLE":
                continue
            if prev is not None and prev.V is not None:
                raise AssertionError(f"{key}: priced feasible (V {prev.V}) but marked terminal-infeasible")
            setup = lay.allocated_cost(self.ev.spec)
            in_menu = self.in_master(lay)
            row = {"scenario": int(scenario), "status": INFEASIBLE_TERMINAL, "gurobi_status": None, "total": None,
                   "opex": None, "bound": None, "C_setup": setup, "gap": None, "runtime_s": 0.0, "cache_hit": False,
                   "best_bd_stop": None, "time_limit": None, "key": None, "error": None,
                   "infeasible_bikes": [str(b) for b in (bikes or [])], "source": source}
            res = PriceResult(layout=lay, status="INFEASIBLE", setup=setup, lb=list(self.L), ub=[None] * self.S,
                              infeasible=INFEASIBLE_TERMINAL, rows=[row], n_solves=0)
            res.lb_p = [self.p[s] * self.L[s] for s in range(self.S)]
            self.priced[key] = res
            if prev is None:
                self.counters["infeasible"] += 1
            self._integer_cuts(lay, res)
            self._emit({"kind": "price", "tag": "feas_skip", "layout_key": key, "status": "INFEASIBLE", "V": None,
                        "lower": res.setup + sum(res.lb_p), "lb": res.lb, "ub": res.ub, "setup": setup,
                        "investment": lay.investment(self.ev.spec), "in_master": in_menu, "ub_ref": None,
                        "infeasible": INFEASIBLE_TERMINAL, "rows": [row], "served_share": None, "n_solves": 0,
                        "tier": "all_candidates", "lp": False, "source": source, "proof_scenario": int(scenario)})
            n += 1
        return n

    # -- bookkeeping -------------------------------------------------------------------
    def _nested_lb(self) -> None:
        run = -INF
        for b in reversed(self.budgets):            # V*_m >= V*_{m'} for m <= m'
            run = max(run, self.LB[b])
            self.LB[b] = run

    def gap(self, b: float) -> Optional[float]:
        ub, lb = self.UB[b], self.LB[b]
        if not math.isfinite(ub):
            return None
        return (ub - lb) / abs(ub) if abs(ub) > 0 else 0.0

    def is_closed(self, b: float) -> bool:
        ub, lb = self.UB[b], self.LB[b]
        if lb == INF:
            return True
        return math.isfinite(ub) and ub - lb <= self.tol(ub) + 1e-9

    # -- phases ---------------------------------------------------------------------
    def warm_start(self, layouts: Sequence[Optional[Layout]], release_lps: bool = False,
                   before_pricing: Optional[Callable[[], bool]] = None) -> None:
        """Price the warm layouts (each after its scenario LPs).  R7 fixer (memory, review of
        2026-10-21): with ``release_lps`` the LPs of EVERY warm layout are solved first, then the
        lazy scenario LPs are disposed (:meth:`release_lps`; ``lp_memo`` keeps the values, so the
        pricings rebuild no LP), and only then the layouts are priced: the scenario LPs and the
        pricing ILPs are never resident together.  ``before_pricing`` (e.g. an RSS guard) is
        called once before the first pricing; ``False`` skips the pricings (the LP values and
        cuts stay).  The default is the old interleaved order."""
        if not release_lps:
            for lay in layouts:
                if lay is None or not lay.n_open or self.wall_out():
                    continue
                if lay.key() in self.priced:
                    continue
                if self.enc.contains(lay):
                    self.lp_at(lay)
                self.price(lay, full=not self.in_master(lay), tag="warm")
            return
        todo = [lay for lay in layouts if lay is not None and lay.n_open and lay.key() not in self.priced]
        for lay in todo:
            if self.wall_out():
                break
            if self.enc.contains(lay):
                self.lp_at(lay)
        self.release_lps()
        if before_pricing is not None and not before_pricing():
            return
        for lay in todo:
            if self.wall_out():
                break
            if lay.key() in self.priced:
                continue
            self.price(lay, full=not self.in_master(lay), tag="warm", lp=lay.key() in self.lp_memo)

    def lp_phase(self) -> None:
        """LP master with Kelley cuts and in-out stabilisation (3.6), per budget, shared cuts.
        Budgets already closed (certified or enumerated) are skipped."""
        for b in self.budgets:
            if self.wall_out():
                break
            if self.closed[b] is not None:
                continue
            core = None
            inside = [self.enc.w_of(l) for l in {lay.key(): lay for lay in self.best.values() if lay is not None}.values()
                      if l.investment(self.ev.spec) <= b + 1e-6 and self.in_master(l)]
            inside += [self.enc.w_of(r.layout) for r in self.priced.values()
                       if r.layout.investment(self.ev.spec) <= b + 1e-6 and self.in_master(r.layout)
                       and r.status in ("PRICED", "PRUNED_BY_BOUND", "UNRESOLVED")]
            if inside:
                core = np.mean(np.array(inside), axis=0)
            alpha = self.inout_alpha if core is not None else 0.0
            hist: List[float] = []
            last = None
            for it in range(self.lp_phase_iters):
                if self.wall_out():
                    break
                res = self.master.solve(b, relax=True)
                self.counters["master_solves"] += 1
                if res.get("w") is None:
                    self._emit({"kind": "lp_phase", "budget": b, "iteration": it, "status": res["status"]})
                    break
                wm, th = res["w"], res["theta"]
                hist.append(res["obj"])
                last = res
                x_sep = alpha * core + (1.0 - alpha) * wm if alpha > 0 else wm
                r_sep = self.lp_at_x(self.enc.x_of(x_sep), "lp_phase_sep")
                cutoff = any(r.c0 is not None and r.value_at(self.enc.x_of(wm)) > th[s] + 1e-6 * max(1.0, abs(th[s]))
                             for s, r in enumerate(r_sep))
                if not cutoff and alpha > 0:
                    r_m = self.lp_at_x(self.enc.x_of(wm), "lp_phase")
                    cutoff = any(r.c0 is not None and (r.Qs or -INF) > th[s] + 1e-6 * max(1.0, abs(th[s]))
                                 for s, r in enumerate(r_m))
                if not cutoff:
                    break                       # no cut separates the LP master point: converged
                if core is not None:
                    core = 0.5 * (core + wm)
                if len(hist) > self.lp_stall_iters and \
                        hist[-1] - hist[-1 - self.lp_stall_iters] <= self.lp_stall_rel * max(1.0, abs(hist[-1])):
                    if alpha > 0:
                        alpha = 0.0             # Kelley from here on
                    else:
                        break
            if last is not None:
                final = self.master.solve(b, relax=True)
                self.counters["master_solves"] += 1
                if final.get("w") is not None:
                    self.LB_LP[b] = float(final["obj"])
                    self.x_star[b] = final["w"]
                    if float(final["obj"]) > self.LB[b]:
                        self.LB[b], self.LB_kind[b] = float(final["obj"]), "lp_phase"
            self._emit({"kind": "lp_phase", "budget": b, "iterations": len(hist), "LB_LP": self.LB_LP[b],
                        "history": [round(h, 6) for h in hist[-20:]]})
        self._nested_lb()

    def screen(self) -> None:
        """Relax-and-round per budget (design 5): cut envelope -> LP of the top ``n_screen_lp``
        -> exact pricing of the top ``n_screen_price`` that survive the LP test."""
        for b in self.budgets:
            if self.wall_out() or self.x_star[b] is None or self.closed[b] is not None:
                continue
            wst = self.x_star[b]
            x = self.enc.x_of(wst)
            rs = self.lp_at_x(x, "screen")
            usage: Dict[str, Dict[str, float]] = {}
            for s, r in enumerate(rs):
                for f, u in r.usage.items():
                    acc = usage.setdefault(f, {})
                    for k, v in u.items():
                        acc[k] = acc.get(k, 0.0) + self.p[s] * v
            cands = relax_and_round(self.enc, wst, usage, b, self.in_master)
            self.counters["screen_layouts"] += len(cands)
            ranked = sorted(cands, key=lambda l: (self.master.envelope(l), l.key()))[:self.n_screen_lp]
            for l in ranked:
                self.lp_at(l)
            ranked.sort(key=lambda l: (self.v_lp(l), l.key()))
            n = 0
            for l in ranked:
                if n >= self.n_screen_price or self.wall_out():
                    break
                if l.key() in self.priced:
                    continue
                ubr = self.ub_ref(l)
                if self.v_lp(l) >= ubr - self.tol(ubr):
                    self.lp_pruned.add(l.key())
                    continue
                self.price(l, tag="screen")
                n += 1
            self._emit({"kind": "screen", "budget": b, "n_candidates": len(cands), "ranked": [l.key() for l in ranked]})

    def _try_new(self, lay: Layout, tag: str) -> str:
        """LP test (C5) and, unless LP-pruned, exact pricing of a layout not seen before.
        Returns ``'lp_pruned'``, ``'priced'`` or ``'skipped'`` (wall)."""
        key = lay.key()
        self.lp_at(lay)
        ubr = self.ub_ref(lay)
        if self.v_lp(lay) >= ubr - self.tol(ubr):
            self.lp_pruned.add(key)
            self.counters["lp_pruned"] += 1
            self._emit({"kind": "lp_pruned", "layout_key": key, "v_LP": self.v_lp(lay), "ub_ref": ubr, "tag": tag})
            return "lp_pruned"
        pr = self.price(lay, tag=tag)
        return "skipped" if pr.status == SKIPPED_BUDGET else "priced"

    def _explore(self, b: float, rnd: int) -> bool:
        """Search completeness: the master proposed a layout that is already resolved as far as
        it can be (priced, no escalation left).  Re-solve a copy of the master with no-goods on
        all such ``stuck`` layouts and handle its proposal (escalate, LP-prune or price).
        ``True`` when something new was learnt.  When the copy's bound reaches ``UB - tol`` (or
        it is infeasible), every layout outside ``stuck`` is resolved: ``explore_done[b]``."""
        for _ in range(max(1, self.max_explore_tries)):
            if self.wall_out():
                return False
            ub = self.UB[b]
            thr = ub - self.tol(ub) if math.isfinite(ub) else INF
            excl = [Layout.from_key(k) for k in sorted(self.stuck)]
            res = self.master.solve_excluding(b, excl)
            self.counters["master_solves"] += 1
            self.counters["explore_solves"] += 1
            lay = res.get("layout")
            bound = res.get("bound")
            done = res["status"] == "INFEASIBLE" or lay is None or (bound is not None and bound >= thr - 1e-9)
            self._emit({"kind": "explore", "round": rnd, "budget": b, "status": res["status"], "bound": bound,
                        "obj": res.get("obj"), "proposal": None if lay is None else lay.key(), "UB": ub,
                        "n_stuck": len(self.stuck), "done": bool(done)})
            if done:
                if res["status"] in ("OPTIMAL", "INFEASIBLE"):
                    self.explore_done[b] = True
                return False
            key = lay.key()
            if key in self.priced:
                if self.escalate(lay):
                    return True
                self.stuck.add(key)
                continue
            if key in self.lp_pruned:
                self.stuck.add(key)
                continue
            self.counters["explore_proposals"] += 1
            st = self._try_new(lay, "explore")
            return st != "skipped"
        return False

    def integer_phase(self) -> None:
        stall = {b: 0 for b in self.budgets}
        for rnd in range(self.max_rounds):
            open_b = [b for b in self.budgets if self.closed[b] is None]
            if not open_b:
                break
            if self.wall_out():
                for b in open_b:
                    self.closed[b] = "wall"
                break
            proposals: Dict[str, Tuple[Layout, List[float]]] = {}
            for b in open_b:
                res = self.master.solve(b, start=self.best[b])
                self.counters["master_solves"] += 1
                if res.get("bound") is not None and float(res["bound"]) > self.LB[b]:
                    self.LB[b], self.LB_kind[b] = float(res["bound"]), "master"
                self._nested_lb()
                if res["status"] == "INFEASIBLE" or self.LB[b] == INF:
                    self.closed[b] = NO_ADMISSIBLE
                    continue
                if self.is_closed(b):
                    self.closed[b] = "gap"
                    continue
                lay = res.get("layout")
                if lay is None:
                    continue
                proposals.setdefault(lay.key(), (lay, []))[1].append(b)
                self._emit({"kind": "master", "round": rnd, "budget": b, "status": res["status"], "bound": res.get("bound"),
                            "obj": res.get("obj"), "proposal": lay.key(), "UB": self.UB[b], "n_cuts": self.master.n_cuts})
            progress: Set[float] = set()
            for key, (lay, bs) in proposals.items():
                if self.wall_out():
                    break
                if key in self.priced or key in self.lp_pruned:
                    if key in self.priced and self.escalate(lay):
                        progress.update(bs)
                        continue
                    # resolved as far as it can be: explore the rest of the menu instead of stalling
                    self.stuck.add(key)
                    for b in bs:
                        if self.closed[b] is None and not self.explore_done[b] and self._explore(b, rnd):
                            progress.add(b)
                    continue
                st = self._try_new(lay, "integer")
                if st == "skipped":
                    break
                progress.update(bs)
            for b in open_b:
                if self.closed[b] is not None:
                    continue
                if self.explore_done[b]:
                    n_open = sum(1 for k in self.stuck if k in self.priced
                                 and self.priced[k].lower < self.UB[b] - self.tol(self.UB[b]) - 1e-9)
                    self.closed[b] = (f"open pricing gaps only ({n_open} priced layouts below UB - tol, escalations "
                                      "used up; every other layout resolved)")
                    continue
                stall[b] = 0 if b in progress else stall[b] + 1
                if stall[b] >= self.stall_rounds:
                    self.closed[b] = "stalled (no new proposal; open pricing gaps)"
        for b in self.budgets:
            if self.closed[b] is None:
                self.closed[b] = "round limit"

    # -- enumeration (measurement gate, design section 8 step 3) ----------------------------
    def access_nonempty(self) -> Optional[Dict[str, List[str]]]:
        """The access rows the master actually enforces (zones with an empty set dropped)."""
        if not self.access:
            return None
        return {str(z): list(ls) for z, ls in self.access.items() if str(z) not in set(self.master.access_empty)}

    def menu_layouts(self, b: float, k_range: Optional[Sequence[int]] = None, inv_lo: float = -INF) -> List[Layout]:
        """All admissible menu layouts within budget ``b`` (master structural rows: one option per
        location, a swap object, swap-only next to charge, non-empty access zones); ``k_range`` /
        ``inv_lo`` as in :func:`menu_layouts`."""
        return menu_layouts(self.ev, self.enc, b, access=self.access_nonempty(), s_needs_charge=self.s_needs_charge,
                            k_range=k_range, inv_lo=inv_lo)

    def lp_gap_cells(self) -> List[float]:
        """``(Q_IP - Q_LP) / Q_IP`` over the scenario cells of every fully priced menu layout with
        an LP solve (``Q_IP`` = the row incumbent, ``Q_LP`` = the safe value ``Qs``)."""
        out: List[float] = []
        for key, pr in self.priced.items():
            lr = self.lp_memo.get(key)
            if lr is None or pr.status != "PRICED":
                continue
            for s in range(self.S):
                qi, ql = pr.ub[s], lr[s].Qs
                if qi is not None and ql is not None and abs(qi) > 1e-9:
                    out.append((float(qi) - float(ql)) / abs(float(qi)))
        return out

    def _known_v_lp(self) -> Dict[str, float]:
        """Safe LP values ``v_LP`` of every layout with an LP solve (memo or restored)."""
        out: Dict[str, float] = {}
        for key, rs in self.lp_memo.items():
            if all(r.c0 is not None for r in rs):
                out[key] = self.v_lp(Layout.from_key(key))
        return out

    def _known_priced(self) -> Dict[str, Tuple[str, float]]:
        return {key: (pr.status, pr.lower) for key, pr in self.priced.items()}

    def _n_priced_on_open(self, keys: Iterable[str]) -> int:
        """Label only (M4 record): layouts of ``keys`` with an open-sites price that is PRICED
        with a value; UNRESOLVED / INFEASIBLE / bound-stopped open records are not counted."""
        n = 0
        for k in keys:
            pr = self.priced_open.get(k)
            if pr is not None and pr.status == "PRICED" and pr.V is not None:
                n += 1
        return n

    def enum_open_priced(self, b: float, lays: Sequence[Layout]) -> List[Tuple[float, str, Layout]]:
        """Priced layouts of ``lays`` (admissible within ``b``) whose best known lower value
        ``max(envelope, v_LP, lower)`` is still below ``UB_b - tol`` (open pricing gaps), lowest
        first.  ``INFEASIBLE`` layouts have ``V = inf`` and bound-stopped ones
        (``PRUNED_BY_BOUND``) were proven ``>= ub_ref - tol`` with ``ub_ref >= UB_b``, so both are
        resolved; ``UNRESOLVED`` layouts (a scenario without incumbent) are open.  Without an
        incumbent (``UB = inf``) every priced layout is open."""
        ub = self.UB[b]
        thr = ub - self.tol(ub) if math.isfinite(ub) else INF
        v_lp = self._known_v_lp()
        out: List[Tuple[float, str, Layout]] = []
        for l in lays:
            key = l.key()
            pr = self.priced.get(key)
            if pr is None or pr.status not in ("PRICED", "UNRESOLVED"):
                continue
            lo = max(self.master.envelope(l), v_lp.get(key, -INF), pr.lower)
            if lo < thr - 1e-9:
                out.append((lo, key, l))
        out.sort(key=lambda t: (t[0], t[1]))
        return out

    def enum_floor(self, b: float) -> Optional[Tuple[float, Optional[str], Dict[str, int]]]:
        """Enumeration floor of budget ``b`` (:func:`enumeration_floor` over its complete
        admissible layout list, known at any time once the enumeration started); ``None`` when
        the enumeration of ``b`` never started."""
        lays = self.enum_lays.get(b)
        if lays is None:
            return None
        return enumeration_floor(self.master, lays, self._known_v_lp(), self._known_priced())

    def _enum_order(self, lays: Sequence[Layout]) -> List[Tuple[Layout, float]]:
        """Location-major order (all options of one site set together, site sets by their best
        envelope), envelope ascending within a site set."""
        env = {l.key(): self.master.envelope(l) for l in lays}
        groups: Dict[Tuple[str, ...], List[Layout]] = {}
        for l in lays:
            groups.setdefault(tuple(l.locations()), []).append(l)
        out: List[Tuple[Layout, float]] = []
        for locs in sorted(groups, key=lambda g: (min(env[l.key()] for l in groups[g]), g)):
            for l in sorted(groups[locs], key=lambda l: (env[l.key()], l.key())):
                out.append((l, env[l.key()]))
        return out

    def _envelope_prune(self, l: Layout, env: Optional[float], tag: str) -> bool:
        """LP-free prune (C5 with the cut envelope): ``envelope(l) >= UB - tol`` for the largest
        budget the layout fits.  Valid because ``envelope(l) <= v_LP(l) <= V(l)`` (every cut is
        valid at every admissible integer point).  Records ``lp_pruned`` with the envelope."""
        key = l.key()
        ubr = self.ub_ref(l)
        if not math.isfinite(ubr):
            return False
        if env is None:
            env = self.master.envelope(l)
        if env >= ubr - self.tol(ubr):
            self.lp_pruned.add(key)
            self.counters["lp_pruned"] += 1
            self.counters["envelope_pruned"] += 1
            self._emit({"kind": "lp_pruned", "layout_key": key, "v_LP": None, "envelope": env, "ub_ref": ubr, "tag": tag,
                        "by": "envelope"})
            return True
        return False

    def _enum_exit(self, b: float, rec: Dict[str, Any], reason: str, lays: Optional[Sequence[Layout]] = None,
                   update_lb: bool = True) -> Dict[str, Any]:
        """Partial exit of the enumeration: raise ``LB[b]`` to the enumeration floor (valid at any
        time over the complete layout list) and record it.  With ``update_lb=False`` (a partial
        list) the floor over ``lays`` is only reported (``LB_enum``)."""
        if lays is not None and not update_lb:
            lowest, arg, cnt = enumeration_floor(self.master, lays, self._known_v_lp(), self._known_priced())
            rec.update(LB_floor=lowest, LB_enum=lowest, argmin=arg, **cnt)
            rec.update(done=False, reason=reason, UB=self.UB[b] if math.isfinite(self.UB[b]) else None)
            self._emit(rec)
            return rec
        fl = self.enum_floor(b)
        if fl is not None:
            lowest, arg, cnt = fl
            if lowest > self.LB[b]:
                self.LB[b] = lowest
                self.LB_kind[b] = "enumeration"
            self._nested_lb()
            rec.update(LB_floor=lowest, LB_enum=lowest, argmin=arg, **cnt)
        rec.update(done=False, reason=reason, UB=self.UB[b] if math.isfinite(self.UB[b]) else None)
        self._emit(rec)
        return rec

    def rep_option(self, role: str = "SC", target: Tuple[int, int] = (3, 2)) -> Optional[Tuple[str, int, int]]:
        """Representative menu option of ``role`` nearest to ``target`` sizes (design 2.2: ``SC:B3:C2``)."""
        opts = [o for o in self.enc.options if o[0] == role]
        if not opts:
            return None
        return min(opts, key=lambda o: (abs(o[1] - target[0]) + abs(o[2] - target[1]), -o[1], -o[2]))

    def lp_per_location(self, locations: Optional[Sequence[str]] = None, option: Optional[Tuple[str, int, int]] = None,
                        tag: str = "location") -> Dict[str, float]:
        """R7 (design 2.2 item 1): one scenario-LP solve per location at the representative
        option BEFORE any envelope prune, so that every candidate has an LP value (the siting
        landscape of the map).  Locations that already have an LP solve of the representative
        layout are not solved again.  Emits ``lp_location`` records; returns ``{loc: v_LP}``."""
        opt = option or self.rep_option()
        out: Dict[str, float] = {}
        if opt is None:
            return out
        for l in (locations or self.enc.locations):
            if self.wall_out():
                break
            if opt[0] not in self.enc.roles_of.get(l, ()):
                alt = next((o for o in self.enc.options if o[0] in self.enc.roles_of.get(l, ())), None)
                if alt is None:
                    continue
                lay = Layout.of([(l,) + alt])
            else:
                lay = Layout.of([(l,) + opt])
            fresh = lay.key() not in self.lp_memo
            rs = self.lp_at(lay)
            v = self.v_lp(lay)
            out[l] = v
            if fresh:
                self.counters["lp_locations"] += 1
            self._emit({"kind": "lp_location", "location": l, "layout_key": lay.key(), "v_LP": v,
                        "Qs": [r.Qs for r in rs], "tag": tag, "fresh": fresh})
        return out

    def certify_by_enumeration(self, b: float, limit: int = 5000, prune: bool = True,
                               force_lp_per_location: bool = False, layouts: Optional[Sequence[Layout]] = None,
                               update_lb: bool = True, tag: str = "enumerate",
                               skip_locations: Optional[Iterable[str]] = None,
                               release_lps: bool = False, price_pass: bool = True) -> Dict[str, Any]:
        """Certify budget ``b`` by enumeration (design section 8 step 3, used when the
        fixed-layout LP gap is too large for the Benders bound).  Pass 1, in location-major /
        envelope order: a layout whose cut envelope (current pool and superset bound) already
        reaches ``UB - tol`` is pruned WITHOUT an LP (``lp_pruned`` record, ``by = envelope``);
        the others get their scenario LPs (cuts added).  Pass 2, in ``v_LP`` order: each layout
        is pruned again against the envelope (which rises with the integer cuts of every pricing)
        and ``v_LP``, else priced with BestBdStop.  The enumeration floor ``min_l
        max(envelope(l), v_LP(l), lower(l))`` over the complete list is a valid lower bound on
        ``V*_b`` at any time (also when the wall stops the enumeration half way); ``LB[b]`` is
        raised to it and propagated to smaller budgets.  Pass 3 escalates the priced layouts
        whose pricing gap keeps them below ``UB - tol`` (:meth:`escalate`, lowest first, the open
        set recomputed after every call) until the budget closes or the levels are used up.  The
        budget is closed when the enumeration finishes (``close_reason`` says whether open pricing
        gaps remain).  Layouts already LP-solved, priced or pruned (e.g. restored on resume) are
        not solved again.

        ``layouts`` (fixer pass, :func:`certify_bnb`): enumerate this list instead of every
        admissible layout of ``b`` (a budget window, e.g. the one-site layouts with investment
        above the smaller budget); the returned ``LB_enum`` is then the floor over that list
        only, so ``update_lb=False`` keeps ``LB[b]`` and ``closed[b]`` untouched (the caller
        combines the floors).  ``tag`` names the records.

        R7 (production plan 5 items 2 and 4): ``skip_locations`` are left out of the forced
        LP per location (terminal-infeasible locations, whose one-site layouts are already
        marked by :meth:`mark_terminal_infeasible`); ``release_lps`` disposes the scenario LPs
        of a lazy :class:`ScenarioLPSet` between pass 1 (LPs) and pass 2 (pricing), where only
        ``lp_memo`` and the cuts are needed.

        R7 re-plan change 5 (``--m1-pass2 off``): with ``price_pass=False`` pass 2 applies the
        prune tests (envelope, ``v_LP``) but prices nothing, and pass 3 (escalation) is skipped.
        The layouts left unpriced below ``UB - tol`` are listed (``unpriced``); the floor is
        computed exactly as before (their ``v_LP`` enters it), so ``LB`` stays valid, and the
        budget closes with a reason that names them unless the gap itself is closed."""
        lays = list(layouts) if layouts is not None else self.menu_layouts(b)
        rec: Dict[str, Any] = {"kind": "enumerate", "tag": tag, "budget": b, "n_layouts": len(lays), "prune": bool(prune),
                               "partial_list": layouts is not None}
        if len(lays) > limit:
            rec.update(done=False, reason=f"{len(lays)} layouts > limit {limit}")
            self._emit(rec)
            return rec
        if update_lb:
            self.enum_lays[b] = lays
        n_lp = n_env = 0
        if force_lp_per_location:               # R7: every location gets its LP value first
            locs = sorted({l.locations()[0] for l in lays if l.n_open == 1})
            if skip_locations is not None:      # R7: terminal-infeasible locations get no LP
                skip = {str(x) for x in skip_locations}
                rec["lp_per_location_skipped"] = sorted(set(locs) & skip)
                locs = [l for l in locs if l not in skip]
                rec["lp_per_location"] = len(self.lp_per_location(locs, tag="enumerate")) if locs else 0
            else:
                rec["lp_per_location"] = len(self.lp_per_location(locs, tag="enumerate"))
        for l, env in self._enum_order(lays):
            key = l.key()
            if key in self.priced or key in self.lp_pruned or key in self.lp_memo:
                continue
            if env == INF:                      # excluded by a row cut / cover row: V = inf
                continue
            if self.wall_out():
                rec.update(n_lp=n_lp, n_envelope_pruned=n_env)
                return self._enum_exit(b, rec, "wall", lays, update_lb)
            if prune and self._envelope_prune(l, env, tag):
                n_env += 1
                continue
            self.lp_at(l)
            n_lp += 1
        if release_lps:                         # R7: pass 2 needs lp_memo and the cuts, not the LPs
            rec["lp_released"] = self.release_lps()
        todo = [l for l in lays if l.key() not in self.priced and l.key() not in self.lp_pruned and l.key() in self.lp_memo]
        todo.sort(key=lambda l: (self.v_lp(l), l.key()))
        n_price = n_prune = 0
        unpriced: List[Tuple[float, str]] = []
        if not price_pass:
            rec["price_pass"] = False
        for l in todo:
            key = l.key()
            if key in self.priced or key in self.lp_pruned:
                continue
            if self.wall_out():
                rec.update(n_lp=n_lp, n_envelope_pruned=n_env, n_priced=n_price, n_lp_pruned=n_prune)
                return self._enum_exit(b, rec, "wall", lays, update_lb)
            if prune and self._envelope_prune(l, None, tag):
                n_env += 1
                continue
            ubr = self.ub_ref(l)
            if self.v_lp(l) >= ubr - self.tol(ubr):
                self.lp_pruned.add(key)
                self.counters["lp_pruned"] += 1
                n_prune += 1
                self._emit({"kind": "lp_pruned", "layout_key": key, "v_LP": self.v_lp(l), "ub_ref": ubr,
                            "tag": tag, "by": "v_LP"})
                continue
            if not price_pass:                  # change 5: test the prunes only, price nothing
                unpriced.append((self.v_lp(l), key))
                continue
            pr = self.price(l, tag=tag)
            n_price += 1
            if pr.status == SKIPPED_BUDGET:
                rec.update(n_lp=n_lp, n_envelope_pruned=n_env, n_priced=n_price, n_lp_pruned=n_prune)
                return self._enum_exit(b, rec, "wall", lays, update_lb)
        # pass 3: the priced layouts with open pricing gaps are escalated (one scenario per call,
        # the lowest layout first; the open set is recomputed after every call because UB can
        # drop and the envelope rises with the new integer cuts) until none is open, every
        # escalation level is used up (``escalate`` returns False for all of them) or the wall.
        # Without this pass the budget would close as "enumerated (open pricing gaps)" and the
        # integer phase, which skips closed budgets, could never escalate them.
        n_esc = 0
        n_open_before = len(self.enum_open_priced(b, lays))
        while price_pass:
            if self.wall_out():
                rec.update(n_lp=n_lp, n_envelope_pruned=n_env, n_priced=n_price, n_lp_pruned=n_prune, n_escalations=n_esc,
                           n_open_before_escalation=n_open_before)
                return self._enum_exit(b, rec, "wall", lays, update_lb)
            open_ = self.enum_open_priced(b, lays)
            if not open_:
                break
            progressed = False
            for _lo, _key, l in open_:
                if self.escalate(l):
                    n_esc += 1
                    progressed = True
                    break
            if not progressed:
                break
        lowest, arg, cnt = enumeration_floor(self.master, lays, self._known_v_lp(), self._known_priced())
        self.counters["enumerated"] += len(lays)
        if update_lb and lowest > self.LB[b]:
            self.LB[b] = lowest
            self.LB_kind[b] = "enumeration"
        if update_lb:
            self._nested_lb()
        open_left = self.enum_open_priced(b, lays)
        if update_lb and self.closed[b] is None:
            if self.is_closed(b):
                self.closed[b] = NO_ADMISSIBLE if self.LB[b] == INF else "gap"
            elif unpriced:
                n_up_open = self._n_priced_on_open(k for _v, k in unpriced)
                self.closed[b] = (f"enumerated without pricing (--m1-pass2 off: {len(unpriced)} layouts with v_LP below "
                                  f"UB - tol not priced on the all-candidates tier ({n_up_open} of them priced on "
                                  f"open_sites)"
                                  + (f", {len(open_left)} priced layouts with open pricing gaps)" if open_left else ")"))
            elif open_left:
                self.closed[b] = (f"enumerated (open pricing gaps: {len(open_left)} priced layouts below UB - tol, "
                                  f"escalations used up after {n_esc} calls)")
            else:
                self.closed[b] = "enumerated (floor below UB - tol)"
        rec.update(done=True, LB_enum=lowest, argmin=arg, UB=self.UB[b] if math.isfinite(self.UB[b]) else None,
                   n_lp=n_lp, n_envelope_pruned=n_env, n_priced=n_price, n_lp_pruned=n_prune,
                   gap=self.gap(b) if math.isfinite(self.LB[b]) else None,
                   n_escalations=n_esc, n_open_before_escalation=n_open_before, n_open_priced=len(open_left),
                   open_priced=[k for _lo, k, _l in open_left[:10]], close_reason=self.closed[b], **cnt)
        if not price_pass:
            unpriced.sort()
            rec.update(n_unpriced=len(unpriced), unpriced=[{"layout_key": k, "v_LP": v} for v, k in unpriced],
                       n_unpriced_with_open_price=self._n_priced_on_open(k for _v, k in unpriced))
        self._emit(rec)
        return rec

    def coverage(self, b: float, limit: int = 50_000) -> Dict[str, Any]:
        """Brute-force coverage check (4.3) when the admissible layouts within ``b`` are at most
        ``limit``: a layout counts as resolved when it is LP-pruned, priced INFEASIBLE, or its
        best known lower value (``max(priced lower, envelope)``) is ``>= UB - tol``.  Priced
        layouts below that threshold (open ILP gaps) are open and reported separately
        (``n_open_priced``)."""
        unit = float(self.enc.inv.min())
        kmax = max(1, int(math.floor((b + 1e-9) / unit)))
        n_est = 0
        nopt = len(self.enc.options)
        for k in range(1, min(kmax, len(self.enc.locations)) + 1):
            n_est += math.comb(len(self.enc.locations), k) * nopt ** k
        if n_est > limit * 20:
            return {"checked": False, "reason": f"about {n_est} layouts"}
        lays = self.menu_layouts(b)
        if len(lays) > limit:
            return {"checked": False, "reason": f"{len(lays)} layouts"}
        ub = self.UB[b]
        thr = ub - self.tol(ub)
        open_: List[str] = []
        open_priced: List[str] = []
        for l in lays:
            key = l.key()
            if key in self.lp_pruned:
                continue
            env = self.master.envelope(l)
            pr = self.priced.get(key)
            if pr is not None:
                if pr.status == "INFEASIBLE" or max(pr.lower, env) >= thr - 1e-9:
                    continue
                open_priced.append(key)
                continue
            if env >= thr - 1e-9:
                continue
            open_.append(key)
        return {"checked": True, "n_layouts": len(lays), "n_open": len(open_) + len(open_priced),
                "n_open_unpriced": len(open_), "n_open_priced": len(open_priced),
                "open": (open_priced + open_)[:20], "access_empty": list(self.master.access_empty)}

    def run(self, warm_layouts: Sequence[Optional[Layout]] = (), lp_phase: bool = True, screen: bool = True,
            coverage_limit: int = 50_000) -> Dict[float, Dict[str, Any]]:
        self.warm_start(warm_layouts)
        if lp_phase:
            self.lp_phase()
        if screen:
            self.screen()
        self.integer_phase()
        return self.finish(coverage_limit)

    def final_bound(self, time_limit: Optional[float] = 120.0) -> Dict[float, Dict[str, Any]]:
        """Guaranteed bound at the close of a target, whatever stopped it (wall, budget, no new
        layouts): one bound-only master solve per budget over the FULL cut pool (cover rows and
        structural rows included; ``ObjBound`` is valid also at ``TIME_LIMIT``), then ``LB_b =
        max(LB so far, master ObjBound, superset trivial bound, enumeration floor where the
        enumeration of ``b`` started)`` with nested-budget propagation (:func:`pool_bound`).
        ``LB`` is therefore never ``-inf`` afterwards; ``LB_kind[b]`` names the component used.
        Emits one ``final_bound`` record per budget."""
        prior = {b: self.LB[b] for b in self.budgets}
        enum_lays = {b: lays for b, lays in self.enum_lays.items()}
        res = pool_bound(self.master, self.enc, self.p, self.L, self.budgets, enum_layouts=enum_lays,
                         v_lp=self._known_v_lp(), priced=self._known_priced(), prior=prior, time_limit=time_limit,
                         start={b: self.best[b] for b in self.budgets})
        self.counters["master_solves"] += len(self.budgets)
        for b in self.budgets:
            r = res[b]
            kind = r["kind"]
            if kind == "prior" or kind.startswith("nested:prior"):
                kind = self.LB_kind[b] or "prior"
                if r["kind"].startswith("nested:"):
                    kind = f"nested:{kind}"
            if r["LB"] > self.LB[b] or self.LB_kind[b] is None:
                self.LB[b] = max(self.LB[b], r["LB"])
                self.LB_kind[b] = kind
            self.LB_parts[b] = {"components": r["components"], "master_status": r["master_status"],
                                "master_bound": r["master_bound"], "master_obj": r["master_obj"],
                                "proposal": r["proposal"], "enumeration": r["enumeration"], "n_cuts": r["n_cuts"]}
            self._emit({"kind": "final_bound", "budget": b, "LB": self.LB[b] if math.isfinite(self.LB[b]) else None,
                        "LB_infinite": None if math.isfinite(self.LB[b]) else NO_ADMISSIBLE, "LB_kind": self.LB_kind[b],
                        "UB": self.UB[b] if math.isfinite(self.UB[b]) else None, "master_runtime_s": r["master_runtime_s"],
                        **self.LB_parts[b]})
        self._nested_lb()
        return res

    def finish(self, coverage_limit: int = 50_000, final_master_s: Optional[float] = 120.0) -> Dict[float, Dict[str, Any]]:
        """Per-budget results (``budget_result`` records).  Call after every pricing that can
        change ``UB`` (search and comparison layouts), so that the reported incumbent is final;
        a budget whose gap closed only through such a later pricing is marked certified.
        Always ends with :meth:`final_bound` (``final_master_s`` = time limit of the bound-only
        master solve per budget), so ``LB`` is finite in every ``budget_result``."""
        out: Dict[float, Dict[str, Any]] = {}
        sup = superset_trivial_bound(self.enc, self.p, self.L)
        self.final_bound(final_master_s)
        for b in self.budgets:
            if self.closed[b] is None:
                self.closed[b] = "not searched"
            if self.LB[b] == INF:
                self.closed[b] = NO_ADMISSIBLE           # never "gap": there is nothing to certify but infeasibility
            elif self.closed[b] != "gap" and math.isfinite(self.UB[b]) and math.isfinite(self.LB[b]) and self.is_closed(b):
                self.closed[b] = "gap"
            rec = self.result(b, sup)
            rec["coverage"] = self.coverage(b, coverage_limit) if math.isfinite(self.UB[b]) else {"checked": False}
            rec["n_stuck"] = len(self.stuck)
            out[b] = rec
            self._emit({"kind": "budget_result", **rec})
        return out

    def result(self, b: float, sup: Optional[float] = None) -> Dict[str, Any]:
        """Per-budget row.  ``LB = inf`` (master infeasible: no admissible layout within ``b``)
        is reported as ``LB None`` with ``close_reason`` :data:`NO_ADMISSIBLE` and counts as
        certified only when no feasible layout was priced within ``b`` either (``UB None``); a
        finite ``UB`` there is flagged as inconsistent.  A finite ``LB`` above ``UB`` (solver
        tolerances) is clamped to ``UB`` in the row (``LB_raw`` keeps the value)."""
        lay = self.best[b]
        bp = self.best_price[b]
        ub, lb = self.UB[b], self.LB[b]
        reason = self.closed[b]
        lb_raw: Optional[float] = None
        if lb == INF:
            lb_out, g = None, None
            certified = not math.isfinite(ub)
            reason = NO_ADMISSIBLE if certified else (f"{NO_ADMISSIBLE}; INCONSISTENT: a feasible layout was priced "
                                                     f"within this budget (UB {ub})")
        else:
            lb_out = lb if math.isfinite(lb) else None
            if lb_out is not None and math.isfinite(ub) and lb_out > ub:
                lb_raw, lb_out = lb_out, ub
            g = None if (lb_out is None or not math.isfinite(ub)) else ((ub - lb_out) / abs(ub) if abs(ub) > 0 else 0.0)
            certified = bool(reason == "gap" and g is not None)
        return {"budget": b, "best_layout": None if lay is None else lay.key(), "UB": None if not math.isfinite(ub) else ub,
                "LB": lb_out, "LB_raw": lb_raw,
                "gap": g, "certified": certified,
                "close_reason": reason, "LB_LP": self.LB_LP[b], "LB_superset": sup,
                "LB_kind": self.LB_kind[b], "LB_parts": self.LB_parts.get(b), "restored": dict(self.restored),
                "investment": None if lay is None else lay.investment(self.ev.spec),
                "served_share": None if bp is None else bp.served_share,
                "best_opex": None if bp is None else bp.ub,
                # R7 re-plan (K2.7): the scenario bounds of an open-sites incumbent hold for the
                # open-sites follower only; they are never reported as all-candidates bounds
                "best_lb": None if (bp is None or bp.tier == "open_sites") else bp.lb,
                **({"best_tier": "open_sites", "best_lb_open": bp.lb} if (bp is not None and bp.tier == "open_sites") else {}),
                "counters": dict(self.counters), "ilp_status": dict(self.ilp_status),
                "max_Qt_minus_Qs": self.max_Qt_minus_Qs, "max_artificial": self.max_artificial,
                "n_cuts": self.master.n_cuts, "wall_s": time.perf_counter() - self.t0}

    def close(self) -> None:
        self.master.dispose()
        if self._own_lps:
            if isinstance(self.lps, ScenarioLPSet):
                self.lps.dispose()
            else:
                for lp in self.lps:
                    lp.dispose()


# ---------------------------------------------------------------------------
# R7: regional branch-and-bound over candidate subsets (design 2.3, corrected in 7.1)
# ---------------------------------------------------------------------------
def setup_min(enc: MenuEncoding, m: int, locations: Sequence[str], s_needs_charge: bool = True,
              inv_lo: float = -INF, inv_hi: float = INF) -> float:
    """Cheapest allocated set-up (27) of an admissible layout with EXACTLY ``m`` open locations
    inside ``locations`` whose investment (33a) lies in the window ``(inv_lo, inv_hi]`` (design
    7.1 item 3 as corrected by the fixer pass: the window is what makes the bound of budget
    ``m`` cover the layouts that the smaller budget's certificate does not, see
    :func:`certify_bnb`): the minimum over multisets of ``m`` menu options (a swap object;
    swap-only next to a charge-capable object; at most as many hubs as hub-capable locations in
    the set); ``inf`` when fewer than ``m`` locations are available or no combination fits the
    window.  Without a window (the defaults) it is independent of the budget."""
    locs = [str(l) for l in locations]
    if len(locs) < int(m) or int(m) < 1:
        return INF
    n_hub = sum(1 for l in locs if "C" in enc.roles_of.get(l, ()))
    n_s = sum(1 for l in locs if "S" in enc.roles_of.get(l, ()))
    n_sc = sum(1 for l in locs if "SC" in enc.roles_of.get(l, ()))
    sp = enc.spec
    opts = sorted(set(enc.options), key=lambda o: (sp.setup_cost(o[0]) + sp.bB * o[1] + sp.bC * o[2], o))
    best = INF
    for combo in itertools.combinations_with_replacement(opts, int(m)):
        roles = [o[0] for o in combo]
        if not any(ROLE_SWAP[r] for r in roles):
            continue
        if s_needs_charge and "S" in roles and not any(ROLE_CHARGE[r] for r in roles):
            continue
        if roles.count("C") > n_hub or roles.count("S") > n_s or roles.count("SC") > n_sc:
            continue
        inv = sum(sp.Fhat + sp.bhat * o[1] + sp.chat * o[2] for o in combo)
        if inv <= inv_lo + 1e-9 or inv > inv_hi + 1e-9:
            continue
        cost = sum(sp.setup_cost(o[0]) + sp.bB * o[1] + sp.bC * o[2] for o in combo)
        if cost < best:
            best = cost
    return best


def subset_bound_value(enc: MenuEncoding, p: Sequence[float], m: int, locations: Sequence[str],
                       lba: Sequence[float], s_needs_charge: bool = True, inv_lo: float = -INF,
                       inv_hi: float = INF) -> float:
    """Node bound ``setup_min(m, A, window) + sum_s p_s LBA_s`` (design 2.3)."""
    sm = setup_min(enc, m, locations, s_needs_charge, inv_lo, inv_hi)
    return INF if sm == INF else sm + sum(float(a) * float(x) for a, x in zip(p, lba))


class SubsetBranchAndBound:
    """Hierarchical branch-and-bound over candidate subsets: ONE pass of :func:`certify_bnb`,
    bounding every admissible layout with EXACTLY ``m`` open locations and investment in the
    window ``(inv_lo, budget]`` (design 2.3 / 7.1, corrected by the fixer pass: the pass alone is
    not a certificate of the budget; ``certify_bnb`` combines the passes ``k = 1..m`` with the
    smaller budget's bound).  ``levels`` = atom partitions from coarse to fine (``[{region:
    [locations]}, {cell: [locations]}, {location: [location]}]``; the last level must be the
    single candidates and every finer atom must lie inside one coarser atom).  A node is a set
    of at most ``m`` atoms of one level; its bound is ``setup_min(m, A, window) + sum_s p_s
    LBA_s`` with the free-size subset LP on the ``S_LP`` scenarios (``L_s`` elsewhere).  A node
    whose bound reaches ``UB_m - tol`` is pruned; otherwise it is refined into the finer-level
    atom sets inside it that touch each of its atoms (every finer node has exactly one such
    parent), or, at the last level with exactly ``m`` atoms, treated as a leaf: re-solved on all
    scenarios, then its admissible size combinations inside the window are pruned by the
    master's cut envelope or priced (``certifier.price(lp=False)``, envelope-ascending, larger
    ``B`` first).  Last-level nodes with fewer than ``m`` atoms hold no layout of this pass
    (another pass bounds them) and are skipped; ``max_level`` (0-based) stops the refinement
    below that level: such nodes stay open at their own bound.

    ``LB_floor`` = the minimum over the pruned nodes' bounds, the unprocessed / unrefined nodes'
    bounds and the leaves' floors (``min`` over their window combinations of ``max(envelope,
    priced lower)``): a valid lower bound on the value of every admissible layout of the pass
    at any time.  With ``update_lb`` (default: only at ``m = 1`` without a window, where the pass
    covers every admissible layout) the certifier's ``LB`` is set to ``min(lb_smaller,
    LB_floor)``; at ``m >= 2`` a single pass never certifies the budget (the layouts with fewer
    open locations in the window are bounded by the other passes of ``certify_bnb``), so ``LB``
    and ``certified`` of the record are ``None`` / ``False`` unless ``update_lb=True`` is forced.
    Records ``subset_bound`` (per node) and ``bnb_done``; resumable because the subset cuts
    (pool) and the pricings (records) are restored by :meth:`SitingCertifier.restore` and
    memoised values are never solved again."""

    def __init__(self, certifier: SitingCertifier, m: int, budget: float, levels: Sequence[Dict[str, Sequence[str]]],
                 S_LP: Optional[Sequence[int]] = None, *, node_budget: Optional[int] = None,
                 lb_smaller: float = -INF, label: str = "", max_leaf_combos: int = 64, inv_lo: float = -INF,
                 max_level: Optional[int] = None, update_lb: Optional[bool] = None) -> None:
        self.c = certifier
        self.m = int(m)
        self.b = float(budget)
        self.inv_lo = float(inv_lo)
        self.levels: List[Dict[str, Tuple[str, ...]]] = [{str(k): tuple(str(x) for x in v) for k, v in lv.items()} for lv in levels]
        if not self.levels or any(len(v) != 1 or k != v[0] for k, v in self.levels[-1].items()):
            raise ValueError("the last level must map every candidate to itself")
        for lv in self.levels:
            for k, locs in lv.items():
                if not locs:
                    raise ValueError(f"empty atom {k}")
        self.S_LP = list(range(certifier.S)) if S_LP is None else sorted({int(s) for s in S_LP})
        self.node_budget = node_budget
        self.lb_smaller = float(lb_smaller)
        self.label = label
        self.max_leaf_combos = int(max_leaf_combos)
        self.max_level = None if max_level is None else max(0, min(int(max_level), len(self.levels) - 1))
        #: a single pass is a certificate of its budget only at m = 1 without a window (every
        #: admissible layout has one open location); otherwise the LB belongs to certify_bnb
        self.update_lb = (self.m == 1 and not math.isfinite(self.inv_lo)) if update_lb is None else bool(update_lb)
        self.n_nodes = self.n_pruned = self.n_leaves = self.n_expanded = self.n_empty = self.n_unrefined = 0
        self.terminal: List[Tuple[float, str]] = []          # (value, why) of every resolved node
        self.open_nodes: List[Dict[str, Any]] = []
        self.leaf_results: List[Dict[str, Any]] = []
        self.stop_reason: Optional[str] = None
        self._parent_of: List[Dict[str, str]] = []
        for k in range(1, len(self.levels)):
            fine, coarse = self.levels[k], self.levels[k - 1]
            mp: Dict[str, str] = {}
            for a, locs in fine.items():
                hosts = [cid for cid, cl in coarse.items() if locs[0] in cl]
                if len(hosts) != 1 or any(l not in coarse[hosts[0]] for l in locs):
                    raise ValueError(f"atom {a} of level {k} is not nested in one atom of level {k - 1}")
                mp[a] = hosts[0]
            self._parent_of.append(mp)

    # -- helpers ---------------------------------------------------------------------
    def locations_of(self, level: int, atoms: Iterable[str]) -> List[str]:
        out: List[str] = []
        for a in atoms:
            out.extend(self.levels[level][a])
        return sorted(set(out))

    def ub_tol(self) -> Tuple[float, float]:
        ub = self.c.UB[self.b]
        return ub, (ub - self.c.tol(ub) if math.isfinite(ub) else INF)

    def in_window(self, layout: Layout) -> bool:
        inv = layout.investment(self.c.enc.spec)
        return inv > self.inv_lo + 1e-9 and inv <= self.b + 1e-9

    def bound(self, level: int, atoms: frozenset, scenarios: Optional[Sequence[int]] = None) -> Tuple[float, float, List[float]]:
        locs = self.locations_of(level, atoms)
        sm = setup_min(self.c.enc, self.m, locs, self.c.s_needs_charge, self.inv_lo, self.b)
        if sm == INF:
            return INF, INF, []
        lba = self.c.subset_bound(locs, self.S_LP if scenarios is None else scenarios, tag=f"bnb{self.m}")
        return sm + sum(p * x for p, x in zip(self.c.p, lba)), sm, lba

    def children(self, level: int, atoms: frozenset) -> List[frozenset]:
        if level + 1 >= len(self.levels):
            return []
        par = self._parent_of[level]
        fine = [a for a in self.levels[level + 1] if par[a] in atoms]
        out: List[frozenset] = []
        for k in range(1, self.m + 1):
            for combo in itertools.combinations(sorted(fine), k):
                if {par[a] for a in combo} == set(atoms):
                    out.append(frozenset(combo))
        return out

    def _emit(self, rec: Dict[str, Any]) -> None:
        self.c._emit({"budget": self.b, "m": self.m, "bnb_label": self.label, "inv_lo": self.inv_lo if math.isfinite(self.inv_lo) else None,
                      **rec})

    # -- leaf -------------------------------------------------------------------------
    def leaf(self, atoms: frozenset, bound_lp: float, lba: List[float]) -> float:
        """Resolve a leaf (``m`` single candidates): full-scenario subset LP, then the size
        combinations inside the window.  Returns the leaf floor."""
        locs = sorted(atoms)
        ub, thr = self.ub_tol()
        full_bound, sm, lba_full = self.bound(len(self.levels) - 1, atoms, scenarios=list(range(self.c.S)))
        if full_bound >= thr - 1e-9:
            self._emit({"kind": "bnb_leaf", "atoms": locs, "bound_lp": bound_lp, "bound_full": full_bound, "pruned": True,
                        "UB": ub if math.isfinite(ub) else None, "n_combos": 0})
            return full_bound
        enc = self.c.enc
        combos: List[Layout] = []
        menus = [[o for o in enc.options if o[0] in enc.roles_of.get(l, ())] for l in locs]
        for choice in itertools.product(*menus):
            lay = Layout.of([(l,) + o for l, o in zip(locs, choice)])
            if not self.in_window(lay) or not self.c.in_master(lay):
                continue
            combos.append(lay)
        ranked = sorted(combos, key=lambda l: (self.c.master.envelope(l), -l.total_B(), -l.total_C(), l.key()))
        n_priced = n_env = n_skip = 0
        floors: List[float] = []
        for lay in ranked[: self.max_leaf_combos]:
            key = lay.key()
            if self.c.wall_out():
                n_skip += 1
                floors.append(max(self.c.master.envelope(lay), full_bound))
                continue
            ub, thr = self.ub_tol()
            env = self.c.master.envelope(lay)
            pr = self.c.priced.get(key)
            if pr is not None and pr.status in ("INFEASIBLE",):
                continue
            if pr is not None and max(pr.lower, env) >= thr - 1e-9:
                floors.append(max(pr.lower, env))
                continue
            if pr is None and (env >= thr - 1e-9 or key in self.c.lp_pruned):
                n_env += 1
                self.c.lp_pruned.add(key)
                floors.append(max(env, full_bound))
                continue
            if pr is None:
                pr = self.c.price(lay, tag=f"bnb{self.m}", lp=False)
                n_priced += 1
                if pr.status == SKIPPED_BUDGET:
                    n_skip += 1
                    floors.append(max(env, full_bound))
                    continue
            floors.append(max(pr.lower, self.c.master.envelope(lay)) if pr.status != "INFEASIBLE" else INF)
        for lay in ranked[self.max_leaf_combos:]:
            floors.append(max(self.c.master.envelope(lay), full_bound))
        floor = min(floors) if floors else INF
        floor = max(floor, full_bound)
        self.leaf_results.append({"atoms": locs, "floor": floor, "n_combos": len(combos), "n_priced": n_priced,
                                  "n_envelope_pruned": n_env, "n_skipped": n_skip})
        self._emit({"kind": "bnb_leaf", "atoms": locs, "bound_lp": bound_lp, "bound_full": full_bound, "pruned": False,
                    "floor": floor, "n_combos": len(combos), "n_priced": n_priced, "n_envelope_pruned": n_env,
                    "n_skipped": n_skip, "UB": self.c.UB[self.b] if math.isfinite(self.c.UB[self.b]) else None})
        return floor

    # -- run ---------------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        last = len(self.levels) - 1
        queue: List[Tuple[int, frozenset, float]] = []
        for k in range(1, self.m + 1):
            for combo in itertools.combinations(sorted(self.levels[0]), k):
                queue.append((0, frozenset(combo), -INF))
        seen: Set[Tuple[int, frozenset]] = set()
        while queue:
            if self.c.wall_out():
                self.stop_reason = "wall"
                break
            if self.node_budget is not None and self.n_nodes >= self.node_budget:
                self.stop_reason = f"node budget {self.node_budget}"
                break
            level, atoms, parent_bound = queue.pop(0)
            if (level, atoms) in seen:
                continue
            seen.add((level, atoms))
            if level == last and len(atoms) < self.m:
                continue                            # fewer than m sites: bounded by another pass of certify_bnb
            self.n_nodes += 1
            bnd, sm, lba = self.bound(level, atoms)
            ub, thr = self.ub_tol()
            if bnd == INF:
                self.n_empty += 1
                self._emit({"kind": "subset_bound", "level": level, "atoms": sorted(atoms), "n_locations": len(self.locations_of(level, atoms)),
                            "bound": None, "setup_min": None, "empty": True, "pruned": True})
                continue
            pruned = bnd >= thr - 1e-9
            self._emit({"kind": "subset_bound", "level": level, "atoms": sorted(atoms),
                        "n_locations": len(self.locations_of(level, atoms)), "bound": bnd, "setup_min": sm,
                        "lba": lba, "scenarios_used": list(self.S_LP), "pruned": bool(pruned),
                        "UB": ub if math.isfinite(ub) else None, "threshold": thr if math.isfinite(thr) else None,
                        "parent_bound": parent_bound if math.isfinite(parent_bound) else None})
            if pruned:
                self.n_pruned += 1
                self.terminal.append((bnd, "pruned"))
                continue
            if level == last:
                self.n_leaves += 1
                self.terminal.append((self.leaf(atoms, bnd, lba), "leaf"))
                continue
            if self.max_level is not None and level >= self.max_level:
                self.n_unrefined += 1               # refinement stopped here: open at its own bound
                self.open_nodes.append({"level": level, "atoms": sorted(atoms), "bound": bnd, "unrefined": True})
                self.terminal.append((bnd, "unrefined"))
                continue
            self.n_expanded += 1
            for ch in self.children(level, atoms):
                queue.append((level + 1, ch, bnd))
        # open nodes: a child's bound is at least its parent's (the open set only shrinks)
        for level, atoms, parent_bound in queue:
            if (level, atoms) in seen or (level == last and len(atoms) < self.m):
                continue
            self.open_nodes.append({"level": level, "atoms": sorted(atoms), "parent_bound": parent_bound})
            self.terminal.append((parent_bound, "open"))
        floor_m = min((v for v, _w in self.terminal), default=INF)
        lb = min(self.lb_smaller, floor_m) if self.update_lb else None
        if self.stop_reason is None:
            self.stop_reason = "complete" if not self.n_unrefined else f"complete (refinement stopped at level {self.max_level})"
        ub = self.c.UB[self.b]
        certified = lb is not None and math.isfinite(ub) and math.isfinite(lb) and ub - lb <= self.c.tol(ub) + 1e-9
        if self.update_lb:
            if lb > self.c.LB[self.b]:
                self.c.LB[self.b] = lb
                self.c.LB_kind[self.b] = f"subset_bnb_L{last + 1}"
            self.c._nested_lb()
            _close_budget(self.c, self.b, certified, [self.stop_reason], len(self.open_nodes))
        rec = {"kind": "bnb_done", "LB_floor_m": floor_m if math.isfinite(floor_m) else None,
               "lb_smaller": self.lb_smaller if math.isfinite(self.lb_smaller) else None,
               "LB": lb if (lb is not None and math.isfinite(lb)) else None, "UB": ub if math.isfinite(ub) else None,
               "certified": bool(certified),
               "n_nodes": self.n_nodes, "n_pruned": self.n_pruned, "n_expanded": self.n_expanded, "n_leaves": self.n_leaves,
               "n_empty": self.n_empty, "n_unrefined": self.n_unrefined, "n_open": len(self.open_nodes),
               "open_nodes": self.open_nodes[:50], "leaves": self.leaf_results, "stop_reason": self.stop_reason,
               "S_LP": list(self.S_LP), "levels": [len(lv) for lv in self.levels], "max_level": self.max_level,
               "wall_s": time.perf_counter() - t0, "update_lb": self.update_lb,
               "best_layout": None if self.c.best[self.b] is None else self.c.best[self.b].key()}
        self._emit(rec)
        return rec



def _close_budget(c: SitingCertifier, b: float, certified: bool, stops: Sequence[str], n_open: int) -> None:
    """``closed[b]`` after the B&B passes of a budget."""
    complete = all(str(x).startswith("complete") for x in stops)
    if certified and c.closed[b] is None:
        c.closed[b] = "gap"
    elif c.closed[b] is None and not complete:
        c.closed[b] = f"bnb stopped: {'; '.join(str(x) for x in stops if not str(x).startswith('complete'))} ({n_open} open nodes)"
    elif c.closed[b] is None:
        c.closed[b] = "bnb complete (open pricing gaps, unrefined nodes or lb_smaller below UB - tol)"


def certify_bnb(certifier: SitingCertifier, m: int, budget: float, levels: Sequence[Dict[str, Sequence[str]]],
                S_LP: Optional[Sequence[int]] = None, *, lb_smaller: float = -INF, budget_smaller: Optional[float] = None,
                node_budget: Optional[int] = None, label: str = "", max_leaf_combos: int = 64,
                enum_limit: int = 20_000, max_level: Optional[int] = None) -> Dict[str, Any]:
    """Certificate of budget ``m`` (investment ``<= budget``) by regional branch-and-bound
    (design 2.3 / 7.1 item 3 as corrected by the fixer pass).

    Every admissible layout within ``budget`` has either investment ``<= budget_smaller`` (its
    value is ``>= lb_smaller``, the bound of the smaller budget) or investment in the window
    ``(budget_smaller, budget]`` with ``k`` open locations, ``1 <= k <= m``.  The window layouts
    are bounded per ``k``: ``k = 1`` by a windowed enumeration (:meth:`SitingCertifier.
    certify_by_enumeration` on the one-site layouts of the window: envelope prune, LP, price;
    the LP cuts of the m = 1 stage make most of it LP-free), ``k >= 2`` by one
    :class:`SubsetBranchAndBound` pass with ``setup_min`` restricted to the window (for ``k < m``
    these are, e.g., the two-site layouts whose large sizes exceed budget ``m - 1``; for ``k =
    m`` the window only tightens the set-up term).  ``LB_m = min(lb_smaller, min_k floor_k)``.
    Without ``budget_smaller`` (``None``) the window is ``(-inf, budget]`` and ``lb_smaller`` is
    not needed (every layout is bounded here).  The k = 1 enumeration falls back to a B&B pass
    when the window holds more than ``enum_limit`` layouts.  ``max_level`` stops the refinement
    of the B&B passes (open nodes at their bound).  Emits ``bnb_pass`` records and one
    ``bnb_certificate`` record; sets ``LB[budget]``, ``LB_kind`` and ``closed``."""
    c = certifier
    b = float(budget)
    lo = -INF if budget_smaller is None else float(budget_smaller)
    lbs = float(lb_smaller) if budget_smaller is not None else INF
    t0 = time.perf_counter()
    passes: List[Dict[str, Any]] = []
    floors: List[float] = []
    stops: List[str] = []
    n_open = 0
    for k in range(1, int(m) + 1):
        if c.wall_out() and k > 1:
            stops.append("wall")
            floors.append(-INF)
            passes.append({"k": k, "method": "skipped", "reason": "wall"})
            continue
        if k == 1:
            lays = c.menu_layouts(b, k_range=[1], inv_lo=lo)
            if len(lays) <= int(enum_limit):
                e = c.certify_by_enumeration(b, limit=int(enum_limit), prune=True, force_lp_per_location=False,
                                             layouts=lays, update_lb=False, tag=f"bnb{m}_k1_window")
                fl = e.get("LB_enum")
                fl = INF if (fl is None and not lays) else (-INF if fl is None else float(fl))
                floors.append(fl)
                stops.append("complete" if e.get("done") else str(e.get("reason")))
                passes.append({"k": 1, "method": "enumeration", "n_layouts": len(lays), "floor": fl if math.isfinite(fl) else None,
                               "done": bool(e.get("done")), "reason": e.get("reason"), "n_priced": e.get("n_priced"),
                               "n_envelope_pruned": e.get("n_envelope_pruned"), "n_lp": e.get("n_lp")})
                c._emit({"kind": "bnb_pass", "budget": b, "m": int(m), "bnb_label": label, **passes[-1]})
                continue
        bb = SubsetBranchAndBound(c, k, b, levels, S_LP, node_budget=node_budget, lb_smaller=INF,
                                  label=f"{label}_k{k}" if label else f"k{k}", max_leaf_combos=max_leaf_combos,
                                  inv_lo=lo, max_level=max_level, update_lb=False)
        r = bb.run()
        fl = INF if r["LB_floor_m"] is None else float(r["LB_floor_m"])
        floors.append(fl)
        stops.append(str(r["stop_reason"]))
        n_open += int(r["n_open"])
        passes.append({"k": k, "method": "bnb", "floor": fl if math.isfinite(fl) else None, "stop_reason": r["stop_reason"],
                       "n_nodes": r["n_nodes"], "n_pruned": r["n_pruned"], "n_leaves": r["n_leaves"], "n_open": r["n_open"],
                       "n_unrefined": r["n_unrefined"], "n_empty": r["n_empty"]})
        c._emit({"kind": "bnb_pass", "budget": b, "m": int(m), "bnb_label": label, **passes[-1]})
    floor_w = min(floors) if floors else INF
    lb = min(lbs, floor_w)
    ub = c.UB[b]
    certified = math.isfinite(ub) and math.isfinite(lb) and ub - lb <= c.tol(ub) + 1e-9
    if lb > c.LB[b]:
        c.LB[b] = lb
        c.LB_kind[b] = f"subset_bnb_L{len(levels)}"
    c._nested_lb()
    _close_budget(c, b, certified, stops, n_open)
    rec = {"kind": "bnb_certificate", "budget": b, "m": int(m), "bnb_label": label,
           "window": [lo if math.isfinite(lo) else None, b], "lb_smaller": lbs if math.isfinite(lbs) else None,
           "LB_floor_window": floor_w if math.isfinite(floor_w) else None, "floors_by_k": [f if math.isfinite(f) else None for f in floors],
           "LB": lb if math.isfinite(lb) else None, "UB": ub if math.isfinite(ub) else None, "certified": bool(certified),
           "passes": passes, "stop_reason": "complete" if all(x.startswith("complete") for x in stops) else "; ".join(stops),
           "n_nodes": sum(int(p.get("n_nodes") or 0) for p in passes), "n_open": n_open,
           "levels": [len(lv) for lv in levels], "max_level": max_level, "S_LP": list(range(c.S)) if S_LP is None else list(S_LP),
           "wall_s": time.perf_counter() - t0, "best_layout": None if c.best[b] is None else c.best[b].key()}
    c._emit(rec)
    return rec


class LPScreen:
    """Score function of the greedy's LP screen (``bilevel.greedy_local_search(screen=LPScreen(c))``):
    ``setup + sum_s p_s max(L_s, Qs_s)`` of the safe LP bound at the layout (the LP solves also
    add their cuts to the certifier); layouts outside the menu get the superset value."""

    def __init__(self, certifier: SitingCertifier) -> None:
        self.c = certifier

    def __call__(self, layout: Layout) -> float:
        c = self.c
        if not c.enc.contains(layout):
            return layout.allocated_cost(c.ev.spec) + sum(p * x for p, x in zip(c.p, c.L))
        c.lp_at(layout)
        return c.v_lp(layout)
