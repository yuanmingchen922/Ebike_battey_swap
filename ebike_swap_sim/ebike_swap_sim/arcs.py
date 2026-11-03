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

Storage modes (option ``library_mode``, R8 fifteen-site study, 2026-10-28)
--------------------------------------------------------------------------
``'per_bike'`` (the default; the key may be absent): :class:`ArcLibrary`, one ``Arc``
object per bike and arc, as before.  ``'union'``: :class:`UnionArcLibrary`, the
bike-independent template stored once as numpy columns with lazy per-bike views that
reproduce the per-bike library exactly (same arcs, same ids, same lookups) at a memory
cost independent of the fleet size; reachability of every bike class in one time-ordered
bitmask sweep (:func:`reach_sweep`).  ``build_arcs(inst, library_mode='union', ...)``,
``inst.options['library_mode'] = 'union'`` or :func:`build_union_arcs`.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict
from dataclasses import dataclass
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import numpy as np

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
    return list(_iter_delivery_specs(inst, opts))


def _iter_delivery_specs(inst: Instance, opts: Dict[str, Any]) -> Iterator[_Spec]:
    """Generator behind :func:`_delivery_specs` (same specs in the same order; the union
    library streams it instead of holding the list)."""
    disc = inst.disc
    H, L = disc.H, disc.L
    rounding = opts.get("energy_rounding", "per_leg")
    dominance = bool(opts.get("dominance", True))
    tau_max = opts.get("tau_max")
    slack = opts.get("start_slack")
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
                    yield ("deliver", (v, t, q), (o.d, u_a, q - g_a), t, u_a,
                           d_a, g_a, o.id, None, theta)


def _template_specs(inst: Instance, opts: Dict[str, Any],
                    gbar: Dict[Tuple[Node, Any], float]) -> List[_Spec]:
    """All bike-independent arc specifications (wait, move, deliver, swap, term)."""
    return list(_iter_template_specs(inst, opts, gbar))


def _iter_template_specs(inst: Instance, opts: Dict[str, Any],
                         gbar: Dict[Tuple[Node, Any], float]) -> Iterator[_Spec]:
    """Generator behind :func:`_template_specs`: the kinds come in the fixed order wait,
    move, deliver, swap, term (real terminal arcs, then the dummy ones); within a kind the
    loops are those written here.  The union library relies on this order (one contiguous
    block per kind, delivery arcs grouped by order, swap arcs grouped by facility)."""
    disc = inst.disc
    H, L = disc.H, disc.L
    # wait
    for v in inst.nodes:
        for t in range(H):
            for q in range(L + 1):
                yield ("wait", (v, t, q), (v, t + 1, q), t, t + 1, 0.0, 0, None, None, 0.0)
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
                yield ("move", (v, t, q), (w, t + tau, q - g), t, t + tau, r.d_km, g,
                       None, None, 0.0)
    # deliver
    yield from _iter_delivery_specs(inst, opts)
    # swap
    q_max = opts.get("swap_q_max")
    q_hi = L - 1 if q_max is None else min(L - 1, int(q_max))
    for j in inst.S:
        f = inst.facility(j)
        if f.y == 0:
            continue  # fixed closed: x_ka <= y_j = 0 anyway
        for t in range(0, H - f.sigma + 1):
            for q in range(0, q_hi + 1):
                yield ("swap", (f.node, t, q), (f.node, t + f.sigma, L), t, t + f.sigma,
                       0.0, 0, None, j, 0.0)
    # terminal (9)
    for v in inst.nodes:
        for j in inst.S:
            if inst.facility(j).y == 0:
                continue
            gb = gbar[(v, j)]
            if gb == math.inf:
                continue
            for q in range(int(gb) + inst.q_res, L + 1):
                yield ("term", (v, H, q), SINK, H, H, 0.0, 0, None, j, 0.0)
    dummy = opts.get("dummy_terminal_cost")
    if dummy is not None:
        for v in inst.nodes:
            for q in range(L + 1):
                yield ("term", (v, H, q), SINK, H, H, 0.0, 0, None, None, float(dummy))


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
    if library_mode(opts) == "union":       # R8: one network, per-bike views (default: per bike)
        return build_union_arcs(inst, strict=strict, **overrides)
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


# ---------------------------------------------------------------------------
# union (bike-class) library: one network of distinct arc keys with per-bike views
# (R8 fifteen-site study, 2026-10-28; ``notes/siting15_design.md`` sections 2-3, critic C2)
# ---------------------------------------------------------------------------
#: ``library_mode`` option values: ``'per_bike'`` (the default, :class:`ArcLibrary` with one
#: ``Arc`` per bike and arc) or ``'union'`` (:class:`UnionArcLibrary`).  The key is NOT in
#: ``DEFAULT_OPTIONS`` (an absent key means ``'per_bike'``), so every existing instance JSON,
#: option dict, pruning signature and cache key is unchanged.
LIBRARY_MODES = ("per_bike", "union")
_KIND_CODE = {kind: i for i, kind in enumerate(KINDS)}
_COLS = ("kind", "src", "dst", "l", "u", "dkm", "g", "oidx", "fidx", "theta")
_COL_DTYPE = {"kind": np.int8, "src": np.int32, "dst": np.int32, "l": np.int32, "u": np.int32,
              "dkm": np.float64, "g": np.int32, "oidx": np.int32, "fidx": np.int32, "theta": np.float64}


def library_mode(options: Dict[str, Any]) -> str:
    """Effective ``library_mode`` of an option dict (``'per_bike'`` when absent or ``None``)."""
    mode = options.get("library_mode") or "per_bike"
    if mode not in LIBRARY_MODES:
        raise ValueError(f"library_mode must be one of {LIBRARY_MODES} (got {mode!r})")
    return mode


