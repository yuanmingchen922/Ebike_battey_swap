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
