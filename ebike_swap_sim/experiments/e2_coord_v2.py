"""Experiment E2, baseline re-evaluation after the policy fixes (reviewer F1-F6).

Why a v2
--------
The event-driven baseline of :mod:`ebike_swap_sim.baseline` was changed after
``outputs/e2_coord/RESULTS.md`` was written: just-in-time dispatch (F1), the
dead-zone swap rule after a reach refusal (F2), the RESERVE / informed variants
(F3, F6) and the explicit gap conventions (F4).  The ILP side (objective,
constraints, arc builder defaults) is untouched, so the ILP rows of
``outputs/e2_coord/results.csv`` remain valid.  This script therefore

1. reloads the 15 saved instances (``outputs/e2_coord/instances/*.json``; three
   demand levels x five seeds) and checks that they are byte-identical to what
   :func:`experiments.e2_coord.make_instance` generates;
2. rebuilds the arc library with the same pruning (reposition targets =
   restaurants + facilities + depots, ``tau_max = 4``, ``start_slack = 6``,
   lossless ``reachable = True``) and checks ``len(lib)`` against ``n_arcs`` of
   the stored rows;
3. re-runs ONLY the baseline side -- the fixed default policy, the legacy
   behaviour (``jit_dispatch = False``, ``swap_on_reach_refusal = False``; must
   reproduce the stored ``baseline`` rows exactly), ``baseline_reserve``,
   ``baseline_informed``, ``baseline_reorder`` (REORDER_POINT; the instances
   have 12 site <-> site shuttles) and ``baseline_zone`` -- with
   :func:`experiments.e2_coord.run_baseline`, so the rows have the columns of
   ``results.csv``;
4. certifies MIP-start acceptance of the new default and RESERVE schedules with
   the fix-and-solve certificate of :meth:`ebike_swap_sim.ilp.ILPModel.verify_mip_start`
   (all variables fixed to the start, Gurobi solve, ``OutputFlag 0``, ``Threads 4``,
   ``TimeLimit 120``) under (a) the written model (``rho = 0.5``, ``R_end_j = 1``;
   (17)-(18) active) and (b) the fully relaxed end targets of
   :func:`experiments.common.relax_end_targets` (``rho = 0`` **and** ``R_end_j = 0``).
   The free ILP is NOT re-solved;
5. recomputes the comparison tables against the stored ``ilp`` (written model)
   and ``ilp_rho0`` (``rho = 0``, ``R_end_j = 1``) rows: relative improvement
   (mean, 95 % t-CI) per demand level, both gap conventions of
   :func:`experiments.common.gap_definitions` (headline ``(baseline - ILP) /
   baseline``), the component decomposition of the gap, service / response /
   lateness / km / swap metrics and the legacy-vs-new baseline difference.

Caveat on the relaxed control: ``ilp_rho0`` was solved with ``R_end_j = 1`` kept,
so its objective is an upper bound on the optimum under the fully relaxed end
targets; the reported improvement of the fully relaxed ILP over the baseline is
therefore a lower bound (the ILP met (17) at zero measurable cost in E2, see
``RESULTS.md``).  The chained dispatch decomposition (``ilp_fixed_arcs`` /
``ilp_fixed_assign``) was computed with the *legacy* baseline's dispatch fixed
and is not recomputed here (it would need new ILP solves).

Outputs (``outputs/e2_coord_v2/``; inputs are read from ``outputs/e2_coord/`` whose
``RESULTS.md`` / ``results.csv`` / ``instances`` are left untouched):
``RESULTS_v2.md``, ``results_v2.csv`` (new baseline rows + the unchanged ILP rows,
column ``source``), ``improvement_v2.csv``, ``gap_decomposition_v2_rho0.csv``,
``gap_decomposition_v2_rho05.csv``, ``per_instance_v2.csv``,
``legacy_vs_new_v2.csv``, ``mip_start_v2.csv``, ``improvement_vs_demand_v2.png``,
``gap_decomposition_v2.png``, ``cost_components_v2.png``.

Run from ``ebike_swap_sim/`` (a few minutes; 30 model builds + certificates)::

    PYTHONPATH=. python3 experiments/e2_coord_v2.py [--src outputs/e2_coord] [--out outputs/e2_coord_v2] [--no-certify]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import ArcLibrary, Instance, Schedule, build_arcs  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import e2_coord as E  # noqa: E402

#: inputs (stored instances + results.csv) of the E2 run
SRC_DIR = E.OUT_DIR
#: outputs of this re-evaluation (a separate directory: several v2 re-runs share the
#: ``outputs/e2_coord`` tree, and files named ``*_v2`` there were being overwritten)
OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e2_coord_v2")
CERT_TIME_LIMIT = 120.0
#: baseline variants re-run (names of :data:`experiments.common.BASELINE_VARIANTS`)
VARIANTS = ["baseline", "baseline_legacy", "baseline_reserve", "baseline_informed",
            "baseline_reorder", "baseline_zone"]
#: schedules whose MIP-start acceptance is certified with the fix-and-solve solve
CERTIFY = ["baseline", "baseline_reserve", "baseline_legacy"]
#: ILP rows of ``results.csv`` reused unchanged
ILP_METHODS = ["ilp", "ilp_rho0", "ilp_fixed_arcs", "ilp_fixed_assign"]
METHOD_ORDER = VARIANTS + ["baseline_old"] + ILP_METHODS
COMPONENTS = E.COMPONENTS
PALETTE = E.PALETTE
SHORT = {"baseline": "Baseline v2 (fixed)", "baseline_legacy": "Baseline legacy", "baseline_reserve": "Baseline RESERVE",
         "baseline_informed": "Baseline informed", "baseline_reorder": "Baseline REORDER_POINT",
         "baseline_zone": "Baseline zone", "baseline_old": "Baseline (stored, legacy)",
         "ilp": "ILP (rho = 0.5)", "ilp_rho0": "ILP (rho = 0)", "ilp_fixed_arcs": "ILP, legacy arcs fixed",
         "ilp_fixed_assign": "ILP, legacy assignment fixed"}


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def load_instances(inst_dir: str) -> List[Instance]:
    """The saved E2 instances (``e2-K10-I*-seed*.json``, rho0 copies excluded), each
    checked to be byte-identical to :func:`experiments.e2_coord.make_instance` of its
    ``(seed, demand_mult)`` meta (``Instance.to_json`` equality)."""
    out = []
    for path in sorted(glob.glob(os.path.join(inst_dir, "e2-K10-I*-seed*.json"))):
        if path.endswith("-rho0.json"):
            continue
        inst = Instance.load(path)
        regen = E.make_instance(int(inst.meta["seed"]), float(inst.meta["demand_mult"]))
        if regen.to_json() != inst.to_json():
            raise RuntimeError(f"{path} differs from the regenerated instance; refusing to compare")
        inst.meta["instance_file"] = os.path.basename(path)
        out.append(inst)
    if len(out) != 15:
        warnings.warn(f"expected 15 instances, found {len(out)}", UserWarning, stacklevel=2)
    return sorted(out, key=lambda i: (float(i.meta["demand_mult"]), int(i.meta["seed"])))


# ---------------------------------------------------------------------------
# MIP-start certificates
# ---------------------------------------------------------------------------
def certify_start(mdl: Any, sched: Schedule, time_limit: float = CERT_TIME_LIMIT) -> Dict[str, Any]:
    """Fix-and-solve certificate of ``sched`` on the built :class:`ILPModel` ``mdl``:
    :meth:`ILPModel.set_mip_start` (prices and checks the start with ``evaluate``)
    followed by :meth:`ILPModel.verify_mip_start` with ``time_limit`` (every variable
    fixed to the start, Gurobi solve, bounds restored).  Returns ``{'accepted',
    'status', 'obj', 'start_obj', 'start_check_ok', 'start_violations', 'seconds'}``."""
    t0 = time.perf_counter()
    info = mdl.set_mip_start(sched, verify=False)
    ok, obj, status = mdl.verify_mip_start(time_limit=time_limit)
    return {"accepted": bool(ok), "status": status, "obj": obj, "start_obj": info["start_obj"],
            "start_check_ok": info["start_check_ok"], "start_violations": info["start_violations"],
            "seconds": time.perf_counter() - t0}


def run_instance(inst: Instance, stored: pd.DataFrame, certify: bool) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """All :data:`VARIANTS` on one instance (+ MIP-start certificates of :data:`CERTIFY`).

    Returns ``(rows, cert_rows)``: ``rows`` have the ``results.csv`` columns of
    :func:`experiments.e2_coord.run_baseline` plus the policy flags
    (``jit_dispatches``, ``reach_refusals``, ``reach_sent_to_swap``,
    ``late_trips_suppressed``, ``stock_aware_reroutes``, ``n_transfers_used``,
    ``variant_params``) and, for the certified variants, ``start_accepted_written``
    / ``start_accepted_relaxed`` (+ status / objective columns); ``cert_rows`` is the
    long form (one row per schedule x model).  Asserts: library size equals the
    stored ``n_arcs``; ``baseline_legacy`` reproduces the stored ``baseline`` row
    (total, travel, unserved, swaps) to 1e-9; the baseline cost does not depend on
    ``rho`` / ``R_end`` (same schedule on the relaxed copy)."""
    from ebike_swap_sim import ilp

    name = inst.meta["name"]
    old = stored[(stored.name == name)]
    old_base = old[old.method == "baseline"].iloc[0]
    pruning = C.pruning_for(inst, reachable=True)
    lib, build_t = C.build_library(inst, pruning)
    assert len(lib) == int(old_base["n_arcs"]), f"{name}: library {len(lib)} != stored n_arcs {old_base['n_arcs']}"

    rows: List[Dict[str, Any]] = []
    scheds: Dict[str, Schedule] = {}
    for variant in VARIANTS:
        params = C.baseline_variant_params(variant, inst)
        row, sched = E.run_baseline(inst, lib, params, variant)
        fl = sched.meta["flags"]
        row.update({
            "source": "rerun_v2", "lib_build_time_s": build_t, "variant_params": json.dumps(params, sort_keys=True),
            "jit_dispatches": int(fl.get("jit_dispatches", 0) or 0),
            "reach_refusals": int((fl.get("reach_refusals") or {}).get("count", 0) or 0),
            "reach_sent_to_swap": int((fl.get("reach_refusals") or {}).get("bikes_sent_to_swap", 0) or 0),
            "late_trips_suppressed": int(fl.get("late_trips_suppressed", 0) or 0),
            "stock_aware_reroutes": int(fl.get("stock_aware_reroutes", 0) or 0),
            "n_transfers_used": int(fl.get("n_transfers_used", 0) or 0),
            "max_need": fl.get("max_need"), "q_thr": fl.get("q_thr"),
        })
        rows.append(row)
        scheds[variant] = sched
    legacy = next(r for r in rows if r["method"] == "baseline_legacy")
    for col in ("total", "C_travel", "unserved", "n_unserved", "n_swaps", "bike_km", "viol_17", "viol_18"):
        assert abs(float(legacy[col]) - float(old_base[col])) < 1e-9, \
            f"{name}: legacy flags do not reproduce stored baseline {col}: {legacy[col]} vs {old_base[col]}"

    cert_rows: List[Dict[str, Any]] = []
    if certify:
        relaxed = C.relax_end_targets(inst)
        lib_rel = build_arcs(relaxed, **lib.options)
        assert len(lib_rel) == len(lib), "rho / R_end do not enter the arc rules"
        models = {
            "written": ilp.build_model(inst, lib, threads=C.THREADS, time_limit=CERT_TIME_LIMIT),
            "relaxed": ilp.build_model(relaxed, lib_rel, threads=C.THREADS, time_limit=CERT_TIME_LIMIT),
        }
        for variant in CERTIFY:
            row = next(r for r in rows if r["method"] == variant)
            params = C.baseline_variant_params(variant, inst)
            for model_name, mdl in models.items():
                if model_name == "written":
                    sched = scheds[variant]
                else:  # same policy on the relaxed copy (its own library object; ids coincide)
                    sched, _ = __import__("ebike_swap_sim").baseline.run_baseline(relaxed, lib_rel, params)
                    assert abs(C.cost(relaxed, lib_rel, sched)["total"] - row["total"]) < 1e-9, \
                        f"{name}/{variant}: baseline cost depends on rho / R_end"
                cert = certify_start(mdl, sched)
                row.update({f"start_accepted_{model_name}": cert["accepted"],
                            f"start_status_{model_name}": cert["status"],
                            f"start_obj_{model_name}": cert["obj"],
                            f"start_check_ok_{model_name}": cert["start_check_ok"],
                            f"cert_seconds_{model_name}": cert["seconds"]})
                cert_rows.append({"name": name, "seed": inst.meta["seed"], "demand_mult": inst.meta["demand_mult"],
                                  "method": variant, "model": model_name,
                                  "rho": (inst.rho if model_name == "written" else 0.0),
                                  "R_end": (inst.facility(inst.S[0]).R_end if model_name == "written" else 0),
                                  "viol_17": row["viol_17"], "viol_18": row["viol_18"],
                                  "check_families": row["check_families"], **cert})
        for mdl in models.values():
            mdl.model.dispose()
            mdl.env.dispose()
    return rows, cert_rows


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def method_means(df: pd.DataFrame, cols: Sequence[str], methods: Sequence[str]) -> pd.DataFrame:
    """Mean of ``cols`` over seeds per ``(demand_mult, method)`` in ``methods`` order."""
    sub = df[df.method.isin(methods)]
    g = sub.groupby(["demand_mult", "method"])[list(cols)].mean(numeric_only=True).reset_index()
    g["method"] = pd.Categorical(g["method"], list(methods), ordered=True)
    return g.sort_values(["demand_mult", "method"]).reset_index(drop=True)


def legacy_vs_new(df: pd.DataFrame, new: str = "baseline", old: str = "baseline_legacy") -> pd.DataFrame:
    """Per demand level (and pooled): mean legacy-minus-new differences of total cost,
    travel km, unserved count and swaps with 95 % t-CI, the share of instances where
    the new policy is not worse, and the share of dispatches the JIT rule changed
    (``jit_dispatches / n_served`` of the new policy)."""
    p = E.paired(df, old, new)
    dn = df[df.method == new].set_index(["seed", "demand_mult"])
    do = df[df.method == old].set_index(["seed", "demand_mult"])
    idx = pd.MultiIndex.from_frame(p[["seed", "demand_mult"]])
    p["d_km"] = do.loc[idx, "bike_km"].to_numpy() - dn.loc[idx, "bike_km"].to_numpy()
    p["d_unserved_n"] = do.loc[idx, "n_unserved"].to_numpy() - dn.loc[idx, "n_unserved"].to_numpy()
    p["d_swaps"] = do.loc[idx, "n_swaps"].to_numpy() - dn.loc[idx, "n_swaps"].to_numpy()
    p["jit"] = dn.loc[idx, "jit_dispatches"].to_numpy()
    p["served_new"] = dn.loc[idx, "n_served"].to_numpy()
    p["reach_refusals"] = dn.loc[idx, "reach_refusals"].to_numpy()
    recs = []
    for mult in sorted(E.DEMAND) + ["all"]:
        s = p if mult == "all" else p[p.demand_mult == mult]
        m, hw, n = E.ci95(s["abs_gain"].tolist())
        mr, hr, _ = E.ci95(s["rel_impr"].tolist())
        mk, hk, _ = E.ci95(s["d_km"].tolist())
        mu, hu, _ = E.ci95(s["d_unserved_n"].tolist())
        recs.append({"demand_mult": mult, "n": n,
                     "legacy_total_mean": s["total_a"].mean(), "new_total_mean": s["total_b"].mean(),
                     "cost_saving_mean": m, "cost_saving_ci95": hw,
                     "cost_saving_pct_mean": mr, "cost_saving_pct_ci95": hr,
                     "km_saved_mean": mk, "km_saved_ci95": hk,
                     "unserved_reduction_mean": mu, "unserved_reduction_ci95": hu,
                     "swaps_change_mean": -s["d_swaps"].mean(),
                     "new_not_worse_share": float((s["abs_gain"] >= -1e-9).mean()),
                     "new_better_n": int((s["abs_gain"] > 1e-9).sum()), "new_worse_n": int((s["abs_gain"] < -1e-9).sum()),
                     "jit_dispatches_mean": s["jit"].mean(),
                     "jit_share_of_dispatches_pct": 100.0 * s["jit"].sum() / max(1, s["served_new"].sum()),
                     "reach_refusals_mean": s["reach_refusals"].mean()})
    return pd.DataFrame(recs)


def per_instance_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per instance: legacy / new / RESERVE baseline totals and components,
    ILP totals (written model and rho = 0), both gap conventions for the new baseline
    (:func:`experiments.common.gap_definitions`) and the MIP-start certificates."""
    piv = {m: df[df.method == m].set_index(["demand_mult", "seed"]).sort_index() for m in
           ["baseline", "baseline_legacy", "baseline_reserve", "ilp", "ilp_rho0"]}
    recs = []
    for key in piv["baseline"].index:
        b, lg, rs = piv["baseline"].loc[key], piv["baseline_legacy"].loc[key], piv["baseline_reserve"].loc[key]
        il = piv["ilp"].loc[key] if key in piv["ilp"].index else None
        i0 = piv["ilp_rho0"].loc[key] if key in piv["ilp_rho0"].index else None
        g05 = C.gap_definitions(float(b["total"]), None if il is None else float(il["total"]))
        g0 = C.gap_definitions(float(b["total"]), None if i0 is None else float(i0["total"]))
        gl = C.gap_definitions(float(lg["total"]), None if i0 is None else float(i0["total"]))
        recs.append({
            "name": b["name"], "demand_mult": key[0], "seed": key[1],
            "legacy_total": lg["total"], "new_total": b["total"], "reserve_total": rs["total"],
            "legacy_minus_new": lg["total"] - b["total"],
            "legacy_km": lg["bike_km"], "new_km": b["bike_km"], "legacy_unserved": lg["n_unserved"], "new_unserved": b["n_unserved"],
            "legacy_swaps": lg["n_swaps"], "new_swaps": b["n_swaps"], "new_jit_dispatches": b["jit_dispatches"],
            "new_reach_refusals": b["reach_refusals"], "new_C_elec": b["C_elec"], "new_response": b["response"],
            "new_lateness": b["lateness"],
            "ilp_total": None if il is None else il["total"], "ilp_status": None if il is None else il["status"],
            "ilp_rho0_total": None if i0 is None else i0["total"], "ilp_rho0_status": None if i0 is None else i0["status"],
            "gap_vs_baseline_pct_rho05": g05["gap_vs_baseline_pct"], "gap_vs_ilp_pct_rho05": g05["gap_vs_ilp_pct"],
            "gap_vs_baseline_pct_rho0": g0["gap_vs_baseline_pct"], "gap_vs_ilp_pct_rho0": g0["gap_vs_ilp_pct"],
            "legacy_gap_vs_baseline_pct_rho0": gl["gap_vs_baseline_pct"],
            "new_families": b["check_families"], "new_viol_17": b["viol_17"], "new_viol_18": b["viol_18"],
            "new_start_written": b.get("start_accepted_written"), "new_start_relaxed": b.get("start_accepted_relaxed"),
            "reserve_families": rs["check_families"],
            "reserve_start_written": rs.get("start_accepted_written"), "reserve_start_relaxed": rs.get("start_accepted_relaxed"),
        })
    return pd.DataFrame(recs)


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def plot_cost_components(df: pd.DataFrame, path: str, methods: Sequence[str]) -> str:
    """Stacked bars of the mean cost components (27)-(32) per method, one panel per
    demand level (same encoding as ``e2_coord.plot_cost_components``)."""
    comps = ["unserved", "response", "lateness", "C_travel", "C_elec", "C_reb", "C_setup"]
    names = {"unserved": "unserved P_i u_i (30)", "response": "response (31)", "lateness": "lateness (31)",
             "C_travel": "travel (29)", "C_elec": "electricity (28)", "C_reb": "transfers (32)",
             "C_setup": "setup (27), constant"}
    mults = sorted(E.DEMAND)
    means = method_means(df, comps + ["total"], methods)
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
        ax.set_xticklabels([SHORT.get(m, m) for m in methods], fontsize=7.5, rotation=35, ha="right",
                           rotation_mode="anchor")
        ax.set_title(f"demand x{mult:g}  (|I| = {E.DEMAND[mult]})", fontsize=10, color="#0b0b0b")
        E._style(ax)
    n_seeds = df["seed"].nunique()
    np.atleast_1d(axes)[0].set_ylabel(f"mean cost over {n_seeds} seeds (toy units)", fontsize=9)
    fig.suptitle("Cost components (27)-(32), fixed baseline (v2) vs legacy baseline vs ILP",
                 fontsize=11, x=0.01, ha="left", color="#0b0b0b")
    fig.legend(loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def _f(v: Any, d: int = 1) -> str:
    return C.fmt(float(v), d) if v is not None and not (isinstance(v, float) and math.isnan(v)) else "-"


def write_results_md(df: pd.DataFrame, certs: pd.DataFrame, out_dir: str, wall: float, certified: bool) -> str:
    """Compose ``RESULTS_v2.md`` (tables + interpretation) and the companion CSVs."""
    pairs = [("ILP (rho=0.5) vs baseline v2", "baseline", "ilp"),
             ("ILP (rho=0) vs baseline v2 [headline]", "baseline", "ilp_rho0"),
             ("ILP (rho=0.5) vs baseline legacy", "baseline_legacy", "ilp"),
             ("ILP (rho=0) vs baseline legacy", "baseline_legacy", "ilp_rho0"),
             ("ILP (rho=0.5) vs baseline RESERVE", "baseline_reserve", "ilp"),
             ("ILP (rho=0) vs baseline RESERVE", "baseline_reserve", "ilp_rho0"),
             ("baseline v2 vs baseline legacy", "baseline_legacy", "baseline"),
             ("baseline RESERVE vs baseline v2", "baseline", "baseline_reserve"),
             ("baseline informed vs baseline v2", "baseline", "baseline_informed"),
             ("baseline REORDER_POINT vs baseline v2", "baseline", "baseline_reorder"),
             ("baseline zone vs baseline v2", "baseline", "baseline_zone")]
    imp = E.improvement_table(df, pairs)
    imp.to_csv(os.path.join(out_dir, "improvement_v2.csv"), index=False)
    dec0 = E.gap_decomposition(df, "baseline", "ilp_rho0")
    dec05 = E.gap_decomposition(df, "baseline", "ilp")
    dec0.to_csv(os.path.join(out_dir, "gap_decomposition_v2_rho0.csv"), index=False)
    dec05.to_csv(os.path.join(out_dir, "gap_decomposition_v2_rho05.csv"), index=False)
    lvn = legacy_vs_new(df)
    lvn.to_csv(os.path.join(out_dir, "legacy_vs_new_v2.csv"), index=False)
    per = per_instance_table(df)
    per.to_csv(os.path.join(out_dir, "per_instance_v2.csv"), index=False)
    if len(certs):
        certs.to_csv(os.path.join(out_dir, "mip_start_v2.csv"), index=False)

    cost_cols = ["total"] + COMPONENTS
    metric_cols = ["served_share", "mean_response_h", "mean_lateness_h", "max_lateness_h", "n_late",
                   "bike_km", "n_swaps", "queue_wait_slots", "kwh_purchased", "transfers_used", "end_full_total"]
    flag_cols = ["jit_dispatches", "reach_refusals", "reach_sent_to_swap", "late_trips_suppressed",
                 "stock_aware_reroutes", "n_transfers_used", "viol_17", "viol_18"]
    table_methods = VARIANTS + ["ilp", "ilp_rho0"]
    means_cost = method_means(df, cost_cols, table_methods)
    means_met = method_means(df, metric_cols, table_methods)
    means_flags = method_means(df, flag_cols, VARIANTS)

    def row(label: str, mult: Any) -> pd.Series:
        return imp[(imp.comparison == label) & (imp.demand_mult == mult)].iloc[0]

    head = row("ILP (rho=0) vs baseline v2 [headline]", "all")
    head05 = row("ILP (rho=0.5) vs baseline v2", "all")
    leg0 = row("ILP (rho=0) vs baseline legacy", "all")
    leg05 = row("ILP (rho=0.5) vs baseline legacy", "all")
    res0 = row("ILP (rho=0) vs baseline RESERVE", "all")
    v2l = row("baseline v2 vs baseline legacy", "all")
    per_head = {m: row("ILP (rho=0) vs baseline v2 [headline]", m) for m in sorted(E.DEMAND)}
    per_leg = {m: row("ILP (rho=0) vs baseline legacy", m) for m in sorted(E.DEMAND)}
    base = df[df.method == "baseline"]
    lgc = df[df.method == "baseline_legacy"]
    rsv = df[df.method == "baseline_reserve"]
    n17, n18 = int((base.viol_17 > 0).sum()), int((base.viol_18 > 0).sum())
    n17l, n18l = int((lgc.viol_17 > 0).sum()), int((lgc.viol_18 > 0).sum())
    n17r, n18r = int((rsv.viol_17 > 0).sum()), int((rsv.viol_18 > 0).sum())
    lvn_all = lvn[lvn.demand_mult == "all"].iloc[0]
    uns_share = float(dec0[dec0.demand_mult == "all"]["unserved_share_pct"].iloc[0])
    uns_by = {m: float(dec0[dec0.demand_mult == m]["unserved_share_pct"].iloc[0]) for m in sorted(E.DEMAND)}
    srv = means_met.set_index(["demand_mult", "method"])["served_share"]
    km = means_met.set_index(["demand_mult", "method"])["bike_km"]
    resp = means_met.set_index(["demand_mult", "method"])["mean_response_h"]
    late = means_met.set_index(["demand_mult", "method"])["mean_lateness_h"]
    sw = means_met.set_index(["demand_mult", "method"])["n_swaps"]

    def g(series: pd.Series, mult: float, m: str) -> float:
        return float(series.get((mult, m), float("nan")))

    acc: Dict[str, Dict[str, int]] = {}
    if certified:
        for m in CERTIFY:
            sub = df[df.method == m]
            acc[m] = {"written": int(sub["start_accepted_written"].eq(True).sum()),
                      "relaxed": int(sub["start_accepted_relaxed"].eq(True).sum()),
                      "n": len(sub)}

    md: List[str] = []
    md.append("# E2 (v2) -- fixed event-driven baseline vs the stored coordinated ILP\n")
    md.append(f"Re-evaluation of `RESULTS.md` after the baseline fixes (reviewer F1 just-in-time dispatch, F2 dead-zone "
              f"swap after a reach refusal, F3/F6 RESERVE and informed variants, F4 explicit gap conventions). The "
              f"{base.shape[0]} instances are the stored `instances/*.json` (10 bikes, |I| in {{22, 30, 45}}, H = 24 x 5 min, "
              f"L = 12, 3 co-located fixed sites, 12 site <-> site shuttles, seeds {sorted(df.seed.unique().tolist())}), "
              f"each verified byte-identical to the generator output; the arc library is rebuilt with the same pruning "
              f"(reposition targets = restaurants + facilities + depots, tau_max = 4, start_slack = 6, reachable = True) and "
              f"its size equals the stored `n_arcs` in every instance. **Only the baseline side was re-run**; the `ilp` "
              f"(rho = 0.5, R_end = 1) and `ilp_rho0` (rho = 0, R_end = 1) rows are taken unchanged from `results.csv` "
              f"(Gurobi 13, TimeLimit 240 s; 4 of 30 solves at x1.5 ended at the limit with gap <= 2.1 %). The legacy flags "
              f"(`jit_dispatch = False`, `swap_on_reach_refusal = False`) reproduce the stored `baseline` rows exactly "
              f"(asserted on total, travel, unserved, swaps, (17)/(18) shortfalls in all {base.shape[0]} instances), so the "
              f"old and new baselines are compared on the same schedules. MIP-start acceptance is certified with the "
              f"fix-and-solve solve (x, u, c, h, z, n fixed; OutputFlag 0, Threads 4, TimeLimit {CERT_TIME_LIMIT:.0f} s) under "
              f"the written model and under the fully relaxed end targets (`common.relax_end_targets`: rho = 0 AND R_end_j = 0); "
              f"the free ILP was not re-solved. Wall time {wall / 60:.1f} min.\n")

    md.append("## Headline\n")
    md.append(f"**Baseline v2 vs `ilp_rho0` (headline gap = (baseline - ILP) / baseline): {head.rel_impr_mean_pct:.1f} % "
              f"(95 % t-CI +/- {head.rel_impr_ci95_pct:.1f}, n = {int(head.n_seeds)})**, by demand "
              + ", ".join(f"x{m:g}: {per_head[m].rel_impr_mean_pct:.1f} +/- {per_head[m].rel_impr_ci95_pct:.1f} %"
                          for m in sorted(E.DEMAND))
              + f"; vs the written model (`ilp`, rho = 0.5): {head05.rel_impr_mean_pct:.1f} % (+/- {head05.rel_impr_ci95_pct:.1f}). "
              f"The legacy baseline gave {leg0.rel_impr_mean_pct:.1f} % (+/- {leg0.rel_impr_ci95_pct:.1f}) and "
              f"{leg05.rel_impr_mean_pct:.1f} % respectively, i.e. the fixes close {leg0.rel_impr_mean_pct - head.rel_impr_mean_pct:.1f} "
              f"points of the reported gap. Excluding the constant setup term (27) the operational-cost reduction is "
              f"{head.rel_impr_ex_setup_mean_pct:.1f} % (+/- {head.rel_impr_ex_setup_ci95_pct:.1f}). The fixed policy lowers the "
              f"baseline's own cost by {v2l.rel_impr_mean_pct:.1f} % on average (+/- {v2l.rel_impr_ci95_pct:.1f}; "
              f"{int(lvn_all.new_better_n)} instances better, {int(lvn_all.new_worse_n)} worse, "
              f"{int(lvn_all.n) - int(lvn_all.new_better_n) - int(lvn_all.new_worse_n)} unchanged), saves "
              f"{lvn_all.km_saved_mean:.1f} km of bike travel per instance (+/- {lvn_all.km_saved_ci95:.1f}; "
              f"{g(km, 1.0, 'baseline_legacy'):.1f} -> {g(km, 1.0, 'baseline'):.1f} km at base demand) and "
              f"{lvn_all.unserved_reduction_mean:.2f} unserved orders (+/- {lvn_all.unserved_reduction_ci95:.2f}); "
              f"{lvn_all.jit_share_of_dispatches_pct:.0f} % of the new baseline's dispatches are just-in-time starts (the "
              f"nearest idle bike was blocked only by the dominance rule; under the old rule each such case went either to a "
              f"farther bike or to the same bike one or more boundaries later, so this is an upper bound on the reviewer's 23 % "
              f"'farther bike' share). "
              f"The gap is still dominated by unserved orders ({uns_share:.0f} % of the baseline-minus-ILP difference; "
              + ", ".join(f"x{m:g} {uns_by[m]:.0f} %" for m in sorted(E.DEMAND)) + ").")
    if certified:
        a, r = acc["baseline"], acc["baseline_reserve"]
        md.append(f" MIP start: the new default schedule is accepted under the written model in {a['written']} of {a['n']} "
                  f"instances (it violates (18) in {n18} and (17) in {n17}; legacy: {n18l} / {n17l}) and under the fully "
                  f"relaxed end targets in {a['relaxed']} of {a['n']}; the RESERVE variant is accepted in {r['written']} / "
                  f"{r['n']} (written) and {r['relaxed']} / {r['n']} (relaxed) and costs "
                  f"{-row('baseline RESERVE vs baseline v2', 'all').rel_impr_mean_pct:+.1f} % relative to the default "
                  f"(negative = cheaper).")
    md.append("\n")

    md.append("## Relative improvement over the baseline variants (mean over seeds, 95 % t-CI)\n")
    md.append(C.markdown_table(imp, ["comparison", "demand_mult", "n_seeds", "rel_impr_mean_pct", "rel_impr_ci95_pct",
                                     "rel_impr_lo_pct", "rel_impr_hi_pct", "abs_gain_mean",
                                     "rel_impr_ex_setup_mean_pct", "rel_impr_ex_setup_ci95_pct"], digits=2))
    md.append("\n`rel_impr` = (cost_A - cost_B) / cost_A in % for the pair 'B vs A' (`common.gap_definitions` "
              "`gap_vs_baseline_pct`, the headline convention); `rel_impr_ex_setup` divides by cost_A minus the constant "
              f"setup term (27) (C_setup = {float(df['C_setup'].iloc[0]):.0f}); negative = B is worse than A. The ILP rows "
              "are the stored solutions; `ilp_rho0` kept R_end_j = 1, so against the fully relaxed ILP the improvement is at "
              "least the value shown.\n")

    md.append("## Legacy vs fixed baseline (legacy minus new, mean over seeds, 95 % t-CI)\n")
    md.append(C.markdown_table(lvn, ["demand_mult", "n", "legacy_total_mean", "new_total_mean", "cost_saving_mean",
                                     "cost_saving_ci95", "cost_saving_pct_mean", "cost_saving_pct_ci95", "km_saved_mean",
                                     "km_saved_ci95", "unserved_reduction_mean", "unserved_reduction_ci95", "swaps_change_mean",
                                     "new_better_n", "new_worse_n", "jit_dispatches_mean", "jit_share_of_dispatches_pct",
                                     "reach_refusals_mean"], digits=2))
    md.append("\n`jit_share_of_dispatches_pct` = just-in-time dispatches / served orders of the new policy (dispatches in "
              "which the nearest idle bike was blocked only by the ILP's dominance rule and now waits and starts at "
              "a_i - tau_r); `reach_refusals_mean` = reach-only refusals per run (the dead-zone rule sends such bikes to swap).\n")

    md.append("## Per instance: legacy / new / RESERVE baseline, stored ILPs, both gap conventions, MIP-start certificates\n")
    per_cols = ["name", "legacy_total", "new_total", "reserve_total", "legacy_km", "new_km", "legacy_unserved", "new_unserved",
                "legacy_swaps", "new_swaps", "new_jit_dispatches", "new_reach_refusals", "ilp_total", "ilp_rho0_total",
                "gap_vs_baseline_pct_rho0", "gap_vs_ilp_pct_rho0", "legacy_gap_vs_baseline_pct_rho0", "new_families",
                "new_start_written", "new_start_relaxed", "reserve_families", "reserve_start_written", "reserve_start_relaxed"]
    md.append(C.markdown_table(per, per_cols, digits=1))
    md.append("\n`gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline), `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP "
              "(baseline excess over the optimum); `*_start_written` / `*_start_relaxed` = fix-and-solve certificate of the "
              "schedule as MIP start under the written model / under rho = 0 and R_end = 0.\n")

    md.append("## Cost (26) and components (27)-(32): mean over seeds per demand level and method\n")
    md.append(C.markdown_table(means_cost, ["demand_mult", "method"] + cost_cols, digits=2))
    md.append("\n## Service / operations metrics: mean over seeds\n")
    md.append(C.markdown_table(means_met, ["demand_mult", "method"] + metric_cols, digits=3))
    md.append("\n## Policy flags of the baseline variants: mean over seeds\n")
    md.append(C.markdown_table(means_flags, ["demand_mult", "method"] + flag_cols, digits=2))
    md.append("\n`viol_17` = summed local end-stock shortfall (17), `viol_18` = global shortfall (18) (both reported, not "
              "enforced, by the policy); `late_trips_suppressed` and `stock_aware_reroutes` are the informed / RESERVE rules.\n")

    md.append("## Gap decomposition (baseline v2 - ILP) by component\n")
    dec_cols = ["demand_mult", "total_gap"] + [c for c in COMPONENTS if c != "C_setup"] + [
        "unserved_share_pct", "response_share_pct", "lateness_share_pct", "C_travel_share_pct"]
    md.append("rho = 0 pair (`ilp_rho0`):\n")
    md.append(C.markdown_table(dec0.assign(demand_mult=dec0.demand_mult.map(E._mlabel)), dec_cols, digits=1))
    md.append("\nWritten model (`ilp`, rho = 0.5):\n")
    md.append(C.markdown_table(dec05.assign(demand_mult=dec05.demand_mult.map(E._mlabel)), dec_cols, digits=1))

    if certified and len(certs):
        md.append("\n## MIP-start certificates (fix-and-solve, Threads 4, TimeLimit 120 s)\n")
        summ = certs.groupby(["method", "model"]).agg(
            n=("accepted", "size"), accepted=("accepted", lambda s: int(s.sum())),
            check_ok=("start_check_ok", lambda s: int(s.sum())), seconds_mean=("seconds", "mean"),
            seconds_max=("seconds", "max")).reset_index()
        md.append(C.markdown_table(summ, list(summ.columns), digits=2))
        rej = certs[~certs.accepted.astype(bool)]
        if len(rej):
            md.append("\nRejected starts: " + "; ".join(
                f"{r.name_}/{r.method}/{r.model} ({r.status}, families {r.check_families})"
                for r in rej.rename(columns={"name": "name_"}).itertuples()) + ".")
        agree = bool(((certs.start_check_ok.astype(bool)) == certs.accepted.astype(bool)).all())
        md.append(f"\n`evaluate.check` (zero violations) and the Gurobi certificate "
                  f"{'agree on every schedule' if agree else 'DISAGREE on some schedule (see mip_start_v2.csv)'}.\n")

    md.append("## Interpretation\n")
    lines = []
    lines.append(f"The fixed baseline is a stronger opponent: its mean cost falls from {lvn_all.legacy_total_mean:.1f} to "
                 f"{lvn_all.new_total_mean:.1f} ({v2l.rel_impr_mean_pct:.1f} %), travel from {float(lgc.bike_km.mean()):.1f} to "
                 f"{float(base.bike_km.mean()):.1f} km and unserved orders from {float(lgc.n_unserved.mean()):.2f} to "
                 f"{float(base.n_unserved.mean()):.2f} per instance, so the ILP's headline advantage shrinks from "
                 f"{leg0.rel_impr_mean_pct:.1f} % to {head.rel_impr_mean_pct:.1f} % (rho = 0 pair) and from {leg05.rel_impr_mean_pct:.1f} % "
                 f"to {head05.rel_impr_mean_pct:.1f} % (written model), with CI half-widths of {head.rel_impr_ci95_pct:.1f} points.")
    lines.append(f"By demand level the ILP's gain over the new baseline is x0.75 {per_head[0.75].rel_impr_mean_pct:.1f} %, x1 "
                 f"{per_head[1.0].rel_impr_mean_pct:.1f} %, x1.5 {per_head[1.5].rel_impr_mean_pct:.1f} % (legacy: "
                 f"{per_leg[0.75].rel_impr_mean_pct:.1f} / {per_leg[1.0].rel_impr_mean_pct:.1f} / {per_leg[1.5].rel_impr_mean_pct:.1f} %): "
                 f"the JIT rule matters most where bikes are plentiful relative to orders and the prep time a_i - r_i is the binding "
                 f"delay; at x1.5 nearly every idle bike is dispatched anyway and the gap is set by how many orders fit into the horizon.")
    lines.append(f"The composition of the gap is unchanged in kind: {uns_share:.0f} % of the baseline-minus-ILP difference is the "
                 f"P_i = 100 penalty (served share {100 * g(srv, 1.0, 'baseline'):.0f} % vs {100 * g(srv, 1.0, 'ilp_rho0'):.0f} % at base "
                 f"demand, {100 * g(srv, 1.5, 'baseline'):.0f} % vs {100 * g(srv, 1.5, 'ilp_rho0'):.0f} % at x1.5); travel is now "
                 f"{g(km, 1.0, 'baseline'):.0f} km vs {g(km, 1.0, 'ilp_rho0'):.0f} km for the ILP at base demand (legacy "
                 f"{g(km, 1.0, 'baseline_legacy'):.0f} km), i.e. the 'farther bike' inefficiency the reviewer measured is gone from "
                 f"the baseline; the remaining travel gap ({g(km, 0.75, 'baseline') - g(km, 0.75, 'ilp_rho0'):.0f} km at x0.75 with an "
                 f"identical served share) is what coordinated assignment, swap placement and repositioning buy beyond nearest-bike "
                 f"dispatch, and at x1.5 it reverses because the ILP serves {100 * (g(srv, 1.5, 'ilp_rho0') - g(srv, 1.5, 'baseline')):.0f} "
                 f"points more of the orders; mean response per served "
                 f"order is {g(resp, 1.0, 'baseline'):.2f} h (legacy {g(resp, 1.0, 'baseline_legacy'):.2f}, ILP {g(resp, 1.0, 'ilp_rho0'):.2f}), "
                 f"mean lateness {g(late, 1.0, 'baseline'):.3f} h (ILP {g(late, 1.0, 'ilp_rho0'):.3f}).")
    lines.append(f"Swaps per run: baseline v2 {float(base.n_swaps.mean()):.1f} (legacy {float(lgc.n_swaps.mean()):.1f}, RESERVE "
                 f"{float(rsv.n_swaps.mean()):.1f}, ILP {float(df[df.method == 'ilp_rho0'].n_swaps.mean()):.1f}); the RESERVE variant "
                 f"suppresses {float(rsv.late_trips_suppressed.mean()):.1f} late swap trips per run and changes the cost by "
                 f"{-row('baseline RESERVE vs baseline v2', 'all').rel_impr_mean_pct:+.1f} % relative to the default (negative = cheaper), "
                 f"while leaving (17) violated in {n17r} and (18) in {n18r} of {len(rsv)} runs (default: {n17} / {n18}; legacy: {n17l} / {n18l}).")
    lines.append(f"REORDER_POINT transfers and zone dispatch change the default by "
                 f"{-row('baseline REORDER_POINT vs baseline v2', 'all').rel_impr_mean_pct:+.2f} % and "
                 f"{-row('baseline zone vs baseline v2', 'all').rel_impr_mean_pct:+.2f} % (12 spares for 10 bikes in a 2 h window leave "
                 f"the reorder rule nothing to ship; the nearest-by-tau rule already picks the same-zone bike), and the informed variant "
                 f"by {-row('baseline informed vs baseline v2', 'all').rel_impr_mean_pct:+.2f} %.")
    lines.append("What does not change: the ILP rows, the toy and p.7 reproductions, and the conclusion that on this 2-hour / 12-spare "
                 "family the gain sits in dispatch rather than in battery logistics (the stored fixed-dispatch ILPs recovered < 2 % of "
                 "the legacy gap; they were not re-solved against the new baseline, see Anomalies). Caveat: toy unit system (P_i = 100 "
                 "dominates), so the comparison is essentially one of service levels.")
    md.append(" ".join(lines) + "\n")

    md.append("## Anomalies and notes\n")
    an = []
    worse = per[per.legacy_minus_new < -1e-9]
    if len(worse):
        an.append("- The fixed policy is more expensive than the legacy one on " + ", ".join(
            f"{r.name} ({r.legacy_total:.1f} -> {r.new_total:.1f})" for r in worse.itertuples())
            + ": a greedy policy is not monotone in its rules (serving an extra order early changes which bikes are idle later); "
              "the reviewer predicted these swings.")
    if certified:
        rej_new = per[per.new_start_written == False]  # noqa: E712
        if len(rej_new):
            an.append(f"- New default schedule rejected as MIP start under the written model in {len(rej_new)} instances "
                      f"({', '.join(rej_new.name)}): end-target families {', '.join(rej_new.new_families)}; reported, not enforced "
                      f"(DECISIONS.md). Under the fully relaxed end targets it is accepted in {acc['baseline']['relaxed']} of "
                      f"{acc['baseline']['n']}.")
        rej_res = per[per.reserve_start_written == False]  # noqa: E712
        if len(rej_res):
            an.append(f"- RESERVE schedule rejected under the written model in {len(rej_res)} instances ({', '.join(rej_res.name)}; "
                      f"families {', '.join(rej_res.reserve_families)}). The reserve guard (`end_reserve_window = W = max sigma + 3 "
                      f"= {1 + C.END_WINDOW_SLACK} slots here, sigma_j = 1`) only refuses swaps inside the "
                      f"last W slots; a swap at t < H - W may still take the last full battery (on e2-K10-I30-seed3 site S1 goes 1 -> 0 "
                      f"at t = 18, window starts at t = 20) and a returned q = 1-2 battery needs L - q = 10-11 charging slots, so (17) "
                      f"cannot be restored by H. A window covering the charging lead time (about L - q_thr slots) or a stock-aware "
                      f"guard 'n_jLt - 1 >= R_end_j unless a charge completes by H' would be needed for a guaranteed (17)-feasible "
                      f"start; this is a limitation of the F3 variant in baseline.py / common.BASELINE_VARIANTS, not changed here.")
    an.append("- `ilp_rho0` was solved with rho = 0 but R_end_j = 1 (E2 run), not with the fully relaxed end targets of "
              "`common.relax_end_targets`; its objective bounds the fully relaxed optimum from above, so the headline improvement is "
              "a lower bound on the fair-control improvement (in E2 the ILP met (17) at zero measurable cost).")
    an.append("- `ilp_fixed_arcs` / `ilp_fixed_assign` fix the *legacy* baseline's dispatch; the chained dispatch decomposition of "
              "RESULTS.md is therefore not recomputed for the new baseline (requires new ILP solves).")
    bad = df[(df.method.isin(ILP_METHODS)) & (df.status != "OPTIMAL")]
    if len(bad):
        an.append("- Stored ILP runs not proven optimal: " + ", ".join(f"{r.name}/{r.method} ({r.status}, gap {float(r.gap):.4f})"
                                                                     for r in bad.itertuples()))
    ineq = per[(per.new_total < per.ilp_rho0_total - 1e-6) | (per.new_total < per.ilp_total - 1e-6)]
    if len(ineq):
        an.append("- Baseline v2 cheaper than a stored ILP on " + ", ".join(ineq.name) + " (would contradict optimality; check).")
    same_inf = per[(per.reserve_total == per.new_total)]
    inf_eq = int((df[df.method == "baseline_informed"].set_index(["seed", "demand_mult"])["total"]
                  - rsv.set_index(["seed", "demand_mult"])["total"]).abs().lt(1e-9).sum())
    an.append(f"- `baseline_informed` coincides with `baseline_reserve` in {inf_eq} of {len(rsv)} runs and `baseline_reserve` with the "
              f"default in {len(same_inf)}: with M_j = 1, sigma_j = 1 and three stocked sites the stock-aware re-routing never fires "
              f"and the two variants differ only through the (17) reserve guard.")
    md.extend(an)
    md.append("\n## Figures\n")
    md.append("- `improvement_vs_demand_v2.png`: relative improvement over the baseline variants vs demand multiplier (mean, 95 % CI).")
    md.append("- `gap_decomposition_v2.png`: baseline v2 minus ILP (rho = 0) by cost component.")
    md.append("- `cost_components_v2.png`: stacked cost components, fixed vs legacy vs RESERVE baseline vs stored ILPs.")
    md.append("\nFiles: `results_v2.csv` (new baseline rows, `source = rerun_v2`, plus the unchanged ILP rows, `source = results.csv`), "
              "`improvement_v2.csv`, `legacy_vs_new_v2.csv`, `per_instance_v2.csv`, `gap_decomposition_v2_rho0.csv`, "
              "`gap_decomposition_v2_rho05.csv`, `mip_start_v2.csv`, all in `outputs/e2_coord_v2/`. The E2 inputs in "
              "`outputs/e2_coord/` (`RESULTS.md`, `results.csv`, `instances/`, figures) are untouched.")
    path = os.path.join(out_dir, "RESULTS_v2.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


def analyse(df: pd.DataFrame, certs: pd.DataFrame, out_dir: str, wall: float, certified: bool) -> None:
    """Figures + ``RESULTS_v2.md`` from the combined frame."""
    plot_cost_components(df, os.path.join(out_dir, "cost_components_v2.png"),
                         ["baseline_legacy", "baseline", "baseline_reserve", "ilp", "ilp_rho0"])
    pairs = [("ILP (rho=0) vs baseline v2 [headline]", "baseline", "ilp_rho0"),
             ("ILP (rho=0.5) vs baseline v2", "baseline", "ilp"),
             ("ILP (rho=0) vs baseline legacy", "baseline_legacy", "ilp_rho0"),
             ("ILP (rho=0) vs baseline RESERVE", "baseline_reserve", "ilp_rho0"),
             ("baseline v2 vs baseline legacy", "baseline_legacy", "baseline")]
    imp_fig = E.improvement_table(df, pairs)
    # e2_coord.plot_improvement derives the seed count from max(n_seeds), which the pooled
    # 'all' row (n = 15) inflates; drop it (the plot ignores that row anyway)
    E.plot_improvement(imp_fig[imp_fig.demand_mult != "all"], os.path.join(out_dir, "improvement_vs_demand_v2.png"))
    E.plot_gap_decomposition(E.gap_decomposition(df, "baseline", "ilp_rho0"),
                             os.path.join(out_dir, "gap_decomposition_v2.png"),
                             "Baseline v2 (fixed policy) minus ILP (rho = 0) by cost component")
    write_results_md(df, certs, out_dir, wall, certified)


def main(out_dir: str, certify: bool = True, src_dir: str = SRC_DIR) -> None:
    """Re-run the baseline variants on the stored instances of ``src_dir``
    (``results.csv`` + ``instances/``), certify MIP starts, and write
    ``results_v2.csv`` + ``RESULTS_v2.md`` + figures into ``out_dir``."""
    t_start = time.perf_counter()
    C.ensure_dir(out_dir)
    stored = pd.read_csv(os.path.join(src_dir, "results.csv"))
    insts = load_instances(os.path.join(src_dir, "instances"))
    rows: List[Dict[str, Any]] = []
    certs: List[Dict[str, Any]] = []
    for inst in insts:
        t0 = time.perf_counter()
        r, c = run_instance(inst, stored, certify)
        rows += r
        certs += c
        b = {x["method"]: x for x in r}
        print(f"[{time.strftime('%H:%M:%S')}] {inst.meta['name']}: legacy {b['baseline_legacy']['total']:.1f} -> v2 "
              f"{b['baseline']['total']:.1f} (km {b['baseline_legacy']['bike_km']:.1f} -> {b['baseline']['bike_km']:.1f}, unserved "
              f"{b['baseline_legacy']['n_unserved']} -> {b['baseline']['n_unserved']}, jit {b['baseline']['jit_dispatches']}), reserve "
              f"{b['baseline_reserve']['total']:.1f}; start v2 written/relaxed "
              f"{b['baseline'].get('start_accepted_written')}/{b['baseline'].get('start_accepted_relaxed')} "
              f"[{time.perf_counter() - t0:.0f}s]", flush=True)
    new_df = C.records_to_frame(rows)
    ilp_df = stored[stored.method.isin(ILP_METHODS)].copy()
    ilp_df["source"] = "results.csv"
    old_df = stored[stored.method == "baseline"].copy()
    old_df["method"] = "baseline_old"
    old_df["source"] = "results.csv"
    df = pd.concat([new_df, ilp_df.dropna(axis=1, how="all"), old_df.dropna(axis=1, how="all")],
                   ignore_index=True, sort=False)
    df.to_csv(os.path.join(out_dir, "results_v2.csv"), index=False)
    certs_df = pd.DataFrame(certs)
    wall = time.perf_counter() - t_start
    with open(os.path.join(out_dir, "wall_time_v2.json"), "w") as fh:
        json.dump({"wall_s": wall, "cert_time_limit": CERT_TIME_LIMIT, "certified": certify,
                   "n_instances": len(insts), "variants": VARIANTS}, fh)
    analyse(df, certs_df, out_dir, wall, certify)
    print(f"done: {out_dir}/RESULTS_v2.md ({wall / 60:.1f} min)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default=SRC_DIR, help="E2 run directory with results.csv and instances/")
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--no-certify", action="store_true", help="skip the fix-and-solve MIP-start certificates")
    args = ap.parse_args()
    main(args.out, certify=not args.no_certify, src_dir=args.src)
