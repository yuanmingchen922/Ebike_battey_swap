"""O1 validation: the aggregated integer flow re-solves the round-3 optima.

For every round-3 E2u (usd4h, 30 instances) and E8 (nyc4h, 20 instances) instance whose
written-target or relaxed-target ILP was certified OPTIMAL with the per-bike model, the
same instance and arc library are rebuilt (same generator, pruning, MIP start, Gurobi
``Threads 3``, ``Seed 0``) and solved with ``ilp.build_model(aggregate=True)``.  The record
compares the optimal values and model sizes; per-bike sizes come from a build-only
per-bike model (no solve) and per-bike run times from the round-3 records.

Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python experiments/r5_o1_validation.py --family usd4h
    PYTHONPATH=. python experiments/r5_o1_validation.py --family nyc4h
    PYTHONPATH=. python experiments/r5_o1_validation.py --analyse
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from ebike_swap_sim import build_arcs, ilp  # noqa: E402
from experiments import common as C  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "outputs", "r5_o1_validation")
TIME_LIMIT = 600.0
THREADS = 3


def _records(path: str) -> Dict[Any, Dict[str, Any]]:
    out: Dict[Any, Dict[str, Any]] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["method"] in ("ilp", "ilp_relaxed") and r.get("status") == "OPTIMAL":
                out[(r["name"], r["method"])] = r
    return out


def _cases(family: str) -> List[Dict[str, Any]]:
    if family == "usd4h":
        from experiments import e2u_coord_usd as E2U
        recs = _records(os.path.join(os.path.dirname(HERE), "outputs", "e2u_round3", "records.jsonl"))
        cases = []
        for mult in (0.75, 1.0, 1.5):
            for seed in range(10):
                cases.append({"make": (lambda s=seed, m=mult: E2U.make_inst(s, m, "usd_sunk")),
                              "prune": {"reachable": True}, "recs": recs})
        return cases
    from experiments import e8_nyc_fixed as E8
    recs = _records(os.path.join(os.path.dirname(HERE), "outputs", "e8_round3", "records.jsonl"))
    cases = []
    for siting in ("busiest", "grid"):
        for seed in range(10):
            cases.append({"make": (lambda s=seed, g=siting: E8.make_instance(s, g)),
                          "prune": {"targets": "facilities"}, "recs": recs})
    return cases


def run(family: str) -> None:
    os.makedirs(OUT, exist_ok=True)
    out_path = os.path.join(OUT, f"records_{family}.jsonl")
    done = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            done = {(json.loads(l)["name"], json.loads(l)["method"]) for l in fh}
    for case in _cases(family):
        inst = case["make"]()
        if family == "nyc4h":
            inst.meta["pruning_targets"] = "facilities"
        name = inst.meta["name"]
        todo = [m for m in ("ilp", "ilp_relaxed") if (name, m) in case["recs"] and (name, m) not in done]
        if not todo:
            continue
        lib, t_lib = C.build_library(inst, C.pruning_for(inst, **case["prune"]))
        t0 = time.perf_counter()
        pb = ilp.build_model(inst, lib, threads=THREADS, time_limit=TIME_LIMIT, params=dict(C.ILP_PARAMS_R3))
        pb_size = pb._size_stats()
        pb_build = time.perf_counter() - t0
        del pb
        for method in todo:
            ref = case["recs"][(name, method)]
            ii, ll = inst, lib
            if method == "ilp_relaxed":
                ii = C.relax_end_targets(inst)
                ll = build_arcs(ii, **lib.options)
            base = C.run_baseline_case(ii, ll, None, "baseline")
            start, _label = C.feasible_mip_start(ii, ll, base)
            t1 = time.perf_counter()
            mdl = ilp.build_model(ii, ll, threads=THREADS, time_limit=TIME_LIMIT,
                                  params=dict(C.ILP_PARAMS_R3), aggregate=True)
            sched, st = mdl.solve(mip_start=start, verify_start=True)
            wall = time.perf_counter() - t1
            row = {
                "family": family, "name": name, "method": method, "status": st["status"],
                "obj_aggregated": st.get("obj"), "bound_aggregated": st.get("bound"), "gap": st.get("gap"),
                "obj_per_bike_r3": ref.get("total"), "runtime_aggregated_s": st["runtime"],
                "build_aggregated_s": st["build_time"], "wall_aggregated_s": wall,
                "runtime_per_bike_r3_s": ref.get("runtime_s"), "n_arcs": len(lib),
                "n_vars_aggregated": st.get("n_vars"), "n_rows_aggregated": st.get("n_rows"),
                "n_bin_aggregated": st.get("n_binaries"), "n_agg_arcs": st.get("n_agg_arcs"),
                "n_vars_per_bike": pb_size["n_vars"], "n_rows_per_bike": pb_size["n_rows"],
                "n_bin_per_bike": pb_size["n_binaries"], "build_per_bike_s": pb_build,
                "lib_build_s": t_lib, "check_ok": None if sched is None else True,
            }
            if row["obj_aggregated"] is not None and row["obj_per_bike_r3"] is not None:
                row["abs_diff"] = abs(row["obj_aggregated"] - row["obj_per_bike_r3"])
            with open(out_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"# {name} {method}: {row['status']} agg {row['obj_aggregated']:.4f} vs per-bike "
                  f"{row['obj_per_bike_r3']:.4f} ({row['runtime_aggregated_s']:.1f} s vs "
                  f"{row['runtime_per_bike_r3_s']:.1f} s)", flush=True)


def analyse() -> None:
    import pandas as pd
    rows = []
    for fam in ("usd4h", "nyc4h"):
        p = os.path.join(OUT, f"records_{fam}.jsonl")
        if os.path.exists(p):
            rows += [json.loads(l) for l in open(p, encoding="utf-8")]
    df = pd.DataFrame(rows)
    df["var_ratio"] = df["n_vars_per_bike"] / df["n_vars_aggregated"]
    df["row_ratio"] = df["n_rows_per_bike"] / df["n_rows_aggregated"]
    df["speedup"] = df["runtime_per_bike_r3_s"] / df["runtime_aggregated_s"]
    summary = df.groupby(["family", "method"]).agg(
        n=("name", "size"), optimal=("status", lambda s: int((s == "OPTIMAL").sum())),
        max_abs_diff=("abs_diff", "max"), vars_pb=("n_vars_per_bike", "mean"),
        vars_agg=("n_vars_aggregated", "mean"), var_ratio=("var_ratio", "mean"),
        rows_pb=("n_rows_per_bike", "mean"), rows_agg=("n_rows_aggregated", "mean"),
        t_pb=("runtime_per_bike_r3_s", "mean"), t_agg=("runtime_aggregated_s", "mean"),
        speedup_median=("speedup", "median")).reset_index()
    df.to_csv(os.path.join(OUT, "per_instance.csv"), index=False)
    summary.to_csv(os.path.join(OUT, "summary.csv"), index=False)
    print(summary.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=["usd4h", "nyc4h"])
    ap.add_argument("--analyse", action="store_true")
    a = ap.parse_args()
    if a.analyse:
        analyse()
    else:
        run(a.family)
