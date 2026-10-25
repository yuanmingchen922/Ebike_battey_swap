"""Round 6, plan item O2 -- certified siting: L-shaped Benders lower bound with exact incumbent
pricing (``notes/o2_siting_bound_design.md``; code ``ebike_swap_sim/benders.py``).

Stages (one per run; outputs under ``outputs/r6_o2/<stage>/``):

``--midtown-validate``
    E9.1 reproduction under the OLD prices (``usd_sunk``): family ``nyc4h_stress2``, candidates
    L01-L04, seeds 0 and 1 (p = 1/2), 6 bikes, budget m = 1 (52,150 USD), option grid
    ``bilevel.VALIDATION_GRID`` (S: B 1-2; SC: B 1-2, C 1), roles {S, SC}, written targets,
    per-bike pricing on a COPY of ``outputs/e9_bilevel/cache`` (C14).  Acceptance: best layout
    ``L02:SC:B2:C1`` (or a tie within the pricing gaps), ``UB = 676.223`` within 1e-6,
    ``661.5 <= LB <= 676.223 + 1e-6``.
``--manhattan``
    ``r5_manhattan`` (15 lattice candidates, seeds 0-2, p = 1/3, 8 bikes) repriced to the
    round-6 base ``costs.R6_PRICING`` (P 60, w 18, v 15; ``costs.reprice_orders``), family menu
    ``sites_nyc.SIZE_MENUS['r5_manhattan']``, budgets m = 1..4 x 52,150 USD, aggregated pricing
    (O1).  Relaxed targets first, then written targets seeded with the relaxed cuts (one-way
    import, C16).  Warm start: CSCD / CSTC (access) / CSAV at every budget, the capacity-matched
    present-day proxy (reference CSAV) at every budget and the two round-5 layouts.  After the
    warm start the fixed-layout LP-gap gate (design section 8 step 3) is measured and acted on:
    median gap <= 0.5 %: default design; 0.5-2 %: S1/S2 recommended (not implemented; the run
    continues and says so); > 2 %: the smallest budget is certified by LP-ordered enumeration
    (``SitingCertifier.certify_by_enumeration``) before the Benders phases (``--gate abort``
    stops instead).  After the search, the rule layouts, the present-day proxy and the round-5
    layouts are priced exactly under the same follower (the ILP) BEFORE the per-budget results
    are written (they can lower UB); the best layouts are cross-evaluated under the R2.3 policy
    (``baseline``) and the selfish follower.  ``--access-D`` adds the [U4] access rows
    (sensitivity).
``--smoke``
    The whole pipeline on the toy siting instance (4 candidates, 2 scenarios, Threads 1,
    seconds) plus an exhaustive cross-check; output ``outputs/r6_o2_smoke/``.
``--analyse``
    Tables from ``records.jsonl`` (combine with a stage flag; default ``--manhattan``): LB, best
    V, gap and chosen layout per target and budget; rule / present-day / round-5 layouts with
    their exact V, the regret interval ``[V_rule - UB, V_rule - LB]`` and the exact-t 95 % CI
    over the scenarios of the paired difference ``V_rule - V_best``; the LP-gap gate; coverage.
    Writes ``RESULTS.md``.

Resume: re-run the same command.  The lower-level cache (``cache/``) returns every solved ILP
row, the cut pool (``cuts.jsonl``, signature-checked) restores every cut, records are
append-only.  A target that finished (``target_done`` record with the same configuration) is
skipped (its best layouts still seed the next target); ``--redo-target`` runs it again.  ``--wall-relaxed`` / ``--wall-written`` (hours) bound the two targets; inside,
``common.WallBudget`` shortens or skips ILP solves (``SKIPPED_BUDGET``, never mistaken for
infeasibility).

Second pass (``notes/o2_manhattan_first_pass.md``): ``--source-dir`` reads the records, cut pool
and cache of an earlier pass READ-ONLY and copies them once into ``--out-dir`` (the source is
never written); ``--resume-open`` ignores ``target_done`` records whose budgets are not all
certified or whose budget-free configuration hash (``config_md5_core``) differs, and restores
every LP solve (from the pool), pricing and LP prune of the target from the copied records, so
nothing solved before is solved again; ``--certify-budgets m ...`` enumerates these budgets
(with envelope pruning and escalation of the open pricing gaps), ``--skip-enumeration`` goes straight to the
Benders phases (LP phase, screen, integer phase) seeded with the pool; ``--lp-method`` chooses
the scenario-LP algorithm (``barrier`` = cold barrier per solve, the default; ``dual`` = the
first pass's warm-started dual simplex; ``concurrent``).  Every target now ends with a
bound-only master solve over the full pool, so ``LB`` is never missing in a ``budget_result``.
``--bound-from-cuts`` (with a stage flag) rebuilds the masters from a stored pool and reports
LB / best priced UB / gap / bound kind / ranked proposals per target and budget without any
LP or ILP solve (``BOUND.md`` and ``bound_from_cuts.jsonl`` in ``--out-dir``).

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r6_o2_siting.py --smoke
    python3 experiments/r6_o2_siting.py --midtown-validate --dry-run
    python3 experiments/r6_o2_siting.py --midtown-validate
    python3 experiments/r6_o2_siting.py --manhattan --dry-run
    python3 experiments/r6_o2_siting.py --manhattan
    python3 experiments/r6_o2_siting.py --manhattan --analyse
    python3 experiments/r6_o2_siting.py --manhattan --bound-from-cuts --source-dir outputs/r6_o2/manhattan \
        --out-dir outputs/r6_o2/manhattan_bound
    python3 experiments/r6_o2_siting.py --manhattan --resume-open --source-dir outputs/r6_o2/manhattan \
        --out-dir outputs/r6_o2/manhattan_pass2 --certify-budgets 1 --gate report

English only.  No E2 equation changes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebike_swap_sim import benders as BD  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import costs as cm  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from experiments import common as C  # noqa: E402

OUT_ROOT = os.path.join(C.OUTPUT_ROOT, "r6_o2")
E9_CACHE = os.path.join(C.OUTPUT_ROOT, "e9_bilevel", "cache")
BUDGET_UNIT = 50_000.0 + 3 * 450.0 + 2 * 400.0          # 52,150 USD (E9 convention)
TOY_UNIT = 130.0
MIDTOWN_EXPECTED = {"layout": "L02:SC:B2:C1", "UB": 676.223, "LB_min": 661.5}
R5_LAYOUTS = ("M06:SC:B4:C2|M12:S:B3:C0", "M08:SC:B3:C2|M09:SC:B3:C2")
TOY_MENU = {"S": [(1, 0), (2, 0)], "C": [(0, 1)], "SC": [(1, 1), (2, 1)]}
TOY_CANDIDATES = (("T1", 1), ("T2", 2), ("T3", 3), ("T4", 4))
#: 97.5 % quantiles of Student's t (fallback when scipy is missing), df 1..10
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def t975(df: int) -> float:
    try:
        from scipy import stats
        return float(stats.t.ppf(0.975, df))
    except Exception:  # noqa: BLE001
        return _T975.get(int(df), 1.96)


# ---------------------------------------------------------------------------
# run context
# ---------------------------------------------------------------------------
class Run:
    def __init__(self, stage: str, args: argparse.Namespace) -> None:
        self.stage = stage
        self.args = args
        root = args.out_root or (OUT_ROOT + "_smoke" if stage == "smoke" else OUT_ROOT)
        out_dir = getattr(args, "out_dir", None)
        self.dir = C.ensure_dir(os.path.abspath(out_dir) if out_dir else os.path.join(root, stage))
        self.records = os.path.join(self.dir, "records.jsonl")
        self.cuts = os.path.join(self.dir, "cuts.jsonl")
        self.cache = os.path.join(self.dir, "cache")
        self.source = os.path.abspath(getattr(args, "source_dir", None)) if getattr(args, "source_dir", None) else None
        if self.source is not None and os.path.realpath(self.source) == os.path.realpath(self.dir):
            raise SystemExit(f"--source-dir and the output directory are the same ({self.dir}); the source is read-only, "
                             "give a different --out-dir")
        self.t0 = time.perf_counter()

    def seed_from_source(self) -> Dict[str, Any]:
        """Copy the records, the cut pool and the lower-level cache of ``--source-dir`` into this
        run's directory ONCE (nothing is ever written into the source; cached rows keep working
        because their ``schedule_path`` is rewritten to the copied schedules).  A directory that
        already has ``records.jsonl`` is left as it is (the copy happened earlier)."""
        rec: Dict[str, Any] = {"kind": "seeded_from", "source": self.source, "copied": False}
        if self.source is None:
            return rec
        if os.path.exists(self.records):
            rec["note"] = "records.jsonl exists; not copied again"
            self.emit(rec)
            return rec
        n = {"records": 0, "cuts": 0, "cache_rows": 0, "schedules": 0, "skipped_lines": 0}
        src_rec = os.path.join(self.source, "records.jsonl")
        rows = load_jsonl_lenient(src_rec)
        n["records"] = len(rows)
        for r in rows:
            C.append_jsonl(self.records, r)
        src_cuts = os.path.join(self.source, "cuts.jsonl")
        if os.path.exists(src_cuts):
            good: List[str] = []
            with open(src_cuts, "r", encoding="utf-8") as fh:
                for ln in fh.read().splitlines():
                    if not ln.strip():
                        continue
                    try:
                        json.loads(ln)
                    except ValueError:
                        n["skipped_lines"] += 1
                        continue
                    good.append(ln)
            with open(self.cuts, "w", encoding="utf-8") as fh:
                fh.write("\n".join(good) + ("\n" if good else ""))
            n["cuts"] = max(0, len(good) - 1)
        src_cache = os.path.join(self.source, "cache")
        if os.path.isdir(src_cache):
            C.ensure_dir(os.path.join(self.cache, "schedules"))
            for name in ("bound.json",):
                p = os.path.join(src_cache, name)
                if os.path.exists(p):
                    shutil.copy2(p, os.path.join(self.cache, name))
            for row in load_jsonl_lenient(os.path.join(src_cache, "index.jsonl")):
                sp = row.get("schedule_path")
                if sp:
                    cand = [sp, os.path.join(src_cache, "schedules", os.path.basename(sp))]
                    src_sched = next((c for c in cand if os.path.exists(c)), None)
                    if src_sched is not None:
                        dst = os.path.join(self.cache, "schedules", os.path.basename(sp))
                        if not os.path.exists(dst):
                            shutil.copy2(src_sched, dst)
                            n["schedules"] += 1
                        row["schedule_path"] = dst
                    else:
                        row.pop("schedule_path", None)
                C.append_jsonl(os.path.join(self.cache, "index.jsonl"), row)
                n["cache_rows"] += 1
        rec.update(copied=True, **n)
        self.emit(rec, echo=True)
        return rec

    def emit(self, rec: Dict[str, Any], echo: bool = False) -> None:
        rec = {"stage": self.stage, **rec}
        C.append_jsonl(self.records, C.jsonable(rec))
        if echo or rec.get("kind") in ("budget_result", "acceptance", "baseline", "plan", "superset_bound"):
            keys = ("kind", "target", "budget", "best_layout", "UB", "LB", "gap", "certified", "close_reason", "rule",
                    "layout_key", "V", "status", "ok")
            print(json.dumps({k: C.jsonable(rec.get(k)) for k in keys if k in rec}), flush=True)
        elif rec.get("kind") == "price":
            print(json.dumps({k: C.jsonable(rec.get(k)) for k in ("kind", "target", "tag", "layout_key", "status", "V",
                                                                    "lower", "n_solves")}), flush=True)


def _layout_or_none(key: Optional[str]) -> Optional[BL.Layout]:
    return None if not key else BL.Layout.from_key(key)


def load_jsonl_lenient(path: str) -> List[Dict[str, Any]]:
    """Records of a JSON-lines file; a line that does not parse (half-written while another
    process appends) is skipped.  ``[]`` when the file is absent."""
    out: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
    return out


def rule_layouts(ev: BL.LowerLevelEvaluator, budgets: Sequence[float], size_menu: Dict[str, Any], D: int
                 ) -> Dict[Tuple[str, float], Optional[BL.Layout]]:
    """CSCD (demand within D blocks), CSTC (inverse-distance access, no singleton ILPs) and CSAV
    layouts at every budget, all SC with the menu's size caps."""
    sc = size_menu.get("SC") or [(1, 1)]
    capB, capC = max(b for b, _c in sc), max(c for _b, c in sc)
    base = min(sc, key=lambda bc: (bc[0] + bc[1], bc))
    w = {"CSCD": BL.demand_weights(ev.candidates, ev.scenarios, D, ev.p),
         "CSTC": BL.access_weights(ev.candidates, ev.scenarios, ev.p), "CSAV": None}
    out: Dict[Tuple[str, float], Optional[BL.Layout]] = {}
    for b in budgets:
        for rule in BL.RULES:
            out[(rule, b)] = BL.rule_layout(rule, ev.candidates, b, ev.spec, w[rule], role="SC", base_size=base,
                                            max_B=capB, max_C=capC)
    return out


