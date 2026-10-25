"""Round 6 -- the round-5 experiments re-run under the recalibrated order prices of
``notes/penalty_calibration.md`` (sections 1, 6, 7): P_i = 60 USD per undelivered order,
w = 18 USD/h from release r_i (unchanged), v = 15 USD/h from the promise b_i.

Why: real platforms pay flat late credits of 5-10 USD and lose about 38-60 USD on an
undelivered order, while the round-2..5 prices (``usd_sunk``: P 30, v 36 USD/h) make a served
order that is more than 13-18 min late cost more than dropping it.  This is a change of DATA
only: no equation of E2 (1)-(33) changes and (31) keeps its form.  Every instance is generated
EXACTLY as in round 5 (same families, seeds, eBaaS energy calibration, pruning, time limits,
MIP-start logic, aggregated ILP O1, Gurobi Threads 3 / Seed 0) and then repriced with
:func:`ebike_swap_sim.costs.reprice_orders`; the arc library is always built on the repriced
instance (``theta`` (31) is stored on the arcs) and verified with
:func:`ebike_swap_sim.costs.check_lib_prices` before any solve (``ilp.build_model`` repeats
the check, and ``ilp.solve`` asserts objective == ``evaluate.cost``).

Stages (``--stage``; outputs under ``outputs/r6_penalty/<stage>/``, one append-only
``records.jsonl`` per stage, resume by key, a wall budget per stage, ``--smoke``, ``--analyse``):

``headline``  ``usd4h`` (eBaaS) at demand x0.75 / x1 / x1.5 seeds 0-9 and ``nyc4h`` (busiest
              siting, eBaaS) seeds 0-9 under (P 60, v 15): rules r2, M2 (``r5_range``), M3
              (``r5_transfer``, only with services), M2+M3 (``r5``) on the written and the
              relaxed copy, best rule (per-instance minimum, end-adjusted) and the relaxed-target
              aggregated ILP; the written-target ILP on usd4h x1 (price of recovery).  Rows carry
              the columns of ``r5_x1_headline`` (``calib`` = the pricing label) plus lateness
              statistics (``n_late_over_60min``, mean / max lateness).
``psweep``    P in {20, 30, 40, 60, 80} at v 15 on usd4h x1 seeds 0-9 and ``r5_stress4h`` (6 bikes
              / 48 orders) seeds 0-9: rules + relaxed ILP; the usd4h P 60 cells are copied from the
              headline records when they exist (identical instance and protocol).
``vsweep``    v in {8, 15, 25, 36} at P 60 on usd4h x1 seeds 0-9 plus the legacy bridge (P 30,
              v 36); v 15 is copied from the headline records when present.
``network``   the 2 x 2 design of ``r5_x4_network`` (home charging vs network x best rule vs
              relaxed ILP) under (P 60, v 15) on usd4h x1 seeds 0-9 and r5_stress4h seeds 0-4
              (phase a of X4 only: the network written ILP is not part of the 2 x 2).
``rolling``   rolling horizon (W 24, k 6, lambda 10 min, aggregated windows, window TimeLimit
              60 s, relaxed final targets, as ``r5_x3_rolling``) under (P 60, v 15) on usd4h x1
              seeds 0-9 and r5_stress4h seeds 0-4; the offline reference and the rules come from
              the headline / psweep rows (joined in ``--analyse`` on the demand hash).
``levers``    ``r5_stress4h_k8`` (8 bikes / 64 orders) seeds 0-4 under (P 60, v 15): reference, no
              on-site charging (P_j = 0, ``site_power_cap_sweep``), lock-out of 2 spares (share 0.25
              at the dinner peak, ``add_battery_lockout``), as ``r5_x5_stress --levers``; rules +
              relaxed ILP, TimeLimit 600 s (gaps reported).
``fleet``     the fleet x spare grid of ``r5_x5_stress --fleet`` (48 orders, 0.6 kWh pack), K in
              {4, 6, 8, 10} x B in {1, 2, 3, 4} per site, seeds 0-2, under (P 60, v 15): rules +
              relaxed ILP (300 s, 600 s at K >= 8) and the system cost = end-adjusted total (with
              the spare set-up of (27)) + K x the allocated bike (+ rider) cost per window; the
              cost-minimal design within the grid per policy and its served share.
``rl``        ``r5_x7_rl`` retrained on the repriced instances (PPO-clip, 200,704 steps, training
              seeds 1000-1019, rider layers r2 and M2+M3, families nyc4h_stress2 and r5_stress4h);
              test seeds 0-9 with never-charge, charge-ASAP, the rule station layers, best rule and
              the relaxed ILP (TimeLimit 300 s; round 5: 120 s, see ``RL_ILP_TIME_LIMIT``).  Models
              under ``outputs/r6_penalty/rl/models/``.

Analysis (``--analyse``): per-stage CSV summaries with exact Student-t 95 % intervals over seeds
(``scipy.stats.t``), differences always paired over seeds (per-seed gaps / differences first,
then mean and CI): ``per_instance.csv``, ``summary.csv`` (long: group, metric, mean, ci95, n),
``paired_vs_ref.csv`` for the sweeps (pricing - reference pricing per seed), plus the stage
tables named below; ``RESULTS.md`` per stage.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r6_penalty.py --stage headline --dry-run
    python3 experiments/r6_penalty.py --stage headline --smoke        # outputs/r6_penalty_smoke/headline
    python3 experiments/r6_penalty.py --stage headline                # full run (resumable)
    python3 experiments/r6_penalty.py --stage all --analyse
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import Instance, Schedule, metrics  # noqa: E402
from ebike_swap_sim import costs as cm  # noqa: E402
from ebike_swap_sim import generator as gen  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r5_x1_headline as X1  # noqa: E402
from experiments import r5_x3_rolling as X3  # noqa: E402
from experiments import r5_x4_network as X4  # noqa: E402
from experiments import r5_x5_stress as X5  # noqa: E402

OUT_ROOT = os.path.join(C.OUTPUT_ROOT, "r6_penalty")
RECORDS = "records.jsonl"
STAGES: Tuple[str, ...] = ("headline", "psweep", "vsweep", "network", "rolling", "levers", "fleet", "rl")
GRID_STAGES: Tuple[str, ...] = ("headline", "psweep", "vsweep")
W_HOUR = 18.0
SEEDS10: Tuple[int, ...] = tuple(range(10))
SEEDS5: Tuple[int, ...] = tuple(range(5))
SEEDS3: Tuple[int, ...] = tuple(range(3))
TIME_LIMIT = 300.0
TL_LONG = 600.0
THREADS = C.THREADS
RULES: Tuple[str, ...] = X1.RULES                       # r2, r5_range, r5_transfer, r5
#: rule names of the round-6 tables (the plan's names): M2 = range-aware + reservation swap rule,
#: M3 = cost-aware transfers, M2+M3 = the combined r5 rule.
RULE_LABEL: Dict[str, str] = {"r2": "r2", "r5_range": "M2", "r5_transfer": "M3", "r5": "M2M3"}
#: Smoke sizes (reduced instances of the same builders; the full sizes are never smoked).
SMOKE_USD: Dict[str, Any] = {"n_bikes": 3, "window_h": 2.0}
SMOKE_R5: Dict[str, Any] = {"n_bikes": 3, "window_h": 2.0}
SMOKE_TL = 30.0
SMOKE_BUDGET_MIN = 30.0

#: Wall budget per stage (minutes): about 1.6 x the expected wall time (EST_MIN); a solve that does
#: not fit is recorded as SKIPPED_BUDGET and re-run on resume.
WALL_BUDGET_MIN: Dict[str, float] = {"headline": 150.0, "psweep": 360.0, "vsweep": 90.0, "network": 75.0,
                                     "rolling": 45.0, "levers": 270.0, "fleet": 380.0, "rl": 270.0}
#: Expected wall minutes per stage at Threads 3 (from the round-5 wall times and per-solve runtimes,
#: outputs/r5_*/records* and wall_time*, with +15 % for the repricing: more orders served):
#: headline = 10 seeds x (x0.75 relaxed 29 s + x1 written 71 s + relaxed 43 s + x1.5 127 s + nyc4h 22 s
#: + 4 x 20 s instance / library / rules);  psweep = 50 r5_stress4h cells x 180 s + 40 usd4h cells x 68 s;
#: vsweep = 40 x 68 s;  network = X4 phase a (round 5: 30 min);  rolling = usd4h 10 x 61 s + r5 5 x 86 s;
#: levers = 15 ILPs at <= 600 s (round 5: 3 of 18 cells OPTIMAL at 300 s) + rules;  fleet = 3 seeds x
#: (K4 4 x 160 s, K6 4 x 155 s, K8 4 x 170 s, K10 4 x 535 s) + 6 %;  rl = round-5 X7 (115 min) minus the
#: written ILP phase, plus about 15 min for the 300 s relaxed-ILP limit (r5_stress4h about 100 s per seed
#: at P 60 / v 15 instead of 50 s).
EST_MIN: Dict[str, float] = {"headline": 75.0, "psweep": 225.0, "vsweep": 50.0, "network": 35.0, "rolling": 20.0,
                             "levers": 165.0, "fleet": 250.0, "rl": 120.0}


# ---------------------------------------------------------------------------
# pricing
# ---------------------------------------------------------------------------
def pricing(P: float, v: float, w: float = W_HOUR) -> Dict[str, Any]:
    """``{'P', 'w', 'v', 'label'}`` of one uniform order pricing."""
    return {"P": float(P), "w": float(w), "v": float(v), "label": cm.pricing_label(P, w, v)}


BASE = pricing(cm.R6_PRICING["P"], cm.R6_PRICING["v"], cm.R6_PRICING["w"])          # P 60, w 18, v 15
BRIDGE = pricing(cm.LEGACY_PRICING["P"], cm.LEGACY_PRICING["v"], cm.LEGACY_PRICING["w"])  # P 30, v 36
P_SWEEP: Tuple[float, ...] = (20.0, 30.0, 40.0, 60.0, 80.0)
V_SWEEP: Tuple[float, ...] = (8.0, 15.0, 25.0, 36.0)


def priced(inst: Instance, pr: Dict[str, Any], stage: str) -> Instance:
    """Repriced copy of a round-5 instance (``costs.reprice_orders``); asserts the prices."""
    out = cm.reprice_orders(inst, P=pr["P"], w=pr["w"], v=pr["v"],
                            source=f"experiments/r6_penalty.py stage {stage}; {cm.R6_PRICING['source']}")
    got = cm.uniform_order_prices(out)
    if got is None or any(abs(got[k] - pr[k]) > 1e-12 for k in cm.PRICE_KEYS):
        raise AssertionError(f"repricing failed: {got} != {pr}")
    if C.demand_md5(out) != C.demand_md5(inst):
        raise AssertionError("repricing changed the demand side")
    return out


def price_cols(pr: Dict[str, Any], stage: str) -> Dict[str, Any]:
    return {"stage": stage, "pricing": pr["label"], "P": pr["P"], "w": pr["w"], "v": pr["v"]}


def lateness_cols(inst: Instance, lib: Any, sched: Optional[Schedule]) -> Dict[str, Any]:
    """Lateness of the served orders in minutes (``[u_a - b_i]_+ Delta``, (31)): counts late, more
    than 30 and more than 60 min late, mean over served / over late orders, max, p90."""
    if sched is None:
        return {}
    dm = inst.disc.Delta_h * 60.0
    late: List[float] = []
    for a in sched.chosen_arcs(lib):
        if a.kind == "deliver":
            o = inst.order(a.order)
            late.append(max(a.u - o.b, 0) * dm)
    pos = [x for x in late if x > 1e-9]
    return {"n_served_arcs": len(late), "n_late_min": len(pos),
            "n_late_over_30min": sum(1 for x in late if x > 30.0 + 1e-9),
            "n_late_over_60min": sum(1 for x in late if x > 60.0 + 1e-9),
            "mean_lateness_min": (sum(late) / len(late)) if late else 0.0,
            "mean_lateness_min_late": (sum(pos) / len(pos)) if pos else 0.0,
            "max_lateness_min": max(late) if late else 0.0,
            "p90_lateness_min": float(np.percentile(late, 90)) if late else 0.0}


def obj_check_cols(rec: Dict[str, Any]) -> Dict[str, Any]:
    """ILP objective vs ``evaluate.cost`` total (ilp.solve already raises on a mismatch)."""
    obj = rec.get("obj")
    tot = (rec.get("cost") or {}).get("total")
    if obj is None or tot is None:
        return {"obj_eq_eval": None}
    d = float(obj) - float(tot)
    return {"obj_minus_eval": d, "obj_eq_eval": bool(abs(d) <= 1e-6 * max(1.0, abs(float(obj))))}


def budget_cut(row: Optional[Dict[str, Any]], requested: Optional[float] = None,
               used_key: str = "time_limit_s", req_key: str = "time_limit_requested_s") -> bool:
    """True for an ILP row that did not reach OPTIMAL while the wall budget had cut its time limit
    below the requested one (``row[used_key] < max(row[req_key], requested) - 1e-6``, or the
    ``budget_shortened`` flag).  Such a row is not done: resume re-solves it at the full limit and
    it is never copied into another stage (as ``r5_x5_stress._is_done``)."""
    if row is None or row.get("status") in ("OPTIMAL", "POLICY", "NOT_APPLICABLE", None):
        return False
    if row.get("budget_shortened"):
        return True
    used = _num(row.get(used_key))
    req = max([x for x in (_num(row.get(req_key)), _num(requested)) if x is not None], default=None)
    return used is not None and req is not None and used < req - 1e-6


def mean_ci(values: Iterable[Any]) -> Tuple[float, float, int]:
    """Mean, exact Student-t 95 % half-width (``scipy.stats.t.ppf(0.975, n - 1)``) and n."""
    v = [float(x) for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n == 0:
        return float("nan"), float("nan"), 0
    m = sum(v) / n
    if n == 1:
        return m, float("nan"), 1
    from scipy.stats import t as _t
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    return m, float(_t.ppf(0.975, n - 1)) * sd / math.sqrt(n), n


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def gap_pct(b: Any, i: Any) -> Optional[float]:
    b, i = _num(b), _num(i)
    if b is None or i is None or abs(b) < 1e-12:
        return None
    return 100.0 * (b - i) / abs(b)


def long_summary(df: pd.DataFrame, by: Sequence[str], cols: Sequence[str]) -> pd.DataFrame:
    """Long table ``by..., metric, mean, ci95, n`` (exact t over the rows of each group)."""
    out: List[Dict[str, Any]] = []
    if df.empty:
        return pd.DataFrame()
    for keys, g in df.groupby(list(by), dropna=False, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for c in cols:
            if c not in g.columns:
                continue
            m, h, n = mean_ci(pd.to_numeric(g[c], errors="coerce").tolist())
            if n == 0:
                continue
            out.append({**dict(zip(by, keys)), "metric": c, "mean": m, "ci95": h, "n": n})
    return pd.DataFrame(out)


def stage_dir(stage: str, smoke: bool, root: Optional[str] = None) -> str:
    base = root or (OUT_ROOT + "_smoke" if smoke else OUT_ROOT)
    return os.path.join(base, stage)


def write_md(path: str, lines: Sequence[str]) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# instances (exactly the round-5 builders)
# ---------------------------------------------------------------------------
def build_case(case: str, seed: int, mult: float = 1.0, smoke: bool = False) -> Tuple[Instance, Dict[str, Any]]:
    """Round-5 instance and pruning of one case: ``usd4h`` = ``r5_x1_headline.make_inst(..., 'ebaas')``
    (= ``r5_x3`` / ``r5_x4`` usd4h_ebaas at x1, reachable pruning), ``nyc4h`` = the X1 eBaaS nyc4h
    (``PRUNING_NYC`` facility targets), ``r5_stress4h`` = ``common.make_instance`` (R5 reachable
    pruning, ``common.pruning_for``).  ``smoke`` reduces fleet and window (same builders)."""
    if case == "usd4h":
        if smoke:
            inst = C.make_instance("usd4h", seed=int(seed), orders_per_bike_hour=X1.BASE_OPH * float(mult),
                                   cost_variant=X1.COST_VARIANT, energy_calibration=X1.ENERGY, **SMOKE_USD)
            inst.meta["demand_mult"] = float(mult)
            inst.meta["seed"] = int(seed)
            inst.meta["name"] = f"usd4h-smoke-K{len(inst.bikes)}-I{len(inst.orders)}-seed{seed}-x{float(mult):g}"
        else:
            inst = X1.make_inst("usd4h", "ebaas", int(seed), float(mult))
        pr = X1.pruning(inst, "usd4h")
    elif case == "nyc4h":
        inst = X1.make_inst("nyc4h", "ebaas", int(seed), 1.0)
        pr = X1.pruning(inst, "nyc4h")
    elif case in ("r5_stress4h", "r5_stress4h_k8"):
        inst = C.make_instance(case, seed=int(seed), **(SMOKE_R5 if smoke else {}))
        inst.meta["name"] = f"{case}{'-smoke' if smoke else ''}-K{len(inst.bikes)}-I{len(inst.orders)}-seed{seed}"
        inst.meta["demand_mult"] = 1.0
        pr = C.pruning_for(inst)
    else:
        raise ValueError(f"unknown case {case!r}")
    inst.meta["r6_case"] = case
    return inst, pr


def time_limit_of(case: str, smoke: bool) -> float:
    if smoke:
        return SMOKE_TL
    return float(C.R5_TIME_LIMITS.get(case, TIME_LIMIT))


# ---------------------------------------------------------------------------
# grid stages: headline, psweep, vsweep
# ---------------------------------------------------------------------------
@dataclass
class Cell:
    case: str
    pr: Dict[str, Any]
    seed: int
    mult: float
    rule_targets: Tuple[str, ...]
    ilp_targets: Tuple[str, ...]
    tl: float
    reuse: Tuple[str, ...] = ()          # stages whose identical rows may be copied (headline)


def plan_grid(stage: str, smoke: bool, seeds: Optional[Sequence[int]] = None) -> List[Cell]:
    """Ordered cells of a grid stage (budget stops leave balanced seeds; reusable cells last)."""
    cells: List[Cell] = []
    if stage == "headline":
        sd = list(seeds) if seeds is not None else ([0] if smoke else list(SEEDS10))
        for s in sd:
            for case, mult in (([("usd4h", 1.0), ("nyc4h", 1.0)]) if smoke else
                               [("usd4h", 0.75), ("usd4h", 1.0), ("usd4h", 1.5), ("nyc4h", 1.0)]):
                ilp_t = ("written", "relaxed") if (case == "usd4h" and mult == 1.0) else ("relaxed",)
                cells.append(Cell(case, BASE, s, mult, ("written", "relaxed"), ilp_t, time_limit_of(case, smoke)))
    elif stage == "psweep":
        sd = list(seeds) if seeds is not None else ([0] if smoke else list(SEEDS10))
        prices = (20.0, 60.0) if smoke else P_SWEEP
        first = [p for p in prices if p == BASE["P"]]
        rest = [p for p in prices if p != BASE["P"]]
        for P in first:                                  # r5_stress4h at the base price first (reference)
            for s in sd:
                cells.append(Cell("r5_stress4h", pricing(P, BASE["v"]), s, 1.0, ("relaxed",), ("relaxed",),
                                  time_limit_of("r5_stress4h", smoke)))
        for P in rest:
            for s in sd:
                for case in ("usd4h", "r5_stress4h"):
                    cells.append(Cell(case, pricing(P, BASE["v"]), s, 1.0, ("relaxed",), ("relaxed",),
                                      time_limit_of(case, smoke)))
        for P in first:                                  # usd4h at the base price: copied from headline
            for s in sd:
                cells.append(Cell("usd4h", pricing(P, BASE["v"]), s, 1.0, ("relaxed",), ("relaxed",),
                                  time_limit_of("usd4h", smoke), reuse=("headline",)))
    elif stage == "vsweep":
        sd = list(seeds) if seeds is not None else ([0] if smoke else list(SEEDS10))
        vs = (8.0, 15.0) if smoke else V_SWEEP
        prs = [pricing(BASE["P"], v) for v in vs if v != BASE["v"]] + [BRIDGE]
        for pr in prs:
            for s in sd:
                cells.append(Cell("usd4h", pr, s, 1.0, ("relaxed",), ("relaxed",), time_limit_of("usd4h", smoke)))
        if BASE["v"] in vs:
            for s in sd:
                cells.append(Cell("usd4h", BASE, s, 1.0, ("relaxed",), ("relaxed",), time_limit_of("usd4h", smoke),
                                  reuse=("headline",)))
    else:
        raise ValueError(stage)
    return cells


def grid_key(case: str, label: str, seed: int, mult: float, targets: str, method: str) -> Tuple:
    return (str(case), str(label), int(seed), float(mult), str(targets), str(method))


class GridRunner:
    """Rules + ILP per cell on one in-memory instance (the X1 protocol), rows in the X1 layout
    (``family`` = case, ``calib`` = pricing label) plus pricing and lateness columns."""

    def __init__(self, stage: str, out_dir: str, threads: int, budget: C.WallBudget, smoke: bool,
                 root: Optional[str] = None) -> None:
        self.stage = stage
        self.out_dir = C.ensure_dir(out_dir)
        self.path = os.path.join(out_dir, RECORDS)
        self.sched_dir = C.ensure_dir(os.path.join(out_dir, "schedules"))
        self.threads = int(threads)
        self.budget = budget
        self.smoke = smoke
        self.root = root
        self.done: Dict[Tuple, Dict[str, Any]] = X1.last_per_key(C.load_jsonl(self.path))
        self.n_runs = 0

    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("source", "r6_penalty")
        row.setdefault("stage", self.stage)
        C.append_jsonl(self.path, row)
        self.done[X1.key_of(row)] = row
        self.n_runs += 1
        rows = sorted(self.done.values(), key=lambda r: (str(r["family"]), str(r["calib"]), int(r["seed"]),
                                                         float(r["mult"]), str(r["targets"]), str(r["method"])))
        C.records_to_frame(rows).to_csv(os.path.join(self.out_dir, "results.csv"), index=False)
        keys = ("name", "pricing", "targets", "method", "status", "total", "total_end_adjusted", "served_share",
                "n_late_over_60min", "mip_gap", "runtime_s", "mip_start_variant", "obj_eq_eval", "reused_from")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys}), flush=True)

    def is_done(self, key: Tuple, tl: Optional[float] = None) -> bool:
        """``r5_x1_headline.row_is_done``, except that an ILP row cut short by the wall budget
        (not OPTIMAL, limit below the requested one) is re-solved."""
        row = self.done.get(key)
        return X1.row_is_done(row) and not budget_cut(row, tl)

    def prior_incumbent(self, name: str, targets: str) -> Optional[Schedule]:
        """The incumbent saved by an earlier solve of the same cell and target
        (``schedules/<name>-ilp-<targets>.json``), offered as a MIP-start candidate when the
        cell is solved again (a budget-cut resume, or ``r6_fill --retry-unsolved``); ``None``
        when there is none.  Candidates are still checked and the cheapest clean one wins."""
        p = os.path.join(self.sched_dir, f"{name}-ilp-{targets}.json")
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as fh:
                return Schedule.from_dict(json.load(fh))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def cell_todo(self, cell: Cell) -> bool:
        lab = cell.pr["label"]
        for tg in cell.rule_targets:
            for r in X1.CORE_RULES:
                if not self.is_done(grid_key(cell.case, lab, cell.seed, cell.mult, tg, r)):
                    return True
        return any(not self.is_done(grid_key(cell.case, lab, cell.seed, cell.mult, tg, "ilp"), cell.tl)
                   for tg in cell.ilp_targets)

    def try_reuse(self, cell: Cell) -> bool:
        """Copy the rows of an identical cell (same case, pricing, seed, demand, protocol) from the
        records of another stage (``cell.reuse``) when every needed row is done there."""
        lab = cell.pr["label"]
        for src in cell.reuse:
            src_path = os.path.join(stage_dir(src, self.smoke, self.root), RECORDS)
            if not os.path.exists(src_path):
                continue
            try:
                srows = X1.last_per_key(C.load_jsonl(src_path))
            except json.JSONDecodeError:              # a line being written by a concurrent lane
                continue
            need = [grid_key(cell.case, lab, cell.seed, cell.mult, tg, r) for tg in cell.rule_targets
                    for r in X1.CORE_RULES]
            need += [grid_key(cell.case, lab, cell.seed, cell.mult, tg, "ilp") for tg in cell.ilp_targets]
            if not all(X1.row_is_done(srows.get(k)) and not budget_cut(srows.get(k), cell.tl) for k in need):
                continue
            extra = [k for k in srows if k[:4] == need[0][:4] and k[4] in cell.rule_targets and k[5] in RULES]
            for k in dict.fromkeys(need + extra):
                if not self.is_done(k):
                    row = dict(srows[k])
                    row.update(stage=self.stage, reused_from=src)
                    self.emit(row)
            return True
        return False

    def _skipped(self, inst: Instance, lib: Any, kw: Dict[str, Any]) -> Dict[str, Any]:
        row = X1.base_row(inst, lib, **kw)
        row.update(status=C.SKIPPED_BUDGET, total=None, skip_reason="wall budget exhausted")
        return row

    def run_cell(self, cell: Cell) -> None:
        t_all = time.perf_counter()
        pr, lab = cell.pr, cell.pr["label"]
        inst0, prun = build_case(cell.case, cell.seed, cell.mult, self.smoke)
        inst = priced(inst0, pr, self.stage)
        name = f"r6-{inst0.meta['name']}-{lab}"
        inst.meta["name"] = name
        relaxed = C.relax_end_targets(inst)
        relaxed.meta["name"] = name + "-relaxed"
        md5, omd5 = C.demand_md5(inst), X1.orders_md5(inst)
        if C.demand_md5(relaxed) != md5:
            raise RuntimeError(f"{name}: relaxed copy changed the demand side")
        lib, t_lib = C.build_library(inst, prun)
        chk = cm.check_lib_prices(inst, lib)
        lib_rel = X3.rebind_library(lib, relaxed)            # the library does not depend on rho / R_end
        copies = {"written": (inst, lib), "relaxed": (relaxed, lib_rel)}
        rules = X1.applicable_rules(inst)
        common_kw = dict(family=cell.case, calib=lab, seed=cell.seed, mult=cell.mult, md5=md5, omd5=omd5)
        extra0 = {**price_cols(pr, self.stage), "lib_build_time_s": t_lib, "lib_price_checked_arcs": chk["n_checked"],
                  "cost_variant_effective": inst.meta.get("cost_variant"), "r6_case": cell.case}
        recs: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for tg in cell.rule_targets:
            ii, ll = copies[tg]
            for rule in rules:
                rec = C.run_baseline_case(ii, ll, C.baseline_variant_params(X1.RULE_VARIANT[rule], ii), label=rule)
                recs[(tg, rule)] = rec
                key = grid_key(cell.case, lab, cell.seed, cell.mult, tg, rule)
                if not self.is_done(key):
                    row = X1.rule_row(ii, ll, rec, targets=tg, method=rule, **common_kw)
                    row.update(extra0, rule_label=RULE_LABEL[rule], **lateness_cols(ii, ll, rec["schedule"]))
                    self.emit(row)
        sched_w: Optional[Schedule] = None
        if "written" in cell.ilp_targets:
            key = grid_key(cell.case, lab, cell.seed, cell.mult, "written", "ilp")
            if not self.is_done(key, cell.tl):
                tl = self.budget.solve_limit(cell.tl)
                if tl is None:
                    self.emit({**self._skipped(inst, lib, {**common_kw, "targets": "written", "method": "ilp"}),
                               **extra0})
                else:
                    if ("written", "r2") not in recs:
                        for rule in rules:
                            recs[("written", rule)] = C.run_baseline_case(
                                inst, lib, C.baseline_variant_params(X1.RULE_VARIANT[rule], inst), label=rule)
                    cands_w = [("prior_incumbent", self.prior_incumbent(name, "written"))]
                    cands_w += [(r, recs[("written", r)]["schedule"]) for r in rules]
                    start, slab = X1.Runner._pick_start(inst, lib, cands_w, recs[("written", "r2")])
                    t0 = time.perf_counter()
                    rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads,
                                         label="ilp", params=C.ILP_PARAMS_R3, **C.R5_ILP_KWARGS)
                    row = X1.ilp_row(inst, lib, rec, slab, tl, self.threads, time.perf_counter() - t0,
                                     targets="written", method="ilp", **common_kw)
                    row.update(extra0, time_limit_requested_s=cell.tl, budget_shortened=bool(tl < cell.tl - 1e-6),
                               **obj_check_cols(rec), **lateness_cols(inst, lib, rec["schedule"]))
                    sched_w = rec["schedule"]
                    if sched_w is not None:
                        with open(os.path.join(self.sched_dir, f"{name}-ilp-written.json"), "w", encoding="utf-8") as fh:
                            json.dump(sched_w.to_dict(), fh)
                    self.emit(row)
            else:
                p = os.path.join(self.sched_dir, f"{name}-ilp-written.json")
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as fh:
                        sched_w = Schedule.from_dict(json.load(fh))
        if "relaxed" in cell.ilp_targets:
            key = grid_key(cell.case, lab, cell.seed, cell.mult, "relaxed", "ilp")
            if not self.is_done(key, cell.tl):
                tl = self.budget.solve_limit(cell.tl)
                if tl is None:
                    self.emit({**self._skipped(relaxed, lib_rel, {**common_kw, "targets": "relaxed", "method": "ilp"}),
                               **extra0})
                else:
                    cands = [("ilp_written", sched_w), ("prior_incumbent", self.prior_incumbent(name, "relaxed"))]
                    cands += [(f"{r}@{tg}", recs[(tg, r)]["schedule"]) for tg in cell.rule_targets for r in rules]
                    fb = recs.get(("relaxed", "r2")) or C.run_baseline_case(
                        relaxed, lib_rel, C.baseline_variant_params("baseline", relaxed), label="r2")
                    start, slab = X1.Runner._pick_start(relaxed, lib_rel, cands, fb)
                    t0 = time.perf_counter()
                    rec = C.run_ilp_case(relaxed, lib_rel, mip_start=start, time_limit=tl, threads=self.threads,
                                         label="ilp_relaxed", params=C.ILP_PARAMS_R3, **C.R5_ILP_KWARGS)
                    row = X1.ilp_row(relaxed, lib_rel, rec, slab, tl, self.threads, time.perf_counter() - t0,
                                     targets="relaxed", method="ilp", **common_kw)
                    row.update(extra0, time_limit_requested_s=cell.tl, budget_shortened=bool(tl < cell.tl - 1e-6),
                               **obj_check_cols(rec), **lateness_cols(relaxed, lib_rel, rec["schedule"]))
                    if rec["schedule"] is not None:
                        with open(os.path.join(self.sched_dir, f"{name}-ilp-relaxed.json"), "w", encoding="utf-8") as fh:
                            json.dump(rec["schedule"].to_dict(), fh)
                    self.emit(row)
        del lib, lib_rel
        gc.collect()
        print(f"# [{self.stage}] {name} done in {time.perf_counter() - t_all:.0f} s "
              f"(budget left {self.budget.remaining() / 60:.0f} min)", flush=True)

    def run(self, cells: Sequence[Cell]) -> None:
        for cell in cells:
            if not self.cell_todo(cell):
                continue
            if cell.reuse and self.try_reuse(cell) and not self.cell_todo(cell):
                continue
            if self.budget.remaining() < self.budget.margin + 30.0:
                # no instance / library / rules once the budget is gone: SKIPPED_BUDGET rows for the
                # missing ILP targets only (re-run on resume; the cell's rules are not emitted, so the
                # analysis keeps rules and ILP on the same seeds)
                print(f"# [{self.stage}] budget exhausted before {cell.case} {cell.pr['label']} s{cell.seed}", flush=True)
                for tg in cell.ilp_targets:
                    if not self.is_done(grid_key(cell.case, cell.pr["label"], cell.seed, cell.mult, tg, "ilp"), cell.tl):
                        self.emit({"family": cell.case, "calib": cell.pr["label"], "seed": cell.seed,
                                   "mult": cell.mult, "targets": tg, "method": "ilp", "status": C.SKIPPED_BUDGET,
                                   "total": None, "skip_reason": "wall budget exhausted before the cell",
                                   "time_limit_requested_s": cell.tl, **price_cols(cell.pr, self.stage)})
                continue
            try:
                self.run_cell(cell)
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001 - record and continue (unattended lanes)
                row = {"family": cell.case, "calib": cell.pr["label"], "seed": cell.seed, "mult": cell.mult,
                       "targets": "*", "method": "cell_error", "status": "ERROR",
                       "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-3000:],
                       **price_cols(cell.pr, self.stage)}
                self.emit(row)


# -- grid analysis ---------------------------------------------------------------------------
GRID_METRICS = ("total", "total_end_adjusted", "C_end_adjust", "served_share", "n_unserved", "n_late",
                "n_late_over_30min", "n_late_over_60min", "mean_lateness_min", "mean_lateness_min_late",
                "max_lateness_min", "unserved", "response", "lateness", "C_travel", "C_elec", "C_setup", "C_reb")


def grid_per_instance(rows: Dict[Tuple, Dict[str, Any]]) -> pd.DataFrame:
    """One row per (case, pricing, seed, mult): every rule (by its plan name), best rule
    (end-adjusted argmin over the rules on either target copy), the relaxed ILP (best known:
    min of the relaxed solve and the written optimum, by the ILP objective, as X1), the written
    ILP when solved, per-instance gaps and paired USD differences."""
    by_cell: Dict[Tuple, Dict[Tuple[str, str], Dict[str, Any]]] = {}
    for k, r in rows.items():
        if r.get("status") in (C.SKIPPED_BUDGET, "ERROR") or k[5] == "cell_error":
            continue
        by_cell.setdefault(k[:4], {})[(k[4], k[5])] = r
    out: List[Dict[str, Any]] = []
    for cell, rr in sorted(by_cell.items(), key=lambda kv: tuple(map(str, kv[0]))):
        case, lab, seed, mult = cell
        any_row = next(iter(rr.values()))
        rec: Dict[str, Any] = {"case": case, "pricing": lab, "seed": seed, "mult": mult,
                               "P": any_row.get("P"), "w": any_row.get("w"), "v": any_row.get("v")}
        md5s = {r.get("demand_md5") for r in rr.values() if r.get("demand_md5")}
        rec["demand_md5"] = next(iter(md5s), None)
        rec["demand_md5_unique"] = len(md5s) == 1
        rule_rows = [(f"{m}@{tg}", m, r) for (tg, m), r in rr.items() if m in RULES and r.get("status") == "POLICY"]
        for m in RULES:
            r = rr.get(("relaxed", m)) or rr.get(("written", m))
            if r is None:
                continue
            lab_m = RULE_LABEL[m]
            for c in GRID_METRICS:
                rec[f"{lab_m}_{c}"] = _num(r.get(c))
        best = None
        for _l, m, r in rule_rows:
            v = _num(r.get("total_end_adjusted"))
            if v is not None and (best is None or v < best[0] - 1e-9):
                best = (v, m, r)
        if best is not None:
            rec["best_rule"] = RULE_LABEL[best[1]]
            for c in GRID_METRICS:
                rec[f"best_{c}"] = _num(best[2].get(c))
        iw, ir = rr.get(("written", "ilp")), rr.get(("relaxed", "ilp"))
        chosen, src = ir, "relaxed"
        if ir is None or _num(ir.get("total")) is None or (
                iw is not None and _num(iw.get("total")) is not None and _num(iw.get("total")) < _num(ir.get("total")) - 1e-9):
            chosen, src = (iw, "written") if iw is not None and _num(iw.get("total")) is not None else (None, None)
        rec["ilp_from"] = src
        rec["ilp_status"] = ir.get("status") if ir else None
        rec["ilp_mip_gap"] = _num(ir.get("mip_gap")) if ir else None
        rec["ilp_obj_eq_eval"] = ir.get("obj_eq_eval") if ir else None
        rec["ilp_reused_from"] = ir.get("reused_from") if ir else None
        rec["ilp_mip_start_variant"] = ir.get("mip_start_variant") if ir else None
        rec["has_relaxed_ilp"] = bool(ir is not None and _num(ir.get("total")) is not None)
        if chosen is not None:
            for c in GRID_METRICS:
                rec[f"ilp_{c}"] = _num(chosen.get(c))
        if iw is not None:
            rec["ilpw_status"] = iw.get("status")
            rec["ilpw_mip_gap"] = _num(iw.get("mip_gap"))
            for c in ("total", "total_end_adjusted", "served_share", "n_late_over_60min"):
                rec[f"ilpw_{c}"] = _num(iw.get(c))
            if chosen is not None:
                rec["price_of_recovery"] = (None if rec.get("ilpw_total") is None else rec["ilpw_total"] - rec["ilp_total"])
                rec["price_of_recovery_end_adjusted"] = (None if rec.get("ilpw_total_end_adjusted") is None
                                                         else rec["ilpw_total_end_adjusted"] - rec["ilp_total_end_adjusted"])
        # gaps (headline: end-adjusted best rule vs relaxed ILP) and paired USD differences
        ilp_ea, ilp_t = rec.get("ilp_total_end_adjusted"), rec.get("ilp_total")
        rec["gap_best_ea_pct"] = gap_pct(rec.get("best_total_end_adjusted"), ilp_ea)
        rec["gap_best_raw_pct"] = gap_pct(rec.get("best_total"), ilp_t)
        for m in RULES:
            lm = RULE_LABEL[m]
            rec[f"gap_{lm}_ea_pct"] = gap_pct(rec.get(f"{lm}_total_end_adjusted"), ilp_ea)
        rec["diff_best_minus_ilp_ea"] = (None if rec.get("best_total_end_adjusted") is None or ilp_ea is None
                                         else rec["best_total_end_adjusted"] - ilp_ea)
        rec["diff_r2_minus_ilp_ea"] = (None if rec.get("r2_total_end_adjusted") is None or ilp_ea is None
                                       else rec["r2_total_end_adjusted"] - ilp_ea)
        out.append(rec)
    return pd.DataFrame(out)


def _summary_cols(per: pd.DataFrame) -> List[str]:
    skip = {"case", "pricing", "seed", "mult", "P", "w", "v", "demand_md5", "demand_md5_unique", "best_rule",
            "ilp_from", "ilp_status", "ilpw_status", "ilp_obj_eq_eval", "ilp_reused_from", "ilp_mip_start_variant",
            "has_relaxed_ilp"}
    return [c for c in per.columns if c not in skip]


#: per-instance columns that depend on the relaxed ILP solution (paired comparisons of these need
#: comparable solves, see :func:`paired_vs_ref`).
ILP_DEPENDENT_PREFIXES: Tuple[str, ...] = ("ilp_", "ilpw_", "gap_", "diff_", "price_of_recovery")


def _start_class(v: Any) -> str:
    """MIP-start family of an ILP row: ``ilp_written`` (warm start from the written ILP optimum,
    headline usd4h x1) or ``rule`` (the cheapest rule schedule)."""
    return "ilp_written" if str(v) == "ilp_written" else "rule"


def _comparable_ilp(a: pd.Series, b: pd.Series) -> bool:
    """Two relaxed ILP solves are comparable when both are OPTIMAL, or when both started from the
    same start family (a time-limited solve then depends only on the instance and the pricing)."""
    if a.get("ilp_status") == "OPTIMAL" and b.get("ilp_status") == "OPTIMAL":
        return True
    return _start_class(a.get("ilp_mip_start_variant")) == _start_class(b.get("ilp_mip_start_variant"))


def paired_vs_ref(per: pd.DataFrame, ref_label: str, cols: Sequence[str]) -> pd.DataFrame:
    """Per (case, mult, pricing != ref): per-seed difference ``metric(pricing) - metric(ref)``
    on the seeds present in both, then mean and exact-t 95 % CI (paired over seeds).  For the
    ILP-dependent metrics a seed is left out when the two relaxed solves are not comparable: one
    is not OPTIMAL and their MIP starts differ (the copied headline reference cells start from the
    written ILP optimum, every other pricing from the rules); ``n_excluded_start`` counts them and
    ``n_pairs_not_optimal`` counts the kept pairs with a non-OPTIMAL side."""
    out: List[Dict[str, Any]] = []
    if per.empty:
        return pd.DataFrame()
    for (case, mult), g in per.groupby(["case", "mult"]):
        ref = g[g.pricing == ref_label].set_index("seed")
        if ref.empty:
            continue
        for lab, h in g[g.pricing != ref_label].groupby("pricing"):
            h = h.set_index("seed")
            seeds = sorted(set(h.index) & set(ref.index))
            for c in cols:
                if c not in h.columns or c not in ref.columns:
                    continue
                ilp_dep = c.startswith(ILP_DEPENDENT_PREFIXES)
                diffs: List[float] = []
                n_excl = n_nopt = 0
                for s in seeds:
                    a, b = _num(h.at[s, c]), _num(ref.at[s, c])
                    if a is None or b is None:
                        continue
                    if ilp_dep:
                        if not _comparable_ilp(h.loc[s], ref.loc[s]):
                            n_excl += 1
                            continue
                        if h.loc[s].get("ilp_status") != "OPTIMAL" or ref.loc[s].get("ilp_status") != "OPTIMAL":
                            n_nopt += 1
                    diffs.append(a - b)
                m, hw, n = mean_ci(diffs)
                if n or n_excl:
                    out.append({"case": case, "mult": mult, "pricing": lab, "ref": ref_label, "metric": c,
                                "mean_diff": m, "ci95": hw, "n_pairs": n,
                                "n_excluded_start": n_excl if ilp_dep else None,
                                "n_pairs_not_optimal": n_nopt if ilp_dep else None,
                                "P": h["P"].iloc[0], "v": h["v"].iloc[0]})
    return pd.DataFrame(out)


KEY_COLS = ("best_total_end_adjusted", "ilp_total_end_adjusted", "gap_best_ea_pct", "gap_r2_ea_pct", "gap_M2_ea_pct",
            "gap_M2M3_ea_pct", "diff_best_minus_ilp_ea", "best_served_share", "ilp_served_share", "best_n_late",
            "ilp_n_late", "best_n_late_over_60min", "ilp_n_late_over_60min", "best_mean_lateness_min",
            "ilp_mean_lateness_min", "best_max_lateness_min", "ilp_max_lateness_min", "best_unserved", "ilp_unserved",
            "best_lateness", "ilp_lateness", "price_of_recovery", "price_of_recovery_end_adjusted", "ilp_mip_gap")


def analyse_grid(stage: str, out_dir: str) -> str:
    rows = X1.last_per_key(C.load_jsonl(os.path.join(out_dir, RECORDS)))
    if not rows:
        return f"{stage}: no records"
    per = grid_per_instance(rows)
    per.to_csv(os.path.join(out_dir, "per_instance.csv"), index=False)
    cols = _summary_cols(per)
    summ = long_summary(per, ["case", "mult", "pricing"], cols)
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    # key table: every metric (rules and ILP) on the same seeds, those with a relaxed ILP row
    per_k = per[per["has_relaxed_ilp"].astype(bool)] if "has_relaxed_ilp" in per.columns else per
    summ_k = long_summary(per_k, ["case", "mult", "pricing"], [c for c in KEY_COLS if c in per_k.columns])
    n_all = (per.groupby(["case", "mult", "pricing"]).size() if not per.empty else pd.Series(dtype=float))
    key = summ_k
    wide = (key.pivot_table(index=["case", "mult", "pricing"], columns="metric", values="mean", aggfunc="first")
            .reset_index() if not key.empty else pd.DataFrame())
    if not wide.empty:
        ci = key.pivot_table(index=["case", "mult", "pricing"], columns="metric", values="ci95", aggfunc="first")
        n = key[key.metric == "best_total_end_adjusted"].set_index(["case", "mult", "pricing"])["n"]
        wide = wide.set_index(["case", "mult", "pricing"])
        for c in ("gap_best_ea_pct", "diff_best_minus_ilp_ea"):
            if c in ci.columns:
                wide[f"{c}_ci95"] = ci[c]
        wide["n_seeds"] = n
        wide["n_seeds_with_rules"] = n_all
        wide = wide.reset_index()
    wide.to_csv(os.path.join(out_dir, "summary_key.csv"), index=False)
    paired = pd.DataFrame()
    if stage in ("psweep", "vsweep"):
        paired = paired_vs_ref(per, BASE["label"], [c for c in KEY_COLS if c in per.columns])
        paired.to_csv(os.path.join(out_dir, "paired_vs_ref.csv"), index=False)
    an: List[str] = []
    if not per.empty:
        bad = per[~per.demand_md5_unique]
        an += [f"demand md5 differs within {len(bad)} cell(s)"] if len(bad) else []
        nobj = per[per.ilp_obj_eq_eval.astype(str) == "False"] if "ilp_obj_eq_eval" in per else per.iloc[0:0]
        an += [f"ILP objective != evaluate.cost on {len(nobj)} cell(s)"] if len(nobj) else []
        nopt = per[(per.ilp_status.notna()) & (per.ilp_status != "OPTIMAL")]
        an += [f"relaxed ILP not OPTIMAL on {len(nopt)} cell(s) (max MIP gap "
               f"{C.fmt(pd.to_numeric(nopt.ilp_mip_gap, errors='coerce').max(), 4)})"] if len(nopt) else []
    errs = [r for r in rows.values() if r.get("status") in ("ERROR", C.SKIPPED_BUDGET)]
    an += [f"{len(errs)} ERROR / SKIPPED_BUDGET row(s) (re-run on resume)"] if errs else []
    L = [f"# R6 {stage} -- order prices recalibrated (base P 60, w 18, v 15 USD/h from b_i)", "",
         "Generated by `experiments/r6_penalty.py --analyse`. Round-5 instances (eBaaS energy, round-5 pruning, "
         "aggregated ILP, Threads 3, Seed 0) repriced with `costs.reprice_orders`; libraries rebuilt and checked "
         "(`costs.check_lib_prices`). Headline gap = 100 (best rule - relaxed ILP) / best rule on end-adjusted totals "
         "(best rule = per-instance min over r2, M2, M3 (services only), M2M3). Means with exact Student-t 95 % "
         "half-widths over seeds; every difference is paired per seed. The key table is computed on the seeds with "
         "a relaxed ILP row (`n_seeds`; `n_seeds_with_rules` = seeds with rule rows); summary.csv keeps every "
         "metric on all of its rows (n per metric).", ""]
    if stage == "vsweep":
        L += ["Not run: the grace variant of penalty_calibration.md section 7 item 3 (v 17 USD/h from b_i + 10 min). "
              "It needs a pricing-only grace parameter in the lateness term (31), whose form R6 keeps unchanged.", ""]
    if not wide.empty:
        show = [c for c in ["case", "mult", "pricing", "n_seeds", "n_seeds_with_rules", "gap_best_ea_pct", "gap_best_ea_pct_ci95",
                            "diff_best_minus_ilp_ea", "best_served_share", "ilp_served_share", "best_n_late_over_60min",
                            "ilp_n_late_over_60min", "best_mean_lateness_min", "ilp_mean_lateness_min",
                            "ilp_max_lateness_min", "price_of_recovery_end_adjusted", "ilp_mip_gap"] if c in wide.columns]
        L += ["## Key metrics (seed means)", "", C.markdown_table(wide, show, 2), ""]
    if not paired.empty:
        p2 = paired[paired.metric.isin(["gap_best_ea_pct", "ilp_served_share", "best_served_share",
                                        "ilp_n_late_over_60min", "best_total_end_adjusted", "ilp_total_end_adjusted"])]
        L += [f"## Paired differences vs {BASE['label']} (per seed, then mean +- t 95 %)", "",
              "ILP-dependent metrics leave out a seed whose two relaxed solves are not comparable (one not "
              "OPTIMAL and different MIP starts: the reference cells copied from headline start from the written "
              "ILP optimum); `n_excluded_start` counts them.", "",
              C.markdown_table(p2, ["case", "pricing", "metric", "mean_diff", "ci95", "n_pairs", "n_excluded_start",
                                    "n_pairs_not_optimal"], 3), ""]
    L += ["## Anomalies", ""] + ([f"* {a}" for a in an] or ["* none"])
    L += ["", "Files: records.jsonl, results.csv, per_instance.csv, summary.csv (long), summary_key.csv"
          + (", paired_vs_ref.csv" if stage in ("psweep", "vsweep") else "") + ", schedules/."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


def run_grid(stage: str, args: argparse.Namespace) -> None:
    out_dir = stage_dir(stage, args.smoke, args.out_root)
    cells = plan_grid(stage, args.smoke, args.seeds)
    budget = (C.WallBudget(args.budget_min * 60.0, margin_s=0.0, min_solve_s=1.0) if args.smoke
              else C.WallBudget(args.budget_min * 60.0))
    if args.dry_run:
        runner_done = X1.last_per_key(C.load_jsonl(os.path.join(out_dir, RECORDS)))
        print(json.dumps({"stage": stage, "out_dir": out_dir, "cells": len(cells),
                          "ilp_solves": sum(len(c.ilp_targets) for c in cells), "existing_rows": len(runner_done),
                          "expected_wall_min": EST_MIN[stage], "budget_min": args.budget_min}, indent=1))
        for c in cells:
            print("  ", c.case, c.pr["label"], c.seed, c.mult, c.ilp_targets, c.tl, c.reuse)
        return
    runner = GridRunner(stage, out_dir, args.threads, budget, args.smoke, args.out_root)
    print(f"# R6 {stage}: {len(cells)} cells -> {out_dir}", flush=True)
    runner.run(cells)
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"stage": stage, "wall_s": budget.elapsed(), "rows": runner.n_runs, "smoke": args.smoke,
                             "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(analyse_grid(stage, out_dir), flush=True)


# ---------------------------------------------------------------------------
# network (r5_x4_network, phase a, under the base pricing)
# ---------------------------------------------------------------------------
class NetworkRunner(X4.Runner):
    """X4 runner whose network / home pair is the repriced round-5 pair."""

    def __init__(self, *a: Any, pr: Dict[str, Any], **k: Any) -> None:
        super().__init__(*a, **k)
        self.pr = pr
        #: lateness columns of the schedules of the current group, by method (merged in emit)
        self._late: Dict[str, Dict[str, Any]] = {}

    def pair(self, case: str, seed: int) -> Dict[str, Instance]:
        k = (case, seed)
        if k not in self._pairs:
            net = priced(X4.make_network(case, seed, self.smoke), self.pr, "network")
            net.meta["name"] = f"r6-{net.meta['name']}-{self.pr['label']}"
            home = X4.make_home(net)
            if cm.uniform_order_prices(home) != {kk: self.pr[kk] for kk in cm.PRICE_KEYS}:
                raise AssertionError("home counterfactual lost the repricing")
            self._pairs = {k: {"network": net, "home": home}}
            for inst in self._pairs[k].values():
                p = os.path.join(self.inst_dir, inst.meta["name"] + ".json")
                if not os.path.exists(p):
                    inst.save(p)
        return self._pairs[k]

    def _policies(self, inst: Instance, lib: Any) -> Dict[str, Dict[str, Any]]:
        out = super()._policies(inst, lib)
        for m, rec in out.items():
            self._late[m] = lateness_cols(inst, lib, rec.get("schedule"))
        return out

    def _solve(self, inst: Instance, lib: Any, start: Optional[Schedule], label: str) -> Optional[Dict[str, Any]]:
        chk = cm.check_lib_prices(inst, lib)
        rec = super()._solve(inst, lib, start, label)
        if rec is not None:
            rec["_lib_price_checked_arcs"] = chk["n_checked"]
            self._late[label] = lateness_cols(inst, lib, rec.get("schedule"))
        return rec

    def run_group(self, phase: str, case: str, seed: int, infra: str, methods: Sequence[str]) -> None:
        self._late = {}
        try:
            super().run_group(phase, case, seed, infra, methods)
        finally:
            self._late = {}

    def emit(self, row: Dict[str, Any], phase: str) -> None:
        row.update(price_cols(self.pr, "network"))
        m = row.get("method")
        if row.get("status") not in (C.SKIPPED_BUDGET, "ERROR", "NOT_APPLICABLE", None) \
                and row.get("solve_mode") != "implied_by_construction" and m in self._late:
            row.update(self._late[m])           # the implied home written row copies the relaxed row's columns
        if str(m).startswith("ilp_") and row.get("solve_mode") != "implied_by_construction":
            req = self.time_limit
            used = _num(row.get("time_limit_s"))
            row["time_limit_requested_s"] = req
            row["budget_shortened"] = bool(used is not None and used < req - 1e-6)
        super().emit(row, phase)


def network_seeds(smoke: bool, seeds: Optional[Sequence[int]]) -> Dict[str, List[int]]:
    if smoke:
        return {c: [0] for c in X4.CASE_ORDER}
    if seeds is not None:
        return {c: [s for s in seeds if s in X4.CASES[c]["seeds"]] for c in X4.CASE_ORDER}
    return {"usd4h_ebaas": list(SEEDS10), "r5_stress4h": list(SEEDS5)}


def run_network(args: argparse.Namespace) -> None:
    out_dir = stage_dir("network", args.smoke, args.out_root)
    tl = SMOKE_TL if args.smoke else X4.TIME_LIMIT
    seeds = network_seeds(args.smoke, args.seeds)
    done = X4.last_per_key(C.load_jsonl(os.path.join(out_dir, RECORDS)))
    # an ILP row cut short by the wall budget (not OPTIMAL) is re-solved; the implied home written
    # row inherits the relaxed row's status and limit, so it is re-planned with it
    done = {k: r for k, r in done.items() if not budget_cut(r, tl)}
    plan = [it for it in X4.build_plan(done, list(X4.CASE_ORDER), seeds) if it[0] == "a"]
    if args.dry_run:
        print(json.dumps({"stage": "network", "out_dir": out_dir, **X4.plan_summary(plan),
                          "expected_wall_min_r6": EST_MIN["network"]}, indent=1))
        return
    budget = C.WallBudget(args.budget_min * 60.0, margin_s=0.0 if args.smoke else 90.0,
                          min_solve_s=1.0 if args.smoke else 30.0)
    runner = NetworkRunner(out_dir, tl, args.threads, budget, smoke=args.smoke, pr=BASE)
    print(f"# R6 network: {len(plan)} items -> {out_dir}", flush=True)
    for phase, case, seed, infra, methods in X4.group_plan(plan):
        try:
            runner.run_group(phase, case, seed, infra, methods)
        except Exception as exc:  # noqa: BLE001
            for m in methods:
                runner.emit({"case": case, "seed": seed, "infra": infra, "method": m, "status": "ERROR",
                             "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-3000:]},
                            phase)
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"stage": "network", "wall_s": budget.elapsed(), "rows": runner.n_runs,
                             "smoke": args.smoke, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(analyse_network(out_dir), flush=True)


def analyse_network(out_dir: str) -> str:
    recs = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not recs:
        return "network: no records"
    rows = X4.last_per_key(recs)
    df = C.records_to_frame(sorted(rows.values(), key=lambda r: (r["case"], r["seed"], r["infra"], r["method"])))
    df.to_csv(os.path.join(out_dir, "results.csv"), index=False)
    dec = X4.decomposition(rows)
    dec = dec[dec.targets == "relaxed"] if not dec.empty else dec
    dec.to_csv(os.path.join(out_dir, "decomposition.csv"), index=False)
    cols = ["H_policy", "H_ilp", "N_policy", "N_ilp", "VoN_policy", "VoN_ilp", "VoC_network", "VoC_home",
            "VoN_policy_pct", "VoN_ilp_pct", "VoC_network_pct", "VoC_home_pct", "total_effect", "interaction",
            "shapley_network", "shapley_coordination"]
    summ = long_summary(dec.rename(columns={"metric": "basis"}), ["case", "basis", "policy"], cols)
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    eb = X4.ebaas_table(rows)
    eb.to_csv(os.path.join(out_dir, "ebaas_metrics.csv"), index=False)
    md5_bad = [f"{c}/{s}" for (c, s), g in df.groupby(["case", "seed"]) if g["demand_md5"].nunique() != 1]
    L = ["# R6 network -- value of the swap network vs coordination (P 60, w 18, v 15)", "",
         "2 x 2 per seed (home charging vs network) x (policy vs relaxed aggregated ILP), as r5_x4_network phase a; "
         "VoN = home - network, VoC = policy - ILP; Shapley shares; mean +- exact t 95 % over seeds (paired per seed).", ""]
    if not summ.empty:
        s2 = summ[(summ.basis == "total_end_adjusted") & (summ.policy == "best_rule")]
        L += ["## best_rule vs relaxed ILP, end-adjusted totals (USD per window)", "",
              C.markdown_table(s2, ["case", "policy", "metric", "mean", "ci95", "n"], 2), ""]
    late_cols = ["n_late", "n_late_over_30min", "n_late_over_60min", "mean_lateness_min", "max_lateness_min",
                 "served_share"]
    pol = df[df.status.isin(["POLICY", "OPTIMAL", "TIME_LIMIT", "SUBOPTIMAL", "INTERRUPTED"])
             & (df.get("solve_mode", pd.Series(index=df.index, dtype=object)) != "implied_by_construction")]
    late = long_summary(pol, ["case", "infra", "method"], [c for c in late_cols if c in pol.columns])
    late.to_csv(os.path.join(out_dir, "lateness.csv"), index=False)
    if not late.empty:
        wl = late.pivot_table(index=["case", "infra", "method"], columns="metric", values="mean",
                              aggfunc="first").reset_index()
        L += ["## Lateness per policy (seed means; lateness.csv has the t 95 % half-widths)", "",
              C.markdown_table(wl, [c for c in ["case", "infra", "method"] + late_cols if c in wl.columns], 2), ""]
    L += ["## Anomalies", "", f"* demand md5 not unique for {md5_bad}" if md5_bad else "* none", "",
          "Files: records.jsonl, results.csv, decomposition.csv, summary.csv (long: case, basis = total or "
          "total_end_adjusted, policy, metric = quantity of the X4 decomposition, mean, ci95, n), ebaas_metrics.csv, "
          "lateness.csv."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ---------------------------------------------------------------------------
# rolling (r5_x3_rolling, lambda 10, relaxed targets, under the base pricing)
# ---------------------------------------------------------------------------
ROLL_W, ROLL_K, ROLL_LAMBDA, ROLL_WINDOW_TL = X3.DEFAULT_W, X3.DEFAULT_K, X3.FORECAST_LAMBDA, X3.TIME_LIMIT_WINDOW
ROLL_EST_S = {"usd4h": 61.0, "r5_stress4h": 86.0}


def rolling_items(smoke: bool, seeds: Optional[Sequence[int]]) -> List[Tuple[str, int]]:
    if smoke:
        return [("usd4h", 0)]
    sd = {"usd4h": list(SEEDS10), "r5_stress4h": list(SEEDS5)}
    if seeds is not None:
        sd = {c: [s for s in seeds if s in v] for c, v in sd.items()}
    out: List[Tuple[str, int]] = []
    for i in range(max(len(v) for v in sd.values())):
        for c in ("usd4h", "r5_stress4h"):
            if i < len(sd[c]):
                out.append((c, sd[c][i]))
    return out


def run_rolling(args: argparse.Namespace) -> None:
    from ebike_swap_sim.rolling import rolling_horizon
    out_dir = stage_dir("rolling", args.smoke, args.out_root)
    items = rolling_items(args.smoke, args.seeds)
    path = os.path.join(out_dir, RECORDS)
    if args.dry_run:
        print(json.dumps({"stage": "rolling", "items": items, "W": ROLL_W, "k": ROLL_K, "lambda_min": ROLL_LAMBDA,
                          "expected_wall_min": EST_MIN["rolling"]}, indent=1))
        return
    C.ensure_dir(out_dir)
    done = {(r["case"], int(r["seed"])) for r in C.load_jsonl(path) if r.get("status") == "ROLLING"}
    wtl = min(ROLL_WINDOW_TL, 20.0) if args.smoke else ROLL_WINDOW_TL
    budget = C.WallBudget(args.budget_min * 60.0, margin_s=60.0, min_solve_s=30.0)
    rows: List[Dict[str, Any]] = C.load_jsonl(path)
    for case, seed in items:
        if (case, seed) in done:
            continue
        base = {"case": case, "seed": seed, "mult": 1.0, "policy": "rolling", "targets": "relaxed",
                "lookahead_min": ROLL_LAMBDA, "W": ROLL_W, "k": ROLL_K, "threads": args.threads,
                **price_cols(BASE, "rolling")}
        est = ROLL_EST_S[case]
        if budget.remaining() - budget.margin < est:
            row = {**base, "status": C.SKIPPED_BUDGET, "skip_reason": f"wall budget (estimate {est:.0f} s)"}
        else:
            try:
                inst0, prun = build_case(case, seed, 1.0, args.smoke)
                inst = priced(inst0, BASE, "rolling")
                inst.meta["name"] = f"r6-{inst0.meta['name']}-{BASE['label']}"
                lib = C.build_library(inst, prun, strict=False)[0]          # X3: strict=False day library
                chk = cm.check_lib_prices(inst, lib)
                t0 = time.perf_counter()
                res = rolling_horizon(inst, W=ROLL_W, k=ROLL_K, lookahead_min=ROLL_LAMBDA, lib=lib, arc_options=prun,
                                      final_targets="relaxed", forecast=None, n_scenarios=1, forecast_seed=int(seed),
                                      aggregate=True, threads=args.threads, time_limit=wtl,
                                      params=dict(C.ILP_PARAMS_R3))
                rt = time.perf_counter() - t0
                summ = res.summary()
                met = metrics(res.inst, res.lib, res.schedule)
                row = {**base, **{k: v for k, v in summ.items() if not k.startswith("param_")},
                       "status": "ROLLING", "runtime": rt, "demand_md5": C.demand_md5(inst), "name": inst.meta["name"],
                       "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "window_time_limit": wtl,
                       "families": summ.get("violations"), "served_share": met.get("served_share"),
                       "n_late": met.get("n_late"), "lib_price_checked_arcs": chk["n_checked"],
                       "n_window_aggregate": sum(1 for w in res.windows if w.get("aggregate")),
                       "windows": [{kk: w.get(kk) for kk in ("t0", "W", "status", "gap", "runtime", "n_known",
                                                             "n_busy", "fallback", "aggregate")} for w in res.windows],
                       "notes": res.notes, **C.flatten_cost(res.cost), **C.flatten_r5(met),
                       **lateness_cols(res.inst, res.lib, res.schedule)}
                del lib, res
                gc.collect()
            except Exception as exc:  # noqa: BLE001
                row = {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}",
                       "traceback": traceback.format_exc()[-3000:]}
        C.append_jsonl(path, row)
        rows.append(C.jsonable(row))
        C.write_csv(rows, os.path.join(out_dir, "results.csv"))
        print(json.dumps({k: C.jsonable(row.get(k)) for k in ("case", "seed", "status", "total", "total_end_adjusted",
                                                              "served_share", "n_late_over_60min", "runtime")}),
              flush=True)
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"stage": "rolling", "wall_s": budget.elapsed(), "smoke": args.smoke,
                             "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(analyse_rolling(out_dir, args.smoke, args.out_root), flush=True)


def analyse_rolling(out_dir: str, smoke: bool = False, root: Optional[str] = None) -> str:
    """Join the rolling rows with the offline relaxed ILP and the rules of the same instance
    (headline: usd4h x1; psweep: r5_stress4h, and usd4h copies) under the base pricing, per seed:
    headline = best_rule - offline, value of information = rolling - offline, value of coordination
    online = best_rule - rolling (end-adjusted and raw totals), then mean and exact-t CI."""
    roll = [r for r in C.load_jsonl(os.path.join(out_dir, RECORDS)) if r.get("status") == "ROLLING"]
    if not roll:
        return "rolling: no records"
    ref: Dict[Tuple, Dict[str, Any]] = {}
    for st in ("headline", "psweep"):
        p = os.path.join(stage_dir(st, smoke, root), RECORDS)
        for k, r in X1.last_per_key(C.load_jsonl(p)).items():
            if k[1] == BASE["label"] and float(k[3]) == 1.0 and X1.row_is_done(r):
                ref.setdefault(k, r)
    out: List[Dict[str, Any]] = []
    for r in {(x["case"], int(x["seed"])): x for x in roll}.values():
        case, seed = r["case"], int(r["seed"])
        off = ref.get(grid_key(case, BASE["label"], seed, 1.0, "relaxed", "ilp"))
        rules = [ref.get(grid_key(case, BASE["label"], seed, 1.0, "relaxed", m)) for m in RULES]
        rules = [x for x in rules if x is not None and x.get("status") == "POLICY"]
        rec: Dict[str, Any] = {"case": case, "seed": seed, "rolling_total": _num(r.get("total")),
                               "rolling_total_end_adjusted": _num(r.get("total_end_adjusted")),
                               "rolling_served_share": _num(r.get("served_share")),
                               "rolling_n_late_over_60min": _num(r.get("n_late_over_60min")),
                               "rolling_runtime": _num(r.get("runtime")),
                               "offline_status": off.get("status") if off else None,
                               "demand_md5_match": (off is not None and off.get("demand_md5") == r.get("demand_md5"))}
        for basis, col in (("ea", "total_end_adjusted"), ("raw", "total")):
            o = _num(off.get(col)) if off else None
            b = min((_num(x.get(col)) for x in rules if _num(x.get(col)) is not None), default=None)
            ro = _num(r.get(col))
            rec[f"offline_{basis}"], rec[f"best_rule_{basis}"] = o, b
            rec[f"headline_{basis}"] = None if b is None or o is None else b - o
            rec[f"value_of_information_{basis}"] = None if ro is None or o is None else ro - o
            rec[f"value_of_coordination_online_{basis}"] = None if ro is None or b is None else b - ro
            rec[f"share_surviving_online_{basis}"] = (None if rec[f"headline_{basis}"] in (None, 0)
                                                     or rec[f"value_of_coordination_online_{basis}"] is None
                                                     else rec[f"value_of_coordination_online_{basis}"]
                                                     / rec[f"headline_{basis}"])
            rec[f"gap_rolling_vs_best_{basis}_pct"] = gap_pct(b, ro)
        out.append(rec)
    per = pd.DataFrame(out).sort_values(["case", "seed"])
    per.to_csv(os.path.join(out_dir, "per_instance.csv"), index=False)
    cols = [c for c in per.columns if c not in ("case", "seed", "offline_status", "demand_md5_match")]
    summ = long_summary(per, ["case"], cols)
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    miss = per[~per.demand_md5_match.astype(bool)]
    L = ["# R6 rolling -- foresight vs coordination under P 60, w 18, v 15", "",
         f"Rolling horizon W {ROLL_W}, k {ROLL_K}, lambda {ROLL_LAMBDA:g} min, aggregated windows, relaxed targets; "
         "offline reference and rules from the headline / psweep rows of the same instance (demand md5 checked). "
         "Per seed: headline = best_rule - offline, VoI = rolling - offline, VoC online = best_rule - rolling; mean "
         "+- exact t 95 %.", ""]
    if not summ.empty:
        s2 = summ[summ.metric.isin(["headline_ea", "value_of_information_ea", "value_of_coordination_online_ea",
                                    "share_surviving_online_ea", "rolling_served_share", "rolling_n_late_over_60min"])]
        L += [C.markdown_table(s2, ["case", "metric", "mean", "ci95", "n"], 3), ""]
    L += ["## Anomalies", "", f"* {len(miss)} rolling row(s) without a matching offline reference (md5 / missing)"
          if len(miss) else "* none"]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ---------------------------------------------------------------------------
# levers and fleet (r5_x5_stress machinery under the base pricing)
# ---------------------------------------------------------------------------
_X5_SCHED_COLS = X5.sched_cols


def _sched_cols_r6(inst: Instance, lib: Any, rec: Dict[str, Any]) -> Dict[str, Any]:
    out = _X5_SCHED_COLS(inst, lib, rec)
    if rec.get("schedule") is not None:
        out.update(lateness_cols(inst, lib, rec["schedule"]))
    if rec.get("obj") is not None:
        out.update(obj_check_cols(rec))
    return out


def last_done_rows(path: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Row per ``(key_md5, method)`` of an X5-layout ``records.jsonl``: the last done row
    (``r5_x5_stress._is_done``), else the last row.  Rows marked ``retry_worse`` (a
    ``r6_fill --retry-unsolved`` re-solve that ended with a worse incumbent than the row it was
    meant to replace) are ignored, so the better earlier row stays the row of the key."""
    rows: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in C.load_jsonl(path):
        if r.get("retry_worse"):
            continue
        k = (str(r.get("key_md5")), str(r.get("method")))
        if X5._is_done(r) or k not in rows:
            rows[k] = r
    return rows


