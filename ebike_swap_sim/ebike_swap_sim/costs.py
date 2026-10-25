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
``usd_r6``
    round 6 (``notes/penalty_calibration.md`` sections 1, 6 and 7): ``usd_sunk``
    with the order prices of (30)-(31) recalibrated to P 60 $ per undelivered
    order (system view: platform cash loss 38 $ + the customer's ticket and
    wasted wait + churn) and v 15 $/h from the promise ``b_i`` (least-squares
    fit to a 5-10 $ flat late credit plus slow churn); w 18 $/h from release
    and every other coefficient unchanged.  A change of DATA only: no E2
    equation changes and (31) keeps its form.

Repricing an existing instance (round 6): :func:`reprice_orders` returns a copy
whose orders carry new ``P`` / ``w`` / ``v`` and whose meta records the prices.
The delivery-arc cost ``theta`` (31) is stored on every arc when the library is
built, so a change of ``w`` or ``v`` REQUIRES rebuilding the arc library
(``build_arcs`` on the repriced copy); :func:`check_lib_prices` compares the
library's ``theta`` with ``Instance.theta`` and raises on a stale library (the
ILP model builder calls it).  A change of ``P`` alone keeps the library valid.

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
    # round 5 (notes/reading_to_model.md: M5, A6, M10)
    "TARIFFS", "load_tariff", "crf", "allocate_per_window", "FLEET_COST_DEFAULTS",
    "allocated_bike_cost", "pack_cost_scaling", "position_cost_per_window",
    "demand_charge_per_window", "demand_charge_proxy",
    # round 6 (notes/penalty_calibration.md): order repricing as data
    "R6_PRICING", "LEGACY_PRICING", "PRICE_KEYS", "PricingMismatchError", "order_prices",
    "uniform_order_prices", "order_price_signature", "pricing_cache_component", "pricing_label",
    "reprice_orders", "check_lib_prices",
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
    "usd_r6": {
        "base": "base",
        "overrides": {"costs": {"kappa": 0.12}, "demand_spec": {"P": 60.0, "w": 18.0, "v": 15.0}},
        "doc": "round 6: usd_sunk with P 60 and v 15 $/h from b_i (notes/penalty_calibration.md 1, 6, 7); w 18",
    },
}


def cost_variants() -> Dict[str, str]:
    """Names and one-line descriptions of the selectable cost variants
    (DECISIONS R2.1), in documentation order: ``toy``, ``usd_A``, ``usd_sunk``
    (default), ``usd_B``, ``usd_low``, ``usd_high``, then ``usd_r6`` (round-6 order
    prices, ``notes/penalty_calibration.md``)."""
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


# ---------------------------------------------------------------------------
# Round 5 (notes/reading_to_model.md): tariffs, allocations and data levers.
# Nothing below changes a cost variant of R2.1 or an E2 equation: these helpers
# produce parameter values (data) for the new instance families and sweeps.
# ---------------------------------------------------------------------------
#: Electricity tariffs selectable by name (plan item M5, ITSC-21 TOU pricing).  ``tou``
#: is ``variants.tou_electricity`` of the calibration JSON (Con Edison SC2 time-of-use,
#: Oct-May peak): off-peak 0.132 $/kWh, peak 0.442 $/kWh, peak hours Mon-Fri
#: 08:00-22:00; ``tou_summer`` uses the Jun-Sep peak 0.74 $/kWh.  ``flat`` keeps the
#: variant's flat ``pi`` (pi_peak None).  Prices enter E2 (28) through ``pi_jt``.
TARIFFS: Dict[str, str] = {
    "flat": "flat pi of the cost variant (R2.1); pi_peak None",
    "tou": "Con Edison SC2 TOU (Oct-May): off-peak 0.132, peak 0.442 $/kWh, peak 08-22 h",
    "tou_summer": "Con Edison SC2 TOU (Jun-Sep): off-peak 0.132, peak 0.74 $/kWh, peak 08-22 h",
}


