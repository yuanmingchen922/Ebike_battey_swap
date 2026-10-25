"""Round 6 fill-in -- the cells that ``outputs/R6_DIGEST.md`` (sections 8 and 9) lists as still
missing or unresolved at the recalibrated order prices (``costs.R6_PRICING``: P 60 USD per
undelivered order, w 18 USD/h from the release, v 15 USD/h from the promise).

Everything here imports :mod:`experiments.r6_penalty` (the round-6 protocol: round-5 instances
generated exactly as in round 5, then repriced with :func:`ebike_swap_sim.costs.reprice_orders`;
the arc library built on the repriced copy and checked with
:func:`ebike_swap_sim.costs.check_lib_prices`; aggregated ILP O1; Gurobi Threads 3 / Seed 0;
MIP start from the first feasible rule schedule; status and MIP gap recorded) and the round-5
machinery (``r5_x2_transfers``, ``r5_x3_rolling`` / ``rolling``, ``r5_x5_stress``,
``r5_x6_manhattan`` / ``e9_bilevel_siting`` / ``bilevel``, ``r5_x7_rl``).

Part 1 -- ``--retry-unsolved [--time-limit S]`` on the existing stages ``headline``, ``psweep``,
``vsweep``, ``fleet`` and ``levers`` of ``outputs/r6_penalty/``: every ILP row (the last row per
key) whose status is not OPTIMAL, or whose solve the laptop sleep truncated (Gurobi counts
wall-clock time: ``runtime_s > wall_s + 10``, or ``wall_s`` below the requested limit while the
status is TIME_LIMIT; rows without ``wall_s`` use ``runtime_s > time_limit + 10``), is re-solved at
the given limit (defaults: headline / psweep / vsweep / fleet 600 s, levers 1800 s) from the
cheapest clean MIP start among the saved incumbent of the earlier solve (grid stages:
``schedules/<name>-ilp-<targets>.json``; X5 stages: ``schedules/<key>_<method>.json``, written by
``r6_penalty.StressRunner`` from this round on -- the first retry of a fleet / levers row solved
before that has no saved incumbent and starts from the rules), the rule schedules and, on the X5
stages, the incumbents of the other cells on the same arc library with their transfers stripped
(``r6_penalty.no_transfer_variants``: the lock-out incumbent seeds the reference cell).
The new row is appended under the same key and carries ``retry_of`` (the index of the replaced
row in ``records.jsonl``), ``retry_of_status``, ``retry_of_mip_gap``, ``retry_of_runtime_s``,
``retry_of_wall_s``, ``retry_of_total``, ``retry_reason`` and ``retry_time_limit_s``.  Winner
rule: the last row per key wins in every ``--analyse``, except that an X5 re-solve that ends
NOT OPTIMAL with a worse total than the row it replaces is marked ``retry_worse`` and ignored
(``r6_penalty.last_done_rows``), so the earlier, better row stays.  Blind re-runs are refused:
a plain TIME_LIMIT row of an X5 stage (not sleep-truncated) is re-solved only when the new
limit exceeds the row's limit (``--time-limit``); such rows are listed under
``skipped_same_limit`` (the four plain 600 s TIME_LIMIT rows of ``fleet`` are included by
``--time-limit 1800``).  The forced rows of an X5 stage are matched to the rebuilt cases by
``(cell, seed, target)`` as well as by the recomputed content key: ``r5_x5_stress.content_key`` is
an md5 over every float of the instance, and an instance rebuilt on another machine (x86-64 Linux
vs arm64 macOS: libm ``cos`` / ``hypot`` in the projection) can hash differently from the recorded
``key_md5``; the retry row then keeps the RECORDED key (so it supersedes the row it replaces in
every reader) and carries ``key_md5_rebuilt``, after ``orders_md5`` / ``demand_md5`` / sizes of the
rebuilt instance were checked against the replaced row (a real difference skips the case as
``RETRY_SKIPPED`` instead of solving a different instance under an old key).  A retry never adds a
``cases.jsonl`` note, and orphan notes (a key without any row, left by an earlier retry whose keys
did not match) are pruned to ``cases_orphans.jsonl`` before the run.  ``--analyse`` of a retried stage runs the ``r6_penalty`` analysis (which
takes the retried rows) and writes ``retries.csv``.  Every R6 table that joins the headline /
psweep ILP rows (``r6_penalty --stage rolling --analyse``, ``rolling_ext``, ``stress``) must be
re-run after a retry; the lanes do so in their final analyse step.

Part 2 -- new stages under ``outputs/r6_fill/<stage>/`` (one append-only ``records.jsonl`` per
stage, resume by key, a wall budget per stage, ``--smoke``, ``--dry-run``, ``--analyse`` with exact
Student-t 95 % intervals paired over seeds):

``transfers``   the round-5 X2 design: layouts co-located / 1 hub / 2 hubs x timetables none /
                direct shuttles (``r3``) / cyclic tours x the transfer switch, relaxed and written
                (M1) targets, rules r2, r2_reorder, M2, M3 (where services exist), M2+M3, best
                rule; usd4h (eBaaS) seeds 0-4; TimeLimit 300 s.
``stress``      stress4h-K10 seeds 0-4 and stress8h (6 bikes) seeds 0-2 (relaxed, 600 s); the
                written-target ILP on stress4h 6 bikes seeds 0-4 (price of recovery, 300 s); the
                M1 boundary grid rho in {0, .25, .5, 1} x R_end in {0, 1} plus the periodic bracket
                on stress4h 6 bikes seeds 0-2 (300 s); the LP shadow prices of one more spare and
                one more charger per site at 6 / 8 / 10 bikes seeds 0-4 (relaxed; written at 6
                bikes).  Identical cells (content key) are solved once.
``rolling_ext`` rolling horizon with lookahead 0 and 20 min and the bootstrap-forecast battery
                plan at 10 min (W 24, k 6, window TimeLimit 60 s, relaxed final targets) on usd4h
                x1 seeds 0-9 and stress4h seeds 0-4; joined at analysis to the lambda-10 rows of
                ``r6_penalty/rolling`` and the offline / rule rows of ``headline`` / ``psweep``.
``pack``        the rule-only pack-size cells of the round-5 fleet sweep: K in {4, 6, 8, 10} x B
                in {1..4} x pack in {0.5, 0.75, 1.0} kWh, seeds 0-2; joined to ``r6_penalty/fleet``
                (the 0.6 kWh grid with the ILP) in the analysis (iso-cost frontier over packs).
``levers_ext``  stress4h-K8 seeds 0-4, relaxed, 600 s: faster chargers (eps 50 Wh = x2), a second
                swap position (M 2), lock-out of one spare (shares 0.05 and 0.10 both round to one
                battery and are solved once); the site power-cap sweep with the demand-charge
                proxy (P_j in {0, p_ch}: the ``P0`` and ``reference`` rows of ``r6_penalty/levers``,
                which the analysis reuses together with the 2-spare lock-out).
``compliance``  the M4 compliance sweep psi in {0, .25, .5, .75, 1} x 3 scenarios x 3 draws, the
                selfish equilibrium (follower E) and the R2.3 rule r2 under the ILP follower's
                plan on the repriced ``r5_manhattan`` scenarios (written targets, TimeLimit 300 s,
                600 s with a charge-only hub), on (a) the layout of ``--layout-key``, by default
                the certified best written-target layout at budget m = 2 of
                ``outputs/r6_o2/manhattan/records.jsonl`` (``kind = budget_result``; the stage
                fails with a clear message when the file or the row is absent), and (b) the
                round-5 layout ``M06:SC:B4:C2|M12:S:B3:C0`` for comparison; both are priced under
                the ILP follower when not already cached (the O2 cache is copied for the layouts
                used; nothing is written into the O2 directory).
``rl_seeds``    PPO seeds 1 and 2 (seed 0 is ``r6_penalty/rl``) for the four cells of the rl stage
                (families nyc4h_stress2 and r5_stress4h x rider layers r2 and M2+M3), the same
                200,000 steps, training seeds 1000-1019 and test seeds 0-9; the ILP and rule
                reference rows are those of ``r6_penalty/rl`` (the rules are re-run per seed
                folder for the parity check; they are deterministic).  Each PPO seed runs in its
                own X7 output folder ``seed<k>/`` (models, instances, X7 records) and its rows are
                appended with ``ppo_seed`` to the stage ``records.jsonl``; the analysis is over the
                three seeds.

Part 3 -- ``--write-lanes``: ``outputs/r6_fill_lanes/lane_1.sh .. lane_4.sh`` and ``launch.json``
(nothing is started).

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r6_fill.py --retry-unsolved --stage headline,vsweep --dry-run
    python3 experiments/r6_fill.py --retry-unsolved --stage levers --time-limit 1800
    python3 experiments/r6_fill.py --stage stress --dry-run
    python3 experiments/r6_fill.py --stage rolling_ext --smoke
    python3 experiments/r6_fill.py --stage compliance --layout-key 'M06:SC:B4:C2|M12:S:B3:C0'
    python3 experiments/r6_fill.py --stage all --analyse
    python3 experiments/r6_fill.py --write-lanes
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import sys
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ebike_swap_sim import Instance, Schedule, metrics  # noqa: E402
from ebike_swap_sim import costs as cm  # noqa: E402
from ebike_swap_sim import generator as gen  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r5_x1_headline as X1  # noqa: E402
from experiments import r5_x2_transfers as X2  # noqa: E402
from experiments import r5_x3_rolling as X3  # noqa: E402
from experiments import r5_x5_stress as X5  # noqa: E402
from experiments import r6_penalty as R6  # noqa: E402

OUT_ROOT = os.path.join(C.OUTPUT_ROOT, "r6_fill")
LANES_DIR = os.path.join(C.OUTPUT_ROOT, "r6_fill_lanes")
O2_RECORDS = os.path.join(C.OUTPUT_ROOT, "r6_o2", "manhattan", "records.jsonl")
O2_CACHE = os.path.join(C.OUTPUT_ROOT, "r6_o2", "manhattan", "cache")
RECORDS = R6.RECORDS
BASE = R6.BASE
THREADS = R6.THREADS
SEEDS10, SEEDS5, SEEDS3 = R6.SEEDS10, R6.SEEDS5, R6.SEEDS3

NEW_STAGES: Tuple[str, ...] = ("transfers", "stress", "rolling_ext", "pack", "levers_ext", "compliance", "rl_seeds")
RETRY_STAGES: Tuple[str, ...] = ("headline", "psweep", "vsweep", "fleet", "levers")
#: Default re-solve limits of ``--retry-unsolved`` (seconds).
RETRY_TL: Dict[str, float] = {"headline": 600.0, "psweep": 600.0, "vsweep": 600.0, "fleet": 600.0, "levers": 1800.0}
#: Sleep guard: a Gurobi runtime more than this many seconds above the measured wall time of the
#: solve means the laptop slept during the solve (Gurobi counts wall-clock time, perf_counter does not).
SLEEP_GUARD_S = 10.0
#: The round-5 Manhattan layout of ``outputs/r5_x6_manhattan/chosen_layout.json`` (comparison).
R5_LAYOUT = "M06:SC:B4:C2|M12:S:B3:C0"
COMPLIANCE_M = 2.0
COMPLIANCE_TARGET = "written"
PSI: Tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
DRAWS: Tuple[int, ...] = (0, 1, 2)
PPO_SEEDS: Tuple[int, ...] = (1, 2)
TRANSFERS_TL = X2.TIME_LIMIT                # 300 s
STRESS_TL, STRESS_TL_LONG = X5.TL_DEFAULT, X5.TL_LONG
LEVERS_TL = X5.TL_LONG                      # 600 s
ROLL_W, ROLL_K, ROLL_WINDOW_TL = R6.ROLL_W, R6.ROLL_K, R6.ROLL_WINDOW_TL
FORECAST_LAMBDA = X3.FORECAST_LAMBDA        # 10 min
ROLL_LAMBDAS_EXT: Tuple[float, ...] = (0.0, 20.0)
#: Expected wall minutes per stage at Threads 3.  Sources: round-5 X2 wall time (8,312 s for 90
#: ILPs at 300 s, mean 92 s per ILP) + 15 % for the repricing (more orders served, harder solves);
#: X5 core / boundary (the K10 and 8 h cells sit at their 600 s limit: 5 x 700 s + 3 x 760 s; K6
#: written 5 x 220 s; LP-only cells 10 x 45 s; boundary 24 ILPs x 250 s, the round-5 boundary ran
#: 3,489 s for 22 ILPs and skipped 5); X3 per-run times on seed 0 (usd4h rolling 53-58 s,
#: forecast 121-123 s; stress4h 85 s / 254 s; round-6 lambda-10 mean 65 s) + 15 %; the rule-only
#: fleet cells of round 5 (about 3 s per cell plus one library per (K, pack, seed)); round-6 levers
#: (517 s per case) for three lever cells x 5 seeds; X6 compliance (plan = cached ILP, 45 policy
#: evaluations per layout) plus two layouts x 3 scenarios priced at <= 300 s and the selfish
#: equilibria; round-6 rl training (544 / 489 s on nyc4h_stress2, 1,603 / 1,413 s on r5_stress4h
#: = 68 min per PPO seed) plus 40 evaluations and the rules.  Retries: n x (limit + 90 s), with
#: the psweep / fleet cells that may finish early counted at about 85 % of the limit.
EST_MIN: Dict[str, float] = {"transfers": 160.0, "stress": 255.0, "rolling_ext": 90.0, "pack": 15.0,
                             "levers_ext": 165.0, "compliance": 75.0, "rl_seeds": 150.0}
#: Wall budget per stage (minutes): about 1.6 x EST_MIN.
WALL_BUDGET_MIN: Dict[str, float] = {"transfers": 260.0, "stress": 400.0, "rolling_ext": 150.0, "pack": 45.0,
                                     "levers_ext": 270.0, "compliance": 150.0, "rl_seeds": 270.0}
SMOKE_BUDGET_MIN = 30.0
SMOKE_TL = 20.0

_num, mean_ci, long_summary, gap_pct, write_md = R6._num, R6.mean_ci, R6.long_summary, R6.gap_pct, R6.write_md


def stage_dir(stage: str, smoke: bool, root: Optional[str] = None) -> str:
    base = root or (OUT_ROOT + "_smoke" if smoke else OUT_ROOT)
    return os.path.join(base, stage)


def _wall_file(out_dir: str, stage: str, budget: C.WallBudget, extra: Optional[Dict[str, Any]] = None) -> None:
    with open(os.path.join(out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"stage": stage, "wall_s": budget.elapsed(), "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
                             **(extra or {})}, default=str) + "\n")


def paired_table(per: pd.DataFrame, by: Sequence[str], a: str, b: str, label: str) -> pd.DataFrame:
    """Per group of ``by``: the per-seed difference ``a - b`` on the seeds where both exist, then
    mean and exact-t 95 % half-width (paired over seeds)."""
    out: List[Dict[str, Any]] = []
    if per.empty or a not in per.columns or b not in per.columns:
        return pd.DataFrame()
    for keys, g in per.groupby(list(by), dropna=False, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        d = [x - y for x, y in zip(pd.to_numeric(g[a], errors="coerce"), pd.to_numeric(g[b], errors="coerce"))
             if x == x and y == y]
        m, h, n = mean_ci(d)
        if n:
            out.append({**dict(zip(by, keys)), "metric": label, "mean_diff": m, "ci95": h, "n_pairs": n})
    return pd.DataFrame(out)


# ===========================================================================
# Part 1: retries of unsolved / sleep-truncated ILP rows
# ===========================================================================
def is_ilp_row(row: Optional[Dict[str, Any]]) -> bool:
    if not row:
        return False
    m = str(row.get("method") or "")
    return m == "ilp" or m.startswith("ILP_tl")


def ilp_timing(row: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """``runtime`` (Gurobi wall-clock seconds), ``wall`` (perf_counter seconds around the solve,
    grid rows only) and ``limit`` (the TimeLimit used) of an ILP row of any round-6 stage."""
    limit = None
    for k in ("time_limit_s", "time_limit_used_s", "time_limit"):
        limit = _num(row.get(k))
        if limit is not None:
            break
    return {"runtime": _num(row.get("runtime_s")), "wall": _num(row.get("wall_s")), "limit": limit}


def sleep_truncated(row: Dict[str, Any], guard: float = SLEEP_GUARD_S) -> bool:
    """True for a TIME_LIMIT row whose solve the laptop sleep cut short: the Gurobi runtime
    exceeds the measured wall time of the solve by more than ``guard`` seconds, or the wall time
    is below the time limit although the solver reports TIME_LIMIT; rows without ``wall_s`` (the
    X5 stages) use ``runtime_s > limit + guard``."""
    if row.get("status") != "TIME_LIMIT":
        return False
    t = ilp_timing(row)
    rt, wall, limit = t["runtime"], t["wall"], t["limit"]
    if wall is not None:
        if rt is not None and rt > wall + guard:
            return True
        return limit is not None and wall < limit - 1.0
    return rt is not None and limit is not None and rt > limit + guard


def retry_reason(row: Optional[Dict[str, Any]]) -> Optional[str]:
    """``None`` for a row that stays (OPTIMAL, or not an ILP row), ``'sleep_truncated'`` or
    ``'not_optimal'`` (TIME_LIMIT, SUBOPTIMAL, INTERRUPTED, ERROR, SKIPPED_BUDGET ...)."""
    if not is_ilp_row(row):
        return None
    if row.get("status") == "OPTIMAL":
        return None
    return "sleep_truncated" if sleep_truncated(row) else "not_optimal"


def retry_cols(index: int, prev: Dict[str, Any], reason: str, tl: float) -> Dict[str, Any]:
    t = ilp_timing(prev)
    return {"retry_of": int(index), "retry_of_status": prev.get("status"),
            "retry_of_mip_gap": _num(prev.get("mip_gap") if "mip_gap" in prev else prev.get("gap")),
            "retry_of_runtime_s": t["runtime"], "retry_of_wall_s": t["wall"], "retry_of_time_limit_s": t["limit"],
            "retry_of_total": _num(prev.get("total")), "retry_reason": reason, "retry_time_limit_s": float(tl),
            "retry_n": int(prev.get("retry_n") or 0) + 1}


def select_grid_retries(records_path: str) -> Dict[Tuple, Tuple[int, Dict[str, Any], str]]:
    """Last row per X1 key of a grid stage (``r5_x1_headline.key_of``) that needs a re-solve:
    ``{key: (record index, row, reason)}``."""
    last: Dict[Tuple, Tuple[int, Dict[str, Any]]] = {}
    for i, r in enumerate(C.load_jsonl(records_path)):
        try:
            last[X1.key_of(r)] = (i, r)
        except (KeyError, TypeError, ValueError):
            continue
    out: Dict[Tuple, Tuple[int, Dict[str, Any], str]] = {}
    for k, (i, r) in last.items():
        reason = retry_reason(r)
        if reason:
            out[k] = (i, r, reason)
    return out


def select_stress_retries(records_path: str) -> Dict[Tuple[str, str], Tuple[int, Dict[str, Any], str]]:
    """Same for an X5-layout stage (``fleet``, ``levers``): the row per ``(key_md5, method)`` that
    ``r6_penalty.wide_r6`` takes (``r6_penalty.last_done_rows``: the last done row, else the last
    row; ``retry_worse`` rows ignored)."""
    rows: Dict[Tuple[str, str], Tuple[int, Dict[str, Any]]] = {}
    for i, r in enumerate(C.load_jsonl(records_path)):
        if r.get("retry_worse"):
            continue
        k = (str(r.get("key_md5")), str(r.get("method")))
        if X5._is_done(r) or k not in rows:
            rows[k] = (i, r)
    out: Dict[Tuple[str, str], Tuple[int, Dict[str, Any], str]] = {}
    for k, (i, r) in rows.items():
        reason = retry_reason(r)
        if reason:
            out[k] = (i, r, reason)
    return out


def blind_rerun(row: Dict[str, Any], reason: str, tl: float) -> bool:
    """True when re-solving ``row`` at ``tl`` would be a blind re-run: a plain TIME_LIMIT row (not
    sleep-truncated) whose limit is already ``>= tl``.  Without a saved incumbent such a re-run
    only repeats the search up to the wall-clock cut; it needs a larger ``--time-limit``."""
    if reason != "not_optimal" or row.get("status") != "TIME_LIMIT":
        return False
    limit = ilp_timing(row)["limit"]
    return limit is not None and float(tl) <= float(limit) + 1e-6


def stress_retry_selection(records_path: str, tl: float
                           ) -> Tuple[Dict[Tuple[str, str], Tuple[int, Dict[str, Any], str]],
                                      Dict[Tuple[str, str], Tuple[int, Dict[str, Any], str]]]:
    """``(to re-solve, skipped_same_limit)`` of an X5 stage at the retry limit ``tl``."""
    sel = select_stress_retries(records_path)
    run = {k: v for k, v in sel.items() if not blind_rerun(v[1], v[2], tl)}
    skip = {k: v for k, v in sel.items() if k not in run}
    return run, skip


class RetryGridRunner(R6.GridRunner):
    """``r6_penalty.GridRunner`` that re-solves the forced keys (``{key: (index, row, reason)}``)
    at ``tl`` and marks the new rows."""

    def __init__(self, stage: str, out_dir: str, threads: int, budget: C.WallBudget, smoke: bool,
                 root: Optional[str], force: Dict[Tuple, Tuple[int, Dict[str, Any], str]], tl: float) -> None:
        super().__init__(stage, out_dir, threads, budget, smoke, root)
        self.force = dict(force)
        self.tl = float(tl)

    def is_done(self, key: Tuple, tl: Optional[float] = None) -> bool:
        if key in self.force:
            return False
        return super().is_done(key, tl)

    def emit(self, row: Dict[str, Any]) -> None:
        key = X1.key_of(row)
        f = self.force.get(key)
        if f is not None and is_ilp_row(row):
            row.update(retry_cols(f[0], f[1], f[2], self.tl))
            row["source"] = "r6_fill_retry"
            self.force.pop(key, None)
        super().emit(row)


def plan_grid_retries(stage: str, sel: Dict[Tuple, Tuple[int, Dict[str, Any], str]], tl: float) -> List[R6.Cell]:
    """One ``Cell`` per (case, pricing, seed, mult) holding the ILP targets to re-solve; the rules
    of those targets are re-run (ms) for the MIP-start candidates."""
    by_cell: Dict[Tuple, List[str]] = {}
    rows: Dict[Tuple, Dict[str, Any]] = {}
    for k, (_i, r, _reason) in sel.items():
        by_cell.setdefault(k[:4], []).append(k[4])
        rows.setdefault(k[:4], r)
    cells: List[R6.Cell] = []
    for ck in sorted(by_cell, key=lambda t: tuple(map(str, t))):
        case, lab, seed, mult = ck
        r = rows[ck]
        pr = R6.pricing(float(r["P"]), float(r["v"]), float(r.get("w", R6.W_HOUR)))
        if pr["label"] != lab:
            raise RuntimeError(f"{stage}: pricing label {pr['label']} != calib {lab} of the row")
        targets = tuple(t for t in ("written", "relaxed") if t in by_cell[ck])
        cells.append(R6.Cell(case, pr, int(seed), float(mult), targets, targets, float(tl)))
    return cells


def case_id_of(row: Dict[str, Any]) -> Tuple[str, int, str]:
    """``(cell, seed, target)`` of an X5-layout row or ``cases.jsonl`` note: the identity by which
    a forced row is matched to its rebuilt case when the content key drifted."""
    return (str(row.get("cell")), int(row.get("seed")), str(row.get("target")))


def instance_drift(t: Instance, prev: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """``(checked, differing)`` fields among ``orders_md5``, ``demand_md5``, ``n_bikes``,
    ``n_orders``, ``H``, ``L`` of the rebuilt instance ``t`` against the replaced row ``prev``
    (fields the row does not carry are not checked).  These are hashes / counts of ids, nodes and
    slots -- stable across machines -- unlike the content key, which hashes every float."""
    new = {"orders_md5": X5.orders_md5(t), "demand_md5": C.demand_md5(t), "n_bikes": len(t.bikes),
           "n_orders": len(t.orders), "H": t.H, "L": t.L}
    checked = [f for f in new if prev.get(f) is not None]
    diff = [f for f in checked if str(prev.get(f)) != str(new[f])]
    return checked, diff


def prune_orphan_case_notes(out_dir: str, dry_run: bool = False) -> List[Dict[str, Any]]:
    """Notes of ``cases.jsonl`` whose ``key_md5`` has no row at all in ``records.jsonl`` while
    another note of the same ``(sub, cell, seed, target)`` has rows: left behind by a retry whose
    recomputed keys did not match the recorded ones (``X5.Runner.run_case`` notes the case before
    it finds nothing to do).  ``wide_r6`` prefers the note naming an ILP method, so such a note
    would hide the cell's real rows from the analysis.  Unless ``dry_run``, the orphans are moved
    to ``cases_orphans.jsonl`` and ``cases.jsonl`` is rewritten without them.  Returns them."""
    cpath = os.path.join(out_dir, "cases.jsonl")
    notes = C.load_jsonl(cpath)
    if not notes:
        return []
    keyed = {str(r.get("key_md5")) for r in C.load_jsonl(os.path.join(out_dir, RECORDS))}
    by_case: Dict[Tuple, List[Dict[str, Any]]] = {}
    for n in notes:
        by_case.setdefault((n.get("sub"),) + case_id_of(n), []).append(n)
    orphans: List[Dict[str, Any]] = []
    for group in by_case.values():
        with_rows = [n for n in group if str(n.get("key_md5")) in keyed]
        if with_rows and len(with_rows) < len(group):
            orphans += [n for n in group if str(n.get("key_md5")) not in keyed]
    if orphans and not dry_run:
        drop = {id(n) for n in orphans}
        with open(os.path.join(out_dir, "cases_orphans.jsonl"), "a", encoding="utf-8") as fh:
            for n in orphans:
                fh.write(json.dumps(C.jsonable({**n, "pruned_at": time.strftime("%Y-%m-%d %H:%M:%S")})) + "\n")
        tmp = cpath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for n in notes:
                if id(n) not in drop:
                    fh.write(json.dumps(C.jsonable(n)) + "\n")
        os.replace(tmp, cpath)
    return orphans


class RetryStressRunner(R6.StressRunner):
    """``r6_penalty.StressRunner`` restricted to the forced ILP rows ``{(key_md5, method): (index,
    row, reason)}``: the case's rules are re-run for the start candidates (not emitted), the ILP is
    solved again at the case's new limit under the ORIGINAL method name (the row key), from the
    cheapest clean start among the saved incumbent ``schedules/<key>_<method>.json`` (when an
    earlier solve by ``StressRunner`` saved one), the rules and the other cells' incumbents on the
    same library (with and without their transfers).  A re-solve that ends NOT OPTIMAL with a
    worse total than the replaced row is appended marked ``retry_worse`` (ignored by every
    reader, its incumbent not saved), so the earlier row stays the row of the key.

    A forced row is matched to the rebuilt case by its recorded ``key_md5`` == the recomputed
    content key, else by ``(cell, seed, target)`` (:func:`case_id_of`): the content key hashes
    every float of the instance and is not stable across machines (the fleet records were written
    on the laptop; rebuilt on the x86-64 server every key differed, no row matched, and the run
    reported every case ``reused``).  On such a drift the row keeps the RECORDED key (it must
    supersede the replaced row under ``r6_penalty.last_done_rows``) and carries
    ``key_md5_rebuilt``; first :func:`instance_drift` checks ``orders_md5`` / ``demand_md5`` /
    sizes, and a real difference skips the case (``RETRY_SKIPPED``, nothing emitted).  The forced
    method is re-solved whatever ``r5_x5_stress._is_done`` / ``common.reusable_ilp_row`` say about
    the row (a TIME_LIMIT row within the 1 % reuse gap is still re-solved when selected)."""

    def __init__(self, out_dir: str, stage: str, pr: Dict[str, Any], threads: int,
                 force: Dict[Tuple[str, str], Tuple[int, Dict[str, Any], str]], tl: float) -> None:
        super().__init__(out_dir, stage, pr, threads)
        self.force = dict(force)
        self.tl = float(tl)
        self._cur: Optional[Tuple[str, Tuple[int, Dict[str, Any], str]]] = None
        self._key: Optional[str] = None
        self._rebuilt_key: Optional[str] = None
        self._mismatch: Optional[str] = None
        self.n_worse = 0
        self.n_drift = 0
        self.skipped_mismatch: List[Dict[str, Any]] = []

    def case_status(self, case: X5.Case) -> Tuple[Instance, Instance, str, Dict[str, Any], List[str]]:
        w, t, key, pr, _todo = super().case_status(case)
        self._cur, self._key, self._rebuilt_key, self._mismatch = None, key, None, None
        hits = [(k, m, f) for (k, m), f in self.force.items() if k == key]
        if not hits:
            cid = (str(case.cell), int(case.seed), str(case.target))
            by_case = [(k, m, f) for (k, m), f in self.force.items() if case_id_of(f[1]) == cid]
            if by_case:
                k, m, f = by_case[-1]
                checked, diff = instance_drift(t, f[1])
                if diff:
                    self._mismatch = (f"recorded key {k[:8]} != rebuilt {key[:8]} and the rebuilt instance differs in "
                                      f"{', '.join(diff)} (checked {', '.join(checked)}); not re-solved")
                    print(f"# retry {case.cell} s{case.seed} {case.target}: {self._mismatch}", flush=True)
                else:
                    self._key, self._rebuilt_key = k, key
                    self.n_drift += 1
                    hits = [(k, m, f)]
                    print(f"# retry {case.cell} s{case.seed} {case.target}: content key drifted (recorded {k[:8]}, rebuilt "
                          f"{key[:8]}; {', '.join(checked) or 'nothing'} equal): the row keeps the recorded key, "
                          f"key_md5_rebuilt records the new one", flush=True)
        if hits:
            _k, m, f = hits[-1]
            self._cur = (m, f)
        # the saved incumbent to offer: schedules/<recorded key>_<forced method>.json
        self._cur_key, self._cur_ilp_method = self._key, (self._cur[0] if self._cur else None)
        return w, t, self._key, pr, ([self._cur[0]] if self._cur else [])

    def note_case(self, case: X5.Case, key: str) -> None:
        """A retry never adds a case note: every forced row's case is already in ``cases.jsonl``
        (``_stress_cases_for_retry`` found it there), and a note under a drifted key would hide
        the cell's rows from ``wide_r6``."""
        return None

    def run_case(self, case: X5.Case) -> Dict[str, Any]:
        s = super().run_case(case)
        if s.pop("reused", False):
            s["status"] = "RETRY_SKIPPED"
            s["skip_reason"] = self._mismatch or "no forced row matched this case (neither by key nor by cell/seed/target)"
            self.skipped_mismatch.append({"cell": case.cell, "seed": case.seed, "target": case.target, "reason": s["skip_reason"]})
            self.skipped.append(f"{case.sub}:{case.cell}:s{case.seed}:{case.target}:retry_skipped")
        return s

    def current_method(self, tl: float) -> str:
        return self._cur[0] if self._cur else X5._r6_orig_ilp_method(tl)   # type: ignore[attr-defined]

    def emit(self, sub: str, row: Dict[str, Any]) -> None:
        worse = False
        if self._cur and row.get("method") == self._cur[0] and str(row.get("key_md5")) == self._key:
            i, prev, reason = self._cur[1]
            row = {**row, **retry_cols(i, prev, reason, self.tl), "source": "r6_fill_retry"}
            if self._rebuilt_key is not None:
                row["key_md5_rebuilt"] = self._rebuilt_key
            new_t, old_t = _num(row.get("total")), _num(prev.get("total"))
            worse = (row.get("status") != "OPTIMAL" and X5._is_done(row) and new_t is not None and old_t is not None
                     and new_t > old_t + 1e-6)
            row["retry_worse"] = worse
            self.force.pop((self._key, self._cur[0]), None)
            if worse:
                self.n_worse += 1
                print(f"# retry {row.get('cell')} s{row.get('seed')} {row.get('method')}: worse total "
                      f"{new_t:.3f} > {old_t:.3f}; marked retry_worse, previous row kept", flush=True)
        super().emit(sub, row)
        if worse:
            self._last_ilp_row = None          # do not overwrite the saved incumbent with a worse one