def incumbent_path(sched_dir: str, key_md5: str, method: str) -> str:
    """``<stage>/schedules/<key_md5>_<method>.json``: the ILP incumbent of a case (decision part,
    ``r5_x5_stress.portable``), saved by :class:`StressRunner` and offered as the MIP-start
    candidate ``prior_incumbent`` when the same key and method are solved again (a budget-cut
    resume or ``r6_fill --retry-unsolved``)."""
    return os.path.join(sched_dir, f"{key_md5}_{method}.json")


def load_incumbent(sched_dir: str, key_md5: str, method: str) -> Optional[Schedule]:
    p = incumbent_path(sched_dir, key_md5, method)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return Schedule.from_dict(json.load(fh))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def no_transfer_variants(cands: Sequence[Tuple[str, Schedule]]) -> List[Tuple[str, Schedule]]:
    """For every start candidate that carries transfers (``h`` / ``z``), a copy with none
    (``<label>|no_transfers``): a schedule learnt on a lock-out variant (sink services that do
    not exist on the reference instance) is rejected by ``evaluate.check`` on the reference,
    while its ``x / u / c`` part with zero transfers is feasible there and is what the lock-out
    solve learnt.  Candidates are still checked and the cheapest clean one wins; a start
    without the forced lock-out transfers is skipped by ``pick_start`` on the lock-out cells."""
    out: List[Tuple[str, Schedule]] = []
    for label, s in cands:
        if (s.h or s.z) and not label.endswith("|no_transfers"):
            out.append((f"{label}|no_transfers", Schedule(x={k: list(v) for k, v in s.x.items()}, u=dict(s.u),
                                                          c=dict(s.c), h={}, z={})))
    return out


