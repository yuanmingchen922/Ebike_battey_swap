"""Plain-data description of an E2 instance (Delivery Bike Operations and Battery
Rebalancing, ``notes/extracted/E2.txt``) plus JSON round-trip and validation.

Everything here is solver-independent: no gurobipy import.  The same ``Instance``
object is consumed by ``arcs.py`` (time-expanded bike networks), ``ilp.py``
(Gurobi model), ``baseline.py`` (event-driven policy) and ``evaluate.py``
(objective (26)-(32) and constraint checker).

Conventions (see ``notes/DECISIONS.md``):

* time boundaries ``t = 0..H``, operating slots ``T = {0..H-1}``, slot length
  ``Delta_h`` hours; battery levels ``q = 0..L`` with ``eps_kwh`` stored kWh per
  level (E2 Section 2);
* routes carry *raw physical* values ``T_h`` (hours), ``E_kwh`` (kWh) and
  ``d_km`` (km); the discrete ``tau_r`` and ``g_r`` of E2 (1) are derived by
  :meth:`Discretisation.tau` / :meth:`Discretisation.g` (ceil, ``tau >= 1`` for
  distinct nodes);
* a missing ``(u, v)`` key in ``Instance.routes`` means "no route offered";
  the empty route ``(v, v)`` always exists with zero time, energy, distance;
* facilities are keyed by their own id (``Facility.id``), *not* by the road node,
  so two facilities may share a node (E2 Section 1: roles may share a site);
* costs are in the toy unit system of E2 p.14 (kappa per km, pi per kWh, P_i per
  unserved order, w_i / v_i per hour, f_e per activation, v_reb per battery,
  F / bB / bC horizon-allocated setup costs).

Node ids may be strings, ints or tuples (GridNetwork uses ``(i, j)`` tuples);
tuples are encoded as JSON lists and decoded back to tuples.
"""
from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union

Node = Any            # hashable road-node id
NodePair = Tuple[Node, Node]

_CEIL_TOL = 1e-9

ENERGY_ROUNDING_OPTIONS = ("per_leg", "concat")

#: Arc-builder and model options understood by the package, with defaults.
#: ``arcs.py`` reads the first block, ``ilp.py`` the second (see CONTRACT.md).
DEFAULT_OPTIONS: Dict[str, Any] = {
    # ---- arc construction (arcs.py) --------------------------------------
    "energy_rounding": "per_leg",   # 'per_leg' (E2 (1)-(3)) or 'concat' (E6 sensitivity)
    "dominance": True,              # drop delivery arcs with t + tau_r < a_i (lossless)
    "swap_q_max": None,             # only swap arcs with return level q <= swap_q_max
    "dummy_terminal_cost": None,    # penalised dummy terminal arc (None = off)
    "reposition_targets": None,     # set of nodes that move arcs may end at (None = all)
    "tau_max": None,                # delivery arcs only from v with tau(v -> o_i) <= tau_max
    "start_slack": None,            # delivery arcs only with t <= b_i + start_slack
    "reachable_pruning": False,     # drop arcs whose tail is unreachable from s_k
    # ---- model switches (ilp.py) -----------------------------------------
    "no_transfers": False,          # h = z = 0
    "colocated": False,             # every facility gets both roles
    "fixed_facilities": None,       # None = fixed iff y/B/C are given in the data
    "lexicographic": False,         # min sum u_i first, then min cost
    "battery_swap_v1_bounds": False,  # add y_j <= B_j and C_j <= B_j (Sep-29 model)
}


def ceil_tol(x: float) -> int:
    """Integer ceiling that ignores floating-point noise below ``1e-9``.

    ``ceil_tol(1.0000000001) == 1`` and ``ceil_tol(1.5) == 2``; negative or zero
    input gives 0.  Used for E2 (1): ``tau_r = ceil(T_r/Delta)``, ``g_r = ceil(E_r/eps)``.
    """
    return max(0, int(math.ceil(x - _CEIL_TOL)))


# ---------------------------------------------------------------------------
# node encoding helpers (tuples <-> lists) for JSON
# ---------------------------------------------------------------------------
def _enc_node(v: Node) -> Any:
    if isinstance(v, tuple):
        return [_enc_node(x) for x in v]
    return v


