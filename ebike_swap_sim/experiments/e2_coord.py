"""Experiment E2 -- coordinated ILP vs event-driven baseline on identical demand
(``plan.experiments[1]`` of ``notes/workflow1_result.json``).

Question
--------
How much does offline coordination (dispatch + swap timing + charging + transfers)
gain over the deck's naive event-driven policy, and where does the gain come from
(unserved orders, response, lateness, distance, electricity, rebalancing)?

Design
------
* Instances: synthetic family of :mod:`ebike_swap_sim.generator`, 10 bikes,
  ``H = 24`` slots of 5 min (dinner window 17:30-19:30), ``L = 12`` levels of
  50 Wh, co-located facilities fixed (3 sites, ``B_j = 4``, ``C_j = 3``,
  ``M_j = 1``, ``sigma_j = 1``), hourly shuttle services between every pair of
  sites (``h, z`` free for the ILP, ``h = z = 0`` for the baseline), demand
  multipliers ``{0.75, 1.0, 1.5}`` of the base 30 orders -> ``|I| in {22, 30,
  45}``, seeds 0-4.  For a given seed the geography (grid, restaurants, sites,
  depots, bikes) is drawn before the orders, so the three demand levels of one
  seed share the same network.  Every method consumes the byte-identical
  :class:`Instance` and :class:`ArcLibrary` (plan pruning: reposition targets =
  restaurants + facilities + depots, ``tau_max = 4``, ``start_slack = 6``,
  lossless ``reachable_pruning = True``).
* Methods (per instance):
  ``baseline`` = Baseline(q_thr = ceil(0.25 L) = 3, FCFS, HIGH_FIRST, NONE);
  ``baseline_opp`` = baseline + opportunistic swap;
  ``baseline_zone`` = baseline with ``dispatch_scope = 'zone'``;
  ``ilp`` = ILP optimum of (5)-(22), (26)-(32) with the baseline as MIP start
  (accepted only when the baseline satisfies (18));
  ``ilp_fixed_arcs`` = ILP with the baseline's delivery arcs fixed
  (``x_ka = 1`` on the baseline's deliver arcs, ``0`` on all other deliver arcs,
  ``u_i`` fixed): only swap / charge / transfer / repositioning decisions free;
  ``ilp_fixed_assign`` = ILP with the baseline's order-to-bike *assignment* fixed
  (``u_i`` fixed, deliver arcs of order ``i`` allowed only for the baseline's
  bike) but delivery timing / sequencing free;
  ``baseline_rho0`` / ``ilp_rho0`` = the headline pair re-run on the same
  instance with ``rho = 0`` ((18) removed, the only family the baseline violates),
  so the baseline is a feasible point of the ILP and the gap is not inflated by
  the recovery target.
* Reported per run (``results.csv``): cost (26) and components (27)-(32), served
  share, mean response, lateness, bike km, swaps, queue wait slots, kWh,
  transfers, baseline violations of (9) / (17) / (18), ILP status / gap / time /
  size, MIP-start acceptance.  ``RESULTS.md`` adds per-demand means, relative
  improvement with 95 % t-confidence intervals over seeds, the decomposition of
  the baseline-ILP gap into components (is ``P_i`` dominant?) and the
  dispatch-vs-swap/charge decomposition from the fixed-dispatch runs.

Run from ``ebike_swap_sim/`` (about 30 min with Threads 4)::

    PYTHONPATH=. python3 experiments/e2_coord.py [--seeds 0 1 2 3 4] [--mults 0.75 1.0 1.5]
                                                 [--time-limit 240] [--out outputs/e2_coord]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import ArcLibrary, Instance, Schedule, build_arcs, check, cost, metrics  # noqa: E402
from ebike_swap_sim import generator as gen  # noqa: E402
from experiments import common as C  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e2_coord")
N_BIKES = 10
BASE_ORDERS = 30
H, L = 24, 12
#: demand multiplier -> |I| (0.75 * 30 = 22.5 is floored to 22)
DEMAND: Dict[float, int] = {0.75: 22, 1.0: 30, 1.5: 45}
SEEDS = [0, 1, 2, 3, 4]
TIME_LIMIT = 240.0
METHODS = ["baseline", "baseline_opp", "baseline_zone", "ilp", "ilp_fixed_arcs",
           "ilp_fixed_assign", "baseline_rho0", "ilp_rho0"]
COMPONENTS = ["C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"]
#: validated categorical palette (dataviz reference instance, light mode, fixed order)
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
#: two-sided 97.5 % Student t quantiles for df = 1..10 (95 % CI of a mean)
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
        9: 2.262, 10: 2.228}


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def make_instance(seed: int, mult: float) -> Instance:
    """E2 instance of one ``(seed, demand multiplier)``: :func:`generator.make_synthetic_instance`
    with 10 bikes, ``DEMAND[mult]`` orders, ``H = 24``, ``L = 12``, default co-located
    fixed facilities (3 sites, ``B = 4``, ``C = 3``, ``M = 1``, ``sigma = 1``) and hourly
    site <-> site shuttle services (``services_spec['site_site']``)."""
    n_orders = DEMAND[mult]
    inst = gen.make_synthetic_instance(
        seed=seed, n_bikes=N_BIKES, n_orders=n_orders, H=H, L=L,
        services_spec={"site_site": True, "site_site_every": 12},
        name=f"e2-K{N_BIKES}-I{n_orders}-seed{seed}")
    inst.meta["family"] = "e2_coord"
    inst.meta["seed"] = seed
    inst.meta["demand_mult"] = mult
    return inst


def rho0_copy(inst: Instance) -> Instance:
    """Byte-identical copy of ``inst`` with ``rho = 0`` ((18) dropped); nothing else changes."""
    inst0 = dataclasses.replace(inst, rho=0.0, meta=dict(inst.meta))
    inst0.meta["name"] = inst.meta["name"] + "-rho0"
    return inst0


def ci95(values: Sequence[float]) -> Tuple[float, float, float]:
    """``(mean, half-width, n)`` of a 95 % Student-t confidence interval over seeds."""
    v = [float(x) for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n == 0:
        return float("nan"), float("nan"), 0
    m = sum(v) / n
    if n == 1:
        return m, float("nan"), 1
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    return m, T975.get(n - 1, 1.96) * sd / math.sqrt(n), n


# ---------------------------------------------------------------------------
# per-run records
# ---------------------------------------------------------------------------
def _base_row(inst: Instance, lib: ArcLibrary, method: str) -> Dict[str, Any]:
    return {
        "name": inst.meta["name"], "seed": inst.meta["seed"], "demand_mult": inst.meta["demand_mult"],
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
        "n_facilities": len(inst.facilities), "n_services": len(inst.services), "rho": inst.rho,
        "n_arcs": len(lib), "method": method,
    }


def _metric_cols(inst: Instance, lib: ArcLibrary, sched: Schedule, rep: Dict[str, Any]) -> Dict[str, Any]:
    """Cost (26)-(32), ``evaluate.metrics`` and checker summary of one schedule."""
    cst = cost(inst, lib, sched)
    met = metrics(inst, lib, sched)
    fams = C.family_counts(rep)
    out: Dict[str, Any] = C.flatten_cost(cst, "")
    out.update({
        "served_share": met["served_share"], "n_served": met["n_served"], "n_unserved": met["n_unserved"],
        "mean_response_h": met["mean_response_h"], "max_response_h": met["max_response_h"],
        "mean_lateness_h": met["mean_lateness_h"], "max_lateness_h": met["max_lateness_h"],
        "n_late": met["n_late"], "bike_km": met["bike_km"], "n_swaps": met["n_swaps"],
        "n_moves": met["n_moves"], "n_waits": met["n_waits"],
        "mean_wait_before_swap": met["mean_wait_before_swap"],
        "queue_wait_slots": sum(met["wait_before_swap"]),
        "kwh_purchased": met["kwh_purchased"],
        "peak_kw_sites": max(met["peak_kw_group"].values()) if met["peak_kw_group"] else 0.0,
        "transfers_used": met["transfers_used"], "batteries_moved": met["batteries_moved"],
        "stockout_slots": sum(met["stockout_slots"].values()),
        "end_full_total": met["end_full_total"], "end_target_shortfall_18": met["end_target_shortfall"],
        "check_ok": rep["ok"], "check_families": json.dumps(fams, sort_keys=True),
        "identity_24_ok": rep["identity_24_ok"] and C.check_identity_24(inst, lib, sched),
    })
    return out


def run_baseline(inst: Instance, lib: ArcLibrary, params: Dict[str, Any], method: str
                 ) -> Tuple[Dict[str, Any], Schedule]:
    """One baseline variant (:func:`common.run_baseline_case`) as a flat row; the
    (9) / (17) / (18) violations the policy *reports* are recorded as
    ``viol_9`` (bikes without terminal certificate), ``viol_17`` (summed local
    shortfall) and ``viol_18`` (global shortfall)."""
    res = C.run_baseline_case(inst, lib, params, label=method)
    fl = res["flags"]
    row = _base_row(inst, lib, method)
    row.update(_metric_cols(inst, lib, res["schedule"], res["check"]))
    row.update({
        "status": "POLICY", "obj": res["cost"]["total"], "bound": None, "gap": None,
        "runtime_s": res["runtime"], "build_time_s": None, "n_binaries": None, "n_rows": None,
        "mip_start_accepted": None, "mip_start_verified_status": None,
        "ok_modulo_report_only": res["ok_modulo_report_only"],
        "viol_9": len(fl["terminal_violations"]), "viol_17": sum(fl["end_shortfalls"]["local"].values()),
        "viol_18": fl["end_shortfalls"]["global"], "stranded_bikes": len(fl["stranded_bikes"]),
        "queued_at_H": len(fl["queued_at_H"]),
        "baseline_queue_wait_slots": sum(fl["wait_slots_in_queue"].values())
        if isinstance(fl.get("wait_slots_in_queue"), dict) else None,
        "pruned_arc_fallbacks": sum((fl.get("pruned_arc_fallbacks") or {}).get("count", {}).values())
        if isinstance((fl.get("pruned_arc_fallbacks") or {}).get("count"), dict) else None,
        "inventory_consistent": fl["inventory_consistent"],
    })
    return row, res["schedule"]


def run_ilp(inst: Instance, lib: ArcLibrary, method: str, start: Schedule,
            fix: Optional[str] = None, time_limit: float = TIME_LIMIT) -> Tuple[Dict[str, Any], Optional[Schedule]]:
    """Solve the E2 ILP (5)-(22), (26)-(32) via :func:`ebike_swap_sim.ilp.build_model`
    (``OutputFlag 0``, ``Threads 4``, ``TimeLimit``) with ``start`` as verified MIP start.

    ``fix = 'arcs'`` fixes the deliver arcs to ``start``'s (``x_ka = 1`` on its deliver
    arcs, ``0`` on every other deliver arc) and ``u_i`` to ``start``'s, leaving only
    swap / charge / transfer / repositioning free; ``fix = 'assign'`` fixes ``u_i``
    and forbids deliver arcs of order ``i`` for every bike other than the one
    serving ``i`` in ``start`` (timing free).  Bounds are applied through the
    :class:`ILPModel` variable maps followed by ``model.update()`` so that the
    fix-and-solve verification of the start restores *these* bounds.
    """
    from ebike_swap_sim import ilp

    t0 = time.perf_counter()
    mdl = ilp.build_model(inst, lib, threads=C.THREADS, time_limit=time_limit)
    if fix is not None:
        chosen = {int(a) for ids in start.x.values() for a in ids}
        bike_of_order = {lib.arc(a).order: lib.arc(a).k for a in chosen if lib.arc(a).kind == "deliver"}
        for a in lib.arcs_of_kind("deliver"):
            var = mdl.x[a.id]
            if fix == "arcs":
                val = 1.0 if a.id in chosen else 0.0
                var.LB = var.UB = val
            elif fix == "assign":
                if bike_of_order.get(a.order) != a.k:
                    var.UB = 0.0
            else:
                raise ValueError(fix)
        for i, var in mdl.u.items():
            var.LB = var.UB = float(start.u.get(i, 0))
        mdl.model.update()
    sched, st = mdl.solve(mip_start=start, verify_start=True)
    wall = time.perf_counter() - t0
    row = _base_row(inst, lib, method)
    ms = st.get("mip_start") or {}
    row.update({
        "status": st["status"], "obj": st.get("obj"), "bound": st.get("bound"), "gap": st.get("gap"),
        "runtime_s": st["runtime"], "build_time_s": st["build_time"], "wall_s": wall,
        "n_binaries": st.get("n_binaries"), "n_rows": st.get("n_rows"), "node_count": st.get("node_count"),
        "mip_start_accepted": ms.get("accepted"), "mip_start_verified_status": ms.get("verified_status"),
        "mip_start_obj": ms.get("start_obj"), "fix": fix or "",
    })
    if sched is None:
        row.update(total=None, check_ok=None)
        return row, None
    rep = check(inst, lib, sched)
    row.update(_metric_cols(inst, lib, sched, rep))
    row.update(viol_9=0, viol_17=0, viol_18=0)
    return row, sched


def run_instance(seed: int, mult: float, time_limit: float, inst_dir: str) -> List[Dict[str, Any]]:
    """All :data:`METHODS` on one ``(seed, mult)`` instance; returns the flat rows."""
    inst = make_instance(seed, mult)
    inst.save(os.path.join(inst_dir, f"{inst.meta['name']}.json"))
    pruning = C.pruning_for(inst, reachable=True)
    lib, build_t = C.build_library(inst, pruning)
    rows: List[Dict[str, Any]] = []

    r_base, s_base = run_baseline(inst, lib, {}, "baseline")
    r_opp, _ = run_baseline(inst, lib, {"opportunistic_swap": True}, "baseline_opp")
    r_zone, _ = run_baseline(inst, lib, {"dispatch_scope": "zone"}, "baseline_zone")
    for r in (r_base, r_opp, r_zone):
        r["lib_build_time_s"] = build_t
    rows += [r_base, r_opp, r_zone]
    print(f"  baseline {r_base['total']:.1f} (unserved {r_base['n_unserved']}, fams {r_base['check_families']})"
          f" opp {r_opp['total']:.1f} zone {r_zone['total']:.1f}", flush=True)

    r_ilp, _ = run_ilp(inst, lib, "ilp", s_base, time_limit=time_limit)
    print(f"  ilp {r_ilp['status']} {r_ilp.get('total')} gap {r_ilp['gap']} {r_ilp['runtime_s']:.1f}s "
          f"start_acc {r_ilp['mip_start_accepted']}", flush=True)
    r_fa, _ = run_ilp(inst, lib, "ilp_fixed_arcs", s_base, fix="arcs", time_limit=time_limit)
    print(f"  ilp_fixed_arcs {r_fa['status']} {r_fa.get('total')} {r_fa['runtime_s']:.1f}s", flush=True)
    r_fs, _ = run_ilp(inst, lib, "ilp_fixed_assign", s_base, fix="assign", time_limit=time_limit)
    print(f"  ilp_fixed_assign {r_fs['status']} {r_fs.get('total')} {r_fs['runtime_s']:.1f}s", flush=True)
    rows += [r_ilp, r_fa, r_fs]

    # rho = 0 pair on the identical instance (only (18) removed)
    inst0 = rho0_copy(inst)
    lib0, _ = C.build_library(inst0, pruning)
    assert len(lib0) == len(lib), "rho does not enter the arc rules; libraries must coincide"
    r_b0, s_b0 = run_baseline(inst0, lib0, {}, "baseline_rho0")
    assert abs(r_b0["total"] - r_base["total"]) < 1e-9, "baseline must not depend on rho"
    r_i0, _ = run_ilp(inst0, lib0, "ilp_rho0", s_b0, time_limit=time_limit)
    print(f"  rho0: baseline {r_b0['total']:.1f} fams {r_b0['check_families']} | ilp {r_i0['status']} "
          f"{r_i0.get('total')} {r_i0['runtime_s']:.1f}s start_acc {r_i0['mip_start_accepted']}", flush=True)
    rows += [r_b0, r_i0]
    for r in rows:
        r["lib_build_time_s"] = build_t
    return rows


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def paired(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Rows of method ``a`` joined to method ``b`` on ``(seed, demand_mult)`` with
    ``rel_impr`` = (total_a - total_b) / total_a in % and per-component differences."""
    da = df[df.method == a].set_index(["seed", "demand_mult"])
    db = df[df.method == b].set_index(["seed", "demand_mult"])
    idx = da.index.intersection(db.index)
    out = pd.DataFrame(index=idx)
    out["total_a"] = da.loc[idx, "total"]
    out["total_b"] = db.loc[idx, "total"]
    out["abs_gain"] = out["total_a"] - out["total_b"]
    out["rel_impr"] = 100.0 * out["abs_gain"] / out["total_a"]
    op_a = out["total_a"] - da.loc[idx, "C_setup"].astype(float)
    out["rel_impr_ex_setup"] = 100.0 * out["abs_gain"] / op_a
    for comp in COMPONENTS:
        out[f"d_{comp}"] = da.loc[idx, comp].astype(float) - db.loc[idx, comp].astype(float)
    return out.reset_index()


