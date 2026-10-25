"""Experiment X3 (round 5, plan item M7) -- rolling horizon: foresight vs coordination.

Question: the offline E2 headline ``(baseline - ILP) / baseline`` mixes two things, perfect
foresight (every order known at ``t = 0``) and coordination (one planner for riders and
batteries).  The rolling-horizon wrapper (``ebike_swap_sim.rolling.rolling_horizon``) re-solves
the unchanged E2 ILP on a moving window that sees orders only ``lambda`` minutes before
release, so per instance

    best_rule - offline  =  (rolling - offline)   +   (best_rule - rolling)
       headline             value of information      value of coordination online
                            (foresight)               (coordination without foresight)

Instances (byte-identical across methods; ``demand_md5`` asserted per instance and across
resumes):

* ``usd4h_ebaas`` -- ``experiments.common.make_instance('usd4h', seed, energy_calibration=
  'ebaas')`` (E2u x1 = 1.5 orders per bike-hour, 6 bikes / 36 orders / H 48, A1 physics L 24),
  seeds 0-9;
* ``r5_stress4h`` -- ``make_instance('r5_stress4h', seed)`` (6 bikes / 48 orders / H 48 / L 24,
  M5), seeds 0-4.

Library: ``common.pruning_for(inst, reachable=True)`` (reachable pruning, lossless), the same
library for every method of an instance (the relaxed copy re-binds it, see
:func:`rebind_library`; the arc library does not depend on ``rho`` / ``R_end``).

Policies per instance and end-target setting (``targets`` = ``relaxed``: rho = 0, R_end_j = 0,
``common.relax_end_targets`` / rolling ``final_targets='relaxed'``, the like-for-like headline
control; ``written``: the written targets, reported as the price of recovery):

* ``baseline_<rule>`` -- the rule policies r2 (R2.3 default), r5_range, r5_transfer (only when
  the instance has services) and r5 (``common.run_baseline_case``); target-independent (the
  policy keeps its written DEMAND_AWARE reserve on the relaxed copy, so one row serves both);
  ``best_rule`` = per-instance min over these rows (derived in the analysis);
* ``offline`` -- the aggregated E2 ILP (O1, ``aggregate=True``) with every order known at
  ``t = 0``; MIP start = ``common.feasible_mip_start`` of the r2 policy on the same copy;
* ``rolling`` -- ``rolling_horizon`` at ``lambda in {0, 10, 20}`` min, window ``W``, commit ``k``
  (defaults 24 / 6 slots, the setting of the rolling probe in DECISIONS "R5 implementation
  notes"; override with ``--W``/``--k`` or ``--wk label=W:k``), aggregated windows, window
  TimeLimit 60 s;
* ``forecast`` -- the same at ``lambda = 10`` with the M7 battery plan on ``--scenarios``
  bootstrap futures (``BootstrapForecast(pool='all')``).

Gurobi: Threads 3, Seed 0 (``common.ILP_PARAMS_R3``), TimeLimit 300 s offline / 60 s per
window, ``aggregate=True`` everywhere.  Every row records ``evaluate.cost`` (26)-(32) with the
M1 end-state adjustment (``C_end_adjust``, ``total_end_adjusted``), the A3 metric pack
(``r5_*`` columns, ``common.flatten_r5``), the check outcome and the demand hash.

Work order (wall budget, default 150 min, guards every run; a run that does not fit is recorded
as ``SKIPPED_BUDGET`` and re-run on resume):

* phase A (headline, relaxed targets): baselines, offline, rolling lambda 10 / 0 / 20,
  forecast lambda 10 -- instances interleaved usd s0, r5 s0, usd s1, r5 s1, ..., usd s5-s9;
* phase B (written targets, price of recovery): offline, rolling lambda 10;
* phase C (written targets): forecast lambda 10, rolling lambda 0 / 20 (expected to be cut by the
  budget at the default settings: phases A + B take about 135 min at Threads 3).

Outputs (``outputs/r5_x3_rolling/``): ``records.jsonl`` (append-only, resume by key
``(label, seed, policy, targets, lambda, W, k, scenarios)``), ``results.csv`` (refreshed after
each run), ``run_stdout.log`` (one line per run), and from the analysis ``per_instance.csv``,
``summary.csv`` (mean and 95 % t-CI over seeds) and ``RESULTS.md``.  The E2 model is not
changed.  Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r5_x3_rolling.py --dry-run           # plan + sizes, no solve, no write
    python3 experiments/r5_x3_rolling.py --smoke --out /tmp/x3_smoke   # one seed, short limits
    python3 experiments/r5_x3_rolling.py                     # the full run (resumable)
    python3 experiments/r5_x3_rolling.py --analyse
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import time
import traceback
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import Instance, build_arcs  # noqa: E402
from ebike_swap_sim.arcs import ArcLibrary  # noqa: E402
from ebike_swap_sim.evaluate import check as eval_check  # noqa: E402
from ebike_swap_sim.evaluate import metrics as eval_metrics  # noqa: E402
from ebike_swap_sim.rolling import (  # noqa: E402
    BootstrapForecast,
    RollingHorizonError,
    _supports_aggregate,
    rolling_horizon,
)
from experiments import common as C  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r5_x3_rolling")
RECORDS = "records.jsonl"

#: Instance families of X3: label -> (common family, make_instance overrides, default seeds).
FAMILY_SPECS: Dict[str, Dict[str, Any]] = {
    "usd4h_ebaas": {"family": "usd4h", "overrides": {"energy_calibration": "ebaas"},
                    "seeds": list(range(10))},
    "r5_stress4h": {"family": "r5_stress4h", "overrides": {}, "seeds": list(range(5))},
}
#: Rule policies (``baseline.BASELINE_VARIANTS`` names) -> ``common.BASELINE_VARIANTS`` keys.
RULES: Dict[str, str] = {"r2": "baseline", "r5_range": "baseline_r5_range",
                         "r5_transfer": "baseline_r5_transfer", "r5": "baseline_r5"}
#: Rules that only make sense when the instance has services (transfers).
RULES_NEED_SERVICES = ("r5_transfer",)
TARGETS = ("relaxed", "written")
LAMBDAS = (0.0, 10.0, 20.0)
FORECAST_LAMBDA = 10.0
DEFAULT_W, DEFAULT_K = 24, 6
TIME_LIMIT_OFFLINE = 300.0
TIME_LIMIT_WINDOW = 60.0
WALL_BUDGET_MIN = 150.0
#: Forecast scenarios per epoch.  One scenario (the plan is that sample's commit-period
#: charging / transfers) keeps the 150 min budget: the scenario solves dominate the forecast run
#: (r5_stress4h seed 0: 254 s with one scenario against 85 s for plain rolling); ``--scenarios 2``
#: is the rolling_horizon.py default and costs about +65 s (usd4h_ebaas) / +165 s (r5_stress4h)
#: per run.
N_SCENARIOS = 1
#: A-priori run-time estimates (s, Threads 3, measured on seed 0 in the X3 smoke / probe,
#: 2026-10-17: usd4h_ebaas offline 44 s OPTIMAL, rolling lambda 10 53-58 s, forecast (1 scenario)
#: 121-123 s; r5_stress4h offline 61 s OPTIMAL, rolling 85 s, forecast (1 scenario) 254 s), used by
#: the budget guard until a run of the same (label, policy) has been observed.  Forecast:
#: ``rolling + n_scenarios * scenario`` below.
EST_RUNTIME: Dict[Tuple[str, str], float] = {
    ("usd4h_ebaas", "offline"): 50.0, ("usd4h_ebaas", "rolling"): 60.0,
    ("r5_stress4h", "offline"): 70.0, ("r5_stress4h", "rolling"): 95.0,
}
EST_SCENARIO_S: Dict[str, float] = {"usd4h_ebaas": 70.0, "r5_stress4h": 170.0}
EST_BASELINES_S = 15.0       # library build + all rule policies of one instance
EST_SETUP_S = 10.0           # instance + library build per (phase, instance) group


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def parse_seeds(text: str) -> List[int]:
    """``'0-4'`` -> ``[0..4]``; ``'0,3,7'`` -> ``[0, 3, 7]``; ``''`` -> ``[]``."""
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


def parse_floats(text: str) -> List[float]:
    return [float(p) for p in str(text).split(",") if p.strip()]


def parse_wk(text: str) -> Dict[str, Tuple[int, int]]:
    """``'usd4h_ebaas=24:6,r5_stress4h=18:6'`` -> ``{label: (W, k)}``."""
    out: Dict[str, Tuple[int, int]] = {}
    for part in str(text or "").split(","):
        part = part.strip()
        if not part:
            continue
        lab, wk = part.split("=", 1)
        w, k = wk.split(":", 1)
        out[lab.strip()] = (int(w), int(k))
    return out


def lam_key(lam: Any) -> Any:
    if lam is None:
        return "-"
    lam = float(lam)
    return "inf" if math.isinf(lam) else lam


def rec_key(rec: Dict[str, Any]) -> Tuple:
    """Resume key of one run."""
    return (rec.get("label"), int(rec.get("seed")), rec.get("policy"), rec.get("targets"),
            lam_key(rec.get("lookahead_min")), rec.get("W"), rec.get("k"),
            rec.get("n_scenarios") or 0)


def item_key(item: Dict[str, Any]) -> Tuple:
    return rec_key(item)


def mean_ci(values: Iterable[Any], level: float = 0.95) -> Tuple[float, float, int]:
    """Mean and half-width of the Student-t CI over seeds (``n - 1`` dof); NaN when n < 2."""
    v = np.asarray([float(x) for x in values if x is not None and not
                    (isinstance(x, float) and math.isnan(x))], dtype=float)
    if v.size == 0:
        return float("nan"), float("nan"), 0
    m = float(v.mean())
    if v.size < 2:
        return m, float("nan"), int(v.size)
    try:
        from scipy import stats
        tq = float(stats.t.ppf(0.5 + level / 2.0, v.size - 1))
    except ImportError:  # pragma: no cover
        tq = 1.96
    return m, tq * float(v.std(ddof=1)) / math.sqrt(v.size), int(v.size)


def rebind_library(lib: ArcLibrary, inst: Instance) -> ArcLibrary:
    """Shallow copy of ``lib`` bound to ``inst`` (an end-target copy of ``lib.inst``).

    The arc library (E2 (1)-(4), (9)) does not depend on ``rho`` or ``R_end_j``
    (``common.relax_end_targets`` docstring), and ``ilp`` / ``baseline`` / ``aggregate`` only
    insist on ``lib.inst == inst``; rebinding avoids a second 2-3 M arc build.  Everything the
    library is built from is asserted equal first."""
    a, b = lib.inst, inst
    same = (a.disc == b.disc and a.nodes == b.nodes and a.routes == b.routes and a.bikes == b.bikes
            and a.orders == b.orders and a.services == b.services and a.options == b.options
            and a.q_res == b.q_res and a.H == b.H and a.L == b.L
            and [(f.id, f.node, f.swap, f.charge, f.y, f.B, f.C, f.sigma) for f in a.facilities]
            == [(f.id, f.node, f.swap, f.charge, f.y, f.B, f.C, f.sigma) for f in b.facilities])
    if not same:
        raise ValueError("rebind_library: the instances differ beyond the end targets")
    out = copy.copy(lib)
    out.inst = inst
    return out


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------
def instance_order(seeds: Dict[str, List[int]]) -> List[Tuple[str, int]]:
    """Interleave the families seed by seed (usd s0, r5 s0, usd s1, ...) so that a budget
    stop leaves both families covered."""
    labels = list(seeds)
    out: List[Tuple[str, int]] = []
    n = max((len(v) for v in seeds.values()), default=0)
    for i in range(n):
        for lab in labels:
            if i < len(seeds[lab]):
                out.append((lab, seeds[lab][i]))
    return out


def build_plan(args: argparse.Namespace, seeds: Dict[str, List[int]]) -> List[Dict[str, Any]]:
    """Ordered work items ``{phase, label, seed, policy, targets, lookahead_min, W, k, n_scenarios}``
    (baseline items carry ``rule``)."""
    order = instance_order(seeds)
    lams = list(args.lambdas)
    lam_first = [FORECAST_LAMBDA] + [x for x in lams if x != FORECAST_LAMBDA] if FORECAST_LAMBDA in lams else lams
    items: List[Dict[str, Any]] = []

    def wk(label: str) -> Tuple[int, int]:
        return args.wk.get(label, (args.W, args.k))

    def add(phase: str, label: str, seed: int, policy: str, targets: str,
            lam: Optional[float] = None, rule: Optional[str] = None) -> None:
        W, k = wk(label) if policy in ("rolling", "forecast") else (None, None)
        items.append({"phase": phase, "label": label, "seed": seed, "policy": policy,
                      "targets": targets, "lookahead_min": lam, "W": W, "k": k, "rule": rule,
                      "n_scenarios": args.scenarios if policy == "forecast" else 0})

    phases = set(args.phases)
    if "A" in phases:
        for label, seed in order:
            for rule in RULES:
                add("A", label, seed, f"baseline_{rule}", "any", rule=rule)
            add("A", label, seed, "offline", "relaxed")
            for lam in lam_first:
                add("A", label, seed, "rolling", "relaxed", lam)
            if args.forecast_lambda is not None:
                add("A", label, seed, "forecast", "relaxed", args.forecast_lambda)
    if "B" in phases:
        for label, seed in order:
            add("B", label, seed, "offline", "written")
            if FORECAST_LAMBDA in lams:
                add("B", label, seed, "rolling", "written", FORECAST_LAMBDA)
    if "C" in phases:
        for label, seed in order:
            if args.forecast_lambda is not None:
                add("C", label, seed, "forecast", "written", args.forecast_lambda)
            for lam in lams:
                if lam != FORECAST_LAMBDA or "B" not in phases:
                    add("C", label, seed, "rolling", "written", lam)
    return items


def group_items(items: List[Dict[str, Any]]) -> List[Tuple[Tuple[str, str, int], List[Dict[str, Any]]]]:
    """Consecutive items of the same (phase, label, seed) share one instance + library build."""
    out: List[Tuple[Tuple[str, str, int], List[Dict[str, Any]]]] = []
    for it in items:
        g = (it["phase"], it["label"], it["seed"])
        if out and out[-1][0] == g:
            out[-1][1].append(it)
        else:
            out.append((g, [it]))
    return out


def estimate(item: Dict[str, Any], observed: Dict[Tuple[str, str, int], List[float]]) -> float:
    pol = item["policy"]
    if pol.startswith("baseline_"):
        return EST_BASELINES_S / len(RULES)
    obs = observed.get((item["label"], pol, item.get("n_scenarios") or 0))
    if obs:
        return float(np.mean(obs))
    if pol == "forecast":
        return (EST_RUNTIME.get((item["label"], "rolling"), 120.0)
                + max(1, int(item.get("n_scenarios") or 1)) * EST_SCENARIO_S.get(item["label"], 200.0))
    return EST_RUNTIME.get((item["label"], pol), 120.0)


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Runner:
    """Executes work items, appends one record per run, refreshes ``results.csv``."""

    def __init__(self, args: argparse.Namespace, out_dir: str, budget: C.WallBudget) -> None:
        self.args = args
        self.out_dir = C.ensure_dir(out_dir)
        self.path = os.path.join(out_dir, RECORDS)
        self.log_path = os.path.join(out_dir, "run_stdout.log")
        self.budget = budget
        self.records = C.load_jsonl(self.path)
        self.done: Dict[Tuple, Dict[str, Any]] = {}
        self.md5: Dict[Tuple[str, int], str] = {}
        self.observed: Dict[Tuple[str, str, int], List[float]] = {}
        for r in self.records:
            if r.get("status") not in (C.SKIPPED_BUDGET, "ERROR"):
                self.done[rec_key(r)] = r
                if r.get("runtime") and r.get("policy") in ("offline", "rolling", "forecast"):
                    self.observed.setdefault((r["label"], r["policy"], r.get("n_scenarios") or 0), []).append(
                        float(r["runtime"]))
            if r.get("demand_md5"):
                self.md5.setdefault((r["label"], int(r["seed"])), r["demand_md5"])
        self.n_runs = 0
        self.params = dict(C.ILP_PARAMS_R3)            # Seed 0
        self.agg = _supports_aggregate()

    # ------------------------------------------------------------- output
    def emit(self, rec: Dict[str, Any]) -> None:
        rec = {k: v for k, v in rec.items() if not k.startswith("_")}
        C.append_jsonl(self.path, rec)
        self.records.append(rec)
        if rec.get("status") not in (C.SKIPPED_BUDGET, "ERROR"):
            self.done[rec_key(rec)] = rec
            if rec.get("runtime") and rec.get("policy") in ("offline", "rolling", "forecast"):
                self.observed.setdefault((rec["label"], rec["policy"], rec.get("n_scenarios") or 0), []).append(
                    float(rec["runtime"]))
        self.n_runs += 1
        try:
            C.write_csv(self.records, os.path.join(self.out_dir, "results.csv"))
        except Exception as exc:  # noqa: BLE001 -- records are the deliverable
            print(f"# results.csv refresh failed: {exc}", flush=True)
        lam = rec.get("lookahead_min")
        line = (f"[{rec.get('phase')}] {rec['label']} s{rec['seed']} {rec['policy']:<20s} "
                f"tgt={rec.get('targets'):<7s} lam={'-' if lam is None else fmt_lam(lam)} "
                f"status={rec.get('status')} total={C.fmt(rec.get('total'))} "
                f"eadj={C.fmt(rec.get('total_end_adjusted'))} gap={C.fmt(rec.get('gap'), 4)} "
                f"hard_ok={rec.get('hard_ok')} rt={C.fmt(rec.get('runtime'), 1)}s "
                f"wall={self.budget.elapsed() / 60:.1f}min")
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def skip(self, item: Dict[str, Any], reason: str, base: Dict[str, Any]) -> None:
        self.emit({**base, **item, "status": C.SKIPPED_BUDGET, "skip_reason": reason})

    # ------------------------------------------------------------ instance
    def build(self, label: str, seed: int) -> Tuple[Instance, ArcLibrary, Dict[str, Any], Dict[str, Any]]:
        spec = FAMILY_SPECS[label]
        t0 = time.perf_counter()
        inst = C.make_instance(spec["family"], seed=seed, **spec["overrides"])
        pr = C.pruning_for(inst, reachable=True)
        lib = build_arcs(inst, strict=False, **pr)
        md5 = C.demand_md5(inst)
        prev = self.md5.get((label, seed))
        if prev is not None and prev != md5:
            raise RuntimeError(f"demand md5 changed for {label} seed {seed}: {prev} != {md5}")
        self.md5[(label, seed)] = md5
        base = {"label": label, "family": spec["family"], "overrides": dict(spec["overrides"]),
                "seed": seed, "H": inst.H, "L": inst.L, "n_bikes": len(inst.bikes),
                "n_orders": len(inst.orders), "n_services": len(inst.services),
                "n_arcs_day": len(lib), "n_unservable": len(C.unservable_orders(inst, lib)),
                "demand_md5": md5, "threads": self.args.threads, "gurobi_seed": self.params.get("Seed"),
                "build_time": time.perf_counter() - t0}
        return inst, lib, pr, base

    def target_inst(self, inst: Instance, lib: ArcLibrary, targets: str
                    ) -> Tuple[Instance, ArcLibrary]:
        if targets == "written":
            return inst, lib
        rel = C.relax_end_targets(inst)
        if C.demand_md5(rel) != C.demand_md5(inst):
            raise RuntimeError("relaxed copy changed the demand")
        return rel, rebind_library(lib, rel)

    # ------------------------------------------------------------- policies
    def run_baseline(self, item: Dict[str, Any], inst: Instance, lib: ArcLibrary,
                     base: Dict[str, Any]) -> None:
        rule = item["rule"]
        rec = {**base, **{k: v for k, v in item.items()}}
        if rule in RULES_NEED_SERVICES and not inst.services:
            rec.update(status="NOT_APPLICABLE", total=None,
                       note="no services in the instance: the transfer rule equals r2")
            self.emit(rec)
            return
        t0 = time.perf_counter()
        b = C.run_baseline_case(inst, lib, C.baseline_variant_params(RULES[rule], inst), label=rule)
        met = b["metrics"]
        rec.update(status="POLICY", runtime=time.perf_counter() - t0,
                   hard_ok=bool(b["ok_modulo_report_only"]), families=b["families"],
                   identity_24_ok=b["identity_24_ok"], served_share=met.get("served_share"),
                   n_unserved=met.get("n_unserved"), stockout_slots=met.get("stockout_slots"),
                   policy_reserve_source=b.get("policy_reserve_source"),
                   **C.flatten_cost(b["cost"]), **C.flatten_r5(met))
        rec.update({f"pruning_{k}": v for k, v in b["pruning_flags"].items()})
        self.emit(rec)

    def run_offline(self, item: Dict[str, Any], inst: Instance, lib: ArcLibrary,
                    base: Dict[str, Any]) -> None:
        from ebike_swap_sim import ilp
        tl = self.budget.solve_limit(self.args.time_limit_offline)
        if tl is None:
            self.skip(item, "wall budget", base)
            return
        tinst, tlib = self.target_inst(inst, lib, item["targets"])
        rec = {**base, **item}
        t0 = time.perf_counter()
        b = C.run_baseline_case(tinst, tlib, None, label="r2_start")
        start, start_variant = C.feasible_mip_start(tinst, tlib, b)
        agg_kw = {"aggregate": True} if self.agg else {}
        sched, st = ilp.solve(tinst, tlib, mip_start=start, threads=self.args.threads, time_limit=tl,
                              params=self.params, **agg_kw)
        rt = time.perf_counter() - t0
        rec.update(status=st.get("status"), runtime=rt, solve_runtime=st.get("runtime"),
                   time_limit=tl, gap=st.get("gap"), bound=st.get("bound"), obj=st.get("obj"),
                   aggregate=bool(agg_kw), n_vars=st.get("n_vars"), n_agg_arcs=st.get("n_agg_arcs"),
                   mip_start_variant=start_variant,
                   mip_start_accepted=(st.get("mip_start") or {}).get("accepted"),
                   start_total=b["cost"]["total"], hard_ok=sched is not None)
        if sched is not None:
            rep = eval_check(tinst, tlib, sched)
            met = eval_metrics(tinst, tlib, sched)
            cst = st.get("cost") or {}
            rec.update(served_share=met.get("served_share"),
                       n_unserved=met.get("n_unserved"), stockout_slots=met.get("stockout_slots"),
                       families=C.family_counts(rep), check_ok=bool(rep["ok"]),
                       **C.flatten_cost(cst), **C.flatten_r5(met))
        else:
            rec.update(total=None)
        self.emit(rec)

    def run_rolling(self, item: Dict[str, Any], inst: Instance, lib: ArcLibrary, pr: Dict[str, Any],
                    base: Dict[str, Any]) -> None:
        est = estimate(item, self.observed)
        if self.budget.remaining() - self.budget.margin < est:
            self.skip(item, f"wall budget (estimate {est:.0f} s)", base)
            return
        use_fc = item["policy"] == "forecast"
        rec = {**base, **item, "pool": self.args.pool if use_fc else None}
        fc = BootstrapForecast(inst, pool=self.args.pool) if use_fc else None
        t0 = time.perf_counter()
        res = rolling_horizon(inst, W=item["W"], k=item["k"], lookahead_min=item["lookahead_min"],
                              lib=lib, arc_options=pr, final_targets=item["targets"],
                              forecast=fc, n_scenarios=item["n_scenarios"] if use_fc else 1,
                              forecast_seed=int(item["seed"]), aggregate=True,
                              threads=self.args.threads, time_limit=self.args.time_limit_window,
                              params=self.params)
        rt = time.perf_counter() - t0
        summ = res.summary()
        met = eval_metrics(res.inst, res.lib, res.schedule)
        rec.update({k: v for k, v in summ.items() if not k.startswith("param_")})
        rec.update(status="ROLLING", runtime=rt, families=summ.get("violations"),
                   served_share=met.get("served_share"), stockout_slots=met.get("stockout_slots"),
                   forecast_source=getattr(fc, "source", None) if fc else None,
                   n_window_aggregate=sum(1 for w in res.windows if w.get("aggregate")),
                   windows=[{kk: w.get(kk) for kk in ("t0", "W", "status", "gap", "runtime", "n_known",
                                                      "n_forecast", "n_busy", "plan_fix", "fallback",
                                                      "aggregate")} for w in res.windows],
                   notes=res.notes, **C.flatten_cost(res.cost), **C.flatten_r5(met))
        self.emit(rec)

    # ---------------------------------------------------------------- loop
    def run_items(self, items: List[Dict[str, Any]]) -> None:
        for (phase, label, seed), group in group_items(items):
            todo = [it for it in group if item_key(it) not in self.done]
            if not todo:
                continue
            need_s = EST_SETUP_S + min(estimate(it, self.observed) for it in todo)
            if self.budget.remaining() - self.budget.margin < need_s:
                for it in todo:
                    self.skip(it, "wall budget", {"label": label, "seed": seed})
                continue
            try:
                inst, lib, pr, base = self.build(label, seed)
            except Exception as exc:  # noqa: BLE001
                for it in todo:
                    self.emit({"label": label, "seed": seed, **it, "status": "ERROR",
                               "error": f"build: {type(exc).__name__}: {exc}"})
                continue
            for it in todo:
                try:
                    if it["policy"].startswith("baseline_"):
                        self.run_baseline(it, inst, lib, base)
                    elif it["policy"] == "offline":
                        self.run_offline(it, inst, lib, base)
                    else:
                        self.run_rolling(it, inst, lib, pr, base)
                except (RollingHorizonError, Exception) as exc:  # noqa: BLE001 -- keep the run going
                    self.emit({**base, **it, "status": "ERROR",
                               "error": f"{type(exc).__name__}: {exc}",
                               "traceback": traceback.format_exc()[-2000:]})
            del inst, lib


def fmt_lam(lam: Any) -> str:
    try:
        return f"{float(lam):g}"
    except (TypeError, ValueError):
        return str(lam)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
BASES = ("total", "total_end_adjusted")


def last_per_key(recs: List[Dict[str, Any]]) -> Dict[Tuple, Dict[str, Any]]:
    out: Dict[Tuple, Dict[str, Any]] = {}
    for r in recs:
        if r.get("status") in (C.SKIPPED_BUDGET, "ERROR", "NOT_APPLICABLE"):
            continue
        if r.get("total") is None:
            continue
        out[rec_key(r)] = r
    return out


def per_instance(recs: List[Dict[str, Any]]) -> pd.DataFrame:
    """One row per (label, seed, targets, basis): offline, rolling per lambda, forecast, r2, r5,
    best_rule, and the decomposition headline = foresight + coordination."""
    last = last_per_key(recs)
    by_inst: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for r in last.values():
        by_inst.setdefault((r["label"], int(r["seed"])), []).append(r)
    rows: List[Dict[str, Any]] = []
    for (label, seed), rr in sorted(by_inst.items()):
        md5s = {r.get("demand_md5") for r in rr if r.get("demand_md5")}
        if len(md5s) > 1:
            raise RuntimeError(f"{label} seed {seed}: methods ran on different demand {md5s}")
        rules = {r["rule"]: r for r in rr if str(r.get("policy", "")).startswith("baseline_")}
        for targets in TARGETS:
            off = next((r for r in rr if r["policy"] == "offline" and r.get("targets") == targets), None)
            rol = {float(r["lookahead_min"]): r for r in rr
                   if r["policy"] == "rolling" and r.get("targets") == targets}
            fcs = {float(r["lookahead_min"]): r for r in rr
                   if r["policy"] == "forecast" and r.get("targets") == targets}
            if off is None and not rol and not fcs:
                continue
            for basis in BASES:
                row: Dict[str, Any] = {"label": label, "seed": seed, "targets": targets, "basis": basis,
                                       "demand_md5": next(iter(md5s), None)}
                vals = {rn: r.get(basis) for rn, r in rules.items() if r.get(basis) is not None}
                for rn, v in vals.items():
                    row[f"rule_{rn}"] = v
                best = min(vals.items(), key=lambda kv: kv[1]) if vals else (None, None)
                row["best_rule_name"], row["best_rule"] = best
                r2 = vals.get("r2")
                row["r2"] = r2
                o = off.get(basis) if off else None
                row["offline"] = o
                row["offline_status"] = off.get("status") if off else None
                row["offline_gap"] = off.get("gap") if off else None
                row["offline_bound"] = off.get("bound") if off else None
                if o is not None and row["best_rule"] is not None:
                    row["headline_gap_pct"] = 100.0 * (row["best_rule"] - o) / row["best_rule"]
                if o is not None and r2 is not None:
                    row["headline_gap_r2_pct"] = 100.0 * (r2 - o) / r2
                for kind, dct in (("rolling", rol), ("forecast", fcs)):
                    for lam, r in sorted(dct.items()):
                        tag = f"{kind}{lam:g}"
                        v = r.get(basis)
                        row[tag] = v
                        row[f"{tag}_hard_ok"] = r.get("hard_ok")
                        if v is None:
                            continue
                        if o is not None:
                            row[f"voi_{tag}"] = v - o
                            row[f"voi_pct_{tag}"] = 100.0 * (v - o) / abs(o) if abs(o) > 1e-12 else None
                        if row["best_rule"] is not None:
                            row[f"coord_{tag}"] = row["best_rule"] - v
                            row[f"coord_pct_{tag}"] = 100.0 * (row["best_rule"] - v) / row["best_rule"]
                            if o is not None and abs(row["best_rule"] - o) > 1e-9:
                                row[f"foresight_share_{tag}"] = (v - o) / (row["best_rule"] - o)
                        if r2 is not None:
                            row[f"coord_r2_{tag}"] = r2 - v
                            row[f"coord_r2_pct_{tag}"] = 100.0 * (r2 - v) / r2
                if f"rolling{FORECAST_LAMBDA:g}" in row and f"forecast{FORECAST_LAMBDA:g}" in row:
                    a, b = row[f"rolling{FORECAST_LAMBDA:g}"], row[f"forecast{FORECAST_LAMBDA:g}"]
                    if a is not None and b is not None:
                        row["battery_plan_value"] = a - b
                rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # price of recovery: written - relaxed per policy column (same seed, same basis)
    pol_cols = [c for c in df.columns if c == "offline" or c.startswith("rolling") or c.startswith("forecast")]
    pol_cols = [c for c in pol_cols if not c.endswith("_hard_ok")]
    piv = df.set_index(["label", "seed", "basis", "targets"])
    extra = []
    for (label, seed, basis), _ in df.groupby(["label", "seed", "basis"]):
        try:
            w = piv.loc[(label, seed, basis, "written")]
            r = piv.loc[(label, seed, basis, "relaxed")]
        except KeyError:
            continue
        row = {"label": label, "seed": seed, "basis": basis, "targets": "written-relaxed"}
        for c in pol_cols:
            if pd.notna(w.get(c)) and pd.notna(r.get(c)):
                row[f"recovery_{c}"] = float(w[c]) - float(r[c])
        extra.append(row)
    if extra:
        df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """Mean and 95 % t-CI over seeds of every numeric derived column per (label, targets, basis)."""
    if df.empty:
        return df
    skip = {"seed"}
    out = []
    for (label, targets, basis), g in df.groupby(["label", "targets", "basis"]):
        for c in df.columns:
            if c in skip or c in ("label", "targets", "basis") or df[c].dtype == object:
                continue
            vals = [v for v in g[c].tolist() if v is not None and not (isinstance(v, float) and math.isnan(v))]
            if not vals:
                continue
            m, h, n = mean_ci(vals)
            out.append({"label": label, "targets": targets, "basis": basis, "quantity": c,
                        "mean": m, "ci95": h, "n": n})
    return pd.DataFrame(out)


def analyse(out_dir: str) -> str:
    recs = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not recs:
        return "no records"
    C.write_csv(recs, os.path.join(out_dir, "results.csv"))
    pi = per_instance(recs)
    if pi.empty:
        return "no complete instance rows yet"
    pi.to_csv(os.path.join(out_dir, "per_instance.csv"), index=False)
    sm = summarise(pi)
    sm.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    last = last_per_key(recs)
    n_err = len({rec_key(r) for r in recs if r.get("status") == "ERROR"} - set(last))
    n_skip = len({rec_key(r) for r in recs if r.get("status") == C.SKIPPED_BUDGET} - set(last))
    bad = [k for k, r in last.items() if r.get("policy") in ("rolling", "forecast") and not r.get("hard_ok")]
    off_nonopt = [k for k, r in last.items() if r.get("policy") == "offline" and r.get("status") != "OPTIMAL"]

    def cell(sub: pd.DataFrame, q: str) -> str:
        s = sub[sub["quantity"] == q]
        if s.empty:
            return "-"
        m, h, n = float(s["mean"].iloc[0]), float(s["ci95"].iloc[0]), int(s["n"].iloc[0])
        return f"{m:.2f} +/- {h:.2f} (n={n})" if not math.isnan(h) else f"{m:.2f} (n={n})"

    lines = ["# X3 / M7 rolling horizon: foresight vs coordination", "",
             "headline = best_rule - offline = (rolling - offline) [value of information] + "
             "(best_rule - rolling) [value of coordination online]; best_rule = per-instance min over "
             "r2, r5_range, r5_transfer (with services) and r5. Mean +/- 95 % t-CI half-width over seeds, USD "
             "per window (percentages: gap = 100 (baseline - ILP) / baseline). Headline = relaxed targets "
             "(rho = 0, R_end = 0) on the end-adjusted basis; written = price of recovery.", "",
             f"Rows: {len(recs)} records, {n_skip} keys still SKIPPED_BUDGET, {n_err} keys with only ERROR rows; rolling/forecast rows failing "
             f"a hard family or (24): {len(bad)}; offline rows not OPTIMAL: {len(off_nonopt)} "
             "(their voi is a difference of upper bounds; see offline_gap / offline_bound in per_instance.csv).", ""]
    qs = ["best_rule", "r2", "offline", "headline_gap_pct", "headline_gap_r2_pct"]
    lam_tags = sorted({c.split("voi_")[1] for c in pi.columns if c.startswith("voi_") and not c.startswith("voi_pct")})
    for t in lam_tags:
        qs += [t, f"voi_{t}", f"voi_pct_{t}", f"coord_{t}", f"coord_pct_{t}", f"foresight_share_{t}",
               f"coord_r2_{t}"]
    qs += ["battery_plan_value"]
    for basis in ("total_end_adjusted", "total"):
        for targets in TARGETS:
            sub = sm[(sm["targets"] == targets) & (sm["basis"] == basis)]
            if sub.empty:
                continue
            labels = sorted(sub["label"].unique())
            lines += [f"## targets = {targets}, basis = {basis}", "",
                      "| quantity | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
            for q in qs:
                if not (sub["quantity"] == q).any():
                    continue
                lines.append(f"| {q} | " + " | ".join(cell(sub[sub['label'] == lab], q) for lab in labels) + " |")
            lines.append("")
    rec_sub = sm[sm["targets"] == "written-relaxed"]
    if not rec_sub.empty:
        lines += ["## price of recovery (written - relaxed, same policy and seed)", ""]
        labels = sorted(rec_sub["label"].unique())
        for basis in ("total_end_adjusted", "total"):
            sub = rec_sub[rec_sub["basis"] == basis]
            lines += [f"basis = {basis}", "", "| quantity | " + " | ".join(labels) + " |",
                      "|---|" + "---|" * len(labels)]
            for q in sorted(sub["quantity"].unique()):
                lines.append(f"| {q} | " + " | ".join(cell(sub[sub['label'] == lab], q) for lab in labels) + " |")
            lines.append("")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(out_dir, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def dry_run(args: argparse.Namespace, seeds: Dict[str, List[int]], items: List[Dict[str, Any]],
            out_dir: str) -> Dict[str, Any]:
    existing = {rec_key(r) for r in C.load_jsonl(os.path.join(out_dir, RECORDS))
                if r.get("status") not in (C.SKIPPED_BUDGET, "ERROR")}
    print(f"# X3 plan: out={out_dir} Threads={args.threads} Seed=0 aggregate=True "
          f"TL offline={args.time_limit_offline:g}s window={args.time_limit_window:g}s "
          f"budget={args.wall_budget_min:g}min W/k default={args.W}/{args.k} overrides={args.wk}")
    for label, ss in seeds.items():
        for s in ss:
            spec = FAMILY_SPECS[label]
            inst = C.make_instance(spec["family"], seed=s, **spec["overrides"])
            W, k = args.wk.get(label, (args.W, args.k))
            print(f"  {label} seed {s}: H={inst.H} L={inst.L} |K|={len(inst.bikes)} |I|={len(inst.orders)} "
                  f"|E|={len(inst.services)} epochs={len(range(0, inst.H, k))} W={W} k={k} "
                  f"md5={C.demand_md5(inst)}")
    est_total = 0.0
    per_phase: Dict[str, Dict[str, Any]] = {}
    seen_groups = set()
    for it in items:
        todo = item_key(it) not in existing
        ph = per_phase.setdefault(it["phase"], {"items": 0, "todo": 0, "est_s": 0.0})
        ph["items"] += 1
        if todo:
            g = (it["phase"], it["label"], it["seed"])
            e = estimate(it, {}) + (EST_SETUP_S if g not in seen_groups else 0.0)
            seen_groups.add(g)
            ph["todo"] += 1
            ph["est_s"] += e
            est_total += e
    for it in items[: min(len(items), 40)]:
        print("   ", {k: v for k, v in it.items() if v is not None})
    if len(items) > 40:
        print(f"    ... {len(items) - 40} more items")
    summ = {"n_items": len(items), "n_todo": sum(p["todo"] for p in per_phase.values()),
            "per_phase": {k: {**v, "est_min": round(v["est_s"] / 60.0, 1)} for k, v in per_phase.items()},
            "expected_wall_min": round(est_total / 60.0, 1), "wall_budget_min": args.wall_budget_min}
    print(json.dumps(summ, indent=1))
    return summ


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=None, help=f"default {OUT_DIR}")
    ap.add_argument("--labels", default=",".join(FAMILY_SPECS), help="subset of " + ",".join(FAMILY_SPECS))
    ap.add_argument("--seeds-usd", default="0-9", help="seeds of usd4h_ebaas")
    ap.add_argument("--seeds-r5", default="0-4", help="seeds of r5_stress4h")
    ap.add_argument("--lambdas", type=parse_floats, default=list(LAMBDAS), help="minutes, e.g. 0,10,20")
    ap.add_argument("--forecast-lambda", type=float, default=FORECAST_LAMBDA)
    ap.add_argument("--no-forecast", action="store_true")
    ap.add_argument("--scenarios", type=int, default=N_SCENARIOS)
    ap.add_argument("--pool", choices=("all", "released"), default="all")
    ap.add_argument("--W", type=int, default=DEFAULT_W, help="window length (slots)")
    ap.add_argument("--k", type=int, default=DEFAULT_K, help="commit step (slots)")
    ap.add_argument("--wk", type=parse_wk, default={}, help="per-label W:k, e.g. usd4h_ebaas=24:6,r5_stress4h=24:6")
    ap.add_argument("--phases", default="A,B,C")
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--time-limit-offline", type=float, default=TIME_LIMIT_OFFLINE)
    ap.add_argument("--time-limit-window", type=float, default=TIME_LIMIT_WINDOW)
    ap.add_argument("--wall-budget-min", type=float, default=WALL_BUDGET_MIN)
    ap.add_argument("--dry-run", action="store_true", help="print the plan and sizes; no solve, no write")
    ap.add_argument("--smoke", action="store_true",
                    help="usd4h_ebaas seed 0, lambda 10, 1 scenario, TL offline 60 s / window 20 s, all phases")
    ap.add_argument("--analyse", action="store_true")
    args = ap.parse_args(argv)
    args.threads = min(int(args.threads), 3)
    args.phases = [p.strip().upper() for p in args.phases.split(",") if p.strip()]
    if args.no_forecast:
        args.forecast_lambda = None
    if args.smoke:
        args.labels = "usd4h_ebaas"
        args.seeds_usd = "0"
        args.lambdas = [10.0]
        args.scenarios = 1
        args.time_limit_offline = min(args.time_limit_offline, 60.0)
        args.time_limit_window = min(args.time_limit_window, 20.0)
        args.wall_budget_min = min(args.wall_budget_min, 30.0)
    out_dir = args.out or (OUT_DIR + "_smoke" if args.smoke else OUT_DIR)
    if args.analyse:
        print(analyse(out_dir))
        return 0
    labels = [x.strip() for x in args.labels.split(",") if x.strip()]
    for lab in labels:
        if lab not in FAMILY_SPECS:
            raise SystemExit(f"unknown label {lab!r}; known {sorted(FAMILY_SPECS)}")
    seeds = {lab: parse_seeds(args.seeds_usd if lab == "usd4h_ebaas" else args.seeds_r5) for lab in labels}
    items = build_plan(args, seeds)
    if args.dry_run:
        dry_run(args, seeds, items, out_dir)
        return 0
    budget = C.WallBudget(args.wall_budget_min * 60.0, margin_s=60.0, min_solve_s=30.0)
    runner = Runner(args, out_dir, budget)
    print(f"# X3 start: {len(items)} items, {sum(1 for it in items if item_key(it) not in runner.done)} to do, "
          f"budget {args.wall_budget_min:g} min -> {out_dir}", flush=True)
    runner.run_items(items)
    wall = budget.elapsed()
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": wall, "n_runs": runner.n_runs, "smoke": bool(args.smoke),
                             "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"# X3 finished: {runner.n_runs} rows in {wall / 60:.1f} min", flush=True)
    try:
        print(analyse(out_dir))
    except Exception as exc:  # noqa: BLE001 -- records are the deliverable; analysis can be re-run
        print(f"# analyse failed: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
