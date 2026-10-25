"""Experiment X2 (round 5) -- value of battery transfers and of separating charging hubs from
swap sites, re-run with the round-5 calibration, the M1 boundary convention, the fair (M3)
transfer rule and the M8 cyclic timetable (``notes/reading_to_model.md`` items A1, A3, M1, M3,
M8, O1; DECISIONS "R5 implementation notes").

Design
------
* Instances: the three E3u layouts of ``experiments/e3u_transfers_usd_fixed.py`` (builder
  :func:`make_layout_instance` reused as is): ``colocated`` (3 swap+charge sites, B 3 / C 2),
  ``separated_1hub`` (3 swap-only sites B 3 + one charge-only hub with all 6 chargers),
  ``separated_2hubs`` (two hubs 3 + 3 chargers); family ``usd4h`` (6 bikes / 36 orders / H 48,
  ``usd_sunk``) with the eBaaS energy calibration (A1: 25 Wh/km, eps 25 Wh, L 24, concat
  rounding, q_res 2 levels); seeds 0-4; byte-identical demand across every layout, timetable
  and target setting of a seed (``demand_md5`` asserted).
* Timetables (services (10)): ``r3`` = the round-3 timetable (hub <-> site shuttles every 6
  slots from boundary 2 in the separated layouts, site <-> site every 6 slots in the
  co-located layout, U 6) and ``cyclic`` = the M8 timetable (chained legs over all facilities,
  one tour every 12 slots = 60 min from boundary 2, cap U 6, the usd_sunk ``f`` split over the
  legs of a tour; no night tour inside the 17-21 h window).  The cyclic instance is the r3
  instance with only ``services`` replaced (asserted).
* End targets (M1): ``relaxed`` = the like-for-like control ``rho 0``, ``R_end_j 0``
  (:func:`experiments.common.relax_end_targets`, the headline) and ``written`` = the written
  targets with ``R_end_j = 0`` at swap-only sites (rho 0.5, ``R_end_j`` 1 at the co-located
  sites, 0 at swap-only sites and hubs; :func:`experiments.common.end_target_copy`) = the price
  of recovery.  ``meta['written_R_end']`` holds the M1 written targets, so the DEMAND_AWARE
  reserve of the policy is the same in both settings.  ``C_end_adjust`` / ``total_end_adjusted``
  are reported for every row.
* Methods per (layout, timetable, targets, seed): the policies ``r2`` (R2.3 rules, NONE),
  ``r2_reorder`` (R2.3 + REORDER_POINT), ``r5_range`` (M2, NONE), ``r5_transfer`` (R2.3 +
  COST_AWARE, M3) and ``r5`` (M2 + M3); ``best_rule`` = min over r2, r5_range, r5_transfer
  (when services exist) and r5 (the conservative comparison); the E2 ILP (aggregated flow O1)
  with transfers free.  The ILP with ``no_transfers`` (h = z = 0) does not depend on the
  timetable, so it is solved once per (layout, targets, seed) on the r3 instance and recorded
  with ``timetable = 'any'``.
* Gurobi: ``OutputFlag 0``, ``Threads 3``, ``Seed 0``, ``TimeLimit 300 s``, ``aggregate=True``;
  MIP start = the cheapest clean policy schedule (transfer-free for ``no_transfers``).
* Protocol: ``records.jsonl`` append-only, ``results.csv`` refreshed after each run, resume by
  key, wall budget 180 min (:class:`experiments.common.WallBudget`; not started solves are
  recorded as ``SKIPPED_BUDGET`` and retried on resume), one printed line per run,
  ``--dry-run`` (plan only), ``--smoke`` (one layout / seed, short limits, into ``--out-dir``),
  ``--analyse`` (``RESULTS.md`` + figures from the records).
* Order of work: all relaxed cells (headline) for seeds 0-4, then the written cells; per
  (layout, seed) ILP none, ILP free r3, ILP free cyclic.  One per-bike arc library is built per
  (layout, seed, target phase) and rebound to the other timetable / target copy after asserting
  that every arc-relevant field is identical (services, rho and R_end do not enter
  ``build_arcs``).

Reports (``--analyse``): headline gaps (relaxed), value of transfers ``ILP(none) - ILP(free)``,
separation cost ``ILP(separated) - ILP(colocated)``, the REORDER_POINT loss vs the COST_AWARE
loss (``r2_reorder - r2`` vs ``r5_transfer - r2``), cyclic vs hub-spoke (``r3``) timetable, the
price of recovery (written - relaxed) and the A3 metric pack.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r5_x2_transfers.py --dry-run
    python3 experiments/r5_x2_transfers.py --smoke --out-dir /tmp/x2_smoke
    python3 experiments/r5_x2_transfers.py
    python3 experiments/r5_x2_transfers.py --analyse
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import ArcLibrary, Instance, Schedule  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments.common import plt  # noqa: E402  (Agg backend)
from experiments import e3u_transfers_usd_fixed as E3U  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r5_x2_transfers")
RECORDS = "records.jsonl"
FAMILY = "usd4h"
ENERGY_CAL = "ebaas"
LAYOUTS: Tuple[str, ...] = tuple(E3U.LAYOUTS)
TIMETABLES: Tuple[str, ...] = ("r3", "cyclic")
TIMETABLE_LABEL = {"r3": "round-3 hub-spoke / site-site shuttles (every 30 min)",
                   "cyclic": "M8 cyclic tours (every 60 min)", "any": "no transfers (timetable irrelevant)"}
TARGETS: Tuple[str, ...] = ("relaxed", "written")
SEEDS: Tuple[int, ...] = (0, 1, 2, 3, 4)
SWITCHES: Tuple[str, ...] = ("none", "free")
TIME_LIMIT = 300.0
WALL_BUDGET_S = 180 * 60.0
#: M8 cyclic timetable (generator ``services_spec['mode'] = 'cyclic'``): one tour per hour from
#: boundary 2 (same first departure as the round-3 shuttles), cap = U 6; f / vreb from usd_sunk.
CYCLIC_SPEC: Dict[str, Any] = {"mode": "cyclic", "tour_every": 12, "first": E3U.SHUTTLE_FIRST,
                               "U": E3U.SERVICE_U, "split_f": True}
#: Policies: label -> (common.BASELINE_VARIANTS name, BaselineParams overrides).
BASELINES: Dict[str, Tuple[str, Dict[str, Any]]] = {
    "r2": ("baseline", {}),
    "r2_reorder": ("baseline", {"transfer_rule": "REORDER_POINT"}),
    "r5_range": ("baseline_r5_range", {}),
    "r5_transfer": ("baseline_r5_transfer", {}),
    "r5": ("baseline_r5", {}),
}
#: Rules of the conservative comparison ``best_rule`` (``r5_transfer`` only when services exist).
BEST_RULE: Tuple[str, ...] = ("r2", "r5_range", "r5_transfer", "r5")
#: MIP-start fallbacks (run only when no computed policy schedule passes ``check`` cleanly).
START_FALLBACKS: Tuple[Tuple[str, Dict[str, Any]], ...] = (
    ("baseline_round1", {}), ("baseline_reserve", {}), ("baseline_reserve", {"transfer_rule": "REORDER_POINT"}))

Key = Tuple[str, str, str, int, str, str]      # (layout, timetable, targets, seed, method, variant)
WorkItem = Tuple[str, str, int, str, str]       # (targets, layout, seed, switch, timetable)


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def _cyclic_layout_instance(seed: int, layout: str) -> Instance:
    """:func:`E3U.make_layout_instance` with the M8 cyclic ``services_spec`` (the E3u builder fixes
    its shuttle spec, so the facility part is reproduced here verbatim and the result is asserted
    equal to the r3 instance except for ``services`` in :func:`make_x2_instance`)."""
    n_hubs = {"colocated": 0, "separated_1hub": 1, "separated_2hubs": 2}[layout]
    site_Bs = [int(E3U.SITE_B)] * E3U.N_SITES
    if n_hubs == 0:
        site_Cs = E3U._split(int(E3U.TOTAL_CHARGERS), E3U.N_SITES)
        hub_Bs: List[int] = []
        hub_Cs: List[int] = []
    else:
        site_Cs = [0] * E3U.N_SITES
        hub_Bs = E3U._split(int(E3U.HUB_SPARES), n_hubs)
        hub_Cs = E3U._split(int(E3U.TOTAL_CHARGERS), n_hubs)
    fac_spec: Dict[str, Any] = {
        "mode": "colocated" if n_hubs == 0 else "separated",
        "n_sites": E3U.N_SITES, "n_hubs": max(1, n_hubs),
        "B": site_Bs[0], "C": site_Cs[0],
        "grid_sites_kw": E3U.GRID_KW, "grid_sites_peak_kw": E3U.GRID_PEAK_KW,
        "hub": {"B": hub_Bs[0] if hub_Bs else 0, "C": hub_Cs[0] if hub_Cs else 0},
    }
    inst = C.make_instance(FAMILY, seed=seed, name=f"e3u-{layout}-seed{seed}", facilities_spec=fac_spec,
                           services_spec=dict(CYCLIC_SPEC), energy_calibration=ENERGY_CAL)
    sites = [f for f in inst.facilities if f.swap]
    hubs = [f for f in inst.facilities if not f.swap]
    assert len(sites) == E3U.N_SITES and len(hubs) == n_hubs, (len(sites), len(hubs))
    for f, b, c in zip(sites, site_Bs, site_Cs):
        f.B, f.C = int(b), int(c)
    for f, b, c in zip(hubs, hub_Bs, hub_Cs):
        f.B, f.C = int(b), int(c)
    if hubs:
        profile = [float(E3U.GRID_PEAK_KW if E3U._in_peak(inst, t) else E3U.GRID_KW) for t in range(inst.H)]
        group = "hub1" if n_hubs == 1 else "hubs"
        for f in hubs:
            f.group = group
        inst.P_grid = {group: profile}
    inst.reindex()
    inst.validate()
    return inst


def _strip(d: Dict[str, Any], drop: Sequence[str]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if k not in drop}


def make_x2_instance(seed: int, layout: str, timetable: str) -> Instance:
    """Written-target X2 instance of one (layout, timetable, seed): the E3u layout builder on
    ``usd4h`` with ``energy_calibration='ebaas'``; for ``cyclic`` the services are those of the
    M8 generator call and everything else is asserted identical to the r3 instance."""
    base = E3U.make_layout_instance(seed, layout, energy_calibration=ENERGY_CAL)
    base.meta["timetable"] = "r3"
    if timetable == "r3":
        return base
    if timetable != "cyclic":
        raise KeyError(f"unknown timetable {timetable!r}")
    cyc = _cyclic_layout_instance(seed, layout)
    a = _strip(base.to_dict(), ("services", "meta"))
    b = _strip(cyc.to_dict(), ("services", "meta"))
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str), \
        f"cyclic {layout} seed {seed}: non-service data differ from the r3 instance"
    out = copy.deepcopy(base)
    out.services = copy.deepcopy(cyc.services)
    out.reindex()
    out.validate()
    out.meta["timetable"] = "cyclic"
    out.meta["cyclic_services"] = cyc.meta.get("cyclic_services")
    rt = Instance.from_json(out.to_json())
    assert rt == out, "cyclic instance does not round-trip through JSON"
    return out


def written_m1(inst: Instance) -> Instance:
    """M1 written targets: ``rho`` as written (0.5), ``R_end_j`` as written (1) at swap+charge
    sites, ``R_end_j = 0`` at swap-only sites (and hubs).  ``meta['written_R_end']`` is set to
    these M1 targets (the DEMAND_AWARE reserve of the policy in both target settings);
    ``meta['written_R_end_e2']`` keeps the E2 written values."""
    sc = [f for f in inst.facilities if f.swap and f.charge]
    assert all(int(f.R_end) == 1 for f in sc), [(f.id, f.R_end) for f in sc]
    e2 = {f.id: int(f.R_end) for f in inst.facilities}
    out = C.end_target_copy(inst, rho=float(inst.rho), R_end=1, label="written_m1", swap_only_zero=True)
    out.meta["written_R_end"] = {f.id: int(f.R_end) for f in out.facilities}
    out.meta["written_R_end_e2"] = e2
    out.meta["end_targets"] = "written"
    return out


def target_copy(inst_written: Instance, targets: str) -> Instance:
    if targets == "written":
        return inst_written
    out = C.relax_end_targets(inst_written)          # rho0_R0, keeps meta['written_R_end'] (M1)
    out.meta["end_targets"] = "relaxed"
    return out


def arc_signature(inst: Instance) -> str:
    """Everything ``build_arcs`` can read: the instance without services, rho, P_grid, meta and
    the per-facility end targets / sizes."""
    d = _strip(inst.to_dict(), ("services", "rho", "P_grid", "meta", "budget", "zeta"))
    d["facilities"] = [_strip(f, ("R_end", "B", "C", "K", "Cbar", "P_kw", "group", "F", "bB", "bC",
                                  "Fhat", "bhat", "chat")) for f in d["facilities"]]
    return json.dumps(d, sort_keys=True, default=str)


def rebind_library(lib: ArcLibrary, inst: Instance) -> ArcLibrary:
    """Shallow copy of ``lib`` bound to ``inst`` (same arcs, ids and indices); asserts that the
    arc-relevant data of both instances are identical."""
    if lib.inst is inst:
        return lib
    assert arc_signature(lib.inst) == arc_signature(inst), "arc-relevant instance data differ"
    out = copy.copy(lib)
    out.inst = inst
    return out


# ---------------------------------------------------------------------------
# keys and plan
# ---------------------------------------------------------------------------
def ilp_key(layout: str, timetable: str, targets: str, seed: int, switch: str) -> Key:
    return (layout, "any" if switch == "none" else timetable, targets, int(seed), "ilp", switch)


def baseline_key(layout: str, timetable: str, targets: str, seed: int, label: str) -> Key:
    return (layout, timetable, targets, int(seed), "baseline", label)


def key_of(row: Dict[str, Any]) -> Key:
    return (row["layout"], row["timetable"], row["targets"], int(row["seed"]), row["method"], row["variant"])


def row_done(row: Optional[Dict[str, Any]], time_limit: float) -> bool:
    """A row counts as done unless it was skipped by the budget or a solve was cut short by the
    budget (smaller TimeLimit) and stopped without a certified optimum."""
    if row is None:
        return False
    if row.get("method") == "baseline":
        return True
    st = row.get("status")
    if st == C.SKIPPED_BUDGET or st is None:
        return False
    if C.reusable_ilp_row(st, row.get("gap")):
        return True
    tl = row.get("time_limit_used_s")
    try:
        return float(tl) >= float(time_limit) - 1.0
    except (TypeError, ValueError):
        return True


def build_plan(done: Dict[Key, Dict[str, Any]], seeds: Sequence[int], layouts: Sequence[str] = LAYOUTS,
               targets_order: Sequence[str] = TARGETS, timetables: Sequence[str] = TIMETABLES,
               switches: Sequence[str] = SWITCHES, time_limit: float = TIME_LIMIT) -> List[WorkItem]:
    plan: List[WorkItem] = []
    for targets in targets_order:
        for seed in seeds:
            for layout in layouts:
                for switch in switches:
                    tts = ("r3",) if switch == "none" else tuple(timetables)
                    for tt in tts:
                        if not row_done(done.get(ilp_key(layout, tt, targets, seed, switch)), time_limit):
                            plan.append((targets, layout, int(seed), switch, tt))
    return plan


def plan_summary(plan: Sequence[WorkItem], time_limit: float, est_solve_s: float, overhead_s: float) -> Dict[str, Any]:
    groups = {(t, l, s) for t, l, s, _sw, _tt in plan}
    per_switch: Dict[str, int] = {}
    for _t, _l, _s, sw, tt in plan:
        per_switch[f"{sw}:{tt}"] = per_switch.get(f"{sw}:{tt}", 0) + 1
    n = len(plan)
    exp_s = n * est_solve_s + len(groups) * overhead_s
    worst_s = n * time_limit + len(groups) * overhead_s
    return {"ilp_items": n, "per_switch_timetable": per_switch, "library_groups": len(groups),
            "baseline_runs_max": len(groups) * 2 * len(BASELINES),
            "expected_wall_min": round(exp_s / 60.0, 1), "worst_wall_min": round(worst_s / 60.0, 1),
            "assumed_solve_s": est_solve_s, "assumed_group_overhead_s": overhead_s}


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------
def _common(inst: Instance, lib: ArcLibrary, build_time: float) -> Dict[str, Any]:
    row = E3U._common_fields(inst, lib, build_time)
    row.update(timetable=inst.meta.get("timetable"), energy_calibration=ENERGY_CAL,
               boundary_variant=inst.meta.get("boundary_variant", "written"),
               written_R_end_m1=json.dumps(inst.meta.get("written_R_end"), sort_keys=True),
               n_services=len(inst.services),
               cyclic_meta=json.dumps(inst.meta.get("cyclic_services"), default=str))
    return row


def _metrics(inst: Instance, met: Dict[str, Any]) -> Dict[str, Any]:
    out = E3U._metric_fields(inst, met)
    out.update(C.flatten_r5(met))
    return out


def baseline_row(inst: Instance, lib: ArcLibrary, build_time: float, label: str, base: Dict[str, Any]) -> Dict[str, Any]:
    fl = base["flags"]
    return {
        **_common(inst, lib, build_time), "method": "baseline", "variant": label,
        "baseline_variant": BASELINES[label][0], "transfer_rule": base["params"].get("transfer_rule"),
        "swap_rule": base["params"].get("swap_rule"), "status": "-",
        **C.flatten_cost(base["cost"]),
        "runtime_s": base["runtime"], "check_ok": base["ok"],
        "check_ok_modulo_report_only": base["ok_modulo_report_only"],
        "reported_families": json.dumps(base["families"]), "identity_24_ok": base["identity_24_ok"],
        "policy_reserve_source": base.get("policy_reserve_source"),
        "charge_rule_effective": json.dumps(fl.get("charge_rule_effective"), default=str, sort_keys=True),
        "cost_aware_flags": json.dumps(fl.get("cost_aware"), default=str, sort_keys=True)[:4000],
        **{f"baseline_{k}": v for k, v in C.baseline_pruning_flags(fl).items()},
        **_metrics(inst, base["metrics"]),
    }


def _best(bases: Dict[str, Dict[str, Any]], labels: Sequence[str], key: str) -> Tuple[Optional[float], Optional[str]]:
    best, arg = None, None
    for lab in labels:
        b = bases.get(lab)
        if b is None or b.get("cost") is None:
            continue
        v = b["cost"].get(key)
        if v is not None and (best is None or v < best - 1e-9):
            best, arg = float(v), lab
    return best, arg


def best_rule_labels(inst: Instance) -> List[str]:
    return [lab for lab in BEST_RULE if lab != "r5_transfer" or inst.services]


def transfer_free_labels(bases: Dict[str, Dict[str, Any]]) -> List[str]:
    return [lab for lab in BASELINES if lab in bases and bases[lab]["params"].get("transfer_rule", "NONE") == "NONE"]


def ilp_row(inst: Instance, lib: ArcLibrary, build_time: float, switch: str, rec: Dict[str, Any],
            start_label: str, tl: float, bases: Dict[str, Dict[str, Any]], threads: int) -> Dict[str, Any]:
    st = rec["stats"]
    row: Dict[str, Any] = {
        **_common(inst, lib, build_time), "method": "ilp", "variant": switch,
        "timetable": "any" if switch == "none" else inst.meta.get("timetable"),
        "solved_on_timetable": inst.meta.get("timetable"),
        "transfers": switch, "status": rec["status"], "obj": rec["obj"], "bound": rec["bound"], "gap": rec["gap"],
        "runtime_s": rec["runtime"], "model_build_time_s": rec["build_time"], "time_limit_used_s": tl,
        "threads": threads, "aggregate": json.dumps({k: (st.get("aggregate") or {}).get(k) for k in
                                ("mode", "n_bike_arcs", "n_agg_arcs", "reduction", "n_classes")}),
        "n_agg_arcs": st.get("n_agg_arcs"),
        "n_binaries": rec["n_binaries"], "n_vars": rec["n_vars"], "n_rows": rec["n_rows"],
        "node_count": st.get("node_count"), "sol_count": st.get("sol_count"),
        "mip_start_variant": start_label, "mip_start_accepted": rec["mip_start_accepted"],
        "mip_start_verified_status": (rec["mip_start_info"] or {}).get("verified_status"),
        "check_ok": rec["ok"], "identity_24_ok": rec["identity_24_ok"],
        "reported_families": json.dumps(rec["families"]),
    }
    if rec["cost"] is None:
        return row
    row.update(C.flatten_cost(rec["cost"]))
    row["obj_eq_cost"] = abs(rec["obj"] - rec["cost"]["total"]) <= 1e-6 * max(1.0, abs(rec["obj"]))
    row.update(_metrics(inst, rec["metrics"]))
    tot, tot_adj = rec["cost"]["total"], rec["cost"].get("total_end_adjusted")
    for lab, b in bases.items():
        bt, bta = b["cost"]["total"], b["cost"].get("total_end_adjusted")
        row[f"baseline_total_{lab}"] = bt
        row[f"baseline_total_end_adjusted_{lab}"] = bta
        row[f"gap_vs_{lab}_pct"] = C.gap_definitions(bt, tot)["gap_vs_baseline_pct"]
        row[f"gap_vs_{lab}_pct_end_adjusted"] = C.gap_definitions(bta, tot_adj)["gap_vs_baseline_pct"]
    for name, labels in (("best_rule", best_rule_labels(inst)), ("best_rule_notransfer", transfer_free_labels(bases))):
        bt, arg = _best(bases, labels, "total")
        bta, arga = _best(bases, labels, "total_end_adjusted")
        row[f"{name}_set"] = json.dumps(labels)
        row[f"{name}_total"], row[f"{name}_label"] = bt, arg
        row[f"{name}_total_end_adjusted"], row[f"{name}_label_end_adjusted"] = bta, arga
        row[f"gap_vs_{name}_pct"] = C.gap_definitions(bt, tot)["gap_vs_baseline_pct"]
        row[f"gap_vs_{name}_pct_end_adjusted"] = C.gap_definitions(bta, tot_adj)["gap_vs_baseline_pct"]
        row[f"ilp_le_{name}"] = None if bt is None else tot <= bt + 1e-6
    return row


def skipped_row(layout: str, timetable: str, targets: str, seed: int, switch: str, reason: str) -> Dict[str, Any]:
    """Row of an ILP cell the wall budget did not allow (retried on resume)."""
    return {"family": FAMILY, "energy_calibration": ENERGY_CAL, "layout": layout, "targets": targets, "seed": int(seed),
            "method": "ilp", "variant": switch, "timetable": "any" if switch == "none" else timetable,
            "solved_on_timetable": timetable, "transfers": switch, "status": C.SKIPPED_BUDGET,
            "reported_families": json.dumps({}), "skip_reason": reason}


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, out_dir: str, time_limit: float, threads: int, budget: C.WallBudget,
                 reachable: bool = True, verify_rebind: bool = False) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.path = os.path.join(out_dir, RECORDS)
        self.tl, self.threads, self.budget = float(time_limit), int(threads), budget
        self.reachable = reachable
        self.verify_rebind = verify_rebind
        self.done: Dict[Key, Dict[str, Any]] = {key_of(r): r for r in C.load_jsonl(self.path)}
        self.md5: Dict[int, str] = {}
        for r in self.done.values():
            if r.get("demand_md5"):
                self.md5.setdefault(int(r["seed"]), r["demand_md5"])
        self.n_runs = 0
        self._lib_key: Optional[Tuple[str, int, str]] = None
        self._lib: Optional[ArcLibrary] = None
        self._lib_build = float("nan")
        self._ctx: Dict[Tuple[str, str], Dict[str, Any]] = {}     # (timetable, targets) -> context

    # -- io -------------------------------------------------------------------
    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("source", "r5_x2")
        C.append_jsonl(self.path, row)
        self.done[key_of(row)] = row
        self.refresh_csv()
        self.n_runs += 1
        keys = ("layout", "timetable", "targets", "seed", "method", "variant", "status", "total",
                "total_end_adjusted", "n_unserved", "transfers_used", "batteries_moved", "gap", "runtime_s",
                "gap_vs_best_rule_pct", "best_rule_label", "mip_start_variant", "mip_start_accepted")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys if k in row}), flush=True)

    def refresh_csv(self) -> None:
        def sk(r: Dict[str, Any]) -> Tuple:
            return (TARGETS.index(r["targets"]) if r["targets"] in TARGETS else 9, int(r["seed"]),
                    LAYOUTS.index(r["layout"]) if r["layout"] in LAYOUTS else 9, r["method"],
                    str(r["timetable"]), str(r["variant"]))
        C.records_to_frame(sorted(self.done.values(), key=sk)).to_csv(os.path.join(self.out_dir, "results.csv"),
                                                                       index=False)

    # -- instances / library ---------------------------------------------------
    def _save(self, inst: Instance, layout: str, timetable: str, targets: str, seed: int) -> None:
        d = C.ensure_dir(os.path.join(self.out_dir, "instances"))
        p = os.path.join(d, f"{layout}_{timetable}_{targets}_seed{seed}.json")
        if not os.path.exists(p):
            inst.save(p)

    def _check_md5(self, inst: Instance, seed: int) -> str:
        h = C.demand_md5(inst)
        prev = self.md5.setdefault(int(seed), h)
        assert prev == h, f"seed {seed}: demand md5 {h} differs from {prev} (byte-identical demand violated)"
        return h

    def context(self, targets: str, layout: str, seed: int, timetable: str) -> Dict[str, Any]:
        """Instance, library and the five policy runs of one (layout, timetable, targets, seed);
        the library is built once per (layout, seed, targets) and rebound across timetables."""
        lk = (layout, int(seed), targets)
        if self._lib_key != lk:
            self._lib_key, self._lib, self._ctx = lk, None, {}
        ck = (timetable, targets)
        if ck in self._ctx:
            return self._ctx[ck]
        inst = target_copy(written_m1(make_x2_instance(seed, layout, timetable)), targets)
        assert inst.meta["layout"] == layout and int(inst.meta["seed"]) == int(seed)
        self._check_md5(inst, seed)
        self._save(inst, layout, timetable, targets, seed)
        if self._lib is None:
            pruning = C.pruning_for(inst, reachable=self.reachable)
            self._lib, self._lib_build = C.build_library(inst, pruning)
            lib = self._lib
        else:
            lib = rebind_library(self._lib, inst)
            if self.verify_rebind:
                fresh, _ = C.build_library(inst, dict(self._lib.options))
                assert len(fresh) == len(lib) and all(
                    (a.k, a.kind, a.src, a.dst, a.l, a.u, a.order, a.fac, a.g) ==
                    (b.k, b.kind, b.src, b.dst, b.l, b.u, b.order, b.fac, b.g)
                    for a, b in zip(fresh.arcs, lib.arcs)), "rebound library differs from a fresh build"
                print(f"# rebind verified: {layout}/{timetable}/{targets}/seed{seed} {len(lib):,} arcs", flush=True)
        bases: Dict[str, Dict[str, Any]] = {}
        for label, (variant, over) in BASELINES.items():
            params = C.baseline_variant_params(variant, inst, **over)
            base = C.run_baseline_case(inst, lib, params, label=label)
            bases[label] = base
            k = baseline_key(layout, timetable, targets, seed, label)
            if k not in self.done:
                self.emit(baseline_row(inst, lib, self._lib_build, label, base))
        ctx = {"inst": inst, "lib": lib, "bases": bases, "extra_starts": {}}
        self._ctx[ck] = ctx
        return ctx

    # -- ILP schedules (saved for analysis and as MIP starts of the transfers-free cells) --------
    def schedule_path(self, layout: str, timetable: str, targets: str, seed: int, switch: str) -> str:
        d = C.ensure_dir(os.path.join(self.out_dir, "schedules"))
        tt = "any" if switch == "none" else timetable
        return os.path.join(d, f"{layout}_{tt}_{targets}_seed{int(seed)}_ilp_{switch}.json")

    def load_none_start(self, layout: str, targets: str, seed: int) -> Optional[Tuple[float, Schedule]]:
        """``(total, schedule)`` of the solved ILP ``none`` cell of this (layout, targets, seed): h = z = 0
        and check-clean, hence feasible for the transfers-free model of either timetable."""
        row = self.done.get(ilp_key(layout, "any", targets, seed, "none"))
        p = self.schedule_path(layout, "any", targets, seed, "none")
        if row is None or row.get("total") is None or not os.path.exists(p) or not row.get("check_ok"):
            return None
        with open(p, "r", encoding="utf-8") as fh:
            return float(row["total"]), Schedule.from_dict(json.load(fh))

    # -- MIP start --------------------------------------------------------------
    def mip_start(self, ctx: Dict[str, Any], switch: str) -> Tuple[Optional[Schedule], str]:
        """Cheapest clean start: the policy schedules without reported family (for ``none`` also
        without transfer) and, for ``free``, the solved ILP ``none`` schedule of the same (layout,
        targets, seed) (feasible with h = z = 0); then the fallbacks of :data:`START_FALLBACKS`;
        else the cheapest policy schedule, unverified."""
        inst, lib = ctx["inst"], ctx["lib"]

        def ok(b: Dict[str, Any]) -> bool:
            if b.get("families"):
                return False
            return switch != "none" or int(b["metrics"]["transfers_used"]) == 0

        cands: List[Tuple[float, str, Schedule]] = [(b["cost"]["total"], lab, b["schedule"])
                                                    for lab, b in ctx["bases"].items() if ok(b)]
        if switch == "free":
            ns = self.load_none_start(inst.meta["layout"], inst.meta["end_targets"], int(inst.meta["seed"]))
            if ns is not None:
                cands.append((ns[0], "ilp_none", ns[1]))
        if cands:
            _, lab, sched = min(cands, key=lambda x: x[0])
            return sched, lab
        for variant, over in START_FALLBACKS:
            if switch == "none" and over.get("transfer_rule", "NONE") != "NONE":
                continue
            tag = variant + (":" + over["transfer_rule"] if "transfer_rule" in over else "")
            if tag not in ctx["extra_starts"]:
                try:
                    ctx["extra_starts"][tag] = C.run_baseline_case(inst, lib, C.baseline_variant_params(variant, inst, **over),
                                                                   label=tag)
                except (ValueError, KeyError, TypeError) as exc:
                    ctx["extra_starts"][tag] = {"error": f"{type(exc).__name__}: {exc}", "families": {"error": 1}}
            b = ctx["extra_starts"][tag]
            if "schedule" in b and ok(b):
                return b["schedule"], tag
        pool = [(b["cost"]["total"], lab, b) for lab, b in ctx["bases"].items()
                if switch != "none" or int(b["metrics"]["transfers_used"]) == 0]
        if not pool:
            return None, "none"
        _, lab, b = min(pool, key=lambda x: x[0])
        return b["schedule"], f"{lab}(unverified)"

    # -- one ILP cell -------------------------------------------------------------
    def run_item(self, item: WorkItem) -> None:
        targets, layout, seed, switch, timetable = item
        tl = self.budget.solve_limit(self.tl)
        if tl is None:       # checked before any library / policy work so that skipping is cheap
            self.emit(skipped_row(layout, timetable, targets, seed, switch,
                                  f"wall budget exhausted after {self.budget.elapsed():.0f}s"))
            return
        ctx = self.context(targets, layout, seed, timetable)
        inst, lib, bases = ctx["inst"], ctx["lib"], ctx["bases"]
        tl = self.budget.solve_limit(self.tl)
        if tl is None:
            self.emit(skipped_row(layout, timetable, targets, seed, switch,
                                  f"wall budget exhausted after {self.budget.elapsed():.0f}s (after policies)"))
            return
        start, start_label = self.mip_start(ctx, switch)
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads, label="ilp",
                             no_transfers=(switch == "none"), params=dict(C.ILP_PARAMS_R3), **C.R5_ILP_KWARGS)
        row = ilp_row(inst, lib, self._lib_build, switch, rec, start_label, tl, bases, self.threads)
        if rec["schedule"] is not None:
            with open(self.schedule_path(layout, timetable, targets, seed, switch), "w", encoding="utf-8") as fh:
                json.dump(C.jsonable(rec["schedule"].to_dict()), fh)
        rec["schedule"] = None
        self.emit(row)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def _is_false(v: Any) -> bool:
    """True only for an explicit False (numpy / pandas booleans included; None / NaN are not False)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return False
    if isinstance(v, str):
        return v.strip().lower() == "false"
    try:
        return not bool(v)
    except (TypeError, ValueError):
        return False


