"""Semi-real NYC data layer for the E2 instance generator (DECISIONS.md R2.4).

Real inputs (``data/raw/``, see ``data/MANIFEST.md``): DOHMH restaurants with
cuisine (R2.4 restaurants), GeoDa NTA polygons with 2008-12 ACS counts (R2.4
zone-weight FALLBACK), the cyclist crash grid and the DOT bicycle counters
(loaders only, R2.4 last bullet).  Order attributes follow R2.2 (Kaggle
calibration: prep ~ DiscreteUniform{20..35} min, promise ``b_i = a_i + ceil(25
min / Delta)``, cuisine shares, Zipf ``s = 1.0`` popularity) and the cost
coefficients follow R2.1 (``cost_variant`` switch, USD values from
``notes/data/cost_calibration_usd.json``).

Geometry (R2.4): there is no real road network yet.  A *semi-real* instance puts
real restaurant / zone / site coordinates onto the synthetic
:class:`~ebike_swap_sim.network.GridNetwork`: local equirectangular metres
(1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N) rotated so that the
Manhattan avenue azimuth (29 deg east of north) becomes the grid ``y`` axis, then
snapped to 150 m blocks inside a :class:`StudyBox` (default Midtown / Chelsea /
Flatiron).  Elevation and signals stay synthetic.  :data:`GEOMETRY_CAVEAT` is
written into every instance ``meta`` and must be repeated in every output.

Zone weights are consumed through a small interface (:class:`ZoneWeights`
protocol or a plain ``zone_weight(lat, lon) -> float`` callable) so that the
literature formula on ACS 2020-24 tables (``acs_weights.py``, another module) can
plug in; :class:`GeoDaZoneWeights` is the fallback of R2.4 (``poptot x (1 + 2.4 x
youth16_19_share)`` with a loud warning).  Weights are *densities* (per km^2) so
that sampling grid nodes proportionally to the weight at the node reproduces the
zone-level law ``pi_z = w_z / sum w`` restricted to the part of each zone inside
the box.

The E2 mathematics (arcs.py, ilp.py, evaluate.py) is untouched: this module only
produces :class:`~ebike_swap_sim.or_instance.Instance` data.  Equation numbers
refer to ``notes/extracted/E2.txt``; ``R2.x`` to the Round 2 section of
``notes/DECISIONS.md``.  Pure python geometry (no shapely / geopandas).
"""
from __future__ import annotations

import dataclasses
import functools
import json
import math
import os
import warnings
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple, Union, runtime_checkable

import numpy as np
import pandas as pd

from .generator import (
    DEFAULT_COSTS,
    DEFAULT_DEMAND_SPEC,
    DEFAULT_FACILITIES_SPEC,
    DEFAULT_PHYSICS,
    DEFAULT_SERVICES_SPEC,
    DestinationSampler,
    RestaurantSampler,
    TimeDependentGenerator,
    block_profile,
    _merge,
    _node,
    _py,
    build_route_library,
)
from .network import GridNetwork
from .or_instance import Bike, Discretisation, Facility, Instance, Node, Order

__all__ = [
    "PROJECT_ROOT", "DATA_RAW", "DEFAULT_PATHS", "GEOMETRY_CAVEAT", "GEODA_FALLBACK_WARNING",
    "M_PER_DEG_LAT", "M_PER_DEG_LON", "GRID_AZIMUTH_DEG", "DEFAULT_BOX",
    "StudyBox", "point_in_ring", "point_in_polygon", "point_in_geometry", "polygon_area_km2",
    "ZoneWeights", "GeoDaZoneWeights", "as_zone_weight_fn",
    "KAGGLE_CLASSES", "CUISINE_MAP", "DOHMH_BBOX", "load_dohmh", "restaurants_in_box",
    "load_kaggle_calibration", "NYCRestaurantSampler", "NYCDestinationSampler",
    "load_crash_grid", "crash_risk_by_node",
    "load_counter_profile", "counter_hourly_profile", "ASSUMED_TIME_PROFILE",
    "assumed_hourly_profile", "period_shares", "compare_counter_profile",
    "COST_VARIANTS", "cost_variant_params", "NYC_FACILITIES_SPEC", "NYC_DEMAND_SPEC",
    "busiest_restaurant_cells", "make_nyc_instance",
]

# ---------------------------------------------------------------------------
# paths and constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
NOTES_DATA = os.path.join(PROJECT_ROOT, "notes", "data")

#: Default real-data files (``data/MANIFEST.md``).
DEFAULT_PATHS: Dict[str, str] = {
    "dohmh": os.path.join(DATA_RAW, "dohmh_restaurants.csv"),
    "nta_geojson": os.path.join(DATA_RAW, "nycnhood_acs.geojson"),
    "crash_grid": os.path.join(DATA_RAW, "cyclist_crash_grid_0005deg.csv"),
    "counter_profile": os.path.join(DATA_RAW, "bike_counter_hourly_profile.csv"),
    "kaggle": os.path.join(NOTES_DATA, "kaggle_calibration.json"),
    "costs_usd": os.path.join(NOTES_DATA, "cost_calibration_usd.json"),
}

#: R2.4 geometry caveat, written into ``meta['geometry_caveat']`` of every instance.
GEOMETRY_CAVEAT = (
    "Semi-real NYC instance: real DOHMH restaurants, real NTA zone weights and real "
    "candidate-site coordinates are projected onto the synthetic 150 m GridNetwork "
    "(local equirectangular metres, 1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N, "
    "rotated by -29 deg to the Manhattan street-grid azimuth and snapped to 150 m blocks "
    "inside the study box); no real road network is used, and elevation and traffic "
    "signals remain synthetic."
)

#: R2.4 fallback warning (GeoDa 2008-12 counts instead of the ACS 2020-24 literature formula).
GEODA_FALLBACK_WARNING = (
    "ZONE WEIGHTS FALLBACK (R2.4): ACS 2020-24 literature weights not used; zone weight = "
    "GeoDa 2008-12 NTA N_z x (1 + 2.4 x youth16_19_share) with N_z = popover18 (adults, the "
    "literature N_z; poptot when popover18 is missing) and youth16_19_share = (male16to19 + "
    "femal16_19) / poptot, using only poptot, popover18, male16to19, femal16_19 (medianinco / "
    "medianage / popdty are corrupt sums and are never read)."
)

M_PER_DEG_LAT = 111_000.0      # R2.4: 1 deg lat = 111.0 km
M_PER_DEG_LON = 84_300.0       # R2.4: 1 deg lon = 84.3 km at 40.7 N
GRID_AZIMUTH_DEG = 29.0        # Manhattan avenues: 29 deg east of true north

#: DOHMH loader bbox of ``data/MANIFEST.md`` section 1 (lat_min, lat_max, lon_min, lon_max).
DOHMH_BBOX = (40.4, 41.0, -74.3, -73.6)


