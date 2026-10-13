"""Experiment E4 -- station sizing sensitivity: spare batteries, chargers, power.

Question (``plan.experiments[3]``): how do cost and service respond to the per-site
initial spare stock ``B_j`` (16), the number of chargers ``C_j`` (20) and the site
input-power limit ``P_j`` (20), and what is the marginal value of one battery /
one charger / one kW?  Co-located sites (``S = C = N``, 3 sites), several seeds,
byte-identical demand for every method and size.

Runs per seed (all on the SAME generated instance; only the facility fields
``B``, ``C``, ``P_kw`` (and ``rho`` for the rho = 0 control) are changed, so the
arc library (1)-(4), (9) is identical up to object identity and is rebuilt per
variant):

* one-at-a-time sweeps ``B_j in B_SWEEP`` (``C_j``, ``P_j`` at the generator
  defaults 3 / 4 kW), ``C_j in C_SWEEP`` (``C_j <= min(Cbar_j, K_j)``), ``P_j in
  P_SWEEP`` kW (multiples of ``p_ch = eps / (eta Delta)`` (19) = 0.667 kW, so
  ``floor(P_j / p_ch)`` = 1, 2, 3, 4 simultaneous chargers);
* a ``B x C`` grid (``HEAT_B x HEAT_C``) at the default power;
* the ILP with ``B_j``, ``C_j`` free and ``y_j = 1`` fixed under the horizon-allocated
  setup costs (27) ``bB = 3``, ``bC = 2`` carried by the instance (``fixed_facilities``
  keeps ``y`` fixed because only ``y`` is given);
* the fixed-size ILP and the baseline at the sizes the free run chose;
* a control ILP with ``rho = 0`` (end target (18) off) on the ``B`` sweep, because the
  baseline never enforces (18) (DECISIONS.md: reported, not enforced) and the
  requirement ``sum_j n_jLH >= rho sum_j B_j`` grows with ``B_j``.

Methods: the E2 ILP (5)-(22), (26)-(32) via :func:`experiments.common.run_ilp_case`
(Gurobi ``OutputFlag 0``, ``Threads 4``, time limit) with the baseline schedule as
MIP start, and the event-driven baseline (``plan.baseline_policy_spec``; transfers
``NONE``, there are no services on the co-located layout) at the same sizes.

Reported per run (``outputs/e4_sizing/results.csv``, one row per variant x method):
total cost (26) and components (27)-(32), operational cost ``total - C_setup``,
``C_orders`` split, ``C_elec``, unserved / response / lateness, swap-wait slots
(wait arcs at the swap node immediately before a swap), stock-out slots per site
(``n_jLt = 0``) and stock-out slots with a queued bike, charger utilisation
``sum_t sum_q c_jqt / (C_j H)``, swap-desk occupancy ``sum_{swap arcs} sigma_j /
(M_j H)``, idle-full-stock share (slots with a full battery left unused:
``n_jLt - S_jt - D_jLt >= 1``), grid-group peak kW (21), solver statistics, the
chosen ``B_j``, ``C_j`` of the free run.  ``summary_*.csv`` hold the per-size means
over seeds and the finite-difference marginal values ``(cost(s) - cost(s'))`` per
added battery / charger / kW (operational and total cost);
``gap_decomposition.csv`` splits baseline - ILP into the (27)-(32) components.
Figures: ``cost_vs_B.png``, ``cost_vs_C.png``, ``cost_vs_P.png``, ``heatmap_BxC.png``.

Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/e4_sizing.py [--seeds 0 1 2] [--time-limit 120] [--probe]
    PYTHONPATH=. python3 experiments/e4_sizing.py --report-only   # tables / figures / RESULTS.md from results.csv
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from experiments import common as C  # noqa: E402
from ebike_swap_sim import (  # noqa: E402
    ArcLibrary, Instance, Schedule, facility_vars, reconstruct_inventory, swap_counts,
    transfer_counts,
)

plt = C.plt

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e4_sizing")
FAMILY = "large"                       # 10 bikes / 30 orders / H 24 / L 12 (integration: optimal in 15 s)
SEEDS = [0, 1, 2]
TIME_LIMIT = 120.0
B_SWEEP = [1, 2, 3, 4, 6]
C_SWEEP = [1, 2, 3, 4]
P_SWEEP = [0.7, 1.4, 2.1, 2.8]
HEAT_B = [2, 4, 6]
HEAT_C = [1, 2, 3]
BASE_B, BASE_C, BASE_P = 4, 3, 4.0     # generator defaults (DEFAULT_FACILITIES_SPEC)
RHO0_SWEEPS = ("B",)                   # sweeps on which the rho = 0 control ILP is also solved
N_SITES = 3

COLOR_ILP = "#2a78d6"                  # categorical slot 1 (blue)
COLOR_BASE = "#eb6834"                 # categorical slot 2 (orange)
COLOR_RHO0 = "#1b9e77"                 # categorical slot 3 (green)
METHOD_STYLE = {
    "ILP": dict(color=COLOR_ILP, linestyle="-", label="ILP (rho = 0.5, written model)"),
    "ILP_rho0": dict(color=COLOR_RHO0, linestyle="--", label="ILP with rho = 0 (end target (18) off)"),
    "baseline": dict(color=COLOR_BASE, linestyle="-", label="baseline policy"),
}
COMPONENTS = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"]


# ---------------------------------------------------------------------------
# instance variants
# ---------------------------------------------------------------------------
def sized_instance(base: Instance, B: Optional[Any] = None, C_: Optional[Any] = None,
                   P: Optional[float] = None, free: bool = False, tag: str = "",
                   rho: Optional[float] = None) -> Instance:
    """Deep copy of ``base`` with the facility fields of every site changed.

    ``B`` / ``C_`` are an int for all sites or a ``{fac_id: value}`` dict; ``P`` is
    the site input-power limit ``P_j`` in kW of (20).  ``free=True`` sets ``B_j`` and
    ``C_j`` to ``None`` (decided by the ILP under (7)-(8) and the setup costs (27))
    while ``y_j`` stays fixed.  ``rho`` overrides the network recovery share of
    (18).  The copy passes ``validate()``; ``meta['variant']`` records the sizes.
    Nothing else (orders, bikes, routes, prices) changes.
    """
    inst = copy.deepcopy(base)
    for f in inst.facilities:
        if free:
            f.B, f.C = None, None
        else:
            if B is not None:
                f.B = int(B[f.id] if isinstance(B, dict) else B)
            if C_ is not None:
                f.C = int(C_[f.id] if isinstance(C_, dict) else C_)
        if P is not None:
            f.P_kw = float(P)
    if rho is not None:
        inst.rho = float(rho)
    inst.reindex()
    inst.validate()
    inst.meta["variant"] = {"tag": tag, "B": _site_map(inst, "B"), "C": _site_map(inst, "C"),
                            "P_kw": _site_map(inst, "P_kw"), "free": free, "rho": inst.rho}
    return inst


def _site_map(inst: Instance, attr: str) -> Dict[str, Any]:
    return {str(f.id): getattr(f, attr) for f in inst.facilities}


def _uniform(d: Dict[str, Any]) -> Any:
    vals = list(d.values())
    return vals[0] if vals and all(v == vals[0] for v in vals) else None


# ---------------------------------------------------------------------------
# per-site metrics
# ---------------------------------------------------------------------------
def site_metrics(inst: Instance, lib: ArcLibrary, sched: Schedule) -> Dict[str, Any]:
    """Station-level diagnostics of a schedule (plan E4 metrics).

    * ``swap_wait_slots[j]``: wait arcs at ``v_j`` immediately preceding a swap at
      ``j`` (queue proxy, same definition for ILP and baseline);
    * ``stockout_slots[j]``: slots ``t in T`` with ``n_jLt = 0`` (13);
    * ``stockout_queue_slots[j]``: those slots in which at least one bike is waiting
      for a swap at ``j``;
    * ``charger_util[j]``: ``sum_t sum_q c_jqt / (C_j H)`` (20), ``None`` if ``C_j = 0``;
    * ``desk_occupancy[j]``: ``sum_{swap arcs at j} (u_a - l_a) / (M_j H)`` (22);
    * ``idle_full_share[j]``: share of slots with ``n_jLt - S_jt - D_jLt >= 1``, i.e. a
      full battery that stays unused in that slot ((12), (11), (14));
    * ``swaps[j]``, ``charge_steps[j]``, ``peak_kw[j]`` and ``peak_kw_group``.
    """
    H, L = inst.H, inst.L
    y, B, Cv = facility_vars(inst, sched)
    n = sched.n if sched.n is not None else reconstruct_inventory(
        inst, lib, {k: list(v) for k, v in sched.x.items()}, sched.c, sched.z, B)
    s, S = swap_counts(inst, lib, sched.x)
    D, _A = transfer_counts(inst, sched.z)
    wait = {j: 0 for j in inst.S}
    swaps = {j: 0 for j in inst.S}
    desk = {j: 0 for j in inst.S}
    queue_len: Dict[Any, Dict[int, int]] = {j: defaultdict(int) for j in inst.S}
    for b in inst.bikes:
        run: List[int] = []
        for a in sched.path(b.id, lib):
            if a.kind == "wait":
                run.append(a.l)
            elif a.kind == "swap":
                wait[a.fac] += len(run)
                for t in run:
                    queue_len[a.fac][t] += 1
                swaps[a.fac] += 1
                desk[a.fac] += a.u - a.l
                run = []
            else:
                run = []
    out: Dict[str, Any] = {
        "swap_wait_slots": wait, "swaps": swaps,
        "stockout_slots": {}, "stockout_queue_slots": {}, "charger_util": {},
        "desk_occupancy": {}, "idle_full_share": {}, "charge_steps": {}, "peak_kw": {},
    }
    group_load: Dict[Tuple[Any, int], float] = defaultdict(float)
    for f in inst.facilities:
        j = f.id
        full = [n.get((j, L, t), 0) for t in range(H + 1)]
        if f.swap:
            out["stockout_slots"][j] = sum(1 for t in range(H) if full[t] == 0)
            out["stockout_queue_slots"][j] = sum(
                1 for t in range(H) if full[t] == 0 and queue_len[j].get(t, 0) > 0)
            out["desk_occupancy"][j] = desk[j] / (f.M * H)
        idle = sum(1 for t in range(H)
                   if full[t] - S.get((j, t), 0) - D.get((j, L, t), 0) >= 1)
        out["idle_full_share"][j] = idle / H
        if f.charge:
            per_t = [sum(sched.c.get((j, q, t), 0) for q in range(L)) for t in range(H)]
            steps = sum(per_t)
            out["charge_steps"][j] = steps
            out["charger_util"][j] = (steps / (Cv[j] * H)) if Cv[j] > 0 else None
            out["peak_kw"][j] = inst.disc.p_ch_kw * max(per_t) if per_t else 0.0
            if f.group is not None:
                for t in range(H):
                    group_load[(f.group, t)] += inst.disc.p_ch_kw * per_t[t]
    peak_group: Dict[Any, float] = defaultdict(float)
    for (g, t), load in group_load.items():
        peak_group[g] = max(peak_group[g], load)
    out["peak_kw_group"] = dict(peak_group)
    return out


def _mean(vals: Sequence[Optional[float]]) -> Optional[float]:
    xs = [float(v) for v in vals if v is not None]
    return sum(xs) / len(xs) if xs else None


# ---------------------------------------------------------------------------
# one variant
# ---------------------------------------------------------------------------
def run_variant(inst: Instance, sweep: str, time_limit: float, free: bool = False,
                run_baseline: bool = True, rho0: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Baseline + ILP on one sized instance; returns ``(rows, extras)``.

    ``rows`` are the flat CSV records, ``method`` = ``baseline`` / ``ILP_rho0`` / ``ILP``:

    1. the baseline policy (identical for every ``rho``: it reports (18), it does
       not enforce it);
    2. with ``rho0``, the ILP on the same instance with ``rho = 0`` ((18) off),
       MIP start = baseline (accepted whenever (18) is the only reported family);
    3. the written model (``rho`` of the instance), MIP start = the ``ILP_rho0``
       schedule when one exists (warm-start chain; accepted when it happens to meet
       (18)), otherwise the baseline.  ``mip_start_from`` records the source.

    ``extras`` carries the ILP's chosen ``B``/``C`` per site (free run).
    """
    lib, t_build = C.build_library(inst, C.pruning_for(inst))
    var = inst.meta["variant"]
    common = {
        "seed": inst.meta.get("seed"), "family": inst.meta.get("family"), "sweep": sweep,
        "tag": var["tag"], "free_sizes": free, "rho": inst.rho,
        "B_j": _uniform(var["B"]), "C_j": _uniform(var["C"]), "P_kw": _uniform(var["P_kw"]),
        "B_sites": json.dumps(var["B"]), "C_sites": json.dumps(var["C"]),
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
        "q0_mean": sum(b.q0 for b in inst.bikes) / len(inst.bikes),
        "p_ch_kw": inst.disc.p_ch_kw, "n_arcs": len(lib), "arc_build_s": t_build,
    }
    rows: List[Dict[str, Any]] = []
    base = None
    start: Optional[Schedule] = None
    start_from = None
    if run_baseline and not free:
        base = C.run_baseline_case(inst, lib)
        rows.append({**common, "method": "baseline", "mip_start_from": None,
                     **_schedule_row(inst, lib, base, base["schedule"])})
        start, start_from = base["schedule"], "baseline"
    if rho0 and not free:
        inst0 = copy.deepcopy(inst)
        inst0.rho = 0.0
        inst0.meta["variant"]["rho"] = 0.0
        lib0, _ = C.build_library(inst0, C.pruning_for(inst0))
        ilp0 = C.run_ilp_case(inst0, lib0, mip_start=start, time_limit=time_limit, threads=C.THREADS,
                              label="ilp_rho0")
        rows.append({**common, "rho": 0.0, "method": "ILP_rho0", "mip_start_from": start_from,
                     **_schedule_row(inst0, lib0, ilp0, ilp0["schedule"])})
        if ilp0["schedule"] is not None:
            start, start_from = ilp0["schedule"], "ILP_rho0"
    ilp = C.run_ilp_case(inst, lib, mip_start=start, time_limit=time_limit, threads=C.THREADS, label="ilp")
    rows.append({**common, "method": "ILP", "mip_start_from": start_from,
                 **_schedule_row(inst, lib, ilp, ilp["schedule"])})
    extras: Dict[str, Any] = {}
    if ilp["schedule"] is not None:
        _y, Bc, Cc = facility_vars(inst, ilp["schedule"])
        extras = {"B": {str(j): v for j, v in Bc.items()}, "C": {str(j): v for j, v in Cc.items()}}
    return rows, extras


