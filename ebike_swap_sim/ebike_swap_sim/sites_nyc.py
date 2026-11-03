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
* Round 5, plan item M6 (``notes/reading_to_model.md``): the Manhattan-wide region
  ``data_nyc.MANHATTAN_S110`` (south of 110th St), :func:`lattice_candidates` (2 km cells of
  the rotated frame, each snapped to its busiest DOHMH node), rider depots at the
  bridge / tunnel entry points (:func:`family_depots`, ``data_nyc.MANHATTAN_ENTRY_POINTS``),
  the access radius anchored to the eBaaS 2 km cabinet coverage
  (:func:`access_radius_blocks`) and the family :data:`R5_MANHATTAN_FAMILY` (``r5_manhattan``:
  eBaaS energy calibration A1, TOU tariff, r5 operating day, 8 bikes / 4 h).  These are data
  only; no E2 equation changes.
"""
from __future__ import annotations

import copy
import math
import csv
import os
import re
from dataclasses import asdict, dataclass, field, fields
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
    "R5_MANHATTAN_FAMILY", "R5_MANHATTAN_PARAMS", "SITING_POST", "LATTICE_CELL_M", "EBAAS_COVERAGE_M",
    "access_radius_blocks", "lattice_candidates", "family_candidates", "family_depots", "family_access_D",
    "MANHATTAN_DOT_FAMILY", "DOT_CSV_DEFAULT", "DOT_TYPE_PRIORITY", "DOT_HUB_TYPES", "DOT_HUB_PRIORITY", "DOT_REJECT_VERDICTS",
    "FAMILY_SPEC_OVERRIDES", "family_spec_overrides", "dot_candidates", "write_candidate_tables",
    "candidate_roles", "scenario_design", "lp_scenario_subset", "SCENARIO_LEVELS", "SCENARIO_DAY_WEIGHTS",
    "candidate_cell", "lattice_cell_of",
    "MANHATTAN15_FAMILY", "MANHATTAN15_PARAMS",
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
#: Round 5 Manhattan-wide siting family (plan item M6 with A1 and M5): the region
#: ``data_nyc.MANHATTAN_S110`` (Manhattan south of 110th St; demand restricted to Manhattan
#: NTAs and Manhattan DOHMH rows), candidates on the 2 km lattice (:func:`lattice_candidates`),
#: riders starting at the six bridge / tunnel entry points (:func:`family_depots`).
#: Energy: the eBaaS calibration (``config.energy_calibration('ebaas')``: 25 Wh/km, 0 Wh per
#: signal, 0.6 Wh per metre of climb, eps 25 Wh, L 24, concat rounding, q_res 2 levels,
#: p_ch 0.333 kW); time: the r5 operating day (``generator.R5_TIME_PROFILE``) on the dinner
#: window 16:00-20:00 (H 48); prices: ``usd_sunk``
#: with the ``tou`` tariff (the whole window is inside the 08-22 h price peak, so pi = 0.442
#: $/kWh flat); sites: ``K 8``, ``Cbar 4``, ``P_j = 1.4 kW`` (4 chargers of 0.333 kW), one flat
#: 2 kW grid group (6 simultaneous charges); ``q0 ~ U{6..12}`` of 24.  Size: 8 bikes / 40 orders
#: (1.25 orders per bike-hour; ex-ante 7.8 km per bike-hour against the eBaaS 8.57 km per
#: rider-hour, ``meta['r5']``).  Sizing probe (seed 0, 2026-10-17, open-sites libraries, aggregated
#: ILP, Threads 3, TimeLimit 300 s): one site M08:SC:B3:C2 1.43 M arcs, OPTIMAL in 27 s, ILP served
#: 0.70 vs baseline 0.48; three sites M04/M08/M10 SC:B2:C1 2.10 M arcs, TIME_LIMIT with gap 1.3 %,
#: ILP served 0.93 vs baseline 0.78 -- layouts differ strongly (the point of M6) and stay solvable.
#: Rejected: 8 bikes x 2.0 orders per bike-hour (64 orders, 2.6-3.6 M arcs, baseline served
#: 0.31-0.56) and 6 bikes x 1.5 (0.9-1.4 M arcs, baseline served 0.42-0.69).  Post-build steps
#: (q_res, rounding, tariff) are listed in :data:`SITING_POST` and applied by
#: :func:`make_base_instance`.
R5_MANHATTAN_FAMILY = "r5_manhattan"
#: R7 siting scale-up (``notes/siting_scaleup_design.md``): the same instance parameters,
#: region, depots, energy calibration and tariff as ``r5_manhattan``; the candidate set is the
#: DOT-based one of :func:`dot_candidates` (``data/raw/dot_candidate_sites.csv`` plus the 15
#: lattice candidates), the size menu is the reduced one (section 1.2), transfer services only
#: within ``max_pair_km = 2.0`` (:data:`FAMILY_SPEC_OVERRIDES`) and hubs only at hub-capable sites.
MANHATTAN_DOT_FAMILY = "manhattan_dot"
#: Default location of the DOT candidate file (built by the parallel data task).
DOT_CSV_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               "data", "raw", "dot_candidate_sites.csv")
#: Merge priority of DOT site types (earlier wins; unknown types are ``'other'``, after every
#: listed type; the lattice candidates come after ``'other'``).  The design's names (pilot,
#: approved, application, citibike_charging, depot, lot, other) and the data task's (pilot,
#: installed, shortlist, revocable_consent, citibike_charging, fdny_hub) are both listed.
DOT_TYPE_PRIORITY: Tuple[str, ...] = ("pilot", "installed", "approved", "revocable_consent", "shortlist",
                                      "application", "citibike_charging", "fdny_hub", "depot", "lot", "other")
#: DOT types whose sites may host a charge-only hub (design 1.2 / 7.4 item 19).
DOT_HUB_TYPES: Tuple[str, ...] = ("depot", "lot", "citibike_charging", "fdny_hub")
#: Order in which hub-capable sites fill the ``max_hub`` slots (2026-10-21): operator stores and
#: hubs (indoor, owner consent) and lots before FDNY sites and grid-connected Citi Bike docks
#: (a sidewalk dock is only a proxy for a power connection); lattice fallback cells last.
DOT_HUB_PRIORITY: Tuple[str, ...] = ("depot", "lot", "fdny_hub", "citibike_charging")
#: Verdict tokens that drop a DOT row: the verdict's FIRST word (lower-cased, ``-`` / ``_`` split)
#: must be one of these, or its first two words ``no go`` / ``out of``.  Whole tokens only
#: (fixer pass): ``'No objection'``, ``'not sure'`` and ``'outstanding candidate'`` are kept;
#: unknown verdicts are kept and listed in ``info['verdicts']``.
DOT_REJECT_VERDICTS: Tuple[str, ...] = ("drop", "dropped", "reject", "rejected", "exclude", "excluded", "nogo", "out",
                                        "outside", "remove", "removed")


def _ebaas_energy() -> Dict[str, Any]:
    from .config import energy_calibration
    return energy_calibration("ebaas")


def _r5_time_profile() -> Dict[str, Any]:
    from .generator import R5_TIME_PROFILE
    return copy.deepcopy(R5_TIME_PROFILE)


_EBAAS = _ebaas_energy()
R5_MANHATTAN_PARAMS: Dict[str, Any] = {
    "n_bikes": 8, "window_h": 4.0, "orders_per_bike_hour": 1.25, "L": int(_EBAAS["L"]),
    "battery_wh": float(_EBAAS["battery_wh"]), "n_sites": 3, "cost_variant": "usd_sunk",
    "region": "manhattan_s110",
    "physics": {k: float(_EBAAS[k]) for k in ("wh_per_km", "wh_per_m_climb", "wh_per_light")},
    "demand_spec": {"window_start_h": 16.0, "profile": _r5_time_profile(), "init_frac": (0.25, 0.5)},
    "facilities_spec": {"B": 2, "C": 1, "P_kw": 1.4, "Cbar": 4, "grid_sites_kw": 2.0, "grid_sites_peak_kw": 2.0},
}
#: Post-build steps of :func:`make_base_instance` per family (data only): ``energy_calibration``
#: (sets ``q_res`` in levels and ``options['energy_rounding']``, records the calibration) and
#: ``tariff`` (``costs.load_tariff``: the price of every slot, flat when constant).
SITING_POST: Dict[str, Dict[str, Any]] = {R5_MANHATTAN_FAMILY: {"energy_calibration": "ebaas", "tariff": "tou"},
                                          MANHATTAN_DOT_FAMILY: {"energy_calibration": "ebaas", "tariff": "tou"}}

#: R8 fifteen-site study (``notes/siting15_design.md`` section 1, critic C4): the ``manhattan_dot``
#: data (DOT candidates, six entry depots, eBaaS energy, TOU tariff, R5 time profile) with a
#: city-scale fleet of 48 riders, 8 per entry depot.  The order count is NOT an override:
#: ``make_nyc_instance`` derives ``n_orders = round(n_bikes x window_h x orders_per_bike_hour)``,
#: so the stratified levels 1.0 / 1.25 / 1.5 of :func:`scenario_design` give 192 / 240 / 288
#: orders per evening.  A new family name keeps every ``manhattan_dot`` cache key untouched.
MANHATTAN15_FAMILY = "manhattan15"
MANHATTAN15_PARAMS: Dict[str, Any] = {**R5_MANHATTAN_PARAMS, "n_bikes": 48}
SITING_POST[MANHATTAN15_FAMILY] = dict(SITING_POST[MANHATTAN_DOT_FAMILY])

#: Families :func:`make_base_instance` can build (``family -> make_nyc_instance`` keyword arguments).
SITING_FAMILIES: Dict[str, Dict[str, Any]] = {STRESS_FAMILY: STRESS_PARAMS, STRESS2_FAMILY: STRESS2_PARAMS,
                                              R5_MANHATTAN_FAMILY: R5_MANHATTAN_PARAMS,
                                              MANHATTAN_DOT_FAMILY: R5_MANHATTAN_PARAMS,
                                              MANHATTAN15_FAMILY: MANHATTAN15_PARAMS}
#: :class:`SitingSpec` overrides per family applied by :func:`family_spec_overrides` (the CLI
#: passes them to :func:`spec_from_instance`); the ``manhattan_dot`` family limits transfer
#: services to pairs within 2 km (design 1.3).  Empty for every older family (unchanged keys).
FAMILY_SPEC_OVERRIDES: Dict[str, Dict[str, Any]] = {MANHATTAN_DOT_FAMILY: {"max_pair_km": 2.0},
                                                    MANHATTAN15_FAMILY: {"max_pair_km": 2.0}}
#: Size menus of the greedy / local search per family (``role -> [(B, C), ...]``).
SIZE_MENUS: Dict[str, Dict[str, List[Tuple[int, int]]]] = {
    STRESS_FAMILY: {"S": [(1, 0), (2, 0), (3, 0)], "C": [(0, 1), (0, 2)],
                    "SC": [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)]},
    STRESS2_FAMILY: {"S": [(1, 0), (2, 0), (3, 0)], "C": [(0, 2), (0, 4)],
                     "SC": [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)]},
    R5_MANHATTAN_FAMILY: {"S": [(1, 0), (2, 0), (3, 0), (4, 0)], "C": [(0, 2), (0, 4)],
                          "SC": [(B, C) for C in (1, 2) for B in (1, 2, 3, 4)]},
    # reduced menu of the scale-up (design 1.2): SC B in {2,3,4} x C in {1,2}; S B in {2,3}; hubs C in {2,4}
    MANHATTAN_DOT_FAMILY: {"S": [(2, 0), (3, 0)], "C": [(0, 2), (0, 4)],
                           "SC": [(B, C) for C in (1, 2) for B in (2, 3, 4)]},
    # R8 (15 sites at 48 riders): the reduced SC menu of the scale-up (sizes polished at the end)
    MANHATTAN15_FAMILY: {"S": [(2, 0), (3, 0)], "C": [(0, 2), (0, 4)],
                         "SC": [(B, C) for C in (1, 2) for B in (2, 3, 4)]},
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
    #: R7 siting scale-up (``notes/siting_scaleup_design.md`` 1.1): may host a charge-only hub
    #: (``C`` role); ``True`` for every candidate of the older families (unchanged behaviour).
    hub_capable: bool = True
    #: ``M01..M15`` when the candidate is (or absorbed) a lattice candidate of ``r5_manhattan``.
    lattice_id: Optional[str] = None
    #: metres between the raw point and its grid node (0 for data-generated nodes).
    snap_m: float = 0.0
    #: DOT site type of the surviving row (``None`` for lattice-only candidates).
    dot_type: Optional[str] = None
    #: lattice cell ``[cx, cy]`` (2 km, :data:`LATTICE_CELL_M`) of the node; the B&B atom.
    cell: Optional[List[int]] = None
    #: candidate class: ``'dot'``, ``'lattice'``, ``'both'`` (a merged pair) or ``''`` (older families).
    cls: str = ""

    def to_record(self) -> Dict[str, Any]:
        d = asdict(self)
        d["node"] = list(self.node) if isinstance(self.node, tuple) else self.node
        return _py(d)

    @classmethod
    def from_record(cls, d: Dict[str, Any]) -> "Candidate":
        known = {f.name for f in fields(cls)}
        d = {k: v for k, v in dict(d).items() if k in known}
        d["node"] = _grid_node(d["node"])
        if d.get("cell") is not None:
            d["cell"] = [int(x) for x in d["cell"]]
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
    if family not in SITING_FAMILIES:
        raise ValueError(f"make_base_instance builds one of {sorted(SITING_FAMILIES)} (got {family!r})")
    if depots is None:
        depots = family_depots(family, cands)
    kw = {**SITING_FAMILIES[family], **overrides}
    if "demand_spec" in overrides and isinstance(SITING_FAMILIES[family].get("demand_spec"), dict):
        kw["demand_spec"] = {**SITING_FAMILIES[family]["demand_spec"], **(overrides["demand_spec"] or {})}
    kw.setdefault("site_latlon", [(c.lat, c.lon) for c in cands])
    inst = dn.make_nyc_instance(seed=int(seed), name=name or f"{family}-siting-seed{seed}",
                                depots=[tuple(d) for d in depots], **kw)
    inst.meta["family"] = family
    inst.meta["seed"] = int(seed)
    if family in SITING_POST:
        _apply_post(inst, SITING_POST[family])
    for c in cands:
        if c.node not in inst.nodes:
            raise RuntimeError(f"candidate {c.id} node {c.node} missing from the instance node set")
    inst.facilities = []
    inst.services = []
    inst.P_grid = {}
    if isinstance(inst.pi, dict):
        inst.pi = float(next(iter(inst.pi.values()))) if inst.pi else float(inst.meta["costs"]["pi"])
    if inst.meta.get("pi_schedule") and len(set(inst.meta["pi_schedule"])) == 1:
        inst.pi = float(inst.meta["pi_schedule"][0])
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
    sched = inst.meta.get("pi_schedule")
    if sched and len(set(sched)) > 1:
        # time-varying tariff (SITING_POST 'tariff'): E2 (28) price pi_jt of every facility
        inst.pi = {(f.id, t): float(sched[t]) for f in facilities for t in range(inst.H)}
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


def candidate_roles(candidates: Sequence[Candidate], roles: Sequence[str] = ROLES) -> Dict[str, Tuple[str, ...]]:
    """Per-location role lists: ``roles`` minus the hub role ``C`` at candidates that are not
    ``hub_capable`` (design 1.2; every candidate of the older families is hub-capable, so the
    result equals ``roles`` everywhere for them)."""
    out: Dict[str, Tuple[str, ...]] = {}
    for c in candidates:
        out[c.id] = tuple(r for r in roles if r != "C" or bool(c.hub_capable))
    return out


def all_candidates_instance(base: Instance, spec: SitingSpec = DEFAULT_SPEC, roles: Any = ROLES,
                            open_all: bool = False, name: Optional[str] = None) -> Instance:
    """Every role object ``(l, r)``, ``r in roles``, of every candidate: with ``open_all =
    False`` the facilities are free (``y = B = C = None``; the integrated model, which adds
    the exclusivity / budget rows itself), with ``open_all = True`` they are all open with
    free sizes (``y = 1``, ``B = C = None``; the superset relaxation used as a lower bound).
    Services exist for every charge-capable / swap-capable pair at different locations.
    ``roles`` may be a per-location dict ``{loc: roles}`` (:func:`candidate_roles`: hubs only
    at hub-capable locations); a location absent from the dict gets no object."""
    nodes = _candidate_nodes(base)
    inst = copy.deepcopy(base)
    if isinstance(roles, dict):
        per = {str(l): tuple(rs) for l, rs in roles.items()}
        role_list = sorted({r for rs in per.values() for r in rs}, key=ROLES.index)
    else:
        per = {loc: tuple(roles) for loc in nodes}
        role_list = list(roles)
    facilities = [spec.facility(loc, nodes[loc], role, None, None, y=1 if open_all else None)
                  for loc in nodes for role in per.get(loc, ())]
    meta = {"layout": None, "layout_key": "all_open" if open_all else "all_free",
            "siting": "all_open" if open_all else "all_free", "roles": role_list,
            "name": name or f"{base.meta.get('base_name', base.meta.get('name'))}-{'all_open' if open_all else 'all_free'}"}
    inst.options["fixed_facilities"] = bool(open_all)
    return _finish(inst, facilities, spec, meta)


def siting_pruning(inst: Instance, targets: str = "all_candidates", approach_radius_blocks: Optional[int] = None,
                   **overrides: Any) -> Dict[str, Any]:
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
    (``tau_max``, ``start_slack``, ``reachable``) are applied on the semi-real path.

    ``approach_radius_blocks`` (R7 scale-up, design 1.4): moves INTO a candidate node only
    from nodes within that many blocks (``arcs`` option ``reposition_target_radius``, one
    entry per candidate node that is not a depot; depots stay unrestricted as targets, and the
    start states ``(v0, q0)`` of the bikes stay unrestricted as tails, ``arcs`` option
    ``reposition_radius_exempt_states``).  ``None`` adds
    NO key, so every existing pruning signature, cache key and ``config_md5`` is unchanged.
    On the toy path the radius is applied too (no other pruning), so the toy tests cover it."""
    if targets not in REPOSITION_MODES:
        raise ValueError(f"targets must be one of {REPOSITION_MODES} (got {targets!r})")
    if not inst.meta.get("semi_real"):
        return _with_radius(inst, {}, approach_radius_blocks)
    from .generator import default_pruning

    kw = {**STRESS_PRUNING, **overrides}
    pr = default_pruning(inst, tau_max=int(kw["tau_max"]), start_slack=int(kw["start_slack"]),
                         reachable=bool(kw["reachable"]))
    pr["reposition_targets"] = reposition_targets(inst, targets)
    return _with_radius(inst, pr, approach_radius_blocks)


