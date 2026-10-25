from dataclasses import dataclass, field


@dataclass
class SimConfig:
    # --- horizon ---
    horizon_min: float = 24 * 60          # simulate one day (minutes)
    weekday: bool = True
    seed: int = 0

    # --- synthetic network ---
    grid_nx: int = 30
    grid_ny: int = 30
    block_m: float = 150.0                # block length (m)
    traffic_light_prob: float = 0.5       # fraction of intersections with a signal
    n_zones_side: int = 5                 # zones = n x n regions of the grid

    # --- demand ---
    base_orders_per_hour: float = 300.0   # city-wide peak-normalised base rate
    n_restaurants: int = 250

    # --- riders ---
    n_riders: int = 120
    speed_m_per_min: float = 250.0        # ~15 km/h
    battery_capacity_wh: float = 600.0
    wh_per_km: float = 12.0
    wh_per_m_climb: float = 0.6           # extra energy per metre of ascent
    wh_per_light: float = 0.4             # stop-and-go penalty per signalised node
    swap_threshold_frac: float = 0.25     # go swap when battery below this fraction
    pickup_service_min: float = 3.0       # waiting at restaurant
    dropoff_service_min: float = 1.5

    # --- stations ---
    n_stations: int = 12
    batteries_per_station: int = 12
    # NOTE: E2 (19) fixes the per-charger power as p_ch = eps / (eta * Delta); the
    # generator derives charger power from Discretisation.p_ch_kw (0.667 kW for
    # L=12, eps=50 Wh, eta=0.9, Delta=5 min) and ignores this legacy value, which
    # only matches (19) for L=8 / eps=75 Wh.
    charger_kw: float = 1.0               # legacy simulator charge rate per battery (kW)
    swap_service_min: float = 2.0

    # --- initial rider battery state ---
    init_battery_min_frac: float = 0.4
    init_battery_max_frac: float = 1.0

    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Round 5 (notes/reading_to_model.md): named physical energy calibrations
# ---------------------------------------------------------------------------
#: Named energy calibrations for the E2 route energy (1)-(3) and the battery grid
#: (``L``, ``eps``; p_ch of (19) follows as ``eps / (eta Delta)``).  Plan item **A1**.
#:
#: * ``legacy`` -- the calibration of every round-1..4 family (12 Wh/km plus climb and
#:   signal terms, 50 Wh levels, 12 levels, per-leg rounding as written in (1)-(3)).
#:   Listed for documentation only: the generator does NOT route old families through
#:   this table, so their JSON stays byte-identical.
#: * ``ebaas`` -- eBaaS (Ding et al., WWW 2025): delivery e-bikes ride "40 kilometers per
#:   degree of electricity" (40 km/kWh = 25 Wh/km, Sec. 4.2 CO2 estimate); the linear
#:   coefficient range model of Table 1(a) supports a per-km linear energy model; the
#:   whole swap takes "less than 10 seconds" (Fig. 1 / Sec. 1), so sigma_j = 1 slot of
#:   5 min (which then covers access and queueing).  Combined with the de-rounding B5 of
#:   the formulation review: eps = 25 Wh, L = 24 (same 0.6 kWh pack), ``energy_rounding =
#:   'concat'`` (g_a = ceil((E_r + E_r') / eps) on the concatenated delivery).  The 25 Wh/km
#:   is a fleet average over real urban rides, so it already contains stop-and-go losses:
#:   ``wh_per_light = 0`` (no separate signal term); the synthetic climb term (0.6 Wh/m)
#:   is kept because the grid elevation is synthetic and small.  The terminal reserve
#:   q_res is kept physical (50 Wh = one legacy level -> 2 levels of 25 Wh).
ENERGY_CALIBRATIONS = {
    "legacy": {
        "wh_per_km": 12.0, "wh_per_m_climb": 0.6, "wh_per_light": 0.4,
        "eps_wh": 50.0, "pack_kwh": 0.6, "energy_rounding": "per_leg", "q_res_wh": 50.0,
        "sigma_slots": 1,
        "source": "rounds 1-4 (config.py SimConfig; DECISIONS 'Default discretisation')",
    },
    "ebaas": {
        "wh_per_km": 25.0, "wh_per_m_climb": 0.6, "wh_per_light": 0.0,
        "eps_wh": 25.0, "pack_kwh": 0.6, "energy_rounding": "concat", "q_res_wh": 50.0,
        "sigma_slots": 1,
        "source": "eBaaS (Ding et al., WWW 2025): 40 km/kWh (Sec. 4.2), linear range model "
                  "(Table 1a), swap < 10 s (Fig. 1); de-rounding B5 (eps 25 Wh, L 24, concat); "
                  "plan item A1 of notes/reading_to_model.md",
    },
}

