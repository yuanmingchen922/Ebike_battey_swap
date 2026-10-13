"""Experiment E3 -- value of battery transfers and of separating charging hubs from
swap sites (``plan.experiments[2]``).

Question
--------
At equal total spare batteries (``sum_j B_j = 12``), chargers (``sum_j C_j = 9``)
and shared grid capacity, what is the value of (i) battery transfers
(``h, z`` free vs the ``no_transfers`` switch ``h = z = 0``, E2 p.9 special case)
and (ii) separating charge-only hubs from swap-only sites (``S`` and ``C``
disjoint vs ``S = C = N``)?

Layouts (synthetic family ``--family`` of ``experiments.common.FAMILIES``, default
``large`` = 10 bikes / 30 orders / ``H = 24`` / ``L = 12``, ``Delta = 5`` min; the
medium family 8 / 24 / 24 / 8 was used for the probe; byte-identical instances for
every method):

``colocated``
    (a) three co-located swap+charge sites at the busiest restaurant zones,
    ``B_j = 4``, ``C_j = 3``, one grid group ``sites`` (8 kW, 6 kW in the 18-20 h
    peak); shuttle services site <-> site every 6 slots (so the transfer switch is
    meaningful here too).
``separated_1hub``
    (b) the same three sites swap-only plus one charge-only hub at the sub-grid
    centre holding all 9 chargers; the hub forms grid group ``hub1`` with the same
    8 / 6 kW profile as the co-located group (equal grid capacity); shuttles hub
    <-> site every 6 slots.
``separated_2hubs``
    (c) as (b) with two hubs (5 + 4 chargers) sharing one grid group ``hubs``
    (same 8 / 6 kW profile).

Spare allocation ``--hub-spares h``: the hubs hold ``h`` of the 12 spares
(``h = 3`` default: sites 3 + 3 + 3, hub 3 or hubs 2 + 1; ``h = 0``: sites 4 + 4 +
4 and empty hubs).  The total is always 12.

Shuttles: departures every 6 slots from boundary 2, duration ``ceil((route +
10 min) / Delta)``, ``U_e = 6``, ``f_e = 5``, ``v_reb = 0.2`` (Section 5, (10),
(32)).

Methods per layout and seed
---------------------------
* baseline policy with ``transfer_rule = NONE`` and ``REORDER_POINT``
  (``plan.baseline_policy_spec``; (9)/(17)/(18) reported, not enforced);
* ILP (5)-(22), (26)-(32) with transfers free (MIP start = baseline
  REORDER_POINT) and with ``no_transfers`` (MIP start = baseline NONE).

Every schedule is priced by ``evaluate.cost`` and verified by ``evaluate.check``
(``experiments.common``).  Reported per run: cost components incl. ``C_reb``,
served share, lateness, stock-out slots ``n_jLt = 0`` per swap site, in-transit
``m_t`` (24), grid-group peak kW (21), solver statistics.

Outputs (``outputs/e3/``): ``results.csv`` (one row per run), ``instances/*.json``,
``RESULTS.md``, ``fig_cost_by_layout.png``, ``fig_cost_components.png``,
``fig_transfer_value.png``, ``fig_full_stock_seed<s>.png``, ``fig_in_transit.png``,
``fig_grid_load_seed<s>.png`` (all figures are drawn from ``results.csv`` alone:
``--figures-only`` redraws them).

Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/e3_transfers_separation.py [--seeds 0 1 2 3 4]
        [--time-limit 300] [--hub-spares 3] [--family large] [--probe]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from experiments import common as C  # noqa: E402
from experiments.common import plt  # noqa: E402  (Agg backend already selected)
from ebike_swap_sim import ArcLibrary, Instance, Schedule  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e3")
FAMILY = "large"   # default family; overridable with --family (calibrated by a probe, see RESULTS.md)
LAYOUTS: Tuple[str, ...] = ("colocated", "separated_1hub", "separated_2hubs")
LAYOUT_LABEL = {"colocated": "(a) co-located 3 sites",
                "separated_1hub": "(b) 3 swap sites + 1 hub",
                "separated_2hubs": "(c) 3 swap sites + 2 hubs"}
#: Equal totals across layouts (overridable: ``--total-spares``, ``--total-chargers``).
#: The probe with the generator defaults (12 spares, q0 ~ U{0.4L..L}) was degenerate --
#: 12 initially full spares cover every swap of a 2 h window, so neither charging nor
#: transfers were ever used; the defaults below make the stock binding.
TOTAL_SPARES = 9
TOTAL_CHARGERS = 9
INIT_FRAC: Tuple[float, float] = (0.3, 0.6)   # bike q0 ~ U{ceil(0.3L)..floor(0.6L)}
SHUTTLE_EVERY = 6
SHUTTLE_FIRST = 2
SERVICE_U, SERVICE_F, SERVICE_VREB = 6, 5.0, 0.2
GRID_KW, GRID_PEAK_KW = 8.0, 6.0


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def _split(total: int, parts: int) -> List[int]:
    """Split ``total`` into ``parts`` integers differing by at most one (largest first)."""
    base, rem = divmod(total, parts)
    return [base + (1 if i < rem else 0) for i in range(parts)]


def make_layout_instance(seed: int, layout: str, hub_spares: int = 3,
                         family: str = FAMILY, total_spares: int = TOTAL_SPARES,
                         total_chargers: int = TOTAL_CHARGERS,
                         init_frac: Tuple[float, float] = INIT_FRAC,
                         relax_end_targets: bool = False,
                         **size_overrides: Any) -> Instance:
    """Medium-family instance (``common.FAMILIES['medium']``) in one of the three
    E3 layouts with equal totals ``sum_j B_j = 12``, ``sum_j C_j = 9`` and equal
    grid capacity (E2 (7)-(8), (15)-(18), (20)-(21); services (10)).

    The order stream, bikes, restaurants and road routes depend on the seed
    only; the layouts differ in the facility roles ``S``/``C``, the placement of
    spares / chargers, the grid groups and the offered services.  The instance
    is validated and JSON round-tripped (``Instance.from_json(to_json) == inst``).
    ``total_spares`` / ``total_chargers`` are the equal totals, ``init_frac`` the
    bike initial-charge range (generator ``demand_spec['init_frac']``) and
    ``size_overrides`` (``n_orders``, ``H`` ...) override the family sizes.
    ``relax_end_targets`` sets ``R_end_j = 0`` and ``rho = 0`` ((17)-(18) off) for the
    side check of how much of the layout / baseline gaps the end targets cause.
    """
    if layout not in LAYOUTS:
        raise KeyError(f"unknown layout {layout!r}")
    n_sites = 3
    n_hubs = {"colocated": 0, "separated_1hub": 1, "separated_2hubs": 2}[layout]
    if n_hubs == 0:
        site_B = _split(total_spares, n_sites)
        hub_B: List[int] = []
        hub_C: List[int] = []
    else:
        site_B = _split(total_spares - int(hub_spares), n_sites)
        hub_B = _split(int(hub_spares), n_hubs)
        hub_C = _split(total_chargers, n_hubs)
    site_C = _split(total_chargers, n_sites) if n_hubs == 0 else [0] * n_sites
    fac_spec: Dict[str, Any] = {
        "mode": "colocated" if n_hubs == 0 else "separated",
        "n_sites": n_sites, "n_hubs": max(1, n_hubs),
        "B": site_B[0], "C": site_C[0],
        "grid_sites_kw": GRID_KW, "grid_sites_peak_kw": GRID_PEAK_KW,
        "hub": {"B": hub_B[0] if hub_B else 0, "C": hub_C[0] if hub_C else 0},
    }
    svc_spec: Dict[str, Any] = {
        "every": SHUTTLE_EVERY, "first": SHUTTLE_FIRST, "U": SERVICE_U, "f": SERVICE_F,
        "vreb": SERVICE_VREB,
        # co-located: the transfer switch needs offered services -> site <-> site shuttles
        "site_site": n_hubs == 0, "site_site_every": SHUTTLE_EVERY,
    }
    inst = C.make_instance(family, seed=seed, name=f"e3-{layout}-seed{seed}",
                           facilities_spec=fac_spec, services_spec=svc_spec,
                           demand_spec={"init_frac": tuple(init_frac)}, **size_overrides)
    # per-facility allocation (generator applies one value to all sites / hubs)
    sites = [f for f in inst.facilities if f.swap]
    hubs = [f for f in inst.facilities if not f.swap]
    assert len(sites) == n_sites and len(hubs) == n_hubs, (len(sites), len(hubs))
    for f, b, c in zip(sites, site_B, site_C):
        f.B, f.C = int(b), int(c)
    for f, b, c in zip(hubs, hub_B, hub_C):
        f.B, f.C = int(b), int(c)
    if relax_end_targets:
        for f in inst.facilities:
            f.R_end = 0
        inst.rho = 0.0
    if hubs:
        # one shared grid group for all hubs with the co-located profile (equal grid capacity)
        profile = [float(GRID_PEAK_KW if _in_peak(inst, t) else GRID_KW) for t in range(inst.H)]
        group = "hub1" if n_hubs == 1 else "hubs"
        for f in hubs:
            f.group = group
        inst.P_grid = {group: profile}
    inst.reindex()
    inst.validate()
    assert sum(f.B for f in inst.facilities) == total_spares
    assert sum(f.C for f in inst.facilities) == total_chargers
    inst.meta.update(layout=layout, hub_spares=int(hub_spares), seed=seed, family=family,
                     site_B=site_B, hub_B=hub_B, hub_C=hub_C, site_C=site_C,
                     total_spares=int(total_spares), total_chargers=int(total_chargers),
                     init_frac=list(init_frac), size_overrides=dict(size_overrides),
                     relax_end_targets=bool(relax_end_targets))
    rt = Instance.from_json(inst.to_json())
    assert rt == inst, "instance does not round-trip through JSON"
    return inst


def _in_peak(inst: Instance, t: int) -> bool:
    """Peak-hour flag of slot ``t`` (generator ``peak_hours`` on the clock of ``meta['window_h']``)."""
    start = float(inst.meta["window_h"][0])
    lo, hi = inst.meta["params"]["facilities_spec"]["peak_hours"]
    hour = start + t * inst.disc.Delta_h
    return lo <= hour < hi


# ---------------------------------------------------------------------------
# records
# ---------------------------------------------------------------------------
def _common_fields(inst: Instance, lib: ArcLibrary, build_time: float) -> Dict[str, Any]:
    hubs = [f for f in inst.facilities if not f.swap]
    return {
        "family": inst.meta.get("family", FAMILY),
        "layout": inst.meta["layout"], "layout_label": LAYOUT_LABEL[inst.meta["layout"]],
        "seed": inst.meta["seed"], "hub_spares": inst.meta["hub_spares"],
        "site_B": json.dumps(inst.meta["site_B"]), "hub_B": json.dumps(inst.meta["hub_B"]),
        "site_C": json.dumps(inst.meta.get("site_C")), "hub_C": json.dumps(inst.meta["hub_C"]),
        "total_spares": inst.meta.get("total_spares"), "total_chargers": inst.meta.get("total_chargers"),
        "init_frac": json.dumps(inst.meta.get("init_frac")),
        "relax_end_targets": bool(inst.meta.get("relax_end_targets", False)),
        "rho": inst.rho, "R_end": json.dumps({f.id: int(f.R_end) for f in inst.facilities}, sort_keys=True),
        "bike_q0": json.dumps([b.q0 for b in inst.bikes]),
        "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "H": inst.H, "L": inst.L,
        "n_facilities": len(inst.facilities), "n_hubs": len(hubs),
        "n_services": len(inst.services), "n_arcs": len(lib), "arc_build_time_s": build_time,
        "grid_limit_kw": json.dumps({g: [float(v) for v in prof] for g, prof in inst.P_grid.items()}, sort_keys=True),
        "facility_roles": json.dumps({f.id: {"swap": bool(f.swap), "charge": bool(f.charge), "B": int(f.B), "C": int(f.C)}
                                      for f in inst.facilities}, sort_keys=True),
    }


def _metric_fields(inst: Instance, m: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the reporting metrics of ``evaluate.metrics`` (E2 p.9 'report
    service, response, lateness, bike distance, transfer loads, grid use')."""
    stockout = m["stockout_slots"]
    peak_group = m["peak_kw_group"]
    group_limit = {g: min(inst.P_grid[g]) for g in inst.P_grid}
    return {
        "served_share": m["served_share"], "n_unserved": m["n_unserved"],
        "mean_response_h": m["mean_response_h"], "mean_lateness_h": m["mean_lateness_h"],
        "max_lateness_h": m["max_lateness_h"], "n_late": m["n_late"],
        "bike_km": m["bike_km"], "n_swaps": m["n_swaps"],
        "swaps_per_facility": json.dumps(m["swaps_per_facility"], default=str, sort_keys=True),
        "mean_wait_before_swap": m["mean_wait_before_swap"],
        "kwh_purchased": m["kwh_purchased"],
        "charge_steps_facility": json.dumps(m["charge_steps_facility"], default=str, sort_keys=True),
        "transfers_used": m["transfers_used"], "batteries_moved": m["batteries_moved"],
        "batteries_moved_by_level": json.dumps(m["batteries_moved_by_level"], sort_keys=True),
        "stockout_slots": json.dumps(stockout, default=str, sort_keys=True),
        "stockout_slots_total": int(sum(stockout.values())),
        "m_t_max": int(max(m["in_transit"])), "m_t_slot_sum": int(sum(m["in_transit"])),
        "m_t": json.dumps([int(v) for v in m["in_transit"]]),
        "peak_kw_group": json.dumps(peak_group, default=str, sort_keys=True),
        "peak_kw_group_max": max(peak_group.values()) if peak_group else 0.0,
        "grid_limit_min_kw": json.dumps(group_limit, default=str, sort_keys=True),
        "end_full_total": m["end_full_total"], "end_target_shortfall": m["end_target_shortfall"],
        "full_stock": json.dumps(m["full_stock"], default=str, sort_keys=True),
    }