def _with_radius(inst: Instance, pr: Dict[str, Any], radius: Optional[int]) -> Dict[str, Any]:
    if radius is None:
        return pr
    depots = {_grid_node(d) for d in inst.meta.get("depots", [])}
    pr = dict(pr)
    pr["reposition_target_radius"] = {v: int(radius) for v in _candidate_nodes(inst).values() if v not in depots}
    # the start states (v0, q0) of the scenario's bikes keep every move arc at every t (a bike's
    # first approach is one arc; arcs option ``reposition_radius_exempt_states``, decision of
    # 2026-10-21, narrowed from whole depot / start tails the same day); bike-independent, so the
    # template and every pricing library of the scenario get the same arcs
    states = {(b.v0, int(b.q0)) for b in inst.bikes}
    pr["reposition_radius_exempt_states"] = sorted(states, key=lambda vq: (str(vq[0]), vq[1]))
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


# ---------------------------------------------------------------------------
# Round 5, plan item M6: Manhattan-wide region, lattice candidates, entry-point depots
# ---------------------------------------------------------------------------
#: Side of the candidate lattice cells (m), anchored to the eBaaS cabinet coverage radius.
LATTICE_CELL_M = 2000.0
#: eBaaS cabinet coverage radius (Ding et al., WWW 2025, Sec. 4.2: "2 km"), ``config.EBAAS_FACTS``.
EBAAS_COVERAGE_M = 2000.0


