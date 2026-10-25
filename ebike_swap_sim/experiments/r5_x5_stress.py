"""Round 5, X5 -- stressed family, M1 boundary grid, A6 fleet x spare x pack, M9 / M10 levers.

Plan items (``notes/reading_to_model.md``; sizes in ``experiments/common.py`` "R5 sizes" and
DECISIONS "R5 implementation notes"): M5 stressed family, M1 boundary handling, A3 metric pack,
A6 fleet x spare x pack, M9 battery lock-out, M10 levers (charger speed, swap positions, site
power cap with the demand-charge proxy).  No E2 equation changes: every variant below is data.

Sub-commands (any combination; run in the order given here):

``--core``      r5_stress4h at 6 / 8 / 10 bikes, seeds 0-4 (ILP 300 s at 6 bikes, 600 s at 8 and
                10 bikes), r5_stress8h at 6 bikes, seeds 0-2 (ILP 600 s); headline = the relaxed
                control ``rho = 0, R_end = 0`` (``common.relax_end_targets``); LP-relaxation
                operating values of one more spare / charger per site (``-RC(B_j) + bB_j``,
                ``-RC(C_j) + bC_j``, the integrate-step probe method) on the relaxed and written
                targets; written-target ILP (price of recovery) at 6 bikes seeds 0-4 (300 s) and at
                8 / 10 bikes seed 0 (600 s, last, budget permitting).  Wall budget 240 min.
``--boundary``  M1 grid (``common.boundary_grid``: rho {0, .25, .5, 1} x R_end {0, 1} + periodic)
                on r5_stress4h 6 bikes seeds 0-2, ILP 300 s: price of recovery per variant =
                ILP(variant) - ILP(rho0_R0), raw and end-adjusted; the policy's schedule does not
                depend on the targets, so its rows report which targets it violates.  Order:
                rho0_R0, periodic, rho0.5_R1 (= the written targets), then the grid; earlier ILP
                schedules that are feasible for a later cell are offered as MIP starts.  60 min.
``--fleet``     A6 (``generator.make_fleet_sweep_instance``, orders fixed at the nominal 48):
                baseline rules on all 48 cells |K| {4,6,8,10} x B {1..4} x pack {0.5, 0.75, 1.0}
                kWh x seeds 0-2; ILP on the 12 cells |K| {4,6,8} x B {1..4} at pack 0.6 kWh x seeds
                0-1 (300 s; 600 s at 8 bikes); allocated bike (+ rider) cost per window
                (``costs.allocated_bike_cost``) and the iso-cost frontier "one more bike vs one
                more spare" in ``--analyse``.  180 min.
``--levers``    on r5_stress4h 8 bikes seeds 0-2 (ILP 300 s; all relaxed control): M10(c) charger
                speed eps 25 vs 50 Wh (``generator.charger_speed_variants``); M10(a) swap
                positions M in {1, 2} (``swap_position_variants``, M = 1 is the reference); M10(b)
                site power cap P_j in {0, p_ch} (``site_power_cap_sweep``; with C_j = 1 the cap
                p_ch has exactly the feasible set of the 4 kW reference, (20), so V(p_ch) is the
                reference row) priced with ``costs.demand_charge_proxy`` at the assumed tariffs
                :data:`DEMAND_TARIFFS`; M9 lock-out of 5 / 10 % of the spares at the dinner peak
                17-18 h (``add_battery_lockout``; with 6 spares both shares round to ONE battery,
                so they are the same instance and are solved once; 25 % = 2 batteries is added as
                the dose-response point).  120 min.

Protocol (binding, round 5): Gurobi ``Threads 3``, ``Seed 0``, ``OutputFlag 0``, ``aggregate=True``
(O1) for every ILP; every method of a case runs on the SAME instance object (``demand_md5``
asserted and recorded); headline gap = (baseline - ILP) / baseline against ``r2``, ``r5`` and the
per-instance ``best_rule`` = min over r2, r5_range, r5_transfer (only when transport services
exist; none in these families) and r5 by total (26) (``gap_vs_best_rule_pct_end_adjusted`` uses the
min of ``total_end_adjusted`` over the same rules); ``C_end_adjust`` and the A3 metric pack are
recorded for every schedule; baseline rows also carry ``families_written`` (the check of the same
schedule against the written targets, since the policy is target-agnostic).

Bookkeeping (round-3 / round-4 pattern): one ``records_<sub>.jsonl`` per sub-command (append
only), ``results_<sub>.csv`` and the union ``results.csv`` refreshed after every case, resume by
row key ``(key_md5, method)`` where ``key_md5`` hashes the instance content (meta excluded) and
the pruning, so identical cells requested by two sub-commands are solved once; methods are
``baseline_<rule>``, ``best_rule``, ``LP`` and ``ILP_tl<limit>``; ``cases_<sub>.jsonl`` maps the
cases onto keys.  ``WallBudget`` per sub-command: a solve whose time limit does not fit is
recorded as ``SKIPPED_BUDGET`` (re-run on resume); a solve the budget shortened is flagged
``budget_shortened`` and re-run on resume unless OPTIMAL.  One printed JSON line per case.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r5_x5_stress.py --core --boundary --fleet --levers --dry-run
    python3 experiments/r5_x5_stress.py --core --boundary --fleet --levers --smoke --out-dir /tmp/x5_smoke
    python3 experiments/r5_x5_stress.py --core --boundary --fleet --levers
    python3 experiments/r5_x5_stress.py --analyse
"""
from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import math
import os
import sys
import time
import traceback
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import ArcLibrary, Instance, Schedule, check, cost  # noqa: E402
from ebike_swap_sim import costs as cost_mod  # noqa: E402
from ebike_swap_sim import generator as gen  # noqa: E402
from experiments import common as C  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r5_x5_stress")
SUBS: Tuple[str, ...] = ("core", "boundary", "fleet", "levers")
#: Wall budget per sub-command (minutes).
WALL_BUDGET_MIN: Dict[str, float] = {"core": 240.0, "boundary": 60.0, "fleet": 180.0, "levers": 120.0}
TL_DEFAULT = 300.0
TL_LONG = 600.0
LP_TIME_LIMIT = 300.0
ILP_PARAMS: Dict[str, Any] = dict(C.ILP_PARAMS_R3)          # Seed 0
ILP_KWARGS: Dict[str, Any] = dict(C.R5_ILP_KWARGS)          # aggregate=True (O1)
#: Baseline rules (``common.BASELINE_VARIANTS`` names); ``r5_transfer`` only with transport services.
RULES: Tuple[str, ...] = ("r2", "r5_range", "r5_transfer", "r5")
RULE_VARIANT: Dict[str, str] = {"r2": "baseline", "r5_range": "baseline_r5_range",
                                "r5_transfer": "baseline_r5_transfer", "r5": "baseline_r5"}
RELAXED = "rho0_R0"

# -- core ----------------------------------------------------------------------------------
#: (family, n_bikes, seeds, ILP time limit) of the relaxed headline cells.
CORE_CELLS: Tuple[Tuple[str, int, Tuple[int, ...], float], ...] = (
    ("r5_stress4h", 6, (0, 1, 2, 3, 4), TL_DEFAULT),
    ("r5_stress4h_k8", 8, (0, 1, 2, 3, 4), TL_LONG),
    ("r5_stress4h_k10", 10, (0, 1, 2, 3, 4), TL_LONG),
    ("r5_stress8h", 6, (0, 1, 2), TL_LONG),
)
#: Written-target ILP cells (price of recovery) run right after the relaxed cell of the same seed.
CORE_WRITTEN_INLINE: Tuple[str, ...] = ("r5_stress4h",)
#: Written-target ILP cells run last (budget permitting): (family, seeds, time limit).
CORE_WRITTEN_TAIL: Tuple[Tuple[str, Tuple[int, ...], float], ...] = (
    ("r5_stress4h_k8", (0,), TL_LONG), ("r5_stress4h_k10", (0,), TL_LONG))

# -- boundary --------------------------------------------------------------------------------
BOUNDARY_FAMILY = "r5_stress4h"
BOUNDARY_SEEDS: Tuple[int, ...] = (0, 1, 2)
#: Variants solved first (headline, periodic bracket = feasible start for every other cell, written).
BOUNDARY_FIRST: Tuple[str, ...] = (RELAXED, C.PERIODIC_LABEL, "rho0.5_R1")

