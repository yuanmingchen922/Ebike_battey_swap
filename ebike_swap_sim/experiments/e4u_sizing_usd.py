"""Experiment E4u -- station sizing under USD (round 2): spares B_j, chargers C_j, power P_j.

Round-2 re-run of ``experiments/e4_sizing.py`` on the ``usd4h`` family of
``DECISIONS.md`` R2.2 (6 bikes / 36 orders / H 48 / L 12, dinner window 17:00-21:00,
3 co-located sites, ``q0 ~ U{4..7}`` = 30-60 % of ``L``) priced in the ``usd_sunk``
coefficients of R2.1 (kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h,
F 12.03 $, bB 0.332 $, bC 0.082 $ per site per 4 h window), with the round-2
baseline rules of R2.3 (stock-aware site choice, DEMAND_AWARE charging, JIT dispatch).

Questions (plan E4 restated in USD): what does a coordinator *buy* when ``B_j``, ``C_j``
are free at the ``usd_sunk`` prices (``y_j = 1`` fixed), how do cost and service respond
to ``B_j``, ``C_j``, ``P_j`` at fixed sizes for the ILP and for the baseline, what is
the marginal value of one battery / one charger / one kW per window and per year, and
how many spares does the baseline need to reach the ILP's service level?

Runs per seed (all on the SAME generated instance; only ``B``, ``C``, ``P_kw`` of the
three sites change, so orders, bikes and routes are byte-identical across methods and
sizes; the arc library (1)-(4), (9) is rebuilt per variant because
``baseline.run_baseline`` insists on ``lib.inst == inst``):

* sweep ``B_j in B_SWEEP = {1,2,3,4,6}`` at ``C_j = 2``, ``P_j = 4 kW`` (R2.2 defaults);
* sweep ``C_j in C_SWEEP = {1,2,3,4}`` at ``B_j = 3``, ``P_j = 4 kW`` (``C_j <= Cbar_j = 6``);
* sweep ``P_j in P_SWEEP = {1.4, 2.8, 4.2} kW`` at ``B_j = 3`` and ``C_j = P_SWEEP_C = 4``:
  with ``p_ch = eps / (eta Delta)`` (19) = 0.667 kW the site limit (20) allows
  ``floor(P_j / p_ch)`` = 2 / 4 / 6 simultaneous chargers, so it binds only at 1.4 kW
  (at the R2.2 default ``C_j = 2`` none of the three values would bind, and the sweep
  would be flat by construction); the shared grid group (21) (8 kW, 6 kW 18-20 h)
  caps 3 x 4 x 0.667 = 8 kW of chargers at 6 kW in the peak hours at every ``P_j``;
* the ``B x C`` grid ``B_SWEEP x C_SWEEP`` at ``P_j = 4 kW`` (the two sweep lines are part
  of it; the 12 off-line cells are solved on ``HEAT_SEEDS`` only, default seed 0, to
  respect the 60 min wall budget);
* the ILP with ``B_j``, ``C_j`` free and ``y_j = 1`` fixed under the ``usd_sunk`` setup
  prices (27) ``bB``, ``bC`` and the bounds (7)-(8) ``B_j <= K_j = 8``,
  ``C_j <= min(Cbar_j, K_j) = 6`` -- "what the coordinator buys"; then the baseline at
  the chosen sizes (and the fixed-size ILP there when the point is not already on the grid).

Methods: the E2 ILP (5)-(22), (26)-(32) through :func:`experiments.common.run_ilp_case`
(Gurobi ``OutputFlag 0``, ``Threads 3``, ``TimeLimit <= 300 s``), warm-started with the
baseline schedule chosen by :func:`experiments.common.feasible_mip_start` (the R2.3
default may violate the report-only (18); the ``mip_start_variant`` column records the
injected policy), and the round-2 baseline (``BaselineParams`` defaults; no transfers,
there are no services on the co-located layout, so ``C_reb = 0``).  Pruning:
``pruning_for(inst, reachable=True)`` -- the plan's pruning plus ``reachable_pruning``,
shown lossless on this family by ``experiments/r2_size_probe.py`` (identical optima,
~40 % fewer arcs).

Reported per run (``outputs/e4u_sizing_usd/results.csv``, one row per variant x method):
total (26) and components (27)-(32), ``operational = total - C_setup``, served share,
mean / max response and lateness, bike km, swaps, kWh purchased, transfers, the
baseline's report-only violations, swap-wait / stock-out / charger-utilisation /
desk-occupancy diagnostics of :func:`experiments.e4_sizing.site_metrics`, solver
statistics and the chosen ``B_j`` / ``C_j``.  ``summary_<sweep>.csv`` hold the per-size
seed means and the finite-difference marginal values per unit added at one site
(network change / 3 sites / step) **per window and per year** (``x 4 windows/day x 365``
= 1460, i.e. ``16 h / 4 h x 365`` as in the task), ``summary_heat_*.csv`` the grid,
``spares_to_match.csv`` the smallest ``B_j`` at which the baseline reaches the ILP's
service level at the R2.2 default size, ``gap_decomposition.csv`` the baseline - ILP
split by component.  Figures: ``cost_vs_B.png``, ``cost_vs_C.png``, ``cost_vs_P.png``,
``heatmap_BxC.png``.  Headline gap = ``(baseline - ILP) / baseline``.

Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/e4u_sizing_usd.py [--seeds 0 1 2] [--time-limit 300] [--heat-seeds 0]
    PYTHONPATH=. python3 experiments/e4u_sizing_usd.py --report-only
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from experiments import common as C  # noqa: E402
from experiments.e4_sizing import _schedule_row, _uniform, sized_instance  # noqa: E402
from ebike_swap_sim import Instance, Schedule, facility_vars  # noqa: E402

plt = C.plt

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e4u_sizing_usd")
FAMILY = "usd4h"                       # R2.2: 6 bikes / 36 orders / H 48 / L 12, usd_sunk
SEEDS = [0, 1, 2]
HEAT_SEEDS = [0]                       # seeds on which the off-line B x C cells are solved
TIME_LIMIT = 300.0
B_SWEEP = [1, 2, 3, 4, 6]
C_SWEEP = [1, 2, 3, 4]
P_SWEEP = [1.4, 2.8, 4.2]
P_SWEEP_C = 4                          # chargers per site on the P sweep (so that (20) can bind)
BASE_B, BASE_C, BASE_P = 3, 2, 4.0     # R2.2 defaults (generator.DEFAULT_FACILITIES_SPEC_R2)
N_SITES = 3
WINDOW_H = 4.0
WINDOWS_PER_YEAR = (16.0 / WINDOW_H) * 365.0    # task: x 16 h / 4 h x 365 = 1460
PRUNING = {"reachable": True}          # pruning_for(inst, **PRUNING): plan pruning + reachable (lossless)

COLOR_ILP = "#2a78d6"
COLOR_BASE = "#eb6834"
METHOD_STYLE = {
    "ILP": dict(color=COLOR_ILP, linestyle="-", label="ILP (E2, rho = 0.5)"),
    "baseline": dict(color=COLOR_BASE, linestyle="-", label="baseline (R2.3 rules)"),
}
COMPONENTS = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"]
AGG_COLS = ["total", "operational", "C_setup", "C_elec", "C_travel", "C_orders", "unserved", "response",
            "lateness", "n_unserved", "served_share", "mean_response_h", "max_response_h", "n_late",
            "mean_lateness_h", "max_lateness_h", "bike_km", "n_swaps", "kwh_purchased", "transfers_used",
            "swap_wait_slots", "stockout_slots", "stockout_queue_slots", "charger_util_mean",
            "desk_occupancy_mean", "idle_full_share_mean", "peak_kw_group", "end_full_total", "runtime_s", "gap"]
SWEEP_SPEC = {"B": ("B_j", {"C_j": BASE_C, "P_kw": BASE_P}),
              "C": ("C_j", {"B_j": BASE_B, "P_kw": BASE_P}),
              "P": ("P_kw", {"B_j": BASE_B, "C_j": P_SWEEP_C})}


# ---------------------------------------------------------------------------
# one variant
# ---------------------------------------------------------------------------
def run_variant(inst: Instance, sweep: str, time_limit: float, free: bool = False,
                run_baseline: bool = True, chain: Optional[Tuple[Schedule, str]] = None
                ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Baseline (R2.3 rules) + ILP on one sized instance; returns ``(rows, extras)``.

    The library is built with :data:`PRUNING` (plan pruning + ``reachable_pruning``,
    lossless on ``usd4h`` per the R2 implementation notes).  The baseline is
    :func:`experiments.common.run_baseline_case` with the ``BaselineParams`` defaults
    (DECISIONS R2.3); the MIP start is picked by
    :func:`experiments.common.feasible_mip_start` because the R2.3 default schedule
    may report (18) (``mip_start_variant`` records the injected policy; the baseline
    row always describes the default policy).  For ``free=True`` (B_j, C_j free under
    (7)-(8) and the usd_sunk prices (27)) no baseline exists; ``extras`` returns the
    sizes the ILP chose.  ``chain = (schedule, label)`` offers the ILP schedule of the
    next-smaller size as the MIP start (:func:`chain_start`): a schedule feasible at
    ``(B, C, P)`` stays feasible at larger sizes ((13)-(18), (20)-(21) only relax, the
    untouched extra spares stay full so (17)-(18) keep holding), and it is a better
    incumbent than the baseline; it is used whenever the baseline start is not clean
    (``mip_start_variant = 'chain:<tag>'``), otherwise the clean policy schedule is kept.
    Rows carry the cost components (26)-(32), the service metrics of
    ``evaluate.metrics``, the station diagnostics of
    :func:`experiments.e4_sizing.site_metrics` and the solver statistics.
    """
    lib, t_build = C.build_library(inst, C.pruning_for(inst, **PRUNING))
    var = inst.meta["variant"]
    common = {
        "seed": inst.meta.get("seed"), "family": inst.meta.get("family"), "sweep": sweep,
        "tag": var["tag"], "free_sizes": free, "rho": inst.rho,
        "B_j": _uniform(var["B"]), "C_j": _uniform(var["C"]), "P_kw": _uniform(var["P_kw"]),
        "B_sites": json.dumps(var["B"]), "C_sites": json.dumps(var["C"]),
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
        "q0_mean": sum(b.q0 for b in inst.bikes) / len(inst.bikes),
        "p_ch_kw": inst.disc.p_ch_kw, "n_arcs": len(lib), "arc_build_s": t_build,
        "cost_variant": inst.meta.get("cost_variant"),
    }
    rows: List[Dict[str, Any]] = []
    start: Optional[Schedule] = None
    start_label = None
    if run_baseline and not free:
        base = C.run_baseline_case(inst, lib)
        start, start_label = C.feasible_mip_start(inst, lib, base)
        if chain is not None and (start_label == "default" and base["families"]):
            start, start_label = chain_start(chain[0], inst, lib), f"chain:{chain[1]}"
        rows.append({**common, "method": "baseline", "mip_start_variant": None,
                     **_schedule_row(inst, lib, base, base["schedule"]),
                     **_extra_metrics(base),
                     "baseline_report_only_ok": base["ok_modulo_report_only"],
                     "stock_aware_fallbacks": base["flags"].get("stock_aware_fallbacks"),
                     "jit_dispatches": base["flags"].get("jit_dispatches")})
    ilp = C.run_ilp_case(inst, lib, mip_start=start, time_limit=time_limit, threads=C.THREADS, label="ilp")
    rows.append({**common, "method": "ILP", "mip_start_variant": start_label,
                 **_schedule_row(inst, lib, ilp, ilp["schedule"]), **_extra_metrics(ilp)})
    extras: Dict[str, Any] = {}
    if ilp["schedule"] is not None:
        _y, Bc, Cc = facility_vars(inst, ilp["schedule"])
        extras = {"B": {str(j): int(v) for j, v in Bc.items()}, "C": {str(j): int(v) for j, v in Cc.items()},
                  "_schedule": ilp["schedule"], "_lib": lib}
    return rows, extras


