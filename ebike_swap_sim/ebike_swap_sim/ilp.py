"""Gurobi formulation of the E2 integer linear program (``notes/extracted/E2.txt``
(5)-(22), (26)-(33); binding conventions in ``notes/DECISIONS.md``) on top of an
:class:`~ebike_swap_sim.or_instance.Instance` and an
:class:`~ebike_swap_sim.arcs.ArcLibrary`.

This is the only module of the package that imports gurobipy.  The solution is
returned as an :class:`~ebike_swap_sim.evaluate.Schedule` that is priced and
checked by ``evaluate.cost`` / ``evaluate.check``; ``solve`` raises
:class:`ILPConsistencyError` if the checker reports a violation or the priced
total differs from the Gurobi objective, so a returned schedule is certified by
solver-independent code.

Variables (E2 Section 2 table)
------------------------------
``x[a]``         binary, one per arc id of the library (``Arc.k`` gives the bike);
``u[i]``         binary, order unserved;
``y[j]``         binary, ``B[j]``, ``C[j]`` integer (fixed through bounds when the
                 facility data are given and ``fixed_facilities`` is on);
``n[j,q,t]``     integer stock, ``j in N``, ``q = 0..L``, ``t = 0..H``;
``c[j,q,t]``     integer charging, only ``j in C``, ``q < L``, ``t < H`` (fixed zeros
                 of (12)-(13) are never created);
``h[e]`` binary, ``z[e,q]`` integer, ``q = 0..L``.
``s_jqt``, ``S_jt`` (12) and ``D_jqt``, ``A_jqt`` (11) are linear expressions.

Switches (keyword arguments of :func:`build_model`; ``None`` = take the value of
``Instance.options`` / ``Instance.budget`` / ``Instance.zeta``): ``no_transfers``
(``h = z = 0``, E2 p.9), ``colocated`` (``S = C = N`` on a copy of the instance,
arc library rebuilt), ``fixed_facilities`` (``True``: fix ``y/B/C`` where given;
``False``: all free), ``budget`` and ``zeta`` (33), ``lexicographic`` (first
``min sum_i u_i``, then min cost with that count fixed, E2 p.9) and
``battery_swap_v1_bounds`` (``y_j <= B_j``, ``C_j <= B_j`` of the Sep-29 model).

Typical use::

    lib = build_arcs(inst)
    sched, stats = solve(inst, lib, mip_start=baseline_schedule)
    # or
    mdl = build_model(inst, lib, no_transfers=True)
    sched, stats = mdl.solve()

Always ``OutputFlag = 0`` unless ``output=True``, ``Threads = 4`` and a
``TimeLimit`` (defaults of :func:`build_model`).
"""
from __future__ import annotations

import copy
import math
import time
import warnings
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import gurobipy as gp
from gurobipy import GRB

from .arcs import SINK, ArcLibrary, build_arcs
from .evaluate import Schedule, check, cost, facility_vars, reconstruct_inventory
from .or_instance import Instance

__all__ = ["ILPModel", "ILPConsistencyError", "build_model", "solve", "colocated_instance",
           "status_name"]

def _status_names() -> Dict[int, str]:
    names: Dict[int, str] = {}
    for name in dir(GRB.Status):
        if name.isupper():
            code = getattr(GRB.Status, name, None)
            if isinstance(code, int):
                names.setdefault(code, name)
    # fallback for gurobipy builds where GRB.Status exposes no attributes
    for name in ("LOADED", "OPTIMAL", "INFEASIBLE", "INF_OR_UNBD", "UNBOUNDED", "CUTOFF",
                 "ITERATION_LIMIT", "NODE_LIMIT", "TIME_LIMIT", "SOLUTION_LIMIT", "INTERRUPTED",
                 "NUMERIC", "SUBOPTIMAL", "INPROGRESS", "USER_OBJ_LIMIT", "WORK_LIMIT",
                 "MEM_LIMIT"):
        code = getattr(GRB, name, None)
        if isinstance(code, int):
            names.setdefault(code, name)
    return names


_STATUS_NAMES: Dict[int, str] = _status_names()


def status_name(code: int) -> str:
    """Human-readable Gurobi status (``'OPTIMAL'``, ``'TIME_LIMIT'``, ``'INFEASIBLE'``, ...)."""
    return _STATUS_NAMES.get(int(code), str(code))


class ILPConsistencyError(RuntimeError):
    """The extracted schedule violates a constraint family according to
    ``evaluate.check`` or its ``evaluate.cost`` total differs from the Gurobi
    objective: the model and the checker disagree, which must never be silent."""


# ---------------------------------------------------------------------------
# co-location special case (E2 p.9: take S = C = N)
# ---------------------------------------------------------------------------
def colocated_instance(inst: Instance) -> Instance:
    """Deep copy of ``inst`` in which every facility is both swap- and charge-capable
    (E2 p.9 special case ``S = C = N``).

    A facility that gains the swap role keeps its own ``M_j``/``sigma_j`` but
    these are raised to the minimum 1 required by (22) when the data had 0 (a
    charge-only hub has ``M = 0`` in the data); a facility that gains the charge
    role keeps its ``Cbar_j``, ``C_j`` and ``P_j`` (so a swap-only site with
    ``Cbar = 0`` still cannot charge).  Rule (8) ``C_j >= y_j`` for ``j in C \\ S``
    becomes void because ``C \\ S`` is empty.  The changes are recorded in
    ``meta['colocated_changes']`` and ``options['colocated'] = True``.
    """
    inst_c = copy.deepcopy(inst)
    changes: List[str] = []
    for f in inst_c.facilities:
        if not f.swap:
            f.swap = True
            if f.M < 1:
                f.M = 1
                changes.append(f"{f.id}: swap role added, M raised 0 -> 1")
            else:
                changes.append(f"{f.id}: swap role added")
            if f.sigma < 1:
                f.sigma = 1
                changes.append(f"{f.id}: sigma raised to 1")
        if not f.charge:
            f.charge = True
            changes.append(f"{f.id}: charge role added (Cbar={f.Cbar}, C={f.C})")
    inst_c.options["colocated"] = True
    inst_c.meta = {**inst_c.meta, "colocated_changes": changes}
    inst_c.reindex()
    return inst_c