class StressRunner(X5.Runner):
    """X5 runner writing ONE ``records.jsonl`` / ``cases.jsonl`` per stage; every library is
    price-checked; rows carry the pricing and lateness columns.

    Additions over ``r5_x5_stress.Runner``: (1) ``cases.jsonl`` is phase-aware -- a case noted
    earlier without an ILP (``ilp_method`` None, e.g. an LP-only cell) is noted again when the
    same (sub, cell, seed, target, key) is planned with an ILP, so the ILP row is visible to
    ``wide_r6``; (2) the ILP incumbent of every solve is saved under ``schedules/<key>_<method>.json``
    and offered as ``prior_incumbent`` when the key is solved again; (3) every start candidate
    with transfers is also offered without them (``no_transfer_variants``), so the incumbent of
    a lock-out cell can seed the reference cell of the same arc library."""

    def __init__(self, out_dir: str, stage: str, pr: Dict[str, Any], threads: int) -> None:
        self.stage = stage
        self.pr = pr
        super().__init__(out_dir, threads=threads, lib_cache=2)
        self.sched_dir = C.ensure_dir(os.path.join(self.out_dir, "schedules"))
        self.rows = last_done_rows(self._records("stress"))
        self.case_ilp: Dict[Tuple, Optional[str]] = {}
        for c in C.load_jsonl(self._cases("stress")):
            tag = (c["sub"], c["cell"], int(c["seed"]), c["target"], c["key_md5"])
            if c.get("ilp_method") or tag not in self.case_ilp:
                self.case_ilp[tag] = c.get("ilp_method")
        self._cur_key: Optional[str] = None
        self._cur_ilp_method: Optional[str] = None
        self._last_ilp_row: Optional[Tuple[str, str]] = None

    def _records(self, sub: str) -> str:
        return os.path.join(self.out_dir, RECORDS)

    def _cases(self, sub: str) -> str:
        return os.path.join(self.out_dir, "cases.jsonl")

    def note_case(self, case: X5.Case, key: str) -> None:
        tag = (case.sub, case.cell, int(case.seed), case.target, key)
        im = X5.ilp_method(case.ilp_tl) if case.ilp_tl else None
        if tag in self.seen_cases and (im is None or self.case_ilp.get(tag) is not None):
            return
        self.seen_cases.add(tag)
        self.case_ilp[tag] = im
        C.append_jsonl(self._cases(case.sub), {"sub": case.sub, "cell": case.cell, "seed": case.seed,
                                                "target": case.target, "key_md5": key, "phase": case.phase,
                                                "ilp_method": im, "lp": case.lp, **case.info})

    def case_status(self, case: X5.Case) -> Tuple[Instance, Instance, str, Dict[str, Any], List[str]]:
        w, t, key, pr, todo = super().case_status(case)
        self._cur_key = key
        self._cur_ilp_method = X5.ilp_method(case.ilp_tl) if case.ilp_tl else None
        return w, t, key, pr, todo

    def pick_start(self, inst: Instance, lib: Any, sig: str, rule_recs: Dict[str, Dict[str, Any]]
                   ) -> Tuple[Optional[Schedule], str]:
        lst = list(self.pool.get(sig, []))
        cands = list(lst)
        if self._cur_key and self._cur_ilp_method:
            prior = load_incumbent(self.sched_dir, self._cur_key, self._cur_ilp_method)
            if prior is not None:
                cands.append(("prior_incumbent", prior))
        cands += no_transfer_variants(cands)
        self.pool[sig] = cands
        try:
            return super().pick_start(inst, lib, sig, rule_recs)
        finally:
            if lst:
                self.pool[sig] = lst
            else:
                self.pool.pop(sig, None)

    def add_pool(self, sig: str, label: str, sched: Schedule) -> None:
        super().add_pool(sig, label, sched)
        if label.startswith("ilp:") and self._last_ilp_row is not None:
            key, m = self._last_ilp_row
            with open(incumbent_path(self.sched_dir, key, m), "w", encoding="utf-8") as fh:
                json.dump(C.jsonable(X5.portable(sched).to_dict()), fh)

    def emit(self, sub: str, row: Dict[str, Any]) -> None:
        row = {**row, **price_cols(self.pr, self.stage)}
        # X5.Runner keys sub_rows by X5.SUBS (core / boundary / fleet / levers); the R6 stages use
        # their own sub names (stress, pack, levers_ext, ...) and one records file, so the sub is
        # created on first use (KeyError otherwise, which the error-row emit raised again).
        self.sub_rows.setdefault(sub, {})
        super().emit(sub, row)
        m = str(row.get("method") or "")
        if m.startswith("ILP_tl") and row.get("status") not in (C.SKIPPED_BUDGET, "ERROR"):
            self._last_ilp_row = (str(row.get("key_md5")), m)

    def refresh_csv(self, sub: str) -> None:
        path = os.path.join(self.out_dir, "results.csv")
        C.records_to_frame(list(self.rows.values())).to_csv(path + ".tmp", index=False)
        os.replace(path + ".tmp", path)

    def library(self, inst: Instance, pruning: Dict[str, Any]):
        lib, sig, bt = super().library(inst, pruning)
        cm.check_lib_prices(inst, lib)
        return lib, sig, bt