def _grid_load(inst: Instance, sched: Schedule) -> Dict[str, List[float]]:
    """Charging load (20)-(21) per grid group and slot, ``p_ch * sum_{j in g, q} c_jqt`` in kW."""
    out: Dict[str, List[float]] = {}
    for g in inst.P_grid:
        members = [f.id for f in inst.facilities if f.group == g]
        out[g] = [round(inst.disc.p_ch_kw * sum(sched.c.get((j, q, t), 0) for j in members
                                                for q in range(inst.L)), 6) for t in range(inst.H)]
    return out


def baseline_record(inst: Instance, lib: ArcLibrary, build_time: float, rule: str,
                    base: Dict[str, Any]) -> Dict[str, Any]:
    """Flat CSV row of a :func:`common.run_baseline_case` result."""
    return {
        **_common_fields(inst, lib, build_time),
        "method": "baseline", "transfers": "free" if rule == "REORDER_POINT" else "none",
        "switch": f"transfer_rule={rule}", "status": "-",
        **C.flatten_cost(base["cost"]),
        "runtime_s": base["runtime"], "check_ok": base["ok"],
        "check_ok_modulo_report_only": base["ok_modulo_report_only"],
        "reported_families": json.dumps(base["families"]),
        "identity_24_ok": base["identity_24_ok"],
        **_metric_fields(inst, base["metrics"]),
        "grid_load_kw": json.dumps(_grid_load(inst, base["schedule"]), sort_keys=True),
    }