def _num(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_frame(out_dir: str) -> pd.DataFrame:
    rows = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not rows:
        raise SystemExit(f"no records in {out_dir}")
    last: Dict[Key, Dict[str, Any]] = {}
    for r in rows:
        last[key_of(r)] = r
    df = C.records_to_frame(list(last.values()))
    num = [c for c in df.columns if c.startswith(("gap", "total", "C_", "baseline_total", "best_rule_total", "r5_"))]
    return _num(df, num + ["seed", "runtime_s", "n_unserved", "served_share", "transfers_used", "batteries_moved",
                           "stockout_slots_total", "m_t_max", "unserved", "response", "lateness", "obj", "bound"])


def _ilp(df: pd.DataFrame, layout: str, tt: str, targets: str, switch: str) -> pd.DataFrame:
    sub = df[(df.method == "ilp") & (df.layout == layout) & (df.targets == targets) & (df.variant == switch)]
    sub = sub[sub.timetable == ("any" if switch == "none" else tt)]
    return sub[sub["total"].notna()] if "total" in sub else sub.iloc[0:0]


def _base(df: pd.DataFrame, layout: str, tt: str, targets: str, label: str) -> pd.DataFrame:
    sub = df[(df.method == "baseline") & (df.layout == layout) & (df.timetable == tt) & (df.targets == targets)
             & (df.variant == label)]
    return sub[sub["total"].notna()]


def _by_seed(sub: pd.DataFrame, col: str = "total") -> Dict[int, float]:
    return {int(s): float(v) for s, v in zip(sub.seed, sub[col]) if v is not None and not pd.isna(v)}


def _diff(a: Dict[int, float], b: Dict[int, float]) -> List[float]:
    return [a[s] - b[s] for s in sorted(set(a) & set(b))]


def _ms(vals: Sequence[float]) -> str:
    if not vals:
        return "-"
    v = np.asarray(vals, dtype=float)
    sd = float(v.std(ddof=1)) if len(v) > 1 else 0.0
    return f"{v.mean():.2f} +- {sd:.2f} (n {len(v)})"


def _best_rule_by_seed(df: pd.DataFrame, layout: str, tt: str, targets: str, col: str = "total",
                       labels: Sequence[str] = BEST_RULE) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for lab in labels:
        for s, v in _by_seed(_base(df, layout, tt, targets, lab), col).items():
            out[s] = min(out.get(s, math.inf), v)
    return out


def analyse(out_dir: str) -> str:
    df = load_frame(out_dir)
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    ilp = df[df.method == "ilp"]
    lines: List[str] = ["# X2 (round 5) -- transfers and separation (usd4h, ebaas, seeds 0-4)", ""]
    lines += [f"Gurobi Threads {C.THREADS}, Seed 0, TimeLimit {TIME_LIMIT:.0f} s, aggregated ILP (O1). "
              f"Gap = 100 (baseline - ILP) / baseline. best_rule = min over {', '.join(BEST_RULE)} per instance. "
              "Headline = relaxed control (rho 0, R_end 0); written = rho 0.5, R_end_j 1 at swap+charge sites, "
              "0 at swap-only sites (M1) = price of recovery. ILP 'none' (h = z = 0) is timetable independent "
              "(solved on the r3 instance, timetable 'any').", ""]
    # status
    st = ilp.groupby(["targets", "variant", "timetable", "status"]).size().reset_index(name="n")
    lines += ["## Solver status", "", C.markdown_table(st, list(st.columns), 0), ""]
    if not ilp.empty and "runtime_s" in ilp:
        lines += [f"ILP runtime: mean {ilp.runtime_s.mean():.1f} s, max {ilp.runtime_s.max():.1f} s, "
                  f"{int((ilp.status == 'OPTIMAL').sum())} OPTIMAL of {len(ilp)}; max gap "
                  f"{C.fmt(pd.to_numeric(ilp.get('gap'), errors='coerce').max(), 4)}.", ""]
    md5 = df.groupby("seed")["demand_md5"].nunique().to_dict() if "demand_md5" in df else {}
    lines += [f"Demand md5 per seed (distinct values, must be 1): {md5}.", ""]
    # headline / per targets
    for targets in TARGETS:
        rows = []
        for layout in LAYOUTS:
            for tt in TIMETABLES:
                for switch in SWITCHES:
                    sub = _ilp(df, layout, tt, targets, switch)
                    if switch == "none" and tt != "r3":
                        continue
                    if sub.empty:
                        continue
                    g = lambda c: (float(sub[c].mean()) if c in sub and sub[c].notna().any() else None)  # noqa: E731
                    rows.append({"layout": layout, "timetable": "any" if switch == "none" else tt, "ILP": switch,
                                 "n": len(sub), "ILP_total": g("total"), "ILP_C_end_adjust": g("C_end_adjust"),
                                 "best_rule_total": g("best_rule_total"),
                                 "gap_best_rule_%": g("gap_vs_best_rule_pct"),
                                 "gap_best_rule_adj_%": g("gap_vs_best_rule_pct_end_adjusted"),
                                 "gap_best_notransfer_%": g("gap_vs_best_rule_notransfer_pct"),
                                 "gap_r2_%": g("gap_vs_r2_pct"), "gap_r2_reorder_%": g("gap_vs_r2_reorder_pct"),
                                 "gap_r5_transfer_%": g("gap_vs_r5_transfer_pct"), "gap_r5_%": g("gap_vs_r5_pct"),
                                 "served": g("served_share"), "transfers": g("transfers_used"),
                                 "moved": g("batteries_moved")})
        tdf = pd.DataFrame(rows)
        title = "Headline (relaxed control, rho 0, R_end 0)" if targets == "relaxed" else "Written targets (M1)"
        lines += [f"## {title}: ILP vs policies (seed means)", "",
                  C.markdown_table(tdf, list(tdf.columns), 2) if not tdf.empty else "-", ""]
    # baselines
    rows = []
    for targets in TARGETS:
        for layout in LAYOUTS:
            for tt in TIMETABLES:
                r: Dict[str, Any] = {"targets": targets, "layout": layout, "timetable": tt}
                for lab in BASELINES:
                    sub = _base(df, layout, tt, targets, lab)
                    r[lab] = float(sub.total.mean()) if not sub.empty else None
                sub = _base(df, layout, tt, targets, "r2")
                r["r2_C_end_adjust"] = float(sub.C_end_adjust.mean()) if not sub.empty and "C_end_adjust" in sub else None
                rows.append(r)
    bdf = pd.DataFrame(rows)
    lines += ["## Policy totals (seed means, USD per 4 h window)", "", C.markdown_table(bdf, list(bdf.columns), 2), ""]
    # value of transfers
    rows = []
    for targets in TARGETS:
        for layout in LAYOUTS:
            for tt in TIMETABLES:
                none = _by_seed(_ilp(df, layout, tt, targets, "none"))
                free = _by_seed(_ilp(df, layout, tt, targets, "free"))
                d = _diff(none, free)
                rows.append({"targets": targets, "layout": layout, "timetable": tt,
                             "ILP value of transfers none - free (USD)": _ms(d),
                             "share of ILP(none) %": _ms([100 * x / none[s] for x, s in
                                                          zip(d, sorted(set(none) & set(free)))])})
    vdf = pd.DataFrame(rows)
    lines += ["## Value of transfers (ILP)", "", C.markdown_table(vdf, list(vdf.columns)), ""]
    # separation cost
    rows = []
    for targets in TARGETS:
        for tt in TIMETABLES:
            for switch in SWITCHES:
                if switch == "none" and tt != "r3":
                    continue
                co = _by_seed(_ilp(df, "colocated", tt, targets, switch))
                for layout in LAYOUTS[1:]:
                    sep = _by_seed(_ilp(df, layout, tt, targets, switch))
                    bsep = _best_rule_by_seed(df, layout, tt, targets)
                    bco = _best_rule_by_seed(df, "colocated", tt, targets)
                    rows.append({"targets": targets, "timetable": "any" if switch == "none" else tt, "ILP": switch,
                                 "layout": layout, "ILP sep - colocated": _ms(_diff(sep, co)),
                                 "best_rule sep - colocated": _ms(_diff(bsep, bco))})
    sdf = pd.DataFrame(rows)
    lines += ["## Separation cost (separated - colocated, USD)", "", C.markdown_table(sdf, list(sdf.columns)), ""]
    # REORDER_POINT vs COST_AWARE
    rows = []
    for targets in TARGETS:
        for layout in LAYOUTS:
            for tt in TIMETABLES:
                r2 = _by_seed(_base(df, layout, tt, targets, "r2"))
                ro = _by_seed(_base(df, layout, tt, targets, "r2_reorder"))
                ca = _by_seed(_base(df, layout, tt, targets, "r5_transfer"))
                rr = _by_seed(_base(df, layout, tt, targets, "r5_range"))
                r5 = _by_seed(_base(df, layout, tt, targets, "r5"))
                common = sorted(set(r2) & set(ro) & set(ca))
                rows.append({"targets": targets, "layout": layout, "timetable": tt,
                             "REORDER loss r2_reorder - r2": _ms(_diff(ro, r2)),
                             "COST_AWARE loss r5_transfer - r2": _ms(_diff(ca, r2)),
                             "r5 - r5_range": _ms(_diff(r5, rr)),
                             "COST_AWARE <= r2 (seeds)": f"{sum(ca[s] <= r2[s] + 1e-6 for s in common)}/{len(common)}",
                             "COST_AWARE < REORDER (seeds)": f"{sum(ca[s] < ro[s] - 1e-6 for s in common)}/{len(common)}"})
    cdf = pd.DataFrame(rows)
    lines += ["## Does COST_AWARE (M3) remove the REORDER_POINT loss? (USD; positive = worse than r2)", "",
              C.markdown_table(cdf, list(cdf.columns)), ""]
    # cyclic vs r3
    rows = []
    for targets in TARGETS:
        for layout in LAYOUTS:
            ilp_c = _ilp(df, layout, "cyclic", targets, "free")
            ilp_r = _ilp(df, layout, "r3", targets, "free")
            r: Dict[str, Any] = {"targets": targets, "layout": layout,
                                 "ILP free cyclic - r3": _ms(_diff(_by_seed(ilp_c), _by_seed(ilp_r))),
                                 "ILP transfers used r3 / cyclic": f"{C.fmt(ilp_r.transfers_used.mean() if not ilp_r.empty else None, 1)} / "
                                                                   f"{C.fmt(ilp_c.transfers_used.mean() if not ilp_c.empty else None, 1)}",
                                 "ILP moved r3 / cyclic": f"{C.fmt(ilp_r.batteries_moved.mean() if not ilp_r.empty else None, 1)} / "
                                                          f"{C.fmt(ilp_c.batteries_moved.mean() if not ilp_c.empty else None, 1)}"}
            for lab in ("r2_reorder", "r5_transfer", "r5"):
                r[f"{lab} cyclic - r3"] = _ms(_diff(_by_seed(_base(df, layout, "cyclic", targets, lab)),
                                                    _by_seed(_base(df, layout, "r3", targets, lab))))
            rows.append(r)
    ydf = pd.DataFrame(rows)
    lines += ["## Cyclic (M8) vs hub-spoke / site-site (round-3) timetable (USD)", "",
              C.markdown_table(ydf, list(ydf.columns)), ""]
    # price of recovery
    rows = []
    for layout in LAYOUTS:
        for tt in TIMETABLES:
            for switch in SWITCHES:
                if switch == "none" and tt != "r3":
                    continue
                w = _ilp(df, layout, tt, "written", switch)
                rx = _ilp(df, layout, tt, "relaxed", switch)
                rows.append({"layout": layout, "timetable": "any" if switch == "none" else tt, "ILP": switch,
                             "ILP written - relaxed (total)": _ms(_diff(_by_seed(w), _by_seed(rx))),
                             "ILP written - relaxed (end-adjusted)": _ms(_diff(_by_seed(w, "total_end_adjusted"),
                                                                              _by_seed(rx, "total_end_adjusted"))),
                             "C_end_adjust written / relaxed": f"{C.fmt(w.C_end_adjust.mean() if not w.empty else None, 2)} / "
                                                                f"{C.fmt(rx.C_end_adjust.mean() if not rx.empty else None, 2)}",
                             "best_rule written - relaxed": _ms(_diff(_best_rule_by_seed(df, layout, "r3" if switch == "none" else tt, "written"),
                                                                      _best_rule_by_seed(df, layout, "r3" if switch == "none" else tt, "relaxed")))})
    pdf = pd.DataFrame(rows)
    lines += ["## Price of recovery (written - relaxed, USD)", "", C.markdown_table(pdf, list(pdf.columns)), ""]
    # A3 metric pack
    keys = ["r5_min_sbur", "r5_bsr", "r5_outage_rate", "r5_empty_km_share", "r5_mean_station_time_min",
            "r5_peak_kw_network", "r5_kwh_purchased", "r5_batteries_saved_total", "C_end_adjust"]
    rows = []
    for targets in TARGETS:
        for layout in LAYOUTS:
            for tt in TIMETABLES:
                for method, lab in (("ilp", "free"), ("baseline", "r2"), ("baseline", "r5")):
                    sub = (_ilp(df, layout, tt, targets, lab) if method == "ilp" else _base(df, layout, tt, targets, lab))
                    if sub.empty:
                        continue
                    r = {"targets": targets, "layout": layout, "timetable": tt, "method": f"{method}:{lab}"}
                    for k in keys:
                        r[k.replace("r5_", "")] = float(sub[k].mean()) if k in sub and sub[k].notna().any() else None
                    rows.append(r)
    adf = pd.DataFrame(rows)
    lines += ["## A3 metric pack (seed means)", "", C.markdown_table(adf, list(adf.columns), 3) if not adf.empty else "-", ""]
    # anomalies
    an: List[str] = []
    for _, r in ilp.iterrows():
        tag = f"{r.layout}/{r.timetable}/{r.targets}/seed{int(r.seed)}/{r.variant}"
        if r.status == C.SKIPPED_BUDGET:
            an.append(f"{tag}: SKIPPED_BUDGET")
            continue
        if r.get("total") is None or pd.isna(r.get("total")):
            an.append(f"{tag}: no incumbent (status {r.status})")
            continue
        if _is_false(r.get("check_ok")):
            an.append(f"{tag}: ILP schedule fails check {r.get('reported_families')}")
        cmp_col = "ilp_le_best_rule" if r.variant == "free" else "ilp_le_best_rule_notransfer"
        if _is_false(r.get(cmp_col)):
            an.append(f"{tag}: ILP total above {cmp_col[7:]} (status {r.status}, gap {r.get('gap')})")
        if _is_false(r.get("mip_start_accepted")):
            an.append(f"{tag}: MIP start {r.get('mip_start_variant')} not accepted")
        if r.status not in ("OPTIMAL",):
            an.append(f"{tag}: status {r.status}, gap {r.get('gap')}")
    base = df[df.method == "baseline"]
    for _, r in base.iterrows():
        if _is_false(r.get("check_ok_modulo_report_only")):
            an.append(f"{r.layout}/{r.timetable}/{r.targets}/seed{int(r.seed)}/{r.variant}: policy violates "
                      f"{r.reported_families} beyond (9)/(17)/(18)")
    lines += ["## Anomalies", ""] + ([f"- {a}" for a in an] or ["- none"]) + [""]
    figs = make_figures(df, out_dir)
    lines += ["## Figures", ""] + [f"- `{os.path.basename(p)}`" for p in figs] + [""]
    md = os.path.join(out_dir, "RESULTS.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return md


def make_figures(df: pd.DataFrame, out_dir: str) -> List[str]:
    out: List[str] = []
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
    series = [("ilp", "free", "r3", "ILP free, r3", "#1f77b4", 1.0), ("ilp", "free", "cyclic", "ILP free, cyclic", "#1f77b4", 0.5),
              ("ilp", "none", "r3", "ILP h = z = 0", "#d62728", 1.0),
              ("best", None, "r3", "best_rule, r3", "#7f7f7f", 1.0), ("best", None, "cyclic", "best_rule, cyclic", "#7f7f7f", 0.5),
              ("base", "r2_reorder", "r3", "r2 REORDER_POINT, r3", "#ff7f0e", 0.8)]
    width = 0.13
    for ax, targets in zip(axes, TARGETS):
        for si, (kind, sw, tt, label, color, alpha) in enumerate(series):
            labelled = False
            for li, layout in enumerate(LAYOUTS):
                if kind == "ilp":
                    vals = list(_by_seed(_ilp(df, layout, tt, targets, sw)).values())
                elif kind == "best":
                    vals = list(_best_rule_by_seed(df, layout, tt, targets).values())
                else:
                    vals = list(_by_seed(_base(df, layout, tt, targets, sw)).values())
                if not vals:
                    continue
                x = li + (si - 2.5) * width
                ax.bar(x, float(np.mean(vals)), width, color=color, alpha=alpha, label=None if labelled else label)
                labelled = True
                ax.scatter([x] * len(vals), vals, s=8, color="black", zorder=3)
        ax.set_xticks(range(len(LAYOUTS)))
        ax.set_xticklabels([E3U.LAYOUT_LABEL[l] for l in LAYOUTS], fontsize=8)
        ax.set_title(f"{targets} targets")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("total cost (26), USD per 4 h window")
    if axes[0].get_legend_handles_labels()[0]:
        axes[0].legend(fontsize=7, frameon=False, ncol=2)
    fig.suptitle("X2: cost by layout, timetable and transfer switch (usd4h, ebaas; bars = seed mean)")
    fig.tight_layout()
    p = os.path.join(out_dir, "fig_cost_by_layout.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    out.append(p)
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--seeds", nargs="*", type=int, default=list(SEEDS))
    ap.add_argument("--layouts", nargs="*", default=list(LAYOUTS), choices=list(LAYOUTS))
    ap.add_argument("--targets", nargs="*", default=list(TARGETS), choices=list(TARGETS),
                    help="target settings, in order of work (default relaxed then written)")
    ap.add_argument("--timetables", nargs="*", default=list(TIMETABLES), choices=list(TIMETABLES))
    ap.add_argument("--switches", nargs="*", default=list(SWITCHES), choices=list(SWITCHES))
    ap.add_argument("--smoke-time-limit", type=float, default=30.0)
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--wall-budget", type=float, default=WALL_BUDGET_S, help="seconds")
    ap.add_argument("--est-solve-s", type=float, default=105.0, help="assumed mean solve time for the dry-run estimate")
    ap.add_argument("--est-group-s", type=float, default=20.0,
                    help="assumed library + policy overhead per (targets, layout, seed) for the estimate")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="layout separated_1hub, seed 0, relaxed + written, all switches / timetables, TimeLimit 30 s")
    ap.add_argument("--verify-rebind", action="store_true", help="rebuild every rebound library and compare (slow)")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    if args.smoke and args.out_dir is None:
        raise SystemExit("--smoke needs --out-dir (a scratch folder)")
    out_dir = args.out_dir or OUT_DIR
    if args.analyse:
        print(analyse(out_dir))
        return {"analysed": out_dir}
    if args.smoke:
        seeds, layouts, tl, wall = [0], ["separated_1hub"], args.smoke_time_limit, 3600.0
    else:
        seeds, layouts, tl, wall = args.seeds, args.layouts, args.time_limit, args.wall_budget
    existing = {key_of(r): r for r in C.load_jsonl(os.path.join(out_dir, RECORDS))}
    plan = build_plan(existing, seeds, layouts, targets_order=args.targets, timetables=args.timetables,
                      switches=args.switches, time_limit=tl)
    summary = plan_summary(plan, tl, args.est_solve_s, args.est_group_s)
    summary.update(out_dir=out_dir, threads=args.threads, time_limit=tl, wall_budget_min=wall / 60.0,
                   existing_rows=len(existing), seeds=list(seeds), layouts=list(layouts), targets=list(args.targets),
                   timetables=list(args.timetables), switches=list(args.switches))
    if args.dry_run:
        # instances only (no library, no solve): byte-identical demand and the timetables
        md5: Dict[int, set] = {}
        for seed in seeds:
            for layout in layouts:
                for tt in TIMETABLES:
                    for targets in TARGETS:
                        inst = target_copy(written_m1(make_x2_instance(seed, layout, tt)), targets)
                        md5.setdefault(seed, set()).add(C.demand_md5(inst))
                        if seed == seeds[0] and targets == "written":
                            print(f"#  {layout:16s} {tt:6s} services {len(inst.services):3d} rho {inst.rho} R_end "
                                  f"{ {f.id: f.R_end for f in inst.facilities} } f {sorted({round(s.f, 3) for s in inst.services})}")
        assert all(len(v) == 1 for v in md5.values()), md5
        print("# plan (targets, layout, seed, switch, timetable):")
        for item in plan:
            print("  ", item)
        summary["demand_md5_per_seed"] = {s: sorted(v)[0] for s, v in md5.items()}
        print(json.dumps(summary, indent=1, default=str))
        return summary
    budget = C.WallBudget(wall, margin_s=(5.0 if args.smoke else 90.0), min_solve_s=(5.0 if args.smoke else 30.0))
    runner = Runner(out_dir, tl, args.threads, budget, verify_rebind=(args.verify_rebind or args.smoke))
    print(f"# X2 plan {json.dumps(summary, default=str)}", flush=True)
    for item in plan:
        runner.run_item(item)
    wall_s = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall_s, "plan": summary, "finished": time.strftime("%Y-%m-%d %H:%M:%S")},
                            default=str) + "\n")
    print(f"# X2 finished: {runner.n_runs} rows in {wall_s / 60:.1f} min", flush=True)
    try:
        print(analyse(out_dir))
    except Exception as exc:  # noqa: BLE001
        print(f"# analyse failed: {type(exc).__name__}: {exc}", flush=True)
    return summary


if __name__ == "__main__":
    main()