def plan_levers_r6(pr: Dict[str, Any], smoke: bool, seeds: Optional[Sequence[int]]) -> List[X5.Case]:
    """reference / P0 (no on-site charging) / lock-out of 2 spares (share 0.25) on r5_stress4h_k8,
    relaxed control, ILP 600 s; builders = the X5 lever builders on the repriced reference."""
    family = "r5_stress4h_k8"
    over = {"window_h": 2.0, "n_bikes": 4} if smoke else {}
    sd = [0] if smoke else (list(seeds) if seeds is not None else list(SEEDS5))
    tl = 20.0 if smoke else TL_LONG
    k = 4 if smoke else 8
    out: List[X5.Case] = []
    for seed in sd:
        def ref(seed: int = seed) -> Instance:
            return C.make_instance(family, seed=seed, **over)

        def b_ref(seed: int = seed) -> Instance:
            return priced(ref(seed), pr, "levers")

        def b_p0(seed: int = seed) -> Instance:
            return priced(gen.site_power_cap_sweep(ref(seed), multiples=[0])[0][1], pr, "levers")

        def b_lock(seed: int = seed, share: float = 0.25) -> Instance:
            base = ref(seed)
            n = X5.n_locked(base, share)
            return priced(gen.add_battery_lockout(base, share=share, slots=X5.lockout_slots(base, n, seed), seed=seed),
                          pr, "levers")

        common = {"family_size": family, "pricing": pr["label"]}
        tag = f"{pr['label']}:{seed}:{'smoke' if smoke else 'full'}"
        out.append(X5.Case("levers", "reference", seed, X5.RELAXED, f"r6:ref:{tag}", b_ref, tl, False, "reference",
                           {**common, "lever": "reference", "lever_value": None, "eps_wh": 25.0, "M": 1,
                            "lockout_share": 0.0, "P_cap_multiple": None}, k, 48))
        out.append(X5.Case("levers", "P0", seed, X5.RELAXED, f"r6:P0:{tag}", b_p0, tl, False, "site_power",
                           {**common, "lever": "site_power", "lever_value": 0.0, "P_cap_multiple": 0}, k, 48))
        out.append(X5.Case("levers", "lockout0.25", seed, X5.RELAXED, f"r6:lock0.25:{tag}", b_lock, tl, False,
                           "lockout", {**common, "lever": "lockout", "lever_value": 0.25, "lockout_share": 0.25,
                                       "lockout_n_target": 2}, k, 48))
    return out


