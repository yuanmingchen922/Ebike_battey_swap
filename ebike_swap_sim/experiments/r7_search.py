"""R7 production search driver (``notes/siting_production_plan.md`` section 5 item 6; stages P, E, F, H,
I and R of section 2.1).  It runs on the configuration, records, cut pool and cache of
``experiments/r7_siting.py`` (same ``--out-dir`` and the same configuration flags, so the same
``Ctx``, ``config_md5``, pool signature and cache keys) and changes no core module: every bound
is a ``SitingCertifier`` bound of the pool (safe Lagrangian / subset cuts, the S_LP rule, the
budget-window rule of ``benders.setup_min``), every value an all-candidates pricing.

Stages (``--stage a,b`` or ``all`` = pairs, m3, roles, oos, noradius; each appends to
``records.jsonl`` / ``cuts.jsonl`` / ``cache/`` and resumes from them):

``calib``      stage P: one 12-cell pricing (template, library and solve times separated: is the
               library build serialised by the GIL?), one one-cell free-size LP with and without
               crossover, and 8 one-site LPs as 3 workers x 3 threads against 4 x 2.
``oos-feas``   held-out feasibility check of the out-of-sample list (library builds only): a
               layout with a bike without a reachable terminal arc in a held-out scenario is
               reported "infeasible out of sample" instead of being priced.
``pairs``      stage E: m = 2 seeds (``--pair-seeds``, the transplanted pairs, the two best m = 1
               locations, stage-A coverage complements, relax-and-round of the master LP point)
               and 1-swap neighbours of the best seed, each screened by ``cert.subset_bound([a, b],
               S_LP)`` (memoised in ``cuts.jsonl``): the pair bound ``setup_min(2, {a, b}, inv <=
               budget_2) + sum_s p_s LBA_s`` holds for EVERY layout with open set exactly {a, b}
               and every size combination; the window bound ``min_k setup_min(k, {a, b},
               (budget_1, budget_2]) + ...`` covers the layouts inside {a, b} that the m = 1
               certificate does not.  The best ``--pair-price`` pairs are priced at their
               envelope-best sizes (BestBdStop against UB_2).
``m3``         stage F: the best pair at the largest sizes, the best pair plus each of the
               ``--m3-thirds`` best m = 1 locations (optionally screened by triple subset LPs).
``roles``      stage H: role table at ``--role-budgets`` (default m = 2): best layout, best
               S-containing layout (at the best pairs) and best hub-containing layout (hub screen:
               ``subset_bound({h} + best pair)`` on ``--hub-scenarios`` scenarios for every
               hub-capable site h, the best ``--role-hub-price`` priced at the hub limit).
``oos``        stage I: the out-of-sample list (``--oos-layouts``, default best@m1 best@m2 CSCD@m2
               dot_all_pilot) on the held-out scenarios: feasibility check first, then pricing.
``noradius``   stage R: every m = 1 layout within ``--near-tie`` (3 %) of UB_1 plus best@m2 and
               best@m3 re-priced on an evaluator with the approach radius UNSET (scenario-major,
               ``--noradius-group`` templates resident, the radius schedule as MIP start).
``price-list`` list pricing of ``--layouts`` / ``--layouts-file`` on ``--evaluator in | out |
               noradius``; ``--tier open_sites`` (re-plan change 2: upper bounds only, resumed per
               layout), the m = 1 list rule ``--layouts m1-lp-order --lp-order-below V`` with
               ``--extend-below-ub on`` (M1 / M1-rest), and for the all-candidates bound probe
               ``--cells`` / ``--warm-tier open_sites`` / ``--ilp-params`` (M3 / M5, change 5).
``import-records`` (re-plan change 3) ``--from DIR``: the price / price_open records and cache rows
               of another out-dir of the same instance (never its budget results, K3.4).
``ub-check``   (re-plan M6, K3.5) the open-sites schedules of ``--layouts`` (default best@m1)
               checked on the all-candidates library (``ub_check_all_candidates`` record).
``report``     ``SEARCH.md`` (pair screens, m = 3, role rows, out-of-sample, radius effect, list
               pricing, UB check, cost).

R7 re-plan after batch 2 (``notes/siting_production_replan_m1.md``, critic K1-K7), change 7:
``--price-tier open_sites`` makes pairs, m3, roles, oos and noradius report open-sites values (a
feasible value of the all-candidates follower, i.e. a valid UB; always full pricing, K2.7); every
lower bound stays all-candidates (envelope / LP / subset cuts / ``L_s``), open-sites ILP bounds are
labelled ``lower_open`` / ``lb_open`` and never used as all-candidates bounds.  Default
``all_candidates``: the older behaviour.

Modes: ``--dry-run`` (plans only), ``--smoke`` (the toy of ``r7_siting.py``), ``--write-lanes``
(the production lane plan of section 2.1 / 2.2 for ``deploy/aws/run_lanes.sh`` in
``outputs/cloud_lanes_siting_prod/``; ``--lanes-plan r2``: ``lanes_r2.txt`` and
``lanes_r2_tier2.txt`` of the re-plan, change 9).  Every invocation appends a row to
``cost.jsonl`` (``experiments/r7_cost.py``).

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r7_search.py --smoke --budgets 1 2 3 --stage all
    python3 experiments/r7_search.py --stage pairs --dry-run --scenarios 12 --held-out --approach-radius 14
    python3 experiments/r7_search.py --write-lanes

English only.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import json
import math
import os
import sys
import time
import warnings
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebike_swap_sim import benders as BD  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r7_cost as RC  # noqa: E402
from experiments import r7_siting as R  # noqa: E402

INF = BL.INF
SEARCH_STAGES = ("calib", "oos-feas", "pairs", "m3", "roles", "oos", "noradius", "price-list", "import-records", "ub-check",
                 "report")
ALL_STAGES = ("pairs", "m3", "roles", "oos", "noradius", "report")
#: default --wall hours per stage (plan section 2.1 central estimate + margin)
WALL_H = {"calib": 1.5, "oos-feas": 1.0, "pairs": 5.0, "m3": 2.0, "roles": 3.5, "oos": 2.5, "noradius": 5.0,
          "price-list": 4.0, "import-records": 0.5, "ub-check": 1.0, "report": 0.5}
#: stages without LP / pricing pools (library builds or files only)
POOL_FREE = ("oos-feas", "report", "import-records", "ub-check")
#: stages that run on every invocation (resume inside the stage, never skipped by a stage_done record)
ALWAYS_RUN = ("report", "price-list", "import-records", "ub-check")
#: the m = 1 list rule of the re-plan (``--layouts m1-lp-order``, section 2.1 M1 / M1-rest)
M1_LP_ORDER = "m1-lp-order"
PROD_LANES_ROOT = os.path.join(C.OUTPUT_ROOT, "cloud_lanes_siting_prod")
OOS_DEFAULT = ("best@m1", "best@m2", "CSCD@m2", "dot_all_pilot")
#: the step-2b probe pool (N = 59, S = 12, radius 14): its all-open subset cuts become root files
#: when the signature matches (``r7_siting.py --root-import``; refused and recorded otherwise)
STEP2B_POOL = "outputs/r7_siting_probe/dot_Nall_S12/cuts.jsonl"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _f(x: Any) -> Optional[float]:
    return None if x is None or not math.isfinite(float(x)) else float(x)


_BULKY = ("lba", "rows", "opex_noradius", "opex_out", "ci_out", "ci_in", "ci_out_plain", "pairs", "template_s", "configs",
          "lb", "ub", "infeasible_bikes", "lb_open", "lb_open_noradius", "cells", "extend_candidates")


def say(run: R.Run, rec: Dict[str, Any]) -> None:
    """Record ``rec`` (as ``Run.emit``, without its echo) and print it without its bulky fields."""
    rec = {"stage": run.stage, **rec}
    C.append_jsonl(run.records, C.jsonable(rec))
    txt = json.dumps(C.jsonable({k: v for k, v in rec.items() if k not in _BULKY}))
    print(txt if len(txt) <= 600 else txt[:597] + "...", flush=True)


def stage_tag(st: str) -> str:
    return "search_" + st.replace("-", "_")


def stage_done(records: Sequence[Dict[str, Any]], st: str, md5: str) -> bool:
    return R.stage_done(records, stage_tag(st), md5)


def budget_of(ctx: R.Ctx, m: int) -> Optional[float]:
    b = float(m) * ctx.unit
    return b if any(abs(b - x) < 1e-6 for x in ctx.budgets) else None


def smaller_budget(ctx: R.Ctx, b: float) -> float:
    sm = [x for x in ctx.budgets if x < b - 1e-6]
    return sm[-1] if sm else -INF


def wall_h(args: argparse.Namespace, st: str) -> float:
    return float(args.wall) if args.wall is not None else WALL_H[st]


def options_at(ctx: R.Ctx, loc: str) -> List[Tuple[str, int, int]]:
    return [o for o in ctx.enc.options if o[0] in ctx.ev.roles_of.get(loc, ())]


def layouts_at(ctx: R.Ctx, cert: BD.SitingCertifier, locs: Iterable[str], budget: float,
               k: Optional[Sequence[int]] = None, pred=None, inv_lo: float = -INF) -> List[BL.Layout]:
    """Admissible menu layouts inside the master (``in_master``: structural, cover, terminal and
    no-good rows) whose open locations lie in ``locs`` (exactly ``k`` of them), investment in
    ``(inv_lo, budget]``, filtered by ``pred``."""
    locs = sorted(set(str(l) for l in locs))
    cands = [c for c in ctx.candidates if c.id in set(locs)]
    grid = {l: options_at(ctx, l) for l in locs}
    ks = list(k) if k is not None else list(range(1, len(locs) + 1))
    lays = BL.enumerate_layouts(cands, grid, budget, ctx.spec, ks, s_needs_charge=True)
    out = []
    for l in lays:
        if l.investment(ctx.spec) <= inv_lo + 1e-9:
            continue
        if not cert.in_master(l) or (pred is not None and not pred(l)):
            continue
        out.append(l)
    return out


def best_by_envelope(cert: BD.SitingCertifier, lays: Sequence[BL.Layout]) -> Optional[Tuple[float, BL.Layout]]:
    best = None
    for l in lays:
        env = cert.master.envelope(l)
        if not math.isfinite(env):
            continue
        if best is None or (env, l.key()) < (best[0], best[1].key()):
            best = (env, l)
    return best


def size_targets(ctx: R.Ctx, recs: Sequence[Dict[str, Any]]) -> Dict[str, Tuple[int, int]]:
    """Per location the (B, C) of its best known one-site layout (priced V, else LP), the sizes a
    multi-site layout of the search starts from."""
    out: Dict[str, Tuple[int, int]] = {}
    for loc, d in one_site_values(recs, R.tiers_of(ctx.run.args)).items():
        key = d.get("V_layout") or d.get("v_LP_layout")
        try:
            it = BL.Layout.from_key(str(key)).open[0]
            out[loc] = (int(it[2]), int(it[3]))
        except (ValueError, IndexError, KeyError):
            continue
    return out


def pick_layout(ctx: R.Ctx, cert: BD.SitingCertifier, lays: Sequence[BL.Layout],
                targets: Dict[str, Tuple[int, int]]) -> Optional[Tuple[float, BL.Layout]]:
    """The layout of a location set to price: the sizes closest to each location's one-site best
    (SC; the representative B3:C2 where unknown; S at the same B; a hub at its largest C), ties by
    the master envelope.  The envelope alone would pick the cheapest set-up (every size
    combination of a set shares the subset cut), which prices small stations that cannot win.
    A heuristic choice of WHICH layout to price: no bound depends on it."""
    rep = cert.rep_option() or R.sc_screen_option(ctx)
    cmax = max([o[2] for o in ctx.enc.options if o[0] == "C"] or [0])

    def dist(l: BL.Layout) -> float:
        d = 0.0
        for loc, r, B, Cc in l.open:
            tB, tC = targets.get(loc, (rep[1], rep[2]))
            if r == "SC":
                d += abs(B - tB) + abs(Cc - tC)
            elif r == "S":
                d += abs(B - tB)
            else:
                d += abs(Cc - cmax)
        return d
    best = None
    for l in lays:
        env = cert.master.envelope(l)
        if not math.isfinite(env):
            continue
        k = (dist(l), env, l.key())
        if best is None or k < best[0]:
            best = (k, l)
    return None if best is None else (best[0][1], best[1])


def pair_next_layout(cert: BD.SitingCertifier, lays: Sequence[BL.Layout], tried: Iterable[str],
                     b: float) -> Tuple[Optional[Tuple[float, BL.Layout]], str]:
    """The next layout of a pair to price after a PRUNED_BY_BOUND / INFEASIBLE try (fixer pass):
    the untried layout of the pair with the lowest master envelope (SC + S and smaller sizes
    included; the envelope is re-read, it rises with the integer cuts of every pricing), skipping
    layouts already resolved (priced PRUNED_BY_BOUND / INFEASIBLE).  ``(None, reason)`` when none
    is left or the lowest envelope already reaches ``UB_b - tol`` (then every layout of the pair is
    resolved: no layout of the pair below ``UB_b - tol``)."""
    tried = set(tried)
    rest = []
    for l in lays:
        k = l.key()
        prev = cert.priced.get(k)
        if k in tried or (prev is not None and prev.status in ("PRUNED_BY_BOUND", "INFEASIBLE")):
            continue
        env = cert.master.envelope(l)
        if math.isfinite(env):
            rest.append((env, k, l))
    if not rest:
        return None, "every layout of the pair tried or resolved"
    env, _k, l = min(rest)
    ub = cert.UB[b]
    if math.isfinite(ub) and env >= ub - cert.tol(ub) - 1e-9:
        return None, "the lowest envelope of the remaining layouts reaches UB - tol (pair resolved)"
    return (env, l), ""


def one_site_values(recs: Sequence[Dict[str, Any]], tiers: Sequence[str] = ("all_candidates",)) -> Dict[str, Dict[str, Any]]:
    """Per location: the best priced one-site value (``V``, all sizes) and the best one-site LP
    value (``v_LP``) in the records (relaxed target); ``score`` = V if priced, else v_LP.
    ``tiers`` with ``'open_sites'`` (re-plan change 7): the ``price_open`` values count as V too
    (upper bounds; the m = 1 ranking of the open-sites pass)."""
    out: Dict[str, Dict[str, Any]] = {}

    def put(loc: str, k: str, v: float, key: str) -> None:
        d = out.setdefault(loc, {})
        if d.get(k) is None or v < d[k]:
            d[k] = float(v)
            d[k + "_layout"] = key
    for r in recs:
        if r.get("target", "relaxed") != "relaxed":
            continue
        kind = r.get("kind")
        try:
            if kind == "price" and r.get("status") == "PRICED" and r.get("V") is not None \
                    and r.get("tier", "all_candidates") == "all_candidates":
                lay = BL.Layout.from_key(r["layout_key"])
                if lay.n_open == 1:
                    put(lay.open[0][0], "V", float(r["V"]), lay.key())
            elif kind == "lp_location" and r.get("v_LP") is not None:
                put(str(r["location"]), "v_LP", float(r["v_LP"]), str(r.get("layout_key")))
            elif kind == "lp_layout" and r.get("v_LP") is not None:
                lay = BL.Layout.from_key(r["layout_key"])
                if lay.n_open == 1:
                    put(lay.open[0][0], "v_LP", float(r["v_LP"]), lay.key())
            elif kind == "price_open" and "open_sites" in tiers and r.get("status") == "PRICED" and r.get("V") is not None:
                lay = BL.Layout.from_key(r["layout_key"])
                if lay.n_open == 1:
                    put(lay.open[0][0], "V", float(r["V"]), lay.key())
        except (KeyError, ValueError, TypeError):
            continue
    for d in out.values():
        d["score"] = d.get("V") if d.get("V") is not None else d.get("v_LP")
    return out


def m1_rank(ctx: R.Ctx, recs: Sequence[Dict[str, Any]], exclude: Iterable[str] = (),
            feasible_only: bool = True) -> List[str]:
    """Locations by their one-site value (priced V, else v_LP), then by CSCD demand weight for the
    locations without a value; proven terminal-infeasible locations last (or dropped with
    ``feasible_only``).  Only locations with a swap role."""
    vals = one_site_values(recs, R.tiers_of(ctx.run.args))
    infeas = infeasible_locations(ctx)
    w = demand_weights(ctx)
    ex = set(exclude)
    locs = [l for l in ctx.ids if l not in ex and any(r in ("S", "SC") for r in ctx.ev.roles_of.get(l, ()))]
    if feasible_only:
        locs = [l for l in locs if l not in infeas]

    def key(l: str):
        sc = (vals.get(l) or {}).get("score")
        return (l in infeas, sc is None, sc if sc is not None else 0.0, -w.get(l, 0.0), l)
    return sorted(locs, key=key)


_DW: Dict[int, Dict[str, float]] = {}


def infeasible_locations(ctx: R.Ctx) -> set:
    """Proven terminal-infeasible locations (``Ctx.feasibility``); empty in ``--dry-run``, where a
    screen of another signature would otherwise be re-proved by library builds."""
    return set() if ctx.run.args.dry_run else set(ctx.feasibility())


def demand_weights(ctx: R.Ctx) -> Dict[str, float]:
    k = id(ctx)
    if k not in _DW:
        _DW[k] = BL.demand_weights(ctx.ev.candidates, ctx.ev.scenarios, ctx.D, ctx.ev.p)
    return _DW[k]


def feas_bikes(run: R.Run) -> Dict[str, Dict[int, set]]:
    """``{loc: {scenario: infeasible bike ids}}`` from every one-site screen of ``--out-dir`` (stage
    ``feas`` files; used for the coverage-complement SEEDS only, never for a bound)."""
    out: Dict[str, Dict[int, set]] = {}
    for p in sorted(glob.glob(os.path.join(run.dir, "feas_one_site*.json"))):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        for r in d.get("rows") or []:
            if not r.get("n_infeasible_bikes"):
                continue
            try:
                lay = BL.Layout.from_key(str(r["layout_key"]))
            except (KeyError, ValueError):
                continue
            if lay.n_open != 1:
                continue
            out.setdefault(lay.open[0][0], {}).setdefault(int(r["scenario"]), set()).update(
                str(x[0]) for x in (r.get("infeasible") or []))
    return out


def best_with_sites(ctx: R.Ctx, recs: Sequence[Dict[str, Any]], b: float, k: int) -> Optional[Tuple[str, float]]:
    """Best layout with exactly ``k`` open sites within ``b`` among the price records with a value
    (PRICED, or a feasible V of a bound-stopped pricing; with ``--price-tier open_sites`` also the
    PRICED ``price_open`` records)."""
    best = None
    use_open = "open_sites" in R.tiers_of(ctx.run.args)
    for r in recs:
        is_open = use_open and r.get("kind") == "price_open" and r.get("status") == "PRICED"
        if not is_open and (r.get("kind") != "price" or r.get("tier", "all_candidates") != "all_candidates"
                            or r.get("status") not in ("PRICED", "PRUNED_BY_BOUND")):
            continue
        if r.get("target") != "relaxed" or r.get("V") is None:
            continue
        try:
            lay = BL.Layout.from_key(r["layout_key"])
        except (KeyError, ValueError):
            continue
        if lay.n_open == k and lay.investment(ctx.spec) <= b + 1e-6 and (best is None or float(r["V"]) < best[1] - 1e-9):
            best = (lay.key(), float(r["V"]))
    return best


def best_known(ctx: R.Ctx, recs: Sequence[Dict[str, Any]], m: int) -> Optional[str]:
    """The best known layout within budget m: the last ``budget_result``'s incumbent, unless a
    layout priced later (a search stage, the restricted master) has a lower V (fixer pass)."""
    b = budget_of(ctx, m)
    if b is None:
        return None
    r = R.last_results(recs).get(b)
    bk = R.best_layout_at(recs, b, ctx.spec, tiers=R.tiers_of(ctx.run.args))
    if r is not None and r.get("best_layout"):
        ub = r.get("UB")
        if bk is not None and (ub is None or bk[1] < float(ub) - 1e-9):
            return bk[0]
        return str(r["best_layout"])
    return None if bk is None else bk[0]


def resolve_layout(ctx: R.Ctx, recs: Sequence[Dict[str, Any]], name: str) -> Tuple[Optional[str], str]:
    """Layout key of a list name: ``best@mK``, ``<RULE>@mK`` (comparison record, else the rule
    layout), ``dot_all_pilot``, ``dot_pilot_proxy@mK``, or a literal layout key."""
    n = str(name)
    if n.startswith("best@m"):
        k = best_known(ctx, recs, int(n.split("@m")[1]))
        return k, "records" if k else "unknown (no priced layout yet)"
    if "@m" in n:
        rule, m = n.split("@m")
        b = budget_of(ctx, int(m))
        if b is None:
            return None, f"budget m = {m} not in --budgets"
        rows = [x for x in recs if x.get("kind") == "baseline" and x.get("rule") == rule and x.get("layout_key")
                and abs(float(x.get("budget") or -1) - b) < 1e-6]
        if rows:
            return str(rows[-1]["layout_key"]), "comparison record"
        if rule in BL.RULES:
            lay = R.rule_layouts(ctx).get((rule, b))
            return (None, "rule layout empty") if lay is None else (lay.key(), "rule layout")
        return None, "no comparison record"
    if n == "dot_all_pilot":
        lay = BL.dot_pilot_layout(ctx.candidates)
        return (None, "no pilot site") if lay is None else (lay.key(), "dot_pilot_layout")
    try:
        return BL.Layout.from_key(n).key(), "literal"
    except (ValueError, KeyError):
        return None, "not a layout key"


def parse_locsets(ctx: R.Ctx, toks: Optional[Sequence[str]]) -> Tuple[List[frozenset], List[Dict[str, Any]]]:
    """``A|B`` location pairs or layout keys -> location sets (unknown ids dropped and listed)."""
    out, bad = [], []
    for t in toks or []:
        for part in str(t).split():
            locs = [x.split(":")[0] for x in part.replace("+", "|").replace(",", "|").split("|") if x]
            if not locs or any(l not in set(ctx.ids) for l in locs) or len(set(locs)) != len(locs):
                bad.append({"seed": part, "reason": "unknown or repeated location"})
                continue
            out.append(frozenset(locs))
    return out, bad


# ---------------------------------------------------------------------------
# bounds of a location set (design 2.3; budget-window rule of benders.certify_bnb)
# ---------------------------------------------------------------------------
def set_bound(ctx: R.Ctx, cert: BD.SitingCertifier, A: Iterable[str], b: float, scenarios: Sequence[int],
              tag: str) -> Dict[str, Any]:
    """Subset LP bound of the location set ``A`` at budget ``b``: ``LBA_s`` on ``scenarios`` (S_LP
    rule: ``L_s`` elsewhere, valid), then

    * ``bound_exact`` = ``setup_min(|A|, A, inv <= b) + sum_s p_s LBA_s``: valid for every
      admissible layout whose open set is EXACTLY ``A`` (every size combination);
    * ``bound_window`` = ``min_k setup_min(k, A, (b_prev, b]) + ...``: valid for every layout
      inside ``A`` with investment in the window above the smaller budget (the layouts the
      smaller budget's certificate does not cover); ``inf`` when the window is empty."""
    A = sorted(set(A))
    lba = cert.subset_bound(A, list(scenarios), tag=tag)
    base = sum(p * x for p, x in zip(cert.p, lba))
    lo = smaller_budget(ctx, b)
    sm_exact = BD.setup_min(cert.enc, len(A), A, cert.s_needs_charge, -INF, b)
    sm_win = min(BD.setup_min(cert.enc, k, A, cert.s_needs_charge, lo, b) for k in range(1, len(A) + 1))
    return {"atoms": A, "budget": b, "m": int(round(b / ctx.unit)), "scenarios": list(scenarios), "lba": lba,
            "opex_floor": base, "setup_min_exact": _f(sm_exact), "bound_exact": _f(sm_exact + base) if math.isfinite(sm_exact) else None,
            "setup_min_window": _f(sm_win), "bound_window": _f(sm_win + base) if math.isfinite(sm_win) else None,
            "window": [_f(lo), b]}


def excluded(cert: BD.SitingCertifier, b: float, bound: Optional[float]) -> Optional[bool]:
    ub = cert.UB[b]
    if not math.isfinite(ub):
        return None
    return bound is None or bound >= ub - cert.tol(ub) - 1e-9


# ---------------------------------------------------------------------------
# certifier / pricing helpers
# ---------------------------------------------------------------------------
def certifier(run: R.Run, ctx: R.Ctx, st: str, pricing_only: bool = False) -> BD.SitingCertifier:
    """The stage's certifier, restored, with the prior LBs.  ``--cover-rows off`` (re-plan: the
    list pricing lanes M1 / M3 / M5) builds the master without cover rows, hence without the 12
    all-candidates templates at start-up (valid, weaker master bound)."""
    kw = {} if getattr(run.args, "cover_rows", "on") != "off" else {"use_cover": False}
    cert = ctx.certifier("relaxed", wall_h=wall_h(run.args, st), label=stage_tag(st), pricing_only=pricing_only, **kw)
    R.restore_prior_lb(cert, run.load())
    return cert


def price(run: R.Run, cert: BD.SitingCertifier, lay: BL.Layout, tag: str, full: bool, tier: Optional[str] = None,
          time_limit: Optional[float] = None, **kw: Any) -> Dict[str, Any]:
    """Price ``lay`` unless the records already hold a final result (resume); the per-layout LPs
    are not built (``lp=False``: the pool's envelope, incl. the subset cuts, is the prior).

    R7 re-plan (changes 2 / 7): ``tier='open_sites'`` prices on the open-sites library, always in
    full (K2.7: a bound-stopped open-sites pricing proves nothing about the all-candidates value);
    the result is an upper bound only (``price_open`` record, no cut).  Resume: a layout with a
    final open-sites pricing (PRICED / INFEASIBLE, every row solved with at least the limit
    asked) is not priced again.  The returned ``lower`` is then the all-candidates lower bound
    (:func:`R.all_candidates_lower`: envelope / LP / all-candidates pricing), ``lower_open`` the
    open-sites ILP bound (open-sites follower only).  ``time_limit`` and ``kw`` (``scenarios``,
    ``strict_scenarios``, ``warm_tier``, ``ilp_params``, change 5) go to ``cert.price``; without
    them the call is the old one."""
    key = lay.key()
    if tier == "open_sites":
        prev = cert.priced_open.get(key)
        out: Dict[str, Any] = {"layout_key": key, "tier": "open_sites"}
        if prev is not None and prev.status in ("PRICED", "INFEASIBLE") and R._limits_ok(prev.rows, time_limit):
            res, out["resumed"] = prev, True
        elif cert.wall_out():
            return dict(out, status="SKIPPED_WALL", V=None)
        else:
            res = cert.price(lay, full=True, tag=tag, tier="open_sites",
                             **({"time_limit": time_limit} if time_limit is not None else {}), **kw)
            out["resumed"] = False
            out["n_solves"] = res.n_solves
        out.update(status=res.status, V=res.V, lower=_f(R.all_candidates_lower(cert, lay)),
                   lower_open=res.setup + sum(p * x for p, x in zip(cert.p, res.lb)))
        return out
    prev = cert.priced.get(key)
    if prev is not None and prev.status in ("PRICED", "INFEASIBLE") or (prev is not None and not full and prev.status == "PRUNED_BY_BOUND"):
        return {"layout_key": key, "status": prev.status, "V": prev.V, "lower": prev.setup + sum(
            p * x for p, x in zip(cert.p, prev.lb)), "resumed": True}
    if cert.wall_out():
        return {"layout_key": key, "status": "SKIPPED_WALL", "V": None}
    if time_limit is not None:
        kw["time_limit"] = time_limit
    res = cert.price(lay, full=full, tag=tag, lp=False, **kw)
    out = {"layout_key": key, "status": res.status, "V": res.V, "lower": res.setup + sum(p * x for p, x in zip(cert.p, res.lb)),
           "resumed": False}
    if kw:                                      # re-plan change 5 (absent: the old return value)
        out.update(n_solves=res.n_solves, skipped_scenarios=list(getattr(res, "skipped", []) or []))
    return out


def tier_kw(run: R.Run, lay: Optional[BL.Layout] = None) -> Dict[str, Any]:
    """Keyword arguments of :func:`price` for the stage's ``--price-tier`` (re-plan change 7):
    ``{}`` for the old all-candidates pricing (the call is then unchanged), else the open-sites
    tier and the ``--time-limit-many-sites`` limit of ``lay``."""
    a = run.args
    if getattr(a, "price_tier", "all_candidates") != "open_sites":
        return {}
    out: Dict[str, Any] = {"tier": "open_sites"}
    tl = R.many_sites_limit(a, lay)
    if tl is not None:
        out["time_limit"] = tl
    return out


def finish(run: R.Run, ctx: R.Ctx, cert: BD.SitingCertifier, st: str) -> Dict[str, Any]:
    R.restore_prior_lb(cert, run.load())
    res = cert.finish(final_master_s=run.args.final_master_s)
    cert.close()
    run.emit({"kind": "stage_done", "stage": stage_tag(st), "config_md5": ctx.config_md5()})
    return {str(b): {k: r.get(k) for k in ("best_layout", "UB", "LB", "gap", "certified")} for b, r in res.items()}


def price_cells(run: R.Run, ev: BL.LowerLevelEvaluator, lays: Sequence[BL.Layout], scenarios: Sequence[int], *,
                workers: int, group: int, evict: bool, warm_from: Optional[BL.LowerLevelEvaluator] = None,
                label: str = "", match_limits: bool = False, tl_of=None) -> Dict[str, int]:
    """Scenario-major pricing of the cells ``(layout, s)`` with ``ev.evaluate_scenario`` (full
    solve, cached): scenarios in groups of ``group``, ``workers`` cells at once; with ``evict`` the
    group's templates are evicted after the group (memory of the no-radius / held-out templates,
    plan 2.2 batch 6).  ``warm_from``: an evaluator whose cached schedule of the same cell is the
    MIP start (a radius schedule is feasible without the radius: the radius only removes arcs);
    ``match_limits`` (fixer pass, stage R): each cell is solved at the time limit of the
    ``warm_from`` row of the same cell (at least the base limit), so that the two values of a cell
    come from solves of equal length.  ``tl_of(layout)`` (re-plan section 3, ``--time-limit-many-sites``):
    a per-layout limit (``None`` = the evaluator's), at least the matched one."""
    order = [int(s) for s in scenarios]
    n = {"cells": 0, "solved": 0, "cache_hits": 0, "errors": 0, "skipped": 0}
    for g in range(0, len(order), max(1, int(group))):
        grp = order[g:g + max(1, int(group))]
        cells = [(lay, s) for s in grp for lay in lays]

        def one(cell):
            lay, s = cell
            warm, tl = None, None
            if warm_from is not None:
                row = warm_from.cache.get(warm_from.cache_key(lay, s, "ilp"))
                warm = warm_from.load_portable(row) if row else None
                if match_limits and row and row.get("time_limit") is not None:
                    tl = max(float(row["time_limit"]), float(ev._time_limit_for(lay)))
            if tl_of is not None:
                t2 = tl_of(lay)
                if t2 is not None:
                    tl = t2 if tl is None else max(tl, float(t2))
            return ev.evaluate_scenario(lay, s, "ilp", warm=warm, time_limit=tl)
        t0 = time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
            rows = list(pool.map(one, cells))
        for r in rows:
            n["cells"] += 1
            st = r.get("status")
            n["cache_hits"] += int(bool(r.get("cache_hit")))
            n["solved"] += int(not r.get("cache_hit") and st not in ("SKIPPED_BUDGET", "ERROR"))
            n["errors"] += int(st == "ERROR")
            n["skipped"] += int(st == "SKIPPED_BUDGET")
        say(run, {"kind": "cell_group", "label": label, "scenarios": grp, "n_cells": len(cells), "wall_s": time.perf_counter() - t0,
                  "statuses": sorted({str(r.get('status')) for r in rows}), "rss_gb": R.rss_gb(),
                  "templates_resident": ev.resident_templates()})
        if evict:
            for s in grp:
                ev.evict_template(s)
    return n


def assemble(ev: BL.LowerLevelEvaluator, lay: BL.Layout) -> BD.PriceResult:
    """Full price of ``lay`` from the cached cells (re-solves only cells that are missing)."""
    return BD.price_layout(ev, lay, [0.0] * ev.n_scenarios, INF, 0.0, full=True, workers=1)


def noradius_evaluator(run: R.Run, ctx: R.Ctx) -> BL.LowerLevelEvaluator:
    """The in-sample evaluator with the approach radius UNSET (stage R): same scenarios, spec,
    probabilities, protocol and cache directory; the pruning signature (hence every cache key)
    differs by the radius only."""
    kw = dict(ctx.ev_kw)
    ev = BL.LowerLevelEvaluator(ctx.scen, ctx.spec, probabilities=ctx.p, cache_dir=run.cache, relaxed_targets=True,
                                verbose=not ctx.smoke, reposition="all_candidates", pruning={}, **kw)
    # --verify-start (K3.6 / change 6): not in the cache key, so resume is unaffected
    ev.verify_checked_starts = ctx.ev.verify_checked_starts
    return ev


# ---------------------------------------------------------------------------
# stage P: calibration
# ---------------------------------------------------------------------------
def calib_candidates(ctx: R.Ctx, args: argparse.Namespace) -> List[BL.Layout]:
    """Calibration layouts in preference order: ``--calib-layout``; else the transplanted one-site
    optimum (M09), then the SC screen option at the candidates by restaurants (proven
    terminal-infeasible locations skipped)."""
    if args.calib_layout:
        return [BL.Layout.from_key(args.calib_layout)]
    out: List[BL.Layout] = []
    for _k, lay in R.transplanted(ctx):
        if lay.n_open == 1 and ctx.enc.contains(lay):
            out.append(lay)
    opt = R.sc_screen_option(ctx)
    infeas = infeasible_locations(ctx)
    by_rest = sorted(ctx.candidates, key=lambda c: (-int(getattr(c, "n_restaurants", 0) or 0), ctx.ids.index(c.id)))
    for c in by_rest:
        if "SC" in ctx.ev.roles_of.get(c.id, ()) and c.id not in infeas:
            lay = BL.Layout.of([(c.id,) + tuple(opt)])
            if lay.key() not in {x.key() for x in out}:
                out.append(lay)
    return out


def calib_layout(ctx: R.Ctx, args: argparse.Namespace, verify: bool = True) -> Tuple[Optional[BL.Layout], List[Dict[str, Any]]]:
    """The first calibration layout that is terminal-feasible in EVERY in-sample scenario (library
    builds; a pricing of an infeasible layout returns INFEASIBLE_TERMINAL rows at once and measures
    nothing -- the transplanted M09 = D38 is infeasible alone in one N = 59 scenario), at most 8
    tries; without ``verify`` (dry run) the first candidate."""
    tried: List[Dict[str, Any]] = []
    for lay in calib_candidates(ctx, args)[:8]:
        if not verify:
            return lay, tried
        bad = None
        for s in range(ctx.ev.n_scenarios):
            inf = BD.verify_terminal_infeasible(ctx.ev, lay, s)
            if inf:
                bad = {"layout": lay.key(), "scenario": s, "infeasible_bikes": inf}
                break
        if bad is None:
            return lay, tried
        tried.append(bad)
    return None, tried


def stage_calib(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    a = run.args
    lay, tried = calib_layout(ctx, a, verify=not a.dry_run)
    if not a.dry_run:
        # fixer pass: the verification built (and kept) the templates and layout libraries; evict
        # them, so that part (a) times the template builds and every cell builds its library
        ctx.ev.evict_template(None)
    order = R.root_order(ctx.design)
    s0 = next((s for s in order if s in set(ctx.S_LP)), order[0])
    cells = list(ctx.levels[-2].items()) if len(ctx.levels) >= 2 else [("all", ctx.ids)]
    cell_name, cell = max(cells, key=lambda kv: (len(kv[1]), kv[0]))
    lp_scen = order[: min(8, len(order))]
    plan = {"kind": "calib_plan", "layout": None if lay is None else lay.key(), "pricing_workers": a.price_workers,
            "threads": a.threads, "time_limit": a.time_limit, "lp_scenario": s0, "cell": cell_name, "cell_locations": cell,
            "lp_threads": a.lp_threads, "one_site_lp_scenarios": lp_scen, "configs": [[3, 3], [4, 2]],
            "skipped_infeasible": tried, "verified": not a.dry_run}
    say(run, plan)
    if a.dry_run or lay is None:
        return plan
    recs = run.load()
    done = {r.get("part") for r in recs if r.get("kind") == "calib" and r.get("layout") == lay.key()}
    out: Dict[str, Any] = {}
    # (a) one 12-cell pricing: templates timed first, then the parallel pricing
    if "pricing" not in done and run.rss_guard("calib pricing"):
        tpl = []
        for s in range(ctx.ev.n_scenarios):
            t0 = time.perf_counter()
            ctx.ev.template(s)
            tpl.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        res = BD.price_layout(ctx.ev, lay, [0.0] * ctx.ev.n_scenarios, INF, 0.0, full=True, workers=a.price_workers)
        wall = time.perf_counter() - t0
        solved = [r for r in res.rows if not r.get("cache_hit")]
        rt = sum(float(r.get("runtime_s") or 0.0) for r in solved)
        rec = {"kind": "calib", "part": "pricing", "layout": lay.key(), "status": res.status, "V": res.V,
               "template_s": tpl, "template_s_sum": sum(tpl), "wall_s": wall, "n_cells": len(res.rows),
               "n_solved": len(solved), "n_cache_hits": len(res.rows) - len(solved), "solver_s_sum": rt,
               "workers": a.price_workers, "threads": a.threads,
               "utilisation": rt / (wall * a.price_workers) if wall > 0 and solved else None,
               "overhead_per_cell_s": (wall * a.price_workers - rt) / len(solved) if solved else None,
               "note": None if solved else "every cell was a cache hit: not a measurement"}
        say(run, rec)
        out["pricing"] = rec
        ctx.ev.evict_template(None)
    # (b) one-cell free-size LP with and without crossover (crossover 0 is valid through cut_from_pi)
    if "crossover" not in done and run.rss_guard("calib crossover"):
        lp = BD.ScenarioLP(ctx.ev, s0, threads=a.lp_threads, method="barrier", relaxed=True)
        lp.release_library()
        ctx.ev.evict_template(s0)
        rows = []
        try:
            for name, xo in (("crossover", -1), ("no_crossover", 0)):
                lp.model.reset()
                lp.model.Params.Crossover = xo
                r = lp.solve_subset(cell)
                rows.append({"variant": name, "status": r.status, "Qs": r.Qs, "Qt": r.Qt, "runtime_s": r.runtime_s,
                             "iterations": r.iterations})
            lp.model.Params.Crossover = -1
        finally:
            lp.dispose()
        sav = None
        if rows[0]["runtime_s"] and rows[1]["runtime_s"] is not None:
            sav = 1.0 - rows[1]["runtime_s"] / rows[0]["runtime_s"]
        rec = {"kind": "calib", "part": "crossover", "layout": lay.key(), "scenario": s0, "cell": cell_name,
               "n_locations": len(cell), "rows": rows, "saving": sav, "keep_nox": bool(sav is not None and sav >= 0.15)}
        say(run, rec)
        out["crossover"] = rec
    # (c) 8 one-site LPs as 3 workers x 3 threads against 4 x 2
    if "lp_workers" not in done and run.rss_guard("calib lp workers"):
        lps = []
        x = ctx.enc.x_of_layout(lay)
        try:
            for s in lp_scen:
                lp = BD.ScenarioLP(ctx.ev, s, threads=3, method="barrier", relaxed=True)
                lp.release_library()
                ctx.ev.evict_template(s)
                lps.append(lp)
            cfg_rows = []
            for workers, thr in ((3, 3), (4, 2)):
                for lp in lps:
                    lp.model.reset()
                    lp.model.Params.Threads = thr
                t0 = time.perf_counter()
                with cf.ThreadPoolExecutor(max_workers=workers) as pool:
                    rs = list(pool.map(lambda lp: lp.solve(x), lps))
                cfg_rows.append({"workers": workers, "threads": thr, "wall_s": time.perf_counter() - t0,
                                 "runtime_s": [r.runtime_s for r in rs], "Qs": [r.Qs for r in rs]})
        finally:
            for lp in lps:
                lp.dispose()
        rec = {"kind": "calib", "part": "lp_workers", "layout": lay.key(), "scenarios": lp_scen, "configs": cfg_rows,
               "faster": None if len(cfg_rows) < 2 else ("3x3" if cfg_rows[0]["wall_s"] <= cfg_rows[1]["wall_s"] else "4x2")}
        say(run, rec)
        out["lp_workers"] = rec
    run.emit({"kind": "stage_done", "stage": stage_tag("calib"), "config_md5": ctx.config_md5()})
    return out


# ---------------------------------------------------------------------------
# stage E: m = 2 seeds and pair screens
# ---------------------------------------------------------------------------
def pair_seeds(run: R.Run, ctx: R.Ctx, cert: Optional[BD.SitingCertifier], b: float,
               recs: Sequence[Dict[str, Any]]) -> Tuple[List[Tuple[frozenset, str]], List[Dict[str, Any]]]:
    """Seed pairs in priority order: ``--pair-seeds``, the transplanted pairs, the two best m = 1
    locations, coverage complements (a location infeasible alone + the best m = 1 location whose
    infeasible bikes are disjoint from its own in every scenario), relax-and-round of the master
    LP point at budget m = 2 (``--rr-seeds``; the all-open root LP stores no usage, so the
    rounding uses the master point and its cut envelope only)."""
    a = run.args
    out: List[Tuple[frozenset, str]] = []
    seen = set()
    notes: List[Dict[str, Any]] = []

    def add(A: frozenset, src: str) -> None:
        if len(A) == 2 and A not in seen and all(any(r in ("S", "SC") for r in ctx.ev.roles_of.get(l, ())) or
                                                  "C" in ctx.ev.roles_of.get(l, ()) for l in A):
            seen.add(A)
            out.append((A, src))
    given, bad = parse_locsets(ctx, a.pair_seeds)
    notes += bad
    for A in given:
        add(A, "given")
    for key, lay in R.transplanted(ctx):
        if lay.n_open == 2:
            add(frozenset(lay.locations()), f"transplant:{key}")
    rank = m1_rank(ctx, recs)
    if len(rank) >= 2:
        add(frozenset(rank[:2]), "m1_top2")
    fb = feas_bikes(run)
    if fb and a.complement_seeds > 0:
        w = demand_weights(ctx)
        rank_all = m1_rank(ctx, recs, feasible_only=False)
        n = 0
        for loc in sorted(fb, key=lambda l: (-w.get(l, 0.0), l)):
            if n >= a.complement_seeds:
                break
            if loc not in set(ctx.ids):
                continue
            for other in rank_all:
                if other == loc:
                    continue
                ob = fb.get(other, {})
                if all(not (fb[loc].get(s, set()) & ob.get(s, set())) for s in set(fb[loc]) | set(ob)):
                    before = len(out)
                    add(frozenset((loc, other)), "coverage_complement")
                    n += int(len(out) > before)
                    break
    if cert is not None and a.rr_seeds > 0:
        try:
            ms = cert.master.solve(b, relax=True)
            if ms.get("w") is not None:
                lays = BD.relax_and_round(cert.enc, ms["w"], {}, b, admissible=cert.in_master, max_layouts=60)
                k = 0
                for lay in lays:
                    if lay.n_open == 2 and k < a.rr_seeds:
                        before = len(out)
                        add(frozenset(lay.locations()), "relax_and_round_master")
                        k += int(len(out) > before)
            else:
                notes.append({"seed": "relax_and_round", "reason": f"master LP {ms.get('status')}"})
        except Exception as exc:  # noqa: BLE001 -- a seed source, never a bound
            notes.append({"seed": "relax_and_round", "reason": f"{type(exc).__name__}: {exc}"})
    return out, notes


def stage_pairs(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    a = run.args
    b = budget_of(ctx, 2)
    if b is None:
        say(run, {"kind": "stage_skipped", "stage": stage_tag("pairs"), "reason": "budget m = 2 not in --budgets"})
        return {}
    recs = run.load()
    if a.dry_run:
        seeds, notes = pair_seeds(run, ctx, None, b, recs)
        plan = {"kind": "pairs_plan", "budget": b, "S_LP": ctx.S_LP, "seeds": [[sorted(A), src] for A, src in seeds],
                "dropped": notes, "n_screens": a.pair_screens, "n_price": a.pair_price, "swap_pool": a.pair_swap_pool,
                "lp_solves_max": a.pair_screens * len(ctx.S_LP), "note": "relax-and-round seeds need the master (not in --dry-run)"}
        say(run, plan)
        return plan
    if not run.rss_guard("pairs"):
        return {}
    cert = certifier(run, ctx, "pairs")
    seeds, notes = pair_seeds(run, ctx, cert, b, recs)
    say(run, {"kind": "pairs_plan", "budget": b, "S_LP": ctx.S_LP, "seeds": [[sorted(A), src] for A, src in seeds],
              "dropped": notes, "n_screens": a.pair_screens, "n_price": a.pair_price, "swap_pool": a.pair_swap_pool})
    screened: Dict[frozenset, Dict[str, Any]] = {}

    def screen(A: frozenset, src: str) -> None:
        if A in screened or len(screened) >= a.pair_screens or cert.wall_out() or not run.rss_guard("pair screen"):
            return
        rec = set_bound(ctx, cert, A, b, ctx.S_LP, tag="pair2")
        rec.update(kind="pair_screen", source=src, UB=_f(cert.UB[b]), excluded=excluded(cert, b, rec["bound_exact"]))
        screened[A] = rec
        say(run, rec)
    for A, src in seeds:
        screen(A, src)
    ranked = sorted((r for r in screened.values() if r["bound_exact"] is not None), key=lambda r: (r["bound_exact"], r["atoms"]))
    if ranked and len(screened) < a.pair_screens:
        best = frozenset(ranked[0]["atoms"])
        pool = m1_rank(ctx, recs, exclude=best)[: max(0, a.pair_swap_pool)]
        neigh = []
        for i, c in enumerate(pool):
            for x in sorted(best):
                neigh.append((i, x, frozenset((best - {x}) | {c})))
        for _i, x, A in sorted(neigh, key=lambda t: (t[0], t[1])):
            screen(A, f"swap:{x}->{sorted(A - (best - {x}))[0]}")
    # price the best pairs (bound order; a pair proven >= UB_2 - tol is not priced): first the
    # sizes nearest each location's one-site best (pick_layout), SC + SC first; when that try
    # comes back PRUNED_BY_BOUND / INFEASIBLE, the next layout of the SAME pair by envelope (SC + S,
    # smaller sizes; pair_next_layout), at most --pair-tries per pair, until one is PRICED or the
    # pair is resolved.  Only PRICED pairs count against --pair-price; at most --pair-price x
    # --pair-tries pricing calls in all (fixer pass: the toy lost its m = 2 optimum, an SC + S
    # layout of a screened pair, because only the SC + SC try was made)
    targets = size_targets(ctx, recs)
    ranked = sorted((r for r in screened.values() if r["bound_exact"] is not None), key=lambda r: (r["bound_exact"], r["atoms"]))
    n_priced = n_calls = 0
    max_calls = max(1, a.pair_price) * max(1, a.pair_tries)
    for r in ranked:
        if n_priced >= a.pair_price or n_calls >= max_calls or cert.wall_out():
            break
        if excluded(cert, b, r["bound_exact"]):
            continue
        lays = layouts_at(ctx, cert, r["atoms"], b, k=[2])
        sc_sc = [l for l in lays if l.n_role("SC") == 2]
        be = pick_layout(ctx, cert, sc_sc or lays, targets)
        if be is None:
            say(run, {"kind": "pair_price", "atoms": r["atoms"], "status": "NO_ADMISSIBLE_LAYOUT"})
            continue
        tried: List[str] = []
        for t in range(max(1, a.pair_tries)):
            pr = price(run, cert, be[1], "pair", full=False, **tier_kw(run, be[1]))
            tried.append(be[1].key())
            n_calls += int(not pr.get("resumed"))
            say(run, {"kind": "pair_price", "atoms": r["atoms"], "envelope": be[0], "n_layouts": len(lays), "try": t + 1, **pr})
            if pr["status"] == "PRICED":
                n_priced += 1
                break
            if pr["status"] == "SKIPPED_WALL" or cert.wall_out() or n_calls >= max_calls:
                break
            nxt, why = pair_next_layout(cert, lays, tried, b)
            if nxt is None:
                say(run, {"kind": "pair_done", "atoms": r["atoms"], "tried": tried, "reason": why})
                break
            be = nxt
    ub = cert.UB[b]
    summ = [{"atoms": r["atoms"], "source": r["source"], "bound_exact": r["bound_exact"], "bound_window": r["bound_window"],
             "excluded": excluded(cert, b, r["bound_exact"])} for r in sorted(screened.values(), key=lambda r: (r["bound_exact"] or INF))]
    say(run, {"kind": "pair_summary", "budget": b, "UB": _f(ub), "best_layout": None if cert.best[b] is None else cert.best[b].key(),
              "n_screened": len(screened), "n_excluded": sum(1 for x in summ if x["excluded"]), "pairs": summ,
              "claim": "a pair marked excluded has no layout (any sizes) with V < UB_2 - tol",
              **({"UB_tier": cert.best_price[b].tier if cert.best_price[b] is not None else None, "price_tier": "open_sites"}
                 if tier_kw(run) else {})})
    return finish(run, ctx, cert, "pairs")


# ---------------------------------------------------------------------------
# stage F: m = 3 additions
# ---------------------------------------------------------------------------
def nearest_option(ctx: R.Ctx, loc: str, role: str, target: Tuple[int, int]) -> Optional[Tuple[str, int, int]]:
    opts = [o for o in options_at(ctx, loc) if o[0] == role]
    if not opts:
        return None
    return min(opts, key=lambda o: (abs(o[1] - target[0]) + abs(o[2] - target[1]), -o[1], -o[2]))


def fit_third(ctx: R.Ctx, cert: BD.SitingCertifier, base: BL.Layout, c: str, b: float) -> Optional[BL.Layout]:
    """``base`` + an SC object at ``c``: the representative size, else the cheapest SC option that
    keeps the layout within ``b`` and in the master."""
    rep = cert.rep_option() or R.sc_screen_option(ctx)
    opts = [o for o in options_at(ctx, c) if o[0] == "SC"]
    order = ([rep] if rep in opts else []) + sorted(opts, key=lambda o: (ctx.spec.Fhat + ctx.spec.bhat * o[1] + ctx.spec.chat * o[2], o))
    for o in order:
        lay = base.add((c,) + tuple(o))
        if lay.investment(ctx.spec) <= b + 1e-6 and cert.in_master(lay):
            return lay
    return None


def stage_m3(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    a = run.args
    b = budget_of(ctx, 3)
    if b is None:
        say(run, {"kind": "stage_skipped", "stage": stage_tag("m3"), "reason": "budget m = 3 not in --budgets"})
        return {}
    recs = run.load()
    pkey = best_known(ctx, recs, 2)
    plan = {"kind": "m3_plan", "budget": b, "best_pair": pkey, "n_thirds": a.m3_thirds, "screen": a.m3_screen}
    if pkey is None or BL.Layout.from_key(pkey).n_open != 2:
        b2 = budget_of(ctx, 2)
        alt = None if b2 is None else best_with_sites(ctx, recs, b2, 2)
        plan["incumbent_m2"] = pkey
        pkey = None if alt is None else alt[0]
        plan["best_pair"] = pkey
        plan["note"] = ("the m = 2 incumbent has one site: the best two-site layout with a value is used" if pkey
                        else "no two-site layout with a value (stage pairs first)")
    if pkey is None:
        say(run, plan)
        return plan
    P = BL.Layout.from_key(pkey)
    thirds = m1_rank(ctx, recs, exclude=P.locations())
    plan["third_candidates"] = thirds[: max(a.m3_thirds, a.m3_screen)]
    say(run, plan)
    if a.dry_run or not run.rss_guard("m3"):
        return plan
    cert = certifier(run, ctx, "m3")
    variants: List[Tuple[str, BL.Layout]] = []
    big = [(l, r) + (nearest_option(ctx, l, r, (4, 2)) or (r, B, Cc))[1:] for l, r, B, Cc in P.open]
    up = BL.Layout.of(big)
    if up.key() != P.key() and up.investment(ctx.spec) <= b + 1e-6 and cert.in_master(up):
        variants.append(("pair_max_sizes", up))
    cands = thirds[: max(a.m3_thirds, a.m3_screen)]
    if a.m3_screen > 0:
        rows = []
        for c in cands[: a.m3_screen]:
            if cert.wall_out():
                break
            rec = set_bound(ctx, cert, set(P.locations()) | {c}, b, ctx.S_LP, tag="triple3")
            rec.update(kind="triple_screen", third=c, excluded=excluded(cert, b, rec["bound_exact"]))
            say(run, rec)
            rows.append(rec)
        cands = [r["third"] for r in sorted(rows, key=lambda r: (r["bound_exact"] if r["bound_exact"] is not None else INF, r["third"]))
                 if not r["excluded"]] + [c for c in cands if c not in {r["third"] for r in rows}]
    k = 0
    for c in cands:
        if k >= a.m3_thirds:
            break
        lay = fit_third(ctx, cert, P, c, b)
        if lay is not None:
            variants.append((f"pair_plus_{c}", lay))
            k += 1
    for name, lay in variants:
        pr = price(run, cert, lay, "m3", full=False, **tier_kw(run, lay))
        say(run, {"kind": "m3_price", "name": name, "budget": b, **pr})
    say(run, {"kind": "m3_summary", "budget": b, "UB_3": _f(cert.UB[b]), "UB_2": _f(cert.UB[budget_of(ctx, 2)]),
              "best_layout": None if cert.best[b] is None else cert.best[b].key(),
              "third_site_pays": bool(cert.best[b] is not None and cert.best[b].n_open >= 3),
              "claim": "no layout found (not proved) when third_site_pays is false"})
    return finish(run, ctx, cert, "m3")


# ---------------------------------------------------------------------------
# stage H: role table (best / best S-containing / best hub-containing)
# ---------------------------------------------------------------------------
def stage_roles(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    a = run.args
    recs = run.load()
    budgets = [(m, budget_of(ctx, m)) for m in a.role_budgets]
    budgets = [(m, b) for m, b in budgets if b is not None]
    hubs = [l for l in ctx.ids if "C" in ctx.ev.roles_of.get(l, ())]
    order = R.root_order(ctx.design)
    hub_scen = [s for s in order if s in set(ctx.S_LP)][: max(1, a.hub_scenarios)]
    plan = {"kind": "roles_plan", "budgets": [b for _m, b in budgets], "hub_capable": hubs, "hub_scenarios": hub_scen,
            "n_hub_price": a.role_hub_price, "n_role_pairs": a.role_pairs,
            "best": {m: best_known(ctx, recs, m) for m, _b in budgets}}
    say(run, plan)
    if a.dry_run or not budgets or not run.rss_guard("roles"):
        return plan
    cert = certifier(run, ctx, "roles")
    targets = size_targets(ctx, recs)
    for m, b in budgets:
        best = cert.best[b]
        if best is None:
            say(run, {"kind": "role_row", "m": m, "budget": b, "note": "no incumbent at this budget"})
            continue
        # S-containing: the best screened pairs (pair_screen records), else the incumbent's locations
        pairs = [r for r in recs if r.get("kind") == "pair_screen" and r.get("bound_exact") is not None
                 and abs(float(r.get("budget") or -1) - b) < 1e-6]
        locsets = [tuple(r["atoms"]) for r in sorted(pairs, key=lambda r: (r["bound_exact"], r["atoms"]))]
        locsets = list(dict.fromkeys([tuple(sorted(best.locations()))] + locsets))[: max(1, a.role_pairs)]
        s_best = None
        for A in locsets:
            if cert.wall_out():
                break
            be = pick_layout(ctx, cert, layouts_at(ctx, cert, A, b, pred=lambda l: l.n_role("S") > 0 and l.n_role("C") == 0), targets)
            if be is not None and (s_best is None or be[0] < s_best[0]):
                s_best = be
        s_rec = None
        if s_best is not None:
            s_rec = price(run, cert, s_best[1], "role_S", full=True, **tier_kw(run, s_best[1]))
            say(run, {"kind": "role_price", "role": "S", "m": m, "envelope": s_best[0], **s_rec})
        # hub screen: subset LP of {h} + the incumbent's locations on the hub scenarios
        base = set(best.locations())
        screen = []
        for h in hubs:
            if h in base or cert.wall_out() or not run.rss_guard("hub screen"):
                continue
            rec = set_bound(ctx, cert, base | {h}, b, hub_scen, tag="hub_screen")
            rec.update(kind="hub_screen", hub=h, m=m)
            say(run, rec)
            screen.append(rec)
        screen.sort(key=lambda r: (r["opex_floor"], r["hub"]))
        hub_recs = []
        for rec in screen[: max(0, a.role_hub_price)]:
            if cert.wall_out():
                break
            be = pick_layout(ctx, cert, layouts_at(ctx, cert, rec["atoms"], b, pred=lambda l: l.n_role("C") > 0), targets)
            if be is None:
                say(run, {"kind": "role_price", "role": "C", "m": m, "hub": rec["hub"], "status": "NO_ADMISSIBLE_LAYOUT"})
                continue
            pr = price(run, cert, be[1], "role_hub", full=True, **tier_kw(run, be[1]))
            hub_recs.append(pr)
            say(run, {"kind": "role_price", "role": "C", "m": m, "hub": rec["hub"], "envelope": be[0], **pr})
        recs_now = run.load()
        row = {"kind": "role_row", "m": m, "budget": b, "UB": _f(cert.UB[b]), "LB": _f(cert.LB[b])}
        open_tier = bool(tier_kw(run))
        if open_tier:                            # re-plan change 7: one follower on every side of a difference
            row.update(follower="open_sites", note="V = open_sites value (UB of the all-candidates value); lower = "
                                                    "all-candidates lower bound (envelope / LP / subset); UB / LB = budget bounds")
        for name, pred in (("best", lambda l: True), ("best_S", lambda l: l.n_role("S") > 0),
                           ("best_hub", lambda l: l.n_role("C") > 0)):
            bk = R.best_layout_at(recs_now, b, ctx.spec, pred=pred, tiers=("open_sites",) if open_tier else ("all_candidates",))
            row[name], row[name + "_V"] = (None, None) if bk is None else bk
            if open_tier and bk is not None:
                row[name + "_lower"] = _f(R.all_candidates_lower(cert, BL.Layout.from_key(bk[0])))
        row["price_of_S"] = None if (row["best_S_V"] is None or row["best_V"] is None) else row["best_S_V"] - row["best_V"]
        row["price_of_hub"] = None if (row["best_hub_V"] is None or row["best_V"] is None) else row["best_hub_V"] - row["best_V"]
        say(run, row)
    return finish(run, ctx, cert, "roles")


# ---------------------------------------------------------------------------
# stage I: out-of-sample list with a held-out feasibility check
# ---------------------------------------------------------------------------
def oos_list(run: R.Run, ctx: R.Ctx) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]]]:
    recs = run.load()
    out, skipped = [], []
    seen = set()
    for name in run.args.oos_layouts or OOS_DEFAULT:
        key, src = resolve_layout(ctx, recs, name)
        if key is None:
            skipped.append({"name": name, "reason": src})
        elif key not in seen:
            seen.add(key)
            out.append((name, key))
    return out, skipped


def oos_feasibility(run: R.Run, ctx: R.Ctx, lays: Sequence[Tuple[str, str]]) -> Dict[str, Dict[int, List[str]]]:
    """``{layout_key: {s: infeasible bikes}}`` on the held-out scenarios (library builds; records
    ``oos_feas`` per cell, resumed from the records)."""
    ev = ctx.ev_out
    have: Dict[Tuple[str, int], List[str]] = {}
    for r in run.load():
        if r.get("kind") == "oos_feas" and r.get("demand_md5") == ev.demand_md5[int(r["scenario"])]:
            have[(r["layout_key"], int(r["scenario"]))] = list(r.get("infeasible_bikes") or [])
    out: Dict[str, Dict[int, List[str]]] = {k: {} for _n, k in lays}
    for s in range(ev.n_scenarios):
        todo = [(n, k) for n, k in lays if (k, s) not in have]
        for n, k in todo:
            inf = BD.verify_terminal_infeasible(ev, BL.Layout.from_key(k), s)
            have[(k, s)] = inf
            run.emit({"kind": "oos_feas", "name": n, "layout_key": k, "scenario": s, "seed": ev.seeds[s],
                      "demand_md5": ev.demand_md5[s], "infeasible_bikes": inf})
        for _n, k in lays:
            if have.get((k, s)):
                out[k][s] = have[(k, s)]
    return out


def stage_oos_feas(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    lays, skipped = oos_list(run, ctx)
    plan = {"kind": "oos_feas_plan", "layouts": lays, "skipped": skipped,
            "held_out_seeds": None if ctx.ev_out is None else ctx.ev_out.seeds}
    say(run, plan)
    if run.args.dry_run or ctx.ev_out is None or not lays:
        return plan
    if not run.rss_guard("oos-feas"):
        return plan
    inf = oos_feasibility(run, ctx, lays)
    res = {"kind": "oos_feas_result", "infeasible": {k: {str(s): b for s, b in v.items()} for k, v in inf.items() if v},
           "n_layouts": len(lays), "skipped": skipped}
    say(run, res)
    run.emit({"kind": "stage_done", "stage": stage_tag("oos-feas"), "config_md5": ctx.config_md5()})
    return res


def stage_oos(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    a = run.args
    lays, skipped = oos_list(run, ctx)
    plan = {"kind": "oos_plan", "layouts": lays, "skipped": skipped, "held_out_seeds": None if ctx.ev_out is None else ctx.ev_out.seeds}
    say(run, plan)
    if a.dry_run or ctx.ev_out is None or not lays:
        if ctx.ev_out is None:
            say(run, {"kind": "stage_skipped", "stage": stage_tag("oos"), "reason": "no held-out scenarios (--held-out)"})
        return plan
    if not run.rss_guard("oos"):
        return plan
    ev = ctx.ev_out
    ev.wall = C.WallBudget(wall_h(a, "oos") * 3600.0, margin_s=60.0, min_solve_s=30.0)
    inf = oos_feasibility(run, ctx, lays)
    ok = [BL.Layout.from_key(k) for _n, k in lays if not inf.get(k)]
    open_tier = bool(tier_kw(run))
    tl_of = (lambda l: R.many_sites_limit(a, l)) if open_tier else None
    ev_in = None
    if open_tier:
        # re-plan change 7: held-out AND in-sample values on the open-sites library (one follower on
        # both sides of V_out - V_in); the in-sample cells are mostly cache hits of the m = 1 pass
        ctx.ev.wall = ev.wall
        ev_in = BD._tier_evaluator(ctx.ev, "open_sites")
        price_cells(run, ev_in, ok, range(ctx.ev.n_scenarios), workers=a.price_workers, group=ctx.ev.n_scenarios,
                    evict=False, label="oos_in_open", tl_of=tl_of)
        ev = BD._tier_evaluator(ev, "open_sites")
    price_cells(run, ev, ok, range(ev.n_scenarios), workers=a.price_workers, group=ev.n_scenarios, evict=False, label="oos",
                **({"tl_of": tl_of} if tl_of is not None else {}))
    recs = run.load()
    pl = R.priced_layouts(recs)
    strata_in = [d["stratum"] for d in ctx.design]
    strata_out = [d["stratum"] for d in ctx.held]
    for name, key in lays:
        v_in = (pl.get(key) or {}).get("V")
        opex_in = (pl.get(key) or {}).get("ub")
        rec: Dict[str, Any] = {"kind": "oos_result", "name": name, "layout_key": key, "V_in": v_in, "source": "r7_search",
                               "ci_out": None, "ci_in": None, "diff": None}
        if ev_in is not None:
            rec["tier"] = "open_sites"
            if not inf.get(key):
                r_in = assemble(ev_in, BL.Layout.from_key(key))
                v_in, opex_in = r_in.V, r_in.ub
                rec.update(V_in=v_in, status_in=r_in.status)
        if inf.get(key):
            rec.update(status="INFEASIBLE_OUT_OF_SAMPLE", V_out=None, infeasible_scenarios={str(s): b for s, b in inf[key].items()})
        else:
            res = assemble(ev, BL.Layout.from_key(key))
            rec.update(status=res.status, V_out=res.V, opex_out=res.ub, served_out=res.served_share)
            if ev_in is not None:
                rec["n_optimal_out"] = sum(1 for x in res.rows if x.get("status") == "OPTIMAL")
            if res.V is not None and all(u is not None for u in res.ub):
                rec["ci_out"] = BL.stratified_ci(res.ub, strata_out, ev.p)
                rec["ci_out_plain"] = BL.paired_ci(res.ub, ev.p)
            if rec["V_out"] is not None and v_in is not None:
                rec["diff"] = rec["V_out"] - v_in
        if opex_in and all(u is not None for u in opex_in):
            rec["ci_in"] = BL.stratified_ci(opex_in, strata_in, ctx.p)
        say(run, rec)
    run.emit({"kind": "stage_done", "stage": stage_tag("oos"), "config_md5": ctx.config_md5()})
    return plan


# ---------------------------------------------------------------------------
# stage R: no-radius re-pricing of the near-tie set
# ---------------------------------------------------------------------------
def near_tie_set(ctx: R.Ctx, recs: Sequence[Dict[str, Any]], tie: float, open_tier: bool = False) -> Dict[str, Any]:
    """The m = 1 layouts within ``tie`` of UB_1.  ``open_tier`` (re-plan change 7): the open-sites
    values only, UB_1 = the best of them (one follower for the radius comparison); the layouts
    whose all-candidates lower bound is in the band but without an open-sites value are listed."""
    b1 = min(ctx.budgets)
    pl = R.priced_layouts(recs, tiers=("open_sites",) if open_tier else ("all_candidates",))
    one = {k: float(r["V"]) for k, r in pl.items() if BL.Layout.from_key(k).n_open == 1
           and BL.Layout.from_key(k).investment(ctx.spec) <= b1 + 1e-6}
    r1 = R.last_results(recs).get(b1) or {}
    if open_tier:
        ub1 = min(one.values()) if one else None
    else:
        ub1 = r1.get("UB") if r1.get("UB") is not None else (min(one.values()) if one else None)
    if ub1 is None:
        return {"UB_1": None, "layouts": [], "unpriced_in_band": []}
    lim = float(ub1) * (1.0 + float(tie))
    tied = sorted((v, k) for k, v in one.items() if v <= lim + 1e-9)
    band = set()
    if open_tier:
        for key, d in R.m1_lower_table(ctx, recs, b1).items():
            if d["lower"] is not None and d["lower"] <= lim and key not in one and not d["infeasible_open"]:
                band.add(key)
    for r in recs:                                  # one-site layouts whose lower bound is in the band but without V
        if r.get("kind") == "price" and r.get("target") == "relaxed" and r.get("layout_key") and r.get("V") is None \
                and r.get("status") in ("PRUNED_BY_BOUND", "UNRESOLVED") and r.get("lower") is not None \
                and float(r["lower"]) <= lim and r["layout_key"] not in one:
            try:
                if BL.Layout.from_key(r["layout_key"]).n_open == 1:
                    band.add(r["layout_key"])
            except ValueError:
                pass
    return {"UB_1": float(ub1), "limit": lim, "layouts": [k for _v, k in tied], "V": {k: v for v, k in tied},
            "unpriced_in_band": sorted(band)}


def stage_noradius(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    a = run.args
    recs = run.load()
    open_tier = bool(tier_kw(run))
    tie = near_tie_set(ctx, recs, a.near_tie, open_tier=open_tier)
    lst: List[Tuple[str, str]] = [("m1_tie", k) for k in tie["layouts"]]
    for m in (2, 3):
        k = best_known(ctx, recs, m)
        if k and k not in {x for _g, x in lst}:
            lst.append((f"best@m{m}", k))
    plan = {"kind": "noradius_plan", "radius": a.approach_radius, "near_tie": a.near_tie, "UB_1": tie["UB_1"],
            "layouts": lst, "unpriced_in_band": tie["unpriced_in_band"], "group": a.noradius_group,
            "workers": a.price_workers, "n_cells": len(lst) * ctx.ev.n_scenarios}
    if a.approach_radius is None:
        plan["note"] = "the run has no approach radius: the re-pricing equals the in-sample pricing (cache keys equal)"
    if open_tier:
        plan["tier"] = "open_sites"
    say(run, plan)
    if a.dry_run or not lst or not run.rss_guard("noradius"):
        return plan
    ev = noradius_evaluator(run, ctx)
    ev.wall = C.WallBudget(wall_h(a, "noradius") * 3600.0, margin_s=60.0, min_solve_s=30.0)
    lays = [BL.Layout.from_key(k) for _g, k in lst]
    match = a.noradius_time_limit == "match"
    ev_r = ctx.ev
    if open_tier:
        # re-plan change 7: open_sites with the radius against open_sites without it (one follower:
        # the radius effect is then exact where both sides are OPTIMAL); the open-sites libraries are
        # built per layout, so no template is resident and no eviction is needed
        ctx.ev.wall = ev.wall
        ev_r = BD._tier_evaluator(ctx.ev, "open_sites")
        ev = BD._tier_evaluator(ev, "open_sites")
        tl_of = lambda l: R.many_sites_limit(a, l)   # noqa: E731
        price_cells(run, ev_r, lays, range(ev.n_scenarios), workers=a.price_workers, group=ev.n_scenarios, evict=False,
                    label="noradius_radius_open", tl_of=tl_of)
        price_cells(run, ev, lays, range(ev.n_scenarios), workers=a.price_workers, group=ev.n_scenarios, evict=False,
                    warm_from=ev_r, label="noradius_open", match_limits=match, tl_of=tl_of)
    else:
        price_cells(run, ev, lays, range(ev.n_scenarios), workers=a.price_workers, group=a.noradius_group, evict=True,
                    warm_from=ctx.ev, label="noradius", match_limits=match)
    pl = R.priced_layouts(run.load())
    rows = []
    for grp, key in lst:
        lay = BL.Layout.from_key(key)
        res = assemble(ev, lay)
        v_r = (pl.get(key) or {}).get("V")
        res_r = None
        if open_tier:
            res_r = assemble(ev_r, lay)
            v_r = res_r.V
        tl_r = [(ev_r.cache.get(ev_r.cache_key(lay, s, "ilp")) or {}).get("time_limit") for s in range(ev.n_scenarios)]
        tl_n = [r.get("time_limit") for r in res.rows]
        rec = {"kind": "noradius_result", "group": grp, "layout_key": key, "status": res.status, "V_radius": v_r,
               "V_noradius": res.V, "diff": None if (res.V is None or v_r is None) else v_r - res.V,
               "rel": None if (res.V is None or v_r is None or not res.V) else (v_r - res.V) / abs(res.V),
               "opex_noradius": res.ub, "time_limits_radius": tl_r, "time_limits_noradius": tl_n,
               "limits_equal": all(x is not None and y is not None and float(y) >= float(x) - 1e-9
                                   for x, y in zip(tl_r, tl_n)),
               "note": None if match else "no-radius cells at the base limit: the effect is a lower bound "
                                          "(the radius values may come from longer, escalated solves)"}
        if res_r is not None:
            n_opt = [sum(1 for x in rr.rows if x.get("status") == "OPTIMAL") for rr in (res_r, res)]
            rec.update(tier="open_sites", n_optimal_radius=n_opt[0], n_optimal_noradius=n_opt[1],
                       exact=bool(n_opt[0] == ev.n_scenarios and n_opt[1] == ev.n_scenarios),
                       lb_open_noradius=res.lb)
        rows.append(rec)
        say(run, rec)
    m1 = [r for r in rows if r["group"] == "m1_tie" and r["V_noradius"] is not None and r["V_radius"] is not None]
    ord_r = [r["layout_key"] for r in sorted(m1, key=lambda r: (r["V_radius"], r["layout_key"]))]
    ord_n = [r["layout_key"] for r in sorted(m1, key=lambda r: (r["V_noradius"], r["layout_key"]))]
    rel1 = [r["rel"] for r in m1 if r["rel"] is not None]
    rel2 = [r["rel"] for r in rows if r["group"] != "m1_tie" and r["rel"] is not None]
    say(run, {"kind": "noradius_summary", "order_radius": ord_r, "order_noradius": ord_n, "order_changed": ord_r != ord_n,
              "m1_rel_effect": [min(rel1), max(rel1)] if rel1 else None, "m23_rel_effect": [min(rel2), max(rel2)] if rel2 else None,
              "bias_m1_minus_m23": (sum(rel1) / len(rel1) - sum(rel2) / len(rel2)) if (rel1 and rel2) else None,
              "consequence": "m = 1 ranking library-conditional" if ord_r != ord_n else "m = 1 order unchanged without the radius"})
    run.emit({"kind": "stage_done", "stage": stage_tag("noradius"), "config_md5": ctx.config_md5()})
    return {"n": len(rows)}


# ---------------------------------------------------------------------------
# list pricing
# ---------------------------------------------------------------------------
def m1_lp_order(ctx: R.Ctx, recs: Sequence[Dict[str, Any]]) -> List[Tuple[float, str]]:
    """The m = 1 list rule of the re-plan (section 2.1 M1 / M1-rest): every admissible m = 1
    layout with a finite all-candidates lower bound in the records (:func:`R.m1_lower_table`:
    LP, cut envelope, all-candidates pricing), lowest first.  In production the B3:C2 location
    LPs come first (the smaller sizes have LPs >= 1166.6 or envelopes >= 1176.0)."""
    tab = R.m1_lower_table(ctx, recs, min(ctx.budgets))
    return sorted((float(d["lower"]), k) for k, d in tab.items()
                  if d["lower"] is not None and math.isfinite(float(d["lower"])) and not d["infeasible"])


def price_list_names(run: R.Run, ctx: R.Ctx, recs: Sequence[Dict[str, Any]]) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]],
                                                                                   List[Tuple[float, str]]]:
    """``(list, skipped, lp-order rest)``: the ``--layouts`` / ``--layouts-file`` names resolved;
    the name ``m1-lp-order`` expands to the layouts of :func:`m1_lp_order` with a lower bound
    below ``--lp-order-below`` (or the first ``--lp-order-top``); the rest of that order is
    returned for ``--extend-below-ub``."""
    a = run.args
    keys = list(a.layouts or [])
    if a.layouts_file:
        with open(a.layouts_file, "r", encoding="utf-8") as fh:
            keys += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    lst: List[Tuple[str, str]] = []
    bad: List[Dict[str, Any]] = []
    rest: List[Tuple[float, str]] = []
    for k in keys:
        if k == M1_LP_ORDER:
            order = m1_lp_order(ctx, recs)
            if a.lp_order_below is not None:
                head = [(v, x) for v, x in order if v < float(a.lp_order_below)]
            else:
                head = order[: max(0, int(a.lp_order_top or 0))]
            seen = {x for _v, x in head}
            lst += [(f"{M1_LP_ORDER}:{v:.2f}", x) for v, x in head]
            rest = [(v, x) for v, x in order if x not in seen]
            if not order:
                bad.append({"name": k, "reason": "no m = 1 layout with an LP / envelope / pricing bound in the records"})
            continue
        key, src = resolve_layout(ctx, recs, k)
        (lst.append((k, key)) if key else bad.append({"name": k, "reason": src}))
    return lst, bad, rest


#: re-plan M5: Tier 2 is started only when the better M3 variant lifts the cell bounds by >= 1 %
#: on average over the cell LP at the probe limit (1,200 s)
PROBE_LIFT_PCT = 1.0
PROBE_TIME_LIMIT = 1200.0


def probe_summary(recs: Sequence[Dict[str, Any]], threshold_pct: float = PROBE_LIFT_PCT,
                  time_limit: float = PROBE_TIME_LIMIT) -> Optional[Dict[str, Any]]:
    """Re-plan M3 / review: the Tier 2 decision from the records (no solve).  Every all-candidates
    ``price`` record of a ``--cells`` run (``strict_scenarios``) is one probe variant, labelled by
    its ``ilp_params`` (``default`` when none); the last record per (layout, variant) counts.  Per
    cell: the LP value ``Qs`` (last ``lp_layout`` / ``lp_location`` record of the layout), the ILP
    OPEX bound (``bound - C_setup``, ``max`` with ``Qs`` as in the pricing), ``lift % = 100 (bound
    - Qs) / Qs``, the status, node count and runtime.  A cell without a usable ILP bound counts
    as lift 0 (its bound stays the LP value).  The verdict: Tier 2 when the better variant's mean
    lift is >= ``threshold_pct`` and every one of its cells ran with a limit of at least
    ``time_limit``.  Reporting only: nothing here enters a bound.  ``None`` without probe
    records."""
    qs: Dict[str, List[float]] = {}
    last: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in recs:
        k = r.get("kind")
        if k in ("lp_layout", "lp_location") and isinstance(r.get("Qs"), list) and r.get("target", "relaxed") == "relaxed":
            qs[str(r.get("layout_key"))] = [float(x) for x in r["Qs"]]
        elif (k == "price" and r.get("tier", "all_candidates") == "all_candidates" and r.get("strict_scenarios")
              and r.get("scenarios")):
            params = r.get("ilp_params") or {}
            var = ",".join(f"{a}={b}" for a, b in sorted(params.items())) or "default"
            last[(str(r.get("layout_key")), var)] = r
    if not last:
        return None
    rows: List[Dict[str, Any]] = []
    per_var: Dict[str, List[Dict[str, Any]]] = {}
    for (key, var), r in sorted(last.items()):
        q = qs.get(key)
        by_s = {int(x.get("scenario")): x for x in (r.get("rows") or []) if x.get("scenario") is not None}
        for s in r.get("scenarios") or []:
            s = int(s)
            row = by_s.get(s) or {}
            q_s = None if q is None or s >= len(q) else q[s]
            blb = BD._row_lb(row) if row else None
            b_s = None if blb is None else (blb if q_s is None else max(q_s, blb))
            lift = None
            if q_s is not None and q_s > 0:
                lift = 100.0 * ((q_s if b_s is None else b_s) - q_s) / q_s
            tl = row.get("time_limit")
            c = {"layout_key": key, "variant": var, "scenario": s, "Qs": q_s, "ilp_bound_opex": b_s, "lift_pct": lift,
                 "status": row.get("status"), "gurobi_status": row.get("gurobi_status"),
                 "node_count": row.get("node_count"), "runtime_s": row.get("runtime_s"), "time_limit": tl,
                 "cache_hit": row.get("cache_hit"), "warm_source": row.get("warm_source")}
            rows.append(c)
            per_var.setdefault(var, []).append(c)
    variants = []
    for var, cs in sorted(per_var.items()):
        lifts = [c["lift_pct"] for c in cs if c["lift_pct"] is not None]
        full_tl = all(c["time_limit"] is not None and float(c["time_limit"]) >= time_limit - 1e-6 for c in cs)
        variants.append({"variant": var, "n_cells": len(cs), "n_with_lift": len(lifts),
                         "mean_lift_pct": (sum(lifts) / len(lifts)) if lifts else None,
                         "n_optimal": sum(1 for c in cs if c["status"] == "OPTIMAL"), "limit_ok": full_tl})
    scored = [v for v in variants if v["mean_lift_pct"] is not None]
    best = max(scored, key=lambda v: (v["mean_lift_pct"], v["variant"] == "default")) if scored else None
    go = bool(best is not None and best["limit_ok"] and best["mean_lift_pct"] >= threshold_pct)
    if best is None:
        verdict = "no lift known (no LP value or ILP bound in the records): Tier 2 not decided"
    elif not best["limit_ok"]:
        verdict = (f"undecided: the better variant ({best['variant']}) has cells below the {time_limit:g} s probe limit")
    elif go:
        verdict = (f"start Tier 2 (lanes_r2_tier2.txt): variant {best['variant']} lifts the cell bounds by "
                   f"{best['mean_lift_pct']:.2f} % >= {threshold_pct:g} %"
                   + ("" if best["variant"] == "default" else
                      f"; regenerate with --write-lanes --lanes-plan r2 --ilp-params {best['variant'].replace(',', ' ')}"))
    else:
        verdict = (f"skip Tier 2: the better variant ({best['variant']}) lifts the cell bounds by "
                   f"{best['mean_lift_pct']:.2f} % < {threshold_pct:g} %")
    return {"kind": "probe_summary", "threshold_pct": threshold_pct, "time_limit": time_limit, "cells": rows,
            "variants": variants, "best_variant": None if best is None else best["variant"], "tier2": go,
            "verdict": verdict, "n_variants_seen": len(variants),
            "note": "reporting only; root LP time is not recorded by the solver wrapper (runtime_s is the whole solve)"}


def stage_price_list(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    """List pricing.  R7 re-plan:

    * change 2 -- ``--tier open_sites`` (evaluator ``in``) prices every listed layout in full on
      the open-sites library (``price_open`` records: upper bounds only, no cut); a layout with a
      final open-sites pricing is not priced again (resume: 0 solves);
    * the list rule ``--layouts m1-lp-order --lp-order-below V`` (M1) and ``--extend-below-ub on``
      (M1-rest): after the list, the next layouts in LP order are priced while their
      all-candidates lower bound is below the best open-sites value at m = 1 (tol 0, K2.2: the
      open-sites certificate of change 8 needs every such layout priced), at most
      ``--extend-max``, within the wall;
    * change 5 -- ``--cells LOC:s ...`` (strict: uncached cells outside the filter are not solved,
      K3.1), ``--warm-tier open_sites`` (change 4) and ``--ilp-params K=V`` (new cache rows) for
      the all-candidates tier: the M3 bound probe and Tier 2 (M5)."""
    a = run.args
    recs = run.load()
    lst, bad, rest = price_list_names(run, ctx, recs)
    tier = getattr(a, "tier", "all_candidates") or "all_candidates"
    plan = {"kind": "price_list_plan", "evaluator": a.evaluator, "layouts": lst, "skipped": bad}
    extra: Dict[str, Any] = {}
    if tier != "all_candidates":
        extra["tier"] = tier
    if a.cells:
        extra["cells"] = {k: sorted(v) for k, v in BD.parse_cells(a.cells).items()}
    if a.warm_tier:
        extra["warm_tier"] = a.warm_tier
    if a.ilp_params:
        extra["ilp_params"] = BD.parse_ilp_params(a.ilp_params)
    if a.extend_below_ub == "on":
        extra.update(extend_below_ub=True, extend_candidates=[[v, k] for v, k in rest[: max(0, int(a.extend_max))]])
    plan.update(extra)
    say(run, plan)
    if a.dry_run or not (lst or (a.extend_below_ub == "on" and rest)) or not run.rss_guard("price-list"):
        return plan
    lays = [BL.Layout.from_key(k) for _n, k in lst]
    if a.evaluator == "in":
        cert = certifier(run, ctx, "price-list")
        cells = BD.parse_cells(a.cells) if a.cells else None
        params = BD.parse_ilp_params(a.ilp_params) if a.ilp_params else None
        if tier == "open_sites" and (cells is not None or a.warm_tier or params):
            raise SystemExit("--cells / --warm-tier / --ilp-params are for --tier all_candidates (the bound probe)")

        def one(n: str, lay: BL.Layout) -> Dict[str, Any]:
            kw: Dict[str, Any] = {}
            if cells is not None:
                kw.update(scenarios=BD.cells_for_layout(cells, lay), strict_scenarios=True)
            if a.warm_tier:
                kw["warm_tier"] = a.warm_tier
            if params:
                kw["ilp_params"] = dict(params)
            tl = R.many_sites_limit(a, lay)
            if tl is not None:
                kw["time_limit"] = tl
            pr = price(run, cert, lay, "list", full=True, **({"tier": "open_sites"} if tier == "open_sites" else {}), **kw)
            say(run, {"kind": "list_price", "evaluator": "in", "name": n, **pr})
            return pr
        for (n, k), lay in zip(lst, lays):
            one(n, lay)
        if cells is not None:                   # review: the Tier 2 decision of the M3 probes, as a record
            ps = probe_summary(run.load())
            if ps is not None:
                say(run, ps)
        if a.extend_below_ub == "on":
            b1 = min(ctx.budgets)

            def ub_open() -> float:
                vals = [pr.V for pr in cert.priced_open.values() if pr.status == "PRICED" and pr.V is not None
                        and pr.layout.investment(ctx.spec) <= b1 + 1e-6]
                return min(vals) if vals else INF
            done = {k for _n, k in lst}
            n_ext, why = 0, "list exhausted"
            for v, k in rest:
                if k in done:
                    continue
                u = ub_open()
                if not v < u - 1e-9:
                    why = f"next lower bound {v:.2f} >= best open_sites value {u:.2f} (tol 0)"
                    break
                if n_ext >= int(a.extend_max):
                    why = f"--extend-max {a.extend_max} reached"
                    break
                if cert.wall_out():
                    why = "wall"
                    break
                one(f"extend:{v:.2f}", BL.Layout.from_key(k))
                n_ext += 1
            say(run, {"kind": "price_list_extension", "n_extended": n_ext, "stop": why, "UB_open": _f(ub_open()),
                      "rule": "price in LP order while the all-candidates lower bound < best open_sites value at m = 1"})
        return finish(run, ctx, cert, "price-list")
    if a.evaluator == "out":
        if ctx.ev_out is None:
            raise SystemExit("--evaluator out needs --held-out")
        ev, warm, evict = ctx.ev_out, None, False
    else:
        ev, warm, evict = noradius_evaluator(run, ctx), ctx.ev, True
    ev.wall = C.WallBudget(wall_h(a, "price-list") * 3600.0, margin_s=60.0, min_solve_s=30.0)
    if tier == "open_sites":                     # change 2 for the other evaluators: open-sites siblings
        ctx.ev.wall = ev.wall
        ev = BD._tier_evaluator(ev, "open_sites")
        warm = None if warm is None else BD._tier_evaluator(ctx.ev, "open_sites")
        evict = False
    price_cells(run, ev, lays, range(ev.n_scenarios), workers=a.price_workers,
                group=(a.noradius_group if evict else ev.n_scenarios), evict=evict, warm_from=warm, label=f"list_{a.evaluator}")
    for (n, k), lay in zip(lst, lays):
        res = assemble(ev, lay)
        rec = {"kind": "list_price", "evaluator": a.evaluator, "name": n, "layout_key": k, "status": res.status,
               "V": res.V, "opex": res.ub}
        if tier == "open_sites":                 # K2.7: open-sites bounds are labelled as such
            rec.update(tier="open_sites", lb_open=res.lb)
        else:
            rec["lb"] = res.lb
        say(run, rec)
    run.emit({"kind": "stage_done", "stage": stage_tag("price-list"), "config_md5": ctx.config_md5()})
    return plan


# ---------------------------------------------------------------------------
# change 3: import of price records and cache rows from another out-dir
# ---------------------------------------------------------------------------
IMPORT_KINDS = ("price_open", "price")


def _rec_id(r: Dict[str, Any]) -> str:
    return BL._md5({k: v for k, v in r.items() if k not in ("imported_from", "import_id")})


def stage_import_records(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    """R7 re-plan change 3 (``--stage import-records --from DIR``): merge the pricing results of
    another out-dir of the SAME instance into ``--out-dir``.

    * records: the ``price_open`` / ``price`` records stamped with this ``instance_md5`` are
      appended (``import_id`` = MD5 of the source record: a second import appends nothing);
      ``budget_result`` / ``final_bound`` / ``stage_done`` and every other kind are NOT imported
      (K3.4: the bound pair of another run would show as the latest result).  A ``price`` record
      is valid here because its bounds and incumbent belong to the same instance (its integer
      cuts are not copied: the restore takes its scenario bounds as they are);
    * cache: the ``cache/index.jsonl`` rows whose key is absent here are appended, with their
      schedule file copied into ``cache/schedules/`` and ``schedule_path`` rewritten.
    Valid because cache keys and ``instance_md5`` fix the instance, the library convention,
    the params and the layout; nothing is solved."""
    import shutil
    a = run.args
    src = os.path.abspath(a.import_from or "")
    if not a.import_from or not os.path.isdir(src):
        raise SystemExit("--stage import-records needs --from DIR (an out-dir of the same instance)")
    if os.path.abspath(src) == os.path.abspath(run.dir):
        raise SystemExit("--from is the --out-dir itself")
    md5 = ctx.instance_md5()
    have = {r.get("import_id") for r in R.load_jsonl_lenient(run.records) if r.get("import_id")}
    have_ids = have | {_rec_id(r) for r in run.load() if r.get("kind") in IMPORT_KINDS}
    n_rec = n_other_inst = n_dup = 0
    kinds: Dict[str, int] = {}
    to_add = []
    for r in R.load_jsonl_lenient(os.path.join(src, "records.jsonl")):
        if r.get("kind") not in IMPORT_KINDS:
            continue
        if r.get("instance_md5") != md5:
            n_other_inst += 1
            continue
        rid = r.get("import_id") or _rec_id(r)
        if rid in have_ids:
            n_dup += 1
            continue
        have_ids.add(rid)
        to_add.append(dict(r, import_id=rid, imported_from=src))
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        n_rec += 1
    # cache rows first (a restored price must find its rows), then the records
    dst_cache = run.cache
    os.makedirs(os.path.join(dst_cache, "schedules"), exist_ok=True)
    dst_index = os.path.join(dst_cache, "index.jsonl")
    keys_here = {r.get("key") for r in C.load_jsonl(dst_index)} if os.path.exists(dst_index) else set()
    n_rows = n_sched = 0
    src_index = os.path.join(src, "cache", "index.jsonl")
    rows = C.load_jsonl(src_index) if os.path.exists(src_index) else []
    for row in rows:
        k = row.get("key")
        if not k or k in keys_here:
            continue
        keys_here.add(k)
        row = dict(row)
        sp = row.get("schedule_path")
        cand = [sp] if sp else []
        cand.append(os.path.join(src, "cache", "schedules", f"{k}.json"))
        got = next((c for c in cand if c and os.path.exists(c)), None)
        if got is not None:
            dst = os.path.join(dst_cache, "schedules", f"{k}.json")
            if not os.path.exists(dst):
                shutil.copyfile(got, dst)
            row["schedule_path"] = dst
            n_sched += 1
        elif sp:
            row.pop("schedule_path", None)
        C.append_jsonl(dst_index, row)
        n_rows += 1
    for r in to_add:
        C.append_jsonl(run.records, C.jsonable(r))
    out = {"kind": "import_result", "from": src, "n_records": n_rec, "by_kind": kinds, "n_duplicates": n_dup,
           "n_other_instance": n_other_inst, "n_cache_rows": n_rows, "n_schedules": n_sched,
           "note": "price / price_open records and cache rows only; no budget_result, final_bound or stage_done (K3.4)"}
    say(run, out)
    return out


# ---------------------------------------------------------------------------
# M6: validity check of the open-sites UB on the all-candidates library
# ---------------------------------------------------------------------------
def stage_ub_check(run: R.Run, ctx: R.Ctx) -> Dict[str, Any]:
    """Re-plan M6 (K3.5, mandatory for the layout that sets UB_1): materialise the open-sites
    schedules of every scenario of ``--layouts`` (default ``best@m1``) on the ALL-CANDIDATES
    layout library, run ``check`` and ``cost`` (``benders.ub_check_all_candidates``) and record
    ``ub_check_all_candidates`` (``source = check``, ``V_checked`` against ``V_open``).  No
    certifier, no LP, no ILP: the all-candidates templates are built one scenario at a time
    (``--max-templates`` bounds the resident ones).  A layout already checked ok with the same
    V_open is skipped (resume)."""
    a = run.args
    recs = run.load()
    names = list(a.layouts or ["best@m1"])
    lst, bad = [], []
    for n in names:
        key, src = resolve_layout(ctx, recs, n)
        (lst.append((n, key)) if key else bad.append({"name": n, "reason": src}))
    plan = {"kind": "ub_check_plan", "layouts": lst, "skipped": bad}
    say(run, plan)
    if a.dry_run or not lst or not run.rss_guard("ub-check"):
        return plan
    op = R.open_priced(recs)
    out = []
    for n, key in lst:
        v_open = (op.get(key) or {}).get("V")
        prev = next((x for x in reversed(recs) if x.get("kind") == "ub_check_all_candidates" and x.get("source") == "check"
                     and x.get("layout_key") == key), None)
        if prev is not None and prev.get("ok") and prev.get("V_open") == v_open:
            say(run, {"kind": "ub_check_skipped", "layout_key": key, "reason": "checked ok with the same V_open"})
            out.append(prev)
            continue
        res = BD.ub_check_all_candidates(ctx.ev, BL.Layout.from_key(key))
        rec = {"kind": "ub_check_all_candidates", "tag": "ub_check", "source": "check", "name": n, **res, "V_open": v_open,
               "same_value": (res.get("V_checked") is not None and v_open is not None
                              and abs(float(res["V_checked"]) - float(v_open)) <= 1e-6 * max(1.0, abs(float(v_open)))),
               "templates_resident": ctx.ev.resident_templates()}
        run.emit(C.jsonable(rec))
        say(run, {"kind": "ub_check_summary", "layout_key": key, "ok": res.get("ok"), "n_ok": res.get("n_ok"),
                  "V_checked": res.get("V_checked"), "V_open": v_open, "wall_s": res.get("wall_s")})
        out.append(rec)
    run.emit({"kind": "stage_done", "stage": stage_tag("ub-check"), "config_md5": ctx.config_md5()})
    return {"checked": [{k: r.get(k) for k in ("layout_key", "ok", "V_checked", "V_open")} for r in out]}


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def stage_report(run: R.Run, ctx: R.Ctx) -> str:
    recs = run.load()
    L: List[str] = [f"# R7 production search -- {ctx.family}", "",
                    f"Records `{run.records}`.  Generated {time.strftime('%Y-%m-%d %H:%M')}.", ""]
    res = R.last_results(recs)
    L += ["## Bounds per budget (last budget_result)", ""]
    L += R._table([{"m": ctx.m_of[b], "best": r.get("best_layout"), "UB": r.get("UB"), "LB": r.get("LB"), "kind": r.get("LB_kind"),
                    "gap": None if r.get("gap") is None else 100 * r["gap"], "cert": r.get("certified")}
                   for b, r in sorted(res.items())],
                  [("m", "m"), ("best", "best layout"), ("UB", "UB"), ("LB", "LB"), ("kind", "LB kind"), ("gap", "gap %"),
                   ("cert", "certified")], 2) + [""]
    ps = [r for r in recs if r.get("kind") == "pair_summary"]
    if ps:
        p = ps[-1]
        L += ["## Pair screens (m = 2; subset LP on S_LP, L_s elsewhere; bound over every size combination)", "",
              f"UB_2 {p.get('UB')}; {p.get('n_excluded')} of {p.get('n_screened')} pairs excluded "
              "(no layout of the pair below UB_2 - tol).", ""]
        L += R._table([{"pair": "|".join(x["atoms"]), "src": next((r.get("source") for r in recs if r.get("kind") == "pair_screen"
                                                                    and r.get("atoms") == x["atoms"]), None),
                        "bnd": x["bound_exact"], "win": x["bound_window"], "ex": x["excluded"]} for x in p["pairs"]],
                       [("pair", "pair"), ("src", "source"), ("bnd", "pair bound"), ("win", "window bound"), ("ex", "excluded")], 2) + [""]
    ps2 = probe_summary(recs)
    if ps2 is not None:
        L += ["## M3 bound probe (Tier 2 decision; lift = ILP OPEX bound over the cell LP value)", "",
              f"Verdict: {ps2['verdict']}.", ""]
        L += R._table(ps2["variants"], [("variant", "variant"), ("n_cells", "cells"), ("mean_lift_pct", "mean lift %"),
                                         ("n_optimal", "cells OPTIMAL"), ("limit_ok", f"limit >= {ps2['time_limit']:g} s")], 3) + [""]
        L += R._table(ps2["cells"], [("variant", "variant"), ("layout_key", "layout"), ("scenario", "s"), ("Qs", "LP Qs"),
                                      ("ilp_bound_opex", "ILP bound"), ("lift_pct", "lift %"), ("status", "status"),
                                      ("node_count", "nodes"), ("runtime_s", "runtime s"), ("time_limit", "limit s")], 3) + [""]
    m3 = [r for r in recs if r.get("kind") in ("m3_price", "m3_summary")]
    if m3:
        L += ["## m = 3 additions", ""]
        L += R._table([{"name": r.get("name") or "summary", "key": r.get("layout_key") or r.get("best_layout"), "status": r.get("status"),
                        "V": r.get("V") if r.get("kind") == "m3_price" else r.get("UB_3"), "lower": r.get("lower"),
                        "tier": r.get("tier"), "lower_open": r.get("lower_open")} for r in m3],
                      [("name", "variant"), ("key", "layout"), ("status", "status"), ("tier", "tier"), ("V", "V (UB)"),
                       ("lower", "LB all-candidates"), ("lower_open", "LB open_sites")], 2) + [""]
    pp = [r for r in recs if r.get("kind") == "pair_price" and r.get("tier") == "open_sites"]
    if pp:
        L += ["### Pair pricings on the open_sites tier (V = UB; LB all-candidates = envelope / LP / subset)", ""]
        L += R._table([{"atoms": "|".join(r.get("atoms") or []), "key": r.get("layout_key"), "status": r.get("status"),
                        "V": r.get("V"), "lower": r.get("lower"), "lower_open": r.get("lower_open")} for r in pp],
                      [("atoms", "pair"), ("key", "layout"), ("status", "status"), ("V", "V_open (UB)"),
                       ("lower", "LB all-candidates"), ("lower_open", "LB open_sites")], 2) + [""]
    rr = list({r["m"]: r for r in recs if r.get("kind") == "role_row" and r.get("best") is not None}.values())
    if rr:
        L += ["## Role table", ""]
        L += R._table(rr, [("m", "m"), ("follower", "follower"), ("UB", "UB"), ("LB", "LB"), ("best", "best"), ("best_V", "V"),
                           ("best_lower", "LB"), ("best_S", "best with S"), ("best_S_V", "V"), ("best_S_lower", "LB"),
                           ("price_of_S", "+ S"), ("best_hub", "best with hub"), ("best_hub_V", "V"), ("best_hub_lower", "LB"),
                           ("price_of_hub", "+ hub")], 2) + [""]
    oo = [r for r in recs if r.get("kind") == "oos_result" and r.get("source") == "r7_search"]
    if oo:
        L += ["## Out of sample (held-out scenarios; feasibility checked first)", ""]
        L += R._table([{"name": r.get("name"), "key": r.get("layout_key"), "st": r.get("status"), "vin": r.get("V_in"),
                        "vout": r.get("V_out"), "d": r.get("diff"), "tier": r.get("tier")} for r in oo],
                      [("name", "layout"), ("key", "key"), ("tier", "tier"), ("st", "status"), ("vin", "V in"), ("vout", "V out"),
                       ("d", "out - in")], 2) + [""]
    nr = [r for r in recs if r.get("kind") == "noradius_result"]
    if nr:
        sm = [r for r in recs if r.get("kind") == "noradius_summary"]
        L += ["## Radius effect (stage R: approach radius unset)", ""]
        L += R._table([{"g": r.get("group"), "key": r.get("layout_key"), "vr": r.get("V_radius"), "vn": r.get("V_noradius"),
                        "rel": None if r.get("rel") is None else 100 * r["rel"], "tier": r.get("tier"), "exact": r.get("exact")}
                       for r in nr],
                      [("g", "group"), ("key", "layout"), ("tier", "tier"), ("vr", "V radius 14"), ("vn", "V no radius"),
                       ("rel", "effect %"), ("exact", "both sides OPTIMAL")], 2)
        if sm:
            L += ["", f"* {sm[-1].get('consequence')}; m = 1 effect {sm[-1].get('m1_rel_effect')}, m = 2/3 effect "
                      f"{sm[-1].get('m23_rel_effect')}"]
        L += [""]
    lp_ = [r for r in recs if r.get("kind") == "list_price" and r.get("evaluator") == "in"]
    if lp_:
        last_lp = {}
        for r in lp_:
            last_lp[(r.get("layout_key"), r.get("tier") or "all_candidates")] = r
        L += ["## List pricing (price-list; open_sites V = UB only, LB all-candidates = envelope / LP / pricing)", ""]
        L += R._table([{"name": r.get("name"), "key": r.get("layout_key"), "tier": r.get("tier") or "all_candidates",
                        "status": r.get("status"), "V": r.get("V"), "lower": r.get("lower"), "lower_open": r.get("lower_open")}
                       for r in last_lp.values()],
                      [("name", "name"), ("key", "layout"), ("tier", "tier"), ("status", "status"), ("V", "V"),
                       ("lower", "LB all-candidates"), ("lower_open", "LB open_sites")], 2) + [""]
    uc = [r for r in recs if r.get("kind") == "ub_check_all_candidates" and r.get("source") == "check"]
    if uc:
        L += ["## UB validity check (M6: open_sites schedules on the all-candidates library)", ""]
        L += R._table([{"key": r.get("layout_key"), "ok": r.get("ok"), "n_ok": r.get("n_ok"), "vc": r.get("V_checked"),
                        "vo": r.get("V_open")} for r in uc],
                      [("key", "layout"), ("ok", "ok"), ("n_ok", "cells ok"), ("vc", "V_checked"), ("vo", "V_open")], 2) + [""]
    cal = [r for r in recs if r.get("kind") == "calib"]
    if cal:
        L += ["## Calibration (stage P)", ""] + [f"* {r.get('part')}: `{json.dumps(C.jsonable({k: v for k, v in r.items() if k not in ('kind', 'stage')}))[:600]}`"
                                                 for r in cal] + [""]
    L += RC.summary_lines(run.dir)
    path = os.path.join(run.dir, "SEARCH.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"# wrote {path}", flush=True)
    return path


STAGE_FN = {"calib": stage_calib, "oos-feas": stage_oos_feas, "pairs": stage_pairs, "m3": stage_m3, "roles": stage_roles,
            "oos": stage_oos, "noradius": stage_noradius, "price-list": stage_price_list,
            "import-records": stage_import_records, "ub-check": stage_ub_check, "report": stage_report}


# ---------------------------------------------------------------------------
# production lanes (plan sections 2.1 / 2.2)
# ---------------------------------------------------------------------------
#: (batch, plan stages, central hours incl. start-up and 10 %) of plan section 2.2
PROD_BATCHES = [(1, "P + A", 3.8), (2, "B + C", 13.9), (3, "D", 13.5), (4, "E + F + H", 9.2), (5, "G + I", 5.6), (6, "R", 4.0)]


def write_prod_lanes(args: argparse.Namespace) -> str:
    """The production lane plan of ``notes/siting_production_plan.md`` sections 2.1 / 2.2 for the
    r7i.4xlarge (``--max-threads`` 12, ``--max-rss-gb`` 110) in the ``deploy/aws/run_lanes.sh``
    format: one lanes file, the six batches chained by ``after`` (a batch starts when the previous
    one is done), every command prefixed with ``R7_BATCH=<n>`` and the instance price for
    ``cost.jsonl``.  Memory, not threads, keeps the lanes of a batch apart: the ``after`` chains
    serialise everything the 110 GB guard cannot hold twice."""
    usable = int(args.max_threads) if getattr(args, "max_threads_explicit", False) else 12
    rss = args.max_rss_gb if args.max_rss_gb is not None else 110.0
    out_dir = args.out_dir or "outputs/r7_siting"
    inst, usd = args.instance, float(args.usd_per_h)
    S_n = int(args.scenarios or 12)
    radius = 14 if args.approach_radius is None else int(args.approach_radius)
    # fixer pass: --held-out only on the two lanes that use the held-out scenarios (b1_oos_feas,
    # b5_oos); it builds 12 more N = 59 instances at start-up (about 15-28 s each) and changes no key
    held = " --held-out"
    tail = (f" --out-dir {out_dir} --family {args.family} --scenarios {S_n} --approach-radius {radius}"
            f" --max-rss-gb {rss:g} --tol-rel 0.01 --tol-abs 1 --restrict dot"
            + (f" --dot-csv {args.dot_csv}" if args.dot_csv else ""))
    lp_pool = " --lp-workers 3 --lp-threads 3 --master-threads 2"
    ilp_pool = " --price-workers 4 --threads 3"
    full = lp_pool + ilp_pool + f" --max-threads {usable}"
    design = S.scenario_design(S_n)
    order = R.root_order(design)
    lanes: List[Dict[str, Any]] = []

    def env(batch: int) -> str:
        return f"R7_BATCH={batch} R7_INSTANCE={inst} R7_USD_PER_H={usd:g} "

    def add(name: str, batch: int, threads: int, after: Sequence[str], cmd: str, hours: float, stage: str) -> None:
        lanes.append({"name": name, "batch": batch, "threads": int(threads), "after": ",".join(after) if after else "-",
                      "command": env(batch) + cmd, "hours": hours, "stage": stage})
    # batch 0: the STALE CODE gate (plan item 10): every production marker in the server tree
    add("b0_gate", 1, 1, [], "python3 experiments/r7_gate.py", 0.0, "gate")
    # batch 1: P (calibration) then A (one-site feasibility, 4 processes) and the held-out check
    add("b1_calib", 1, usable, ["b0_gate"], f"python3 experiments/r7_search.py --stage calib --wall 1.5{full}{tail}", 0.7, "P")
    feas_names = []
    P_feas = 4
    for g in range(P_feas):
        grp = sorted(order[g::P_feas])
        nm = f"b1_feas_{g + 1}"
        feas_names.append(nm)
        add(nm, 1, 1, ["b1_calib"], "python3 experiments/r7_siting.py --stage feas --feas-scenarios "
            + " ".join(str(s) for s in grp) + " --lp-workers 1 --lp-threads 1 --master-threads 1 --price-workers 1 --threads 1"
            " --max-threads 1" + tail, 2.4, "A")
    add("b1_oos_feas", 1, 1, feas_names, "python3 experiments/r7_search.py --stage oos-feas --lp-workers 1 --lp-threads 1"
        " --master-threads 1 --price-workers 1 --threads 1 --max-threads 1" + tail + held, 0.3, "A (held-out)")
    # batch 2: B + C (m = 1 LP pass with the skip list, then pricing and batched escalation)
    add("b2_m1", 2, usable, ["b1_oos_feas"] + feas_names, f"python3 experiments/r7_siting.py --stage m1 --wall-m1 13{full}{tail}",
        12.3, "B + C")
    # batch 3: D (all-open root LPs, one process per scenario, 3 chains, longest stratum first)
    k = 3
    T = max(1, usable // k)
    root_names = []
    imp = f" --root-import {args.root_import or STEP2B_POOL}"
    for i, s in enumerate(order):
        nm = f"b3_rootlp_s{s:02d}"
        after = ["b2_m1"] if i < k else [root_names[i - k]]
        add(nm, 3, T, after, f"python3 experiments/r7_siting.py --stage rootlp --root-scenarios {s}"
            + (imp if i == 0 else "") + f" --lp-workers 1 --lp-threads {T} --master-threads 1 --price-workers 1 --threads 1"
            f" --max-threads {T}" + tail, round(11.9 / len(order) * k, 2), "D")
        root_names.append(nm)
    last_roots = root_names[-k:]
    # batch 4: E + F + H
    seeds = " ".join(str(x).replace("|", "+") for x in args.pair_seeds) if args.pair_seeds else "D30+D38 D09+D38"
    add("b4_pairs", 4, usable, last_roots, f"python3 experiments/r7_search.py --stage pairs --wall 5 --pair-seeds {seeds}"
        f" --pair-screens 16 --pair-price 4{full}{tail}", 4.0, "E")
    add("b4_m3", 4, usable, ["b4_pairs"], f"python3 experiments/r7_search.py --stage m3 --wall 2 --m3-thirds 2{full}{tail}", 1.3, "F")
    add("b4_roles", 4, usable, ["b4_m3"], f"python3 experiments/r7_search.py --stage roles --wall 3.5 --hub-scenarios 3"
        f" --role-hub-price 2{full}{tail}", 2.7, "H")
    # batch 5: G (filtered comparison, DOT-only restricted) + I (out of sample)
    add("b5_comparison", 5, usable, ["b4_roles"], "python3 experiments/r7_siting.py --stage comparison --wall-comparison 4"
        " --comparison-rules CSCD@1,2,3 CSAV@2 dot_all_pilot dot_pilot_proxy@2 --comparison-time-limits 2:600" + full + tail,
        2.6, "G")
    add("b5_restricted", 5, usable, ["b5_comparison"], f"python3 experiments/r7_siting.py --stage restricted --wall-restricted 1{full}{tail}",
        0.7, "G (DOT-only)")
    add("b5_oos", 5, usable, ["b5_restricted"], f"python3 experiments/r7_search.py --stage oos --wall 2{full}{tail}{held}", 1.5, "I")
    # batch 6: R (no-radius re-pricing, 3 workers, templates evicted per group of 4)
    add("b6_noradius", 6, 9, ["b5_oos"], "python3 experiments/r7_search.py --stage noradius --wall 5 --noradius-group 4"
        " --lp-workers 3 --lp-threads 2 --master-threads 2 --price-workers 3 --threads 3 --max-threads 9" + tail, 3.3, "R")
    lanes_dir = os.path.abspath(args.lanes_dir) if args.lanes_dir else PROD_LANES_ROOT
    os.makedirs(lanes_dir, exist_ok=True)
    rel = os.path.relpath(lanes_dir, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(lanes_dir, "lanes.txt")
    tot_h = sum(h for _b, _s, h in PROD_BATCHES)
    head = ["# R7 siting PRODUCTION lanes for deploy/aws/run_lanes.sh -- written by experiments/r7_search.py --write-lanes",
            f"# plan: notes/siting_production_plan.md sections 2.1 / 2.2; instance {inst} at {usd:g} USD/h, dispatcher budget "
            f"{usable} threads, --max-rss-gb {rss:g}",
            "# precondition: the step-2b probe has finished or was stopped by hand ('tmux ls' shows no probe session and "
            "outputs/r7_siting_probe/probe.log ends with 'probe done'); the 110 GB guard is per process",
            f"# start on the server (project root, after deploy/aws/sync_up.sh): LANES_DIR=$PWD/ebike_swap_sim/{rel} "
            f"bash deploy/aws/run_lanes.sh start ebike_swap_sim/{rel}/lanes.txt --max-threads {usable}",
            "# batches run one after the other (after = the previous batch's last lanes); every command appends to "
            f"{out_dir}/cost.jsonl (R7_BATCH)",
            "# analysis on the laptop after sync_down: r7_siting.py --stage analyse and r7_search.py --stage report (same flags)",
            "# re-run 'run_lanes.sh start' after a stop: every stage resumes from records.jsonl + cuts.jsonl + cache/",
            "# format: name <TAB> threads <TAB> after <TAB> command (bash, from the package root)"]
    for b, stg, h in PROD_BATCHES:
        head.append(f"# batch {b} ({stg}): about {h} h = {h * usd:.1f} USD (plan 2.2, incl. start-up and 10 %)")
    head.append(f"# total about {tot_h:.1f} h = {tot_h * usd:.1f} USD")
    lines = list(head)
    cur = None
    for l in lanes:
        if l["batch"] != cur:
            cur = l["batch"]
            lines.append(f"# ---- batch {cur}")
        lines.append(f"# {l['name']}: stage {l['stage']}, about {l['hours']} h")
        lines.append("\t".join([l["name"], str(l["threads"]), l["after"], l["command"]]))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    meta = {"lanes": lanes, "batches": [{"batch": b, "stages": stg, "hours": h, "usd": round(h * usd, 2),
                                         "lanes": [l["name"] for l in lanes if l["batch"] == b]} for b, stg, h in PROD_BATCHES],
            "instance": inst, "usd_per_h": usd, "usable_threads": usable, "max_rss_gb": rss, "out_dir": out_dir,
            "total_hours": tot_h, "total_usd": round(tot_h * usd, 2), "root_order": order}
    with open(os.path.join(lanes_dir, "lanes.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    print(f"wrote {path} ({len(lanes)} lanes, 6 batches, about {tot_h:.1f} h = {tot_h * usd:.1f} USD)")
    return path


#: re-plan after batch 2 (notes/siting_production_replan_m1.md with the critic corrections K1-K7):
#: (lane, central hours, (low, high)) of the post-batch-3 run, 4 x 3 pricing on the r7i.4xlarge
R2_HOURS = {"r2_gate": (0.0, (0.0, 0.0)),
            # M1 + M1-rest at 4 x 3: 144 cells x about 300 s / 4 = 3.0 h (2.0-5.3) plus 0.3-0.5 h of extension
            # (K2.4 / K5: 0-1.7 h); no cover rows, so no template build at start-up
            "r2_m1_ub": (3.3, (2.0, 6.5)),
            "r2_m3probe_a": (0.43, (0.35, 0.55)), "r2_m3probe_b": (0.43, (0.35, 0.55)),     # K5: 0.85 (0.7-1.1)
            "r2_m4": (0.5, (0.4, 0.6)),                                                      # K5 (setup 0.42 h)
            "r2_m6": (0.2, (0.15, 0.3)),                                                     # K3.5 / K5, mandatory
            # review of the r2 lanes: pairs / roles / restricted keep the cover rows (subset-LP screens, the
            # restricted master bound), so each builds the 12 all-candidates templates at start-up: + 0.3 h
            # (0.2-0.4, batch-2 log: 12 builds, about 577 s, plus the LPs); m3 / comparison run with
            # --cover-rows off (pricing only, the prior LBs restored): no setup term
            "r2_b4_pairs": (3.7, (3.1, 4.6)), "r2_b4_m3": (0.6, (0.4, 0.9)), "r2_b4_roles": (2.5, (2.0, 3.2)),
            "r2_b5_comparison": (1.3, (1.0, 1.9)), "r2_b5_restricted": (1.0, (0.7, 1.4)), "r2_b5_oos": (0.9, (0.7, 1.3)),
            "r2_b6_noradius": (1.5, (1.2, 2.4))}
#: re-plan section 3: the 10 % contingency of batches 4, 5 and 6 (hours), counted in the totals
R2_CONTINGENCY = {"4": 0.6, "5": 0.3, "6": 0.2}
#: K5 / K6: Tier 2 (M5 + M4 again), conditional, at most 0.9 gap points (K2.6)
R2_TIER2_HOURS = {"r2t2_gate": (0.0, (0.0, 0.0)), "r2t2_m5": (3.2, (2.5, 4.2)), "r2t2_m4": (0.5, (0.4, 0.6))}
#: M3 / M5 cells: the weekday scenarios of the lowest-LP B3:C2 locations of the batch-2 records
#: (lp_location: D29 1034.1, D28 1036.0, D34 1037.2); M3 = D29 s5 and s2 (p = 0.119 each)
R2_PROBE = ("D29:SC:B3:C2", ("D29:5", "D29:2"))
R2_TIER2 = (("D29:SC:B3:C2", "D28:SC:B3:C2", "D34:SC:B3:C2"), ("D29:0-5", "D28:0-5", "D34:0-5"))


def write_r2_lanes(args: argparse.Namespace) -> str:
    """Re-plan change 9: the post-batch-3 lane plan for the r7i.4xlarge (12 threads, 110 GB guard),
    ``lanes_r2.txt`` (Tier 1 + batches 4-6, one chain) and ``lanes_r2_tier2.txt`` (Tier 2, NOT
    chained: started by hand only when M3 shows a mean bound lift >= 1 % at 1,200 s), each with a
    ``.json``.  Every lane writes ``cost.jsonl`` rows (the gate through ``--cost-dir``); every
    pricing lane passes ``--verify-start unchecked`` (change 6) and ``--tol-rel 0.01``; batches 4-6
    pass ``--price-tier open_sites`` (change 7) with the re-plan walls; lane names carry the prefix
    ``r2_`` / ``r2t2_`` so that their status files never collide with ``lanes.txt``."""
    usable = 12
    rss = args.max_rss_gb if args.max_rss_gb is not None else 110.0
    out_dir = args.out_dir or "outputs/r7_siting"
    inst, usd = args.instance, float(args.usd_per_h)
    S_n = int(args.scenarios or 12)
    radius = 14 if args.approach_radius is None else int(args.approach_radius)
    tail = (f" --out-dir {out_dir} --family {args.family} --scenarios {S_n} --approach-radius {radius}"
            f" --max-rss-gb {rss:g} --tol-rel 0.01 --tol-abs 1 --restrict dot"
            + (f" --dot-csv {args.dot_csv}" if args.dot_csv else ""))
    vs = " --verify-start unchecked"
    full = " --lp-workers 3 --lp-threads 3 --master-threads 2 --price-workers 4 --threads 3 --max-threads 12"
    op = " --price-tier open_sites --time-limit 600 --time-limit-many-sites 5:900"
    seeds = " ".join(str(x).replace("|", "+") for x in args.pair_seeds) if args.pair_seeds else "D30+D38 D09+D38"
    params = BD.parse_ilp_params(args.ilp_params) if args.ilp_params else {}
    ptxt = (" --ilp-params " + " ".join(f"{k}={v}" for k, v in params.items())) if params else ""

    def env(batch: str) -> str:
        return f"R7_BATCH={batch} R7_INSTANCE={inst} R7_USD_PER_H={usd:g} "

    def lanes_of(spec: Sequence[Tuple[str, str, int, Sequence[str], str, str]], hours: Dict[str, Tuple[float, Tuple[float, float]]]
                 ) -> List[Dict[str, Any]]:
        out = []
        for name, batch, thr, after, cmd, step in spec:
            h, rng = hours[name]
            out.append({"name": name, "batch": batch, "threads": int(thr), "after": ",".join(after) if after else "-",
                        "command": env(batch) + cmd, "hours": h, "range": list(rng), "step": step})
        return out
    gate = f"python3 experiments/r7_gate.py --cost-dir {out_dir}"
    pl = "python3 experiments/r7_search.py --stage price-list --evaluator in"
    m4 = ("python3 experiments/r7_siting.py --stage m1 --m1-pass2 off --max-escalations 0 --wall-m1 1.5 --lp-workers 3"
          " --lp-threads 3 --master-threads 2 --price-workers 1 --threads 1 --max-threads 12" + vs + tail)
    probe = (f"{pl} --tier all_candidates --layouts {R2_PROBE[0]} --cells {' '.join(R2_PROBE[1])} --warm-tier open_sites"
             " --cover-rows off --time-limit 1200 --wall 1 --lp-workers 1 --lp-threads 1 --master-threads 1 --price-workers 2"
             " --threads 4 --max-threads 8" + vs + tail)
    spec1 = [
        ("r2_gate", "2b", 1, [], gate, "gate (markers of changes 1-9)"),
        ("r2_m1_ub", "2b", 12, ["r2_gate"],
         f"{pl} --tier open_sites --layouts {M1_LP_ORDER} --lp-order-below 1075 --extend-below-ub on --extend-max 24"
         " --cover-rows off --time-limit 600 --wall 6 --lp-workers 1 --lp-threads 1 --master-threads 2 --price-workers 4"
         " --threads 3 --max-threads 12" + vs + tail, "M1 + M1-rest (open_sites UB pass in LP order)"),
        ("r2_m4", "2b", 12, ["r2_m1_ub"], m4, "M4 m1 resume without pricing (official m = 1 bound pair)"),
        ("r2_m6", "2b", 3, ["r2_m4"],
         "python3 experiments/r7_search.py --stage ub-check --layouts best@m1 --max-templates 2 --wall 1 --lp-workers 1"
         " --lp-threads 1 --master-threads 1 --price-workers 1 --threads 1 --max-threads 3" + tail,
         "M6 UB validity check (mandatory, K3.5)"),
        # review: the probes are a side branch after M6 (K2.6: M3 moves the m = 1 floor by 0); a failed probe
        # blocks nothing else; 8 threads each, so the dispatcher runs them one at a time before batch 4
        ("r2_m3probe_a", "2b", 8, ["r2_m6"], probe, "M3 bound probe, variant a (default params, 2 x 4, K3.6; side branch)"),
        ("r2_m3probe_b", "2b", 8, ["r2_m6"], probe.replace(" --cover-rows off", " --ilp-params Method=2 --cover-rows off"),
         "M3 bound probe, variant b (Method 2; side branch; its probe_summary record gives the Tier 2 verdict)"),
        ("r2_b4_pairs", "4", 12, ["r2_m6"],
         f"python3 experiments/r7_search.py --stage pairs{op} --wall 4 --pair-seeds {seeds} --pair-screens 16 --pair-price 4"
         + full + vs + tail, "E (pairs: screens unchanged, pricing open_sites)"),
        ("r2_b4_m3", "4", 12, ["r2_b4_pairs"],
         f"python3 experiments/r7_search.py --stage m3{op} --wall 1 --m3-thirds 2 --cover-rows off" + full + vs + tail,
         "F (m = 3; no cover rows: pricing only, --m3-screen 0)"),
        ("r2_b4_roles", "4", 12, ["r2_b4_m3"],
         f"python3 experiments/r7_search.py --stage roles{op} --wall 2.5 --hub-scenarios 3 --role-hub-price 2" + full + vs + tail,
         "H (role table)"),
        ("r2_b5_comparison", "5", 12, ["r2_b4_roles"],
         f"python3 experiments/r7_siting.py --stage comparison{op} --wall-comparison 2 --comparison-rules CSCD@1,2,3 CSAV@2"
         " dot_all_pilot dot_pilot_proxy@2 --comparison-time-limits 2:600 --cover-rows off" + full + vs + tail,
         "G (comparison; no cover rows: pricing only)"),
        ("r2_b5_restricted", "5", 12, ["r2_b5_comparison"],
         f"python3 experiments/r7_siting.py --stage restricted{op} --wall-restricted 1" + full + vs + tail,
         "G (DOT-only; cover rows kept for the restricted master bound)"),
        ("r2_b5_oos", "5", 12, ["r2_b5_restricted"],
         f"python3 experiments/r7_search.py --stage oos{op} --wall 1" + full + vs + tail + " --held-out", "I (out of sample)"),
        ("r2_b6_noradius", "6", 12, ["r2_b5_oos"],
         f"python3 experiments/r7_search.py --stage noradius{op} --wall 2 --noradius-group 4" + full + vs + tail,
         "R (radius effect, open_sites with and without the radius)"),
    ]
    spec2 = [
        ("r2t2_gate", "2b_tier2", 1, [], gate, "gate"),
        ("r2t2_m5", "2b_tier2", 8, ["r2t2_gate"],
         f"{pl} --tier all_candidates --layouts {' '.join(R2_TIER2[0])} --cells {' '.join(R2_TIER2[1])} --warm-tier open_sites"
         + ptxt + " --cover-rows off --time-limit 1200 --wall 4.5 --lp-workers 1 --lp-threads 1 --master-threads 1"
         " --price-workers 2 --threads 4 --max-threads 8" + vs + tail,
         "M5 Tier 2 bound pass (18 weekday cells, the 2 M3 cells re-used)"),
        ("r2t2_m4", "2b_tier2", 12, ["r2t2_m5"], m4, "M4 again (floor with the Tier 2 cell bounds)"),
    ]
    l1, l2 = lanes_of(spec1, R2_HOURS), lanes_of(spec2, R2_TIER2_HOURS)
    lanes_dir = os.path.abspath(args.lanes_dir) if args.lanes_dir else PROD_LANES_ROOT
    os.makedirs(lanes_dir, exist_ok=True)
    rel = os.path.relpath(lanes_dir, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def tot(ls: Sequence[Dict[str, Any]], extra: float = 0.0) -> Tuple[float, float, float]:
        return (sum(x["hours"] for x in ls) + extra, sum(x["range"][0] for x in ls) + extra,
                sum(x["range"][1] for x in ls) + extra)
    cont = sum(R2_CONTINGENCY.values())
    t1, t2 = tot(l1, cont), tot(l2)

    def batches(ls: Sequence[Dict[str, Any]], contingency: Dict[str, float]) -> List[Dict[str, Any]]:
        out = []
        for b in dict.fromkeys(x["batch"] for x in ls):
            xs = [x for x in ls if x["batch"] == b]
            h = sum(x["hours"] for x in xs) + contingency.get(b, 0.0)
            out.append({"batch": b, "lanes": [x["name"] for x in xs], "hours": round(h, 2), "usd": round(h * usd, 2),
                        "range_h": [round(sum(x["range"][0] for x in xs) + contingency.get(b, 0.0), 2),
                                    round(sum(x["range"][1] for x in xs) + contingency.get(b, 0.0), 2)]})
        return out

    def write(fname: str, ls: Sequence[Dict[str, Any]], head: List[str], meta: Dict[str, Any]) -> str:
        path = os.path.join(lanes_dir, fname)
        lines = list(head)
        cur = None
        for x in ls:
            if x["batch"] != cur:
                cur = x["batch"]
                lines.append(f"# ---- batch {cur}")
            lines.append(f"# {x['name']}: {x['step']}, about {x['hours']} h ({x['range'][0]}-{x['range'][1]})")
            lines.append("\t".join([x["name"], str(x["threads"]), x["after"], x["command"]]))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(os.path.splitext(path)[0] + ".json", "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=1)
        return path
    common = [f"# instance {inst} at {usd:g} USD/h, dispatcher budget {usable} threads, --max-rss-gb {rss:g} per process; "
              "--tol-rel 0.01 everywhere (the analyse stage reports the open_sites gap with tol 0, K2.2)",
              "# format: name <TAB> threads <TAB> after <TAB> command (bash, from the package root); every lane appends to "
              f"{out_dir}/cost.jsonl (R7_BATCH)",
              "# pre-flight: bash deploy/aws/r7_prod_check.sh --no-probe (markers of changes 1-9 and both r2 lane files)"]
    h1 = ["# R7 siting re-plan after batch 2, Tier 1 + batches 4-6 -- written by experiments/r7_search.py --write-lanes "
          "--lanes-plan r2",
          "# plan: notes/siting_production_replan_m1.md sections 2-7 with the critic corrections K1-K7 (they override the plan); "
          "no concurrent C0 lane: everything runs after batch 3 at 4 x 3 pricing",
          "# precondition: batch 3 is finished (run_lanes.sh status shows the 12 b3_rootlp lanes done, no tmux session "
          "lanes_dispatch); the batch 4-6 lanes of lanes.txt are SUPERSEDED by this file and must not be started",
          "# upload: deploy/aws/sync_up.sh / unzip r7_code_r2.zip ONLY AFTER the 12 b3_rootlp lanes are done (later batch-3 "
          "lanes would otherwise import the re-plan code mid-batch; no rootlp run was made on the new tree)",
          f"# start (project root, after deploy/aws/sync_up.sh): LANES_DIR=$PWD/ebike_swap_sim/{rel} bash deploy/aws/run_lanes.sh "
          f"start ebike_swap_sim/{rel}/lanes_r2.txt --max-threads {usable}",
          "#   or per batch with --only (2b first: r2_gate,r2_m1_ub,r2_m4,r2_m6,r2_m3probe_a,r2_m3probe_b); every stage resumes "
          "from records.jsonl + cuts.jsonl + cache/",
          "# chain: gate -> M1 -> M4 -> M6 -> batch 4-6; the M3 probes hang off M6 as a side branch (a failed probe blocks "
          "nothing; they run before batch 4 because the dispatcher starts lanes in file order)",
          "# M4 is LP-free only while the best open_sites value stays below about 1176 (K2.4); M3 moves the floor by 0 (K2.6) "
          "and decides Tier 2 (lanes_r2_tier2.txt, started by hand only if the mean bound lift is >= 1 % at 1,200 s: the "
          "probe_summary record of r2_m3probe_b, or r7_search.py --stage report, gives the verdict)",
          "# after sync_down: r7_siting.py --stage analyse and r7_search.py --stage report (same flags) on the laptop"] + common
    for b in batches(l1, R2_CONTINGENCY):
        h1.append(f"# batch {b['batch']}: about {b['hours']} h = {b['usd']:.1f} USD (range {b['range_h'][0]}-{b['range_h'][1]} h"
                  + (f", incl. {R2_CONTINGENCY[b['batch']]} h contingency" if b["batch"] in R2_CONTINGENCY else "") + ")")
    h1.append(f"# total about {t1[0]:.1f} h = {t1[0] * usd:.1f} USD (range {t1[1]:.1f}-{t1[2]:.1f} h = "
              f"{t1[1] * usd:.1f}-{t1[2] * usd:.1f} USD); Tier 2 (lanes_r2_tier2.txt) adds {t2[0]:.1f} h = {t2[0] * usd:.1f} USD")
    h2 = ["# R7 siting re-plan after batch 2, Tier 2 (M5 + M4 again) -- written by experiments/r7_search.py --write-lanes "
          "--lanes-plan r2",
          "# CONDITIONAL and NOT chained to lanes_r2.txt: start it by hand only when r2_m3probe_a / _b show a mean bound lift "
          ">= 1.0 % over the cell LP at 1,200 s in the better variant (re-plan M5); at most 0.9 gap points (K2.6: D33 caps the "
          "floor at 1043.54)",
          "# the M5 lane uses the default Gurobi params; when variant b (Method 2) was better, regenerate this file with "
          "--write-lanes --lanes-plan r2 --ilp-params Method=2",
          "# precondition: every lane of lanes_r2.txt is done or stopped (no tmux session lanes_dispatch)",
          f"# start: LANES_DIR=$PWD/ebike_swap_sim/{rel} bash deploy/aws/run_lanes.sh start "
          f"ebike_swap_sim/{rel}/lanes_r2_tier2.txt --max-threads {usable}"] + common
    h2.append(f"# total about {t2[0]:.1f} h = {t2[0] * usd:.1f} USD (range {t2[1]:.1f}-{t2[2]:.1f} h)")
    meta1 = {"plan": "notes/siting_production_replan_m1.md + critic K1-K7", "lanes": l1, "batches": batches(l1, R2_CONTINGENCY),
             "contingency_h": R2_CONTINGENCY, "instance": inst, "usd_per_h": usd, "usable_threads": usable, "max_rss_gb": rss,
             "out_dir": out_dir, "tol_rel": 0.01, "total_hours": round(t1[0], 2), "total_usd": round(t1[0] * usd, 2),
             "range_hours": [round(t1[1], 2), round(t1[2], 2)], "tier2_hours": round(t2[0], 2), "tier2_usd": round(t2[0] * usd, 2)}
    meta2 = {"plan": "re-plan M5 (Tier 2), conditional", "lanes": l2, "batches": batches(l2, {}), "instance": inst,
             "usd_per_h": usd, "usable_threads": usable, "max_rss_gb": rss, "out_dir": out_dir, "ilp_params": params,
             "total_hours": round(t2[0], 2), "total_usd": round(t2[0] * usd, 2), "range_hours": [round(t2[1], 2), round(t2[2], 2)]}
    p1 = write("lanes_r2.txt", l1, h1, meta1)
    write("lanes_r2_tier2.txt", l2, h2, meta2)
    print(f"wrote {p1} ({len(l1)} lanes, about {t1[0]:.1f} h = {t1[0] * usd:.1f} USD) and lanes_r2_tier2.txt ({len(l2)} lanes, "
          f"about {t2[0]:.1f} h = {t2[0] * usd:.1f} USD)")
    return p1


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = R.build_parser()
    ap.description = (__doc__ or "").split("\n")[0]
    for act in ap._actions:
        if act.dest == "stage":
            act.default = "all"
            act.help = "comma-separated stages or 'all' (" + ", ".join(ALL_STAGES) + "): " + ", ".join(SEARCH_STAGES)
    ap.add_argument("--wall", type=float, default=None, help="hours for this invocation's stage (default per stage)")
    ap.add_argument("--pair-seeds", nargs="*", default=None, help="seed pairs 'A+B' (or 'A|B', quoted) or layout keys")
    ap.add_argument("--pair-screens", type=int, default=16, help="pairs screened by a subset LP on S_LP")
    ap.add_argument("--pair-price", type=int, default=4, help="best screened pairs priced (PRICED results counted)")
    ap.add_argument("--pair-tries", type=int, default=4,
                    help="layouts tried per pair: the nearest sizes first, then by envelope after a PRUNED_BY_BOUND try")
    ap.add_argument("--pair-swap-pool", type=int, default=8, help="m = 1-ranked locations tried in the 1-swaps")
    ap.add_argument("--complement-seeds", type=int, default=4, help="coverage-complement seed pairs")
    ap.add_argument("--rr-seeds", type=int, default=2, help="relax-and-round seeds of the master LP point (0 = off)")
    ap.add_argument("--m3-thirds", type=int, default=2, help="third sites added to the best pair")
    ap.add_argument("--m3-screen", type=int, default=0, help="third sites screened by a triple subset LP first (0 = off)")
    ap.add_argument("--role-budgets", nargs="*", type=int, default=[2], help="m values of the role table")
    ap.add_argument("--role-pairs", type=int, default=2, help="location pairs searched for the best S-containing layout")
    ap.add_argument("--hub-scenarios", type=int, default=3, help="scenarios of the hub screen subset LPs")
    ap.add_argument("--role-hub-price", type=int, default=2, help="hub layouts priced after the screen")
    ap.add_argument("--oos-layouts", nargs="*", default=None, help=f"out-of-sample list (default {' '.join(OOS_DEFAULT)})")
    ap.add_argument("--near-tie", type=float, default=0.03, help="stage noradius: m = 1 layouts within this share of UB_1")
    ap.add_argument("--noradius-group", type=int, default=4, help="templates resident at once in stage noradius")
    ap.add_argument("--noradius-time-limit", choices=["match", "base"], default="match",
                    help="stage noradius: solve each cell at the radius row's time limit (match) or at the base limit "
                         "(base: the effect is then a lower bound)")
    ap.add_argument("--layouts", nargs="*", default=None, help="stage price-list: layout keys or names")
    ap.add_argument("--layouts-file", default=None, help="stage price-list: one layout key per line")
    ap.add_argument("--evaluator", choices=["in", "out", "noradius"], default="in", help="stage price-list evaluator")
    ap.add_argument("--calib-layout", default=None, help="stage calib: one-site layout (default the transplanted M09)")
    # R7 re-plan after batch 2 (notes/siting_production_replan_m1.md changes 2, 3, 5, 9)
    ap.add_argument("--tier", choices=list(BD.PRICING_TIERS), default="all_candidates",
                    help="stage price-list: pricing tier (open_sites = upper bounds only, price_open records; change 2)")
    ap.add_argument("--cells", nargs="*", default=None,
                    help="stage price-list (all_candidates): cells LOC:s / LOC:0-5 / LOC:2+5 / KEY@s; uncached cells outside "
                         "the filter are not solved (K3.1; the bound probe M3 / Tier 2)")
    ap.add_argument("--warm-tier", choices=["open_sites"], default=None,
                    help="stage price-list (all_candidates): MIP starts from the open-sites schedules of the same cells (change 4)")
    ap.add_argument("--ilp-params", nargs="*", default=None,
                    help="stage price-list: extra Gurobi parameters K=V (enter the cache key: new rows by design); with "
                         "--write-lanes --lanes-plan r2: the params of the Tier 2 lanes (the better M3 variant)")
    ap.add_argument("--lp-order-below", type=float, default=None,
                    help=f"stage price-list, --layouts {M1_LP_ORDER}: the m = 1 layouts with an all-candidates lower bound "
                         "below this value, lowest first (re-plan M1: 1075)")
    ap.add_argument("--lp-order-top", type=int, default=None,
                    help=f"stage price-list, --layouts {M1_LP_ORDER}: the first N of the LP order (when --lp-order-below is unset)")
    ap.add_argument("--extend-below-ub", choices=["on", "off"], default="off",
                    help="stage price-list: after the list, price the next m = 1 layouts in LP order while their lower bound "
                         "is below the best open_sites value at m = 1 (tol 0; re-plan M1-rest)")
    ap.add_argument("--extend-max", type=int, default=24, help="stage price-list: at most N layouts added by --extend-below-ub")
    ap.add_argument("--from", dest="import_from", default=None,
                    help="stage import-records: the out-dir whose price / price_open records and cache rows are merged (change 3)")
    # --cover-rows: defined in r7_siting.build_parser (also used by stages comparison / restricted there)
    ap.add_argument("--lanes-plan", choices=["prod", "r2"], default="prod",
                    help="--write-lanes: 'prod' (lanes.txt, plan sections 2.1 / 2.2) or 'r2' (lanes_r2.txt + "
                         "lanes_r2_tier2.txt, the re-plan after batch 2)")
    ap.add_argument("--instance", default=RC.DEFAULT_INSTANCE, help="--write-lanes: instance type for cost.jsonl")
    ap.add_argument("--usd-per-h", type=float, default=RC.DEFAULT_USD_PER_H, help="--write-lanes: price for cost.jsonl")
    return ap


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    return R.parse_args(argv, parser=build_parser())


def main(argv: Optional[List[str]] = None) -> Any:
    args = parse_args(argv)
    if args.write_lanes:
        return write_r2_lanes(args) if getattr(args, "lanes_plan", "prod") == "r2" else write_prod_lanes(args)
    stages = list(ALL_STAGES) if args.stage == "all" else [s.strip() for s in args.stage.split(",") if s.strip()]
    for st in stages:
        if st not in SEARCH_STAGES:
            raise SystemExit(f"unknown stage {st!r}; choose from {SEARCH_STAGES}")
    if not all(st in POOL_FREE for st in stages):
        if args.lp_workers * args.lp_threads + args.master_threads > args.max_threads:
            raise SystemExit(f"lp_workers x lp_threads + master_threads exceeds --max-threads {args.max_threads}")
        if args.price_workers * args.threads > args.max_threads:
            raise SystemExit(f"price_workers x threads exceeds --max-threads {args.max_threads}")
    warnings.simplefilter("ignore")
    run = R.Run(args)
    cost = RC.CostLog(run.dir, ",".join(stages), "r7_search.py", dry_run=bool(args.dry_run), argv=argv,
                      enabled=not all(st in ("report",) for st in stages))     # laptop report: not billed
    cost.install_signal_handlers()              # run_lanes.sh stop / tmux kill-session still write the row
    status = "error"
    try:
        ctx = R.Ctx(run)
        md5 = ctx.config_md5()
        out: Dict[str, Any] = {}
        for st in stages:
            run.stage = stage_tag(st)
            if st not in ALWAYS_RUN and not args.dry_run and not args.redo and stage_done(run.load(), st, md5):
                run.emit({"kind": "stage_skipped", "stage": stage_tag(st), "reason": "stage_done record with the same configuration"},
                         echo=True)
                continue
            t0 = time.perf_counter()
            out[st] = STAGE_FN[st](run, ctx)
            if not args.dry_run:
                with open(os.path.join(run.dir, "wall_time.json"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"stage": stage_tag(st), "wall_s": time.perf_counter() - t0, "rss_gb": R.rss_gb(),
                                         "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
        ctx.close()
        status = "ok"
        return out
    except BaseException as exc:  # noqa: BLE001 -- recorded in cost.jsonl, then re-raised
        status = f"error: {type(exc).__name__}"
        raise
    finally:
        cost.finish(status)


if __name__ == "__main__":
    main()