def _stress_cases_for_retry(stage: str, sel: Dict[Tuple[str, str], Tuple[int, Dict[str, Any], str]],
                            out_dir: str, tl: float, smoke: bool) -> List[X5.Case]:
    """The X5 cases (from the stage planner, rebuilt with the new limit) whose ILP row is in ``sel``;
    ``cases.jsonl`` maps ``key_md5`` to (cell, seed, target).  Levers: the lock-out cells first so
    that their incumbents are in the start pool when the reference is solved."""
    cases = {c["key_md5"]: c for c in C.load_jsonl(os.path.join(out_dir, "cases.jsonl"))}
    plan = (R6.plan_levers_r6 if stage == "levers" else R6.plan_fleet_r6)(BASE, smoke, None)
    by_cell = {(c.cell, int(c.seed), c.target): c for c in plan}
    out: List[X5.Case] = []
    for (key, _m), (_i, row, _reason) in sel.items():
        c = cases.get(key)
        if c is None:
            print(f"# {stage}: no case for key {key} (row {row.get('cell')} s{row.get('seed')}); skipped", flush=True)
            continue
        case = by_cell.get((c["cell"], int(c["seed"]), c["target"]))
        if case is None:
            print(f"# {stage}: planner has no case {c['cell']} s{c['seed']} {c['target']}; skipped", flush=True)
            continue
        case = X5.Case(case.sub, case.cell, case.seed, case.target, case.build_id, case.builder, float(tl), case.lp,
                       case.phase, dict(case.info), case.n_bikes, case.H)
        out.append(case)
    order = {"lockout0.25": 0, "lockout0.1": 0, "lockout0.05": 0, "P0": 1, "reference": 2}
    out.sort(key=lambda c: (c.seed, order.get(c.cell, 1), c.cell) if stage == "levers" else (c.seed, c.cell))
    return out


class ilp_method_override:
    """``with ilp_method_override(runner):`` -- ``r5_x5_stress.ilp_method`` returns the forced
    method name of the runner's current case (``RetryStressRunner.current_method``), so the
    retried row keeps its method name (its key) at the new limit; restored on exit."""

    def __init__(self, runner: RetryStressRunner) -> None:
        self.runner = runner

    def __enter__(self) -> "ilp_method_override":
        if not hasattr(X5, "_r6_orig_ilp_method"):
            X5._r6_orig_ilp_method = X5.ilp_method          # type: ignore[attr-defined]
        X5.ilp_method = self.runner.current_method
        return self

    def __exit__(self, *exc: Any) -> None:
        X5.ilp_method = X5._r6_orig_ilp_method             # type: ignore[attr-defined]


