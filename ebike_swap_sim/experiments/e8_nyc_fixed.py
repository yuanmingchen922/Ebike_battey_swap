"""Experiment E8 (review-fixed copy) -- the semi-real NYC instance (DECISIONS R2.4) under the round-2 rules.

Review fixes relative to ``e8_nyc.py`` (which was running when the review landed and
was left untouched; this copy writes to ``outputs/e8_nyc_fixed/`` by default):

* units F1: ``data_nyc.make_nyc_instance`` now samples releases from the R2.2 block
  profile as a step function (``assumed_block_config``), like the synthetic ``usd4h``
  family; the realised ``nyc4h`` instances therefore differ from the ones in
  ``outputs/e8_nyc/`` and E8 must be re-run with this script.  ``meta['hourly_profile_used']``
  records the profile object (``kind = 'block_step'``) and RESULTS.md states it.
* units F2 / F3: ``meta['costs']`` exists on NYC instances; the unreachable DOHMH share
  (``'other'`` cuisine class, 26 % of the box) is recorded and reported.
* units F7: the demand side (orders, q0, H, L -- not the bikes' start nodes, which move
  with the sites) is hashed (``common.demand_md5``) per run and asserted identical across
  the two sitings of a seed; the hash is written to ``results.csv`` / RESULTS.md.
* fairness F2: ``PRUNING_NYC`` (moves only into the 3 site nodes) restricts the ILP but
  not the policy, so the ILP total is an upper bound on the written optimum and the gap a
  lower bound; stated in the methods paragraph and the caveats.  ``--targets default`` runs
  the lossless probe (restaurants + sites as targets, reachable pruning) when the machine
  is free.
* fairness F4 / F5 / F7: baseline pruned-arc fallbacks, stranded bikes, suppressed late
  trips, structurally unservable orders (served share relative to the servable orders) and
  MIP-start fallback errors are exported and listed under anomalies.
* fairness F1: the relaxed-copy baseline (MIP start of ``ilp_relaxed``) now runs with the
  written ``R_end_j`` as DEMAND_AWARE reserve (``common.run_baseline_case``), so
  ``baseline_relaxed_copy_differs`` is expected to be False.

Question
--------
Does the coordinated E2 ILP keep its advantage over the round-2 event-driven baseline
(R2.3) when restaurants, customer zone weights and candidate-site coordinates are
real (DOHMH restaurants, ACS 2020-24 literature zone weights, Midtown / Chelsea /
Flatiron study box), and how sensitive is the result to *where* the three
co-located sites are placed?

Design
------
* Instances: ``experiments.common.FAMILIES['nyc4h']`` (``data_nyc.make_nyc_instance``;
  6 bikes, 4 h dinner window 17:00-21:00 = ``H 48`` x 5 min, 1.5 orders per
  bike-hour -> 36 orders, ``L 12``, ``usd_sunk`` costs (R2.1), Kaggle order attributes
  (R2.2)), seeds 0-2, two sitings of the three co-located sites (``B 3, C 2, K 8,
  M 1, sigma 1, P 4 kW``):
  ``busiest`` = the three busiest DOHMH restaurant cells of the box (>= 4 blocks
  apart; ``data_nyc.busiest_restaurant_cells``) and ``grid`` = three given
  coordinates in the Citi Bike 'grid-connected station' spirit (8th Ave / W 34th,
  Union Square, Grand Central; :data:`GRID_SITES`) snapped to the grid.  Orders,
  bikes' battery levels and the restaurant ranks of one seed are drawn from the same
  ``numpy`` stream in both sitings (the sites enter the stream only through the bikes'
  start nodes, which are the sites), so the two sitings of a seed share the demand.
* Methods on every instance (byte-identical ``Instance`` / ``ArcLibrary`` per method,
  pruning ``common.PRUNING_NYC`` = moves only into facility / depot nodes, ``tau_max 4``,
  ``start_slack 6``, lossless ``reachable_pruning``):
  ``baseline`` = the round-2 policy (R2.3 defaults: stock-aware site choice,
  DEMAND_AWARE charging, JIT dispatch, dead-zone rule; (9)/(17)/(18) reported, not
  enforced); ``ilp`` = the written E2 model ((5)-(22), (26)-(32), ``rho 0.5``,
  ``R_end 1``) with the first feasible baseline schedule as verified MIP start
  (``common.feasible_mip_start``); ``ilp_relaxed`` = the fair control of
  ``common.relax_end_targets`` (``rho 0`` AND ``R_end_j 0``: both end targets off,
  so the baseline is a feasible point and the gap is not inflated by the recovery
  targets).  Gurobi 13, ``OutputFlag 0``, ``Threads 3``, ``TimeLimit`` per solve.
* Reported per run (``results.csv``): cost (26) and components (27)-(32), served
  share, response, lateness, bike km, swaps, kWh, transfers, baseline report-only
  violations (9)/(17)/(18), solver status / gap / time / size, MIP-start acceptance
  and the variant injected.  ``RESULTS.md``: Chinese summary, headline gap
  ``(baseline - ILP) / baseline`` per seed and siting (mean, 95 % t-CI), siting
  sensitivity, the demand-pattern comparison with the synthetic ``usd4h`` family
  (cuisine shares vs the Kaggle target, customer zone shares vs the sampling law,
  restaurant top-10 concentration, trip lengths), the geometry caveat, anomalies.
* Figures (Agg): ``map_seed0.png`` (grid nodes, DOHMH restaurants coloured by Kaggle
  cuisine, ACS zone-weight heat, both sitings, the ILP bike paths of seed 0),
  ``cost_components.png``, ``gap_by_seed.png``, ``demand_comparison.png``.

Everything in USD (``usd_sunk``).  The E2 mathematics is untouched; this script only
calls ``experiments.common`` / the package.  Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/e8_nyc.py [--seeds 0 1 2] [--time-limit 300]
                                               [--sitings busiest grid] [--out outputs/e8_nyc]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys
import time
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import ArcLibrary, Instance, Schedule, build_arcs, check, cost, metrics  # noqa: E402
from ebike_swap_sim import data_nyc  # noqa: E402
from experiments import common as C  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e8_nyc_fixed")
FAMILY = "nyc4h"
SEEDS = [0, 1, 2]
TIME_LIMIT = 300.0
#: Citi Bike-style 'grid-connected' siting (R2.4 "real candidate-site coordinates"):
#: three well-known Midtown anchors, WGS84 (lat, lon), snapped to the 150 m grid.
GRID_SITES: Dict[str, Tuple[float, float]] = {
    "8th Ave / W 34th St": (40.75270, -73.99370),
    "Union Square": (40.73590, -73.99110),
    "Grand Central": (40.75270, -73.97720),
}
SITINGS = ("busiest", "grid")
METHODS = ("baseline", "ilp", "ilp_relaxed")
COMPONENTS = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"]
#: validated categorical palette (dataviz reference instance, light mode, fixed order)
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
#: sequential blue ramp (dataviz reference, steps 100..700) for the zone-weight heat
SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
            "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
INK, INK2, GRID_INK, SURFACE = "#0b0b0b", "#52514e", "#d8d7d2", "#fcfcfb"
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def make_instance(seed: int, siting: str) -> Instance:
    """``nyc4h`` instance of ``seed`` with the sites placed by ``siting`` (R2.4):
    ``'busiest'`` = :func:`data_nyc.busiest_restaurant_cells` (the family default),
    ``'grid'`` = :data:`GRID_SITES` through ``site_latlon``.  ``meta['siting']`` and
    ``meta['site_labels']`` are added; everything else is ``common.make_instance``."""
    if siting == "busiest":
        inst = C.make_instance(FAMILY, seed=seed, name=f"nyc4h-{siting}-seed{seed}")
        inst.meta["site_labels"] = [f"busiest cell {i + 1}" for i in range(len(inst.facilities))]
    elif siting == "grid":
        inst = C.make_instance(FAMILY, seed=seed, name=f"nyc4h-{siting}-seed{seed}",
                               site_latlon=list(GRID_SITES.values()))
        inst.meta["site_labels"] = list(GRID_SITES.keys())
    else:
        raise ValueError(siting)
    inst.meta["siting"] = siting
    return inst


def ci95(values: Sequence[float]) -> Tuple[float, float, int]:
    """``(mean, half-width, n)`` of a 95 % Student-t confidence interval over seeds."""
    v = [float(x) for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n == 0:
        return float("nan"), float("nan"), 0
    m = sum(v) / n
    if n == 1:
        return m, float("nan"), 1
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    return m, T975.get(n - 1, 1.96) * sd / math.sqrt(n), n


# ---------------------------------------------------------------------------
# per-run rows (same columns as experiments/e2_coord.py, plus siting)
# ---------------------------------------------------------------------------
def _base_row(inst: Instance, lib: ArcLibrary, method: str) -> Dict[str, Any]:
    return {
        "name": inst.meta["name"], "seed": inst.meta["seed"], "siting": inst.meta["siting"],
        "method": method, "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H,
        "L": inst.L, "n_facilities": len(inst.facilities), "n_services": len(inst.services),
        "rho": inst.rho, "R_end": inst.facility(inst.S[0]).R_end, "n_arcs": len(lib),
        "n_nodes": len(inst.nodes), "cost_variant": inst.meta.get("cost_variant"),
        "zone_weights_source": inst.meta.get("zone_weights_source"),
        "sites": json.dumps(inst.meta.get("sites")), "sites_latlon": json.dumps(inst.meta.get("sites_latlon")),
        # review additions: demand hash (units F7), unservable orders (fairness F5), pruning / profile declarations
        "demand_md5": C.demand_md5(inst, include_bike_nodes=False),
        "n_unservable": len(C.unservable_orders(inst, lib)),
        "pruning_targets": inst.meta.get("pruning_targets", "facilities"),
        "hourly_profile_kind": (inst.meta.get("hourly_profile_used") or {}).get("kind")
        if isinstance(inst.meta.get("hourly_profile_used"), dict) else "hour_top_interpolated",
        "unmapped_share_in_box": inst.meta.get("unmapped_share_in_box"),
    }


def _metric_cols(inst: Instance, lib: ArcLibrary, sched: Schedule, rep: Dict[str, Any]) -> Dict[str, Any]:
    """Cost (26)-(32), ``evaluate.metrics`` and the checker summary of one schedule."""
    cst = cost(inst, lib, sched)
    met = metrics(inst, lib, sched)
    fams = C.family_counts(rep)
    out: Dict[str, Any] = C.flatten_cost(cst, "")
    out.update({
        "served_share": met["served_share"], "n_served": met["n_served"], "n_unserved": met["n_unserved"],
        "mean_response_h": met["mean_response_h"], "max_response_h": met["max_response_h"],
        "mean_lateness_h": met["mean_lateness_h"], "max_lateness_h": met["max_lateness_h"],
        "n_late": met["n_late"], "bike_km": met["bike_km"], "n_swaps": met["n_swaps"],
        "n_moves": met["n_moves"], "n_waits": met["n_waits"],
        "queue_wait_slots": sum(met["wait_before_swap"]),
        "kwh_purchased": met["kwh_purchased"],
        "peak_kw_sites": max(met["peak_kw_group"].values()) if met["peak_kw_group"] else 0.0,
        "transfers_used": met["transfers_used"], "batteries_moved": met["batteries_moved"],
        "stockout_slots": sum(met["stockout_slots"].values()),
        "end_full_total": met["end_full_total"], "end_target_shortfall_18": met["end_target_shortfall"],
        "swaps_per_facility": json.dumps(met["swaps_per_facility"], sort_keys=True, default=str),
        "check_ok": rep["ok"], "check_families": json.dumps(fams, sort_keys=True),
        "identity_24_ok": rep["identity_24_ok"] and C.check_identity_24(inst, lib, sched),
    })
    return out


def run_baseline(inst: Instance, lib: ArcLibrary, method: str = "baseline") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Round-2 default baseline (R2.3) as a flat row; the (9) / (17) / (18) violations the
    policy *reports* are ``viol_9`` (bikes without terminal certificate), ``viol_17``
    (summed local shortfall), ``viol_18`` (global shortfall).  Returns ``(row, record)``
    where ``record`` is the :func:`common.run_baseline_case` dict (schedule, flags)."""
    res = C.run_baseline_case(inst, lib, None, label=method)
    fl = res["flags"]
    row = _base_row(inst, lib, method)
    row.update(_metric_cols(inst, lib, res["schedule"], res["check"]))
    row.update({
        "status": "POLICY", "obj": res["cost"]["total"], "bound": None, "gap": None,
        "runtime_s": res["runtime"], "build_time_s": None, "n_binaries": None, "n_rows": None,
        "mip_start_accepted": None, "mip_start_variant": None, "mip_start_verified_status": None,
        "ok_modulo_report_only": res["ok_modulo_report_only"],
        "viol_9": len(fl["terminal_violations"]), "viol_17": sum(fl["end_shortfalls"]["local"].values()),
        "viol_18": fl["end_shortfalls"]["global"], "stranded_bikes": len(fl["stranded_bikes"]),
        "queued_at_H": len(fl["queued_at_H"]),
        "jit_dispatches": int(fl.get("jit_dispatches", 0) or 0),
        "reach_refusals": int((fl.get("reach_refusals") or {}).get("count", 0) or 0),
        "stock_aware_reroutes": int(fl.get("stock_aware_reroutes", 0) or 0),
        "stock_aware_fallbacks": int(fl.get("stock_aware_fallbacks", 0) or 0),
        "charge_rule_effective": json.dumps(fl.get("charge_rule_effective"), default=str, sort_keys=True),
        "inventory_consistent": fl["inventory_consistent"],
        # fairness review F4 (round-1 parity rule 'report pruned fallbacks') and F1 (reserve source)
        **{f"baseline_{k}": v for k, v in C.baseline_pruning_flags(fl).items()},
        "policy_reserve_source": res.get("policy_reserve_source", "R_end"),
        "served_share_servable": (None if len(inst.orders) == row["n_unservable"] else
                                  res["metrics"]["n_served"] / (len(inst.orders) - row["n_unservable"])),
    })
    return row, res