def _schedule_row(inst: Instance, lib: ArcLibrary, rec: Dict[str, Any],
                  sched: Optional[Schedule]) -> Dict[str, Any]:
    """Flatten a :func:`common.run_*_case` record plus :func:`site_metrics`."""
    row: Dict[str, Any] = {
        "status": rec.get("status", "-"), "gap": rec.get("gap"), "bound": rec.get("bound"),
        "runtime_s": rec.get("runtime"), "model_build_s": rec.get("build_time"),
        "n_binaries": rec.get("n_binaries"), "n_rows": rec.get("n_rows"),
        "mip_start_accepted": rec.get("mip_start_accepted"),
        "check_ok": rec.get("ok"), "identity_24_ok": rec.get("identity_24_ok"),
        "reported_families": json.dumps(rec.get("families", {})),
    }
    if sched is None or rec.get("cost") is None:
        row.update(total=None)
        return row
    c = rec["cost"]
    row.update(C.flatten_cost(c))
    row["operational"] = c["total"] - c["C_setup"]
    m = rec["metrics"]
    row.update({
        "n_unserved": m["n_unserved"], "served_share": m["served_share"],
        "mean_response_h": m["mean_response_h"], "n_late": m["n_late"],
        "mean_lateness_h": m["mean_lateness_h"], "bike_km": m["bike_km"],
        "n_swaps": m["n_swaps"], "kwh_purchased": m["kwh_purchased"],
        "end_full_total": m["end_full_total"], "end_target_shortfall": m["end_target_shortfall"],
    })
    sm = site_metrics(inst, lib, sched)
    row.update({
        "swap_wait_slots": sum(sm["swap_wait_slots"].values()),
        "swap_wait_sites": json.dumps({str(k): v for k, v in sm["swap_wait_slots"].items()}),
        "stockout_slots": sum(sm["stockout_slots"].values()),
        "stockout_sites": json.dumps({str(k): v for k, v in sm["stockout_slots"].items()}),
        "stockout_queue_slots": sum(sm["stockout_queue_slots"].values()),
        "stockout_queue_sites": json.dumps({str(k): v for k, v in sm["stockout_queue_slots"].items()}),
        "charger_util_mean": _mean(list(sm["charger_util"].values())),
        "charger_util_sites": json.dumps({str(k): v for k, v in sm["charger_util"].items()}),
        "desk_occupancy_mean": _mean(list(sm["desk_occupancy"].values())),
        "desk_occupancy_sites": json.dumps({str(k): v for k, v in sm["desk_occupancy"].items()}),
        "idle_full_share_mean": _mean(list(sm["idle_full_share"].values())),
        "idle_full_share_sites": json.dumps({str(k): v for k, v in sm["idle_full_share"].items()}),
        "peak_kw_group": max(sm["peak_kw_group"].values()) if sm["peak_kw_group"] else 0.0,
        "swaps_sites": json.dumps({str(k): v for k, v in sm["swaps"].items()}),
    })
    y_, B_, C_ = facility_vars(inst, sched)
    row["chosen_B"] = json.dumps({str(j): v for j, v in B_.items()})
    row["chosen_C"] = json.dumps({str(j): v for j, v in C_.items()})
    row["sum_B"] = sum(B_.values())
    row["sum_C"] = sum(C_.values())
    return row


