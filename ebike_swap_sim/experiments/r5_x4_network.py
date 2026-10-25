"""Experiment X4 (round 5, plan item A5) -- value of the swap network: the eBaaS "ride home
to charge" (EIEM) counterfactual against the swap network, under the ILP and the rule policies.

Question
--------
How much of the cost of a delivery window is due to the swap NETWORK (infrastructure) and how
much to COORDINATING it (decisions)?  On byte-identical demand, every instance is solved twice:

* ``network`` -- the instance as generated (3 co-located swap + charge sites);
* ``home``    -- :func:`ebike_swap_sim.generator.home_charging_counterfactual`: every network
  facility and service removed, one swap-only ``HOMEn`` per depot where a "swap" is a recharge
  of the rider's own battery (``sigma_j`` = 25 slots at 0.24 kW for L 24, stock sized so that
  (12)-(18) never bind, no setup cost).  Orders, bikes, routes are unchanged
  (``common.demand_md5`` asserted equal for the pair and for every row of a seed).

and each of the two by the coordinator (E2 ILP, aggregated flow O1) and by the rule policies.

Cells (``notes/reading_to_model.md`` item A5; DECISIONS "R5 implementation notes")
----------------------------------------------------------------------------------
* ``usd4h_ebaas``: ``usd4h`` at demand x1 (1.5 orders per bike-hour, 6 bikes / 36 orders,
  4 h, ``usd_sunk``) with the eBaaS energy calibration (``energy_calibration='ebaas'``: 25 Wh/km,
  eps 25 Wh, L 24, concat rounding), seeds 0-9; reachable pruning (lossless, round 2);
* ``r5_stress4h``: the round-5 single-ILP family (6 bikes / 48 orders / H 48 / L 24, TOU tariff),
  seeds 0-4; ``common.pruning_for`` (R5 reachable pruning).

Methods per (case, seed, infrastructure)
----------------------------------------
* policies ``r2`` (R2.3 rules, ``baseline``), ``r5_range``, ``r5_transfer`` (only when the
  instance has transport services -- none of the two families has any, so it is recorded as
  not applicable), ``r5`` (``common.BASELINE_VARIANTS['baseline_r5*']``), each priced and checked
  by ``evaluate`` on the relaxed copy (the policy keeps its written DEMAND_AWARE reserve there,
  so its schedule is the written-instance schedule); ``best_rule`` = per instance and metric the
  minimum over ``r2``, ``r5_range``, ``r5_transfer`` (when services exist) and ``r5`` (derived in
  the analysis, the conservative comparison);
* ``ilp_relaxed`` -- HEADLINE: the like-for-like control (``common.relax_end_targets``: rho = 0,
  R_end = 0, the ``rho0_R0`` cell of ``common.boundary_grid``);
* ``ilp_written`` -- the written targets (rho 0.5, R_end_j 1): the price of recovery.  On the
  ``home`` instance (17) is void (R_end_j = 0 at the homes) and (18) is slack by construction
  (B_j sized for every possible recharge), so the written optimum IS the relaxed optimum: the
  row is recorded without a solve (``solve_mode = implied_by_construction``) after checking the
  relaxed schedule against (17)-(18) of the written home instance.

Gurobi: ``Threads 3``, ``Seed 0``, ``TimeLimit 300 s``, ``aggregate = True``
(``common.R5_ILP_KWARGS``), MIP start = the cheapest policy schedule that passes ``evaluate.check``
on the instance solved (for ``ilp_written`` also the relaxed ILP schedule and the
``common.MIP_START_FALLBACKS`` variants are candidates).  The A3 metric pack
(``metrics(...)['r5']``) and ``C_end_adjust`` / ``total_end_adjusted`` (M1) are recorded for
every row; ``total_end_adjusted`` also prices the home recharges (the station part of the M1
adjustment values the depleted batteries left at a home), which (28) cannot see.

Reported quantities (analysis, per seed, then mean and 95 % t-CI over seeds)
---------------------------------------------------------------------------
For a metric ``X`` (``total`` (26) and ``total_end_adjusted``), targets (relaxed headline,
written) and a policy ``P`` (``r2``, ``best_rule``, ``r5``) with cells ``H_P``, ``H_ILP``,
``N_P``, ``N_ILP``:

* value of the network under P / under the ILP: ``VoN_P = H_P - N_P``, ``VoN_ILP = H_ILP - N_ILP``
  (also in % of the home cost);
* value of coordination on the network / at home: ``VoC_N = N_P - N_ILP``, ``VoC_H = H_P - H_ILP``
  (headline gap convention ``(baseline - ILP) / baseline``);
* 2x2 decomposition of the total ``H_P - N_ILP = VoN_P + VoC_N = VoC_H + VoN_ILP``: interaction
  ``VoC_N - VoC_H = VoN_ILP - VoN_P`` and the Shapley shares ``network = (VoN_P + VoN_ILP) / 2``,
  ``coordination = (VoC_N + VoC_H) / 2`` (they add up to the total);
* eBaaS-comparable metrics per cell: empty km per rider-hour (reposition arcs, A3
  ``empty_km_per_bike_hour``), orders served per rider-hour, bike km per rider-hour, orders given
  up, served share, home recharges / swaps per rider-hour.

Protocol (round-3/4 patterns): append-only ``records.jsonl`` keyed by
``(case, seed, infra, method)`` (resume skips done keys; ``SKIPPED_BUDGET`` rows are retried),
``results.csv`` refreshed after each run, ``instances/*.json``, ``schedules/*.json`` (ILP
incumbents, reused as MIP starts on resume), ``run_stdout.log`` via the launcher, one printed JSON
line per run, a :class:`experiments.common.WallBudget` (default 120 min; the last solve is
shortened, later ones are recorded as ``SKIPPED_BUDGET``).  Order of work: phase ``a`` = policies
+ ``ilp_relaxed`` on both infrastructures of every seed (the headline), phase ``b`` = the
network ``ilp_written`` cells (price of recovery).  Outputs under ``outputs/r5_x4_network/``:
``records.jsonl``, ``results.csv``, ``decomposition.csv``, ``summary.csv``, ``ebaas_metrics.csv``,
``RESULTS.md``, ``x4_decomposition.png``, ``wall_time.json``.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r5_x4_network.py --dry-run     # plan only, nothing solved or written
    python3 experiments/r5_x4_network.py --smoke --out-dir /tmp/x4_smoke   # reduced instances, Threads 1, 30 s
    python3 experiments/r5_x4_network.py               # full run (resumable), Threads 3, 300 s, 120 min budget
    python3 experiments/r5_x4_network.py --analyse     # tables, figure, RESULTS.md from records.jsonl

The E2 model (``ilp.py`` / ``arcs.py`` / ``evaluate.py``) is not touched.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ebike_swap_sim import Instance, Schedule, build_arcs, check, cost, metrics  # noqa: E402
from ebike_swap_sim import generator as G  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import e2u_coord_usd as E2U  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r5_x4_network")
RECORDS = "records.jsonl"
TIME_LIMIT = 300.0
WALL_BUDGET_S = 120 * 60.0
ILP_PARAMS = dict(C.ILP_PARAMS_R3)            # {'Seed': 0}
ILP_KWARGS = dict(C.R5_ILP_KWARGS)            # {'aggregate': True}

#: case -> (family of experiments.common.FAMILIES, make_instance overrides, seeds, pruning overrides)
CASES: Dict[str, Dict[str, Any]] = {
    "usd4h_ebaas": {"family": "usd4h", "overrides": {"orders_per_bike_hour": 1.5, "energy_calibration": "ebaas"},
                    "seeds": list(range(10)), "pruning": {"reachable": True}, "demand_mult": 1.0,
                    "label": "usd4h x1 (eBaaS energy)"},
    "r5_stress4h": {"family": "r5_stress4h", "overrides": {}, "seeds": list(range(5)), "pruning": {},
                    "demand_mult": None, "label": "r5_stress4h (6 bikes)"},
}
CASE_ORDER = ("usd4h_ebaas", "r5_stress4h")
#: Smoke instances: the same builders with a reduced fleet and window (no full-size solves).
SMOKE_OVERRIDES = {"n_bikes": 3, "window_h": 2.0}
INFRAS = ("network", "home")
#: rule policies: short name -> common.BASELINE_VARIANTS key
POLICIES: Dict[str, str] = {"r2": "baseline", "r5_range": "baseline_r5_range",
                            "r5_transfer": "baseline_r5_transfer", "r5": "baseline_r5"}
#: policies entering best_rule (r5_transfer only when the instance has services)
BEST_RULE_OVER = ("r2", "r5_range", "r5_transfer", "r5")
ILP_METHODS = ("ilp_relaxed", "ilp_written")
METHODS = tuple(POLICIES) + ILP_METHODS
REPORT_POLICIES = ("r2", "best_rule", "r5")
METRICS_X = ("total", "total_end_adjusted")

Key = Tuple[str, int, str, str]          # (case, seed, infra, method)
WorkItem = Tuple[str, str, int, str, str]  # (phase, case, seed, infra, method)


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def make_network(case: str, seed: int, smoke: bool = False) -> Instance:
    """Network instance of ``case`` / ``seed`` (``common.make_instance`` with the case
    overrides; ``SMOKE_OVERRIDES`` with ``smoke``)."""
    spec = CASES[case]
    kw = dict(spec["overrides"])
    if smoke:
        kw.update(SMOKE_OVERRIDES)
    inst = C.make_instance(spec["family"], seed=seed, **kw)
    tag = "smoke-" if smoke else ""
    inst.meta["name"] = f"x4-{tag}{case}-K{len(inst.bikes)}-I{len(inst.orders)}-seed{seed}"
    inst.meta["seed"] = int(seed)
    inst.meta["x4_case"] = case
    inst.meta["x4_infra"] = "network"
    if spec.get("demand_mult") is not None:
        inst.meta["demand_mult"] = float(spec["demand_mult"])
    return inst


def make_home(net: Instance) -> Instance:
    """A5 counterfactual of ``net`` (``generator.home_charging_counterfactual``, defaults
    0.24 kW / return at 25 %); asserts byte-identical demand."""
    home = G.home_charging_counterfactual(net)
    home.meta["name"] = net.meta["name"] + "-home"
    home.meta["x4_infra"] = "home"
    if C.demand_md5(home) != C.demand_md5(net):
        raise AssertionError(f"home counterfactual changed the demand side of {net.meta['name']}")
    return home


def make_pair(case: str, seed: int, smoke: bool = False) -> Dict[str, Instance]:
    net = make_network(case, seed, smoke)
    return {"network": net, "home": make_home(net)}


def pruning_of(case: str, inst: Instance) -> Dict[str, Any]:
    return C.pruning_for(inst, **CASES[case]["pruning"])


# ---------------------------------------------------------------------------
# records
# ---------------------------------------------------------------------------
def key_of(row: Dict[str, Any]) -> Key:
    return (str(row["case"]), int(row["seed"]), str(row["infra"]), str(row["method"]))


def last_per_key(rows: Sequence[Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
    out: Dict[Key, Dict[str, Any]] = {}
    for r in rows:
        out[key_of(r)] = r
    return out


def row_done(row: Optional[Dict[str, Any]], retry_unsolved: bool = False) -> bool:
    """Done = policy row, not-applicable row, implied row, or an ILP row with an outcome
    (``SKIPPED_BUDGET`` and errors are retried; with ``retry_unsolved`` also ILP rows that are
    neither OPTIMAL nor within 1 % gap)."""
    if row is None:
        return False
    st = row.get("status")
    if st in (C.SKIPPED_BUDGET, "ERROR", None):
        return False
    if st in ("POLICY", "NOT_APPLICABLE") or row.get("solve_mode") == "implied_by_construction":
        return True
    if retry_unsolved:
        return C.reusable_ilp_row(st, row.get("mip_gap"))
    return True


def _rider_hours(inst: Instance) -> float:
    return len(inst.bikes) * inst.H * inst.disc.Delta_h


def base_row(case: str, inst: Instance, lib_len: int, infra: str, method: str, targets: str) -> Dict[str, Any]:
    hc = inst.meta.get("home_charging") or {}
    co = inst.meta.get("costs") or {}
    return {
        "case": case, "family": CASES[case]["family"], "seed": int(inst.meta["seed"]), "infra": infra,
        "method": method, "targets": targets, "name": inst.meta["name"],
        "demand_md5": C.demand_md5(inst), "n_bikes": len(inst.bikes), "n_orders": len(inst.orders),
        "H": inst.H, "L": inst.L, "Delta_h": inst.disc.Delta_h, "rider_hours": _rider_hours(inst),
        "n_facilities": len(inst.facilities), "n_services": len(inst.services), "n_arcs": int(lib_len),
        "rho": float(inst.rho), "R_end_sum": int(sum(f.R_end for f in inst.facilities)),
        "B_sum": int(sum(int(f.B or 0) for f in inst.facilities)),
        "energy_calibration": (inst.meta.get("energy_calibration") or {}).get("name"),
        "tariff": (inst.meta.get("tariff") or {}).get("name") if isinstance(inst.meta.get("tariff"), dict)
        else inst.meta.get("tariff"),
        "coef_pi": co.get("pi"), "coef_pi_peak": co.get("pi_peak"),
        "home_sigma_slots": hc.get("sigma_slots"), "home_B": hc.get("B_home"), "home_n": len(hc.get("homes") or []),
        "home_kwh_per_charge": hc.get("kwh_per_home_charge"),
    }


def ebaas_cols(inst: Instance, met: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """eBaaS-comparable per-rider-hour metrics (EIEM counterfactual: invalid km, orders given up)."""
    if not met:
        return {}
    rh = _rider_hours(inst)
    r5 = met.get("r5") or {}
    return {
        "orders_per_rider_hour": met["n_served"] / rh if rh > 0 else None,
        "empty_km_per_rider_hour": r5.get("empty_km_per_bike_hour"),
        "bike_km_per_rider_hour": met["bike_km"] / rh if rh > 0 else None,
        "swaps_per_rider_hour": met["n_swaps"] / rh if rh > 0 else None,
        "orders_given_up": met["n_unserved"],
    }


def result_cols(inst: Instance, rec: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if rec.get("cost") is not None:
        out.update(C.flatten_cost(rec["cost"]))
    if rec.get("metrics"):
        out.update(E2U._metric_cols(rec["metrics"]))
        out.update(C.flatten_r5(rec["metrics"]))
        out.update(ebaas_cols(inst, rec["metrics"]))
    return out


def policy_row(case: str, inst: Instance, lib_len: int, infra: str, method: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    row = base_row(case, inst, lib_len, infra, method, "relaxed")
    row.update(result_cols(inst, rec))
    fl = rec["flags"]
    row.update({
        "status": "POLICY", "solve_mode": "policy", "variant": POLICIES[method], "runtime_s": rec["runtime"],
        "check_ok": rec["ok"], "ok_modulo_report_only": rec["ok_modulo_report_only"],
        "families": json.dumps(rec["families"]), "identity_24_ok": rec["identity_24_ok"],
        "policy_reserve_source": rec.get("policy_reserve_source"),
        "swap_rule": rec["params"].get("swap_rule"), "transfer_rule": rec["params"].get("transfer_rule"),
        "charge_rule": rec["params"].get("charge_rule"),
        "pruned_fallbacks": rec["pruning_flags"]["pruned_fallbacks"], "stranded": rec["pruning_flags"]["stranded"],
        "reach_refusals": (fl.get("reach_refusals") or {}).get("count", 0),
        "outages": json.dumps(fl.get("outages"), default=str) if fl.get("outages") is not None else None,
    })
    return row


def ilp_row(case: str, inst: Instance, lib_len: int, infra: str, method: str, targets: str,
            rec: Dict[str, Any], start_label: str) -> Dict[str, Any]:
    row = base_row(case, inst, lib_len, infra, method, targets)
    row.update(result_cols(inst, rec))
    st = rec["stats"]
    row.update({
        "status": rec["status"], "solve_mode": "solved", "obj": rec["obj"], "bound": rec["bound"],
        "mip_gap": rec["gap"], "runtime_s": rec["runtime"], "build_time_s": rec["build_time"],
        "n_binaries": rec["n_binaries"], "n_vars": rec["n_vars"], "n_rows": rec["n_rows"],
        "n_agg_arcs": st.get("n_agg_arcs"), "aggregate": st.get("aggregate"),
        "node_count": st.get("node_count"), "sol_count": st.get("sol_count"),
        "check_ok": rec["ok"], "families": json.dumps(rec["families"]), "identity_24_ok": rec["identity_24_ok"],
        "mip_start_accepted": rec["mip_start_accepted"], "mip_start_variant": start_label,
        "mip_start_obj": (rec["mip_start_info"] or {}).get("start_obj"),
        "time_limit_s": st["switches"].get("time_limit"), "threads": st["switches"].get("threads"),
    })
    return row


def skipped_row(case: str, inst: Instance, lib_len: int, infra: str, method: str, targets: str,
                reason: str) -> Dict[str, Any]:
    row = base_row(case, inst, lib_len, infra, method, targets)
    row.update({"status": C.SKIPPED_BUDGET, "solve_mode": "skipped", "skip_reason": reason})
    return row


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------
def build_plan(done: Dict[Key, Dict[str, Any]], cases: Sequence[str], seeds: Optional[Dict[str, List[int]]] = None,
               retry_unsolved: bool = False) -> List[WorkItem]:
    """Phase a: per (case, seed): network then home policies + ilp_relaxed (+ home ilp_written,
    implied); phase b: network ilp_written per (case, seed)."""
    plan: List[WorkItem] = []
    seeds = seeds or {c: CASES[c]["seeds"] for c in cases}
    for case in cases:
        for seed in seeds[case]:
            for infra in INFRAS:
                for m in tuple(POLICIES) + ("ilp_relaxed",) + (("ilp_written",) if infra == "home" else ()):
                    if not row_done(done.get((case, seed, infra, m)), retry_unsolved):
                        plan.append(("a", case, seed, infra, m))
    for case in cases:
        for seed in seeds[case]:
            if not row_done(done.get((case, seed, "network", "ilp_written")), retry_unsolved):
                plan.append(("b", case, seed, "network", "ilp_written"))
    return plan


def group_plan(plan: Sequence[WorkItem]) -> List[Tuple[str, str, int, str, List[str]]]:
    groups: List[Tuple[str, str, int, str, List[str]]] = []
    for phase, case, seed, infra, m in plan:
        if groups and groups[-1][:4] == (phase, case, seed, infra):
            groups[-1][4].append(m)
        else:
            groups.append((phase, case, seed, infra, [m]))
    return groups


#: seconds per ILP solve for the wall estimate (probe 2026-10-17, seed 0, Threads 3, aggregated:
#: relaxed solves usd4h_ebaas network 35 s / home 8.5 s, r5_stress4h network 46 s / home 6 s; the written
#: network solve of r5_stress4h took 75 s in the R5 probe)
EST_SOLVE_S = {("usd4h_ebaas", "network"): 45.0, ("usd4h_ebaas", "home"): 12.0,
               ("r5_stress4h", "network"): 70.0, ("r5_stress4h", "home"): 10.0}
#: per (case, seed, infra) group overhead: instance + library (2-4 s) + model build + start verification
EST_GROUP_OVERHEAD_S = 25.0


def plan_summary(plan: Sequence[WorkItem]) -> Dict[str, Any]:
    per_method: Dict[str, int] = {}
    solves = 0
    est = 0.0
    worst = 0.0
    for phase, case, seed, infra, m in plan:
        per_method[m] = per_method.get(m, 0) + 1
        if m in ILP_METHODS and not (infra == "home" and m == "ilp_written"):
            solves += 1
            est += EST_SOLVE_S[(case, infra)]
            worst += TIME_LIMIT
    groups = group_plan(plan)
    est += EST_GROUP_OVERHEAD_S * len(groups)
    worst += EST_GROUP_OVERHEAD_S * len(groups)
    return {"work_items": len(plan), "ilp_solves": solves, "per_method": per_method, "groups": len(groups),
            "instances": len({(c, s) for _p, c, s, _i, _m in plan}),
            "expected_wall_min": round(est / 60.0, 1), "worst_wall_min_at_time_limit": round(worst / 60.0, 1)}


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, out_dir: str, time_limit: float, threads: int, budget: C.WallBudget,
                 smoke: bool = False) -> None:
        self.out_dir = C.ensure_dir(out_dir)
        self.path = os.path.join(out_dir, RECORDS)
        self.inst_dir = C.ensure_dir(os.path.join(out_dir, "instances"))
        self.sched_dir = C.ensure_dir(os.path.join(out_dir, "schedules"))
        self.time_limit = float(time_limit)
        self.threads = int(threads)
        self.budget = budget
        self.smoke = smoke
        self.done = last_per_key(C.load_jsonl(self.path))
        self.n_runs = 0
        self._pairs: Dict[Tuple[str, int], Dict[str, Instance]] = {}

    # -- output -----------------------------------------------------------
    def emit(self, row: Dict[str, Any], phase: str) -> None:
        row["phase"] = phase
        row.setdefault("threads", self.threads)
        row.setdefault("time_limit_s", self.time_limit)
        C.append_jsonl(self.path, row)
        self.done[key_of(row)] = row
        self.refresh_csv()
        self.n_runs += 1
        keys = ("name", "infra", "method", "targets", "phase", "status", "solve_mode", "total", "total_end_adjusted",
                "served_share", "n_unserved", "n_swaps", "empty_km_per_rider_hour", "orders_per_rider_hour",
                "mip_gap", "runtime_s", "mip_start_variant", "mip_start_accepted")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys}), flush=True)

    def refresh_csv(self) -> None:
        rows = sorted(self.done.values(), key=lambda r: (r["case"], r["seed"], r["infra"], r["method"]))
        C.records_to_frame(rows).to_csv(os.path.join(self.out_dir, "results.csv"), index=False)

    def sched_path(self, inst: Instance, method: str) -> str:
        return os.path.join(self.sched_dir, f"{inst.meta['name']}__{method}.json")

    def save_sched(self, inst: Instance, method: str, sched: Optional[Schedule]) -> None:
        if sched is None:
            return
        with open(self.sched_path(inst, method), "w", encoding="utf-8") as fh:
            json.dump(sched.to_dict(), fh)

    def load_sched(self, inst: Instance, method: str) -> Optional[Schedule]:
        p = self.sched_path(inst, method)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as fh:
            return Schedule.from_dict(json.load(fh))

    def pair(self, case: str, seed: int) -> Dict[str, Instance]:
        k = (case, seed)
        if k not in self._pairs:
            self._pairs = {k: make_pair(case, seed, self.smoke)}       # keep one pair in memory
            for infra, inst in self._pairs[k].items():
                p = os.path.join(self.inst_dir, inst.meta["name"] + ".json")
                if not os.path.exists(p):
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(inst.to_json())
        return self._pairs[k]

    # -- helpers ----------------------------------------------------------
    def _policies(self, inst: Instance, lib) -> Dict[str, Dict[str, Any]]:
        """All rule policies on ``(inst, lib)``; ``r5_transfer`` only with services."""
        out: Dict[str, Dict[str, Any]] = {}
        for m, variant in POLICIES.items():
            if m == "r5_transfer" and not inst.services:
                continue
            out[m] = C.run_baseline_case(inst, lib, C.baseline_variant_params(variant, inst), m)
        return out

    @staticmethod
    def _best_clean(inst: Instance, lib, cands: Sequence[Tuple[str, Optional[Schedule]]]
                    ) -> Tuple[Optional[Schedule], str]:
        """Cheapest candidate schedule that passes ``evaluate.check`` with zero violations."""
        best: Tuple[Optional[Schedule], str, float] = (None, "none", float("inf"))
        for label, sched in cands:
            if sched is None:
                continue
            try:
                rep = check(inst, lib, sched)
            except Exception:  # noqa: BLE001 - a schedule that does not fit this library is not a start
                continue
            if not rep["ok"]:
                continue
            tot = cost(inst, lib, sched)["total"]
            if tot < best[2] - 1e-9:
                best = (sched, label, tot)
        return best[0], best[1]

    def _solve(self, inst: Instance, lib, start: Optional[Schedule], label: str) -> Optional[Dict[str, Any]]:
        tl = self.budget.solve_limit(self.time_limit)
        if tl is None:
            return None
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads, label=label,
                             params=ILP_PARAMS, **ILP_KWARGS)
        rec["_tl"] = tl
        return rec

    # -- phase a: policies + relaxed ILP (+ implied home written) ---------------------------
    def run_relaxed_group(self, case: str, seed: int, infra: str, methods: Sequence[str]) -> None:
        t0 = time.perf_counter()
        inst = self.pair(case, seed)[infra]
        rinst = C.relax_end_targets(inst)
        rinst.meta["name"] = inst.meta["name"]
        rlib, t_lib = C.build_library(rinst, pruning_of(case, inst))
        pols = self._policies(rinst, rlib)
        for m in POLICIES:
            if m not in methods:
                continue
            if m in pols:
                row = policy_row(case, rinst, len(rlib), infra, m, pols[m])
            else:
                row = base_row(case, rinst, len(rlib), infra, m, "relaxed")
                row.update({"status": "NOT_APPLICABLE", "solve_mode": "not_applicable",
                            "skip_reason": "no transport services: COST_AWARE transfers never act"})
            row["lib_build_time_s"] = t_lib
            self.emit(row, "a")
        sched: Optional[Schedule] = None
        relaxed_row = self.done.get((case, seed, infra, "ilp_relaxed"))
        if "ilp_relaxed" in methods:
            cands = [(m, r["schedule"]) for m, r in sorted(pols.items(), key=lambda kv: kv[1]["cost"]["total"])]
            start, slabel = self._best_clean(rinst, rlib, cands)
            if start is None:
                start, slabel = pols["r2"]["schedule"], "r2(unverified)"
            rec = self._solve(rinst, rlib, start, "ilp_relaxed")
            if rec is None:
                row = skipped_row(case, rinst, len(rlib), infra, "ilp_relaxed", "relaxed", "wall budget exhausted")
            else:
                row = ilp_row(case, rinst, len(rlib), infra, "ilp_relaxed", "relaxed", rec, slabel)
                row["time_limit_s"] = rec["_tl"]
                sched = rec["schedule"]
                self.save_sched(rinst, "ilp_relaxed", sched)
            row["lib_build_time_s"] = t_lib
            self.emit(row, "a")
            relaxed_row = row
        if infra == "home" and "ilp_written" in methods:
            self.emit(self._implied_home_written(case, inst, rinst, rlib, relaxed_row, sched), "a")
        del rlib
        gc.collect()
        print(f"# {inst.meta['name']} {infra} {list(methods)} done in {time.perf_counter() - t0:.0f} s "
              f"(budget left {self.budget.remaining() / 60:.0f} min)", flush=True)

    def _implied_home_written(self, case: str, inst: Instance, rinst: Instance, rlib,
                              relaxed_row: Optional[Dict[str, Any]], sched: Optional[Schedule]) -> Dict[str, Any]:
        """Home ``ilp_written``: (17) void (R_end_j = 0 at homes), (18) slack by construction, so the
        written optimum equals the relaxed one; verified on the relaxed incumbent."""
        if relaxed_row is None or relaxed_row.get("status") in (C.SKIPPED_BUDGET, None) or \
                relaxed_row.get("total") is None:
            row = skipped_row(case, inst, len(rlib), "home", "ilp_written", "written",
                              "relaxed home ILP not available")
            return row
        if sched is None:
            sched = self.load_sched(rinst, "ilp_relaxed")
        if any(int(f.R_end) != 0 for f in inst.facilities):
            raise AssertionError("home instance has R_end_j > 0; the implied written row is not valid")
        verified = None
        end_full = None
        if sched is not None:
            met = metrics(rinst, rlib, sched)
            end_full = met["end_full_total"]
            need = inst.rho * sum(int(f.B or 0) for f in inst.facilities)
            verified = bool(end_full >= need - 1e-9)
            if not verified:
                raise AssertionError(f"home relaxed optimum violates the written (18): {end_full} < {need}")
        row = {k: v for k, v in relaxed_row.items() if k not in ("wall_clock", "phase")}
        row.update(base_row(case, inst, len(rlib), "home", "ilp_written", "written"))
        row.update({"solve_mode": "implied_by_construction", "runtime_s": 0.0, "implied_from": "ilp_relaxed",
                    "implied_verified_18": verified, "implied_end_full_total": end_full,
                    "implied_rho_B": inst.rho * sum(int(f.B or 0) for f in inst.facilities)})
        return row

    # -- phase b: written network ILP --------------------------------------
    def run_written_group(self, case: str, seed: int, infra: str, methods: Sequence[str]) -> None:
        assert infra == "network" and list(methods) == ["ilp_written"], (infra, methods)
        t0 = time.perf_counter()
        inst = self.pair(case, seed)[infra]
        lib, t_lib = C.build_library(inst, pruning_of(case, inst))
        tl = self.budget.solve_limit(self.time_limit)
        if tl is None:
            row = skipped_row(case, inst, len(lib), infra, "ilp_written", "written", "wall budget exhausted")
        else:
            pols = self._policies(inst, lib)
            fam_written = {m: r["families"] for m, r in pols.items()}
            cands: List[Tuple[str, Optional[Schedule]]] = [("ilp_relaxed", self.load_sched(inst, "ilp_relaxed"))]
            cands += [(m, r["schedule"]) for m, r in pols.items()]
            for name in C.MIP_START_FALLBACKS:
                try:
                    fb = C.run_baseline_case(inst, lib, C.baseline_variant_params(name, inst), name)
                    cands.append((name, fb["schedule"]))
                except (ValueError, KeyError, TypeError) as exc:
                    fam_written[name] = {"error": f"{type(exc).__name__}: {exc}"}
            start, slabel = self._best_clean(inst, lib, cands)
            if start is None:
                start, slabel = pols["r2"]["schedule"], "r2(unverified)"
            rec = self._solve(inst, lib, start, "ilp_written")
            if rec is None:
                row = skipped_row(case, inst, len(lib), infra, "ilp_written", "written", "wall budget exhausted")
            else:
                row = ilp_row(case, inst, len(lib), infra, "ilp_written", "written", rec, slabel)
                row["time_limit_s"] = rec["_tl"]
                self.save_sched(inst, "ilp_written", rec["schedule"])
            row["policy_written_families"] = json.dumps(fam_written, default=str)
        row["lib_build_time_s"] = t_lib
        self.emit(row, "b")
        del lib
        gc.collect()
        print(f"# {inst.meta['name']} written done in {time.perf_counter() - t0:.0f} s "
              f"(budget left {self.budget.remaining() / 60:.0f} min)", flush=True)

    def run_group(self, phase: str, case: str, seed: int, infra: str, methods: Sequence[str]) -> None:
        if phase == "a":
            self.run_relaxed_group(case, seed, infra, methods)
        else:
            self.run_written_group(case, seed, infra, methods)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def cell_values(rows: Dict[Key, Dict[str, Any]], case: str, seed: int, infra: str, targets: str,
                metric: str) -> Dict[str, Tuple[Optional[float], str]]:
    """``{policy or 'ilp': (value, label)}`` for one infrastructure; ``best_rule`` = min over
    :data:`BEST_RULE_OVER` rows that exist (POLICY status)."""
    out: Dict[str, Tuple[Optional[float], str]] = {}
    for m in POLICIES:
        r = rows.get((case, seed, infra, m))
        if r is not None and r.get("status") == "POLICY":
            out[m] = (_num(r.get(metric)), m)
    cand = [(v, m) for m, (v, _l) in out.items() if m in BEST_RULE_OVER and v is not None]
    out["best_rule"] = (min(cand)[0], min(cand)[1]) if cand else (None, "-")
    ilp_m = "ilp_relaxed" if targets == "relaxed" else "ilp_written"
    r = rows.get((case, seed, infra, ilp_m))
    ok = r is not None and r.get("status") not in (C.SKIPPED_BUDGET, None) and r.get(metric) is not None
    out["ilp"] = (_num(r.get(metric)) if ok else None, ilp_m)
    out["ilp_status"] = ((r or {}).get("status"), str((r or {}).get("mip_gap")))
    return out


def _sub(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else a - b


def _pct(num: Optional[float], den: Optional[float]) -> Optional[float]:
    return None if num is None or den is None or abs(den) < 1e-12 else 100.0 * num / abs(den)


def decomposition(rows: Dict[Key, Dict[str, Any]]) -> pd.DataFrame:
    """One row per (case, seed, targets, metric, policy): the 2x2 cells and their decomposition."""
    out: List[Dict[str, Any]] = []
    for case, seed in sorted({(k[0], k[1]) for k in rows}):
        md5s = {r.get("demand_md5") for k, r in rows.items() if k[:2] == (case, seed) and r.get("demand_md5")}
        for targets in ("relaxed", "written"):
            for metric in METRICS_X:
                H = cell_values(rows, case, seed, "home", targets, metric)
                N = cell_values(rows, case, seed, "network", targets, metric)
                nsetup = _num((rows.get((case, seed, "network", "ilp_relaxed")) or {}).get("C_setup"))
                for pol in REPORT_POLICIES:
                    hp, hl = H.get(pol, (None, "-"))
                    np_, nl = N.get(pol, (None, "-"))
                    hi, ni = H["ilp"][0], N["ilp"][0]
                    von_p, von_i = _sub(hp, np_), _sub(hi, ni)
                    voc_n, voc_h = _sub(np_, ni), _sub(hp, hi)
                    tot = _sub(hp, ni)
                    out.append({
                        "case": case, "seed": seed, "targets": targets, "metric": metric, "policy": pol,
                        "demand_md5_unique": len(md5s) == 1, "home_policy_variant": hl, "network_policy_variant": nl,
                        "H_policy": hp, "H_ilp": hi, "N_policy": np_, "N_ilp": ni,
                        "home_ilp_status": H["ilp_status"][0], "network_ilp_status": N["ilp_status"][0],
                        "network_ilp_gap": _num(N["ilp_status"][1]),
                        "VoN_policy": von_p, "VoN_ilp": von_i, "VoC_network": voc_n, "VoC_home": voc_h,
                        "VoN_policy_pct": _pct(von_p, hp), "VoN_ilp_pct": _pct(von_i, hi),
                        "VoC_network_pct": _pct(voc_n, np_), "VoC_home_pct": _pct(voc_h, hp),
                        "total_effect": tot, "total_effect_pct": _pct(tot, hp),
                        "interaction": _sub(voc_n, voc_h),
                        "shapley_network": None if von_p is None or von_i is None else 0.5 * (von_p + von_i),
                        "shapley_coordination": None if voc_n is None or voc_h is None else 0.5 * (voc_n + voc_h),
                        "network_setup_cost": nsetup,
                        "VoN_ilp_gross_of_setup": None if von_i is None or nsetup is None else von_i + nsetup,
                    })
    return pd.DataFrame(out)


def summarise(dec: pd.DataFrame) -> pd.DataFrame:
    cols = ["H_policy", "H_ilp", "N_policy", "N_ilp", "VoN_policy", "VoN_ilp", "VoC_network", "VoC_home",
            "VoN_policy_pct", "VoN_ilp_pct", "VoC_network_pct", "VoC_home_pct", "total_effect", "total_effect_pct",
            "interaction", "shapley_network", "shapley_coordination", "VoN_ilp_gross_of_setup"]
    out: List[Dict[str, Any]] = []
    for (case, targets, metric, pol), g in dec.groupby(["case", "targets", "metric", "policy"], sort=False):
        row: Dict[str, Any] = {"case": case, "targets": targets, "metric": metric, "policy": pol}
        for c in cols:
            m, hw, n = E2U.ci95(g[c].tolist())
            row[f"{c}_mean"] = m
            row[f"{c}_ci95"] = hw
        row["n"] = int(g[["VoN_policy", "VoN_ilp", "VoC_network", "VoC_home"]].notna().all(axis=1).sum())
        out.append(row)
    return pd.DataFrame(out)


def ebaas_table(rows: Dict[Key, Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(list(rows.values()))
    df = df[df.status.isin(["POLICY", "OPTIMAL", "TIME_LIMIT", "SUBOPTIMAL", "INTERRUPTED"])
            | (df.get("solve_mode") == "implied_by_construction")]
    cols = ["total", "total_end_adjusted", "C_end_adjust", "served_share", "orders_given_up",
            "orders_per_rider_hour", "empty_km_per_rider_hour", "bike_km_per_rider_hour", "swaps_per_rider_hour",
            "r5_empty_km_share", "r5_outage_rate", "r5_n_energy_refused_orders", "r5_mean_station_time_min",
            "r5_mean_detour_km_per_swap", "mean_response_h", "mean_lateness_h"]
    cols = [c for c in cols if c in df.columns]
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    g = df.groupby(["case", "infra", "method"])[cols].mean(numeric_only=True).reset_index()
    g["n"] = df.groupby(["case", "infra", "method"]).size().values
    return g


def analyse(out_dir: str) -> str:
    recs = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not recs:
        raise SystemExit(f"no records in {out_dir}")
    rows = last_per_key(recs)
    df = C.records_to_frame(sorted(rows.values(), key=lambda r: (r["case"], r["seed"], r["infra"], r["method"])))
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    # byte-identical demand per (case, seed) across infrastructures and methods
    md5_bad = [f"{c}/{s}" for (c, s), g in df.groupby(["case", "seed"]) if g["demand_md5"].nunique() != 1]
    dec = decomposition(rows)
    dec.to_csv(os.path.join(out_dir, "decomposition.csv"), index=False)
    summ = summarise(dec)
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    eb = ebaas_table(rows)
    eb.to_csv(os.path.join(out_dir, "ebaas_metrics.csv"), index=False)
    fig = os.path.join(out_dir, "x4_decomposition.png")
    try:
        _plot(summ, fig)
    except Exception as exc:  # noqa: BLE001 - the tables are the deliverable
        fig = f"(figure failed: {exc})"
    ilp = df[df.method.isin(list(ILP_METHODS))].copy()
    for c in ("mip_gap", "runtime_s"):
        ilp[c] = pd.to_numeric(ilp.get(c), errors="coerce")
    solver = (ilp.groupby(["case", "infra", "method"])
              .agg(n=("status", "size"), optimal=("status", lambda s: int((s == "OPTIMAL").sum())),
                   time_limit=("status", lambda s: int((s == "TIME_LIMIT").sum())),
                   skipped=("status", lambda s: int((s == C.SKIPPED_BUDGET).sum())),
                   implied=("solve_mode", lambda s: int((s == "implied_by_construction").sum())),
                   gap_max=("mip_gap", "max"), runtime_mean=("runtime_s", "mean"), runtime_max=("runtime_s", "max"))
              .reset_index())
    md: List[str] = ["# X4 -- value of the swap network (A5, eBaaS home-charging counterfactual)", ""]
    md.append("Network instance vs `generator.home_charging_counterfactual` (one swap-only home per depot, "
              "recharge of the rider's own battery at 0.24 kW, stock never binding), identical demand "
              "(demand md5 per seed: " + ("all identical" if not md5_bad else f"MISMATCH in {md5_bad}") + "). "
              f"Gurobi Threads {C.THREADS}, Seed 0, TimeLimit {TIME_LIMIT:.0f} s, aggregated flow (O1). "
              "Headline = relaxed targets (rho 0, R_end 0); written targets = price of recovery. "
              "VoN = home - network (value of the network), VoC = policy - ILP (value of coordination); "
              "percentages: VoN in % of the home cost, VoC in % of the policy cost ((baseline - ILP) / baseline). "
              "best_rule = per instance min over r2, r5_range, r5_transfer (only with services), r5.")
    md.append("")
    for metric in METRICS_X:
        for targets in ("relaxed", "written"):
            sub = summ[(summ.metric == metric) & (summ.targets == targets)]
            if sub.empty:
                continue
            md.append(f"## {metric}, {targets} targets{' (headline)' if targets == 'relaxed' and metric == 'total' else ''}")
            md.append(C.markdown_table(sub, ["case", "policy", "n", "H_policy_mean", "H_ilp_mean", "N_policy_mean",
                                             "N_ilp_mean", "VoN_policy_mean", "VoN_ilp_mean", "VoC_network_mean",
                                             "VoC_home_mean", "VoC_network_pct_mean", "VoN_ilp_pct_mean",
                                             "interaction_mean", "shapley_network_mean",
                                             "shapley_coordination_mean", "total_effect_mean"], 2))
            md.append("")
    md.append("## 95 % t-CI half-widths (relaxed, total)")
    sub = summ[(summ.metric == "total") & (summ.targets == "relaxed")]
    md.append(C.markdown_table(sub, ["case", "policy", "n", "VoN_policy_ci95", "VoN_ilp_ci95", "VoC_network_ci95",
                                     "VoC_home_ci95", "VoC_network_pct_ci95", "interaction_ci95"], 2))
    md.append("")
    md.append("## eBaaS-comparable metrics (means over seeds)")
    md.append(C.markdown_table(eb, list(eb.columns), 3))
    md.append("")
    md.append("Empty km = reposition arcs (A3 `empty_km`); the approach leg of a delivery arc counts as delivery km. "
              "At home a 'swap' is a recharge trip (sigma = 25 slots). `total_end_adjusted` adds the M1 end-state "
              "adjustment, which also prices the depleted batteries left at the homes.")
    md.append("")
    md.append("## Solver statistics")
    md.append(C.markdown_table(solver, list(solver.columns), 3))
    md.append("")
    md.append(f"Figure: `{os.path.basename(fig)}`")
    path = os.path.join(out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    return path


def _plot(summ: pd.DataFrame, path: str) -> None:
    import matplotlib.pyplot as plt
    sub = summ[(summ.metric == "total") & (summ.targets == "relaxed")]
    cases = [c for c in CASE_ORDER if c in set(sub.case)]
    if not cases:
        return
    comps = [("VoN_policy", "VoN under policy"), ("VoN_ilp", "VoN under ILP"),
             ("VoC_home", "VoC at home"), ("VoC_network", "VoC on network"), ("interaction", "interaction")]
    colors = ["#2a6f97", "#61a5c2", "#c75146", "#e48f72", "#8a8a85"]
    fig, axes = plt.subplots(1, len(cases), figsize=(5.2 * len(cases), 3.8), squeeze=False)
    for ax, case in zip(axes[0], cases):
        s = sub[sub.case == case].set_index("policy")
        pols = [p for p in REPORT_POLICIES if p in s.index]
        width = 0.8 / len(comps)
        for ci, (c, lab) in enumerate(comps):
            xs = [i + (ci - (len(comps) - 1) / 2) * width for i in range(len(pols))]
            ys = [float(s.loc[p, f"{c}_mean"]) for p in pols]
            es = [float(s.loc[p, f"{c}_ci95"]) for p in pols]
            es = [0.0 if math.isnan(e) else e for e in es]
            ax.bar(xs, ys, width * 0.92, yerr=es, capsize=2, color=colors[ci], label=lab if case == cases[0] else None)
        ax.axhline(0, color="#9a9a96", linewidth=0.8)
        ax.set_xticks(range(len(pols)))
        ax.set_xticklabels([f"policy {p}" for p in pols])
        ax.set_title(f"{CASES[case]['label']}", fontsize=10)
        ax.set_ylabel("USD per window (relaxed targets)")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.legend(fontsize=7.5, frameon=False, loc="upper center", ncol=len(comps))
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=None, help=f"default {OUT_DIR} (or {OUT_DIR}_smoke with --smoke)")
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--wall-budget", type=float, default=WALL_BUDGET_S, help="seconds (default 7200)")
    ap.add_argument("--cases", nargs="+", default=list(CASE_ORDER), choices=list(CASES))
    ap.add_argument("--seeds", nargs="*", type=int, default=None, help="restrict every case to these seeds")
    ap.add_argument("--retry-unsolved", action="store_true", help="re-solve ILP rows not OPTIMAL / gap <= 1 %%")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, solve nothing, write nothing")
    ap.add_argument("--smoke", action="store_true",
                    help="seed 0 of every case on reduced instances (3 bikes, 2 h), Threads 1, TimeLimit 30 s")
    ap.add_argument("--analyse", action="store_true", help="tables / figure / RESULTS.md from records.jsonl")
    args = ap.parse_args(argv)
    if args.time_limit > 300 and not args.smoke:
        raise SystemExit("round-5 protocol: TimeLimit 300 s for X4")
    if args.threads > 3:
        raise SystemExit("protocol: Threads <= 3")
    out_dir = args.out_dir or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse:
        print(analyse(out_dir))
        return {"analysed": out_dir}

    seeds = {c: (list(args.seeds) if args.seeds is not None else CASES[c]["seeds"]) for c in args.cases}
    if args.smoke:
        seeds = {c: [seeds[c][0] if seeds[c] else 0] for c in args.cases}
        budget = C.WallBudget(3600.0, margin_s=0.0, min_solve_s=1.0)
        runner = Runner(out_dir, 30.0, 1, budget, smoke=True)
        plan = build_plan(runner.done, args.cases, seeds)
        for phase, case, seed, infra, methods in group_plan(plan):
            runner.run_group(phase, case, seed, infra, methods)
        print(f"# smoke done: {runner.n_runs} rows -> {runner.path}", flush=True)
        print(analyse(out_dir))
        return {"smoke": runner.path, "rows": runner.n_runs}

    existing = last_per_key(C.load_jsonl(os.path.join(out_dir, RECORDS))) if os.path.isdir(out_dir) else {}
    plan = build_plan(existing, args.cases, seeds, args.retry_unsolved)
    summary = plan_summary(plan)
    summary.update(out_dir=out_dir, time_limit=args.time_limit, threads=args.threads,
                   wall_budget_min=args.wall_budget / 60.0, existing_rows=len(existing),
                   cases={c: seeds[c] for c in args.cases})
    if args.dry_run:
        print("# plan (phase, case, seed, infra, method):")
        for item in plan:
            print("  ", item)
        print(json.dumps(summary, indent=1))
        return summary
    budget = C.WallBudget(args.wall_budget)
    runner = Runner(out_dir, args.time_limit, args.threads, budget)
    print(f"# X4 plan {json.dumps(summary)}", flush=True)
    for phase, case, seed, infra, methods in group_plan(plan):
        runner.run_group(phase, case, seed, infra, methods)
    wall = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall, "plan": summary, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"# X4 runs finished: {runner.n_runs} rows in {wall / 60:.1f} min", flush=True)
    try:
        print(analyse(out_dir))
    except Exception as exc:  # noqa: BLE001 - the records are the deliverable; the report can be regenerated
        print(f"# analyse failed: {exc}", flush=True)
    return summary


if __name__ == "__main__":
    main()
