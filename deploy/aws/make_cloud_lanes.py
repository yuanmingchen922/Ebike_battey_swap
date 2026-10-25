#!/usr/bin/env python3
"""Write the lanes file for run_lanes.sh: the remaining round-6 work, one stage per lane.

Run it ON the machine whose ``outputs/`` the lanes will use (the instance, after sync_up.sh),
from anywhere::

    . ~/battery_swap/env.sh
    python3 deploy/aws/make_cloud_lanes.py                 # -> outputs/cloud_lanes/lanes.txt
    python3 deploy/aws/make_cloud_lanes.py --vcpu 32 --o2 auto --include-finished

It reads the records that exist and writes one lane per remaining stage:

* the ``r6_fill --retry-unsolved`` re-solves of the ``r6_penalty`` stages headline / psweep /
  vsweep / fleet / levers (a lane is written only when the records still contain rows that
  the retry selection of ``experiments/r6_fill.py`` picks);
* the new ``r6_fill`` stages transfers / stress / rolling_ext / pack / levers_ext / compliance /
  rl_seeds (a stage with a ``RESULTS.md`` is treated as finished and listed as a comment unless
  ``--include-finished``; every stage resumes from its ``records.jsonl``, so re-running a finished
  stage costs only its analysis);
* the O2 siting second pass (``--o2 auto``: step 2 of ``outputs/r6_fill_lanes/orchestrate.sh``,
  Benders at budgets m = 2-4 on ``manhattan_pass2`` with the bound-from-cuts report and the
  analysis chained after it) when ``manhattan_pass2`` has no certified written results at
  m = 2, 3, 4; ``--o2 force`` / ``--o2 none`` override;
* compliance points at the O2 pass that holds a written m = 2 ``budget_result`` (pass 2 first,
  then pass 1) through ``--o2-records`` / ``--o2-cache``; when an O2 lane is in the file,
  compliance waits for it (``after``); without any O2 result it runs on the round-5 layout only
  (``--layout-key``);
* a final ``r6_analyse_all`` lane (``r6_fill.ANALYSE_ALL``) after every r6 lane, so the joined
  tables are consistent;
* commented placeholders for the planned O3 / O4 / O5 runs (``notes/reading_to_model.md``),
  whose scripts do not exist yet.

Lanes file format (TAB-separated; ``#`` comments)::

    name <TAB> threads <TAB> after <TAB> command

Threads: 3 per r6 lane (the R6 protocol caps Gurobi at Threads 3), 11 for the O2 pass (3 LP
workers x 3 threads + a 2-thread master), 1 for the analysis.  With ``--vcpu 32`` the summary
shows how the dispatcher of run_lanes.sh fills the machine.  EC2 vCPUs are hyperthreads (two per
physical core), so the dispatcher's default budget is 1.5 threads per core, capped at vcpu - 1:
24 on 32 vCPUs = eight r6 lanes at once, or four beside the O2 lane (``--max-threads`` here and
in run_lanes.sh to change; 31 uses every hyperthread = ten lanes, slower each).  A companion
``lanes.json`` carries the expected minutes (``r6_fill.EST_MIN`` and the retry plan, measured on
the laptop with 3 threads on physical cores) and the decisions taken.

The O2 lane chains step 2, the bound report and the analysis with ";" so the report always runs,
but exits with the status of step 2; run_lanes.sh treats a non-zero exit as *failed*, so the
compliance lane (``after`` the O2 lane) waits until step 2 has been re-run successfully.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PKG = os.path.normpath(os.path.join(HERE, "..", "..", "ebike_swap_sim"))

R6_THREADS = 3
O2_THREADS = 11      # --lp-workers 3 x --lp-threads 3 + --master-threads 2
ANALYSE_THREADS = 1
#: Step 2 of the O2 second pass (outputs/r6_fill_lanes/orchestrate.sh), then the bound report and
#: the tables; ";" so the report and the analysis run even when step 2 stops at its wall budget,
#: and "exit $rc" so the lane's exit code (and the run_lanes.sh state) is that of step 2.
O2_STEP2 = ("python3 experiments/r6_o2_siting.py --manhattan --source-dir outputs/r6_o2/manhattan "
            "--out-dir outputs/r6_o2/manhattan_pass2 --resume-open --budgets 2 3 4 --skip-enumeration "
            "--gate report --lp-method barrier --lp-workers 3 --lp-threads 3 --threads 3 --master-threads 2 "
            "--wall-relaxed {wr:g} --wall-written {ww:g} --reserve-min 30")
O2_BOUND = ("python3 experiments/r6_o2_siting.py --manhattan --bound-from-cuts --no-cover "
            "--source-dir outputs/r6_o2/manhattan_pass2 --out-dir outputs/r6_o2/manhattan_pass2_bound "
            "--master-threads 1 --threads 1 --lp-threads 1 --lp-workers 1")
O2_ANALYSE = "python3 experiments/r6_o2_siting.py --manhattan --analyse --out-dir outputs/r6_o2/manhattan_pass2"
O2_PASSES = ("manhattan_pass2", "manhattan")
#: Planned runs without scripts yet (notes/reading_to_model.md items O3-O5; plan step 6).
PLACEHOLDERS = [
    ("o3_surrogate_labels", 9, "-", "O3(a) Neur2SP training set: cached OPTIMAL ILP rows + 1,500-3,000 random layouts x 3 seeds "
                                    "(about 11-22 h on 3 processes); script experiments/r7_o3_surrogate.py --stage labels (not written)"),
    ("o3_surrogate_fit", 3, "o3_surrogate_labels", "O3(b-d) fit the per-seed NN-P surrogate, surrogate screen, surrogate MIP, E9.1 acceptance "
                                                   "(L02:SC:B2:C1 at 676.22); experiments/r7_o3_surrogate.py --stage fit,evaluate (not written)"),
    ("o4_aggregate_shortlist", 3, "-", "O4 static aggregate surrogate for city-wide candidates, validated against the Midtown ranking; "
                                       "experiments/r7_o4_aggregate.py (not written)"),
    ("o5_policy_aware_siting", 3, "o3_surrogate_fit", "O5 policy-aware / robust siting on baseline-policy labels; "
                                                      "experiments/r7_o5_robust.py (not written)"),
]


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def o2_state(pkg: str, budgets=(2.0, 3.0, 4.0)) -> Dict[str, Any]:
    """Which O2 pass has a written m = 2 result, and whether pass 2 is certified at m = 2-4."""
    import experiments.r6_o2_siting as O2  # noqa: WPS433
    unit = float(O2.BUDGET_UNIT)
    out: Dict[str, Any] = {"written_m2": None, "pass2_certified": False, "pass2_rows": 0}
    for name in O2_PASSES:
        rec = os.path.join(pkg, "outputs", "r6_o2", name, "records.jsonl")
        rows = [r for r in load_jsonl(rec) if r.get("kind") == "budget_result"]
        if name == "manhattan_pass2":
            out["pass2_rows"] = len(rows)
            cert = {(r.get("target"), round(float(r.get("budget") or 0) / unit, 3)): bool(r.get("certified"))
                    for r in rows}
            # the last row per (target, m) wins
            out["pass2_certified"] = all(cert.get(("written", float(m)), False) for m in budgets)
            out["pass2_certified_detail"] = {f"{t}@m{m:g}": v for (t, m), v in sorted(cert.items(), key=str)}
        has_m2 = [r for r in rows if r.get("target") == "written" and r.get("best_layout")
                  and abs(float(r.get("budget") or 0) / unit - 2.0) < 1e-6]
        if has_m2 and out["written_m2"] is None:
            last = has_m2[-1]
            out["written_m2"] = {"pass": name, "best_layout": last.get("best_layout"),
                                 "certified": bool(last.get("certified")), "records": rec,
                                 "cache": os.path.join(pkg, "outputs", "r6_o2", name, "cache")}
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pkg", default=DEFAULT_PKG, help=f"ebike_swap_sim package root (default {DEFAULT_PKG})")
    ap.add_argument("--out", default=None, help="lanes file (default <pkg>/outputs/cloud_lanes/lanes.txt)")
    ap.add_argument("--vcpu", type=int, default=32, help="vCPU count of the target instance (for the summary)")
    ap.add_argument("--max-threads", type=int, default=None,
                    help="dispatcher thread budget for the summary (default: 1.5 x physical cores = 0.75 x vcpu, "
                         "capped at vcpu - 1, as in run_lanes.sh)")
    ap.add_argument("--o2", choices=["auto", "force", "none"], default="auto",
                    help="O2 second-pass lane: auto (when manhattan_pass2 lacks certified written m=2-4), force, none")
    ap.add_argument("--o2-wall", type=float, nargs=2, default=(4.0, 4.0), metavar=("RELAXED_H", "WRITTEN_H"),
                    help="wall hours of the O2 step-2 targets (default 4 4, as in orchestrate.sh)")
    ap.add_argument("--include-finished", action="store_true", help="also write lanes for stages that have a RESULTS.md")
    ap.add_argument("--skip", default="", help="comma-separated lane names to leave out (written as comments)")
    ap.add_argument("--no-analyse-lane", action="store_true", help="omit the final r6_analyse_all lane")
    args = ap.parse_args(argv)

    pkg = os.path.abspath(args.pkg)
    if not os.path.isdir(os.path.join(pkg, "experiments")):
        print(f"package not found at {pkg} (pass --pkg)", file=sys.stderr)
        return 2
    sys.path.insert(0, pkg)
    os.chdir(pkg)
    try:
        import experiments.r6_fill as F  # noqa: WPS433
        import experiments.r6_penalty as R6  # noqa: WPS433
    except Exception as exc:  # noqa: BLE001
        print(f"cannot import the experiments ({type(exc).__name__}: {exc}); activate the venv first (. env.sh)",
              file=sys.stderr)
        return 2

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    rel = lambda p: os.path.relpath(p, pkg)  # noqa: E731
    lanes: List[Dict[str, Any]] = []     # active lanes
    notes: List[str] = []                # comment lines explaining what was left out
    decisions: Dict[str, Any] = {}

    def add(name: str, threads: int, after: str, cmd: str, minutes: float, why: str = "") -> None:
        if name in skip:
            notes.append(f"# skipped by --skip: {name}: {cmd}")
            return
        lanes.append({"name": name, "threads": threads, "after": after, "command": cmd,
                      "expected_wall_min": round(minutes), "why": why})

    # ---------------------------------------------------------------- O2 second pass
    o2 = o2_state(pkg)
    decisions["o2"] = o2
    o2_lane = None
    want_o2 = args.o2 == "force" or (args.o2 == "auto" and not o2["pass2_certified"])
    if want_o2:
        wr, ww = args.o2_wall
        cmd = "; ".join([O2_STEP2.format(wr=wr, ww=ww), "rc=$?", O2_BOUND, O2_ANALYSE, "exit $rc"])
        add("o2_pass2_step2", O2_THREADS, "-", cmd, (wr + ww) * 60 + 20,
            "manhattan_pass2 written target not certified at m = 2-4" if args.o2 == "auto" else "--o2 force")
        o2_lane = "o2_pass2_step2" if "o2_pass2_step2" not in skip else None
    else:
        notes.append("# O2 second pass: " + ("disabled by --o2 none" if args.o2 == "none"
                                              else "manhattan_pass2 already certified at written m = 2, 3, 4"))

    # ---------------------------------------------------------------- retries
    r6_lanes: List[str] = []
    for stage in F.RETRY_STAGES:
        rec = os.path.join(R6.stage_dir(stage, False, None), F.RECORDS)
        tl = F.RETRY_TL[stage]
        if not os.path.exists(rec):
            notes.append(f"# retry {stage}: no records at {rel(rec)} (stage never ran here); nothing to retry")
            continue
        try:
            sel = F.select_grid_retries(rec) if stage in R6.GRID_STAGES else F.stress_retry_selection(rec, tl)[0]
        except Exception as exc:  # noqa: BLE001
            notes.append(f"# retry {stage}: selection failed ({type(exc).__name__}: {exc}); lane written anyway")
            sel = None
        n = len(sel) if sel is not None else {"headline": 3, "psweep": 23, "vsweep": 2, "fleet": 20, "levers": 11}[stage]
        if n == 0:
            notes.append(f"# retry {stage}: every ILP row is OPTIMAL or already retried at {tl:g} s; no lane")
            continue
        minutes = n * (tl * (0.85 if stage in ("psweep", "fleet") else 1.0) + 90.0) / 60.0
        name = f"r6_retry_{stage}"
        add(name, R6_THREADS, "-", f"python3 experiments/r6_fill.py --retry-unsolved --stage {stage}", minutes,
            f"{n} rows to re-solve at {tl:g} s")
        r6_lanes.append(name)
        decisions[name] = {"n_retries": n, "time_limit_s": tl}

    # ---------------------------------------------------------------- new stages
    def compliance_args():
        """(after, extra CLI, why) for the compliance stage: which O2 pass / layout it uses."""
        if o2_lane:
            return (o2_lane,
                    " --o2-records outputs/r6_o2/manhattan_pass2/records.jsonl --o2-cache outputs/r6_o2/manhattan_pass2/cache",
                    "waits for the O2 pass-2 lane (rc=0), then uses its written m = 2 layout from manhattan_pass2")
        if o2["written_m2"]:
            w = o2["written_m2"]
            return ("-", f" --o2-records {rel(w['records'])} --o2-cache {rel(w['cache'])}",
                    f"O2 layout {w['best_layout']} from {w['pass']} ({'certified' if w['certified'] else 'NOT certified'})")
        return ("-", f" --layout-key '{F.R5_LAYOUT}'", "no O2 written m = 2 result anywhere: round-5 layout only")

    c_after, c_extra, c_why = compliance_args()
    decisions["compliance"] = {"after": c_after, "extra_args": c_extra.strip(), "why": c_why}
    compliance_note = f"# compliance uses: {c_why}"
    for stage in F.NEW_STAGES:
        out_dir = F.stage_dir(stage, False)
        finished = os.path.exists(os.path.join(out_dir, "RESULTS.md"))
        name = f"r6_{stage}"
        if finished and not args.include_finished:
            notes.append(f"# {name}: {rel(out_dir)}/RESULTS.md exists (finished); --include-finished re-runs it (resume = analysis only)")
            if stage == "compliance":
                compliance_note += " [RESULTS.md exists; not re-run]"
            continue
        cmd = f"python3 experiments/r6_fill.py --stage {stage}"
        after = "-"
        why = "resumable from records.jsonl"
        if stage == "compliance":
            after, why = c_after, c_why
            cmd += c_extra
        add(name, R6_THREADS, after, cmd, F.EST_MIN[stage], why)
        if name not in skip:
            r6_lanes.append(name)

    # ---------------------------------------------------------------- final analysis
    if r6_lanes and not args.no_analyse_lane:
        add("r6_analyse_all", ANALYSE_THREADS, ",".join(r6_lanes), F.ANALYSE_ALL, 3,
            "joined tables after every r6 lane (rolling / retries / new stages)")

    # ---------------------------------------------------------------- write
    out = args.out or os.path.join(pkg, "outputs", "cloud_lanes", "lanes.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cores = max(1, args.vcpu // 2)
    all_ht = max(1, args.vcpu - 1)
    usable = args.max_threads if args.max_threads else max(1, min(all_ht, cores * 3 // 2))
    total_threads = sum(l["threads"] for l in lanes)
    lines = [
        "# Cloud lanes for run_lanes.sh -- written by deploy/aws/make_cloud_lanes.py",
        f"# package: {pkg}",
        f"# target: {args.vcpu} vCPU = {cores} physical cores -> dispatcher budget {usable} threads: "
        f"{usable // R6_THREADS} r6 lanes at Threads 3 at once"
        + (f", or {max(0, usable - O2_THREADS) // R6_THREADS} beside the {O2_THREADS}-thread O2 lane" if o2_lane else "")
        + f"; run_lanes.sh start --max-threads {all_ht} uses every hyperthread ({all_ht // R6_THREADS} lanes, slower each)",
        f"# lanes: {len(lanes)}, threads if all ran at once: {total_threads}",
        "# format: name <TAB> threads <TAB> after (- or lane,lane) <TAB> command (bash, from the package root)",
        "#",
        f"# O2 manhattan_pass2: {o2['pass2_rows']} budget_result rows; written target certified at m = 2, 3, 4: "
        f"{'yes' if o2['pass2_certified'] else 'no'}"
        + (f"; detail {o2.get('pass2_certified_detail')}" if o2.get("pass2_certified_detail") else ""),
        compliance_note,
    ]
    lines += notes
    lines.append("#")
    for l in lanes:
        lines.append(f"# {l['name']}: about {l['expected_wall_min']} min; {l['why']}")
        lines.append("\t".join([l["name"], str(l["threads"]), l["after"], l["command"]]))
    lines += ["#", "# Planned O3-O5 runs (notes/reading_to_model.md): placeholders, scripts not written yet.",
              "# Remove the leading '# ' once the script exists."]
    for name, threads, after, desc in PLACEHOLDERS:
        lines.append(f"# {desc}")
        lines.append("# " + "\t".join([name, str(threads), after, f"echo 'not implemented: {name}'; exit 1"]))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    meta = {"lanes": lanes, "notes": notes, "decisions": decisions, "vcpu": args.vcpu, "physical_cores": cores,
            "usable_threads": usable, "all_hyperthreads": all_ht,
            "total_threads": total_threads, "placeholders": [p[0] for p in PLACEHOLDERS],
            "expected_wall_min_sum": sum(l["expected_wall_min"] for l in lanes)}
    with open(os.path.splitext(out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, default=str)

    # ---------------------------------------------------------------- summary
    print(f"wrote {out} ({len(lanes)} lanes, {total_threads} threads if all ran at once)")
    print(f"{'lane':28s} {'thr':>3s} {'min':>5s}  after / note")
    for l in lanes:
        print(f"{l['name']:28s} {l['threads']:3d} {l['expected_wall_min']:5d}  {l['after']}  -- {l['why']}")
    for n in notes:
        print(n)
    # crude wave plan: greedy packing by the dispatcher order, ignoring "after"
    free, wave, waves = usable, [], []
    for l in lanes:
        if l["after"] != "-":
            continue
        if l["threads"] > free:
            waves.append(wave); wave, free = [], usable
        wave.append(l["name"]); free -= l["threads"]
    if wave:
        waves.append(wave)
    print(f"with the default budget of {usable} threads ({cores} cores x 1.5) the dispatcher starts: "
          + " | then ".join(", ".join(w) for w in waves))
    print(compliance_note.lstrip("# "))
    print(f"sum of expected lane minutes: {meta['expected_wall_min_sum']} (lanes run in parallel; the longest lane bounds the wall time)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
