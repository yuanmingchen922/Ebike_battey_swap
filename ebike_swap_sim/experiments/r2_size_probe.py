"""Round-2 size probe (DECISIONS R2.2: "the integrate step may reduce bikes/orders to
keep single ILP solves under ~5 min at Threads 3 and must report the sizes used").

For every (bikes, pruning, seed) combination the script builds the instance of the
requested family, the arc library, runs the baseline (default R2.3 rules) and solves
the E2 ILP ((5)-(22), (26)-(33), unchanged) with ``Threads = 3`` and the given time
limit, and appends one JSON record per run to ``outputs/r2_probe/<tag>.jsonl``
(arcs per kind, binaries, rows, build / model / solve times, status, objective,
bound, gap, baseline total, MIP-start acceptance).  ``--arcs-only`` sizes the
library without solving.  Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r2_size_probe.py --family usd4h --bikes 6 8 10 --seeds 0 1 \
        --pruning default reachable --time-limit 300 --tag usd4h
    python3 experiments/r2_size_probe.py --family usd8h --bikes 8 --seeds 0 1 --tag usd8h
    python3 experiments/r2_size_probe.py --family nyc4h --bikes 8 --seeds 0 1 --tag nyc4h
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments import common as C  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r2_probe")


def _jsonable(v: Any) -> Any:
    if isinstance(v, (bool, int, float, str)) or v is None:
        return v
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x) for x in v]
    return str(v)


def probe_one(family: str, n_bikes: int, seed: int, pruning: str, time_limit: float,
              threads: int, arcs_only: bool, inst_overrides: Dict[str, Any]) -> Dict[str, Any]:
    """One probe record (sizes, times, solver status) for ``family`` at ``n_bikes``
    bikes, ``seed`` and the pruning preset ``pruning`` (``'default'`` =
    :func:`experiments.common.pruning_for`, ``'reachable'`` = the same plus
    ``reachable_pruning = True``; R2.2 sizing)."""
    t0 = time.perf_counter()
    inst = C.make_instance(family, seed=seed, n_bikes=n_bikes, **inst_overrides)
    t_inst = time.perf_counter() - t0
    pr = C.pruning_for(inst, reachable=(pruning == "reachable"))
    lib, t_build = C.build_library(inst, pr)
    rec: Dict[str, Any] = {
        "family": family, "seed": seed, "pruning": pruning, "threads": threads,
        "time_limit": time_limit, "n_bikes": len(inst.bikes), "n_orders": len(inst.orders),
        "H": inst.H, "L": inst.L, "n_nodes": len(inst.nodes), "n_facilities": len(inst.facilities),
        "n_reposition_targets": len(pr.get("reposition_targets") or []),
        "instance_time_s": t_inst, "n_arcs": len(lib), "arc_counts": lib.counts(),
        "lib_build_time_s": t_build, "cost_variant": inst.meta.get("cost_variant"),
        "name": inst.meta.get("name"),
    }
    if arcs_only:
        return rec
    base = C.run_baseline_case(inst, lib)
    rec.update({
        "baseline_total": base["cost"]["total"], "baseline_families": base["families"],
        "baseline_unserved": base["flags"]["n_unserved"], "baseline_runtime_s": base["runtime"],
    })
    start = C.feasible_mip_start(inst, lib, base) if hasattr(C, "feasible_mip_start") else (base["schedule"], "default")
    sched_start, start_label = start
    ilp = C.run_ilp_case(inst, lib, mip_start=sched_start, time_limit=time_limit, threads=threads)
    rec.update({
        "mip_start_variant": start_label,
        "ilp_status": ilp["status"], "ilp_obj": ilp["obj"], "ilp_bound": ilp["bound"],
        "ilp_gap": ilp["gap"], "ilp_runtime_s": ilp["runtime"], "ilp_build_time_s": ilp["build_time"],
        "n_binaries": ilp["n_binaries"], "n_vars": ilp["n_vars"], "n_rows": ilp["n_rows"],
        "mip_start_accepted": ilp["mip_start_accepted"],
        "ilp_total": (ilp["cost"] or {}).get("total"), "ilp_ok": ilp["ok"],
        "ilp_unserved_n": (ilp["metrics"] or {}).get("n_unserved"),
        "total_time_s": time.perf_counter() - t0,
    })
    return rec


def main(argv: List[str] | None = None) -> List[Dict[str, Any]]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--family", default="usd4h")
    ap.add_argument("--bikes", nargs="+", type=int, default=[6, 8, 10])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1])
    ap.add_argument("--pruning", nargs="+", default=["default", "reachable"], choices=["default", "reachable"])
    ap.add_argument("--time-limit", type=float, default=300.0)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--arcs-only", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--override", nargs="*", default=[], help="key=json instance overrides")
    args = ap.parse_args(argv)
    overrides = {}
    for kv in args.override:
        k, v = kv.split("=", 1)
        overrides[k] = json.loads(v)
    C.ensure_dir(OUT_DIR)
    path = os.path.join(OUT_DIR, f"{args.tag or args.family}.jsonl")
    out = []
    for nb in args.bikes:
        for pruning in args.pruning:
            for seed in args.seeds:
                try:
                    rec = probe_one(args.family, nb, seed, pruning, args.time_limit, args.threads,
                                    args.arcs_only, overrides)
                except Exception as exc:  # record failures instead of aborting the sweep
                    rec = {"family": args.family, "seed": seed, "pruning": pruning, "n_bikes": nb,
                           "error": f"{type(exc).__name__}: {exc}"}
                rec["wall_clock"] = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(_jsonable(rec)) + "\n")
                print(json.dumps({k: rec.get(k) for k in ("family", "n_bikes", "n_orders", "H", "seed", "pruning",
                                                          "n_arcs", "lib_build_time_s", "n_binaries",
                                                          "ilp_build_time_s", "ilp_runtime_s", "ilp_status",
                                                          "ilp_obj", "ilp_gap", "baseline_total",
                                                          "mip_start_accepted", "error")}), flush=True)
                out.append(rec)
    return out


if __name__ == "__main__":
    main()
