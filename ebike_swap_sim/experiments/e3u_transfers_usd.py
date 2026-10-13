"""Experiment E3u -- value of battery transfers and of separating charging hubs from
swap sites under USD costs, 4 h window (round 2; DECISIONS.md R2.1 / R2.2 / R2.3).

Question
--------
Round 1 (``outputs/e3/``, toy units, 2 h window) found that the whole value of
transfers was a *recovery-target* effect: with the end targets (17)-(18) relaxed the
separated layouts served every order with zero transfers.  E3u repeats the layout x
transfer-switch design on the round-2 family ``usd4h`` (6 bikes / 36 orders / H = 48 /
L = 12, dinner window 17:00-21:00, ``usd_sunk`` costs, ``B_j = 3`` at every swap site,
R2.2) and runs the relaxed control (``rho = 0``, ``R_end_j = 0``) for *every* layout and
*both* switches, so that the within-horizon replenishment value of transfers,
``cost(h = z = 0) - cost(transfers free)`` under the relaxed targets, is separated from
the recovery-target effect, the same difference under the written targets.

Layouts (equal totals: ``sum_j B_j = 9`` full spares, ``sum_j C_j = 6`` chargers, the
same 8 kW / 6 kW (18-20 h) grid group in every layout; byte-identical bikes, orders,
restaurants, routes per seed):

``colocated``
    (a) three co-located swap+charge sites at the busiest restaurant zones, ``B_j = 3``,
    ``C_j = 2`` (R2.2 defaults), grid group ``sites``; site <-> site shuttles every 6
    slots so that the transfer switch is meaningful here too.
``separated_1hub``
    (b) the same three sites swap-only (``B_j = 3``, ``C_j = 0``, R2.2) plus one
    charge-only hub at the sub-grid centre holding all 6 chargers and ``--hub-spares``
    (default 0) initial spares; grid group ``hub1`` with the sites' 8 / 6 kW profile;
    shuttles hub <-> site every 6 slots.
``separated_2hubs``
    (c) as (b) with two hubs (3 + 3 chargers) sharing one grid group ``hubs``.

Shuttles (10): departures every 6 slots from boundary 2, duration ``ceil((route + 10
min) / Delta)``, ``U_e = 6``; ``f_e = 20 USD`` and ``v_reb = 1 USD`` per battery come from
the ``usd_sunk`` calibration (R2.1) and are NOT overridden here.

Methods per layout, seed and end-target setting (``written`` = rho 0.5, R_end 1;
``relaxed`` = rho 0, R_end 0 via :func:`experiments.common.relax_end_targets`):

* baseline policy with the R2.3 default rules (``transfer_rule = NONE``) and the
  ``REORDER_POINT`` variant ((9)/(17)/(18) reported, not enforced);
* E2 ILP (5)-(22), (26)-(32), unchanged, with transfers free and with the
  ``no_transfers`` switch (``h = z = 0``); the Gurobi MIP start is the first *clean*
  baseline schedule among the documented variants (``mip_start_variant`` column).

Headline gap: ``100 (baseline - ILP) / baseline`` (``gap_vs_baseline_*_pct``).  Every
schedule is priced by ``evaluate.cost`` and verified by ``evaluate.check``.  Gurobi:
``OutputFlag 0``, ``Threads 3``, ``TimeLimit <= 300 s``; the ``--wall-budget`` guard
(default 57 min) shortens or skips the remaining solves (``status = SKIPPED_BUDGET``).

Outputs (``outputs/e3u/``): ``results.csv`` (one row per run, written incrementally),
``instances/*.json``, ``RESULTS.md``, ``fig_cost_by_layout.png``,
``fig_cost_components.png``, ``fig_transfer_value.png``, ``fig_full_stock_<targets>_seed<s>.png``,
``fig_in_transit.png``, ``fig_grid_load_seed<s>.png`` (figures are drawn from
``results.csv`` alone: ``--figures-only`` redraws them).

Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/e3u_transfers_usd.py [--seeds 0 1 2] [--time-limit 300]
        [--hub-spares 0] [--wall-budget 3420] [--probe]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from experiments import common as C  # noqa: E402
from experiments.common import plt  # noqa: E402  (Agg backend already selected)
from ebike_swap_sim import ArcLibrary, Instance, Schedule  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e3u")
FAMILY = "usd4h"
LAYOUTS: Tuple[str, ...] = ("colocated", "separated_1hub", "separated_2hubs")
LAYOUT_LABEL = {"colocated": "(a) co-located 3 sites",
                "separated_1hub": "(b) 3 swap sites + 1 hub",
                "separated_2hubs": "(c) 3 swap sites + 2 hubs"}
TARGETS: Tuple[str, ...] = ("written", "relaxed")
TARGET_LABEL = {"written": "written targets (rho 0.5, R_end 1)", "relaxed": "relaxed (rho 0, R_end 0)"}
#: R2.2: every swap site holds ``B_j = 3`` spares; co-located sites ``C_j = 2``.
SITE_B = 3
SITE_C = 2
N_SITES = 3
TOTAL_SPARES = SITE_B * N_SITES          # 9, equal in every layout (hubs add --hub-spares, default 0)
TOTAL_CHARGERS = SITE_C * N_SITES        # 6, equal in every layout
HUB_SPARES = 0
SHUTTLE_EVERY = 6
SHUTTLE_FIRST = 2
SERVICE_U = 6
GRID_KW, GRID_PEAK_KW = 8.0, 6.0
#: Baseline variants per transfer rule (``experiments.common.BASELINE_VARIANTS`` names).
BASELINE_RUNS: Tuple[Tuple[str, str], ...] = (("baseline", "NONE"), ("baseline_reorder", "REORDER_POINT"))
#: MIP-start candidates per ILP switch, tried in order until one passes ``check`` cleanly
#: (variant name of ``common.BASELINE_VARIANTS``, transfer rule).  A NONE schedule is
#: feasible for both switches; a REORDER_POINT schedule only when transfers are free.
START_CANDIDATES: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "free": (("baseline_reorder", "REORDER_POINT"), ("baseline", "NONE"),
             ("baseline_round1", "REORDER_POINT"), ("baseline_round1", "NONE"),
             ("baseline_reserve", "REORDER_POINT"), ("baseline_reserve", "NONE")),
    "none": (("baseline", "NONE"), ("baseline_round1", "NONE"), ("baseline_reserve", "NONE")),
}
WALL_BUDGET_S = 57 * 60.0
MIN_SOLVE_S = 30.0


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def _split(total: int, parts: int) -> List[int]:
    """Split ``total`` into ``parts`` integers differing by at most one (largest first)."""
    base, rem = divmod(total, parts)
    return [base + (1 if i < rem else 0) for i in range(parts)]


def make_layout_instance(seed: int, layout: str, hub_spares: int = HUB_SPARES,
                         family: str = FAMILY, site_B: int = SITE_B, total_chargers: int = TOTAL_CHARGERS,
                         **size_overrides: Any) -> Instance:
    """``usd4h`` instance (R2.2: 6 bikes, 4 h, 1.5 orders per bike-hour, ``usd_sunk`` R2.1)
    in one of the three E3u layouts with equal totals ``sum_j B_j = 3 site_B + hub_spares``
    and ``sum_j C_j = total_chargers`` and the same grid profile (E2 (7)-(8), (15)-(18),
    (20)-(21); services (10)).

    Bikes, orders, restaurants and routes depend on the seed only; the layouts differ in
    the roles ``S`` / ``C``, the placement of spares / chargers, the grid groups and the
    offered services.  Swap-only sites get ``B_j = site_B``, ``C_j = 0`` (R2.2); hubs
    ``B = hub_spares`` split equally, ``C = total_chargers`` split equally, ``R_end = 0``.
    The instance validates and round-trips through JSON (byte-identical for ILP and
    baseline).  ``size_overrides`` (e.g. ``n_bikes``) override the family knobs.
    """
    if layout not in LAYOUTS:
        raise KeyError(f"unknown layout {layout!r}")
    n_hubs = {"colocated": 0, "separated_1hub": 1, "separated_2hubs": 2}[layout]
    site_Bs = [int(site_B)] * N_SITES
    if n_hubs == 0:
        site_Cs = _split(int(total_chargers), N_SITES)
        hub_Bs: List[int] = []
        hub_Cs: List[int] = []
    else:
        site_Cs = [0] * N_SITES
        hub_Bs = _split(int(hub_spares), n_hubs)
        hub_Cs = _split(int(total_chargers), n_hubs)
    fac_spec: Dict[str, Any] = {
        "mode": "colocated" if n_hubs == 0 else "separated",
        "n_sites": N_SITES, "n_hubs": max(1, n_hubs),
        "B": site_Bs[0], "C": site_Cs[0],
        "grid_sites_kw": GRID_KW, "grid_sites_peak_kw": GRID_PEAK_KW,
        "hub": {"B": hub_Bs[0] if hub_Bs else 0, "C": hub_Cs[0] if hub_Cs else 0},
    }
    # f_e / v_reb deliberately absent: they come from the usd_sunk calibration (R2.1)
    svc_spec: Dict[str, Any] = {
        "every": SHUTTLE_EVERY, "first": SHUTTLE_FIRST, "U": SERVICE_U,
        "site_site": n_hubs == 0, "site_site_every": SHUTTLE_EVERY,
    }
    inst = C.make_instance(family, seed=seed, name=f"e3u-{layout}-seed{seed}",
                           facilities_spec=fac_spec, services_spec=svc_spec, **size_overrides)
    sites = [f for f in inst.facilities if f.swap]
    hubs = [f for f in inst.facilities if not f.swap]
    assert len(sites) == N_SITES and len(hubs) == n_hubs, (len(sites), len(hubs))
    for f, b, c in zip(sites, site_Bs, site_Cs):
        f.B, f.C = int(b), int(c)
    for f, b, c in zip(hubs, hub_Bs, hub_Cs):
        f.B, f.C = int(b), int(c)
    if hubs:
        # one shared grid group for all hubs with the co-located 8 / 6 kW profile (equal grid capacity)
        profile = [float(GRID_PEAK_KW if _in_peak(inst, t) else GRID_KW) for t in range(inst.H)]
        group = "hub1" if n_hubs == 1 else "hubs"
        for f in hubs:
            f.group = group
        inst.P_grid = {group: profile}
    inst.reindex()
    inst.validate()
    total_spares = N_SITES * int(site_B) + int(hub_spares)
    assert sum(f.B for f in inst.facilities) == total_spares
    assert sum(f.C for f in inst.facilities) == int(total_chargers)
    inst.meta.update(layout=layout, hub_spares=int(hub_spares), seed=seed, family=family,
                     site_B=site_Bs, hub_B=hub_Bs, hub_C=hub_Cs, site_C=site_Cs,
                     total_spares=int(total_spares), total_chargers=int(total_chargers),
                     size_overrides=dict(size_overrides), end_targets="written")
    rt = Instance.from_json(inst.to_json())
    assert rt == inst, "instance does not round-trip through JSON"
    return inst


def relaxed_copy(inst: Instance) -> Instance:
    """Relaxed-end-target control of ``inst`` (:func:`experiments.common.relax_end_targets`:
    ``rho = 0`` and ``R_end_j = 0``, (17)-(18) off, E2 p.6); ``meta['end_targets'] =
    'relaxed'``.  Everything else is byte-identical."""
    out = C.relax_end_targets(inst)
    out.meta["end_targets"] = "relaxed"
    return out


def _in_peak(inst: Instance, t: int) -> bool:
    """Peak-hour flag of slot ``t`` (generator ``peak_hours`` on the clock of ``meta['window_h']``)."""
    start = float(inst.meta["window_h"][0])
    lo, hi = inst.meta["params"]["facilities_spec"]["peak_hours"]
    hour = start + t * inst.disc.Delta_h
    return lo <= hour < hi


# ---------------------------------------------------------------------------
# records
# ---------------------------------------------------------------------------
def _common_fields(inst: Instance, lib: ArcLibrary, build_time: float) -> Dict[str, Any]:
    hubs = [f for f in inst.facilities if not f.swap]
    co = inst.meta.get("costs") or {}
    return {
        "family": inst.meta.get("family", FAMILY), "cost_variant": inst.meta.get("cost_variant"),
        "layout": inst.meta["layout"], "layout_label": LAYOUT_LABEL[inst.meta["layout"]],
        "targets": inst.meta.get("end_targets", "written"),
        "seed": inst.meta["seed"], "hub_spares": inst.meta["hub_spares"],
        "site_B": json.dumps(inst.meta["site_B"]), "hub_B": json.dumps(inst.meta["hub_B"]),
        "site_C": json.dumps(inst.meta.get("site_C")), "hub_C": json.dumps(inst.meta["hub_C"]),
        "total_spares": inst.meta.get("total_spares"), "total_chargers": inst.meta.get("total_chargers"),
        "rho": inst.rho, "R_end": json.dumps({f.id: int(f.R_end) for f in inst.facilities}, sort_keys=True),
        "bike_q0": json.dumps([b.q0 for b in inst.bikes]),
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
        "n_facilities": len(inst.facilities), "n_hubs": len(hubs),
        "n_services": len(inst.services), "n_arcs": len(lib), "arc_build_time_s": build_time,
        "coef_kappa": co.get("kappa"), "coef_pi": co.get("pi"), "coef_P": co.get("P"), "coef_w": co.get("w"),
        "coef_v": co.get("v"), "coef_f": co.get("f"), "coef_vreb": co.get("vreb"), "coef_F": co.get("F"),
        "coef_F_hub": co.get("F_hub"), "coef_bB": co.get("bB"), "coef_bC": co.get("bC"),
        "grid_limit_kw": json.dumps({g: [float(v) for v in prof] for g, prof in inst.P_grid.items()}, sort_keys=True),
        "facility_roles": json.dumps({f.id: {"swap": bool(f.swap), "charge": bool(f.charge), "B": int(f.B), "C": int(f.C)}
                                      for f in inst.facilities}, sort_keys=True),
    }


def _metric_fields(inst: Instance, m: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten ``evaluate.metrics`` (E2 p.9 'report service, response, lateness, bike
    distance, transfer loads, grid use')."""
    stockout = m["stockout_slots"]
    peak_group = m["peak_kw_group"]
    group_limit = {g: min(inst.P_grid[g]) for g in inst.P_grid}
    return {
        "served_share": m["served_share"], "n_unserved": m["n_unserved"],
        "mean_response_h": m["mean_response_h"], "max_response_h": m["max_response_h"],
        "mean_lateness_h": m["mean_lateness_h"], "max_lateness_h": m["max_lateness_h"], "n_late": m["n_late"],
        "bike_km": m["bike_km"], "n_swaps": m["n_swaps"],
        "swaps_per_facility": json.dumps(m["swaps_per_facility"], default=str, sort_keys=True),
        "mean_wait_before_swap": m["mean_wait_before_swap"],
        "kwh_purchased": m["kwh_purchased"], "kwh_stored": m["kwh_stored"],
        "charge_steps_facility": json.dumps(m["charge_steps_facility"], default=str, sort_keys=True),
        "transfers_used": m["transfers_used"], "batteries_moved": m["batteries_moved"],
        "batteries_moved_by_level": json.dumps(m["batteries_moved_by_level"], sort_keys=True),
        "stockout_slots": json.dumps(stockout, default=str, sort_keys=True),
        "stockout_slots_total": int(sum(stockout.values())),
        "m_t_max": int(max(m["in_transit"])), "m_t_slot_sum": int(sum(m["in_transit"])),
        "m_t": json.dumps([int(v) for v in m["in_transit"]]),
        "peak_kw_group": json.dumps(peak_group, default=str, sort_keys=True),
        "peak_kw_group_max": max(peak_group.values()) if peak_group else 0.0,
        "grid_limit_min_kw": json.dumps(group_limit, default=str, sort_keys=True),
        "end_full_total": m["end_full_total"], "end_target_shortfall": m["end_target_shortfall"],
        "full_stock": json.dumps(m["full_stock"], default=str, sort_keys=True),
        "bike_end_levels": json.dumps(m["bike_end_levels"], default=str, sort_keys=True),
    }