def chain_start(sched: Schedule, inst: Instance, lib: Any) -> Schedule:
    """ILP schedule of a smaller-sized variant re-expressed for ``inst`` / ``lib`` as a
    MIP start: the chosen arcs are re-found by ``(kind, src, dst, order, fac)`` (the
    libraries differ only through the facility fields, so every arc exists), the
    ``y/B/C`` and ``n`` entries are dropped so that ``ilp.set_mip_start`` takes the
    facility data of ``inst`` and rebuilds the stock by the (13) recursion.  E2
    semantics are untouched; this only chooses the start."""
    x: Dict[Any, List[int]] = {}
    for k, ids in sched.x.items():
        new_ids = []
        for a_id in ids:
            a = sched.meta["_lib"].arc(a_id) if "_lib" in sched.meta else None
            if a is None:
                raise ValueError("chain_start needs the source library in sched.meta['_lib']")
            b = lib.find(k, a.kind, a.src, order=a.order, fac=a.fac, dst=a.dst)
            if b is None:
                raise ValueError(f"chained start arc {a_id} of bike {k} missing in the new library")
            new_ids.append(b.id)
        x[k] = new_ids
    return Schedule(x=x, u=dict(sched.u), c=dict(sched.c), h=dict(sched.h), z=dict(sched.z))


