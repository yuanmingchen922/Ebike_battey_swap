"""Round 5, X1 -- headline re-validation of the round-3 coordination gaps (``usd4h`` 29.6 %,
``nyc4h`` 31.8 %) under the round-5 accounting (plan ``notes/reading_to_model.md``, items A1,
M1, M2, M3, A3, O1; DECISIONS "R5 implementation notes").

Question: how much of the round-3 headline (ILP written model vs the R2.3 rule, raw (26) totals,
legacy 12 Wh/km energy) survives

(a) the eBaaS energy calibration (``config.ENERGY_CALIBRATIONS['ebaas']``: 25 Wh/km, eps 25 Wh,
    L 24, concat rounding, q_res 2 levels),
(b) the stronger per-instance best rule ``best_rule = min over r2, r5_range, r5_transfer (only
    when the instance has services) and r5`` (conservative comparison), and
(c) the like-for-like relaxed targets (rho 0, R_end 0: ``common.relax_end_targets`` = the
    ``rho0_R0`` cell of ``common.boundary_grid``) compared on ``total_end_adjusted`` (M1
    end-state adjustment ``C_end_adjust`` applied to both policies)?

Design
------
* families: ``usd4h`` (6 bikes, demand x0.75 / x1 / x1.5 of 1.5 orders per bike-hour, seeds 0-9,
  ``usd_sunk``) and ``nyc4h`` (busiest siting, seeds 0-9); calibration ``ebaas`` via the
  ``energy_calibration`` option (usd4h: ``generator.make_synthetic_instance(energy_calibration=
  'ebaas')``; nyc4h: ``L`` / ``battery_wh`` / ``physics`` of the calibration passed to
  ``data_nyc.make_nyc_instance`` plus the ``sites_nyc`` post-build step that sets ``q_res`` and
  ``energy_rounding``, the convention of the ``r5_manhattan`` family).
* pruning: usd4h ``pruning_for(inst, reachable=True)`` (lossless, as round 3); nyc4h
  ``pruning_for(inst, targets='facilities')`` = ``PRUNING_NYC`` (restricts only the ILP: the nyc4h
  gaps are lower bounds, as in round 3).
* methods per instance: rules ``r2``, ``r5_range``, ``r5_transfer`` (services only), ``r5`` run on
  the written instance AND on its relaxed copy (the M3 cost-aware transfer rule reads ``R_end``;
  ``run_baseline_case`` keeps the written DEMAND_AWARE reserve on the copy); ``ilp`` on the
  written instance (MIP start = cheapest clean rule schedule, else ``feasible_mip_start``) and
  ``ilp`` on the relaxed copy (MIP start = the written ILP schedule, feasible for the relaxation).
  Gurobi ``OutputFlag 0``, ``Threads 3``, ``Seed 0``, ``TimeLimit 300 s``, ``aggregate=True`` (O1).
  ``best_rule`` is derived per instance in the analysis (min over the rules; on the relaxed cells
  min over the rules run on either copy, by the measure being compared).
* legacy anchor (cheap, no ILP): the round-3 instances are rebuilt with the legacy calibration, the
  four rules are re-run on both copies (the r2 total is checked against the stored round-3
  baseline row) and the stored round-3 ILP rows (``outputs/e2u_round3`` / ``outputs/e8_round3``,
  ``ilp`` and ``ilp_relaxed``) are copied in (``source = round3``), giving the 2 x 2 x 2 grid
  calibration x rule x targets on raw totals for a Shapley decomposition of (a), (b), (c1); the
  end-state step (c2) needs ILP schedules and is measured on ``ebaas`` only.
* byte-identical instances across methods: one in-memory instance per cell, ``demand_md5`` asserted
  equal for the relaxed copy and re-checked over all rows of a cell in the analysis.
* headline gap = 100 (baseline - ILP) / baseline per instance, pooled as the mean over instances
  with a 95 % Student-t interval (same convention as the round-3 29.6 % / 31.8 %).
* records: ``records.jsonl`` (append-only, one per run, resume by key ``(family, calib, seed, mult,
  targets, method)``), ``results.csv`` refreshed after each run, ``instances/*.json`` (ebaas
  instances and ILP schedules), one printed line per run, ``SKIPPED_BUDGET`` when the 150 min wall
  budget cannot fit a solve.  ``--analyse`` writes ``per_instance.csv``, ``stages.csv``,
  ``shapley.csv``, ``components.csv``, ``metric_pack.csv``, ``solver.csv``, ``summary.json``,
  ``stages.png`` and ``RESULTS.md``.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r5_x1_headline.py --dry-run
    python3 experiments/r5_x1_headline.py --smoke --out-dir /tmp/x1_smoke   # 2 cells, Threads 1, TimeLimit 30 s
    python3 experiments/r5_x1_headline.py                                   # full run (resumable)
    python3 experiments/r5_x1_headline.py --analyse
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ebike_swap_sim import ArcLibrary, Instance, Schedule, build_arcs, check  # noqa: E402
from experiments import common as C  # noqa: E402

plt = C.plt

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r5_x1_headline")
R3_E2U = os.path.join(C.OUTPUT_ROOT, "e2u_round3", "records.jsonl")
R3_E8 = os.path.join(C.OUTPUT_ROOT, "e8_round3", "records.jsonl")
RECORDS = "records.jsonl"
FAMILIES: Tuple[str, ...] = ("usd4h", "nyc4h")
CALIBS: Tuple[str, ...] = ("legacy", "ebaas")
ENERGY = "ebaas"
COST_VARIANT = "usd_sunk"
BASE_OPH = 1.5
MULTS: Tuple[float, ...] = (0.75, 1.0, 1.5)
SEEDS: Tuple[int, ...] = tuple(range(10))
TARGETS: Tuple[str, ...] = ("written", "relaxed")
RULES: Tuple[str, ...] = ("r2", "r5_range", "r5_transfer", "r5")
#: rules that always apply (``r5_transfer`` only when the instance has services)
CORE_RULES: Tuple[str, ...] = ("r2", "r5_range", "r5")
RULE_VARIANT = {"r2": "baseline", "r5_range": "baseline_r5_range", "r5_transfer": "baseline_r5_transfer",
                "r5": "baseline_r5"}
TIME_LIMIT = 300.0
WALL_BUDGET_S = 150 * 60.0
#: round-3 headlines (README, outputs/e2u_round3 and outputs/e8_round3 RESULTS_final.md)
ROUND3_HEADLINE = {"usd4h": 29.6, "nyc4h": 31.8}
COMPONENTS = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb", "C_end_adjust"]
#: expected wall seconds per written ILP solve at Threads 3, used only for the --dry-run estimate (probe
#: 2026-10-17, seed 0, aggregated, Threads 3: usd4h x1 39 s / x1.5 46 s OPTIMAL, relaxed 32 / 39 s from the
#: written start; nyc4h seed 0 OPTIMAL in 21 s / 19 s at Threads 1)
EST_ILP_S = {("usd4h", 0.75): 40.0, ("usd4h", 1.0): 45.0, ("usd4h", 1.5): 55.0, ("nyc4h", 1.0): 25.0}
#: relaxed solve time as a share of the written one (MIP start = written optimum)
EST_RELAXED_FACTOR = 0.85
#: expected wall seconds per cell for instance + 2 libraries + rule runs + checks (probe: 18 s usd4h ebaas,
#: 4-7 s legacy cells)
EST_INSTANCE_S = {("usd4h", "ebaas"): 20.0, ("nyc4h", "ebaas"): 20.0, ("usd4h", "legacy"): 5.0,
                  ("nyc4h", "legacy"): 8.0}
#: A3 metric-pack scalars summarised per method (``flatten_r5`` columns without prefix)
METRIC_KEYS = ["total", "total_end_adjusted", "C_end_adjust", "served_share", "n_unserved", "n_late", "bike_km",
               "r5_n_swaps", "r5_bsr", "r5_min_sbur", "r5_mean_sbur", "r5_outage_rate", "r5_n_energy_refused_orders",
               "r5_mean_station_time_min", "r5_mean_detour_km_per_swap", "r5_empty_km_share",
               "r5_empty_km_per_bike_hour", "r5_peak_kw_network", "r5_kwh_purchased", "r5_batteries_saved_total"]

Key = Tuple[str, str, int, float, str, str]          # (family, calib, seed, mult, targets, method)
Cell = Tuple[str, str, int, float]                    # (family, calib, seed, mult)
WorkItem = Tuple[str, str, int, float, str, str]      # (family, calib, seed, mult, targets, method|'rules')


# ---------------------------------------------------------------------------
# keys and plan
# ---------------------------------------------------------------------------
def key_of(row: Dict[str, Any]) -> Key:
    return (str(row["family"]), str(row["calib"]), int(row["seed"]), float(row["mult"]), str(row["targets"]),
            str(row["method"]))


def cell_of(row: Dict[str, Any]) -> Cell:
    return (str(row["family"]), str(row["calib"]), int(row["seed"]), float(row["mult"]))


def last_per_key(rows: Iterable[Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
    out: Dict[Key, Dict[str, Any]] = {}
    for r in rows:
        out[key_of(r)] = r
    return out


def row_is_done(row: Optional[Dict[str, Any]], retry_unsolved: bool = False) -> bool:
    """Policy rows always; ILP rows solved (OPTIMAL / gap <= 1 %), or stopped at the time limit
    with Seed 0 (a re-run reproduces them; ``retry_unsolved`` forces it), or copied from round 3.
    ``SKIPPED_BUDGET`` rows are never done."""
    if row is None:
        return False
    st = row.get("status")
    if st == "POLICY" or row.get("source") == "round3":
        return True
    if st == C.SKIPPED_BUDGET:
        return False
    if C.reusable_ilp_row(st, row.get("mip_gap")):
        return True
    return (not retry_unsolved) and st in ("TIME_LIMIT", "INFEASIBLE", "INF_OR_UNBD")


def cells_for(families: Sequence[str], seeds: Sequence[int], mults: Sequence[float]) -> List[Tuple[str, int, float]]:
    """Seed-major order interleaving the families so that a budget stop leaves balanced seeds."""
    out: List[Tuple[str, int, float]] = []
    for seed in seeds:
        for fam in families:
            for mult in (mults if fam == "usd4h" else (1.0,)):
                out.append((fam, int(seed), float(mult)))
    return out


def build_plan(done: Dict[Key, Dict[str, Any]], families: Sequence[str] = FAMILIES, seeds: Sequence[int] = SEEDS,
               mults: Sequence[float] = MULTS, legacy: bool = True, retry_unsolved: bool = False) -> List[WorkItem]:
    """Work items not yet done: phase L (legacy rules, all cells first: cheap) then phase E (ebaas:
    rules, ILP written, ILP relaxed per cell).  A ``'rules'`` item stands for the rule runs of one
    cell on both copies (done when r2 / r5_range / r5 exist on both)."""
    def todo(fam: str, cal: str, seed: int, mult: float, tg: str, m: str) -> bool:
        return not row_is_done(done.get((fam, cal, seed, float(mult), tg, m)), retry_unsolved)

    plan: List[WorkItem] = []
    cells = cells_for(families, seeds, mults)
    if legacy:
        for fam, seed, mult in cells:
            if any(todo(fam, "legacy", seed, mult, tg, r) for tg in TARGETS for r in CORE_RULES):
                plan.append((fam, "legacy", seed, mult, "*", "rules"))
    for fam, seed, mult in cells:
        if any(todo(fam, "ebaas", seed, mult, tg, r) for tg in TARGETS for r in CORE_RULES):
            plan.append((fam, "ebaas", seed, mult, "*", "rules"))
        for tg in TARGETS:
            if todo(fam, "ebaas", seed, mult, tg, "ilp"):
                plan.append((fam, "ebaas", seed, mult, tg, "ilp"))
    return plan


def group_plan(plan: Sequence[WorkItem]) -> List[Tuple[str, str, int, float, List[Tuple[str, str]]]]:
    """Consecutive items of one cell share one instance / library build."""
    groups: List[Tuple[str, str, int, float, List[Tuple[str, str]]]] = []
    for fam, cal, seed, mult, tg, m in plan:
        if groups and groups[-1][:4] == (fam, cal, seed, mult):
            groups[-1][4].append((tg, m))
        else:
            groups.append((fam, cal, seed, mult, [(tg, m)]))
    return groups


def plan_summary(plan: Sequence[WorkItem], time_limit: float = TIME_LIMIT) -> Dict[str, Any]:
    n_ilp = sum(1 for it in plan if it[5] == "ilp")
    cells = {it[:4] for it in plan}
    overhead = sum(EST_INSTANCE_S.get((c[0], c[1]), 20.0) for c in cells)
    est = overhead
    for fam, _cal, _seed, mult, tg, m in plan:
        if m == "ilp":
            s = EST_ILP_S.get((fam, float(mult)), 90.0)
            est += (EST_RELAXED_FACTOR * s if tg == "relaxed" else s)   # relaxed starts from the written optimum
    worst = overhead + n_ilp * (time_limit + 25.0)
    per_phase: Dict[str, int] = {}
    for it in plan:
        per_phase[it[1]] = per_phase.get(it[1], 0) + 1
    return {"work_items": len(plan), "ilp_items": n_ilp, "cells": len(cells), "per_calib": per_phase,
            "rule_groups": sum(1 for it in plan if it[5] == "rules"),
            "expected_wall_min": round(est / 60.0, 1), "worst_wall_min_at_time_limit": round(worst / 60.0, 1)}


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def orders_md5(inst: Instance) -> str:
    """MD5 of the order stream only (ids, nodes, times): equal across calibrations iff the energy
    calibration left the demand draw untouched (``demand_md5`` also hashes ``q0`` and ``L``)."""
    txt = json.dumps([(o.id, o.o, o.d, o.r, o.a, o.b, o.hp, o.hd) for o in inst.orders], default=str)
    return hashlib.md5(txt.encode("utf-8")).hexdigest()


def make_inst(family: str, calib: str, seed: int, mult: float = 1.0) -> Instance:
    """Instance of one cell.  ``legacy`` = exactly the round-3 builders (``e2u_coord_usd.make_inst`` /
    ``e8_nyc_fixed.make_instance(seed, 'busiest')``); ``ebaas`` = the same family with the A1 energy
    calibration."""
    if calib not in CALIBS:
        raise ValueError(f"unknown calibration {calib!r}")
    if family == "usd4h":
        if calib == "legacy":
            from experiments import e2u_coord_usd as E2U
            inst = E2U.make_inst(int(seed), float(mult), COST_VARIANT)
        else:
            inst = C.make_instance("usd4h", seed=int(seed), orders_per_bike_hour=BASE_OPH * float(mult),
                                   cost_variant=COST_VARIANT, energy_calibration=ENERGY)
            inst.meta["demand_mult"] = float(mult)
            inst.meta["name"] = f"usd4h-{ENERGY}-K{len(inst.bikes)}-I{len(inst.orders)}-seed{seed}-x{float(mult):g}"
            inst.meta["seed"] = int(seed)
    elif family == "nyc4h":
        if float(mult) != 1.0:
            raise ValueError("nyc4h has demand x1 only")
        if calib == "legacy":
            from experiments import e8_nyc_fixed as E8
            inst = E8.make_instance(int(seed), "busiest")
        else:
            from ebike_swap_sim import sites_nyc
            from ebike_swap_sim.config import energy_calibration
            ecal = energy_calibration(ENERGY)
            inst = C.make_instance("nyc4h", seed=int(seed), name=f"nyc4h-busiest-seed{seed}-{ENERGY}",
                                   L=int(ecal["L"]), battery_wh=float(ecal["battery_wh"]),
                                   physics={k: float(ecal[k]) for k in ("wh_per_km", "wh_per_m_climb", "wh_per_light")})
            sites_nyc._apply_post(inst, {"energy_calibration": ENERGY})   # q_res levels + concat rounding (A1)
            inst.meta["site_labels"] = [f"busiest cell {i + 1}" for i in range(len(inst.facilities))]
            inst.meta["siting"] = "busiest"
            inst.validate(raise_on_error=True)
        inst.meta["pruning_targets"] = "facilities"
        inst.meta["demand_mult"] = 1.0
    else:
        raise ValueError(f"unknown family {family!r}")
    inst.meta["x1_calib"] = calib
    return inst


def pruning(inst: Instance, family: str) -> Dict[str, Any]:
    """Round-3 pruning: usd4h plan + reachable (lossless); nyc4h PRUNING_NYC (facility targets)."""
    if family == "nyc4h":
        return C.pruning_for(inst, targets="facilities")
    return C.pruning_for(inst, reachable=True)


def applicable_rules(inst: Instance) -> List[str]:
    return [r for r in RULES if r != "r5_transfer" or len(inst.services) > 0]


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------
def _cost_cols(cst: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not cst:
        return {"total": None, "total_end_adjusted": None, "C_end_adjust": None}
    return C.flatten_cost(cst, "")


def _metric_cols(met: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not met:
        return {}
    out = {k: met.get(k) for k in ("served_share", "n_served", "n_unserved", "n_late", "mean_response_h",
                                   "mean_lateness_h", "bike_km", "n_swaps", "kwh_purchased", "transfers_used",
                                   "end_full_total", "end_target_shortfall")}
    out["stockout_slots"] = sum((met.get("stockout_slots") or {}).values())
    out.update(C.flatten_r5(met, ""))
    return out


def base_row(inst: Instance, lib: ArcLibrary, family: str, calib: str, seed: int, mult: float, targets: str,
             method: str, md5: str, omd5: str) -> Dict[str, Any]:
    return {
        "family": family, "calib": calib, "seed": int(seed), "mult": float(mult), "targets": targets,
        "method": method, "name": inst.meta.get("name"), "demand_md5": md5, "orders_md5": omd5,
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L, "q_res": inst.q_res,
        "eps_kwh": inst.disc.eps_kwh, "energy_rounding": inst.options.get("energy_rounding", "per_leg"),
        "n_facilities": len(inst.facilities), "n_services": len(inst.services), "rho": inst.rho,
        "R_end_sum": sum(int(f.R_end) for f in inst.facilities), "n_arcs": len(lib),
        "n_unservable": len(C.unservable_orders(inst, lib)), "cost_variant": inst.meta.get("cost_variant"),
        "boundary_variant": inst.meta.get("boundary_variant", "written"),
    }


def rule_row(inst: Instance, lib: ArcLibrary, rec: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    row = base_row(inst, lib, **kw)
    fl = rec["flags"]
    row.update({
        "status": "POLICY", "variant": RULE_VARIANT[kw["method"]], "runtime_s": rec["runtime"],
        "families": json.dumps(rec["families"], sort_keys=True), "ok_modulo_report_only": rec["ok_modulo_report_only"],
        "clean": not rec["families"], "identity_24_ok": rec["identity_24_ok"],
        "policy_reserve_source": rec.get("policy_reserve_source"),
        "swap_rule_effective": fl.get("swap_rule_effective"),
        **{f"policy_{k}": v for k, v in (rec.get("pruning_flags") or {}).items()},
    })
    row.update(_cost_cols(rec["cost"]))
    row.update(_metric_cols(rec["metrics"]))
    return row


def ilp_row(inst: Instance, lib: ArcLibrary, rec: Dict[str, Any], start_label: str, tl: float, threads: int,
            wall: float, **kw: Any) -> Dict[str, Any]:
    row = base_row(inst, lib, **kw)
    st = rec.get("stats") or {}
    row.update({
        "status": rec["status"], "obj": rec["obj"], "bound": rec["bound"], "mip_gap": rec["gap"],
        "runtime_s": rec["runtime"], "build_time_s": rec["build_time"], "wall_s": wall,
        "n_vars": rec["n_vars"], "n_binaries": rec["n_binaries"], "n_rows": rec["n_rows"],
        "n_agg_arcs": st.get("n_agg_arcs"), "aggregate": st.get("aggregate"), "node_count": st.get("node_count"),
        "mip_start_variant": start_label, "mip_start_accepted": rec["mip_start_accepted"],
        "mip_start_obj": (rec.get("mip_start_info") or {}).get("start_obj"),
        "time_limit_s": tl, "threads": threads, "gurobi_seed": C.ILP_PARAMS_R3.get("Seed"),
        "check_ok": rec["ok"], "families": json.dumps(rec["families"], sort_keys=True),
        "identity_24_ok": rec["identity_24_ok"],
    })
    row.update(_cost_cols(rec["cost"]))
    row.update(_metric_cols(rec["metrics"]))
    return row


def round3_ilp_rows(families: Sequence[str], seeds: Sequence[int], mults: Sequence[float]
                    ) -> Tuple[Dict[Key, Dict[str, Any]], Dict[Cell, float]]:
    """Stored round-3 rows as legacy records: ILP written / relaxed (copied, ``source = round3``) and
    the stored r2 baseline totals (for the reproduction check of the re-run legacy rule)."""
    out: Dict[Key, Dict[str, Any]] = {}
    base_tot: Dict[Cell, float] = {}
    keep = ("name", "status", "total", "obj", "bound", "runtime_s", "n_unserved", "served_share", "n_late",
            "bike_km", "n_swaps", "n_orders", "n_bikes", "n_arcs", "n_binaries", "demand_md5", "C_setup", "C_elec",
            "C_travel", "unserved", "response", "lateness", "C_reb", "mip_start_variant", "rho")
    if "usd4h" in families:
        last: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        for r in C.load_jsonl(R3_E2U):
            last[(int(r["seed"]), float(r["demand_mult"]), r.get("cost_variant"), r["method"])] = r
        for (seed, mult, var, method), r in last.items():
            if var != COST_VARIANT or seed not in seeds or mult not in [float(m) for m in mults]:
                continue
            if method == "baseline" and r.get("total") is not None:
                base_tot[("usd4h", "legacy", seed, mult)] = float(r["total"])
            elif method in ("ilp", "ilp_relaxed"):
                rr = {k: r.get(k) for k in keep}
                rr.update(family="usd4h", calib="legacy", seed=seed, mult=mult, method="ilp",
                          targets="written" if method == "ilp" else "relaxed", mip_gap=r.get("mip_gap"),
                          source="round3", r3_method=method)
                out[key_of(rr)] = rr
    if "nyc4h" in families:
        last = {}
        for r in C.load_jsonl(R3_E8):
            last[(str(r["siting"]), int(r["seed"]), r["method"])] = r
        for (siting, seed, method), r in last.items():
            if siting != "busiest" or seed not in seeds:
                continue
            if method == "baseline" and r.get("total") is not None:
                base_tot[("nyc4h", "legacy", seed, 1.0)] = float(r["total"])
            elif method in ("ilp", "ilp_relaxed"):
                rr = {k: r.get(k) for k in keep}
                rr["demand_md5_r3_convention"] = rr.pop("demand_md5", None)   # include_bike_nodes=False there
                rr.update(family="nyc4h", calib="legacy", seed=seed, mult=1.0, method="ilp",
                          targets="written" if method == "ilp" else "relaxed", mip_gap=r.get("gap"),
                          source="round3", r3_method=method)
                out[key_of(rr)] = rr
    return out, base_tot


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, out_dir: str, time_limit: float, threads: int, budget: C.WallBudget,
                 retry_unsolved: bool = False) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.inst_dir = C.ensure_dir(os.path.join(out_dir, "instances"))
        self.path = os.path.join(out_dir, RECORDS)
        self.time_limit, self.threads, self.budget = float(time_limit), int(threads), budget
        self.retry_unsolved = retry_unsolved
        self.done: Dict[Key, Dict[str, Any]] = last_per_key(C.load_jsonl(self.path))
        self.r3_base: Dict[Cell, float] = {}
        self.n_runs = 0

    # -- output -------------------------------------------------------------
    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("source", "r5_x1")
        C.append_jsonl(self.path, row)
        self.done[key_of(row)] = row
        self.refresh_csv()
        self.n_runs += 1
        keys = ("name", "calib", "targets", "method", "status", "total", "total_end_adjusted", "C_end_adjust",
                "n_unserved", "mip_gap", "runtime_s", "mip_start_variant", "mip_start_accepted", "families")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys}), flush=True)

    def refresh_csv(self) -> None:
        rows = sorted(self.done.values(), key=lambda r: (r["family"], r["calib"], int(r["seed"]), float(r["mult"]),
                                                         str(r["targets"]), str(r["method"])))
        C.records_to_frame(rows).to_csv(os.path.join(self.out_dir, "results.csv"), index=False)

    def seed_round3(self, rows: Dict[Key, Dict[str, Any]], base_tot: Dict[Cell, float]) -> int:
        self.r3_base.update(base_tot)
        n = 0
        for k, r in rows.items():
            if k not in self.done:
                C.append_jsonl(self.path, r)
                self.done[k] = r
                n += 1
        if n:
            self.refresh_csv()
        return n

    def is_done(self, key: Key) -> bool:
        return row_is_done(self.done.get(key), self.retry_unsolved)

    # -- helpers ------------------------------------------------------------
    def _sched_path(self, name: str, targets: str) -> str:
        return os.path.join(self.inst_dir, f"{name}-ilp-{targets}-schedule.json")

    def _load_sched(self, name: str, targets: str) -> Optional[Schedule]:
        p = self._sched_path(name, targets)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as fh:
            return Schedule.from_dict(json.load(fh))

    @staticmethod
    def _pick_start(inst: Instance, lib: ArcLibrary, cands: Sequence[Tuple[str, Optional[Schedule]]],
                    fallback: Optional[Dict[str, Any]]) -> Tuple[Optional[Schedule], str]:
        """Cheapest candidate schedule that passes ``check`` cleanly on ``inst``; else
        ``common.feasible_mip_start`` on the r2 record (fallback variants); else ``None``."""
        best: Tuple[float, str, Optional[Schedule]] = (math.inf, "none", None)
        for label, sched in cands:
            if sched is None:
                continue
            rep = check(inst, lib, sched)
            if not rep["ok"]:
                continue
            tot = float(C.cost(inst, lib, sched)["total"])
            if tot < best[0] - 1e-9:
                best = (tot, label, sched)
        if best[2] is not None:
            return best[2], best[1]
        if fallback is not None:
            sched, lab = C.feasible_mip_start(inst, lib, fallback)
            # 'default' = no clean schedule exists: the r2 schedule is offered and Gurobi rejects it
            return sched, ("r2_unclean" if lab == "default" else lab)
        return None, "none"

    def _skipped(self, inst: Instance, lib: ArcLibrary, kw: Dict[str, Any]) -> Dict[str, Any]:
        row = base_row(inst, lib, **kw)
        row.update(status=C.SKIPPED_BUDGET, total=None, skip_reason="wall budget exhausted")
        return row

    # -- one cell -----------------------------------------------------------
    def run_cell(self, family: str, calib: str, seed: int, mult: float, items: Sequence[Tuple[str, str]]) -> None:
        t_all = time.perf_counter()
        inst = make_inst(family, calib, seed, mult)
        name = str(inst.meta["name"])
        if calib == "ebaas":
            p = os.path.join(self.inst_dir, name + ".json")
            if not os.path.exists(p):
                inst.save(p)
        relaxed = C.relax_end_targets(inst)
        relaxed.meta["name"] = name + "-relaxed"
        md5, omd5 = C.demand_md5(inst), orders_md5(inst)
        if C.demand_md5(relaxed) != md5 or orders_md5(relaxed) != omd5:
            raise RuntimeError(f"{name}: relaxed copy changed the demand side")
        lib, t_lib = C.build_library(inst, pruning(inst, family))
        lib_rel = build_arcs(relaxed, **lib.options)
        if len(lib_rel) != len(lib):
            raise RuntimeError(f"{name}: rho / R_end changed the arc library")
        copies = {"written": (inst, lib), "relaxed": (relaxed, lib_rel)}
        rules = applicable_rules(inst)
        recs: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for tg in TARGETS:
            ii, ll = copies[tg]
            for rule in rules:
                rec = C.run_baseline_case(ii, ll, C.baseline_variant_params(RULE_VARIANT[rule], ii), label=rule)
                recs[(tg, rule)] = rec
                key = (family, calib, int(seed), float(mult), tg, rule)
                if not self.is_done(key):
                    row = rule_row(ii, ll, rec, family=family, calib=calib, seed=seed, mult=mult, targets=tg,
                                   method=rule, md5=md5, omd5=omd5)
                    row["lib_build_time_s"] = t_lib
                    if calib == "legacy" and tg == "written" and rule == "r2":
                        ref = self.r3_base.get((family, calib, int(seed), float(mult)))
                        row["r3_baseline_total"] = ref
                        row["r3_baseline_reproduced"] = (None if ref is None else abs(ref - row["total"]) < 1e-6)
                    self.emit(row)
        if calib == "ebaas":
            want = {tg for tg, m in items if m == "ilp"}
            sched_w: Optional[Schedule] = None
            kw = dict(family=family, calib=calib, seed=seed, mult=mult, md5=md5, omd5=omd5, method="ilp")
            if "written" in want and not self.is_done((family, calib, int(seed), float(mult), "written", "ilp")):
                tl = self.budget.solve_limit(self.time_limit)
                if tl is None:
                    self.emit(self._skipped(inst, lib, {**kw, "targets": "written"}))
                else:
                    start, lab = self._pick_start(inst, lib, [(r, recs[("written", r)]["schedule"]) for r in rules],
                                                  recs[("written", "r2")])
                    t0 = time.perf_counter()
                    rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads,
                                         label="ilp", params=C.ILP_PARAMS_R3, **C.R5_ILP_KWARGS)
                    row = ilp_row(inst, lib, rec, lab, tl, self.threads, time.perf_counter() - t0,
                                  targets="written", **kw)
                    row["lib_build_time_s"] = t_lib
                    sched_w = rec["schedule"]
                    if sched_w is not None:
                        with open(self._sched_path(name, "written"), "w", encoding="utf-8") as fh:
                            json.dump(sched_w.to_dict(), fh)
                    self.emit(row)
            else:
                sched_w = self._load_sched(name, "written")
            if "relaxed" in want and not self.is_done((family, calib, int(seed), float(mult), "relaxed", "ilp")):
                tl = self.budget.solve_limit(self.time_limit)
                if tl is None:
                    self.emit(self._skipped(relaxed, lib_rel, {**kw, "targets": "relaxed"}))
                else:
                    cands = [("ilp_written", sched_w)] + [(f"{r}@{tg}", recs[(tg, r)]["schedule"])
                                                          for tg in TARGETS for r in rules]
                    start, lab = self._pick_start(relaxed, lib_rel, cands, recs[("relaxed", "r2")])
                    t0 = time.perf_counter()
                    rec = C.run_ilp_case(relaxed, lib_rel, mip_start=start, time_limit=tl, threads=self.threads,
                                         label="ilp_relaxed", params=C.ILP_PARAMS_R3, **C.R5_ILP_KWARGS)
                    row = ilp_row(relaxed, lib_rel, rec, lab, tl, self.threads, time.perf_counter() - t0,
                                  targets="relaxed", **kw)
                    row["lib_build_time_s"] = t_lib
                    if rec["schedule"] is not None:
                        with open(self._sched_path(name, "relaxed"), "w", encoding="utf-8") as fh:
                            json.dump(rec["schedule"].to_dict(), fh)
                    self.emit(row)
        print(f"# {name} [{calib}] {len(items)} item(s) done in {time.perf_counter() - t_all:.0f} s "
              f"(budget left {self.budget.remaining() / 60:.0f} min)", flush=True)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def gap_pct(b: Optional[float], i: Optional[float]) -> Optional[float]:
    if b is None or i is None or abs(b) < 1e-12:
        return None
    if isinstance(b, float) and math.isnan(b) or isinstance(i, float) and math.isnan(i):
        return None
    return 100.0 * (float(b) - float(i)) / abs(float(b))


def ci95(values: Iterable[Any]) -> Tuple[float, float, int]:
    """``(mean, 95 % Student-t half-width, n)`` with exact t quantiles (scipy; 1.96 fallback)."""
    v = [float(x) for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n == 0:
        return float("nan"), float("nan"), 0
    m = sum(v) / n
    if n == 1:
        return m, float("nan"), 1
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    try:
        from scipy.stats import t as _t
        q = float(_t.ppf(0.975, n - 1))
    except Exception:  # noqa: BLE001
        q = 1.96
    return m, q * sd / math.sqrt(n), n


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _argmin(rows: Sequence[Tuple[str, Dict[str, Any]]], col: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    best: Tuple[float, Optional[str], Optional[Dict[str, Any]]] = (math.inf, None, None)
    for lab, r in rows:
        v = _num(r.get(col))
        if v is not None and v < best[0] - 1e-9:
            best = (v, lab, r)
    return best[1], best[2]


def per_instance(done: Dict[Key, Dict[str, Any]]) -> pd.DataFrame:
    """One row per cell (family, calib, seed, mult): the rule / ILP totals of every comparison, the
    argmin rules and the per-instance gaps of the 2 x 2 x 2 grid plus the end-adjusted headline."""
    by_cell: Dict[Cell, Dict[Tuple[str, str], Dict[str, Any]]] = {}
    for k, r in done.items():
        if r.get("status") == C.SKIPPED_BUDGET:
            continue
        by_cell.setdefault(k[:4], {})[(k[4], k[5])] = r
    out = []
    for cell, rows in sorted(by_cell.items()):
        fam, cal, seed, mult = cell
        md5s = {r.get("demand_md5") for r in rows.values() if r.get("source") != "round3" and r.get("demand_md5")}
        if len(md5s) > 1:
            raise RuntimeError(f"cell {cell}: demand md5 differs across methods {md5s}")
        rules_w = [(m, r) for (tg, m), r in rows.items() if tg == "written" and m in RULES]
        rules_all = [(f"{m}@{tg}", r) for (tg, m), r in rows.items() if m in RULES]
        r2_all = [(f"r2@{tg}", r) for (tg, m), r in rows.items() if m == "r2"]
        iw = rows.get(("written", "ilp"))
        ir = rows.get(("relaxed", "ilp"))
        rec: Dict[str, Any] = {"family": fam, "calib": cal, "seed": seed, "mult": mult,
                               "demand_md5": next(iter(md5s), None),
                               "orders_md5": next((r.get("orders_md5") for r in rows.values() if r.get("orders_md5")), None),
                               "rules_run": ",".join(sorted({m for _tg, m in rows if m in RULES}))}
        r2w = rows.get(("written", "r2"))
        rec["B_r2_w"] = _num(r2w.get("total")) if r2w else None
        for m in RULES:
            r = rows.get(("written", m))
            rec[f"B_{m}_w"] = _num(r.get("total")) if r else None
            r = rows.get(("written", m))
            rec[f"B_{m}_w_ea"] = _num(r.get("total_end_adjusted")) if r else None
        lab, r = _argmin(rules_w, "total")
        rec["best_rule_w"], rec["B_best_w"] = lab, (_num(r.get("total")) if r else None)
        lab, r = _argmin(r2_all, "total")
        rec["B_r2_rel"] = _num(r.get("total")) if r else None
        lab, r = _argmin(r2_all, "total_end_adjusted")
        rec["B_r2_rel_ea"] = _num(r.get("total_end_adjusted")) if r else None
        lab, r = _argmin(rules_all, "total")
        rec["best_rule_rel"], rec["B_best_rel"] = lab, (_num(r.get("total")) if r else None)
        lab, r = _argmin(rules_all, "total_end_adjusted")
        rec["best_rule_rel_ea"], rec["B_best_rel_ea"] = lab, (_num(r.get("total_end_adjusted")) if r else None)
        rec["B_best_rel_ea_C_end_adjust"] = _num(r.get("C_end_adjust")) if r else None
        for c in COMPONENTS:
            rec[f"Bcomp_{c}"] = _num(r.get(c)) if r else None
        # ILP: written row; relaxed = best known (min of the relaxed solve and the written optimum, which is
        # feasible for the relaxation), chosen by the ILP objective (raw total), end-adjusted value of the
        # chosen schedule
        rec["I_w"] = _num(iw.get("total")) if iw else None
        rec["I_w_ea"] = _num(iw.get("total_end_adjusted")) if iw else None
        rec["I_w_status"] = iw.get("status") if iw else None
        rec["I_w_gap"] = _num(iw.get("mip_gap")) if iw else None
        rec["I_w_source"] = iw.get("source") if iw else None
        chosen, src = ir, "relaxed"
        if ir is None or _num(ir.get("total")) is None or (
                iw is not None and _num(iw.get("total")) is not None and _num(iw.get("total")) < _num(ir.get("total")) - 1e-9):
            chosen, src = (iw, "written") if iw is not None and _num(iw.get("total")) is not None else (None, None)
        rec["I_rel"] = _num(chosen.get("total")) if chosen else None
        rec["I_rel_ea"] = _num(chosen.get("total_end_adjusted")) if chosen else None
        rec["I_rel_C_end_adjust"] = _num(chosen.get("C_end_adjust")) if chosen else None
        rec["I_rel_from"] = src
        rec["I_rel_status"] = ir.get("status") if ir else None
        rec["I_rel_gap"] = _num(ir.get("mip_gap")) if ir else None
        for c in COMPONENTS:
            rec[f"Icomp_{c}"] = _num(chosen.get(c)) if chosen else None
        # gaps of the grid (raw totals) and the end-adjusted headline
        rec["g_w_r2"] = gap_pct(rec["B_r2_w"], rec["I_w"])
        rec["g_w_best"] = gap_pct(rec["B_best_w"], rec["I_w"])
        rec["g_rel_r2"] = gap_pct(rec["B_r2_rel"], rec["I_rel"])
        rec["g_rel_best"] = gap_pct(rec["B_best_rel"], rec["I_rel"])
        rec["g_rel_r2_ea"] = gap_pct(rec["B_r2_rel_ea"], rec["I_rel_ea"])
        rec["g_rel_best_ea"] = gap_pct(rec["B_best_rel_ea"], rec["I_rel_ea"])   # headline (ebaas)
        rec["g_w_r5"] = gap_pct(rec.get("B_r5_w"), rec["I_w"])
        rec["g_w_r5_range"] = gap_pct(rec.get("B_r5_range_w"), rec["I_w"])
        rec["price_of_recovery"] = (None if rec["I_w"] is None or rec["I_rel"] is None else rec["I_w"] - rec["I_rel"])
        rec["price_of_recovery_ea"] = (None if rec["I_w_ea"] is None or rec["I_rel_ea"] is None
                                       else rec["I_w_ea"] - rec["I_rel_ea"])
        r2c = rows.get(("written", "r2"))
        rec["r3_baseline_reproduced"] = r2c.get("r3_baseline_reproduced") if r2c else None
        out.append(rec)
    return pd.DataFrame(out)


#: stage path of the survival question (column of :func:`per_instance`, calibration, label)
STAGES: List[Tuple[str, str, str, str]] = [
    ("S0", "g_w_r2", "legacy", "round 3: legacy energy, r2 rule, written targets, raw total"),
    ("S1", "g_w_r2", "ebaas", "(a) eBaaS energy calibration"),
    ("S2", "g_w_best", "ebaas", "(b) + per-instance best rule"),
    ("S3", "g_rel_best", "ebaas", "(c1) + relaxed targets (rho 0, R_end 0), raw total"),
    ("S4", "g_rel_best_ea", "ebaas", "(c2) + end-state adjustment = X1 headline"),
]
#: 2 x 2 x 2 grid (calibration, rule, targets) -> per-instance gap column on raw totals
GRID = {(a, b, c): (col, a) for a in ("legacy", "ebaas")
        for b, c, col in (("r2", "written", "g_w_r2"), ("best", "written", "g_w_best"),
                          ("r2", "relaxed", "g_rel_r2"), ("best", "relaxed", "g_rel_best"))}


def _wide(per: pd.DataFrame) -> pd.DataFrame:
    """Cells keyed by (family, seed, mult) with ``<col>__<calib>`` columns."""
    if per.empty:
        return pd.DataFrame()
    parts = []
    for cal in CALIBS:
        sub = per[per.calib == cal].drop(columns=["calib"]).set_index(["family", "seed", "mult"])
        parts.append(sub.add_suffix(f"__{cal}"))
    return pd.concat(parts, axis=1).reset_index()


def _groups(wide: pd.DataFrame) -> List[Tuple[str, pd.DataFrame]]:
    out: List[Tuple[str, pd.DataFrame]] = []
    for fam in FAMILIES:
        sub = wide[wide.family == fam]
        if sub.empty:
            continue
        out.append((fam, sub))
        if fam == "usd4h":
            for m in MULTS:
                s = sub[sub.mult == float(m)]
                if not s.empty:
                    out.append((f"usd4h x{m:g}", s))
    return out


def stage_table(wide: pd.DataFrame) -> pd.DataFrame:
    """Mean per-instance gap (95 % t-CI, n, n positive) of every stage, per group, on the cells where all
    five stages exist (``common``) and on all cells of the stage (``own``)."""
    rows = []
    for grp, sub in _groups(wide):
        cols = [f"{col}__{cal}" for _s, col, cal, _l in STAGES]
        have = [c for c in cols if c in sub.columns]
        common = sub.dropna(subset=have) if len(have) == len(cols) else sub.iloc[0:0]
        for (sid, col, cal, label), c in zip(STAGES, cols):
            vals = sub[c] if c in sub.columns else pd.Series(dtype=float)
            m, h, n = ci95(vals)
            mc, hc, nc = ci95(common[c]) if c in common.columns else (float("nan"), float("nan"), 0)
            rows.append({"group": grp, "stage": sid, "label": label, "mean_pct": m, "ci95_pct": h, "n": n,
                         "n_positive": int((pd.to_numeric(vals, errors="coerce") > 0).sum()),
                         "mean_pct_common": mc, "ci95_pct_common": hc, "n_common": nc})
    df = pd.DataFrame(rows)
    if not df.empty:
        base = df[df.stage == "S0"].set_index("group")["mean_pct_common"]
        prev = df.groupby("group")["mean_pct_common"].shift(1)
        df["step_pts_common"] = df["mean_pct_common"] - prev
        df["survival_vs_S0_common"] = [r.mean_pct_common / base.get(r.group) if base.get(r.group) else float("nan")
                                       for r in df.itertuples()]
    return df


def shapley(v: Dict[Tuple[int, ...], float], n: int) -> List[float]:
    """Shapley values of ``n`` binary factors from the cell means ``v[(f_1..f_n)]`` (0 = round-3 level,
    1 = round-5 level); they sum to ``v[1..1] - v[0..0]``."""
    phi = [0.0] * n
    for perm in itertools.permutations(range(n)):
        state = [0] * n
        for f in perm:
            before = v[tuple(state)]
            state[f] = 1
            phi[f] += v[tuple(state)] - before
    nf = math.factorial(n)
    return [p / nf for p in phi]


def shapley_table(wide: pd.DataFrame) -> pd.DataFrame:
    """Shapley split of the change S0 -> S3 (raw totals) into (a) calibration, (b) best rule, (c1) relaxed
    targets on the cells where all 8 grid cells exist, plus (c2) = S4 - S3 on the same cells (only defined
    on the eBaaS side)."""
    rows = []
    for grp, sub in _groups(wide):
        cols = {k: f"{col}__{cal}" for k, (col, cal) in GRID.items()}
        if not all(c in sub.columns for c in cols.values()):
            continue
        need = list(cols.values()) + (["g_rel_best_ea__ebaas"] if "g_rel_best_ea__ebaas" in sub.columns else [])
        s = sub.dropna(subset=need)
        if s.empty:
            continue
        lv = {"legacy": 0, "ebaas": 1, "r2": 0, "best": 1, "written": 0, "relaxed": 1}
        v = {(lv[a], lv[b], lv[c]): float(pd.to_numeric(s[col]).mean()) for (a, b, c), col in cols.items()}
        phi = shapley(v, 3)
        c2 = float(pd.to_numeric(s["g_rel_best_ea__ebaas"]).mean()) - v[(1, 1, 1)] if "g_rel_best_ea__ebaas" in s else float("nan")
        s0 = v[(0, 0, 0)]
        rows.append({"group": grp, "n": len(s), "S0_round3_pct": s0, "a_calibration_pts": phi[0],
                     "b_best_rule_pts": phi[1], "c1_relaxed_targets_pts": phi[2], "c2_end_adjust_pts": c2,
                     "S4_headline_pct": s0 + sum(phi) + (0.0 if math.isnan(c2) else c2),
                     "survival_share": (s0 + sum(phi) + (0.0 if math.isnan(c2) else c2)) / s0 if s0 else float("nan"),
                     **{f"cell_{a}_{b}_{c}_pct": v[(lv[a], lv[b], lv[c])] for (a, b, c) in cols}})
    return pd.DataFrame(rows)


def component_table(per: pd.DataFrame) -> pd.DataFrame:
    """Composition of the headline difference (best rule end-adjusted row minus the chosen relaxed ILP row,
    eBaaS) by cost component, mean USD per instance and share of the mean difference."""
    rows = []
    sub_all = per[per.calib == "ebaas"]
    groups = [(f, sub_all[sub_all.family == f]) for f in FAMILIES]
    for grp, sub in groups:
        if sub.empty:
            continue
        diff_tot = pd.to_numeric(sub["B_best_rel_ea"]) - pd.to_numeric(sub["I_rel_ea"])
        rec = {"group": grp, "n": int(diff_tot.notna().sum()), "diff_total_end_adjusted": float(diff_tot.mean())}
        for c in COMPONENTS:
            d = pd.to_numeric(sub[f"Bcomp_{c}"]) - pd.to_numeric(sub[f"Icomp_{c}"])
            rec[f"diff_{c}"] = float(d.mean())
            rec[f"share_{c}"] = float(d.mean() / diff_tot.mean()) if diff_tot.mean() else float("nan")
        rows.append(rec)
    return pd.DataFrame(rows)


def metric_pack_table(done: Dict[Key, Dict[str, Any]], per: pd.DataFrame) -> pd.DataFrame:
    """Mean A3 metric pack per family, calibration and method (rules on the written copy, the per-instance
    best rule of the written comparison, the ILP written and relaxed rows)."""
    rows = []
    best_of = {(r.family, r.calib, int(r.seed), float(r.mult)): r.best_rule_w for r in per.itertuples()}
    buckets: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for k, r in done.items():
        if r.get("status") == C.SKIPPED_BUDGET or r.get("source") == "round3":
            continue
        fam, cal, seed, mult, tg, m = k
        if m in RULES and tg == "written":
            buckets.setdefault((fam, cal, m), []).append(r)
            if best_of.get((fam, cal, seed, mult)) == m:
                buckets.setdefault((fam, cal, "best_rule"), []).append(r)
        elif m == "ilp":
            buckets.setdefault((fam, cal, f"ilp_{tg}"), []).append(r)
    order = list(RULES) + ["best_rule", "ilp_written", "ilp_relaxed"]
    for (fam, cal, m), rs in sorted(buckets.items(), key=lambda kv: (kv[0][0], kv[0][1], order.index(kv[0][2]))):
        rec = {"family": fam, "calib": cal, "method": m, "n": len(rs)}
        for c in METRIC_KEYS:
            vals = [_num(r.get(c)) for r in rs]
            vals = [v for v in vals if v is not None]
            rec[c] = (sum(vals) / len(vals)) if vals else None
        rows.append(rec)
    return pd.DataFrame(rows)


def solver_table(done: Dict[Key, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for k, r in done.items():
        if k[5] == "ilp" and k[1] == "ebaas":
            buckets.setdefault((k[0], k[4]), []).append(r)
    for (fam, tg), rs in sorted(buckets.items()):
        st: Dict[str, int] = {}
        for r in rs:
            st[str(r.get("status"))] = st.get(str(r.get("status")), 0) + 1
        rt = [_num(r.get("runtime_s")) for r in rs if _num(r.get("runtime_s")) is not None]
        gaps = [_num(r.get("mip_gap")) for r in rs if _num(r.get("mip_gap")) is not None]
        acc = [bool(r.get("mip_start_accepted")) for r in rs if r.get("mip_start_accepted") is not None]
        rows.append({"family": fam, "targets": tg, "n": len(rs), "statuses": json.dumps(st, sort_keys=True),
                     "mean_runtime_s": (sum(rt) / len(rt)) if rt else None, "max_runtime_s": max(rt) if rt else None,
                     "max_mip_gap": max(gaps) if gaps else None,
                     "mip_start_accepted_share": (sum(acc) / len(acc)) if acc else None,
                     "check_ok_all": all(bool(r.get("check_ok")) for r in rs if r.get("total") is not None),
                     "mean_n_vars": (sum(_num(r.get("n_vars")) or 0 for r in rs) / len(rs)) if rs else None,
                     "mean_n_arcs": (sum(_num(r.get("n_arcs")) or 0 for r in rs) / len(rs)) if rs else None})
    return pd.DataFrame(rows)


def anomalies(done: Dict[Key, Dict[str, Any]], per: pd.DataFrame) -> List[str]:
    out: List[str] = []
    for k, r in sorted(done.items()):
        if r.get("status") == C.SKIPPED_BUDGET:
            out.append(f"{k}: SKIPPED_BUDGET")
        if k[5] == "ilp" and r.get("source") != "round3" and r.get("total") is not None and not r.get("check_ok"):
            out.append(f"{k}: ILP schedule fails evaluate.check")
        if k[5] == "ilp" and r.get("source") != "round3" and r.get("status") not in ("OPTIMAL", C.SKIPPED_BUDGET):
            out.append(f"{k}: ILP status {r.get('status')} gap {r.get('mip_gap')}")
        if r.get("r3_baseline_reproduced") is False:
            out.append(f"{k}: legacy r2 total {r.get('total')} != stored round-3 baseline {r.get('r3_baseline_total')}")
    if not per.empty:
        for r in per.itertuples():
            if r.calib == "ebaas" and r.I_rel_from == "written" and r.I_rel_status is not None:
                out.append(f"{(r.family, r.seed, r.mult)}: relaxed ILP not better than the written optimum "
                           f"(status {r.I_rel_status}); best-known relaxed value = written")
        neg = per[(per.calib == "ebaas") & (pd.to_numeric(per.g_rel_best_ea, errors="coerce") < 0)]
        for r in neg.itertuples():
            out.append(f"{(r.family, r.seed, r.mult)}: headline gap negative ({r.g_rel_best_ea:.2f} %): the best rule "
                       f"beats the relaxed ILP on the end-adjusted total")
    return out


def plot_stages(st: pd.DataFrame, path: str) -> str:
    groups = [g for g in ("usd4h", "nyc4h") if g in set(st.group)]
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    colors = ["#8a8a85", "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"]
    width = 0.8 / max(1, len(STAGES))
    for gi, g in enumerate(groups):
        sub = st[st.group == g].set_index("stage")
        for si, (sid, _c, _cal, label) in enumerate(STAGES):
            if sid not in sub.index:
                continue
            m, h = sub.loc[sid, "mean_pct_common"], sub.loc[sid, "ci95_pct_common"]
            ax.bar(gi + si * width, m, width, yerr=None if math.isnan(h) else h, color=colors[si], capsize=2,
                   label=f"{sid} {label}" if gi == 0 else None)
    ax.set_xticks([gi + 0.4 - width / 2 for gi in range(len(groups))])
    ax.set_xticklabels(groups)
    ax.set_ylabel("gap (baseline - ILP) / baseline, %")
    ax.axhline(0, color="#444", lw=0.6)
    ax.set_title("X1: survival of the round-3 coordination gap (common cells, 95 % CI)")
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def analyse(out_dir: str) -> str:
    done = last_per_key(C.load_jsonl(os.path.join(out_dir, RECORDS)))
    if not done:
        raise SystemExit("no records yet")
    C.records_to_frame(sorted(done.values(), key=lambda r: key_of(r))).to_csv(os.path.join(out_dir, "results.csv"),
                                                                             index=False)
    per = per_instance(done)
    per.to_csv(os.path.join(out_dir, "per_instance.csv"), index=False)
    wide = _wide(per)
    st = stage_table(wide)
    st.to_csv(os.path.join(out_dir, "stages.csv"), index=False)
    sh = shapley_table(wide)
    sh.to_csv(os.path.join(out_dir, "shapley.csv"), index=False)
    comp = component_table(per)
    comp.to_csv(os.path.join(out_dir, "components.csv"), index=False)
    mp = metric_pack_table(done, per)
    mp.to_csv(os.path.join(out_dir, "metric_pack.csv"), index=False)
    sol = solver_table(done)
    sol.to_csv(os.path.join(out_dir, "solver.csv"), index=False)
    an = anomalies(done, per)
    fig = plot_stages(st, os.path.join(out_dir, "stages.png")) if not st.empty else None
    eb = per[per.calib == "ebaas"] if not per.empty else per
    settings = sorted({(r.get("threads"), r.get("time_limit_s"), r.get("gurobi_seed"), r.get("n_agg_arcs") is not None)
                       for k, r in done.items() if k[5] == "ilp" and k[1] == "ebaas" and r.get("threads") is not None},
                      key=str)
    summary: Dict[str, Any] = {"round3_headline_pct": ROUND3_HEADLINE, "n_records": len(done), "anomalies": len(an),
                               "ilp_settings_threads_timelimit_seed_aggregate": [list(s) for s in settings]}
    for fam in FAMILIES:
        sub = eb[eb.family == fam] if not eb.empty else eb
        if sub.empty:
            continue
        m, h, n = ci95(sub.g_rel_best_ea)
        summary[fam] = {
            "headline_gap_pct": m, "ci95": h, "n": n,
            "n_positive": int((pd.to_numeric(sub.g_rel_best_ea, errors="coerce") > 0).sum()),
            "best_rule_counts_end_adjusted": sub.best_rule_rel_ea.value_counts().to_dict(),
            "best_rule_counts_written": sub.best_rule_w.value_counts().to_dict(),
            "price_of_recovery_usd_mean": ci95(sub.price_of_recovery)[0],
            "price_of_recovery_end_adjusted_usd_mean": ci95(sub.price_of_recovery_ea)[0],
            "C_end_adjust_best_rule_mean": ci95(sub.B_best_rel_ea_C_end_adjust)[0],
            "C_end_adjust_ilp_relaxed_mean": ci95(sub.I_rel_C_end_adjust)[0],
            "orders_identical_to_legacy": None,
        }
        if not per.empty and "orders_md5" in per.columns:
            leg = per[(per.calib == "legacy") & (per.family == fam)].set_index(["seed", "mult"])["orders_md5"]
            ebs = sub.set_index(["seed", "mult"])["orders_md5"]
            both = leg.index.intersection(ebs.index)
            summary[fam]["orders_identical_to_legacy"] = f"{int((leg[both] == ebs[both]).sum())}/{len(both)}"
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(C.jsonable(summary), fh, indent=1)
    md = write_results_md(out_dir, st, sh, comp, mp, sol, summary, an, fig)
    return md


def write_results_md(out_dir: str, st: pd.DataFrame, sh: pd.DataFrame, comp: pd.DataFrame, mp: pd.DataFrame,
                     sol: pd.DataFrame, summary: Dict[str, Any], an: Sequence[str], fig: Optional[str]) -> str:
    L: List[str] = ["# X1 -- headline re-validation (round 5)", ""]
    L.append("Gap = 100 (baseline - ILP) / baseline per instance, mean with 95 % t-CI. Headline = eBaaS energy, "
             "per-instance best rule (min over r2, r5_range, r5_transfer when services exist, r5; either target copy), "
             "relaxed targets (rho 0, R_end 0), end-adjusted totals (M1). ILP settings (Threads, TimeLimit s, Seed, "
             f"aggregated flow O1) used: {summary.get('ilp_settings_threads_timelimit_seed_aggregate')}. nyc4h gaps are "
             "lower bounds (PRUNING_NYC restricts only the ILP). Legacy ILP values are the stored round-3 rows "
             "(per-bike model, raw totals only).")
    L.append("")
    for fam in FAMILIES:
        s = summary.get(fam)
        if not s:
            continue
        L.append(f"* **{fam}: {C.fmt(s['headline_gap_pct'], 1)} % +/- {C.fmt(s['ci95'], 1)}** (n = {s['n']}, positive "
                 f"on {s['n_positive']}), round 3: {ROUND3_HEADLINE[fam]} %. Price of recovery (written - relaxed ILP): "
                 f"{C.fmt(s['price_of_recovery_usd_mean'], 2)} USD raw, {C.fmt(s['price_of_recovery_end_adjusted_usd_mean'], 2)} "
                 f"USD end-adjusted. C_end_adjust best rule {C.fmt(s['C_end_adjust_best_rule_mean'], 2)} / ILP relaxed "
                 f"{C.fmt(s['C_end_adjust_ilp_relaxed_mean'], 2)} USD. Orders identical to legacy: "
                 f"{s['orders_identical_to_legacy']}.")
    L += ["", "## Survival path (cells where all five stages exist)", ""]
    if not st.empty:
        L.append(C.markdown_table(st, ["group", "stage", "label", "mean_pct_common", "ci95_pct_common", "n_common",
                                       "step_pts_common", "survival_vs_S0_common", "mean_pct", "n", "n_positive"], 2))
    L += ["", "## Shapley decomposition of S0 -> S3 (raw totals) plus the end-state step", ""]
    if not sh.empty:
        L.append(C.markdown_table(sh, ["group", "n", "S0_round3_pct", "a_calibration_pts", "b_best_rule_pts",
                                       "c1_relaxed_targets_pts", "c2_end_adjust_pts", "S4_headline_pct",
                                       "survival_share"], 2))
    L += ["", "## Headline difference by cost component (eBaaS, USD per instance)", ""]
    if not comp.empty:
        cols = ["group", "n", "diff_total_end_adjusted"] + [f"diff_{c}" for c in COMPONENTS]
        L.append(C.markdown_table(comp, cols, 2))
    L += ["", "## A3 metric pack (means)", ""]
    if not mp.empty:
        L.append(C.markdown_table(mp, ["family", "calib", "method", "n"] + METRIC_KEYS, 3))
    L += ["", "## Solver (eBaaS ILP rows)", ""]
    if not sol.empty:
        L.append(C.markdown_table(sol, list(sol.columns), 2))
    L += ["", "## Anomalies", ""]
    L += [f"* {a}" for a in an] or ["* none"]
    if fig:
        L += ["", f"![stages]({os.path.basename(fig)})"]
    L += ["", "Files: records.jsonl, results.csv, per_instance.csv, stages.csv, shapley.csv, components.csv, "
          "metric_pack.csv, solver.csv, summary.json, instances/."]
    p = os.path.join(out_dir, "RESULTS.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return p


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--wall-budget", type=float, default=WALL_BUDGET_S, help="seconds")
    ap.add_argument("--families", nargs="+", default=list(FAMILIES), choices=list(FAMILIES))
    ap.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    ap.add_argument("--mults", nargs="+", type=float, default=list(MULTS))
    ap.add_argument("--no-legacy", action="store_true", help="skip the legacy anchor (rules + round-3 rows)")
    ap.add_argument("--retry-unsolved", action="store_true", help="re-solve TIME_LIMIT rows")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="usd4h seed 0 x0.75 + nyc4h seed 0 (legacy + ebaas), Threads 1, TimeLimit 30 s, then --analyse")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    if args.time_limit > 300 and not args.smoke:
        raise SystemExit("X1 protocol: TimeLimit 300 s")
    if args.threads > 3:
        raise SystemExit("X1 protocol: Threads <= 3")
    out_dir = args.out_dir or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse:
        print(analyse(out_dir))
        return {"analysed": out_dir}
    if args.smoke:
        fams, seeds, mults = list(args.families), [args.seeds[0] if args.seeds != list(SEEDS) else 0], [0.75]
        tl, threads, budget = 30.0, 1, C.WallBudget(3600.0, margin_s=0.0, min_solve_s=1.0)
    else:
        fams, seeds, mults = list(args.families), list(args.seeds), list(args.mults)
        tl, threads, budget = args.time_limit, args.threads, C.WallBudget(args.wall_budget)
    legacy = not args.no_legacy
    existing = last_per_key(C.load_jsonl(os.path.join(out_dir, RECORDS))) if os.path.isdir(out_dir) else {}
    r3_rows, r3_base = round3_ilp_rows(fams, seeds, mults) if legacy else ({}, {})
    done = dict(existing)
    for k, r in r3_rows.items():
        done.setdefault(k, r)
    plan = build_plan(done, fams, seeds, mults, legacy=legacy, retry_unsolved=args.retry_unsolved)
    summary = plan_summary(plan, tl)
    summary.update(out_dir=out_dir, time_limit=tl, threads=threads, wall_budget_min=budget.budget / 60.0,
                   existing_rows=len(existing), round3_rows_to_copy=len([k for k in r3_rows if k not in existing]),
                   families=fams, seeds=seeds, mults=mults, legacy=legacy, aggregate=C.R5_ILP_KWARGS,
                   gurobi_params=C.ILP_PARAMS_R3)
    if args.dry_run:
        print("# plan (family, calib, seed, mult, targets, method):")
        for item in plan:
            print("  ", item)
        print(json.dumps(summary, indent=1))
        return summary
    runner = Runner(out_dir, tl, threads, budget, retry_unsolved=args.retry_unsolved)
    n_seeded = runner.seed_round3(r3_rows, r3_base)
    print(f"# {n_seeded} round-3 ILP rows copied; plan {json.dumps(summary)}", flush=True)
    for fam, cal, seed, mult, items in group_plan(plan):
        runner.run_cell(fam, cal, seed, mult, items)
    wall = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall, "plan": C.jsonable(summary), "rows": runner.n_runs,
                             "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"# X1 runs finished: {runner.n_runs} rows in {wall / 60:.1f} min", flush=True)
    try:
        print(analyse(out_dir))
    except Exception as exc:  # noqa: BLE001
        print(f"# analyse failed: {type(exc).__name__}: {exc}", flush=True)
        if args.smoke:
            raise
    return summary


if __name__ == "__main__":
    main()