def _grid_load(inst: Instance, sched: Schedule) -> Dict[str, List[float]]:
    """Charging load (20)-(21) per grid group and slot, ``p_ch sum_{j in g, q} c_jqt`` in kW."""
    out: Dict[str, List[float]] = {}
    for g in inst.P_grid:
        members = [f.id for f in inst.facilities if f.group == g]
        out[g] = [round(inst.disc.p_ch_kw * sum(sched.c.get((j, q, t), 0) for j in members
                                                for q in range(inst.L)), 6) for t in range(inst.H)]
    return out


def baseline_record(inst: Instance, lib: ArcLibrary, build_time: float, variant: str, rule: str,
                    base: Dict[str, Any]) -> Dict[str, Any]:
    """Flat CSV row of a :func:`common.run_baseline_case` result (policy under test:
    R2.3 default rules, ``transfer_rule = rule``)."""
    fl = base["flags"]
    return {
        **_common_fields(inst, lib, build_time),
        "method": "baseline", "baseline_variant": variant,
        "transfers": "free" if rule == "REORDER_POINT" else "none",
        "switch": f"transfer_rule={rule}", "status": "-",
        **C.flatten_cost(base["cost"]),
        "runtime_s": base["runtime"], "check_ok": base["ok"],
        "check_ok_modulo_report_only": base["ok_modulo_report_only"],
        "reported_families": json.dumps(base["families"]),
        "identity_24_ok": base["identity_24_ok"],
        "jit_dispatches": fl.get("jit_dispatches", 0),
        "reach_refusals": (fl.get("reach_refusals") or {}).get("count", 0),
        "stock_aware_reroutes": fl.get("stock_aware_reroutes", 0),
        "stock_aware_fallbacks": fl.get("stock_aware_fallbacks", 0),
        "charge_rule_effective": json.dumps(fl.get("charge_rule_effective"), default=str, sort_keys=True),
        **_metric_fields(inst, base["metrics"]),
        "grid_load_kw": json.dumps(_grid_load(inst, base["schedule"]), sort_keys=True),
    }