def _dec_node(v: Any) -> Node:
    if isinstance(v, list):
        return tuple(_dec_node(x) for x in v)
    return v


_SET_TAG = "__set__"
_ITEMS_TAG = "__items__"


def _enc_option(name: str, val: Any) -> Any:
    """JSON-encode one ``Instance.options`` value (node-aware).

    ``reposition_targets`` keeps its plain-list encoding; any other ``set`` becomes
    ``{"__set__": [...]}`` and any dict with non-string keys (e.g. ``{node: zone}``)
    becomes ``{"__items__": [[key, value], ...]}``, tuple nodes encoded as lists.
    Every set (``reposition_targets`` included) is emitted in ``repr``-sorted
    order so that the JSON text is deterministic across processes (set iteration
    order depends on hash randomisation).  Everything else passes through unchanged.
    """
    if val is None:
        return None
    if name == "reposition_targets":
        return sorted((_enc_node(v) for v in val), key=repr)
    if isinstance(val, (set, frozenset)):
        return {_SET_TAG: sorted((_enc_node(v) for v in val), key=repr)}
    if isinstance(val, dict) and any(not isinstance(k, str) for k in val):
        return {_ITEMS_TAG: [[_enc_node(k), v] for k, v in val.items()]}
    return val


def _dec_option(name: str, val: Any) -> Any:
    """Inverse of :func:`_enc_option`."""
    if val is None:
        return None
    if name == "reposition_targets":
        return {_dec_node(v) for v in val}
    if isinstance(val, dict) and set(val) == {_SET_TAG}:
        return {_dec_node(v) for v in val[_SET_TAG]}
    if isinstance(val, dict) and set(val) == {_ITEMS_TAG}:
        return {_dec_node(k): v for k, v in val[_ITEMS_TAG]}
    return val


# ---------------------------------------------------------------------------
# dataclasses
# ---------------------------------------------------------------------------
@dataclass
class Discretisation:
    """Time/energy grid of E2 Section 2 and charging power (19).

    Attributes
    ----------
    Delta_h : hours per slot (``Delta``)
    H       : number of operating slots; boundaries are ``0..H``
    L       : full battery level
    eps_kwh : stored kWh per level (``eps``); capacity is ``L * eps``
    eta     : charging efficiency in ``(0, 1]``
    """
    Delta_h: float
    H: int
    L: int
    eps_kwh: float
    eta: float

    @property
    def p_ch_kw(self) -> float:
        """Input power per active charging battery, E2 (19): ``eps / (eta * Delta)`` kW."""
        return self.eps_kwh / (self.eta * self.Delta_h)

    @property
    def kwh_per_step(self) -> float:
        """Purchased kWh per charging step, E2 (28): ``eps / eta``."""
        return self.eps_kwh / self.eta

    def tau(self, T_h: float, distinct: bool = True) -> int:
        """Discrete duration of a route, E2 (1): ``ceil(T_h / Delta)``.

        For a route between distinct nodes the result is at least 1 (E2 p.3:
        "distinct-node travel takes at least one slot").  With ``distinct=False``
        (empty route or a concatenated route that may be empty) 0 is allowed.
        """
        tau = ceil_tol(T_h / self.Delta_h)
        return max(1, tau) if distinct else tau

    def g(self, E_kwh: float) -> int:
        """Discrete energy use of a route, E2 (1): ``ceil(E_kwh / eps) >= 0``."""
        return ceil_tol(E_kwh / self.eps_kwh)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Discretisation":
        return cls(**d)


@dataclass
class Route:
    """Raw physical data of one offered road route (E2 Section 3).

    ``T_h`` hours of travel, ``E_kwh`` energy drawn from the bike battery, ``d_km``
    distance.  Discrete ``tau_r``/``g_r`` are obtained through :class:`Discretisation`.
    """
    T_h: float
    E_kwh: float
    d_km: float


EMPTY_ROUTE = Route(0.0, 0.0, 0.0)


@dataclass
class Bike:
    """Delivery bike ``k`` with initial state ``(v0, 0, q0)`` (E2 Section 3)."""
    id: Any
    v0: Node
    q0: int