def price_baseline(run: Run, cert: BD.SitingCertifier, name: str, lay: Optional[BL.Layout], b: float) -> Dict[str, Any]:
    """Exact (full) price of a comparison layout under the certifier's follower and target."""
    rec: Dict[str, Any] = {"kind": "baseline", "target": cert.target, "budget": b, "rule": name,
                           "layout_key": None if lay is None else lay.key()}
    if lay is None:
        rec.update(status="NONE", V=None)
    else:
        prev = cert.priced.get(lay.key())
        res = prev if (prev is not None and prev.status == "PRICED") else cert.price(lay, full=True, tag=f"baseline:{name}")
        rec.update(status=res.status, V=res.V, opex=res.ub, lb=res.lb, setup=res.setup,
                   investment=lay.investment(cert.ev.spec), in_menu=cert.enc.contains(lay),
                   within_budget=lay.investment(cert.ev.spec) <= b + 1e-6, served_share=res.served_share)
    run.emit(rec)
    return rec


def emit_best(run: Run, cert: BD.SitingCertifier, res: Dict[float, Dict[str, Any]]) -> None:
    for b, r in res.items():
        bp = cert.best_price[b]
        run.emit({"kind": "best_detail", "target": cert.target, "budget": b, "layout_key": r["best_layout"],
                  "opex": None if bp is None else bp.ub, "setup": None if bp is None else bp.setup})


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------
def build_midtown(run: Run, args: argparse.Namespace) -> Tuple[BL.LowerLevelEvaluator, Dict[str, Any]]:
    family = S.STRESS2_FAMILY
    all_c = S.family_candidates(family)
    cands = all_c[:4]
    depots = S.family_depots(family, all_c)
    scen = [S.make_base_instance(s, cands, family=family, depots=depots, n_bikes=6) for s in (0, 1)]
    spec = S.spec_from_instance(scen[0])
    if not os.path.exists(os.path.join(run.cache, "index.jsonl")):
        if not os.path.exists(os.path.join(E9_CACHE, "index.jsonl")):
            raise SystemExit(f"E9 cache not found at {E9_CACHE}")
        os.makedirs(run.cache, exist_ok=True)
        shutil.copy2(os.path.join(E9_CACHE, "index.jsonl"), os.path.join(run.cache, "index.jsonl"))
        if os.path.exists(os.path.join(E9_CACHE, "bound.json")):
            shutil.copy2(os.path.join(E9_CACHE, "bound.json"), os.path.join(run.cache, "bound.json"))
        if os.path.isdir(os.path.join(E9_CACHE, "schedules")) and not os.path.isdir(os.path.join(run.cache, "schedules")):
            shutil.copytree(os.path.join(E9_CACHE, "schedules"), os.path.join(run.cache, "schedules"))
    ev = BL.LowerLevelEvaluator(scen, spec, time_limit=args.time_limit, time_limit_hub=args.time_limit_hub,
                                threads=args.threads, params=dict(C.ILP_PARAMS_R3), cache_dir=run.cache,
                                relaxed_targets=False, verbose=True, reposition="all_candidates", aggregate=False)
    menu = {"S": [(1, 0), (2, 0)], "SC": [(1, 1), (2, 1)]}
    return ev, {"menu": menu, "roles": ("S", "SC"), "budgets": [BUDGET_UNIT], "candidates": [c.id for c in cands]}