def retry_plan(stage: str, args: argparse.Namespace) -> Dict[str, Any]:
    out_dir = R6.stage_dir(stage, args.smoke, args.out_root)
    tl = float(args.time_limit) if args.time_limit else RETRY_TL[stage]
    path = os.path.join(out_dir, RECORDS)
    if stage in R6.GRID_STAGES:
        sel: Dict[Any, Tuple[int, Dict[str, Any], str]] = select_grid_retries(path)
        items = [{"key": list(map(str, k)), "index": i, "status": r.get("status"), "mip_gap": _num(r.get("mip_gap")),
                  "runtime_s": _num(r.get("runtime_s")), "wall_s": _num(r.get("wall_s")), "reason": reason}
                 for k, (i, r, reason) in sorted(sel.items(), key=lambda kv: tuple(map(str, kv[0])))]
        skipped: List[Dict[str, Any]] = []
    else:
        sel, skip = stress_retry_selection(path, tl)

        def item(k: str, m: str, i: int, r: Dict[str, Any], reason: str) -> Dict[str, Any]:
            return {"key": [r.get("cell"), r.get("seed"), m], "key_md5": k, "index": i, "status": r.get("status"),
                    "mip_gap": _num(r.get("gap")), "runtime_s": _num(r.get("runtime_s")),
                    "time_limit": _num(r.get("time_limit")), "reason": reason}
        order = lambda kv: (str(kv[1][1].get("seed")), str(kv[1][1].get("cell")))  # noqa: E731
        items = [item(k, m, i, r, reason) for (k, m), (i, r, reason) in sorted(sel.items(), key=order)]
        skipped = [{**item(k, m, i, r, reason), "skip_reason": f"plain TIME_LIMIT at {_num(r.get('time_limit'))} s >= retry limit "
                    f"{tl:g} s: a blind re-run; pass a larger --time-limit"}
                   for (k, m), (i, r, reason) in sorted(skip.items(), key=order)]
    est_min = len(sel) * (tl * (0.85 if stage in ("psweep", "fleet") else 1.0) + 90.0) / 60.0
    out = {"stage": stage, "out_dir": out_dir, "time_limit_s": tl, "n_retries": len(sel), "expected_wall_min": round(est_min, 1),
           "n_skipped_same_limit": len(skipped), "items": items, "skipped_same_limit": skipped, "_sel": sel}
    if stage not in R6.GRID_STAGES:
        orphans = prune_orphan_case_notes(out_dir, dry_run=True)
        out["n_orphan_case_notes"] = len(orphans)
        out["orphan_case_notes"] = [{"cell": o.get("cell"), "seed": o.get("seed"), "target": o.get("target"),
                                     "key_md5": o.get("key_md5"), "ilp_method": o.get("ilp_method")} for o in orphans]
    return out


def run_retry(stage: str, args: argparse.Namespace) -> None:
    plan = retry_plan(stage, args)
    sel, tl, out_dir = plan.pop("_sel"), plan["time_limit_s"], plan["out_dir"]
    if args.dry_run:
        print(json.dumps(plan, indent=1, default=str))
        return
    if plan.get("skipped_same_limit"):
        print(f"# retry {stage}: {len(plan['skipped_same_limit'])} plain TIME_LIMIT row(s) at a limit >= {tl:g} s skipped "
              f"(blind re-run; pass a larger --time-limit): "
              + ", ".join(f"{x['key'][0]} s{x['key'][1]}" for x in plan["skipped_same_limit"]), flush=True)
    if not sel:
        print(f"# retry {stage}: nothing to re-solve", flush=True)
        print(R6.analyse(stage, args.smoke, args.out_root), flush=True)
        return
    budget_min = args.budget_min or max(30.0, 1.3 * len(sel) * (tl + 90.0) / 60.0)
    budget = (C.WallBudget(budget_min * 60.0, margin_s=0.0, min_solve_s=1.0) if args.smoke
              else C.WallBudget(budget_min * 60.0))
    print(f"# retry {stage}: {len(sel)} ILP row(s) at {tl:.0f} s -> {out_dir} (budget {budget_min:.0f} min)", flush=True)
    if stage in R6.GRID_STAGES:
        runner = RetryGridRunner(stage, out_dir, args.threads, budget, args.smoke, args.out_root, sel, tl)
        runner.run(plan_grid_retries(stage, sel, tl))
        n_rows = runner.n_runs
    else:
        X5.sched_cols = R6._sched_cols_r6
        orphans = prune_orphan_case_notes(out_dir)
        if orphans:
            print(f"# retry {stage}: {len(orphans)} orphan cases.jsonl note(s) (keys without rows, left by an earlier retry whose "
                  f"keys did not match) moved to cases_orphans.jsonl: "
                  + ", ".join(f"{o.get('cell')} s{o.get('seed')} {str(o.get('key_md5'))[:8]}" for o in orphans), flush=True)
        runner_s = RetryStressRunner(out_dir, stage, BASE, args.threads, sel, tl)
        cases = _stress_cases_for_retry(stage, sel, out_dir, tl, args.smoke)
        with ilp_method_override(runner_s):                # the retried row keeps its method name (its key)
            runner_s.run_plan(stage, cases, budget_min * 60.0)
        n_rows = len(cases)
        if runner_s.n_drift:
            print(f"# retry {stage}: {runner_s.n_drift} case(s) rebuilt with a drifted content key; their rows keep the recorded "
                  f"key_md5 and carry key_md5_rebuilt", flush=True)
        if runner_s.skipped_mismatch:
            print(f"# retry {stage}: {len(runner_s.skipped_mismatch)} case(s) NOT re-solved (RETRY_SKIPPED): "
                  + "; ".join(f"{x['cell']} s{x['seed']}: {x['reason']}" for x in runner_s.skipped_mismatch), flush=True)
        if runner_s.force:
            print(f"# retry {stage}: WARNING {len(runner_s.force)} forced row(s) were not re-solved: "
                  + ", ".join(f"{f[1].get('cell')} s{f[1].get('seed')} {m}" for (_k, m), f in runner_s.force.items()), flush=True)
        if runner_s.n_worse:
            print(f"# retry {stage}: {runner_s.n_worse} re-solve(s) ended worse than the replaced row (retry_worse; previous row kept)",
                  flush=True)
    extra = {"rows": n_rows, "time_limit_s": tl, "smoke": args.smoke, "skipped_same_limit": len(plan.get("skipped_same_limit") or [])}
    if stage not in R6.GRID_STAGES:
        extra.update(key_drift=runner_s.n_drift, retry_skipped=len(runner_s.skipped_mismatch), not_resolved=len(runner_s.force))
    _wall_file(out_dir, f"{stage}_retry", budget, extra)
    print(analyse_retry(stage, args.smoke, args.out_root), flush=True)


def retries_table(stage: str, out_dir: str) -> pd.DataFrame:
    """``retries.csv``: per retried key the replaced row and the final row (last per key)."""
    rows = C.load_jsonl(os.path.join(out_dir, RECORDS))
    grid = stage in R6.GRID_STAGES
    out: List[Dict[str, Any]] = []
    last: Dict[Any, Dict[str, Any]] = {}
    for r in rows:
        if r.get("retry_of") is None:
            continue
        k = X1.key_of(r) if grid else (str(r.get("key_md5")), str(r.get("method")))
        last[k] = r
    for k, r in last.items():
        gap = r.get("mip_gap") if grid else r.get("gap")
        out.append({"key": "|".join(map(str, k)) if grid else f"{r.get('cell')}|s{r.get('seed')}|{k[1]}",
                    "cell": r.get("name") or r.get("cell"), "seed": r.get("seed"), "retry_n": r.get("retry_n"),
                    "retry_worse": bool(r.get("retry_worse")),
                    "retry_reason": r.get("retry_reason"), "prev_status": r.get("retry_of_status"),
                    "prev_mip_gap": r.get("retry_of_mip_gap"), "prev_total": r.get("retry_of_total"),
                    "prev_runtime_s": r.get("retry_of_runtime_s"), "prev_wall_s": r.get("retry_of_wall_s"),
                    "new_status": r.get("status"), "new_mip_gap": _num(gap), "new_total": _num(r.get("total")),
                    "new_runtime_s": _num(r.get("runtime_s")), "new_time_limit_s": r.get("retry_time_limit_s"),
                    "mip_start_variant": r.get("mip_start_variant"), "obj_eq_eval": r.get("obj_eq_eval"),
                    "improved_usd": (None if _num(r.get("retry_of_total")) is None or _num(r.get("total")) is None
                                     else _num(r.get("retry_of_total")) - _num(r.get("total")))})
    return pd.DataFrame(out)


def analyse_retry(stage: str, smoke: bool, root: Optional[str]) -> str:
    out_dir = R6.stage_dir(stage, smoke, root)
    msg = R6.analyse(stage, smoke, root)
    t = retries_table(stage, out_dir)
    t.to_csv(os.path.join(out_dir, "retries.csv"), index=False)
    if not t.empty:
        n_opt = int((t.new_status == "OPTIMAL").sum())
        n_worse = int(t.retry_worse.sum())
        lines = ["", "## Retries (r6_fill --retry-unsolved; last row per key wins above, except retry_worse rows, which "
                 "are ignored and leave the previous row in place)", "",
                 f"{len(t)} re-solved ILP row(s), {n_opt} now OPTIMAL, {n_worse} worse than the replaced row (kept); "
                 "improvement = previous total - new total (USD).", "",
                 C.markdown_table(t, ["key", "retry_reason", "prev_status", "prev_mip_gap", "new_status", "new_mip_gap",
                                      "improved_usd", "retry_worse", "new_runtime_s", "new_time_limit_s", "mip_start_variant"], 4), ""]
        p = os.path.join(out_dir, "RESULTS.md")
        if os.path.exists(p):
            with open(p, "a", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
    return f"{msg}; retries.csv: {len(t)} row(s)"


# ===========================================================================
# Part 2a: transfers (r5_x2_transfers under the base pricing)
# ===========================================================================
def _install_x2_pricing(pr: Dict[str, Any]) -> Any:
    """Route every X2 instance through the repriced builder and add the round-6 columns (pricing,
    lateness, objective check) to the X2 row builders.  Idempotent."""
    if getattr(X2, "_r6_wrapped", None) == pr["label"]:
        return X2
    orig_make = getattr(X2, "_r6_orig_make_x2_instance", X2.make_x2_instance)
    orig_base = getattr(X2, "_r6_orig_baseline_row", X2.baseline_row)
    orig_ilp = getattr(X2, "_r6_orig_ilp_row", X2.ilp_row)
    X2._r6_orig_make_x2_instance, X2._r6_orig_baseline_row, X2._r6_orig_ilp_row = orig_make, orig_base, orig_ilp

    def make_x2_instance(seed: int, layout: str, timetable: str) -> Instance:
        inst = R6.priced(orig_make(seed, layout, timetable), pr, "transfers")
        inst.meta["r6_case"] = "x2"
        return inst

    def baseline_row(inst: Instance, lib: Any, build_time: float, label: str, base: Dict[str, Any]) -> Dict[str, Any]:
        row = orig_base(inst, lib, build_time, label, base)
        row.update(R6.lateness_cols(inst, lib, base.get("schedule")), **R6.price_cols(pr, "transfers"))
        row["rule_label"] = R6.RULE_LABEL.get(label, label)
        return row

    def ilp_row(inst: Instance, lib: Any, build_time: float, switch: str, rec: Dict[str, Any], start_label: str,
                tl: float, bases: Dict[str, Dict[str, Any]], threads: int) -> Dict[str, Any]:
        row = orig_ilp(inst, lib, build_time, switch, rec, start_label, tl, bases, threads)
        row.update(R6.lateness_cols(inst, lib, rec.get("schedule")), **R6.price_cols(pr, "transfers"))
        if rec.get("obj") is not None and rec.get("cost") is not None:
            row.update(R6.obj_check_cols({"obj": rec["obj"], "cost": rec["cost"]}))
        row["time_limit_requested_s"] = row.get("time_limit_requested_s", tl)
        return row

    X2.make_x2_instance, X2.baseline_row, X2.ilp_row = make_x2_instance, baseline_row, ilp_row
    X2._r6_wrapped = pr["label"]
    return X2


class TransfersRunner(X2.Runner):
    """X2 runner on the repriced instances: library price check per context, ``wall_s`` around the
    solve, requested limit recorded (resume rule of ``r6_penalty.budget_cut``)."""

    def __init__(self, out_dir: str, time_limit: float, threads: int, budget: C.WallBudget, pr: Dict[str, Any]) -> None:
        super().__init__(out_dir, time_limit, threads, budget, verify_rebind=False)
        self.pr = pr

    def emit(self, row: Dict[str, Any]) -> None:
        row.setdefault("stage", "transfers")
        row["source"] = "r6_fill"
        super().emit(row)

    def context(self, targets: str, layout: str, seed: int, timetable: str) -> Dict[str, Any]:
        ctx = super().context(targets, layout, seed, timetable)
        if "lib_price_checked_arcs" not in ctx:
            ctx["lib_price_checked_arcs"] = cm.check_lib_prices(ctx["inst"], ctx["lib"])["n_checked"]
        return ctx

    def run_item(self, item: X2.WorkItem) -> None:
        targets, layout, seed, switch, timetable = item
        tl = self.budget.solve_limit(self.tl)
        if tl is None:
            self.emit(X2.skipped_row(layout, timetable, targets, seed, switch,
                                     f"wall budget exhausted after {self.budget.elapsed():.0f}s"))
            return
        ctx = self.context(targets, layout, seed, timetable)
        inst, lib, bases = ctx["inst"], ctx["lib"], ctx["bases"]
        tl = self.budget.solve_limit(self.tl)
        if tl is None:
            self.emit(X2.skipped_row(layout, timetable, targets, seed, switch,
                                     f"wall budget exhausted after {self.budget.elapsed():.0f}s (after policies)"))
            return
        start, start_label = self.mip_start(ctx, switch)
        t0 = time.perf_counter()
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=self.threads, label="ilp",
                             no_transfers=(switch == "none"), params=dict(C.ILP_PARAMS_R3), **C.R5_ILP_KWARGS)
        wall = time.perf_counter() - t0
        row = X2.ilp_row(inst, lib, self._lib_build, switch, rec, start_label, tl, bases, self.threads)
        row.update(wall_s=wall, time_limit_requested_s=self.tl, budget_shortened=bool(tl < self.tl - 1e-6),
                   lib_price_checked_arcs=ctx["lib_price_checked_arcs"])
        if rec["schedule"] is not None:
            with open(self.schedule_path(layout, timetable, targets, seed, switch), "w", encoding="utf-8") as fh:
                json.dump(C.jsonable(rec["schedule"].to_dict()), fh)
        rec["schedule"] = None
        self.emit(row)


def transfers_design(smoke: bool, seeds: Optional[Sequence[int]]) -> Dict[str, Any]:
    if smoke:
        return {"seeds": [0], "layouts": ["colocated"], "targets": ["relaxed"], "timetables": ["r3"],
                "switches": ["none", "free"], "tl": SMOKE_TL}
    return {"seeds": list(seeds) if seeds is not None else list(X2.SEEDS), "layouts": list(X2.LAYOUTS),
            "targets": list(X2.TARGETS), "timetables": list(X2.TIMETABLES), "switches": list(X2.SWITCHES),
            "tl": TRANSFERS_TL}


def _transfers_done(path: str, tl: float) -> Dict[X2.Key, Dict[str, Any]]:
    done = {X2.key_of(r): r for r in C.load_jsonl(path)}
    # a row cut short by the wall budget is re-solved (r6 rule); X2.row_done handles the rest
    return {k: r for k, r in done.items() if not R6.budget_cut(r, tl, used_key="time_limit_used_s")}


def run_transfers(args: argparse.Namespace) -> None:
    out_dir = stage_dir("transfers", args.smoke, args.out_root)
    d = transfers_design(args.smoke, args.seeds)
    _install_x2_pricing(BASE)
    existing = _transfers_done(os.path.join(out_dir, RECORDS), d["tl"])
    plan = X2.build_plan(existing, d["seeds"], d["layouts"], targets_order=d["targets"], timetables=d["timetables"],
                         switches=d["switches"], time_limit=d["tl"])
    summ = X2.plan_summary(plan, d["tl"], 92.0 * 1.15, 25.0)
    summ.update(stage="transfers", out_dir=out_dir, existing_rows=len(existing), expected_wall_min_r6=EST_MIN["transfers"],
                pricing=BASE["label"], **{k: v for k, v in d.items()})
    if args.dry_run:
        print(json.dumps(summ, indent=1, default=str))
        for it in plan:
            print("  ", it)
        return
    budget = C.WallBudget(args.budget_min * 60.0, margin_s=(5.0 if args.smoke else 90.0), min_solve_s=(5.0 if args.smoke else 30.0))
    runner = TransfersRunner(out_dir, d["tl"], args.threads, budget, BASE)
    print(f"# R6 transfers: {len(plan)} ILP items -> {out_dir}", flush=True)
    for item in plan:
        try:
            runner.run_item(item)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - unattended lanes
            targets, layout, seed, switch, timetable = item
            row = X2.skipped_row(layout, timetable, targets, seed, switch, f"{type(exc).__name__}: {exc}")
            row.update(status="ERROR", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc()[-3000:])
            runner.emit(row)
    _wall_file(out_dir, "transfers", budget, {"rows": runner.n_runs, "smoke": args.smoke})
    print(analyse_transfers(out_dir), flush=True)


