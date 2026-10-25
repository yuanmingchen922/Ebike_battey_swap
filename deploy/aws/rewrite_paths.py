#!/usr/bin/env python3
"""Rewrite absolute laptop paths stored inside the resumable outputs to the server's root.

The lower-level caches of the siting runs (``outputs/r6_o2/*/cache/index.jsonl``) and the RL
records (``model_path``) store absolute paths such as
``/Users/<name>/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/...``.  The code
tolerates a missing file (the cached schedule is then not used as a MIP start, the siting
``--source-dir`` copy falls back to ``cache/schedules/<basename>``), so nothing breaks without
this step -- but the warm starts are lost.  This script replaces the prefix before
``/ebike_swap_sim/outputs/`` with the current project root, in place, with a ``.bak`` copy.

    python3 deploy/aws/rewrite_paths.py --root ~/battery_swap            # dry run: counts only
    python3 deploy/aws/rewrite_paths.py --root ~/battery_swap --apply

Only ``index.jsonl`` and ``records.jsonl`` files under ``ebike_swap_sim/outputs/{r6_o2,r6_fill,
r6_penalty}`` are touched; the replacement is a literal string substitution of the detected
prefix, so JSON stays valid.  Idempotent: a second run finds nothing to change.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

SUBDIRS = ("r6_o2", "r6_fill", "r6_penalty")
NAMES = ("index.jsonl", "records.jsonl")
PREFIX_RE = re.compile(r'"((?:/[^"/]+)+?)/ebike_swap_sim/outputs/')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="project root (default: two levels above this script)")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: report only)")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    out_root = os.path.join(root, "ebike_swap_sim", "outputs")
    if not os.path.isdir(out_root):
        print(f"no outputs folder at {out_root}; nothing to do")
        return 0
    files = []
    for sub in SUBDIRS:
        for dirpath, _dirs, names in os.walk(os.path.join(out_root, sub)):
            files += [os.path.join(dirpath, n) for n in names if n in NAMES]
    n_files = n_lines = 0
    prefixes = set()
    for path in sorted(files):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        found = {m.group(1) for m in PREFIX_RE.finditer(text) if m.group(1) != root}
        if not found:
            continue
        new = text
        count = 0
        for old in found:
            count += new.count(old + "/ebike_swap_sim/outputs/")
            new = new.replace(old + "/ebike_swap_sim/outputs/", root + "/ebike_swap_sim/outputs/")
        prefixes |= found
        n_files += 1
        n_lines += count
        rel = os.path.relpath(path, root)
        if args.apply:
            shutil.copyfile(path, path + ".bak")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            print(f"rewrote {count:5d} paths in {rel}")
        else:
            print(f"would rewrite {count:5d} paths in {rel}")
    if n_files == 0:
        print(f"nothing to rewrite under {out_root} (all stored paths already start with {root})")
    else:
        verb = "rewrote" if args.apply else "would rewrite"
        print(f"{verb} {n_lines} paths in {n_files} files; old prefix(es): {', '.join(sorted(prefixes))}")
        if not args.apply:
            print("re-run with --apply to write (a .bak copy of each file is kept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