def ilp_record(inst: Instance, lib: ArcLibrary, build_time: float, no_transfers: bool,
               rec: Dict[str, Any], start_variant: str, time_limit_used: float,
               baseline_totals: Dict[str, Optional[float]]) -> Dict[str, Any]:
    """Flat CSV row of a :func:`common.run_ilp_case` result with solver statistics and
    the headline gaps ``100 (baseline - ILP) / baseline`` against the default baseline
    (NONE), the REORDER_POINT baseline and the better of the two."""
    st = rec["stats"]
    row: Dict[str, Any] = {
        **_common_fields(inst, lib, build_time),
        "method": "ilp", "baseline_variant": "-",
        "transfers": "none" if no_transfers else "free",
        "switch": "no_transfers" if no_transfers else "transfers free",
        "status": rec["status"], "obj": rec["obj"], "bound": rec["bound"], "gap": rec["gap"],
        "runtime_s": rec["runtime"], "model_build_time_s": rec["build_time"], "time_limit_used_s": time_limit_used,
        "n_binaries": rec["n_binaries"], "n_vars": rec["n_vars"], "n_rows": rec["n_rows"],
        "node_count": st.get("node_count"), "sol_count": st.get("sol_count"),
        "mip_start_variant": start_variant,
        "mip_start_accepted": rec["mip_start_accepted"],
        "mip_start_verified_status": (rec["mip_start_info"] or {}).get("verified_status"),
        "check_ok": rec["ok"], "identity_24_ok": rec["identity_24_ok"],
        "reported_families": json.dumps(rec["families"]),
    }
    if rec["cost"] is not None:
        row.update(C.flatten_cost(rec["cost"]))
        row["obj_eq_cost"] = abs(rec["obj"] - rec["cost"]["total"]) <= 1e-6 * max(1.0, abs(rec["obj"]))
        row.update(_metric_fields(inst, rec["metrics"]))
        row["grid_load_kw"] = json.dumps(_grid_load(inst, rec["schedule"]), sort_keys=True)
        tot = rec["cost"]["total"]
        for key, bt in baseline_totals.items():
            row[f"baseline_total_{key}"] = bt
            row[f"gap_vs_baseline_{key}_pct"] = C.gap_definitions(bt, tot)["gap_vs_baseline_pct"]
        best = min((v for v in baseline_totals.values() if v is not None), default=None)
        row["baseline_total_best"] = best
        row["gap_vs_baseline_best_pct"] = C.gap_definitions(best, tot)["gap_vs_baseline_pct"]
        row["ilp_le_baseline_best"] = None if best is None else tot <= best + 1e-6
    return row


