"""Experiment E4u, round 3 -- station sizing under USD: fill the ILP cells the round-2 wall
budget skipped and extend the default size, the B sweep and the free-size run to seeds 3-5
(DECISIONS round-3 decision (3)).

Everything is the design of ``experiments/e4u_sizing_usd.py`` (family ``usd4h``, 3
co-located sites, ``usd_sunk`` prices, R2.3 baseline, plan pruning + lossless reachable
pruning); its helpers (``sized_instance``, ``chain_start``, ``_schedule_row``,
``_extra_metrics``, ``report``) are imported.  Round-3 rules:

* reuse: the 29 round-2 ILP rows of ``outputs/e4u_sizing_usd/results.csv`` (28 OPTIMAL,
  1 TIME_LIMIT at MIP gap 0.29 % <= 1 %) are copied (``source = round2``); the baseline is
  recomputed at EVERY cell (milliseconds, same code path; it reproduced the stored rows
  exactly in round 2, ``results_baseline_fill.csv``);
* ILP cells solved here, in this order: (1) the P sweep ``P_j in {1.4, 2.8, 4.2} kW`` at
  ``B_j = 3, C_j = 4`` for seeds 0-2 (9 cells) and the skipped seed-2 ``B3_C4_P4`` cell of
  the C sweep; (2) the 12 off-line ``B x C`` cells (``B in {1,2,3,4,6} x C in {1,2,3,4}``
  minus the two sweep lines) on seed 0; (3) seeds 3-5: the B sweep ``B_j in {1,2,3,4,6}``
  at ``C_j = 2, P_j = 4 kW`` (which contains the default size ``B3_C2_P4``) in ascending
  order with chained MIP starts, then the free-size ILP (``B_j, C_j`` free, ``y_j = 1``)
  and the baseline (plus the fixed-size ILP when off the grid) at the chosen sizes;
* Gurobi ``OutputFlag 0``, ``Threads 3``, ``TimeLimit 300 s``, ``Seed 0``; wall budget 4 h
  (remaining cells recorded as ``SKIPPED_BUDGET``); ``records.jsonl`` appended per run,
  ``results.csv`` refreshed per run, one printed line per completed run; ``--analyse``
  rebuilds the round-2 script's summaries, figures and ``RESULTS.md`` on the union.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/e4u_round3.py --dry-run
    python3 experiments/e4u_round3.py --smoke        # seed 0 B3_C2_P4, Threads 1, TimeLimit 30 s
    python3 experiments/e4u_round3.py
    python3 experiments/e4u_round3.py --analyse
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

from ebike_swap_sim import Instance, Schedule, facility_vars  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import e4u_sizing_usd as E4U  # noqa: E402
from experiments.e4_sizing import _schedule_row, _uniform, sized_instance  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e4u_round3")
ROUND2_CSV = os.path.join(C.OUTPUT_ROOT, "e4u_sizing_usd", "results.csv")
RECORDS = "records.jsonl"
FAMILY = E4U.FAMILY
SEEDS_R2 = [0, 1, 2]
SEEDS_NEW = [3, 4, 5]
HEAT_SEEDS = [0]
TIME_LIMIT = 300.0
WALL_BUDGET_S = 4 * 3600.0
B_SWEEP, C_SWEEP, P_SWEEP = list(E4U.B_SWEEP), list(E4U.C_SWEEP), list(E4U.P_SWEEP)
BASE_B, BASE_C, BASE_P, P_SWEEP_C = E4U.BASE_B, E4U.BASE_C, E4U.BASE_P, E4U.P_SWEEP_C

Key = Tuple[int, str, str]                        # (seed, tag, method)
WorkItem = Tuple[str, int, str, int, int, float]  # (phase, seed, sweep, B, C, P); B/C = -1 -> free


def tag_of(B: int, C_: int, P: float) -> str:
    return f"B{B}_C{C_}_P{P:g}"


# ---------------------------------------------------------------------------
# reuse
# ---------------------------------------------------------------------------
def round2_ilp_rows() -> Dict[Key, Dict[str, Any]]:
    if not os.path.exists(ROUND2_CSV):
        return {}
    out: Dict[Key, Dict[str, Any]] = {}
    for _, r in pd.read_csv(ROUND2_CSV).iterrows():
        row = {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.to_dict().items()}
        if row["method"] == "ILP" and C.reusable_ilp_row(row.get("status"), row.get("gap")):
            row["source"] = "round2"
            row["phase"] = "reuse"
            out[(int(row["seed"]), str(row["tag"]), "ILP")] = row
    return out


def row_is_solved(row: Dict[str, Any]) -> bool:
    if row.get("method") == "baseline":
        return True
    if C.reusable_ilp_row(row.get("status"), row.get("gap")):
        return True
    return row.get("source") == "round3" and row.get("status") in ("TIME_LIMIT", "INFEASIBLE", "INF_OR_UNBD")


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------
def build_plan(done: Dict[Key, Dict[str, Any]], seeds_r2: Sequence[int] = SEEDS_R2,
               seeds_new: Sequence[int] = SEEDS_NEW, heat_seeds: Sequence[int] = HEAT_SEEDS) -> List[WorkItem]:
    def todo(seed: int, tag: str) -> bool:
        r = done.get((seed, tag, "ILP"))
        return r is None or not row_is_solved(r)

    plan: List[WorkItem] = []
    for seed in seeds_r2:                                  # (1) P sweep + skipped C-sweep cell
        for P in P_SWEEP:
            if todo(seed, tag_of(BASE_B, P_SWEEP_C, P)):
                plan.append(("P", seed, "P", BASE_B, P_SWEEP_C, P))
        if todo(seed, tag_of(BASE_B, P_SWEEP_C, BASE_P)):
            plan.append(("C", seed, "C", BASE_B, P_SWEEP_C, BASE_P))
    for seed in heat_seeds:                                # (2) off-line B x C cells
        for B in B_SWEEP:
            for C_ in C_SWEEP:
                if (B == BASE_B or C_ == BASE_C):
                    continue
                if todo(seed, tag_of(B, C_, BASE_P)):
                    plan.append(("heat", seed, "heat", B, C_, BASE_P))
    for seed in seeds_new:                                 # (3) B sweep (default size included) + free
        for B in B_SWEEP:
            if todo(seed, tag_of(B, BASE_C, BASE_P)):
                plan.append(("B", seed, "B", B, BASE_C, BASE_P))
        if todo(seed, "free"):
            plan.append(("free", seed, "free", -1, -1, BASE_P))
    return plan


def plan_summary(plan: Sequence[WorkItem], reused: int) -> Dict[str, Any]:
    per_phase: Dict[str, int] = {}
    for phase, *_rest in plan:
        per_phase[phase] = per_phase.get(phase, 0) + 1
    n_free = per_phase.get("free", 0)
    n_ilp = len(plan) + n_free                            # a free run may add one fixed-size ILP
    return {"reused_round2_ilp_rows": reused, "ilp_items": len(plan), "ilp_items_incl_free_fixed": n_ilp,
            "per_phase": per_phase, "expected_wall_min_at_120s": round(n_ilp * 120 / 60.0, 1),
            "worst_wall_min_at_300s": round(n_ilp * 300 / 60.0, 1)}


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, out_dir: str, time_limit: float, threads: int, budget: C.WallBudget) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.path = os.path.join(out_dir, RECORDS)
        self.time_limit, self.threads, self.budget = float(time_limit), int(threads), budget
        self.done: Dict[Key, Dict[str, Any]] = {(int(r["seed"]), str(r["tag"]), str(r["method"])): r
                                                for r in C.load_jsonl(self.path)}
        self.bases: Dict[int, Instance] = {}
        self.n_runs = 0
        self.skipped: List[str] = []

    def base_of(self, seed: int) -> Instance:
        if seed not in self.bases:
            self.bases[seed] = C.make_instance(FAMILY, seed=seed)
        return self.bases[seed]

    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("source", "round3")
        C.append_jsonl(self.path, row)
        self.done[(int(row["seed"]), str(row["tag"]), str(row["method"]))] = row
        self.refresh_csv()
        self.n_runs += 1
        keys = ("seed", "sweep", "tag", "method", "status", "total", "served_share", "gap", "runtime_s",
                "mip_start_accepted", "mip_start_variant", "chosen_B", "chosen_C", "phase")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys}), flush=True)

    def refresh_csv(self) -> None:
        rows = sorted(self.done.values(), key=lambda r: (int(r["seed"]), str(r["tag"]), str(r["method"])))
        C.records_to_frame(rows).to_csv(os.path.join(self.out_dir, "results.csv"), index=False)

    def seed_reused(self, reused: Dict[Key, Dict[str, Any]]) -> int:
        n = 0
        for k, r in reused.items():
            if k not in self.done:
                C.append_jsonl(self.path, r)
                self.done[k] = r
                n += 1
        if n:
            self.refresh_csv()
        return n

    # -- one sized variant (baseline + ILP), round-2 run_variant with Seed 0 ----------
    def run_variant(self, inst: Instance, sweep: str, phase: str, free: bool = False,
                    run_baseline: bool = True, run_ilp: bool = True,
                    chain: Optional[Tuple[Schedule, str]] = None) -> Dict[str, Any]:
        lib, t_build = C.build_library(inst, C.pruning_for(inst, **E4U.PRUNING))
        var = inst.meta["variant"]
        common = {
            "seed": inst.meta.get("seed"), "family": inst.meta.get("family"), "sweep": sweep,
            "tag": var["tag"], "free_sizes": free, "rho": inst.rho,
            "B_j": _uniform(var["B"]), "C_j": _uniform(var["C"]), "P_kw": _uniform(var["P_kw"]),
            "B_sites": json.dumps(var["B"]), "C_sites": json.dumps(var["C"]),
            "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
            "q0_mean": sum(b.q0 for b in inst.bikes) / len(inst.bikes),
            "p_ch_kw": inst.disc.p_ch_kw, "n_arcs": len(lib), "arc_build_s": t_build,
            "cost_variant": inst.meta.get("cost_variant"), "phase": phase, "source": "round3",
            "threads": self.threads,
        }
        extras: Dict[str, Any] = {}
        start: Optional[Schedule] = None
        start_label: Optional[str] = None
        if run_baseline and not free:
            base = C.run_baseline_case(inst, lib)
            start, start_label = C.feasible_mip_start(inst, lib, base)
            if chain is not None and (start_label == "default" and base["families"]):
                start, start_label = E4U.chain_start(chain[0], inst, lib), f"chain:{chain[1]}"
            key = (int(inst.meta["seed"]), var["tag"], "baseline")
            if key not in self.done:
                self.emit({**common, "method": "baseline", "mip_start_variant": None,
                           **_schedule_row(inst, lib, base, base["schedule"]), **E4U._extra_metrics(base),
                           "baseline_report_only_ok": base["ok_modulo_report_only"],
                           "stock_aware_fallbacks": base["flags"].get("stock_aware_fallbacks"),
                           "jit_dispatches": base["flags"].get("jit_dispatches")})
        if not run_ilp:
            return extras
        tl = self.budget.solve_limit(self.time_limit)
        if tl is None:
            self.skipped.append(f"seed {inst.meta['seed']} {var['tag']}")
            self.emit({**common, "method": "ILP", "status": C.SKIPPED_BUDGET, "mip_start_variant": start_label,
                       "skip_reason": f"wall budget exhausted after {self.budget.elapsed():.0f}s", "total": None})
            return extras
        ilp = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads, label="ilp",
                             params=C.ILP_PARAMS_R3)
        self.emit({**common, "method": "ILP", "mip_start_variant": start_label, "time_limit_used_s": tl,
                   **_schedule_row(inst, lib, ilp, ilp["schedule"]), **E4U._extra_metrics(ilp)})
        if ilp["schedule"] is not None:
            _y, Bc, Cc = facility_vars(inst, ilp["schedule"])
            sch = ilp["schedule"]
            sch.meta["_lib"] = lib
            extras = {"B": {str(j): int(v) for j, v in Bc.items()}, "C": {str(j): int(v) for j, v in Cc.items()},
                      "_schedule": sch}
        return extras

    def run_fixed(self, phase: str, seed: int, sweep: str, B: int, C_: int, P: float,
                  chain: Optional[Tuple[Schedule, str]]) -> Optional[Tuple[Schedule, str]]:
        tag = tag_of(B, C_, P)
        inst = sized_instance(self.base_of(seed), B=B, C_=C_, P=P, tag=tag)
        need_ilp = (seed, tag, "ILP") not in self.done or not row_is_solved(self.done[(seed, tag, "ILP")])
        extras = self.run_variant(inst, sweep, phase, chain=chain, run_ilp=need_ilp)
        if extras.get("_schedule") is not None:
            return extras["_schedule"], tag
        return chain

    def run_free(self, phase: str, seed: int) -> None:
        base = self.base_of(seed)
        inst_free = sized_instance(base, P=BASE_P, free=True, tag="free")
        extras = self.run_variant(inst_free, "free", phase, free=True, run_baseline=False)
        if not extras:
            return
        Bu, Cu = _uniform(extras["B"]), _uniform(extras["C"])
        on_grid = any(k[0] == seed and k[2] == "ILP" and r.get("sweep") not in ("free", "free_fixed")
                      and r.get("B_j") == Bu and r.get("C_j") == Cu and r.get("P_kw") == BASE_P
                      and row_is_solved(r) for k, r in self.done.items())
        inst_fix = sized_instance(base, B=extras["B"], C_=extras["C"], P=BASE_P, tag="free_fixed")
        self.run_variant(inst_fix, "free_fixed", phase, run_ilp=not on_grid, chain=(extras["_schedule"], "free"))

    def run_plan(self, plan: Sequence[WorkItem]) -> None:
        chain: Optional[Tuple[Schedule, str]] = None
        last: Tuple[Any, Any] = (None, None)
        for phase, seed, sweep, B, C_, P in plan:
            if (phase, seed) != last:
                chain, last = None, (phase, seed)
            if phase == "heat":
                chain = None
            if sweep == "free":
                self.run_free(phase, seed)
                continue
            chain = self.run_fixed(phase, seed, sweep, B, C_, P, chain)
            # baseline at the P-sweep / heat cells of other seeds is cheap and keeps "baseline at every cell"
        self.fill_baselines()

    def fill_baselines(self) -> None:
        """Baseline at every ILP cell of the frame that has no baseline row yet (ms each)."""
        for (seed, tag, method), r in list(self.done.items()):
            if method != "ILP" or (seed, tag, "baseline") in self.done or tag in ("free",):
                continue
            if tag == "free_fixed":
                try:
                    B = json.loads(r["B_sites"]) if isinstance(r.get("B_sites"), str) else None
                    Cc = json.loads(r["C_sites"]) if isinstance(r.get("C_sites"), str) else None
                except (TypeError, ValueError):
                    B = Cc = None
                if not B or not Cc:
                    continue
                inst = sized_instance(self.base_of(seed), B=B, C_=Cc, P=BASE_P, tag="free_fixed")
                sweep = "free_fixed"
            else:
                inst = sized_instance(self.base_of(seed), B=int(r["B_j"]), C_=int(r["C_j"]), P=float(r["P_kw"]), tag=tag)
                sweep = str(r.get("sweep"))
            self.run_variant(inst, sweep, "baseline_fill", run_ilp=False)


# ---------------------------------------------------------------------------
# analysis (round-2 script's report on the union)
# ---------------------------------------------------------------------------
def analyse(out_dir: str, time_limit: float = TIME_LIMIT) -> str:
    rows = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not rows:
        raise SystemExit("no records yet")
    last: Dict[Key, Dict[str, Any]] = {}
    for r in rows:
        last[(int(r["seed"]), str(r["tag"]), str(r["method"]))] = r
    df = C.records_to_frame(list(last.values()))
    num = ["total", "operational", "C_setup", "C_elec", "C_travel", "C_orders", "unserved", "response", "lateness",
           "gap", "runtime_s", "served_share", "n_unserved", "B_j", "C_j", "P_kw", "n_arcs", "n_binaries", "n_rows",
           "arc_build_s", "model_build_s", "mean_response_h", "max_response_h", "n_late", "mean_lateness_h",
           "max_lateness_h", "bike_km", "n_swaps", "kwh_purchased", "transfers_used", "swap_wait_slots",
           "stockout_slots", "stockout_queue_slots", "charger_util_mean", "desk_occupancy_mean",
           "idle_full_share_mean", "peak_kw_group", "end_full_total", "seed"]
    for c in num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("check_ok", "identity_24_ok", "mip_start_accepted"):
        if c in df.columns:
            df[c] = df[c].map(lambda v: True if v in (True, "True") else (False if v in (False, "False") else v))
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    wall = 0.0
    wp = os.path.join(out_dir, "wall_time.json")
    skipped: List[str] = []
    if os.path.exists(wp):
        for w in C.load_jsonl(wp):
            wall += float(w.get("wall_s", 0.0))
            skipped += list(w.get("skipped", []))
    seeds = sorted(df.seed.dropna().unique().astype(int).tolist())
    E4U.report(df[df.status != C.SKIPPED_BUDGET] if "status" in df.columns else df, out_dir, wall, time_limit,
               seeds, HEAT_SEEDS, skipped)
    md = os.path.join(out_dir, "RESULTS.md")
    src = df.groupby(["method", "source"]).size().reset_index(name="n") if "source" in df.columns else pd.DataFrame()
    with open(md, "r", encoding="utf-8") as fh:
        body = fh.read()
    head = ["# E4u round 3 -- provenance", "",
            f"Rows by method and source (round2 = reused ILP rows of outputs/e4u_sizing_usd, OPTIMAL or gap <= 1 %; "
            f"round3 = solved here, Threads {C.THREADS}, Seed 0, TimeLimit {time_limit:.0f} s; every baseline row is "
            f"recomputed in round 3):", "", C.markdown_table(src, list(src.columns), 0) if not src.empty else "-", ""]
    with open(md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(head) + "\n" + body)
    return md


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--wall-budget", type=float, default=WALL_BUDGET_S, help="seconds")
    ap.add_argument("--seeds-r2", nargs="*", type=int, default=SEEDS_R2)
    ap.add_argument("--seeds-new", nargs="*", type=int, default=SEEDS_NEW)
    ap.add_argument("--heat-seeds", nargs="*", type=int, default=HEAT_SEEDS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="seed 0 B3_C2_P4 baseline + ILP, Threads 1, TimeLimit 30")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    if args.time_limit > 300 and not args.smoke:
        raise SystemExit("round-3 rule: TimeLimit <= 300 s for E4u")
    out_dir = args.out_dir or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse:
        print(analyse(out_dir, args.time_limit))
        return {"analysed": out_dir}
    reused = round2_ilp_rows()
    if args.smoke:
        runner = Runner(out_dir, 30.0, 1, C.WallBudget(3600.0, margin_s=0.0, min_solve_s=1.0))
        runner.done = {}
        runner.run_fixed("smoke", 0, "B", BASE_B, BASE_C, BASE_P, None)
        print(f"# smoke done: {runner.n_runs} rows -> {runner.path}", flush=True)
        return {"smoke": runner.path, "rows": runner.n_runs}
    existing = {(int(r["seed"]), str(r["tag"]), str(r["method"])): r
                for r in C.load_jsonl(os.path.join(out_dir, RECORDS))} if os.path.isdir(out_dir) else {}
    done = dict(existing)
    for k, r in reused.items():
        done.setdefault(k, r)
    plan = build_plan(done, args.seeds_r2, args.seeds_new, args.heat_seeds)
    summary = plan_summary(plan, len(reused))
    summary.update(out_dir=out_dir, time_limit=args.time_limit, threads=args.threads,
                   wall_budget_min=args.wall_budget / 60.0, existing_round3_rows=len(existing))
    if args.dry_run:
        print("# plan (phase, seed, sweep, B, C, P):")
        for item in plan:
            print("  ", item)
        print(json.dumps(summary, indent=1))
        return summary
    budget = C.WallBudget(args.wall_budget)
    runner = Runner(out_dir, args.time_limit, args.threads, budget)
    n_seeded = runner.seed_reused(reused)
    print(f"# {n_seeded} round-2 ILP rows copied; plan {json.dumps(summary)}", flush=True)
    runner.run_plan(plan)
    wall = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall, "plan": summary, "skipped": runner.skipped,
                             "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"# round-3 E4u runs finished: {runner.n_runs} rows in {wall / 60:.1f} min; skipped {runner.skipped}", flush=True)
    try:
        print(analyse(out_dir, args.time_limit))
    except Exception as exc:  # noqa: BLE001
        print(f"# analyse failed: {exc}", flush=True)
    return summary


if __name__ == "__main__":
    main()