# -- fleet -----------------------------------------------------------------------------------
FLEET_FAMILY = "r5_stress4h"
FLEET_K: Tuple[int, ...] = (4, 6, 8, 10)
FLEET_B: Tuple[int, ...] = (1, 2, 3, 4)
FLEET_PACKS: Tuple[float, ...] = (0.5, 0.75, 1.0)
FLEET_SEEDS: Tuple[int, ...] = (0, 1, 2)
FLEET_ILP_K: Tuple[int, ...] = (4, 6, 8)
FLEET_ILP_PACK = 0.6
FLEET_ILP_SEEDS: Tuple[int, ...] = (0, 1)

# -- levers ----------------------------------------------------------------------------------
LEVER_FAMILY = "r5_stress4h"
LEVER_K = 8
LEVER_SEEDS: Tuple[int, ...] = (0, 1, 2)
LEVER_EPS_WH: Tuple[float, ...] = (25.0, 50.0)
LEVER_M: Tuple[int, ...] = (1, 2)
LOCKOUT_SHARES: Tuple[float, ...] = (0.05, 0.10, 0.25)
#: Dinner peak of ``generator.R5_TIME_PROFILE`` (clock hours) = the M9 lock-out window.
DINNER_PEAK_H: Tuple[float, float] = (17.0, 18.0)
#: Monthly demand tariffs (USD per kW of monthly peak) for the M10(b) proxy: an order-of-magnitude
#: ASSUMPTION (no NYC demand tariff is calibrated in notes/data/cost_calibration_usd.json).
DEMAND_TARIFFS: Tuple[float, ...] = (10.0, 25.0, 40.0)

#: Arc libraries kept in memory per sub-command (fleet / core loop so that one library serves the
#: consecutive variants; boundary keeps its three seeds; levers the reference and the eps-50 library).
LIB_CACHE: Dict[str, int] = {"core": 1, "boundary": 3, "fleet": 1, "levers": 2}

SMOKE_TL = 20.0
SMOKE_LP_TL = 60.0
SMOKE_BUDGET_MIN = 20.0