# ---------------------------------------------------------------------------
# the experiment
# ---------------------------------------------------------------------------
ALL_SWEEPS = ("B", "C", "P", "heat", "free")


def variant_plan(sweeps: Sequence[str] = ALL_SWEEPS) -> List[Tuple[str, int, int, float]]:
    """Ordered, de-duplicated list of ``(sweep, B, C, P)`` fixed-size variants of the
    requested ``sweeps`` (``'free'`` is handled by :func:`main`).  A variant that
    belongs to several sweeps is run once; :func:`summarise` re-attaches it to every
    sweep by its sizes."""
    plan: List[Tuple[str, int, int, float]] = []
    seen = set()

    def add(sweep: str, B: int, C_: int, P: float) -> None:
        key = (B, C_, P)
        if key not in seen:
            seen.add(key)
            plan.append((sweep, B, C_, P))

    if "B" in sweeps:
        for B in B_SWEEP:
            add("B", B, BASE_C, BASE_P)
    if "C" in sweeps:
        for C_ in C_SWEEP:
            add("C", BASE_B, C_, BASE_P)
    if "P" in sweeps:
        for P in P_SWEEP:
            add("P", BASE_B, BASE_C, P)
    if "heat" in sweeps:
        for B in HEAT_B:
            for C_ in HEAT_C:
                add("heat", B, C_, BASE_P)
    return plan