def analyse_transfers(out_dir: str) -> str:
    if not os.path.exists(os.path.join(out_dir, RECORDS)):
        return "transfers: no records"
    try:
        X2.analyse(out_dir)
        if os.path.exists(os.path.join(out_dir, "RESULTS.md")):
            os.replace(os.path.join(out_dir, "RESULTS.md"), os.path.join(out_dir, "RESULTS_x2.md"))
    except SystemExit as exc:
        return f"transfers: {exc}"
    except Exception as exc:  # noqa: BLE001
        print(f"# X2.analyse failed: {type(exc).__name__}: {exc}", flush=True)
    df = X2.load_frame(out_dir)
    ilp = df[df.method == "ilp"].copy()
    if ilp.empty:
        return "transfers: no ILP rows yet"
    for c in ("gap_vs_best_rule_pct", "gap_vs_best_rule_pct_end_adjusted", "n_late_over_60min", "served_share",
              "transfers_used", "batteries_moved", "total", "total_end_adjusted", "gap", "runtime_s", "mean_lateness_min"):
        if c in ilp.columns:
            ilp[c] = pd.to_numeric(ilp[c], errors="coerce")
    ilp["cell"] = ilp.apply(lambda r: f"{r['layout']}/{r['timetable']}/{r['variant']}", axis=1)
    cols = ["total", "total_end_adjusted", "gap_vs_best_rule_pct", "gap_vs_best_rule_pct_end_adjusted",
            "gap_vs_best_rule_notransfer_pct", "gap_vs_r2_pct", "gap_vs_r5_transfer_pct", "gap_vs_r5_pct", "served_share",
            "n_late_over_60min", "mean_lateness_min", "transfers_used", "batteries_moved", "gap", "runtime_s",
            "best_rule_total", "best_rule_total_end_adjusted"]
    summ = long_summary(ilp, ["targets", "layout", "timetable", "variant"], [c for c in cols if c in ilp.columns])
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    # paired quantities per seed
    def tot(layout: str, tt: str, targets: str, switch: str, col: str) -> Dict[int, float]:
        sub = ilp[(ilp.layout == layout) & (ilp.timetable == tt) & (ilp.targets == targets) & (ilp.variant == switch)]
        return {int(s): float(v) for s, v in zip(sub.seed, sub[col]) if v == v}
    paired: List[Dict[str, Any]] = []

    def add(label: str, group: Dict[str, Any], a: Dict[int, float], b: Dict[int, float]) -> None:
        d = [a[s] - b[s] for s in sorted(set(a) & set(b))]
        m, h, n = mean_ci(d)
        if n:
            paired.append({**group, "metric": label, "mean_diff": m, "ci95": h, "n_pairs": n})
    for targets in X2.TARGETS:
        for layout in X2.LAYOUTS:
            for col, suffix in (("total", ""), ("total_end_adjusted", "_end_adjusted")):
                none = tot(layout, "any", targets, "none", col)
                for tt in X2.TIMETABLES:
                    free = tot(layout, tt, targets, "free", col)
                    add(f"value_of_transfers{suffix}", {"targets": targets, "layout": layout, "timetable": tt}, none, free)
                add(f"cyclic_minus_r3{suffix}", {"targets": targets, "layout": layout, "timetable": "cyclic-r3"},
                    tot(layout, "cyclic", targets, "free", col), tot(layout, "r3", targets, "free", col))
                if layout != "colocated":
                    for tt, sw in (("any", "none"), ("r3", "free"), ("cyclic", "free")):
                        add(f"separation_cost{suffix}", {"targets": targets, "layout": layout, "timetable": f"{tt}/{sw}"},
                            tot(layout, tt, targets, sw, col), tot("colocated", tt, targets, sw, col))
            for tt, sw in (("any", "none"), ("r3", "free"), ("cyclic", "free")):
                if targets == "written":
                    for col, suffix in (("total", ""), ("total_end_adjusted", "_end_adjusted")):
                        add(f"price_of_recovery{suffix}", {"targets": "written-relaxed", "layout": layout, "timetable": f"{tt}/{sw}"},
                            tot(layout, tt, "written", sw, col), tot(layout, tt, "relaxed", sw, col))
    base = df[df.method == "baseline"].copy()
    base["total"] = pd.to_numeric(base["total"], errors="coerce")
    for targets in X2.TARGETS:
        for layout in X2.LAYOUTS:
            for tt in X2.TIMETABLES:
                sub = base[(base.layout == layout) & (base.timetable == tt) & (base.targets == targets)]
                by = {lab: {int(s): float(v) for s, v in zip(g.seed, g.total) if v == v} for lab, g in sub.groupby("variant")}
                for lab in ("r5_transfer", "r2_reorder", "r5", "r5_range"):
                    if lab in by and "r2" in by:
                        add(f"{lab}_minus_r2", {"targets": targets, "layout": layout, "timetable": tt}, by[lab], by["r2"])
    pdf = pd.DataFrame(paired)
    pdf.to_csv(os.path.join(out_dir, "paired.csv"), index=False)
    st = ilp.groupby(["targets", "variant", "timetable", "status"]).size().reset_index(name="n")
    L = ["# R6 transfers -- value of transfers and hub separation under P 60, w 18, v 15", "",
         "r5_x2_transfers design on the repriced usd4h (eBaaS) instances, seeds 0-4; aggregated ILP, Threads 3, "
         "Seed 0, TimeLimit 300 s; libraries price-checked.  Means with exact Student-t 95 % half-widths over seeds; "
         "every difference paired per seed.  `RESULTS_x2.md` holds the round-5 report layout on these records.", "",
         "## Solver status", "", C.markdown_table(st, list(st.columns), 0), ""]
    key = summ[summ.metric.isin(["gap_vs_best_rule_pct_end_adjusted", "total_end_adjusted", "served_share",
                                 "n_late_over_60min", "transfers_used", "gap"])]
    L += ["## ILP per cell (seed means +- t 95 %)", "",
          C.markdown_table(key, ["targets", "layout", "timetable", "variant", "metric", "mean", "ci95", "n"], 3), ""]
    if not pdf.empty:
        L += ["## Paired differences (USD per window; per seed, then mean +- t 95 %)", "",
              C.markdown_table(pdf, ["targets", "layout", "timetable", "metric", "mean_diff", "ci95", "n_pairs"], 3), ""]
    nopt = ilp[ilp.status != "OPTIMAL"]
    L += ["## Anomalies", "", f"* {len(nopt)} ILP row(s) not OPTIMAL (max gap {C.fmt(nopt.gap.max(), 4)})" if len(nopt) else "* none",
          "", "Files: records.jsonl, results.csv, summary.csv (long), paired.csv, RESULTS_x2.md, figs/, instances/, schedules/."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ===========================================================================
# Part 2b: stress (X5 core / boundary / LP under the base pricing)
# ===========================================================================
STRESS_FAMILIES: Dict[str, Tuple[int, int]] = {"r5_stress4h": (6, 48), "r5_stress4h_k8": (8, 48),
                                               "r5_stress4h_k10": (10, 48), "r5_stress8h": (6, 96)}


def _priced_builder(family: str, seed: int, pr: Dict[str, Any], stage: str, over: Dict[str, Any]) -> Callable[[], Instance]:
    def build() -> Instance:
        inst = C.make_instance(family, seed=int(seed), **over)
        inst.meta["family_size"] = family
        return R6.priced(inst, pr, stage)
    return build


def plan_stress_r6(pr: Dict[str, Any], smoke: bool, seeds: Optional[Sequence[int]] = None) -> List[X5.Case]:
    """Ordered cases: LP-only relaxed cells (K6 seeds 3-4, K8 seeds 0-4; cheap), K6 written (ILP
    300 s + LP), the boundary grid on K6 seeds 0-2 (300 s; rho0.5_R1 = the written cell, solved
    once) whose reference cell rho0_R0 (= the relaxed K6 cell) is ONE case per seed carrying both
    the LP and the ILP (``r5_x5_stress.Runner.note_case`` dedups on (sub, cell, seed, target, key),
    so a separate LP-only note of the same cell would hide the ILP row from the analysis), then
    the relaxed K10 (600 s + LP) and stress8h (600 s + LP) cells.  ``seeds`` restricts every block."""
    tag = "smoke" if smoke else "full"
    over = {"n_bikes": 3, "window_h": 2.0} if smoke else {}

    def case(sub_cell: str, family: str, seed: int, target: str, tl: Optional[float], lp: bool, phase: str,
             info: Dict[str, Any]) -> X5.Case:
        k, H = STRESS_FAMILIES[family]
        if smoke:
            k, H = 3, 24
        return X5.Case("stress", sub_cell, int(seed), target, f"r6:{family}:{seed}:{tag}",
                       _priced_builder(family, seed, pr, "stress", over), tl, lp, phase,
                       {"family_size": family, "pricing": pr["label"], **info}, k, H)

    def sd(default: Sequence[int]) -> List[int]:
        d = list(default)
        return [s for s in seeds if s in d] if seeds is not None else d

    out: List[X5.Case] = []
    if smoke:
        out.append(case("r5_stress4h_K3", "r5_stress4h", 0, X5.RELAXED, SMOKE_TL, True, "relaxed", {"K": 3}))
        out.append(case("r5_stress4h_K3", "r5_stress4h", 0, "written", SMOKE_TL, True, "written", {"K": 3}))
        return out
    for s in sd([x for x in SEEDS5 if x not in SEEDS3]):
        out.append(case("r5_stress4h_K6", "r5_stress4h", s, X5.RELAXED, None, True, "lp_only", {"K": 6}))
    for s in sd(SEEDS5):
        out.append(case("r5_stress4h_k8_K8", "r5_stress4h_k8", s, X5.RELAXED, None, True, "lp_only", {"K": 8}))
    for s in sd(SEEDS5):
        out.append(case("r5_stress4h_K6", "r5_stress4h", s, "written", STRESS_TL, True, "written", {"K": 6}))
    labels = list(X5.BOUNDARY_FIRST) + [lab for lab in X5.boundary_specs() if lab not in X5.BOUNDARY_FIRST]
    for lab in labels:
        for s in sd(SEEDS3):
            # the reference rho0_R0 (= relaxed K6) carries the LP of the shadow-price block too
            out.append(case("r5_stress4h_K6", "r5_stress4h", s, lab, STRESS_TL, lab == X5.RELAXED, "boundary",
                            {"K": 6, "boundary_spec": list(X5.boundary_specs()[lab])}))
    for s in sd(SEEDS5):
        out.append(case("r5_stress4h_k10_K10", "r5_stress4h_k10", s, X5.RELAXED, STRESS_TL_LONG, True, "relaxed", {"K": 10}))
    for s in sd(SEEDS3):
        out.append(case("r5_stress8h_K6", "r5_stress8h", s, X5.RELAXED, STRESS_TL_LONG, True, "relaxed", {"K": 6, "H": 96}))
    return out


def run_x5_stage(stage: str, plan: List[X5.Case], args: argparse.Namespace) -> None:
    out_dir = stage_dir(stage, args.smoke, args.out_root)
    if args.dry_run:
        exp = sum(X5.est_case_s(c)[0] for c in plan) / 60.0
        print(json.dumps({"stage": stage, "out_dir": out_dir, "cases": len(plan), "x5_estimate_min": round(exp, 1),
                          "expected_wall_min_r6": EST_MIN[stage], "budget_min": args.budget_min, "pricing": BASE["label"]}, indent=1))
        for c in plan:
            print("  ", c.cell, c.seed, c.target, c.ilp_tl, "LP" if c.lp else "")
        return
    X5.sched_cols = R6._sched_cols_r6
    X5.LIB_CACHE[stage] = 2
    runner = R6.StressRunner(out_dir, stage, BASE, args.threads)
    if args.smoke:
        runner.lp_time_limit = X5.SMOKE_LP_TL
    print(f"# R6 {stage}: {len(plan)} cases -> {out_dir}", flush=True)
    runner.run_plan(stage, plan, args.budget_min * 60.0)
    print(analyse(stage, args.smoke, args.out_root), flush=True)


def _psweep_relaxed_by_md5(smoke: bool, root: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Relaxed ILP rows of r5_stress4h at the base pricing in ``r6_penalty/psweep`` by demand md5
    (the same instances as the K6 cells here; the retried rows win)."""
    p = os.path.join(R6.stage_dir("psweep", smoke, root), RECORDS)
    out: Dict[str, Dict[str, Any]] = {}
    for k, r in X1.last_per_key(C.load_jsonl(p)).items():
        if k[0] == "r5_stress4h" and k[1] == BASE["label"] and k[4] == "relaxed" and k[5] == "ilp" and r.get("demand_md5"):
            out[r["demand_md5"]] = r
    return out


def add_lp_cols(df: pd.DataFrame, out_dir: str) -> pd.DataFrame:
    """``r6_penalty.wide_r6`` carries the rule and ILP rows only; this adds the ``LP`` row of each
    case (``lp_*`` fields prefixed ``LP_``, plus ``LP_status``) by ``key_md5`` (last done row)."""
    lp: Dict[str, Dict[str, Any]] = {k[0]: r for k, r in R6.last_done_rows(os.path.join(out_dir, RECORDS)).items()
                                     if k[1] == "LP"}
    if df.empty or not lp:
        return df
    cols: Dict[str, List[Any]] = {}
    keys = sorted({k for r in lp.values() for k in r if k.startswith("lp_")})
    for k in keys + ["status"]:
        cols[f"LP_{k}"] = [lp.get(str(key), {}).get(k) for key in df["key_md5"]]
    return df.assign(**cols)


def analyse_stress(out_dir: str, smoke: bool = False, root: Optional[str] = None) -> str:
    df = add_lp_cols(R6.wide_r6(out_dir), out_dir)
    if df.empty:
        return "stress: no cases"
    df.to_csv(os.path.join(out_dir, "cases_wide.csv"), index=False)
    df["best_ea"] = R6._best_ea(df)
    df["ilp_ea"] = pd.to_numeric(df.get("ilp_total_end_adjusted"), errors="coerce")
    df["ilp_raw"] = pd.to_numeric(df.get("ilp_total"), errors="coerce")
    df["gap_best_ea_pct"] = [gap_pct(b, i) for b, i in zip(df["best_ea"], df["ilp_ea"])]
    L = ["# R6 stress -- stressed family, price of recovery, boundary grid, LP shadow prices (P 60, w 18, v 15)", "",
         "r5_x5_stress machinery on the repriced instances (aggregated ILP, Threads 3, Seed 0; identical cells solved "
         "once by content key).  best rule = per-instance min over the rules (end-adjusted); mean +- exact t 95 % over "
         "seeds; deltas paired per seed.", ""]
    # core: relaxed headline cells (K10, 8h) and the K6 written cell
    core = df[df.phase.isin(["relaxed", "written"])]
    cols = ["ilp_ea", "best_ea", "gap_best_ea_pct", "ilp_gap", "ilp_served_share", "best_rule_served_share",
            "ilp_n_late_over_60min", "best_rule_n_late_over_60min", "ilp_mean_lateness_min", "ilp_runtime_s"]
    if not core.empty:
        s = long_summary(core, ["cell", "target"], cols)
        s.to_csv(os.path.join(out_dir, "summary_core.csv"), index=False)
        L += ["## Core cells (relaxed control) and the K6 written cell", "",
              C.markdown_table(s[s.metric.isin(["ilp_ea", "best_ea", "gap_best_ea_pct", "ilp_gap", "ilp_served_share"])],
                               ["cell", "target", "metric", "mean", "ci95", "n"], 3), ""]
        st = core.groupby(["cell", "target"])["ilp_status"].agg(lambda x: json.dumps(x.value_counts().to_dict()))
        L += ["ILP status: " + "; ".join(f"{k} {v}" for k, v in st.items()), ""]
    # price of recovery on K6: written - relaxed (relaxed = the boundary rho0_R0 row here, else psweep)
    ps = _psweep_relaxed_by_md5(smoke, root)
    por: List[Dict[str, Any]] = []
    k6 = df[(df.cell == "r5_stress4h_K6")]
    for _, r in k6[k6.target == "written"].iterrows():
        rel = k6[(k6.target == X5.RELAXED) & (k6.seed == r.seed)]
        src, rel_ea, rel_raw, rel_status = None, None, None, None
        if not rel.empty and _num(rel.iloc[0].get("ilp_ea")) is not None:
            src, rel_ea, rel_raw, rel_status = "stress", _num(rel.iloc[0]["ilp_ea"]), _num(rel.iloc[0]["ilp_raw"]), rel.iloc[0].get("ilp_status")
        elif r.get("demand_md5") in ps:
            p = ps[r["demand_md5"]]
            src, rel_ea, rel_raw, rel_status = "psweep", _num(p.get("total_end_adjusted")), _num(p.get("total")), p.get("status")
        por.append({"seed": int(r.seed), "written_ea": _num(r.ilp_ea), "relaxed_ea": rel_ea, "relaxed_source": src,
                    "written_status": r.get("ilp_status"), "relaxed_status": rel_status,
                    "price_of_recovery_end_adjusted": None if rel_ea is None or _num(r.ilp_ea) is None else _num(r.ilp_ea) - rel_ea,
                    "price_of_recovery": None if rel_raw is None or _num(r.ilp_raw) is None else _num(r.ilp_raw) - rel_raw,
                    "lp_spare_written": _num(r.get("LP_lp_spare_value_mean")), "lp_charger_written": _num(r.get("LP_lp_charger_value_mean"))})
    pdf = pd.DataFrame(por)
    pdf.to_csv(os.path.join(out_dir, "price_of_recovery.csv"), index=False)
    if not pdf.empty:
        m, h, n = mean_ci(pdf["price_of_recovery_end_adjusted"].tolist())
        L += ["## Price of recovery on stress4h 6 bikes (ILP written - ILP relaxed, end-adjusted)", "",
              C.markdown_table(pdf, list(pdf.columns), 2), "", f"mean {C.fmt(m, 2)} +- {C.fmt(h, 2)} USD (n {n}).", ""]
    # boundary grid
    bnd = df[df.phase == "boundary"].copy()
    if not bnd.empty:
        ref = bnd[bnd.target == X5.RELAXED].set_index("seed")
        for col, out_col in (("ilp_raw", "price_of_recovery"), ("ilp_ea", "price_of_recovery_end_adjusted")):
            bnd[out_col] = [(_num(r[col]) - _num(ref.at[r["seed"], col])) if r["seed"] in ref.index and _num(r[col]) is not None
                            and _num(ref.at[r["seed"], col]) is not None else None for _, r in bnd.iterrows()]
        bs = long_summary(bnd, ["target"], ["ilp_raw", "ilp_ea", "price_of_recovery", "price_of_recovery_end_adjusted",
                                            "ilp_gap", "ilp_served_share", "ilp_n_late_over_60min"])
        bs.to_csv(os.path.join(out_dir, "summary_boundary.csv"), index=False)
        L += ["## Boundary grid (rho x R_end + periodic) on stress4h 6 bikes seeds 0-2: price of recovery vs rho0_R0 (paired)", "",
              C.markdown_table(bs[bs.metric.isin(["price_of_recovery", "price_of_recovery_end_adjusted", "ilp_gap"])],
                               ["target", "metric", "mean", "ci95", "n"], 3), ""]
    # LP shadow prices
    lp_cols = [c for c in ("LP_lp_spare_value_mean", "LP_lp_spare_value_min", "LP_lp_spare_value_max",
                           "LP_lp_charger_value_mean", "LP_lp_charger_value_min", "LP_lp_charger_value_max", "LP_lp_obj")
               if c in df.columns]
    lp = df[df[lp_cols].notna().any(axis=1)] if lp_cols else df.iloc[0:0]
    if not lp.empty:
        ls = long_summary(lp, ["cell", "target"], lp_cols)
        ls.to_csv(os.path.join(out_dir, "summary_lp.csv"), index=False)
        L += ["## LP shadow prices: operating value of one more spare / charger per site (USD per window)", "",
              C.markdown_table(ls[ls.metric.isin(["LP_lp_spare_value_mean", "LP_lp_charger_value_mean"])],
                               ["cell", "target", "metric", "mean", "ci95", "n"], 3), ""]
    errs = [r for r in C.load_jsonl(os.path.join(out_dir, RECORDS)) if r.get("status") in ("ERROR", C.SKIPPED_BUDGET)]
    L += ["## Anomalies", "", f"* {len(errs)} ERROR / SKIPPED_BUDGET row(s)" if errs else "* none", "",
          "Files: records.jsonl, cases.jsonl, results.csv, cases_wide.csv, summary_core.csv, price_of_recovery.csv, "
          "summary_boundary.csv, summary_lp.csv."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ===========================================================================
# Part 2c: rolling_ext (lambda 0 / 20 and the forecast plan)
# ===========================================================================
ROLL_EST_S: Dict[Tuple[str, str], float] = {("usd4h", "rolling"): 70.0, ("usd4h", "forecast"): 145.0,
                                            ("r5_stress4h", "rolling"): 100.0, ("r5_stress4h", "forecast"): 300.0}


def rolling_ext_items(smoke: bool, seeds: Optional[Sequence[int]]) -> List[Tuple[str, int, str, float]]:
    """``(case, seed, policy, lookahead_min)`` interleaved over seeds and cases (budget stops leave
    balanced seeds): rolling lambda 0, rolling lambda 20, forecast lambda 10."""
    if smoke:
        return [("usd4h", 0, "rolling", 0.0), ("usd4h", 0, "forecast", FORECAST_LAMBDA)]
    pols = [("rolling", lam) for lam in ROLL_LAMBDAS_EXT] + [("forecast", FORECAST_LAMBDA)]
    out: List[Tuple[str, int, str, float]] = []
    for case, seed in R6.rolling_items(False, seeds):
        for pol, lam in pols:
            out.append((case, seed, pol, lam))
    return out


def run_rolling_ext(args: argparse.Namespace) -> None:
    from ebike_swap_sim.rolling import BootstrapForecast, rolling_horizon
    out_dir = stage_dir("rolling_ext", args.smoke, args.out_root)
    items = rolling_ext_items(args.smoke, args.seeds)
    path = os.path.join(out_dir, RECORDS)
    if args.dry_run:
        print(json.dumps({"stage": "rolling_ext", "out_dir": out_dir, "items": items, "W": ROLL_W, "k": ROLL_K,
                          "window_time_limit": ROLL_WINDOW_TL, "n_scenarios": X3.N_SCENARIOS, "pool": "all",
                          "expected_wall_min": EST_MIN["rolling_ext"]}, indent=1))
        return
    C.ensure_dir(out_dir)
    rows: List[Dict[str, Any]] = C.load_jsonl(path)
    done = {(r["case"], int(r["seed"]), r["policy"], float(r["lookahead_min"])) for r in rows if r.get("status") == "ROLLING"}
    wtl = min(ROLL_WINDOW_TL, 20.0) if args.smoke else ROLL_WINDOW_TL
    budget = C.WallBudget(args.budget_min * 60.0, margin_s=60.0, min_solve_s=30.0)
    cache: Dict[Tuple[str, int], Tuple[Instance, Any, Dict[str, Any], int]] = {}
    for case, seed, pol, lam in items:
        if (case, seed, pol, lam) in done:
            continue
        base = {"case": case, "seed": seed, "mult": 1.0, "policy": pol, "targets": "relaxed", "lookahead_min": lam,
                "W": ROLL_W, "k": ROLL_K, "threads": args.threads, "n_scenarios": X3.N_SCENARIOS if pol == "forecast" else 0,
                "pool": "all" if pol == "forecast" else None, **R6.price_cols(BASE, "rolling_ext")}
        est = ROLL_EST_S[(case, pol)]
        if budget.remaining() - budget.margin < est:
            row = {**base, "status": C.SKIPPED_BUDGET, "skip_reason": f"wall budget (estimate {est:.0f} s)"}
        else:
            try:
                if (case, seed) not in cache:
                    cache.clear()
                    gc.collect()
                    inst0, prun = R6.build_case(case, seed, 1.0, args.smoke)
                    inst = R6.priced(inst0, BASE, "rolling_ext")
                    inst.meta["name"] = f"r6-{inst0.meta['name']}-{BASE['label']}"
                    lib = C.build_library(inst, prun, strict=False)[0]
                    chk = cm.check_lib_prices(inst, lib)["n_checked"]
                    cache[(case, seed)] = (inst, lib, prun, chk)
                inst, lib, prun, chk = cache[(case, seed)]
                fc = BootstrapForecast(inst, pool="all") if pol == "forecast" else None
                t0 = time.perf_counter()
                res = rolling_horizon(inst, W=ROLL_W, k=ROLL_K, lookahead_min=lam, lib=lib, arc_options=prun,
                                      final_targets="relaxed", forecast=fc,
                                      n_scenarios=X3.N_SCENARIOS if fc is not None else 1, forecast_seed=int(seed),
                                      aggregate=True, threads=args.threads, time_limit=wtl, params=dict(C.ILP_PARAMS_R3))
                rt = time.perf_counter() - t0
                summ = res.summary()
                met = metrics(res.inst, res.lib, res.schedule)
                row = {**base, **{k: v for k, v in summ.items() if not k.startswith("param_")},
                       "status": "ROLLING", "runtime": rt, "demand_md5": C.demand_md5(inst), "name": inst.meta["name"],
                       "n_bikes": len(inst.bikes), "n_orders": len(inst.orders), "window_time_limit": wtl,
                       "families": summ.get("violations"), "served_share": met.get("served_share"),
                       "n_late": met.get("n_late"), "lib_price_checked_arcs": chk,
                       "forecast_source": getattr(fc, "source", None) if fc else None,
                       "n_window_aggregate": sum(1 for w in res.windows if w.get("aggregate")),
                       "windows": [{kk: w.get(kk) for kk in ("t0", "W", "status", "gap", "runtime", "n_known", "n_forecast",
                                                             "n_busy", "plan_fix", "fallback", "aggregate")} for w in res.windows],
                       "notes": res.notes, **C.flatten_cost(res.cost), **C.flatten_r5(met),
                       **R6.lateness_cols(res.inst, res.lib, res.schedule)}
                del res
                gc.collect()
            except Exception as exc:  # noqa: BLE001
                row = {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-3000:]}
        C.append_jsonl(path, row)
        rows.append(C.jsonable(row))
        C.write_csv(rows, os.path.join(out_dir, "results.csv"))
        print(json.dumps({k: C.jsonable(row.get(k)) for k in ("case", "seed", "policy", "lookahead_min", "status", "total",
                                                              "total_end_adjusted", "served_share", "runtime")}), flush=True)
    cache.clear()
    _wall_file(out_dir, "rolling_ext", budget, {"smoke": args.smoke})
    print(analyse_rolling_ext(out_dir, args.smoke, args.out_root), flush=True)


def analyse_rolling_ext(out_dir: str, smoke: bool = False, root: Optional[str] = None) -> str:
    """Per seed: offline relaxed ILP and best rule (headline / psweep rows), lambda 10 (r6_penalty
    rolling), lambda 0 / 20 and the forecast plan (this stage); VoI, VoC online, share surviving,
    and paired differences to lambda 10; mean +- exact t over seeds."""
    mine = [r for r in C.load_jsonl(os.path.join(out_dir, RECORDS)) if r.get("status") == "ROLLING"]
    if not mine:
        return "rolling_ext: no records"
    lam10 = [r for r in C.load_jsonl(os.path.join(R6.stage_dir("rolling", smoke, root), RECORDS)) if r.get("status") == "ROLLING"]
    ref: Dict[Tuple, Dict[str, Any]] = {}
    for st in ("headline", "psweep"):
        for k, r in X1.last_per_key(C.load_jsonl(os.path.join(R6.stage_dir(st, smoke, root), RECORDS))).items():
            if k[1] == BASE["label"] and float(k[3]) == 1.0 and X1.row_is_done(r):
                ref.setdefault(k, r)
    pol_rows: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
    for r in lam10:
        pol_rows[(r["case"], int(r["seed"]), "lam10")] = r
    for r in mine:
        lab = "forecast10" if r["policy"] == "forecast" else f"lam{float(r['lookahead_min']):g}"
        pol_rows[(r["case"], int(r["seed"]), lab)] = r
    pols = ("lam0", "lam10", "lam20", "forecast10")
    out: List[Dict[str, Any]] = []
    for case, seed in sorted({(k[0], k[1]) for k in pol_rows}):
        off = ref.get(R6.grid_key(case, BASE["label"], seed, 1.0, "relaxed", "ilp"))
        rules = [ref.get(R6.grid_key(case, BASE["label"], seed, 1.0, "relaxed", m)) for m in R6.RULES]
        rules = [x for x in rules if x is not None and x.get("status") == "POLICY"]
        rec: Dict[str, Any] = {"case": case, "seed": seed, "offline_status": off.get("status") if off else None,
                               "offline_mip_gap": _num(off.get("mip_gap")) if off else None}
        for basis, col in (("ea", "total_end_adjusted"), ("raw", "total")):
            o = _num(off.get(col)) if off else None
            b = min((_num(x.get(col)) for x in rules if _num(x.get(col)) is not None), default=None)
            rec[f"offline_{basis}"], rec[f"best_rule_{basis}"] = o, b
            rec[f"headline_{basis}"] = None if b is None or o is None else b - o
            for p in pols:
                r = pol_rows.get((case, seed, p))
                v = _num(r.get(col)) if r else None
                rec[f"{p}_{basis}"] = v
                rec[f"voi_{p}_{basis}"] = None if v is None or o is None else v - o
                rec[f"voc_online_{p}_{basis}"] = None if v is None or b is None else b - v
                rec[f"share_surviving_{p}_{basis}"] = (None if rec[f"headline_{basis}"] in (None, 0) or rec[f"voc_online_{p}_{basis}"] is None
                                                       else rec[f"voc_online_{p}_{basis}"] / rec[f"headline_{basis}"])
                rec[f"gap_{p}_vs_best_{basis}_pct"] = gap_pct(b, v)
                if p != "lam10":
                    v10 = _num(pol_rows[(case, seed, "lam10")].get(col)) if (case, seed, "lam10") in pol_rows else None
                    rec[f"diff_{p}_minus_lam10_{basis}"] = None if v is None or v10 is None else v - v10
        for p in pols:
            r = pol_rows.get((case, seed, p))
            rec[f"{p}_served_share"] = _num(r.get("served_share")) if r else None
            rec[f"{p}_n_late_over_60min"] = _num(r.get("n_late_over_60min")) if r else None
            rec[f"{p}_runtime"] = _num(r.get("runtime")) if r else None
            rec[f"{p}_demand_md5_match"] = (off is not None and r is not None and off.get("demand_md5") == r.get("demand_md5"))
        out.append(rec)
    per = pd.DataFrame(out).sort_values(["case", "seed"])
    per.to_csv(os.path.join(out_dir, "per_instance.csv"), index=False)
    cols = [c for c in per.columns if c not in ("case", "seed", "offline_status") and not c.endswith("_match")]
    summ = long_summary(per, ["case"], cols)
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    L = ["# R6 rolling_ext -- lookahead 0 / 20 min and the bootstrap-forecast battery plan under P 60, w 18, v 15", "",
         f"W {ROLL_W}, k {ROLL_K}, window TimeLimit {ROLL_WINDOW_TL:.0f} s, aggregated windows, relaxed final targets; "
         "forecast = BootstrapForecast(pool all), 1 scenario, lambda 10.  Lambda 10 from r6_penalty/rolling; offline "
         "relaxed ILP and the rules from headline / psweep (same instances).  Per seed: VoI = rolling - offline, VoC online "
         "= best rule - rolling, share surviving = VoC online / headline; differences to lambda 10 paired per seed; "
         "mean +- exact t 95 %.", ""]
    show = [f"{q}_{p}_ea" for p in pols for q in ("voc_online", "share_surviving")] + \
           [f"diff_{p}_minus_lam10_ea" for p in pols if p != "lam10"] + [f"{p}_served_share" for p in pols]
    s2 = summ[summ.metric.isin(show)]
    if not s2.empty:
        L += [C.markdown_table(s2, ["case", "metric", "mean", "ci95", "n"], 3), ""]
    miss = [c for c in per.columns if c.endswith("_match")]
    n_bad = int((~per[miss].fillna(False).astype(bool)).sum().sum()) if miss else 0
    L += ["## Anomalies", "", f"* {n_bad} policy row(s) without a matching offline reference (md5 / missing)" if n_bad else "* none",
          "", "Files: records.jsonl, results.csv, per_instance.csv, summary.csv."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ===========================================================================
# Part 2d: pack (rule-only pack-size cells of the fleet sweep)
# ===========================================================================
PACKS: Tuple[float, ...] = X5.FLEET_PACKS          # 0.5, 0.75, 1.0 kWh


def plan_pack_r6(pr: Dict[str, Any], smoke: bool, seeds: Optional[Sequence[int]] = None) -> List[X5.Case]:
    """K x B x pack grid (48 orders), relaxed control, rules only (no ILP), seed-major."""
    sd = [0] if smoke else (list(seeds) if seeds is not None else list(SEEDS3))
    Ks = (4,) if smoke else R6.FLEET_K
    Bs = (1,) if smoke else R6.FLEET_B
    packs = (0.5,) if smoke else PACKS
    out: List[X5.Case] = []
    for seed in sd:
        for k in Ks:
            for pack in packs:
                for B in Bs:
                    def b(seed: int = seed, k: int = k, B: int = B, pack: float = pack) -> Instance:
                        return R6.priced(gen.make_fleet_sweep_instance("r5_stress4h", seed=seed, n_bikes=k, B=B, pack_kwh=pack),
                                         pr, "pack")
                    out.append(X5.Case("pack", f"K{k}_B{B}_pack{pack:g}", seed, X5.RELAXED,
                                       f"r6:pack:{pr['label']}:{seed}:{k}:{B}:{pack:g}", b, None, False, "grid",
                                       {"K": k, "B_per_site": B, "pack_kwh": pack, "pricing": pr["label"]}, k, 48))
    return out


def analyse_pack(out_dir: str, smoke: bool = False, root: Optional[str] = None) -> str:
    df = R6.wide_r6(out_dir)
    if df.empty:
        return "pack: no cases"
    df.to_csv(os.path.join(out_dir, "cases_wide.csv"), index=False)
    fleet_dir = R6.stage_dir("fleet", smoke, root)
    fl = R6.wide_r6(fleet_dir) if os.path.exists(os.path.join(fleet_dir, RECORDS)) else pd.DataFrame()
    both = pd.concat([df.assign(stage_src="pack"), fl.assign(stage_src="fleet")], ignore_index=True, sort=False) if not fl.empty \
        else df.assign(stage_src="pack")
    for c in ("K", "B_per_site", "pack_kwh", "allocated_per_bike_window"):
        both[c] = pd.to_numeric(both.get(c), errors="coerce")
    both["best_ea"] = R6._best_ea(both)
    both["ilp_ea"] = pd.to_numeric(both.get("ilp_total_end_adjusted"), errors="coerce")
    both["alloc"] = both["allocated_per_bike_window"]
    both["best_system_cost"] = both["best_ea"] + both["alloc"] * both["K"]
    both["ilp_system_cost"] = both["ilp_ea"] + both["alloc"] * both["K"]
    both.to_csv(os.path.join(out_dir, "cases_wide_joined.csv"), index=False)
    cols = ["best_ea", "best_system_cost", "best_rule_served_share", "best_rule_n_late_over_60min", "ilp_ea", "ilp_system_cost"]
    summ = long_summary(both, ["pack_kwh", "K", "B_per_site"], cols)
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    fr = pd.DataFrame()
    try:
        fl2 = both.rename(columns={})
        fl2["best_rule_total_end_adjusted"] = both["best_ea"]
        fr = X5.fleet_frontier(fl2)
        fr.to_csv(os.path.join(out_dir, "fleet_frontier.csv"), index=False)
    except Exception as exc:  # noqa: BLE001
        print(f"# fleet_frontier failed: {exc}", flush=True)
    # cost-minimal design per pack (best rule; seed-mean system cost on complete cells)
    opt: List[Dict[str, Any]] = []
    g = both.dropna(subset=["best_system_cost"])
    if not g.empty:
        m = g.groupby(["pack_kwh", "K", "B_per_site"]).agg(system_cost=("best_system_cost", "mean"),
                                                            served_share=("best_rule_served_share", "mean"),
                                                            n=("best_system_cost", "size")).reset_index()
        for pack, mp in m.groupby("pack_kwh"):
            mp = mp[mp.n == mp.n.max()]
            top = mp.sort_values("system_cost").iloc[0]
            ci = mean_ci(g[(g.pack_kwh == pack) & (g.K == top.K) & (g.B_per_site == top.B_per_site)]["best_system_cost"].tolist())
            opt.append({"pack_kwh": pack, "K": int(top.K), "B_per_site": int(top.B_per_site), "system_cost_mean": top.system_cost,
                        "system_cost_ci95": ci[1], "served_share_mean": top.served_share, "n_seeds": int(top.n)})
    odf = pd.DataFrame(opt)
    odf.to_csv(os.path.join(out_dir, "cost_minimal_design_by_pack.csv"), index=False)
    L = ["# R6 pack -- pack-size axis of the fleet sweep (rules), joined to the 0.6 kWh grid (P 60, w 18, v 15)", "",
         "Rule-only cells K {4, 6, 8, 10} x B {1..4} x pack {0.5, 0.75, 1.0} kWh, seeds 0-2, relaxed control, repriced; "
         "the 0.6 kWh grid (rules + ILP) from r6_penalty/fleet.  System cost = end-adjusted best-rule total (spare set-up "
         "(27) included) + K x allocated bike (+ rider) cost per window.  Means +- exact t 95 % over seeds.", "",
         "## Cost-minimal design per pack (best rule, seed-mean system cost)", "",
         C.markdown_table(odf, list(odf.columns), 2) if not odf.empty else "-", ""]
    if not fr.empty:
        fb = fr[fr.policy == "best_rule"]
        L += ["## Iso-cost frontier (best rule): marginal value of a bike vs a spare per (pack, K, B)", "",
              C.markdown_table(fb, [c for c in ["pack_kwh", "K", "B_per_site", "V", "dV_bike", "dV_spare", "alloc_per_bike", "bike_net",
                                                "cheaper_lever"] if c in fb.columns], 2), ""]
    sm = summ[summ.metric.isin(["best_system_cost", "best_rule_served_share"])]
    L += ["## Grid means", "", C.markdown_table(sm, ["pack_kwh", "K", "B_per_site", "metric", "mean", "ci95", "n"], 2), ""]
    errs = [r for r in C.load_jsonl(os.path.join(out_dir, RECORDS)) if r.get("status") in ("ERROR", C.SKIPPED_BUDGET)]
    L += ["## Anomalies", "", f"* {len(errs)} ERROR / SKIPPED_BUDGET row(s)" if errs else "* none", "",
          "Files: records.jsonl, cases.jsonl, results.csv, cases_wide.csv, cases_wide_joined.csv, summary.csv, "
          "fleet_frontier.csv, cost_minimal_design_by_pack.csv."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ===========================================================================
# Part 2e: levers_ext (charger speed, second swap position, 1-spare lock-out, power cap)
# ===========================================================================
LEVER_FAMILY, LEVER_K = "r5_stress4h_k8", 8
LOCKOUT_ONE: Tuple[float, ...] = (0.05, 0.10)      # both round to one battery of the 6 spares -> one solve


def plan_levers_ext_r6(pr: Dict[str, Any], smoke: bool, seeds: Optional[Sequence[int]] = None) -> List[X5.Case]:
    """eps 50 Wh (x2 charger speed), M 2 (second swap position), lock-out of one spare (shares
    0.05 and 0.10, identical content -> solved once) on the repriced r5_stress4h_k8, relaxed
    control, ILP 600 s; the reference / P0 / 2-spare lock-out rows come from r6_penalty/levers."""
    over = {"window_h": 2.0, "n_bikes": 4} if smoke else {}
    sd = [0] if smoke else (list(seeds) if seeds is not None else list(SEEDS5))
    tl = SMOKE_TL if smoke else LEVERS_TL
    k = 4 if smoke else LEVER_K
    out: List[X5.Case] = []
    for seed in sd:
        def ref(seed: int = seed) -> Instance:
            return C.make_instance(LEVER_FAMILY, seed=seed, **over)

        def b_eps(seed: int = seed, e: float = 50.0) -> Instance:
            inst = gen.charger_speed_variants("r5_stress4h", seed=seed, eps_wh=(e,), n_bikes=k, **({"window_h": 2.0} if smoke else {}))[e]
            inst.meta["family"] = f"r5_stress4h_eps{e:g}"
            return R6.priced(inst, pr, "levers_ext")

        def b_pos(seed: int = seed, M: int = 2) -> Instance:
            return R6.priced(gen.swap_position_variants(ref(seed), M_values=(M,))[M], pr, "levers_ext")

        def b_lock(seed: int = seed, share: float = 0.05) -> Instance:
            base = ref(seed)
            n = X5.n_locked(base, share)
            return R6.priced(gen.add_battery_lockout(base, share=share, slots=X5.lockout_slots(base, n, seed), seed=seed),
                             pr, "levers_ext")

        common = {"family_size": LEVER_FAMILY, "pricing": pr["label"]}
        tag = f"{pr['label']}:{seed}:{'smoke' if smoke else 'full'}"
        out.append(X5.Case("levers_ext", "eps50", seed, X5.RELAXED, f"r6:eps50:{tag}", b_eps, tl, False, "charger_speed",
                           {**common, "lever": "charger_speed", "lever_value": 50.0, "eps_wh": 50.0}, k, 48))
        if smoke:
            continue
        out.append(X5.Case("levers_ext", "M2", seed, X5.RELAXED, f"r6:M2:{tag}", b_pos, tl, False, "swap_positions",
                           {**common, "lever": "swap_positions", "lever_value": 2, "M": 2}, k, 48))
        for share in LOCKOUT_ONE:
            out.append(X5.Case("levers_ext", f"lockout{share:g}", seed, X5.RELAXED, f"r6:lock{share:g}:{tag}",
                               (lambda s=seed, sh=share: b_lock(s, sh)), tl, False, "lockout",
                               {**common, "lever": "lockout", "lever_value": share, "lockout_share": share, "lockout_n_target": 1}, k, 48))
    return out


def analyse_levers_ext(out_dir: str, smoke: bool = False, root: Optional[str] = None) -> str:
    df = R6.wide_r6(out_dir)
    if df.empty:
        return "levers_ext: no cases"
    lev_dir = R6.stage_dir("levers", smoke, root)
    lv = R6.wide_r6(lev_dir) if os.path.exists(os.path.join(lev_dir, RECORDS)) else pd.DataFrame()
    both = pd.concat([lv.assign(stage_src="levers"), df.assign(stage_src="levers_ext")], ignore_index=True, sort=False) if not lv.empty \
        else df.assign(stage_src="levers_ext")
    both["best_ea"] = R6._best_ea(both)
    both["ilp_ea"] = pd.to_numeric(both.get("ilp_total_end_adjusted"), errors="coerce")
    both["ilp_raw"] = pd.to_numeric(both.get("ilp_total"), errors="coerce")
    both["best_raw"] = pd.to_numeric(both.get("best_rule_total"), errors="coerce")
    both["gap_best_ea_pct"] = [gap_pct(b, i) for b, i in zip(both["best_ea"], both["ilp_ea"])]
    both.to_csv(os.path.join(out_dir, "cases_wide_joined.csv"), index=False)
    ref = both[both.cell == "reference"].set_index("seed")
    for col in ("ilp_ea", "best_ea", "ilp_raw", "best_raw"):
        both[f"delta_{col}"] = [(_num(r[col]) - _num(ref.at[r["seed"], col])) if r["seed"] in ref.index and _num(r[col]) is not None
                                and _num(ref.at[r["seed"], col]) is not None else None for _, r in both.iterrows()]
    cols = ["ilp_ea", "best_ea", "gap_best_ea_pct", "delta_ilp_ea", "delta_best_ea", "delta_ilp_raw", "ilp_gap", "ilp_served_share",
            "best_rule_served_share", "ilp_n_late_over_60min", "ilp_mean_lateness_min", "ilp_lockout_end_share_excl_sink", "ilp_runtime_s"]
    summ = long_summary(both, ["lever", "cell"], [c for c in cols if c in both.columns])
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    dc = pd.DataFrame()
    try:
        dc = X5.demand_charge_table(both)          # reference (cap p_ch) and P0 rows, per seed and policy
        dc.to_csv(os.path.join(out_dir, "demand_charge_proxy.csv"), index=False)
    except Exception as exc:  # noqa: BLE001
        print(f"# demand_charge_table failed: {exc}", flush=True)
    L = ["# R6 levers_ext -- station levers on stress4h-K8 under P 60, w 18, v 15", "",
         "Relaxed control, aggregated ILP, Threads 3, Seed 0, TimeLimit 600 s (reference rows re-solved by "
         "--retry-unsolved at 1800 s where present).  Reference, P0 (no on-site charging) and the 2-spare lock-out from "
         "r6_penalty/levers; charger speed x2 (eps 50 Wh), second swap position (M 2) and the 1-spare lock-out (shares "
         "0.05 / 0.10 = one battery) from this stage.  Deltas vs the reference paired per seed; mean +- exact t 95 %.", ""]
    L += [C.markdown_table(summ[summ.metric.isin(["ilp_ea", "best_ea", "gap_best_ea_pct", "delta_ilp_ea", "delta_best_ea", "ilp_gap"])],
                           ["lever", "cell", "metric", "mean", "ci95", "n"], 3), ""]
    st = both.groupby("cell")["ilp_status"].agg(lambda s: json.dumps(s.value_counts().to_dict()))
    L += ["ILP status per cell: " + "; ".join(f"{k} {v}" for k, v in st.items()), ""]
    if not dc.empty:
        ds = long_summary(dc, ["policy", "usd_per_kw_month"], ["V_P0", "V_Pch", "best_P_kw", "best_total"])
        L += ["## Site power cap with the demand-charge proxy (P_j in {0, p_ch}; tariffs are assumptions)", "",
              C.markdown_table(ds, ["policy", "usd_per_kw_month", "metric", "mean", "ci95", "n"], 2), ""]
    errs = [r for r in C.load_jsonl(os.path.join(out_dir, RECORDS)) if r.get("status") in ("ERROR", C.SKIPPED_BUDGET)]
    L += ["## Anomalies", "", f"* {len(errs)} ERROR / SKIPPED_BUDGET row(s)" if errs else "* none", "",
          "Files: records.jsonl, cases.jsonl, results.csv, cases_wide_joined.csv, summary.csv, demand_charge_proxy.csv."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ===========================================================================
# Part 2f: compliance (M4 on the repriced Manhattan scenarios)
# ===========================================================================
def load_jsonl_lenient(path: str) -> List[Dict[str, Any]]:
    """``common.load_jsonl`` for a file another process may still be appending to (the O2 run
    writes ``records.jsonl`` / ``cache/index.jsonl`` per budget): a line that does not parse (a
    half-written last line) is skipped with a note instead of raising."""
    if not os.path.exists(path):
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                print(f"# {path}: line {n} does not parse (partially written?); skipped", flush=True)
    return out


def o2_best_layout(records_path: str = O2_RECORDS, target: str = COMPLIANCE_TARGET, m: float = COMPLIANCE_M) -> Dict[str, Any]:
    """The last ``budget_result`` row of ``target`` at budget ``m`` x the budget unit of the O2
    Manhattan run.  Raises ``FileNotFoundError`` / ``LookupError`` with a clear message."""
    from experiments import r6_o2_siting as O2
    if not os.path.exists(records_path):
        raise FileNotFoundError(f"O2 Manhattan records not found: {records_path} (the certified siting run has not "
                                f"written its results; pass --layout-key or wait for the run)")
    unit = O2.BUDGET_UNIT
    found = None
    for r in load_jsonl_lenient(records_path):
        if r.get("kind") != "budget_result" or r.get("target") != target:
            continue
        b = _num(r.get("budget"))
        if b is None or abs(b / unit - float(m)) > 1e-6:
            continue
        found = r
    if found is None:
        raise LookupError(f"no budget_result row with target {target!r} at m = {m:g} (budget {m * unit:.0f}) in {records_path}: "
                          f"the O2 {target} target has not finished; pass --layout-key or wait")
    if not found.get("best_layout"):
        raise LookupError(f"the O2 budget_result row at m = {m:g} ({target}) has no best_layout: {json.dumps(found)[:300]}")
    return found


def seed_cache(src: str, dst: str, layout_keys: Sequence[str]) -> int:
    """Copy the lower-level cache rows (and schedule files) of ``layout_keys`` from the O2 cache
    into this stage's cache so that priced layouts are not solved again.  Returns the number of
    rows copied; never writes into ``src``."""
    idx = os.path.join(src, "index.jsonl")
    if not os.path.exists(idx):
        return 0
    C.ensure_dir(os.path.join(dst, "schedules"))
    have = {r.get("key") for r in C.load_jsonl(os.path.join(dst, "index.jsonl"))}
    n = 0
    for r in load_jsonl_lenient(idx):
        if r.get("layout_key") not in layout_keys or r.get("key") in have:
            continue
        sp = r.get("schedule_path")
        if sp and not os.path.exists(sp):
            # The index may carry an absolute path written on another machine (laptop vs server);
            # the schedule file itself lives in <src>/schedules/ under the same basename.
            alt = os.path.join(src, "schedules", os.path.basename(sp))
            if os.path.exists(alt):
                sp = alt
        if sp and os.path.exists(sp):
            tgt = os.path.join(dst, "schedules", os.path.basename(sp))
            if not os.path.exists(tgt):
                shutil.copyfile(sp, tgt)
            r = {**r, "schedule_path": tgt}
        C.append_jsonl(os.path.join(dst, "index.jsonl"), r)
        have.add(r.get("key"))
        n += 1
    return n


def compliance_layouts(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """``[{'label', 'layout_key', 'source'}]``: the O2 best written-target layout at m 2 (or
    ``--layout-key``) and the round-5 layout; in smoke mode the toy layouts (a ``--layout-key``
    must then open toy candidates T1..T4: the smoke evaluator knows no Manhattan candidate)."""
    if args.smoke:
        return [{"label": "smoke_a", "layout_key": args.layout_key or "T1:SC:B1:C1|T2:S:B1:C0", "source": "smoke"},
                {"label": "smoke_b", "layout_key": "T1:SC:B2:C1", "source": "smoke"}]
    if args.layout_key:
        first = {"label": "o2_best_m2", "layout_key": args.layout_key, "source": "cli --layout-key"}
    else:
        r = o2_best_layout(args.o2_records)
        first = {"label": "o2_best_m2", "layout_key": r["best_layout"], "source": f"{args.o2_records} budget_result {COMPLIANCE_TARGET} m 2",
                 "o2_UB": r.get("UB"), "o2_LB": r.get("LB"), "o2_gap": r.get("gap"), "o2_certified": r.get("certified")}
    out = [first]
    if first["layout_key"] != R5_LAYOUT:
        out.append({"label": "r5_chosen", "layout_key": R5_LAYOUT, "source": "outputs/r5_x6_manhattan/chosen_layout.json"})
    return out


def build_compliance_evaluator(args: argparse.Namespace, cache_dir: str) -> Tuple[Any, Dict[str, Any]]:
    """The repriced ``r5_manhattan`` evaluator of ``r6_o2_siting.build_manhattan`` (written targets,
    aggregated, reposition all_candidates) or the toy evaluator in smoke mode."""
    from ebike_swap_sim import bilevel as BL
    from ebike_swap_sim import sites_nyc as S
    from experiments import r6_o2_siting as O2
    pr = BASE
    if args.smoke:
        scen = []
        for s in (0, 1):
            base = S.toy_base_instance(s, candidates=O2.TOY_CANDIDATES)
            scen.append(cm.reprice_orders(base, P=pr["P"], w=pr["w"], v=pr["v"], source="r6_fill compliance smoke"))
        ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, params={"Seed": 0, "MIPGap": 0.0},
                                    cache_dir=cache_dir, reposition="all_candidates", aggregate=True)
        return ev, {"family": "toy", "seeds": [0, 1], "time_limit": 30.0}
    family = S.R5_MANHATTAN_FAMILY
    cands = S.family_candidates(family)
    depots = S.family_depots(family, cands)
    seeds = list(args.seeds) if args.seeds is not None else [0, 1, 2]
    scen = []
    for s in seeds:
        base = S.make_base_instance(int(s), cands, family=family, depots=depots, n_bikes=int(S.SITING_FAMILIES[family]["n_bikes"]))
        rep = cm.reprice_orders(base, P=pr["P"], w=pr["w"], v=pr["v"], source=f"experiments/r6_fill.py compliance; {pr['label']}")
        if C.demand_md5(rep) != C.demand_md5(base):
            raise AssertionError("repricing changed the demand side")
        scen.append(rep)
    spec = S.spec_from_instance(scen[0])
    ev = BL.LowerLevelEvaluator(scen, spec, time_limit=float(args.time_limit or 300.0), time_limit_hub=600.0, threads=args.threads,
                                params=dict(C.ILP_PARAMS_R3), cache_dir=cache_dir, relaxed_targets=False, verbose=True,
                                reposition="all_candidates", aggregate=True, keep_libraries=2)
    return ev, {"family": family, "seeds": seeds, "time_limit": float(args.time_limit or 300.0), "time_limit_hub": 600.0,
                "pricing": {k: pr[k] for k in ("P", "w", "v")}, "demand_md5": ev.demand_md5}


def _compliance_done(rows: Sequence[Dict[str, Any]], layout_key: str, alphas: Sequence[float], draws: Sequence[int],
                     n_scen: int) -> Dict[str, bool]:
    have = {(r.get("layout_key"), r.get("kind"), r.get("policy")) for r in rows if r.get("status") not in ("ERROR", C.SKIPPED_BUDGET)}
    cells = {(r.get("scenario"), float(r.get("alpha_c")), r.get("draw")) for r in rows
             if r.get("kind") == "compliance" and r.get("layout_key") == layout_key and r.get("status") == "OK"}
    need = {(s, float(a), d) for s in range(n_scen) for a in alphas for d in draws}
    return {"ilp": (layout_key, "price", "ilp") in have, "selfish": (layout_key, "price", "selfish") in have,
            "baseline": (layout_key, "price", "baseline") in have, "sweep": need <= cells}


def run_compliance(args: argparse.Namespace) -> None:
    from ebike_swap_sim import bilevel as BL
    out_dir = stage_dir("compliance", args.smoke, args.out_root)
    path = os.path.join(out_dir, RECORDS)
    alphas = list(args.psi) if args.psi else list(PSI)
    draws = list(DRAWS) if not args.smoke else [0, 1]
    try:
        layouts = compliance_layouts(args)
        layout_error = None
    except (FileNotFoundError, LookupError) as exc:
        layouts, layout_error = [], f"{type(exc).__name__}: {exc}"
    plan = {"stage": "compliance", "out_dir": out_dir, "layouts": layouts, "psi": alphas, "draws": draws, "station_plan": "plan",
            "target": COMPLIANCE_TARGET, "pricing": BASE["label"], "expected_wall_min": EST_MIN["compliance"],
            "o2_records": args.o2_records, "o2_cache": args.o2_cache, "layout_error": layout_error}
    if args.dry_run:
        print(json.dumps(plan, indent=1, default=str))
        return
    if layout_error:
        raise SystemExit(f"compliance: {layout_error}")
    C.ensure_dir(out_dir)
    cache_dir = os.path.join(out_dir, "cache")
    keys = [l["layout_key"] for l in layouts]
    n_seeded = seed_cache(args.o2_cache, cache_dir, keys) if (not args.smoke and os.path.isdir(args.o2_cache)) else 0
    ev, cfg = build_compliance_evaluator(args, cache_dir)
    known = set(getattr(ev, "cand_node", {}) or {})
    for lay_info in layouts:
        locs = [it[0] for it in BL.Layout.from_key(lay_info["layout_key"]).open]
        bad = sorted(set(locs) - known)
        if known and bad:
            raise SystemExit(f"compliance: layout {lay_info['layout_key']!r} ({lay_info['source']}) opens unknown candidate(s) {bad}; "
                             f"the {cfg.get('family')} evaluator knows {sorted(known)}"
                             + (" (smoke mode uses the toy candidates: pass a T1..T4 key or drop --layout-key)" if args.smoke else ""))
    budget = C.WallBudget(args.budget_min * 60.0, margin_s=60.0, min_solve_s=30.0)
    ev.wall = budget
    rows = C.load_jsonl(path)
    C.append_jsonl(path, {"kind": "plan", **plan, **{k: v for k, v in cfg.items() if k != "demand_md5"},
                          "demand_md5": cfg.get("demand_md5"), "cache_rows_seeded_from_o2": n_seeded})

    def emit(row: Dict[str, Any]) -> None:
        row = {"stage": "compliance", "source": "r6_fill", **R6.price_cols(BASE, "compliance"), **row}
        C.append_jsonl(path, C.jsonable(row))
        rows.append(C.jsonable(row))
        print(json.dumps({k: C.jsonable(row.get(k)) for k in ("kind", "layout_key", "policy", "alpha_c", "status", "V", "served_share")
                          if k in row}), flush=True)

    for lay_info in layouts:
        key = lay_info["layout_key"]
        lay = BL.Layout.from_key(key)
        done = _compliance_done(rows, key, alphas, draws, ev.n_scenarios)
        for pol in ("ilp", "selfish", "baseline"):
            if done[pol]:
                continue
            t0 = time.perf_counter()
            try:
                r = ev.evaluate(lay, pol)
                emit({"kind": "price", "layout_key": key, "layout_label": lay_info["label"], "layout_source": lay_info["source"], "policy": pol,
                      "status": r.get("status"), "V": r.get("V"), "C_setup": r.get("C_setup"), "investment": r.get("investment"),
                      "opex": r.get("opex"), "statuses": r.get("statuses"), "gaps": r.get("gaps"), "served_share": r.get("served_share"),
                      "n_late": r.get("n_late"), "n_cache_hits": r.get("n_cache_hits"), "n_solves": r.get("n_solves"),
                      "equilibrium": [x.get("equilibrium") for x in r.get("rows", [])] if pol == "selfish" else None,
                      "runtime_s": time.perf_counter() - t0, **{k: lay_info[k] for k in lay_info if k.startswith("o2_")}})
            except Exception as exc:  # noqa: BLE001
                emit({"kind": "price", "layout_key": key, "policy": pol, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}",
                      "traceback": traceback.format_exc()[-3000:]})
            for lr in ev.new_rows:
                emit({"kind": "lower_level", **{k: v for k, v in lr.items() if not k.startswith("_")}})
            ev.new_rows.clear()
        if not done["sweep"]:
            if budget.remaining() < budget.margin + 60.0:
                emit({"kind": "compliance_summary", "layout_key": key, "status": C.SKIPPED_BUDGET, "skip_reason": "wall budget"})
                continue
            try:
                cs = BL.compliance_sweep(ev, lay, alphas=alphas, seeds=draws, station_plan="plan")
                for r in cs["rows"]:
                    emit({"kind": "compliance", "layout_key": key, "layout_label": lay_info["label"], "station_plan": "plan",
                          "C_setup": cs.get("C_setup"), **r})
                for r in cs["summary"]:
                    emit({"kind": "compliance_summary", "layout_key": key, "layout_label": lay_info["label"], "station_plan": "plan",
                          "C_setup": cs.get("C_setup"), **r})
            except Exception as exc:  # noqa: BLE001
                emit({"kind": "compliance_summary", "layout_key": key, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}",
                      "traceback": traceback.format_exc()[-3000:]})
            for lr in ev.new_rows:
                emit({"kind": "lower_level", **{k: v for k, v in lr.items() if not k.startswith("_")}})
            ev.new_rows.clear()
    C.write_csv(rows, os.path.join(out_dir, "results.csv"))
    _wall_file(out_dir, "compliance", budget, {"smoke": args.smoke, "layouts": keys})
    print(analyse_compliance(out_dir), flush=True)


def analyse_compliance(out_dir: str) -> str:
    rows = C.load_jsonl(os.path.join(out_dir, RECORDS))
    if not rows:
        return "compliance: no records"
    price: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in rows:
        if r.get("kind") == "price" and r.get("status") not in ("ERROR",):
            price[(r["layout_key"], r["policy"])] = r
    comp = [r for r in rows if r.get("kind") == "compliance" and r.get("status") == "OK"]
    labels = {r["layout_key"]: r.get("layout_label") for r in rows if r.get("kind") in ("price", "compliance") and r.get("layout_key")}
    per: List[Dict[str, Any]] = []
    for key in sorted({r["layout_key"] for r in comp}):
        rs = [r for r in comp if r["layout_key"] == key]
        setup = _num(rs[0].get("C_setup")) or 0.0
        scen = sorted({int(r["scenario"]) for r in rs})
        p = 1.0 / len(scen)
        v_ilp = _num((price.get((key, "ilp")) or {}).get("V"))
        v_sf = _num((price.get((key, "selfish")) or {}).get("V"))
        v_r2 = _num((price.get((key, "baseline")) or {}).get("V"))
        for a in sorted({float(r["alpha_c"]) for r in rs}):
            for d in sorted({int(r["draw"]) for r in rs if float(r["alpha_c"]) == a}):
                cell = {int(r["scenario"]): r for r in rs if float(r["alpha_c"]) == a and int(r["draw"]) == d}
                if set(cell) != set(scen):
                    continue
                V = setup + sum(p * float(cell[s]["opex"]) for s in scen)
                share = sum(p * float(cell[s]["served_share"]) for s in scen)
                rec = {"layout_key": key, "layout_label": labels.get(key), "alpha_c": a, "draw": d, "V": V, "served_share": share,
                       "n_defected": sum(int(cell[s]["n_defected"]) for s in scen) / len(scen),
                       "V_ilp": v_ilp, "V_selfish": v_sf, "V_r2": v_r2,
                       "V_minus_ilp": None if v_ilp is None else V - v_ilp,
                       "gap_vs_selfish_pct": gap_pct(v_sf, V), "gap_vs_r2_pct": gap_pct(v_r2, V)}
                rec["share_of_selfish_gap_recovered"] = (None if v_sf is None or v_ilp is None or abs(v_sf - v_ilp) < 1e-9
                                                         else (v_sf - V) / (v_sf - v_ilp))
                per.append(rec)
    pdf = pd.DataFrame(per)
    pdf.to_csv(os.path.join(out_dir, "per_draw.csv"), index=False)
    summ = long_summary(pdf, ["layout_key", "alpha_c"], ["V", "served_share", "n_defected", "V_minus_ilp", "gap_vs_selfish_pct",
                                                         "gap_vs_r2_pct", "share_of_selfish_gap_recovered"]) if not pdf.empty else pd.DataFrame()
    summ.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    pr_rows = [{"layout_key": k[0], "layout_label": labels.get(k[0]), "policy": k[1], "status": r.get("status"), "V": r.get("V"),
                "served_share": r.get("served_share"), "statuses": json.dumps(r.get("statuses")), "gaps": json.dumps(r.get("gaps")),
                "n_solves": r.get("n_solves"), "o2_UB": r.get("o2_UB"), "o2_certified": r.get("o2_certified")}
               for k, r in sorted(price.items())]
    prdf = pd.DataFrame(pr_rows)
    prdf.to_csv(os.path.join(out_dir, "layout_values.csv"), index=False)
    L = ["# R6 compliance -- M4 compliance sweep, selfish equilibrium and rule r2 on Manhattan under P 60, w 18, v 15", "",
         "Repriced r5_manhattan scenarios (3 seeds, written targets, aggregated ILP, Threads 3, Seed 0, TimeLimit 300 s / 600 s "
         "with a charge-only hub).  V = allocated set-up + mean scenario OPEX.  Compliance: share psi of the riders follows "
         "the ILP plan (station layer = plan), the others follow follower E (r5_selfish); 3 draws of the compliant set per psi; "
         "V per draw, then mean +- exact t 95 % over draws.  psi = 1 reproduces the ILP value.", "",
         "## Layout values under the followers", "", C.markdown_table(prdf, list(prdf.columns), 2) if not prdf.empty else "-", ""]
    if not summ.empty:
        L += ["## Compliance curve (mean +- t 95 % over draws)", "",
              C.markdown_table(summ[summ.metric.isin(["V", "served_share", "share_of_selfish_gap_recovered", "gap_vs_selfish_pct"])],
                               ["layout_key", "alpha_c", "metric", "mean", "ci95", "n"], 3), ""]
    errs = [r for r in rows if r.get("status") in ("ERROR", C.SKIPPED_BUDGET)]
    L += ["## Anomalies", "", f"* {len(errs)} ERROR / SKIPPED_BUDGET row(s)" if errs else "* none", "",
          "Files: records.jsonl, results.csv, per_draw.csv, summary.csv, layout_values.csv, cache/."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ===========================================================================
# Part 2g: rl_seeds (PPO seeds 1 and 2 of the rl stage)
# ===========================================================================
def rl_seed_argv(args: argparse.Namespace, sub_dir: str) -> List[str]:
    argv = ["--out", sub_dir, "--no-ilp", "--no-written", "--wall-budget-min", str(args.budget_min / max(1, len(args.ppo_seeds))),
            "--ilp-time-limit", str(R6.RL_ILP_TIME_LIMIT)]
    if args.smoke:
        argv += ["--smoke", "--families", "nyc4h_stress2", "--riders", "r2"]
    if args.dry_run:
        argv.append("--dry-run")
    if args.seeds is not None:
        argv += ["--test-seeds", ",".join(str(s) for s in args.seeds)]
    return argv


def _merge_rl_rows(stage_path: str, sub_path: str, ppo_seed: int) -> int:
    have = {(r.get("ppo_seed"), r.get("kind"), r.get("family"), str(r.get("seed")), r.get("method"), r.get("train_id"))
            for r in C.load_jsonl(stage_path)}
    n = 0
    for r in C.load_jsonl(sub_path):
        k = (ppo_seed, r.get("kind"), r.get("family"), str(r.get("seed")), r.get("method"), r.get("train_id"))
        if k in have:
            continue
        C.append_jsonl(stage_path, {**r, "ppo_seed": ppo_seed, "stage": "rl_seeds", "source": "r6_fill"})
        have.add(k)
        n += 1
    return n


def run_rl_seeds(args: argparse.Namespace) -> None:
    out_dir = stage_dir("rl_seeds", args.smoke, args.out_root)
    X7 = R6._install_rl_loader(BASE)
    orig_seed = X7.PPO_SEED
    src_inst = os.path.join(R6.stage_dir("rl", args.smoke, args.out_root), "instances")
    for k in args.ppo_seeds:
        sub = os.path.join(out_dir, f"seed{k}")
        if not args.dry_run:
            C.ensure_dir(os.path.join(sub, "instances"))
            if os.path.isdir(src_inst):           # the repriced instances of the rl stage (checked on load)
                for f in os.listdir(src_inst):
                    if f.endswith(".json") and not os.path.exists(os.path.join(sub, "instances", f)):
                        shutil.copyfile(os.path.join(src_inst, f), os.path.join(sub, "instances", f))
        X7.PPO_SEED = int(k)
        try:
            print(f"# R6 rl_seeds: PPO seed {k} -> {sub}", flush=True)
            X7.main(rl_seed_argv(args, sub))
        finally:
            X7.PPO_SEED = orig_seed
        if not args.dry_run:
            n = _merge_rl_rows(os.path.join(out_dir, RECORDS), os.path.join(sub, RECORDS), int(k))
            print(f"# rl_seeds: {n} row(s) of PPO seed {k} appended to the stage records", flush=True)
    if not args.dry_run:
        print(analyse_rl_seeds(out_dir, args.smoke, args.out_root), flush=True)


def analyse_rl_seeds(out_dir: str, smoke: bool = False, root: Optional[str] = None) -> str:
    """Three PPO seeds: per (family, rider, ppo_seed) the mean over test seeds of the agent's
    end-adjusted total and its paired differences to the replay of its rider rule, the best rule
    and the relaxed ILP (reference rows of r6_penalty/rl); then mean +- exact t over the PPO
    seeds (n 3) and pooled over seeds x test seeds."""
    from experiments import r5_x7_rl as X7
    mine = C.load_jsonl(os.path.join(out_dir, RECORDS))
    ref_rows = C.load_jsonl(os.path.join(R6.stage_dir("rl", smoke, root), RECORDS))
    if not mine and not ref_rows:
        return "rl_seeds: no records"
    ref = X7.last_per_key([r for r in ref_rows if r.get("kind") != "train"])
    by_seed: Dict[int, List[Dict[str, Any]]] = {0: [r for r in ref_rows]}
    for r in mine:
        by_seed.setdefault(int(r.get("ppo_seed", -1)), []).append(r)
    derived: Dict[int, Dict[Tuple, Dict[str, Any]]] = {}
    for k, rows in by_seed.items():
        last = X7.last_per_key([r for r in rows if r.get("kind") != "train"])
        derived[k] = last
    per: List[Dict[str, Any]] = []
    trains: List[Dict[str, Any]] = []
    for k, rows in by_seed.items():
        for r in rows:
            if r.get("kind") == "train":
                trains.append({"ppo_seed": k, "family": r["family"], "rider": r.get("rider_variant"), "status": r.get("status"),
                               "timesteps_done": r.get("timesteps_done"), "runtime_s": r.get("runtime_s"),
                               "return_first100": r.get("return_first100"), "return_last100": r.get("return_last100"),
                               "train_id": r.get("train_id")})
        last = derived[k]
        fams = sorted({kk[1] for kk in last if kk[0] == "rl"})
        for fam in fams:
            seeds = sorted({int(kk[2]) for kk in last if kk[0] == "rl" and kk[1] == fam})
            for rider in ("r2", "r5"):
                for s in seeds:
                    rl = last.get(("rl", fam, str(s), f"rl_ppo[{rider}]"))
                    if rl is None or rl.get("total") is None:
                        continue
                    rep = last.get(("rl", fam, str(s), f"replay[{rider}]"))
                    ilp = ref.get(("ilp", fam, str(s), "ilp_relaxed"))
                    rules = [ref.get(("rule", fam, str(s), f"rule_{m}")) for m in X7.BEST_RULE_OVER]
                    rules = [x for x in rules if x is not None and x.get("total") is not None]
                    best = min((_num(x.get("total_end_adjusted")) for x in rules), default=None)
                    ea = _num(rl.get("total_end_adjusted"))
                    rec = {"ppo_seed": k, "family": fam, "rider": rider, "test_seed": s, "rl_ea": ea,
                           "replay_ea": _num(rep.get("total_end_adjusted")) if rep else None,
                           "best_rule_ea": best, "ilp_ea": _num(ilp.get("total_end_adjusted")) if ilp else None,
                           "ilp_status": ilp.get("status") if ilp else None, "rl_served_share": _num(rl.get("served_share")),
                           "rl_n_late_over_60min": _num(rl.get("n_late_over_60min"))}
                    rec["rl_minus_replay"] = None if ea is None or rec["replay_ea"] is None else ea - rec["replay_ea"]
                    rec["rl_minus_best_rule"] = None if ea is None or best is None else ea - best
                    rec["rl_minus_ilp"] = None if ea is None or rec["ilp_ea"] is None else ea - rec["ilp_ea"]
                    rec["gap_rl_vs_ilp_pct"] = gap_pct(ea, rec["ilp_ea"])
                    rec["gap_best_rule_vs_ilp_pct"] = gap_pct(best, rec["ilp_ea"])
                    per.append(rec)
    pdf = pd.DataFrame(per)
    pdf.to_csv(os.path.join(out_dir, "per_test_seed.csv"), index=False)
    tdf = pd.DataFrame(trains)
    tdf.to_csv(os.path.join(out_dir, "training.csv"), index=False)
    cols = ["rl_ea", "replay_ea", "best_rule_ea", "ilp_ea", "rl_minus_replay", "rl_minus_best_rule", "rl_minus_ilp", "gap_rl_vs_ilp_pct",
            "gap_best_rule_vs_ilp_pct", "rl_served_share", "rl_n_late_over_60min"]
    within = long_summary(pdf, ["family", "rider", "ppo_seed"], cols) if not pdf.empty else pd.DataFrame()
    within.to_csv(os.path.join(out_dir, "summary_by_ppo_seed.csv"), index=False)
    across = pd.DataFrame()
    if not within.empty:
        w = within.pivot_table(index=["family", "rider", "ppo_seed"], columns="metric", values="mean", aggfunc="first").reset_index()
        across = long_summary(w, ["family", "rider"], [c for c in cols if c in w.columns])
        across.to_csv(os.path.join(out_dir, "summary_across_ppo_seeds.csv"), index=False)
    pooled = long_summary(pdf, ["family", "rider"], cols) if not pdf.empty else pd.DataFrame()
    pooled.to_csv(os.path.join(out_dir, "summary_pooled.csv"), index=False)
    L = ["# R6 rl_seeds -- PPO over three training seeds under P 60, w 18, v 15", "",
         "Seed 0 = r6_penalty/rl; seeds 1 and 2 = this stage (same 200,000 steps, training seeds 1000-1019, test seeds "
         "0-9, hyper-parameters a7_rl.PPO_DEFAULTS).  Reference rows (relaxed ILP 300 s, rules) from r6_penalty/rl.  "
         "Per PPO seed: mean over the test seeds (paired differences per test seed); across: mean +- exact t 95 % over "
         "the PPO seeds (n 3); pooled: over seeds x test seeds.", ""]
    if not tdf.empty:
        L += ["## Training", "", C.markdown_table(tdf, list(tdf.columns), 2), ""]
    if not across.empty:
        L += ["## Across PPO seeds (n = number of PPO seeds with the cell)", "",
              C.markdown_table(across[across.metric.isin(["rl_ea", "rl_minus_replay", "rl_minus_best_rule", "rl_minus_ilp", "gap_rl_vs_ilp_pct"])],
                               ["family", "rider", "metric", "mean", "ci95", "n"], 3), ""]
    if not within.empty:
        L += ["## Per PPO seed (means over test seeds)", "",
              C.markdown_table(within[within.metric.isin(["rl_ea", "rl_minus_replay", "rl_minus_best_rule", "gap_rl_vs_ilp_pct"])],
                               ["family", "rider", "ppo_seed", "metric", "mean", "ci95", "n"], 3), ""]
    L += ["Files: records.jsonl (seeds 1-2, with ppo_seed), seed<k>/ (X7 folders), per_test_seed.csv, training.csv, "
          "summary_by_ppo_seed.csv, summary_across_ppo_seeds.csv, summary_pooled.csv."]
    return write_md(os.path.join(out_dir, "RESULTS.md"), L)


# ===========================================================================
# Part 3: lanes
# ===========================================================================
LANE_HEADER = '''#!/usr/bin/env bash
# r6_fill lane {n}: {desc}
# Start only after the certified O2 Manhattan siting run (outputs/r6_o2/manhattan) has finished:
# every lane runs Gurobi at Threads 3 and the four lanes together need the machine.
# caffeinate -i keeps the laptop awake: Gurobi counts wall-clock time, so a sleep truncates solves.
set -u
cd "{pkg}" || exit 1
export PYTHONPATH=.
LD="{ld}"
ST="$LD/lane_{n}.status"
echo "lane {n} start $(date -u +%Y-%m-%dT%H:%M:%SZ) pid $$" >> "$ST"
run() {{ local name=$1; shift
  echo "$name START $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ST"
  caffeinate -i "$@" > "$LD/$name.log" 2>&1
  local rc=$?
  echo "$name EXIT $rc $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ST"
}}
# wait_for_o2: polls every 5 min for the O2 written m=2 budget_result, at most O2_WAIT_MAX_POLLS
# times ({wait_h:g} h); returns 1 on timeout (O2 crashed, aborted or stopped at a smaller budget), and
# the lane then runs compliance on the round-5 layout only (--layout-key) so its analyse still runs.
wait_for_o2() {{ local n=0
  until python3 experiments/r6_fill.py --check-o2 > /dev/null 2>&1; do
    n=$((n + 1))
    if [ "$n" -ge {max_polls} ]; then echo "O2 wait timed out after $n polls $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ST"; return 1; fi
    echo "waiting for the O2 written m=2 result $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ST"; sleep 300; done; }}
'''
#: Bound of ``wait_for_o2`` (polls of 5 min): 12 h.
O2_WAIT_MAX_POLLS = 144
#: The final analyse of every lane: the new stages, the retried stages (retries.csv) and the
#: r6_penalty rolling analysis, whose tables join the headline / psweep relaxed-ILP rows that the
#: retries replace (network and rl do not join them).
ANALYSE_ALL = ("python3 experiments/r6_fill.py --stage all --analyse; "
               "python3 experiments/r6_fill.py --retry-unsolved --stage headline,psweep,vsweep,fleet,levers --analyse; "
               "python3 experiments/r6_penalty.py --stage rolling --analyse")


def lane_plan() -> List[Dict[str, Any]]:
    """Four lanes balanced by the expected minutes (retries from ``retry_plan`` where the records
    exist, else the digest counts); rl_seeds alone in lane 4; compliance last in its lane after
    ``wait_for_o2``."""
    def retry_min(stage: str) -> Tuple[float, int]:
        p = os.path.join(R6.stage_dir(stage, False, None), RECORDS)
        n = {"headline": 3, "psweep": 23, "vsweep": 2, "fleet": 20, "levers": 11}[stage]
        tl = RETRY_TL[stage]
        if os.path.exists(p):
            sel = select_grid_retries(p) if stage in R6.GRID_STAGES else stress_retry_selection(p, tl)[0]
            n = len(sel)
        return n * (tl * (0.85 if stage in ("psweep", "fleet") else 1.0) + 90.0) / 60.0, n

    def retry(stage: str) -> Dict[str, Any]:
        m, n = retry_min(stage)
        return {"name": f"r6_retry_{stage}", "command": f"python3 experiments/r6_fill.py --retry-unsolved --stage {stage}",
                "out_dir": R6.stage_dir(stage, False, None), "expected_wall_min": round(m), "n_retries": n}

    def new(stage: str) -> Dict[str, Any]:
        return {"name": f"r6_{stage}", "command": f"python3 experiments/r6_fill.py --stage {stage}",
                "out_dir": stage_dir(stage, False), "expected_wall_min": EST_MIN[stage]}

    lanes = [
        {"lane": "lane_1", "desc": "levers retry (1800 s), levers_ext, pack",
         "commands": [retry("levers"), new("levers_ext"), new("pack")]},
        {"lane": "lane_2", "desc": "psweep retry (600 s), stress, headline retry (600 s)",
         "commands": [retry("psweep"), new("stress"), retry("headline")]},
        {"lane": "lane_3", "desc": "transfers, fleet retry (600 s), rolling_ext, vsweep retry (600 s), then compliance after the O2 result",
         "commands": [new("transfers"), retry("fleet"), new("rolling_ext"), retry("vsweep"),
                      {**new("compliance"), "wait_for_o2": True}]},
        {"lane": "lane_4", "desc": "rl_seeds alone (PPO seeds 1 and 2; torch threads 3)", "commands": [new("rl_seeds")]},
    ]
    for lane in lanes:
        lane["commands"].append({"name": f"r6_analyse_{lane['lane']}", "command": ANALYSE_ALL, "expected_wall_min": 2})
        lane["expected_wall_min"] = round(sum(c["expected_wall_min"] for c in lane["commands"]))
    return lanes


def write_lanes(ld: str = LANES_DIR) -> Dict[str, Any]:
    C.ensure_dir(ld)
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lanes = lane_plan()
    for i, lane in enumerate(lanes, start=1):
        lines = [LANE_HEADER.format(n=i, desc=lane["desc"], pkg=pkg, ld=ld, max_polls=O2_WAIT_MAX_POLLS,
                                    wait_h=O2_WAIT_MAX_POLLS * 5 / 60.0)]
        for c in lane["commands"]:
            cmd = c["command"]
            if c.get("wait_for_o2"):
                lines += ["wait_for_o2", "if [ $? -eq 0 ]; then", f"  run {c['name']} {cmd}", "else",
                          f"  run {c['name']} {cmd} --layout-key '{R5_LAYOUT}'", "fi"]
            elif c["name"].startswith("r6_analyse"):
                lines.append(f'run {c["name"]} bash -c "{cmd}"')
            else:
                lines.append(f"run {c['name']} {cmd}")
            c["log"] = os.path.join(ld, c["name"] + ".log")
        lines.append('echo "lane DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ST"')
        p = os.path.join(ld, f"lane_{i}.sh")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        os.chmod(p, 0o755)
        lane.update(script=p, status_file=os.path.join(ld, f"lane_{i}.status"), pid=None)
    launch = {
        "start_time_utc": None, "status": "not started (start the lanes after the O2 Manhattan run has finished)",
        "package_root": pkg, "env": "PYTHONPATH=.", "threads_per_lane": 3,
        "estimate_basis": "experiments/r6_fill.py EST_MIN (round-5 wall times outputs/r5_*/wall_time*, round-6 wall times "
                          "outputs/r6_penalty/*/wall_time*, per-solve runtimes of the records) and retry_plan (n x (limit + 90 s))",
        "prerequisites": ["outputs/r6_o2/manhattan run finished (it uses 9-11 threads and most of the memory)",
                          "lanes run under caffeinate -i (laptop sleep truncates Gurobi solves)"],
        "dependencies": [
            "compliance (lane 3, last) polls for the written m=2 budget_result of outputs/r6_o2/manhattan/records.jsonl "
            f"(python3 experiments/r6_fill.py --check-o2) for at most {O2_WAIT_MAX_POLLS * 5 / 60:g} h; on a timeout it runs on "
            "the round-5 layout only (--layout-key)",
            "rolling_ext --analyse joins r6_penalty/rolling (lambda 10) and headline / psweep; pack joins r6_penalty/fleet; "
            "levers_ext joins r6_penalty/levers; stress joins psweep (relaxed K6 reference); rl_seeds joins r6_penalty/rl: "
            "every lane ends with --analyse of every stage plus r6_penalty --stage rolling --analyse (its tables join the "
            "headline / psweep relaxed-ILP rows that the retries replace), so the last lane to finish leaves consistent tables",
            "the retries append rows under the existing keys of outputs/r6_penalty/<stage>/records.jsonl (last row wins; an X5 "
            "re-solve that ends worse is marked retry_worse and ignored); plain TIME_LIMIT X5 rows at a limit >= the retry "
            "limit are skipped (blind re-run)"],
        "lanes": lanes, "expected_wall_min_max_lane": max(l["expected_wall_min"] for l in lanes),
        "launch_command": "for k in 1 2 3 4; do nohup bash outputs/r6_fill_lanes/lane_$k.sh > outputs/r6_fill_lanes/lane_$k.nohup.out 2>&1 & "
                          "echo $! >> outputs/r6_fill_lanes/pids.txt; done",
    }
    with open(os.path.join(ld, "launch.json"), "w", encoding="utf-8") as fh:
        json.dump(launch, fh, indent=1)
    return launch


# ===========================================================================
# main
# ===========================================================================
def analyse(stage: str, smoke: bool, root: Optional[str]) -> str:
    d = stage_dir(stage, smoke, root)
    if not os.path.isdir(d):
        return f"{stage}: no output directory {d}"
    if stage == "transfers":
        return analyse_transfers(d)
    if stage == "stress":
        return analyse_stress(d, smoke, root)
    if stage == "rolling_ext":
        return analyse_rolling_ext(d, smoke, root)
    if stage == "pack":
        return analyse_pack(d, smoke, root)
    if stage == "levers_ext":
        return analyse_levers_ext(d, smoke, root)
    if stage == "compliance":
        return analyse_compliance(d)
    return analyse_rl_seeds(d, smoke, root)


def run_stage(stage: str, args: argparse.Namespace) -> None:
    if stage == "transfers":
        run_transfers(args)
    elif stage == "stress":
        run_x5_stage("stress", plan_stress_r6(BASE, args.smoke, args.seeds), args)
    elif stage == "rolling_ext":
        run_rolling_ext(args)
    elif stage == "pack":
        run_x5_stage("pack", plan_pack_r6(BASE, args.smoke, args.seeds), args)
    elif stage == "levers_ext":
        run_x5_stage("levers_ext", plan_levers_ext_r6(BASE, args.smoke, args.seeds), args)
    elif stage == "compliance":
        run_compliance(args)
    else:
        run_rl_seeds(args)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", default=None,
                    help="new stages: " + ", ".join(NEW_STAGES) + ", 'all', or a comma-separated list; with "
                         "--retry-unsolved: " + ", ".join(RETRY_STAGES))
    ap.add_argument("--retry-unsolved", action="store_true", help="re-solve the unsolved / sleep-truncated ILP rows of the r6_penalty stages")
    ap.add_argument("--time-limit", type=float, default=None, help="retry limit in seconds (defaults per stage); compliance ILP limit")
    ap.add_argument("--smoke", action="store_true", help="tiny instances / short limits, into <out-root>_smoke")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--threads", type=int, default=THREADS)
    ap.add_argument("--budget-min", type=float, default=None, help="wall budget (default per stage)")
    ap.add_argument("--seeds", nargs="+", type=int, default=None, help="override the stage's seeds (new stages)")
    ap.add_argument("--out-root", default=None, help=f"default {OUT_ROOT} ({OUT_ROOT}_smoke with --smoke); retries use r6_penalty's root")
    ap.add_argument("--layout-key", default=None, help="compliance: the first layout (default: the O2 best written layout at m 2)")
    ap.add_argument("--psi", nargs="+", type=float, default=None, help="compliance shares (default 0 .25 .5 .75 1)")
    ap.add_argument("--o2-records", default=O2_RECORDS)
    ap.add_argument("--o2-cache", default=O2_CACHE)
    ap.add_argument("--ppo-seeds", nargs="+", type=int, default=list(PPO_SEEDS))
    ap.add_argument("--write-lanes", action="store_true", help=f"write {LANES_DIR}/lane_*.sh and launch.json (nothing is started)")
    ap.add_argument("--check-o2", action="store_true", help="exit 0 when the O2 written m=2 budget_result exists, else 1")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    if args.threads > 3:
        raise SystemExit("R6 protocol: Threads <= 3")
    if args.check_o2:
        try:
            r = o2_best_layout(args.o2_records)
            print(json.dumps({k: r.get(k) for k in ("target", "budget", "best_layout", "UB", "LB", "gap", "certified")}))
            return
        except (FileNotFoundError, LookupError) as exc:
            print(str(exc))
            raise SystemExit(1)
    if args.write_lanes:
        launch = write_lanes()
        print(json.dumps({l["lane"]: {"expected_wall_min": l["expected_wall_min"], "commands": [c["name"] for c in l["commands"]]}
                          for l in launch["lanes"]}, indent=1))
        return
    if not args.stage:
        raise SystemExit("--stage is required (or --write-lanes / --check-o2)")
    known = RETRY_STAGES if args.retry_unsolved else NEW_STAGES
    stages = list(known) if args.stage == "all" else [x.strip() for x in args.stage.split(",") if x.strip()]
    bad = [x for x in stages if x not in known]
    if bad or not stages:
        raise SystemExit(f"unknown stage(s) {bad}; known: {list(known)} or 'all'")
    if args.analyse:
        for st in stages:
            try:
                print(analyse_retry(st, args.smoke, args.out_root) if args.retry_unsolved else analyse(st, args.smoke, args.out_root),
                      flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"# analyse {st} failed: {type(exc).__name__}: {exc}", flush=True)
                traceback.print_exc()
        return
    for st in stages:
        a = argparse.Namespace(**vars(args))
        if args.retry_unsolved:
            run_retry(st, a)
            continue
        if a.budget_min is None:
            a.budget_min = SMOKE_BUDGET_MIN if a.smoke else WALL_BUDGET_MIN[st]
        run_stage(st, a)


if __name__ == "__main__":
    main()
