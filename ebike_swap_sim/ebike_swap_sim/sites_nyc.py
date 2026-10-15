"""Candidate sites and layout instances for the bi-level siting study
(``notes/bilevel_siting_design.md`` sections 4-5).

This module only produces :class:`~ebike_swap_sim.or_instance.Instance` data; the
E2 mathematics (``arcs.py``, ``ilp.py``, ``evaluate.py``) is untouched.  The upper-level
(planner) objects live in :mod:`ebike_swap_sim.bilevel`, which imports this module.

* :func:`candidate_sites` -- the candidate locations ``Lambda`` of the Midtown / Chelsea /
  Flatiron box: (i) the busiest DOHMH restaurant cells, (ii) landmark coordinates (the E8
  'grid-connected' sites and Penn Station) and (iii) the centres of the heaviest ACS
  demand zones, deduplicated to distinct grid nodes and merged below ``min_sep_blocks``.
* :class:`SitingSpec` -- role parameters (``S`` swap-only, ``C`` charge-only hub, ``SC``
  co-located), window-allocated and investment cost coefficients, the transfer timetable
  and the grid group; :func:`spec_from_instance` reads the coefficients of a built
  instance (``meta['costs']``), :data:`TOY_SPEC` is a unit-free spec for tests.
* :func:`make_base_instance` -- the energy-stressed ``nyc4h_stress`` instance of a seed
  with every candidate in ``V`` and NO facilities / services (bikes start at the three
  busiest cells, ``depots``), so that the demand side is byte-identical across layouts.
* :func:`layout_instance` -- the base plus one :class:`Facility` per open ``(l, r, B, C)``
  (facilities fixed) and the shuttle services between charge-capable and swap-capable
  objects at different locations; :func:`all_candidates_instance` -- every role object
  of every candidate with ``y, B, C`` free (the integrated model) or all open (the
  superset bound); :func:`siting_pruning` -- the arc-builder options shared by every
  layout of a scenario (``targets='all_candidates'``: reposition targets = all candidate
  nodes + depots, so that the lower-level libraries of different layouts are sub-libraries
  of one template and the integrated model and the enumerated layouts price exactly the
  same arcs; ``targets='open_sites'``: open facility nodes + depots, the per-layout
  libraries of the search algorithms, E8 convention); :func:`layout_admissible` -- the
  structural rules (a swap-capable object; swap-only sites only next to a C / SC object).
* Families: :data:`STRESS_PARAMS` (``nyc4h_stress``, 8 bikes, the first E9 attempt) and
  :data:`STRESS2_PARAMS` (``nyc4h_stress2``, 6 bikes, the relaunch), :data:`SIZE_MENUS`.
* :func:`subset_library` -- the arc library of a layout instance derived from the
  all-candidates library of the same scenario (identical to ``build_arcs`` on the layout
  instance, asserted in ``tests/test_bilevel.py``) without re-templating 1-2 M arcs.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .arcs import ArcLibrary, compute_gbar
from .generator import _node, _py
from .or_instance import Facility, Instance, Node, Service

__all__ = [
    "ROLES", "ROLE_SWAP", "ROLE_CHARGE", "LANDMARKS", "STRESS_FAMILY", "STRESS_PARAMS", "STRESS2_FAMILY", "STRESS2_PARAMS",
    "SITING_FAMILIES", "SIZE_MENUS", "STRESS_PRUNING", "REPOSITION_MODES", "Candidate", "SitingSpec",
    "DEFAULT_SPEC", "TOY_SPEC", "spec_from_instance", "candidate_sites", "candidates_to_records",
    "candidates_from_records", "make_base_instance", "toy_base_instance", "layout_items", "layout_instance",
    "all_candidates_instance", "siting_pruning", "subset_library", "facility_id", "split_facility_id",
    "manhattan_blocks", "layout_admissible", "reposition_targets",
]

#: Facility roles of the planner (design section 2.1): ``S`` swap-only, ``C`` charge-only
#: hub, ``SC`` co-located; ``(l, r)`` is one E2 facility object with the ``swap`` / ``charge`` flags.
ROLES: Tuple[str, ...] = ("S", "C", "SC")
ROLE_SWAP: Dict[str, bool] = {"S": True, "C": False, "SC": True}
ROLE_CHARGE: Dict[str, bool] = {"S": False, "C": True, "SC": True}

#: Landmark candidates (WGS84): the E8 'grid-connected' siting plus Penn Station.
LANDMARKS: Dict[str, Tuple[float, float]] = {
    "8th Ave / W 34th St": (40.75270, -73.99370),
    "Union Square": (40.73590, -73.99110),
    "Grand Central Terminal": (40.75270, -73.97720),
    "Penn Station (7th Ave / W 32nd)": (40.75050, -73.99340),
}

#: Instance family of the siting study (``experiments.common.FAMILIES['nyc4h_stress']`` is
#: built from these keyword arguments of ``data_nyc.make_nyc_instance``; design section 5,
#: E2_formulation_review proposal SC-1): 8 bikes / 48 orders / H 48, ``q0 ~ U{2..4}`` of 12,
#: one spare and one 1.4 kW charger per site (``Cbar 4``), a flat 4 kW grid group.
STRESS_FAMILY = "nyc4h_stress"
STRESS_PARAMS: Dict[str, Any] = {
    "n_bikes": 8, "window_h": 4.0, "orders_per_bike_hour": 1.5, "L": 12, "n_sites": 3,
    "cost_variant": "usd_sunk",
    "demand_spec": {"init_frac": (2.0 / 12.0, 4.0 / 12.0)},
    "facilities_spec": {"B": 1, "C": 1, "P_kw": 1.4, "Cbar": 4, "grid_sites_kw": 4.0, "grid_sites_peak_kw": 4.0},
}
#: 'Stressed but sane' family of the E9 relaunch (``notes/DECISIONS.md``, E9 relaunch decisions):
#: 6 bikes / 36 orders / H 48, ``q0 ~ U{3..6}`` of 12 (150-300 Wh, 2-4 deliveries), the same one
#: spare / one charger / ``Cbar 4`` / flat 4 kW grid group as ``nyc4h_stress``; the site power cap
#: is 2.8 kW so that a charge-only hub can run its 4 chargers (``4 x 0.667 kW``; with 1.4 kW the
#: ``C = 4`` option would be dominated), while the 4 kW group still caps the network at 6
#: simultaneous charges.  Size menu :data:`SIZE_MENUS` ``['nyc4h_stress2']``: ``S: B in {1, 2, 3}``,
#: ``SC: B in {1, 2, 3} x C in {1, 2}``, hubs ``C in {2, 4}``; swap-only sites are admissible only
#: when at least one charge-capable (C or SC) object is open (:func:`layout_admissible`).
STRESS2_FAMILY = "nyc4h_stress2"
STRESS2_PARAMS: Dict[str, Any] = {
    "n_bikes": 6, "window_h": 4.0, "orders_per_bike_hour": 1.5, "L": 12, "n_sites": 3,
    "cost_variant": "usd_sunk",
    "demand_spec": {"init_frac": (3.0 / 12.0, 6.0 / 12.0)},
    "facilities_spec": {"B": 1, "C": 1, "P_kw": 2.8, "Cbar": 4, "grid_sites_kw": 4.0, "grid_sites_peak_kw": 4.0},
}
#: Families :func:`make_base_instance` can build (``family -> make_nyc_instance`` keyword arguments).
SITING_FAMILIES: Dict[str, Dict[str, Any]] = {STRESS_FAMILY: STRESS_PARAMS, STRESS2_FAMILY: STRESS2_PARAMS}
#: Size menus of the greedy / local search per family (``role -> [(B, C), ...]``).
SIZE_MENUS: Dict[str, Dict[str, List[Tuple[int, int]]]] = {
    STRESS_FAMILY: {"S": [(1, 0), (2, 0), (3, 0)], "C": [(0, 1), (0, 2)],
                    "SC": [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)]},
    STRESS2_FAMILY: {"S": [(1, 0), (2, 0), (3, 0)], "C": [(0, 2), (0, 4)],
                     "SC": [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)]},
}
#: Arc-builder pruning of the semi-real instances (``experiments.common.PRUNING_NYC`` values).
STRESS_PRUNING: Dict[str, Any] = {"tau_max": 4, "start_slack": 6, "reachable": True}
#: Reposition-target conventions of :func:`siting_pruning`: ``'all_candidates'`` (moves into every
#: candidate node + depots; one template library per scenario, every layout a sub-library of it;
#: the integrated model (A) and the exhaustive enumeration (B) of E9.1 price exactly the same arcs)
#: and ``'open_sites'`` (moves only into the OPEN facility nodes + depots, the E8 ``targets =
#: 'facilities'`` convention; smaller libraries per layout, used by the search algorithms (C)-(E);
#: a sub-library of the all-candidates one, so its ILP totals are upper bounds on the
#: all-candidates values and the superset bound stays valid).
REPOSITION_MODES: Tuple[str, ...] = ("all_candidates", "open_sites")


def _grid_node(n: Any) -> Node:
    """Node decoding tolerant of scalar (toy) node ids: lists become tuples, scalars stay."""
    return _node(n) if isinstance(n, (list, tuple)) else n


def facility_id(loc: str, role: str) -> str:
    """Facility id of the role object ``(l, r)``: ``'L01:SC'``."""
    return f"{loc}:{role}"


def split_facility_id(fid: str) -> Tuple[str, str]:
    """Inverse of :func:`facility_id`."""
    loc, role = str(fid).rsplit(":", 1)
    return loc, role


def manhattan_blocks(a: Node, b: Node) -> int:
    """Manhattan distance of two grid nodes in blocks (scalar nodes: absolute difference)."""
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return sum(abs(int(x) - int(y)) for x, y in zip(a, b))
    return abs(int(a) - int(b))


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------
@dataclass
class Candidate:
    """One candidate location ``l`` of the planner.

    ``id`` (``'L01'``), ``label``, ``source`` in ``{'busiest', 'landmark', 'zone'}``,
    ``lat, lon`` (WGS84 of the generating point), ``node`` (grid node ``(ix, iy)``),
    ``grid_connected`` (a landmark of the E8 'grid-connected' siting, or a cell into
    which one was merged), ``n_restaurants`` (DOHMH rows snapped to the node),
    ``merged_labels`` (labels of candidates merged into this one), ``zone`` (NTA code for
    zone-centre candidates), ``rank`` (position in the generating list).
    """
    id: str
    label: str
    source: str
    lat: float
    lon: float
    node: Node
    grid_connected: bool = False
    n_restaurants: int = 0
    merged_labels: List[str] = field(default_factory=list)
    zone: Optional[str] = None
    rank: int = 0

    def to_record(self) -> Dict[str, Any]:
        d = asdict(self)
        d["node"] = list(self.node) if isinstance(self.node, tuple) else self.node
        return _py(d)

    @classmethod
    def from_record(cls, d: Dict[str, Any]) -> "Candidate":
        d = dict(d)
        d["node"] = _grid_node(d["node"])
        return cls(**d)


def candidates_to_records(cands: Sequence[Candidate]) -> List[Dict[str, Any]]:
    return [c.to_record() for c in cands]


def candidates_from_records(recs: Iterable[Dict[str, Any]]) -> List[Candidate]:
    return [Candidate.from_record(r) for r in recs]


def candidate_sites(box: Any = None, n_busiest: int = 6, landmarks: Optional[Dict[str, Tuple[float, float]]] = None,
                    n_zones: int = 3, min_sep_blocks: int = 2, busiest_sep_blocks: int = 4,
                    restaurants: Any = None, zone_weights: Any = None) -> List[Candidate]:
    """Candidate set ``Lambda`` of the design (section 4), recomputed from the data files.

    Sources, in order: (i) the ``n_busiest`` DOHMH restaurant cells
    (:func:`data_nyc.busiest_restaurant_cells` with ``busiest_sep_blocks``); (ii) the
    ``landmarks`` (default :data:`LANDMARKS`); (iii) the centres of the ``n_zones``
    heaviest demand zones (sampler mass of :class:`data_nyc.NYCDestinationSampler`;
    centre = the support node nearest to the mean of the zone's in-box nodes).  Rules:
    candidates are deduplicated to distinct grid nodes, and two candidates closer than
    ``min_sep_blocks`` (Manhattan) are merged into the one with more restaurants (ties:
    the earlier one), the merged labels being kept in ``merged_labels``; ids ``L01..``
    follow the surviving order.  Deterministic.
    """
    import numpy as np
    from . import data_nyc as dn

    box = box or dn.DEFAULT_BOX
    landmarks = dict(LANDMARKS if landmarks is None else landmarks)
    rest = dn.restaurants_in_box(box) if restaurants is None else restaurants
    counts: Dict[Node, int] = {}
    for v in rest["node"]:
        counts[_node(v)] = counts.get(_node(v), 0) + 1
    raw: List[Candidate] = []
    rank = 0
    for v in dn.busiest_restaurant_cells(rest, int(n_busiest), int(busiest_sep_blocks)):
        lat, lon = box.node_latlon(v)
        rank += 1
        raw.append(Candidate(id="", label=f"busiest cell {rank}", source="busiest", lat=float(lat), lon=float(lon),
                             node=v, grid_connected=False, n_restaurants=counts.get(v, 0), rank=rank))
    for label, (lat, lon) in landmarks.items():
        v = box.snap(float(lat), float(lon))
        rank += 1
        raw.append(Candidate(id="", label=label, source="landmark", lat=float(lat), lon=float(lon), node=v,
                             grid_connected=True, n_restaurants=counts.get(v, 0), rank=rank))
    if n_zones > 0:
        zw = zone_weights if zone_weights is not None else dn.default_zone_weights(box)
        dest = dn.NYCDestinationSampler(box, zw, np.random.default_rng(0))
        totals = {k: v for k, v in dest.zone_totals().items() if k is not None}
        support = set(dest.support)
        for code, _mass in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:int(n_zones)]:
            nodes = [v for v in dest.nodes if dest.node_zone_code.get(v) == code and box.contains(*dest.node_latlon[v])]
            if not nodes:
                continue
            mx = sum(box.node_xy(v)[0] for v in nodes) / len(nodes)
            my = sum(box.node_xy(v)[1] for v in nodes) / len(nodes)
            pool = [v for v in nodes if v in support] or nodes
            centre = min(pool, key=lambda v: ((box.node_xy(v)[0] - mx) ** 2 + (box.node_xy(v)[1] - my) ** 2, v))
            lat, lon = box.node_latlon(centre)
            rank += 1
            raw.append(Candidate(id="", label=f"zone centre {code}", source="zone", lat=float(lat), lon=float(lon),
                                 node=centre, grid_connected=False, n_restaurants=counts.get(centre, 0),
                                 zone=str(code), rank=rank))
    # dedup / merge --------------------------------------------------------------
    kept: List[Candidate] = []
    for c in raw:
        near = [k for k in kept if manhattan_blocks(k.node, c.node) < int(min_sep_blocks)]
        if not near:
            kept.append(c)
            continue
        host = near[0]
        if c.n_restaurants > host.n_restaurants:
            # the newcomer has more restaurants: it becomes the host and absorbs the old one
            idx = kept.index(host)
            c.merged_labels = list(host.merged_labels) + [host.label] + list(c.merged_labels)
            c.grid_connected = c.grid_connected or host.grid_connected
            kept[idx] = c
        else:
            host.merged_labels.append(c.label)
            host.grid_connected = host.grid_connected or c.grid_connected
    for i, c in enumerate(kept):
        c.id = f"L{i + 1:02d}"
    return kept


# ---------------------------------------------------------------------------
# spec
# ---------------------------------------------------------------------------
@dataclass
class SitingSpec:
    """Role parameters and cost coefficients of the siting study (design section 4,
    table 'Role parameters'): per role object ``K, Cbar, M, sigma, P_kw, R_end``; the
    window-allocated setup costs ``F`` (S / SC), ``F_hub`` (C), ``bB``, ``bC`` (27); the
    investment coefficients ``Fhat, bhat, chat`` (33); the transfer timetable (``every``,
    ``first``, ``handling_min``, ``U``, ``f``, ``vreb``, optional ``max_pair_km``); the grid
    group ``grid_kw`` (flat) and the swap-only end target ``R_end_S`` (1 written, 0 = SC-4
    sensitivity).  ``Delta_min`` is needed for the service durations."""
    K: int = 8
    Cbar: int = 4
    M: int = 1
    sigma: int = 1
    P_kw: float = 1.4
    R_end_S: int = 1
    R_end_SC: int = 1
    F: float = 12.03
    F_hub: float = 29.19
    bB: float = 0.332
    bC: float = 0.082
    Fhat: float = 50_000.0
    bhat: float = 450.0
    chat: float = 400.0
    every: int = 6
    first: int = 2
    handling_min: float = 10.0
    U: int = 6
    f: float = 20.0
    vreb: float = 1.0
    max_pair_km: Optional[float] = None
    grid_kw: float = 4.0
    grid_group: str = "sites"
    Delta_min: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return _py(asdict(self))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SitingSpec":
        return cls(**d)

    def setup_cost(self, role: str) -> float:
        return float(self.F_hub if role == "C" else self.F)

    def R_end(self, role: str) -> int:
        return {"S": int(self.R_end_S), "SC": int(self.R_end_SC), "C": 0}[role]

    def c_min(self, role: str) -> int:
        """Lower bound on ``C_j`` of an open object: (8) ``C_j >= y_j`` for ``j in C \\ S``."""
        return 1 if role == "C" else 0

    def c_max(self, role: str) -> int:
        return int(min(self.Cbar, self.K)) if ROLE_CHARGE[role] else 0

    def valid_sizes(self, role: str, B: int, C: int) -> bool:
        return 0 <= int(B) <= self.K and self.c_min(role) <= int(C) <= self.c_max(role)

    def facility(self, cand_id: str, node: Node, role: str, B: Optional[int], C: Optional[int],
                 y: Optional[int]) -> Facility:
        """One E2 facility object; ``None`` sizes are free (the integrated model)."""
        if role not in ROLES:
            raise ValueError(f"unknown role {role!r}")
        charge = ROLE_CHARGE[role]
        return Facility(
            id=facility_id(cand_id, role), node=node, swap=ROLE_SWAP[role], charge=charge, y=y,
            B=None if B is None else int(B), C=(None if C is None else int(C)) if charge else 0,
            K=int(self.K), Cbar=int(self.Cbar) if charge else 0, M=int(self.M), sigma=int(self.sigma),
            P_kw=float(self.P_kw) if charge else 0.0, group=self.grid_group if charge else None,
            F=self.setup_cost(role), bB=float(self.bB), bC=float(self.bC), R_end=self.R_end(role),
            Fhat=float(self.Fhat), bhat=float(self.bhat), chat=float(self.chat))


#: Coefficients of the ``usd_sunk`` 4 h window (design section 4; ``notes/data/cost_calibration_usd.json``).
DEFAULT_SPEC = SitingSpec()
#: Unit-free spec for the toy tests (E2 p.14 units, small sizes so that an option grid covers
#: every integer size: ``K = 2``, ``Cbar = 1``).
TOY_SPEC = SitingSpec(K=2, Cbar=1, M=1, sigma=1, P_kw=10.0, R_end_S=0, R_end_SC=0, F=2.0, F_hub=3.0, bB=0.5,
                      bC=0.25, Fhat=100.0, bhat=10.0, chat=10.0, every=3, first=1, handling_min=0.0, U=2, f=1.0,
                      vreb=0.2, grid_kw=10.0, Delta_min=5.0)


def spec_from_instance(inst: Instance, **overrides: Any) -> SitingSpec:
    """Spec with the cost coefficients of a built instance (``meta['costs']``: ``F, F_hub, bB,
    bC, Fhat, bhat, chat, f, vreb``), the facility sizes of ``meta['params']['facilities_spec']``
    (``K, Cbar, M, sigma, P_kw, grid_sites_kw``) and ``Delta_min``; ``overrides`` win."""
    costs = inst.meta.get("costs") or {}
    fac = ((inst.meta.get("params") or {}).get("facilities_spec")) or {}
    kw: Dict[str, Any] = {}
    for key in ("F", "F_hub", "bB", "bC", "Fhat", "bhat", "chat", "f", "vreb"):
        if costs.get(key) is not None:
            kw[key] = float(costs[key])
    for src, dst in (("K", "K"), ("Cbar", "Cbar"), ("M", "M"), ("sigma", "sigma"), ("P_kw", "P_kw"),
                     ("grid_sites_kw", "grid_kw"), ("R_end", "R_end_SC")):
        if fac.get(src) is not None:
            kw[dst] = fac[src]
    if fac.get("R_end") is not None:
        kw["R_end_S"] = fac["R_end"]
    kw["Delta_min"] = float(inst.disc.Delta_h * 60.0)
    kw.update(overrides)
    return SitingSpec(**kw)


# ---------------------------------------------------------------------------
# base instance
# ---------------------------------------------------------------------------
def make_base_instance(seed: int, candidates: Sequence[Candidate], family: str = STRESS_FAMILY,
                       depots: Optional[Sequence[Node]] = None, name: Optional[str] = None,
                       **overrides: Any) -> Instance:
    """Scenario ``s = seed`` of the siting study: the family instance (``family`` in
    :data:`SITING_FAMILIES`: ``nyc4h_stress`` or ``nyc4h_stress2``, the keyword arguments of
    ``experiments.common.FAMILIES``) built with ``site_latlon`` = every candidate
    (so ``V`` and the route library contain all candidate nodes) and ``depots`` (default:
    the first three candidates = the ``nyc4h`` busiest cells), then stripped of its
    facilities, services and grid group.  ``meta['candidates']`` carries the candidate
    records, ``meta['depots']`` the depot nodes, ``meta['sites'] = []``.  The demand side
    (orders, ``q0``) of a seed does not depend on the candidate set (``data_nyc``: sites
    never touch the random stream)."""
    from . import data_nyc as dn

    cands = list(candidates)
    if not cands:
        raise ValueError("no candidates")
    if depots is None:
        depots = [c.node for c in cands[:3]]
    if family not in SITING_FAMILIES:
        raise ValueError(f"make_base_instance builds one of {sorted(SITING_FAMILIES)} (got {family!r})")
    kw = {**SITING_FAMILIES[family], **overrides}
    kw.setdefault("site_latlon", [(c.lat, c.lon) for c in cands])
    inst = dn.make_nyc_instance(seed=int(seed), name=name or f"{family}-siting-seed{seed}",
                                depots=[tuple(d) for d in depots], **kw)
    inst.meta["family"] = family
    inst.meta["seed"] = int(seed)
    for c in cands:
        if c.node not in inst.nodes:
            raise RuntimeError(f"candidate {c.id} node {c.node} missing from the instance node set")
    inst.facilities = []
    inst.services = []
    inst.P_grid = {}
    if isinstance(inst.pi, dict):
        inst.pi = float(next(iter(inst.pi.values()))) if inst.pi else float(inst.meta["costs"]["pi"])
    inst.meta["candidates"] = candidates_to_records(cands)
    inst.meta["depots"] = [list(d) for d in depots]
    inst.meta["sites"] = []
    inst.meta["sites_latlon"] = []
    inst.meta["siting"] = "base"
    inst.meta["base_name"] = inst.meta["name"]
    inst.reindex()
    inst.validate()
    return inst


def toy_base_instance(seed: int = 0, n_orders: int = 4, n_bikes: int = 2, q0: int = 3, H: int = 12, L: int = 6,
                      candidates: Sequence[Tuple[str, int]] = (("T1", 1), ("T2", 3))) -> Instance:
    """Toy base instance for the bi-level tests: a chain of five nodes ``0..4`` (one slot, one
    level and 0.5 km per hop, routes between every pair), ``n_bikes`` bikes at node 0 with
    ``q0`` of ``L = 6`` levels (``q_res = 1``, ``rho = 0.5``), ``n_orders`` seed-dependent orders
    among nodes 1-4 (``a = r``, ``b = r + 3``, ``hp = 1``, ``hd = 0``, E2 p.14 order costs), a 1 h
    window (``H = 12``, ``Delta = 5 min``), NO facilities.  ``meta['candidates']`` holds the
    candidates (default two: nodes 1 and 3), ``meta['depots'] = [0]``; use it with
    :data:`TOY_SPEC` and :func:`layout_instance`.  Bikes cannot reach the far end and come back
    without a swap, so the layout matters."""
    import random

    from .or_instance import Bike, Discretisation, Order, Route

    disc = Discretisation(Delta_h=1.0 / 12.0, H=int(H), L=int(L), eps_kwh=0.1, eta=1.0)
    nodes = [0, 1, 2, 3, 4]
    routes = {}
    for u in nodes:
        for v in nodes:
            if u != v:
                d = abs(u - v)
                routes[(u, v)] = Route(T_h=d * disc.Delta_h, E_kwh=d * disc.eps_kwh, d_km=0.5 * d)
    rng = random.Random(int(seed))
    orders = []
    for i in range(int(n_orders)):
        o = rng.choice([1, 2, 3, 4])
        d = rng.choice([v for v in [1, 2, 3, 4] if v != o])
        r = rng.randint(0, 5)
        orders.append(Order(id=i + 1, o=o, d=d, r=r, a=r, b=r + 3, hp=1, hd=0, P=100.0, w=12.0, v=24.0))
    bikes = [Bike(id=k + 1, v0=0, q0=int(q0)) for k in range(int(n_bikes))]
    cands = [Candidate(id=cid, label=f"toy node {node}", source="toy", lat=0.0, lon=float(node), node=int(node),
                       rank=i + 1) for i, (cid, node) in enumerate(candidates)]
    meta = {"name": f"toy-siting-seed{seed}", "family": "toy_siting", "seed": int(seed),
            "candidates": candidates_to_records(cands), "depots": [0], "sites": [], "siting": "base",
            "base_name": f"toy-siting-seed{seed}",
            "costs": {"F": TOY_SPEC.F, "F_hub": TOY_SPEC.F_hub, "bB": TOY_SPEC.bB, "bC": TOY_SPEC.bC,
                      "Fhat": TOY_SPEC.Fhat, "bhat": TOY_SPEC.bhat, "chat": TOY_SPEC.chat, "f": TOY_SPEC.f,
                      "vreb": TOY_SPEC.vreb, "kappa": 1.0, "pi": 2.0, "q_res": 1, "rho": 0.5},
            "cost_variant": "toy"}
    inst = Instance(disc=disc, nodes=nodes, routes=routes, bikes=bikes, orders=orders, facilities=[], services=[],
                    P_grid={}, kappa=1.0, pi=2.0, q_res=1, rho=0.5, options={}, meta=meta)
    inst.validate()
    return inst


def _candidate_nodes(base: Instance) -> Dict[str, Node]:
    recs = base.meta.get("candidates")
    if not recs:
        raise ValueError("base instance has no meta['candidates'] (build it with make_base_instance)")
    return {str(r["id"]): _grid_node(r["node"]) for r in recs}


def layout_items(layout: Any) -> List[Tuple[str, str, int, int]]:
    """Normalise a layout given as a ``Layout`` (``.open``) or an iterable of
    ``(loc, role, B, C)`` into a sorted list of tuples."""
    items = getattr(layout, "open", layout)
    out = [(str(l), str(r), int(B), int(C)) for (l, r, B, C) in items]
    return sorted(out)


def layout_admissible(layout: Any, s_needs_charge: bool = True, require_swap: bool = True) -> bool:
    """Structural admissibility of a layout for the planner (independent of budget and spec):
    with ``require_swap`` at least one swap-capable object (a C-only layout violates (9), no bike
    can end at a swap site), and with ``s_needs_charge`` the E9 relaunch rule "swap-only sites are
    allowed only when at least one C or SC site is open" (a swap-only site holds ``B_j <= 3``
    full batteries and cannot recharge; without a charge-capable object in the network nothing
    can ever be resupplied, so an S-only layout is a dead stock, not a design)."""
    items = layout_items(layout)
    if require_swap and not any(ROLE_SWAP[r] for _l, r, _B, _C in items):
        return False
    if s_needs_charge and any(r == "S" for _l, r, _B, _C in items) and not any(ROLE_CHARGE[r] for _l, r, _B, _C in items):
        return False
    return True


# ---------------------------------------------------------------------------
# layout instances
# ---------------------------------------------------------------------------
def _services(inst: Instance, facilities: Sequence[Facility], spec: SitingSpec) -> List[Service]:
    """Shuttle services between every charge-capable and every swap-capable object at
    different locations, both directions (design rule (e)): departures ``first, first +
    every, ...``, duration ``ceil((route minutes + handling) / Delta)`` slots, ``U, f, vreb``
    of the spec, optional ``max_pair_km``."""
    H = inst.H
    Delta_min = inst.disc.Delta_h * 60.0
    charge = [f for f in facilities if f.charge]
    swap = [f for f in facilities if f.swap]
    pairs: List[Tuple[Facility, Facility]] = []
    for a in charge:
        for b in swap:
            if split_facility_id(a.id)[0] == split_facility_id(b.id)[0]:
                continue
            pairs.append((a, b))
            pairs.append((b, a))
    seen = set()
    services: List[Service] = []
    for a, b in pairs:
        if (a.id, b.id) in seen:
            continue
        seen.add((a.id, b.id))
        r = inst.route(a.node, b.node)
        if r is None:
            continue
        if spec.max_pair_km is not None and r.d_km > spec.max_pair_km + 1e-9:
            continue
        dur = max(1, int(math.ceil((r.T_h * 60.0 + spec.handling_min) / Delta_min - 1e-9)))
        for l in range(int(spec.first), H, int(spec.every)):
            u = l + dur
            if u <= H:
                services.append(Service(id=len(services) + 1, o_fac=a.id, d_fac=b.id, l=l, u=u,
                                        U=int(spec.U), f=float(spec.f), vreb=float(spec.vreb)))
    return services


def _finish(inst: Instance, facilities: List[Facility], spec: SitingSpec, meta: Dict[str, Any]) -> Instance:
    inst.facilities = facilities
    inst.services = _services(inst, facilities, spec)
    if any(f.charge for f in facilities):
        inst.P_grid = {spec.grid_group: [float(spec.grid_kw)] * inst.H}
    else:
        inst.P_grid = {}
    inst.meta = {**inst.meta, **meta}
    inst.meta["sites"] = []
    seen = set()
    for f in facilities:
        if f.node not in seen:
            seen.add(f.node)
            inst.meta["sites"].append(list(f.node) if isinstance(f.node, tuple) else f.node)
    inst.meta["siting_spec"] = spec.to_dict()
    inst.reindex()
    inst.validate()
    return inst


def layout_instance(base: Instance, layout: Any, spec: SitingSpec = DEFAULT_SPEC,
                    name: Optional[str] = None) -> Instance:
    """Instance of a layout ``{(l, r, B, C)}`` on ``base``: one fixed facility object per
    open item (``y = 1``, ``B``, ``C`` fixed; ``fixed_facilities = True``), the shuttle
    services of rule (e), the flat grid group; ``meta['layout']``, ``meta['layout_key']``,
    ``meta['sites']`` (open nodes), ``meta['site_labels']``.  Raises ``ValueError`` on an
    unknown location, a repeated location, a role outside :data:`ROLES` or sizes outside
    (7)-(8)."""
    items = layout_items(layout)
    nodes = _candidate_nodes(base)
    inst = copy.deepcopy(base)
    facilities: List[Facility] = []
    locs = set()
    for loc, role, B, C in items:
        if loc not in nodes:
            raise ValueError(f"unknown candidate {loc!r}")
        if loc in locs:
            raise ValueError(f"location {loc} opened twice (one role per location)")
        locs.add(loc)
        if not spec.valid_sizes(role, B, C):
            raise ValueError(f"sizes B={B}, C={C} outside (7)-(8) for role {role} at {loc}")
        facilities.append(spec.facility(loc, nodes[loc], role, B, C, y=1))
    key = "|".join(f"{l}:{r}:B{B}:C{C}" for l, r, B, C in items) or "empty"
    labels = {str(r["id"]): str(r["label"]) for r in base.meta["candidates"]}
    meta = {"layout": [list(it) for it in items], "layout_key": key, "siting": "layout",
            "site_labels": [f"{l} {labels[l]} ({r}, B {B}, C {C})" for l, r, B, C in items],
            "name": name or f"{base.meta.get('base_name', base.meta.get('name'))}-{key}"}
    inst.options["fixed_facilities"] = True
    return _finish(inst, facilities, spec, meta)


def all_candidates_instance(base: Instance, spec: SitingSpec = DEFAULT_SPEC, roles: Sequence[str] = ROLES,
                            open_all: bool = False, name: Optional[str] = None) -> Instance:
    """Every role object ``(l, r)``, ``r in roles``, of every candidate: with ``open_all =
    False`` the facilities are free (``y = B = C = None``; the integrated model, which adds
    the exclusivity / budget rows itself), with ``open_all = True`` they are all open with
    free sizes (``y = 1``, ``B = C = None``; the superset relaxation used as a lower bound).
    Services exist for every charge-capable / swap-capable pair at different locations."""
    nodes = _candidate_nodes(base)
    inst = copy.deepcopy(base)
    facilities = [spec.facility(loc, nodes[loc], role, None, None, y=1 if open_all else None)
                  for loc in nodes for role in roles]
    meta = {"layout": None, "layout_key": "all_open" if open_all else "all_free",
            "siting": "all_open" if open_all else "all_free", "roles": list(roles),
            "name": name or f"{base.meta.get('base_name', base.meta.get('name'))}-{'all_open' if open_all else 'all_free'}"}
    inst.options["fixed_facilities"] = bool(open_all)
    return _finish(inst, facilities, spec, meta)


def siting_pruning(inst: Instance, targets: str = "all_candidates", **overrides: Any) -> Dict[str, Any]:
    """Arc-builder options of a siting instance: for semi-real instances the ``PRUNING_NYC``
    values (``tau_max 4``, ``start_slack 6``, reachable pruning) with ``reposition_targets``
    chosen by ``targets`` (:data:`REPOSITION_MODES`):

    * ``'all_candidates'`` -- ALL candidate nodes + depots (not only the open facilities), so
      that the library of a layout is a sub-library of the all-candidates template and the
      integrated model (A) and the enumerated layouts (B) price the same move arcs (E9.1);
    * ``'open_sites'`` -- the nodes of the facilities of ``inst`` that are not fixed closed +
      depots (the E8 ``targets = 'facilities'`` convention), the per-layout library of the
      search algorithms; on an all-candidates instance both conventions coincide.

    ILP totals remain upper bounds on the written optimum under both conventions because
    moves to restaurant / customer nodes are excluded (E8 convention), and the ``open_sites``
    value of a layout is an upper bound on its ``all_candidates`` value.  For other instances
    (toy tests) no pruning at all, so the same statements hold trivially.  ``overrides``
    (``tau_max``, ``start_slack``, ``reachable``) are applied on the semi-real path."""
    if targets not in REPOSITION_MODES:
        raise ValueError(f"targets must be one of {REPOSITION_MODES} (got {targets!r})")
    if not inst.meta.get("semi_real"):
        return {}
    from .generator import default_pruning

    kw = {**STRESS_PRUNING, **overrides}
    pr = default_pruning(inst, tau_max=int(kw["tau_max"]), start_slack=int(kw["start_slack"]),
                         reachable=bool(kw["reachable"]))
    pr["reposition_targets"] = reposition_targets(inst, targets)
    return pr


def reposition_targets(inst: Instance, targets: str = "all_candidates") -> set:
    """Node set of the ``reposition_targets`` option under a :data:`REPOSITION_MODES` convention."""
    if targets == "all_candidates":
        out = set(_candidate_nodes(inst).values())
    else:
        out = {f.node for f in inst.facilities if f.y != 0}
    out.update(_grid_node(d) for d in inst.meta.get("depots", []))
    return out


def subset_library(template: ArcLibrary, inst: Instance, strict: bool = False) -> ArcLibrary:
    """Arc library of ``inst`` (a layout / all-open instance of the same scenario) derived
    from the all-candidates ``template`` library: swap and terminal arcs are kept only for
    the swap facilities of ``inst`` that are not fixed closed, the forward reachability pass
    of ``build_arcs`` is repeated per bike (unreachable arcs dropped when the template was
    built with ``reachable_pruning``) and ids are renumbered bike after bike.  The result is
    identical to ``build_arcs(inst, strict, **template.options)`` (same arcs, same ids), which
    ``tests/test_bilevel.py`` asserts; it only avoids re-templating.  ``inst`` must share
    nodes, routes, bikes and orders with ``template.inst``."""
    t_inst = template.inst
    if (inst.nodes != t_inst.nodes or inst.routes != t_inst.routes or inst.bikes != t_inst.bikes
            or inst.orders != t_inst.orders or inst.disc != t_inst.disc or inst.q_res != t_inst.q_res):
        raise ValueError("subset_library: the instance is not a facility variant of the template's instance")
    keep_fac = {j for j in inst.S if inst.facility(j).y != 0}
    for j in keep_fac:
        if j not in set(t_inst.S):
            raise ValueError(f"subset_library: swap facility {j} is not in the template")
    opts = dict(template.options)
    gbar = compute_gbar(inst)
    lib = ArcLibrary(inst, opts, gbar)
    prune = bool(opts.get("reachable_pruning", False))
    next_id = 0
    for b in inst.bikes:
        arcs = [a for a in template.arcs_of(b.id)
                if not (a.kind in ("swap", "term") and a.fac is not None and a.fac not in keep_fac)]
        by_src: Dict[Tuple, List[int]] = {}
        for idx, a in enumerate(arcs):
            by_src.setdefault(a.src, []).append(idx)
        source = (b.v0, 0, b.q0)
        seen = {source}
        stack = [source]
        while stack:
            s = stack.pop()
            for idx in by_src.get(s, ()):
                d = arcs[idx].dst
                if d not in seen:
                    seen.add(d)
                    stack.append(d)
        if not any(a.kind == "term" and a.fac is not None and a.src in seen for a in arcs):
            lib.infeasible_bikes.append(b.id)
        for a in arcs:
            if prune and a.src not in seen:
                continue
            lib._add(type(a)(next_id, a.k, a.kind, a.src, a.dst, a.l, a.u, a.d_km, a.g, a.order, a.fac, a.theta))
            next_id += 1
    if lib.infeasible_bikes and strict and not lib.has_dummy_terminal:
        from .arcs import InfeasibleInstanceError
        raise InfeasibleInstanceError("no reachable terminal arc (9) for bikes "
                                      + ", ".join(map(str, lib.infeasible_bikes)))
    return lib