def main(seeds: Sequence[int] = SEEDS, time_limit: float = TIME_LIMIT, heatmap: bool = True,
         family: str = FAMILY, out_dir: str = OUT_DIR, probe: bool = False,
         sweeps: Sequence[str] = ALL_SWEEPS, init_frac: Optional[Sequence[float]] = None,
         rho0: bool = True) -> List[Dict[str, Any]]:
    """Run E4 and write ``results.csv``, ``summary_*.csv``, figures and ``RESULTS.md``.

    ``init_frac = (lo, hi)`` overrides the generator's initial-charge range
    ``q0 ~ U{ceil(lo L), ..., hi L}`` (default 0.4-1.0; the bikes are drawn after the
    orders, so the demand stays byte-identical) for a swap-stressed supplement."""
    C.ensure_dir(out_dir)
    t_start = time.perf_counter()
    rows: List[Dict[str, Any]] = []
    sweeps = [s for s in sweeps if heatmap or s != "heat"]
    plan = variant_plan(sweeps)
    if probe:   # hardest fixed variants + the free run on the first seed only
        plan = [("B", 1, BASE_C, BASE_P), ("C", BASE_B, 1, BASE_P), ("P", BASE_B, BASE_C, 0.7),
                ("B", BASE_B, BASE_C, BASE_P)]
        seeds = list(seeds)[:1]
    overrides: Dict[str, Any] = {}
    if init_frac is not None:
        overrides["demand_spec"] = {"init_frac": (float(init_frac[0]), float(init_frac[1]))}
    free_choice: Dict[int, Dict[str, Any]] = {}
    for seed in seeds:
        base = C.make_instance(family, seed=seed, **overrides)
        for sweep, B, C_, P in plan:
            inst = sized_instance(base, B=B, C_=C_, P=P, tag=f"B{B}_C{C_}_P{P:g}")
            # rho = 0 control + warm-start chain on the B sweep (where (18) scales with B)
            # and on the one-charger variants (where the baseline start is rejected and
            # Gurobi's own heuristics were seen to fail within the time limit)
            vrows, _ = run_variant(inst, sweep, time_limit, rho0=rho0 and (sweep in RHO0_SWEEPS or C_ == 1))
            rows.extend(vrows)
            _log(vrows, t_start)
            C.write_csv(rows, os.path.join(out_dir, "results.csv"))     # incremental checkpoint
        if "free" in sweeps:
            # ILP with B_j, C_j free (y fixed) under the setup costs bB = 3, bC = 2 of the instance
            inst_free = sized_instance(base, P=BASE_P, free=True, tag="free")
            frows, extras = run_variant(inst_free, "free", time_limit, free=True, run_baseline=False)
            rows.extend(frows)
            _log(frows, t_start)
            if extras:
                free_choice[seed] = extras
                inst_fix = sized_instance(base, B=extras["B"], C_=extras["C"], P=BASE_P, tag="free_fixed")
                xrows, _ = run_variant(inst_fix, "free_fixed", time_limit, rho0=rho0)
                rows.extend(xrows)
                _log(xrows, t_start)
    df = C.write_csv(rows, os.path.join(out_dir, "results.csv"))
    wall = time.perf_counter() - t_start
    with open(os.path.join(out_dir, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"seeds": list(seeds), "time_limit": time_limit, "family": family, "wall_s": wall,
                   "heatmap": heatmap, "probe": probe, "sweeps": list(sweeps), "init_frac": init_frac,
                   "free_choice": free_choice}, fh, indent=1)
    report(df, out_dir, wall, time_limit, list(seeds), family, heatmap)
    print(f"done: {len(rows)} rows in {wall / 60:.1f} min -> {out_dir}")
    return rows


