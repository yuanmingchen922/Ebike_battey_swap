"""Experiment E2u, round 3 -- coordination value under USD costs with the service-share
constraint (33), seeds 0-9 (DECISIONS round-3 user decisions, 2026-10-12).

Round-3 decisions applied here (binding):

1. the lexicographic (service-first) variant of round 2 is DROPPED; the service level is
   imposed with (33) ``sum_i (1 - u_i) >= zeta |I|``: ``ilp_zeta90`` (zeta = 0.90, main
   setting) and ``ilp_zeta85`` (zeta = 0.85, sensitivity), passed as
   ``ilp.build_model(zeta=...)`` through :func:`experiments.common.run_zeta_case`.  When a
   zeta run is INFEASIBLE (structurally unservable orders, or more orders than 6 bikes can
   serve) the row records status INFEASIBLE **and** the maximum feasible served share
   (:func:`experiments.common.max_service_share`: one ``min sum u_i`` solve, the
   lexicographic stage 1 alone) so the reader sees why.  When the certified written-model
   optimum already serves >= zeta |I| orders, the zeta-constrained optimum is the written
   one (adding a satisfied constraint cannot change the optimum) and the cell is recorded
   without a solve (``solve_mode = implied_by_written``; ``--no-imply`` forces solves).
2. end-of-horizon targets stay rho = 0.5 / R_end = 1 (``ilp``); the relaxed control
   ``ilp_relaxed`` (rho = 0, R_end = 0) is kept as in round 2.
3. every ILP cell of round 2 that is not solved (OPTIMAL or MIP gap <= 1 %) is re-solved,
   and the seeds are extended from 0-4 to 0-9.

Design (byte-identical instances per (seed, demand) across methods, as in round 2)
---------------------------------------------------------------------------------
* instances: ``experiments.common.make_instance('usd4h', seed, orders_per_bike_hour = 1.5
  x mult)``, ``mult`` in {0.75, 1, 1.5} (27 / 36 / 54 orders), seeds 0-9, ``usd_sunk``;
* arc library: ``pruning_for(inst, reachable=True)`` (lossless, as in round 2);
* methods: ``baseline`` (R2.3 rules), ``ilp`` (written model), ``ilp_zeta90``,
  ``ilp_zeta85``, ``ilp_relaxed``;  Gurobi ``OutputFlag 0``, ``Threads 3``, ``TimeLimit
  300 s``, ``Seed 0`` (:data:`experiments.common.ILP_PARAMS_R3`), MIP start = first clean
  policy schedule (:func:`experiments.common.feasible_mip_start`; for the zeta models the
  written-model schedule when it satisfies (33), else the policy schedule if it does);
* reuse: the LAST round-2 record per ``(seed, mult, cost_variant, method)`` of
  ``outputs/e2u_coord_usd/records.jsonl`` is copied into this directory
  (``source = round2``) when it is a policy row or an ILP row with status OPTIMAL or MIP
  gap <= 1 %; everything else is (re-)solved here (``source = round3``);
* order of work: (a) zeta90 + zeta85 on seeds 0-4; (b) the round-2 fills, then seeds 5-9
  baseline + ilp + zeta90 + relaxed; (c) zeta85 on seeds 5-9.  A wall budget (default
  5 h) shortens the last solve and records the rest as ``SKIPPED_BUDGET``;
* outputs (``outputs/e2u_round3/``): ``records.jsonl`` (one record per run, appended as
  runs finish; the script resumes from it), ``results.csv`` (refreshed after every run),
  ``instances/*.json`` (new seeds), ``run_stdout.log`` (one line per completed run),
  ``wall_time.json``, and with ``--analyse`` ``improvement.csv``, ``zeta_feasibility.csv``,
  ``RESULTS.md``, ``gap_by_demand.png``.

The E2 model (``ilp.py`` / ``arcs.py`` / ``evaluate.py``) is not touched.  Run from
``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/e2u_round3.py --dry-run            # plan only, no solves
    python3 experiments/e2u_round3.py --smoke              # cheapest cell, Threads 1, TimeLimit 30 s
    python3 experiments/e2u_round3.py                      # the round-3 runs (resumable)
    python3 experiments/e2u_round3.py --analyse            # tables, figure, RESULTS.md
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ebike_swap_sim import Instance, Schedule, build_arcs  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import e2u_coord_usd as E2U  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e2u_round3")
ROUND2_RECORDS = os.path.join(C.OUTPUT_ROOT, "e2u_coord_usd", "records.jsonl")
RECORDS = "records.jsonl"
FAMILY = E2U.FAMILY                     # usd4h
VARIANT = E2U.HEADLINE_VARIANT          # usd_sunk
BASE_OPH = E2U.BASE_OPH
MULTS = list(E2U.MULTS)                 # 0.75, 1, 1.5
SEEDS_R2 = [0, 1, 2, 3, 4]
SEEDS_NEW = [5, 6, 7, 8, 9]
TIME_LIMIT = 300.0
WALL_BUDGET_S = 5 * 3600.0
METHODS = ["baseline", "ilp", "ilp_zeta90", "ilp_zeta85", "ilp_relaxed"]
ZETA_OF = {"ilp_zeta90": C.ZETA_MAIN, "ilp_zeta85": C.ZETA_SENS}
#: round-2 methods whose rows are reused (the lexicographic rows are dropped, decision 1)
REUSED_METHODS = ["baseline", "ilp", "ilp_relaxed"]
SHORT = {"baseline": "Baseline (R2.3 rules)", "ilp": "ILP (written, rho 0.5, R_end 1)",
         "ilp_zeta90": "ILP + (33) zeta 0.90", "ilp_zeta85": "ILP + (33) zeta 0.85",
         "ilp_relaxed": "ILP relaxed (rho 0, R_end 0)"}

WorkItem = Tuple[str, int, float, str]   # (phase, seed, mult, method)


# ---------------------------------------------------------------------------
# records and keys
# ---------------------------------------------------------------------------
def key_of(row: Dict[str, Any]) -> Tuple[int, float, str, str]:
    return (int(row["seed"]), float(row["demand_mult"]), str(row["cost_variant"]), str(row["method"]))


def last_per_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[int, float, str, str], Dict[str, Any]]:
    out: Dict[Tuple[int, float, str, str], Dict[str, Any]] = {}
    for r in rows:
        out[key_of(r)] = r
    return out


def row_is_solved(row: Dict[str, Any]) -> bool:
    """A record counts as done when it is a policy row, a reused / solved ILP row (OPTIMAL
    or gap <= 1 %), a proven INFEASIBLE zeta row, or an implied cell."""
    st = row.get("status")
    if st == "POLICY":
        return True
    if st in ("INFEASIBLE", "INF_OR_UNBD"):
        return True
    if row.get("solve_mode") in ("implied_by_written", "implied_by_max_service"):
        return True
    return C.reusable_ilp_row(st, row.get("mip_gap"))


def round2_reusable_rows() -> Dict[Tuple[int, float, str, str], Dict[str, Any]]:
    """Reusable round-2 rows (last record per key, usd_sunk, methods of
    :data:`REUSED_METHODS`, policy rows or ILP rows solved to OPTIMAL / gap <= 1 %)."""
    out = {}
    for k, r in last_per_key(C.load_jsonl(ROUND2_RECORDS)).items():
        seed, mult, variant, method = k
        if variant != VARIANT or method not in REUSED_METHODS or seed not in SEEDS_R2:
            continue
        if row_is_solved(r):
            rr = dict(r)
            rr["source"] = "round2"
            rr["phase"] = "reuse"
            rr["solve_mode"] = "reused"
            out[k] = rr
    return out


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------
def build_plan(done: Dict[Tuple[int, float, str, str], Dict[str, Any]], seeds_r2: Sequence[int] = SEEDS_R2,
               seeds_new: Sequence[int] = SEEDS_NEW, mults: Sequence[float] = MULTS) -> List[WorkItem]:
    """Ordered work items not yet done: (a) zeta90 / zeta85 on ``seeds_r2``; (b) round-2 fills
    (baseline / ilp / ilp_relaxed of ``seeds_r2`` missing or not solved) then ``seeds_new``
    baseline + ilp + zeta90 + relaxed; (c) zeta85 on ``seeds_new``."""
    def todo(seed: int, mult: float, method: str) -> bool:
        r = done.get((seed, float(mult), VARIANT, method))
        return r is None or not row_is_solved(r)

    plan: List[WorkItem] = []
    for seed in seeds_r2:
        for mult in mults:
            for m in ("ilp_zeta90", "ilp_zeta85"):
                if todo(seed, mult, m):
                    plan.append(("a", seed, float(mult), m))
    for seed in seeds_r2:
        for mult in mults:
            for m in ("baseline", "ilp", "ilp_relaxed"):
                if todo(seed, mult, m):
                    plan.append(("b", seed, float(mult), m))
    for seed in seeds_new:
        for mult in mults:
            for m in ("baseline", "ilp", "ilp_zeta90", "ilp_relaxed"):
                if todo(seed, mult, m):
                    plan.append(("b", seed, float(mult), m))
    for seed in seeds_new:
        for mult in mults:
            if todo(seed, mult, "ilp_zeta85"):
                plan.append(("c", seed, float(mult), "ilp_zeta85"))
    return plan


def group_plan(plan: Sequence[WorkItem]) -> List[Tuple[str, int, float, List[str]]]:
    """Consecutive items of one (phase, seed, mult) share one instance / library build."""
    groups: List[Tuple[str, int, float, List[str]]] = []
    for phase, seed, mult, method in plan:
        if groups and groups[-1][0] == phase and groups[-1][1] == seed and groups[-1][2] == mult:
            groups[-1][3].append(method)
        else:
            groups.append((phase, seed, mult, [method]))
    return groups


def plan_summary(plan: Sequence[WorkItem], reused: int) -> Dict[str, Any]:
    per_phase: Dict[str, int] = {}
    per_method: Dict[str, int] = {}
    for phase, _s, _m, method in plan:
        per_phase[phase] = per_phase.get(phase, 0) + 1
        per_method[method] = per_method.get(method, 0) + 1
    n_ilp = sum(v for k, v in per_method.items() if k != "baseline")
    return {"reused_round2_rows": reused, "work_items": len(plan), "ilp_items": n_ilp,
            "per_phase": per_phase, "per_method": per_method,
            "instances": len({(s, m) for _p, s, m, _me in plan}),
            "expected_wall_min_at_120s": round(n_ilp * 120 / 60.0, 1),
            "worst_wall_min_at_300s": round(n_ilp * 300 / 60.0, 1)}


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------
PRUNING_LABEL = "plan+reachable"


def zeta_cols(rec: Dict[str, Any]) -> Dict[str, Any]:
    ms = rec.get("max_service") or {}
    return {
        "zeta": rec.get("zeta"), "zeta_min_served": rec.get("zeta_min_served"),
        "zeta_feasible": rec.get("zeta_feasible"), "start_satisfies_zeta": rec.get("start_satisfies_zeta"),
        "ms_status": ms.get("status"), "ms_min_unserved": ms.get("min_unserved"),
        "ms_min_unserved_bound": ms.get("min_unserved_bound"),
        "ms_share_achievable": ms.get("share_achievable"), "ms_share_upper_bound": ms.get("share_upper_bound"),
        "ms_certified": ms.get("certified"), "ms_runtime_s": ms.get("runtime"),
        "ms_n_unservable": ms.get("n_unservable"),
    }


def implied_row(written: Dict[str, Any], method: str, zeta: float, phase: str) -> Dict[str, Any]:
    """Zeta cell implied by a certified written optimum that serves >= zeta |I| orders:
    the written row's costs / metrics with the zeta bookkeeping, no solve."""
    row = {k: v for k, v in written.items() if k != "wall_clock"}
    row.update({
        "method": method, "status": "OPTIMAL", "solve_mode": "implied_by_written", "source": "round3",
        "phase": phase, "runtime_s": 0.0, "mip_start_variant": "written_optimum",
        "mip_start_accepted": None, "zeta": zeta,
        "zeta_min_served": math.ceil(zeta * int(written["n_orders"]) - 1e-9), "zeta_feasible": True,
        "implied_from_status": written.get("status"), "implied_from_mip_gap": written.get("mip_gap"),
        "implied_from_source": written.get("source", "round3"),
    })
    return row