def run_midtown(run: Run, args: argparse.Namespace) -> Dict[str, Any]:
    ev, cfg = build_midtown(run, args)
    lays = BL.enumerate_layouts(ev.candidates, BL.option_grid(cfg["menu"], cfg["roles"]), BUDGET_UNIT, ev.spec, (1,),
                                s_needs_charge=True)
    hits = sum(1 for l in lays for s in range(ev.n_scenarios) if ev.cache_key(l, s, "ilp") in ev.cache)
    plan = {"kind": "plan", "family": ev.family, "seeds": ev.seeds, "n_layouts": len(lays), "layouts": [l.key() for l in lays],
            "cached_rows_for_layouts": hits, "n_rows_needed": len(lays) * ev.n_scenarios, **cfg}
    run.emit(plan)
    if args.dry_run:
        return plan
    wall = C.WallBudget(args.wall_relaxed * 3600.0, margin_s=60.0, min_solve_s=30.0)
    ev.wall = wall
    L = ev.superset_bound(time_limit=args.time_limit)
    run.emit({"kind": "superset_bound", "bound": L, "rows": ev.bound_rows})
    pool = BD.CutPool(run.cuts, BD.pool_signature(ev))
    cert = BD.SitingCertifier(ev, cfg["budgets"], cfg["menu"], cfg["roles"], s_needs_charge=True, L=L, pool=pool,
                              tol_rel=args.tol_rel, tol_abs=args.tol_abs, lp_threads=args.lp_threads,
                              master_threads=args.master_threads, wall=wall, on_record=run.emit, label="midtown",
                              lp_workers=args.lp_workers, lp_method=args.lp_method,
                              max_escalations=0 if args.max_escalations is None else args.max_escalations)
    res = cert.run(warm_layouts=[], lp_phase=not args.no_lp_phase, screen=not args.no_screen)
    emit_best(run, cert, res)
    r = res[BUDGET_UNIT]
    ub, lb = r["UB"], r["LB"]
    exp = MIDTOWN_EXPECTED
    exp_price = cert.priced.get(exp["layout"])
    tie = (r["best_layout"] != exp["layout"] and exp_price is not None and exp_price.V is not None and ub is not None
           and abs(exp_price.V - ub) <= sum(p * ((u or 0.0) - l) for p, u, l in zip(ev.p, exp_price.ub, exp_price.lb)) + 1e-6)
    acc = {"kind": "acceptance", "best_layout": r["best_layout"], "UB": ub, "LB": lb, "gap": r["gap"],
           "same_layout": r["best_layout"] == exp["layout"], "tie_within_pricing_gaps": tie,
           "UB_matches": ub is not None and abs(ub - exp["UB"]) <= 1e-3,
           "LB_valid": isinstance(lb, float) and lb <= exp["UB"] + 1e-6, "LB_above_superset": isinstance(lb, float) and lb >= exp["LB_min"],
           "integrated_bound_E9": 668.04, "LB_LP": r["LB_LP"], "counters": r["counters"]}
    acc["ok"] = bool((acc["same_layout"] or tie) and acc["UB_matches"] and acc["LB_valid"] and acc["LB_above_superset"])
    run.emit(acc)
    cert.close()
    analyse(run)
    return acc


def build_manhattan(run: Run, args: argparse.Namespace) -> Tuple[BL.LowerLevelEvaluator, Dict[str, Any]]:
    family = S.R5_MANHATTAN_FAMILY
    cands = S.family_candidates(family)
    depots = S.family_depots(family, cands)
    pr = cm.R6_PRICING
    scen = []
    for s in args.seeds or [0, 1, 2]:
        base = S.make_base_instance(int(s), cands, family=family, depots=depots,
                                    n_bikes=int(S.SITING_FAMILIES[family]["n_bikes"]))
        rep = cm.reprice_orders(base, P=pr["P"], w=pr["w"], v=pr["v"],
                                source=f"experiments/r6_o2_siting.py; {pr['source']}")
        if C.demand_md5(rep) != C.demand_md5(base):
            raise AssertionError("repricing changed the demand side")
        scen.append(rep)
    spec = S.spec_from_instance(scen[0])
    ev = BL.LowerLevelEvaluator(scen, spec, time_limit=args.time_limit, time_limit_hub=args.time_limit_hub,
                                threads=args.threads, params=dict(C.ILP_PARAMS_R3), cache_dir=run.cache,
                                relaxed_targets=False, verbose=True, reposition="all_candidates", aggregate=True,
                                keep_libraries=2)
    menu = dict(S.SIZE_MENUS[family])
    budgets = [float(m) * BUDGET_UNIT for m in (args.budgets or [1, 2, 3, 4])]
    return ev, {"menu": menu, "roles": S.ROLES, "budgets": budgets, "D": S.access_radius_blocks(),
                "pricing": {k: pr[k] for k in ("P", "w", "v")}}


def build_smoke(run: Run, args: argparse.Namespace) -> Tuple[BL.LowerLevelEvaluator, Dict[str, Any]]:
    scen = [S.toy_base_instance(s, candidates=TOY_CANDIDATES) for s in (0, 1)]
    ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, params={"Seed": 0, "MIPGap": 0.0},
                                cache_dir=run.cache, reposition="all_candidates", aggregate=True)
    return ev, {"menu": TOY_MENU, "roles": S.ROLES, "budgets": [TOY_UNIT, 2 * TOY_UNIT], "D": 1}