def access_radius_blocks(coverage_m: float = EBAAS_COVERAGE_M, block_m: float = 150.0) -> int:
    """Access radius ``D`` of the planner-only row [U4] in grid blocks, anchored to the eBaaS
    2 km cabinet coverage (plan item M6): the smallest number of 150 m blocks whose grid
    (network) distance is at least ``coverage_m``, ``ceil(2000 / 150) = 14`` blocks (2.1 km).
    No E2 equation is involved ([U4] is an upper-level row)."""
    return int(math.ceil(float(coverage_m) / float(block_m) - 1e-9))


def lattice_candidates(region: Any = "manhattan_s110", cell_m: float = LATTICE_CELL_M, min_restaurants: int = 10,
                       min_sep_blocks: int = 2, restaurants: Any = None) -> List[Candidate]:
    """Candidate set ``Lambda`` of the Manhattan-wide E9 redesign (plan item M6; data only, no
    E2 equation): the region's box frame (R2.4 rotated metres, avenues along ``y``) is tiled in
    square cells of ``cell_m`` (2 km, the eBaaS coverage) from the frame origin; every cell with
    at least ``min_restaurants`` DOHMH rows of the region (``data_nyc.region_restaurants``)
    contributes ONE candidate, its busiest restaurant node (most rows snapped to the node; ties
    by node order), skipping nodes closer than ``min_sep_blocks`` (Manhattan) to a candidate of
    an earlier cell.  Cells are visited south to north, then west to east (``(cy, cx)``), ids
    ``M01, M02, ...``; ``source = 'lattice'``, ``n_restaurants`` = rows at the node, ``label``
    names the cell and its total.  Deterministic."""
    from . import data_nyc as dn

    reg = dn.resolve_region(region)
    box = reg.box
    rest = dn.region_restaurants(reg) if restaurants is None else restaurants
    counts: Dict[Node, int] = {}
    for v in rest["node"]:
        v = _node(v)
        counts[v] = counts.get(v, 0) + 1
    cells: Dict[Tuple[int, int], List[Node]] = {}
    for v in counts:
        x, y = box.node_xy(v)
        cells.setdefault((int(math.floor(x / cell_m)), int(math.floor(y / cell_m))), []).append(v)
    out: List[Candidate] = []
    for cx, cy in sorted(cells, key=lambda c: (c[1], c[0])):
        nodes = cells[(cx, cy)]
        total = sum(counts[v] for v in nodes)
        if total < int(min_restaurants):
            continue
        ranked = sorted(nodes, key=lambda v: (-counts[v], v))
        pick = next((v for v in ranked if all(manhattan_blocks(v, c.node) >= int(min_sep_blocks) for c in out)), None)
        if pick is None:
            continue
        lat, lon = box.node_latlon(pick)
        out.append(Candidate(id=f"M{len(out) + 1:02d}", label=f"lattice cell ({cx}, {cy}): {total} restaurants",
                             source="lattice", lat=float(lat), lon=float(lon), node=pick, grid_connected=False,
                             n_restaurants=int(counts[pick]), rank=len(out) + 1))
    return out