def ilp_record(inst: Instance, lib: ArcLibrary, build_time: float, no_transfers: bool,
               rec: Dict[str, Any], baseline_total: Optional[float]) -> Dict[str, Any]:
    """Flat CSV row of a :func:`common.run_ilp_case` result (solver stats included)."""
    st = rec["stats"]
    row: Dict[str, Any] = {
        **_common_fields(inst, lib, build_time),
        "method": "ilp", "transfers": "none" if no_transfers else "free",
        "switch": "no_transfers" if no_transfers else "transfers free",
        "status": rec["status"], "obj": rec["obj"], "bound": rec["bound"], "gap": rec["gap"],
        "runtime_s": rec["runtime"], "model_build_time_s": rec["build_time"],
        "n_binaries": rec["n_binaries"], "n_vars": rec["n_vars"], "n_rows": rec["n_rows"],
        "node_count": st.get("node_count"), "sol_count": st.get("sol_count"),
        "mip_start_accepted": rec["mip_start_accepted"],
        "mip_start_verified_status": (rec["mip_start_info"] or {}).get("verified_status"),
        "check_ok": rec["ok"], "identity_24_ok": rec["identity_24_ok"],
        "reported_families": json.dumps(rec["families"]),
    }
    if rec["cost"] is not None:
        row.update(C.flatten_cost(rec["cost"]))
        row["obj_eq_cost"] = abs(rec["obj"] - rec["cost"]["total"]) <= 1e-6 * max(1.0, abs(rec["obj"]))
        row.update(_metric_fields(inst, rec["metrics"]))
        row["grid_load_kw"] = json.dumps(_grid_load(inst, rec["schedule"]), sort_keys=True)
        if baseline_total is not None:
            row["baseline_total_same_switch"] = baseline_total
            row["ilp_le_baseline"] = rec["cost"]["total"] <= baseline_total + 1e-6
            row["baseline_gap_pct"] = 100.0 * (baseline_total - rec["cost"]["total"]) / max(1e-9, abs(rec["cost"]["total"]))
    return row


