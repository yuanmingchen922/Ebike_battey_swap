"""Experiment E2 (smoke) -- baseline vs ILP on the three synthetic families.

For ``small`` (4 bikes / 12 orders / H 24 / L 8), ``medium`` (8 / 24 / 24 / 8) and
``large`` (10 / 30 / 24 / 12) of :data:`experiments.common.FAMILIES`, seed 0, with
the plan's pruning (reposition targets = restaurants + facilities + depots,
``tau_max = 4``, ``start_slack = 6``): build the arc library, run the baseline,
solve the ILP (E2 (5)-(22), (26)-(32); Threads 4, time limit 300 s) with the
baseline as MIP start, and assert

* the baseline passes ``evaluate.check`` except for the report-only families
  (9), (17), (18) (DECISIONS.md),
* the ILP schedule passes ``evaluate.check`` with zero violations,
* ILP cost <= baseline cost, and identity (24) holds for both.

Writes ``outputs/e2_smoke/results.csv`` and ``RESULTS.md`` with build time,
solve time, gap and binaries per family.  Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/e2_synthetic_smoke.py [--time-limit 300] [--families small medium large]
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments import common as C  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e2_smoke")


def main(families: List[str], seed: int = 0, time_limit: float = C.DEFAULT_TIME_LIMIT,
         out_dir: str = OUT_DIR) -> List[Dict[str, Any]]:
    """Run :func:`common.run_pair` on each family and write the result tables."""
    C.ensure_dir(out_dir)
    rows = []
    for fam in families:
        inst = C.make_instance(fam, seed=seed)
        rec = C.run_pair(inst, pruning=C.pruning_for(inst), time_limit=time_limit, threads=C.THREADS)
        C.assert_pair(rec)
        rows.append(rec)
        print(f"{fam:>7}: arcs {rec['n_arcs']:>9,} build {rec['build_time_s']:.2f}s | baseline {rec['baseline_total']:.2f} "
              f"({rec['baseline_runtime_s']:.2f}s, families {rec['baseline_families']}) | ILP {rec['ilp_status']} "
              f"obj {C.fmt(rec['ilp_obj'])} gap {C.fmt(rec['ilp_gap'], 4)} solve {rec['ilp_runtime_s']:.1f}s "
              f"model-build {rec['ilp_build_time_s']:.1f}s binaries {rec['ilp_binaries']:,} rows {rec['ilp_rows']:,} "
              f"start accepted {rec['mip_start_accepted']}")
    df = C.write_csv(rows, os.path.join(out_dir, "results.csv"))
    cols = ["family", "n_bikes", "n_orders", "H", "L", "n_arcs", "build_time_s", "ilp_build_time_s",
            "ilp_binaries", "ilp_rows", "ilp_status", "ilp_obj", "ilp_bound", "ilp_gap", "ilp_runtime_s",
            "baseline_total", "baseline_runtime_s", "baseline_families", "baseline_unserved", "ilp_unserved_n",
            "baseline_gap_pct", "mip_start_accepted", "mip_start_verified_status", "ilp_ok",
            "baseline_identity_24_ok", "ilp_identity_24_ok"]
    md = ["# E2 smoke -- synthetic families, baseline vs ILP", "",
          f"Seed {seed}; pruning {C.PRUNING_DEFAULTS} (reposition targets = restaurants + facilities + depots); "
          f"Gurobi Threads {C.THREADS}, TimeLimit {time_limit:.0f} s, OutputFlag 0.", "",
          C.markdown_table(df, cols, 4), "",
          "`baseline_gap_pct` = (baseline - ILP) / ILP in %; `baseline_families` are the constraint families "
          "the policy reports (only (9), (17), (18) are allowed, they are reported, not enforced); "
          "`mip_start_accepted` is the fix-and-solve certificate of the baseline start (False when the "
          "baseline violates (18), i.e. ends with fewer full spares than rho * sum B)."]
    with open(os.path.join(out_dir, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--families", nargs="+", default=["small", "medium", "large"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--time-limit", type=float, default=C.DEFAULT_TIME_LIMIT)
    args = ap.parse_args()
    main(args.families, args.seed, args.time_limit)
