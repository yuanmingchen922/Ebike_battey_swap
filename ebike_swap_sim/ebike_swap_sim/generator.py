"""Synthetic E2 instance generator (NYC e-bike delivery, battery swapping).

Mirrors the OD generator of the *Ebike Battery Swap* deck (p.5: time-dependent
generator, demographic destination sampler, restaurant-type sampler) and the
``instance_generator_spec`` of ``notes/workflow1_result.json``; binding defaults
are those of ``notes/DECISIONS.md`` ("Default discretisation for synthetic
experiments").  Output is a plain :class:`~ebike_swap_sim.or_instance.Instance`
that passes ``validate()`` and round-trips through JSON byte-identically for a
given seed, so that ``ilp.py`` and ``baseline.py`` consume the same data.

Equation numbers refer to ``notes/extracted/E2.txt``.

Pipeline of :func:`make_synthetic_instance`
-------------------------------------------
1. ``GridNetwork`` of ``sub_grid`` nodes (default 20 x 20 blocks of 150 m, i.e. a
   3 km square) with ``zones_side x zones_side`` zones (default 4 x 4) and
   synthetic per-zone demographics (population, young share, income factor,
   commercial score) drawn once from the seed.
2. Road-node set ``V`` (E2 Section 3): restaurants (denser in commercial zones),
   facility nodes (zone centres of the busiest restaurant zones, plus charge hubs
   in ``separated`` mode), depots (bike start nodes) and a customer anchor
   lattice (every ``anchor_spacing`` blocks).  Every ordered pair of ``V`` gets
   the unique shortest road route from ``GridNetwork.route`` with raw physical
   values ``T_h = length_m / speed_m_per_min / 60``, ``E_kwh`` from the config
   energy model (``wh_per_km``, ``wh_per_m_climb``, ``wh_per_light``) and
   ``d_km``; the discrete ``tau_r``, ``g_r`` of (1) are derived later by the
   :class:`~ebike_swap_sim.or_instance.Discretisation`.
3. Orders (E2 Section 3): release minutes from :class:`TimeDependentGenerator`,
   customer from :class:`DemographicDestinationSampler` (snapped to the anchor
   lattice), restaurant and prep time from :class:`RestaurantTypeSampler`;
   ``r_i = floor(min / Delta)``, ``a_i = r_i + ceil(prep / Delta)``,
   ``b_i = r_i + promise_slots`` (default 9), ``hp = hd = 1``; platform label
   ``phi(i)`` for reporting only.
4. Facilities (7)-(8), (15), (17), (20)-(22): co-located swap+charge sites by
   default, or swap-only sites plus 1-2 charge-only hubs (``separated``); one
   grid group for the sites (peak-hour limit) and one per hub (21).
5. Transport services (Section 5, (10)): shuttles hub <-> site in both
   directions every ``every`` slots with duration ``ceil((route_min + handling)
   / Delta)``, ``U = 6``, ``f = 5``, ``v_reb = 0.2``; only when hubs exist, plus
   optional hourly site <-> site services.
6. Bikes: depots round robin, ``q0 ~ U{ceil(0.4 L), ..., L}``.
7. ``options['node_zone']`` (zone of every node of ``V`` for the baseline's
   zone dispatch; JSON-safe list of ``[node, zone]`` pairs, decode with
   :func:`node_zone_map`) and ``meta`` with every generator parameter.

Replacing the synthetic modules by real data
--------------------------------------------
The three OD modules share small abstract interfaces (:class:`ReleaseTimeGenerator`,
:class:`DestinationSampler`, :class:`RestaurantSampler`) and are injected into
:func:`make_synthetic_instance` through ``od_modules``.  Planned real-data
implementations with the *same* interface: DOHMH restaurant inspection results
(lat/lon + cuisine, deduplicated by CAMIS) for :class:`RestaurantSampler`; NYC
Neighborhood ACS 2008-12 (population, median income, 18-34 share on NTA
polygons) for the zone weights of :class:`DestinationSampler`; Kaggle
food-delivery timestamps for the weekday/weekend ratio and prep-time
distribution of :class:`ReleaseTimeGenerator`.  A real road network only has to
implement :class:`~ebike_swap_sim.network.RoadNetwork` (``nodes``,
``node_zone``, ``zone_nodes``, ``route``) to be used by :func:`build_route_library`.

Round 2 (``notes/DECISIONS.md`` R2.1 / R2.2)
---------------------------------------------
:func:`make_synthetic_instance` has a *round-2 mode*, entered by giving the
window length ``window_h`` (or ``round2=True``).  In that mode the defaults of
R2.2 apply unless overridden explicitly: ``H = window_h * 60 / Delta_min``
(4 h -> 48), ``window_start_hour = 17.0`` (dinner 17:00-21:00),
``n_orders = round(orders_per_bike_hour * n_bikes * window_h)`` with 1.5 orders
per bike-hour (10 bikes x 4 h -> 60), bikes start at ``q0 ~ U{ceil(0.3 L) ..
floor(0.6 L)}``, co-located sites with ``B_j = 3`` and ``C_j = 2``
(:data:`DEFAULT_FACILITIES_SPEC_R2`), cost coefficients from
:mod:`ebike_swap_sim.costs` (``cost_variant='usd_sunk'``, window-scaled, R2.1),
Kaggle-calibrated order attributes (``kaggle_calibrated=True``: prep ~
DiscreteUniform{20..35} min, promise ``b_i = a_i + ceil(25 min / Delta)``,
cuisine shares and Zipf ``s = 1.0`` restaurant popularity within a cuisine,
:class:`KaggleRestaurantSampler`) and the declared time-of-day profile
:data:`TIME_PROFILE_R2` (flagged ``'assumption'``; lunch 28 % / dinner 45 % /
late 12 % / rest 15 %, weekend x1.15) used by :class:`TimeDependentGenerator`
over the window.  Legacy calls (``H`` given, no ``window_h``) are byte-identical
to round 1: old defaults (``B = 4``, ``C = 3``, ``q0 ~ U{ceil(0.4 L)..L}``, toy
costs, synthetic cuisines, hourly profile) and an unchanged ``meta``.  The old
defaults stay reachable in round-2 mode through the explicit arguments
(``facilities_spec={'B': 4, 'C': 3}``, ``init_frac=(0.4, 1.0)``,
``cost_variant='toy'``, ``kaggle_calibrated=False``, ``time_profile='weekday'``).

No solver import: this module depends on numpy and the package data classes only.
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from . import costs as cost_mod
from .arcs import ArcLibrary, build_arcs
from .config import SimConfig
from .network import GridNetwork, RoadNetwork
from .network import Route as GridRoute
from .or_instance import Bike, Discretisation, Facility, Instance, Node, Order, Route, Service

__all__ = [
    "HOURLY_PROFILES", "DEFAULT_PHYSICS", "DEFAULT_DEMAND_SPEC", "DEFAULT_FACILITIES_SPEC",
    "DEFAULT_SERVICES_SPEC", "DEFAULT_COSTS", "DEFAULT_CUISINES",
    "DEFAULT_FACILITIES_SPEC_R2", "R2_DEFAULTS", "TIME_PROFILE_R2", "DEFAULT_KAGGLE_PATH",
    "load_kaggle_calibration", "block_profile", "profile_integral",
    "ReleaseTimeGenerator", "TimeDependentGenerator",
    "DestinationSampler", "DemographicDestinationSampler",
    "RestaurantSampler", "RestaurantTypeSampler", "KaggleRestaurantSampler",
    "ZoneDemographics", "synthetic_zone_demographics",
    "anchor_lattice", "zone_centres", "snap_to_anchor", "place_restaurants",
    "apportion_counts",
    "route_physics", "build_route_library",
    "make_synthetic_instance", "default_pruning", "node_zone_map", "estimate_arcs",
]

# ---------------------------------------------------------------------------
# defaults (DECISIONS.md "Default discretisation", plan instance_generator_spec)
# ---------------------------------------------------------------------------
#: Relative order intensity at the top of every hour ``h = 0..23`` (piecewise
#: linear in between, periodic).  Lunch peak 12-13 h (1.0), dinner peak
#: 18:00-20:00 (1.2 weekday, 1.4 weekend), 0.2 at night (deck p.5 / plan).
HOURLY_PROFILES: Dict[str, List[float]] = {
    "weekday": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.4, 0.5, 0.4, 0.4, 0.7,
                1.0, 1.0, 0.6, 0.4, 0.5, 0.8, 1.2, 1.2, 0.9, 0.6, 0.4, 0.3],
    "weekend": [0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8,
                1.0, 1.0, 0.7, 0.5, 0.6, 0.9, 1.4, 1.4, 1.1, 0.8, 0.5, 0.4],
}

_CFG = SimConfig()
#: Physical route model (config.py): speed and the energy model of the deck
#: (length, climb, signalised nodes).  ``light_delay_s`` is an optional stop
#: penalty per signal (0 = the task's ``T_h = length_m / 250 / 60``).
DEFAULT_PHYSICS: Dict[str, float] = {
    "speed_m_per_min": _CFG.speed_m_per_min,      # 250 m/min ~ 15 km/h
    "wh_per_km": _CFG.wh_per_km,                  # 12 Wh/km
    "wh_per_m_climb": _CFG.wh_per_m_climb,        # 0.6 Wh per metre of ascent
    "wh_per_light": _CFG.wh_per_light,            # 0.4 Wh per signalised node
    "light_delay_s": 0.0,
    "block_m": _CFG.block_m,                      # 150 m
    "traffic_light_prob": _CFG.traffic_light_prob,  # 0.5
}

#: Cuisines with mean prep time (min); prep ~ U(mean - spread, mean + spread).
DEFAULT_CUISINES: Dict[str, float] = {"pizza": 10.0, "chinese": 15.0, "fine_dining": 25.0}

DEFAULT_DEMAND_SPEC: Dict[str, Any] = {
    "profile": "weekday",          # key of HOURLY_PROFILES or a 24-list
    "window_start_h": 17.5,        # dinner window starts 17:30 (hours of day)
    "tail_slots": 8,               # no new releases in the last tail_slots slots
    "exact_count": True,           # exactly n_orders releases (else Poisson(n_orders))
    "promise_slots": 9,            # b_i = r_i + 9 (45 min at Delta = 5 min)
    "prep_spread_min": 5.0,        # prep ~ U(mean - 5, mean + 5) per cuisine
    "cuisines": DEFAULT_CUISINES,
    "nearest_k": 3,                # restaurant = random among the k nearest of the cuisine
    "hp": 1, "hd": 1,              # pickup / handoff slots (config 3.0 / 1.5 min)
    "P": 100.0, "w": 12.0, "v": 24.0,   # unserved penalty, response and lateness per hour (30)-(31)
    "platforms": {"A": 0.5, "B": 0.3, "C": 0.2},   # phi(i) shares (reporting only)
    "init_frac": (_CFG.init_battery_min_frac, _CFG.init_battery_max_frac),  # q0 ~ U{ceil(0.4L)..L}
}

DEFAULT_FACILITIES_SPEC: Dict[str, Any] = {
    "mode": "colocated",           # 'colocated' (S = C = N) or 'separated' (swap sites + charge hubs)
    "n_sites": 3,                  # sites at the centres of the busiest restaurant zones
    "n_hubs": 1,                   # charge-only hubs (separated mode only)
    "fixed": True,                 # y, B, C fixed data (False: free, decided by the ILP)
    "K": 8, "Cbar": 6, "M": 1, "sigma": 1, "P_kw": 4.0,
    "B": 4, "C": 3,                # default sizes (sum B = 12 ~ 1.2 |K| for 10 bikes)
    "R_end": 1,
    "hub": {"K": 30, "Cbar": 20, "P_kw": 12.0, "B": 4, "C": 6, "R_end": 0},
    "grid_sites_kw": 8.0,          # shared supply group of the sites (21)
    "grid_sites_peak_kw": 6.0,     # ... during peak hours
    "peak_hours": (18.0, 20.0),    # grid-limit peak; price peak = 'price_peak_hours' (default: same; TOU: (8, 22))
}

DEFAULT_SERVICES_SPEC: Dict[str, Any] = {
    "every": 6,                    # departures every 6 slots (30 min) ...
    "first": 2,                    # ... starting at boundary 2
    "handling_min": 10.0,          # duration = ceil((route_min + handling) / Delta)
    "U": 6, "f": 5.0, "vreb": 0.2,
    "site_site": False,            # optional services between swap sites
    "site_site_every": 12,         # hourly
}

#: Toy unit system of E2 p.14 (kept for comparability; a USD layer can rescale later).
DEFAULT_COSTS: Dict[str, Any] = {
    "kappa": 1.0,                  # per km (29)
    "pi": 2.0,                     # per purchased kWh (28), flat
    "pi_peak": None,               # e.g. 3.0 -> dict price during peak_hours
    "F": 20.0, "F_hub": 40.0,      # horizon-allocated site cost (27)
    "bB": 3.0, "bC": 2.0,          # per spare battery / charger (27)
    "Fhat": 5000.0, "bhat": 500.0, "chat": 300.0,   # investment coefficients (33)
    "q_res": 1, "rho": 0.5,        # terminal reserve (9), network recovery share (18)
}

# ---------------------------------------------------------------------------
# round-2 defaults (DECISIONS.md R2.1 / R2.2)
# ---------------------------------------------------------------------------
#: R2.2 facility defaults: every co-located site ``B_j = 3`` spares (sweep 2-3),
#: ``C_j = 2`` chargers; ``K = 8``, ``M = 1``, ``sigma = 1``, ``P_j = 4 kW`` and the
#: 8 kW (6 kW 18-20 h) grid group are unchanged from round 1.  Swap-only sites of
#: separated layouts get ``B = 3``, ``C = 0`` automatically.
DEFAULT_FACILITIES_SPEC_R2: Dict[str, Any] = {**DEFAULT_FACILITIES_SPEC, "B": 3, "C": 2}

#: Declared time-of-day profile (R2.2; ``notes/literature_demand_model.md`` section 6
#: item 3).  **No paper supports a profile**, hence ``status = 'assumption'``.  Shares
#: of the daily order volume per block, piecewise constant inside a block; the rest
#: of the day (``24 h - sum of block lengths = 14 h``) carries ``rest_share``
#: uniformly.  Hours may exceed 24 (late block 21:30-01:00 = 21.5-25.0; the
#: profile is periodic).  Weekend volume = ``weekend_factor`` x weekday volume.
TIME_PROFILE_R2: Dict[str, Any] = {
    "name": "r2_lunch_dinner_late",
    "status": "assumption",
    "source": "DECISIONS.md R2.2; notes/literature_demand_model.md section 6 (placeholder until "
              "the DCWP 2022 hourly trip distribution is digitised)",
    "blocks": [
        {"name": "lunch", "start_h": 11.5, "end_h": 14.0, "share": 0.28},
        {"name": "dinner", "start_h": 17.5, "end_h": 21.5, "share": 0.45},
        {"name": "late", "start_h": 21.5, "end_h": 25.0, "share": 0.12},
    ],
    "rest_share": 0.15,
    "weekend_factor": 1.15,
}

#: Round-2 scalar defaults of :func:`make_synthetic_instance` (R2.2), applied in
#: round-2 mode when the corresponding argument is ``None``.
R2_DEFAULTS: Dict[str, Any] = {
    "window_h": 4.0,                 # H = 48 at Delta = 5 min
    "window_start_hour": 17.0,       # dinner window 17:00-21:00 (8 h sensitivity: 14:00-22:00)
    "orders_per_bike_hour": 1.5,     # 10 bikes x 4 h -> 60 orders
    "init_frac": (0.3, 0.6),         # q0 ~ U{ceil(0.3 L) .. floor(0.6 L)} = 4..7 for L = 12
    "cost_variant": "usd_sunk",      # R2.1 default
    "kaggle_calibrated": True,       # prep / promise / cuisine / Zipf from kaggle_calibration.json
    "time_profile": "r2",            # TIME_PROFILE_R2 ('weekday' / 'weekend' = old hourly profiles)
    "day_type": "weekday",
    "promise_after_ready_min": 25.0,  # b_i = a_i + ceil(25 min / Delta) (Kaggle delivery-time centre)
    "zipf_s": 1.0,                   # restaurant popularity within cuisine (R2.2)
    "restaurant_radius_km": 2.5,     # candidate radius around the customer (R2.4), expand if < 3
    "restaurant_min_candidates": 3,
}

#: ``notes/data/kaggle_calibration.json`` relative to the package.
DEFAULT_KAGGLE_PATH: str = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "data",
    "kaggle_calibration.json"))


def load_kaggle_calibration(path: Optional[str] = None) -> Dict[str, Any]:
    """Order-attribute calibration of R2.2 from ``notes/data/kaggle_calibration.json``.

    Returns ``{'source', 'prep_min_range': [20, 35] (DiscreteUniform, recommendation
    of the file), 'promise_after_ready_min': 25.0 (Kaggle delivery-time centre,
    R2.2), 'delivery_time_mean_min', 'cuisine_shares': {cuisine: share} (Kaggle
    order shares, normalised), 'cuisine_mean_prep_min', 'zipf_s': 1.0 (loglog slope
    of the restaurant popularity for counts >= 5 is -1.00), 'zipf_slope_observed'}``.
    """
    src = path or DEFAULT_KAGGLE_PATH
    with open(src, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    prep = data["food_preparation_time"]
    shares = {str(k): float(v) for k, v in data["cuisine_shares"].items()}
    tot = sum(shares.values())
    shares = {k: v / tot for k, v in shares.items()}
    pop = data.get("restaurant_popularity", {})
    return {
        "source": src,
        "prep_min_range": [int(prep["min"]), int(prep["max"])],
        "promise_after_ready_min": float(R2_DEFAULTS["promise_after_ready_min"]),
        "delivery_time_mean_min": float(data["delivery_time"]["mean"]),
        "cuisine_shares": shares,
        "cuisine_mean_prep_min": {str(k): float(v) for k, v in data.get("cuisine_mean_prep_time", {}).items()},
        "zipf_s": float(R2_DEFAULTS["zipf_s"]),
        "zipf_slope_observed": float(pop.get("zipf_loglog_counts_ge5", {}).get("slope", float("nan"))),
    }


def block_profile(cfg: Dict[str, Any] = TIME_PROFILE_R2, day_type: str = "weekday"
                  ) -> Callable[[float], float]:
    """Density (share of the *weekday* daily volume per hour) of a block profile
    such as :data:`TIME_PROFILE_R2` (R2.2 'time-of-day profile', assumption).

    Inside block ``k`` the density is ``share_k / (end_k - start_k)``; outside all
    blocks it is ``rest_share / (24 - sum_k (end_k - start_k))``; the function is
    periodic in 24 h.  ``day_type='weekend'`` multiplies by ``weekend_factor``
    (1.15), so the weekday profile integrates to 1 over a day and the weekend
    profile to 1.15 (:func:`profile_integral`).  Block hours may run past 24.
    """
    blocks = [(float(b["start_h"]), float(b["end_h"]), float(b["share"])) for b in cfg["blocks"]]
    block_len = sum(e - s for s, e, _ in blocks)
    if block_len >= 24.0 - 1e-9:
        raise ValueError("blocks must leave some rest time in the day")
    rest_density = float(cfg.get("rest_share", 0.0)) / (24.0 - block_len)
    factor = float(cfg.get("weekend_factor", 1.0)) if day_type == "weekend" else 1.0
    if day_type not in ("weekday", "weekend"):
        raise ValueError("day_type must be 'weekday' or 'weekend'")

    def density(hour: float) -> float:
        h = float(hour) % 24.0
        for s, e, share in blocks:
            # a block may wrap past midnight (e.g. 21.5-25.0): test h and h + 24
            if s <= h < e or s <= h + 24.0 < e:
                return factor * share / (e - s)
        return factor * rest_density

    return density


def profile_integral(density: Callable[[float], float], start_h: float = 0.0, end_h: float = 24.0,
                     n: int = 24 * 60 * 4) -> float:
    """Midpoint-rule integral of a density over ``[start_h, end_h]`` (``n`` steps of
    15 s by default) -- used to verify that a profile integrates to the daily
    volume (weekday 1.0, weekend ``weekend_factor``)."""
    step = (end_h - start_h) / n
    return float(sum(density(start_h + (k + 0.5) * step) for k in range(n)) * step)


def _merge(default: Dict[str, Any], given: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Shallow merge of ``given`` over ``default`` (one nested level for dict values)."""
    out = dict(default)
    for key, val in (given or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out


def _py(x: Any) -> Any:
    """Convert numpy scalars / tuples recursively into JSON-native Python values."""
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, (tuple, list)):
        return [_py(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _py(v) for k, v in x.items()}
    return x


def _node(n: Any) -> Node:
    """Grid node as a tuple of Python ints."""
    return tuple(int(v) for v in n)


# ---------------------------------------------------------------------------
# zone demographics
# ---------------------------------------------------------------------------
@dataclasses.dataclass
class ZoneDemographics:
    """Per-zone covariates driving demand (deck p.5 'demographic destination
    sampling'; literature: young, high-income, time-pressed customers).

    Lists are indexed by zone id.  ``weight`` is the destination weight
    ``pop * (1 + 0.5 young_share) * income_factor`` (normalised); ``commercial``
    drives restaurant density.  A real-data implementation fills the same
    fields from ACS tables (population, 18-34 share, median income).
    """
    pop: List[float]
    young_share: List[float]
    income_factor: List[float]
    commercial: List[float]

    @property
    def n_zones(self) -> int:
        return len(self.pop)

    @property
    def weight(self) -> np.ndarray:
        w = np.array(self.pop) * (1.0 + 0.5 * np.array(self.young_share)) * np.array(self.income_factor)
        return w / w.sum()

    def to_dict(self) -> Dict[str, List[float]]:
        return {"pop": _py(self.pop), "young_share": _py(self.young_share),
                "income_factor": _py(self.income_factor), "commercial": _py(self.commercial),
                "weight": _py(self.weight.tolist())}


def synthetic_zone_demographics(n_zones: int, rng: np.random.Generator) -> ZoneDemographics:
    """Synthetic covariates per zone, fixed per seed (plan instance_generator_spec):
    ``pop ~ LogNormal(0, 0.5)``, ``young_share ~ U(0.15, 0.45)``,
    ``income_factor ~ U(0.8, 1.3)``, ``commercial ~ U(0.5, 2.0)``."""
    return ZoneDemographics(
        pop=[float(v) for v in rng.lognormal(0.0, 0.5, n_zones)],
        young_share=[float(v) for v in rng.uniform(0.15, 0.45, n_zones)],
        income_factor=[float(v) for v in rng.uniform(0.8, 1.3, n_zones)],
        commercial=[float(v) for v in rng.uniform(0.5, 2.0, n_zones)],
    )


# ---------------------------------------------------------------------------
# OD generator modules (deck p.5), swappable through small interfaces
# ---------------------------------------------------------------------------
class ReleaseTimeGenerator(ABC):
    """Interface: release times of orders inside the planning window.

    ``sample(rng, n)`` returns sorted minutes from the window start.  With
    ``n=None`` the count is random (Poisson); with an int exactly ``n`` times are
    drawn.  A data-driven implementation (e.g. a Kaggle-calibrated weekday /
    weekend profile) only has to implement this method and :meth:`rate`.
    """

    @abstractmethod
    def rate(self, hour: float) -> float:
        """Order intensity (orders per hour) at clock time ``hour`` (hours of day)."""

    @abstractmethod
    def sample(self, rng: np.random.Generator, n: Optional[int] = None) -> List[float]:
        """Sorted release minutes measured from the window start."""


class TimeDependentGenerator(ReleaseTimeGenerator):
    """Day-type x time-of-day intensity with inhomogeneous Poisson thinning.

    ``lambda(hour) = scale * profile(hour)`` where ``profile`` is one of
    :data:`HOURLY_PROFILES` (``'weekday'`` / ``'weekend'``) or any 24-list,
    interpolated piecewise linearly and periodically; ``scale`` is chosen so that
    the expected count in ``window_h = (start, end)`` equals ``target``.

    :meth:`sample` draws candidates from a homogeneous process of rate
    ``lambda_max`` and keeps each with probability ``lambda(t) / lambda_max``
    (thinning).  With ``n`` given, candidates are drawn until ``n`` are accepted:
    conditional on the count, inhomogeneous-Poisson points are i.i.d. with
    density proportional to ``lambda``, so this is the same law conditioned on
    ``N = n`` and gives instances of exactly the requested size.

    Round 2 (DECISIONS R2.2): ``profile`` may also be a block-profile config dict
    such as :data:`TIME_PROFILE_R2` (or the string ``'r2'``), evaluated with
    :func:`block_profile` for ``day_type`` (``'weekday'`` / ``'weekend'``), or any
    callable ``hour -> density``.  Because ``scale`` normalises the expected count
    to ``target``, only the *shape* of the profile inside the window matters here;
    the weekend volume factor is applied by :func:`make_synthetic_instance` when it
    derives ``n_orders``.
    """

    def __init__(self, profile: Any = "weekday", window_h: Tuple[float, float] = (17.5, 19.5),
                 target: float = 30.0, day_type: str = "weekday") -> None:
        self.day_type = str(day_type)
        self.profile: Optional[List[float]] = None
        self._density: Optional[Callable[[float], float]] = None
        if isinstance(profile, str) and profile == "r2":
            profile = TIME_PROFILE_R2
        if isinstance(profile, str):
            self.profile_name = profile
            prof = HOURLY_PROFILES[profile]
        elif isinstance(profile, dict):
            self.profile_name = f"{profile.get('name', 'block')}:{self.day_type}"
            self.profile_config = profile
            self._density = block_profile(profile, self.day_type)
            prof = None
        elif callable(profile):
            self.profile_name = getattr(profile, "__name__", "callable")
            self._density = profile
            prof = None
        else:
            self.profile_name = "custom"
            prof = list(profile)
        if prof is not None:
            if len(prof) != 24:
                raise ValueError("profile needs 24 hourly values")
            self.profile = [float(v) for v in prof]
        self.window_h = (float(window_h[0]), float(window_h[1]))
        if not self.window_h[1] > self.window_h[0]:
            raise ValueError("window end must exceed window start")
        self.target = float(target)
        # expected count with scale 1 (trapezoid on a fine grid of the window)
        grid = np.linspace(self.window_h[0], self.window_h[1], 721)
        vals = np.array([self._profile_at(h) for h in grid])
        integral = float(np.sum((vals[1:] + vals[:-1]) / 2.0 * np.diff(grid)))  # trapezoid rule
        self.scale = self.target / integral if integral > 0 else 0.0

    def _profile_at(self, hour: float) -> float:
        if self._density is not None:
            return float(self._density(hour))
        h = hour % 24.0
        i = int(math.floor(h))
        frac = h - i
        a, b = self.profile[i % 24], self.profile[(i + 1) % 24]
        return a + frac * (b - a)

    def rate(self, hour: float) -> float:
        """``lambda(hour)`` in orders per hour."""
        return self.scale * self._profile_at(hour)

    def expected_count(self) -> float:
        """Expected number of releases in the window (= ``target`` by construction)."""
        return self.target

    def sample(self, rng: np.random.Generator, n: Optional[int] = None) -> List[float]:
        start, end = self.window_h
        span_h = end - start
        lam_max = max(self.rate(start + k * span_h / 720.0) for k in range(721))
        if lam_max <= 0:
            return []
        out: List[float] = []
        if n is None:
            m = int(rng.poisson(lam_max * span_h))
            cand = np.sort(rng.uniform(0.0, span_h, m))
            keep = rng.uniform(0.0, 1.0, m)
            for c, u in zip(cand, keep):
                if u * lam_max <= self.rate(start + c):
                    out.append(float(c * 60.0))
            return out
        while len(out) < n:
            c = float(rng.uniform(0.0, span_h))
            if rng.uniform(0.0, 1.0) * lam_max <= self.rate(start + c):
                out.append(c * 60.0)
        return sorted(out)


class DestinationSampler(ABC):
    """Interface: customer (destination) node ``d_i`` of an order.

    ``sample(rng)`` returns a node of the instance node set ``V``; ``zone_of(node)``
    returns the zone used by the restaurant sampler's cuisine preference.  A
    real-data version samples an NTA by ACS weight and snaps a point in it to
    the nearest node of ``V``.
    """

    @abstractmethod
    def sample(self, rng: np.random.Generator) -> Node:
        """Customer node (already snapped to ``V``)."""

    @abstractmethod
    def zone_of(self, node: Node) -> int:
        """Zone id of a node."""


class DemographicDestinationSampler(DestinationSampler):
    """Zone by demographic weight, uniform node in the zone, snapped to the anchor
    lattice (deck p.5; plan: ``w_z ∝ pop_z (1 + 0.5 young_share_z) income_factor_z``).

    ``net`` provides ``zone_nodes`` and ``node_zone``; ``anchors`` is the customer
    lattice (subset of ``V``) that every sampled location is snapped to with
    :func:`snap_to_anchor` (Manhattan metric on grid indices, ties to the first
    anchor in list order).
    """

    def __init__(self, net: RoadNetwork, demo: ZoneDemographics, anchors: Sequence[Node]) -> None:
        self.net = net
        self.demo = demo
        self.anchors = [_node(a) for a in anchors]
        self.zone_ids = sorted(int(z) for z in net.zone_nodes.keys())
        self.weights = demo.weight

    def sample_zone(self, rng: np.random.Generator) -> int:
        return int(self.zone_ids[int(rng.choice(len(self.zone_ids), p=self.weights))])

    def sample(self, rng: np.random.Generator) -> Node:
        z = self.sample_zone(rng)
        pool = self.net.zone_nodes[z]
        raw = _node(pool[int(rng.integers(len(pool)))])
        return snap_to_anchor(raw, self.anchors)

    def zone_of(self, node: Node) -> int:
        return int(self.net.node_zone[node])


class RestaurantSampler(ABC):
    """Interface: restaurant node ``o_i`` and food-prep time (minutes) of an order.

    ``sample(rng, customer, zone)`` returns ``(restaurant_node, prep_min)``.  A
    DOHMH-based implementation keeps the same signature (restaurants with
    cuisine from the inspection dataset, prep-time distribution per cuisine).
    """

    @abstractmethod
    def sample(self, rng: np.random.Generator, customer: Node, zone: int) -> Tuple[Node, float]:
        """``(o_i, prep_minutes)`` for a customer at ``customer`` in ``zone``."""


class RestaurantTypeSampler(RestaurantSampler):
    """Cuisine ~ Categorical(zone preference), then a random restaurant among the
    ``nearest_k`` restaurants of that cuisine (Manhattan distance to the
    customer), then ``prep ~ U(mean_c - spread, mean_c + spread)`` minutes
    (deck p.5 'restaurant type sampling'; plan: pizza 10 / chinese 15 / fine
    dining 25 min mean; DECISIONS default range U(10, 25) is bracketed).

    ``restaurants`` is a list of ``(node, cuisine)``; ``cuisine_pref`` is a
    ``n_zones x n_cuisines`` row-stochastic array (synthetic: Dirichlet(2)).
    Falls back to all restaurants when a cuisine has no restaurant.
    """

    def __init__(self, restaurants: Sequence[Tuple[Node, str]], cuisines: Sequence[str],
                 cuisine_pref: np.ndarray, prep_mean_min: Dict[str, float],
                 prep_spread_min: float = 5.0, nearest_k: int = 3) -> None:
        self.restaurants = [(_node(n), str(c)) for n, c in restaurants]
        self.cuisines = [str(c) for c in cuisines]
        self.cuisine_pref = np.asarray(cuisine_pref, dtype=float)
        self.prep_mean_min = {str(k): float(v) for k, v in prep_mean_min.items()}
        self.prep_spread_min = float(prep_spread_min)
        self.nearest_k = max(1, int(nearest_k))
        self._by_cuisine: Dict[str, List[Node]] = {c: [] for c in self.cuisines}
        for n, c in self.restaurants:
            self._by_cuisine.setdefault(c, []).append(n)

    def sample_cuisine(self, rng: np.random.Generator, zone: int) -> str:
        p = self.cuisine_pref[zone]
        return self.cuisines[int(rng.choice(len(self.cuisines), p=p / p.sum()))]

    def sample(self, rng: np.random.Generator, customer: Node, zone: int) -> Tuple[Node, float]:
        cuisine = self.sample_cuisine(rng, zone)
        cands = self._by_cuisine.get(cuisine) or [n for n, _ in self.restaurants]
        cands = sorted(cands, key=lambda n: (_manhattan(n, customer), n))
        pick = cands[int(rng.integers(min(self.nearest_k, len(cands))))]
        mean = self.prep_mean_min.get(cuisine, 17.5)
        prep = float(rng.uniform(mean - self.prep_spread_min, mean + self.prep_spread_min))
        return pick, max(1.0, prep)


class KaggleRestaurantSampler(RestaurantSampler):
    """Kaggle-calibrated restaurant / prep-time sampler (DECISIONS R2.2, R2.4).

    * cuisine ~ Categorical(Kaggle order shares) restricted to the cuisines that
      have at least one restaurant (renormalised; ``effective_shares`` records the
      law actually sampled, and equals the Kaggle shares when every cuisine is
      represented);
    * restaurant: within the cuisine, candidates within ``radius_km`` of the
      customer (Manhattan metric on grid indices x ``block_m``), radius doubled
      until at least ``min_candidates`` (or all restaurants of the cuisine) are
      inside; drawn with weight ``rank ** -zipf_s`` where the popularity rank is a
      random permutation assigned **once per seed** within each cuisine
      (``rank_rng`` at construction; R2.2 'Zipf s = 1.0 within cuisine');
    * prep ~ DiscreteUniform{prep_min_range} minutes, independent of cuisine
      (Kaggle: chi2 p = 0.995 for U{20..35}).

    ``restaurants`` is a list of ``(node, cuisine)``.  :meth:`sample` keeps the
    :class:`RestaurantSampler` signature; :meth:`sample_detail` also returns the
    cuisine and the rank for the instance ``meta``.
    """

    def __init__(self, restaurants: Sequence[Tuple[Node, str]], cuisine_shares: Dict[str, float],
                 rank_rng: np.random.Generator, prep_min_range: Sequence[int] = (20, 35),
                 zipf_s: float = 1.0, radius_km: float = 2.5, min_candidates: int = 3,
                 block_m: float = 150.0) -> None:
        self.restaurants = [(_node(n), str(c)) for n, c in restaurants]
        self.prep_lo, self.prep_hi = int(prep_min_range[0]), int(prep_min_range[1])
        if self.prep_hi < self.prep_lo:
            raise ValueError("prep_min_range must be (lo, hi) with lo <= hi")
        self.zipf_s = float(zipf_s)
        self.radius_km = float(radius_km)
        self.min_candidates = max(1, int(min_candidates))
        self.block_m = float(block_m)
        self._by_cuisine: Dict[str, List[Node]] = {}
        for n, c in self.restaurants:
            self._by_cuisine.setdefault(c, []).append(n)
        # popularity ranks: one random permutation per cuisine, fixed at construction
        self.rank: Dict[Node, int] = {}
        for c in sorted(self._by_cuisine):
            nodes = self._by_cuisine[c]
            perm = rank_rng.permutation(len(nodes))
            for pos, idx in enumerate(perm):
                self.rank[nodes[int(idx)]] = pos + 1
        shares = {str(k): float(v) for k, v in cuisine_shares.items()}
        present = [c for c in shares if self._by_cuisine.get(c)]
        if not present:
            raise ValueError("no restaurant belongs to any cuisine of the share table")
        tot = sum(shares[c] for c in present)
        self.cuisines: List[str] = present
        self.cuisine_shares = shares
        self.effective_shares: Dict[str, float] = {c: shares[c] / tot for c in present}
        self._p = np.array([self.effective_shares[c] for c in present], dtype=float)
        self._dropped_share = 1.0 - tot / max(sum(shares.values()), 1e-12)

    def sample_cuisine(self, rng: np.random.Generator) -> str:
        return self.cuisines[int(rng.choice(len(self.cuisines), p=self._p))]

    def candidates(self, cuisine: str, customer: Node) -> List[Node]:
        """Restaurants of ``cuisine`` within the (expanding) radius of ``customer``."""
        pool = self._by_cuisine[cuisine]
        radius_blocks = self.radius_km * 1000.0 / self.block_m
        cands = [n for n in pool if _manhattan(n, customer) <= radius_blocks]
        while len(cands) < min(self.min_candidates, len(pool)):
            radius_blocks *= 2.0
            cands = [n for n in pool if _manhattan(n, customer) <= radius_blocks]
        return cands

    def sample_detail(self, rng: np.random.Generator, customer: Node, zone: int) -> Dict[str, Any]:
        """``{'node', 'prep_min', 'cuisine', 'rank', 'n_candidates'}`` for one order."""
        cuisine = self.sample_cuisine(rng)
        cands = self.candidates(cuisine, customer)
        w = np.array([self.rank[n] ** (-self.zipf_s) for n in cands], dtype=float)
        pick = cands[int(rng.choice(len(cands), p=w / w.sum()))]
        prep = int(rng.integers(self.prep_lo, self.prep_hi + 1))
        return {"node": pick, "prep_min": float(prep), "cuisine": cuisine,
                "rank": int(self.rank[pick]), "n_candidates": len(cands)}

    def sample(self, rng: np.random.Generator, customer: Node, zone: int) -> Tuple[Node, float]:
        d = self.sample_detail(rng, customer, zone)
        return d["node"], d["prep_min"]

    def to_meta(self) -> Dict[str, Any]:
        """JSON-safe record of the sampler's calibration for ``Instance.meta``."""
        return {
            "sampler": type(self).__name__,
            "prep_min_range": [self.prep_lo, self.prep_hi],
            "zipf_s": self.zipf_s, "radius_km": self.radius_km,
            "min_candidates": self.min_candidates,
            "cuisine_shares_kaggle": dict(self.cuisine_shares),
            "cuisine_shares_effective": dict(self.effective_shares),
            "cuisines_present": list(self.cuisines),
            "dropped_share": self._dropped_share,
            "restaurant_rank": [[list(n), int(r)] for n, r in sorted(self.rank.items())],
        }


def _manhattan(a: Node, b: Node) -> int:
    return int(abs(a[0] - b[0]) + abs(a[1] - b[1]))


# ---------------------------------------------------------------------------
# geometry helpers on the grid
# ---------------------------------------------------------------------------
def anchor_lattice(net: GridNetwork, spacing: int) -> List[Node]:
    """Customer anchor lattice: grid nodes ``(x, y)`` with ``x, y`` in
    ``range(spacing // 2, n, spacing)`` (every ``spacing`` blocks, e.g. 16 anchors
    on a 20 x 20 grid with spacing 5; snapping error <= ``spacing/2`` blocks per axis)."""
    off = spacing // 2
    return [(x, y) for x in range(off, net.nx_, spacing) for y in range(off, net.ny_, spacing)]


def snap_to_anchor(node: Node, anchors: Sequence[Node]) -> Node:
    """Nearest anchor in the Manhattan metric on grid indices (ties: first in list)."""
    best = anchors[0]
    best_d = _manhattan(node, best)
    for a in anchors[1:]:
        d = _manhattan(node, a)
        if d < best_d:
            best, best_d = a, d
    return best


def zone_centres(net: GridNetwork) -> List[Node]:
    """Node closest to the centroid of each zone (list indexed by zone id)."""
    out: List[Node] = []
    for z in range(net.n_zones):
        pts = net.zone_nodes[z]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        out.append(_node(min(pts, key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p))))
    return out