# ---------------------------------------------------------------------------
# one (layout, seed)
# ---------------------------------------------------------------------------
def run_layout_seed(layout: str, seed: int, hub_spares: int, time_limit: float,
                    out_dir: str, keep: Dict[str, Any], family: str = FAMILY,
                    inst_kwargs: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Build the instance and arc library, run both baselines and both ILP
    variants; return the flat rows (``keep`` only records sizes; figures read ``results.csv``)."""
    inst = make_layout_instance(seed, layout, hub_spares, family, **(inst_kwargs or {}))
    inst.save(os.path.join(C.ensure_dir(os.path.join(out_dir, "instances")), f"{layout}_seed{seed}.json"))
    lib, build_time = C.build_library(inst, C.pruning_for(inst))
    rows: List[Dict[str, Any]] = []
    bases: Dict[str, Dict[str, Any]] = {}
    for rule in ("NONE", "REORDER_POINT"):
        base = C.run_baseline_case(inst, lib, {"transfer_rule": rule}, label=f"baseline-{rule}")
        bases[rule] = base
        rows.append(baseline_record(inst, lib, build_time, rule, base))
        print(f"  [{layout} seed {seed}] baseline {rule:<13} total {base['cost']['total']:9.2f} "
              f"unserved {base['metrics']['n_unserved']:2d} transfers {base['metrics']['transfers_used']:2d} "
              f"families {base['families']} ({base['runtime']:.2f}s)")
    for no_transfers in (False, True):
        start_rule = "NONE" if no_transfers else "REORDER_POINT"
        rec = C.run_ilp_case(inst, lib, mip_start=bases[start_rule]["schedule"], time_limit=time_limit,
                             threads=C.THREADS, label="ilp", no_transfers=no_transfers)
        rows.append(ilp_record(inst, lib, build_time, no_transfers, rec, bases[start_rule]["cost"]["total"]))
        tag = "no_transfers" if no_transfers else "transfers    "
        print(f"  [{layout} seed {seed}] ILP {tag} {rec['status']:>9} obj {C.fmt(rec['obj'], 2):>9} "
              f"gap {C.fmt(rec['gap'], 4)} solve {rec['runtime']:6.1f}s build {rec['build_time']:.1f}s "
              f"binaries {rec['n_binaries']:,} start accepted {rec['mip_start_accepted']}"
              + (f" | unserved {rec['metrics']['n_unserved']} transfers {rec['metrics']['transfers_used']} "
                 f"moved {rec['metrics']['batteries_moved']} stockouts {rec['metrics']['stockout_slots']} "
                 f"peak kW {rec['metrics']['peak_kw_group']}" if rec["metrics"] else ""))
    keep[(layout, seed)] = {"n_arcs": len(lib), "arc_build_time_s": build_time}  # figures read results.csv
    return rows


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
_COLORS = {"free": "#1f77b4", "none": "#d62728", "baseline": "#7f7f7f"}


def plot_cost_by_layout(df, path: str) -> str:
    """Mean total cost (26) per layout for ILP transfers free / no transfers and the
    baseline REORDER_POINT; one dot per seed."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    series = [("ilp", "free", "ILP, transfers free", _COLORS["free"]),
              ("ilp", "none", "ILP, no transfers (h = z = 0)", _COLORS["none"]),
              ("baseline", "free", "baseline, REORDER_POINT", _COLORS["baseline"])]
    width = 0.26
    rng = np.random.default_rng(0)
    for si, (method, transfers, label, color) in enumerate(series):
        for li, layout in enumerate(LAYOUTS):
            sub = df[(df.layout == layout) & (df.method == method) & (df.transfers == transfers)]
            vals = sub["total"].dropna().to_numpy(dtype=float)
            if len(vals) == 0:
                continue
            x = li + (si - 1) * width
            ax.bar(x, vals.mean(), width, color=color, alpha=0.85, label=label if li == 0 else None)
            jitter = (rng.uniform(-0.3, 0.3, len(vals)) * width) if len(vals) > 1 else np.zeros(len(vals))
            ax.scatter(x + jitter, vals, s=14, color="black", zorder=3)
    ax.set_xticks(range(len(LAYOUTS)))
    ax.set_xticklabels([LAYOUT_LABEL[l] for l in LAYOUTS])
    ax.set_ylabel("total cost (26), toy units; bars = mean, dots = seeds")
    ax.set_title("E3: total cost by layout and transfer switch")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_cost_components(df, path: str) -> str:
    """Stacked mean cost components (27)-(32) per layout x transfer switch (ILP)."""
    comps = [("C_travel", "travel (29)"), ("C_elec", "electricity (28)"), ("unserved", "unserved (30)"),
             ("response", "response (31)"), ("lateness", "lateness (31)"), ("C_reb", "transfers (32)")]
    cmap = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs, labels = [], []
    pos = 0.0
    for layout in LAYOUTS:
        for transfers in ("free", "none"):
            sub = df[(df.layout == layout) & (df.method == "ilp") & (df.transfers == transfers)]
            if sub.empty:
                continue
            bottom = 0.0
            for ci, (col, lab) in enumerate(comps):
                v = float(sub[col].mean()) if col in sub else 0.0
                ax.bar(pos, v, 0.8, bottom=bottom, color=cmap(ci), label=lab if pos == 0.0 else None)
                bottom += v
            xs.append(pos)
            labels.append(f"{layout}\n{'transfers' if transfers == 'free' else 'no transfers'}")
            pos += 1.0
        pos += 0.5
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("mean cost over seeds (toy units)")
    ax.set_title("E3: ILP cost components by layout and transfer switch")
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _runs(df, layout: str, seed: int, method: str = "ilp", transfers: str = "free"):
    """Rows of one (layout, seed, method, transfer switch) with a schedule (``total`` not NaN)."""
    sub = df[(df.layout == layout) & (df.seed == seed) & (df.method == method) & (df.transfers == transfers)]
    return sub[sub["total"].notna()]