FLEET_K: Tuple[int, ...] = (4, 6, 8, 10)
FLEET_B: Tuple[int, ...] = (1, 2, 3, 4)
FLEET_PACK = 0.6


def plan_fleet_r6(pr: Dict[str, Any], smoke: bool, seeds: Optional[Sequence[int]]) -> List[X5.Case]:
    """K x B grid at the 0.6 kWh pack (48 orders), relaxed control, rules + ILP (300 s, 600 s at
    K >= 8 as round 5), seed-major."""
    sd = [0] if smoke else (list(seeds) if seeds is not None else list(SEEDS3))
    Ks = (4,) if smoke else FLEET_K
    Bs = (1, 2) if smoke else FLEET_B
    out: List[X5.Case] = []
    for seed in sd:
        for k in Ks:
            for B in Bs:
                tl = 20.0 if smoke else (TL_LONG if k >= 8 else TIME_LIMIT)

                def b(seed: int = seed, k: int = k, B: int = B) -> Instance:
                    return priced(gen.make_fleet_sweep_instance("r5_stress4h", seed=seed, n_bikes=k, B=B,
                                                                pack_kwh=FLEET_PACK), pr, "fleet")
                out.append(X5.Case("fleet", f"K{k}_B{B}_pack{FLEET_PACK:g}", seed, X5.RELAXED,
                                   f"r6:fleet:{pr['label']}:{seed}:{k}:{B}", b, tl, False, "ilp",
                                   {"K": k, "B_per_site": B, "pack_kwh": FLEET_PACK, "pricing": pr["label"]}, k, 48))
    return out