def load_tariff(name: str = "tou", path: Optional[str] = None) -> Dict[str, Any]:
    """Electricity tariff ``name`` of :data:`TARIFFS` as generator overrides (plan item M5;
    E2 (28) price ``pi_jt``).

    Returns ``{'name', 'source', 'costs': {'pi', 'pi_peak'}, 'facilities_spec':
    {'price_peak_hours': (lo, hi)}}``; for ``flat`` the two inner dicts are empty.  The
    values are read from ``variants.tou_electricity`` of the calibration JSON
    (``pi`` off-peak, ``pi_peak`` peak, ``facilities_spec.peak_hours``; ``summer_pi_peak``
    for ``tou_summer``).  Pass them as ``costs=`` / ``facilities_spec=`` of the generator
    (``make_synthetic_instance(tariff=...)`` does this); ``price_peak_hours`` is the
    price window, separate from the grid-limit peak ``peak_hours`` (units review F8).
    Raises ``KeyError`` for an unknown tariff."""
    if name not in TARIFFS:
        raise KeyError(f"unknown tariff {name!r}; known: {list(TARIFFS)}")
    if name == "flat":
        return {"name": name, "source": "cost variant", "costs": {}, "facilities_spec": {}}
    src = path or DEFAULT_CALIBRATION_PATH
    tou = _read_json(src)["variants"]["tou_electricity"]
    peak = float(tou["summer_pi_peak"]) if name == "tou_summer" else float(tou["costs"]["pi_peak"])
    hours = tou["facilities_spec"]["peak_hours"]
    return {
        "name": name, "source": src,
        "costs": {"pi": float(tou["costs"]["pi"]), "pi_peak": peak},
        "facilities_spec": {"price_peak_hours": (float(hours[0]), float(hours[1]))},
    }


def crf(rate: float, years: float) -> float:
    """Capital recovery factor ``r (1 + r)^n / ((1 + r)^n - 1)`` (``1 / n`` at ``r = 0``),
    the annualisation of the calibration JSON (``meta.allocation_rule``)."""
    r, n = float(rate), float(years)
    if n <= 0:
        raise ValueError("years must be positive")
    if abs(r) < 1e-12:
        return 1.0 / n
    return r * (1.0 + r) ** n / ((1.0 + r) ** n - 1.0)


def allocate_per_window(capex: float, rate: float = 0.07, life_years: float = 10.0,
                        opex_per_year: float = 0.0, window_h: float = REFERENCE_WINDOW_H,
                        days_per_month: float = 30.0, hours_per_day: float = 16.0) -> float:
    """Per-window allocation of an investment by the JSON rule (``meta.allocation_rule``):
    ``(capex x CRF(rate, life) + opex) / 12 / days_per_month x window_h / hours_per_day``.
    Used for the horizon-allocated set-up costs of E2 (27) in the plan items A6 and
    M10(a).  Reproduces ``F_j`` = 12.03 $ per 4 h from capex 50,000, CRF(7 %, 10 y) and
    opex 10,200 $/yr."""
    annual = float(capex) * crf(rate, life_years) + float(opex_per_year)
    return annual / 12.0 / float(days_per_month) * float(window_h) / float(hours_per_day)


#: Fleet cost parameters of the fleet x spare x pack sweep (plan item A6, ITSC-21 Table I:
#: fleet procurement dominates).  ``bike_capex_usd`` = 1,600 $ (bike price of the kappa
#: wear derivation in the calibration JSON), ``bike_life_years`` = 3 (declared assumption,
#: not calibrated; the JSON wear figure implies a 20,000 km life), discount 7 %
#: (JSON base), ``rider_wage_per_h`` = 22.13 $/h (NYC DCWP 2026 minimum pay, JSON
#: ``labour_facts``).  Bikes and riders are *given* resources in E2 (p.9), so these numbers
#: never enter (26)-(32); they price "one more bike" against "one more spare" in reports.
FLEET_COST_DEFAULTS: Dict[str, float] = {
    "bike_capex_usd": 1600.0, "bike_life_years": 3.0, "rate": 0.07,
    "rider_wage_per_h": 22.13, "hours_per_day": 16.0, "days_per_month": 30.0,
}


