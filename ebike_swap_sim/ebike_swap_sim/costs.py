"""Cost-coefficient variants for the E2 objective (26)-(32) and budget (33).

Implements ``notes/DECISIONS.md`` section **R2.1** ("Cost units: USD"): one
switch ``cost_variant`` selects a complete set of coefficients for
:func:`ebike_swap_sim.generator.make_synthetic_instance`, in the same key
layout as the generator defaults (``DEFAULT_COSTS`` / ``DEFAULT_DEMAND_SPEC`` /
``DEFAULT_SERVICES_SPEC``), so that the result can be passed straight through
as ``costs=`` / ``demand_spec=`` / ``services_spec=``.

Variants (R2.1)
---------------
``toy``
    E2 p.14 units kept for continuity with round 1: kappa 1 /km, pi 2 /kWh,
    P 100, w 12 /h, v 24 /h, f 5, v_reb 0.2, F 20 (F_hub 40), bB 3, bC 2 per
    horizon, budget coefficients Fhat 5000 / bhat 500 / chat 300.  The toy
    numbers are *per horizon* as in round 1 and are **not** rescaled with the
    window length.
``usd_A``
    the calibration agent's base (``generator_overrides.base`` of the JSON):
    kappa 0.50 $/km (wear + 25 % labour), w 40 $/h, v 80 $/h, P 30 $, pi 0.32
    $/kWh, f_e 20 $, v_reb 1.0 $, F 12.03 / F_hub 29.19 $ per 4 h window,
    bB 0.332, bC 0.082 $ per 4 h, Fhat 50,000 / bhat 450 / chat 400 $.
``usd_sunk``
    **default** for new families.  E2 p.9: bikes and operators are given fleet
    resources, so rider labour is sunk: ``usd_A`` with kappa 0.12 $/km (wear
    only), w 18 $/h (customer value of waiting only), v 36 $/h; P and all other
    coefficients as ``usd_A``.
``usd_B``
    clean split (``variants.option_B_clean_split``): kappa 1.60 $/km (full
    labour + wear on every arc), w 18 $/h, v 36 $/h, rest as ``usd_A``.
``usd_low`` / ``usd_high``
    the low / high envelopes (``generator_overrides.low`` / ``.high``) for
    sensitivity.

Window scaling (R2.1): ``F``, ``F_hub``, ``bB``, ``bC`` are per
``REFERENCE_WINDOW_H = 4`` h in the JSON and scale linearly with ``window_h``
(8 h -> x2, 2 h -> x0.5); kappa, pi, w, v, P, f_e, v_reb and the budget
coefficients do not scale.

Known spec inconsistency (units review F5, kept as written): the JSON ``bB`` =
0.332 per 4 h is the sum of a time-proportional holding cost (0.119) and a
**one-off** initial full charge (0.213 = 0.6 / 0.9 x 0.32, ``coefficients.b^B_j.
initial_charge``).  R2.1 scales the whole ``bB`` with the window, so an 8 h instance
charges the initial charge twice (``bB`` 0.664) and a 2 h instance half of it.  The
magnitude is 0.213 $ per spare per extra 4 h (9 spares -> 1.9 $ per 8 h instance,
about 0.3 % of a ~600 $ total); the 4 h families are exact.  :data:`BB_INITIAL_CHARGE_USD`
and the ``'notes'`` entry of :func:`load_cost_calibration` document it; splitting
``bB`` into ``bB_hold`` / ``bB_init`` is a JSON / DECISIONS change, not made here.

The machine-readable source is ``notes/data/cost_calibration_usd.json``
(``DEFAULT_CALIBRATION_PATH``; derivations in ``notes/cost_calibration.md``).
Only the ``toy`` variant works without the file.
"""
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "DEFAULT_CALIBRATION_PATH", "REFERENCE_WINDOW_H", "WINDOW_SCALED_KEYS", "BB_INITIAL_CHARGE_USD",
    "TOY_COEFFICIENTS", "COST_VARIANTS", "cost_variants", "load_cost_calibration",
    "flat_coefficients", "apply_cost_calibration", "variant_table",
]

#: ``notes/data/cost_calibration_usd.json`` relative to the package
#: (``<repo>/ebike_swap_sim/ebike_swap_sim/costs.py`` -> ``<repo>/notes/data``).
DEFAULT_CALIBRATION_PATH: str = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "data",
    "cost_calibration_usd.json"))

#: Window length (h) the JSON's F / F_hub / bB / bC refer to (R2.1: "values above are per 4 h").
REFERENCE_WINDOW_H: float = 4.0