def family_candidates(family: str, dot_csv: Optional[str] = None, **kw: Any) -> List[Candidate]:
    """Candidate set of a siting family: :func:`lattice_candidates` for ``r5_manhattan`` (M6),
    :func:`dot_candidates` (``dot_csv``, default :data:`DOT_CSV_DEFAULT`; ``kw`` forwarded) for
    ``manhattan_dot`` (R7), :func:`candidate_sites` (Midtown box) for the round-3/4 families."""
    if family == R5_MANHATTAN_FAMILY:
        return lattice_candidates()
    if family in (MANHATTAN_DOT_FAMILY, MANHATTAN15_FAMILY):
        return dot_candidates(dot_csv or DOT_CSV_DEFAULT, **kw)[0]
    return candidate_sites()


def family_depots(family: str, candidates: Sequence[Candidate]) -> List[Node]:
    """Rider depots of a siting family: the six bridge / tunnel entry points of
    ``data_nyc.MANHATTAN_ENTRY_POINTS`` for ``r5_manhattan`` and ``manhattan_dot`` (M6), the
    first three candidates (the ``nyc4h`` busiest cells) otherwise (unchanged)."""
    if family in (R5_MANHATTAN_FAMILY, MANHATTAN_DOT_FAMILY, MANHATTAN15_FAMILY):
        from . import data_nyc as dn
        return dn.entry_point_depots(dn.resolve_region(R5_MANHATTAN_PARAMS["region"]).box)
    return [c.node for c in list(candidates)[:3]]