#: Facts of the eBaaS deployment used to ground the round-5 stressed families (plan item
#: M5) and the value-of-network counterfactual (A5).  Quoted from Ding et al., WWW 2025.
EBAAS_FACTS = {
    "km_per_rider_day": 120.0,          # Sec. 1-2: "riders travel an average of around 120 kilometers daily"
    "operating_hours": (8.0, 22.0),     # Sec. 4.1: records between 8:00 am and 10:00 pm
    "meal_peaks": ((10.0, 13.0), (17.0, 18.0)),   # Sec. 4.2: peak hours 10:00-13:00, 17:00-18:00
    "km_per_kwh": 40.0,                 # Sec. 4.2: 40 km per kWh
    "swap_seconds_max": 10.0,           # Fig. 1: swapping takes less than 10 seconds
    "cabinet_radius_km": 2.0,           # Sec. 4.2: cabinet coverage radius 2 km
    "invalid_km_saved_per_rider_day": 6.2,   # Sec. 4.2 (EIEM)
    "orders_gain_share": 0.20,          # abstract: order volume +20 % per rider and day
}

#: Home-charging counterfactual of plan item A5 (eBaaS EIEM: "ride home to charge").
#: ``charger_kw`` = 0.24 kW input power, the 48 V / 5 A e-bike charger of the cost
#: calibration (notes/data/cost_calibration_usd.json, b^C_j derivation); ``return_frac``
#: = typical level at which a rider goes home (the baseline swap threshold 0.25).
HOME_CHARGING_DEFAULTS = {"charger_kw": 0.24, "return_frac": 0.25}


def energy_calibration(name="ebaas", Delta_h=5.0 / 60.0, eta=0.9, **overrides):
    """Resolve a named energy calibration of :data:`ENERGY_CALIBRATIONS` (plan item A1;
    E2 (1)-(3) route energy, (19) p_ch).

    ``overrides`` replace entries of the table (e.g. ``pack_kwh=1.0`` or ``eps_wh=50``
    for the A6 pack sweep and the M10(c) charger-speed sensitivity).  Returns a new dict
    with the table entries plus the derived ``L = pack_kwh * 1000 / eps_wh`` (must be an
    integer within 1e-9), ``battery_wh = L * eps_wh``, ``eps_kwh``, ``q_res`` =
    ``ceil(q_res_wh / eps_wh)`` levels, ``p_ch_kw = eps / (eta Delta)`` (19) and ``name``.
    Raises ``KeyError`` for an unknown name and ``ValueError`` when the pack is not an
    integer number of levels."""
    import math as _math
    if name not in ENERGY_CALIBRATIONS:
        raise KeyError(f"unknown energy calibration {name!r}; known: {sorted(ENERGY_CALIBRATIONS)}")
    cal = dict(ENERGY_CALIBRATIONS[name])
    unknown = set(overrides) - set(cal)
    if unknown:
        raise KeyError(f"unknown energy calibration keys {sorted(unknown)}")
    cal.update(overrides)
    eps_wh = float(cal["eps_wh"])
    pack_wh = float(cal["pack_kwh"]) * 1000.0
    if eps_wh <= 0 or pack_wh <= 0:
        raise ValueError("eps_wh and pack_kwh must be positive")
    L_float = pack_wh / eps_wh
    L = int(round(L_float))
    if L < 1 or abs(L - L_float) > 1e-9:
        raise ValueError(f"pack {pack_wh} Wh is not an integer number of {eps_wh} Wh levels")
    cal.update({
        "name": name, "L": L, "battery_wh": L * eps_wh, "eps_kwh": eps_wh / 1000.0,
        "q_res": int(_math.ceil(float(cal["q_res_wh"]) / eps_wh - 1e-9)),
        "p_ch_kw": (eps_wh / 1000.0) / (float(eta) * float(Delta_h)),
    })
    return cal