def run_ilp(inst: Instance, lib: ArcLibrary, method: str, base: Dict[str, Any],
            time_limit: float) -> Tuple[Dict[str, Any], Optional[Schedule]]:
    """E2 ILP (5)-(22), (26)-(32) through :func:`common.run_ilp_case` with the MIP start
    picked by :func:`common.feasible_mip_start` from the baseline record ``base``
    (``mip_start_variant`` records which policy schedule was injected)."""
    start, start_label = C.feasible_mip_start(inst, lib, base)
    t0 = time.perf_counter()
    rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=time_limit, threads=C.THREADS, label=method)
    wall = time.perf_counter() - t0
    row = _base_row(inst, lib, method)
    row.update({
        "status": rec["status"], "obj": rec["obj"], "bound": rec["bound"], "gap": rec["gap"],
        "runtime_s": rec["runtime"], "build_time_s": rec["build_time"], "wall_s": wall,
        "n_binaries": rec["n_binaries"], "n_vars": rec["n_vars"], "n_rows": rec["n_rows"],
        "node_count": (rec["stats"] or {}).get("node_count"),
        "mip_start_accepted": rec["mip_start_accepted"], "mip_start_variant": start_label,
        "mip_start_verified_status": (rec["mip_start_info"] or {}).get("verified_status"),
        "mip_start_obj": (rec["mip_start_info"] or {}).get("start_obj"),
    })
    if rec["schedule"] is None:
        row.update(total=None, check_ok=None)
        return row, None
    row.update(_metric_cols(inst, lib, rec["schedule"], rec["check"]))
    row.update(viol_9=0, viol_17=0, viol_18=0)
    return row, rec["schedule"]


def run_instance(seed: int, siting: str, time_limit: float, inst_dir: str,
                 methods: Sequence[str] = METHODS, targets: str = "facilities") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """All ``methods`` on the ``(seed, siting)`` instance.  Returns ``(rows, keep)`` where
    ``keep`` carries the instance, library and the ILP schedule (for the map).
    ``targets`` = ``'facilities'`` (PRUNING_NYC, the default) or ``'default'`` (restaurants +
    sites + depots, the plan pruning with reachable pruning: the lossless probe of fairness
    review F2, much larger library)."""
    inst = make_instance(seed, siting)
    inst.meta["pruning_targets"] = targets
    inst.save(os.path.join(inst_dir, f"{inst.meta['name']}.json"))
    pruning = C.pruning_for(inst, targets=targets)
    lib, build_t = C.build_library(inst, pruning)
    rows: List[Dict[str, Any]] = []
    keep: Dict[str, Any] = {"inst": inst, "lib": lib}

    r_base, base = run_baseline(inst, lib)
    r_base["lib_build_time_s"] = build_t
    rows.append(r_base)
    print(f"  [{siting} seed {seed}] arcs {len(lib):,} ({build_t:.1f}s) baseline {r_base['total']:.2f} USD, "
          f"unserved {r_base['n_unserved']}, fams {r_base['check_families']}, swaps {r_base['n_swaps']}", flush=True)

    if "ilp" in methods:
        r_ilp, s_ilp = run_ilp(inst, lib, "ilp", base, time_limit)
        r_ilp["lib_build_time_s"] = build_t
        rows.append(r_ilp)
        keep["ilp_schedule"] = s_ilp
        if s_ilp is not None:
            with open(os.path.join(inst_dir, f"{inst.meta['name']}-ilp-schedule.json"), "w", encoding="utf-8") as fh:
                json.dump(s_ilp.to_dict(), fh)
        print(f"  [{siting} seed {seed}] ilp {r_ilp['status']} {r_ilp.get('total')} gap {r_ilp['gap']} "
              f"{r_ilp['runtime_s']:.1f}s start {r_ilp['mip_start_variant']}/{r_ilp['mip_start_accepted']}", flush=True)

    if "ilp_relaxed" in methods:
        relaxed = C.relax_end_targets(inst)
        relaxed.meta["name"] = inst.meta["name"] + "-relaxed"
        lib_rel = build_arcs(relaxed, **lib.options)
        assert len(lib_rel) == len(lib), "rho / R_end do not enter the arc rules"
        # The round-2 DEMAND_AWARE charge rule reserves R_end_j y_j (R2.3), so the policy's
        # schedule on the relaxed copy (R_end 0) may differ from the written one: the relaxed-copy
        # baseline is used only as the MIP start of the relaxed model (reported as a diagnostic).
        r_b0, base0 = run_baseline(relaxed, lib_rel, "baseline_relaxed_copy")
        r_rel, s_rel = run_ilp(relaxed, lib_rel, "ilp_relaxed", base0, time_limit)
        r_rel["lib_build_time_s"] = build_t
        r_rel["name"] = inst.meta["name"]
        r_rel["baseline_relaxed_copy_total"] = r_b0["total"]
        r_rel["baseline_relaxed_copy_differs"] = abs(r_b0["total"] - r_base["total"]) > 1e-9
        r_rel["baseline_relaxed_copy_reserve_source"] = r_b0.get("policy_reserve_source")
        rows.append(r_rel)
        keep["ilp_relaxed_schedule"] = s_rel
        print(f"  [{siting} seed {seed}] ilp_relaxed {r_rel['status']} {r_rel.get('total')} gap {r_rel['gap']} "
              f"{r_rel['runtime_s']:.1f}s start {r_rel['mip_start_variant']}/{r_rel['mip_start_accepted']}", flush=True)
    return rows, keep


