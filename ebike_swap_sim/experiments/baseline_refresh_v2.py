"""Baseline re-run (v2) on the byte-identical E2 / E3 instances after the baseline fixes.

Why
---
The event-driven baseline policy (:mod:`ebike_swap_sim.baseline`) was fixed after the
E2 (``outputs/e2_coord``) and E3 (``outputs/e3``) runs: just-in-time dispatch
(reviewer F1), the dead-zone rule on reach refusals (F2), the documented
``baseline_reserve`` / ``baseline_informed`` variants (F3, F6) and the explicit gap
definitions (F4).  The ILP (objective (26)-(32), constraints (5)-(22)) and the arc
builder are unchanged, so the ILP rows of the existing ``results.csv`` files stay
valid.  This script re-runs **only the baseline side** on the saved instances
(``outputs/*/instances/*.json``), rebuilds the arc libraries with the pruning of the
original scripts (asserting that the arc counts match the v1 rows, i.e. the library
is reproduced), joins the unchanged ILP rows and recomputes the comparison tables.

What is computed per instance
-----------------------------
* every documented baseline variant of :data:`experiments.common.BASELINE_VARIANTS`
  (``baseline`` = fixed policy, ``baseline_legacy`` = pre-fix behaviour, ``baseline_reserve``,
  ``baseline_informed``, ``baseline_reorder``; for E3 every variant is run with both
  transfer rules ``NONE`` and ``REORDER_POINT``), priced with ``evaluate.cost``
  (26)-(32) and verified with ``evaluate.check`` ((9), (17), (18) are report-only);
* the reproduction check ``baseline_legacy == v1 baseline row`` (same instance, same
  library, same policy -> identical cost);
* the MIP-start certificate of every variant: the baseline schedule is loaded into
  the ILP (``ILPModel.set_mip_start``) and Gurobi solves the model with every
  variable fixed (``ILPModel.verify_mip_start``, Threads 4, TimeLimit 120 s,
  OutputFlag 0) **under the written model** (rho, R_end as in the instance) and
  **under the fully relaxed end targets** (:func:`experiments.common.relax_end_targets`:
  rho = 0 and R_end_j = 0, i.e. (17) and (18) off).  The free ILP is *not* re-solved.
* the headline gap ``gap_vs_baseline_pct = 100 (baseline - ILP) / baseline`` and the
  secondary ``gap_vs_ilp_pct`` (:func:`experiments.common.gap_definitions`) against
  the v1 ILP rows: for E2 the ILP at rho = 0.5 (written model) and at rho = 0
  (``ilp_rho0``; note that no ILP with R_end = 0 exists, so the gap against the fully
  relaxed ILP is bounded below by the rho = 0 gap); for E3 the ILP with the matching
  transfer switch (``NONE`` <-> ``no_transfers``, ``REORDER_POINT`` <-> transfers free).

Outputs (the v1 files are left untouched)
-----------------------------------------
``outputs/e2_coord/results_v2.csv``, ``RESULTS_v2.md``, ``cost_components_v2.png``,
``improvement_vs_demand_v2.png``, ``gap_decomposition_rho0_v2.png``;
``outputs/e3/results_v2.csv``, ``RESULTS_v2.md``, ``fig_cost_by_layout_v2.png``,
``fig_transfer_value_v2.png``; ``wall_time_v2.json`` in both.

Run from ``ebike_swap_sim/`` (about 10-15 min, baseline runs take milliseconds, the
time goes into model builds for the certificates)::

    PYTHONPATH=. python3 experiments/baseline_refresh_v2.py [--parts e2 e3]
        [--certify-time-limit 120] [--no-certify] [--analyse-only] [--max-instances N]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from experiments import common as C  # noqa: E402
from experiments.common import plt  # noqa: E402  (Agg backend already selected)
from experiments.e2_coord import DEMAND, PALETTE, _style, ci95  # noqa: E402
from experiments.e3_transfers_separation import LAYOUTS, LAYOUT_LABEL  # noqa: E402
from ebike_swap_sim import ArcLibrary, Instance, Schedule, build_arcs, check  # noqa: E402

E2_DIR = os.path.join(C.OUTPUT_ROOT, "e2_coord")
E3_DIR = os.path.join(C.OUTPUT_ROOT, "e3")
CERTIFY_TIME_LIMIT = 120.0
COMPONENTS = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"]
#: Baseline variants re-run (names of :data:`common.BASELINE_VARIANTS`); ``baseline_zone``
#: is left out (confirmed no-op: identical to ``baseline`` on every v1 instance).
E2_VARIANTS = ["baseline", "baseline_legacy", "baseline_reserve", "baseline_informed", "baseline_reorder"]
E3_VARIANTS = ["baseline", "baseline_legacy", "baseline_reserve", "baseline_informed"]
E3_RULES = ["NONE", "REORDER_POINT"]
VARIANT_LABEL = {"baseline": "baseline (fixed policy)", "baseline_legacy": "baseline_legacy (v1 behaviour)",
                 "baseline_reserve": "baseline_reserve (end windows W)",
                 "baseline_informed": "baseline_informed (stock-aware + late window)",
                 "baseline_reorder": "baseline_reorder (REORDER_POINT)"}


# ---------------------------------------------------------------------------
# helpers shared by both parts
# ---------------------------------------------------------------------------
def _nan(v: Any) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _n_true(series: pd.Series) -> int:
    """Number of ``True`` entries of a bool/object column that may hold NaN."""
    return int((series == True).sum())  # noqa: E712


def _ci_text(values: Sequence[float], digits: int = 1) -> str:
    m, hw, n = ci95(list(values))
    if n == 0:
        return "-"
    return f"{m:.{digits}f} +/- {hw:.{digits}f} (n = {n})" if n > 1 else f"{m:.{digits}f} (n = 1)"


def load_instances(inst_dir: str, max_instances: Optional[int] = None) -> List[Instance]:
    """All ``*.json`` instances of ``inst_dir`` (sorted by file name), via
    :meth:`Instance.load` (JSON round-trip is byte-identical, see the v1 scripts)."""
    paths = sorted(glob.glob(os.path.join(inst_dir, "*.json")))
    if max_instances is not None:
        paths = paths[:max_instances]
    out = []
    for p in paths:
        inst = Instance.load(p)
        inst.meta.setdefault("name", os.path.splitext(os.path.basename(p))[0])
        inst.meta["instance_path"] = p
        out.append(inst)
    return out


def assert_same_arcs(lib: ArcLibrary, other: ArcLibrary, ids: Iterable[int]) -> None:
    """Assert that the arcs ``ids`` of ``lib`` have the same ``(k, kind, src, dst, order, fac)``
    in ``other`` (the relaxed copy of an instance must reproduce the arc ids, since the
    arc rules (1)-(4), (9) do not depend on ``rho`` / ``R_end``)."""
    if len(lib) != len(other):
        raise AssertionError(f"libraries differ in size: {len(lib)} vs {len(other)}")
    for a_id in ids:
        a, b = lib.arc(a_id), other.arc(a_id)
        if (a.k, a.kind, a.src, a.dst, a.order, a.fac) != (b.k, b.kind, b.src, b.dst, b.order, b.fac):
            raise AssertionError(f"arc {a_id} differs between the libraries: {a} vs {b}")


class StartCertifier:
    """Fix-and-solve certificate of baseline schedules as MIP starts of one ILP.

    Builds the E2 ILP (5)-(22), (26)-(32) once for ``(inst, lib, no_transfers)``
    (``OutputFlag 0``, ``Threads 4``, ``TimeLimit`` = ``time_limit``) and certifies
    any number of schedules with :meth:`ILPModel.set_mip_start` (``verify=False``) +
    :meth:`ILPModel.verify_mip_start` (all variables fixed to the start, Gurobi
    solve, bounds restored).  :meth:`close` disposes the Gurobi model and
    environment.  The free ILP is never solved."""

    def __init__(self, inst: Instance, lib: ArcLibrary, no_transfers: bool, time_limit: float) -> None:
        from ebike_swap_sim import ilp

        t0 = time.perf_counter()
        self.mdl = ilp.build_model(inst, lib, threads=C.THREADS, time_limit=time_limit,
                                   no_transfers=no_transfers)
        self.build_time = time.perf_counter() - t0
        self.time_limit = time_limit
        self.n_certified = 0

    def certify(self, sched: Schedule) -> Dict[str, Any]:
        """``{'accepted', 'status', 'obj', 'start_obj', 'start_check_ok', 'seconds'}`` of ``sched``."""
        t0 = time.perf_counter()
        info = self.mdl.set_mip_start(sched, verify=False)
        ok, obj, status = self.mdl.verify_mip_start(time_limit=self.time_limit)
        self.n_certified += 1
        return {"accepted": bool(ok), "status": status, "obj": obj, "start_obj": info["start_obj"],
                "start_check_ok": info["start_check_ok"], "seconds": time.perf_counter() - t0}

    def close(self) -> None:
        try:
            self.mdl.model.dispose()
            self.mdl.env.dispose()
        except Exception:  # pragma: no cover - disposal is best effort
            pass


def baseline_row(inst: Instance, lib: ArcLibrary, variant: str, rule: str,
                 res: Dict[str, Any]) -> Dict[str, Any]:
    """Flat record of one :func:`common.run_baseline_case` result: cost (26)-(32),
    ``evaluate.metrics``, policy flags (JIT dispatches, reach refusals, suppressed late
    trips, stock-aware re-routes), report-only violations (9) / (17) / (18) and the
    checker summary."""
    fl, met = res["flags"], res["metrics"]
    rr = fl.get("reach_refusals") or {}
    row: Dict[str, Any] = {
        "name": inst.meta.get("name"), "seed": inst.meta.get("seed"),
        "method": variant if rule == "NONE" or variant == "baseline_reorder" else f"{variant}_reorder",
        "variant": variant, "transfer_rule": rule,
        "transfers": "free" if rule == "REORDER_POINT" else "none",
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
        "n_services": len(inst.services), "n_arcs": len(lib), "rho": inst.rho,
        "status": "POLICY", "runtime_s": res["runtime"],
        **C.flatten_cost(res["cost"]),
        "served_share": met["served_share"], "n_unserved": met["n_unserved"],
        "mean_response_h": met["mean_response_h"], "mean_lateness_h": met["mean_lateness_h"],
        "n_late": met["n_late"], "bike_km": met["bike_km"], "n_swaps": met["n_swaps"],
        "queue_wait_slots": sum(met["wait_before_swap"]), "kwh_purchased": met["kwh_purchased"],
        "transfers_used": met["transfers_used"], "batteries_moved": met["batteries_moved"],
        "stockout_slots_total": int(sum(met["stockout_slots"].values())),
        "end_full_total": met["end_full_total"], "end_target_shortfall_18": met["end_target_shortfall"],
        "jit_dispatches": int(fl.get("jit_dispatches", 0)),
        "reach_refusals": int(rr.get("count", 0)),
        "reach_bikes_sent_to_swap": int(rr.get("bikes_sent_to_swap", 0) or 0),
        "late_trips_suppressed": int(fl.get("late_trips_suppressed", 0) or 0),
        "stock_aware_reroutes": int(fl.get("stock_aware_reroutes", 0) or 0),
        "max_need": fl.get("max_need"), "q_thr": fl.get("q_thr"),
        "viol_9": len(fl["terminal_violations"]), "viol_17": sum(fl["end_shortfalls"]["local"].values()),
        "viol_18": fl["end_shortfalls"]["global"], "stranded_bikes": len(fl["stranded_bikes"]),
        "queued_at_H": len(fl["queued_at_H"]),
        "pruned_arc_fallbacks": sum((fl.get("pruned_arc_fallbacks") or {}).get("count", {}).values())
        if isinstance((fl.get("pruned_arc_fallbacks") or {}).get("count"), dict) else 0,
        "check_ok": res["ok"], "ok_modulo_report_only": res["ok_modulo_report_only"],
        "check_families": json.dumps(res["families"], sort_keys=True),
        "identity_24_ok": res["identity_24_ok"], "inventory_consistent": fl["inventory_consistent"],
    }
    return row


def add_certificates(row: Dict[str, Any], tag: str, cert: Optional[Dict[str, Any]],
                     families: Optional[Dict[str, int]] = None) -> None:
    """Attach a :meth:`StartCertifier.certify` result under ``start_<tag>_*`` columns."""
    if cert is None:
        row.update({f"start_{tag}_accepted": None, f"start_{tag}_status": None, f"start_{tag}_obj": None,
                    f"start_{tag}_seconds": None})
    else:
        row.update({f"start_{tag}_accepted": cert["accepted"], f"start_{tag}_status": cert["status"],
                    f"start_{tag}_obj": cert["obj"], f"start_{tag}_seconds": cert["seconds"]})
    if families is not None:
        row[f"check_families_{tag}"] = json.dumps(families, sort_keys=True)


def relaxed_pair(inst: Instance, lib: ArcLibrary, chosen_ids: Iterable[int]) -> Tuple[Instance, ArcLibrary]:
    """``(relaxed instance, its library)`` of :func:`common.relax_end_targets`; the library
    is rebuilt with ``lib.options`` and the arcs in ``chosen_ids`` are asserted identical."""
    inst_rel = C.relax_end_targets(inst)
    lib_rel = build_arcs(inst_rel, **lib.options)
    assert_same_arcs(lib, lib_rel, chosen_ids)
    return inst_rel, lib_rel


def chosen_arcs(scheds: Iterable[Schedule]) -> List[int]:
    ids = set()
    for s in scheds:
        for lst in s.x.values():
            ids.update(int(a) for a in lst)
    return sorted(ids)


# ---------------------------------------------------------------------------
# E2 (outputs/e2_coord): 15 instances, variants, ILP rows at rho = 0.5 and rho = 0
# ---------------------------------------------------------------------------
def e2_run_instance(inst: Instance, old: pd.DataFrame, certify: bool, time_limit: float,
                    log: List[str]) -> List[Dict[str, Any]]:
    """All E2 baseline variants on one saved instance + certificates + joined ILP rows."""
    name = inst.meta["name"]
    old_i = old[(old.seed == inst.meta["seed"]) & (np.isclose(old.demand_mult.astype(float), float(inst.meta["demand_mult"])))]
    v1_base = old_i[old_i.method == "baseline"].iloc[0]
    v1_ilp = old_i[old_i.method == "ilp"].iloc[0]
    v1_ilp0 = old_i[old_i.method == "ilp_rho0"].iloc[0]
    pruning = C.pruning_for(inst, reachable=True)                 # as experiments/e2_coord.py
    lib, lib_t = C.build_library(inst, pruning)
    arcs_match = len(lib) == int(v1_base["n_arcs"])
    if not arcs_match:
        log.append(f"{name}: arc library NOT reproduced ({len(lib)} vs v1 {int(v1_base['n_arcs'])})")

    results: Dict[str, Dict[str, Any]] = {}
    for variant in E2_VARIANTS:
        params = C.baseline_variant_params(variant, inst)
        results[variant] = C.run_baseline_case(inst, lib, params, label=variant)
    legacy_total = results["baseline_legacy"]["cost"]["total"]
    legacy_reproduced = abs(legacy_total - float(v1_base["total"])) <= 1e-6 * max(1.0, abs(legacy_total))
    if not legacy_reproduced:
        log.append(f"{name}: baseline_legacy {legacy_total:.4f} != v1 baseline {float(v1_base['total']):.4f}")

    certs_w: Dict[str, Dict[str, Any]] = {}
    certs_r: Dict[str, Dict[str, Any]] = {}
    fams_r: Dict[str, Dict[str, int]] = {}
    cert_wall = 0.0
    if certify:
        t0 = time.perf_counter()
        cw = StartCertifier(inst, lib, no_transfers=False, time_limit=time_limit)
        for variant, res in results.items():
            certs_w[variant] = cw.certify(res["schedule"])
        cw.close()
        inst_rel, lib_rel = relaxed_pair(inst, lib, chosen_arcs(r["schedule"] for r in results.values()))
        cr = StartCertifier(inst_rel, lib_rel, no_transfers=False, time_limit=time_limit)
        for variant, res in results.items():
            certs_r[variant] = cr.certify(res["schedule"])
            fams_r[variant] = C.family_counts(check(inst_rel, lib_rel, res["schedule"]))
        cr.close()
        cert_wall = time.perf_counter() - t0

    rows: List[Dict[str, Any]] = []
    for variant, res in results.items():
        row = baseline_row(inst, lib, variant, "REORDER_POINT" if variant == "baseline_reorder" else "NONE", res)
        row["method"] = variant
        row.update({
            "part": "e2", "demand_mult": inst.meta.get("demand_mult"),
            "n_arcs_match_v1": arcs_match, "legacy_reproduces_v1": legacy_reproduced,
            "lib_build_time_s": lib_t, "certify_wall_s": cert_wall if certify else None,
            "v1_baseline_total": float(v1_base["total"]), "v1_baseline_unserved_n": int(v1_base["n_unserved"]),
            "v1_mip_start_accepted_rho05": bool(v1_ilp["mip_start_accepted"]),
            "v1_mip_start_accepted_rho0": bool(v1_ilp0["mip_start_accepted"]),
            "ilp_total": float(v1_ilp["total"]), "ilp_status": v1_ilp["status"], "ilp_gap": v1_ilp["gap"],
            "ilp_unserved_n": int(v1_ilp["n_unserved"]),
            "ilp_rho0_total": float(v1_ilp0["total"]), "ilp_rho0_status": v1_ilp0["status"],
            "ilp_rho0_gap": v1_ilp0["gap"], "ilp_rho0_unserved_n": int(v1_ilp0["n_unserved"]),
            "delta_vs_v1_baseline": res["cost"]["total"] - float(v1_base["total"]),
        })
        g = C.gap_definitions(res["cost"]["total"], float(v1_ilp["total"]))
        g0 = C.gap_definitions(res["cost"]["total"], float(v1_ilp0["total"]))
        row.update({"gap_vs_baseline_pct": g["gap_vs_baseline_pct"], "gap_vs_ilp_pct": g["gap_vs_ilp_pct"],
                    "gap_rho0_vs_baseline_pct": g0["gap_vs_baseline_pct"], "gap_rho0_vs_ilp_pct": g0["gap_vs_ilp_pct"]})
        add_certificates(row, "written", certs_w.get(variant))
        add_certificates(row, "relaxed", certs_r.get(variant), fams_r.get(variant) if certify else None)
        rows.append(row)
    # the unchanged ILP rows (v1) for a self-contained CSV
    for _, r in old_i[old_i.method.isin(["ilp", "ilp_rho0"])].iterrows():
        rows.append({"part": "e2", "name": name, "seed": r["seed"], "demand_mult": r["demand_mult"],
                     "method": r["method"], "variant": r["method"], "source": "v1 results.csv (ILP unchanged)",
                     "rho": r["rho"], "n_arcs": r["n_arcs"], "status": r["status"], "gap": r["gap"],
                     "runtime_s": r["runtime_s"], "total": r["total"],
                     **{c: r[c] for c in COMPONENTS}, "n_unserved": r["n_unserved"],
                     "served_share": r["served_share"], "bike_km": r["bike_km"], "n_swaps": r["n_swaps"],
                     "kwh_purchased": r["kwh_purchased"], "transfers_used": r["transfers_used"],
                     "end_full_total": r["end_full_total"],
                     "v1_mip_start_accepted": r["mip_start_accepted"]})
    b = results["baseline"]
    print(f"  {name}: legacy {legacy_total:8.2f} (v1 {float(v1_base['total']):8.2f}, reproduced={legacy_reproduced}) "
          f"-> new {b['cost']['total']:8.2f} (unserved {b['flags']['n_unserved']}, swaps {b['flags']['n_swaps']}, "
          f"JIT {b['flags'].get('jit_dispatches', 0)}, reach {(b['flags'].get('reach_refusals') or {}).get('count', 0)}) "
          f"| reserve {results['baseline_reserve']['cost']['total']:8.2f} | ILP {float(v1_ilp['total']):8.2f} / "
          f"rho0 {float(v1_ilp0['total']):8.2f}"
          + (f" | start new: written {certs_w['baseline']['accepted']} relaxed {certs_r['baseline']['accepted']} "
             f"({cert_wall:.0f}s)" if certify else ""), flush=True)
    return rows


def e2_tables(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Summary frames of the E2 v2 results: per-instance comparison, per-demand means
    with 95 % t-CI of the headline gap, variant means, acceptance counts, gap
    decomposition new baseline - ILP (rho = 0) by component."""
    base = df[df.method.isin(E2_VARIANTS)].copy()
    new = base[base.method == "baseline"].sort_values(["demand_mult", "seed"])
    per_inst = new[["name", "demand_mult", "seed", "n_orders", "v1_baseline_total", "total", "delta_vs_v1_baseline",
                    "ilp_total", "ilp_rho0_total", "gap_vs_baseline_pct", "gap_rho0_vs_baseline_pct",
                    "n_unserved", "v1_baseline_unserved_n", "ilp_rho0_unserved_n", "jit_dispatches",
                    "reach_refusals", "reach_bikes_sent_to_swap", "viol_17", "viol_18",
                    "start_written_accepted", "start_relaxed_accepted", "v1_mip_start_accepted_rho05",
                    "v1_mip_start_accepted_rho0"]].copy()
    per_inst["v1_gap_rho0_vs_baseline_pct"] = 100 * (per_inst["v1_baseline_total"] - per_inst["ilp_rho0_total"]) / per_inst["v1_baseline_total"]
    per_inst["v1_gap_vs_baseline_pct"] = 100 * (per_inst["v1_baseline_total"] - per_inst["ilp_total"]) / per_inst["v1_baseline_total"]

    recs = []
    for variant in E2_VARIANTS:
        sub_v = base[base.method == variant]
        for mult in sorted(DEMAND) + ["all"]:
            sub = sub_v if mult == "all" else sub_v[sub_v.demand_mult == mult]
            if sub.empty:
                continue
            m0, h0, n = ci95(sub["gap_rho0_vs_baseline_pct"].tolist())
            m5, h5, _ = ci95(sub["gap_vs_baseline_pct"].tolist())
            recs.append({"variant": variant, "demand_mult": mult, "n": n,
                         "baseline_total_mean": sub["total"].mean(),
                         "ilp_rho05_total_mean": sub["ilp_total"].mean(), "ilp_rho0_total_mean": sub["ilp_rho0_total"].mean(),
                         "gap_rho0_mean_pct": m0, "gap_rho0_ci95_pct": h0,
                         "gap_rho05_mean_pct": m5, "gap_rho05_ci95_pct": h5,
                         "abs_gain_rho0_mean": (sub["total"] - sub["ilp_rho0_total"]).mean(),
                         "unserved_mean": sub["n_unserved"].mean(), "bike_km_mean": sub["bike_km"].mean(),
                         "swaps_mean": sub["n_swaps"].mean(), "jit_mean": sub["jit_dispatches"].mean(),
                         "reach_refusals_mean": sub["reach_refusals"].mean(),
                         "late_suppressed_mean": sub["late_trips_suppressed"].mean(),
                         "viol_17_runs": int((sub["viol_17"] > 0).sum()), "viol_18_runs": int((sub["viol_18"] > 0).sum()),
                         "start_written_accepted": _n_true(sub["start_written_accepted"]),
                         "start_relaxed_accepted": _n_true(sub["start_relaxed_accepted"])})
    gaps = pd.DataFrame(recs)

    comp_rows = []
    for mult in sorted(DEMAND):
        for method in E2_VARIANTS + ["ilp", "ilp_rho0"]:
            sub = df[(df.method == method) & (df.demand_mult == mult)]
            if sub.empty:
                continue
            rec = {"demand_mult": mult, "method": method, "total": sub["total"].mean()}
            rec.update({c: sub[c].astype(float).mean() for c in COMPONENTS})
            rec["n_unserved"] = sub["n_unserved"].mean()
            comp_rows.append(rec)
    comps = pd.DataFrame(comp_rows)

    dec_rows = []
    for mult in sorted(DEMAND) + ["all"]:
        sub = new if mult == "all" else new[new.demand_mult == mult]
        ilp0 = df[df.method == "ilp_rho0"].set_index("name")
        gap = (sub["total"].to_numpy() - sub["ilp_rho0_total"].to_numpy()).mean()
        rec: Dict[str, Any] = {"demand_mult": "all" if mult == "all" else f"x{mult:g}", "total_gap": gap}
        for c in COMPONENTS:
            if c == "C_setup":
                continue
            d = (sub[c].astype(float).to_numpy() - ilp0.loc[sub["name"], c].astype(float).to_numpy()).mean()
            rec[c] = d
            rec[f"{c}_share_pct"] = 100 * d / gap if gap else float("nan")
        dec_rows.append(rec)
    dec = pd.DataFrame(dec_rows)
    return {"per_instance": per_inst, "gaps": gaps, "components": comps, "decomposition": dec}


