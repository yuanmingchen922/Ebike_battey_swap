"""Time-expanded action networks of the delivery bikes (E2 Section 3, (1)-(4), (9);
toy construction E2_Example p.11; conventions in ``notes/DECISIONS.md``).

States are ``(v, t, q)`` with ``v`` a road node, ``t = 0..H`` a boundary and
``q = 0..L`` a battery level.  Every bike ``k`` has its own copy of the arcs
(``Arc.k``), a source ``s_k = (v0_k, 0, q0_k)`` and one sink ``('sink',)``.

Arc kinds and transitions
-------------------------
wait     ``(v,t,q) -> (v,t+1,q)``, ``t < H``, zero energy/distance.
move     ``(v,t,q) -> (w, t+tau_r, q-g_r)`` for an offered route ``r: v -> w``,
         ``v != w``, iff ``q >= g_r`` and ``t + tau_r <= H``; ``d_a = d_r``.
deliver  ``(v,t,q) -> (d_i, u_a, q-g_a)`` for order ``i`` with routes
         ``r: v -> o_i`` and ``r': o_i -> d_i`` (2)-(3): ``u_a = max(t+tau_r, a_i)
         + hp_i + tau_r' + hd_i``, ``g_a = g_r + g_r'`` (``energy_rounding='per_leg'``)
         or ``ceil((E_r+E_r')/eps)`` (``'concat'``); created iff (4) ``t >= r_i``,
         ``q >= g_a``, ``u_a <= H``; ``theta`` from (31); ``d_a = d_r + d_r'``.
swap     ``(v_j,t,q) -> (v_j, t+sigma_j, L)`` for ``j in S``, ``q < L``,
         ``t + sigma_j <= H`` (one arc per *facility*, keyed by ``Arc.fac``).
term     ``(v,H,q) -> ('sink',)`` labelled ``fac = j in S`` iff (9)
         ``q >= gbar(v,j) + q_res``; the ILP adds ``x_ka <= y_j``.  With option
         ``dummy_terminal_cost`` an extra penalised terminal arc with ``fac=None``
         and ``theta = dummy_terminal_cost`` leaves every ``(v,H,q)``.

Arc ids are global integers ``0..n_arcs-1`` (bike after bike, kinds interleaved);
``ArcLibrary.arc(id)`` returns the object.  All arcs except ``term`` strictly
increase ``t``, so the per-bike graph is acyclic and a unit flow satisfying (5)
is a single path.

Pruning options (all read from ``Instance.options``, overridable by keyword;
defaults OFF except ``dominance``):

* ``dominance`` (default ON, lossless): drop delivery arcs with ``t + tau_r < a_i``;
  the later start ``max(r_i, a_i - tau_r)`` reached by waiting has the same
  ``u_a``, ``g_a``, ``theta``.  The library built with ``dominance=False`` is
  always a superset of the one built with ``dominance=True`` (same other options).
  Note: combined with ``start_slack`` the replacement start ``a_i - tau_r`` may
  itself be cut (``a_i - tau_r > b_i + start_slack``); the combination is then
  lossier than either option alone.
* ``reposition_targets``: move arcs only into this node set.
* ``reposition_target_radius``: ``{node: blocks}`` (R7 siting scale-up, approach radius):
  a move arc INTO one of these nodes is created only from a tail node within that many
  grid blocks (Manhattan distance of ``(ix, iy)`` nodes; scalar nodes: absolute
  difference).  Nodes absent from the dict (depots, non-candidate targets) are not
  restricted.  ``None`` (default) = no restriction, byte-identical libraries.
* ``reposition_radius_exempt_states``: ``[(node, q), ...]`` tail states whose move arcs are
  NOT subject to ``reposition_target_radius`` (R7, 2026-10-21: the start states ``(v0_k, q0_k)``
  of the scenario's bikes, at every ``t``, so that a bike's first approach to a far site is a
  single move arc; without it a bike that starts far from a one-site layout with little charge
  can lose the only terminal-feasible path to two-hop rounding).  The set is bike-independent
  (one set per scenario), so the template and every pricing library apply it identically.  A
  JSON round-trip (node tuples as lists) is tolerated.  Only read when the radius is set.
* ``tau_max``: delivery arcs only from ``v`` with ``tau(v -> o_i) <= tau_max``.
* ``start_slack``: delivery arcs only with ``t <= b_i + start_slack``.
* ``reachable_pruning``: drop arcs whose tail state is unreachable from ``s_k``.
* ``swap_q_max``: swap arcs only for return level ``q <= swap_q_max``.

The builder always runs a forward reachability pass from ``s_k`` and checks that
at least one real terminal arc is reachable (otherwise bike ``k`` can never
satisfy (5)+(9)); ``strict=True`` raises :class:`InfeasibleInstanceError`,
``strict=False`` records the bikes in ``ArcLibrary.infeasible_bikes``.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from .or_instance import Instance, Node, DEFAULT_OPTIONS

State = Tuple[Any, int, int]
SINK: Tuple[str] = ("sink",)
KINDS = ("wait", "move", "deliver", "swap", "term")


def node_blocks(a: Any, b: Any) -> int:
    """Grid distance in blocks of two nodes: Manhattan distance of ``(ix, iy)`` tuples,
    absolute difference of scalar (toy) node ids."""
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return sum(abs(int(x) - int(y)) for x, y in zip(a, b))
    return abs(int(a) - int(b))


def radius_exempt_states(raw: Any) -> Dict[Node, Tuple[int, ...]]:
    """``{node: sorted q levels}`` of the ``reposition_radius_exempt_states`` option; list nodes
    (a JSON round-trip of tuple nodes) are turned back into tuples."""
    out: Dict[Node, Set[int]] = {}
    for item in raw or ():
        v, q = item
        if isinstance(v, list):
            v = tuple(v)
        out.setdefault(v, set()).add(int(q))
    return {v: tuple(sorted(qs)) for v, qs in out.items()}


class InfeasibleInstanceError(ValueError):
    """Raised when some bike has no reachable terminal arc (5)+(9) cannot hold."""


@dataclass(slots=True)
class Arc:
    """One candidate action of bike ``k``.

    ``src``/``dst`` are states ``(v, t, q)`` (``dst = ('sink',)`` for ``term``),
    ``l``/``u`` the start/end boundaries (``l = u = H`` for ``term``), ``d_km``
    the distance ``d_a`` priced by (29), ``g`` the energy consumed (``src_q -
    dst_q`` for wait/move/deliver; 0 for swap and term), ``order`` the order id
    of a deliver arc, ``fac`` the facility id of a swap or term arc, ``theta``
    the fixed cost coefficient (31) of a deliver arc (or the dummy-terminal
    penalty).
    """
    id: int
    k: Any
    kind: str
    src: Tuple
    dst: Tuple
    l: int
    u: int
    d_km: float
    g: int
    order: Any = None
    fac: Any = None
    theta: float = 0.0


def arc_key(a: Arc) -> Tuple[str, Tuple, Tuple, Any, Any]:
    """Bike-independent identity ``(kind, src, dst, order, fac)`` of an arc (plan item
    O1, E2 (5), (9)).

    Within one bike's network the key is unique: wait/move arcs are fixed by their
    end states (one offered route per ordered node pair), deliver arcs by order and
    start state, swap arcs by facility and start state, real terminal arcs by
    ``(v, H, q)`` and facility, the dummy terminal arc by ``fac = None``.  All other
    fields (``l, u, d_km, g, theta``) are functions of the key, so two bikes'
    copies of the same key describe the same action; ``aggregate.AggregatedNetwork``
    merges them into one integer flow variable."""
    return (a.kind, a.src, a.dst, a.order, a.fac)


# ---------------------------------------------------------------------------
# minimum discrete energy to each swap facility (for terminal arcs, (9))
# ---------------------------------------------------------------------------
def compute_gbar(inst: Instance) -> Dict[Tuple[Node, Any], float]:
    """``gbar(v, j)`` of (9): minimum discrete road energy from node ``v`` to the
    node of swap facility ``j``, by Dijkstra over the route library with weights
    ``g_r`` (levels); ``inf`` if unreachable.  Returns ``{(v, j): levels}`` for
    every node ``v`` and every ``j in S``.

    Runs one Dijkstra per swap facility on the *reversed* route graph (edge
    ``w -> v`` with weight ``g(v -> w)``) so that a route ``v -> w`` can be used
    in the forward direction only if it is offered.
    """
    rev: Dict[Node, List[Tuple[Node, int]]] = defaultdict(list)
    for (u, v) in inst.routes:
        rev[v].append((u, inst.g(u, v)))
    out: Dict[Tuple[Node, Any], float] = {}
    for j in inst.S:
        target = inst.facility(j).node
        dist: Dict[Node, float] = {n: math.inf for n in inst.nodes}
        dist[target] = 0
        heap = [(0, 0, target)]
        counter = 1
        while heap:
            dv, _, v = heapq.heappop(heap)
            if dv > dist[v]:
                continue
            for u, w in rev.get(v, ()):
                nd = dv + w
                if nd < dist.get(u, math.inf):
                    dist[u] = nd
                    heapq.heappush(heap, (nd, counter, u))
                    counter += 1
        for v in inst.nodes:
            out[(v, j)] = dist.get(v, math.inf)
    return out


# ---------------------------------------------------------------------------
# library
# ---------------------------------------------------------------------------
class ArcLibrary:
    """Arc sets ``A_k`` of all bikes with lookup indices.

    Build with :func:`build_arcs` (or ``ArcLibrary.build``).  Public attributes:
    ``inst``, ``options`` (effective builder options), ``gbar``, ``arcs``
    (list indexed by id), ``infeasible_bikes`` (bikes without a reachable real
    terminal arc), ``has_dummy_terminal``.
    """

    def __init__(self, inst: Instance, options: Dict[str, Any],
                 gbar: Dict[Tuple[Node, Any], float]) -> None:
        self.inst = inst
        self.options = options
        self.gbar = gbar
        self.arcs: List[Arc] = []
        self.infeasible_bikes: List[Any] = []
        self.has_dummy_terminal = options.get("dummy_terminal_cost") is not None
        self._by_bike: Dict[Any, List[int]] = defaultdict(list)
        self._out: Dict[Any, Dict[Tuple, List[int]]] = defaultdict(lambda: defaultdict(list))
        self._in: Dict[Any, Dict[Tuple, List[int]]] = defaultdict(lambda: defaultdict(list))
        self._deliv: Dict[Any, List[int]] = defaultdict(list)
        self._swap: Dict[Any, List[int]] = defaultdict(list)
        self._swap_at: Dict[Tuple[Any, int, int], List[int]] = defaultdict(list)
        self._term: Dict[Any, List[int]] = defaultdict(list)
        self._kind: Dict[str, List[int]] = defaultdict(list)

    # ------------------------------------------------------------ building
    @classmethod
    def build(cls, inst: Instance, strict: bool = True, **overrides: Any) -> "ArcLibrary":
        """Alias of :func:`build_arcs`."""
        return build_arcs(inst, strict=strict, **overrides)

    def _add(self, arc: Arc) -> None:
        self.arcs.append(arc)
        self._by_bike[arc.k].append(arc.id)
        self._out[arc.k][arc.src].append(arc.id)
        self._in[arc.k][arc.dst].append(arc.id)
        self._kind[arc.kind].append(arc.id)
        if arc.kind == "deliver":
            self._deliv[arc.order].append(arc.id)
        elif arc.kind == "swap":
            self._swap[arc.fac].append(arc.id)
            self._swap_at[(arc.fac, arc.l, arc.src[2])].append(arc.id)
        elif arc.kind == "term":
            self._term[arc.k].append(arc.id)

    # ------------------------------------------------------------- lookups
    def arc(self, arc_id: int) -> Arc:
        return self.arcs[arc_id]

    def __len__(self) -> int:
        return len(self.arcs)

    def source(self, k: Any) -> State:
        """``s_k = (v0_k, 0, q0_k)`` (E2 Section 3)."""
        b = self.inst.bike(k)
        return (b.v0, 0, b.q0)

    @property
    def sink(self) -> Tuple[str]:
        return SINK

    def bikes(self) -> List[Any]:
        return [b.id for b in self.inst.bikes]

    def arcs_of(self, k: Any) -> List[Arc]:
        """All arcs ``A_k`` of bike ``k``."""
        return [self.arcs[i] for i in self._by_bike.get(k, ())]

    def ids_of(self, k: Any) -> List[int]:
        return list(self._by_bike.get(k, ()))

    def states(self, k: Any) -> Set[Tuple]:
        """All network nodes of bike ``k`` (states appearing as tail or head, plus
        the sink); the flow conservation (5) is written once per element."""
        s: Set[Tuple] = set(self._out[k].keys())
        s.update(self._in[k].keys())
        s.add(self.source(k))
        s.add(SINK)
        return s

    def out_arcs(self, k: Any, node: Tuple) -> List[Arc]:
        """``delta^+_k(node)``: arcs of bike ``k`` leaving ``node`` (5)."""
        return [self.arcs[i] for i in self._out[k].get(node, ())]

    def in_arcs(self, k: Any, node: Tuple) -> List[Arc]:
        """``delta^-_k(node)``: arcs of bike ``k`` entering ``node`` (5)."""
        return [self.arcs[i] for i in self._in[k].get(node, ())]

    def delivery_arcs(self, i: Any, k: Any = None) -> List[Arc]:
        """``A^ord_ki`` over all bikes (or bike ``k``) for order ``i`` (6), (30)."""
        arcs = [self.arcs[a] for a in self._deliv.get(i, ())]
        return arcs if k is None else [a for a in arcs if a.k == k]

    def swap_arcs(self, j: Any, k: Any = None) -> List[Arc]:
        """``A^sw_k(j)`` over all bikes (or bike ``k``) at swap facility ``j`` (22)."""
        arcs = [self.arcs[a] for a in self._swap.get(j, ())]
        return arcs if k is None else [a for a in arcs if a.k == k]

    def swap_arcs_at(self, j: Any, t: int, q: int, k: Any = None) -> List[Arc]:
        """``A^sw_k(j, t, q)``: swap arcs at ``j`` starting at ``t`` with return level ``q`` (12)."""
        arcs = [self.arcs[a] for a in self._swap_at.get((j, t, q), ())]
        return arcs if k is None else [a for a in arcs if a.k == k]

    def terminal_arcs(self, k: Any = None) -> List[Arc]:
        """Terminal arcs (9) of bike ``k`` (all bikes if ``None``), dummy ones included."""
        if k is None:
            return [self.arcs[a] for a in self._kind.get("term", ())]
        return [self.arcs[a] for a in self._term.get(k, ())]

    def arcs_of_kind(self, kind: str, k: Any = None) -> List[Arc]:
        arcs = [self.arcs[a] for a in self._kind.get(kind, ())]
        return arcs if k is None else [a for a in arcs if a.k == k]

    def find(self, k: Any, kind: str, src: Tuple, order: Any = None, fac: Any = None,
             dst: Optional[Tuple] = None) -> Optional[Arc]:
        """First arc of bike ``k`` of the given ``kind`` leaving state ``src`` that
        matches the optional ``order`` / ``fac`` / ``dst`` labels, or ``None`` if the
        library does not contain it (e.g. pruned).  Used by the baseline policy so
        that it never takes an action the ILP cannot take."""
        for i in self._out[k].get(src, ()):
            a = self.arcs[i]
            if a.kind != kind:
                continue
            if order is not None and a.order != order:
                continue
            if fac is not None and a.fac != fac:
                continue
            if dst is not None and a.dst != dst:
                continue
            return a
        return None

    # ------------------------------------------------------------- summary
    def counts(self, k: Any = None) -> Dict[str, int]:
        """Arc counts per kind (for bike ``k`` or all bikes), plus ``total``."""
        ids = self._by_bike.get(k, ()) if k is not None else range(len(self.arcs))
        c = {kind: 0 for kind in KINDS}
        for i in ids:
            c[self.arcs[i].kind] += 1
        c["total"] = sum(c[kind] for kind in KINDS)
        return c

    def summary(self) -> Dict[str, Any]:
        """Counts of arcs per kind in total and per bike, number of bikes, states,
        options in effect and infeasible bikes."""
        return {
            "n_bikes": len(self.inst.bikes),
            "n_arcs": len(self.arcs),
            "per_kind": self.counts(),
            "per_bike": {k: self.counts(k) for k in self.bikes()},
            "n_states": {k: len(self.states(k)) for k in self.bikes()},
            "infeasible_bikes": list(self.infeasible_bikes),
            "options": {key: (sorted(map(str, val)) if isinstance(val, set) else val)
                        for key, val in self.options.items()},
        }


# ---------------------------------------------------------------------------
# template (bike-independent) arc specifications
# ---------------------------------------------------------------------------
# spec = (kind, src, dst, l, u, d_km, g, order, fac, theta)
_Spec = Tuple[str, Tuple, Tuple, int, int, float, int, Any, Any, float]


def _delivery_specs(inst: Instance, opts: Dict[str, Any]) -> List[_Spec]:
    """Delivery arcs per (2)-(4) and (31) for every order, start node, start time
    and level; honours ``energy_rounding``, ``dominance``, ``tau_max``, ``start_slack``."""
    disc = inst.disc
    H, L = disc.H, disc.L
    rounding = opts.get("energy_rounding", "per_leg")
    dominance = bool(opts.get("dominance", True))
    tau_max = opts.get("tau_max")
    slack = opts.get("start_slack")
    specs: List[_Spec] = []
    for o in inst.orders:
        r2 = inst.route(o.o, o.d)
        if r2 is None:
            continue  # no route restaurant -> customer: order can only be unserved
        tau2 = disc.tau(r2.T_h, distinct=o.o != o.d)
        g2 = disc.g(r2.E_kwh)
        t_hi = H if slack is None else min(H, o.b + int(slack))
        for v in inst.nodes:
            r1 = inst.route(v, o.o)
            if r1 is None:
                continue
            tau1 = disc.tau(r1.T_h, distinct=v != o.o)
            if tau_max is not None and tau1 > tau_max:
                continue
            g1 = disc.g(r1.E_kwh)
            d_a = r1.d_km + r2.d_km
            if rounding == "concat":
                g_cat = disc.g(r1.E_kwh + r2.E_kwh)
                tau_cat = disc.tau(r1.T_h + r2.T_h, distinct=(v != o.o or o.o != o.d))
            for t in range(o.r, t_hi + 1):
                arrive = t + tau1
                if dominance and arrive < o.a:
                    continue  # waiting at v then starting at a_i - tau1 dominates
                if rounding == "concat":
                    g_a = g_cat
                    if arrive >= o.a:
                        u_a = t + tau_cat + o.hp + o.hd
                    else:  # legs separated by the food-ready wait
                        u_a = o.a + o.hp + tau2 + o.hd
                else:
                    g_a = g1 + g2
                    u_a = max(arrive, o.a) + o.hp + tau2 + o.hd
                if u_a > H:
                    # For t with arrive >= a_i, u_a is non-decreasing in t, so no later
                    # start fits either.  For arrive < a_i (only reached with
                    # dominance OFF) u_a = a_i + hp + tau_r' + hd is constant and, with
                    # 'concat' rounding, may exceed the u_a of the later starts
                    # (tau_cat <= tau_r + tau_r'), so those must still be examined.
                    if arrive >= o.a:
                        break
                    continue
                theta = inst.theta(o.id, u_a)
                for q in range(g_a, L + 1):
                    specs.append(("deliver", (v, t, q), (o.d, u_a, q - g_a), t, u_a,
                                  d_a, g_a, o.id, None, theta))
    return specs


def _template_specs(inst: Instance, opts: Dict[str, Any],
                    gbar: Dict[Tuple[Node, Any], float]) -> List[_Spec]:
    """All bike-independent arc specifications (wait, move, deliver, swap, term)."""
    disc = inst.disc
    H, L = disc.H, disc.L
    specs: List[_Spec] = []
    # wait
    for v in inst.nodes:
        for t in range(H):
            for q in range(L + 1):
                specs.append(("wait", (v, t, q), (v, t + 1, q), t, t + 1, 0.0, 0, None, None, 0.0))
    # move (reposition)
    targets = opts.get("reposition_targets")
    radius = opts.get("reposition_target_radius")
    exempt = radius_exempt_states(opts.get("reposition_radius_exempt_states")) if radius is not None else {}
    for (v, w), r in inst.routes.items():
        if targets is not None and w not in targets:
            continue
        restricted = radius is not None and w in radius and node_blocks(v, w) > int(radius[w])
        if restricted and v not in exempt:
            continue
        tau, g = disc.tau(r.T_h, distinct=True), disc.g(r.E_kwh)
        # outside the radius only from the exempt start levels of v (at every t)
        q_levels = [q for q in exempt[v] if g <= q <= L] if restricted else range(g, L + 1)
        for t in range(0, H - tau + 1):
            for q in q_levels:
                specs.append(("move", (v, t, q), (w, t + tau, q - g), t, t + tau, r.d_km, g,
                              None, None, 0.0))
    # deliver
    specs.extend(_delivery_specs(inst, opts))
    # swap
    q_max = opts.get("swap_q_max")
    q_hi = L - 1 if q_max is None else min(L - 1, int(q_max))
    for j in inst.S:
        f = inst.facility(j)
        if f.y == 0:
            continue  # fixed closed: x_ka <= y_j = 0 anyway
        for t in range(0, H - f.sigma + 1):
            for q in range(0, q_hi + 1):
                specs.append(("swap", (f.node, t, q), (f.node, t + f.sigma, L), t, t + f.sigma,
                              0.0, 0, None, j, 0.0))
    # terminal (9)
    for v in inst.nodes:
        for j in inst.S:
            if inst.facility(j).y == 0:
                continue
            gb = gbar[(v, j)]
            if gb == math.inf:
                continue
            for q in range(int(gb) + inst.q_res, L + 1):
                specs.append(("term", (v, H, q), SINK, H, H, 0.0, 0, None, j, 0.0))
    dummy = opts.get("dummy_terminal_cost")
    if dummy is not None:
        for v in inst.nodes:
            for q in range(L + 1):
                specs.append(("term", (v, H, q), SINK, H, H, 0.0, 0, None, None, float(dummy)))
    return specs


def _reachable(specs: List[_Spec], by_src: Dict[Tuple, List[int]], source: Tuple) -> Set[Tuple]:
    """Forward pass: states reachable from ``source`` through the template arcs."""
    seen: Set[Tuple] = {source}
    stack = [source]
    while stack:
        s = stack.pop()
        for idx in by_src.get(s, ()):
            d = specs[idx][2]
            if d not in seen:
                seen.add(d)
                stack.append(d)
    return seen


def build_arcs(inst: Instance, strict: bool = True, **overrides: Any) -> ArcLibrary:
    """Build the arc library of every bike per E2 (1)-(4), (9) and ``DECISIONS.md``.

    Options are ``DEFAULT_OPTIONS`` updated by ``inst.options`` and then by the
    keyword ``overrides`` (e.g. ``build_arcs(inst, dominance=False, tau_max=4)``).
    A forward reachability pass from ``s_k`` is always run for the terminal
    pre-check; with ``reachable_pruning=True`` unreachable arcs are dropped.
    ``strict`` controls whether a bike without any reachable real terminal arc
    raises :class:`InfeasibleInstanceError` (unless a dummy terminal arc exists).
    """
    opts = dict(DEFAULT_OPTIONS)
    opts.update(inst.options)
    opts.update(overrides)
    if opts.get("reposition_targets") is not None:
        opts["reposition_targets"] = set(opts["reposition_targets"])
    gbar = compute_gbar(inst)
    lib = ArcLibrary(inst, opts, gbar)
    specs = _template_specs(inst, opts, gbar)
    by_src: Dict[Tuple, List[int]] = defaultdict(list)
    for idx, sp in enumerate(specs):
        by_src[sp[1]].append(idx)
    prune = bool(opts.get("reachable_pruning", False))
    next_id = 0
    for b in inst.bikes:
        source = (b.v0, 0, b.q0)
        reach = _reachable(specs, by_src, source)
        has_real_term = any(sp[0] == "term" and sp[8] is not None and sp[1] in reach
                            for sp in specs)
        if not has_real_term:
            lib.infeasible_bikes.append(b.id)
        for sp in specs:
            if prune and sp[1] not in reach:
                continue
            kind, src, dst, l, u, d_km, g, order, fac, theta = sp
            lib._add(Arc(next_id, b.id, kind, src, dst, l, u, d_km, g, order, fac, theta))
            next_id += 1
    if lib.infeasible_bikes and strict and not lib.has_dummy_terminal:
        raise InfeasibleInstanceError(
            "no reachable terminal arc (9) for bikes " + ", ".join(map(str, lib.infeasible_bikes))
            + ": raise q0, add routes/swap sites, lower q_res, or set options.dummy_terminal_cost")
    return lib