def report(df: pd.DataFrame, out_dir: str, wall: float, time_limit: float, seeds: List[int],
           family: str, heatmap: bool = True) -> None:
    """Summaries, figures and ``RESULTS.md`` from a results frame (also used by ``--report-only``)."""
    summaries = summarise(df, out_dir)
    figs = make_figures(df, summaries, out_dir, heatmap)
    write_results_md(df, summaries, figs, out_dir, wall, time_limit, seeds, family)


def _log(rows: List[Dict[str, Any]], t_start: float) -> None:
    for r in rows:
        print(f"[{(time.perf_counter() - t_start) / 60:5.1f} min] seed {r['seed']} {r['sweep']:>10} "
              f"{r['tag']:<14} {r['method']:>8} status {r['status']:<10} total {C.fmt(r.get('total'))} "
              f"op {C.fmt(r.get('operational'))} unserved {r.get('n_unserved')} gap {C.fmt(r.get('gap'), 4)} "
              f"t {C.fmt(r.get('runtime_s'), 1)} s start {r.get('mip_start_accepted')}", flush=True)


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
AGG_COLS = ["total", "operational", "C_setup", "C_elec", "C_travel", "C_orders", "unserved", "response",
            "lateness", "n_unserved", "swap_wait_slots", "stockout_slots", "stockout_queue_slots",
            "charger_util_mean", "desk_occupancy_mean", "idle_full_share_mean", "peak_kw_group",
            "n_swaps", "kwh_purchased", "end_full_total", "runtime_s", "gap"]
SWEEP_SPEC = {"B": ("B_j", {"C_j": BASE_C, "P_kw": BASE_P}),
              "C": ("C_j", {"B_j": BASE_B, "P_kw": BASE_P}),
              "P": ("P_kw", {"B_j": BASE_B, "C_j": BASE_C})}


def sweep_rows(df: pd.DataFrame, sweep: str) -> pd.DataFrame:
    """Rows of ``df`` that lie on the one-at-a-time line of ``sweep`` (whatever
    sweep label they were run under; the free-size runs are excluded)."""
    col, fixed = SWEEP_SPEC[sweep]
    sub = df[~df["sweep"].isin(["free", "free_fixed"])]
    for k, v in fixed.items():
        sub = sub[sub[k] == v]
    return sub[sub[col].notna()]


def summarise(df: pd.DataFrame, out_dir: str) -> Dict[str, Any]:
    """Per-size means over seeds for each sweep and method, finite-difference
    marginal values (operational and total cost per added battery / charger / kW:
    network-wide change divided by the number of sites and the step), the ``B x C``
    grid means and the baseline-vs-ILP gap decomposition by (27)-(32) component.
    Writes ``summary_<sweep>.csv``, ``summary_heat_*.csv`` and ``gap_decomposition.csv``."""
    out: Dict[str, Any] = {}
    gap_rows: List[Dict[str, Any]] = []
    for sweep, (col, _fixed) in SWEEP_SPEC.items():
        sub = sweep_rows(df, sweep)
        if sub.empty or sub[col].nunique() < 2:      # sweep not run (e.g. --sweeps B C)
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
                g.loc[m.index, f"marginal_{cost_col}_per_unit"] = mv
        g.to_csv(os.path.join(out_dir, f"summary_{sweep}.csv"), index=False)
        out[sweep] = g
        # gap decomposition: baseline - ILP (and - ILP_rho0) per size, by component
        for size in sorted(sub[col].unique()):
            at = sub[sub[col] == size]
            bl = at[at["method"] == "baseline"]
            for ilp_method in ("ILP", "ILP_rho0"):
                il = at[at["method"] == ilp_method]
                if bl.empty or il.empty:
                    continue
                rec: Dict[str, Any] = {"sweep": sweep, "size": size, "vs": ilp_method,
                                       "baseline_total": bl["total"].mean(), "ilp_total": il["total"].mean()}
                rec["gap_total"] = rec["baseline_total"] - rec["ilp_total"]
                rec["gap_pct"] = 100.0 * rec["gap_total"] / max(1e-9, rec["ilp_total"])
                for comp in COMPONENTS:
                    rec[f"gap_{comp}"] = bl[comp].mean() - il[comp].mean()
                rec["unserved_share_of_gap"] = (rec["gap_unserved"] / rec["gap_total"]) if abs(rec["gap_total"]) > 1e-9 else None
                rec["baseline_n_unserved"] = bl["n_unserved"].mean()
                rec["ilp_n_unserved"] = il["n_unserved"].mean()
                gap_rows.append(rec)
    if gap_rows:
        gd = pd.DataFrame(gap_rows)
        gd.to_csv(os.path.join(out_dir, "gap_decomposition.csv"), index=False)
        out["gap"] = gd
    heat_base = df[(df["P_kw"] == BASE_P) & df["B_j"].isin(HEAT_B) & df["C_j"].isin(HEAT_C)
                   & ~df["sweep"].isin(["free", "free_fixed"])]
    for method in ("ILP", "baseline"):
        heat = heat_base[heat_base["method"] == method]
        if not heat.empty:
            hb = heat.groupby(["B_j", "C_j"])[["total", "operational", "C_orders", "n_unserved", "swap_wait_slots",
                                               "stockout_slots", "charger_util_mean"]].mean().reset_index()
            hb.to_csv(os.path.join(out_dir, f"summary_heat_{method}.csv"), index=False)
            out[f"heat_{method}"] = hb
    free = df[df["sweep"].isin(["free", "free_fixed"])]
    if not free.empty:
        out["free"] = free
    return out


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