@dataclass
class Order:
    """Delivery order ``i`` (E2 Section 3, delivery action construction).

    ``o`` restaurant node, ``d`` customer node, ``r`` release, ``a`` food-ready
    (``a >= r``), ``b`` promise (soft, ``b >= r``), ``hp``/``hd`` pickup and
    handoff durations in slots (``hp + hd >= 1``), ``P`` unserved penalty,
    ``w``/``v`` response and lateness cost per hour (31), ``platform`` label
    ``phi(i)`` (reporting only).
    """
    id: Any
    o: Node
    d: Node
    r: int
    a: int
    b: int
    hp: int = 1
    hd: int = 1
    P: float = 100.0
    w: float = 12.0
    v: float = 24.0
    platform: Any = "default"


@dataclass
class Facility:
    """Physical facility ``j in N = S u C`` (E2 Sections 2, 4, 6, 7, 9).

    ``swap``/``charge`` flags give the roles (``j in S`` / ``j in C``).
    ``y``, ``B``, ``C`` are the facility decisions (7)-(8); ``None`` means
    *free* (decided by the ILP), an int means fixed data.  ``K`` storage
    capacity (15), ``Cbar`` charger bound (7), ``M`` swap positions and ``sigma``
    swap duration (22), ``P_kw`` site input-power limit (20), ``group`` supply
    group ``gamma(j)`` (21), ``F``/``bB``/``bC`` horizon-allocated setup costs
    (27), ``R_end`` local final full-battery target (17), ``Fhat``/``bhat``/``chat``
    investment coefficients of the optional budget (33).
    """
    id: Any
    node: Node
    swap: bool
    charge: bool
    y: Optional[int] = None
    B: Optional[int] = None
    C: Optional[int] = None
    K: int = 1
    Cbar: int = 0
    M: int = 1
    sigma: int = 1
    P_kw: float = 0.0
    group: Any = None
    F: float = 0.0
    bB: float = 0.0
    bC: float = 0.0
    R_end: int = 0
    Fhat: float = 0.0
    bhat: float = 0.0
    chat: float = 0.0


@dataclass
class Service:
    """Offered battery transport service ``e`` (E2 Section 5).

    ``o_fac``/``d_fac`` are *facility ids*, ``l``/``u`` departure/arrival
    boundaries with ``0 <= l < u <= H``, ``U`` load capacity, ``f`` activation
    cost and ``vreb`` per-battery cost (32); ``vreb`` is a scalar or a list of
    length ``L + 1`` indexed by charge level ``q``.
    """
    id: Any
    o_fac: Any
    d_fac: Any
    l: int
    u: int
    U: int
    f: float = 0.0
    vreb: Union[float, List[float]] = 0.0

    def vreb_q(self, q: int) -> float:
        """Per-battery transfer cost ``v^reb_eq`` for level ``q`` (32)."""
        if isinstance(self.vreb, (list, tuple)):
            return float(self.vreb[q])
        return float(self.vreb)


