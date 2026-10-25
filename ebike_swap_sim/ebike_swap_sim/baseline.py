"""Event-driven baseline policy for the E2 model (``notes/extracted/E2.txt``), run
on exactly the same :class:`~ebike_swap_sim.or_instance.Instance` and
:class:`~ebike_swap_sim.arcs.ArcLibrary` as the ILP (``notes/DECISIONS.md``,
section "Baseline policy"; pseudo-code in ``notes/workflow1_result.json`` ->
``plan.baseline_policy_spec`` steps 1-14).

The policy is the "naive" simulator of the proposal deck and of Battery_Swap
p.7 / E2 p.9, upgraded by the round-2 decisions (``DECISIONS.md`` R2.3):
nearest-feasible-rider dispatch with an order-FIFO queue, a battery-threshold
swap rule whose trip goes to the nearest *stocked* open swap site
(``stock_aware_site``, R2.3), first-come-first-served swap service with position
occupancy (22), demand-aware charging (``charge_rule='DEMAND_AWARE'``, R2.3;
ASAP ``HIGH_FIRST`` / ``LOW_FIRST`` remain selectable) within (20)-(21), and, by
default, no battery transfers (optional reorder-point rule for (10)-(11)).
Every step uses only information available at the current boundary ``t``;
nothing is anticipated.

Information set of every rule (non-anticipative, all evaluated at boundary ``t``)
------------------------------------------------------------------------------
* Order release / FIFO (steps 2, 6): orders with ``r_i <= t`` and their
  attributes ``(o_i, d_i, a_i, b_i, hp_i, hd_i)`` -- known at release; nothing
  about orders released later.
* Dispatch (step 6): the idle bikes' current states ``(v, t, q)``, the static
  route library (``tau_r``, ``g_r``, ``d_r``; deterministic data), the arc
  library (same pruning as the ILP) and ``gbar`` (static shortest-path energies).
* Threshold rule (step 4): the bike's own level ``q`` and ``q_thr``.
* Stock-aware site choice (R2.3, :meth:`_BaselineRun._go_swap`): the current full
  stock ``n_jLt`` of every open swap site (station lists are public), the bike's
  own position and energy.  Not used: future arrivals / returns, other bikes'
  intentions, bikes already queued at the site.
* FCFS swap service (step 5): queue order, ``n_jLt`` (14), ongoing swaps (22).
* DEMAND_AWARE charging (R2.3, :meth:`_BaselineRun._step9_charging`): the swap
  counts ``S_j,tau`` of this site for ``tau in (t - lookback, t]`` (including the
  swaps issued at this boundary, which precede step 9), the current stock
  ``n_jqt`` after this boundary's swaps and departures, ``R_end_j``, the charger /
  power / grid caps.  Not used: future orders, future swaps, planned trips.
* REORDER_POINT transfers (step 8): current stock, shipments already dispatched
  (``pending_arrivals``), the timetable of the services departing now.

Round-5 rules (``notes/reading_to_model.md`` items M2, M3, M4; no E2 equation changes)
-------------------------------------------------------------------------------------
* M2 range-aware swap trigger (``swap_rule='RANGE'``, eBaaS): the bike's own ``(v, q)``;
  the FIFO head of the released, unassigned queue ``Q`` (orders with ``r_i <= t``) or,
  when ``Q`` has no order routable from ``v``, the median requirement over the orders
  *released so far* (``range_typical='released'``; ``'static'`` uses the instance's
  restaurant / customer node pairs, declared like ``max_need`` as static service-area
  knowledge); the static route energies ``g_r`` and ``gbar``; the current
  reservable full stock of every open swap site.  Nothing about unreleased orders.
* M2 reservations (``reservation=True``): the current full stock ``n_jLt`` and the
  reservations already granted (decisions of the past); a reservation is a
  bookkeeping hold on ``n_jLt`` only -- it never moves a battery, so (13)-(16) are
  untouched.
* M3 COST_AWARE transfers (step 8, IJCAI-25): swaps observed at every site in
  ``(t - transfer_lookback, t]`` (rate), current stock ``n_jqt`` after this
  boundary's swaps, reservations, the bikes queued at each site now (public
  queues), shipments already dispatched, the published
  timetable of the services departing now, the static tariff data ``P_i`` / ``w_i``
  (31), ``f_e``, ``v_reb`` (32) and the charger caps (20)-(21).  No future swap or
  order enters; the forecast is ``rate x window``.
* M4 LOGIT site choice (``site_choice='LOGIT'``, IJCAI-15): the bike's own state, the
  static route library, the current queue lengths ``|queue_j|`` and positions
  ``M_j / sigma_j`` (public), the current full stock and the recent swap rate; in the
  equilibrium mode (:func:`run_selfish_equilibrium`) the waits experienced in the
  *previous* simulated day (iteration), never the current day's future.  The logit
  draw uses a private random stream seeded by ``(choice_seed, bike, t)``.
* Compliance (:func:`simulate_compliance`): compliant bikes follow a given schedule
  (the coordinator's plan, computed before the day like every ILP schedule); the
  non-compliant bikes run the policy on the orders the plan does not assign to a
  compliant bike, with the information sets above.

Parity with the ILP
-------------------
* Bike actions are taken **only** through ``ArcLibrary.find`` so the baseline can
  never use an arc the ILP does not have (same (1)-(4), (9) rules and the same
  pruning options).  When an arc would exist by (2)-(4) but was pruned, the bike
  waits and the event is recorded in ``flags['pruned_arc_fallbacks']``.
* Just-in-time dispatch (``BaselineParams.jit_dispatch``, default on): the ILP's
  lossless dominance rule drops delivery arcs with ``t + tau_r < a_i`` (the start
  ``a_i - tau_r`` reached by waiting has the same ``u_a``, ``g_a``, ``theta``).
  That rule is lossless for the optimiser but not for a greedy policy, so step 6
  treats an idle bike whose arc is missing *only* for that reason as a candidate
  with start ``a_i - tau_r``: it commits the wait arcs ``(v,t,q) -> (v, a_i -
  tau_r, q)`` followed by the delivery arc of the library (all ILP arcs), is busy
  until ``u_a`` and is ranked by ``tau_r`` like every other candidate (nearest
  rider; response ``u_a - r_i`` unchanged).  ``flags['jit_dispatches']`` counts them.
* Dead-zone rule (``swap_on_reach_refusal``, default on): a bike refused an order
  *solely* by the post-delivery reach guard of step 6 and with ``q <= max_need``
  (``max_need`` = max over orders / start nodes of ``g_a + gbar(d_i) + q_res``) is
  sent to swap instead of idling to ``H``; ``flags['reach_refusals']`` reports it.
  ``max_need`` is a single static constant of the service area, computed once at
  construction over the instance's restaurant -> customer pairs (fairness review
  F6): it is declared as *static fleet knowledge of the service area* (the energy
  envelope of a delivery in the area, which a dispatcher knows from the map and the
  bike physics), not as knowledge of individual future orders -- no release time,
  identity or count of an unreleased order enters any decision through it.  A
  purely geographic bound (max over all node pairs of ``V``) would be >= this value
  and only make the dead-zone rule fire more often.
* Stock-aware site choice (``stock_aware_site``, default on, R2.3): the swap trip
  goes to the nearest open site with ``n_jLt >= 1`` at decision time, falling back
  to the nearest site when none has stock; ``flags['stock_aware_reroutes']``
  counts the trips whose destination differs from the naive nearest site (or
  that leave an empty site), ``flags['stock_aware_fallbacks']`` the fallbacks.
* Demand-aware charging (``charge_rule='DEMAND_AWARE'``, default, R2.3): at
  boundary ``t`` a charge site charges ``min(need_j, caps)`` batteries HIGH_FIRST
  with ``need_j = forecast_j(t) + reserve_j - n_jLt``, ``forecast_j(t)`` = swaps
  observed at ``j`` in ``(t - lookback, t]`` scaled to the lead window
  (``ceil(swaps * lead / w)``, ``w = min(lookback, t + 1)`` observed slots; 0
  without any swap yet) and ``reserve_j = R_end_j`` (17).  A battery at level ``q``
  charged from ``t`` on is full at ``t + (L - q) <= t + lead`` (default ``lead = L``),
  so the batteries being charged are exactly the "already charging, finishing
  within the lead window" term of R2.3 and are counted implicitly: the rule
  continues them first (HIGH_FIRST) and starts new ones only for the remaining
  need.  ``flags['demand_aware']`` records forecasts, needs and the ASAP
  counterfactual caps.  Charge-only hubs (``j in C \\ S``) never observe a swap,
  so their forecast is identically 0; ``hub_charge_rule`` (default
  ``'HIGH_FIRST'``) governs them and ``'DEMAND_AWARE'`` gives the literal
  reading (hubs then charge only up to ``R_end_j``).
* Facility inventory is stepped with the exact balance (13), initial stock (16)
  and the joint availability (14); the trajectory ``n_jqt`` is returned in
  ``Schedule.n`` and cross-checked against ``evaluate.reconstruct_inventory``
  (``flags['inventory_consistent']``).
* The result is a :class:`~ebike_swap_sim.evaluate.Schedule` priced by
  ``evaluate.cost`` (26)-(32) and verified by ``evaluate.check``.  Families (5),
  (6), (10), (13), (14), (15), (16), (20), (21), (22) hold by construction;
  (9), (17), (18) are *reported* (``flags``), not enforced.

Timing conventions (E2 Section 5, DECISIONS.md): ``n_jqt`` is the stock after
transport arrivals at ``t`` and before new actions; swaps and departures at ``t``
draw from that stock; a bike-returned battery enters stock at ``t+1``; charging in
slot ``t`` finishes at ``t+1``.  Determinism: all ties are broken by index
(bike / order / facility position in the instance lists).
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .arcs import Arc, ArcLibrary
from .evaluate import Schedule, reconstruct_inventory
from .or_instance import Instance, Order

CHARGE_RULES = ("DEMAND_AWARE", "HIGH_FIRST", "LOW_FIRST")
#: ``'ASAP'`` is accepted as an alias of the round-1 rule ``'HIGH_FIRST'`` (R2.3).
CHARGE_RULE_ALIASES = {"ASAP": "HIGH_FIRST"}
#: ``'COST_AWARE'`` = M3 (round 5); ``'PLAN'`` is set internally by
#: :func:`simulate_compliance` (replay of a plan's ``h`` / ``z``) and is not a user value.
TRANSFER_RULES = ("NONE", "REORDER_POINT", "COST_AWARE")
DISPATCH_SCOPES = ("global", "zone")
#: M2: ``'THRESHOLD'`` = round-1/2 rule ``q <= q_thr``; ``'RANGE'`` = range-aware trigger.
SWAP_RULES = ("THRESHOLD", "RANGE")
#: M4: ``'NEAREST'`` = round-2 site choice (``stock_aware_site`` governs); ``'LOGIT'`` =
#: self-interested multinomial-logit choice.
SITE_CHOICES = ("NEAREST", "LOGIT")
RANGE_TYPICAL = ("released", "static")
STOCKOUT_COST_MODES = ("P", "wait")
STATION_PLANS = ("plan", "policy")
TRANSFER_RESERVE = ("end", "always", "none")
_FLOOR_TOL = 1e-9
_MAX_EXAMPLES = 50


# ---------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------
@dataclass
class BaselineParams:
    """Policy parameters of the baseline (``plan.baseline_policy_spec``).

    Attributes
    ----------
    q_thr : int or None
        Swap threshold of the rider rule (deck p.7): an idle bike with
        ``q <= q_thr < L`` heads for a swap site.  ``None`` means
        ``ceil(swap_threshold_frac * L)`` (config 0.25 -> 1 of 2, 3 of 12).
    swap_threshold_frac : float
        Used only when ``q_thr`` is ``None``.
    charge_rule : ``'DEMAND_AWARE'`` | ``'HIGH_FIRST'`` | ``'LOW_FIRST'`` (``'ASAP'`` = HIGH_FIRST)
        ``DEMAND_AWARE`` (default, DECISIONS R2.3): at boundary ``t`` charge
        ``min(need_j, caps)`` batteries HIGH_FIRST with ``need_j = forecast_j(t) +
        reserve_j - n_jLt`` (see the module docstring; information set = swaps
        observed at ``j`` in ``(t - charge_lookback, t]``, current stock, ``R_end_j``).
        ``HIGH_FIRST`` / ``LOW_FIRST`` are the round-1 ASAP rules: charge at the
        maximum admissible rate (20)-(21), batteries closest to full first
        (earliest next full battery) or the most depleted ones first.
    charge_lead : int
        ``lead`` of DEMAND_AWARE: the forecast window in slots (R2.3: 12 = one full
        charge from empty at ``L = 12``).
    charge_lookback : int
        ``lookback`` of DEMAND_AWARE: swaps in ``(t - lookback, t]`` are scaled by
        ``lead / w`` with ``w = min(lookback, t + 1)`` observed slots (R2.3: 12).
    charge_reserve : None | int | dict
        ``reserve_j`` of DEMAND_AWARE: ``None`` (default) = ``R_end_j y_j`` of (17);
        an int for every site or ``{fac_id: reserve}``.
    hub_charge_rule : ``'HIGH_FIRST'`` | ``'LOW_FIRST'`` | ``'DEMAND_AWARE'``
        Rule used under ``charge_rule='DEMAND_AWARE'`` at charge-only hubs
        (``j in C \\ S``), where no swap is ever observed and the literal R2.3
        forecast is identically 0.  Default ``'HIGH_FIRST'`` (ASAP at hubs, so that
        separated layouts still recharge the batteries shipped to the hub);
        ``'DEMAND_AWARE'`` is the literal reading (hubs charge only up to
        ``reserve_j``).  Ignored when ``charge_rule`` is not DEMAND_AWARE.
    transfer_rule : ``'NONE'`` | ``'REORDER_POINT'``
        ``NONE``: ``h = z = 0``.  ``REORDER_POINT``: at a service departure
        ``l_e = t`` from a charge hub to a swap site, ship full batteries when the
        swap site's full stock plus already-dispatched full arrivals by
        ``t + lead`` is at most ``s_j``; from a swap site to a charge hub, ship the
        non-full batteries (lowest level first).  Loads respect (10), (14) and the
        destination storage (15) at arrival.
    reorder_point : int or dict
        ``s_j`` of the reorder rule, a scalar for all swap sites or ``{fac_id: s_j}``.
    reorder_lead : int or None
        Look-ahead ``lead`` of the reorder rule; ``None`` = the arrival boundary of
        the service under consideration (``u_e``).
    opportunistic_swap : bool
        Step 7: an idle bike standing at an open swap site with ``q < L`` swaps when
        a full battery and a free position are available, even above threshold.
    dispatch_scope : ``'global'`` | ``'zone'``
        ``'zone'`` prefers candidate bikes in the restaurant's zone
        (``inst.options['node_zone']``: node -> zone); without that option or
        without a same-zone candidate it behaves like ``'global'``.
    end_reserve_window : int or None
        RESERVE variant of step 13: during the last ``W_end`` slots refuse a swap
        at ``j`` when ``n_jLt <= R_end_j``; ``None`` = off.
    require_post_delivery_reach : bool
        Dispatch guard of step 6 (deck assumption): a bike is a candidate only if,
        after the delivery, ``q - g_a >= min_j gbar(d_i, j) + q_res`` so that (9)
        can be certified at ``H``.
    jit_dispatch : bool
        Step 6 just-in-time start (reviewer F1): an idle bike whose delivery arc
        is absent only because of the ILP's dominance rule (``t + tau_r < a_i``)
        is a candidate that waits at its node and starts at ``a_i - tau_r`` (the
        arc the library does contain); ranked by ``tau_r`` like every other
        candidate.  ``False`` reproduces the pre-fix behaviour (farther bikes
        with ``t + tau_r >= a_i`` win).
    swap_on_reach_refusal : bool
        Step 6 dead-zone rule (reviewer F2): a bike refused an order solely by the
        post-delivery reach guard, not dispatched at this boundary and with
        ``q <= max_need`` goes to swap (same routing as the threshold rule, at the
        same boundary) instead of idling to ``H``.  ``False`` = pre-fix behaviour.
    stock_aware_site : bool
        DECISIONS R2.3 (reviewer F6 a), default ``True``: the swap trip goes to the
        nearest open site with at least one full battery *now* (``n_jLt >= 1`` at
        decision time, public station lists), falling back to the nearest site
        when none has stock; a bike standing at an empty site that is not yet
        queued rides to a stocked one.  ``False`` = round-1 naive deck policy
        (nearest site regardless of stock).
    late_threshold_window : int or None
        Informed variant (b) of reviewer F6 / end-of-horizon awareness of the
        RESERVE variant: no swap trip (threshold or reach-refusal) whose swap
        could only end after ``H - W`` (``t + tau + sigma_j > H - W``; at a site
        ``t + sigma_j > H - W``); the bike stays idle and dispatchable instead.
        ``None`` = off.

    Round-5 fields (``notes/reading_to_model.md``; defaults keep the round-2 policy)
    -------------------------------------------------------------------------------
    swap_rule : ``'THRESHOLD'`` | ``'RANGE'``
        M2 (eBaaS).  ``RANGE``: an idle bike with ``q < L`` needs a swap when
        ``q < min(need + range_margin, ceil(range_cap_frac L))`` with ``need = g_a(v,
        i) + gbar_stocked(d_i) + q_res`` for the next order ``i`` (FIFO head of the
        released queue routable from ``v``), else the median of that quantity over the
        typical orders (``range_typical``), else ``gbar_stocked(v) + q_res`` without
        any order; ``gbar_stocked(x)`` = least energy (Dijkstra ``gbar``) from ``x`` to
        an open swap site with reservable full stock (all open sites when none).
    range_margin : int
        Safety margin ``T`` in levels.
    range_cap_frac : float
        Upper cap of the trigger level as a share of ``L`` (no swap above it).
    range_typical : ``'released'`` | ``'static'``
        Typical-order set: orders released so far (strictly non-anticipative,
        default) or all restaurant / customer node pairs of the instance (static
        service-area knowledge, as ``max_need``).
    reservation : bool
        M2: a bike deciding to swap at site ``j`` reserves one full battery there
        when ``n_jLt`` minus the other active reservations is ``>= 1``; reserved
        batteries are not issued to other bikes (FCFS service and transfers skip
        them); a reservation is consumed by the swap and released when the bike
        re-routes, gives up, or has not arrived within ``reservation_timeout`` slots
        of the decision (a bike queued at the site keeps it).
    reservation_timeout : int
        Timeout in slots.
    transfer_lookback, transfer_lead : int
        M3 (``transfer_rule='COST_AWARE'``): swap rate = swaps in ``(t - lookback,
        t]`` / ``min(lookback, t + 1)``; the forecast window after a shipment's
        arrival is ``lead`` slots.
    transfer_prior_rate : float
        Swap rate per slot assumed at a swap site before any swap is observed
        (default 0: nothing is shipped on a zero forecast unless a reserve is short).
    stockout_cost_mode : ``'P'`` | ``'wait'``
        Value ``V`` of one avoided stock-out: ``P`` = mean ``P_i`` (31) times
        ``orders_per_stockout``; ``wait`` = mean ``w_i`` x ``Delta`` x
        ``stockout_wait_slots`` (``None`` = ``L`` slots, one full charge).
    orders_per_stockout : float
    stockout_wait_slots : int or None
    transfer_load_cap : int or None
        Extra cap on one service load (IJCAI-25 action range); ``None`` = ``U_e`` only.
    transfer_reserve : ``'end'`` | ``'always'`` | ``'none'``
        When the end reserve ``R_end_j`` (17) counts as demand in M3: only for forecast
        windows reaching ``H`` (default), always, or never.
    site_choice : ``'NEAREST'`` | ``'LOGIT'``
        M4 (IJCAI-15).  ``LOGIT``: the swap site is drawn from a multinomial logit over
        the reachable open swap sites with utility ``-(logit_alpha tau_j + logit_beta
        W_j + logit_gamma R_j) / logit_scale`` (``tau_j`` travel slots, ``W_j`` expected
        wait in slots, ``R_j`` stock-out risk in [0, 1]); ``W_j = |queue_j| / (M_j /
        sigma_j)`` or ``expected_wait[j]`` when given (equilibrium mode); ``R_j =
        Pr(Poisson(rate_j tau_j) >= a_j)`` with ``a_j`` = full stock minus queued bikes
        and other reservations (``R_j = 1`` when ``a_j <= 0``).
    logit_alpha, logit_beta, logit_gamma, logit_scale : float
    choice_seed : int
        Seed of the logit draws (one private stream per ``(seed, bike, t)``).
    expected_wait : dict or None
        ``{fac_id: slots}``; set by :func:`run_selfish_equilibrium`.
    """
    q_thr: Optional[int] = None
    swap_threshold_frac: float = 0.25
    charge_rule: str = "DEMAND_AWARE"
    charge_lead: int = 12
    charge_lookback: int = 12
    charge_reserve: Union[None, int, Dict[Any, int]] = None
    hub_charge_rule: str = "HIGH_FIRST"
    transfer_rule: str = "NONE"
    reorder_point: Union[int, Dict[Any, int]] = 1
    reorder_lead: Optional[int] = None
    opportunistic_swap: bool = False
    dispatch_scope: str = "global"
    end_reserve_window: Optional[int] = None
    require_post_delivery_reach: bool = True
    jit_dispatch: bool = True
    swap_on_reach_refusal: bool = True
    stock_aware_site: bool = True
    late_threshold_window: Optional[int] = None
    # --- round 5 (M2 / M3 / M4); defaults reproduce the round-2 policy exactly
    swap_rule: str = "THRESHOLD"
    range_margin: int = 1
    range_cap_frac: float = 0.5
    range_typical: str = "released"
    reservation: bool = False
    reservation_timeout: int = 6
    transfer_lookback: int = 12
    transfer_lead: int = 12
    transfer_prior_rate: float = 0.0
    stockout_cost_mode: str = "P"
    orders_per_stockout: float = 1.0
    stockout_wait_slots: Optional[int] = None
    transfer_load_cap: Optional[int] = None
    transfer_reserve: str = "end"
    site_choice: str = "NEAREST"
    logit_alpha: float = 1.0
    logit_beta: float = 1.0
    logit_gamma: float = 4.0
    logit_scale: float = 1.0
    choice_seed: int = 0
    expected_wait: Optional[Dict[Any, float]] = None

    def validate(self) -> None:
        self.charge_rule = CHARGE_RULE_ALIASES.get(self.charge_rule, self.charge_rule)
        self.hub_charge_rule = CHARGE_RULE_ALIASES.get(self.hub_charge_rule, self.hub_charge_rule)
        if self.charge_rule not in CHARGE_RULES:
            raise ValueError(f"charge_rule must be one of {CHARGE_RULES} (or 'ASAP')")
        if self.hub_charge_rule not in CHARGE_RULES:
            raise ValueError(f"hub_charge_rule must be one of {CHARGE_RULES} (or 'ASAP')")
        if int(self.charge_lead) < 0:
            raise ValueError("charge_lead must be >= 0")
        if int(self.charge_lookback) < 1:
            raise ValueError("charge_lookback must be >= 1")
        if self.charge_reserve is not None and not isinstance(self.charge_reserve, dict) \
                and int(self.charge_reserve) < 0:
            raise ValueError("charge_reserve must be >= 0")
        if self.transfer_rule not in TRANSFER_RULES:
            raise ValueError(f"transfer_rule must be one of {TRANSFER_RULES}")
        if self.dispatch_scope not in DISPATCH_SCOPES:
            raise ValueError(f"dispatch_scope must be one of {DISPATCH_SCOPES}")
        if self.q_thr is not None and self.q_thr < 0:
            raise ValueError("q_thr must be >= 0")
        if not (0 <= self.swap_threshold_frac <= 1):
            raise ValueError("swap_threshold_frac must lie in [0, 1]")
        if self.end_reserve_window is not None and self.end_reserve_window < 0:
            raise ValueError("end_reserve_window must be >= 0")
        if self.reorder_lead is not None and self.reorder_lead < 0:
            raise ValueError("reorder_lead must be >= 0")
        if self.late_threshold_window is not None and self.late_threshold_window < 0:
            raise ValueError("late_threshold_window must be >= 0")
        if self.swap_rule not in SWAP_RULES:
            raise ValueError(f"swap_rule must be one of {SWAP_RULES}")
        if self.site_choice not in SITE_CHOICES:
            raise ValueError(f"site_choice must be one of {SITE_CHOICES}")
        if self.range_typical not in RANGE_TYPICAL:
            raise ValueError(f"range_typical must be one of {RANGE_TYPICAL}")
        if self.stockout_cost_mode not in STOCKOUT_COST_MODES:
            raise ValueError(f"stockout_cost_mode must be one of {STOCKOUT_COST_MODES}")
        if int(self.range_margin) < 0 or not (0 < float(self.range_cap_frac) <= 1):
            raise ValueError("range_margin must be >= 0 and range_cap_frac in (0, 1]")
        if int(self.reservation_timeout) < 0:
            raise ValueError("reservation_timeout must be >= 0")
        if int(self.transfer_lookback) < 1 or int(self.transfer_lead) < 0:
            raise ValueError("transfer_lookback must be >= 1 and transfer_lead >= 0")
        if float(self.transfer_prior_rate) < 0 or float(self.orders_per_stockout) < 0:
            raise ValueError("transfer_prior_rate and orders_per_stockout must be >= 0")
        if self.stockout_wait_slots is not None and int(self.stockout_wait_slots) < 0:
            raise ValueError("stockout_wait_slots must be >= 0")
        if self.transfer_reserve not in TRANSFER_RESERVE:
            raise ValueError(f"transfer_reserve must be one of {TRANSFER_RESERVE}")
        if self.transfer_load_cap is not None and int(self.transfer_load_cap) < 0:
            raise ValueError("transfer_load_cap must be >= 0")
        if float(self.logit_scale) <= 0:
            raise ValueError("logit_scale must be > 0")
        if min(float(self.logit_alpha), float(self.logit_beta), float(self.logit_gamma)) < 0:
            raise ValueError("logit coefficients must be >= 0")

    def threshold(self, L: int) -> int:
        """Effective ``q_thr``: the given value or ``ceil(swap_threshold_frac * L)``."""
        if self.q_thr is not None:
            return int(self.q_thr)
        return int(math.ceil(self.swap_threshold_frac * L - _FLOOR_TOL))

    def s_j(self, j: Any) -> int:
        """Reorder point ``s_j`` of swap site ``j``."""
        if isinstance(self.reorder_point, dict):
            return int(self.reorder_point.get(j, 0))
        return int(self.reorder_point)

    def reserve_j(self, j: Any, R_end_eff: int) -> int:
        """``reserve_j`` of the DEMAND_AWARE rule (R2.3): ``charge_reserve`` when
        given (scalar or ``{fac_id: reserve}``), else ``R_end_eff = R_end_j y_j`` (17)."""
        if self.charge_reserve is None:
            return int(R_end_eff)
        if isinstance(self.charge_reserve, dict):
            return int(self.charge_reserve.get(j, R_end_eff))
        return int(self.charge_reserve)

    @classmethod
    def coerce(cls, params: Union["BaselineParams", Dict[str, Any], None]) -> "BaselineParams":
        """Accept a :class:`BaselineParams`, a dict of its fields, or ``None`` (defaults)."""
        if params is None:
            p = cls()
        elif isinstance(params, cls):
            p = params
        elif isinstance(params, dict):
            p = cls(**params)
        else:
            raise TypeError("params must be BaselineParams, dict or None")
        p.validate()
        return p


# ---------------------------------------------------------------------------
# per-bike state
# ---------------------------------------------------------------------------
class _BikeState:
    __slots__ = ("k", "v", "q", "free_at", "needs_swap", "path", "queued_at", "queue_since",
                 "episode", "ep_outage", "swap_target")

    def __init__(self, k: Any, v: Any, q: int) -> None:
        self.k = k
        self.v = v
        self.q = q
        self.free_at = 0
        self.needs_swap = False
        self.path: List[int] = []
        self.queued_at: Any = None      # facility id of the swap queue the bike is in
        self.queue_since: Optional[int] = None
        self.episode = False            # a swap episode (decision -> swap) is open
        self.ep_outage = False          # the open episode met a stock-out
        self.swap_target: Any = None    # site the bike is riding to for a swap


# ---------------------------------------------------------------------------
# the simulation
# ---------------------------------------------------------------------------
class _BaselineRun:
    """One slot-stepped run of the baseline policy (steps 1-14 of the spec)."""

    def __init__(self, inst: Instance, lib: ArcLibrary, params: BaselineParams) -> None:
        self.inst = inst
        self.lib = lib
        self.p = params
        self._notes: List[str] = []
        disc = inst.disc
        self.H, self.L = disc.H, disc.L
        self.q_thr = params.threshold(self.L)
        self.kidx = {b.id: i for i, b in enumerate(inst.bikes)}
        self.fidx = {f.id: i for i, f in enumerate(inst.facilities)}
        self.oidx = {o.id: i for i, o in enumerate(inst.orders)}
        # effective facility data (free y -> open, free B/C -> 0, as evaluate does)
        self.y = {f.id: (1 if f.y is None else int(f.y)) for f in inst.facilities}
        self.B = {f.id: (0 if f.B is None else int(f.B)) for f in inst.facilities}
        self.C = {f.id: (0 if f.C is None else int(f.C)) for f in inst.facilities}
        self.open_swap = [f.id for f in inst.facilities if f.swap and self.y[f.id] == 1]
        self.open_charge = [f.id for f in inst.facilities if f.charge and self.y[f.id] == 1]
        self.swap_at_node: Dict[Any, List[Any]] = defaultdict(list)
        for j in self.open_swap:
            self.swap_at_node[inst.facility(j).node].append(j)
        # transfers are disabled by the model switch as well
        self.transfer_rule = params.transfer_rule
        if inst.option("no_transfers") and self.transfer_rule != "NONE":
            self.transfer_rule = "NONE"
            self._note("options.no_transfers is set: transfer_rule forced to NONE")
        if self.transfer_rule == "COST_AWARE" and not inst.services:
            self.transfer_rule = "NONE"                 # 'r5': M3 applies only when services exist
            self._note("no services in the instance: COST_AWARE transfer rule inert (NONE)")
        # zone map for dispatch_scope='zone'
        self.node_zone = self._zone_map(inst.options.get("node_zone"))
        # minimal energy from a node to any open swap site (dispatch guard, step 6)
        self.min_gbar: Dict[Any, float] = {}
        for v in inst.nodes:
            vals = [lib.gbar.get((v, j), math.inf) for j in self.open_swap]
            self.min_gbar[v] = min(vals) if vals else math.inf
        # max over orders and start nodes of g_a + gbar(d_i) + q_res (dead-zone rule, reviewer F2)
        self.max_need: float = self._compute_max_need()
        # state
        self.bikes: Dict[Any, _BikeState] = {b.id: _BikeState(b.id, b.v0, b.q0) for b in inst.bikes}
        self.n: Dict[Any, List[int]] = {}
        self.hold: Dict[Any, List[int]] = {}
        for f in inst.facilities:
            row = [0] * (self.L + 1)
            row[self.L] = self.B[f.id]                       # (16)
            self.n[f.id] = row
            self.hold[f.id] = [0] * (self.L + 1)
        self.active_swaps: Dict[Any, List[int]] = defaultdict(list)
        self.queue: Dict[Any, List[Any]] = defaultdict(list)   # fac -> FIFO of bike ids
        self.Q: List[Any] = []                                  # released, unassigned orders
        self.assigned: Dict[Any, Tuple[Any, int]] = {}         # order -> (bike, u_a)
        self.pending_arrivals: Dict[Any, List[Tuple[int, int, int]]] = defaultdict(list)  # fac -> [(u, q, cnt)]
        # records
        self.s: Dict[Tuple[Any, int, int], int] = defaultdict(int)
        self.S: Dict[Tuple[Any, int], int] = defaultdict(int)
        self.c: Dict[Tuple[Any, int, int], int] = {}
        self.D: Dict[Tuple[Any, int, int], int] = defaultdict(int)
        self.A: Dict[Tuple[Any, int, int], int] = defaultdict(int)
        self.h: Dict[Any, int] = {e.id: 0 for e in inst.services}
        self.z: Dict[Tuple[Any, int], int] = {}
        self.n_hist: Dict[Tuple[Any, int, int], int] = {}
        # flags
        self.flags: Dict[str, Any] = {
            "stranded": [],                 # (bike, t, reason)
            "stranded_bikes": [],
            "queued_at_H": [],
            "terminal_violations": [],      # (bike, state, how)
            "storage_violations": [],       # (facility, t, stock, capacity)
            "end_shortfalls": {"local": {}, "global": 0.0},
            "wait_slots_in_queue": {j: 0 for j in self.open_swap},
            "pruned_arc_fallbacks": {"count": {"move": 0, "deliver": 0, "swap": 0}, "examples": []},
            "inventory_consistent": None,
            "notes": self._notes,
            "q_thr": self.q_thr,
            "max_need": (None if self.max_need == math.inf else self.max_need),
            "transfer_rule_effective": self.transfer_rule,
            "jit_dispatches": 0,            # step 6 just-in-time starts (reviewer F1)
            "reach_refusals": {"count": 0, "bikes_sent_to_swap": 0, "examples": []},   # reviewer F2
            "late_trips_suppressed": 0,     # late_threshold_window (reviewer F6 b)
            "stock_aware_reroutes": 0,      # R2.3: trips not to the naive nearest site / leaving an empty site
            "stock_aware_fallbacks": 0,     # R2.3: no stocked site -> nearest site used
            "charge_rule_effective": {},    # facility -> rule actually applied in step 9
            "demand_aware": {               # R2.3 charging diagnostics (per charge site, per slot)
                "forecast": {}, "need": {}, "charged": {}, "asap_cap": {},
                "charge_steps": 0, "asap_cap_steps": 0,
            },
        }
        self.swaps_by_slot: Dict[Any, List[int]] = {f.id: [0] * (self.H + 1) for f in inst.facilities}
        # round 5 (M2 / M3 / M4 / compliance) state and flags
        self.resv: Dict[Any, Dict[Any, int]] = {j: {} for j in self.open_swap}   # site -> {bike: expiry}
        self._g_cache: Dict[Tuple[Any, Any], Optional[int]] = {}
        self.compliant: Dict[Any, List[Arc]] = {}      # bike -> remaining planned arcs (simulate_compliance)
        self.plan_terminal: Dict[Any, Arc] = {}
        self.plan_orders: Dict[Any, Any] = {}          # order -> compliant bike holding it
        self.plan_station: Optional[Dict[str, Any]] = None
        self.flags.update({
            "swap_rule_effective": params.swap_rule,
            "site_choice_effective": params.site_choice,
            "outages": {                    # M2 / A3: policy-side stock-out accounting
                "swap_episodes": 0,         # decisions to swap (threshold, range or dead-zone rule)
                "outage_episodes": 0,       # episodes that met a stock-out (below)
                "decisions_without_stock": 0,     # no open site had (reservable) full stock
                "arrivals_to_empty": 0,     # rode to a site for a swap and found no battery for it
                "stockout_queue_slots": 0,  # queued bike-slots without an issuable battery (14)
                "position_queue_slots": 0,  # queued bike-slots blocked only by positions (22)
                "reservations_made": 0, "reservations_used": 0, "reservations_released": 0,
                "reservations_expired": 0, "reservations_refused": 0,
                "outage_rate": 0.0,
            },
            "range_rule": {"triggers": 0, "by_source": {"next_order": 0, "typical": 0, "no_order": 0}},
            "site_choice": {"decisions": {j: 0 for j in self.open_swap},
                            "queue_joins": {j: 0 for j in self.open_swap},
                            "logit_draws": 0},
            "cost_aware": {"shipments": [], "considered": 0, "rejected_by_cost": 0},
        })
        # M9 lock-out: data-forced transfers (``options['forced_transfers']``, see
        # ``generator.add_battery_lockout``) are executed by :meth:`_step8_forced` and never
        # touched by the voluntary transfer rules; ``no_transfers`` removes them (as in the ILP)
        self.forced: Dict[Any, Optional[int]] = {}
        for rec in (inst.options.get("forced_transfers") or []):
            self.forced[rec["service"]] = None if rec.get("level") is None else int(rec["level"])
        if self.forced and inst.option("no_transfers"):
            self._note("options.no_transfers is set: forced transfers (M9 lock-out) not executed")
            self.forced = {}
        if self.forced:
            self.flags["forced_transfers"] = {"executed": 0, "missed": [], "loads": []}
        for f in inst.facilities:
            if f.charge and f.C is None:
                self._note(f"facility {f.id}: C free in data; baseline charges nothing there")
            if f.y is None:
                self._note(f"facility {f.id}: y free in data; assumed open by the baseline")

    # ---------------------------------------------------------------- utils
    def _note(self, msg: str) -> None:
        self._notes.append(msg)

    @staticmethod
    def _zone_map(raw: Any) -> Optional[Dict[Any, Any]]:
        if raw is None:
            return None
        if isinstance(raw, dict):
            return dict(raw)
        out: Dict[Any, Any] = {}
        for rec in raw:                    # list of [node, zone] records (JSON form)
            node, zone = rec
            if isinstance(node, list):
                node = tuple(node)
            out[node] = zone
        return out

    def _pruned(self, k: Any, t: int, kind: str, detail: Any) -> None:
        rec = self.flags["pruned_arc_fallbacks"]
        rec["count"][kind] += 1
        if len(rec["examples"]) < _MAX_EXAMPLES:
            rec["examples"].append((k, t, kind, detail))

    def _take(self, bs: _BikeState, arc: Arc) -> None:
        """Append ``arc`` to bike ``bs`` and move its state to the arc head."""
        assert arc.src == (bs.v, bs.free_at, bs.q), (arc, bs.v, bs.free_at, bs.q)
        bs.path.append(arc.id)
        if arc.kind != "term":
            bs.v, _, bs.q = arc.dst
            bs.free_at = arc.u

    def _wait(self, bs: _BikeState, t: int) -> None:
        arc = self.lib.find(bs.k, "wait", (bs.v, t, bs.q))
        if arc is None:  # cannot happen: wait arcs exist from every reachable state, t < H
            raise RuntimeError(f"arc library has no wait arc from {(bs.v, t, bs.q)} for bike {bs.k}")
        self._take(bs, arc)

    def _positions_free(self, j: Any, t: int) -> bool:
        """Swap position available at ``j`` in slot ``t`` (22): ongoing swaps ``< M_j``."""
        ongoing = sum(1 for e in self.active_swaps[j] if e > t)
        return ongoing < self.inst.facility(j).M

    def _reserve_blocks(self, j: Any, t: int) -> bool:
        """RESERVE variant (step 13): keep ``R_end_j`` full batteries in the last ``W_end`` slots."""
        W = self.p.end_reserve_window
        if W is None:
            return False
        f = self.inst.facility(j)
        return t >= self.H - W and self.n[j][self.L] <= f.R_end * self.y[j]

    def _try_swap(self, bs: _BikeState, j: Any, t: int) -> bool:
        """Issue a swap to bike ``bs`` at facility ``j`` starting at ``t`` if a full
        battery (14), a swap position (22), the horizon and the arc allow it.
        Bookkeeping of (12): ``s_jqt``, ``S_jt``; the issued full battery leaves
        ``n_jLt`` now and the returned battery is held until ``t+1`` (13)."""
        f = self.inst.facility(j)
        if bs.q >= self.L or t + f.sigma > self.H:
            return False
        if self._avail_full(j, bs.k) < 1 or not self._positions_free(j, t) or self._reserve_blocks(j, t):
            return False
        arc = self.lib.find(bs.k, "swap", (bs.v, t, bs.q), fac=j)
        if arc is None:
            self._pruned(bs.k, t, "swap", j)      # exists by (22)/(4) rules, pruned (swap_q_max)
            return False
        q_ret = bs.q
        self._take(bs, arc)
        self.s[(j, q_ret, t)] += 1
        self.S[(j, t)] += 1
        self.swaps_by_slot[j][t] += 1
        self.n[j][self.L] -= 1
        self.hold[j][q_ret] += 1
        self.active_swaps[j].append(t + f.sigma)
        bs.needs_swap = False
        if j in self.resv and bs.k in self.resv[j]:
            del self.resv[j][bs.k]
            self.flags["outages"]["reservations_used"] += 1
        self._release_reservation(bs.k)            # a hold elsewhere (cannot happen) is dropped
        bs.episode, bs.ep_outage, bs.swap_target = False, False, None
        return True

    # ------------------------------------------------- round 5: reservations (M2)
    def _others_reserved(self, j: Any, k: Any) -> int:
        """Active reservations at ``j`` held by bikes other than ``k`` (M2)."""
        r = self.resv.get(j)
        if not r:
            return 0
        return len(r) - (1 if k in r else 0)

    def _avail_full(self, j: Any, k: Any = None) -> int:
        """Full batteries at ``j`` issuable to bike ``k`` now: ``n_jLt`` minus the other
        bikes' active reservations (M2).  Without reservations this is ``n_jLt``, the
        round-2 quantity, so every round-2 decision is unchanged."""
        return self.n[j][self.L] - self._others_reserved(j, k)

    def _release_reservation(self, k: Any) -> None:
        for j, r in self.resv.items():
            if k in r:
                del r[k]
                self.flags["outages"]["reservations_released"] += 1

    def _reserve(self, bs: _BikeState, j: Any, t: int) -> None:
        """M2: on deciding to swap at ``j`` reserve one full battery there if the
        reservable stock allows it (else count a refusal); any older hold of the bike
        elsewhere is released first."""
        if not self.p.reservation or j not in self.resv:
            return
        if bs.k in self.resv[j]:
            self.resv[j][bs.k] = max(self.resv[j][bs.k], t + int(self.p.reservation_timeout))
            return
        self._release_reservation(bs.k)
        if self._avail_full(j, bs.k) >= 1:
            self.resv[j][bs.k] = t + int(self.p.reservation_timeout)
            self.flags["outages"]["reservations_made"] += 1
        else:
            self.flags["outages"]["reservations_refused"] += 1

    def _expire_reservations(self, t: int) -> None:
        """M2 timeout: drop reservations with ``expiry < t`` whose bike is not queued at
        the site (a queued bike is using its reservation)."""
        if not self.p.reservation:
            return
        for j, r in self.resv.items():
            for k in [k for k, exp in r.items() if exp < t and self.bikes[k].queued_at != j]:
                del r[k]
                self.flags["outages"]["reservations_expired"] += 1

    # ---------------------------------------------- round 5: outage accounting (M2)
    def _start_episode(self, bs: _BikeState) -> None:
        if not bs.episode:
            bs.episode, bs.ep_outage = True, False
            self.flags["outages"]["swap_episodes"] += 1

    def _mark_outage(self, bs: _BikeState) -> None:
        if bs.episode and not bs.ep_outage:
            bs.ep_outage = True
            self.flags["outages"]["outage_episodes"] += 1

    def _end_episode(self, bs: _BikeState) -> None:
        bs.episode, bs.ep_outage, bs.swap_target = False, False, None
        self._release_reservation(bs.k)

    def _g_a(self, v: Any, o: Order) -> Optional[int]:
        """Delivery energy ``g_a`` (3) from start node ``v`` for order ``o`` under the
        library's ``energy_rounding``; ``None`` without routes."""
        inst, disc = self.inst, self.inst.disc
        r1, r2 = inst.route(v, o.o), inst.route(o.o, o.d)
        if r1 is None or r2 is None:
            return None
        if self.lib.options.get("energy_rounding", "per_leg") == "concat":
            return disc.g(r1.E_kwh + r2.E_kwh)
        return disc.g(r1.E_kwh) + disc.g(r2.E_kwh)

    def _compute_max_need(self) -> float:
        """``max_need`` of the dead-zone rule: largest ``g_a + min_j gbar(d_i, j) + q_res``
        over all orders and start nodes with routes (``inf`` if some destination
        cannot reach an open swap site).  Static service-area constant (declared as
        fleet knowledge of the area in the module docstring, fairness review F6): it
        uses only restaurant / customer *nodes* of the instance, never release times."""
        best = 0.0
        for o in self.inst.orders:
            gb = self.min_gbar.get(o.d, math.inf)
            for v in self.inst.nodes:
                g_a = self._g_a(v, o)
                if g_a is None:
                    continue
                best = max(best, g_a + gb + self.inst.q_res)
        return best

    def _late_blocked(self, t: int, tau: int, sigma: int) -> bool:
        """``late_threshold_window`` rule: a swap reached after ``tau`` slots and lasting
        ``sigma`` may only be started if it ends by ``H - W``."""
        W = self.p.late_threshold_window
        return W is not None and t + tau + sigma > self.H - W

    def _go_swap(self, bs: _BikeState, t: int) -> str:
        """Route a bike that ``needs_swap`` (threshold / range rule of step 4 or dead-zone
        rule of step 6) at boundary ``t`` (DECISIONS R2.3, ``stock_aware_site``).

        Information set: the bike's own ``(v, t, q)``, the static route / arc
        library and the *current* full stock ``n_jLt`` of every open swap site
        (public station lists) -- minus the other bikes' active reservations when
        ``reservation`` is on (M2); nothing about future arrivals or other bikes.

        Naive rule (``stock_aware_site=False``, round 1): at an open swap site join
        its FIFO queue, elsewhere take the best reposition arc by ``(tau, g, d,
        facility index)``.  Stock-aware rule (default): the candidate set is first
        restricted to open sites with ``n_jLt >= 1`` (a site at the bike's own node
        with stock is taken by queueing there); when no site has stock the naive
        choice is used (``flags['stock_aware_fallbacks']``).  A trip whose
        destination differs from the naive nearest site, or that leaves an empty
        site, counts in ``flags['stock_aware_reroutes']``.  With ``site_choice=
        'LOGIT'`` the choice is :meth:`_go_swap_logit` (M4).  With ``reservation``
        the chosen site's battery is reserved (:meth:`_reserve`, M2).  Outage
        accounting (``flags['outages']``): a decision with no stocked site anywhere
        and a bike arriving at its target site without an issuable battery mark the
        episode as an outage.

        Returns ``'queued'`` (joined / stays in the FIFO queue of the swap site at its
        node, still idle for step 5), ``'moved'`` (took a reposition arc to an open
        swap site), ``'wait'`` (no feasible or unpruned arc: waits one slot, flagged
        ``stranded``) or ``'suppressed'`` (``late_threshold_window`` forbids every
        trip; ``needs_swap`` is reset and the bike stays idle)."""
        if self.p.site_choice == "LOGIT":
            return self._go_swap_logit(bs, t)
        out = self.flags["outages"]
        sc = self.flags["site_choice"]
        here = self.swap_at_node.get(bs.v, [])
        stock_aware = self.p.stock_aware_site
        if here:
            j_here = here[0]                                    # tie by facility index
            sigma_here = self.inst.facility(j_here).sigma
            if bs.queued_at is not None:
                return "queued"                                 # queued bikes never re-route
            if self._late_blocked(t, 0, sigma_here):
                self.flags["late_trips_suppressed"] += 1
                bs.needs_swap = False
                self._end_episode(bs)
                return "suppressed"
            empty_here = self._avail_full(j_here, bs.k) < 1
            if empty_here and bs.swap_target == j_here:
                out["arrivals_to_empty"] += 1
                self._mark_outage(bs)
            if not (stock_aware and empty_here):
                self._join_queue(bs, j_here, t)
                return "queued"
            # stock-aware: empty site here -> try a stocked site elsewhere, else queue here
        cands: List[Tuple[Tuple[int, int, float, int], bool, Arc, Any]] = []   # (naive key, stocked, arc, j)
        any_unpruned = False
        any_late = False
        for j in self.open_swap:
            f = self.inst.facility(j)
            vj = f.node
            if vj == bs.v:
                continue
            tau, g, d = self.inst.tau(bs.v, vj), self.inst.g(bs.v, vj), self.inst.d(bs.v, vj)
            if tau is None or bs.q < g or t + tau > self.H:
                continue
            if self._late_blocked(t, tau, f.sigma):
                any_late = True
                continue
            stocked = self._avail_full(j, bs.k) >= 1
            if here and stock_aware and not stocked:
                continue                                        # no better than queueing here
            any_unpruned = True
            arc = self.lib.find(bs.k, "move", (bs.v, t, bs.q), dst=(vj, t + tau, bs.q - g))
            if arc is None:
                continue
            cands.append(((tau, g, d, self.fidx[j]), stocked, arc, j))
        if cands:
            naive = min(cands, key=lambda c: c[0])
            choice = naive
            stocked_cands = [c for c in cands if c[1]]
            if not stocked_cands:
                out["decisions_without_stock"] += 1
                self._mark_outage(bs)
            if stock_aware:
                if stocked_cands:
                    choice = min(stocked_cands, key=lambda c: c[0])
                else:
                    self.flags["stock_aware_fallbacks"] += 1
                if here or choice[3] != naive[3]:
                    self.flags["stock_aware_reroutes"] += 1
            self._take(bs, choice[2])
            sc["decisions"][choice[3]] += 1
            bs.swap_target = choice[3]
            self._reserve(bs, choice[3], t)
            return "moved"
        if here:                                                # stock-aware fallback: queue here
            self.flags["stock_aware_fallbacks"] += 1
            out["decisions_without_stock"] += 1
            self._mark_outage(bs)
            self._join_queue(bs, here[0], t)
            return "queued"
        if any_late and not any_unpruned:
            self.flags["late_trips_suppressed"] += 1
            bs.needs_swap = False
            self._end_episode(bs)
            return "suppressed"
        reason = "pruned" if any_unpruned else "no_feasible_reposition"
        if any_unpruned:
            self._pruned(bs.k, t, "move", "to swap site")
        self.flags["stranded"].append((bs.k, t, reason))
        if bs.k not in self.flags["stranded_bikes"]:
            self.flags["stranded_bikes"].append(bs.k)
        self._wait(bs, t)
        return "wait"

    def _join_queue(self, bs: _BikeState, j: Any, t: int) -> None:
        """Join the FIFO swap queue of site ``j`` (at the bike's node) at boundary ``t``;
        records the choice (M4 shares) and reserves a battery when ``reservation`` is on."""
        self.queue[j].append(bs.k)
        bs.queued_at, bs.queue_since = j, t
        if bs.swap_target != j:                    # arriving at the chosen site is not a new choice
            self.flags["site_choice"]["decisions"][j] += 1
        bs.swap_target = j
        self.flags["site_choice"]["queue_joins"][j] += 1
        self._reserve(bs, j, t)

    # ------------------------------------------------ round 5: logit site choice (M4)
    def swap_rate(self, j: Any, t: int, lookback: Optional[int] = None) -> float:
        """Observed swap rate at ``j`` per slot (M3 / M4): swaps issued at ``j`` in ``(t -
        lookback, t]`` divided by ``w = min(lookback, t + 1)`` (past information only;
        swaps of boundary ``t`` count once step 5 has run).  Before any observed swap
        at a swap site, ``transfer_prior_rate`` is used.  ``lookback`` defaults to
        ``transfer_lookback``."""
        lb = int(self.p.transfer_lookback if lookback is None else lookback)
        w = min(lb, t + 1)
        swaps = sum(self.swaps_by_slot[j][tau] for tau in range(t - w + 1, t + 1))
        if swaps <= 0 and self.inst.facility(j).swap and self.y.get(j) == 1:
            seen = sum(self.swaps_by_slot[j][tau] for tau in range(0, t + 1))
            if seen == 0:
                return float(self.p.transfer_prior_rate)
        return swaps / w if w > 0 else 0.0

    def site_utility(self, bs: _BikeState, j: Any, tau: int, t: int) -> Tuple[float, Dict[str, float]]:
        """M4 utility of swap site ``j`` for bike ``bs`` reached after ``tau`` slots
        (IJCAI-15 Sec. 3.2: travel + queueing time + a stock-out term):
        ``U_j = -(alpha tau + beta W_j + gamma R_j)``; see :class:`BaselineParams`."""
        f = self.inst.facility(j)
        rate_srv = max(1, int(f.M)) / max(1, int(f.sigma))
        if self.p.expected_wait is not None:
            wait = float(self.p.expected_wait.get(j, self.p.expected_wait.get(str(j), 0.0)))
        else:
            wait = len(self.queue[j]) / rate_srv
        avail = self._avail_full(j, bs.k) - len(self.queue[j])
        lam = self.swap_rate(j, t) * tau
        risk = 1.0 if avail <= 0 else poisson_sf(lam, avail)
        u = -(self.p.logit_alpha * tau + self.p.logit_beta * wait + self.p.logit_gamma * risk)
        return u, {"tau": float(tau), "wait": wait, "risk": risk}

    def _go_swap_logit(self, bs: _BikeState, t: int) -> str:
        """M4 self-interested station choice (IJCAI-15): among the open swap sites the bike
        can reach (own site with ``tau = 0`` by queueing, others by an unpruned
        reposition arc with ``q >= g`` and ``t + tau <= H``, ``late_threshold_window``
        respected), draw one from the multinomial logit ``P_j ~ exp(U_j / scale)``
        (:meth:`site_utility`) with the private stream ``(choice_seed, bike, t)``.  A bike
        arriving at the site it chose queues there when a battery is issuable to it, and
        chooses again (an ``arrivals_to_empty`` outage) when not.  Same return values and
        outage accounting as :meth:`_go_swap`."""
        out = self.flags["outages"]
        sc = self.flags["site_choice"]
        if bs.queued_at is not None:
            return "queued"
        here = self.swap_at_node.get(bs.v, [])
        opts: List[Tuple[Any, int, Optional[Arc]]] = []      # (j, tau, arc or None = queue here)
        any_unpruned = any_late = False
        for j in self.open_swap:
            f = self.inst.facility(j)
            if f.node == bs.v:
                if j != here[0]:
                    continue                                # one queue per node (index tie)
                if self._late_blocked(t, 0, f.sigma):
                    any_late = True
                    continue
                any_unpruned = True
                opts.append((j, 0, None))
                continue
            tau, g = self.inst.tau(bs.v, f.node), self.inst.g(bs.v, f.node)
            if tau is None or bs.q < g or t + tau > self.H:
                continue
            if self._late_blocked(t, tau, f.sigma):
                any_late = True
                continue
            any_unpruned = True
            arc = self.lib.find(bs.k, "move", (bs.v, t, bs.q), dst=(f.node, t + tau, bs.q - g))
            if arc is None:
                continue
            opts.append((j, tau, arc))
        if here and bs.swap_target == here[0]:
            j0 = here[0]
            if self._avail_full(j0, bs.k) < 1:
                out["arrivals_to_empty"] += 1              # chosen site empty on arrival: choose again
                self._mark_outage(bs)
            elif not self._late_blocked(t, 0, self.inst.facility(j0).sigma):
                self._join_queue(bs, j0, t)                # arrived at the chosen, stocked site
                return "queued"
        if opts:
            if not any(self._avail_full(j, bs.k) >= 1 for j, _, _ in opts):
                out["decisions_without_stock"] += 1
                self._mark_outage(bs)
            utils = [self.site_utility(bs, j, tau, t)[0] for j, tau, _ in opts]
            probs = logit_probabilities(utils, self.p.logit_scale)
            rng = random.Random(f"logit:{int(self.p.choice_seed)}:{self.kidx[bs.k]}:{t}")
            sc["logit_draws"] += 1
            r, acc, pick = rng.random(), 0.0, len(opts) - 1
            for idx, pr in enumerate(probs):
                acc += pr
                if r < acc:
                    pick = idx
                    break
            j, tau, arc = opts[pick]
            if arc is None:
                self._join_queue(bs, j, t)
                return "queued"
            self._take(bs, arc)
            sc["decisions"][j] += 1
            bs.swap_target = j
            self._reserve(bs, j, t)
            return "moved"
        if any_late and not any_unpruned:
            self.flags["late_trips_suppressed"] += 1
            bs.needs_swap = False
            self._end_episode(bs)
            return "suppressed"
        reason = "pruned" if any_unpruned else "no_feasible_reposition"
        if any_unpruned:
            self._pruned(bs.k, t, "move", "to swap site")
        self.flags["stranded"].append((bs.k, t, reason))
        if bs.k not in self.flags["stranded_bikes"]:
            self.flags["stranded_bikes"].append(bs.k)
        self._wait(bs, t)
        return "wait"

    # --------------------------------------------- round 5: range-aware trigger (M2)
    def _g_cached(self, v: Any, o: Order) -> Optional[int]:
        key = (v, o.id)
        if key not in self._g_cache:
            self._g_cache[key] = self._g_a(v, o)
        return self._g_cache[key]

    def gbar_stocked(self, x: Any, k: Any = None) -> float:
        """M2: least energy ``gbar(x, j)`` from node ``x`` to an open swap site with
        reservable full stock for bike ``k`` now (all open sites when none has stock)."""
        vals = [self.lib.gbar.get((x, j), math.inf) for j in self.open_swap if self._avail_full(j, k) >= 1]
        if not vals:
            return self.min_gbar.get(x, math.inf)
        return min(vals)

    def range_need(self, bs: _BikeState, t: int) -> Tuple[float, str]:
        """M2 energy requirement (levels) of bike ``bs`` at boundary ``t`` and its source:
        ``('next_order')`` ``g_a(v, i) + gbar_stocked(d_i) + q_res`` for the FIFO head
        ``i`` of the released queue routable from ``v``; ``('typical')`` the upper
        median of that quantity over the typical orders (``range_typical``);
        ``('no_order')`` ``gbar_stocked(v) + q_res``.  Information: see the module
        docstring (orders with ``r_i <= t`` only, unless ``range_typical='static'``)."""
        q_res = self.inst.q_res
        for i in self.Q:
            o = self.inst.order(i)
            g = self._g_cached(bs.v, o)
            if g is None:
                continue
            return g + self.gbar_stocked(o.d, bs.k) + q_res, "next_order"
        if self.p.range_typical == "static":
            pool = self.inst.orders
        else:
            pool = [o for o in self.inst.orders if o.r <= t]
        reach: Dict[Any, float] = {}
        vals: List[float] = []
        for o in pool:
            g = self._g_cached(bs.v, o)
            if g is None:
                continue
            if o.d not in reach:
                reach[o.d] = self.gbar_stocked(o.d, bs.k)
            vals.append(g + reach[o.d] + q_res)
        if vals:
            vals.sort()
            return vals[len(vals) // 2], "typical"
        return self.gbar_stocked(bs.v, bs.k) + q_res, "no_order"

    def _swap_trigger(self, bs: _BikeState, t: int) -> bool:
        """Step 4 trigger: ``THRESHOLD`` ``q <= q_thr`` (round 1/2) or the M2 ``RANGE``
        rule ``q < min(range_need + range_margin, ceil(range_cap_frac L))``."""
        if bs.q >= self.L:
            return False
        if self.p.swap_rule == "THRESHOLD":
            return bs.q <= self.q_thr
        cap = int(math.ceil(float(self.p.range_cap_frac) * self.L - _FLOOR_TOL))
        need, src = self.range_need(bs, t)
        level = min(need + int(self.p.range_margin), cap)
        if bs.q < level:
            rr = self.flags["range_rule"]
            rr["triggers"] += 1
            rr["by_source"][src] += 1
            return True
        return False

    def _delivery_unpruned(self, v: Any, t: int, q: int, o: Order) -> bool:
        """Would the delivery arc ``(v, t, q)`` for order ``o`` exist by (2)-(4) alone
        (plus the lossless dominance rule)?  Used to tell a pruned arc from one
        that never existed."""
        inst, disc = self.inst, self.inst.disc
        r1, r2 = inst.route(v, o.o), inst.route(o.o, o.d)
        if r1 is None or r2 is None or t < o.r:
            return False
        tau1 = disc.tau(r1.T_h, distinct=v != o.o)
        tau2 = disc.tau(r2.T_h, distinct=o.o != o.d)
        arrive = t + tau1
        if self.lib.options.get("dominance", True) and arrive < o.a:
            return False
        if self.lib.options.get("energy_rounding", "per_leg") == "concat":
            g_a = disc.g(r1.E_kwh + r2.E_kwh)
            if arrive >= o.a:
                u_a = t + disc.tau(r1.T_h + r2.T_h, distinct=(v != o.o or o.o != o.d)) + o.hp + o.hd
            else:
                u_a = o.a + o.hp + tau2 + o.hd
        else:
            g_a = disc.g(r1.E_kwh) + disc.g(r2.E_kwh)
            u_a = max(arrive, o.a) + o.hp + tau2 + o.hd
        return q >= g_a and u_a <= self.H

    # ------------------------------------------------------------ main loop
    def run(self) -> Tuple[Schedule, Dict[str, Any]]:
        H = self.H
        orders_sorted = sorted(self.inst.orders, key=lambda o: (o.r, self.oidx[o.id]))
        release_at: Dict[int, List[Any]] = defaultdict(list)
        for o in orders_sorted:
            release_at[o.r].append(o.id)
        for t in range(H):
            self._record_stock(t)                                  # step 1
            self.Q.extend(release_at.get(t, ()))                   # step 2
            idle = [k for k in self.bikes if self.bikes[k].free_at == t]   # step 3 (index order)
            idle = self._step4_threshold(idle, t)
            idle = self._step5_fcfs_swaps(idle, t)
            idle = self._step6_dispatch(idle, t)
            self._step7_remaining(idle, t)
            if self.forced:
                self._step8_forced(t)
            if self.transfer_rule != "NONE":
                self._step8_transfers(t)
            self._step9_charging(t)
            self._step10_inventory_step(t)
        self._record_stock(H)
        return self._finish()                                      # steps 11-14

    # step 1 ---------------------------------------------------------------
    def _record_stock(self, t: int) -> None:
        """``n_hist[j,q,t] = n_jqt``: stock after arrivals at ``t``, before new actions (13)."""
        for j, row in self.n.items():
            for q in range(self.L + 1):
                self.n_hist[(j, q, t)] = row[q]

    # step 4 ---------------------------------------------------------------
    def _step4_threshold(self, idle: List[Any], t: int) -> List[Any]:
        """Rider threshold rule: idle bikes with ``q <= q_thr < L`` need a swap; at an
        open swap site they join its FIFO queue, elsewhere they take the best
        reposition arc (``tau``, then ``g``, then ``d``, then facility index) to an
        open swap site; with no feasible arc they wait (flag ``stranded``).  Routing
        (and the ``stock_aware_site`` / ``late_threshold_window`` variants) is
        :meth:`_go_swap`.

        Round 5: the trigger is :meth:`_swap_trigger` (``THRESHOLD`` or the M2
        ``RANGE`` rule); expired reservations are dropped first (M2), and in a
        compliance run the compliant bikes take their planned arcs before any policy
        rule (:meth:`_step_compliant`).  These hooks live inside step 4 so that the
        slot loop of :meth:`run` (mirrored by ``rl_env._StationRun``) is unchanged."""
        self._expire_reservations(t)
        if self.plan_orders:                       # orders held for compliant bikes never enter Q
            self.Q = [i for i in self.Q if i not in self.plan_orders]
        if self.compliant:
            idle = self._step_compliant(idle, t)
        still_idle: List[Any] = []
        for k in idle:
            bs = self.bikes[k]
            if not bs.needs_swap and self._swap_trigger(bs, t):
                bs.needs_swap = True
            if bs.needs_swap:
                self._start_episode(bs)
            if not bs.needs_swap:
                still_idle.append(k)
                continue
            outcome = self._go_swap(bs, t)
            if outcome in ("queued", "suppressed"):
                still_idle.append(k)                 # queued: served by step 5; suppressed: dispatchable
        return still_idle

    # step 5 ---------------------------------------------------------------
    def _step5_fcfs_swaps(self, idle: List[Any], t: int) -> List[Any]:
        """FCFS swap service (station rule): for each open swap site, queued bikes in
        arrival order get a swap when (14), (22), ``t + sigma_j <= H`` and the arc
        allow it; otherwise they wait one slot and keep their queue position."""
        served: set = set()
        for j in self.open_swap:
            q_list = list(self.queue[j])
            remaining: List[Any] = []
            for k in q_list:
                bs = self.bikes[k]
                if bs.free_at != t:        # defensive: queued bikes are always idle
                    remaining.append(k)
                    continue
                if self._try_swap(bs, j, t):
                    bs.queued_at, bs.queue_since = None, None
                else:
                    self._queue_wait_reason(bs, j)
                    self._wait(bs, t)
                    self.flags["wait_slots_in_queue"][j] += 1
                    remaining.append(k)
                served.add(k)
            self.queue[j] = remaining
        return [k for k in idle if k not in served]

    def _queue_wait_reason(self, bs: _BikeState, j: Any) -> None:
        """Outage accounting of one queued wait slot at ``j`` (M2 / A3): no issuable full
        battery for this bike (14) -> stock-out slot (the episode is an outage), else a
        position / horizon block (22)."""
        out = self.flags["outages"]
        if j is not None and self._avail_full(j, bs.k) < 1:
            out["stockout_queue_slots"] += 1
            self._mark_outage(bs)
        else:
            out["position_queue_slots"] += 1

    # step 3a (compliance runs only) -----------------------------------------
    def _step_compliant(self, idle: List[Any], t: int) -> List[Any]:
        """Compliant bikes of :func:`simulate_compliance` take their next planned arc
        (same arc ids as the plan; the plan's swaps draw from the live stock and
        positions through :meth:`_try_swap`).  A planned swap that the live state
        cannot honour (no issuable battery (14), no position (22)) makes the bike
        *defect*: from then on it is a policy bike and its planned but not yet started
        orders return to the policy queue ``Q`` (``flags['compliance']['defected']``).
        Returns the idle bikes left for the policy (non-compliant or defected)."""
        rest: List[Any] = []
        comp = self.flags["compliance"]
        for k in idle:
            plan = self.compliant.get(k)
            if plan is None:
                rest.append(k)
                continue
            bs = self.bikes[k]
            arc = plan[0] if plan else None
            if arc is None or arc.kind == "term" or arc.src != (bs.v, t, bs.q):
                self._defect(k, t, "plan_mismatch")
                rest.append(k)
                continue
            if arc.kind == "swap":
                if not self._try_swap(bs, arc.fac, t):
                    reason = "no_battery" if self._avail_full(arc.fac, k) < 1 else "no_position"
                    self._defect(k, t, reason)
                    rest.append(k)
                    continue
                plan.pop(0)
                comp["planned_swaps_done"] += 1
                continue
            if arc.kind == "deliver":
                self.assigned[arc.order] = (k, arc.u)
                self.plan_orders.pop(arc.order, None)
            self._take(bs, arc)
            plan.pop(0)
        return rest

    def _defect(self, k: Any, t: int, reason: str) -> None:
        """Turn compliant bike ``k`` into a policy bike at ``t`` (see :meth:`_step_compliant`)."""
        self.compliant.pop(k, None)
        self.plan_terminal.pop(k, None)
        self.flags["compliance"]["defected"].append((k, t, reason))
        back = [i for i, kk in self.plan_orders.items() if kk == k]
        for i in back:
            del self.plan_orders[i]
            if self.inst.order(i).r <= t:
                self.Q.append(i)
        if back:
            self.Q.sort(key=lambda i: (self.inst.order(i).r, self.oidx[i]))

    # step 6 ---------------------------------------------------------------
    def _jit_delivery_arc(self, bs: _BikeState, o: Order, t: int) -> Optional[Arc]:
        """Just-in-time candidate (reviewer F1): when the delivery arc from ``(v, t, q)``
        is absent *only* because of the dominance rule (``t + tau_r < a_i``, library
        built with ``dominance=True``), return the library's arc from ``(v, a_i -
        tau_r, q)`` (same ``u_a``, ``g_a``, ``theta`` by (2)-(3)); ``None`` when the
        arc is missing for another reason (energy, horizon, pruning)."""
        if not self.lib.options.get("dominance", True):
            return None                       # nothing was dropped: the arc is really absent
        r1 = self.inst.route(bs.v, o.o)
        if r1 is None or t < o.r:
            return None
        tau1 = self.inst.disc.tau(r1.T_h, distinct=bs.v != o.o)
        if t + tau1 >= o.a:
            return None
        t_start = o.a - tau1                  # > t and >= r_i (a_i >= r_i)
        arc = self.lib.find(bs.k, "deliver", (bs.v, t_start, bs.q), order=o.id)
        if arc is None and self._delivery_unpruned(bs.v, t_start, bs.q, o):
            self._pruned(bs.k, t, "deliver", (o.id, "jit", t_start))
        return arc

    def _step6_dispatch(self, idle: List[Any], t: int) -> List[Any]:
        """Nearest-feasible-rider dispatch, order FIFO by ``(r_i, i)``: candidates are
        idle bikes not needing a swap whose delivery arc exists in the library
        ((2)-(4) and the ILP pruning) -- or, with ``jit_dispatch``, whose arc is
        absent only by the dominance rule and exists from ``(v, a_i - tau_r, q)``
        (:meth:`_jit_delivery_arc`) -- and that keep enough energy to certify (9)
        after the delivery; tie-break ``(tau(v_k -> o_i), d, bike index)``; with
        ``dispatch_scope='zone'`` same-zone candidates are preferred.  The chosen
        bike commits wait arcs up to the arc start (just-in-time) and the delivery
        arc, and is busy until ``u_a``.  With ``swap_on_reach_refusal`` a bike
        refused solely by the reach guard, left idle and with ``q <= max_need``
        is routed to a swap site (:meth:`_go_swap`) at this boundary."""
        idle_set = list(idle)
        reach_refused: Dict[Any, Any] = {}      # bike -> first order refused for the reach reason
        for i in list(self.Q):
            o = self.inst.order(i)
            cands: List[Tuple[Tuple[int, float, int], Any, Arc]] = []
            for k in idle_set:
                bs = self.bikes[k]
                if bs.needs_swap:
                    continue
                arc = self.lib.find(k, "deliver", (bs.v, t, bs.q), order=i)
                if arc is None:
                    if self.p.jit_dispatch:
                        arc = self._jit_delivery_arc(bs, o, t)
                    elif self._delivery_unpruned(bs.v, t, bs.q, o):
                        self._pruned(k, t, "deliver", i)
                    if arc is None:
                        continue
                if self.p.require_post_delivery_reach:
                    need = self.min_gbar.get(o.d, math.inf) + self.inst.q_res
                    if need == math.inf and self.lib.has_dummy_terminal:
                        pass                      # only a dummy terminal can close the path anyway
                    elif bs.q - arc.g < need:
                        reach_refused.setdefault(k, i)
                        continue
                tau = self.inst.tau(bs.v, o.o)
                d = self.inst.d(bs.v, o.o)
                cands.append(((tau if tau is not None else 10 ** 9, d if d is not None else math.inf,
                               self.kidx[k]), k, arc))
            if not cands:
                continue                           # order stays in Q
            if self.p.dispatch_scope == "zone" and self.node_zone is not None:
                zone = self.node_zone.get(o.o)
                same = [c for c in cands if self.node_zone.get(self.bikes[c[1]].v) == zone]
                if same:
                    cands = same
            cands.sort(key=lambda c: c[0])
            _, k_star, arc = cands[0]
            bs_star = self.bikes[k_star]
            if arc.l > t:                          # just-in-time start: wait at v until a_i - tau_r
                for tt in range(t, arc.l):
                    self._wait(bs_star, tt)
                self.flags["jit_dispatches"] += 1
            self._take(bs_star, arc)
            self.assigned[i] = (k_star, arc.u)
            self.Q.remove(i)
            idle_set.remove(k_star)
        # dead-zone rule (reviewer F2): reach-only refusals of bikes left idle
        for k, i in reach_refused.items():
            if k not in idle_set:
                continue                           # dispatched to another order after all
            bs = self.bikes[k]
            rec = self.flags["reach_refusals"]
            rec["count"] += 1
            if len(rec["examples"]) < _MAX_EXAMPLES:
                rec["examples"].append((k, t, i, bs.q))
            if not self.p.swap_on_reach_refusal or bs.q > self.max_need or bs.q >= self.L:
                continue
            bs.needs_swap = True
            self._start_episode(bs)
            outcome = self._go_swap(bs, t)
            if outcome == "queued":                # step 5 has run: wait this slot in the queue
                self._queue_wait_reason(bs, bs.queued_at)
                self._wait(bs, t)
                self.flags["wait_slots_in_queue"][bs.queued_at] += 1
            if outcome != "suppressed":
                rec["bikes_sent_to_swap"] += 1
                idle_set.remove(k)
        return idle_set

    # step 7 ---------------------------------------------------------------
    def _step7_remaining(self, idle: List[Any], t: int) -> None:
        """Remaining idle bikes wait one slot; with ``opportunistic_swap`` a bike at an
        open swap site with ``q < L`` swaps first if stock and a position allow it."""
        for k in idle:
            bs = self.bikes[k]
            if bs.free_at != t:
                continue
            if self.p.opportunistic_swap and bs.q < self.L:
                done = False
                for j in self.swap_at_node.get(bs.v, []):
                    if self._try_swap(bs, j, t):
                        done = True
                        break
                if done:
                    continue
            self._wait(bs, t)

    # step 8 ---------------------------------------------------------------
    def _inbound(self, j: Any, t: int, full_only: bool = False, by: Optional[int] = None) -> int:
        """Batteries already dispatched to ``j`` that arrive after ``t`` (and by ``by``)."""
        tot = 0
        for (u, q, cnt) in self.pending_arrivals[j]:
            if u > t and (by is None or u <= by) and (not full_only or q == self.L):
                tot += cnt
        return tot

    def _stock_total(self, j: Any) -> int:
        return sum(self.n[j])

    def _step8_transfers(self, t: int) -> None:
        """REORDER_POINT transfer rule for services departing at ``t`` (10)-(11).

        Hub -> swap site: ship full batteries when ``n_jLt + incoming_full <= s_j``;
        swap site -> hub: ship the non-full batteries, lowest level first.  Loads are
        bounded by ``U_e``, the origin's beginning stock after this boundary's swaps
        (14), and the destination's free storage at arrival (15):
        ``K_d y_d - N_d(t) - inbound``.  Departures draw from stock before charging.
        Reserved full batteries (M2) are never shipped.  ``COST_AWARE`` (M3) is
        :meth:`_step8_cost_aware`; ``PLAN`` (compliance runs) is :meth:`_step8_plan`.
        """
        if self.transfer_rule == "COST_AWARE":
            self._step8_cost_aware(t)
            return
        if self.transfer_rule == "PLAN":
            self._step8_plan(t)
            return
        L = self.L
        for svc in self.inst.services:
            if svc.l != t or svc.id in self.forced:
                continue
            o_fac, d_fac = svc.o_fac, svc.d_fac
            if self.y[o_fac] != 1 or self.y[d_fac] != 1:
                continue
            fo, fd = self.inst.facility(o_fac), self.inst.facility(d_fac)
            room = fd.K * self.y[d_fac] - self._stock_total(d_fac) - self._inbound(d_fac, t)
            cap = min(svc.U, room)
            if cap <= 0:
                continue
            loads: Dict[int, int] = {}
            if fo.charge and fd.swap:
                by = svc.u if self.p.reorder_lead is None else t + self.p.reorder_lead
                if self.n[d_fac][L] + self._inbound(d_fac, t, full_only=True, by=by) <= self.p.s_j(d_fac):
                    reserve_o = self.p.s_j(o_fac) if fo.swap else 0
                    avail = self._avail_full(o_fac) - reserve_o
                    zL = min(cap, avail)
                    if zL >= 1:
                        loads[L] = zL
            elif fo.swap and fd.charge:
                left = cap
                for q in range(L):
                    if left <= 0:
                        break
                    zq = min(self.n[o_fac][q], left)
                    if zq >= 1:
                        loads[q] = zq
                        left -= zq
            if not loads:
                continue
            self.h[svc.id] = 1
            for q, val in loads.items():
                self.z[(svc.id, q)] = self.z.get((svc.id, q), 0) + val
                self.D[(o_fac, q, t)] += val
                self.A[(d_fac, q, svc.u)] += val
                self.n[o_fac][q] -= val
                self.pending_arrivals[d_fac].append((svc.u, q, val))

    def _step8_forced(self, t: int) -> None:
        """Execute the data-forced transfers departing at ``t`` (plan item M9, battery
        lock-out of ``generator.add_battery_lockout``; E2 (10)-(11) with ``h_e = 1``).

        Each forced service moves exactly one battery (``U_e = 1``): the level given in
        ``options['forced_transfers']`` (``L`` for ``level='full'``), else the lowest-level
        battery in stock at the origin (a full one only if no non-full battery is left).
        Full batteries reserved by other bikes (M2) are taken last.  A forced service
        whose origin has no battery at ``t`` is recorded in
        ``flags['forced_transfers']['missed']`` (the ILP would be infeasible there).
        Runs before the voluntary rule of step 8, which never touches forced services."""
        L = self.L
        ft = self.flags["forced_transfers"]
        for svc in self.inst.services:
            if svc.l != t or svc.id not in self.forced:
                continue
            o_fac = svc.o_fac
            want = self.forced[svc.id]
            q_pick: Optional[int] = None
            if want is not None:
                if self.n[o_fac][want] >= 1:
                    q_pick = want
            else:
                for q in range(L):
                    if self.n[o_fac][q] >= 1:
                        q_pick = q
                        break
                if q_pick is None and self.n[o_fac][L] >= 1:
                    q_pick = L
            if q_pick is None:
                ft["missed"].append((svc.id, t))
                continue
            self._ship(svc, {q_pick: 1}, t)
            ft["executed"] += 1
            ft["loads"].append((svc.id, t, q_pick))

    def _ship(self, svc: Any, loads: Dict[int, int], t: int) -> None:
        """Book a service departure at ``t`` with ``{q: z_eq}`` (10)-(11): ``h_e = 1``,
        ``D_{o,q,t}``, ``A_{d,q,u_e}``, origin stock, pending arrival."""
        self.h[svc.id] = 1
        for q, val in loads.items():
            self.z[(svc.id, q)] = self.z.get((svc.id, q), 0) + val
            self.D[(svc.o_fac, q, t)] += val
            self.A[(svc.d_fac, q, svc.u)] += val
            self.n[svc.o_fac][q] -= val
            self.pending_arrivals[svc.d_fac].append((svc.u, q, val))

    def _room(self, svc: Any, t: int) -> int:
        """Free storage (15) at the destination for a load arriving at ``u_e`` (same
        conservative bound as the REORDER_POINT rule)."""
        fd = self.inst.facility(svc.d_fac)
        return fd.K * self.y[svc.d_fac] - self._stock_total(svc.d_fac) - self._inbound(svc.d_fac, t)

    # ------------------------------------------ round 5: cost-aware transfers (M3)
    def _charge_cap_site(self, j: Any) -> int:
        f = self.inst.facility(j)
        return min(self.C[j], int(math.floor(f.P_kw * self.y[j] / self.inst.disc.p_ch_kw + _FLOOR_TOL)))

    def chargeable_within(self, j: Any, window: int, extra_steps: int = 0) -> int:
        """M3: number of non-full batteries at ``j`` (stock + batteries returned at this
        boundary) that ``j``'s own chargers can bring to ``L`` within ``window`` slots
        (aggregate charge-step budget ``cap_j x window`` minus ``extra_steps``, most
        advanced batteries first, each needing ``L - q <= window`` steps; caps (20))."""
        if j not in self.open_charge or window <= 0:
            return 0
        cap = self._charge_cap_site(j)
        budget = cap * int(window) - int(extra_steps)
        if budget <= 0:
            return 0
        cnt = 0
        for q in range(self.L - 1, -1, -1):
            need = self.L - q
            if need > window:
                break
            m = self.n[j][q] + self.hold[j][q]
            take = min(m, budget // need)
            cnt += take
            budget -= take * need
            if take < m:
                break
        return cnt

    def _reserve_target(self, j: Any, t: int, window: int) -> int:
        """End reserve counted by M3 at ``j`` for a window ``(t, t + window]``:
        ``R_end_j y_j`` (17) at swap sites when ``transfer_reserve='always'`` or when
        the window reaches ``H`` (``'end'``, default); 0 for ``'none'`` and hubs."""
        f = self.inst.facility(j)
        mode = self.p.transfer_reserve
        if not f.swap or mode == "none" or (mode == "end" and t + window < self.H):
            return 0
        return int(f.R_end * self.y[j])

    def _known_requests(self, j: Any) -> int:
        """Swap requests at ``j`` known now and not yet backed by stock: bikes queued at
        ``j`` without a reservation there (with reservations the holders are already
        netted out of :meth:`_avail_full`)."""
        r = self.resv.get(j, {})
        return sum(1 for k in self.queue.get(j, ()) if k not in r)

    def full_supply(self, j: Any, t: int, window: int) -> int:
        """M3 supply of full batteries at ``j`` over ``(t, t + window]`` net of known
        requests and of its end reserve: issuable full stock + full batteries already
        dispatched to ``j`` and arriving by ``t + window`` + :meth:`chargeable_within`
        - bikes queued at ``j`` (:meth:`_known_requests`) - :meth:`_reserve_target` (17)."""
        return (self._avail_full(j) + self._inbound(j, t, full_only=True, by=t + window)
                + self.chargeable_within(j, window) - self._known_requests(j)
                - self._reserve_target(j, t, window))

    def stockout_value(self) -> float:
        """M3 value ``V`` of one avoided stock-out (static tariff data of (31)):
        ``mean P_i x orders_per_stockout`` or ``mean w_i x Delta x stockout_wait_slots``."""
        orders = self.inst.orders
        if not orders:
            return 0.0
        if self.p.stockout_cost_mode == "P":
            return float(sum(o.P for o in orders)) / len(orders) * float(self.p.orders_per_stockout)
        slots = self.L if self.p.stockout_wait_slots is None else int(self.p.stockout_wait_slots)
        return float(sum(o.w for o in orders)) / len(orders) * self.inst.disc.Delta_h * slots

    def cost_aware_candidates(self, svc: Any, t: int) -> List[Tuple[float, float, int]]:
        """M3 candidate batteries for service ``svc`` departing at ``t``, as ``(expected
        benefit, marginal cost v_reb_q, level q)`` in shipping order (benefits are
        non-increasing within each kind).

        * Full batteries (``q = L``), ``m = 1, 2, ...`` up to the issuable full stock
          at the origin ``o``: benefit ``V (Pr[N_d >= a_d + m] - Pr[N_o >= a_o - m + 1])``
          with ``N_x ~ Poisson(rate_x W_x)`` the forecast swaps (``rate`` from
          :meth:`swap_rate`), ``W_d = u_e - t + lead`` (the shipment's arrival plus the
          lead window), ``W_o = lead`` and ``a_x`` = :meth:`full_supply` over that
          window: the probability that the ``m``-th battery prevents a stock-out at the
          destination minus the probability that its removal causes one at the origin.
        * Non-full batteries from an origin without chargers to a destination with
          chargers (highest level first): benefit ``V Pr[N_net >= S_net + m]`` with the
          network forecast ``N_net ~ Poisson(sum_j rate_j W_b)`` and network supply
          ``S_net = sum_j full_supply(j, W_b)`` over ``W_b`` = arrival + estimated
          charge completion at ``d`` (``ceil((backlog_d + L - q) / cap_d)``) + lead.
        """
        L, lead = self.L, int(self.p.transfer_lead)
        V = self.stockout_value()
        o, d = svc.o_fac, svc.d_fac
        cands: List[Tuple[float, float, int]] = []
        # full batteries
        Wd = svc.u - t + lead
        lam_d = self.swap_rate(d, t) * Wd if self.inst.facility(d).swap else 0.0
        a_d = self.full_supply(d, t, Wd)
        lam_o = self.swap_rate(o, t) * lead if self.inst.facility(o).swap else 0.0
        a_o = self.full_supply(o, t, lead)
        for m in range(1, max(0, self._avail_full(o)) + 1):
            b = V * (poisson_sf(lam_d, a_d + m) - poisson_sf(lam_o, a_o - m + 1))
            cands.append((b, svc.vreb_q(L), L))
        # non-full batteries (dead stock at an origin without chargers)
        cap_d = self._charge_cap_site(d) if d in self.open_charge else 0
        if cap_d > 0 and (o not in self.open_charge or self._charge_cap_site(o) <= 0):
            backlog = sum((self.n[d][q] + self.hold[d][q]) * (L - q) for q in range(L))
            backlog += sum(cnt * (L - q) for (u, q, cnt) in self.pending_arrivals[d] if u > t and q < L)
            rate_net = sum(self.swap_rate(j, t) for j in self.open_swap)
            m = 0
            for q in range(L - 1, -1, -1):
                for _ in range(self.n[o][q]):
                    m += 1
                    backlog += L - q
                    Wb = svc.u - t + int(math.ceil(backlog / cap_d - _FLOOR_TOL)) + lead
                    supply = sum(self.full_supply(j, t, Wb) for j in self.inst.N if self.y.get(j) == 1)
                    b = V * poisson_sf(rate_net * Wb, supply + m)
                    cands.append((b, svc.vreb_q(q), q))
        return cands

    def _step8_cost_aware(self, t: int) -> None:
        """M3 cost-aware, zero-sum transfer rule (IJCAI-25 action design) for the
        services departing at ``t`` (10)-(11).

        For each service ``e = (o -> d)`` with both ends open, the candidate batteries
        of :meth:`cost_aware_candidates` are ranked by their marginal net value
        ``benefit - v_reb_q`` and taken while it is positive, within ``min(U_e,
        transfer_load_cap, free storage at d (15))``; the load is shipped only if the
        total expected avoided stock-out cost exceeds ``f_e + sum v_reb_q`` (32).
        Batteries only move between sites (surplus -> forecast deficit), so the network
        total is unchanged (zero-sum; identity (24)).  Departures draw from the stock
        left after this boundary's swaps (14); reserved batteries (M2) never leave.
        ``flags['cost_aware']`` records every shipment (``service, t, loads, benefit,
        cost``), the services considered and those rejected by the cost test."""
        ca = self.flags["cost_aware"]
        for svc in self.inst.services:
            if svc.l != t or svc.id in self.forced or self.y[svc.o_fac] != 1 or self.y[svc.d_fac] != 1:
                continue
            ca["considered"] += 1
            cap = min(int(svc.U), self._room(svc, t))
            if self.p.transfer_load_cap is not None:
                cap = min(cap, int(self.p.transfer_load_cap))
            if cap <= 0:
                continue
            cands = self.cost_aware_candidates(svc, t)
            order = sorted(range(len(cands)), key=lambda i: -(cands[i][0] - cands[i][1]))
            loads: Dict[int, int] = {}
            benefit = var_cost = 0.0
            for i in order[:cap]:
                b, c, q = cands[i]
                if b - c <= 0:
                    break
                loads[q] = loads.get(q, 0) + 1
                benefit += b
                var_cost += c
            if not loads:
                continue
            if benefit - var_cost <= float(svc.f):
                ca["rejected_by_cost"] += 1
                continue
            self._ship(svc, loads, t)
            ca["shipments"].append({"service": svc.id, "t": t, "loads": dict(loads),
                                    "benefit": benefit, "cost": float(svc.f) + var_cost})

    # ------------------------------------------- compliance runs: plan replay
    def _step8_plan(self, t: int) -> None:
        """Replay the plan's service loads ``z_eq`` at ``t`` (compliance runs with
        ``station_plan='plan'``), clipped to the live issuable stock (14) and the free
        storage at the destination (15); clipping is recorded in
        ``flags['compliance']['clipped_loads']``."""
        st = self.plan_station or {}
        z, h = st.get("z", {}), st.get("h", {})
        for svc in self.inst.services:
            if (svc.l != t or svc.id in self.forced or not h.get(svc.id, 0)
                    or self.y[svc.o_fac] != 1 or self.y[svc.d_fac] != 1):
                continue
            left = min(int(svc.U), self._room(svc, t))
            loads: Dict[int, int] = {}
            clipped = 0
            for q in range(self.L, -1, -1):
                want = int(z.get((svc.id, q), 0))
                if want <= 0:
                    continue
                have = self._avail_full(svc.o_fac) if q == self.L else self.n[svc.o_fac][q]
                val = max(0, min(want, have, left))
                clipped += want - val
                if val:
                    loads[q] = val
                    left -= val
            if clipped:
                self.flags["compliance"]["clipped_loads"] += clipped
            if loads:
                self._ship(svc, loads, t)

    def _step9_plan(self, t: int) -> None:
        """Replay the plan's charging ``c_jqt`` (compliance runs, ``station_plan='plan'``)
        clipped to the live stock (14) and the caps (20)-(21); clipped steps are
        recorded in ``flags['compliance']['clipped_charge']``."""
        c_plan = (self.plan_station or {}).get("c", {})
        p_ch = self.inst.disc.p_ch_kw
        group_left: Dict[Any, int] = {}
        for j in self.open_charge:
            f = self.inst.facility(j)
            self.flags["charge_rule_effective"][j] = "PLAN"
            left = self._charge_cap_site(j)
            if f.group is not None and f.group not in group_left:
                lim = self.inst.grid_limit(f.group, t)
                group_left[f.group] = (10 ** 9 if lim == math.inf
                                       else int(math.floor(lim / p_ch + _FLOOR_TOL)))
            for q in range(self.L - 1, -1, -1):
                want = int(c_plan.get((j, q, t), 0))
                if want <= 0:
                    continue
                lim_g = group_left[f.group] if f.group is not None else 10 ** 9
                cq = max(0, min(want, self.n[j][q], left, lim_g))
                if want - cq:
                    self.flags["compliance"]["clipped_charge"] += want - cq
                if cq <= 0:
                    continue
                self.c[(j, q, t)] = cq
                left -= cq
                if f.group is not None:
                    group_left[f.group] -= cq

    # step 9 ---------------------------------------------------------------
    def _charge_rule_for(self, j: Any) -> str:
        """Charging rule applied at charge site ``j``: ``charge_rule``, except that
        under DEMAND_AWARE a charge-only hub (``j in C \\ S``, which never observes
        a swap) uses ``hub_charge_rule`` (R2.3 gap, see :class:`BaselineParams`)."""
        rule = self.p.charge_rule
        if rule == "DEMAND_AWARE" and not self.inst.facility(j).swap:
            rule = self.p.hub_charge_rule
        return rule

    def forecast_swaps(self, j: Any, t: int) -> int:
        """DEMAND_AWARE forecast of the swaps at ``j`` in the next ``lead`` slots
        (DECISIONS R2.3), from past information only: the swaps issued at ``j`` in
        the slots ``(t - lookback, t]`` (those of boundary ``t`` included, step 5
        precedes step 9), scaled to the lead window, ``ceil(swaps * lead / w)`` with
        ``w = min(lookback, t + 1)`` the number of observed slots (at ``t <
        lookback - 1`` the shorter observed window is scaled); 0 when no swap has
        been observed in the window."""
        lead, lookback = int(self.p.charge_lead), int(self.p.charge_lookback)
        w = min(lookback, t + 1)
        swaps = sum(self.swaps_by_slot[j][tau] for tau in range(t - w + 1, t + 1))
        if swaps <= 0 or lead <= 0:
            return 0
        return int(math.ceil(swaps * lead / w - _FLOOR_TOL))

    def demand_aware_need(self, j: Any, t: int) -> Tuple[int, int]:
        """``(forecast_j(t), need_j)`` of the DEMAND_AWARE rule at boundary ``t``
        (DECISIONS R2.3): ``need_j = max(0, forecast + reserve_j - n_jLt)`` with
        ``n_jLt`` the full stock after this boundary's swaps and departures and
        ``reserve_j = R_end_j y_j`` (17) unless ``charge_reserve`` overrides it.
        The batteries already being charged are counted implicitly: a battery at
        level ``q`` charged from ``t`` on is full at ``t + (L - q) <= t + lead`` for
        ``lead >= L``, and HIGH_FIRST continues the most advanced ones first, so
        charging ``need_j`` batteries equals "continue the pipeline + start
        ``need_j - pipeline`` new ones"."""
        f = self.inst.facility(j)
        reserve = self.p.reserve_j(j, f.R_end * self.y[j])
        forecast = self.forecast_swaps(j, t)
        need = max(0, forecast + reserve - self.n[j][self.L])
        return forecast, need

    def _step9_charging(self, t: int) -> None:
        """Charging at open charge sites within (20)-(21): per site at most
        ``cap_j = min(C_j, floor(P_j y_j / p_ch))`` batteries, per supply group at
        most ``floor(P^grid_gt / p_ch)`` (allocated in facility order), each level
        bounded by the stock left after this boundary's swaps and departures (14).

        * ``HIGH_FIRST`` / ``LOW_FIRST`` (round-1 ASAP): charge up to ``cap_j``,
          levels ``L-1 .. 0`` or ``0 .. L-1``.
        * ``DEMAND_AWARE`` (DECISIONS R2.3, default): charge ``min(need_j, cap_j)``
          batteries HIGH_FIRST, ``need_j`` from :meth:`demand_aware_need` (forecast
          of the next ``lead`` slots from the swaps observed in ``(t - lookback, t]``
          plus the reserve ``R_end_j``, minus the current full stock).  Charge-only
          hubs follow ``hub_charge_rule`` (:meth:`_charge_rule_for`).

        Diagnostics in ``flags['demand_aware']``: per site and slot the forecast,
        the need, the batteries charged and the ASAP counterfactual cap
        ``min(cap_j, non-full stock)`` (what HIGH_FIRST would have charged from the
        same stock, grid limit ignored), plus their totals.  In a compliance run with
        ``station_plan='plan'`` the plan's charging is replayed (:meth:`_step9_plan`)."""
        if self.plan_station is not None:
            self._step9_plan(t)
            return
        L = self.L
        p_ch = self.inst.disc.p_ch_kw
        group_left: Dict[Any, int] = {}
        da = self.flags["demand_aware"]
        for j in self.open_charge:
            f = self.inst.facility(j)
            rule = self._charge_rule_for(j)
            self.flags["charge_rule_effective"][j] = rule
            cap_site = min(self.C[j], int(math.floor(f.P_kw * self.y[j] / p_ch + _FLOOR_TOL)))
            if f.group is not None and f.group not in group_left:
                lim = self.inst.grid_limit(f.group, t)
                group_left[f.group] = (10 ** 9 if lim == math.inf
                                       else int(math.floor(lim / p_ch + _FLOOR_TOL)))
            non_full = sum(self.n[j][q] for q in range(L))
            asap_cap = min(cap_site, non_full)
            if rule == "DEMAND_AWARE":
                forecast, need = self.demand_aware_need(j, t)
                budget = min(cap_site, need)
                levels = range(L - 1, -1, -1)
            else:
                forecast, need = None, None
                budget = cap_site
                levels = range(L - 1, -1, -1) if rule == "HIGH_FIRST" else range(L)
            charged = 0
            for q in levels:
                if budget <= 0:
                    break
                lim_g = group_left.get(f.group, 10 ** 9) if f.group is not None else 10 ** 9
                cq = min(self.n[j][q], budget, lim_g)
                if cq <= 0:
                    continue
                self.c[(j, q, t)] = cq
                budget -= cq
                charged += cq
                if f.group is not None:
                    group_left[f.group] -= cq
            for key, val in (("forecast", forecast), ("need", need), ("charged", charged), ("asap_cap", asap_cap)):
                da[key].setdefault(j, []).append(val)
            da["charge_steps"] += charged
            da["asap_cap_steps"] += asap_cap

    # step 10 --------------------------------------------------------------
    def _step10_inventory_step(self, t: int) -> None:
        """Balance (13) to boundary ``t+1``: ``n' = n - c_q + c_{q-1} + hold_q + A_{q,t+1}``
        (``S_jt`` and ``D_jqt`` were subtracted when executed).  Storage (15) is
        checked and violations flagged."""
        L = self.L
        for f in self.inst.facilities:
            j = f.id
            row = self.n[j]
            new = [0] * (L + 1)
            for q in range(L + 1):
                c_q = self.c.get((j, q, t), 0) if q < L else 0
                c_qm = self.c.get((j, q - 1, t), 0) if q >= 1 else 0
                new[q] = row[q] - c_q + c_qm + self.hold[j][q] + self.A.get((j, q, t + 1), 0)
                if new[q] < 0:
                    self.flags["storage_violations"].append((j, t + 1, "negative", q, new[q]))
            tot = sum(new)
            cap = f.K * self.y[j]
            if tot > cap:
                self.flags["storage_violations"].append((j, t + 1, tot, cap))
            self.n[j] = new
            self.hold[j] = [0] * (L + 1)
        # drop delivered arrivals
        for j in list(self.pending_arrivals):
            self.pending_arrivals[j] = [rec for rec in self.pending_arrivals[j] if rec[0] > t + 1]

    # steps 11-14 ----------------------------------------------------------
    def _finish(self) -> Tuple[Schedule, Dict[str, Any]]:
        inst, lib, H, L = self.inst, self.lib, self.H, self.L
        # 11. unserved orders
        u = {o.id: (0 if o.id in self.assigned else 1) for o in inst.orders}
        # 12. terminal arcs (9): open swap site certificate, else dummy, else open path
        for k, bs in self.bikes.items():
            if bs.free_at != H:
                raise RuntimeError(f"bike {k} not at the horizon (free_at={bs.free_at})")
            state = (bs.v, H, bs.q)
            term: Optional[Arc] = None
            planned = self.plan_terminal.get(k)
            if planned is not None and planned.src == state:
                term = planned                           # compliant bike: the plan's own (9) arc
            for j in ([] if term is not None else self.open_swap):
                term = lib.find(k, "term", state, fac=j)
                if term is not None:
                    break
            if term is None:
                dummy = [a for a in lib.out_arcs(k, state) if a.kind == "term" and a.fac is None]
                if dummy:
                    term = dummy[0]
                    self.flags["terminal_violations"].append((k, state, "dummy_terminal"))
                else:
                    self.flags["terminal_violations"].append((k, state, "no_terminal_arc"))
            if term is not None:
                self._take(bs, term)
            if bs.queued_at is not None:
                self.flags["queued_at_H"].append(k)
        # 13. end targets (17), (18): reported, not enforced
        local = {}
        for j in inst.S:
            f = inst.facility(j)
            short = max(0, f.R_end * self.y[j] - self.n[j][L])
            if short:
                local[j] = short
        full_end = sum(self.n[j][L] for j in inst.N)
        self.flags["end_shortfalls"] = {
            "local": local,
            "global": max(0.0, inst.rho * sum(self.B.values()) - full_end),
        }
        # 14. schedule + cross-check of the online inventory against (13)
        x = {k: list(bs.path) for k, bs in self.bikes.items()}
        n_rec = reconstruct_inventory(inst, lib, x, self.c, self.z, self.B)
        self.flags["inventory_consistent"] = all(
            n_rec.get(key, 0) == val for key, val in self.n_hist.items()) and all(
            self.n_hist.get(key, 0) == val for key, val in n_rec.items())
        self.flags["n_swaps"] = sum(self.S.values())
        self.flags["n_transfers_used"] = sum(self.h.values())
        self.flags["n_unserved"] = sum(u.values())
        out = self.flags["outages"]
        out["outage_rate"] = (out["outage_episodes"] / out["swap_episodes"]) if out["swap_episodes"] else 0.0
        sc = self.flags["site_choice"]
        tot = sum(sc["decisions"].values())
        sc["shares"] = {j: (v / tot if tot else 0.0) for j, v in sc["decisions"].items()}
        sc["mean_wait"] = {j: (self.flags["wait_slots_in_queue"][j] / sc["queue_joins"][j]
                               if sc["queue_joins"][j] else None) for j in self.open_swap}
        if "compliance" in self.flags:
            self.flags["compliance"]["compliant_final"] = sorted(self.compliant, key=lambda k: self.kidx[k])
        self.flags["stranded_bikes"] = sorted(self.flags["stranded_bikes"], key=lambda k: self.kidx[k])
        sched = Schedule(
            x=x, u=u, c=dict(self.c), h=dict(self.h), z=dict(self.z),
            y=dict(self.y), B=dict(self.B), C=dict(self.C), n=dict(self.n_hist),
            meta={"policy": "baseline", "params": asdict(self.p), "flags": self.flags},
        )
        return sched, self.flags


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------
def run_baseline(inst: Instance, arcs: ArcLibrary,
                 params: Union[BaselineParams, Dict[str, Any], None] = None
                 ) -> Tuple[Schedule, Dict[str, Any]]:
    """Run the event-driven baseline policy on ``inst`` with the arc library ``arcs``
    (``plan.baseline_policy_spec`` steps 1-14) and return ``(Schedule, flags)``.

    The Schedule holds the chosen arc ids per bike (``x``, a source-to-sink path
    in ``arcs`` satisfying (5)), ``u`` (6), ``c`` (20)-(21), ``h``/``z`` (10), the
    effective facility values ``y``/``B``/``C`` and the inventory trajectory ``n``
    stepped with (13), (14), (16).  Price it with ``evaluate.cost`` (26)-(32) and
    verify it with ``evaluate.check``; it can be injected as a Gurobi MIP start.

    ``flags`` keys: ``stranded`` (bike, t, reason), ``stranded_bikes``,
    ``queued_at_H``, ``terminal_violations`` (bike, state, how) for (9),
    ``storage_violations`` for (15), ``end_shortfalls`` (``local`` (17),
    ``global`` (18)), ``wait_slots_in_queue`` per swap facility,
    ``pruned_arc_fallbacks`` (``count`` per kind, ``examples``),
    ``inventory_consistent`` (online (13) stepping equals
    ``evaluate.reconstruct_inventory``), ``notes``, ``q_thr``, ``max_need``,
    ``transfer_rule_effective``, ``n_swaps``, ``n_transfers_used``, ``n_unserved``,
    ``jit_dispatches`` (just-in-time starts of step 6), ``reach_refusals``
    (``count`` of reach-only refusals, ``bikes_sent_to_swap``, ``examples``),
    ``late_trips_suppressed``, ``stock_aware_reroutes`` / ``stock_aware_fallbacks``
    (R2.3 site choice), ``charge_rule_effective`` (facility -> rule applied) and
    ``demand_aware`` (R2.3 charging diagnostics: per-site per-slot ``forecast``,
    ``need``, ``charged``, ``asap_cap`` and the totals ``charge_steps``,
    ``asap_cap_steps``).  Round 5: ``swap_rule_effective``, ``site_choice_effective``,
    ``outages`` (M2 / A3: ``swap_episodes``, ``outage_episodes``, ``outage_rate``,
    ``decisions_without_stock``, ``arrivals_to_empty``, ``stockout_queue_slots``,
    ``position_queue_slots``, ``reservations_made`` / ``_used`` / ``_released`` /
    ``_expired`` / ``_refused``), ``range_rule`` (M2 triggers by source), ``site_choice``
    (M4: ``decisions`` / ``shares`` / ``queue_joins`` / ``mean_wait`` per site,
    ``logit_draws``), ``cost_aware`` (M3 shipments with benefit and cost).

    ``params`` is a :class:`BaselineParams`, a dict of its fields, or ``None`` for
    the round-2 defaults (DECISIONS R2.3: ``q_thr = ceil(0.25 L)``, DEMAND_AWARE
    charging with ``lead = lookback = 12`` and reserve ``R_end_j``, stock-aware
    site choice, NONE transfers, no opportunistic swaps, global dispatch, no end
    reserve, just-in-time dispatch and the dead-zone rule on), i.e. the variant
    ``'r2'``.  The named variants of :func:`baseline_variant_params` reproduce the
    round-1 policies and give the round-5 rules (``'r5_range'`` M2, ``'r5_transfer'``
    M3, ``'r5_selfish'`` M4, ``'r5'`` = the default of new experiments).  None of them
    changes an E2 equation: every schedule is checked against (5)-(22) as before.
    """
    if arcs.inst is not inst and arcs.inst != inst:
        raise ValueError("arc library was built for a different instance")
    p = BaselineParams.coerce(params)
    return _BaselineRun(inst, arcs, p).run()


#: Named parameter sets for ablations (DECISIONS R2.3 "the legacy flags remain
#: for reproducibility"; round-5 variants from ``notes/reading_to_model.md``):
#:
#: * ``'default'`` / ``'r2'`` -- the round-2 rules (stock-aware site choice, DEMAND_AWARE
#:   charging, just-in-time dispatch, dead-zone rule; threshold swap rule, no transfers);
#:   ``BaselineParams()`` defaults, kept so that every stored round-2..4 output reproduces;
#: * ``'round1'``  -- the round-1 baseline after the reviewer fixes (nearest site
#:   regardless of stock, ASAP HIGH_FIRST charging, JIT dispatch and dead-zone rule on);
#: * ``'legacy'``  -- the pre-review round-1 policy (``round1`` plus ``jit_dispatch=False``,
#:   ``swap_on_reach_refusal=False``);
#: * ``'r5_range'`` -- M2: range-aware swap trigger + battery reservations (eBaaS);
#: * ``'r5_transfer'`` -- M3: cost-aware zero-sum transfer rule (IJCAI-25) on top of r2;
#: * ``'r5_selfish'`` -- M4: self-interested logit station choice (IJCAI-15) on top of r2;
#: * ``'r5'`` -- the round-5 default for new experiments: r5_range + r5_transfer
#:   (the transfer rule is inert when the instance has no services) + stock-aware site
#:   choice + DEMAND_AWARE charging.
BASELINE_VARIANTS: Dict[str, Dict[str, Any]] = {
    "default": {},
    "r2": {},
    "round1": {"stock_aware_site": False, "charge_rule": "HIGH_FIRST"},
    "legacy": {"stock_aware_site": False, "charge_rule": "HIGH_FIRST",
               "jit_dispatch": False, "swap_on_reach_refusal": False},
    "r5_range": {"swap_rule": "RANGE", "reservation": True},
    "r5_transfer": {"transfer_rule": "COST_AWARE"},
    "r5_selfish": {"site_choice": "LOGIT"},
    "r5": {"swap_rule": "RANGE", "reservation": True, "transfer_rule": "COST_AWARE",
           "stock_aware_site": True, "charge_rule": "DEMAND_AWARE"},
}

#: Variant that new (round-5) experiments use by default (plan items M2 + M3).
DEFAULT_VARIANT_NEW = "r5"


def baseline_variant_params(name: str, **overrides: Any) -> Dict[str, Any]:
    """``BaselineParams`` field dict of the named variant of :data:`BASELINE_VARIANTS`
    (``'default'`` / ``'r2'`` = DECISIONS R2.3 rules, ``'round1'`` = ``stock_aware_site=False``
    + ``charge_rule='HIGH_FIRST'``, ``'legacy'`` = round-1 legacy flags, ``'r5_range'`` (M2),
    ``'r5_transfer'`` (M3), ``'r5_selfish'`` (M4), ``'r5'`` (M2 + M3, new default)), updated by
    ``overrides`` (e.g. ``transfer_rule='REORDER_POINT'``).  The result validates
    through :meth:`BaselineParams.coerce` and can be passed to :func:`run_baseline`."""
    if name not in BASELINE_VARIANTS:
        raise KeyError(f"unknown baseline variant {name!r}; known: {sorted(BASELINE_VARIANTS)}")
    params = dict(BASELINE_VARIANTS[name])
    params.update(overrides)
    BaselineParams.coerce(dict(params))
    return params


# ---------------------------------------------------------------------------
# round-5 helpers (M3 / M4)
# ---------------------------------------------------------------------------
def poisson_sf(lam: float, k: float) -> float:
    """``Pr[N >= k]`` for ``N ~ Poisson(lam)`` (plan items M3 / M4: forecast swaps =
    recent swap rate x window).  ``k <= 0`` gives 1, ``lam <= 0`` with ``k >= 1`` gives 0;
    a fractional ``k`` is rounded up."""
    k = int(math.ceil(k - _FLOOR_TOL))
    if k <= 0:
        return 1.0
    if lam <= 0:
        return 0.0
    pmf = math.exp(-lam)
    cdf = pmf
    for i in range(1, k):
        pmf *= lam / i
        cdf += pmf
    return max(0.0, min(1.0, 1.0 - cdf))


def logit_probabilities(utilities: Sequence[float], scale: float = 1.0) -> List[float]:
    """Multinomial-logit choice probabilities ``exp(U_j / scale) / sum_l exp(U_l / scale)``
    (plan item M4, IJCAI-15 follower; numerically stable by subtracting the maximum)."""
    if not utilities:
        return []
    s = float(scale)
    m = max(utilities)
    w = [math.exp((u - m) / s) for u in utilities]
    tot = sum(w)
    return [x / tot for x in w]


def _variant_dict(params: Union[BaselineParams, Dict[str, Any], None], base: str) -> Dict[str, Any]:
    """Field dict: the named ``base`` variant updated by ``params`` (a dict of overrides
    or a full :class:`BaselineParams`, which then replaces the variant)."""
    if isinstance(params, BaselineParams):
        return asdict(params)
    out = dict(BASELINE_VARIANTS[base])
    out.update(dict(params or {}))
    return out


def run_selfish_equilibrium(inst: Instance, arcs: ArcLibrary,
                            params: Union[BaselineParams, Dict[str, Any], None] = None,
                            max_iter: int = 10, tol: float = 0.01, averaging: str = "msa"
                            ) -> Tuple[Schedule, Dict[str, Any], Dict[str, Any]]:
    """M4 equilibrium mode of the self-interested follower (IJCAI-15 Sec. 3.3-3.4,
    iterated best response over a simulated day).

    Iteration 1 runs the ``r5_selfish`` policy (``params`` = overrides of that variant,
    or a full :class:`BaselineParams` with ``site_choice='LOGIT'``) with the myopic wait
    estimate ``|queue_j| / (M_j / sigma_j)``.  Each later iteration repeats the same day
    (same demand, same logit seed: common random numbers) with ``expected_wait[j]`` =
    the mean queue wait per queue join experienced at ``j`` in the previous iterations
    (``averaging='msa'``: method of successive averages, ``'none'``: last iteration
    only; a site without a queue join keeps its previous value).  The loop stops when
    every site's choice share changes by less than ``tol`` (absolute share, 0.01 = one
    percentage point) or after ``max_iter`` iterations.  Information: within a day each
    rider uses only the information set of the LOGIT rule (module docstring); the
    expected waits come from previous days, never from the current one.  No E2 equation
    is involved; every iterate is a Schedule checked against (5)-(22) like any policy.

    Returns ``(schedule, flags, info)`` of the last iteration with ``info = {'iterations',
    'converged', 'shares' (per iteration), 'expected_wait' (per iteration, input),
    'max_share_change' (per iteration from the second), 'tol', 'averaging'}``.
    """
    if averaging not in ("msa", "none"):
        raise ValueError("averaging must be 'msa' or 'none'")
    if int(max_iter) < 1:
        raise ValueError("max_iter must be >= 1")
    base = _variant_dict(params, "r5_selfish")
    if base.get("site_choice") != "LOGIT":
        raise ValueError("run_selfish_equilibrium needs site_choice='LOGIT'")
    base.pop("expected_wait", None)
    info: Dict[str, Any] = {"iterations": 0, "converged": False, "shares": [], "expected_wait": [],
                            "max_share_change": [], "tol": float(tol), "averaging": averaging}
    expected: Optional[Dict[Any, float]] = None
    prev: Optional[Dict[Any, float]] = None
    sched: Optional[Schedule] = None
    flags: Dict[str, Any] = {}
    for it in range(1, int(max_iter) + 1):
        p = dict(base)
        p["expected_wait"] = None if expected is None else dict(expected)
        sched, flags = run_baseline(inst, arcs, p)
        shares = dict(flags["site_choice"]["shares"])
        info["iterations"] = it
        info["shares"].append(shares)
        info["expected_wait"].append(None if expected is None else dict(expected))
        if prev is not None:
            diff = max([abs(shares.get(j, 0.0) - prev.get(j, 0.0)) for j in set(shares) | set(prev)] or [0.0])
            info["max_share_change"].append(diff)
            if diff < tol:
                info["converged"] = True
                break
        realized = flags["site_choice"]["mean_wait"]
        new: Dict[Any, float] = {}
        for j, w in realized.items():
            old = None if expected is None else expected.get(j)
            if w is None:
                new[j] = 0.0 if old is None else old
            elif old is None or averaging == "none":
                new[j] = float(w)
            else:
                new[j] = old + (float(w) - old) / it        # MSA step 1/it (it >= 2 here)
        expected = new
        prev = shares
    flags["equilibrium"] = {k: v for k, v in info.items() if k not in ("shares", "expected_wait")}
    return sched, flags, info


def select_compliant_bikes(inst: Instance, alpha_c: float, seed: int = 0) -> List[Any]:
    """Compliant bikes for a compliance share ``alpha_c`` in [0, 1] (plan item M4):
    ``round(alpha_c |K|)`` bikes (half up) drawn without replacement with
    ``random.Random(seed)``, returned in instance order."""
    a = float(alpha_c)
    if not (0.0 <= a <= 1.0):
        raise ValueError("alpha_c must lie in [0, 1]")
    ids = [b.id for b in inst.bikes]
    n_c = int(math.floor(a * len(ids) + 0.5))
    chosen = set(random.Random(int(seed)).sample(range(len(ids)), n_c))
    return [ids[i] for i in range(len(ids)) if i in chosen]


def simulate_compliance(inst: Instance, arcs: ArcLibrary, plan: Schedule, alpha_c: float,
                        params: Union[BaselineParams, Dict[str, Any], None] = None, seed: int = 0,
                        compliant: Optional[Sequence[Any]] = None, station_plan: str = "plan"
                        ) -> Tuple[Schedule, Dict[str, Any]]:
    """Compliance sweep helper (plan item M4): a share ``alpha_c`` of the riders follows
    the coordinator's schedule ``plan`` (e.g. an ILP incumbent on the same ``arcs``), the
    others behave self-interestedly with the ``r5_selfish`` policy.

    * Compliant bikes (:func:`select_compliant_bikes` with ``seed``, or the explicit
      list ``compliant``) take exactly their planned arcs (E2 (2)-(4), (9) arcs of the
      plan) and serve the orders the plan assigns to them; these orders never enter the
      policy queue.  A planned swap that the live stock (14) or positions (22) cannot
      honour turns the bike into a policy bike from then on (``defected``) and returns
      its unstarted planned orders to the policy queue.
    * Non-compliant bikes run the policy ``params`` (overrides of ``r5_selfish``, or a full
      :class:`BaselineParams`) on all other released orders.
    * Station layer: ``station_plan='plan'`` (default) replays the plan's charging ``c``
      and service loads ``h, z`` clipped to the live stock (14), storage (15) and caps
      (20)-(21); ``'policy'`` runs the policy's own charging / transfer rules.

    With ``alpha_c = 1`` and ``station_plan='plan'`` a clean plan is reproduced exactly;
    with ``alpha_c = 0`` and ``station_plan='policy'`` the run equals
    ``run_baseline(inst, arcs, params)``.  The result is an ordinary Schedule priced by
    ``evaluate.cost`` (26)-(32) and checked by ``evaluate.check``; ``flags['compliance']``
    holds ``alpha_c``, ``compliant`` (initial), ``compliant_final``, ``defected`` (bike, t,
    reason), ``planned_swaps_done``, ``clipped_loads``, ``clipped_charge``,
    ``station_plan``."""
    if station_plan not in STATION_PLANS:
        raise ValueError(f"station_plan must be one of {STATION_PLANS}")
    if arcs.inst is not inst and arcs.inst != inst:
        raise ValueError("arc library was built for a different instance")
    p = BaselineParams.coerce(_variant_dict(params, "r5_selfish"))
    if compliant is None:
        comp = select_compliant_bikes(inst, alpha_c, seed)
    else:
        known = {b.id for b in inst.bikes}
        comp = [b.id for b in inst.bikes if b.id in set(compliant)]
        if set(compliant) - known:
            raise ValueError(f"unknown bikes in compliant: {sorted(set(compliant) - known, key=str)}")
    run = _BaselineRun(inst, arcs, p)
    run.flags["compliance"] = {"alpha_c": float(alpha_c), "compliant": list(comp), "compliant_final": [],
                               "defected": [], "planned_swaps_done": 0, "clipped_loads": 0,
                               "clipped_charge": 0, "station_plan": station_plan, "seed": int(seed)}
    for k in comp:
        path = plan.path(k, arcs)
        if not path or path[0].src != arcs.source(k):
            raise ValueError(f"plan has no source-to-sink path for bike {k}")
        body = [a for a in path if a.kind != "term"]
        run.compliant[k] = body
        terms = [a for a in path if a.kind == "term"]
        if terms:
            run.plan_terminal[k] = terms[0]
        for a in body:
            if a.kind == "deliver":
                run.plan_orders[a.order] = k
    if station_plan == "plan":
        run.plan_station = {"c": dict(plan.c), "h": dict(plan.h), "z": dict(plan.z)}
        if not inst.option("no_transfers"):
            run.transfer_rule = "PLAN"
            run.flags["transfer_rule_effective"] = "PLAN"
    return run.run()


__all__ = ["BaselineParams", "run_baseline", "baseline_variant_params", "BASELINE_VARIANTS",
           "DEFAULT_VARIANT_NEW", "CHARGE_RULES", "CHARGE_RULE_ALIASES", "TRANSFER_RULES",
           "DISPATCH_SCOPES", "SWAP_RULES", "SITE_CHOICES", "RANGE_TYPICAL", "STOCKOUT_COST_MODES",
           "STATION_PLANS", "poisson_sf", "logit_probabilities", "run_selfish_equilibrium",
           "select_compliant_bikes", "simulate_compliance"]