def skipped_record(inst: Instance, lib: ArcLibrary, build_time: float, no_transfers: bool,
                   reason: str) -> Dict[str, Any]:
    """Row of an ILP run that the wall-budget guard skipped (``status = SKIPPED_BUDGET``)."""
    return {**_common_fields(inst, lib, build_time), "method": "ilp", "baseline_variant": "-",
            "transfers": "none" if no_transfers else "free",
            "switch": "no_transfers" if no_transfers else "transfers free",
            "status": "SKIPPED_BUDGET", "reported_families": json.dumps({}), "skip_reason": reason}


# ---------------------------------------------------------------------------
# one (layout, seed, targets)
# ---------------------------------------------------------------------------
class WallBudget:
    """Wall-clock guard: ``remaining()`` seconds left; ``solve_limit(tl)`` = the time limit
    to give the next solve (``min(tl, remaining - margin)``) or ``None`` when fewer than
    :data:`MIN_SOLVE_S` seconds remain (the run is then recorded as skipped)."""

    def __init__(self, budget_s: float, margin_s: float = 45.0) -> None:
        self.t0 = time.perf_counter()
        self.budget = float(budget_s)
        self.margin = float(margin_s)

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0

    def remaining(self) -> float:
        return self.budget - self.elapsed()

    def solve_limit(self, time_limit: float) -> Optional[float]:
        avail = self.remaining() - self.margin
        if avail < MIN_SOLVE_S:
            return None
        return float(min(time_limit, avail))


def choose_mip_start(inst: Instance, lib: ArcLibrary, switch: str,
                     bases: Dict[str, Dict[str, Any]]) -> Tuple[Optional[Schedule], str]:
    """First baseline schedule among :data:`START_CANDIDATES` [``switch``] that passes
    ``evaluate.check`` cleanly (the ILP enforces (17)-(18), which the policy only reports;
    DECISIONS R2.3 / 'R2 implementation notes').  Schedules already in ``bases`` (keyed
    by variant name) are reused; the others are run on demand.  Falls back to the
    first candidate's schedule (Gurobi ignores an infeasible start) with the label
    ``'<variant>(unverified)'``."""
    first: Optional[Schedule] = None
    first_label = "none"
    for variant, rule in START_CANDIDATES[switch]:
        key = f"{variant}:{rule}"
        if key not in bases:
            try:
                params = C.baseline_variant_params(variant, inst, transfer_rule=rule)
                bases[key] = C.run_baseline_case(inst, lib, params, label=key)
            except Exception as exc:  # a variant may be inapplicable
                bases[key] = {"error": str(exc), "families": {"error": 1}}
                continue
        rec = bases[key]
        if "schedule" not in rec:
            continue
        if first is None:
            first, first_label = rec["schedule"], key
        if not rec["families"]:
            return rec["schedule"], key
    return first, f"{first_label}(unverified)"