def apportion_counts(weights: Dict[str, float], n: int) -> Dict[str, int]:
    """Largest-remainder apportionment of ``n`` items to the keys of ``weights``
    (deterministic; ties broken by larger weight, then key order).  Used in
    round-2 mode to give the synthetic restaurants cuisines in proportion to the
    Kaggle order shares (R2.2) so that popular cuisines are represented first."""
    keys = list(weights)
    tot = float(sum(weights.values()))
    if n <= 0 or tot <= 0:
        return {k: 0 for k in keys}
    quotas = {k: n * float(weights[k]) / tot for k in keys}
    counts = {k: int(math.floor(quotas[k])) for k in keys}
    left = n - sum(counts.values())
    # remainders rounded to 9 decimals so that exact ties (e.g. 0.6 vs 0.6) are not decided
    # by floating-point noise but by the larger weight, then key order
    order = sorted(keys, key=lambda k: (-round(quotas[k] - counts[k], 9), -weights[k], keys.index(k)))
    for k in order[:left]:
        counts[k] += 1
    return counts


def place_restaurants(net: GridNetwork, n: int, rng: np.random.Generator,
                      commercial: Sequence[float], cuisines: Sequence[str],
                      cuisine_weights: Optional[Dict[str, float]] = None) -> List[Tuple[Node, str]]:
    """``n`` distinct restaurant nodes: zone ~ commercial score, node uniform in
    the zone (resampled on collision); cuisine assigned cyclically so every
    cuisine is represented when ``n >= len(cuisines)``.  With ``cuisine_weights``
    (round 2, R2.2) the cuisines are instead apportioned by
    :func:`apportion_counts` and assigned in decreasing share order."""
    if cuisine_weights is not None:
        counts = apportion_counts(cuisine_weights, int(n))
        labels: List[str] = []
        for c in sorted(cuisine_weights, key=lambda k: (-cuisine_weights[k], list(cuisine_weights).index(k))):
            labels.extend([str(c)] * counts[c])
        cuisines = labels
    w = np.asarray(commercial, dtype=float)
    w = w / w.sum()
    zones = sorted(int(z) for z in net.zone_nodes.keys())
    chosen: List[Node] = []
    seen = set()
    guard = 0
    while len(chosen) < n:
        guard += 1
        if guard > 100 * n + 100:
            raise ValueError("cannot place that many distinct restaurants")
        z = zones[int(rng.choice(len(zones), p=w))]
        pool = net.zone_nodes[z]
        node = _node(pool[int(rng.integers(len(pool)))])
        if node in seen:
            continue
        seen.add(node)
        chosen.append(node)
    return [(node, str(cuisines[i % len(cuisines)])) for i, node in enumerate(chosen)]