# ---------------------------------------------------------------------------
# 1. geometry: study box, projection, grid, snapping
# ---------------------------------------------------------------------------
@dataclasses.dataclass
class StudyBox:
    """Study area in WGS84 with the R2.4 local projection onto a 150 m grid.

    ``project(lat, lon) -> (x, y)`` metres: equirectangular east / north offsets from
    the box's south-west corner (:data:`M_PER_DEG_LAT`, :data:`M_PER_DEG_LON`) rotated
    so that the avenue azimuth ``azimuth_deg`` (29 deg east of north) becomes the
    ``+y`` axis (the frame is rotated by ``-29 deg``, i.e. the coordinates by
    ``+29 deg`` counter-clockwise), then shifted so that the rotated box has
    ``min x = min y = 0``.  ``inverse`` undoes it exactly.  ``grid_nx x grid_ny``
    nodes of ``block_m`` cover the rotated bounding box of the four corners; a
    node ``(ix, iy)`` sits at ``(ix block_m, iy block_m)`` (same convention as
    :class:`~ebike_swap_sim.network.GridNetwork`).  Default box: Midtown /
    Chelsea / Flatiron, lat 40.735-40.770, lon -74.005 to -73.965 (R2.4).
    """
    lat_min: float = 40.735
    lat_max: float = 40.770
    lon_min: float = -74.005
    lon_max: float = -73.965
    block_m: float = 150.0
    azimuth_deg: float = GRID_AZIMUTH_DEG

    def __post_init__(self) -> None:
        if not (self.lat_max > self.lat_min and self.lon_max > self.lon_min and self.block_m > 0):
            raise ValueError("StudyBox needs lat_max > lat_min, lon_max > lon_min, block_m > 0")
        a = math.radians(self.azimuth_deg)
        self._cos, self._sin = math.cos(a), math.sin(a)
        corners = [(self.lat_min, self.lon_min), (self.lat_min, self.lon_max),
                   (self.lat_max, self.lon_min), (self.lat_max, self.lon_max)]
        self._x0 = self._y0 = 0.0
        pts = [self._rotate(*self._east_north(lat, lon)) for lat, lon in corners]
        self._x0 = min(p[0] for p in pts)
        self._y0 = min(p[1] for p in pts)
        self.width_m = max(p[0] for p in pts) - self._x0
        self.height_m = max(p[1] for p in pts) - self._y0
        self.grid_nx = int(math.ceil(self.width_m / self.block_m - 1e-9)) + 1
        self.grid_ny = int(math.ceil(self.height_m / self.block_m - 1e-9)) + 1

    # -- projection -------------------------------------------------------
    def _east_north(self, lat: float, lon: float) -> Tuple[float, float]:
        return (lon - self.lon_min) * M_PER_DEG_LON, (lat - self.lat_min) * M_PER_DEG_LAT

    def _rotate(self, e: float, n: float) -> Tuple[float, float]:
        # coordinates rotated +azimuth CCW: an avenue vector (sin a, cos a) maps to (0, 1)
        return e * self._cos - n * self._sin, e * self._sin + n * self._cos

    def project(self, lat: float, lon: float) -> Tuple[float, float]:
        """WGS84 -> rotated local metres ``(x, y)`` (R2.4 geometry)."""
        x, y = self._rotate(*self._east_north(lat, lon))
        return x - self._x0, y - self._y0

    def inverse(self, x: float, y: float) -> Tuple[float, float]:
        """Rotated local metres -> ``(lat, lon)``; exact inverse of :meth:`project`."""
        x, y = x + self._x0, y + self._y0
        e = x * self._cos + y * self._sin
        n = -x * self._sin + y * self._cos
        return self.lat_min + n / M_PER_DEG_LAT, self.lon_min + e / M_PER_DEG_LON

    def contains(self, lat: float, lon: float) -> bool:
        """True iff the WGS84 point lies inside the (unrotated) box."""
        return self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max

    # -- grid ---------------------------------------------------------------
    def snap(self, lat: float, lon: float) -> Node:
        """Nearest grid node ``(ix, iy)`` of the 150 m grid (clamped to the grid)."""
        x, y = self.project(lat, lon)
        ix = min(max(int(round(x / self.block_m)), 0), self.grid_nx - 1)
        iy = min(max(int(round(y / self.block_m)), 0), self.grid_ny - 1)
        return (ix, iy)

    def node_xy(self, node: Node) -> Tuple[float, float]:
        """Local metres of a grid node."""
        return float(node[0]) * self.block_m, float(node[1]) * self.block_m

    def node_latlon(self, node: Node) -> Tuple[float, float]:
        """WGS84 position of a grid node."""
        return self.inverse(*self.node_xy(node))

    def grid_nodes(self) -> List[Node]:
        """All grid nodes ``(ix, iy)`` in ``GridNetwork`` order (x-major)."""
        return [(ix, iy) for ix in range(self.grid_nx) for iy in range(self.grid_ny)]

    def make_grid(self, rng: np.random.Generator, light_prob: float = DEFAULT_PHYSICS["traffic_light_prob"],
                  n_zones_side: int = 1) -> GridNetwork:
        """``GridNetwork`` covering the box (``grid_nx x grid_ny`` blocks of
        ``block_m``); elevation and signals are drawn from ``rng`` (synthetic, R2.4)."""
        return GridNetwork(self.grid_nx, self.grid_ny, float(self.block_m), float(light_prob),
                           int(n_zones_side), rng)

    def to_dict(self) -> Dict[str, Any]:
        return {"lat_min": self.lat_min, "lat_max": self.lat_max, "lon_min": self.lon_min,
                "lon_max": self.lon_max, "block_m": self.block_m, "azimuth_deg": self.azimuth_deg,
                "grid_nx": self.grid_nx, "grid_ny": self.grid_ny,
                "width_m": self.width_m, "height_m": self.height_m}


DEFAULT_BOX = StudyBox()