def run_case(inst: Instance, out_dir: str, time_limit: float, budget: WallBudget,
             pruning: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Both baselines and both ILP switches on one instance (one layout, seed and
    end-target setting); returns the flat rows."""
    tag = f"{inst.meta['layout']}_{inst.meta['end_targets']}_seed{inst.meta['seed']}"
    inst.save(os.path.join(C.ensure_dir(os.path.join(out_dir, "instances")), f"{tag}.json"))
    lib, build_time = C.build_library(inst, pruning)
    rows: List[Dict[str, Any]] = []
    bases: Dict[str, Dict[str, Any]] = {}
    totals: Dict[str, Optional[float]] = {}
    for variant, rule in BASELINE_RUNS:
        params = C.baseline_variant_params(variant, inst, transfer_rule=rule)
        base = C.run_baseline_case(inst, lib, params, label=f"{variant}:{rule}")
        bases[f"{variant}:{rule}"] = base
        totals["default" if rule == "NONE" else "reorder"] = base["cost"]["total"]
        rows.append(baseline_record(inst, lib, build_time, variant, rule, base))
        m = base["metrics"]
        print(f"  [{tag}] baseline {rule:<13} total {base['cost']['total']:9.2f} unserved {m['n_unserved']:2d} "
              f"swaps {m['n_swaps']:2d} transfers {m['transfers_used']:2d} moved {m['batteries_moved']:2d} "
              f"families {base['families']} ({base['runtime']:.2f}s)", flush=True)
    for no_transfers in (False, True):
        switch = "none" if no_transfers else "free"
        tl = budget.solve_limit(time_limit)
        if tl is None:
            rows.append(skipped_record(inst, lib, build_time, no_transfers,
                                       f"wall budget exhausted after {budget.elapsed():.0f}s"))
            print(f"  [{tag}] ILP {switch}: SKIPPED (wall budget)", flush=True)
            continue
        start, start_label = choose_mip_start(inst, lib, switch, bases)
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=C.THREADS,
                             label="ilp", no_transfers=no_transfers)
        rows.append(ilp_record(inst, lib, build_time, no_transfers, rec, start_label, tl, totals))
        print(f"  [{tag}] ILP {switch:<4} {rec['status']:>10} obj {C.fmt(rec['obj'], 2):>9} gap {C.fmt(rec['gap'], 4)} "
              f"solve {rec['runtime']:6.1f}s (limit {tl:.0f}) build {rec['build_time']:.1f}s binaries {rec['n_binaries']:,} "
              f"start {start_label} accepted {rec['mip_start_accepted']}"
              + (f" | unserved {rec['metrics']['n_unserved']} swaps {rec['metrics']['n_swaps']} transfers "
                 f"{rec['metrics']['transfers_used']} moved {rec['metrics']['batteries_moved']} kWh "
                 f"{rec['metrics']['kwh_purchased']:.2f} end_full {rec['metrics']['end_full_total']}"
                 if rec["metrics"] else ""), flush=True)
    return rows


# ---------------------------------------------------------------------------
# figures (all from results.csv)
# ---------------------------------------------------------------------------
def _sel(df, layout: str, method: str, transfers: str, targets: str, seed: Optional[int] = None,
         variant: Optional[str] = None):
    sub = df[(df.layout == layout) & (df.method == method) & (df.transfers == transfers) & (df.targets == targets)]
    if seed is not None:
        sub = sub[sub.seed == seed]
    if variant is not None:
        sub = sub[sub.baseline_variant == variant]
    return sub[sub["total"].notna()] if "total" in sub else sub


def plot_cost_by_layout(df, path: str) -> str:
    """Mean total cost (26) per layout: ILP transfers free / no transfers under the written
    and the relaxed targets, baselines default (NONE) and REORDER_POINT; dots = seeds."""
    series = [("ilp", "free", "written", None, "ILP transfers free, written targets", "#1f77b4", 1.0),
              ("ilp", "none", "written", None, "ILP h = z = 0, written targets", "#d62728", 1.0),
              ("ilp", "free", "relaxed", None, "ILP transfers free, relaxed", "#1f77b4", 0.45),
              ("ilp", "none", "relaxed", None, "ILP h = z = 0, relaxed", "#d62728", 0.45),
              ("baseline", "none", "written", "baseline", "baseline default (NONE)", "#7f7f7f", 1.0),
              ("baseline", "free", "written", "baseline_reorder", "baseline REORDER_POINT", "#7f7f7f", 0.5)]
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    width = 0.13
    rng = np.random.default_rng(0)
    for si, (method, transfers, targets, variant, label, color, alpha) in enumerate(series):
        for li, layout in enumerate(LAYOUTS):
            sub = _sel(df, layout, method, transfers, targets, variant=variant)
            vals = sub["total"].to_numpy(dtype=float)
            if len(vals) == 0:
                continue
            x = li + (si - 2.5) * width
            ax.bar(x, vals.mean(), width, color=color, alpha=alpha, label=label if li == 0 else None)
            jitter = (rng.uniform(-0.3, 0.3, len(vals)) * width) if len(vals) > 1 else np.zeros(len(vals))
            ax.scatter(x + jitter, vals, s=12, color="black", zorder=3)
    ax.set_xticks(range(len(LAYOUTS)))
    ax.set_xticklabels([LAYOUT_LABEL[l] for l in LAYOUTS])
    ax.set_ylabel("total cost (26), USD per 4 h window; bars = seed mean, dots = seeds")
    ax.set_title("E3u: total cost by layout, transfer switch and end-target setting (usd4h, usd_sunk)")
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_cost_components(df, path: str) -> str:
    """Stacked mean cost components (27)-(32) per layout x switch x targets (ILP)."""
    comps = [("C_setup", "setup (27)"), ("C_travel", "travel (29)"), ("C_elec", "electricity (28)"),
             ("unserved", "unserved (30)"), ("response", "response (31)"), ("lateness", "lateness (31)"),
             ("C_reb", "transfers (32)")]
    cmap = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(11, 4.4))
    xs, labels = [], []
    pos = 0.0
    for layout in LAYOUTS:
        for targets in TARGETS:
            for transfers in ("free", "none"):
                sub = _sel(df, layout, "ilp", transfers, targets)
                if sub.empty:
                    continue
                bottom = 0.0
                for ci, (col, lab) in enumerate(comps):
                    v = float(sub[col].mean()) if col in sub else 0.0
                    ax.bar(pos, v, 0.8, bottom=bottom, color=cmap(ci), label=lab if pos == 0.0 else None)
                    bottom += v
                xs.append(pos)
                labels.append(f"{layout.replace('separated_', 'sep ')}\n{'free' if transfers == 'free' else 'h=z=0'}\n{targets}")
                pos += 1.0
            pos += 0.3
        pos += 0.6
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("mean cost over seeds (USD)")
    ax.set_title("E3u: ILP cost components by layout, transfer switch and end-target setting")
    ax.legend(fontsize=7, frameon=False, ncol=4)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def transfer_values(df) -> Dict[str, Dict[str, List[float]]]:
    """Per layout and targets the per-seed value of transfers ``total(h = z = 0) -
    total(transfers free)`` of the ILP (seeds with both solutions)."""
    out: Dict[str, Dict[str, List[float]]] = {}
    for layout in LAYOUTS:
        out[layout] = {}
        for targets in TARGETS:
            vals = []
            for s in sorted(df.seed.unique()):
                a, b = _sel(df, layout, "ilp", "none", targets, s), _sel(df, layout, "ilp", "free", targets, s)
                if not a.empty and not b.empty:
                    vals.append(float(a.iloc[0]["total"]) - float(b.iloc[0]["total"]))
            out[layout][targets] = vals
    return out


def separation_costs(df, transfers: str = "free") -> Dict[str, Dict[str, List[float]]]:
    """Per layout and targets the per-seed cost of separation ``total(layout) -
    total(colocated)`` of the ILP with the given switch."""
    out: Dict[str, Dict[str, List[float]]] = {}
    for layout in LAYOUTS:
        out[layout] = {}
        for targets in TARGETS:
            vals = []
            for s in sorted(df.seed.unique()):
                a, b = _sel(df, layout, "ilp", transfers, targets, s), _sel(df, "colocated", "ilp", transfers, targets, s)
                if not a.empty and not b.empty:
                    vals.append(float(a.iloc[0]["total"]) - float(b.iloc[0]["total"]))
            out[layout][targets] = vals
    return out


def plot_transfer_value(df, path: str) -> str:
    """Left: value of transfers per layout, written vs relaxed targets (bar = seed mean,
    markers = seeds); right: cost of separation vs (a) with transfers free."""
    tv, sc = transfer_values(df), separation_costs(df)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    width = 0.36
    colors = {"written": "#1f77b4", "relaxed": "#ff7f0e"}
    for ax, data, ttl, yl in ((axes[0], tv, "value of transfers: cost(h = z = 0) - cost(transfers free), ILP",
                               "USD per 4 h window"),
                              (axes[1], sc, "cost of separation: cost(layout) - cost(co-located), ILP transfers free",
                               "USD per 4 h window")):
        for ti, targets in enumerate(TARGETS):
            for li, layout in enumerate(LAYOUTS):
                vals = data[layout][targets]
                if not vals:
                    continue
                x = li + (ti - 0.5) * width
                ax.bar(x, float(np.mean(vals)), width, color=colors[targets], alpha=0.8,
                       label=TARGET_LABEL[targets] if li == 0 else None)
                ax.scatter([x] * len(vals), vals, s=14, color="black", zorder=3)
        ax.set_xticks(range(len(LAYOUTS)))
        ax.set_xticklabels([LAYOUT_LABEL[l].replace(" 3 sites", "\n3 sites").replace(" + ", "\n+ ") for l in LAYOUTS],
                           fontsize=8)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_ylabel(yl)
        ax.set_title(ttl, fontsize=8.5)
        ax.legend(fontsize=7, frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_full_stock(df, seed: int, targets: str, path: str) -> str:
    """Full-battery stock ``n_jLt`` (13) per facility over ``t = 0..H`` for the ILP with
    transfers free (solid: swap sites, dashed: hubs), one panel per layout, one seed and
    one end-target setting (``full_stock`` / ``facility_roles`` columns)."""
    fig, axes = plt.subplots(len(LAYOUTS), 1, figsize=(8, 2.6 * len(LAYOUTS)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, layout in zip(axes, LAYOUTS):
        sub = _sel(df, layout, "ilp", "free", targets, seed)
        if sub.empty:
            ax.set_title(f"{LAYOUT_LABEL[layout]} -- no ILP schedule", fontsize=9)
            continue
        r = sub.iloc[0]
        roles = json.loads(r["facility_roles"])
        for j, traj in json.loads(r["full_stock"]).items():
            fac = roles[j]
            ax.step(range(len(traj)), traj, where="post", linestyle="-" if fac["swap"] else "--",
                    label=f"{j} ({'swap' if fac['swap'] else 'hub'}, B={fac['B']}, C={fac['C']})")
        ax.set_ylabel("full spares n_jLt")
        ax.set_title(f"{LAYOUT_LABEL[layout]} -- stock-out slots {r['stockout_slots']}, transfers used "
                     f"{int(r['transfers_used'])}, batteries moved {int(r['batteries_moved'])}, swaps {int(r['n_swaps'])}",
                     fontsize=8.5)
        ax.legend(fontsize=7, frameon=False, ncol=2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("boundary t (slots of 5 min; 17:00 + t x 5 min)")
    fig.suptitle(f"E3u: full-battery stock per facility, ILP with transfers, seed {seed}, {TARGET_LABEL[targets]}",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_in_transit(df, seeds: Sequence[int], path: str) -> str:
    """In-transit batteries ``m_t`` (24) over ``t`` for the ILP with transfers free, one
    colour per layout, solid = written targets, dashed = relaxed (seed means, thin = seeds)."""
    fig, ax = plt.subplots(figsize=(8, 3.9))
    cmap = plt.get_cmap("tab10")
    for li, layout in enumerate(LAYOUTS):
        for targets, ls in (("written", "-"), ("relaxed", "--")):
            series = []
            for s in seeds:
                sub = _sel(df, layout, "ilp", "free", targets, s)
                if not sub.empty:
                    series.append(np.array(json.loads(sub.iloc[0]["m_t"]), dtype=float))
            if not series:
                continue
            H = len(series[0]) - 1
            for arr in series:
                ax.step(range(H + 1), arr, where="post", color=cmap(li), alpha=0.2, linewidth=0.7, linestyle=ls)
            ax.step(range(H + 1), np.mean(series, axis=0), where="post", color=cmap(li), linewidth=2, linestyle=ls,
                    label=f"{LAYOUT_LABEL[layout]}, {targets} (mean of {len(series)})")
    ax.set_xlabel("boundary t (slots of 5 min)")
    ax.set_ylabel("batteries in transit m_t")
    ax.set_title("E3u: in-transit batteries over time, ILP with transfers free")
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_grid_load(df, seed: int, path: str, targets: str = "written") -> str:
    """Charging load per grid group (20)-(21) vs its limit, ILP with transfers free."""
    fig, axes = plt.subplots(len(LAYOUTS), 1, figsize=(8, 2.2 * len(LAYOUTS)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, layout in zip(axes, LAYOUTS):
        sub = _sel(df, layout, "ilp", "free", targets, seed)
        if sub.empty:
            ax.set_title(f"{LAYOUT_LABEL[layout]} -- no ILP schedule", fontsize=9)
            continue
        r = sub.iloc[0]
        loads, limits = json.loads(r["grid_load_kw"]), json.loads(r["grid_limit_kw"])
        for g, load in loads.items():
            H = len(load)
            ax.step(range(H), load, where="post", label=f"group {g} charging load")
            ax.step(range(H), limits[g], where="post", linestyle=":", color="black", label=f"P_grid[{g}] limit")
        ax.set_ylabel("kW")
        ax.set_title(LAYOUT_LABEL[layout], fontsize=9)
        ax.legend(fontsize=7, frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("slot t (5 min)")
    fig.suptitle(f"E3u: grid-group charging load vs limit (21), ILP with transfers, seed {seed}, {targets} targets",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def summary_table(df):
    """Seed means per (layout, targets, method, switch) of the headline columns."""
    cols = ["total", "C_setup", "C_travel", "C_elec", "unserved", "response", "lateness", "C_reb",
            "served_share", "n_unserved", "mean_response_h", "mean_lateness_h", "n_late", "bike_km", "n_swaps",
            "kwh_purchased", "transfers_used", "batteries_moved", "stockout_slots_total", "m_t_max",
            "peak_kw_group_max", "end_full_total", "runtime_s", "gap", "gap_vs_baseline_default_pct",
            "gap_vs_baseline_reorder_pct", "gap_vs_baseline_best_pct"]
    present = [c for c in cols if c in df.columns]
    keys = ["layout", "targets", "method", "switch"]
    g = df.groupby(keys, sort=False)[present].mean(numeric_only=True).reset_index()
    g["n_seeds"] = df.groupby(keys, sort=False).size().to_numpy()
    order = {l: i for i, l in enumerate(LAYOUTS)}
    g["_o"] = (g["layout"].map(order) * 10 + g["targets"].map({"written": 0, "relaxed": 5})
               + g["method"].map({"ilp": 0.0, "baseline": 2.0}))
    return g.sort_values(["_o", "switch"]).drop(columns="_o")


def headline_lines(df) -> List[str]:
    """Bullet list: value of transfers (written vs relaxed), cost of separation, headline gaps."""
    tv, sc = transfer_values(df), separation_costs(df)
    out: List[str] = []
    for layout in LAYOUTS:
        parts = []
        for targets in TARGETS:
            vals = tv[layout][targets]
            if vals:
                parts.append(f"{targets}: {np.mean(vals):.2f} (seeds {', '.join(f'{v:.2f}' for v in vals)})")
        out.append(f"value of transfers, {LAYOUT_LABEL[layout]}: " + "; ".join(parts or ["-"]))
    for layout in LAYOUTS[1:]:
        parts = []
        for targets in TARGETS:
            vals = sc[layout][targets]
            if vals:
                parts.append(f"{targets}: {np.mean(vals):.2f} (seeds {', '.join(f'{v:.2f}' for v in vals)})")
        out.append(f"cost of separation (transfers free), {LAYOUT_LABEL[layout]} vs (a): " + "; ".join(parts or ["-"]))
    for layout in LAYOUTS:
        for targets in TARGETS:
            sub = _sel(df, layout, "ilp", "free", targets)
            if sub.empty or "gap_vs_baseline_best_pct" not in sub:
                continue
            g = sub["gap_vs_baseline_best_pct"].dropna()
            gd = sub["gap_vs_baseline_default_pct"].dropna()
            gr = sub["gap_vs_baseline_reorder_pct"].dropna()
            if len(g):
                out.append(f"headline gap (baseline - ILP)/baseline, {LAYOUT_LABEL[layout]}, {targets}, ILP transfers free: "
                           f"vs best baseline {g.mean():.1f} % (seeds {', '.join(f'{v:.1f}' for v in g)}); "
                           f"vs default (NONE) {gd.mean():.1f} %; vs REORDER_POINT {gr.mean():.1f} %")
    return out


def write_results_md(df, out_dir: str, seeds: Sequence[int], hub_spares: int, time_limit: float,
                     figures: List[str], anomalies: List[str], timing: float, pruning: Dict[str, Any]) -> str:
    summ = summary_table(df)
    ilp = df[df.method == "ilp"]
    base = df[df.method == "baseline"]
    co = {k: ilp.iloc[0][f"coef_{k}"] if not ilp.empty and f"coef_{k}" in ilp else None
          for k in ("kappa", "pi", "P", "w", "v", "f", "vreb", "F", "F_hub", "bB", "bC")}
    pr = {k: (sorted(map(str, v)) if isinstance(v, (set, list)) else v) for k, v in pruning.items()
          if k != "reposition_targets"}
    lines: List[str] = ["# E3u -- transfers and separation under USD costs, 4 h window (round 2)", ""]
    zh = os.path.join(out_dir, "SUMMARY_zh.md")   # hand-written Chinese summary, kept across re-runs
    if os.path.exists(zh):
        with open(zh, encoding="utf-8") as fh:
            lines += [fh.read().rstrip(), ""]
    lines += [
        f"Family `{FAMILY}` (R2.2: {C.FAMILIES[FAMILY]}), seeds {list(seeds)}; costs `usd_sunk` (R2.1: kappa {co['kappa']} $/km, "
        f"pi {co['pi']} $/kWh, P {co['P']} $, w {co['w']} $/h, v {co['v']} $/h, f_e {co['f']} $, v_reb {co['vreb']} $/battery, "
        f"F {co['F']} / F_hub {co['F_hub']}, bB {co['bB']}, bC {co['bC']} per 4 h). Equal totals in every layout: "
        f"sum B = {N_SITES * SITE_B + hub_spares} ({SITE_B} per swap site, hubs {hub_spares}), sum C = {TOTAL_CHARGERS}, "
        f"grid group {GRID_KW:.0f} kW ({GRID_PEAK_KW:.0f} kW 18-20 h). Shuttles every {SHUTTLE_EVERY} slots from t = {SHUTTLE_FIRST}, "
        f"U_e = {SERVICE_U}. End targets: `written` = rho 0.5, R_end_j = 1 at swap sites (E2 (17)-(18)); `relaxed` = rho 0, "
        f"R_end = 0 (control, every layout and both switches). Pruning {pr} (reachable pruning is lossless); Gurobi Threads "
        f"{C.THREADS}, TimeLimit {time_limit:.0f} s, OutputFlag 0. Total wall time {timing / 60:.1f} min (single process).", "",
        "## Headline", ""] + [f"- {h}" for h in headline_lines(df)] + ["",
        "## Seed means per layout, end-target setting, method and transfer switch", "",
        C.markdown_table(summ, list(summ.columns), 3), "",
        "`stockout_slots_total` = slots with `n_jLt = 0` summed over facilities; `m_t_max` = max in-transit batteries (24); "
        "`peak_kw_group_max` = max over grid groups of the peak charging load (21); `end_full_total` = sum_j n_jLH "
        f"((18) requires >= rho sum B = {0.5 * (N_SITES * SITE_B + hub_spares):g} under the written targets); "
        "`gap_vs_baseline_*_pct` = 100 (baseline - ILP) / baseline against the default (NONE) baseline, the REORDER_POINT "
        "baseline and the better of the two, all under the same end-target setting.", "",
        "## Per-run table (ILP)", ""]
    cols = ["layout", "targets", "seed", "switch", "status", "total", "C_setup", "C_travel", "C_elec", "unserved", "response",
            "lateness", "C_reb", "served_share", "n_late", "mean_response_h", "bike_km", "n_swaps", "kwh_purchased",
            "transfers_used", "batteries_moved", "stockout_slots", "m_t_max", "peak_kw_group", "end_full_total",
            "n_binaries", "n_rows", "runtime_s", "time_limit_used_s", "gap", "mip_start_variant", "mip_start_accepted",
            "check_ok", "identity_24_ok", "baseline_total_default", "baseline_total_reorder", "gap_vs_baseline_default_pct",
            "gap_vs_baseline_reorder_pct", "gap_vs_baseline_best_pct", "skip_reason"]
    lines += [C.markdown_table(ilp, [c for c in cols if c in ilp.columns], 3), "", "## Per-run table (baseline)", ""]
    bcols = ["layout", "targets", "seed", "switch", "total", "C_setup", "C_travel", "C_elec", "unserved", "response", "lateness",
             "C_reb", "served_share", "n_late", "mean_response_h", "bike_km", "n_swaps", "kwh_purchased", "transfers_used",
             "batteries_moved", "stockout_slots", "m_t_max", "peak_kw_group", "end_full_total", "reported_families",
             "check_ok_modulo_report_only", "identity_24_ok", "jit_dispatches", "reach_refusals", "stock_aware_reroutes",
             "stock_aware_fallbacks", "runtime_s"]
    lines += [C.markdown_table(base, [c for c in bcols if c in base.columns], 3), ""]
    lines += ["## Figures", ""] + [f"- `{os.path.basename(f)}`" for f in figures] + [""]
    lines += ["## Anomalies / checks", ""] + ([f"- {a}" for a in anomalies] or ["- none"]) + [""]
    interp = os.path.join(out_dir, "INTERPRETATION.md")   # hand-written discussion, kept across re-runs
    if os.path.exists(interp):
        with open(interp, encoding="utf-8") as fh:
            lines += [fh.read().rstrip(), ""]
    path = os.path.join(out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def collect_anomalies(df) -> List[str]:
    """Automatic sanity flags (solver status, ILP check / identity (24), ILP vs baseline,
    relaxed <= written, transfers-free <= no-transfers, baseline report-only families)."""
    out: List[str] = []
    for _, r in df.iterrows():
        tag = f"{r['layout']} {r['targets']} seed {r['seed']} {r['method']} {r['switch']}"
        if r["method"] == "ilp":
            if r["status"] != "OPTIMAL":
                out.append(f"{tag}: status {r['status']} gap {C.fmt(r.get('gap'), 4)}"
                           + (f" ({r.get('skip_reason')})" if isinstance(r.get("skip_reason"), str) else ""))
            if r["status"] == "SKIPPED_BUDGET":
                continue
            if r.get("check_ok") is not True:
                out.append(f"{tag}: ILP schedule fails evaluate.check")
            if r.get("identity_24_ok") is not True:
                out.append(f"{tag}: identity (24) violated")
            if r.get("mip_start_accepted") is not True:
                out.append(f"{tag}: MIP start {r.get('mip_start_variant')} not accepted ({r.get('mip_start_verified_status')})")
            if r.get("ilp_le_baseline_best") is False:
                out.append(f"{tag}: ILP total {r['total']:.2f} > best baseline {r['baseline_total_best']:.2f} "
                           f"(status {r['status']}, gap {C.fmt(r.get('gap'), 4)})")
        else:
            if r.get("check_ok_modulo_report_only") is not True:
                out.append(f"{tag}: baseline violates a non-report-only family {r['reported_families']}")
            if r.get("identity_24_ok") is not True:
                out.append(f"{tag}: baseline breaks identity (24)")
    # monotonicity: relaxed optimum <= written optimum; transfers free <= no transfers (same targets)
    for layout in LAYOUTS:
        for s in sorted(df.seed.unique()):
            for transfers in ("free", "none"):
                a, b = _sel(df, layout, "ilp", transfers, "written", s), _sel(df, layout, "ilp", transfers, "relaxed", s)
                if not a.empty and not b.empty and a.iloc[0]["status"] == "OPTIMAL" and b.iloc[0]["status"] == "OPTIMAL":
                    if float(b.iloc[0]["total"]) > float(a.iloc[0]["total"]) + 1e-6:
                        out.append(f"{layout} seed {s} {transfers}: relaxed optimum {b.iloc[0]['total']:.2f} > written {a.iloc[0]['total']:.2f}")
            for targets in TARGETS:
                a, b = _sel(df, layout, "ilp", "none", targets, s), _sel(df, layout, "ilp", "free", targets, s)
                if not a.empty and not b.empty and a.iloc[0]["status"] == "OPTIMAL" and b.iloc[0]["status"] == "OPTIMAL":
                    if float(b.iloc[0]["total"]) > float(a.iloc[0]["total"]) + 1e-6:
                        out.append(f"{layout} seed {s} {targets}: transfers-free optimum {b.iloc[0]['total']:.2f} > "
                                   f"no-transfers optimum {a.iloc[0]['total']:.2f}")
    return out


def make_figures(df, out_dir: str, seeds: Sequence[int]) -> List[str]:
    """All E3u figures from the ``results.csv`` frame."""
    figures = [plot_cost_by_layout(df, os.path.join(out_dir, "fig_cost_by_layout.png")),
               plot_cost_components(df, os.path.join(out_dir, "fig_cost_components.png")),
               plot_transfer_value(df, os.path.join(out_dir, "fig_transfer_value.png")),
               plot_in_transit(df, seeds, os.path.join(out_dir, "fig_in_transit.png"))]
    s0 = int(seeds[0])
    for targets in TARGETS:
        figures.append(plot_full_stock(df, s0, targets, os.path.join(out_dir, f"fig_full_stock_{targets}_seed{s0}.png")))
    figures.append(plot_grid_load(df, s0, os.path.join(out_dir, f"fig_grid_load_seed{s0}.png")))
    return figures


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(seeds: Sequence[int], hub_spares: int = HUB_SPARES, time_limit: float = C.DEFAULT_TIME_LIMIT,
         out_dir: str = OUT_DIR, layouts: Sequence[str] = LAYOUTS, targets: Sequence[str] = TARGETS,
         probe: bool = False, figures_only: bool = False, wall_budget: float = WALL_BUDGET_S,
         reachable: bool = True) -> Any:
    """Run every (seed, layout, targets), write ``results.csv`` incrementally, figures and
    ``RESULTS.md``.  Order: seed-major so that early seeds are complete if the wall budget
    runs out.  With ``figures_only`` the existing ``results.csv`` is re-read and only
    figures + ``RESULTS.md`` are regenerated."""
    import pandas as pd
    C.ensure_dir(out_dir)
    csv_path = os.path.join(out_dir, "results.csv")
    wall_path = os.path.join(out_dir, "wall_time.json")
    pruning: Dict[str, Any] = {}
    if figures_only:
        df = pd.read_csv(csv_path)
        seeds = sorted(df.seed.unique())
        meta = json.load(open(wall_path)) if os.path.exists(wall_path) else {}
        wall = meta.get("wall_s", float("nan"))
        time_limit = meta.get("time_limit", time_limit)
        hub_spares = meta.get("hub_spares", hub_spares)
        pruning = meta.get("pruning", {})
    else:
        budget = WallBudget(wall_budget)
        rows: List[Dict[str, Any]] = []
        for seed in seeds:
            for layout in layouts:
                inst = make_layout_instance(seed, layout, hub_spares)
                pruning = C.pruning_for(inst, reachable=reachable)
                for tg in targets:
                    case = inst if tg == "written" else relaxed_copy(inst)
                    rows.extend(run_case(case, out_dir, time_limit, budget, pruning))
                    C.write_csv(rows, csv_path)  # incremental
                    sys.stdout.flush()
        df = C.write_csv(rows, csv_path)
        wall = budget.elapsed()
        with open(wall_path, "w", encoding="utf-8") as fh:
            json.dump({"wall_s": wall, "seeds": list(seeds), "time_limit": time_limit, "hub_spares": hub_spares,
                       "wall_budget": wall_budget, "threads": C.THREADS,
                       "pruning": {k: (sorted(map(str, v)) if isinstance(v, set) else v) for k, v in pruning.items()
                                   if k != "reposition_targets"}}, fh)
        if probe:
            print(C.markdown_table(summary_table(df), None, 3))
            return df
    figures = make_figures(df, out_dir, seeds)
    anomalies = collect_anomalies(df)
    md = write_results_md(df, out_dir, seeds, hub_spares, time_limit, figures, anomalies, wall, pruning)
    print(f"wrote {md} and {len(figures)} figures; wall {wall:.0f}s")
    print(C.markdown_table(summary_table(df), None, 3))
    for h in headline_lines(df):
        print("HEADLINE:", h)
    for a in anomalies:
        print("ANOMALY:", a)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--layouts", nargs="+", default=list(LAYOUTS), choices=list(LAYOUTS))
    ap.add_argument("--targets", nargs="+", default=list(TARGETS), choices=list(TARGETS))
    ap.add_argument("--hub-spares", type=int, default=HUB_SPARES,
                    help="initial spares at the hubs (added to the 3 x 3 site spares; default 0 keeps sum B = 9)")
    ap.add_argument("--time-limit", type=float, default=C.DEFAULT_TIME_LIMIT)
    ap.add_argument("--wall-budget", type=float, default=WALL_BUDGET_S, help="seconds; remaining solves are shortened / skipped")
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--probe", action="store_true", help="run only, no figures / RESULTS.md")
    ap.add_argument("--no-reachable", action="store_true", help="use the plan pruning without reachable_pruning")
    ap.add_argument("--figures-only", action="store_true", help="re-read results.csv, redraw figures + RESULTS.md")
    args = ap.parse_args()
    if args.time_limit > 300:
        raise SystemExit("round-2 rule: TimeLimit <= 300 s")
    main(args.seeds, args.hub_spares, args.time_limit, args.out_dir, args.layouts, args.targets, args.probe,
         figures_only=args.figures_only, wall_budget=args.wall_budget, reachable=not args.no_reachable)
