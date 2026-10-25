"""Round-5 experiment X6 -- Manhattan-wide siting on ``r5_manhattan`` (plan items M6, A4, M4 of
``notes/reading_to_model.md``; DECISIONS "R5 implementation notes").

One driver that chains the round-5 sub-commands of ``experiments/e9_bilevel_siting.py``
in-process on ONE output root ``outputs/r5_x6_manhattan/`` (one shared lower-level cache
``cache/``, one sub-folder per stage with ``records.jsonl`` / ``results.csv`` / figures /
``RESULTS.md`` written by the sub-command) and adds the round-5 fairness / targets table:

1. ``sweep``        (b) bi-level greedy + local search, ILP lower level (aggregated flow O1),
                        budgets m = 1..4 (x 52,150 USD), seeds 0-2 (``e9 run_sweep``, no
                        integrated bound: the all-candidates model of 15 Manhattan candidates
                        x 3 scenarios is far beyond 600 s).
2. ``baselines``    (a) IJCAI-15 rules CSCD / CSTC / CSAV and the capacity-matched present-day
                        proxy at m = 1..4 under the ILP, the R2.3 rule (r2) and follower E
                        (``e9 run_baselines``); the proxy is matched to the stage-1 layout of
                        each budget (that is why (b) runs first).
3. ``policy_aware`` (d) greedy + local search with follower E (the ``r5_selfish`` equilibrium)
                        as the lower level, chosen layouts cross-evaluated under ilp / r2 /
                        selfish (``e9 run_policy_aware``).
4. ``levers``       (c) marginal-lever table at the chosen bi-level layout under the ILP and
                        under r5_selfish (``e9 run_levers --followers ilp selfish``).
5. ``compliance``   (e) alpha_c in {0, 0.25, 0.5, 0.75, 1} at the chosen layout
                        (``e9 run_compliance``; plan = cached ILP schedule).
6. ``headline``     round-5 protocol table for the chosen / compared layouts: per (layout,
                        seed) the ILP and every rule variant (r2, r5_range, r5_transfer when
                        services exist, r5, r5_selfish, and the selfish equilibrium) on the
                        written targets AND on the like-for-like relaxed control (rho = 0,
                        R_end = 0, ``common.relax_end_targets`` = the ``rho0_R0`` cell of
                        ``common.boundary_grid``); ``best_rule`` = min over r2, r5_range,
                        r5_transfer (services only), r5; headline gap = (rule - ILP) / rule on
                        the relaxed control, the written targets reported as the price of
                        recovery; ``C_end_adjust`` / ``total_end_adjusted`` and the A3 metric
                        pack (``common.flatten_r5``) for every policy.

The "chosen layout" of (c), (e) is the stage-1 greedy layout with the lowest V over the
budgets (``chosen_layout.json``; ``--layout KEY`` overrides).

Protocol (binding): Gurobi Threads 3, Seed 0, TimeLimit 300 s per lower-level solve (600 s for
layouts with a charge-only hub, the E9 rule), aggregate=True for every ILP (also the relaxed
control and the lever variants); byte-identical demand across methods (the demand md5 per seed
is stored in ``demand_md5.json`` on the first run and asserted on every later stage / run, and
every layout instance of the headline table is asserted against it); append-only
``records.jsonl`` everywhere, ``results.csv`` refreshed (at most every 60 s during a stage and
at its end; after every cell in ``headline``), resume = re-run the same command (the shared
cache returns every solved lower level; completed stages are skipped, ``--redo`` re-runs
them; headline cells are resumed by (layout, seed)); one printed JSON line per run.

Wall budgets: ``--total-min`` (default 300) is split by ``ALLOC_MIN``; a stage gets everything
not reserved for the later stages (unused time carries forward).  Inside a stage
``common.WallBudget`` shortens / skips ILP solves (``SKIPPED_BUDGET``) and, added here, policy
evaluations are skipped once the stage budget is spent (``X6Evaluator``), so a stage overruns
by at most one evaluation.  Search sizes are reduced to fit (``--k-screen 2``, the ``x6`` size
menu, ``--menu full`` restores the family menu); truncated searches are reported
(``search_complete = False``), never mistaken for infeasibility.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r5_x6_manhattan.py --dry-run
    python3 experiments/r5_x6_manhattan.py --smoke --out-dir /tmp/x6_smoke     # toy siting instances
    python3 experiments/r5_x6_manhattan.py                                      # full run (300 min)

English only.  The E2 model and the e9 / bilevel modules are not modified.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import shutil
import sys
import tempfile
import time
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from ebike_swap_sim.evaluate import check, cost, metrics  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import e9_bilevel_siting as E9  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r5_x6_manhattan")
FAMILY = S.R5_MANHATTAN_FAMILY
SEEDS = [0, 1, 2]
BUDGETS = [1.0, 2.0, 3.0, 4.0]
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]
TOTAL_MIN = 300.0
TIME_LIMIT = 300.0
TIME_LIMIT_HUB = 600.0
STAGES: Tuple[str, ...] = ("sweep", "baselines", "policy_aware", "levers", "compliance", "headline")
#: Wall allocation (minutes) per stage; the first stage gets ``total - sum(later)``.
ALLOC_MIN: Dict[str, float] = {"sweep": 125.0, "baselines": 45.0, "policy_aware": 30.0, "levers": 40.0,
                               "compliance": 5.0, "headline": 55.0}
MIN_STAGE_S = 120.0
#: Reduced size menu of the X6 searches (sizes still move by +-1 in the local search).
X6_MENU: Dict[str, List[Tuple[int, int]]] = {
    "S": [(1, 0), (2, 0), (3, 0)],
    "C": [(0, 2)],
    "SC": [(1, 1), (2, 1), (3, 1), (2, 2), (3, 2), (4, 2)],
}
#: Rule variants of the headline table (``common.BASELINE_VARIANTS`` names) and best_rule members.
RULE_VARIANTS: Dict[str, str] = {"r2": "baseline", "r5_range": "baseline_r5_range",
                                 "r5_transfer": "baseline_r5_transfer", "r5": "baseline_r5",
                                 "r5_selfish": "baseline_r5_selfish"}
BEST_RULE_MEMBERS: Tuple[str, ...] = ("r2", "r5_range", "r5_transfer", "r5")
TARGETS: Tuple[str, ...] = ("relaxed", "written")      # headline first, then the price of recovery
REFRESH_S = 60.0


# ---------------------------------------------------------------------------
# evaluator / study with the X6 wall guard and shared scenarios
# ---------------------------------------------------------------------------
class X6Evaluator(BL.LowerLevelEvaluator):
    """``LowerLevelEvaluator`` whose policy (non-ILP) evaluations are skipped
    (``SKIPPED_BUDGET``, never cached) once the wall budget is spent, so that a greedy screen
    of a few hundred baseline evaluations cannot overrun the stage budget.  Cached rows are
    still returned; ILP rows keep the ``WallBudget.solve_limit`` rule of the base class."""

    def evaluate_scenario(self, layout: BL.Layout, s: int, policy: str = "ilp",
                          warm: Optional[Dict[str, Any]] = None, force: bool = False) -> Dict[str, Any]:
        if policy != "ilp" and self.wall is not None and self.wall.remaining() <= 0.0:
            key = self.cache_key(layout, s, policy)
            row = self.cache.get(key)
            if row is None or force or not self._reusable(row, self._time_limit_for(layout)):
                out = self._base_row(layout, s, policy, key)
                out.update(status=BL.SKIPPED_BUDGET, feasible=None, total=None, opex=None, C_setup=None,
                           skip_reason=BL.WALL_EXHAUSTED)
                return out
        return super().evaluate_scenario(layout, s, policy, warm=warm, force=force)

    def derive(self, **kw: Any) -> "X6Evaluator":
        ev = super().derive(**kw)
        ev.__class__ = X6Evaluator
        return ev


_SHARED: Dict[str, Any] = {"scen": {}, "spec": None}


class X6Study(E9.Study):
    """``e9_bilevel_siting.Study`` with :class:`X6Evaluator`, scenarios shared across the
    stages of one process (the base instance build is ~20 s per seed) and a throttled
    ``results.csv`` refresh."""

    def __init__(self, sub: str, args: argparse.Namespace, menu: Optional[Dict[str, List[Tuple[int, int]]]] = None
                 ) -> None:
        super().__init__(sub, args)
        self._scen = _SHARED["scen"]
        if _SHARED["spec"] is not None:
            self.spec = _SHARED["spec"]
        if menu is not None and not self.smoke:
            self.size_menu = {r: list(v) for r, v in menu.items()}
        self._last_refresh = time.perf_counter()

    def scenario(self, seed: int, n_bikes: Optional[int] = None, candidates: Optional[Sequence[S.Candidate]] = None):
        inst = super().scenario(seed, n_bikes, candidates)
        if _SHARED["spec"] is None:
            _SHARED["spec"] = self.spec
        return inst

    def evaluator(self, seeds: Sequence[int], n_bikes: Optional[int] = None, relaxed: bool = False,
                  candidates: Optional[Sequence[S.Candidate]] = None) -> BL.LowerLevelEvaluator:
        scen = [self.scenario(s, n_bikes, candidates) for s in seeds]
        kw: Dict[str, Any] = {}
        if self.aggregate is not False:
            kw["aggregate"] = self.aggregate
        return X6Evaluator(scen, self.spec, time_limit=self.time_limit, time_limit_hub=self.time_limit_hub,
                           threads=self.threads, params=dict(C.ILP_PARAMS_R3), cache_dir=self.cache_dir,
                           relaxed_targets=relaxed, wall=self.wall, verbose=True, reposition=self.reposition, **kw)

    def emit(self, row: Dict[str, Any]) -> None:
        super().emit(row)
        if time.perf_counter() - self._last_refresh > REFRESH_S:
            self.refresh_csv()
            self._last_refresh = time.perf_counter()


def e9_namespace(**over: Any) -> argparse.Namespace:
    """The argument namespace of ``e9_bilevel_siting.main`` (its defaults) with overrides."""
    ns: Dict[str, Any] = {sub: False for sub in E9.SUBS + E9.NEW_SUBS}
    ns.update(dry_run=False, smoke=False, out_root=None, threads=C.THREADS, time_limit=E9.TIME_LIMIT,
              time_limit_hub=E9.TIME_LIMIT_HUB, integrated_time_limit=E9.INTEGRATED_TIME_LIMIT,
              wall_budget=8 * 3600.0, seeds=None, budgets=None, bikes=None, n_candidates=None, with_hub=False,
              k_screen=5, iterations=3, access_d=None, zeta=None, layouts=None, family=None,
              min_served=E9.MIN_SERVED_SHARE, allow_s_only=False, reposition="open_sites", access_mode="repair",
              aggregate="auto", followers=None, follower="selfish", rules=None, cstc_mode="isolation",
              alphas=None, draws=3, station_plan="plan", probe_ilp=False)
    for k, v in over.items():
        if k not in ns:
            raise KeyError(f"unknown e9 option {k!r}")
        ns[k] = v
    return argparse.Namespace(**ns)


# ---------------------------------------------------------------------------
# driver helpers
# ---------------------------------------------------------------------------
def _log(root: str, row: Dict[str, Any]) -> None:
    C.append_jsonl(os.path.join(root, "driver_log.jsonl"), C.jsonable(row))
    print(json.dumps(C.jsonable({k: row.get(k) for k in ("stage", "event", "status", "complete", "wall_budget_min",
                                                          "wall_min", "note") if k in row})), flush=True)


def _stage_complete(root: str, stage: str) -> bool:
    last = None
    for r in C.load_jsonl(os.path.join(root, "driver_log.jsonl")):
        if r.get("stage") == stage and r.get("event") == "finished":
            last = r
    return bool(last and last.get("complete"))


def _check_demand(root: str, smoke: bool) -> Dict[str, str]:
    """md5 of every shared base scenario; stored on the first run, asserted afterwards."""
    path = os.path.join(root, "demand_md5.json")
    saved: Dict[str, str] = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
    cur = {f"seed{k[0]}_bikes{k[1]}_cands{len(k[2])}": C.demand_md5(inst, include_bike_nodes=True, include_facilities=False)
           for k, inst in _SHARED["scen"].items()}
    for k, v in cur.items():
        if k in saved and saved[k] != v:
            raise AssertionError(f"demand md5 changed for {k}: {saved[k]} -> {v} (instances are not byte-identical)")
    merged = {**saved, **cur}
    if merged != saved:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=1, sort_keys=True)
    return merged


def _last_by(rows: Sequence[Dict[str, Any]], key) -> Dict[Any, Dict[str, Any]]:
    out: Dict[Any, Dict[str, Any]] = {}
    for r in rows:
        out[key(r)] = r
    return out


def sweep_layouts(root: str) -> Dict[float, Dict[str, Any]]:
    """Last stage-1 greedy row per budget (``kind layout_chosen``, ``method greedy_ls``)."""
    rows = [r for r in C.load_jsonl(os.path.join(root, "sweep", "records.jsonl"))
            if r.get("kind") == "layout_chosen" and r.get("method") == "greedy_ls" and r.get("layout")]
    return _last_by(rows, lambda r: float(r.get("budget_m") or 0.0))


def chosen_layout(root: str, override: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """The bi-level layout of (c) / (e): lowest V over the stage-1 budgets (ties: lower
    investment, then smaller budget); fallback the best ILP-priced rule layout."""
    if override:
        return override, {"source": "cli --layout"}
    best = None
    for m, r in sorted(sweep_layouts(root).items()):
        if r.get("V") is None:
            continue
        cand = (float(r["V"]), float(r.get("investment") or 0.0), m)
        if best is None or cand < best[0]:
            best = (cand, r)
    if best is not None:
        r = best[1]
        return r["layout_key"], {"source": f"sweep greedy_ls@m{r.get('budget_m')}", "V": r.get("V"),
                                 "budget_m": r.get("budget_m"), "search_complete": r.get("search_complete"),
                                 "served_share": r.get("served_share")}
    rules = [r for r in C.load_jsonl(os.path.join(root, "baselines", "records.jsonl"))
             if r.get("kind") == "rule_layout" and r.get("policy") == "ilp" and r.get("V") is not None and r.get("layout_key")]
    if rules:
        r = min(rules, key=lambda r: (float(r["V"]), float(r.get("investment") or 0.0)))
        return r["layout_key"], {"source": f"fallback: rule {r.get('rule')}@m{r.get('budget_m')} (no sweep layout)",
                                 "V": r.get("V"), "budget_m": r.get("budget_m")}
    return None, {"source": "none"}


def headline_layouts(root: str, chosen: Optional[str]) -> List[Tuple[str, List[str]]]:
    """Layouts of the headline table in priority order, ``[(layout_key, [labels])]``."""
    order: List[str] = []
    labels: Dict[str, List[str]] = {}

    def add(key: Optional[str], label: str) -> None:
        if not key:
            return
        if key not in labels:
            order.append(key)
            labels[key] = []
        labels[key].append(label)

    add(chosen, "bilevel_chosen")
    for m, r in sorted(sweep_layouts(root).items()):
        add(r.get("layout_key"), f"bilevel_m{m:g}")
    pa = [r for r in C.load_jsonl(os.path.join(root, "policy_aware", "records.jsonl"))
          if r.get("kind") == "layout_chosen" and r.get("layout_key")]
    for m, r in sorted(_last_by(pa, lambda r: float(r.get("budget_m") or 0.0)).items()):
        add(r["layout_key"], f"policy_aware_m{m:g}")
    rl = [r for r in C.load_jsonl(os.path.join(root, "baselines", "records.jsonl"))
          if r.get("kind") == "rule_layout" and r.get("policy") == "ilp" and r.get("layout_key")]
    last = _last_by(rl, lambda r: (float(r.get("budget_m") or 0.0), r.get("rule")))
    for m in sorted({k[0] for k in last}):
        cands = [r for k, r in last.items() if k[0] == m and r.get("rule") != "present_day" and r.get("V") is not None]
        if cands:
            b = min(cands, key=lambda r: float(r["V"]))
            add(b["layout_key"], f"best_siting_rule_m{m:g}({b['rule']})")
        pdr = last.get((m, "present_day"))
        if pdr is not None:
            add(pdr["layout_key"], f"present_day_m{m:g}")
    return [(k, labels[k]) for k in order]


# ---------------------------------------------------------------------------
# headline: rule variants x targets, end adjustment, metric pack
# ---------------------------------------------------------------------------
def _policy_cols(prefix: str, inst, lib, sched) -> Dict[str, Any]:
    cst = cost(inst, lib, sched)
    met = metrics(inst, lib, sched)
    rep = check(inst, lib, sched)
    out = {f"{prefix}total": cst["total"], f"{prefix}C_setup": cst["C_setup"],
           f"{prefix}C_end_adjust": cst.get("C_end_adjust"), f"{prefix}total_end_adjusted": cst.get("total_end_adjusted"),
           f"{prefix}served_share": met["served_share"], f"{prefix}n_late": met["n_late"],
           f"{prefix}kwh_purchased": met["kwh_purchased"], f"{prefix}transfers_used": met["transfers_used"],
           f"{prefix}check_families": C.family_counts(rep)}
    out.update(C.flatten_r5(met, prefix))
    return out


def _gap(base: Optional[float], ilp: Optional[float]) -> Optional[float]:
    if base is None or ilp is None or not base:
        return None
    return 100.0 * (float(base) - float(ilp)) / float(base)


def headline_cell(ev: BL.LowerLevelEvaluator, ev_rel: BL.LowerLevelEvaluator, lay: BL.Layout, s: int,
                  base_md5: str) -> Dict[str, Any]:
    """One (layout, scenario) cell: ILP + rule variants + follower E on the relaxed control
    and on the written targets."""
    row: Dict[str, Any] = {"status": "OK"}
    port_w = None
    for t in ("written", "relaxed"):         # written first: its schedule warm-starts the relaxed solve
        e = ev if t == "written" else ev_rel
        r_ilp = e.evaluate_scenario(lay, s, "ilp", warm=(port_w if t == "relaxed" else None))
        row.update({f"{t}_ilp_status": r_ilp.get("status"), f"{t}_ilp_gap": r_ilp.get("gap"),
                    f"{t}_ilp_runtime_s": r_ilp.get("runtime_s"), f"{t}_ilp_cache_hit": r_ilp.get("cache_hit"),
                    f"{t}_ilp_mip_start": r_ilp.get("mip_start_variant")})
        if r_ilp.get("status") in (BL.SKIPPED_BUDGET, BL.ERROR):
            row["status"] = r_ilp["status"]
            row["error"] = r_ilp.get("error")
            return row
        inst, lib = e.layout_pair(lay, s)
        md5 = C.demand_md5(inst, include_bike_nodes=True, include_facilities=False)
        if md5 != base_md5:
            raise AssertionError(f"{lay.key()} s{s} {t}: demand md5 {md5} != base {base_md5}")
        row[f"{t}_demand_md5"] = md5
        row["n_services"] = len(inst.services)
        port = e.load_portable(r_ilp) if r_ilp.get("feasible") else None
        sched = BL.materialise_schedule(port, inst, lib) if port else None
        if t == "written":
            port_w = port
        if sched is None:
            row[f"{t}_ilp_total"] = None
            row["status"] = "NO_ILP_SCHEDULE" if row["status"] == "OK" else row["status"]
        else:
            row.update(_policy_cols(f"{t}_ilp_", inst, lib, sched))
        for name, variant in RULE_VARIANTS.items():
            if name == "r5_transfer" and not inst.services:
                row[f"{t}_{name}_total"] = None
                row[f"{t}_{name}_note"] = "no services (fewer than two locations)"
                continue
            rec = C.run_baseline_case(inst, lib, C.baseline_variant_params(variant, inst), label=name)
            row.update(_policy_cols(f"{t}_{name}_", inst, lib, rec["schedule"]))
            row[f"{t}_{name}_runtime_s"] = rec["runtime"]
        r_sf = e.evaluate_scenario(lay, s, "selfish")
        p_sf = e.load_portable(r_sf) if r_sf.get("feasible") else None
        s_sf = BL.materialise_schedule(p_sf, inst, lib) if p_sf else None
        if s_sf is not None:
            row.update(_policy_cols(f"{t}_selfish_eq_", inst, lib, s_sf))
            row[f"{t}_selfish_eq_equilibrium"] = r_sf.get("equilibrium")
        members = [m for m in BEST_RULE_MEMBERS if row.get(f"{t}_{m}_total") is not None]
        if members:
            br = min(members, key=lambda m: float(row[f"{t}_{m}_total"]))
            bra = min(members, key=lambda m: float(row[f"{t}_{m}_total_end_adjusted"]))
            row.update({f"{t}_best_rule": br, f"{t}_best_rule_total": row[f"{t}_{br}_total"],
                        f"{t}_best_rule_end_adjusted": bra,
                        f"{t}_best_rule_total_end_adjusted": row[f"{t}_{bra}_total_end_adjusted"]})
        ilp_t, ilp_a = row.get(f"{t}_ilp_total"), row.get(f"{t}_ilp_total_end_adjusted")
        for p in ("r2", "r5", "best_rule", "selfish_eq"):
            bt = row.get(f"{t}_best_rule_total") if p == "best_rule" else row.get(f"{t}_{p}_total")
            ba = (row.get(f"{t}_best_rule_total_end_adjusted") if p == "best_rule"
                  else row.get(f"{t}_{p}_total_end_adjusted"))
            row[f"{t}_gap_vs_{p}_pct"] = _gap(bt, ilp_t)
            row[f"{t}_gap_vs_{p}_pct_end_adjusted"] = _gap(ba, ilp_a)
    for p in ("ilp", "best_rule", "r2", "r5"):
        w = row.get(f"written_{p}_total")
        r = row.get(f"relaxed_{p}_total")
        row[f"price_of_recovery_{p}"] = None if w is None or r is None else float(w) - float(r)
        wa = row.get(f"written_{p}_total_end_adjusted")
        ra = row.get(f"relaxed_{p}_total_end_adjusted")
        row[f"price_of_recovery_{p}_end_adjusted"] = None if wa is None or ra is None else float(wa) - float(ra)
    return row


HEADLINE_SUMMARY_COLS = (
    "relaxed_ilp_total", "relaxed_best_rule_total", "relaxed_gap_vs_best_rule_pct", "relaxed_gap_vs_r2_pct",
    "relaxed_gap_vs_r5_pct", "relaxed_gap_vs_best_rule_pct_end_adjusted", "relaxed_ilp_C_end_adjust",
    "relaxed_best_rule_total_end_adjusted", "relaxed_ilp_served_share", "relaxed_r2_served_share",
    "relaxed_selfish_eq_total", "relaxed_gap_vs_selfish_eq_pct",
    "written_ilp_total", "written_best_rule_total", "written_gap_vs_best_rule_pct", "written_gap_vs_r2_pct",
    "written_ilp_C_end_adjust", "written_gap_vs_best_rule_pct_end_adjusted",
    "price_of_recovery_ilp", "price_of_recovery_ilp_end_adjusted", "price_of_recovery_best_rule",
    "relaxed_ilp_r5_min_sbur", "relaxed_ilp_r5_bsr", "relaxed_ilp_r5_outage_rate", "relaxed_ilp_r5_empty_km",
    "relaxed_r2_r5_min_sbur", "relaxed_r2_r5_bsr", "relaxed_r2_r5_outage_rate", "relaxed_r2_r5_empty_km",
)


def run_headline(study: X6Study, root: str, chosen: Optional[str], dry_run: bool) -> Dict[str, Any]:
    seeds = E9._r5_seeds(study)
    lays = headline_layouts(root, chosen)
    plan = {"sub": "headline", **study.plan_common(), "seeds": seeds, "n_layouts": len(lays),
            "layouts": {k: v for k, v in lays}, "targets": list(TARGETS), "rule_variants": RULE_VARIANTS,
            "best_rule_members": list(BEST_RULE_MEMBERS), "cells": len(lays) * len(seeds)}
    print(json.dumps(C.jsonable(plan), indent=1, default=str), flush=True)
    if dry_run:
        return {"plan": plan, "complete": True}
    done = {(r.get("layout_key"), r.get("seed")) for r in C.load_jsonl(study.records_path)
            if r.get("kind") == "headline_cell" and r.get("status") in ("OK", "NO_ILP_SCHEDULE")}
    if not lays:
        study.emit({"kind": "headline_status", "status": "NONE", "note": "no layouts in the stage records"})
        study.refresh_csv()
        E9.write_md(study, "X6 headline -- no layouts", [("Status", "no layouts found in sweep / baselines / policy_aware")], [])
        return {"complete": False}
    ev = study.evaluator(seeds)
    ev_rel = ev.derive(relaxed_targets=True)
    complete = True
    for key, labels in lays:
        lay = BL.Layout.from_key(key)
        for i, sd in enumerate(seeds):
            if (key, sd) in done:
                continue
            if study.wall.solve_limit(study.time_limit) is None:
                study.emit({"kind": "headline_cell", "layout_key": key, "labels": labels, "seed": sd,
                            "status": C.SKIPPED_BUDGET})
                complete = False
                continue
            t0 = time.perf_counter()
            try:
                cell = headline_cell(ev, ev_rel, lay, i, ev.demand_md5[i])
            except AssertionError:
                raise
            except Exception as exc:  # noqa: BLE001 -- recorded, the table goes on
                import traceback
                cell = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-3000:]}
            cell.update(kind="headline_cell", layout_key=key, labels=labels, seed=sd, scenario=i,
                        investment=lay.investment(study.spec), C_setup_allocated=lay.allocated_cost(study.spec),
                        n_open=lay.n_open, wall_s=time.perf_counter() - t0,
                        V=cell.get("relaxed_ilp_total"), gap=cell.get("relaxed_gap_vs_best_rule_pct"),
                        served_share=cell.get("relaxed_ilp_served_share"))
            study.emit(cell)
            study.emit_cache_rows(ev)
            study.refresh_csv()
            if cell["status"] not in ("OK", "NO_ILP_SCHEDULE"):
                complete = False
    # summary per layout (mean over the seeds with a complete cell) --------------------------
    cells = _last_by([r for r in C.load_jsonl(study.records_path) if r.get("kind") == "headline_cell"],
                     lambda r: (r.get("layout_key"), r.get("seed")))
    summ: List[Dict[str, Any]] = []
    for key, labels in lays:
        rs = [cells[(key, sd)] for sd in seeds if (key, sd) in cells and cells[(key, sd)].get("status") == "OK"]
        row: Dict[str, Any] = {"layout_key": key, "labels": ", ".join(labels), "n_seeds_ok": len(rs),
                               "all_seeds": len(rs) == len(seeds),
                               "best_rule_relaxed": ",".join(str(r.get("relaxed_best_rule")) for r in rs),
                               "ilp_status_relaxed": ",".join(str(r.get("relaxed_ilp_status")) for r in rs)}
        for c in HEADLINE_SUMMARY_COLS:
            vals = [float(r[c]) for r in rs if isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool)]
            row[c] = (sum(vals) / len(vals)) if vals and len(vals) == len(rs) else None
        summ.append(row)
    df = pd.DataFrame(summ)
    df.to_csv(os.path.join(study.out_dir, "summary.csv"), index=False)
    study.refresh_csv()
    main_cols = ["layout_key", "labels", "n_seeds_ok", "relaxed_ilp_total", "relaxed_best_rule_total",
                 "relaxed_gap_vs_best_rule_pct", "relaxed_gap_vs_r2_pct", "relaxed_gap_vs_r5_pct",
                 "relaxed_gap_vs_best_rule_pct_end_adjusted", "relaxed_ilp_C_end_adjust", "relaxed_gap_vs_selfish_eq_pct",
                 "best_rule_relaxed", "ilp_status_relaxed"]
    rec_cols = ["layout_key", "written_ilp_total", "written_best_rule_total", "written_gap_vs_best_rule_pct",
                "written_gap_vs_r2_pct", "written_ilp_C_end_adjust", "written_gap_vs_best_rule_pct_end_adjusted",
                "price_of_recovery_ilp", "price_of_recovery_ilp_end_adjusted", "price_of_recovery_best_rule"]
    pack_cols = ["layout_key"] + [c for c in HEADLINE_SUMMARY_COLS if c.startswith(("relaxed_ilp_r5_", "relaxed_r2_r5_"))]
    sections = [
        ("Protocol", f"Seeds {seeds}; ILP = aggregated E2 ILP (O1), Threads {study.threads}, Seed 0, TimeLimit "
                     f"{study.time_limit:.0f} s (hubs {study.time_limit_hub:.0f} s); rules {RULE_VARIANTS} "
                     f"(r5_transfer only when the layout has shuttle services); best_rule = per-instance min over "
                     f"{list(BEST_RULE_MEMBERS)} by (26) total (end-adjusted columns re-pick the best rule by "
                     f"total_end_adjusted); selfish_eq = follower E (r5_selfish equilibrium). Headline = relaxed "
                     f"control (rho = 0, R_end = 0, common.relax_end_targets); written targets = price of recovery. "
                     f"Gap = 100 (rule - ILP) / rule. Demand md5 asserted per cell."),
        ("Headline (relaxed control, mean over seeds)", C.markdown_table(df, [c for c in main_cols if c in df.columns], 3)
         if not df.empty else "(no rows)"),
        ("Written targets and price of recovery", C.markdown_table(df, [c for c in rec_cols if c in df.columns], 3)
         if not df.empty else "(no rows)"),
        ("A3 metric pack (relaxed control; full pack per policy in results.csv)",
         C.markdown_table(df, [c for c in pack_cols if c in df.columns], 3) if not df.empty else "(no rows)"),
        ("Solver statistics", json.dumps({"written": ev.stats(), "relaxed": ev_rel.stats()})),
    ]
    E9.write_md(study, "X6 headline -- ILP vs rule variants (best_rule), relaxed control and written targets", sections, [])
    return {"complete": complete, "summary": summ}


# ---------------------------------------------------------------------------
# stage runner
# ---------------------------------------------------------------------------
def stage_complete_flag(stage: str, out: Any) -> bool:
    """Whether a stage finished without truncation (from the sub-command's return value)."""
    if not isinstance(out, dict):
        return False
    if stage == "sweep":
        g = out.get("greedy") or {}
        res = out.get("results") or {}
        return (not g.get("wall_exhausted")) and all((v.get("greedy") or {}).get("search_complete") is not False
                                                     for v in res.values())
    if stage == "baselines":
        return all(r.get("status") != C.SKIPPED_BUDGET for r in out.get("rows", []))
    if stage == "policy_aware":
        g = out.get("greedy") or {}
        rows = out.get("rows") or []
        bad = any(str(v) == C.SKIPPED_BUDGET for r in rows for k, v in r.items() if k.endswith("_status"))
        return (not g.get("wall_exhausted")) and not bad
    if stage == "levers":
        rows = out.get("rows")
        if rows is None:
            return False
        return all(r.get("status") != C.SKIPPED_BUDGET for r in rows) and all(v is not None for v in (out.get("reference") or {}).values())
    if stage == "compliance":
        summ = out.get("summary")
        return bool(summ) and all(r.get("complete") for r in summ)
    if stage == "headline":
        return bool(out.get("complete"))
    return False


def build_stage_args(args: argparse.Namespace, stage: str, out_root: str, wall_s: float, layout: Optional[str]
                     ) -> argparse.Namespace:
    over: Dict[str, Any] = dict(
        smoke=bool(args.smoke), dry_run=bool(args.dry_run), out_root=out_root, threads=int(args.threads),
        time_limit=float(args.time_limit), time_limit_hub=float(args.time_limit_hub), wall_budget=float(wall_s),
        seeds=list(args.seeds), budgets=list(args.budgets), k_screen=int(args.k_screen), family=FAMILY,
        min_served=float(args.min_served), reposition="open_sites", aggregate="on", cstc_mode=str(args.cstc_mode),
        draws=int(args.draws), alphas=list(ALPHAS), station_plan="plan")
    if stage in E9.SUBS + E9.NEW_SUBS:
        over[stage] = True
    if stage == "baselines":
        over["followers"] = ["ilp", "baseline", "selfish"]
    elif stage == "policy_aware":
        over.update(followers=["ilp", "baseline", "selfish"], follower="selfish", min_served=float(args.pa_min_served))
    elif stage == "levers":
        over.update(followers=["ilp", "selfish"], layouts=[layout] if layout else None)
    elif stage == "compliance":
        over.update(layouts=[layout] if layout else None)
    return e9_namespace(**over)


def run_stage(stage: str, a: argparse.Namespace, menu: Optional[Dict[str, List[Tuple[int, int]]]], root: str,
              chosen: Optional[str]) -> Any:
    study = X6Study(stage, a, menu=menu)
    if stage == "sweep":
        return E9.run_sweep(study, role_set=("S", "C", "SC"), tag="sweep", integrated=False)
    if stage == "baselines":
        return E9.run_baselines(study)
    if stage == "policy_aware":
        return E9.run_policy_aware(study)
    if stage == "levers":
        return E9.run_levers(study)
    if stage == "compliance":
        return E9.run_compliance(study)
    if stage == "headline":
        return run_headline(study, root, chosen, bool(a.dry_run))
    raise ValueError(stage)


def write_driver_md(root: str, args: argparse.Namespace, stage_rows: List[Dict[str, Any]], chosen: Optional[str],
                    chosen_info: Dict[str, Any], md5: Dict[str, str]) -> str:
    log = C.load_jsonl(os.path.join(root, "driver_log.jsonl"))
    fin = _last_by([r for r in log if r.get("event") == "finished"], lambda r: r.get("stage"))
    lines = ["# X6 -- Manhattan-wide siting (M6, A4, M4) on `r5_manhattan`", "",
             f"Driver `experiments/r5_x6_manhattan.py`; seeds {args.seeds}; budgets m = {args.budgets} (x 52,150 USD); "
             f"Threads {args.threads}, Seed 0, TimeLimit {args.time_limit:.0f} s (hubs {args.time_limit_hub:.0f} s), "
             f"aggregated ILP (O1); k_screen {args.k_screen}; size menu `{args.menu}`; total wall budget "
             f"{args.total_min:.0f} min. Every ILP total is an upper bound on the written optimum (moves only into open "
             f"sites / depots); the R2.4 geometry caveat applies."
             + (" SMOKE: toy siting instances (seeds 0-1, budgets 1-2 toy units, TimeLimit 30 s)." if args.smoke else ""), "",
             "## Stages", "", "| stage | status | complete | wall budget (min) | wall used (min) | folder |", "|---|---|---|---|---|---|"]
    for st in STAGES:
        r = fin.get(st) or {}
        lines.append(f"| {st} | {r.get('status', 'not run')} | {r.get('complete')} | "
                     f"{C.fmt(r.get('wall_budget_min'), 1)} | {C.fmt(r.get('wall_min'), 1)} | `{st}/` |")
    lines += ["", "## Chosen bi-level layout", "", f"`{chosen}` -- {json.dumps(C.jsonable(chosen_info))}", "",
              "## Demand md5 per base scenario (asserted across stages and runs)", "", "```", json.dumps(md5, indent=1), "```", "",
              "Per-stage reports: `sweep/RESULTS.md` (b), `baselines/RESULTS.md` (a), `policy_aware/RESULTS.md` (d), "
              "`levers/RESULTS.md` (c), `compliance/RESULTS.md` (e), `headline/RESULTS.md` (fairness + targets: "
              "relaxed-control headline gap vs best_rule, written targets = price of recovery, C_end_adjust and the A3 "
              "metric pack for both policies). Truncated stages (complete = False) resume by re-running the same command.", ""]
    path = os.path.join(root, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description="X6: Manhattan-wide siting (M6, A4, M4) driver")
    ap.add_argument("--dry-run", action="store_true", help="print the plan of every stage, solve nothing, write nothing")
    ap.add_argument("--smoke", action="store_true", help="toy siting instances (seconds); use with --out-dir <scratch>")
    ap.add_argument("--out-dir", default=None, help=f"output root (default {OUT_DIR})")
    ap.add_argument("--total-min", type=float, default=None, help=f"total wall budget in minutes (default {TOTAL_MIN:g}; smoke 20)")
    ap.add_argument("--stages", nargs="*", default=None, choices=list(STAGES), help="subset of the stages (in driver order)")
    ap.add_argument("--redo", action="store_true", help="re-run stages already completed in this output root")
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--time-limit-hub", type=float, default=TIME_LIMIT_HUB)
    ap.add_argument("--seeds", nargs="*", type=int, default=SEEDS)
    ap.add_argument("--budgets", nargs="*", type=float, default=BUDGETS)
    ap.add_argument("--k-screen", type=int, default=2, help="greedy: ILP-priced moves per role after the baseline screen")
    ap.add_argument("--menu", default="x6", choices=["x6", "full"], help="size menu of the searches")
    ap.add_argument("--min-served", type=float, default=E9.MIN_SERVED_SHARE, help="(b) served-share guard of the greedy")
    ap.add_argument("--pa-min-served", type=float, default=0.0,
                    help="(d) served-share guard with the selfish follower (0: the policy's dropped orders are priced by P_i)")
    ap.add_argument("--cstc-mode", default="access", choices=["isolation", "access"],
                    help="(a) CSTC weights: IJCAI-15 inverse-distance access (default, no solves) or ILP singletons")
    ap.add_argument("--draws", type=int, default=3, help="(e) draws of the compliant set per alpha")
    ap.add_argument("--layout", default=None, help="override the chosen layout of (c) / (e)")
    args = ap.parse_args(argv)
    if args.threads > 3:
        raise SystemExit("protocol: Threads <= 3")
    if args.time_limit > 300.0 and not args.smoke:
        raise SystemExit("protocol: TimeLimit 300 s per lower-level solve (hubs via --time-limit-hub)")
    total_min = float(args.total_min if args.total_min is not None else (20.0 if args.smoke else TOTAL_MIN))
    args.total_min = total_min
    stages = [s for s in STAGES if args.stages is None or s in args.stages]
    menu = X6_MENU if args.menu == "x6" else None
    warnings.simplefilter("ignore")
    scale = total_min / TOTAL_MIN
    alloc = {s: ALLOC_MIN[s] * scale for s in stages}

    if args.dry_run:
        real_root = args.out_dir or OUT_DIR
        tmp = tempfile.mkdtemp(prefix="x6_dry_")
        try:
            chosen, info = chosen_layout(real_root, args.layout) if os.path.isdir(real_root) else (args.layout, {"source": "pending (from sweep)"})
            plan = {"driver": "r5_x6_manhattan", "out_dir": real_root, "family": FAMILY, "seeds": args.seeds,
                    "budgets_m": args.budgets, "stages": stages, "alloc_min": alloc, "total_min": total_min,
                    "threads": args.threads, "time_limit": args.time_limit, "time_limit_hub": args.time_limit_hub,
                    "aggregate": True, "k_screen": args.k_screen, "menu": menu or "family", "chosen_layout": chosen,
                    "chosen_source": info.get("source")}
            print(json.dumps(C.jsonable(plan), indent=1), flush=True)
            for st in stages:
                a = build_stage_args(args, st, tmp, alloc[st] * 60.0, chosen)
                print(f"# ---- stage {st} (alloc {alloc[st]:.0f} min) ----", flush=True)
                run_stage(st, a, menu, real_root if st == "headline" else tmp, chosen)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return {"dry_run": True}

    root = C.ensure_dir(args.out_dir or OUT_DIR)
    t_start = time.perf_counter()
    total_s = total_min * 60.0
    stage_rows: List[Dict[str, Any]] = []
    chosen, info = chosen_layout(root, args.layout)
    md5: Dict[str, str] = {}
    for i, st in enumerate(stages):
        if st in ("levers", "compliance", "headline"):
            chosen, info = chosen_layout(root, args.layout)
            with open(os.path.join(root, "chosen_layout.json"), "w", encoding="utf-8") as fh:
                json.dump(C.jsonable({"layout_key": chosen, **info}), fh, indent=1)
        if _stage_complete(root, st) and not args.redo:
            _log(root, {"stage": st, "event": "skipped", "status": "already complete", "complete": True})
            continue
        remaining = total_s - (time.perf_counter() - t_start)
        reserve = sum(alloc[s] * 60.0 for s in stages[i + 1:] if args.redo or not _stage_complete(root, s))
        budget_s = remaining - reserve
        if budget_s < MIN_STAGE_S * (scale if args.smoke else 1.0):
            _log(root, {"stage": st, "event": "finished", "status": C.SKIPPED_BUDGET, "complete": False,
                        "wall_budget_min": budget_s / 60.0, "wall_min": 0.0, "note": "no wall budget left for this stage"})
            continue
        if st in ("levers", "compliance") and not chosen:
            _log(root, {"stage": st, "event": "finished", "status": "NO_LAYOUT", "complete": False,
                        "wall_budget_min": budget_s / 60.0, "wall_min": 0.0, "note": "no chosen layout (sweep produced none)"})
            continue
        _log(root, {"stage": st, "event": "started", "wall_budget_min": budget_s / 60.0, "chosen_layout": chosen})
        t0 = time.perf_counter()
        a = build_stage_args(args, st, root, budget_s, chosen)
        status, err = "OK", None
        try:
            out = run_stage(st, a, menu, root, chosen)
            complete = stage_complete_flag(st, out)
        except AssertionError:
            raise
        except Exception as exc:  # noqa: BLE001 -- one stage failing must not lose the others
            import traceback
            status, err, complete = "ERROR", f"{type(exc).__name__}: {exc}", False
            traceback.print_exc()
        md5 = _check_demand(root, bool(args.smoke))
        row = {"stage": st, "event": "finished", "status": status, "complete": complete, "error": err,
               "wall_budget_min": budget_s / 60.0, "wall_min": (time.perf_counter() - t0) / 60.0,
               "total_elapsed_min": (time.perf_counter() - t_start) / 60.0}
        _log(root, row)
        stage_rows.append(row)
    chosen, info = chosen_layout(root, args.layout)
    with open(os.path.join(root, "chosen_layout.json"), "w", encoding="utf-8") as fh:
        json.dump(C.jsonable({"layout_key": chosen, **info}), fh, indent=1)
    md5 = md5 or _check_demand(root, bool(args.smoke))
    path = write_driver_md(root, args, stage_rows, chosen, info, md5)
    with open(os.path.join(root, "wall_time.json"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"wall_s": time.perf_counter() - t_start, "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
                             "args": vars(args)}) + "\n")
    print(f"# X6 finished in {(time.perf_counter() - t_start) / 60.0:.1f} min -> {path}", flush=True)
    return {"root": root, "stages": stage_rows, "chosen": chosen}


if __name__ == "__main__":
    main()