def allocated_bike_cost(window_h: float = REFERENCE_WINDOW_H, include_rider: bool = True,
                        **overrides: float) -> Dict[str, Any]:
    """Allocated cost of one bike (and its rider) per planning window (plan item A6).

    ``bike_capex_per_window`` = :func:`allocate_per_window` of ``bike_capex_usd`` over
    ``bike_life_years``; ``rider_wage_per_window`` = ``rider_wage_per_h x window_h`` when
    ``include_rider``; ``allocated_per_bike_window`` = their sum.  ``overrides`` replace
    entries of :data:`FLEET_COST_DEFAULTS`.  Note: the wear part of kappa (0.08 $/km bike
    depreciation) prices the same bike per km inside (29); the allocation here is a
    fleet-size (outside-E2) price and must not be added to an objective that already
    contains the per-km depreciation without saying so."""
    unknown = set(overrides) - set(FLEET_COST_DEFAULTS)
    if unknown:
        raise KeyError(f"unknown fleet cost keys {sorted(unknown)}")
    par = {**FLEET_COST_DEFAULTS, **{k: float(v) for k, v in overrides.items()}}
    bike = allocate_per_window(par["bike_capex_usd"], par["rate"], par["bike_life_years"], 0.0,
                               window_h, par["days_per_month"], par["hours_per_day"])
    rider = par["rider_wage_per_h"] * float(window_h) if include_rider else 0.0
    return {"window_h": float(window_h), "bike_capex_per_window": bike,
            "rider_wage_per_window": rider, "allocated_per_bike_window": bike + rider,
            "include_rider": bool(include_rider), "parameters": par,
            "source": "calibration JSON (bike 1,600 $, DCWP 22.13 $/h); life 3 y assumption"}


def pack_cost_scaling(costs: Dict[str, Any], pack_kwh: float, ref_pack_kwh: float = 0.6) -> Dict[str, Any]:
    """Battery coefficients of E2 (27) / (33) for another pack size (plan item A6): ``bB``
    (holding + initial charge per window) and ``bhat`` (pack price) scale linearly with
    the pack energy relative to the calibrated 0.6 kWh pack (declared assumption: the JSON
    gives 400-800 $ for the 1 kWh class, i.e. roughly proportional).  Returns a copy of
    ``costs`` with the two keys rescaled (other keys unchanged)."""
    if pack_kwh <= 0 or ref_pack_kwh <= 0:
        raise ValueError("pack sizes must be positive")
    out = dict(costs)
    factor = float(pack_kwh) / float(ref_pack_kwh)
    for key in ("bB", "bhat"):
        if out.get(key) is not None:
            out[key] = float(out[key]) * factor
    return out


def position_cost_per_window(position_capex: float = 400.0, life_years: float = 10.0,
                             rate: float = 0.07, window_h: float = REFERENCE_WINDOW_H) -> float:
    """Per-window set-up cost of one extra swap position (plan item M10(a); E2 (22) M_j,
    priced through F_j in (27)).  Default capex 400 $ = the slot capex incl. cabinet share
    of the JSON (``chat``), annualised over the cabinet life (10 y, 7 %) like ``F_j``."""
    return allocate_per_window(position_capex, rate, life_years, 0.0, window_h)


def demand_charge_per_window(usd_per_kw_month: float, window_h: float = REFERENCE_WINDOW_H,
                             days_per_month: float = 30.0, hours_per_day: float = 16.0) -> float:
    """Monthly demand tariff (``$ per kW of monthly peak``) rescaled to one planning window
    by the JSON allocation rule (plan item M10(b); ITSC-21 demand charge).  No NYC tariff
    value is built in (none is calibrated in the JSON); the caller must supply it."""
    return float(usd_per_kw_month) / float(days_per_month) * float(window_h) / float(hours_per_day)