def family_access_D(family: str) -> Optional[int]:
    """Default access radius [U4] in blocks: :func:`access_radius_blocks` (eBaaS 2 km) for
    ``r5_manhattan`` / ``manhattan_dot``; ``None`` (the experiment's own grid) otherwise."""
    return access_radius_blocks() if family in (R5_MANHATTAN_FAMILY, MANHATTAN_DOT_FAMILY, MANHATTAN15_FAMILY) else None


def family_spec_overrides(family: str) -> Dict[str, Any]:
    """:data:`FAMILY_SPEC_OVERRIDES` of a family (``{}`` for the older families)."""
    return dict(FAMILY_SPEC_OVERRIDES.get(family, {}))


# ---------------------------------------------------------------------------
# R7 siting scale-up: DOT candidates (design 1.1), stratified scenarios (design 1.7)
# ---------------------------------------------------------------------------
def lattice_cell_of(box: Any, node: Node, cell_m: float = LATTICE_CELL_M) -> List[int]:
    """Lattice cell index ``[cx, cy]`` of a grid node (the tiling of :func:`lattice_candidates`)."""
    x, y = box.node_xy(node)
    return [int(math.floor(x / cell_m)), int(math.floor(y / cell_m))]


def candidate_cell(c: Candidate) -> Tuple[int, int]:
    """Cell of a candidate as a tuple (``(0, 0)`` for candidates without a cell, e.g. toy)."""
    return tuple(int(x) for x in c.cell) if c.cell else (0, 0)


