"""Experiment E3u, round 3 -- transfers and separation under USD costs: fill the cells the
round-2 wall budget skipped and extend to seeds 0-4 (DECISIONS round-3 decision (3)).

Design is that of ``experiments/e3u_transfers_usd_fixed.py`` (its instance builder, record
layout, MIP-start candidates and report are imported, not copied): layouts ``colocated`` /
``separated_1hub`` / ``separated_2hubs`` x transfers ``free`` / ``none`` (``no_transfers``)
x end targets ``written`` (rho 0.5, R_end 1) / ``relaxed`` (rho 0, R_end 0), family
``usd4h`` (6 bikes / 36 orders / H 48, ``usd_sunk``), equal totals sum B = 9, sum C = 6.

Round-3 rules applied:

* reuse: the 17 round-2 ILP rows of ``outputs/e3u/results.csv`` solved to OPTIMAL are copied
  (``source = round2``); the 4 separated / written / transfers-free rows that stopped at
  TIME_LIMIT with a 2 % gap are re-solved here with ``TimeLimit 600 s`` (that cell type
  gets 600 s for every seed; all other cells 300 s); the 15 SKIPPED_BUDGET cells are solved;
* baselines: the policy rows (NONE and REORDER_POINT, both target settings) are recomputed
  with the fixed script's ``baseline_record`` (milliseconds; the current package reproduces
  the round-2 written rows exactly and, by fairness fix F1, the relaxed-copy rows are the
  same schedule -- ``outputs/e3u/RESULTS_final.md``), so every row of this directory comes
  from one code path; the recomputed totals are asserted against the stored written rows;
* order of work: seed 2 (all 12 ILP cells), the 3 missing (c) cells of seed 1, seeds 3-4
  (everything), then the 4 round-2 TIME_LIMIT cells at 600 s (incumbent improvement last,
  so that missing cells come first if the 4 h wall budget runs out);
* Gurobi ``OutputFlag 0``, ``Threads 3``, ``Seed 0``; wall budget 4 h (remaining solves
  are recorded as ``SKIPPED_BUDGET``); ``records.jsonl`` appended per run, ``results.csv``
  refreshed per run, one printed line per completed run; ``--analyse`` regenerates the
  figures and ``RESULTS.md`` with the fixed script's functions.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/e3u_round3.py --dry-run
    python3 experiments/e3u_round3.py --smoke        # colocated / written / seed 0 / transfers free, Threads 1, 30 s
    python3 experiments/e3u_round3.py
    python3 experiments/e3u_round3.py --analyse
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

from ebike_swap_sim import Instance, Schedule  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import e3u_transfers_usd_fixed as E3U  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e3u_round3")
ROUND2_CSV = os.path.join(C.OUTPUT_ROOT, "e3u", "results.csv")
RECORDS = "records.jsonl"
LAYOUTS = list(E3U.LAYOUTS)
TARGETS = list(E3U.TARGETS)
SWITCHES = ("free", "none")
SEEDS_R2 = [0, 1, 2]
SEEDS_NEW = [3, 4]
TIME_LIMIT = 300.0
TIME_LIMIT_LONG = 600.0
WALL_BUDGET_S = 4 * 3600.0

Key = Tuple[str, str, int, str, str]      # (layout, targets, seed, method, switch)
WorkItem = Tuple[str, str, str, int, str]  # (phase, layout, targets, seed, switch)


# ---------------------------------------------------------------------------
# keys / reuse
# ---------------------------------------------------------------------------
def ilp_key(layout: str, targets: str, seed: int, switch: str) -> Key:
    return (layout, targets, int(seed), "ilp", switch)


def baseline_key(layout: str, targets: str, seed: int, rule: str) -> Key:
    return (layout, targets, int(seed), "baseline", rule)


def key_of(row: Dict[str, Any]) -> Key:
    if row["method"] == "ilp":
        return ilp_key(row["layout"], row["targets"], int(row["seed"]), row["transfers"])
    rule = str(row.get("switch", "")).replace("transfer_rule=", "")
    return baseline_key(row["layout"], row["targets"], int(row["seed"]), rule)


def long_cell(layout: str, targets: str, switch: str) -> bool:
    """The separated / written / transfers-free cells hit the 300 s limit in round 2."""
    return layout != "colocated" and targets == "written" and switch == "free"


def time_limit_for(layout: str, targets: str, switch: str, tl: float = TIME_LIMIT,
                   tl_long: float = TIME_LIMIT_LONG) -> float:
    return tl_long if long_cell(layout, targets, switch) else tl


def round2_rows() -> Tuple[Dict[Key, Dict[str, Any]], Dict[Key, Dict[str, Any]]]:
    """``(reusable_ilp, written_baselines)`` from the round-2 ``results.csv``: ILP rows solved
    to OPTIMAL / gap <= 1 % (copied with ``source = round2``) and the stored WRITTEN
    baseline rows (used only to assert the recomputation)."""
    if not os.path.exists(ROUND2_CSV):
        return {}, {}
    df = pd.read_csv(ROUND2_CSV)
    ilp: Dict[Key, Dict[str, Any]] = {}
    base: Dict[Key, Dict[str, Any]] = {}
    for _, r in df.iterrows():
        row = {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.to_dict().items()}
        if row["method"] == "ilp":
            if C.reusable_ilp_row(row.get("status"), row.get("gap")):
                row["source"] = "round2"
                row["phase"] = "reuse"
                ilp[key_of(row)] = row
        elif row["targets"] == "written":
            base[key_of(row)] = row
    return ilp, base


def row_is_solved(row: Dict[str, Any]) -> bool:
    """Done = policy row, ILP row solved to OPTIMAL / gap <= 1 %, or an ILP row already
    attempted in round 3 with its full time limit (TIME_LIMIT, INFEASIBLE); only round-2
    TIME_LIMIT rows and SKIPPED_BUDGET rows are (re-)solved."""
    if row.get("method") == "baseline":
        return True
    if C.reusable_ilp_row(row.get("status"), row.get("gap")):
        return True
    return row.get("source") == "round3" and row.get("status") in ("TIME_LIMIT", "INFEASIBLE", "INF_OR_UNBD")


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------
def build_plan(done: Dict[Key, Dict[str, Any]], seeds_r2: Sequence[int] = SEEDS_R2,
               seeds_new: Sequence[int] = SEEDS_NEW) -> List[WorkItem]:
    """Ordered ILP work items: seed 2 (all), seed 1 missing, (seed 0 missing, if any),
    seeds 3-4 everything, then the round-2 TIME_LIMIT cells (not reusable) last."""
    def todo(layout: str, targets: str, seed: int, switch: str) -> bool:
        r = done.get(ilp_key(layout, targets, seed, switch))
        return r is None or not row_is_solved(r)

    def missing_not_timelimit(layout: str, targets: str, seed: int, switch: str) -> bool:
        r = done.get(ilp_key(layout, targets, seed, switch))
        return r is None or (not row_is_solved(r) and r.get("status") != "TIME_LIMIT")

    plan: List[WorkItem] = []
    fill_order = [s for s in sorted(seeds_r2, reverse=True)]       # seed 2, then 1, then 0
    for seed in fill_order:
        for layout in LAYOUTS:
            for targets in TARGETS:
                for switch in SWITCHES:
                    if missing_not_timelimit(layout, targets, seed, switch):
                        plan.append(("fill", layout, targets, seed, switch))
    for seed in seeds_new:
        for layout in LAYOUTS:
            for targets in TARGETS:
                for switch in SWITCHES:
                    if todo(layout, targets, seed, switch):
                        plan.append(("extend", layout, targets, seed, switch))
    for seed in sorted(seeds_r2):
        for layout in LAYOUTS:
            for targets in TARGETS:
                for switch in SWITCHES:
                    r = done.get(ilp_key(layout, targets, seed, switch))
                    if r is not None and not row_is_solved(r) and r.get("status") == "TIME_LIMIT":
                        plan.append(("resolve600", layout, targets, seed, switch))
    return plan


def plan_summary(plan: Sequence[WorkItem], reused: int) -> Dict[str, Any]:
    per_phase: Dict[str, int] = {}
    secs = 0.0
    for phase, layout, targets, _seed, switch in plan:
        per_phase[phase] = per_phase.get(phase, 0) + 1
        secs += time_limit_for(layout, targets, switch)
    return {"reused_round2_ilp_rows": reused, "ilp_items": len(plan), "per_phase": per_phase,
            "n_long_600s": sum(1 for _p, l, t, _s, sw in plan if long_cell(l, t, sw)),
            "expected_wall_min": round(0.45 * secs / 60.0, 1), "worst_wall_min": round(secs / 60.0, 1)}


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, out_dir: str, time_limit: float, time_limit_long: float, threads: int,
                 budget: C.WallBudget, hub_spares: int = E3U.HUB_SPARES, reachable: bool = True) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.path = os.path.join(out_dir, RECORDS)
        self.tl, self.tl_long, self.threads = float(time_limit), float(time_limit_long), int(threads)
        self.budget = budget
        self.hub_spares = hub_spares
        self.reachable = reachable
        self.done: Dict[Key, Dict[str, Any]] = {key_of(r): r for r in C.load_jsonl(self.path)}
        self.n_runs = 0
        self.stored_written_baselines: Dict[Key, Dict[str, Any]] = {}
        self.round2_prev: Dict[Key, Dict[str, Any]] = {}   # round-2 rows that are re-solved here
        self.baseline_mismatches: List[str] = []

    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("source", "round3")
        C.append_jsonl(self.path, row)
        self.done[key_of(row)] = row
        self.refresh_csv()
        self.n_runs += 1
        keys = ("layout", "targets", "seed", "method", "switch", "status", "total", "n_unserved", "transfers_used",
                "gap", "runtime_s", "time_limit_used_s", "mip_start_variant", "mip_start_accepted", "phase")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys}), flush=True)

    def refresh_csv(self) -> None:
        rows = sorted(self.done.values(), key=lambda r: (r["seed"], LAYOUTS.index(r["layout"]), r["targets"],
                                                         r["method"], str(r.get("switch"))))
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

    # -- instances ------------------------------------------------------------
    def instance(self, layout: str, targets: str, seed: int) -> Instance:
        inst = E3U.make_layout_instance(seed, layout, self.hub_spares)
        if targets == "relaxed":
            inst = E3U.relaxed_copy(inst)
        inst_dir = C.ensure_dir(os.path.join(self.out_dir, "instances"))
        p = os.path.join(inst_dir, f"{layout}_{targets}_seed{seed}.json")
        if not os.path.exists(p):
            inst.save(p)
        return inst

    def ensure_baselines(self, inst: Instance, lib: Any, build_time: float) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Optional[float]]]:
        """Both policy rows of this (layout, targets, seed) (recomputed if absent) and the
        schedules / totals the ILP rows need."""
        layout, targets, seed = inst.meta["layout"], inst.meta["end_targets"], int(inst.meta["seed"])
        bases: Dict[str, Dict[str, Any]] = {}
        totals: Dict[str, Optional[float]] = {}
        for variant, rule in E3U.BASELINE_RUNS:
            params = C.baseline_variant_params(variant, inst, transfer_rule=rule)
            base = C.run_baseline_case(inst, lib, params, label=f"{variant}:{rule}")
            bases[f"{variant}:{rule}"] = base
            totals["default" if rule == "NONE" else "reorder"] = base["cost"]["total"]
            k = baseline_key(layout, targets, seed, rule)
            if k not in self.done:
                row = E3U.baseline_record(inst, lib, build_time, variant, rule, base)
                row["phase"] = "baseline"
                stored = self.stored_written_baselines.get(baseline_key(layout, "written", seed, rule))
                if stored is not None and stored.get("total") is not None:
                    diff = abs(float(stored["total"]) - base["cost"]["total"])
                    row["round2_written_total"] = float(stored["total"])
                    row["matches_round2_written"] = diff <= 1e-6
                    if diff > 1e-6:
                        self.baseline_mismatches.append(f"{layout}/{targets}/seed{seed}/{rule}: {base['cost']['total']:.3f} vs {stored['total']}")
                self.emit(row)
        return bases, totals

    # -- one ILP cell ---------------------------------------------------------
    def run_cell(self, phase: str, layout: str, targets: str, seed: int, switch: str,
                 cache: Dict[Tuple[str, str, int], Tuple[Instance, Any, float, Dict[str, Any], Dict[str, Any]]]) -> None:
        ck = (layout, targets, seed)
        if ck not in cache:
            inst = self.instance(layout, targets, seed)
            pruning = C.pruning_for(inst, reachable=self.reachable)
            lib, build_time = C.build_library(inst, pruning)
            bases, totals = self.ensure_baselines(inst, lib, build_time)
            cache.clear()                      # one library in memory at a time
            cache[ck] = (inst, lib, build_time, bases, totals)
        inst, lib, build_time, bases, totals = cache[ck]
        no_transfers = switch == "none"
        tl_cell = time_limit_for(layout, targets, switch, self.tl, self.tl_long)
        tl = self.budget.solve_limit(tl_cell)
        if tl is None:
            row = E3U.skipped_record(inst, lib, build_time, no_transfers, f"wall budget exhausted after {self.budget.elapsed():.0f}s")
            row["phase"] = phase
            self.emit(row)
            return
        start, start_label = E3U.choose_mip_start(inst, lib, switch, bases)
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads, label="ilp",
                             no_transfers=no_transfers, params=C.ILP_PARAMS_R3)
        row = E3U.ilp_record(inst, lib, build_time, no_transfers, rec, start_label, tl, totals)
        row["phase"] = phase
        row["threads"] = self.threads
        prev = self.round2_prev.get(ilp_key(layout, targets, seed, switch))
        if prev is not None and prev.get("total") is not None:
            row["round2_total"] = prev.get("total")
            row["round2_status"] = prev.get("status")
            row["round2_gap"] = prev.get("gap")
        self.emit(row)


# ---------------------------------------------------------------------------
# analysis (fixed script's figures + report on the round-3 frame)
# ---------------------------------------------------------------------------
def analyse(out_dir: str, time_limit: float = TIME_LIMIT) -> str:
    rows = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not rows:
        raise SystemExit("no records yet")
    last: Dict[Key, Dict[str, Any]] = {}
    for r in rows:
        last[key_of(r)] = r
    df = C.records_to_frame(list(last.values()))
    for c in ("total", "gap", "runtime_s", "n_unserved", "served_share", "transfers_used", "batteries_moved",
              "stockout_slots_total", "m_t_max", "peak_kw_group_max", "end_full_total", "gap_vs_baseline_default_pct",
              "gap_vs_baseline_reorder_pct", "gap_vs_baseline_best_pct", "seed"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    seeds = sorted(df.seed.dropna().unique().astype(int).tolist())
    figures = E3U.make_figures(df, out_dir, seeds)
    anomalies = E3U.collect_anomalies(df)
    wall_path = os.path.join(out_dir, "wall_time.json")
    wall = 0.0
    if os.path.exists(wall_path):
        for w in C.load_jsonl(wall_path):
            wall += float(w.get("wall_s", 0.0))
    pruning = {"tau_max": 4, "start_slack": 6, "reachable": True}
    md = E3U.write_results_md(df, out_dir, seeds, E3U.HUB_SPARES, time_limit, figures, anomalies, wall, pruning)
    # round-3 provenance block prepended to the fixed script's report
    with open(md, "r", encoding="utf-8") as fh:
        body = fh.read()
    src = df.groupby(["method", "source"]).size().reset_index(name="n") if "source" in df.columns else pd.DataFrame()
    ilp = df[df.method == "ilp"]
    head = ["# E3u round 3 -- provenance", "",
            f"Rows by method and source (round2 = reused OPTIMAL rows of outputs/e3u; round3 = solved here with "
            f"Threads {C.THREADS}, Seed 0, TimeLimit {TIME_LIMIT:.0f} s / {TIME_LIMIT_LONG:.0f} s for separated-written-free cells):", "",
            C.markdown_table(src, list(src.columns), 0) if not src.empty else "-", "",
            f"ILP statuses: {ilp['status'].value_counts().to_dict() if not ilp.empty else {}}; seeds {seeds}.", ""]
    if "round2_total" in df.columns:
        cmp = ilp[ilp["round2_total"].notna()][["layout", "targets", "seed", "switch", "status", "total", "gap",
                                                  "round2_status", "round2_total", "round2_gap"]]
        if not cmp.empty:
            head += ["Re-solved round-2 TIME_LIMIT cells (600 s) against their round-2 incumbents:", "",
                     C.markdown_table(cmp, list(cmp.columns), 3), ""]
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
    ap.add_argument("--time-limit-long", type=float, default=TIME_LIMIT_LONG)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--wall-budget", type=float, default=WALL_BUDGET_S, help="seconds")
    ap.add_argument("--seeds-r2", nargs="*", type=int, default=SEEDS_R2)
    ap.add_argument("--seeds-new", nargs="*", type=int, default=SEEDS_NEW)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="colocated / written / seed 0 / transfers free, Threads 1, TimeLimit 30")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    out_dir = args.out_dir or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse:
        print(analyse(out_dir, args.time_limit))
        return {"analysed": out_dir}
    reused, stored_base = round2_rows()
    if args.smoke:
        runner = Runner(out_dir, 30.0, 30.0, 1, C.WallBudget(3600.0, margin_s=0.0, min_solve_s=1.0))
        runner.stored_written_baselines = stored_base
        runner.run_cell("smoke", "colocated", "written", 0, "free", {})
        print(f"# smoke done: {runner.n_runs} rows -> {runner.path}; baseline mismatches {runner.baseline_mismatches}", flush=True)
        return {"smoke": runner.path, "rows": runner.n_runs}
    existing = {key_of(r): r for r in C.load_jsonl(os.path.join(out_dir, RECORDS))} if os.path.isdir(out_dir) else {}
    done: Dict[Key, Dict[str, Any]] = dict(existing)
    # the round-2 frame also tells us which cells stopped at TIME_LIMIT (re-solve last)
    if os.path.exists(ROUND2_CSV):
        for _, r in pd.read_csv(ROUND2_CSV).iterrows():
            if r["method"] == "ilp" and ilp_key(r["layout"], r["targets"], int(r["seed"]), r["transfers"]) not in done:
                row = {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.to_dict().items()}
                done[key_of(row)] = row
    plan = build_plan(done, args.seeds_r2, args.seeds_new)
    summary = plan_summary(plan, len(reused))
    summary.update(out_dir=out_dir, threads=args.threads, wall_budget_min=args.wall_budget / 60.0,
                   existing_round3_rows=len(existing))
    if args.dry_run:
        print("# plan (phase, layout, targets, seed, switch):")
        for item in plan:
            print("  ", item, f"TL {time_limit_for(item[1], item[2], item[4], args.time_limit, args.time_limit_long):.0f}s")
        print(json.dumps(summary, indent=1))
        return summary
    budget = C.WallBudget(args.wall_budget)
    runner = Runner(out_dir, args.time_limit, args.time_limit_long, args.threads, budget)
    runner.stored_written_baselines = stored_base
    runner.round2_prev = {k: r for k, r in done.items() if k[3] == "ilp" and r.get("source") != "round3"
                          and r.get("status") == "TIME_LIMIT"}
    n_seeded = runner.seed_reused(reused)
    print(f"# {n_seeded} round-2 ILP rows copied; plan {json.dumps(summary)}", flush=True)
    cache: Dict[Any, Any] = {}
    for phase, layout, targets, seed, switch in plan:
        runner.run_cell(phase, layout, targets, seed, switch, cache)
    wall = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall, "plan": summary, "baseline_mismatches": runner.baseline_mismatches,
                             "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"# round-3 E3u runs finished: {runner.n_runs} rows in {wall / 60:.1f} min; baseline mismatches "
          f"{runner.baseline_mismatches}", flush=True)
    try:
        print(analyse(out_dir, args.time_limit))
    except Exception as exc:  # noqa: BLE001
        print(f"# analyse failed: {exc}", flush=True)
    return summary


if __name__ == "__main__":
    main()