# ---------------------------------------------------------------------------
# pure-python polygon geometry (R2.4 last bullet: ray casting, no shapely)
# ---------------------------------------------------------------------------
def point_in_ring(lon: float, lat: float, ring: Sequence[Sequence[float]]) -> bool:
    """Even-odd ray casting of ``(lon, lat)`` against one GeoJSON ring (R2.4)."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_cross = xj + (lat - yj) * (xi - xj) / (yi - yj)
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygon(lon: float, lat: float, rings: Sequence[Sequence[Sequence[float]]]) -> bool:
    """Point in a GeoJSON Polygon (outer ring minus holes, even-odd rule)."""
    inside = False
    for ring in rings:
        if point_in_ring(lon, lat, ring):
            inside = not inside
    return inside


def point_in_geometry(lon: float, lat: float, geometry: Dict[str, Any]) -> bool:
    """Point in a GeoJSON ``Polygon`` or ``MultiPolygon`` geometry."""
    gtype = geometry["type"]
    if gtype == "Polygon":
        return point_in_polygon(lon, lat, geometry["coordinates"])
    if gtype == "MultiPolygon":
        return any(point_in_polygon(lon, lat, poly) for poly in geometry["coordinates"])
    raise ValueError(f"unsupported geometry type {gtype!r}")


def _ring_area_m2(ring: Sequence[Sequence[float]]) -> float:
    """Shoelace area of a lon/lat ring in equirectangular square metres."""
    s = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0] * M_PER_DEG_LON, ring[i][1] * M_PER_DEG_LAT
        x2, y2 = ring[(i + 1) % n][0] * M_PER_DEG_LON, ring[(i + 1) % n][1] * M_PER_DEG_LAT
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def polygon_area_km2(geometry: Dict[str, Any]) -> float:
    """Area (km^2) of a GeoJSON Polygon / MultiPolygon: outer rings minus holes,
    equirectangular metres (:data:`M_PER_DEG_LAT`, :data:`M_PER_DEG_LON`)."""
    polys = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    total = 0.0
    for rings in polys:
        if rings:
            total += _ring_area_m2(rings[0]) - sum(_ring_area_m2(r) for r in rings[1:])
    return total / 1e6


def _geometry_bbox(geometry: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """``(lon_min, lat_min, lon_max, lat_max)`` of a Polygon / MultiPolygon."""
    polys = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    lons = [p[0] for rings in polys for ring in rings for p in ring]
    lats = [p[1] for rings in polys for ring in rings for p in ring]
    return min(lons), min(lats), max(lons), max(lats)


# ---------------------------------------------------------------------------
# 3a. zone weights interface + GeoDa fallback (R2.4)
# ---------------------------------------------------------------------------
@runtime_checkable
class ZoneWeights(Protocol):
    """Interface for destination zone weights (R2.4 "Zone weights").

    ``weight_at(lat, lon)`` returns the demand weight *density* at a point (relative
    expected orders per km^2; 0 outside every zone) and ``zones()`` the list of zone
    ids (NTA codes) the object knows.  Implementations may add ``zone_at(lat, lon)
    -> Optional[str]`` (used for zone labels when present).  ``acs_weights.py``
    (literature formula on ACS 2020-24) implements this; :class:`GeoDaZoneWeights`
    is the fallback.  A plain ``zone_weight(lat, lon) -> float`` callable is
    accepted wherever a ``ZoneWeights`` is (see :func:`as_zone_weight_fn`).
    """

    def weight_at(self, lat: float, lon: float) -> float: ...

    def zones(self) -> List[str]: ...


def as_zone_weight_fn(zw: Union["ZoneWeights", Callable[[float, float], float]]) -> Callable[[float, float], float]:
    """Return the ``zone_weight(lat, lon) -> float`` callable of a :class:`ZoneWeights`
    object (its ``weight_at``) or pass a plain callable through (R2.4 interface)."""
    if hasattr(zw, "weight_at"):
        return zw.weight_at  # type: ignore[union-attr]
    if callable(zw):
        return zw
    raise TypeError("zone weights must implement weight_at(lat, lon) or be a callable")


#: The only GeoDa attributes the fallback is allowed to read (R2.4).
GEODA_FIELDS = ("poptot", "popover18", "male16to19", "femal16_19")


class GeoDaZoneWeights:
    """R2.4 FALLBACK zone weights from the GeoDa NTA GeoJSON (ACS 2008-12 counts).

    Per NTA ``z``: ``w_z = poptot_z x (1 + youth_coef x youth16_19_share_z)`` with
    ``youth16_19_share = (male16to19 + femal16_19) / poptot`` (``youth_coef = 2.4``,
    the age-rate ratio of the literature formula collapsed onto the only age proxy
    the file offers) and ``weight_at`` = ``w_z / area_z`` in km^-2 (0 outside every
    polygon, zero-population park / cemetery NTAs are naturally ~0).  Reads only
    :data:`GEODA_FIELDS`; ``medianinco`` / ``medianage`` / ``popdty`` are never
    touched (corrupt tract sums, MANIFEST section 2).  ``box`` restricts the
    polygon search to NTAs whose bounding box intersects it (speed only).
    A :data:`GEODA_FALLBACK_WARNING` is issued on construction and exposed as
    ``.warning`` for the instance meta.
    """

    source = "geoda_fallback"

    def __init__(self, path: Optional[str] = None, youth_coef: float = 2.4,
                 box: Optional[StudyBox] = None, warn: bool = True) -> None:
        self.path = path or DEFAULT_PATHS["nta_geojson"]
        self.youth_coef = float(youth_coef)
        self.warning = GEODA_FALLBACK_WARNING
        with open(self.path, "r", encoding="utf-8") as fh:
            gj = json.load(fh)
        self._features: List[Dict[str, Any]] = []
        for feat in gj["features"]:
            props = feat["properties"]
            geom = feat["geometry"]
            if geom is None:
                continue
            bbox = _geometry_bbox(geom)
            if box is not None and (bbox[2] < box.lon_min or bbox[0] > box.lon_max
                                    or bbox[3] < box.lat_min or bbox[1] > box.lat_max):
                continue
            poptot = float(props.get("poptot") or 0.0)
            popover18 = float(props.get("popover18") or 0.0)
            youth = float(props.get("male16to19") or 0.0) + float(props.get("femal16_19") or 0.0)
            share = youth / poptot if poptot > 0 else 0.0
            # R2.4 fallback formula N_z x (1 + 2.4 x youth16_19_share) with N_z the adult (18+)
            # population as in the literature model (units review F6); poptot only when the
            # GeoDa row has no popover18 value.
            n_z = popover18 if popover18 > 0 else poptot
            w_total = n_z * (1.0 + self.youth_coef * share)
            area = polygon_area_km2(geom)
            self._features.append({
                "code": str(props["ntacode"]), "name": str(props.get("ntaname", "")),
                "boro": str(props.get("boroname", "")), "geometry": geom, "bbox": bbox,
                "poptot": poptot, "popover18": popover18, "N_z": n_z,
                "youth16_19": youth, "youth16_19_share": share, "w_total": w_total,
                "area_km2": area, "density": (w_total / area) if area > 0 else 0.0,
            })
        self._features.sort(key=lambda f: f["code"])
        self._by_code = {f["code"]: f for f in self._features}
        if warn:
            warnings.warn(self.warning, UserWarning, stacklevel=2)

    def _find(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        for f in self._features:
            b = f["bbox"]
            if b[0] <= lon <= b[2] and b[1] <= lat <= b[3] and point_in_geometry(lon, lat, f["geometry"]):
                return f
        return None

    def zone_at(self, lat: float, lon: float) -> Optional[str]:
        """NTA code containing the point (pure-python ray casting), or ``None``."""
        f = self._find(lat, lon)
        return f["code"] if f else None

    def weight_at(self, lat: float, lon: float) -> float:
        """Weight density (km^-2) of the NTA containing the point; 0 outside every NTA."""
        f = self._find(lat, lon)
        return float(f["density"]) if f else 0.0

    def zones(self) -> List[str]:
        """Sorted NTA codes known to this object (those intersecting ``box`` if given)."""
        return [f["code"] for f in self._features]

    def zone_total(self, code: str) -> float:
        """Whole-NTA weight ``w_z`` (not per area)."""
        return float(self._by_code[code]["w_total"])

    def info(self, code: str) -> Dict[str, Any]:
        """Attributes used for one NTA (no geometry)."""
        f = self._by_code[code]
        return {k: v for k, v in f.items() if k not in ("geometry", "bbox")}

    def table(self) -> pd.DataFrame:
        """One row per NTA with the fields that enter the weight."""
        return pd.DataFrame([self.info(c) for c in self.zones()])


# ---------------------------------------------------------------------------
# 2. restaurants: DOHMH loader, cuisine mapping, sampler (R2.4 / R2.2)
# ---------------------------------------------------------------------------
#: The 14 Kaggle cuisine classes (``kaggle_calibration.json`` ``cuisine_shares``).
KAGGLE_CLASSES: Tuple[str, ...] = (
    "American", "Japanese", "Italian", "Chinese", "Mexican", "Indian", "Middle Eastern",
    "Mediterranean", "Thai", "French", "Southern", "Korean", "Spanish", "Vietnamese",
)

#: R2.4 declared mapping of the 90 DOHMH ``cuisine_description`` values to the 14
#: Kaggle classes + ``'other'``.  Rules: national cuisines to their class; Pizza ->
#: Italian; Tex-Mex / Southwestern -> Mexican; Barbecue / Soul Food / Cajun / Creole
#: -> Southern; Greek / Moroccan -> Mediterranean; Afghan / Armenian / Egyptian /
#: Iranian / Lebanese / Turkish -> Middle Eastern; Bangladeshi / Pakistani -> Indian;
#: Basque / Tapas -> Spanish; Chinese/x fusion -> Chinese; Haute Cuisine / New
#: French -> French; Southeast Asian -> Vietnamese (DOHMH has no Vietnamese value);
#: American-style counters (Hamburgers, Chicken, Hotdogs, Sandwiches, Salads,
#: Steakhouse, Seafood, Bagels, Pancakes, Irish pubs, New American, Californian)
#: -> American; cafes, bakeries, desserts, juice, beverages, grocery-like and
#: cuisines with no Kaggle class -> 'other' (never sampled: Kaggle share 0).
#:
#: Declared assumption (units review F3): the ``'other'`` class is unreachable by
#: construction and holds 32.5 % of the usable DOHMH rows citywide and 26.1 % of the
#: rows in the default study box (Coffee/Tea 460, Bakery 113, 'Other' 111, Donuts 76,
#: Juice 71, Asian/Asian Fusion 70, Frozen Desserts 46, Latin American 40 of 4,607), i.e.
#: the cafe / bakery / dessert delivery segment is excluded.  Debatable entries kept as
#: declared: 'Chicken' (fast-food, Korean and Peruvian chicken) -> American, 'Southeast
#: Asian' (Vietnamese, Malaysian and Thai-style rows) -> Vietnamese, 'Hawaiian' (poke)
#: -> other, 'Asian/Asian Fusion', 'Latin American', 'Caribbean' -> other.
#: ``make_nyc_instance`` records the unreachable share in ``meta`` and accepts
#: ``cuisine_map_overrides`` (e.g. :data:`CUISINE_MAP_CAFES_AS_AMERICAN`) for sensitivity runs.
CUISINE_MAP: Dict[str, str] = {
    "Afghan": "Middle Eastern",
    "African": "other",
    "American": "American",
    "Armenian": "Middle Eastern",
    "Asian/Asian Fusion": "other",
    "Australian": "other",
    "Bagels/Pretzels": "American",
    "Bakery Products/Desserts": "other",
    "Bangladeshi": "Indian",
    "Barbecue": "Southern",
    "Basque": "Spanish",
    "Bottled Beverages": "other",
    "Brazilian": "other",
    "Cajun": "Southern",
    "Californian": "American",
    "Caribbean": "other",
    "Chicken": "American",
    "Chilean": "other",
    "Chimichurri": "other",
    "Chinese": "Chinese",
    "Chinese/Cuban": "Chinese",
    "Chinese/Japanese": "Chinese",
    "Coffee/Tea": "other",
    "Continental": "other",
    "Creole": "Southern",
    "Creole/Cajun": "Southern",
    "Czech": "other",
    "Donuts": "other",
    "Eastern European": "other",
    "Egyptian": "Middle Eastern",
    "English": "other",
    "Ethiopian": "other",
    "Filipino": "other",
    "French": "French",
    "Frozen Desserts": "other",
    "Fruits/Vegetables": "other",
    "Fusion": "other",
    "German": "other",
    "Greek": "Mediterranean",
    "Hamburgers": "American",
    "Haute Cuisine": "French",
    "Hawaiian": "other",
    "Hotdogs": "American",
    "Hotdogs/Pretzels": "American",
    "Indian": "Indian",
    "Indonesian": "other",
    "Iranian": "Middle Eastern",
    "Irish": "American",
    "Italian": "Italian",
    "Japanese": "Japanese",
    "Jewish/Kosher": "other",
    "Juice, Smoothies, Fruit Salads": "other",
    "Korean": "Korean",
    "Latin American": "other",
    "Lebanese": "Middle Eastern",
    "Mediterranean": "Mediterranean",
    "Mexican": "Mexican",
    "Middle Eastern": "Middle Eastern",
    "Moroccan": "Mediterranean",
    "New American": "American",
    "New French": "French",
    "Not Listed/Not Applicable": "other",
    "Nuts/Confectionary": "other",
    "Other": "other",
    "Pakistani": "Indian",
    "Pancakes/Waffles": "American",
    "Peruvian": "other",
    "Pizza": "Italian",
    "Polish": "other",
    "Polynesian": "other",
    "Portuguese": "other",
    "Russian": "other",
    "Salads": "American",
    "Sandwiches": "American",
    "Sandwiches/Salads/Mixed Buffet": "American",
    "Scandinavian": "other",
    "Seafood": "American",
    "Soul Food": "Southern",
    "Soups": "other",
    "Soups/Salads/Sandwiches": "American",
    "Southeast Asian": "Vietnamese",
    "Southwestern": "Mexican",
    "Spanish": "Spanish",
    "Steakhouse": "American",
    "Tapas": "Spanish",
    "Tex-Mex": "Mexican",
    "Thai": "Thai",
    "Turkish": "Middle Eastern",
    "Vegan": "other",
    "Vegetarian": "other",
}
assert len(CUISINE_MAP) == 90
assert set(CUISINE_MAP.values()) <= set(KAGGLE_CLASSES) | {"other"}

#: Sensitivity mapping (units review F3): cafes / bakeries / desserts / juice counters are
#: treated as American-style delivery supply instead of being unreachable.  Pass as
#: ``make_nyc_instance(cuisine_map_overrides=CUISINE_MAP_CAFES_AS_AMERICAN)``.
CUISINE_MAP_CAFES_AS_AMERICAN: Dict[str, str] = {
    "Coffee/Tea": "American", "Bakery Products/Desserts": "American", "Donuts": "American",
    "Juice, Smoothies, Fruit Salads": "American", "Frozen Desserts": "American",
    "Bottled Beverages": "American", "Nuts/Confectionary": "American",
}
#: Sensitivity mapping (units review F3): the national / regional classes that the declared
#: map sends to ``'other'`` although a Kaggle class is arguably close.
CUISINE_MAP_REGIONAL_TO_KAGGLE: Dict[str, str] = {
    "Asian/Asian Fusion": "Japanese", "Latin American": "Spanish", "Caribbean": "Spanish",
    "Hawaiian": "Japanese", "Peruvian": "Spanish", "Brazilian": "Spanish",
}


@functools.lru_cache(maxsize=4)
def _load_dohmh_cached(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"camis": str, "r_zip": str, "r_cb": str, "r_tract": str},
                     low_memory=False)
    df["r_lat"] = pd.to_numeric(df["r_lat"], errors="coerce")
    df["r_lon"] = pd.to_numeric(df["r_lon"], errors="coerce")
    lat_min, lat_max, lon_min, lon_max = DOHMH_BBOX
    keep = (df["r_lat"].between(lat_min, lat_max) & df["r_lon"].between(lon_min, lon_max)
            & df["r_cuisine"].notna() & (df["r_cuisine"].astype(str).str.strip() != "")
            & df["r_last_insp"].notna() & (df["r_last_insp"].astype(str).str.strip() != ""))
    out = df.loc[keep].copy()
    out = out.rename(columns={"r_dba": "dba", "r_boro": "boro", "r_lat": "lat", "r_lon": "lon",
                              "r_cuisine": "cuisine", "r_nta": "nta", "r_zip": "zip"})
    out["cuisine"] = out["cuisine"].astype(str).str.strip()
    out["kaggle_class"] = out["cuisine"].map(lambda c: CUISINE_MAP.get(c, "other"))
    out = out.sort_values("camis", kind="mergesort").reset_index(drop=True)
    return out[["camis", "dba", "boro", "zip", "lat", "lon", "cuisine", "kaggle_class", "nta",
                "r_last_insp", "n_rows"]]


def load_dohmh(path: Optional[str] = None) -> pd.DataFrame:
    """Deduplicated DOHMH restaurant table with the MANIFEST section 1 filters (R2.4):
    lat/lon inside :data:`DOHMH_BBOX`, ``cuisine_description`` present, inspection
    date present (27,030 usable rows).  Adds ``kaggle_class`` via :data:`CUISINE_MAP`
    (unmapped -> ``'other'``).  Sorted by ``camis``; cached per path, a copy is returned."""
    return _load_dohmh_cached(path or DEFAULT_PATHS["dohmh"]).copy()


def restaurants_in_box(box: StudyBox = DEFAULT_BOX, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Usable DOHMH restaurants inside ``box`` with local coordinates ``x, y`` (m) and
    the snapped grid ``node`` (R2.4 geometry).  Deterministic order (by ``camis``)."""
    if df is None:
        df = load_dohmh()
    sel = df[(df["lat"] >= box.lat_min) & (df["lat"] <= box.lat_max)
             & (df["lon"] >= box.lon_min) & (df["lon"] <= box.lon_max)].copy()
    xy = [box.project(float(a), float(b)) for a, b in zip(sel["lat"], sel["lon"])]
    sel["x"] = [p[0] for p in xy]
    sel["y"] = [p[1] for p in xy]
    sel["node"] = [box.snap(float(a), float(b)) for a, b in zip(sel["lat"], sel["lon"])]
    return sel.reset_index(drop=True)


