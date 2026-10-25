"""A7 online learned comparator (``notes/reading_to_model.md`` item A7, IJCAI-25 Sec. 4.1):
a gymnasium environment that controls ONLY the station layer of the E2 model on top
of the event-driven rider policy of :mod:`ebike_swap_sim.baseline`.

What the agent decides (per slot ``t``, after the riders have acted at boundary ``t``)
----------------------------------------------------------------------------------
* ``c_jqt`` (20)-(21): for every charge-capable facility ``j in C`` the NUMBER of
  batteries to charge in slot ``t``, bounded by ``cap_j = min(C_j, floor(P_j y_j / p_ch))``
  (20); the batteries are taken HIGH_FIRST (most advanced first) from the stock left
  after this boundary's swaps and departures (14) and the supply-group limit (21) is
  applied in facility order, exactly as in ``baseline._step9_charging``.
* ``h_e, z_eq`` (10)-(11): for every service ``e`` departing at ``l_e = t`` the NUMBER
  of batteries to load, bounded by ``U_e`` (10), the origin stock (14) and the free
  storage at the destination at arrival (15); towards a swap site the fullest
  batteries go first, towards a charge-only hub the emptiest go first (the level
  rule of the REORDER_POINT baseline).  The service entry of the action is ignored
  in slots where the service does not depart.

Everything else (order release, dispatch, swap trips, FIFO swap service, the
terminal certificate (9)) is the baseline rider policy (``baseline.BASELINE_VARIANTS``
variant, default ``'default'`` = DECISIONS R2.3 rules, alias ``'r2'``), executed through
``ArcLibrary.find`` only, so the agent can never take an action the ILP does not have.
The E2 equations are untouched: this module is a policy wrapper (A7 is a "policy /
wrapper" item of the plan).

State (observation, ``float32`` vector)
---------------------------------------
Per facility ``j`` (instance order): stock by level ``n_jqt / K_j`` (``q = 0..L``),
swaps at ``j`` issued at the boundaries ``(t - lookback, t]`` and at ``t`` itself (``S_jt`` of (12),
normalised), FIFO swap-queue length / ``|K|``, batteries in transit to ``j`` (full and
non-full, (11)/(24)) / ``K_j``.  Global: ``t / H``, time of day ``(sin, cos)`` of the
wall-clock hour (``meta['window_h'][0] + t Delta``), released unassigned orders /
``|K|``, share of bikes at or below the swap threshold, mean bike level / ``L``,
batteries in transit ``m_t`` (24) / ``sum_j B_j``.  Per service: departs-now flag and
slots until departure / ``H`` (clipped to ``[-1, 1]``).

Reward (negative incremental E2 cost)
-------------------------------------
Let ``Phi_t`` be :func:`ebike_swap_sim.evaluate.cost` ``['total']`` (26) of the partial
schedule observed at boundary ``t`` (arcs committed so far (29)-(31), ``c`` (28) and
``h, z`` (32) issued so far, setup (27), and -- with ``provisional_unserved`` -- the
unserved penalty ``P_i u_i`` (30) of every released order still unassigned).  The
reward of the step ``t -> t+1`` is ``-(Phi_{t+1} - Phi_t) * reward_scale``; at the
last step ``Phi_H`` is the cost of the finished schedule plus the M1 end-state
adjustment (:func:`end_state_adjustment`).  The rewards telescope: the episode return
equals ``-(J + adj - Phi_0) * reward_scale`` where ``J`` is ``evaluate.cost(...)['total']``
of the final schedule and ``Phi_0`` the (uncontrollable) cost already committed by the
riders at ``t = 0``.

Episodes are one window (``H`` slots) of one instance; instances come from a factory
(:func:`make_family_factory`: a family of ``experiments.common.FAMILIES`` and a seed
list -- random training seeds, held-out test seeds) or an explicit instance list.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

try:  # gymnasium is an optional dependency of the package (A7 only)
    import gymnasium as gym
    from gymnasium import spaces
except ImportError as _exc:  # pragma: no cover - exercised only without gymnasium
    raise ImportError("ebike_swap_sim.rl_env needs gymnasium (pip install gymnasium)") from _exc

from . import baseline as bl
from .arcs import ArcLibrary, build_arcs
from .evaluate import Schedule, cost as e2_cost
from .or_instance import Instance

_FLOOR_TOL = 1e-9

#: Aliases of rider-policy names used in the A7 plan text: ``'r2'`` = the round-2
#: DECISIONS R2.3 rules (``baseline.BASELINE_VARIANTS['default']``).  ``'r5'`` maps to a
#: round-5 variant only when ``baseline.BASELINE_VARIANTS`` defines one (key ``'r5'``).
RIDER_ALIASES: Dict[str, str] = {"r2": "default", "R2.3": "default"}

InstanceLike = Union[Instance, Tuple[Instance, ArcLibrary]]
Factory = Callable[[int], Tuple[Instance, ArcLibrary]]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def resolve_rider_variant(name: str) -> str:
    """Name of the ``baseline.BASELINE_VARIANTS`` entry used as the rider layer (A7).

    ``'r2'`` -> ``'default'`` (DECISIONS R2.3); any key of ``BASELINE_VARIANTS`` is
    accepted as is (so a round-5 ``'r5'`` variant is picked up once ``baseline.py``
    defines it).  Raises ``KeyError`` for unknown names."""
    key = RIDER_ALIASES.get(name, name)
    if key not in bl.BASELINE_VARIANTS:
        raise KeyError(f"unknown rider variant {name!r}; known: "
                       f"{sorted(set(bl.BASELINE_VARIANTS) | set(RIDER_ALIASES))}")
    return key


def rider_params(inst: Instance, variant: str = "r2", **overrides: Any) -> bl.BaselineParams:
    """``BaselineParams`` of the rider layer (A7) on ``inst``.

    The named variant (:func:`resolve_rider_variant`) updated by ``overrides``.  On a
    ``relax_end_targets`` copy (``meta['relax_end_targets']``) the DEMAND_AWARE reserve is
    the WRITTEN ``R_end_j`` (as ``experiments.common.run_baseline_case`` does, fairness
    review F1), so the station rule of the baseline -- used by ``station_policy=
    'baseline'`` and by :func:`heuristic_action` -- is the same policy under both
    end-target settings (E2 (17))."""
    params = bl.baseline_variant_params(resolve_rider_variant(variant), **overrides)
    p = bl.BaselineParams.coerce(params)
    written = inst.meta.get("written_R_end") if inst.meta.get("relax_end_targets") else None
    if written and p.charge_reserve is None:
        import dataclasses
        p = dataclasses.replace(p, charge_reserve={j: int(v) for j, v in written.items()})
    return p


def charge_cap(inst: Instance, j: Any, y: int, C: int) -> int:
    """Per-slot charging bound of site ``j`` (A7 action bound): ``min(C_j, floor(P_j y_j / p_ch))``
    -- the site rows of (20) for a fixed ``(y_j, C_j)``; 0 off ``C`` or when closed."""
    f = inst.facility(j)
    if not f.charge or y != 1:
        return 0
    p_ch = inst.disc.p_ch_kw
    return max(0, min(int(C), int(math.floor(f.P_kw * y / p_ch + _FLOOR_TOL))))


def end_state_adjustment(inst: Instance, n_end: Dict[Any, Sequence[int]],
                         bike_end_levels: Dict[Any, int]) -> Dict[str, float]:
    """M1 end-state adjustment (``reading_to_model.md`` M1), applied identically to every
    method compared in A7: ``pi (eps / eta) [sum_j sum_q (L - q) n_jqH + sum_k (q0_k - q_k(H))^+]``,
    i.e. the energy that would have to be bought to bring the station stock back to full
    and the fleet back to its start levels, priced with the electricity term of (28).

    ``n_end[j]`` is the list ``n_jqH`` (``q = 0..L``), ``bike_end_levels[k]`` the level at
    ``H``.  The price is ``evaluate.end_reference_price(inst)`` (``meta['end_price']`` if
    set, else the mean of ``pi_jt`` over ``C x T``), the same reference price as
    ``evaluate.end_state_adjustment`` so that A7 and the E2 tables use one M1 convention.
    Returns ``{'station', 'fleet', 'total', 'price'}`` (USD or the instance's units).  This
    is a reporting term, not part of E2 (26)."""
    from .evaluate import end_reference_price
    L = inst.L
    price = end_reference_price(inst)
    kwh = inst.disc.kwh_per_step
    station_steps = sum((L - q) * int(row[q]) for row in n_end.values() for q in range(L + 1))
    fleet_steps = sum(max(0, int(b.q0) - int(bike_end_levels.get(b.id, b.q0))) for b in inst.bikes)
    station = price * kwh * station_steps
    fleet = price * kwh * fleet_steps
    return {"station": station, "fleet": fleet, "total": station + fleet, "price": price,
            "station_steps": float(station_steps), "fleet_steps": float(fleet_steps)}


def bike_end_levels(inst: Instance, lib: ArcLibrary, sched: Schedule) -> Dict[Any, int]:
    """Level ``q_k(H)`` of every bike in a finished schedule (head of its last non-terminal arc)."""
    out: Dict[Any, int] = {}
    for b in inst.bikes:
        q = b.q0
        best_u = -1
        for aid in sched.x.get(b.id, ()):
            a = lib.arc(aid)
            if a.kind != "term" and a.u >= best_u:
                best_u, q = a.u, a.dst[2]
        out[b.id] = int(q)
    return out


def schedule_end_stock(inst: Instance, sched: Schedule) -> Dict[Any, List[int]]:
    """``n_jqH`` per facility from ``Schedule.n`` (missing entries = 0)."""
    n = sched.n or {}
    return {f.id: [int(n.get((f.id, q, inst.H), 0)) for q in range(inst.L + 1)] for f in inst.facilities}


def adjusted_cost(inst: Instance, lib: ArcLibrary, sched: Schedule) -> Dict[str, Any]:
    """``evaluate.cost`` (26)-(32) of ``sched`` plus the M1 end-state adjustment
    (:func:`end_state_adjustment`); the comparison metric of A7.  When ``sched.n`` is
    ``None`` the stock is reconstructed with ``evaluate.reconstruct_inventory`` (13)."""
    from .evaluate import reconstruct_inventory
    if sched.n is None:
        sched = Schedule(**{**sched.__dict__})
        sched.n = reconstruct_inventory(inst, lib, sched.x, sched.c, sched.z, sched.B)
    c = e2_cost(inst, lib, sched)
    adj = end_state_adjustment(inst, schedule_end_stock(inst, sched), bike_end_levels(inst, lib, sched))
    return {"cost": c, "E2_total": c["total"], "end_adj": adj["total"], "end_adj_parts": adj,
            "adjusted_total": c["total"] + adj["total"]}


# ---------------------------------------------------------------------------
# a stepped baseline run with an exposed station layer
# ---------------------------------------------------------------------------
class _StationRun(bl._BaselineRun):  # noqa: SLF001 - deliberate reuse of the rider rules
    """The baseline simulation (``baseline._BaselineRun``) stepped slot by slot with the
    station layer (steps 8-9) replaced by external decisions (A7).

    The slot loop below mirrors ``_BaselineRun.run`` exactly (steps 1-7, 8-9, 10, then
    11-14); ``tests/test_rl_env.py`` asserts parity with ``baseline.run_baseline`` so any
    change of the loop in ``baseline.py`` is detected."""

    def begin(self) -> None:
        orders_sorted = sorted(self.inst.orders, key=lambda o: (o.r, self.oidx[o.id]))
        self._release_at: Dict[int, List[Any]] = {}
        for o in orders_sorted:
            self._release_at.setdefault(o.r, []).append(o.id)
        self.t = 0
        self.riders(0)

    def riders(self, t: int) -> None:
        """Steps 1-7 of the baseline at boundary ``t`` (stock record, releases, threshold
        rule, FCFS swaps (12)/(22), dispatch, idle bikes)."""
        self._record_stock(t)
        self.Q.extend(self._release_at.get(t, ()))
        idle = [k for k in self.bikes if self.bikes[k].free_at == t]
        idle = self._step4_threshold(idle, t)
        idle = self._step5_fcfs_swaps(idle, t)
        idle = self._step6_dispatch(idle, t)
        self._step7_remaining(idle, t)

    def station_baseline(self, t: int) -> None:
        """Steps 8-9 of the baseline itself (forced M9 transfers, transfer rule, charging rule)."""
        if self.forced:
            self._step8_forced(t)
        if self.transfer_rule != "NONE":
            self._step8_transfers(t)
        self._step9_charging(t)

    def station_external(self, t: int, charge: Dict[Any, int], loads: Dict[Any, int]) -> Dict[str, Any]:
        """Apply external station decisions at boundary ``t``: service loads first (step 8
        order, (10), (11), (14), (15)), then charging (step 9 order, (14), (20), (21)).
        Returns the amounts actually applied (after clipping)."""
        L = self.L
        applied_loads: Dict[Any, int] = {}
        if self.forced:                       # M9 lock-out: data, not an agent decision
            self._step8_forced(t)
        if not self.inst.option("no_transfers"):
            for svc in self.inst.services:
                want = int(loads.get(svc.id, 0))
                if svc.l != t or want <= 0 or svc.id in self.forced:
                    continue
                o_fac, d_fac = svc.o_fac, svc.d_fac
                if self.y[o_fac] != 1 or self.y[d_fac] != 1:
                    continue
                fd = self.inst.facility(d_fac)
                room = fd.K * self.y[d_fac] - self._stock_total(d_fac) - self._inbound(d_fac, t)
                left = min(want, int(svc.U), room)
                if left <= 0:
                    continue
                order = range(L, -1, -1) if fd.swap else range(L + 1)
                lo: Dict[int, int] = {}
                for q in order:
                    if left <= 0:
                        break
                    # full batteries reserved by bikes (M2 reservations) never leave
                    have = self._avail_full(o_fac) if q == L else self.n[o_fac][q]
                    zq = min(have, left)
                    if zq >= 1:
                        lo[q] = zq
                        left -= zq
                if not lo:
                    continue
                self.h[svc.id] = 1
                for q, val in lo.items():
                    self.z[(svc.id, q)] = self.z.get((svc.id, q), 0) + val
                    self.D[(o_fac, q, t)] += val
                    self.A[(d_fac, q, svc.u)] += val
                    self.n[o_fac][q] -= val
                    self.pending_arrivals[d_fac].append((svc.u, q, val))
                applied_loads[svc.id] = sum(lo.values())
        applied_charge: Dict[Any, int] = {}
        group_left: Dict[Any, int] = {}
        p_ch = self.inst.disc.p_ch_kw
        for j in self.open_charge:
            f = self.inst.facility(j)
            budget = min(int(charge.get(j, 0)), charge_cap(self.inst, j, self.y[j], self.C[j]))
            if f.group is not None and f.group not in group_left:
                lim = self.inst.grid_limit(f.group, t)
                group_left[f.group] = (10 ** 9 if lim == math.inf
                                       else int(math.floor(lim / p_ch + _FLOOR_TOL)))
            charged = 0
            for q in range(L - 1, -1, -1):
                if budget <= 0:
                    break
                lim_g = group_left[f.group] if f.group is not None else 10 ** 9
                cq = min(self.n[j][q], budget, lim_g)
                if cq <= 0:
                    continue
                self.c[(j, q, t)] = cq
                budget -= cq
                charged += cq
                if f.group is not None:
                    group_left[f.group] -= cq
            applied_charge[j] = charged
        return {"charge": applied_charge, "loads": applied_loads}

    def end_slot(self, t: int) -> None:
        """Step 10: inventory balance (13) to ``t + 1``."""
        self._step10_inventory_step(t)

    def finish(self) -> Tuple[Schedule, Dict[str, Any]]:
        """Stock record at ``H`` and steps 11-14 (terminal arcs (9), end targets, Schedule)."""
        self._record_stock(self.H)
        return self._finish()

    def partial_schedule(self, provisional_unserved: bool = True) -> Schedule:
        """Schedule of everything committed so far (A7 reward potential): bike arcs, ``c``,
        ``h``, ``z``; ``u_i = 1`` for released, unassigned orders when
        ``provisional_unserved`` (else no ``u``)."""
        u = {i: 1 for i in self.Q} if provisional_unserved else {}
        return Schedule(x={k: list(bs.path) for k, bs in self.bikes.items()}, u=u,
                        c=dict(self.c), h=dict(self.h), z=dict(self.z),
                        y=dict(self.y), B=dict(self.B), C=dict(self.C), n=None)


# ---------------------------------------------------------------------------
# instance factories
# ---------------------------------------------------------------------------
def make_family_factory(family: str, relax_targets: bool = True,
                        pruning_overrides: Optional[Dict[str, Any]] = None,
                        **family_overrides: Any) -> Factory:
    """Factory ``seed -> (Instance, ArcLibrary)`` for an ``experiments.common.FAMILIES``
    family (A7 episodes: random training seeds, held-out test seeds).

    ``relax_targets`` (default, the M1 headline control) applies
    ``experiments.common.relax_end_targets`` (``rho = R_end_j = 0`` in (17)-(18)); the
    library is built with ``experiments.common.pruning_for`` (the same pruning as the
    ILP of the family).  Needs the ``experiments`` package on ``sys.path`` (run from
    ``ebike_swap_sim/`` with ``PYTHONPATH=.``)."""
    from experiments import common as C  # lazy: the package itself does not depend on experiments

    def factory(seed: int) -> Tuple[Instance, ArcLibrary]:
        inst = C.make_instance(family, int(seed), **family_overrides)
        if relax_targets:
            inst = C.relax_end_targets(inst)
        lib, _ = C.build_library(inst, C.pruning_for(inst, **(pruning_overrides or {})))
        return inst, lib

    factory.family = family  # type: ignore[attr-defined]
    return factory


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------
@dataclass
class EnvConfig:
    """Configuration of :class:`StationEnv` (A7).

    Attributes
    ----------
    rider_variant : str
        Rider policy (``baseline.BASELINE_VARIANTS`` key or alias, default ``'r2'``).
    rider_overrides : dict
        ``BaselineParams`` overrides of the rider layer.
    station_policy : ``'agent'`` | ``'baseline'``
        ``'agent'``: the action drives steps 8-9.  ``'baseline'``: the action is ignored and
        the baseline's own transfer / charging rules run (replay; parity check and the
        zero-learning comparator inside the environment).
    reward_scale : float
        Multiplier of the negative cost increment.
    provisional_unserved : bool
        Count ``P_i`` (30) for released, unassigned orders in the potential ``Phi_t``.
    end_state : ``'m1'`` | ``'none'``
        Add the M1 end-state adjustment to ``Phi_H``.
    shortfall_penalty : float
        Extra cost per battery of (17) / (18) shortfall at ``H`` (0 by default; with
        ``relax_targets`` the targets are 0 anyway).
    lookback : int
        Window of the recent-swap feature (slots).
    episodes_per_instance : int
        Consecutive episodes on one instance before the next one is drawn (amortises the
        arc-library build).
    cache_size : int
        Instances (with their libraries) kept in memory.
    seeds : sequence of int
        Seeds passed to the factory (training seeds by default; test seeds for evaluation).
    shuffle : bool
        Draw the next seed at random (``np_random``) instead of cycling.
    """
    rider_variant: str = "r2"
    rider_overrides: Dict[str, Any] = field(default_factory=dict)
    station_policy: str = "agent"
    reward_scale: float = 0.1
    provisional_unserved: bool = True
    end_state: str = "m1"
    shortfall_penalty: float = 0.0
    lookback: int = 12
    episodes_per_instance: int = 8
    cache_size: int = 2
    seeds: Sequence[int] = tuple(range(1000, 1064))
    shuffle: bool = True

    def validate(self) -> None:
        if self.station_policy not in ("agent", "baseline"):
            raise ValueError("station_policy must be 'agent' or 'baseline'")
        if self.end_state not in ("m1", "none"):
            raise ValueError("end_state must be 'm1' or 'none'")
        if self.lookback < 1 or self.episodes_per_instance < 1 or self.cache_size < 1:
            raise ValueError("lookback, episodes_per_instance and cache_size must be >= 1")
        if not len(self.seeds):
            raise ValueError("seeds must be non-empty")
        resolve_rider_variant(self.rider_variant)


# ---------------------------------------------------------------------------
# the environment
# ---------------------------------------------------------------------------
class StationEnv(gym.Env):
    """Gymnasium environment of the A7 RL comparator (station layer only, see module doc).

    Parameters
    ----------
    factory : callable ``seed -> (Instance, ArcLibrary)``, optional
        Instance source (:func:`make_family_factory`).
    instances : list of ``Instance`` or ``(Instance, ArcLibrary)``, optional
        Explicit instance pool instead of a factory (libraries are built unpruned when
        missing); ``config.seeds`` then indexes this list.
    config : :class:`EnvConfig` or dict, optional.

    ``reset(options={'seed': s})`` forces the instance of seed ``s`` (or list index for
    an explicit pool).  ``info`` of the terminal step holds ``schedule``, ``cost``
    ((26)-(32)), ``end_adj`` (M1), ``adjusted_total``, ``episode_cost`` (= E2 total),
    ``flags`` (baseline flags (9)/(17)/(18)) and ``phi0``.

    All instances of one environment must share the station layout shape (facility
    ids, service ids, ``L``); the action bounds are the maxima over the first instance
    loaded (template) and are clipped per instance to (10), (20).
    """

    metadata = {"render_modes": []}

    def __init__(self, factory: Optional[Factory] = None,
                 instances: Optional[Sequence[InstanceLike]] = None,
                 config: Union[EnvConfig, Dict[str, Any], None] = None) -> None:
        super().__init__()
        if config is None:
            config = EnvConfig()
        elif isinstance(config, dict):
            config = EnvConfig(**config)
        self.cfg = config
        if instances is not None:
            pool = []
            for it in instances:
                if isinstance(it, tuple):
                    pool.append(it)
                else:
                    pool.append((it, build_arcs(it)))
            self._pool = pool
            if tuple(self.cfg.seeds) == tuple(EnvConfig().seeds):
                self.cfg.seeds = tuple(range(len(pool)))
            self._factory: Factory = lambda s: self._pool[int(s)]
        elif factory is not None:
            self._factory = factory
            self._pool = None
        else:
            raise ValueError("StationEnv needs a factory or an instance list")
        self.cfg.validate()
        self._cache: "OrderedDict[int, Tuple[Instance, ArcLibrary]]" = OrderedDict()
        self._cursor = 0
        self._episodes_on_current = 0
        self._current_seed: Optional[int] = None
        # template instance fixes the spaces
        tmpl_seed = int(self.cfg.seeds[0])
        inst, _ = self._load(tmpl_seed)
        self._layout = self._layout_of(inst)
        self.fac_ids: List[Any] = [f.id for f in inst.facilities]
        self.charge_ids: List[Any] = [f.id for f in inst.facilities if f.charge]
        self.svc_ids: List[Any] = [e.id for e in inst.services]
        caps = []
        for j in self.charge_ids:
            f = inst.facility(j)
            y = 1 if f.y is None else int(f.y)
            C = int(f.C) if f.C is not None else 0
            caps.append(charge_cap(inst, j, y, C))
        self.charge_caps_template = caps
        self.service_caps_template = [int(inst.service(e).U) for e in self.svc_ids]
        nvec = [c + 1 for c in caps] + [u + 1 for u in self.service_caps_template]
        if not nvec:
            nvec = [1]                        # no station decision at all: a dummy action
        self.action_space = spaces.MultiDiscrete(np.array(nvec, dtype=np.int64))
        self.L = inst.L
        n_obs = len(self.fac_ids) * (self.L + 1 + 2 + 1 + 2) + 8 + 2 * len(self.svc_ids)
        self.observation_space = spaces.Box(low=-1.0, high=np.inf, shape=(n_obs,), dtype=np.float32)
        self.inst: Optional[Instance] = None
        self.lib: Optional[ArcLibrary] = None
        self.run: Optional[_StationRun] = None
        self.phi: float = 0.0
        self.phi0: float = 0.0
        self.last_applied: Dict[str, Any] = {}

    # ------------------------------------------------------------- instances
    @staticmethod
    def _layout_of(inst: Instance) -> Tuple[Any, ...]:
        return (tuple(f.id for f in inst.facilities), tuple(f.charge for f in inst.facilities),
                tuple(e.id for e in inst.services), inst.L)

    def _load(self, seed: int) -> Tuple[Instance, ArcLibrary]:
        if seed in self._cache:
            self._cache.move_to_end(seed)
            return self._cache[seed]
        inst, lib = self._factory(seed)
        if hasattr(self, "_layout") and self._layout_of(inst) != self._layout:
            raise ValueError(f"instance of seed {seed} has a different station layout "
                             f"{self._layout_of(inst)} than the template {self._layout}")
        self._cache[seed] = (inst, lib)
        while len(self._cache) > self.cfg.cache_size:
            self._cache.popitem(last=False)
        return inst, lib

    def _next_seed(self) -> int:
        seeds = list(self.cfg.seeds)
        if self._current_seed is not None and self._episodes_on_current < self.cfg.episodes_per_instance:
            return self._current_seed
        if self.cfg.shuffle:
            s = int(seeds[int(self.np_random.integers(len(seeds)))])
        else:
            s = int(seeds[self._cursor % len(seeds)])
            self._cursor += 1
        self._episodes_on_current = 0
        return s

    # ------------------------------------------------------------- gym API
    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None):
        super().reset(seed=seed)
        options = options or {}
        if "seed" in options:
            s = int(options["seed"])
            self._episodes_on_current = 0
        else:
            s = self._next_seed()
        self._current_seed = s
        self._episodes_on_current += 1
        self.inst, self.lib = self._load(s)
        p = rider_params(self.inst, self.cfg.rider_variant, **self.cfg.rider_overrides)
        self.run = _StationRun(self.inst, self.lib, p)
        self.run.begin()
        self.phi = self._potential()
        self.phi0 = self.phi
        self.last_applied = {}
        return self._obs(), {"instance_seed": s, "phi0": self.phi0, "t": 0}

    def step(self, action: Any):
        if self.run is None:
            raise RuntimeError("call reset() first")
        run, t, H = self.run, self.run.t, self.run.H
        if self.cfg.station_policy == "baseline":
            run.station_baseline(t)
            self.last_applied = {"policy": "baseline"}
        else:
            charge, loads = self.decode_action(action)
            self.last_applied = run.station_external(t, charge, loads)
        run.end_slot(t)
        run.t = t + 1
        info: Dict[str, Any] = {"t": run.t, "instance_seed": self._current_seed,
                                "applied": self.last_applied}
        if run.t < H:
            run.riders(run.t)
            phi_new = self._potential()
            terminated = False
        else:
            sched, flags = run.finish()
            c = e2_cost(self.inst, self.lib, sched)
            adj = end_state_adjustment(self.inst, schedule_end_stock(self.inst, sched),
                                       bike_end_levels(self.inst, self.lib, sched))
            shortfall = (sum(flags["end_shortfalls"]["local"].values())
                         + flags["end_shortfalls"]["global"])
            phi_new = (c["total"] + (adj["total"] if self.cfg.end_state == "m1" else 0.0)
                       + self.cfg.shortfall_penalty * shortfall)
            terminated = True
            info.update(schedule=sched, flags=flags, cost=c, episode_cost=c["total"],
                        end_adj=adj["total"], end_adj_parts=adj,
                        adjusted_total=c["total"] + adj["total"], shortfall=shortfall,
                        phi0=self.phi0)
        reward = -(phi_new - self.phi) * self.cfg.reward_scale
        info["phi_prev"], info["phi"] = self.phi, phi_new
        self.phi = phi_new
        obs = self._obs() if not terminated else self._obs(final=True)
        return obs, float(reward), terminated, False, info

    # ------------------------------------------------------------- pieces
    def decode_action(self, action: Any) -> Tuple[Dict[Any, int], Dict[Any, int]]:
        """Action vector -> (``{charge site: batteries to charge}`` (20), ``{service: load}`` (10)),
        clipped to the bounds of the current instance."""
        a = np.asarray(action, dtype=np.int64).reshape(-1)
        nC = len(self.charge_ids)
        charge: Dict[Any, int] = {}
        for idx, j in enumerate(self.charge_ids):
            v = int(a[idx]) if idx < a.size else 0
            charge[j] = max(0, v)
        loads: Dict[Any, int] = {}
        for idx, e in enumerate(self.svc_ids):
            pos = nC + idx
            v = int(a[pos]) if pos < a.size else 0
            loads[e] = max(0, min(v, int(self.inst.service(e).U)))
        return charge, loads

    def encode_action(self, charge: Dict[Any, int], loads: Dict[Any, int]) -> np.ndarray:
        """Inverse of :meth:`decode_action` (values clipped to the action space)."""
        vec = [int(charge.get(j, 0)) for j in self.charge_ids] + [int(loads.get(e, 0)) for e in self.svc_ids]
        if not vec:
            vec = [0]
        return np.minimum(np.maximum(np.array(vec, dtype=np.int64), 0), self.action_space.nvec - 1)

    def partial_schedule(self) -> Schedule:
        """Snapshot of the committed schedule (the argument of the potential ``Phi_t``)."""
        return self.run.partial_schedule(self.cfg.provisional_unserved)

    def _potential(self) -> float:
        return float(e2_cost(self.inst, self.lib, self.partial_schedule())["total"])

    def _obs(self, final: bool = False) -> np.ndarray:
        run, inst = self.run, self.inst
        L, H = inst.L, inst.H
        t = min(run.t, H)
        nK = max(1, len(inst.bikes))
        lb = self.cfg.lookback
        feats: List[float] = []
        for j in self.fac_ids:
            f = inst.facility(j)
            K = max(1, int(f.K))
            row = run.n[j]
            feats.extend(float(row[q]) / K for q in range(L + 1))
            hist = run.swaps_by_slot[j]
            # swaps issued at boundaries (t - lookback, t]; those of t precede the action
            lo = max(0, t - lb + 1)
            recent = sum(hist[lo:t + 1])
            last = hist[t] if t < len(hist) else 0
            feats.append(recent / float(lb))
            feats.append(float(last))
            feats.append(len(run.queue.get(j, ())) / nK)
            full_in = sum(cnt for (u, q, cnt) in run.pending_arrivals.get(j, ()) if u > t and q == L)
            all_in = sum(cnt for (u, q, cnt) in run.pending_arrivals.get(j, ()) if u > t)
            feats.append(full_in / K)
            feats.append((all_in - full_in) / K)
        start_h = 0.0
        wh = inst.meta.get("window_h")
        if isinstance(wh, (list, tuple)) and wh:
            start_h = float(wh[0])
        hour = (start_h + t * inst.disc.Delta_h) % 24.0
        levels = [bs.q for bs in run.bikes.values()]
        B_tot = max(1, sum(run.B.values()))
        in_transit = sum(cnt for lst in run.pending_arrivals.values() for (u, q, cnt) in lst if u > t)
        feats.extend([
            t / float(H),
            math.sin(2 * math.pi * hour / 24.0), math.cos(2 * math.pi * hour / 24.0),
            len(run.Q) / nK,
            sum(1 for q in levels if q <= run.q_thr) / nK,
            (float(np.mean(levels)) / L) if levels else 0.0,
            in_transit / B_tot,
            1.0 if final else 0.0,
        ])
        for e in self.svc_ids:
            svc = inst.service(e)
            feats.append(1.0 if svc.l == t else 0.0)
            feats.append(max(-1.0, min(1.0, (svc.l - t) / float(H))))
        return np.asarray(feats, dtype=np.float32)

    # ------------------------------------------------------------- heuristics
    def heuristic_action(self, name: str = "demand_aware") -> np.ndarray:
        """Hand-written station rules expressed in the A7 action space (comparators):

        * ``'none'``          -- charge nothing, ship nothing;
        * ``'asap'``          -- charge ``cap_j`` everywhere (HIGH_FIRST ASAP of round 1), no loads;
        * ``'demand_aware'``  -- the baseline's R2.3 counts (``min(need_j, cap_j)`` at swap
          sites, ``hub_charge_rule`` HIGH_FIRST at hubs), no loads.  With no services this
          reproduces ``baseline.run_baseline`` exactly (tested)."""
        run = self.run
        t = run.t
        charge: Dict[Any, int] = {}
        for j in self.charge_ids:
            cap = charge_cap(self.inst, j, run.y[j], run.C[j]) if j in run.open_charge else 0
            if name == "none":
                charge[j] = 0
            elif name == "asap":
                charge[j] = cap
            elif name == "demand_aware":
                rule = run._charge_rule_for(j)
                if rule == "DEMAND_AWARE":
                    _, need = run.demand_aware_need(j, t)
                    charge[j] = min(cap, need)
                else:
                    charge[j] = cap
            else:
                raise ValueError(f"unknown heuristic {name!r}")
        return self.encode_action(charge, {})


__all__ = ["StationEnv", "EnvConfig", "make_family_factory", "resolve_rider_variant",
           "rider_params", "charge_cap", "end_state_adjustment", "adjusted_cost",
           "bike_end_levels", "schedule_end_stock", "RIDER_ALIASES"]