# ---------------------------------------------------------------------------
# model wrapper
# ---------------------------------------------------------------------------
class ILPModel:
    """gurobipy model of E2 plus variable maps and objective components.

    Attributes
    ----------
    inst, lib
        The instance and arc library the model is built on.  With
        ``colocated=True`` these are the co-located copy and its rebuilt library
        (``inst_original`` / ``lib_original`` keep the inputs); the returned
        ``Schedule`` refers to ``lib``.
    model
        The ``gurobipy.Model``.
    x, u, y, B, C, n, c, h, z
        Variable maps (``x`` keyed by arc id; ``n``/``c`` by ``(j, q, t)``; ``z`` by ``(e, q)``).
    components
        ``{'C_setup', 'C_elec', 'C_travel', 'C_orders', 'C_reb', 'C_dummy_terminal'}``
        -> ``LinExpr`` of (27)-(32) (dummy terminal penalties separately), ``objective``
        = (26) and ``sum_u`` = ``sum_i u_i``.
    switches
        Effective model switches.
    """

    def __init__(self, inst: Instance, lib: ArcLibrary, *, no_transfers: bool,
                 colocated: bool, fixed_facilities: bool, budget: Optional[float],
                 zeta: Optional[float], lexicographic: bool, battery_swap_v1_bounds: bool,
                 threads: int, time_limit: float, output: bool,
                 params: Optional[Dict[str, Any]] = None, names: Optional[bool] = None,
                 model: Optional[gp.Model] = None, prefix: str = "",
                 facility_vars: Optional[Tuple[Dict[Any, gp.Var], Dict[Any, gp.Var], Dict[Any, gp.Var]]] = None,
                 set_objective: bool = True) -> None:
        """With the defaults the model owns its ``gp.Env`` / ``gp.Model`` and behaves as
        documented above.  The three optional *shared-model* arguments (bi-level siting,
        ``ebike_swap_sim.bilevel.integrated_stochastic_ilp``) make the instance a
        **sub-model** of a caller-owned ``model``: its variables and rows (5)-(6),
        (9)-(22) are added to that model under ``prefix`` (names), the facility variables
        ``y, B, C`` are taken from ``facility_vars`` (``{facility_id: Var}`` maps, shared
        across scenario copies) instead of being created, the facility bounds (7)-(8)
        and the rows (33) are left to the caller (they are on the shared variables only),
        and with ``set_objective=False`` the objective (26) is computed in
        ``self.objective`` / ``self.components`` but not set on the model.  Gurobi
        parameters are not touched on a shared model."""
        t0 = time.perf_counter()
        if lib.inst is not inst and lib.inst != inst:
            raise ValueError("the arc library was built on a different instance")
        self.inst_original = inst
        self.lib_original = lib
        if colocated and not all(f.swap and f.charge for f in inst.facilities):
            inst = colocated_instance(inst)
            overrides = dict(lib.options)
            overrides["colocated"] = True
            lib = build_arcs(inst, strict=not lib.has_dummy_terminal, **overrides)
        self.inst = inst
        self.lib = lib
        self.switches: Dict[str, Any] = {
            "no_transfers": bool(no_transfers), "colocated": bool(colocated),
            "fixed_facilities": bool(fixed_facilities), "budget": budget, "zeta": zeta,
            "lexicographic": bool(lexicographic),
            "battery_swap_v1_bounds": bool(battery_swap_v1_bounds),
            "threads": threads, "time_limit": time_limit,
        }
        self._names = (len(lib) <= 300_000) if names is None else bool(names)
        self._prefix = str(prefix)
        self._shared_facilities = facility_vars
        self._set_objective = bool(set_objective)
        self.shared_model = model is not None
        if model is None:
            # an explicit environment lets OutputFlag be set BEFORE the licence banner
            self.env = gp.Env(empty=True)
            self.env.setParam("OutputFlag", 1 if output else 0)
            self.env.start()
            self.model = gp.Model("E2", env=self.env)
            self._set_params(threads, time_limit, output, params or {})
        else:
            self.env = None
            self.model = model
        self.components: Dict[str, gp.LinExpr] = {}
        self.objective: gp.LinExpr = gp.LinExpr()
        self.sum_u: gp.LinExpr = gp.LinExpr()
        self.n_rows: Dict[str, int] = defaultdict(int)
        self._start_values: Optional[Dict[gp.Var, float]] = None
        self.mip_start_info: Dict[str, Any] = {"given": False}
        self._first_incumbent: Optional[Tuple[float, float]] = None
        self._build()
        self.model.update()
        self.build_time = time.perf_counter() - t0

    # ------------------------------------------------------------- params
    def _set_params(self, threads: int, time_limit: float, output: bool,
                    params: Dict[str, Any]) -> None:
        m = self.model
        m.Params.OutputFlag = 1 if output else 0
        m.Params.Threads = int(threads)
        m.Params.TimeLimit = float(time_limit)
        for key, val in params.items():
            m.setParam(key, val)

    def _nm(self, base: str, *idx: Any) -> str:
        if not self._names:
            return ""
        base = self._prefix + base
        return base + "[" + ",".join(str(i) for i in idx) + "]" if idx else base

    # -------------------------------------------------------------- build
    def _build(self) -> None:
        """Create variables, constraints (5)-(22), (33) and objective (26)-(32)."""
        inst, lib, m = self.inst, self.lib, self.model
        H, L = inst.H, inst.L
        disc = inst.disc
        sw = self.switches
        fixed = sw["fixed_facilities"]
        Cset = set(inst.Cset)

        # ---------------------------------------------------- one scan of the arcs
        out_ids: Dict[Tuple[Any, Tuple], List[int]] = defaultdict(list)
        in_ids: Dict[Tuple[Any, Tuple], List[int]] = defaultdict(list)
        states: Dict[Any, set] = {b.id: {lib.source(b.id), SINK} for b in inst.bikes}
        deliv_ids: Dict[Any, List[int]] = defaultdict(list)
        swap_at: Dict[Tuple[Any, int, int], List[int]] = defaultdict(list)   # (j, t, q) (12)
        occ: Dict[Tuple[Any, int], List[int]] = defaultdict(list)            # (j, tau) (22)
        term_kj: Dict[Tuple[Any, Any], List[int]] = defaultdict(list)        # (k, j) (9)
        travel_ids: List[int] = []
        travel_coef: List[float] = []
        theta_ids: List[int] = []
        theta_coef: List[float] = []
        dummy_ids: List[int] = []
        dummy_coef: List[float] = []
        for a in lib.arcs:
            out_ids[(a.k, a.src)].append(a.id)
            in_ids[(a.k, a.dst)].append(a.id)
            st = states[a.k]
            st.add(a.src)
            st.add(a.dst)
            if a.d_km:
                travel_ids.append(a.id)
                travel_coef.append(inst.kappa * a.d_km)
            if a.kind == "deliver":
                deliv_ids[a.order].append(a.id)
                if a.theta:
                    theta_ids.append(a.id)
                    theta_coef.append(a.theta)
            elif a.kind == "swap":
                swap_at[(a.fac, a.l, a.src[2])].append(a.id)
                for tau in range(a.l, min(a.u, H)):
                    occ[(a.fac, tau)].append(a.id)
            elif a.kind == "term":
                if a.fac is None:
                    dummy_ids.append(a.id)
                    dummy_coef.append(a.theta)
                else:
                    term_kj[(a.k, a.fac)].append(a.id)

        # ------------------------------------------------------------ variables
        self.x = m.addVars(range(len(lib.arcs)), vtype=GRB.BINARY, name=self._nm("x"))
        self.u = m.addVars([o.id for o in inst.orders], vtype=GRB.BINARY, name=self._nm("u"))
        self.y: Dict[Any, gp.Var] = {}
        self.B: Dict[Any, gp.Var] = {}
        self.C: Dict[Any, gp.Var] = {}
        shared = self._shared_facilities
        if shared is not None:
            for f in inst.facilities:
                if f.id not in shared[0] or f.id not in shared[1] or f.id not in shared[2]:
                    raise ValueError(f"shared facility variables lack facility {f.id!r}")
                self.y[f.id], self.B[f.id], self.C[f.id] = shared[0][f.id], shared[1][f.id], shared[2][f.id]
        for f in inst.facilities:
            j = f.id
            if shared is not None:
                continue
            if fixed and f.y is not None:
                self.y[j] = m.addVar(lb=f.y, ub=f.y, vtype=GRB.BINARY, name=self._nm("y", j))
            else:
                self.y[j] = m.addVar(vtype=GRB.BINARY, name=self._nm("y", j))
            if fixed and f.B is not None:
                self.B[j] = m.addVar(lb=f.B, ub=f.B, vtype=GRB.INTEGER, name=self._nm("B", j))
            else:
                self.B[j] = m.addVar(lb=0, ub=f.K, vtype=GRB.INTEGER, name=self._nm("B", j))
            c_ub = min(f.Cbar, f.K) if f.charge else 0            # (7), (8) C_j = 0 off C
            if fixed and f.C is not None:
                self.C[j] = m.addVar(lb=f.C, ub=f.C, vtype=GRB.INTEGER, name=self._nm("C", j))
            else:
                self.C[j] = m.addVar(lb=0, ub=c_ub, vtype=GRB.INTEGER, name=self._nm("C", j))
        n_keys = [(f.id, q, t) for f in inst.facilities for q in range(L + 1) for t in range(H + 1)]
        n_ub = [inst.facility(j).K for (j, q, t) in n_keys]
        self.n = m.addVars(n_keys, lb=0, ub=n_ub, vtype=GRB.INTEGER, name=self._nm("n"))
        c_keys = [(j, q, t) for j in inst.Cset for q in range(L) for t in range(H)]
        c_ub = [min(inst.facility(j).Cbar, inst.facility(j).K) for (j, q, t) in c_keys]
        self.c = m.addVars(c_keys, lb=0, ub=c_ub, vtype=GRB.INTEGER, name=self._nm("c"))
        no_tr = sw["no_transfers"]
        self.h = m.addVars([s.id for s in inst.services], vtype=GRB.BINARY,
                           ub=0 if no_tr else 1, name=self._nm("h"))
        z_keys = [(s.id, q) for s in inst.services for q in range(L + 1)]
        z_ub = [0 if no_tr else inst.service(e).U for (e, q) in z_keys]
        self.z = m.addVars(z_keys, lb=0, ub=z_ub, vtype=GRB.INTEGER, name=self._nm("z"))
        x, u, y, B, C, n, c, h, z = (self.x, self.u, self.y, self.B, self.C, self.n, self.c,
                                     self.h, self.z)

        # service buckets for (11)
        dep: Dict[Tuple[Any, int], List[Any]] = defaultdict(list)   # (o_e, l_e) -> [e]
        arr: Dict[Tuple[Any, int], List[Any]] = defaultdict(list)   # (d_e, u_e) -> [e]
        for s_ in inst.services:
            dep[(s_.o_fac, s_.l)].append(s_.id)
            arr[(s_.d_fac, s_.u)].append(s_.id)

        def D(j: Any, q: int, t: int) -> Optional[gp.LinExpr]:
            """``D_jqt`` of (11): loads departing ``j`` at ``t``."""
            es = dep.get((j, t))
            return gp.quicksum(z[e, q] for e in es) if es else None

        def A(j: Any, q: int, t: int) -> Optional[gp.LinExpr]:
            """``A_jqt`` of (11): loads arriving at ``j`` at ``t``."""
            es = arr.get((j, t))
            return gp.quicksum(z[e, q] for e in es) if es else None

        def s_(j: Any, q: int, t: int) -> Optional[gp.LinExpr]:
            """``s_jqt`` of (12): swap arcs at ``j`` starting at ``t`` with return level ``q``."""
            ids = swap_at.get((j, t, q))
            return gp.quicksum(x[a] for a in ids) if ids else None

        def S_(j: Any, t: int) -> Optional[gp.LinExpr]:
            """``S_jt`` of (12)."""
            parts = [s_(j, q, t) for q in range(L)]
            parts = [p for p in parts if p is not None]
            return gp.quicksum(parts) if parts else None

        def c_(j: Any, q: int, t: int) -> Optional[gp.Var]:
            """``c_jqt`` with the fixed zeros ``c_{j,-1,t} = c_{jLt} = 0`` and ``c = 0`` off ``C``."""
            if j in Cset and 0 <= q < L:
                return c[j, q, t]
            return None

        def add(name: str, expr: Any, sense: str, rhs: Any, label: str) -> None:
            m.addLConstr(expr, sense, rhs, name=self._nm(label) if self._names else "")
            self.n_rows[name] += 1

        # ------------------------------------------------------------ (5) flow
        for b in inst.bikes:
            k = b.id
            src = lib.source(k)
            for w in states[k]:
                o_ids = out_ids.get((k, w), ())
                i_ids = in_ids.get((k, w), ())
                expr = gp.LinExpr([1.0] * len(o_ids) + [-1.0] * len(i_ids),
                                  [x[a] for a in o_ids] + [x[a] for a in i_ids])
                rhs = 1 if w == src else (-1 if w == SINK else 0)
                add("(5)", expr, GRB.EQUAL, rhs, f"flow[{k},{w}]")

        # ------------------------------------------------------------ (6) orders
        for o in inst.orders:
            ids = deliv_ids.get(o.id, ())
            add("(6)", gp.quicksum(x[a] for a in ids) + u[o.id], GRB.EQUAL, 1, f"order[{o.id}]")

        # ------------------------------------------------------- (7)-(8) facilities
        # (on a shared model the caller owns y/B/C and adds (7)-(8) and (33) once)
        for f in (inst.facilities if shared is None else []):
            j = f.id
            add("(7)-(8)", B[j] - f.K * y[j], GRB.LESS_EQUAL, 0, f"B_le_Ky[{j}]")
            add("(7)-(8)", C[j] - min(f.Cbar, f.K) * y[j], GRB.LESS_EQUAL, 0, f"C_le_Cbary[{j}]")
            if f.charge and not f.swap:
                add("(7)-(8)", C[j] - y[j], GRB.GREATER_EQUAL, 0, f"C_ge_y[{j}]")
            if sw["battery_swap_v1_bounds"]:
                add("(7)-(8)", y[j] - B[j], GRB.LESS_EQUAL, 0, f"v1_y_le_B[{j}]")
                add("(7)-(8)", C[j] - B[j], GRB.LESS_EQUAL, 0, f"v1_C_le_B[{j}]")

        # ------------------------------------------------------------ (9) terminal
        for (k, j), ids in term_kj.items():
            add("(9)", gp.quicksum(x[a] for a in ids) - y[j], GRB.LESS_EQUAL, 0, f"term[{k},{j}]")

        # ------------------------------------------------------------ (10) services
        for s0 in inst.services:
            e = s0.id
            load = gp.quicksum(z[e, q] for q in range(L + 1))
            add("(10)", load - h[e], GRB.GREATER_EQUAL, 0, f"svc_lo[{e}]")
            add("(10)", load - s0.U * h[e], GRB.LESS_EQUAL, 0, f"svc_hi[{e}]")
            add("(10)", h[e] - y[s0.o_fac], GRB.LESS_EQUAL, 0, f"svc_yo[{e}]")
            add("(10)", h[e] - y[s0.d_fac], GRB.LESS_EQUAL, 0, f"svc_yd[{e}]")

        # ------------------------------------------- (13), (14), (15), (16), (17)
        for f in inst.facilities:
            j = f.id
            for t in range(H):
                S_jt = S_(j, t)
                for q in range(L + 1):
                    # (13): n[t+1] = n[t] - c_q + c_{q-1} + s_q - 1{q=L} S - D_t + A_{t+1}
                    expr = gp.LinExpr(n[j, q, t + 1] - n[j, q, t])
                    cq = c_(j, q, t)
                    if cq is not None:
                        expr += cq
                    cqm = c_(j, q - 1, t)
                    if cqm is not None:
                        expr -= cqm
                    sq = s_(j, q, t) if q < L else None
                    if sq is not None:
                        expr -= sq
                    if q == L and S_jt is not None:
                        expr += S_jt
                    Dq = D(j, q, t)
                    if Dq is not None:
                        expr += Dq
                    Aq = A(j, q, t + 1)
                    if Aq is not None:
                        expr -= Aq
                    add("(13)", expr, GRB.EQUAL, 0, f"bal[{j},{q},{t}]")
                    # (14) joint availability
                    if q < L:
                        parts = [p for p in (cq, Dq) if p is not None]
                    else:
                        parts = [p for p in (S_jt, Dq) if p is not None]
                    if parts:
                        add("(14)", gp.quicksum(parts) - n[j, q, t], GRB.LESS_EQUAL, 0,
                            f"avail[{j},{q},{t}]")
            for t in range(H + 1):                                     # (15)
                add("(15)", gp.quicksum(n[j, q, t] for q in range(L + 1)) - f.K * y[j],
                    GRB.LESS_EQUAL, 0, f"store[{j},{t}]")
            add("(16)", n[j, L, 0] - B[j], GRB.EQUAL, 0, f"init_full[{j}]")   # (16)
            for q in range(L):
                add("(16)", gp.LinExpr(n[j, q, 0]), GRB.EQUAL, 0, f"init_zero[{j},{q}]")
            if f.swap:                                                   # (17)
                add("(17)", n[j, L, H] - f.R_end * y[j], GRB.GREATER_EQUAL, 0, f"end_local[{j}]")
        # (18) network-wide recovery share over ALL facilities (DECISIONS)
        add("(18)", gp.quicksum(n[j, L, H] for j in inst.N) - inst.rho * gp.quicksum(B.values()),
            GRB.GREATER_EQUAL, 0, "end_share")

        # ----------------------------------------------------------- (20), (21)
        p_ch = disc.p_ch_kw
        group_load: Dict[Tuple[Any, int], List[gp.Var]] = defaultdict(list)
        for j in inst.Cset:
            f = inst.facility(j)
            for t in range(H):
                tot = gp.quicksum(c[j, q, t] for q in range(L))
                add("(20)", tot - C[j], GRB.LESS_EQUAL, 0, f"chargers[{j},{t}]")
                add("(20)", p_ch * tot - f.P_kw * y[j], GRB.LESS_EQUAL, 0, f"site_power[{j},{t}]")
                if f.group is not None:
                    group_load[(f.group, t)].extend(c[j, q, t] for q in range(L))
        for (g, t), vs in group_load.items():
            lim = inst.grid_limit(g, t)
            if math.isinf(lim):
                continue
            add("(21)", p_ch * gp.quicksum(vs), GRB.LESS_EQUAL, lim, f"grid[{g},{t}]")

        # ------------------------------------------------------------- (22)
        for j in inst.S:
            f = inst.facility(j)
            for tau in range(H):
                ids = occ.get((j, tau))
                if ids:
                    add("(22)", gp.quicksum(x[a] for a in ids) - f.M * y[j], GRB.LESS_EQUAL, 0,
                        f"swap_pos[{j},{tau}]")

        # ------------------------------------------------------------- (33)
        if sw["budget"] is not None and shared is None:
            inv = gp.quicksum(f.Fhat * y[f.id] + f.bhat * B[f.id] + f.chat * C[f.id]
                              for f in inst.facilities)
            add("(33)", inv, GRB.LESS_EQUAL, float(sw["budget"]), "budget")
        self.sum_u = gp.quicksum(u.values())
        if sw["zeta"] is not None and inst.orders:
            add("(33)", len(inst.orders) - self.sum_u, GRB.GREATER_EQUAL,
                float(sw["zeta"]) * len(inst.orders), "service_share")

        # ------------------------------------------------------ objective (26)-(32)
        comp = self.components
        comp["C_setup"] = gp.quicksum(f.F * y[f.id] + f.bB * B[f.id] + f.bC * C[f.id]
                                      for f in inst.facilities)                       # (27)
        comp["C_elec"] = gp.quicksum(inst.price(j, t) * disc.kwh_per_step * c[j, q, t]
                                     for (j, q, t) in c_keys)                         # (28)
        comp["C_travel"] = gp.LinExpr(travel_coef, [x[a] for a in travel_ids])          # (29)
        comp["C_orders"] = (gp.quicksum(o.P * u[o.id] for o in inst.orders)
                            + gp.LinExpr(theta_coef, [x[a] for a in theta_ids]))      # (30)-(31)
        comp["C_reb"] = (gp.quicksum(s0.f * h[s0.id] for s0 in inst.services)
                         + gp.quicksum(inst.service(e).vreb_q(q) * z[e, q] for (e, q) in z_keys))  # (32)
        comp["C_dummy_terminal"] = gp.LinExpr(dummy_coef, [x[a] for a in dummy_ids])
        self.objective = gp.quicksum(comp.values())                                   # (26)
        if self._set_objective:
            m.setObjective(self.objective, GRB.MINIMIZE)

    # ---------------------------------------------------------- MIP start
    def _translate_schedule(self, sched: Schedule) -> Schedule:
        """Map a schedule written against ``lib_original`` onto ``lib`` (needed after a
        co-located rebuild); arcs are matched by ``(kind, src, dst, order, fac)``."""
        if self.lib is self.lib_original:
            return sched
        x: Dict[Any, List[int]] = {}
        for k, ids in sched.x.items():
            new_ids = []
            for a_id in ids:
                a = self.lib_original.arc(a_id)
                b = self.lib.find(k, a.kind, a.src, order=a.order, fac=a.fac, dst=a.dst)
                if b is None:
                    raise ValueError(f"MIP start arc {a_id} of bike {k} has no counterpart in the "
                                     f"rebuilt (co-located) library")
                new_ids.append(b.id)
            x[k] = new_ids
        return Schedule(x=x, u=sched.u, c=sched.c, h=sched.h, z=sched.z, y=sched.y, B=sched.B,
                        C=sched.C, n=sched.n, meta=sched.meta)

    def set_mip_start(self, sched: Schedule, verify: bool = True) -> Dict[str, Any]:
        """Load a :class:`Schedule` into the ``Start`` attributes of all variables.

        Every variable receives a start value (``x`` 1 on chosen arcs, 0 elsewhere;
        ``u``, ``c``, ``h``, ``z`` from the schedule with missing entries 0;
        ``y/B/C`` from ``evaluate.facility_vars``; ``n`` from ``sched.n`` or the (13)
        recursion).  The schedule is priced and checked with ``evaluate`` and, with
        ``verify=True``, Gurobi is asked to solve the model with all variables fixed
        to the start (bounds temporarily tightened and restored), which certifies
        acceptance independently of the log.  Returns and stores ``mip_start_info``:
        ``given``, ``start_obj`` (evaluate.cost total), ``start_check_ok``,
        ``start_violations``, ``verified`` (``True``/``False``/``None`` if not run),
        ``verified_obj``, ``verified_status``.
        """
        inst, lib, m = self.inst, self.lib, self.model
        sched = self._translate_schedule(sched)
        cst = cost(inst, lib, sched)
        rep = check(inst, lib, sched, switches=self.switches)
        yv, Bv, Cv = facility_vars(inst, sched)
        chosen = set()
        for ids in sched.x.values():
            chosen.update(int(a) for a in ids)
        vals: Dict[gp.Var, float] = {}
        for a_id, var in self.x.items():
            vals[var] = 1.0 if a_id in chosen else 0.0
        for i, var in self.u.items():
            vals[var] = float(sched.u.get(i, 0))
        for j in inst.N:
            vals[self.y[j]] = float(yv[j])
            vals[self.B[j]] = float(Bv[j])
            vals[self.C[j]] = float(Cv[j])
        for key, var in self.c.items():
            vals[var] = float(sched.c.get(key, 0))
        for e, var in self.h.items():
            vals[var] = float(sched.h.get(e, 0))
        for key, var in self.z.items():
            vals[var] = float(sched.z.get(key, 0))
        n = sched.n
        if n is None:
            n = reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z, Bv)
        for key, var in self.n.items():
            vals[var] = float(n.get(key, 0))
        var_list = list(vals.keys())
        val_list = [vals[v] for v in var_list]
        m.setAttr("Start", var_list, val_list)
        self._start_values = vals
        info: Dict[str, Any] = {
            "given": True, "start_obj": cst["total"], "start_check_ok": rep["ok"],
            "start_violations": rep["n_violations"], "verified": None,
            "verified_obj": None, "verified_status": None,
        }
        if verify:
            ok, obj, status = self.verify_mip_start()
            info.update(verified=ok, verified_obj=obj, verified_status=status)
        self.mip_start_info = info
        return info

    def verify_mip_start(self, time_limit: float = 60.0) -> Tuple[bool, Optional[float], str]:
        """Fix every variable to its stored start value, solve, restore the bounds.

        Returns ``(feasible, objective, status_name)``; ``feasible`` is ``True`` iff
        Gurobi finds the fixed point feasible, i.e. the MIP start is acceptable.
        """
        if not self._start_values:
            raise ValueError("no MIP start loaded")
        m = self.model
        vars_ = list(self._start_values.keys())
        lbs = m.getAttr("LB", vars_)
        ubs = m.getAttr("UB", vars_)
        vals = [self._start_values[v] for v in vars_]
        old_tl = m.Params.TimeLimit
        try:
            m.setAttr("LB", vars_, vals)
            m.setAttr("UB", vars_, vals)
            m.Params.TimeLimit = min(old_tl, time_limit)
            m.optimize()
            feasible = m.Status == GRB.OPTIMAL and m.SolCount > 0
            obj = m.ObjVal if feasible else None
            status = status_name(m.Status)
        finally:
            m.setAttr("LB", vars_, lbs)
            m.setAttr("UB", vars_, ubs)
            m.Params.TimeLimit = old_tl
            m.update()
        return feasible, obj, status

    # ------------------------------------------------------------- solving
    def _callback(self, model: gp.Model, where: int) -> None:
        if where == GRB.Callback.MIPSOL and self._first_incumbent is None:
            self._first_incumbent = (model.cbGet(GRB.Callback.MIPSOL_OBJ),
                                     model.cbGet(GRB.Callback.MIPSOL_NODCNT))

    def _optimize(self) -> None:
        self._first_incumbent = None
        self.model.optimize(lambda mdl, where: self._callback(mdl, where))

    def solve(self, mip_start: Optional[Schedule] = None, verify_start: bool = True,
              obj_tol: float = 1e-6) -> Tuple[Optional[Schedule], Dict[str, Any]]:
        """Optimise and return ``(schedule, stats)``.

        With ``lexicographic`` the model is first solved for ``min sum_i u_i``; the
        optimal count is then imposed as ``sum_i u_i <= U*`` and the cost (26) is
        minimised (E2 p.9 alternative to (33)).  ``schedule`` is ``None`` when no
        incumbent exists (infeasible / time limit without solution); otherwise it is
        the incumbent, which must pass ``evaluate.check`` with zero violations and
        whose ``evaluate.cost`` total must equal the Gurobi objective within
        ``obj_tol * max(1, |obj|)``, else :class:`ILPConsistencyError` is raised.

        ``stats`` keys: ``status``, ``status_code``, ``obj``, ``bound``, ``gap``,
        ``runtime``, ``build_time``, ``n_vars``, ``n_binaries``, ``n_integers``
        (Gurobi's NumIntVars, binaries included), ``n_rows``, ``n_nonzeros``,
        ``rows_by_family``, ``node_count``, ``sol_count``, ``cost`` (evaluate.cost
        dict), ``components`` (objective LinExpr values), ``check`` (families /
        notes of evaluate.check), ``mip_start`` (see :meth:`set_mip_start`, plus
        ``first_incumbent_obj``/``first_incumbent_node`` and ``accepted``),
        ``switches``, and for lexicographic runs ``lex_min_unserved``,
        ``lex_stage1_status``, ``lex_stage1_runtime``, ``lex_certified`` (stage 1
        proved optimal) and, when it did not, ``lex_min_unserved_bound`` (Gurobi's
        ``ObjBound`` of stage 1): then ``lex_min_unserved`` is only the incumbent's
        count, an upper bound, and the result is *not* a certified lexicographic
        optimum (a ``UserWarning`` is issued; reviewer F7).  ``evaluate.check`` is
        run with the effective ``switches`` so that ``no_transfers`` / ``budget`` /
        ``zeta`` given as keywords are re-verified independently of Gurobi.
        """
        m = self.model
        if mip_start is not None:
            self.set_mip_start(mip_start, verify=verify_start)
        stats: Dict[str, Any] = {"switches": dict(self.switches), "build_time": self.build_time}
        total_runtime = 0.0
        if self.switches["lexicographic"]:
            m.setObjective(self.sum_u, GRB.MINIMIZE)
            self._optimize()
            total_runtime += m.Runtime
            stats["lex_stage1_status"] = status_name(m.Status)
            stats["lex_stage1_runtime"] = m.Runtime
            if m.SolCount == 0:
                stats.update(self._size_stats(), status=status_name(m.Status),
                             status_code=m.Status, obj=None, bound=None, gap=None,
                             runtime=total_runtime, sol_count=0)
                return None, stats
            u_star = int(round(m.ObjVal))
            stats["lex_min_unserved"] = u_star
            stats["lex_certified"] = bool(m.Status == GRB.OPTIMAL)
            if not stats["lex_certified"]:
                try:
                    stats["lex_min_unserved_bound"] = float(m.ObjBound)
                except gp.GurobiError:
                    stats["lex_min_unserved_bound"] = None
                warnings.warn(
                    f"lexicographic stage 1 stopped with status {stats['lex_stage1_status']}: "
                    f"min sum u_i = {u_star} is the incumbent's count (bound "
                    f"{stats['lex_min_unserved_bound']}), not a certified minimum", UserWarning,
                    stacklevel=2)
            m.addLConstr(self.sum_u, GRB.LESS_EQUAL, u_star, name="lex_unserved")
            self.n_rows["lex"] += 1
            m.setObjective(self.objective, GRB.MINIMIZE)
        self._optimize()
        total_runtime += m.Runtime
        stats.update(self._size_stats())
        stats.update(status=status_name(m.Status), status_code=m.Status, runtime=total_runtime,
                     node_count=m.NodeCount, sol_count=m.SolCount)
        ms = dict(self.mip_start_info)
        if ms.get("given"):
            fi = self._first_incumbent
            ms["first_incumbent_obj"] = None if fi is None else fi[0]
            ms["first_incumbent_node"] = None if fi is None else fi[1]
            if ms.get("verified") is not None:
                ms["accepted"] = bool(ms["verified"])
            else:
                ms["accepted"] = (fi is not None and ms["start_obj"] is not None
                                  and fi[0] <= ms["start_obj"] + 1e-6 * max(1.0, abs(ms["start_obj"])))
        stats["mip_start"] = ms
        if m.SolCount == 0:
            stats.update(obj=None, bound=None, gap=None)
            return None, stats
        obj = m.ObjVal
        stats["obj"] = obj
        try:
            stats["bound"] = m.ObjBound
            stats["gap"] = m.MIPGap
        except gp.GurobiError:
            stats["bound"], stats["gap"] = None, None
        sched = self.extract_schedule()
        cst = cost(self.inst, self.lib, sched)
        rep = check(self.inst, self.lib, sched, switches=self.switches)
        stats["cost"] = cst
        stats["components"] = {name: expr.getValue() for name, expr in self.components.items()}
        stats["check"] = {"ok": rep["ok"], "n_violations": rep["n_violations"],
                          "families": rep["families"], "notes": rep["notes"]}
        if not rep["ok"]:
            raise ILPConsistencyError(
                f"extracted schedule violates {rep['n_violations']} constraint(s): "
                + "; ".join(f"{fam}: {rec['examples'][:2]}" for fam, rec in rep["families"].items()))
        if abs(cst["total"] - obj) > obj_tol * max(1.0, abs(obj)):
            raise ILPConsistencyError(
                f"evaluate.cost total {cst['total']!r} differs from Gurobi objective {obj!r}")
        sched.meta.update(status=stats["status"], obj=obj, bound=stats["bound"], gap=stats["gap"],
                          runtime=total_runtime, switches=dict(self.switches))
        return sched, stats

    def _size_stats(self) -> Dict[str, Any]:
        m = self.model
        m.update()
        return {
            "n_vars": m.NumVars, "n_binaries": m.NumBinVars, "n_integers": m.NumIntVars,
            "n_rows": m.NumConstrs, "n_nonzeros": m.NumNZs,
            "rows_by_family": dict(self.n_rows), "n_arcs": len(self.lib),
        }

    # ------------------------------------------------------------ extraction
    def extract_schedule(self) -> Schedule:
        """Round the incumbent into a :class:`Schedule` (CONTRACT.md Section 3):
        ``x`` per bike, ``u`` for every order, nonzero ``c`` and ``z``, ``h`` for every
        service, ``y/B/C`` for every facility and the full ``n`` table ``t = 0..H``."""
        inst, lib, m = self.inst, self.lib, self.model
        if m.SolCount == 0:
            raise RuntimeError("no solution available")
        xv = m.getAttr("X", self.x)
        x: Dict[Any, List[int]] = {b.id: [] for b in inst.bikes}
        for a in lib.arcs:
            if xv[a.id] > 0.5:
                x[a.k].append(a.id)
        u = {i: int(round(v)) for i, v in m.getAttr("X", self.u).items()} if len(self.u) else {}
        c = ({key: int(round(v)) for key, v in m.getAttr("X", self.c).items() if round(v) != 0}
             if len(self.c) else {})
        h = {e: int(round(v)) for e, v in m.getAttr("X", self.h).items()} if len(self.h) else {}
        z = ({key: int(round(v)) for key, v in m.getAttr("X", self.z).items() if round(v) != 0}
             if len(self.z) else {})
        y = {j: int(round(var.X)) for j, var in self.y.items()}
        B = {j: int(round(var.X)) for j, var in self.B.items()}
        C = {j: int(round(var.X)) for j, var in self.C.items()}
        n = {key: int(round(v)) for key, v in m.getAttr("X", self.n).items()}
        return Schedule(x=x, u=u, c=c, h=h, z=z, y=y, B=B, C=C, n=n,
                        meta={"solver": "gurobi", "colocated": self.switches["colocated"]})