def load_kaggle_calibration(source: Union[None, str, Dict[str, Any]] = None) -> Dict[str, Any]:
    """``notes/data/kaggle_calibration.json`` (or an already loaded dict) (R2.2)."""
    if isinstance(source, dict):
        return source
    with open(source or DEFAULT_PATHS["kaggle"], "r", encoding="utf-8") as fh:
        return json.load(fh)


class NYCRestaurantSampler(RestaurantSampler):
    """R2.4 restaurant choice + R2.2 prep time on the real DOHMH table.

    1. cuisine class ~ Kaggle order shares renormalised over the classes present
       in ``box`` (``'other'`` has no Kaggle share and is never drawn);
    2. candidates = restaurants of that class within ``radius_m`` (2.5 km) of the
       customer (Euclidean in projected metres); the radius grows by
       ``radius_growth`` (x1.5) until at least ``min_candidates`` (3) are found
       (or all restaurants of the class are candidates);
    3. restaurant ~ weight ``rank ** -zipf_s`` (``s = 1.0``), where the popularity
       rank is a random permutation within the class drawn once from ``rng`` at
       construction (fixed per seed, R2.4 "rank assigned once per seed");
    4. prep ~ DiscreteUniform{20..35} min (R2.2, Kaggle ``food_preparation_time``).

    ``sample(rng, customer, zone)`` keeps the generator interface and returns
    ``(restaurant_node, prep_min)``; :meth:`sample_record` returns the full record
    (camis, class, radius used, distance) for the instance meta.
    """

    def __init__(self, box: StudyBox, rng: np.random.Generator,
                 kaggle_json: Union[None, str, Dict[str, Any]] = None,
                 restaurants: Optional[pd.DataFrame] = None, radius_m: float = 2500.0,
                 radius_growth: float = 1.5, min_candidates: int = 3, zipf_s: float = 1.0,
                 prep_range_min: Tuple[int, int] = (20, 35)) -> None:
        self.box = box
        self.rng = rng
        self.kaggle = load_kaggle_calibration(kaggle_json)
        self.df = restaurants_in_box(box) if restaurants is None else restaurants.reset_index(drop=True)
        self.radius_m = float(radius_m)
        self.radius_growth = float(radius_growth)
        self.min_candidates = int(min_candidates)
        self.zipf_s = float(zipf_s)
        self.prep_range_min = (int(prep_range_min[0]), int(prep_range_min[1]))
        shares = self.kaggle["cuisine_shares"]
        present = set(self.df["kaggle_class"])
        self.cuisines: List[str] = [c for c in shares if c in present]
        if not self.cuisines:
            raise ValueError("no Kaggle cuisine class has a restaurant in the box")
        tot = sum(float(shares[c]) for c in self.cuisines)
        self.cuisine_p = np.array([float(shares[c]) / tot for c in self.cuisines])
        self.dropped_classes = sorted(set(shares) - present)
        # per-class arrays and the once-per-seed Zipf ranks
        self._cls: Dict[str, Dict[str, Any]] = {}
        self.rank = np.zeros(len(self.df), dtype=int)
        for c in self.cuisines:
            idx = np.flatnonzero(self.df["kaggle_class"].to_numpy() == c)
            perm = rng.permutation(len(idx))
            ranks = np.empty(len(idx), dtype=int)
            ranks[perm] = np.arange(1, len(idx) + 1)
            self.rank[idx] = ranks
            self._cls[c] = {
                "idx": idx,
                "xy": self.df[["x", "y"]].to_numpy(dtype=float)[idx],
                "rank": ranks,
                "weight": ranks.astype(float) ** (-self.zipf_s),
            }
        self.df = self.df.assign(rank=self.rank)

    @property
    def n_restaurants(self) -> int:
        return int(len(self.df))

    def cuisine_shares(self) -> Dict[str, float]:
        """Renormalised Kaggle shares actually used."""
        return {c: float(p) for c, p in zip(self.cuisines, self.cuisine_p)}

    def sample_cuisine(self, rng: Optional[np.random.Generator] = None) -> str:
        rng = rng if rng is not None else self.rng
        return self.cuisines[int(rng.choice(len(self.cuisines), p=self.cuisine_p))]

    def candidates(self, cuisine: str, customer: Node) -> Tuple[np.ndarray, float]:
        """``(positions into self.df, radius_used_m)`` of the candidate set (step 2)."""
        cls = self._cls[cuisine]
        cx, cy = self.box.node_xy(customer)
        dist = np.hypot(cls["xy"][:, 0] - cx, cls["xy"][:, 1] - cy)
        r = self.radius_m
        n_all = len(cls["idx"])
        mask = dist <= r
        while mask.sum() < min(self.min_candidates, n_all):
            r *= self.radius_growth
            mask = dist <= r
        return np.flatnonzero(mask), r

    def sample_record(self, rng: Optional[np.random.Generator], customer: Node) -> Dict[str, Any]:
        """Full draw: cuisine, restaurant row, radius used, distance, prep (steps 1-4)."""
        rng = rng if rng is not None else self.rng
        cuisine = self.sample_cuisine(rng)
        cls = self._cls[cuisine]
        local, radius = self.candidates(cuisine, customer)
        w = cls["weight"][local]
        pick_local = int(local[int(rng.choice(len(local), p=w / w.sum()))])
        row_i = int(cls["idx"][pick_local])
        row = self.df.iloc[row_i]
        cx, cy = self.box.node_xy(customer)
        dist = float(math.hypot(float(row["x"]) - cx, float(row["y"]) - cy))
        lo, hi = self.prep_range_min
        prep = float(rng.integers(lo, hi + 1))
        return {"camis": str(row["camis"]), "dba": str(row["dba"]), "cuisine_dohmh": str(row["cuisine"]),
                "cuisine": cuisine, "rank": int(cls["rank"][pick_local]), "node": _node(row["node"]),
                "lat": float(row["lat"]), "lon": float(row["lon"]), "radius_m": float(radius),
                "dist_m": dist, "n_candidates": int(len(local)), "prep_min": prep}

    def sample(self, rng: np.random.Generator, customer: Node, zone: int) -> Tuple[Node, float]:
        """Generator interface: ``(o_i node, prep_min)``; ``zone`` is ignored (cuisine
        preference is the city-wide Kaggle share, R2.2)."""
        rec = self.sample_record(rng, customer)
        self.last_record = rec
        return rec["node"], rec["prep_min"]


