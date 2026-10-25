"""Experiment E7 / plan item M7 -- offline vs online value of the E2 plan (rolling horizon).

Question (SC-2 of ``notes/E2_formulation_review.md``; M7 of ``notes/reading_to_model.md``):
how much of the E2u coordination gap (offline ILP vs rule baseline) survives when the
ILP sees orders only ``lambda`` minutes before release, and how much of the value of
information is on the battery side (charging, transfers) vs the rider side (dispatch)?

Policies per instance (same instance, same arc options, same ``evaluate.cost`` (26)-(32)):

* ``offline``   -- the E2 ILP with every order known at ``t = 0`` (lower bound);
* ``rolling``   -- ``ebike_swap_sim.rolling.rolling_horizon`` at ``lambda in --lambdas``
                   (minutes; ``inf`` = full information inside the window), window ``--W``
                   slots, commit step ``--k`` slots, targets (9), (17), (18) only in
                   windows reaching ``H`` (``--final-targets`` written | m1 | relaxed);
* ``forecast``  -- the same with the M7 battery plan on ``--scenarios`` sampled futures
                   (``BootstrapForecast``, ``--pool all|released``), riders dispatched
                   to known orders only (``--forecast forecast|both``);
* ``baseline``  -- the R2.3 rule policy (``experiments.common.run_baseline_case``) with
                   ``--baseline``.

Reported per row: ``total`` (26), components, ``voi = rolling - offline``,
``share_surviving = (baseline - rolling) / (baseline - offline)`` (the share of the
coordination gap that survives without foresight), check outcome (hard families and
(24)), window statistics.  Rows are appended to ``<out>/records.jsonl`` (resumable by
``(family, seed, policy, lambda, W, k, final_targets)``); ``--analyse`` writes
``results.csv`` and ``RESULTS.md``.

Gurobi: ``Threads <= 3``, a ``TimeLimit`` per offline solve and per window.  The E2 model
is not changed.  Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/rolling_horizon.py --dry-run                     # plan + sizes only
    python3 experiments/rolling_horizon.py --family toy --seeds 0 --W 4 --k 2   # seconds
    python3 experiments/rolling_horizon.py --family usd4h --seeds 0-4 --baseline   # E7 (long)
    python3 experiments/rolling_horizon.py --analyse
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

from ebike_swap_sim import build_arcs  # noqa: E402
from ebike_swap_sim.rolling import (  # noqa: E402
    FINAL_TARGETS,
    BootstrapForecast,
    _supports_aggregate,
    rolling_horizon,
)
from experiments import common  # noqa: E402

DEFAULT_OUT = os.path.join(common.OUTPUT_ROOT, "rolling_horizon")
#: offline totals already recorded (``--reuse``), keyed like :func:`_key`
done_totals: Dict[Tuple, Any] = {}


def parse_seeds(text: str) -> List[int]:
    """``'0-4'`` -> ``[0, 1, 2, 3, 4]``; ``'0,3,7'`` -> ``[0, 3, 7]``."""
    out: List[int] = []
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def parse_lambdas(text: str) -> List[float]:
    """``'0,10,20,inf'`` -> ``[0.0, 10.0, 20.0, inf]`` (minutes)."""
    return [math.inf if p.strip().lower() in ("inf", "infinity", "none") else float(p)
            for p in str(text).split(",") if p.strip()]


def _key(rec: Dict[str, Any]) -> Tuple:
    lam = rec.get("lookahead_min")
    lam = "inf" if lam is None or (isinstance(lam, float) and math.isinf(lam)) else float(lam)
    return (rec.get("family"), rec.get("seed"), rec.get("policy"), lam, rec.get("W"),
            rec.get("k"), rec.get("final_targets"), rec.get("pool"))


def _row_from_cost(c: Dict[str, Any]) -> Dict[str, Any]:
    return common.flatten_cost(c)


def run_instance(family: str, seed: int, args: argparse.Namespace, done: set,
                 out_path: str) -> List[Dict[str, Any]]:
    """All policies on one instance; appends each finished row to ``out_path``."""
    from ebike_swap_sim import ilp

    inst = common.make_instance(family, seed=seed)
    pr = common.pruning_for(inst, reachable=True) if family not in ("toy", "p7") else {}
    t0 = time.perf_counter()
    lib = build_arcs(inst, strict=False, **pr)
    lib_time = time.perf_counter() - t0
    W = args.W if args.W else inst.H
    k = args.k if args.k else max(1, W // 3)
    base = {"family": family, "seed": seed, "H": inst.H, "n_orders": len(inst.orders),
            "n_bikes": len(inst.bikes), "n_arcs_day": len(lib), "lib_time": lib_time,
            "W": W, "k": k, "final_targets": args.final_targets, "pool": None,
            "demand_md5": common.demand_md5(inst)}
    rows: List[Dict[str, Any]] = []
    params = {**common.ILP_PARAMS_R3, "MIPGap": float(args.mip_gap)}

    def emit(rec: Dict[str, Any]) -> None:
        common.append_jsonl(out_path, rec)
        rows.append(rec)
        print(f"[{family} s{seed}] {rec['policy']:9s} lam={rec.get('lookahead_min')} "
              f"total={common.fmt(rec.get('total'))} status={rec.get('status')} "
              f"hard_ok={rec.get('hard_ok')}", flush=True)

    # ---------------------------------------------------------- baseline
    base_total = None
    start = None
    if args.baseline or not args.no_mip_start:
        b = common.run_baseline_case(inst, lib)
        base_total = b["cost"]["total"]
        start, start_variant = common.feasible_mip_start(inst, lib, b)
        rec = {**base, "policy": "baseline", "lookahead_min": None, "total": base_total,
               "status": "POLICY", "hard_ok": b["ok_modulo_report_only"],
               "families": b["families"], **_row_from_cost(b["cost"])}
        if args.baseline and _key(rec) not in done:
            emit(rec)
    # ----------------------------------------------------------- offline
    rec = {**base, "policy": "offline", "lookahead_min": None}
    off_total = None
    if _key(rec) in done and args.reuse:
        off_total = done_totals.get(_key(rec))
    else:
        t1 = time.perf_counter()
        # --aggregate also applies to the offline reference (O1, equivalent model): on
        # r5_stress8h the per-bike offline solve stops far from the optimum and would make the
        # value of information negative
        agg_kw = {"aggregate": True} if (args.aggregate and _supports_aggregate()) else {}
        sched, st = ilp.solve(inst, lib, mip_start=None if args.no_mip_start else start,
                              threads=args.threads, time_limit=args.time_limit_offline,
                              params=params, **agg_kw)
        rec["offline_aggregate"] = bool(agg_kw)
        off_total = (st.get("cost") or {}).get("total")
        rec.update(_row_from_cost(st.get("cost") or {}))
        rec.update(total=off_total, status=st.get("status"), gap=st.get("gap"),
                   bound=st.get("bound"), runtime=time.perf_counter() - t1,
                   hard_ok=sched is not None)
        emit(rec)
    # ----------------------------------------------------------- rolling
    variants: List[Tuple[float, bool]] = []
    if args.forecast in ("none", "both"):
        variants += [(lam, False) for lam in args.lambdas]
    if args.forecast in ("forecast", "both"):
        variants += [(lam, True) for lam in args.lambdas if not math.isinf(lam)]
    fc = BootstrapForecast(inst, pool=args.pool) if any(v[1] for v in variants) else None
    for lam, use_fc in variants:
        rec = {**base, "policy": "forecast" if use_fc else "rolling", "lookahead_min": lam,
               "pool": args.pool if use_fc else None}
        if _key(rec) in done:
            continue
        res = rolling_horizon(inst, W=W, k=k, lookahead_min=lam, lib=lib, arc_options=pr,
                              final_targets=args.final_targets,
                              forecast=fc if use_fc else None, n_scenarios=args.scenarios,
                              forecast_seed=seed, aggregate=args.aggregate,
                              threads=args.threads, time_limit=args.time_limit_window,
                              params=params)
        summ = res.summary()
        rec.update({key: v for key, v in summ.items() if not key.startswith("param_")})
        rec.update(status="ROLLING", n_scenarios=args.scenarios if use_fc else 0,
                   windows=[{kk: w.get(kk) for kk in ("t0", "W", "status", "gap", "runtime",
                                                      "n_known", "n_forecast", "n_busy",
                                                      "n_in_transit", "plan_fix", "fallback",
                                                      "aggregate")} for w in res.windows],
                   notes=res.notes)
        if off_total is not None:
            rec["voi"] = res.total - off_total
            rec["voi_pct"] = 100.0 * rec["voi"] / abs(off_total) if abs(off_total) > 1e-12 else None
        if base_total is not None and off_total is not None and abs(base_total - off_total) > 1e-9:
            rec["share_surviving"] = (base_total - res.total) / (base_total - off_total)
        emit(rec)
    return rows


def analyse(out_dir: str) -> str:
    """``results.csv`` and ``RESULTS.md`` (mean voi / share surviving by policy and lambda)."""
    recs = common.load_jsonl(os.path.join(out_dir, "records.jsonl"))
    if not recs:
        return "no records"
    df = common.write_csv(recs, os.path.join(out_dir, "results.csv"))
    lines = ["# E7 / M7 rolling horizon: offline vs online", "",
             "Rows: mean over seeds per (family, policy, lambda, W, k, final targets); "
             "`voi` = rolling - offline (USD), `share_surviving` = (baseline - rolling) / "
             "(baseline - offline).", ""]
    df = df.copy()
    df["lookahead_min"] = df["lookahead_min"].astype(str)
    cols = [c for c in ("total", "voi", "voi_pct", "share_surviving", "n_unserved") if c in df]
    grp = df.groupby(["family", "policy", "lookahead_min", "W", "k", "final_targets"],
                     dropna=False)[cols].mean().reset_index()
    grp["n"] = df.groupby(["family", "policy", "lookahead_min", "W", "k", "final_targets"],
                          dropna=False).size().values
    lines.append(common.markdown_table(grp))
    if "hard_ok" in df:
        bad = df[(df["policy"].isin(["rolling", "forecast"])) & (df["hard_ok"] != True)]  # noqa: E712
        lines += ["", f"Rolling rows failing a hard family or (24): {len(bad)}"]
    text = "\n".join(lines) + "\n"
    with open(os.path.join(out_dir, "RESULTS.md"), "w") as fh:
        fh.write(text)
    return text


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--family", default="usd4h")
    ap.add_argument("--seeds", default="0-4")
    ap.add_argument("--W", type=int, default=24, help="window length in slots (0 = H)")
    ap.add_argument("--k", type=int, default=6, help="commit step in slots (0 = W // 3)")
    ap.add_argument("--lambdas", type=parse_lambdas, default=parse_lambdas("0,10,20,inf"))
    ap.add_argument("--final-targets", choices=FINAL_TARGETS, default="written")
    ap.add_argument("--forecast", choices=("none", "forecast", "both"), default="none")
    ap.add_argument("--scenarios", type=int, default=2)
    ap.add_argument("--pool", choices=("all", "released"), default="all")
    ap.add_argument("--aggregate", action="store_true", help="O1 aggregated windows (feature-detected)")
    ap.add_argument("--baseline", action="store_true", help="also record the rule baseline")
    ap.add_argument("--no-mip-start", action="store_true", help="offline solve without a policy start")
    ap.add_argument("--threads", type=int, default=common.THREADS)
    ap.add_argument("--time-limit-offline", type=float, default=300.0)
    ap.add_argument("--time-limit-window", type=float, default=60.0)
    ap.add_argument("--mip-gap", type=float, default=1e-4)
    ap.add_argument("--reuse", action="store_true", help="skip the offline solve if recorded")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    args.threads = min(int(args.threads), 3)
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "records.jsonl")
    if args.analyse:
        print(analyse(args.out))
        return 0
    seeds = parse_seeds(args.seeds)
    if args.dry_run:
        for s in seeds:
            inst = common.make_instance(args.family, seed=s)
            W = args.W or inst.H
            k = args.k or max(1, W // 3)
            n_epochs = len(range(0, inst.H, k)) if k < inst.H else 1
            print(f"{args.family} seed {s}: H={inst.H} |K|={len(inst.bikes)} |I|={len(inst.orders)} "
                  f"W={W} k={k} epochs={n_epochs} lambdas={args.lambdas} "
                  f"forecast={args.forecast} final_targets={args.final_targets}")
        return 0
    done = set()
    for rec in common.load_jsonl(out_path) if os.path.exists(out_path) else []:
        done.add(_key(rec))
        if rec.get("policy") == "offline":
            done_totals[_key(rec)] = rec.get("total")
    for s in seeds:
        run_instance(args.family, s, args, done, out_path)
    print(analyse(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