def run_stress(stage: str, args: argparse.Namespace) -> None:
    out_dir = stage_dir(stage, args.smoke, args.out_root)
    plan = (plan_levers_r6 if stage == "levers" else plan_fleet_r6)(BASE, args.smoke, args.seeds)
    if args.dry_run:
        exp = sum(X5.est_case_s(c)[0] for c in plan) / 60.0
        print(json.dumps({"stage": stage, "out_dir": out_dir, "cases": len(plan), "x5_estimate_min": round(exp, 1),
                          "expected_wall_min_r6": EST_MIN[stage]}, indent=1))
        for c in plan:
            print("  ", c.cell, c.seed, c.ilp_tl)
        return
    X5.sched_cols = _sched_cols_r6            # lateness + objective-check columns on every priced schedule
    runner = StressRunner(out_dir, stage, BASE, args.threads)
    print(f"# R6 {stage}: {len(plan)} cases -> {out_dir}", flush=True)
    runner.run_plan(stage, plan, args.budget_min * 60.0)
    print(analyse_stress(stage, out_dir), flush=True)


def wide_r6(out_dir: str) -> pd.DataFrame:
    """``r5_x5_stress.wide_cases`` on the single-file layout of a round-6 stage (rows per key by
    :func:`last_done_rows`: ``retry_worse`` rows are ignored)."""
    rows = last_done_rows(os.path.join(out_dir, RECORDS))
    cases: Dict[Tuple, Dict[str, Any]] = {}
    for c in C.load_jsonl(os.path.join(out_dir, "cases.jsonl")):
        ck = (c["sub"], c["cell"], int(c["seed"]), c["target"])
        # several cases.jsonl rows per key (an LP-only note and a later ILP note of the same
        # cell): the one naming an ILP method wins, so its ILP row is read
        if ck not in cases or c.get("ilp_method") or not cases[ck].get("ilp_method"):
            cases[ck] = c
    fields = tuple(X5._WIDE_FIELDS) + ("n_late_over_60min", "n_late_over_30min", "mean_lateness_min",
                                       "max_lateness_min", "n_late", "obj_eq_eval")
    out: List[Dict[str, Any]] = []
    for c in cases.values():
        key = c["key_md5"]
        w: Dict[str, Any] = dict(c)
        anyrow = next((rows[(key, m)] for m in ("best_rule", "baseline_r2") if (key, m) in rows), None)
        if anyrow is not None:
            for f in ("n_bikes", "n_orders", "H", "L", "pack_kwh", "bB_site", "total_spares", "n_locked",
                      "allocated_per_bike_window", "bike_capex_per_window", "demand_md5", "orders_md5", "P", "w", "v"):
                w[f] = anyrow.get(f)
        for r in RULES + ("best_rule",):
            m = "best_rule" if r == "best_rule" else f"baseline_{r}"
            row = rows.get((key, m))
            if row is None:
                continue
            if r == "best_rule":
                # X5's best_rule row is the argmin by RAW total; the round-6 tables use the
                # end-adjusted best rule, so every best_rule_* metric comes from that rule's row
                # (cost and service metrics of the same rule, as grid_per_instance)
                ea_rule = row.get("best_rule_end_adjusted_rule") or row.get("rule")
                ea_row = rows.get((key, f"baseline_{ea_rule}"))
                w["best_rule_rule_raw"] = row.get("rule")
                w["best_rule_rule"] = ea_rule
                w["best_rule_total_end_adjusted_min"] = row.get("best_rule_total_end_adjusted_min")
                w["best_rule_source"] = "end_adjusted_argmin" if ea_row is not None else "raw_argmin_row"
                if ea_row is not None:
                    row = ea_row
            for f in fields:
                w[f"{r}_{f}"] = row.get(f)
        im = c.get("ilp_method")
        if im and (key, im) in rows:
            row = rows[(key, im)]
            for f in tuple(X5._ILP_FIELDS) + ("n_late_over_60min", "mean_lateness_min", "max_lateness_min",
                                               "obj_eq_eval", "gap_vs_best_rule_pct_end_adjusted", "gap_vs_r2_pct",
                                               "gap_vs_r2_pct_end_adjusted"):
                w[f"ilp_{f}"] = row.get(f)
        out.append(w)
    return pd.DataFrame(out)