# ---------------------------------------------------------------------------
# 3b. customers: destination sampler on zone weights (R2.4)
# ---------------------------------------------------------------------------
class NYCDestinationSampler(DestinationSampler):
    """Customer node ~ zone weight at the node (R2.4 "Zone weights").

    Every grid node of ``box`` gets ``w(node) = zone_weight(lat, lon)`` (a density,
    see :class:`ZoneWeights`); nodes outside the box or outside every zone get 0
    (park NTAs are naturally ~0).  ``sample(rng)`` draws a node with probability
    ``w / sum w``.  ``zone_of(node)`` is the integer index of the node's zone in
    :meth:`zone_ids` (``-1`` if none), used for ``options['node_zone']``.
    ``zone_weights`` may be a :class:`ZoneWeights` object or a bare callable.
    """

    def __init__(self, box: StudyBox, zone_weights: Union[ZoneWeights, Callable[[float, float], float]],
                 rng: Optional[np.random.Generator] = None) -> None:
        self.box = box
        self.zw = zone_weights
        self.rng = rng
        fn = as_zone_weight_fn(zone_weights)
        zone_at = getattr(zone_weights, "zone_at", None)
        self.nodes: List[Node] = box.grid_nodes()
        self.node_latlon: Dict[Node, Tuple[float, float]] = {}
        self.node_weight: Dict[Node, float] = {}
        self.node_zone_code: Dict[Node, Optional[str]] = {}
        for v in self.nodes:
            lat, lon = box.node_latlon(v)
            self.node_latlon[v] = (lat, lon)
            inside = box.contains(lat, lon)
            w = float(fn(lat, lon)) if inside else 0.0
            self.node_weight[v] = max(0.0, w)
            self.node_zone_code[v] = (zone_at(lat, lon) if (zone_at is not None and inside) else None)
        codes = sorted({c for c in self.node_zone_code.values() if c is not None})
        self._zone_ids: List[str] = codes
        self._zone_index = {c: i for i, c in enumerate(codes)}
        self._pool = [v for v in self.nodes if self.node_weight[v] > 0]
        if not self._pool:
            raise ValueError("no grid node inside the box has positive zone weight")
        w = np.array([self.node_weight[v] for v in self._pool], dtype=float)
        self._p = w / w.sum()

    def zone_ids(self) -> List[str]:
        """Zone codes (NTAs) that contain at least one grid node of the box."""
        return list(self._zone_ids)

    @property
    def support(self) -> List[Node]:
        """Grid nodes with positive sampling weight (the sampler's support)."""
        return list(self._pool)

    def zone_totals(self) -> Dict[str, float]:
        """Share of the sampling mass per zone code (nodes with no zone under ``None``)."""
        out: Dict[Any, float] = {}
        for v, p in zip(self._pool, self._p):
            out[self.node_zone_code[v]] = out.get(self.node_zone_code[v], 0.0) + float(p)
        return out

    def sample(self, rng: Optional[np.random.Generator] = None) -> Node:
        rng = rng if rng is not None else self.rng
        return self._pool[int(rng.choice(len(self._pool), p=self._p))]

    def zone_of(self, node: Node) -> int:
        code = self.node_zone_code.get(_node(node))
        return self._zone_index.get(code, -1) if code is not None else -1


# ---------------------------------------------------------------------------
# 4. loaders: crash grid, counter profile, assumed profile comparison
# ---------------------------------------------------------------------------
def load_crash_grid(path: Optional[str] = None) -> Dict[Tuple[float, float], Dict[str, int]]:
    """Cyclist crash grid (MANIFEST section 3): ``{(lat_cell, lon_cell): {cyc_crashes,
    cyc_inj, cyc_killed}}``; cell key = SW corner ``floor(x * 200) / 200`` rounded to
    3 decimals.  Risk layer only (R2.4: not in the objective this round)."""
    df = pd.read_csv(path or DEFAULT_PATHS["crash_grid"])
    out: Dict[Tuple[float, float], Dict[str, int]] = {}
    for rec in df.itertuples(index=False):
        key = (round(float(rec.lat_cell), 3), round(float(rec.lon_cell), 3))
        out[key] = {"cyc_crashes": int(rec.cyc_crashes), "cyc_inj": int(rec.cyc_inj),
                    "cyc_killed": int(rec.cyc_killed)}
    return out


def crash_risk_by_node(box: StudyBox = DEFAULT_BOX, grid: Optional[Dict[Tuple[float, float], Dict[str, int]]] = None,
                       field: str = "cyc_crashes", nodes: Optional[Sequence[Node]] = None) -> Dict[Node, float]:
    """Crash count of the 0.005 deg cell containing each grid node (the nearest cell
    centre); cells absent from the table had no cyclist-injury crash -> 0."""
    grid = load_crash_grid() if grid is None else grid
    out: Dict[Node, float] = {}
    for v in (nodes if nodes is not None else box.grid_nodes()):
        lat, lon = box.node_latlon(v)
        key = (round(math.floor(lat * 200) / 200, 3), round(math.floor(lon * 200) / 200, 3))
        out[_node(v)] = float(grid.get(key, {}).get(field, 0))
    return out


def load_counter_profile(path: Optional[str] = None) -> pd.DataFrame:
    """DOT bicycle counter hourly profile (MANIFEST section 4): one row per
    ``(id, daytype, hour)`` with ``share_of_day``."""
    return pd.read_csv(path or DEFAULT_PATHS["counter_profile"], dtype={"id": str})


def counter_hourly_profile(path: Optional[str] = None, exclude: Sequence[str] = ("Staten Island Ferry",),
                           df: Optional[pd.DataFrame] = None) -> Dict[str, List[float]]:
    """Mean ``share_of_day`` per clock hour across the avenue counters (equal weight
    per counter id), excluding names in ``exclude`` ('Staten Island Ferry' is not an
    avenue counter).  ``{'weekday': [24 shares], 'weekend': [24 shares]}``, each
    renormalised to sum 1 (R2.4 profile cross-check)."""
    df = load_counter_profile(path) if df is None else df
    df = df[~df["name"].isin(list(exclude))]
    out: Dict[str, List[float]] = {}
    for daytype, sub in df.groupby("daytype"):
        mean = sub.groupby("hour")["share_of_day"].mean().reindex(range(24), fill_value=0.0)
        vals = mean.to_numpy(dtype=float)
        s = vals.sum()
        out[str(daytype)] = [float(v / s) if s > 0 else 0.0 for v in vals]
    return out


#: R2.2 time-of-day profile: a DECLARED ASSUMPTION (no paper supports a profile,
#: ``notes/literature_demand_model.md`` Sec. 6).  Shares of the daily order count by
#: period; ``'rest'`` is the complement.  Weekend volume x1.15.
ASSUMED_TIME_PROFILE: Dict[str, Any] = {
    "flag": "assumption",
    "source": "DECISIONS.md R2.2 / literature_demand_model.md Sec. 6 (placeholder until the "
              "NYC DCWP 2022 hourly trip distribution is digitised)",
    "periods": {
        "lunch": {"start_h": 11.5, "end_h": 14.0, "share": 0.28},
        "dinner": {"start_h": 17.5, "end_h": 21.5, "share": 0.45},
        "late": {"start_h": 21.5, "end_h": 25.0, "share": 0.12},
        "rest": {"share": 0.15},
    },
    "weekend_volume_factor": 1.15,
}


def assumed_block_config(profile: Dict[str, Any] = ASSUMED_TIME_PROFILE) -> Dict[str, Any]:
    """The R2.2 assumed profile in the block layout of
    :data:`ebike_swap_sim.generator.TIME_PROFILE_R2` (``blocks`` / ``rest_share`` /
    ``weekend_factor``), i.e. the **step function** that
    :class:`~ebike_swap_sim.generator.TimeDependentGenerator` evaluates through
    :func:`~ebike_swap_sim.generator.block_profile`.  This is what
    :func:`make_nyc_instance` passes to the release-time generator, so the semi-real
    family realises the same within-window shape as the synthetic round-2 family
    (units review F1)."""
    blocks = [{"name": name, "start_h": float(p["start_h"]), "end_h": float(p["end_h"]),
               "share": float(p["share"])}
              for name, p in profile["periods"].items() if name != "rest"]
    return {
        "name": "assumed_r2_2", "status": profile.get("flag", "assumption"),
        "source": profile.get("source", ""), "blocks": blocks,
        "rest_share": float(profile["periods"]["rest"]["share"]),
        "weekend_factor": float(profile.get("weekend_volume_factor", 1.0)),
    }