def run_siting(run: Run, args: argparse.Namespace, smoke: bool = False) -> Dict[str, Any]:
    if run.source is not None:
        run.seed_from_source()                  # before the evaluator reads the cache index
    ev, cfg = (build_smoke if smoke else build_manhattan)(run, args)
    budgets = cfg["budgets"]
    unit = TOY_UNIT if smoke else BUDGET_UNIT
    plan = {"kind": "plan", "family": ev.family, "seeds": ev.seeds, "budgets": budgets, "menu": cfg["menu"],
            "n_candidates": len(ev.candidates), "candidates": [c.id for c in ev.candidates],
            "pricing": cfg.get("pricing"), "targets": args.targets, "demand_md5": ev.demand_md5,
            "price_signatures": [cm.pricing_cache_component(i) for i in ev.scenarios]}
    enc = BD.MenuEncoding([c.id for c in ev.candidates], cfg["menu"], cfg["roles"], ev.spec)
    plan["n_options_per_location"] = len(enc.options)
    plan["n_master_binaries"] = enc.n
    if smoke or len(budgets) <= 2 or args.dry_run:
        counts = {}
        for b in budgets:
            k = int(math.floor((b + 1e-9) / float(enc.inv.min())))
            if k <= 2:
                counts[str(b)] = len(BL.enumerate_layouts(ev.candidates, enc.options, b, ev.spec, range(1, k + 1),
                                                          s_needs_charge=True))
        plan["admissible_layouts"] = counts
    rules = rule_layouts(ev, budgets, cfg["menu"], int(cfg.get("D", 14)))
    plan["warm_layouts"] = {f"{r}@m{b / unit:g}": (None if l is None else
                                                   {"key": l.key(), "in_menu": enc.contains(l),
                                                    "investment": l.investment(ev.spec)})
                            for (r, b), l in rules.items()}
    if args.access_D is not None:
        cfg["access"] = BL.access_sets(ev.candidates, ev.scenarios, int(args.access_D))
        plan["access"] = {"D_blocks": int(args.access_D), "n_zones": len(cfg["access"]),
                          "empty_zones": sorted(z for z, ls in cfg["access"].items() if not ls)}
    cfg_md5 = config_md5(ev, cfg, args)
    cfg_md5_core = config_md5(ev, cfg, args, core=True)
    plan["config_md5"] = cfg_md5
    plan["config_md5_core"] = cfg_md5_core
    S_n = ev.n_scenarios
    esc = int(2 if args.max_escalations is None else args.max_escalations)
    lv = {}
    for name, base in (("swap", args.time_limit), ("hub", args.time_limit_hub)):
        tls, prev = [], base
        for k in range(1, esc + 1):
            t = min(1800.0, base * 3.0 ** k)
            if t > prev + 1e-9:
                tls.append(t)
            prev = t
        lv[name] = {"levels_s": tls, "worst_case_per_layout_s": S_n * sum(tls)}
    plan["escalation_estimate"] = {"note": "one scenario per escalation call; levels per (layout, scenario); "
                                           "in addition to the base pricing (about 6 min per priced layout)", **lv}
    run.emit(plan)
    if args.dry_run:
        print(json.dumps(C.jsonable(plan["warm_layouts"]), indent=1), flush=True)
        print(json.dumps(C.jsonable(plan["escalation_estimate"]), indent=1), flush=True)
        return plan
    t_s = time.perf_counter()
    L = ev.superset_bound(time_limit=args.time_limit)
    run.emit({"kind": "superset_bound", "bound": L, "rows": ev.bound_rows, "wall_s": time.perf_counter() - t_s})
    lps = [BD.ScenarioLP(ev, s, threads=args.lp_threads, method=args.lp_method) for s in range(ev.n_scenarios)]
    run.emit({"kind": "lp_sizes", "sizes": [lp.size for lp in lps], "lp_method": args.lp_method,
              "lp_threads": args.lp_threads, "lp_workers": args.lp_workers})
    pool = BD.CutPool(run.cuts, BD.pool_signature(ev))
    run.emit({"kind": "pool_loaded", "n_cuts": len(pool.cuts), "by_kind": pool.counts(), "skipped_lines": pool.n_skipped})
    r5 = [] if smoke else [BL.Layout.from_key(k) for k in R5_LAYOUTS]
    pdw = BL.present_day_sites(ev.candidates)
    run.emit({"kind": "present_day_source", "source": pdw["source"], "proxy": pdw["proxy"], "n_points": pdw["n_points"]})
    pd_warm = []
    for b in budgets:
        ref = rules[("CSAV", b)]
        if ref is not None:
            pd_warm.append(BL.capacity_matched_layout(ev.candidates, ref, pdw["weights"], ev.spec, role="SC"))
    access = cfg.get("access")
    done = {} if args.redo_target else finished_targets(run, cfg_md5, resume_open=args.resume_open, budgets=budgets,
                                                        md5_core=cfg_md5_core)
    out: Dict[str, Any] = {}
    prev_best: List[BL.Layout] = []
    for target in args.targets:
        if target in done:
            d = done[target]
            prev_best = [BL.Layout.from_key(k) for k in d.get("best_layouts") or [] if k]
            out[target] = d.get("results")
            run.emit({"kind": "target_skipped", "target": target,
                      "reason": ("target_done record with every budget certified" if args.resume_open
                                 else "target_done record with the same configuration"),
                      "best_layouts": d.get("best_layouts")}, echo=True)
            continue
        evt = ev if target == "written" else ev.derive(relaxed_targets=True)
        wall = C.WallBudget((args.wall_relaxed if target == "relaxed" else args.wall_written) * 3600.0,
                            margin_s=60.0, min_solve_s=30.0)
        evt.wall = wall
        cert = BD.SitingCertifier(evt, budgets, cfg["menu"], cfg["roles"], s_needs_charge=True, L=L, lps=lps, pool=pool,
                                  access=access, tol_rel=args.tol_rel, tol_abs=args.tol_abs,
                                  master_threads=args.master_threads, wall=wall, on_record=run.emit, label=target,
                                  lp_workers=args.lp_workers, wall_margin_s=max(120.0, 60.0 * args.reserve_min),
                                  max_escalations=2 if args.max_escalations is None else args.max_escalations)
        if args.resume_open:
            cert.restore(load_jsonl_lenient(run.records))
        warm = [l for l in rules.values() if l is not None] + pd_warm + r5 + prev_best
        cert.warm_start(warm)
        gate = gate_after_warm(run, cert, args, budgets, unit)
        if not args.no_lp_phase:
            cert.lp_phase()
        if not args.no_screen:
            cert.screen()
        cert.integer_phase()
        # comparison layouts under the same follower and target, BEFORE the results (they can lower UB)
        for b in budgets:
            for rule in BL.RULES:
                price_baseline(run, cert, rule, rules[(rule, b)], b)
            ref = cert.best[b] if b > unit + 1e-6 else (rules[("CSAV", b)] or cert.best[b])
            pd_lay = None if ref is None else BL.capacity_matched_layout(ev.candidates, ref, pdw["weights"], ev.spec,
                                                                          role="SC")
            price_baseline(run, cert, "present_day", pd_lay, b)
            for k in r5:
                if k.investment(ev.spec) <= b + 1e-6:
                    price_baseline(run, cert, "round5:" + k.key(), k, b)
        res = cert.finish(final_master_s=args.final_master_s)
        emit_best(run, cert, res)
        if not args.no_cross_eval:
            cross_followers(run, cert, evt)
        if args.with_greedy:
            g = BL.greedy_local_search(evt, ev.candidates, max(budgets), size_menu=cfg["menu"], budget_levels=budgets,
                                       screen=BD.LPScreen(cert), k_screen=2, s_needs_charge=True)
            for b, r in g["per_budget"].items():
                run.emit({"kind": "greedy_lp_screen", "target": target, "budget": b,
                          "layout_key": None if r["layout"] is None else r["layout"].key(), "V": r["value"],
                          "status": r["status"]})
        if smoke:
            for b in budgets:
                lays = BL.enumerate_layouts(ev.candidates, enc.options, b, ev.spec, range(1, 3), s_needs_charge=True,
                                            access=cert.access_nonempty())
                vals = [(evt.value(l), l.key()) for l in lays]
                best = min(vals)
                r = res[b]
                ok = r["UB"] is not None and abs(best[0] - r["UB"]) <= 1e-6 and isinstance(r["LB"], float) \
                    and r["LB"] <= best[0] + 1e-6
                run.emit({"kind": "acceptance", "target": target, "budget": b, "exhaustive_V": best[0],
                          "exhaustive_layout": best[1], "UB": r["UB"], "LB": r["LB"], "ok": ok, "n_layouts": len(lays)})
        prev_best = [l for l in cert.best.values() if l is not None]
        out[target] = {str(b): r for b, r in res.items()}
        run.emit({"kind": "target_done", "target": target, "config_md5": cfg_md5, "config_md5_core": cfg_md5_core,
                  "gate": gate.get("action"),
                  "best_layouts": [None if l is None else l.key() for l in cert.best.values()],
                  "results": out[target]}, echo=True)
        cert.close()
    for lp in lps:
        lp.dispose()
    analyse(run)
    return out


def config_md5(ev: BL.LowerLevelEvaluator, cfg: Dict[str, Any], args: argparse.Namespace, core: bool = False) -> str:
    """Configuration of a siting run that a finished target must match to be skipped on resume.
    ``core=True``: the same without the budget list (``--resume-open`` lets the budgets differ
    between passes and nothing else)."""
    d = {"family": ev.family, "seeds": ev.seeds, "demand": ev.demand_md5,
         "prices": [cm.pricing_cache_component(i) for i in ev.scenarios], "budgets": cfg["budgets"],
         "menu": {k: [list(x) for x in v] for k, v in cfg["menu"].items()}, "roles": list(cfg["roles"]),
         "access_D": args.access_D, "tol": [args.tol_rel, args.tol_abs], "spec": ev.spec.to_dict(),
         "max_escalations": args.max_escalations, "gate": args.gate}
    if core:
        d.pop("budgets")
        d["core"] = True
    return BL._md5(d)


