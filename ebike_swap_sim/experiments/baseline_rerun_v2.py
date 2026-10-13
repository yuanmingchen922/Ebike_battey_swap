"""Re-run of the *fixed* baseline policy on the byte-identical instances of E2, E3
and E4, with the ILP rows re-used from the existing ``results.csv`` files.

Background
----------
The reviewer fixes to :mod:`ebike_swap_sim.baseline` (F1 just-in-time dispatch,
F2 dead-zone rule, F3 ``baseline_reserve`` / ``late_threshold_window``, F6
``stock_aware_site``) change the baseline schedules only; the ILP objective,
constraints and the arc builder's default behaviour are untouched, so every ILP
row of ``outputs/e2_coord``, ``outputs/e3`` and ``outputs/e4_sizing`` (incl.
``stressed_lowq0``) stays valid.  This script therefore

1. loads (E2, E3) or deterministically regenerates (E4) every instance those
   experiments used, builds the same arc library ((1)-(4), (9) with the same
   pruning options) and checks byte-identity: ``n_arcs`` equals the old
   ``n_arcs`` column and the ``baseline_legacy`` variant (``jit_dispatch = False``,
   ``swap_on_reach_refusal = False``) reproduces the old baseline total exactly;
2. runs the documented baseline variants of :data:`experiments.common.BASELINE_VARIANTS`
   (``baseline`` = the fixed default, ``baseline_legacy`` = the old behaviour,
   ``baseline_reserve`` = end-reserve + late-threshold windows (respects (17)),
   ``baseline_informed`` = stock-aware site choice + end awareness, and
   ``baseline_reorder`` = REORDER_POINT transfers where services exist (E2, E3));
3. certifies MIP-start acceptance of the new default baseline (and of the
   REORDER_POINT / RESERVE variants where cheap) with the existing fix-and-solve
   certificate of :meth:`ebike_swap_sim.ilp.ILPModel.verify_mip_start` (Gurobi with
   every variable fixed, ``OutputFlag 0``, ``Threads 4``, ``TimeLimit 120``) under
   (a) the written model, (b) ``rho = 0`` only (the (18) row removed; the control of
   the old ``ilp_rho0`` / ``ILP_rho0`` runs) and (c) the fully relaxed end targets
   ``rho = 0`` and ``R_end_j = 0`` ((17) and (18) removed, :func:`common.relax_end_targets`).
   The free ILP is **not** re-solved;
4. recomputes the comparison tables with the headline gap
   ``gap_vs_baseline_pct = 100 (baseline - ILP) / baseline`` (and ``gap_vs_ilp_pct``,
   :func:`experiments.common.gap_definitions`), writes ``results_v2.csv`` /
   ``RESULTS_v2.md`` next to the untouched ``results.csv`` / ``RESULTS.md`` of each
   experiment and redraws the figures with a ``_v2`` suffix (E4: ``cost_vs_B_v2.png``
   and ``cost_vs_C_v2.png`` with both regimes, ``cost_vs_P_v2.png``).

Costs: :func:`ebike_swap_sim.evaluate.cost` (26)-(32); checks:
:func:`ebike_swap_sim.evaluate.check` (5)-(22), (24).  Only this module's
certificate step touches gurobipy (through :mod:`ebike_swap_sim.ilp`).

Run from ``ebike_swap_sim/`` (baseline runs take milliseconds; the certificates
dominate: about 10 s per instance / variant)::

    PYTHONPATH=. python3 experiments/baseline_rerun_v2.py --parts e2 e3          # ~6 min
    PYTHONPATH=. python3 experiments/baseline_rerun_v2.py --parts e4             # ~9 min
    PYTHONPATH=. python3 experiments/baseline_rerun_v2.py --parts e4s            # ~5 min
    PYTHONPATH=. python3 experiments/baseline_rerun_v2.py --report-only          # tables + figures
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from experiments import common as C  # noqa: E402
from experiments import e4_sizing as E4  # noqa: E402
from experiments.e2_coord import DEMAND, ci95  # noqa: E402
from ebike_swap_sim import ArcLibrary, Instance, Schedule  # noqa: E402

plt = C.plt

OUT_E2 = os.path.join(C.OUTPUT_ROOT, "e2_coord")
OUT_E3 = os.path.join(C.OUTPUT_ROOT, "e3")
OUT_E4 = os.path.join(C.OUTPUT_ROOT, "e4_sizing")
OUT_E4S = os.path.join(OUT_E4, "stressed_lowq0")
#: E2 / E3 outputs of THIS script go to a subfolder: two sibling scripts
#: (``baseline_refresh_v2.py``, ``e2_coord_v2.py``) write ``results_v2.csv`` / ``RESULTS_v2.md``
#: directly into ``outputs/e2_coord`` and ``outputs/e3``; the subfolder avoids clobbering them.
OUT_E2_V2 = os.path.join(OUT_E2, "baseline_rerun_v2")
OUT_E3_V2 = os.path.join(OUT_E3, "baseline_rerun_v2")
CERT_TIME_LIMIT = 120.0
COMPONENTS = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"]
#: ``gap_vs_baseline_pct`` is the headline definition (plan): 100 (baseline - ILP) / baseline.
GAP_NOTE = ("`gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline, plan definition); "
            "`gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP (baseline excess over the optimum).")

#: validated categorical palette (dataviz reference instance, fixed slot order; the
#: contrast WARN on slots 3-5 is relieved by the legend, the line styles and the tables)
PALETTE = {"ILP": "#2a78d6", "baseline": "#eb6834", "baseline_legacy": "#1baf7a",
           "baseline_reserve": "#eda100", "ILP_rho0": "#e87ba4", "baseline_informed": "#4a3aa7",
           "baseline_reorder": "#008300", "baseline_reorder_legacy": "#e34948"}
LINESTYLE = {"ILP": "-", "ILP_rho0": "--", "baseline": "-", "baseline_legacy": "--",
             "baseline_reserve": ":", "baseline_informed": "-.", "baseline_reorder": "-",
             "baseline_reorder_legacy": "--"}
LABEL = {"ILP": "ILP (written model, rho = 0.5)", "ILP_rho0": "ILP with rho = 0 ((18) off)",
         "baseline": "baseline v2 (fixed policy)", "baseline_legacy": "baseline legacy (old behaviour)",
         "baseline_reserve": "baseline_reserve (end windows)", "baseline_informed": "baseline_informed",
         "baseline_reorder": "baseline REORDER_POINT v2", "baseline_reorder_legacy": "baseline REORDER_POINT legacy"}

E2_VARIANTS = ["baseline", "baseline_legacy", "baseline_reserve", "baseline_informed", "baseline_reorder"]
E3_VARIANTS = ["baseline", "baseline_legacy", "baseline_reserve", "baseline_informed",
               "baseline_reorder", "baseline_reorder_legacy"]
E4_VARIANTS = ["baseline", "baseline_legacy", "baseline_reserve", "baseline_informed"]


# ---------------------------------------------------------------------------
# variants
# ---------------------------------------------------------------------------
def variant_params(name: str, inst: Instance) -> Dict[str, Any]:
    """``BaselineParams`` field dict of a variant: :func:`common.baseline_variant_params`
    plus the extra ``baseline_reorder_legacy`` (old behaviour with REORDER_POINT, the
    E3 reference run)."""
    if name == "baseline_reorder_legacy":
        return {**C.baseline_variant_params("baseline_legacy", inst), "transfer_rule": "REORDER_POINT"}
    return C.baseline_variant_params(name, inst)


def _count(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, dict):
        return int(v.get("count", len(v))) if "count" in v else len(v)
    return len(v)


def accept_by_check(families: Dict[str, int]) -> Dict[str, bool]:
    """Solver-independent acceptance of a schedule from its ``evaluate.check`` families:
    the written model accepts iff no family is reported; the ``rho = 0`` control iff only
    (18) is reported; the fully relaxed end targets iff only (17) / (18) are reported."""
    fams = set(families)
    return {"accept_written_by_check": not fams,
            "accept_rho0_by_check": fams <= {"(18)"},
            "accept_relaxed_by_check": fams <= {"(17)", "(18)"}}


def baseline_row(inst: Instance, lib: ArcLibrary, variant: str, res: Dict[str, Any]) -> Dict[str, Any]:
    """Flat record of one :func:`common.run_baseline_case` result: cost (26)-(32),
    ``evaluate.metrics``, the report-only violations (9) / (17) / (18) the policy
    reports, the fix diagnostics (``jit_dispatches``, ``reach_refusals``,
    ``late_trips_suppressed``, ``stock_aware_reroutes``) and the check-based
    acceptance flags of :func:`accept_by_check`."""
    fl, m, cst = res["flags"], res["metrics"], res["cost"]
    rr = fl.get("reach_refusals") or {}
    row: Dict[str, Any] = {
        "variant": variant, "params": json.dumps(res["params"], sort_keys=True, default=str),
        "n_arcs": len(lib), "runtime_ms": 1000.0 * res["runtime"],
        **C.flatten_cost(cst), "operational": cst["total"] - cst["C_setup"],
        "n_unserved": m["n_unserved"], "served_share": m["served_share"],
        "mean_response_h": m["mean_response_h"], "n_late": m["n_late"], "mean_lateness_h": m["mean_lateness_h"],
        "bike_km": m["bike_km"], "n_swaps": m["n_swaps"], "kwh_purchased": m["kwh_purchased"],
        "transfers_used": m["transfers_used"], "batteries_moved": m["batteries_moved"],
        "end_full_total": m["end_full_total"], "end_target_shortfall_18": m["end_target_shortfall"],
        "viol_17_local_sum": sum(fl["end_shortfalls"]["local"].values()),
        "viol_18_global": fl["end_shortfalls"]["global"], "viol_9": len(fl["terminal_violations"]),
        "families": json.dumps(res["families"], sort_keys=True),
        "check_ok": res["ok"], "ok_modulo_report_only": res["ok_modulo_report_only"],
        "identity_24_ok": res["identity_24_ok"], "inventory_consistent": fl["inventory_consistent"],
        "jit_dispatches": _count(fl.get("jit_dispatches", 0)),
        "reach_refusals": _count(rr.get("count", 0)) if rr else 0,
        "reach_bikes_sent_to_swap": _count(rr.get("bikes_sent_to_swap", 0)) if rr else 0,
        "late_trips_suppressed": _count(fl.get("late_trips_suppressed", 0)),
        "stock_aware_reroutes": _count(fl.get("stock_aware_reroutes", 0)),
        "max_need": fl.get("max_need"), "q_thr": fl.get("q_thr"),
    }
    row.update(accept_by_check(res["families"]))
    return row


def run_variants(inst: Instance, lib: ArcLibrary, variants: Sequence[str]
                 ) -> Tuple[List[Dict[str, Any]], Dict[str, Schedule]]:
    """Run every variant on ``(inst, lib)``; returns ``(rows, {variant: Schedule})``."""
    rows, scheds = [], {}
    for name in variants:
        res = C.run_baseline_case(inst, lib, variant_params(name, inst), label=name)
        rows.append(baseline_row(inst, lib, name, res))
        scheds[name] = res["schedule"]
    return rows, scheds


# ---------------------------------------------------------------------------
# fix-and-solve certificate
# ---------------------------------------------------------------------------
def _build_model(inst: Instance, lib: ArcLibrary, time_limit: float):
    """:class:`ebike_swap_sim.ilp.ILPModel` of ``inst`` with the switches resolved as
    :func:`ebike_swap_sim.ilp.build_model` does (``inst.options`` / ``inst.budget`` /
    ``inst.zeta``) and constraint names on, so that the (17) rows (``end_local[j]``)
    and the (18) row (``end_share``) can be removed for the relaxed certificates."""
    from ebike_swap_sim import ilp

    fixed = inst.option("fixed_facilities")
    return ilp.ILPModel(
        inst, lib,
        no_transfers=bool(inst.option("no_transfers")), colocated=bool(inst.option("colocated")),
        fixed_facilities=True if fixed is None else bool(fixed),
        budget=inst.budget, zeta=inst.zeta, lexicographic=bool(inst.option("lexicographic")),
        battery_swap_v1_bounds=bool(inst.option("battery_swap_v1_bounds")),
        threads=C.THREADS, time_limit=time_limit, output=False, names=True)


def certify(inst: Instance, lib: ArcLibrary, scheds: Dict[str, Schedule],
            time_limit: float = CERT_TIME_LIMIT) -> Dict[str, Dict[str, Any]]:
    """Fix-and-solve MIP-start certificate (:meth:`ILPModel.verify_mip_start`) of
    every schedule in ``scheds`` under three end-target regimes on ONE model:

    * ``written``  -- the model as written ((17) with ``R_end_j``, (18) with ``rho``);
    * ``rho0``     -- the (18) row ``end_share`` removed (``rho = 0``; the control of the
      old ``ilp_rho0`` / ``ILP_rho0`` runs);
    * ``relaxed``  -- additionally the (17) rows ``end_local[j]`` removed (``rho = 0`` and
      ``R_end_j = 0``, :func:`common.relax_end_targets`).

    A schedule accepted at an earlier stage is accepted at every later one (pure
    relaxations; recorded as status ``'implied'``).  All variables are fixed, so the
    ``no_transfers`` switch is immaterial (a start with ``h = z = 0`` is feasible for the
    free model iff it is for the ``h = z = 0`` model).  Returns per label
    ``cert_<stage>`` (bool), ``cert_<stage>_status``, ``cert_written_obj`` (Gurobi objective
    of the fixed point) and the timings ``cert_build_s`` / ``cert_solve_s``."""
    t0 = time.perf_counter()
    mdl = _build_model(inst, lib, time_limit)
    build_s = time.perf_counter() - t0
    cons = mdl.model.getConstrs()
    c17 = [c for c in cons if c.ConstrName.startswith("end_local[")]
    c18 = [c for c in cons if c.ConstrName == "end_share"]
    assert len(c17) == len(inst.S) and len(c18) == 1, (len(c17), len(c18))
    out: Dict[str, Dict[str, Any]] = {k: {"cert_build_s": build_s, "cert_solve_s": 0.0} for k in scheds}
    try:
        for stage, drop in (("written", []), ("rho0", c18), ("relaxed", c17)):
            if drop:
                mdl.model.remove(drop)
                mdl.model.update()
            for label, sched in scheds.items():
                rec = out[label]
                prev = [s for s in ("written", "rho0") if f"cert_{s}" in rec and rec[f"cert_{s}"]]
                if prev:
                    rec[f"cert_{stage}"] = True
                    rec[f"cert_{stage}_status"] = "implied"
                    continue
                t1 = time.perf_counter()
                mdl.set_mip_start(sched, verify=False)
                ok, obj, status = mdl.verify_mip_start(time_limit)
                rec["cert_solve_s"] += time.perf_counter() - t1
                rec[f"cert_{stage}"] = bool(ok)
                rec[f"cert_{stage}_status"] = status
                if stage == "written":
                    rec["cert_written_obj"] = obj
                elif ok:
                    rec["cert_obj"] = obj
    finally:
        mdl.model.dispose()
        mdl.env.dispose()
    return out


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def _first(df: pd.DataFrame, col: str, default: Any = None) -> Any:
    if df.empty or col not in df.columns:
        return default
    v = df[col].iloc[0]
    if isinstance(v, float) and math.isnan(v):
        return default
    return v


def _attach_gaps(row: Dict[str, Any], ilp_total: Optional[float], ilp_rho0_total: Optional[float]) -> None:
    g = C.gap_definitions(row["total"], ilp_total)
    row["gap_vs_baseline_pct"] = g["gap_vs_baseline_pct"]
    row["gap_vs_ilp_pct"] = g["gap_vs_ilp_pct"]
    row["gap_rho0_vs_baseline_pct"] = C.gap_definitions(row["total"], ilp_rho0_total)["gap_vs_baseline_pct"]


def _close(a: Any, b: Any, tol: float = 1e-6) -> Optional[bool]:
    if a is None or b is None:
        return None
    return abs(float(a) - float(b)) <= tol


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# E2: 15 saved instances
# ---------------------------------------------------------------------------
def run_e2(do_certify: bool = True) -> pd.DataFrame:
    """Baseline variants + certificates on the 15 saved E2 instances
    (``outputs/e2_coord/instances/*.json``, pruning ``reachable = True`` as in
    ``e2_coord``); ILP rows (``ilp`` rho = 0.5, ``ilp_rho0`` rho = 0) from the old
    ``results.csv``.  Writes ``results_v2.csv``."""
    old = pd.read_csv(os.path.join(OUT_E2, "results.csv"))
    rows: List[Dict[str, Any]] = []
    t_start = time.perf_counter()
    for path in sorted(glob.glob(os.path.join(OUT_E2, "instances", "*.json"))):
        inst = Instance.load(path)
        name = inst.meta["name"]
        lib, t_lib = C.build_library(inst, C.pruning_for(inst, reachable=True))
        o = old[old["name"] == name]
        o_rho0 = old[old["name"] == name + "-rho0"]
        ob = o[o["method"] == "baseline"]
        oi = o[o["method"] == "ilp"]
        oi0 = o_rho0[o_rho0["method"] == "ilp_rho0"]
        ilp_total, ilp_rho0_total = _first(oi, "total"), _first(oi0, "total")
        vrows, scheds = run_variants(inst, lib, E2_VARIANTS)
        certs = certify(inst, lib, {k: scheds[k] for k in ("baseline", "baseline_reserve", "baseline_reorder")}) \
            if do_certify else {}
        for r in vrows:
            r.update({
                "exp": "e2", "group": "main", "name": name, "seed": inst.meta["seed"],
                "demand_mult": inst.meta["demand_mult"], "n_orders": len(inst.orders), "rho": inst.rho,
                "lib_build_s": t_lib, "n_arcs_old": _first(ob, "n_arcs"),
                "n_arcs_match": _close(len(lib), _first(ob, "n_arcs"), 0),
                "old_baseline_total": _first(ob, "total"), "old_baseline_n_unserved": _first(ob, "n_unserved"),
                "old_baseline_C_travel": _first(ob, "C_travel"),
                "legacy_matches_old": _close(r["total"], _first(ob, "total")) if r["variant"] == "baseline_legacy" else None,
                "ilp_total": ilp_total, "ilp_status": _first(oi, "status"), "ilp_gap": _first(oi, "gap"),
                "ilp_n_unserved": _first(oi, "n_unserved"), "ilp_runtime_s": _first(oi, "runtime_s"),
                "ilp_mip_start_accepted_old": _first(oi, "mip_start_accepted"),
                "ilp_rho0_total": ilp_rho0_total, "ilp_rho0_status": _first(oi0, "status"),
                "ilp_rho0_mip_start_accepted_old": _first(oi0, "mip_start_accepted"),
            })
            r.update(certs.get(r["variant"], {}))
            _attach_gaps(r, ilp_total, ilp_rho0_total)
        rows.extend(vrows)
        b = vrows[0]
        _log(f"e2 {name}: v2 {b['total']:.2f} (unserved {b['n_unserved']}) legacy {vrows[1]['total']:.2f} "
             f"old {_first(ob, 'total')} ilp {ilp_total} cert {certs.get('baseline', {}).get('cert_written')}/"
             f"{certs.get('baseline', {}).get('cert_relaxed')} arcs match {b['n_arcs_match']} "
             f"[{(time.perf_counter() - t_start) / 60:.1f} min]")
        C.write_csv(rows, os.path.join(C.ensure_dir(OUT_E2_V2), "results_v2.csv"))
    return C.write_csv(rows, os.path.join(C.ensure_dir(OUT_E2_V2), "results_v2.csv"))


# ---------------------------------------------------------------------------
# E3: 9 saved layout instances + 2 relaxed-end-target instances
# ---------------------------------------------------------------------------
def run_e3(do_certify: bool = True) -> pd.DataFrame:
    """Baseline variants (NONE and REORDER_POINT families) + certificates on the saved
    E3 instances (``outputs/e3/instances``, group ``main``) and on the relaxed
    end-target side run (``outputs/e3/relaxed_end_targets/instances``, group
    ``relaxed_end_targets``); ILP rows (transfers free / ``no_transfers``) from the
    old ``results.csv`` of each group.  Writes ``outputs/e3/results_v2.csv``."""
    rows: List[Dict[str, Any]] = []
    t_start = time.perf_counter()
    for group, root in (("main", OUT_E3), ("relaxed_end_targets", os.path.join(OUT_E3, "relaxed_end_targets"))):
        old = pd.read_csv(os.path.join(root, "results.csv"))
        for path in sorted(glob.glob(os.path.join(root, "instances", "*.json"))):
            inst = Instance.load(path)
            layout, seed = inst.meta["layout"], inst.meta["seed"]
            lib, t_lib = C.build_library(inst, C.pruning_for(inst))
            o = old[(old["layout"] == layout) & (old["seed"] == seed)]
            ob_none = o[(o["method"] == "baseline") & (o["transfers"] == "none")]
            ob_free = o[(o["method"] == "baseline") & (o["transfers"] == "free")]
            oi_free = o[(o["method"] == "ilp") & (o["transfers"] == "free")]
            oi_none = o[(o["method"] == "ilp") & (o["transfers"] == "none")]
            vrows, scheds = run_variants(inst, lib, E3_VARIANTS)
            certs = certify(inst, lib, {k: scheds[k] for k in ("baseline", "baseline_reorder", "baseline_reserve")}) \
                if do_certify else {}
            for r in vrows:
                reorder = r["variant"].startswith("baseline_reorder")
                ob = ob_free if reorder else ob_none
                # the ILP of the same transfer switch is the natural comparison; both are kept
                ilp_same = _first(oi_free, "total") if reorder else _first(oi_none, "total")
                r.update({
                    "exp": "e3", "group": group, "name": inst.meta.get("name", f"e3-{layout}-seed{seed}"),
                    "layout": layout, "seed": seed, "rho": inst.rho,
                    "R_end": json.dumps({f.id: int(f.R_end) for f in inst.facilities}, sort_keys=True),
                    "transfers": "free" if reorder else "none", "lib_build_s": t_lib,
                    "n_arcs_old": _first(ob, "n_arcs"), "n_arcs_match": _close(len(lib), _first(ob, "n_arcs"), 0),
                    "old_baseline_total": _first(ob, "total"), "old_baseline_n_unserved": _first(ob, "n_unserved"),
                    "legacy_matches_old": _close(r["total"], _first(ob, "total"))
                    if r["variant"] in ("baseline_legacy", "baseline_reorder_legacy") else None,
                    "ilp_total": ilp_same, "ilp_free_total": _first(oi_free, "total"),
                    "ilp_none_total": _first(oi_none, "total"),
                    "ilp_free_status": _first(oi_free, "status"), "ilp_free_gap": _first(oi_free, "gap"),
                    "ilp_none_status": _first(oi_none, "status"),
                    "ilp_free_n_unserved": _first(oi_free, "n_unserved"), "ilp_none_n_unserved": _first(oi_none, "n_unserved"),
                    "ilp_free_mip_start_accepted_old": _first(oi_free, "mip_start_accepted"),
                    "ilp_none_mip_start_accepted_old": _first(oi_none, "mip_start_accepted"),
                })
                r.update(certs.get(r["variant"], {}))
                _attach_gaps(r, ilp_same, None)
                r["gap_vs_ilp_free_pct"] = C.gap_definitions(r["total"], _first(oi_free, "total"))["gap_vs_baseline_pct"]
            rows.extend(vrows)
            b = vrows[0]
            _log(f"e3 {group} {layout} seed {seed}: NONE v2 {b['total']:.2f} legacy {vrows[1]['total']:.2f} "
                 f"old {_first(ob_none, 'total')} | REORDER v2 {vrows[4]['total']:.2f} legacy {vrows[5]['total']:.2f} "
                 f"old {_first(ob_free, 'total')} | cert {certs.get('baseline', {}).get('cert_written')}/"
                 f"{certs.get('baseline', {}).get('cert_relaxed')} [{(time.perf_counter() - t_start) / 60:.1f} min]")
            C.write_csv(rows, os.path.join(C.ensure_dir(OUT_E3_V2), "results_v2.csv"))
    return C.write_csv(rows, os.path.join(C.ensure_dir(OUT_E3_V2), "results_v2.csv"))


# ---------------------------------------------------------------------------
# E4: regenerated sizing variants (both regimes)
# ---------------------------------------------------------------------------
def _apply_sizes(work: Instance, B: Any, C_: Any, P: float, tag: str) -> None:
    """In-place counterpart of :func:`experiments.e4_sizing.sized_instance` (same
    fields, same ``meta['variant']``), so that ONE arc library serves every variant
    of a seed: the arcs (1)-(4), (9) do not depend on ``B_j``, ``C_j`` or ``P_j`` and
    the library keeps its identity with the instance object."""
    for f in work.facilities:
        f.B = int(B[str(f.id)] if isinstance(B, dict) else B)
        f.C = int(C_[str(f.id)] if isinstance(C_, dict) else C_)
        f.P_kw = float(P)
    work.reindex()
    work.validate()
    work.meta["variant"] = {"tag": tag, "B": E4._site_map(work, "B"), "C": E4._site_map(work, "C"),
                            "P_kw": E4._site_map(work, "P_kw"), "free": False, "rho": work.rho}


def run_e4(regime: str, do_certify: bool = True) -> pd.DataFrame:
    """Baseline variants + certificate of the default baseline on every fixed-size
    E4 variant of ``regime`` (``'main'`` -> ``outputs/e4_sizing``, ``'stressed_lowq0'`` ->
    its subfolder): the instances are regenerated deterministically from
    ``run_meta.json`` (family, seeds, sweeps, ``init_frac``) exactly as
    :func:`experiments.e4_sizing.main` does (``variant_plan`` + the ``free_fixed`` sizes
    of ``free_choice``); byte-identity is verified against the old ``n_arcs`` and
    ``q0_mean`` columns and by the legacy variant reproducing the old baseline total.
    ILP rows (``ILP``, ``ILP_rho0``) come from the old ``results.csv``.  Writes
    ``results_v2.csv`` in the regime's folder."""
    root = OUT_E4 if regime == "main" else OUT_E4S
    meta = json.load(open(os.path.join(root, "run_meta.json"), encoding="utf-8"))
    old = pd.read_csv(os.path.join(root, "results.csv"))
    overrides: Dict[str, Any] = {}
    if meta.get("init_frac"):
        overrides["demand_spec"] = {"init_frac": (float(meta["init_frac"][0]), float(meta["init_frac"][1]))}
    plan = E4.variant_plan([s for s in meta["sweeps"] if s != "free" and (meta.get("heatmap", True) or s != "heat")])
    rows: List[Dict[str, Any]] = []
    t_start = time.perf_counter()
    for seed in meta["seeds"]:
        base = C.make_instance(meta["family"], seed=seed, **overrides)
        work = copy.deepcopy(base)
        variants: List[Tuple[str, str, Any, Any, float]] = [(sw, f"B{B}_C{C_}_P{P:g}", B, C_, P) for sw, B, C_, P in plan]
        fc = (meta.get("free_choice") or {}).get(str(seed))
        if fc:
            variants.append(("free_fixed", "free_fixed", fc["B"], fc["C"], E4.BASE_P))
        lib: Optional[ArcLibrary] = None
        for sweep, tag, B, C_, P in variants:
            _apply_sizes(work, B, C_, P, tag)
            if lib is None:
                lib, t_lib = C.build_library(work, C.pruning_for(work))
            o = old[(old["seed"] == seed) & (old["tag"] == tag)]
            ob = o[o["method"] == "baseline"]
            oi = o[o["method"] == "ILP"]
            oi0 = o[o["method"] == "ILP_rho0"]
            ilp_total, ilp_rho0_total = _first(oi, "total"), _first(oi0, "total")
            vrows, scheds = run_variants(work, lib, E4_VARIANTS)
            certs = certify(work, lib, {"baseline": scheds["baseline"]}) if do_certify else {}
            var = work.meta["variant"]
            q0_mean = sum(b.q0 for b in work.bikes) / len(work.bikes)
            for r in vrows:
                r.update({
                    "exp": "e4", "group": regime, "regime": regime, "name": f"{meta['family']}-seed{seed}-{tag}",
                    "seed": seed, "sweep": sweep, "tag": tag, "rho": work.rho,
                    "B_j": E4._uniform(var["B"]), "C_j": E4._uniform(var["C"]), "P_kw": E4._uniform(var["P_kw"]),
                    "B_sites": json.dumps(var["B"]), "C_sites": json.dumps(var["C"]),
                    "sum_B": sum(var["B"].values()), "sum_C": sum(var["C"].values()),
                    "q0_mean": q0_mean, "q0_mean_old": _first(ob, "q0_mean"),
                    "q0_match": _close(q0_mean, _first(ob, "q0_mean"), 1e-9),
                    "lib_build_s": t_lib, "n_arcs_old": _first(ob, "n_arcs"),
                    "n_arcs_match": _close(len(lib), _first(ob, "n_arcs"), 0),
                    "old_baseline_total": _first(ob, "total"), "old_baseline_n_unserved": _first(ob, "n_unserved"),
                    "old_baseline_operational": _first(ob, "operational"),
                    "legacy_matches_old": _close(r["total"], _first(ob, "total")) if r["variant"] == "baseline_legacy" else None,
                    "ilp_total": ilp_total, "ilp_operational": _first(oi, "operational"),
                    "ilp_status": _first(oi, "status"), "ilp_gap": _first(oi, "gap"),
                    "ilp_n_unserved": _first(oi, "n_unserved"), "ilp_mip_start_accepted_old": _first(oi, "mip_start_accepted"),
                    "ilp_mip_start_from_old": _first(oi, "mip_start_from"),
                    "ilp_rho0_total": ilp_rho0_total, "ilp_rho0_n_unserved": _first(oi0, "n_unserved"),
                    "ilp_rho0_mip_start_accepted_old": _first(oi0, "mip_start_accepted"),
                })
                r.update(certs.get(r["variant"], {}))
                _attach_gaps(r, ilp_total, ilp_rho0_total)
            rows.extend(vrows)
            b = vrows[0]
            _log(f"e4 {regime} seed {seed} {tag:<12}: v2 {b['total']:8.2f} (unserved {b['n_unserved']}) legacy "
                 f"{vrows[1]['total']:8.2f} old {C.fmt(_first(ob, 'total'), 2)} ilp {C.fmt(ilp_total, 2)} "
                 f"cert {certs.get('baseline', {}).get('cert_written')}/{certs.get('baseline', {}).get('cert_rho0')}/"
                 f"{certs.get('baseline', {}).get('cert_relaxed')} arcs {b['n_arcs_match']} legacy==old "
                 f"{vrows[1]['legacy_matches_old']} [{(time.perf_counter() - t_start) / 60:.1f} min]")
            C.write_csv(rows, os.path.join(root, "results_v2.csv"))
    return C.write_csv(rows, os.path.join(root, "results_v2.csv"))


# ---------------------------------------------------------------------------
# reporting helpers
# ---------------------------------------------------------------------------
def _style(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontsize=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e5e5e2", linewidth=0.8)
    ax.set_axisbelow(True)


def _cert_summary(df: pd.DataFrame, variant: str = "baseline") -> str:
    """One-line acceptance summary of the fix-and-solve certificate for ``variant``."""
    b = df[df["variant"] == variant]
    if "cert_written" not in b.columns or b["cert_written"].isna().all():
        return f"`{variant}`: no certificate run."
    n = int(b["cert_written"].notna().sum())
    w = int((b["cert_written"] == True).sum())  # noqa: E712
    r0 = int((b["cert_rho0"] == True).sum()) if "cert_rho0" in b.columns else None  # noqa: E712
    rx = int((b["cert_relaxed"] == True).sum()) if "cert_relaxed" in b.columns else None  # noqa: E712
    agree = bool(((b["cert_written"] == True) == b["accept_written_by_check"]).all())  # noqa: E712
    return (f"`{variant}` MIP start accepted (Gurobi fix-and-solve, all variables fixed, Threads {C.THREADS}, "
            f"TimeLimit {CERT_TIME_LIMIT:.0f} s): written model {w}/{n}, rho = 0 only {r0}/{n}, fully relaxed "
            f"end targets (rho = 0, R_end = 0) {rx}/{n}; certificate agrees with `evaluate.check` on every run: {agree}.")


def _anomalies_common(df: pd.DataFrame, exp: str) -> List[str]:
    out: List[str] = []
    bad_arcs = df[df["n_arcs_match"] == False]  # noqa: E712
    if len(bad_arcs):
        out.append(f"{exp}: n_arcs differs from the old results on {bad_arcs['name'].nunique()} instance(s): "
                   f"{sorted(bad_arcs['name'].unique())[:6]}")
    leg = df[df["legacy_matches_old"] == False]  # noqa: E712
    if len(leg):
        out.append(f"{exp}: the legacy variant does NOT reproduce the old baseline total on "
                   f"{len(leg)} run(s): {leg[['name', 'variant', 'total', 'old_baseline_total']].head(6).to_dict('records')}")
    if "cert_written" in df.columns:
        c = df[df["cert_written"].notna()]
        dis = c[(c["cert_written"] == True) != c["accept_written_by_check"]]  # noqa: E712
        if len(dis):
            out.append(f"{exp}: Gurobi certificate and evaluate.check disagree on {len(dis)} run(s)")
        objs = c[(c["cert_written"] == True) & c["cert_written_obj"].notna()]  # noqa: E712
        off = objs[(objs["cert_written_obj"] - objs["total"]).abs() > 1e-5]
        if len(off):
            out.append(f"{exp}: certified objective differs from evaluate.cost on {len(off)} run(s)")
    bl = df[df["variant"] == "baseline"]
    better = bl[(bl["ilp_total"].notna()) & (bl["total"] < bl["ilp_total"] - 1e-6)]
    for _, r in better.iterrows():
        st = r.get("ilp_status", r.get("ilp_free_status"))
        fam = r["families"]
        if r.get("cert_written") is True and st == "OPTIMAL":
            out.append(f"{exp} {r['name']}: SEVERE -- new baseline {r['total']:.3f} is feasible for the written model "
                       f"yet below the OPTIMAL ILP {r['ilp_total']:.3f}")
        else:
            out.append(f"{exp} {r['name']}: new baseline {r['total']:.3f} < ILP {r['ilp_total']:.3f} "
                       f"(ILP status {st}; baseline families {fam}; cert written {r.get('cert_written')}) -- "
                       "legitimate when the ILP hit its time limit or the baseline violates (17)/(18)")
    return out


def _interpretation(folder: str) -> List[str]:
    """Markdown lines of ``INTERPRETATION_v2.md`` in ``folder`` (written by hand after
    reading the numbers; embedded into ``RESULTS_v2.md`` when present)."""
    path = os.path.join(folder, "INTERPRETATION_v2.md")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return ["## Interpretation", "", fh.read().rstrip(), ""]


def _mean_table(df: pd.DataFrame, by: List[str], cols: List[str]) -> pd.DataFrame:
    g = df.groupby(by)[cols].mean().reset_index()
    g["n"] = df.groupby(by)["seed"].nunique().values
    return g


# ---------------------------------------------------------------------------
# E2 report
# ---------------------------------------------------------------------------
def _paired_gap(df: pd.DataFrame, variant: str, ilp_col: str) -> pd.DataFrame:
    b = df[df["variant"] == variant].copy()
    b = b[b[ilp_col].notna()]
    b["rel_impr"] = 100.0 * (b["total"] - b[ilp_col]) / b["total"]
    b["abs_gain"] = b["total"] - b[ilp_col]
    b["rel_impr_ex_setup"] = 100.0 * b["abs_gain"] / (b["total"] - b["C_setup"])
    return b


def e2_improvement_table(df: pd.DataFrame) -> pd.DataFrame:
    """Headline table of E2: mean ``100 (baseline - ILP) / baseline`` with 95 % t-CI
    over seeds per demand level (and pooled) for every baseline variant against the
    written-model ILP and, for the default variant, against the rho = 0 ILP."""
    pairs = [(f"ILP (rho=0.5) vs {v}", v, "ilp_total") for v in E2_VARIANTS]
    pairs.insert(1, ("ILP (rho=0) vs baseline", "baseline", "ilp_rho0_total"))
    recs = []
    for label, v, col in pairs:
        p = _paired_gap(df, v, col)
        for mult in sorted(DEMAND) + ["all"]:
            sub = p if mult == "all" else p[p["demand_mult"] == mult]
            m, hw, n = ci95(sub["rel_impr"].tolist())
            ma, _, _ = ci95(sub["abs_gain"].tolist())
            mx, hx, _ = ci95(sub["rel_impr_ex_setup"].tolist())
            recs.append({"comparison": label, "demand_mult": mult, "n": n, "gap_vs_baseline_mean_pct": m,
                         "ci95_pct": hw, "lo_pct": m - hw, "hi_pct": m + hw, "abs_gain_mean": ma,
                         "gap_ex_setup_mean_pct": mx, "gap_ex_setup_ci95_pct": hx,
                         "baseline_mean": sub["total"].mean(), "ilp_mean": sub[col].mean()})
    return pd.DataFrame(recs)


def e2_component_means(df: pd.DataFrame) -> pd.DataFrame:
    """Seed means of cost (26) and components (27)-(32) per demand level for every
    baseline variant, the old baseline and the two ILPs."""
    recs = []
    for mult in sorted(DEMAND):
        d = df[df["demand_mult"] == mult]
        for v in E2_VARIANTS:
            b = d[d["variant"] == v]
            recs.append({"demand_mult": mult, "method": v, "total": b["total"].mean(),
                         **{c: b[c].mean() for c in COMPONENTS}, "n_unserved": b["n_unserved"].mean(),
                         "n_swaps": b["n_swaps"].mean(), "bike_km": b["bike_km"].mean(),
                         "jit_dispatches": b["jit_dispatches"].mean(), "reach_refusals": b["reach_refusals"].mean()})
        b = d[d["variant"] == "baseline"]
        recs.append({"demand_mult": mult, "method": "baseline_old (results.csv)", "total": b["old_baseline_total"].mean(),
                     "n_unserved": b["old_baseline_n_unserved"].mean(), "C_travel": b["old_baseline_C_travel"].mean()})
        recs.append({"demand_mult": mult, "method": "ilp (rho=0.5)", "total": b["ilp_total"].mean(),
                     "n_unserved": b["ilp_n_unserved"].mean()})
        recs.append({"demand_mult": mult, "method": "ilp_rho0", "total": b["ilp_rho0_total"].mean()})
    return pd.DataFrame(recs)


def e2_gap_decomposition(df: pd.DataFrame, old: pd.DataFrame, variant: str, ilp_method: str) -> pd.DataFrame:
    """Baseline-variant minus ILP by component (27)-(32), seed means per demand level."""
    recs = []
    b = df[df["variant"] == variant]
    for mult in sorted(DEMAND) + ["all"]:
        bb = b if mult == "all" else b[b["demand_mult"] == mult]
        names = set(bb["name"]) if ilp_method == "ilp" else {n + "-rho0" for n in bb["name"]}
        ii = old[(old["method"] == ilp_method) & old["name"].isin(names)]
        rec: Dict[str, Any] = {"demand_mult": "all" if mult == "all" else f"x{mult:g}",
                               "baseline_total": bb["total"].mean(), "ilp_total": ii["total"].mean()}
        rec["gap_total"] = rec["baseline_total"] - rec["ilp_total"]
        for c in COMPONENTS:
            rec[f"d_{c}"] = bb[c].mean() - ii[c].mean()
        for c in ("unserved", "response", "lateness", "C_travel", "C_elec"):
            rec[f"{c}_share_pct"] = 100.0 * rec[f"d_{c}"] / rec["gap_total"] if abs(rec["gap_total"]) > 1e-9 else None
        rec["gap_vs_baseline_pct"] = 100.0 * rec["gap_total"] / rec["baseline_total"]
        recs.append(rec)
    return pd.DataFrame(recs)


def plot_e2_components(means: pd.DataFrame, path: str) -> str:
    """Stacked (27)-(32) bars per demand level for the baseline variants and the ILP."""
    methods = E2_VARIANTS + ["ilp (rho=0.5)"]
    comp_colors = ["#9a9a96", "#eda100", "#2a78d6", "#e34948", "#1baf7a", "#e87ba4", "#4a3aa7"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True, constrained_layout=True)
    old = pd.read_csv(os.path.join(OUT_E2, "results.csv"))
    for ax, mult in zip(axes, sorted(DEMAND)):
        d = means[means["demand_mult"] == mult].set_index("method")
        oi = old[(old["method"] == "ilp") & (old["demand_mult"] == mult)]
        xs = list(range(len(methods)))
        bottoms = [0.0] * len(methods)
        for ci, comp in enumerate(COMPONENTS):
            vals = []
            for m in methods:
                if m == "ilp (rho=0.5)":
                    vals.append(float(oi[comp].mean()))
                else:
                    vals.append(float(d.loc[m, comp]) if m in d.index else 0.0)
            ax.bar(xs, vals, 0.72, bottom=bottoms, color=comp_colors[ci], label=comp if mult == sorted(DEMAND)[0] else None,
                   edgecolor="#fcfcfb", linewidth=1)
            bottoms = [b + v for b, v in zip(bottoms, vals)]
        for x, b in zip(xs, bottoms):
            ax.text(x, b + 8, f"{b:.0f}", ha="center", va="bottom", fontsize=7.5, color="#52514e")
        ax.set_xticks(xs)
        ax.set_xticklabels([m.replace("baseline_", "b_").replace("baseline", "b_v2").replace("ilp (rho=0.5)", "ILP")
                            for m in methods], rotation=25, ha="right", fontsize=8)
        _style(ax, "", "cost (26), toy units" if mult == sorted(DEMAND)[0] else "", f"demand x{mult:g} (|I| = {DEMAND[mult]})")
    axes[0].legend(frameon=False, fontsize=8, ncol=2)
    fig.suptitle("E2 v2: cost components (27)-(32), seed means; b_v2 = fixed baseline, b_legacy = old behaviour", x=0.01,
                 ha="left", fontsize=11)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_e2_improvement(imp: pd.DataFrame, path: str) -> str:
    """Mean headline gap (baseline - ILP)/baseline with 95 % CI per demand level and
    baseline variant (dot + error bar)."""
    comps = [c for c in imp["comparison"].unique() if "rho=0)" not in c]
    fig, ax = plt.subplots(figsize=(9, 4.2), constrained_layout=True)
    mults = sorted(DEMAND) + ["all"]
    width = 0.8 / len(comps)
    for ci, comp in enumerate(comps):
        sub = imp[imp["comparison"] == comp].set_index("demand_mult")
        variant = comp.split(" vs ")[1]
        xs = [i + ci * width - 0.4 + width / 2 for i in range(len(mults))]
        ys = [float(sub.loc[m, "gap_vs_baseline_mean_pct"]) for m in mults]
        es = [float(sub.loc[m, "ci95_pct"]) if not math.isnan(float(sub.loc[m, "ci95_pct"])) else 0.0 for m in mults]
        ax.errorbar(xs, ys, yerr=es, fmt="o", color=PALETTE.get(variant, "#52514e"), markersize=6, capsize=3,
                    linewidth=1.4, label=LABEL.get(variant, variant))
    ax.axhline(0, color="#9a9a96", linewidth=0.8)
    ax.set_xticks(range(len(mults)))
    ax.set_xticklabels([f"x{m:g}" if m != "all" else "all" for m in mults])
    _style(ax, "demand multiplier", "100 (baseline - ILP) / baseline  [%]",
           "E2 v2: ILP (rho = 0.5) gain over each baseline variant, mean over seeds with 95 % t-CI")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def report_e2(df: pd.DataFrame) -> Tuple[str, List[str], Dict[str, Any]]:
    """``outputs/e2_coord/baseline_rerun_v2/RESULTS_v2.md`` + ``_v2`` figures; returns ``(path, anomalies, headline)``."""
    old = pd.read_csv(os.path.join(OUT_E2, "results.csv"))
    imp = e2_improvement_table(df)
    means = e2_component_means(df)
    dec = e2_gap_decomposition(df, old, "baseline", "ilp")
    dec0 = e2_gap_decomposition(df, old, "baseline", "ilp_rho0")
    dec_leg = e2_gap_decomposition(df, old, "baseline_legacy", "ilp")
    imp.to_csv(os.path.join(C.ensure_dir(OUT_E2_V2), "improvement_v2.csv"), index=False)
    dec.to_csv(os.path.join(C.ensure_dir(OUT_E2_V2), "gap_decomposition_rho05_v2.csv"), index=False)
    dec0.to_csv(os.path.join(C.ensure_dir(OUT_E2_V2), "gap_decomposition_rho0_v2.csv"), index=False)
    figs = [plot_e2_components(means, os.path.join(C.ensure_dir(OUT_E2_V2), "cost_components_v2.png")),
            plot_e2_improvement(imp, os.path.join(C.ensure_dir(OUT_E2_V2), "improvement_vs_demand_v2.png"))]
    anomalies = _anomalies_common(df, "e2")
    b = df[df["variant"] == "baseline"].sort_values(["demand_mult", "seed"])
    leg = df[df["variant"] == "baseline_legacy"].set_index("name")
    res = df[df["variant"] == "baseline_reserve"].set_index("name")
    inf = df[df["variant"] == "baseline_informed"].set_index("name")
    reo = df[df["variant"] == "baseline_reorder"].set_index("name")
    per = []
    for _, r in b.iterrows():
        n = r["name"]
        per.append({
            "name": n, "old_baseline": r["old_baseline_total"], "legacy_v2": leg.loc[n, "total"],
            "legacy==old": leg.loc[n, "legacy_matches_old"], "baseline_v2": r["total"],
            "reserve": res.loc[n, "total"], "informed": inf.loc[n, "total"], "reorder": reo.loc[n, "total"],
            "ilp": r["ilp_total"], "ilp_status": r["ilp_status"], "ilp_rho0": r["ilp_rho0_total"],
            "gap_v2_pct": r["gap_vs_baseline_pct"], "gap_legacy_pct": leg.loc[n, "gap_vs_baseline_pct"],
            "gap_v2_rho0_pct": r["gap_rho0_vs_baseline_pct"],
            "unserved_old/v2/ilp": f"{int(r['old_baseline_n_unserved'])}/{int(r['n_unserved'])}/{int(r['ilp_n_unserved'])}",
            "km_old/v2": f"{r['old_baseline_C_travel']:.1f}/{r['bike_km']:.1f}", "jit": r["jit_dispatches"],
            "reach_ref": r["reach_refusals"], "families_v2": r["families"],
            "cert_written": r.get("cert_written"), "cert_rho0": r.get("cert_rho0"), "cert_relaxed": r.get("cert_relaxed"),
            "cert_reserve_written": res.loc[n, "cert_written"] if "cert_written" in res.columns else None,
            "cert_reorder_written": reo.loc[n, "cert_written"] if "cert_written" in reo.columns else None,
            "old_start_accepted": r["ilp_mip_start_accepted_old"],
        })
    per_df = pd.DataFrame(per)
    all_imp = imp[(imp["demand_mult"] == "all")].set_index("comparison")
    hl = {
        "gap_v2_pct": float(all_imp.loc["ILP (rho=0.5) vs baseline", "gap_vs_baseline_mean_pct"]),
        "gap_v2_ci": float(all_imp.loc["ILP (rho=0.5) vs baseline", "ci95_pct"]),
        "gap_legacy_pct": float(all_imp.loc["ILP (rho=0.5) vs baseline_legacy", "gap_vs_baseline_mean_pct"]),
        "gap_legacy_ci": float(all_imp.loc["ILP (rho=0.5) vs baseline_legacy", "ci95_pct"]),
        "gap_v2_rho0_pct": float(all_imp.loc["ILP (rho=0) vs baseline", "gap_vs_baseline_mean_pct"]),
        "gap_reserve_pct": float(all_imp.loc["ILP (rho=0.5) vs baseline_reserve", "gap_vs_baseline_mean_pct"]),
        "mean_v2": float(b["total"].mean()), "mean_legacy": float(b["old_baseline_total"].mean()),
        "mean_reserve": float(res["total"].mean()), "mean_ilp": float(b["ilp_total"].mean()),
        "unserved_v2": float(b["n_unserved"].mean()), "unserved_legacy": float(b["old_baseline_n_unserved"].mean()),
        "unserved_ilp": float(b["ilp_n_unserved"].mean()),
        "km_v2": float(b["bike_km"].mean()), "km_legacy": float(b["old_baseline_C_travel"].mean()),
        "v2_le_legacy": int((b["total"] <= b["old_baseline_total"] + 1e-9).sum()), "n": len(b),
        "cert_written": int((b["cert_written"] == True).sum()) if "cert_written" in b.columns else None,  # noqa: E712
        "cert_relaxed": int((b["cert_relaxed"] == True).sum()) if "cert_relaxed" in b.columns else None,  # noqa: E712
        "cert_rho0": int((b["cert_rho0"] == True).sum()) if "cert_rho0" in b.columns else None,  # noqa: E712
        "old_accepted": int((b["ilp_mip_start_accepted_old"] == True).sum()),  # noqa: E712
        "legacy_all_match": bool(leg["legacy_matches_old"].all()), "arcs_all_match": bool(df["n_arcs_match"].all()),
    }
    md: List[str] = ["# E2 v2 -- fixed baseline re-run (ILP rows unchanged)", ""]
    md.append(f"Same 15 saved instances (`instances/*.json`, |K| = 10, |I| in {{22, 30, 45}}, H = 24, L = 12, 3 co-located sites "
              f"B_j = 4, C_j = 3, 12 hourly shuttles, seeds 0-4), same arc library (pruning tau_max 4, start_slack 6, "
              f"reachable = True; n_arcs equal to the old `results.csv` on every instance: {hl['arcs_all_match']}). "
              f"The ILP rows (`ilp` rho = 0.5, `ilp_rho0` rho = 0 with R_end = 1 kept) are re-used from `results.csv` "
              f"(objective, constraints and arc defaults untouched by the baseline fixes); only the baseline side is re-run. "
              f"Baseline variants: `baseline` (fixed policy: JIT dispatch F1 + dead-zone rule F2), `baseline_legacy` "
              f"(old behaviour; reproduces the old `baseline` rows exactly on every instance: {hl['legacy_all_match']}), "
              f"`baseline_reserve` (F3: end-reserve window and late-threshold window W = max sigma_j + 3 = 4 slots), "
              f"`baseline_informed` (F6: stock-aware site choice + late-threshold window), `baseline_reorder` "
              f"(REORDER_POINT transfers on the shuttles). {GAP_NOTE}")
    md.append("")
    md.append("## Headline")
    md.append("")
    md.append(f"**ILP (rho = 0.5) vs the fixed baseline: {hl['gap_v2_pct']:.1f} % (95 % CI +/- {hl['gap_v2_ci']:.1f}, n = {hl['n']})** "
              f"of the baseline cost is saved by coordination (was {hl['gap_legacy_pct']:.1f} % +/- {hl['gap_legacy_ci']:.1f} against the "
              f"old baseline; against `baseline_reserve` {hl['gap_reserve_pct']:.1f} %; with the rho = 0 ILP {hl['gap_v2_rho0_pct']:.1f} %). "
              f"Mean baseline cost {hl['mean_legacy']:.1f} -> {hl['mean_v2']:.1f} (reserve {hl['mean_reserve']:.1f}) against the ILP "
              f"mean {hl['mean_ilp']:.1f}; mean unserved {hl['unserved_legacy']:.2f} -> {hl['unserved_v2']:.2f} (ILP {hl['unserved_ilp']:.2f}); "
              f"mean bike km {hl['km_legacy']:.1f} -> {hl['km_v2']:.1f}; the fixed baseline is at most as expensive as the old one on "
              f"{hl['v2_le_legacy']} of {hl['n']} instances (the JIT rule changes the greedy assignment, so single instances swing both ways).")
    md.append("")
    md.append(f"MIP start of the fixed baseline: accepted by the written model on {hl['cert_written']} / {hl['n']} instances "
              f"(old baseline: {hl['old_accepted']} / {hl['n']}), by the rho = 0 model on {hl['cert_rho0']} / {hl['n']} and under the "
              f"fully relaxed end targets (rho = 0, R_end = 0) on {hl['cert_relaxed']} / {hl['n']} (Gurobi fix-and-solve certificate; "
              f"the free ILP was not re-solved). {_cert_summary(df, 'baseline')}")
    md.append("")
    md.append("## Per instance: new baseline vs old baseline vs ILP")
    md.append("")
    md.append(C.markdown_table(per_df, None, 2))
    md.append("")
    md.append("`legacy_v2` = the fixed code run with `jit_dispatch = False, swap_on_reach_refusal = False` (must equal `old_baseline`); "
              "`unserved_old/v2/ilp` = unserved orders; `km_old/v2` = bike km (C_travel at kappa = 1); `jit` = just-in-time dispatches, "
              "`reach_ref` = reach-only refusals of the new rules; `cert_*` = Gurobi acceptance of the new baseline start "
              "(written model / (18) removed / (17)+(18) removed); `old_start_accepted` = acceptance of the old baseline in the original run.")
    md.append("")
    md.append("## Headline gap per demand level: mean 100 (baseline - ILP) / baseline with 95 % t-CI over seeds")
    md.append("")
    md.append(C.markdown_table(imp, None, 2))
    md.append("")
    md.append("## Cost (26) and components (27)-(32): seed means per demand level")
    md.append("")
    md.append(C.markdown_table(means, None, 2))
    md.append("")
    md.append("## Gap decomposition baseline_v2 - ILP (rho = 0.5) by component")
    md.append("")
    md.append(C.markdown_table(dec, None, 2))
    md.append("")
    md.append("Same against the rho = 0 ILP:")
    md.append("")
    md.append(C.markdown_table(dec0, None, 2))
    md.append("")
    md.append("Old behaviour (baseline_legacy) - ILP (rho = 0.5), for reference:")
    md.append("")
    md.append(C.markdown_table(dec_leg, None, 2))
    md.append("")
    md.append("## Figures")
    md.append("")
    md.extend(f"- `{os.path.basename(f)}`" for f in figs)
    md.append("")
    md.append("## Anomalies")
    md.append("")
    md.extend(f"- {a}" for a in anomalies) if anomalies else md.append("- none")
    md.append("")
    md.extend(_interpretation(OUT_E2_V2))
    path = os.path.join(C.ensure_dir(OUT_E2_V2), "RESULTS_v2.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path, anomalies, hl


# ---------------------------------------------------------------------------
# E3 report
# ---------------------------------------------------------------------------
def plot_e3_layouts(df: pd.DataFrame, path: str) -> str:
    """Mean total cost per layout: ILP (free / no transfers) and the baseline variants."""
    d = df[df["group"] == "main"]
    layouts = ["colocated", "separated_1hub", "separated_2hubs"]
    series = [("ILP transfers free", lambda g: g[g["variant"] == "baseline"]["ilp_free_total"].mean(), PALETTE["ILP"], ""),
              ("ILP no transfers", lambda g: g[g["variant"] == "baseline"]["ilp_none_total"].mean(), PALETTE["ILP"], "//"),
              ("baseline v2 NONE", lambda g: g[g["variant"] == "baseline"]["total"].mean(), PALETTE["baseline"], ""),
              ("baseline v2 REORDER_POINT", lambda g: g[g["variant"] == "baseline_reorder"]["total"].mean(), PALETTE["baseline_reorder"], ""),
              ("baseline legacy NONE", lambda g: g[g["variant"] == "baseline_legacy"]["total"].mean(), PALETTE["baseline_legacy"], ""),
              ("baseline legacy REORDER_POINT", lambda g: g[g["variant"] == "baseline_reorder_legacy"]["total"].mean(), PALETTE["baseline_reorder_legacy"], ""),
              ("baseline_reserve NONE", lambda g: g[g["variant"] == "baseline_reserve"]["total"].mean(), PALETTE["baseline_reserve"], "")]
    fig, ax = plt.subplots(figsize=(11, 4.4), constrained_layout=True)
    width = 0.8 / len(series)
    for si, (label, fn, color, hatch) in enumerate(series):
        xs = [i + si * width - 0.4 + width / 2 for i in range(len(layouts))]
        ys = [fn(d[d["layout"] == lay]) for lay in layouts]
        ax.bar(xs, ys, width * 0.92, color=color, hatch=hatch, edgecolor="#fcfcfb", linewidth=1, label=label)
        for x, y in zip(xs, ys):
            ax.text(x, y + 8, f"{y:.0f}", ha="center", va="bottom", fontsize=7, color="#52514e", rotation=90)
    ax.set_xticks(range(len(layouts)))
    ax.set_xticklabels(["(a) co-located", "(b) 3 sites + 1 hub", "(c) 3 sites + 2 hubs"])
    _style(ax, "", "total cost (26), seed mean", "E3 v2: total cost per layout (ILP rows from the original run; baselines re-run)")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def report_e3(df: pd.DataFrame) -> Tuple[str, List[str], Dict[str, Any]]:
    """``outputs/e3/baseline_rerun_v2/RESULTS_v2.md`` + ``fig_cost_by_layout_v2.png``."""
    figs = [plot_e3_layouts(df, os.path.join(C.ensure_dir(OUT_E3_V2), "fig_cost_by_layout_v2.png"))]
    anomalies = _anomalies_common(df, "e3")
    main = df[df["group"] == "main"]
    cols = ["total", "C_travel", "C_elec", "unserved", "response", "lateness", "C_reb", "n_unserved", "n_swaps",
            "transfers_used", "batteries_moved", "end_full_total", "viol_17_local_sum", "viol_18_global",
            "gap_vs_baseline_pct", "gap_vs_ilp_free_pct"]
    means = _mean_table(main, ["layout", "variant"], cols)
    ilp_means = _mean_table(main[main["variant"] == "baseline"], ["layout"],
                            ["ilp_free_total", "ilp_none_total", "ilp_free_n_unserved", "ilp_none_n_unserved", "old_baseline_total"])
    per_cols = ["layout", "seed", "variant", "total", "old_baseline_total", "legacy_matches_old", "n_unserved", "transfers_used",
                "batteries_moved", "C_reb", "families", "ilp_total", "ilp_free_total", "ilp_none_total", "gap_vs_baseline_pct",
                "gap_vs_ilp_free_pct", "cert_written", "cert_rho0", "cert_relaxed", "ilp_free_mip_start_accepted_old",
                "ilp_none_mip_start_accepted_old", "jit_dispatches", "reach_refusals"]
    per_cols = [c for c in per_cols if c in df.columns]
    b = main[main["variant"] == "baseline"]
    r = main[main["variant"] == "baseline_reorder"]
    hl = {
        "none_v2": float(b["total"].mean()), "none_old": float(b["old_baseline_total"].mean()),
        "reorder_v2": float(r["total"].mean()), "reorder_old": float(r["old_baseline_total"].mean()),
        "ilp_free": float(b["ilp_free_total"].mean()), "ilp_none": float(b["ilp_none_total"].mean()),
        "gap_none_v2": float(b["gap_vs_baseline_pct"].mean()),
        "gap_none_legacy": float(main[main["variant"] == "baseline_legacy"]["gap_vs_baseline_pct"].mean()),
        "gap_reorder_v2": float(r["gap_vs_baseline_pct"].mean()),
        "gap_reorder_legacy": float(main[main["variant"] == "baseline_reorder_legacy"]["gap_vs_baseline_pct"].mean()),
        "cert_written_none": int((b["cert_written"] == True).sum()) if "cert_written" in b.columns else None,  # noqa: E712
        "cert_relaxed_none": int((b["cert_relaxed"] == True).sum()) if "cert_relaxed" in b.columns else None,  # noqa: E712
        "cert_written_reorder": int((r["cert_written"] == True).sum()) if "cert_written" in r.columns else None,  # noqa: E712
        "cert_relaxed_reorder": int((r["cert_relaxed"] == True).sum()) if "cert_relaxed" in r.columns else None,  # noqa: E712
        "n": len(b), "legacy_all_match": bool(df["legacy_matches_old"].dropna().all()), "arcs_all_match": bool(df["n_arcs_match"].all()),
        "unserved_none_v2": float(b["n_unserved"].mean()), "unserved_none_old": float(b["old_baseline_n_unserved"].mean()),
        "unserved_reorder_v2": float(r["n_unserved"].mean()), "unserved_reorder_old": float(r["old_baseline_n_unserved"].mean()),
    }
    md: List[str] = ["# E3 v2 -- fixed baseline re-run (ILP rows unchanged)", ""]
    md.append(f"Same 9 saved layout instances (`instances/*.json`: family large, sum B = 9, sum C = 9, q0 ~ U{{0.3L..0.6L}}, seeds 0-2) "
              f"and the two relaxed-end-target instances of `relaxed_end_targets/` (seed 0, rho = 0, R_end = 0); same arc library "
              f"(n_arcs equal to the old results on every instance: {hl['arcs_all_match']}). ILP rows (transfers free / `no_transfers`) "
              f"from the old `results.csv`. Baseline families: NONE (`baseline`, `baseline_legacy`, `baseline_reserve`, `baseline_informed`) "
              f"and REORDER_POINT (`baseline_reorder`, `baseline_reorder_legacy`); the legacy variants reproduce the old rows exactly: "
              f"{hl['legacy_all_match']}. `ilp_total` = the ILP of the same transfer switch (free for REORDER_POINT, `no_transfers` for NONE); "
              f"`gap_vs_ilp_free_pct` compares every variant with the transfers-free ILP. {GAP_NOTE}")
    md.append("")
    md.append("## Headline")
    md.append("")
    md.append(f"Seed-and-layout means: baseline NONE {hl['none_old']:.1f} -> {hl['none_v2']:.1f} (unserved {hl['unserved_none_old']:.2f} -> "
              f"{hl['unserved_none_v2']:.2f}) against the no-transfer ILP {hl['ilp_none']:.1f}: headline gap {hl['gap_none_legacy']:.1f} % -> "
              f"{hl['gap_none_v2']:.1f} %; baseline REORDER_POINT {hl['reorder_old']:.1f} -> {hl['reorder_v2']:.1f} (unserved "
              f"{hl['unserved_reorder_old']:.2f} -> {hl['unserved_reorder_v2']:.2f}) against the transfers-free ILP {hl['ilp_free']:.1f}: gap "
              f"{hl['gap_reorder_legacy']:.1f} % -> {hl['gap_reorder_v2']:.1f} %. New NONE start accepted by the written model on "
              f"{hl['cert_written_none']} / {hl['n']} runs and under the fully relaxed end targets on {hl['cert_relaxed_none']} / {hl['n']}; "
              f"REORDER_POINT start {hl['cert_written_reorder']} / {hl['n']} and {hl['cert_relaxed_reorder']} / {hl['n']}. The E3 headline "
              f"(ILP vs ILP: value of transfers, cost of separation) is unaffected.")
    md.append("")
    md.append(_cert_summary(df[df["group"] == "main"], "baseline"))
    md.append("")
    md.append(_cert_summary(df[df["group"] == "main"], "baseline_reorder"))
    md.append("")
    md.append("## Seed means per layout and variant (group main)")
    md.append("")
    md.append(C.markdown_table(means, None, 2))
    md.append("")
    md.append("ILP references (old rows) and old baseline NONE per layout:")
    md.append("")
    md.append(C.markdown_table(ilp_means, None, 2))
    md.append("")
    md.append("## Per run (both groups)")
    md.append("")
    md.append(C.markdown_table(df.sort_values(["group", "layout", "seed", "variant"]), ["group"] + per_cols, 2))
    md.append("")
    md.append("## Figures")
    md.append("")
    md.extend(f"- `{os.path.basename(f)}`" for f in figs)
    md.append("")
    md.append("## Anomalies")
    md.append("")
    md.extend(f"- {a}" for a in anomalies) if anomalies else md.append("- none")
    md.append("")
    md.extend(_interpretation(OUT_E3_V2))
    path = os.path.join(C.ensure_dir(OUT_E3_V2), "RESULTS_v2.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path, anomalies, hl


# ---------------------------------------------------------------------------
# E4 report (both regimes)
# ---------------------------------------------------------------------------
def _e4_combined(df: pd.DataFrame, old: pd.DataFrame, regime: str) -> pd.DataFrame:
    """Long frame with one row per (seed, tag, method): the new baseline variants plus
    the old ``ILP`` / ``ILP_rho0`` rows (columns needed for the sweep summaries)."""
    keep = ["seed", "sweep", "tag", "B_j", "C_j", "P_kw", "total", "operational", "n_unserved", "C_elec",
            "C_travel", "unserved", "response", "lateness", "C_setup", "n_swaps", "end_full_total"]
    new = df[keep + ["variant"]].rename(columns={"variant": "method"})
    o = old[old["method"].isin(["ILP", "ILP_rho0"])][keep + ["method"]].copy()
    comb = pd.concat([new, o], ignore_index=True)
    comb["regime"] = regime
    return comb


def e4_sweep_summary(comb: pd.DataFrame, sweep: str) -> pd.DataFrame:
    """Per-size seed means (total, operational, unserved, electricity, swaps) per
    method on the one-at-a-time line of ``sweep`` and the finite-difference marginal
    values per unit added at one site (as ``e4_sizing.summarise``)."""
    col, fixed = E4.SWEEP_SPEC[sweep]
    sub = comb[~comb["sweep"].isin(["free", "free_fixed"])]
    for k, v in fixed.items():
        sub = sub[sub[k] == v]
    sub = sub[sub[col].notna()]
    if sub.empty:
        return pd.DataFrame()
    g = sub.groupby(["method", col]).agg(total_mean=("total", "mean"), total_min=("total", "min"), total_max=("total", "max"),
                                         operational_mean=("operational", "mean"), n_unserved_mean=("n_unserved", "mean"),
                                         n_unserved_max=("n_unserved", "max"), C_elec_mean=("C_elec", "mean"),
                                         lateness_mean=("lateness", "mean"), n_swaps_mean=("n_swaps", "mean"),
                                         end_full_total_mean=("end_full_total", "mean"), n_seeds=("seed", "nunique")).reset_index()
    for method in g["method"].unique():
        m = g[g["method"] == method].sort_values(col)
        sizes = list(m[col])
        for cost_col in ("operational", "total"):
            vals = list(m[f"{cost_col}_mean"])
            mv: List[Optional[float]] = [None] * len(sizes)
            for i in range(len(sizes) - 1):
                step = (sizes[i + 1] - sizes[i]) * E4.N_SITES
                mv[i] = (vals[i] - vals[i + 1]) / step if step else None
            g.loc[m.index, f"marginal_{cost_col}_per_unit"] = mv
    order = {"ILP": 0, "ILP_rho0": 1, "baseline": 2, "baseline_legacy": 3, "baseline_reserve": 4, "baseline_informed": 5}
    g["_o"] = g["method"].map(order)
    return g.sort_values(["_o", col]).drop(columns="_o")


def e4_gap_table(comb: pd.DataFrame, sweep: str) -> pd.DataFrame:
    """Gap of each baseline variant to ``ILP`` (and of the default to ``ILP_rho0``) per
    size of ``sweep``: seed-mean totals, both gap conventions, component differences."""
    col, fixed = E4.SWEEP_SPEC[sweep]
    sub = comb[~comb["sweep"].isin(["free", "free_fixed"])]
    for k, v in fixed.items():
        sub = sub[sub[k] == v]
    recs = []
    for size in sorted(sub[col].dropna().unique()):
        at = sub[sub[col] == size]
        for variant in ("baseline", "baseline_legacy", "baseline_reserve"):
            bl = at[at["method"] == variant]
            for ilp_method in ("ILP", "ILP_rho0"):
                il = at[at["method"] == ilp_method]
                if bl.empty or il.empty or (ilp_method == "ILP_rho0" and variant != "baseline"):
                    continue
                rec: Dict[str, Any] = {"sweep": sweep, "size": size, "baseline": variant, "vs": ilp_method,
                                       "baseline_total": bl["total"].mean(), "ilp_total": il["total"].mean()}
                rec["gap_total"] = rec["baseline_total"] - rec["ilp_total"]
                rec.update(C.gap_definitions(rec["baseline_total"], rec["ilp_total"]))
                for comp in ("unserved", "response", "lateness", "C_travel", "C_elec"):
                    rec[f"d_{comp}"] = bl[comp].mean() - il[comp].mean()
                rec["unserved_share_of_gap"] = rec["d_unserved"] / rec["gap_total"] if abs(rec["gap_total"]) > 1e-9 else None
                rec["baseline_n_unserved"] = bl["n_unserved"].mean()
                rec["ilp_n_unserved"] = il["n_unserved"].mean()
                recs.append(rec)
    return pd.DataFrame(recs)


def e4_spares_to_match(comb: pd.DataFrame, summary_B: pd.DataFrame) -> List[Dict[str, Any]]:
    """'Extra spares the baseline needs to match the ILP service level': for the ILP
    service level (mean unserved) at B_ref in {2, default 4}, the smallest B_j of the
    sweep at which each baseline variant's mean unserved is <= that level (seed means),
    plus the per-seed version (smallest B_j per seed, max over seeds)."""
    out = []
    ilp = summary_B[summary_B["method"] == "ILP"].set_index("B_j")
    base_rows = comb[(comb["C_j"] == E4.BASE_C) & (comb["P_kw"] == E4.BASE_P) & ~comb["sweep"].isin(["free", "free_fixed"])]
    for B_ref in (2, E4.BASE_B):
        if B_ref not in ilp.index:
            continue
        level = float(ilp.loc[B_ref, "n_unserved_mean"])
        ilp_cost = float(ilp.loc[B_ref, "total_mean"])
        for variant in ("baseline", "baseline_legacy", "baseline_reserve"):
            m = summary_B[summary_B["method"] == variant].sort_values("B_j")
            hit = m[m["n_unserved_mean"] <= level + 1e-9]
            need = float(hit["B_j"].iloc[0]) if len(hit) else None
            # per seed: smallest B with unserved <= ILP's unserved at B_ref on the same seed
            per_seed = []
            for seed in sorted(base_rows["seed"].unique()):
                il_s = base_rows[(base_rows["method"] == "ILP") & (base_rows["seed"] == seed) & (base_rows["B_j"] == B_ref)]
                bl_s = base_rows[(base_rows["method"] == variant) & (base_rows["seed"] == seed)].sort_values("B_j")
                if il_s.empty or bl_s.empty:
                    continue
                ok = bl_s[bl_s["n_unserved"] <= float(il_s["n_unserved"].iloc[0]) + 1e-9]
                per_seed.append(float(ok["B_j"].iloc[0]) if len(ok) else math.inf)
            cost_hit = m[m["total_mean"] <= ilp_cost + 1e-9]
            out.append({"B_ref": B_ref, "ilp_unserved_at_B_ref": level, "ilp_total_at_B_ref": ilp_cost, "baseline": variant,
                        "min_B_j_matching_service_level (seed means)": need if need is not None else f"> {int(m['B_j'].max())} (not within sweep)",
                        "extra_spares_per_site": (need - B_ref) if need is not None else (
                            f"> {int(m['B_j'].max()) - B_ref}" if int(m["B_j"].max()) > B_ref else "not reached within the sweep"),
                        "per_seed_min_B_j": [("inf" if v == math.inf else int(v)) for v in per_seed],
                        "baseline_unserved_at_B_ref": float(m.set_index("B_j").loc[B_ref, "n_unserved_mean"]) if B_ref in set(m["B_j"]) else None,
                        "min_B_j_matching_ILP_total": float(cost_hit["B_j"].iloc[0]) if len(cost_hit) else "never (baseline never reaches the ILP cost)"})
    return out


def plot_e4_sweep(frames: Dict[str, pd.DataFrame], sweep: str, path: str) -> str:
    """Two regimes side by side: (top) mean total cost (26) vs size with min-max bands
    for the ILP and the fixed baseline, (bottom) mean unserved orders vs size."""
    col, fixed = E4.SWEEP_SPEC[sweep]
    regimes = [r for r in ("main", "stressed_lowq0") if r in frames]
    fig, axes = plt.subplots(2, len(regimes), figsize=(6.2 * len(regimes), 7.6), squeeze=False, constrained_layout=True)
    xlabel = {"B": "spare batteries per site B_j", "C": "chargers per site C_j", "P": "site power limit P_j [kW]"}[sweep]
    fixed_txt = ", ".join(f"{k.replace('_j', '_j').replace('P_kw', 'P_j')} = {v:g}" for k, v in fixed.items())
    for ci, regime in enumerate(regimes):
        s = e4_sweep_summary(frames[regime], sweep)
        ax, ax2 = axes[0][ci], axes[1][ci]
        for method in ("ILP", "ILP_rho0", "baseline", "baseline_legacy", "baseline_reserve"):
            m = s[s["method"] == method].sort_values(col)
            if m.empty:
                continue
            if method in ("ILP", "baseline"):
                ax.fill_between(m[col], m["total_min"], m["total_max"], color=PALETTE[method], alpha=0.12, linewidth=0)
            ax.plot(m[col], m["total_mean"], color=PALETTE[method], linestyle=LINESTYLE[method], linewidth=2, marker="o",
                    markersize=4.5, label=LABEL[method])
            ax2.plot(m[col], m["n_unserved_mean"], color=PALETTE[method], linestyle=LINESTYLE[method], linewidth=2, marker="o",
                     markersize=4.5, label=LABEL[method])
            ax.annotate(method.replace("baseline", "b"), (float(m[col].iloc[-1]), float(m["total_mean"].iloc[-1])),
                        xytext=(4, 0), textcoords="offset points", fontsize=7, color="#52514e", va="center")
        xt = sorted(s[col].unique())
        for a in (ax, ax2):
            a.set_xticks(xt)
            a.set_xticklabels([f"{x:g}" for x in xt])
        title = {"main": "main regime (q0 ~ U{0.4L..L})", "stressed_lowq0": "swap-stressed regime (q0 ~ U{3..6})"}[regime]
        _style(ax, xlabel, "total cost (26), seed mean (bands = min-max)", f"({'ab'[ci]}) {title}: cost")
        _style(ax2, xlabel, "unserved orders, seed mean", f"({'cd'[ci]}) {title}: unserved orders")
    axes[0][0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"E4 v2: cost and service vs {xlabel} ({fixed_txt}); ILP rows from the original run, baselines re-run",
                 x=0.01, ha="left", fontsize=11)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _e4_regime_md(df: pd.DataFrame, comb: pd.DataFrame, regime: str, root: str) -> Tuple[List[str], Dict[str, Any], List[str]]:
    """Markdown sections + headline dict + anomalies of one E4 regime."""
    anomalies = _anomalies_common(df, f"e4/{regime}")
    md: List[str] = []
    b = df[df["variant"] == "baseline"]
    d0 = b[b["tag"] == f"B{E4.BASE_B}_C{E4.BASE_C}_P{E4.BASE_P:g}"]
    leg0 = df[(df["variant"] == "baseline_legacy") & (df["tag"] == f"B{E4.BASE_B}_C{E4.BASE_C}_P{E4.BASE_P:g}")]
    res0 = df[(df["variant"] == "baseline_reserve") & (df["tag"] == f"B{E4.BASE_B}_C{E4.BASE_C}_P{E4.BASE_P:g}")]
    hl: Dict[str, Any] = {
        "regime": regime, "n_variants": int(b.shape[0]),
        "default_v2": float(d0["total"].mean()), "default_old": float(d0["old_baseline_total"].mean()),
        "default_reserve": float(res0["total"].mean()), "default_ilp": float(d0["ilp_total"].mean()),
        "default_gap_v2_pct": float(d0["gap_vs_baseline_pct"].mean()), "default_gap_legacy_pct": float(leg0["gap_vs_baseline_pct"].mean()),
        "default_gap_v2_per_seed": [round(float(v), 2) for v in d0.sort_values("seed")["gap_vs_baseline_pct"]],
        "default_gap_reserve_pct": float(res0["gap_vs_baseline_pct"].mean()),
        "default_unserved_v2": float(d0["n_unserved"].mean()), "default_unserved_old": float(d0["old_baseline_n_unserved"].mean()),
        "default_unserved_ilp": float(d0["ilp_n_unserved"].mean()),
        "cert_written": int((b["cert_written"] == True).sum()) if "cert_written" in b.columns else None,  # noqa: E712
        "cert_rho0": int((b["cert_rho0"] == True).sum()) if "cert_rho0" in b.columns else None,  # noqa: E712
        "cert_relaxed": int((b["cert_relaxed"] == True).sum()) if "cert_relaxed" in b.columns else None,  # noqa: E712
        "old_accepted": int(((b["ilp_mip_start_accepted_old"] == True)  # noqa: E712
                             & (b["ilp_mip_start_from_old"] == "baseline")).sum()),
        "old_started_from_baseline": int((b["ilp_mip_start_from_old"] == "baseline").sum()),
        "old_accepted_rho0": int(((b["ilp_rho0_mip_start_accepted_old"] == True)  # noqa: E712
                                  & b["ilp_rho0_total"].notna()).sum()),
        "old_rho0_runs": int(b["ilp_rho0_total"].notna().sum()),
        "mean_v2": float(b["total"].mean()), "mean_old": float(b["old_baseline_total"].mean()),
        "v2_le_old": int((b["total"] <= b["old_baseline_total"] + 1e-9).sum()),
        "legacy_all_match": bool(df["legacy_matches_old"].dropna().all()), "arcs_all_match": bool(df["n_arcs_match"].all()),
        "q0_all_match": bool(df["q0_match"].all()),
        "ilp_le_v2_all": bool((b["ilp_total"] <= b["total"] + 1e-6).all()),
    }
    summaries = {sw: e4_sweep_summary(comb, sw) for sw in ("B", "C", "P")}
    summaries = {k: v for k, v in summaries.items() if not v.empty and v[E4.SWEEP_SPEC[k][0]].nunique() >= 2}
    gaps = pd.concat([e4_gap_table(comb, sw) for sw in summaries], ignore_index=True) if summaries else pd.DataFrame()
    spares = e4_spares_to_match(comb, summaries["B"]) if "B" in summaries else []
    hl["spares_to_match"] = spares
    for sw, s in summaries.items():
        s.to_csv(os.path.join(root, f"summary_{sw}_v2.csv"), index=False)
    if len(gaps):
        gaps.to_csv(os.path.join(root, "gap_decomposition_v2.csv"), index=False)
    md.append(f"## Regime `{regime}` -- headline at the default sizes B_j = {E4.BASE_B}, C_j = {E4.BASE_C}, P_j = {E4.BASE_P:g} kW")
    md.append("")
    md.append(f"Baseline {hl['default_old']:.1f} -> **{hl['default_v2']:.1f}** (reserve {hl['default_reserve']:.1f}) vs ILP {hl['default_ilp']:.1f}: "
              f"headline gap (baseline - ILP)/baseline {hl['default_gap_legacy_pct']:.1f} % -> **{hl['default_gap_v2_pct']:.1f} %** "
              f"(per seed {hl['default_gap_v2_per_seed']}; vs baseline_reserve {hl['default_gap_reserve_pct']:.1f} %); unserved "
              f"{hl['default_unserved_old']:.2f} -> {hl['default_unserved_v2']:.2f} (ILP {hl['default_unserved_ilp']:.2f}). Over all "
              f"{hl['n_variants']} fixed-size variants the mean baseline cost moves {hl['mean_old']:.1f} -> {hl['mean_v2']:.1f}, the fixed "
              f"baseline is at most as expensive as the old one on {hl['v2_le_old']} / {hl['n_variants']} variants, and ILP <= new baseline "
              f"on every variant: {hl['ilp_le_v2_all']}. Byte-identity: n_arcs equal to the old run on every variant {hl['arcs_all_match']}, "
              f"q0_mean equal {hl['q0_all_match']}, legacy variant reproduces the old baseline total exactly {hl['legacy_all_match']}.")
    md.append("")
    md.append(f"New baseline MIP start accepted by the written model on {hl['cert_written']} / {hl['n_variants']} variants (old baseline: "
              f"{hl['old_accepted']} of the {hl['old_started_from_baseline']} written-model ILP runs that used it as start, the others "
              f"started from the ILP_rho0 chain; {hl['old_accepted_rho0']} of the {hl['old_rho0_runs']} old ILP_rho0 runs), by the rho = 0 "
              f"model on {hl['cert_rho0']} / {hl['n_variants']} and under the fully relaxed end targets "
              f"on {hl['cert_relaxed']} / {hl['n_variants']}. {_cert_summary(df, 'baseline')}")
    md.append("")
    for sw, s in summaries.items():
        col = E4.SWEEP_SPEC[sw][0]
        md.append(f"### Sweep {sw}: {col} (seed means; ILP / ILP_rho0 from the original run)")
        md.append("")
        md.append(C.markdown_table(s, None, 2))
        md.append("")
    md.append("`marginal_*_per_unit` at size s = (cost(s) - cost(next s)) per unit added at one site (positive = adding the unit saves cost).")
    md.append("")
    if len(gaps):
        md.append("### Gap to the ILP per size (seed means)")
        md.append("")
        md.append(C.markdown_table(gaps, None, 2))
        md.append("")
        md.append(GAP_NOTE + " `d_<comp>` = baseline component - ILP component.")
        md.append("")
    if spares:
        md.append("### Extra spares the baseline needs to match the ILP service level (B sweep, C_j = 3, P_j = 4 kW)")
        md.append("")
        md.append(C.markdown_table(pd.DataFrame(spares), None, 2))
        md.append("")
    free = df[df["sweep"] == "free_fixed"].sort_values(["seed", "variant"])
    if len(free):
        md.append("### Baseline at the sizes the free-size ILP chose (`free_fixed`)")
        md.append("")
        md.append(C.markdown_table(free, ["seed", "variant", "B_sites", "C_sites", "total", "old_baseline_total", "ilp_total",
                                          "gap_vs_baseline_pct", "n_unserved", "ilp_n_unserved", "families", "cert_written",
                                          "cert_relaxed"], 2))
        md.append("")
    md.append("### Per variant (default baseline): new vs old vs ILP")
    md.append("")
    cols = ["seed", "tag", "total", "old_baseline_total", "ilp_total", "ilp_rho0_total", "gap_vs_baseline_pct", "gap_rho0_vs_baseline_pct",
            "n_unserved", "old_baseline_n_unserved", "ilp_n_unserved", "C_travel", "C_elec", "lateness", "n_swaps", "jit_dispatches",
            "reach_refusals", "families", "cert_written", "cert_rho0", "cert_relaxed", "ilp_mip_start_accepted_old", "ilp_status"]
    md.append(C.markdown_table(b.sort_values(["seed", "sweep", "tag"]), [c for c in cols if c in b.columns], 2))
    md.append("")
    md.append("### All variants (seed means per tag)")
    md.append("")
    allm = _mean_table(df, ["tag", "variant"], ["total", "operational", "n_unserved", "C_elec", "lateness", "n_swaps", "end_full_total",
                                                  "viol_17_local_sum", "viol_18_global", "gap_vs_baseline_pct", "late_trips_suppressed"])
    md.append(C.markdown_table(allm, None, 2))
    md.append("")
    return md, hl, anomalies


def report_e4(frames: Dict[str, pd.DataFrame]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """``outputs/e4_sizing/RESULTS_v2.md`` (both regimes), ``stressed_lowq0/RESULTS_v2.md``
    (stressed regime only), ``cost_vs_B_v2.png``, ``cost_vs_C_v2.png``, ``cost_vs_P_v2.png``."""
    combs: Dict[str, pd.DataFrame] = {}
    sections: Dict[str, List[str]] = {}
    hls: Dict[str, Any] = {}
    anomalies: List[str] = []
    for regime, df in frames.items():
        root = OUT_E4 if regime == "main" else OUT_E4S
        old = pd.read_csv(os.path.join(root, "results.csv"))
        combs[regime] = _e4_combined(df, old, regime)
        sections[regime], hls[regime], an = _e4_regime_md(df, combs[regime], regime, root)
        anomalies += an
    figs = [plot_e4_sweep(combs, "B", os.path.join(OUT_E4, "cost_vs_B_v2.png")),
            plot_e4_sweep(combs, "C", os.path.join(OUT_E4, "cost_vs_C_v2.png"))]
    if "main" in combs:
        figs.append(plot_e4_sweep({"main": combs["main"]}, "P", os.path.join(OUT_E4, "cost_vs_P_v2.png")))
    head = ["# E4 v2 -- fixed baseline re-run on the sizing variants (ILP rows unchanged)", "",
            "Instances regenerated deterministically from `run_meta.json` (family large, seeds 0-2, sweeps B / C / P / B x C grid "
            "and the `free_fixed` sizes of the free-size ILP; the swap-stressed regime uses `init_frac = (0.25, 0.5)`), the same "
            f"arc library per seed (pruning {C.PRUNING_DEFAULTS}) shared by all sizes of that seed (the arcs do not depend on B_j, "
            "C_j, P_j). ILP rows (`ILP` rho = 0.5, `ILP_rho0`) come from the old `results.csv`; only the baseline side is re-run: "
            "`baseline` (fixed policy), `baseline_legacy` (old behaviour, must reproduce the old rows), `baseline_reserve` (F3 end "
            "windows W = 4 slots), `baseline_informed` (F6). No services exist on the co-located layout, so REORDER_POINT is not "
            f"applicable. {GAP_NOTE} Certificates: Gurobi fix-and-solve of the new default baseline under the written model, with the "
            "(18) row removed (rho = 0) and with (17) + (18) removed (rho = 0, R_end = 0); the free ILP is not re-solved.", ""]
    body: List[str] = []
    for regime in ("main", "stressed_lowq0"):
        if regime in sections:
            body += sections[regime]
    abl = os.path.join(OUT_E4, "ablation_fixes_v2.csv")
    if os.path.exists(abl):
        a = pd.read_csv(abl)
        g = a.groupby(["regime", "B_j", "variant"])[["total", "n_unserved", "n_swaps", "bike_km", "lateness", "jit",
                                                     "reach_refusals", "reach_to_swap", "stockout_slots"]].mean().reset_index()
        body += ["## Ablation of the two policy fixes on the B sweep (C_j = 3, P_j = 4 kW; seed means; `experiments/baseline_fix_ablation_v2.py`)",
                 "",
                 "`legacy` = old behaviour; `jit_only` = just-in-time dispatch (F1) alone; `deadzone_only` = reach-refusal swap rule (F2) "
                 "alone; `v2` = both (the fixed default); `*_no_reach_guard` = the post-delivery reach guard of step 6 switched off "
                 "(`require_post_delivery_reach = False`, which also disables the dead-zone rule).",
                 "", C.markdown_table(g, None, 2), ""]
    tail = ["## Figures", ""] + [f"- `{os.path.basename(f)}`" for f in figs] + ["", "## Anomalies", ""]
    tail += [f"- {a}" for a in anomalies] if anomalies else ["- none"]
    tail += [""] + _interpretation(OUT_E4)
    path_main = os.path.join(OUT_E4, "RESULTS_v2.md")
    with open(path_main, "w", encoding="utf-8") as fh:
        fh.write("\n".join(head + body + tail) + "\n")
    paths = [path_main]
    if "stressed_lowq0" in sections:
        p = os.path.join(OUT_E4S, "RESULTS_v2.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("\n".join(["# E4 v2 -- swap-stressed regime (q0 ~ U{3..6}); see ../RESULTS_v2.md for both regimes and figures", ""]
                               + sections["stressed_lowq0"]
                               + ["## Figures (in the parent folder)", ""] + [f"- `../{os.path.basename(f)}`" for f in figs]) + "\n")
        paths.append(p)
    return paths + figs, anomalies, hls


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
PARTS = ("e2", "e3", "e4", "e4s")


def main(parts: Sequence[str], do_certify: bool = True, report_only: bool = False) -> Dict[str, Any]:
    """Run the requested parts (writing ``results_v2.csv`` each) and then rebuild every
    report whose CSV exists; returns the headline dicts."""
    t0 = time.perf_counter()
    if not report_only:
        if "e2" in parts:
            run_e2(do_certify)
        if "e3" in parts:
            run_e3(do_certify)
        if "e4" in parts:
            run_e4("main", do_certify)
        if "e4s" in parts:
            run_e4("stressed_lowq0", do_certify)
    out: Dict[str, Any] = {"wall_s": time.perf_counter() - t0}
    p = os.path.join(OUT_E2_V2, "results_v2.csv")
    if os.path.exists(p) and ("e2" in parts or report_only):
        path, an, hl = report_e2(pd.read_csv(p))
        out["e2"] = {"path": path, "anomalies": an, "headline": hl}
    p = os.path.join(OUT_E3_V2, "results_v2.csv")
    if os.path.exists(p) and ("e3" in parts or report_only):
        path, an, hl = report_e3(pd.read_csv(p))
        out["e3"] = {"path": path, "anomalies": an, "headline": hl}
    frames = {}
    for regime, root in (("main", OUT_E4), ("stressed_lowq0", OUT_E4S)):
        p = os.path.join(root, "results_v2.csv")
        if os.path.exists(p):
            frames[regime] = pd.read_csv(p)
    if frames and ({"e4", "e4s"} & set(parts) or report_only):
        paths, an, hl = report_e4(frames)
        out["e4"] = {"paths": paths, "anomalies": an, "headline": hl}
    with open(os.path.join(C.OUTPUT_ROOT, "baseline_rerun_v2_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parts", nargs="+", default=list(PARTS), choices=list(PARTS))
    ap.add_argument("--no-certify", action="store_true", help="skip the Gurobi fix-and-solve certificates")
    ap.add_argument("--report-only", action="store_true", help="rebuild RESULTS_v2.md / figures from results_v2.csv")
    args = ap.parse_args()
    res = main(args.parts, not args.no_certify, args.report_only)
    print(json.dumps({k: (v.get("headline") if isinstance(v, dict) else v) for k, v in res.items()}, indent=1, default=str)[:4000])