def assumed_hourly_profile(profile: Dict[str, Any] = ASSUMED_TIME_PROFILE) -> List[float]:
    """24 hourly shares (hour ``h`` covers ``[h, h+1)``, i.e. **integrated** over the
    hour, not the density at the top of the hour) of the R2.2 assumed profile:
    uniform density inside each period, ``'rest'`` spread uniformly over the
    remaining hours.  Sums to 1.  Meant for period aggregation
    (:func:`period_shares`, :func:`compare_counter_profile`); do **not** hand it to
    :class:`~ebike_swap_sim.generator.TimeDependentGenerator` as a 24-list, which
    interprets list entries as hour-top intensities and interpolates linearly
    between them (the 17:30 step would become a ramp over 17:00-18:00; units
    review F1) -- use :func:`assumed_block_config` for sampling."""
    hours = np.zeros(24)
    covered = np.zeros(24)
    for name, p in profile["periods"].items():
        if name == "rest":
            continue
        s, e = float(p["start_h"]), float(p["end_h"])
        dens = float(p["share"]) / (e - s)
        for h in range(24):
            for shift in (0.0, 24.0):   # periods may wrap past midnight
                lo, hi = max(h + shift, s), min(h + 1 + shift, e)
                if hi > lo:
                    hours[h] += dens * (hi - lo)
                    covered[h] += hi - lo
    rest_hours = np.clip(1.0 - covered, 0.0, 1.0)
    if rest_hours.sum() > 0:
        hours += float(profile["periods"]["rest"]["share"]) * rest_hours / rest_hours.sum()
    return [float(v) for v in hours]


def period_shares(hourly: Sequence[float], profile: Dict[str, Any] = ASSUMED_TIME_PROFILE) -> Dict[str, float]:
    """Aggregate 24 hourly shares into the R2.2 periods (fractional hours pro rata)."""
    hourly = np.asarray(hourly, dtype=float)
    out: Dict[str, float] = {}
    used = 0.0
    for name, p in profile["periods"].items():
        if name == "rest":
            continue
        s, e = float(p["start_h"]), float(p["end_h"])
        tot = 0.0
        for h in range(24):
            for shift in (0.0, 24.0):
                lo, hi = max(h + shift, s), min(h + 1 + shift, e)
                if hi > lo:
                    tot += hourly[h] * (hi - lo)
        out[name] = float(tot)
        used += tot
    out["rest"] = float(hourly.sum() - used)
    return out


def compare_counter_profile(counter: Optional[Dict[str, List[float]]] = None,
                            profile: Dict[str, Any] = ASSUMED_TIME_PROFILE) -> pd.DataFrame:
    """Small table comparing the R2.2 assumed period shares with the bicycle-counter
    profile (weekday / weekend): columns ``period, assumed, counter_weekday,
    counter_weekend, ratio_weekday, ratio_weekend`` (R2.4 cross-check only; counters
    measure all cycling, not deliveries)."""
    counter = counter_hourly_profile() if counter is None else counter
    assumed = period_shares(assumed_hourly_profile(profile), profile)
    wk = period_shares(counter.get("weekday", [0.0] * 24), profile)
    we = period_shares(counter.get("weekend", [0.0] * 24), profile)
    rows = []
    for name in assumed:
        rows.append({"period": name, "assumed": assumed[name], "counter_weekday": wk[name],
                     "counter_weekend": we[name],
                     "ratio_weekday": wk[name] / assumed[name] if assumed[name] > 0 else float("nan"),
                     "ratio_weekend": we[name] / assumed[name] if assumed[name] > 0 else float("nan")})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5. cost variants (R2.1) and the semi-real instance builder (R2.2 / R2.4)
# ---------------------------------------------------------------------------
COST_VARIANTS: Tuple[str, ...] = ("toy", "usd_A", "usd_sunk", "usd_B", "usd_low", "usd_high")

#: R2.2 co-located site defaults (generator spec overridden: B = 3, C = 2; K 8, M 1,
#: sigma 1, P 4 kW, grid 8 kW / 6 kW 18-20 h kept from the generator defaults).
NYC_FACILITIES_SPEC: Dict[str, Any] = _merge(DEFAULT_FACILITIES_SPEC, {"B": 3, "C": 2})

#: R2.2 demand defaults: window 17:00-21:00, q0 ~ U{ceil(0.3 L)..floor(0.6 L)},
#: prep ~ DU{20..35} min, promise ``b_i = a_i + ceil(25 min / Delta)``.
NYC_DEMAND_SPEC: Dict[str, Any] = _merge(DEFAULT_DEMAND_SPEC, {
    "window_start_h": 17.0, "init_frac": (0.3, 0.6), "prep_range_min": (20, 35),
    "promise_after_ready_min": 25.0, "profile": "assumed_r2_2",
})


def cost_variant_params(variant: str = "usd_sunk", window_h: float = 4.0,
                        path: Optional[str] = None) -> Dict[str, Any]:
    """Cost coefficients of one R2.1 ``cost_variant`` as generator-style dicts.

    Thin wrapper around :func:`ebike_swap_sim.costs.load_cost_calibration` (the single
    implementation of the R2.1 variants ``toy``, ``usd_A``, ``usd_sunk`` (default),
    ``usd_B``, ``usd_low``, ``usd_high``; ``F, F_hub, bB, bC`` scaled by
    ``window_h / 4`` for the USD variants, toy unscaled).  Returns ``{'variant',
    'costs', 'demand_spec', 'services_spec', 'window_h', 'description'}`` where
    ``costs`` has the keys of ``generator.DEFAULT_COSTS`` (incl. ``q_res``, ``rho``
    from the defaults), ``demand_spec`` the order prices ``P, w, v`` ((30)-(31)) and
    ``services_spec`` ``f, vreb`` (32).  Unknown variants raise ``ValueError``
    (``costs.py`` raises ``KeyError``)."""
    from .costs import load_cost_calibration
    if variant not in COST_VARIANTS:
        raise ValueError(f"unknown cost_variant {variant!r}; known: {COST_VARIANTS}")
    try:
        cal = load_cost_calibration(path, variant=variant, window_h=float(window_h))
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
    costs = dict(DEFAULT_COSTS)
    costs.update(cal["costs"])
    costs = {k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in ("q_res",) else v)
             for k, v in costs.items()}
    costs["q_res"] = int(DEFAULT_COSTS["q_res"])
    costs["rho"] = float(DEFAULT_COSTS["rho"])
    demand = {k: float(cal["demand_spec"][k]) for k in ("P", "w", "v")}
    services = {k: float(cal["services_spec"][k]) for k in ("f", "vreb")}
    desc = f"{cal.get('source', 'costs.load_cost_calibration')} variant {variant} (window scale {cal.get('window_scale', 1.0)})"
    return {"variant": variant, "costs": costs, "demand_spec": demand, "services_spec": services,
            "window_h": float(window_h), "window_scale": float(cal.get("window_scale", 1.0)),
            "source": cal.get("source"), "description": desc}


def busiest_restaurant_cells(restaurants: pd.DataFrame, n: int, min_sep_blocks: int = 4) -> List[Node]:
    """``n`` grid nodes with the most DOHMH restaurants snapped to them, chosen
    greedily with a Manhattan separation of at least ``min_sep_blocks`` blocks between
    sites (ties by node order); used for the co-located facility sites (R2.4
    "real candidate-site coordinates")."""
    counts: Dict[Node, int] = {}
    for v in restaurants["node"]:
        counts[_node(v)] = counts.get(_node(v), 0) + 1
    ranked = sorted(counts, key=lambda v: (-counts[v], v))
    chosen: List[Node] = []
    for v in ranked:
        if all(abs(v[0] - c[0]) + abs(v[1] - c[1]) >= min_sep_blocks for c in chosen):
            chosen.append(v)
        if len(chosen) >= n:
            break
    if len(chosen) < n:   # relax the separation if the box is too small
        for v in ranked:
            if v not in chosen:
                chosen.append(v)
            if len(chosen) >= n:
                break
    return chosen


def default_zone_weights(box: Optional[StudyBox] = None, paths: Optional[Dict[str, str]] = None) -> ZoneWeights:
    """Zone-weight object used by :func:`make_nyc_instance` when none is given (R2.4):
    ``acs_weights.ACSZoneWeights(box=box, fallback='auto')`` -- the literature formula
    on the ACS 2020-24 NTA tables when they are present under ``data/raw/acs/``,
    otherwise its GeoDa 2008-12 fallback with the loud warning.  If even the GeoDa
    file is missing the plain :class:`GeoDaZoneWeights` constructor is called so the
    original ``FileNotFoundError`` surfaces.  Imported lazily (``acs_weights``
    imports this module)."""
    paths = dict(DEFAULT_PATHS, **(paths or {}))
    try:
        from .acs_weights import ACSZoneWeights
        return ACSZoneWeights(box=box, fallback="auto", warn=True)
    except (FileNotFoundError, KeyError, ValueError, RuntimeError, ImportError):
        return GeoDaZoneWeights(paths["nta_geojson"], box=box, warn=True)