def _extra_metrics(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Service / logistics columns of ``evaluate.metrics`` not covered by ``_schedule_row``."""
    m = rec.get("metrics")
    if not m:
        return {}
    return {"max_response_h": m["max_response_h"], "max_lateness_h": m["max_lateness_h"],
            "transfers_used": m["transfers_used"], "n_moves": m["n_moves"], "n_waits": m["n_waits"],
            "kwh_stored": m["kwh_stored"]}


# ---------------------------------------------------------------------------
# plan and main loop
# ---------------------------------------------------------------------------
def variant_plan(heat: bool) -> List[Tuple[str, int, int, float]]:
    """Ordered, de-duplicated ``(sweep, B, C, P)`` list: the B / C / P sweep lines and,
    with ``heat``, the off-line cells of ``B_SWEEP x C_SWEEP`` at ``P_j = BASE_P``."""
    plan: List[Tuple[str, int, int, float]] = []
    seen = set()

    def add(sweep: str, B: int, C_: int, P: float) -> None:
        key = (B, C_, P)
        if key not in seen:
            seen.add(key)
            plan.append((sweep, B, C_, P))

    for B in B_SWEEP:
        add("B", B, BASE_C, BASE_P)
    for C_ in C_SWEEP:
        add("C", BASE_B, C_, BASE_P)
    for P in P_SWEEP:
        add("P", BASE_B, P_SWEEP_C, P)
    if heat:
        for B in B_SWEEP:
            for C_ in C_SWEEP:
                add("heat", B, C_, BASE_P)
    return plan


def main(seeds: Sequence[int] = SEEDS, time_limit: float = TIME_LIMIT, heat_seeds: Sequence[int] = HEAT_SEEDS,
         out_dir: str = OUT_DIR, probe: bool = False, free: bool = True, wall_budget_min: float = 58.0
         ) -> List[Dict[str, Any]]:
    """Run E4u and write ``results.csv``, summaries, figures and ``RESULTS.md``.

    Priority phases under the wall budget (``wall_budget_min``; a variant is skipped
    once the budget is exhausted and listed in ``run_meta.json``): (1) per seed the B
    sweep in ascending ``B_j`` with chained starts, then the free-size ILP and the
    baseline at its choice; (2) the C sweep per seed (ascending ``C_j``); (3) the P
    sweep per seed (ascending ``P_j``; ``P_j = 4.2`` only on the first seed because at
    ``C_j = 4`` it is the same model as 2.8 kW, (20) being slack for both); (4) the
    off-line ``B x C`` cells on ``heat_seeds``."""
    C.ensure_dir(out_dir)
    t_start = time.perf_counter()
    rows: List[Dict[str, Any]] = []
    skipped: List[str] = []
    free_choice: Dict[int, Dict[str, Any]] = {}
    csv_path = os.path.join(out_dir, "results.csv")
    seeds = list(seeds)
    bases: Dict[int, Instance] = {}

    def base_of(seed: int) -> Instance:
        if seed not in bases:
            bases[seed] = C.make_instance(FAMILY, seed=seed)
        return bases[seed]

    def budget_left() -> bool:
        return (time.perf_counter() - t_start) / 60.0 < wall_budget_min

    def run_fixed(seed: int, sweep: str, B: int, C_: int, P: float,
                  chain: Optional[Tuple[Schedule, str]]) -> Optional[Tuple[Schedule, str]]:
        tag = f"B{B}_C{C_}_P{P:g}"
        if any(r["seed"] == seed and r["tag"] == tag for r in rows):
            return chain
        if not budget_left():
            skipped.append(f"seed {seed} {tag}")
            return chain
        inst = sized_instance(base_of(seed), B=B, C_=C_, P=P, tag=tag)
        vrows, extras = run_variant(inst, sweep, time_limit, chain=chain)
        rows.extend(vrows)
        _log(vrows, t_start)
        C.write_csv(rows, csv_path)
        if extras.get("_schedule") is not None:
            sch = extras["_schedule"]
            sch.meta["_lib"] = extras["_lib"]
            return sch, tag
        return chain

    phases: List[Tuple[str, List[Tuple[int, str, int, int, float]]]] = []
    if probe:
        phases.append(("probe", [(seeds[0], "B", 1, 1, BASE_P), (seeds[0], "B", BASE_B, BASE_C, BASE_P)]))
        seeds = seeds[:1]
        free = False
        heat_seeds = []
    else:
        phases.append(("B", [(sd, "B", B, BASE_C, BASE_P) for sd in seeds for B in B_SWEEP]))
        phases.append(("C", [(sd, "C", BASE_B, C_, BASE_P) for sd in seeds for C_ in C_SWEEP]))
        phases.append(("P", [(sd, "P", BASE_B, P_SWEEP_C, P) for sd in seeds for P in P_SWEEP
                             if P < max(P_SWEEP) or sd == seeds[0]]))
        phases.append(("heat", [(sd, "heat", B, C_, BASE_P) for sd in heat_seeds for B in B_SWEEP for C_ in C_SWEEP]))
    for phase, items in phases:
        chain: Optional[Tuple[Schedule, str]] = None
        last_seed = None
        for seed, sweep, B, C_, P in items:
            if seed != last_seed:
                chain, last_seed = None, seed
            if phase == "heat":
                chain = None
            chain = run_fixed(seed, sweep, B, C_, P, chain)
            if phase == "B" and B == B_SWEEP[-1] and free and budget_left():
                _run_free(seed, base_of(seed), rows, free_choice, time_limit, t_start, csv_path)
    df = C.write_csv(rows, csv_path)
    wall = time.perf_counter() - t_start
    with open(os.path.join(out_dir, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"seeds": list(seeds), "heat_seeds": list(heat_seeds), "time_limit": time_limit,
                   "family": FAMILY, "wall_s": wall, "probe": probe,
                   "free_choice": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in free_choice.items()},
                   "skipped": skipped, "pruning": PRUNING, "threads": C.THREADS,
                   "windows_per_year": WINDOWS_PER_YEAR}, fh, indent=1)
    report(df, out_dir, wall, time_limit, list(seeds), list(heat_seeds), skipped)
    print(f"done: {len(rows)} rows in {wall / 60:.1f} min -> {out_dir}; skipped {len(skipped)}")
    return rows


def _run_free(seed: int, base: Instance, rows: List[Dict[str, Any]], free_choice: Dict[int, Dict[str, Any]],
              time_limit: float, t_start: float, csv_path: str) -> None:
    """Free-size ILP (B_j, C_j free, y_j = 1 fixed, usd_sunk prices (27)) for one seed,
    then the baseline at the chosen sizes (and the fixed-size ILP there when the point
    is not already on the grid)."""
    inst_free = sized_instance(base, P=BASE_P, free=True, tag="free")
    frows, extras = run_variant(inst_free, "free", time_limit, free=True, run_baseline=False)
    rows.extend(frows)
    _log(frows, t_start)
    if extras:
        free_choice[seed] = {"B": extras["B"], "C": extras["C"]}
        Bu, Cu = _uniform(extras["B"]), _uniform(extras["C"])
        on_grid = any(r["seed"] == seed and r["method"] == "ILP" and r["sweep"] not in ("free", "free_fixed")
                      and r["B_j"] == Bu and r["C_j"] == Cu and r["P_kw"] == BASE_P for r in rows)
        inst_fix = sized_instance(base, B=extras["B"], C_=extras["C"], P=BASE_P, tag="free_fixed")
        if on_grid:   # baseline only; the ILP at these sizes is already on the grid
            lib, _tb = C.build_library(inst_fix, C.pruning_for(inst_fix, **PRUNING))
            bl = C.run_baseline_case(inst_fix, lib)
            var = inst_fix.meta["variant"]
            xrows = [{"seed": seed, "family": FAMILY, "sweep": "free_fixed", "tag": "free_fixed",
                      "free_sizes": False, "rho": inst_fix.rho, "B_j": Bu, "C_j": Cu, "P_kw": BASE_P,
                      "B_sites": json.dumps(var["B"]), "C_sites": json.dumps(var["C"]),
                      "n_bikes": len(inst_fix.bikes), "n_orders": len(inst_fix.orders),
                      "H": inst_fix.H, "L": inst_fix.L, "p_ch_kw": inst_fix.disc.p_ch_kw,
                      "n_arcs": len(lib), "cost_variant": inst_fix.meta.get("cost_variant"),
                      "method": "baseline", "mip_start_variant": None,
                      **_schedule_row(inst_fix, lib, bl, bl["schedule"]), **_extra_metrics(bl),
                      "baseline_report_only_ok": bl["ok_modulo_report_only"]}]
        else:
            sch = extras["_schedule"]
            sch.meta["_lib"] = extras["_lib"]
            xrows, _ = run_variant(inst_fix, "free_fixed", time_limit, chain=(sch, "free"))
        rows.extend(xrows)
        _log(xrows, t_start)
    C.write_csv(rows, csv_path)


def _log(rows: List[Dict[str, Any]], t_start: float) -> None:
    for r in rows:
        print(f"[{(time.perf_counter() - t_start) / 60:5.1f} min] seed {r['seed']} {r['sweep']:>10} "
              f"{r['tag']:<14} {r['method']:>8} status {r['status']:<10} total {C.fmt(r.get('total'), 2)} "
              f"served {C.fmt(r.get('served_share'), 3)} gap {C.fmt(r.get('gap'), 4)} "
              f"t {C.fmt(r.get('runtime_s'), 1)} s start {r.get('mip_start_accepted')} {r.get('mip_start_variant') or ''}",
              flush=True)


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
def sweep_rows(df: pd.DataFrame, sweep: str) -> pd.DataFrame:
    """Rows on the one-at-a-time line of ``sweep`` (whatever label they were run under)."""
    col, fixed = SWEEP_SPEC[sweep]
    sub = df[~df["sweep"].isin(["free", "free_fixed"])]
    for k, v in fixed.items():
        sub = sub[sub[k] == v]
    return sub[sub[col].notna()]


def summarise(df: pd.DataFrame, out_dir: str) -> Dict[str, Any]:
    """Per-size seed means for each sweep and method with finite-difference marginal
    values of the *operational* and *total* cost per unit added at one site, per
    window and per year (``x WINDOWS_PER_YEAR``), the ``B x C`` grid means, the
    baseline - ILP gap decomposition by component (27)-(32) with the headline gap
    ``(baseline - ILP) / baseline`` and the spares-to-match table
    (:func:`spares_to_match`).  Writes ``summary_<sweep>.csv``, ``summary_heat_*.csv``,
    ``gap_decomposition.csv``, ``spares_to_match.csv``."""
    out: Dict[str, Any] = {}
    gap_rows: List[Dict[str, Any]] = []
    for sweep, (col, _fixed) in SWEEP_SPEC.items():
        sub = sweep_rows(df, sweep)
        if sub.empty or sub[col].nunique() < 2:
            continue
        cols = [c for c in AGG_COLS if c in sub.columns]
        g = sub.groupby(["method", col])[cols].agg(["mean", "min", "max"])
        g.columns = [f"{a}_{b}" for a, b in g.columns]
        g["n_seeds"] = sub.groupby(["method", col])["seed"].nunique()
        g = g.reset_index().sort_values(["method", col])
        for method in g["method"].unique():
            m = g[g["method"] == method].sort_values(col)
            sizes = list(m[col])
            for cost_col in ("operational", "total"):
                vals = list(m[f"{cost_col}_mean"])
                mv: List[Optional[float]] = [None] * len(sizes)
                for i in range(len(sizes) - 1):
                    step = (sizes[i + 1] - sizes[i]) * N_SITES
                    mv[i] = (vals[i] - vals[i + 1]) / step if step else None
                g.loc[m.index, f"marginal_{cost_col}_per_unit_window"] = mv
                g.loc[m.index, f"marginal_{cost_col}_per_unit_year"] = [
                    (v * WINDOWS_PER_YEAR if v is not None else None) for v in mv]
        g.to_csv(os.path.join(out_dir, f"summary_{sweep}.csv"), index=False)
        out[sweep] = g
        for size in sorted(sub[col].unique()):
            at = sub[sub[col] == size]
            bl = at[at["method"] == "baseline"]
            il = at[at["method"] == "ILP"]
            if bl.empty or il.empty:
                continue
            rec: Dict[str, Any] = {"sweep": sweep, "size": size, "n_seeds": il["seed"].nunique(),
                                   "baseline_total": bl["total"].mean(), "ilp_total": il["total"].mean()}
            rec["gap_total"] = rec["baseline_total"] - rec["ilp_total"]
            rec["gap_pct_of_baseline"] = 100.0 * rec["gap_total"] / max(1e-9, rec["baseline_total"])
            for comp in COMPONENTS:
                rec[f"gap_{comp}"] = bl[comp].mean() - il[comp].mean()
            rec["baseline_served_share"] = bl["served_share"].mean()
            rec["ilp_served_share"] = il["served_share"].mean()
            rec["baseline_n_unserved"] = bl["n_unserved"].mean()
            rec["ilp_n_unserved"] = il["n_unserved"].mean()
            gap_rows.append(rec)
    if gap_rows:
        gd = pd.DataFrame(gap_rows)
        gd.to_csv(os.path.join(out_dir, "gap_decomposition.csv"), index=False)
        out["gap"] = gd
    heat_base = df[(df["P_kw"] == BASE_P) & df["B_j"].isin(B_SWEEP) & df["C_j"].isin(C_SWEEP)
                   & ~df["sweep"].isin(["free", "free_fixed"])]
    for method in ("ILP", "baseline"):
        heat = heat_base[heat_base["method"] == method]
        if not heat.empty:
            hb = heat.groupby(["B_j", "C_j"])[["total", "operational", "C_orders", "n_unserved", "served_share",
                                               "swap_wait_slots", "stockout_slots", "charger_util_mean"]].mean().reset_index()
            hb["n_seeds"] = heat.groupby(["B_j", "C_j"])["seed"].nunique().values
            hb.to_csv(os.path.join(out_dir, f"summary_heat_{method}.csv"), index=False)
            out[f"heat_{method}"] = hb
    free = df[df["sweep"].isin(["free", "free_fixed"])]
    if not free.empty:
        out["free"] = free
    stm = spares_to_match(df)
    if stm is not None:
        stm.to_csv(os.path.join(out_dir, "spares_to_match.csv"), index=False)
        out["spares"] = stm
    return out


def spares_to_match(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Smallest ``B_j`` on the B sweep (``C_j = BASE_C``, ``P_j = BASE_P``) at which the
    baseline's served share (and, separately, its total cost) reaches the ILP's value at
    the R2.2 default size ``B_j = BASE_B``, per seed; ``None`` in a column means the
    sweep does not reach it (``'> max(B_SWEEP)'``).  The ILP reference is the written
    model with ``rho = 0.5`` (the baseline reports, but does not enforce, (17)-(18))."""
    sub = sweep_rows(df, "B")
    if sub.empty:
        return None
    rows = []
    for seed in sorted(sub["seed"].unique()):
        s = sub[sub["seed"] == seed]
        ref = s[(s["method"] == "ILP") & (s["B_j"] == BASE_B)]
        if ref.empty or pd.isna(ref["total"].iloc[0]):
            continue
        ref_share = float(ref["served_share"].iloc[0])
        ref_total = float(ref["total"].iloc[0])
        ref_resp = float(ref["mean_response_h"].iloc[0])
        bl = s[s["method"] == "baseline"].sort_values("B_j")
        b_share = next((int(b) for b, v in zip(bl["B_j"], bl["served_share"]) if v >= ref_share - 1e-9), None)
        b_total = next((int(b) for b, v in zip(bl["B_j"], bl["total"]) if v <= ref_total + 1e-6), None)
        b_resp = next((int(b) for b, v, sh in zip(bl["B_j"], bl["mean_response_h"], bl["served_share"])
                       if sh >= ref_share - 1e-9 and v <= ref_resp + 1e-9), None)
        rows.append({"seed": seed, "ilp_B": BASE_B, "ilp_served_share": ref_share, "ilp_total": ref_total,
                     "ilp_mean_response_h": ref_resp,
                     "baseline_served_share_at_B3": float(bl[bl["B_j"] == BASE_B]["served_share"].iloc[0]) if (bl["B_j"] == BASE_B).any() else None,
                     "baseline_B_to_match_served_share": b_share,
                     "baseline_B_to_match_served_and_response": b_resp,
                     "baseline_B_to_match_total_cost": b_total,
                     "baseline_served_share_at_max_B": float(bl["served_share"].iloc[-1]),
                     "baseline_total_at_max_B": float(bl["total"].iloc[-1]), "max_B_swept": int(bl["B_j"].max())})
    return pd.DataFrame(rows) if rows else None


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def _style(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontsize=10.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e5e5e2", linewidth=0.8)
    ax.set_axisbelow(True)


def _sweep_figure(summary: pd.DataFrame, col: str, xlabel: str, path: str, title: str) -> str:
    """Three panels: (a) mean total cost (26) in USD with the min-max band over seeds,
    (b) served share, (c) operational cost minus each method's own value at the
    largest size (within-method marginal structure)."""
    fig, (ax, axs, ax2) = plt.subplots(1, 3, figsize=(15.5, 4.4), constrained_layout=True)
    xticks = sorted(summary[col].unique())
    for method in ("baseline", "ILP"):
        m = summary[summary["method"] == method].sort_values(col)
        if m.empty:
            continue
        st = METHOD_STYLE[method]
        ax.fill_between(m[col], m["total_min"], m["total_max"], color=st["color"], alpha=0.13, linewidth=0)
        ax.plot(m[col], m["total_mean"], color=st["color"], linestyle=st["linestyle"], linewidth=2,
                marker="o", markersize=4.5, label=st["label"])
        axs.plot(m[col], 100 * m["served_share_mean"], color=st["color"], linewidth=2, marker="o", markersize=4.5,
                 label=st["label"])
        rel = m["operational_mean"] - float(m["operational_mean"].iloc[-1])
        ax2.plot(m[col], rel, color=st["color"], linestyle=st["linestyle"], linewidth=2, marker="o",
                 markersize=4.5, label=st["label"])
    for a in (ax, axs, ax2):
        a.set_xticks(list(xticks))
        a.set_xticklabels([f"{x:g}" for x in xticks])
    _style(ax, xlabel, "total cost (26), USD per 4 h window", "(a) " + title)
    _style(axs, xlabel, "served orders, %", "(b) service level (seed mean)")
    _style(ax2, xlabel, "USD vs value at the largest size", "(c) operational cost (total - setup) minus its value at the largest size")
    ax2.axhline(0, color="#9a9a96", linewidth=0.8)
    fig.text(0.01, -0.06, "lines = mean over seeds, band = min-max over seeds; usd4h family (6 bikes / 36 orders / H 48), usd_sunk prices",
             fontsize=8, color="#52514e")
    ax.legend(frameon=False, fontsize=8.5)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def make_figures(df: pd.DataFrame, summaries: Dict[str, Any], out_dir: str) -> List[str]:
    """``cost_vs_B``, ``cost_vs_C``, ``cost_vs_P`` and the ``B x C`` heat map (ILP and
    baseline mean total cost, own colour scale each; cells annotated with the cost and
    the number of seeds)."""
    figs: List[str] = []
    if "B" in summaries:
        figs.append(_sweep_figure(summaries["B"], "B_j", f"spare batteries per site B_j  (C_j = {BASE_C}, P_j = {BASE_P:g} kW)",
                                  os.path.join(out_dir, "cost_vs_B.png"), "total cost vs spares per site"))
    if "C" in summaries:
        figs.append(_sweep_figure(summaries["C"], "C_j", f"chargers per site C_j  (B_j = {BASE_B}, P_j = {BASE_P:g} kW)",
                                  os.path.join(out_dir, "cost_vs_C.png"), "total cost vs chargers per site"))
    if "P" in summaries:
        figs.append(_sweep_figure(summaries["P"], "P_kw", f"site power limit P_j, kW  (B_j = {BASE_B}, C_j = {P_SWEEP_C}, p_ch = 0.667 kW)",
                                  os.path.join(out_dir, "cost_vs_P.png"), "total cost vs site power limit"))
    if "heat_ILP" in summaries:
        panels = [("ILP", summaries["heat_ILP"])]
        if "heat_baseline" in summaries:
            panels.append(("baseline", summaries["heat_baseline"]))
        fig, axes = plt.subplots(1, len(panels), figsize=(6.2 * len(panels), 4.6), squeeze=False,
                                 constrained_layout=True)
        for idx, (ax, (method, hb)) in enumerate(zip(axes[0], panels)):
            grid = hb.pivot(index="B_j", columns="C_j", values="total").reindex(index=B_SWEEP, columns=C_SWEEP)
            ns = hb.pivot(index="B_j", columns="C_j", values="n_seeds").reindex(index=B_SWEEP, columns=C_SWEEP)
            vals = grid.values.astype(float)
            flat = pd.Series(vals.ravel()).dropna()
            vmin, vmax = float(flat.min()), float(flat.max())
            im = ax.imshow(vals, cmap="Blues", origin="lower", aspect="auto", vmin=vmin, vmax=vmax)
            ax.set_xticks(range(len(C_SWEEP)))
            ax.set_xticklabels([str(c) for c in C_SWEEP])
            ax.set_yticks(range(len(B_SWEEP)))
            ax.set_yticklabels([str(b) for b in B_SWEEP])
            for i, b in enumerate(B_SWEEP):
                for j, c in enumerate(C_SWEEP):
                    v = grid.loc[b, c]
                    if not (isinstance(v, float) and math.isnan(v)):
                        light = (v - vmin) / max(1e-9, vmax - vmin) < 0.55
                        n_s = ns.loc[b, c]
                        ax.text(j, i, f"{v:.0f}\n({int(n_s)}s)", ha="center", va="center", fontsize=8.5,
                                color="#0b0b0b" if light else "#ffffff")
            ax.set_xlabel("chargers per site C_j")
            if idx == 0:
                ax.set_ylabel("initial spare batteries per site B_j")
            ax.set_title(f"{method}: mean total cost, USD per window ({vmin:.0f}-{vmax:.0f})", loc="left", fontsize=10)
            cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cb.set_label("USD per 4 h window, own scale")
        fig.suptitle(f"B x C grid at P_j = {BASE_P:g} kW; cell = seed mean (number of seeds in brackets)",
                     x=0.01, ha="left", fontsize=11)
        p = os.path.join(out_dir, "heatmap_BxC.png")
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        figs.append(p)
    return figs


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def report(df: pd.DataFrame, out_dir: str, wall: float, time_limit: float, seeds: List[int],
           heat_seeds: List[int], skipped: List[str]) -> None:
    """Summaries, figures and ``RESULTS.md`` (also used by ``--report-only``)."""
    summaries = summarise(df, out_dir)
    figs = make_figures(df, summaries, out_dir)
    write_results_md(df, summaries, figs, out_dir, wall, time_limit, seeds, heat_seeds, skipped)


def write_results_md(df: pd.DataFrame, summaries: Dict[str, Any], figs: List[str], out_dir: str,
                     wall: float, time_limit: float, seeds: List[int], heat_seeds: List[int],
                     skipped: List[str]) -> None:
    """``RESULTS.md``: Chinese summary (from ``SUMMARY_zh.md`` in ``out_dir`` when present),
    setup, sweep tables with marginal values per window and per year, free-size runs,
    spares-to-match, gap decomposition, grid, solver statistics, figures and the
    interpretation (from ``INTERPRETATION.md`` in ``out_dir``)."""
    md: List[str] = ["# E4u -- station sizing under USD (spares B_j, chargers C_j, power P_j), usd4h family", ""]
    zh = os.path.join(out_dir, "SUMMARY_zh.md")
    if os.path.exists(zh):
        md.append(open(zh, encoding="utf-8").read().rstrip())
        md.append("")
    d0 = df.iloc[0]
    md.append(f"Family `usd4h` (DECISIONS R2.2: |K| = {d0['n_bikes']}, |I| = {d0['n_orders']}, H = {d0['H']} slots of 5 min "
              f"(17:00-21:00), L = {d0['L']}, q0 ~ U{{4..7}} = 30-60 %, p_ch = {d0['p_ch_kw']:.3f} kW), 3 co-located sites "
              f"(K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, grid group 8 kW / 6 kW 18-20 h), "
              f"seeds {seeds} on the sweep lines, seeds {heat_seeds} on the off-line B x C cells; cost variant `{d0['cost_variant']}` "
              f"(R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03 $, bB 0.332 $, bC 0.082 $ per site per 4 h). "
              f"Pruning: plan defaults + reachable (lossless on this family, R2 implementation notes). Gurobi Threads {C.THREADS}, "
              f"TimeLimit {time_limit:.0f} s, OutputFlag 0; wall {wall / 60:.1f} min. Baseline = round-2 rules (R2.3). "
              f"Instances are byte-identical across methods and sizes (only B_j, C_j, P_kw change).")
    md.append("")
    md.append("Costs in USD per 4 h window. `total` is (26) including the setup constant (27) `F_j + bB B_j + bC C_j`; "
              "`operational` = total - C_setup. Marginal values = finite differences of the seed-mean cost per *one unit added "
              f"at one site* (network change / 3 sites / step), per window and per year (x {WINDOWS_PER_YEAR:.0f} = 16 h/4 h x 365). "
              "Headline gap = (baseline - ILP) / baseline.")
    if skipped:
        md.append("")
        md.append(f"Runs skipped by the wall budget: {len(skipped)} ({', '.join(skipped[:12])}{' ...' if len(skipped) > 12 else ''}).")
    md.append("")
    free = summaries.get("free")
    if free is not None and not free.empty:
        md.append("## What the coordinator buys: ILP with B_j, C_j free (y_j = 1 fixed) at usd_sunk prices, and the baseline at those sizes")
        md.append("")
        cols = ["seed", "sweep", "method", "status", "total", "operational", "C_setup", "C_orders", "unserved", "response",
                "lateness", "C_elec", "served_share", "n_swaps", "chosen_B", "chosen_C", "sum_B", "sum_C",
                "charger_util_mean", "idle_full_share_mean", "end_full_total", "gap", "runtime_s", "mip_start_accepted"]
        cols = [c for c in cols if c in free.columns]
        md.append(C.markdown_table(free.sort_values(["seed", "sweep", "method"]), cols, 2))
        md.append("")
    for sweep, col, unit in (("B", "B_j", "battery"), ("C", "C_j", "charger"), ("P", "P_kw", "kW")):
        g = summaries.get(sweep)
        if g is None:
            continue
        fixed = ", ".join(f"{k} = {v:g}" for k, v in SWEEP_SPEC[sweep][1].items())
        md.append(f"## Sweep {sweep}: {col} ({fixed}; seed means, min/max over seeds for total)")
        md.append("")
        cols = ["method", col, "n_seeds", "total_mean", "total_min", "total_max", "operational_mean", "C_setup_mean",
                "unserved_mean", "response_mean", "lateness_mean", "C_elec_mean", "C_travel_mean",
                "served_share_mean", "mean_response_h_mean", "max_lateness_h_mean", "n_late_mean", "bike_km_mean",
                "n_swaps_mean", "kwh_purchased_mean", "swap_wait_slots_mean", "stockout_slots_mean",
                "charger_util_mean_mean", "desk_occupancy_mean_mean", "idle_full_share_mean_mean", "peak_kw_group_mean",
                "end_full_total_mean", "marginal_operational_per_unit_window", "marginal_total_per_unit_window",
                "marginal_total_per_unit_year", "runtime_s_mean", "runtime_s_max", "gap_max"]
        cols = [c for c in cols if c in g.columns]
        md.append(C.markdown_table(g, cols, 2))
        md.append("")
        md.append(f"`marginal_*_per_unit_window` at size s = (cost(s) - cost(next s)) per added {unit} at one site per 4 h window "
                  f"(positive = adding the unit saves cost); `*_per_unit_year` = x {WINDOWS_PER_YEAR:.0f}. "
                  "`charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H); `desk_occupancy` = occupancy of the single swap position (22); "
                  "`idle_full_share` = share of slots with an unused full battery; `end_full_total` = sum_j n_jLH, the (18) left-hand side.")
        md.append("")
    stm = summaries.get("spares")
    if stm is not None:
        md.append("## Spares the baseline needs to match the ILP service level (B sweep, C_j = 2, P_j = 4 kW)")
        md.append("")
        md.append(C.markdown_table(stm, None, 3))
        md.append("")
        md.append("Reference = the ILP at the R2.2 default B_j = 3; `baseline_B_to_match_*` = smallest B_j in the sweep at which the "
                  "baseline reaches the ILP's served share / served share and mean response / total cost (`-` = not reached up to B_j = 6).")
        md.append("")
    gd = summaries.get("gap")
    if gd is not None:
        md.append("## Gap decomposition: baseline - ILP by cost component (seed means; gap % of baseline)")
        md.append("")
        cols = ["sweep", "size", "n_seeds", "baseline_total", "ilp_total", "gap_total", "gap_pct_of_baseline", "gap_unserved",
                "gap_response", "gap_lateness", "gap_C_travel", "gap_C_elec", "baseline_served_share", "ilp_served_share",
                "baseline_n_unserved", "ilp_n_unserved"]
        md.append(C.markdown_table(gd, [c for c in cols if c in gd.columns], 2))
        md.append("")
    if "heat_ILP" in summaries:
        md.append(f"## B x C grid (P_j = {BASE_P:g} kW; seed means, `n_seeds` per cell)")
        md.append("")
        md.append("ILP:")
        md.append("")
        md.append(C.markdown_table(summaries["heat_ILP"], None, 2))
        md.append("")
        if "heat_baseline" in summaries:
            md.append("Baseline on the same grid:")
            md.append("")
            md.append(C.markdown_table(summaries["heat_baseline"], None, 2))
            md.append("")
    md.append("## Solver statistics")
    md.append("")
    ilp = df[df["method"] == "ILP"]
    if not ilp.empty:
        md.append(f"- ILP runs: {len(ilp)}; statuses {ilp['status'].value_counts().to_dict()}; arcs "
                  f"{int(ilp['n_arcs'].min()):,}-{int(ilp['n_arcs'].max()):,}; binaries "
                  f"{int(ilp['n_binaries'].min()):,}-{int(ilp['n_binaries'].max()):,}; rows "
                  f"{int(ilp['n_rows'].min()):,}-{int(ilp['n_rows'].max()):,}; solve time mean {ilp['runtime_s'].mean():.1f} s, "
                  f"max {ilp['runtime_s'].max():.1f} s; MIP gap max {ilp['gap'].max():.4f}; arc build mean {ilp['arc_build_s'].mean():.2f} s; "
                  f"model build mean {ilp['model_build_s'].mean():.2f} s; every ILP schedule passes `evaluate.check`: "
                  f"{bool(ilp['check_ok'].all())}; MIP start accepted in {int((ilp['mip_start_accepted'] == True).sum())} "
                  f"of {int(ilp['mip_start_accepted'].notna().sum())} runs with a start; start variants "
                  f"{ilp['mip_start_variant'].value_counts(dropna=False).to_dict()}.")
    bl = df[df["method"] == "baseline"]
    if not bl.empty:
        md.append(f"- baseline: {len(bl)} runs, reported families {sorted(set(bl['reported_families']))} (only the report-only "
                  f"families (9), (17), (18) may appear); identity (24) holds on all schedules: {bool(df['identity_24_ok'].all())}; "
                  f"ILP <= baseline on every variant: {bool(_ilp_le_baseline(df))}.")
    md.append("")
    md.append("## Figures")
    md.append("")
    for f in figs:
        md.append(f"- `{os.path.basename(f)}`")
    md.append("")
    md.append("## Interpretation and anomalies")
    md.append("")
    interp = os.path.join(out_dir, "INTERPRETATION.md")
    if os.path.exists(interp):
        md.append(open(interp, encoding="utf-8").read().rstrip())
    else:
        md.append("(not written yet: put the text in INTERPRETATION.md next to this file and re-run with --report-only)")
    with open(os.path.join(out_dir, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")


def _ilp_le_baseline(df: pd.DataFrame) -> bool:
    ok = True
    for (_seed, _tag), g in df.groupby(["seed", "tag"]):
        i = g[g["method"] == "ILP"]["total"]
        b = g[g["method"] == "baseline"]["total"]
        if len(i) and len(b) and not (float(i.iloc[0]) <= float(b.iloc[0]) + 1e-6):
            ok = False
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    ap.add_argument("--heat-seeds", nargs="*", type=int, default=HEAT_SEEDS)
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--wall-budget-min", type=float, default=58.0)
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--probe", action="store_true", help="B1/C1 and the default size on the first seed only")
    ap.add_argument("--no-free", action="store_true", help="skip the free-size ILP")
    ap.add_argument("--report-only", action="store_true",
                    help="rebuild summaries, figures and RESULTS.md from <out-dir>/results.csv without solving")
    args = ap.parse_args()
    if args.report_only:
        frame = pd.read_csv(os.path.join(args.out_dir, "results.csv"))
        meta_path = os.path.join(args.out_dir, "run_meta.json")
        meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
        report(frame, args.out_dir, meta.get("wall_s", float("nan")), meta.get("time_limit", args.time_limit),
               meta.get("seeds", args.seeds), meta.get("heat_seeds", args.heat_seeds), meta.get("skipped", []))
    else:
        main(args.seeds, args.time_limit, args.heat_seeds, args.out_dir, args.probe, not args.no_free,
             args.wall_budget_min)