def improvement_table(df: pd.DataFrame, pairs: Sequence[Tuple[str, str, str]]) -> pd.DataFrame:
    """Mean relative improvement (%) with 95 % CI half-width per demand level for each
    ``(label, baseline method, improved method)`` pair, plus the all-demand pooled row."""
    recs = []
    for label, a, b in pairs:
        p = paired(df, a, b)
        for mult in sorted(DEMAND) + ["all"]:
            sub = p if mult == "all" else p[p.demand_mult == mult]
            m, hw, n = ci95(sub["rel_impr"].tolist())
            ma, _, _ = ci95(sub["abs_gain"].tolist())
            mx, hx, _ = ci95(sub["rel_impr_ex_setup"].tolist())
            recs.append({"comparison": label, "demand_mult": mult, "n_seeds": n,
                         "rel_impr_mean_pct": m, "rel_impr_ci95_pct": hw,
                         "rel_impr_lo_pct": m - hw, "rel_impr_hi_pct": m + hw, "abs_gain_mean": ma,
                         "rel_impr_ex_setup_mean_pct": mx, "rel_impr_ex_setup_ci95_pct": hx})
    return pd.DataFrame(recs)


def _mlabel(mult: Any) -> str:
    """Table label of a demand multiplier (``'x0.75'``; ``'all'`` unchanged)."""
    return "all" if mult == "all" else f"x{float(mult):g}"