def make_nyc_instance(seed: int = 0, n_bikes: int = 10, window_h: float = 4.0,
                      orders_per_bike_hour: float = 1.5, cost_variant: str = "usd_sunk",
                      box: Optional[StudyBox] = None, n_sites: int = 3,
                      site_latlon: Optional[Sequence[Tuple[float, float]]] = None,
                      site_min_sep_blocks: int = 4, Delta_min: float = 5.0, L: int = 12,
                      battery_wh: float = 600.0, eta: float = 0.9, tail_slots: int = 8,
                      n_orders: Optional[int] = None,
                      zone_weights: Union[None, ZoneWeights, Callable[[float, float], float]] = None,
                      restaurant_sampler: Optional[NYCRestaurantSampler] = None,
                      cuisine_map_overrides: Optional[Dict[str, str]] = None,
                      facilities_spec: Optional[Dict[str, Any]] = None,
                      demand_spec: Optional[Dict[str, Any]] = None,
                      physics: Optional[Dict[str, float]] = None,
                      pruning: Optional[Dict[str, Any]] = None,
                      paths: Optional[Dict[str, str]] = None,
                      name: Optional[str] = None) -> Instance:
    """Semi-real NYC E2 instance (R2.4) with the R2.2 instance-family conventions
    and the R2.1 ``cost_variant`` switch.

    Pipeline (mirrors ``generator.make_synthetic_instance``, reusing its helpers
    ``build_route_library``, ``TimeDependentGenerator`` and spec merging):

    1. ``box`` (default :data:`DEFAULT_BOX`) -> ``GridNetwork`` of ``grid_nx x grid_ny``
       150 m blocks (synthetic elevation / signals from ``seed``), R2.4 geometry.
    2. Zone weights: ``zone_weights`` (a :class:`ZoneWeights` or a callable) or
       :func:`default_zone_weights` = the ACS literature formula
       (``acs_weights.ACSZoneWeights``, NTA-2020 codes) when the ACS tables are
       present, else the :class:`GeoDaZoneWeights` fallback with its warning (R2.4);
       ``zw.meta()`` (source, warning, vintage, switches) is merged into ``meta``;
       :class:`NYCDestinationSampler` over the grid nodes inside the box.
    3. Restaurants: :class:`NYCRestaurantSampler` on the DOHMH rows inside the box
       (Kaggle cuisine shares, 2.5 km candidate radius, Zipf rank weights).
    4. Orders: ``n_orders = round(n_bikes x window_h x orders_per_bike_hour)``
       (R2.2 knob, base 1.5) released by ``TimeDependentGenerator`` with the R2.2
       assumed profile over ``[17:00, 17:00 + (H - tail_slots) Delta]``, ``r_i =
       floor(min / Delta)``, ``a_i = r_i + ceil(prep / Delta)`` with prep ~ DU{20..35},
       ``b_i = a_i + ceil(25 / Delta)``, ``hp = hd = 1``, ``P, w, v`` from the variant.
    5. Facilities: ``n_sites`` co-located swap+charge sites at the busiest-restaurant
       grid cells (:func:`busiest_restaurant_cells`) or at ``site_latlon`` snapped to
       the grid; R2.2 sizes ``B 3, C 2, K 8, M 1, sigma 1, P 4 kW``, grid group
       ``'sites'`` 8 kW (6 kW 18-20 h) (20)-(21); ``F, bB, bC`` from the variant (27).
       No hubs / services (``no_transfers`` is not forced: E = {} simply).
    6. Bikes start at the sites round robin with ``q0 ~ U{ceil(0.3 L)..floor(0.6 L)}``.
    7. ``V`` = restaurant nodes used + sites + customer nodes; one shortest grid route
       per ordered pair (E2 p.10) via ``build_route_library``; ``options['node_zone']``
       = NTA index per node; ``meta['semi_real'] = True`` with the box, the counts of
       restaurants / zones used, ``GEOMETRY_CAVEAT``, the zone-weight source and
       warning, the cost variant and the assumption-flagged time profile.

    Deterministic for a given ``seed`` (one ``numpy`` generator; Zipf ranks drawn
    first); the result validates and round-trips through JSON.
    """
    box = box or DEFAULT_BOX
    paths = {**DEFAULT_PATHS, **(paths or {})}
    fac_spec = _merge(NYC_FACILITIES_SPEC, facilities_spec)
    dem = _merge(NYC_DEMAND_SPEC, demand_spec)
    phys = _merge(DEFAULT_PHYSICS, physics)
    if fac_spec["mode"] != "colocated":
        raise ValueError("make_nyc_instance builds co-located sites only (R2.2); use the generator for hubs")
    H = int(round(float(window_h) * 60.0 / float(Delta_min)))
    if n_orders is None:
        n_orders = int(round(float(n_bikes) * float(window_h) * float(orders_per_bike_hour)))
    n_orders = max(0, int(n_orders))
    cv = cost_variant_params(cost_variant, window_h, paths.get("costs_usd"))
    cost = cv["costs"]
    dem.update(cv["demand_spec"])          # P, w, v of the variant
    rng = np.random.default_rng(int(seed))
    disc = Discretisation(Delta_h=Delta_min / 60.0, H=H, L=int(L),
                          eps_kwh=battery_wh / L / 1000.0, eta=float(eta))

    # 1. grid ---------------------------------------------------------------
    net = box.make_grid(rng, float(phys["traffic_light_prob"]))

    # 2. zone weights + destination sampler -----------------------------------
    if zone_weights is None:
        zone_weights = default_zone_weights(box, paths)
    zw_source = getattr(zone_weights, "source", type(zone_weights).__name__)
    zw_warning = getattr(zone_weights, "warning", None)
    zw_meta_fn = getattr(zone_weights, "meta", None)
    zw_meta = dict(zw_meta_fn()) if callable(zw_meta_fn) else {}
    dest = NYCDestinationSampler(box, zone_weights, rng)

    # 3. restaurants ------------------------------------------------------------
    if restaurant_sampler is None and cuisine_map_overrides:
        # units review F3: sensitivity remapping of DOHMH cuisine values (declared map otherwise)
        cmap = {**CUISINE_MAP, **{str(k): str(v) for k, v in cuisine_map_overrides.items()}}
        bad = set(cmap.values()) - set(KAGGLE_CLASSES) - {"other"}
        if bad:
            raise ValueError(f"cuisine_map_overrides map to unknown classes {sorted(bad)}")
        rest_df = restaurants_in_box(box)
        rest_df["kaggle_class"] = rest_df["cuisine"].map(lambda c: cmap.get(c, "other"))
        restaurant_sampler = NYCRestaurantSampler(
            box, rng, paths["kaggle"], restaurants=rest_df,
            radius_m=float(dem.get("radius_m", 2500.0)), prep_range_min=tuple(dem["prep_range_min"]))
    rest = restaurant_sampler or NYCRestaurantSampler(
        box, rng, paths["kaggle"], radius_m=float(dem.get("radius_m", 2500.0)),
        prep_range_min=tuple(dem["prep_range_min"]))
    restaurants_df = rest.df
    # unreachable supply (units review F3): rows whose class has no Kaggle share
    n_unmapped = int((restaurants_df["kaggle_class"] == "other").sum()) if "kaggle_class" in restaurants_df else 0
    unmapped_counts = (restaurants_df.loc[restaurants_df["kaggle_class"] == "other", "cuisine"].value_counts().to_dict()
                       if "kaggle_class" in restaurants_df and "cuisine" in restaurants_df else {})

    # 5a. sites (needed before orders only for the node list order) -------------
    if site_latlon is not None:
        site_nodes = [box.snap(float(a), float(b)) for a, b in site_latlon]
        sites_latlon = [[float(a), float(b)] for a, b in site_latlon]
    else:
        site_nodes = busiest_restaurant_cells(restaurants_df, int(n_sites), int(site_min_sep_blocks))
        sites_latlon = [list(box.node_latlon(v)) for v in site_nodes]
    seen = set()
    site_nodes = [v for v in site_nodes if not (v in seen or seen.add(v))]
    if not site_nodes:
        raise ValueError("no facility site could be placed")

    # 4. orders -----------------------------------------------------------------
    window_start = float(dem["window_start_h"])
    tail = int(tail_slots)
    release_slots = max(1, H - tail)
    release_span_h = release_slots * disc.Delta_h
    if dem["profile"] == "assumed_r2_2":
        # R2.2 block profile as a step function -- the same object the synthetic round-2
        # family uses (generator.block_profile); see assumed_hourly_profile for why the
        # 24-list must not be passed here (units review F1).
        profile: Any = assumed_block_config()
        profile_used: Dict[str, Any] = {
            "kind": "block_step", "config": _py(profile),
            "hourly_density": [float(block_profile(profile)(h + 0.5)) for h in range(24)]}
    else:
        profile = dem["profile"]
        profile_used = {"kind": ("block_step" if isinstance(profile, dict) else
                                 "hour_top_interpolated" if isinstance(profile, (list, tuple)) else
                                 "callable" if callable(profile) else "named"),
                        "value": (profile if isinstance(profile, str) else
                                  _py(profile) if isinstance(profile, (dict, list, tuple)) else
                                  getattr(profile, "__name__", "callable"))}
    release_gen = TimeDependentGenerator(profile, (window_start, window_start + release_span_h),
                                         float(max(n_orders, 1)))
    minutes = release_gen.sample(rng, n_orders) if n_orders > 0 else []
    promise_slots = int(math.ceil(float(dem["promise_after_ready_min"]) / Delta_min - 1e-9))
    plat_names = list(dem["platforms"].keys())
    plat_p = np.array([dem["platforms"][p] for p in plat_names], dtype=float)
    plat_p = plat_p / plat_p.sum()
    orders: List[Order] = []
    order_meta: List[Dict[str, Any]] = []
    rest_nodes: List[Node] = []
    cust_nodes: List[Node] = []
    used_restaurants: Dict[str, Dict[str, Any]] = {}
    for idx, minute in enumerate(minutes):
        r = min(int(math.floor(minute / Delta_min)), H - 1)
        d_node = dest.sample(rng)
        zone = dest.zone_of(d_node)
        rec = rest.sample_record(rng, d_node)
        o_node, prep = rec["node"], rec["prep_min"]
        a = r + int(math.ceil(prep / Delta_min - 1e-9))
        b = a + promise_slots
        platform = str(plat_names[int(rng.choice(len(plat_names), p=plat_p))])
        orders.append(Order(id=idx + 1, o=o_node, d=d_node, r=r, a=a, b=b, hp=int(dem["hp"]),
                            hd=int(dem["hd"]), P=float(dem["P"]), w=float(dem["w"]),
                            v=float(dem["v"]), platform=platform))
        d_lat, d_lon = dest.node_latlon[d_node]
        order_meta.append({"id": idx + 1, "release_min": float(minute), "prep_min": float(prep),
                           "zone": int(zone), "zone_code": dest.node_zone_code.get(d_node),
                           "customer_latlon": [float(d_lat), float(d_lon)],
                           "camis": rec["camis"], "cuisine": rec["cuisine"],
                           "cuisine_dohmh": rec["cuisine_dohmh"], "rank": rec["rank"],
                           "radius_m": rec["radius_m"], "dist_m": rec["dist_m"],
                           "n_candidates": rec["n_candidates"]})
        if o_node not in rest_nodes:
            rest_nodes.append(o_node)
        if d_node not in cust_nodes:
            cust_nodes.append(d_node)
        used_restaurants.setdefault(rec["camis"], {
            "camis": rec["camis"], "dba": rec["dba"], "cuisine": rec["cuisine"],
            "cuisine_dohmh": rec["cuisine_dohmh"], "lat": rec["lat"], "lon": rec["lon"],
            "node": list(o_node), "rank": rec["rank"]})

    # 7a. node set and routes -----------------------------------------------------
    nodes: List[Node] = []
    for v in rest_nodes + site_nodes + cust_nodes:
        if v not in nodes:
            nodes.append(v)
    routes = build_route_library(net, nodes, phys)

    # 5b. facilities ---------------------------------------------------------------
    fixed = bool(fac_spec["fixed"])
    facilities: List[Facility] = []
    for i, node in enumerate(site_nodes):
        facilities.append(Facility(
            id=f"S{i + 1}", node=node, swap=True, charge=True,
            y=1 if fixed else None,
            B=int(fac_spec["B"]) if fixed else None,
            C=int(fac_spec["C"]) if fixed else None,
            K=int(fac_spec["K"]), Cbar=int(fac_spec["Cbar"]), M=int(fac_spec["M"]),
            sigma=int(fac_spec["sigma"]), P_kw=float(fac_spec["P_kw"]), group="sites",
            F=float(cost["F"]), bB=float(cost["bB"]), bC=float(cost["bC"]),
            R_end=int(fac_spec["R_end"]),
            Fhat=float(cost["Fhat"]), bhat=float(cost["bhat"]), chat=float(cost["chat"])))

    def hour_of(t: int) -> float:
        return window_start + t * disc.Delta_h

    def in_peak(t: int) -> bool:
        lo, hi = fac_spec["peak_hours"]
        return lo <= hour_of(t) < hi

    # units review F8: the electricity price peak (TOU, Con Edison SC2 08-22 h per
    # cost_calibration.md section 6) is a separate window from the grid-limit peak
    # (18-20 h); ``facilities_spec['price_peak_hours']`` sets it, default = ``peak_hours``.
    price_peak_hours = tuple(fac_spec.get("price_peak_hours") or fac_spec["peak_hours"])

    def in_price_peak(t: int) -> bool:
        lo, hi = price_peak_hours
        return lo <= hour_of(t) < hi

    P_grid = {"sites": [float(fac_spec["grid_sites_peak_kw"] if in_peak(t) else fac_spec["grid_sites_kw"])
                        for t in range(H)]}

    # 6. bikes -----------------------------------------------------------------------
    lo_frac, hi_frac = dem["init_frac"]
    q_lo = int(math.ceil(lo_frac * L - 1e-9))
    q_hi = max(q_lo, int(math.floor(hi_frac * L + 1e-9)))
    depots = list(site_nodes)
    bikes = [Bike(id=k + 1, v0=depots[k % len(depots)], q0=int(rng.integers(q_lo, q_hi + 1)))
             for k in range(int(n_bikes))]

    # 7b. prices, options, meta ---------------------------------------------------------
    pi: Any = float(cost["pi"])
    if cost.get("pi_peak") is not None:
        pi = {(f.id, t): float(cost["pi_peak"] if in_price_peak(t) else cost["pi"])
              for f in facilities for t in range(H)}
    options: Dict[str, Any] = {"node_zone": [[list(v), int(dest.zone_of(v))] for v in nodes]}
    if pruning:
        options.update(pruning)
    zones_used = sorted({c for c in (dest.node_zone_code[v] for v in dest.support) if c is not None})
    meta: Dict[str, Any] = {
        "name": name or f"nyc seed={seed} K={n_bikes} I={n_orders} H={H} L={L} {cost_variant}",
        "generator": "ebike_swap_sim.data_nyc.make_nyc_instance",
        "semi_real": True,
        "geometry_caveat": GEOMETRY_CAVEAT,
        "box": box.to_dict(),
        "params": _py({
            "seed": seed, "n_bikes": n_bikes, "window_h": window_h,
            "orders_per_bike_hour": orders_per_bike_hour, "n_orders": n_orders, "H": H,
            "Delta_min": Delta_min, "L": L, "battery_wh": battery_wh, "eta": eta,
            "tail_slots": tail, "n_sites": n_sites, "site_min_sep_blocks": site_min_sep_blocks,
            "facilities_spec": fac_spec, "demand_spec": dem, "physics": phys, "pruning": pruning,
            "restaurant_sampler": {"radius_m": rest.radius_m, "radius_growth": rest.radius_growth,
                                   "min_candidates": rest.min_candidates, "zipf_s": rest.zipf_s,
                                   "prep_range_min": list(rest.prep_range_min)},
        }),
        "cost_variant": cost_variant,
        "cost_variant_params": _py(cv),
        # R2.1 'record variant, window and every coefficient' -- flat, as generator.py writes it
        # (units review F2); experiment helpers read inst.meta['costs']
        "costs": _py({
            "variant": cv["variant"], "window_h": cv["window_h"],
            "window_scale": cv.get("window_scale"), "source": cv.get("source"),
            **{k: cost.get(k) for k in ("kappa", "pi", "pi_peak", "F", "F_hub", "bB", "bC", "Fhat", "bhat", "chat")},
            **{k: dem[k] for k in ("P", "w", "v")},
            **{k: cv["services_spec"][k] for k in ("f", "vreb")},
            "q_res": cost["q_res"], "rho": cost["rho"]}),
        "price_peak_hours": (list(price_peak_hours) if cost.get("pi_peak") is not None else None),
        "n_restaurants_in_box": int(rest.n_restaurants),
        "n_restaurants_unmapped_in_box": n_unmapped,
        "unmapped_share_in_box": (n_unmapped / rest.n_restaurants) if rest.n_restaurants else 0.0,
        "unmapped_cuisines_in_box": _py({str(k): int(v) for k, v in unmapped_counts.items()}),
        "cuisine_map_overrides": _py(dict(cuisine_map_overrides)) if cuisine_map_overrides else None,
        "n_restaurants_used": len(used_restaurants),
        "cuisine_shares_used": _py(rest.cuisine_shares()),
        "cuisine_classes_dropped": list(rest.dropped_classes),
        "n_zones_used": len(zones_used),
        "zones_used": zones_used,
        "zone_weights_source": str(zw_source),
        "zone_weights_warning": zw_warning,
        **_py({k: v for k, v in zw_meta.items() if k not in ("zone_weights_source", "zone_weights_warning")}),
        "zone_mass": _py({str(k): v for k, v in dest.zone_totals().items()}),
        "time_profile": _py(ASSUMED_TIME_PROFILE),
        "hourly_profile_used": _py(profile_used),
        "window_h": [window_start, window_start + H * disc.Delta_h],
        "release_window_h": [window_start, window_start + release_span_h],
        "restaurants": [[list(n), c] for n, c in
                        ((_node(rec["node"]), rec["cuisine"]) for rec in used_restaurants.values())],
        "restaurant_records": _py(list(used_restaurants.values())),
        "anchors": [],
        "customers": [list(v) for v in cust_nodes],
        "depots": [list(d) for d in depots],
        "sites": [list(s) for s in site_nodes],
        "sites_latlon": _py(sites_latlon),
        "hubs": [],
        "orders": _py(order_meta),
        "p_ch_kw": disc.p_ch_kw,
    }
    inst = Instance(disc=disc, nodes=nodes, routes=routes, bikes=bikes, orders=orders,
                    facilities=facilities, services=[], P_grid=P_grid,
                    kappa=float(cost["kappa"]), pi=pi, q_res=int(cost["q_res"]),
                    rho=float(cost["rho"]), options=options, meta=meta)
    inst.validate()
    return inst