def skipped_row(inst: Instance, n_arcs: int, method: str, phase: str, reason: str) -> Dict[str, Any]:
    row = E2U.base_row(inst, _FakeLib(n_arcs), method, VARIANT, PRUNING_LABEL)
    row.update({"status": C.SKIPPED_BUDGET, "skip_reason": reason, "source": "round3", "phase": phase,
                "solve_mode": "skipped", "zeta": ZETA_OF.get(method)})
    return row


class _FakeLib:
    """Only ``len()`` is needed by :func:`E2U.base_row`."""
    def __init__(self, n: int) -> None:
        self.n = int(n)

    def __len__(self) -> int:
        return self.n


# ---------------------------------------------------------------------------
# one instance
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, out_dir: str, time_limit: float, threads: int, budget: C.WallBudget,
                 imply: bool = True, force: bool = False) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.path = os.path.join(out_dir, RECORDS)
        self.time_limit = float(time_limit)
        self.threads = int(threads)
        self.budget = budget
        self.imply = imply
        self.force = force
        self.done = last_per_key(C.load_jsonl(self.path))
        self.n_runs = 0

    # -- output -----------------------------------------------------------
    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("source", "round3")
        C.append_jsonl(self.path, row)
        self.done[key_of(row)] = row
        self.refresh_csv()
        self.n_runs += 1
        keys = ("name", "method", "phase", "status", "solve_mode", "total", "n_unserved", "served_share",
                "mip_gap", "runtime_s", "mip_start_variant", "mip_start_accepted", "zeta_feasible",
                "ms_share_achievable", "ms_certified")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys}), flush=True)

    def refresh_csv(self) -> None:
        df = C.records_to_frame(sorted(self.done.values(), key=lambda r: (r["seed"], r["demand_mult"], r["method"])))
        df.to_csv(os.path.join(self.out_dir, "results.csv"), index=False)

    def seed_reused(self, reused: Dict[Tuple[int, float, str, str], Dict[str, Any]]) -> int:
        n = 0
        for k, r in reused.items():
            if k not in self.done:
                C.append_jsonl(self.path, r)
                self.done[k] = r
                n += 1
        if n:
            self.refresh_csv()
        return n

    # -- one instance -----------------------------------------------------
    def run_group(self, phase: str, seed: int, mult: float, methods: Sequence[str]) -> None:
        t_all = time.perf_counter()
        inst = E2U.make_inst(seed, mult, VARIANT)
        inst_dir = C.ensure_dir(os.path.join(self.out_dir, "instances"))
        p = os.path.join(inst_dir, inst.meta["name"] + ".json")
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(inst.to_json())
        pr = C.pruning_for(inst, reachable=True)
        lib, t_lib = C.build_library(inst, pr)
        n = len(inst.orders)

        def finish(row: Dict[str, Any], method: str) -> None:
            row["lib_build_time_s"] = t_lib
            row["phase"] = phase
            row["source"] = "round3"
            row.setdefault("solve_mode", "solved")
            row["time_limit_s"] = row.get("time_limit_s") or self.time_limit
            row["threads"] = self.threads
            self.emit(row)

        base = C.run_baseline_case(inst, lib, None, "baseline")
        if "baseline" in methods:
            finish(E2U.baseline_row(inst, lib, base, "baseline", VARIANT, PRUNING_LABEL), "baseline")
        start, start_label = C.feasible_mip_start(inst, lib, base)

        written_row = self.done.get((seed, float(mult), VARIANT, "ilp"))
        written_sched: Optional[Schedule] = None
        if "ilp" in methods:
            tl = self.budget.solve_limit(self.time_limit)
            if tl is None:
                finish(skipped_row(inst, len(lib), "ilp", phase, "wall budget exhausted"), "ilp")
            else:
                rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads,
                                     label="ilp", params=C.ILP_PARAMS_R3)
                row = E2U.ilp_row(inst, lib, rec, "ilp", VARIANT, PRUNING_LABEL, start_label)
                row["time_limit_s"] = tl
                finish(row, "ilp")
                written_row = row
                written_sched = rec["schedule"]

        ms_cache: Optional[Dict[str, Any]] = None
        for method in ("ilp_zeta90", "ilp_zeta85"):
            if method not in methods:
                continue
            zeta = ZETA_OF[method]
            if (self.imply and written_row is not None and written_row.get("status") != C.SKIPPED_BUDGET
                    and C.zeta_implied_by_written(written_row.get("status"), written_row.get("served_share"), zeta,
                                                  written_row.get("mip_gap"))):
                finish(implied_row(written_row, method, zeta, phase), method)
                continue
            if ms_cache is not None and ms_cache.get("certified") and ms_cache.get("share_achievable") is not None \
                    and ms_cache["share_achievable"] < zeta - 1e-9:
                # the certified maximum share (from the zeta90 run) is below this zeta: infeasible by bound
                row = E2U.base_row(inst, lib, method, VARIANT, PRUNING_LABEL)
                row.update({"status": "INFEASIBLE", "solve_mode": "implied_by_max_service", "runtime_s": 0.0,
                            "check_ok": None, "families": "{}", "mip_start_variant": None, "mip_start_accepted": None})
                row.update(zeta_cols({"zeta": zeta, "zeta_min_served": math.ceil(zeta * n - 1e-9),
                                      "zeta_feasible": False, "max_service": ms_cache}))
                finish(row, method)
                continue
            tl = self.budget.solve_limit(self.time_limit)
            if tl is None:
                finish(skipped_row(inst, len(lib), method, phase, "wall budget exhausted"), method)
                continue
            ms_tl = max(10.0, min(self.time_limit, self.budget.remaining() - tl - self.budget.margin))
            zstart = written_sched if written_sched is not None else start
            rec = C.run_zeta_case(inst, lib, zeta, mip_start=zstart, time_limit=tl, threads=self.threads,
                                  label=method, max_service_start=zstart, max_service_time_limit=ms_tl)
            label = ("written_ilp" if written_sched is not None else start_label) if rec.get("start_satisfies_zeta") \
                else "none(start violates zeta)"
            row = E2U.ilp_row(inst, lib, rec, method, VARIANT, PRUNING_LABEL, label)
            row.update(zeta_cols(rec))
            row["time_limit_s"] = tl
            finish(row, method)
            if rec.get("max_service"):
                ms_cache = rec["max_service"]

        if "ilp_relaxed" in methods:
            tl = self.budget.solve_limit(self.time_limit)
            if tl is None:
                finish(skipped_row(inst, len(lib), "ilp_relaxed", phase, "wall budget exhausted"), "ilp_relaxed")
            else:
                rinst = C.relax_end_targets(inst)
                rinst.meta["name"] = inst.meta["name"]
                rlib = build_arcs(rinst, **lib.options)
                if len(rlib) != len(lib):
                    raise RuntimeError("relaxed library differs in size from the original")
                r1 = C.run_baseline_case(inst, lib, C.baseline_variant_params("baseline_round1", inst), "baseline_round1")
                cands: List[Tuple[str, Schedule]] = [("default", base["schedule"]), ("baseline_round1", r1["schedule"])]
                if written_sched is not None:
                    cands.insert(0, ("written_ilp", written_sched))
                rstart, rlabel = E2U.pick_start(rinst, rlib, cands)
                rec = C.run_ilp_case(rinst, rlib, mip_start=rstart, time_limit=tl, threads=self.threads,
                                     label="ilp_relaxed", params=C.ILP_PARAMS_R3)
                row = E2U.ilp_row(rinst, rlib, rec, "ilp_relaxed", VARIANT, PRUNING_LABEL, rlabel)
                row["rho"], row["R_end_sum"] = 0.0, 0
                row["time_limit_s"] = tl
                finish(row, "ilp_relaxed")
        print(f"# {inst.meta['name']} phase {phase} methods {list(methods)} done in "
              f"{time.perf_counter() - t_all:.0f} s (budget left {self.budget.remaining() / 60:.0f} min)", flush=True)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def analyse(out_dir: str) -> str:
    recs = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not recs:
        raise SystemExit("no records yet")
    rows = list(last_per_key(recs).values())
    df = pd.DataFrame(rows)
    for c in ["total"] + E2U.COMPONENTS + ["mip_gap", "runtime_s", "n_unserved", "n_orders", "served_share",
                                           "ms_share_achievable", "ms_share_upper_bound", "zeta"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values(["demand_mult", "seed", "method"]).reset_index(drop=True)
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    pairs = [(f"{SHORT[m]} vs baseline R2.3", "baseline", m, VARIANT) for m in METHODS if m != "baseline"]
    imp = E2U.improvement_table(df, pairs)
    imp.to_csv(os.path.join(out_dir, "improvement.csv"), index=False)
    zcols = ["name", "seed", "demand_mult", "n_orders", "method", "zeta", "zeta_min_served", "status", "solve_mode",
             "zeta_feasible", "total", "n_unserved", "served_share", "mip_gap", "runtime_s", "ms_status",
             "ms_min_unserved", "ms_min_unserved_bound", "ms_share_achievable", "ms_share_upper_bound", "ms_certified",
             "ms_n_unservable"]
    zdf = df[df.method.isin(list(ZETA_OF))]
    zdf = zdf[[c for c in zcols if c in zdf.columns]]
    zdf.to_csv(os.path.join(out_dir, "zeta_feasibility.csv"), index=False)
    ilp_rows = df[df.method != "baseline"]
    solver = (ilp_rows.groupby(["method", "demand_mult"])
              .agg(n=("status", "size"), optimal=("status", lambda s: int((s == "OPTIMAL").sum())),
                   time_limit=("status", lambda s: int((s == "TIME_LIMIT").sum())),
                   infeasible=("status", lambda s: int(s.isin(["INFEASIBLE", "INF_OR_UNBD"]).sum())),
                   skipped=("status", lambda s: int((s == C.SKIPPED_BUDGET).sum())),
                   implied=("solve_mode", lambda s: int(s.isin(["implied_by_written", "implied_by_max_service"]).sum())),
                   gap_max=("mip_gap", "max"), runtime_mean=("runtime_s", "mean"), runtime_max=("runtime_s", "max"))
              .reset_index())
    fig = os.path.join(out_dir, "gap_by_demand.png")
    try:
        _plot_gap(imp, fig)
    except Exception as exc:  # noqa: BLE001
        fig = f"(figure failed: {exc})"
    svc_cols = ["total", "served_share", "n_unserved", "mean_response_h", "mean_lateness_h", "n_late", "bike_km",
                "n_swaps", "kwh_purchased", "end_full_total"]
    means = (df.groupby(["demand_mult", "method"])[[c for c in svc_cols if c in df.columns]]
             .mean(numeric_only=True).reset_index())
    means["n"] = df.groupby(["demand_mult", "method"]).size().values
    md: List[str] = ["# E2u round 3 -- coordination value with the service-share constraint (33), seeds 0-9", ""]
    md.append(f"Family `{FAMILY}` ({VARIANT}), demand x0.75 / x1 / x1.5, seeds {sorted(df.seed.unique().tolist())}; "
              f"methods {METHODS}; zeta 0.90 (main) / 0.85 (sensitivity); Gurobi Threads {C.THREADS}, TimeLimit "
              f"{TIME_LIMIT:.0f} s, Seed 0; rows with `source = round2` are reused round-2 records (OPTIMAL or gap "
              f"<= 1 %), `solve_mode = implied_by_written` cells are certified written optima that already serve "
              f">= zeta |I| orders (no solve needed), `implied_by_max_service` cells are infeasible by the certified "
              f"maximum share of the zeta-0.90 run. Gap = 100 (baseline - ILP) / baseline, mean over seeds, 95 % t-CI.")
    md.append("")
    md.append("## Gap per method and demand level")
    md.append(C.markdown_table(imp, ["comparison", "demand_mult", "n", "gap_mean_pct", "gap_ci95_pct", "gap_lo_pct",
                                     "gap_hi_pct", "abs_gain_mean", "policy_total_mean", "ilp_total_mean"], 2))
    md.append("")
    md.append("Zeta rows enter the gap only when they have a total (feasible); INFEASIBLE cells are listed below.")
    md.append("")
    md.append("## Service-share feasibility (zeta runs)")
    md.append(C.markdown_table(zdf, list(zdf.columns), 3))
    md.append("")
    md.append("`ms_*` = maximum feasible served share (min sum u solve) recorded for INFEASIBLE / undecided cells: "
              "`ms_share_achievable` is reached by the incumbent, `ms_share_upper_bound` from Gurobi's bound; "
              "`ms_n_unservable` orders have no delivery arc at all.")
    md.append("")
    md.append("## Means per method and demand level")
    md.append(C.markdown_table(means, list(means.columns), 3))
    md.append("")
    md.append("## Solver statistics")
    md.append(C.markdown_table(solver, list(solver.columns), 3))
    md.append("")
    md.append(f"Figure: `{os.path.basename(fig)}`")
    path = os.path.join(out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


def _plot_gap(imp: pd.DataFrame, path: str) -> None:
    import matplotlib.pyplot as plt
    comps = [c for c in imp.comparison.unique()]
    levels = sorted(MULTS) + ["all"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    width = 0.8 / max(1, len(comps))
    for ci, comp in enumerate(comps):
        sub = imp[imp.comparison == comp].set_index("demand_mult")
        xs = [i + (ci - (len(comps) - 1) / 2) * width for i in range(len(levels))]
        means = [float(sub.loc[lv, "gap_mean_pct"]) if lv in sub.index else float("nan") for lv in levels]
        errs = [float(sub.loc[lv, "gap_ci95_pct"]) if lv in sub.index else 0.0 for lv in levels]
        errs = [0.0 if (e is None or math.isnan(e)) else e for e in errs]
        ax.bar(xs, means, width * 0.92, yerr=errs, capsize=3, color=E2U.PALETTE[ci % len(E2U.PALETTE)],
               edgecolor="white", linewidth=0.8, label=comp)
    ax.axhline(0, color="#9a9a96", linewidth=0.8)
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels([f"demand {E2U._mlabel(lv)}" for lv in levels])
    ax.set_ylabel("gap = 100 (policy - ILP) / policy  [%]")
    ax.set_title("E2u round 3: coordination value, usd4h, seeds 0-9, 95 % t-CI", fontsize=10)
    E2U._style(ax)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=None, help=f"default {OUT_DIR} (or {OUT_DIR}_smoke with --smoke)")
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--wall-budget", type=float, default=WALL_BUDGET_S, help="seconds")
    ap.add_argument("--seeds-r2", nargs="*", type=int, default=SEEDS_R2)
    ap.add_argument("--seeds-new", nargs="*", type=int, default=SEEDS_NEW)
    ap.add_argument("--mults", nargs="+", type=float, default=MULTS)
    ap.add_argument("--dry-run", action="store_true", help="print the plan, solve nothing, write nothing")
    ap.add_argument("--smoke", action="store_true", help="one cheapest cell (seed 0 x0.75 ilp_zeta90), Threads 1, TimeLimit 30")
    ap.add_argument("--no-imply", action="store_true", help="solve zeta cells even when implied by the written optimum")
    ap.add_argument("--analyse", action="store_true", help="tables / figure / RESULTS.md from records.jsonl")
    args = ap.parse_args(argv)
    if args.time_limit > 300 and not args.smoke:
        raise SystemExit("round-3 rule: TimeLimit <= 300 s for E2u")
    out_dir = args.out_dir or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse:
        print(analyse(out_dir))
        return {"analysed": out_dir}

    reused = round2_reusable_rows()
    if args.smoke:
        budget = C.WallBudget(3600.0, margin_s=0.0, min_solve_s=1.0)
        runner = Runner(out_dir, 30.0, 1, budget, imply=False, force=True)
        seed, mult = args.seeds_r2[0] if args.seeds_r2 else 0, min(args.mults)
        runner.run_group("smoke", seed, mult, ["baseline", "ilp_zeta90"])
        print(f"# smoke done: {runner.n_runs} rows -> {runner.path}", flush=True)
        return {"smoke": runner.path, "rows": runner.n_runs}

    existing = last_per_key(C.load_jsonl(os.path.join(out_dir, RECORDS))) if os.path.isdir(out_dir) else {}
    done = dict(existing)
    for k, r in reused.items():
        done.setdefault(k, r)
    plan = build_plan(done, args.seeds_r2, args.seeds_new, args.mults)
    summary = plan_summary(plan, len(reused))
    summary.update(out_dir=out_dir, time_limit=args.time_limit, threads=args.threads,
                   wall_budget_min=args.wall_budget / 60.0, existing_round3_rows=len(existing))
    if args.dry_run:
        print("# plan (phase, seed, mult, method):")
        for item in plan:
            print("  ", item)
        print(json.dumps(summary, indent=1))
        return summary
    budget = C.WallBudget(args.wall_budget)
    runner = Runner(out_dir, args.time_limit, args.threads, budget, imply=not args.no_imply)
    n_seeded = runner.seed_reused(reused)
    print(f"# {n_seeded} round-2 rows copied; plan {json.dumps(summary)}", flush=True)
    for phase, seed, mult, methods in group_plan(plan):
        runner.run_group(phase, seed, mult, methods)
    wall = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall, "plan": summary, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"# round-3 E2u runs finished: {runner.n_runs} rows in {wall / 60:.1f} min", flush=True)
    try:
        print(analyse(out_dir))
    except Exception as exc:  # noqa: BLE001 - the records are the deliverable; the report can be regenerated
        print(f"# analyse failed: {exc}", flush=True)
    return summary


if __name__ == "__main__":
    main()
