"""Schedule container, objective (26)-(32), constraint checker (5)-(22) and
reporting metrics for E2 (``notes/extracted/E2.txt``; conventions in
``notes/DECISIONS.md``), plus the round-5 additions of ``notes/reading_to_model.md``:
the A3 metric pack (:func:`metric_pack`, ``metrics()['r5']``) and the M1 end-state
adjustment (:func:`end_state_adjustment`, ``cost()['C_end_adjust']``, never part of (26)).  Solver-independent: both the Gurobi solution
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
def cost(inst: Instance, lib: ArcLibrary, sched: Schedule, end_price: Optional[float] = None,
         bike_term: str = "positive") -> Dict[str, Any]:
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

    Plan item M1 adds three reporting lines that are NOT part of (26) and never
    enter ``total``: ``C_end_adjust`` (end-state energy adjustment of
    :func:`end_state_adjustment`, priced at ``pi_ref eps/eta`` per missing level;
    ``end_price`` / ``bike_term`` are passed through), ``C_end_adjust_parts``
    (station / bike split) and ``total_end_adjusted = total + C_end_adjust``, the
    figure to use when an ILP and a baseline schedule (or two boundary variants) are
    compared on equal end states.
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
    adj = end_state_adjustment(inst, lib, sched, end_price=end_price, bike_term=bike_term)
    return {
        "C_setup": C_setup, "C_elec": C_elec, "C_travel": C_travel,
        "C_orders": C_orders,
        "C_orders_parts": {"unserved": unserved, "response": response, "lateness": lateness},
        "C_reb": C_reb, "C_dummy_terminal": dummy, "total": total,
        # M1: reported next to (26), never part of it
        "C_end_adjust": adj["C_end_adjust"],
        "C_end_adjust_parts": {"station": adj["station_cost"], "bikes": adj["bike_cost"],
                               "price": adj["price"], "station_levels": adj["station_levels"],
                               "bike_levels": adj["bike_levels"]},
        "total_end_adjusted": total + adj["C_end_adjust"],
    }


# ---------------------------------------------------------------------------
# M1: end-state energy adjustment (reported, not part of (26))
# ---------------------------------------------------------------------------
#: Accepted values of the ``bike_term`` argument of :func:`end_state_adjustment`.
END_ADJUST_BIKE_TERMS = ("positive", "signed", "none")


def end_reference_price(inst: Instance, end_price: Optional[float] = None) -> float:
    """Reference price per purchased kWh of the M1 end-state adjustment.

    ``end_price`` if given, else ``inst.meta['end_price']`` if set, else the mean of
    the (28) prices ``pi_jt`` over ``j in C`` and ``t in T`` (equal to ``pi`` for a
    flat price, which every round-1..4 cost variant uses); an instance without a
    charge-capable facility falls back to the flat ``pi`` (or the mean of a price
    dict).  Plan item M1; E2 (28)."""
    if end_price is not None:
        return float(end_price)
    if inst.meta.get("end_price") is not None:
        return float(inst.meta["end_price"])
    cset = list(inst.Cset)
    if cset and inst.H > 0:
        vals = [inst.price(j, t) for j in cset for t in range(inst.H)]
        return float(sum(vals) / len(vals))
    if isinstance(inst.pi, dict):
        return float(sum(inst.pi.values()) / len(inst.pi)) if inst.pi else 0.0
    return float(inst.pi)


def bike_end_levels(inst: Instance, lib: ArcLibrary, sched: Schedule) -> Dict[Any, int]:
    """Battery level ``q_k(H)`` carried by each bike at the end of its path (the head of
    its last non-terminal arc; ``q0_k`` for a bike without arcs).  Used by the M1
    end-state adjustment and the A3 metric pack; E2 Section 3 states ``(v, t, q)``."""
    out: Dict[Any, int] = {}
    for b in inst.bikes:
        q = int(b.q0)
        for a in sched.path(b.id, lib):
            if a.kind != "term":
                q = int(a.dst[2])
        out[b.id] = q
    return out


def end_state_adjustment(inst: Instance, lib: ArcLibrary, sched: Schedule,
                         end_price: Optional[float] = None, bike_term: str = "positive",
                         n: Optional[Dict[Tuple[Any, int, int], int]] = None) -> Dict[str, Any]:
    """End-state energy adjustment of plan item M1 (``C_end_adjust``), NOT part of (26).

    Values the energy that is missing at the horizon relative to the start, at the
    purchase cost of recharging it, so that the ILP and the baseline (or two boundary
    variants of :func:`experiments.common.boundary_grid`) are compared on equal end
    states::

        C_end_adjust = pi_ref (eps / eta) [ sum_j sum_q (L - q) (n_jqH - n_jq0)
                                            + sum_k bike_term(q0_k - q_k(H)) ]

    * station term: level deficit of the facility stock at ``H`` minus that at
      ``t = 0`` (13), (16); with the all-full start (16) the second sum is zero and the
      term is the plan's ``sum_j sum_q (L - q) n_jqH``.  No cargo is in transit at ``H``
      (E2 p.6, (24)), so this covers every spare battery.
    * bike term: ``'positive'`` (default, the plan's formula) charges
      ``(q0_k - q_k(H))^+`` -- energy a bike ends with above its start level is not
      credited, because the next window starts the bikes at their given ``q0`` (E2
      p.9: bike batteries are given fleet resources); ``'signed'`` credits it
      (pure energy balance); ``'none'`` drops it.
    * ``pi_ref`` from :func:`end_reference_price`; ``eps / eta`` is the purchased
      kWh per level, as in (28).

    Zero whenever the end state equals the start state (every station at its initial
    stock, every bike at ``q0``).  Returns ``{'C_end_adjust', 'station_cost',
    'bike_cost', 'station_levels', 'bike_levels', 'bike_levels_signed', 'price',
    'kwh_per_level', 'bike_term'}`` (``*_levels`` in charge levels)."""
    if bike_term not in END_ADJUST_BIKE_TERMS:
        raise ValueError(f"bike_term must be one of {END_ADJUST_BIKE_TERMS}, got {bike_term!r}")
    H, L = inst.H, inst.L
    _, B, _ = facility_vars(inst, sched)
    if n is None:
        n = sched.n
    if n is None:
        n = reconstruct_inventory(inst, lib, {k: sched.arc_ids(k) for k in sched.x}, sched.c, sched.z, B)
    n0 = {(f.id, q): (int(B.get(f.id, 0)) if q == L else 0) for f in inst.facilities for q in range(L + 1)}
    station_levels = 0
    for f in inst.facilities:
        for q in range(L + 1):
            station_levels += (L - q) * (int(n.get((f.id, q, H), 0)) - n0[(f.id, q)])
    q_end = bike_end_levels(inst, lib, sched)
    signed = sum(int(b.q0) - q_end[b.id] for b in inst.bikes)
    if bike_term == "positive":
        bike_levels = sum(max(int(b.q0) - q_end[b.id], 0) for b in inst.bikes)
    elif bike_term == "signed":
        bike_levels = signed
    else:
        bike_levels = 0
    price = end_reference_price(inst, end_price)
    per_level = price * inst.disc.kwh_per_step
    return {
        "C_end_adjust": per_level * (station_levels + bike_levels),
        "station_cost": per_level * station_levels, "bike_cost": per_level * bike_levels,
        "station_levels": int(station_levels), "bike_levels": int(bike_levels),
        "bike_levels_signed": int(signed), "price": price,
        "kwh_per_level": inst.disc.kwh_per_step, "bike_term": bike_term,
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
    ``end_target_shortfall`` (18), ``per_platform`` served share, ``bike_end_levels``,
    and ``r5``: the round-5 metric pack of plan item A3 (:func:`metric_pack`).
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
    out_lock = _lockout_metrics(inst, sched, full_stock, stock, end_full)
    return {
        **({"lockout": out_lock} if out_lock is not None else {}),
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
        "r5": metric_pack(inst, lib, sched, n=n),
    }


def _lockout_metrics(inst: Instance, sched: Schedule, full_stock: Dict[Any, List[int]],
                     stock: Dict[Any, List[int]], end_full: int) -> Optional[Dict[str, Any]]:
    """Lock-out view of the stock metrics (plan item M9; ``meta['lockout']['sink']`` of
    ``generator.add_battery_lockout``).  E2 (18) as written sums over all facilities and so
    counts batteries locked at the dummy sink; the keys here exclude the sink and the forced
    services so that recovery and transfer metrics describe the real network.  ``None``
    when the instance has no lock-out sink (the ``metrics`` dict is then unchanged)."""
    lk = inst.meta.get("lockout") or {}
    sink = lk.get("sink")
    if sink is None or sink not in full_stock:
        return None
    forced = {rec["service"] for rec in (inst.options.get("forced_transfers") or [])}
    real_N = [j for j in inst.N if j != sink]
    end_full_real = sum(full_stock[j][inst.H] for j in real_N)
    B_real = sum(int(inst.facility(j).B or 0) for j in real_N)
    return {
        "sink": sink,
        "locked_batteries": stock[sink][inst.H],
        "locked_full_at_H": full_stock[sink][inst.H],
        "forced_executed": sum(int(sched.h.get(e, 0)) for e in forced),
        "forced_total": len(forced),
        "end_full_total_excl_sink": end_full_real,
        "end_share_excl_sink": (end_full_real / B_real) if B_real else None,
        "transfers_used_excl_forced": sum(int(v) for e, v in sched.h.items() if e not in forced),
        "batteries_moved_excl_forced": sum(int(v) for (e, _q), v in sched.z.items() if e not in forced),
        "end_full_total_incl_sink": end_full,
    }


# ---------------------------------------------------------------------------
# A3: round-5 metric pack (computed from any Schedule, no re-solve)
# ---------------------------------------------------------------------------
def metric_pack(inst: Instance, lib: ArcLibrary, sched: Schedule,
                n: Optional[Dict[Tuple[Any, int, int], int]] = None) -> Dict[str, Any]:
    """Round-5 metric pack of plan item A3, computed from any :class:`Schedule` (ILP or
    baseline) and the shared arc library only -- no solver, no policy flags, so the
    two methods are measured by exactly the same code.  E2 references: swaps (12),
    stock (13)/(16), availability (14), storage (15), charging (19)-(21), swap
    positions (22), objective prices (28).

    Station side (IJCAI-25 Def. 1-2):

    * ``sbur`` ``{j: S_j / B_j}`` -- station battery utilisation, full batteries issued
      over the horizon per initial spare, for open swap sites with ``B_j > 0``
      (``None`` when ``B_j = 0``); ``min_sbur`` over those sites;
      ``swaps_per_storage_slot`` ``{j: S_j / K_j}``.
    * ``bsr`` -- battery supply ratio, share of swaps the bike started without any
      wait slot at the station immediately before it ('met without wait');
      ``bsr_unblocked`` -- share of swaps none of whose preceding wait slots was
      *blocked*, i.e. a slot ``t`` with no issuable full battery
      (``n_jLt - S_jt - D_jLt <= 0``, (14)) or all positions busy (``>= M_j y_j``,
      (22)); ``n_blocked_wait_slots``, ``n_stockout_wait_slots``. ``None`` without swaps.
    * ``swaps_per_slot`` (length ``H``, swap starts per slot) and
      ``swaps_per_slot_facility``.
    * ``batteries_saved`` ``{j: k_j}`` and ``batteries_saved_total`` /
      ``batteries_saved_share`` -- the largest number of initial spares at ``j`` that
      could be removed at ``t = 0`` without changing any decision of the schedule:
      ``k_j = min(B_j, min_{t<H}(n_jLt - S_jt - D_jLt), n_jLH)`` (exact for (14)-(16);
      the end targets (17)-(18) are ignored -- they are reported separately).

    Rider side (IJCAI-15 Eq. 3/7, eBaaS Sec. 2.4):

    * ``station_time_min`` per swap = (wait slots at the station before the swap +
      swap duration ``u_a - l_a``) x Delta, in minutes; ``mean_station_time_min``,
      ``max_station_time_min``; ``mean_wait_min_per_swap``; ``mean_detour_km_per_swap``
      / ``mean_detour_min_per_swap`` (the reposition arc that brought the bike to the
      station, 0 when it arrived with a delivery or started there).
    * outage / stranding: ``reserve_breach_bikes`` (bikes whose path visits a level
      ``q < q_res``, (9)), ``stranded_bikes`` (no real terminal arc: missing or dummy,
      (9)), ``energy_refused_orders`` / ``energy_refused_bikes`` (an unserved order for
      which one of the bike's own delivery arcs leaves a node ``(v, t, q')`` while the
      bike waits idle at ``(v, t, q)`` with ``q < q'``: it was in place and free but
      lacked the energy (4); a proxy, limited to arcs present in the library),
      ``outage_bikes`` (union of the three) and ``outage_rate`` = ``|outage_bikes| /
      |K|`` (one window = one bike-window).
    * ``empty_km`` (reposition arcs), ``delivery_km``, ``empty_km_per_bike_hour`` =
      ``empty_km / (|K| H Delta)``, ``empty_km_share``.

    Grid side (ITSC-21 Table II, Fig. 3):

    * ``peak_kw_network`` = ``max_t p_ch sum_{j in C} sum_q c_jqt`` (19)-(21),
      ``peak_kw_facility``; ``kwh_by_price`` ``{price: kWh purchased}`` where a price
      period is the set of (site, slot) pairs with the same ``pi_jt`` (28) (one key for
      a flat price), ``peak_kw_by_price`` the peak network load within each period.
    * ``batteries_end_levels_missing`` and ``bike_end_levels`` (M1 end state).
    """
    H, L = inst.H, inst.L
    disc = inst.disc
    Delta = disc.Delta_h
    y, B, C = facility_vars(inst, sched)
    if n is None:
        n = sched.n
    if n is None:
        n = reconstruct_inventory(inst, lib, {k: sched.arc_ids(k) for k in sched.x}, sched.c, sched.z, B)
    s, S = swap_counts(inst, lib, {k: sched.arc_ids(k) for k in sched.x})
    D, _A = transfer_counts(inst, sched.z)
    swap_ids = [j for j in inst.S]
    # ----------------------------------------------- swap occupancy (22) and profile
    busy: Dict[Any, List[int]] = {j: [0] * H for j in swap_ids}
    swaps_slot = [0] * H
    swaps_slot_fac: Dict[Any, List[int]] = {j: [0] * H for j in swap_ids}
    swaps_fac: Dict[Any, int] = {j: 0 for j in swap_ids}
    paths = {b.id: sched.path(b.id, lib) for b in inst.bikes}
    for arcs in paths.values():
        for a in arcs:
            if a.kind != "swap":
                continue
            if 0 <= a.l < H:
                swaps_slot[a.l] += 1
                swaps_slot_fac.setdefault(a.fac, [0] * H)[a.l] += 1
            swaps_fac[a.fac] = swaps_fac.get(a.fac, 0) + 1
            for tau in range(max(a.l, 0), min(a.u, H)):
                busy.setdefault(a.fac, [0] * H)[tau] += 1

    def issuable(j: Any, t: int) -> int:
        return int(n.get((j, L, t), 0)) - int(S.get((j, t), 0)) - int(D.get((j, L, t), 0))

    # ------------------------------------------------------ unserved-order index (4)
    unserved = [o.id for o in inst.orders if int(sched.u.get(o.id, 0))]
    need: Dict[Tuple[Any, Any, int], Dict[Any, int]] = defaultdict(dict)
    for i in unserved:
        for a in lib.delivery_arcs(i):
            key = (a.k, a.src[0], a.src[1])
            prev = need[key].get(i)
            if prev is None or a.src[2] < prev:
                need[key][i] = int(a.src[2])
    # ---------------------------------------------------------------- per-bike pass
    station_time: List[float] = []
    wait_min: List[float] = []
    detour_km: List[float] = []
    detour_min: List[float] = []
    n_no_wait = n_unblocked = 0
    n_blocked_slots = n_stockout_slots = 0
    empty_km = deliv_km = 0.0
    reserve_breach: List[Any] = []
    stranded: List[Any] = []
    refused_orders: set = set()
    refused_bikes: List[Any] = []
    q_res = int(inst.q_res)
    for b in inst.bikes:
        k = b.id
        arcs = paths[k]
        min_q = int(b.q0)
        trailing_waits: List[int] = []
        prev_arc: Optional[Arc] = None
        has_real_term = False
        bike_refused = False
        for a in arcs:
            if a.kind == "term":
                if a.fac is not None:
                    has_real_term = True
                continue
            min_q = min(min_q, int(a.src[2]), int(a.dst[2]))
            if a.kind == "move":
                empty_km += a.d_km
            elif a.kind == "deliver":
                deliv_km += a.d_km
            if a.kind == "wait":
                if need:
                    for i, q_need in need.get((k, a.src[0], a.src[1]), {}).items():
                        if a.src[2] < q_need:
                            refused_orders.add(i)
                            bike_refused = True
                trailing_waits.append(a.l)
                continue
            if a.kind == "swap":
                j = a.fac
                f = inst.facility(j)
                n_wait = len(trailing_waits)
                blocked = 0
                for t in trailing_waits:
                    stock_out = issuable(j, t) <= 0
                    full_pos = busy.get(j, [0] * H)[t] >= f.M * y.get(j, 0) if 0 <= t < H else False
                    if stock_out:
                        n_stockout_slots += 1
                    if stock_out or full_pos:
                        blocked += 1
                n_blocked_slots += blocked
                n_no_wait += int(n_wait == 0)
                n_unblocked += int(blocked == 0)
                station_time.append((n_wait + (a.u - a.l)) * Delta * 60.0)
                wait_min.append(n_wait * Delta * 60.0)
                if prev_arc is not None and prev_arc.kind == "move":
                    detour_km.append(prev_arc.d_km)
                    detour_min.append((prev_arc.u - prev_arc.l) * Delta * 60.0)
                else:
                    detour_km.append(0.0)
                    detour_min.append(0.0)
            trailing_waits = []
            prev_arc = a
        if min_q < q_res:
            reserve_breach.append(k)
        if not has_real_term:
            stranded.append(k)
        if bike_refused:
            refused_bikes.append(k)
    flagged = set(reserve_breach) | set(stranded) | set(refused_bikes)
    outage = [b.id for b in inst.bikes if b.id in flagged]
    n_sw = len(station_time)
    # ------------------------------------------------------------------ station side
    sbur: Dict[Any, Optional[float]] = {}
    for j in swap_ids:
        if not y.get(j, 0):
            continue
        sbur[j] = (swaps_fac.get(j, 0) / B[j]) if B.get(j, 0) > 0 else None
    sbur_vals = [v for v in sbur.values() if v is not None]
    per_slot_k = {j: (swaps_fac.get(j, 0) / inst.facility(j).K) for j in swap_ids
                  if y.get(j, 0) and inst.facility(j).K > 0}
    saved: Dict[Any, int] = {}
    for f in inst.facilities:
        j = f.id
        if B.get(j, 0) <= 0:
            continue
        slack = min([issuable(j, t) for t in range(H)] + [int(n.get((j, L, H), 0)), int(B[j])])
        saved[j] = max(0, int(slack))
    total_B = sum(B.values())
    saved_total = sum(saved.values())
    # ---------------------------------------------------------------------- grid side
    p_ch = disc.p_ch_kw
    charge_ids = set(inst.Cset)
    load_t = [0.0] * H
    kwh_price: Dict[str, float] = defaultdict(float)
    load_price: Dict[str, List[float]] = {}
    peak_fac: Dict[Any, float] = {}
    fac_t: Dict[Any, List[int]] = {j: [0] * H for j in charge_ids}
    for (j, q, t), val in sched.c.items():
        if not val or j not in charge_ids or not (0 <= q < L) or not (0 <= t < H):
            continue
        fac_t[j][t] += int(val)
        load_t[t] += p_ch * val
        key = f"{inst.price(j, t):g}"
        kwh_price[key] += disc.kwh_per_step * val
        load_price.setdefault(key, [0.0] * H)[t] += p_ch * val
    for j, per_t in fac_t.items():
        peak_fac[j] = p_ch * max(per_t) if per_t else 0.0
    adj = end_state_adjustment(inst, lib, sched, n=n)
    q_end = bike_end_levels(inst, lib, sched)
    km_hours = len(inst.bikes) * H * Delta

    def mean(v: List[float]) -> Optional[float]:
        return (sum(v) / len(v)) if v else None

    return {
        # station side
        "sbur": sbur, "min_sbur": (min(sbur_vals) if sbur_vals else None),
        "mean_sbur": mean(sbur_vals),
        "swaps_per_storage_slot": per_slot_k,
        "n_swaps": n_sw,
        "bsr": (n_no_wait / n_sw) if n_sw else None,
        "bsr_unblocked": (n_unblocked / n_sw) if n_sw else None,
        "n_blocked_wait_slots": n_blocked_slots, "n_stockout_wait_slots": n_stockout_slots,
        "swaps_per_slot": swaps_slot, "swaps_per_slot_facility": swaps_slot_fac,
        "peak_swaps_per_slot": max(swaps_slot) if swaps_slot else 0,
        "batteries_saved": saved, "batteries_saved_total": saved_total,
        "batteries_saved_share": (saved_total / total_B) if total_B else None,
        # rider side
        "station_time_min": station_time,
        "mean_station_time_min": mean(station_time),
        "max_station_time_min": max(station_time) if station_time else None,
        "mean_wait_min_per_swap": mean(wait_min),
        "mean_detour_km_per_swap": mean(detour_km),
        "mean_detour_min_per_swap": mean(detour_min),
        "reserve_breach_bikes": reserve_breach, "stranded_bikes": stranded,
        "energy_refused_orders": sorted(refused_orders, key=str), "energy_refused_bikes": refused_bikes,
        "n_energy_refused_orders": len(refused_orders),
        "outage_bikes": outage, "n_outage_bikes": len(outage),
        "outage_rate": (len(outage) / len(inst.bikes)) if inst.bikes else 0.0,
        "empty_km": empty_km, "delivery_km": deliv_km,
        "empty_km_per_bike_hour": (empty_km / km_hours) if km_hours > 0 else 0.0,
        "empty_km_share": (empty_km / (empty_km + deliv_km)) if (empty_km + deliv_km) > 0 else 0.0,
        # grid side
        "peak_kw_network": max(load_t) if load_t else 0.0,
        "peak_kw_facility": peak_fac,
        "kwh_by_price": dict(kwh_price),
        "peak_kw_by_price": {key: max(v) for key, v in load_price.items()},
        "kwh_purchased": sum(kwh_price.values()),
        # M1 end state
        "station_end_levels_missing": adj["station_levels"],
        "bike_end_levels_missing": adj["bike_levels"],
        "bike_end_levels": q_end,
        "C_end_adjust": adj["C_end_adjust"],
    }


#: Scalar entries of :func:`metric_pack` copied into flat experiment records
#: (``experiments.common.flatten_r5``).
R5_SCALAR_KEYS = (
    "min_sbur", "mean_sbur", "n_swaps", "bsr", "bsr_unblocked", "n_blocked_wait_slots",
    "n_stockout_wait_slots", "peak_swaps_per_slot", "batteries_saved_total", "batteries_saved_share",
    "mean_station_time_min", "max_station_time_min", "mean_wait_min_per_swap",
    "mean_detour_km_per_swap", "mean_detour_min_per_swap", "n_energy_refused_orders",
    "n_outage_bikes", "outage_rate", "empty_km", "delivery_km", "empty_km_per_bike_hour",
    "empty_km_share", "peak_kw_network", "kwh_purchased", "station_end_levels_missing",
    "bike_end_levels_missing", "C_end_adjust",
)
