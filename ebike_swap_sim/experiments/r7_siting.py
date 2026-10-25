"""R7 siting scale-up (``notes/siting_scaleup_design.md``, section 4 as corrected in section 7):
optimal siting of swapping / charging stations on the DOT-based candidate set of Manhattan
(family ``manhattan_dot``: 40-60 DOT sites + the 15 lattice candidates, reduced size menu, hubs
only at hub-capable sites, transfer services within 2 km) on >= 10 stratified demand scenarios,
with certified bounds (m = 1 by pruned enumeration, m = 2-3 by the regional subset
branch-and-bound) and the comparison protocol of design section 2.6.  No E2 equation changes;
the lower level is the unchanged operations ILP priced through ``bilevel.LowerLevelEvaluator``.

Stages (``--stage``; ``all`` runs them in this order; every stage appends to ``records.jsonl``,
``cuts.jsonl`` and ``cache/`` of ``--out-dir`` and resumes from them):

``setup``       candidates (DOT CSV -> ``candidates.csv`` / ``candidates_dropped.csv``), scenario
                design, demand hashes, template / LP sizes, z-column count, RSS, the four LP
                timings of the ``size`` dry run (one-site, two-site, one-cell free-size, all-open
                free-size), superset bound.
``feas``        stage A of the production plan: one-site terminal-feasibility screen (library builds
                only, no solve) on ``--feas-scenarios`` (default all), written to
                ``feas_one_site_<tag>.json`` with the configuration's ``feasibility_signature``; the
                later stages read every ``feas_one_site*.json`` of ``--out-dir`` (or ``--feas-json``)
                and mark the one-site layouts of a terminal-infeasible location INFEASIBLE_TERMINAL
                (``V = inf``, no LP) with a terminal row in the master (claims of a file with another
                signature, e.g. ``r7_probe.py feas``, are re-proved by one library build each).
``rootlp``      stage D: the all-open free-size subset LP per scenario (``--root-scenarios``, default
                all, longest stratum first; one process per scenario in the lanes of ``--write-lanes
                --lanes rootlp``) -> ``root_lp/root_s<NN>.json`` (``bound.json`` form: ``key``,
                ``bound``, ``rows``); merged on restore as ``L_s = max(L_s, value)`` (``--root-merge``).
``comparison``  rule layouts CSCD / CSTC / CSAV scaled to N at every budget, the DOT pilot proxy
                (capacity-matched) and the all-pilot layout, the transplanted 15-candidate optima;
                all priced on the ``all_candidates`` tier (design 2.5; ``--price-tier open_sites``, re-plan
                change 7: on the open-sites tier, V = UB_rule, LB_rule = envelope / LP).  Production filter (plan 5
                item 5): ``--comparison-rules CSCD@1,2,3 CSAV@2 dot_all_pilot dot_pilot_proxy@2``,
                ``--comparison-budgets``, ``--comparison-time-limits 2:600`` (auto for manhattan_dot).
``m1``          pruned enumeration of budget m = 1 with one LP per location (design 2.2).
``bb2`` / ``bb3`` regional subset branch-and-bound at m = 2 / 3 (design 2.3; ``S_LP`` scenarios;
                ``benders.certify_bnb``: the budget window ``(budget_{m-1}, budget_m]`` is bounded
                for every number of open locations ``k <= m``, so layouts with fewer sites and
                large sizes are covered).
``polish``      optional Benders integer phase on the open budgets (fixed wall).
``restricted``  DOT-only run (``--restrict dot``): the master with the lattice-only candidates fixed
                closed (same template, cuts and cache), bound and incumbent per budget (T3).
``written``     written-target pricing of the best / rule / DOT layouts (8 layouts, escalations).
``oos``         out-of-sample pricing on the held-out scenarios (shared cache).
``compliance``  compliance sweep on the chosen m = 2 layout; followers r2 / selfish at the best layouts.
``hubecon``     hub-economics sensitivity on the hub-capable sites (site power cap; hub priced like a site).
``analyse``     ``RESULTS.md`` tables T1-T9 (bounds, comparison, DOT-only vs full, role table, ...),
                ``map_data.csv`` for the map figure; the m = 1 statement under both followers
                (re-plan change 8: all-candidates [floor, UB] with the locations not excluded, the
                open-sites certificate at tol 0, the M6 check; record ``m1_dual_statement``).

Modes: ``--dry-run`` (plan and sizes without any solve), ``--smoke`` (the toy instance, Threads 1,
seconds; ``--reduced N`` = the first N candidates of the real family for a short server smoke),
``--write-lanes`` (deploy-compatible lanes for ``deploy/aws/run_lanes.sh`` into
``outputs/cloud_lanes_siting/``), ``--max-rss-gb`` (abort a stage before a solve when the process
RSS exceeds it), ``--wall-<stage>`` hours.  Thread budget: ``--max-threads`` (default the
``run_lanes.sh`` rule, 1.5 per physical core) replaces the laptop cap of ``r6_o2_siting.py``.

Every invocation appends one row to ``cost.jsonl`` of ``--out-dir`` (plan 5 item 7,
``experiments/r7_cost.py``; ``R7_INSTANCE`` / ``R7_USD_PER_H`` / ``R7_BATCH``).  The search stages
of the plan (E, F, H, I, R, calibration P) and the production lane plan are in
``experiments/r7_search.py``.

Production switches (``notes/siting_production_plan.md`` section 5 items 1-4; ``auto`` = on for
the ``manhattan_dot`` family, off for the toy and ``r5_manhattan``, whose behaviour stays as
before): ``--superset off`` skips the per-bike superset LP (``L_s = 0``, valid), ``--root-merge``
raises ``L_s`` to the all-open root LP values, ``--lp-lifecycle`` builds the scenario LPs lazily,
disposes them between the m = 1 LP pass and the pricing pass and keeps the pricing-only stages
(comparison, restricted) LP-free, ``--escalate-batch`` re-prices all open scenarios of a layout
in one parallel wave, ``--evict-templates`` / ``--max-templates`` bound the resident templates.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r7_siting.py --smoke --stage all
    python3 experiments/r7_siting.py --stage setup --dry-run
    python3 experiments/r7_siting.py --stage setup --lp-workers 6 --lp-threads 2
    python3 experiments/r7_siting.py --write-lanes --vcpu 16

English only.
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import math
import os
import resource
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
from experiments import r6_o2_siting as O2  # noqa: E402
from experiments import r7_cost as RC  # noqa: E402
from experiments.r6_o2_siting import _table, load_jsonl_lenient  # noqa: E402

OUT_ROOT = os.path.join(C.OUTPUT_ROOT, "r7_siting")
LANES_ROOT = os.path.join(C.OUTPUT_ROOT, "cloud_lanes_siting")
BUDGET_UNIT = 50_000.0 + 3 * 450.0 + 2 * 400.0          # 52,150 USD (E9 convention)
TOY_UNIT = 130.0
TOY_MENU = {"S": [(1, 0), (2, 0)], "C": [(0, 1)], "SC": [(1, 1), (2, 1)]}
TOY_CANDIDATES = (("T1", 1), ("T2", 2), ("T3", 3), ("T4", 4))
TOY_LEVELS = [{"R1": ["T1", "T2"], "R2": ["T3", "T4"]}]
STAGES = ("setup", "feas", "rootlp", "comparison", "m1", "bb2", "bb3", "polish", "restricted", "written", "oos", "compliance",
          "hubecon", "analyse")
#: stages that run without the LP / pricing pools (their own thread check; production plan 5 items 1, 4)
POOL_FREE_STAGES = ("feas", "rootlp")
SOLVE_STAGES = ("setup", "comparison", "m1", "bb2", "bb3", "polish", "restricted", "written", "oos", "compliance", "hubecon")
R5_TRANSPLANT = ("M09:SC:B3:C2", "M04:SC:B2:C2|M09:SC:B4:C2", "M08:SC:B3:C2|M09:SC:B3:C2")
HUB_SETTINGS = {"site_power_cap": {"variant": {"P_kw": {"SC": 0.7, "C": 2.8}}, "spec": {}},
                "hub_priced_like_site": {"variant": {}, "spec": {"F_hub": 12.03}}}
#: expected wall minutes per stage (design 3.2, N = 60, S = 12, r7i.8xlarge; the lane plan is
#: regenerated from the measured unit times after stage setup / comparison)
EST_MIN = {"setup": 80, "feas": 150, "rootlp": 240, "comparison": 240, "m1": 210, "bb2": 600, "bb3": 240, "polish": 90, "restricted": 40,
           "written": 150, "oos": 120, "compliance": 30, "hubecon": 80, "analyse": 10}


def rss_gb() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return ru / (1024.0 ** 3) if sys.platform == "darwin" else ru / (1024.0 ** 2)


def default_max_threads() -> int:
    """The ``run_lanes.sh`` rule: 1.5 solver threads per physical core, at most nproc - 1."""
    return O2.default_max_threads()


# ---------------------------------------------------------------------------
# run context
# ---------------------------------------------------------------------------
class Run:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        root = args.out_root or (OUT_ROOT + "_smoke" if args.smoke else OUT_ROOT)
        self.dir = C.ensure_dir(os.path.abspath(args.out_dir) if args.out_dir else root)
        self.records = os.path.join(self.dir, "records.jsonl")
        self.cuts = os.path.join(self.dir, "cuts.jsonl")
        self.cache = os.path.join(self.dir, "cache")
        self.t0 = time.perf_counter()
        self.stage = "-"
        #: md5 of the instance (Ctx.instance_md5, set by Ctx): stamped on every record; records
        #: of ANOTHER instance in the same out-dir are invisible to :meth:`load` (fixer pass)
        self.instance_md5: Optional[str] = None

    def emit(self, rec: Dict[str, Any], echo: bool = False) -> None:
        rec = {"stage": self.stage, **rec}
        if self.instance_md5 is not None and "instance_md5" not in rec:
            rec["instance_md5"] = self.instance_md5
        C.append_jsonl(self.records, C.jsonable(rec))
        if echo or rec.get("kind") in ("budget_result", "acceptance", "baseline", "plan", "bnb_done", "stage_done",
                                       "written_price", "oos_result", "hubecon", "sizes", "aborted", "root_lp",
                                       "feas_result", "feas_skip_list", "root_bound_merged"):
            keys = ("kind", "target", "budget", "best_layout", "UB", "LB", "gap", "certified", "close_reason", "rule",
                    "layout_key", "V", "status", "ok", "n_candidates", "reason", "setting")
            print(json.dumps({k: C.jsonable(rec.get(k)) for k in keys if k in rec}), flush=True)
        elif rec.get("kind") in ("price", "subset_bound", "bnb_leaf"):
            print(json.dumps({k: C.jsonable(rec.get(k)) for k in ("kind", "tag", "layout_key", "atoms", "level", "status",
                                                                    "V", "lower", "bound", "pruned", "n_solves")
                              if k in rec}), flush=True)

    def load(self) -> List[Dict[str, Any]]:
        """The records of this instance: records stamped with another ``instance_md5`` (another
        candidate set, scenario set, spec, radius, ... written into the same out-dir, e.g. a
        ``--reduced`` run) are left out, so that no LB, price or incumbent of another instance
        is restored as a bound of this one (review of 2026-10-21).  Records written before the
        stamp existed carry none and are kept."""
        recs = load_jsonl_lenient(self.records)
        if self.instance_md5 is None:
            return recs
        return [r for r in recs if r.get("instance_md5") in (None, self.instance_md5)]

    def rss_guard(self, where: str) -> bool:
        lim = self.args.max_rss_gb
        if lim is None:
            return True
        r = rss_gb()
        if r > float(lim):
            self.emit({"kind": "aborted", "reason": f"RSS {r:.1f} GB > --max-rss-gb {lim} before {where}", "rss_gb": r},
                      echo=True)
            return False
        return True


# ---------------------------------------------------------------------------
# instance context
# ---------------------------------------------------------------------------
class Ctx:
    """Candidates, scenarios (in-sample and held-out), spec, evaluators, menu, budgets and the
    B&B levels of one configuration (smoke = toy; else ``manhattan_dot`` or ``r5_manhattan``)."""

    def __init__(self, run: Run) -> None:
        a = run.args
        self.run = run
        self.smoke = bool(a.smoke)
        self.unit = TOY_UNIT if self.smoke else BUDGET_UNIT
        self.budgets = [float(m) * self.unit for m in (a.budgets or ([1, 2] if self.smoke else [1, 2, 3]))]
        self.m_of = {b: int(round(b / self.unit)) for b in self.budgets}
        self.info: Dict[str, Any] = {}
        self.dropped: List[Dict[str, Any]] = []
        if self.smoke:
            self.family = "toy_siting"
            self.cands = None
            self.design = [{"seed": s, "stratum": 1 + (s % 2), "day_type": "weekday", "level": 1.0, "p": 0.5,
                            "seed_in_stratum": 0, "overrides": {}} for s in (0, 1)]
            self.held = [{"seed": 100 + s, "stratum": 1 + (s % 2), "day_type": "weekday", "level": 1.0, "p": 0.5,
                          "seed_in_stratum": 0, "overrides": {}} for s in (0, 1)]
            self.scen = [S.toy_base_instance(d["seed"], candidates=TOY_CANDIDATES) for d in self.design]
            self.scen_out = [S.toy_base_instance(d["seed"], candidates=TOY_CANDIDATES) for d in self.held]
            self.spec = S.TOY_SPEC
            self.menu = dict(TOY_MENU)
            self.levels_coarse = [dict(lv) for lv in TOY_LEVELS]
            self.S_LP = [0]
            self.ev_kw = dict(time_limit=30.0, threads=1, params={"Seed": 0, "MIPGap": 0.0}, aggregate=True)
        else:
            self.family = a.family
            if self.family == S.MANHATTAN_DOT_FAMILY:
                self.cands, self.dropped, self.info = S.dot_candidates(a.dot_csv or S.DOT_CSV_DEFAULT, merge_m=a.merge_m,
                                                                       cap=a.cap)
            else:
                self.cands = S.family_candidates(self.family)
            if a.reduced:
                self.cands = self.cands[:int(a.reduced)]
            if not self.cands:
                raise SystemExit("no candidates (DOT CSV absent and no lattice?)")
            depots = S.family_depots(self.family, self.cands)
            self.design = S.scenario_design(a.scenarios) if a.scenarios else [
                {"seed": s, "stratum": 1, "day_type": "weekday", "level": 1.25, "p": 1.0 / len(a.seeds or [0, 1, 2]),
                 "seed_in_stratum": i, "overrides": {}} for i, s in enumerate(a.seeds or [0, 1, 2])]
            self.held = S.scenario_design(a.scenarios, held_out=True) if (a.scenarios and a.held_out) else []
            pr = cm.R6_PRICING
            nb = int(S.SITING_FAMILIES[self.family]["n_bikes"])

            def build(d: Dict[str, Any]):
                base = S.make_base_instance(int(d["seed"]), self.cands, family=self.family, depots=depots, n_bikes=nb,
                                            **d.get("overrides", {}))
                rep = cm.reprice_orders(base, P=pr["P"], w=pr["w"], v=pr["v"], source=f"experiments/r7_siting.py; {pr['source']}")
                if C.demand_md5(rep) != C.demand_md5(base):
                    raise AssertionError("repricing changed the demand side")
                return rep
            self.scen = [build(d) for d in self.design]
            self.scen_out = [build(d) for d in self.held]
            self.spec = S.spec_from_instance(self.scen[0], **S.family_spec_overrides(self.family))
            self.menu = dict(S.SIZE_MENUS[self.family] if a.menu == "reduced" or self.family != S.MANHATTAN_DOT_FAMILY
                             else S.SIZE_MENUS[S.R5_MANHATTAN_FAMILY])
            if a.menu == "full" and self.family == S.MANHATTAN_DOT_FAMILY:
                self.menu = dict(S.SIZE_MENUS[S.R5_MANHATTAN_FAMILY])
            self.levels_coarse = self.regions()
            self.S_LP = S.lp_scenario_subset(self.design) if a.scenarios else list(range(len(self.design)))
            self.ev_kw = dict(time_limit=a.time_limit, time_limit_hub=a.time_limit_hub, threads=a.threads,
                              params=dict(C.ILP_PARAMS_R3), aggregate=True, keep_libraries=max(2, a.price_workers))
        pruning = {} if (self.smoke or a.approach_radius is None) else {"approach_radius_blocks": int(a.approach_radius)}
        if self.smoke and a.approach_radius is not None:
            pruning = {"approach_radius_blocks": int(a.approach_radius)}
        self.p = [float(d["p"]) for d in self.design]
        self.ev = BL.LowerLevelEvaluator(self.scen, self.spec, probabilities=self.p, cache_dir=run.cache,
                                         relaxed_targets=True, verbose=not self.smoke, reposition="all_candidates",
                                         pruning=pruning, **self.ev_kw)
        self.ev_written = self.ev.derive(relaxed_targets=False)
        self.ev_out = None
        if self.scen_out:
            self.ev_out = BL.LowerLevelEvaluator(self.scen_out, self.spec, probabilities=[float(d["p"]) for d in self.held],
                                                 cache_dir=run.cache, relaxed_targets=True, verbose=not self.smoke,
                                                 reposition="all_candidates", pruning=pruning, **self.ev_kw)
        self.candidates = self.ev.candidates
        self.ids = [c.id for c in self.candidates]
        self.enc = BD.MenuEncoding(self.ids, self.menu, S.ROLES, self.spec, roles_of=self.ev.roles_of)
        self.levels = self.levels_coarse + [{l: [l] for l in self.ids}]
        self.D = 1 if self.smoke else S.access_radius_blocks()
        self.lps: Optional[Any] = None              # list of ScenarioLP, or a lazy BD.ScenarioLPSet (R7)
        self.pool: Optional[BD.CutPool] = None
        self.L: Optional[List[float]] = None
        # R7 production switches (plan section 5 items 1-4): 'auto' = on for the manhattan_dot family only
        self.production = (not self.smoke) and self.family == S.MANHATTAN_DOT_FAMILY

        def _sw(name: str, auto: bool) -> bool:
            v = str(getattr(a, name, "auto") or "auto")
            return auto if v == "auto" else v == "on"
        self.use_superset = _sw("superset", not self.production)
        self.root_merge = _sw("root_merge", self.production)
        self.lifecycle = _sw("lp_lifecycle", self.production)
        self.escalate_batch = _sw("escalate_batch", self.production)
        # fixer pass: at escalation levels >= 2 a batch re-prices at most one wave of open cells
        ebm = str(getattr(a, "escalate_batch_max", "auto") or "auto")
        if ebm == "auto":
            self.escalate_batch_max = int(a.price_workers) if (self.production and self.escalate_batch) else None
        else:
            self.escalate_batch_max = int(ebm) if int(ebm) > 0 else None
        mt = getattr(a, "max_templates", None)
        if mt:
            for ev in (self.ev, self.ev_out):
                if ev is not None:
                    ev.max_templates = int(mt)
        # R7 re-plan change 6: skip the verification solve of check-clean MIP starts (not in any key)
        if str(getattr(a, "verify_start", "always") or "always") == "unchecked":
            for ev in (self.ev, self.ev_written, self.ev_out):
                if ev is not None:
                    ev.verify_checked_starts = False
        self._feas: Optional[Dict[str, Dict[str, Any]]] = None
        run.instance_md5 = self.instance_md5()

    def restrict_ids(self) -> List[str]:
        """Locations of the DOT-only run (``--restrict dot``, design 2.6): the candidates of class
        ``dot`` / ``both`` (a DOT row survived at the node).  Toy (smoke): the first half of the
        candidates stand in for the DOT set so that the stage is exercised."""
        if self.smoke:
            return list(self.ids[: max(1, len(self.ids) // 2)])
        return [c.id for c in self.candidates if getattr(c, "cls", "") in ("dot", "both")]

    def regions(self) -> List[Dict[str, List[str]]]:
        """B&B atoms of the real families: level 1 = coarse regions of three adjacent lattice
        cells (south -> north), level 2 = lattice cells; cells without candidates are absent."""
        cells: Dict[Tuple[int, int], List[str]] = {}
        for c in self.cands:
            cells.setdefault(S.candidate_cell(c), []).append(c.id)
        order = sorted(cells, key=lambda cc: (cc[1], cc[0]))
        cell_level = {f"cell_{cc[0]}_{cc[1]}": cells[cc] for cc in order}
        names = list(cell_level)
        region_level: Dict[str, List[str]] = {}
        for i in range(0, len(names), 3):
            region_level[f"region_{i // 3 + 1}"] = [l for n in names[i:i + 3] for l in cell_level[n]]
        return [region_level, cell_level] if len(names) > 3 else [cell_level]

    def config_md5(self) -> str:
        parts = {"family": self.family, "seeds": self.ev.seeds, "demand": self.ev.demand_md5, "p": self.p,
                 "spec": self.spec.to_dict(), "menu": {k: [list(x) for x in v] for k, v in self.menu.items()},
                 "budgets": self.budgets, "candidates": self.ids, "pruning": self.ev.pruning_signature(0),
                 "prices": [cm.pricing_cache_component(i) for i in self.scen]}
        roles_sig = self.ev.roles_signature()   # hub-capable set; None (no key) when every site is hub-capable
        if roles_sig is not None:
            parts["roles_of"] = roles_sig
        return BL._md5(parts)

    def instance_md5(self) -> str:
        """:meth:`config_md5` without the budget list: the instance a bound or a price belongs to
        (a budget_result carries its own budget, so runs with other ``--budgets`` share it)."""
        parts = {"family": self.family, "seeds": self.ev.seeds, "demand": self.ev.demand_md5, "p": self.p,
                 "spec": self.spec.to_dict(), "menu": {k: [list(x) for x in v] for k, v in self.menu.items()},
                 "candidates": self.ids, "pruning": self.ev.pruning_signature(0),
                 "prices": [cm.pricing_cache_component(i) for i in self.scen], "roles_of": self.ev.roles_signature()}
        return BL._md5(parts)

    # -- shared solver objects ------------------------------------------------------
    def superset(self) -> List[float]:
        """Per-scenario floors ``L_s`` valid for every layout: the per-bike superset LP bound
        (``--superset on``; ``off`` = 0, valid because every cost coefficient is nonnegative),
        raised to the all-open free-size root LP values (``--root-merge``, :meth:`merge_root`)."""
        if self.L is None:
            t0 = time.perf_counter()
            if self.use_superset:
                L = self.ev.superset_bound(time_limit=self.run.args.time_limit)
                self.run.emit({"kind": "superset_bound", "bound": L, "rows": self.ev.bound_rows,
                               "wall_s": time.perf_counter() - t0})
            else:
                L = [0.0] * self.ev.n_scenarios
                self.run.emit({"kind": "superset_bound", "bound": L, "rows": [], "skipped": True, "wall_s": 0.0,
                               "note": "--superset off: per-bike superset LP skipped (L_s = 0 is valid; every cost "
                                       "coefficient is nonnegative)"})
            L = [float(x) for x in L]
            if self.root_merge:
                L = self.merge_root(L)
            self.L = L
        return self.L

    # -- R7 root bound (production plan 5 item 1) ---------------------------------------
    def root_key(self) -> str:
        """Key of a root LP value: the cut-pool signature (scenarios, demand, prices, spec,
        pruning incl. the radius, library convention, hub-capable set) and the atom set (every
        candidate).  A value stored under this key is valid for scenario ``s`` of this run."""
        return BL._md5({"kind": "root_lp_all_open_free", "pool": BD.pool_signature(self.ev), "atoms": sorted(self.ids)})

    def root_values(self) -> Dict[int, Dict[str, Any]]:
        """Best known all-open free-size LP value per scenario: ``root_lp/root_s*.json`` files with
        this run's :meth:`root_key` and ``subset`` cuts of the pool whose atoms contain every
        candidate (e.g. the ``all_open_free`` timing of stage setup or an imported step-2b pool)."""
        out: Dict[int, Dict[str, Any]] = {}
        key = self.root_key()

        def put(s: int, v: float, src: str) -> None:
            if 0 <= s < self.ev.n_scenarios and math.isfinite(v) and (s not in out or v > out[s]["value"] + 1e-12):
                out[s] = {"value": float(v), "source": src}
        for path in sorted(glob.glob(os.path.join(self.run.dir, "root_lp", "root_s*.json"))):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    d = json.load(fh)
            except (OSError, ValueError):
                continue
            if d.get("key") != key:
                continue
            for s, v in enumerate(d.get("bound") or []):
                if v is not None:
                    put(int(s), float(v), os.path.relpath(path, self.run.dir))
        ids = set(self.ids)
        for c in self.cut_pool().cuts:
            if c.kind != "subset" or c.scenario is None or not c.applies_to("relaxed"):
                continue
            if ids <= {str(x) for x in (c.meta or {}).get("atoms") or []}:
                put(int(c.scenario), max(float(c.c0), float(c.L)), "cuts.jsonl")
        return out

    def merge_root(self, L: Sequence[float]) -> List[float]:
        """``L_s = max(L_s, root value)`` (valid: the all-open free-size LP with relaxed targets
        bounds the relaxed OPEX of every layout, and the written OPEX through the one-way
        import).  Root values that came from files only are added to the pool as ``subset``
        cuts (atoms = every candidate), so the B&B memo and later runs see them."""
        vals = self.root_values()
        before = [float(x) for x in L]
        out = list(before)
        for s, d in vals.items():
            out[s] = max(out[s], d["value"])
        pool = self.cut_pool()
        n_added = 0
        for s, d in sorted(vals.items()):
            if d["source"] != "cuts.jsonl":
                n_added += int(pool.add(BD.Cut(kind="subset", target="relaxed", scenario=int(s), c0=float(d["value"]),
                                               L=before[s], meta={"tag": "root", "atoms": sorted(self.ids),
                                                                  "source": d["source"], "n_atoms": len(self.ids)})))
        self.run.emit({"kind": "root_bound_merged", "L_before": before, "L": out,
                       "root": {str(s): d for s, d in sorted(vals.items())},
                       "missing": [s for s in range(self.ev.n_scenarios) if s not in vals], "n_cuts_added": n_added,
                       "superset": self.use_superset})
        return out

    # -- R7 feasibility skip list (production plan 5 item 4) ---------------------------
    def feasibility(self) -> Dict[str, Dict[str, Any]]:
        """Terminal-infeasible locations of this configuration: ``{loc: {scenario, bikes, source,
        verified}}`` from the feasibility screens (``--feas-json``, default every
        ``feas_one_site*.json`` of ``--out-dir``; ``--feas off`` disables).  A claim is used
        only with a proof for THIS evaluator: the screen's ``signature`` equals
        :func:`benders.feasibility_signature` (stage ``feas`` of the same configuration), or a
        library build of the one-site layout confirms a bike without a reachable terminal arc
        (:func:`benders.verify_terminal_infeasible`; any other file, e.g. ``r7_probe.py feas``,
        and every claim under ``--feas-verify always``).  Unconfirmed claims are dropped (and
        listed).  Recomputed only when the set of screen files (or their modification times)
        changes, e.g. after stage ``feas`` ran in the same process; record ``feas_skip_list``."""
        a = self.run.args
        if str(getattr(a, "feas", "auto")) == "off":
            self._feas = {}
            return self._feas
        paths = list(getattr(a, "feas_json", None) or []) or sorted(glob.glob(os.path.join(self.run.dir, "feas_one_site*.json")))
        stamp = tuple((p, os.path.getmtime(p) if os.path.exists(p) else None) for p in paths)
        if self._feas is not None and getattr(self, "_feas_stamp", None) == stamp:
            return self._feas
        self._feas_stamp = stamp
        self._feas = {}
        if not paths:
            return self._feas
        sig = BD.feasibility_signature(self.ev)
        always = str(getattr(a, "feas_verify", "auto")) == "always"
        ids = set(self.ids)
        claims: Dict[str, List[Tuple[int, List[str], str, bool, str]]] = {}
        dropped: List[Dict[str, Any]] = []
        t0 = time.perf_counter()
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    d = json.load(fh)
            except (OSError, ValueError) as exc:
                dropped.append({"source": p, "reason": f"unreadable: {type(exc).__name__}"})
                continue
            trusted = (d.get("signature") == sig) and not always
            for r in d.get("rows") or []:
                if not r.get("n_infeasible_bikes"):
                    continue
                try:
                    lay = BL.Layout.from_key(str(r["layout_key"]))
                    s = int(r["scenario"])
                except (KeyError, ValueError, TypeError):
                    continue
                if lay.n_open != 1 or lay.open[0][1] != "SC" or lay.open[0][0] not in ids:
                    dropped.append({"layout_key": r.get("layout_key"), "source": p, "reason": "not a one-site SC layout of this run"})
                    continue
                bikes = [str(x[0]) for x in (r.get("infeasible") or [])]
                claims.setdefault(lay.open[0][0], []).append((s, bikes, p, trusted, lay.key()))
        out: Dict[str, Dict[str, Any]] = {}
        n_builds = 0
        for loc in sorted(claims):
            proof = None
            for s, bikes, p, trusted, lkey in sorted(claims[loc], key=lambda c: (not c[3], c[0])):
                if not 0 <= s < self.ev.n_scenarios:
                    continue
                if trusted:
                    proof = {"scenario": s, "bikes": bikes, "source": p, "verified": False, "trusted": True}
                    break
                n_builds += 1
                inf = BD.verify_terminal_infeasible(self.ev, BL.Layout.from_key(lkey), s)
                if inf:
                    proof = {"scenario": s, "bikes": inf, "source": p, "verified": True, "trusted": False}
                    break
            if proof is None:
                dropped.append({"location": loc, "reason": "no claim confirmed by a library build of this configuration"})
            else:
                out[loc] = proof
        self._feas = out
        self.run.emit({"kind": "feas_skip_list", "signature": sig, "sources": paths, "locations": sorted(out),
                       "n_locations": len(out), "proofs": out, "dropped": dropped[:200], "n_dropped": len(dropped),
                       "n_verification_builds": n_builds, "wall_s": time.perf_counter() - t0})
        return out

    def apply_feasibility(self, cert: BD.SitingCertifier) -> int:
        """Mark the one-site layouts of every proven terminal-infeasible location (and add the
        terminal rows) on ``cert``; returns the number of layouts newly marked."""
        n = 0
        for loc, pr in self.feasibility().items():
            src = f"feasibility screen {os.path.basename(str(pr['source']))}" + (" (re-proved)" if pr.get("verified") else "")
            n += cert.mark_terminal_infeasible(loc, int(pr["scenario"]), role="SC", bikes=pr.get("bikes"), source=src)
        return n

    def _lp_built(self, s: int, lp: BD.ScenarioLP) -> None:
        self.run.emit({"kind": "lp_built", "scenario": int(s), "size": lp.size, "build_s": lp.build_s, "rss_gb": rss_gb(),
                       "templates_resident": self.ev.resident_templates()})

    def scenario_lps(self) -> Any:
        """The scenario LPs: an eager list (as before), or with ``--lp-lifecycle`` a lazy
        :class:`benders.ScenarioLPSet` (an LP is built on first use; ``--evict-templates`` evicts
        its template right after the build)."""
        a = self.run.args
        if self.lps is None:
            t0 = time.perf_counter()
            if self.lifecycle:
                self.lps = BD.ScenarioLPSet(self.ev, threads=a.lp_threads, method=a.lp_method, relaxed=True,
                                            evict_templates=bool(getattr(a, "evict_templates", False)), on_build=self._lp_built)
                self.run.emit({"kind": "lp_sizes", "lazy": True, "sizes": [], "lp_method": a.lp_method,
                               "lp_threads": a.lp_threads, "lp_workers": a.lp_workers, "build_s": 0.0, "rss_gb": rss_gb(),
                               "evict_templates": self.lps.evict_templates})
                return self.lps
            self.lps = [BD.ScenarioLP(self.ev, s, threads=a.lp_threads, method=a.lp_method, relaxed=True)
                        for s in range(self.ev.n_scenarios)]
            self.run.emit({"kind": "lp_sizes", "sizes": [lp.size for lp in self.lps], "lp_method": a.lp_method,
                           "lp_threads": a.lp_threads, "lp_workers": a.lp_workers, "build_s": time.perf_counter() - t0,
                           "rss_gb": rss_gb()})
        return self.lps

    def cut_pool(self) -> BD.CutPool:
        if self.pool is None:
            self.pool = BD.CutPool(self.run.cuts, BD.pool_signature(self.ev))
            self.run.emit({"kind": "pool_loaded", "n_cuts": len(self.pool.cuts), "by_kind": self.pool.counts(),
                           "skipped_lines": self.pool.n_skipped})
        return self.pool

    def certifier(self, target: str = "relaxed", budgets: Optional[Sequence[float]] = None, wall_h: float = 1.0,
                  label: str = "", pricing_only: bool = False, use_cover: bool = True) -> BD.SitingCertifier:
        """A certifier on the shared LPs, pool and floors, restored from the records, with the
        feasibility skip list applied.  ``pricing_only`` (comparison, restricted): with
        ``--lp-lifecycle`` its pricings take the master's cut envelope as prior bounds and never
        build a scenario LP (``cert.pricing_only``).  ``use_cover=False`` (R7 re-plan, the list
        pricing of ``r7_search.py --cover-rows off``): no cover rows in the master, so no
        all-candidates template is built at start-up (12 templates, about 0.4 h at N = 59); the
        master bound is then weaker (valid), and the prior LBs are restored as before."""
        a = self.run.args
        ev = self.ev if target == "relaxed" else self.ev_written
        wall = C.WallBudget(float(wall_h) * 3600.0, margin_s=60.0, min_solve_s=30.0)
        ev.wall = wall
        cert = BD.SitingCertifier(ev, list(budgets or self.budgets), self.menu, S.ROLES, s_needs_charge=True,
                                  L=self.superset(), lps=self.scenario_lps(), pool=self.cut_pool(),
                                  tol_rel=a.tol_rel, tol_abs=a.tol_abs, master_threads=a.master_threads, wall=wall,
                                  on_record=self.run.emit, label=label or target, lp_workers=a.lp_workers,
                                  wall_margin_s=120.0, max_escalations=a.max_escalations, price_workers=a.price_workers,
                                  roles_of=self.ev.roles_of, escalate_batch=self.escalate_batch,
                                  escalate_batch_max=self.escalate_batch_max,
                                  escalate_factor=float(getattr(a, "escalate_factor", 3.0)),
                                  escalate_cap_s=float(getattr(a, "escalate_cap_s", 1800.0)),
                                  **({} if use_cover else {"use_cover": False}))
        cert.pricing_only = bool(pricing_only and self.lifecycle)
        cert.restore(self.run.load())
        self.apply_feasibility(cert)
        return cert

    def close(self) -> None:
        if isinstance(self.lps, BD.ScenarioLPSet):
            self.lps.dispose()
        else:
            for lp in self.lps or []:
                lp.dispose()


# ---------------------------------------------------------------------------
# record helpers
# ---------------------------------------------------------------------------
def last_results(records: Sequence[Dict[str, Any]], target: str = "relaxed") -> Dict[float, Dict[str, Any]]:
    out: Dict[float, Dict[str, Any]] = {}
    for r in records:
        if r.get("kind") == "budget_result" and r.get("target") == target and r.get("budget") is not None:
            out[float(r["budget"])] = r
    return out


def priced_layouts(records: Sequence[Dict[str, Any]], target: str = "relaxed",
                   tiers: Sequence[str] = ("all_candidates",)) -> Dict[str, Dict[str, Any]]:
    """PRICED layouts with a value: the last all-candidates ``price`` record per layout (the old
    behaviour); with ``'open_sites'`` in ``tiers`` (R7 re-plan change 7) also the ``price_open``
    records (per layout the lowest ``V`` of either tier; ``tier`` says which).  An open-sites
    value is a feasible value of the all-candidates follower too (sub-library, K1): a valid
    upper bound, never a lower bound."""
    out: Dict[str, Dict[str, Any]] = {}
    for r in records:
        if r.get("kind") == "price" and r.get("target") == target and r.get("layout_key") and r.get("status") == "PRICED" \
                and r.get("V") is not None and r.get("tier", "all_candidates") == "all_candidates" \
                and "all_candidates" in tiers:
            out[r["layout_key"]] = r
    if "open_sites" in tiers:
        for key, r in open_priced(records, target).items():
            if key not in out or float(r["V"]) < float(out[key]["V"]) - 1e-9:
                out[key] = r
    return out


def open_priced(records: Sequence[Dict[str, Any]], target: str = "relaxed") -> Dict[str, Dict[str, Any]]:
    """Per layout the ``price_open`` record (open-sites pricing, change 1 / 2) with the lowest
    ``V`` among the PRICED ones."""
    out: Dict[str, Dict[str, Any]] = {}
    for r in records:
        if r.get("kind") == "price_open" and r.get("target") == target and r.get("layout_key") \
                and r.get("status") == "PRICED" and r.get("V") is not None:
            k = r["layout_key"]
            if k not in out or float(r["V"]) <= float(out[k]["V"]):
                out[k] = dict(r, tier="open_sites")
    return out


def open_records(records: Sequence[Dict[str, Any]], target: str = "relaxed") -> Dict[str, Dict[str, Any]]:
    """Per layout the last ``price_open`` record whatever its status (INFEASIBLE included), the
    lowest-``V`` PRICED one when there is one."""
    out: Dict[str, Dict[str, Any]] = {}
    for r in records:
        if r.get("kind") == "price_open" and r.get("target") == target and r.get("layout_key") \
                and r.get("status") != "SKIPPED_BUDGET":
            out[r["layout_key"]] = r
    out.update(open_priced(records, target))
    return out


def tiers_of(args: argparse.Namespace) -> Tuple[str, ...]:
    """The value tiers a stage reads: the old all-candidates values only, or both tiers with
    ``--price-tier open_sites`` (re-plan change 7)."""
    return ("all_candidates", "open_sites") if getattr(args, "price_tier", "all_candidates") == "open_sites" \
        else ("all_candidates",)


def many_sites_limit(args: argparse.Namespace, lay: Optional[BL.Layout]) -> Optional[float]:
    """``--time-limit-many-sites K:SECONDS``: the per-cell limit of a layout with >= K open sites
    (re-plan section 3: 900 s for the DOT all-pilot layout), else ``None`` (the evaluator's)."""
    tok = getattr(args, "time_limit_many_sites", None)
    if not tok or lay is None:
        return None
    k, _, sec = str(tok).partition(":")
    if not sec:
        raise SystemExit(f"--time-limit-many-sites: expected K:SECONDS, got {tok!r}")
    return float(sec) if lay.n_open >= int(k) else None


def all_candidates_lower(cert: BD.SitingCertifier, lay: BL.Layout) -> Optional[float]:
    """The best all-candidates lower bound on ``V(lay)`` the certifier holds (valid for both
    followers): ``max(master envelope, v_LP if the layout's LPs are known, lower of an
    all-candidates pricing)``.  Never an open-sites ILP bound (K2.7).  ``None`` when unknown."""
    lo = -BL.INF
    key = lay.key()
    if cert.enc.contains(lay):                  # outside the menu the master says nothing (envelope inf)
        lo = max(lo, float(cert.master.envelope(lay)))
    if key in cert.lp_memo and all(r.c0 is not None for r in cert.lp_memo[key]):
        lo = max(lo, float(cert.v_lp(lay)))
    pr = cert.priced.get(key)
    if pr is not None and pr.status != "SKIPPED_BUDGET":
        lo = max(lo, float(pr.lower))
    return None if lo == -BL.INF else lo


def cover_kw(a: argparse.Namespace) -> Dict[str, Any]:
    """``--cover-rows off`` (review of the r2 lanes): ``{"use_cover": False}`` for
    :meth:`Ctx.certifier`, else ``{}`` (the old call)."""
    return {"use_cover": False} if getattr(a, "cover_rows", "on") == "off" else {}


def m1_lower_table(ctx: "Ctx", records: Sequence[Dict[str, Any]], b: Optional[float] = None,
                   target: str = "relaxed") -> Dict[str, Dict[str, Any]]:
    """R7 re-plan changes 2 / 8: per admissible layout of budget ``b`` (default m = 1; open sets
    of at most m sites, as the acceptance check) the best all-candidates lower bound known from
    the records -- ``v_LP`` (``lp_layout`` / ``lp_location`` / ``lp_pruned``), the cut envelope of
    an ``lp_pruned`` record, the ``lower`` of an all-candidates ``price`` record -- and ``inf``
    for a layout proven infeasible ONLY by a terminal-infeasible location of the skip list or an
    all-candidates ``price`` record with status INFEASIBLE.  An open-sites (``price_open``)
    INFEASIBLE says nothing about the all-candidates follower (the open-sites library is the
    smaller one): it sets ``infeasible_open`` only and never ``lower`` / ``infeasible``.  Every
    value is a valid lower bound for BOTH followers (all-candidates V <= open-sites V).  ``lower`` is ``None``
    when nothing is known (the certificate then lists the layout as unresolved).
    ``infeasible_open``: INFEASIBLE under the open-sites follower (a ``price_open`` record, or
    infeasible for both); it never sets ``lower``."""
    b = min(ctx.budgets) if b is None else float(b)
    lays = BL.enumerate_layouts(ctx.candidates, ctx.enc.options, b, ctx.spec, range(1, ctx.m_of.get(b, 1) + 1),
                                s_needs_charge=True)
    fsl = next((r for r in reversed(records) if r.get("kind") == "feas_skip_list"), None)
    infeasible_locs = set((fsl or {}).get("locations") or [])
    out: Dict[str, Dict[str, Any]] = {l.key(): {"layout": l, "lower": None, "source": None, "infeasible": False,
                                                 "infeasible_open": False} for l in lays}

    def put(key: Optional[str], v: Any, src: str) -> None:
        d = out.get(str(key)) if key else None
        if d is None or v is None:
            return
        v = float(v)
        if not math.isfinite(v) and v < 0:
            return
        if d["lower"] is None or v > d["lower"]:
            d["lower"], d["source"] = v, src
    for r in records:
        if r.get("target", target) != target:
            continue
        k = r.get("kind")
        if k in ("lp_layout", "lp_location"):
            put(r.get("layout_key"), r.get("v_LP"), "v_LP")
        elif k == "lp_pruned":
            put(r.get("layout_key"), r.get("v_LP") if r.get("v_LP") is not None else r.get("envelope"),
                "v_LP" if r.get("v_LP") is not None else "envelope")
        elif k == "price" and r.get("tier", "all_candidates") == "all_candidates" and r.get("status") != "SKIPPED_BUDGET":
            if r.get("status") == "INFEASIBLE":
                d = out.get(str(r.get("layout_key")))
                if d is not None:
                    d["infeasible"] = True
            else:
                put(r.get("layout_key"), r.get("lower"), "pricing")
        elif k == "price_open" and r.get("status") == "INFEASIBLE":
            d = out.get(str(r.get("layout_key")))
            if d is not None:                   # open-sites follower only: never an all-candidates claim
                d["infeasible_open"] = True
    for key, d in out.items():
        if d["infeasible"] or (d["layout"].n_open == 1 and d["layout"].open[0][0] in infeasible_locs):
            d["infeasible"] = True
            d["lower"], d["source"] = BL.INF, "infeasible"
        d.setdefault("infeasible_open", False)
        d["infeasible_open"] = bool(d["infeasible_open"] or d["infeasible"])
    return out


def best_layout_at(records: Sequence[Dict[str, Any]], budget: float, spec: S.SitingSpec, target: str = "relaxed",
                   pred=None, tiers: Sequence[str] = ("all_candidates",)) -> Optional[Tuple[str, float]]:
    """Best priced menu layout within ``budget`` (``pred`` filters layouts; ``tiers``: see
    :func:`priced_layouts`)."""
    best = None
    for key, r in priced_layouts(records, target, tiers).items():
        lay = BL.Layout.from_key(key)
        if lay.investment(spec) > budget + 1e-6 or (pred is not None and not pred(lay)):
            continue
        if best is None or r["V"] < best[1] - 1e-9:
            best = (key, float(r["V"]))
    return best


def stage_done(records: Sequence[Dict[str, Any]], stage: str, md5: str) -> bool:
    return any(r.get("kind") == "stage_done" and r.get("stage") == stage and r.get("config_md5") == md5 for r in records)


def rule_layouts(ctx: Ctx) -> Dict[Tuple[str, float], Optional[BL.Layout]]:
    ev = ctx.ev
    sc = ctx.menu.get("SC") or [(1, 1)]
    capB, capC = max(b for b, _c in sc), max(c for _b, c in sc)
    base = min(sc, key=lambda bc: (bc[0] + bc[1], bc))
    w = {"CSCD": BL.demand_weights(ev.candidates, ev.scenarios, ctx.D, ev.p),
         "CSTC": BL.access_weights(ev.candidates, ev.scenarios, ev.p), "CSAV": None}
    out: Dict[Tuple[str, float], Optional[BL.Layout]] = {}
    for b in ctx.budgets:
        for rule in BL.RULES:
            out[(rule, b)] = BL.rule_layout(rule, ev.candidates, b, ev.spec, w[rule], role="SC", base_size=base,
                                            max_B=capB, max_C=capC)
    return out


def transplanted(ctx: Ctx) -> List[Tuple[str, BL.Layout]]:
    """The 15-candidate optima moved to the merged candidates through ``lattice_id``."""
    mp = {c.lattice_id: c.id for c in ctx.candidates if c.lattice_id}
    out = []
    for key in R5_TRANSPLANT:
        try:
            lay = BL.Layout.from_key(key)
        except ValueError:
            continue
        items = []
        ok = True
        for l, r, B, C in lay.open:
            if l not in mp:
                ok = False
                break
            items.append((mp[l], r, B, C))
        if ok:
            out.append((key, BL.Layout.of(items)))
    return out


def _limits_ok(rows: Sequence[Dict[str, Any]], time_limit: Optional[float]) -> bool:
    """Every row final (OPTIMAL / infeasible) or solved with at least ``time_limit``."""
    return time_limit is None or all(float(r.get("time_limit") or 0.0) >= float(time_limit) - 1e-9
                                     or r.get("status") in ("OPTIMAL", "INFEASIBLE_TERMINAL", "INFEASIBLE_ILP")
                                     for r in rows)


def price_named(run: Run, cert: BD.SitingCertifier, name: str, lay: Optional[BL.Layout], b: float,
                tag: str = "baseline", time_limit: Optional[float] = None, tier: str = "all_candidates") -> Dict[str, Any]:
    """Exact (full) price of a comparison layout on the all-candidates tier (design 2.5).
    ``time_limit`` (R7 comparison filter, production plan 5 item 5): the per-row ILP limit (e.g.
    600 s for the m = 2 rows); an earlier pricing at a shorter limit is then re-priced (final
    cached rows are reused, TIME_LIMIT rows re-solved warm).  ``None`` = unchanged behaviour.

    R7 re-plan change 7: ``tier='open_sites'`` prices the row on the open-sites library (full
    pricing only, K2.7): ``V`` is then an upper bound on the row's all-candidates value
    (``UB_rule``), its scenario bounds are kept as ``lb_open`` (open-sites follower only) and
    ``LB_rule`` is the all-candidates lower bound of the certifier (envelope / LP / an
    all-candidates pricing, :func:`all_candidates_lower`), so that the regret interval is
    ``[LB_rule - UB*_m, UB_rule - LB*_m]``."""
    rec: Dict[str, Any] = {"kind": "baseline", "target": cert.target, "budget": b, "rule": name,
                           "layout_key": None if lay is None else lay.key()}
    if time_limit is not None:
        rec["time_limit"] = float(time_limit)
    if lay is None:
        rec.update(status="NONE", V=None)
    else:
        bad = [l for l, r, _B, _C in lay.open if r not in cert.ev.roles_of.get(l, ())]
        if bad:
            rec.update(status="NOT_ALLOWED", V=None, note=f"role not allowed at {bad}")
        elif tier == "open_sites":
            prev = cert.priced_open.get(lay.key())
            reuse = prev is not None and prev.status in ("PRICED", "INFEASIBLE") and _limits_ok(prev.rows, time_limit)
            res = prev if reuse else cert.price(lay, full=True, tag=f"{tag}:{name}", tier="open_sites", time_limit=time_limit)
            rec.update(status=res.status, V=res.V, opex=res.ub, lb_open=res.lb, setup=res.setup,
                       lower_open=res.setup + sum(p * x for p, x in zip(cert.p, res.lb)),
                       LB_rule=all_candidates_lower(cert, lay), investment=lay.investment(cert.ev.spec),
                       in_menu=cert.enc.contains(lay), within_budget=lay.investment(cert.ev.spec) <= b + 1e-6,
                       served_share=res.served_share, tier="open_sites", resumed=bool(reuse),
                       note="V = open_sites value (UB on the all-candidates value); LB_rule = all-candidates lower "
                            "bound (envelope / LP / all-candidates pricing); lb_open holds for the open_sites follower only")
        else:
            prev = cert.priced.get(lay.key())
            reuse = prev is not None and prev.status == "PRICED" and (
                time_limit is None or all(float(r.get("time_limit") or 0.0) >= float(time_limit) - 1e-9
                                          or r.get("status") == "OPTIMAL" for r in prev.rows))
            res = prev if reuse else \
                cert.price(lay, full=True, tag=f"{tag}:{name}", lp=not getattr(cert, "pricing_only", False),
                           time_limit=time_limit)
            rec.update(status=res.status, V=res.V, opex=res.ub, lb=res.lb, setup=res.setup,
                       investment=lay.investment(cert.ev.spec), in_menu=cert.enc.contains(lay),
                       within_budget=lay.investment(cert.ev.spec) <= b + 1e-6, served_share=res.served_share,
                       tier="all_candidates")
    run.emit(rec)
    return rec


def warm_layouts(ctx: Ctx, records: Sequence[Dict[str, Any]], rules) -> List[BL.Layout]:
    out = [l for l in rules.values() if l is not None]
    for key in priced_layouts(records):
        out.append(BL.Layout.from_key(key))
    pilot = BL.dot_pilot_layout(ctx.candidates)
    if pilot is not None and pilot.investment(ctx.spec) <= max(ctx.budgets) + 1e-6:
        out.append(pilot)
    seen = set()
    uniq = []
    for l in out:
        if l.key() not in seen and ctx.enc.contains(l):
            seen.add(l.key())
            uniq.append(l)
    return uniq


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------
def stage_setup(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    recs = run.load()
    plan: Dict[str, Any] = {"kind": "plan", "family": ctx.family, "n_candidates": len(ctx.ids), "candidates": ctx.ids,
                            "budgets": ctx.budgets, "menu": ctx.menu, "n_options": len(ctx.enc.options), "n_w": ctx.enc.n,
                            "n_hub_capable": sum(1 for c in ctx.candidates if "C" in ctx.ev.roles_of[c.id]),
                            "scenarios": [{k: v for k, v in d.items() if k != "overrides"} for d in ctx.design],
                            "held_out": [{k: v for k, v in d.items() if k != "overrides"} for d in ctx.held],
                            "S_LP": ctx.S_LP, "p": ctx.p, "demand_md5": ctx.ev.demand_md5,
                            "demand_md5_held_out": None if ctx.ev_out is None else ctx.ev_out.demand_md5,
                            "n_orders": [len(i.orders) for i in ctx.scen], "spec": ctx.spec.to_dict(),
                            "pruning": ctx.ev.pruning_signature(0), "levels": [len(lv) for lv in ctx.levels],
                            "atoms": ctx.levels[:-1], "config_md5": ctx.config_md5(), "dot_info": ctx.info,
                            "approach_radius": a.approach_radius, "max_threads": a.max_threads,
                            "threads": {"ilp": a.threads, "lp": a.lp_threads, "lp_workers": a.lp_workers,
                                        "price_workers": a.price_workers, "master": a.master_threads}}
    cands = ctx.cands if ctx.cands is not None else list(ctx.candidates)      # toy: the evaluator's candidates
    S.write_candidate_tables(cands, ctx.dropped, run.dir)
    plan["candidate_classes"] = {cls: sum(1 for c in cands if c.cls == cls) for cls in ("dot", "lattice", "both")}
    plan["snap_m_max"] = max([c.snap_m for c in cands], default=0.0)
    # demand hash is layout-independent (one layout instance per scenario)
    probe = BL.Layout.of([(ctx.ids[0],) + ctx.enc.options[0]]) if ctx.enc.options[0][0] in ctx.ev.roles_of[ctx.ids[0]] else None
    if probe is not None:
        for s in range(ctx.ev.n_scenarios):
            li = S.layout_instance(ctx.scen[s], probe, ctx.spec)
            if C.demand_md5(li, include_facilities=False) != ctx.ev.demand_md5[s]:
                raise AssertionError(f"demand_md5 of scenario {s} depends on the layout")
    plan["demand_layout_independent"] = True
    plan["weights_sum"] = sum(ctx.p)
    if ctx.cands is not None:
        access = BL.access_sets(ctx.candidates, ctx.scen, ctx.D)
        plan["access"] = {"D_blocks": ctx.D, "n_zones": len(access), "empty_zones": sorted(z for z, ls in access.items() if not ls)}
    run.emit(plan, echo=True)
    if a.dry_run:
        return plan
    if not run.rss_guard("setup templates"):
        return plan
    sizes: Dict[str, Any] = {"kind": "sizes", "templates": [], "rss_gb_start": rss_gb()}
    for s in range(ctx.ev.n_scenarios):
        t0 = time.perf_counter()
        inst, lib = ctx.ev.template(s)
        sizes["templates"].append({"scenario": s, "n_arcs": len(lib), "n_services": len(inst.services),
                                   "n_facilities": len(inst.facilities), "build_s": time.perf_counter() - t0,
                                   "infeasible_bikes": [str(b) for b in lib.infeasible_bikes]})
    L = ctx.superset()
    lps = ctx.scenario_lps()
    sizes["lp"] = [lp.size for lp in lps]
    sizes["z_columns"] = [len(lp.sub.z) for lp in lps]
    sizes["superset"] = L
    sizes["rss_gb_after_lps"] = rss_gb()
    # the four LP timings of the size dry run (design 5.1 step 5 / 5.3)
    cert = ctx.certifier("relaxed", wall_h=a.wall_setup, label="setup")
    cert.covers = []
    timings: Dict[str, Any] = {}
    rep = cert.rep_option()
    # Representative FEASIBLE fixed layouts (probe review of 2026-10-21): a layout on which a bike
    # has no reachable terminal arc gives an LP dominated by artificial columns, whose time is not
    # a fixed-layout time.  One site: the candidate of lattice cell M09 (the 15-candidate optimum),
    # else the candidates by restaurants; two sites: the transplanted M08|M09 / M04|M09 optima
    # (through lattice_id), else the chosen site plus the next candidates by restaurants.  A layout
    # with infeasible bikes in ANY scenario the timings solve (cert.lp_at solves all S; adversarial
    # review of 2026-10-21: S_LP[0] alone is the lowest-demand weekday scenario) is skipped
    # (recorded with the first failing scenario), at most 8 tries per kind.  The check builds
    # layout libraries only (no LP); the scenarios are checked in S_LP order first.
    s_all = list(range(ctx.ev.n_scenarios))
    s_chk = [int(s) for s in ctx.S_LP] + [s for s in s_all if s not in set(int(x) for x in ctx.S_LP)]
    by_rest = sorted(ctx.candidates, key=lambda c: (-int(getattr(c, "n_restaurants", 0) or 0), ctx.ids.index(c.id)))
    lid = {c.id: (getattr(c, "lattice_id", None) or (c.id if ctx.family == S.R5_MANHATTAN_FAMILY else None))
           for c in ctx.candidates}

    def rep_ok(l: str) -> bool:
        return bool(rep) and rep[0] in ctx.ev.roles_of.get(l, ())

    def pick(seq: Sequence[BL.Layout]) -> Tuple[Optional[BL.Layout], List[str], List[Dict[str, Any]]]:
        skipped: List[Dict[str, Any]] = []
        seen = set()
        for lay in seq:
            if lay is None or lay.key() in seen or not ctx.enc.contains(lay):
                continue
            seen.add(lay.key())
            if len(skipped) >= 8:
                break
            inf, bad_s = [], None
            for s in s_chk:
                _inst, lib = ctx.ev.layout_pair(lay, s)
                inf = [str(b) for b in lib.infeasible_bikes]
                if inf:
                    bad_s = s
                    break
            if not inf:
                return lay, inf, skipped
            skipped.append({"layout": lay.key(), "infeasible_bikes": inf, "scenario": bad_s})
        return None, [], skipped

    one_seq = [BL.Layout.of([(c.id,) + rep]) for c in
               sorted(by_rest, key=lambda c: 0 if lid.get(c.id) == "M09" else 1) if rep_ok(c.id)]
    one, one_inf, one_skip = pick(one_seq)
    tp = dict(transplanted(ctx))
    if ctx.family == S.R5_MANHATTAN_FAMILY:          # lattice ids are the candidate ids themselves
        for key in R5_TRANSPLANT:
            lay = BL.Layout.from_key(key)
            if key not in tp and all(l in lid for l in lay.locations()):
                tp[key] = lay
    two_seq: List[BL.Layout] = [tp[k] for k in ("M08:SC:B3:C2|M09:SC:B3:C2", "M04:SC:B2:C2|M09:SC:B4:C2") if k in tp]
    if one is not None:
        l1 = one.open[0][0]
        two_seq += [BL.Layout.of([(l1,) + rep, (c.id,) + rep]) for c in by_rest if c.id != l1 and rep_ok(c.id)]
    two, two_inf, two_skip = pick(two_seq)
    for name, lay, inf, skip in (("one_site", one, one_inf, one_skip), ("two_site", two, two_inf, two_skip)):
        if lay is None:
            timings[name] = {"layout": None, "skipped_infeasible": skip, "check_scenarios": s_chk,
                             "note": "no representative layout feasible in every scenario found"}
            continue
        t0 = time.perf_counter()
        rs = cert.lp_at(lay)
        timings[name] = {"layout": lay.key(), "wall_s": time.perf_counter() - t0, "runtime_s": [r.runtime_s for r in rs],
                         "v_LP": cert.v_lp(lay), "artificial": [r.artificial for r in rs],
                         "lattice_ids": [lid.get(l) for l in lay.locations()], "check_scenarios": s_chk,
                         "infeasible_bikes": inf, "skipped_infeasible": skip}
    cell = max(ctx.levels[-2].items(), key=lambda kv: len(kv[1]))[1] if len(ctx.levels) >= 2 else ctx.ids
    # R7_SIZE_ALL_OPEN_MAX_SCEN (probe only, 2026-10-21): the all-open free-size LP took 37-79 min per
    # scenario at N = 40 (no time limit), so the size probe may time it on the first k LP scenarios only
    # (one parallel wave); unset = every LP scenario, as before.
    k_all = int(os.environ.get("R7_SIZE_ALL_OPEN_MAX_SCEN", "0") or 0)
    for name, atoms in (("one_cell_free", cell), ("all_open_free", ctx.ids)):
        scen = list(ctx.S_LP)[:k_all] if (name == "all_open_free" and k_all > 0) else list(ctx.S_LP)
        t0 = time.perf_counter()
        lba = cert.subset_bound(atoms, scen, tag="size")
        timings[name] = {"n_locations": len(atoms), "wall_s": time.perf_counter() - t0, "lba": lba,
                         "scenarios": scen}
    sizes["timings"] = timings
    # against the per-bike superset LP itself (not the merged floors; None when --superset off)
    L_sup = ctx.ev._bound if ctx.use_superset else None
    sizes["all_open_equals_superset_max_abs"] = max(abs(x - l) for x, l in zip(timings["all_open_free"]["lba"], L_sup)) \
        if (L_sup is not None and ctx.S_LP == list(range(ctx.ev.n_scenarios))) else None
    sizes["rss_gb_end"] = rss_gb()
    sizes["counters"] = dict(cert.counters)
    run.emit(sizes, echo=True)
    cert.close()
    run.emit({"kind": "stage_done", "stage": "setup", "config_md5": ctx.config_md5()})
    return sizes


def _write_json_atomic(path: str, obj: Any) -> None:
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(C.jsonable(obj), fh, indent=1)
    os.replace(tmp, path)


def sc_screen_option(ctx: Ctx) -> Tuple[str, int, int]:
    """Size option of the one-site screen: the menu's SC option nearest to B3:C2 (terminal
    feasibility does not depend on the sizes, ``benders.SitingCertifier.mark_terminal_infeasible``)."""
    opts = [o for o in ctx.enc.options if o[0] == "SC"]
    if not opts:
        raise SystemExit("the menu has no SC option: no one-site layout to screen")
    return min(opts, key=lambda o: (abs(o[1] - 3) + abs(o[2] - 2), -o[1], -o[2]))


def stage_feas(run: Run, ctx: Ctx) -> Dict[str, Any]:
    """Stage A of the production plan: terminal reachability of every one-site layout
    ``<loc>:SC`` on ``--feas-scenarios`` (default all), library builds only (no solve).  Each
    scenario's template is built, every location's layout library derived from it, and the
    template evicted afterwards (production plan 5 item 2).  Writes
    ``feas_one_site_<tag>.json`` (the rows of ``r7_probe.py feas`` plus ``signature`` =
    :func:`benders.feasibility_signature`, seeds, demand hashes); skipped when that file exists
    with the same signature and scenarios (``--redo`` reruns).  Several processes with disjoint
    ``--feas-scenarios`` write disjoint files; the later stages read them all."""
    a = run.args
    S_n = ctx.ev.n_scenarios
    scen = sorted({int(s) for s in a.feas_scenarios}) if a.feas_scenarios else list(range(S_n))
    bad = [s for s in scen if not 0 <= s < S_n]
    if bad:
        raise SystemExit(f"--feas-scenarios {bad} out of range 0..{S_n - 1}")
    locs = [l for l in ctx.ids if "SC" in ctx.ev.roles_of[l]]
    opt = sc_screen_option(ctx)
    tag = "all" if scen == list(range(S_n)) else "s" + "_".join(str(s) for s in scen)
    path = os.path.join(run.dir, f"feas_one_site_{tag}.json")
    sig = BD.feasibility_signature(ctx.ev)
    plan = {"kind": "feas_plan", "scenarios": scen, "n_locations": len(locs), "n_layouts": len(locs) * len(scen),
            "option": list(opt), "path": os.path.relpath(path, run.dir), "signature": sig}
    run.emit(plan, echo=True)
    if a.dry_run:
        return plan
    if not a.redo and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
        except (OSError, ValueError):
            old = {}
        if old.get("signature") == sig and old.get("scenarios") == scen:
            run.emit({"kind": "stage_skipped", "stage": "feas", "reason": f"{os.path.basename(path)} exists (same signature)"},
                     echo=True)
            return {k: old.get(k) for k in ("scenarios", "n_layouts", "infeasible_locations")}
    if not run.rss_guard("feas"):
        return plan
    cand = {c.id: c for c in ctx.candidates}
    rows: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for s in scen:
        t1 = time.perf_counter()
        ctx.ev.template(s)
        t_tpl = time.perf_counter() - t1
        n_inf = 0
        for l in locs:
            lay = BL.Layout.of([(l,) + tuple(opt)])
            inst, lib = ctx.ev.layout_pair(lay, s)
            inf = [str(b) for b in lib.infeasible_bikes]
            bikes = {str(b.id): b for b in inst.bikes}
            n_inf += int(bool(inf))
            rows.append({"layout_key": lay.key(), "location": l, "lattice_id": getattr(cand[l], "lattice_id", None),
                         "scenario": s, "seed": ctx.ev.seeds[s], "n_arcs": len(lib), "n_infeasible_bikes": len(inf),
                         "infeasible": [[i, str(bikes[i].v0), int(bikes[i].q0)] for i in inf]})
        ctx.ev.evict_template(s)                # this stage never needs it again (production plan 5 item 2)
        run.emit({"kind": "feas_scenario", "scenario": s, "n_infeasible_layouts": n_inf, "template_s": t_tpl,
                  "wall_s": time.perf_counter() - t1, "rss_gb": rss_gb()})
    inf_rows = [r for r in rows if r["n_infeasible_bikes"]]
    res = {"kind": "feas_one_site", "signature": sig, "config_md5": ctx.config_md5(), "family": ctx.family,
           "seeds": ctx.ev.seeds, "demand_md5": ctx.ev.demand_md5, "scenarios": scen, "option": list(opt),
           "approach_radius": a.approach_radius, "n_layouts": len(rows), "n_infeasible_layout_scenarios": len(inf_rows),
           "infeasible_layouts": sorted({r["layout_key"] for r in inf_rows}),
           "infeasible_locations": sorted({r["location"] for r in inf_rows}), "rows": rows,
           "wall_s": time.perf_counter() - t0, "rss_gb_peak": rss_gb()}
    _write_json_atomic(path, res)
    summary = {k: v for k, v in res.items() if k != "rows"}
    run.emit({**summary, "kind": "feas_result", "path": os.path.relpath(path, run.dir)}, echo=True)
    run.emit({"kind": "stage_done", "stage": "feas", "config_md5": ctx.config_md5(), "scenarios": scen})
    return summary


def root_order(design: Sequence[Dict[str, Any]]) -> List[int]:
    """Scenarios longest first for the all-open root LPs (production plan 2.1 stage D): demand
    level descending, weekday before weekend, then the scenario index."""
    return sorted(range(len(design)), key=lambda s: (-float(design[s].get("level", 0.0) or 0.0),
                                                     0 if design[s].get("day_type", "weekday") == "weekday" else 1, s))


def import_root_from_pool(run: Run, ctx: Ctx, path: str) -> Dict[int, float]:
    """``--root-import``: the all-open subset cuts (atoms containing every candidate) of another
    ``cuts.jsonl`` whose header signature equals this run's pool signature (e.g. the step-2b
    probe pool), written as root files (method ``imported``).  A pool with another signature is
    refused (record ``root_import`` with the reason)."""
    key = ctx.root_key()
    try:
        pool = BD.CutPool(path, BD.pool_signature(ctx.ev), read_only=True)
    except (ValueError, FileNotFoundError) as exc:
        run.emit({"kind": "root_import", "path": path, "ok": False, "reason": f"{type(exc).__name__}: {exc}"}, echo=True)
        return {}
    ids = set(ctx.ids)
    best: Dict[int, float] = {}
    for c in pool.cuts:
        if c.kind == "subset" and c.scenario is not None and c.applies_to("relaxed") \
                and ids <= {str(x) for x in (c.meta or {}).get("atoms") or []}:
            best[int(c.scenario)] = max(best.get(int(c.scenario), -BL.INF), max(float(c.c0), float(c.L)))
    rdir = os.path.join(run.dir, "root_lp")
    os.makedirs(rdir, exist_ok=True)
    for s, v in sorted(best.items()):
        fp = os.path.join(rdir, f"root_s{s:02d}.json")
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    old = json.load(fh)
                if old.get("key") == key and (old.get("bound") or [None] * (s + 1))[s] is not None \
                        and float(old["bound"][s]) >= v:
                    continue
            except (OSError, ValueError, TypeError, IndexError):
                pass
        bound: List[Optional[float]] = [None] * ctx.ev.n_scenarios
        bound[s] = float(v)
        _write_json_atomic(fp, {"key": key, "kind": "root_lp", "method": "imported", "scenario": s, "bound": bound,
                                "rows": [{"scenario": s, "seed": ctx.ev.seeds[s], "bound": float(v), "status": "imported",
                                          "source": os.path.abspath(path)}]})
    run.emit({"kind": "root_import", "path": path, "ok": True, "scenarios": sorted(best), "values": best}, echo=True)
    return best


def stage_rootlp(run: Run, ctx: Ctx) -> Dict[str, Any]:
    """Stage D / production plan 5 item 1: the root floor ``L_s`` = safe value of the all-open
    free-size subset LP (``ScenarioLP.solve_subset`` over every candidate; box minimum of the
    C1 cut, valid for any multipliers) of each scenario of ``--root-scenarios`` (default all,
    longest stratum first), one LP at a time: the template is built, the LP built, the template
    evicted (the LP releases its library reference) and the LP disposed after the solve.  Each
    value goes to ``root_lp/root_s<NN>.json`` in the ``bound.json`` form (``key`` =
    :meth:`Ctx.root_key`, ``bound`` with this scenario's entry, ``rows``); scenarios with a file
    under the same key are skipped (``--redo`` reruns).  Never writes the shared cut pool (three
    such processes run at once); the solving stages merge the files (``--root-merge``)."""
    a = run.args
    order = root_order(ctx.design)
    scen = [int(s) for s in a.root_scenarios] if a.root_scenarios else order
    bad = [s for s in scen if not 0 <= s < ctx.ev.n_scenarios]
    if bad:
        raise SystemExit(f"--root-scenarios {bad} out of range 0..{ctx.ev.n_scenarios - 1}")
    key = ctx.root_key()
    rdir = os.path.join(run.dir, "root_lp")
    plan = {"kind": "rootlp_plan", "scenarios": scen, "order": order, "key": key, "n_locations": len(ctx.ids),
            "lp_threads": a.lp_threads, "lp_method": a.lp_method, "import": a.root_import}
    run.emit(plan, echo=True)
    if a.dry_run:
        return plan
    os.makedirs(rdir, exist_ok=True)
    if a.root_import:
        import_root_from_pool(run, ctx, a.root_import)
    out: Dict[str, Any] = {}
    for s in scen:
        fp = os.path.join(rdir, f"root_s{s:02d}.json")
        if not a.redo and os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    old = json.load(fh)
                if old.get("key") == key and (old.get("bound") or [None] * (s + 1))[s] is not None:
                    run.emit({"kind": "stage_skipped", "stage": "rootlp", "scenario": s,
                              "reason": f"{os.path.basename(fp)} exists (same key)"}, echo=True)
                    out[str(s)] = old["bound"][s]
                    continue
            except (OSError, ValueError, TypeError, IndexError):
                pass
        if not run.rss_guard(f"rootlp scenario {s}"):
            break
        t0 = time.perf_counter()
        lp = BD.ScenarioLP(ctx.ev, s, threads=a.lp_threads, method=a.lp_method, relaxed=True)
        lp.release_library()
        ctx.ev.evict_template(s)                # the solve needs the model only (production plan 5 item 2)
        rss_built = rss_gb()
        try:
            r = lp.solve_subset(ctx.ids)
        finally:
            size, build_s = dict(lp.size), float(lp.build_s)
            lp.dispose()
        value = None if r.Qs is None else max(0.0, float(r.Qs))
        row = {"scenario": s, "seed": ctx.ev.seeds[s], "stratum": ctx.design[s].get("stratum"), "status": r.status,
               "method": r.method, "bound": value, "Qs": r.Qs, "Qt": r.Qt, "artificial": r.artificial,
               "runtime_s": r.runtime_s, "iterations": r.iterations, "build_s": build_s, "size": size,
               "wall_s": time.perf_counter() - t0, "rss_gb_after_build": rss_built, "rss_gb": rss_gb(),
               "n_locations": len(ctx.ids), "demand_md5": ctx.ev.demand_md5[s]}
        bound: List[Optional[float]] = [None] * ctx.ev.n_scenarios
        bound[s] = value
        _write_json_atomic(fp, {"key": key, "kind": "root_lp", "method": "all_open_free", "scenario": s, "bound": bound,
                                "rows": [row]})
        run.emit({"kind": "root_lp", **row}, echo=True)
        out[str(s)] = value
    ctx.L = None                                # later stages of this process merge the new values
    missing = [s for s in scen if out.get(str(s)) is None]
    if missing:                                 # fixer pass: the lane must fail (re-runnable), not report done
        run.emit({"kind": "rootlp_incomplete", "missing": missing, "requested": scen,
                  "reason": "RSS guard or a root LP without a finite value"}, echo=True)
        raise SystemExit(3)
    run.emit({"kind": "stage_done", "stage": "rootlp", "config_md5": ctx.config_md5(), "scenarios": scen})
    return out


COMPARISON_NAMES = tuple(BL.RULES) + ("dot_pilot_proxy", "dot_all_pilot", "transplant")


def comparison_filter(args: argparse.Namespace, ctx: Ctx) -> Dict[str, Optional[set]]:
    """R7 comparison filter (production plan 5 item 5): ``{name: allowed m values or None}``.
    ``--comparison-rules`` tokens ``NAME`` or ``NAME@m1,m2`` (NAME in :data:`COMPARISON_NAMES`;
    ``transplant`` = every transplanted 15-candidate optimum); ``--comparison-budgets m ...`` is
    the default m set of the per-budget rows (CSCD / CSTC / CSAV / dot_pilot_proxy) named without
    ``@``.  The rows with their own budget (dot_all_pilot, transplant) are kept at any m unless
    ``@`` restricts them.  Neither flag = every row (the old behaviour)."""
    toks = getattr(args, "comparison_rules", None)
    dflt = getattr(args, "comparison_budgets", None)
    dflt_set = None if not dflt else {int(m) for m in dflt}
    if not toks:                                 # every row; --comparison-budgets alone limits the per-budget rows
        return {n: (None if n in ("dot_all_pilot", "transplant") else (None if dflt_set is None else set(dflt_set)))
                for n in COMPARISON_NAMES}
    out: Dict[str, Optional[set]] = {}
    for t in toks:
        for part in str(t).split():
            name, _, ms = part.partition("@")
            key = next((n for n in COMPARISON_NAMES if n.lower() == name.strip().lower()), None)
            if key is None:
                raise SystemExit(f"--comparison-rules: unknown row {name!r}; choose from {COMPARISON_NAMES}")
            if ms:
                allowed = {int(x) for x in ms.replace(",", " ").split()}
            else:
                allowed = dflt_set if key not in ("dot_all_pilot", "transplant") else None
            prev = out.get(key, set())
            out[key] = None if (allowed is None or prev is None and key in out) else (set(prev or set()) | allowed)
    return out


def comparison_time_limits(args: argparse.Namespace, ctx: Ctx) -> Dict[int, float]:
    """Per-row ILP limits by budget multiple m (``--comparison-time-limits m:seconds ...``);
    ``auto`` = ``{2: 600}`` for the ``manhattan_dot`` production family (plan stage G: the m = 2
    rows at 600 s), none for the toy and ``r5_manhattan`` (unchanged)."""
    toks = getattr(args, "comparison_time_limits", None)
    if toks is None or list(toks) == ["auto"]:
        return {2: 600.0} if ctx.production else {}
    out: Dict[int, float] = {}
    for t in toks:
        if str(t).lower() in ("none", "off", ""):
            continue
        m, _, sec = str(t).partition(":")
        if not sec:
            raise SystemExit(f"--comparison-time-limits: expected m:seconds, got {t!r}")
        out[int(m)] = float(sec)
    return out


def restore_prior_lb(cert: BD.SitingCertifier, records: Sequence[Dict[str, Any]]) -> Dict[float, float]:
    """Raise ``cert.LB[b]`` to the last ``budget_result`` LB of every budget of the certifier
    (and take its ``LB_kind``), as stages bb / polish do.  Valid: every earlier LB of the same
    configuration is a lower bound on ``V*_b``.  Stages that run AFTER a certificate (production
    order: comparison and the r7_search stages after m1) call it before ``finish``, so their
    ``budget_result`` keeps the certificate instead of the master's weaker pool bound."""
    prior = last_results(records, cert.target)
    out: Dict[float, float] = {}
    for b in cert.budgets:
        r = prior.get(b)
        if r is not None and isinstance(r.get("LB"), (int, float)) and float(r["LB"]) > cert.LB[b]:
            cert.LB[b] = float(r["LB"])
            cert.LB_kind[b] = r.get("LB_kind") or cert.LB_kind[b]
            out[b] = float(r["LB"])
    cert._nested_lb()
    return out


def stage_comparison(run: Run, ctx: Ctx) -> Dict[str, Any]:
    """Comparison layouts (design 2.6) priced on the all-candidates tier.  R7 filter (production
    plan 5 item 5): ``--comparison-rules`` / ``--comparison-budgets`` select the rows
    (:func:`comparison_filter`), ``--comparison-time-limits`` sets the per-row ILP limit by m
    (:func:`comparison_time_limits`; production: the m = 2 rows at 600 s).  The prior bounds of
    the budgets are restored before ``finish`` (the production order runs this stage after m1)."""
    a = run.args
    rules = rule_layouts(ctx)
    filt = comparison_filter(a, ctx)
    tls = comparison_time_limits(a, ctx)

    def keep(name: str, m: Optional[int]) -> bool:
        if name not in filt:
            return False
        allowed = filt[name]
        return allowed is None or (m is not None and int(m) in allowed)

    def m_of_budget(b: float) -> int:
        return int(round(b / ctx.unit))

    plan = {"kind": "comparison_plan", "rules": {f"{r}@m{ctx.m_of[b]}": (None if l is None else l.key()) for (r, b), l in rules.items()},
            "transplanted": [(k, l.key()) for k, l in transplanted(ctx)],
            # the family name and max_pair_km enter every cache key of manhattan_dot: the transplanted
            # 15-candidate optima are re-priced here, never cache hits of outputs/r6_o2/manhattan_pass2
            "transplanted_note": "re-priced on this family (cache keys differ from r5_manhattan by family, "
                                 "max_pair_km and transfer pairs); not cache hits",
            "filter": {k: (None if v is None else sorted(v)) for k, v in filt.items()},
            "time_limits_by_m": {str(k): v for k, v in sorted(tls.items())}}
    pdw = BL.present_day_sites(ctx.candidates, dot_csv=a.dot_csv) if not ctx.smoke else {"weights": {c.id: 1.0 for c in ctx.candidates}, "source": "toy", "proxy": True, "n_points": 0}
    pilot = BL.dot_pilot_layout(ctx.candidates)
    plan["present_day"] = {"source": pdw["source"], "proxy": pdw["proxy"], "n_points": pdw["n_points"],
                           "all_pilot": None if pilot is None else pilot.key(),
                           "n_pilot_sites": 0 if pilot is None else pilot.n_open}
    rows: List[Tuple[str, Optional[BL.Layout], float]] = []
    for b in ctx.budgets:
        for rule in BL.RULES:
            if keep(rule, ctx.m_of[b]):
                rows.append((rule, rules[(rule, b)], b))
        if keep("dot_pilot_proxy", ctx.m_of[b]):
            rows.append(("dot_pilot_proxy", None, b))       # built from the best layout when priced
    if pilot is not None:
        b_pilot = float(math.ceil(pilot.investment(ctx.spec) / ctx.unit - 1e-9)) * ctx.unit
        if keep("dot_all_pilot", m_of_budget(b_pilot)):
            rows.append(("dot_all_pilot", pilot, b_pilot))
    for key, lay in transplanted(ctx):
        b_t = float(math.ceil(lay.investment(ctx.spec) / ctx.unit - 1e-9)) * ctx.unit
        if keep("transplant", m_of_budget(b_t)):
            rows.append((f"transplant:{key}", lay, b_t))
    plan["rows"] = [(n, None if l is None else l.key(), b, tls.get(m_of_budget(b))) for n, l, b in rows]
    plan["n_rows"] = len(rows)
    tier = getattr(a, "price_tier", "all_candidates")
    if tier != "all_candidates":                   # re-plan change 7 (absent: the old record)
        plan["price_tier"] = tier
    run.emit(plan, echo=True)
    if a.dry_run:
        return plan
    if not run.rss_guard("comparison"):
        return plan
    cert = ctx.certifier("relaxed", wall_h=a.wall_comparison, label="comparison", pricing_only=True, **cover_kw(a))
    restore_prior_lb(cert, run.load())
    for name, lay, b in rows:
        if cert.wall_out():
            run.emit({"kind": "stage_skipped", "stage": "comparison", "reason": f"wall before row {name} at m {m_of_budget(b)}"},
                     echo=True)
            break
        if name == "dot_pilot_proxy":
            ref_key = best_layout_at(run.load(), b, ctx.spec, tiers=tiers_of(a))
            ref = BL.Layout.from_key(ref_key[0]) if ref_key else rules[("CSAV", b)]
            lay = None if ref is None else BL.capacity_matched_layout(ctx.candidates, ref, pdw["weights"], ctx.spec, role="SC")
        tl = tls.get(m_of_budget(b))
        ms = many_sites_limit(a, lay)               # re-plan section 3: 900 s for >= 5 open sites
        if ms is not None:
            tl = ms if tl is None else max(tl, ms)
        if tier == "open_sites":                    # re-plan change 7
            price_named(run, cert, name, lay, b, time_limit=tl, tier=tier)
        else:
            price_named(run, cert, name, lay, b, time_limit=tl)
    res = cert.finish(final_master_s=a.final_master_s)
    cert.close()
    run.emit({"kind": "stage_done", "stage": "comparison", "config_md5": ctx.config_md5()})
    return {str(b): r for b, r in res.items()}


def m1_warm_layouts(ctx: Ctx, warm: Sequence[BL.Layout], b1: float) -> List[BL.Layout]:
    """Production warm start of stage m1 (plan 2.1 stage B: the transplanted sites first for UB_1):
    the warm layouts within budget m = 1 plus a one-site layout at every location of the
    transplanted 15-candidate optima (their own size when it fits ``b1``, else the representative
    option).  The m1 certifier has the single budget ``b1``, so ``ub_ref`` of a larger layout is
    ``-inf`` and ``price_layout`` would price it IN FULL (12 LPs + 12 ILPs per layout, about
    0.5 h each at N = 59) for nothing the m = 1 certificate uses; the comparison stage prices the
    rule layouts of m = 2, 3 later.  Older families keep the unfiltered list."""
    out: List[BL.Layout] = [l for l in warm if l.investment(ctx.spec) <= b1 + 1e-6]
    rep = None
    opts = [o for o in ctx.enc.options if o[0] == "SC"]
    if opts:
        rep = min(opts, key=lambda o: (abs(o[1] - 3) + abs(o[2] - 2), -o[1], -o[2]))
    for _key, lay in transplanted(ctx):
        for it in lay.open:
            one = BL.Layout.of([it])
            if one.investment(ctx.spec) > b1 + 1e-6 or not ctx.enc.contains(one):
                if rep is None or rep[0] not in ctx.ev.roles_of.get(it[0], ()):
                    continue
                one = BL.Layout.of([(it[0],) + tuple(rep)])
            if one.investment(ctx.spec) <= b1 + 1e-6 and ctx.enc.contains(one):
                out.append(one)
    seen, uniq = set(), []
    for l in out:
        if l.key() not in seen:
            seen.add(l.key())
            uniq.append(l)
    return uniq


def stage_m1(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    b1 = min(ctx.budgets)
    if a.dry_run:
        n = len(BL.enumerate_layouts(ctx.candidates, ctx.enc.options, b1, ctx.spec, (1,), s_needs_charge=True))
        plan = {"kind": "m1_plan", "budget": b1, "n_layouts": n, "n_lp_locations": len(ctx.ids),
                "n_lp_solves_min": len(ctx.ids) * ctx.ev.n_scenarios}
        run.emit(plan, echo=True)
        return plan
    if not run.rss_guard("m1"):
        return {}
    cert = ctx.certifier("relaxed", budgets=[b1], wall_h=a.wall_m1, label="m1")
    price_pass = str(getattr(a, "m1_pass2", "on") or "on") != "off"
    warm = warm_layouts(ctx, run.load(), rule_layouts(ctx))
    if ctx.production:
        warm = m1_warm_layouts(ctx, warm, b1)
        run.emit({"kind": "m1_warm", "layouts": [l.key() for l in warm]}, echo=True)
    if not price_pass:
        # R7 re-plan change 5 (M4): no pricing at all; the restored UB (incl. the open-sites
        # values, change 1) drives the prunes and the floor is computed as before
        run.emit({"kind": "m1_warm_skipped", "reason": "--m1-pass2 off: no pricing in this pass",
                  "UB": {str(b): (u if math.isfinite(u) else None) for b, u in cert.UB.items()},
                  "restored": dict(cert.restored)}, echo=True)
    elif ctx.lifecycle:
        # fixer pass (memory): the warm layouts' LPs first, the scenario LPs disposed, then the
        # warm pricings (templates + ILP workers, never together with the 12 LPs); pass 1 of the
        # enumeration rebuilds the LPs lazily
        run.emit({"kind": "m1_warm_memory", "when": "before warm start", "rss_gb": rss_gb()})

        def _guard() -> bool:
            run.emit({"kind": "m1_warm_memory", "when": "warm LPs solved and released", "rss_gb": rss_gb()})
            return run.rss_guard("m1 warm pricing")
        cert.warm_start(warm, release_lps=True, before_pricing=_guard)
        run.emit({"kind": "m1_warm_memory", "when": "after warm pricing", "rss_gb": rss_gb()})
    else:
        cert.warm_start(warm)
    # R7 production plan 5 items 2 and 4: no LP at a proven terminal-infeasible location (its
    # one-site layouts are marked INFEASIBLE_TERMINAL by ctx.certifier); with --lp-lifecycle the
    # scenario LPs are disposed between the LP pass and the pricing pass
    infeasible = sorted(ctx.feasibility())
    e = cert.certify_by_enumeration(b1, limit=a.enum_limit, force_lp_per_location=True,
                                    skip_locations=infeasible if infeasible else None, release_lps=ctx.lifecycle,
                                    **({} if price_pass else {"price_pass": False}))
    res = cert.finish(final_master_s=a.final_master_s)
    if ctx.smoke and price_pass:
        acceptance(run, ctx, cert, res, (1,))
    cert.close()
    done = {"kind": "stage_done", "stage": "m1", "config_md5": ctx.config_md5(),
            "enumeration": {k: e.get(k) for k in ("done", "reason", "gap", "close_reason")}}
    if not price_pass:
        done.update(m1_pass2="off", n_unpriced=e.get("n_unpriced"))
    run.emit(done)
    return {str(b): r for b, r in res.items()}


def stage_bnb(run: Run, ctx: Ctx, m: int) -> Dict[str, Any]:
    a = run.args
    b = float(m) * ctx.unit
    if b not in ctx.budgets:
        run.emit({"kind": "stage_skipped", "stage": f"bb{m}", "reason": f"budget m = {m} not in --budgets"}, echo=True)
        return {}
    smaller = [x for x in ctx.budgets if x < b - 1e-6]
    node_budget = {2: a.bnb_nodes[0], 3: a.bnb_nodes[1] if len(a.bnb_nodes) > 1 else a.bnb_nodes[0]}.get(m, a.bnb_nodes[-1])
    levels = ctx.levels
    # m = 3: refinement stops below level --bnb-levels-m3 (1-based count of levels visited; the
    # default 2 = regions and cells; open nodes are reported at their bound) when that truncates
    max_level = (a.bnb_levels_m3 - 1) if (m == 3 and 1 <= a.bnb_levels_m3 < len(levels)) else None
    visited = levels if max_level is None else levels[: max_level + 1]
    if a.dry_run:
        n0 = sum(math.comb(len(levels[0]), k) for k in range(1, m + 1))
        plan = {"kind": f"bb{m}_plan", "budget": b, "levels": [len(lv) for lv in visited], "levels_all": [len(lv) for lv in levels],
                "max_level": max_level, "level1_nodes": n0, "node_budget": node_budget, "S_LP": ctx.S_LP,
                "lp_solves_max": node_budget * len(ctx.S_LP), "window": [smaller[-1] if smaller else None, b],
                "passes": list(range(1, m + 1))}
        run.emit(plan, echo=True)
        return plan
    if not run.rss_guard(f"bb{m}"):
        return {}
    budgets = smaller[-1:] + [b] if smaller else [b]
    cert = ctx.certifier("relaxed", budgets=budgets, wall_h=getattr(a, f"wall_bb{m}"), label=f"bb{m}")
    cert.warm_start(warm_layouts(ctx, run.load(), rule_layouts(ctx)))
    prior = last_results(run.load())
    lb_smaller = -BL.INF
    if smaller:
        r = prior.get(smaller[-1])
        if r is not None and isinstance(r.get("LB"), (int, float)):
            lb_smaller = float(r["LB"])
            cert.LB[smaller[-1]] = max(cert.LB[smaller[-1]], lb_smaller)
    # the certificate of budget m: window (budget_{m-1}, budget_m] bounded for k = 1..m open
    # locations (k = 1 by windowed enumeration, k >= 2 by B&B passes), combined with LB_{m-1}
    rec = BD.certify_bnb(cert, m, b, levels, S_LP=ctx.S_LP, lb_smaller=lb_smaller,
                         budget_smaller=(smaller[-1] if smaller else None), node_budget=node_budget, label=f"bb{m}",
                         max_leaf_combos=a.max_leaf_combos, enum_limit=max(a.enum_limit, 20_000), max_level=max_level)
    res = cert.finish(final_master_s=a.final_master_s)
    if ctx.smoke:
        acceptance(run, ctx, cert, res, (m,))
    cert.close()
    run.emit({"kind": "stage_done", "stage": f"bb{m}", "config_md5": ctx.config_md5(), "bnb": {k: rec.get(k) for k in ("LB", "UB", "certified", "stop_reason", "n_nodes")}})
    return {str(x): r for x, r in res.items()}


def stage_polish(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    open_b = [b for b, r in last_results(run.load()).items() if not r.get("certified") and b in ctx.budgets] or \
        [b for b in ctx.budgets if b > min(ctx.budgets) + 1e-6]
    if a.dry_run:
        plan = {"kind": "polish_plan", "budgets": open_b, "wall_h": a.wall_polish}
        run.emit(plan, echo=True)
        return plan
    if not open_b or not run.rss_guard("polish"):
        run.emit({"kind": "stage_done", "stage": "polish", "config_md5": ctx.config_md5(), "note": "nothing open"})
        return {}
    cert = ctx.certifier("relaxed", budgets=open_b, wall_h=a.wall_polish, label="polish")
    cert.warm_start(warm_layouts(ctx, run.load(), rule_layouts(ctx)))
    prior = last_results(run.load())
    for b in open_b:
        r = prior.get(b)
        if r is not None and isinstance(r.get("LB"), (int, float)):
            cert.LB[b] = max(cert.LB[b], float(r["LB"]))
            cert.LB_kind[b] = r.get("LB_kind")
    cert.integer_phase()
    res = cert.finish(final_master_s=a.final_master_s)
    cert.close()
    run.emit({"kind": "stage_done", "stage": "polish", "config_md5": ctx.config_md5()})
    return {str(b): r for b, r in res.items()}


def stage_restricted(run: Run, ctx: Ctx) -> Dict[str, Any]:
    """DOT-only vs full (design 2.6 / section 4 item 4, table T3): the master with every location
    outside ``ctx.restrict_ids()`` fixed closed (``Master.restrict``; same template, cuts and
    cache), one bound-only solve per budget (a valid lower bound on ``V*_restricted >=
    V*_full``), the restricted incumbent (the best priced layout inside the set, or the master
    proposal priced exactly), reported beside the full bounds.  The restriction is never active
    when a full bound is computed."""
    a = run.args
    ids = ctx.restrict_ids()
    recs = run.load()
    full = last_results(recs)
    plan = {"kind": "restricted_plan", "restrict": a.restrict, "n_locations": len(ids), "locations": ids,
            "n_all": len(ctx.ids), "budgets": ctx.budgets}
    run.emit(plan, echo=True)
    if a.restrict != "dot":
        run.emit({"kind": "stage_skipped", "stage": "restricted", "reason": f"--restrict {a.restrict}"}, echo=True)
        run.emit({"kind": "stage_done", "stage": "restricted", "config_md5": ctx.config_md5(), "note": "not requested"})
        return plan
    if a.dry_run:
        return plan
    if not ids or len(ids) >= len(ctx.ids):
        run.emit({"kind": "stage_skipped", "stage": "restricted", "reason": "no lattice-only candidate to fix closed"}, echo=True)
        run.emit({"kind": "stage_done", "stage": "restricted", "config_md5": ctx.config_md5(), "note": "nothing to restrict"})
        return plan
    if not run.rss_guard("restricted"):
        return plan
    cert = ctx.certifier("relaxed", wall_h=a.wall_restricted, label="restricted", pricing_only=True, **cover_kw(a))
    for b in ctx.budgets:                       # the full bounds of the earlier stages (valid, restored)
        r = full.get(b)
        if r is not None and isinstance(r.get("LB"), (int, float)):
            cert.LB[b] = max(cert.LB[b], float(r["LB"]))
            cert.LB_kind[b] = r.get("LB_kind")
    keep = set(ids)
    out: Dict[str, Any] = {}
    tier = getattr(a, "price_tier", "all_candidates")
    open_tier = tier == "open_sites"            # re-plan change 7: open-sites values are UBs only
    try:
        cert.master.restrict(ids)
        for b in ctx.budgets:
            if cert.wall_out():
                break
            fr = full.get(b) or {}
            pools = [cert.priced] + ([cert.priced_open] if open_tier else [])
            inside = [(pr.V, key) for pool in pools for key, pr in pool.items() if pr.status == "PRICED" and pr.V is not None
                      and set(pr.layout.locations()) <= keep and pr.layout.investment(ctx.spec) <= b + 1e-6
                      and cert.in_master(pr.layout)]
            best_v, best_key = min(inside) if inside else (None, None)
            start = BL.Layout.from_key(best_key) if best_key else None
            ms = cert.master.solve(b, start=start, time_limit=a.final_master_s)
            cert.counters["master_solves"] += 1
            lb_m = ms.get("bound")
            proposal = ms.get("layout")
            priced_now = None
            if proposal is not None and cert.enc.contains(proposal) and set(proposal.locations()) <= keep \
                    and proposal.key() not in cert.priced and not (open_tier and proposal.key() in cert.priced_open) \
                    and not cert.wall_out():
                if open_tier:                    # full pricing on the open-sites library (K2.7): a UB only
                    pr = cert.price(proposal, full=True, tag="restricted", tier="open_sites",
                                    time_limit=many_sites_limit(a, proposal))
                else:
                    pr = cert.price(proposal, full=True, tag="restricted",       # exact value: the restricted incumbent
                                    lp=not getattr(cert, "pricing_only", False))
                priced_now = {"layout_key": proposal.key(), "status": pr.status, "V": pr.V}
                if open_tier:
                    priced_now["tier"] = "open_sites"
                if pr.status == "PRICED" and pr.V is not None and (best_v is None or pr.V < best_v - 1e-9):
                    best_v, best_key = pr.V, proposal.key()
                ms2 = cert.master.solve(b, start=proposal, time_limit=a.final_master_s)   # bound with the new cuts
                cert.counters["master_solves"] += 1
                if ms2.get("bound") is not None and (lb_m is None or ms2["bound"] > lb_m):
                    lb_m, ms = ms2["bound"], ms2
            lb_full = fr.get("LB")
            no_dot_layout = lb_m is not None and not math.isfinite(float(lb_m))     # master infeasible inside the DOT set
            if no_dot_layout:
                lb_m = None
            lb_r = None if lb_m is None else (lb_m if lb_full is None else max(float(lb_m), float(lb_full)))
            if lb_r is not None and best_v is not None and lb_r > best_v:
                lb_r = best_v                                             # solver tolerance: never above the incumbent
            ub_full = fr.get("UB")
            tol = cert.tol(best_v) if best_v is not None else None
            rec = {"kind": "restricted_result", "restrict": "dot", "budget": b, "m": ctx.m_of[b], "n_locations": len(ids),
                   "LB": lb_r, "UB": best_v, "best_layout": best_key, "master_status": ms.get("status"),
                   "master_bound": lb_m, "proposal": None if proposal is None else proposal.key(), "priced_now": priced_now,
                   "LB_full": lb_full, "UB_full": ub_full, "best_full": fr.get("best_layout"),
                   "gap": None if (best_v is None or lb_r is None) else ((best_v - lb_r) / abs(best_v) if abs(best_v) > 0 else 0.0),
                   "certified": bool(best_v is not None and lb_r is not None and best_v - lb_r <= tol + 1e-9),
                   "price_of_restriction_lo": None if (lb_r is None or ub_full is None) else lb_r - ub_full,
                   "price_of_restriction_hi": None if (best_v is None or lb_full is None) else best_v - lb_full}
            if open_tier:
                rec["tier"] = "open_sites" if (best_key and best_key in cert.priced_open and (
                    best_key not in cert.priced or cert.priced[best_key].V is None
                    or cert.priced_open[best_key].V <= cert.priced[best_key].V)) else "all_candidates"
                rec["LB_tier"] = "all_candidates (master / prior certificate)"
            if no_dot_layout:
                rec["note"] = "no admissible DOT-only layout within this budget (restricted master infeasible)"
            elif best_v is not None and ub_full is not None and best_v < ub_full - 1e-9:
                rec["note"] = "restricted incumbent below the full incumbent: the full UB of this budget is stale"
            run.emit(rec, echo=True)
            out[str(b)] = rec
    finally:
        cert.master.restrict(None)
    # fixer pass: a restricted layout priced here is a full-problem layout, i.e. a valid full UB;
    # finish() (restriction lifted, prior LBs restored) writes a budget_result with it, so that
    # T1, the oos / noradius lists and the map use the better incumbent
    restore_prior_lb(cert, run.load())
    res = cert.finish(final_master_s=a.final_master_s)
    out["budget_results"] = {str(b): {k: r.get(k) for k in ("best_layout", "UB", "LB", "gap", "certified")}
                             for b, r in res.items()}
    cert.close()
    run.emit({"kind": "stage_done", "stage": "restricted", "config_md5": ctx.config_md5()})
    return out


def chosen_layouts(run: Run, ctx: Ctx, with_rules: bool = True, with_dot: bool = True) -> List[Tuple[str, BL.Layout, float]]:
    """``(name, layout, budget)``: the best layout per budget, the best rule layout per budget,
    the DOT all-pilot layout and the capacity-matched DOT proxy at m = 2 (design 2.6 / 7.4 item 21)."""
    recs = run.load()
    out: List[Tuple[str, BL.Layout, float]] = []
    seen = set()

    def add(name, key, b):
        if key and key not in seen:
            seen.add(key)
            out.append((name, BL.Layout.from_key(key), b))
    for b in ctx.budgets:
        r = last_results(recs).get(b)
        if r is not None and r.get("best_layout"):
            add(f"best@m{ctx.m_of[b]}", r["best_layout"], b)
        else:
            bk = best_layout_at(recs, b, ctx.spec)
            if bk:
                add(f"best@m{ctx.m_of[b]}", bk[0], b)
        if with_rules:
            rows = [x for x in recs if x.get("kind") == "baseline" and x.get("rule") in BL.RULES and float(x.get("budget") or -1) == b
                    and x.get("V") is not None]
            if rows:
                best = min(rows, key=lambda x: x["V"])
                add(f"{best['rule']}@m{ctx.m_of[b]}", best["layout_key"], b)
    if with_dot:
        for x in recs:
            if x.get("kind") == "baseline" and x.get("rule") == "dot_all_pilot" and x.get("layout_key"):
                add("dot_all_pilot", x["layout_key"], float(x["budget"]))
            if x.get("kind") == "baseline" and x.get("rule") == "dot_pilot_proxy" and x.get("layout_key") \
                    and abs(float(x.get("budget") or 0) / ctx.unit - 2.0) < 1e-6:
                add("dot_pilot_proxy@m2", x["layout_key"], float(x["budget"]))
    return out


def stage_written(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    lays = chosen_layouts(run, ctx)[: a.written_layouts]
    plan = {"kind": "written_plan", "layouts": [(n, l.key(), b) for n, l, b in lays]}
    run.emit(plan, echo=True)
    if a.dry_run or not lays:
        return plan
    if not run.rss_guard("written"):
        return plan
    cert = ctx.certifier("written", wall_h=a.wall_written, label="written")
    rel = last_results(run.load())
    for name, lay, b in lays:
        if cert.wall_out():
            break
        res = cert.price(lay, full=True, tag=f"written:{name}")
        n_esc = 0
        while res.status in ("PRICED", "UNRESOLVED") and cert.escalate(lay) and n_esc < 2 * ctx.ev.n_scenarios:
            n_esc += 1
            res = cert.priced[lay.key()]
        lb_rel = (rel.get(b) or {}).get("LB")
        run.emit({"kind": "written_price", "target": "written", "name": name, "budget": b, "layout_key": lay.key(),
                  "status": res.status, "V": res.V, "opex": res.ub, "lb": res.lb, "n_escalations": n_esc,
                  "LB_relaxed_budget": lb_rel, "served_share": res.served_share}, echo=True)
    res = cert.finish(final_master_s=a.final_master_s)
    cert.close()
    run.emit({"kind": "stage_done", "stage": "written", "config_md5": ctx.config_md5()})
    return {str(b): r for b, r in res.items()}


def stage_oos(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    lays = chosen_layouts(run, ctx)
    plan = {"kind": "oos_plan", "layouts": [(n, l.key(), b) for n, l, b in lays],
            "held_out_seeds": None if ctx.ev_out is None else ctx.ev_out.seeds}
    run.emit(plan, echo=True)
    if a.dry_run or ctx.ev_out is None or not lays:
        if ctx.ev_out is None:
            run.emit({"kind": "stage_skipped", "stage": "oos", "reason": "no held-out scenarios (--held-out)"}, echo=True)
        return plan
    if not run.rss_guard("oos"):
        return plan
    wall = C.WallBudget(a.wall_oos * 3600.0, margin_s=60.0, min_solve_s=30.0)
    ctx.ev_out.wall = wall
    recs = run.load()
    strata_in = [d["stratum"] for d in ctx.design]
    strata_out = [d["stratum"] for d in ctx.held]
    for name, lay, b in lays:
        if wall.remaining() < 120.0:
            break
        res = BD.price_layout(ctx.ev_out, lay, [0.0] * ctx.ev_out.n_scenarios, BL.INF, 0.0, full=True,
                              workers=a.price_workers)
        v_in = (priced_layouts(recs).get(lay.key()) or {}).get("V")
        opex_in = (priced_layouts(recs).get(lay.key()) or {}).get("ub")
        rec = {"kind": "oos_result", "name": name, "budget": b, "layout_key": lay.key(), "status": res.status,
               "V_out": res.V, "opex_out": res.ub, "V_in": v_in, "served_out": res.served_share,
               "ci_out": None, "ci_in": None, "diff": None}
        if res.V is not None and all(u is not None for u in res.ub):
            rec["ci_out"] = BL.stratified_ci(res.ub, strata_out, ctx.ev_out.p)
            rec["ci_out_plain"] = BL.paired_ci(res.ub, ctx.ev_out.p)
        if v_in is not None and opex_in and all(u is not None for u in opex_in):
            rec["ci_in"] = BL.stratified_ci(opex_in, strata_in, ctx.p)
        if rec["V_out"] is not None and v_in is not None:
            rec["diff"] = rec["V_out"] - v_in
        run.emit(rec, echo=True)
    run.emit({"kind": "stage_done", "stage": "oos", "config_md5": ctx.config_md5()})
    return plan


def stage_compliance(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    recs = run.load()
    b2 = next((b for b in ctx.budgets if ctx.m_of[b] == 2), max(ctx.budgets))
    r2 = last_results(recs).get(b2)
    key = r2.get("best_layout") if r2 else (best_layout_at(recs, b2, ctx.spec) or [None])[0]
    lays = chosen_layouts(run, ctx, with_dot=False)
    plan = {"kind": "compliance_plan", "layout_key": key, "alphas": a.alphas, "draws": a.draws,
            "followers_on": [(n, l.key()) for n, l, _b in lays]}
    run.emit(plan, echo=True)
    if a.dry_run or key is None:
        return plan
    if not run.rss_guard("compliance"):
        return plan
    wall = C.WallBudget(a.wall_compliance * 3600.0, margin_s=60.0, min_solve_s=30.0)
    ctx.ev.wall = wall
    for name, lay, b in lays:
        for pol in ("baseline", "selfish"):
            try:
                r = ctx.ev.evaluate(lay, pol)
                rec = {"V": r.get("V"), "status": r.get("status"), "served_share": r.get("served_share")}
            except Exception as exc:  # noqa: BLE001
                rec = {"V": None, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
            v_ilp = (priced_layouts(recs).get(lay.key()) or {}).get("V")
            run.emit({"kind": "cross_follower", "target": "relaxed", "name": name, "budget": b, "layout_key": lay.key(),
                      "policy": pol, "V_ilp": v_ilp, **rec}, echo=True)
    lay = BL.Layout.from_key(key)
    try:
        sw = BL.compliance_sweep(ctx.ev, lay, alphas=tuple(a.alphas), seeds=tuple(range(a.draws)))
        for row in sw["summary"]:
            run.emit({"kind": "compliance", "layout_key": key, "budget": b2, **row}, echo=True)
        run.emit({"kind": "compliance_rows", "layout_key": key, "n_rows": len(sw["rows"]), "rows": sw["rows"][:200]})
    except Exception as exc:  # noqa: BLE001
        run.emit({"kind": "compliance", "layout_key": key, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}, echo=True)
    run.emit({"kind": "stage_done", "stage": "compliance", "config_md5": ctx.config_md5()})
    return plan


def stage_hubecon(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    recs = run.load()
    b2 = next((b for b in ctx.budgets if ctx.m_of[b] == 2), max(ctx.budgets))
    r2 = last_results(recs).get(b2)
    inc_key = r2.get("best_layout") if r2 else (best_layout_at(recs, b2, ctx.spec) or [None])[0]
    cscd = next((x["layout_key"] for x in recs if x.get("kind") == "baseline" and x.get("rule") == "CSCD"
                 and float(x.get("budget") or -1) == b2 and x.get("layout_key")), None)
    hubs = [c.id for c in ctx.candidates if "C" in ctx.ev.roles_of[c.id]]
    hub_opts = [o for o in ctx.enc.options if o[0] == "C"]
    adds: List[BL.Layout] = []
    if inc_key:
        inc = BL.Layout.from_key(inc_key)
        for l in hubs:
            if inc.item(l) is not None:
                continue
            for o in hub_opts:
                adds.append(inc.add((l,) + o))
    plan = {"kind": "hubecon_plan", "incumbent_m2": inc_key, "cscd_m2": cscd, "hub_capable": hubs, "n_hub_additions": len(adds),
            "settings": HUB_SETTINGS, "n_screen": a.hub_screen}
    run.emit(plan, echo=True)
    if a.dry_run or inc_key is None:
        return plan
    if not run.rss_guard("hubecon"):
        return plan
    cert = ctx.certifier("relaxed", wall_h=a.wall_hubecon, label="hubecon")
    screened: List[Tuple[float, BL.Layout]] = []
    for lay in adds:
        if cert.wall_out() or not ctx.enc.contains(lay):
            continue
        cert.lp_at(lay)
        screened.append((cert.v_lp(lay), lay))
        run.emit({"kind": "hub_screen", "layout_key": lay.key(), "v_LP": screened[-1][0]})
    screened.sort(key=lambda t: (t[0], t[1].key()))
    hub_lays = [l for _v, l in screened[: a.hub_screen]]
    base_lays = [("best_m2", BL.Layout.from_key(inc_key))] + ([("CSCD_m2", BL.Layout.from_key(cscd))] if cscd else []) \
        + [(f"hub_add_{i + 1}", l) for i, l in enumerate(hub_lays)]
    for setting, cfg in HUB_SETTINGS.items():
        spec = S.SitingSpec(**{**ctx.spec.to_dict(), **cfg["spec"]})
        ev = ctx.ev.derive(variant=(cfg["variant"] or None), spec=spec)
        ev.wall = cert.ev.wall
        for name, lay in base_lays:
            if cert.wall_out():
                break
            if cfg["variant"]:
                r = ev.evaluate(lay, "ilp")
                rec = {"status": r["status"], "V": r["V"] if r["V"] not in (None, BL.INF) else None, "opex": r["opex"],
                       "served_share": r.get("served_share")}
            else:                       # F_hub only moves the set-up: recompute from the cached rows
                r = ctx.ev.evaluate(lay, "ilp")
                v = None if r["V"] in (None, BL.INF) else lay.allocated_cost(spec) + (r["V"] - lay.allocated_cost(ctx.spec))
                rec = {"status": r["status"], "V": v, "opex": r["opex"], "served_share": r.get("served_share"),
                       "note": "OPEX rows reused; set-up recomputed with the new F_hub"}
            run.emit({"kind": "hubecon", "setting": setting, "name": name, "layout_key": lay.key(), "budget": b2,
                      "n_hubs": lay.n_role("C"), **rec}, echo=True)
    cert.close()
    run.emit({"kind": "stage_done", "stage": "hubecon", "config_md5": ctx.config_md5()})
    return plan


def acceptance(run: Run, ctx: Ctx, cert: BD.SitingCertifier, res: Dict[float, Dict[str, Any]], ms: Sequence[int]) -> None:
    """Smoke cross-check: the certified UB equals the exhaustive optimum and LB is valid."""
    for b in ctx.budgets:
        if ctx.m_of[b] not in ms:
            continue
        lays = BL.enumerate_layouts(ctx.candidates, ctx.enc.options, b, ctx.spec, range(1, ctx.m_of[b] + 1), s_needs_charge=True)
        vals = [(ctx.ev.value(l), l.key()) for l in lays]
        best = min(vals)
        r = res[b]
        ok = r["UB"] is not None and abs(best[0] - r["UB"]) <= 1e-6 and isinstance(r["LB"], float) and r["LB"] <= best[0] + 1e-6
        run.emit({"kind": "acceptance", "target": "relaxed", "budget": b, "exhaustive_V": best[0], "exhaustive_layout": best[1],
                  "UB": r["UB"], "LB": r["LB"], "ok": bool(ok), "n_layouts": len(lays)}, echo=True)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
def role_table(recs: Sequence[Dict[str, Any]], ctx: Ctx, tiers: Sequence[str] = ("all_candidates",)) -> List[Dict[str, Any]]:
    """Per budget: the best layout, the best S-containing and the best hub-containing layout found
    (priced values; the LP screen value where only an LP exists) with the budget's bounds.
    ``tiers=('open_sites',)`` (re-plan change 7): the same rows from the open-sites values only
    (one follower on every side of a difference)."""
    out = []
    lp_vals = {r["layout_key"]: r["v_LP"] for r in recs if r.get("kind") == "lp_layout" and r.get("target") == "relaxed"}
    results = last_results(recs)
    for b in ctx.budgets:
        row = {"m": ctx.m_of[b], "LB": (results.get(b) or {}).get("LB"), "UB": (results.get(b) or {}).get("UB")}
        if tuple(tiers) != ("all_candidates",):
            row["follower"] = "+".join(tiers)
        for name, pred in (("best", lambda l: True), ("best_S", lambda l: l.n_role("S") > 0), ("best_hub", lambda l: l.n_role("C") > 0)):
            bk = best_layout_at(recs, b, ctx.spec, pred=pred, tiers=tiers)
            row[name] = None if bk is None else bk[0]
            row[name + "_V"] = None if bk is None else bk[1]
            if bk is None:
                cands = [(v, k) for k, v in lp_vals.items() if pred(BL.Layout.from_key(k)) and BL.Layout.from_key(k).investment(ctx.spec) <= b + 1e-6]
                if cands:
                    v, k = min(cands)
                    row[name] = k
                    row[name + "_lp_only"] = v
        out.append(row)
    return out


def instance_plan(run: Run, ctx: Ctx) -> Dict[str, Any]:
    """The ``plan`` record of :func:`stage_setup` without its solves and checks (fixer pass): the
    production lanes never run stage setup, so stage analyse writes it (and ``candidates.csv``)
    from the context when the records have none."""
    a = run.args
    cands = ctx.cands if ctx.cands is not None else list(ctx.candidates)
    return {"kind": "plan", "family": ctx.family, "n_candidates": len(ctx.ids), "candidates": ctx.ids,
            "budgets": ctx.budgets, "menu": ctx.menu, "n_options": len(ctx.enc.options), "n_w": ctx.enc.n,
            "n_hub_capable": sum(1 for c in ctx.candidates if "C" in ctx.ev.roles_of[c.id]),
            "scenarios": [{k: v for k, v in d.items() if k != "overrides"} for d in ctx.design],
            "held_out": [{k: v for k, v in d.items() if k != "overrides"} for d in ctx.held],
            "S_LP": ctx.S_LP, "p": ctx.p, "demand_md5": ctx.ev.demand_md5,
            "n_orders": [len(i.orders) for i in ctx.scen], "spec": ctx.spec.to_dict(),
            "levels": [len(lv) for lv in ctx.levels], "atoms": ctx.levels[:-1], "config_md5": ctx.config_md5(),
            "dot_info": ctx.info, "approach_radius": a.approach_radius, "weights_sum": sum(ctx.p),
            "candidate_classes": {cls: sum(1 for c in cands if c.cls == cls) for cls in ("dot", "lattice", "both")},
            "snap_m_max": max([c.snap_m for c in cands], default=0.0), "source": "analyse (no stage setup record)"}


def m1_epsilon(recs: Sequence[Dict[str, Any]], key: Optional[str]) -> Optional[Dict[str, Any]]:
    """Achieved incumbent MIP gap of the m = 1 layout (plan section 3, epsilon_1): ``(V - lower) /
    V`` of its last PRICED record, ``lower = setup + sum_s p_s lb_s``, with the worst scenario."""
    if not key:
        return None
    r = next((x for x in reversed(recs) if x.get("kind") == "price" and x.get("target") == "relaxed"
              and x.get("layout_key") == key and x.get("status") == "PRICED" and x.get("V") is not None), None)
    follower = "all_candidates"
    if r is None:                               # re-plan: an open-sites incumbent (its gap holds for that follower)
        o = open_priced(recs).get(key)
        if o is not None and o.get("lower_open") is not None:
            r = dict(o, lower=o["lower_open"], lb=o.get("lb_open"))
            follower = "open_sites"
    if r is None or r.get("lower") is None:
        return None
    V, lo = float(r["V"]), float(r["lower"])
    worst = None
    for s, (u, l) in enumerate(zip(r.get("ub") or [], r.get("lb") or [])):
        if u is not None and l is not None and float(u) > 0:
            g = (float(u) - float(l)) / float(u)
            if worst is None or g > worst[1]:
                worst = (s, g)
    return {"layout_key": key, "V": V, "lower": lo, "epsilon": (V - lo) / abs(V) if V else 0.0,
            "worst_scenario": None if worst is None else worst[0], "worst_gap": None if worst is None else worst[1],
            **({} if follower == "all_candidates" else {"follower": follower})}


BOTH_TIERS = ("all_candidates", "open_sites")


def _fmt(x: Any, nd: int = 2) -> str:
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def dual_statement_lines(d: Dict[str, Any]) -> List[str]:
    """``RESULTS.md`` lines of :func:`m1_dual_statement`."""
    al, op, ck = d["all_candidates"], d["open_sites"], d.get("ub_check")
    pct = (lambda g: "-" if g is None else f"{100 * g:.2f} %")
    out = ["## m = 1 under both followers (re-plan change 8)", "",
           f"* **All-candidates follower (model of record):** V*_1 in [{_fmt(al['LB'])}, {_fmt(al['UB'])}] "
           f"(gap {pct(al['gap'])}; LB = {al.get('LB_kind')}, UB = {al['best_layout']} priced on the {al['UB_tier']} tier, a "
           "feasible schedule of the all-candidates follower).",
           f"* locations not excluded (best known all-candidates lower bound < UB, tol 0): {al['n_locations_not_excluded']}: "
           + (", ".join(f"{x['location']} ({x['lower']:.2f})" for x in al["not_excluded"]) or "none")
           + (f"; {al['n_unknown']} layouts without any bound in the records" if al["n_unknown"] else ""),
           "* UB validity check (M6, open_sites schedules on the all-candidates library): "
           + ("not run" if ck is None else f"ok = {ck.get('ok')}, {ck.get('n_ok')} cells ok, V_checked = {_fmt(ck.get('V_checked'))} "
                                            f"against V_open = {_fmt(ck.get('V_open'))}"),
           f"* **Open-sites follower (tol 0):** V*_open in [{_fmt(op['LB'])}, {_fmt(op['UB'])}] (gap {pct(op['gap'])}; best "
           f"{op['best_layout']}; "
           + (f"LB from {op['argmin']}" if op["argmin"] is not None else
              f"LB unknown: {op['n_unknown']} layouts without any bound") + "); certificate "
           + ("COMPLETE: every layout with an open-sites lower bound below UB_open is priced" if op["complete"] else
              f"INCOMPLETE: {op['n_to_price']} layouts below UB_open not priced on open_sites"
              + (f" (first {', '.join(x['layout_key'] for x in op['to_price'][:8])})" if op["to_price"] else "")
              + (f", {op['n_unknown']} without any bound" if op["n_unknown"] else "")), ""]
    if op["ranking"]:
        out += ["Open-sites ranking at m = 1 (V_open = UB for both followers; lower_open holds for the open-sites follower "
                "only; lower_all = LP / envelope / all-candidates pricing):", ""]
        out += _table(op["ranking"], [("layout_key", "layout"), ("status", "status"), ("V_open", "V_open"),
                                      ("lower_open", "lower_open"), ("lower_all", "lower_all"), ("n_optimal", "cells OPTIMAL"),
                                      ("n_rows", "cells")], 2) + [""]
    return out


def _ub_tier(recs: Sequence[Dict[str, Any]], key: Optional[str], ub: Optional[float]) -> Optional[str]:
    """The tier of the pricing that gives ``ub`` at ``key`` (all_candidates when both tiers do)."""
    if not key or ub is None:
        return None
    for tiers in (("all_candidates",), ("open_sites",)):
        r = priced_layouts(recs, tiers=tiers).get(key)
        if r is not None and abs(float(r["V"]) - float(ub)) <= 1e-9 * max(1.0, abs(float(ub))):
            return tiers[0]
    return None


def m1_dual_statement(run: Run, ctx: Ctx, recs: Sequence[Dict[str, Any]], ub_all: Optional[float],
                      best_all: Optional[str]) -> Dict[str, Any]:
    """R7 re-plan change 8 (with K2.2): the m = 1 statement under both followers, from the
    records only (no solve).

    * All-candidates follower (model of record): ``V*_1 in [LB, UB]`` with ``LB`` the last
      ``budget_result`` LB of m = 1 (the enumeration floor), ``UB`` the best value of either tier
      (an open-sites value is feasible for the all-candidates follower, K1), and the locations
      whose best known lower bound (:func:`m1_lower_table`: LP, cut envelope, all-candidates
      pricing) is below ``UB`` (not excluded at tol = 0).
    * Open-sites follower (tol = 0, K2.2): ``UB_open`` = the best open-sites value; every layout's
      open-sites lower bound is ``max(lower of the table, lower_open of its price_open record)``
      (``inf`` when infeasible under that follower); ``LB_open`` = their minimum, ``gap_open =
      (UB_open - LB_open) / UB_open``.  The certificate is complete when no layout with an
      open-sites lower bound below ``UB_open`` is left unpriced (``to_price`` empty) and no
      layout is without a bound (``unknown`` empty).
    * M6: the last ``ub_check_all_candidates`` record (``source = check``) of the UB layout."""
    b1 = min(ctx.budgets)
    r1 = last_results(recs).get(b1) or {}
    tab = m1_lower_table(ctx, recs, b1)
    orec = open_records(recs)
    lb = r1.get("LB")
    # all-candidates follower
    by_loc: Dict[str, Tuple[float, str]] = {}
    unknown = []
    for key, d in tab.items():
        if d["lower"] is None:
            unknown.append(key)
            continue
        if ub_all is not None and d["lower"] < float(ub_all) - 1e-9:
            for loc in d["layout"].locations():
                if loc not in by_loc or d["lower"] < by_loc[loc][0]:
                    by_loc[loc] = (d["lower"], key)
    near_all = [{"location": loc, "lower": v, "layout_key": k} for loc, (v, k) in sorted(by_loc.items(), key=lambda t: (t[1][0], t[0]))]
    gap_all = None if (lb is None or ub_all is None or not ub_all) else (float(ub_all) - float(lb)) / abs(float(ub_all))
    # open-sites follower, tol = 0
    ub_open, best_open = None, None
    rows = []
    for key, d in tab.items():
        r = orec.get(key)
        if r is not None and r.get("status") == "PRICED" and r.get("V") is not None:
            if ub_open is None or float(r["V"]) < ub_open - 1e-12:
                ub_open, best_open = float(r["V"]), key
    lo_min, lo_arg = None, None
    to_price, unknown_open = [], []
    for key, d in tab.items():
        r = orec.get(key)
        lo = -BL.INF if d["lower"] is None else float(d["lower"])
        src = d["source"]
        if d["infeasible_open"] or (r is not None and r.get("status") == "INFEASIBLE"):
            lo, src = BL.INF, "infeasible"
        elif r is not None and r.get("status") == "PRICED" and r.get("lower_open") is not None and float(r["lower_open"]) > lo:
            lo, src = float(r["lower_open"]), "open_sites pricing"
        priced_open = r is not None and r.get("status") == "PRICED"
        if lo == -BL.INF:
            unknown_open.append(key)
        elif ub_open is not None and lo < ub_open - 1e-9 and not priced_open:
            to_price.append((lo, key))
        if r is not None and r.get("status") in ("PRICED", "INFEASIBLE"):
            rows.append({"layout_key": key, "status": r.get("status"), "V_open": r.get("V"), "lower_open": r.get("lower_open"),
                         "lower_all": d["lower"], "n_optimal": sum(1 for x in (r.get("rows") or []) if x.get("status") == "OPTIMAL"),
                         "n_rows": len(r.get("rows") or [])})
        if lo_min is None or lo < lo_min:
            lo_min, lo_arg = lo, key
    lb_open = None if (lo_min is None or lo_min == -BL.INF) else lo_min
    if lb_open is None:                         # no layout sets an LB of minus infinity
        lo_arg = None
    gap_open = None if (ub_open is None or lb_open is None or not ub_open) else (ub_open - min(lb_open, ub_open)) / abs(ub_open)
    to_price.sort()
    rows.sort(key=lambda x: (x["V_open"] is None, x["V_open"] if x["V_open"] is not None else 0.0, x["layout_key"]))
    chk = next((x for x in reversed(recs) if x.get("kind") == "ub_check_all_candidates" and x.get("source") == "check"
                and x.get("layout_key") == best_all), None)
    out = {"kind": "m1_dual_statement", "budget": b1, "n_layouts": len(tab),
           "all_candidates": {"LB": lb, "LB_kind": r1.get("LB_kind"), "UB": ub_all, "best_layout": best_all,
                              "UB_tier": _ub_tier(recs, best_all, ub_all),
                              "gap": gap_all, "n_locations_not_excluded": len(near_all), "not_excluded": near_all,
                              "n_unknown": len(unknown), "unknown": sorted(unknown)[:20]},
           "open_sites": {"UB": ub_open, "best_layout": best_open, "LB": lb_open, "argmin": lo_arg, "gap": gap_open,
                          "tol": 0.0, "complete": bool(ub_open is not None and not to_price and not unknown_open),
                          "n_to_price": len(to_price), "to_price": [{"layout_key": k, "lower": v} for v, k in to_price[:30]],
                          "n_unknown": len(unknown_open), "unknown": sorted(unknown_open)[:20], "ranking": rows[:40]},
           "ub_check": None if chk is None else {k: chk.get(k) for k in ("ok", "n_ok", "V_checked", "V_open", "scenarios")}}
    return out


def analyse(run: Run, ctx: Ctx) -> str:
    recs = run.load()
    if not any(r.get("kind") == "plan" for r in recs):
        run.emit(instance_plan(run, ctx))
        recs = run.load()
    if not os.path.exists(os.path.join(run.dir, "candidates.csv")):
        S.write_candidate_tables(ctx.cands if ctx.cands is not None else list(ctx.candidates), ctx.dropped, run.dir)
    unit = ctx.unit
    a = run.args
    res = last_results(recs)
    res_w = last_results(recs, "written")
    lines = [f"# R7 siting scale-up -- {ctx.family}", "",
             f"Records `{run.records}`; cut pool `{run.cuts}`; cache `{run.cache}`.  Generated {time.strftime('%Y-%m-%d %H:%M')}.",
             ""]
    probs = []
    # fixer pass: a layout priced after the last budget_result (e.g. by a search stage) can beat its UB
    best_now: Dict[float, Tuple[Optional[str], Optional[float]]] = {}
    for b in ctx.budgets:
        r = res.get(b) or {}
        ub = r.get("UB")
        bk = best_layout_at(recs, b, ctx.spec, tiers=BOTH_TIERS)      # re-plan: open-sites values are UBs too
        if bk is not None and (ub is None or bk[1] < float(ub) - 1e-9):
            best_now[b] = bk
            probs.append(f"m = {ctx.m_of[b]}: a layout priced after the last budget_result is better: {bk[0]} at "
                         f"V = {bk[1]:.2f} (budget_result UB {ub}); T1 uses it")
    for b, r in sorted(res.items()):
        if not r.get("certified"):
            probs.append(f"m = {ctx.m_of[b]}: NOT certified (gap {100 * r['gap']:.2f} % if known; stop: {r.get('close_reason')})"
                         if r.get("gap") is not None else f"m = {ctx.m_of[b]}: NOT certified (stop: {r.get('close_reason')})")
    # plan section 3 items: skip list, root values, epsilon_1, near-tie set
    fsl = next((r for r in reversed(recs) if r.get("kind") == "feas_skip_list"), None)
    if fsl is not None and fsl.get("n_dropped"):
        probs.append(f"feasibility screens: {fsl.get('n_dropped')} claim(s) not confirmed for this configuration (dropped)")
    rbm = next((r for r in reversed(recs) if r.get("kind") == "root_bound_merged"), None)
    if rbm is not None and rbm.get("missing"):
        probs.append(f"root LP values missing for scenarios {rbm.get('missing')} (L_s = superset / 0 there: valid, weaker)")
    for r in recs:
        if r.get("kind") == "root_import" and not r.get("ok"):
            probs.append(f"--root-import refused: {r.get('reason')}")
        if r.get("kind") == "rootlp_incomplete":
            probs.append(f"stage rootlp incomplete: scenarios {r.get('missing')} without a value ({r.get('reason')})")
    b1 = min(ctx.budgets)
    key1 = (best_now.get(b1) or (None,))[0] or (res.get(b1) or {}).get("best_layout")
    eps1 = m1_epsilon(recs, key1)
    tie = float(getattr(a, "near_tie", 0.03) or 0.03)
    ub1 = (best_now.get(b1) or (None, None))[1]
    if ub1 is None:
        ub1 = (res.get(b1) or {}).get("UB")
    near: List[Tuple[float, str]] = []
    near_open: set = set()                      # re-plan: near-tie values from open-sites pricing
    if ub1 is not None:
        for k, r in priced_layouts(recs, tiers=BOTH_TIERS).items():
            lay = BL.Layout.from_key(k)
            if lay.n_open == 1 and lay.investment(ctx.spec) <= b1 + 1e-6 and float(r["V"]) <= float(ub1) * (1.0 + tie) + 1e-9:
                near.append((float(r["V"]), k))
                if r.get("tier") == "open_sites":
                    near_open.add(k)
        near.sort()
    for r in recs:
        if r.get("kind") == "aborted":
            probs.append(f"stage {r.get('stage')} aborted: {r.get('reason')}")
        if r.get("kind") == "acceptance" and not r.get("ok"):
            probs.append(f"acceptance FAILED at budget {r.get('budget')}")
    lines += ["## Problems (read first)", ""] + ([f"* {p}" for p in probs] or ["* none"]) + [""]
    lines += ["## Certificate details (plan section 3)", "",
              f"* terminal-infeasible one-site locations (skip list): "
              + ("not screened" if fsl is None else f"{fsl.get('n_locations')} {fsl.get('locations')}"),
              f"* root LP values (L_s): " + ("not merged" if rbm is None else
                                            f"{len(rbm.get('root') or {})} scenarios, missing {rbm.get('missing')}; "
                                            f"L = {[round(float(x), 2) for x in (rbm.get('L') or [])]}"),
              f"* epsilon_1 (achieved incumbent MIP gap at m = 1): " + ("unknown" if eps1 is None else
                                                                     f"{100 * eps1['epsilon']:.3f} % of V = {eps1['V']:.2f} "
                                                                     f"({eps1['layout_key']}; worst scenario {eps1['worst_scenario']} "
                                                                     f"at {100 * (eps1['worst_gap'] or 0.0):.3f} %)"
                                                                     + (f" [{eps1['follower']} follower]" if eps1.get("follower") else "")),
              f"* near-tie set at m = 1 (priced one-site layouts within {100 * tie:.1f} % of UB_1 = {ub1}): "
              + (", ".join(f"{k} ({v:.2f}{' open_sites' if k in near_open else ''})" for v, k in near) if near else "none"), ""]
    # R7 re-plan change 8: the m = 1 statement under both followers
    dual = m1_dual_statement(run, ctx, recs, ub1, key1)
    run.emit(dual)
    lines += dual_statement_lines(dual)
    plan = next((r for r in reversed(recs) if r.get("kind") == "plan"), {})
    lines += ["## Instance", "", f"* candidates: {plan.get('n_candidates')} (classes {plan.get('candidate_classes')}); hub-capable "
              f"{plan.get('n_hub_capable')}; snap max {plan.get('snap_m_max')}; DOT info `{json.dumps(C.jsonable(plan.get('dot_info')))}`",
              f"* scenarios: {len(plan.get('scenarios') or [])} in-sample (weights sum {plan.get('weights_sum')}), "
              f"{len(plan.get('held_out') or [])} held out; orders {plan.get('n_orders')}; S_LP {plan.get('S_LP')}",
              f"* menu options {plan.get('n_options')}, master binaries {plan.get('n_w')}; budgets m = {[ctx.m_of[b] for b in ctx.budgets]}", ""]
    t1 = []
    for b, r in sorted(res.items()):
        c = r.get("counters") or {}
        row = {"m": ctx.m_of[b], "layout": r.get("best_layout"), "inv": r.get("investment"), "UB": r.get("UB"),
               "LB": r.get("LB"), "kind": r.get("LB_kind"), "gap": None if r.get("gap") is None else 100 * r["gap"],
               "cert": r.get("certified"), "reason": r.get("close_reason"), "priced": c.get("priced"),
               "subset_lps": c.get("subset_lps"), "ilp": c.get("ilp_solves"), "served": r.get("served_share"),
               "tier": r.get("best_tier") or ("all_candidates" if r.get("UB") is not None else None)}
        if b in best_now:                       # a better incumbent priced after this budget_result
            k, v = best_now[b]
            lb = r.get("LB")
            tier_now = _ub_tier(recs, k, v)
            row.update(layout=f"{k} (later)", UB=v, inv=BL.Layout.from_key(k).investment(ctx.spec), served=None, tier=tier_now)
            if lb is not None:
                row["gap"] = 100 * (v - float(lb)) / abs(v) if v else 0.0
                row["cert"] = bool(v - float(lb) <= BD.tolerance(v, a.tol_rel, a.tol_abs) + 1e-9)
        t1.append(row)
    lines += ["## T1 -- bound per budget (relaxed targets, all-candidates library)", "",
              "UB tier: the library of the pricing that gave the incumbent; an open_sites value is a feasible value of the "
              "all-candidates follower (sub-library), so UB is valid for the model of record either way; LB is always "
              "all-candidates (LP / cuts / enumeration floor).", ""]
    lines += _table(t1, [("m", "m"), ("layout", "best layout"), ("inv", "inv USD"), ("UB", "UB"), ("tier", "UB tier"), ("LB", "LB"),
                         ("kind", "LB kind"),
                         ("gap", "gap %"), ("cert", "certified"), ("reason", "stop"), ("priced", "priced"), ("subset_lps", "subset LPs"),
                         ("ilp", "ILP solves"), ("served", "served")], 3) + [""]
    bnb = [r for r in recs if r.get("kind") == "bnb_certificate"]
    if bnb:
        lines += ["B&B certificates (window (budget_{m-1}, budget_m] bounded for k = 1..m open locations): " +
                  "; ".join(f"m = {r.get('m')}: floors by k {r.get('floors_by_k')}, LB_{{m-1}} {r.get('lb_smaller')}, nodes "
                            f"{r.get('n_nodes')}, open {r.get('n_open')}, stop {r.get('stop_reason')}" for r in bnb), ""]
    base = {}
    for r in recs:
        if r.get("kind") == "baseline" and r.get("target") == "relaxed":
            base[(float(r["budget"]), r["rule"])] = r
    best_detail = {}
    for r in recs:
        if r.get("kind") == "price" and r.get("target") == "relaxed" and r.get("status") == "PRICED":
            best_detail[r["layout_key"]] = r
    best_open = open_priced(recs)                # re-plan change 7: open-sites rows compare with open-sites values
    strata = [d["stratum"] for d in ctx.design]
    t2 = []
    any_open = False
    for (b, rule), r in sorted(base.items()):
        br = res.get(b, {})
        UB, LB, V = br.get("UB"), br.get("LB"), r.get("V")
        bkey = br.get("best_layout") or ""
        if b in best_now:
            bkey, UB = best_now[b][0], best_now[b][1]
        row = {"m": round(b / unit, 2), "rule": rule, "layout": r.get("layout_key"), "V": V, "status": r.get("status"), "UB": UB}
        is_open = r.get("tier") == "open_sites"
        if is_open:
            any_open = True
            row.update(tier="open_sites", LB_rule=r.get("LB_rule"))
            # regret interval [LB_rule - UB*_m, UB_rule - LB*_m] (re-plan section 3): valid under the
            # all-candidates follower; LB_rule = envelope / LP / all-candidates pricing, UB_rule = V_open
            row["reg_lo"] = None if (r.get("LB_rule") is None or UB is None) else float(r["LB_rule"]) - float(UB)
            row["reg_hi"] = None if (V is None or LB is None) else V - LB
        elif V is not None and UB is not None:
            row["reg_lo"] = V - UB
            row["reg_hi"] = None if LB is None else V - LB
        bd = (best_open if is_open else best_detail).get(bkey)
        if bd and r.get("opex") and bd.get("ub") and all(x is not None for x in r["opex"]) and all(x is not None for x in bd["ub"]):
            d = [x - y for x, y in zip(r["opex"], bd["ub"])]
            ds = (r.get("setup") or 0.0) - (bd.get("setup") or 0.0)
            pl = BL.paired_ci(d, ctx.p)
            st = BL.stratified_ci(d, strata, ctx.p) if len(set(strata)) > 1 else pl
            row.update(diff=ds + pl["mean"], ci_plain=pl["half"], ci_strat=st["half"], df_strat=st.get("df"))
        t2.append(row)
    lines += ["## T2 -- comparison layouts (all priced on the all-candidates tier): regret intervals and paired CIs", "",
              "regret lo = V - UB (vs the best found), regret hi = V - LB (vs any layout); diff = V - V_best with the plain "
              "paired t (11 df at S = 12) and the stratified half-width (6 df); neither is narrow.", ""]
    if any_open:
        lines += ["Rows of tier open_sites (re-plan change 7): V = V_open is an upper bound on the rule's all-candidates value "
                  "(UB_rule) and LB rule its all-candidates lower bound (envelope / LP), so the regret interval under the "
                  "all-candidates follower is [LB_rule - UB*_m, UB_rule - LB*_m]; diff and its CIs compare open_sites values "
                  "on both sides (V_open - V_open(best); none when the best layout has no open_sites pricing).", ""]
    lines += _table(t2, [("m", "m"), ("rule", "layout"), ("layout", "key"), ("V", "V"), ("status", "status"),
                         ("tier", "tier"), ("LB_rule", "LB rule"), ("UB", "UB"),
                         ("reg_lo", "regret lo"), ("reg_hi", "regret hi"), ("diff", "V - V_best"), ("ci_plain", "CI plain"),
                         ("ci_strat", "CI strat"), ("df_strat", "df")], 2) + [""]
    rr = [r for r in recs if r.get("kind") == "restricted_result"]
    lines += ["## T3 -- DOT-only vs full (lattice-only candidates fixed closed; same template, cuts and cache)", ""]
    if rr:
        last_rr = {}
        for r in rr:
            last_rr[float(r["budget"])] = r
        lines += ["price of the restriction: certified range [LB_dot - UB_full, UB_dot - LB_full] (>= 0 when both bounds hold).", ""]
        lines += _table([{"m": r.get("m"), "n": r.get("n_locations"), "UB_full": r.get("UB_full"), "LB_full": r.get("LB_full"),
                          "UB_dot": r.get("UB"), "LB_dot": r.get("LB"), "layout": r.get("best_layout"), "cert": r.get("certified"),
                          "lo": r.get("price_of_restriction_lo"), "hi": r.get("price_of_restriction_hi"),
                          "tier": r.get("tier")}
                         for _b, r in sorted(last_rr.items())],
                        [("m", "m"), ("n", "DOT sites"), ("UB_full", "UB full"), ("LB_full", "LB full"), ("UB_dot", "UB DOT-only"),
                         ("tier", "UB DOT tier"),
                         ("LB_dot", "LB DOT-only"), ("layout", "best DOT-only"), ("cert", "certified"), ("lo", "price lo"),
                         ("hi", "price hi")], 2) + [""]
    else:
        lines += ["* not run (`--restrict dot` and stage `restricted`)", ""]
    rt = role_table(recs, ctx)
    run.emit({"kind": "role_table", "rows": rt})
    lines += ["## T4 -- role table per budget (best / best S-containing / best hub-containing found)", ""]
    lines += _table(rt, [("m", "m"), ("UB", "UB"), ("LB", "LB"), ("best", "best"), ("best_V", "V"), ("best_S", "best with S"),
                         ("best_S_V", "V"), ("best_S_lp_only", "LP only"), ("best_hub", "best with hub"), ("best_hub_V", "V"),
                         ("best_hub_lp_only", "LP only")], 2) + [""]
    if open_priced(recs):                       # re-plan change 7: the same rows under the open-sites follower
        rto = role_table(recs, ctx, tiers=("open_sites",))
        run.emit({"kind": "role_table", "rows": rto, "follower": "open_sites"})
        lines += ["T4b -- the same rows from the open_sites values only (one follower on every side of a difference; "
                  "V = UB of the all-candidates value; UB / LB are the budget's all-candidates bounds):", ""]
        lines += _table(rto, [("m", "m"), ("UB", "UB"), ("LB", "LB"), ("best", "best"), ("best_V", "V_open"),
                              ("best_S", "best with S"), ("best_S_V", "V_open"), ("best_hub", "best with hub"),
                              ("best_hub_V", "V_open")], 2) + [""]
    xf = [r for r in recs if r.get("kind") == "cross_follower"]
    comp = [r for r in recs if r.get("kind") == "compliance"]
    if xf or comp:
        lines += ["## T5 -- followers and compliance", ""]
        lines += _table([{"name": r.get("name"), "layout": r.get("layout_key"), "policy": r.get("policy"), "V": r.get("V"),
                          "V_ilp": r.get("V_ilp"), "status": r.get("status")} for r in xf],
                        [("name", "layout"), ("layout", "key"), ("policy", "follower"), ("V", "V"), ("V_ilp", "V ILP"), ("status", "status")], 2)
        lines += [""] + _table([{"alpha": r.get("alpha_c"), "V": r.get("V"), "served": r.get("served_share"), "def": r.get("mean_defected"),
                                 "complete": r.get("complete")} for r in comp],
                               [("alpha", "alpha_c"), ("V", "V"), ("served", "served"), ("def", "mean defected"), ("complete", "complete")], 3) + [""]
    oos = [r for r in recs if r.get("kind") == "oos_result"]
    if oos:
        lines += ["## T6 -- out-of-sample (held-out scenarios, shared cache)", ""]
        lines += _table([{"name": r.get("name"), "layout": r.get("layout_key"), "V_in": r.get("V_in"), "V_out": r.get("V_out"),
                          "diff": r.get("diff"), "ci": (r.get("ci_out") or {}).get("half"), "status": r.get("status"),
                          "tier": r.get("tier")} for r in oos],
                        [("name", "layout"), ("layout", "key"), ("tier", "tier"), ("V_in", "V in"), ("V_out", "V out"),
                         ("diff", "out - in"), ("ci", "CI out (strat)"), ("status", "status")], 2) + [""]
    hub = [r for r in recs if r.get("kind") == "hubecon"]
    if hub:
        lines += ["## T7 -- hub-economics sensitivity (hub-capable sites only)", ""]
        lines += _table([{"setting": r.get("setting"), "name": r.get("name"), "layout": r.get("layout_key"), "V": r.get("V"),
                          "hubs": r.get("n_hubs"), "status": r.get("status")} for r in hub],
                        [("setting", "setting"), ("name", "layout"), ("layout", "key"), ("V", "V"), ("hubs", "hubs"), ("status", "status")], 2) + [""]
    sizes = next((r for r in reversed(recs) if r.get("kind") == "sizes"), None)
    lines += ["## T8 -- sizes, timings, coverage", ""]
    if sizes:
        lines += [f"* templates: {json.dumps(C.jsonable(sizes.get('templates')))}", f"* LP sizes: {json.dumps(C.jsonable(sizes.get('lp')))}",
                  f"* z columns: {sizes.get('z_columns')}; RSS GB start/after LPs/end: {sizes.get('rss_gb_start')}/"
                  f"{sizes.get('rss_gb_after_lps')}/{sizes.get('rss_gb_end')}",
                  f"* timings: {json.dumps(C.jsonable(sizes.get('timings')))}", ""]
    done = [r for r in recs if r.get("kind") == "stage_done"]
    lines += ["* stages done: " + ", ".join(f"{r.get('stage')}" for r in done), ""]
    wr = [r for r in recs if r.get("kind") == "written_price"]
    if wr:
        lines += ["## T9 -- written targets (sensitivity)", ""]
        lines += _table([{"name": r.get("name"), "layout": r.get("layout_key"), "V": r.get("V"), "status": r.get("status"),
                          "esc": r.get("n_escalations"), "LB_rel": r.get("LB_relaxed_budget")} for r in wr],
                        [("name", "layout"), ("layout", "key"), ("V", "V written"), ("status", "status"), ("esc", "escalations"),
                         ("LB_rel", "LB (relaxed, valid)")], 2) + [""]
    lines += RC.summary_lines(run.dir)
    lines += ["## Caveats", "",
              "* Every ILP value is an upper bound on the unpruned optimum (PRUNING_NYC; approach radius when set); V* is the "
              "optimum under the all-candidates library convention.",
              "* Regional bounds use free sizes (design 7.1 item 1) on the S_LP scenarios and the superset value elsewhere.",
              "* Hubs are allowed at the hub-capable candidates only; the role table says what the alternatives cost.",
              "* open_sites values (re-plan): the follower repositions only to open sites and depots; such a value is a "
              "feasible value, hence an upper bound, of the all-candidates follower; its ILP bounds hold for the open-sites "
              "follower only and are never used as all-candidates lower bounds."]
    path = os.path.join(run.dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    # map data for outputs/r7_siting/figs/siting_map.py
    lp_loc = {}
    for r in recs:
        if r.get("kind") == "lp_location":
            lp_loc[r["location"]] = r.get("v_LP")
    best_keys = {b: ((best_now.get(b) or (None,))[0] or (res.get(b) or {}).get("best_layout")) for b in ctx.budgets}
    infeasible_locs = set((fsl or {}).get("locations") or [])
    near_locs = {BL.Layout.from_key(k).open[0][0] for _v, k in near}
    pair_st: Dict[str, str] = {}               # production m = 2 search: pair screens (r7_search stage pairs)
    for r in recs:
        if r.get("kind") == "pair_screen":
            for loc in r.get("atoms") or []:
                st = "screened" if not r.get("excluded") else "excluded"
                if pair_st.get(loc) != "screened":
                    pair_st[loc] = st
    import csv
    with open(os.path.join(run.dir, "map_data.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "lat", "lon", "cls", "dot_type", "hub_capable", "lattice_id", "v_LP_one_site", "cell_x", "cell_y",
                    "in_best_m1", "in_best_m2", "in_best_m3", "pilot", "terminal_infeasible", "near_tie_m1", "pair_status"])
        for c in ctx.candidates:
            inb = {m: (best_keys.get(float(m) * unit) or "").find(c.id + ":") >= 0 for m in (1, 2, 3)}
            w.writerow([c.id, c.lat, c.lon, c.cls, c.dot_type or "", int(bool(c.hub_capable)), c.lattice_id or "", lp_loc.get(c.id),
                        (c.cell or ["", ""])[0], (c.cell or ["", ""])[1], int(inb[1]), int(inb[2]), int(inb[3]),
                        int(c.dot_type == "pilot"), int(c.id in infeasible_locs), int(c.id in near_locs),
                        pair_st.get(c.id, "")])
    print(f"# wrote {path}", flush=True)
    return path


# ---------------------------------------------------------------------------
# lanes
# ---------------------------------------------------------------------------
def fit_workers(args: argparse.Namespace, usable: int) -> Tuple[int, int]:
    """Worker counts that fit the thread budget ``usable``: ``lp_workers x lp_threads +
    master_threads <= usable`` and ``price_workers x threads <= usable`` (the requested counts
    reduced, never raised; at least one worker each).  16 vCPU (12 threads): 5 x 2 + 2 LP
    workers, 4 x 3 pricing workers; 32 vCPU (24 threads): 11 x 2 + 2 and 8 x 3."""
    lp_w = max(1, min(int(args.lp_workers), (int(usable) - int(args.master_threads)) // max(1, int(args.lp_threads))))
    pr_w = max(1, min(int(args.price_workers), int(usable) // max(1, int(args.threads))))
    return lp_w, pr_w


def write_lanes(args: argparse.Namespace) -> str:
    """Deploy-compatible lanes (``deploy/aws/run_lanes.sh`` format) for the stages, respecting the
    dispatcher's thread budget of a 16- or 32-vCPU instance: LP stages use ``lp_workers x
    lp_threads + master``, ILP stages ``price_workers x threads``; the stages after ``polish``
    (written, oos, compliance, hubecon) run in parallel when the budget allows."""
    vcpu = int(args.vcpu)
    cores = max(1, vcpu // 2)
    usable = int(args.max_threads) if getattr(args, "max_threads_explicit", False) else max(1, min(vcpu - 1, cores * 3 // 2))
    lp_workers, price_workers = fit_workers(args, usable)
    lp_t = lp_workers * args.lp_threads + args.master_threads
    ilp_t = price_workers * args.threads
    # the lanes run from the package root on the server: keep --out-dir relative unless given
    out_dir = args.out_dir if args.out_dir else os.path.relpath(OUT_ROOT + "_smoke" if args.smoke else OUT_ROOT,
                                                                 os.path.dirname(C.OUTPUT_ROOT))
    tail = ((" --smoke" if args.smoke else "") + (f" --scenarios {args.scenarios}" if args.scenarios else "")
            + (" --held-out" if args.held_out else "") + (f" --family {args.family}" if not args.smoke else "")
            + (f" --dot-csv {args.dot_csv}" if args.dot_csv else "") + (f" --reduced {args.reduced}" if args.reduced else "")
            + (f" --approach-radius {args.approach_radius}" if args.approach_radius is not None else "")
            + (f" --max-rss-gb {args.max_rss_gb}" if args.max_rss_gb is not None else "")
            + (f" --budgets {' '.join(str(int(m)) for m in args.budgets)}" if args.budgets else "")
            + (f" --restrict {args.restrict}" if args.restrict != "full" else ""))

    def lane_budget(par: int) -> Tuple[int, int, int]:
        """Worker counts fitted to a lane's OWN thread budget ``par`` and the threads it then
        really uses (``max(lp_w x lp_threads + master, price_w x threads)``, at least one
        worker each): every process declares exactly the pools it opens (fixer pass; the
        dispatcher sums the declared column)."""
        lp_w, pr_w = fit_workers(args, max(1, int(par)))
        used = max(lp_w * args.lp_threads + args.master_threads, pr_w * args.threads)
        return lp_w, pr_w, used

    def command(stage: str, threads: int) -> Tuple[str, int]:
        lp_w, pr_w, used = lane_budget(threads)
        return (f"python3 experiments/r7_siting.py --stage {stage} --out-dir {out_dir} --lp-workers {lp_w} "
                f"--lp-threads {args.lp_threads} --threads {args.threads} --price-workers {pr_w} "
                f"--master-threads {args.master_threads} --max-threads {used}" + tail), used
    lanes = []

    def add(name, threads, after, stage, minutes):
        cmd, used = command(stage, threads)
        lanes.append({"name": name, "threads": int(used), "after": after, "stage": stage, "command": cmd,
                      "expected_wall_min": minutes})
    add("r7_setup", lp_t, "-", "setup", EST_MIN["setup"])
    add("r7_comparison", max(lp_t, ilp_t), "r7_setup", "comparison", EST_MIN["comparison"])
    add("r7_m1", max(lp_t, ilp_t), "r7_comparison", "m1", EST_MIN["m1"])
    add("r7_bb2", max(lp_t, ilp_t), "r7_m1", "bb2", EST_MIN["bb2"])
    add("r7_bb3", max(lp_t, ilp_t), "r7_bb2", "bb3", EST_MIN["bb3"])
    add("r7_polish", max(lp_t, ilp_t), "r7_bb3", "polish", EST_MIN["polish"])
    # the post-polish lanes run side by side: each gets its own (smaller) budget and worker counts
    par = min(ilp_t, max(3, usable // 3)) if usable >= 9 else ilp_t
    for st in ("restricted", "written", "oos", "compliance", "hubecon"):
        add(f"r7_{st}", par if st != "compliance" else min(par, 3), "r7_polish", st, EST_MIN[st])
    add("r7_analyse", 1, "r7_restricted,r7_written,r7_oos,r7_compliance,r7_hubecon", "analyse", EST_MIN["analyse"])
    lanes_dir = os.path.abspath(args.lanes_dir) if args.lanes_dir else LANES_ROOT
    os.makedirs(lanes_dir, exist_ok=True)
    path = os.path.join(lanes_dir, "lanes.txt")
    lines = ["# R7 siting lanes for deploy/aws/run_lanes.sh -- written by experiments/r7_siting.py --write-lanes",
             f"# target: {vcpu} vCPU = {cores} physical cores -> dispatcher budget {usable} threads; "
             f"LP stages {lp_t} threads, ILP stages {ilp_t} threads",
             f"# start on the server (from the project root, after deploy/aws/sync_up.sh): "
             f"LANES_DIR=ebike_swap_sim/outputs/cloud_lanes_siting deploy/aws/run_lanes.sh start "
             f"ebike_swap_sim/outputs/cloud_lanes_siting/lanes.txt --max-threads {usable}",
             "# setup -> comparison -> m1 -> bb2 -> bb3 -> polish -> (restricted | written | oos | compliance | hubecon) -> analyse",
             "# every lane declares the threads its own pools use (--max-threads of its command); the parallel lanes fit together",
             "# every stage resumes from records.jsonl + cuts.jsonl + cache/; re-run `run_lanes.sh start` after a Spot restart",
             "# regenerate after stage comparison with the measured unit times (design 3.3) when they exceed the table by 30 %",
             "# format: name <TAB> threads <TAB> after <TAB> command (bash, from the package root)"]
    for l in lanes:
        lines.append(f"# {l['name']}: about {l['expected_wall_min']} min (design 3.2 estimate)")
        lines.append("\t".join([l["name"], str(l["threads"]), l["after"], l["command"]]))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    meta = {"lanes": lanes, "vcpu": vcpu, "physical_cores": cores, "usable_threads": usable, "lp_threads_total": lp_t,
            "ilp_threads_total": ilp_t, "lp_workers": lp_workers, "price_workers": price_workers, "expected_wall_min_sum": sum(l["expected_wall_min"] for l in lanes),
            "critical_path_min": sum(EST_MIN[s] for s in ("setup", "comparison", "m1", "bb2", "bb3", "polish", "written", "analyse")),
            "parallel_lane_threads": {l["name"]: l["threads"] for l in lanes if l["after"] == "r7_polish"}}
    with open(os.path.join(lanes_dir, "lanes.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    print(f"wrote {path} ({len(lanes)} lanes; budget {usable} threads; critical path about {meta['critical_path_min']} min)")
    return path


def _lane_tail(args: argparse.Namespace) -> str:
    """The configuration arguments every lane of one run repeats (same as :func:`write_lanes`,
    plus the R7 production switches when they are not 'auto')."""
    tail = ((" --smoke" if args.smoke else "") + (f" --scenarios {args.scenarios}" if args.scenarios else "")
            + (" --held-out" if args.held_out else "") + (f" --family {args.family}" if not args.smoke else "")
            + (f" --dot-csv {args.dot_csv}" if args.dot_csv else "") + (f" --reduced {args.reduced}" if args.reduced else "")
            + (f" --approach-radius {args.approach_radius}" if args.approach_radius is not None else "")
            + (f" --max-rss-gb {args.max_rss_gb}" if args.max_rss_gb is not None else "")
            + (f" --budgets {' '.join(str(int(m)) for m in args.budgets)}" if args.budgets else "")
            + (f" --restrict {args.restrict}" if args.restrict != "full" else "")
            + (f" --lp-method {args.lp_method}" if args.lp_method != "barrier" else ""))
    for flag, name in (("--superset", "superset"), ("--root-merge", "root_merge"), ("--lp-lifecycle", "lp_lifecycle"),
                       ("--escalate-batch", "escalate_batch")):
        v = getattr(args, name, "auto")
        if v != "auto":
            tail += f" {flag} {v}"
    return tail


def write_stage_lanes(args: argparse.Namespace) -> str:
    """Lanes for the per-scenario stages of the production plan (``deploy/aws/run_lanes.sh``
    format, ``lanes_<kind>.txt`` / ``.json`` in ``--lanes-dir``):

    * ``--lanes rootlp`` (stage D): one lane per scenario, longest stratum first
      (:func:`root_order`), in ``--root-concurrency`` chains (default 3; lane ``i`` runs after
      lane ``i - k``), so at most ``k`` all-open LPs run at once whatever the dispatcher's
      budget; each lane declares ``--lp-threads`` threads and solves one LP.
    * ``--lanes feas`` (stage A): ``--feas-processes`` lanes (default 4) with disjoint scenario
      groups (round robin over the longest-first order), one thread each (library builds)."""
    vcpu = int(args.vcpu)
    cores = max(1, vcpu // 2)
    usable = int(args.max_threads) if getattr(args, "max_threads_explicit", False) else max(1, min(vcpu - 1, cores * 3 // 2))
    out_dir = args.out_dir if args.out_dir else os.path.relpath(OUT_ROOT + "_smoke" if args.smoke else OUT_ROOT,
                                                                 os.path.dirname(C.OUTPUT_ROOT))
    if args.smoke:
        design = [{"level": 1.0, "day_type": "weekday"} for _s in (0, 1)]
    elif args.scenarios:
        design = S.scenario_design(args.scenarios)
    else:
        design = [{"level": 1.25, "day_type": "weekday"} for _s in (args.seeds or [0, 1, 2])]
    order = root_order(design)
    tail = _lane_tail(args)
    lanes: List[Dict[str, Any]] = []
    if args.lanes == "rootlp":
        k = max(1, int(args.root_concurrency))
        T = max(1, int(args.lp_threads))
        for i, s in enumerate(order):
            cmd = (f"python3 experiments/r7_siting.py --stage rootlp --root-scenarios {s} --out-dir {out_dir} "
                   f"--lp-threads {T} --lp-workers 1 --threads 1 --price-workers 1 --master-threads 1 --max-threads {T}" + tail)
            lanes.append({"name": f"r7_rootlp_s{s:02d}", "threads": T, "after": "-" if i < k else lanes[i - k]["name"],
                          "stage": "rootlp", "scenarios": [s], "command": cmd, "expected_wall_min": EST_MIN["rootlp"]})
        head = (f"# {len(order)} all-open root LPs in {k} chains (longest stratum first); at most {k} x {T} = {k * T} "
                f"threads at once (dispatcher budget {usable})")
    else:
        P = max(1, min(int(args.feas_processes), len(order)))
        for g in range(P):
            grp = sorted(order[g::P])
            cmd = (f"python3 experiments/r7_siting.py --stage feas --feas-scenarios {' '.join(str(s) for s in grp)} "
                   f"--out-dir {out_dir} --lp-threads 1 --lp-workers 1 --threads 1 --price-workers 1 --master-threads 1 "
                   f"--max-threads 1" + tail)
            lanes.append({"name": f"r7_feas_{g + 1}", "threads": 1, "after": "-", "stage": "feas", "scenarios": grp,
                          "command": cmd, "expected_wall_min": EST_MIN["feas"]})
        head = f"# one-site feasibility screen in {P} processes (library builds only, 1 thread each)"
    lanes_dir = os.path.abspath(args.lanes_dir) if args.lanes_dir else LANES_ROOT
    os.makedirs(lanes_dir, exist_ok=True)
    path = os.path.join(lanes_dir, f"lanes_{args.lanes}.txt")
    lines = [f"# R7 siting {args.lanes} lanes for deploy/aws/run_lanes.sh -- written by experiments/r7_siting.py "
             f"--write-lanes --lanes {args.lanes}", head,
             "# format: name <TAB> threads <TAB> after <TAB> command (bash, from the package root)"]
    for l in lanes:
        lines.append("\t".join([l["name"], str(l["threads"]), l["after"], l["command"]]))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(lanes_dir, f"lanes_{args.lanes}.json"), "w", encoding="utf-8") as fh:
        json.dump({"lanes": lanes, "kind": args.lanes, "order": order, "vcpu": vcpu, "usable_threads": usable}, fh, indent=1)
    print(f"wrote {path} ({len(lanes)} lanes)")
    return path


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", default="all", help="comma-separated stages or 'all': " + ", ".join(STAGES))
    ap.add_argument("--smoke", action="store_true", help="toy instance, Threads 1, seconds")
    ap.add_argument("--dry-run", action="store_true", help="plan / sizes only, no solve")
    ap.add_argument("--redo", action="store_true", help="re-run stages that have a stage_done record")
    ap.add_argument("--family", default=S.MANHATTAN_DOT_FAMILY, choices=[S.MANHATTAN_DOT_FAMILY, S.R5_MANHATTAN_FAMILY])
    ap.add_argument("--dot-csv", default=None, help=f"DOT candidate CSV (default {S.DOT_CSV_DEFAULT})")
    ap.add_argument("--merge-m", type=float, default=80.0)
    ap.add_argument("--cap", type=int, default=60)
    ap.add_argument("--reduced", type=int, default=None, help="use only the first N candidates (server smoke)")
    ap.add_argument("--menu", choices=["reduced", "full"], default="reduced")
    ap.add_argument("--scenarios", type=int, default=12, help="stratified design size (6, 10, 12, 15); 0 = --seeds")
    ap.add_argument("--seeds", nargs="*", type=int, default=None, help="plain seeds when --scenarios 0 (reproduction)")
    ap.add_argument("--held-out", action="store_true", help="also build the held-out scenarios (stage oos)")
    ap.add_argument("--approach-radius", type=int, default=None, help="move arcs into candidates only from within N blocks")
    ap.add_argument("--budgets", nargs="*", type=float, default=None, help="budget multipliers m (default 1 2 3)")
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--lp-threads", type=int, default=2)
    ap.add_argument("--lp-workers", type=int, default=12, help="scenario LPs in parallel (fitted to --max-threads by --write-lanes)")
    ap.add_argument("--price-workers", type=int, default=8, help="pricing ILPs in parallel (fitted to --max-threads by --write-lanes)")
    ap.add_argument("--master-threads", type=int, default=2)
    ap.add_argument("--max-threads", type=int, default=None, help="thread budget (default run_lanes.sh rule)")
    ap.add_argument("--max-rss-gb", type=float, default=None)
    ap.add_argument("--time-limit", type=float, default=300.0)
    ap.add_argument("--time-limit-hub", type=float, default=600.0)
    ap.add_argument("--tol-rel", type=float, default=0.0025)
    ap.add_argument("--tol-abs", type=float, default=1.0)
    ap.add_argument("--max-escalations", type=int, default=None,
                    help="escalation levels per (layout, scenario); default 3 for manhattan_dot (production plan 5 "
                         "item 3), 2 for the toy and r5_manhattan (the old default); a level whose limit equals the "
                         "previous one (cap) is skipped")
    ap.add_argument("--escalate-batch-max", default="auto",
                    help="batched escalation at levels >= 2: at most N open cells per batch, largest p_s x gap first "
                         "(auto: --price-workers for manhattan_dot, unlimited otherwise; 0 = unlimited)")
    ap.add_argument("--escalate-factor", type=float, default=3.0, help="time limit x factor per escalation level")
    ap.add_argument("--escalate-cap-s", type=float, default=1800.0, help="cap of an escalated time limit (s)")
    ap.add_argument("--escalate-batch", choices=["auto", "on", "off"], default="auto",
                    help="re-price all open scenarios of a layout in one parallel wave (auto: on for manhattan_dot)")
    ap.add_argument("--enum-limit", type=int, default=5000)
    ap.add_argument("--m1-pass2", choices=["on", "off"], default="on",
                    help="stage m1: 'off' (R7 re-plan change 5, the M4 resume) tests the prunes of pass 2 but prices "
                         "nothing (no warm pricing, no escalation); the floor is computed as before.  Runs even when "
                         "m1 has a stage_done record (an explicit resume pass)")
    ap.add_argument("--verify-start", choices=["always", "unchecked"], default="always",
                    help="Gurobi fix-and-solve verification of the ILP MIP start: 'always' (old behaviour) or only "
                         "for starts that did not pass evaluate.check ('unchecked', R7 re-plan change 6; not in the "
                         "cache key, saves up to 60 s per cell)")
    ap.add_argument("--cover-rows", choices=["on", "off"], default="on",
                    help="'off': the stage's master without cover rows (no all-candidates template at start-up; valid, "
                         "weaker master bound, the prior LBs are restored); r7_search.py stages (the list pricing lanes "
                         "M1 / M3 / M5, m3) and stages comparison / restricted here; ignored by the other stages")
    ap.add_argument("--price-tier", choices=list(BD.PRICING_TIERS), default="all_candidates",
                    help="pricing tier of the reported values of stages comparison / restricted (here) and pairs / m3 / "
                         "roles / oos / noradius (r7_search.py): 'open_sites' (R7 re-plan change 7; production batches "
                         "4-6) prices on the open-sites library, a valid upper bound only (no cut, never an LB); the "
                         "tables then show UB (open_sites) and the all-candidates LB (envelope / LP / subset) apart")
    ap.add_argument("--time-limit-many-sites", default=None,
                    help="'K:SECONDS': per-cell ILP limit of a layout with K or more open sites (re-plan section 3: "
                         "5:900 for the DOT all-pilot layout on the open-sites tier); default none (unchanged)")
    ap.add_argument("--bnb-nodes", nargs="*", type=int, default=[200, 100])
    ap.add_argument("--bnb-levels-m3", type=int, default=2,
                    help="levels visited by the m = 3 B&B passes (2 = regions and cells; nodes below stay open at their bound)")
    ap.add_argument("--restrict", choices=["full", "dot"], default="full",
                    help="stage restricted: 'dot' fixes the lattice-only candidates closed (DOT-only vs full, table T3)")
    ap.add_argument("--max-leaf-combos", type=int, default=64)
    ap.add_argument("--written-layouts", type=int, default=8)
    ap.add_argument("--hub-screen", type=int, default=2)
    ap.add_argument("--alphas", nargs="*", type=float, default=[0.0, 0.25, 0.5, 0.75, 1.0])
    ap.add_argument("--draws", type=int, default=3)
    ap.add_argument("--lp-method", choices=list(BD.LP_METHODS), default="barrier")
    ap.add_argument("--final-master-s", type=float, default=120.0)
    # R7 production plan section 5 items 1, 2, 4 ('auto' = on for manhattan_dot, off for the toy and r5_manhattan)
    ap.add_argument("--superset", choices=["auto", "on", "off"], default="auto",
                    help="per-bike superset LP bound (auto: off for manhattan_dot, where it times out; L_s = 0 then)")
    ap.add_argument("--root-merge", choices=["auto", "on", "off"], default="auto",
                    help="raise L_s to the all-open free-size root LP values (root_lp/ files, pool subset cuts)")
    ap.add_argument("--root-scenarios", nargs="*", type=int, default=None,
                    help="stage rootlp: scenario indices (default all, longest stratum first)")
    ap.add_argument("--root-import", default=None,
                    help="stage rootlp: import the all-open subset cuts of another cuts.jsonl with the same pool signature")
    ap.add_argument("--lp-lifecycle", choices=["auto", "on", "off"], default="auto",
                    help="lazy scenario LPs, disposed between the m1 LP and pricing passes; no LP in comparison / restricted")
    ap.add_argument("--evict-templates", action="store_true", help="evict a scenario's template right after its LP is built")
    ap.add_argument("--max-templates", type=int, default=None, help="at most N templates resident (LRU eviction)")
    ap.add_argument("--feas", choices=["auto", "off"], default="auto",
                    help="use the one-site feasibility screens (feas_one_site*.json of --out-dir or --feas-json)")
    ap.add_argument("--feas-json", nargs="*", default=None, help="feasibility screen files (default: --out-dir/feas_one_site*.json)")
    ap.add_argument("--feas-scenarios", nargs="*", type=int, default=None, help="stage feas: scenario indices (default all)")
    ap.add_argument("--feas-verify", choices=["auto", "always"], default="auto",
                    help="re-prove every claim by a library build ('auto': only claims of a screen with another signature)")
    ap.add_argument("--lanes", choices=["pipeline", "rootlp", "feas"], default="pipeline",
                    help="--write-lanes: the stage pipeline, or one lane per scenario for rootlp / per group for feas")
    ap.add_argument("--root-concurrency", type=int, default=3, help="--lanes rootlp: chains (at most this many at once)")
    ap.add_argument("--feas-processes", type=int, default=4, help="--lanes feas: parallel screen processes")
    # R7 production plan section 5 item 5 (comparison filter)
    ap.add_argument("--comparison-rules", nargs="*", default=None,
                    help="stage comparison: rows NAME or NAME@m1,m2 (CSCD, CSTC, CSAV, dot_pilot_proxy, dot_all_pilot, "
                         "transplant); default every row")
    ap.add_argument("--comparison-budgets", nargs="*", type=int, default=None,
                    help="stage comparison: m values of the per-budget rows named without @ (default every budget)")
    ap.add_argument("--comparison-time-limits", nargs="*", default=None,
                    help="stage comparison: per-row ILP limits 'm:seconds' (auto: 2:600 for manhattan_dot, none otherwise)")
    for st, h in (("setup", 2.0), ("comparison", 5.0), ("m1", 4.0), ("bb2", 11.0), ("bb3", 5.0), ("polish", 1.5),
                  ("restricted", 1.0), ("written", 3.0), ("oos", 2.5), ("compliance", 1.0), ("hubecon", 1.5)):
        ap.add_argument(f"--wall-{st}", type=float, default=h, help=f"hours for stage {st}")
    ap.add_argument("--write-lanes", action="store_true")
    ap.add_argument("--lanes-dir", default=None)
    ap.add_argument("--vcpu", type=int, default=16)
    return ap


def parse_args(argv: Optional[List[str]] = None, parser: Optional[argparse.ArgumentParser] = None) -> argparse.Namespace:
    """Parsed arguments with the smoke defaults and the thread budget applied (used by the
    reproduction check ``tests`` and scripts that build a :class:`Ctx` without running a stage;
    ``parser``: an extension of :func:`build_parser`, e.g. ``experiments/r7_search.py``)."""
    args = (parser or build_parser()).parse_args(argv)
    args.max_threads_explicit = args.max_threads is not None
    if args.smoke:
        args.threads = args.lp_threads = args.master_threads = 1
        args.lp_workers = args.price_workers = 2
        args.tol_rel, args.tol_abs = 1e-9, 1e-6
        args.time_limit = args.time_limit_hub = 30.0
        args.scenarios = 0
        args.held_out = True
        args.alphas = [0.0, 0.5, 1.0]
        args.draws = 1
        args.restrict = "dot"
    if args.max_escalations is None:            # fixer pass: older families keep the old default 2
        args.max_escalations = 3 if (not args.smoke and args.family == S.MANHATTAN_DOT_FAMILY) else 2
    if args.max_threads is None:
        args.max_threads = default_max_threads()
    return args


#: laptop analysis stages: no cost.jsonl row (review of 2026-10-21)
UNBILLED_STAGES = ("analyse",)


def main(argv: Optional[List[str]] = None) -> Any:
    args = parse_args(argv)
    if args.write_lanes:
        return write_stage_lanes(args) if getattr(args, "lanes", "pipeline") != "pipeline" else write_lanes(args)
    stages = list(STAGES) if args.stage == "all" else [s.strip() for s in args.stage.split(",") if s.strip()]
    for st in stages:
        if st not in STAGES:
            raise SystemExit(f"unknown stage {st!r}; choose from {STAGES}")
    if stages and all(st in POOL_FREE_STAGES for st in stages):
        if args.lp_threads > args.max_threads:     # rootlp: one LP at lp_threads; feas: library builds only
            raise SystemExit(f"lp_threads exceeds --max-threads {args.max_threads}")
    else:
        if args.lp_workers * args.lp_threads + args.master_threads > args.max_threads:
            raise SystemExit(f"lp_workers x lp_threads + master_threads exceeds --max-threads {args.max_threads}")
        if args.price_workers * args.threads > args.max_threads:
            raise SystemExit(f"price_workers x threads exceeds --max-threads {args.max_threads}")
    warnings.simplefilter("ignore")
    run = Run(args)
    # R7 production plan 5 item 7: one cost.jsonl row per invocation (also when it fails)
    cost = RC.CostLog(run.dir, ",".join(stages), "r7_siting.py", dry_run=bool(args.dry_run), argv=argv,
                      enabled=not all(st in UNBILLED_STAGES for st in stages))
    cost.install_signal_handlers()              # run_lanes.sh stop / tmux kill-session still write the row
    status = "error"
    try:
        ctx = Ctx(run)
        md5 = ctx.config_md5()
        out: Dict[str, Any] = {}
        for st in stages:
            run.stage = st
            resume_pass = st == "m1" and str(getattr(args, "m1_pass2", "on") or "on") == "off"   # re-plan change 5
            if st in SOLVE_STAGES and not args.dry_run and not args.redo and not resume_pass \
                    and stage_done(run.load(), st, md5):
                run.emit({"kind": "stage_skipped", "stage": st, "reason": "stage_done record with the same configuration"}, echo=True)
                continue
            t0 = time.perf_counter()
            fn = {"setup": stage_setup, "feas": stage_feas, "rootlp": stage_rootlp, "comparison": stage_comparison, "m1": stage_m1, "bb2": lambda r, c: stage_bnb(r, c, 2),
                  "bb3": lambda r, c: stage_bnb(r, c, 3), "polish": stage_polish, "restricted": stage_restricted,
                  "written": stage_written, "oos": stage_oos,
                  "compliance": stage_compliance, "hubecon": stage_hubecon, "analyse": analyse}[st]
            out[st] = fn(run, ctx)
            if not args.dry_run:
                with open(os.path.join(run.dir, "wall_time.json"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"stage": st, "wall_s": time.perf_counter() - t0, "rss_gb": rss_gb(),
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
