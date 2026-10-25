"""R7 server probe (``notes/siting_scaleup_design.md`` sections 1.4, 3.1 and 5.1): the measurements
that must exist before the first production lane of ``r7_siting.py``.  Driven by
``deploy/aws/r7_probe.sh`` on the instance (never on the laptop, except ``synth`` and ``summary``,
which solve nothing).

Subcommands (all write JSON into ``--out``, default ``outputs/r7_siting_probe``):

``repro``    validation 5.1 step 1 through the r7 code path: ``--family r5_manhattan --menu full
             --scenarios 0 --seeds 0 1 2`` must reproduce every cache key of
             ``outputs/r6_o2/manhattan_pass2/cache/index.jsonl``, the demand hashes, the template
             arc counts (5,835,874 / 5,923,013 / 6,133,784) and price the three radius layouts as
             cache hits; the bounds (1,052.995 / 675.740 / 1,115.251 / 676.240) are read from the
             ``--bound-from-cuts`` output of ``r6_o2_siting.py`` (run by the driver).
``radius``   validation 5.1 step 3: the three layouts x three scenarios re-priced with
             ``--approach-radius 14`` at ``max(300 s, cached time limit)``, warm-started from the
             cached schedule, compared with the cached values without the radius through the
             Gurobi bounds (verdict 'keep 14' / 'inconclusive (gap)' / 'raise'); template arc
             counts with and without the radius; the laptop-to-server factors (one-site ScenarioLP
             barrier times, two pass-2 ILPs re-solved with ``force=True``, template build times).
``price``    one exact pricing ILP (300 s, ``force=True``) of the M09 lattice location
             (``SC:B3:C2``) on one 40-order weekday scenario of a ``manhattan_dot`` setup
             directory, with the template / library / solve times separated.
``synth``    synthetic DOT CSV (clearly labelled) on restaurant-dense nodes, used only when
             ``data/raw/dot_candidate_sites.csv`` is absent.
``summary``  ``probe_summary.json``: every number of the probe in one file (also on the laptop).

English only.  No E2 equation changes; nothing here alters a model.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import glob
import json
import os
import shlex
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebike_swap_sim import bilevel as BL  # noqa: E402
from experiments import common as C  # noqa: E402

PASS2 = os.path.join(C.OUTPUT_ROOT, "r6_o2", "manhattan_pass2")
OUT_DEFAULT = os.path.join(C.OUTPUT_ROOT, "r7_siting_probe")
EXPECTED_ARCS = [5_835_874, 5_923_013, 6_133_784]
EXPECTED_BOUNDS = {("relaxed", 1): 1052.995, ("relaxed", 2): 675.740, ("relaxed", 3): 675.740, ("relaxed", 4): 675.740,
                   ("written", 1): 1115.251, ("written", 2): 676.240, ("written", 3): 676.240, ("written", 4): 676.240}
EXPECTED_UB = {("relaxed", 1): 1052.995, ("relaxed", 2): 700.113, ("written", 1): 1131.800, ("written", 2): 699.957}
#: validation 5.1 step 3: (layout, target) -- the relaxed m = 1 optimum, the written m = 2 incumbent
#: (only priced under written targets in pass 2) and the relaxed m = 2 incumbent
RADIUS_LAYOUTS = [("M09:SC:B3:C2", "relaxed"), ("M04:SC:B2:C2|M09:SC:B4:C2", "written"),
                  ("M08:SC:B3:C2|M09:SC:B3:C2", "relaxed")]
#: laptop-to-server factor (design 1.4 / 3.1 / 7.2 item 9): pass-2 laptop rows of this layout,
#: relaxed targets, OPTIMAL in 152.2 s (s1) / 171.7 s (s2) at 3 threads, 300 s, MIP start 'default'
FACTOR_LAYOUT = "M09:SC:B3:C2"
FACTOR_SCENARIOS = (1, 2)
LAPTOP_LP_S = (13.0, 17.0)          # one-site r5 ScenarioLP, cold barrier + crossover, 3 threads (laptop)
LAPTOP_TEMPLATE_S = (10.0, 12.0)    # pass-2 template builds (laptop)
R5_ARGS = ["--family", "r5_manhattan", "--menu", "full", "--scenarios", "0", "--seeds", "0", "1", "2", "--stage", "setup",
           "--dry-run"]


def _rss_gb() -> float:
    import resource
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return ru / (1024.0 ** 3) if sys.platform == "darwin" else ru / (1024.0 ** 2)


def _dump(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(C.jsonable(obj), fh, indent=1)
    print(f"# wrote {path}", flush=True)


def _ctx(extra: List[str]):
    from experiments import r7_siting as R
    args = R.parse_args(extra)
    return R.Ctx(R.Run(args))


def _row_brief(r: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("layout_key", "scenario", "seed", "policy", "relaxed_targets", "status", "total", "opex", "gap", "bound",
            "runtime_s", "build_time_s", "time_limit", "n_arcs", "n_binaries", "n_rows", "node_count",
            "mip_start_variant", "gurobi_status", "cache_hit", "error")
    return {k: r.get(k) for k in keys if k in r}


# ---------------------------------------------------------------------------
def cmd_repro(a: argparse.Namespace) -> Dict[str, Any]:
    out = os.path.join(a.out, "repro")
    cache = os.path.join(out, "cache")
    if not os.path.exists(os.path.join(cache, "index.jsonl")):
        raise SystemExit(f"copy {PASS2}/cache into {cache} first (the driver does)")
    t0 = time.perf_counter()
    ctx = _ctx(R5_ARGS + ["--out-dir", out, "--threads", str(a.threads), "--max-threads", str(a.max_threads),
                          "--lp-workers", "1", "--lp-threads", "1", "--price-workers", str(a.workers)])
    rows = C.load_jsonl(os.path.join(PASS2, "cache", "index.jsonl"))
    miss = []
    for r in rows:
        ev = ctx.ev if r.get("relaxed_targets", True) else ctx.ev_written
        if ev.cache_key(BL.Layout.from_key(r["layout_key"]), int(r["scenario"]), r["policy"]) != r["key"]:
            miss.append([r["layout_key"], r["scenario"], r["policy"], r.get("relaxed_targets")])
    md5_cache = [m for _s, m in sorted({(int(x["scenario"]), x["demand_md5"]) for x in rows})]
    res: Dict[str, Any] = {"n_index_rows": len(rows), "n_key_mismatch": len(miss), "key_mismatch_first": miss[:10],
                           "demand_md5_equal": ctx.ev.demand_md5 == md5_cache, "demand_md5": ctx.ev.demand_md5,
                           "pruning_signature": ctx.ev.pruning_signature(0), "config_md5": ctx.config_md5()}
    arcs = []
    for s in range(ctx.ev.n_scenarios):
        t1 = time.perf_counter()
        _inst, lib = ctx.ev.template(s)
        arcs.append({"scenario": s, "n_arcs": len(lib), "build_s": time.perf_counter() - t1})
    res["template_arcs"] = arcs
    res["template_arcs_equal"] = [x["n_arcs"] for x in arcs] == EXPECTED_ARCS
    hits = []
    for key, target in RADIUS_LAYOUTS:
        ev = ctx.ev if target == "relaxed" else ctx.ev_written
        for s in range(ctx.ev.n_scenarios):
            r = ev.evaluate_scenario(BL.Layout.from_key(key), s, time_limit=300.0)
            hits.append({**_row_brief(r), "target": target})
    res["cached_prices"] = hits
    res["all_cache_hits"] = all(h.get("cache_hit") for h in hits)
    res["n_new_solves"] = ctx.ev.n_solves + ctx.ev_written.n_solves
    bpath = os.path.join(a.out, "repro_bound", "bound_from_cuts.jsonl")
    bounds = []
    if os.path.exists(bpath):
        for r in C.load_jsonl(bpath):
            m = int(round(float(r["budget"]) / 52150.0))
            exp_lb = EXPECTED_BOUNDS.get((r["target"], m))
            exp_ub = EXPECTED_UB.get((r["target"], m))
            bounds.append({"target": r["target"], "m": m, "LB": r.get("LB"), "LB_kind": r.get("LB_kind"),
                           "UB": r.get("UB"), "UB_layout": r.get("UB_layout"), "expected_LB": exp_lb, "expected_UB": exp_ub,
                           "LB_ok": exp_lb is not None and r.get("LB") is not None and abs(float(r["LB"]) - exp_lb) <= 5e-4,
                           "UB_ok": exp_ub is None or (r.get("UB") is not None and abs(float(r["UB"]) - exp_ub) <= 5e-4)})
    res["bounds"] = bounds
    res["bounds_ok"] = bool(bounds) and all(b["LB_ok"] and b["UB_ok"] for b in bounds)
    res["ok"] = bool(res["n_key_mismatch"] == 0 and res["demand_md5_equal"] and res["template_arcs_equal"]
                     and res["all_cache_hits"] and res["bounds_ok"])
    res["wall_s"] = time.perf_counter() - t0
    res["rss_gb_peak"] = _rss_gb()
    _dump(os.path.join(a.out, "repro.json"), res)
    return res


# ---------------------------------------------------------------------------
def _warm_of(ev: Any, row: Dict[str, Any], cache_dir: str) -> Any:
    """Portable schedule of a cached row: its ``schedule_path`` when it resolves, else
    ``<cache_dir>/schedules/<basename>`` (the pass-2 rows carry laptop paths); ``(None, None)``
    when neither exists."""
    w = ev.load_portable(row)
    if w is not None:
        return w, "schedule_path"
    path = row.get("schedule_path")
    if path:
        alt = os.path.join(cache_dir, "schedules", os.path.basename(str(path)))
        if os.path.exists(alt):
            with open(alt, "r", encoding="utf-8") as fh:
                return json.load(fh), "cache_basename"
    return None, None


def _radius_option_keys(ctx0: Any, ctx1: Any) -> Dict[str, Any]:
    """Arc-builder options that the approach radius adds, read through ``sites_nyc.
    siting_pruning`` (option names are not hard-coded: they may change in the library)."""
    from ebike_swap_sim import sites_nyc as S
    p0 = S.siting_pruning(ctx0.ev.scenarios[0], **ctx0.ev.pruning_overrides)
    p1 = S.siting_pruning(ctx1.ev.scenarios[0], **ctx1.ev.pruning_overrides)
    out: Dict[str, Any] = {}
    for k in sorted(set(p1) - set(p0)):
        v = p1[k]
        out[k] = {"n_entries": len(v)} if hasattr(v, "__len__") and not isinstance(v, str) else v
        if isinstance(v, (list, tuple, set)) and len(v) <= 64:
            out[k]["entries"] = sorted(str(x) for x in v)
    return out


def _lp_factor(ctx0: Any, a: argparse.Namespace) -> Dict[str, Any]:
    """Cold barrier + crossover of the one-site r5 ScenarioLP at ``x_of_layout(M09:SC:B3:C2)``,
    s = 0..2, ``a.threads`` threads each, 3 LPs at once (the laptop protocol: lp_workers 3 x 3
    threads, 13-17 s), then one solo re-solve of s = 0 (``LPWarmStart 0``: again cold)."""
    from ebike_swap_sim import benders as BD
    lay = BL.Layout.from_key(FACTOR_LAYOUT)
    x = ctx0.enc.x_of_layout(lay)
    n = ctx0.ev.n_scenarios
    t0 = time.perf_counter()
    lps = [BD.ScenarioLP(ctx0.ev, s, threads=int(a.threads), method="barrier", relaxed=True) for s in range(n)]
    build_s = time.perf_counter() - t0
    lpw = max(1, min(n, int(a.max_threads) // int(a.threads), 3))
    try:
        with cf.ThreadPoolExecutor(max_workers=lpw) as pool:
            rs = list(pool.map(lambda lp: lp.solve(x), lps))
        solo = lps[0].solve(x)
    finally:
        for lp in lps:
            lp.dispose()
    rows = [{"scenario": s, "status": r.status, "runtime_s": r.runtime_s, "Qt": r.Qt, "Qs": r.Qs,
             "artificial": getattr(r, "artificial", None), "iterations": getattr(r, "iterations", None),
             "method": r.method} for s, r in enumerate(rs)]
    conc = [r["runtime_s"] for r in rows if r["status"] == "OPTIMAL"]
    mean = sum(conc) / len(conc) if conc else None
    lo, hi = LAPTOP_LP_S
    return {"layout_key": FACTOR_LAYOUT, "threads": int(a.threads), "lp_workers": lpw, "build_s": build_s,
            "sizes": [lp.size for lp in lps], "concurrent": rows, "solo_s0": {"status": solo.status, "runtime_s": solo.runtime_s},
            "laptop_s": [lo, hi], "mean_runtime_s": mean,
            "factor_lp": None if mean is None else mean / (0.5 * (lo + hi)),
            "factor_lp_range": None if mean is None else [mean / hi, mean / lo],
            "factor_lp_solo": solo.runtime_s / (0.5 * (lo + hi)) if solo.status == "OPTIMAL" else None}


def cmd_radius(a: argparse.Namespace) -> Dict[str, Any]:
    """Validation 5.1 step 3 at equal solver effort (probe review 2026-10-21), plus the
    laptop-to-server factor: (i) template arc counts and build times with / without the radius
    (``factor_python``); (ii) the one-site ScenarioLP barrier timings (``factor_lp``); (iii) the
    pass-2 laptop rows M09:SC:B3:C2 relaxed s1 / s2 re-solved with ``force=True`` at 300 s on an
    isolated evaluator (the repro cache keeps the laptop rows), ``factor_ilp`` = server / laptop
    runtime; (iv) the 3 layouts x 3 scenarios with the radius at ``max(300, cached time limit)``,
    warm-started from the cached schedule, compared through Gurobi bounds."""
    t0 = time.perf_counter()
    base_dir = os.path.join(a.out, "repro")           # pass-2 cache copy: values without the radius
    rad_dir = os.path.join(a.out, "radius")
    common = ["--threads", str(a.threads), "--max-threads", str(a.max_threads), "--lp-workers", "1", "--lp-threads", "1",
              "--price-workers", str(a.workers), "--time-limit", "300"]
    ctx0 = _ctx(R5_ARGS + ["--out-dir", base_dir] + common)
    ctx1 = _ctx(R5_ARGS + ["--out-dir", rad_dir, "--approach-radius", str(a.radius)] + common)
    base_cache = ctx0.run.cache
    res: Dict[str, Any] = {"radius_blocks": a.radius, "pruning_with": ctx1.ev.pruning_signature(0),
                           "pruning_without": ctx0.ev.pruning_signature(0),
                           "radius_option_keys": _radius_option_keys(ctx0, ctx1), "nproc_all": os.cpu_count()}
    arcs = []
    for s in range(ctx1.ev.n_scenarios):
        t1 = time.perf_counter()
        _i, lib1 = ctx1.ev.template(s)
        b1 = time.perf_counter() - t1
        t1 = time.perf_counter()
        _i, lib0 = ctx0.ev.template(s)
        b0 = time.perf_counter() - t1
        arcs.append({"scenario": s, "n_arcs_radius": len(lib1), "n_arcs_none": len(lib0),
                     "n_arcs_none_expected": EXPECTED_ARCS[s], "build_s": b1, "build_s_none": b0})
    res["template_arcs"] = arcs
    b_none = [x["build_s_none"] for x in arcs]
    res["factor_python_none_templates"] = sum(b_none) / len(b_none) / (0.5 * sum(LAPTOP_TEMPLATE_S))
    print(json.dumps(C.jsonable({"template_arcs": arcs})), flush=True)
    # (ii) LP factor: 3 LPs x a.threads, before the ILP pool (thread budget)
    res["lp_factor"] = _lp_factor(ctx0, a)
    print(json.dumps(C.jsonable({k: res["lp_factor"][k] for k in ("mean_runtime_s", "factor_lp", "solo_s0")})), flush=True)
    # (iii) ILP factor on an isolated evaluator: same keys, no cache read or write
    ev_f = ctx0.ev.derive()
    ev_f.cache, ev_f.index_path, ev_f.sched_dir, ev_f.new_rows = {}, None, None, []
    cells: List[tuple] = [("factor", FACTOR_LAYOUT, "relaxed", s) for s in FACTOR_SCENARIOS]
    cells += [("radius", key, target, s) for key, target in RADIUS_LAYOUTS for s in range(ctx0.ev.n_scenarios)]

    def job(cell):
        kind, key, target, s = cell
        lay = BL.Layout.from_key(key)
        ev0 = ctx0.ev if target == "relaxed" else ctx0.ev_written
        r0 = ev0.evaluate_scenario(lay, s, time_limit=300.0)          # cached laptop row
        if kind == "factor":
            t1 = time.perf_counter()
            r = ev_f.evaluate_scenario(lay, s, force=True, time_limit=300.0)
            out = {"kind": kind, "layout_key": key, "target": target, "scenario": s, "laptop": _row_brief(r0),
                   "server": _row_brief(r), "wall_s": time.perf_counter() - t1}
            rl, rs_ = r0.get("runtime_s"), r.get("runtime_s")
            out["laptop_reference_ok"] = bool(r0.get("cache_hit") and float(r0.get("time_limit") or 0) == 300.0
                                              and r0.get("status") == "OPTIMAL")
            out["runtime_ratio"] = None if not (rl and rs_) else float(rs_) / float(rl)
            out["censored"] = r.get("status") != "OPTIMAL"       # a TIME_LIMIT ratio is a lower bound
            out["total_diff"] = None if (r.get("total") is None or r0.get("total") is None) else float(r["total"]) - float(r0["total"])
            nl, ns = r0.get("node_count"), r.get("node_count")
            out["nodes_per_s_ratio"] = (None if not (nl and ns and rl and rs_)
                                        else (float(ns) / float(rs_)) / (float(nl) / float(rl)))
            return out
        ev1 = ctx1.ev if target == "relaxed" else ctx1.ev_written
        tl = max(300.0, float(r0.get("time_limit") or 300.0))
        warm, wsrc = _warm_of(ev0, r0, base_cache)
        r1 = ev1.evaluate_scenario(lay, s, time_limit=tl, warm=warm)
        return {"kind": kind, "layout_key": key, "target": target, "scenario": s, "time_limit": tl, "warm_source": wsrc,
                "none": _row_brief(r0), "radius": _row_brief(r1)}

    rows, factor_rows = [], []
    with cf.ThreadPoolExecutor(max_workers=int(a.workers)) as pool:
        for r in pool.map(job, cells):
            if r["kind"] == "factor":
                factor_rows.append(r)
                print(json.dumps(C.jsonable({k: r[k] for k in ("scenario", "runtime_ratio", "censored", "total_diff")})),
                      flush=True)
                continue
            n, d = r["none"], r["radius"]
            v0, v1 = n.get("total"), d.get("total")
            b0, b1 = n.get("bound"), d.get("bound")
            r["diff"] = None if (v0 is None or v1 is None) else float(v1) - float(v0)
            r["diff_rel"] = None if r["diff"] is None else r["diff"] / float(v0)
            # radius restricts arcs: true diff >= 0; [bound_r - total_n, total_r - bound_n] contains it
            r["diff_lo"] = None if (b1 is None or v0 is None) else float(b1) - float(v0)
            r["diff_hi"] = None if (v1 is None or b0 is None) else float(v1) - float(b0)
            rows.append(r)
            print(json.dumps(C.jsonable({k: r[k] for k in ("layout_key", "target", "scenario", "diff", "diff_lo", "diff_hi")})),
                  flush=True)
    res["cells"] = rows
    ok = [f for f in factor_rows if f["laptop_reference_ok"] and f["runtime_ratio"] is not None]
    res["ilp_factor"] = {"rows": factor_rows, "concurrent_ilps": int(a.workers), "threads": int(a.threads),
                         "factor_ilp": (sum(f["runtime_ratio"] for f in ok) / len(ok)) if ok else None,
                         "censored": any(f["censored"] for f in ok),
                         "note": f"server rows ran with {a.workers} concurrent ILPs x {a.threads} threads; the laptop rows "
                                 "are pass-2 solves (3 threads); a censored (TIME_LIMIT) ratio is a lower bound"}
    per_layout = []
    for key, target in RADIUS_LAYOUTS:
        rr = [r for r in rows if r["layout_key"] == key]
        st1 = [r["radius"].get("status") for r in rr]
        st0 = [r["none"].get("status") for r in rr]
        base = {"layout_key": key, "target": target, "statuses_radius": st1, "statuses_none": st0,
                "time_limits": [r["time_limit"] for r in rr], "warm_sources": [r["warm_source"] for r in rr],
                "gaps_none": [r["none"].get("gap") for r in rr], "gaps_radius": [r["radius"].get("gap") for r in rr]}
        if not all(r["diff"] is not None for r in rr):
            lost = any(str(x).startswith("INFEASIBLE") for x in st1) and not any(str(x).startswith("INFEASIBLE") for x in st0)
            per_layout.append({**base, "diff": None, "lost_feasibility": lost,
                               "note": "a value is missing (e.g. INFEASIBLE_TERMINAL under the radius)"})
            continue
        k = len(rr)
        v0 = sum(r["none"]["total"] for r in rr) / k
        v1 = sum(r["radius"]["total"] for r in rr) / k
        lo = None if any(r["diff_lo"] is None for r in rr) else sum(r["diff_lo"] for r in rr) / k
        hi = None if any(r["diff_hi"] is None for r in rr) else sum(r["diff_hi"] for r in rr) / k
        per_layout.append({**base, "V_none": v0, "V_radius": v1, "diff": v1 - v0, "diff_rel": (v1 - v0) / v0,
                           "diff_lo": lo, "diff_hi": hi, "diff_lo_rel": None if lo is None else lo / v0,
                           "diff_hi_rel": None if hi is None else hi / v0})
    res["per_layout"] = per_layout
    diffs = [abs(p["diff_rel"]) for p in per_layout if p.get("diff") is not None]
    res["n_missing"] = sum(1 for p in per_layout if p.get("diff") is None)
    res["max_abs_diff_rel"] = max(diffs) if diffs else None
    his = [p.get("diff_hi_rel") for p in per_layout if p.get("diff") is not None]
    los = [p.get("diff_lo_rel") for p in per_layout if p.get("diff") is not None]
    res["max_diff_hi_rel"] = None if (not his or None in his) else max(his)
    res["max_diff_lo_rel"] = None if (not los or None in los) else max(los)
    tol = 0.01
    if any(p.get("lost_feasibility") for p in per_layout):
        res["verdict"], note = "raise", "a layout lost feasibility under the radius (see per_layout)"
    elif res["n_missing"] or res["max_diff_hi_rel"] is None or res["max_diff_lo_rel"] is None:
        res["verdict"], note = "inconclusive (gap)", "a value or a bound is missing (see per_layout)"
    elif res["max_diff_hi_rel"] <= tol:
        res["verdict"], note = "keep 14", "the upper end of the difference (total_radius - bound_none) is <= 1 % on every layout"
    elif res["max_diff_lo_rel"] > tol:
        res["verdict"], note = "raise", "the lower end of the difference (bound_radius - total_none) exceeds 1 % on a layout: " \
                                        "raise the radius to 20 blocks and redo the size table (design 5.1.3)"
    else:
        res["verdict"], note = "inconclusive (gap)", "diff_lo <= 1 % < diff_hi: the MIP gaps decide; re-solve longer"
    res["verdict_note"] = note
    res["n_new_solves"] = ctx1.ev.n_solves + ctx1.ev_written.n_solves
    res["n_factor_solves"] = ev_f.n_solves
    res["solver_time_s"] = ctx1.ev.solver_time + ctx1.ev_written.solver_time
    res["wall_s"] = time.perf_counter() - t0
    res["rss_gb_peak"] = _rss_gb()
    _dump(os.path.join(a.out, "radius.json"), res)
    return res


# ---------------------------------------------------------------------------
def cmd_price(a: argparse.Namespace) -> Dict[str, Any]:
    """One exact pricing ILP of the M09 location (``force=True``: never a cache hit), with the
    template, layout-library, model-build and solve times separated."""
    t0 = time.perf_counter()
    extra = shlex.split(a.r7_args) + ["--out-dir", a.setup_dir, "--dry-run"]
    ctx = _ctx(extra)
    cand = next((c for c in ctx.candidates if getattr(c, "lattice_id", None) == "M09"), None)
    if cand is None:
        cand = max(ctx.candidates, key=lambda c: getattr(c, "n_restaurants", 0))
    lay = BL.Layout.of([(cand.id, "SC", 3, 2)])
    s = next((i for i, d in enumerate(ctx.design) if d["day_type"] == "weekday" and abs(float(d["level"]) - 1.25) < 1e-9), 0)
    t1 = time.perf_counter()
    _ti, tlib = ctx.ev.template(s)
    template_s = time.perf_counter() - t1
    t1 = time.perf_counter()
    _inst, lib = ctx.ev.layout_pair(lay, s)
    library_s = time.perf_counter() - t1
    t1 = time.perf_counter()
    r = ctx.ev.evaluate_scenario(lay, s, time_limit=float(a.time_limit), force=True)
    res = {"layout_key": lay.key(), "candidate": cand.id, "lattice_id": getattr(cand, "lattice_id", None),
           "scenario": s, "design": {k: v for k, v in ctx.design[s].items() if k != "overrides"},
           "row": _row_brief(r), "template_s": template_s, "n_arcs_template": len(tlib), "library_s": library_s,
           "library_time_s": ctx.ev.library_time, "n_arcs_layout": len(lib),
           "infeasible_bikes": [str(b) for b in lib.infeasible_bikes], "evaluate_wall_s": time.perf_counter() - t1,
           "wall_s": time.perf_counter() - t0, "rss_gb_peak": _rss_gb(),
           "n_candidates": len(ctx.candidates), "threads": ctx.ev.threads}
    _dump(os.path.join(a.setup_dir, "price_probe.json"), res)
    return res


# ---------------------------------------------------------------------------
def cmd_feas(a: argparse.Namespace) -> Dict[str, Any]:
    """Terminal reachability of every one-site layout (``<loc>:SC:B3:C2``) under the given r7
    arguments, library builds only (no solve): the approach radius can make a one-site layout
    INFEASIBLE_TERMINAL that is feasible without it (laptop smoke 2026-10-21: a bike starting at
    the northern entry point with q0 = 8 of 24 reaches a southern site only by the direct move)."""
    t0 = time.perf_counter()
    ctx = _ctx(shlex.split(a.r7_args) + ["--out-dir", a.setup_dir, "--dry-run"])
    scen = [int(x) for x in a.scen.split()] if a.scen else list(range(ctx.ev.n_scenarios))
    rows = []
    for c in ctx.candidates:
        if "SC" not in ctx.ev.roles_of[c.id]:
            continue
        lay = BL.Layout.of([(c.id, "SC", 3, 2)])
        for s in scen:
            inst, lib = ctx.ev.layout_pair(lay, s)
            inf = [str(b) for b in lib.infeasible_bikes]
            starts = {str(b.id): b.v0 for b in inst.bikes}
            rows.append({"layout_key": lay.key(), "lattice_id": getattr(c, "lattice_id", None), "scenario": s,
                         "n_arcs": len(lib), "n_infeasible_bikes": len(inf),
                         "infeasible": [[i, str(starts.get(i)), int(q0)] for i, q0 in
                                        ((str(b.id), b.q0) for b in inst.bikes) if i in inf]})
    res = {"r7_args": a.r7_args, "scenarios": scen, "n_layouts": len(rows),
           "n_infeasible_layout_scenarios": sum(1 for r in rows if r["n_infeasible_bikes"]),
           "infeasible_layouts": sorted({r["layout_key"] for r in rows if r["n_infeasible_bikes"]}),
           "rows": rows, "wall_s": time.perf_counter() - t0, "rss_gb_peak": _rss_gb()}
    _dump(os.path.join(a.setup_dir, "feas_one_site.json"), res)
    print(json.dumps({k: res[k] for k in ("n_layouts", "n_infeasible_layout_scenarios", "infeasible_layouts")}), flush=True)
    return res

# ---------------------------------------------------------------------------
def cmd_synth(a: argparse.Namespace) -> str:
    """Synthetic stand-in for the DOT CSV (only when the real file is absent): ``n`` rows on the
    restaurant-densest grid nodes of the study band at least ``spacing`` blocks apart, type
    cycling through pilot / shortlist / citibike_charging / depot; every name starts with
    'SYNTHETIC'."""
    from ebike_swap_sim import data_nyc as dn
    from ebike_swap_sim import sites_nyc as S
    reg = dn.resolve_region("manhattan_s110")
    rest = dn.region_restaurants(reg)
    counts: Dict[Any, int] = {}
    for v in rest["node"]:
        v = tuple(v) if isinstance(v, (list, tuple)) else v
        counts[v] = counts.get(v, 0) + 1
    chosen: List[Any] = []
    for v, _n in sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        if all(S.manhattan_blocks(v, w) >= int(a.spacing) for w in chosen):
            chosen.append(v)
        if len(chosen) >= int(a.n):
            break
    types = ("pilot", "shortlist", "citibike_charging", "depot", "shortlist")
    os.makedirs(os.path.dirname(os.path.abspath(a.path)), exist_ok=True)
    with open(a.path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "address", "lat", "lon", "site_type", "operator", "status_date", "source_url",
                    "coord_method", "verdict", "angle"])
        for i, v in enumerate(chosen):
            lat, lon = reg.box.node_latlon(v)
            w.writerow([f"SYN{i + 1:03d}", f"SYNTHETIC restaurant-dense node {v} ({counts[v]} restaurants)", "", f"{lat:.7f}",
                        f"{lon:.7f}", types[i % len(types)], "synthetic", "", "", "grid node", "confirmed", "synthetic"])
    print(f"# wrote {len(chosen)} SYNTHETIC rows to {a.path}", flush=True)
    return a.path


# ---------------------------------------------------------------------------
def _setup_summary(d: str) -> Optional[Dict[str, Any]]:
    rec_path = os.path.join(d, "records.jsonl")
    if not os.path.exists(rec_path):
        return None
    from experiments.r6_o2_siting import load_jsonl_lenient
    recs = load_jsonl_lenient(rec_path)
    last = {}
    for r in recs:
        last[r.get("kind")] = r
    plan, sizes = last.get("plan") or {}, last.get("sizes") or {}
    out: Dict[str, Any] = {"dir": d, "n_candidates": plan.get("n_candidates"), "n_hub_capable": plan.get("n_hub_capable"),
                           "candidate_classes": plan.get("candidate_classes"), "dot_info": plan.get("dot_info"),
                           "n_orders": plan.get("n_orders"), "scenarios": plan.get("scenarios"),
                           "n_options": plan.get("n_options"), "n_w": plan.get("n_w"), "access": plan.get("access"),
                           "snap_m_max": plan.get("snap_m_max"), "pruning": plan.get("pruning"),
                           "aborted": [r for r in recs if r.get("kind") == "aborted"],
                           "config_md5": plan.get("config_md5"), "approach_radius": plan.get("approach_radius")}
    # radius convention of the run (adversarial review of 2026-10-21): runs from before the start-state
    # exemption (no exemption, or the whole-tail exemption) measure other libraries -> flagged stale
    pr = plan.get("pruning") or {}
    if "reposition_target_radius" not in pr:
        out["radius_convention"] = "none"
    elif pr.get("reposition_radius_exempt_states"):
        out["radius_convention"] = "exempt_states"
    elif "reposition_radius_exempt_tails" in pr:
        out["radius_convention"] = "exempt_tails (stale)"
    else:
        out["radius_convention"] = "no_exemption (stale)"
    out["stale"] = (not plan) or out["radius_convention"].endswith("(stale)")
    if sizes:
        tpl = sizes.get("templates") or []
        out["template_arcs"] = [t["n_arcs"] for t in tpl]
        out["template_build_s"] = [round(t["build_s"], 1) for t in tpl]
        out["n_services"] = [t["n_services"] for t in tpl]
        out["infeasible_bikes"] = [t["infeasible_bikes"] for t in tpl]
        out["lp_sizes"] = sizes.get("lp")
        out["z_columns"] = sizes.get("z_columns")
        out["superset"] = sizes.get("superset")
        out["rss_gb"] = {k: sizes.get(k) for k in ("rss_gb_start", "rss_gb_after_lps", "rss_gb_end")}
        out["lp_timings"] = sizes.get("timings")
        out["all_open_equals_superset_max_abs"] = sizes.get("all_open_equals_superset_max_abs")
    sb = last.get("superset_bound") or {}
    out["superset_rows"] = [{k: r.get(k) for k in ("scenario", "status", "bound", "runtime_s", "n_arcs", "wall_s")}
                            for r in (sb.get("rows") or [])]
    # a superset LP that is not LP_OPTIMAL gives L_s = 0 silently (and bound.json has no time limit in its key)
    out["superset_non_optimal"] = [{"scenario": r.get("scenario"), "status": r.get("status"), "runtime_s": r.get("runtime_s")}
                                   for r in out["superset_rows"] if r.get("status") != "LP_OPTIMAL"]
    # per-scenario cold-barrier times of the size subset LPs and their ratio to the two-site LP
    tim = (sizes or {}).get("timings") or {}
    n_cell = (tim.get("one_cell_free") or {}).get("n_locations")
    n_all = (tim.get("all_open_free") or {}).get("n_locations")
    # a per-scenario fixed-layout time whose LP has artificial > 0 (a bike without a reachable
    # terminal arc in that scenario) is not a fixed-layout time: dropped from the ratios
    def _clean(name: str) -> List[Optional[float]]:
        t = tim.get(name) or {}
        rt, art = t.get("runtime_s") or [], t.get("artificial") or []
        return [None if (i < len(art) and (art[i] or 0.0) > 1e-9) else x for i, x in enumerate(rt)]
    two_rt, one_rt = _clean("two_site"), _clean("one_site")
    out["fixed_layout_artificial_scenarios"] = {
        k: [i for i, x in enumerate((tim.get(k) or {}).get("artificial") or []) if (x or 0.0) > 1e-9]
        for k in ("one_site", "two_site")}
    sub = []
    for r in recs:
        if r.get("kind") != "subset_lp" or r.get("tag") != "size":
            continue
        s, na = r.get("scenario"), len(r.get("atoms") or [])
        rt = r.get("runtime_s")
        t2 = two_rt[s] if isinstance(s, int) and s < len(two_rt) else None
        t1 = one_rt[s] if isinstance(s, int) and s < len(one_rt) else None
        sub.append({"scenario": s, "which": "all_open" if na == n_all else "one_cell" if na == n_cell else None,
                    "n_atoms": na, "runtime_s": rt, "method": r.get("method"), "Qs": r.get("Qs"), "L": r.get("L"),
                    "two_site_runtime_s": t2, "ratio_subset_to_two_site": (rt / t2) if (rt and t2) else None,
                    "ratio_subset_to_one_site": (rt / t1) if (rt and t1) else None})
    out["subset_lp_size"] = sub
    for which in ("one_cell", "all_open"):
        rs = [x["ratio_subset_to_two_site"] for x in sub if x["which"] == which and x["ratio_subset_to_two_site"]]
        out[f"ratio_{which}_to_two_site"] = {"mean": sum(rs) / len(rs), "max": max(rs)} if rs else None
    out["representative_layouts"] = {k: {kk: (tim.get(k) or {}).get(kk) for kk in
                                         ("layout", "lattice_ids", "infeasible_bikes", "skipped_infeasible", "check_scenarios")}
                                     for k in ("one_site", "two_site")}
    lps = last.get("lp_sizes") or {}
    out["lp_build_s"] = lps.get("build_s")
    wt = os.path.join(d, "wall_time.json")
    if os.path.exists(wt):
        out["wall_time"] = C.load_jsonl(wt)
    fp = os.path.join(d, "feas_one_site.json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as fh:
            fe = json.load(fh)
        out["feas_one_site"] = {k: fe.get(k) for k in ("scenarios", "n_layouts", "n_infeasible_layout_scenarios",
                                                        "infeasible_layouts", "wall_s")}
    pp = os.path.join(d, "price_probe.json")
    if os.path.exists(pp):
        with open(pp, encoding="utf-8") as fh:
            out["price_probe"] = json.load(fh)
    return out


def cmd_summary(a: argparse.Namespace) -> Dict[str, Any]:
    res: Dict[str, Any] = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "host": os.uname().nodename}
    for name in ("repro", "radius"):
        p = os.path.join(a.out, f"{name}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                res[name] = json.load(fh)
    # only the driver's setup dirs (dot_N<N>_S<SCEN>); older dot_N* / laptop smoke dirs are not mixed
    # in, and every entry carries its radius convention (stale entries are listed separately)
    res["setup"] = {os.path.basename(d): _setup_summary(d) for d in sorted(glob.glob(os.path.join(a.out, "dot_N*_S*")))
                    if os.path.isdir(d)}
    res["setup_stale"] = sorted(k for k, v in res["setup"].items() if v and v.get("stale"))
    res["feas_r5"] = {}
    for d in sorted(glob.glob(os.path.join(a.out, "feas_r5_*"))):
        fp = os.path.join(d, "feas_one_site.json")
        if os.path.exists(fp):
            with open(fp, encoding="utf-8") as fh:
                fe = json.load(fh)
            res["feas_r5"][os.path.basename(d)] = {k: fe.get(k) for k in ("scenarios", "n_layouts",
                                                                          "n_infeasible_layout_scenarios",
                                                                          "infeasible_layouts")}
    steps = os.path.join(a.out, "steps.jsonl")
    if os.path.exists(steps):
        res["steps"] = C.load_jsonl(steps)
    # laptop-to-server factors (server / laptop time; > 1 = the server is slower)
    rad, rep_ = res.get("radius") or {}, res.get("repro") or {}
    bs = [x.get("build_s") for x in (rep_.get("template_arcs") or []) if x.get("build_s")]
    fac: Dict[str, Any] = {
        "factor_ilp": (rad.get("ilp_factor") or {}).get("factor_ilp"),
        "factor_ilp_censored": (rad.get("ilp_factor") or {}).get("censored"),
        "factor_ilp_note": (rad.get("ilp_factor") or {}).get("note"),
        "factor_lp": (rad.get("lp_factor") or {}).get("factor_lp"),
        "factor_lp_range": (rad.get("lp_factor") or {}).get("factor_lp_range"),
        "factor_lp_solo": (rad.get("lp_factor") or {}).get("factor_lp_solo"),
        "factor_python": (sum(bs) / len(bs) / (0.5 * sum(LAPTOP_TEMPLATE_S))) if bs else rad.get("factor_python_none_templates"),
        "factor_python_source": "repro.json template build_s / 11 s" if bs else "radius.json none-template build_s / 11 s",
        "factor_python_radius_step": rad.get("factor_python_none_templates")}
    res["factors"] = fac
    res["radius_verdict"] = {k: rad.get(k) for k in ("verdict", "verdict_note", "max_diff_lo_rel", "max_diff_hi_rel",
                                                      "max_abs_diff_rel", "n_missing")} if rad else None
    res["superset_non_optimal"] = {k: v.get("superset_non_optimal") for k, v in res["setup"].items()
                                   if v and v.get("superset_non_optimal")}
    _dump(os.path.join(a.out, "probe_summary.json"), res)
    return res


def main(argv: Optional[List[str]] = None) -> Any:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("repro", "radius", "price", "feas", "synth", "summary"):
        p = sub.add_parser(name)
        p.add_argument("--out", default=OUT_DEFAULT)
        p.add_argument("--threads", type=int, default=3)
        p.add_argument("--workers", type=int, default=4)
        p.add_argument("--max-threads", type=int, default=12)
        p.add_argument("--radius", type=int, default=14)
        p.add_argument("--time-limit", type=float, default=300.0)
        p.add_argument("--setup-dir", default=None)
        p.add_argument("--r7-args", default="")
        p.add_argument("--path", default=None)
        p.add_argument("--n", type=int, default=50)
        p.add_argument("--spacing", type=int, default=3)
        p.add_argument("--scen", default="", help="feas: scenario indices, e.g. '0 1 2' (default all)")
    a = ap.parse_args(argv)
    a.out = os.path.abspath(a.out)
    if a.workers * a.threads > a.max_threads:
        raise SystemExit("workers x threads exceeds --max-threads")
    return {"repro": cmd_repro, "radius": cmd_radius, "price": cmd_price, "feas": cmd_feas, "synth": cmd_synth,
            "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    main()