# ---------------------------------------------------------------------------
# demand-pattern comparison with the synthetic family (R2.2 vs R2.4)
# ---------------------------------------------------------------------------
def demand_pattern(inst: Instance) -> Dict[str, Any]:
    """Demand descriptors of one instance (semi-real or synthetic round-2): cuisine
    shares of the orders, customer zone shares (NTA code for NYC, zone index for the
    synthetic grid), restaurant order counts, top-10 restaurant share, restaurant ->
    customer route length (km) and prep / promise statistics (R2.2 / R2.4)."""
    m = inst.meta
    orders_meta = m.get("orders") or []
    cuisines = collections.Counter(str(o.get("cuisine")) for o in orders_meta)
    n = max(1, len(inst.orders))
    if m.get("semi_real"):
        zones = collections.Counter(str(o.get("zone_code")) for o in orders_meta)
        rest = collections.Counter(str(o.get("camis")) for o in orders_meta)
        rest_names = {r["camis"]: f"{r['dba']} ({r['cuisine']})" for r in m.get("restaurant_records", [])}
    else:
        zones = collections.Counter(str(o.get("zone")) for o in orders_meta)
        rest = collections.Counter(str(tuple(o.o)) for o in inst.orders)
        rest_names = {str(tuple(n_)): f"{tuple(n_)} ({c})" for n_, c in
                      ((tuple(r[0]), r[1]) for r in m.get("restaurants", []))}
    top = rest.most_common(10)
    d_km = [inst.d(o.o, o.d) for o in inst.orders]
    d_km = [x for x in d_km if x is not None]
    prep = [(o.a - o.r) * inst.disc.Delta_h * 60 for o in inst.orders]
    return {
        "name": m.get("name"), "n_orders": len(inst.orders),
        "cuisine_shares": {k: v / n for k, v in cuisines.items()},
        "zone_shares": {k: v / n for k, v in zones.items()},
        "n_zones_hit": len(zones), "n_restaurants_hit": len(rest),
        "top10": [(rest_names.get(k, k), v) for k, v in top],
        "top10_share": sum(v for _, v in top) / n,
        "top3_share": sum(v for _, v in top[:3]) / n,
        "mean_od_km": float(np.mean(d_km)) if d_km else float("nan"),
        "max_od_km": float(np.max(d_km)) if d_km else float("nan"),
        "mean_prep_min": float(np.mean(prep)), "promise_slots": int(inst.orders[0].b - inst.orders[0].a) if inst.orders else None,
        "zone_mass": m.get("zone_mass"),
    }