def demand_charge_proxy(values: Dict[float, Optional[float]], usd_per_kw_month: float,
                        window_h: float = REFERENCE_WINDOW_H, n_sites: int = 1) -> Dict[str, Any]:
    """Exact demand-charge pricing by a site power-cap sweep (plan item M10(b); OE5 avoided).

    ``values`` maps a common site cap ``P_j`` (kW, E2 (20)) to the optimal value ``V(P_j)``
    of the instance with that cap (``None`` = infeasible / not solved).  Because the peak
    charging power only takes multiples of ``p_ch``, ``min_P V(P) + p_dem n_sites P`` over
    the sweep ``{0, p_ch, ..., C_j p_ch}`` equals the optimum with a demand charge.  Returns
    ``{'p_dem_per_kw_window', 'rows': [{'P_kw', 'V', 'demand_charge', 'total'}], 'best'}``."""
    p_dem = demand_charge_per_window(usd_per_kw_month, window_h)
    rows = []
    for P in sorted(values):
        V = values[P]
        charge = p_dem * float(P) * int(n_sites)
        rows.append({"P_kw": float(P), "V": V, "demand_charge": charge,
                     "total": None if V is None else float(V) + charge})
    feasible = [r for r in rows if r["total"] is not None]
    best = min(feasible, key=lambda r: (r["total"], r["P_kw"])) if feasible else None
    return {"p_dem_per_kw_window": p_dem, "rows": rows, "best": best}



# ---------------------------------------------------------------------------
# Round 6 (notes/penalty_calibration.md sections 1, 6, 7): order prices as data.
# P_i, w_i, v_i are fields of every Order (E2 (30)-(31)); nothing below changes an
# equation.  The delivery-arc coefficient theta (31) is computed by arcs.build_arcs and
# stored on the arc, so a library built before a change of w or v is STALE: rebuild it
# (build_arcs on the repriced copy) and verify with check_lib_prices.
# ---------------------------------------------------------------------------
#: Order price keys of E2 (30)-(31).
PRICE_KEYS: Tuple[str, ...] = ("P", "w", "v")

#: Round-6 base pricing (``notes/penalty_calibration.md`` section 1 item 5, section 6.1 base
#: column, section 6.2 fit, section 7 item 1): P 60 USD per undelivered order, w 18 USD/h from
#: release r_i (unchanged), v 15 USD/h from the promise b_i.
R6_PRICING: Dict[str, Any] = {
    "P": 60.0, "w": 18.0, "v": 15.0,
    "source": "notes/penalty_calibration.md sections 1, 6, 7 (round-6 base: P 60, w 18, v 15 from b_i)",
}

#: Pricing of ``usd_sunk`` (rounds 2-5; the 'legacy bridge' of round 6).
LEGACY_PRICING: Dict[str, Any] = {
    "P": 30.0, "w": 18.0, "v": 36.0, "source": "usd_sunk (DECISIONS R2.1; rounds 2-5)",
}

#: Variants that differ from ``usd_sunk`` only in the order prices; a repriced copy of one of
#: them is relabelled with the other when its prices match it exactly.
_PRICE_ONLY_VARIANTS: Dict[str, Dict[str, float]] = {
    "usd_sunk": {k: float(LEGACY_PRICING[k]) for k in ("P", "w", "v")},
    "usd_r6": {k: float(R6_PRICING[k]) for k in ("P", "w", "v")},
}


class PricingMismatchError(ValueError):
    """An arc library's delivery-arc ``theta`` (31) disagrees with ``Instance.theta``: the
    library was built under other order prices and must be rebuilt."""


def order_prices(inst: Any) -> List[Tuple[Any, float, float, float]]:
    """``[(order id, P, w, v)]`` of an instance, in order-list order."""
    return [(o.id, float(o.P), float(o.w), float(o.v)) for o in inst.orders]


def uniform_order_prices(inst: Any) -> Optional[Dict[str, float]]:
    """``{'P', 'w', 'v'}`` when every order has the same prices, else ``None`` (also for an
    instance without orders)."""
    vals = {(p, w, v) for _i, p, w, v in order_prices(inst)}
    if len(vals) != 1:
        return None
    p, w, v = next(iter(vals))
    return {"P": p, "w": w, "v": v}