def _row_positions(n: int, nx_: int, y: int) -> List[Node]:
    """``n`` nodes evenly spaced along row ``y`` (fractions ``(i+1)/(n+1)``)."""
    return [(int(round((i + 1) * (nx_ - 1) / (n + 1))), int(y)) for i in range(n)]


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------
def route_physics(groute: GridRoute, physics: Dict[str, float]) -> Route:
    """Raw physical route values for E2 (1) from a ``GridNetwork`` route:
    ``T_h = length_m / speed_m_per_min / 60 (+ light_delay_s * n_lights / 3600)``,
    ``E_kwh = (wh_per_km * km + wh_per_m_climb * climb_m + wh_per_light * n_lights) / 1000``,
    ``d_km = length_m / 1000`` (config.py energy model; deck p.7)."""
    km = groute.length_m / 1000.0
    T_h = groute.length_m / physics["speed_m_per_min"] / 60.0 \
        + physics.get("light_delay_s", 0.0) * groute.n_lights / 3600.0
    E_wh = physics["wh_per_km"] * km + physics["wh_per_m_climb"] * groute.climb_m \
        + physics["wh_per_light"] * groute.n_lights
    return Route(T_h=float(T_h), E_kwh=float(E_wh / 1000.0), d_km=float(km))


def build_route_library(net: RoadNetwork, nodes: Sequence[Node],
                        physics: Dict[str, float]) -> Dict[Tuple[Node, Node], Route]:
    """One offered route per ordered pair of distinct nodes (E2 p.10: 'only the
    unique shortest road route between each pair is offered')."""
    routes: Dict[Tuple[Node, Node], Route] = {}
    for u in nodes:
        for v in nodes:
            if u != v:
                routes[(u, v)] = route_physics(net.route(u, v), physics)
    return routes


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------
def make_synthetic_instance(seed: int = 0, n_bikes: int = 10, n_orders: Optional[int] = None,
                            H: Optional[int] = None,
                            Delta_min: float = 5.0, L: int = 12, battery_wh: float = 600.0,
                            eta: float = 0.9, sub_grid: Tuple[int, int] = (20, 20),
                            n_restaurants: int = 6, n_depots: int = 2, anchor_spacing: int = 5,
                            zones_side: Optional[int] = None,
                            facilities_spec: Optional[Dict[str, Any]] = None,
                            services_spec: Optional[Dict[str, Any]] = None,
                            costs: Optional[Dict[str, Any]] = None,
                            demand_spec: Optional[Dict[str, Any]] = None,
                            physics: Optional[Dict[str, float]] = None,
                            pruning: Optional[Dict[str, Any]] = None,
                            od_modules: Optional[Dict[str, Any]] = None,
                            name: Optional[str] = None,
                            *,
                            window_h: Optional[float] = None,
                            window_start_hour: Optional[float] = None,
                            orders_per_bike_hour: Optional[float] = None,
                            init_frac: Optional[Tuple[float, float]] = None,
                            cost_variant: Optional[str] = None,
                            kaggle_calibrated: Optional[bool] = None,
                            time_profile: Optional[Union[str, Dict[str, Any], List[float]]] = None,
                            day_type: Optional[str] = None,
                            round2: Optional[bool] = None,
                            calibration_paths: Optional[Dict[str, str]] = None) -> Instance:
    """Build a synthetic E2 instance from a ``GridNetwork`` (module docstring for
    the pipeline; defaults per ``DECISIONS.md``, round-2 mode per R2.1 / R2.2).

    Parameters
    ----------
    seed, n_bikes, n_orders, H : reproducibility seed, |K|, |I|, horizon slots.
        ``n_orders=None`` -> 30 in legacy mode, derived from ``orders_per_bike_hour``
        in round-2 mode; ``H=None`` -> 24 in legacy mode, ``window_h * 60 /
        Delta_min`` when ``window_h`` is given (both given and inconsistent ->
        ``ValueError``).
    Delta_min, L, battery_wh, eta : ``Delta = Delta_min / 60`` h, full level ``L``,
        ``eps = battery_wh / L / 1000`` kWh, charging efficiency (19): default
        5 min, 12 levels of 50 Wh, ``p_ch = 0.667 kW``.
    sub_grid, anchor_spacing, zones_side : study area in blocks (150 m), customer
        lattice spacing, zones per side (default ``sub_grid[0] // anchor_spacing``,
        so zone centres coincide with anchors for the 20 x 20 / 5 default).
    n_restaurants, n_depots : |R| (denser in commercial zones), bike start nodes.
    facilities_spec, services_spec, costs, demand_spec, physics : partial dicts
        merged over :data:`DEFAULT_FACILITIES_SPEC` (:data:`DEFAULT_FACILITIES_SPEC_R2`
        in round-2 mode), :data:`DEFAULT_SERVICES_SPEC`, :data:`DEFAULT_COSTS`,
        :data:`DEFAULT_DEMAND_SPEC`, :data:`DEFAULT_PHYSICS`; explicit keys always
        win, also over a cost variant (R2.1: "existing calls that pass costs
        explicitly keep theirs").
    pruning : optional arc-builder options written into ``Instance.options``
        (``reposition_targets``, ``tau_max``, ``start_slack``, ...) so that ILP and
        baseline share them; see :func:`default_pruning`.
    od_modules : optional replacements ``{'release': ReleaseTimeGenerator,
        'destination': DestinationSampler, 'restaurant': RestaurantSampler}``.
    name : stored in ``meta['name']``.

    Round-2 keyword arguments (R2.2; ``None`` = the mode's default)
    ----------------------------------------------------------------
    window_h : window length in hours; giving it enters round-2 mode (``H =
        window_h * 12`` at 5 min; the cost coefficients F, F_hub, bB, bC are
        scaled by ``window_h / 4``, R2.1).
    window_start_hour : clock hour of boundary 0 (round 2: 17.0 = dinner
        17:00-21:00, 8 h sensitivity 14.0; legacy: 17.5).
    orders_per_bike_hour : demand knob (round 2: 1.5); ``n_orders = round(oph *
        n_bikes * H * Delta)`` times ``weekend_factor`` for ``day_type='weekend'``.
    init_frac : ``(lo, hi)`` with ``q0 ~ U{ceil(lo L) .. floor(hi L)}`` (round 2:
        ``(0.3, 0.6)`` -> 4..7 for L = 12; legacy ``(0.4, 1.0)``).
    cost_variant : :func:`ebike_swap_sim.costs.cost_variants` name (round 2:
        ``'usd_sunk'``; legacy ``None`` = toy :data:`DEFAULT_COSTS`).  Any value
        other than ``None`` is honoured in both modes and recorded in
        ``meta['cost_variant']`` / ``meta['costs']``.
    kaggle_calibrated : Kaggle order attributes (round 2: True): prep ~
        U{20..35} min -> ``a_i = r_i + ceil(prep / Delta)``, ``b_i = a_i +
        ceil(25 min / Delta)``, cuisine shares, Zipf ``s = 1`` popularity
        (:class:`KaggleRestaurantSampler`); False = synthetic cuisines and
        ``b_i = r_i + promise_slots``.
    time_profile : ``'r2'`` / :data:`TIME_PROFILE_R2`-like dict (round 2), or a
        key of :data:`HOURLY_PROFILES` / 24-list (legacy ``'weekday'``).
    day_type : ``'weekday'`` (default) or ``'weekend'`` (volume x1.15 with the
        block profile).
    round2 : force the mode (default ``window_h is not None``).
    calibration_paths : ``{'costs': path, 'kaggle': path}`` overriding the JSON
        locations.

    Returns a validated :class:`Instance` whose ``options['node_zone']`` holds the
    zone of every node (JSON list of ``[node, zone]``) and whose ``meta`` records
    every parameter plus the drawn geography (restaurants, depots, anchors,
    sites, hubs, zone demographics); in round-2 mode also ``meta['round2']``,
    ``meta['cost_variant']``, ``meta['costs']`` (every coefficient and the window),
    ``meta['time_profile']`` (config + ``status``), ``meta['kaggle_calibration']``
    and per-order ``cuisine`` / ``rank``.  Legacy calls produce byte-identical
    JSON to round 1.
    """
    # -- mode and round-2 defaults (R2.2) ------------------------------------
    if round2 is None:
        round2 = window_h is not None
    round2 = bool(round2)
    paths = dict(calibration_paths or {})
    if window_h is not None:
        H_from_window = int(round(float(window_h) * 60.0 / float(Delta_min)))
        if H is not None and int(H) != H_from_window:
            raise ValueError(f"H={H} inconsistent with window_h={window_h} h at Delta={Delta_min} min")
        H = H_from_window
    elif H is None:
        H = int(round(R2_DEFAULTS["window_h"] * 60.0 / float(Delta_min))) if round2 else 24
    H = int(H)
    window_hours = H * float(Delta_min) / 60.0
    if cost_variant is None and round2:
        cost_variant = R2_DEFAULTS["cost_variant"]
    if kaggle_calibrated is None:
        kaggle_calibrated = bool(round2 and R2_DEFAULTS["kaggle_calibrated"])
    if day_type is None:
        day_type = R2_DEFAULTS["day_type"]
    if day_type not in ("weekday", "weekend"):
        raise ValueError("day_type must be 'weekday' or 'weekend'")
    weekend_factor = 1.0
    if round2 and orders_per_bike_hour is None:
        orders_per_bike_hour = R2_DEFAULTS["orders_per_bike_hour"]
    if time_profile is None and round2:
        time_profile = R2_DEFAULTS["time_profile"]
    if isinstance(time_profile, str) and time_profile == "r2":
        time_profile = TIME_PROFILE_R2
    if isinstance(time_profile, dict) and day_type == "weekend":
        weekend_factor = float(time_profile.get("weekend_factor", 1.0))
    if n_orders is None:
        if orders_per_bike_hour is not None:
            n_orders = max(1, int(round(float(orders_per_bike_hour) * int(n_bikes) * window_hours
                                        * weekend_factor)))
        else:
            n_orders = 30
    n_orders = int(n_orders)

    fac_spec = _merge(DEFAULT_FACILITIES_SPEC_R2 if round2 else DEFAULT_FACILITIES_SPEC, facilities_spec)
    svc_spec = _merge(DEFAULT_SERVICES_SPEC, services_spec)
    cost = _merge(DEFAULT_COSTS, costs)
    dem = _merge(DEFAULT_DEMAND_SPEC, demand_spec)
    r2_dem: Dict[str, Any] = {}
    if round2:
        r2_dem["window_start_h"] = R2_DEFAULTS["window_start_hour"]
        r2_dem["init_frac"] = R2_DEFAULTS["init_frac"]
    if window_start_hour is not None:
        r2_dem["window_start_h"] = float(window_start_hour)
    if init_frac is not None:
        r2_dem["init_frac"] = (float(init_frac[0]), float(init_frac[1]))
    if time_profile is not None:
        r2_dem["profile"] = time_profile
    if r2_dem:
        # explicit demand_spec keys still win over the round-2 scalar defaults
        dem = _merge(_merge(dem, r2_dem), demand_spec)
    cal: Optional[Dict[str, Any]] = None
    if cost_variant is not None:
        cal = cost_mod.load_cost_calibration(paths.get("costs"), cost_variant, window_hours)
        c_over, d_over, s_over = cost_mod.apply_cost_calibration(cal, costs, demand_spec, services_spec)
        cost = _merge(cost, c_over)
        dem = _merge(dem, d_over)
        svc_spec = _merge(svc_spec, s_over)
    kag: Optional[Dict[str, Any]] = None
    if kaggle_calibrated:
        kag = load_kaggle_calibration(paths.get("kaggle"))
        kag_dem = {"promise_after_ready_min": kag["promise_after_ready_min"],
                   "prep_min_range": list(kag["prep_min_range"]),
                   "zipf_s": kag["zipf_s"],
                   "restaurant_radius_km": R2_DEFAULTS["restaurant_radius_km"],
                   "restaurant_min_candidates": R2_DEFAULTS["restaurant_min_candidates"]}
        dem = _merge(_merge(dem, kag_dem), demand_spec)
        if not (demand_spec or {}).get("cuisines"):
            # Kaggle cuisine list (values = Kaggle mean prep, informational: prep is
            # sampled cuisine-independently from prep_min_range)
            dem["cuisines"] = {c: float(kag["cuisine_mean_prep_min"].get(c, 27.5))
                               for c in kag["cuisine_shares"]}
    phys = _merge(DEFAULT_PHYSICS, physics)
    od_modules = od_modules or {}

    nx_, ny_ = int(sub_grid[0]), int(sub_grid[1])
    if zones_side is None:
        zones_side = max(1, nx_ // int(anchor_spacing))
    rng = np.random.default_rng(int(seed))
    disc = Discretisation(Delta_h=Delta_min / 60.0, H=int(H), L=int(L),
                          eps_kwh=battery_wh / L / 1000.0, eta=float(eta))

    # 1. network + zones --------------------------------------------------
    net = GridNetwork(nx_, ny_, float(phys["block_m"]), float(phys["traffic_light_prob"]),
                      int(zones_side), rng)
    demo = synthetic_zone_demographics(net.n_zones, rng)
    centres = zone_centres(net)
    anchors = anchor_lattice(net, int(anchor_spacing))
    cuisines = list(dem["cuisines"].keys())
    cuisine_pref: Optional[np.ndarray] = None
    if not kaggle_calibrated:
        cuisine_pref = rng.dirichlet(np.full(len(cuisines), 2.0), size=net.n_zones)

    # 2. nodes: restaurants, facilities, depots, anchors -------------------
    cuisine_weights = None
    if kaggle_calibrated:
        assert kag is not None
        cuisine_weights = {c: kag["cuisine_shares"].get(c, 0.0) for c in cuisines}
    restaurants = place_restaurants(net, int(n_restaurants), rng, demo.commercial, cuisines,
                                    cuisine_weights)
    rest_per_zone = [0] * net.n_zones
    for node, _ in restaurants:
        rest_per_zone[net.node_zone[node]] += 1
    busiest = sorted(range(net.n_zones), key=lambda z: (-rest_per_zone[z], z))
    n_sites = min(int(fac_spec["n_sites"]), net.n_zones)
    site_nodes = [centres[z] for z in busiest[:n_sites]]
    separated = fac_spec["mode"] == "separated"
    if fac_spec["mode"] not in ("colocated", "separated"):
        raise ValueError("facilities_spec['mode'] must be 'colocated' or 'separated'")
    hub_nodes = _row_positions(int(fac_spec["n_hubs"]), nx_, ny_ // 2) if separated else []
    depots = _row_positions(int(n_depots), nx_, ny_ // 4)
    nodes: List[Node] = []
    for v in [n for n, _ in restaurants] + site_nodes + hub_nodes + depots + anchors:
        if v not in nodes:
            nodes.append(v)
    routes = build_route_library(net, nodes, phys)

    # 3. orders -----------------------------------------------------------
    window_start = float(dem["window_start_h"])
    tail = int(dem["tail_slots"])
    release_slots = max(1, H - tail)
    release_span_h = release_slots * disc.Delta_h
    release_gen: ReleaseTimeGenerator = od_modules.get("release") or TimeDependentGenerator(
        dem["profile"], (window_start, window_start + release_span_h), float(n_orders),
        day_type=day_type)
    dest_sampler: DestinationSampler = od_modules.get("destination") or \
        DemographicDestinationSampler(net, demo, anchors)
    rest_sampler: RestaurantSampler
    if od_modules.get("restaurant") is not None:
        rest_sampler = od_modules["restaurant"]
    elif kaggle_calibrated:
        assert kag is not None
        rest_sampler = KaggleRestaurantSampler(
            restaurants, kag["cuisine_shares"], rng, dem["prep_min_range"], float(dem["zipf_s"]),
            float(dem["restaurant_radius_km"]), int(dem["restaurant_min_candidates"]),
            float(phys["block_m"]))
    else:
        rest_sampler = RestaurantTypeSampler(
            restaurants, cuisines, cuisine_pref, dem["cuisines"], float(dem["prep_spread_min"]),
            int(dem["nearest_k"]))
    # promise (R2.2 Kaggle: b_i = a_i + ceil(25 min / Delta); legacy: b_i = r_i + promise_slots)
    promise_after_ready = dem.get("promise_after_ready_min")
    promise_after_ready_slots = (int(math.ceil(float(promise_after_ready) / Delta_min - 1e-9))
                                 if promise_after_ready is not None else None)
    minutes = release_gen.sample(rng, int(n_orders) if dem["exact_count"] else None)
    plat_names = list(dem["platforms"].keys())
    plat_p = np.array([dem["platforms"][p] for p in plat_names], dtype=float)
    plat_p = plat_p / plat_p.sum()
    orders: List[Order] = []
    order_meta: List[Dict[str, Any]] = []
    for idx, minute in enumerate(minutes):
        r = min(int(math.floor(minute / Delta_min)), H - 1)
        d_node = dest_sampler.sample(rng)
        zone = dest_sampler.zone_of(d_node)
        detail: Optional[Dict[str, Any]] = None
        if hasattr(rest_sampler, "sample_detail"):
            detail = rest_sampler.sample_detail(rng, d_node, zone)  # type: ignore[attr-defined]
            o_node, prep = detail["node"], float(detail["prep_min"])
        else:
            o_node, prep = rest_sampler.sample(rng, d_node, zone)
        a = r + int(math.ceil(prep / Delta_min - 1e-9))
        if promise_after_ready_slots is not None:
            b = a + promise_after_ready_slots
        else:
            b = r + int(dem["promise_slots"])
        platform = str(plat_names[int(rng.choice(len(plat_names), p=plat_p))])
        orders.append(Order(id=idx + 1, o=o_node, d=d_node, r=r, a=a, b=b, hp=int(dem["hp"]),
                            hd=int(dem["hd"]), P=float(dem["P"]), w=float(dem["w"]),
                            v=float(dem["v"]), platform=platform))
        rec = {"id": idx + 1, "release_min": float(minute), "prep_min": float(prep),
               "zone": int(zone)}
        if detail is not None:
            rec["cuisine"] = str(detail["cuisine"])
            rec["rank"] = int(detail["rank"])
        order_meta.append(rec)

    # 4. facilities ---------------------------------------------------------
    fixed = bool(fac_spec["fixed"])
    hub = fac_spec["hub"]
    facilities: List[Facility] = []
    for i, node in enumerate(site_nodes):
        charge = not separated
        facilities.append(Facility(
            id=f"S{i + 1}", node=node, swap=True, charge=charge,
            y=1 if fixed else None,
            B=int(fac_spec["B"]) if fixed else None,
            C=(int(fac_spec["C"]) if charge else 0) if fixed else (None if charge else 0),
            K=int(fac_spec["K"]), Cbar=int(fac_spec["Cbar"]) if charge else 0,
            M=int(fac_spec["M"]), sigma=int(fac_spec["sigma"]),
            P_kw=float(fac_spec["P_kw"]) if charge else 0.0,
            group="sites" if charge else None,
            F=float(cost["F"]), bB=float(cost["bB"]), bC=float(cost["bC"]),
            R_end=int(fac_spec["R_end"]),
            Fhat=float(cost["Fhat"]), bhat=float(cost["bhat"]), chat=float(cost["chat"])))
    for h_idx, node in enumerate(hub_nodes):
        facilities.append(Facility(
            id=f"HUB{h_idx + 1}", node=node, swap=False, charge=True,
            y=1 if fixed else None,
            B=int(hub["B"]) if fixed else None,
            C=int(hub["C"]) if fixed else None,
            K=int(hub["K"]), Cbar=int(hub["Cbar"]), M=1, sigma=1,
            P_kw=float(hub["P_kw"]), group=f"hub{h_idx + 1}",
            F=float(cost["F_hub"]), bB=float(cost["bB"]), bC=float(cost["bC"]),
            R_end=int(hub["R_end"]),
            Fhat=float(cost["Fhat"]), bhat=float(cost["bhat"]), chat=float(cost["chat"])))

    def hour_of(t: int) -> float:
        return window_start + t * disc.Delta_h

    def in_peak(t: int) -> bool:
        lo, hi = fac_spec["peak_hours"]
        return lo <= hour_of(t) < hi

    # units review F8: the electricity price peak (TOU variant, Con Edison SC2 08-22 h per
    # notes/cost_calibration.md section 6 / JSON variants.tou_electricity) is a separate
    # window from the grid-limit peak (18-20 h).  ``facilities_spec['price_peak_hours']``
    # sets it; default = ``peak_hours`` (unchanged behaviour).  Not selectable through
    # ``cost_variant`` (R2.1 has pi_peak = None in all six variants): pass
    # ``costs={'pi': 0.132, 'pi_peak': 0.442}, facilities_spec={'price_peak_hours': (8, 22)}``.
    price_peak_hours = tuple(fac_spec.get("price_peak_hours") or fac_spec["peak_hours"])

    def in_price_peak(t: int) -> bool:
        lo, hi = price_peak_hours
        return lo <= hour_of(t) < hi

    P_grid: Dict[str, List[float]] = {}
    if not separated:
        P_grid["sites"] = [float(fac_spec["grid_sites_peak_kw"] if in_peak(t)
                                 else fac_spec["grid_sites_kw"]) for t in range(H)]
    for h_idx in range(len(hub_nodes)):
        P_grid[f"hub{h_idx + 1}"] = [float(hub["P_kw"])] * H

    # 5. services -------------------------------------------------------------
    services: List[Service] = []
    swap_ids = [f.id for f in facilities if f.swap]
    hub_ids = [f.id for f in facilities if not f.swap]
    fac_node = {f.id: f.node for f in facilities}

    def duration(a: Node, b: Node) -> int:
        route_min = net.route(a, b).length_m / phys["speed_m_per_min"]
        return max(1, int(math.ceil((route_min + svc_spec["handling_min"]) / Delta_min - 1e-9)))

    def add_services(pairs: List[Tuple[str, str]], every: int) -> None:
        for l in range(int(svc_spec["first"]), H, int(every)):
            for o_id, d_id in pairs:
                u = l + duration(fac_node[o_id], fac_node[d_id])
                if u <= H:
                    services.append(Service(id=len(services) + 1, o_fac=o_id, d_fac=d_id, l=l, u=u,
                                            U=int(svc_spec["U"]), f=float(svc_spec["f"]),
                                            vreb=float(svc_spec["vreb"])))

    if hub_ids:
        pairs = []
        for hid in hub_ids:
            for sid in swap_ids:
                pairs.append((hid, sid))
                pairs.append((sid, hid))
        add_services(pairs, int(svc_spec["every"]))
    if svc_spec["site_site"] and len(swap_ids) > 1:
        add_services([(a, b) for a in swap_ids for b in swap_ids if a != b],
                     int(svc_spec["site_site_every"]))

    # 6. bikes ------------------------------------------------------------------
    lo_frac, hi_frac = dem["init_frac"]
    q_lo = int(math.ceil(lo_frac * L - 1e-9))
    q_hi = int(math.floor(hi_frac * L + 1e-9))
    bikes = [Bike(id=k + 1, v0=depots[k % len(depots)], q0=int(rng.integers(q_lo, q_hi + 1)))
             for k in range(int(n_bikes))]

    # 7. prices, options, meta ----------------------------------------------------
    pi: Any = float(cost["pi"])
    if cost["pi_peak"] is not None:
        pi = {(f.id, t): float(cost["pi_peak"] if in_price_peak(t) else cost["pi"])
              for f in facilities if f.charge for t in range(H)}
    options: Dict[str, Any] = {"node_zone": [[list(v), int(net.node_zone[v])] for v in nodes]}
    if pruning:
        options.update(pruning)
    params: Dict[str, Any] = {
        "seed": seed, "n_bikes": n_bikes, "n_orders": n_orders, "H": H, "Delta_min": Delta_min,
        "L": L, "battery_wh": battery_wh, "eta": eta, "sub_grid": list(sub_grid),
        "n_restaurants": n_restaurants, "n_depots": n_depots, "anchor_spacing": anchor_spacing,
        "zones_side": zones_side, "facilities_spec": fac_spec, "services_spec": svc_spec,
        "costs": cost, "demand_spec": dem, "physics": phys, "pruning": pruning,
        "od_modules": {k: type(v).__name__ for k, v in od_modules.items()},
    }
    if round2 or cost_variant is not None or kaggle_calibrated:
        # round-2 parameters (R2.2); absent from legacy instances so that their JSON is unchanged
        params.update({
            "round2": round2, "window_h": window_hours, "window_start_hour": window_start,
            "orders_per_bike_hour": orders_per_bike_hour, "init_frac": list(dem["init_frac"]),
            "cost_variant": cost_variant, "kaggle_calibrated": bool(kaggle_calibrated),
            "day_type": day_type, "weekend_factor": weekend_factor,
            "calibration_paths": paths,
        })
    meta: Dict[str, Any] = {
        "name": name or f"synthetic seed={seed} K={n_bikes} I={n_orders} H={H} L={L}",
        "generator": "ebike_swap_sim.generator.make_synthetic_instance",
        "params": _py(params),
        "window_h": [window_start, window_start + H * disc.Delta_h],
        "release_window_h": [window_start, window_start + release_span_h],
        "restaurants": [[list(n), c] for n, c in restaurants],
        "cuisines": cuisines,
        "cuisine_pref": _py(cuisine_pref.tolist()) if cuisine_pref is not None else None,
        "zone_demographics": demo.to_dict(),
        "zone_centres": [list(c) for c in centres],
        "restaurants_per_zone": rest_per_zone,
        "anchors": [list(a) for a in anchors],
        "depots": [list(d) for d in depots],
        "sites": [list(s) for s in site_nodes],
        "hubs": [list(h) for h in hub_nodes],
        "orders": order_meta,
        "p_ch_kw": disc.p_ch_kw,
    }
    if round2:
        meta["round2"] = True
        meta["window_length_h"] = window_hours
        meta["day_type"] = day_type
    if cost["pi_peak"] is not None:
        meta["price_peak_hours"] = [float(price_peak_hours[0]), float(price_peak_hours[1])]
    if cal is not None:
        # R2.1: variant, window and every coefficient actually used (explicit overrides included)
        meta["cost_variant"] = cost_variant
        flat = cost_mod.flat_coefficients(cal)
        flat.update({k: cost[k] for k in ("kappa", "pi", "pi_peak", "F", "F_hub", "bB", "bC",
                                          "Fhat", "bhat", "chat")})
        flat.update({k: dem[k] for k in ("P", "w", "v")})
        flat.update({k: svc_spec[k] for k in ("f", "vreb")})
        flat["q_res"], flat["rho"] = cost["q_res"], cost["rho"]
        meta["costs"] = _py(flat)
    if isinstance(dem.get("profile"), dict):
        prof_cfg = dem["profile"]
        meta["time_profile"] = _py({
            **prof_cfg,
            "status": prof_cfg.get("status", "assumption"),
            "day_type": day_type,
            "weekday_integral": profile_integral(block_profile(prof_cfg, "weekday")),
            "sampler": type(release_gen).__name__,
        })
    if kag is not None:
        kmeta = {k: v for k, v in kag.items() if k != "cuisine_mean_prep_min"}
        kmeta["promise_after_ready_slots"] = promise_after_ready_slots
        if isinstance(rest_sampler, KaggleRestaurantSampler):
            kmeta.update(rest_sampler.to_meta())
        meta["kaggle_calibration"] = _py(kmeta)
    inst = Instance(disc=disc, nodes=nodes, routes=routes, bikes=bikes, orders=orders,
                    facilities=facilities, services=services, P_grid=P_grid,
                    kappa=float(cost["kappa"]), pi=pi, q_res=int(cost["q_res"]),
                    rho=float(cost["rho"]), options=options, meta=meta)
    inst.validate()
    return inst


# ---------------------------------------------------------------------------
# helpers for the other modules
# ---------------------------------------------------------------------------
def node_zone_map(inst: Instance) -> Dict[Node, int]:
    """Decode ``inst.options['node_zone']`` into ``{node: zone}`` (nodes as tuples)
    for the baseline's zone dispatch; empty if the instance has no zones."""
    recs = inst.options.get("node_zone") or []
    return {(_node(n) if isinstance(n, (list, tuple)) else n): int(z) for n, z in recs}


def default_pruning(inst: Instance, tau_max: int = 4, start_slack: int = 6,
                    reachable: bool = False) -> Dict[str, Any]:
    """Recommended arc-builder options (plan size_estimates 'ways to shrink' 1-3):
    reposition only to restaurants + facility nodes + depots, delivery starts
    within ``tau_max`` slots of the restaurant, start window ``t <= b_i + start_slack``.
    Targets are read from ``inst.meta`` (falls back to restaurant / facility / bike
    start nodes of the data)."""
    meta = inst.meta
    targets: List[Node] = []
    if meta.get("restaurants") or meta.get("depots"):
        for n, _ in meta.get("restaurants", []):
            targets.append(_node(n))
        for n in meta.get("depots", []):
            targets.append(_node(n))
    else:
        targets.extend(o.o for o in inst.orders)
        targets.extend(b.v0 for b in inst.bikes)
    targets.extend(f.node for f in inst.facilities)
    return {"reposition_targets": set(targets), "tau_max": int(tau_max),
            "start_slack": int(start_slack), "reachable_pruning": bool(reachable)}


def estimate_arcs(inst: Instance, pruning: Optional[Dict[str, Any]] = None,
                  sample_bikes: Optional[int] = None, strict: bool = False) -> Dict[str, Any]:
    """Size the ILP quickly by building the :class:`ArcLibrary` and reading its summary.

    ``pruning`` are builder option overrides (e.g. :func:`default_pruning`);
    ``sample_bikes = m`` builds only the first ``m`` bikes and extrapolates the
    totals (per-bike counts differ only under ``reachable_pruning``).  Returns
    ``arcs_per_bike`` (mean), ``per_kind_per_bike``, ``n_arcs`` (= binaries ``x``),
    ``binaries`` (``x`` + ``u_i`` + ``h_e`` + free ``y_j``), ``integers`` (``n_jqt``,
    ``c_jqt``, ``z_eq``, free ``B_j``/``C_j``), ``flow_rows`` (5), ``infeasible_bikes``
    (terminal pre-check (9)), ``extrapolated`` and the effective ``options``.
    """
    pruning = dict(pruning or {})
    sub = inst
    extrapolated = False
    if sample_bikes is not None and sample_bikes < len(inst.bikes):
        sub = dataclasses.replace(inst, bikes=inst.bikes[:max(1, int(sample_bikes))])
        extrapolated = True
    lib: ArcLibrary = build_arcs(sub, strict=strict, **pruning)
    summ = lib.summary()
    n_built = len(sub.bikes)
    n_bikes = len(inst.bikes)
    per_bike_mean = len(lib) / max(1, n_built)
    kinds = {kind: cnt / max(1, n_built) for kind, cnt in summ["per_kind"].items() if kind != "total"}
    flow_rows_built = sum(summ["n_states"].values())
    scale = n_bikes / max(1, n_built)
    H, L = inst.H, inst.L
    N, C, E, I = len(inst.facilities), len(inst.Cset), len(inst.services), len(inst.orders)
    free_y = sum(1 for f in inst.facilities if f.y is None)
    free_B = sum(1 for f in inst.facilities if f.B is None)
    free_C = sum(1 for f in inst.facilities if f.C is None and f.charge)
    n_arcs = int(round(len(lib) * scale))
    return {
        "n_bikes": n_bikes, "bikes_built": n_built, "extrapolated": extrapolated,
        "arcs_per_bike": per_bike_mean,
        "per_kind_per_bike": kinds,
        "n_arcs": n_arcs,
        "binaries": n_arcs + I + E + free_y,
        "integers": N * (L + 1) * (H + 1) + C * L * H + E * (L + 1) + free_B + free_C,
        "flow_rows": int(round(flow_rows_built * scale)),
        "infeasible_bikes": summ["infeasible_bikes"],
        "options": summ["options"],
        "instance": inst.summary(),
    }