@dataclass
class Instance:
    """Complete E2 instance: discretisation, road nodes and routes, bikes, orders,
    facilities, transport services, grid limits, cost coefficients and options.

    ``pi`` is the electricity price per purchased kWh (28): a float (flat) or a
    dict ``{(facility_id, t): price}``.  ``P_grid`` maps supply group to a list of
    ``H`` residual kW limits (21).  ``kappa`` is the travel cost per km (29),
    ``q_res`` the terminal reserve (9), ``rho`` the network-wide recovery share
    (18), ``budget``/``zeta`` the optional (33) parameters.
    """
    disc: Discretisation
    nodes: List[Node]
    routes: Dict[NodePair, Route]
    bikes: List[Bike]
    orders: List[Order]
    facilities: List[Facility]
    services: List[Service]
    P_grid: Dict[Any, List[float]] = field(default_factory=dict)
    kappa: float = 1.0
    pi: Union[float, Dict[Tuple[Any, int], float]] = 2.0
    q_res: int = 0
    rho: float = 0.0
    budget: Optional[float] = None
    zeta: Optional[float] = None
    options: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    # indices (not part of equality / serialisation)
    _bike: Dict[Any, Bike] = field(init=False, repr=False, compare=False, default_factory=dict)
    _order: Dict[Any, Order] = field(init=False, repr=False, compare=False, default_factory=dict)
    _fac: Dict[Any, Facility] = field(init=False, repr=False, compare=False, default_factory=dict)
    _svc: Dict[Any, Service] = field(init=False, repr=False, compare=False, default_factory=dict)

    def __post_init__(self) -> None:
        self.reindex()

    # ----------------------------------------------------------------- index
    def reindex(self) -> None:
        """Rebuild the id -> object lookup tables (call after mutating the lists)."""
        self._bike = {b.id: b for b in self.bikes}
        self._order = {o.id: o for o in self.orders}
        self._fac = {f.id: f for f in self.facilities}
        self._svc = {s.id: s for s in self.services}
        full = dict(DEFAULT_OPTIONS)
        full.update(self.options)
        self.options = full

    def bike(self, k) -> Bike:
        return self._bike[k]

    def order(self, i) -> Order:
        return self._order[i]

    def facility(self, j) -> Facility:
        return self._fac[j]

    def service(self, e) -> Service:
        return self._svc[e]

    @property
    def H(self) -> int:
        return self.disc.H

    @property
    def L(self) -> int:
        return self.disc.L

    @property
    def S(self) -> List[Any]:
        """Swap-capable facility ids (``j in S``)."""
        return [f.id for f in self.facilities if f.swap]

    @property
    def Cset(self) -> List[Any]:
        """Charge-capable facility ids (``j in C``)."""
        return [f.id for f in self.facilities if f.charge]

    @property
    def N(self) -> List[Any]:
        return [f.id for f in self.facilities]

    @property
    def groups(self) -> List[Any]:
        """Supply groups ``g in G`` appearing on charge-capable facilities."""
        seen: List[Any] = []
        for f in self.facilities:
            if f.charge and f.group is not None and f.group not in seen:
                seen.append(f.group)
        return seen

    def option(self, name: str) -> Any:
        return self.options.get(name, DEFAULT_OPTIONS.get(name))

    # ---------------------------------------------------------------- routes
    def route(self, u: Node, v: Node) -> Optional[Route]:
        """Offered route ``u -> v`` (empty route for ``u == v``), or ``None``."""
        if u == v:
            return EMPTY_ROUTE
        return self.routes.get((u, v))

    def tau(self, u: Node, v: Node) -> Optional[int]:
        """``tau_r`` of (1) for the route ``u -> v`` (0 if ``u == v``), or ``None``."""
        if u == v:
            return 0
        r = self.routes.get((u, v))
        return None if r is None else self.disc.tau(r.T_h, distinct=True)

    def g(self, u: Node, v: Node) -> Optional[int]:
        """``g_r`` of (1) for the route ``u -> v`` (0 if ``u == v``), or ``None``."""
        if u == v:
            return 0
        r = self.routes.get((u, v))
        return None if r is None else self.disc.g(r.E_kwh)

    def d(self, u: Node, v: Node) -> Optional[float]:
        """Distance ``d_r`` in km for the route ``u -> v`` (0 if ``u == v``), or ``None``."""
        if u == v:
            return 0.0
        r = self.routes.get((u, v))
        return None if r is None else r.d_km

    # ----------------------------------------------------------------- costs
    def price(self, j: Any, t: int) -> float:
        """Electricity price ``pi_jt`` per purchased kWh (28)."""
        if isinstance(self.pi, dict):
            return float(self.pi.get((j, t), 0.0))
        return float(self.pi)

    def theta(self, i: Any, u_a: int) -> float:
        """Delivery-arc cost coefficient (31): ``w_i Delta (u_a - r_i) + v_i Delta [u_a - b_i]_+``."""
        o = self.order(i)
        D = self.disc.Delta_h
        return o.w * D * (u_a - o.r) + o.v * D * max(u_a - o.b, 0)

    def grid_limit(self, group: Any, t: int) -> float:
        """Residual supply limit ``P^grid_gt`` in kW (21); ``inf`` if the group has no limit."""
        lim = self.P_grid.get(group)
        if lim is None:
            return math.inf
        return float(lim[t])

    # ------------------------------------------------------------ validation
    def validate(self, raise_on_error: bool = True) -> List[str]:
        """Check the instance data against the E2 domain requirements.

        Returns the list of problems (empty if valid).  With ``raise_on_error``
        a non-empty list raises ``ValueError``.  Checked: Section 2 domains
        (``H >= 1``, ``L >= 1``, ``Delta, eps > 0``, ``0 < eta <= 1``), bike
        starts ``0 <= q0 <= L`` (Section 3), order times ``a_i, b_i >= r_i`` and
        ``hp + hd >= 1`` (Section 3), facility bounds of (7)-(8), (15), (22),
        service windows ``0 <= l_e < u_e <= H`` and ``U_e >= 1`` (Section 5),
        ``P_grid`` lengths (21), ``rho in [0, 1]``, ``q_res >= 0`` (9), (18),
        and option values.  A charge-capable facility with ``Cbar_j > 0`` but
        ``P_j = 0`` kW is legal yet can never charge ((20) forces ``c = 0``); it
        is reported with ``warnings.warn`` (``UserWarning``), not as an error.
        """
        p: List[str] = []
        d = self.disc
        if d.H < 1:
            p.append("H must be >= 1")
        if d.L < 1:
            p.append("L must be >= 1")
        if d.Delta_h <= 0 or d.eps_kwh <= 0:
            p.append("Delta_h and eps_kwh must be > 0")
        if not (0 < d.eta <= 1):
            p.append("eta must lie in (0, 1]")
        nodes = set(self.nodes)
        if len(nodes) != len(self.nodes):
            p.append("duplicate node ids")
        # routes
        for (u, v), r in self.routes.items():
            if u == v:
                p.append(f"route ({u},{v}): same-node routes are implicit, remove it")
            if u not in nodes or v not in nodes:
                p.append(f"route ({u},{v}) references unknown node")
            if r.T_h < 0 or r.E_kwh < 0 or r.d_km < 0:
                p.append(f"route ({u},{v}) has negative T/E/d")
        # bikes
        ids = [b.id for b in self.bikes]
        if len(set(ids)) != len(ids):
            p.append("duplicate bike ids")
        for b in self.bikes:
            if b.v0 not in nodes:
                p.append(f"bike {b.id}: start node {b.v0} unknown")
            if not (0 <= b.q0 <= d.L):
                p.append(f"bike {b.id}: q0={b.q0} outside 0..L")
        # orders
        ids = [o.id for o in self.orders]
        if len(set(ids)) != len(ids):
            p.append("duplicate order ids")
        for o in self.orders:
            if o.o not in nodes or o.d not in nodes:
                p.append(f"order {o.id}: unknown restaurant/customer node")
            if not (0 <= o.r <= d.H):
                p.append(f"order {o.id}: release r={o.r} outside 0..H")
            if o.a < o.r or o.b < o.r:
                p.append(f"order {o.id}: need a_i >= r_i and b_i >= r_i")
            if o.hp < 0 or o.hd < 0 or o.hp + o.hd < 1:
                p.append(f"order {o.id}: need hp, hd >= 0 and hp + hd >= 1")
            if o.P < 0 or o.w < 0 or o.v < 0:
                p.append(f"order {o.id}: negative cost coefficient")
            if o.o != o.d and (o.o, o.d) not in self.routes:
                p.append(f"order {o.id}: no route o_i -> d_i offered")
        # facilities
        ids = [f.id for f in self.facilities]
        if len(set(ids)) != len(ids):
            p.append("duplicate facility ids")
        for f in self.facilities:
            if f.node not in nodes:
                p.append(f"facility {f.id}: node {f.node} unknown")
            if not (f.swap or f.charge):
                p.append(f"facility {f.id}: must be swap- and/or charge-capable")
            if f.K < 1:
                p.append(f"facility {f.id}: K_j >= 1 required (15)")
            if f.Cbar < 0:
                p.append(f"facility {f.id}: Cbar_j >= 0 required (7)")
            if f.swap and (f.M < 1 or f.sigma < 1):
                p.append(f"facility {f.id}: M_j >= 1 and sigma_j >= 1 required (22)")
            if f.y is not None and f.y not in (0, 1):
                p.append(f"facility {f.id}: y_j must be 0/1 or None")
            if f.B is not None:
                if f.B < 0 or (f.y is not None and f.B > f.K * f.y):
                    p.append(f"facility {f.id}: B_j violates 0 <= B_j <= K_j y_j (7)")
            if f.C is not None:
                if f.C < 0 or (f.y is not None and f.C > min(f.Cbar, f.K) * f.y):
                    p.append(f"facility {f.id}: C_j violates 0 <= C_j <= min(Cbar_j,K_j) y_j (7)")
                if not f.charge and f.C != 0:
                    p.append(f"facility {f.id}: C_j = 0 required at non-charge site (8)")
                if f.charge and not f.swap and f.y is not None and f.C < f.y:
                    p.append(f"facility {f.id}: C_j >= y_j required for j in C\\S (8)")
            if f.charge and f.P_kw < 0:
                p.append(f"facility {f.id}: P_j >= 0 required (20)")
            if f.charge and f.Cbar > 0 and f.P_kw == 0:
                warnings.warn(f"facility {f.id}: charge-capable with Cbar_j = {f.Cbar} but "
                              f"P_j = 0 kW: (20) forbids all charging there (set P_kw)",
                              UserWarning, stacklevel=2)
            if f.R_end < 0:
                p.append(f"facility {f.id}: R_end >= 0 required (17)")
            if f.charge and f.group is not None and f.group not in self.P_grid:
                p.append(f"facility {f.id}: group {f.group} has no P_grid entry (21) "
                         f"(treated as unlimited)")
        fac_ids = set(ids)
        # services
        ids = [s.id for s in self.services]
        if len(set(ids)) != len(ids):
            p.append("duplicate service ids")
        for s in self.services:
            if s.o_fac not in fac_ids or s.d_fac not in fac_ids:
                p.append(f"service {s.id}: endpoints must be facility ids")
            if s.o_fac == s.d_fac:
                p.append(f"service {s.id}: origin and destination must differ")
            if not (0 <= s.l < s.u <= d.H):
                p.append(f"service {s.id}: need 0 <= l_e < u_e <= H")
            if s.U < 1:
                p.append(f"service {s.id}: U_e >= 1 required (10)")
            if isinstance(s.vreb, (list, tuple)) and len(s.vreb) != d.L + 1:
                p.append(f"service {s.id}: vreb list must have length L+1")
        # grid
        for gname, lim in self.P_grid.items():
            if len(lim) != d.H:
                p.append(f"P_grid[{gname}] must have length H={d.H}")
        # scalars
        if not (0 <= self.rho <= 1):
            p.append("rho must lie in [0, 1] (18)")
        if self.q_res < 0:
            p.append("q_res must be >= 0 (9)")
        if self.kappa < 0:
            p.append("kappa must be >= 0")
        if self.zeta is not None and not (0 <= self.zeta <= 1):
            p.append("zeta must lie in [0, 1] (33)")
        if self.option("energy_rounding") not in ENERGY_ROUNDING_OPTIONS:
            p.append(f"options.energy_rounding must be one of {ENERGY_ROUNDING_OPTIONS}")
        if raise_on_error and p:
            raise ValueError("invalid instance:\n  " + "\n  ".join(p))
        return p

    # ------------------------------------------------------------------ JSON
    def to_dict(self) -> dict:
        """JSON-compatible dict (tuple nodes -> lists, tuple-keyed dicts -> record lists)."""
        opts = {name: _enc_option(name, val) for name, val in self.options.items()}
        pi: Any
        if isinstance(self.pi, dict):
            pi = [[j, t, val] for (j, t), val in self.pi.items()]
        else:
            pi = self.pi
        return {
            "disc": self.disc.to_dict(),
            "nodes": [_enc_node(v) for v in self.nodes],
            "routes": [{"u": _enc_node(u), "v": _enc_node(v), **asdict(r)}
                       for (u, v), r in self.routes.items()],
            "bikes": [{"id": b.id, "v0": _enc_node(b.v0), "q0": b.q0} for b in self.bikes],
            "orders": [{**asdict(o), "o": _enc_node(o.o), "d": _enc_node(o.d)}
                       for o in self.orders],
            "facilities": [{**asdict(f), "node": _enc_node(f.node)} for f in self.facilities],
            "services": [asdict(s) for s in self.services],
            "P_grid": [{"group": gname, "limits": list(lim)} for gname, lim in self.P_grid.items()],
            "kappa": self.kappa,
            "pi": pi,
            "q_res": self.q_res,
            "rho": self.rho,
            "budget": self.budget,
            "zeta": self.zeta,
            "options": opts,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Instance":
        opts = {name: _dec_option(name, val) for name, val in d.get("options", {}).items()}
        pi_raw = d.get("pi", 2.0)
        pi: Any
        if isinstance(pi_raw, list):
            pi = {(rec[0], int(rec[1])): float(rec[2]) for rec in pi_raw}
        else:
            pi = float(pi_raw)
        routes = {}
        for rec in d["routes"]:
            routes[(_dec_node(rec["u"]), _dec_node(rec["v"]))] = Route(
                T_h=rec["T_h"], E_kwh=rec["E_kwh"], d_km=rec["d_km"])
        return cls(
            disc=Discretisation.from_dict(d["disc"]),
            nodes=[_dec_node(v) for v in d["nodes"]],
            routes=routes,
            bikes=[Bike(id=b["id"], v0=_dec_node(b["v0"]), q0=b["q0"]) for b in d["bikes"]],
            orders=[Order(**{**o, "o": _dec_node(o["o"]), "d": _dec_node(o["d"])})
                    for o in d["orders"]],
            facilities=[Facility(**{**f, "node": _dec_node(f["node"])}) for f in d["facilities"]],
            services=[Service(**s) for s in d["services"]],
            P_grid={rec["group"]: list(rec["limits"]) for rec in d.get("P_grid", [])},
            kappa=d.get("kappa", 1.0),
            pi=pi,
            q_res=d.get("q_res", 0),
            rho=d.get("rho", 0.0),
            budget=d.get("budget"),
            zeta=d.get("zeta"),
            options=opts,
            meta=d.get("meta", {}),
        )

    def to_json(self, **kw) -> str:
        kw.setdefault("indent", 1)
        return json.dumps(self.to_dict(), **kw)

    @classmethod
    def from_json(cls, s: str) -> "Instance":
        return cls.from_dict(json.loads(s))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "Instance":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_json(fh.read())

    # -------------------------------------------------------------- summary
    def summary(self) -> Dict[str, Any]:
        """Size summary: |K|, |I|, |V|, |N|, |S|, |C|, |E|, H, L, p_ch."""
        return {
            "bikes": len(self.bikes), "orders": len(self.orders), "nodes": len(self.nodes),
            "routes": len(self.routes), "facilities": len(self.facilities),
            "swap_sites": len(self.S), "charge_sites": len(self.Cset),
            "services": len(self.services), "H": self.H, "L": self.L,
            "Delta_h": self.disc.Delta_h, "eps_kwh": self.disc.eps_kwh,
            "p_ch_kw": self.disc.p_ch_kw,
        }


# ---------------------------------------------------------------------------
# reference instances
# ---------------------------------------------------------------------------
def toy_instance() -> Instance:
    """The E2 toy example, ``notes/extracted/E2_Example.txt`` pp.10-15 (optimum J = 12.5).

    Chain ``B - A - C``: A = restaurant + swap station, B = customer, C = charging
    station.  Each road edge takes one slot, one level and 1 km, so with
    ``T_h = d_km = delta * Delta`` and ``E_kwh = delta * eps`` the discrete values
    of (1) are ``tau = g = d = delta(v, w)``.  Two bikes at ``(A, 0, 2)``; orders
    1-3 A -> B with ``r = a = 0, 0, 4``, ``b = 2, 2, 6``, ``hp = 1``, ``hd = 0``;
    facility A swap-only (``y=1, B=0, C=0, K=1, M=1, sigma=1``), facility C
    charge-only (``y=1, B=1, C=1, Cbar=1, K=1, P=0.3 kW``, group ``g1`` with
    0.3 kW in every slot); services 1: C->A (1, 3, U=1) and 2: A->C (4, 6, U=1)
    with ``f = 1``, ``vreb = 0.2``; ``Delta = 1/12 h, H = 8, L = 2, eps = 0.02 kWh,
    eta = 0.8`` (``p_ch = 0.3 kW``); ``kappa = 1``, ``pi = 2``, ``q_res = 0``,
    ``rho = 1``, ``R_end = 0``; order costs ``P = 100``, ``w = 12/h``, ``v = 24/h``.
    """
    disc = Discretisation(Delta_h=1.0 / 12.0, H=8, L=2, eps_kwh=0.02, eta=0.8)
    nodes = ["A", "B", "C"]

    def delta(v: str, w: str) -> int:
        if v == w:
            return 0
        if {v, w} in ({"A", "B"}, {"A", "C"}):
            return 1
        return 2

    routes = {}
    for v in nodes:
        for w in nodes:
            if v != w:
                dl = delta(v, w)
                routes[(v, w)] = Route(T_h=dl * disc.Delta_h, E_kwh=dl * disc.eps_kwh, d_km=float(dl))
    bikes = [Bike(1, "A", 2), Bike(2, "A", 2)]
    orders = [
        Order(1, "A", "B", r=0, a=0, b=2, hp=1, hd=0, P=100.0, w=12.0, v=24.0, platform="p1"),
        Order(2, "A", "B", r=0, a=0, b=2, hp=1, hd=0, P=100.0, w=12.0, v=24.0, platform="p1"),
        Order(3, "A", "B", r=4, a=4, b=6, hp=1, hd=0, P=100.0, w=12.0, v=24.0, platform="p1"),
    ]
    facilities = [
        Facility("A", "A", swap=True, charge=False, y=1, B=0, C=0, K=1, Cbar=0, M=1, sigma=1,
                 P_kw=0.0, group=None, R_end=0),
        Facility("C", "C", swap=False, charge=True, y=1, B=1, C=1, K=1, Cbar=1, M=0, sigma=1,
                 P_kw=0.3, group="g1", R_end=0),
    ]
    services = [
        Service(1, "C", "A", l=1, u=3, U=1, f=1.0, vreb=0.2),
        Service(2, "A", "C", l=4, u=6, U=1, f=1.0, vreb=0.2),
    ]
    return Instance(
        disc=disc, nodes=nodes, routes=routes, bikes=bikes, orders=orders,
        facilities=facilities, services=services, P_grid={"g1": [0.3] * disc.H},
        kappa=1.0, pi=2.0, q_res=0, rho=1.0,
        options={"energy_rounding": "per_leg", "dominance": True},
        meta={"name": "E2 toy (pp.10-15)", "J_opt": 12.5},
    )


def battery_swap_p7_instance() -> Instance:
    """Single co-located station of ``Battery_Swap.pdf`` p.7: ``L = 2``, ``B = C = M = 1``,
    ``sigma = 1``, ``H = 4``, no orders, no transport.

    Two bikes start empty at the station node ``J``.  A swap at ``t = 0`` returns
    an empty battery that charges in slots 1 and 2 and is full at ``t = 3``, when
    the next swap can start (inventory rows ``(0,0,1), (1,0,0), (0,1,0), (0,0,1),
    (1,0,0)``).  Used as an inventory-recursion unit test for (13)-(14).
    """
    disc = Discretisation(Delta_h=1.0 / 12.0, H=4, L=2, eps_kwh=0.02, eta=0.8)
    fac = Facility("J", "J", swap=True, charge=True, y=1, B=1, C=1, K=1, Cbar=1, M=1,
                   sigma=1, P_kw=10.0, group="g1", R_end=0)
    return Instance(
        disc=disc, nodes=["J"], routes={}, bikes=[Bike(1, "J", 0), Bike(2, "J", 0)],
        orders=[], facilities=[fac], services=[], P_grid={"g1": [10.0] * disc.H},
        kappa=1.0, pi=2.0, q_res=0, rho=0.0,
        meta={"name": "Battery_Swap p.7 single station"},
    )
