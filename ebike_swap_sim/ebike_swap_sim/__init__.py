"""E2 delivery-bike / battery-swap optimisation package (NYC e-bike delivery).

Module map
----------
config       -- SimConfig (physical parameters of the synthetic simulator)
network      -- GridNetwork: synthetic Manhattan grid, route(u, v) -> GridRoute
or_instance  -- Instance / Discretisation / Route / Bike / Order / Facility / Service
                (plain dataclasses, JSON round-trip, validate, toy instances)
arcs         -- ArcLibrary: time-expanded bike networks per E2 (1)-(4), (9)
evaluate     -- Schedule, cost (26)-(32), check (5)-(22), metrics, reconstruct_inventory
ilp          -- gurobipy model of E2 (lazy import; needs Gurobi)
baseline     -- event-driven policy on the same Instance / ArcLibrary (lazy import)
generator    -- synthetic instance generator (lazy import)
costs        -- round-2 cost variants (DECISIONS R2.1; lazy import)
data_nyc     -- semi-real NYC instances: DOHMH restaurants, NTA zones, study box (R2.4; lazy)
acs_weights  -- ACS literature zone weights (R2.4; lazy)

The modules ``ilp``, ``baseline``, ``generator``, ``costs``, ``data_nyc`` and
``acs_weights`` are imported lazily through ``ebike_swap_sim.<name>`` so that the
package imports without gurobipy / pandas-heavy data loaders.
"""
from __future__ import annotations

import importlib

from .config import SimConfig
from .network import GridNetwork, RoadNetwork, Route as GridRoute
from .or_instance import (
    DEFAULT_OPTIONS,
    Bike,
    Discretisation,
    Facility,
    Instance,
    Order,
    Route,
    Service,
    battery_swap_p7_instance,
    ceil_tol,
    toy_instance,
)
from .arcs import SINK, Arc, ArcLibrary, InfeasibleInstanceError, build_arcs, compute_gbar
from .evaluate import (
    Schedule,
    check,
    cost,
    facility_vars,
    in_transit,
    metrics,
    reconstruct_inventory,
    swap_counts,
    transfer_counts,
)

_LAZY_MODULES = {"ilp", "baseline", "generator", "costs", "data_nyc", "acs_weights", "sites_nyc", "bilevel"}

__all__ = [
    "SimConfig", "GridNetwork", "RoadNetwork", "GridRoute",
    "DEFAULT_OPTIONS", "Bike", "Discretisation", "Facility", "Instance", "Order", "Route",
    "Service", "battery_swap_p7_instance", "ceil_tol", "toy_instance",
    "SINK", "Arc", "ArcLibrary", "InfeasibleInstanceError", "build_arcs", "compute_gbar",
    "Schedule", "check", "cost", "facility_vars", "in_transit", "metrics",
    "reconstruct_inventory", "swap_counts", "transfer_counts",
]  # lazy modules (ilp, baseline, ...) are deliberately not in __all__


def __getattr__(name: str):
    """Lazy access to the gurobipy-dependent / heavier modules (ilp, baseline, generator, costs, data_nyc, acs_weights)."""
    if name in _LAZY_MODULES:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
