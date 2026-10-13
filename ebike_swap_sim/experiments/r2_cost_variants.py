"""Round-2 cost-variant comparison (DECISIONS R2.1).

The same instance (same seed, geography, orders, bikes, facilities) is priced with
several ``cost_variant`` settings and solved with ``experiments.common.run_pair``
(baseline + E2 ILP, unchanged model).  The record of interest is the share of orders
the ILP leaves unserved under each variant: R2.1 argues that with ``usd_A`` (rider
labour priced per hour and per km) the unavoidable response cost of a typical order
exceeds ``P = 30``, so "drop every order" is optimal -- a degenerate objective, which
is why ``usd_sunk`` (labour sunk, E2 p.9) is the default.  ``toy`` is the round-1 unit
system for continuity.

Writes ``outputs/r2_costs/results.csv`` and ``RESULTS.md``.  Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/r2_cost_variants.py --family usd4h --seed 0 \
        --variants usd_sunk usd_A toy --time-limit 300
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

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r2_costs")


def run_variant(family: str, seed: int, variant: str, time_limit: float, threads: int,
                pruning: str = "default") -> Dict[str, Any]:
    """``run_pair`` on ``family`` / ``seed`` priced with ``cost_variant = variant``
    (R2.1); returns the flat record plus ``variant``, the coefficients used
    (``meta['costs']``) and the ILP / baseline unserved shares."""
    inst = C.make_instance(family, seed=seed, cost_variant=variant)
    pr = C.pruning_for(inst, reachable=(pruning == "reachable"))
    t0 = time.perf_counter()
    rec = C.run_pair(inst, pruning=pr, time_limit=time_limit, threads=threads)
    rec["wall_s"] = time.perf_counter() - t0
    rec["variant"] = variant
    rec["pruning"] = pruning
    co = inst.meta.get("costs") or {}
    for key in ("kappa", "pi", "P", "w", "v", "F", "bB", "bC", "window_scale"):
        rec[f"coef_{key}"] = co.get(key)
    n = len(inst.orders)
    rec["ilp_unserved_share"] = (None if rec.get("ilp_unserved_n") is None else rec["ilp_unserved_n"] / n)
    rec["baseline_unserved_share"] = rec["baseline_unserved"] / n
    # response cost of a typical order under this variant vs P (R2.1 argument)
    o = inst.orders[0]
    typical_h = (sum(x.a - x.r for x in inst.orders) / n + o.hp + o.hd + 2) * inst.disc.Delta_h
    rec["typical_response_h"] = typical_h
    rec["typical_response_cost"] = typical_h * o.w
    rec["P"] = o.P
    return rec


def main(argv: List[str] | None = None) -> List[Dict[str, Any]]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--family", default="usd4h")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--variants", nargs="+", default=["usd_sunk", "usd_A", "toy"])
    ap.add_argument("--time-limit", type=float, default=300.0)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--pruning", default="default", choices=["default", "reachable"])
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)
    C.ensure_dir(args.out_dir)
    recs = []
    for v in args.variants:
        rec = run_variant(args.family, args.seed, v, args.time_limit, args.threads, args.pruning)
        recs.append(rec)
        print(json.dumps({k: rec.get(k) for k in ("variant", "n_bikes", "n_orders", "ilp_status", "ilp_gap",
                                                  "ilp_runtime_s", "ilp_total", "baseline_total",
                                                  "ilp_unserved_n", "ilp_unserved_share",
                                                  "baseline_unserved", "mip_start_accepted",
                                                  "mip_start_variant")}), flush=True)
    df = C.write_csv(recs, os.path.join(args.out_dir, "results.csv"))
    cols = ["variant", "n_bikes", "n_orders", "H", "coef_kappa", "coef_pi", "coef_P", "coef_w", "coef_v",
            "coef_F", "coef_bB", "coef_bC", "typical_response_cost", "ilp_status", "ilp_gap", "ilp_runtime_s",
            "ilp_total", "ilp_C_travel", "ilp_C_elec", "ilp_unserved", "ilp_response", "ilp_lateness",
            "ilp_unserved_n", "ilp_unserved_share", "baseline_total", "baseline_unserved",
            "baseline_unserved_share", "gap_vs_baseline_pct", "mip_start_accepted", "mip_start_variant"]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    md = [f"# Round-2 cost variants on `{args.family}` seed {args.seed} (DECISIONS R2.1)", "",
          f"Same instance (bikes, orders, geography, facilities) priced with each `cost_variant`; "
          f"E2 ILP with Threads {args.threads}, TimeLimit {args.time_limit:.0f} s, pruning `{args.pruning}` "
          f"(`experiments.common.pruning_for`), baseline = round-2 rules (R2.3). `typical_response_cost` = "
          f"w x (mean prep + handling + ~10 min ride) per order, compared with P (`coef_P`): when it "
          f"exceeds P, serving an order costs more than dropping it and the objective degenerates.", "",
          C.markdown_table(df, cols, 3), "",
          "`ilp_unserved_share` = share of orders the ILP leaves unserved (u_i = 1); "
          "`baseline_unserved_share` = the same for the policy. `mip_start_variant` names the baseline "
          "schedule injected as the Gurobi start (`default` or a fallback variant when the default "
          "schedule violates (18)).", ""]
    with open(os.path.join(args.out_dir, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    return recs


if __name__ == "__main__":
    main()