#: Coefficients of ``costs`` that scale linearly with the window length (R2.1).
WINDOW_SCALED_KEYS: Tuple[str, ...] = ("F", "F_hub", "bB", "bC")

#: One-off initial full charge included in the JSON ``bB`` (base, $ per spare; units
#: review F5).  It is window-scaled with the rest of ``bB`` per R2.1, which overstates it
#: by ``BB_INITIAL_CHARGE_USD x (window_scale - 1)`` per spare for windows other than 4 h.
BB_INITIAL_CHARGE_USD: float = 0.213

#: Round-1 toy unit system (E2 p.14 + DECISIONS "Default discretisation"), grouped
#: like the generator defaults.  Identical to ``generator.DEFAULT_COSTS`` (minus
#: ``q_res`` / ``rho``, which are not prices), ``DEFAULT_DEMAND_SPEC[P, w, v]`` and
#: ``DEFAULT_SERVICES_SPEC[f, vreb]``.
TOY_COEFFICIENTS: Dict[str, Dict[str, Any]] = {
    "costs": {"kappa": 1.0, "pi": 2.0, "pi_peak": None, "F": 20.0, "F_hub": 40.0,
              "bB": 3.0, "bC": 2.0, "Fhat": 5000.0, "bhat": 500.0, "chat": 300.0},
    "demand_spec": {"P": 100.0, "w": 12.0, "v": 24.0},
    "services_spec": {"f": 5.0, "vreb": 0.2},
}

#: Variant table (R2.1).  ``base`` is the ``generator_overrides`` block of the JSON
#: the variant starts from (``None`` = the hard-coded toy numbers), ``overrides``
#: are applied on top, ``doc`` is the one-line description returned by
#: :func:`cost_variants`.
COST_VARIANTS: Dict[str, Dict[str, Any]] = {
    "toy": {
        "base": None, "overrides": {},
        "doc": "E2 p.14 toy units (round 1); per horizon, not window-scaled",
    },
    "usd_A": {
        "base": "base", "overrides": {},
        "doc": "USD base: kappa 0.50 (wear + 25% labour), w 40, v 80, P 30 (calibration agent's option A)",
    },
    "usd_sunk": {
        "base": "base",
        "overrides": {"costs": {"kappa": 0.12}, "demand_spec": {"w": 18.0, "v": 36.0}},
        "doc": "DEFAULT. usd_A with rider labour sunk (E2 p.9): kappa 0.12 wear only, w 18 customer value, v 36",
    },
    "usd_B": {
        "base": "base",
        "overrides": {"costs": {"kappa": 1.6}, "demand_spec": {"w": 18.0, "v": 36.0}},
        "doc": "clean split (option B): kappa 1.60 full labour per km on every arc, w 18, v 36",
    },
    "usd_low": {
        "base": "low", "overrides": {},
        "doc": "low envelope of every coefficient (sensitivity)",
    },
    "usd_high": {
        "base": "high", "overrides": {},
        "doc": "high envelope of every coefficient (sensitivity)",
    },
}


