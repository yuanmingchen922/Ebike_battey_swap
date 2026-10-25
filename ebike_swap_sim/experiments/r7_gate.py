"""R7 production gate (``notes/siting_production_plan.md`` section 5 item 10; review of
2026-10-21): the first production lane (``b0_gate``) checks that the server tree carries the
production code, i.e. every ``STALE CODE`` marker of the core lane, the drivers lane and the
fixer pass is in its file.  Flag-level drift fails loudly in argparse, but behaviour fixes
without a new flag would otherwise run silently on a stale tree.

Run from the package root (the lane wrapper does ``cd $PKG``)::

    python3 experiments/r7_gate.py            # exit 0 = every marker found, 2 = a marker missing

English only.  No solver, no instance build.
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)

#: (marker, file relative to the package root)
MARKERS: Tuple[Tuple[str, str], ...] = (
    # core lane (plan 5 items 1-4)
    ("def stage_rootlp", "experiments/r7_siting.py"),
    ("def stage_feas", "experiments/r7_siting.py"),
    ("class ScenarioLPSet", "ebike_swap_sim/benders.py"),
    ("def mark_terminal_infeasible", "ebike_swap_sim/benders.py"),
    ("def _escalate_batch", "ebike_swap_sim/benders.py"),
    ("def evict_template", "ebike_swap_sim/bilevel.py"),
    # drivers lane (plan 5 items 5-7)
    ("def comparison_filter", "experiments/r7_siting.py"),
    ("def m1_warm_layouts", "experiments/r7_siting.py"),
    ("class CostLog", "experiments/r7_cost.py"),
    ("def stage_pairs", "experiments/r7_search.py"),
    ("def stage_noradius", "experiments/r7_search.py"),
    ("def write_prod_lanes", "experiments/r7_search.py"),
    # fixer pass (reviews of 2026-10-21)
    ("escalate_batch_max", "ebike_swap_sim/benders.py"),
    ("def install_signal_handlers", "experiments/r7_cost.py"),
    ("def instance_md5", "experiments/r7_siting.py"),
    ("def instance_plan", "experiments/r7_siting.py"),
    ("def pair_next_layout", "experiments/r7_search.py"),
    # R7 re-plan after batch 2 (notes/siting_production_replan_m1.md changes 1-9, critic K2 / K3)
    ("def _restore_open", "ebike_swap_sim/benders.py"),                 # 1 restore of price_open
    ("lower_open", "ebike_swap_sim/benders.py"),                        # 1 / K2.7 labelled open-sites bounds
    ("M1_LP_ORDER", "experiments/r7_search.py"),                        # 2 price-list --tier, list rule
    ("--extend-below-ub", "experiments/r7_search.py"),                  # 2 M1-rest extension
    ("def stage_import_records", "experiments/r7_search.py"),           # 3 import-records
    ("def _warm_pick", "ebike_swap_sim/benders.py"),                    # 4 warm start from open_sites
    ("def ub_check_all_candidates", "ebike_swap_sim/benders.py"),       # 4 / M6
    ("def parse_cells", "ebike_swap_sim/benders.py"),                   # 5 cell filter (K3.1)
    ("strict_scenarios", "ebike_swap_sim/benders.py"),                  # 5 K3.1
    ("--m1-pass2", "experiments/r7_siting.py"),                         # 5 M4
    ("verify_checked_starts", "ebike_swap_sim/bilevel.py"),             # 6
    ("--verify-start", "experiments/r7_siting.py"),                     # 6
    ("--price-tier", "experiments/r7_siting.py"),                       # 7
    ("def all_candidates_lower", "experiments/r7_siting.py"),           # 7 (K2.7)
    ("def tier_kw", "experiments/r7_search.py"),                        # 7
    ("def m1_dual_statement", "experiments/r7_siting.py"),              # 8
    ("def stage_ub_check", "experiments/r7_search.py"),                 # 9 / M6
    ("def write_r2_lanes", "experiments/r7_search.py"),                 # 9
)


def check(root: str = PKG, markers: Sequence[Tuple[str, str]] = MARKERS) -> List[str]:
    """The markers not found (``'marker in file'``); empty when the tree is current."""
    miss = []
    for mark, rel in markers:
        path = os.path.join(root, rel)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                ok = mark in fh.read()
        except OSError:
            ok = False
        if not ok:
            miss.append(f"{mark!r} in {rel}")
    return miss


def main(argv: Optional[Sequence[str]] = None) -> int:
    """``r7_gate.py [ROOT] [--cost-dir DIR]``: ``--cost-dir`` (the re-plan lanes, "every lane writes
    cost rows") appends this invocation's start / end rows to ``DIR/cost.jsonl``
    (``experiments/r7_cost.py``; R7_BATCH / R7_INSTANCE / R7_USD_PER_H from the environment)."""
    args = list(argv) if argv is not None else sys.argv[1:]
    cost_dir = None
    if "--cost-dir" in args:
        i = args.index("--cost-dir")
        if i + 1 >= len(args):
            print("--cost-dir needs a directory", flush=True)
            return 64
        cost_dir = args[i + 1]
        del args[i:i + 2]
    root = args[:1] or [PKG]
    log = None
    if cost_dir:
        sys.path.insert(0, PKG)
        from experiments import r7_cost as RC
        log = RC.CostLog(os.path.abspath(cost_dir), "gate", "r7_gate.py", argv=list(argv) if argv is not None else sys.argv[1:])
    miss = check(root[0])
    if miss:
        for m in miss:
            print(f"STALE CODE: {m} missing; sync the current tree (deploy/aws/sync_up.sh) first", flush=True)
        if log is not None:
            log.finish("stale code")
        return 2
    print(f"gate ok: {len(MARKERS)} production markers found under {root[0]}", flush=True)
    if log is not None:
        log.finish("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