# ---------------------------------------------------------------------------
# module-level API
# ---------------------------------------------------------------------------
def _resolve(value: Any, inst: Instance, name: str) -> Any:
    return inst.option(name) if value is None else value


def build_model(inst: Instance, arcs: ArcLibrary, *, no_transfers: Optional[bool] = None,
                colocated: Optional[bool] = None, fixed_facilities: Optional[bool] = None,
                budget: Optional[float] = None, zeta: Optional[float] = None,
                lexicographic: Optional[bool] = None, battery_swap_v1_bounds: Optional[bool] = None,
                mip_start: Optional[Schedule] = None, threads: int = 4, time_limit: float = 600.0,
                output: bool = False, params: Optional[Dict[str, Any]] = None,
                verify_start: bool = True) -> ILPModel:
    """Build the E2 ILP (5)-(22), (26)-(33) and return an :class:`ILPModel`.

    Switch arguments left at ``None`` take ``inst.options[name]`` (``no_transfers``,
    ``colocated``, ``lexicographic``, ``battery_swap_v1_bounds`` default ``False``;
    ``fixed_facilities`` ``None``/``True`` = fix ``y/B/C`` wherever the facility data
    give a value, ``False`` = all facility variables free) and ``inst.budget`` /
    ``inst.zeta`` for (33).  ``mip_start`` (a :class:`Schedule`, e.g. the baseline)
    is loaded with :meth:`ILPModel.set_mip_start` (verified by a fixed solve when
    ``verify_start``).  Gurobi parameters: ``OutputFlag = output``, ``Threads``,
    ``TimeLimit`` and any extra ``params`` (``{'MIPGap': 0.01}``).
    """
    fixed = _resolve(fixed_facilities, inst, "fixed_facilities")
    fixed = True if fixed is None else bool(fixed)
    mdl = ILPModel(
        inst, arcs,
        no_transfers=bool(_resolve(no_transfers, inst, "no_transfers")),
        colocated=bool(_resolve(colocated, inst, "colocated")),
        fixed_facilities=fixed,
        budget=inst.budget if budget is None else budget,
        zeta=inst.zeta if zeta is None else zeta,
        lexicographic=bool(_resolve(lexicographic, inst, "lexicographic")),
        battery_swap_v1_bounds=bool(_resolve(battery_swap_v1_bounds, inst, "battery_swap_v1_bounds")),
        threads=threads, time_limit=time_limit, output=output, params=params,
    )
    if mip_start is not None:
        mdl.set_mip_start(mip_start, verify=verify_start)
    return mdl


def solve(inst: Instance, arcs: ArcLibrary, *, mip_start: Optional[Schedule] = None,
          verify_start: bool = True, obj_tol: float = 1e-6,
          **build_kwargs: Any) -> Tuple[Optional[Schedule], Dict[str, Any]]:
    """Build (see :func:`build_model`) and solve; returns ``(schedule, stats)`` as
    :meth:`ILPModel.solve`.  ``schedule`` is ``None`` without an incumbent.  The
    stats carry the ``evaluate.cost`` components (``stats['cost']``) so that ILP
    and baseline results are priced by the same code."""
    mdl = build_model(inst, arcs, **build_kwargs)
    return mdl.solve(mip_start=mip_start, verify_start=verify_start, obj_tol=obj_tol)