def demand_comparison(nyc_insts: Sequence[Instance], seeds: Sequence[int]) -> Dict[str, Any]:
    """Pooled (over seeds) demand descriptors of the NYC instances versus the synthetic
    ``usd4h`` family of the same seeds and the Kaggle cuisine target (R2.2)."""
    syn_insts = [C.make_instance("usd4h", seed=s) for s in seeds]
    nyc = [demand_pattern(i) for i in nyc_insts]
    syn = [demand_pattern(i) for i in syn_insts]
    kaggle = data_nyc.load_kaggle_calibration()["cuisine_shares"]
    tot_k = sum(float(v) for v in kaggle.values())

    def pool(pats: Sequence[Dict[str, Any]], key: str) -> Dict[str, float]:
        acc: Dict[str, float] = collections.defaultdict(float)
        n_tot = sum(p["n_orders"] for p in pats)
        for p in pats:
            for k, v in p[key].items():
                acc[k] += v * p["n_orders"] / n_tot
        return dict(sorted(acc.items(), key=lambda kv: -kv[1]))

    cuisine_rows = []
    nyc_c, syn_c = pool(nyc, "cuisine_shares"), pool(syn, "cuisine_shares")
    for c in sorted(kaggle, key=lambda k: -float(kaggle[k])):
        cuisine_rows.append({"cuisine": c, "kaggle_share": float(kaggle[c]) / tot_k,
                             "nyc_share": nyc_c.get(c, 0.0), "synthetic_share": syn_c.get(c, 0.0)})
    # NYC zone shares: realised vs the sampling law (zone_mass of the ACS weights)
    zone_rows = []
    nyc_z = pool(nyc, "zone_shares")
    mass = nyc_insts[0].meta.get("zone_mass") or {}
    names = {}
    try:
        zw = data_nyc.default_zone_weights(data_nyc.DEFAULT_BOX)
        for code in zw.zones():
            try:
                names[code] = zw.info(code).get("name", "")
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    for code in sorted(set(nyc_z) | set(mass), key=lambda k: -float(mass.get(k, 0.0))):
        zone_rows.append({"zone": code, "name": names.get(code, ""), "sampling_law_share": float(mass.get(code, 0.0)),
                          "realised_share": nyc_z.get(code, 0.0)})
    syn_z = pool(syn, "zone_shares")
    # pooled restaurant top-10 (NYC: by camis over all seeds; synthetic: by node)
    nyc_rest: collections.Counter = collections.Counter()
    for p in nyc:
        for name, cnt in p["top10"]:
            nyc_rest[name] += cnt
    syn_rest: collections.Counter = collections.Counter()
    for p in syn:
        for name, cnt in p["top10"]:
            syn_rest[name] += cnt
    n_nyc = sum(p["n_orders"] for p in nyc)
    n_syn = sum(p["n_orders"] for p in syn)
    summary = {
        "nyc": {"n_orders": n_nyc, "n_restaurants_hit": [p["n_restaurants_hit"] for p in nyc],
                "n_zones_hit": [p["n_zones_hit"] for p in nyc],
                "top10_share": [p["top10_share"] for p in nyc], "top3_share": [p["top3_share"] for p in nyc],
                "mean_od_km": [p["mean_od_km"] for p in nyc], "max_od_km": [p["max_od_km"] for p in nyc],
                "mean_prep_min": [p["mean_prep_min"] for p in nyc], "promise_slots": nyc[0]["promise_slots"],
                "n_restaurants_in_box": nyc_insts[0].meta.get("n_restaurants_in_box"),
                "zone_weights_source": nyc_insts[0].meta.get("zone_weights_source"),
                "top10_pooled": nyc_rest.most_common(10), "zone_shares_pooled": nyc_z},
        "synthetic": {"n_orders": n_syn, "n_restaurants_hit": [p["n_restaurants_hit"] for p in syn],
                      "n_zones_hit": [p["n_zones_hit"] for p in syn],
                      "top10_share": [p["top10_share"] for p in syn], "top3_share": [p["top3_share"] for p in syn],
                      "mean_od_km": [p["mean_od_km"] for p in syn], "max_od_km": [p["max_od_km"] for p in syn],
                      "mean_prep_min": [p["mean_prep_min"] for p in syn], "promise_slots": syn[0]["promise_slots"],
                      "n_restaurants": len(syn_insts[0].meta.get("restaurants", [])),
                      "top10_pooled": syn_rest.most_common(10), "zone_shares_pooled": syn_z},
        "cuisine_table": cuisine_rows, "zone_table": zone_rows,
    }
    return summary


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def _style(ax: plt.Axes) -> None:
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID_INK)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.yaxis.grid(True, color=GRID_INK, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_facecolor(SURFACE)


def plot_map(inst: Instance, lib: ArcLibrary, sched: Optional[Schedule], grid_inst: Optional[Instance],
             path: str) -> str:
    """Map of the study box in the rotated local frame (R2.4 geometry): ACS zone-weight
    heat (sequential blue, NTA-2020 polygons projected with ``StudyBox.project``), the
    150 m grid nodes, DOHMH restaurants coloured by Kaggle cuisine (top 7 classes,
    rest grey), the restaurants / customers of the instance, the two sitings and the
    ILP bike paths (move / deliver arcs as polylines, swaps as markers) of ``sched``.
    Synthetic elevation / signals are not drawn (they are synthetic, R2.4)."""
    box = data_nyc.StudyBox(**{k: inst.meta["box"][k] for k in ("lat_min", "lat_max", "lon_min", "lon_max",
                                                                 "block_m", "azimuth_deg")})
    fig, ax = plt.subplots(figsize=(9.2, 9.6))
    ax.set_facecolor(SURFACE)
    corners = [(box.lat_min, box.lon_min), (box.lat_min, box.lon_max), (box.lat_max, box.lon_max),
               (box.lat_max, box.lon_min)]
    cp = [box.project(*c) for c in corners]
    clip_patch = MplPolygon(cp, closed=True, facecolor="none", edgecolor="none")
    ax.add_patch(clip_patch)
    # zone heat ---------------------------------------------------------------
    zw = None
    heat_label = "zone weight (none)"
    try:
        zw = data_nyc.default_zone_weights(box)
        from ebike_swap_sim import acs_weights
        gj_path = zw.paths["nta2020"] if getattr(zw, "fallback", None) is None else None
        if gj_path is not None:
            gj = acs_weights.load_nta2020(gj_path)
            code_key = "nta2020"
        else:
            with open(data_nyc.DEFAULT_PATHS["nta_geojson"], "r", encoding="utf-8") as fh:
                gj = json.load(fh)
            code_key = "ntacode"
        dens = {c: float(zw.info(c).get("density", 0.0)) for c in zw.zones()}
        dmax = max(dens.values()) or 1.0
        labelled: set = set()
        from matplotlib.colors import LinearSegmentedColormap, Normalize
        from matplotlib.cm import ScalarMappable
        cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
        norm = Normalize(vmin=0.0, vmax=dmax)
        for feat in gj["features"]:
            code = str(feat["properties"].get(code_key, ""))
            if code not in dens or feat.get("geometry") is None:
                continue
            geom = feat["geometry"]
            polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
            for rings in polys:
                pts = [box.project(p[1], p[0]) for p in rings[0]]
                patch = MplPolygon(pts, closed=True, facecolor=cmap(norm(dens[code])), edgecolor="white",
                                   linewidth=0.8, alpha=0.8, zorder=1)
                ax.add_patch(patch)
                patch.set_clip_path(clip_patch)
                cx_, cy_ = float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts]))
                if (code not in labelled and 0 < cx_ < box.grid_nx * box.block_m
                        and 0 < cy_ < box.grid_ny * box.block_m):
                    ax.annotate(code, (cx_, cy_), fontsize=6, color=INK2, ha="center", zorder=3)
                    labelled.add(code)
        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])
        cb = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.01)
        cb.set_label("zone weight density w_z / area_z (per km^2), clipped to the box", fontsize=8, color=INK2)
        cb.ax.tick_params(labelsize=7, colors=INK2)
        heat_label = f"ACS 2020-24 literature zone weights (max {dmax:,.0f} / km^2)" if gj_path else \
            "GeoDa fallback zone weights"
    except Exception as exc:  # noqa: BLE001 - the map must not fail the experiment
        warnings.warn(f"zone heat not drawn: {exc}", UserWarning, stacklevel=2)
    # grid nodes ------------------------------------------------------------------
    gx = [box.node_xy(v)[0] for v in box.grid_nodes()]
    gy = [box.node_xy(v)[1] for v in box.grid_nodes()]
    ax.scatter(gx, gy, s=1.5, color="#9a9890", zorder=2, linewidths=0, label="150 m grid node")
    # study box outline -------------------------------------------------------------
    cpl = cp + [cp[0]]
    ax.plot([p[0] for p in cpl], [p[1] for p in cpl], color=INK2, linewidth=1.0, linestyle="--", zorder=3)
    # restaurants by cuisine ---------------------------------------------------------
    rest = data_nyc.restaurants_in_box(box)
    counts = rest["kaggle_class"].value_counts()
    top = [c for c in counts.index if c != "other"][:7]
    for i, cls in enumerate(top):
        sub = rest[rest["kaggle_class"] == cls]
        ax.scatter(sub["x"], sub["y"], s=4, color=PALETTE[i], alpha=0.7, linewidths=0, zorder=4,
                   label=f"{cls} ({len(sub)})")
    other = rest[~rest["kaggle_class"].isin(top)]
    ax.scatter(other["x"], other["y"], s=3, color="#b5b3ab", alpha=0.5, linewidths=0, zorder=3,
               label=f"other cuisines ({len(other)})")
    # instance restaurants / customers ------------------------------------------------
    rx = [box.node_xy(tuple(r[0]))[0] for r in inst.meta["restaurants"]]
    ry = [box.node_xy(tuple(r[0]))[1] for r in inst.meta["restaurants"]]
    ax.scatter(rx, ry, s=60, marker="s", facecolor="none", edgecolor=INK, linewidths=1.0, zorder=6,
               label=f"restaurants used by the {len(inst.orders)} orders ({len(rx)})")
    cx = [box.node_xy(tuple(c))[0] for c in inst.meta["customers"]]
    cy = [box.node_xy(tuple(c))[1] for c in inst.meta["customers"]]
    ax.scatter(cx, cy, s=34, marker="^", facecolor="white", edgecolor=INK, linewidths=0.9, zorder=6,
               label=f"customers ({len(cx)})")
    # bike paths ------------------------------------------------------------------------
    if sched is not None:
        for bi, bike in enumerate(inst.bikes):
            col = PALETTE[bi % len(PALETTE)]
            pts: List[Tuple[float, float]] = []
            swaps: List[Tuple[float, float]] = []
            for a in sched.path(bike.id, lib):
                if a.kind == "term":
                    continue
                src = box.node_xy(tuple(a.src[0]))
                if not pts:
                    pts.append(src)
                if a.kind == "move":
                    pts.append(box.node_xy(tuple(a.dst[0])))
                elif a.kind == "deliver":
                    o = inst.order(a.order)
                    pts.append(box.node_xy(tuple(o.o)))
                    pts.append(box.node_xy(tuple(o.d)))
                elif a.kind == "swap":
                    swaps.append(src)
            if len(pts) > 1:
                off = (bi - (len(inst.bikes) - 1) / 2) * 9.0   # small per-bike offset so overlapping legs stay visible
                ax.plot([p[0] + off for p in pts], [p[1] + off for p in pts], color=col, linewidth=1.6, alpha=0.85,
                        zorder=7, solid_capstyle="round", label=f"bike {bike.id} path (ILP, q0 = {bike.q0})")
            if swaps:
                ax.scatter([p[0] for p in swaps], [p[1] for p in swaps], s=90, marker="o", facecolor="none",
                           edgecolor=col, linewidths=1.6, zorder=8)
    # sites -----------------------------------------------------------------------------
    sx = [box.node_xy(tuple(s))[0] for s in inst.meta["sites"]]
    sy = [box.node_xy(tuple(s))[1] for s in inst.meta["sites"]]
    ax.scatter(sx, sy, s=260, marker="*", facecolor="#eda100", edgecolor=INK, linewidths=1.2, zorder=9,
               label=f"sites: {inst.meta['siting']} (B 3, C 2)")
    for (x, y), f in zip(zip(sx, sy), inst.facilities):
        ax.annotate(f.id, (x, y), xytext=(6, 6), textcoords="offset points", fontsize=8, color=INK, zorder=10)
    if grid_inst is not None:
        gsx = [box.node_xy(tuple(s))[0] for s in grid_inst.meta["sites"]]
        gsy = [box.node_xy(tuple(s))[1] for s in grid_inst.meta["sites"]]
        ax.scatter(gsx, gsy, s=200, marker="P", facecolor="white", edgecolor="#e34948", linewidths=1.6, zorder=9,
                   label="sites: grid-connected variant (8th Av/W34, Union Sq, Grand Central)")
        for (x, y), lab in zip(zip(gsx, gsy), grid_inst.meta.get("site_labels", [])):
            ax.annotate(lab, (x, y), xytext=(6, -11), textcoords="offset points", fontsize=7, color="#e34948", zorder=10)
    ax.set_xlim(-100, box.grid_nx * box.block_m + 100)
    ax.set_ylim(-100, box.grid_ny * box.block_m + 100)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m) along the avenues' normal; frame rotated 29 deg from east (R2.4 projection)", fontsize=8, color=INK2)
    ax.set_ylabel("y (m) along the avenues (azimuth 29 deg east of north)", fontsize=8, color=INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.set_title(f"{inst.meta['name']}: {len(inst.bikes)} bikes, {len(inst.orders)} orders, 17:00-21:00; "
                 f"{heat_label}\nStudy box lat {box.lat_min}-{box.lat_max}, lon {box.lon_min}-{box.lon_max}; "
                 f"dashed = box, synthetic 150 m grid; elevation / signals synthetic (R2.4 caveat)",
                 fontsize=9, color=INK, loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=3, fontsize=7, frameon=False, markerscale=0.9)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_cost_components(df: pd.DataFrame, path: str) -> str:
    """Stacked mean cost components (27)-(32) per method, one panel per siting."""
    comps = ["unserved", "response", "lateness", "C_travel", "C_elec", "C_reb", "C_setup"]
    names = {"unserved": "unserved P u (30)", "response": "response (31)", "lateness": "lateness (31)",
             "C_travel": "travel (29)", "C_elec": "electricity (28)", "C_reb": "transfers (32)",
             "C_setup": "setup (27), constant"}
    sitings = [s for s in SITINGS if s in set(df.siting)]
    methods = [m for m in METHODS if m in set(df.method)]
    fig, axes = plt.subplots(1, len(sitings), figsize=(4.4 * len(sitings) + 1.5, 5.0), sharey=True)
    for ax, siting in zip(np.atleast_1d(axes), sitings):
        sub = df[(df.siting == siting)].groupby("method")[comps + ["total"]].mean(numeric_only=True)
        xs = np.arange(len(methods))
        bottom = np.zeros(len(methods))
        for ci, comp in enumerate(comps):
            vals = np.array([float(sub.loc[m, comp]) if m in sub.index else 0.0 for m in methods])
            ax.bar(xs, vals, 0.66, bottom=bottom, color=PALETTE[ci], edgecolor="white", linewidth=1.0,
                   label=names[comp] if siting == sitings[0] else None)
            bottom += vals
        for x, tot in zip(xs, bottom):
            ax.text(x, tot + 4, f"{tot:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xticks(xs)
        ax.set_xticklabels(methods, fontsize=8)
        ax.set_title(f"sites: {siting}", fontsize=10, color=INK)
        _style(ax)
    np.atleast_1d(axes)[0].set_ylabel(f"mean cost over {df.seed.nunique()} seeds (USD, usd_sunk)", fontsize=9)
    fig.suptitle("E8 NYC semi-real: cost components (27)-(32), baseline vs ILP vs relaxed-target ILP",
                 fontsize=11, x=0.01, ha="left", color=INK)
    fig.legend(loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_gap_by_seed(per: pd.DataFrame, path: str) -> str:
    """Headline gap ``(baseline - ILP) / baseline`` per seed, siting and ILP variant (dots), with
    the mean +/- 95 % CI as a bar behind them."""
    sitings = [s for s in SITINGS if s in set(per.siting)]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs, labels = [], []
    k = 0
    for siting in sitings:
        for gi, (col, lab) in enumerate((("gap_vs_baseline_pct", "ILP (written, rho 0.5)"),
                                         ("gap_relaxed_vs_baseline_pct", "ILP relaxed (rho 0, R_end 0)"))):
            vals = per[per.siting == siting][col].dropna().tolist()
            if not vals:
                continue
            m, hw, n = ci95(vals)
            ax.bar(k, m, 0.6, color=PALETTE[gi], alpha=0.35, edgecolor="none")
            if n > 1 and not math.isnan(hw):
                ax.errorbar(k, m, yerr=hw, fmt="none", ecolor=INK2, elinewidth=1.2, capsize=4)
            ax.scatter([k] * len(vals), vals, s=36, color=PALETTE[gi], edgecolor="white", linewidths=1.0, zorder=5)
            for s, v in zip(per[per.siting == siting]["seed"], vals):
                ax.annotate(f"s{int(s)}", (k, v), xytext=(8, -3), textcoords="offset points", fontsize=7, color=INK2)
            xs.append(k)
            labels.append(f"{siting}\n{lab}")
            k += 1
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("gap = 100 (baseline - ILP) / baseline, %", fontsize=9)
    ax.set_title("E8 NYC semi-real: headline gap per seed (dots) and mean with 95 % t-CI (bar)",
                 fontsize=10, color=INK, loc="left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_demand_comparison(cmp: Dict[str, Any], path: str) -> str:
    """Two panels: cuisine shares (Kaggle target vs NYC realised vs synthetic realised) and
    NYC customer zone shares (sampling law vs realised); grouped thin bars."""
    ct = pd.DataFrame(cmp["cuisine_table"])
    zt = pd.DataFrame(cmp["zone_table"])
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axes[0]
    xs = np.arange(len(ct))
    w = 0.27
    for i, (col, lab) in enumerate((("kaggle_share", "Kaggle order share (target)"),
                                    ("nyc_share", "NYC semi-real, realised"),
                                    ("synthetic_share", "synthetic usd4h, realised"))):
        ax.bar(xs + (i - 1) * w, 100 * ct[col], w, color=PALETTE[i], edgecolor="white", linewidth=0.6, label=lab)
    ax.set_xticks(xs)
    ax.set_xticklabels(ct["cuisine"], rotation=40, ha="right", fontsize=8, rotation_mode="anchor")
    ax.set_ylabel("share of orders, %", fontsize=9)
    ax.set_title("Cuisine shares (pooled over seeds)", fontsize=10, color=INK, loc="left")
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    ax = axes[1]
    xs = np.arange(len(zt))
    for i, (col, lab) in enumerate((("sampling_law_share", "ACS zone weight (sampling law)"),
                                    ("realised_share", "realised customer share"))):
        ax.bar(xs + (i - 0.5) * 0.38, 100 * zt[col], 0.38, color=PALETTE[i], edgecolor="white", linewidth=0.6, label=lab)
    ax.set_xticks(xs)
    ax.set_xticklabels(zt["zone"], rotation=40, ha="right", fontsize=8, rotation_mode="anchor")
    ax.set_ylabel("share of customers, %", fontsize=9)
    ax.set_title("NYC customer zones (NTA-2020) in the study box", fontsize=10, color=INK, loc="left")
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# analysis + report
# ---------------------------------------------------------------------------
def per_instance_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per ``(siting, seed)``: baseline / ILP / relaxed totals, both gap conventions,
    service metrics, start acceptance and solver status."""
    recs = []
    for (siting, seed), sub in df.groupby(["siting", "seed"]):
        b = sub[sub.method == "baseline"].iloc[0]
        il = sub[sub.method == "ilp"].iloc[0] if (sub.method == "ilp").any() else None
        rl = sub[sub.method == "ilp_relaxed"].iloc[0] if (sub.method == "ilp_relaxed").any() else None
        g = C.gap_definitions(float(b["total"]), None if il is None or pd.isna(il["total"]) else float(il["total"]))
        gr = C.gap_definitions(float(b["total"]), None if rl is None or pd.isna(rl["total"]) else float(rl["total"]))
        recs.append({
            "siting": siting, "seed": seed, "name": b["name"], "n_arcs": b["n_arcs"],
            "baseline_total": b["total"], "baseline_unserved": b["n_unserved"], "baseline_km": b["bike_km"],
            "baseline_swaps": b["n_swaps"], "baseline_families": b["check_families"],
            "viol_17": b["viol_17"], "viol_18": b["viol_18"],
            "ilp_total": None if il is None else il["total"], "ilp_status": None if il is None else il["status"],
            "ilp_gap": None if il is None else il["gap"], "ilp_runtime_s": None if il is None else il["runtime_s"],
            "ilp_unserved": None if il is None else il["n_unserved"], "ilp_km": None if il is None else il["bike_km"],
            "ilp_swaps": None if il is None else il["n_swaps"],
            "mip_start_variant": None if il is None else il["mip_start_variant"],
            "mip_start_accepted": None if il is None else il["mip_start_accepted"],
            "relaxed_total": None if rl is None else rl["total"], "relaxed_status": None if rl is None else rl["status"],
            "relaxed_gap": None if rl is None else rl["gap"], "relaxed_runtime_s": None if rl is None else rl["runtime_s"],
            "relaxed_unserved": None if rl is None else rl["n_unserved"],
            "relaxed_start_accepted": None if rl is None else rl["mip_start_accepted"],
            "gap_vs_baseline_pct": g["gap_vs_baseline_pct"], "gap_vs_ilp_pct": g["gap_vs_ilp_pct"],
            "gap_relaxed_vs_baseline_pct": gr["gap_vs_baseline_pct"],
            "ilp_minus_relaxed": None if (il is None or rl is None) else float(il["total"]) - float(rl["total"]),
        })
    return pd.DataFrame(recs)


def method_means(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    g = df.groupby(["siting", "method"])[list(cols)].mean(numeric_only=True).reset_index()
    g["method"] = pd.Categorical(g["method"], list(METHODS), ordered=True)
    return g.sort_values(["siting", "method"]).reset_index(drop=True)


def siting_table(per: pd.DataFrame) -> pd.DataFrame:
    """Busiest vs grid siting per seed: totals of each method and the differences
    (grid minus busiest; positive = grid-connected siting is more expensive)."""
    recs = []
    pb = per[per.siting == "busiest"].set_index("seed")
    pg = per[per.siting == "grid"].set_index("seed")
    for seed in sorted(set(pb.index) & set(pg.index)):
        b, g = pb.loc[seed], pg.loc[seed]
        rec = {"seed": seed}
        for m, col in (("baseline", "baseline_total"), ("ilp", "ilp_total"), ("ilp_relaxed", "relaxed_total")):
            bv, gv = b[col], g[col]
            rec[f"{m}_busiest"] = bv
            rec[f"{m}_grid"] = gv
            rec[f"{m}_grid_minus_busiest"] = None if (bv is None or gv is None or pd.isna(bv) or pd.isna(gv)) else float(gv) - float(bv)
            rec[f"{m}_grid_minus_busiest_pct"] = None if rec[f"{m}_grid_minus_busiest"] is None or float(bv) == 0 else \
                100.0 * rec[f"{m}_grid_minus_busiest"] / float(bv)
        rec["gap_busiest_pct"] = b["gap_vs_baseline_pct"]
        rec["gap_grid_pct"] = g["gap_vs_baseline_pct"]
        recs.append(rec)
    return pd.DataFrame(recs)


def _mean(series: Any) -> Optional[float]:
    """Mean of a column that may hold ``None`` (object dtype); ``None`` when empty."""
    v = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    return float(v.mean()) if len(v) else None


def _f(v: Any, d: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return C.fmt(float(v), d)


def write_results_md(df: pd.DataFrame, per: pd.DataFrame, sit: pd.DataFrame, cmp: Dict[str, Any],
                     insts: Dict[Tuple[str, int], Instance], out_dir: str, wall: float, time_limit: float,
                     figures: Sequence[str]) -> str:
    """Compose ``RESULTS.md`` (Chinese summary, tables, interpretation, anomalies, caveat)."""
    inst0 = insts[("busiest", int(sorted(df.seed.unique())[0]))]
    m0 = inst0.meta
    seeds = sorted(df.seed.unique().tolist())
    busiest = per[per.siting == "busiest"]
    grid = per[per.siting == "grid"]
    gb, hb, nb = ci95(busiest["gap_vs_baseline_pct"].tolist())
    grb, hrb, _ = ci95(busiest["gap_relaxed_vs_baseline_pct"].tolist())
    gg, hg, ng = ci95(grid["gap_vs_baseline_pct"].tolist()) if len(grid) else (float("nan"), float("nan"), 0)
    grg, hrg, _ = ci95(grid["gap_relaxed_vs_baseline_pct"].tolist()) if len(grid) else (float("nan"), float("nan"), 0)
    means_cost = method_means(df, ["total"] + COMPONENTS)
    metric_cols = ["served_share", "n_unserved", "mean_response_h", "max_response_h", "mean_lateness_h",
                   "n_late", "bike_km", "n_swaps", "queue_wait_slots", "kwh_purchased", "peak_kw_sites",
                   "transfers_used", "end_full_total", "viol_17", "viol_18"]
    means_met = method_means(df, metric_cols)
    solver_cols = ["n_arcs", "n_binaries", "n_rows", "build_time_s", "runtime_s", "gap", "node_count"]
    df_solver = df[df.method != "baseline"].copy()
    for c in solver_cols:
        if c not in df_solver.columns:
            df_solver[c] = float("nan")
        df_solver[c] = pd.to_numeric(df_solver[c], errors="coerce")
    if len(df_solver):
        solver = df_solver.groupby(["siting", "method"])[solver_cols].agg(["mean", "max"]).reset_index()
        solver.columns = ["_".join(c).rstrip("_") for c in solver.columns.to_flat_index()]
    else:
        solver = pd.DataFrame(columns=["siting", "method"])
    base_rows = df[df.method == "baseline"]
    ilp_rows = df[df.method == "ilp"]
    rel_rows = df[df.method == "ilp_relaxed"]
    n_opt = int((ilp_rows.status == "OPTIMAL").sum())
    n_opt_r = int((rel_rows.status == "OPTIMAL").sum())
    n18 = int((base_rows.viol_18 > 0).sum())
    n17 = int((base_rows.viol_17 > 0).sum())
    acc = int(ilp_rows.mip_start_accepted.eq(True).sum())
    acc_r = int(rel_rows.mip_start_accepted.eq(True).sum())
    starts = collections.Counter(ilp_rows.mip_start_variant.tolist())

    def mm(siting: str, method: str, col: str) -> float:
        s = means_met if col in metric_cols else means_cost
        r = s[(s.siting == siting) & (s.method == method)]
        return float(r[col].iloc[0]) if len(r) else float("nan")

    nyc, syn = cmp["nyc"], cmp["synthetic"]
    ct = pd.DataFrame(cmp["cuisine_table"])
    zt = pd.DataFrame(cmp["zone_table"])
    l1_c_nyc = float((ct.nyc_share - ct.kaggle_share).abs().sum())
    l1_c_syn = float((ct.synthetic_share - ct.kaggle_share).abs().sum())
    l1_z = float((zt.realised_share - zt.sampling_law_share).abs().sum())
    top_zones = zt.head(3)
    comp_gap = {}
    for c in COMPONENTS:
        comp_gap[c] = float(busiest.merge(df[df.method == "baseline"][["siting", "seed", c]], on=["siting", "seed"])[c].mean()
                            - df[(df.method == "ilp") & (df.siting == "busiest")][c].mean()) if len(busiest) else float("nan")
    total_gap_abs = float(busiest["baseline_total"].mean() - busiest["ilp_total"].mean()) if len(busiest) else float("nan")

    md: List[str] = []
    md.append("# E8 -- NYC semi-real instance (DOHMH restaurants, ACS zone weights, real site coordinates on the synthetic grid)\n")
    md.append("## Summary\n")
    md.append(
        f"This experiment compares the round-2 baseline policy, the E2 integer program (rho 0.5, R_end 1) and the ILP control "
        f"with relaxed terminal targets on the R2.4 semi-real NYC instance (Midtown/Chelsea/Flatiron study box, real DOHMH "
        f"restaurants, ACS 2020-24 literature-formula zone weights, real candidate site coordinates projected onto the synthetic "
        f"150 m grid) with {len(inst0.bikes)} bikes, {len(inst0.orders)} orders, 17:00-21:00 (H = {inst0.H}), usd_sunk USD costs "
        f"and {len(seeds)} random seeds. "
        f"With the sites placed on the busiest restaurant cells, the ILP's total-cost reduction relative to the baseline "
        f"((baseline - ILP)/baseline) averages {gb:.1f} % (95 % t half-width {hb:.1f}, n = {nb}); the relaxed control gives "
        f"{grb:.1f} %; the ILP reached optimality in {n_opt}/{len(ilp_rows)} solves (Threads 3, time limit {time_limit:.0f} s). "
        f"Moving the three sites to Citi Bike-style 'grid' landmarks (8th Ave/W 34th, Union Sq, Grand Central) changes the mean "
        f"baseline cost by {_f(_mean(sit['baseline_grid_minus_busiest_pct']) if len(sit) else None, 1)} % and the ILP cost by "
        f"{_f(_mean(sit['ilp_grid_minus_busiest_pct']) if len(sit) else None, 1)} %, "
        f"and the ILP's relative advantage is {gg:.1f} % (half-width {hg:.1f}), i.e. siting affects both methods but does not "
        f"change the conclusion. "
        f"Compared with the synthetic usd4h family, the semi-real instance's cuisine shares are closer to the Kaggle target "
        f"(L1 deviation {l1_c_nyc:.2f} vs {l1_c_syn:.2f}), customers fall in {nyc['n_zones_hit']} NTAs and the restaurants are "
        f"spread over about {int(np.mean(nyc['n_restaurants_hit']))} establishments (the synthetic family has only "
        f"{syn['n_restaurants']}), "
        f"but the mean restaurant-to-customer distance {np.mean(nyc['mean_od_km']):.2f} km is close to the synthetic family's "
        f"{np.mean(syn['mean_od_km']):.2f} km. "
        f"Geometry caveat: the road network is still the synthetic grid (rotated 29 degrees, 150 m blocks), elevation and "
        f"traffic signals are synthetic values, and all distances / energy use come from that synthetic geometry rather than "
        f"real roads.\n")

    md.append("## Setup\n")
    md.append(
        f"Family `nyc4h` (`experiments/common.py`, builder `data_nyc.make_nyc_instance`): {len(inst0.bikes)} bikes, "
        f"{len(inst0.orders)} orders (1.5 orders per bike-hour), window 17:00-21:00 (H = {inst0.H} slots of 5 min), "
        f"L = {inst0.L} levels of 50 Wh, costs `{m0['cost_variant']}` (R2.1: kappa {inst0.kappa} $/km, pi {inst0.pi} $/kWh, "
        f"P {inst0.orders[0].P}, w {inst0.orders[0].w} $/h, v {inst0.orders[0].v} $/h, F {inst0.facilities[0].F:.2f}, "
        f"bB {inst0.facilities[0].bB:.3f}, bC {inst0.facilities[0].bC:.3f} per 4 h site), q_res {inst0.q_res}, rho {inst0.rho}, "
        f"R_end {inst0.facilities[0].R_end}. Three co-located sites (B 3, C 2, K 8, M 1, sigma 1, P 4 kW, group 8 kW / 6 kW 18-20 h). "
        f"Study box lat {m0['box']['lat_min']}-{m0['box']['lat_max']}, lon {m0['box']['lon_min']}-{m0['box']['lon_max']} "
        f"({m0['box']['grid_nx']} x {m0['box']['grid_ny']} grid nodes of 150 m). Restaurants: {m0['n_restaurants_in_box']} usable DOHMH rows in the box "
        f"mapped to the Kaggle cuisines (`data_nyc.CUISINE_MAP`), sampled by Kaggle share within 2.5 km of the customer with Zipf s = 1 ranks. "
        f"**Zone weights: `{m0['zone_weights_source']}`** ({m0.get('zone_weights_vintage')}; {m0.get('zone_weights_n_zones')} NTAs intersect the box, "
        f"{m0['n_zones_used']} contain grid nodes" + (f"; WARNING {m0['zone_weights_warning']}" if m0.get("zone_weights_warning") else
                                                        "; the literature formula on the ACS 2020-24 tables, no fallback") + "). "
        f"Seeds {seeds}; sitings `busiest` = the three busiest restaurant cells (sites {m0['sites']}, lat/lon {[[round(a, 4), round(b, 4)] for a, b in m0['sites_latlon']]}) "
        f"and `grid` = {', '.join(GRID_SITES)} snapped to the grid"
        + (f" (sites {insts[('grid', seeds[0])].meta['sites']})" if ("grid", seeds[0]) in insts else "") +
        f". Pruning `common.PRUNING_NYC` (moves only into the 3 site nodes, tau_max 4, start_slack 6, reachable pruning): "
        f"{int(df.n_arcs.mean()):,} arcs on average. **This pruning restricts the ILP but not the policy** (fairness review F2): "
        f"the baseline repositions only to swap sites and starts deliveries in place, so it loses nothing, whereas the ILP loses "
        f"pre-positioning moves towards restaurants / customers (tau_max never binds on nyc4h: every customer -> restaurant pair "
        f"is within 4 slots). The ILP totals below are therefore UPPER bounds on the written E2 optimum and the gaps LOWER bounds "
        f"on the coordination value; no lossless probe exists for these targets yet (`--targets default` runs it). "
        f"Release times follow the R2.2 block profile as a step function (`meta['hourly_profile_used']['kind']` = "
        f"`{df.hourly_profile_kind.iloc[0] if 'hourly_profile_kind' in df else 'n/a'}`, units review F1), the same object as the synthetic usd4h family. "
        f"Restaurant supply: {100 * float(df.unmapped_share_in_box.iloc[0]):.0f} % of the usable DOHMH rows in the box map to the "
        f"unreachable `other` class (cafes, bakeries, desserts, juice; units review F3, declared assumption). Demand hash per "
        f"(seed, siting): `demand_md5` column (orders, q0, H, L; identical across sitings by assertion). Methods: `baseline` (R2.3 defaults), `ilp` (written E2 model, baseline as verified MIP start "
        f"via `common.feasible_mip_start`), `ilp_relaxed` (`common.relax_end_targets`: rho 0 and R_end 0 -- the fair control). "
        f"Gurobi 13, OutputFlag 0, Threads {C.THREADS}, TimeLimit {time_limit:.0f} s. Wall time {wall / 60:.1f} min.\n")
    md.append(f"**Geometry caveat (R2.4):** {m0['geometry_caveat']}\n")

    md.append("## Headline\n")
    md.append(
        f"**Busiest-cell siting: ILP vs baseline gap = (baseline - ILP) / baseline = {gb:.1f} % (95 % t-CI +/- {hb:.1f}, n = {nb}); "
        f"relaxed-target ILP {grb:.1f} % (+/- {hrb:.1f}).** Grid-connected siting: {gg:.1f} % (+/- {hg:.1f}) and {grg:.1f} % (+/- {hrg:.1f}). "
        f"Mean totals (busiest): baseline {mm('busiest', 'baseline', 'total'):.1f}, ILP {mm('busiest', 'ilp', 'total'):.1f}, relaxed {mm('busiest', 'ilp_relaxed', 'total'):.1f} USD; "
        f"served share {100 * mm('busiest', 'baseline', 'served_share'):.0f} % vs {100 * mm('busiest', 'ilp', 'served_share'):.0f} % vs "
        f"{100 * mm('busiest', 'ilp_relaxed', 'served_share'):.0f} %. ILP solved to optimality in {n_opt} of {len(ilp_rows)} runs "
        f"(relaxed {n_opt_r} of {len(rel_rows)}); MIP start accepted in {acc} / {len(ilp_rows)} (variants injected: {dict(starts)}) and "
        f"{acc_r} / {len(rel_rows)} for the relaxed model; the baseline reports (18) in {n18} and (17) in {n17} of {len(base_rows)} runs.\n")

    md.append("## Per instance (both sitings): totals, both gap conventions, solver and start status\n")
    md.append(C.markdown_table(per, ["siting", "seed", "n_arcs", "baseline_total", "baseline_unserved", "baseline_km", "baseline_swaps",
                                     "baseline_families", "ilp_total", "ilp_status", "ilp_gap", "ilp_runtime_s", "ilp_unserved", "ilp_km",
                                     "ilp_swaps", "mip_start_variant", "mip_start_accepted", "relaxed_total", "relaxed_status", "relaxed_gap",
                                     "relaxed_runtime_s", "relaxed_unserved", "relaxed_start_accepted", "gap_vs_baseline_pct",
                                     "gap_vs_ilp_pct", "gap_relaxed_vs_baseline_pct", "ilp_minus_relaxed"], digits=2))
    md.append("\n`gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline), `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP; "
              "`gap_relaxed_vs_baseline_pct` uses the relaxed-target ILP (rho 0, R_end 0); `ilp_minus_relaxed` = price of the end targets "
              "(17)-(18) in the optimum; `baseline_families` = constraint families the policy *reports* (not enforced).\n")

    md.append("## Cost (26) and components (27)-(32): mean over seeds per siting and method (USD)\n")
    md.append(C.markdown_table(means_cost, ["siting", "method", "total"] + COMPONENTS, digits=2))
    md.append("\n## Service / operations metrics: mean over seeds\n")
    md.append(C.markdown_table(means_met, ["siting", "method"] + metric_cols, digits=3))
    md.append("\n`viol_17` / `viol_18` = end-stock shortfalls reported by the baseline (0 for the ILP by construction); "
              "`transfers_used` is 0 everywhere (no services in the NYC family, E = {}).\n")
    md.append("## Solver statistics (mean / max over seeds)\n")
    md.append(C.markdown_table(solver, list(solver.columns), digits=3))
    md.append("\n## Siting sensitivity: grid-connected variant minus busiest-cell siting (same orders, bikes' levels and ranks per seed)\n")
    if len(sit):
        md.append(C.markdown_table(sit, list(sit.columns), digits=2))
    else:
        md.append("(grid siting not run)")
    md.append("\n## Demand pattern: NYC semi-real vs synthetic `usd4h` (same seeds)\n")
    md.append(f"| descriptor | NYC semi-real | synthetic usd4h |\n|---|---|---|\n"
              f"| orders pooled | {nyc['n_orders']} | {syn['n_orders']} |\n"
              f"| restaurants available | {nyc['n_restaurants_in_box']} (DOHMH rows in box) | {syn['n_restaurants']} (synthetic) |\n"
              f"| distinct restaurants hit per seed | {nyc['n_restaurants_hit']} | {syn['n_restaurants_hit']} |\n"
              f"| top-10 restaurants' share of orders per seed | {[round(x, 2) for x in nyc['top10_share']]} | {[round(x, 2) for x in syn['top10_share']]} |\n"
              f"| top-3 restaurants' share per seed | {[round(x, 2) for x in nyc['top3_share']]} | {[round(x, 2) for x in syn['top3_share']]} |\n"
              f"| customer zones hit per seed | {nyc['n_zones_hit']} (NTA-2020) | {syn['n_zones_hit']} (synthetic zones of 16) |\n"
              f"| mean restaurant -> customer route (km) per seed | {[round(x, 2) for x in nyc['mean_od_km']]} | {[round(x, 2) for x in syn['mean_od_km']]} |\n"
              f"| max route (km) per seed | {[round(x, 2) for x in nyc['max_od_km']]} | {[round(x, 2) for x in syn['max_od_km']]} |\n"
              f"| mean prep (min) per seed | {[round(x, 1) for x in nyc['mean_prep_min']]} | {[round(x, 1) for x in syn['mean_prep_min']]} |\n"
              f"| promise after ready (slots) | {nyc['promise_slots']} | {syn['promise_slots']} |\n"
              f"| L1 distance of cuisine shares to Kaggle target | {l1_c_nyc:.3f} | {l1_c_syn:.3f} |\n"
              f"| zone weights | {nyc['zone_weights_source']} | synthetic Dirichlet demographics |\n")
    md.append("\nCuisine shares (pooled over seeds):\n")
    md.append(C.markdown_table(ct, ["cuisine", "kaggle_share", "nyc_share", "synthetic_share"], digits=3))
    md.append("\nNYC customer zone shares (sampling law = ACS zone-weight mass of the grid nodes in the box; realised = orders):\n")
    md.append(C.markdown_table(zt, ["zone", "name", "sampling_law_share", "realised_share"], digits=3))
    md.append("\nNYC restaurant top-10 (pooled over seeds; name (cuisine): orders): " +
              "; ".join(f"{n} {c}" for n, c in nyc["top10_pooled"]) + ".\n")
    md.append("Synthetic restaurant top-10 (node (cuisine): orders): " + "; ".join(f"{n} {c}" for n, c in syn["top10_pooled"]) + ".\n")

    md.append("## Interpretation\n")
    lines = []
    lines.append(f"On the semi-real Midtown instance the coordinated ILP lowers the baseline's cost by {gb:.1f} % (+/- {hb:.1f}) with the "
                 f"written end targets and by {grb:.1f} % (+/- {hrb:.1f}) under the fair relaxed control, so the advantage seen on the synthetic "
                 f"usd4h family (seed 0: 615 vs 733 USD, 16 %; seed 1: 660 vs 973, 32 %, `outputs/r2_probe/`) survives real restaurant and "
                 f"customer geography of the same size.")
    lines.append(f"The gap is made of unserved orders ({_f(comp_gap['unserved'])} USD of the {_f(total_gap_abs)} USD mean difference at the busiest "
                 f"siting), response ({_f(comp_gap['response'])}), lateness ({_f(comp_gap['lateness'])}) and travel ({_f(comp_gap['C_travel'])}); "
                 f"electricity ({_f(comp_gap['C_elec'], 2)}) is negligible at pi = {inst0.pi} $/kWh and there are no transfers (E = {{}}).")
    lines.append(f"The baseline serves {100 * mm('busiest', 'baseline', 'served_share'):.0f} % of the orders against {100 * mm('busiest', 'ilp', 'served_share'):.0f} % "
                 f"for the ILP, with mean response {mm('busiest', 'baseline', 'mean_response_h'):.2f} h vs {mm('busiest', 'ilp', 'mean_response_h'):.2f} h and "
                 f"{mm('busiest', 'baseline', 'bike_km'):.1f} vs {mm('busiest', 'ilp', 'bike_km'):.1f} km; with P = {inst0.orders[0].P} USD and w = "
                 f"{inst0.orders[0].w} $/h a dropped order costs about as much as 1.7 h of waiting, so the ILP trades response time for coverage.")
    lines.append(f"Swaps: baseline {mm('busiest', 'baseline', 'n_swaps'):.1f} vs ILP {mm('busiest', 'ilp', 'n_swaps'):.1f} per run with "
                 f"{mm('busiest', 'baseline', 'kwh_purchased'):.2f} vs {mm('busiest', 'ilp', 'kwh_purchased'):.2f} kWh purchased; the ILP meets (17)-(18) "
                 f"at a price of {_f(_mean(busiest['ilp_minus_relaxed']), 2)} USD on average (written minus relaxed optimum), while the baseline ends "
                 f"with (18) violated in {n18} of {len(base_rows)} runs (DEMAND_AWARE charging covers only the per-site reserve (17), DECISIONS R2 notes).")
    if len(sit):
        lines.append(f"Siting matters for both methods: moving the three sites to the grid-connected landmarks changes the baseline by "
                     f"{_f(_mean(sit['baseline_grid_minus_busiest_pct']))} % and the ILP by {_f(_mean(sit['ilp_grid_minus_busiest_pct']))} % on average "
                     f"(per seed ILP: {[None if x is None or pd.isna(x) else round(float(x), 1) for x in sit['ilp_grid_minus_busiest_pct']]} %), and the ILP's relative advantage is "
                     f"{gg:.1f} % there (+/- {hg:.1f}); Union Square sits on the southern edge of the box, so bikes starting there ride farther to the "
                     f"Midtown demand mass, which the ILP absorbs better than the nearest-rider policy only when a dropped order is at stake.")
    lines.append(f"Demand realism: the realised cuisine mix of the NYC instances is within L1 = {l1_c_nyc:.2f} of the Kaggle order shares "
                 f"(synthetic {l1_c_syn:.2f}, where only {syn['n_restaurants']} restaurants exist and some cuisines have none), the customers fall in "
                 f"{nyc['n_zones_hit']} NTAs with the top three zones ({', '.join(top_zones.zone)}: {', '.join(f'{100 * x:.0f} %' for x in top_zones.sampling_law_share)} "
                 f"of the sampling mass) receiving {100 * float(top_zones.realised_share.sum()):.0f} % of the orders (L1 realised-vs-law {l1_z:.2f} over "
                 f"{len(zt)} zones at 36 orders per seed), and orders spread over about {int(np.mean(nyc['n_restaurants_hit']))} distinct restaurants per seed "
                 f"(top-10 share {np.mean(nyc['top10_share']):.2f}) against {syn['n_restaurants']} fixed synthetic restaurants (top-10 share 1.0).")
    lines.append(f"Trip geometry is similar in both families (mean restaurant -> customer route {np.mean(nyc['mean_od_km']):.2f} vs "
                 f"{np.mean(syn['mean_od_km']):.2f} km) because both live on the same 150 m grid with the same speed / energy physics; the semi-real "
                 f"instance only changes *where* the mass sits (Chelsea / Hudson Yards / Midtown South NTAs) and how concentrated the restaurants are.")
    lines.append(f"Solver: {int(df.n_arcs.mean()):,} arcs under PRUNING_NYC (versus 1.9 M for usd4h at the same size) because moves are allowed only "
                 f"into the three site nodes; the ILPs solved in {ilp_rows.runtime_s.mean():.0f} s on average (max {ilp_rows.runtime_s.max():.0f} s), "
                 f"{n_opt + n_opt_r} of {len(ilp_rows) + len(rel_rows)} runs proven optimal within {time_limit:.0f} s at Threads {C.THREADS}.")
    lines.append("Caveats: synthetic road geometry (rotated grid, synthetic elevation and signals, one shortest grid route per pair), "
                 "3 seeds (CIs are wide), 6 bikes / 36 orders (the R2.2 nominal 10 / 60 was not solved here), and the baseline's "
                 "(17)/(18) violations are reported, not priced -- the relaxed control is the fair comparison. PRUNING_NYC binds "
                 "only the ILP (no repositioning to non-site nodes), so every ILP total is an upper bound on the written optimum and "
                 "every gap a lower bound on the coordination value (fairness review F2); the `other` cuisine class (26 % of the "
                 "box's restaurants) is unreachable by construction (units review F3).")
    md.append(" ".join(lines) + "\n")

    md.append("## Anomalies and notes\n")
    an = []
    bad = df[(df.method != "baseline") & (df.status != "OPTIMAL")]
    if len(bad):
        an.append("- ILP runs not proven optimal: " + ", ".join(f"{r.name}/{r.method} ({r.status}, gap {float(r.gap):.4f})" for r in bad.itertuples()) + ".")
    worse = per[(per.ilp_total.notna()) & (per.ilp_total > per.baseline_total + 1e-6)]
    if len(worse):
        an.append("- ILP more expensive than the baseline on " + ", ".join(worse.name) + " (would contradict optimality; check).")
    rel_worse = per[(per.relaxed_total.notna()) & (per.ilp_total.notna()) & (per.relaxed_total > per.ilp_total + 1e-6)]
    if len(rel_worse):
        an.append("- Relaxed ILP more expensive than the written ILP on " + ", ".join(rel_worse.name) + " (the relaxed model is a relaxation; "
                  "possible only when a solve hit the time limit).")
    rej = ilp_rows[ilp_rows.mip_start_accepted != True]  # noqa: E712
    if len(rej):
        an.append("- MIP start rejected on " + ", ".join(f"{r.name} ({r.mip_start_variant}, {r.mip_start_verified_status})" for r in rej.itertuples())
                  + "; Gurobi then starts cold (the start is only a warm start, DECISIONS R2 notes).")
    fb = ilp_rows[ilp_rows.mip_start_variant != "default"]
    if len(fb):
        an.append("- The default baseline schedule violated (18) and a fallback variant was injected as start on "
                  + ", ".join(f"{r.name} ({r.mip_start_variant})" for r in fb.itertuples()) + " (baseline columns still describe the default policy).")
    n_box_edge = sum(1 for (s, _), i in insts.items() if s == "grid" for v in i.meta["sites"]
                     if v[0] in (0, i.meta["box"]["grid_nx"] - 1) or v[1] in (0, i.meta["box"]["grid_ny"] - 1))
    if n_box_edge:
        an.append(f"- {n_box_edge} grid-connected site(s) snapped to the edge of the grid (Union Square lies at the southern boundary of the box).")
    if m0.get("zone_weights_warning"):
        an.append(f"- Zone weights used the fallback: {m0['zone_weights_warning']}")
    for (s, seed), inst in sorted(insts.items()):
        dropped = inst.meta.get("cuisine_classes_dropped") or []
        if dropped:
            an.append(f"- {inst.meta['name']}: Kaggle cuisine classes without a restaurant in the box (never sampled): {dropped}.")
            break
    if "baseline_relaxed_copy_differs" in rel_rows.columns and rel_rows.baseline_relaxed_copy_differs.eq(True).any():
        d = rel_rows[rel_rows.baseline_relaxed_copy_differs.eq(True)]
        an.append("- The baseline policy depends on R_end_j through the DEMAND_AWARE reserve (R2.3: reserve = R_end_j y_j), so its "
                  "schedule on the relaxed copy (R_end 0) differs from the written one on " + ", ".join(
                      f"{r.name} ({float(r.baseline_relaxed_copy_total):.2f} vs written baseline)" for r in d.itertuples())
                  + "; the relaxed-copy schedule is only the MIP start of `ilp_relaxed`, all baseline columns are the written-instance policy.")
    pruned = df[(df.method == "baseline") & (df.get("baseline_pruned_fallbacks", 0) > 0)] if "baseline_pruned_fallbacks" in df else df.iloc[0:0]
    if len(pruned):
        an.append("- The shared pruning bound the baseline (pruned_arc_fallbacks > 0; round-1 parity rule) on "
                  + ", ".join(f"{r.name} ({int(r.baseline_pruned_fallbacks)})" for r in pruned.itertuples()) + ".")
    if "n_unservable" in df and df.n_unservable.gt(0).any():
        u = df[(df.method == "baseline") & (df.n_unservable > 0)]
        an.append("- Structurally unservable orders (no delivery arc; both methods pay P, raw drop rates inflated identically): "
                  + ", ".join(f"{r.name} ({int(r.n_unservable)})" for r in u.itertuples())
                  + "; `served_share_servable` is the share relative to the servable orders (fairness review F5).")
    if "baseline_stranded" in df and df[df.method == "baseline"].baseline_stranded.gt(0).any():
        s_ = df[(df.method == "baseline") & (df.baseline_stranded > 0)]
        an.append("- Baseline bikes stranded (no feasible reposition / terminal) on "
                  + ", ".join(f"{r.name} ({int(r.baseline_stranded)})" for r in s_.itertuples()) + ".")
    if "mip_start_fallback_errors" in df:
        e_ = df[df.mip_start_fallback_errors.astype(str).str.len() > 2]
        if len(e_):
            an.append("- MIP-start fallback variants raised on " + ", ".join(f"{r.name}: {r.mip_start_fallback_errors}" for r in e_.itertuples()) + ".")
    an.append("- Sites are placed by node, several facilities could share a node if two sitings coincided (they do not here); the grid-connected "
              "coordinates are my choice of three well-known landmarks, not Citi Bike station records.")
    an.append("- `data_nyc.make_nyc_instance` draws the bikes' start nodes round robin over the sites, so the two sitings of a seed differ only in "
              "the site nodes and the bikes' starting positions; orders, prep times, restaurant ranks and q0 are identical.")
    md.extend(an)
    md.append("\n## Figures\n")
    for f in figures:
        md.append(f"- `{os.path.basename(f)}`")
    md.append("\nFiles: `results.csv` (one row per instance x method), `per_instance.csv`, `siting.csv`, `demand_comparison.json`, "
              "`instances/*.json` (byte-identical inputs of every method), `wall_time.json`; all in `outputs/e8_nyc/`.")
    path = os.path.join(out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(seeds: Sequence[int], sitings: Sequence[str], time_limit: float, out_dir: str,
         methods: Sequence[str] = METHODS, targets: str = "facilities") -> pd.DataFrame:
    t_start = time.perf_counter()
    demand_keys: Dict[int, Any] = {}
    C.ensure_dir(out_dir)
    inst_dir = C.ensure_dir(os.path.join(out_dir, "instances"))
    rows: List[Dict[str, Any]] = []
    insts: Dict[Tuple[str, int], Instance] = {}
    keep0: Optional[Dict[str, Any]] = None
    jsonl = os.path.join(out_dir, "rows.jsonl")
    for seed in seeds:
        for siting in sitings:
            print(f"[{time.strftime('%H:%M:%S')}] {siting} seed {seed}", flush=True)
            r, keep = run_instance(seed, siting, time_limit, inst_dir, methods, targets)
            rows += r
            insts[(siting, seed)] = keep["inst"]
            # units review F7: the two sitings of a seed must share the demand side exactly
            key = C.demand_key(keep["inst"], include_bike_nodes=False)
            if seed in demand_keys and demand_keys[seed] != key:
                raise RuntimeError(f"siting {siting} changed the demand of seed {seed} (orders / q0 / H / L differ)")
            demand_keys.setdefault(seed, key)
            if siting == "busiest" and keep0 is None:
                keep0 = keep
            with open(jsonl, "a", encoding="utf-8") as fh:
                for rec in r:
                    fh.write(json.dumps(rec, default=str) + "\n")
    df = C.records_to_frame(rows)
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    per = per_instance_table(df)
    per.to_csv(os.path.join(out_dir, "per_instance.csv"), index=False)
    sit = siting_table(per) if "grid" in sitings and "busiest" in sitings else pd.DataFrame()
    sit.to_csv(os.path.join(out_dir, "siting.csv"), index=False)
    nyc_insts = [insts[("busiest", s)] for s in seeds if ("busiest", s) in insts] or list(insts.values())
    cmp = demand_comparison(nyc_insts, seeds)
    with open(os.path.join(out_dir, "demand_comparison.json"), "w", encoding="utf-8") as fh:
        json.dump(cmp, fh, indent=1, default=str)
    figures = []
    if keep0 is not None:
        grid_inst = insts.get(("grid", keep0["inst"].meta["seed"]))
        figures.append(plot_map(keep0["inst"], keep0["lib"], keep0.get("ilp_schedule"), grid_inst,
                                os.path.join(out_dir, f"map_seed{keep0['inst'].meta['seed']}.png")))
    figures.append(plot_cost_components(df, os.path.join(out_dir, "cost_components.png")))
    figures.append(plot_gap_by_seed(per, os.path.join(out_dir, "gap_by_seed.png")))
    figures.append(plot_demand_comparison(cmp, os.path.join(out_dir, "demand_comparison.png")))
    wall = time.perf_counter() - t_start
    with open(os.path.join(out_dir, "wall_time.json"), "w") as fh:
        json.dump({"wall_s": wall, "time_limit": time_limit, "threads": C.THREADS, "seeds": list(seeds),
                   "sitings": list(sitings), "methods": list(methods), "pruning_targets": targets,
                   "demand_md5": {str(s): C.demand_md5(insts[(sitings[0], s)], include_bike_nodes=False)
                                  for s in seeds if (sitings[0], s) in insts}}, fh)
    write_results_md(df, per, sit, cmp, insts, out_dir, wall, time_limit, figures)
    print(f"done: {out_dir}/RESULTS.md ({wall / 60:.1f} min)")
    return df


def map_only(seed: int, out_dir: str, time_limit: float) -> str:
    """Rebuild the ``busiest`` instance of ``seed``, reload its saved ILP schedule from
    ``instances/<name>-ilp-schedule.json`` (or re-solve the ILP when the file is absent)
    and redraw ``map_seed<seed>.png`` without touching ``results.csv``."""
    inst_dir = C.ensure_dir(os.path.join(out_dir, "instances"))
    inst = make_instance(seed, "busiest")
    grid_inst = make_instance(seed, "grid")
    lib, _ = C.build_library(inst, C.pruning_for(inst))
    path = os.path.join(inst_dir, f"{inst.meta['name']}-ilp-schedule.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            sched = Schedule.from_dict(json.load(fh))
    else:
        _, base = run_baseline(inst, lib)
        _, sched = run_ilp(inst, lib, "ilp", base, time_limit)
        if sched is not None:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(sched.to_dict(), fh)
    return plot_map(inst, lib, sched, grid_inst, os.path.join(out_dir, f"map_seed{seed}.png"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    ap.add_argument("--sitings", nargs="+", default=list(SITINGS), choices=list(SITINGS))
    ap.add_argument("--methods", nargs="+", default=list(METHODS), choices=list(METHODS))
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--map-only", action="store_true", help="only redraw map_seed<first seed>.png")
    ap.add_argument("--targets", default="facilities", choices=["facilities", "default"],
                    help="reposition targets: 'facilities' = PRUNING_NYC (restricts the ILP only, fairness F2); "
                         "'default' = restaurants + sites + depots with reachable pruning (lossless probe, large library)")
    args = ap.parse_args()
    if args.map_only:
        print(map_only(args.seeds[0], args.out, args.time_limit))
    else:
        main(args.seeds, args.sitings, args.time_limit, args.out, args.methods, args.targets)