def order_price_signature(inst: Any) -> str:
    """MD5 of :func:`order_prices` (ids and the three prices of every order)."""
    import hashlib
    txt = json.dumps([[str(i), p, w, v] for i, p, w, v in order_prices(inst)])
    return hashlib.md5(txt.encode("utf-8")).hexdigest()


def pricing_cache_component(inst: Any) -> Optional[str]:
    """Price component of a result-cache key (``bilevel.LowerLevelEvaluator``): ``None`` for an
    instance priced as generated (no ``meta['pricing']`` and the order prices equal the
    ``meta['costs']`` P / w / v when those are recorded) -- so that the cache keys of earlier
    rounds are unchanged -- else :func:`order_price_signature`.  Results computed under other
    order prices are therefore never returned from a cache."""
    meta = getattr(inst, "meta", None) or {}
    if meta.get("pricing"):
        return order_price_signature(inst)
    rec = meta.get("costs") or {}
    if all(k in rec for k in PRICE_KEYS):
        want = (float(rec["P"]), float(rec["w"]), float(rec["v"]))
        if any((p, w, v) != want for _i, p, w, v in order_prices(inst)):
            return order_price_signature(inst)
    return None


def pricing_label(P: float, w: float, v: float) -> str:
    """Short label of a uniform pricing, e.g. ``'P60_w18_v15'``."""
    return f"P{float(P):g}_w{float(w):g}_v{float(v):g}"


def _update_price_records(obj: Any, new: Dict[str, float], key: Optional[str] = None) -> int:
    """Recursively set the keys of ``new`` in every meta dict that records order prices: the
    dicts stored under a key ``'costs'`` or ``'demand_spec'`` (generator ``meta['costs']``,
    ``meta['params']['demand_spec']``, ``data_nyc``'s ``meta['cost_variant_params']
    ['demand_spec']``); only keys already present are replaced.  Returns the number of
    replaced entries."""
    n = 0
    if isinstance(obj, dict):
        if key in ("costs", "demand_spec"):
            for k, val in new.items():
                if k in obj:
                    obj[k] = float(val)
                    n += 1
        for k, val in obj.items():
            if isinstance(val, (dict, list)):
                n += _update_price_records(val, new, str(k))
    elif isinstance(obj, list):
        for val in obj:
            if isinstance(val, dict):
                n += _update_price_records(val, new, None)
    return n


def reprice_orders(inst: Any, P: Optional[float] = None, w: Optional[float] = None,
                   v: Optional[float] = None, source: Optional[str] = None) -> Any:
    """Copy of ``inst`` with every order's ``P`` / ``w`` / ``v`` replaced (round 6; data only,
    E2 (30)-(31) unchanged).  ``None`` keeps a price.

    The copy's meta is updated: every recorded price (``meta['costs']`` and any
    ``demand_spec`` dict, see :func:`_update_price_records`), ``meta['cost_variant']``
    (``usd_r6`` / ``usd_sunk`` when the copy of a price-only variant now matches one of them
    exactly, else ``'<generated variant>@P.._w.._v..'``; the generated variant is kept in
    ``meta['cost_variant_generated']``) and ``meta['pricing'] = {'P', 'w', 'v', 'source',
    'label', 'changed', 'previous', 'library_rebuild_required'}`` (``P`` / ``w`` / ``v`` are
    ``None`` when the orders are not uniformly priced; ``previous`` = the prices of the
    instance as generated).

    IMPORTANT: ``theta`` (31) is stored on the arcs at build time, so when ``w`` or ``v``
    changes (``meta['pricing']['library_rebuild_required']``) an arc library of the original
    instance is stale: build a new one on the returned copy and check it with
    :func:`check_lib_prices` (``ilp.build_model`` runs the same check and raises
    :class:`PricingMismatchError`).  A change of ``P`` alone keeps every library valid
    (``P_i`` enters (30) through ``u_i`` only), although ``ilp`` / ``baseline`` insist on
    ``lib.inst == inst``, so re-bind or rebuild it anyway.  Raises ``ValueError`` for a
    negative or non-finite price."""
    import math
    new: Dict[str, float] = {}
    for k, val in (("P", P), ("w", w), ("v", v)):
        if val is None:
            continue
        f = float(val)
        if not math.isfinite(f) or f < 0:
            raise ValueError(f"price {k} must be finite and >= 0 (got {val!r})")
        new[k] = f
    before = uniform_order_prices(inst)
    out = copy.deepcopy(inst)
    theta_changed = False
    for o in out.orders:
        for k, f in new.items():
            if k in ("w", "v") and float(getattr(o, k)) != f:
                theta_changed = True
            setattr(o, k, f)
    out.reindex()
    meta = out.meta
    _update_price_records(meta, new)
    after = uniform_order_prices(out)
    old_variant = meta.get("cost_variant")
    if old_variant is not None:
        gen_variant = meta.setdefault("cost_variant_generated", old_variant)
        label = None
        if after is not None and gen_variant in _PRICE_ONLY_VARIANTS:
            for name, ref in _PRICE_ONLY_VARIANTS.items():
                if all(ref[k] == after[k] for k in PRICE_KEYS):
                    label = name
                    break
        if label is None:
            label = f"{gen_variant}@" + (pricing_label(**after) if after is not None else "mixed")
        meta["cost_variant"] = label
    old = meta.get("pricing") or {}
    meta["pricing"] = {
        "P": None if after is None else after["P"],
        "w": None if after is None else after["w"],
        "v": None if after is None else after["v"],
        "source": source or "costs.reprice_orders",
        "label": None if after is None else pricing_label(**after),
        "changed": sorted(new),
        "previous": old.get("previous", before) if old else before,
        "library_rebuild_required": bool(theta_changed),
    }
    return out


