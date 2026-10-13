"""Schedule container, objective (26)-(32), constraint checker (5)-(22) and
reporting metrics for E2 (``notes/extracted/E2.txt``; conventions in
``notes/DECISIONS.md``).  Solver-independent: both the Gurobi solution
(``ilp.py``) and the event-driven baseline (``baseline.py``) are converted to a
:class:`Schedule` and priced / checked by the same code.

Index conventions
-----------------
* ``x[k]``   : list (or set) of *arc ids* chosen by bike ``k`` (ids from ``ArcLibrary``).
* ``u[i]``   : 0/1, order ``i`` unserved (6).
* ``y/B/C[j]``: facility decisions (7)-(8); ``None`` = take the fixed values of the
  ``Facility`` records.
* ``n[(j, q, t)]`` : stock at boundary ``t = 0..H`` after transport arrivals and
  before new actions (13); ``None`` = reconstruct from (13).
* ``c[(j, q, t)]`` : batteries charged ``q -> q+1`` in slot ``t`` (``q < L``, ``t < H``).
* ``h[e]``, ``z[(e, q)]`` : transport service use and loads (10); ``q = 0..L``.
Missing dictionary entries are zeros.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .arcs import Arc, ArcLibrary, SINK
from .or_instance import Instance

_TOL = 1e-6


@dataclass
class Schedule:
    """All independent decisions of E2 (Section 2 table) in plain dictionaries.

    ``x`` maps bike id -> iterable of arc ids (order irrelevant; :meth:`path`
    sorts by start time).  ``u``, ``c``, ``h``, ``z`` as in the module docstring.
    ``y``, ``B``, ``C`` and ``n`` are optional (``None`` = fixed data / reconstruct).
    ``meta`` is free-form (solver status, baseline flags, ...).
    """
    x: Dict[Any, Iterable[int]]
    u: Dict[Any, int] = field(default_factory=dict)
    c: Dict[Tuple[Any, int, int], int] = field(default_factory=dict)
    h: Dict[Any, int] = field(default_factory=dict)
    z: Dict[Tuple[Any, int], int] = field(default_factory=dict)
    y: Optional[Dict[Any, int]] = None
    B: Optional[Dict[Any, int]] = None
    C: Optional[Dict[Any, int]] = None
    n: Optional[Dict[Tuple[Any, int, int], int]] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    # ----------------------------------------------------------- helpers
    def arc_ids(self, k: Any) -> List[int]:
        return list(self.x.get(k, ()))

    def path(self, k: Any, lib: ArcLibrary) -> List[Arc]:
        """Arcs of bike ``k`` sorted by ``(l, u)`` (a valid path is totally ordered)."""
        arcs = [lib.arc(a) for a in self.arc_ids(k)]
        arcs.sort(key=lambda a: (a.l, a.u, a.kind == "term"))
        return arcs

    def chosen_arcs(self, lib: ArcLibrary) -> List[Arc]:
        """All chosen arcs of all bikes."""
        out: List[Arc] = []
        for k in self.x:
            out.extend(lib.arc(a) for a in self.arc_ids(k))
        return out

    # -------------------------------------------------------------- JSON
    def to_dict(self) -> dict:
        def enc(v):
            return [enc(w) for w in v] if isinstance(v, tuple) else v
        return {
            "x": [[enc(k), sorted(int(a) for a in ids)] for k, ids in self.x.items()],
            "u": [[enc(i), int(val)] for i, val in self.u.items()],
            "c": [[enc(j), q, t, int(val)] for (j, q, t), val in self.c.items() if val],
            "h": [[enc(e), int(val)] for e, val in self.h.items()],
            "z": [[enc(e), q, int(val)] for (e, q), val in self.z.items() if val],
            "y": None if self.y is None else [[enc(j), int(v)] for j, v in self.y.items()],
            "B": None if self.B is None else [[enc(j), int(v)] for j, v in self.B.items()],
            "C": None if self.C is None else [[enc(j), int(v)] for j, v in self.C.items()],
            "n": None if self.n is None else [[enc(j), q, t, int(v)] for (j, q, t), v in self.n.items()],
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Schedule":
        def dec(v):
            return tuple(dec(w) for w in v) if isinstance(v, list) else v
        def kv(lst):
            return None if lst is None else {dec(k): v for k, v in lst}
        return cls(
            x={dec(k): list(ids) for k, ids in d["x"]},
            u=kv(d.get("u", [])) or {},
            c={(dec(j), q, t): v for j, q, t, v in d.get("c", [])},
            h=kv(d.get("h", [])) or {},
            z={(dec(e), q): v for e, q, v in d.get("z", [])},
            y=kv(d.get("y")), B=kv(d.get("B")), C=kv(d.get("C")),
            n=None if d.get("n") is None else {(dec(j), q, t): v for j, q, t, v in d["n"]},
            meta=d.get("meta", {}),
        )


# ---------------------------------------------------------------------------
# derived quantities
# ---------------------------------------------------------------------------
def facility_vars(inst: Instance, sched: Schedule) -> Tuple[Dict[Any, int], Dict[Any, int], Dict[Any, int]]:
    """Effective ``(y, B, C)`` per facility: schedule values if given, else the fixed
    data of the ``Facility`` records (``None`` in the data counts as ``y = 1``,
    ``B = C = 0`` and is flagged by :func:`check`)."""
    y: Dict[Any, int] = {}
    B: Dict[Any, int] = {}
    C: Dict[Any, int] = {}
    for f in inst.facilities:
        yv = sched.y.get(f.id) if sched.y is not None else f.y
        Bv = sched.B.get(f.id) if sched.B is not None else f.B
        Cv = sched.C.get(f.id) if sched.C is not None else f.C
        y[f.id] = 1 if yv is None else int(yv)
        B[f.id] = 0 if Bv is None else int(Bv)
        C[f.id] = 0 if Cv is None else int(Cv)
    return y, B, C


def swap_counts(inst: Instance, lib: ArcLibrary, x: Dict[Any, Iterable[int]]
                ) -> Tuple[Dict[Tuple[Any, int, int], int], Dict[Tuple[Any, int], int]]:
    """``s_jqt`` and ``S_jt`` of (12) from the chosen swap arcs: ``s[(j, q, t)]`` counts
    swap arcs at facility ``j`` starting at ``t`` with return level ``q < L``."""
    s: Dict[Tuple[Any, int, int], int] = defaultdict(int)
    S: Dict[Tuple[Any, int], int] = defaultdict(int)
    for k, ids in x.items():
        for a_id in ids:
            a = lib.arc(a_id)
            if a.kind == "swap":
                s[(a.fac, a.src[2], a.l)] += 1
                S[(a.fac, a.l)] += 1
    return dict(s), dict(S)


def transfer_counts(inst: Instance, z: Dict[Tuple[Any, int], int]
                    ) -> Tuple[Dict[Tuple[Any, int, int], int], Dict[Tuple[Any, int, int], int]]:
    """Departures ``D_jqt`` and arrivals ``A_jqt`` of (11) from the loads ``z_eq``:
    ``D[(o_e, q, l_e)] += z_eq`` and ``A[(d_e, q, u_e)] += z_eq``."""
    D: Dict[Tuple[Any, int, int], int] = defaultdict(int)
    A: Dict[Tuple[Any, int, int], int] = defaultdict(int)
    for (e, q), val in z.items():
        if not val:
            continue
        svc = inst.service(e)
        D[(svc.o_fac, q, svc.l)] += int(val)
        A[(svc.d_fac, q, svc.u)] += int(val)
    return dict(D), dict(A)


def in_transit(inst: Instance, z: Dict[Tuple[Any, int], int]) -> List[int]:
    """``m_t`` of (24) for ``t = 0..H``: batteries on services with ``l_e < t < u_e`` (strict)."""
    m = [0] * (inst.H + 1)
    for (e, q), val in z.items():
        if not val:
            continue
        svc = inst.service(e)
        for t in range(svc.l + 1, svc.u):
            m[t] += int(val)
    return m


def reconstruct_inventory(inst: Instance, lib: ArcLibrary, x: Dict[Any, Iterable[int]],
                          c: Dict[Tuple[Any, int, int], int], z: Dict[Tuple[Any, int], int],
                          B: Optional[Dict[Any, int]] = None
                          ) -> Dict[Tuple[Any, int, int], int]:
    """Recompute ``n_jqt`` for all ``j in N``, ``q = 0..L``, ``t = 0..H`` from (16) and
    the balance (13)::

        n[j][q][t+1] = n[j][q][t] - c[j][q][t] + c[j][q-1][t] + s[j][q][t]
                       - 1{q=L} S[j][t] - D[j][q][t] + A[j][q][t+1]

    with the fixed zeros ``c[j][-1][t] = c[j][L][t] = 0`` and ``s[j][L][t] = 0``.
    Initial stock (16): ``n[j][L][0] = B_j`` (``B`` argument, else ``Facility.B``),
    other levels 0.  Negative values are returned as computed (the checker
    flags them); nothing is clipped.
    """
    H, L = inst.H, inst.L
    if B is None:
        B = {f.id: (0 if f.B is None else int(f.B)) for f in inst.facilities}
    s, S = swap_counts(inst, lib, x)
    D, A = transfer_counts(inst, z)
    n: Dict[Tuple[Any, int, int], int] = {}
    for f in inst.facilities:
        j = f.id
        for q in range(L + 1):
            n[(j, q, 0)] = int(B.get(j, 0)) if q == L else 0
        for t in range(H):
            S_jt = S.get((j, t), 0)
            for q in range(L + 1):
                c_q = c.get((j, q, t), 0) if q < L else 0
                c_qm = c.get((j, q - 1, t), 0) if q >= 1 else 0
                s_q = s.get((j, q, t), 0) if q < L else 0
                n[(j, q, t + 1)] = (n[(j, q, t)] - c_q + c_qm + s_q - (S_jt if q == L else 0)
                                    - D.get((j, q, t), 0) + A.get((j, q, t + 1), 0))
    return n


# ---------------------------------------------------------------------------
# objective (26)-(32)
# ---------------------------------------------------------------------------
def cost(inst: Instance, lib: ArcLibrary, sched: Schedule) -> Dict[str, Any]:
    """Objective (26) and its components, exactly as written:

    * ``C_setup`` (27) ``sum_j F_j y_j + bB_j B_j + bC_j C_j`` (a constant when
      facilities are fixed; reported anyway);
    * ``C_elec`` (28) ``sum_{j in C, t} pi_jt (eps/eta) sum_{q<L} c_jqt``;
    * ``C_travel`` (29) ``kappa sum_k sum_a d_a x_ka``;
    * ``C_orders`` (30)-(31) split into ``unserved`` ``sum_i P_i u_i``, ``response``
      ``sum w_i Delta (u_a - r_i)`` and ``lateness`` ``sum v_i Delta [u_a - b_i]_+``
      over chosen delivery arcs;
    * ``C_reb`` (32) ``sum_e f_e h_e + sum_q v^reb_eq z_eq``;
    * ``total`` = (26).  ``C_dummy_terminal`` (penalised dummy terminal arcs, 0 in
      the written model) is listed separately and included in ``total``.
    """
    y, B, C = facility_vars(inst, sched)
    disc = inst.disc
    C_setup = sum(f.F * y[f.id] + f.bB * B[f.id] + f.bC * C[f.id] for f in inst.facilities)
    C_elec = 0.0
    charge_ids = set(inst.Cset)
    for (j, q, t), val in sched.c.items():
        if val and j in charge_ids and q < inst.L:
            C_elec += inst.price(j, t) * disc.kwh_per_step * val
    C_travel = 0.0
    response = 0.0
    lateness = 0.0
    dummy = 0.0
    for a in sched.chosen_arcs(lib):
        C_travel += a.d_km
        if a.kind == "deliver":
            o = inst.order(a.order)
            response += o.w * disc.Delta_h * (a.u - o.r)
            lateness += o.v * disc.Delta_h * max(a.u - o.b, 0)
        elif a.kind == "term" and a.fac is None:
            dummy += a.theta
    C_travel *= inst.kappa
    unserved = sum(inst.order(i).P * val for i, val in sched.u.items() if val)
    C_reb = 0.0
    for e, val in sched.h.items():
        if val:
            C_reb += inst.service(e).f * val
    for (e, q), val in sched.z.items():
        if val:
            C_reb += inst.service(e).vreb_q(q) * val
    C_orders = unserved + response + lateness
    total = C_setup + C_elec + C_travel + C_orders + C_reb + dummy
    return {
        "C_setup": C_setup, "C_elec": C_elec, "C_travel": C_travel,
        "C_orders": C_orders,
        "C_orders_parts": {"unserved": unserved, "response": response, "lateness": lateness},
        "C_reb": C_reb, "C_dummy_terminal": dummy, "total": total,
    }


# ---------------------------------------------------------------------------
# constraint checker
# ---------------------------------------------------------------------------
class _Report:
    def __init__(self, max_examples: int = 10) -> None:
        self.fam: Dict[str, Dict[str, Any]] = {}
        self.max_examples = max_examples

    def add(self, family: str, msg: str) -> None:
        rec = self.fam.setdefault(family, {"count": 0, "examples": []})
        rec["count"] += 1
        if len(rec["examples"]) < self.max_examples:
            rec["examples"].append(msg)


def check(inst: Instance, lib: ArcLibrary, sched: Schedule, max_examples: int = 10,
          switches: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Verify a schedule against every constraint family of E2 and the identity (24).

    ``switches`` are the *effective* model switches of an ILP run
    (``ILPModel.switches``: ``no_transfers``, ``budget``, ``zeta``); when given they
    take precedence over ``inst.options['no_transfers']``, ``inst.budget`` and
    ``inst.zeta`` so that switches passed as ``build_model`` keywords are
    re-verified by solver-independent code too (reviewer F5).

    Returns ``{'ok': bool, 'n_violations': int, 'families': {name: {'count', 'examples'}},
    'identity_24_ok': bool, 'notes': [...], 'n_source': 'given'|'reconstructed'}``.
    Family keys (E2 equation numbers):

    * ``'arcs'``   arc ids exist and belong to the bike;
    * ``'(5)'``    unit path flow per bike (out - in = 1 at ``s_k``, -1 at sink, 0 else);
      a path that tiles ``[0, H]`` but ends at ``(v, H, q)`` without a terminal arc
      (no admissible certificate (9) -- the baseline's ``no_terminal_arc`` case) is
      reported under ``'(9)'`` instead, since every other flow row holds;
    * ``'(6)'``    each order served once or unserved;
    * ``'(7)-(8)'`` facility bounds (``0 <= B <= K y``, ``0 <= C <= min(Cbar,K) y``,
      ``C = 0`` off ``C``, ``C >= y`` on ``C \\ S``; optional v1 bounds);
    * ``'(9)'``    chosen terminal arc only at an open swap site (dummy arcs noted);
    * ``'(10)'``   ``h_e <= sum_q z_eq <= U_e h_e``, ``h_e <= y_oe, y_de``;
    * ``'(13)'``   given ``n`` equals the (13) recursion; ``'(16)'`` initial stock;
    * ``'(14)'``   joint availability ``c + D <= n`` (``q < L``), ``S + D_L <= n_L``;
    * ``'(15)'``   storage ``sum_q n_jqt <= K_j y_j`` for ``t = 0..H``;
    * ``'(17)'``   ``n_jLH >= R_end_j y_j`` (``j in S``); ``'(18)'`` ``sum_j n_jLH >= rho sum_j B_j``;
    * ``'(20)'``   chargers / site power, ``c = 0`` off ``C``; ``'(21)'`` grid groups;
    * ``'(22)'``   swap occupancy over ``[l_a, u_a)`` ``<= M_j y_j``;
    * ``'(33)'``   optional budget / service share when set on the instance;
    * ``'domain'`` integrality / sign / binary domains and negative stock.
    Identity (24) ``sum_j N_jt + m_t = sum_j B_j`` is reported in ``identity_24_ok``
    and, when violated, under family ``'(24)'``.
    """
    rep = _Report(max_examples)
    notes: List[str] = []
    H, L = inst.H, inst.L
    sw = switches or {}

    def _switch(name: str, fallback: Any) -> Any:
        return fallback if sw.get(name) is None else sw[name]
    disc = inst.disc
    y, B, C = facility_vars(inst, sched)
    opts = inst.options

    # ---------------------------------------------------------- domains
    for i, val in sched.u.items():
        if val not in (0, 1):
            rep.add("domain", f"u[{i}] = {val} not binary")
    for e, val in sched.h.items():
        if val not in (0, 1):
            rep.add("domain", f"h[{e}] = {val} not binary")
    for key, val in sched.z.items():
        if val < 0 or int(val) != val:
            rep.add("domain", f"z[{key}] = {val} not a nonnegative integer")
        if key[1] < 0 or key[1] > L:
            rep.add("domain", f"z[{key}] level outside 0..L")
    for (j, q, t), val in sched.c.items():
        if val < 0 or int(val) != val:
            rep.add("domain", f"c[{(j, q, t)}] = {val} not a nonnegative integer")
        if not (0 <= q < L) or not (0 <= t < H):
            if val:
                rep.add("domain", f"c[{(j, q, t)}] outside q < L, t < H (fixed zero)")
    for j in inst.N:
        if y[j] not in (0, 1):
            rep.add("domain", f"y[{j}] = {y[j]} not binary")
        if B[j] < 0 or C[j] < 0:
            rep.add("domain", f"B[{j}] = {B[j]}, C[{j}] = {C[j]} must be >= 0")

    # ------------------------------------------------------- arcs and (5)
    chosen_by_bike: Dict[Any, List[Arc]] = {}
    for b in inst.bikes:
        k = b.id
        ids = sched.arc_ids(k)
        arcs: List[Arc] = []
        for a_id in ids:
            if not (0 <= a_id < len(lib.arcs)):
                rep.add("arcs", f"bike {k}: arc id {a_id} does not exist")
                continue
            a = lib.arc(a_id)
            if a.k != k:
                rep.add("arcs", f"bike {k}: arc {a_id} belongs to bike {a.k}")
                continue
            arcs.append(a)
        if len(set(a.id for a in arcs)) != len(arcs):
            rep.add("arcs", f"bike {k}: duplicate arc ids")
        chosen_by_bike[k] = arcs
        flow: Dict[Tuple, int] = defaultdict(int)
        for a in arcs:
            flow[a.src] += 1
            flow[a.dst] -= 1
        src = lib.source(k)
        mismatch = {node: val for node, val in flow.items()
                    if val != (1 if node == src else (-1 if node == SINK else 0))}
        open_end = None
        if arcs and SINK not in flow and src in flow and len(mismatch) == 1:
            node, val = next(iter(mismatch.items()))
            if val == -1 and node != src and len(node) == 3 and node[1] == H:   # entered, never left
                open_end = node            # a complete path to the horizon without a terminal arc
        if open_end is not None:
            rep.add("(9)", f"bike {k}: path ends at {open_end} without a terminal certificate "
                           f"(no admissible terminal arc (9); flow to the sink missing)")
        else:
            for node, val in mismatch.items():
                want = 1 if node == src else (-1 if node == SINK else 0)
                rep.add("(5)", f"bike {k}: net flow {val} at {node} (want {want})")
            if not arcs:
                rep.add("(5)", f"bike {k}: no arcs chosen (want a path from {src} to sink)")
            elif src not in flow:
                rep.add("(5)", f"bike {k}: path does not leave the source {src}")
            elif SINK not in flow:
                rep.add("(5)", f"bike {k}: path does not reach the sink")
    for k in sched.x:
        if k not in chosen_by_bike:
            rep.add("arcs", f"x has unknown bike {k}")

    # ------------------------------------------------------------- (6)
    served_by: Dict[Any, int] = defaultdict(int)
    for arcs in chosen_by_bike.values():
        for a in arcs:
            if a.kind == "deliver":
                served_by[a.order] += 1
    for o in inst.orders:
        lhs = served_by.get(o.id, 0) + int(sched.u.get(o.id, 0))
        if lhs != 1:
            rep.add("(6)", f"order {o.id}: deliveries {served_by.get(o.id, 0)} + u {sched.u.get(o.id, 0)} != 1")
    for i in served_by:
        if i not in inst._order:
            rep.add("(6)", f"delivery arc for unknown order {i}")

    # --------------------------------------------------------- (7)-(8)
    for f in inst.facilities:
        j = f.id
        if not (0 <= B[j] <= f.K * y[j]):
            rep.add("(7)-(8)", f"facility {j}: B={B[j]} outside 0..K y = {f.K * y[j]}")
        if not (0 <= C[j] <= min(f.Cbar, f.K) * y[j]):
            rep.add("(7)-(8)", f"facility {j}: C={C[j]} outside 0..min(Cbar,K) y = {min(f.Cbar, f.K) * y[j]}")
        if not f.charge and C[j] != 0:
            rep.add("(7)-(8)", f"facility {j}: C={C[j]} but j not in C")
        if f.charge and not f.swap and C[j] < y[j]:
            rep.add("(7)-(8)", f"facility {j}: C={C[j]} < y={y[j]} for j in C\\S")
        if opts.get("battery_swap_v1_bounds"):
            if y[j] > B[j]:
                rep.add("(7)-(8)", f"facility {j}: v1 bound y <= B violated")
            if C[j] > B[j]:
                rep.add("(7)-(8)", f"facility {j}: v1 bound C <= B violated")
        if sched.y is None and f.y is None:
            notes.append(f"facility {j}: y free in data and absent from schedule; assumed open")

    # ------------------------------------------------------------- (9)
    n_dummy = 0
    for k, arcs in chosen_by_bike.items():
        terms = [a for a in arcs if a.kind == "term"]
        for a in terms:
            if a.fac is None:
                n_dummy += 1
            elif y.get(a.fac, 0) != 1:
                rep.add("(9)", f"bike {k}: terminal arc labelled {a.fac} but y={y.get(a.fac)}")
    if n_dummy:
        notes.append(f"{n_dummy} dummy terminal arc(s) used (penalised, not in the written model)")

    # ------------------------------------------------------------ (10)
    for svc in inst.services:
        e = svc.id
        he = int(sched.h.get(e, 0))
        tot = sum(int(sched.z.get((e, q), 0)) for q in range(L + 1))
        if not (he <= tot <= svc.U * he):
            rep.add("(10)", f"service {e}: h={he}, sum_q z={tot}, U={svc.U}")
        if he > y.get(svc.o_fac, 0) or he > y.get(svc.d_fac, 0):
            rep.add("(10)", f"service {e}: used but endpoint closed (y_o={y.get(svc.o_fac)}, y_d={y.get(svc.d_fac)})")
    for (e, q), val in sched.z.items():
        if val and e not in inst._svc:
            rep.add("(10)", f"z for unknown service {e}")
    if _switch("no_transfers", opts.get("no_transfers")):
        if any(sched.h.values()) or any(sched.z.values()):
            rep.add("(10)", "no_transfers switch set but h/z nonzero")

    # -------------------------------------------------- inventory (13)-(18)
    x_chosen = {k: [a.id for a in arcs] for k, arcs in chosen_by_bike.items()}
    n_rec = reconstruct_inventory(inst, lib, x_chosen, sched.c, sched.z, B)
    if sched.n is not None:
        n_src = "given"
        n = dict(sched.n)
        for key, val in n_rec.items():
            given = n.get(key, 0)
            if given != val:
                fam = "(16)" if key[2] == 0 else "(13)"
                rep.add(fam, f"n{key}: given {given}, recursion gives {val}")
        for key in n:
            if key not in n_rec and n[key]:
                rep.add("domain", f"n{key}: outside index range")
    else:
        n_src = "reconstructed"
        n = n_rec
    s, S = swap_counts(inst, lib, x_chosen)
    D, A = transfer_counts(inst, sched.z)
    for f in inst.facilities:
        j = f.id
        for t in range(H + 1):
            for q in range(L + 1):
                if n.get((j, q, t), 0) < 0:
                    rep.add("domain", f"n{(j, q, t)} = {n.get((j, q, t), 0)} < 0")
            tot = sum(n.get((j, q, t), 0) for q in range(L + 1))
            if tot > f.K * y[j]:
                rep.add("(15)", f"facility {j}, t={t}: stock {tot} > K y = {f.K * y[j]}")
        for t in range(H):
            for q in range(L):
                lhs = sched.c.get((j, q, t), 0) + D.get((j, q, t), 0)
                if lhs > n.get((j, q, t), 0):
                    rep.add("(14)", f"facility {j}, q={q}, t={t}: c + D = {lhs} > n = {n.get((j, q, t), 0)}")
            lhs = S.get((j, t), 0) + D.get((j, L, t), 0)
            if lhs > n.get((j, L, t), 0):
                rep.add("(14)", f"facility {j}, full, t={t}: S + D = {lhs} > n_L = {n.get((j, L, t), 0)}")
        if f.swap and n.get((j, L, H), 0) < f.R_end * y[j]:
            rep.add("(17)", f"facility {j}: n_LH = {n.get((j, L, H), 0)} < R_end y = {f.R_end * y[j]}")
    for (j, q, t), val in s.items():
        if not inst.facility(j).swap:
            rep.add("(12)", f"swap recorded at non-swap facility {j}")
    full_end = sum(n.get((j, L, H), 0) for j in inst.N)
    target = inst.rho * sum(B.values())
    if full_end + _TOL < target:
        rep.add("(18)", f"sum_j n_jLH = {full_end} < rho sum B = {target}")

    # ------------------------------------------------------ (20), (21)
    charge_ids = set(inst.Cset)
    p_ch = disc.p_ch_kw
    group_load: Dict[Tuple[Any, int], float] = defaultdict(float)
    for f in inst.facilities:
        j = f.id
        for t in range(H):
            tot = sum(sched.c.get((j, q, t), 0) for q in range(L))
            if j not in charge_ids:
                if tot:
                    rep.add("(20)", f"facility {j} (not in C), t={t}: charging {tot}")
                continue
            if tot > C[j]:
                rep.add("(20)", f"facility {j}, t={t}: charging {tot} > C_j = {C[j]}")
            if p_ch * tot > f.P_kw * y[j] + _TOL:
                rep.add("(20)", f"facility {j}, t={t}: {p_ch * tot:.4g} kW > P_j y_j = {f.P_kw * y[j]}")
            if f.group is not None:
                group_load[(f.group, t)] += p_ch * tot
    for (gname, t), load in group_load.items():
        lim = inst.grid_limit(gname, t)
        if load > lim + _TOL:
            rep.add("(21)", f"group {gname}, t={t}: {load:.4g} kW > P_grid = {lim}")

    # ------------------------------------------------------------- (22)
    for j in inst.S:
        f = inst.facility(j)
        busy = [0] * H
        for arcs in chosen_by_bike.values():
            for a in arcs:
                if a.kind == "swap" and a.fac == j:
                    for tau in range(a.l, min(a.u, H)):
                        busy[tau] += 1
        for tau in range(H):
            if busy[tau] > f.M * y[j]:
                rep.add("(22)", f"facility {j}, slot {tau}: {busy[tau]} ongoing swaps > M y = {f.M * y[j]}")

    # ------------------------------------------------------------- (33)
    budget = _switch("budget", inst.budget)
    zeta = _switch("zeta", inst.zeta)
    if budget is not None:
        inv = sum(f.Fhat * y[f.id] + f.bhat * B[f.id] + f.chat * C[f.id] for f in inst.facilities)
        if inv > budget + _TOL:
            rep.add("(33)", f"investment {inv} > budget {budget}")
    if zeta is not None and inst.orders:
        served = sum(1 - int(sched.u.get(o.id, 0)) for o in inst.orders)
        if served + _TOL < zeta * len(inst.orders):
            rep.add("(33)", f"served {served} < zeta |I| = {zeta * len(inst.orders)}")

    # ------------------------------------------------------------- (24)
    m = in_transit(inst, sched.z)
    total_B = sum(B.values())
    identity_ok = True
    for t in range(H + 1):
        lhs = sum(n.get((j, q, t), 0) for j in inst.N for q in range(L + 1)) + m[t]
        if lhs != total_B:
            identity_ok = False
            rep.add("(24)", f"t={t}: sum_j N_jt + m_t = {lhs} != sum_j B_j = {total_B}")

    n_viol = sum(rec["count"] for rec in rep.fam.values())
    return {
        "ok": n_viol == 0,
        "n_violations": n_viol,
        "families": rep.fam,
        "identity_24_ok": identity_ok,
        "notes": notes,
        "n_source": n_src,
    }


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
def metrics(inst: Instance, lib: ArcLibrary, sched: Schedule) -> Dict[str, Any]:
    """Reporting quantities of E2 p.9 ("report service, response, lateness, bike
    distance, transfer loads, grid use and cost separately") plus inventory and
    queue diagnostics:

    ``served_share``, ``n_orders``, ``n_served``, ``n_unserved``,
    ``mean_response_h`` / ``max_response_h`` (``(u_a - r_i) Delta`` over served
    orders), ``mean_lateness_h`` / ``max_lateness_h`` / ``n_late``, ``bike_km``,
    ``n_swaps``, ``n_moves``, ``n_waits``, ``kwh_purchased`` (``eps/eta sum c``),
    ``kwh_stored`` (``eps sum c``), ``peak_kw_facility`` / ``peak_kw_group``,
    ``charge_steps_facility``, ``transfers_used`` (``sum h``), ``batteries_moved``
    (``sum z``), ``batteries_moved_by_level``, ``in_transit`` (``m_t``),
    ``full_stock`` (``n_jLt`` trajectory per facility), ``stock`` (``N_jt``),
    ``stockout_slots`` (slots with ``n_jLt = 0`` at a swap site), ``wait_before_swap``
    (wait slots at the swap node immediately before each swap, a queue proxy),
    ``mean_wait_before_swap``, ``swaps_per_facility``, ``end_full_total``,
    ``end_target_shortfall`` (18), ``per_platform`` served share, ``bike_end_levels``.
    """
    H, L = inst.H, inst.L
    disc = inst.disc
    y, B, C = facility_vars(inst, sched)
    resp: List[float] = []
    late: List[float] = []
    km = 0.0
    n_swaps = n_moves = n_waits = 0
    wait_before_swap: List[int] = []
    swaps_per_fac: Dict[Any, int] = defaultdict(int)
    platform_tot: Dict[Any, int] = defaultdict(int)
    platform_served: Dict[Any, int] = defaultdict(int)
    end_levels: Dict[Any, Optional[int]] = {}
    for o in inst.orders:
        platform_tot[o.platform] += 1
    for b in inst.bikes:
        path = sched.path(b.id, lib)
        run_wait = 0
        last_state = None
        for a in path:
            km += a.d_km
            if a.kind == "deliver":
                o = inst.order(a.order)
                resp.append((a.u - o.r) * disc.Delta_h)
                late.append(max(a.u - o.b, 0) * disc.Delta_h)
                platform_served[o.platform] += 1
                run_wait = 0
            elif a.kind == "swap":
                n_swaps += 1
                swaps_per_fac[a.fac] += 1
                wait_before_swap.append(run_wait)
                run_wait = 0
            elif a.kind == "move":
                n_moves += 1
                run_wait = 0
            elif a.kind == "wait":
                n_waits += 1
                run_wait += 1
            if a.kind != "term":
                last_state = a.dst
        end_levels[b.id] = None if last_state is None else last_state[2]
    n_orders = len(inst.orders)
    n_unserved = sum(int(sched.u.get(o.id, 0)) for o in inst.orders)
    n_served = len(resp)
    # charging
    kwh_steps = 0
    peak_fac: Dict[Any, float] = {}
    steps_fac: Dict[Any, int] = {}
    group_load: Dict[Tuple[Any, int], float] = defaultdict(float)
    for f in inst.facilities:
        if not f.charge:
            continue
        per_t = [sum(sched.c.get((f.id, q, t), 0) for q in range(L)) for t in range(H)]
        steps_fac[f.id] = sum(per_t)
        kwh_steps += sum(per_t)
        peak_fac[f.id] = disc.p_ch_kw * max(per_t) if per_t else 0.0
        if f.group is not None:
            for t in range(H):
                group_load[(f.group, t)] += disc.p_ch_kw * per_t[t]
    peak_group: Dict[Any, float] = defaultdict(float)
    for (gname, t), load in group_load.items():
        peak_group[gname] = max(peak_group[gname], load)
    # inventory
    n = sched.n
    if n is None:
        n = reconstruct_inventory(inst, lib, {k: sched.arc_ids(k) for k in sched.x}, sched.c, sched.z, B)
    full_stock = {f.id: [n.get((f.id, L, t), 0) for t in range(H + 1)] for f in inst.facilities}
    stock = {f.id: [sum(n.get((f.id, q, t), 0) for q in range(L + 1)) for t in range(H + 1)]
             for f in inst.facilities}
    stockout = {j: sum(1 for t in range(H) if full_stock[j][t] == 0) for j in inst.S}
    end_full = sum(full_stock[j][H] for j in inst.N)
    by_level = {q: sum(int(v) for (e, qq), v in sched.z.items() if qq == q) for q in range(L + 1)}
    return {
        "n_orders": n_orders, "n_served": n_served, "n_unserved": n_unserved,
        "served_share": (n_served / n_orders) if n_orders else 1.0,
        "mean_response_h": (sum(resp) / n_served) if n_served else 0.0,
        "max_response_h": max(resp) if resp else 0.0,
        "mean_lateness_h": (sum(late) / n_served) if n_served else 0.0,
        "max_lateness_h": max(late) if late else 0.0,
        "n_late": sum(1 for x in late if x > 0),
        "bike_km": km, "n_swaps": n_swaps, "n_moves": n_moves, "n_waits": n_waits,
        "swaps_per_facility": dict(swaps_per_fac),
        "wait_before_swap": wait_before_swap,
        "mean_wait_before_swap": (sum(wait_before_swap) / len(wait_before_swap)) if wait_before_swap else 0.0,
        "kwh_purchased": kwh_steps * disc.kwh_per_step,
        "kwh_stored": kwh_steps * disc.eps_kwh,
        "charge_steps_facility": steps_fac,
        "peak_kw_facility": peak_fac, "peak_kw_group": dict(peak_group),
        "transfers_used": sum(int(v) for v in sched.h.values()),
        "batteries_moved": sum(int(v) for v in sched.z.values()),
        "batteries_moved_by_level": by_level,
        "in_transit": in_transit(inst, sched.z),
        "full_stock": full_stock, "stock": stock, "stockout_slots": stockout,
        "end_full_total": end_full,
        "end_target_shortfall": max(0.0, inst.rho * sum(B.values()) - end_full),
        "per_platform": {p: {"orders": platform_tot[p], "served": platform_served.get(p, 0)}
                         for p in platform_tot},
        "bike_end_levels": end_levels,
        "facility_vars": {"y": y, "B": B, "C": C},
    }