def plot_full_stock(df, seed: int, path: str, layouts: Sequence[str] = LAYOUTS) -> str:
    """Full-battery stock ``n_jLt`` (13) per facility over ``t = 0..H`` for the ILP
    with transfers free (solid: swap sites, dashed: hubs), one panel per layout,
    one seed; read from the ``full_stock`` / ``facility_roles`` columns."""
    fig, axes = plt.subplots(len(layouts), 1, figsize=(7.5, 2.6 * len(layouts)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, layout in zip(axes, layouts):
        sub = _runs(df, layout, seed)
        if sub.empty:
            ax.set_title(f"{LAYOUT_LABEL[layout]} -- no ILP schedule", fontsize=9)
            continue
        r = sub.iloc[0]
        roles = json.loads(r["facility_roles"])
        for j, traj in json.loads(r["full_stock"]).items():
            fac = roles[j]
            ax.step(range(len(traj)), traj, where="post", linestyle="-" if fac["swap"] else "--",
                    label=f"{j} ({'swap' if fac['swap'] else 'hub'}, B={fac['B']}, C={fac['C']})")
        ax.set_ylabel("full spares n_jLt")
        ax.set_title(f"{LAYOUT_LABEL[layout]} -- stock-out slots {r['stockout_slots']}, "
                     f"transfers used {int(r['transfers_used'])}", fontsize=9)
        ax.legend(fontsize=7, frameon=False, ncol=2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("boundary t (slots of 5 min)")
    fig.suptitle(f"E3: full-battery stock per facility, ILP with transfers, seed {seed}", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_in_transit(df, seeds: Sequence[int], path: str, layouts: Sequence[str] = LAYOUTS) -> str:
    """In-transit batteries ``m_t`` (24) over ``t`` for the ILP with transfers free,
    one colour per layout (thick: seed mean, thin: seeds); ``m_t`` column."""
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    cmap = plt.get_cmap("tab10")
    for li, layout in enumerate(layouts):
        series = [np.array(json.loads(_runs(df, layout, s).iloc[0]["m_t"]), dtype=float)
                  for s in seeds if not _runs(df, layout, s).empty]
        if not series:
            continue
        H = len(series[0]) - 1
        for arr in series:
            ax.step(range(H + 1), arr, where="post", color=cmap(li), alpha=0.25, linewidth=0.8)
        ax.step(range(H + 1), np.mean(series, axis=0), where="post", color=cmap(li), linewidth=2,
                label=f"{LAYOUT_LABEL[layout]} (mean of {len(series)} seeds)")
    ax.set_xlabel("boundary t (slots of 5 min)")
    ax.set_ylabel("batteries in transit m_t")
    ax.set_title("E3: in-transit batteries over time, ILP with transfers")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_grid_load(df, seed: int, path: str, layouts: Sequence[str] = LAYOUTS) -> str:
    """Charging load of each grid group (20)-(21) per slot vs its limit ``P_grid``,
    ILP with transfers, one panel per layout, one seed (``grid_load_kw`` /
    ``grid_limit_kw`` columns)."""
    fig, axes = plt.subplots(len(layouts), 1, figsize=(7.5, 2.2 * len(layouts)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, layout in zip(axes, layouts):
        sub = _runs(df, layout, seed)
        if sub.empty:
            ax.set_title(f"{LAYOUT_LABEL[layout]} -- no ILP schedule", fontsize=9)
            continue
        r = sub.iloc[0]
        loads, limits = json.loads(r["grid_load_kw"]), json.loads(r["grid_limit_kw"])
        for g, load in loads.items():
            H = len(load)
            ax.step(range(H), load, where="post", label=f"group {g} charging load")
            ax.step(range(H), limits[g], where="post", linestyle=":", color="black", label=f"P_grid[{g}] limit")
        ax.set_ylabel("kW")
        ax.set_title(LAYOUT_LABEL[layout], fontsize=9)
        ax.legend(fontsize=7, frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("slot t (5 min)")
    fig.suptitle(f"E3: grid-group charging load vs limit (21), ILP with transfers, seed {seed}", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_transfer_value(df, path: str, layouts: Sequence[str] = LAYOUTS) -> str:
    """Per-seed value of transfers, ``total(no_transfers) - total(transfers free)``
    of the ILP, and value of co-location, ``total(layout) - total(colocated)`` with
    transfers free; one marker per seed, bar = seed mean."""
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.9))
    cmap = plt.get_cmap("tab10")
    seeds = sorted(df.seed.unique())
    for li, layout in enumerate(layouts):
        vals = []
        for s in seeds:
            a, b = _runs(df, layout, s, "ilp", "none"), _runs(df, layout, s, "ilp", "free")
            if not a.empty and not b.empty:
                vals.append(float(a.iloc[0]["total"]) - float(b.iloc[0]["total"]))
        if vals:
            axes[0].bar(li, np.mean(vals), 0.6, color=cmap(li), alpha=0.8)
            axes[0].scatter([li] * len(vals), vals, s=16, color="black", zorder=3)
        vals = []
        for s in seeds:
            a, b = _runs(df, layout, s), _runs(df, "colocated", s)
            if not a.empty and not b.empty:
                vals.append(float(a.iloc[0]["total"]) - float(b.iloc[0]["total"]))
        if vals:
            axes[1].bar(li, np.mean(vals), 0.6, color=cmap(li), alpha=0.8)
            axes[1].scatter([li] * len(vals), vals, s=16, color="black", zorder=3)
    for ax, ttl, yl in zip(axes, ("value of transfers: cost(h = z = 0) - cost(transfers free)",
                                  "cost of separation: cost(layout) - cost(co-located), transfers free"),
                           ("cost difference (toy units)", "cost difference (toy units)")):
        ax.set_xticks(range(len(layouts)))
        ax.set_xticklabels([LAYOUT_LABEL[l].replace(" 3 sites", "\n3 sites").replace(" + ", "\n+ ")
                            for l in layouts], fontsize=8)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_ylabel(yl)
        ax.set_title(ttl, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def summary_table(df):
    """Seed means per (layout, method, switch) of the headline columns."""
    cols = ["total", "C_travel", "C_elec", "unserved", "response", "lateness", "C_reb",
            "served_share", "n_unserved", "mean_lateness_h", "n_late", "n_swaps", "transfers_used",
            "batteries_moved", "stockout_slots_total", "m_t_max", "peak_kw_group_max",
            "end_full_total", "runtime_s", "gap"]
    present = [c for c in cols if c in df.columns]
    g = df.groupby(["layout", "method", "switch"], sort=False)[present].mean(numeric_only=True).reset_index()
    g["n_seeds"] = df.groupby(["layout", "method", "switch"], sort=False).size().to_numpy()
    order = {l: i for i, l in enumerate(LAYOUTS)}
    g["_o"] = g["layout"].map(order) + g["method"].map({"ilp": 0.0, "baseline": 0.5})
    return g.sort_values(["_o", "switch"]).drop(columns="_o")


def write_results_md(df, out_dir: str, seeds: Sequence[int], hub_spares: int, time_limit: float,
                     figures: List[str], anomalies: List[str], timing: float,
                     family: str = FAMILY, inst_kwargs: Optional[Dict[str, Any]] = None) -> str:
    summ = summary_table(df)
    ilp = df[df.method == "ilp"]
    kw = dict(inst_kwargs or {})
    total_spares = kw.get("total_spares", TOTAL_SPARES)
    total_chargers = kw.get("total_chargers", TOTAL_CHARGERS)
    init_frac = kw.get("init_frac", INIT_FRAC)
    sizes = {**C.FAMILIES[family], **{k: v for k, v in kw.items() if k in ("n_bikes", "n_orders", "H", "L")}}
    lines = ["# E3 -- value of battery transfers and of separating charging hubs from swap sites", "",
             f"Family `{family}` ({sizes}), seeds {list(seeds)}; bike q0 ~ U{{ceil({init_frac[0]}L)..floor({init_frac[1]}L)}}; equal totals "
             f"sum B = {total_spares}, sum C = {total_chargers}, grid group {GRID_KW:.0f} kW "
             f"({GRID_PEAK_KW:.0f} kW in the 18-20 h peak) in every layout; hubs hold {hub_spares} of the spares. "
             f"Shuttles every {SHUTTLE_EVERY} slots from t = {SHUTTLE_FIRST}, U_e = {SERVICE_U}, f_e = {SERVICE_F}, "
             f"v_reb = {SERVICE_VREB}. Pruning {C.PRUNING_DEFAULTS}; Gurobi Threads {C.THREADS}, TimeLimit "
             f"{time_limit:.0f} s, OutputFlag 0. Total wall time {timing / 60:.1f} min (single process).", "",
             "## Seed means per layout, method and transfer switch", "",
             C.markdown_table(summ, list(summ.columns), 3), "",
             "`stockout_slots_total` = slots with `n_jLt = 0` summed over swap sites; `m_t_max` = max in-transit "
             "batteries (24); `peak_kw_group_max` = max over grid groups of the peak charging load (21); "
             f"`end_full_total` = sum_j n_jLH ((18) requires >= rho sum B = {0.5 * total_spares:g}).", "",
             "## Per-run table (ILP)", ""]
    cols = ["layout", "seed", "switch", "status", "total", "C_travel", "C_elec", "unserved", "response",
            "lateness", "C_reb", "served_share", "n_late", "transfers_used", "batteries_moved",
            "stockout_slots", "m_t_max", "peak_kw_group", "end_full_total", "n_binaries", "n_rows",
            "runtime_s", "gap", "mip_start_accepted", "check_ok", "identity_24_ok", "baseline_total_same_switch",
            "baseline_gap_pct"]
    lines += [C.markdown_table(ilp, [c for c in cols if c in ilp.columns], 3), "",
              "## Per-run table (baseline)", ""]
    bcols = ["layout", "seed", "switch", "total", "C_travel", "C_elec", "unserved", "response", "lateness",
             "C_reb", "served_share", "n_late", "transfers_used", "batteries_moved", "stockout_slots",
             "m_t_max", "peak_kw_group", "end_full_total", "reported_families", "check_ok_modulo_report_only",
             "identity_24_ok", "runtime_s"]
    base = df[df.method == "baseline"]
    lines += [C.markdown_table(base, [c for c in bcols if c in base.columns], 3), ""]
    lines += ["## Figures", ""] + [f"- `{os.path.basename(f)}`" for f in figures] + [""]
    lines += ["## Anomalies / checks", ""] + ([f"- {a}" for a in anomalies] or ["- none"]) + [""]
    interp = os.path.join(out_dir, "INTERPRETATION.md")   # hand-written discussion, kept across re-runs
    if os.path.exists(interp):
        with open(interp, encoding="utf-8") as fh:
            lines += [fh.read().rstrip(), ""]
    path = os.path.join(out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def collect_anomalies(df) -> List[str]:
    """Automatic sanity flags (ILP check / identity (24) / baseline comparison / gaps)."""
    out: List[str] = []
    for _, r in df.iterrows():
        tag = f"{r['layout']} seed {r['seed']} {r['method']} {r['switch']}"
        if r["method"] == "ilp":
            if r["status"] != "OPTIMAL":
                out.append(f"{tag}: status {r['status']} gap {r.get('gap')}")
            if r.get("check_ok") is not True:
                out.append(f"{tag}: ILP schedule fails evaluate.check")
            if r.get("identity_24_ok") is not True:
                out.append(f"{tag}: identity (24) violated")
            if r.get("ilp_le_baseline") is False:
                brow = df[(df.layout == r["layout"]) & (df.seed == r["seed"]) & (df.method == "baseline")
                          & (df.transfers == r["transfers"])]
                bfam = brow.iloc[0]["reported_families"] if not brow.empty else "?"
                out.append(f"{tag}: ILP total {r['total']:.2f} > baseline {r['baseline_total_same_switch']:.2f} "
                           f"(baseline reported families {bfam}: the baseline point is infeasible for the model, "
                           f"so this is not a counter-example to optimality)")
        else:
            if r.get("check_ok_modulo_report_only") is not True:
                out.append(f"{tag}: baseline violates a non-report-only family {r['reported_families']}")
            if r.get("identity_24_ok") is not True:
                out.append(f"{tag}: baseline breaks identity (24)")
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def make_figures(df, out_dir: str, seeds: Sequence[int], layouts: Sequence[str] = LAYOUTS) -> List[str]:
    """All E3 figures from the ``results.csv`` frame (no schedules needed)."""
    figures = [plot_cost_by_layout(df, os.path.join(out_dir, "fig_cost_by_layout.png")),
               plot_cost_components(df, os.path.join(out_dir, "fig_cost_components.png")),
               plot_transfer_value(df, os.path.join(out_dir, "fig_transfer_value.png"), layouts),
               plot_in_transit(df, seeds, os.path.join(out_dir, "fig_in_transit.png"), layouts)]
    s0 = seeds[0]
    figures.append(plot_full_stock(df, s0, os.path.join(out_dir, f"fig_full_stock_seed{s0}.png"), layouts))
    figures.append(plot_grid_load(df, s0, os.path.join(out_dir, f"fig_grid_load_seed{s0}.png"), layouts))
    return figures


def main(seeds: Sequence[int], hub_spares: int = 3, time_limit: float = C.DEFAULT_TIME_LIMIT,
         out_dir: str = OUT_DIR, layouts: Sequence[str] = LAYOUTS, probe: bool = False,
         family: str = FAMILY, inst_kwargs: Optional[Dict[str, Any]] = None,
         figures_only: bool = False) -> Any:
    """Run every (layout, seed), write ``results.csv`` (incrementally), figures and
    ``RESULTS.md``.  With ``figures_only`` the existing ``results.csv`` of
    ``out_dir`` is re-read and only figures + ``RESULTS.md`` are regenerated."""
    t_start = time.perf_counter()
    C.ensure_dir(out_dir)
    csv_path = os.path.join(out_dir, "results.csv")
    wall_path = os.path.join(out_dir, "wall_time.json")
    if figures_only:
        import pandas as pd
        df = pd.read_csv(csv_path)
        seeds = sorted(df.seed.unique())
        wall = json.load(open(wall_path))["wall_s"] if os.path.exists(wall_path) else float("nan")
    else:
        rows: List[Dict[str, Any]] = []
        keep: Dict[str, Any] = {}
        for seed in seeds:
            for layout in layouts:
                rows.extend(run_layout_seed(layout, seed, hub_spares, time_limit, out_dir, keep, family, inst_kwargs))
                C.write_csv(rows, csv_path)  # incremental
                sys.stdout.flush()
        df = C.write_csv(rows, csv_path)
        wall = time.perf_counter() - t_start
        with open(wall_path, "w", encoding="utf-8") as fh:
            json.dump({"wall_s": wall, "seeds": list(seeds), "time_limit": time_limit, "family": family,
                       "inst_kwargs": inst_kwargs or {}, "hub_spares": hub_spares}, fh)
        if probe:
            print(C.markdown_table(summary_table(df), None, 3))
            return df
    figures = make_figures(df, out_dir, seeds, layouts)
    anomalies = collect_anomalies(df)
    md = write_results_md(df, out_dir, seeds, hub_spares, time_limit, figures, anomalies, wall, family,
                          inst_kwargs or {})
    print(f"wrote {md} and {len(figures)} figures; wall {wall:.0f}s")
    print(C.markdown_table(summary_table(df), None, 3))
    for a in anomalies:
        print("ANOMALY:", a)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    ap.add_argument("--layouts", nargs="+", default=list(LAYOUTS))
    ap.add_argument("--hub-spares", type=int, default=3)
    ap.add_argument("--time-limit", type=float, default=C.DEFAULT_TIME_LIMIT)
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--probe", action="store_true", help="run only, no figures / RESULTS.md")
    ap.add_argument("--family", default=FAMILY,
                    choices=[f for f in C.FAMILIES if f not in ("toy", "p7") and f not in C.R2_FAMILIES],
                    help="synthetic family of experiments.common.FAMILIES (sizes); the round-2 families "
                         "(window_h / orders_per_bike_hour knobs, no n_orders / H) are excluded here")
    ap.add_argument("--total-spares", type=int, default=TOTAL_SPARES)
    ap.add_argument("--total-chargers", type=int, default=TOTAL_CHARGERS)
    ap.add_argument("--init-frac", type=float, nargs=2, default=list(INIT_FRAC), metavar=("LO", "HI"))
    ap.add_argument("--n-orders", type=int, default=None, help="override the family order count")
    ap.add_argument("--H", type=int, default=None, help="override the family horizon (slots)")
    ap.add_argument("--figures-only", action="store_true", help="re-read results.csv, redraw figures + RESULTS.md")
    ap.add_argument("--relax-end-targets", action="store_true", help="R_end = 0, rho = 0 ((17)-(18) off)")
    args = ap.parse_args()
    ikw: Dict[str, Any] = {"total_spares": args.total_spares, "total_chargers": args.total_chargers,
                           "init_frac": tuple(args.init_frac), "relax_end_targets": args.relax_end_targets}
    if args.n_orders is not None:
        ikw["n_orders"] = args.n_orders
    if args.H is not None:
        ikw["H"] = args.H
    main(args.seeds, args.hub_spares, args.time_limit, args.out_dir, args.layouts, args.probe, args.family, ikw,
         figures_only=args.figures_only)
