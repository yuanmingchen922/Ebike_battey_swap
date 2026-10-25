"""Aggregated integer-flow implementation of E2 (plan item O1, ``notes/reading_to_model.md``;
source: ITSC-21 Sec. II-c).

Why it is exact
---------------
In E2 nothing but the arc set ``A_k`` and the source ``s_k = (v0_k, 0, q0_k)`` depends
on the bike index ``k``: arc costs (29)-(30) and every coupling row that touches ``x``
((6) orders, (9) terminal, (12) swap counts, (22) swap positions) are sums over ``k``
of per-arc terms whose coefficients depend on the action only (``arcs.arc_key``).  The
per-bike unit flows (5) can therefore be replaced by integer flows on the union
``(v, t, q)`` network:

* bikes whose arc sets coincide and whose sources coincide form a class; a class
  is a *commodity* with supply ``m_c`` = number of its bikes;
* if every class is *closed* (every union arc whose tail is reachable from the class
  source through union arcs belongs to the class's own arc set, which holds without
  pruning and with ``reachable_pruning``, because pruning only removes arcs whose tail
  is unreachable), all classes share ONE network with supplies ``m_c`` at their
  sources (``mode='single'``); otherwise every class keeps its own copy
  (``mode='groups'``, still ``|classes| <= |K|`` copies);
* integer arc flows ``X_a in {0..U_a}``; rows (5) become ``out - in = supply(w)``
  (``-sum m_c`` at the sink); (6) ``sum X_a + u_i = 1`` (so deliver arcs are binary);
  (9) ``sum_{a in term(j)} X_a <= U_j y_j``; (12), (22), (29), (30) unchanged with
  ``X_a`` in place of ``sum_k x_ka``.

Every integer feasible aggregated flow decomposes into ``|K|`` source-to-sink paths
(the network is acyclic: every non-terminal arc strictly increases ``t``), and each
path starting at ``s_c`` uses only arcs of class ``c`` (closure), so assigning the
paths to the bikes of the class gives a per-bike schedule with the same value of
every E2 row and of (26); conversely summing a per-bike schedule gives an aggregated
flow.  Both models therefore have the same optimum (E2 equations unchanged).  The
only LP difference is (9): the per-bike rows ``sum_a x_ka <= y_j`` are summed, so with
free ``y_j`` the aggregated LP bound can be weaker (it is identical when facilities are
fixed, as in the E2u / E8 families).

Arcs that can carry no flow in any (LP or integer) feasible solution are dropped
(tail unreachable from every source, or head unable to reach the sink); this is
lossless.

This module does not import gurobipy; the Gurobi side is ``ilp.build_model(...,
aggregate=True)`` and ``ilp.build_submodel(..., aggregate=True)``.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .arcs import SINK, Arc, ArcLibrary, arc_key
from .or_instance import Instance

__all__ = ["AggregatedNetwork", "Commodity", "AggregationError", "AGG_MODES",
           "aggregate_network", "decompose_flow"]

AGG_MODES = ("auto", "single", "groups")

State = Tuple[Any, ...]
Key = Tuple[str, Tuple, Tuple, Any, Any]


class AggregationError(ValueError):
    """The arc library cannot be aggregated in the requested mode (e.g. ``mode='single'``
    on a library whose bike classes are not closed), or a flow does not decompose."""


@dataclass
class Commodity:
    """One flow commodity of the aggregated model (O1).

    ``id`` is the commodity index (``Arc.k`` of its aggregated arcs), ``bikes`` the
    bike ids in ``inst.bikes`` order, ``supply`` ``{source state: number of bikes}``
    (one entry per class merged into this commodity), ``arc_ids`` the aggregated arc
    ids of the commodity."""
    id: int
    bikes: List[Any]
    supply: Dict[State, int]
    arc_ids: List[int] = field(default_factory=list)

    @property
    def m(self) -> int:
        """Total supply ``m_c`` (number of bikes) of the commodity."""
        return int(sum(self.supply.values()))


def _forward(src: Iterable[State], out_adj: Mapping[State, Sequence[int]],
             dst_of: Sequence[State], allowed: Optional[Set[int]] = None) -> Set[State]:
    seen: Set[State] = set(src)
    stack = list(seen)
    while stack:
        s = stack.pop()
        for idx in out_adj.get(s, ()):
            if allowed is not None and idx not in allowed:
                continue
            d = dst_of[idx]
            if d not in seen:
                seen.add(d)
                stack.append(d)
    return seen


class AggregatedNetwork:
    """Union ``(v, t, q)`` network of an :class:`~ebike_swap_sim.arcs.ArcLibrary` with
    commodity supplies (plan item O1; E2 (5), (6), (9), (12), (22), (29)-(30)).

    Parameters
    ----------
    inst, lib
        The instance and its per-bike arc library (``lib.inst`` must be ``inst``).
    mode
        ``'auto'`` (default): one network if every bike class is closed, else one copy
        per class; ``'single'``: one network, :class:`AggregationError` if a class is
        not closed; ``'groups'``: one copy per class (always exact).
    prune
        Drop arcs that cannot carry flow (lossless; default ``True``).

    Attributes
    ----------
    arcs
        ``list[Arc]`` of aggregated arcs: ``Arc.id`` is the aggregated id (position),
        ``Arc.k`` the commodity id, every other field as in the per-bike library.
    commodities
        ``list[Commodity]``.
    ub
        Per aggregated arc the upper bound ``U_a`` (``1`` on deliver arcs, else the
        number of bikes whose source reaches the tail).
    term_ub
        ``{(c, j): U}`` for (9): number of bikes of commodity ``c`` that can reach a
        terminal arc labelled ``j``.
    mode, requested_mode, classes, closed, n_bike_arcs, n_dropped
        Diagnostics (see :meth:`summary`).
    """

    def __init__(self, inst: Instance, lib: ArcLibrary, mode: str = "auto",
                 prune: bool = True) -> None:
        if mode not in AGG_MODES:
            raise ValueError(f"mode must be one of {AGG_MODES}, got {mode!r}")
        if lib.inst is not inst and lib.inst != inst:
            raise ValueError("the arc library was built on a different instance")
        self.inst = inst
        self.lib = lib
        self.requested_mode = mode
        self.n_bike_arcs = len(lib)

        # ---------------------------------------------- union arcs (first copy wins)
        uid_of: Dict[Key, int] = {}
        union: List[Arc] = []
        bike_uids: Dict[Any, List[int]] = {}
        for b in inst.bikes:
            uids: List[int] = []
            for a in lib.arcs_of(b.id):
                key = arc_key(a)
                u = uid_of.get(key)
                if u is None:
                    u = len(union)
                    uid_of[key] = u
                    union.append(a)
                else:
                    r = union[u]
                    if (r.l, r.u, r.g) != (a.l, a.u, a.g) or abs(r.d_km - a.d_km) > 1e-12 \
                            or abs(r.theta - a.theta) > 1e-12:
                        raise AggregationError(
                            f"arc {a.id} of bike {a.k} and arc {r.id} of bike {r.k} share the key "
                            f"{key} but differ in (l, u, g, d_km, theta): the action is bike-specific")
                uids.append(u)
            bike_uids[b.id] = uids
        dst_of = [a.dst for a in union]
        src_of = [a.src for a in union]
        out_adj: Dict[State, List[int]] = defaultdict(list)
        in_adj: Dict[State, List[int]] = defaultdict(list)
        for u, a in enumerate(union):
            out_adj[a.src].append(u)
            in_adj[a.dst].append(u)

        # ---------------------------------------------- bike classes (source, arc set)
        cls_index: Dict[Tuple[State, Tuple[int, ...]], int] = {}
        classes: List[Dict[str, Any]] = []
        for b in inst.bikes:
            src = lib.source(b.id)
            sig = (src, tuple(bike_uids[b.id]))
            ci = cls_index.get(sig)
            if ci is None:
                ci = len(classes)
                cls_index[sig] = ci
                classes.append({"source": src, "bikes": [], "uids": bike_uids[b.id]})
            classes[ci]["bikes"].append(b.id)
        del cls_index, bike_uids

        # backward co-reachability of the sink (an arc whose head cannot reach the
        # sink carries no flow in any feasible solution)
        if prune:
            co: Set[State] = {SINK}
            stack: List[State] = [SINK]
            while stack:
                s = stack.pop()
                for u in in_adj.get(s, ()):
                    t = src_of[u]
                    if t not in co:
                        co.add(t)
                        stack.append(t)
        else:
            co = set()

        # ---------------------------------------------- closure test
        closed = True
        reach_union: List[Set[State]] = []
        for cl in classes:
            r = _forward([cl["source"]], out_adj, dst_of)
            reach_union.append(r)
            own = set(cl["uids"])
            if closed:
                for u in range(len(union)):
                    if src_of[u] in r and u not in own:
                        closed = False
                        break
        self.closed = closed
        if mode == "single" and not closed:
            raise AggregationError("mode='single' requested but some bike class is not closed "
                                   "(its arc set misses union arcs reachable from its source)")
        eff = "single" if (mode == "single" or (mode == "auto" and closed)) else "groups"
        self.mode = eff
        self.classes = [{"source": cl["source"], "bikes": list(cl["bikes"]), "n_arcs": len(cl["uids"])}
                        for cl in classes]

        # ---------------------------------------------- aggregated arcs
        self.arcs: List[Arc] = []
        self.ub: List[int] = []
        self.commodities: List[Commodity] = []
        self.term_ub: Dict[Tuple[int, Any], int] = {}
        self._index: Dict[Tuple[int, Key], int] = {}
        self._commodity_of_bike: Dict[Any, int] = {}

        def emit(c: int, u: int, bound: int) -> None:
            a = union[u]
            new = Arc(len(self.arcs), c, a.kind, a.src, a.dst, a.l, a.u, a.d_km, a.g,
                      a.order, a.fac, a.theta)
            self._index[(c, arc_key(a))] = new.id
            self.arcs.append(new)
            self.ub.append(1 if a.kind == "deliver" else int(bound))
            self.commodities[c].arc_ids.append(new.id)

        def keep(u: int, reach: Set[State]) -> bool:
            if src_of[u] not in reach:
                return False
            return (not prune) or dst_of[u] in co

        if eff == "single":
            bikes = [b.id for b in inst.bikes]
            supply: Dict[State, int] = defaultdict(int)
            for cl in classes:
                supply[cl["source"]] += len(cl["bikes"])
            self.commodities.append(Commodity(0, bikes, dict(supply)))
            for k in bikes:
                self._commodity_of_bike[k] = 0
            all_reach: Set[State] = set().union(*reach_union) if reach_union else set()
            # U_a = bikes whose source reaches the tail of a
            reach_count: Dict[State, int] = defaultdict(int)
            for cl, r in zip(classes, reach_union):
                for s in r:
                    reach_count[s] += len(cl["bikes"])
            for u in range(len(union)):
                if keep(u, all_reach):
                    emit(0, u, reach_count[src_of[u]])
            for cl, r in zip(classes, reach_union):
                facs = {union[u].fac for u in range(len(union))
                        if union[u].kind == "term" and union[u].fac is not None and src_of[u] in r}
                for j in facs:
                    self.term_ub[(0, j)] = self.term_ub.get((0, j), 0) + len(cl["bikes"])
        else:
            for ci, cl in enumerate(classes):
                self.commodities.append(Commodity(ci, list(cl["bikes"]), {cl["source"]: len(cl["bikes"])}))
                for k in cl["bikes"]:
                    self._commodity_of_bike[k] = ci
                own = set(cl["uids"])
                r = _forward([cl["source"]], out_adj, dst_of, allowed=own)
                m_c = len(cl["bikes"])
                facs: Set[Any] = set()
                for u in cl["uids"]:
                    if keep(u, r):
                        emit(ci, u, m_c)
                        if union[u].kind == "term" and union[u].fac is not None:
                            facs.add(union[u].fac)
                for j in facs:
                    self.term_ub[(ci, j)] = m_c
        self.n_dropped = (len(union) if eff == "single" else sum(len(cl["uids"]) for cl in classes)) \
            - len(self.arcs)
        self.n_union = len(union)

    # ------------------------------------------------------------- lookups
    def __len__(self) -> int:
        return len(self.arcs)

    def commodity_of(self, k: Any) -> int:
        """Commodity id of bike ``k``."""
        return self._commodity_of_bike[k]

    def sources(self, c: int) -> Dict[State, int]:
        """``{source state: supply}`` of commodity ``c`` (right-hand sides of (5))."""
        return dict(self.commodities[c].supply)

    def agg_id(self, k: Any, a: Arc) -> Optional[int]:
        """Aggregated arc id that carries the per-bike arc ``a`` of bike ``k``
        (``None`` if the arc was dropped as unable to carry flow)."""
        return self._index.get((self._commodity_of_bike[k], arc_key(a)))

    def summary(self) -> Dict[str, Any]:
        """Sizes and mode: ``mode``, ``requested_mode``, ``closed``, ``n_bike_arcs``
        (per-bike library), ``n_union`` (distinct keys), ``n_agg_arcs`` (variables),
        ``n_dropped`` (lossless drops), ``reduction`` (``n_bike_arcs / n_agg_arcs``),
        ``n_commodities``, ``n_classes``, ``supplies``."""
        return {
            "mode": self.mode, "requested_mode": self.requested_mode, "closed": self.closed,
            "n_bike_arcs": self.n_bike_arcs, "n_union": self.n_union, "n_agg_arcs": len(self.arcs),
            "n_dropped": self.n_dropped,
            "reduction": (self.n_bike_arcs / len(self.arcs)) if self.arcs else None,
            "n_commodities": len(self.commodities), "n_classes": len(self.classes),
            "supplies": [{str(s): m for s, m in c.supply.items()} for c in self.commodities],
        }

    # ------------------------------------------------------------- mapping
    def aggregate_x(self, x: Mapping[Any, Iterable[int]]) -> Tuple[Dict[int, int], List[Tuple[Any, int]]]:
        """Sum a per-bike arc selection ``{bike: [lib arc ids]}`` into aggregated flows
        ``{agg id: X_a}`` (O1; the map behind a MIP start).  Returns ``(flows, missing)``
        where ``missing`` lists ``(bike, lib arc id)`` pairs whose arc has no aggregated
        counterpart (dropped as unable to carry flow, so the selection is infeasible)."""
        flows: Dict[int, int] = defaultdict(int)
        missing: List[Tuple[Any, int]] = []
        for k, ids in x.items():
            for i in ids:
                a = self.lib.arc(int(i))
                aid = self.agg_id(k, a)
                if aid is None:
                    missing.append((k, int(i)))
                else:
                    flows[aid] += 1
        return dict(flows), missing

    def decompose(self, values: Mapping[int, float] | Sequence[float], tol: float = 1e-6) -> Dict[Any, List[int]]:
        """Flow decomposition (O1): split the integer aggregated flow ``values`` (by
        aggregated arc id) into one source-to-sink path per bike and return the per-bike
        selection ``{bike: [lib arc ids]}`` of the original :class:`ArcLibrary`, so that
        ``evaluate.check`` / ``evaluate.cost`` apply unchanged (E2 (5) per bike; (6),
        (9), (12), (22), (29)-(30) keep their values because they are arc sums).

        Deterministic: bikes in ``inst.bikes`` order, out-arcs in aggregated id order.
        Raises :class:`AggregationError` if a value is fractional beyond ``tol``, the
        flow does not conserve, or flow is left after all bikes are routed."""
        if isinstance(values, Mapping):
            get = values.get
        else:
            seq = values
            get = lambda i, d=0.0: seq[i]  # noqa: E731
        out: Dict[Any, List[int]] = {b.id: [] for b in self.inst.bikes}
        for com in self.commodities:
            rem: Dict[int, int] = {}
            adj: Dict[State, List[int]] = defaultdict(list)
            for aid in com.arc_ids:
                v = float(get(aid, 0.0))
                r = int(round(v))
                if abs(v - r) > tol:
                    raise AggregationError(f"aggregated arc {aid} carries fractional flow {v}")
                if r < 0:
                    raise AggregationError(f"aggregated arc {aid} carries negative flow {v}")
                if r > 0:
                    rem[aid] = r
                    adj[self.arcs[aid].src].append(aid)
            ptr: Dict[State, int] = defaultdict(int)
            for k in com.bikes:
                node = self.lib.source(k)
                path: List[int] = []
                while node != SINK:
                    lst = adj.get(node, ())
                    p = ptr[node]
                    while p < len(lst) and rem[lst[p]] == 0:
                        p += 1
                    ptr[node] = p
                    if p >= len(lst):
                        raise AggregationError(
                            f"flow decomposition stuck at {node} for bike {k} (commodity {com.id}): "
                            f"the aggregated flow violates (5)")
                    aid = lst[p]
                    rem[aid] -= 1
                    path.append(aid)
                    node = self.arcs[aid].dst
                out[k] = [self._lib_arc_id(k, aid) for aid in path]
            left = {a: r for a, r in rem.items() if r}
            if left:
                raise AggregationError(f"flow left after routing every bike of commodity {com.id}: "
                                       f"{list(left.items())[:5]}")
        return out

    def _lib_arc_id(self, k: Any, aid: int) -> int:
        a = self.arcs[aid]
        key = arc_key(a)
        for b in self.lib.out_arcs(k, a.src):
            if arc_key(b) == key:
                return b.id
        raise AggregationError(f"bike {k} has no arc with key {key} (class closure violated)")


def aggregate_network(inst: Instance, lib: ArcLibrary, mode: str = "auto",
                      prune: bool = True) -> AggregatedNetwork:
    """Build the :class:`AggregatedNetwork` of ``lib`` (plan item O1; E2 (5), (6), (9),
    (12), (22), (29)-(30) on the union network).  Alias of the constructor."""
    return AggregatedNetwork(inst, lib, mode=mode, prune=prune)


def decompose_flow(net: AggregatedNetwork, values: Mapping[int, float] | Sequence[float]) -> Dict[Any, List[int]]:
    """Per-bike arc selection from an aggregated integer flow (plan item O1; per-bike
    E2 (5) restored by path decomposition).  See :meth:`AggregatedNetwork.decompose`."""
    return net.decompose(values)
