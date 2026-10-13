"""Experiment E8, round 3 -- the semi-real NYC instance (DECISIONS R2.4) on seeds 0-9
(DECISIONS round-3 decision (3): extend the seeds; seeds 0-2 are reused).

Design is that of ``experiments/e8_nyc_fixed.py`` (imported: instance builder with the two
sitings ``busiest`` / ``grid``, the baseline row, the per-instance / siting tables, the
demand comparison, the figures and the report).  Methods ``baseline`` (R2.3 rules), ``ilp``
(written model, rho 0.5, R_end 1) and ``ilp_relaxed`` (rho 0, R_end 0), family ``nyc4h``
(6 bikes / 36 orders / H 48, ``usd_sunk``), pruning ``PRUNING_NYC`` (restricts the ILP only:
the ILP total is an upper bound on the written optimum and the gap a lower bound).

Round-3 rules: the 18 round-2 rows of ``outputs/e8_nyc_fixed/rows.jsonl`` (seeds 0-2, all
ILP solves OPTIMAL) are copied (``source = round2``); seeds 3-9 x both sitings x the three
methods are run here with Gurobi ``OutputFlag 0``, ``Threads 3``, ``TimeLimit 300 s``,
``Seed 0``; the demand side of a seed is asserted identical across the two sitings
(``demand_md5``); wall budget 2 h (remaining solves recorded as ``SKIPPED_BUDGET``);
``records.jsonl`` appended per run, ``results.csv`` refreshed per run, one printed line
per completed run; ``--analyse`` rebuilds ``per_instance.csv``, ``siting.csv``, the figures
and ``RESULTS.md`` on the union (the seed-0 map reuses the saved round-2 ILP schedule).

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/e8_round3.py --dry-run
    python3 experiments/e8_round3.py --smoke          # busiest seed 3, baseline + ilp, Threads 1, TimeLimit 30 s
    python3 experiments/e8_round3.py
    python3 experiments/e8_round3.py --analyse
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ebike_swap_sim import ArcLibrary, Instance, Schedule, build_arcs  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import e8_nyc_fixed as E8  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e8_round3")
ROUND2_DIR = os.path.join(C.OUTPUT_ROOT, "e8_nyc_fixed")
ROUND2_ROWS = os.path.join(ROUND2_DIR, "rows.jsonl")
RECORDS = "records.jsonl"
SEEDS_R2 = [0, 1, 2]
SEEDS_NEW = [3, 4, 5, 6, 7, 8, 9]
SITINGS = list(E8.SITINGS)
METHODS = list(E8.METHODS)
TIME_LIMIT = 300.0
WALL_BUDGET_S = 2 * 3600.0

Key = Tuple[str, int, str]          # (siting, seed, method)
WorkItem = Tuple[str, int, str]     # (siting, seed, method)


def key_of(row: Dict[str, Any]) -> Key:
    return (str(row["siting"]), int(row["seed"]), str(row["method"]))


def row_is_solved(row: Dict[str, Any]) -> bool:
    if row.get("method") == "baseline":
        return True
    if C.reusable_ilp_row(row.get("status"), row.get("gap")):
        return True
    return row.get("source") == "round3" and row.get("status") in ("TIME_LIMIT", "INFEASIBLE", "INF_OR_UNBD")


def round2_rows() -> Dict[Key, Dict[str, Any]]:
    out: Dict[Key, Dict[str, Any]] = {}
    for r in C.load_jsonl(ROUND2_ROWS):
        if int(r["seed"]) in SEEDS_R2 and row_is_solved(r):
            rr = dict(r)
            rr["source"] = "round2"
            out[key_of(rr)] = rr
    return out


def build_plan(done: Dict[Key, Dict[str, Any]], seeds: Sequence[int], sitings: Sequence[str] = SITINGS,
               methods: Sequence[str] = METHODS) -> List[WorkItem]:
    plan: List[WorkItem] = []
    for seed in seeds:
        for siting in sitings:
            for m in methods:
                r = done.get((siting, seed, m))
                if r is None or not row_is_solved(r):
                    plan.append((siting, seed, m))
    return plan


def plan_summary(plan: Sequence[WorkItem], reused: int) -> Dict[str, Any]:
    n_ilp = sum(1 for _s, _d, m in plan if m != "baseline")
    return {"reused_round2_rows": reused, "work_items": len(plan), "ilp_items": n_ilp,
            "instances": len({(s, d) for s, d, _m in plan}),
            "expected_wall_min_at_60s": round(n_ilp * 60 / 60.0, 1),
            "worst_wall_min_at_300s": round(n_ilp * 300 / 60.0, 1)}


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, out_dir: str, time_limit: float, threads: int, budget: C.WallBudget) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.inst_dir = C.ensure_dir(os.path.join(out_dir, "instances"))
        self.path = os.path.join(out_dir, RECORDS)
        self.time_limit, self.threads, self.budget = float(time_limit), int(threads), budget
        self.done: Dict[Key, Dict[str, Any]] = {key_of(r): r for r in C.load_jsonl(self.path)}
        self.demand_keys: Dict[int, Any] = {}
        self.n_runs = 0

    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("source", "round3")
        C.append_jsonl(self.path, row)
        self.done[key_of(row)] = row
        self.refresh_csv()
        self.n_runs += 1
        keys = ("name", "siting", "seed", "method", "status", "total", "n_unserved", "gap", "runtime_s",
                "n_arcs", "mip_start_variant", "mip_start_accepted")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys}), flush=True)

    def refresh_csv(self) -> None:
        rows = sorted(self.done.values(), key=lambda r: (int(r["seed"]), str(r["siting"]), METHODS.index(r["method"])
                                                         if r["method"] in METHODS else 9))
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

    def run_ilp(self, inst: Instance, lib: ArcLibrary, method: str, base: Dict[str, Any], tl: float
                ) -> Tuple[Dict[str, Any], Optional[Schedule]]:
        """E8's ``run_ilp`` with the round-3 Gurobi seed."""
        start, start_label = C.feasible_mip_start(inst, lib, base)
        t0 = time.perf_counter()
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads, label=method,
                             params=C.ILP_PARAMS_R3)
        wall = time.perf_counter() - t0
        row = E8._base_row(inst, lib, method)
        row.update({
            "status": rec["status"], "obj": rec["obj"], "bound": rec["bound"], "gap": rec["gap"],
            "runtime_s": rec["runtime"], "build_time_s": rec["build_time"], "wall_s": wall,
            "n_binaries": rec["n_binaries"], "n_vars": rec["n_vars"], "n_rows": rec["n_rows"],
            "node_count": (rec["stats"] or {}).get("node_count"),
            "mip_start_accepted": rec["mip_start_accepted"], "mip_start_variant": start_label,
            "mip_start_verified_status": (rec["mip_start_info"] or {}).get("verified_status"),
            "mip_start_obj": (rec["mip_start_info"] or {}).get("start_obj"),
            "time_limit_used_s": tl, "threads": self.threads,
        })
        if rec["schedule"] is None:
            row.update(total=None, check_ok=None)
            return row, None
        row.update(E8._metric_cols(inst, lib, rec["schedule"], rec["check"]))
        row.update(viol_9=0, viol_17=0, viol_18=0)
        return row, rec["schedule"]

    def run_instance(self, seed: int, siting: str, methods: Sequence[str]) -> None:
        t_all = time.perf_counter()
        inst = E8.make_instance(seed, siting)
        inst.meta["pruning_targets"] = "facilities"
        inst.save(os.path.join(self.inst_dir, f"{inst.meta['name']}.json"))
        key = C.demand_key(inst, include_bike_nodes=False)
        if seed in self.demand_keys and self.demand_keys[seed] != key:
            raise RuntimeError(f"siting {siting} changed the demand of seed {seed}")
        self.demand_keys.setdefault(seed, key)
        lib, build_t = C.build_library(inst, C.pruning_for(inst, targets="facilities"))
        r_base, base = E8.run_baseline(inst, lib)
        r_base["lib_build_time_s"] = build_t
        if "baseline" in methods:
            self.emit(r_base)
        if "ilp" in methods:
            tl = self.budget.solve_limit(self.time_limit)
            if tl is None:
                row = E8._base_row(inst, lib, "ilp")
                row.update(status=C.SKIPPED_BUDGET, total=None, skip_reason="wall budget exhausted")
                self.emit(row)
            else:
                r_ilp, s_ilp = self.run_ilp(inst, lib, "ilp", base, tl)
                r_ilp["lib_build_time_s"] = build_t
                self.emit(r_ilp)
                if s_ilp is not None:
                    with open(os.path.join(self.inst_dir, f"{inst.meta['name']}-ilp-schedule.json"), "w", encoding="utf-8") as fh:
                        json.dump(s_ilp.to_dict(), fh)
        if "ilp_relaxed" in methods:
            tl = self.budget.solve_limit(self.time_limit)
            if tl is None:
                row = E8._base_row(inst, lib, "ilp_relaxed")
                row.update(status=C.SKIPPED_BUDGET, total=None, skip_reason="wall budget exhausted")
                self.emit(row)
            else:
                relaxed = C.relax_end_targets(inst)
                relaxed.meta["name"] = inst.meta["name"] + "-relaxed"
                lib_rel = build_arcs(relaxed, **lib.options)
                assert len(lib_rel) == len(lib), "rho / R_end do not enter the arc rules"
                r_b0, base0 = E8.run_baseline(relaxed, lib_rel, "baseline_relaxed_copy")
                r_rel, _s_rel = self.run_ilp(relaxed, lib_rel, "ilp_relaxed", base0, tl)
                r_rel["lib_build_time_s"] = build_t
                r_rel["name"] = inst.meta["name"]
                r_rel["baseline_relaxed_copy_total"] = r_b0["total"]
                r_rel["baseline_relaxed_copy_differs"] = abs(r_b0["total"] - r_base["total"]) > 1e-9
                r_rel["baseline_relaxed_copy_reserve_source"] = r_b0.get("policy_reserve_source")
                self.emit(r_rel)
        print(f"# {inst.meta['name']} methods {list(methods)} done in {time.perf_counter() - t_all:.0f} s "
              f"(budget left {self.budget.remaining() / 60:.0f} min)", flush=True)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def analyse(out_dir: str, time_limit: float = TIME_LIMIT) -> str:
    rows = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not rows:
        raise SystemExit("no records yet")
    last: Dict[Key, Dict[str, Any]] = {}
    for r in rows:
        last[key_of(r)] = r
    df = C.records_to_frame(list(last.values()))
    for c in ("total", "gap", "runtime_s", "n_unserved", "n_served", "served_share", "bike_km", "n_swaps", "seed",
              "viol_17", "viol_18", "n_arcs", "n_binaries", "n_rows", "build_time_s", "node_count",
              "mean_response_h", "max_response_h", "mean_lateness_h", "n_late", "queue_wait_slots",
              "kwh_purchased", "peak_kw_sites", "transfers_used", "end_full_total") + tuple(E8.COMPONENTS):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df.status != C.SKIPPED_BUDGET] if "status" in df.columns else df
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    seeds = sorted(df.seed.dropna().unique().astype(int).tolist())
    per = E8.per_instance_table(df)
    per.to_csv(os.path.join(out_dir, "per_instance.csv"), index=False)
    sit = E8.siting_table(per) if {"busiest", "grid"} <= set(df.siting) else pd.DataFrame()
    sit.to_csv(os.path.join(out_dir, "siting.csv"), index=False)
    insts: Dict[Tuple[str, int], Instance] = {}
    for seed in seeds:
        for siting in SITINGS:
            if ((df.seed == seed) & (df.siting == siting)).any():
                insts[(siting, seed)] = E8.make_instance(seed, siting)
    nyc_insts = [insts[("busiest", s)] for s in seeds if ("busiest", s) in insts] or list(insts.values())
    cmp = E8.demand_comparison(nyc_insts, seeds)
    with open(os.path.join(out_dir, "demand_comparison.json"), "w", encoding="utf-8") as fh:
        json.dump(cmp, fh, indent=1, default=str)
    figures: List[str] = []
    s0 = seeds[0]
    if ("busiest", s0) in insts:
        inst0 = insts[("busiest", s0)]
        sched = None
        for d in (os.path.join(out_dir, "instances"), os.path.join(ROUND2_DIR, "instances")):
            p = os.path.join(d, f"{inst0.meta['name']}-ilp-schedule.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as fh:
                    sched = Schedule.from_dict(json.load(fh))
                break
        lib0, _ = C.build_library(inst0, C.pruning_for(inst0, targets="facilities"))
        try:
            figures.append(E8.plot_map(inst0, lib0, sched, insts.get(("grid", s0)), os.path.join(out_dir, f"map_seed{s0}.png")))
        except Exception as exc:  # noqa: BLE001
            print(f"# map failed: {exc}", flush=True)
    figures.append(E8.plot_cost_components(df, os.path.join(out_dir, "cost_components.png")))
    figures.append(E8.plot_gap_by_seed(per, os.path.join(out_dir, "gap_by_seed.png")))
    figures.append(E8.plot_demand_comparison(cmp, os.path.join(out_dir, "demand_comparison.png")))
    wall = 0.0
    wp = os.path.join(out_dir, "wall_time.json")
    if os.path.exists(wp):
        for w in C.load_jsonl(wp):
            wall += float(w.get("wall_s", 0.0))
    md = E8.write_results_md(df, per, sit, cmp, insts, out_dir, wall, time_limit, figures)
    src = df.groupby(["method", "source"]).size().reset_index(name="n") if "source" in df.columns else pd.DataFrame()
    with open(md, "r", encoding="utf-8") as fh:
        body = fh.read()
    head = ["# E8 round 3 -- provenance", "",
            f"Rows by method and source (round2 = reused rows of outputs/e8_nyc_fixed, seeds 0-2; round3 = seeds 3-9 "
            f"solved here, Threads {C.THREADS}, Seed 0, TimeLimit {time_limit:.0f} s):", "",
            C.markdown_table(src, list(src.columns), 0) if not src.empty else "-", ""]
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
    ap.add_argument("--seeds", nargs="*", type=int, default=SEEDS_NEW)
    ap.add_argument("--sitings", nargs="+", default=SITINGS, choices=SITINGS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="busiest seed 3 baseline + ilp, Threads 1, TimeLimit 30")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    if args.time_limit > 300 and not args.smoke:
        raise SystemExit("round-3 rule: TimeLimit <= 300 s for E8")
    out_dir = args.out_dir or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse:
        print(analyse(out_dir, args.time_limit))
        return {"analysed": out_dir}
    reused = round2_rows()
    if args.smoke:
        runner = Runner(out_dir, 30.0, 1, C.WallBudget(3600.0, margin_s=0.0, min_solve_s=1.0))
        runner.run_instance(args.seeds[0] if args.seeds else 3, "busiest", ["baseline", "ilp"])
        print(f"# smoke done: {runner.n_runs} rows -> {runner.path}", flush=True)
        return {"smoke": runner.path, "rows": runner.n_runs}
    existing = {key_of(r): r for r in C.load_jsonl(os.path.join(out_dir, RECORDS))} if os.path.isdir(out_dir) else {}
    done = dict(existing)
    for k, r in reused.items():
        done.setdefault(k, r)
    plan = build_plan(done, args.seeds, args.sitings)
    summary = plan_summary(plan, len(reused))
    summary.update(out_dir=out_dir, time_limit=args.time_limit, threads=args.threads,
                   wall_budget_min=args.wall_budget / 60.0, existing_round3_rows=len(existing))
    if args.dry_run:
        print("# plan (siting, seed, method):")
        for item in plan:
            print("  ", item)
        print(json.dumps(summary, indent=1))
        return summary
    budget = C.WallBudget(args.wall_budget)
    runner = Runner(out_dir, args.time_limit, args.threads, budget)
    n_seeded = runner.seed_reused(reused)
    print(f"# {n_seeded} round-2 rows copied; plan {json.dumps(summary)}", flush=True)
    groups: Dict[Tuple[int, str], List[str]] = {}
    order: List[Tuple[int, str]] = []
    for siting, seed, m in plan:
        if (seed, siting) not in groups:
            groups[(seed, siting)] = []
            order.append((seed, siting))
        groups[(seed, siting)].append(m)
    for seed, siting in order:
        runner.run_instance(seed, siting, groups[(seed, siting)])
    wall = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall, "plan": summary, "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
                             "demand_md5": {str(s): C.demand_md5(E8.make_instance(s, "busiest"), include_bike_nodes=False)
                                            for s in sorted(runner.demand_keys)}}) + "\n")
    print(f"# round-3 E8 runs finished: {runner.n_runs} rows in {wall / 60:.1f} min", flush=True)
    try:
        print(analyse(out_dir, args.time_limit))
    except Exception as exc:  # noqa: BLE001
        print(f"# analyse failed: {exc}", flush=True)
    return summary


if __name__ == "__main__":
    main()