# ---------------------------------------------------------------------------
# hashing and small helpers
# ---------------------------------------------------------------------------
def _canon(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _canon(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (set, frozenset)):
        return sorted(str(v) for v in obj)
    if isinstance(obj, (list, tuple)):
        return [_canon(v) for v in obj]
    return obj


def _md5(obj: Any) -> str:
    return hashlib.md5(json.dumps(_canon(obj), default=str, sort_keys=True).encode("utf-8")).hexdigest()


def content_key(inst: Instance, pruning: Dict[str, Any]) -> str:
    """Row key of a case: the instance content without ``meta`` plus the arc-builder pruning."""
    d = inst.to_dict()
    d.pop("meta", None)
    return _md5({"inst": d, "pruning": pruning})


def arc_signature(inst: Instance, pruning: Dict[str, Any]) -> str:
    """Everything ``arcs.build_arcs`` reads: discretisation, nodes, routes, bikes, orders,
    ``q_res``, the swap facilities' ``(id, node, sigma, y)`` (charge-only sites and ``B, C, M, P,
    R_end, rho`` never enter the arc library), the arc options and the pruning.  Instances with
    the same signature share one library (rebound to the variant instance)."""
    d = inst.to_dict()
    opts = {k: v for k, v in (d.get("options") or {}).items() if k != "forced_transfers"}
    sw = [(f.id, f.node, f.sigma, f.y) for f in inst.facilities if f.swap]
    return _md5({"disc": d["disc"], "nodes": d["nodes"], "routes": d["routes"], "bikes": d["bikes"],
                 "orders": d["orders"], "q_res": inst.q_res, "swap": sw, "options": opts, "pruning": pruning})


def orders_md5(inst: Instance) -> str:
    """MD5 of the orders alone (ids, nodes, slots) -- equal across fleet sizes, packs and levers."""
    return _md5([(o.id, o.o, o.d, o.r, o.a, o.b, o.hp, o.hd, o.P) for o in inst.orders])


def target_copy(inst: Instance, target: str) -> Instance:
    """``'written'`` -> ``inst``; ``'rho0_R0'`` -> :func:`common.relax_end_targets`; any other M1
    label -> :func:`common.end_target_copy` with the grid's (rho, R_end)."""
    if target == "written":
        return inst
    if target == RELAXED:
        return C.relax_end_targets(inst)
    spec = boundary_specs().get(target)
    if spec is None:
        raise KeyError(f"unknown target {target!r}")
    return C.end_target_copy(inst, spec[0], spec[1], target)


def boundary_specs() -> "OrderedDict[str, Tuple[float, Any]]":
    out: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()
    for rho in C.BOUNDARY_RHOS:
        for r in C.BOUNDARY_R_ENDS:
            out[C.boundary_label(rho, r)] = (float(rho), r)
    out[C.PERIODIC_LABEL] = (1.0, "B")
    return out


def targets_label(inst: Instance) -> str:
    """Data label of the end targets of an instance (written or copy), e.g. ``rho0.5_R1``."""
    rs = sorted({int(f.R_end) for f in inst.facilities if f.swap and f.charge})
    bs = sorted({int(f.B or 0) for f in inst.facilities if f.swap and f.charge})
    if len(rs) == 1:
        if float(inst.rho) == 1.0 and len(bs) == 1 and rs[0] == bs[0] and rs[0] > 1:
            return C.PERIODIC_LABEL
        return C.boundary_label(inst.rho, rs[0])
    return f"rho{float(inst.rho):g}_Rmixed"


def real_services(inst: Instance) -> List[Any]:
    forced = {r["service"] for r in (inst.options.get("forced_transfers") or [])}
    return [s.id for s in inst.services if s.id not in forced]


def rules_for(inst: Instance) -> List[str]:
    return [r for r in RULES if r != "r5_transfer" or real_services(inst)]


def _count(v: Any) -> Any:
    """Length of a list / dict flag, the value itself for a scalar."""
    return len(v) if isinstance(v, (list, tuple, dict, set)) else v


def ilp_method(tl: float) -> str:
    return f"ILP_tl{int(round(tl))}"


def pct_gap(base: Optional[float], ilp: Optional[float]) -> Optional[float]:
    if base is None or ilp is None or abs(base) < 1e-12:
        return None
    return 100.0 * (float(base) - float(ilp)) / abs(float(base))


def portable(sched: Schedule) -> Schedule:
    """Decision part of a schedule (``x, u, c, h, z``) without stock or facility values, so it can
    be re-checked / offered as a start on a variant instance with other ``B / C / M / P`` data."""
    return Schedule(x={k: list(v) for k, v in sched.x.items()}, u=dict(sched.u), c=dict(sched.c),
                    h=dict(sched.h), z=dict(sched.z))


def swap_occupancy(inst: Instance, lib: ArcLibrary, sched: Schedule) -> Dict[str, Any]:
    """Peak of LHS(22) / M_j: swap arcs occupying a position at site j in slot tau ([l_a, u_a))."""
    occ: Dict[Tuple[Any, int], int] = {}
    for a in sched.chosen_arcs(lib):
        if a.kind == "swap":
            for tau in range(a.l, min(a.u, inst.H)):
                occ[(a.fac, tau)] = occ.get((a.fac, tau), 0) + 1
    ratio = 0.0
    full = 0
    for (j, _tau), v in occ.items():
        M = max(1, int(inst.facility(j).M))
        ratio = max(ratio, v / M)
        full += int(v >= M)
    return {"peak_swap_occupancy_ratio": ratio, "slots_at_swap_capacity": full}


def lockout_slots(inst: Instance, n: int, seed: int) -> List[int]:
    """``n`` lock-out slots drawn uniformly in the dinner peak 17-18 h of the window
    (``numpy.random.default_rng([seed, 9010])``), sorted."""
    start_h = float((inst.meta.get("params") or {}).get("window_start_hour", 16.0))
    dt = inst.disc.Delta_h
    a = max(1, int(round((DINNER_PEAK_H[0] - start_h) / dt)))
    b = min(inst.H - 1, int(round((DINNER_PEAK_H[1] - start_h) / dt)))
    if b <= a:
        raise ValueError(f"dinner peak outside the window (start {start_h} h)")
    rng = np.random.default_rng([int(seed), 9010])
    return sorted(int(v) for v in rng.integers(a, b, size=n))


def n_locked(inst: Instance, share: float) -> int:
    """Number of batteries ``generator.add_battery_lockout`` locks for ``share``."""
    total = sum(int(f.B or 0) for f in inst.facilities)
    return 0 if share <= 0 else min(total, max(1, int(round(float(share) * total))))


# ---------------------------------------------------------------------------
# cases (plan items)
# ---------------------------------------------------------------------------
@dataclass
class Case:
    sub: str
    cell: str
    seed: int
    target: str                         # 'written' | 'rho0_R0' | M1 label
    build_id: str                       # cache id of the written instance
    builder: Callable[[], Instance]
    ilp_tl: Optional[float] = None
    lp: bool = False
    phase: str = ""
    info: Dict[str, Any] = field(default_factory=dict)
    n_bikes: int = 6
    H: int = 48


def _core_builder(family: str, seed: int, over: Dict[str, Any]) -> Callable[[], Instance]:
    return lambda: C.make_instance(family, seed=seed, **over)


def plan_core(smoke: bool = False) -> List[Case]:
    cells = CORE_CELLS if not smoke else (("r5_stress4h", 6, (0,), SMOKE_TL),)
    out: List[Case] = []
    for family, k, seeds, tl in cells:
        H = 96 if "8h" in family else 48
        for seed in seeds:
            bid = f"core:{family}:{seed}"
            b = _core_builder(family, seed, {})
            info = {"family_size": family}
            out.append(Case("core", f"{family}_K{k}", seed, RELAXED, bid, b, tl, True, "relaxed", dict(info), k, H))
            if family in CORE_WRITTEN_INLINE:
                out.append(Case("core", f"{family}_K{k}", seed, "written", bid, b, tl, True, "written", dict(info), k, H))
    if not smoke:
        for family, seeds, tl in CORE_WRITTEN_TAIL:
            k = int(C.FAMILIES[family].get("n_bikes", 6))
            for seed in seeds:
                out.append(Case("core", f"{family}_K{k}", seed, "written", f"core:{family}:{seed}",
                                _core_builder(family, seed, {}), tl, True, "written_tail",
                                {"family_size": family}, k, 48))
    return out


def plan_boundary(smoke: bool = False) -> List[Case]:
    labels = list(BOUNDARY_FIRST) + [lab for lab in boundary_specs() if lab not in BOUNDARY_FIRST]
    seeds = BOUNDARY_SEEDS if not smoke else (0,)
    tl = TL_DEFAULT if not smoke else SMOKE_TL
    if smoke:
        labels = [RELAXED, C.PERIODIC_LABEL]
    out: List[Case] = []
    for lab in labels:
        for seed in seeds:
            out.append(Case("boundary", f"{BOUNDARY_FAMILY}_K6", seed, lab, f"core:{BOUNDARY_FAMILY}:{seed}",
                            _core_builder(BOUNDARY_FAMILY, seed, {}), tl, False, "grid",
                            {"family_size": BOUNDARY_FAMILY, "boundary_spec": list(boundary_specs()[lab])}, 6, 48))
    return out


def _fleet_builder(seed: int, k: int, B: int, pack: float) -> Callable[[], Instance]:
    return lambda: gen.make_fleet_sweep_instance(FLEET_FAMILY, seed=seed, n_bikes=k, B=B, pack_kwh=pack)


def plan_fleet(smoke: bool = False) -> List[Case]:
    out: List[Case] = []
    seeds = FLEET_SEEDS if not smoke else (0,)
    Ks = FLEET_K if not smoke else (4,)
    for seed in seeds:                                   # (1) baseline grid, 48 cells
        for k in Ks:
            for pack in FLEET_PACKS:
                for B in FLEET_B:
                    out.append(Case("fleet", f"K{k}_B{B}_pack{pack:g}", seed, RELAXED, f"fleet:{seed}:{k}:{B}:{pack:g}",
                                    _fleet_builder(seed, k, B, pack), None, False, "grid",
                                    {"K": k, "B_per_site": B, "pack_kwh": pack}, k, 48))
    ilp_seeds = FLEET_ILP_SEEDS if not smoke else (0,)
    ilp_K = FLEET_ILP_K if not smoke else (4,)
    ilp_B = FLEET_B if not smoke else (1, 2)
    for seed in ilp_seeds:                               # (2) ILP subset at pack 0.6 kWh
        for k in ilp_K:
            tl = (TL_LONG if k >= 8 else TL_DEFAULT) if not smoke else SMOKE_TL
            for B in ilp_B:
                pack = FLEET_ILP_PACK
                out.append(Case("fleet", f"K{k}_B{B}_pack{pack:g}", seed, RELAXED, f"fleet:{seed}:{k}:{B}:{pack:g}",
                                _fleet_builder(seed, k, B, pack), tl, False, "ilp",
                                {"K": k, "B_per_site": B, "pack_kwh": pack}, k, 48))
    return out


def plan_levers(smoke: bool = False) -> List[Case]:
    k = LEVER_K if not smoke else 6
    family = "r5_stress4h_k8" if k == 8 else "r5_stress4h"
    seeds = LEVER_SEEDS if not smoke else (0,)
    tl = TL_DEFAULT if not smoke else SMOKE_TL
    out: List[Case] = []
    for seed in seeds:
        ref_id = f"core:{family}:{seed}"

        def ref(seed=seed, family=family) -> Instance:
            return C.make_instance(family, seed=seed)

        def eps(seed=seed, e=50.0, k=k) -> Instance:
            inst = gen.charger_speed_variants(LEVER_FAMILY, seed=seed, eps_wh=(e,), n_bikes=k)[e]
            inst.meta["family"] = f"{LEVER_FAMILY}_eps{e:g}"
            return inst

        def pos(seed=seed, M=2, ref=ref) -> Instance:
            return gen.swap_position_variants(ref(seed), M_values=(M,))[M]

        def lock(seed=seed, share=0.05, ref=ref) -> Instance:
            base = ref(seed)
            n = n_locked(base, share)
            return gen.add_battery_lockout(base, share=share, slots=lockout_slots(base, n, seed), seed=seed)

        def power0(seed=seed, ref=ref) -> Instance:
            return gen.site_power_cap_sweep(ref(seed), multiples=[0])[0][1]

        common = {"family_size": family}
        out.append(Case("levers", "reference", seed, RELAXED, ref_id, ref, tl, False, "reference",
                        {**common, "lever": "reference", "lever_value": None, "eps_wh": 25.0, "M": 1,
                         "lockout_share": 0.0, "P_cap_multiple": None}, k, 48))
        for e in LEVER_EPS_WH:
            if e == 25.0:
                continue
            out.append(Case("levers", f"eps{e:g}", seed, RELAXED, f"lever:eps{e:g}:{seed}:{k}",
                            (lambda s=seed, e=e: eps(s, e)), tl, False, "charger_speed",
                            {**common, "lever": "charger_speed", "lever_value": e, "eps_wh": e}, k, 48))
        for M in LEVER_M:
            if M == 1:
                continue
            out.append(Case("levers", f"M{M}", seed, RELAXED, f"lever:M{M}:{seed}:{k}",
                            (lambda s=seed, M=M: pos(s, M)), tl, False, "swap_positions",
                            {**common, "lever": "swap_positions", "lever_value": M, "M": M}, k, 48))
        for share in LOCKOUT_SHARES:
            out.append(Case("levers", f"lockout{share:g}", seed, RELAXED, f"lever:lock{share:g}:{seed}:{k}",
                            (lambda s=seed, sh=share: lock(s, sh)), tl, False, "lockout",
                            {**common, "lever": "lockout", "lever_value": share, "lockout_share": share}, k, 48))
        out.append(Case("levers", "P0", seed, RELAXED, f"lever:P0:{seed}:{k}", (lambda s=seed: power0(s)), tl, False,
                        "site_power", {**common, "lever": "site_power", "lever_value": 0.0, "P_cap_multiple": 0}, k, 48))
    return out


PLANNERS: Dict[str, Callable[[bool], List[Case]]] = {
    "core": plan_core, "boundary": plan_boundary, "fleet": plan_fleet, "levers": plan_levers}


def est_case_s(case: Case, new_library: bool = True, need_ilp: bool = True, need_lp: bool = True
               ) -> Tuple[float, float]:
    """(expected, worst) seconds of a case: rules + checks ~4 s, a library build when the arc
    signature is new (about 1.7 s per million per-bike arcs; r5_stress4h 6 bikes = 3.14 M arcs at
    L 24, 8 h = x 2.2), the LP (r5 probe: 13 s at 6 bikes) and the ILP (6 bikes OPTIMAL in about
    75 s, 8 / 10 bikes and 8 h at the time limit; + about 40 s model build, start check, extraction)."""
    k, H = case.n_bikes, case.H
    L = 24.0 * float(case.info.get("pack_kwh", 0.6)) / 0.6 if "pack_kwh" in case.info else 24.0
    if "eps_wh" in case.info:
        L = 600.0 / float(case.info["eps_wh"])
    arcs_m = 0.523 * k * (L + 1.0) / 25.0 * (2.2 if H > 48 else 1.0)
    base = 4.0 + 0.4 * arcs_m + (1.7 * arcs_m if new_library else 0.0)
    lp_s = 0.0
    if case.lp and need_lp:
        lp_s = 4.5 * arcs_m * (2.0 if H > 48 else 1.0)
    exp = worst = base + lp_s
    if case.ilp_tl and need_ilp:
        typical = {4: 45.0, 6: 100.0}.get(k, case.ilp_tl) if H <= 48 else case.ilp_tl
        exp += min(case.ilp_tl, typical) + 40.0
        worst += case.ilp_tl + 60.0
    return exp, worst


# ---------------------------------------------------------------------------
# LP-relaxation capacity values (integrate-step probe method)
# ---------------------------------------------------------------------------
def lp_capacity_values(inst: Instance, lib: ArcLibrary, threads: int, time_limit: float) -> Dict[str, Any]:
    """LP relaxation of the aggregated E2 model (O1) of ``inst``; the operating value of one more
    spare / charger at site j (USD per window) is ``-RC(B_j) + bB_j`` / ``-RC(C_j) + bC_j``, the
    reduced cost of the fixed size variable minus its own set-up coefficient (27).  Marginal LP
    values, not integer values (DECISIONS R5 "Sizes chosen")."""
    from ebike_swap_sim import ilp
    import gurobipy as gp
    t0 = time.perf_counter()
    mdl = ilp.build_model(inst, lib, threads=threads, time_limit=time_limit, params=dict(ILP_PARAMS), **ILP_KWARGS)
    build_s = time.perf_counter() - t0
    lp = mdl.model.relax()
    lp.Params.OutputFlag = 0
    lp.Params.Threads = int(threads)
    lp.Params.TimeLimit = float(time_limit)
    lp.optimize()
    out: Dict[str, Any] = {"status": "LP_" + ilp.status_name(lp.Status), "lp_runtime_s": float(lp.Runtime),
                           "lp_build_s": build_s, "lp_obj": None, "lp_n_vars": lp.NumVars}
    sink = (inst.meta.get("lockout") or {}).get("sink")
    if lp.Status == gp.GRB.OPTIMAL:
        out["lp_obj"] = float(lp.ObjVal)
        lv = lp.getVars()
        spare: Dict[str, float] = {}
        charger: Dict[str, float] = {}
        for f in inst.facilities:
            if f.id == sink or f.id not in mdl.B:
                continue
            if f.swap or f.charge:
                spare[str(f.id)] = -float(lv[mdl.B[f.id].index].RC) + float(f.bB)
            if f.charge:
                charger[str(f.id)] = -float(lv[mdl.C[f.id].index].RC) + float(f.bC)
        out["lp_spare_value"] = spare
        out["lp_charger_value"] = charger
        for name, d in (("spare", spare), ("charger", charger)):
            vals = list(d.values())
            out[f"lp_{name}_value_mean"] = (sum(vals) / len(vals)) if vals else None
            out[f"lp_{name}_value_min"] = min(vals) if vals else None
            out[f"lp_{name}_value_max"] = max(vals) if vals else None
    for obj in (lp, mdl.model):
        try:
            obj.dispose()
        except Exception:  # noqa: BLE001
            pass
    try:
        mdl.env.dispose()
    except Exception:  # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------------------
# row builders
# ---------------------------------------------------------------------------
def instance_cols(case: Case, w: Instance, t: Instance, key: str) -> Dict[str, Any]:
    sites = [f for f in t.facilities if f.id != (t.meta.get("lockout") or {}).get("sink")]
    lk = t.meta.get("lockout") or {}
    fs = t.meta.get("fleet_sweep") or {}
    return {
        "sub": case.sub, "cell": case.cell, "seed": case.seed, "phase": case.phase, "target": case.target,
        "targets_label": targets_label(t), "written_targets_label": targets_label(w), "key_md5": key,
        "family": t.meta.get("family"), "n_bikes": len(t.bikes), "n_orders": len(t.orders), "H": t.H, "L": t.L,
        "eps_wh": 1000.0 * t.disc.eps_kwh, "pack_kwh": t.L * t.disc.eps_kwh, "p_ch_kw": t.disc.p_ch_kw,
        "rho": t.rho, "R_end_sites": json.dumps({str(f.id): int(f.R_end) for f in sites}),
        "B_sites": json.dumps({str(f.id): f.B for f in sites}), "C_sites": json.dumps({str(f.id): f.C for f in sites}),
        "M_sites": json.dumps({str(f.id): f.M for f in sites if f.swap}),
        "P_kw_sites": json.dumps({str(f.id): f.P_kw for f in sites if f.charge}),
        "total_spares": sum(int(f.B or 0) for f in sites), "n_services_real": len(real_services(t)),
        "bB_site": sites[0].bB if sites else None, "bC_site": sites[0].bC if sites else None,
        "n_locked": lk.get("n_locked"), "lockout_slots": json.dumps(lk.get("slots")) if lk else None,
        "allocated_per_bike_window": (fs.get("allocated_bike_cost") or {}).get("allocated_per_bike_window"),
        "bike_capex_per_window": (fs.get("allocated_bike_cost") or {}).get("bike_capex_per_window"),
        "demand_md5": C.demand_md5(t), "orders_md5": orders_md5(t), "threads": None, **case.info,
    }


def sched_cols(inst: Instance, lib: ArcLibrary, rec: Dict[str, Any]) -> Dict[str, Any]:
    """Cost (26)-(32) + M1 adjustment, metrics, A3 pack, check of one priced schedule."""
    if rec.get("cost") is None or rec.get("schedule") is None:
        return {"total": None, "total_end_adjusted": None}
    met = rec["metrics"]
    unserv = C.unservable_orders(inst, lib)
    n_servable = max(0, len(inst.orders) - len(unserv))
    out: Dict[str, Any] = {
        **C.flatten_cost(rec["cost"]),
        "served_share": met["served_share"], "n_served": met["n_served"], "n_unserved": met["n_unserved"],
        "n_unservable": len(unserv),
        "served_share_servable": (met["n_served"] / n_servable) if n_servable else None,
        "mean_response_h": met["mean_response_h"], "n_late": met["n_late"], "mean_lateness_h": met["mean_lateness_h"],
        "bike_km": met["bike_km"], "n_swaps": met["n_swaps"], "kwh_purchased": met["kwh_purchased"],
        "transfers_used": met["transfers_used"], "end_full_total": met["end_full_total"],
        "end_target_shortfall": met["end_target_shortfall"],
        "stockout_slots_total": int(sum(met["stockout_slots"].values())),
        "stockout_slots": json.dumps({str(j): int(v) for j, v in met["stockout_slots"].items()}),
        "peak_kw_group": json.dumps({str(g): v for g, v in met["peak_kw_group"].items()}),
        "families": json.dumps(rec.get("families") or {}), "check_ok": rec.get("ok"),
        "identity_24_ok": rec.get("identity_24_ok"),
        **swap_occupancy(inst, lib, rec["schedule"]),
        **C.flatten_r5(met),
    }
    if met.get("lockout"):
        out.update({f"lockout_{k}": v for k, v in met["lockout"].items()})
    return out


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
def _is_done(row: Optional[Dict[str, Any]]) -> bool:
    if row is None:
        return False
    st = row.get("status")
    if st in (C.SKIPPED_BUDGET, "ERROR"):
        return False
    if row.get("budget_shortened") and st != "OPTIMAL":
        return False
    return True


class Runner:
    def __init__(self, out_dir: str, threads: int = C.THREADS, lp_time_limit: float = LP_TIME_LIMIT,
                 lib_cache: int = 3) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.threads = int(threads)
        self.lp_time_limit = float(lp_time_limit)
        self.lib_cache = int(lib_cache)
        self.rows: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.sub_rows: Dict[str, Dict[Tuple[str, str], Dict[str, Any]]] = {s: {} for s in SUBS}
        for sub in SUBS:
            for r in C.load_jsonl(self._records(sub)):
                k = (str(r.get("key_md5")), str(r.get("method")))
                self.sub_rows[sub][k] = r
                if _is_done(r) or k not in self.rows:
                    self.rows[k] = r
        self.seen_cases = set()
        for sub in SUBS:
            for c in C.load_jsonl(self._cases(sub)):
                self.seen_cases.add((c["sub"], c["cell"], int(c["seed"]), c["target"], c["key_md5"]))
        self.libs: "OrderedDict[str, ArcLibrary]" = OrderedDict()
        self.lib_build_s: Dict[str, float] = {}
        self.pool: Dict[str, List[Tuple[str, Schedule]]] = {}
        self.inst_cache: "OrderedDict[str, Instance]" = OrderedDict()
        self.budget: Optional[C.WallBudget] = None
        self.n_cases = 0
        self.skipped: List[str] = []

    # -- files -------------------------------------------------------------------------
    def _records(self, sub: str) -> str:
        return os.path.join(self.out_dir, f"records_{sub}.jsonl")

    def _cases(self, sub: str) -> str:
        return os.path.join(self.out_dir, f"cases_{sub}.jsonl")

    def emit(self, sub: str, row: Dict[str, Any]) -> None:
        row = {**row, "threads": self.threads}
        C.append_jsonl(self._records(sub), row)
        k = (str(row["key_md5"]), str(row["method"]))
        self.sub_rows[sub][k] = row
        self.rows[k] = row

    def refresh_csv(self, sub: str) -> None:
        def write(rows: List[Dict[str, Any]], name: str) -> None:
            path = os.path.join(self.out_dir, name)
            tmp = path + ".tmp"
            C.records_to_frame(rows).to_csv(tmp, index=False)
            os.replace(tmp, path)
        write(list(self.sub_rows[sub].values()), f"results_{sub}.csv")
        write(list(self.rows.values()), "results.csv")

    def note_case(self, case: Case, key: str) -> None:
        tag = (case.sub, case.cell, case.seed, case.target, key)
        if tag in self.seen_cases:
            return
        self.seen_cases.add(tag)
        C.append_jsonl(self._cases(case.sub), {"sub": case.sub, "cell": case.cell, "seed": case.seed,
                                                "target": case.target, "key_md5": key, "phase": case.phase,
                                                "ilp_method": ilp_method(case.ilp_tl) if case.ilp_tl else None,
                                                "lp": case.lp, **case.info})

    # -- instances / libraries ---------------------------------------------------------------
    def written(self, case: Case) -> Instance:
        inst = self.inst_cache.get(case.build_id)
        if inst is None:
            inst = case.builder()
            self.inst_cache[case.build_id] = inst
            while len(self.inst_cache) > 12:
                self.inst_cache.popitem(last=False)
        return inst

    def library(self, inst: Instance, pruning: Dict[str, Any]) -> Tuple[ArcLibrary, str, float]:
        sig = arc_signature(inst, pruning)
        lib0 = self.libs.get(sig)
        if lib0 is None:
            gc.collect()
            lib0, bt = C.build_library(inst, pruning)
            self.libs[sig] = lib0
            self.lib_build_s[sig] = bt
            while len(self.libs) > self.lib_cache:
                old, _ = self.libs.popitem(last=False)
                self.pool.pop(old, None)
            gc.collect()
        else:
            self.libs.move_to_end(sig)
        if lib0.inst is inst:
            return lib0, sig, self.lib_build_s.get(sig, float("nan"))
        lib = copy.copy(lib0)            # same arcs and ids; bound to the variant (B, C, M, P, targets)
        lib.inst = inst
        return lib, sig, self.lib_build_s.get(sig, float("nan"))

    def pick_start(self, inst: Instance, lib: ArcLibrary, sig: str, rule_recs: Dict[str, Dict[str, Any]]
                   ) -> Tuple[Optional[Schedule], str]:
        """Cheapest candidate that passes ``evaluate.check`` on ``inst``: the rule schedules of this
        case and earlier ILP / rule schedules on the same arc library (chained starts); else the
        ``common.feasible_mip_start`` fallbacks of the r2 record."""
        cands: List[Tuple[str, Schedule]] = list(self.pool.get(sig, []))   # this case's rules are in the pool
        best: Optional[Tuple[float, str, Schedule]] = None
        forced = inst.options.get("forced_transfers") or []
        for label, s in cands:
            ps = portable(s)
            # evaluate.check does not test the M9 data fixings (h_e >= 1, z_eq >= 1), and
            # ilp.verify_mip_start fixes h / z to the start values (overriding those bounds), so a
            # start without the forced lock-out transfers would pass both and be rejected by Gurobi
            if any(int(ps.h.get(r["service"], 0)) < 1 or (r.get("level") is not None and
                                                          int(ps.z.get((r["service"], int(r["level"])), 0)) < 1)
                   for r in forced):
                continue
            try:
                rep = check(inst, lib, ps)
            except Exception:  # noqa: BLE001 - a candidate that does not fit is simply not used
                continue
            if not rep["ok"]:
                continue
            tot = cost(inst, lib, ps)["total"]
            if best is None or tot < best[0] - 1e-9:
                best = (tot, label, ps)
        if best is not None:
            return best[2], best[1]
        if forced:
            return None, "none_forced"
        r2 = rule_recs.get("r2")
        if r2 is None:
            return None, "none"
        s, lab = C.feasible_mip_start(inst, lib, r2)
        return s, (f"fallback:{lab}" if lab != "default" else "default_unclean")

    def add_pool(self, sig: str, label: str, sched: Schedule) -> None:
        lst = self.pool.setdefault(sig, [])
        lst.append((label, portable(sched)))
        del lst[:-12]

    # -- one case ------------------------------------------------------------------------------
    def case_status(self, case: Case) -> Tuple[Instance, Instance, str, Dict[str, Any], List[str]]:
        w = self.written(case)
        t = target_copy(w, case.target)
        pr = C.pruning_for(t)
        key = content_key(t, pr)
        methods = [f"baseline_{r}" for r in rules_for(t)] + ["best_rule"]
        if case.lp:
            methods.append("LP")
        if case.ilp_tl:
            methods.append(ilp_method(case.ilp_tl))
        todo = [m for m in methods if not _is_done(self.rows.get((key, m)))]
        return w, t, key, pr, todo

    def run_case(self, case: Case) -> Dict[str, Any]:
        t_case = time.perf_counter()
        w, t, key, pr, todo = self.case_status(case)
        self.note_case(case, key)
        assert C.demand_md5(t) == C.demand_md5(w), "target copy changed the demand"
        summary: Dict[str, Any] = {"sub": case.sub, "cell": case.cell, "seed": case.seed, "target": case.target,
                                   "key": key[:8]}
        if not todo:
            summary["reused"] = True
            return summary
        base = instance_cols(case, w, t, key)
        bud = self.budget
        if bud is not None and bud.remaining() < 30.0:
            for m in todo:
                self.emit(case.sub, {**base, "method": m, "status": C.SKIPPED_BUDGET,
                                     "skip_reason": f"wall budget exhausted after {bud.elapsed():.0f}s"})
            self.skipped.append(f"{case.sub}:{case.cell}:s{case.seed}:{case.target}")
            summary["status"] = C.SKIPPED_BUDGET
            return summary
        lib, sig, bt = self.library(t, pr)
        base.update(n_arcs=len(lib), lib_build_s=bt)
        dmd5 = C.demand_md5(t)
        # -- rules (always re-run: ms, needed for gaps and starts) ----------------------------
        rule_recs: Dict[str, Dict[str, Any]] = {}
        rule_rows: Dict[str, Dict[str, Any]] = {}
        w_lib = None
        if case.target != "written":
            w_lib, _sig_w, _ = self.library(w, C.pruning_for(w))
        for r in rules_for(t):
            rec = C.run_baseline_case(t, lib, C.baseline_variant_params(RULE_VARIANT[r], t), label=r)
            assert C.demand_md5(lib.inst) == dmd5
            rule_recs[r] = rec
            row = {**base, "method": f"baseline_{r}", "rule": r, "status": "OK", "runtime_s": rec["runtime"],
                   "policy_reserve_source": rec.get("policy_reserve_source"),
                   "ok_modulo_report_only": rec["ok_modulo_report_only"],
                   **{f"flag_{k}": v for k, v in rec["pruning_flags"].items()},
                   "flag_outages": _count(rec["flags"].get("outages")),
                   **sched_cols(t, lib, rec)}
            if w_lib is not None:
                rw = check(w, w_lib, portable(rec["schedule"]))
                row["families_written"] = json.dumps(C.family_counts(rw))
            else:
                row["families_written"] = row["families"]
            rule_rows[r] = row
            self.add_pool(sig, f"rule:{r}@{case.cell}:{case.target}", rec["schedule"])
            if f"baseline_{r}" in todo:
                self.emit(case.sub, row)
        best_r = min(rule_rows, key=lambda r: (rule_rows[r]["total"], RULES.index(r)))
        best_adj_r = min(rule_rows, key=lambda r: (rule_rows[r]["total_end_adjusted"], RULES.index(r)))
        best_row = {**rule_rows[best_r], "method": "best_rule", "rule": best_r,
                    "best_rule_end_adjusted_rule": best_adj_r,
                    "best_rule_total_end_adjusted_min": rule_rows[best_adj_r]["total_end_adjusted"],
                    "rule_totals": json.dumps({r: rule_rows[r]["total"] for r in rule_rows})}
        if "best_rule" in todo:
            self.emit(case.sub, best_row)
        summary.update(best_rule=best_r, best_rule_total=round(best_row["total"], 3),
                       r2_total=round(rule_rows["r2"]["total"], 3), r5_total=round(rule_rows["r5"]["total"], 3))
        # -- LP capacity values ------------------------------------------------------------
        if "LP" in todo:
            if bud is not None and bud.remaining() < bud.margin + 60.0:
                self.emit(case.sub, {**base, "method": "LP", "status": C.SKIPPED_BUDGET,
                                     "skip_reason": f"wall budget after {bud.elapsed():.0f}s"})
            else:
                lpr = lp_capacity_values(t, lib, self.threads, self.lp_time_limit)
                self.emit(case.sub, {**base, "method": "LP", **lpr, "lp_time_limit": self.lp_time_limit,
                                     "runtime_s": lpr["lp_runtime_s"]})
                summary["lp_spare"] = lpr.get("lp_spare_value_mean")
                summary["lp_charger"] = lpr.get("lp_charger_value_mean")
                gc.collect()
        # -- ILP -----------------------------------------------------------------------------
        m_ilp = ilp_method(case.ilp_tl) if case.ilp_tl else None
        if m_ilp and m_ilp in todo:
            tl = float(case.ilp_tl)
            tl_used = bud.solve_limit(tl) if bud is not None else tl
            if tl_used is None:
                self.emit(case.sub, {**base, "method": m_ilp, "status": C.SKIPPED_BUDGET, "time_limit": tl,
                                     "skip_reason": f"wall budget exhausted after {bud.elapsed():.0f}s"})
                self.skipped.append(f"{case.sub}:{case.cell}:s{case.seed}:{case.target}:{m_ilp}")
                summary["ilp_status"] = C.SKIPPED_BUDGET
            else:
                start, start_label = self.pick_start(t, lib, sig, rule_recs)
                rec = C.run_ilp_case(t, lib, mip_start=start, time_limit=tl_used, threads=self.threads,
                                     label=m_ilp, params=dict(ILP_PARAMS), **ILP_KWARGS)
                st = rec["stats"]
                row = {**base, "method": m_ilp, "status": rec["status"], "obj": rec["obj"], "bound": rec["bound"],
                       "gap": rec["gap"], "runtime_s": rec["runtime"], "build_time_s": rec["build_time"],
                       "n_vars": rec["n_vars"], "n_binaries": rec["n_binaries"], "n_rows": rec["n_rows"],
                       "n_agg_arcs": st.get("n_agg_arcs"), "aggregate": bool((st.get("switches") or {}).get("aggregate")),
                       "forced_transfers_fixed": (st.get("switches") or {}).get("forced_transfers"),
                       "time_limit": tl, "time_limit_used_s": tl_used, "budget_shortened": tl_used < tl - 1e-6,
                       "mip_start_variant": start_label, "mip_start_accepted": rec["mip_start_accepted"],
                       "mip_start_verified_status": (rec["mip_start_info"] or {}).get("verified_status"),
                       **sched_cols(t, lib, rec)}
                tot, adj = row.get("total"), row.get("total_end_adjusted")
                for r in ("r2", "r5"):
                    row[f"gap_vs_{r}_pct"] = pct_gap(rule_rows[r]["total"], tot)
                    row[f"gap_vs_{r}_pct_end_adjusted"] = pct_gap(rule_rows[r]["total_end_adjusted"], adj)
                row["best_rule"] = best_r
                row["best_rule_total"] = best_row["total"]
                row["gap_vs_best_rule_pct"] = pct_gap(best_row["total"], tot)
                row["gap_vs_best_rule_pct_end_adjusted"] = pct_gap(best_row["best_rule_total_end_adjusted_min"], adj)
                row["ilp_le_best_rule"] = None if tot is None else bool(tot <= best_row["total"] + 1e-6)
                self.emit(case.sub, row)
                if rec["schedule"] is not None:
                    self.add_pool(sig, f"ilp:{case.cell}:{case.target}", rec["schedule"])
                summary.update(ilp_status=rec["status"], ilp_total=None if tot is None else round(tot, 3),
                               ilp_gap=rec["gap"], ilp_runtime_s=round(rec["runtime"], 1), start=start_label,
                               gap_vs_best_rule_pct=row["gap_vs_best_rule_pct"])
                del rec
                gc.collect()
        summary["wall_s"] = round(time.perf_counter() - t_case, 1)
        return summary

    def run_plan(self, sub: str, plan: Sequence[Case], budget_s: float) -> None:
        self.budget = C.WallBudget(budget_s)
        self.skipped = []
        self.lib_cache = LIB_CACHE.get(sub, 2)
        while len(self.libs) > self.lib_cache:
            old, _ = self.libs.popitem(last=False)
            self.pool.pop(old, None)
        gc.collect()
        for case in plan:
            try:
                s = self.run_case(case)
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001 - record and continue (long unattended run)
                tb = traceback.format_exc(limit=6)
                try:
                    w = self.written(case)
                    t = target_copy(w, case.target)
                    key = content_key(t, C.pruning_for(t))
                except Exception:  # noqa: BLE001
                    key = f"error:{case.sub}:{case.cell}:{case.seed}:{case.target}"
                self.emit(sub, {"sub": case.sub, "cell": case.cell, "seed": case.seed, "target": case.target,
                                "key_md5": key, "method": "case_error", "status": "ERROR",
                                "error": f"{type(exc).__name__}: {exc}", "traceback": tb})
                s = {"sub": case.sub, "cell": case.cell, "seed": case.seed, "target": case.target,
                     "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
            self.n_cases += 1
            self.refresh_csv(sub)
            print(json.dumps({k: C.jsonable(v) for k, v in s.items()}), flush=True)
        wall = self.budget.elapsed()
        with open(os.path.join(self.out_dir, "wall_time.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"sub": sub, "wall_s": wall, "budget_s": budget_s, "n_cases": len(plan),
                                 "skipped": self.skipped, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
        print(f"# {sub}: {len(plan)} cases in {wall / 60:.1f} min; skipped {len(self.skipped)}", flush=True)


# ---------------------------------------------------------------------------
# dry run
# ---------------------------------------------------------------------------
def dry_run(subs: Sequence[str], out_dir: str, smoke: bool) -> Dict[str, Any]:
    runner = Runner(out_dir) if os.path.isdir(out_dir) else None
    summary: Dict[str, Any] = {"out_dir": out_dir, "smoke": smoke, "subs": {}}
    cache: Dict[str, Instance] = {}
    seen_keys: set = set()
    seen_methods: set = set()
    for sub in subs:
        plan = PLANNERS[sub](smoke)
        n_ilp = n_lp = n_reused = n_dup = 0
        exp = worst = 0.0
        orders_by_seed: Dict[int, set] = {}
        libs: "OrderedDict[str, None]" = OrderedDict()
        print(f"# {sub}: {len(plan)} cases (cell, seed, target, ILP method, LP, sizes, key, methods to run)")
        for case in plan:
            w = cache.get(case.build_id)
            if w is None:
                w = case.builder()
                cache[case.build_id] = w
            t = target_copy(w, case.target)
            pr = C.pruning_for(t)
            key = content_key(t, pr)
            sig = arc_signature(t, pr)
            assert C.demand_md5(t) == C.demand_md5(w)
            orders_by_seed.setdefault(case.seed, set()).add(orders_md5(t))
            methods = [f"baseline_{r}" for r in rules_for(t)] + ["best_rule"] + (["LP"] if case.lp else []) \
                + ([ilp_method(case.ilp_tl)] if case.ilp_tl else [])
            todo = [m for m in methods if (runner is None or not _is_done(runner.rows.get((key, m))))
                    and (key, m) not in seen_methods]
            n_dup += int(any((key, m) in seen_methods for m in methods))
            seen_methods.update((key, m) for m in methods)
            if not todo:
                n_reused += 1
            new_lib = sig not in libs
            libs[sig] = None
            libs.move_to_end(sig)
            while len(libs) > LIB_CACHE.get(sub, 2):
                libs.popitem(last=False)
            m_ilp = ilp_method(case.ilp_tl) if case.ilp_tl else None
            if todo:
                e, wst = est_case_s(case, new_lib, m_ilp in todo, "LP" in todo)
                exp += e
                worst += wst
            n_ilp += int(m_ilp is not None and m_ilp in todo)
            n_lp += int("LP" in todo)
            print(f"   {case.cell:28s} s{case.seed} {case.target:10s} {m_ilp or '-':10s} "
                  f"LP={int(case.lp)} L={t.L:2d} K={len(t.bikes):2d} I={len(t.orders):3d} key={key[:8]} "
                  f"{('run:' + ','.join(todo)) if todo else 'reused'}")
        budget = SMOKE_BUDGET_MIN if smoke else WALL_BUDGET_MIN[sub]
        summary["subs"][sub] = {"cases": len(plan), "ilp_solves": n_ilp, "lp_solves": n_lp,
                                "cases_fully_reused": n_reused, "cases_sharing_rows_with_earlier_cases": n_dup,
                                "expected_wall_min": round(exp / 60.0, 1), "worst_wall_min": round(worst / 60.0, 1),
                                "budget_min": budget,
                                "orders_identical_per_seed": ({s: len(v) == 1 for s, v in orders_by_seed.items()}
                                                              if sub != "core" else "n/a (several families)")}
    summary["expected_wall_min_total"] = round(sum(min(v["expected_wall_min"], v["budget_min"])
                                                   for v in summary["subs"].values()), 1)
    print(json.dumps(summary, indent=1))
    return summary


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
_WIDE_FIELDS = ("status", "total", "total_end_adjusted", "C_end_adjust", "C_setup", "C_elec", "C_travel",
                "C_orders", "unserved", "response", "lateness", "served_share", "stockout_slots_total", "n_swaps",
                "r5_outage_rate", "r5_mean_sbur", "r5_empty_km_per_bike_hour", "families", "families_written",
                "peak_swap_occupancy_ratio")
_ILP_FIELDS = ("status", "obj", "bound", "gap", "runtime_s", "total", "total_end_adjusted", "C_end_adjust",
               "served_share", "stockout_slots_total", "gap_vs_r2_pct", "gap_vs_r5_pct", "gap_vs_best_rule_pct",
               "gap_vs_r2_pct_end_adjusted", "gap_vs_r5_pct_end_adjusted", "gap_vs_best_rule_pct_end_adjusted",
               "mip_start_variant", "time_limit", "peak_swap_occupancy_ratio", "r5_outage_rate", "r5_mean_sbur",
               "lockout_end_share_excl_sink", "n_vars")
_LP_FIELDS = ("status", "lp_obj", "lp_spare_value_mean", "lp_spare_value_min", "lp_spare_value_max",
              "lp_charger_value_mean", "lp_charger_value_min", "lp_charger_value_max", "lp_runtime_s")


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def wide_cases(out_dir: str) -> pd.DataFrame:
    rows: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for sub in SUBS:
        for r in C.load_jsonl(os.path.join(out_dir, f"records_{sub}.jsonl")):
            k = (str(r.get("key_md5")), str(r.get("method")))
            if _is_done(r) or k not in rows:
                rows[k] = r
    cases: Dict[Tuple, Dict[str, Any]] = {}
    for sub in SUBS:
        for c in C.load_jsonl(os.path.join(out_dir, f"cases_{sub}.jsonl")):
            cases[(c["sub"], c["cell"], int(c["seed"]), c["target"])] = c
    out: List[Dict[str, Any]] = []
    for (_sub, _cell, _seed, _tgt), c in cases.items():
        key = c["key_md5"]
        w: Dict[str, Any] = {k: v for k, v in c.items()}
        anyrow = next((rows[(key, m)] for m in ("best_rule", "baseline_r2") if (key, m) in rows), None)
        if anyrow is not None:
            for f in ("n_bikes", "n_orders", "H", "L", "eps_wh", "pack_kwh", "p_ch_kw", "bB_site", "bC_site",
                      "total_spares", "n_locked",
                      "allocated_per_bike_window", "bike_capex_per_window", "demand_md5", "orders_md5",
                      "targets_label", "rho"):
                w[f] = anyrow.get(f)
        for r in RULES + ("best_rule",):
            m = "best_rule" if r == "best_rule" else f"baseline_{r}"
            row = rows.get((key, m))
            if row is None:
                continue
            for f in _WIDE_FIELDS:
                w[f"{r}_{f}"] = row.get(f)
            if r == "best_rule":
                w["best_rule_rule"] = row.get("rule")
                w["best_rule_total_end_adjusted_min"] = row.get("best_rule_total_end_adjusted_min")
        im = c.get("ilp_method")
        if im and (key, im) in rows:
            row = rows[(key, im)]
            for f in _ILP_FIELDS:
                w[f"ilp_{f}"] = row.get(f)
        if (key, "LP") in rows:
            row = rows[(key, "LP")]
            for f in _LP_FIELDS:
                w[f"lp_{f}" if not f.startswith("lp_") else f] = row.get(f)
        out.append(w)
    return pd.DataFrame(out)


def _mean_table(df: pd.DataFrame, by: List[str], cols: List[str]) -> pd.DataFrame:
    d = df.copy()
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d.columns else float("nan")
    g = d.groupby(by, dropna=False)
    out = g[cols].mean().reset_index()
    out.insert(len(by), "n_seeds", g.size().values)
    return out


def analyse(out_dir: str) -> str:
    df = wide_cases(out_dir)
    if df.empty:
        raise SystemExit(f"no cases recorded in {out_dir}")
    df.to_csv(os.path.join(out_dir, "cases_wide.csv"), index=False)
    md: List[str] = ["# X5 -- stressed family, boundary grid, fleet x spare x pack, levers (round 5)", "",
                     "Generated by `experiments/r5_x5_stress.py --analyse`. Totals in USD per window (E2 (26)); "
                     "`*_end_adjusted` = total + C_end_adjust (M1, reporting only); gaps = 100 (baseline - ILP) / baseline; "
                     "best_rule = min over r2, r5_range, r5_transfer (only with transport services) and r5 by total; "
                     "headline = relaxed control rho0_R0. Means over the seeds present (n_seeds).", ""]
    gapcols = ["best_rule_total", "r2_total", "r5_total", "ilp_total", "ilp_gap", "ilp_gap_vs_best_rule_pct",
               "ilp_gap_vs_r2_pct", "ilp_gap_vs_r5_pct", "ilp_gap_vs_best_rule_pct_end_adjusted",
               "best_rule_C_end_adjust", "ilp_C_end_adjust", "best_rule_served_share", "ilp_served_share",
               "best_rule_stockout_slots_total", "ilp_stockout_slots_total"]
    # core
    core = df[df["sub"] == "core"]
    if not core.empty:
        t = _mean_table(core, ["cell", "target"], gapcols + ["lp_spare_value_mean", "lp_charger_value_mean"])
        t.to_csv(os.path.join(out_dir, "summary_core.csv"), index=False)
        md += ["## Core (M5 stressed family)", "", C.markdown_table(t, list(t.columns), 2), ""]
        piv = core.pivot_table(index=["cell", "seed"], columns="target", values="ilp_total_end_adjusted",
                               aggfunc="first")
        if "written" in piv.columns and RELAXED in piv.columns:
            por = (pd.to_numeric(piv["written"], errors="coerce") - pd.to_numeric(piv[RELAXED], errors="coerce"))
            por = por.reset_index(name="price_of_recovery_end_adjusted").dropna()
            por.to_csv(os.path.join(out_dir, "core_price_of_recovery.csv"), index=False)
            if not por.empty:
                md += ["Price of recovery (ILP written - ILP relaxed, end-adjusted totals):", "",
                       C.markdown_table(por, list(por.columns), 2), ""]
    # boundary
    bnd = df[df["sub"] == "boundary"].copy()
    if not bnd.empty:
        ref = bnd[bnd["target"] == RELAXED].set_index("seed")
        for col in ("ilp_total", "ilp_total_end_adjusted"):
            bnd[f"price_of_recovery_{col[4:]}"] = [
                (_num(r[col]) - _num(ref.loc[r["seed"], col])) if (r["seed"] in ref.index and _num(r[col]) is not None
                                                                    and _num(ref.loc[r["seed"], col]) is not None)
                else None for _, r in bnd.iterrows()]
        t = _mean_table(bnd, ["target"], ["ilp_total", "ilp_total_end_adjusted", "price_of_recovery_total",
                                          "price_of_recovery_total_end_adjusted", "ilp_gap", "ilp_C_end_adjust",
                                          "best_rule_total", "ilp_gap_vs_best_rule_pct",
                                          "ilp_gap_vs_best_rule_pct_end_adjusted", "ilp_served_share"])
        viol = bnd.groupby("target")["best_rule_families"].agg(lambda s: "; ".join(sorted(set(map(str, s)))))
        t["best_rule_families"] = t["target"].map(viol)
        order = {lab: i for i, lab in enumerate(boundary_specs())}
        t = t.sort_values("target", key=lambda s: s.map(order)).reset_index(drop=True)
        t.to_csv(os.path.join(out_dir, "summary_boundary.csv"), index=False)
        md += ["## Boundary grid (M1, r5_stress4h 6 bikes)", "", C.markdown_table(t, list(t.columns), 2), ""]
    # fleet
    fl = df[df["sub"] == "fleet"].copy()
    if not fl.empty:
        fl["alloc"] = pd.to_numeric(fl.get("allocated_per_bike_window"), errors="coerce")
        for pol in ("best_rule", "ilp"):
            col = f"{pol}_total_end_adjusted"
            if col in fl.columns:
                fl[f"{pol}_system_cost"] = pd.to_numeric(fl[col], errors="coerce") + fl["alloc"] * fl["K"].astype(float)
        t = _mean_table(fl, ["K", "B_per_site", "pack_kwh"],
                        ["best_rule_total", "best_rule_total_end_adjusted", "best_rule_served_share",
                         "best_rule_system_cost", "ilp_total", "ilp_total_end_adjusted", "ilp_served_share",
                         "ilp_system_cost", "ilp_gap", "ilp_gap_vs_best_rule_pct"])
        t.to_csv(os.path.join(out_dir, "summary_fleet.csv"), index=False)
        fr = fleet_frontier(fl)
        fr.to_csv(os.path.join(out_dir, "fleet_frontier.csv"), index=False)
        md += ["## Fleet x spare x pack (A6)", "", C.markdown_table(t, list(t.columns), 2), "",
               "Iso-cost frontier (seed means; `dV_bike` = operating saving of one more bike = "
               "(V(K) - V(K+2)) / 2, `dV_spare` = saving of one more spare = (V(B) - V(B+1)) / sites, V = "
               "total_end_adjusted incl. the spares' set-up cost (27); `bike_net` = dV_bike - allocated bike cost; "
               "`spares_per_bike_cost` = allocated bike cost / bB):", "",
               C.markdown_table(fr, list(fr.columns), 2) if not fr.empty else "-", ""]
    # levers
    lv = df[df["sub"] == "levers"].copy()
    if not lv.empty:
        ref = lv[lv["cell"] == "reference"].set_index("seed")
        for col in ("ilp_total", "ilp_total_end_adjusted", "best_rule_total"):
            lv[f"delta_{col}"] = [(_num(r[col]) - _num(ref.loc[r["seed"], col]))
                                  if (r["seed"] in ref.index and _num(r.get(col)) is not None
                                      and _num(ref.loc[r["seed"], col]) is not None) else None
                                  for _, r in lv.iterrows()]
        t = _mean_table(lv, ["lever", "cell"], ["ilp_total", "ilp_gap", "delta_ilp_total",
                                                "delta_ilp_total_end_adjusted", "best_rule_total",
                                                "delta_best_rule_total", "ilp_gap_vs_best_rule_pct",
                                                "ilp_served_share", "best_rule_served_share",
                                                "ilp_peak_swap_occupancy_ratio", "ilp_lockout_end_share_excl_sink"])
        t.to_csv(os.path.join(out_dir, "summary_levers.csv"), index=False)
        md += ["## Levers (M9, M10; r5_stress4h 8 bikes, relaxed control)", "", C.markdown_table(t, list(t.columns), 2), ""]
        dc = demand_charge_table(lv)
        if not dc.empty:
            dc.to_csv(os.path.join(out_dir, "demand_charge_proxy.csv"), index=False)
            md += ["Demand-charge proxy (M10(b); V(p_ch) = reference row, since C_j = 1 makes P_j = p_ch and 4 kW "
                   "equivalent in (20); tariffs are assumptions):", "", C.markdown_table(dc, list(dc.columns), 3), ""]
    path = os.path.join(out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


def fleet_frontier(fl: pd.DataFrame) -> pd.DataFrame:
    """Marginal value of one more bike vs one more spare per (pack, K, B), for each policy."""
    out: List[Dict[str, Any]] = []
    for pol in ("best_rule", "ilp"):
        col = f"{pol}_total_end_adjusted"
        if col not in fl.columns:
            continue
        d = fl[["seed", "K", "B_per_site", "pack_kwh", "alloc", "bB_site", col]].copy()
        d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=[col])
        if d.empty:
            continue
        V = d.groupby(["pack_kwh", "K", "B_per_site"])[col].mean()
        A = d.groupby(["pack_kwh", "K", "B_per_site"])["alloc"].mean()
        BB = pd.to_numeric(d["bB_site"], errors="coerce").groupby([d["pack_kwh"], d["K"], d["B_per_site"]]).mean()
        n_sites = 3
        for (pack, K, B), v in V.items():
            row: Dict[str, Any] = {"policy": pol, "pack_kwh": pack, "K": K, "B_per_site": B, "V": v}
            vk = V.get((pack, K + 2, B))
            vb = V.get((pack, K, B + 1))
            row["dV_bike"] = None if vk is None else (v - vk) / 2.0
            row["dV_spare"] = None if vb is None else (v - vb) / n_sites
            a = A.get((pack, K, B))
            row["alloc_per_bike"] = a
            row["bike_net"] = None if row["dV_bike"] is None or a is None or math.isnan(a) else row["dV_bike"] - a
            bB = BB.get((pack, K, B))
            row["bB_per_spare"] = bB
            row["spares_per_bike_cost"] = (None if a is None or bB is None or math.isnan(a) or math.isnan(bB) or bB <= 0
                                           else a / bB)
            if row["bike_net"] is not None and row["dV_spare"] is not None:
                row["cheaper_lever"] = "bike" if row["bike_net"] > row["dV_spare"] else "spare"
            out.append(row)
    return pd.DataFrame(out)


def demand_charge_table(lv: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    p_ch = None
    try:
        p_ch = float(pd.to_numeric(lv["p_ch_kw"], errors="coerce").dropna().iloc[0]) if "p_ch_kw" in lv else None
    except IndexError:
        p_ch = None
    if p_ch is None:
        p_ch = 0.025 / 0.9 / (5.0 / 60.0)
    for seed, g in lv.groupby("seed"):
        refr = g[g["cell"] == "reference"]
        p0 = g[g["cell"] == "P0"]
        if refr.empty or p0.empty:
            continue
        for pol in ("ilp", "best_rule"):
            vals = {0.0: _num(p0.iloc[0].get(f"{pol}_total")), p_ch: _num(refr.iloc[0].get(f"{pol}_total"))}
            for tariff in DEMAND_TARIFFS:
                prox = cost_mod.demand_charge_proxy(vals, tariff, window_h=4.0, n_sites=3)
                best = prox["best"] or {}
                rows.append({"seed": seed, "policy": pol, "usd_per_kw_month": tariff,
                             "p_dem_per_kw_window": prox["p_dem_per_kw_window"],
                             "V_P0": vals[0.0], "V_Pch": vals[p_ch], "best_P_kw": best.get("P_kw"),
                             "best_total": best.get("total")})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for sub in SUBS:
        ap.add_argument(f"--{sub}", action="store_true")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--budget-scale", type=float, default=1.0, help="multiply every sub-command's wall budget")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="seed 0, reduced cells, ILP TimeLimit 20 s, LP 60 s (use --out-dir on a scratch folder)")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    if args.threads > 3:
        raise SystemExit("round-5 protocol: Threads <= 3")
    subs = [s for s in SUBS if getattr(args, s)]
    out_dir = args.out_dir or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse and not subs:
        print(analyse(out_dir))
        return {"analysed": out_dir}
    if not subs:
        raise SystemExit("choose at least one of --core --boundary --fleet --levers (or --analyse)")
    if args.dry_run:
        return dry_run(subs, out_dir, args.smoke)
    runner = Runner(out_dir, threads=args.threads, lp_time_limit=SMOKE_LP_TL if args.smoke else LP_TIME_LIMIT)
    t0 = time.perf_counter()
    for sub in subs:
        plan = PLANNERS[sub](args.smoke)
        budget = 60.0 * (SMOKE_BUDGET_MIN if args.smoke else WALL_BUDGET_MIN[sub]) * float(args.budget_scale)
        print(f"# {sub}: {len(plan)} cases, wall budget {budget / 60:.0f} min, Threads {args.threads}, "
              f"out {out_dir}", flush=True)
        runner.run_plan(sub, plan, budget)
    print(f"# X5 finished: {runner.n_cases} cases in {(time.perf_counter() - t0) / 60:.1f} min", flush=True)
    try:
        print(analyse(out_dir))
    except Exception as exc:  # noqa: BLE001
        print(f"# analyse failed: {type(exc).__name__}: {exc}", flush=True)
    return {"out_dir": out_dir, "cases": runner.n_cases}


if __name__ == "__main__":
    main()