class _BitRank:
    """Bit vector over the stored specs with rank / select: ``test(i)``, ``rank(i)`` (set bits
    below ``i``), ``select(r)`` (index of the ``r``-th set bit), ``count``; about 1 MB per
    million specs.  ``identity`` marks the all-ones vector (no storage)."""
    __slots__ = ("n", "count", "words", "cum", "identity")

    def __init__(self, mask: Optional[np.ndarray], n: int) -> None:
        self.n = int(n)
        if mask is None:
            self.identity = True
            self.count = self.n
            self.words = None
            self.cum = None
            return
        self.identity = False
        n_words = max(1, (self.n + 63) // 64)
        bits = np.zeros(n_words * 64, dtype=np.uint8)
        bits[:self.n] = np.asarray(mask, dtype=bool)[:self.n]
        packed = np.packbits(bits, bitorder="little")
        self.words = np.frombuffer(packed.tobytes(), dtype="<u8").copy()
        pop = np.unpackbits(packed).reshape(n_words, 64).sum(axis=1).astype(np.int64)
        self.cum = np.concatenate([np.zeros(1, dtype=np.int64), np.cumsum(pop)])
        self.count = int(self.cum[-1])

    def test(self, i: int) -> bool:
        if self.identity:
            return 0 <= i < self.n
        if i >= self.n or i < 0:
            return False
        return bool((int(self.words[i >> 6]) >> (i & 63)) & 1)

    def rank(self, i: int) -> int:
        """Number of set specs below ``i``; ``rank(n)`` is the total (R8 fix: ``n`` a multiple of 64
        indexed one word past the end before)."""
        if self.identity:
            return int(i)
        if i >= self.n:
            return self.count
        w = i >> 6
        return int(self.cum[w]) + (int(self.words[w]) & ((1 << (i & 63)) - 1)).bit_count()

    def select(self, r: int) -> int:
        if self.identity:
            return int(r)
        if not (0 <= r < self.count):
            raise IndexError(r)
        w = int(np.searchsorted(self.cum, r, side="right")) - 1
        x = int(self.words[w])
        for _ in range(r - int(self.cum[w])):
            x &= x - 1
        return (w << 6) + ((x & -x).bit_length() - 1)

    def mask(self, lo: int = 0, hi: Optional[int] = None) -> np.ndarray:
        """Boolean mask of the specs ``lo..hi-1``."""
        hi = self.n if hi is None else int(hi)
        if self.identity:
            return np.ones(max(0, hi - lo), dtype=bool)
        w0, w1 = lo >> 6, (hi + 63) >> 6
        bits = np.unpackbits(np.frombuffer(self.words[w0:w1].tobytes(), dtype=np.uint8), bitorder="little")
        return bits[lo - (w0 << 6): hi - (w0 << 6)].astype(bool)

    def indices(self, lo: int = 0, hi: Optional[int] = None) -> np.ndarray:
        """Set spec indices in ``lo..hi-1`` (ascending)."""
        hi = self.n if hi is None else int(hi)
        if self.identity:
            return np.arange(lo, hi, dtype=np.int64)
        return lo + np.flatnonzero(self.mask(lo, hi))


def reach_sweep(src: np.ndarray, dst: np.ndarray, state_t: np.ndarray, sources: Sequence[int],
                n_levels: int) -> np.ndarray:
    """One time-ordered bitmask sweep (critic C2): states reachable from every source at once.

    ``src`` / ``dst`` are the state ids of the arcs, ``state_t[s]`` the time level of state
    ``s`` (every arc satisfies ``state_t[dst] >= state_t[src]``; the sink sits at level
    ``H + 1``), ``sources[c]`` the source state of class ``c``.  Returns ``R`` of shape
    ``(n_states, n_words)`` (``uint64``) with bit ``c`` of ``R[s]`` set iff ``s`` is reachable
    from ``sources[c]``.  Levels are processed in increasing ``t``; the arcs of a level that
    stay on the level (zero-duration arcs, if any) are iterated to a fixpoint before the
    level is propagated, so the result equals a per-class depth-first search."""
    n_states = int(state_t.shape[0])
    n_classes = len(sources)
    n_words = max(1, (n_classes + 63) // 64)
    R = np.zeros((n_states, n_words), dtype=np.uint64)
    for c, sid in enumerate(sources):
        R[sid, c >> 6] |= np.uint64(1) << np.uint64(c & 63)
    if src.shape[0] == 0:
        return R
    src_t = state_t[src]
    dst_t = state_t[dst]
    order = np.argsort(src_t, kind="stable")
    bounds = np.searchsorted(src_t[order], np.arange(n_levels + 1))
    flat = R.reshape(-1) if n_words == 1 else None

    def apply(idx: np.ndarray) -> None:
        if flat is not None:
            np.bitwise_or.at(flat, dst[idx], flat[src[idx]])
        else:
            np.bitwise_or.at(R, dst[idx], R[src[idx]])

    for t in range(n_levels):
        sel = order[bounds[t]:bounds[t + 1]]
        if sel.size == 0:
            continue
        zd = sel[dst_t[sel] == t]
        if zd.size:
            heads = dst[zd]
            while True:
                before = R[heads].copy()
                apply(zd)
                if np.array_equal(R[heads], before):
                    break
        apply(sel)
    return R


def coreach_sweep(src: np.ndarray, dst: np.ndarray, state_t: np.ndarray, sink: int,
                  n_levels: int) -> np.ndarray:
    """Backward counterpart of :func:`reach_sweep`: boolean ``co[s]`` = the sink is reachable
    from state ``s`` through the given arcs (levels processed in decreasing ``t``)."""
    co = np.zeros(int(state_t.shape[0]), dtype=bool)
    co[sink] = True
    if src.shape[0] == 0:
        return co
    src_t = state_t[src]
    dst_t = state_t[dst]
    order = np.argsort(src_t, kind="stable")
    bounds = np.searchsorted(src_t[order], np.arange(n_levels + 1))
    for t in range(n_levels - 1, -1, -1):
        sel = order[bounds[t]:bounds[t + 1]]
        if sel.size == 0:
            continue
        zd = sel[dst_t[sel] == t]
        if zd.size:
            tails = src[zd]
            while True:
                before = co[tails].copy()
                np.logical_or.at(co, tails, co[dst[zd]])
                if np.array_equal(co[tails], before):
                    break
        np.logical_or.at(co, src[sel], co[dst[sel]])
    return co


class _Columns:
    """Accumulator of spec columns emitted block by block in template order.  With ``keep``
    (a boolean mask over the template specs) only the kept rows are stored; ``full=False``
    stores ``kind`` / ``src`` / ``dst`` only (the reachability pass)."""
    __slots__ = ("keep", "full", "pos", "parts")

    def __init__(self, keep: Optional[np.ndarray], full: bool) -> None:
        self.keep = None if keep is None else keep
        self.full = full
        self.pos = 0
        self.parts: Dict[str, List[np.ndarray]] = {c: [] for c in _COLS}

    def put(self, kind: int, src: np.ndarray, dst: np.ndarray, l: Any = 0, u: Any = 0, dkm: Any = 0.0,
            g: Any = 0, oidx: Any = -1, fidx: Any = -1, theta: Any = 0.0) -> None:
        m = int(src.shape[0])
        if m == 0:
            return
        idx = None
        if self.keep is not None:
            sel = self.keep[self.pos:self.pos + m]
            self.pos += m
            if not sel.any():
                return
            idx = np.flatnonzero(sel)
            src, dst = src[idx], dst[idx]
            m = idx.size
        else:
            self.pos += m
        p = self.parts
        p["kind"].append(np.full(m, kind, dtype=np.int8))
        p["src"].append(src.astype(np.int32, copy=False))
        p["dst"].append(dst.astype(np.int32, copy=False))
        if not self.full:
            return
        for name, val in (("l", l), ("u", u), ("dkm", dkm), ("g", g), ("oidx", oidx), ("fidx", fidx), ("theta", theta)):
            if isinstance(val, np.ndarray):
                arr = val[idx] if idx is not None else val
                p[name].append(arr.astype(_COL_DTYPE[name], copy=False))
            else:
                p[name].append(np.full(m, val, dtype=_COL_DTYPE[name]))

    def finish(self) -> Dict[str, np.ndarray]:
        out = {}
        for name in _COLS:
            lst = self.parts[name]
            if not lst:
                if name in ("kind", "src", "dst") or self.full:
                    out[name] = np.zeros(0, dtype=_COL_DTYPE[name])
                continue
            out[name] = np.concatenate(lst)
            lst.clear()
        return out


def _union_columns(inst: Instance, opts: Dict[str, Any], gbar: Dict[Tuple[Node, Any], float],
                   nidx: Dict[Node, int], stride_v: int, sink_sid: int,
                   keep: Optional[np.ndarray] = None, full: bool = True) -> Dict[str, np.ndarray]:
    """The template specs of :func:`_iter_template_specs` as numpy columns, emitted block by
    block in exactly the same order (wait, move, deliver, swap, term; same loops), with dense
    state ids ``sid(v, t, q) = nidx[v] * stride_v + t * (L + 1) + q`` and the sink at
    ``sink_sid``.  Vectorised per block, so no per-spec Python object is created.  The
    reproduction tests assert equality with the generator for every option."""
    disc = inst.disc
    H, L = disc.H, disc.L
    Lq = L + 1
    cols = _Columns(keep, full)
    opos = {o.id: p for p, o in enumerate(inst.orders)}
    fpos = {j: p for p, j in enumerate(inst.S)}
    n_nodes = len(inst.nodes)
    # ---- wait: for v, for t < H, for q
    if n_nodes and H > 0:
        base = (np.arange(n_nodes, dtype=np.int64) * stride_v)[:, None, None]
        rel = (np.arange(H, dtype=np.int64)[None, :, None] * Lq + np.arange(Lq, dtype=np.int64)[None, None, :])
        src = (base + rel).ravel()
        tt = np.tile(np.repeat(np.arange(H, dtype=np.int64), Lq), n_nodes)
        cols.put(_KIND_CODE["wait"], src, src + Lq, l=tt, u=tt + 1)
    # ---- move: for (v, w) in routes order
    targets = opts.get("reposition_targets")
    radius = opts.get("reposition_target_radius")
    exempt = radius_exempt_states(opts.get("reposition_radius_exempt_states")) if radius is not None else {}
    tmpl: Dict[Tuple[int, int, Tuple[int, ...]], Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for (v, w), r in inst.routes.items():
        if targets is not None and w not in targets:
            continue
        restricted = radius is not None and w in radius and node_blocks(v, w) > int(radius[w])
        if restricted and v not in exempt:
            continue
        tau, g = disc.tau(r.T_h, distinct=True), disc.g(r.E_kwh)
        n_t = H - tau + 1
        if n_t <= 0:
            continue
        q_levels = tuple(q for q in exempt[v] if g <= q <= L) if restricted else tuple(range(g, L + 1))
        if not q_levels:
            continue
        key = (tau, g, q_levels)
        t3 = tmpl.get(key)
        if t3 is None:
            tq = np.arange(n_t, dtype=np.int64)
            qa = np.asarray(q_levels, dtype=np.int64)
            rel_src = (tq[:, None] * Lq + qa[None, :]).ravel()
            rel_dst = ((tq + tau)[:, None] * Lq + (qa - g)[None, :]).ravel()
            ll = np.repeat(tq, qa.size)
            t3 = tmpl[key] = (rel_src, rel_dst, ll)
        rel_src, rel_dst, ll = t3
        cols.put(_KIND_CODE["move"], nidx[v] * stride_v + rel_src, nidx[w] * stride_v + rel_dst,
                 l=ll, u=ll + tau, dkm=r.d_km, g=g)
    # ---- deliver: for o, for v, for t, for q
    rounding = opts.get("energy_rounding", "per_leg")
    dominance = bool(opts.get("dominance", True))
    tau_max = opts.get("tau_max")
    slack = opts.get("start_slack")
    kd = _KIND_CODE["deliver"]
    for o in inst.orders:
        r2 = inst.route(o.o, o.d)
        if r2 is None:
            continue
        tau2 = disc.tau(r2.T_h, distinct=o.o != o.d)
        g2 = disc.g(r2.E_kwh)
        t_hi = H if slack is None else min(H, o.b + int(slack))
        theta_u = np.array([inst.theta(o.id, ua) for ua in range(H + 1)], dtype=np.float64)
        base_d = nidx[o.d] * stride_v
        oi = opos[o.id]
        t_all = np.arange(o.r, t_hi + 1, dtype=np.int64)
        if t_all.size == 0:
            continue
        for v in inst.nodes:
            r1 = inst.route(v, o.o)
            if r1 is None:
                continue
            tau1 = disc.tau(r1.T_h, distinct=v != o.o)
            if tau_max is not None and tau1 > tau_max:
                continue
            g1 = disc.g(r1.E_kwh)
            d_a = r1.d_km + r2.d_km
            t = t_all
            arrive = t + tau1
            if dominance:
                m_ = arrive >= o.a
                t, arrive = t[m_], arrive[m_]
            if rounding == "concat":
                g_a = disc.g(r1.E_kwh + r2.E_kwh)
                tau_cat = disc.tau(r1.T_h + r2.T_h, distinct=(v != o.o or o.o != o.d))
                u = np.where(arrive >= o.a, t + tau_cat + o.hp + o.hd, o.a + o.hp + tau2 + o.hd)
            else:
                g_a = g1 + g2
                u = np.maximum(arrive, o.a) + o.hp + tau2 + o.hd
            ok = u <= H
            t, u = t[ok], u[ok]
            n_q = L + 1 - g_a
            if t.size == 0 or n_q <= 0:
                continue
            q = np.arange(g_a, L + 1, dtype=np.int64)
            src = nidx[v] * stride_v + (t[:, None] * Lq + q[None, :]).ravel()
            dst = base_d + (u[:, None] * Lq + (q - g_a)[None, :]).ravel()
            cols.put(kd, src, dst, l=np.repeat(t, n_q), u=np.repeat(u, n_q), dkm=d_a, g=g_a, oidx=oi,
                     theta=np.repeat(theta_u[u], n_q))
    # ---- swap: for j, for t, for q <= q_hi
    q_max = opts.get("swap_q_max")
    q_hi = L - 1 if q_max is None else min(L - 1, int(q_max))
    for j in inst.S:
        f = inst.facility(j)
        if f.y == 0:
            continue
        n_t = H - f.sigma + 1
        if n_t <= 0 or q_hi < 0:
            continue
        tq = np.arange(n_t, dtype=np.int64)
        qa = np.arange(q_hi + 1, dtype=np.int64)
        base_f = nidx[f.node] * stride_v
        src = base_f + (tq[:, None] * Lq + qa[None, :]).ravel()
        dst = base_f + np.repeat((tq + f.sigma) * Lq + L, qa.size)
        ll = np.repeat(tq, qa.size)
        cols.put(_KIND_CODE["swap"], src, dst, l=ll, u=ll + f.sigma, fidx=fpos[j])
    # ---- terminal (9): for v, for j, for q >= gbar + q_res; then dummy
    kt = _KIND_CODE["term"]
    for v in inst.nodes:
        base_v = nidx[v] * stride_v + H * Lq
        for j in inst.S:
            if inst.facility(j).y == 0:
                continue
            gb = gbar[(v, j)]
            if gb == math.inf:
                continue
            q = np.arange(int(gb) + inst.q_res, L + 1, dtype=np.int64)
            if q.size == 0:
                continue
            cols.put(kt, base_v + q, np.full(q.size, sink_sid, dtype=np.int64), l=H, u=H, fidx=fpos[j])
    dummy = opts.get("dummy_terminal_cost")
    if dummy is not None:
        q = np.arange(L + 1, dtype=np.int64)
        for v in inst.nodes:
            base_v = nidx[v] * stride_v + H * Lq
            cols.put(kt, base_v + q, np.full(q.size, sink_sid, dtype=np.int64), l=H, u=H, theta=float(dummy))
    return cols.finish()


class _ArcSeq(Sequence):
    """Lazy ``lib.arcs`` of a :class:`UnionArcLibrary`: ``len`` = number of per-bike arcs,
    ``seq[id]`` materialises the arc, iteration runs bike after bike in id order."""
    __slots__ = ("_lib",)

    def __init__(self, lib: "UnionArcLibrary") -> None:
        self._lib = lib

    def __len__(self) -> int:
        return self._lib._n_total

    def __getitem__(self, i: Any) -> Any:
        if isinstance(i, slice):
            return [self._lib.arc(j) for j in range(*i.indices(len(self)))]
        i = int(i)
        if i < 0:
            i += len(self)
        if not (0 <= i < len(self)):
            raise IndexError(i)
        return self._lib.arc(i)

    def __iter__(self) -> Iterator[Arc]:
        lib = self._lib
        for k in lib._bike_order:
            yield from lib.arcs_of_iter(k)


class _LazyIds(Sequence):
    """Ids of the arcs of all bikes over one block ``lo..hi-1`` of specs (bike after bike,
    ascending), computed arithmetically: ``len`` and ``seq[j]`` without materialising."""
    __slots__ = ("_lib", "_lo", "_hi", "_cum", "_start")

    def __init__(self, lib: "UnionArcLibrary", lo: int, hi: int) -> None:
        self._lib = lib
        self._lo, self._hi = int(lo), int(hi)
        cum = [0]
        start = []
        for k in lib._bike_order:
            rs = lib._view[lib.class_of_bike[k]]
            r0 = rs.rank(self._lo)
            start.append(lib._offset_of[k] + r0)
            cum.append(cum[-1] + rs.rank(self._hi) - r0)
        self._cum = cum
        self._start = start

    def __len__(self) -> int:
        return self._cum[-1]

    def __getitem__(self, j: Any) -> Any:
        if isinstance(j, slice):
            return [self[i] for i in range(*j.indices(len(self)))]
        j = int(j)
        if j < 0:
            j += len(self)
        if not (0 <= j < len(self)):
            raise IndexError(j)
        pos = bisect_right(self._cum, j) - 1
        return self._start[pos] + (j - self._cum[pos])


class _LazyDeliv(Mapping):
    """``lib._deliv`` of a union library (read by ``costs.check_lib_prices``): order id ->
    lazy id sequence of its delivery arcs over all bikes."""
    __slots__ = ("_lib",)

    def __init__(self, lib: "UnionArcLibrary") -> None:
        self._lib = lib

    def __getitem__(self, i: Any) -> _LazyIds:
        lo, hi = self._lib._order_range[i]
        return _LazyIds(self._lib, lo, hi)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._lib._order_range)

    def __len__(self) -> int:
        return len(self._lib._order_range)


class UnionArcLibrary(ArcLibrary):
    """Arc sets ``A_k`` of all bikes stored ONCE as the union network of distinct arc keys
    (the template specs of :func:`_iter_template_specs`, columnar numpy arrays) with lazy
    per-bike views (``library_mode = 'union'``; design note sections 2-3, critic C2).

    Every bike ``k`` sees exactly the arcs :func:`build_arcs` would have produced for it,
    with the SAME ids: the specs with a tail state reachable from ``s_k`` when
    ``reachable_pruning`` is on (all specs otherwise), numbered bike after bike in template
    order (``id = offset_k + rank_c(spec)``; :class:`_BitRank` per bike class).  Bikes with
    the same source state ``(v0, q0)`` form a class; reachability is one time-ordered
    bitmask sweep over the union network for all classes (:func:`reach_sweep`), never a
    per-bike search.  With ``reachable_pruning`` the stored columns hold only the specs
    reachable by at least one class (the others are in no bike's set, so every view and
    every id is unchanged).  Memory is that of the stored union network plus about 1 MB per
    class per million specs, independent of the fleet size; states are dense integers
    ``nidx[v] * (H + 2) * (L + 1) + t * (L + 1) + q`` (no state table).

    Same public interface as :class:`ArcLibrary` (``arc``, ``arcs`` (lazy), ``find``,
    ``out_arcs``, ``in_arcs``, ``delivery_arcs``, ``swap_arcs``, ``swap_arcs_at``,
    ``terminal_arcs``, ``arcs_of_kind``, ``arcs_of``, ``ids_of``, ``states``, ``counts``,
    ``summary``, ``source``, ``bikes``, ``gbar``, ``options``, ``has_dummy_terminal``,
    ``infeasible_bikes``), plus the class-level accessors (``class_of_bike``,
    ``class_source``, ``class_bikes``, ``n_classes``, ``reachable_mask``,
    ``reachable_states``, ``has_real_terminal``, ``spec_of_id``, ``id_of``, ``spec_view``,
    ``memory_bytes``, ``timings``).  ``aggregate.AggregatedNetwork`` has a fast path on it.
    """

    def __init__(self, inst: Instance, options: Dict[str, Any],
                 gbar: Dict[Tuple[Node, Any], float]) -> None:
        self.inst = inst
        self.options = options
        self.gbar = gbar
        self.infeasible_bikes: List[Any] = []
        self.has_dummy_terminal = options.get("dummy_terminal_cost") is not None
        self.prune = bool(options.get("reachable_pruning", False))
        self.n_specs = 0                      # stored specs
        self.n_template_specs = 0             # specs of the template (all kinds, every tail)
        self.timings: Dict[str, float] = {}
        # dense state space
        self._nodes: List[Node] = list(inst.nodes)
        self._nidx: Dict[Node, int] = {v: i for i, v in enumerate(self._nodes)}
        self._Lq = inst.L + 1
        self._stride_v = (inst.H + 2) * self._Lq
        self._sink_sid = len(self._nodes) * self._stride_v
        self._n_states = self._sink_sid + 1
        H = inst.H
        self._state_t = np.concatenate([np.tile(np.repeat(np.arange(H + 2, dtype=np.int32), self._Lq), len(self._nodes)),
                                        np.array([H + 1], dtype=np.int32)])
        self._state_q = np.concatenate([np.tile(np.arange(self._Lq, dtype=np.int32), (H + 2) * len(self._nodes)),
                                        np.array([-1], dtype=np.int32)])
        # columns (filled by the builder)
        self._kind = self._src = self._dst = self._l = self._u = self._g = None
        self._oidx = self._fidx = self._dkm = self._theta = None
        self._order_ids: List[Any] = [o.id for o in inst.orders]
        self._fac_ids: List[Any] = list(inst.S)
        self._order_pos = {i: p for p, i in enumerate(self._order_ids)}
        self._fac_pos = {j: p for p, j in enumerate(self._fac_ids)}
        self._block: Dict[str, Tuple[int, int]] = {}
        self._order_range: Dict[Any, Tuple[int, int]] = {}
        self._swap_range: Dict[Any, Tuple[int, int]] = {}
        self._csr_order = self._csr_ptr = None
        self._in_order = self._in_ptr = None
        self.n_states_used = 0
        # classes
        self.class_source: List[State] = []
        self.class_bikes: List[List[Any]] = []
        self.class_of_bike: Dict[Any, int] = {}
        self.class_sid: List[int] = []
        self._reach: Optional[np.ndarray] = None       # (n_states, n_words) uint64
        self._reach_rs: List[_BitRank] = []            # reachable stored specs per class
        self._view: List[_BitRank] = []                # specs of a bike's view per class
        self.class_has_term: List[bool] = []
        self._bike_order: List[Any] = []
        self._offsets: List[int] = []
        self._offset_of: Dict[Any, int] = {}
        self._n_total = 0

    # ------------------------------------------------------------ building
    @classmethod
    def build(cls, inst: Instance, strict: bool = True, **overrides: Any) -> "UnionArcLibrary":
        """Alias of :func:`build_union_arcs`."""
        return build_union_arcs(inst, strict=strict, **overrides)

    def _sid_of(self, st: Tuple) -> Optional[int]:
        """Dense state id of a state tuple (``None`` if it is not a state of this instance)."""
        if st == SINK:
            return self._sink_sid
        if len(st) != 3:
            return None
        n = self._nidx.get(st[0])
        if n is None:
            return None
        try:
            t, q = int(st[1]), int(st[2])
        except (TypeError, ValueError):
            return None
        if t != st[1] or q != st[2] or not (0 <= t <= self.inst.H) or not (0 <= q <= self.inst.L):
            return None
        return n * self._stride_v + t * self._Lq + q

    def _state_tuple(self, sid: int) -> Tuple:
        sid = int(sid)
        if sid == self._sink_sid:
            return SINK
        n, rem = divmod(sid, self._stride_v)
        t, q = divmod(rem, self._Lq)
        return (self._nodes[n], t, q)

    def _build(self) -> None:
        """Columns, classes and reachability (critic C2: one sweep for all classes)."""
        import time as _time

        inst, opts, gbar = self.inst, self.options, self.gbar
        for b in inst.bikes:
            key = (b.v0, 0, b.q0)
            c = self.class_of_bike.get(("class", key))
            if c is None:
                c = len(self.class_source)
                self.class_source.append(key)
                self.class_bikes.append([])
                sid = self._sid_of(key)
                if sid is None:
                    raise ValueError(f"bike {b.id!r} starts outside the state space: {key}")
                self.class_sid.append(sid)
                self.class_of_bike[("class", key)] = c
            self.class_bikes[c].append(b.id)
            self.class_of_bike[b.id] = c
        for key in list(self.class_source):
            self.class_of_bike.pop(("class", key), None)
        n_levels = inst.H + 2
        t0 = _time.perf_counter()
        if self.prune:
            light = _union_columns(inst, opts, gbar, self._nidx, self._stride_v, self._sink_sid, keep=None, full=False)
            self.n_template_specs = int(light["src"].shape[0])
            t1 = _time.perf_counter()
            self._reach = reach_sweep(light["src"], light["dst"], self._state_t, self.class_sid, n_levels)
            keep = (self._reach[light["src"]] != 0).any(axis=1)
            del light
            t2 = _time.perf_counter()
            cols = _union_columns(inst, opts, gbar, self._nidx, self._stride_v, self._sink_sid, keep=keep, full=True)
            del keep
            t3 = _time.perf_counter()
            self.timings.update({"specs_light": t1 - t0, "reach": t2 - t1, "specs": t3 - t2})
        else:
            cols = _union_columns(inst, opts, gbar, self._nidx, self._stride_v, self._sink_sid, keep=None, full=True)
            self.n_template_specs = int(cols["src"].shape[0])
            t1 = _time.perf_counter()
            self._reach = reach_sweep(cols["src"], cols["dst"], self._state_t, self.class_sid, n_levels)
            t2 = _time.perf_counter()
            self.timings.update({"specs": t1 - t0, "reach": t2 - t1})
        for name in _COLS:
            setattr(self, "_" + name, cols[name])
        self.n_specs = int(self._src.shape[0])
        # blocks per kind (kinds are emitted in KINDS order), order and facility ranges
        edges = np.searchsorted(self._kind, np.arange(len(KINDS) + 1), side="left")
        for i, kind in enumerate(KINDS):
            self._block[kind] = (int(edges[i]), int(edges[i + 1]))
        lo, hi = self._block["deliver"]
        e = np.searchsorted(self._oidx[lo:hi], np.arange(len(self._order_ids) + 1), side="left") if hi > lo else None
        for p, i in enumerate(self._order_ids):
            self._order_range[i] = (lo + int(e[p]), lo + int(e[p + 1])) if e is not None else (lo, lo)
        lo, hi = self._block["swap"]
        e = np.searchsorted(self._fidx[lo:hi], np.arange(len(self._fac_ids) + 1), side="left") if hi > lo else None
        for p, j in enumerate(self._fac_ids):
            self._swap_range[j] = (lo + int(e[p]), lo + int(e[p + 1])) if e is not None else (lo, lo)
        # CSR by tail state (template order within a state)
        order = np.argsort(self._src, kind="stable").astype(np.int32)
        self._csr_ptr = np.searchsorted(self._src[order], np.arange(self._n_states + 1), side="left")
        self._csr_order = order
        self.n_states_used = int(np.unique(np.concatenate([self._src, self._dst])).size) if self.n_specs else 0
        # per-class reachable specs, terminal pre-check, offsets
        t_lo, t_hi = self._block["term"]
        real_term = np.arange(t_lo, t_hi)[self._fidx[t_lo:t_hi] >= 0]
        for c in range(len(self.class_source)):
            bits = ((self._reach[self._src, c >> 6] >> np.uint64(c & 63)) & np.uint64(1)).astype(bool)
            self._reach_rs.append(_BitRank(bits, self.n_specs))
            self.class_has_term.append(bool(bits[real_term].any()) if real_term.size else False)
        self._view = list(self._reach_rs) if self.prune else [_BitRank(None, self.n_specs)] * max(1, len(self.class_source))
        off = 0
        for b in inst.bikes:
            c = self.class_of_bike[b.id]
            self._bike_order.append(b.id)
            self._offsets.append(off)
            self._offset_of[b.id] = off
            off += self._view[c].count
            if not self.class_has_term[c]:
                self.infeasible_bikes.append(b.id)
        self._n_total = off
        self.timings["index"] = _time.perf_counter() - (t3 if self.prune else t2)

    # ------------------------------------------------------------- id maps
    def spec_of_id(self, arc_id: int) -> Tuple[Any, int]:
        """``(bike, stored spec index)`` of a per-bike arc id."""
        arc_id = int(arc_id)
        if not (0 <= arc_id < self._n_total):
            raise IndexError(f"arc id {arc_id} outside 0..{self._n_total - 1}")
        pos = bisect_right(self._offsets, arc_id) - 1
        k = self._bike_order[pos]
        return k, self._view[self.class_of_bike[k]].select(arc_id - self._offsets[pos])

    def id_of(self, k: Any, spec: int) -> int:
        """Per-bike arc id of stored spec ``spec`` in bike ``k``'s view (``KeyError`` if absent)."""
        rs = self._view[self.class_of_bike[k]]
        if not rs.test(int(spec)):
            raise KeyError(f"spec {spec} is not in the arc set of bike {k!r}")
        return self._offset_of[k] + rs.rank(int(spec))

    def spec_view(self, k: Any) -> _BitRank:
        """Rank / select vector of bike ``k``'s arc set over the stored specs."""
        return self._view[self.class_of_bike[k]]

    def reachable_mask(self, k: Any) -> np.ndarray:
        """Boolean mask over the stored specs: tail state reachable from ``s_k``."""
        return self._reach_rs[self.class_of_bike[k]].mask()

    def reachable_states(self, k: Any) -> Set[Tuple]:
        """States reachable from ``s_k`` (what ``_reachable`` returns for the per-bike path)."""
        c = self.class_of_bike[k]
        bits = (self._reach[:, c >> 6] >> np.uint64(c & 63)) & np.uint64(1)
        return {self._state_tuple(s) for s in np.flatnonzero(bits)}

    def has_real_terminal(self, k: Any) -> bool:
        return self.class_has_term[self.class_of_bike[k]]

    @property
    def n_classes(self) -> int:
        return len(self.class_source)

    # ------------------------------------------------------------- lookups
    def _make(self, k: Any, s: int, arc_id: int) -> Arc:
        oi = int(self._oidx[s])
        fi = int(self._fidx[s])
        return Arc(int(arc_id), k, KINDS[self._kind[s]], self._state_tuple(self._src[s]), self._state_tuple(self._dst[s]),
                   int(self._l[s]), int(self._u[s]), float(self._dkm[s]), int(self._g[s]),
                   self._order_ids[oi] if oi >= 0 else None, self._fac_ids[fi] if fi >= 0 else None,
                   float(self._theta[s]))

    def _arcs_from_specs(self, k: Any, specs: np.ndarray) -> List[Arc]:
        """Arcs of bike ``k`` for ascending stored spec indices that are all in its view."""
        if specs.size == 0:
            return []
        rs = self._view[self.class_of_bike[k]]
        off = self._offset_of[k]
        if rs.identity:
            return [self._make(k, int(s), off + int(s)) for s in specs]
        first = rs.rank(int(specs[0]))
        if specs.size == int(specs[-1]) - int(specs[0]) + 1:   # contiguous run
            return [self._make(k, int(s), off + first + i) for i, s in enumerate(specs)]
        return [self._make(k, int(s), off + rs.rank(int(s))) for s in specs]

    def _view_specs(self, k: Any, lo: int, hi: int) -> np.ndarray:
        return self._view[self.class_of_bike[k]].indices(lo, hi)

    def arc(self, arc_id: int) -> Arc:
        k, s = self.spec_of_id(arc_id)
        return self._make(k, s, int(arc_id))

    @property
    def arcs(self) -> _ArcSeq:   # type: ignore[override]
        return _ArcSeq(self)

    @arcs.setter
    def arcs(self, value: Any) -> None:   # ArcLibrary.__init__ compatibility (unused)
        pass

    @property
    def _deliv(self) -> _LazyDeliv:   # type: ignore[override]
        return _LazyDeliv(self)

    @_deliv.setter
    def _deliv(self, value: Any) -> None:
        pass

    def __len__(self) -> int:
        return self._n_total

    def arcs_of_iter(self, k: Any) -> Iterator[Arc]:
        rs = self._view[self.class_of_bike[k]]
        off = self._offset_of[k]
        if rs.identity:
            for s in range(self.n_specs):
                yield self._make(k, s, off + s)
        else:
            for i, s in enumerate(rs.indices()):
                yield self._make(k, int(s), off + i)

    def arcs_of(self, k: Any) -> List[Arc]:
        return list(self.arcs_of_iter(k))

    def ids_of(self, k: Any) -> List[int]:
        off = self._offset_of[k]
        return list(range(off, off + self._view[self.class_of_bike[k]].count))

    def states(self, k: Any) -> Set[Tuple]:
        specs = self._view[self.class_of_bike[k]].indices()
        ids = np.unique(np.concatenate([self._src[specs], self._dst[specs]])) if specs.size else np.zeros(0, int)
        out = {self._state_tuple(s) for s in ids}
        out.add(self.source(k))
        out.add(SINK)
        return out

    def _slice(self, st: Tuple) -> np.ndarray:
        s = self._sid_of(st)
        if s is None:
            return np.zeros(0, dtype=np.int32)
        return self._csr_order[self._csr_ptr[s]:self._csr_ptr[s + 1]]

    def _in_slice(self, st: Tuple) -> np.ndarray:
        if self._in_order is None:
            order = np.argsort(self._dst, kind="stable").astype(np.int32)
            self._in_ptr = np.searchsorted(self._dst[order], np.arange(self._n_states + 1), side="left")
            self._in_order = order
        s = self._sid_of(st)
        if s is None:
            return np.zeros(0, dtype=np.int32)
        return self._in_order[self._in_ptr[s]:self._in_ptr[s + 1]]

    def _filter_view(self, k: Any, specs: np.ndarray) -> np.ndarray:
        rs = self._view[self.class_of_bike[k]]
        if rs.identity or specs.size == 0:
            return specs
        w = specs >> 6
        bits = (rs.words[w] >> (specs & 63).astype(np.uint64)) & np.uint64(1)
        return specs[bits.astype(bool)]

    def out_arcs(self, k: Any, node: Tuple) -> List[Arc]:
        specs = self._filter_view(k, self._slice(node))
        return [self._make(k, int(s), self.id_of(k, int(s))) for s in specs]

    def in_arcs(self, k: Any, node: Tuple) -> List[Arc]:
        specs = np.sort(self._filter_view(k, self._in_slice(node)))
        return [self._make(k, int(s), self.id_of(k, int(s))) for s in specs]

    def _range_arcs(self, lo: int, hi: int, k: Any = None) -> List[Arc]:
        if k is not None:
            return self._arcs_from_specs(k, self._view_specs(k, lo, hi))
        out: List[Arc] = []
        for kk in self._bike_order:
            out.extend(self._arcs_from_specs(kk, self._view_specs(kk, lo, hi)))
        return out

    def delivery_arcs(self, i: Any, k: Any = None) -> List[Arc]:
        lo, hi = self._order_range.get(i, (0, 0))
        return self._range_arcs(lo, hi, k)

    def delivery_need(self, orders: Sequence[Any]) -> Dict[Tuple[Any, Any, int], Dict[Any, int]]:
        """``{(bike, node, t): {order: min tail level q}}`` over the delivery arcs of ``orders``
        (what ``evaluate.metric_pack`` derives from ``delivery_arcs`` for the unserved orders),
        computed per bike class without materialising arcs: delivery specs of an order are
        stored in ``(v, t, q)`` order, so the first spec of each ``(v, t)`` group carries the
        minimum level."""
        need: Dict[Tuple[Any, Any, int], Dict[Any, int]] = defaultdict(dict)
        Lq = self._Lq
        for i in orders:
            lo, hi = self._order_range.get(i, (0, 0))
            if hi <= lo:
                continue
            for c, bikes in enumerate(self.class_bikes):
                specs = self._view[c].indices(lo, hi)
                if specs.size == 0:
                    continue
                sids = self._src[specs].astype(np.int64)
                grp, first = np.unique(sids // Lq, return_index=True)
                qs = (sids[first] % Lq).tolist()
                nodes_t = [(self._nodes[int(g // (self._stride_v // Lq))], int(g % (self._stride_v // Lq))) for g in grp.tolist()]
                for k in bikes:
                    for (v, t), q in zip(nodes_t, qs):
                        need[(k, v, t)][i] = int(q)
        return need

    def swap_arcs(self, j: Any, k: Any = None) -> List[Arc]:
        lo, hi = self._swap_range.get(j, (0, 0))
        return self._range_arcs(lo, hi, k)

    def swap_arcs_at(self, j: Any, t: int, q: int, k: Any = None) -> List[Arc]:
        lo, hi = self._swap_range.get(j, (0, 0))
        if hi <= lo:
            return []
        sel = np.arange(lo, hi)[(self._l[lo:hi] == int(t)) & (self._state_q[self._src[lo:hi]] == int(q))]
        bikes = [k] if k is not None else self._bike_order
        out: List[Arc] = []
        for kk in bikes:
            out.extend(self._arcs_from_specs(kk, self._filter_view(kk, sel)))
        return out

    def terminal_arcs(self, k: Any = None) -> List[Arc]:
        lo, hi = self._block["term"]
        return self._range_arcs(lo, hi, k)

    def arcs_of_kind(self, kind: str, k: Any = None) -> List[Arc]:
        lo, hi = self._block.get(kind, (0, 0))
        return self._range_arcs(lo, hi, k)

    def find(self, k: Any, kind: str, src: Tuple, order: Any = None, fac: Any = None,
             dst: Optional[Tuple] = None) -> Optional[Arc]:
        sel = self._slice(src)
        if sel.size == 0:
            return None
        kc = _KIND_CODE.get(kind)
        if kc is None:
            return None
        kinds = self._kind[sel]
        lo = int(np.searchsorted(kinds, kc, side="left"))
        hi = int(np.searchsorted(kinds, kc, side="right"))
        if hi <= lo:
            return None
        cand = sel[lo:hi]
        if order is not None:
            oi = self._order_pos.get(order)
            if oi is None:
                return None
            cand = cand[self._oidx[cand] == oi]
        if fac is not None:
            fi = self._fac_pos.get(fac)
            if fi is None:
                return None
            cand = cand[self._fidx[cand] == fi]
        if dst is not None:
            d = self._sid_of(dst)
            if d is None:
                return None
            cand = cand[self._dst[cand] == d]
        if cand.size == 0:
            return None
        rs = self._view[self.class_of_bike[k]]
        if rs.identity:
            s = int(cand[0])
        else:
            s = -1
            for x in cand:
                if rs.test(int(x)):
                    s = int(x)
                    break
            if s < 0:
                return None
        return self._make(k, s, self._offset_of[k] + rs.rank(s))

    # ------------------------------------------------------------- summary
    def counts(self, k: Any = None) -> Dict[str, int]:
        if k is None:
            tot = np.zeros(len(KINDS), dtype=np.int64)
            for c, bikes in enumerate(self.class_bikes):
                tot += len(bikes) * self._class_counts(c)
        else:
            tot = self._class_counts(self.class_of_bike[k])
        c = {kind: int(tot[i]) for i, kind in enumerate(KINDS)}
        c["total"] = int(tot.sum())
        return c

    def _class_counts(self, c: int) -> np.ndarray:
        rs = self._view[c]
        if rs.identity:
            return np.bincount(self._kind, minlength=len(KINDS))[:len(KINDS)].astype(np.int64)
        return np.bincount(self._kind[rs.indices()], minlength=len(KINDS))[:len(KINDS)].astype(np.int64)

    def memory_bytes(self) -> int:
        """Resident bytes of the library's arrays (columns, CSR, reach words, rank/select)."""
        n = 0
        for name in ("_kind", "_src", "_dst", "_l", "_u", "_g", "_oidx", "_fidx", "_dkm", "_theta",
                     "_csr_order", "_csr_ptr", "_in_order", "_in_ptr", "_reach", "_state_t", "_state_q"):
            arr = getattr(self, name, None)
            if arr is not None:
                n += int(arr.nbytes)
        for rs in self._reach_rs:
            if not rs.identity:
                n += int(rs.words.nbytes) + int(rs.cum.nbytes)
        return n

    def summary(self) -> Dict[str, Any]:
        per_class = {c: self._class_counts(c) for c in range(self.n_classes)}
        n_states_c = {}
        for c in range(self.n_classes):
            specs = self._view[c].indices()
            n_states_c[c] = int(np.unique(np.concatenate([self._src[specs], self._dst[specs]])).size + 2 if specs.size else 2)

        def cnt(c: int) -> Dict[str, int]:
            d = {kind: int(per_class[c][i]) for i, kind in enumerate(KINDS)}
            d["total"] = int(per_class[c].sum())
            return d
        return {
            "library_mode": "union",
            "n_bikes": len(self.inst.bikes),
            "n_arcs": self._n_total,
            "n_specs": self.n_specs,
            "n_template_specs": self.n_template_specs,
            "n_union_states": self.n_states_used,
            "n_classes": self.n_classes,
            "classes": [{"source": str(self.class_source[c]), "n_bikes": len(self.class_bikes[c]),
                         "n_arcs": int(self._view[c].count), "n_reachable_specs": int(self._reach_rs[c].count),
                         "has_real_terminal": self.class_has_term[c]} for c in range(self.n_classes)],
            "per_kind": self.counts(),
            "per_bike": {k: cnt(self.class_of_bike[k]) for k in self.bikes()},
            "n_states": {k: n_states_c[self.class_of_bike[k]] for k in self.bikes()},
            "infeasible_bikes": list(self.infeasible_bikes),
            "options": {key: (sorted(map(str, val)) if isinstance(val, set) else val)
                        for key, val in self.options.items()},
            "memory_mb": round(self.memory_bytes() / 2 ** 20, 1),
            "timings_s": {k: round(v, 3) for k, v in self.timings.items()},
        }


def build_union_arcs(inst: Instance, strict: bool = True, **overrides: Any) -> UnionArcLibrary:
    """Build the :class:`UnionArcLibrary` of ``inst`` (same options and semantics as
    :func:`build_arcs`; ``library_mode`` is set to ``'union'`` in ``lib.options`` so that a
    rebuild from ``lib.options`` stays in union mode).  ``strict`` as in :func:`build_arcs`."""
    import time as _time

    opts = dict(DEFAULT_OPTIONS)
    opts.update(inst.options)
    opts.update(overrides)
    opts["library_mode"] = "union"
    if opts.get("reposition_targets") is not None:
        opts["reposition_targets"] = set(opts["reposition_targets"])
    t0 = _time.perf_counter()
    gbar = compute_gbar(inst)
    lib = UnionArcLibrary(inst, opts, gbar)
    t1 = _time.perf_counter()
    lib._build()
    lib.timings["gbar"] = t1 - t0
    lib.timings["total"] = _time.perf_counter() - t0
    if lib.infeasible_bikes and strict and not lib.has_dummy_terminal:
        raise InfeasibleInstanceError(
            "no reachable terminal arc (9) for bikes " + ", ".join(map(str, lib.infeasible_bikes))
            + ": raise q0, add routes/swap sites, lower q_res, or set options.dummy_terminal_cost")
    return lib