def cost_variants() -> Dict[str, str]:
    """Names and one-line descriptions of the selectable cost variants
    (DECISIONS R2.1), in documentation order: ``toy``, ``usd_A``, ``usd_sunk``
    (default), ``usd_B``, ``usd_low``, ``usd_high``."""
    return {name: spec["doc"] for name, spec in COST_VARIANTS.items()}


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_cost_calibration(path: Optional[str] = None, variant: str = "usd_sunk",
                          window_h: float = REFERENCE_WINDOW_H) -> Dict[str, Any]:
    """Coefficients of one cost ``variant`` for a planning window of ``window_h``
    hours (DECISIONS R2.1).

    Parameters
    ----------
    path : JSON file (default :data:`DEFAULT_CALIBRATION_PATH`); only read for
        the USD variants.
    variant : one of :func:`cost_variants` (``'toy'``, ``'usd_A'``, ``'usd_sunk'``,
        ``'usd_B'``, ``'usd_low'``, ``'usd_high'``).
    window_h : window length in hours; ``F``, ``F_hub``, ``bB``, ``bC`` of the USD
        variants are multiplied by ``window_h / 4`` (R2.1).  The toy variant is
        not scaled.

    Returns a dict::

        {"variant", "window_h", "reference_window_h", "window_scaled_keys",
         "window_scale",            # factor applied (1.0 for toy)
         "source",                  # JSON path or 'builtin toy'
         "costs":         {kappa, pi, pi_peak, F, F_hub, bB, bC, Fhat, bhat, chat},
         "demand_spec":   {P, w, v},          # w, v in $/h (generator multiplies by Delta)
         "services_spec": {f, vreb}}

    whose three inner dicts use the keys of ``generator.DEFAULT_COSTS``,
    ``DEFAULT_DEMAND_SPEC`` and ``DEFAULT_SERVICES_SPEC`` and can be passed
    straight to :func:`ebike_swap_sim.generator.make_synthetic_instance`.
    Raises ``KeyError`` for an unknown variant and ``ValueError`` for
    ``window_h <= 0``.
    """
    if variant not in COST_VARIANTS:
        raise KeyError(f"unknown cost variant {variant!r}; known: {list(COST_VARIANTS)}")
    window_h = float(window_h)
    if not window_h > 0:
        raise ValueError("window_h must be positive")
    spec = COST_VARIANTS[variant]
    if spec["base"] is None:
        groups = copy.deepcopy(TOY_COEFFICIENTS)
        source = "builtin toy (E2 p.14)"
        scale = 1.0
    else:
        src = path or DEFAULT_CALIBRATION_PATH
        data = _read_json(src)
        block = data["generator_overrides"][spec["base"]]
        groups = {
            "costs": dict(block["costs"]),
            "demand_spec": dict(block["demand_spec"]),
            "services_spec": dict(block["services_spec"]),
        }
        ref = float(data.get("meta", {}).get("window_h", REFERENCE_WINDOW_H))
        scale = window_h / ref
        for key in WINDOW_SCALED_KEYS:
            if groups["costs"].get(key) is not None:
                groups["costs"][key] = float(groups["costs"][key]) * scale
        source = src
    for group, over in spec["overrides"].items():
        groups[group].update(over)
    # normalise numeric types (JSON ints -> float, keep None for pi_peak)
    for group in groups.values():
        for k, v in list(group.items()):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                group[k] = float(v)
    notes: List[str] = []
    if spec["base"] is not None and abs(scale - 1.0) > 1e-12:
        notes.append(
            f"bB includes a one-off initial charge of {BB_INITIAL_CHARGE_USD} $ per spare that R2.1 "
            f"scales with the window like the holding part; at window_scale {scale:g} this over-/under-"
            f"states bB by {BB_INITIAL_CHARGE_USD * (scale - 1.0):+.3f} $ per spare (units review F5).")
    return {
        "variant": variant,
        "window_h": window_h,
        "reference_window_h": REFERENCE_WINDOW_H,
        "window_scaled_keys": list(WINDOW_SCALED_KEYS) if spec["base"] is not None else [],
        "window_scale": scale,
        "source": source,
        "costs": groups["costs"],
        "demand_spec": groups["demand_spec"],
        "services_spec": groups["services_spec"],
        "notes": notes,
    }


def flat_coefficients(cal: Dict[str, Any]) -> Dict[str, Any]:
    """Flat ``{symbol: value}`` view of a :func:`load_cost_calibration` result for
    ``Instance.meta['costs']`` (R2.1: record variant, window and every
    coefficient): ``variant``, ``window_h``, ``window_scale``, ``source``, then
    kappa, pi, pi_peak, F, F_hub, bB, bC, Fhat, bhat, chat, P, w, v, f, vreb."""
    out: Dict[str, Any] = {
        "variant": cal["variant"], "window_h": cal["window_h"],
        "window_scale": cal["window_scale"], "source": cal["source"],
    }
    for group in ("costs", "demand_spec", "services_spec"):
        for k, v in cal[group].items():
            out[k] = v
    return out


def apply_cost_calibration(cal: Dict[str, Any],
                           costs: Optional[Dict[str, Any]] = None,
                           demand_spec: Optional[Dict[str, Any]] = None,
                           services_spec: Optional[Dict[str, Any]] = None
                           ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Merge a :func:`load_cost_calibration` result under explicit generator
    overrides: returns ``(costs, demand_spec, services_spec)`` partial dicts where
    the variant's coefficients are the base and any key present in the given
    dicts wins (R2.1: "existing calls that pass costs explicitly keep theirs")."""
    c = {**cal["costs"], **(costs or {})}
    d = {**cal["demand_spec"], **(demand_spec or {})}
    s = {**cal["services_spec"], **(services_spec or {})}
    return c, d, s


def variant_table(path: Optional[str] = None, window_h: float = REFERENCE_WINDOW_H
                  ) -> List[Dict[str, Any]]:
    """Flat rows (one per variant of :func:`cost_variants`) for documentation
    tables: :func:`flat_coefficients` of every variant at ``window_h``."""
    return [flat_coefficients(load_cost_calibration(path, name, window_h)) for name in COST_VARIANTS]