def gap_decomposition(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Mean component differences ``a - b`` per demand level and their share of the
    mean total gap (the share of ``unserved`` answers "does ``P_i`` dominate?")."""
    p = paired(df, a, b)
    recs = []
    for mult in sorted(DEMAND) + ["all"]:
        sub = p if mult == "all" else p[p.demand_mult == mult]
        gap = sub["abs_gain"].mean()
        rec: Dict[str, Any] = {"demand_mult": mult, "total_gap": gap}
        for comp in COMPONENTS:
            d = sub[f"d_{comp}"].mean()
            rec[comp] = d
            rec[f"{comp}_share_pct"] = 100.0 * d / gap if gap else float("nan")
        recs.append(rec)
    return pd.DataFrame(recs)


def method_means(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    """Mean of ``cols`` over seeds per ``(demand_mult, method)`` in :data:`METHODS` order."""
    g = df.groupby(["demand_mult", "method"])[list(cols)].mean(numeric_only=True).reset_index()
    g["method"] = pd.Categorical(g["method"], METHODS, ordered=True)
    return g.sort_values(["demand_mult", "method"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def _style(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#9a9a96")
    ax.tick_params(colors="#52514e", labelsize=8)
    ax.yaxis.grid(True, color="#e6e6e3", linewidth=0.8)
    ax.set_axisbelow(True)


def plot_cost_components(df: pd.DataFrame, path: str, methods: Sequence[str]) -> str:
    """Stacked bars of the mean cost components (27)-(32) per method, one panel per
    demand level (shared y-axis, cost in toy units)."""
    comps = ["unserved", "response", "lateness", "C_travel", "C_elec", "C_reb", "C_setup"]
    names = {"unserved": "unserved P_i u_i (30)", "response": "response (31)", "lateness": "lateness (31)",
             "C_travel": "travel (29)", "C_elec": "electricity (28)", "C_reb": "transfers (32)",
             "C_setup": "setup (27), constant"}
    short = {"baseline": "Baseline", "baseline_opp": "Baseline + opp. swap", "baseline_zone": "Baseline zone dispatch",
             "ilp_fixed_arcs": "ILP, fixed arcs", "ilp_fixed_assign": "ILP, fixed assignment", "ilp": "ILP (rho = 0.5)",
             "ilp_rho0": "ILP (rho = 0)", "baseline_rho0": "Baseline (rho = 0)"}
    mults = sorted(DEMAND)
    means = method_means(df, comps + ["total"])
    fig, axes = plt.subplots(1, len(mults), figsize=(3.8 * len(mults) + 1.5, 5.2), sharey=True)
    for ax, mult in zip(np.atleast_1d(axes), mults):
        sub = means[means.demand_mult == mult].set_index("method")
        xs = np.arange(len(methods))
        bottom = np.zeros(len(methods))
        for ci, comp in enumerate(comps):
            vals = np.array([float(sub.loc[m, comp]) if m in sub.index else 0.0 for m in methods])
            ax.bar(xs, vals, 0.68, bottom=bottom, color=PALETTE[ci], edgecolor="white", linewidth=1.0,
                   label=names[comp] if mult == mults[0] else None)
            bottom += vals
        for x, tot in zip(xs, bottom):
            ax.text(x, tot + 8, f"{tot:.0f}", ha="center", va="bottom", fontsize=7.5, color="#0b0b0b")
        ax.set_xticks(xs)
        ax.set_xticklabels([short.get(m, m) for m in methods], fontsize=7.5, rotation=35, ha="right",
                           rotation_mode="anchor")
        ax.set_title(f"demand x{mult:g}  (|I| = {DEMAND[mult]})", fontsize=10, color="#0b0b0b")
        _style(ax)
    n_seeds = df["seed"].nunique()
    np.atleast_1d(axes)[0].set_ylabel(f"mean cost over {n_seeds} seeds (toy units)", fontsize=9)
    fig.suptitle("Cost components (27)-(32) by method and demand level: the baseline pays mostly for unserved orders",
                 fontsize=11, x=0.01, ha="left", color="#0b0b0b")
    fig.legend(loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_improvement(imp: pd.DataFrame, path: str) -> str:
    """Relative improvement over the baseline (%) vs demand multiplier, mean and 95 % CI
    over seeds, one line per comparison."""
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    comps = list(dict.fromkeys(imp["comparison"]))
    mults = sorted(DEMAND)
    n_seeds = int(imp["n_seeds"].max()) if len(imp) else 0
    for ci, label in enumerate(comps):
        sub = imp[(imp.comparison == label) & (imp.demand_mult != "all")].copy()
        sub["demand_mult"] = sub["demand_mult"].astype(float)
        sub = sub.sort_values("demand_mult").dropna(subset=["rel_impr_mean_pct"])
        if sub.empty:
            continue
        off = (ci - (len(comps) - 1) / 2) * 0.012
        x = sub["demand_mult"].to_numpy() + off
        yerr = sub["rel_impr_ci95_pct"].fillna(0.0)
        ax.errorbar(x, sub["rel_impr_mean_pct"], yerr=yerr, color=PALETTE[ci],
                    marker="o", markersize=5, linewidth=2, capsize=3, label=label)
        ax.annotate(f"{sub['rel_impr_mean_pct'].iloc[-1]:.1f} %", (x[-1], sub["rel_impr_mean_pct"].iloc[-1]),
                    xytext=(8, 9 * ((len(comps) - 1) / 2 - ci)), textcoords="offset points", fontsize=7.5,
                    color="#52514e", va="center")
    ax.axhline(0, color="#9a9a96", linewidth=0.8)
    ax.set_xticks(mults)
    ax.set_xticklabels([f"x{m:g}\n|I| = {DEMAND[m]}" for m in mults])
    ax.set_xlabel("demand multiplier (orders for 10 bikes in a 2 h window)", fontsize=9)
    ax.set_ylabel("cost reduction vs baseline (%)", fontsize=9)
    ax.set_xlim(0.6, 1.7)
    ax.set_title(f"Relative improvement over the event-driven baseline (mean and 95 % CI over {n_seeds} seeds)",
                 fontsize=10, loc="left", color="#0b0b0b")
    ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_gap_decomposition(dec: pd.DataFrame, path: str, title: str) -> str:
    """Stacked bars of the baseline-minus-ILP gap by component per demand level."""
    comps = ["unserved", "response", "lateness", "C_travel", "C_elec", "C_reb"]
    names = {"unserved": "unserved P_i", "response": "response", "lateness": "lateness",
             "C_travel": "travel", "C_elec": "electricity", "C_reb": "transfers"}
    sub = dec[dec.demand_mult != "all"].copy()
    sub["demand_mult"] = sub["demand_mult"].astype(float)
    sub = sub.sort_values("demand_mult")
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    xs = np.arange(len(sub))
    pos = np.zeros(len(sub))
    neg = np.zeros(len(sub))
    for ci, comp in enumerate(comps):
        vals = sub[comp].to_numpy(dtype=float)
        bottoms = np.where(vals >= 0, pos, neg)
        ax.bar(xs, vals, 0.6, bottom=bottoms, color=PALETTE[ci], edgecolor="white", linewidth=1.0,
               label=names[comp])
        pos += np.where(vals >= 0, vals, 0)
        neg += np.where(vals < 0, vals, 0)
    for x, tot, share in zip(xs, sub["total_gap"], sub["unserved_share_pct"]):
        ax.text(x, pos[int(x)] + 5, f"gap {tot:.0f}\nunserved {share:.0f} %", ha="center", va="bottom",
                fontsize=7.5, color="#0b0b0b")
    ax.axhline(0, color="#9a9a96", linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"x{m:g}  (|I| = {DEMAND[m]})" for m in sub["demand_mult"]])
    ax.set_ylabel("baseline cost - ILP cost (toy units, mean over seeds)", fontsize=9)
    ax.set_xlabel("demand multiplier", fontsize=9)
    ax.set_title(title, fontsize=10, loc="left", color="#0b0b0b")
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    ax.set_ylim(min(neg.min(), 0) - 20, pos.max() * 1.2 + 30)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def write_results_md(df: pd.DataFrame, out_dir: str, wall: float, time_limit: float) -> str:
    """Compose ``RESULTS.md``: tables (per-demand means, improvement CIs, gap and
    dispatch decompositions, solver stats, baseline violations) + interpretation."""
    pairs = [("ILP (rho=0.5) vs baseline", "baseline", "ilp"),
             ("ILP (rho=0) vs baseline [headline]", "baseline_rho0", "ilp_rho0"),
             ("ILP fixed arcs vs baseline", "baseline", "ilp_fixed_arcs"),
             ("ILP fixed assignment vs baseline", "baseline", "ilp_fixed_assign"),
             ("baseline+opp. swap vs baseline", "baseline", "baseline_opp"),
             ("baseline zone dispatch vs baseline", "baseline", "baseline_zone")]
    imp = improvement_table(df, pairs)
    imp.to_csv(os.path.join(out_dir, "improvement.csv"), index=False)
    dec0 = gap_decomposition(df, "baseline_rho0", "ilp_rho0")
    dec = gap_decomposition(df, "baseline", "ilp")
    dec0.to_csv(os.path.join(out_dir, "gap_decomposition_rho0.csv"), index=False)
    dec.to_csv(os.path.join(out_dir, "gap_decomposition_rho05.csv"), index=False)

    cost_cols = ["total"] + COMPONENTS
    metric_cols = ["served_share", "mean_response_h", "mean_lateness_h", "max_lateness_h", "n_late",
                   "bike_km", "n_swaps", "queue_wait_slots", "mean_wait_before_swap", "kwh_purchased",
                   "transfers_used", "batteries_moved", "end_full_total"]
    solver_cols = ["n_binaries", "n_rows", "runtime_s", "gap"]
    means_cost = method_means(df, cost_cols)
    means_met = method_means(df, metric_cols)
    ilp_rows = df[df.method.str.startswith("ilp")]
    solver = ilp_rows.groupby(["demand_mult", "method"]).agg(
        n_binaries=("n_binaries", "mean"), n_rows=("n_rows", "mean"), runtime_mean_s=("runtime_s", "mean"),
        runtime_max_s=("runtime_s", "max"), gap_max=("gap", "max"),
        n_optimal=("status", lambda s: int((s == "OPTIMAL").sum())), n_runs=("status", "size"),
        start_accepted=("mip_start_accepted", lambda s: int(sum(bool(v) for v in s)))).reset_index()
    base_rows = df[df.method == "baseline"]
    viol = base_rows.groupby("demand_mult").agg(
        viol_9_bikes=("viol_9", "sum"), viol_17_shortfall=("viol_17", "sum"), viol_18_runs=("viol_18", lambda s: int((s > 0).sum())),
        viol_18_mean_shortfall=("viol_18", "mean"), stranded=("stranded_bikes", "sum"),
        queued_at_H=("queued_at_H", "sum"), seeds=("seed", "size")).reset_index()

    # dispatch vs swap/charge decomposition (rho = 0.5 family, all three ILPs on the same instance)
    dd = []
    for mult in sorted(DEMAND) + ["all"]:
        sub = df if mult == "all" else df[df.demand_mult == mult]
        piv = sub.pivot_table(index=["seed", "demand_mult"], columns="method", values="total", aggfunc="first")
        if not {"baseline", "ilp", "ilp_fixed_arcs", "ilp_fixed_assign"} <= set(piv.columns):
            continue
        ok = piv.dropna(subset=["baseline", "ilp", "ilp_fixed_arcs", "ilp_fixed_assign"])
        tot = ok["baseline"] - ok["ilp"]
        swap_only = ok["baseline"] - ok["ilp_fixed_arcs"]
        timing = ok["ilp_fixed_arcs"] - ok["ilp_fixed_assign"]
        reassign = ok["ilp_fixed_assign"] - ok["ilp"]
        dd.append({"demand_mult": _mlabel(mult), "n": len(ok), "total_gain": tot.mean(),
                   "swap_charge_transfer_only": swap_only.mean(),
                   "swap_charge_transfer_share_pct": 100 * swap_only.sum() / tot.sum() if tot.sum() else float("nan"),
                   "delivery_timing_resequencing": timing.mean(),
                   "timing_share_pct": 100 * timing.sum() / tot.sum() if tot.sum() else float("nan"),
                   "order_reassignment": reassign.mean(),
                   "reassignment_share_pct": 100 * reassign.sum() / tot.sum() if tot.sum() else float("nan")})
    ddf = pd.DataFrame(dd)
    ddf.to_csv(os.path.join(out_dir, "dispatch_decomposition.csv"), index=False)

    def row(label: str, mult: Any) -> pd.Series:
        return imp[(imp.comparison == label) & (imp.demand_mult == mult)].iloc[0]

    head = row("ILP (rho=0) vs baseline [headline]", "all")
    head05 = row("ILP (rho=0.5) vs baseline", "all")
    fa = row("ILP fixed arcs vs baseline", "all")
    fs = row("ILP fixed assignment vs baseline", "all")
    opp = row("baseline+opp. swap vs baseline", "all")
    zone = row("baseline zone dispatch vs baseline", "all")
    uns_share_all = float(dec0[dec0.demand_mult == "all"]["unserved_share_pct"].iloc[0])
    per_mult_head = {m: row("ILP (rho=0) vs baseline [headline]", m) for m in sorted(DEMAND)}
    n18 = int((base_rows["viol_18"] > 0).sum())
    served = means_met.set_index(["demand_mult", "method"])["served_share"]
    resp = means_met.set_index(["demand_mult", "method"])["mean_response_h"]
    qwait = means_met.set_index(["demand_mult", "method"])["queue_wait_slots"]
    km = means_met.set_index(["demand_mult", "method"])["bike_km"]
    kwh = means_met.set_index(["demand_mult", "method"])["kwh_purchased"]
    trf = means_met.set_index(["demand_mult", "method"])["transfers_used"]
    n_timeout = int((ilp_rows["status"] != "OPTIMAL").sum())
    dd_all = ddf[ddf.demand_mult == "all"].iloc[0] if len(ddf) else None
    ilp0_rows = df[df.method == "ilp_rho0"]
    ilp_kwh = float(ilp0_rows["kwh_purchased"].sum())
    ilp_transfers = int(ilp0_rows["transfers_used"].sum())
    rho_diff = paired(df, "ilp", "ilp_rho0")
    rho_cost_of_18 = float(rho_diff["abs_gain"].mean()) if len(rho_diff) else float("nan")
    zone_identical = bool((paired(df, "baseline", "baseline_zone")["abs_gain"].abs() < 1e-9).all())

    md: List[str] = []
    md.append("# E2 -- coordinated ILP vs event-driven baseline on identical demand\n")
    md.append(f"Instances: 10 bikes, |I| in {{22, 30, 45}} (demand x0.75 / x1.0 / x1.5 of 30 orders), H = 24 slots of "
              f"5 min, L = 12, 3 co-located fixed sites (B_j = 4, C_j = 3, M_j = 1, sigma_j = 1), hourly site <-> site "
              f"shuttles ({int(df['n_services'].iloc[0])} services; h, z free in the ILP, h = z = 0 in the baseline), "
              f"seeds {sorted(df.seed.unique().tolist())}. Pruning: reposition targets = restaurants + facilities + "
              f"depots, tau_max = 4, start_slack = 6, reachable_pruning = True (lossless). Gurobi 13: OutputFlag 0, "
              f"Threads 4, TimeLimit {time_limit:.0f} s; {n_timeout} of {len(ilp_rows)} ILP solves hit the limit. "
              f"Total wall time {wall / 60:.1f} min. One instance JSON per (seed, demand) in `instances/`; every "
              f"method consumes the byte-identical instance and arc library (the rho = 0 pair uses a copy that differs "
              f"only in `rho`).\n")
    md.append("## Headline\n")
    n17 = int((base_rows["viol_17"] > 0).sum())
    rej0 = df[(df.method == "ilp_rho0") & (df.mip_start_accepted == False)]  # noqa: E712
    md.append(f"**The headline comparison is `baseline_rho0` vs `ilp_rho0`** (both with rho = 0, i.e. without the "
              f"network recovery target (18), the family the baseline violates most often): there the baseline schedule is "
              f"an accepted MIP start in {len(base_rows) - len(rej0)} of {len(base_rows)} runs; the remaining {len(rej0)} "
              f"end with a local shortfall of (17) (R_end = 1 full spare per site, violated by the baseline in {n17} runs), "
              f"which the ILP meets at no measurable cost. Mean cost reduction **{head.rel_impr_mean_pct:.1f} % "
              f"(95 % CI +/- {head.rel_impr_ci95_pct:.1f}, n = {int(head.n_seeds)})**; by demand: "
              + ", ".join(f"x{m:g}: {per_mult_head[m].rel_impr_mean_pct:.1f} +/- {per_mult_head[m].rel_impr_ci95_pct:.1f} %"
                          for m in sorted(DEMAND))
              + f"; excluding the constant setup term (27) the operational cost falls by "
              f"{head.rel_impr_ex_setup_mean_pct:.1f} % (+/- {head.rel_impr_ex_setup_ci95_pct:.1f})"
              + f". With the written model (rho = 0.5) the reduction is {head05.rel_impr_mean_pct:.1f} % "
              f"(+/- {head05.rel_impr_ci95_pct:.1f}); the baseline violates (18) in {n18} of {len(base_rows)} runs, so "
              f"its MIP start is rejected there (reported, not enforced, per DECISIONS.md).\n")
    md.append("## Relative improvement over the baseline (mean over seeds, 95 % t-CI)\n")
    md.append(C.markdown_table(imp, ["comparison", "demand_mult", "n_seeds", "rel_impr_mean_pct", "rel_impr_ci95_pct",
                                     "rel_impr_lo_pct", "rel_impr_hi_pct", "abs_gain_mean",
                                     "rel_impr_ex_setup_mean_pct", "rel_impr_ex_setup_ci95_pct"], digits=2))
    md.append("\n`rel_impr` = (cost_baseline - cost_method) / cost_baseline in % (plan definition); "
              "`rel_impr_ex_setup` divides by the baseline cost without the constant setup term (27) "
              f"(C_setup = {float(df['C_setup'].iloc[0]):.0f} for the fixed facilities), i.e. the operational-cost "
              "reduction; `abs_gain_mean` in toy units; negative = the method is worse than the baseline.\n")
    md.append("## Cost (26) and components (27)-(32): mean over seeds per demand level and method\n")
    md.append(C.markdown_table(means_cost, ["demand_mult", "method"] + cost_cols, digits=2))
    md.append("\n## Service / operations metrics: mean over seeds\n")
    md.append(C.markdown_table(means_met, ["demand_mult", "method"] + metric_cols, digits=3))
    md.append("\n`queue_wait_slots` = wait slots at a swap node immediately before a swap (summed over swaps); "
              "`end_full_total` = full spares at H summed over sites ((18) requires >= rho * 12 = 6 at rho = 0.5).\n")
    md.append("## Gap decomposition (baseline - ILP) by component, rho = 0 headline pair\n")
    dec_cols = ["demand_mult", "total_gap"] + [c for c in COMPONENTS if c != "C_setup"] + [
        "unserved_share_pct", "response_share_pct", "lateness_share_pct", "C_travel_share_pct"]
    md.append(C.markdown_table(dec0.assign(demand_mult=dec0.demand_mult.map(_mlabel)), dec_cols, digits=1))
    md.append("\nSame decomposition for the written model (rho = 0.5):\n")
    md.append(C.markdown_table(dec.assign(demand_mult=dec.demand_mult.map(_mlabel)), dec_cols, digits=1))
    md.append("\n## Dispatch vs swap/charge decomposition (rho = 0.5, same instance, three ILPs)\n")
    md.append("`ilp_fixed_arcs` keeps the baseline's delivery arcs (who, when, from where) and frees only swaps, "
              "charging, transfers and repositioning; `ilp_fixed_assign` keeps the order-to-bike assignment and the "
              "unserved set but frees delivery timing; `ilp` frees everything. Gains are chained: baseline -> fixed arcs "
              "(swap/charge/transfer only) -> fixed assignment (re-timing) -> ILP (re-assignment incl. serving more orders).\n")
    md.append(C.markdown_table(ddf, list(ddf.columns), digits=1))
    md.append("\n## Solver statistics (ILP runs)\n")
    md.append(C.markdown_table(solver, list(solver.columns), digits=2))
    md.append("\n## Baseline violations of the report-only families (default baseline, per demand level)\n")
    md.append(C.markdown_table(viol, list(viol.columns), digits=2))
    md.append("\n`viol_9_bikes` = bikes without a terminal certificate (9); `viol_17_shortfall` = summed local "
              "end-stock shortfall (17); `viol_18_runs` = runs ending below rho * sum B (18).\n")
    md.append("## Interpretation\n")
    def g(series: pd.Series, key: Tuple[float, str]) -> float:
        return float(series.get(key, float("nan")))

    lines = []
    plan_rel = ("above" if head.rel_impr_mean_pct > 40 else "within" if head.rel_impr_mean_pct >= 10 else "below")
    lines.append(f"The ILP lowers the cost by {head.rel_impr_mean_pct:.0f} % on average (rho = 0 headline; "
                 f"{head05.rel_impr_mean_pct:.0f} % with rho = 0.5), {plan_rel} the 10-40 % band the plan expected at base "
                 f"demand, and the effect is {'stable' if head.rel_impr_ci95_pct < 0.5 * abs(head.rel_impr_mean_pct) else 'noisy'} "
                 f"across seeds (CI half-width {head.rel_impr_ci95_pct:.1f} points).")
    uns_by = {m: float(dec0[dec0.demand_mult == m]['unserved_share_pct'].iloc[0]) for m in sorted(DEMAND)}
    dom = "dominated" if uns_share_all > 50 else "not dominated"
    lines.append(f"The gap is {dom} by the P_i = 100 penalty: {uns_share_all:.0f} % of the baseline-minus-ILP "
                 f"difference is unserved orders (shares by demand: "
                 + ", ".join(f"x{m:g} {uns_by[m]:.0f} %" for m in sorted(DEMAND))
                 + f"); the baseline serves {100 * g(served, (1.0, 'baseline')):.0f} % of the orders at base "
                 f"demand versus {100 * g(served, (1.0, 'ilp_rho0')):.0f} % for the ILP, and "
                 f"{100 * g(served, (1.5, 'baseline')):.0f} % vs {100 * g(served, (1.5, 'ilp_rho0')):.0f} % at x1.5.")
    d_resp = float(dec0[dec0.demand_mult == "all"]["response"].iloc[0])
    lines.append(f"Response is the next component (mean response per served order {g(resp, (1.0, 'baseline')):.2f} h "
                 f"baseline vs {g(resp, (1.0, 'ilp_rho0')):.2f} h ILP at base demand); its summed cost "
                 f"{'falls' if d_resp > 0 else 'rises'} by {abs(d_resp):.0f} units on average because the ILP serves more orders, "
                 f"so the per-order response and the summed response cost move in opposite directions; "
                 f"travel ({g(km, (1.0, 'baseline')):.0f} vs {g(km, (1.0, 'ilp_rho0')):.0f} km) and electricity "
                 f"({g(kwh, (1.0, 'baseline')):.1f} vs {g(kwh, (1.0, 'ilp_rho0')):.1f} kWh) change little, as the plan predicted.")
    if dd_all is not None:
        where = ("dispatch" if dd_all.swap_charge_transfer_share_pct < 50 else "battery logistics")
        lines.append(f"The chained decomposition attributes {dd_all.swap_charge_transfer_share_pct:.0f} % of the gain to "
                     f"swap/charge/transfer decisions alone (baseline deliveries kept), "
                     f"{dd_all.timing_share_pct:.0f} % to re-timing the same assignment and "
                     f"{dd_all.reassignment_share_pct:.0f} % to re-assigning orders (including serving the orders the "
                     f"baseline dropped): the gain sits in {where}, "
                     f"{'which matches' if where == 'dispatch' else 'contrary to'} the plan's expectation.")
    tr_base, tr_hi = g(trf, (1.0, 'ilp_rho0')), g(trf, (1.5, 'ilp_rho0'))
    lines.append(f"The baseline swaps {df[df.method == 'baseline']['n_swaps'].mean():.1f} times per run (ILP "
                 f"{df[df.method == 'ilp_rho0']['n_swaps'].mean():.1f}) and accumulates "
                 f"{g(qwait, (1.5, 'baseline')):.1f} queue-wait slots per run at x1.5 (ILP {g(qwait, (1.5, 'ilp_rho0')):.1f}); "
                 f"the ILP uses {tr_base:.1f} transfer services per run at base demand and {tr_hi:.1f} at x1.5 "
                 f"(f_e = 5 per service), so site <-> site transfers are "
                 f"{'rarely' if max(tr_base, tr_hi) < 1 else 'regularly'} worth their fee when every site charges.")
    lines.append(f"Battery logistics is barely exercised by this 2-hour family: the ILP purchases {ilp_kwh:.1f} kWh in total over "
                 f"all {len(ilp0_rows)} runs and uses {ilp_transfers} transfer services, because 12 full spares for 10 bikes "
                 f"(q0 >= 0.4 L) cover every swap it needs within H = 24 and (18) costs it on average {rho_cost_of_18:.1f} units "
                 f"(ILP cost at rho = 0.5 minus rho = 0); the swap-queue congestion the plan expected at x1.5 does not appear "
                 f"either (M_j = 1, sigma_j = 1 and only {df[df.method == 'baseline']['n_swaps'].mean():.0f} swaps per run), so "
                 f"charging, transfers and (18) only become decision-relevant with a longer horizon or fewer spares (E3/E4).")
    if zone_identical:
        lines.append("Zone dispatch is byte-identical to global dispatch in every run: with 5 x 5-block zones a same-zone idle "
                     "bike, when it exists, is also the nearest-by-tau candidate, so the zone preference never changes the choice.")
    lines.append(f"The opportunistic-swap variant changes the baseline cost by {-opp.rel_impr_mean_pct:+.1f} % and zone dispatch "
                 f"by {-zone.rel_impr_mean_pct:+.1f} % (positive = worse): both are second-order next to the coordination gap, "
                 f"and the fixed-dispatch ILPs ({fa.rel_impr_mean_pct:.1f} % with fixed arcs, {fs.rel_impr_mean_pct:.1f} % with "
                 f"fixed assignment) show that re-optimising only the battery side of the baseline's plan recovers "
                 f"{'little' if fs.rel_impr_mean_pct < 0.3 * head05.rel_impr_mean_pct else 'a substantial part'} of the gap.")
    lines.append("Caveat: the gap is measured in the toy unit system of E2 p.14 (P_i = 100, w_i = 12/h, v_i = 24/h, kappa = 1/km, "
                 "pi = 2/kWh). With P_i this large relative to the operational terms, the comparison is essentially a "
                 "comparison of service levels; a USD-calibrated P_i or the service-share form (33) would rebalance the picture, "
                 "and the lexicographic switch would separate service level from cost explicitly.")
    md.append(" ".join(lines) + "\n")
    md.append("## Anomalies\n")
    anomalies = []
    if n18 or n17:
        rej05 = df[(df.method == "ilp") & (df.mip_start_accepted == False)]  # noqa: E712
        anomalies.append(f"- The default baseline ends below rho * sum B in {n18} of {len(base_rows)} runs (18) and below "
                         f"R_end_j = 1 at some site in {n17} runs (17), so its MIP start is rejected by the fix-and-solve "
                         f"verification in {len(rej05)} runs at rho = 0.5 and still in {len(rej0)} runs at rho = 0 "
                         f"(the (17)-only cases); both families are reported, not enforced, by the policy (DECISIONS.md). "
                         f"The rho = 0 re-run is the headline because (18) is the network-wide target the deck's policy does "
                         f"not know about; (17) could be removed the same way (R_end = 0) if a fully feasible start is wanted.")
    bad = df[(df.method.str.startswith("ilp")) & (df.status != "OPTIMAL")]
    if len(bad):
        anomalies.append("- ILP runs not proven optimal: " + ", ".join(f"{r.name}/{r.method} ({r.status}, gap {r.gap})" for r in bad.itertuples()))
    nonmono = paired(df, "ilp_fixed_arcs", "ilp")
    if (nonmono["abs_gain"] < -1e-6).any():
        anomalies.append("- ilp_fixed_arcs cheaper than ilp in some run (should be impossible): check solver gaps.")
    worse = paired(df, "baseline", "ilp")
    if (worse["abs_gain"] < -1e-6).any():
        anomalies.append("- ILP more expensive than the baseline in some run (impossible when the start is accepted).")
    v9 = int(base_rows["viol_9"].sum())
    if v9:
        anomalies.append(f"- Baseline bikes without terminal certificate (9): {v9}.")
    chk = df[df.method.str.startswith("ilp") & df.status.eq("OPTIMAL") & ~df.check_ok.astype(bool)]
    if len(chk):
        anomalies.append("- ILP schedules failing evaluate.check: " + ", ".join(chk.name))
    if not (df[df.method.str.startswith("ilp")]["identity_24_ok"].dropna().astype(bool)).all():
        anomalies.append("- Identity (24) broken on some ILP schedule.")
    srv_ilp = df[df.method == "ilp"].set_index(["seed", "demand_mult"])["n_unserved"]
    srv_ilp0 = df[df.method == "ilp_rho0"].set_index(["seed", "demand_mult"])["n_unserved"]
    if (srv_ilp0 > srv_ilp.reindex(srv_ilp0.index)).any():
        anomalies.append("- rho = 0 ILP serves fewer orders than the rho = 0.5 ILP in some run (relaxation should not reduce service).")
    if ilp_kwh == 0 and ilp_transfers == 0:
        anomalies.append("- The ILP never charges (C_elec = 0, kWh = 0) and never uses a transfer in any run: the charging / "
                         "transfer part of the model is feasible but non-binding on this family (12 spares, H = 24); the "
                         "baseline's small C_elec comes from its ASAP charging rule, not from need.")
    if zone_identical:
        anomalies.append("- `baseline_zone` reproduces `baseline` exactly in every run (counter-intuitive but explained: the "
                         "nearest-by-tau rule already prefers the same-zone bike); the zone map itself decodes correctly.")
    if not anomalies:
        anomalies.append("- none")
    md.extend(anomalies)
    md.append("\n## Figures\n")
    md.append("- `cost_components.png`: stacked cost components per method, one panel per demand level (means over seeds).")
    md.append("- `improvement_vs_demand.png`: relative improvement vs demand multiplier with 95 % CI, one line per comparison.")
    md.append("- `gap_decomposition_rho0.png`: baseline-minus-ILP gap by component (rho = 0 headline pair).")
    md.append("\nFiles: `results.csv` (one row per run), `improvement.csv`, `gap_decomposition_rho0.csv`, "
              "`gap_decomposition_rho05.csv`, `dispatch_decomposition.csv`, `instances/*.json`.")
    path = os.path.join(out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


def analyse(out_dir: str, wall: float, time_limit: float) -> None:
    """Figures + RESULTS.md from ``results.csv`` (re-runnable without solving)."""
    df = pd.read_csv(os.path.join(out_dir, "results.csv"))
    plot_cost_components(df, os.path.join(out_dir, "cost_components.png"),
                         ["baseline", "baseline_opp", "baseline_zone", "ilp_fixed_arcs", "ilp_fixed_assign", "ilp", "ilp_rho0"])
    pairs = [("ILP (rho=0) vs baseline [headline]", "baseline_rho0", "ilp_rho0"),
             ("ILP (rho=0.5) vs baseline", "baseline", "ilp"),
             ("ILP fixed assignment vs baseline", "baseline", "ilp_fixed_assign"),
             ("ILP fixed arcs vs baseline", "baseline", "ilp_fixed_arcs")]
    plot_improvement(improvement_table(df, pairs), os.path.join(out_dir, "improvement_vs_demand.png"))
    plot_gap_decomposition(gap_decomposition(df, "baseline_rho0", "ilp_rho0"),
                           os.path.join(out_dir, "gap_decomposition_rho0.png"),
                           "Baseline minus ILP (rho = 0) by cost component")
    write_results_md(df, out_dir, wall, time_limit)


def main(seeds: Sequence[int], mults: Sequence[float], time_limit: float, out_dir: str,
         analyse_only: bool = False) -> None:
    """Run every method on every ``(seed, mult)`` instance, saving ``results.csv`` after
    each instance, then build figures and ``RESULTS.md``."""
    C.ensure_dir(out_dir)
    inst_dir = C.ensure_dir(os.path.join(out_dir, "instances"))
    csv_path = os.path.join(out_dir, "results.csv")
    t_start = time.perf_counter()
    if not analyse_only:
        rows: List[Dict[str, Any]] = []
        for mult in mults:
            for seed in seeds:
                t0 = time.perf_counter()
                print(f"[{time.strftime('%H:%M:%S')}] demand x{mult:g} (|I|={DEMAND[mult]}) seed {seed}", flush=True)
                rows += run_instance(seed, mult, time_limit, inst_dir)
                C.write_csv(rows, csv_path)
                print(f"  instance done in {time.perf_counter() - t0:.0f}s, elapsed {(time.perf_counter() - t_start) / 60:.1f} min",
                      flush=True)
        wall = time.perf_counter() - t_start
        with open(os.path.join(out_dir, "wall_time.json"), "w") as fh:
            json.dump({"wall_s": wall, "time_limit": time_limit, "seeds": list(seeds), "mults": list(mults)}, fh)
    else:
        with open(os.path.join(out_dir, "wall_time.json")) as fh:
            wall = json.load(fh)["wall_s"]
    analyse(out_dir, wall, time_limit)
    print(f"done: {out_dir}  ({wall / 60:.1f} min)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    ap.add_argument("--mults", type=float, nargs="+", default=sorted(DEMAND))
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--analyse-only", action="store_true", help="rebuild figures / RESULTS.md from results.csv")
    args = ap.parse_args()
    main(args.seeds, args.mults, args.time_limit, args.out, args.analyse_only)