def check_lib_prices(inst: Any, lib: Any, per_order: int = 3, rel_tol: float = 1e-9,
                     raise_on_error: bool = True) -> Dict[str, Any]:
    """Verify that the delivery arcs of ``lib`` carry ``theta = Instance.theta(i, u_a)`` (31)
    under the CURRENT order prices of ``inst`` (round 6: a library built before a change of
    ``w`` / ``v`` is stale).  Checks ``per_order`` arcs of every order (first, last and evenly
    spaced ones; all of them when fewer), so the cost is O(|I|) whatever the library size.

    Returns ``{'ok', 'n_checked', 'n_orders', 'max_abs_diff', 'examples'}``; raises
    :class:`PricingMismatchError` on a mismatch when ``raise_on_error``."""
    deliv = getattr(lib, "_deliv", None)
    if deliv is None:                                   # foreign library object: scan the arcs
        deliv = {}
        for a in getattr(lib, "arcs", []):
            if a.kind == "deliver":
                deliv.setdefault(a.order, []).append(a.id)
    n_checked = 0
    max_diff = 0.0
    bad: List[Dict[str, Any]] = []
    order_ids = {o.id for o in inst.orders}
    per_order = max(1, int(per_order))
    for i, ids in deliv.items():
        if not ids:
            continue
        if i not in order_ids:
            bad.append({"order": i, "issue": "delivery arcs of an order unknown to the instance"})
            continue
        m = len(ids)
        if m <= per_order:
            pick = list(range(m))
        elif per_order == 1:
            pick = [0]
        else:
            pick = sorted({int(round(j * (m - 1) / (per_order - 1))) for j in range(per_order)})
        for j in pick:
            a = lib.arcs[ids[j]]
            want = float(inst.theta(i, a.u))
            diff = abs(float(a.theta) - want)
            n_checked += 1
            max_diff = max(max_diff, diff)
            if diff > rel_tol * max(1.0, abs(want)):
                bad.append({"order": i, "arc": a.id, "u": a.u, "theta_lib": float(a.theta), "theta_inst": want})
    res = {"ok": not bad, "n_checked": n_checked, "n_orders": len(deliv), "max_abs_diff": max_diff,
           "examples": bad[:5]}
    if bad and raise_on_error:
        raise PricingMismatchError(
            f"arc library theta (31) disagrees with the instance order prices on {len(bad)} checked arc(s), "
            f"e.g. {bad[:3]}: the library was built under other w / v -- rebuild it (build_arcs) on the "
            "repriced instance")
    return res