def _dot_type(raw: Any) -> str:
    t = str(raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    return t if t in DOT_TYPE_PRIORITY else "other"


def _priority(c: Candidate) -> int:
    if c.dot_type is None:
        return len(DOT_TYPE_PRIORITY) + 1          # lattice: after every DOT type
    return DOT_TYPE_PRIORITY.index(c.dot_type)


def _rejected(verdict: Any) -> bool:
    """``True`` when the verdict's first word is a rejecting token (:data:`DOT_REJECT_VERDICTS`)
    or its first two words are ``no go`` / ``out of``; whole tokens only."""
    toks = [t for t in re.split(r"[^a-z0-9]+", str(verdict or "").strip().lower()) if t]
    if not toks:
        return False
    if toks[0] in DOT_REJECT_VERDICTS:
        return True
    return len(toks) >= 2 and (toks[0], toks[1]) in (("no", "go"), ("out", "of"))


def read_dot_rows(path: str) -> List[Dict[str, Any]]:
    """Rows of the DOT candidate CSV as dicts (every column kept; missing columns tolerated)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def dot_candidates(path: str, region: Any = "manhattan_s110", merge_m: float = 80.0, cap: int = 60,
                   hub_types: Sequence[str] = DOT_HUB_TYPES, with_lattice: bool = True, min_hub: int = 4,
                   lattice_hub_fallback: int = 8, max_hub: int = 12, restaurants: Any = None,
                   lattice: Optional[Sequence[Candidate]] = None
                   ) -> Tuple[List[Candidate], List[Dict[str, Any]], Dict[str, Any]]:
    """DOT-based candidate set of the ``manhattan_dot`` family (design 1.1), deterministic.

    1. Rows of ``path`` with numeric ``lat`` / ``lon`` inside the region band (``StudyRegion.
       in_band``); rows outside, without coordinates or with a rejecting ``verdict``
       (:data:`DOT_REJECT_VERDICTS`) are returned in ``dropped`` with the reason.  The type comes
       from ``site_type`` (or ``type``); unknown values are ``'other'``.  Unknown columns are kept
       in ``Candidate.label`` through ``name`` / ``address`` only (the raw row is in ``dropped``
       / ``info['rows']``).
    2. Snap to the 150 m grid (``box.snap``); ``snap_m`` = metres from the raw point to the node.
    3. Merge rows whose raw points are closer than ``merge_m`` or whose nodes coincide; the
       survivor is the best ``(type priority, restaurants at the node, input order)``; merged
       names go to ``merged_labels``.
    4. Union with :func:`lattice_candidates` (``with_lattice``; or the given ``lattice`` list) by
       the same rule, lattice below every DOT type; the survivor keeps ``lattice_id``.
    5. ``hub_capable`` = type in ``hub_types``; if fewer than ``min_hub`` qualify, the
       ``lattice_hub_fallback`` lattice candidates with most restaurants are added; at most
       ``max_hub`` hub-capable sites, filled in :data:`DOT_HUB_PRIORITY` order (depot, lot,
       fdny_hub, citibike_charging; ties: more restaurants at the node, then input order; lattice
       fallback cells last); the rest are set non-capable.  The hub type of a merged survivor is
       the best one among the rows it absorbed (an operator store merged into a pilot row keeps
       the operator store's slot).  Applied after the cap of step 6, so a capped row never holds a
       hub slot (the cap does not depend on hub capability).
    6. Cap at ``cap``: drop ``other`` rows with the fewest restaurants within 4 blocks, then ``lot``.
    7. Ids ``D01..`` south -> north, west -> east by lattice cell ``(cy, cx)`` then node ``(iy,
       ix)`` (the order of the lattice ids, so the 15-point fixture reproduces ``M01..M15`` in
       order); ``rank`` = input order; ``cell`` = lattice cell; ``cls`` = ``dot`` / ``lattice`` /
       ``both``.

    Returns ``(candidates, dropped, info)``; ``info`` carries the counts of the plan record."""
    from . import data_nyc as dn

    reg = dn.resolve_region(region)
    box = reg.box
    rest = dn.region_restaurants(reg) if restaurants is None else restaurants
    counts: Dict[Node, int] = {}
    for v in rest["node"]:
        v = _node(v)
        counts[v] = counts.get(v, 0) + 1
    rows = read_dot_rows(path) if path and os.path.exists(path) else []
    dropped: List[Dict[str, Any]] = []
    raw: List[Candidate] = []
    #: projected raw point per candidate OBJECT (``id(c)``), never per id string: duplicate ids
    #: (or a DOT id equal to a lattice id) must not alias two rows kilometres apart (fixer pass)
    xy: Dict[int, Tuple[float, float]] = {}
    lat_c = list(lattice if lattice is not None else (lattice_candidates(region=reg, restaurants=rest) if with_lattice else []))
    reserved = {str(c.id) for c in lat_c}
    seen_ids: Dict[str, int] = {}
    renamed: Dict[str, str] = {}
    verdict_dropped: List[Dict[str, Any]] = []
    verdicts: Dict[str, int] = {}
    for i, r in enumerate(rows):
        rid0 = str(r.get("id") or f"row{i + 1}")
        rid = rid0
        if rid in reserved:                     # a DOT id spelled like a lattice id: keep both apart
            rid = f"{rid0}~dot"
        n_prev = seen_ids.get(rid, 0)
        seen_ids[rid] = n_prev + 1
        if n_prev:
            rid = f"{rid}~{n_prev + 1}"
        if rid != rid0:
            renamed[rid] = rid0
        name = str(r.get("name") or rid0)
        try:
            lat, lon = float(r.get("lat")), float(r.get("lon"))
        except (TypeError, ValueError):
            dropped.append({**r, "reason": "missing or non-numeric lat/lon"})
            continue
        v = str(r.get("verdict") or "").strip()
        if _rejected(v):
            dropped.append({**r, "reason": f"verdict {v!r}"})
            verdict_dropped.append({"id": rid0, "name": name, "verdict": v})
            continue
        if v:
            verdicts[v] = verdicts.get(v, 0) + 1
        if not reg.in_band(lat, lon):
            dropped.append({**r, "reason": "outside the region band (box or north of the boundary)"})
            continue
        node = box.snap(lat, lon)
        px, py = box.project(lat, lon)
        nx, ny = box.node_xy(node)
        t = _dot_type(r.get("site_type", r.get("type")))
        label = name + (f", {r['address']}" if r.get("address") else "")
        c = Candidate(id=rid, label=label, source=f"dot:{t}", lat=lat, lon=lon, node=node, grid_connected=False,
                      n_restaurants=counts.get(node, 0), rank=i + 1, hub_capable=t in set(hub_types),
                      snap_m=float(math.hypot(px - nx, py - ny)), dot_type=t, cell=lattice_cell_of(box, node), cls="dot")
        raw.append(c)
        xy[id(c)] = (px, py)
    n_dot_in = len(raw)
    if with_lattice:
        for c in lat_c:
            px, py = box.node_xy(c.node)
            lc = Candidate(id=c.id, label=c.label, source="lattice", lat=c.lat, lon=c.lon, node=c.node,
                           n_restaurants=c.n_restaurants, rank=n_dot_in + c.rank, hub_capable=False,
                           lattice_id=c.id, snap_m=0.0, dot_type=None, cell=lattice_cell_of(box, c.node), cls="lattice")
            raw.append(lc)
            xy[id(lc)] = (px, py)
    # best hub type per candidate OBJECT (index in DOT_HUB_PRIORITY; len = none / not listed):
    # carried through the merge, so an operator store absorbed by a pilot row keeps its hub slot
    n_hp = len(DOT_HUB_PRIORITY)
    hub_type_rank: Dict[int, int] = {id(c): (DOT_HUB_PRIORITY.index(c.dot_type) if c.hub_capable and
                                              c.dot_type in DOT_HUB_PRIORITY else n_hp) for c in raw}
    # merge --------------------------------------------------------------------------
    kept: List[Candidate] = []
    n_merged = 0
    for c in raw:
        near = [k for k in kept if k.node == c.node
                or math.hypot(xy[id(k)][0] - xy[id(c)][0], xy[id(k)][1] - xy[id(c)][1]) < float(merge_m) - 1e-9]
        if not near:
            kept.append(c)
            continue
        host = near[0]
        n_merged += 1
        better = (_priority(c), -c.n_restaurants, c.rank) < (_priority(host), -host.n_restaurants, host.rank)
        win, lose = (c, host) if better else (host, c)
        win.merged_labels = list(win.merged_labels) + [lose.label] + list(lose.merged_labels)
        win.hub_capable = bool(win.hub_capable or lose.hub_capable)
        hub_type_rank[id(win)] = min(hub_type_rank[id(win)], hub_type_rank[id(lose)])
        if lose.lattice_id and not win.lattice_id:
            win.lattice_id = lose.lattice_id
        if {win.cls, lose.cls} == {"dot", "lattice"} or lose.cls == "both" or win.cls == "both":
            win.cls = "both"
        if better:
            kept[kept.index(host)] = c
    # cap ---------------------------------------------------------------------------
    # before the hub-capable set (adversarial review of 2026-10-21): a capped lot must not hold a
    # hub slot that a kept dock or depot would otherwise get (the cap does not read hub_capable)
    capped: List[Dict[str, Any]] = []
    def near_rest(c: Candidate) -> int:
        return sum(n for v, n in counts.items() if manhattan_blocks(v, c.node) <= 4)
    for drop_type in ("other", "lot"):
        while len(kept) > int(cap):
            pool = [c for c in kept if c.dot_type == drop_type and not c.lattice_id]
            if not pool:
                break
            victim = min(pool, key=lambda c: (near_rest(c), -c.rank))
            kept.remove(victim)
            capped.append({"id": victim.id, "name": victim.label, "type": victim.dot_type, "reason": f"cap {cap}: {drop_type} with fewest restaurants within 4 blocks"})
    dropped.extend(capped)
    # hub-capable set ----------------------------------------------------------------
    n_hub_dot = sum(1 for c in kept if c.hub_capable)
    hub_fallback: List[str] = []
    if n_hub_dot < int(min_hub):
        lat_pool = sorted([c for c in kept if c.lattice_id and not c.hub_capable],
                          key=lambda c: (-c.n_restaurants, c.lattice_id))
        for c in lat_pool[:int(lattice_hub_fallback)]:
            c.hub_capable = True
            hub_fallback.append(c.lattice_id or c.id)
    def hub_rank(c: Candidate) -> int:          # best hub type over the merged rows; lattice fallback last
        return hub_type_rank.get(id(c), n_hp)
    hubs = sorted([c for c in kept if c.hub_capable], key=lambda c: (hub_rank(c), -c.n_restaurants, c.rank))
    for c in hubs[int(max_hub):]:
        c.hub_capable = False
    # ids ---------------------------------------------------------------------------
    # south -> north, west -> east by lattice cell (the order of the lattice ids), then by node
    kept.sort(key=lambda c: ((c.cell[1], c.cell[0]) if c.cell else (0, 0))
              + ((c.node[1], c.node[0]) if isinstance(c.node, tuple) else (c.node, 0)))
    out: List[Candidate] = []
    for i, c in enumerate(kept):
        c = copy.copy(c)
        c.merged_labels = list(c.merged_labels)
        c.label = f"{c.label} [{c.id}]"
        c.id = f"D{i + 1:02d}"
        out.append(c)
    info = {"n_rows": len(rows), "n_dot_in_region": n_dot_in, "n_dropped": len(dropped) - len(capped),
            "n_capped": len(capped), "n_lattice": sum(1 for c in raw if c.cls == "lattice"), "n_merged": n_merged,
            "n_candidates": len(out), "n_dot": sum(1 for c in out if c.cls in ("dot", "both")),
            "n_lattice_only": sum(1 for c in out if c.cls == "lattice"), "n_both": sum(1 for c in out if c.cls == "both"),
            "n_hub_capable": sum(1 for c in out if c.hub_capable), "hub_fallback_lattice": hub_fallback,
            "snap_m_max": max([c.snap_m for c in out], default=0.0), "merge_m": float(merge_m), "cap": int(cap),
            "hub_types": list(hub_types), "types": sorted({c.dot_type for c in out if c.dot_type}), "path": path,
            "file_present": bool(path and os.path.exists(path)),
            # fixer pass: what the author must see before stage setup
            "renamed_ids": renamed, "verdict_dropped": verdict_dropped, "verdicts_kept": verdicts,
            "reject_tokens": list(DOT_REJECT_VERDICTS)}
    return out, dropped, info


def write_candidate_tables(cands: Sequence[Candidate], dropped: Sequence[Dict[str, Any]], out_dir: str) -> Dict[str, str]:
    """``candidates.csv`` and ``candidates_dropped.csv`` of :func:`dot_candidates` in ``out_dir``."""
    os.makedirs(out_dir, exist_ok=True)
    p1 = os.path.join(out_dir, "candidates.csv")
    cols = ["id", "label", "cls", "dot_type", "lattice_id", "lat", "lon", "node_x", "node_y", "cell_x", "cell_y",
            "snap_m", "n_restaurants", "hub_capable", "rank", "merged_labels"]
    with open(p1, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for c in cands:
            nx, ny = (c.node[0], c.node[1]) if isinstance(c.node, tuple) else (c.node, "")
            cx, cy = (c.cell[0], c.cell[1]) if c.cell else ("", "")
            w.writerow([c.id, c.label, c.cls, c.dot_type or "", c.lattice_id or "", c.lat, c.lon, nx, ny, cx, cy,
                        round(c.snap_m, 1), c.n_restaurants, int(bool(c.hub_capable)), c.rank, " | ".join(c.merged_labels)])
    p2 = os.path.join(out_dir, "candidates_dropped.csv")
    keys: List[str] = []
    for r in dropped:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys or ["reason"])
        w.writeheader()
        for r in dropped:
            w.writerow({k: r.get(k, "") for k in (keys or ["reason"])})
    return {"candidates": p1, "dropped": p2}


#: Demand levels of the stratified scenario design (orders per bike-hour; 8 bikes x 4 h ->
#: 32 / 40 / 48 orders) and the day-type weights (5 weekdays / 2 weekend days).
SCENARIO_LEVELS: Tuple[float, ...] = (1.0, 1.25, 1.5)
SCENARIO_DAY_WEIGHTS: Dict[str, float] = {"weekday": 5.0 / 7.0, "weekend": 2.0 / 7.0}


def scenario_design(S: int = 12, held_out: bool = False, levels: Sequence[float] = SCENARIO_LEVELS,
                    seed_base: Optional[int] = None) -> List[Dict[str, Any]]:
    """Stratified scenario design of the scale-up (design 1.7): 6 strata = 3 demand levels x
    weekday / weekend, two seeds per stratum at ``S = 12`` (``p_s`` = day weight x 1/3 / 2).
    ``S = 6``: one seed per stratum; ``S = 10``: strata 1-3 (weekday) with two seeds and the
    weekend mid level with four seeds (the other weekend strata folded into it); ``S = 15``:
    three seeds for the weekday strata.  Seeds ``seed_base + i`` with ``seed_base`` 0 in-sample
    and 100 held out (``held_out``).  Weekday scenarios use the family's own time profile;
    weekend scenarios use the generator's ``'weekend'`` hourly shape (``demand_spec.profile``)
    with ``day_type='weekend'`` recorded; the order count follows the level.  Returns
    ``[{'seed', 'stratum', 'day_type', 'level', 'orders_per_bike_hour', 'p', 'seed_in_stratum',
    'overrides'}]`` with ``sum p = 1``."""
    S = int(S)
    base = (100 if held_out else 0) if seed_base is None else int(seed_base)
    levels = [float(x) for x in levels]
    strata: List[Tuple[str, float, float, int]] = []    # (day, level, weight, n_seeds)
    if S == 6:
        for day in ("weekday", "weekend"):
            for lv in levels:
                strata.append((day, lv, SCENARIO_DAY_WEIGHTS[day] / len(levels), 1))
    elif S == 10:
        for lv in levels:
            strata.append(("weekday", lv, SCENARIO_DAY_WEIGHTS["weekday"] / len(levels), 2))
        strata.append(("weekend", levels[len(levels) // 2], SCENARIO_DAY_WEIGHTS["weekend"], 4))
    elif S == 12:
        for day in ("weekday", "weekend"):
            for lv in levels:
                strata.append((day, lv, SCENARIO_DAY_WEIGHTS[day] / len(levels), 2))
    elif S == 15:
        for day, n in (("weekday", 3), ("weekend", 2)):
            for lv in levels:
                strata.append((day, lv, SCENARIO_DAY_WEIGHTS[day] / len(levels), n))
    else:
        raise ValueError("scenario_design supports S in {6, 10, 12, 15}")
    out: List[Dict[str, Any]] = []
    seed = base
    for k, (day, lv, w, n) in enumerate(strata):
        for j in range(n):
            over: Dict[str, Any] = {"orders_per_bike_hour": lv}
            if day == "weekend":
                over["demand_spec"] = {"profile": "weekend", "day_type": "weekend"}
            out.append({"seed": seed, "stratum": k + 1, "day_type": day, "level": lv, "orders_per_bike_hour": lv,
                        "p": w / n, "seed_in_stratum": j, "overrides": over})
            seed += 1
    tot = sum(r["p"] for r in out)
    for r in out:
        r["p"] = r["p"] / tot
    return out


def lp_scenario_subset(design: Sequence[Dict[str, Any]]) -> List[int]:
    """Indices of the first seed of every stratum (the ``S_LP`` scenarios of the B&B, design 2.3)."""
    return [i for i, r in enumerate(design) if int(r.get("seed_in_stratum", 0)) == 0]


def _apply_post(inst: Instance, post: Dict[str, Any]) -> None:
    """Post-build data steps of :data:`SITING_POST` (energy calibration A1: ``q_res`` levels and
    ``energy_rounding``; tariff M5: per-slot price list ``meta['pi_schedule']``)."""
    ecal_name = post.get("energy_calibration")
    if ecal_name:
        from .config import energy_calibration
        ecal = energy_calibration(ecal_name, Delta_h=inst.disc.Delta_h, eta=inst.disc.eta)
        if int(ecal["L"]) != inst.L or abs(float(ecal["eps_kwh"]) - inst.disc.eps_kwh) > 1e-12:
            raise ValueError("family L / eps do not match the energy calibration")
        inst.q_res = int(ecal["q_res"])
        inst.options["energy_rounding"] = str(ecal["energy_rounding"])
        inst.meta["energy_calibration"] = _py(dict(ecal))
        inst.meta.setdefault("costs", {})["q_res"] = int(ecal["q_res"])
    tariff = post.get("tariff")
    if tariff:
        from .costs import load_tariff
        tar = load_tariff(tariff)
        lo, hi = tar["facilities_spec"].get("price_peak_hours", (0.0, 0.0))
        start = float(inst.meta.get("window_h", [0.0])[0])
        pi_off = float(tar["costs"].get("pi", inst.meta["costs"]["pi"]))
        pi_peak = float(tar["costs"].get("pi_peak", pi_off))
        sched = [pi_peak if lo <= start + t * inst.disc.Delta_h < hi else pi_off for t in range(inst.H)]
        inst.meta["pi_schedule"] = sched
        inst.meta["tariff"] = {"name": tar["name"], "source": str(tar["source"]), "pi": pi_off, "pi_peak": pi_peak,
                               "price_peak_hours": [float(lo), float(hi)]}
        inst.meta["price_peak_hours"] = [float(lo), float(hi)]
        inst.meta["costs"]["pi"] = pi_off
        inst.meta["costs"]["pi_peak"] = pi_peak
        inst.pi = float(sched[0])   # flat until facilities exist; _finish expands a time-varying schedule
    try:
        from .generator import riding_intensity
        inst.meta["r5"] = _py({"plan_items": ["M6", "A1", "M5"], "intensity": riding_intensity(inst)})
    except ImportError:  # pragma: no cover
        pass