def _range_text(summary: pd.DataFrame, col: str) -> str:
    """``'ILP a -> b, baseline c -> d'`` of the mean total cost from the smallest to the largest size."""
    parts = []
    for method in ("ILP", "baseline"):
        m = summary[summary["method"] == method].sort_values(col)
        if len(m) >= 2:
            parts.append(f"{method} {m['total_mean'].iloc[0]:.0f} -> {m['total_mean'].iloc[-1]:.0f}")
    return ", ".join(parts)


def _sweep_figure(summary: pd.DataFrame, col: str, xlabel: str, path: str, title: str,
                  xticks: Optional[Sequence[float]] = None) -> str:
    """Two panels: (a) mean total cost (26) with the min-max band over seeds;
    (b) operational cost (total - setup) minus each method's own value at the
    largest size, so that the within-method marginal structure is visible even
    though the baseline costs about twice the ILP."""
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.4), constrained_layout=True)
    xticks = sorted(summary[col].unique())
    for method in ("baseline", "ILP", "ILP_rho0"):
        m = summary[summary["method"] == method].sort_values(col)
        if m.empty:
            continue
        st = METHOD_STYLE[method]
        ax.fill_between(m[col], m["total_min"], m["total_max"], color=st["color"], alpha=0.13, linewidth=0)
        ax.plot(m[col], m["total_mean"], color=st["color"], linestyle=st["linestyle"], linewidth=2,
                marker="o", markersize=4.5, label=st["label"])
        rel = m["operational_mean"] - float(m["operational_mean"].iloc[-1])
        ax2.plot(m[col], rel, color=st["color"], linestyle=st["linestyle"], linewidth=2, marker="o",
                 markersize=4.5, label=st["label"])
    for a in (ax, ax2):
        a.set_xticks(list(xticks))
        a.set_xticklabels([f"{x:g}" for x in xticks])
    head, _, ranges = title.partition(": ")
    _style(ax, xlabel, "total cost (26), toy units", "(a) " + head)
    _style(ax2, xlabel, "operational cost minus its value at the largest size",
           "(b) operational cost (total - setup) vs largest size")
    ax2.axhline(0, color="#9a9a96", linewidth=0.8)
    fig.text(0.01, -0.06, "lines = mean over seeds, bands = min-max over seeds; smallest -> largest size: " + ranges,
             fontsize=8, color="#52514e")
    ax.legend(frameon=False, fontsize=8.5)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def make_figures(df: pd.DataFrame, summaries: Dict[str, Any], out_dir: str, heatmap: bool) -> List[str]:
    """``cost_vs_B``, ``cost_vs_C``, ``cost_vs_P`` (baseline, ILP and the rho = 0 ILP
    where available; mean with min-max band over seeds) and the ``B x C`` heat map
    of the ILP mean total cost with the baseline's grid alongside."""
    figs: List[str] = []
    if "B" in summaries:
        s = summaries["B"]
        figs.append(_sweep_figure(s, "B_j", "spare batteries per site B_j  (C_j = %d, P_j = %g kW)" % (BASE_C, BASE_P),
                                  os.path.join(out_dir, "cost_vs_B.png"),
                                  "Total cost vs spares per site: " + _range_text(s, "B_j")))
    if "C" in summaries:
        s = summaries["C"]
        figs.append(_sweep_figure(s, "C_j", "chargers per site C_j  (B_j = %d, P_j = %g kW)" % (BASE_B, BASE_P),
                                  os.path.join(out_dir, "cost_vs_C.png"),
                                  "Total cost vs chargers per site: " + _range_text(s, "C_j")))
    if "P" in summaries:
        s = summaries["P"]
        figs.append(_sweep_figure(s, "P_kw", "site power limit P_j in kW  (B_j = %d, C_j = %d, p_ch = 0.667 kW)" % (BASE_B, BASE_C),
                                  os.path.join(out_dir, "cost_vs_P.png"),
                                  "Total cost vs site power limit: " + _range_text(s, "P_kw")))
    if heatmap and "heat_ILP" in summaries:
        panels = [("ILP", summaries["heat_ILP"])]
        if "heat_baseline" in summaries:
            panels.append(("baseline", summaries["heat_baseline"]))
        fig, axes = plt.subplots(1, len(panels), figsize=(5.8 * len(panels), 4.3), squeeze=False,
                                 constrained_layout=True)
        for idx, (ax, (method, hb)) in enumerate(zip(axes[0], panels)):
            grid = hb.pivot(index="B_j", columns="C_j", values="total").reindex(index=HEAT_B, columns=HEAT_C)
            vals = grid.values.astype(float)
            vmin, vmax = float(pd.Series(vals.ravel()).min()), float(pd.Series(vals.ravel()).max())
            im = ax.imshow(vals, cmap="Blues", origin="lower", aspect="auto", vmin=vmin, vmax=vmax)
            ax.set_xticks(range(len(HEAT_C)))
            ax.set_xticklabels([str(c) for c in HEAT_C])
            ax.set_yticks(range(len(HEAT_B)))
            ax.set_yticklabels([str(b) for b in HEAT_B])
            for i, b in enumerate(HEAT_B):
                for j, c in enumerate(HEAT_C):
                    v = grid.loc[b, c]
                    if not (isinstance(v, float) and math.isnan(v)):
                        light = (v - vmin) / max(1e-9, vmax - vmin) < 0.55
                        ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=10,
                                color="#0b0b0b" if light else "#ffffff")
            ax.set_xlabel("chargers per site C_j")
            if idx == 0:
                ax.set_ylabel("initial spare batteries per site B_j")
            ax.set_title(f"{method}: mean total cost (26), range {vmin:.1f}-{vmax:.1f}", loc="left", fontsize=10)
            cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cb.set_label("total cost (toy units), own scale")
        fig.suptitle(f"B x C grid at P_j = {BASE_P:g} kW, seed means (each panel has its own colour scale)",
                     x=0.01, ha="left", fontsize=11)
        p = os.path.join(out_dir, "heatmap_BxC.png")
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        figs.append(p)
    return figs


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def write_results_md(df: pd.DataFrame, summaries: Dict[str, Any], figs: List[str], out_dir: str,
                     wall: float, time_limit: float, seeds: List[int], family: str) -> None:
    """``RESULTS.md``: setup, headline comparison statement, sweep tables with marginal
    values, gap decomposition, grid, free-size runs, solver statistics, figures and the
    interpretation (embedded from ``INTERPRETATION.md`` in ``out_dir`` when present)."""
    md: List[str] = ["# E4 -- station sizing sensitivity (spares B_j, chargers C_j, power P_j)", ""]
    d0 = df.iloc[0]
    md.append(f"Family `{family}` (|K| = {d0['n_bikes']}, |I| = {d0['n_orders']}, H = {d0['H']} "
              f"slots of 5 min, L = {d0['L']}, p_ch = {d0['p_ch_kw']:.3f} kW), co-located 3 sites "
              f"(K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, shared grid group 8 kW / 6 kW "
              f"from 18:00), seeds {seeds}; pruning {C.PRUNING_DEFAULTS} (reposition targets = restaurants + facilities + depots); "
              f"Gurobi Threads {C.THREADS}, TimeLimit {time_limit:.0f} s, OutputFlag 0; total wall time {wall / 60:.1f} min. "
              f"Baseline: nearest-feasible dispatch, threshold swap (q_thr = 3), FCFS, HIGH_FIRST charging, no transfers "
              f"(no services exist on the co-located layout, so C_reb = 0 everywhere). Instances are byte-identical across "
              f"methods and sizes (only the facility fields B_j, C_j, P_kw and, for the control, rho change).")
    md.append("")
    md.append("Costs are in the toy unit system (E2 p.14). `total` is (26) including the setup constant (27) "
              f"`F_j y_j + bB B_j + bC C_j` (F = 20, bB = 3, bC = 2 per site per horizon); `operational` = total - C_setup. "
              "Marginal values are finite differences of the seed-mean cost per *one unit added at one site* "
              "(network change / 3 sites / step).")
    md.append("")
    md.append("## Which comparison is the headline")
    md.append("")
    md.append("**Headline: ILP (written model, rho = 0.5) vs baseline at identical sizes.** The baseline does not enforce "
              "the network end target (18) (DECISIONS.md: reported, not enforced), so its schedule is the same under rho = 0 "
              "and rho = 0.5, while the ILP with rho = 0.5 carries the extra requirement sum_j n_jLH >= 0.5 sum_j B_j. "
              "To show how much of the gap is (18), the `ILP_rho0` rows re-solve the same instances with rho = 0 (same "
              "baseline MIP start); `gap_decomposition.csv` reports both `vs = ILP` and `vs = ILP_rho0`. The rho = 0 "
              "comparison is the fair *operational* comparison; the rho = 0.5 comparison is the one that matches the written model.")
    md.append("")
    for sweep, col, unit in (("B", "B_j", "battery"), ("C", "C_j", "charger"), ("P", "P_kw", "kW")):
        g = summaries.get(sweep)
        if g is None:
            continue
        md.append(f"## Sweep {sweep}: {col} (seed means; min/max over seeds for total)")
        md.append("")
        cols = ["method", col, "n_seeds", "total_mean", "total_min", "total_max", "operational_mean", "C_setup_mean",
                "C_orders_mean", "unserved_mean", "response_mean", "lateness_mean", "C_elec_mean", "C_travel_mean",
                "n_unserved_mean", "swap_wait_slots_mean", "stockout_slots_mean", "stockout_queue_slots_mean",
                "charger_util_mean_mean", "desk_occupancy_mean_mean", "idle_full_share_mean_mean", "peak_kw_group_mean",
                "n_swaps_mean", "end_full_total_mean", "marginal_operational_per_unit", "marginal_total_per_unit",
                "runtime_s_mean", "runtime_s_max", "gap_max"]
        cols = [c for c in cols if c in g.columns]
        md.append(C.markdown_table(g, cols, 2))
        md.append("")
        md.append(f"`marginal_*_per_unit` at size s = (cost(s) - cost(next s)) per added {unit} at one site (positive = adding "
                  "the unit saves cost); `charger_util_mean_mean` = sum_t sum_q c_jqt / (C_j H) averaged over sites and seeds; "
                  "`desk_occupancy` = swap-slot occupancy of the single swap position (22); `idle_full_share` = share of "
                  "slots in which a full battery stays unused; `stockout_queue_slots` = slots with n_jLt = 0 and a bike "
                  "waiting to swap; `end_full_total` = sum_j n_jLH (the (18) left-hand side).")
        md.append("")
    gd = summaries.get("gap")
    if gd is not None:
        md.append("## Gap decomposition: baseline - ILP by cost component (seed means)")
        md.append("")
        cols = ["sweep", "size", "vs", "baseline_total", "ilp_total", "gap_total", "gap_pct", "gap_unserved", "gap_response",
                "gap_lateness", "gap_C_travel", "gap_C_elec", "unserved_share_of_gap", "baseline_n_unserved", "ilp_n_unserved"]
        md.append(C.markdown_table(gd, [c for c in cols if c in gd.columns], 2))
        md.append("")
        md.append("`gap_<component>` = baseline component - ILP component (positive = baseline pays more); "
                  "`unserved_share_of_gap` = gap_unserved / gap_total (P_i = 100 per unserved order).")
        md.append("")
    if "heat_ILP" in summaries:
        md.append("## B x C grid (seed means, P_j = 4 kW)")
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
    free = summaries.get("free")
    if free is not None and not free.empty:
        md.append("## ILP with B_j, C_j free (y fixed, bB = 3, bC = 2) and the fixed re-run at the chosen sizes")
        md.append("")
        cols = ["seed", "sweep", "method", "status", "total", "operational", "C_setup", "C_orders", "C_elec",
                "n_unserved", "swap_wait_slots", "stockout_slots", "chosen_B", "chosen_C", "sum_B", "sum_C",
                "charger_util_mean", "idle_full_share_mean", "end_full_total", "gap", "runtime_s", "mip_start_accepted"]
        cols = [c for c in cols if c in free.columns]
        md.append(C.markdown_table(free.sort_values(["seed", "sweep", "method"]), cols, 2))
        md.append("")
    md.append("## Solver statistics")
    md.append("")
    for method in ("ILP", "ILP_rho0"):
        ilp = df[df["method"] == method]
        if ilp.empty:
            continue
        md.append(f"- `{method}` runs: {len(ilp)}; statuses {ilp['status'].value_counts().to_dict()}; binaries "
                  f"{int(ilp['n_binaries'].min()):,}-{int(ilp['n_binaries'].max()):,}; rows "
                  f"{int(ilp['n_rows'].min()):,}-{int(ilp['n_rows'].max()):,}; solve time mean {ilp['runtime_s'].mean():.1f} s, "
                  f"max {ilp['runtime_s'].max():.1f} s; gap max {ilp['gap'].max():.4f}; arc build mean {ilp['arc_build_s'].mean():.2f} s; "
                  f"model build mean {ilp['model_build_s'].mean():.2f} s; every schedule passes `evaluate.check`: "
                  f"{bool(ilp['check_ok'].all())}; MIP start accepted in {int((ilp['mip_start_accepted'] == True).sum())} "
                  f"of {int(ilp['mip_start_accepted'].notna().sum())} runs with a start.")
    bl = df[df["method"] == "baseline"]
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
        with open(interp, encoding="utf-8") as fh:
            md.append(fh.read().rstrip())
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
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--family", default=FAMILY)
    ap.add_argument("--no-heatmap", action="store_true")
    ap.add_argument("--probe", action="store_true", help="hardest variants on the first seed only")
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--sweeps", nargs="+", default=list(ALL_SWEEPS), choices=list(ALL_SWEEPS),
                    help="subset of the sweeps to run (default all)")
    ap.add_argument("--init-frac", nargs=2, type=float, default=None, metavar=("LO", "HI"),
                    help="override the initial-charge range q0 ~ U{ceil(LO L)..HI L} (swap-stressed supplement)")
    ap.add_argument("--no-rho0", action="store_true", help="skip the rho = 0 control ILP / warm-start chain")
    ap.add_argument("--report-only", action="store_true",
                    help="rebuild summaries, figures and RESULTS.md from <out-dir>/results.csv without solving")
    args = ap.parse_args()
    if args.report_only:
        frame = pd.read_csv(os.path.join(args.out_dir, "results.csv"))
        meta_path = os.path.join(args.out_dir, "run_meta.json")
        meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
        report(frame, args.out_dir, meta.get("wall_s", float("nan")), meta.get("time_limit", args.time_limit),
               meta.get("seeds", args.seeds), meta.get("family", args.family), not args.no_heatmap)
    else:
        main(args.seeds, args.time_limit, not args.no_heatmap, args.family, args.out_dir, args.probe,
             args.sweeps, args.init_frac, not args.no_rho0)