def _best_ea(df: pd.DataFrame) -> pd.Series:
    """End-adjusted best rule: the min of total_end_adjusted over the rules (X5 'best_rule' row
    is the argmin by raw total; ``best_rule_total_end_adjusted_min`` is the end-adjusted min)."""
    return pd.to_numeric(df.get("best_rule_total_end_adjusted_min"), errors="coerce")


def analyse_stress(stage: str, out_dir: str) -> str:
    df = wide_r6(out_dir)
    if df.empty:
        return f"{stage}: no cases"
    df.to_csv(os.path.join(out_dir, "cases_wide.csv"), index=False)
    df["best_ea"] = _best_ea(df)
    df["ilp_ea"] = pd.to_numeric(df.get("ilp_total_end_adjusted"), errors="coerce")
    df["gap_best_ea_pct"] = [gap_pct(b, i) for b, i in zip(df["best_ea"], df["ilp_ea"])]
    L = [f"# R6 {stage} -- under P 60, w 18, v 15", "",
         "r5_x5_stress machinery (relaxed control rho 0 / R_end 0, aggregated ILP, Threads 3, Seed 0); best rule = "
         "per-instance min over the rules (end-adjusted); mean +- exact t 95 % over seeds; deltas paired per seed.", ""]
    if stage == "levers":
        ref = df[df.cell == "reference"].set_index("seed")
        for col in ("ilp_ea", "best_ea"):
            df[f"delta_{col}"] = [(_num(r[col]) - _num(ref.at[r["seed"], col]))
                                  if r["seed"] in ref.index and _num(r[col]) is not None
                                  and _num(ref.at[r["seed"], col]) is not None else None for _, r in df.iterrows()]
        cols = ["ilp_ea", "best_ea", "gap_best_ea_pct", "delta_ilp_ea", "delta_best_ea", "ilp_gap", "ilp_served_share",
                "best_rule_served_share", "ilp_n_late_over_60min", "best_rule_n_late_over_60min",
                "ilp_mean_lateness_min", "ilp_lockout_end_share_excl_sink"]
        summ = long_summary(df, ["lever", "cell"], cols)
        L += [C.markdown_table(summ[summ.metric.isin(["ilp_ea", "best_ea", "gap_best_ea_pct", "delta_ilp_ea",
                                                       "delta_best_ea", "ilp_gap", "ilp_served_share"])],
                               ["lever", "cell", "metric", "mean", "ci95", "n"], 3), ""]
        st = df.groupby("cell")["ilp_status"].agg(lambda s: json.dumps(s.value_counts().to_dict()))
        L += ["ILP status per lever: " + "; ".join(f"{k} {v}" for k, v in st.items()), ""]
    else:
        df["alloc"] = pd.to_numeric(df.get("allocated_per_bike_window"), errors="coerce")
        df["K"] = pd.to_numeric(df["K"], errors="coerce")
        df["best_system_cost"] = df["best_ea"] + df["alloc"] * df["K"]
        df["ilp_system_cost"] = df["ilp_ea"] + df["alloc"] * df["K"]
        cols = ["best_ea", "ilp_ea", "best_system_cost", "ilp_system_cost", "best_rule_served_share", "ilp_served_share",
                "gap_best_ea_pct", "ilp_gap", "ilp_n_late_over_60min", "best_rule_n_late_over_60min"]
        summ = long_summary(df, ["K", "B_per_site"], cols)
        # cost-minimal design within the grid per policy (seed-mean system cost) and its served share
        best_rows: List[Dict[str, Any]] = []
        for pol, sc, ss in (("best_rule", "best_system_cost", "best_rule_served_share"),
                            ("ilp", "ilp_system_cost", "ilp_served_share")):
            g = df.assign(_sc=pd.to_numeric(df[sc], errors="coerce"),
                          _ss=pd.to_numeric(df[ss], errors="coerce")).dropna(subset=["_sc"])
            if g.empty:
                continue
            m = g.groupby(["K", "B_per_site"]).agg(system_cost=("_sc", "mean"), served_share=("_ss", "mean"),
                                                    n=("_sc", "size")).reset_index()
            full_n = m["n"].max()
            m = m[m["n"] == full_n]
            top = m.sort_values("system_cost").iloc[0]
            per_seed = g.loc[g.groupby("seed")["_sc"].idxmin(), ["seed", "K", "B_per_site"]]
            ci = mean_ci(g[(g.K == top.K) & (g.B_per_site == top.B_per_site)]["_sc"].tolist())
            best_rows.append({"policy": pol, "K": int(top.K), "B_per_site": int(top.B_per_site),
                              "system_cost_mean": top.system_cost, "system_cost_ci95": ci[1],
                              "served_share_mean": top.served_share, "n_seeds": int(full_n),
                              "per_seed_argmin": json.dumps({int(r.seed): f"K{int(r.K)}_B{int(r.B_per_site)}"
                                                             for r in per_seed.itertuples()})})
        opt = pd.DataFrame(best_rows)
        opt.to_csv(os.path.join(out_dir, "cost_minimal_design.csv"), index=False)
        fl = df.rename(columns={})
        fl["best_rule_total_end_adjusted"] = df["best_ea"]
        try:
            fr = X5.fleet_frontier(fl.assign(pack_kwh=pd.to_numeric(fl["pack_kwh"], errors="coerce")))
            fr.to_csv(os.path.join(out_dir, "fleet_frontier.csv"), index=False)
        except Exception as exc:  # noqa: BLE001
            print(f"# fleet_frontier failed: {exc}", flush=True)
        L += ["## Cost-minimal design within the grid (system cost = end-adjusted total incl. spare set-up (27) + "
              "K x allocated bike + rider cost per window)", "",
              C.markdown_table(opt, list(opt.columns), 2) if not opt.empty else "-", ""]
        sm = summ[summ.metric.isin(["ilp_system_cost", "best_system_cost", "ilp_served_share", "gap_best_ea_pct"])]
        L += ["## Grid means", "", C.markdown_table(sm, ["K", "B_per_site", "metric", "mean", "ci95", "n"], 2), ""]
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    errs = [r for r in C.load_jsonl(os.path.join(out_dir, RECORDS)) if r.get("status") in ("ERROR", C.SKIPPED_BUDGET)]
    L += ["## Anomalies", "", f"* {len(errs)} ERROR / SKIPPED_BUDGET row(s)" if errs else "* none",
          "", "Files: records.jsonl, cases.jsonl, results.csv, cases_wide.csv, summary.csv"
          + (", cost_minimal_design.csv, fleet_frontier.csv" if stage == "fleet" else "") + "."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ---------------------------------------------------------------------------
# rl (r5_x7_rl retrained on the repriced instances)
# ---------------------------------------------------------------------------
def _install_rl_loader(pr: Dict[str, Any]) -> Any:
    """Route every X7 instance (training and test seeds) through the repriced round-5 builder;
    the JSON cache under ``<out>/instances`` holds the repriced instances (checked on load)."""
    from experiments import r5_x7_rl as X7

    def load_written(family: str, seed: int, cache_dir: str) -> Instance:
        path = os.path.join(cache_dir, f"{family}_seed{int(seed)}.json")
        if os.path.exists(path):
            inst = Instance.load(path)
            if (inst.meta.get("pricing") or {}).get("label") != pr["label"]:
                raise RuntimeError(f"{path}: cached instance not priced {pr['label']}")
            return inst
        inst = priced(C.make_instance(family, int(seed)), pr, "rl")
        inst.save(path)
        return inst

    X7.load_written = load_written
    _wrap_x7_rows(X7, pr)
    return X7


def _wrap_x7_rows(X7: Any, pr: Dict[str, Any]) -> None:
    """Round-6 columns on every X7 row (pricing; lateness of every priced schedule, as the other
    stages) and the budget-cut resume rule for the X7 ILP rows.  Idempotent."""
    if getattr(X7, "_r6_wrapped", None) == pr["label"]:
        return
    orig_sched = getattr(X7, "_r6_orig_schedule_row", X7.schedule_row)
    orig_skip = getattr(X7, "_r6_orig_skipped_row", X7.skipped_row)
    orig_done = getattr(X7, "_r6_orig_ilp_done", X7._ilp_done)
    X7._r6_orig_schedule_row, X7._r6_orig_skipped_row, X7._r6_orig_ilp_done = orig_sched, orig_skip, orig_done

    def schedule_row(kind: str, family: str, seed: int, method: str, inst: Instance, lib: Any, sched: Any,
                     runtime: float, md5: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        row = orig_sched(kind, family, seed, method, inst, lib, sched, runtime, md5, extra)
        lc = lateness_cols(inst, lib, sched)
        row.update(lc)
        row.setdefault("n_late", lc.get("n_late_min"))
        if kind == "ilp" and row.get("time_limit") is not None:
            row["budget_shortened"] = bool(float(row["time_limit"]) < float(row.get("time_limit_requested")
                                                                            or row["time_limit"]) - 1e-6)
        row.update(price_cols(pr, "rl"))
        return row

    def skipped_row(kind: str, family: str, seed: Any, method: str, status: str, **extra: Any) -> Dict[str, Any]:
        return {**orig_skip(kind, family, seed, method, status, **extra), **price_cols(pr, "rl")}

    def _ilp_done(ctx: Any, family: str, seed: int, method: str) -> bool:
        if not orig_done(ctx, family, seed, method):
            return False
        r = ctx.done.get(("ilp", family, str(seed), method))
        return not budget_cut(r, getattr(ctx.a, "ilp_time_limit", None), used_key="time_limit",
                              req_key="time_limit_requested")

    X7.schedule_row, X7.skipped_row, X7._ilp_done = schedule_row, skipped_row, _ilp_done
    X7._r6_wrapped = pr["label"]


#: relaxed-ILP reference of the rl stage: 300 s (round 5: 120 s).  Under (P 60, v 15) the full-size
#: r5_stress4h relaxed ILP takes about 100 s at Threads 3 (44-54 s at P 30 / v 36), so 120 s would leave
#: some test seeds gap-bounded; 300 s is the psweep limit of the same instances.  The X7 smoke caps it
#: at 30 s.
RL_ILP_TIME_LIMIT = 300.0


def run_rl(args: argparse.Namespace) -> None:
    out_dir = stage_dir("rl", args.smoke, args.out_root)
    X7 = _install_rl_loader(BASE)
    argv = ["--out", out_dir, "--no-written", "--wall-budget-min", str(args.budget_min),
            "--ilp-time-limit", str(RL_ILP_TIME_LIMIT)]
    if args.smoke:
        argv.append("--smoke")
    if args.dry_run:
        argv.append("--dry-run")
    if args.seeds is not None:
        argv += ["--test-seeds", ",".join(str(s) for s in args.seeds)]
    if not args.dry_run:
        C.ensure_dir(out_dir)
    X7.main(argv)
    if not args.dry_run:
        analyse_rl(out_dir, smoke=args.smoke)


def analyse_rl(out_dir: str, smoke: bool = False) -> str:
    X7 = _install_rl_loader(BASE)
    if not os.path.exists(os.path.join(out_dir, RECORDS)):
        return "rl: no records"
    X7.main(["--analyse", "--out", out_dir, "--ilp-time-limit", str(RL_ILP_TIME_LIMIT)] + (["--smoke"] if smoke else []))
    # lateness per (family, method) on the test seeds (penalty_calibration.md section 7 item 5)
    der = [r for r in X7.derived_rows(C.load_jsonl(os.path.join(out_dir, RECORDS)))
           if r.get("total") is not None and r.get("kind") != "train"]
    late_cols = ["n_late", "n_late_over_30min", "n_late_over_60min", "mean_lateness_min", "max_lateness_min",
                 "served_share"]
    late = (long_summary(pd.DataFrame(der), ["family", "method"], late_cols) if der else pd.DataFrame())
    late.to_csv(os.path.join(out_dir, "lateness.csv"), index=False)
    p = os.path.join(out_dir, "RESULTS.md")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as fh:
            txt = fh.read()
        txt = txt.replace("(round 5)", "(round 6: P 60, w 18, v 15 USD/h from b_i)", 1)
        if not late.empty:
            wide = late.pivot_table(index=["family", "method"], columns="metric", values="mean",
                                    aggfunc="first").reset_index()
            nn = late[late.metric == "n_late"].set_index(["family", "method"])["n"]
            wide = wide.set_index(["family", "method"])
            wide["n"] = nn
            wide = wide.reset_index()
            txt += "\n" + "\n".join(["## Lateness (seed means; lateness.csv has the t 95 % half-widths)", "",
                                      C.markdown_table(wide, [c for c in ["family", "method", "n"] + late_cols
                                                              if c in wide.columns], 2), ""]) + "\n"
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(txt)
    return p


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def analyse(stage: str, smoke: bool, root: Optional[str]) -> str:
    d = stage_dir(stage, smoke, root)
    if not os.path.isdir(d):
        return f"{stage}: no output directory {d}"
    if stage in GRID_STAGES:
        return analyse_grid(stage, d)
    if stage == "network":
        return analyse_network(d)
    if stage == "rolling":
        return analyse_rolling(d, smoke, root)
    if stage in ("levers", "fleet"):
        return analyse_stress(stage, d)
    return analyse_rl(d, smoke=smoke)


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", required=True,
                    help="one of " + ", ".join(STAGES) + ", 'all', or a comma-separated list")
    ap.add_argument("--smoke", action="store_true", help="tiny seeds / reduced instances / short limits")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--threads", type=int, default=THREADS)
    ap.add_argument("--budget-min", type=float, default=None, help="wall budget (default per stage)")
    ap.add_argument("--seeds", nargs="+", type=int, default=None, help="override the stage's seeds")
    ap.add_argument("--out-root", default=None, help=f"default {OUT_ROOT} ({OUT_ROOT}_smoke with --smoke)")
    args = ap.parse_args(argv)
    if args.threads > 3:
        raise SystemExit("R6 protocol: Threads <= 3")
    stages = list(STAGES) if args.stage == "all" else [x.strip() for x in args.stage.split(",") if x.strip()]
    bad = [x for x in stages if x not in STAGES]
    if bad or not stages:
        raise SystemExit(f"unknown stage(s) {bad}; known: {list(STAGES)} or 'all'")
    if args.analyse:
        for st in stages:
            try:
                print(analyse(st, args.smoke, args.out_root), flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"# analyse {st} failed: {type(exc).__name__}: {exc}", flush=True)
                traceback.print_exc()
        return
    for st in stages:
        a = argparse.Namespace(**vars(args))
        if a.budget_min is None:
            a.budget_min = SMOKE_BUDGET_MIN if a.smoke else WALL_BUDGET_MIN[st]
        if st in GRID_STAGES:
            run_grid(st, a)
        elif st == "network":
            run_network(a)
        elif st == "rolling":
            run_rolling(a)
        elif st in ("levers", "fleet"):
            run_stress(st, a)
        else:
            run_rl(a)


if __name__ == "__main__":
    main()