def finished_targets(run: Run, md5: str, resume_open: bool = False,
                     budgets: Optional[Sequence[float]] = None, md5_core: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """``target_done`` records of this run directory with configuration ``md5`` (last one wins).
    With ``resume_open`` a target counts as finished only when its results cover every
    requested budget, all of them are certified, AND its budget-free configuration hash
    ``config_md5_core`` equals ``md5_core`` (a wall-stopped target is run again, restored from the
    pool and the records; a pass over other budgets is not skipped; a certified row of another
    configuration -- tolerances, menu, prices, access rows, escalations, gate -- is NOT skipped
    and a ``target_not_skipped`` record says so)."""
    out: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(run.records):
        return out
    for r in load_jsonl_lenient(run.records):
        if r.get("kind") != "target_done":
            continue
        if resume_open:
            res = r.get("results") or {}
            have = {round(float(k), 3): v for k, v in res.items()}
            want = [round(float(b), 3) for b in (budgets or have.keys())]
            if not have or not all(b in have and bool(have[b].get("certified")) for b in want):
                out.pop(r["target"], None)
                continue
            if md5_core is not None and r.get("config_md5_core") != md5_core:
                run.emit({"kind": "target_not_skipped", "target": r.get("target"),
                          "reason": "target_done row certified but its configuration differs (budget-free hash); "
                                    "the target is run again",
                          "stored_config_md5_core": r.get("config_md5_core"), "config_md5_core": md5_core,
                          "stored_config_md5": r.get("config_md5")}, echo=True)
                out.pop(r["target"], None)
                continue
        elif r.get("config_md5") != md5:
            continue
        out[r["target"]] = r
    return out


def gate_after_warm(run: Run, cert: BD.SitingCertifier, args: argparse.Namespace, budgets: Sequence[float],
                    unit: float) -> Dict[str, Any]:
    """Design section 8 step 3: median fixed-layout LP gap over the warm-start cells, and the
    action it calls for (enumeration of the smallest budget when > 2 %)."""
    cells = sorted(cert.lp_gap_cells())
    g = cells[len(cells) // 2] if cells else None
    if g is None:
        action = "none (no fully priced warm layout)"
    elif g <= 0.005:
        action = "default design"
    elif g <= 0.02:
        action = "S1/S2 recommended (not implemented; Benders continues)"
    else:
        action = "certify smallest budget by enumeration"
    if g is not None and g > 0.02 and args.gate == "abort":
        action = "abort"
    certify = getattr(args, "certify_budgets", None)
    skip = bool(getattr(args, "skip_enumeration", False))
    limit = int(getattr(args, "enum_limit", 5000) or 5000)
    rec = {"kind": "gate", "target": cert.target, "n_cells": len(cells), "median": g,
           "max": cells[-1] if cells else None, "action": action, "mode": args.gate,
           "certify_budgets": certify, "skip_enumeration": skip}
    run.emit(rec, echo=True)
    if action == "abort":
        raise SystemExit(f"LP-gap gate: median {100 * g:.2f} % > 2 % (--gate abort)")
    if skip:
        return rec
    if certify:
        todo = [b for b in budgets if any(abs(b / unit - float(m)) <= 1e-6 for m in certify)]
    elif action.startswith("certify") and args.gate == "auto":
        todo = [min(budgets)]
    else:
        todo = []
    for b0 in todo:
        e = cert.certify_by_enumeration(b0, limit=limit)
        run.emit({"kind": "gate_enumeration", "target": cert.target, "m": b0 / unit,
                  **{k: e.get(k) for k in ("done", "reason", "n_layouts", "LB_enum", "LB_floor", "UB", "gap", "close_reason",
                                           "n_lp", "n_envelope_pruned", "n_priced", "n_lp_pruned")}},
                 echo=True)
    return rec


def cross_followers(run: Run, cert: BD.SitingCertifier, evt: BL.LowerLevelEvaluator) -> None:
    """The best layout of every budget under the R2.3 policy (``baseline``) and the selfish
    follower (same target, same library convention); ``V_ilp`` = its ILP value."""
    seen: Dict[str, List[float]] = {}
    for b, lay in cert.best.items():
        if lay is not None:
            seen.setdefault(lay.key(), []).append(b)
    for key, bs in seen.items():
        lay = BL.Layout.from_key(key)
        pr = cert.priced.get(key)
        for pol in ("baseline", "selfish"):
            try:
                r = evt.evaluate(lay, pol)
                rec = {"V": r.get("V"), "status": r.get("status"), "served_share": r.get("served_share")}
            except Exception as exc:  # noqa: BLE001 -- recorded, never fatal for the certificate
                rec = {"V": None, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
            run.emit({"kind": "cross_follower", "target": cert.target, "budgets": bs, "layout_key": key, "policy": pol,
                      "V_ilp": None if pr is None else pr.V, **rec}, echo=True)


# ---------------------------------------------------------------------------
# bound from a stored cut pool (no LP / ILP solve)
# ---------------------------------------------------------------------------
def records_state(records: Sequence[Dict[str, Any]], target: str) -> Dict[str, Any]:
    """What the records of ``target`` already know: ``v_lp`` (safe LP value per layout, from the
    ``lp_layout`` records), ``priced`` (``(status, lower)`` per layout, last ``price`` record),
    ``ub_rows`` (priced menu layouts with their ``V`` and investment), ``enumerate`` records per
    budget and the ``budget_result`` rows (last per budget)."""
    v_lp: Dict[str, float] = {}
    priced: Dict[str, Tuple[str, float]] = {}
    ub_rows: List[Tuple[str, float, float]] = []
    enum: Dict[float, Dict[str, Any]] = {}
    results: Dict[float, Dict[str, Any]] = {}
    prior: Dict[float, float] = {}
    for r in records:
        if r.get("target") != target:
            continue
        k = r.get("kind")
        if k == "lp_layout" and r.get("layout_key") and r.get("v_LP") is not None:
            v_lp[r["layout_key"]] = float(r["v_LP"])
        elif k == "price" and r.get("layout_key") and r.get("status") != BL.SKIPPED_BUDGET:
            key = r["layout_key"]
            lower = r.get("lower")
            if lower is not None:
                priced[key] = (str(r.get("status")), float(lower))
            if r.get("status") == "PRICED" and r.get("V") is not None and r.get("in_master") and r.get("investment") is not None:
                ub_rows.append((key, float(r["V"]), float(r["investment"])))
        elif k == "enumerate" and r.get("budget") is not None:
            enum[float(r["budget"])] = r
        elif k == "budget_result" and r.get("budget") is not None:
            results[float(r["budget"])] = r
            lb = r.get("LB")
            if isinstance(lb, (int, float)) and math.isfinite(float(lb)):
                prior[float(r["budget"])] = float(lb)
    return {"v_lp": v_lp, "priced": priced, "ub_rows": ub_rows, "enumerate": enum, "results": results, "prior": prior}


def bound_from_pool(ev: BL.LowerLevelEvaluator, cfg: Dict[str, Any], pool_path: str, records: Sequence[Dict[str, Any]],
                    targets: Sequence[str], L: Sequence[float], *, with_cover: bool = True, top: int = 5,
                    threads: int = 1, time_limit: Optional[float] = 120.0, enum_limit: int = 5000,
                    use_prior: bool = False, on_record: Any = None) -> List[Dict[str, Any]]:
    """Masters per target and budget from the stored pool (``applies_to`` filter: relaxed cuts
    serve the written master, never the reverse), the superset bound ``L``, the cover rows
    (``with_cover``; needs the all-candidates templates) and nested-budget propagation
    (:func:`benders.pool_bound`).  ``UB`` = best priced ``V`` of a menu layout within the budget
    from the records; the enumeration floor is added for budgets whose enumeration started
    (``enumerate`` record) with at most ``enum_limit`` layouts.  ``use_prior`` also folds the
    ``LB`` of the stored ``budget_result`` rows in (default off: the bound is recomputed from the
    pool alone).  Returns one row per (target, budget)."""
    enc = BD.MenuEncoding([c.id for c in ev.candidates], cfg["menu"], cfg["roles"], ev.spec)
    pool = BD.CutPool(pool_path, BD.pool_signature(ev), read_only=True)
    covers = BD.cover_sets(ev, enc.objects) if with_cover else None
    access = cfg.get("access")
    rows: List[Dict[str, Any]] = []
    budgets = sorted(float(b) for b in cfg["budgets"])
    for target in targets:
        master = BD.Master(enc, ev.p, L, s_needs_charge=True, access=access, covers=covers, threads=threads)
        n_added = 0
        for c in pool.for_target(target):
            n_added += int(master.add_cut(c))
        st = records_state(records, target)
        access_rows = None if not access else {z: ls for z, ls in access.items() if z not in set(master.access_empty)}
        enum_lays: Dict[float, List[BL.Layout]] = {}
        for b in budgets:
            e = st["enumerate"].get(b)
            if e is not None and int(e.get("n_layouts") or 0) <= enum_limit:
                enum_lays[b] = BD.menu_layouts(ev, enc, b, access=access_rows, s_needs_charge=True)
        ub: Dict[float, float] = {}
        ub_lay: Dict[float, Optional[str]] = {}
        for b in budgets:
            cands = [(v, key) for key, v, inv in st["ub_rows"] if inv <= b + 1e-6 and master.rows_ok(BL.Layout.from_key(key))]
            if cands:
                v, key = min(cands)
                ub[b], ub_lay[b] = v, key
        res = BD.pool_bound(master, enc, ev.p, L, budgets, ub=ub, enum_layouts=enum_lays, v_lp=st["v_lp"],
                            priced=st["priced"], prior=(st["prior"] if use_prior else None), time_limit=time_limit,
                            pool_solutions=top)
        for b in budgets:
            r = res[b]
            ranked = []
            for val, key in r.get("ranked") or []:
                pr = st["priced"].get(key)
                ranked.append({"layout_key": key, "envelope": val, "v_LP": st["v_lp"].get(key),
                               "priced_status": None if pr is None else pr[0], "priced_lower": None if pr is None else pr[1],
                               "resolved": bool(r.get("UB") is not None and val >= r["UB"] - BD.tolerance(r["UB"], 0.0025, 1.0) - 1e-9)})
            lb_val, lb_kind, gap = r["LB"], r["kind"], r.get("gap")
            if lb_val is not None and not math.isfinite(lb_val):
                # master infeasible at this budget (no admissible layout): nothing to bound
                lb_val, lb_kind, gap = None, BD.NO_ADMISSIBLE, None
            row = {"kind": "bound_from_cuts", "target": target, "budget": b, "LB": lb_val, "LB_kind": lb_kind,
                   "components": r["components"], "UB": r.get("UB"), "UB_layout": ub_lay.get(b), "gap": gap,
                   "master_status": r["master_status"], "master_bound": r["master_bound"], "master_obj": r["master_obj"],
                   "master_runtime_s": r["master_runtime_s"], "proposal": r["proposal"], "ranked": ranked,
                   "enumeration": r["enumeration"], "n_cuts_in_master": n_added, "n_cuts_by_kind": pool.counts(target),
                   "n_cuts_pool": len(pool.cuts), "n_cover_rows": len(master.cover_rows), "with_cover": bool(with_cover),
                   "stored_LB": (st["results"].get(b) or {}).get("LB"), "stored_UB": (st["results"].get(b) or {}).get("UB"),
                   "stored_close_reason": (st["results"].get(b) or {}).get("close_reason")}
            rows.append(row)
            if on_record is not None:
                on_record(row)
        master.dispose()
    return rows


def bound_from_cuts(run: Run, args: argparse.Namespace, smoke: bool = False) -> List[Dict[str, Any]]:
    """``--bound-from-cuts``: rebuild the masters from the pool of ``--source-dir`` (read-only;
    default: this stage's own directory) and write ``bound_from_cuts.jsonl`` and ``BOUND.md`` to
    ``--out-dir`` (default ``<stage>_bound`` next to the stage).  No LP or ILP is solved; the
    superset bound is taken from the source's ``superset_bound`` record (else recomputed into
    this run's own cache)."""
    src = run.source or os.path.join(os.path.dirname(run.dir), run.stage)
    if os.path.realpath(src) == os.path.realpath(run.dir):
        raise SystemExit("--bound-from-cuts writes into --out-dir, which must differ from the source directory")
    records = load_jsonl_lenient(os.path.join(src, "records.jsonl"))
    pool_path = os.path.join(src, "cuts.jsonl")
    if not os.path.exists(pool_path):
        raise SystemExit(f"no cut pool at {pool_path}")
    ev, cfg = (build_smoke if smoke else build_manhattan)(run, args)
    if args.access_D is not None:
        cfg["access"] = BL.access_sets(ev.candidates, ev.scenarios, int(args.access_D))
    L: Optional[List[float]] = None
    for r in records:
        if r.get("kind") == "superset_bound" and r.get("bound"):
            L = [float(x) for x in r["bound"]]
    if L is None or len(L) != ev.n_scenarios:
        L = ev.superset_bound(time_limit=args.time_limit)
    unit = TOY_UNIT if smoke else BUDGET_UNIT
    run.emit({"kind": "bound_from_cuts_setup", "source": src, "L": L, "targets": args.targets, "with_cover": not args.no_cover,
              "n_records": len(records)})
    rows = bound_from_pool(ev, cfg, pool_path, records, args.targets, L, with_cover=not args.no_cover, top=args.top,
                           threads=args.master_threads, time_limit=args.final_master_s, enum_limit=args.enum_limit,
                           use_prior=args.use_prior, on_record=lambda r: run.emit(r))
    path = os.path.join(run.dir, "bound_from_cuts.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(C.jsonable(r)) + "\n")
    lines = [f"# O2 bound from the stored cut pool -- {run.stage}", "",
             f"Source `{src}` (read-only); generated {time.strftime('%Y-%m-%d %H:%M')}.  LB = max(master ObjBound over the "
             f"full pool with cover rows, superset trivial bound, enumeration floor where the enumeration started), "
             f"nested over budgets; UB = best priced V of a menu layout within the budget (records).  No LP or ILP solved.", ""]
    t = [{"target": r["target"], "m": round(r["budget"] / unit, 3), "LB": r["LB"], "kind": r["LB_kind"], "UB": r["UB"],
          "UB_layout": r["UB_layout"], "gap": None if r["gap"] is None else 100 * r["gap"], "master": r["master_bound"],
          "sup": r["components"].get("superset"), "enum": r["components"].get("enumeration"),
          "n_cuts": r["n_cuts_in_master"], "cover": r["n_cover_rows"], "status": r["master_status"],
          "stored_LB": r["stored_LB"], "stored_UB": r["stored_UB"]} for r in rows]
    lines += _table(t, [("target", "target"), ("m", "m"), ("LB", "LB"), ("kind", "bound kind"), ("UB", "UB"),
                        ("UB_layout", "UB layout"), ("gap", "gap %"), ("master", "master bound"), ("sup", "superset"),
                        ("enum", "enumeration floor"), ("n_cuts", "cuts"), ("cover", "cover rows"), ("status", "master status"),
                        ("stored_LB", "stored LB"), ("stored_UB", "stored UB")], 3) + [""]
    for r in rows:
        lines.append(f"## {r['target']}, m = {r['budget'] / unit:g}: ranked master proposals")
        lines.append("")
        lines += _table([{"rank": i + 1, **x} for i, x in enumerate(r["ranked"])],
                        [("rank", "rank"), ("layout_key", "layout"), ("envelope", "envelope"), ("v_LP", "v_LP"),
                         ("priced_status", "priced"), ("priced_lower", "priced lower"), ("resolved", "resolved (>= UB - tol)")], 3)
        lines.append("")
        lines.append(f"Cuts by kind:target in this master: `{json.dumps(r['n_cuts_by_kind'])}`; enumeration: "
                     f"`{json.dumps(C.jsonable(r['enumeration']))}`")
        lines.append("")
    md = os.path.join(run.dir, "BOUND.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    for r in rows:
        print(json.dumps(C.jsonable({k: r[k] for k in ("target", "budget", "LB", "LB_kind", "UB", "UB_layout", "gap",
                                                          "master_status", "proposal")})), flush=True)
    print(f"# wrote {md}", flush=True)
    return rows


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def _fmt(v: Any, d: int = 2) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return f"{v:,d}"
    if isinstance(v, float):
        if not math.isfinite(v):
            return "inf"
        return f"{v:,.{d}f}"
    return str(v).replace("|", "\\|")


def _table(rows: Sequence[Dict[str, Any]], cols: Sequence[Tuple[str, str]], d: int = 2) -> List[str]:
    out = ["| " + " | ".join(h for _k, h in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_fmt(r.get(k), d) for k, _h in cols) + " |")
    return out


def analyse(run: Run) -> str:
    recs = C.load_jsonl(run.records)
    res: Dict[Tuple[str, float], Dict[str, Any]] = {}
    base: Dict[Tuple[str, float, str], Dict[str, Any]] = {}
    best: Dict[Tuple[str, float], Dict[str, Any]] = {}
    lp_lay: Dict[Tuple[str, str], Dict[str, Any]] = {}
    prices: Dict[Tuple[str, str], Dict[str, Any]] = {}
    acc = [r for r in recs if r.get("kind") == "acceptance"]
    for r in recs:
        k = r.get("kind")
        if k == "budget_result":
            res[(r["target"], float(r["budget"]))] = r
        elif k == "baseline":
            base[(r["target"], float(r["budget"]), r["rule"])] = r
        elif k == "best_detail":
            best[(r["target"], float(r["budget"]))] = r
        elif k == "lp_layout":
            lp_lay[(r["target"], r["layout_key"])] = r
        elif k == "price":
            prices[(r["target"], r["layout_key"])] = r
    unit = TOY_UNIT if run.stage == "smoke" else BUDGET_UNIT
    lines = [f"# O2 certified siting -- {run.stage}", "",
             f"Records `{run.records}`; cut pool `{run.cuts}`; cache `{run.cache}`.  Generated "
             f"{time.strftime('%Y-%m-%d %H:%M')}.", ""]
    # problems first ----------------------------------------------------------------------
    probs: List[str] = []
    for (t, b), r in sorted(res.items()):
        if not r.get("certified"):
            probs.append(f"{t}, m = {b / unit:g}: NOT certified (gap {_fmt(100 * r['gap'] if r.get('gap') is not None else None)} %, "
                         f"stop: {r.get('close_reason')}).")
        if (r.get("served_share") or 1.0) < 0.5:
            probs.append(f"{t}, m = {b / unit:g}: best layout serves only {_fmt(r['served_share'], 3)} of the orders.")
        cov = r.get("coverage") or {}
        if cov.get("checked") and cov.get("n_open"):
            probs.append(f"{t}, m = {b / unit:g}: {cov['n_open']} layouts still open at stop (brute-force check; "
                         f"{cov.get('n_open_priced', 0)} of them priced with open ILP gaps).")
        msg = (f"{t}: artificial columns active in some LP (max {_fmt(r.get('max_artificial'), 4)} bikes): the bound LP "
               "is elastic at some (fractional or infeasible) points; validity unaffected.")
        if (r.get("max_artificial") or 0.0) > 1e-6 and msg not in probs:
            probs.append(msg)
    for a in acc:
        if not a.get("ok"):
            probs.append(f"acceptance FAILED: {json.dumps({k: a.get(k) for k in ('budget', 'target', 'best_layout', 'UB', 'LB', 'exhaustive_V')})}")
    lines += ["## Problems (read first)", ""] + ([f"* {p}" for p in probs] or ["* none"]) + [""]
    # table 1 --------------------------------------------------------------------------------
    t1 = []
    for (t, b), r in sorted(res.items()):
        c = r.get("counters") or {}
        st = r.get("ilp_status") or {}
        t1.append({"target": t, "m": round(b / unit, 3), "layout": r.get("best_layout"), "inv": r.get("investment"), "UB": r.get("UB"),
                   "LB": r.get("LB") if isinstance(r.get("LB"), (int, float)) else None, "LB_kind": r.get("LB_kind"),
                   "gap": None if r.get("gap") is None else 100 * r["gap"], "cert": r.get("certified"),
                   "LB_LP": r.get("LB_LP"), "sup": r.get("LB_superset"), "priced": c.get("priced"),
                   "lp_pruned": c.get("lp_pruned"), "bound_stop": c.get("pruned_by_bound"), "infeas": c.get("infeasible"),
                   "ilp": ", ".join(f"{k} {v}" for k, v in sorted(st.items())), "lp_solves": c.get("lp_solves"),
                   "wall_min": (r.get("wall_s") or 0.0) / 60.0, "served": r.get("served_share")})
    lines += ["## Table 1 -- certified bound per target and budget", "",
              "UB = best feasible V found (exact up to the MIP gaps of its rows; ILP follower, all-candidates "
              "library); LB = master bound (valid lower bound on "
              "V*_m); gap = (UB - LB) / UB; LB_LP = LP-phase master bound; superset = min setup + superset LP bound.  "
              "Counters (priced ... LP solves, wall) are per target run, shared by its budgets.", ""]
    lines += _table(t1, [("target", "target"), ("m", "m"), ("layout", "best layout"), ("inv", "inv USD"), ("UB", "UB"),
                         ("LB", "LB"), ("LB_kind", "bound kind"), ("gap", "gap %"), ("cert", "certified"), ("LB_LP", "LB_LP"),
                         ("sup", "superset"),
                         ("priced", "priced"), ("lp_pruned", "LP-pruned"), ("bound_stop", "bound-stopped"),
                         ("infeas", "infeasible"), ("ilp", "ILP solves by status"), ("lp_solves", "LP solves"),
                         ("wall_min", "wall min"), ("served", "served share")], 3) + [""]
    # table 2 --------------------------------------------------------------------------------
    t2 = []
    for (t, b, rule), r in sorted(base.items()):
        br = res.get((t, b), {})
        bd = best.get((t, b), {})
        UB = br.get("UB")
        LB = br.get("LB") if isinstance(br.get("LB"), (int, float)) else None
        V = r.get("V")
        row = {"target": t, "m": round(b / unit, 3), "rule": rule, "layout": r.get("layout_key"), "V": V, "status": r.get("status"),
               "UB": UB}
        if V is not None and UB is not None:
            row["reg_lo"] = V - UB
            row["reg_hi"] = None if LB is None else V - LB
            row["reg_lo_pct"] = 100 * (V - UB) / V
            row["reg_hi_pct"] = None if LB is None else 100 * (V - LB) / V
        ob, orl = bd.get("opex"), r.get("opex")
        if ob and orl and all(x is not None for x in ob) and all(x is not None for x in orl) and len(ob) == len(orl) > 1:
            d = [a - c for a, c in zip(orl, ob)]
            n = len(d)
            mean = sum(d) / n
            sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1))
            h = t975(n - 1) * sd / math.sqrt(n)
            dsetup = (r.get("setup") or 0.0) - (bd.get("setup") or 0.0)
            row.update(diff=dsetup + mean, ci_lo=dsetup + mean - h, ci_hi=dsetup + mean + h)
        t2.append(row)
    lines += ["## Table 2 -- rule, present-day and round-5 layouts against the certified bound", "",
              "Regret interval [V_rule - UB, V_rule - LB]: how much worse the rule layout is than the best found (lower end) "
              "and than any layout can be at most (upper end).  diff = V_rule - V_best with the exact-t 95 % CI over the "
              "scenarios (paired OPEX differences; uniform p).", ""]
    lines += _table(t2, [("target", "target"), ("m", "m"), ("rule", "layout rule"), ("layout", "layout"), ("V", "V"),
                         ("status", "status"), ("reg_lo", "regret lo"), ("reg_hi", "regret hi"), ("reg_lo_pct", "lo %"),
                         ("reg_hi_pct", "hi %"), ("diff", "V_rule - V_best"), ("ci_lo", "CI lo"), ("ci_hi", "CI hi")]) + [""]
    # gate and coverage ------------------------------------------------------------------------------
    gaps: Dict[str, List[float]] = {}
    for (t, key), pr in prices.items():
        lr = lp_lay.get((t, key))
        if lr is None or pr.get("status") != "PRICED" or not pr.get("ub"):
            continue
        for qi, ql in zip(pr["ub"], lr.get("Qs") or []):
            if qi is not None and ql is not None and abs(qi) > 1e-9:
                gaps.setdefault(t, []).append((qi - ql) / abs(qi))
    t3 = []
    for t, g in sorted(gaps.items()):
        g = sorted(g)
        med = g[len(g) // 2]
        t3.append({"target": t, "n": len(g), "median": 100 * med, "max": 100 * g[-1],
                   "exact": 100 * sum(1 for x in g if x <= 1e-6) / len(g),
                   "gate": "default design" if med <= 0.005 else ("S1/S2 needed" if med <= 0.02 else "certify m = 1 only")})
    lines += ["## Table 3 -- fixed-layout LP gap (measurement gate) and coverage", "",
              "(Q_IP - Q_LP) / Q_IP over the scenario cells of every fully priced layout (Q_LP = safe Benders value).", ""]
    lines += _table(t3, [("target", "target"), ("n", "cells"), ("median", "median %"), ("max", "max %"),
                         ("exact", "exact cells %"), ("gate", "gate")], 3) + [""]
    cov_rows = [{"target": t, "m": round(b / unit, 3),
                 **{k: (r.get("coverage") or {}).get(k) for k in ("checked", "n_layouts", "n_open", "n_open_priced", "reason")},
                 "stuck": r.get("n_stuck"), "explore": (r.get("counters") or {}).get("explore_proposals")}
                for (t, b), r in sorted(res.items())]
    lines += _table(cov_rows, [("target", "target"), ("m", "m"), ("checked", "brute-force checked"),
                               ("n_layouts", "layouts"), ("n_open", "open at stop"), ("n_open_priced", "of which priced (open gaps)"),
                               ("stuck", "stuck layouts"), ("explore", "exploration proposals"), ("reason", "note")]) + [""]
    gates = [r for r in recs if r.get("kind") in ("gate", "gate_enumeration")]
    if gates:
        lines += ["Gate records (measured after the warm start, acted on during the run):", ""]
        lines += [f"* `{json.dumps(C.jsonable({k: v for k, v in g.items() if k not in ('stage',)}))}`" for g in gates] + [""]
    xf = [r for r in recs if r.get("kind") == "cross_follower"]
    if xf:
        lines += ["## Table 4 -- best layouts under other followers", "",
                  "Same layout, same target; V under the R2.3 policy (`baseline`) and the selfish follower against its ILP value.", ""]
        lines += _table([{"target": r.get("target"), "layout": r.get("layout_key"), "policy": r.get("policy"),
                          "V": r.get("V"), "V_ilp": r.get("V_ilp"), "status": r.get("status"),
                          "served": r.get("served_share")} for r in xf],
                        [("target", "target"), ("layout", "layout"), ("policy", "follower"), ("V", "V"),
                         ("V_ilp", "V (ILP)"), ("status", "status"), ("served", "served share")], 3) + [""]
    if acc:
        lines += ["## Acceptance", ""] + [f"* `{json.dumps(C.jsonable({k: v for k, v in a.items() if k not in ('counters',)}))}`"
                                          for a in acc] + [""]
    lines += ["## Caveats", "",
              "* Every ILP value is an upper bound on the unpruned written optimum (PRUNING_NYC); V* is the optimum under the "
              "all-candidates library convention (values are not comparable one to one with round-5 `open_sites` numbers).",
              "* Certificates hold for this scenario set (seeds listed in the plan record) and this library only; CIs over "
              "three scenarios are wide by construction.",
              "* LB is valid under solver tolerances: LP cuts are safe Lagrangian bounds (C1), integer cuts use Gurobi "
              "ObjBound minus C_setup (C3)."]
    path = os.path.join(run.dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"# wrote {path}", flush=True)
    return path


# ---------------------------------------------------------------------------
def default_max_threads() -> int:
    """Thread budget of one process (the ``deploy/aws/run_lanes.sh`` rule): 1.5 solver threads
    per physical core (EC2 vCPUs are hyperthreads, two per core), at most ``nproc - 1``."""
    n = os.cpu_count() or 4
    cores = max(1, n // 2)
    return max(1, min(n - 1, cores * 3 // 2))


def check_thread_budget(args: argparse.Namespace) -> int:
    """R7: ``lp_workers x lp_threads + master_threads <= --max-threads`` (default
    :func:`default_max_threads`) replaces the former hard-coded laptop cap of 12 cores."""
    if getattr(args, "max_threads", None) is None:
        args.max_threads = default_max_threads()
    if args.lp_workers * args.lp_threads + args.master_threads > args.max_threads:
        raise SystemExit(f"lp_workers x lp_threads + master_threads must be at most --max-threads {args.max_threads} "
                         "(default: the run_lanes.sh rule, 1.5 per physical core)")
    return int(args.max_threads)


def main(argv: Optional[List[str]] = None) -> Any:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--midtown-validate", action="store_true")
    ap.add_argument("--manhattan", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="toy pipeline, Threads 1, seconds")
    ap.add_argument("--analyse", action="store_true", help="tables from the records only (no solve)")
    ap.add_argument("--dry-run", action="store_true", help="plan and cache-key check, no solve")
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--threads", type=int, default=3, help="Threads of every pricing ILP (default 3)")
    ap.add_argument("--lp-threads", type=int, default=3,
                    help="Threads of every scenario LP (default 3: barrier scales; 3 workers x 3 threads + 2 master "
                         "threads = 11 of 12 cores)")
    ap.add_argument("--master-threads", type=int, default=2)
    ap.add_argument("--max-threads", type=int, default=None,
                    help="thread budget lp_workers x lp_threads + master_threads (R7: replaces the laptop cap of 12; "
                         "default = the run_lanes.sh rule, 1.5 per physical core, at most nproc - 1)")
    ap.add_argument("--lp-workers", type=int, default=3,
                    help="scenario LPs solved in parallel (threads of Python; default 3 = one per Manhattan scenario)")
    ap.add_argument("--reserve-min", type=float, default=60.0,
                    help="manhattan: minutes of each target's wall kept for the comparison layouts after the search")
    ap.add_argument("--time-limit", type=float, default=300.0)
    ap.add_argument("--time-limit-hub", type=float, default=600.0)
    ap.add_argument("--wall-relaxed", type=float, default=9.0, help="hours for the relaxed target (midtown: whole run)")
    ap.add_argument("--wall-written", type=float, default=10.0, help="hours for the written target")
    ap.add_argument("--tol-rel", type=float, default=0.0025)
    ap.add_argument("--tol-abs", type=float, default=1.0)
    ap.add_argument("--budgets", nargs="*", type=float, default=None, help="manhattan: budget multipliers m")
    ap.add_argument("--seeds", nargs="*", type=int, default=None, help="manhattan: scenario seeds (default 0 1 2)")
    ap.add_argument("--targets", nargs="*", default=["relaxed", "written"], choices=["relaxed", "written"])
    ap.add_argument("--no-lp-phase", action="store_true")
    ap.add_argument("--no-screen", action="store_true")
    ap.add_argument("--max-escalations", type=int, default=None,
                    help="re-pricings of a binding TIME_LIMIT layout with TimeLimit x3, x9 (cap 1800 s); "
                         "default 0 for --midtown-validate, 2 otherwise")
    ap.add_argument("--with-greedy", action="store_true", help="also run the greedy with the LP screen (comparison)")
    ap.add_argument("--gate", choices=["auto", "report", "abort"], default="auto",
                    help="LP-gap gate after the warm start: auto = enumerate the smallest budget when the median "
                         "gap > 2 %%; report = record only; abort = stop when > 2 %%")
    ap.add_argument("--access-D", type=int, default=None,
                    help="manhattan / smoke: [U4] access rows with radius D blocks (sensitivity; default none)")
    ap.add_argument("--no-cross-eval", action="store_true", help="skip the baseline / selfish cross-evaluation")
    ap.add_argument("--redo-target", action="store_true", help="re-run targets that already have a target_done record")
    # second pass (notes/o2_manhattan_first_pass.md)
    ap.add_argument("--lp-method", choices=list(BD.LP_METHODS), default="barrier",
                    help="scenario-LP algorithm: barrier = cold barrier + crossover per solve (default), dual = "
                         "warm-started dual simplex (LPWarmStart 2), concurrent = Gurobi Method 3")
    ap.add_argument("--source-dir", default=None,
                    help="directory of an earlier pass (records.jsonl, cuts.jsonl, cache/) read READ-ONLY and copied "
                         "once into --out-dir; nothing is written into it")
    ap.add_argument("--out-dir", default=None, help="output directory of this pass (default outputs/r6_o2/<stage>)")
    ap.add_argument("--resume-open", action="store_true",
                    help="ignore target_done records whose budgets are not all certified or whose budget-free "
                         "configuration differs; restore LP solves (pool), pricings and LP prunes (records) of the "
                         "target before searching")
    ap.add_argument("--certify-budgets", nargs="*", type=float, default=None,
                    help="budget multipliers m to certify by enumeration (envelope pruning) regardless of the gate")
    ap.add_argument("--skip-enumeration", action="store_true",
                    help="no enumeration: Benders phases (LP phase, screen, integer phase) seeded with the pool")
    ap.add_argument("--enum-limit", type=int, default=5000, help="largest admissible layout count enumerated")
    ap.add_argument("--final-master-s", type=float, default=120.0,
                    help="time limit of the bound-only master solve that closes every target / budget")
    ap.add_argument("--bound-from-cuts", action="store_true",
                    help="rebuild the masters from the stored pool of --source-dir (read-only) and report LB / UB / gap "
                         "per target and budget into --out-dir (no LP or ILP solve)")
    ap.add_argument("--no-cover", action="store_true", help="bound-from-cuts: omit the a-priori cover rows (no templates)")
    ap.add_argument("--use-prior", action="store_true",
                    help="bound-from-cuts: also fold the LB of the stored budget_result rows in")
    ap.add_argument("--top", type=int, default=5, help="bound-from-cuts: ranked master proposals per budget")
    args = ap.parse_args(argv)
    stages = [s for s, f in (("midtown_validate", args.midtown_validate), ("manhattan", args.manhattan),
                             ("smoke", args.smoke)) if f]
    if not stages:
        if args.analyse or args.bound_from_cuts:
            stages = ["manhattan"]
        else:
            raise SystemExit("choose --midtown-validate, --manhattan, --smoke and/or --analyse")
    if args.smoke:
        args.threads = args.lp_threads = args.master_threads = args.lp_workers = 1
        args.reserve_min = 0.0
        args.tol_rel, args.tol_abs = 1e-9, 1e-6
    if max(args.threads, args.lp_threads, args.master_threads) > 6:
        raise SystemExit("Threads per solve at most 6")
    check_thread_budget(args)
    if "relaxed" in args.targets and "written" in args.targets:
        args.targets = ["relaxed", "written"]        # relaxed cuts seed the written run (C16), never the reverse
    if args.bound_from_cuts and not args.out_dir:
        root = args.out_root or (OUT_ROOT + "_smoke" if args.smoke else OUT_ROOT)
        args.out_dir = os.path.join(root, stages[0] + "_bound")
    warnings.simplefilter("ignore")
    out: Dict[str, Any] = {}
    for stage in stages:
        run = Run(stage, args)
        if args.bound_from_cuts:
            out[stage] = bound_from_cuts(run, args, smoke=(stage == "smoke"))
            continue
        if args.analyse:
            out[stage] = analyse(run)
            continue
        if stage == "midtown_validate":
            out[stage] = run_midtown(run, args)
        else:
            out[stage] = run_siting(run, args, smoke=(stage == "smoke"))
        if not args.dry_run:
            with open(os.path.join(run.dir, "wall_time.json"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"wall_s": time.perf_counter() - run.t0, "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
                                     "args": vars(args)}) + "\n")
    return out


if __name__ == "__main__":
    main()