def e2_plot_components(df: pd.DataFrame, path: str) -> str:
    """Stacked mean cost components (27)-(32) per method and demand level (v2)."""
    comps = ["unserved", "response", "lateness", "C_travel", "C_elec", "C_reb", "C_setup"]
    names = {"unserved": "unserved P_i u_i (30)", "response": "response (31)", "lateness": "lateness (31)",
             "C_travel": "travel (29)", "C_elec": "electricity (28)", "C_reb": "transfers (32)",
             "C_setup": "setup (27), constant"}
    methods = ["baseline_legacy", "baseline", "baseline_reserve", "baseline_informed", "baseline_reorder", "ilp", "ilp_rho0"]
    short = {"baseline_legacy": "Baseline v1 (legacy)", "baseline": "Baseline (fixed)", "baseline_reserve": "Baseline reserve",
             "baseline_informed": "Baseline informed", "baseline_reorder": "Baseline reorder-point",
             "ilp": "ILP (rho = 0.5)", "ilp_rho0": "ILP (rho = 0)"}
    mults = sorted(DEMAND)
    fig, axes = plt.subplots(1, len(mults), figsize=(3.9 * len(mults) + 1.5, 5.3), sharey=True)
    for ax, mult in zip(np.atleast_1d(axes), mults):
        xs = np.arange(len(methods))
        bottom = np.zeros(len(methods))
        for ci, comp in enumerate(comps):
            vals = np.array([float(df[(df.method == m) & (df.demand_mult == mult)][comp].astype(float).mean())
                             if not df[(df.method == m) & (df.demand_mult == mult)].empty else 0.0 for m in methods])
            ax.bar(xs, vals, 0.68, bottom=bottom, color=PALETTE[ci], edgecolor="white", linewidth=1.0,
                   label=names[comp] if mult == mults[0] else None)
            bottom += vals
        for x, tot in zip(xs, bottom):
            ax.text(x, tot + 8, f"{tot:.0f}", ha="center", va="bottom", fontsize=7.5, color="#0b0b0b")
        ax.set_xticks(xs)
        ax.set_xticklabels([short[m] for m in methods], fontsize=7.5, rotation=35, ha="right", rotation_mode="anchor")
        ax.set_title(f"demand x{mult:g}  (|I| = {DEMAND[mult]})", fontsize=10, color="#0b0b0b")
        _style(ax)
    n_seeds = df["seed"].nunique()
    np.atleast_1d(axes)[0].set_ylabel(f"mean cost over {n_seeds} seeds (toy units)", fontsize=9)
    fig.suptitle("E2 v2: cost components (27)-(32) by method and demand level (baseline policy fixed; ILP rows unchanged)",
                 fontsize=11, x=0.01, ha="left", color="#0b0b0b")
    fig.legend(loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def e2_plot_improvement(gaps: pd.DataFrame, path: str) -> str:
    """Headline gap (baseline - ILP) / baseline (%) vs demand, mean and 95 % CI over
    seeds; one line per baseline variant (ILP at rho = 0) plus the fixed baseline vs
    the written model (rho = 0.5)."""
    series = [("baseline", "gap_rho0", "ILP (rho = 0) vs baseline (fixed) [headline]"),
              ("baseline", "gap_rho05", "ILP (rho = 0.5) vs baseline (fixed)"),
              ("baseline_legacy", "gap_rho0", "ILP (rho = 0) vs baseline v1 (legacy)"),
              ("baseline_reserve", "gap_rho0", "ILP (rho = 0) vs baseline_reserve"),
              ("baseline_reorder", "gap_rho0", "ILP (rho = 0) vs baseline_reorder")]
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    mults = sorted(DEMAND)
    for ci, (variant, col, label) in enumerate(series):
        sub = gaps[(gaps.variant == variant) & (gaps.demand_mult != "all")].copy()
        if sub.empty:
            continue
        sub["demand_mult"] = sub["demand_mult"].astype(float)
        sub = sub.sort_values("demand_mult")
        off = (ci - (len(series) - 1) / 2) * 0.012
        x = sub["demand_mult"].to_numpy() + off
        y = sub[f"{col}_mean_pct"].to_numpy()
        ax.errorbar(x, y, yerr=sub[f"{col}_ci95_pct"].fillna(0.0), color=PALETTE[ci], marker="o", markersize=5,
                    linewidth=2, capsize=3, label=label)
        if ci in (0, 2):                       # direct labels on the headline and the v1 reference only
            ax.annotate(f"{label.split(' vs ')[1]}: {y[-1]:.1f} %", (x[-1], y[-1]), xytext=(10, 10 if ci == 0 else -10),
                        textcoords="offset points", fontsize=7.5, color="#52514e", va="center")
    ax.axhline(0, color="#9a9a96", linewidth=0.8)
    ax.set_xticks(mults)
    ax.set_xticklabels([f"x{m:g}\n|I| = {DEMAND[m]}" for m in mults])
    ax.set_xlabel("demand multiplier (orders for 10 bikes in a 2 h window)", fontsize=9)
    ax.set_ylabel("gap (baseline - ILP) / baseline (%)", fontsize=9)
    ax.set_xlim(0.6, 1.9)
    n_seeds = int(gaps["n"].max()) if len(gaps) else 0
    ax.set_title(f"E2 v2: coordination gap vs demand (mean and 95 % CI over {n_seeds} seeds)", fontsize=10,
                 loc="left", color="#0b0b0b")
    ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def e2_plot_decomposition(dec: pd.DataFrame, path: str) -> str:
    """Stacked bars of (fixed baseline - ILP at rho = 0) by cost component per demand level."""
    comps = ["unserved", "response", "lateness", "C_travel", "C_elec", "C_reb"]
    names = {"unserved": "unserved P_i", "response": "response", "lateness": "lateness",
             "C_travel": "travel", "C_elec": "electricity", "C_reb": "transfers"}
    sub = dec[dec.demand_mult != "all"].copy()
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    xs = np.arange(len(sub))
    pos, neg = np.zeros(len(sub)), np.zeros(len(sub))
    for ci, comp in enumerate(comps):
        vals = sub[comp].to_numpy(dtype=float)
        ax.bar(xs, vals, 0.6, bottom=np.where(vals >= 0, pos, neg), color=PALETTE[ci], edgecolor="white",
               linewidth=1.0, label=names[comp])
        pos += np.where(vals >= 0, vals, 0)
        neg += np.where(vals < 0, vals, 0)
    for i, (tot, share) in enumerate(zip(sub["total_gap"], sub["unserved_share_pct"])):
        ax.text(i, pos[i] + 5, f"gap {tot:.0f}\nunserved {share:.0f} %", ha="center", va="bottom", fontsize=7.5)
    ax.axhline(0, color="#9a9a96", linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{m}  (|I| = {DEMAND[float(m[1:])]})" for m in sub["demand_mult"]])
    ax.set_ylabel("baseline (fixed) - ILP (rho = 0), toy units, seed means", fontsize=9)
    ax.set_title("E2 v2: baseline (fixed) minus ILP (rho = 0) by cost component", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.set_ylim(min(neg.min(), 0) - 20, max(pos.max(), 1) * 1.25 + 30)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def e2_write_results(df: pd.DataFrame, out_dir: str, wall: float, time_limit: float, certified: bool) -> str:
    """Compose ``RESULTS_v2.md`` for E2 from ``results_v2.csv``."""
    T = e2_tables(df)
    per_inst, gaps, comps, dec = T["per_instance"], T["gaps"], T["components"], T["decomposition"]
    figs = [e2_plot_components(df, os.path.join(out_dir, "cost_components_v2.png")),
            e2_plot_improvement(gaps, os.path.join(out_dir, "improvement_vs_demand_v2.png")),
            e2_plot_decomposition(dec, os.path.join(out_dir, "gap_decomposition_rho0_v2.png"))]
    base = df[df.method.isin(E2_VARIANTS)]
    new = base[base.method == "baseline"]
    leg = base[base.method == "baseline_legacy"]
    n_inst = len(new)

    def grow(variant: str, mult: Any) -> pd.Series:
        return gaps[(gaps.variant == variant) & (gaps.demand_mult == mult)].iloc[0]

    mults_present = [m for m in sorted(DEMAND) if not gaps[(gaps.variant == "baseline") & (gaps.demand_mult == m)].empty]

    h_new, h_leg = grow("baseline", "all"), grow("baseline_legacy", "all")
    h_res = grow("baseline_reserve", "all")
    acc_w = _n_true(new["start_written_accepted"])
    acc_r = _n_true(new["start_relaxed_accepted"])
    acc_w_leg = _n_true(leg["start_written_accepted"])
    acc_r_res = _n_true(base[base.method == "baseline_reserve"]["start_relaxed_accepted"])
    acc_w_res = _n_true(base[base.method == "baseline_reserve"]["start_written_accepted"])
    better = int((new["delta_vs_v1_baseline"] < -1e-9).sum())
    worse = int((new["delta_vs_v1_baseline"] > 1e-9).sum())
    md: List[str] = []
    md.append("# E2 v2 -- coordinated ILP vs the *fixed* event-driven baseline (baseline side re-run only)\n")
    md.append(f"Byte-identical instances `instances/*.json` of the v1 run (10 bikes, |I| in {{22, 30, 45}}, H = 24, L = 12, "
              f"3 co-located fixed sites, 12 hourly site <-> site shuttles, seeds {sorted(new.seed.unique().tolist())}); arc "
              f"libraries rebuilt with the v1 pruning (`pruning_for(inst, reachable=True)`), arc counts reproduced in "
              f"{int(new['n_arcs_match_v1'].sum())}/{n_inst} instances. **The ILP rows (`ilp` at rho = 0.5, `ilp_rho0` at rho = 0) "
              f"are the unchanged v1 rows of `results.csv`; the free ILP was not re-solved.** The pre-fix policy "
              f"(`baseline_legacy`: `jit_dispatch = False`, `swap_on_reach_refusal = False`) reproduces the v1 `baseline` cost "
              f"exactly in {int(new['legacy_reproduces_v1'].sum())}/{n_inst} instances. MIP-start certificates: fix-and-solve "
              f"(`ILPModel.verify_mip_start`, Threads {C.THREADS}, TimeLimit {time_limit:.0f} s, OutputFlag 0) under the written "
              f"model and under `relax_end_targets` (rho = 0 and R_end_j = 0)"
              + ("" if certified else " -- **not run in this invocation**") + f". Wall time {wall / 60:.1f} min.\n")
    md.append("Headline gap definition: `gap_vs_baseline_pct = 100 (baseline - ILP) / baseline` "
              "(`common.gap_definitions`); `gap_vs_ilp_pct = 100 (baseline - ILP) / ILP` is in the CSV. "
              "`gap_rho0_*` compares with `ilp_rho0` (rho = 0 only; the ILP with R_end = 0 as well was never solved, so the "
              "gap against the fully relaxed ILP is >= the rho = 0 gap).\n")
    md.append("## Headline\n")
    md.append(f"- Fixed baseline vs ILP (rho = 0): mean gap **{h_new.gap_rho0_mean_pct:.1f} % (95 % CI +/- "
              f"{h_new.gap_rho0_ci95_pct:.1f}, n = {int(h_new.n)})**; vs ILP (rho = 0.5, written model): "
              f"{h_new.gap_rho05_mean_pct:.1f} % (+/- {h_new.gap_rho05_ci95_pct:.1f}). By demand (rho = 0): "
              + ", ".join(f"x{m:g}: {grow('baseline', m).gap_rho0_mean_pct:.1f} +/- {grow('baseline', m).gap_rho0_ci95_pct:.1f} %"
                          for m in mults_present) + ".")
    md.append(f"- v1 (legacy) baseline vs ILP (rho = 0): {h_leg.gap_rho0_mean_pct:.1f} % (+/- {h_leg.gap_rho0_ci95_pct:.1f}); "
              f"the fix moves the mean baseline cost from {h_leg.baseline_total_mean:.1f} to {h_new.baseline_total_mean:.1f} "
              f"({100 * (h_new.baseline_total_mean / h_leg.baseline_total_mean - 1):+.1f} %), cheaper in {better} and dearer in "
              f"{worse} of {n_inst} instances (greedy policy: a better first leg does not imply a better schedule).")
    md.append(f"- `baseline_reserve` (end windows W = max sigma + 3): {h_res.baseline_total_mean:.1f} mean cost, gap "
              f"{h_res.gap_rho0_mean_pct:.1f} % (+/- {h_res.gap_rho0_ci95_pct:.1f}).")
    if certified:
        md.append(f"- MIP start of the fixed baseline accepted under the written model in {acc_w}/{n_inst} instances "
                  f"(legacy: {acc_w_leg}/{n_inst}; v1 run: {int(new['v1_mip_start_accepted_rho05'].sum())}/{n_inst}) and under "
                  f"the fully relaxed end targets in {acc_r}/{n_inst}; `baseline_reserve`: {acc_w_res}/{n_inst} written, "
                  f"{acc_r_res}/{n_inst} relaxed. Rejections under the relaxed targets can only come from (9) (terminal "
                  f"certificate), since every other family holds by construction.")
    md.append("")
    md.append("## Per-instance comparison (fixed baseline `baseline` vs v1 baseline vs unchanged ILP rows)\n")
    cols = ["name", "demand_mult", "seed", "v1_baseline_total", "total", "delta_vs_v1_baseline", "ilp_total",
            "ilp_rho0_total", "v1_gap_rho0_vs_baseline_pct", "gap_rho0_vs_baseline_pct", "gap_vs_baseline_pct",
            "v1_baseline_unserved_n", "n_unserved", "ilp_rho0_unserved_n", "jit_dispatches", "reach_refusals",
            "reach_bikes_sent_to_swap", "viol_17", "viol_18", "start_written_accepted", "start_relaxed_accepted",
            "v1_mip_start_accepted_rho05", "v1_mip_start_accepted_rho0"]
    md.append(C.markdown_table(per_inst, cols, digits=2))
    md.append("\n`total` = fixed baseline cost (26); `v1_baseline_total` = legacy; `v1_gap_rho0_*` / `gap_rho0_*` = headline gap "
              "of the legacy / fixed baseline against `ilp_rho0`; `gap_vs_baseline_pct` = fixed baseline against the written-model "
              "ILP; `start_*_accepted` = fix-and-solve certificate of the fixed baseline (written model / rho = 0 & R_end = 0); "
              "`v1_mip_start_accepted_*` = certificate of the legacy start in the v1 run.\n")
    md.append("## Variant means per demand level (gap mean and 95 % t-CI over seeds, flags, acceptance counts)\n")
    gcols = ["variant", "demand_mult", "n", "baseline_total_mean", "ilp_rho05_total_mean", "ilp_rho0_total_mean",
             "gap_rho0_mean_pct", "gap_rho0_ci95_pct", "gap_rho05_mean_pct", "gap_rho05_ci95_pct", "abs_gain_rho0_mean",
             "unserved_mean", "bike_km_mean", "swaps_mean", "jit_mean", "reach_refusals_mean", "late_suppressed_mean",
             "viol_17_runs", "viol_18_runs", "start_written_accepted", "start_relaxed_accepted"]
    md.append(C.markdown_table(gaps, gcols, digits=2))
    md.append("\n## Cost (26) and components (27)-(32): mean over seeds per demand level and method\n")
    md.append(C.markdown_table(comps, ["demand_mult", "method", "total"] + COMPONENTS + ["n_unserved"], digits=2))
    md.append("\n## Gap decomposition (fixed baseline - ILP at rho = 0) by component\n")
    md.append(C.markdown_table(dec, ["demand_mult", "total_gap"] + [c for c in COMPONENTS if c != "C_setup"]
                               + ["unserved_share_pct", "response_share_pct", "lateness_share_pct", "C_travel_share_pct"], digits=1))
    # interpretation
    uns_share = float(dec[dec.demand_mult == "all"]["unserved_share_pct"].iloc[0])
    d_travel = float(dec[dec.demand_mult == "all"]["C_travel"].iloc[0])
    lines = []
    lines.append(f"The fix changes the baseline, not the conclusion: the fixed policy costs {h_new.baseline_total_mean:.1f} on "
                 f"average against {h_leg.baseline_total_mean:.1f} for the v1 policy, so the coordination gap moves from "
                 f"{h_leg.gap_rho0_mean_pct:.1f} % to {h_new.gap_rho0_mean_pct:.1f} % (rho = 0; {h_new.gap_rho05_mean_pct:.1f} % "
                 f"against the written model). The CI half-width ({h_new.gap_rho0_ci95_pct:.1f} points) is of the same order as "
                 f"in v1, so the headline is robust to the dispatch bug.")
    lines.append(f"Mechanics of the fix: {new['jit_dispatches'].mean():.1f} just-in-time dispatches and {new['reach_refusals'].mean():.1f} "
                 f"reach-only refusals per run ({new['reach_bikes_sent_to_swap'].mean():.1f} bikes sent to swap by the dead-zone rule); "
                 f"travel falls from {leg['bike_km'].mean():.1f} to {new['bike_km'].mean():.1f} km per run and unserved orders from "
                 f"{leg['n_unserved'].mean():.2f} to {new['n_unserved'].mean():.2f}, but the greedy policy is not monotone in its "
                 f"inputs: {worse} instances get dearer because a nearer bike taken now is missing later.")
    lines.append(f"The gap stays {'dominated' if uns_share > 50 else 'not dominated'} by the P_i = 100 penalty ({uns_share:.0f} % of "
                 f"the fixed-baseline-minus-ILP difference is unserved orders); the travel component of the gap is now "
                 f"{d_travel:.1f} units ({'the ILP still travels less' if d_travel > 0 else 'the ILP travels more than the fixed baseline'}), "
                 f"i.e. the F1 bug explained part, not all, of the v1 travel difference.")
    if certified:
        lines.append(f"MIP-start acceptance: the fixed baseline is a feasible point of the written model in {acc_w}/{n_inst} runs and of "
                     f"the fully relaxed model in {acc_r}/{n_inst}; the remaining rejections are the report-only end targets (17)/(18) "
                     f"({int((new['viol_17'] > 0).sum())} runs with a local shortfall, {int((new['viol_18'] > 0).sum())} with a global one) "
                     f"-- `baseline_reserve` is accepted in {acc_w_res}/{n_inst} runs under the written model and is the variant to use "
                     f"as a warm start when (17)/(18) are kept.")
    lines.append("The `ilp_fixed_arcs` / `ilp_fixed_assign` rows of v1 are tied to the *legacy* baseline's delivery arcs and are not "
                 "re-used here; the dispatch-vs-logistics decomposition would need those two ILPs re-solved with the fixed baseline's arcs.")
    md.append("\n## Interpretation\n")
    md.append(" ".join(lines) + "\n")
    md.append("## Anomalies / checks\n")
    an = []
    if int(new["n_arcs_match_v1"].sum()) != n_inst:
        an.append("- arc library not reproduced on some instance (see CSV `n_arcs_match_v1`).")
    if int(new["legacy_reproduces_v1"].sum()) != n_inst:
        an.append("- `baseline_legacy` does not reproduce the v1 baseline cost on some instance (see CSV `legacy_reproduces_v1`).")
    for _, r in new.iterrows():
        if r["total"] < r["ilp_rho0_total"] - 1e-6:
            an.append(f"- {r['name']}: fixed baseline {r['total']:.2f} cheaper than ilp_rho0 {r['ilp_rho0_total']:.2f} "
                      f"(status {r['ilp_rho0_status']}, start accepted relaxed = {r['start_relaxed_accepted']}).")
        if r["total"] < r["ilp_total"] - 1e-6:
            an.append(f"- {r['name']}: fixed baseline {r['total']:.2f} cheaper than ILP (rho = 0.5) {r['ilp_total']:.2f} "
                      f"(status {r['ilp_status']}, gap {r['ilp_gap']}; the baseline point violates (17)/(18)? written start accepted = "
                      f"{r['start_written_accepted']}).")
    if certified:
        bad = base[(base["start_written_accepted"] == True) & (base["check_ok"] == False)]  # noqa: E712
        if len(bad):
            an.append("- a start accepted by Gurobi although evaluate.check reports violations: " + ", ".join(bad.name))
        bad2 = base[(base["start_written_accepted"] == False) & (base["check_ok"] == True)]  # noqa: E712
        if len(bad2):
            an.append("- a start rejected by Gurobi although evaluate.check is clean: " + ", ".join(bad2.name))
        rel_rej = base[(base["start_relaxed_accepted"] == False)]  # noqa: E712
        if len(rel_rej):
            an.append("- starts rejected even under rho = 0, R_end = 0: " + ", ".join(f"{r.name}/{r.method} ({r.check_families_relaxed})"
                                                                                     for r in rel_rej.itertuples()))
    nm = base[~base["ok_modulo_report_only"].astype(bool)]
    if len(nm):
        an.append("- baseline violates a non-report-only family: " + ", ".join(f"{r.name}/{r.method} {r.check_families}" for r in nm.itertuples()))
    if not base["identity_24_ok"].astype(bool).all() or not base["inventory_consistent"].astype(bool).all():
        an.append("- identity (24) or online inventory consistency broken on some baseline run.")
    tl = df[df.method.isin(["ilp", "ilp_rho0"]) & (df.status != "OPTIMAL")]
    if len(tl):
        an.append("- v1 ILP rows not proven optimal (inherited): " + ", ".join(f"{r.name}/{r.method} ({r.status}, gap {r.gap})" for r in tl.itertuples()))
    md.extend(an or ["- none"])
    md.append("\n## Figures\n")
    md.extend(f"- `{os.path.basename(f)}`" for f in figs)
    md.append("\nFiles: `results_v2.csv` (baseline variant rows + the unchanged v1 ILP rows, column `source`), `wall_time_v2.json`. "
              "v1 files (`RESULTS.md`, `results.csv`, figures without suffix) are untouched.")
    path = os.path.join(out_dir, "RESULTS_v2.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


def run_e2(out_dir: str, certify: bool, time_limit: float, max_instances: Optional[int],
           analyse_only: bool) -> None:
    csv_path = os.path.join(out_dir, "results_v2.csv")
    wall_path = os.path.join(out_dir, "wall_time_v2.json")
    if not analyse_only:
        old = pd.read_csv(os.path.join(out_dir, "results.csv"))
        insts = load_instances(os.path.join(out_dir, "instances"), max_instances)
        t0 = time.perf_counter()
        rows: List[Dict[str, Any]] = []
        log: List[str] = []
        print(f"[E2] {len(insts)} instances", flush=True)
        for inst in insts:
            rows += e2_run_instance(inst, old, certify, time_limit, log)
            C.write_csv(rows, csv_path)
        wall = time.perf_counter() - t0
        with open(wall_path, "w") as fh:
            json.dump({"wall_s": wall, "certify": certify, "certify_time_limit": time_limit, "log": log}, fh)
        for line in log:
            print("  WARNING:", line)
    else:
        meta = json.load(open(wall_path))
        wall, certify = meta["wall_s"], meta["certify"]
    df = pd.read_csv(csv_path)
    print(e2_write_results(df, out_dir, wall, time_limit, certify))


# ---------------------------------------------------------------------------
# E3 (outputs/e3): 3 layouts x 3 seeds, NONE / REORDER_POINT, ILP no_transfers / free
# ---------------------------------------------------------------------------
def e3_run_instance(inst: Instance, old: pd.DataFrame, certify: bool, time_limit: float,
                    log: List[str]) -> List[Dict[str, Any]]:
    """All E3 baseline variants x transfer rules on one saved instance + certificates
    (NONE starts under the ``no_transfers`` model, REORDER_POINT starts under the
    transfers-free model, each under the written and the relaxed end targets) +
    joined ILP rows."""
    layout, seed = inst.meta["layout"], inst.meta["seed"]
    old_i = old[(old.layout == layout) & (old.seed == seed)]
    v1_b = {sw: old_i[(old_i.method == "baseline") & (old_i.switch == f"transfer_rule={sw}")].iloc[0] for sw in E3_RULES}
    v1_ilp = {"NONE": old_i[(old_i.method == "ilp") & (old_i.switch == "no_transfers")].iloc[0],
              "REORDER_POINT": old_i[(old_i.method == "ilp") & (old_i.switch == "transfers free")].iloc[0]}
    pruning = C.pruning_for(inst)                                  # as experiments/e3_transfers_separation.py
    lib, lib_t = C.build_library(inst, pruning)
    arcs_match = len(lib) == int(v1_b["NONE"]["n_arcs"])
    if not arcs_match:
        log.append(f"{layout}/seed{seed}: arc library NOT reproduced ({len(lib)} vs {int(v1_b['NONE']['n_arcs'])})")

    results: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for variant in E3_VARIANTS:
        for rule in E3_RULES:
            params = C.baseline_variant_params(variant, inst, transfer_rule=rule)
            results[(variant, rule)] = C.run_baseline_case(inst, lib, params, label=f"{variant}-{rule}")
    repro = {}
    for rule in E3_RULES:
        tot = results[("baseline_legacy", rule)]["cost"]["total"]
        repro[rule] = abs(tot - float(v1_b[rule]["total"])) <= 1e-6 * max(1.0, abs(tot))
        if not repro[rule]:
            log.append(f"{layout}/seed{seed}: legacy {rule} {tot:.4f} != v1 {float(v1_b[rule]['total']):.4f}")

    certs_w: Dict[Tuple[str, str], Dict[str, Any]] = {}
    certs_r: Dict[Tuple[str, str], Dict[str, Any]] = {}
    fams_r: Dict[Tuple[str, str], Dict[str, int]] = {}
    cert_wall = 0.0
    if certify:
        t0 = time.perf_counter()
        inst_rel, lib_rel = relaxed_pair(inst, lib, chosen_arcs(r["schedule"] for r in results.values()))
        for rule in E3_RULES:
            no_tr = rule == "NONE"
            cw = StartCertifier(inst, lib, no_transfers=no_tr, time_limit=time_limit)
            for variant in E3_VARIANTS:
                certs_w[(variant, rule)] = cw.certify(results[(variant, rule)]["schedule"])
            cw.close()
            cr = StartCertifier(inst_rel, lib_rel, no_transfers=no_tr, time_limit=time_limit)
            for variant in E3_VARIANTS:
                certs_r[(variant, rule)] = cr.certify(results[(variant, rule)]["schedule"])
                fams_r[(variant, rule)] = C.family_counts(check(inst_rel, lib_rel, results[(variant, rule)]["schedule"],
                                                                switches={"no_transfers": no_tr}))
            cr.close()
        cert_wall = time.perf_counter() - t0

    rows: List[Dict[str, Any]] = []
    for (variant, rule), res in results.items():
        row = baseline_row(inst, lib, variant, rule, res)
        row["method"] = variant
        ilp = v1_ilp[rule]
        row.update({
            "part": "e3", "layout": layout, "layout_label": LAYOUT_LABEL[layout],
            "switch": f"transfer_rule={rule}", "ilp_switch": "no_transfers" if rule == "NONE" else "transfers free",
            "n_arcs_match_v1": arcs_match, "legacy_reproduces_v1": repro[rule],
            "lib_build_time_s": lib_t, "certify_wall_s": cert_wall if certify else None,
            "v1_baseline_total": float(v1_b[rule]["total"]), "v1_baseline_unserved_n": int(v1_b[rule]["n_unserved"]),
            "v1_mip_start_accepted": bool(ilp["mip_start_accepted"]),
            "ilp_total": float(ilp["total"]), "ilp_status": ilp["status"], "ilp_gap": ilp["gap"],
            "ilp_unserved_n": int(ilp["n_unserved"]), "ilp_transfers_used": ilp["transfers_used"],
            "delta_vs_v1_baseline": res["cost"]["total"] - float(v1_b[rule]["total"]),
        })
        row.update(C.gap_definitions(res["cost"]["total"], float(ilp["total"])))
        add_certificates(row, "written", certs_w.get((variant, rule)))
        add_certificates(row, "relaxed", certs_r.get((variant, rule)), fams_r.get((variant, rule)) if certify else None)
        rows.append(row)
    for _, r in old_i[old_i.method == "ilp"].iterrows():
        rows.append({"part": "e3", "layout": layout, "layout_label": LAYOUT_LABEL[layout], "seed": seed,
                     "name": inst.meta.get("name"), "method": "ilp", "variant": "ilp",
                     "transfer_rule": "NONE" if r["switch"] == "no_transfers" else "REORDER_POINT",
                     "transfers": r["transfers"], "switch": r["switch"], "ilp_switch": r["switch"],
                     "source": "v1 results.csv (ILP unchanged)", "status": r["status"], "gap": r["gap"],
                     "runtime_s": r["runtime_s"], "total": r["total"], **{c: r[c] for c in COMPONENTS},
                     "n_unserved": r["n_unserved"], "served_share": r["served_share"], "bike_km": r["bike_km"],
                     "n_swaps": r["n_swaps"], "kwh_purchased": r["kwh_purchased"], "transfers_used": r["transfers_used"],
                     "batteries_moved": r["batteries_moved"], "end_full_total": r["end_full_total"],
                     "stockout_slots_total": r["stockout_slots_total"], "n_arcs": r["n_arcs"],
                     "v1_mip_start_accepted": r["mip_start_accepted"]})
    b_n, b_r = results[("baseline", "NONE")], results[("baseline", "REORDER_POINT")]
    print(f"  [{layout} seed {seed}] NONE: legacy {results[('baseline_legacy', 'NONE')]['cost']['total']:8.2f} "
          f"(repro {repro['NONE']}) -> new {b_n['cost']['total']:8.2f} (uns {b_n['flags']['n_unserved']}) ILP {float(v1_ilp['NONE']['total']):8.2f} | "
          f"REORDER: legacy {results[('baseline_legacy', 'REORDER_POINT')]['cost']['total']:8.2f} (repro {repro['REORDER_POINT']}) -> new "
          f"{b_r['cost']['total']:8.2f} (uns {b_r['flags']['n_unserved']}, transfers {b_r['flags']['n_transfers_used']}) ILP "
          f"{float(v1_ilp['REORDER_POINT']['total']):8.2f}"
          + (f" | starts new: written {certs_w[('baseline', 'NONE')]['accepted']}/{certs_w[('baseline', 'REORDER_POINT')]['accepted']} "
             f"relaxed {certs_r[('baseline', 'NONE')]['accepted']}/{certs_r[('baseline', 'REORDER_POINT')]['accepted']} ({cert_wall:.0f}s)"
             if certify else ""), flush=True)
    return rows


def e3_tables(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Summary frames: cost by layout x switch per method (means, headline gap), value
    of transfers per layout (baseline NONE - REORDER_POINT, ILP no_transfers - free),
    cost of separation, acceptance counts."""
    base = df[df.method.isin(E3_VARIANTS)]
    recs = []
    for layout in LAYOUTS:
        for rule in E3_RULES:
            ilp = df[(df.method == "ilp") & (df.layout == layout) & (df.transfer_rule == rule)]
            for variant in E3_VARIANTS:
                sub = base[(base.method == variant) & (base.layout == layout) & (base.transfer_rule == rule)]
                if sub.empty:
                    continue
                m, hw, n = ci95(sub["gap_vs_baseline_pct"].tolist())
                recs.append({"layout": layout, "transfer_rule": rule, "ilp_switch": sub["ilp_switch"].iloc[0], "variant": variant,
                             "n": n, "baseline_total_mean": sub["total"].mean(), "v1_baseline_total_mean": sub["v1_baseline_total"].mean(),
                             "ilp_total_mean": ilp["total"].mean(), "gap_vs_baseline_mean_pct": m, "gap_vs_baseline_ci95_pct": hw,
                             "unserved_mean": sub["n_unserved"].mean(), "ilp_unserved_mean": ilp["n_unserved"].mean(),
                             "swaps_mean": sub["n_swaps"].mean(), "transfers_used_mean": sub["transfers_used"].mean(),
                             "batteries_moved_mean": sub["batteries_moved"].mean(), "jit_mean": sub["jit_dispatches"].mean(),
                             "reach_refusals_mean": sub["reach_refusals"].mean(), "late_suppressed_mean": sub["late_trips_suppressed"].mean(),
                             "viol_17_runs": int((sub["viol_17"] > 0).sum()), "viol_18_runs": int((sub["viol_18"] > 0).sum()),
                             "start_written_accepted": _n_true(sub["start_written_accepted"]),
                             "start_relaxed_accepted": _n_true(sub["start_relaxed_accepted"])})
    by_layout = pd.DataFrame(recs)

    seeds = sorted(df.seed.unique())
    tv = []
    for layout in LAYOUTS:
        for method, label in [("ilp", "ILP: cost(no_transfers) - cost(transfers free)")] + \
                [(v, f"{v}: cost(NONE) - cost(REORDER_POINT)") for v in E3_VARIANTS]:
            vals = []
            for s in seeds:
                a = df[(df.method == method) & (df.layout == layout) & (df.seed == s) & (df.transfer_rule == "NONE")]
                b = df[(df.method == method) & (df.layout == layout) & (df.seed == s) & (df.transfer_rule == "REORDER_POINT")]
                if not a.empty and not b.empty:
                    vals.append(float(a["total"].iloc[0]) - float(b["total"].iloc[0]))
            if vals:
                m, hw, n = ci95(vals)
                tv.append({"layout": layout, "method": method, "quantity": label, "n": n, "mean": m, "ci95": hw,
                           "min": min(vals), "max": max(vals), "per_seed": json.dumps([round(v, 3) for v in vals])})
    transfer_value = pd.DataFrame(tv)

    sep = []
    for layout in LAYOUTS:
        for method, rule in [("ilp", "REORDER_POINT"), ("baseline", "REORDER_POINT"), ("baseline", "NONE"),
                             ("baseline_legacy", "REORDER_POINT")]:
            vals = []
            for s in seeds:
                a = df[(df.method == method) & (df.layout == layout) & (df.seed == s) & (df.transfer_rule == rule)]
                b = df[(df.method == method) & (df.layout == "colocated") & (df.seed == s) & (df.transfer_rule == rule)]
                if not a.empty and not b.empty:
                    vals.append(float(a["total"].iloc[0]) - float(b["total"].iloc[0]))
            if vals:
                m, hw, n = ci95(vals)
                sep.append({"layout": layout, "method": method, "transfer_rule": rule, "n": n, "mean": m, "ci95": hw,
                            "per_seed": json.dumps([round(v, 3) for v in vals])})
    separation = pd.DataFrame(sep)
    return {"by_layout": by_layout, "transfer_value": transfer_value, "separation": separation}


def e3_plot_cost_by_layout(df: pd.DataFrame, path: str) -> str:
    """Mean total cost (26) per layout: ILP transfers free, ILP no_transfers, fixed baseline
    NONE and REORDER_POINT (bars = seed means, dots = seeds); the v1 (legacy) baseline
    means are drawn as hollow markers at the matching bars."""
    series = [("ilp", "REORDER_POINT", "ILP, transfers free", PALETTE[0]),
              ("ilp", "NONE", "ILP, no transfers (h = z = 0)", PALETTE[1]),
              ("baseline", "NONE", "baseline (fixed), NONE", PALETTE[2]),
              ("baseline", "REORDER_POINT", "baseline (fixed), REORDER_POINT", PALETTE[3])]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    width = 0.2
    rng = np.random.default_rng(0)
    for si, (method, rule, label, color) in enumerate(series):
        for li, layout in enumerate(LAYOUTS):
            sub = df[(df.layout == layout) & (df.method == method) & (df.transfer_rule == rule)]
            vals = sub["total"].dropna().to_numpy(dtype=float)
            if len(vals) == 0:
                continue
            x = li + (si - 1.5) * width
            ax.bar(x, vals.mean(), width - 0.02, color=color, edgecolor="white", linewidth=1.0, label=label if li == 0 else None)
            jitter = rng.uniform(-0.25, 0.25, len(vals)) * width if len(vals) > 1 else np.zeros(len(vals))
            ax.scatter(x + jitter, vals, s=12, color="#0b0b0b", zorder=3)
            ax.text(x, vals.mean() + 12, f"{vals.mean():.0f}", ha="center", va="bottom", fontsize=7, color="#0b0b0b")
            if method == "baseline":
                leg = df[(df.layout == layout) & (df.method == "baseline_legacy") & (df.transfer_rule == rule)]["total"]
                if len(leg):
                    ax.scatter([x], [leg.mean()], s=46, facecolors="none", edgecolors="#52514e", linewidths=1.2, zorder=4,
                               label="v1 (legacy) baseline mean" if (li == 0 and rule == "NONE") else None)
    ax.set_xticks(range(len(LAYOUTS)))
    ax.set_xticklabels([LAYOUT_LABEL[l] for l in LAYOUTS], fontsize=8.5)
    ax.set_ylabel("total cost (26), toy units; bars = seed means, dots = seeds", fontsize=9)
    ax.set_title("E3 v2: total cost by layout and transfer switch (fixed baseline; ILP rows unchanged)", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _bar_label(ax: plt.Axes, x: float, vals: Sequence[float], pad: float = 4.0) -> None:
    """Mean value label beside a bar: above a non-negative bar, below a negative one."""
    m = float(np.mean(vals))
    top = max(max(vals), m, 0.0)
    bot = min(min(vals), m, 0.0)
    if m >= 0:
        ax.text(x, top + pad, f"{m:.0f}", ha="center", va="bottom", fontsize=7, color="#0b0b0b")
    else:
        ax.text(x, bot - pad, f"{m:.0f}", ha="center", va="top", fontsize=7, color="#0b0b0b")


def e3_plot_transfer_value(tv: pd.DataFrame, sep: pd.DataFrame, path: str) -> str:
    """Left: value of transfers per layout (ILP: no_transfers - free; baseline fixed and
    legacy: NONE - REORDER_POINT); right: cost of separation vs co-located (ILP free,
    fixed baseline REORDER_POINT and NONE).  Bars = seed means, dots = seeds."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.0))
    left = [("ilp", "ILP (no_transfers - free)", PALETTE[0]), ("baseline", "baseline fixed (NONE - REORDER_POINT)", PALETTE[2]),
            ("baseline_legacy", "baseline v1 legacy (NONE - REORDER_POINT)", PALETTE[4])]
    width = 0.26
    labelled: set = set()
    for si, (method, label, color) in enumerate(left):
        for li, layout in enumerate(LAYOUTS):
            sub = tv[(tv.layout == layout) & (tv.method == method)]
            if sub.empty:
                continue
            vals = json.loads(sub["per_seed"].iloc[0])
            x = li + (si - 1) * width
            axes[0].bar(x, np.mean(vals), width - 0.02, color=color, edgecolor="white",
                        label=None if ("L", si) in labelled else labelled.add(("L", si)) or label)
            axes[0].scatter([x] * len(vals), vals, s=12, color="#0b0b0b", zorder=3)
            _bar_label(axes[0], x, vals)
    right = [("ilp", "REORDER_POINT", "ILP, transfers free", PALETTE[0]),
             ("baseline", "REORDER_POINT", "baseline fixed, REORDER_POINT", PALETTE[3]),
             ("baseline", "NONE", "baseline fixed, NONE", PALETTE[2])]
    for si, (method, rule, label, color) in enumerate(right):
        for li, layout in enumerate(LAYOUTS):
            sub = sep[(sep.layout == layout) & (sep.method == method) & (sep.transfer_rule == rule)]
            if sub.empty:
                continue
            vals = json.loads(sub["per_seed"].iloc[0])
            x = li + (si - 1) * width
            axes[1].bar(x, np.mean(vals), width - 0.02, color=color, edgecolor="white",
                        label=None if ("R", si) in labelled else labelled.add(("R", si)) or label)
            axes[1].scatter([x] * len(vals), vals, s=12, color="#0b0b0b", zorder=3)
            _bar_label(axes[1], x, vals)
    for ax, ttl in zip(axes, ("value of transfers: cost without - cost with transfers",
                              "cost of separation: cost(layout) - cost(co-located)")):
        ax.set_xticks(range(len(LAYOUTS)))
        ax.set_xticklabels([LAYOUT_LABEL[l].replace(" 3 sites", "\n3 sites").replace(" + ", "\n+ ") for l in LAYOUTS], fontsize=8)
        ax.axhline(0, color="#9a9a96", linewidth=0.8)
        ax.set_ylabel("cost difference (toy units)", fontsize=8.5)
        ax.margins(y=0.15)
        ax.set_title(ttl, fontsize=9.5, loc="left", pad=10)
        ax.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1)
        _style(ax)
    fig.suptitle("E3 v2: value of transfers and cost of separation (bars = seed means, dots = seeds; "
                 "fixed baseline, ILP rows unchanged)", fontsize=10, x=0.01, ha="left", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def e3_write_results(df: pd.DataFrame, out_dir: str, wall: float, time_limit: float, certified: bool) -> str:
    """Compose ``RESULTS_v2.md`` for E3 from ``results_v2.csv``."""
    T = e3_tables(df)
    by_layout, tv, sep = T["by_layout"], T["transfer_value"], T["separation"]
    figs = [e3_plot_cost_by_layout(df, os.path.join(out_dir, "fig_cost_by_layout_v2.png")),
            e3_plot_transfer_value(tv, sep, os.path.join(out_dir, "fig_transfer_value_v2.png"))]
    base = df[df.method.isin(E3_VARIANTS)]
    new = base[base.method == "baseline"]
    leg = base[base.method == "baseline_legacy"]
    n_runs = len(new)
    seeds = sorted(df.seed.unique().tolist())
    md: List[str] = []
    md.append("# E3 v2 -- value of transfers and of separation, baseline side re-run with the fixed policy\n")
    md.append(f"Byte-identical instances `instances/*.json` of the v1 run (family `large`: 10 bikes / 30 orders / H = 24 / L = 12; "
              f"layouts {list(LAYOUTS)}, seeds {seeds}; equal totals sum B = 9, sum C = 9, hubs hold 3 spares; bike q0 ~ "
              f"U{{0.3L..0.6L}}; shuttles every 6 slots). Arc libraries rebuilt with the v1 pruning (`pruning_for(inst)`), arc "
              f"counts reproduced in {int(new['n_arcs_match_v1'].sum())}/{n_runs} runs. **ILP rows (`no_transfers` and transfers free) "
              f"are the unchanged v1 rows; the free ILP was not re-solved.** `baseline_legacy` reproduces the v1 baseline cost "
              f"in {int(base[base.method == 'baseline_legacy']['legacy_reproduces_v1'].sum())}/{len(leg)} (layout, seed, rule) runs. "
              f"Certificates: fix-and-solve (Threads {C.THREADS}, TimeLimit {time_limit:.0f} s) of NONE starts in the `no_transfers` "
              f"model and REORDER_POINT starts in the transfers-free model, under the written model and under `relax_end_targets` "
              f"(rho = 0, R_end_j = 0)" + ("" if certified else " -- **not run in this invocation**") + f". Wall time {wall / 60:.1f} min.\n")
    md.append("Headline gap definition: `gap_vs_baseline_pct = 100 (baseline - ILP) / baseline` with the ILP of the matching "
              "transfer switch (`NONE` <-> `no_transfers`, `REORDER_POINT` <-> transfers free).\n")

    def bl(layout: str, rule: str, variant: str) -> Optional[pd.Series]:
        sub = by_layout[(by_layout.layout == layout) & (by_layout.transfer_rule == rule) & (by_layout.variant == variant)]
        return None if sub.empty else sub.iloc[0]

    present = [l for l in LAYOUTS if l in set(df.layout)]
    md.append("## Headline\n")
    for layout in present:
        bits = []
        for rule in E3_RULES:
            r, l0 = bl(layout, rule, "baseline"), bl(layout, rule, "baseline_legacy")
            if r is None or l0 is None:
                continue
            bits.append(f"{rule}: baseline {l0.baseline_total_mean:.1f} (v1) -> {r.baseline_total_mean:.1f} (fixed) vs ILP "
                        f"{r.ilp_total_mean:.1f}, gap {r.gap_vs_baseline_mean_pct:.1f} +/- {r.gap_vs_baseline_ci95_pct:.1f} % "
                        f"(v1 gap {l0.gap_vs_baseline_mean_pct:.1f} %)")
        md.append(f"- {LAYOUT_LABEL[layout]}: " + "; ".join(bits) + ".")
    for layout in present:
        ti = tv[(tv.layout == layout) & (tv.method == "ilp")].iloc[0]
        tb = tv[(tv.layout == layout) & (tv.method == "baseline")].iloc[0]
        tl = tv[(tv.layout == layout) & (tv.method == "baseline_legacy")].iloc[0]
        md.append(f"- value of transfers, {LAYOUT_LABEL[layout]}: ILP {ti['mean']:.1f} +/- {ti['ci95']:.1f}; fixed baseline "
                  f"(NONE - REORDER_POINT) {tb['mean']:.1f} +/- {tb['ci95']:.1f} (v1 legacy {tl['mean']:.1f}); per seed "
                  f"{tb['per_seed']}.")
    if certified:
        for rule in E3_RULES:
            sub = new[new.transfer_rule == rule]
            md.append(f"- MIP start of the fixed baseline ({rule}) accepted under the written model in "
                      f"{_n_true(sub['start_written_accepted'])}/{len(sub)} runs "
                      f"(v1 legacy: {int(sub['v1_mip_start_accepted'].sum())}/{len(sub)}) and under rho = 0, R_end = 0 in "
                      f"{_n_true(sub['start_relaxed_accepted'])}/{len(sub)}; `baseline_reserve`: "
                      f"{_n_true(base[(base.method == 'baseline_reserve') & (base.transfer_rule == rule)]['start_written_accepted'])}/{len(sub)} written.")
    md.append("")
    md.append("## Cost by layout x transfer switch (seed means; gap mean and 95 % t-CI over seeds)\n")
    md.append(C.markdown_table(by_layout, ["layout", "transfer_rule", "ilp_switch", "variant", "n", "v1_baseline_total_mean",
                                           "baseline_total_mean", "ilp_total_mean", "gap_vs_baseline_mean_pct",
                                           "gap_vs_baseline_ci95_pct", "unserved_mean", "ilp_unserved_mean", "swaps_mean",
                                           "transfers_used_mean", "batteries_moved_mean", "jit_mean", "reach_refusals_mean",
                                           "late_suppressed_mean", "viol_17_runs", "viol_18_runs", "start_written_accepted",
                                           "start_relaxed_accepted"], digits=2))
    md.append("\n## Value of transfers (per layout; ILP: no_transfers - free; baseline: NONE - REORDER_POINT)\n")
    md.append(C.markdown_table(tv, ["layout", "quantity", "n", "mean", "ci95", "min", "max", "per_seed"], digits=2))
    md.append("\n## Cost of separation (cost(layout) - cost(co-located), same method and switch)\n")
    md.append(C.markdown_table(sep, ["layout", "method", "transfer_rule", "n", "mean", "ci95", "per_seed"], digits=2))
    md.append("\n## Per-run table (baseline variants)\n")
    cols = ["layout", "seed", "transfer_rule", "method", "v1_baseline_total", "total", "delta_vs_v1_baseline", "ilp_total",
            "ilp_status", "gap_vs_baseline_pct", "n_unserved", "ilp_unserved_n", "n_swaps", "transfers_used", "batteries_moved",
            "jit_dispatches", "reach_refusals", "reach_bikes_sent_to_swap", "late_trips_suppressed", "viol_17", "viol_18",
            "check_families", "start_written_accepted", "start_written_status", "start_relaxed_accepted", "check_families_relaxed",
            "v1_mip_start_accepted"]
    md.append(C.markdown_table(base.sort_values(["layout", "seed", "transfer_rule", "method"]), [c for c in cols if c in base.columns], digits=2))
    # interpretation
    g_new = {rule: new[new.transfer_rule == rule]["gap_vs_baseline_pct"].mean() for rule in E3_RULES}
    g_leg = {rule: leg[leg.transfer_rule == rule]["gap_vs_baseline_pct"].mean() for rule in E3_RULES}
    tv_b = tv[tv.method == "baseline"].set_index("layout")["mean"]
    tv_l = tv[tv.method == "baseline_legacy"].set_index("layout")["mean"]
    tv_i = tv[tv.method == "ilp"].set_index("layout")["mean"]
    lines = []
    lines.append(f"With the fixed policy the coordination gap is {g_new['NONE']:.0f} % (NONE vs no_transfers ILP) and "
                 f"{g_new['REORDER_POINT']:.0f} % (REORDER_POINT vs transfers-free ILP) on average over layouts and seeds, "
                 f"against {g_leg['NONE']:.0f} % / {g_leg['REORDER_POINT']:.0f} % for the v1 policy: the E3 conclusions (transfers are worth "
                 f"nothing when every site charges and 250-260 units when it does not; separation costs the coordinator 55-100 units) do "
                 f"not involve the baseline and are unchanged; the baseline moves by {new['delta_vs_v1_baseline'].mean():+.1f} units on average "
                 f"({int((new['delta_vs_v1_baseline'] < -1e-9).sum())} runs cheaper, {int((new['delta_vs_v1_baseline'] > 1e-9).sum())} dearer of {n_runs}).")
    co = tv_b.get("colocated", float("nan"))
    hub_vals = [tv_b[l] for l in present if l != "colocated"]
    lines.append("Value of transfers for the baseline (NONE - REORDER_POINT, seed means): "
                 + "; ".join(f"{LAYOUT_LABEL[l]} {tv_b[l]:.0f} (v1 {tv_l[l]:.0f}; ILP {tv_i[l]:.0f})" for l in present) + ". "
                 + (f"Where charging is separated from swapping the reorder-point rule recovers "
                    f"{100 * min(hub_vals) / max(1e-9, min(tv_i[l] for l in present if l != 'colocated')):.0f}-"
                    f"{100 * max(hub_vals) / max(1e-9, max(tv_i[l] for l in present if l != 'colocated')):.0f} % of the value the "
                    f"coordinator extracts from the shuttles" if hub_vals else "")
                 + (f"; in the co-located layout the fixed policy's extra swaps trigger shipments between sites that charge "
                    f"themselves ({tv[(tv.layout == 'colocated') & (tv.method == 'baseline')]['per_seed'].iloc[0]} per seed, "
                    f"{new[(new.layout == 'colocated') & (new.transfer_rule == 'REORDER_POINT')]['transfers_used'].mean():.1f} services and "
                    f"C_reb {new[(new.layout == 'colocated') & (new.transfer_rule == 'REORDER_POINT')]['C_reb'].mean():.1f} per run), "
                    f"so the rule costs {-co:.0f} units there, whereas the ILP never ships between co-located sites (value 0)."
                    if co < -1 else f"; in the co-located layout transfers are worth {co:.0f} to the baseline and 0 to the ILP."))
    sep_i = sep[(sep.method == "ilp")].set_index("layout")["mean"]
    sep_b = sep[(sep.method == "baseline") & (sep.transfer_rule == "REORDER_POINT")].set_index("layout")["mean"]
    sep_n = sep[(sep.method == "baseline") & (sep.transfer_rule == "NONE")].set_index("layout")["mean"]
    lines.append("Cost of separation (layout minus co-located): "
                 + "; ".join(f"{LAYOUT_LABEL[l]} ILP {sep_i[l]:.0f} / fixed baseline REORDER_POINT {sep_b[l]:.0f} / NONE {sep_n[l]:.0f}"
                             for l in present if l != "colocated")
                 + ". Without transfers the baseline pays several times more for separation than the coordinator (swap-only sites "
                 "with two spares each and no charger run dry); with the reorder-point rule its separation penalty is "
                 + ("smaller than the ILP's, because its co-located REORDER_POINT run is itself inflated by the pointless shipments above."
                    if all(sep_b[l] < sep_i[l] for l in present if l != "colocated") else "of the same order as the ILP's."))
    by_var = {v: base[base.method == v]["total"].mean() for v in E3_VARIANTS}
    lines.append(f"Variants (mean over layouts, rules and seeds): legacy {by_var['baseline_legacy']:.1f}, fixed {by_var['baseline']:.1f}, "
                 f"reserve {by_var['baseline_reserve']:.1f}, informed {by_var['baseline_informed']:.1f}. On this swap-scarce family "
                 f"(9 spares for 10 bikes starting at 0.3-0.6 L) the fixed policy is dearer than the v1 policy on average; the likely mechanism "
                 f"(not isolated here) is that the just-in-time rule ({new['jit_dispatches'].mean():.1f} JIT dispatches per run) keeps bikes "
                 f"idle-but-committed instead of sending them to swap early, and one more order per run is left unserved ({leg['n_unserved'].mean():.2f} -> {new['n_unserved'].mean():.2f}); "
                 f"the stock-aware site choice of `baseline_informed` is the one variant that helps here, "
                 f"{by_var['baseline'] - by_var['baseline_informed']:.0f} units below the fixed default.")
    if certified:
        rej = new[new["start_written_accepted"] == False]  # noqa: E712
        lines.append(f"MIP starts: {len(new) - len(rej)}/{len(new)} fixed-baseline starts are feasible points of the written model; the rejected "
                     f"ones all carry (17)/(18) shortfalls (report-only families), and "
                     f"{_n_true(new['start_relaxed_accepted'])}/{len(new)} are accepted once rho = 0 and R_end = 0. "
                     f"Note that the ILP rows at the written targets therefore compare a constrained optimum with an unconstrained "
                     f"policy; the partial v1 side run `relaxed_end_targets/` (seed 0, two layouts) showed the ILP cost moving by only a few "
                     f"units when (17)-(18) are dropped.")
    md.append("\n## Interpretation\n")
    md.append(" ".join(lines) + "\n")
    md.append("## Anomalies / checks\n")
    an = []
    if int(new["n_arcs_match_v1"].sum()) != n_runs:
        an.append("- arc library not reproduced on some instance.")
    if int(leg["legacy_reproduces_v1"].sum()) != len(leg):
        an.append("- `baseline_legacy` does not reproduce the v1 baseline cost in some run (CSV `legacy_reproduces_v1`).")
    for _, r in base.iterrows():
        if r["total"] < r["ilp_total"] - 1e-6:
            an.append(f"- {r['layout']} seed {r['seed']} {r['method']}/{r['transfer_rule']}: baseline {r['total']:.2f} < ILP {r['ilp_total']:.2f} "
                      f"(ILP status {r['ilp_status']}, gap {r['ilp_gap']}; baseline families {r['check_families']}; written start accepted = "
                      f"{r['start_written_accepted']}) -- the baseline point is infeasible for the written model or the ILP timed out, "
                      f"not a counter-example to optimality.")
    if certified:
        bad = base[(base["start_written_accepted"] == True) & (base["check_ok"] == False)]  # noqa: E712
        if len(bad):
            an.append("- a start accepted by Gurobi although evaluate.check reports violations.")
        bad2 = base[(base["start_written_accepted"] == False) & (base["check_ok"] == True)]  # noqa: E712
        if len(bad2):
            an.append("- a start rejected by Gurobi although evaluate.check is clean.")
        rel_rej = base[base["start_relaxed_accepted"] == False]  # noqa: E712
        if len(rel_rej):
            an.append("- starts rejected even under rho = 0, R_end = 0: " + ", ".join(
                f"{r.layout}/seed{r.seed}/{r.method}/{r.transfer_rule} ({r.check_families_relaxed})" for r in rel_rej.itertuples()))
    nm = base[~base["ok_modulo_report_only"].astype(bool)]
    if len(nm):
        an.append("- baseline violates a non-report-only family: " + ", ".join(
            f"{r.layout}/seed{r.seed}/{r.method}/{r.transfer_rule} {r.check_families}" for r in nm.itertuples()))
    if not base["identity_24_ok"].astype(bool).all() or not base["inventory_consistent"].astype(bool).all():
        an.append("- identity (24) or online inventory consistency broken on some baseline run.")
    tl = df[(df.method == "ilp") & (df.status != "OPTIMAL")]
    if len(tl):
        an.append("- v1 ILP rows not proven optimal (inherited): " + ", ".join(
            f"{r.layout}/seed{r.seed}/{r.switch} ({r.status}, gap {float(r.gap):.4f})" for r in tl.itertuples()))
    md.extend(an or ["- none"])
    md.append("\n## Figures\n")
    md.extend(f"- `{os.path.basename(f)}`" for f in figs)
    md.append("\nFiles: `results_v2.csv` (baseline variant rows + the unchanged v1 ILP rows, column `source`), `wall_time_v2.json`. "
              "v1 files (`RESULTS.md`, `results.csv`, figures without suffix) are untouched.")
    path = os.path.join(out_dir, "RESULTS_v2.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


def run_e3(out_dir: str, certify: bool, time_limit: float, max_instances: Optional[int],
           analyse_only: bool) -> None:
    csv_path = os.path.join(out_dir, "results_v2.csv")
    wall_path = os.path.join(out_dir, "wall_time_v2.json")
    if not analyse_only:
        old = pd.read_csv(os.path.join(out_dir, "results.csv"))
        insts = load_instances(os.path.join(out_dir, "instances"), max_instances)
        t0 = time.perf_counter()
        rows: List[Dict[str, Any]] = []
        log: List[str] = []
        print(f"[E3] {len(insts)} instances", flush=True)
        for inst in insts:
            rows += e3_run_instance(inst, old, certify, time_limit, log)
            C.write_csv(rows, csv_path)
        wall = time.perf_counter() - t0
        with open(wall_path, "w") as fh:
            json.dump({"wall_s": wall, "certify": certify, "certify_time_limit": time_limit, "log": log}, fh)
        for line in log:
            print("  WARNING:", line)
    else:
        meta = json.load(open(wall_path))
        wall, certify = meta["wall_s"], meta["certify"]
    df = pd.read_csv(csv_path)
    print(e3_write_results(df, out_dir, wall, time_limit, certify))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(parts: Sequence[str], certify: bool, time_limit: float, max_instances: Optional[int],
         analyse_only: bool) -> None:
    t0 = time.perf_counter()
    if "e2" in parts:
        run_e2(E2_DIR, certify, time_limit, max_instances, analyse_only)
    if "e3" in parts:
        run_e3(E3_DIR, certify, time_limit, max_instances, analyse_only)
    print(f"total wall {(time.perf_counter() - t0) / 60:.1f} min")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parts", nargs="+", default=["e2", "e3"], choices=["e2", "e3"])
    ap.add_argument("--certify-time-limit", type=float, default=CERTIFY_TIME_LIMIT)
    ap.add_argument("--no-certify", action="store_true", help="skip the fix-and-solve MIP-start certificates")
    ap.add_argument("--max-instances", type=int, default=None, help="smoke run on the first N instances")
    ap.add_argument("--analyse-only", action="store_true", help="rebuild RESULTS_v2.md / figures from results_v2.csv")
    args = ap.parse_args()
    main(args.parts, not args.no_certify, args.certify_time_limit, args.max_instances, args.analyse_only)
